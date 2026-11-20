# SAGGA SEQ: what was new, version by version

The reference of the current version is [../SAGGA-SEQ.md](../SAGGA-SEQ.md); the Italian release notes of each version
are beside this file (`RELEASE-NOTES-X.md`), with the installation sheets of their time (`SAGGA-SEQ-X-INSTALL.md`: for
today's, [../INSTALLA.md](../INSTALLA.md)). These are the "What is new" chapters the reference had, newest first, as they
were written.

## What is new in 0.29

**The genres are 22** (25 until 0.28), with **eight progressions** each, **BALANI** new, the **BALAFON** a part of its
own, REGGAETON and BALANI's THEORY rules **written by hand**, and more to play with: **ROLL** and **ACCENT** among the
MIDI FX, **five scales**, **three grooves**, **four chord shapes**. The projects of before open as they were, each
genre where it went; a 0.28 opens a project of 0.29, without what it has no room for.

* **The genres.** AMAPIANO went into REGGAETON (its log drum, shakers, rims, piano chords: REGGAETON's tempo is 90-112
  now), BASSLINE into UK GARAGE (its sub and stabs: speed garage with the bass in front), GRIME into DUBSTEP, AFRO HOUSE
  is gone (its percussion went into GQOM and BATIDA), and **BALANI** came - the balafon's music at the street parties
  of Bamako, fast (160-180 BPM): the kick in four, the djembe's 3-3-2 on the conga and the perc, the shaker's 16ths, the
  toms rolling, the MC's shouts, and the **BALAFON**. The genres' order: TECHNO, HARDTECHNO, DUB TECHNO, HOUSE, UK
  GARAGE, UK FUNKY, DUBSTEP, JUNGLE, REGGAETON, BATIDA, GQOM, EXPERIMENT, ELECTRO, DRUM+BASS, BALANI, FOOTWORK, TRANCE,
  UK DRILL, HARDCORE, PHONK, BAILE FUNK, MERENGUE. The grid's BEAT view has two pages of genres again (12 + 10).
* **A project of before** opens with each of its genres where it went: GRIME as DUBSTEP, BASSLINE as UK GARAGE, AFRO
  HOUSE as GQOM, AMAPIANO as REGGAETON - wherever a genre is kept (the project's, the harmony's, the journey's, a track's
  pattern, a pattern the engines made, a snapshot). On the Pi, the patterns and progressions **you** kept in those four
  genres move to the genre that took them in (the stock ones stay behind), the first time the hub starts.
* **Eight progressions a genre** (six until 0.28): the six of before where they were - a project keeps its progression
  by its number - and two more (the bassline's in UK GARAGE, the grime's in DUBSTEP, the amapiano's in REGGAETON, the
  afro house's in GQOM and BATIDA, the genre's own elsewhere). SEQ 4 (ARP 3) K2: PROG 1-8, USER 1-4, DICE/PI. The
  VIAGGIO view of the grid, row 7: pads 1-8 the genre's, 9-12 yours, 13 DICE/PI, 14-16 the chord playing in turn
  (white: the progression's first). The BEAT view's row 3 keeps PROG 1-6. SAGGA Mod's PROGRESSION: PROG 1-8, USER 1-4,
  DICE/PI (channel 13, CC 117, 0-12).
* **The BALAFON**: a part (and a role) of its own - a tune, struck: its notes are short, from middle C, and with the
  harmony it follows the chords as a MELODY (as a LEAD or a VOX). BALANI's band has it where it had a LEAD.
* **THEORY**: REGGAETON and BALANI have rules written by hand now (TECHNO, HOUSE, DUBSTEP and DRUM+BASS had them; the
  other sixteen are counted from the library). REGGAETON: the dembow at every energy (the snare's `...x..x....x..x.`),
  the rest coming in with the energy, the log drum's slides, four chords a bar each. BALANI: the clap on 2 and 4, the djembe's
  3-3-2, the balafon's ostinato in 16ths on the pentatonic, one or two chords. The seventeen genres that did not change
  (and FREE) make what they made, bit for bit; UK GARAGE, BATIDA and GQOM's counted rules changed with their libraries.
* **ROLL** (MIDI FX): each note 2-6 hits in its step - LEVEL, RISING or FALLING - with a chance (K2, K3, K4). The trap
  hats. **ACCENT**: every 2-8 steps (K3), from a step of its own (K4), louder (K2 up to +60; below 0, softer): three
  over four. In the chain's ORDER, ACCENT comes after VEL CURVE and ROLL before ECHO. On the grid: SHIFT + pads 7 and 8
  of the TRACK 3 view's second row.
* **Scales**: HUNGARIAN MINOR, DOUBLE HARMONIC, LYDIAN DOMINANT, MAJOR BLUES, IN SEN (21 in all). On the grid's PROJ
  view: SHIFT + row 2, pads 1-5.
* **Grooves**: MALI (the djembe's 16ths, leaning towards three a beat), DEMBOW (the snare's two on the 'a', late and
  loud), BROKEN (broken beat: the 'e' early, the 'a' late).
* **Chord shapes**: 7#9, 7B9, MAJ7#11, QUARTAL (36 in all) - for a track's CHORD and in your progressions.
* **Fixed**: the BEAT part chosen past the sixteenth of the list (a LEAD, a VOX, a LOG DRUM ...) came back as the KICK
  after a power cycle; now it stays. The dice's progression in the VIAGGIO (DICE/PI: the grid's row 7 pad 13, or
  PRESETS) took the first user slot's name on the screen (`USER PROG ...`); now it says `DICE/PI` and its chords.
* **The projects.** A project of 0.29 is saved as 0.28 saves, plus one chunk for what 0.28 has no room for: BALANI, the
  7th and 8th progressions, the balafon, ROLL and ACCENT. A 0.28 opens it: BALANI as AFRO HOUSE, PROG 7 and 8 as PROG 1,
  the balafon as a LEAD, the new effects, scales, grooves and shapes left out (their default).

On the Pi: the pattern and progression pages have the 22 genres, SAGGA Live the new grooves, shapes and effects, SAGGA
Mod the 22 genres and the eight progressions, the editor ROLL and ACCENT. Install the FM-1 and the Pi together.

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
  the scenes and the snapshots keep all eight. The remote's lane knobs: lanes 1-6 channel 13 CC 101-106, lanes 7 and 8
  (0.28.1) channel 12 CC 62 / 63 - SAGGA Mod has all eight.
* **The projects.** One of 0.27 or before opens with its first twelve tracks: its tracks 13-16 are left out (an LFO or a
  MOD aimed at one of them stops, an LFO's TRIG from one of them goes back to CLOCK; their mutes go). A project of 0.28 is saved as 0.27 saves, plus one chunk
  for the notes 5-6 and the lanes 7-8: a 0.27 opens it, without them. A MIDI file read into a project on the Pi:
  channels 1-12 become tracks 1-12, channels 13-16 are left out (`sagga_sgqmid` says how many notes).
* **The memory**: a project is 15 KB smaller (163 KB in RAM; a step is 22 bytes, a track's settings 104).

On the Pi: the editor shows twelve tracks, six notes a step and eight lanes; the bridge sends the previews and the
phrases to tracks 1-12, up to six notes. Install the FM-1 and the Pi together.

## What is new in 0.27

Four proposals of the map of the generators ([MAPPA-GENERATORI.md](../MAPPA-GENERATORI.md)), a fix asked for and one
the explorer found. Nothing is taken away: the projects of before open as they are and play as they did.

* **A band with no key starts on its root** (the fix). With no key (the scale CHROMA, as in a new project) a part's
  root was the note it starts from, and an arpeggio starts from a G: the BAND's arpeggio - the library's and the
  engines' - played a fifth above the bass and the chords. Now a part written on a new track with no key (BAND, BEAT
  of the engines, a proposal) starts on the project's root (C in a new project), in the part's own register. With a
  key nothing changes; what is already written stays as it is.
* **RANDOM is a roll of the dice** (SEQ + white 5): the same bar of chance and its phrase, on the SCOPE's tracks, but
  it waits like a dice: `RANDOM: OCT+ KEEP, OCT- BACK`. OCT- (or UNDO) puts back what was there, ALG goes through the
  rolls (up to 16, with the other dice), RANDOM again is one more roll. EVERY repeating RANDOM still changes at once.
* **EVOLVE's RETURN** (SEQ 3, **SEL + K2**, 0-100 %): before each change, how much of the seed comes back. 100 (EVOLVE
  as it was): every change starts from the seed, and stays near it; 0: every change starts from the last one and goes
  away - that is DRIFT; between: that share of the steps (and of the LFOs) goes back to the seed, the rest wanders on.
  `EVOLVE RETURN 40%: PART OF THE WAY BACK`. The DRIFT key (SEQ + black 8) is RETURN 0, and pressed again the RETURN it
  had: `DRIFT: EVOLVE WANDERS AWAY`, `NO DRIFT: EVOLVE STAYS NEAR THE SEED`. A project with DRIFT on opens with RETURN 0.
* **The screen says who is acting**: the four hands that make the music fuller or emptier say what they work on -
  `T3 DENSITY 60%: THIS TRACK ONLY` (SEQ 2), `T3 CHANCE 40%: THIS TRACK ONLY` (HOME 6), `ENERGY 70: THE WHOLE SET + 4
  ENGINE PARTS` (GLO 3 K1: every track, and the patterns of the engines it fills and empties), `QUEUED: THIN - THE
  WHOLE SET, 2 TRACKS OUT` and `QUEUED: SWELL - THE WHOLE SET, 2 TRACKS IN` (the MOSSE).
* **A third profile, SEMPLICE** (SAVE 1 K4 goes FULL, SEMPLICE, PALCO): all of FULL, but SEQ's pages 2 (the four
  algorithms) and 3 (EVOLVE) are hidden while nothing of theirs plays - SEQ + OCT- / OCT+ skips them. An algorithm on
  the selected track brings SEQ 2 back, EVOLVE on brings SEQ 3: nothing is switched off. `PROFILE SEMPLICE: SEQ 2 AND
  3 HIDDEN WHILE OFF`. PALCO is now two steps of K4 away.
* **ENV K1 that writes nothing leaves the step alone** (the explorer; there from 0.24). Turned down on a step with no
  lock, K1 wrote nothing but flagged the step as written: a key that turned it on later played note 60, not the
  track's pen (on a kick, another drum), and a copy of the pattern turned so made every copy the player's step. And a
  step written after the loop where a pattern longer than its track keeps the mark of its end (a lock, a note): the
  steps are the player's at once, as the next LENGTH made them - the mark was left half a mark, half a step.

On the Pi: the converter knows RETURN. An older firmware reads a RETURN under 50 % as DRIFT on, the others as DRIFT off.

## What is new in 0.26

Seven things, and the technical check of 0.23 - 0.25. The projects of before open as they are and play as they did.

* **THE CLICK** (SAVE 5, a new page): a metronome on the beats **of the metre** - the bar line higher and louder -,
  OFF / while it RECords / while it PLAYs; the FM-1's own sound, or a note on a MIDI channel (CLICK OUT); and a
  **COUNT IN** of one or two bars before a recording. See [The click](../SAGGA-SEQ.md#the-click).
* **The keyboard's chords are the harmony**: KEYBOARD (SAVE 4 K2) has two more ways, **CHORDS** and **CHORD <C3**. The
  chord you hold (two notes or more; below C3 only, in the second) is the harmony's chord from that moment - every
  FOLLOW track goes to it, as when the progression changes chord -, with the HARMONY off too, until the next one.
  `CHORD IV (THE KEYBOARD'S)`.
* **The scenes bring their metre** (GLO 4 K3, **SCENE METRE**: BRING IT): a scene stored remembers the metre it was
  stored in (`SCENE STORED 2 IN 7/8`), and brings it when it is recalled - stopped at once, playing at the bar line. A
  song walks through its scenes' metres, and finds its place in them from any point.
* **Chords that move little**: FOLLOW has a fifth way, **SMOOTH** (ARP 4 K1, past MELODY). The chord is the one FOLLOW
  makes of it, its notes in the octaves nearest to the written ones: the notes two chords share stay, the others move
  a step or two (C E G on IV: C F A). The PADs and PIANOs the makers write follow so.
* **The keyboard's expression**: the pedal, the pitch wheel, the aftertouch (a key's own too) and every controller of a
  keyboard played through the FM-1 go where its notes go; with REC on they are recorded - the wheels in the track's
  LANES, the pedal as the length of the notes. See [The keyboard's expression](../SAGGA-SEQ.md#the-keyboards-expression).
* **The engines make a part IN the bar**: in 7/8, in 5/4 a part of the THEORY engines is made in seven, in five - every
  step of the bar has its place in the metre - and no longer a 4/4 re-barred.
* **An answer has notes**: a bass takes the notes of the tune it answers, a tune plays the notes of the chord it
  answers. Both: [THEORY](../SAGGA-SEQ.md#theory-the-engines). In 4/4 the engines make what 0.25 made, bit for bit; a pattern of
  0.25 is made again as 0.25 made it.

On the Pi: the editor and the converter know all of it (Project: IL CLICK, the two new ways of KEYBOARD, SMOOTH).

## What is new in 0.25

Six things the sequencer could not do.

* **The bar has a metre** (GLO 4). A bar was sixteen 16ths whatever the tracks did. It is now 3 to 32 steps, divided
  in beats the way you choose - 7/8 as 2+2+3, 5/4, 6/8, 9/8, 15/16 - and everything that waits for the bar or counts
  bars follows it: the lengths, a queued pattern, QUANTISE, WHEN and EVERY, the MOSSE and their phrase, the song, the
  harmony's chords, LOOP and REPEAT, EXPO, MOTION, the tape. The library's patterns and the engines' are made in the
  metre's bars. The whole of it: [The metre](../SAGGA-SEQ.md#the-metre), in the reference.
* **True polyrhythms** (HOME 1 K3, past 1/32T; the grid's TRACK row 4, pads 15 and 16). Six more steps: `1/4 5:4`,
  `1/8 5:4`, `1/16 5:4`, `1/4 7:4`, `1/8 7:4`, `1/16 7:4` - five, or seven, steps in the time of four of that value.
  A track at 1/16 5:4 plays five steps in a quarter; at 1/4 5:4, five in a bar of 4/4 (a loop of five steps: five
  hits against the kick's four, for good). The clock has 24 ticks a quarter and a fifth of a quarter is 4.8 of them:
  the FM-1 plays each of these steps at its own time between two ticks, so the five are even and the track comes back
  on the bar line exactly, bar after bar. Swing, GROOVE, the ratchets, the ARP, a nudge work on them as on any step.
* **TURING as long as its track** (SEQ 2, B turned past 16: `TRACK`). A TURING's phrase was its register, sixteen
  steps at most, going round inside the track. On TRACK the register is as long as the track (up to 64 steps): the
  whole written rhythm is its loop, and it grows and shrinks with the track. **NUMERIC fits the bar**: its sixteen
  rhythms were written for 16 steps, and a shorter loop played their beginning. Now a rhythm is laid on the steps it
  has - the metre's bar, or a loop shorter than a bar - each hit at its place in proportion (one that would fall on
  the hit before it, or right beside it, is left out: the rhythm keeps its rests); 16 steps play as they did.
* **The engines' parts listen to each other.** Until 0.24 every part was made alone (the kick apart: a rumble avoids
  it, a sub leans on it). Now a **lead, a voice and an arpeggio answer the chords**: they stay away from the places
  where the chords strike and fall right after them more often. **The percussion answers the snare** the same way,
  and **a bass leaves room under the lead**. It works whatever order the parts were made in: when the part they
  answer is made again (BEAT, a seed turned, the dice, UNDO), the parts that answer it are made again within a moment
  from their own seed. A part that answers nobody (the kick, the snare, the hats, the chords) is what it was in 0.24.
* **The melody knows the chord**: FOLLOW has a fourth way, **MELODY** (ARP 4 K1, past LEGATO). A riff under FOLLOW is
  moved whole with every chord, and so was a lead: the same tune a third down, a fourth up. In MELODY a tune stays
  where it is written, and its **strong notes** - on a beat of the metre, or longer than a step - go to the nearest
  note of the chord playing (of two as near, the lower). The short notes between the beats play as written: passing
  notes of the key. A note held through a change of chord slides to the new chord's nearest note, as LEGATO does. A
  step of two notes or more is a chord and moves as ever. **A LEAD or a VOX that BEAT, BAND, the dice or the engines
  make follows as a MELODY** by itself; any other part on that track later puts it back to HOLD (RETRIG and LEGATO, if
  you chose them, stay). A lead made before 0.25 is on HOLD until you turn the knob or make it again.
* **LONGER and SHORTER from the tablet**: two taps on SAGGA Live (channel 12 CC 61 / 60): every track twice or half
  as long, at the next bar while it plays, at once when stopped; the other one takes it back.

And on the Pi: **the grid bridge leaves the FM-1 alone while it is being updated** (it took the update loader,
"Felucca Update", for the FM-1 and sent it a message a second through an install); **the editor shows the copies while
you type a length**, before Save, as the FM-1 would make them; the editor has the metre (Project: the bar and its
beats, the marks of the beats on every row), the six new steps, FOLLOW's MELODY; a MIDI file is written and read in
the project's metre.

A project of 0.25 read by 0.24: the metre is 4/4, a polyrhythm step is 1/16, a TURING on TRACK is 16 steps long, a
MELODY track is on HOLD. Nothing else is lost.

## What is new in 0.24

**The length is the track's.** A track's LENGTH (HOME 1 K2, the grid, the pages, the moves) is the player's, and its
eight patterns fit it: a pattern shorter than its track goes round again in what the track has more, one longer keeps
what the track does not play. Nothing that brings a pattern changes the length any more. The whole of it is in
[The length of a track](../SAGGA-SEQ.md#the-length-of-a-track-and-its-patterns), in the reference; in short:

* **A length that changes lands on the bar line.** While it plays a new length waits for the bar, as since 0.11 - but
  the step ON that bar line was still the old loop's (the track was put in line a tick later): a track of 19 steps
  made 32 at a bar played its step 11 there. It now plays the step the clock asks for, from that tick. The same for
  everything else that changes a loop on a bar line (a snapshot, a pattern with other settings, the Pi's phrase).
* **16, then 19, then 32: on the rails again.** A longer track repeats the PATTERN, whatever lengths came before.
  0.11 repeated "the length when the knob began to turn": 16 made 19 at a bar (a polymetre, fine) and then 32 was the
  nineteen going on - a second bar that began with steps 1 2 3 again and stayed three steps off for good. Now 32 is
  the 16 steps twice. The steps the track has more are the pattern's **COPIES**: they follow it (change a step, its
  copies change), until one of them is written - then they are all steps of yours (`THE COPIES ARE YOUR STEPS NOW`),
  and the pattern is as long as the track. The screen says `LENGTH 32: THE 16 STEPS REPEAT`; the grid shows the
  copies in a colour of their own.
* **Shorter and back.** A track made shorter keeps its pattern whole after the loop, with a mark where it ends. Made
  16 again, a pattern of 16 with a silent last quarter is as it was (0.11 - 0.23 wrote its first four steps there);
  made 32 from 12, it is the pattern twice. Every pattern of the track fits a new length, not only the one that plays.
* **Silence when you ask for it.** What you write after the loop is part of the pattern, and the pattern then ends
  with the round of itself your last step is in: write the 64th step alone and a longer track stays silent up to it
  (turn it off before the cursor gets there: 64 steps, 48 of them silent); write a second bar while the track loops
  the first, and 64 steps are those two bars twice.
* **A pattern that comes keeps the track's length.** BEAT, KIT, BAND, the dice, the proposals, GENRE LIVE, the Pi's
  patterns, the engines: on a track of 32 a pattern of 16 comes with its copies, on a track of 17 with its first step
  again, on a track of 12 its first twelve play and the rest waits. (Until 0.23 the pattern made the track as long as
  itself.) SAVE 2 K4 was LIBRARY LEN and is **LONG PATTERNS**: COPY (a one-bar variation repeats) or PHRASE (the long
  form of 0.10: the next variation in the last bar, the genre's fill). The variations the library has written over
  two or four bars come whole on a track that long either way.
* **LONGER / SHORTER, two moves.** On the MOSSE, SEL + black 6 (DOUBLE) and SEL + black 5 (HALF); on the grid's VIAGGIO
  view SHIFT + those pads: every track twice or half as long, at the phrase's end (stopped: at once). SHORTER after
  LONGER gives every pattern back as it was.
* **The generators make a phrase for the length.** RANDOM and the dice on a track of 32 or 64 steps no longer fill it
  with chance: a bar, its answer (the bar with another ending), the bar, the turn. COOK walks to the next variation
  as a phrase as long as the track. The THEORY engines make the bars the track has (16, 32 or 64 steps) and the rest
  is copies; a seed turned (SEQ 8 K3) makes the pattern again for the track as it is now.
* **The Pi and the grid.** The grid's light role 18, GHOST, is a copy that plays (the bridge of 0.24 has its colour;
  an older bridge shows it dim). The editor shows the copies and, when it saves, the Pi's converter puts them in
  order as the FM-1 would: a track made longer there has its patterns go round, a copy changed there makes them steps.
* **The project file.** That a step is a copy is not in the step: a list after the steps says which are (chunk 3).
  A copied rest costs nothing; SAGGA SEQ 0.23 reads a 0.24 project and finds plain steps where the copies were.
* Smaller things: a move that cancels its opposite in the queue says so (`CANCELLED: LONGER`, `CANCELLED: HALF`); a
  phrase from the Pi's regia that changes a track's length puts the track in time; the explorers have a rule for the
  copies (COPIE).

## What is new in 0.23.2

The Pi and the grid, read again from end to end; one change in the FM-1.

* **The tablet's A on a CELL picks the even rules.** On SAGGA Live, A set a CELL's rule spread over 0-255: the knob's
  128 places gave the even rules up to 126 and the odd ones from 129, and the rules to start from - 170 and 240 (the
  rhythm slides), 204 (it stays), 184 and 226, 150 - could not be had from the tablet. Now the rule is twice the
  knob (85 is 170, 102 is 204, 120 is 240): every one of the grid's sixteen rule pads but 51 and 105, which stay the
  panel's and the grid's. The knob's place the FM-1 says back was already the rule halved.
* **The Pi keeps out of the music.** RaspiMIDIHub takes its whole matrix down and up again whenever an ALSA client
  comes or goes on the Pi (its hotplug scan: the notes that sound are ended, every road is away for a moment), and a
  program that looks at the list of MIDI ports makes two such clients. Three things of SAGGA did that while you
  played: the hub's page asked the FM-1 who it was the first time it was opened and every ten minutes after; the
  bridge without its two Launchpads looked at the ports every 3 s; the bridge without the FM-1 ended and was started
  again every 2 s, with a look each time. Now the page's service asks the FM-1 only when the FM-1 itself came back
  (its USB appearance changed), from a thread of its own, and the bridge waits on `/proc` - a look only when a device
  came or went. A fourth, for who keeps the synths' patches with the snapshots (`patches.json`): a snapshot that
  brought its patches back opened and closed a port for every synth, in the music; the synths' ports are now opened
  when the bridge starts (or when a synth is plugged in) and stay open. Nothing of SAGGA makes an ALSA client while
  you play.
* **The bridge notices an FM-1 that restarted in half a second.** It watched the ALSA clients once a second, by number
  and name; the user's own log shows the FM-1 gone and back in 0.44 s under the same number: the bridge sat there
  with connections that were not there any more, the grid dead until something restarted it. It now watches its own
  connections too (in `/proc/asound/seq/clients`). And a bridge that is stopped (the banco does it, and a shutdown)
  switches the Launchpads off and tells the FM-1: the grid no longer stays lit and still, looking alive.
* **The Pi's clock is not trusted.** A Pi has no clock of its own: with no internet it falls behind (the user's bench
  files of 17 November are dated 26 October), and it can start at a moment already past. The editor's versions and the
  bench runs kept on the SD were ordered by their time: a new one could count as the oldest. A version's name is now always later than the newest there; the run just made always stays.
* **The piano roll of 0.11 is gone; the editor's Tape tab is the piano roll.** The old page (the "piano roll" link by
  each project) saved through a MIDI file, and what came back was not the project: a TAPE track on another MIDI
  channel was written onto the track of that channel's number (a step track there became an emptied TAPE, and the
  TAPE track itself kept its old notes); a transposed TAPE track was transposed once more; a loop of one bar came
  back four bars long, its notes repeated (a note changed stayed the old one in the other three). Save alone did it,
  with nothing touched. The editor's Tape tab (0.15) writes the events as they are kept, track by track. The link is
  away; an old `/roll/...` address opens the editor on its Tape tab.
* **BREAK IN SLICE says when the loop is not in the file.** A BPM too slow for the file, or too many bars, made a
  loop longer than the file: the zip came back with its last slices empty (WAV files with no sound, keys that played
  nothing) and not a word. Now the page says how long the file is and what tempo it would be. Bars that give a tempo
  that cannot be (four bars said of a one-bar file: 544 BPM) are refused too.
* Smaller things: the hub's page refuses a POST that comes from a page of another site; `install_hub.sh` checks that
  the root is writable before every block of writes; a light role the bridge does not know is DIM, not dark; the
  editor's note on a THEORY pattern names the parts whose hand-written steps do not stay (a RUMBLE or a SUB that
  follows the kick); the banco's log (and the matrix check's) carries the bridge's own last lines, and what it says
  when it starts again.

