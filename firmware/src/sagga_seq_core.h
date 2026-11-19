/* SPDX-License-Identifier: GPL-3.0-only */
#ifndef SAGGA_SEQ_CORE_H
#define SAGGA_SEQ_CORE_H

#include <stdint.h>

#define SQ_TRACKS   12u      /* 0.28: twelve (were sixteen): the memory went to the chords of six notes and the eight lanes. The
                              * image still has the sixteen of 0.27 (sagga_img27.h), the last four empty */
#define SQ_TRACK_BITS ((1u << SQ_TRACKS) - 1u)   /* 0.28: a bit for each track */
#define SQ_PATTERNS 8u
#define SQ_STEPS    64u
#define SQ_SCENES   16u      /* 0.9: sixteen (SGQ8 images carry eight; SALVA VIAGGIO fills them from the trail) */
#define SQ_SCENES8  8u       /* ... what a 0.8 image holds, and what the panel's black keys reach without the bank */
#define SQ_SNAPS    8u       /* SNAPSHOTS: the whole live state, eight of them (0.8) */
#define SQ_SNAP_CC  48u      /* the synth CC values a snapshot keeps (captured from the synths, sent when it comes back) */
#define SQ_POLY     6u       /* 0.28: the notes a step holds (were four) - as many as a chord shape plays (SQ_POLY_OUT) */
#define SQ_LANES    8u       /* CC lanes per track: a value per step that is sent when the step plays (0.10: six, were four;
                              * 0.28: eight) */
#define SQ_LFOS     16u
#define SQ_CHANNELS 16u      /* what is kept per MIDI channel (arrays) */
#define SQ_MIDI_CH  14u      /* the channels tracks play on with one USB port: 15 and 16 carry the grid (0.8: two USB
                              * ports give the tracks all 16, dinghy.c: track_ch) */

#define SQ_NOTE_NONE 255u
#define SQ_LANE_NONE 255u    /* a lane with no lock on this step / a lane with no CC / a lane with no base value */
#define SQ_CC_BEND 128u      /* 0.10: a lane or an LFO on pitch bend instead of a CC (64 = centre) */
#define SQ_CC_AT   129u      /* 0.10: ... on channel aftertouch */
#define SQ_CC_MAX  129u

#define SQ_STEP_ON   0x01u
#define SQ_STEP_SET  0x02u   /* the step has been programmed once (its note is the player's, not the default) */
#define SQ_STEP_LOCK 0x04u   /* EVOLVE and dice leave this step exactly as written */
#define SQ_STEP_XOFF 0x08u   /* 0.10: a plain step on an EXPO track: it plays as written, no curve (EDIT + black 5) */
#define SQ_STEP_TIE  0x10u   /* 0.10: legato: the note ends after the next step's note has begun (a mono synth slides) */
#define SQ_STEP_SLIDE 0x20u  /* 0.13: TIE, and the next note glides into place: portamento on (CC 65) for that note (the 808) */
#define SQ_STEP_GHOST 0x40u  /* 0.24: an automatic COPY: the pattern going round again in a track longer than it is (sq_row_fit).
                              * In the image the flag is not in the step (a copied rest costs nothing): chunk 3 says which steps */
#define SQ_STEP_FLAGS (SQ_STEP_ON | SQ_STEP_SET | SQ_STEP_LOCK | SQ_STEP_XOFF | SQ_STEP_TIE | SQ_STEP_SLIDE | SQ_STEP_GHOST)
#define SQ_STEP_LEGATO (SQ_STEP_TIE | SQ_STEP_SLIDE)   /* 0.13: the note holds into the next step (TIE, or SLIDE) */

#define SQ_RATCHET_MAX 8u    /* repeats per step (BLOCK) or notes per step (ARP) */
#define SQ_NUDGE_MAX   50u   /* % of a step a step can be moved: + late, - early */
#define SQ_SWING_MIN   50u   /* % of the pair of steps where the second one starts (50 = straight, 66 = triplets) */
#define SQ_SWING_MAX   75u
#define SQ_ARP_MAX     18u   /* 6 notes x 3 octaves (a chord shape plays up to SQ_POLY_OUT) */
#define SQ_ARP_OUT     (2u * SQ_ARP_MAX)   /* room for the longest sequence (up & down) */

enum {
    SQ_CLOCK_MASTER = 0,
    SQ_CLOCK_SLAVE  = 1
};

enum {
    SQ_DIR_FWD = 0,
    SQ_DIR_REV,
    SQ_DIR_PINGPONG,
    SQ_DIR_RANDOM,
    SQ_DIR_COUNT
};

/* A step lasts this many ticks of the 24 PPQN clock (see sq_div_ticks). Longest first. */
enum {
    SQ_DIV_1_1 = 0,    /* 96 */
    SQ_DIV_1_2,        /* 48 */
    SQ_DIV_1_4D,       /* 36 dotted quarter */
    SQ_DIV_1_4,        /* 24 */
    SQ_DIV_1_8D,       /* 18 dotted eighth */
    SQ_DIV_1_4T,       /* 16 quarter triplet */
    SQ_DIV_1_8,        /* 12 */
    SQ_DIV_1_16D,      /*  9 dotted sixteenth */
    SQ_DIV_1_8T,       /*  8 */
    SQ_DIV_1_16,       /*  6 */
    SQ_DIV_1_16T,      /*  4 */
    SQ_DIV_1_32,       /*  3 */
    SQ_DIV_1_32T,      /*  2 */
    /* 0.25 the POLYRHYTHMS: five or seven steps in the time of four - a step is not a number of ticks (sq_div_frac) */
    SQ_DIV_1_4Q5,      /* 96/5: five steps in the time of four quarters (a 4/4 bar) */
    SQ_DIV_1_8Q5,      /* 48/5: ... of four eighths */
    SQ_DIV_1_16Q5,     /* 24/5: ... of four 16ths (a quintuplet of 16ths) */
    SQ_DIV_1_4Q7,      /* 96/7: seven steps in the time of four quarters */
    SQ_DIV_1_8Q7,      /* 48/7 */
    SQ_DIV_1_16Q7,     /* 24/7 */
    SQ_DIV_COUNT
};
#define SQ_DIV_PLAIN 13u         /* the divisions that are a number of ticks: 0 .. 12 (a 0.24 firmware reads the others as 1/16) */

enum {
    SQ_COND_ALWAYS = 0,
    SQ_COND_1_2,
    SQ_COND_2_2,
    SQ_COND_1_4,
    SQ_COND_2_4,
    SQ_COND_3_4,
    SQ_COND_4_4,
    SQ_COND_FILL,
    SQ_COND_NOT_FILL,
    SQ_COND_1_3,               /* 0.10 */
    SQ_COND_2_3,
    SQ_COND_3_3,
    SQ_COND_1_8,
    SQ_COND_FIRST,             /* the first loop after PLAY (or a restart) only */
    SQ_COND_PRE,               /* plays if the step before it played */
    SQ_COND_NOT_PRE,
    SQ_COND_COUNT
};

/* Chord handling of a track: BLOCK plays every note of a step together (ratchet repeats the chord);
 * the ARP modes play one note per slice, "ratchet" slices per step. Bits 0-3 mode, bits 4-5 octaves-1. */
enum {
    SQ_CHORD_BLOCK = 0,
    SQ_CHORD_ARP_UP,         /* low to high */
    SQ_CHORD_ARP_DOWN,       /* high to low */
    SQ_CHORD_ARP_UPDN,       /* up then down, the ends played once  (C E G E) */
    SQ_CHORD_ARP_DNUP,       /* down then up, the ends played once  (G E C E) */
    SQ_CHORD_ARP_UPDN2,      /* up then down, the ends played twice (C E G G E C) */
    SQ_CHORD_ARP_CONV,       /* converge: low, high, next low, next high ... */
    SQ_CHORD_ARP_DIV,        /* diverge: from the middle outwards */
    SQ_CHORD_ARP_RND,        /* any note of the chord */
    SQ_CHORD_ARP_WALK,       /* a random walk: one note up or down at a time */
    SQ_CHORD_ARP_PLAYED,     /* in the order the notes were entered */
    SQ_CHORD_ARP_THUMB,      /* the lowest note between the others (C E C G) */
    SQ_CHORD_ARP_PINKY,      /* the highest note between the others (C G E G) */
    SQ_CHORD_COUNT
};
#define SQ_CHORD_MODE(v)   ((uint8_t)((v) & 0x0Fu))
#define SQ_CHORD_OCTS(v)   ((uint8_t)((((v) >> 4) & 3u) + 1u))   /* 1..4, SQ_ARP_MAX caps it at 3 */
#define SQ_CHORD_PACK(mode, octs) ((uint8_t)(((mode) & 0x0Fu) | ((((octs) - 1u) & 3u) << 4)))

typedef struct __attribute__((packed)) {
    uint8_t note[SQ_POLY];       /* MIDI notes; 255 = unused */
    uint8_t velocity;            /* 1..127 */
    uint8_t length;              /* 1..100 = gate % of a ratchet slice; 101 = 1.5 steps; 102..164 = 2..64 steps */
    uint8_t chance;              /* 0..100 percent */
    uint8_t ratchet;             /* 1..SQ_RATCHET_MAX */
    uint8_t condition;           /* SQ_COND_* */
    uint8_t flags;               /* SQ_STEP_* */
    uint8_t lane[SQ_LANES];      /* CC value locked to this step, 0..127; SQ_LANE_NONE = no lock */
    int8_t nudge;                /* -SQ_NUDGE_MAX..+SQ_NUDGE_MAX: percent of the step, - early, + late */
    int8_t ramp;                 /* -100..+100: velocity of the ratchets, - fades out, + builds up */
} sq_step_t;                     /* 22 bytes (0.27: 18 - four notes, six lanes) */

/* 0.8: a track's live layer. EUCLID (SQ_TF_EUC on) plays euc_pulses hits spread over the loop instead of the written
 * on / off; the ALGORITHM changes what plays while it plays. Both leave the pattern as written: off, it is all back. */
enum { SQ_ALGO_OFF = 0,
       SQ_ALGO_TURING,           /* a shift register that loops (mutation 0) or drifts: a = mutation %, b = length 2..16,
                                  * c = what it moves: 0 the rhythm, 1 the notes (scale steps 0..7), 2 both */
       SQ_ALGO_CELL,             /* an elementary cellular automaton: a = the rule 0..255, b = cells 4..64 (step i plays
                                  * cell i of the row), c = a new generation every 1 / 2 / 4 bars / loop of the track */
       SQ_ALGO_ACCENT,           /* a moving accent: a = BEAT / OFFBEAT / POLY3 / SYNC / RANDOM, b = amount 0..63,
                                  * c = where it starts 0..15 */
       SQ_ALGO_DENSITY,          /* fewer or more hits: a = 0..200 (100 = as written; under: hits drop, the beat last;
                                  * over: ghost hits on the rests), b = the ghosts' velocity 10..100 */
       SQ_ALGOS };
enum { SQ_TM_RHYTHM = 0, SQ_TM_NOTES, SQ_TM_BOTH, SQ_TM_MODES };
#define SQ_TM_LEN_TRACK 17u      /* 0.25: a TURING's length (b) past 16: TRACK - the register is as long as the track's loop (64 at
                                  * most), all of the written rhythm its first loop; made longer or shorter with the track (a
                                  * 0.24 firmware reads it as 16) */
/* 0.11: a track has SQ_ALGO_SLOTS algorithms, run in order on each step: slot 1 is algo / algo_a / algo_b / algo_c of
 * the track (where 0.10 kept its one algorithm), slots 2..4 are algo2[]. A rhythm algorithm (TURING on the rhythm,
 * CELL) replaces the hits so far, DENSITY thins or fills them, ACCENTs add their velocities, TURINGs on the notes add
 * their steps of the scale. Each slot keeps a state of its own (dinghy.c). */
typedef struct __attribute__((packed)) { uint8_t algo, a, b, c; } sq_algo_t;   /* 4 bytes */
#define SQ_ALGO_SLOTS 4u

typedef struct sq_project sq_project_t;   /* (defined below) */

/* 0.11 TAPE: a track that keeps what was played as events with their timing, not steps. Time is in tape ticks: 384 a
 * beat (16 a MIDI clock), a loop of 1..16 bars = up to 24576 ticks. The events of every tape track sit in one array of
 * the project, sorted by track then start; SQ_TAPE_MAX in all. */
#define SQ_TAPE_PPQ   384u
#define SQ_TAPE_BAR   (4u * SQ_TAPE_PPQ)
#define SQ_TAPE_MAX   1536u
#define SQ_TAPE_BARS_MAX 16u
typedef struct __attribute__((packed)) {
    uint16_t on;                 /* start, tape ticks from the loop's beginning */
    uint16_t dur;                /* length in tape ticks (1 .. the loop) */
    uint8_t note;                /* 0..127 */
    uint8_t vel;                 /* 1..127 */
} sq_tape_ev_t;
typedef struct __attribute__((packed)) {
    uint8_t bars;                /* 1..16: the loop */
    uint8_t quant;               /* 0..100 %: how far each start is pulled to the nearest 1/16 when it plays (the tape keeps its timing) */
    uint8_t flags;               /* reserved */
    uint8_t reserved;
} sq_tape_cfg_t;
void sq_tape_cfg_default(sq_tape_cfg_t *c);
void sq_tape_sanitize(sq_project_t *p);
uint32_t sq_tape_len(const sq_tape_cfg_t *c);                                       /* ticks of the loop, in bars of sixteen 16ths */
uint32_t sq_tape_len_bar(const sq_tape_cfg_t *c, uint8_t bar_steps);                /* 0.25: ... in bars of bar_steps 16ths */
uint32_t sq_tape_len_p(const sq_project_t *p, uint8_t t);                           /* ... of track t: bars of the project's metre */
uint16_t sq_tape_quantised(uint16_t on, uint8_t quant, uint32_t len);               /* where a start plays */
/* the events of track t: first index and count (sorted) */
void sq_tape_range(const sq_project_t *p, uint8_t t, uint16_t *first, uint16_t *n);
/* add an event to track t (kept sorted); 0 = done, -1 = full */
int sq_tape_add(sq_project_t *p, uint8_t t, uint16_t on, uint16_t dur, uint8_t note, uint8_t vel);
/* remove the events of track t that start in [a, b) ticks (b > len wraps nothing: give [a, len) then [0, b - len)) */
uint32_t sq_tape_erase(sq_project_t *p, uint8_t t, uint32_t a, uint32_t b);
uint32_t sq_tape_clear(sq_project_t *p, uint8_t t);
/* move track t's events by d ticks (wrapping in its loop) */
void sq_tape_shift(sq_project_t *p, uint8_t t, int32_t d);

/* ---- 0.10 EXPO: a track's rhythm as an exponential curve instead of the grid (SEQ pages 5 and 6; after Kelvin T's
 * exposaw for Ksoloti Gills). The hits of a span (the step itself, a beat, a bar ...) get closer or further apart by a
 * constant ratio: an accelerando, a bouncing ball. The pattern stays as written: it says where a span starts and
 * which notes it plays. Part of the track's settings. */
enum { SQ_XS_OFF = 0, SQ_XS_RAMP, SQ_XS_BOUNCE, SQ_XS_SETTLE, SQ_X_SHAPES };   /* SETTLE: exposaw's own law, below */
enum { SQ_XSPAN_STEP = 0, SQ_XSPAN_BEAT, SQ_XSPAN_2BEATS, SQ_XSPAN_BAR, SQ_XSPAN_2BARS, SQ_XSPAN_4BARS, SQ_X_SPANS };
enum { SQ_XV_FLAT = 0, SQ_XV_FALL, SQ_XV_RISE, SQ_XV_BOUNCE, SQ_XV_GRACE, SQ_X_VELS };   /* GRACE: the first hit at 75 %, the rest as written */
enum { SQ_XN_CHORD = 0, SQ_XN_ARP, SQ_XN_ARP1, SQ_XN_ARP2, SQ_XN_ARP3, SQ_X_NOTES };   /* ARPn: n octaves above too */
#define SQ_X_HITS_MIN 2u
#define SQ_X_HITS_MAX 64u
typedef struct __attribute__((packed)) {
    uint8_t shape;               /* SQ_XS_*: OFF = the track plays as written */
    uint8_t hits;                /* 2..64 hits in the span; SETTLE: hits a beat once settled (the rate) */
    int8_t curve;                /* -8..+8: 0 = even; RAMP: + the hits get closer (accelerando), - further apart;
                                  * BOUNCE: + fast in the middle, - slow in the middle. 8 = 16 x between the ends.
                                  * SETTLE: the depth, octaves faster at the start (+) or after a rise (-) */
    uint8_t span;                /* SQ_XSPAN_*: STEP = every hit step bounces in its own slot; longer: the step at the
                                  * span's boundary plays the whole span, the other steps are silent */
    uint8_t vel;                 /* SQ_XV_*: how the velocity moves along the hits */
    uint8_t gate;                /* 5..100 % of the gap to the next hit */
    uint8_t jitter;              /* 0..50 % of the gap, at random */
    uint8_t notes;               /* SQ_XN_*: CHORD = every hit the step's notes; ARP = one note a hit */
    uint8_t reserved[4];
} sq_expo_t;                     /* 12 bytes */

