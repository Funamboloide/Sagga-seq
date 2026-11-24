# SAGGA SEQ 0.32.1

(The Pi's side - the hub's page, the banco, the grid's bridge - is 0.32.3; the FM-1's firmware is 0.32.1; 0.32.4 and
0.32.5 change only the live effects: FIGO on norns (0.32.4), and on the Gills VARIAZIONI, FIGO and SCENA in one object,
alone or beside Microcosm or Chroma Console (0.32.5).)

![SAGGA SEQ on the FM-1's screen](docs/screen.png)

SAGGA SEQ turns the M-VAVE FM-1 into a MIDI-only performance sequencer: 12 tracks on 16 MIDI channels (0.28: chords of
six notes a step, eight CC lanes a track), 8 patterns of up to 64 steps per track (0.24: the length is the track's - a pattern goes round again in a longer track, a length changed while it plays lands on the bar line), a bar in any metre and tracks in five or seven against four (0.25: 7/8, 5/4, 15/16 ...; the polyrhythms' steps played between the clock's ticks; 0.26: the engines make a part IN that bar, a click on its beats, the scenes bring their metre; 0.27: the profile SEMPLICE hides the lab's pages), 32 scenes, 16 snapshots, a song of 128 entries (0.30), the tracks in four groups - drums, bass, melodic, all - on the keys and pads that were tracks 13-16 (0.31), every key and pad with a job (0.32: a step's force and place, the lanes' ramps and tools, the LFOs copied, the Pi's setlist on the panel, the MASTER knob on the ENERGY), 16 LFOs, 16 keys, a library of 22 genres (0.29: BALANI is new, four went into others; a band of 8 to 11 parts each, 12
variations a part in order of likeness, notes of their own length), the THEORY engines (0.23: a band MADE from the rules
of a genre and a seed, in all 22 genres and in none, that the ENERGY fills and empties), live Euclidean rhythms and four algorithm slots per
track, a harmony that the tracks follow (the genre's progressions or yours, on any root, with lengths in 16ths, pushes,
the genres' harmonic rhythms and ten moods; more of them, and more variations, kept by the Pi), chords and arpeggios from one note, eleven MIDI effects in a chain on every track, in the order you choose (velocity curve, octave, harmony, echo, chance, random, note filter, gate, glitch; 0.29: roll, accent), envelopes and a MOD MATRIX, eight CC lanes with slides and NRPN, tools that wait for the bar or repeat
every so many, TAPE tracks and EXPO curves, the journey (every set cut into phrases; the MOSSE, PERF's third page,
queue moves for the phrase, the bar or the beat, and what you played becomes a song), BREAK tracks (a drum break in slices, sixteen chops on the white keys, re-ordered live),
TAKE and THROWS, every knob also set from the keys (PICK, from the grid too), the buttons' pages as windows a tap
opens (no button to hold), and a 16 x 8 grid made of two Launchpads through a Raspberry Pi that follows the FM-1's page,
with six controller pages for the Pi's RaspiMIDIHub (and a BeatStep Pro as knobs and pads): the tablet works on a track
of its own, and the FM-1 sends its values back to it.

**MIDI only.** SAGGA SEQ makes no sound: the FM-1's speaker and headphone output stay silent. It plays your synths
over USB MIDI (and listens on the TRS input). It cannot read the projects or samples of other FM-1 firmwares.

## Install

* **In the browser:** [The Firmware Hub](https://thefirmwarehub.com) (Chrome or Edge, FM-1 on USB): one click, and one
  click back to the official firmware or any other.
* **From the Pi:** the hub's page (port 8090), FIRMWARE: upload `sagga-X.fwsc`, Installa. The whole set (the FM-1, the
  Pi, the grid), the first time and every update: [docs/INSTALLA.md](docs/INSTALLA.md) (Italian).
* **From a computer:** download `sagga-X.fwsc` (the `pacchetti` branch has the newest) and run
  `python3 tools/fm1_install.py sagga-X.fwsc` (Python 3 and `mido` + `python-rtmidi`).
* To leave SAGGA SEQ, install another firmware the same way. If anything goes wrong, hold **OCT-** while switching
  the FM-1 on: the USB rescue always takes a new firmware.

The package identity is `FM-1_9` + (50 + the minor version): 0.9 is `FM-1_959`, 0.10 is `FM-1_960`, 0.11 is `FM-1_961`, 0.12 is `FM-1_962` ... 0.18 and 0.18.1 are `FM-1_968`, 0.19 is `FM-1_969`, 0.20 is `FM-1_970`, 0.21 is `FM-1_971`, 0.22 is `FM-1_972`, 0.23, 0.23.1 and 0.23.2 are `FM-1_973`, 0.24 is `FM-1_974`, 0.25 is `FM-1_975`, 0.26 is `FM-1_976`, 0.27 is `FM-1_977`, 0.28 and 0.28.1 are `FM-1_978`, 0.29 is `FM-1_979`, 0.30 is `FM-1_980`, 0.31 is `FM-1_981`, 0.32 and 0.32.1 are `FM-1_982`.

## Docs

* [docs/SAGGA-SEQ.md](docs/SAGGA-SEQ.md): the reference (every control, the SysEx, the remote's CCs).
* [docs/SAGGA-GRID.md](docs/SAGGA-GRID.md): the grid, the bridge on the Pi, the snapshot patches.
* [docs/INSTALLA.md](docs/INSTALLA.md): install and update the three parts, the FM-1, the Pi and the grid (Italian).
* [RELEASE-NOTES-0.32.5.md](RELEASE-NOTES-0.32.5.md): what changed in this version (Italian) - **only the Gills; the FM-1 stays 0.32.1, the Pi 0.32.3, FIGO on norns 0.2**: VARIAZIONI, FIGO rewritten in C++ for the Gills (the same machine as on norns, sample by sample) and SCENA in one object, alone (tools/gills/figo_scena.axp, figo_scena_aux.axp) or beside Microcosm or Chroma Console on a bus (tools/gills/microcosm_figo_scena.axp, chroma_console_figo_scena.axp, made by tools/gills/make_bus.py from the effect patches in tools/gills/effetti; the norns versions of those effects, with Caramello, are in tools/norns/effetti): two pages (the encoder held a second alone and let go), pick-up on every knob, MIDI CC 110-119 from any page to launch the variations over the effect, the code that does not run every sample in the board's second RAM; three errors found by the new checks put right before release (a click when a change came during a crossfade, the stopped tape back for a moment after TAPE STOP, INDIETRO off the beat when the tempo moved); SCENA's first repeat no longer clicks, and its aux patch starts ROLL and FREEZE a round trip early. [docs/storia/RELEASE-NOTES-0.32.4.md](docs/storia/RELEASE-NOTES-0.32.4.md): only FIGO and SCENA, the live effects: FIGO reads the tape half a ms behind the head instead of 8 (softcut writes a block before it reads it), and on a bus (routing aux) it plays no dry and starts what it plays a round trip early, so its repeats land on the grid of the dry at the mixer; SCENA has an aux patch that never plays the dry (a copy a ms or two late combs it on a bus); three old errors of FIGO's put right (the rising ROLL and the double-speed MEMORIA got past the record head; a START in the middle of an event held it open). [docs/storia/RELEASE-NOTES-0.32.3.md](docs/storia/RELEASE-NOTES-0.32.3.md): the Pi's side only: DA ABLETON, the MIDI clips exported from Ableton made a project of steps on the hub's page (tools/hub/sagga_ableton.py), each part on the channel of the machine that plays it - the swing kept in the steps' nudge, rolls as ratchets, ties, the copies of a short pattern, CHAIN for 8 bars, TAPE for 16; the comparison of the bench's logs reads a probe taken a ms before a clock tick as timing. [docs/storia/RELEASE-NOTES-0.32.2.md](docs/storia/RELEASE-NOTES-0.32.2.md): 0.32.1 on a real FM-1 (the bench's 71 sessions: the FM-1 is the simulator in every one), and what those logs showed of the Pi - the grid's bridge that did not end when the banco stopped it (python-rtmidi locks up closing an input as a message comes in: the bridge now says its goodbye and is gone, no port closed; Controlla la matrice starts a bridge that is down), the banco's question that SAVED ON THE PI covered on the FM-1's screen, a project more in the library at every prova. [docs/storia/](docs/storia/) keeps the notes of every version before (0.32.1: 0.32 on a real FM-1 (the bench's 69 sessions: the FM-1 is the simulator in every one), and everything since 0.27 read again - the tablet reaches the 32 scenes and the 16 snapshots (SAGGA Remote's SCENES and SNAPS), the grid's pads that change every track or every scene ask twice, the LFO's RESET asks for the LFO chosen, HOME's and GLO's key maps say their whites 13-16, the bench's comparison no longer calls timing an error; 0.32: the keys and pads that did nothing since before).
* [docs/MAPPA-GENERATORI.md](docs/MAPPA-GENERATORI.md): the map of the generators (Italian) - who makes a pattern, who changes it, who moves it while it plays; where two ways do the same thing; what was joined and hidden in 0.27 (RANDOM a roll of the dice, DRIFT inside EVOLVE, who is acting, the profile SEMPLICE).
* [docs/TEORIA.md](docs/TEORIA.md): the THEORY engines - what each does, why, which instrument it is like - and
  [docs/TEORIA-GENERI.md](docs/TEORIA-GENERI.md): the rules of 16 genres, counted from the library (Italian).
* [docs/SAGGA-ESPLORATORE.md](docs/SAGGA-ESPLORATORE.md): the explorer, on a computer, on the FM-1 and on the banco (Italian).
* [tools/hub/LEGGIMI.md](tools/hub/LEGGIMI.md): the Pi's page - the firmware library, the projects and their editor, the
  update, the keeper of the FM-1's cells, the banco (Italian). [tools/raspimidihub/README.md](tools/raspimidihub/README.md): the
  seven plugins.
* [docs/storia/](docs/storia/): the past - what each version brought ([NOVITA.md](docs/storia/NOVITA.md)), the release
  notes of 0.8 to 0.22, the installation sheets of their time, the design 0.12 started from.
* [docs/SAGGA-GRID-ZYNTHIAN.md](docs/SAGGA-GRID-ZYNTHIAN.md): the minimal stage set-up, the bridge on a Zynthian (Italian).
* [tools/norns/figo/README.md](tools/norns/figo/README.md) and [tools/gills/LEGGIMI.md](tools/gills/LEGGIMI.md): the live
  effects of the set, FIGO on norns (the loop varied by itself, in time) and SCENA on the Ksoloti Gills (one knob from
  break-down to build-up), each in insert or on a mixer's send and return (Italian).
* [tools/m8link/LEGGIMI.md](tools/m8link/LEGGIMI.md): two headless M8s on TrimUI Bricks as MIDI instruments for the
  Pi (Italian).

## What runs where

| | |
| --- | --- |
| FM-1 | the firmware: `firmware/` |
| Raspberry Pi with [RaspiMIDIHub](https://github.com/wamdam/raspimidihub) | the hub's page (`tools/hub/`: firmware, projects, editor, update, the keeper of the FM-1's cells, the banco), the grid bridge (`tools/sagga_grid_bridge.py`), the seven plugins (`tools/raspimidihub/`), the M8 link's Pi side (`tools/m8link/pi/`) |
| TrimUI Brick with KNULLI | the M8 link's Brick side (`tools/m8link/brick/`) |

Everything on the Pi and the Bricks is optional: the FM-1 alone is a complete sequencer.

## Build

```sh
./build.sh --release 0.32.1       # identity FM-1_982
```

Needs the JieLi toolchain and the AC79 SDK (`tools/get_toolchain.sh`; `build.sh` says what is missing). Install with
`tools/fm1_install.py`.

## Test (no FM-1 needed)

```sh
sh tests/run_sagga_tests.sh                 # core, the FM-1's two builds parsed, USB, bridge, plugins (RMH=...), hub, simulator, fuzz (ASan + UBSan), explorer, banco
SANITIZE=1 FUZZ=200 sh tests/run_sagga_tests.sh   # everything with the sanitizers, more random runs
python3 tests/sagga_explore.py              # the explorer, all of it: every gesture in 11 situations, pairs, sessions
```

The explorer ([docs/SAGGA-ESPLORATORE.md](docs/SAGGA-ESPLORATORE.md), Italian) tries every gesture of the panel and the
grid from 11 starting situations, then pairs and long random sessions, and checks rules (browsing never changes the
harmony, nobody but HOME 1 K1 changes a channel, every track in time two bars later, no hung notes ...); it writes
what each gesture changes and how to repeat a broken rule.

## Project format

0.11 and later write `SGQB` (0.12 uses two of a track's reserved bytes for its BREAK settings; what 0.13 - 0.20 added lives in a tagged chunk an older firmware skips) and read 0.10's `SGQA` too (a 0.10 project opens with the new things off); SGQ3 .. SGQ9 slots and
files are refused (keep a 0.9 firmware for 0.9 projects). The format carries the track settings (96 bytes a track: the
four algorithm slots, FOLLOW's way; 0.28 still writes sixteen of them, the last four empty, and puts the notes 5-6 and
the lanes 7-8 in a chunk of their own, so a 0.27 opens its projects), five user progressions (roots, shapes, lengths, pushes, moods), 16 scenes, a song of 64 entries with a tempo
each, the snapshots (sparse; 0.30: scenes 17-32, entries 65-128, snapshots 9-16 and the tapes past 1536 events in a chunk of their own, so a 0.29 opens its projects), the project's id (the Pi keeps the snapshot patches by it) and a tail of tagged chunks,
so a later version can add data without a new format.

## USB

One USB-MIDI port by default (the grid on channels 15 / 16, the tracks on 1-14). USB PORTS 2 (SAVE page 3,
K1; SEL + K1 twice reconnects) gives two: port 1 the synths with 16 channels, port 2 the grid, the remote and the SysEx.

## Credits and licence

GPL-3.0-only (`LICENSE`). SAGGA SEQ stands on [Felucca](https://github.com/hugelton/Felucca) (Leo Kuroshita,
Hügelton Instruments), [SLOOP](https://github.com/isod89/sloop-fm1) (isod89) and Dinghy (zvenson): who made what is in
[LICENSING.md](LICENSING.md).
