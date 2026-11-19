# SAGGA GRID: two Launchpads as one pad grid for the FM-1

```
 Launchpad (left)  ─┐          ┌──────────────── Raspberry Pi ────────────────┐
 Launchpad (right) ─┼─ USB ───►│ sagga_grid_bridge.py  ◄────────►  FM-1 (USB) │
 FM-1              ─┤          │ RaspiMIDIHub:  FM-1  ◄────────►  synths, boxes│
 synths, boxes     ─┘          └───────────────────────────────────────────────┘
```

The FM-1 is a USB device (not a host) and its TRS jack is a MIDI input only, so the Launchpads cannot be plugged
into it. They go to the Pi, next to RaspiMIDIHub. `tools/sagga_grid_bridge.py`, a small program on that Pi, joins them
into one **16 x 8 grid** (left Launchpad = columns 1-8, right = 9-16, row 1 on top) and exchanges plain MIDI with
the FM-1. The firmware knows nothing about Launchpads, only about that grid, so another controller only needs
another bridge.

This is the idea of the **midigrid** mod for norns, which makes two Launchpads one grid: each is a quad of a
virtual grid, the first one the left. What midigrid learned about the Launchpad Mini MK3 is used here as it is
in its source (github.com/jaggednz/midigrid, GPL-3.0, as is this): programmer mode; the flash and pulse layers
of every LED cleared at start; only SysEx sent to the Launchpad; the second USB MIDI interface of the Mini MK3
(the first is for DAWs) is the one that is used; the LED colours go out as 7-bit RGB, 80 LEDs in one message.
What is different: here the "script" that draws on the grid is the FM-1 itself, and the Pi is the norns.
Not taken over: rotating a Launchpad by 90 degrees, and 2 x 2 (16 x 16) layouts.

Status (0.9): tested in the host simulator (the real firmware code) and with fake MIDI ports. The bridge with `--model mini
--frame` runs on a Raspberry Pi 4 with two first-generation Launchpad Minis and the FM-1 (0.7). Three drivers:

| `--model` | for | how |
|---|---|---|
| `mk3` (default) | Launchpad Mini MK3 (RGB, USB-C) | midigrid's driver and Novation's Programmer's Reference: programmer mode, RGB SysEx |
| `mini` | **Launchpad Mini MK1 / MK2** (red, green and amber only, micro / mini USB) and the first Launchpad | the X-Y layout of Novation's Launchpad Programmer's Reference: pads Note y*16+x, right column Note y*16+8, top row CC 104-111, LED = velocity 16*green + red + 12. The 16 roles become 16 shades of red / green / amber |
| `mk2` | Launchpad MK2 (RGB, 9 x 9) | midigrid's driver, palette colours; untested |

Which Mini you have: a Mini MK3 has a USB-C socket and RGB pads. A Mini with red / green / yellow pads only and a
mini-USB socket is an MK1 or MK2: use `--model mini`. (Windows names two of them "Launchpad Mini" and
"Launchpad Mini 10"; on the Pi they are told apart by their ALSA client number.)

## 1. Set-up

### 1.1 The bridge on the Pi that runs RaspiMIDIHub

RaspiMIDIHub's Pi is a Raspberry Pi OS Lite with Python 3.11 and ssh, and its root filesystem is read-only: `rw`
makes it writable, `ro` locks it again. The Pi needs an internet connection for the one-off install (the hub
manual, chapter 13: Ethernet, USB tethering or WiFi client mode). From a computer:

```
scp tools/sagga_grid_bridge.py tools/sagga-grid-bridge.service <you>@raspimidihub-<id>.local:/tmp/
ssh <you>@raspimidihub-<id>.local
rw
sudo apt install python3-mido python3-rtmidi      # or a venv with: pip install mido python-rtmidi
sudo mkdir -p /opt/sagga && sudo cp /tmp/sagga_grid_bridge.py /tmp/sagga-grid-bridge.service /opt/sagga/
python3 /opt/sagga/sagga_grid_bridge.py --list
```

`--list` shows the MIDI ports. With both Launchpads and the FM-1 plugged in, try it by hand:

```
python3 /opt/sagga/sagga_grid_bridge.py --model mini --identify   # left half green, right half red; press a pad of each
python3 /opt/sagga/sagga_grid_bridge.py --model mini              # run (add --swap if the halves are the wrong way round)
```

(`--model mini` for the red / green Minis; leave it out for Mini MK3s. `--frame`: the left one turned, its round buttons
framing the grid.) It prints the ports it chose. Then as a service, so that it starts with the Pi and starts again
after a cable was pulled. The service file says `--model mini --frame`; change that line if your set-up differs (add
`--swap` if you needed it):

```
sudo nano /opt/sagga/sagga-grid-bridge.service    # ExecStart=/usr/bin/python3 /opt/sagga/sagga_grid_bridge.py --model mini --frame
sudo cp /opt/sagga/sagga-grid-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sagga-grid-bridge
ro
```

The log: `journalctl -u sagga-grid-bridge -e`. (The unit runs as root like the hub's own; to run it as yourself, add
`User=<you>` and `SupplementaryGroups=audio` to it.)

* The FM-1 is found by its USB name (Felucca-based firmware, which SAGGA SEQ is, calls itself **"Felucca"**); the
  default pattern is `FM-1|Felucca`. If `--list` shows another name, give it with `--fm1 REGEX`.