/* 0.10: the role a track plays in the band: what the library, BAND, COOK and VIAGGIO write on it (NONE: decided by
 * its notes). The first seven are the library's functions + 1 (sagga_beats.h SQ_FUNC_*), 0.11 adds the parts of the
 * genres' bands (sagga_beats.h SQ_FUNC_CLAP .. SQ_FUNC_VOX, in the same order). Each new role belongs to a FAMILY, one
 * of the first seven: what VIAGGIO's ladder, COOK and the dice know of it (a CLAP is a SNARE, a PAD a CHORD ...). */
enum { SQ_ROLE_NONE = 0, SQ_ROLE_KICK, SQ_ROLE_SNARE, SQ_ROLE_HAT, SQ_ROLE_PERC, SQ_ROLE_BASS, SQ_ROLE_CHORD, SQ_ROLE_ARP,
       SQ_ROLE_CLAP, SQ_ROLE_OHAT, SQ_ROLE_RIDE, SQ_ROLE_SHAKER, SQ_ROLE_CONGA, SQ_ROLE_TOM, SQ_ROLE_RIM, SQ_ROLE_CRASH,
       SQ_ROLE_COWBELL, SQ_ROLE_RUMBLE, SQ_ROLE_SUB, SQ_ROLE_LOGDRUM, SQ_ROLE_STAB, SQ_ROLE_PAD, SQ_ROLE_PIANO,
       SQ_ROLE_LEAD, SQ_ROLE_VOX,
       SQ_ROLE_BALAFON,          /* 0.29 (a 0.28 image: a LEAD, chunk 5 says it is the balafon) */
       SQ_ROLE_COUNT };
#define SQ_ROLE_FAMILIES 8u      /* NONE + KICK .. ARP */
const char *sq_role_name(uint8_t role);
uint8_t sq_role_family(uint8_t role);   /* 0.11: SQ_ROLE_NONE .. SQ_ROLE_ARP */
uint8_t sq_role_melodic(uint8_t role);  /* 0.11: 1 for the families BASS, CHORD, ARP */
/* 0.10 CHORD: one written or played note becomes a chord of this shape (up to SQ_POLY_OUT notes); the voicing and the
 * arpeggio then work on it. The shapes are the chords the machine's genres live on: triads, sixths, sevenths, ninths,
 * the sus and add colours, the 9sus4 of garage and house, the 11th and 13th, the shells of a stab. */
enum { SQ_CH_OFF = 0, SQ_CH_OCT, SQ_CH_POWER, SQ_CH_5_8, SQ_CH_MAJ, SQ_CH_MIN, SQ_CH_DIM, SQ_CH_AUG, SQ_CH_SUS2, SQ_CH_SUS4,
       SQ_CH_MAJ6, SQ_CH_MIN6, SQ_CH_7, SQ_CH_MIN7, SQ_CH_MAJ7, SQ_CH_MINMAJ7, SQ_CH_DIM7, SQ_CH_M7B5, SQ_CH_7SUS4,
       SQ_CH_ADD9, SQ_CH_MADD9, SQ_CH_9, SQ_CH_MIN9, SQ_CH_MAJ9, SQ_CH_9SUS4, SQ_CH_69, SQ_CH_MIN69, SQ_CH_MIN11,
       SQ_CH_13, SQ_CH_SHELL7, SQ_CH_MSHELL, SQ_CH_1358,
       /* 0.29: 7#9 (funk) 7b9 (drill and phonk) maj7#11 (deep) in fourths */
       SQ_CH_7S9, SQ_CH_7B9, SQ_CH_MAJ7S11, SQ_CH_QUARTAL,
       SQ_CH_COUNT };
#define SQ_CH_COUNT28 32u        /* (0.28's: a 0.28 opens one of the four new ones as OFF) */
/* the shapes 0.10's first cut had, for the tests and the tools that named them */
#define SQ_CH_TRIAD SQ_CH_MAJ
#define SQ_CH_6     SQ_CH_MAJ6
#define SQ_CH_SHELL SQ_CH_SHELL7
/* how the chord meets the key of a track IN KEY: DIATONIC builds it on the scale (the quality follows the step: D in
 * C major gives D minor), FREE keeps the exact intervals (the quality you asked, notes out of the key allowed),
 * STRICT keeps the intervals and silences the notes that fall out of the key. A FREE track: always the intervals. */
enum { SQ_CK_DIATONIC = 0, SQ_CK_FREE, SQ_CK_STRICT, SQ_CK_COUNT };
#define SQ_POLY_OUT 6u           /* the notes a chord shape can play at once (a written step holds SQ_POLY) */
const char *sq_chord_shape_name(uint8_t shape);
const char *sq_chord_key_name(uint8_t ck);
/* the notes of the chord (at most SQ_POLY_OUT, low to high, the written note first in place); `ck` is SQ_CK_* (the
 * caller passes SQ_CK_FREE for a track that is not IN KEY); returns the count */
uint8_t sq_chord_build(uint8_t note, uint8_t shape, uint8_t ck, uint8_t root, uint8_t scale, uint8_t *out);
/* 0.10: the rhythm families of EUCLID LIVE and the EUCLID tool */
enum { SQ_RF_EUCLID = 0, SQ_RF_TRESILLO, SQ_RF_NUMERIC, SQ_RF_COUNT };
/* 0.10 the arpeggio's clock: 0 ROLL (the notes spread over the step, as before), 1..4 notes a step; it runs across
 * the empty steps while the chord holds (its gate), or always with HOLD. 0.18: 5 = a note every 2 steps, 6 = every 4
 * (counted from the chord's step; the knob shows 1/4 1/2 ROLL 1 2 3 4) */
#define SQ_ARP_R_HALF    5u
#define SQ_ARP_R_QUARTER 6u
#define SQ_ARP_RATE_MAX  6u
#define SQ_ARP_PER_STEP(r) ((uint8_t)((r) >= 1u && (r) <= 4u ? (r) : (r) ? 1u : 0u))   /* notes in a step */
#define SQ_ARP_EVERY(r)    ((uint8_t)((r) == SQ_ARP_R_HALF ? 2u : (r) == SQ_ARP_R_QUARTER ? 4u : 1u))   /* steps a note */
#define SQ_AF_HOLD   0x01u
#define SQ_AF_RETRIG 0x02u       /* a new chord starts the arpeggio from its first note */
/* 0.10 a lane's flags */
#define SQ_LF_SLIDE    0x01u     /* the value glides from a lock to the next one over the steps between them */
#define SQ_LF_TRIGLESS 0x02u     /* a lock on a step that does not play is sent all the same */
#define SQ_LF_NRPN     0x04u     /* the lane sends NRPN lane_hi:lane_cc (data entry MSB = the value) instead of a CC */
#define SQ_KEY_FOLLOW 255u       /* key_slot: the track plays in the key that is current */

typedef struct __attribute__((packed)) {
    uint8_t channel;             /* 0..15 (16 only with two USB ports: one USB port plays 15/16 on 14) */
    uint8_t length;              /* 1..64: the loop ends after this step (steps start..length-1 play) */
    uint8_t start;               /* 0..length-1: the first step of the loop */
    uint8_t division;            /* SQ_DIV_* */
    uint8_t direction;           /* SQ_DIR_* */
    int8_t transpose;            /* -48..+48 semitones; a track IN KEY: -24..+24 steps of the scale (0.10) */
    uint8_t initial_pattern;     /* 0..7 */
    uint8_t chord_mode;          /* SQ_CHORD_PACK(mode, octaves) */
    uint8_t swing;               /* SQ_SWING_MIN..SQ_SWING_MAX: odd steps are late */
    int8_t vel_offset;           /* -63..+63 added to every velocity of the track */
    uint8_t hum_time;            /* 0..SQ_NUDGE_MAX: random timing, percent of a step either way */
    uint8_t hum_vel;             /* 0..50: random velocity, either way */
    uint8_t lane_cc[SQ_LANES];   /* the CC number each lane sends (128 BEND, 129 AFTERT; NRPN: the LSB); SQ_LANE_NONE = lane off */
    uint8_t lane_base[SQ_LANES]; /* what a lane goes back to when a step has no lock; SQ_LANE_NONE = stays as it is */
    uint8_t lane_flags[SQ_LANES];/* 0.10: SQ_LF_* */
    uint8_t lane_hi[SQ_LANES];   /* 0.10: NRPN: the parameter's MSB */
    uint8_t flags;               /* SQ_TF_* */
    uint8_t plen[3];             /* SQ_PL_*: the loop of the notes, the velocities, the gates; 0 = the track's own */
    uint8_t voicing;             /* SQ_VOICE_*: block chords and the chord an arpeggio is made of */
    int8_t strum;                /* -50..+50: the notes of a chord spread over this % of a step; - from the top */
    uint8_t mfx;                 /* SQ_MFX_*: the track's MIDI effect */
    int8_t mfx_amt;              /* HARM: -7..+7 steps of the key (FREE track: -12..+12 semitones); OCTAVE: -2..+2;
                                  * ECHO: 1..4 repeats; VEL CURVE: -8..+8 */
    uint8_t mfx_time;            /* ECHO: the delay (SQ_ECHO_TIMES); OCTAVE: which steps (ALT, RANDOM, 3RD, 4TH) */
    uint8_t mfx_fb;              /* ECHO: the velocity each repeat keeps, 10..100 %; HARM: the voice's velocity % */
    uint8_t euc_pulses;          /* EUCLID: 1..64 hits spread over the loop (SQ_TF_EUC: on) */
    uint8_t euc_rot;             /* 0..63: the pattern turned right */
    uint8_t algo;                /* SQ_ALGO_* */
    uint8_t algo_a, algo_b, algo_c;
    uint8_t pen;                 /* the track's own note: what a new step plays (a drum track: which drum it is), 0..127 */
    /* 0.10 */
    uint8_t role;                /* SQ_ROLE_* */
    uint8_t chord;               /* SQ_CH_*: one note becomes this chord */
    int8_t octave;               /* -3..+3 octaves, on top of the transpose (PERF + OCT) */
    uint8_t key_slot;            /* SQ_KEY_FOLLOW, or 0..15: the track always plays in that key slot */
    uint8_t src_func, src_var;   /* the library function and variation this track's pattern came from (255: none): GENRE
                                  * LIVE reloads it when the genre changes */
    uint8_t euc_fam;             /* SQ_RF_*: the family of EUCLID LIVE */
    uint8_t arp_rate;            /* 0 ROLL, 1..4 notes a step, 5 / 6 a note every 2 / 4 steps (0.18) */
    uint8_t arp_flags;           /* SQ_AF_* */
    int8_t delay_ms;             /* the track's notes this many ms late (+) or early (-): the synth's latency */
    sq_expo_t expo;
    sq_tape_cfg_t tape;
    uint8_t chord_key;           /* SQ_CK_*: how CHORD meets the key (a track IN KEY) */
    /* 0.11 (SGQB; a 0.10 image ends at 80 bytes: these are defaults) */
    sq_algo_t algo2[SQ_ALGO_SLOTS - 1u];   /* the algorithms of slots 2..4 (slot 1: algo, algo_a, algo_b, algo_c above) */
    uint8_t src_genre;           /* the genre src_func / src_var came from (255: not known: a 0.10 track) - COOK walks
                                  * towards the next variation of that genre's part */
    uint8_t follow_mode;         /* SQ_FM_*: a note held across a change of chord: kept, struck again, or slid */
    /* 0.12 (the two bytes 0.11 kept in reserve; a 0.11 image has them 0): a BREAK track (SQ_TF_BREAK) */
    uint8_t brk_chop;            /* the chop the pattern was written from (SQ_BRK_CHOPS: the library of re-orders) */
    uint8_t brk_cfg;             /* SQ_BRK_PACK(slices 0..2 = 8 / 16 / 32, roll 0..7, swap 0..7) + 1: 0 = not set (a 0.11 image: the default) */
} sq_track_cfg_t;                /* 104 bytes (0.27: 96 - six lanes) */
#define SQ_BRK_PACK(sl, roll, swap) ((uint8_t)((((sl) & 3u) | (((roll) & 7u) << 2) | (((swap) & 7u) << 5)) + 1u))
#define SQ_BRK_SL(cfg)   (((cfg) ? (cfg) - 1u : 0u) & 3u)
#define SQ_BRK_ROLL(cfg) ((((cfg) ? (cfg) - 1u : 0u) >> 2) & 7u)
#define SQ_BRK_SWAP(cfg) ((((cfg) ? (cfg) - 1u : 0u) >> 5) & 7u)
#define SQ_BRK_DEFAULT SQ_BRK_PACK(1u, 2u, 3u)   /* 16 slices, two rolls, the dice swaps about 40 % */
#define SQ_TRACK_CFG_A 80u       /* the bytes a 0.10 (SGQA) image holds of a track */
enum { SQ_FM_HOLD = 0, SQ_FM_RETRIG, SQ_FM_LEGATO, SQ_FM_MELODY, SQ_FM_SMOOTH, SQ_FMS };   /* 0.11 FOLLOW: HOLD (0.10: the chord at its start), RETRIG, LEGATO (the notes the chords share go on);
                                                                              * 0.25 MELODY: a tune stays where it is written, its strong notes go to the chord (sq_harm_melody);
                                                                              * 0.26 SMOOTH: a chord's notes go to the nearest notes of the chord playing (sq_harm_smooth) */
/* slot k (0..3) of a track's algorithms (slot 0 is the four bytes algo .. algo_c, laid out like sq_algo_t) */
#define SQ_ALGO_AT(c, k) ((k) ? &(c)->algo2[(k) - 1u] : (sq_algo_t *)&(c)->algo)
#define SQ_TF_SCALE  0x01u       /* the track's notes are kept in the project's key (not for drums) */
#define SQ_TF_DRUM   0x02u       /* a drum voice: its notes play as written (never the key); the drum keys and views */
#define SQ_TF_FOLLOW 0x04u       /* 0.8: the track follows the HARMONY (its notes move to the chord that plays) */
#define SQ_TF_EUC    0x08u       /* 0.8: EUCLID LIVE on */
#define SQ_TF_CHAIN  0x10u       /* 0.10: the pattern and its partner (1+2, 3+4, 5+6, 7+8) play one after the other: 128 steps */
#define SQ_TF_TAPE   0x20u       /* 0.10: a TAPE track: what was played, with its timing, in a loop of bars (sq_tape_*) */
#define SQ_TF_BREAK  0x40u       /* 0.12: a BREAK track: every step is a slice of a drum break (note = pen + slice - 1), never the
                                  * key; the chops, the dice and the live keys re-order the slices (sagga_break.c) */
#define SQ_TF_MASK   0x7Fu
enum { SQ_VOICE_CLOSE = 0, SQ_VOICE_INV1, SQ_VOICE_INV2, SQ_VOICE_DROP2, SQ_VOICE_OPEN, SQ_VOICES };
/* the MIDI effects (HOME 6). 0.20: five more after the four of 0.19 - a 0.19 firmware knows only up to SQ_MFXS_019 */
enum { SQ_MFX_OFF = 0, SQ_MFX_HARM, SQ_MFX_OCTAVE, SQ_MFX_ECHO, SQ_MFX_VELOCITY, SQ_MFXS_019,
       SQ_MFX_CHANCE = SQ_MFXS_019,   /* each note (or each step) passes with a chance */
       SQ_MFX_RANDOM,                 /* the note and the velocity moved at random, within a spread, in the key */
       SQ_MFX_FILTER,                 /* NOTE FILTER: only the notes between two, or one of every N */
       SQ_MFX_GATE,                   /* the length: times a factor, or a fixed one, a little at random */
       SQ_MFX_GLITCH,                 /* now and then a step stutters, rises, jumps an octave or is cut short */
       SQ_MFXS_020,                   /* (0.20 - 0.28 know up to here: the image's own block holds these, 0.29's chunk 5 the rest) */
       SQ_MFX_ROLL = SQ_MFXS_020,     /* 0.29: each note a roll - 2..6 in its step, level, rising or falling (the trap hats) */
       SQ_MFX_ACCENT,                 /* 0.29: an accent every 2..8 steps, from a step of its own: three over four */
       SQ_MFXS };
enum { SQ_ROLL_FLAT = 0, SQ_ROLL_UP, SQ_ROLL_DOWN, SQ_ROLLS };   /* ROLL K3: the hits' velocity */
#define SQ_GATE_FACTORS 7u       /* GATE K2 -3..+3: x1/4 x1/2 x3/4 x1 x3/2 x2 x4 */
#define SQ_GATE_FIXED 8u         /* GATE K3: OFF, 1/32 1/16 1/8 1/4 1/2 1 BAR 2 BARS */
enum { SQ_GL_MIX = 0, SQ_GL_STUTTER, SQ_GL_RISE, SQ_GL_JUMP, SQ_GL_CUT, SQ_GLITCHES };   /* GLITCH K3 */
#define SQ_ECHO_TIMES 8u         /* 1/32 1/16 1/8T 1/16. 1/8 1/4T 1/8. 1/4 (sq_echo_ticks) */
enum { SQ_OCT_ALT = 0, SQ_OCT_RANDOM, SQ_OCT_THIRD, SQ_OCT_FOURTH, SQ_OCT_PATTERNS };

/* Lengths per parameter (as on Kria): the steps that play (on / off, chance, condition, ratchet, nudge, CC locks) follow
 * the track's loop; the notes, the velocities and the gates can each have a loop of their own, 1..64 steps from the
 * track's first step, that always goes forward one step each time the track moves. A 16-step rhythm with a 5-step
 * melody and a 3-step accent pattern repeats after 240 steps. */
