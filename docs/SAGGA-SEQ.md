# SAGGA SEQ 0.14

A MIDI-only performance sequencer for the M-VAVE FM-1, built on Dinghy's platform. No synthesis: the FM-1 sends
notes, CCs and clock over USB to a hub (RaspiMIDIHub on a Raspberry Pi) that feeds the instruments. **Sixteen
tracks**, eight patterns of up to 64 steps per track, **sixteen scenes**, eight **snapshots**, a song of **64
entries**, sixteen LFOs, **sixteen keys**, eight project slots, a library of **24 genres** (patterns of 16, 32 and 64
steps), and **VIAGGIO**: a way to play a set as a journey of phrases, with moves queued for the phrase's end (or the
bar, or the beat). With two Launchpads through the Pi it becomes a 16 x 8
grid sequencer ([SAGGA-GRID.md](SAGGA-GRID.md)); almost everything is also on the FM-1's own panel.

The screen says `SAGGA SEQ 0.14` for three seconds after power-on: that is how you know the update took.

The tutorial (Italian) builds a song step by step; this page is the reference: every control, every message.

## What is new in 0.14

**A new project.** Choose an empty slot (SAVE + PRESETS: the screen says `EMPTY`) and load it, HOME + SAVE twice:
`LOAD SLOT 7 EMPTY: AGAIN = NEW PROJECT`, then `NEW PROJECT: SAVE PUTS IT IN SLOT 7`. Everything is at its defaults
(the tempo, the tracks, the key, the scenes, the song...); SAVE writes it in that slot. RELOAD has nothing to go back to
until it is saved. The other slots are not touched.

**The web editor (the Pi).** The hub's page (port 8090) opens every project of the library in an editor (`editor` next
to its name; **Nuovo** makes a new one, **Ricevi dall'FM-1** takes the FM-1's project as it is, stopped). On a phone or
a computer: **Tracce** (the 16 tracks with their 64 steps of a pattern: a tap turns a step on with the track's PEN note,
or only selects it; below, the step: its four notes, velocity, gate, chance, ratchet, condition, nudge, ramp, TIE,
SLIDE, PLAIN, LOCK, the six lanes' locks; copy / paste / clear), **Traccia** (every setting of the HOME pages; copy a
pattern to another track or pattern, clear it, turn it), **Lane** (the locks of a lane drawn with a finger, the lane's CC,
base, slide, NRPN), **Scene** (patterns, mutes, program changes, key), **Song** (the entries, the bars, the tempo; add,
move, take away), **Catene** (OFF, P1+2, a LIST), **LFO** (with RATE SEQ and TRIG), **Progetto** (tempo, clock, the 16
key slots, QUANTISE, MORPH, the macros, CC LEAD, LIVE IN, the synths of the channels). **Salva** writes the project in
the library (the file as it was is kept: **versioni**, **Ripristina**); **Manda all'FM-1** loads it in the FM-1 (stopped;
SAVE on the FM-1 keeps it). Annulla / Ctrl+Z, Ctrl+S.

The page never builds a project itself: the Pi's `sagga_sgqjson` is built from the firmware's own core, reads the
project with the FM-1's code and writes the changes through the FM-1's sanitize, so the editor cannot make a project
the FM-1 would not take (a value out of range is put right: the page says how many were). The TAPE tracks stay the piano
roll's; the snapshots and VIAGGIO are not touched. With the grid bridge running, the hub asks it (it holds the FM-1's
port); without it, it runs `sagga_grid_bridge.py --export / --import` itself.

## What is new in 0.13

0.13 keeps the **SGQB** format: its new settings travel in an extra block at the end of the project (written only when
something in it is not at its default), so 0.12 opens a 0.13 project (it skips the block: the CHAIN LISTs, the RATE
SEQs, the MOTION are not there) and 0.13 opens every 0.12 project as it is. Snapshots do not carry the new settings.

**LFO RATE SEQ (LFO page 4).** An LFO can change its rate as the music goes: **K1 STEPS** (OFF, 2-8 rates), **K2 EVERY**
(BEAT, 2 BEATS, BAR, 2 BARS: how long each rate lasts), **K3 POSITION** (which of them the knob below sets), **K4 RATE** of
that position (`(RATE)` in brackets: it still plays the LFO's own). Each rate starts its cycle where its time starts, so
a 1 BAR, 1/8, 1/4T, 1/16 sequence is a wobble that changes its speed on the beat (dubstep, bass music). **The rates go on
after 1/32 with the triplets 1/4T, 1/8T, 1/16T, 1/32T** (LFO page 1 K2, the RATE SEQ, SAGGA Mod).

**TRIG: the sidechain (LFO page 3 K4).** CLOCK (as always) or **T1-T16**: every hit of that track starts the LFO's cycle
again, and at the end of the cycle it stays there until the next hit. With the shape **DECAY** and **INVERT** on a
volume (an LFO on a CC, CC 7 or 11 of a pad's channel, centre and depth to taste) the pad ducks under the kick: the
pump of house and of bass music, played by the kick track itself (a muted track does not trigger it).

**NOTE REPEAT on a DRUM track.** ARP held (or its window), a white key held (its drum), and **black 1-4 held**: the drum
again every **1/16, 1/32, 1/32T, 1/8** while you hold them, in time with the track's steps (with its swing). With REC on
the repeats are written (a 1/32 or 1/32T as RATCHET 2 or 3 on the step). The blacks 1-4 are lit on a drum track while
playing, the one held blinks. On a melodic track ARP + keys play as before; on a BREAK the blacks are its moves.

**KEYBOARD and MIDI IN (SAVE page 4 LIVE IN).** **K2 KEYBOARD**: OFF, **ALL** (every note coming in on the MIDI IN
transposes the key: TRANSPOSE as GLO 1 K3, from -5 to +6, counted from the key as it was before any transpose: D in C =
+2, B = -1), **SPLIT C3** (the notes below C3 transpose, C3 and above are notes). **K3 KEYB CH**: ANY or 1-16, the channel
the keyboard sends on (the others are notes). The transpose waits for the QUANTISE moment, as the knob's (stopped: at
once); the notes that transpose are not played and not recorded. **K4 MIDI IN**: REC ONLY (as before: the notes that
come in play the selected track while REC is on) or **ALWAYS** (they play the selected track - a drum pad controller
its drums - REC or not; REC still records them, and TAKE always remembers them).

**MOTION (SAVE 4 K1): the macros' moves recorded.** OFF, 1, 2 or 4 BARS. With **REC on**, what you do to the four macros
(FX + K1-K4, a THROW gliding back, the remote's faders) is written into the loop, a 16th a cell, and then plays back by
itself: the FILTER opening on the last beat of every bar, the INTENSITY that breathes. While you turn a knob, and 0.3 s
after, the hand wins; without REC nothing is written. **FX + OCT-** (MACROS 0) wipes the motion too (`MACROS 0, THE
MOTION WIPED`). The FX screen and line 5 say MOTION / MOTION REC. The motion is saved with the project; OFF keeps it (it
plays again when the bars are set back).

**SLIDE (EDIT + black 7).** As TIE, the note holds into the next step, and **the next note glides into place**: the
portamento switch of the channel (CC 65) goes on (127) just before it and off (0) before the first note after it that does
not slide (and at STOP, PANIC). The glide's time is the synth's (its portamento / glide knob: an 808 bass, a TB-303, a
mono synth in legato). EDIT + black 6 TIE and black 7 SLIDE are one or the other; EDIT's blacks 5-7 are lit on a step
that has PLAIN, TIE, SLIDE; the screen says SLIDE, the screen's strip and the grid show it as a TIE. Not on drum and BREAK
tracks.

**CHAIN LIST (HOME 7 K2, HOME 8).** HOME 7 K2 is now **OFF / P1+2 / LIST** (P1+2: the pair of 0.10). **HOME 8 CHAIN LIST**:
K1 LENGTH 1-8 (the entries), K2 ENTRY (which one the knobs below set), K3 its PATTERN 1-8, K4 how many TIMES 1-8 it plays.
The track plays the list, each pattern at the end of the loop before (`HOME 8/8 1 >2X2 3`: the list, `>` the entry the
knobs set, `*` the one playing). PLAY starts from entry 1. A pattern chosen by hand (PRESETS, a scene, the remote) plays
as always at its moment; if it is in the list, the list goes on from it, if it is not, the list switches off (`T1 CHAIN
LIST OFF: P5 IS NOT IN IT`). PICK sets the four knobs too (HOME + SEL + a key).

**The Pi: BREAK IN SLICE.** The hub's page (port 8090) has a new section: a drum loop in WAV (PCM 8-32 bit or float)
goes in, a zip comes back - the slices 01.wav .. (8, 16 or 32, in the source's format), the loop with a cue point at every
slice, a **.sfz** that puts them on the keys from the first note up (C1 = 36 unless you say), one at a time (sfizz on the
Zynthian, Sforzando: load it as it is) and `LEGGIMI.txt` with the tempo found, the bars and what to set on the FM-1 (a
BREAK track, its PEN note = the first slice, SEQ 7 SLICES). The slicer finds where the break starts, its bars and tempo (a
power of two of bars between 90 and 180 BPM, or the BPM / bars you give) and moves each cut of the 16th grid onto the hit
next to it. The same from a terminal: `python3 sagga_slicer.py amen.wav --slices 16`. **SAGGA Mod**'s RATE has the
triplets.

## What is new in 0.12

0.12 keeps the **SGQB** format: 0.11 projects, snapshots and the Pi's library open as they are (a track's new fields,
the BREAK settings, start at their defaults). The pages of the buttons moved: the table below is the map.

**Windows: a tap instead of a hold.** A tap on **HOME, SEQ, EDIT, ENV, LFO, ARP or FX** (pressed and let go within
0.6 s with nothing else happening) **opens the button's window**: from then on it is as if you held the button - the
knobs and the screen are its, **the keys are its** (SEQ: the tools; LFO: the LFOs; HOME: the tracks; ARP: the keys play
the track; FX: the effects and the loops), **OCT- / OCT+ turn its pages**, **SEL + a key is PICK**. The same button
tapped again closes it; another window button opens its own instead; a button **really held** always wins, and lets
the window be when it goes. The button of the window open is lit full. **GLO's window is PERF** (a tap, as always: it
closes any other window; in PERF **OCT- / OCT+ turn GLO's three pages** and **SEL + OCT- / OCT+** make the white keys mutes
/ solos). SAVE has no window: a tap saves. The two taps of 0.11 moved under SEL: **SEL + ARP** = the arpeggio on / off,
**SEL + FX** = the next two-step gesture is a LOOP.

**Pages where they belong.** Each button holds what its name says and its pages go from the common to the rare: HOME
7 (the track), **GLO 3** (the live: LIVE, TRACK LIVE, **VIAGGIO**), SEQ 7 (rhythm and generators, **BREAK** last), **ARP 6**
(notes, chords, **the harmony and the user progressions**, which were SEQ 4 and 8), EDIT (the step; **SEL + knobs: its
four notes**), ENV 6, LFO 3, FX (**SEL + knobs: the THROWS**), **SAVE 3** (SYSTEM: the USB ports, the button lights).
GLO + OCT turns GLO's pages; the track's live octave is **GLO + SEL + OCT**. The reconnect is **SEL + K1 twice on SAVE 3**.
The second meanings of the SEQ keys are **holds**: UNDO held 0.6 s = REDO, COOK held = the random COOK, KIT held = BAND,
DICE SEQ held = DICE PROG (the tap acts when the key is let go).

**PICK: choosing with the keys.** A group button + SEL + a key sets the knob **in focus** of the page shown (the knob
last turned on that page; black 11 moves the focus; the screen marks it `>`): lists on the whites and blacks (items
1-16, 17-26), lengths 4, 8 .. 64 on the whites and 3 5 6 7 9 10 11 13 14 15 on the blacks, roots on the chromatic keyboard
from F3, semitone values with F4 = 0, percentages 10-100 on whites 1-10, the step's notes (EDIT + SEL: the key is the
note), 26 common CC numbers. The keys that mean something are lit, the one of the value now blinks. A knob the keys
cannot set says `-`. **A group held half a second shows the map of its keys** on the screen (in a window the map stays
four seconds). **From the grid**: the PICK view (SHIFT + STEP twice) shows the four knobs of the window open, a row each,
their values on the pads (rows 5-8: the black keys' values); a pad sets the knob.

**Long notes and the legato as one block.** On the screen a note of N steps is one bar through the gaps (1.5 steps:
half a cell more; TIE welds a step to the next); on the keyboard the covered keys **glow** (the low level of the LEDs);
on the grid they are dark green (TAIL) and a tied step light green (TIE; the bridge has the two colours).

**Studio and VIAGGIO on the same tracks.** **SEL + GLO, a tap**, switches the keyboard between VIAGGIO's (tracks and
moves) and the studio's (the steps) **with the journey going on**; the first time it starts the journey. **SEL + GLO held
0.6 s**: the journey off. A track you write, mute or clear by hand while the journey runs takes its state (IN, OUT,
EMPTY): THIN, SWELL, the energy and the proposals see it. **GLO held + keys = the PERF keys** (mutes, scenes) in any mode.