## What is new in 0.23.1

Two things that were there and could not be used, put right; and the PC test counts what the FM-1 sends.

* **NUMERIC is sixteen rhythms.** The third rhythm family of EUCLID LIVE (SEQ 1 K3) laid the binary digits of the n-th
  prime number over the steps: most values of K1 gave nearly every step, none a rhythm one would write (a misreading
  of the Numeric Repetitor, whose "prime rhythms" are rhythms chosen by hand). Now **K1 picks one of sixteen base
  rhythms** of 16 steps, from the straight to the syncopated, and **K2 turns it** a step at a time, as in the other
  families. Each has a hit on the first step, 4 to 7 hits, never two in a row; none is another one turned. Over 32 or
  64 steps the sixteen come round again; past 16, K1 comes round too. The screen says `NUMERIC READY 7 OF 16`, the
  message gives the rhythm's shape as the steps from each hit to the next: `NUMERIC LIVE T1: 7 = 3-3-4-2-4 ROT 2`.
  Turning K3 says what K1 and K2 do in the family chosen. **A project that plays a NUMERIC rhythm sounds different
  from 0.23**: choose the rhythm again.

  | K1 | the rhythm | its shape | |
  |---|---|---|---|
  | 1 | `x...x...x...x...` | 4-4-4-4 | four on the floor |
  | 2 | `x...x...x.....x.` | 4-4-6-2 | the last beat late |
  | 3 | `x..x....x...x...` | 3-5-4-4 | |
  | 4 | `x..x....x..x....` | 3-5-3-5 | |
  | 5 | `x...x...x...x.x.` | 4-4-4-2-2 | four and a pickup |
  | 6 | `x..x..x.x...x...` | 3-3-2-4-4 | a tresillo, then two beats |
  | 7 | `x..x..x...x.x...` | 3-3-4-2-4 | the son clave |
  | 8 | `x..x...x..x.x...` | 3-4-3-2-4 | the rumba clave |
  | 9 | `x..x..x...x..x..` | 3-3-4-3-3 | the bossa nova |
  | 10 | `x.x.x...x.x.x...` | 2-2-4-2-2-4 | |
  | 11 | `x..x..x.x...x.x.` | 3-3-2-4-2-2 | a tresillo, a beat and a pickup |
  | 12 | `x..x..x.x..x..x.` | 3-3-2-3-3-2 | the tresillo, twice |
  | 13 | `x..x..x..x..x.x.` | 3-3-3-3-2-2 | |
  | 14 | `x.x.x.x.x.x.x...` | 2-2-2-2-2-2-4 | |
  | 15 | `x.x.x.x.x.x..x..` | 2-2-2-2-2-3-3 | |
  | 16 | `x..x.x.x..x.x.x.` | 3-2-2-3-2-2-2 | |

