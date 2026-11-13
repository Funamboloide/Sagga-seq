/* SPDX-License-Identifier: GPL-3.0-only */
/* 0.10: names for the CC numbers of the lanes and the LFOs, by the synth on the channel. GENERIC: the MIDI
 * specification's controllers. ELEKTRON: the numbers Digitakt, Digitone and Syntakt share for the filter, the amp,
 * the LFO and the sends (check the box's manual for the rest). Included by sagga_seq_core.c. */
typedef struct { uint8_t cc; const char *name; } sq_ccname_t;

static const sq_ccname_t CC_GENERIC[] = {
    {1u, "MOD"}, {2u, "BREATH"}, {4u, "FOOT"}, {5u, "PORTA T"}, {7u, "VOLUME"}, {8u, "BALANCE"}, {10u, "PAN"},
    {11u, "EXPR"}, {12u, "FX 1"}, {13u, "FX 2"}, {64u, "SUSTAIN"}, {65u, "PORTA"}, {66u, "SOSTEN"}, {67u, "SOFT"},
    {68u, "LEGATO"}, {70u, "VARIAT"}, {71u, "RESO"}, {72u, "RELEASE"}, {73u, "ATTACK"}, {74u, "CUTOFF"}, {75u, "DECAY"},
    {76u, "VIB RATE"}, {77u, "VIB DEP"}, {78u, "VIB DEL"}, {84u, "PORTA N"}, {91u, "REVERB"}, {92u, "TREMOLO"},
    {93u, "CHORUS"}, {94u, "DETUNE"}, {95u, "PHASER"}, {120u, "SOUNDOFF"}, {121u, "RESET"}, {123u, "NOTESOFF"},
    {128u, "BEND"}, {129u, "AFTERT"},
};
static const sq_ccname_t CC_ELEKTRON[] = {
    {7u, "AMP VOL"}, {10u, "PAN"}, {94u, "MUTE"}, {95u, "LEVEL"},
    {70u, "FLT ATK"}, {71u, "FLT DEC"}, {72u, "FLT SUS"}, {73u, "FLT REL"}, {74u, "FLT FREQ"}, {75u, "FLT RESO"},
    {76u, "FLT TYPE"}, {77u, "FLT ENV"},
    {78u, "AMP ATK"}, {79u, "AMP HLD"}, {80u, "AMP DEC"}, {81u, "OVERDRV"}, {82u, "DELAY S"}, {83u, "REVERB S"},
    {102u, "LFO SPD"}, {103u, "LFO MUL"}, {104u, "LFO FADE"}, {105u, "LFO DST"}, {106u, "LFO WAV"}, {107u, "LFO PHA"},
    {108u, "LFO TRG"}, {109u, "LFO DEP"},
    {128u, "BEND"}, {129u, "AFTERT"},
};