**BREAK: a drum break cut into slices.** A track in mode BREAK (HOME 4 K1) plays the slices of a sampler: every step a
slice (its number in the NOTE cell; the note = PEN + slice - 1), gate, ratchet, nudge, conditions as always. **SEQ 7
BREAK**: K1 **CHOP** (**16 re-orders, one a white key**, written over the loop: 1 STRAIGHT, 2 END ROLL, 3 RUSH, 4 REPEAT,
5 DOUBLE, 6 HALF, 7 BACKWARDS, 8 GHOST, 9 LOW, 10 HIGH, 11 SHUFFLE, 12 THINK, 13 APACHE, 14 SNARES, 15 TRIPLE, 16 BUILD),
K2 ROLLS, K3 SWAP (the dice), K4 SLICES 8 / 16 / 32. The dice (SEQ + black 1) keeps the backbone (kick on the one and
three, snare on the two and four) and re-orders the rest. **COOK walks the chops of the library's genre** (SEQ + PRESETS:
JUNGLE has seven, TECHNO five ...; held: one of them at random). **ARP (held or its window) + whites 1-16 = the chops
live**: tapped, the chop stays (as the knob writes it); **held, it plays while you hold the key and the pattern before
comes back when you let go**. ARP + blacks: 1 ROLL (the slice played last again on every step while held), 2 ROLL 1/32,
3 HALF, 4 DOUBLE, 5 BACKWARDS, 6 DICE, 7 RESET, 8 / 9 the chop after / before. **The slices are played with REC** (the
whites, written as you play; TAKE remembers them), from the Pi's pads and from the grid. On any other track ARP + keys
play it without recording.

**From Skiff.** **TAKE** (REC held 0.6 s): what you played on the keys or sent in over MIDI in the last loop of the
selected track goes into its pattern, REC or not (the FM-1 always remembers the last 96 notes). **THROWS** (FX + SEL
+ K1-K4): the four macros thrown, gliding back to 0 over a bar from the moment you let the knob go.

**The Pi.** Channel 13 answers **CC 33 and up** (patterns and lengths a track, the BREAK moves and the slices as pads
76-91, an LFO, the lanes' bases, TAKE, the THROWS, the track and its mode, VIAGGIO's energy, genre, key, the harmony),
**notes 36-51**: the slices, or the track's notes, and **notes 100-115: LFO 1-16 on / off** (SAGGA Mod's sixteen
switches, all at hand). Three new RaspiMIDIHub pages use them: **SAGGA Motori**, **SAGGA Break**, **SAGGA Mod**; SAGGA
Remote has TAKE. **ARP + SAVE** sends the progression to the Pi (it was SEQ + SAVE on SEQ 4 / 8).

## What is new in 0.11

0.11 writes **SGQB** projects and still reads 0.10's **SGQA** (the slots, the Pi's library, the snapshots): a 0.10
project opens with every new thing off (one algorithm slot, the harmony's genre the project's, FOLLOW HOLD, the
progressions as they were). A 0.11 project does not load on a 0.10.

**Time and harmony**

* **The HARMONY has a genre of its own.** Browsing the genres (SEQ + PRESETS, the BEAT view) no longer changes the
  chords: the progression comes from the harmony's genre, which follows the machine's only when something of that
  genre is actually loaded (BEAT, KIT, BAND, PROG, GENRE LIVE, VIAGGIO, a snapshot). **HARMONY OFF / ON / LOCK** (SEQ 4
  K1): LOCK keeps the harmony where you put it whatever is loaded, and keeps the dice from choosing a progression.
  SEL + K2 on SEQ 4 sets the harmony's genre by hand.
* **A length changes at the bar.** Turning a track's length while playing (HOME 1 K2, the grid's LEN row) waits for the
  bar line (`LENGTH 64 AT THE BAR`, the cell says it); a longer loop gets its new steps **filled with the loop that was
  there** (16 to 32: the 16 twice), and the steps a shorter length hid come back as they were. A library pattern or a
  snapshot loaded while playing lands in phase with the bar, not on step 1.
* **Progressions of your own, chromatic** (SEQ 8 USER PROG): a chord is a **root**, any of the 12 above the key's
  (I, bII, II, bIII ... the bVII and the bVI of the epic minor, the bII of the dark one), K3, and a **shape**, K4: the
  key's own chord there with a colour (TRIAD, 7, 9, SUS4, SUS2, 6), or any of the **chord shapes** (MAJ, MIN, MAJ7,
  MIN9, 9SUS4, DIM7, M7B5 ...). SEL + K3 gives a chord its own **length in 16ths** (1-64), SEL + K4 its **PUSH** (0-4
  16ths early: the house chord that comes before the bar). Five slots: USER 1-4 and **DICE/PI**.
* **When the chords change** (SEQ 4, SEL + K4 RHYTHM): BARS (a chord every so many bars, K3, as 0.10), **GENRE** (the
  genre's own: house and garage push a 16th, reggaeton and dancehall 3+3+2 ...), PUSH 16TH, PUSH 8TH, **3+3+2** (6, 6
  and 4 16ths: three chords a bar), TWO A BAR, 3+5, 3+1, 2 BARS. The changes keep their places in the bar: a rhythm of
  2 or 3 lengths is laid over the chords until both come round together (3+3+2 over four chords: four bars). The
  harmony can change on any 16th.
* **FOLLOW: HOLD, RETRIG, LEGATO** (SEQ 4, SEL + K1, for the selected track): a note held across a change of chord
  keeps its chord (HOLD, 0.10), is struck again on the new one (RETRIG), or slides to it (LEGATO: the new notes start
  before the old ones end, the notes the two chords share go on; a mono synth glides).