* **CELL comes back to what you wrote.** CELL (SEQ 2) turns the track's rhythm into a new row every bar by a fixed
  rule. When a row came out empty - it does with more than a hundred of the 256 rules - it started again from a single
  hit in the middle of the bar, and the rhythm you wrote never returned. Now **an empty row is the written rhythm
  again**: many rules become a phrase of a few bars that always comes home (rule 90 on 16 cells: at most eight rows, then
  yours). Nothing written: the single hit, as before.
* **The screen says what a rule does.** Turning RULE or CELLS (K2, K3; the grid's pads; the tablet's A and B) says
  what the rule makes of this track's rhythm from here on - from the row that plays, or from the written rhythm while
  it is READY: `T1 CELL RULE 204: THE RHYTHM STAYS AS IT IS`, `... SLIDES 1 STEP LATER EVERY ROW`,
  `... A LOOP OF 8 ROWS`, `... AFTER 4 ROWS A LOOP OF 4`, `... AFTER 1 ROW EVERY STEP PLAYS`,
  `... KEEPS CHANGING FOR A LONG TIME`. The 256 numbers have no names; the screen reads them for you.
* **The grid's sixteen rule pads go from the calm to the wild** (TRACK 3, row 5): 204 the row stays as it is (a tap
  while a CELL plays holds the row of that bar), 170 and 240 it slides a step earlier / later, 184 it slides and the
  hits in a row open up, 51 hits and rests swap, 90 150 105 60 loops of a few rows through the written rhythm, 54 thin
  and thick in turn, 18 22 126 122 110 longer stories, 30 no loop in sight. (They were 30 45 54 60 73 90 105 110 122
  126 150 18 22 57 62 184, in no order.) From the tablet the A knob reached one rule in two (128 places for 256
  rules: not 170, 240, 184, 204, 51, 150 - and 171 and 241, its nearest, fill the holes of three steps or more before
  they slide); 0.23.2: the tablet's A is the even rule, twice the knob.
* **The PC test counts.** The FM-1 counts what its program hands to the USB, by port and kind (clock ticks, note-ons,
  note-offs, control changes, the rest, the bytes), and the output ring keeps its own account; the test's DIAG says
  them, a new **QUIET** stops the FM-1 and leaves it silent. The Pi's banco asks before each session and after it and
  compares with what it heard, and with what the Pi's USB driver received: when a message the FM-1 sent is not heard,
  the log says so and **where it was lost** (inside the FM-1, on the way, or in the Pi). The 0.23 banco had six such
  messages in 28 sessions and could not tell.
* **Corrected in the sheets**: "a step written by hand in an engine's pattern stays when the energy changes" is true
  of every part but the ones that follow the kick - RUMBLE in TECHNO and HARDTECHNO, SUB in DRUM+BASS, DUBSTEP,
  JUNGLE, GRIME, BASSLINE, FOOTWORK, PHONK, UK DRILL and BAILE FUNK: those are made again around the kicks, whole.

## What is new in 0.23

**The THEORY engines.** Until 0.22 a part was LOADED: the library holds up to twelve written patterns for each part of
each genre. With **SOURCE THEORY** (the new SEQ page 8, K1) a part is **MADE** when you ask for it, from the rules of
the genre and a number, the **SEED**; one more click, **SOURCE FREE**, and it is made by the rules of **no genre**,
whatever the genre is. SOURCE LIBRARY is 0.22 as it was; the three can be switched at any time, in play too. The whole
of it, in Italian: [TEORIA.md](../TEORIA.md) (what each engine does, why, which existing instrument it is
like) and [TEORIA-GENERI.md](../TEORIA-GENERI.md) (the rules of 21 genres, counted from the library).

