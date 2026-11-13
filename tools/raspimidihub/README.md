# SAGGA Remote, Mutes, Motori, Break, Mod: five RaspiMIDIHub plugins for SAGGA SEQ 0.12 / 0.13

Five pages of the hub's web interface (open them full screen on the phone or a tablet) that send SAGGA SEQ's commands
to the FM-1 as Control Changes on MIDI channels 14 and 13 (the map: docs/SAGGA-SEQ.md, "SAGGA REMOTE" and "channel 13").
Channel 13 needs **SAVE K2 = REMOTE 13 + 14** on the FM-1 (the default of the PALCO profile; the 0.12 pages all use it).

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
  0.13: RATE goes on to the triplets (1/4T, 1/8T, 1/16T, 1/32T), as the FM-1's LFO RATE does.

To update from an older SAGGA: copy the folders again (the same commands as below) and restart the hub; the plugins
keep their place in the matrix.

## Install (on the Pi, over SSH)

`install_hub.sh` (the sagga-hub zip, 0.12) copies the five folders into RaspiMIDIHub's plugins folder and restarts the hub
when the hub is on the same Pi; then only the matrix step below remains. By hand, copy the five folders to the Pi (from the
PC, in the folder where they are):

    scp -r sagga_remote sagga_mutes sagga_motori sagga_break sagga_mod user@PI-ADDRESS:/tmp/

Then on the Pi:

    rw
    sudo cp -r /tmp/sagga_remote /tmp/sagga_mutes /tmp/sagga_motori /tmp/sagga_break /tmp/sagga_mod /usr/lib/python3/dist-packages/raspimidihub/plugins/
    sudo systemctl restart raspimidihub
    ro

In the web interface: add the plugins (they are with the controllers), connect each one's OUT to the FM-1 in the
matrix (with USB PORTS 2 on the FM-1: to its port 2, "Felucca MIDI 2"), Save Config. Nothing else needs them. If an
update of RaspiMIDIHub ever removes them, copy them again.

They are written against RaspiMIDIHub 6.0's ControllerBase (the base of its Controller Mixer / FX / Performance
pages). tests/sagga_plugin_tests.py checks them with a stand-in of the hub's API (every cell a command the FM-1
answers, the grids, the presses), and with the hub's own plugin host and test harness when RMH= points at a checkout
of RaspiMIDIHub; not yet on a Pi.