* **Ten moods**: SAD, MELANCHOLY, SATISFYING, ENERGETIC, EUPHORIC, EPIC, DREAMY, DARK, TENSE, SUSPENDED. Every
  progression has one: the one you give it (SEQ 8, SEL + K1), or the machine's guess from what it is (minor chords, the
  borrowed bVI and bVII, the V-I cadence, the sevenths and ninths, the sus, the tritone, how fast it moves). **MOOD**
  (SEQ 4, SEL + K3) filters K2: it goes only through the progressions of that mood (`NO MORE EPIC` at the end).
  **DICE PROG** (SEQ + SEL + black 1): a new progression of the mood into DICE/PI, playing at once.
* **The Pi's progressions** (with the grid bridge): SEQ 4 K2 past the FM-1's last goes on into the Pi's, those of the
  harmony's genre and of the MOOD, **the most like the one that was playing first** (`PI EPIC 3/8: i-bVI-bVII-i`);
  each comes into DICE/PI and plays; K2 back below the first returns to where you were. **SEQ + SAVE on SEQ 4** sends
  the progression playing to the Pi, **on SEQ 8** the one you are writing, with its mood. The Pi starts with 701 (a
  file a genre, by mood, coloured the genre's way); the hub page lists, adds (typed as `i bVI bVII i`, `ii7:8 V7:8
  Imaj7^1`) and deletes them.

**The library, the band, COOK**

* **A band for each genre**: 8 to 11 parts (TECHNO: kick, clap, hat, open hat, ride, perc, rumble, bass, stab, pad;
  AMAPIANO: kick, clap, shaker, hat, rim, perc, log drum, bass, piano, pad, vox ...), from **25 roles**: the 0.10 seven
  and CLAP, OPEN HAT, RIDE, SHAKER, CONGA, TOM, RIM, CRASH, COWBELL, RUMBLE, SUB, LOG DRUM, STAB, PAD, PIANO, LEAD, VOX
  (HOME 4 K2). **BAND** puts the formation on the tracks you gave those roles, else on free tracks (empty ones first);
  **it never changes a track's channel**, and changes its note only on a track with nothing written on the default
  note. SEQ + SELECT goes through the genre's parts, PROG and KIT.
* **12 variations of a main part, 6 of the others, in order of likeness**: the first is the most typical, each next one
  the closest to it, the density rising, the odd ones last. **COOK on a library track walks towards the next
  variation** (HEAT steps a press: the weak 16ths first, the bar's one last; locked steps kept), `COOK KICK #3: 2 TO
  GO`, then `REACHED`, then on to the next. **SEQ + SEL + COOK** (grid: SHIFT + COOK) is the random COOK of 0.10.
* **The Pi keeps more variations** (with the grid bridge): SEQ + ALG past the 12th (or 6th) goes on into the Pi's
  (`#14/12+PI`), BEAT loads one; **SEQ + SAVE** sends the selected track's loop to the Pi as a new variation of its
  part. The Pi starts with the next 12 / 6 of every part; the hub page lists and deletes them.
* **Notes of their own length.** The library's patterns hold notes (a pad a bar, a bass that rings to the next hit);
  RANDOM, EUCLID and the dice give melodic notes lengths by role; a melodic track whose rhythm an algorithm makes holds
  each note to the algorithm's next hit.
* **Hold a step and press another: the note between them** (both counted: steps 3 and 6 make a note of four steps; the
  grid's STEP view too). **FX tapped first** (pressed and let go alone): the same gesture is the step loop of 0.10.

**The algorithms**

* **Four algorithm slots a track** (SEQ 2): SEL + K1 picks the slot (ALGO 1-4), K1 its algorithm, K2-K4 its
  parameters. They run in order on every step: a rhythm algorithm (TURING, CELL) replaces the hits so far, DENSITY
  thins or fills them, the ACCENTs add up. WRITE LIVE writes them down and keeps the ACCENTs. The grid's TRACK 3 view
  works on the slot shown; pad 8 of its algorithm row goes to the next slot.

Fixed: with -O2 a DENSITY slot read a flag that VIAGGIO had not set, and on some builds a step with a condition (1:2,
FILL) played anyway at velocity 1.

## What is new in 0.10

0.10 starts the project format over (**SGQA**): a 0.10 project does not load on a 0.9, and 0.10 does not read SGQ3 ..
SGQ9 projects (the bridge, the hub and the converter say so). The panel was laid out again from what a month of 0.9
taught: the second part of this list is that rework.

* **EXPO** (SEQ pages 5 and 6): a track's rhythm as an exponential curve. K4 SHAPE: OFF, RAMP (the hits get closer or
  further apart along the span), BOUNCE (fast in the middle), SETTLE (exposaw's law: a retrigger whose period follows
  an envelope). K1 HITS 2-64 (SETTLE: the RATE a beat), K2 CURVE -8..+8 (SETTLE: DEPTH), K3 SPAN (STEP, BEAT, 2 BEATS,
  BAR, 2 BARS, 4 BARS); page 6: VEL (FLAT, FALL, RISE, BOUNCE, GRACE: the first hit at 75 %), GATE 5-100 %, JITTER 0-50 %, NOTES (CHORD, ARP, ARP +1..+3
  octaves). A step that is ON starts a span and gives it its notes; inside a span the other steps are silent. Turning
  K1-K3 switches it on (RAMP). **EDIT + black 5** makes the cursor step **PLAIN**: a span that begins on it plays its
  steps as written, no curve, so a pattern can mix curves and plain beats. With VIAGGIO on, the **energy** halves or
  doubles the hits (0 / 100).
* **REC keeps the length**: a note played while recording (keys or MIDI in) gives its step the gate it was held, or the
  steps (1.5 .. 64) when held longer. REC FREE (SEL + REC) keeps the timing as before, at 1 % of a step.
* **DELAY** (HOME 6/7 K1): a track's notes up to 30 ms early or late, for a synth's latency (early: a slow synth).
* **BEND and AFTERTOUCH**: a lane's number or an LFO's CC number turned past 127 reads BEND (128: pitch bend, 64 the
  centre) or AFTERT (129: channel aftertouch). STOP and PANIC put them back.
* **UNDO goes back through the last edits** (16 pattern rows of them); **REDO** is SEQ + SEL + UNDO (grid: SHIFT + the
  UNDO pad). A new edit drops what could be redone.
* **CHAIN** (HOME 6/7 K2): the pattern and its partner (1+2, 3+4, 5+6, 7+8) play one after the other: 128 steps.
* **TAPE tracks** (HOME 3/7 K4: FREE, IN KEY, DRUM, **TAPE**): a track that keeps what is played with its timing, 384
  ticks a beat, in a loop of 1-16 bars (HOME 6/7 K3) instead of steps. REC overdubs onto it with the length held; REC
  QUANTISED puts the start on the 1/16. **TAPE QUANT** (HOME 6/7 K4, 0-100 %) pulls the starts to the grid as it plays,
  the tape untouched. Tools: CLEAR, SHIFT < >, DOUBLE. The grid's STEP view is the loop: 64 pads, a pad per 1/64 of it;
  tapping a pad erases what starts under it; row 5 the bars, row 6 the quant, row 8 the tools. 1536 notes in all.
* **On the Pi** (the hub page, port 8090): every project of the library downloads as a **.mid**, a .mid uploads as a
  project of TAPE tracks, and a **piano roll** in the browser edits the TAPE tracks of a project and saves it back.
* Fixed: ghost hits on a drum track played C4 (0.9.1).

The rework (the 0.9 manual with a month of notes on it):

* **Everything lands in time.** A track is where the bar says it is: after a length or a division changed (and changed
  back), after HALF / DOUBLE / REVERSE / FREEZE / RANDOM are let go, after a LOOP, a REPEAT or a step loop ends, the
  pattern plays the step the clock points at, never shifted. A **step loop** (hold a step, press another) remembers the
  length it replaced: **EXIT** (FX + black 11) puts it back, in time.
* **One genre** for the machine (SEQ + PRESETS, the BEAT view, HOME 8 K3): the library, the progressions and VIAGGIO's
  proposals all come from it. **24 genres**: BREAKBEAT, TRAP, MINIMAL and LO-FI are gone, **UK DRILL**, **HARDCORE**,
  **PHONK** and **BAILE FUNK** are in. **GENRE mode** (SEQ 7 K4): FREE (the generators ignore the genre: COOK and the dice are plain), ON (they mind
  it: the default), **LIVE** (a change of genre reloads, at the next bar, every track that came from the library, with
  the same function and variant: the whole band changes colour on the bar line). The library has **16, 32 and 64-step
  patterns** (SAVE page 2 K4 LIBRARY: 16 / 32 / 64 STEPS tiles the shorter ones with their variants and a fill).
* **BAND** (SEQ + SEL + black 7; grid: SHIFT + the KIT pad): the whole genre at once: KICK SNARE HAT PERC BASS CHORD ARP
  and PROG on eight tracks, each on the track that has that **role** (HOME 4 K2), else on the eight of the bank.
* **Roles** per track (HOME 4 K2: KICK SNARE HAT PERC BASS CHORD ARP, or none: by its note). **COOK** cooks by role (a
  kick keeps its beats and gets pickups, a snare ghosts and rolls, a hat opens and ratchets, a bass keeps the root on
  the beats and moves by fifths and octaves ...), BAND and VIAGGIO's proposals follow it.
* **Tools that wait, tools that repeat** (SEQ page 7 TOOLS): **WHEN** (NOW, or at the next 1, 2, 4, 8, 16 bars: a tool
  pressed while playing waits for that bar line, the screen says `CLEAR IN 2 BARS`), **EVERY** (OFF, 1 .. 32 bars: the
  last schedulable tool runs again every so many bars; COOK every 4 bars is a slow evolution you can hear coming).
  The random density moved here (K1).
* **Rhythm families** (SEQ 1 K3): EUCLID, **TRESILLO** (3-3-2 cells), **NUMERIC** (the binary of the n-th prime): the
  same pulses, another rhythm. **16 conditions**: + 1:3, 2:3, 3:3, 1:8, FIRST (the first loop after PLAY), **PRE** (after
  a step that played) and **!PRE**.
* **Chords and arpeggios.** **CHORD** (HOME 4 K3; ARP page 2): one written note becomes a chord of up to **six notes**,
  from **32 shapes**: OCTAVE, POWER, 5-8, MAJOR, MINOR, DIM, AUG, SUS2, SUS4, MAJ6, MIN6, DOM7, MIN7, MAJ7, MINMAJ7, DIM7,
  M7B5, 7SUS4, ADD9, MINADD9, DOM9, MIN9, MAJ9, 9SUS4, 6/9, MIN6/9, MIN11, DOM13, SHELL7, MINSHELL, 1-3-5-8 (the chords
  the genres live on: the m7 / m9 / 9sus4 of house and garage, the stabs of techno, the maj7 of amapiano ...). On a
  track IN KEY the **KEY** mode (ARP page 2 K2) says how the shape meets the scale: **DIATONIC** builds it on the scale
  (the quality follows the step: MAJOR on D in C major gives D minor), **FREE** keeps the exact shape (the quality you
  asked for, notes out of the key allowed: D major in C major), **STRICT** keeps the shape and silences the notes that
  fall out of the key (D major in C major plays D and A). A FREE track always plays the exact shape. ARP page 1:
  mode, octaves, **RATE** (ROLL: the chord inside the step, as 0.9; 1-4 notes a step: the arpeggio runs on through the
  empty steps while the chord's gate lasts), **RUN** (OFF, RETRIG: a new chord starts it from its first note, HOLD: it
  runs on to the next chord, HOLD+RT). A written step still holds four notes; a shape plays six.
* **TIE** (EDIT + black 6; grid SHIFT + row 7 pad 16): the step's note holds into the next step, legato (the next note
  starts before it ends).
