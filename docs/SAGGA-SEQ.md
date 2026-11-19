# SAGGA SEQ 0.28

A MIDI-only performance sequencer for the M-VAVE FM-1, built on Dinghy's platform. No synthesis: the FM-1 sends
notes, CCs and clock over USB to a hub (RaspiMIDIHub on a Raspberry Pi) that feeds the instruments. **Twelve
tracks** on sixteen MIDI channels, eight patterns of up to 64 steps per track (a step: up to **six notes**, **eight CC
lanes** a track), **sixteen scenes**, eight **snapshots**, a song of **64
entries**, sixteen LFOs, **sixteen keys**, eight project slots, a library of **25 genres** (patterns of 16, 32 and 64
steps), the **THEORY engines** that make a band from a seed in each of them, in the bar of its metre, a bar in **any
metre** and tracks in **five or seven against four**, a **click** with a count-in, the keyboard's chords as the harmony,
its pedal and wheels recorded, and **the journey**: every set is cut into phrases, the **MOSSE** (PERF's third page)
queue moves for the phrase's end (or the bar, or the beat), and what you played can become a song. With two Launchpads through the Pi it becomes a 16 x 8
grid sequencer ([SAGGA-GRID.md](SAGGA-GRID.md)); almost everything is also on the FM-1's own panel.

The screen says `SAGGA SEQ 0.28` for three seconds after power-on: that is how you know the update took.

This page is the reference: every control, every message. [MAPPA-GENERATORI.md](MAPPA-GENERATORI.md) (Italian) is the map of everything that makes or changes a pattern - which to use for what. The manual (Italian, a Claude Doc the author keeps) builds
a song step by step; [INSTALLA.md](INSTALLA.md) installs and updates the three parts (the FM-1, the Pi, the grid);
[storia/NOVITA.md](storia/NOVITA.md) is what each version brought, from 0.8 to 0.27.

## What is new in 0.28

**Twelve tracks** instead of sixteen, and with the memory they leave **chords of six notes** and **eight CC lanes** a
track. The projects of before open with their first twelve tracks; a 0.27 opens a project of 0.28, without what it
has no room for.

* **Twelve tracks.** The MIDI channels stay sixteen: a track can be on any of them. **HOME + white 1-12** picks a
  track, whites 13-16 do nothing for now. The black keys: 1-8 the tracks of the bank, 9 the other bank - the banks
  are **1-8 and 9-12** (in 9-12, blacks 5-8 do nothing). GLO + white 1-12: the mutes. DICE ALL rolls the eight
  tracks of the selected one's side: 1-8, or 5-12. On the grid the pads of tracks 13-16 are dark; the remote's
  commands for tracks 13-16 do nothing, and SAGGA Live, Motori, Mutes and BeatStep on the Pi show twelve.
* **Chords of six notes**: a step holds up to six notes (four until 0.27). SEL + keys takes up to six within 0.45 s
  (`CHORD FULL (6 NOTES)` past that); MIDI REC, the grid and the Pi's editor write six too. **EDIT + SEL + K1-K4**
  still set notes 1-4; the line says notes 5 and 6 when the step has them. The ARP, the strum and the voicing work on
  all six; at most six sound from a step, with a CHORD shape too.
* **Eight CC lanes** a track (six until 0.27): the ENV pages go `LANE 1/8` .. `LANE 8/8`; in a new project lane 7 is
  CC 73 (attack) and lane 8 CC 72 (release). The grid's CC view (pads 1-8), the CC learn (a ninth CC: `NO FREE LANE`),
  the scenes and the snapshots keep all eight. The remote's lane knobs (channel 13 CC 101-106) stay on lanes 1-6.
* **The projects.** One of 0.27 or before opens with its first twelve tracks: its tracks 13-16 are left out (an LFO, a
  MOD or a TRIG aimed at one of them stops; their mutes go). A project of 0.28 is saved as 0.27 saves, plus one chunk
  for the notes 5-6 and the lanes 7-8: a 0.27 opens it, without them. A MIDI file read into a project on the Pi:
  channels 1-12 become tracks 1-12, channels 13-16 are left out (`sagga_sgqmid` says how many notes).
* **The memory**: a project is 15 KB smaller (163 KB in RAM; a step is 22 bytes, a track's settings 104).

On the Pi: the editor shows twelve tracks, six notes a step and eight lanes; the bridge sends the previews and the
phrases to tracks 1-12, up to six notes. Install the FM-1 and the Pi together.

## The FM-1 panel

The rule: **the button you hold says what you work on; the white keys pick, the black keys act, the knobs set**.
OCT- / OCT+ with a button held turn that button's pages (the page is remembered). **0.12: a tap on HOME, SEQ, EDIT, ENV,
LFO, ARP or FX opens its window** - the button counts as held until the same tap closes it or another window opens;
a button really held wins meanwhile. The rows below read the same way for a window.

| held | white keys 1-16 | black keys 1-11 | K1 K2 K3 K4 |
|---|---|---|---|
| nothing | the steps (**0.11: hold one, press another: the note between them**; **SEL + FX** tapped first (0.12; FX alone in 0.11): a step loop between them, EXIT puts the length back) | 1-8 track of the bank, 9 other bank (**0.28: the banks are 1-8 and 9-12**), 10 mute, 11 solo | note (an off step: its note and the pen, a preview, not lit), velocity, chance, ratchet of the cursor step |
| SEL | the keys are notes for the cursor step (within 0.45 s: a chord of up to 6 - 0.28; 4 until 0.27) | (notes) | velocity offset, humanise timing, humanise velocity, **pen note** |
| **a group + SEL** (0.12) | **PICK**: the key is the value of the knob in focus (lists, lengths, roots, semitones, percentages: see PICK) | 1-10 items 17-26; **11: the focus to the next knob** | |
| HOME | **track 1-12** (0.28; whites 13-16: nothing, for now) | as with nothing held; in PERF: the song (1-8 add a scene, 9 loop, 10 take the last away, 11 clear) | see HOME pages (8) |
| EDIT | the cursor to that step (not switched) | **1 STEP LOCK**, 2 COPY, 3 PASTE, 4 CLEAR the step, **5 PLAIN** (no EXPO from this step), **6 TIE** (legato into the next step), **7 SLIDE** (0.13: TIE, and the next note glides: CC 65) | gate (1 % .. 100 %, 1.5 .. 64 STEP), condition (16), nudge, ramp; **SEL + K1-K4 (0.12): the step's notes 1-4** (a knob below the first: the note taken away; 0.28: the line shows notes 5 and 6, written by playing - SEL + keys, MIDI REC, the grid, the Pi's editor) |
| ENV | the cursor to that step | | **one lane a page (OCT- / OCT+: lanes 1-8; 0.28, six until 0.27)**: K1 the lock on the step, K2 the CC number (SEL + K2: the NRPN MSB), K3 the base, K4 the mode NORMAL / SLIDE / TRIGLESS / NRPN |
| LFO | that LFO on / off | | page 1 shape (**0.20: + ENV**), rate (**0.13: then 1/4T 1/8T 1/16T 1/32T**), depth, centre; page 2 destination (**0.20: + MOD ONLY**), target, CC, phase; page 3 on, retrigger, invert, **TRIG** (0.13: CLOCK or T1-T12, the sidechain); **page 4 RATE SEQ** (0.13): steps, every, position, its rate; **0.20: page 5 ENV** attack, decay, sustain, release; **page 6 MOD** slot, source (SEL: which), destination (SEL: which), amount |
| SEQ | the 16 tools (WHEN / EVERY: when they happen; **0.12: UNDO held 0.6 s = REDO, COOK held = the random COOK**; **0.17: BEAT held = a PROPOSAL** in a free pattern; the tap acts when the key is let go) | dice SEQ CC LFO GROOVE ALL (**0.12: black 1 held = DICE PROG**), SCOPE, KIT (**held: BAND**), DRIFT, EVOLVE, FREEZE, REVERT | see SEQ pages (7) |
| FX | the 16 effects while held | 1-8 LOOP (tap) / REPEAT (hold) 1/32 .. 4 bars, 9 RESTART, 10 STOP at the bar, 11 EXIT (a DJ loop, or the step loop of the selected track; SEL also held: the selected track only) | INTENSITY, GATE, SWING, FILTER (the macros, saved); **SEL + K1-K4 (0.12): the THROWS** (the same four, gliding back to 0 over a bar); FX + OCT-: to 0; FX + OCT+: ECHO ALL; **FX + ARP twice: BAKE**; **FX + HOME: PANIC** |
| ARP | **0.12: the keys play the selected track** (its notes, a drum's hits), REC on: written; **on a BREAK track: the chops 1-16** (tapped: stays; held: while held, then back) | on a BREAK track: 1 ROLL, 2 ROLL 1/32 (held), 3 HALF, 4 DOUBLE, 5 BACKWARDS, 6 DICE, 7 RESET, 8 / 9 the chop after / before; **on a DRUM track, playing (0.13): 1-4 NOTE REPEAT 1/16, 1/32, 1/32T, 1/8 of the white held**; else the keys play | see ARP pages (6) |
| SAVE | slot 1-8; **white 16: the set played becomes scenes and the song** (SALVA VIAGGIO) | **1-8 SNAPSHOT** (SEL also held: store), **9 CC CAPTURE, 10 SEND, 11 PATCHES** | see SAVE pages (4); PRESETS: the slot |
| GLO (PERF) | **0.12: mute 1-12 in any mode** (0.28: twelve tracks) (PERF: SEL + OCT+ first: solo, SEL + OCT-: mute) | pages 1-2: scenes 1-8 of the cursor's bank (SEL: store), 9 all on, 10 only the selected, 11 invert; **page 3 (0.17): the MOSSE** (below) | see GLO pages (4); PRESETS: the scene cursor 1-16; **GLO + OCT- / OCT+ (PERF: OCT- / OCT+ alone): the pages; GLO + SEL + OCT- / OCT+: the track's octave** |
| **MOSSE** (SEL + GLO: PERF on page 3; 0.17) | PERF's mutes (SEL: solo) | the moves at the phrase's end: FILL, BREAK, RISER, DROP, HALF, DOUBLE (0.24, with SEL: SHORTER, LONGER - every track's length), THIN, SWELL, 9 INDIETRO, 10 the last cancelled, 11 NOW | K1 the energy, K2 the phrase, K3 the genre, K4 the key; **ALG MOVES AT**; SEL + ALG the tempo; **PRESETS the progression** (queued) |

A group **held half a second** with nothing else shows the map of its keys on the screen's message lines, and what
SEL + a key does for the knob in focus (in a window the map stays four seconds, then the key and genre lines come back).

### HOME pages (OCT- / OCT+ with HOME held)

| page | K1 | K2 | K3 | K4 |
|---|---|---|---|---|
| 1 TRACK | MIDI channel (1-14; 1-16 with two USB ports) | length 1-64 (playing: at the bar - 0.25: the metre's -, from the bar line; **0.24**: longer, the pattern goes round again in the new steps - its copies; shorter, it waits whole after the loop) | step: 1/1 .. 1/32T, **0.25: then the polyrhythms** 1/4 5:4, 1/8 5:4, 1/16 5:4, 1/4 7:4, 1/8 7:4, 1/16 7:4 (five, seven steps in the time of four) | transpose: IN KEY -24 .. +24 **steps of the scale**, FREE -48 .. +48 semitones |
| 2 PLAY | direction FWD REV PING RND | swing 50 % (straight) .. 75 % | **OCTAVE** -3 .. +3 | **FOLLOW** the harmony |
| 3 KEY | **SLOT** 1-16 (the key that plays) | root | scale | shift -24 .. +24 |
| 4 MODE | mode: FREE / IN KEY / DRUM / TAPE / **BREAK** (0.12: a track of slices) | **ROLE**: none, KICK SNARE HAT PERC BASS CHORD ARP, CLAP OPEN HAT RIDE SHAKER CONGA TOM RIM CRASH COWBELL RUMBLE SUB LOG DRUM STAB PAD PIANO LEAD VOX | **CHORD**: OFF, or one of 32 shapes (ARP page 2 has it too, with the KEY mode) | **KEY**: follows the slot that plays, or pinned to slot 1-16 |
| 5 LOOPS | the notes' loop | the velocities' loop | the gates' loop | the program of the track's channel in the PERF cursor's scene |
| 6 MIDI FX | effect shown: OFF HARM OCTAVE ECHO VEL (**0.16: READY, SEQ + white 6 starts it, with the values it had on the track; 0.19: the four in a chain, VEL > OCTAVE > HARM > ECHO: SEQ + white 6 adds the one shown, or takes it out if it plays; OFF: all stop**; **0.20: + CHANCE RANDOM NOTE FILTER GATE GLITCH; SEL + K1: the one shown earlier / later in the ORDER**) | amount (of the one shown) | time (ECHO) / which steps (OCTAVE) / the new ones' K3 | how much each keeps (ECHO) / its velocity (HARM) / the new ones' K4 |
| 7 TIMING | DELAY -30 .. +30 ms | CHAIN **OFF / P1+2 / LIST** (0.13) | **GROOVE** OFF HOUSE GARAGE DILLA AFRO SAMBA LAID BACK PUSH HUMAN TRAP (0.15; a TAPE track: TAPE BARS 1-16) | **GROOVE AMT** 0-100 % (a TAPE track: TAPE QUANT 0-100 %) |
| **8 CHAIN LIST** (0.13) | LENGTH 1-8 entries | ENTRY (the one the knobs set) | its PATTERN 1-8 | how many TIMES 1-8 |

(VIAGGIO's knobs, HOME 8 until 0.11, are **GLO 3**: 0.17 the MOSSE.)

MIDI FX amounts: HARM -7 .. +7 steps of the key (a FREE track: -12 .. +12 semitones); OCTAVE -2 .. +2 octaves, on
ALT (every other step), RANDOM, 3RD, 4TH; ECHO 0-4 repeats, every 1/32, 1/16, 1/8T, 1/16 dotted, 1/8, 1/4T, 1/8 dotted
(the default), 1/4, each keeping 10-100 % of the velocity of the one before; VEL -8 .. +8 (soft .. hard). The
effect's notes are ornaments: STOP, PANIC, a mute or a KILL cancel the ones waiting. **0.19, the chain**: VEL CURVE
first (the velocity every other effect starts from), then OCTAVE (the note), HARM (its voice on the moved note, at its
velocity %), ECHO (the note and the voice, each repeat keeping its %). 128 ornaments wait at most: past that the
softest are dropped. **0.20**: nine effects, in the track's ORDER (SEL + K1); "What is new in 0.20" has their knobs.

### SEQ pages

| page | K1 | K2 | K3 | K4 |
|---|---|---|---|---|
| 1 EUCLID | pulses (this track; **0.16: EUCLID LIVE off: READY, SEQ + white 6 starts it**; **0.23.1, NUMERIC: one of sixteen rhythms**, **0.25: fit to the bar**) | rotation | **FAMILY**: EUCLID, TRESILLO, NUMERIC (turned: the screen says what K1 and K2 do in it) | heat (COOK, the dice) |
| 2 ALGORITHM | OFF TURING CELL ACCENT DENSITY (the slot shown; **SEL + K1: the slot 1-4**; **0.16: READY, SEQ + white 6 starts / stops it**) | A (of the READY one, else the one playing) | B | C |
| 3 EVOLVE | targets RHYTHM .. ALL | amount (**0.27, SEL + K2: RETURN** 0-100 %, how much of the seed comes back before each change: 100 stays near it, 0 is DRIFT) | every 1 2 4 8 16 bars | scope |
| 4 EXPO | HITS 2-64 (SETTLE: RATE a beat) | CURVE -8 .. +8 (SETTLE: DEPTH) | SPAN STEP, BEAT, 2 BEATS, BAR, 2 BARS, 4 BARS | SHAPE OFF, RAMP, BOUNCE, SETTLE (**0.16: the one that starts it**; K1-K3 set it up while OFF) |
| 5 EXPO 2 | VEL FLAT, FALL, RISE, BOUNCE, GRACE (the first hit at 75 %) | GATE 5-100 % | JITTER 0-50 % | NOTES CHORD, ARP, ARP +1 .. +3 OCT |
| 6 TOOLS | random density 0-100 % | **WHEN**: NOW, BAR, 2, 4, 8, 16 BARS | **EVERY**: OFF, 1, 2, 4, 8, 16, 32 BARS | **GENRE**: FREE, ON, LIVE |
| **7 BREAK** (0.12) | **CHOP**: the re-order written over the loop (16, one a white key: STRAIGHT .. BUILD; UNDO takes it back) | **ROLLS** 0-7: how many steps the dice rolls | **SWAP** 0-100 %: how much of the bar the dice re-orders | **SLICES** 8 / 16 / 32 |
| **8 THEORY** (0.23) | **SOURCE**: LIBRARY (the patterns are loaded), THEORY (they are made by the genre's rules), FREE (made by the rules of no genre) | **NEXT SEED** 1-999: the seed of the next BEAT, KIT, BAND | **TRACK SEED**: the seed of the pattern this track plays - turned, it is another part at once | **VARIATION** 0-99 of that pattern, its size HEAT (COOK walks there a step at a time) |

(The harmony, SEQ 4 and SEQ 8 until 0.11, is **ARP 3-6**.)

| algorithm | A | B | C |
|---|---|---|---|
| TURING | mutation 0-100 % (0: a locked loop) | length 2-16 steps, **0.25: then TRACK** (as long as the track, up to 64; it grows and shrinks with it) | moves the RHYTHM, the NOTES (0-7 steps up the key), or BOTH |
| CELL | rule 0-255 (**0.23.1**: turned, the screen says what it makes of the track's rhythm; the ones to start from are below) | cells 4-64 (the row repeats every so many steps) | a new generation every 1, 2, 4 bars, or every loop |
| ACCENT | BEAT, OFFBEAT, POLY3, SYNC 3+3+2, RANDOM | amount 0-63 | offset 0-15 steps |
| DENSITY | 0-200 % (100: as written; under: fewer, the beat last; over: ghost notes added) | the ghosts' velocity 10-100 % | |

Turning EUCLID's knobs while EUCLID LIVE is off sets it up (0.16: READY; until 0.15 it switched it on); SEQ + white 6
switches it on / off (on the scope). On SEQ 2 K1 makes an algorithm READY, K2-K4 set it, SEQ + white 6 starts it with
those values (and stops it). A new algorithm starts from the written rhythm; its knobs never restart it. The families: EUCLID spreads the pulses as evenly
as they go (E(5,16) = x..x..x..x..x...); TRESILLO fills 3-3-2 cells, half a bar at a time; NUMERIC (0.23.1) is sixteen
base rhythms of 16 steps: K1 picks one (1 four on the floor ... 7 the son clave, 8 the rumba, 9 the bossa ... 12 the
tresillo twice ... 16 the busiest; the table is in "What is new in 0.23.1"), K2 turns it. The rhythms are written on
16 steps. **0.25: a rhythm is fit to the steps it has**: the metre's bar (14 steps in 7/8, 20 in 5/4), or the loop
when the loop is shorter than a bar - every hit at its place in proportion; a hit that would fall on the one before
it, or right beside it, is left out, so the rhythm keeps its rests. A track of several bars repeats the bar's rhythm.
(Until 0.24 a loop shorter than 16 played the beginning of the rhythm.)

**CELL** is a row of cells on a ring, one a step: a cell of the next row is on or off by what itself and its two
neighbours are now, and the RULE (0-255) is the table of the eight cases. Its first row is the rhythm written on the
track (nothing written: one hit in the middle); the same rhythm and the same rule always tell the same story - there
is no chance in it. 0.23.1: a row that comes out empty is the written rhythm again. Rules to start from, on 16 cells:
**204** the row stays as it is; **170** it slides a step earlier every row, **240** a step later; **184** and **226**
slide too, and hits in a row open up; **51** swaps hits and rests; **90** and **150** open the rhythm up and come back
to it in at most 8 rows; **60** and **102** longer phrases (up to 16 rows); **54** thin and thick in turn; **18**,
**22** sparse stories; **110**, **30** long ones, 30 with no loop in sight. Most of the other rules freeze, fill
every step or do nothing: the screen says which as you turn. With fewer CELLS than steps the row repeats inside the
loop (8 cells: half a bar, twice).

WHEN and EVERY apply to the tools that change a pattern (CLEAR, REVERSE, SHIFT, RANDOM, COOK, BEAT, PROG, PASTE,
DOUBLE, INVERT, HUMANIZE; not UNDO, WRITE LIVE, EUCLID LIVE, COPY). With WHEN on BAR a tool pressed while playing waits
for the bar line (the screen counts the bars); EVERY repeats the last tool used every so many bars from the next one.

### SEQ held: keys

| | |
|---|---|
| white keys 1-16 | CLEAR, REVERSE, SHIFT <, SHIFT >, RANDOM (**0.27: a roll of the dice**: OCT+ keeps it, OCT- puts it back, ALG goes through the rolls), **EUCLID LIVE on / off** (**0.16: on SEQ 2 the slot's algorithm: the READY one starts, else the one playing stops; a MIDI FX READY on the track (HOME 6): it starts**), **WRITE LIVE**, UNDO (a dice waiting: BACK; **held 0.6 s: REDO**), COOK (by the track's role; **held: the random COOK**; on a BREAK: the next chop of the library's genre, held: one of them at random), BEAT, PROG, COPY, PASTE, DOUBLE, INVERT (on an empty row: all on), HUMANIZE. UNDO, COOK, DICE SEQ and KIT act when the key is let go. On a TAPE track: CLEAR, SHIFT <, SHIFT >, DOUBLE |
| black keys 1-11 | DICE SEQ (**held: DICE PROG**; on a BREAK: the backbone kept), DICE CC, DICE LFO, DICE GROOVE, DICE ALL, SCOPE (next; held + white keys: the CUSTOM tracks), KIT (**held: BAND**), DRIFT (**0.27: EVOLVE's RETURN at 0**, and back to the one it had), EVOLVE on / off, FREEZE, REVERT |
| SELECT / ALG / PRESETS | BEAT part (the genre's band, PROG, KIT) / variation 1-12 (1-6), **then the Pi's** (**0.23, SOURCE THEORY: the NEXT SEED**) / **the genre** (of everything; the harmony follows only what is loaded) |
| SAVE | **the selected track's loop to the Pi** as a variation of its part (**ARP + SAVE**: the progression, the one being written on ARP 5 / 6, else the one playing) |

BEAT on one track loads the part chosen for the track's length (0.24: the track keeps it; a pattern shorter than the track comes with its copies) (KIT: the genre's drums; they become drum tracks; BAND:
the genre's whole band, on the tracks with those roles, else on free tracks; channels are kept); pressed again, the
next variation. A BASS or ARP loaded while HARMONY is on gets FOLLOW; **0.25: a LEAD or a VOX follows as a MELODY** (ARP 4 K1). A loaded track remembers where it came from:
GENRE LIVE reloads it from the new genre at the bar line. The tools apply to the scope (the screen says on how many
tracks). **0.23, SOURCE THEORY** (SEQ 8 K1): the part is not loaded, the engines make it from NEXT SEED in the genre's
style (pressed again: the next seed; SOURCE FREE, or GENRE FREE: the style of no genre); COOK walks to the next variation of the
pattern's own seed; the machine's ENERGY fills and empties it ([THEORY](#theory-the-engines)).

### Other controls

| control | does |
|---|---|
| PLAY | start / stop. SEL + PLAY: continue. HOME + PLAY: master / slave clock |
| REC | tap: arm (the keys and incoming notes are played and recorded, with the length held; stopped: step recording; a TAPE track: overdub). **Held 0.6 s (0.12): TAKE**, what was played in the last loop of the selected track into its pattern. SEL + REC: quantised / free. HOME + REC: tap tempo. ENV + REC / LFO + REC: LEARN the CC number. **0.13: with MOTION on (SAVE 4 K1), REC writes the macros' moves too**; MIDI IN ALWAYS (SAVE 4 K4): the incoming notes play without REC |
| ARP | **tap (0.12): its window** (the keys play the track until the next tap; a BREAK: the chops on the whites, its moves on the blacks); **SEL + ARP tapped: the arpeggio on / off** (the tap alone in 0.11). HOME + ARP, twice: BAKE the key into the patterns. **FX + ARP, twice: BAKE the macros**. **ARP + SAVE: the progression to the Pi** |
| HOME, SEQ, EDIT, ENV, LFO, FX | **tap (0.12): the window** of the button (closed by the same tap, or by another window; a button really held wins). **SEL + FX tapped: the next two steps are a LOOP** (FX alone in 0.11) |
| OCT - / + | page of 16 steps; SEL: octave of the keys; HOME / ENV / LFO / SEQ / ARP / SAVE / **GLO** held, **or their window open**: the pages. A dice waiting: OCT+ keeps it, OCT- puts it back. **FX + OCT-: the macros to 0. FX + OCT+: ECHO ALL on / off** (off: the repeats waiting go too). **GLO + SEL held: the track an octave down / up**. **PERF: GLO's pages; SEL + OCT-: the white keys mute, SEL + OCT+: solo** |
| SELECT encoder | the track (LFO held: the LFO; SEQ held: the BEAT function) |
| ALG encoder | the cursor; **a dice waiting: the rolls**; SEL + ALG: tempo; HOME + ALG: loop start; SEQ + ALG: BEAT variation; **the MOSSE: MOVES AT** |
| PRESETS encoder | the track's pattern (queued while playing; **0.17: a PROPOSAL waiting is queued first**); PERF: the scene cursor (**the MOSSE: the progression**); SAVE + PRESETS: the slot; SEQ + PRESETS: the genre |
| GLO | a tap: PERF on / off - **its window** (another window tapped leaves it; SEQ pressed leaves it). Held: its pages' knobs and the PERF keys. HOME + GLO: the song on / off. **SEL + GLO (0.17): PERF on page 3, the MOSSE; again: the studio** (0.12-0.16: VIAGGIO's keyboard; held: the journey off) |
| SAVE | tap, then again within 3 s: saved. HOME + SAVE, twice: load the slot (0.14: an empty slot = a new project). SEL + SAVE: RELOAD |
| **FX + HOME** | **PANIC**: sustain up, All Notes Off, All Sound Off on every channel; again within 2 s: the transport stops too |
| HOME + EDIT | the button lights: OFF, LOW, MID, HIGH, MAX (SAVE 3 K2 too) |
| SAVE 3 SYSTEM | K1 one or two USB ports; **SEL + K1 twice: reconnect** (and the ports change); K2 the button lights |
| MASTER knob | TEMPO 30 .. 300 BPM (the default), MORPH or FILTER (SAVE + K1). It takes over only after you move it; FILTER has a dead zone in the middle (0) |

Conditions: ALL, 1:2, 2:2, 1:4, 2:4, 3:4, 4:4 (which loop of the track), FILL, !FILL, 1:3, 2:3, 3:3, 1:8, FIRST (the
first loop after PLAY only), PRE (only after a step of the track that played), !PRE. Chance is per step. A step that
is switched on for the first time plays the track's **pen note** (SEL + K4; saved with the project).

### Knobs

Values that move by more than one a detent (gate and strum 5 %, filter 2, morph 4, heat, density, EVOLVE amount 5)
move on a grid of that step: from an odd value (set by the grid or the remote) the first detent goes to the next
multiple, so 0 and the round values are always reached. Turned fast (detents under 45 ms apart) a knob moves 2x after
3 detents and 4x after 6; the first detent after a pause and every change of direction is one step.

### ARP pages (the notes, the chords, the harmony)

| page | K1 | K2 | K3 | K4 |
|---|---|---|---|---|
| 1 ARP | mode (13: BLOCK, UP, DOWN, UP-DN, DN-UP, UP&DN, CONV, DIV, RND, WALK, PLAYED, THUMB, PINKY) | octaves 1-3 | **RATE**: **1/4**, **1/2** (0.18: a note every 4 / 2 steps), ROLL (the chord inside its step), 1-4 notes a step | **RUN**: OFF / RETRIG / HOLD / HOLD+RT |
| 2 CHORD | **shape** (32) | **KEY**: DIATONIC / FREE / STRICT | voicing | strum |
| 3 HARMONY | **OFF / ON / LOCK** | progression 1-6 of the genre, USER 1-4, DICE/PI, **then the Pi's** (of the MOOD); **0.16: with the HARMONY off it is READY, K1 starts it** | bars a chord: the progression's own, 1, 2, 4, 8 | FOLLOW this track |
| 4 HARMONY 2 | **FOLLOW**: HOLD, RETRIG, LEGATO, **MELODY** (0.25: a tune - it stays where it is written, its strong notes go to the chord), **SMOOTH** (0.26: chords - the notes two chords share stay, the others go to the nearest) (this track) | **the harmony's genre** (**0.16: FREE**, left of the first: no genre, ARP 3 K2 through all 150) | **MOOD**: ANY, SAD .. SUSPENDED | **RHYTHM**: BARS, GENRE, PUSH 16TH, PUSH 8TH, 3+3+2, TWO A BAR, 3+5, 3+1, 2 BARS |
| 5 USER PROG | the progression USER 1-4, DICE/PI | the chord 1-8 | **its root**: I bII II bIII III IV #IV V bVI VI bVII VII, or `--` (the progression ends before it) | **its shape**: the key's chord with a colour (TRIAD, 7, 9, SUS4, SUS2, 6), then the chord shapes OCT .. 1-3-5-8 |
| 6 USER PROG 2 | **MOOD** (GUESSED: the machine's) | the lengths of a RHYTHM written into the chords | **the chord's length**: 1-64 16ths (0: the HARMONY's rhythm) | **PUSH** 0-4 16ths |

### GLO pages (the live; GLO + OCT- / OCT+, or tap GLO for PERF: OCT- / OCT+ alone turn them)

| page | K1 | K2 | K3 | K4 |
|---|---|---|---|---|
| 1 LIVE | MORPH | MORPH TO (the scene) | TRANSPOSE (the key) | QUANTISE |
| 2 TRACK LIVE | the track's pattern (queued) | its length | the scale | MUTE QUEUE |
| 3 MOSSE (0.17; VIAGGIO until 0.16) | the energy (the target) | the phrase: 4, 8, 16 bars | the genre (queued while playing) | the key's root (queued while playing) |
| **4 THE METRE** (0.25) | **BAR**: 3-32 steps (16ths). Stopped: at once; playing: at the bar line (`BAR 14: 7/8 2+2+3 AT THE BAR`, the cell says `BAR >`) | **BEATS**: the ways that bar divides (14 steps: 2+2+3, 2+3+2, 3+2+2) | **SCENE METRE** (0.26): OFF / BRING IT - a scene stored keeps the metre, and brings it when recalled (the metre's name - 7/8, 5/4, 15/16 - is in the line under the cells: `GLO 4/4 METRE 7/8 = 2+2+3`) | (shows BAR.STEP: where the music is) |

In PERF mode (GLO tapped), **SEL + the knobs are TRACK LIVE** whatever page is shown, as in 0.11; SEL + ALG the tempo;
**OCT- / OCT+ turn the pages** and **SEL + OCT- / OCT+** make the white keys mutes / solos. On page 3 (the MOSSE) ALG is
MOVES AT and PRESETS the progression; the black keys are the moves. Page 4 with PICK: the white and black keys are
the bar's steps (white 1 = 3 steps), or the ways it divides.

### SAVE pages

| page | K1 | K2 | K3 | K4 |
|---|---|---|---|---|
| 1 | MASTER knob function | the remote OFF / CH 14 / 13 + 14 | snapshots bring their tempo | the PROFILE: FULL, SEMPLICE, PALCO |
| 2 | **CC LEAD** 0-30 ms | **SONG TEMPO** | **DEVICE** of the track's channel (GENERIC, ELEKTRON) | **LONG PATTERNS** (0.24; LIBRARY LEN until 0.23): COPY (a library pattern of one bar repeats in a longer track) / PHRASE (the long form: the next variation in the last bar, the genre's fill) |
| 3 SYSTEM (0.12) | **USB PORTS** 1 / 2 (SEL + K1 twice: reconnect) | the button lights | | |
| **4 LIVE IN** (0.13) | **MOTION** OFF / 1 / 2 / 4 BARS (REC + FX K: written) | **KEYBOARD** OFF / TRANSPOSE / TRANS <C3 (the MIDI IN transposes), **0.26: CHORDS / CHORD <C3** (its chords are the harmony) | **KEYB CH** ANY / 1-16 | **MIDI IN** REC ONLY / ALWAYS |
| **5 THE CLICK** (0.26) | **CLICK** OFF / REC / PLAY | **COUNT IN** OFF / 1 BAR / 2 BARS | **CLICK OUT** FM-1 / CH 1-16 | **LEVEL** 1-10 (SEL + K4: the MIDI note) |

SAVE held, whatever the page: PRESETS or whites 1-8 choose the slot; SAVE tapped twice saves; HOME + SAVE twice loads;
**SAVE + REC twice clears the slot** (0.15). Page 1 shows the slot's project name and the one in the FM-1 (0.15).

### PICK: the keys set the knobs

Hold a group button (HOME, GLO, SEQ, ARP, EDIT, ENV, LFO) - **or open its window with a tap** - and SEL: the keys set
the knob **in focus** of the page shown, the one turned last on that page (K1 at first); the screen marks it with `>`
before its label (`>-` when the keys cannot set it: a continuous value such as a velocity or a CC value stays on the
knob). **Black 11** moves the focus to the next knob. The knob is then turned by the difference, so what a knob does
(its messages, its limits, the bar line it waits for) happens the same way; the keys that mean something are lit and
the key of the value now blinks. **On the grid** the FOLLOW view (SHIFT + STEP, twice: CC, then FOLLOW; PICK until
0.17) shows the four knobs of the page open (a group held or its window; PERF's page when PERF is on, HOME's when
nothing is), a knob a row: pads 1-16 of rows 1-4 are the white keys of PICK, the pad of the value now white, a knob the
keys cannot set a faint row; a pad sets the knob (the focus goes to it). Rows 5-8 (0.18): a knob of the track across
the twelve tracks (a tap: that track gets the value; SHIFT + a tap: the FM-1 goes there), a knob that is no track's
(and the channel, a scene's program) its black keys 1-10. While it FOLLOWs, the grid's view goes with the FM-1's page
(SAGGA-GRID.md).

| the knob is | the keys |
|---|---|
| a list (a mode, a scale, a shape, a genre, a chop ...) | whites 1-16 = items 1-16, blacks 1-10 = items 17-26 |
| a count (pulses, hits, a track, a scene, a pattern) | whites 1-16, blacks 17-26 |
| a length in steps (LENGTH, a loop, a chord's 16ths) | whites 4, 8, 12 .. 64; blacks 3 5 6 7 9 10 11 13 14 15 (the polymeters) |
| a root (the KEY, VIAGGIO's key, a chord's root) | the key is the note: F3 .. G5, chromatic |
| semitones or scale steps (TRANSPOSE, SHIFT, a CURVE) | F4 = 0, F3 = -12, G5 = +14 |
| a percentage (heat, density, a gate, the energy ...) | whites 1-10 = 10 .. 100 %, blacks 1-10 = 5, 15 .. 95 % |
| a note (EDIT + SEL: NOTE 1-4 of the step, the one in focus) | the key is the note, with the keyboard's octave (SEL + OCT); the gate and the condition stay on EDIT's knobs |
| a CC number (a lane's, an LFO's) | 26 common CCs: 1 MOD 2 BREATH 5 PORTA 7 VOL 10 PAN 11 EXPR 12 13 71 RES 72 REL 73 ATT 74 CUTOFF 75 DEC 76 77 78 (whites); 64 SUSTAIN 65 PORTA ON 91 REV 93 CHO 16-19 GP 128 BEND 129 AFTERTOUCH (blacks) |

### BREAK: a drum break in slices

A sampler (an M8, a Digitakt, Simpler ...) has the break on consecutive notes, a slice a note, from the track's **PEN**
note (SEL + K4). A track in mode **BREAK** (HOME 4 K1) plays slices: every step is one (its number in the NOTE cell,
and in the STEP page's SLICE cell), the gate how long it rings, the ratchet a roll, the BEND lane its pitch; the key never
touches it. The chops (SEQ 7 K1, COOK, ARP + white 1-16, ARP + black 8 / 9) write a re-order over the loop, counting
the bar from the loop's first step; a step with STEP LOCK (EDIT + black 1) stays as written through the chops, the
dice and the moves; UNDO takes them back. The sixteen, one a white key: 1 STRAIGHT (the slices in a row), 2 END ROLL
(the last two steps roll), 3 RUSH (two rushes into the snares), 4 REPEAT (the first half twice), 5 DOUBLE (every other
slice, twice over), 6 HALF (every slice held two steps), 7 BACKWARDS, 8 GHOST (rests between the hits), 9 LOW (kicks
only), 10 HIGH (no kicks), 11 SHUFFLE (the pairs swapped), 12 THINK, 13 APACHE (the first two slices back on the three),
14 SNARES (the snare everywhere), 15 TRIPLE (threes against the four), 16 BUILD (every slice four times). **COOK** walks
the chops of the library's genre (SEQ + PRESETS), the ones that belong to it, in its order - JUNGLE: STRAIGHT, THINK,
APACHE, SHUFFLE, SNARES, TRIPLE, END ROLL; TECHNO: STRAIGHT, GHOST, HALF, LOW, END ROLL; FOOTWORK: TRIPLE, RUSH, REPEAT,
DOUBLE, SNARES, BUILD ... (the screen says `END ROLL (JUNGLE 7/7)`); COOK held picks one of them at random. The dice
(SEQ + black 1, RANDOM) keeps the backbone: slice 1 on the one and three, slice 5 on the two and four (a 16-slice bar:
the kick and the snare), re-orders SWAP % of the rest and rolls ROLLS steps; HEAT (SEQ 1 K4) says how far.

**ARP held, or its window open**: **whites 1-16 are the chops, live**: a tap writes the chop and it stays (UNDO takes it
back); a key **held** longer than 0.6 s plays its chop while you hold it and the pattern as it was comes back when you
let go (another white meanwhile: its chop, the same pattern underneath); the chop written blinks on the keys. Blacks
1 ROLL and 2 ROLL 1/32 (the slice played last on this track, else the step that plays, again on every step boundary,
with the swing, while held; each repeat rings for half its time), 3 HALF (every slice two steps), 4 DOUBLE, 5 BACKWARDS,
6 DICE, 7 RESET (STRAIGHT), 8 / 9 the chop after / before. **The slices are played with REC armed** (no ARP): whites
1-16, blacks 17-27 (a 32-slice break), written as you play (TAKE remembers them), and from the Pi's pads (SAGGA Break,
channel 13 notes 36-51 or CC 76-91) and the grid's STEP view note row. With 8 or 32 SLICES the slices wrap on the
notes the break has.

### TAKE and THROWS (from Skiff)

**TAKE** (REC held 0.6 s, or CC 107 on channel 13): the FM-1 always remembers the last 96 notes played on the keys, the
Pi's pads or sent in over MIDI since PLAY (the step each began on and where in it). TAKE writes the ones from the last
loop of the selected track into its pattern, on the step REC would have put them (a note in the second half of a step
goes to the next, as an early one): quantised (REC QUANTISED) or with the nudge (REC FREE), the gate as long as the
note was held, the velocity as played; a chord on a step adds its notes (up to four). UNDO takes it back. Not on a TAPE
(it records by itself) and only while playing; a STOP forgets what was played. **THROWS** (FX + SEL + K1-K4): INTENSITY, GATE, SWING, FILTER as throws:
from the moment the knob stops they glide back to 0 over a bar. FX + K alone: the macro stays, as always.

## The live features

* **QUANTISE** (PERF K4): when a queued pattern, scene, mute, snapshot or TRANSPOSE happens. AUTO (a pattern at the end
  of its track's loop, a scene or snapshot at the bar), NOW, BEAT, BAR, 2, 4, 8 BARS. **MUTE QUEUE**: mutes wait too.
* **LOOP / REPEAT** (FX + black 1-8, the grid's FX view): a tap is a LOOP that stays, held a REPEAT that lands in time.
* **MORPH**: a scene keeps the CC lanes' base values; MORPH glides from the scene playing to MORPH TO.
* **The macros** (FX + K1..K4): INTENSITY (velocity +/-), GATE (%), SWING, FILTER (lane 1 of every track), on every
  track at once, saved with the project; FX + OCT- puts them back to 0; FX + ARP twice bakes them into the patterns.
* **TRANSPOSE the key** (PERF K3, FX view row 3, remote CC 11): the key moves (root and shift), the tracks in key with
  it, at the QUANTISE moment.
* **Program Change per scene** (HOME page 5 K4), **RELOAD** (SEL + SAVE), **TEMP** (grid FX view), **song mode**,
  **tap tempo**, **step recording**, **finger drumming** on drum tracks, **MIDI LEARN** of CC numbers: as in 0.5.
* **The dice**: DICE SEQ (patterns of the genre with the progression of the roll), CC (the lanes' bases), LFO, GROOVE,
  ALL (the bank becomes a piece of the genre); 0.27: RANDOM too. Up to 16 rolls are remembered: ALG goes through them.
  OCT+ keeps, OCT- (or UNDO) puts back what was there before the first roll.
* **EVOLVE** every 1-16 bars, by the amount, around the seed; how near, its RETURN says (SEQ 3, SEL + K2: 100 from the
  seed every time, 0 away from it - DRIFT -, between part of the way back); FREEZE, REVERT. Rhythm-heavy genres
  move the rhythm more, melodic ones the notes; on FOLLOW tracks the beats get chord tones of the tonic, the steps
  between move by step. A locked step (EDIT + black 1) never changes.

## The click

SAVE page 5. The click sounds on the **beats of the metre** (GLO 4): in 7/8 as 2+2+3 three clicks a bar, the bar line
higher (2000 Hz against 1000) and louder. All of it is saved with the project; a new project has the click OFF.

| | |
|---|---|
| **CLICK** (K1) | OFF; **REC**: while it plays with REC on; **PLAY**: whenever it plays |
| **COUNT IN** (K2) | OFF, 1 BAR, 2 BARS. With REC on, PLAY first counts so many bars of the metre at the tempo - the screen says `COUNT IN 1.1`, `1.2` ..., the PLAY light blinks, the click sounds whatever K1 says - and then starts. PLAY during the count stops it (`COUNT IN STOPPED`). Nothing is recorded during the count. Only when the FM-1 gives the tempo (a clock from outside starts when it starts) |
| **CLICK OUT** (K3) | **FM-1**: the FM-1's own sound, from its audio output. **CH 1-16**: a MIDI note on that channel (40 ms; the bar line louder), for a synth or a drum machine |
| **LEVEL** (K4) | 1-10. **SEL + K4**: the MIDI note (75, a clave, unless changed) |

The FM-1's own sound is asked for a few milliseconds ahead, so that it lands on the beat; the audio output is otherwise
silent, as since 0.22.

## The keyboard's expression

Until 0.25 a keyboard played through the FM-1 (MIDI IN) lost everything but its notes. Now, whenever its notes are played
through - REC on, or MIDI IN ALWAYS (SAVE 4 K4):

| | |
|---|---|
| through | the **pitch wheel**, the channel's **aftertouch**, a key's own aftertouch (to the note that key plays), the **pedal** and every controller go to the channel of the track the notes play (the selected one; a LOOP's). LEARN, CC CAPTURE and the MOD MATRIX's CC IN still see a controller first |
| nothing left on | the pedal's release goes to the channel its press went to, wherever the track is by then; a wheel off its centre is centred there when the next move goes to another channel; STOP and PANIC let the pedal go, centre the wheel, take the aftertouch off |
| recorded: the wheels | REC on, while it plays, a track of steps: the pitch wheel, the aftertouch and a controller are written in the track's **LANES** as a knob is (the value on the steps as they play): in the lane that already sends that control, else in one that is off or was never written - from the last, never lane 1 - which is taken for it with SLIDE on. `LANE 6 RECORDS THE PITCH WHEEL`, `LANE 3 RECORDS CC 1`; `NO FREE LANE FOR CC 23` when there is none. The switches (CC 64-69), the bank and the channel's mode messages get no lane by themselves |
| recorded: the pedal | not a lane: the notes played while it is down are recorded **as long as they sound** - to the pedal's release -, on a track of steps, on a TAPE and in TAKE. Played back they need no pedal |
| a TAPE track | the wheel and the controllers pass and are not kept: a tape keeps notes |

## The length of a track, and its patterns

A track has ONE length (1-64 steps) and a loop start, for its eight patterns; a pattern is 64 steps of storage. What
plays is steps START .. LENGTH of the pattern.

| | |
|---|---|
| a length changes | **Playing: at the bar** (0.25: the metre's bar - in 7/8, every 14 steps) (`LENGTH 32 AT THE BAR`; the knob, the grid's SHIFT + step and TRACK row, the pages), and from that bar line the track is where the clock says a loop of that length is: two tracks of the same length are always in step, however they got there. Stopped: at once. LONGER / SHORTER: at the phrase's end |
| longer than the pattern | the pattern goes round again in the steps the track has more: its **COPIES**. Step i plays the step of the pattern that would play there, whatever lengths came before (16 -> 19 -> 32: the sixteen twice). `LENGTH 32: THE 16 STEPS REPEAT` |
| the copies | follow the pattern: a step of it changed by anyone (a key, the grid, a page, a tool, an engine, the energy) changes its copies within a moment. **A copy changed** (written, turned off, its note): all the copies are steps of yours from then on, the pattern is as long as the track (`THE COPIES ARE YOUR STEPS NOW`). The grid: a copy that plays is GHOST (a dim blue-green); the Pi's editor: the same colour |
| shorter than the pattern | the track plays its first steps; the pattern stays whole after the loop (the grid shows those steps blue, as ever), with a MARK where it ends. Longer again: the pattern as it was, its silences too, then round again from its own end (16 -> 12 -> 32: the sixteen twice) |
| written after the loop | steps you write after the loop are part of the pattern: made longer, the track plays them, and the pattern ends with the round of itself the last of them is in. The 64th step alone: silence up to it. A second bar written while the first loops, then LENGTH 64: the two bars twice |
| an empty pattern | has no copies: a longer empty track is a longer empty track |
| all eight patterns | fit the track's length, the ones that do not play too. A snapshot, UNDO, a dice put back, RELOAD, the end of TEMP bring a length back: the patterns fit it (the pattern that came back with it is as it was) |
| a tool on the loop | works on the loop as it sounds (REVERSE, SHIFT, INVERT, EUCLID, HUMANIZE, COOK, RANDOM): after it a loop that still is a pattern and its rounds keeps its copies, one that is not is steps. DOUBLE writes the loop again as STEPS (no copies: to be changed by hand); COPY / PASTE carry steps |
| a loop between two steps | (two keys, the grid's row) holds the track for a while: the copies wait as they are, EXIT brings the loop back |
| the loop's START moves | (HOME + ALG, the grid, a pattern that comes and puts it back on step 1, a snapshot): no copy stands for the step it stood for any more - the copies of the track's patterns are kept as steps, as they sound |
| a pattern that comes | **keeps the track's length**: the library, the engines, the Pi's patterns, the dice, the proposals, GENRE LIVE. It is made for the track - 64 steps for a track of 64, 32 for one of 32 .. 63, 16 for a shorter one - and what the track has more is its copies, what it has less waits after the loop. Only a pattern that does not fit a bar (the bembé's twelve steps, a Pi pattern of 12 or 24) makes the track as long as itself; the Pi's regia brings its own bars |
| LONG PATTERNS (SAVE 2 K4) | a library variation of one bar on a longer track: COPY, it repeats (its copies); PHRASE, the long form of 0.10 - the bars before the last are the variation, the last is the next variation with the genre's fill. A variation written over two or four bars comes as written. An old project's LIBRARY LEN 16 reads as COPY, 32 and 64 as PHRASE |
| LONGER / SHORTER | the MOSSE's SEL + black 6 / SEL + black 5: every track twice / half as long, at the phrase's end. **0.25: the tablet's LONGER / SHORTER** (SAGGA Live, channel 12 CC 61 / 60): the same, at the next bar |
| saved | the copies and the mark are saved (a list of which steps are copies: a copied rest takes no room). Steps kept after a loop take room in the project as any step |

What each generator makes of a track longer than a bar:

| | on 32 or 64 steps |
|---|---|
| the library (BEAT, KIT, BAND, GENRE LIVE) | the variation as written when it is two or four bars long; a one-bar one: COPY or PHRASE (LONG PATTERNS) |
| the THEORY engines | their own phrase: two bars a a', four bars a a' a b (the turn-around, the fill) |
| DICE SEQ | the library: a variation as a PHRASE, every bar a light take of its own; the engines: a new seed's phrase; GENRE FREE: a bar of chance and its phrase (as RANDOM) |
| RANDOM | (0.27: a roll of the dice, it waits for OCT+ or OCT-) a bar of chance, then its phrase: A A' on two bars, A A' A B on four. A' is the bar with its second half cooked (by the track's role, in the key), B the bar cooked harder but for its first beat; HEAT says how much. An answer the cook left as the question gets a pickup at its end (or loses one) |
| COOK | at random: every bar by the role's rules, its beats kept - the bars drift apart. Towards the next variation: the variation as a phrase as long as the track, a few steps a press |
| EVOLVE | cooks the whole loop: the bars evolve each their own way |
| EUCLID (live, and the tool) | its pulses are spread over the loop: 5 over 32 steps is not 5 over 16 twice |
| NUMERIC | a rhythm of one bar (0.25: the metre's bar, the rhythm fit to its steps), repeated; a loop shorter than a bar: the rhythm fit to the loop |
| TRESILLO | its 3 3 2 groups run along the whole loop: PULSES counts them over it |
| TURING | its phrase is its register (B: 2-16 steps): it goes round inside the track, whatever the length. **0.25, B on TRACK**: the register is the track's loop, as long as the track is now |
| CELL | its row is B cells (4-64): set B to the track's length for one row a loop; a new generation every 1 / 2 / 4 bars or every loop |
| ACCENT, DENSITY, the ARP, EXPO | by step and by beat: the same on any length (POLY3 runs across the bars) |
| the HARMONY, FOLLOW | by bars (0.25: of the metre): a track of 64 steps in 4/4 hears four bars of chords |
| a BREAK's chops | written over the track's loop |

## The metre

The bar is N **steps** (16ths), 3 to 32, and its **beats** are groups of those steps. GLO page 4 (PERF: its fourth
page) sets both: K1 the bar, K2 the way it divides. Sixteen steps in four quarters is 4/4, as it always was, and a
project that never touches the page is as it was.

| | |
|---|---|
| the bar (K1) | 3-32 steps. An even bar is counted in eighths (14: 7/8, 20: 5/4 or 10/8, 12: 3/4 or 6/8, 18: 9/8), an odd one in sixteenths (7: 7/16, 15: 15/16). The message says what it is: `BAR 14: 7/8 2+2+3, 12 TRACKS FOLLOW` |
| the beats (K2) | every way the bar divides in beats of 2 and 3 eighths (an odd bar: of 3, 4, 5 sixteenths), 217 in all: 14 steps are 2+2+3, 2+3+2 or 3+2+2; 16 are 4/4, or 8/8 as 3+3+2, 3+2+3, 2+3+3; 20 are 5/4 or six ways of 10/8; 12 are 3/4 (2+2+2) or 6/8 (3+3). The first way is the usual one. The beats move no track |
| when | stopped: at once. Playing: at the next bar line of the bar that plays (`BAR 14: 7/8 2+2+3 AT THE BAR`, the cells show `BAR >`, `BEATS >`), and every track begins again on that line: the new metre is counted from its first bar |
| the tracks | a track that is a number of bars long **follows**: 16 steps become 14, 32 become 28, 64 become 56 (in a bar of 20: 20, 40, 60 - three bars, the fourth does not fit 64 steps). Its patterns are not rewritten: a shorter track plays their first steps and keeps the rest after the loop, a longer one goes round in the steps it has more (their copies), and the old bar gives every pattern back whole. A track of any other length - 19 steps against the bar, your polymetre - stays as it is. A TAPE's loop is bars of the metre |
| what waits for the bar | a LENGTH, a queued pattern or scene or snapshot or mute (QUANTISE BAR, 2, 4, 8 BARS; BEAT: the metre's next beat), the transpose, WHEN and EVERY, EVOLVE's bars, STOP at the bar, GENRE LIVE, a proposal, the song, the MOSSE's moves at the BAR and at the BEAT and their phrase (4, 8, 16 bars of the metre) |
| what is counted in bars | the harmony (a chord a bar of the metre; the rhythms 3+3+2, PUSH, TWO A BAR keep their places in it), LOOP and REPEAT's 1, 2, 4 bars, EXPO's BAR spans, MOTION's bars, TAPE BARS, the grid's and the editor's bars, the place the Pi's pages show |
| a pattern that comes | **is made in the metre's bars.** The library's variations are written in 4/4: each beat of the bar that plays takes a beat of the written bar - the first the first, the last the last, the ones between the second and the third in turn - with as many of its steps as the beat has (a beat of three eighths: the quarter and its last two 16ths again). The engines make their patterns the same way, and theirs **follow a new metre**: made in 4/4 and the bar becomes 14, they are made again in 7/8 from their seed (one a pass; a pattern of theirs you changed by hand stays as you made it, in its own metre, and the ENERGY leaves it alone until the bar is that metre's again). RANDOM, COOK, the dice and the proposals work in the bar that plays |
| the feel | GROOVE, ACCENT (BEAT, OFFBEAT, SYNC), DENSITY, the cook and EVOLVE read a step by its place in the metre's bar: the beat is the metre's beat |
| NUMERIC, EUCLID | NUMERIC's rhythm is fit to the bar; EUCLID spreads its pulses over the loop, as ever |
| saved | with the project (the bar and a mask of its beats; 4/4 is written as nothing at all). The editor on the Pi has both (Project: METRO), the marks of the beats on every row, and a MIDI file carries the time signature |

## THEORY: the engines

SEQ 8 K1 chooses where BEAT, KIT, BAND, the dice and the proposals take a pattern from: the **LIBRARY** (the written
variations, as until 0.22), the **THEORY** engines, which make it from the rules of the genre and a seed, or the engines
**FREE** of the genre, which make it from the rules of no genre whatever the genre and its mode. In Italian,
with what each engine does and why: [TEORIA.md](TEORIA.md); the rules of the 21 counted genres: [TEORIA-GENERI.md](TEORIA-GENERI.md).

| | |
|---|---|
| a band, a kit, a part | BAND, KIT, BEAT as always: made from **NEXT SEED** (SEQ 8 K2, SEQ + ALG, the grid's BEAT view) in the genre's style; the next press takes the next seed. The screen: `REGGAETON BAND SEED 12: 9 TRACKS`, `TECHNO HAT SEED 3` |
| another part on a track | SEQ 8 K3, the pattern's own seed: made again at once (the first turn is one UNDO) |
| a variation | COOK walks the pattern towards variation n + 1 of its seed (`COOK HAT VAR 3 TO GO`, then `REACHED`), n + 2 after it; HEAT is how much of the part a variation makes again - up to 40 % the details, above it the big choices too (a motif's shape); the family of the part is the seed's and stays. SEQ 8 K4 goes there at once. A variation that would change nothing is passed over |
| fuller, emptier | the machine's ENERGY (GLO 3 K1, the grid's energy row, RISER, DROP, remote CC 3 on channel 14, channel 13 CC 114): the patterns the engines made follow it, one a pass, the kicks first. Only the steps that differ between the two energies are written (a part that minds the kick - a rumble, a sub - is written whole) |
| the dice | DICE SEQ: seeds of the dice on the scope (the rolls, OCT+ and OCT- as with the library); DICE PROG: a progression by the genre's rules in the DICE / PI slot, which plays |
| the genre | GENRE LIVE: a new genre makes the engines' patterns again in its style from their seeds, at the bar |
| no genre | **SOURCE FREE** (SEQ 8 K1, the click past THEORY): FREE's band (KICK SNARE HAT PERC BASS CHORD ARP LEAD; KIT: the first four) and its rules of no genre, no swing or groove of a genre, the tempo as it is; BEAT on several tracks (the scope) gives each the part of its ROLE - FREE has a rule for every role; DICE PROG rolls in any scale; a change of genre leaves the engines' patterns alone, GENRE LIVE or not (a track of the library takes the new genre's part from the library, as always). The screen: `FREE BAND SEED 3: 8 TRACKS`, `FREE HAT SEED 4`. **GENRE FREE** (SEQ 6 K4) does the same while the SOURCE is THEORY (the cell says THEORY, the line under it FREE); **HARMONY FREE** (ARP 4 K2) frees DICE PROG alone. A pattern keeps the style it was made in: the energy and COOK treat a FREE one as FREE until BEAT makes it again |
| the parts listen (0.25) | a part is made WITH the part it answers: a **lead, a voice, an arpeggio** with the first track of chords, the **percussion** with the snare, a **bass** with the first lead, voice or arpeggio. Where the other part strikes, a note of this one that is not one of its fixed ones stays away two times in three; right after it, a note is likelier. The part answered is read as it sounds: an engines' pattern from its seed (at the middle energy, so that the answer does not change with every move of the energy), a library pattern or one of yours from its steps. When it is made again by BEAT, a seed, the dice or UNDO, the parts that answer it are made again within a moment, from their own seed - changes made to them by hand are lost then |
| the melody (0.25) | a LEAD or a VOX gets FOLLOW's **MELODY** way: it stays where the engine wrote it and its strong notes go to the chord playing (ARP 4 K1) |
| the metre (0.25, **0.26: in the bar**) | a part is made IN the bar of the metre: every step stands for a 16th of a 4/4 bar - the bar's two halves are that bar's, the beats of a half the first and its answer - and the style's rules are read there, every choice by the step's own place: a kick on every beat of a 7/8, no beat the copy of another. An odd bar is felt one of two ways (the long beat of 2+2+3 whole, or split): the band's, by its seed. A 16th a part is built on that has no step in the bar (the snare of dubstep on three, in three beats) is carried by the nearest beat. One, two or four BARS OF THE METRE, as the track has. It follows a new metre: made again in the new bar - a pattern of 0.25 too -, and back in the old one it is what it was |
| an answer has notes (0.26) | **a bass under a tune** takes the tune's notes: off the beat, where the tune has no attack, the note it had an 8th or a beat before - as readily as its style's own bass uses that note (a bass of roots stays one). **A tune over chords** plays, on the 16ths right after a chord, a note of it - its third, its fifth, its seventh - and FOLLOW MELODY takes that note to the chord that plays. The part answered is heard as it IS (with the part it answers itself). Only patterns made new by 0.26: one of 0.25 is made again as 0.25 made it (what the engines keep of a pattern says which) |
| the length | **0.24: the track's.** A track of 16 steps (or less) gets a bar, one of 32 .. 63 a bar and its answer, one of 64 the two again with the genre's fill in the last; what the track has more than that is the pattern again (its copies). SEQ 8 K3 makes it again for the track as it is now |

What the engines know of a pattern (its seed, style, part, variation, energy) is kept with the pattern: saved with the
project, restored by UNDO, RELOAD and the dice's BACK, copied with the pattern. A pattern that is pasted, doubled,
cleared, recorded over by a tool that writes it whole or loaded from the library is nobody's again: the energy leaves
it alone. A TAPE or BREAK track's pattern is never the engines'. With SOURCE LIBRARY the patterns the engines made
earlier still follow the energy. The SOURCE is saved with the project (0 LIBRARY, 1 THEORY, 2 FREE).

## The journey and the MOSSE

**The journey always runs** (0.17): there is nothing to switch on. **SEL + GLO** opens PERF on its third page, **the
MOSSE**; SEL + GLO again goes back to the studio; GLO + OCT reaches the page too, and GLO held on it gives its black
keys from any mode. The white keys are PERF's mutes, as on every PERF page. The black keys light what waits in the
queue (black 10: something to cancel; black 11 blinks while NOW waits for the bar).

**The phrase.** 16 bars (GLO 3 K2: 4, 8, 16), counted from PLAY. At its end (the **boundary**) the queue runs, in
the order it was filled, and the phrase is written into the trail. **MOVES AT** (ALG on the MOSSE) chooses when the
queue runs: the phrase boundary (the default), **every bar**, or **every beat** (you decide when things happen; the
phrase still counts for FILL, RISER, DROP and the trail). The screen shows the energy, the bar of the phrase, the genre
and key (with `>` when one is queued) and the queue; the grid's VIAGGIO view shows it all at once.

**Roles.** A track's role (HOME 4 K2: KICK SNARE HAT PERC BASS CHORD ARP ..., or none) says what it is in the genre:
the proposals follow it, THIN and SWELL read its place on the genre's ladder (a track with no role takes the next free
one).

**The tracks** have a state: EMPTY, PROPOSED (it has patterns that do not play), IN (it plays), OUT (it has notes and
is muted). It follows the hands: a mute in PERF, a scene, a pattern changed, a row written or cleared.

* **On the panel** a track goes in and out with PERF's mutes (MUTE QUEUE and QUANTISE make them wait for the bar or
  the phrase), and a **proposal** is made in SEQ: **SEQ + BEAT held 0.6 s** writes what BEAT would (SEQ's genre, part
  and variation) into a free pattern of the selected track, the one playing untouched; held again: the next
  variation; **PRESETS** queues the proposal waiting first, and it enters at the QUANTISE with its settings.
* **On the grid's VIAGGIO view and the remote on channel 13** the journey has its tracks as VIAGGIO mode had them: a
  tap on an EMPTY track, a proposal from the library of the genre (`T1 KICK P2 READY`), with the track's role, else
  the next free one on the genre's ladder, and its note; a tap on a PROPOSED track goes through its proposals
  (`T1 KICK P3 (2/3)`); **held** (the grid, 0.45 s): the dice (another variant, maybe the genre's neighbour; for PERC in
  the afro / latin genres a tresillo, son clave 3-2 and 2-3, rumba, cascara, bossa, cinquillo, bembé 12/8). Up to seven
  proposals a track, each with the settings it asks for; when the patterns are full the oldest proposal goes. A tap on
  a track that is IN changes nothing in the sound. Queued (the grid's row 3, CC 32): IN at the boundary (an OUT track,
  or a proposal); on an IN track: OUT at the boundary, its last bar fading out; the opposite move cancels the queued
  one. SWAP queues the proposal chosen in place of what plays.

**The moves** (the MOSSE's black keys; the grid's row 4; remote channel 13 CC 17-27, in the old order: 9 SWAP, 10 LOOP,
11 NOW):

| black | move | at the boundary |
|---|---|---|
| 1 | FILL | the last bar of the phrase fills: the steps' FILL conditions play, and every track gets ghost hits, more in the bar's second half. Asked in the last bar itself: at once |
| 2 | BREAK | 1 bar with only the selected track; with SEL: 2 bars of silence, then everything back. A track that enters during a break waits for its end |
| 3 | RISER | the last 4 bars of an 8- or 16-bar phrase climb to energy 100, then back to the target |
| 4 | DROP | a fill in the last bar, then every track with notes IN and energy 100 at once |
| 5 / 6 | HALF / DOUBLE | every track at half / double speed for one phrase (the tempo and the tracks' divisions stay; every track restarts on the bar line at both ends) |
| SEL + 5 / SEL + 6 | **SHORTER / LONGER** (0.24) | the LENGTH of every track, half or twice (not the speed): longer, each pattern goes round again in what its track has more; shorter, the tracks play their first half and the rest waits after the loop - LONGER brings it back as it was. A track that cannot (twice would pass 64 steps; an odd number of steps) stays as it is; not a TAPE track, not a track in a LOOP of the journey. Stopped: at once. The grid: SHIFT + the pads |
| 7 | THIN | two tracks out: the two highest on the genre's ladder (never the last one); they fade in the last bar |
| 8 | SWELL | two tracks back in, the nearest to the energy |
| 9 | INDIETRO | the phrase before the one that ends plays again (patterns, mutes, key, genre, progression, energy; not the tempo); again before the boundary: one more back; with NOW (or stopped) it is the phrase before the one playing (0.9-0.16: OCT-) |
| 10 | cancel | the last move queued goes (0.9-0.16: OCT+) |
| 11 | NOW | the queue runs at the next bar instead (stopped: at once) |
| grid / CC 25 | SWAP | the selected track's proposal replaces what it plays |
| grid / CC 26 | LOOP | from the boundary the keys play and record on the selected track (64 steps of 1/16, in key; on a drum track every white key is that drum; an external keyboard records there too); the next boundary closes it and it loops. With SHIFT on the grid: 4 bars repeated. The track's length and division come back when it leaves the loop (BACK, SWAP) and return with it; a loop nothing was played into is forgotten |

GLO 3 K3 / K4 and PRESETS on the MOSSE queue a new GENRE, KEY, PROGRESSION (stopped: at once; the PROGRESSION with the
HARMONY off is READY, ARP 3 K1 starts it).

**The energy** (GLO 3 K1, the grid's row 5, remote CC 3 on channel 14): 0-100, 50 is neutral (0.17: at 50 nothing changes). It moves velocity (-20 ..
+20), the FILTER macro (-40 .. +40), gate (-10 .. +10 %), density (60-130 %: fewer hits, or ghost notes; the kick
stays whole; tracks with their own DENSITY algorithm keep it), the LFOs' depth (50-100 % up to 50, then 100 %), and from 70 the chords take
their 7th. A new target glides there over the rest of the phrase, a step a bar; DROP jumps.

**The genres** (GLO 3 K3, SEQ + PRESETS, the BEAT view: one genre for the library, the progressions and the journey):
each has a neighbour the dice may borrow from, a swing, and a ladder: the energy at which a role enters, in the order
kick snare hat perc bass chord arp (THIN takes the roles with the highest thresholds out, SWELL puts the nearest to
the energy back).

| genre | the dice's neighbour | swing | ladder |
|---|---|---|---|
| TECHNO | HARDTECHNO | 50 | 0 50 20 45 35 60 75 |
| HARDTECHNO | TECHNO | 50 | 5 45 20 35 15 70 55 |
| DUB TECHNO | TECHNO | 54 | 10 60 25 45 35 30 70 |
| HOUSE | AFRO HOUSE | 54 | 0 30 15 50 25 40 70 |
| UK GARAGE | UK FUNKY | 60 | 5 20 15 45 30 50 65 |
| UK FUNKY | UK GARAGE | 56 | 5 30 20 15 35 55 70; afro / latin percussion |
| GRIME | UK DRILL | 50 | 5 15 40 55 20 35 70; half-time |
| DUBSTEP | GRIME | 52 | 15 20 35 50 10 60 75; half-time |
| JUNGLE | DRUM+BASS | 50 | 10 5 30 45 20 65 75 |
| BASSLINE | UK GARAGE | 56 | 0 25 20 50 10 55 70 |
| REGGAETON | BATIDA | 50 | 0 10 40 25 35 55 75; afro / latin percussion |
| BATIDA | GQOM | 52 | 0 35 30 10 40 60 70; afro / latin percussion |
| GQOM | BATIDA | 54 | 0 45 35 15 30 65 80; afro / latin percussion |
| EXPERIMENT | FOOTWORK | 50 | 10 40 50 20 35 30 60 |
| ELECTRO | TECHNO | 50 | 0 15 25 55 20 50 40 |
| DRUM+BASS | JUNGLE | 50 | 10 5 25 50 15 60 75 |
| AFRO HOUSE | HOUSE | 54 | 0 50 30 10 35 45 70; afro / latin percussion |
| AMAPIANO | AFRO HOUSE | 58 | 15 55 35 20 30 10 70; afro / latin percussion |
| FOOTWORK | JUNGLE | 50 | 0 30 35 15 25 70 55 |
| TRANCE | TECHNO | 50 | 0 45 20 60 15 50 30 |
| UK DRILL | GRIME | 54 | 5 15 10 50 25 45 70; half-time |
| HARDCORE | HARDTECHNO | 50 | 0 35 15 55 20 40 70 |
| PHONK | UK DRILL | 52 | 0 20 15 45 10 55 30; half-time (the cowbell riff is the ARP) |
| BAILE FUNK | REGGAETON | 54 | 0 25 30 10 20 60 70; afro / latin percussion |
| MERENGUE | BATIDA | 50 | 0 40 5 10 25 35 55; afro / latin percussion |

**SEL + PLAY** on the MOSSE while stopped: the SEED, a dice on the set genre, the key and a tempo of the genre.

**The trail and SALVA VIAGGIO.** Every phrase is kept (the last 128), always (0.17). **SAVE + white 16** makes the
set a song:
the runs of equal phrases become scenes 1.. (at most 16, the shortest runs left out), the song plays them for as many
bars as they lasted. Then save the project as usual.

**The remote on channel 13** (SAVE + K2 on 13 + 14; with two USB ports on port 2): CC 1-12 a tap on track 1-12 (0.28; 13-16 nothing), CC
17-27 the moves (FILL BREAK RISER DROP HALF DOUBLE THIN SWELL SWAP LOOP NOW), 28 INDIETRO, 29 cancel the last, 30 the
phrase's length (0-95 shorter, 96-127 longer), 31 the next progression, 32 track value / 8 queued in / out (0-95: tracks 1-12). A button:
64-127.

**The profiles** (SAVE + K4, in this order): FULL, SEMPLICE (0.27) and PALCO. SEMPLICE is FULL with SEQ's pages
2 (the four algorithms) and 3 (EVOLVE) hidden while nothing of theirs plays: SEQ + OCT- / OCT+ skips them; an
algorithm on the selected track brings SEQ 2 back, EVOLVE on brings SEQ 3, and nothing is switched off
(`PROFILE SEMPLICE: SEQ 2 AND 3 HIDDEN WHILE OFF`). PALCO opens the MOSSE, shows HOME pages 1 and 3 only, refuses SEQ,
EDIT and ENV (the screen says so) and puts the remote on 13 + 14. The profile is kept in the FM-1's settings, not in
the project: power-on comes back in it.

## SNAPSHOTS

| | panel | grid (FX view) | remote |
|---|---|---|---|
| recall 1-8 (at the QUANTISE moment; again before then: cancelled) | SAVE + black 1-8 | row 8 pads 5-12 | CC 106-113 |
| store 1-8 | SAVE + SEL + black 1-8 | SHIFT + row 8 pads 5-12 | CC 12-19 |
| CC CAPTURE on / off | SAVE + black 9 | row 8 pad 13 | CC 114 |
| SEND the snapshot's sound | SAVE + black 10 | row 8 pad 14 | CC 115 |
| PATCHES (the Pi keeps the synths' patches) | SAVE + black 11 | row 8 pad 15 | CC 116 |

A snapshot keeps: the pattern of every track (not the steps: the patterns are the project's), mutes and solos, the
four macros, the key (its slot, root, scale, shift) and TRANSPOSE, HARMONY (on, the genre, progression, bars), every track's
settings (0.19: not the MIDI FX chain: it stays as it is), the 16 LFOs, MORPH TO, the tempo (if SAVE + K3 says "snapshots bring their tempo"), and up to 48 captured
CC values (channel, CC, value). When it comes back its sound goes out: the lanes' base values, then the captured CCs
(a CC a lane already sends is not sent twice), and a SysEx 40 tells the Pi to send the patches it keeps.

**CC CAPTURE**: store a snapshot, switch capture on (SAVE + black 9 blinks), turn the synths' knobs: every CC that
comes in (any channel; not the channel mode messages 120-127, not RPN / NRPN) goes into the snapshot playing, and a
lane of a track on that channel with that CC takes it as its base. Switch it off when done.

**PATCHES**: the Pi (the bridge, `patches.json`, see SAGGA-GRID.md) asks each synth for its patch, or listens for 10 s
while you send it from the synth, and keeps it with the snapshot and the project's id. The screen says how many synths
it kept; when the snapshot comes back the Pi sends them again and says so.

## USB: one port or two

The USB page (0.12: SAVE 3 SYSTEM; before, HOME + SEL) shows the link; K1 chooses **USB PORTS 1 or 2**, SEL + K1
twice reconnects with that.
Saved in the FM-1's settings (not the project), so the computer sees the same device from power-on.

* **1 port** (the default): everything on one port; channels 15 and 16 carry the grid, the tracks use 1-14 (14 is the
  remote's unless SAVE + K2 switches the remote off).
* **2 ports**: the FM-1 shows "Felucca MIDI 1" and "Felucca MIDI 2". **Port 1**: the synths, the tracks on **channels
  1-16**, clock, transport, incoming notes and CCs (REC, CC CAPTURE, LEARN), the TRS input. **Port 2**: the grid, the
  remote (channel 14), the project / library / snapshot SysEx. The bridge takes port 2 by itself. In RaspiMIDIHub's
  matrix connect the synths to port 1 only, and the remote plugins to port 2.

## Saving

Eight slots. The slot saved last is loaded at power-on. 0.15: SAVE + REC twice clears the chosen slot (stopped); the
slot's header page carries the project's name. Saving never stops the music (nine areas of flash, erased while
stopped; a save writes into an erased one and is read back before it counts; a power cut never loses a slot). Saved
with the project: everything above (the macros too, from 0.10) but the dice and EVOLVE state, TEMP and the song's
position; the journey's settings (on, phrase, energy, genre, the tracks' states), the patterns playing, the mutes and
the scene cursor. **0.10 reads 0.10 projects only** (SGQA): the format was laid out again (sixteen keys, six lanes,
roles, the tools' schedule, user progressions ...) and nothing older loads; keep a 0.9 firmware to play 0.9 projects.
**0.28** saves a project as 0.27 does (sixteen places for tracks, the last four empty), plus a chunk of its own for the
notes 5-6 and the lanes 7-8: a 0.27 opens it without them; 0.28 opens one of 0.27 or before with its first twelve
tracks.

## Export and import (SysEx)

With the transport stopped, the EXPORT pad of the grid's PROJ view sends the project to the Pi, where the bridge saves
it as a `.sgq` file (`/boot/firmware/sagga/`). From the Pi, or any computer with the FM-1 on USB and Python:

```
python3 sagga_grid_bridge.py --export          # the current project -> a new .sgq file
python3 sagga_grid_bridge.py --export 3        # saved slot 3
python3 sagga_grid_bridge.py --import FILE.sgq # into the FM-1: it replaces the project there; SAVE keeps it
```

Every frame is `F0 7D 53 47 <cmd> ... F7`, all bytes 7-bit. With two USB ports, all of them are on port 2.

| cmd | frame | |
|---|---|---|
| 01 | `[slot 0-7]` | ask for an export (no slot: the project as it is) |
| 02 | `idx idx cnt cnt data... sum` | a chunk: 256 bytes of the image packed 8-to-7, LSB first; idx and cnt 14-bit; sum = the sum of the data bytes & 7F |
| 03 | `len*3 crc*5` | the end: length (21 bits) and CRC-32 of the image |
| 10 | `code idx idx` | the FM-1's answer to each import chunk and to the end (idx 3FFF): 0 ok, 1 busy, 2 damaged chunk, 3 out of order, 4 the image does not check out, 5 not a project, 6 slot empty |
| 20 | `idx idx` | (to the Pi) entry idx of the library, please |
| 21 | `idx cnt name...` | (from the Pi) entry idx of cnt (cnt 0: no file), the name up to 16 characters |
| 22 | `idx idx` | (to the Pi) load file idx: the Pi sends it as an import |
| 23 | `idx idx` | (to the Pi) the export that follows goes over file idx (3FFF: a new file) |
| 24 | `code idx idx` | (from the Pi) 0 saved, 1 could not save, 2 no such file, 3 could not read it |
| **40** | `n id*5 playing` | (to the Pi) snapshot n came back (or SEND): send the patches you keep for it |
| **41** | `n id*5 playing` | (to the Pi) keep the synths' patches for snapshot n |
| **42** | `code count` | (from the Pi) 0 kept, count synths; 1 nothing came; 2 sent to count synths |
| **50** | `bar*2 scene snap root scale deg+64 col harm pbar pbars energy genre queue play` | (to the Pi, 0.9 STATO) at every bar line and at a change of scene, snapshot or chord. bar: bars since PLAY (14 bits); snap 127: none; deg: the chord's step of the key; pbar / pbars: the phrase; queue: moves waiting |
| **51** | `t bars n (step note vel len)*n` | (from the Pi, FRASE) a phrase onto track t's playing pattern at the next bar (stopped: at once); bars 1-4 of 16 steps; len 1-100 the gate %, 0 = a long note; vel 0 = 100. UNDO takes it back; STEP LOCK steps stay |
| **52** | `t code` | (to the Pi, RISPOSTA) 0 written, 1 busy (one waits), 2 the track is locked (LOOP records on it, or every step locked), 3 the frame is broken |
| **53** | `t` | (to the Pi, TOCCATA) a hand changed track t |
| **54** | `led*16` | (from the Pi, REGIA LED) the 16 rules of the grid's REGIA view: 0 off, 1 on, 2 passing |
| **55** | `r` | (to the Pi, REGIA TASTO) rule r tapped on the grid |
| **60** | `G P` | (to the Pi, 0.11) how many variations of genre G, part P (SQ_FUNC_*) do you keep? |
| **61** | `G P n*2` | (from the Pi) that many |
| **62** | `G P i*2` | (to the Pi) variation i of yours (the first is 0) |
| **63** | `G P i*2 len has text*len notes*len` | (from the Pi) it, in the library's text (`. x X o g 2 3 4 -`; notes: a semitone above the root in hex, or a chord letter); len 0: none; has 0: a drum |
| **64** | `G P len has text*len notes*len` | (to the Pi) keep this one (SEQ + SAVE) |
| **65** | `G P code i*2` | (from the Pi) kept as variation i (0), could not write it (1), not a pattern (2) |
| **66** | `G M` | (to the Pi, 0.11) how many progressions of genre G and mood M (0: any)? |
| **67** | `G M n*2` | (from the Pi) that many |
| **68** | `G M i*2 r (semi shape)*r` | (to the Pi) the i-th, in order of likeness to these r chords (the one playing) |
| **69** | `G M i*2 n mood (semi shape dur push)*n` | (from the Pi) it: semi 0-11 the root above the key's, shape 6-36 a chord shape (5 + SQ_CH_*), dur 0-64 16ths, push 0-4; n 0: none |
| **6A** | `G mood n (semi shape dur push)*n` | (to the Pi) keep this one (SEQ + SAVE on SEQ 4 / SEQ 8) |
| **6B** | `G mood code i*2` | (from the Pi) kept as the i-th of its mood (0), could not write it (1), not a progression (2) |
| **70** | `sub ...` | (from the PC, 0.11: the PC test, `firmware/src/sagga_test.c`) 0 HELLO; 1 OPEN (the screen asks, SEL on the FM-1 = yes); 2 BOOT (a reboot into the test: no project, no slot read or written, a hand on any key stops it); 3 GO; 4 EV `idx*2 n (t*4 kind a*2 b*2 gc*4)*n` (presses at t ms after GO: 1 press, 2 release, 3 knob `b` = detents + 8192, 4 MASTER, 5 keys `a \| b<<14`, 6 probe, 7 end); 5 CLOSE (a normal reboot); 6 AGAIN `idx*2`; 7 TAKEN `idx*2 n`; 8 DIAG (0.20.9); 9 QUIET (0.23.1: the session is over - the FM-1 stops, every note off, takes no more events and sends nothing more, so that DIAG's counts stand still) |
| **71** | `sub ...` | (to the PC) the answers: 0 `state booted playing boots*2 vec*5 pc*5 ms*4 usb_ports profile version`; 1 `state` (1 asking, 2 yes, 3 no, 4 no answer, 5 playing); 2 `ok`; 3 `ms*4`; 4 `ok next*2 free`; 5 `ok`; 6 DONE `applied*2 late*2 lag*2 lost`; 7 ABORT; 8 DIAG (0.20.9) 19 numbers of 4 bytes, since the boot: the HELLOs and the test's frames that came in, the answers the USB had no room for, the ms of the main loop's first pass, the longest it stood still (ms); the USB's bus resets, SET_CONFIGURATIONs, the ms of the last, suspends, starts tried again, OUT packets taken, held back, malformed events, SysEx packets lost to the other port's SysEx, SysEx frames lost because the one before still waited for the main loop, IN packets sent, the most polls (2 kHz) one waited for the host, MIDI events dropped with the ring full; the ms now; **0.23.1, 16 more**: what the program handed to the USB on port 1, then on port 2 (each: clock ticks, note-ons, note-offs - a note-on of velocity 0 too -, control changes, the rest, the bytes of them all and of the SysEx frames), then the output ring's account (events put into IN packets, dropped unconfigured, thrown away by a bus reset, waiting now); 9 `ok` (QUIET) |
| **72** | `idx*2 k last text...` | (to the PC) the probe event idx asked for, in pieces of 150 characters: the explorer's `PROBE G`, `PROBE T1..16`, `PROBE H` lines |
| **73** | `n (idx*2 ms*4 gc*4)*n` | (to the PC) where each event was taken: the FM-1's ms and clock tick (the explorer replays the session in the simulator at those places) |
| **74** | `seq*2 n (ms*4 gc*4 st d1 d2 cable)*n` | (to the PC, 0.20.3, when GO's byte 1 bit 0 asked to hear the ports) every MIDI message that came in from the ports and was played: the ms, the clock tick before it, the status without bit 7, the cable (0 port 1, 1 port 2); seq = the number of the first in the session. DONE then also carries `heard*2 lost` |
| **30** | `on` | (from the Pi, 0.15) 1: send the positions for the next 6 s (the bridge asks again every 2 s while an editor page follows); 0: stop |
| **31** | `play scene song clk*3 bpm*2 (step pat)*16` | (to the Pi) where everything is: every 16th while asked, and at START / STOP. song 127: no song; clk: clock ticks since START (24 a beat, 21 bits: a TAPE track's place in its loop); each track's step sounding (0-63) and the pattern it plays |
| **32** | `t vel gate flags n note*n` | (from the Pi) play these notes on track t as the track plays a step (its channel, key, CHORD, voicing) for gate x 10 ms; flags bit 0: a TAPE note (the key only). A new one ends the one before; PANIC and STOP end it |

The FM-1 sends 31 only while asked (30), with the same rule: a position that does not fit the USB queue is skipped.
The FM-1 sends 50, 52, 53, 55 only after the Pi has sent a 51 or a 54 (the bridge's `Regista` class; `--regista`
prints the STATO frames), and never waits for them to go: a frame that does not fit the USB queue is dropped and the
next bar sends a new STATO.

`id` is the project's 32-bit id (made when a project is new), 7 bits a byte, LSB first: the Pi keeps the patches per
project and snapshot. The image starts with `SGQB` (0.11; 0.10's `SGQA` is read too), at most 32,512 bytes: a header
(tempo, clock, the current key and its slot), the 16 keys, the 16 channels' devices, the 5 user progressions (52 bytes
each: the chords by step and colour, or by root and shape, their lengths and pushes, the mood), the tracks (96 bytes
each: with their lanes, role, chord, octave, key slot, EXPO, TAPE, the four algorithm slots, FOLLOW's way), the scenes (with a Program Change per channel and their key slot),
the LFOs, the generators (with the harmony's genre, LOCK, RHYTHM and MOOD), the song (with a tempo per entry), the live settings (the macros, CC LEAD, SONG TEMPO), the
journey, the tapes' counts, the snapshots that are used (a track is stored only where it differs from the project),
then the steps (a 24-bit mask of the bytes that differ from an empty step, then those bytes), the tape events, then a
tail of chunks `tag len*2 data`, ended by a 0. Chunk 1 (0.13) holds what 0.13 added (RATE SEQ and TRIG, the CHAIN
LISTs, MOTION, LIVE IN): 780 bytes, 796 from 0.15 (the GROOVE in two bytes that were reserved, the name at the end); it is
written only when it is not at its defaults, and a firmware reads as much of it as it knows. A later version can add chunks; 0.11 skips the ones it does
not know. Chunk 2 (0.23) is the THEORY engines': the SOURCE, the next seed (two bytes), a count, then ten bytes for each pattern the engines made
(track, pattern, seed, style + 1 with the length in bits 5-6, part, variation, its size, energy, a reserved byte); written only when there is something to say. An `SGQA` image is read with 80-byte tracks, 18-byte progressions (four) and 24-byte generators, the rest
put to what 0.10 did. SGQ3 .. SGQ9 images are refused.

## SAGGA REMOTE: the commands on MIDI channel 14

Control Changes on channel 14 are commands (with two USB ports: on port 2, and channel 14 of port 1 is a track
channel). A knob: 0-127. A button: 64-127 pressed, 0-63 let go. SAVE + K2: OFF, CH 14, 13 + 14 (VIAGGIO on
channel 13, see VIAGGIO).

| CC | | CC | |
|---|---|---|---|
| 1 | MORPH position | 2 | MORPH TO scene 1-16 (0-15, or 16-127: value / 8) |
| **3** | **VIAGGIO energy** (0-127: 0-100) | | |
| 4 | EVOLVE amount | 5 | heat |
| 6 | QUANTISE 0-6 (AUTO NOW BEAT BAR 2 4 8 BARS) | 7 | INTENSITY (64 = 0) |
| 8 | GATE (64 = 0; 0 = -90 %, 127 = +100 %) | 9 | SWING (64 = 0, -25 .. +25) |
| 10 | FILTER (64 = 0) | 11 | TRANSPOSE the key (12 = 0, 0-24: -12 .. +12) |
| **12-19** | **store SNAPSHOT 1-8** | 20 | PLAY / STOP |
| 21 | CONTINUE | 22 | RELOAD |
| 23 | FILL (held) | 24-27 | LOOP / REPEAT 1/4, 1/8, 1/16, 1/32 (a tap: LOOP, held: REPEAT) |
| 28 / 29 | scene - / + | 30 / 31 | tempo -1 / +1 |
| 32 | TAP | 33 / 34 / 35 | EVOLVE, FREEZE, REVERT |
| 36 | UNDO (a dice waiting: BACK) | 37 | TEMP (held) |
| 38 | PANIC | 39 | MUTE QUEUE on / off |
| 40-47 | scene 1-8 | 48-59 | mute track 1-12 (0.28: 60-63 nothing) |
| 64-75 | kill track 1-12 (held; 76-79 nothing) | 80-84 | DICE SEQ, CC, LFO, GROOVE, ALL |
| 85 / 86 | keep the dice / put it back | 87 | STOP at the end of the bar |
| 88 | RESTART every track | 89 | EXIT the loop |
| 90-101 | RETRIG track 1-12 (102-105 nothing) | **106-113** | **SNAPSHOT 1-8** (at the QUANTISE moment) |
| **114** | **CC CAPTURE on / off** | **115** | **SEND the snapshot's sound** |
| **116** | **PATCHES** (the Pi) | **117** | **HARMONY on / off** |
| **118** | **ECHO on every track** | **119** | **WRITE LIVE** |

CC 120-127 are never commands: they are MIDI's channel mode messages (a PANIC's All Notes Off must not store a
snapshot). The plugins for RaspiMIDIHub are in `tools/raspimidihub`.

### Channel 13 (0.12): more commands beside VIAGGIO's

With REMOTE 13 + 14, channel 13's CC 1-32 are VIAGGIO's (see VIAGGIO) and **CC 33 and up** these; **notes** on channel
13 play the selected track as the keys do with ARP held (on a BREAK, notes 36-51 are the slices 1-16), and **notes
100-115 switch LFO 1-16 on (note on) and off (note off)**: SAGGA Mod's sixteen switches. A knob: 0-127 (a short list
takes the value as the index when it is under its size, else value / its share). A button: 64-127 pressed, 0-63 let go.

| CC | | CC | |
|---|---|---|---|
| 33-44 | track 1-12: the pattern 0-7 (or value / 16), at the QUANTISE moment (0.28: 45-48 nothing) | 49-60 | track 1-12: LENGTH 1-64 (61-64 nothing) |
| 65 | ROLL (held; a BREAK) | 66 / 67 / 68 | HALF, DOUBLE, BACKWARDS (a BREAK) |
| 69 | DICE SEQ | 70 | RESET (STRAIGHT; a BREAK) |
| 71 | ROLL 1/32 (held) | 72 | CHOP 0-15 (or value / 8; a BREAK) |
| 73 / 74 | the dice's SWAP 0-7, ROLLS 0-7 | 75 | SLICES 8 / 16 / 32 (0-42 / 43-85 / 86-127) |
| 76-91 | the slices 1-16 as pads (the value is the velocity, 0 = off) | 92 | which LFO (0-15, or value / 8) |
| 93 / 94 / 95 / 96 | that LFO's SHAPE, RATE, DEPTH, DEST | 97 | that LFO on / off |
| 101-106 | lane 1-6 of the selected track: the base, sent at once (lanes 7-8: the panel, the grid, the editor) | 107 | TAKE |
| 108-111 | THROWS: INTENSITY, GATE, SWING, FILTER (64 = 0), gliding back | 112 | the selected track (0-11; 12-15 nothing; 16-127: the twelve over the range) |
| 113 | its MODE (FREE IN KEY DRUM TAPE BREAK) | 114 | the journey's energy 0-100 |
| 115 | the set's genre 0-24 | 116 | the set's key, the root 0-11 |
| 117 | the harmony's progression | 118 | HARMONY OFF / ON / LOCK |

The pages: **SAGGA Motori** (the tracks: 33-64, 112, 113, 69 and channel 14's mutes, kills, RETRIG), **SAGGA Break**
(65-91, 107; 0.21: its SWAP, ROLLS and SLICES knobs show the tablet's track's), **SAGGA Mod** (92-97, 101-106, 108-111, 114-118, and the notes 100-115: the sixteen LFO switches).

0.18: what channels 13 and 14 do on "the selected track" (the pads, the lanes, TAKE, MODE, the LFO chosen, BREAK) they
do on **the tablet's track**: CC 112 chooses it, and the FM-1's own track stays as it is (the screen: `TAB T5: ...`).

### Channel 12 (0.18): SAGGA Live, the tablet's track

With REMOTE 13 + 14, Control Changes on channel 12 are the LIVE page's (with two USB ports: on port 2, and channel 12
of port 1 stays a track channel; with one port, channel 12's CCs coming in are the tablet's, its notes still record).
All on the tablet's track. A switch: 64-127 on, 0-63 off. A tap: it acts at 64-127.

| CC | | CC | |
|---|---|---|---|
| 1 | MUTE (a switch) | 2 | SOLO (a switch) |
| 3 | PATTERN 0-7, at the QUANTISE moment | 4 | LENGTH 1-64, at the bar |
| 5 | OCTAVE 0-6 (3 = 0) | 6 | SWING 50-75 |
| 7 | GROOVE 0-9 (OFF HOUSE GARAGE DILLA AFRO SAMBA LAID BACK PUSH HUMAN TRAP) | 8 | GROOVE AMOUNT 0-100 |
| 9 | MIDI FX 0-9 shown (OFF HARM OCTAVE ECHO VEL CURVE CHANCE RANDOM NOTE FILTER GATE GLITCH; not playing: READY) | 10 | its AMOUNT 0-24 (the first four: 12 = 0, -12..+12; the five of 0.20: over the effect's range) |
| 11 | FX GO (a tap; 0.19: the one shown joins the chain, or leaves it if it plays; OFF: all stop) | 12 | ALGO 0-4 READY on the slot shown |
| 13 / 14 / 15 | its A / B / C, 0-127 over the algorithm's range | 16 | ALGO GO (a tap) |
| 17 | EUCLID PULSES 1-64 | 18 | ROTATION 0-63 |
| 19 | EUCLID LIVE on / off (a switch; this track only) | 20 | ARP 0-12 (BLOCK UP DOWN ... PINKY) |
| 21 | OCTAVES 1-3 | 22 | RATE 0-6 (1/4 1/2 ROLL 1 2 3 4) |
| 23 | RUN 0-3 (OFF RETRIG HOLD HOLD+RT) | 24 | CHORD 0-31 (the 32 shapes) |
| 25 | FOLLOW (a switch) | 26 / 27 | COOK, BEAT (taps; this track only, now) |
| 28 | PROPOSAL (as SEQ + BEAT held) | 29 | QUEUE the proposal (as PRESETS) |
| 30 | RETRIG | 31 / 32 | DICE SEQ, UNDO (taps; this track only) |
| 40-51 | MUTE of track 1-12 (switches; 0.28: 52-55 nothing) | 56 | **SOURCE** (0.23): 0 LIBRARY, 1 THEORY, 2 FREE (a higher value, a switch's "on": THEORY from LIBRARY, a SOURCE on FREE stays) |
| 57 | NEXT SEED 0-127 (seeds 1-128) | 58 / 59 | the SEED 0-127 of the pattern the tablet's track plays (made again at once) / its VARIATION 0-99 |
| 60 | **SHORTER** (0.25; a tap): every track half as long, at the next bar (stopped: at once) | 61 | **LONGER** (0.25; a tap): every track twice as long. Each takes the other back |

### What goes back to the hub (0.18)

With **USB PORTS 2**, once the hub has said something on port 2 since the FM-1 started (0.20.8: anything - the grid
bridge's keep-alive comes every second, with or without Launchpads - so the pages follow from the start; before 0.20.8 a
page had to send a command first), the FM-1 sends on its port 2 what the
hub's pages show: when it changes (a few messages a millisecond, with room left for the clock and the notes), and
slowly all of it again (one value every 40 ms: a hub that restarted, a page reopened, catch up within seconds). A page
of RaspiMIDIHub takes a CC that comes in on a cell's channel and number as that cell's value and sends nothing back.
A value the tablet has just moved is left alone for 0.4 s (no fight with the hand); a value the FM-1 did not take (a
LENGTH past the pattern, an OCTAVE on a drum track) comes back corrected after that.

* channel 12: CC 1-10, 12-15, 17-25 (the tablet's track as above), 40-55 (the mutes as meant: MUTE QUEUE's waiting ones
  included, a BREAK's silence not), 56-59 (0.23: THEORY, the next seed, the track's seed and variation - a seed past
  128 shows as 128; nothing for a pattern that is not the engines');
* channel 13: CC 33-48 (the patterns: the one queued, else the one playing), 49-64 (the lengths: the one waiting for
  the bar, else the length), 73-75 (0.21: the BREAK's SWAP, ROLLS and SLICES 0-2 of the tablet's track), 92-97 (the tablet's LFO), 101-106 (the tablet's track's lanes), 112 (the tablet's track),
  113 (its MODE), 114-118 (energy 0-127, genre, key, progression, HARMONY); notes 100-115 (the LFOs on / off: note on
  127 / note off);
* channel 14: CC 1 (MORPH), 2 (MORPH TO, scenes 1-8), 4 / 5 (EVOLVE amount, heat), 6 (QUANTISE), 7-10 (the macros, 64 =
  0: a THROW gliding back moves them), 11 (TRANSPOSE).

0.20.6: four of these come back on **channel 12 CC 33-36** instead: 33 SWING (channel 12 CC 6), 34 QUANTISE (channel 14
CC 6), 35 the pattern of track 6 (channel 13 CC 38), 36 lane 1 (channel 13 CC 101). In MIDI 2.0, CC 6 and 38 are the Data
Entry of an RPN / NRPN and CC 98-101 choose one; RaspiMIDIHub 6 runs its pages as MIDI 2.0 clients where the Pi's kernel
speaks MIDI 2.0, and the kernel then turns the FM-1's CC 6 / 38 / 101 into RPN parts that never reach the page. The
SAGGA pages take channel 12 CC 33-36 as those four cells (so a binding of yours on them still works). QUANTISE goes back
with REMOTE 14 too (0.20.7), the other three with REMOTE 13 + 14. Coming in nothing
changed: the pages, the BeatStep plugin and any controller still send CC 6, 38 and 101.

In RaspiMIDIHub's matrix: the FM-1's port 2 ("Felucca MIDI 2") to the IN of each SAGGA page, beside their OUT to the
FM-1 (tools/raspimidihub/README.md). With one USB port nothing goes back (port 1 goes to the synths).

## Limits you should know

* The THEORY engines: a part answers ONE other part (a lead the first track of chords, not the bass too), and by its
  rhythm only - no call and response of notes; they write sixteens in four beats and the metre lays them on its bar
  (a 7/8 of theirs is a 4/4 re-barred, not a rhythm thought in seven); a phrase is two bars (four bars: the two
  again, with the fill); a motif is one voice; the counted genres play like their library, not better. The tablet
  reaches seeds 1-128, the panel all 999.
* The metre (0.25): one metre for the whole project (a track in another metre is a track of another length: a
  polymetre); a track exactly one bar long follows the bar back and forth (a track of 14 in 4/4, the bar made 14 and
  then 16 again: 16); the BEATS cell holds nine characters (the line under it and the message have them whole); the
  bar is not on the tablet; an engines' pattern changed by hand does not follow a new metre.
* The polyrhythms (0.25): five and seven in the time of four, no other ratio; EXPO's spans on such a track are those
  of a plain 1/16 track; a 0.24 firmware plays them as 1/16.
* MELODY (0.25): what is strong is decided by the step's place in the track's own loop and by its length, not by its
  velocity; the notes between the beats are not checked against the chord (over a borrowed chord a passing note of
  the key can rub for a 16th); TURING moving the notes comes after it.

* A TAPE note plays its note, velocity and length (with the track's transpose, key, mute, kill, INTENSITY and a positive
  DELAY): no conditions, ratchets, lanes or EXPO on a tape. A TAPE track's steps rest while it is a TAPE and are back
  when it is not. The DELAY of an EXPO span is not applied (spans start on the grid).

* The lengths (0.24): LONGER cannot make a track pass 64 steps and SHORTER cannot halve an odd number of steps (those
  tracks stay as they are, and the screen counts them); a TURING's phrase is its register (16 steps, or the track with
  B on TRACK: 0.25) and NUMERIC a rhythm of one bar, whatever the track's length; a pattern kept whole after a
  shortened loop takes room in the project as any other steps.
* An export blocks the FM-1 for about half a second (stopped only); a file of the library loads only while stopped.
* EVOLVE changes the patterns that were playing when it started.
* The parameter loops always go forward, whatever the track's direction.
* FILTER moves lane 1 of every track (put the synth's cutoff on lane 1); a lane with no base value is not moved.
* The ornaments (HARM, ECHO) share 128 places: when they are full the faintest echo waiting gives way.
* A snapshot keeps which pattern plays, not the pattern's steps.
* The proposals (SEQ + BEAT held, the grid's VIAGGIO view, the remote) take free patterns of the track (8 per track):
  when none is free the oldest proposal is replaced (SEQ + BEAT never takes a pattern written by hand). The trail
  lives in RAM: a power cycle starts it again (SAVE + white 16 before that).
* The remote's scene CCs 40-47 reach scenes 1-8; scenes 9-16 through CC 2, 28 / 29 or the panel.
* The patches need the bridge running on the Pi and the synths connected to the Pi; a synth that cannot send its patch
  over MIDI cannot have it kept.
* A SLIDE lane glides a step at a time (one value per step of the track): smooth enough for a filter sweep, not for a
  pitch bend; an NRPN lane sends its three CCs on every change.
* The eight lanes of a track share the step: a step is 22 bytes, a project about 163 KB of the FM-1's RAM (0.28:
  twelve tracks; sixteen, six lanes and four notes were 178 KB).
* A written step holds six notes (0.28: SEL + keys, MIDI REC, the grid, the Pi's editor; EDIT + SEL's knobs set notes
  1-4); a CHORD shape plays up to six, and the arpeggio, the strum and the voicing work on all six: at most six sound
  from a step.
* 0.28: twelve tracks. A project of 0.27 or before keeps its first twelve (its tracks 13-16 are left out); a 0.27 opens
  a project of 0.28 without its notes 5-6 and lanes 7-8. The remote's and the tablet's commands for tracks 13-16 do
  nothing; the remote's lane knobs (CC 101-106) reach lanes 1-6.
* 0.11: the Pi's variations and progressions need the grid bridge running (it answers for the hub's folders); without
  it SEQ + ALG stops at the FM-1's last variation and SEQ 4 K2 at its last progression (`PI: NO ANSWER`, then `NO MORE
  <MOOD>` without asking again for a while). A progression has up to 8 chords; one from the Pi takes the DICE/PI slot,
  and DICE PROG writes over it (SEQ + SAVE keeps it on the Pi first).
* 0.11: RETRIG and LEGATO (0.25: and MELODY) move the held notes of a FOLLOW track (long gates, TIE, held notes); an
  arpeggio's notes and a strum keep the chord they began on.
* 0.13: MOTION has 64 cells a macro (4 bars of 16ths): a move between two 16ths is written on the one it falls in. The
  KEYBOARD transposes the key (the IN KEY tracks), as TRANSPOSE does: FREE and DRUM tracks stay. A SLIDE sends CC 65 on
  the track's channel: a synth that ignores CC 65 still gets the legato (most mono synths glide on overlapping notes
  in their legato mode). A CHAIN LIST and the song's scenes are two ways of choosing patterns: a scene that gives the
  track a pattern not in its list switches the list off. The RATE SEQ, TRIG, CHAIN LISTs, MOTION, the KEYBOARD and MIDI
  IN settings are in the project, not in the snapshots.
* No audio: the speaker and the headphone output are silent by design.
* Tested on a computer: the real firmware code in a simulator (timing, MIDI, the screen, the flash, random input under
  AddressSanitizer), the USB descriptors, the bridge and the hub plugins with fake ports; and on a real FM-1 with the
  two Launchpads, two USB ports and an M8 through the link.
