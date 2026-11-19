# SAGGA SEQ 0.29

![SAGGA SEQ on the FM-1's screen](docs/screen.png)

SAGGA SEQ turns the M-VAVE FM-1 into a MIDI-only performance sequencer: 12 tracks on 16 MIDI channels (0.28: chords of
six notes a step, eight CC lanes a track), 8 patterns of up to 64 steps per track (0.24: the length is the track's - a pattern goes round again in a longer track, a length changed while it plays lands on the bar line), a bar in any metre and tracks in five or seven against four (0.25: 7/8, 5/4, 15/16 ...; the polyrhythms' steps played between the clock's ticks; 0.26: the engines make a part IN that bar, a click on its beats, the scenes bring their metre; 0.27: the profile SEMPLICE hides the lab's pages), scenes, snapshots, a song, 16 LFOs, 16 keys, a library of 22 genres (0.29: BALANI is new, four went into others; a band of 8 to 11 parts each, 12
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

The package identity is `FM-1_9` + (50 + the minor version): 0.9 is `FM-1_959`, 0.10 is `FM-1_960`, 0.11 is `FM-1_961`, 0.12 is `FM-1_962` ... 0.18 and 0.18.1 are `FM-1_968`, 0.19 is `FM-1_969`, 0.20 is `FM-1_970`, 0.21 is `FM-1_971`, 0.22 is `FM-1_972`, 0.23, 0.23.1 and 0.23.2 are `FM-1_973`, 0.24 is `FM-1_974`, 0.25 is `FM-1_975`, 0.26 is `FM-1_976`, 0.27 is `FM-1_977`, 0.28 and 0.28.1 are `FM-1_978`.

## Docs

* [docs/SAGGA-SEQ.md](docs/SAGGA-SEQ.md): the reference (every control, the SysEx, the remote's CCs).
* [docs/SAGGA-GRID.md](docs/SAGGA-GRID.md): the grid, the bridge on the Pi, the snapshot patches.
* [docs/INSTALLA.md](docs/INSTALLA.md): install and update the three parts, the FM-1, the Pi and the grid (Italian).
* [RELEASE-NOTES-0.29.md](RELEASE-NOTES-0.29.md): what changed in this version (Italian): 22 genres (AMAPIANO into REGGAETON, BASSLINE into UK GARAGE, GRIME into DUBSTEP, AFRO HOUSE into GQOM and BATIDA; BALANI new, with the BALAFON), eight progressions a genre, REGGAETON and BALANI's THEORY rules written by hand, ROLL and ACCENT, five scales, three grooves, four chord shapes. 0.28.1's (the SAGGA Mod page with all eight lanes): [docs/storia/RELEASE-NOTES-0.28.1.md](docs/storia/RELEASE-NOTES-0.28.1.md). 0.28's (twelve tracks, chords of six notes, eight CC lanes a track): [docs/storia/RELEASE-NOTES-0.28.md](docs/storia/RELEASE-NOTES-0.28.md); the earlier ones are beside it, in [docs/storia/](docs/storia/).
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
  break-down to build-up) (Italian).
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
./build.sh --release 0.28.1       # identity FM-1_978
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
each, the snapshots (sparse), the project's id (the Pi keeps the snapshot patches by it) and a tail of tagged chunks,
so a later version can add data without a new format.

## USB

One USB-MIDI port by default (the grid on channels 15 / 16, the tracks on 1-14). USB PORTS 2 (SAVE page 3,
K1; SEL + K1 twice reconnects) gives two: port 1 the synths with 16 channels, port 2 the grid, the remote and the SysEx.

## Credits and licence

GPL-3.0-only (`LICENSE`). SAGGA SEQ stands on [Felucca](https://github.com/hugelton/Felucca) (Leo Kuroshita,
Hügelton Instruments), [SLOOP](https://github.com/isod89/sloop-fm1) (isod89) and Dinghy (zvenson): who made what is in
[LICENSING.md](LICENSING.md).