* **Gate to 64 steps**: the grid's long gates row goes 1.5, 2 .. 6, 8 .. 16, 20 .. 64 (SHIFT: 17 .. 32).
* **The pen**: SEL + K4 chooses the note first; K1 on a step that is off changes its note and the pen, plays a preview
  and does not light the step; a step switched on takes the pen.
* **Transpose in the key** (HOME 1 K4): on a track IN KEY it counts steps of the scale (-24 .. +24), on a FREE track
  semitones. **OCTAVE** per track (HOME 2 K3; live: PERF held + OCT- / OCT+). PERF K3 TRANSPOSE moves the key itself
  (root and shift together), so everything in key moves together.
* **Sixteen keys** (HOME 3: K1 the SLOT 1-16, K2 root, K3 scale, K4 shift). A track plays in the slot that is current,
  or is **pinned** to one (HOME 4 K4); scenes and snapshots bring their slot back. The grid's PROJ rows edit the current
  slot.
* **Six CC lanes, one a page** (ENV + OCT- / OCT+): K1 the lock on the step (from the base, or 64), K2 the CC (SEL + K2
  the NRPN MSB), K3 the base, K4 the mode: NORMAL, **SLIDE** (the value glides from lock to lock, on silent steps too),
  **TRIGLESS** (a lock is sent on a silent step), **NRPN** (99 MSB, 98 LSB = the CC number, 6 the value). **Recording a
  lane**: with REC on, ENV held and K1 turning write the knob onto the steps as they play. **CC LEAD** (SAVE page 2 K1):
  the locks go out up to 30 ms before the notes (a synth that needs the filter set before the note). **LEARN** (ENV +
  REC) takes the CC's value as the base and names it for the channel's **DEVICE** (SAVE page 2 K3: GENERIC, ELEKTRON).
* **User progressions** (SEQ page 8: which of 4, the chord 1-8, its step i .. vii or `--` to end, its colour): HARMONY
  (SEQ 4 K2) plays 1-6 the genre's or USER 1-4; VIAGGIO's row 7 and PRESETS reach them too.
* **The macros are saved** with the project; FX + OCT- puts them to 0 (and the MASTER knob with them); **FX + ARP twice
  BAKES** them into the patterns (velocities, gates, swing, the bases of lane 1) and zeroes them.
* **PANIC is FX + HOME**: sustain up, All Notes Off and All Sound Off on every channel, paced so the USB never drops
  them; pressed again within 2 s it stops the transport too. A plain STOP sends All Notes Off and lifts the sustain,
  and leaves the synths' tails. **ECHO ALL** (FX + OCT+) off cancels the repeats that were waiting.
* **The song sets the tempo** (SAVE page 2 K2): each entry remembers the BPM it was added at.
* **VIAGGIO** works with all 24 genres (the ladders are the library's); you choose each track's **role** (K3) and
  **channel** (K4) in VIAGGIO mode; a tap on a PROPOSED track browses, the hold throws the dice, ALG goes through the
  proposals (`T1 KICK P4 (3/3)`); **MOVES AT** (K2): the phrase boundary, every bar or every beat; a new GENRE waits for
  the boundary while playing and the proposals keep their own settings per slot.

## What is new in 0.9

0.9 reads the projects and library files of 0.8 (SGQ8) and saves SGQ9. Nothing of 0.8 was taken away.

* **VIAGGIO** (SEL + PERF): the set as a journey. Time is cut into **phrases** of 16 bars (8 or 4); what you ask for
  waits in a **queue** and happens together at the phrase's end, so the hands are free to prepare the next one. A tap
  on an empty track makes a **proposal** for it from the library of the genre (the hold: the dice); SEL + the key puts
  it in at the boundary; a track that plays is never silenced by a tap. The black keys are the **moves**: FILL, BREAK,
  RISER, DROP, HALF, DOUBLE, THIN, SWELL, SWAP, LOOP (a phrase recorded by hand), NOW (the queue at the next bar).
  **ENERGY** 0-100 (K1) moves velocity, filter, gate, density, the LFOs' depth and the chords' colour together, and
  glides over the phrase. Five **set genres** (LOFI DEEP, DUB TECHNO, HARDTECHNO, DUBSTEP, JUNGLE DNB) with a ladder of
  roles and, for the bass genres, an AFRO / LATIN percussion family. Every phrase goes into the **trail** (128):
  OCT- goes back, SAVE + white 16 turns the journey into scenes and a song. See "VIAGGIO" below.
* **Profiles** (SAVE + K4): **FULL** (everything, as 0.8) or **PALCO** (the stage: VIAGGIO from power-on, the panel
  plays the set and does not edit steps, HOME shows only the KEY and VIAGGIO pages, the remote on 13 + 14). Kept in
  the FM-1's settings.
* **The remote on channel 13** too (SAVE + K2: OFF, CH 14, 13 + 14): the VIAGGIO commands. CC 3 on channel 14 is the
  energy.
* **The regista** (SysEx 50-55): a program on the Pi can follow the set (bar, scene, key, chord, phrase, energy) and
  write a phrase onto a track at the next bar; the grid gets a REGIA view for its rules.
* **16 scenes, 64 song entries.** The panel's black keys reach the 8 scenes of the bank the PERF cursor is in (PERF +
  PRESETS moves the cursor 1-16); the grid's scene buttons the same; the SONG view pages its entries 16 at a time.
* **A save keeps what plays**: the pattern of every track, the mutes and the scene come back at power-on as they were.
* Fixed from 0.8: with two USB ports the LFOs' CCs, the scenes' Program Changes and MIDI LEARN reached only channels
  1-14; a wholesale mute (scene all-on / only / invert) left queued mutes behind; LEARN waiting survived a project
  load; an external STOP was handled twice; a snapshot that changed a track's pattern kept the step decided for the old
  one.

## What is new in 0.8

0.8 does not read the projects of 0.7 or older (their slots are ignored; the library files of the Pi are refused):
the format was redone for 0.8's features (SGQ8).

* **The live layer, per track.** **EUCLID LIVE**: turn SEQ + K1 / K2 and the track plays that Euclidean rhythm at once,
  over what is written (the notes, velocities, CC locks of the steps stay); each track its own pulses and rotation.
  Then an **ALGORITHM** per track (SEQ page 2): **TURING** (a looping or drifting register: the rhythm, the notes or
  both), **CELL** (a cellular automaton: a new generation every 1, 2, 4 bars or every loop), **ACCENT** (velocity
  patterns: beat, offbeat, 3 against 4, 3+3+2, random), **DENSITY** (fewer hits, or more: ghost notes). The step LEDs,
  the screen's strip and the grid show **what you hear** (cyan: a hit the live layer adds). **WRITE LIVE** (SEQ +
  white 7) puts what you hear into the pattern and switches the layer off; UNDO takes it back. Turning an algorithm's
  knobs never starts it again: only choosing another algorithm does.
* **HARMONY.** Each genre has six chord progressions with colours (7th, 9th, sus4, sus2, 6th). Turn HARMONY on (HOME
  page 2 K4, SEQ page 4) and the tracks with **FOLLOW** move to the chord that plays: write a bass line, an arp or
  chords on the tonic, they play I, VI, III, VII ... PROG writes the tonic chord and turns FOLLOW and HARMONY on. The
  chord's name is on the screen.
