# SAGGA Remote, Mutes, Motori, Break, Mod, Live, BeatStep: seven RaspiMIDIHub plugins for SAGGA SEQ 0.12 - 0.20

Six pages of the hub's web interface (and, 0.20, SAGGA BeatStep: below) (open them full screen on the phone or a tablet) that send SAGGA SEQ's commands
to the FM-1 as Control Changes on MIDI channels 14, 13 and 12 (the map: docs/SAGGA-SEQ.md, "SAGGA REMOTE", "channel 13",
"channel 12"). Channels 13 and 12 need **SAVE K2 = REMOTE 13 + 14** on the FM-1 (the default of the PALCO profile; the
0.12 pages all use it).

**0.18: the tablet has a track of its own.** What the pages do on "the selected track" (the pads, the lanes, TAKE, the
LFO, MODE, the break) they do on the tablet's track, chosen with TRACK (SAGGA Live, Motori, Mod: channel 13 CC 112);
the FM-1 keeps its own track, page and cursor (its screen says `TAB T5: ...` when the tablet did something). **And the
FM-1 sends its values back** (USB PORTS 2: on its port 2): the knobs and switches of the pages move when the FM-1
changes them.

* **SAGGA Remote** (channel 14): PLAY / STOP, CONTINUE, STOP @BAR, RESTART; FILL, RELOAD, TEMP, PANIC; LOOP 1/4 1/8
  1/16 1/32 (a tap: the loop stays) and REP 1/4 .. 1/32 (on until pressed again: a REPEAT that lands in time when
  switched off); EXIT LOOP, UNDO, KEEP DICE, MUTE QUEUE; scene - / +, EVOLVE, FREEZE, scenes 1-8; MORPH (fader) and
  MORPH TO; the macros INTENSITY, GATE, SWING, FILTER (64 = 0); TRANSPOSE (0 in the middle), QUANTISE, EVOLVE amount,
  heat; tempo -1 / +1, TAP, REVERT; the snapshots; HARMONY, ECHO, WRITE LIVE; 0.12: **TAKE** (channel 13).
* **SAGGA Mutes** (channel 14): MUTE 1-16, KILL 1-16 (silent while on), RETRIG 1-16 (the track from its first step).
* **SAGGA Motori** (0.12): a row a track: MUTE, PATTERN 1-8 (at the QUANTISE moment), LENGTH 1-64 (at the bar), RETRIG,
  KILL; under them the selected TRACK and its MODE (FREE, IN KEY, DRUM, TAPE, BREAK), DICE, UNDO, KEEP DICE.