enum { SQ_PL_NOTE = 0, SQ_PL_VEL, SQ_PL_GATE, SQ_PLANES };

#define SQ_PC_NONE 255u
typedef struct __attribute__((packed)) {
    uint8_t pattern[SQ_TRACKS];  /* pattern selected on each track */
    uint16_t mute_mask;          /* bit per track */
    uint8_t pc[SQ_CHANNELS];     /* the Program Change each MIDI channel gets when the scene comes (SQ_PC_NONE: none) */
    uint8_t lane[SQ_TRACKS][SQ_LANES];   /* the CC lanes' base values stored with the scene (MORPH); SQ_LANE_NONE: none */
    uint8_t key_slot;            /* 0.10: the key slot the scene brings (SQ_KEY_FOLLOW: it leaves the key alone) */
} sq_scene_t;

/* live settings of the project: when queued changes happen, mutes that wait, MORPH, the remote channel */
enum { SQ_Q_AUTO = 0,            /* a pattern at the end of its track's loop, a scene (a snapshot, a queued mute) at the bar */
       SQ_Q_NOW, SQ_Q_BEAT, SQ_Q_BAR, SQ_Q_2BAR, SQ_Q_4BAR, SQ_Q_8BAR, SQ_QUANTS };
#define SQ_REMOTE_OFF 255u
typedef struct __attribute__((packed)) {
    uint8_t quant;               /* SQ_Q_* */
    uint8_t mute_q;              /* 0: a mute is at once; 1: it waits for the next quantised moment (the bar on AUTO) */
    uint8_t morph_b;             /* MORPH goes from the scene playing to this one, 0..7 */
    uint8_t remote_ch;           /* the MIDI channel SAGGA REMOTE's commands come in on (0..13), SQ_REMOTE_OFF: none */
    uint8_t master_fn;           /* what the MASTER knob does: SQ_MK_* */
    int8_t ktrans;               /* TRANSPOSE: how far the key has been moved (root and shift together), -12..+12 */
    uint8_t snap_tempo;          /* 0.8: a snapshot brings its tempo back too */
    uint8_t remote_mode;         /* 0.9: SQ_RM_*: the remote off, on channel 14, or on 13 + 14 (VIAGGIO on 13) */
    uint8_t mute_lo, mute_hi;    /* 0.9: the mutes as they were when the project was saved (0.8 saved none) */
    uint8_t scene_cursor;        /* 0.9: the scene selected when it was saved */
    int8_t mac[4];               /* 0.10: the macros INTENSITY, GATE, SWING, FILTER, saved with the project */
    uint8_t cc_lead_ms;          /* 0.10: the CC locks of a step go out this many ms before its notes, 0..30 */
    uint8_t song_tempo;          /* 0.10: 1: a song entry with a tempo sets it */
    uint8_t reserved[3];
} sq_live_t;                     /* 20 bytes */
enum { SQ_MK_TEMPO = 0, SQ_MK_MORPH, SQ_MK_FILTER, SQ_MKS };
enum { SQ_RM_OFF = 0, SQ_RM_14, SQ_RM_13_14, SQ_RMS };
#define SQ_KTRANS_MAX 12
#define SQ_CC_LEAD_MAX 30u
void sq_live_default(sq_live_t *l);

/* LFO: a value that moves with the beat. It goes out as a CC, or moves one parameter of a track. */
enum { SQ_LFO_SINE = 0, SQ_LFO_TRI, SQ_LFO_RAMP_UP, SQ_LFO_RAMP_DN, SQ_LFO_SQUARE, SQ_LFO_SH, SQ_LFO_SMOOTH,
       SQ_LFO_DECAY, SQ_LFO_ENV, SQ_LFO_SHAPES };   /* 0.20 ENV: an envelope (sq_lfoe_t); the others are waves */
#define SQ_LFO_WAVES SQ_LFO_ENV  /* the periodic shapes (what COOK picks from) */
enum { SQ_LD_CC = 0, SQ_LD_VEL, SQ_LD_GATE, SQ_LD_CHANCE, SQ_LD_TIMING, SQ_LD_SWING, SQ_LD_KINDS,
       SQ_LD_MOD = SQ_LD_KINDS,  /* 0.20 MOD ONLY: it sends nothing, it is a source of the MOD MATRIX */
       SQ_LD_ALL };
#define SQ_LFO_RATES 20u        /* 0.13: 16 from 16 bars to 1/32, then the triplets 1/4T 1/8T 1/16T 1/32T */
#define SQ_LFO_RATES_STRAIGHT 16u
#define SQ_LF_RETRIG 0x01u      /* start the cycle again when the transport starts */
#define SQ_LF_INVERT 0x02u

typedef struct __attribute__((packed)) {
    uint8_t enabled;             /* 0 / 1 */
    uint8_t shape;               /* SQ_LFO_* */
    uint8_t rate;                /* 0..15: sq_lfo_ticks() */
    uint8_t depth;               /* 0..127: how far it swings either way */
    uint8_t center;              /* 0..127: CC value in the middle of the swing */
    uint8_t phase;               /* 0..127: where in the cycle it starts */
    uint8_t dest;                /* SQ_LD_* */
    uint8_t target;              /* CC: the MIDI channel 0..15; the others: the track 0..11 */
    uint8_t param;               /* CC: the controller number 0..127 */
    uint8_t flags;               /* SQ_LF_* */
} sq_lfo_t;

/* ---- 0.13: what 0.13 adds to the project. It lives in chunk 1 of the image (sq_serialize), so a 0.12 image loads with
 * the defaults and a 0.12 firmware skips it. Snapshots do not carry it. */
#define SQ_RSEQ_MAX 8u
enum { SQ_RE_BEAT = 0, SQ_RE_2BEATS, SQ_RE_BAR, SQ_RE_2BARS, SQ_RES };   /* RATE SEQ: a new rate every ... */
#define SQ_RSEQ_OWN 255u        /* a RATE SEQ entry that is the LFO's own RATE */
typedef struct __attribute__((packed)) {
    uint8_t seq_n;               /* 0: the LFO's RATE; 2..8: RATE SEQ, the rates one after the other (the wobble that changes) */
    uint8_t seq_every;           /* SQ_RE_*: how long each rate lasts; the cycle starts again with each one */
    uint8_t seq_rate[SQ_RSEQ_MAX];   /* 0..SQ_LFO_RATES-1, or SQ_RSEQ_OWN */
    uint8_t trig;                /* 0: the clock; 1..12: the hits of track trig-1 start the cycle, which holds at its end
                                  * (DECAY, inverted: the sidechain duck) */
    uint8_t reserved;
} sq_lfox_t;                     /* 12 bytes */
#define SQ_CHAIN_MAX 8u
#define SQ_NAME_LEN 16u
/* 0.15 GROOVE: a template a track plays its steps with - each 16th of the bar a little early or late (% of a step, on
 * top of the step's nudge and the swing) and louder or softer; the amount scales both */
enum { SQ_GROOVE_OFF = 0, SQ_GROOVE_HOUSE, SQ_GROOVE_GARAGE, SQ_GROOVE_DILLA, SQ_GROOVE_AFRO, SQ_GROOVE_SAMBA,
       SQ_GROOVE_LAIDBACK, SQ_GROOVE_PUSH, SQ_GROOVE_HUMAN, SQ_GROOVE_TRAP,
       SQ_GROOVE_MALI,           /* 0.29: the djembe's 16ths, leaning towards three a beat (balani) */
       SQ_GROOVE_DEMBOW,         /* ... reggaeton's: the snare's two on the 'a' late and loud */
       SQ_GROOVE_BROKEN,         /* ... broken beat: the 'e' early, the 'a' late, uneven */
       SQ_GROOVES };
#define SQ_GROOVES28 10u         /* (0.28's: a 0.28 opens one of the three new ones as OFF) */
const char *sq_groove_name(uint8_t g);
int32_t sq_groove_time(uint8_t g, uint8_t amt, uint32_t step);   /* % of a step, - early */
int32_t sq_groove_vel(uint8_t g, uint8_t amt, uint32_t step);    /* velocity, +/- */
/* 0.15: a project's name as the FM-1 shows it: upper case, the characters it draws (others become _), no spaces at
 * the ends, 0 after the last (0 or FF ends it: an erased flash reads as no name) */
void sq_name_sanitize(char *n, uint32_t len);
typedef struct __attribute__((packed)) {
    uint8_t chain_on;            /* 1: the CHAIN LIST plays (HOME 7 K2 = LIST) */
    uint8_t chain_n;             /* 1..8 entries */
    uint8_t chain_pat[SQ_CHAIN_MAX];   /* the pattern of each entry, 0..7 */
    uint8_t chain_rep[SQ_CHAIN_MAX];   /* how many loops it plays, 1..8 */
    uint8_t groove;              /* 0.15 GROOVE: SQ_GROOVE_* (0 off), the track's steps pushed and accented a 16th each */
    uint8_t groove_amt;          /* 0..100 %: how much of the template */
} sq_trackx_t;                   /* 20 bytes */
#define SQ_MOTION_CELLS 64u      /* a 16th each: 4 bars */
#define SQ_MOTION_NONE (-128)
enum { SQ_KB_OFF = 0, SQ_KB_ALL, SQ_KB_SPLIT,             /* the keyboard's notes TRANSPOSE: none, all, those under C3 */
       SQ_KB_CHORD, SQ_KB_CHORD_SPLIT,                     /* 0.26 LIVE CHORDS: the notes held are the HARMONY's chord: all of them, those under C3 */
       SQ_KBS };
#define SQ_KB_IS_SPLIT(m) ((m) == SQ_KB_SPLIT || (m) == SQ_KB_CHORD_SPLIT)
#define SQ_KB_IS_CHORD(m) ((m) == SQ_KB_CHORD || (m) == SQ_KB_CHORD_SPLIT)
#define SQ_KB_SPLIT_NOTE 48u     /* C3 */
/* 0.19: a track's MIDI FX CHAIN (HOME 6). The four effects can play together, always in this order: VEL CURVE, OCTAVE,
 * HARM, ECHO (the velocity, then the note moved, then the harmony's voice on it, then the echoes of both); each keeps
 * its own values here, saved with the project. The track's mfx .. mfx_fb stay equal to the first effect of the chain
 * that plays (in SQ_MFX_* order), so a 0.18 firmware, which skips this, plays that one; a 0.18 image has no chain: its
 * one effect becomes the chain (sq_mfx_from_track). */
#define SQ_MFX_N (SQ_MFXS_019 - 1u)      /* the four of 0.19, OFF apart: effect x at [x - 1] */
typedef struct __attribute__((packed)) {
    uint8_t on;                  /* bit (1 << SQ_MFX_*): that effect plays */
    int8_t amt[SQ_MFX_N];        /* as the track's mfx_amt (each effect its own range) */
    uint8_t time[SQ_MFX_N];      /* as mfx_time */
    uint8_t fb[SQ_MFX_N];        /* as mfx_fb */
} sq_mfxc_t;                     /* 13 bytes */
#define SQ_MFX_ON(m, fx) ((uint8_t)(((m)->on >> (fx)) & 1u))
#define SQ_MFX_ALL (((1u << SQ_MFXS_019) - 1u) & ~1u)
extern const uint8_t SQ_MFX_ORDER[SQ_MFX_N];   /* the order the four of 0.19 play in: VEL CURVE, OCTAVE, HARM, ECHO */
void sq_mfx_defaults(uint8_t fx, int8_t *amt, uint8_t *time, uint8_t *fb);   /* an effect's values when first chosen */
void sq_mfx_sanitize(sq_mfxc_t *m);
void sq_mfx_mirror(const sq_mfxc_t *m, sq_track_cfg_t *c);       /* the track's mfx .. mfx_fb from its chain */
void sq_mfx_from_track(const sq_track_cfg_t *c, sq_mfxc_t *m);   /* a 0.18 track's one effect, as a chain */
/* 0.20: the five new effects of a track, and the ORDER all nine play in (the player's: SEL + K1 in HOME 6). A 0.19
 * image has none: the defaults, and the order keeps 0.19's VEL CURVE, OCTAVE, HARM, ECHO with the new ones around it */
#define SQ_MFX_NEW (SQ_MFXS - SQ_MFXS_019)   /* 7 (0.20 - 0.28: 5): effect x at [x - SQ_MFXS_019] */
#define SQ_MFX_ALLN (SQ_MFXS - 1u)           /* 11 (0.20 - 0.28: 9) */
#define SQ_MFX_NEW28 (SQ_MFXS_020 - SQ_MFXS_019)   /* 5: 0.28's */
#define SQ_MFX_ALLN28 (SQ_MFXS_020 - 1u)           /* 9 */
typedef struct __attribute__((packed)) {
    uint8_t on;                  /* bit (1 << (fx - SQ_MFXS_019)): that effect plays */
    uint8_t order[SQ_MFX_ALLN];  /* the effects in the order they play, each once (0.29: eleven) */
    int8_t amt[SQ_MFX_NEW];      /* K2 of each new effect */
    uint8_t time[SQ_MFX_NEW];    /* K3 */
    uint8_t fb[SQ_MFX_NEW];      /* K4 */
} sq_mfxd_t;                     /* 33 bytes (0.20 - 0.28: 25, the image's block: sq27_mfxd_t) */
extern const uint8_t SQ_MFX_ORDER_DEF[SQ_MFX_ALLN];   /* FILTER CHANCE VEL ACCENT RANDOM OCTAVE HARM GATE GLITCH ROLL ECHO */
void sq_mfxd_default(sq_mfxd_t *d);
void sq_mfxd_sanitize(sq_mfxd_t *d);
/* any effect of track t, old or new: on, its values (clamped to the effect's range), the count that plays */
struct sq_ext_s;
uint8_t sq_mfx_is_on(const struct sq_ext_s *x, uint32_t t, uint8_t fx);
void sq_mfx_set_on(struct sq_ext_s *x, uint32_t t, uint8_t fx, uint8_t on);
void sq_mfx_get(const struct sq_ext_s *x, uint32_t t, uint8_t fx, int8_t *amt, uint8_t *time, uint8_t *fb);
void sq_mfx_put(struct sq_ext_s *x, uint32_t t, uint8_t fx, int8_t amt, uint8_t time, uint8_t fb);
uint8_t sq_mfx_count(const struct sq_ext_s *x, uint32_t t);
void sq_mfx_range(uint8_t fx, uint8_t knob, uint8_t in_key, int32_t *lo, int32_t *hi);   /* knob 0 K2, 1 K3, 2 K4 */
int sq_mfx_order_pos(const struct sq_ext_s *x, uint32_t t, uint8_t fx);                 /* where fx plays, 0..8 */
void sq_mfx_order_move(struct sq_ext_s *x, uint32_t t, uint8_t fx, int32_t d);          /* earlier (-) or later (+) */
uint32_t sq_gate_fixed_ticks(uint8_t idx);   /* GATE K3: 0 (OFF), 3 6 12 24 48 96 192 */
uint32_t sq_gate_factor_x4(int8_t idx);      /* GATE K2: the factor in quarters (1 2 3 4 6 8 16) */

/* 0.20 ENVELOPES: an LFO whose SHAPE is ENV rises and falls with the notes of its TRIG track (the clock: once a cycle of
 * its RATE, held half of it): ATTACK, DECAY to SUSTAIN while the note is held, RELEASE after. The times are steps of
 * the clock (sq_env_ticks). */
#define SQ_ENV_TIMES 16u         /* 0 1/96 1/48 1/32 1/24 1/16 1/16. 1/8 1/8. 1/4 1/4. 1/2 1/2. 1 BAR 2 BARS 4 BARS */
typedef struct __attribute__((packed)) {
    uint8_t a, d;                /* 0..SQ_ENV_TIMES-1 */
    uint8_t s;                   /* 0..100 % */
    uint8_t r;                   /* 0..SQ_ENV_TIMES-1 */
} sq_lfoe_t;                     /* 4 bytes */
uint32_t sq_env_ticks(uint8_t idx);
/* the level (0..65535) an envelope has `el` clock ticks (x 256: fractions) after its note started, the note held for
 * `gate` ticks (x 256) */
uint32_t sq_env_level(const sq_lfoe_t *e, uint32_t el, uint32_t gate);

/* 0.20 MOD MATRIX: eight slots, each a SOURCE moving a DESTINATION by an AMOUNT (-100..+100 %) */
#define SQ_MODS 8u
enum { SQ_MS_OFF = 0, SQ_MS_LFO, SQ_MS_MACRO, SQ_MS_ENERGY, SQ_MS_RANDOM, SQ_MS_VEL, SQ_MS_CCIN, SQ_MSS };
enum { SQ_MD_OFF = 0, SQ_MD_DEPTH, SQ_MD_CENTER, SQ_MD_VEL, SQ_MD_GATE, SQ_MD_CHANCE, SQ_MD_TIMING, SQ_MD_SWING,
       SQ_MD_FX, SQ_MDS };