* **SNAPSHOTS.** Eight memories of the live state: which patterns play, mutes and solos, the macros, the key and
  TRANSPOSE, the harmony, every track's settings (channel, loop, swing, MIDI FX, EUCLID, algorithm, CC lane bases),
  the LFOs, the tempo if you want. They come back at the QUANTISE moment. Their **sound** goes with them: the CC lanes'
  base values, and the synths' own CC values that **CC CAPTURE** took while you turned the synths' knobs. **PATCHES**:
  the Raspberry Pi keeps the synths' patches (SysEx) for a snapshot and sends them back when it returns.
* **MIDI FX per track** (HOME page 5): HARM (a second voice, steps of the key), OCTAVE (jumps on alternate / random /
  every 3rd / 4th step), ECHO (1-4 repeats, 1/32 .. 1/4 dotted, how much each keeps), VEL CURVE. **FX + OCT+**: an ECHO
  on every track at once.
* **The dice remember**: up to 16 rolls; while a dice waits, **ALG** goes back and forth through them (each one exactly
  as it was), OCT+ keeps the one you hear, OCT- puts everything back.
* **Every knob returns to 0**: values that move by 2, 4 or 5 a detent snap to those steps, so 0 (and every round
  value) is always reached; a fast turn moves 2x then 4x, a slow turn and every turn back one step a detent.
* **24 genres**: + ELECTRO, BREAKBEAT, DRUM+BASS, TRAP, AFRO HOUSE, AMAPIANO, FOOTWORK, MINIMAL, TRANCE, LO-FI.
* **USB PORTS 2** (the USB page): the FM-1 shows two MIDI ports. Port 1: the synths, **16 channels** for the tracks;
  port 2: the grid, the remote and the Pi's SysEx. With one port (the default) channels 15 and 16 stay the grid's.
* **EDIT + black 1: STEP LOCK**: EVOLVE and the dice leave that step alone.
* **Grid**: EUCLID view (BEAT again), TRACK 3 view (TRACK 2 again), the BEAT view rebuilt, FX view: snapshots,
  capture, send, patches, the global ECHO.
* Fixed from 0.7: STOP and PANIC cancel the echoes and strums waiting; a mute or a KILL cuts a long note at once; the
  live algorithms stay on their track; a full chord with strum and echo never loses a chord note; EVOLVE uses a
  progression only with HARMONY; the CELLS knob works; STACCATO is short on ratchets too; the macros turn fast.

## The FM-1 panel

The rule: **the button you hold says what you work on; the white keys pick, the black keys act, the knobs set**.
OCT- / OCT+ with a button held turn that button's pages (the page is remembered). **0.12: a tap on HOME, SEQ, EDIT, ENV,
LFO, ARP or FX opens its window** - the button counts as held until the same tap closes it or another window opens;
a button really held wins meanwhile. The rows below read the same way for a window.