* **USB PORTS 2** (0.8, the FM-1's USB page): the FM-1 has two ports, "Felucca MIDI 1" (the synths) and "Felucca MIDI
  2" (the grid). The bridge takes port 2 by itself (`--port auto`; `--port 1` / `--port 2` to choose).
* Two identical Launchpads are told apart by their ALSA client number (the lower one is left, the order in which
  Linux found them). `--swap` exchanges them, or name them with `--left REGEX --right REGEX`.
* A Mini MK3 has two MIDI ports per unit. The bridge ignores the ones whose name has `DAW` or `DIN` (`--exclude`)
  and, if two remain, takes the one with the higher port number: the second USB interface, as midigrid does.

On any other Linux, macOS or Windows machine that sees the Launchpads and the FM-1 as MIDI ports it is the same
program with `pip install mido python-rtmidi`.

### 1.1b Projects saved on the Pi: the LIBRARY

While the bridge runs, the EXPORT pad (PROJ view, FM-1 stopped) sends the project over and the bridge saves it as
`sagga-001.sgq`, `sagga-002.sgq` ... in `/boot/firmware/sagga/`: RaspiMIDIHub keeps the root file system read-only,
and the boot partition is where it keeps what must survive (`--dump-dir` chooses another folder; the journal shows the
path). The hub mounts that partition read-only as well, so the bridge (0.5) opens it for writing only while it writes
a file, then closes it again, under the hub's own lock (0.4 could not save there). Put the SD card (or the SSD) in a
Windows PC and the files are on the small FAT partition, in `sagga\`: rename them there, `01-techno.sgq`,
`02-gqom.sgq` ..., and that is the order of the setlist.

Those files are the **LIB view** of the grid (SHIFT + REC twice): load one, the next one, save over one. To send a
file back without the grid (FM-1 stopped; it replaces the project there), and to fetch the project or a slot:

```
sudo python3 /opt/sagga/sagga_grid_bridge.py --import /boot/firmware/sagga/sagga-001.sgq
sudo python3 /opt/sagga/sagga_grid_bridge.py --export          # or --export 3 for slot 3
```

These work while the service runs (ALSA shares the FM-1's port) and from any computer with the FM-1 on USB.

### 1.1e More variations and progressions on the Pi (0.11)

The bridge also keeps, next to the projects, a folder **`patterns/`** and a folder **`progressions/`**: one text file
a genre (`TECHNO.txt` ...). The first time a genre's file changes it is started from the stock one that
`install_hub.sh` put in `/opt/sagga/hub/` (the next 12 / 6 variations of every part after the FM-1's, and 701
progressions by mood); from then on that file is yours.

* `patterns/TECHNO.txt`: a line a variation, `PART <tab> pattern <tab> notes` (`KICK	X...X...X..xX...	-`,
  `BASS	x-..x.x.	0...7.c.`). On the FM-1, SEQ + ALG past the last variation shows `#13/12+PI` ...: BEAT loads it.
  SEQ + SAVE adds the selected track's loop at the end of the file.
* `progressions/TECHNO.txt`: a line a progression, `MOOD <tab> chords [<tab> a name]`; the chords above the key's root,
  small for minor, with their shape, their own length (`:8`) and push (`^1`): `EPIC	i bVI bVII i`,
  `SATISFYING	ii7:8 V7:8 Imaj7^1`. On the FM-1, SEQ 4 K2 past the last progression goes into them (those of the HARMONY's
  genre and MOOD, the most like the one playing first). SEQ + SAVE on SEQ 4 or SEQ 8 adds one.

The SAGGA HUB page (port 8090) lists both, a genre at a time, deletes a line, and adds a progression typed in. The
bridge logs every one it sends or keeps (`journalctl -u sagga-grid-bridge`).

### 1.1c Snapshot patches (0.8)

A snapshot can bring back the synths' own patches: SAVE + black 11 (or the FX view's PATCHES pad) asks the bridge to
keep them, and when the snapshot comes back the bridge sends them to the synths again. The bridge needs to know your
synths: write `/boot/firmware/sagga/patches.json` (on a PC: `sagga\patches.json` on the SD card's FAT partition):

```
{
  "synths": [
    {"name": "MySynth", "port": "MySynth", "request": "F0 .. F7", "wait": 3},
    {"name": "TD-3", "port": "TD-3"}
  ],
  "send_while_playing": true
}
```

* `port`: a part of the synth's MIDI port name as `--list` shows it (a regex). The synth must be plugged into the Pi.
* `request`: the SysEx that asks the synth for its current patch (its MIDI implementation chart says which; `F0 .. F7`
  above stands for it, write the real bytes in hex). Without
  one, the bridge listens for `wait` seconds (default 10): send the patch from the synth by hand (its "send / dump"
  function) in that time.
* The patches are kept in `/boot/firmware/sagga/patches/<project id>/s<snapshot>/<name>.syx`, the same files any
  SysEx librarian reads.
* `send_while_playing: false` sends them only when the FM-1 is stopped (some synths stop sounding while they load a
  patch).
* 0.23.2: the bridge opens each synth's port **when it starts** (or when the synth is plugged in) and keeps it open.
  Until 0.23.1 it looked at the ports and opened and closed one at every snapshot; each of those is an ALSA client
  that comes and goes, and RaspiMIDIHub builds its whole matrix again at every one - a snapshot recalled while playing
  cut the notes that sounded on every synth. The bridge says `snapshot patches: NAME (ports open: NAME)` at its
  start. Of what a synth sends, the bridge takes its SysEx only.

The bridge prints what it kept and sent (`journalctl -u sagga-grid-bridge -e`); the FM-1's screen says it too.

### 1.1d The regista (0.9)

The FM-1 can tell a program on the Pi where the set is, and take phrases from it (SysEx 50-55, see SAGGA-SEQ.md). The
bridge reads SGQ8 and SGQ9 projects, and has a `Regista` class: `frase(track, bars, steps)` sends a phrase that the
FM-1 writes at the next bar, `led(list16)` lights the REGIA view's rules; `on_stato`, `on_risposta`, `on_toccata`,
`on_key` are called with what the FM-1 says. The FM-1 stays silent until the Pi sends one of these (so a plain bridge
costs nothing). `--regista` prints the STATO frames and starts the conversation with the 16 rules off: a regista
script that imports the bridge does the rest.

### 1.2 What to set in RaspiMIDIHub

The bridge needs **no cell in the routing matrix**: it opens the FM-1 and the two Launchpads itself through ALSA,
next to the hub (ALSA lets several programs listen to one port). RaspiMIDIHub lists only real MIDI devices and its
own plugins, so the bridge does not appear in the matrix, and that is normal. In the matrix, once:

1. **Launchpads: no connections at all**, in either direction. A fresh hub connects new devices to nothing
   (Settings, "Default routing"); if yours is set to all-to-all, or an older config connects them, clear their row
   and column. Otherwise the hub would feed the FM-1's notes into the pads, which a Launchpad in programmer mode takes
   for LED colours, and the pad presses into the FM-1 and the synths.
2. **FM-1 -> synths: block channels 15 and 16** (one USB port). Tap the FM-1 -> synth cell, *Edit*, and in *MIDI
   Channels* tap 15 and 16 so that their dots turn red (red drops the channel). The grid link rides on those two
   channels and a note on channel 16 *is* a note. Do it for every connection that starts at the FM-1. SAGGA SEQ's
   tracks use channels 1-14 only for this reason; clock, start and stop are not channel messages and still pass.
   Nothing at all is sent on 15 / 16 until the bridge has attached. **With USB PORTS 2** none of this: connect the
   synths to the FM-1's **port 1** only (all 16 channels are tracks there) and leave port 2 to the bridge and the
   remote.
3. **Synths -> FM-1**: as you like (notes for recording, clock if the FM-1 is slave), but **block channel 14** there
   too: since 0.5 the CCs on channel 14 are SAGGA REMOTE's commands.
4. **SAGGA Remote / SAGGA Mutes -> FM-1** (if you use the phone remote: tools/raspimidihub/README.md; with USB PORTS 2:
   to port 2). 0.18: and **the FM-1's port 2 -> each SAGGA page** (Remote, Mutes, Motori, Break, Mod, Live): the values
   the FM-1 sends back, so that the tablet's knobs move with the FM-1's.
5. *Save Config.*

The hub sends a MIDI-CI inquiry (a universal SysEx message) to every bidirectional device when it connects. The
FM-1 firmware ignores SysEx that is not its own (the update protocol, and the project dumps that start with
`7D 53 47`). If a Launchpad ever acts oddly right after the hub
starts, the hub can switch the probing off for it (`midi2.ci_disabled`, hub manual chapter 5).

### 1.3 Why it is a program and not a hub plugin (and what the plugins of 0.5 do)

The two plugins of 0.5 (tools/raspimidihub, SAGGA Remote and SAGGA Mutes) are not the grid: they are pages of
buttons and faders for the phone that send SAGGA REMOTE's CCs on channel 14 (docs/SAGGA-SEQ.md).

RaspiMIDIHub plugins can send SysEx (`send_sysex`) and receive notes and CCs, so a plugin could do this job, in two
instances, one per Launchpad. I did not build it: a plugin has one input and one output port per instance, would
have to be copied into the hub's plugin folder on the read-only system, and I cannot run the hub here to try it. The
translation itself (`Bridge` in the script) does no I/O of its own, so it could be wrapped later.

## 2. The protocol (SGP, version 1)

Plain channel messages on the FM-1's USB MIDI port, so any router passes them. x = 0..15 (left to right),
y = 0..7 (top to bottom).

| direction | message | meaning |
|---|---|---|
| to FM-1 | `9F  y*16+x  vel` / `8F ...` | pad down (velocity > 0) / up (velocity 0, or Note Off) |
| to FM-1 | `BE  id  127/0` | button `id` 0..31 down / up |
| to FM-1 | `BF 118 127` | attach: the FM-1 forgets what it sent and repaints every LED |
| to FM-1 | `BF 118 64` | keep-alive, once a second (it also attaches if the FM-1 is not attached, e.g. after a reboot) |
| to FM-1 | `BF 118 0` | detach |
| from FM-1 | `9F  y*16+x  role` | pad LED `role` 0..15 (see below) |
| from FM-1 | `BE  id  role` | button LED |

* **Time-out**: if the FM-1 hears nothing from the grid for 3.5 s it detaches by itself (it lets go of held
  buttons such as FILL, and stops sending LEDs). The bridge's keep-alive prevents that.
* **LED traffic is polite**: changed LEDs only, at most 8 messages every 20 ms, never when fewer than 28 of the
  64 slots of the USB output queue are free (notes and clock always have room), and one LED is sent again every
  100 ms when nothing changed so a dropped message heals itself. The bridge sends every LED to the Launchpads again
  every two seconds, as midigrid refreshes them now and then.
* A full repaint (attach) is 160 messages, about half a second.
* Buttons: 0-7 top row of the left Launchpad, 8-15 top row of the right one, 16-23 and 24-31 the side columns
  (left, right), each from the top.

### LED roles

The colours live in the bridge (`ROLE_RGB`), not in the firmware. (`--model mk2` has no RGB: it takes the nearest of
the palette colours in `MK2_PALETTE`.)

| role | name | used for |
|---|---|---|
| 0 | OFF | nothing |
| 1 | FAINT | a step slot that is off, an unused button |
| 2 | DIM | an inactive control |
| 3 | ON | a step that is on, an active control |
| 4 | ACCENT | a loud step (velocity 110+), the top of a bar |
| 5 | PLAY | the playhead, REC armed |
| 6 | CURSOR | the selected step (on), the current view / track |
| 7 | BLUE | steps on past the pattern length, gate and nudge |
| 8 | MUTED | a muted track |
| 9 | PEND | queued (pattern, scene): the bridge blinks it |
| 10 | FILL | FILL held |
| 11 | WHITE | the current value in a row of choices |
| 12 | CYAN | chance, random density |
| 13 | VIOLET | chord / arp choices |
| 14 | ORANGE | the selected step (off), tools, ratchet |
| 15 | YELLOW | solo, a marker |
| 16 | TAIL (0.12) | a step a long note covers (the note before it still rings): a dark green, so the note reads as one block |
| 17 | TIE (0.12) | a step tied to the next (legato): a lighter green |
| 18 | GHOST (0.24) | a **copy** that plays: the pattern going round again in a track longer than it is (a dim blue-green; on the red-green Launchpads a medium green). A copy at rest is a rest as any other. A bridge older than 0.24 shows it DIM |

## 3. What the pads do

Seventeen views share the 128 pads; the 32 buttons never change. **SHIFT** is button 7 (hold): with it, every button
does its second job, and the buttons that have one turn orange while SHIFT is held. **0.5.1: SHIFT tapped twice
quickly, with nothing else pressed, stays held** (yellow): the grid with one hand; tap it once more to let it go. The FM-1's screen shows the
view on its last line (`G:STEP`, `G:CC`, ...).

### Buttons (always)

| id | button | with SHIFT |
|---|---|---|
| 0 | PLAY / STOP | CONTINUE from where it stopped (the receiver gets the Song Position) |
| 1 | REC arm | the **PROJ** view; in PROJ: the **LIB** view |
| 2 | FILL (hold) | the other bank of tracks (1-8 / 9-12: 0.28, twelve tracks) |
| 3 | UNDO / REDO of the last tool (a dice waiting: BACK) | the **FX** view |
| 4 | the **STEP** view; in STEP: the **DRUM** view | the **CC** view; in CC: **FOLLOW** (0.18; PICK until 0.17) |
| 5 | the **PERF** view; in PERF: the **SONG** view; in SONG: **VIAGGIO**; in VIAGGIO: **REGIA** (once a regista has spoken), then PERF. (0.9-0.16: with VIAGGIO on, the button opened VIAGGIO first; 0.17: PERF first, always) | the **LFO** view |
| 6 | the **TRACK** view; again: **TRACK 2**, again: **TRACK 3** | the **BEAT** view; again: the **EUCLID** view |
| 7 | SHIFT (0.18: cyan while the grid FOLLOWs the FM-1) | |
| 8-15 | select track 1-8 of the bank (blue: bank 2; 0.28: it has four, 9-12 - buttons 12-15 dark) | solo that track |
| 16-23 | pattern 1-8 of the selected track, queued to the end of its loop | copy the playing pattern there (UNDO takes it back) |
| 24-31 | scene 1-8 of the bank the scene cursor is in (1-8 / 9-16), queued to the next bar | store the scene |

A view button is amber when its view is shown, violet when its SHIFT view is, cyan for DRUM and SONG, accent for VIAGGIO, white for REGIA. While stopped, pattern and scene
changes apply at once.

### STEP (the selected track)

| rows | pads |
|---|---|
| 1-4 | the 64 steps, 16 a row (0.8: what you hear; cyan a hit the live layer adds; **0.24: blue-green, a COPY - the pattern going round again in a track longer than it: it follows the pattern until you write on one, then they are all steps of yours**). Tap: on / off (the step becomes the cursor). **Hold one and press another: the note between them** (0.11: the first step plays that long, both counted; the FM-1's SEL + FX tapped first (0.12; FX alone in 0.11): the track loops between them instead, the first one stays as it was). Hold alone half a second: select without changing it. SHIFT + pad: the pattern ends here. Outside the loop: dark (blue if the step is on). 0.12: the steps a long note covers are dark green (TAIL), a tied step light green (TIE): a long note is one block. On a BREAK track the steps are slices: the note row (row 8) is the 16 slices. |
| 5 | velocity of the cursor step, 16 levels |
| 6 | chance, 6 % .. 100 %. **SHIFT: the condition** ALL, 1:2, 2:2, 1:4, 2:4, 3:4, 4:4, FILL, !FILL, 1:3, 2:3, 3:3, 1:8, FIRST, PRE, !PRE (0.10) |
| 7 | left: ratchet 1..8; right: gate 12 % .. 100 %. **SHIFT** (0.10): pad 15 **PLAIN** (no EXPO from this step), pad 16 **TIE** (the note holds into the next step, legato) |
| 8 | notes. Chromatic from C3 (SEL + OCT on the FM-1 moves it), or, on a track that follows the key, **the notes of the scale from its root**: two octaves and more, nothing out of key; the roots are white. Tap: that note (you hear it). SHIFT + tap: add / remove a note, a chord of up to 4 |

### DRUM (STEP again: the eight tracks of the bank, one per row; 0.28: bank 2, four rows)

| pads | |
|---|---|
| tap | that track's step on / off (it plays the track's note: which drum it is) |
| hold half a second | select that track and that step (it stays as it was): the FM-1's knobs edit it |
| SHIFT + pad 1-4 (any row) | the page of 16 steps (a track of 16 steps always shows its 16) |
| SHIFT + another pad | select the track of that row |

Lit: green a hit, bright an accent, red the playhead, amber the cursor of the selected track, dark beyond a track's
length, dim red a muted track's hits.

### PERF (the eight tracks of the bank, one per row; 0.28: bank 2 is tracks 9-12, rows 5-8 dark)

| column | pad |
|---|---|
| 1 | mute (blinking: queued, MUTE QUEUE) |
| 2 | solo |
| 3-10 | pattern 1-8 (green = playing, blinking = queued) |
| 11 | **RETRIG** (0.5.1): the track starts again from its first step on its next step (blinking until then) |
| 12 | **KILL** (0.5.1) while held (SHIFT: latched); its notes stop at once |
| 13-16 | where the track's playhead is (four positions); tap: select the track |

### TRACK (the selected track)

| row | pads |
|---|---|
| 1 | the 16 tools: CLEAR, REVERSE, SHIFT <, SHIFT >, RANDOM (0.27: a roll of the dice), **EUCLID LIVE on / off**, **WRITE LIVE**, UNDO, COOK (0.11: towards the next variation; **SHIFT: the random COOK**), BEAT, PROG, COPY, PASTE, DOUBLE, INVERT, HUMANIZE, on the scope (their settings: BEAT view) |
| 2 | arp mode (13: BLOCK, UP, DOWN, UP-DN, DN-UP, UP&DN, CONV, DIV, RND, WALK, PLAYED, THUMB, PINKY); octaves 1-3 (14-16) |
| 3 | swing 50 .. 75 % (1-8); direction FWD, REV, PING, RND (9-12); transpose -12, -1, +1, +12 (13-16; SHIFT: back to 0) |
| 4 | division 1/1 .. 1/32T (1-13); the track FREE / IN KEY (cyan) / DRUM (amber) / BREAK (0.12) (14; a TAPE: HOME 4 K1 on the FM-1); **0.25, the polyrhythms: five (15) or seven (16) steps in the time of four** - a tap: of the value the track had (four quarters from 1/4, four eighths from 1/8, else four 16ths); again: the next of the three; violet, white the one that is on; a pad 1-13 goes back to a plain step. (Mute and solo: the PERF view) |
| 5 | length 4, 8 .. 64 (0.11: playing, at the bar - 0.25: the metre's bar, GLO 4 on the FM-1 -; **0.24**: a longer track has the pattern go round again in its new steps - the copies, whatever lengths came before - and a shorter one keeps the pattern whole after the loop). SHIFT: the loop start 1, 5 .. 61 |
| 6 | humanise: timing 0 .. 50 % (1-8), velocity 0 .. 50 (9-16) |
| 7 | velocity offset -63 .. +63 (the middle pad: 0) |
| 8 | nudge of the cursor step -50 .. +50 % (left of the middle: early) |

### CC (the CC lanes of the selected track; SHIFT + STEP)

| row | pads |
|---|---|
| 1-4 | a bar per step of the page: the value the selected lane locks on that step (top row 127, then 80, 48, 16). Tap a level: lock it (the step is switched on). Tap the top of a bar again: no lock |
| 5 | lane 1-8 (pads 1-8; 0.28: eight lanes, six until 0.27); page of steps 1-4 (pads 9-12); clear the lane in the whole pattern (16) |
| 6 | the lane's CC number: 1, 5, 7, 10, 11, 12, 13, 64, 71, 72, 73, 74, 75, 91, 93, 94. **SHIFT + any: LEARN** (move a knob of the synth; the row blinks while it waits) |
| 7 | the lane's base value 0 .. 127 (where it goes back after a lock) |
| 8 | lane off (1); no base value (2) |

### FOLLOW (CC again; PICK in 0.12-0.17): the grid goes with the FM-1

**FOLLOW** (0.18): from SHIFT + STEP twice on, the grid's view **goes with the FM-1's page** - a quarter of a second
after the page changes (a button tapped in passing moves nothing):

| the FM-1 | the grid |
|---|---|
| the steps (no group held, no window) | STEP |
| PERF (GLO tapped, or held) | PERF; on page 3 (the MOSSE): VIAGGIO |
| LFO held or its window | LFO |
| FX held or its window | FX |
| ENV held or its window | CC (the lanes) |
| EDIT held or its window | STEP |
| HOME, SEQ, ARP held or their window | this view: the four knobs of the page |
| SAVE held | the view stays |

The grid is always on the FM-1's track (the tablet has a track of its own: SAGGA-SEQ.md, channel 12). A view chosen
by hand with a button stops FOLLOW; SHIFT + STEP twice: it follows again. While it follows, **SHIFT is cyan**; on this
view STEP is yellow.

The view: the four knobs of the page open on the FM-1 (a group held or the **window** a tap opened - HOME, SEQ, EDIT,
ENV, LFO, ARP; PERF's page when PERF is on; HOME's when nothing is), a knob a row, as the FM-1's PICK keys set them
(SAGGA-SEQ.md, PICK).

| row | pads |
|---|---|
| 1-4 | K1 .. K4: the white keys of PICK. A list or a count: items 1-16; a length: 4, 8 .. 64; a root or a note: the keys from F3; semitones: F3 = -12 .. ; a percentage: 10 .. 100 % on pads 1-10. The pad of the value now is **white**; the valid pads green (K1), blue (K2), violet (K3), orange (K4); a knob the keys cannot set (a velocity, a CC value): a faint row |
| 5-8 | **0.18, a knob of the track: the same knob across the tracks** (0.28: twelve, pads 13-16 dark), pad 1 = track 1: the FM-1's track **white**, the tracks with its value lit (green, blue, violet, orange), the others faint. **A tap: that track gets the value** (the knob turned for it, so lengths wait for the bar, patterns for the QUANTISE, and the screen says `T3 LENGTH AS T1`); **SHIFT + a tap: the FM-1 goes to that track**. A knob that is no track's (the key, the energy, the genre, the morph, the LFOs, a step's notes), and the track's MIDI channel and a scene's PROGRAM (a synth's: never copied by a tap): the black keys 1-10 of PICK there, as in 0.12-0.17 (pads 1-10; items 17-26, the odd lengths 3 5 6 7 9 10 11 13 14 15, the sharps) |

The knobs across the tracks: HOME 1 LENGTH, DIVISION, TRANSPOSE; HOME 2 all four; HOME 4 all four; HOME 5 the note,
velocity and gate lengths; HOME 6 (MIDI FX), HOME 7; PERF 2 PATTERN and LENGTH; SEQ 1 PULSES, ROTATION, FAMILY; SEQ 4
and 5 (EXPO); SEQ 7 and 8 (the BREAK); ARP 1 and 2 all four; ARP 3 FOLLOW; ARP 4 FOLLOW's way; ENV the lane's CC and its
mode.

A pad sets the knob (the knob is turned by the difference, so its messages and the bar line it waits for are the
same) and puts it in focus for the FM-1's keys. Turn the window's pages on the FM-1 (OCT- / OCT+). SHIFT + STEP once
more: CC again (and FOLLOW stops).

### LFO (SHIFT + PERF)

| row | pads |
|---|---|
| 1 | the 16 LFOs: tap one to select it, tap the selected one to switch it on / off (green: on) |
| 2 | shape: sine, triangle, ramp up, ramp down, square, S&H, smooth random, decay (1-8); destination: CC, velocity, gate, chance, timing, swing (9-14); retrigger (15); invert (16) |
| 3 | rate: 16 bars .. 1/32 |
| 4 | depth |
| 5 | centre |
| 6 | phase |
| 7 | target: MIDI channel 1-14 (1-16 with two USB ports) for a CC LFO, else track 1-12 |
| 8 | CC number (the same 16 as the CC view). **SHIFT + any: LEARN** |

### BEAT (SHIFT + TRACK): the library, the generators, the dice, EVOLVE (0.8)

| row | pads |
|---|---|
| 1 | genre 1-12. **0.29**: page 1: techno, hard techno, dub techno, house, UK garage, UK funky, dubstep, jungle, reggaeton, batida, gqom, experimental; page 2: electro, drum+bass, balani, footwork, trance, UK drill, hardcore, phonk, baile funk, merengue (22 genres: grime, bassline, afro house and amapiano went into others; until 0.28 25, on three pages); **PAGE** (13: blue page 1, cyan page 2); **LOAD** (14: BEAT on the scope; again: the next variation); **KIT** (15; SHIFT: **BAND**); **DICE ALL** (16) |
| 2 | the genre's **parts** (0.11: its band, violet, then PROG and KIT; more than nine: pads 1-8 a page, pad 9 the next page); **scope**: this track, bank, all, drums, melodic, CUSTOM (10-15); **WRITE LIVE** (16, orange while the track has a live layer) |
| 3 | the genre's **progressions** 1-6 (cyan: playing; 0.29: 7 and 8 are on the VIAGGIO view and SEQ 4 K2); **HARMONY** on / off (7); bars a chord (8: the progression's own, 1, 2, 4, 8); **FOLLOW** this track (9); **variations 1-6 / 7-12** (10: the page; 11-16). **0.23, SOURCE THEORY or FREE** (SEQ 8 K1): the **seeds** in their place - 11-16 six seeds (white: the next one), 10 the six after them; SHIFT shows on rows 5-6 what the engines would make of the seed |
| 4 | **DICE** SEQ, CC, LFO, GROOVE, ALL (1-5); **KEEP** (6); **BACK** (7); targets RHYTHM, +NOTES, +CC, +NOTES+CC, +CC+LFO, ALL (9-14); **the roll before / after** (15 / 16, yellow when there is one) |
| 5 | **EUCLID pulses** 1 .. 16 of this track, heard at once if EUCLID LIVE is on (cyan: live; 0.16: off, set up for EUCLID LIVE to start it); with scope CUSTOM, track membership 1-12. **SHIFT: rows 5-6 show the pattern LOAD would bring** |
| 6 | EUCLID rotation 0 .. 15 |
| 7 | random density 10 .. 90 % (1-8); heat 5 .. 90 % (9-16) |
| 8 | **EVOLVE** on / off (1); **FREEZE** (2); **REVERT** (3); DRIFT (4; 0.27: EVOLVE's RETURN at 0, and back); every 1, 2, 4, 8, 16 bars (5-9); amount 5 .. 80 % (10-16) |

### EUCLID (BEAT again, 0.8): the eight tracks of the bank (0.28: bank 2, four rows)

| pads | |
|---|---|
| 1 of a row | EUCLID LIVE of that track on / off (red: live and heard, dim red: live but muted) |
| 2-16 | pulses 1-15, heard at once if the row is live (0.16: off, they set it up, READY: pad 1 starts it); **SHIFT**: the rotation 0-14 |

Eight tracks of Euclidean rhythms, each its own, played over what is written. WRITE LIVE (TRACK row 1 pad 7, BEAT row
2 pad 16, SEQ + white 7) puts them into the patterns.

### SONG (PERF again)

| row | pads |
|---|---|
| 1 | 16 entries of the song (0.9: of 64, the page of the one chosen): tap one to edit it (the one after the last: a new one). SHIFT + tap: the song jumps there |
| 2 | the scene of the entry, 1-16 (on the new one: it is added, for 4 bars) |
| 3 | its length: 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 16, 20, 24, 32, 48, 64 bars |
| 4 | SONG on / off (1); LOOP (2); INSERT a copy after it (3); DELETE it (4); the entries' page back / forward (13 / 14); SHIFT + 16: clear the song |
| 5-8 | the song bar by bar (64 bars), a colour per entry, red the bar playing; tap: the song jumps to that entry |

The song starts with PLAY from its first entry, and changes scene on the bar line. Turned on while playing, it
starts on the next bar.

### VIAGGIO (SONG again, 0.9): the journey

The journey always runs (0.17: this view switches nothing on; until 0.16 a tap switched VIAGGIO on). See "The journey
and the MOSSE" in SAGGA-SEQ.md for what the moves do; on the FM-1 they are PERF's page 3 (SEL + GLO).

| row | pads |
|---|---|
| 1 | the bars of the phrase (red: playing, lit: past, the last one in the FILL colour when a fill waits); any pad: **NOW** (stopped: the queue at once) |
| 2 | the 12 tracks: faint EMPTY, dim PROPOSED, lit IN, muted OUT; the selected one amber; red: LOOP records on it. **Tap**: a proposal (on an IN track nothing changes); **hold**: the dice; **SHIFT + tap** (0.10): the track's next **role** (KICK SNARE HAT PERC BASS CHORD ARP, or none: by its note) — the proposals follow it |
| 3 | the queue: a track with a move waiting is lit; **tap**: IN / OUT at the boundary (the remote's CC 32) |
| 4 | the moves 1-11 (FILL BREAK RISER DROP HALF DOUBLE THIN SWELL SWAP LOOP NOW; SHIFT: BREAK all / LOOP 4 bars; **0.24: SHIFT + HALF = SHORTER, SHIFT + DOUBLE = LONGER: every track's length half / twice**, at the phrase's end, stopped at once); 15 **INDIETRO**; 16 **cancel** the last |
| 5 | the energy 0-100 (the bar: what sounds; the target in the waiting colour while it glides) |
| 6 | the patterns of the selected track: the one playing red, the proposals lit; tap one: SWAP (IN track) or IN at the boundary; 16: the dice |
| 7 | the progressions: **0.29**: 1-8 the genre's, 9-12 yours (violet; ARP 5 writes them), 13 DICE/PI, queued (0.17: with the HARMONY off, READY); 14-16 the chord playing, in turn (white: the progression's first). Until 0.28: 1-6 the genre's, 7-10 yours |
| 8 | the trail: 16 = this phrase, 15 = one back ... (queues INDIETRO that far) |

### REGIA (VIAGGIO again, 0.9; only when a regista on the Pi has spoken)

| row | pads |
|---|---|
| 1 | the 16 rules of the regista: off, lit (on), red (passing) as the Pi says (SysEx 54). Tap: SysEx 55 to the Pi; the LED flips at once until the Pi answers |

### FX (SHIFT + UNDO): live

| row | pads |
|---|---|
| 1 | the 16 effects, **while held** (SHIFT + pad: latched, until SHIFT + pad again): FILL, stutter 2 / 4 / 8, half time, double time, reverse, freeze, random, octave up, octave down, fifth, max velocity, staccato (40 % of each note or ratchet), legato, kill all |
| 2 | **LOOP / REPEAT**: 1/32, 1/16, 1/8, 1/4, 1/2, 1 bar, 2 bars, 4 bars (1-8), 1/32T, 1/16T, 1/8T, 1/4T (9-12); **ECHO on every track** (14, 0.8); **EXIT** (16). **A tap: a LOOP that stays** (the same pad again: off; another pad: that length). **Held: REPEAT**, and when you let go every track is where it would have been. The tracks of row 4 |
| 3 | **TRANSPOSE** the key -7 .. +8 semitones (pad 8 = 0): the tracks that follow the key, at the QUANTISE moment |
| 4 | which tracks LOOP and REPEAT take, 1-12 (none lit: all) |
| 5 | **MORPH**: from the scene playing (1) to MORPH TO (16) |
| 6 | **kill** track 1-12 while held (SHIFT: latched); its notes stop at once, long ones too |
| 7 | **MORPH TO** scene 1-8 (1-8); **QUANTISE** AUTO, NOW, BEAT, BAR, 2, 4, 8 BARS (9-15); **MUTE QUEUE** (16) |
| 8 | **TEMP** (1, held; SHIFT: latched); **RELOAD** (2); **RESTART** (3); **STOP at the end of the bar** (4); **SNAPSHOT 1-8** (5-12: tap recalls at the QUANTISE moment, SHIFT + tap stores; green the one playing, blinking the one waiting); **CC CAPTURE** (13); **SEND** the snapshot's sound (14); **PATCHES** (15, the Pi); PANIC (16) |

### PROJ (SHIFT + REC): the key, the slots, the tempo, the song

| row | pads |
|---|---|
| 1 | root C .. B (1-12) |
| 2 | scale: chromatic (key off), major, minor, dorian, phrygian, lydian, mixolydian, locrian, harmonic minor, melodic minor, major pentatonic, minor pentatonic, blues, whole tone, phrygian dominant, hirajoshi; **0.29, SHIFT + pads 1-5**: hungarian minor, double harmonic, lydian dominant, major blues, in sen |
| 3 | shift -24, -12, -7, -5, -3, -2, -1, 0, +1, +2, +3, +5, +7, +12, +24 semitones |
| 4 | the mode of track 1-12: FREE, IN KEY (cyan), DRUM (amber), a tap moves to the next |
| 5 | **the MASTER knob: TEMPO, MORPH, FILTER (1-3)**; **the remote: OFF, CH 14, 13 + 14 (5; accent: 13 + 14)**; BAKE the key into the patterns, press twice (14); all tracks but the drum tracks follow the key (15); none (16) |
| 6 | slot 1-8 (1-8); SAVE, press twice (9); LOAD, press twice (10); **EXPORT** the project to the Pi (12) |
| 7 | tempo -10, -1, +1, +10 (1-4); **TAP** tempo (5); REC quantised / free (6); master / slave clock (7); unmute all (9) |
| 8 | jump to bar 1-16: playing, the tracks go there at once; stopped, SHIFT + PLAY then continues from there. As the master it sends the Song Position |

### TRACK 2 (TRACK again, 0.5): the loops of the parameters, the programs

| row | pads |
|---|---|
| 1 | the loop of the **notes**: 1-16 steps (SHIFT: 17-32; longer: HOME page 4); the length it has, again: back to the track's loop |
| 2 | the loop of the **velocities** |
| 3 | the loop of the **gates** |
| 4 | the **Program Change** of the track's channel in the scene of row 5: 1-16 (SHIFT: 17-32; the rest: HOME page 4); again: none. Sent at once |
| 5 | which scene's program row 4 sets, 1-8; 16: send that scene's programs now |
| 6-8 | the three loops: red the step they play, dim how long they are (dark: they follow the track) |

The colour of a bar is its page: green 1-16, cyan 17-32, blue 33-48, violet 49-64.

### TRACK 3 (TRACK 2 again, 0.8): the selected track's chords, MIDI FX, algorithm

| row | pads |
|---|---|
| 1 | voicing CLOSE, INV 1, INV 2, DROP 2, OPEN (1-5); strum -50 .. +50 % (6-16, pad 11 = 0; minus: from the top) |
| 2 | MIDI FX OFF, HARM, OCTAVE, ECHO, VEL CURVE (1-5; 0.16: a tap READY, orange; again: it starts, white; on the one playing: it stops; each with the values it had on the track; 0.19: they play together, in a chain - every one that plays is white; OFF tapped twice: all stop; **0.20: SHIFT + pads 2-6: CHANCE, RANDOM, NOTE FILTER, GATE, GLITCH**; **0.29: SHIFT + pads 7, 8: ROLL, ACCENT**); amount -5 .. +5 (6-16, pad 11 = 0) of the one shown (0.20, a new one: its K2 from its lowest to its highest over pads 6-16) |
| 3 | ECHO time 1/32 .. 1/4 (1-8; OCTAVE: ALT, RANDOM, 3RD, 4TH); how much each ECHO keeps / the HARM voice's velocity 20 .. 100 % (9-16); 0.20, a new effect: its K3 on 1-8 and its K4 on 9-16, each over its range (a short range: a value a pad) |
| 4 | algorithm OFF, TURING, CELL, ACCENT, DENSITY (1-5) of the slot shown (**0.16: a tap READY, orange; again: it starts with what rows 5-6 set, white; a tap on the one playing stops it**); FOLLOW (6); EUCLID LIVE (7); **the slot 1-4** (8, 0.11: tap for the next); C (9-16): TURING rhythm / notes / both, CELL every 1 / 2 / 4 bars / loop, ACCENT offset |
| 5 | A: TURING mutation, CELL rule, ACCENT style, DENSITY (16 levels, 0 .. 200 %) — of the READY algorithm if there is one, else of the one playing. **0.23.1, the sixteen CELL rules from the calm to the wild**: 204 (the row stays as it is: a tap while a CELL plays holds the row of that bar), 170 (it slides a step earlier every row), 240 (a step later), 184 (it slides, hits in a row open up), 51 (hits and rests swap), 90, 150, 105, 60 (loops of a few rows through the written rhythm), 54 (thin and thick in turn), 18, 22, 126, 122, 110 (longer stories), 30 (no loop in sight). A tap says on the FM-1's screen what that rule makes of the track's rhythm (`T1 CELL RULE 90: A LOOP OF 8 ROWS`); so does a pad of row 6 on a CELL |
| 6 | B: TURING length 2-16 (pads 1-15; **0.25, pad 16: TRACK** - as long as the track, and it follows it), CELL cells, ACCENT amount, DENSITY the ghosts' velocity |
| 7 | the cursor step's long gate: 1.5, 2 .. 6, 8 .. 16, 20 .. 64 steps — a whole four-bar pattern (SHIFT: 17 .. 32 one by one) |
| 8 | the MIDI channel 1-16 (15 and 16 need two USB ports) |

### LIB (PROJ again, 0.5): the files on the Pi

| row | pads |
|---|---|
| 1-4 | the files, 64 at most, in the order of their names: tap one to choose it (the screen shows its name), tap it again to LOAD it. While playing it loads when you press STOP (blinking until then) |
| 8 | PREVIOUS (1), NEXT (2): the file before / after the one loaded (a setlist); REFRESH the list (4); SAVE AS A NEW FILE (8); SAVE OVER the chosen file (9, twice); LOAD the chosen one (16) |

Lit: green the file loaded, amber the one chosen. A project loaded from the Pi is not in a slot: SAVE on the FM-1
keeps it there too; RELOAD works from it while nothing else has used the FM-1's buffer (a save, an export).

## 4. Troubleshooting

* *"found 0 (or 1) Launchpad(s), need 2".* `--list` shows what the Pi sees. The default looks for ports with
  `Launchpad Mini` in the name; name them yourself with `--left` / `--right` (a regex, e.g. `20:` for ALSA client
  20). `--model mini` and `--model mk2` look for `Launchpad`.
* *The pads light in the wrong places, or not at all, on red / green Minis.* You are running the MK3 driver: add
  `--model mini` (also in the service file).
* *The FM-1 shows `G:STEP` (or another view) on its last line, but the pads are dark, or the colours are wrong.* The bridge reaches
  the FM-1 but not the right Launchpad port: read the `left Launchpad: in ... out ...` lines it prints. It should
  name the `MIDI` port, not the `DAW` one. Pick the port with `--left` / `--right`, and run `--identify`.
* *The two halves are exchanged.* `--swap`.
* *Pads act twice.* The bridge opens one port per Launchpad, so this should not happen. If it does, the Launchpad is
  reachable under two names (for example a hub connection, section 1.2): remove the extra one.
* *"GRID LOST" after a few seconds.* The FM-1 stopped hearing the keep-alive: the bridge is stuck, or something
  blocks channel 16 on the way to the FM-1.
* *A synth plays notes while the grid runs.* The hub forwards channel 16 to it: block channels 15 and 16 on that
  connection (section 1.2).
* *Pad presses play notes, or the Launchpad lights by itself.* A Launchpad has a connection in the hub's matrix:
  remove it (section 1.2).
* *The bridge stops with "bridge stopped: ...".* A cable was pulled, or a Launchpad restarted. ALSA gives a program
  no error when the port it writes to disappears, so the bridge looks once a second whether the clients of the
  Launchpads and the FM-1 are still there (it reads `/proc/asound/seq/clients`: asking for the port list would
  create an ALSA client each time, and RaspiMIDIHub takes its whole matrix down and up again whenever a client comes
  or goes). If one is gone it ends with an error, and as a service it comes back by itself after two seconds and
  finds the new ports; by hand, start it again. Without that file (not Linux) there is no such check.
  **0.23.2**: it also looks whether its own connections are still there ("the bridge's connection ... is gone: the
  device was made again"): an FM-1 that restarts is back in half a second under the same number and name, and the
  bridge used to stay there connected to nothing, the grid dead.
* *The bridge says "no FM-1 ... the bridge waits for it"* (0.23.2). The FM-1 is off or not plugged in: the bridge
  waits, without looking at the ports again until a device comes (it used to end, and the service started it again
  every two seconds - each start disturbed RaspiMIDIHub's matrix). The same without two Launchpads ("no grid ...").
* *While a firmware is being installed* (0.25). The FM-1 in update mode is another device, "Felucca Update". Until
  0.24 the bridge (and the keeper of the pages' cells) took it for the FM-1: it attached to it and sent it its
  keep-alive every second through the install. Now the update loader is not the FM-1: the bridge says "no FM-1 ... the
  bridge waits for it" and comes back when the FM-1 restarts with the new firmware.
* *The Launchpads are dark and the FM-1 said GRID LOST* (0.23.2). The bridge was stopped: the Pi's banco stops it for
  a prova and starts it again at the end, and so does a shutdown. A stopped bridge switches the lights off (until
  0.23.1 the grid stayed lit and still, as if it were alive).
* *The LED colours.* Edit `ROLE_RGB` in the bridge (0..127 per channel).
* *"could not save the FM-1's project".* The dump folder is not writable: the bridge runs as a user who cannot
  write to `/boot/firmware`, or the folder is on the read-only root. Give `--dump-dir` a writable folder.
* *`--import` says busy.* Stop the FM-1 first (and let a save finish).