typedef struct __attribute__((packed)) {
    uint8_t src;                 /* SQ_MS_* */
    uint8_t src_i;               /* LFO 0..15, MACRO 0..3, VEL: the track 0..11, CC IN: the controller 0..127 */
    uint8_t dst;                 /* SQ_MD_* */
    uint8_t dst_i;               /* DEPTH / CENTER: the LFO 0..15; the others: the track 0..11 */
    int8_t amt;                  /* -100..+100 */
} sq_mod_t;                      /* 5 bytes */
uint8_t sq_mod_src_count(uint8_t src);   /* how many of that kind (LFO 16, MACRO 4, VEL 12, CC IN 128, else 1) */
uint8_t sq_mod_dst_count(uint8_t dst);   /* DEPTH / CENTER 16, the track ones 12, OFF 1 */
void sq_mod_sanitize(sq_mod_t *m);
typedef struct __attribute__((packed)) sq_ext_s {
    sq_lfox_t lfo[SQ_LFOS];
    sq_trackx_t track[SQ_TRACKS];
    uint8_t motion_bars;         /* MOTION: 0 off, 1, 2, 4 bars: REC writes the macros' moves, they play back */
    uint8_t kb_mode;             /* SQ_KB_* */
    uint8_t kb_ch;               /* the keyboard's channel: 0 any, 1..16 */
    uint8_t in_thru;             /* 0: MIDI IN plays the selected track with REC only (0.12); 1: always */
    int8_t motion[4][SQ_MOTION_CELLS];   /* the macros INTENSITY GATE SWING FILTER a 16th; SQ_MOTION_NONE: not written */
    /* 0.26 (six of the eight bytes 0.13 kept in reserve: an older image has them 0, an older firmware puts them to 0) */
    uint8_t click;               /* SQ_CLICK_*: the metronome - OFF, while REC is on, whenever it plays */
    uint8_t count_in;            /* the bars counted before PLAY with REC on starts: 0 none, 1, 2 */
    uint8_t click_out;           /* where the click sounds: 0 the FM-1's own sound, 1..16 a note on that MIDI channel */
    uint8_t click_note;          /* ... that note (0: SQ_CLICK_NOTE_DEF) */
    uint8_t click_level;         /* how loud, 1..SQ_CLICK_LEVELS (0: SQ_CLICK_LEVEL_DEF): the FM-1's sound, the note's velocity */
    uint8_t scene_metre_on;      /* 1: a scene keeps the metre it was stored in and brings it back (scene_metre, at the end) */
    uint8_t evo_ret;             /* 0.27: EVOLVE's RETURN + 1 (1..101); 0: not set (an older image): from gen.evo_drift */
    uint8_t reserved[1];
    char name[SQ_NAME_LEN];      /* 0.15: the project's name (the Pi's editor writes it; SAVE + PRESETS shows it): A-Z 0-9
                                  * space - _ . + # & ! ' ( ) / :, 0 after the last; a 0.14 image has none (a 0.14 firmware
                                  * takes the 780 bytes before it) */
    sq_mfxc_t mfxc[SQ_TRACKS];   /* 0.19: the MIDI FX chain of each track (a 0.18 image has none: sq_mfx_from_track) */
    sq_mfxd_t mfxd[SQ_TRACKS];   /* 0.20: the five new effects and the order of the nine (a 0.19 image: the defaults) */
    sq_lfoe_t lfoe[SQ_LFOS];     /* 0.20: each LFO's envelope (SHAPE ENV) */
    sq_mod_t mod[SQ_MODS];       /* 0.20: the MOD MATRIX */
    uint8_t scene_metre[SQ_SCENES];   /* 0.26: the metre each scene brings: 0 = it leaves the metre alone, else sq_metre_id + 1
                                       * (a 0.25 image has none: every scene leaves it alone; a 0.25 firmware takes the 1508
                                       * bytes before it) */
} sq_ext_t;                      /* 1292 bytes (0.27: 1524 - sixteen tracks; the image keeps that layout: sagga_img27.h) */
/* 0.26 THE CLICK (SAVE 5): a metronome on the beats of the metre, the bar line louder; a count before a recording */
enum { SQ_CLICK_OFF = 0, SQ_CLICK_REC, SQ_CLICK_PLAY, SQ_CLICKS };
#define SQ_COUNT_IN_MAX 2u
#define SQ_CLICK_NOTE_DEF 75u    /* claves (General MIDI); the bar line: the same note, louder */
#define SQ_CLICK_LEVELS 10u
#define SQ_CLICK_LEVEL_DEF 7u
uint8_t sq_click_note(const sq_ext_t *x);        /* the note a MIDI click plays */
uint8_t sq_click_level(const sq_ext_t *x);       /* 1..SQ_CLICK_LEVELS */
uint8_t sq_click_vel(const sq_ext_t *x, uint8_t accent);   /* its velocity: the bar line 127 at the top level, a beat lower */
/* the FM-1's own click: a short sine that dies away - 2000 Hz on the bar line, 1000 Hz on a beat -, made a block of
 * frames at a time (the audio interrupt). sq_click_start: a click from its first frame; sq_click_render ADDS it to
 * `frames` stereo frames (L R L R, Q15) from frame `from` on, and returns 1 while there is more of it to come. */
typedef struct { uint32_t phase, inc; int32_t env; uint16_t left; uint8_t on, reserved; } sq_click_t;
#define SQ_CLICK_FS 44100u
void sq_click_start(sq_click_t *c, uint8_t accent, uint8_t level);
uint8_t sq_click_render(sq_click_t *c, int32_t *out, uint32_t frames, uint32_t from);
#define SQ_CHUNK_EXT 1u          /* the image's chunk of sq_ext_t */

/* 0.23 THEORY: a pattern can be MADE by the engines (sagga_theory.h) from the rules of a style instead of loaded from
 * the library. The project keeps where its patterns come from, the seed of the next one, and for every pattern the
 * engines made what it was made from - so it can be made again at another energy, or walked to its next variation. */
