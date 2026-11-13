# strati — from samples and stems to synth patches

strati listens to a sound and splits it into **layers** (*strati*):

- the **tonal** layer: the harmonics of a note over time, or the modes of a drum or a bell (partials that are not harmonics);
- the **noise** layer: 24 bands over time (a breath, a pick, a snare's wires, a hi-hat).

Each layer has its own envelope. The result is a **recipe** (`recipes/<name>.json`), and every synth's patch is made from it. Each patch is then improved by trial and error: the patch is played (in a model of that synth), compared with the original, nudged, and played again.

This is **resynthesis**: the patch plays the sound with the synth's own oscillators, filters and envelopes, at any note. It does not use the sample.

## Use

```
python3 -m strati convert FOLDER [--out OUT] [--budget SECONDS]
```

Run it from `tools/strati`. It needs Python 3, numpy, scipy and ffmpeg.

| in FOLDER | what strati does |
|---|---|
| `one-shot/` (or `oneshot/`, `hits/`, `drums/`) | every file is one sound |
| `stems/` (or `loops/`) | every file is cut at its onsets; the different sounds (at most 8) become patches, and repeated hits are grouped |
| anything else | a file under 3 s is one sound; a longer one is treated as a stem |

Formats: wav, mp3, flac, aiff, ogg and m4a.

`OUT` (default `FOLDER/patches`) gets:

| file | what it is |
|---|---|
| `recipes/<name>.json` | what the analysis heard |
| `preview/<name>-recipe.wav` | the recipe played back: what the layers hold, with no synth in between |
| `surge/<name>.fxp` | the Surge XT patch (for Zynthian) |
| `preview/<name>-surge.wav` | strati's model of that patch |
| `norns/<name>.strati` | a sound for the strati script on Norns |
| `preview/<name>-norns.wav` | that sound as the script's engine plays it |
| `relitto/<name>.syx` | the Relitto sound: a USER table and its parameters (`python3 -m strati send FILE.syx` loads it into the FM-1) |
| `relitto/<name>.txt` | the same sound as knob values, page by page |
| `preview/<name>-relitto.wav` | that sound played by Relitto's own engine (host mode: the real one, bit for bit) |
| `report.txt`, `report.json` | every sound, its layers, and how close each step got |

### Reading the report

The distance is in dB: the mean gap between two spectrograms at the same loudness.

- 0 means the same sound.
- About 3 is close.
- Two different noises score about 3, because no two noises are alike sample by sample.
- Over 10 is another sound.

## Pads: `strati pad`

```
python3 -m strati pad FILE [--start S] [--length S] [--name NAME] [--out OUT]
```

This is for a held, chordal part over a noise bed, even inside a full mix. strati finds:

- the record's tuning;
- the notes, frame by frame: the strongest note, its harmonics taken out, then the next;
- the chords (anything under E3 counts as bass and is left out of the pad);
- the timbre of one voice: each harmonic against the fundamental, measured only where no other note covers it;
- the noise bed, from the low quarter of the spectrum, where the chord's partials do not reach.

How the noise moves becomes **one control**, the mod wheel. At 1 the noise is as open and loud as it gets; at 0 it is 14 dB quieter and low-passed at 2.5 kHz instead of 16 kHz.

| output | what it is |
|---|---|
| `norns/NAME.strati` | 12 harmonics, each played by two sines 10 cents apart, and the noise bands. The mod wheel (CC 1) drives the noise. |
| `surge/NAME.fxp` | Scene A: the wavetable with 2 unison voices at ±10 cents. Scene B: the noise through a 12 dB low-pass. The mod wheel raises the noise's level and cutoff. |
| `dexed/NAME.syx` | A DX7 bank for MicroDexed-touch and for Dexed on Zynthian. Algorithm 5: three FM stacks fitted to the harmonics, two of them detuned. No noise yet: on MicroDexed-touch that layer will be Braids. |
| `recipes/NAME-performance.json` | The notes and the noise control as the original played them |
| `preview/NAME-*.wav` | That performance played by each patch (in strati's models), at the original's loudness |

## Relitto

Relitto (the wavetable synth for the FM-1, 0.2 or later) is the one target whose preview is the **real engine**: strati compiles Relitto's host mode from its source (`STRATI_RELITTO=/path/to/relitto`, or a `relitto` folder next to this repository) and plays every sound through it, so the trial and error turns the knobs against the original with the sound the FM-1 will make.

| the sound | what Relitto gets |
|---|---|
| pitched | OSC A = a USER table of 16 frames: frame 15 is the start of the sound, frame 0 its end; ENV 2 sweeps the position down along its own decay, and the frames are sampled where that curve puts them |
| drum, bell | the same table built on a fraction f0/q of the pitch, so that the modes fall on harmonics (q picked for the least error in cents); the table carries a root offset that puts the note back in tune |
| noise layer | OSC B = NOISE, its colour from the noise's centroid; when the noise decays faster than the tone, its level follows ENV 2 |
| only noise | NOISE on OSC A through the filter (band-pass on a narrow noise), ENV 2 on the cutoff when it darkens |
| pitch envelope | a kick, a tom, a sweep: ENV 2 to the pitch (±48 semitones), found by the analysis (`pitch_env` in the recipe) |
| pad | frames all alike; OSC B the same table 10 cents away, or NOISE on the mod wheel (level and colour) when the noise matters |

`strati send FILE.syx [--port NAME] [--slot 0-3]` loads a sound into one of the FM-1's four USER slots over USB-MIDI (mido, python-rtmidi), waiting for the FM-1's answer to every frame. The sound plays as soon as it is in, and is kept in the slot (program change 8–11, or the PRESETS knob past the factory presets).

## The Surge XT patch

**Pitched sound:** scene A gets a 16-frame wavetable built from the harmonics, sampled along the sound. The filter EG sweeps through the frames, so the timbre changes over time as the original does. The amp EG is fitted to the sound.

**Drum or bell:** scene A gets up to 3 sine oscillators, one on each of the strongest modes.

**Noise layer:** scene B gets the noise generator. Its colour comes from the noise's slope, and a 12 dB band-pass or low-pass follows the noise's centroid with its own EG. A pitched sound keeps a noise layer only when the noise holds over 15 % of the sound's energy.

**Both layers:** dual scene mode, so one note plays both.

Patches are in category `STRATI`. The template is Surge's own "Init Wavetable" (CC0).

**Not yet verified:** strati's model of Surge (`surge.simulate`) is an approximation, written from Surge's source. The patches are correct as files: Surge's format, read back here. Their sound still has to be checked in the real Surge, on the Pi (`strati verify`, next step).

## Norns

The `strati` script (`norns/strati`) has its own SuperCollider engine. It plays the recipe more directly than any other target:

- **24 sines**, each at its own ratio of the note (harmonics, or a drum's modes), each with its own envelope;
- **24 noise bands**: white noise through a band-pass, each band with its own envelope.

Every envelope has 12 points. The last point holds while the key is down; then comes the release. The band gains are solved together, so the overlapping band-passes add up to the noise's real spectrum.

**Install:**

1. Copy `norns/strati` to `dust/code/strati`.
2. Copy the `.strati` files to `dust/data/strati/sounds/`.
3. The first time only, restart Norns (SYSTEM > RESTART) so the new engine is compiled.

**Play:**

- MIDI notes play the selected sound on the chosen port and channel ("all" by default).
- Program change picks the sound.
- E2 changes the sound; E3 sets the volume.
- K2 plays the sound at its original note; K3 an octave up.

| parameter | what it does |
|---|---|
| noise follows note | 0: the noise stays where it was (a snare's wires); 1: it moves with the note |
| voices | 6 by default; a Norns plays about that many of these voices at once |

**Not yet verified:** SuperCollider is not installed where strati was written. The engine has been checked against the file format and by reading, not run. It will be tested on the Norns.

## Next

| target | output |
|---|---|
| MicroDexed-touch | a performance with Dexed, Braids and MSynth layers on one MIDI channel |
| Relitto | the Pi's hub page sends the .syx itself; a second ENV for the noise; the pitch envelope on the other targets |
| M8 | a song with instruments layered on tracks that share a channel |
| Pi | automatic conversion when a stick is inserted, a web page for uploading, and copying to Zynthian |