* **A seed is a band.** The same seed gives the same parts; another seed another band of the same genre; 999 seeds a
  genre. All **25 genres** have a style, and **FREE** is a style with no genre: the metre and what a family of parts
  does. The engines make drums, bass lines, chords, arpeggios, motifs (LEAD, VOX) and progressions.
* **Free of the genre.** **SOURCE FREE** (SEQ 8 K1, past THEORY) is the engines' own free mode: BAND, KIT, BEAT, the
  dice and DICE PROG work by FREE's rules whatever the genre and its mode, and a change of genre leaves the engines'
  patterns as they are (with GENRE LIVE too: only the library's tracks follow it, from the library). The machine's **GENRE FREE** (SEQ 6 K4) frees the engines with
  everything else while the SOURCE is THEORY; **HARMONY FREE** (ARP 4 K2) frees DICE PROG alone.
* **The same gestures.** BEAT, KIT, BAND make the pattern from NEXT SEED (pressed again: the next seed); SEQ + ALG is
  the seed where it was the library's variation; **COOK** walks the pattern to the next VARIATION of its own seed, HEAT
  being its size (EVERY + COOK: it evolves); DICE SEQ rolls seeds (OCT+ keeps, OCT- puts back); DICE PROG makes a
  progression by the genre's rules into the dice's slot; GENRE LIVE makes the engines' patterns again in the new
  genre from the same seeds. **SEQ 8**: K1 SOURCE, K2 NEXT SEED, K3 the SEED of the pattern the track plays (turned:
  another part at once), K4 its VARIATION.
* **The ENERGY is the engines' own.** The machine's ENERGY (GLO 3 K1, the grid, RISER, DROP, the remote) fills and
  empties what the engines made: a service makes one pattern a pass again at the new energy, the kicks first, and
  writes only the steps that differ - a step written by hand stays (not in a part that follows the kick, a RUMBLE or
  a SUB: that one is made again around the kicks, whole). A higher energy only ADDS: the hits of a lower one
  are all there, and a note that stays keeps its pitch. The journey's own thinning leaves these patterns alone.
* **The rules.** TECHNO, HOUSE, DRUM+BASS, DUBSTEP and FREE are written by hand (`sagga_theory.c`). The other 21 genres
  are **counted from the library itself** (`tools/theory/gen_rules.py` -> `sagga_theory_data.h`, the way of GESMI): the
  variations of a part that are one pattern are a family; what nearly all of them play is always there (half of it at
  every energy, the rest from energy 25), what some play has a weight; a variation of two bars gives a rule for the
  bar and one for its answer; the levels and the rolls are the place's own; the tones of a bass are fitted to the
  library's counts; the six progressions of a genre give the way its chords move. Measured against the library at
  energy 50 (`tools/theory/compare.py`): 218 of 229 parts fall where the library's fall, a made bar is half a 16th from
  the nearest written one on average, two bars of three are bars the library has.
* **A project remembers** the SOURCE, the next seed and, for each pattern the engines made, what it was made from
  (8 bytes: seed, style, part, variation and its size, energy): image chunk 2, written only when there is something
  to say; a 0.22 firmware skips it and plays the patterns as written ones. UNDO, the dice's BACK, RELOAD and a copy
  of a pattern keep it; a pattern pasted, doubled, cleared or loaded from the library is nobody's again.
* **The grid**: the BEAT view's third row shows seeds where it showed variations (pads 11-16 six seeds, pad 10 the next
  six; SHIFT: what the seed would make). **The tablet** (channel 12): CC 56 SOURCE (0 LIBRARY, 1 THEORY, 2 FREE), 57
  NEXT SEED, 58 the track's SEED, 59 its VARIATION, with their values back to the hub; SAGGA Live has a row for them. **The Pi's editor** keeps the
  records, marks a track whose pattern is the engines' with its seed, and forgets a record when it empties or moves
  the pattern.
* **A snapshot that brought a track's DIRECTION back left it off the bar.** Recalling a snapshot put a track in time
  when its length, start or division changed, not when its DIRECTION did: BACKWARD played, a snapshot with FORWARD
  recalled, and the track stayed a step away from where the bar says until the next STOP. So since 0.11, when a
  snapshot learned to land in time. The explorer's random sessions found it; a test now.
* **The explorer** explores the engines: five situations (TECHNO; REGGAETON with GENRE LIVE; SOURCE FREE with
  four-bar patterns; AMAPIANO with the tablet and the grid; HOUSE on the MOSSE), the tablet's four new
  commands, SEQ page 8, and a rule of its own (MOTORI: stopped, every pattern the engines know is at the machine's
  energy) - checked by breaking the service on purpose.

Not verified on an FM-1: everything here ran in the simulator (the firmware itself, built for a computer). GitHub's
build of 0.23: the image 441,544 B of 581,564 (0.22: 390,132; +51 KB, the engines and their counted rules), RAM
.data + .bss 68,736 B of 98,304 (+464), the pool 326,416 B of 344,064 (+3,332: the engines' rows and the records).

## What is new in 0.22

0.22 is the dig down to the first version: the parts no test could see (the USB's ring, the panel's wait, the
counters' wraps), the tools that test the rest, and the way the FM-1, the Pi and the grid spend their time. No new
feature, the same project format (`SGQB`).

* **The notes waited for the screen.** A piece of the screen (a line: 5 ms of pixels at 12 MHz; a big cell: 8) goes out
  by itself, but the piece after it waited for it to end, with the whole loop: the clock and the notes due in that
  time left late. With the simulator charging the panel's time, four knobs turned in play made 79 notes of 130 leave
  1 to 8 ms late; a tempo knob at 300 BPM gave clock gaps of 3 to 14 ms for 8.3. The loop now starts a piece only when
  the panel has taken the one before (`lcd_idle`): 0 to 2 ms, gaps of 7 to 10.
* **A burst of messages could be lost.** The USB output ring held 64 events, as the input's; what a pass sent beyond
  its room was dropped and only counted (DROPPED on the USB page). A dice on the CCs sends six lanes on sixteen tracks
  at once; three keys together made 68 Control Changes in one pass and four were gone. No test could see it: the
  simulator had no ring. It has the FM-1's now, the random test plays with it, and the ring is 256 (the senders that
  can wait - the grid's lights, the lanes, the LFOs, the values for the hub - still see the first 64, so the music
  never queues behind them).
* **The GATE effect never made a note longer than its step.** FIXED 1/8 .. 2 BARS and x3/2, x2, x4 gave a 1/16
  whatever was asked: a note of a step ends when the track's next step comes, and the effect's longer gate was cut
  with it (since 0.20; the only test tried FIXED 1/32). A note the MIDI FX chain makes longer than the gap to the
  track's next hit now goes out as a held note, with its own end (`MFX_LONG` in `fire_slice`): FIXED 1/8 is two steps,
  x4 of a gate of 80 % is 3.2. It overlaps the notes after it (a mono synth: legato); the same note coming back
  before its end ends it there. HUMAN alone still never carries a note past its step.
* **A TIE into the same note left 15 ms of it.** The tied note's end, 15 ms into the next step, came while the new
  note of the same pitch sounded, and ended it (since 0.10). A held voice of the same pitch that would end before the
  new note does now ends as the new note begins (`held_same_off`); one that outlasts it is left as it was.
* **The grid shows a view in a tenth of a second.** 24 lights a frame, not 8: a view of 130 lights took 350 ms, now
  110. The bridge sends a frame of lights as one message to each Launchpad (it sent one a light), and wakes 50 times a
  second when nothing happens, not 200.
* **The Pi asked the FM-1 who it was every 5 seconds** while the hub's page was open: a Python started, an ALSA client
  made (RaspiMIDIHub scans its devices again at each one) and a SysEx to the FM-1, twelve times a minute, in the
  middle of a set too. It asks when ALSA's clients change.
* **The explorer explored an empty project.** Its "band" was 0.11's gesture (SEQ + SEL + black 7), which 0.12 gave to
  something else: fourteen situations of seventeen, in the simulator and in the plans for the FM-1 and the banco, had
  no band, and its grid went after 3.5 s (no keep-alive). With real bands and a grid that stays: 55829 gestures in 17
  situations, 6799 pairs, 200 sessions, no error. A situation "with a band" that has none is now an error itself.
* **What no test ran.** gcov over every suite that drives the simulator (`-DSAGGA_GCOV --coverage`: the forked
  branches of the explorer write their counters too): 97 % of the firmware's lines run (347 of 13223 run in no test).
  Of what never ran, read and tried by hand: a TAPE track's grid view, six destinations and three sources of the MOD
  MATRIX, the harmony's rhythms 3+5, 3+1 and 2 BARS, the conditions 1:4, 4:4 and NOT FILL, the GATE effect's factors
  and lengths - all as the manual says but GATE (above). They are a test now (`t022_unrun`), and the explorer taps the
  128 pads of the grid's VIAGGIO view too.
* The audio interrupt no longer clears, scales and shifts a buffer of silence every 5.8 ms. 76 and 150 minutes in
  play across the counters' wraps (every 179 s, and the microseconds at 71.6 minutes): the clock never late, the band
  the same, nothing hung - a test now. Two functions nothing called are gone.

## What is new in 0.21

0.21 is 0.20.9 read again from end to end: no new feature to learn, the same project format (`SGQB`).

* **A line of the screen could be written past its end.** The line of what is going on (DICE? EVOLVE SONG TEMP LOOP
  STOP@BAR RESTART TR> MACRO MOTION MORPH LEARN RELOAD MUTES WAIT ECHO ALL STEP LOOP TOOL WAITS EVERY SNAP CAPTURE, the
  chord) was put together in 64 bytes of the stack with nothing to stop it: seven or eight of those at once (a dice
  waiting, TEMP held, a LOOP, RESTART, a macro, MORPH, ECHO ALL) went past them, into whatever the stack held next. A
  random run with the memory checker found it (one in five hundred); seven controls of the hub's pages do it too. The
  lines are now written in a buffer the text writers end, as the messages always were.
* **What goes back to the hub's pages**: a value the tablet had moved looked "just moved" again 65.536 s later, for
  0.4 s (the stamps are 16 bits of ms), and a change made on the panel in that moment reached the page late. The
  stamps are kept young now. And SAGGA Break's knobs follow the tablet's track as the other pages do: SWAP, ROLLS and
  SLICES go back on channel 13 CC 73-75.
* The tests: the suite fails when a test fails (the pipes hid the exit codes), parses the FM-1's two builds with
  this computer's clang (0.20.9's first push did not build), and runs the random test with ASan + UBSan; the random
  test plays the hub's pages too (channels 12 and 13, the pads, every SysEx of the app, USB PORTS 2), and one run in
  eight starts from a project image with bytes changed at random.