* **SAGGA Break** (0.12): sixteen slice pads (slice 1 bottom left), ROLL and ROLL/2 (held), HALF, DOUBLE, BACKWARDS,
  DICE, RESET, TAKE; the knobs CHOP (the library of sixteen re-orders, the FM-1's white keys), ROLLS, SWAP, SLICES (8 / 16
  / 32). The selected track must be a BREAK (HOME 4 K1 on the FM-1, or Motori's MODE): its PEN note is slice 1 on the sampler.
* **SAGGA Mod** (0.12): one LFO at a time (which, ON, SHAPE, RATE, DEPTH, DEST), the six CC lanes of the selected
  track (their base, sent as you move it), the four THROWS (the macros that spring back to 0 over a bar), VIAGGIO's
  ENERGY, GENRE, KEY, the harmony's PROGRESSION and state; under them **L1-L16, the sixteen LFOs on / off at once**
  (each a note on channel 13, 100 + the LFO; the hub shows a CC 0 binding on those cells: a placeholder the FM-1 ignores).
  0.13: RATE goes on to the triplets (1/4T, 1/8T, 1/16T, 1/32T), as the FM-1's LFO RATE does. 0.18: GENRE reaches
  MERENGUE (25 genres); the LFO knobs are the tablet's LFO; L1-L16 follow the FM-1.
* **SAGGA Live** (0.18, channel 12): the tablet's track, everything at hand while the FM-1 works on another - TRACK and
  MODE, MUTE, SOLO, PATTERN, LENGTH, OCTAVE, RETRIG; SWING, GROOVE, GROOVE AMT, FOLLOW; ARP, OCTAVES, RATE (1/4, 1/2:
  a note every 4 / 2 steps), RUN; CHORD; MIDI FX (READY), FX AMOUNT, FX GO (0.19: the effect shown joins the track's chain, again: it leaves); ALGO (READY), A, B, C, ALGO GO; PULSES,
  ROTATION, EUCLID; COOK, BEAT, PROPOSAL, QUEUE; DICE, KEEP, BACK, UNDO (on that track only); MUTE 1-16. The hub's PANIC
  leaves it alone (its switches are the FM-1's mutes).

To update from an older SAGGA: copy the folders again (the same commands as below) and restart the hub; the plugins
keep their place in the matrix.

## Install (on the Pi, over SSH)

`install_hub.sh` (the sagga-hub zip, 0.12) copies the folders (0.20: seven) into RaspiMIDIHub's plugins folder and restarts the hub
when the hub is on the same Pi; then only the matrix step below remains. By hand, copy the folders to the Pi (from the
PC, in the folder where they are):

    scp -r sagga_remote sagga_mutes sagga_motori sagga_break sagga_mod sagga_live sagga_bsp user@PI-ADDRESS:/tmp/

Then on the Pi:

    rw
    sudo cp -r /tmp/sagga_remote /tmp/sagga_mutes /tmp/sagga_motori /tmp/sagga_break /tmp/sagga_mod /tmp/sagga_live /tmp/sagga_bsp /usr/lib/python3/dist-packages/raspimidihub/plugins/
    sudo systemctl restart raspimidihub
    ro

In the web interface: add the plugins (they are with the controllers), connect each one's OUT to the FM-1 in the
matrix (with USB PORTS 2 on the FM-1: to its port 2, "Felucca MIDI 2"), **0.18: and the FM-1's port 2 to each one's
IN** (what the FM-1 sends back: the values; port 2 carries nothing for the synths), Save Config. Nothing else needs
them. If an update of RaspiMIDIHub ever removes them, copy them again.

**SAGGA BeatStep** (0.20, `sagga_bsp`): not a page but a plugin with an IN - an Arturia BeatStep Pro in CONTROL mode as
real knobs and pads. Wire the BeatStep Pro to its IN, its OUT to the FM-1's port 2. **LEARN**: turn the 16 encoders one
after the other (top row, then bottom), then tap the 16 pads; the hub keeps what it learned. The encoders are SAGGA
Live's knobs on the tablet's track (TRACK, PATTERN, LENGTH, OCTAVE, SWING, GROOVE, ARP, CHORD / MIDI FX, FX AMOUNT,
ALGO, A, B, C, PULSES, ROTATION; ABSOLUTE or RELATIVE), the pads the 16 MUTES or (PADS = ACTIONS) PLAY, FILL, FX GO,
ALGO GO, COOK, BEAT, DICE, UNDO, PROPOSAL, QUEUE, KEEP, BACK, RETRIG, MUTE, EUCLID, ECHO ALL. Its CV outputs are wired
apart: the FM-1's port 1 to the BeatStep Pro, channels 1, 2 and 10 (docs/SAGGA-SEQ.md, "What is new in 0.20").

**RaspiMIDIHub's own note plugins after the FM-1** (0.19: a chain of MIDI FX on the hub, beside the FM-1's own):
docs/SAGGA-SEQ.md, "A chain on the hub too" - only the track's notes into the chain (a filtered cell of the matrix),
its CCs and the clock straight to the synth, since the plugins come with CCs bound (MIDI Delay 74 / 75 / 76, Note
Transpose 74, Scale Remapper 74) and a bound CC does not pass.

They are written against RaspiMIDIHub 6.0's ControllerBase (the base of its Controller Mixer / FX / Performance
pages). tests/sagga_plugin_tests.py checks them with a stand-in of the hub's API (every cell a command the FM-1
answers, the grids, the presses), and with the hub's own plugin host and test harness when RMH= points at a checkout
of RaspiMIDIHub; not yet on a Pi.