#define SQ_TH_FREE 22u           /* a style is a genre of the library (SQ_GENRE_* of sagga_beats.h: 0..21), or FREE: no genre
                                  * (0.29: 22; 0.28's images: 25, sq_genre_from28) */
#define SQ_TH_STYLES 23u
#define SQ_TH_SEEDS 999u         /* the seeds of the FM-1: 0..998 (the screen shows 1..999) */
enum { SQ_SRC_LIBRARY = 0,      /* the patterns are loaded from the library */
       SQ_SRC_THEORY,           /* ... made by the engines, in the style of the genre (of no genre while the GENRE mode is FREE) */
       SQ_SRC_FREE,             /* ... made by the engines in the style of NO genre, whatever the genre and its mode */
       SQ_SRCS };
typedef struct __attribute__((packed)) {
    uint16_t seed;               /* the seed it was made from */
    uint8_t style;               /* 0: not the engines' (written by hand, loaded from the library). Else bits 0-4: 1 +
                                  * the style; bits 5-6: the length it was made at, 0 = 16 steps, 1 = 32, 2 = 64 (0.26, with
                                  * bit 7, SQ_THP_V26: one, two, four bars of its metre) */
    uint8_t func;                /* the part it is: SQ_FUNC_* (sagga_beats.h) */
    uint8_t var;                 /* the variation of the seed it is (0: the seed's own; COOK walks to the next) */
    uint8_t vary;                /* how large that variation is, 0..100 % (SQ_THP_VARY; 0.26, bit 7: SQ_THPV_NOTES) */
    uint8_t energy;              /* the energy it was made at, 0..100 */
    uint8_t metre;               /* 0.25: the metre it was made in (sq_metre_id; 0: 4/4) - made again when the bar is another */
} sq_thpat_t;                    /* 8 bytes */
#define SQ_THP_V26 0x80u         /* 0.26, bit 7 of `style`: made IN the bar of its metre by the engines of 0.26 - its length is one,
                                  * two or four bars OF THAT METRE, not sixteens re-barred. A pattern without it is made again
                                  * the way 0.25 made it. (A 0.25 firmware does not know the bit: it takes the pattern for one
                                  * written by hand, and leaves it as it is.) */
#define SQ_THPV_NOTES 0x80u      /* 0.26, bit 7 of `vary`, only with SQ_THP_V26: its ANSWERS HAVE NOTES (sq_th_t.mate_nt). Every
                                  * pattern made new by 0.26 has both; a pattern of 0.25 made again in another metre is made in
                                  * the bar and keeps its answers as they were (so that back in 4/4 it is what it was: there a
                                  * pattern with neither bit - made in the bar and made in sixteens are the same thing) */
#define SQ_THP_VARY(m)  ((uint8_t)((m)->vary & 127u))                    /* how large its variation is, 0..100 */
#define SQ_THP_NOTES(m) ((uint8_t)((((m)->style & SQ_THP_V26) && ((m)->vary & SQ_THPV_NOTES)) ? 1u : 0u))
#define SQ_THP_STYLE(m) ((uint8_t)(((m)->style & 31u) - 1u))            /* the style of a pattern the engines made */
#define SQ_THP_LEN(m)   ((uint8_t)(16u << (((m)->style >> 5) & 3u)))    /* 16, 32, 64 */
#define SQ_THP_PACK(style, len) ((uint8_t)(((style) + 1u) | ((len) >= 64u ? 0x40u : (len) >= 32u ? 0x20u : 0u)))
typedef struct __attribute__((packed)) {
    uint8_t src;                 /* SQ_SRC_*: where BEAT, KIT, BAND, the proposals, the dice and GENRE LIVE take patterns from */
    uint8_t reserved;
    uint16_t seed;               /* 0..SQ_TH_SEEDS-1: the seed of the next band, the next part */
    sq_thpat_t pat[SQ_TRACKS][SQ_PATTERNS];
} sq_theory_t;                   /* 772 bytes (0.27: 1028) */
#define SQ_CHUNK_TH 2u           /* the image's chunk of it: src, seed (2), n, then n x (track, pattern, sq_thpat_t): only the
                                  * patterns the engines made; no chunk when there is nothing to say (a 0.22 firmware skips it) */
#define SQ_CHUNK_GHOST 3u        /* 0.24: the image's chunk of the copies (SQ_STEP_GHOST): n x (track, pattern, first, end) - the
                                  * steps first .. end-1 of that pattern are copies. The steps themselves are in the image as
                                  * plain steps (a 0.23 firmware, which skips the chunk, plays them); a copied rest is not there */
void sq_theory_default(sq_theory_t *h);
void sq_theory_sanitize(sq_theory_t *h);
void sq_thpat_sanitize(sq_thpat_t *m);
void sq_ext_default(sq_ext_t *x);
void sq_ext_sanitize(sq_ext_t *x);
/* RATE SEQ: the rate an LFO has at clock tick `tick` (24 a beat), and the tick its cycle counts from (a new rate starts it) */
uint8_t sq_lfo_rate_at(const sq_lfo_t *l, const sq_lfox_t *x, uint32_t tick);
uint32_t sq_lfo_seq_tick(const sq_lfox_t *x, uint32_t tick);
uint32_t sq_rseq_ticks(uint8_t every);                   /* 24 48 96 192 */
/* CHAIN LIST: where the chain goes after a loop: pos and loops left (in / out); returns the pattern to play */
uint8_t sq_chain_next(const sq_trackx_t *c, uint8_t *pos, uint8_t *left);
int sq_chain_find(const sq_trackx_t *c, uint8_t pattern);   /* the first entry with that pattern, -1 none */
/* the keyboard's note as TRANSPOSE: the semitones from the key's own root (as TRANSPOSE found it), -5..+6 */
int32_t sq_kb_transpose(uint8_t note, uint8_t base_root);

/* the generators' settings, kept with the project (COOK, RANDOM, BEAT, PROG, the dice, EVOLVE, the HARMONY).
 * 0.10: ONE genre for the whole machine (the library, the progressions, the dice, COOK, EVOLVE, VIAGGIO). */
enum { SQ_SCOPE_THIS = 0, SQ_SCOPE_BANK, SQ_SCOPE_ALL, SQ_SCOPE_DRUM, SQ_SCOPE_MELO, SQ_SCOPE_CUSTOM, SQ_SCOPES };
#define SQ_GT_RHYTHM 0x01u       /* which steps play, accents, ratchets, gates, conditions (always) */
#define SQ_GT_NOTES  0x02u       /* the notes move in the key (not on drum tracks) */
#define SQ_GT_CC     0x04u       /* the CC lanes' values per step */
#define SQ_GT_LFO    0x08u       /* the LFOs aimed at the track */
#define SQ_EVO_EVERY 5u          /* EVOLVE every 1, 2, 4, 8, 16 bars */
enum { SQ_GM_FREE = 0, SQ_GM_ON, SQ_GM_LIVE, SQ_GMS };   /* 0.10 GENRE: FREE = the generators ignore it; ON = its feel;
                                                          * LIVE = ON, and the tracks loaded from the library follow a change */
enum { SQ_WHEN_NOW = 0, SQ_WHEN_BAR, SQ_WHEN_2, SQ_WHEN_4, SQ_WHEN_8, SQ_WHEN_16, SQ_WHENS };   /* 0.10: a tool applies at ... */
enum { SQ_EVERY_OFF = 0, SQ_EVERY_1, SQ_EVERY_2, SQ_EVERY_4, SQ_EVERY_8, SQ_EVERY_16, SQ_EVERY_32, SQ_EVERYS };   /* ... and again every ... bars */
/* 0.24 LONG PATTERNS: what a library pattern of one bar becomes in a longer track. COPY: itself again (the track
 * repeats it); PHRASE: the long form of 0.10 (the next variation in the last bar, the genre's fill). The patterns the
 * library has written over two or four bars come as they are either way. (0.10 - 0.23: LIBRARY LEN 16 / 32 / 64, the
 * length a pattern was loaded at - and the track made that long. The length is the track's now: 16 reads as COPY,
 * 32 and 64 as PHRASE.) */
enum { SQ_LL_COPY = 0, SQ_LL_PHRASE, SQ_LLS };
#define SQ_LIB_PROGS 8u          /* the library's progressions a genre (sagga_beats.h SQ_PROGS; 0.29: 8, until then 6) */
#define SQ_UPROGS 4u             /* 0.10: progressions written by the player; harm_prog SQ_PROGS.. picks them */
#define SQ_UPROG_SLOTS (SQ_UPROGS + 1u)   /* 0.11: and one more, the progression that came from the Pi (harm_prog 12) */
#define SQ_PROG_PI (SQ_LIB_PROGS + SQ_UPROGS)       /* 0.11: harm_prog of the Pi's progression (uprog[SQ_UPROGS]) */
#define SQ_PROGS_ALL (SQ_LIB_PROGS + SQ_UPROGS + 1u)
/* 0.29: a harm_prog as 0.28 numbered it (0..5 the genre's, 6..9 the player's, 10 the Pi's) and back: the image keeps
 * 0.28's numbers; the genre's 7th and 8th go to 0.28 as its 1st (chunk 5 keeps which they were) */
uint8_t sq_prog_from28(uint8_t p);
uint8_t sq_prog_to28(uint8_t p);
typedef struct __attribute__((packed)) {
    uint8_t genre, func, var;    /* the BEAT library: what LOAD brings; genre: THE genre */
    uint8_t scope;               /* SQ_SCOPE_*: which tracks the generators work on */
    uint8_t targets;             /* SQ_GT_*: what they change */
    uint8_t density;             /* RANDOM: 0..100 */
    uint8_t heat;                /* COOK and the dice: 1..100 */
    uint8_t evo_amount;          /* EVOLVE: how much each time, 1..100 */
    uint8_t evo_every;           /* 0..SQ_EVO_EVERY-1 */
    uint8_t evo_drift;           /* 0: every change starts from the seed again; 1: each change starts from the last */
    uint8_t harm_on;             /* 0.8 HARMONY: the progression plays; the tracks with SQ_TF_FOLLOW move with it */
    uint8_t genre_mode;          /* 0.10: SQ_GM_* */
    uint8_t harm_prog;           /* ... which progression: 0..7 the genre's, 8..11 the player's (uprog), 12 the Pi's
                                  * (0.29; 0.28: 0..5, 6..9, 10 - and so in the image: sq_prog_to28) */
    uint8_t harm_bars;           /* ... bars a chord: 0 the progression's own, else 1, 2, 4, 8 */
    uint16_t custom;             /* SCOPE CUSTOM: bit per track */
    uint8_t panel_lights;        /* 0 unset (HIGH), else 1..5 OFF..MAX */
    uint8_t when;                /* 0.10: SQ_WHEN_* */
    uint8_t every;               /* 0.10: SQ_EVERY_* */
    uint8_t every_tool;          /* 0.10: the tool EVERY repeats (255: none yet) */
    uint8_t lib_len;             /* 0.10: SQ_LL_* */
    uint8_t harm_genre;          /* 0.11: the genre the HARMONY's progression is taken from. It follows `genre` when a
                                  * pattern is LOADED from another genre (or VIAGGIO / GENRE LIVE change the genre), not
                                  * while the knobs browse the library; HARM LOCK keeps it where the player put it */
    uint8_t harm_lock;           /* 0.11: 1 = the harmony changes only by the player's hand (SEQ 4 K1: LOCK) */
    uint8_t harm_free;           /* 0.16: 1 = FREE (ARP 4 K2): the chords are nobody's genre - a pattern loaded never
                                  * changes harm_genre, and ARP 3 K2 goes through every genre's progressions (harm_genre
                                  * is then the genre of the one that plays) */
    /* 0.11 (SGQB; a 0.10 image ends at 24 bytes) */
    uint8_t harm_rhythm;         /* SQ_HR_*: when the chords change (BARS: a chord every harm_bars, as 0.10) */
    uint8_t harm_mood;           /* SQ_MOOD_*: the progressions K2 goes through, and DICE PROG's (ANY: all) */
    /* 0.25 THE METRE (a 0.11 - 0.24 image has zeros here: 4/4) */
    uint8_t bar_steps;           /* the bar in 16ths: 0 = 16, else SQ_BAR_MIN .. SQ_BAR_MAX (sq_bar_steps) */
    uint8_t bar_beats[4];        /* where its beats begin: a bit a step, step 0 = bit 0 of the first byte; all 0: the bar's
                                  * usual way (sq_bar_beats) */
    uint8_t reserved11[1];
} sq_gen_t;                      /* 32 bytes */
/* 0.27 EVOLVE's RETURN: how far each change starts back towards the seed, 0..100 % - 100: from the seed itself, as
 * EVOLVE always did; 0: from the last change, DRIFT. An image without it: DRIFT's switch says which. Set: DRIFT's switch
 * follows (on below 50 %), so an older firmware plays the nearest of the two */
#define SQ_EVO_RETURN_MAX 100u
uint8_t sq_evo_return(const sq_ext_t *x, const sq_gen_t *g);
void sq_evo_return_set(sq_ext_t *x, sq_gen_t *g, uint8_t r);
#define SQ_GEN_A 24u             /* the bytes a 0.10 image holds of it */

/* 0.25 THE METRE. Until 0.24 the bar was sixteen 16ths, whatever the tracks' lengths: a length, a pattern, a tool, a
 * move that waited "for the bar" waited for a multiple of 16 steps, and the engines thought in 4/4. Now the bar is
 * `steps` 16ths (12: 3/4 or 6/8; 14: 7/8; 20: 5/4) and its BEATS are groups of them: two eighths (a quarter) or three
 * (a dotted one) in an even bar - 14 steps are 2+2+3, 2+3+2 or 3+2+2 -; quarters and one beat a 16th short or long in
 * an odd one. `beats` is a mask: bit s set = step s of the bar begins a beat (bit 0 always). */
#define SQ_BAR_MIN 3u
#define SQ_BAR_MAX 32u
#define SQ_BAR_GROUPS 16u        /* the most beats a bar can have (a mask from outside: beats of two steps) */
#define SQ_BEATS_44 0x1111u      /* 4/4: the sixteen steps in four quarters */
uint8_t  sq_bar_steps(const sq_gen_t *g);                              /* SQ_BAR_MIN .. SQ_BAR_MAX; 16 for anything else */
uint32_t sq_bar_beats(const sq_gen_t *g);                              /* the mask, put right (sq_metre_fix) */
void     sq_bar_set(sq_gen_t *g, uint8_t steps, uint32_t beats);       /* (16 steps in four quarters are written as zeros: an old image's) */
uint32_t sq_metre_fix(uint8_t steps, uint32_t beats);                  /* bit 0 set, nothing past the bar, no beat of one step; 0 or 1: the usual way */
uint8_t  sq_metre_options(uint8_t steps);                              /* how many ways a bar of `steps` divides (1 .. 37) */
uint32_t sq_metre_option(uint8_t steps, uint8_t idx);                  /* the idx-th (0: the usual one), a mask */
uint8_t  sq_metre_index(uint8_t steps, uint32_t beats);                /* which of them `beats` is; 255: none (a mask from outside) */
uint8_t  sq_metre_groups(uint8_t steps, uint32_t beats, uint8_t *len); /* the beats' lengths in steps (SQ_BAR_GROUPS places) -> how many */
uint8_t  sq_metre_beat(uint8_t steps, uint32_t beats, uint32_t s);     /* 1: step s of the bar (any s: taken modulo) begins a beat */
void     sq_metre_sig(uint8_t steps, uint32_t beats, char *out);       /* "4/4", "7/8", "6/8", "15/16": 6 chars at most + 0 */
void     sq_metre_split(uint8_t steps, uint32_t beats, char *out);     /* "2+2+3" (eighths), "4+4+4+3/16", "6x2+3": SQ_SPLIT_TEXT - 1 chars at most + 0 */
#define SQ_SPLIT_TEXT 40u        /* (a mask from outside, sixteen beats of two steps: "2+3+2+3 ..." - the bars' own ways need 16) */
/* a track's length when the bar changes: one that was a number of bars (from its loop's start) is that many of the
 * new ones - as many as fit 64 steps -, any other stays -> the new length, or 0: it stays */
uint8_t  sq_metre_follow(uint8_t len, uint8_t start, uint8_t old_bar, uint8_t new_bar);
/* RE-BARRING: `bars` bars of sixteen steps made for 4/4 (row[0 .. 16 * bars)) become `bars` bars of the metre, in
 * place (row has SQ_STEPS steps; bars * steps <= SQ_STEPS). Every beat of the new bar takes a beat of the old one:
 * the first its first, the last its last (where a pattern turns round), the ones between its second and third in turn
 * (the backbeat); a beat longer than a quarter has its second eighth again, one shorter loses its end. What is left
 * of the sixteens after the new bars is cleared. 16 steps in four quarters: nothing changes. */
void     sq_rebar(sq_step_t *row, uint8_t bars, uint8_t steps, uint32_t beats);
uint8_t  sq_rebar_src(uint8_t steps, uint32_t beats, uint8_t s);       /* the step of the 16-step bar that step s of the bar takes */
uint8_t  sq_rebar_len(uint8_t n16, uint8_t steps, uint32_t beats);     /* the steps n16 steps of sixteens are after sq_rebar (n16 itself: 4/4, or not bars) */
/* for what moves through the bar in time (the harmony's chords): the 16th of a 4/4 bar that step s stands for - never
 * going back, the beats spread over the four quarters */
uint8_t  sq_metre_virt16(uint8_t steps, uint32_t beats, uint8_t s);
/* 0.26 A BAR THOUGHT IN ITS OWN METRE (the engines: sagga_theory.c). Re-barring gives every beat of the bar a beat of
 * a 4/4 bar that was made first - and a 7/8 is then a 4/4 with a piece cut off. Here every step of the bar is given the
 * 16th of a 4/4 bar it STANDS FOR, so a part is made straight in the bar: what the step weighs, whether it carries the
 * kick or the backbeat, comes from its place in the metre.
 *   The bar is two HALVES, at the beat nearest its middle: the first stands for beats 1 and 2 (the one, and its
 *   answer), the second for beats 3 and 4. In a half the beats are the first and its answer in turn; a half with an
 *   odd number of them has two answers at its end (way 0: 5/4 as 3+2 is ONE two two | THREE four) or two firsts at
 *   its start (way 1). A half that is ONE beat is the answer (way 0: the waltz, the aksak's long last beat) or, way 1,
 *   is split when it is a long one: its first two eighths the first beat, its third eighth the answer (2+2+3 played
 *   ONE two THREE-four); a short one is then the first. When the middle falls between two beats as near, way 0 takes
 *   the later (3+2), way 1 the earlier (2+3).
 *   A bar of two beats is half a bar (two of them: ONE two | THREE four), a bar of one beat a quarter of one.
 * a16[s]: the 16th of that 4/4 bar step s stands for - 0..15 in a bar of three beats or more; 0..7 in a bar of two
 * (the caller adds 8 in every second bar); 0..3 in a bar of one (4 x the bar, modulo 4). starts: a bit a step that
 * BEGINS one of those beats. Returns how many bars of the metre make the 4/4 bar: 1, 2 or 4. 16 steps in four quarters:
 * a16[s] = s. */
uint8_t  sq_metre_native(uint8_t steps, uint32_t beats, uint8_t way, uint8_t *a16, uint32_t *starts);
/* a number for the metre, to keep with what was made in it: 0 = 4/4 (what every older image says), 1 .. SQ_METRE_IDS the
 * bars' own ways, 255 a mask from outside */
#define SQ_METRE_IDS 217u
uint8_t  sq_metre_id(uint8_t steps, uint32_t beats);
uint8_t  sq_metre_of(uint8_t id, uint8_t *steps, uint32_t *beats);     /* ... and back; 0: no such number (255: not known) */
/* THE GRID OF THE BAR, for whoever weighs a step by its place in the bar - the dice and COOK (the beat stays, the
 * backbeat, the "and", the pickup), DENSITY and the ENERGY (the beat goes last), the accents, the gates, the GROOVE's
 * sixteen places. They ask sq_g16(i): the 16th of a 4/4 bar that step i of their row stands for - i & 15 in 4/4 (the
 * way they always counted), in another metre the place re-barring gives it (sq_rebar_src). The machine says which
 * metre it is when it changes (sq_grid_set; a program that never does is in 4/4); a row that does not begin on a bar
 * line says which step of the bar its step 0 is (sq_grid_from -> the one it had: put it back after). */
void     sq_grid_set(uint8_t steps, uint32_t beats);
uint8_t  sq_grid_from(uint8_t base);
uint8_t  sq_g16(uint32_t i);
/* 0.10: a progression written by the player: chords as steps of the key and colours, like the library's.
 * 0.11: a chord may instead be a ROOT a number of semitones above the key's (any of the 12: the bVII, the bII ...)
 * with a SHAPE (the key's own chord there with a colour, or any of the 32 chord shapes), and each its own length in
 * 16ths and its PUSH (how early it comes in); the progression has a mood (the player's, or the machine's guess). */
typedef struct __attribute__((packed)) {
    uint8_t n, bars;             /* chords; bars a chord (when its dur is 0 and the HARMONY's rhythm is BARS) */
    int8_t deg[8];               /* 0.10: the step of the key (semi 255) */
    uint8_t col[8];              /* 0.10: its colour SQ_HC_* */
    uint8_t semi[8];             /* 0.11: 255 = by deg / col; 0..11 = the root, semitones above the key's root */
    uint8_t shape[8];            /* 0.11: with a root: 0..5 the key's chord on it with colour SQ_HC_* (a root out of the
                                  * key: a major chord), SQ_HSHAPE_CH + SQ_CH_* a chord shape */
    uint8_t dur[8];              /* 0.11: its length in 16ths, 1..64 (0: the HARMONY's rhythm decides) */
    uint8_t push[8];             /* 0.11: 16ths early it comes in, 0..4 (a house chord comes a 16th before the bar) */
    uint8_t mood;                /* 0.11: SQ_MOOD_* the player gave it (ANY: the machine's guess, sq_hprog_mood) */
    uint8_t reserved;
} sq_uprog_t;                    /* 52 bytes */
#define SQ_UPROG_A 18u           /* the bytes a 0.10 image holds of one */
/* the chord playing after `bar` bars: index, step, colour (bars_override 0: the progression's own length a chord) */
uint8_t sq_uprog_at(const sq_uprog_t *u, uint32_t bar, uint8_t bars_override, int8_t *deg, uint8_t *col);
void sq_uprog_name(const sq_uprog_t *u, uint8_t scale, char *out, uint32_t cap);   /* "i7-VI-III-VII" ("--": empty) */
void sq_uprog_default(sq_uprog_t *u);
void sq_uprog_sanitize(sq_uprog_t *u);
void sq_uprog_tail_default(sq_uprog_t *u);   /* 0.11: semi / shape / dur / push / mood as a 0.10 progression has them */

/* SONG: scenes in a row, each for a number of bars */
#define SQ_SONG_LEN 64u
#define SQ_SONG_BARS_MAX 64u
typedef struct __attribute__((packed)) { uint8_t scene, bars; uint16_t bpm; } sq_song_entry_t;   /* 0.10: bpm 0 = unchanged */
typedef struct __attribute__((packed)) {
    uint8_t len;                 /* entries in use, 0..SQ_SONG_LEN */
    uint8_t loop;                /* 1: after the last back to the first; 0: the last one goes on */
    sq_song_entry_t e[SQ_SONG_LEN];   /* scene 0..15, bars 1..64 */
} sq_song_t;

/* 0.26 THE METRE WITH THE SCENE: where a song is `ticks` clock ticks (24 a beat) after its start when its scenes bring
 * their metres (scene_metre: SQ_SCENES bytes, 0 = the scene leaves the metre, else sq_metre_id + 1; a null pointer: no
 * scene brings one). The song begins in the bar `steps0` / `beats0`. A song that loops goes round; one that does not
 * stays on its last entry, whose bars go on being counted. Returns 0 when the song is empty. */
typedef struct {
    uint8_t entry;               /* the entry playing */
    uint8_t bar;                 /* the bar of it (a song that does not loop, past its end: the entry's last bar) */
    uint8_t steps;               /* the bar there, in 16ths ... */
    uint8_t on_line;             /* 1: `ticks` is on a bar line */
    uint32_t beats;              /* ... and its beats */
    uint32_t line;               /* the tick of the entry's first bar line (a later round of a song that loops: of that round) */
    uint32_t bars_before;        /* the bars played before that line */
    uint32_t metre_from;         /* the tick the metre last changed at, 0 if it never did: where the tracks began again */
} sq_song_pos_t;
uint8_t sq_song_locate(const sq_song_t *sg, const uint8_t *scene_metre, uint8_t steps0, uint32_t beats0, uint32_t ticks, sq_song_pos_t *o);

/* ---- 0.9 VIAGGIO: the journey from the blank page (sagga_viaggio.c; the pure parts are here, tested on a computer).
 * The set is made of phrases of SQ_PHRASE bars. Every track is VUOTA (nothing written), PROPOSTA (it has phrases that do
 * not play), DENTRO (it plays) or FUORI (it played, and is muted). What you decide goes into the queue and happens at the
 * next phrase boundary (NOW: at the next bar). The energy, 0..100, moves the density, the velocity, the filter, the
 * colour of the chords; it glides along the phrase. The trail remembers every phrase: INDIETRO brings one back. */
#define SQ_PHRASE_MAX 16u
#define SQ_MOVES     16u             /* the queue */
#define SQ_TRAIL     128u            /* phrases remembered */
#define SQ_SET_GENRES 22u            /* 0.10: every genre of the library is a genre of the set (sagga_setgenre_data.h); 0.29: 22 */
#define SQ_ROLES     7u              /* KICK SNARE HAT PERC BASS CHORD ARP (sagga_beats.h SQ_FUNC_*) */
enum { SQ_VQ_PHRASE = 0, SQ_VQ_BAR, SQ_VQ_BEAT, SQ_VQS };   /* 0.10: when VIAGGIO's moves happen: the phrase boundary, every bar, every beat */
enum { SQ_TS_EMPTY = 0, SQ_TS_PROPOSED, SQ_TS_IN, SQ_TS_OUT };
enum { SQ_MV_NONE = 0,
       SQ_MV_IN,                 /* a: track; b: the pattern that enters (255: the proposal browsed last) */
       SQ_MV_OUT,                /* a: track */
       SQ_MV_SWAP,               /* a: track; b: the pattern that takes the place of the one playing */
       SQ_MV_FILL,               /* the last bar of the phrase with the fills */
       SQ_MV_BREAK,              /* a: the track that stays (255: none); b: bars 1, 2, 4 */
       SQ_MV_RISER,              /* the last four bars: the energy climbs to 100 */
       SQ_MV_DROP,               /* every track with a phrase in, energy 100 at once, a fill before */
       SQ_MV_HALF, SQ_MV_DOUBLE, /* the next phrase at half / twice the speed (the step, not the tempo) */
       SQ_MV_TRANSPOSE,          /* a: 12 + semitones (-12..+12) */
       SQ_MV_PROG,               /* a: the progression (harm_prog) */
       SQ_MV_GENRE,              /* a: the set genre 0..SQ_SET_GENRES-1 */
       SQ_MV_THIN, SQ_MV_SWELL,  /* two tracks out / two proposals in */
       SQ_MV_LOOP,               /* a: track; b: 0 the whole phrase, 1 four bars repeated */
       SQ_MV_KEY,                /* a: root 0..11; b: scale */
       SQ_MV_ENERGY,             /* a: the target 0..100 */
       SQ_MV_BACK,               /* INDIETRO: a phrases back in the trail */
       SQ_MV_LONGER, SQ_MV_SHORTER,   /* 0.24: every track twice / half as long (its patterns go round again in it, or wait after it) */
       SQ_MOVE_KINDS };
typedef struct __attribute__((packed)) { uint8_t kind, a, b; } sq_move_t;
typedef struct { sq_move_t m[SQ_MOVES]; uint8_t n; } sq_queue_t;
/* push: 0 ok, -1 full. A move with the same kind and track as one already queued replaces it; IN after OUT (or OUT after
 * IN) on the same track cancels both: the queue is what will change, never a history. */
int sq_queue_push(sq_queue_t *q, uint8_t kind, uint8_t a, uint8_t b);
void sq_queue_drop_last(sq_queue_t *q);
void sq_queue_remove(sq_queue_t *q, uint32_t i);
void sq_queue_clear(sq_queue_t *q);
int sq_queue_find(const sq_queue_t *q, uint8_t kind, uint8_t a);     /* index, or -1 */
uint8_t sq_move_has_track(uint8_t kind);                             /* its `a` is a track */
const char *sq_move_name(uint8_t kind);                              /* "FILL", "BREAK" ... (at most 9 chars) */

/* saved with the project */
typedef struct __attribute__((packed)) {
    uint8_t on;                  /* VIAGGIO mode */
    uint8_t phrase_bars;         /* 4, 8 or 16 */
    uint8_t energy;              /* the target, 0..100 */
    uint8_t set_genre;           /* 0..SQ_SET_GENRES-1: the genre of the set = the project's genre (gen.genre; kept in step) */
    uint8_t state[SQ_TRACKS];    /* SQ_TS_* */
    uint8_t phrase_count;        /* phrases played since the seed (the trail's index, modulo) */
    uint8_t quant;               /* 0.10: SQ_VQ_*: the moves happen at the phrase boundary, at the bar, at once */
    uint8_t reserved[6];
} sq_viaggio_t;
void sq_viaggio_default(sq_viaggio_t *v);
void sq_viaggio_sanitize(sq_viaggio_t *v);

/* one phrase as the trail keeps it: 26 bytes, 128 of them (3.3 KB) */
typedef struct __attribute__((packed)) {
    uint8_t pattern[SQ_TRACKS];
    uint16_t mute;               /* bit per track: it did not play */
    uint8_t energy, key_root, key_scale, set_genre, prog, flags;   /* flags: SQ_PF_* */
    uint16_t bpm;
} sq_phrase_t;
#define SQ_PF_HARM 0x01u         /* the HARMONY was on */
#define SQ_PF_HALF 0x02u         /* the phrase played at half speed */
#define SQ_PF_DOUBLE 0x04u
#define SQ_PF_BARS(f) ((uint8_t)(4u << (((f) >> 4) & 3u)))     /* bits 4-5: the phrase's length, 4, 8 or 16 bars */
#define SQ_PF_BARS_FLAG(b) ((uint8_t)((((b) >= 16u ? 2u : (b) >= 8u ? 1u : 0u)) << 4))
typedef struct { uint8_t head, n; } sq_trail_t;    /* ring of SQ_TRAIL: head = where the next one goes */
void sq_trail_init(sq_trail_t *t);
void sq_trail_push(sq_trail_t *t, sq_phrase_t *ring, const sq_phrase_t *ph);
/* the phrase `back` phrases ago (0 = the last one pushed), or 0 if there is none */
const sq_phrase_t *sq_trail_get(const sq_trail_t *t, const sq_phrase_t *ring, uint32_t back);
void sq_trail_drop(sq_trail_t *t, uint32_t n);     /* INDIETRO: the last n phrases leave the trail */
/* SALVA VIAGGIO: the `cap` phrase states that lasted longest (runs of equal phrases count as one, their bars added):
 * out[i] = index in the trail (0 = oldest kept), bars[i] = how many bars; returns how many */
uint32_t sq_trail_scenes(const sq_trail_t *t, const sq_phrase_t *ring, uint8_t phrase_bars, uint32_t cap,
                         uint8_t *out, uint8_t *bars);

/* ---- 0.10 EXPO: a track's rhythm as an exponential curve instead of the grid (SEQ pages 5 and 6; after Kelvin T's
 * exposaw for Ksoloti Gills). The hits of a span (the step itself, a beat, a bar ...) get closer or further apart by a
 * constant ratio: an accelerando, a bouncing ball. The pattern stays as written: it says where a span starts and
 * which notes it plays. Saved with the project (SGQ9 chunk X); a 0.9 reader skips it. */
void sq_expo_default(sq_expo_t *x);
void sq_expo_sanitize(sq_expo_t *x);
uint8_t sq_expo_energy_hits(uint8_t hits, uint8_t energy);   /* 0.10: VIAGGIO's energy on the hits: 0 halves, 50 as set, 100 doubles */
uint16_t sq_expo_span_ticks(uint8_t span);                 /* clock ticks of a span; 0 for STEP */
/* where each hit starts, in us from the span's start (out[0] = 0, out[k] < span_us), by the shape and the curve;
 * the jitter uses rng. Pure. */
void sq_expo_times(const sq_expo_t *x, uint32_t span_us, uint32_t *out, uint32_t *rng);
uint8_t sq_expo_vel(const sq_expo_t *x, uint8_t vel, uint32_t k);   /* hit k's velocity by the VEL curve */
/* SETTLE, exposaw's law: a note held retriggers its envelope, and the period follows a second envelope through the
 * exponential time scale. The gap after the hit at pos_us: the settled period (a beat / hits) made 2^(depth x env)
 * shorter, env = 1 at the start then halving every quarter of the span (+), or rising over the first quarter
 * first (-). Pure. */
uint32_t sq_expo_settle_gap(const sq_expo_t *x, uint32_t pos_us, uint32_t span_us, uint32_t beat_us, uint32_t *rng);

/* the energy: what it does to the sound. Linear ramps from 0 to 100 (50 = nothing changes). */
typedef struct {
    int8_t vel;                  /* INTENSITY: -20..+20 */
    int8_t filt;                 /* FILTER: -40..+40 */
    int8_t gate;                 /* GATE: -10..+10 */
    uint8_t density;             /* hits: 60..130 % (over 100: ghost hits on the rests) */
    uint8_t lfo_pct;             /* the LFOs' depth: 50..100 % */
    uint8_t color7;              /* 1: triads get their 7th (energy >= 70) */
} sq_energy_fx_t;
void sq_energy_map(uint8_t energy, sq_energy_fx_t *out);
/* the energy applied at bar `bar` (0..bars-1) of a phrase that glides from `from` to `to` */
uint8_t sq_energy_glide(uint8_t from, uint8_t to, uint8_t bar, uint8_t bars);
/* RISER: in the last four bars (bar counts from the boundary) the energy climbs from `base` to 100 */
uint8_t sq_energy_riser(uint8_t base, uint8_t bar, uint8_t bars);

/* the genres of the set: a name, the library genre the proposals come from (and a second one for variety), the energy
 * at which each role enters (the ladder), the swing, half-time (the beat on the 3) */
typedef struct {
    const char *name;            /* at most 10 characters */
    uint8_t genre, genre2;       /* SQ_GENRE_* of sagga_beats.h */
    uint8_t ladder[SQ_ROLES];    /* the energy a role needs, 0..100 (KICK SNARE HAT PERC BASS CHORD ARP) */
    uint8_t swing;               /* 50..75 */
    uint8_t half_time;           /* 1: the snare on the 3 (dubstep, jungle in half-time feel) */
    uint8_t afro;                /* 1: the percussion comes from the AFRO/LATIN family first */
} sq_set_genre_t;
const sq_set_genre_t *sq_set_genre(uint8_t i);
/* the role a track takes in a genre: by its drum note / register if it has notes, else the i-th role of the ladder
 * (kick, bass, hat, chord, perc, arp, snare ...) skipping the roles `taken` (bit per role) */
uint8_t sq_role_for_track(uint8_t set_genre, uint8_t drum, uint8_t note, uint8_t has_notes, uint8_t i, uint8_t taken);
uint8_t sq_role_energy(uint8_t set_genre, uint8_t role);

/* AFRO/LATIN: percussion of the family, as the library writes patterns ('.', 'x', 'X', 'o', 'g'); 16 steps of a 16th,
 * or 12 steps of an eighth triplet (a 12/8 bar) */
#define SQ_AFRO_N 8u
typedef struct { const char *name; const char *text; uint8_t steps; } sq_afro_t;
const sq_afro_t *sq_afro(uint8_t i);

/* the profiles (sagga_viaggio.c has the table; this is the shape): what the firmware shows and allows */
enum { SQ_PROF_FULL = 0, SQ_PROF_PALCO, SQ_PROF_SEMPLICE, SQ_PROFILES };   /* 0.27: SEMPLICE, the lab's pages hidden (the knob: FULL, SEMPLICE, PALCO) */

/* 0.8 SNAPSHOT: everything that is not the notes. The patterns playing, the mutes and solos, the macros, the key and
 * TRANSPOSE, the HARMONY, every track's settings (channel, loop, swing, MIDI FX, EUCLID, algorithm, the CC lanes' base
 * values ...), the LFOs, the tempo (if SQ_LIVE snap_tempo), and the synths' own CC values (captured from them). */
typedef struct __attribute__((packed)) { uint8_t ch, cc, val; } sq_ccv_t;
typedef struct __attribute__((packed)) {
    uint8_t used;
    uint8_t ccn;                 /* the CC values kept, 0..SQ_SNAP_CC */
    uint16_t bpm;
    uint8_t key_root, key_scale;
    int8_t key_shift, ktrans;
    uint8_t pattern[SQ_TRACKS];
    uint16_t mute, solo;
    int8_t mac[4];               /* the macros: INTENSITY, GATE, SWING, FILTER */
    uint8_t harm_on, genre, harm_prog, harm_bars;   /* (0.10: the genre, where 0.9 kept the harmony's) */
    uint8_t morph_b;
    uint8_t key_cur;             /* 0.10: the key slot that was current */
    uint8_t harm_genre;          /* 0.11: the harmony's genre (a 0.10 image: the genre) */
    uint8_t reserved[1];
    sq_track_cfg_t track[SQ_TRACKS];
    sq_lfo_t lfo[SQ_LFOS];
    sq_ccv_t cc[SQ_SNAP_CC];
} sq_snap_t;
#define SQ_SNAP_HEAD 36u         /* the bytes of a snapshot before its tracks (0.27: 40 - sixteen patterns) */

/* 0.10: the keys of the project, sixteen slots. Slot key_cur is the key that plays (key_root / key_scale / key_shift
 * are its copy, kept in step); a scene can bring a slot, a track can be pinned to one. */
#define SQ_KEYS 16u
typedef struct __attribute__((packed)) { uint8_t root, scale; int8_t shift; uint8_t reserved; } sq_key_t;
/* 0.10: the synth on a MIDI channel: names for the CC numbers of its lanes (sagga_devices.h) */
enum { SQ_DEV_GENERIC = 0, SQ_DEV_ELEKTRON, SQ_DEV_COUNT };
const char *sq_device_name(uint8_t dev);
const char *sq_cc_name(uint8_t dev, uint8_t cc);   /* "CUTOFF", "RESO" ... or "" when it has no name (at most 7 chars) */
/* 0.10: the written note as the track plays it: the octave, the transpose (steps of the scale when IN KEY), the key */
uint8_t sq_track_note(const sq_track_cfg_t *c, int32_t note, uint8_t root, uint8_t scale, int8_t shift);

struct sq_project {
    uint32_t id;                 /* 0.8: which project this is (random, made once): the Pi files its synth patches under it */
    uint16_t bpm;                /* 30..300 */
    uint8_t clock_mode;          /* master/slave */
    uint8_t key_root;            /* 0..11: C .. B, the tonic of the key */
    uint8_t key_scale;           /* 0..SQ_SCALES-1; 0 = chromatic, the key is off */
    int8_t key_shift;            /* -24..+24: the tracks that follow the key are moved this many semitones */
    uint8_t key_cur;             /* 0.10: which of the key slots plays */
    uint8_t reserved0;
    sq_key_t key[SQ_KEYS];       /* 0.10 */
    uint8_t device[SQ_CHANNELS]; /* 0.10: SQ_DEV_* per MIDI channel */
    sq_uprog_t uprog[SQ_UPROG_SLOTS];   /* 0.10; 0.11: the fifth, the Pi's */
    sq_track_cfg_t track[SQ_TRACKS];
    sq_scene_t scene[SQ_SCENES];
    sq_lfo_t lfo[SQ_LFOS];
    sq_gen_t gen;
    sq_song_t song;
    sq_live_t live;
    sq_snap_t snap[SQ_SNAPS];
    sq_viaggio_t viaggio;        /* 0.9 */
    sq_ext_t ext;                /* 0.13: chunk 1 of the image */
    sq_theory_t th;              /* 0.23: chunk 2 of the image */
    uint16_t tape_cnt[SQ_TRACKS];                /* events of each track, in tape_ev one track after the other */
    uint16_t tape_n;                             /* events in tape_ev in all (the sum of tape_cnt) */
    uint16_t tape_reserved;                      /* (keeps the struct a multiple of 4: no padding bytes to compare) */
    sq_tape_ev_t tape_ev[SQ_TAPE_MAX];
    sq_step_t step[SQ_TRACKS][SQ_PATTERNS][SQ_STEPS];
    uint16_t reserved_end;       /* (the struct a multiple of 4 without padding: images compare whole) */
};
void sq_gen_default(sq_gen_t *g);
void sq_key_default(sq_key_t *k);

typedef struct {
    uint8_t step;
    uint8_t pattern;
    uint8_t pending_pattern;     /* 0..7, 255 = none */
    int8_t ping_dir;             /* +1/-1 */
    uint16_t div_accum;          /* incoming MIDI-clock ticks */
    uint8_t advances;            /* for random-direction loop counting */
    uint8_t prev_hit;            /* 0.10: the step before this one played (the PRE conditions) */
    uint32_t loop_count;
    uint32_t anchor;             /* 0.10: the clock tick the loop was last started at: where the track IS is where it would
                                  * be from there (sq_track_seek realigns it after a length change or a time FX) */
    uint8_t ppos[SQ_PLANES];     /* where the notes / velocities / gates with a loop of their own are: 0..length-1 */
} sq_track_rt_t;
/* 0.10: where the track is `ticks` clock ticks after its anchor (its first step at tick 0 of the count), the step of
 * `div` ticks: step, div_accum, loop_count, the planes. A RANDOM track keeps its step. Pure. */
void sq_track_seek(const sq_track_cfg_t *c, sq_track_rt_t *rt, uint32_t ticks, uint32_t div);
/* 0.25: ... the step of num / den ticks (a polyrhythm: 96/5 ...): div_accum is then how far the track's next step
 * is, in 1 / den of a tick (under den: it begins before the next tick) */
void sq_track_seek_frac(const sq_track_cfg_t *c, sq_track_rt_t *rt, uint32_t ticks, uint32_t num, uint32_t den);

/* the length of a parameter's loop (1..64-start) or 0 if it follows the track */
uint8_t sq_plane_len(const sq_track_cfg_t *c, uint8_t k);
/* the step whose note / velocity / gate plays now (the step being played if the parameter follows the track) */
uint8_t sq_plane_step(const sq_track_cfg_t *c, const sq_track_rt_t *rt, uint8_t k, uint8_t step);
/* the parameters with a loop of their own go one step on (sq_advance_step calls it) */
void sq_plane_advance(const sq_track_cfg_t *c, sq_track_rt_t *rt);
/* where they are after `steps` moves of the track from its start (a Song Position Pointer) */
void sq_plane_seek(const sq_track_cfg_t *c, sq_track_rt_t *rt, uint32_t steps);
/* the step that plays: on / off, chance, ratchets ... from `trig`; the notes, velocity and gate from the parameters' own
 * steps (row = the pattern) */
void sq_plane_compose(const sq_track_cfg_t *c, const sq_track_rt_t *rt, const sq_step_t *row, uint8_t step, sq_step_t *out);

uint32_t sq_rng_next(uint32_t *state);
uint32_t sq_hash3(uint32_t a, uint32_t b, uint32_t c);   /* the same three numbers: the same answer */
uint8_t sq_div_ticks(uint8_t div);                     /* the ticks of a step (a polyrhythm's: the whole ticks in it, 4.8 -> 4) */
/* 0.25: a step is num / den ticks: den 1 for the plain divisions, 5 or 7 for the polyrhythms (num: four of the base
 * value's steps, 96 / 48 / 24) */
void sq_div_frac(uint8_t div, uint16_t *num, uint8_t *den);
uint8_t sq_div_tuplet(uint8_t div);                    /* 0 a plain division; 5 or 7: that many steps in the time of four */
uint8_t sq_echo_ticks(uint8_t idx);
/* prev_hit: the step before played (the PRE conditions); FIRST is loop_count 0 */
uint8_t sq_condition_pass(uint8_t cond, uint32_t loop_count, uint8_t fill, uint8_t prev_hit);
uint8_t sq_step_should_play(const sq_step_t *s, uint32_t loop_count, uint8_t fill, uint8_t prev_hit, uint32_t *rng);
const char *sq_cond_name(uint8_t c);
uint8_t sq_advance_step(const sq_track_cfg_t *cfg, sq_track_rt_t *rt, uint32_t *rng);
void sq_step_default(sq_step_t *st);
void sq_track_default(sq_track_cfg_t *c, uint32_t index);
void sq_algo_default(sq_track_cfg_t *c, uint8_t algo);  /* an algorithm's parameters as it starts (slot 1) */
void sq_algo_slot_default(sq_algo_t *s, uint8_t algo);   /* 0.11: the same for any slot */
uint8_t sq_track_algo_any(const sq_track_cfg_t *c, uint8_t algo);   /* 0.11: 1 if some slot runs this algorithm */
void sq_lfo_default(sq_lfo_t *l);
void sq_project_init(sq_project_t *p);
/* put every field of the project in range (a corrupt or foreign image never crashes the player) */
void sq_project_sanitize(sq_project_t *p);
void sq_track_sanitize(sq_track_cfg_t *c);

/* Where a step starts, in microseconds from its slot: swing (odd steps are late) + nudge (signed).
 * The answer stays inside [-step/2, step - 1]: an early step starts at most half a step before its slot. */
int32_t sq_step_offset(uint32_t step_us, uint8_t step_index, uint8_t swing, int8_t nudge);

/* velocity of ratchet i of n (n >= 1) with a ramp -100..+100 */
uint8_t sq_ramp_velocity(uint8_t vel, int8_t ramp, uint8_t i, uint8_t n);

/* Long-gate encoding kept compact inside the step byte.
 * 1..100: percentage of the current ratchet slice; 101: 150% of a whole step; 102..164: 2..64 whole steps. */
#define SQ_GATE_LONG_MIN 101u
#define SQ_GATE_LONG_MAX 164u
uint8_t sq_gate_sanitize(uint8_t v);
uint8_t sq_gate_steps(uint8_t steps);   /* 0.11: a note `steps` (1..64) steps long, encoded (1: 100 %) */
uint8_t sq_gate_span(uint8_t encoded);  /* 0.11: the whole steps a gate covers (1 for 1..101) */
uint32_t sq_gate_us(uint8_t encoded, uint32_t step_us, uint32_t slice_us);

/* the notes an ARP track plays for a step, in order; returns the count (0 = no notes);
 * out holds SQ_ARP_OUT bytes. RND and WALK return the notes ascending: the caller picks. */
uint8_t sq_arp_build(const sq_step_t *s, uint8_t chord_mode, uint8_t *out);
/* the same from the notes that play (0.10: a chord shape may have more than a step holds) */
uint8_t sq_arp_build_notes(const uint8_t *notes, uint8_t n, uint8_t chord_mode, uint8_t *out);
/* Voice the notes in[0..n-1] (any order, SQ_NOTE_NONE skipped): out low-to-high; returns 0..4 notes */
uint8_t sq_voice_notes(const uint8_t *in, uint8_t n, uint8_t voicing, uint8_t *out);
/* Build a voiced chord, low-to-high, from a written step. Returns 0..4 notes. */
uint8_t sq_chord_voice(const sq_step_t *s, uint8_t voicing, uint8_t *out);
/* Apply the track's velocity MIDI FX. */
uint8_t sq_mfx_velocity(uint8_t vel, int8_t amount);

/* Euclidean rhythm: bits[i] = 1 for `pulses` hits spread evenly over len steps, rotated right by rot */
void sq_euclid(uint8_t pulses, uint8_t len, uint8_t rot, uint8_t *bits);
uint8_t sq_euclid_hit(uint8_t pulses, uint8_t len, uint8_t rot, uint8_t i);   /* one step of it */
/* 0.10 the rhythm families: EUCLID as above; TRESILLO: groups of 3 (3-3-2 over 8, 3-3-3-3-2-2 over 16 ...), `pulses`
 * of them kept from the start; NUMERIC (0.23.1): `pulses` picks one of SQ_NUMERIC_RHYTHMS base rhythms of 16 steps
 * (1 = four on the floor ... the claves ... 16 = the busiest; past 16 they come round again), repeated over the
 * steps; `rot` turns them all. (0.10-0.23: NUMERIC was the binary of the pulses-th prime number.) */
#define SQ_NUMERIC_RHYTHMS 16u
void sq_rhythm(uint8_t fam, uint8_t pulses, uint8_t len, uint8_t rot, uint8_t *bits);
uint8_t sq_rhythm_hit(uint8_t fam, uint8_t pulses, uint8_t len, uint8_t rot, uint8_t i);
const char *sq_rhythm_name(uint8_t fam);
uint8_t sq_numeric_index(uint8_t pulses);              /* the base rhythm the pulses knob picks: 0..15 */
uint16_t sq_numeric_word(uint8_t pulses);              /* its 16 steps, step 1 = the top bit */
/* its shape as the steps from each hit to the next ("3-3-4-2-4"): at most 13 characters and the 0; returns the end */
char *sq_numeric_gaps(uint8_t pulses, char *out);
/* 0.25 NUMERIC FOLLOWS THE BAR AND THE LOOP. The sixteen rhythms are written over 16 steps. In a bar of n steps
 * (sq_numeric_fit: bit s = step s) every hit falls where it does in proportion - step p of 16 on step p * n / 16: the
 * son clave over 12 steps is 2-2-3-2-3, the clave of 12/8 - and never two hits in a row (the later one goes). The unit
 * (sq_numeric_unit) is the metre's bar - the rhythm comes round every bar, the last one cut by the loop, as ever in
 * 4/4 - or the loop itself when it is shorter than a bar (until 0.24 that was the first steps of the sixteen, cut). */
uint32_t sq_numeric_fit(uint8_t pulses, uint8_t n);
uint8_t sq_numeric_unit(uint8_t len);
char *sq_numeric_gaps_n(uint8_t pulses, uint8_t n, char *out);   /* its shape in n steps: at most 31 characters and the 0 */

/* ---- 0.8 the algorithms' pure parts (dinghy.c keeps their state) */
/* TURING: the register moves one step: the bit that comes out goes back in at the top, flipped with `mutation` %
 * chance (rnd: 0..99); returns the new register (len bits) */
uint32_t sq_turing_step(uint32_t reg, uint8_t len, uint8_t mutation, uint32_t rnd);
uint64_t sq_turing_step64(uint64_t reg, uint8_t len, uint8_t mutation, uint32_t rnd);   /* 0.25: ... up to 64 steps (the same up to 32) */
uint64_t sq_turing_resize(uint64_t reg, uint8_t old_len, uint8_t new_len);   /* ... a register made new_len long: its loop again in what it has more */
/* CELL: the next generation of `cells` cells (a ring) under `rule` (Wolfram's numbering); never all empty */
uint64_t sq_cell_next(uint64_t row, uint8_t cells, uint8_t rule);
/* 0.23.1: the same, 0 when every cell died; and the row a track plays next: when every cell died the rhythm written on
 * the track (`home`) again, a single cell in the middle when nothing is written */
uint64_t sq_cell_raw(uint64_t row, uint8_t cells, uint8_t rule);
uint64_t sq_cell_step(uint64_t row, uint8_t cells, uint8_t rule, uint64_t home);
/* 0.23.1: what the rule makes of a row from here on: `lead` rows that never come back, then a loop of `period` rows
 * (1: it stays); `slide`: every row of the loop is the one before moved that many steps (+ later, - earlier);
 * `full`: it stays with every cell on. sq_cell_story returns 0 when no loop shows in SQ_CELL_STORY_STEPS rows. */
#define SQ_CELL_STORY_STEPS 192u
typedef struct { uint8_t lead, period; int8_t slide; uint8_t full; } sq_cell_story_t;
uint8_t sq_cell_story(uint64_t row, uint8_t cells, uint8_t rule, uint64_t home, sq_cell_story_t *out);
/* ACCENT: the velocity change of step i (amount 0..63) for a style; rnd for RANDOM */
int32_t sq_accent(uint8_t style, uint8_t amount, uint8_t offset, uint32_t i, uint32_t rnd);
/* DENSITY: does step i (written on or off) play in this loop? `h` a hash of (track, step, loop); density 0..200; *ghost
 * set when it is a hit the algorithm adds */
uint8_t sq_density_hit(uint8_t written, uint8_t density, uint32_t i, uint32_t h, uint8_t *ghost);

/* editing tools on one pattern row; len = how many steps to work on (give them row + start and length - start
 * to work on the loop only) */
void sq_row_clear(sq_step_t *row);
void sq_row_reverse(sq_step_t *row, uint8_t len);
void sq_row_shift(sq_step_t *row, uint8_t len, int8_t dir);               /* dir > 0 right, else left */
void sq_row_random(sq_step_t *row, uint8_t len, uint8_t density, uint32_t *rng);
void sq_row_euclid(sq_step_t *row, uint8_t len, uint8_t pulses, uint8_t rot);
void sq_row_rhythm(sq_step_t *row, uint8_t len, uint8_t fam, uint8_t pulses, uint8_t rot);   /* 0.10: any family */
void sq_row_invert(sq_step_t *row, uint8_t len);                          /* hits become rests and the rests hits */
void sq_row_humanize(sq_step_t *row, uint8_t len, uint32_t *rng);        /* a little random velocity and timing */
/* COOK: stir the pattern, the more heat (1..100) the more is changed: rhythm, accents, ratchets, gates, conditions,
 * the order of the notes it already has. The first step and the beat are the last to go. */
void sq_row_cook(sq_step_t *row, uint8_t len, uint8_t heat, uint32_t *rng);
/* 0.10 COOK by role: a KICK keeps its downbeats and gains pickups; a SNARE keeps the backbeat and gains ghosts and
 * rolls; a HAT opens up (ratchets, accents, offbeats); PERC syncopates; a BASS moves between root, fifth and octave
 * on the beats and gains pickups; a CHORD changes colour and rhythm, not its roots; an ARP changes order and gaps.
 * NONE: sq_row_cook (and the notes by sq_row_cook_notes). Melodic roles need the key. */
void sq_row_cook_role(sq_step_t *row, uint8_t len, uint8_t heat, uint8_t role, uint8_t root, uint8_t scale, uint32_t *rng);
/* 0.11: COOK on a track that came from the library walks it towards `target` (the next variation of its part, as
 * long): at most `steps` steps of row become target's, the weakest places first (16ths, then the "and"s, then the
 * beats, the bar's one last), locked steps never. Returns the steps that still differ after it (0: there). */
uint8_t sq_row_approach(sq_step_t *row, const sq_step_t *target, uint8_t len, uint8_t steps, uint32_t *rng);
/* 0.11: how long the notes of a generated melodic part last, by its role, so a written part is not a row of one-step
 * notes: a PAD holds to the next chord, a BASS holds on the beats and is short between them (a legato TIE now and
 * then), a STAB is short, a LEAD phrases (the last note of a phrase held), an ARP stays short. Locked steps and steps
 * already longer than one step are kept. */
void sq_row_phrase_gates(sq_step_t *row, uint8_t len, uint8_t role, uint8_t heat, uint32_t *rng);
/* DOUBLE: the pattern is repeated after itself; returns the new length (at most `room`, the steps there are from row) */
uint8_t sq_row_double(sq_step_t *row, uint8_t len, uint8_t room);
/* 0.24: A PATTERN IN A TRACK LONGER THAN IT IS. The length is the track's; a pattern shorter than its track goes
 * round again in the steps the track has more: those steps are its COPIES (SQ_STEP_GHOST), each the step of the
 * pattern that would play there - step i is step start + (i - start) % (own - start), `own` the pattern's own length.
 * In a row the copies are the end of the loop: own .. length-1. They are kept equal to the pattern (sq_ghost_service:
 * a step of the pattern changed, its copies change), until one of them is written by hand, or a tool rewrites the
 * loop: then all of them are the player's steps, and the pattern is as long as the track.
 * A pattern LONGER than its track (a track made shorter, a library pattern in a short track) keeps the steps the track
 * does not play; one step at rest flagged a copy, after its last, is the MARK of where it ends - so that the track
 * made longer again finds the pattern as it was, its silences too, and goes round from there.
 * (0.11 had sq_row_extend: the loop repeated into the new steps, once, the period "the length when the knob began to
 * turn" - 16, then 19 at the bar, then 32 repeated the 19: a second bar three steps off, for good.) */
/* the pattern's own length in the loop start .. len-1: where its copies begin; len when it has none; 0 when the flags
 * are not those of copies (a copy on the loop's first step, a step after the first copy that is not one) */
uint8_t sq_row_own(const sq_step_t *row, uint8_t start, uint8_t len);
/* THE TRACK'S LENGTH CHANGED, old_len -> new_len (longer, shorter, or the same: a row to be put in order). The
 * pattern ends where its copies begin, at its mark, or with the old loop; what the track has after that is the
 * pattern again, whatever lengths came before, and what the track no longer has loses its copies (the pattern's own
 * steps stay where they are, with the mark when the loop is now shorter than the pattern).
 * BUT the steps the player wrote after the pattern (a step that plays, not a copy, from old_len on) are part of it:
 * the pattern then ends with the round of itself that the last of them is in (a step written in the second bar of a
 * 16-step pattern: 32 steps; the last step alone, the 64th: all 64, silent up to it), its copies become steps, and
 * only what the track has after THAT is copied. A pattern with no step that plays has no copies and no mark.
 * Returns the copies in the loop */
uint8_t sq_row_fit(sq_step_t *row, uint8_t start, uint8_t old_len, uint8_t new_len);
/* a pattern was MADE in steps 0 .. made-1 (the library, an engine) for a track of len steps: the rest of the row is
 * cleared, then the copies (len > made) or the mark (len < made). Returns the copies */
uint8_t sq_row_made(sq_step_t *row, uint8_t made, uint8_t len);
/* a loop of steps (none flagged: a tool worked on it) that IS a pattern of `own` and its rounds - every step from own
 * on the step of the pattern that would play there: those steps are flagged its copies again. Returns 1 if it was */
uint8_t sq_row_again(sq_step_t *row, uint8_t start, uint8_t own, uint8_t len);
/* the copies become the player's steps: nothing in the row is flagged */
void sq_row_keep(sq_step_t *row);
uint8_t sq_step_alike(const sq_step_t *a, const sq_step_t *b);   /* the same step, but for SQ_STEP_GHOST */
uint16_t sq_step_hash(const sq_step_t *s);                        /* of a step without SQ_STEP_GHOST */
/* what the copies of the pattern a track plays were last seen made from: a hash a step of the pattern */
typedef struct { uint16_t h[SQ_STEPS]; uint8_t pat, own, start; } sq_ghost_t;   /* pat 255: nothing known */
enum { SQ_GH_NONE = 0,           /* no copies, or all as they should be */
       SQ_GH_AGAIN,              /* the pattern changed: its copies were made again */
       SQ_GH_KEPT };             /* a copy was written (it differs from the pattern, and is not what the pattern was): all
                                  * the copies are the player's steps now. Also when the flags are not those of copies */
/* called now and then on the pattern a track plays (pattern number `pat`, to know when it is another) */
uint8_t sq_ghost_service(sq_step_t *row, uint8_t start, uint8_t len, uint8_t pat, sq_ghost_t *g);
/* the generators' other targets: notes moved by steps of the key (chords move together), CC lane values per step
 * (lane_mask: bit per lane; base: the lanes' base values, SQ_LANE_NONE = 64), random notes of the key around center */
void sq_row_cook_notes(sq_step_t *row, uint8_t len, uint8_t heat, uint8_t root, uint8_t scale, uint32_t *rng);
void sq_row_cook_lanes(sq_step_t *row, uint8_t len, uint8_t heat, uint8_t lane_mask, const uint8_t *base, uint32_t *rng);
void sq_row_random_notes(sq_step_t *row, uint8_t len, uint8_t center, uint8_t root, uint8_t scale, uint32_t *rng);
void sq_row_random_lanes(sq_step_t *row, uint8_t len, uint8_t density, uint8_t lane_mask, uint32_t *rng);
/* 0.8 EVOLVE with the theory: the notes of a melodic part move by the rules of voice leading - on the beats the tones of
 * the tonic chord (the HARMONY moves a FOLLOW track to the chord that plays), between them steps of the scale from the
 * note before; leaps of more than a fifth come back; the register stays around `center`. A bass keeps root and fifth
 * on the beats. Chords move to the nearest inversion of the tonic or of a chord a third away. amount 0..100 */
void sq_row_evolve_notes(sq_step_t *row, uint8_t len, uint8_t amount, uint8_t root, uint8_t scale, uint8_t bass,
                         uint8_t center, uint32_t *rng);

/* ---- timing helpers for REC: where does a note played at `phase_pct` (0..99) of the step `cur` belong? */
void sq_rec_target(uint8_t cur, uint8_t start, uint8_t len, uint8_t dir, uint8_t phase_pct, uint8_t quantize,
                   uint8_t *step_out, int8_t *nudge_out);

/* ---- LFO */
uint16_t sq_lfo_ticks(uint8_t rate);                       /* the cycle, in ticks of the 24 PPQN clock */
/* the shape at one moment, -128..+127 (before depth): `tick` counts clock ticks, `frac16` is the part of the
 * current tick that has passed (0..65535) */
int16_t sq_lfo_wave(const sq_lfo_t *l, uint8_t index, uint32_t tick, uint16_t frac16);
/* a CC LFO's value 0..127 (centre +- depth) / an internal LFO's offset -64..+63 */
uint8_t sq_lfo_cc(const sq_lfo_t *l, uint8_t index, uint32_t tick, uint16_t frac16);
int16_t sq_lfo_offset(const sq_lfo_t *l, uint8_t index, uint32_t tick, uint16_t frac16);

/* ---- scales and modes: the key of the project. The notes of the tracks with SQ_TF_SCALE are moved by key_shift and
 * then to the nearest note of the key (a tie goes down) when they are played, so a change of root, scale or shift
 * applies at once to every pattern, chord and arpeggio, and changing back brings the written notes back. */
#define SQ_SCALES 21u             /* 0.29: 21 (0.28: 16 - a 0.28 opens one of the five new ones as CHROMATIC) */
#define SQ_SCALES28 16u
enum { SQ_SC_CHROMATIC = 0, SQ_SC_MAJOR, SQ_SC_MINOR, SQ_SC_DORIAN, SQ_SC_PHRYGIAN, SQ_SC_LYDIAN, SQ_SC_MIXOLYDIAN,
       SQ_SC_LOCRIAN, SQ_SC_HARM_MINOR, SQ_SC_MEL_MINOR, SQ_SC_PENT_MAJOR, SQ_SC_PENT_MINOR, SQ_SC_BLUES, SQ_SC_WHOLE,
       SQ_SC_PHRYG_DOM, SQ_SC_HIRAJOSHI,
       SQ_SC_HUNG_MINOR,         /* 0.29: HUNGARIAN MINOR (the harmonic minor with a raised 4th: drill, phonk) */
       SQ_SC_DBL_HARM,           /* ... DOUBLE HARMONIC (the flat 2nd and the major 3rd, two augmented seconds) */
       SQ_SC_LYD_DOM,            /* ... LYDIAN DOMINANT (the raised 4th and the flat 7th: funk, jazz) */
       SQ_SC_MAJ_BLUES,          /* ... MAJOR BLUES (the major pentatonic with the minor 3rd) */
       SQ_SC_IN_SEN };           /* ... IN SEN (Japanese: 1 b2 4 5 b7) */
uint16_t sq_scale_mask(uint8_t scale);             /* bit i: the note i semitones above the root belongs to the scale */
const char *sq_scale_name(uint8_t scale);          /* at most 7 characters: "DORIAN" */
const char *sq_scale_long_name(uint8_t scale);     /* "HARMONIC MINOR" */
const char *sq_root_name(uint8_t root);            /* "C", "C#", ... */
uint8_t sq_scale_snap(uint8_t note, uint8_t root, uint8_t scale);
/* shift, then snap: what a track in the key plays for this written note */
uint8_t sq_scale_apply(int32_t note, uint8_t root, uint8_t scale, int8_t shift);
/* the note `deg` steps of the scale away (snapped first; chromatic: semitones), kept in 0..127 */
uint8_t sq_scale_degree(int32_t note, uint8_t root, uint8_t scale, int32_t deg);
/* the n-th note of the scale counted from the root in the octave of `base` (n may be negative or past 7) */
uint8_t sq_scale_nth(uint8_t base, uint8_t root, uint8_t scale, int32_t n);
/* where a note is in the scale: the steps of the scale from the root of octave -1 (a note outside it: the one under) */
int32_t sq_scale_index(uint8_t note, uint8_t root, uint8_t scale);
uint8_t sq_scale_at(int32_t index, uint8_t root, uint8_t scale);   /* the note at an index (kept in 0..127) */
/* write into the patterns the notes that sound now (tracks with SQ_TF_SCALE), and put key_shift back to 0;
 * returns how many notes changed */
uint32_t sq_project_bake_scale(sq_project_t *p);

/* ---- 0.8 HARMONY: a chord of a progression is a step of the key (0 = the tonic's chord) and a colour. The notes of a
 * FOLLOW track are written on the tonic: they move by the chord's steps of the scale, and the colour changes the chord
 * (sus4 / sus2 move its third; 7, 9, 6 add that note, or put it where the fifth or a doubled note was). */
enum { SQ_HC_TRIAD = 0, SQ_HC_7, SQ_HC_9, SQ_HC_SUS4, SQ_HC_SUS2, SQ_HC_6, SQ_HCS };
/* the seven-note scale the harmony counts in: the key's own, or its parent (pentatonic, blues ...; no key: minor) */
uint8_t sq_harm_scale(uint8_t scale);
/* notes[0..n-1] (MIDI notes, already in the key; SQ_NOTE_NONE kept out) moved to the chord; `chord`: they are a chord
 * (2 notes or more, so 7 / 9 / 6 may add one); returns the count (room: SQ_POLY) */
uint8_t sq_harm_apply(uint8_t *notes, uint8_t n, uint8_t root, uint8_t scale, int8_t deg, uint8_t color, uint8_t chord);
/* "i", "VI", "iii", "vii°" ... of a step of a key (scale: the key's), with the colour: "VI9", "isus4" */
void sq_harm_chord_name(uint8_t scale, int8_t deg, uint8_t color, char *out);   /* out: 10 bytes */

/* ---- 0.11 HARMONY: a chord is a step of the key with a colour (as 0.10: semi 255), or a root 0..11 semitones above the
 * key's with a shape (sq_uprog_t). A progression plays as a row of chords, each its 16ths and its push (sq_hprog_t),
 * made from the library's or the player's by the HARMONY's RHYTHM: BARS (a chord every so many bars, 0.10), the
 * genre's own, a push of a 16th or an 8th, 3+3+2 (6, 6, 4 16ths), two a bar, 3+5, 3+1, a chord every two bars. */
#define SQ_HSHAPE_CH 5u          /* shape > 5: the chord shape SQ_CH_* (shape - 5) */
#define SQ_HSHAPES (SQ_HSHAPE_CH + SQ_CH_COUNT)   /* 0..5 the key's chord + colour, 6.. the shapes (0.29: 36, to 40) */
typedef struct { int8_t deg; uint8_t col, semi, shape; } sq_hchord_t;
#define SQ_HPROG_CH 8u            /* chords in a progression */
#define SQ_HPROG_MAX 24u          /* entries of its row: a rhythm of 2 or 3 lengths is laid over the chords round after
                                   * round until both come back together (3+3+2 over 4 chords: 12, 4 bars), so the
                                   * changes keep their places in the bar */
typedef struct { uint8_t n, nc; sq_hchord_t c[SQ_HPROG_MAX]; uint8_t dur[SQ_HPROG_MAX], push[SQ_HPROG_MAX]; } sq_hprog_t;   /* nc: the progression's chords (entry k is chord k % nc) */
enum { SQ_HR_BARS = 0, SQ_HR_GENRE, SQ_HR_PUSH16, SQ_HR_PUSH8, SQ_HR_332, SQ_HR_HALF, SQ_HR_35, SQ_HR_31, SQ_HR_2BARS, SQ_HRS };
const char *sq_hrhythm_name(uint8_t r);
/* the row of chords: a library progression (its steps, colours, bars a chord) or the player's; `bars` overrides the
 * bars a chord (0: their own); `rhythm` SQ_HR_* (GENRE: resolved by the caller to the genre's) */
void sq_hprog_lib(sq_hprog_t *h, const int8_t *deg, const uint8_t *col, uint8_t n, uint8_t bars, uint8_t rhythm);
void sq_hprog_user(sq_hprog_t *h, const sq_uprog_t *u, uint8_t bars, uint8_t rhythm);
uint32_t sq_hprog_len(const sq_hprog_t *h);                       /* its 16ths, all chords */
/* the chord at 16th `pos` of the transport (a pushed chord already sounds `push` 16ths before its place); returns
 * which chord of the progression it is (0 .. nc - 1) */
uint8_t sq_hprog_at(const sq_hprog_t *h, uint32_t pos, sq_hchord_t *c);
/* the notes of a FOLLOW track moved to the chord (written on the tonic; a chord by its step: sq_harm_apply; a root and
 * a shape: every note by its place in the tonic's chord - root, third, fifth, seventh, ninth ... - to that of the shape,
 * the nearest octave, a written chord gets the shape's seventh or ninth when there is room) */
uint8_t sq_harm_apply_chord(uint8_t *notes, uint8_t n, uint8_t root, uint8_t scale, const sq_hchord_t *c, uint8_t chord);
/* 0.25 FOLLOW MELODY: the melody knows the chord. A tune is not moved with the chords as a riff is: it stays where it is
 * written, and its STRONG notes (on a beat of the metre, or longer than a step: the caller says which) go to the nearest
 * tone of the chord playing; the others play as written, passing notes of the key.
 * sq_harm_tones: the chord's tones as pitch classes (0..11) - the tonic's triad as FOLLOW moves it there, with the note
 * its colour adds (a 7th, a 9th, a 6th; a sus has its fourth or second, no third); returns how many (pc: room for
 * SQ_POLY_OUT). sq_harm_melody: the nearest of them to a note (already in the key); of two as near, the lower one. */
uint8_t sq_harm_tones(uint8_t root, uint8_t scale, const sq_hchord_t *c, uint8_t *pc);
uint8_t sq_harm_melody(uint8_t note, uint8_t root, uint8_t scale, const sq_hchord_t *c);
/* 0.26 FOLLOW SMOOTH: the chords move little. FOLLOW moves a written chord to the chord playing with the whole hand:
 * every note by the same steps (the chords of a riff, in parallel). A keyboard player does not: the notes two chords
 * share stay where they are, the others go to the nearest note of the new chord - an inversion. Here the chord is first
 * moved as FOLLOW always moved it (sq_harm_apply_chord: what kind of chord it is, the colour the progression adds, stay
 * the same), then each of its notes is put in the octave nearest to a WRITTEN note, one each, the way that moves the
 * least in all (of two ways as near: the one more notes stay still in). So the voicing stays about where it was
 * written whatever the chord, and nothing depends on the chord before. `notes` holds SQ_POLY_OUT; returns the count. */
uint8_t sq_harm_smooth(uint8_t *notes, uint8_t n, uint8_t root, uint8_t scale, const sq_hchord_t *c);
/* 0.26 LIVE CHORDS: the notes held on a keyboard as a chord of the HARMONY. `mask`: a bit a pitch class held (bit 0 = C),
 * `bass`: the lowest note held (its pitch class counts). sq_chord_detect: the root (0..11) and the shape SQ_CH_* that
 * fit best - every note of the shape there and no other is best; a fifth left out costs little, a third or a seventh
 * more, a note the shape has not most; of two as good, the one whose root is the bass, then the simpler shape. One
 * note: SQ_CH_OFF (the caller: the key's own chord on it). Returns 0 when nothing is held.
 * sq_hchord_live: ... as a chord of the harmony in the key - the key's own chord on that step with its colour when it is
 * one (it is named "vi7" and a FOLLOW track moves to it by the steps of the key), else the root and the shape. */
uint8_t sq_chord_detect(uint16_t mask, uint8_t bass, uint8_t *root, uint8_t *shape);
uint8_t sq_hchord_live(sq_hchord_t *c, uint16_t mask, uint8_t bass, uint8_t key_root, uint8_t key_scale);
void sq_hchord_name(uint8_t scale, const sq_hchord_t *c, char *out);   /* "bVII", "iv7", "bIImaj7", "Vsus4" (12 bytes) */
const char *sq_degree_name(uint8_t semi);                              /* 0.12: "I", "bII" .. "VII" for 0..11 semitones above the key */
uint8_t sq_hchord_semi(uint8_t scale, const sq_hchord_t *c);    /* its root, semitones above the key's */
void sq_hchord_explicit(uint8_t scale, const sq_hchord_t *c, uint8_t *semi, uint8_t *shape);   /* as a root and a shape SQ_HSHAPE_CH + SQ_CH_* (for the Pi) */
uint8_t sq_hchord_quality(uint8_t scale, const sq_hchord_t *c, uint8_t *ext);   /* 0 major 1 minor 2 dim 3 aug 4 sus; *ext: bit 0 a 7th, 1 a maj7, 2 a 9th or more */
/* the moods a progression can have; sq_hprog_mood guesses one from what it is (minor chords, the borrowed bVI and
 * bVII, the cadence V-I, the colours, the sus, the tritone, how fast it moves) */
enum { SQ_MOOD_ANY = 0, SQ_MOOD_SAD, SQ_MOOD_MELANCHOLY, SQ_MOOD_SATISFYING, SQ_MOOD_ENERGETIC, SQ_MOOD_EUPHORIC,
       SQ_MOOD_EPIC, SQ_MOOD_DREAMY, SQ_MOOD_DARK, SQ_MOOD_TENSE, SQ_MOOD_SUSPENDED, SQ_MOODS };
const char *sq_mood_name(uint8_t m);
uint8_t sq_hprog_mood(const sq_hprog_t *h, uint8_t scale);
/* DICE PROG: a new progression of that mood (ANY: any) into u, from the shapes progressions of the mood have, turned
 * and coloured at random; `rhythm` decides the lengths (BARS: a bar a chord) */
void sq_uprog_dice(sq_uprog_t *u, uint8_t mood, uint8_t minor_key, uint8_t rhythm, uint32_t *rng);

/* ---- note names */
/* "C4", "C#3", "G-1"; 60 = C4. out holds 5 bytes. */
void sq_note_name(uint8_t note, char *out);

/* ---- 0.12 BREAK: a drum break cut into slices on consecutive notes of a sampler (slice 1 = the track's pen note).
 * A CHOP is a bar of 16 steps that says which slice each step plays (0 = a rest), with the steps that roll (a ratchet)
 * and the accents: the library of re-orders jungle, drum+bass and footwork live on. The backbone of a one-bar break at
 * 16ths: slice 1 is the kick on the one, 5 the snare on the two, 9 the kick on the three, 13 the snare on the four. */
#define SQ_BRK_CHOPS 16u             /* one a white key: 1 STRAIGHT 2 END ROLL 3 RUSH 4 REPEAT 5 DOUBLE 6 HALF 7 BACKWARDS 8 GHOST
                                        9 LOW 10 HIGH 11 SHUFFLE 12 THINK 13 APACHE 14 SNARES 15 TRIPLE 16 BUILD */
typedef struct {
    const char *name;            /* at most 9 characters */
    uint8_t sl[16];              /* the slice a step, 1..16; 0 = a rest */
    uint16_t roll;               /* bit per step: the step rolls (ratchet 2) */
    uint16_t acc;                /* bit per step: an accent */
    uint8_t gate;                /* the steps' gate: 100 = the step, 102 = two steps (HALF: a slice held through the gap) */
} sq_brk_chop_t;
const sq_brk_chop_t *sq_brk_chop(uint8_t i);
/* the chops of a genre (sagga_beats.h's 25), the ones COOK walks in this order: the count, and chop `pos` (0..count-1) */
uint8_t sq_brk_genre_chops(uint8_t genre);
uint8_t sq_brk_genre_chop(uint8_t genre, uint8_t pos);
#define SQ_BRK_SLICES(sl) ((sl) == 0u ? 8u : (sl) == 2u ? 32u : 16u)   /* SQ_BRK_SL(cfg) -> how many slices */
/* step i of `row` plays `slice` (1..); 0 = a rest (the step goes off, its note kept). n_slices: the break's (a slice
 * past them wraps). The step's other notes are cleared: a slice is one note. */
void sq_brk_step(sq_step_t *row, uint8_t i, uint8_t slice, uint8_t pen, uint8_t n_slices, uint8_t gate, uint8_t vel);
/* the chop written over the loop start..length-1, a bar (16 steps) at a time; the steps keep their chance / condition /
 * lanes. vel: the velocity of a plain step (an accent is +20) */
void sq_brk_apply(sq_step_t *row, uint8_t start, uint8_t length, uint8_t chop, uint8_t pen, uint8_t n_slices);
/* the dice: the backbone kept (slice 1 on steps 1 and 9, slice 5 on 5 and 13 of each bar), `swap` (0..7) of the other
 * steps given another slice, `roll` (0..7) steps rolled, a few rests at low heat, the rolls grow with heat (1..100) */
void sq_brk_dice(sq_step_t *row, uint8_t start, uint8_t length, uint8_t pen, uint8_t n_slices, uint8_t swap, uint8_t roll,
                 uint8_t heat, uint32_t *rng);
/* a step's slice (1..) as written, 0 when the step is off or plays a note outside the break */
uint8_t sq_brk_slice_of(const sq_step_t *s, uint8_t pen, uint8_t n_slices);
/* the pattern's slices half / double / backwards: the chops' transforms over what is written */
void sq_brk_half(sq_step_t *row, uint8_t start, uint8_t length, uint8_t pen, uint8_t n_slices);
void sq_brk_double(sq_step_t *row, uint8_t start, uint8_t length, uint8_t pen, uint8_t n_slices);
void sq_brk_backwards(sq_step_t *row, uint8_t start, uint8_t length);

/* ---- saved projects. 0.11 writes SGQB and reads SGQB and SGQA (0.10; older images are refused: the format was made
 * over, the user's choice). The project's settings at their sizes, the snapshots (a track or the LFOs equal to the
 * project's are not written again), the patterns sparse (a step as the bytes that differ from an empty one), the tape
 * events, then a tail of chunks (tag, 16-bit length, data; tag 0 ends it) for what comes later: a reader skips what it
 * does not know. SGQB: the harmony's own genre and lock (bytes that were reserved in SGQA: a 0.10 image gets the
 * genre), and whatever 0.11 adds below. */
#define SQ_SAVE_MAGIC 0x42514753u      /* "SGQB" */
#define SQ_SAVE_MAGICA 0x41514753u     /* "SGQA": 0.10, read */
#define SQ_SAVE_MAGIC9 0x39514753u     /* "SGQ9": refused (tests) */
#define SQ_SAVE_MAGIC7 0x37514753u     /* "SGQ7": refused (tests) */
#define SQ_DELAY_MAX 30                /* ms either way */
/* RELOAD: one track's settings and one of its patterns, as an image has them (the rest of the image is not read);
 * 0 = ok, both sanitised */
int sq_image_track(const uint8_t *in, uint32_t len, uint8_t t, uint8_t pat, sq_track_cfg_t *cfg, sq_step_t *row);
/* 0.23: ... and what the engines knew of the pattern (th->style 0: nothing: it was not theirs) */
int sq_image_track_th(const uint8_t *in, uint32_t len, uint8_t t, uint8_t pat, sq_track_cfg_t *cfg, sq_step_t *row, sq_thpat_t *th);
/* returns the number of bytes written, or 0 if `cap` is too small */
uint32_t sq_serialize(const sq_project_t *p, uint8_t *out, uint32_t cap);
/* 0 = ok; the project is rebuilt from the image and sanitised */
int sq_deserialize(sq_project_t *p, const uint8_t *in, uint32_t len);
/* 0.28: an image of 0.27 or before has sixteen tracks: the first twelve are read, its tracks 13-16 are left out (and
 * what was aimed at them: an LFO stops, a MOD slot goes OFF, their mutes go) */
/* 0 if sq_deserialize() would take the image whole (it reads nothing into a project): check first, then replace */
int sq_image_ok(const uint8_t *in, uint32_t len);
/* 0.29: a genre (or a THEORY style) of 0.28's numbering as 0.29 numbers it (v29: the image is 0.29's - its AFRO HOUSE is
 * BALANI), and back (BALANI: AFRO HOUSE) */
uint8_t sq_genre_from28(uint8_t g, uint8_t v29);
uint8_t sq_genre_to28(uint8_t g);
uint32_t sq_crc32(const uint8_t *p, uint32_t n);

#endif