| held | white keys 1-16 | black keys 1-11 | K1 K2 K3 K4 |
|---|---|---|---|
| nothing | the steps (**0.11: hold one, press another: the note between them**; **SEL + FX** tapped first (0.12; FX alone in 0.11): a step loop between them, EXIT puts the length back) | 1-8 track of the bank, 9 other bank, 10 mute, 11 solo | note (an off step: its note and the pen, a preview, not lit), velocity, chance, ratchet of the cursor step |
| SEL | the keys are notes for the cursor step (within 0.45 s: a chord of up to 4) | (notes) | velocity offset, humanise timing, humanise velocity, **pen note** |
| **a group + SEL** (0.12) | **PICK**: the key is the value of the knob in focus (lists, lengths, roots, semitones, percentages: see PICK) | 1-10 items 17-26; **11: the focus to the next knob** | |
| HOME | **track 1-16** | as with nothing held; in PERF: the song (1-8 add a scene, 9 loop, 10 take the last away, 11 clear) | see HOME pages (8) |
| EDIT | the cursor to that step (not switched) | **1 STEP LOCK**, 2 COPY, 3 PASTE, 4 CLEAR the step, **5 PLAIN** (no EXPO from this step), **6 TIE** (legato into the next step), **7 SLIDE** (0.13: TIE, and the next note glides: CC 65) | gate (1 % .. 100 %, 1.5 .. 64 STEP), condition (16), nudge, ramp; **SEL + K1-K4 (0.12): the step's four notes** (a knob below the first: the note taken away) |
| ENV | the cursor to that step | | **one lane a page (OCT- / OCT+: lanes 1-6)**: K1 the lock on the step, K2 the CC number (SEL + K2: the NRPN MSB), K3 the base, K4 the mode NORMAL / SLIDE / TRIGLESS / NRPN |
| LFO | that LFO on / off | | page 1 shape, rate (**0.13: then 1/4T 1/8T 1/16T 1/32T**), depth, centre; page 2 destination, target, CC, phase; page 3 on, retrigger, invert, **TRIG** (0.13: CLOCK or T1-T16, the sidechain); **page 4 RATE SEQ** (0.13): steps, every, position, its rate |
| SEQ | the 16 tools (WHEN / EVERY: when they happen; **0.12: UNDO held 0.6 s = REDO, COOK held = the random COOK**; the tap acts when the key is let go) | dice SEQ CC LFO GROOVE ALL (**0.12: black 1 held = DICE PROG**), SCOPE, KIT (**held: BAND**), DRIFT, EVOLVE, FREEZE, REVERT | see SEQ pages (7) |
| FX | the 16 effects while held | 1-8 LOOP (tap) / REPEAT (hold) 1/32 .. 4 bars, 9 RESTART, 10 STOP at the bar, 11 EXIT (a DJ loop, or the step loop of the selected track; SEL also held: the selected track only) | INTENSITY, GATE, SWING, FILTER (the macros, saved); **SEL + K1-K4 (0.12): the THROWS** (the same four, gliding back to 0 over a bar); FX + OCT-: to 0; FX + OCT+: ECHO ALL; **FX + ARP twice: BAKE**; **FX + HOME: PANIC** |
| ARP | **0.12: the keys play the selected track** (its notes, a drum's hits), REC on: written; **on a BREAK track: the chops 1-16** (tapped: stays; held: while held, then back) | on a BREAK track: 1 ROLL, 2 ROLL 1/32 (held), 3 HALF, 4 DOUBLE, 5 BACKWARDS, 6 DICE, 7 RESET, 8 / 9 the chop after / before; **on a DRUM track, playing (0.13): 1-4 NOTE REPEAT 1/16, 1/32, 1/32T, 1/8 of the white held**; else the keys play | see ARP pages (6) |
| SAVE | slot 1-8; **white 16: SALVA VIAGGIO** | **1-8 SNAPSHOT** (SEL also held: store), **9 CC CAPTURE, 10 SEND, 11 PATCHES** | see SAVE pages (4); PRESETS: the slot |
| GLO (PERF) | **0.12: mute 1-16 in any mode** (PERF: SEL + OCT+ first: solo, SEL + OCT-: mute) | scenes 1-8 of the cursor's bank (SEL: store), 9 all on, 10 only the selected, 11 invert | see GLO pages (3); PRESETS: the scene cursor 1-16; **GLO + OCT- / OCT+ (PERF: OCT- / OCT+ alone): the pages; GLO + SEL + OCT- / OCT+: the track's octave** |
| **VIAGGIO** (SEL + GLO) | the tracks (tap: a proposal / browse; hold: the dice; SEL + key: in / out at the boundary) | the moves (below) | K1 the energy, **K2 MOVES AT** (phrase, bar, beat), **K3 the track's role**, **K4 its channel**; ALG the proposals of the selected track; SEL + ALG the tempo; PRESETS the progression (queued) |

A group **held half a second** with nothing else shows the map of its keys on the screen's message lines, and what
SEL + a key does for the knob in focus (in a window the map stays four seconds, then the key and genre lines come back).

### HOME pages (OCT- / OCT+ with HOME held)

| page | K1 | K2 | K3 | K4 |
|---|---|---|---|---|
| 1 TRACK | MIDI channel (1-14; 1-16 with two USB ports) | length 1-64 (playing: at the bar; longer: the new steps filled with the loop) | step: 1/1 .. 1/32T | transpose: IN KEY -24 .. +24 **steps of the scale**, FREE -48 .. +48 semitones |
| 2 PLAY | direction FWD REV PING RND | swing 50 % (straight) .. 75 % | **OCTAVE** -3 .. +3 | **FOLLOW** the harmony |
| 3 KEY | **SLOT** 1-16 (the key that plays) | root | scale | shift -24 .. +24 |
| 4 MODE | mode: FREE / IN KEY / DRUM / TAPE / **BREAK** (0.12: a track of slices) | **ROLE**: none, KICK SNARE HAT PERC BASS CHORD ARP, CLAP OPEN HAT RIDE SHAKER CONGA TOM RIM CRASH COWBELL RUMBLE SUB LOG DRUM STAB PAD PIANO LEAD VOX | **CHORD**: OFF, or one of 32 shapes (ARP page 2 has it too, with the KEY mode) | **KEY**: follows the slot that plays, or pinned to slot 1-16 |
| 5 LOOPS | the notes' loop | the velocities' loop | the gates' loop | the program of the track's channel in the PERF cursor's scene |
| 6 MIDI FX | effect: OFF HARM OCTAVE ECHO VEL | amount | time (ECHO) / which steps (OCTAVE) | how much each keeps (ECHO) / its velocity (HARM) |
| 7 TIMING | DELAY -30 .. +30 ms | CHAIN **OFF / P1+2 / LIST** (0.13) | TAPE BARS 1-16 | TAPE QUANT 0-100 % |
| **8 CHAIN LIST** (0.13) | LENGTH 1-8 entries | ENTRY (the one the knobs set) | its PATTERN 1-8 | how many TIMES 1-8 |

(VIAGGIO's knobs, HOME 8 until 0.11, are **GLO 3**.)

MIDI FX amounts: HARM -7 .. +7 steps of the key (a FREE track: -12 .. +12 semitones); OCTAVE -2 .. +2 octaves, on
ALT (every other step), RANDOM, 3RD, 4TH; ECHO 0-4 repeats, every 1/32, 1/16, 1/8T, 1/16 dotted, 1/8, 1/4T, 1/8 dotted
(the default), 1/4, each keeping 10-100 % of the velocity of the one before; VEL -8 .. +8 (soft .. hard). The
effect's notes are ornaments: STOP, PANIC, a mute or a KILL cancel the ones waiting.

### SEQ pages

| page | K1 | K2 | K3 | K4 |
|---|---|---|---|---|
| 1 EUCLID | pulses (this track, live) | rotation (live) | **FAMILY**: EUCLID, TRESILLO, NUMERIC | heat (COOK, the dice) |
| 2 ALGORITHM | OFF TURING CELL ACCENT DENSITY (the slot shown; **SEL + K1: the slot 1-4**) | A | B | C |
| 3 EVOLVE | targets RHYTHM .. ALL | amount | every 1 2 4 8 16 bars | scope |
| 4 EXPO | HITS 2-64 (SETTLE: RATE a beat) | CURVE -8 .. +8 (SETTLE: DEPTH) | SPAN STEP, BEAT, 2 BEATS, BAR, 2 BARS, 4 BARS | SHAPE OFF, RAMP, BOUNCE, SETTLE |
| 5 EXPO 2 | VEL FLAT, FALL, RISE, BOUNCE, GRACE (the first hit at 75 %) | GATE 5-100 % | JITTER 0-50 % | NOTES CHORD, ARP, ARP +1 .. +3 OCT |
| 6 TOOLS | random density 0-100 % | **WHEN**: NOW, BAR, 2, 4, 8, 16 BARS | **EVERY**: OFF, 1, 2, 4, 8, 16, 32 BARS | **GENRE**: FREE, ON, LIVE |
| **7 BREAK** (0.12) | **CHOP**: the re-order written over the loop (16, one a white key: STRAIGHT .. BUILD; UNDO takes it back) | **ROLLS** 0-7: how many steps the dice rolls | **SWAP** 0-100 %: how much of the bar the dice re-orders | **SLICES** 8 / 16 / 32 |

(The harmony, SEQ 4 and SEQ 8 until 0.11, is **ARP 3-6**.)

| algorithm | A | B | C |
|---|---|---|---|
| TURING | mutation 0-100 % (0: a locked loop) | length 2-16 steps | moves the RHYTHM, the NOTES (0-7 steps up the key), or BOTH |
| CELL | rule 0-255 (90, 30, 110 ...) | cells 4-64 (the row repeats every so many steps) | a new generation every 1, 2, 4 bars, or every loop |
| ACCENT | BEAT, OFFBEAT, POLY3, SYNC 3+3+2, RANDOM | amount 0-63 | offset 0-15 steps |
| DENSITY | 0-200 % (100: as written; under: fewer, the beat last; over: ghost notes added) | the ghosts' velocity 10-100 % | |

Turning EUCLID's knobs switches EUCLID LIVE on for the track. SEQ + white 6 switches it on / off (on the scope). A new
algorithm starts from the written rhythm; its knobs never restart it. The families: EUCLID spreads the pulses as evenly
as they go (E(5,16) = x..x..x..x..x...); TRESILLO fills 3-3-2 cells, half a bar at a time; NUMERIC writes the binary
digits of the n-th prime number (n = the pulses): a rhythm that is neither even nor random.

WHEN and EVERY apply to the tools that change a pattern (CLEAR, REVERSE, SHIFT, RANDOM, COOK, BEAT, PROG, PASTE,
DOUBLE, INVERT, HUMANIZE; not UNDO, WRITE LIVE, EUCLID LIVE, COPY). With WHEN on BAR a tool pressed while playing waits
for the bar line (the screen counts the bars); EVERY repeats the last tool used every so many bars from the next one.

### SEQ held: keys

| | |
|---|---|
| white keys 1-16 | CLEAR, REVERSE, SHIFT <, SHIFT >, RANDOM, **EUCLID LIVE on / off**, **WRITE LIVE**, UNDO (a dice waiting: BACK; **held 0.6 s: REDO**), COOK (by the track's role; **held: the random COOK**; on a BREAK: the next chop of the library's genre, held: one of them at random), BEAT, PROG, COPY, PASTE, DOUBLE, INVERT (on an empty row: all on), HUMANIZE. UNDO, COOK, DICE SEQ and KIT act when the key is let go. On a TAPE track: CLEAR, SHIFT <, SHIFT >, DOUBLE |
| black keys 1-11 | DICE SEQ (**held: DICE PROG**; on a BREAK: the backbone kept), DICE CC, DICE LFO, DICE GROOVE, DICE ALL, SCOPE (next; held + white keys: the CUSTOM tracks), KIT (**held: BAND**), DRIFT, EVOLVE on / off, FREEZE, REVERT |
| SELECT / ALG / PRESETS | BEAT part (the genre's band, PROG, KIT) / variation 1-12 (1-6), **then the Pi's** / **the genre** (of everything; the harmony follows only what is loaded) |
| SAVE | **the selected track's loop to the Pi** as a variation of its part (**ARP + SAVE**: the progression, the one being written on ARP 5 / 6, else the one playing) |

BEAT on one track loads the part chosen at the LIBRARY length (KIT: the genre's drums; they become drum tracks; BAND:
the genre's whole band, on the tracks with those roles, else on free tracks; channels are kept); pressed again, the
next variation. A BASS or ARP loaded while HARMONY is on gets FOLLOW. A loaded track remembers where it came from:
GENRE LIVE reloads it from the new genre at the bar line. The tools apply to the scope (the screen says on how many
tracks).

### Other controls

| control | does |
|---|---|
| PLAY | start / stop. SEL + PLAY: continue. HOME + PLAY: master / slave clock |
| REC | tap: arm (the keys and incoming notes are played and recorded, with the length held; stopped: step recording; a TAPE track: overdub). **Held 0.6 s (0.12): TAKE**, what was played in the last loop of the selected track into its pattern. SEL + REC: quantised / free. HOME + REC: tap tempo. ENV + REC / LFO + REC: LEARN the CC number. **0.13: with MOTION on (SAVE 4 K1), REC writes the macros' moves too**; MIDI IN ALWAYS (SAVE 4 K4): the incoming notes play without REC |
| ARP | **tap (0.12): its window** (the keys play the track until the next tap; a BREAK: the chops on the whites, its moves on the blacks); **SEL + ARP tapped: the arpeggio on / off** (the tap alone in 0.11). HOME + ARP, twice: BAKE the key into the patterns. **FX + ARP, twice: BAKE the macros**. **ARP + SAVE: the progression to the Pi** |
| HOME, SEQ, EDIT, ENV, LFO, FX | **tap (0.12): the window** of the button (closed by the same tap, or by another window; a button really held wins). **SEL + FX tapped: the next two steps are a LOOP** (FX alone in 0.11) |
| OCT - / + | page of 16 steps; SEL: octave of the keys; HOME / ENV / LFO / SEQ / ARP / SAVE / **GLO** held, **or their window open**: the pages. A dice waiting: OCT+ keeps it, OCT- puts it back. **FX + OCT-: the macros to 0. FX + OCT+: ECHO ALL on / off** (off: the repeats waiting go too). **GLO + SEL held: the track an octave down / up**. **PERF: GLO's pages; SEL + OCT-: the white keys mute, SEL + OCT+: solo** |
| SELECT encoder | the track (LFO held: the LFO; SEQ held: the BEAT function) |
| ALG encoder | the cursor; **a dice waiting: the rolls**; SEL + ALG: tempo; HOME + ALG: loop start; SEQ + ALG: BEAT variation |
| PRESETS encoder | the track's pattern (queued while playing); PERF: the scene cursor; SAVE + PRESETS: the slot; SEQ + PRESETS: the genre |
| GLO | a tap: PERF on / off - **its window** (another window tapped leaves it; SEQ pressed leaves it). Held: its pages' knobs and the PERF keys. HOME + GLO: the song on / off. **SEL + GLO (0.12): a tap switches the keyboard between VIAGGIO and the studio, the journey going on (the first time it starts it); held 0.6 s: the journey off** |
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

### ARP pages (0.12: the notes, the chords, the harmony)

| page | K1 | K2 | K3 | K4 |
|---|---|---|---|---|
| 1 ARP | mode (13: BLOCK, UP, DOWN, UP-DN, DN-UP, UP&DN, CONV, DIV, RND, WALK, PLAYED, THUMB, PINKY) | octaves 1-3 | **RATE** | **RUN**: OFF / RETRIG / HOLD / HOLD+RT |
| 2 CHORD | **shape** (32) | **KEY**: DIATONIC / FREE / STRICT | voicing | strum |
| 3 HARMONY | **OFF / ON / LOCK** | progression 1-6 of the genre, USER 1-4, DICE/PI, **then the Pi's** (of the MOOD) | bars a chord: the progression's own, 1, 2, 4, 8 | FOLLOW this track |
| 4 HARMONY 2 | **FOLLOW**: HOLD, RETRIG, LEGATO (this track) | **the harmony's genre** | **MOOD**: ANY, SAD .. SUSPENDED | **RHYTHM**: BARS, GENRE, PUSH 16TH, PUSH 8TH, 3+3+2, TWO A BAR, 3+5, 3+1, 2 BARS |
| 5 USER PROG | the progression USER 1-4, DICE/PI | the chord 1-8 | **its root**: I bII II bIII III IV #IV V bVI VI bVII VII, or `--` (the progression ends before it) | **its shape**: the key's chord with a colour (TRIAD, 7, 9, SUS4, SUS2, 6), then the chord shapes OCT .. 1-3-5-8 |
| 6 USER PROG 2 | **MOOD** (GUESSED: the machine's) | the lengths of a RHYTHM written into the chords | **the chord's length**: 1-64 16ths (0: the HARMONY's rhythm) | **PUSH** 0-4 16ths |

### GLO pages (0.12: the live; GLO + OCT- / OCT+, or tap GLO for PERF: OCT- / OCT+ alone turn them)

| page | K1 | K2 | K3 | K4 |
|---|---|---|---|---|
| 1 LIVE | MORPH | MORPH TO (the scene) | TRANSPOSE (the key) | QUANTISE |
| 2 TRACK LIVE | the track's pattern (queued) | its length | the scale | MUTE QUEUE |
| 3 VIAGGIO | the energy (the target) | the phrase: 4, 8, 16 bars | the genre (queued while playing) | the key's root (queued while playing) |

In PERF mode (GLO tapped), **SEL + the knobs are TRACK LIVE** whatever page is shown, as in 0.11; SEL + ALG the tempo;
**OCT- / OCT+ turn the pages** and **SEL + OCT- / OCT+** make the white keys mutes / solos.

### SAVE pages

| page | K1 | K2 | K3 | K4 |
|---|---|---|---|---|
| 1 | MASTER knob function | the remote OFF / CH 14 / 13 + 14 | snapshots bring their tempo | the PROFILE |
| 2 | **CC LEAD** 0-30 ms | **SONG TEMPO** | **DEVICE** of the track's channel (GENERIC, ELEKTRON) | **LIBRARY** 16 / 32 / 64 STEPS |
| 3 SYSTEM (0.12) | **USB PORTS** 1 / 2 (SEL + K1 twice: reconnect) | the button lights | | |
| **4 LIVE IN** (0.13) | **MOTION** OFF / 1 / 2 / 4 BARS (REC + FX K: written) | **KEYBOARD** OFF / ALL / SPLIT C3 (the MIDI IN transposes) | **KEYB CH** ANY / 1-16 | **MIDI IN** REC ONLY / ALWAYS |

### PICK: the keys set the knobs (0.12)

Hold a group button (HOME, GLO, SEQ, ARP, EDIT, ENV, LFO) - **or open its window with a tap** - and SEL: the keys set
the knob **in focus** of the page shown, the one turned last on that page (K1 at first); the screen marks it with `>`
before its label (`>-` when the keys cannot set it: a continuous value such as a velocity or a CC value stays on the
knob). **Black 11** moves the focus to the next knob. The knob is then turned by the difference, so what a knob does
(its messages, its limits, the bar line it waits for) happens the same way; the keys that mean something are lit and
the key of the value now blinks. **On the grid** the PICK view (SHIFT + STEP, twice: CC, then PICK) shows the four knobs
of the window open (PERF's page when PERF is on, HOME's when nothing is), a knob a row: pads 1-16 of rows 1-4 are the
white keys of PICK, pads 1-10 of rows 5-8 its black keys 1-10, the pad of the value now white, a knob the keys cannot set a
faint row; a pad sets the knob (the focus goes to it).

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

### BREAK: a drum break in slices (0.12)

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

### TAKE and THROWS (0.12, from Skiff)

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
* **Program Change per scene** (HOME page 4 K4), **RELOAD** (SEL + SAVE), **TEMP** (grid FX view), **song mode**,
  **tap tempo**, **step recording**, **finger drumming** on drum tracks, **MIDI LEARN** of CC numbers: as in 0.5.
* **The dice**: DICE SEQ (patterns of the genre with the progression of the roll), CC (the lanes' bases), LFO, GROOVE,
  ALL (the bank becomes a piece of the genre). Up to 16 rolls are remembered: ALG goes through them. OCT+ keeps,
  OCT- (or UNDO) puts back what was there before the first roll.
* **EVOLVE** every 1-16 bars, by the amount, around the seed (DRIFT: away from it); FREEZE, REVERT. Rhythm-heavy genres
  move the rhythm more, melodic ones the notes; on FOLLOW tracks the beats get chord tones of the tonic, the steps
  between move by step. A locked step (EDIT + black 1) never changes.

## VIAGGIO

**SEL + GLO** switches VIAGGIO on (and off). GLO alone goes to PERF and back to the keys as mutes: the journey goes on
underneath (its phrases, queue and energy), SEL + GLO brings the VIAGGIO keys back. HOME jumps to page 8/8.

**The phrase.** 16 bars (HOME 8/8 K2: 4, 8, 16), counted from PLAY. At its end (the **boundary**) the queue runs, in
the order it was filled, and the phrase is written into the trail. **MOVES AT** (K2 in VIAGGIO mode) chooses when the
queue runs: the phrase boundary (the default), **every bar**, or **every beat** (you decide when things happen; the
phrase still counts for FILL, RISER, DROP and the trail). The screen shows the bar of the phrase, the energy, the genre
and the queue; the grid's VIAGGIO view shows it all at once.

**Roles and channels.** In VIAGGIO mode K3 is the selected track's **role** (KICK SNARE HAT PERC BASS CHORD ARP, or
none) and K4 its **channel**: you say what each track is and where it goes, the proposals follow (a track with no role
takes the next free one on the genre's ladder).

**The tracks** (white keys 1-16; the grid's row 2) have a state: EMPTY, PROPOSED, IN (it plays), OUT (it has notes and
is muted).

* A tap on an EMPTY track: a **proposal** from the library of the genre, in a free pattern of the track (the one that
  plays is not touched): `T1 KICK P2 SEL+KEY: IN`. The role is the track's (K3), else the next free one on the genre's
  ladder, with its note. A tap on a PROPOSED track selects it and says what it has; **held** (0.45 s): the dice
  (another variant, maybe the genre's neighbour; for PERC in the afro / latin genres a tresillo, son clave 3-2 and
  2-3, rumba, cascara, bossa, cinquillo, bembé 12/8). Up to seven proposals a track, each with the settings it asks
  for; when the patterns are full the oldest proposal goes.
* A tap on a track that is IN: nothing changes in the sound, ever. The screen says what you can do.
* **SEL + the key**: IN at the boundary (an OUT track, or a proposal); on an IN track: OUT at the boundary, its last
  bar fading out. The opposite move cancels the queued one.
* **ALG** browses the proposals of the selected track (`T1 KICK P3 (2/3)`); **SWAP** (black 9) queues the one browsed
  in place of what plays.

**The moves** (black keys; the grid's row 4; remote channel 13 CC 17-27):

| black | move | at the boundary |
|---|---|---|
| 1 | FILL | the last bar of the phrase fills: the steps' FILL conditions play, and every track gets ghost hits, more in the bar's second half. Asked in the last bar itself: at once |
| 2 | BREAK | 1 bar with only the selected track; with SEL: 2 bars of silence, then everything back. A track that enters during a break waits for its end |
| 3 | RISER | the last 4 bars of an 8- or 16-bar phrase climb to energy 100, then back to the target |
| 4 | DROP | a fill in the last bar, then every track with notes IN and energy 100 at once |
| 5 / 6 | HALF / DOUBLE | every track at half / double speed for one phrase (the tempo and the tracks' divisions stay; every track restarts on the bar line at both ends) |
| 7 | THIN | two tracks out: the two highest on the genre's ladder (never the last one); they fade in the last bar |
| 8 | SWELL | two tracks back in, the nearest to the energy |
| 9 | SWAP | the selected track's browsed proposal replaces what it plays |
| 10 | LOOP | from the boundary the keys play and record on the selected track (64 steps of 1/16, in key; on a drum track every white key is that drum; an external keyboard records there too); the next boundary closes it and it loops. With SEL: 4 bars repeated. The track's length and division come back when it leaves the loop (BACK, SWAP) and return with it; a loop nothing was played into is forgotten |
| 11 | NOW | the queue runs at the next bar instead (stopped: at once) |

**OCT-** queues INDIETRO: at the boundary the phrase before the one that ends plays again (patterns, mutes, key,
genre, progression, energy; not the tempo); again before the boundary: one more back; with NOW (or stopped) it is
the phrase before the one playing. **OCT+** cancels the last move
queued. HOME 8/8 K3 / K4 and PRESETS queue a new GENRE, KEY, PROGRESSION (stopped: at once).

**The energy** (K1, the grid's row 5, remote CC 3 on channel 14): 0-100, 50 is neutral. It moves velocity (-20 ..
+20), the FILTER macro (-40 .. +40), gate (-10 .. +10 %), density (60-130 %: fewer hits, or ghost notes; the kick
stays whole; tracks with their own DENSITY algorithm keep it), the LFOs' depth (50-100 %), and from 70 the chords take
their 7th. A new target glides there over the rest of the phrase, a step a bar; DROP jumps.

**The genres** (HOME 8/8 K3, SEQ + PRESETS, the BEAT view: one genre for the library, the progressions and VIAGGIO):
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

**SEL + PLAY** while stopped: the SEED, a dice on the set genre, the key and a tempo of the genre.

**The trail and SALVA VIAGGIO.** Every phrase is kept (the last 128). **SAVE + white 16** makes the journey a song:
the runs of equal phrases become scenes 1.. (at most 16, the shortest runs left out), the song plays them for as many
bars as they lasted. Then save the project as usual.

**The remote on channel 13** (SAVE + K2 on 13 + 14; with two USB ports on port 2): CC 1-16 a tap on track 1-16, CC
17-27 the moves (black 1-11), 28 INDIETRO, 29 cancel the last, 30 the phrase's length (0-95 shorter, 96-127 longer),
31 the next progression, 32 SEL + key on track value / 8. A button: 64-127.

**The profiles** (SAVE + K4): FULL and PALCO. PALCO switches VIAGGIO on, shows HOME pages 1, 3 and 8 only, refuses SEQ,
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
settings, the 16 LFOs, MORPH TO, the tempo (if SAVE + K3 says "snapshots bring their tempo"), and up to 48 captured
CC values (channel, CC, value). When it comes back its sound goes out: the lanes' base values, then the captured CCs
(a CC a lane already sends is not sent twice), and a SysEx 40 tells the Pi to send the patches it keeps.

**CC CAPTURE**: store a snapshot, switch capture on (SAVE + black 9 blinks), turn the synths' knobs: every CC that
comes in (any channel; not the channel mode messages 120-127, not RPN / NRPN) goes into the snapshot playing, and a
lane of a track on that channel with that CC takes it as its base. Switch it off when done.

**PATCHES**: the Pi (the bridge, `patches.json`, see SAGGA-GRID.md) asks each synth for its patch, or listens for 10 s
while you send it from the synth, and keeps it with the snapshot and the project's id. The screen says how many synths
it kept; when the snapshot comes back the Pi sends them again and says so.

## USB: one port or two

The USB page (hold HOME + SEL) shows the link; K1 chooses **USB PORTS 1 or 2**, OCT+ twice reconnects with that.
Saved in the FM-1's settings (not the project), so the computer sees the same device from power-on.

* **1 port** (the default): everything on one port; channels 15 and 16 carry the grid, the tracks use 1-14 (14 is the
  remote's unless SAVE + K2 switches the remote off).
* **2 ports**: the FM-1 shows "Felucca MIDI 1" and "Felucca MIDI 2". **Port 1**: the synths, the tracks on **channels
  1-16**, clock, transport, incoming notes and CCs (REC, CC CAPTURE, LEARN), the TRS input. **Port 2**: the grid, the
  remote (channel 14), the project / library / snapshot SysEx. The bridge takes port 2 by itself. In RaspiMIDIHub's
  matrix connect the synths to port 1 only, and the remote plugins to port 2.

## Saving

Eight slots. The slot saved last is loaded at power-on. Saving never stops the music (nine areas of flash, erased while
stopped; a save writes into an erased one and is read back before it counts; a power cut never loses a slot). Saved
with the project: everything above (the macros too, from 0.10) but the dice and EVOLVE state, TEMP and the song's
position; the journey's settings (on, phrase, energy, genre, the tracks' states), the patterns playing, the mutes and
the scene cursor. **0.10 reads 0.10 projects only** (SGQA): the format was laid out again (sixteen keys, six lanes,
roles, the tools' schedule, user progressions ...) and nothing older loads; keep a 0.9 firmware to play 0.9 projects.

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
| **70** | `sub ...` | (from the PC, 0.11: the PC test, `firmware/src/sagga_test.c`) 0 HELLO; 1 OPEN (the screen asks, SEL on the FM-1 = yes); 2 BOOT (a reboot into the test: no project, no slot read or written, a hand on any key stops it); 3 GO; 4 EV `idx*2 n (t*4 kind a*2 b*2 gc*4)*n` (presses at t ms after GO: 1 press, 2 release, 3 knob `b` = detents + 8192, 4 MASTER, 5 keys `a \| b<<14`, 6 probe, 7 end); 5 CLOSE (a normal reboot); 6 AGAIN `idx*2`; 7 TAKEN `idx*2 n` |
| **71** | `sub ...` | (to the PC) the answers: 0 `state booted playing boots*2 vec*5 pc*5 ms*4 usb_ports profile version`; 1 `state` (1 asking, 2 yes, 3 no, 4 no answer, 5 playing); 2 `ok`; 3 `ms*4`; 4 `ok next*2 free`; 5 `ok`; 6 DONE `applied*2 late*2 lag*2 lost`; 7 ABORT |
| **72** | `idx*2 k last text...` | (to the PC) the probe event idx asked for, in pieces of 150 characters: the explorer's `PROBE G`, `PROBE T1..16`, `PROBE H` lines |
| **73** | `n (idx*2 ms*4 gc*4)*n` | (to the PC) where each event was taken: the FM-1's ms and clock tick (the explorer replays the session in the simulator at those places) |

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
tail of chunks `tag len*2 data`, ended by a 0 (none yet). A later version can add chunks; 0.11 skips the ones it does
not know. An `SGQA` image is read with 80-byte tracks, 18-byte progressions (four) and 24-byte generators, the rest
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
| 40-47 | scene 1-8 | 48-63 | mute track 1-16 |
| 64-79 | kill track 1-16 (held) | 80-84 | DICE SEQ, CC, LFO, GROOVE, ALL |
| 85 / 86 | keep the dice / put it back | 87 | STOP at the end of the bar |
| 88 | RESTART every track | 89 | EXIT the loop |
| 90-105 | RETRIG track 1-16 | **106-113** | **SNAPSHOT 1-8** (at the QUANTISE moment) |
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
| 33-48 | track 1-16: the pattern 0-7 (or value / 16), at the QUANTISE moment | 49-64 | track 1-16: LENGTH 1-64 |
| 65 | ROLL (held; a BREAK) | 66 / 67 / 68 | HALF, DOUBLE, BACKWARDS (a BREAK) |
| 69 | DICE SEQ | 70 | RESET (STRAIGHT; a BREAK) |
| 71 | ROLL 1/32 (held) | 72 | CHOP 0-15 (or value / 8; a BREAK) |
| 73 / 74 | the dice's SWAP 0-7, ROLLS 0-7 | 75 | SLICES 8 / 16 / 32 (0-42 / 43-85 / 86-127) |
| 76-91 | the slices 1-16 as pads (the value is the velocity, 0 = off) | 92 | which LFO (0-15, or value / 8) |
| 93 / 94 / 95 / 96 | that LFO's SHAPE, RATE, DEPTH, DEST | 97 | that LFO on / off |
| 101-106 | lane 1-6 of the selected track: the base, sent at once | 107 | TAKE |
| 108-111 | THROWS: INTENSITY, GATE, SWING, FILTER (64 = 0), gliding back | 112 | the selected track (0-15, or value / 8) |
| 113 | its MODE (FREE IN KEY DRUM TAPE BREAK) | 114 | VIAGGIO energy 0-100 |
| 115 | VIAGGIO genre 0-23 | 116 | VIAGGIO key, the root 0-11 |
| 117 | the harmony's progression | 118 | HARMONY OFF / ON / LOCK |

The pages: **SAGGA Motori** (the tracks: 33-64, 112, 113, 69 and channel 14's mutes, kills, RETRIG), **SAGGA Break**
(65-91, 107), **SAGGA Mod** (92-97, 101-106, 108-111, 114-118, and the notes 100-115: the sixteen LFO switches).

## Limits you should know

* A TAPE note plays its note, velocity and length (with the track's transpose, key, mute, kill, INTENSITY and a positive
  DELAY): no conditions, ratchets, lanes or EXPO on a tape. A TAPE track's steps rest while it is a TAPE and are back
  when it is not. The DELAY of an EXPO span is not applied (spans start on the grid).

* An export blocks the FM-1 for about half a second (stopped only); a file of the library loads only while stopped.
* EVOLVE changes the patterns that were playing when it started.
* The parameter loops always go forward, whatever the track's direction.
* FILTER moves lane 1 of every track (put the synth's cutoff on lane 1); a lane with no base value is not moved.
* The ornaments (HARM, ECHO) share 128 places: when they are full the faintest echo waiting gives way.
* A snapshot keeps which pattern plays, not the pattern's steps.
* VIAGGIO's proposals take free patterns of the track (8 per track): when none is free the oldest proposal is
  replaced. The trail lives in RAM: a power cycle starts it again (SALVA VIAGGIO before that).
* The remote's scene CCs 40-47 reach scenes 1-8; scenes 9-16 through CC 2, 28 / 29 or the panel.
* The patches need the bridge running on the Pi and the synths connected to the Pi; a synth that cannot send its patch
  over MIDI cannot have it kept.
* A SLIDE lane glides a step at a time (one value per step of the track): smooth enough for a filter sweep, not for a
  pitch bend; an NRPN lane sends its three CCs on every change.
* The six lanes of a track share the step: a step is 18 bytes, a project about 170 KB of the FM-1's RAM.
* A written step holds four notes (SEL + keys, the grid's chord pads); a CHORD shape plays up to six, and the
  arpeggio, the strum and the voicing work on all six.
* 0.11: the Pi's variations and progressions need the grid bridge running (it answers for the hub's folders); without
  it SEQ + ALG stops at the FM-1's last variation and SEQ 4 K2 at its last progression (`PI: NO ANSWER`, then `NO MORE
  <MOOD>` without asking again for a while). A progression has up to 8 chords; one from the Pi takes the DICE/PI slot,
  and DICE PROG writes over it (SEQ + SAVE keeps it on the Pi first).
* 0.11: RETRIG and LEGATO move the held notes of a FOLLOW track (long gates, TIE, held notes); an arpeggio's notes and
  a strum keep the chord they began on.
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