* The documents: one installation sheet for today's set ([../INSTALLA.md](../INSTALLA.md)), the release notes and the
  sheets of the past versions in this folder, this page without its 800 lines of history.

## What is new in 0.20.9

The runs of 0.20.8 on the real banco found that **RaspiMIDIHub 6 loses the cells of a device that is away**: its
autosave (every 15-30 s while something changes, and the SAGGA pages change all the time, they follow the FM-1) writes
the cells of the devices that are there only; if the FM-1 is rebooting or off in that second, its cells are gone from
RaspiMIDIHub's memory too, and it does not put them back when the FM-1 returns. The Pi now has **a keeper of the FM-1's
cells** (`tools/hub/sagga_celle.py`, inside the hub's page): it remembers them (with their filters and mappings) while
the FM-1 is there, and when the FM-1 (or the other end of a cell) goes and comes back - its USB device number changes
each time - it waits 5 s for RaspiMIDIHub and puts back the ones that are missing. A cell taken away with the FM-1 on
stays away. The first time it starts from the cells the SAGGA pages need. The page shows what it did (LE CELLE
DELL'FM-1). The banco does the same after each of its reboots, has the host find the FM-1 again when it does not answer
for 12 s (a USB port reset, as the `usbreset` tool), writes the kernel's USB lines and the FM-1's counters in its log
(the test's new DIAG: the HELLOs it heard since its boot, the answers it could not send, when the host configured it,
how long its main loop stood still), and when the FM-1 does not come back puts the project it had before the run in
the hub's library. The comparison of a run with the simulator now looks at each probe's clock tick: a probe one
tick apart on a step's edge is timing, even when the next ones are on the edge too.

## What is new in 0.20.8 (the FM-1 only)

The FM-1 sent its values back to the hub's pages only after a page had sent a command since it started: turned on the
FM-1 first, a page did not follow until it was touched. Now anything that comes in on port 2 opens the way, and the grid
bridge's keep-alive comes every second (with or without Launchpads): the pages follow from the start.

## What is new in 0.20.7 (the FM-1 only)

0.20.6 sent QUANTISE back on channel 12 CC 34 only with REMOTE 13 + 14; with REMOTE 14 (the FM-1's default, SAGGA Remote
alone) it never went back. It goes back with either now (port 2 goes to the hub's pages only); the other three echoes
(SWING, track 6's pattern, lane 1) belong to the pages on channels 12 and 13 and stay with REMOTE 13 + 14.

## What is new in 0.20.6

The first banco on the real Pi found two things. **The values the FM-1 sends back to the hub on CC 6** (QUANTISE, the LIVE
page's SWING; CC 38 and 101 too: track 6's pattern, lane 1) never reached the pages: RaspiMIDIHub 6 runs its pages as
MIDI 2.0 clients, and in MIDI 2.0 those CCs are parts of an RPN / NRPN. The FM-1 now sends those four on channel 12
CC 33-36, and the pages take them there; coming in, nothing changed. And **the banco stopped at its third session**: the
runner left an ALSA client behind at every reconnect (python-rtmidi's MidiIn / MidiOut end their client only when they
are deleted, not when their port closes) until ALSA had none left; now each is deleted with its port.

## What is new in 0.20.5 (the Pi only)

The banco's runner takes the grid's lights and the values for the pages from the FM-1's remote port only (port 2 with
two): it took them from both, and the STOP's sustain-off for the synths (CC 64 = 0 on every channel, port 1) looked
like a value of SAGGA Motori (l15, channel 13 CC 64). A crash of the runner is now written in its own log. The first
runs on the real banco: the FM-1 equals the simulator; the pages, the matrix and the bridge carry every command; the
values the FM-1 sends back on CC 6 (QUANTISE, the LIVE page's SWING) do not reach the pages (CC 6 is MIDI's Data Entry
of RPN / NRPN), every other value does: to be moved to other CCs with a firmware.

## What is new in 0.20.4 (the Pi only)

The banco's explorer stopped the grid bridge before asking the FM-1 for its yes: the FM-1 then let the grid go and its
GRID DETACHED covered the question (PC TEST? SEL = YES), so nobody pressed SEL and the run ended there. Now the bridge
is stopped only after the yes, the question is asked again (up to three times) when nobody answers, and without a yes
the bridge and the matrix are left as they were.

## What is new in 0.20.3

The banco's explorer (docs/SAGGA-ESPLORATORE.md, "Il banco"): on the hub's page, ESPLORATORE DEL BANCO checks the
matrix and tests the FM-1, the Pi and the grid together along the real roads (the six SAGGA pages pressed inside
RaspiMIDIHub through its API, the real grid bridge with two Launchpads of its own, the panel and the probes through the
PC test), with the cells between the FM-1 and the synths taken away for the run and put back after it. The same page
also runs the whole FM-1's explorer (the PC explorer's sessions, every situation) from the Pi, no PC needed.

The firmware (0.20.3) changes in its PC test only: GO with byte 1 bit 0 set asks the FM-1 to hear its ports during the
session. It then plays what comes in (before, the test ignored all the ports' MIDI) and says each message back (SysEx
74, below) with its ms, the clock tick before it and the port, so the session can be replayed in the simulator with
those messages where they came. Outside the test nothing changes; the PC's explorer works as before.

## What is new in 0.20.2 (the Pi only)

`install_hub.sh` restarted RaspiMIDIHub halfway; RaspiMIDIHub puts the root file system back read-only when it starts,
so the rest of the install failed (`Read-only file system` on the service files), and its WiFi could drop with the SSH
session. Now RaspiMIDIHub restarts last, the root is made writable again before the services, and the install runs in
a systemd unit of its own (the terminal follows `/run/sagga-install.log`, last line `SAGGA_INSTALL_EXIT=N`): a dropped
connection no longer stops it. The page's AGGIORNA IL PI runs it the same way.

## What is new in 0.20.1 (the Pi only)

The firmware stays 0.20 (`FM-1_970`); only the hub changes (`sagga-hub-0.20.1.zip`).

* **Elimina** next to every package of the firmware library (port 8090): the file goes away from the Pi's library (the
  read-only boot partition is opened for that moment, as for an upload). The firmware on the FM-1 does not change, and
  the package being installed cannot be deleted.
* **AGGIORNA IL PI**: upload a `sagga-hub-X.zip` and the Pi installs it by itself. The page checks the zip first (one
  folder `sagga-hub-X`, no path out of it, no links, `install_hub.sh` and the page inside, the new page compiles and
  can still update: a hub older than 0.20.1 is refused, it would leave the Pi updatable by SSH only),
  unpacks it in `/run/sagga-update` and runs `install_hub.sh` in a systemd unit of its own (`systemd-run`): the script
  restarts this page, and a child of the page would die with it. `--no-pc` unless the PC port's service is enabled
  here. The page goes away for a few seconds and comes back with the new version at the top (`SAGGA HUB 0.20.1`) and
  the installer's log under the button. Not while the FM-1 installs (the restart would cut the write), and no FM-1
  install while the Pi updates.
* Anyone on the Pi's network can do this, as anyone there can install a firmware: the WiFi password is the key. The
  two new buttons send a header of the page's own, so a form on another site cannot press them.
* The first time, to get this page, is still the SSH way (`SAGGA-SEQ-0.20.1-INSTALL.md`).

## What is new in 0.20

**Five more MIDI FX, and the order is yours.** HOME 6 K1 now goes through nine effects: OFF, HARM, OCTAVE, ECHO, VEL
CURVE and **CHANCE, RANDOM, NOTE FILTER, GATE, GLITCH**. They join the chain as the four of 0.19 do (K1 shows one,
SEQ + white 6 adds it or takes it out, K1 on OFF + SEQ + white 6 stops them all).

| effect | K2 | K3 | K4 |
|---|---|---|---|
| CHANCE | the chance a note passes, 0-100 % (5 a click) | EACH NOTE (each its own throw) / EACH STEP (one throw for the chord) | - |
| RANDOM | the notes' spread: 0 .. +-7 steps of the key (FREE: +-12 semitones) | the velocity's spread +-0 .. 64 | HOW OFTEN, 0-100 % of the notes |
| NOTE FILTER | the LOWEST note that passes | the HIGHEST | ONE IN 1-8 (1: every note) |
| GATE | the LENGTH x1/4 x1/2 x3/4 x1 x3/2 x2 x4 | FIXED: OFF, 1/32 1/16 1/8 1/4 1/2 1 BAR 2 BARS (it wins over the factor) | HUMAN: +-0 .. 50 % at random |
| GLITCH | HOW OFTEN a step glitches, 0-100 % | KIND: MIX (any), STUTTER (the step in pieces), RISE (pieces that climb the key), JUMP (an octave up or down), CUT (a click of a note) | PIECES 1-8 (STUTTER, RISE; JUMP over 4: two octaves; CUT: shorter) |

* **SEL + K1 in HOME 6: the ORDER.** The effect shown plays earlier (left) or later (right) in the chain; the screen
  says the order of those that play, the moved one with them (`T1 ORDER OCT>FILT>HARM`). The default: NOTE FILTER,
  CHANCE, VEL CURVE, RANDOM, OCTAVE, HARM, GATE, GLITCH, ECHO (0.19's four keep their order). An effect works on what
  the ones before it made: ECHO after HARM repeats the voice too, HARM after ECHO gives each repeat a voice, a FILTER
  after OCTAVE sees the moved note.
* Each effect keeps its values in the project, and the order; a 0.19 project opens with the defaults for the new ones.
  A 0.19 firmware opens a 0.20 project with the four it knows.
* **The tablet** (SAGGA Live: MIDI FX 0-9, FX AMOUNT: the new five over their whole range), **the grid** (TRACK 3, row 2:
  SHIFT + pads 2-6 are CHANCE, RANDOM, NOTE FILTER, GATE, GLITCH; their K2 on pads 7-16, K3 and K4 on row 3), **the Pi's
  editor** (the chain in its order, arrows to move an effect).

**ENVELOPES: an LFO shaped ENV.** LFO page 1 K1 has a ninth shape, **ENV**: the LFO rises from CENTER by DEPTH (INVERT:
falls) with each note of its **TRIG** track (page 3 K4), holds while the note is held, and falls back. **LFO page 5
ENV**: K1 ATTACK, K2 DECAY, K3 SUSTAIN 0-100 %, K4 RELEASE, each 0, 1/96 .. 4 BARS. With TRIG on the clock it starts once
a cycle of its RATE and holds half of it. A filter that opens with every bass note: LFO 1 ENV, CC 74 of the bass's
channel, TRIG the bass track, DEPTH 80, CENTER 30, DECAY 1/8.

**The MOD MATRIX: LFO page 6 MOD.** Eight slots: K1 the SLOT, K2 the SOURCE, K3 the DESTINATION, K4 the AMOUNT -100 ..
+100 %; **SEL + K2 / SEL + K3**: which one (which LFO, macro, track, CC).

* Sources: **LFO 1-16** (its output; an LFO whose DESTINATION is **MOD ONLY**, page 2 K1's new last choice, sends
  nothing and only modulates), **MACRO** INTENSITY / GATE / SWING / FILTER, **ENERGY** (the MOSSE's), **RANDOM** (a new
  value each 16th), **VEL T1-T16** (that track's last velocity), **CC IN** (a CC from MIDI IN, the KEYBOARD's channel:
  **LFO + REC** on page 6 learns it).
* Destinations: **DEPTH** and **CENTER of LFO 1-16**; **VEL, GATE, CHANCE, TIMING, SWING of T1-T16** (as an LFO aimed
  there); **FX T1-T16**: the depth of the track's MIDI FX chain (-100 %: none of it .. +100 %: twice): CHANCE's drop,
  RANDOM's and GLITCH's how often, HARM's voice, ECHO's keep, VEL CURVE's curve.
* The matrix is in the project, not in the snapshots. An LFO modulating another LFO answers a moment later (a pass of
  the LFOs); a source that does not move (CC IN, a macro) is there from the first step.

**The BeatStep Pro (an Arturia BeatStep Pro beside the FM-1).** Two things, through the Pi:

* **CV and gates**: the BeatStep Pro turns MIDI into CV. In the hub's matrix, `Felucca MIDI 1` to the BeatStep Pro,
  filtered to channels 1, 2 and 10: the notes of channel 1 come out of its sequencer 1 jacks (pitch 1V/octave, gate,
  velocity), channel 2 of its sequencer 2 jacks, notes 36-43 (C1 .. G1) of channel 10 out of its 8 drum gates. Put a
  SAGGA track on channel 1 or 2 (HOME 1 K1), a DRUM track's PEN on 36-43 and channel 10. (Try it with your BeatStep Pro,
  its sequencers stopped: which of its modes keeps converting is the BeatStep's matter.)
* **Knobs and pads**: the new RaspiMIDIHub plugin **SAGGA BeatStep** (tools/raspimidihub/sagga_bsp). The BeatStep Pro in
  CONTROL mode to its IN, its OUT to the FM-1's port 2. **LEARN**: turn the 16 encoders one after the other (the top row
  left to right, then the bottom one), then tap the 16 pads. The encoders are SAGGA Live's knobs on the tablet's track:
  TRACK, PATTERN, LENGTH, OCTAVE, SWING, GROOVE, ARP, CHORD / MIDI FX, FX AMOUNT, ALGO, A, B, C, PULSES, ROTATION
  (ABSOLUTE, or RELATIVE: 64 + n steps); the pads the 16 MUTES, or (PADS = ACTIONS) PLAY, FILL, FX GO, ALGO GO, COOK,
  BEAT, DICE, UNDO, PROPOSAL, QUEUE, KEEP, BACK, RETRIG, MUTE, EUCLID, ECHO ALL. Its lights do not show the FM-1's state:
  the BeatStep Pro has no documented way to set them from outside.

## What is new in 0.19

**The MIDI FX in a chain.** Until 0.18 a track had one MIDI FX at a time. Now **the four can play together** on the
same track, always in this order: **VEL CURVE** (the velocity), **OCTAVE** (the note moved), **HARM** (the second
voice, built on the note OCTAVE moved), **ECHO** (the repeats of the note *and* of the voice).

* **HOME 6 K1 shows one of the four.** Not playing: it is READY (`T1 MIDI FX HARM READY: SEQ + WHITE 6`), K2-K4 set it
  up, **SEQ + white 6 adds it to the chain** (`T1 MIDI FX HARM STARTS: HARM+ECHO`). Playing: K2-K4 change it live
  (`MIDI FX ON` on the screen), and SEQ + white 6 right after K1 found it (`T1 MIDI FX ECHO PLAYS: SEQ + WHITE 6
  TAKES IT OUT`) takes it out; after K2-K4 that key is EUCLID's again. **K1 on OFF, SEQ + white 6: they all stop.**
  The page's title line shows the chain in the order it plays: `HOME 6/8 FX OCT+HARM+ECHO`.
* **Each effect keeps its values in the project** (until 0.18 only the one playing was saved; the others' values were
  kept while the FM-1 was on). A project of 0.18 or before opens with its one effect as the chain; the format stays
  `SGQB` (the chain is in the extension chunk: a 0.18 firmware plays the chain's first effect, in the list's order
  HARM, OCTAVE, ECHO, VEL CURVE).
* **ECHO repeats HARM's voice too**, and so does FX + OCT+ (ECHO ALL) when the track has no ECHO of its own (until
  0.18 the voice was never echoed).
* **A snapshot leaves the MIDI FX as they are** (the chain is the track's, not a snapshot's; until 0.18 a snapshot
  brought back the one effect it had).
* **The tablet** (SAGGA Live: MIDI FX, FX AMOUNT, FX GO): FX GO adds the effect shown to the chain of the tablet's
  track, again takes it out; on OFF it stops them all. **The grid** (TRACK 3, row 2): every effect that plays is white;
  a tap on one that plays stops it, a tap on another makes it READY (orange), again: it starts. **The Pi's editor**
  shows the chain: a box per effect and its values.

### A chain on the hub too (RaspiMIDIHub's plugins)

RaspiMIDIHub's own plugins (Velocity Curve, Velocity Equalizer, Note Transpose, Scale Remapper, Chord Generator, Hold,
MIDI Delay, Arpeggiator ...) chain in the hub's matrix, one's OUT into the next one's IN. Use them for what the FM-1
does not do (MIDI Delay: up to 10 repeats, in time or in ms; Hold; +/-48 semitones). Keep on the FM-1 what must follow
the key and the progression (HARM IN KEY, CHORD DIATONIC): the plugins do not know SAGGA's key, and the FM-1 does not
know the hub's chain (not on its screen, not in the project: it is in the hub's config).

1. Add the plugins in the order they should play (for instance Velocity Equalizer, then MIDI Delay).
2. Matrix: `Felucca MIDI 1` to the first plugin's IN, the cell filtered to the track's channel and **notes only**; each
   plugin's OUT to the next one's IN; the last OUT to the synth.
3. `Felucca MIDI 1` to the synth: the same channel, **everything but notes** (CC, pitch bend, aftertouch, program,
   clock). The plugins do not pass the clock on; the lanes and the LFOs reach the synth without a plugin in the way.
4. MIDI Delay with **Sync to Clock** follows the FM-1's clock by itself (the hub reads the clock of every device that
   sends one), and START / STOP clear its echoes.
5. Every plugin costs a few ms (a filtered cell of the matrix 1-3 ms): set the track's **DELAY** (HOME 7 K1) a little
   early, -5 ms, then by ear.

**The CC trap.** Most plugins come with CCs bound to their controls: MIDI Delay 74 / 75 / 76 (delay ms, repeats,
decay), Note Transpose 74 (semitones), Scale Remapper 74 (root), Chord Generator 76, Velocity Equalizer 74 / 75 / 76,
Arpeggiator 70 / 71 / 73 / 74 / 75 / 83. A bound CC is taken by the plugin and **does not pass**: lane 1 (CC 74, the
cutoff, the one the FILTER macro moves) sent into the chain would transpose the notes or move the root instead of
opening the synth's filter. Notes only into the chain (step 2) avoids it; or long-press the plugin's control and
**Clear**; or use it on purpose: a lane on CC 75 sent into MIDI Delay sets its repeats step by step (0-127: 0-10).

**Echoes.** MIDI Delay's echoes last 50 ms whatever the note (staccato on a pad: there, the FM-1's ECHO, which keeps the
gate). The FM-1's ECHO and MIDI Delay together multiply (2 repeats and 3 repeats: 12 notes for each note written): keep
one of them.

## What is new in 0.18.1

The PC test (the explorer on the real FM-1, docs/SAGGA-ESPLORATORE.md) sends MIDI too: the tablet's commands (channel 12,
channel 13's TRACK) and the grid's pads and buttons come in as if from the Pi, on the remote's port, so the explorer's
sessions try the tablet's track, the values going back, FOLLOW and the copy across the tracks on the hardware. Where the
FM-1 takes an event it now reports the clock tick before the event, not after (a grid's BAR jump moves the clock); the
probe carries the grid's FOLLOW, the tablet's track and whether the tablet has spoken. Nothing changes on the panel, the
tablet or the grid.

## What is new in 0.18

**Three brains, one set: the FM-1, the tablet and the grid at once.** The FM-1 is the centre; the tablet (the hub's
pages) and the grid each do something else at the same time, and they never lose each other.

* **The tablet has a track of its own.** What the hub's pages send on channels 13 and 14 (the pads, the lanes, TAKE,
  the LFO, MODE, the patterns ...) acts on **the tablet's track**, chosen with TRACK (channel 13 CC 112, on SAGGA
  Live, Motori and Mod); the FM-1's track, page and cursor stay where your other hand is. The tablet has its own LFO
  too (SAGGA Mod's LFO knob). The FM-1's screen says when the tablet did something: `TAB T5: LFO ON`, `TAB T3 MIDI FX
  ECHO READY: GO` (the tablet's GO is the panel's SEQ + white 6). Until 0.17 the tablet acted on the FM-1's track.
* **SAGGA Live, a new page for the hub** (channel 12, see "Channel 12"): everything of the tablet's track at hand -
  MUTE, SOLO, PATTERN, LENGTH, OCTAVE, RETRIG, SWING, GROOVE, FOLLOW, the ARP (mode, octaves, rate, run), the CHORD,
  the MIDI FX (READY, amount, GO), an ALGORITHM (READY, A B C, GO), EUCLID, COOK, BEAT, a PROPOSAL and QUEUE, DICE with
  KEEP / BACK, UNDO (on that track only, whatever the SCOPE), and the sixteen MUTES.
* **The FM-1 sends its values back to the hub** (with USB PORTS 2, on port 2, once the hub has said something there;
  0.20.8: anything, the grid bridge's keep-alive too, so from the start):
  turn a knob on the FM-1 and the knob on the tablet moves; a mute on the panel lights on SAGGA Live; the patterns
  and lengths of SAGGA Motori, the tablet's LFO and lanes on SAGGA Mod, the macros, MORPH, QUANTISE and TRANSPOSE of
  SAGGA Remote follow. A value the tablet is moving is left alone while the hand is on it (0.4 s). In the hub's
  matrix: the FM-1's port 2 to each page's IN (see "What goes back to the hub").
* **The grid FOLLOWs the FM-1** (SHIFT + STEP twice: CC, then FOLLOW; it was PICK): its view goes with the FM-1's
  page - the steps, PERF (the MOSSE: VIAGGIO), the LFOs, the FX, the lanes (ENV), else the four knobs of the page open.
  On that view rows 1-4 are the knobs' values (as PICK), **rows 5-8 the same knobs across the sixteen tracks** (the
  FM-1's track white, the tracks with its value lit): a tap gives that track the value, SHIFT + a tap takes the FM-1
  to that track. A knob that is no track's (the key, the energy, the morph) has the black keys' values there, as PICK
  had. A view chosen by hand stops FOLLOW (SHIFT lit cyan while it follows); SHIFT + STEP twice: it follows again.
* **ARP RATE 1/2 and 1/4**: a note every 2 or 4 steps, left of ROLL on ARP 1 K3 (the knob: 1/4, 1/2, ROLL, 1, 2, 3, 4).
  A chord held over 16 steps with RATE 1/4 is four notes, one a beat; with RUN HOLD it goes on to the next chord.
* The 25th genre on SAGGA Mod's GENRE knob (MERENGUE). The doc's "Program Change per scene" is HOME page 5 K4.

## What is new in 0.17

**No VIAGGIO mode: the journey is part of every set.** Until 0.16 VIAGGIO was a keyboard of its own (SEL + GLO), where
the same keys did other things, and the journey ran only once it was switched on. In 0.17:

* **The journey always runs.** Its phrase counts from PLAY (16 bars; GLO 3 K2: 4, 8, 16), the queue runs at its end,
  the trail keeps every phrase. At energy 50 (the default) with nothing queued it changes nothing: the music plays as
  written. (0.9-0.16, VIAGGIO on: the LFOs at 75 % depth at energy 50; now 100 %, shallower below 50.)
* **The MOSSE are PERF's page 3** (GLO 3). **SEL + GLO** opens PERF on that page; SEL + GLO again: the studio. Its
  **black keys are the moves**, at the end of the phrase: 1 FILL, 2 BREAK (SEL: all, 2 bars), 3 RISER, 4 DROP, 5 HALF,
  6 DOUBLE, 7 THIN, 8 SWELL, **9 INDIETRO** (0.9-0.16: OCT-), **10 the last move cancelled** (0.9-0.16: OCT+), 11 NOW.
  The white keys stay PERF's mutes (MUTE QUEUE and QUANTISE bring tracks in and out on time). K1 the energy, K2 the
  phrase, K3 the genre and K4 the key (queued while playing), **ALG: MOVES AT** (phrase, bar, beat; 0.10-0.16: K2 in
  VIAGGIO mode), **PRESETS: the progression** (queued; with the HARMONY off it is READY, as ARP 3 K2 since 0.16).
  SEL + PLAY stopped: the SEED. GLO held on page 3: the same moves from any mode. On pages 1 and 2 the black keys are
  the scenes, as ever. The difference: **FX acts now, while you hold it; the MOSSE act at the end of the phrase, by
  themselves.**
* **The PROPOSALS are made in SEQ.** **SEQ + BEAT held 0.6 s** writes what BEAT would (SEQ's genre, part and variation)
  into a free pattern of the selected track, the pattern playing untouched: `PROPOSAL KICK #1 IN P2: PRESETS QUEUES
  IT`. Held again: the next variation, in the next free pattern. **PRESETS** (nothing held) then queues it first
  (`T1 PROPOSAL P2 QUEUED`): it plays at the QUANTISE, with its settings (length, division, swing, groove). A tap of
  BEAT writes on the pattern playing, as before (it acts when the key is let go, as UNDO and COOK). A proposal never
  takes a pattern written by hand: with no empty one the oldest proposal goes, else `NO FREE PATTERN`.
* **The set is always recorded.** **SAVE + white 16** turns the phrases played into scenes and the song, however you
  played them (with the MOSSE or without).
* The grid's VIAGGIO view and the remote on channel 13 work as before (the tracks EMPTY / PROPOSED / IN / OUT, the
  proposals, SWAP, LOOP); they switch nothing on any more. The grid's PERF button opens PERF first, always. The
  tracks' states follow the hands at every boundary (a mute in PERF, a scene, a pattern changed): THIN, SWELL and the
  trail see the music as it is. "No silence by mistake" (a track kept when the moves leave none) acts only when the
  moves made the silence: a silence made by hand stays.
* The PROGRESSION move no longer switches the HARMONY on: the progression changes at the boundary, the HARMONY stays as
  the hands left it.
* **PALCO** (SAVE + K4) starts on the MOSSE; SEQ pressed there no longer leaves PERF (PALCO has no SEQ).
* Projects: one saved with VIAGGIO off plays as it did (its energy comes back at 50); one saved with VIAGGIO on keeps
  its energy, phrase and states. A project of 0.17 loads on 0.16 with VIAGGIO on.

## What is new in 0.16

**A 25th genre: MERENGUE** (SEQ + PRESETS, the last: 24 turns from TECHNO), 128-156 BPM, major keys (MAJOR,
MIXOLYDIAN, MINOR), straight (swing 50). Its band (BAND, nine parts): **KICK** (the bass drum on every beat, as the
orquesta and merengue de calle play it), **SNARE** (the tambora's rim on the "and" of 2 and 4), **HAT** (the guira:
an 8th and two 16ths a beat, "cha chi-ki"; KIT note 69, cabasa), **PERC** (the tambora: its slap and the roll into the
bar; note 66), **CONGA**, **BASS** (anticipating the beat: root and fifth), **PIANO** (the offbeat montuno), **LEAD**
(the sax / accordion riff), **VOX** (the coro). Its progressions: I-V7, I-IV-V7-I, I-vi-ii-V7, I-IV-I-V7, I-ii-V7-I,
vi-IV-V7-I. Its GROOVE: the guira and the shaker PUSH 30 (a hair ahead), the tambora HUMAN 40, the rim HUMAN 30, the
rest straight. VIAGGIO: after the kick the guira and the tambora come first, BATIDA its neighbour. BREAK chops: STRAIGHT, SHUFFLE, REPEAT,
END ROLL. The grid's BEAT view has it on a third page of genres (PAGE violet). A project made by 0.16 with the merengue
loads on 0.15 with TECHNO in its place.

**A genre's patterns come with their GROOVE.** A pattern of the library (BEAT, BAND, KIT, GENRE LIVE, VIAGGIO's
proposals, the Pi's variations) used to bring only the genre's swing; now it brings the part's GROOVE too, and the
swing that goes with it. The hats, shakers and percussion carry the groove; the kick stays the anchor; the bass and
the chords keep the genre's swing. Where a template carries the shuffle (GARAGE, SAMBA) the drums are straight under
it (swing 50) and the bass and the chords take the swing that matches it (GARAGE 100 % is about swing 63, 60 % about
58): the parts still meet. **DICE GROOVE** keeps each part's template and moves its amount (± 20 %) and the swing a
little. A GROOVE or a swing set by hand is replaced by the next pattern loaded on that track, as the swing always was;
turn them afterwards for your own feel.

| genre | kick | snare / clap | hat / ride | open hat | shaker | perc / rim / conga / tom | bass | chords | arp / lead / vox |
|---|---|---|---|---|---|---|---|---|---|
| TECHNO (sw 50) | - | - | HOUSE 40 | - | HUMAN 30 | HUMAN 30 | - | - | - |
| HARDTECHNO (50) | - | - | PUSH 30 | - | PUSH 30 | PUSH 30 | - | - | - |
| DUB TECHNO (54) | - | - | HOUSE 50 | HOUSE 40 | HOUSE 50 | HUMAN 40 | - | LAID BACK 30 | LAID BACK 30 |
| HOUSE (54) | - | - | HOUSE 100 | HOUSE 60 | HOUSE 100 | HOUSE 60 | HUMAN 30 | HUMAN 30 | HUMAN 30 |
| UK GARAGE | GARAGE 100, sw 50 | GARAGE 100, sw 50 | GARAGE 100, sw 50 | GARAGE 100, sw 50 | GARAGE 100, sw 50 | GARAGE 100, sw 50 | sw 63 | sw 63 | sw 63 |
| UK FUNKY (56) | - | AFRO 40 | GARAGE 50, sw 50 | GARAGE 50, sw 50 | AFRO 80 | AFRO 80 | - | HUMAN 30 | - |
| GRIME (50) | - | - | TRAP 50 | - | TRAP 40 | HUMAN 30 | - | - | - |
| DUBSTEP (52) | - | - | LAID BACK 40 | LAID BACK 40 | LAID BACK 40 | LAID BACK 40 | - | - | - |
| JUNGLE (50) | HUMAN 30 | HUMAN 60 | PUSH 50 | PUSH 40 | PUSH 50 | HUMAN 50 | - | HUMAN 30 | - |
| BASSLINE | - (56) | - (56) | GARAGE 60, sw 50 | GARAGE 60, sw 50 | GARAGE 60, sw 50 | GARAGE 60, sw 50 | sw 58 | sw 58 | sw 58 |
| REGGAETON (50) | - | AFRO 60 | TRAP 40 | - | AFRO 50 | AFRO 60 | - | - | - |
| BATIDA (52) | - | AFRO 40 | AFRO 60 | AFRO 40 | AFRO 80 | AFRO 100 | - | - | - |
| GQOM (54) | - | - | AFRO 50 | - | AFRO 60 | AFRO 80 | - | - | - |
| EXPERIMENT (50) | HUMAN 30 | DILLA 40 | DILLA 60 | DILLA 40 | DILLA 60 | DILLA 60 | HUMAN 50 | HUMAN 50 | HUMAN 50 |
| ELECTRO (50) | - | - | TRAP 40 | - | TRAP 30 | HUMAN 20 | - | - | - |
| DRUM+BASS (50) | - | - | PUSH 40 | PUSH 30 | PUSH 40 | HUMAN 30 | - | HUMAN 30 | - |
| AFRO HOUSE (54) | - | - | HOUSE 70 | HOUSE 50 | AFRO 100 | AFRO 100 | HUMAN 30 | HUMAN 30 | HUMAN 30 |
| AMAPIANO (58) | - | - | AFRO 60 | AFRO 40 | AFRO 80 | AFRO 80 | - (the log drum too) | LAID BACK 40 | LAID BACK 30 |
| FOOTWORK (50) | - | - | TRAP 60 | - | TRAP 40 | HUMAN 30 | - | - | - |
| TRANCE (50) | - | - | - | - | - | - | - | - | - |
| UK DRILL (54) | - | - | TRAP 100 | TRAP 60 | TRAP 60 | TRAP 60 | - | - | - |
| HARDCORE (50) | - | - | PUSH 40 | PUSH 30 | PUSH 40 | PUSH 30 | - | - | - |
| PHONK (52) | - | - | TRAP 80 | TRAP 50 | TRAP 50 | HUMAN 20 | - | LAID BACK 30 | LAID BACK 30 |
| BAILE FUNK (54) | - | AFRO 50 | SAMBA 80, sw 50 | SAMBA 60, sw 50 | SAMBA 100, sw 50 | SAMBA 100, sw 50 | - | - | - |
| MERENGUE (50) | - | HUMAN 30 | PUSH 30 | - | PUSH 30 | HUMAN 40 | - | - | - |

(sw: the swing; in brackets the genre's, which every part has where nothing else is said. The crash goes with the
kick, the rim with the percussion, the sub, the rumble and the log drum with the bass, the stab, pad and piano with
the chords.)

**The algorithms are set up before they play.** Until 0.15, K1 on SEQ 2 started an algorithm at once with its
default values, and the first touch of EUCLID's knobs switched EUCLID LIVE on with what they had: live, the track
jumped somewhere before you could set it. Now **K1 makes the algorithm READY** on the slot (the screen: `ALGO 1 READY
TURING`, the grid's pad orange), **K2-K4 set its values**, and **SEQ + white 6 starts it with them** (`T1 ALGO 1:
TURING STARTS`). While it plays, K2-K4 change it as before. SEQ + white 6 again stops it (`TURING STOPS (READY
AGAIN)`): its values stay, and the next SEQ + white 6 starts it the same. While one plays, K1 on another makes that
one READY and K2-K4 set it; the one playing goes on until SEQ + white 6 swaps them (K1 back on the one playing: its
knobs again; K1 on OFF: SEQ + white 6 stops it). Each algorithm of each slot keeps its own values while the FM-1 is on
(the project saves the one that plays). **EUCLID** the same: with EUCLID LIVE off its knobs set it up (`EUCLID READY
T1: 5/16 ROT 2 SEQ + WHITE 6 STARTS IT`), SEQ + white 6 starts it (on the scope, as before); on, they change it as it
plays. SEQ + white 6 is EUCLID LIVE on every SEQ page but SEQ 2, where it is the slot's algorithm. The grid's TRACK 3
view: a tap on an algorithm makes it READY (orange), a second tap starts it (white), a tap on the one playing stops
it; its rows 4-5 set the READY one. Its EUCLID view: the pulses and the rotation of a row whose EUCLID LIVE is off are
set up, pad 1 starts it.

**The same elsewhere.** The **HARMONY**: with it off, ARP 3 K2 chooses the progression (`READY TECHNO i-VII-VI-VII: K1
ON`) and K1 starts it (until 0.15 turning K2 switched the HARMONY on). **EXPO** (SEQ 4): with SHAPE OFF, K1-K3 set it
up (`EXPO READY: K4 SHAPE STARTS IT`), K4 starts it with them (until 0.15 the first touch switched it on, on RAMP). A
**MIDI FX** the same way: HOME 6 K1 makes an effect READY (`T1 MIDI FX ECHO READY: SEQ + WHITE 6`; what plays goes
on), K2-K4 set its values, **SEQ + white 6** starts it (with K1 just turned on the selected track that key acts on the
MIDI FX, not EUCLID; HOME + white 6 stays track 6). **0.19: it joins the chain** - the others keep playing; K1 on one
that plays, then SEQ + white 6: it leaves; K1 on OFF, then SEQ + white 6: they all stop. Each effect keeps its own
values (0.19: in the project; its defaults only the first time; until 0.15 its defaults every time it was chosen, and
at once). The grid's TRACK 3 row 2: a tap READY (orange), again: it starts; a tap on one that plays (white): it stops. ARP and CHORD were already so: the
octaves, RATE, RUN, the voicing and the strum are the track's and stay when the mode or the shape changes (set them
with the mode on BLOCK, the shape OFF, then choose); the LFOs, EVOLVE, the GROOVE amount too.

**Harmony FREE.** ARP 4 K2, one to the left of the first genre: **FREE**. The chords are nobody's genre: ARP 3 K2
walks through all 150 progressions of the library (6 of each of the 25 genres, in the genre's order: `TECHNO 1` ..
`MERENGUE 6`), then the USER ones and DICE/PI; with a MOOD (ARP 4 K3) only those of that mood. A pattern loaded, BAND,
GENRE LIVE or VIAGGIO's genre do not move the harmony any more (without FREE the harmony follows the genre of what is
loaded, as in 0.11). ARP 4 K2 to the right: the genres again. Saved with the project.

**Copy a progression into a USER slot: EDIT + ARP.** The progression that plays (one of the library, a USER, the
Pi's) is written into a USER slot, chord by chord with its shapes: the one shown on ARP 5 if it is not the one
playing, else the first empty one (`COPIED TO USER 2: ARP 5 TO CHANGE IT`). It plays from the copy at once (it sounds
the same) and ARP 5 / ARP 6 change it: a chord, its root, its shape, its length. Over a slot that has a progression the
FM-1 asks first (`COPY OVER USER 1: EDIT+ARP AGAIN`, within 3 s).

**A note on FOLLOW.** A track with FOLLOW keeps the rhythm written in it: the harmony changes its notes (the pitch, in
steps of the scale), never where they fall or how long they last. Only RETRIG and LEGATO act on a note held across a
chord change (RETRIG strikes it again on the new chord, LEGATO bends it there). A pad that should follow the harmonic
rhythm: one long note (a long gate or TIE) with FOLLOW RETRIG.

## What is new in 0.15

**Clear a slot.** Choose the slot (SAVE + PRESETS), then **SAVE + REC**: `CLEAR SLOT 3 MY SONG: SAVE+REC AGAIN`; again
within three seconds: `SLOT 3 CLEARED: THE PROJECT YOU HAVE STAYS`. The slot is `EMPTY` from then on (after a power
cycle too: every copy of it in the flash loses its header); the project in the FM-1 is not touched, SAVE puts it in any
slot. Only while stopped (`CLEAR A SLOT: STOP FIRST`); an empty slot says `NOTHING TO CLEAR`.

**The project's name.** A project has a name of up to 16 characters (A-Z, 0-9, space and `- _ . + # & ! ' ( ) / :`).
The Pi's editor writes it (Progetto, **NOME**; **Nuovo** names the project after its file; a file of the library loaded
from the grid's LIB view that has no name takes the file's). The FM-1 shows it: SAVE held (page 1), lines 3 and 4 say
`SLOT 3: MY SONG` (`NO NAME`, `EMPTY`) and `NOW: <the project in the FM-1>`; LOAD asks `LOAD SLOT 3 MY SONG: HOME+SAVE
AGAIN` and says `LOADED SLOT 3: MY SONG`. The slot keeps the name in its header page, so choosing a slot shows it
without reading the project; a slot saved by 0.14 has no name until it is saved again. (SAVE held shows the names in
place of the key map on page 1; the map is on pages 2-4.)

**GROOVE.** HOME 7 K3 / K4 on a track that is not TAPE: a template and how much of it, 0-100 %. A template moves each
16th of the bar a little early or late (a percentage of the step, on top of the step's nudge, the swing and HUMAN) and
makes it louder or softer: **HOUSE** (the 16ths a touch late, the offbeat 8th up), **GARAGE** (the 2-step shuffle),
**DILLA** (drunk: never twice the same), **AFRO** (3 + 3 + 2, pushed), **SAMBA** (the second and fourth 16th early),
**LAID BACK** (behind the beat), **PUSH** (ahead of it), **HUMAN** (a player's small misses), **TRAP** (tight, the
accents do it). A template chosen at 0 % takes 100 %. On a TAPE track K3 / K4 are its TAPE BARS and TAPE QUANT, as
before. PICK sets the template with the whites; saved with the project (a 0.14 firmware ignores it).

**The editor follows the music, and plays what you touch (the Pi).** In the editor's header: **segui l'FM-1** marks,
while the FM-1 plays, the step each track is on (a white frame; a track on another pattern says `▶P3`), the tempo, the
scene; in the Tape view a line runs through the loop. **ascolta**: a step turned on, a note of the roll touched or
moved, is played by the FM-1 on that track (its channel, key, CHORD, voicing; a TAPE note as the tape plays it), and the
step panel has **♪ ascolta**. Both need the grid bridge running (it holds the FM-1's port; from 0.15 it runs without the Launchpads too, and starts
again with them when they are plugged in); the FM-1 sends positions only while the Pi asks for them (SysEx 30, 31, 32
below).

**TAPE tracks in the editor.** The **Tape** tab: a piano roll of a track's tape (384 ticks a beat, the loop of TAPE
battute). Tap the empty roll: a 16th note there; drag a note to move it (in 16ths with **griglia 1/16**, else in steps of
12 ticks, a 32nd of a beat), drag its right edge to make it longer; Canc takes the chosen one away; below, the chosen
note's start, length, pitch and velocity by number. The loop's bars and TAPE QUANT are on the same row. Saved like the
rest (versions, the firmware's checks: a note past the end of the loop is dropped, and the page says how many). The
Traccia tab shows TAPE BARS / TAPE QUANT on a TAPE track, the GROOVE on the others; **Tracce** links a TAPE track to its
roll. (The 0.14 editor's mode menu set the wrong bits for TAPE and BREAK: fixed.)

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
  K1-K3 switches it on (RAMP); **0.16: they set it up (`EXPO READY`), K4 SHAPE starts it**. **EDIT + black 5** makes the cursor step **PLAIN**: a span that begins on it plays its
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
* **VIAGGIO** works with all the genres (the ladders are the library's); you choose each track's **role** (K3) and
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
  TRANSPOSE, the harmony, every track's settings (channel, loop, swing, EUCLID, algorithm, CC lane bases; 0.19: not
  the MIDI FX chain, which is the track's),
  the LFOs, the tempo if you want. They come back at the QUANTISE moment. Their **sound** goes with them: the CC lanes'
  base values, and the synths' own CC values that **CC CAPTURE** took while you turned the synths' knobs. **PATCHES**:
  the Raspberry Pi keeps the synths' patches (SysEx) for a snapshot and sends them back when it returns.
* **MIDI FX per track** (HOME page 5; 0.19: page 6, the four in a chain): HARM (a second voice, steps of the key),
  OCTAVE (jumps on alternate / random / every 3rd / 4th step), ECHO (1-4 repeats, 1/32 .. 1/4 dotted, how much each
  keeps), VEL CURVE. **FX + OCT+**: an ECHO on every track at once.
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
