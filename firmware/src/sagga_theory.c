/* SPDX-License-Identifier: GPL-3.0-only
 * SAGGA SEQ 0.23: the THEORY engines (sagga_theory.h). The rules of a style and the engines that turn them into a
 * part. No signed 64-bit numbers, no 64-bit division (the FM-1's library has neither).
 *
 * WHERE THE RULES COME FROM
 *   TECHNO, HOUSE, DRUM AND BASS, DUBSTEP and FREE: written by hand, below, from what is written about the genres.
 *   The other 21 genres: COUNTED from the library of the FM-1 itself (tools/theory/gen_rules.py -> sagga_theory_data.h),
 *   the way of GESMI: the variations of a part that are one pattern are a FAMILY; what nearly all of them play is
 *   always there, what some play has a weight; a variation of two bars gives a rule for the bar and one for its answer.
 *
 * HOW A PART IS MADE
 *   the rhythm   a bar of 16ths. Some hits are always there (the four kicks of techno, the snare on 2 and 4), some
 *                never (a rumble on the kick). Every other 16th has a WEIGHT, 0..15: how likely a hit is there, from
 *                the metre and from the style. A CLASS of 16ths (the beats, the 'e's, the '&'s, the 'a's) can come as
 *                one choice: that is what makes a hat or a shaker regular instead of sprinkled. A cycle of 3 16ths can
 *                run over the bar lines (the percussion of techno). Bars 2 and 4 make a share of the choices again
 *                (the answer to bar 1), the last bar gets the style's fill.
 *   a line       (a bass, a sub, a rumble) the rhythm, then a tone of the chord for each note: the root on the one,
 *                the root, fifth or octave on the beats, the octave right after a root, a turn at the end.
 *   chords       (a stab, a pad, a piano) the rhythm, then the kind of chord; the HARMONY moves them.
 *   a motif      (a lead, a voice) the rhythm, then a walk on the steps of the scale: mostly by step, a leap now and
 *                then and back by step after it, chord tones on the beats, home at the end.
 *   an arpeggio  the chord's tones in an order, one a note.
 *   the chords   the roots move by the steps of the scale the style favours (a fourth up in house, a step down or
 *                the flat second in techno, the flat sixth and seventh in drum and bass), never onto a diminished or
 *                an augmented chord; the last chord is one that leads home.
 * Every choice is a number 0..255 made from the seed, the part and what is being chosen: nothing depends on the order
 * the parts are made in, and a variation changes only the choices it draws again. */
#include "sagga_theory.h"
#include "sagga_theory_data.h"

typedef char th_free_is_the_style_past_the_genres[SQ_TH_FREE == SQ_GENRES && SQ_TH_STYLES == SQ_GENRES + 1u ? 1 : -1];

/* ------------------------------------------------------------------ the numbers */
static uint32_t th_mix(uint32_t h)
{
    h ^= h >> 16; h *= 0x7FEB352Du; h ^= h >> 15; h *= 0x846CA68Bu; h ^= h >> 16;
    return h;
}
static uint32_t th_raw(uint32_t seed, uint32_t part, uint32_t key, uint32_t salt)
{
    return th_mix(th_mix(seed + 0x9E3779B9u * (part + 1u)) ^ (key * 0x85EBCA6Bu + salt * 0xC2B2AE35u + 0x165667B1u));
}
/* the seed's own number for a choice: 0..255 */
static uint32_t th_u0(const sq_th_t *t, uint32_t part, uint32_t key, uint32_t salt)
{
    return th_raw(t->seed, part, key, salt) >> 24;
}
/* ... and the number the variation plays with: the seed's own, or - for `vary` % of the choices - another */
static uint32_t th_u(const sq_th_t *t, uint32_t part, uint32_t key, uint32_t salt)
{
    if (t->var && t->vary) {
        uint32_t again = th_raw(t->seed ^ (t->var * 0x27D4EB2Fu), part, key, salt + 0x100u);
        if (again % 100u < t->vary) return th_raw(t->seed ^ (t->var * 0x9E3779B1u + 0x7F4A7C15u), part, key, salt) >> 24;
    }
    return th_raw(t->seed, part, key, salt) >> 24;
}
/* ... and the number of a BIG choice (which 16ths a hat has, the shape of a motif, the kind of the chords): a small
 * variation, up to 40 %, never makes it again; from there the chance rises to all of them at 100 % */
static uint32_t th_ub(const sq_th_t *t, uint32_t part, uint32_t key, uint32_t salt)
{
    if (t->var && t->vary > 40u) {
        uint32_t again = th_raw(t->seed ^ (t->var * 0x27D4EB2Fu), part, key, salt + 0x100u);
        if (again % 60u < (uint32_t)t->vary - 40u) return th_raw(t->seed ^ (t->var * 0x9E3779B1u + 0x7F4A7C15u), part, key, salt) >> 24;
    }
    return th_raw(t->seed, part, key, salt) >> 24;
}
/* lo at energy 0, hi at 100 */
static uint32_t th_en(const sq_th_t *t, uint32_t lo, uint32_t hi)
{
    uint32_t e = t->energy > 100u ? 100u : t->energy;
    return hi >= lo ? lo + (hi - lo) * e / 100u : lo - (lo - hi) * e / 100u;
}
/* one of n things by their weights, with a number 0..255 */
static uint32_t th_pick(const uint8_t *w, uint32_t n, uint32_t u)
{
    uint32_t total = 0u, i, x, acc = 0u;
    for (i = 0; i < n; i++) total += w[i];
    if (!total) return 0u;
    x = u * total / 256u;
    for (i = 0; i < n; i++) { acc += w[i]; if (x < acc) return i; }
    return n - 1u;
}

/* ------------------------------------------------------------------ the rules of a rhythm */
enum { TH_G = 1, TH_O, TH_X, TH_A };                 /* a ghost, a soft hit, a hit, an accent */
enum { TH_F_NONE = 0, TH_F_PICK, TH_F_ROLL, TH_F_LATE, TH_F_TRIP, TH_F_HAT, TH_F_BUSY };
enum { TH_K_NONE = 0, TH_K_AVOID, TH_K_WITH };       /* the kick of the same band: never where it is / likelier where it is */
enum { TH_K_APART = 0x10,       /* no two hits on 16ths next to each other */
       TH_K_LV = 0x20,          /* a rule counted from the library: the level of a hit is its place's (lv), whatever its weight */
       TH_K_TWO = 0x40 };       /* ... and the rule after it in the table is the one of bars 2 and 4 (its style: 255, no genre) */
#define TB(s) ((uint16_t)(1u << (s)))
#define TH_BEATS 0x1111u
#define TH_OFFS  0x4444u
#define TH_EIGHT 0x5555u
#define TW(a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p) \
    {(uint8_t)((a) << 4 | (b)), (uint8_t)((c) << 4 | (d)), (uint8_t)((e) << 4 | (f)), (uint8_t)((g) << 4 | (h)), \
     (uint8_t)((i) << 4 | (j)), (uint8_t)((k) << 4 | (l)), (uint8_t)((m) << 4 | (n)), (uint8_t)((o) << 4 | (p))}
#define TW0 {0, 0, 0, 0, 0, 0, 0, 0}
#define TCL(beat, e, and, a) ((uint8_t)(((beat) - 1u) | ((e) - 1u) << 2 | ((and) - 1u) << 4 | ((a) - 1u) << 6))
#define TH_NOCLS {0, 0, 0, 0}, 0, 0, 0, 0
#define TH_HAND 0, 0, 0, 0                           /* (a rule written by hand: nothing of what only a counted rule has) */
#define TL(hi, lo) (((uint32_t)(hi) << 16) | (uint32_t)(lo))   /* the levels of a counted rule: 16ths 9-16, 16ths 1-8 */

typedef struct {
    uint8_t style, func;
    uint8_t pick;                /* its share among the rules of the same part (the families of a house bass) */
    uint16_t fixA, fixx, never;  /* a bit a 16th: always there with an accent / always there / never there */
    uint8_t w[8];                /* the weight of a hit on each 16th, 0..15 (a nibble each); 12 and more: an accent */
    uint8_t d_lo, d_hi;          /* how much of the weights counts at energy 0 / 100, 0..255 */
    uint8_t soft, soft_lev;      /* a hit whose weight is `soft` or less is this (TH_G, TH_O) */
    uint8_t cls[4];              /* the chance at energy 100 that a whole class of 16ths is there: the beats, the
                                  * 'e's, the '&'s, the 'a's (255: always, whatever the energy) */
    uint8_t cls_e0;              /* ... the share of those chances left at energy 0, 0..255 */
    uint8_t cls_lev;             /* ... their levels: TCL(beats, e, and, a) */
    uint8_t cls_link;            /* 1: the classes come or stay away together (the 16ths of a shaker) */
    uint8_t hole;                /* the chance 0..255 that one hit of a class is left out */
    uint8_t cyc;                 /* low nibble: a hit every N 16ths, over the bar lines; high: its chance / 16 */
    uint8_t bar2;                /* % of the choices that bars 2 and 4 make again */
    uint8_t fill;                /* F_*: the last bar */
    uint8_t kick;                /* K_*; + TH_K_APART: no two hits on 16ths next to each other (a sub, a pad): the one that
                                  * is not always there goes; + TH_K_LV, TH_K_TWO */
    /* the rules counted from the library (the ones written by hand leave these 0) */
    uint16_t mid;                /* a bit a 16th: always there from energy TH_DATA_MID_E up (the half of a family's pattern that
                                  * goes first when the part empties) */
    uint16_t rollm;              /* a bit a 16th: a hit here can be a roll */
    uint32_t lv;                 /* two bits a 16th: the level of a hit there - 0 a hit, 1 an accent, 2 a soft hit, 3 a ghost */
    uint8_t roll;                /* bits 6-7: the roll's hits a step, less one; bits 0-5: its chance / 4 */
} th_rule_t;

#define T SQ_TH_TECHNO
#define H SQ_TH_HOUSE
#define D SQ_TH_DNB
#define S SQ_TH_DUBSTEP
#define F SQ_TH_FREE
static const th_rule_t TH_RULES[] = {
    /* ---- TECHNO: four on the floor; the clap on 2 and 4, the 4 nearly always; the hat on the '&', its 16ths by the
     * energy; a 3-against-4 percussion; a rumble on the three 16ths between the kicks, never on them */
    {T, SQ_FUNC_KICK, 0, TH_BEATS, 0, 0, TW(0,0,0,3, 0,1,0,2, 0,1,2,5, 0,1,4,6), 0, 200, 3, TH_O, TH_NOCLS, 0, 35, TH_F_PICK, 0, TH_HAND},
    {T, SQ_FUNC_CLAP, 0, TB(12), 0, 0, TW(0,1,0,0, 13,1,1,2, 0,2,1,0, 0,4,5,3), 120, 255, 5, TH_G, TH_NOCLS, 0, 30, TH_F_ROLL, 0, TH_HAND},
    {T, SQ_FUNC_HAT, 0, 0, TH_OFFS, 0, TW0, 0, 0, 0, TH_O, {60, 70, 0, 150}, 80, TCL(TH_X, TH_O, TH_X, TH_X), 0, 25, 0, 20, TH_F_HAT, 0, TH_HAND},
    {T, SQ_FUNC_OHAT, 0, 0, 0, 0, TW(0,2,6,2, 0,2,13,1, 0,2,6,0, 0,1,11,2), 160, 255, 2, TH_G, TH_NOCLS, 0, 15, TH_F_NONE, 0, TH_HAND},
    {T, SQ_FUNC_RIDE, 0, 0, 0, 0, TW0, 0, 0, 0, TH_O, {235, 30, 250, 70}, 170, TCL(TH_X, TH_O, TH_X, TH_O), 0, 15, 0, 10, TH_F_NONE, 0, TH_HAND},
    {T, SQ_FUNC_PERC, 0, 0, 0, 0, TW(1,4,1,4, 3,2,8,6, 0,3,2,5, 3,6,3,6), 70, 200, 3, TH_G, TH_NOCLS, 0x63, 30, TH_F_BUSY, 0, TH_HAND},
    {T, SQ_FUNC_RUMBLE, 0, 0, 0, TH_BEATS, TW0, 0, 0, 0, TH_O, {0, 170, 245, 252}, 200, TCL(TH_X, TH_O, TH_X, TH_X), 0, 12, 0, 15, TH_F_NONE, TH_K_AVOID, TH_HAND},
    {T, SQ_FUNC_BASS, 0, 0, TH_OFFS, 0, TW0, 0, 0, 0, TH_O, {110, 110, 0, 200}, 130, TCL(TH_X, TH_X, TH_X, TH_X), 0, 12, 0, 20, TH_F_NONE, 0, TH_HAND},
    {T, SQ_FUNC_STAB, 0, 0, 0, 0, TW(4,0,0,10, 0,0,10,3, 0,0,2,10, 5,5,0,3), 80, 210, 0, TH_O, TH_NOCLS, 0, 40, TH_F_NONE, 0, TH_HAND},
    {T, SQ_FUNC_PAD, 0, 0, TB(0), 0, TW(0,0,0,0, 0,1,2,1, 7,1,0,0, 0,0,0,0), 110, 240, 0, TH_O, TH_NOCLS, 0, 30, TH_F_NONE, TH_K_APART, TH_HAND},
    {T, SQ_FUNC_ARP, 0, 0, TH_EIGHT, 0, TW0, 0, 0, 0, TH_O, {0, 60, 0, 60}, 60, TCL(TH_X, TH_X, TH_X, TH_X), 1, 12, 0, 15, TH_F_NONE, 0, TH_HAND},
    /* ---- HOUSE: four on the floor, the clap on 2 and 4 always; the open hat on the '&' of 2 and 4 first; a shaker in
     * 16ths; three families of bass (the off-beat, the 3+3+2 riff, the syncopated one) and of piano */
    {H, SQ_FUNC_KICK, 0, TH_BEATS, 0, 0, TW(0,0,0,3, 0,1,0,2, 0,0,2,3, 0,1,5,5), 0, 200, 3, TH_O, TH_NOCLS, 0, 35, TH_F_PICK, 0, TH_HAND},
    {H, SQ_FUNC_CLAP, 0, TB(4) | TB(12), 0, 0, TW(0,1,2,1, 0,0,1,4, 0,3,3,2, 0,2,5,3), 40, 220, 11, TH_G, TH_NOCLS, 0, 35, TH_F_ROLL, 0, TH_HAND},
    {H, SQ_FUNC_HAT, 0, 0, TH_OFFS, 0, TW0, 0, 0, 0, TH_O, {120, 30, 0, 80}, 90, TCL(TH_X, TH_O, TH_X, TH_O), 0, 20, 0, 20, TH_F_HAT, 0, TH_HAND},
    {H, SQ_FUNC_OHAT, 0, 0, 0, 0, TW(0,4,5,1, 0,3,14,2, 0,0,5,1, 0,2,13,2), 175, 255, 4, TH_G, TH_NOCLS, 0, 15, TH_F_NONE, 0, TH_HAND},
    {H, SQ_FUNC_SHAKER, 0, 0, TH_OFFS, 0, TW0, 0, 0, 0, TH_O, {150, 150, 0, 150}, 60, TCL(TH_X, TH_O, TH_X, TH_O), 1, 15, 0, 15, TH_F_NONE, 0, TH_HAND},
    {H, SQ_FUNC_PERC, 0, 0, 0, 0, TW(0,0,8,2, 0,2,12,1, 0,0,4,3, 3,1,11,1), 120, 240, 2, TH_O, TH_NOCLS, 0, 55, TH_F_BUSY, 0, TH_HAND},
    {H, SQ_FUNC_BASS, 35, 0, TH_OFFS, 0, TW(0,0,0,2, 3,0,0,1, 0,0,0,3, 3,0,0,2), 40, 160, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, 0, TH_HAND},
    {H, SQ_FUNC_BASS, 35, 0, TB(0) | TB(3) | TB(6) | TB(8) | TB(11) | TB(14), 0, TW(0,0,0,0, 0,0,0,1, 0,2,0,0, 2,0,0,2), 0, 150, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, 0, TH_HAND},
    {H, SQ_FUNC_BASS, 30, 0, TB(2) | TB(8) | TB(14), 0, TW(3,0,0,4, 9,2,5,0, 0,2,3,6, 7,0,0,2), 100, 230, 0, TH_O, TH_NOCLS, 0, 30, TH_F_NONE, 0, TH_HAND},
    {H, SQ_FUNC_PIANO, 40, 0, TB(0) | TB(3) | TB(6) | TB(8) | TB(11) | TB(14), 0, TW(0,0,0,0, 0,0,0,0, 0,0,2,0, 0,0,0,2), 0, 120, 15, TH_O, TH_NOCLS, 0, 20, TH_F_NONE, 0, TH_HAND},
    {H, SQ_FUNC_PIANO, 30, 0, TH_OFFS, 0, TW(0,0,0,1, 0,0,0,3, 0,0,0,5, 0,2,0,2), 60, 200, 15, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, 0, TH_HAND},
    {H, SQ_FUNC_PIANO, 30, 0, TB(2) | TB(5) | TB(7) | TB(10) | TB(13) | TB(15), 0, TW(0,0,0,0, 0,0,0,0, 4,5,0,5, 0,0,0,0), 60, 200, 15, TH_O, TH_NOCLS, 0, 20, TH_F_NONE, 0, TH_HAND},
    {H, SQ_FUNC_PAD, 0, 0, TB(0), 0, TW(0,0,0,0, 0,0,7,0, 3,0,0,0, 0,0,3,0), 80, 200, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART, TH_HAND},
    {H, SQ_FUNC_VOX, 0, 0, 0, 0, TW(0,0,9,4, 2,2,0,2, 0,0,9,0, 8,0,3,0), 150, 255, 2, TH_O, TH_NOCLS, 0, 50, TH_F_NONE, 0, TH_HAND},
    {H, SQ_FUNC_ARP, 50, 0, TH_EIGHT, 0, TW0, 0, 0, 0, TH_O, {0, 0, 0, 0}, 0, 0, 0, 14, 0, 15, TH_F_NONE, 0, TH_HAND},
    {H, SQ_FUNC_ARP, 50, 0, 0, 0, TW0, 0, 0, 0, TH_O, {255, 255, 255, 255}, 255, TCL(TH_X, TH_X, TH_X, TH_X), 0, 10, 0, 15, TH_F_NONE, 0, TH_HAND},
    /* ---- DRUM AND BASS: the two-step - the kick on the one and on the '&' of 3, the snare on 2 and 4 - with ghost
     * snares between; the hats in 8ths; the last snare an 8th late now and then (the break's third bar); a sub that
     * starts with the kicks and holds */
    {D, SQ_FUNC_KICK, 0, TB(0), TB(10), 0, TW(0,0,2,2, 0,0,0,1, 2,0,0,3, 5,1,1,3), 30, 170, 2, TH_O, TH_NOCLS, 0, 45, TH_F_PICK, 0, TH_HAND},
    {D, SQ_FUNC_SNARE, 0, TB(4) | TB(12), 0, 0, TW(0,3,2,3, 0,3,0,9, 2,4,0,9, 0,4,2,5), 90, 230, 11, TH_G, TH_NOCLS, 0, 40, TH_F_LATE, 0, TH_HAND},
    {D, SQ_FUNC_HAT, 0, 0, TH_EIGHT, 0, TW0, 0, 0, 0, TH_O, {0, 40, 0, 130}, 60, TCL(TH_X, TH_O, TH_X, TH_X), 0, 22, 0, 20, TH_F_HAT, 0, TH_HAND},
    {D, SQ_FUNC_RIDE, 60, 0, TH_BEATS, 0, TW0, 0, 0, 0, TH_O, {0, 0, 180, 150}, 110, TCL(TH_X, TH_O, TH_O, TH_X), 0, 15, 0, 15, TH_F_NONE, 0, TH_HAND},
    {D, SQ_FUNC_RIDE, 40, 0, TH_OFFS, 0, TW(0,0,0,3, 0,0,0,3, 0,0,0,4, 0,0,0,2), 40, 160, 15, TH_O, TH_NOCLS, 0, 15, TH_F_NONE, 0, TH_HAND},
    {D, SQ_FUNC_SHAKER, 0, 0, 0, 0, TW0, 0, 0, 0, TH_O, {255, 255, 255, 255}, 255, TCL(TH_X, TH_O, TH_X, TH_O), 0, 55, 0, 15, TH_F_NONE, 0, TH_HAND},
    {D, SQ_FUNC_PERC, 65, 0, 0, 0, TW(2,9,0,3, 9,0,4,1, 5,4,4,6, 0,2,1,2), 110, 245, 11, TH_G, TH_NOCLS, 0, 35, TH_F_NONE, 0, TH_HAND},
    {D, SQ_FUNC_PERC, 35, 0, 0, 0, TW(0,0,0,0, 0,0,0,0, 0,0,3,0, 0,0,0,3), 40, 160, 3, TH_O, TH_NOCLS, 0xF3, 20, TH_F_NONE, 0, TH_HAND},
    {D, SQ_FUNC_SUB, 0, TB(0), 0, 0, TW(0,0,0,0, 0,0,3,0, 3,1,11,0, 0,0,7,0), 150, 255, 0, TH_O, TH_NOCLS, 0, 30, TH_F_NONE, TH_K_WITH | TH_K_APART, TH_HAND},
    {D, SQ_FUNC_BASS, 0, TB(0), 0, 0, TW(0,0,0,1, 0,1,3,2, 10,0,3,2, 0,0,5,2), 120, 240, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_APART, TH_HAND},
    {D, SQ_FUNC_PAD, 0, 0, TB(0), 0, TW(0,0,1,0, 0,0,5,3, 9,0,1,0, 0,0,0,1), 120, 240, 0, TH_O, TH_NOCLS, 0, 30, TH_F_NONE, TH_K_APART, TH_HAND},
    {D, SQ_FUNC_LEAD, 55, 0, TB(0) | TB(3) | TB(6) | TB(8), 0, TW(0,0,0,0, 0,0,0,2, 0,0,0,0, 2,3,2,3), 30, 160, 15, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, 0, TH_HAND},
    {D, SQ_FUNC_LEAD, 45, 0, TH_EIGHT, 0, TW(0,0,0,3, 0,0,0,3, 0,3,0,3, 0,0,0,3), 0, 140, 15, TH_O, {0, 0, 0, 0}, 0, 0, 0, 30, 0, 25, TH_F_NONE, 0, TH_HAND},
    /* ---- DUBSTEP: half-time - the kick on the one, the snare on the 3 - in phrases of two bars; sparse hats with a
     * pair of 16ths at the end; a sub in long notes; a bass whose rolls are the wobble */
    {S, SQ_FUNC_KICK, 0, TB(0), 0, 0, TW(0,1,1,0, 0,1,5,3, 3,1,6,1, 2,0,1,3), 70, 210, 3, TH_O, TH_NOCLS, 0, 60, TH_F_PICK, 0, TH_HAND},
    {S, SQ_FUNC_SNARE, 0, TB(8), 0, 0, TW(1,2,1,1, 0,1,3,3, 0,0,2,1, 0,3,1,4), 60, 190, 11, TH_G, TH_NOCLS, 0, 60, TH_F_TRIP, 0, TH_HAND},
    {S, SQ_FUNC_HAT, 75, 0, TB(4) | TB(12), 0, TW(1,0,4,1, 0,1,4,1, 2,2,4,2, 0,1,7,5), 30, 150, 1, TH_O, TH_NOCLS, 0, 40, TH_F_TRIP, 0, TH_HAND},
    {S, SQ_FUNC_HAT, 25, 0, TH_EIGHT, 0, TW0, 0, 0, 0, TH_O, {0, 30, 0, 60}, 60, TCL(TH_X, TH_O, TH_X, TH_O), 0, 25, 0, 30, TH_F_TRIP, 0, TH_HAND},
    {S, SQ_FUNC_PERC, 0, 0, 0, 0, TW(0,0,0,7, 3,1,4,1, 0,0,8,6, 0,2,4,3), 100, 235, 2, TH_O, TH_NOCLS, 0, 50, TH_F_NONE, 0, TH_HAND},
    {S, SQ_FUNC_SUB, 0, TB(0), 0, 0, TW(0,0,0,0, 0,0,8,0, 6,0,10,0, 5,0,0,0), 120, 230, 0, TH_O, TH_NOCLS, 0, 45, TH_F_NONE, TH_K_WITH | TH_K_APART, TH_HAND},
    {S, SQ_FUNC_BASS, 0, 0, TB(0), 0, TW(0,1,0,8, 0,0,5,1, 11,1,0,0, 11,2,2,1), 160, 255, 2, TH_O, TH_NOCLS, 0, 40, TH_F_NONE, 0, TH_HAND},
    {S, SQ_FUNC_PAD, 0, 0, TB(0), 0, TW(0,0,0,0, 0,0,1,0, 3,1,0,0, 0,0,0,0), 40, 140, 0, TH_O, TH_NOCLS, 0, 50, TH_F_NONE, TH_K_APART, TH_HAND},
    {S, SQ_FUNC_LEAD, 55, 0, TB(0) | TB(4) | TB(6) | TB(8), 0, TW(0,0,0,0, 0,0,0,0, 0,0,0,0, 2,0,2,3), 20, 150, 15, TH_O, TH_NOCLS, 0, 40, TH_F_NONE, 0, TH_HAND},
    {S, SQ_FUNC_LEAD, 45, 0, TB(0), 0, TW(0,0,7,9, 3,6,10,3, 10,3,7,0, 9,0,6,4), 150, 255, 3, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, 0, TH_HAND},
    /* ---- FREE: no genre. The metre (the one, the beats, the 8ths, the 16ths) and what a family of parts does: a kick
     * leans on the beats, a snare on 2 and 4, a hat on the 8ths, the percussion off them. One rule a family. */
    {F, SQ_FUNC_KICK, 0, TB(0), 0, 0, TW(0,1,3,2, 9,1,3,2, 10,1,3,3, 9,1,4,3), 40, 220, 3, TH_O, TH_NOCLS, 0, 40, TH_F_PICK, 0, TH_HAND},
    {F, SQ_FUNC_SNARE, 0, 0, 0, 0, TW(1,1,2,2, 11,1,2,3, 3,2,2,3, 11,2,3,3), 80, 230, 3, TH_G, TH_NOCLS, 0, 40, TH_F_ROLL, 0, TH_HAND},
    {F, SQ_FUNC_HAT, 0, 0, 0, 0, TW0, 0, 0, 0, TH_O, {150, 50, 200, 90}, 100, TCL(TH_X, TH_O, TH_X, TH_O), 0, 30, 0, 25, TH_F_HAT, 0, TH_HAND},
    {F, SQ_FUNC_PERC, 0, 0, 0, 0, TW(2,4,3,5, 2,4,6,5, 2,4,3,5, 3,5,5,5), 40, 170, 3, TH_O, TH_NOCLS, 0x53, 40, TH_F_BUSY, 0, TH_HAND},
    {F, SQ_FUNC_BASS, 0, 0, TB(0), 0, TW(0,2,6,4, 6,2,6,3, 7,2,5,4, 6,2,7,3), 60, 220, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, 0, TH_HAND},
    {F, SQ_FUNC_CHORD, 0, 0, TB(0), 0, TW(0,0,3,3, 4,1,5,2, 6,1,3,3, 4,2,4,2), 30, 160, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, 0, TH_HAND},
    {F, SQ_FUNC_ARP, 0, 0, 0, 0, TW(8,2,6,4, 7,2,6,4, 8,2,6,4, 7,3,6,4), 60, 230, 3, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, 0, TH_HAND},
    {F, SQ_FUNC_LEAD, 0, 0, TB(0), 0, TW(0,1,5,6, 5,1,7,2, 7,1,5,4, 5,2,5,3), 90, 240, 1, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, 0, TH_HAND},
    /* ---- the other genres: counted from the library (sagga_theory_data.h) */
    TH_DATA_RULES
};
#define TH_N_RULES (sizeof TH_RULES / sizeof TH_RULES[0])

/* ------------------------------------------------------------------ the rules of the notes */
/* a line: the weights of root, fifth, octave, third, seventh, fourth, second, sixth; chances 0..255 */
typedef struct {
    uint8_t style, func;
    uint8_t tone[8];
    uint8_t first_root;          /* the first note of a bar is the root */
    uint8_t strong;              /* a note on a beat is the root, the fifth or the octave */
    uint8_t octpair, pair;       /* a note at most `pair` 16ths after its beat answers the beat's root with the octave (and its octave with the root) */
    uint8_t same;                /* a note off the beat repeats its beat's tone */
    uint8_t turn;                /* a note in the last 8th of the pattern leads home (seventh, fifth, second, fourth) */
    uint8_t hold, hold_max, gap; /* a note with room is held; steps at most (0: to the next); rests kept before the next: 0..gap */
    uint8_t roll;                /* a note rolls (2, 3 or 4 a step): the wobble */
} th_line_t;
static const th_line_t TH_LINES[] = {
    {T, SQ_FUNC_RUMBLE, {100, 4, 3, 3, 2, 0, 2, 0}, 220, 0, 0, 0, 0, 30, 0, 0, 0, 0},
    {T, SQ_FUNC_BASS, {70, 8, 14, 3, 3, 2, 0, 0}, 235, 200, 90, 3, 60, 110, 0, 0, 0, 0},
    {H, SQ_FUNC_BASS, {50, 13, 22, 6, 6, 3, 0, 0}, 215, 190, 110, 4, 30, 120, 60, 1, 0, 0},
    {D, SQ_FUNC_SUB, {60, 14, 8, 9, 6, 3, 0, 0}, 245, 150, 0, 0, 40, 80, 255, 0, 3, 0},
    {D, SQ_FUNC_BASS, {66, 12, 3, 10, 6, 3, 0, 0}, 235, 170, 0, 0, 60, 60, 90, 3, 0, 0},
    {S, SQ_FUNC_SUB, {55, 12, 15, 6, 7, 0, 5, 0}, 250, 170, 40, 6, 30, 90, 255, 0, 2, 0},
    {S, SQ_FUNC_BASS, {68, 8, 12, 4, 2, 6, 0, 0}, 240, 190, 60, 6, 70, 40, 0, 0, 0, 120},
    {F, SQ_FUNC_BASS, {40, 15, 12, 10, 8, 6, 5, 4}, 180, 140, 40, 2, 30, 70, 80, 2, 0, 0},
    TH_DATA_LINES
};
/* a motif: the ladder it moves on, the shape it has over a bar, how far a note strays from it. (The register and the
 * weights of the chord's tones, of the three written by hand too, are the library's own: tools/theory/gen_rules.py.) */
typedef struct {
    uint8_t style, func;
    uint8_t penta;               /* the chance its ladder is the key's pentatonic (else all seven notes) */
    uint8_t shape[4];            /* the weights of: it falls, it rises, an arch, two notes in turn */
    uint8_t span_lo, span_hi;    /* the rungs of the ladder a bar covers */
    uint8_t rep;                 /* a note repeats its beat's (the shape moves by beats there) */
    uint8_t jit, leap;           /* a note is a rung off its place / two */
    uint8_t chord, off;          /* a note on a beat is a tone of the chord / a note off the beat is */
    uint8_t cad;                 /* the last note is home, and bar 2 ends open */
    uint8_t hold, hold_max, gap;
    uint8_t cw[3];               /* the tones of the chord it stands on and comes back to: the weights of the root, the fifth,
                                  * the third (0: not that one) */
    uint8_t hi;                  /* the highest note, in semitones above the root (7..15) */
} th_lead_t;
static const th_lead_t TH_LEADS[] = {
    {H, SQ_FUNC_VOX, 230, {25, 10, 20, 45}, 1, 2, 110, 50, 10, 220, 170, 150, 60, 2, 0, {4, 6, 2}, 12},
    {D, SQ_FUNC_LEAD, 190, {40, 15, 30, 15}, 2, 4, 60, 60, 20, 200, 50, 190, 170, 0, 1, {6, 5, 4}, 12},
    {S, SQ_FUNC_LEAD, 180, {45, 10, 25, 20}, 2, 4, 90, 50, 15, 200, 70, 200, 200, 0, 0, {6, 6, 5}, 12},
    {F, SQ_FUNC_LEAD, 110, {25, 25, 30, 20}, 2, 5, 50, 70, 30, 160, 40, 130, 80, 2, 1, {3, 2, 1}, 15},
    TH_DATA_LEADS
};
/* chords: the weights of a triad, a seventh chord, a sus4, a power chord; `same`: every chord of the pattern is the
 * first one's kind. No part writes a sus4: the HARMONY moves a written chord by the steps of the key, and on one step of
 * every key the fourth is not a perfect one. The suspended chords are colours of the progression, which knows the step. */
typedef struct { uint8_t style, func; uint8_t kind[4]; uint8_t same, hold, hold_max, gap; } th_chord_t;
static const th_chord_t TH_CHORDS[] = {
    {T, SQ_FUNC_STAB, {60, 30, 0, 10}, 230, 0, 0, 0},
    {T, SQ_FUNC_PAD, {45, 55, 0, 0}, 200, 255, 0, 2},
    {H, SQ_FUNC_PIANO, {10, 90, 0, 0}, 215, 150, 1, 0},
    {H, SQ_FUNC_PAD, {25, 75, 0, 0}, 200, 255, 0, 2},
    {D, SQ_FUNC_PAD, {35, 65, 0, 0}, 190, 255, 0, 2},
    {S, SQ_FUNC_PAD, {60, 40, 0, 0}, 220, 255, 0, 1},
    {F, SQ_FUNC_CHORD, {50, 40, 0, 10}, 150, 120, 2, 1},
    TH_DATA_CHORDS
};
/* the chords of a style: how many, how long, where the roots go */
typedef struct {
    uint8_t n_w[4];              /* 1, 2, 3, 4 chords */
    uint8_t bars_w[4];           /* a chord lasts 1, 2, 4, 8 bars */
    uint8_t move_w[6];           /* the next root 1..6 steps of the scale up (3: a fourth up, 5: a third down, 6: a step down) */
    uint8_t first;               /* % it starts at home */
    uint8_t last_w[7];           /* the last chord, by its step of the scale */
    uint8_t col_w[SQ_HCS];       /* a triad, a 7th, a 9th, sus4, sus2, a 6th */
    uint8_t col_same;            /* % one colour for every chord */
    uint8_t scale_w[6];          /* MINOR DORIAN PHRYGIAN MAJOR MIXOLYDIAN HARMONIC MINOR (all 0: the genre's own three) */
    uint8_t push_w[3];           /* a chord comes in on the bar, a 16th before it, an 8th before it */
} th_prog_t;
static const th_prog_t TH_PROGS[SQ_TH_STYLES] = {
    /* TECHNO: one chord, or two; slow; the flat second (phrygian), the flat sixth, the flat seventh; triads */
    [T] = {{40, 40, 5, 15}, {5, 25, 45, 25}, {30, 5, 10, 8, 30, 35}, 95, {0, 25, 5, 10, 10, 25, 25}, {60, 25, 0, 5, 10, 0}, 80, {45, 15, 40, 0, 0, 0}, {95, 5, 0}},
    /* HOUSE: two or four chords, a bar or two each; a fourth up, a third or a step down; sevenths and ninths; the
     * chords come in early */
    [H] = {{5, 35, 10, 50}, {45, 45, 10, 0}, {8, 14, 30, 12, 22, 22}, 85, {0, 3, 10, 22, 25, 15, 25}, {8, 50, 27, 8, 3, 4}, 60, {45, 35, 0, 12, 8, 0}, {50, 25, 25}},
    /* DRUM AND BASS: two or four chords, two bars each; down to the flat sixth and the flat seventh; sevenths */
    [D] = {{10, 40, 5, 45}, {5, 55, 35, 5}, {5, 18, 16, 10, 30, 25}, 90, {0, 3, 12, 18, 15, 25, 27}, {15, 45, 25, 3, 10, 2}, 55, {70, 15, 10, 0, 0, 5}, {85, 0, 15}},
    /* DUBSTEP: one chord, or two; long; the flat sixth, the flat second; triads */
    [S] = {{45, 40, 5, 10}, {5, 35, 45, 15}, {22, 6, 10, 8, 30, 28}, 97, {0, 20, 8, 10, 12, 25, 25}, {65, 20, 3, 2, 10, 0}, 80, {55, 0, 35, 0, 0, 10}, {100, 0, 0}},
    /* FREE: anything of the key */
    [F] = {{10, 30, 20, 40}, {30, 40, 25, 5}, {17, 17, 17, 17, 16, 16}, 70, {14, 14, 14, 14, 14, 15, 15}, {30, 25, 15, 10, 10, 10}, 30, {25, 15, 15, 25, 10, 10}, {70, 15, 15}},
    /* the other genres: their six progressions, counted */
    TH_DATA_PROGS
};
#undef T
#undef H
#undef D
#undef S
#undef F

/* ------------------------------------------------------------------ styles and genres */
uint8_t sq_th_style(uint8_t genre) { return (uint8_t)(genre < SQ_GENRES ? genre : 255u); }     /* a style is its genre */
uint8_t sq_th_genre(uint8_t style) { return (uint8_t)(style < SQ_GENRES ? style : 255u); }
const char *sq_th_name(uint8_t style) { return style < SQ_GENRES ? sq_genre_name(style) : "FREE"; }
/* the band: the genre's own. FREE: a band of the seven families and a motif. */
uint8_t sq_th_band(uint8_t style, uint8_t *funcs)
{
    static const uint8_t FREE_BAND[8] = {SQ_FUNC_KICK, SQ_FUNC_SNARE, SQ_FUNC_HAT, SQ_FUNC_PERC, SQ_FUNC_BASS, SQ_FUNC_CHORD, SQ_FUNC_ARP, SQ_FUNC_LEAD};
    uint8_t parts[SQ_PARTS_MAX], n, i, g = sq_th_genre(style);
    if (g == 255u) { for (i = 0; i < 8u; i++) funcs[i] = FREE_BAND[i]; return 8u; }
    n = sq_genre_band(g);
    sq_genre_parts(g, parts);
    for (i = 0; i < n; i++) funcs[i] = parts[i];
    return n;
}
uint8_t sq_th_scale(const sq_th_t *t)
{
    static const uint8_t SC[6] = {SQ_SC_MINOR, SQ_SC_DORIAN, SQ_SC_PHRYGIAN, SQ_SC_MAJOR, SQ_SC_MIXOLYDIAN, SQ_SC_HARM_MINOR};
    static const uint8_t OWN[3] = {50u, 30u, 20u};
    uint8_t st = (uint8_t)(t->style < SQ_TH_STYLES ? t->style : SQ_TH_FREE);
    const th_prog_t *p = &TH_PROGS[st];
    uint32_t u = th_u0(t, 0x7000u, 1u, 1u), i, any = 0u;
    for (i = 0; i < 6u; i++) any |= p->scale_w[i];
    if (!any) return sq_genre_scale(st, (uint8_t)th_pick(OWN, 3u, u));    /* a genre counted from the library: its own three scales */
    return SC[th_pick(p->scale_w, 6u, u)];
}
uint8_t sq_th_root(const sq_th_t *t)
{
    static const uint8_t R[8] = {0u, 2u, 4u, 5u, 7u, 9u, 10u, 3u};      /* C D E F G A Bb Eb */
    return R[th_u0(t, 0x7000u, 2u, 1u) & 7u];
}

/* ------------------------------------------------------------------ the bar a part is made in (0.26) */
/* Until 0.25 a part was made in bars of sixteen 16ths, four quarters - and the firmware re-barred it for another metre
 * (sq_rebar: a 7/8 was a 4/4 with a beat left out). 0.26 (sq_th_t.gen): the part is made IN the bar. Every step of the
 * bar stands for a 16th of a 4/4 bar (sq_metre_native: the bar's two halves are that bar's, the beats of a half the
 * first and its answer; the WAY an odd bar divides is the band's, by its seed): the rules of the style - what a 16th
 * weighs, what is always there, the classes of 16ths - are read at the 16th the step stands for, and every choice has
 * the name of the step's own place, so no two beats of the bar are copies of each other. A bar of two beats is half
 * a 4/4 bar (two of them make it: ONE two | THREE four), a bar of one a quarter. In 4/4 nothing changes: a step
 * stands for itself. */
typedef struct {
    uint8_t steps;               /* the bar in 16ths */
    uint8_t per;                 /* how many of them make the 4/4 bar they stand for: 1, 2, 4 */
    uint8_t a16[SQ_BAR_MAX];     /* a step of the bar -> the 16th it stands for (before its bar's share of the 4/4 bar) */
    uint8_t beat[SQ_BAR_MAX];    /* ... -> the step its beat begins on */
    uint32_t starts;             /* a bit a step that begins a beat */
} th_bar_t;
static uint8_t th_native(const sq_th_t *t)
{
    return (uint8_t)(t->gen && t->bar_steps >= SQ_BAR_MIN && t->bar_steps <= SQ_BAR_MAX &&
                     !(t->bar_steps == 16u && sq_metre_fix(16u, t->bar_beats) == SQ_BEATS_44));
}
static void th_ctx(const sq_th_t *t, th_bar_t *x)
{
    uint32_t s, b = 0u;
    if (!th_native(t)) {
        x->steps = 16u; x->per = 1u; x->starts = SQ_BEATS_44;
        for (s = 0; s < 16u; s++) { x->a16[s] = (uint8_t)s; x->beat[s] = (uint8_t)(s & ~3u); }
        return;
    }
    x->steps = t->bar_steps;
    x->per = sq_metre_native(t->bar_steps, t->bar_beats, (uint8_t)(th_u0(t, 0x7000u, 3u, 1u) & 1u), x->a16, &x->starts);
    for (s = 0; s < x->steps; s++) { if ((x->starts >> s) & 1u) b = s; x->beat[s] = (uint8_t)b; }
}
/* of step `at` of a pattern: the 16th of the 4/4 bar it stands for; which of those bars it is in; its place in that
 * bar (the name of its choices); its beat's place; whether it begins a beat; how far it is from its beat's start */
static uint32_t th_s16(const th_bar_t *x, uint32_t at) { return (uint32_t)x->a16[at % x->steps] + (16u / x->per) * ((at / x->steps) % x->per); }
static uint32_t th_ab(const th_bar_t *x, uint32_t at) { return (at / x->steps) / x->per; }
static uint32_t th_pos(const th_bar_t *x, uint32_t at) { return ((at / x->steps) % x->per) * x->steps + at % x->steps; }
static uint32_t th_bpos(const th_bar_t *x, uint32_t at) { return ((at / x->steps) % x->per) * x->steps + x->beat[at % x->steps]; }
static uint32_t th_onbeat(const th_bar_t *x, uint32_t at) { return (x->starts >> (at % x->steps)) & 1u; }
static uint32_t th_off(const th_bar_t *x, uint32_t at) { return at % x->steps - x->beat[at % x->steps]; }
/* the steps a part of `len` is made of: 16, 32 or 64 in 4/4; one, two, three or four bars of another metre */
static uint8_t th_len(const th_bar_t *x, uint8_t len)
{
    if (x->steps == 16u && x->per == 1u && x->starts == SQ_BEATS_44) return (uint8_t)(len == 32u || len == 64u ? len : 16u);
    if (len && len % x->steps == 0u && len / x->steps <= 4u && len <= SQ_STEPS) return len;
    return x->steps;
}

/* ------------------------------------------------------------------ the rhythm */
typedef struct { uint8_t lev[SQ_STEPS], rat[SQ_STEPS]; } th_grid_t;

static uint32_t th_nib(const uint8_t *w, uint32_t s) { return (s & 1u) ? (uint32_t)(w[s >> 1] & 15u) : (uint32_t)(w[s >> 1] >> 4); }

/* the rule of a part: one of the style's own for it (by their shares, the seed's choice: a variation keeps the
 * family), else the style's rule for the part's family, else FREE's */
static const th_rule_t *th_rule(const sq_th_t *t, uint8_t func)
{
    uint32_t pass, i;
    uint8_t fam = sq_func_family(func), st = t->style < SQ_TH_STYLES ? t->style : SQ_TH_FREE;
    for (pass = 0; pass < 3u; pass++) {
        uint8_t s = pass < 2u ? st : SQ_TH_FREE, f = pass == 0u ? func : fam;
        uint32_t total = 0u, x, acc = 0u;
        if (pass == 1u)                                  /* (a snare in a style that has a clap: the clap's rules) */
            for (i = 0; i < TH_N_RULES; i++) if (TH_RULES[i].style == s && sq_func_family(TH_RULES[i].func) == fam) { f = TH_RULES[i].func; break; }
        for (i = 0; i < TH_N_RULES; i++) if (TH_RULES[i].style == s && TH_RULES[i].func == f) total += TH_RULES[i].pick ? TH_RULES[i].pick : 1u;
        if (!total) continue;
        x = th_u0(t, func, 0xA17u, 1u) * total / 256u;
        for (i = 0; i < TH_N_RULES; i++) if (TH_RULES[i].style == s && TH_RULES[i].func == f) {
            acc += TH_RULES[i].pick ? TH_RULES[i].pick : 1u;
            if (x < acc) return &TH_RULES[i];
        }
    }
    return &TH_RULES[TH_N_RULES - 1u];
}

static void th_rhythm(const sq_th_t *t, const th_bar_t *x, uint8_t func, uint32_t n, th_grid_t *g);

/* the rule of the bar a 16th of the pattern is in: bars 2 and 4 have their own when the family answers itself */
static const th_rule_t *th_bar(const th_rule_t *q, const th_bar_t *x, uint32_t at) { return (th_ab(x, at) & 1u) && (q->kick & TH_K_TWO) ? q + 1 : q; }
/* the weight of a hit on 16th `at` of the pattern (a sub leans on the kicks of its band). 0.25: and the part it answers
 * (mate, n 16ths of it): on the 16th, or the two, right after an attack of that one - where it has just spoken and is
 * silent now - the weight is three more (never an accent it was not): the answer comes after the call */
static uint32_t th_weight(const th_rule_t *q, const th_bar_t *x, const th_grid_t *kick, const uint8_t *mate, uint32_t n, uint32_t at)
{
    uint32_t w = th_nib(th_bar(q, x, at)->w, th_s16(x, at));
    if ((q->kick & 15u) == TH_K_WITH && w && kick->lev[at] >= TH_X) w = w + 5u > 15u ? 15u : w + 5u;
    if (mate && w && w < 11u && mate[at] < TH_O && (mate[(at + n - 1u) % n] >= TH_O || mate[(at + n - 2u) % n] >= TH_O)) w = w + 3u > 11u ? 11u : w + 3u;
    return w;
}
/* the level of a hit of weight w on 16th `at`: its place's own in a rule counted from the library, else by its weight */
static uint32_t th_level(const th_rule_t *q, const th_bar_t *x, uint32_t w, uint32_t at)
{
    static const uint8_t LV[4] = {TH_X, TH_A, TH_O, TH_G};
    if (q->kick & TH_K_LV) return LV[(th_bar(q, x, at)->lv >> (2u * th_s16(x, at))) & 3u];
    return w >= 12u ? TH_A : w > q->soft ? TH_X : q->soft_lev;
}
/* the 16ths of the bar of `at` that are always there at this energy */
static uint16_t th_fix(const sq_th_t *t, const th_rule_t *q, const th_bar_t *x, uint32_t at)
{
    const th_rule_t *qb = th_bar(q, x, at);
    return (uint16_t)(qb->fixA | qb->fixx | (t->energy >= TH_DATA_MID_E ? qb->mid : 0u));
}
/* the name of the choices on 16th s of bar b: bars 1 and 3 are the same bar; bars 2 and 4 make `bar2` % of them again
 * (0.26: b the 4/4 bar the step stands in, s its place there - th_ab, th_pos: in 4/4 the bar and the 16th as ever) */
static uint32_t th_key(const sq_th_t *t, const th_rule_t *q, uint32_t part, uint32_t b, uint32_t s)
{
    return ((b & 1u) && th_u(t, part, 0x400u + s, 9u) * 100u < (uint32_t)q->bar2 * 256u) ? 0x800u + s : s;
}
static uint32_t th_keyat(const sq_th_t *t, const th_rule_t *q, const th_bar_t *x, uint32_t part, uint32_t at)
{
    return th_key(t, q, part, th_ab(x, at), th_pos(x, at));
}

/* 0.25: 16th `at` is one the part leaves to the part it answers: that one attacks there, and this part's number for the
 * place says so, two times in three (a number of the place: the same at every energy) */
static uint32_t th_shy(const sq_th_t *t, uint32_t part, const uint8_t *mate, uint32_t at, uint32_t key)
{
    return mate && mate[at] >= TH_O && th_u(t, part, 0x500u + key, 8u) < 170u;
}
/* 0.26 A PART KEEPS ITS BACKBONE IN ANY BAR. A bar of three beats stands for three of the four beats of a 4/4 bar, a
 * pattern of one bar of two beats for half of it: the 16th a part is BUILT on - the snare of dubstep on three, the clap
 * of hard techno - may not be among the pattern's steps at all. Then the step that stands for the nearest 16th with the
 * same place in its beat (of two as near: the later one) carries it: the snare on three is on the bar's last beat.
 * Which 16th: one the part always plays (its accent first); a part with none: its heaviest, when no step of the pattern
 * could ever be more than a ghost (a part is never empty). `present`: the 16ths the pattern's steps stand for in the
 * bars of this rule, less the ones the rule never plays. Returns the 16th that carries it (lev: at what level), or
 * 255: nothing to move - always so in 4/4, where every 16th is there. */
static uint32_t th_backbone(const th_rule_t *q, const th_rule_t *qb, uint32_t present, uint32_t cyc_on, uint32_t *lev)
{
    static const uint8_t LV[4] = {TH_X, TH_A, TH_O, TH_G};
    uint32_t F = (uint32_t)(qb->fixA | qb->fixx), f = 255u, s, best = 255u, bk = 0xFFFFu, lv = 0u;
    if (!present) return 255u;
    if (F) {
        if (F & present) return 255u;
        for (s = 0; s < 16u && f == 255u; s++) if ((qb->fixA >> s) & 1u) f = s;
        for (s = 0; s < 16u && f == 255u; s++) if ((qb->fixx >> s) & 1u) f = s;
        lv = (q->kick & TH_K_LV) ? LV[(qb->lv >> (2u * f)) & 3u] : ((qb->fixA >> f) & 1u) ? TH_A : TH_X;
    } else {
        uint32_t wbest = 0u, c;
        for (c = 0; c < 4u; c++)                         /* (a part of classes: a class that is among the steps) */
            if (q->cls[c] && 1u + ((q->cls_lev >> (2u * c)) & 3u) >= TH_O && (present & (0x1111u << c))) return 255u;
        if (cyc_on) return 255u;                         /* (a cycle that turns: it is the part) */
        for (s = 0; s < 16u; s++) {
            uint32_t w = th_nib(qb->w, s), l = !w ? 0u : (q->kick & TH_K_LV) ? LV[(qb->lv >> (2u * s)) & 3u] : w >= 12u ? TH_A : w > q->soft ? TH_X : q->soft_lev;
            if (l < TH_O) continue;
            if ((present >> s) & 1u) return 255u;        /* (a step of the pattern can be a hit: nothing to move) */
            if (w > wbest) { wbest = w; f = s; lv = l; }
        }
        if (f == 255u) return 255u;
    }
    for (s = 0; s < 16u; s++) {
        uint32_t d, key;
        if (!((present >> s) & 1u)) continue;
        d = s > f ? s - f : f - s;
        key = ((s & 3u) != (f & 3u) ? 64u : 0u) + d * 2u - (s > f ? 1u : 0u);
        if (key < bk) { bk = key; best = s; }
    }
    *lev = lv;
    return best;
}
/* 0.26, a part whose notes STAND APART, in a bar of its own. Of two hits on steps next to each other the one that came
 * in later goes - and a hit that is always there never does. In 4/4 the style's rule keeps the two from ever meeting:
 * it gives no weight to a 16th beside one that is always there (at any energy). In another bar steps are neighbours
 * that were not - a long beat says its end twice, a bar of three beats goes from beat two to beat four - and a hit
 * would be there until its neighbour comes in at a higher energy, and then go. So there the step BESIDE one that is
 * always there (at some energy; or that carries the part's backbone) is left empty at every energy. */
static uint32_t th_core_at(const th_rule_t *q, const th_bar_t *x, uint32_t at, const uint32_t *bone, uint32_t two)
{
    const th_rule_t *qb = th_bar(q, x, at);
    uint32_t s16 = th_s16(x, at);
    return (((uint32_t)(qb->fixA | qb->fixx | qb->mid) >> s16) & 1u) || bone[two & th_ab(x, at)] == s16;
}
static uint32_t th_beside(const sq_th_t *t, const th_rule_t *q, const th_bar_t *x, uint32_t n, uint32_t at, const uint32_t *bone, uint32_t two)
{
    if (!(q->kick & TH_K_APART) || !th_native(t) || th_core_at(q, x, at, bone, two)) return 0u;
    return (at && th_core_at(q, x, at - 1u, bone, two)) || (at + 1u < n && th_core_at(q, x, at + 1u, bone, two));
}
static void th_rhythm_rule(const sq_th_t *t, const th_bar_t *x, const th_rule_t *q, uint8_t func, uint32_t n, th_grid_t *g)
{
    uint32_t part = func, s, c, dens = th_en(t, q->d_lo, q->d_hi), share = th_en(t, q->cls_e0, 255u);
    uint32_t cyc_n = q->cyc & 15u, cyc_on = 0u, cyc_ph = 0u, cyc_per = 1u, link = th_ub(t, part, 0xC0u, 1u), L, at;
    uint32_t i, bars = n / x->steps, any = 0u, some = 0u, best_c = 4u, best = 0xFFFFu, avoid = (q->kick & 15u) == TH_K_AVOID;
    uint16_t rk[SQ_STEPS];                               /* how late a hit comes in as the energy rises: its number against its
                                                          * weight (0: it is always there; 0xFFFF: no hit can be here) */
    uint8_t con[4], opc[4] = {1u, 1u, 1u, 1u};
    th_grid_t kick;
    const uint8_t *mate = sq_th_mate_family(func) != 255u ? t->mate : 0;   /* 0.25: the part this one answers (a part that answers nobody: nobody) */
    uint32_t pres[2] = {0u, 0u}, bone[2] = {255u, 255u}, bone_lv[2] = {0u, 0u}, two = (q->kick & TH_K_TWO) ? 1u : 0u;   /* 0.26: th_backbone */
    for (i = 0; i < SQ_STEPS; i++) { g->lev[i] = 0u; g->rat[i] = 0u; rk[i] = 0xFFFFu; kick.lev[i] = 0u; }
    if (cyc_n) {                                         /* (the cycle is the part: the rest thins out; a low energy: every other hit of it) */
        cyc_on = th_ub(t, part, 0xCCu, 1u) < (uint32_t)(q->cyc >> 4) * 17u;
        cyc_ph = th_ub(t, part, 0xCDu, 1u) % cyc_n;
        cyc_per = t->energy < 40u ? cyc_n * 2u : cyc_n;
        if (cyc_on) dens /= 2u;
    }
    for (i = 0; i < n; i++) pres[two & th_ab(x, i)] |= TB(th_s16(x, i));
    if (pres[0] != 0xFFFFu) bone[0] = th_backbone(q, q, pres[0] & ~(uint32_t)q->never, cyc_on, &bone_lv[0]);
    if (two && pres[1] != 0xFFFFu) bone[1] = th_backbone(q, q + 1, pres[1] & ~(uint32_t)(q + 1)->never, cyc_on, &bone_lv[1]);
    if (q->kick & 15u) {                                 /* the kick that plays with it, else the seed's own */
        if (t->kick) for (i = 0; i < n; i++) kick.lev[i] = t->kick[i];
        else {                                           /* (a part that leans on the kicks: on the ones that are there at every
                                                          * energy - what it leans on must not move as the energy rises; 0.25: the
                                                          * kick answers nobody, whoever this part answers) */
            sq_th_t t0 = *t;
            t0.mate = 0; t0.mate_nt = 0;
            if ((q->kick & 15u) == TH_K_WITH) t0.energy = 0u;
            th_rhythm(&t0, x, SQ_FUNC_KICK, n, &kick);
        }
    }
    if (mate) {                                          /* 0.25: the places this part can play on and does not leave to the part
                                                          * it answers, class by class (whatever the energy). None at all: it
                                                          * takes no notice of the other - a part is never empty */
        uint32_t open = 0u;
        opc[0] = opc[1] = opc[2] = opc[3] = 0u;
        for (i = 0; i < n; i++) {
            const th_rule_t *qb = th_bar(q, x, i);
            uint32_t s16 = th_s16(x, i), core = ((uint32_t)(qb->fixA | qb->fixx) & TB(s16)) || bone[two & th_ab(x, i)] == s16;
            if ((qb->never & TB(s16)) || (avoid && kick.lev[i]) || th_beside(t, q, x, n, i, bone, two)) continue;
            if (!core && !th_nib(qb->w, s16) && !q->cls[s16 & 3u] && !cyc_n) continue;
            if (!core && th_shy(t, part, mate, i, th_keyat(t, q, x, part, i))) continue;
            open++; opc[s16 & 3u] = 1u;
        }
        if (!open) mate = 0;
    }
    for (c = 0; c < 4u; c++) {                           /* a class is there when its number, against its chance, is under the share */
        uint32_t cx = q->cls[c] ? (q->cls_link ? link : th_ub(t, part, 0xC1u + c, 1u)) * 255u / q->cls[c] : 0xFFFFu;
        con[c] = (uint8_t)(q->cls[c] == 255u || cx < share);
        if (cx < best && (!mate || opc[c]) && ((pres[0] | pres[1]) & (0x1111u << c))) { best = cx; best_c = c; }   /* (the one that comes in first as the energy rises - 0.25:
                                                                        *  of those with a place the part does not leave to the other) */
    }
    for (at = 0; at < n; at++) {
        {
            uint32_t key = th_keyat(t, q, x, part, at), w = th_weight(q, x, &kick, mate, n, at), lev = 0u, shy;
            const th_rule_t *qb = th_bar(q, x, at);
            uint32_t out;
            s = th_s16(x, at);
            out = (qb->never & TB(s)) || (avoid && kick.lev[at]) || th_beside(t, q, x, n, at, bone, two);
            c = s & 3u;
            if (w) {                                     /* a hit is there when its number, against its weight, is under the density */
                rk[at] = (uint16_t)(th_u(t, part, 0x200u + key, 3u) * 15u / w);
                if (rk[at] < dens) lev = th_level(q, x, w, at);
            }
            if (con[c] && th_u(t, part, 0x100u + key, 2u) >= q->hole && 1u + ((q->cls_lev >> (2u * c)) & 3u) >= lev) { lev = 1u + ((q->cls_lev >> (2u * c)) & 3u); rk[at] = 0u; }
            if (cyc_on && at % cyc_per == cyc_ph && lev < TH_X) { lev = TH_X; rk[at] = 0u; }
            /* 0.25 THE PARTS LISTEN: where the part it answers attacks, this one stays away two times in three (by its
             * place: the same at every energy) - what the part ALWAYS plays, below, is there whatever (of a rule
             * counted from the library: what every variation plays, not what half of them do) */
            shy = th_shy(t, part, mate, at, key);
            if (shy) { lev = 0u; rk[at] = 0xFFFFu; }
            if (q->kick & TH_K_LV) {                     /* (counted from the library: what is always there has its place's level) */
                if ((shy ? (uint16_t)(qb->fixA | qb->fixx) : th_fix(t, q, x, at)) & TB(s)) { lev = th_level(q, x, 15u, at); rk[at] = 0u; }
            } else {
                if ((q->fixx & TB(s)) && lev < TH_X) { lev = TH_X; rk[at] = 0u; }
                if (q->fixA & TB(s)) { lev = TH_A; rk[at] = 0u; }
            }
            if (bone[two & th_ab(x, at)] == s && lev < bone_lv[two & th_ab(x, at)]) { lev = bone_lv[two & th_ab(x, at)]; rk[at] = 0u; }   /* 0.26: its backbone, carried here */
            if (out) { lev = 0u; rk[at] = 0xFFFFu; }
            if (lev && (qb->rollm & TB(s)) && th_u(t, part, 0x300u + key, 6u) < ((uint32_t)(qb->roll & 63u) << 2))
                g->rat[at] = (uint8_t)((qb->roll >> 6) + 1u);    /* (by its place: the same roll at every energy) */
            g->lev[at] = (uint8_t)lev;
            if (lev) some = 1u;
            if (lev >= TH_O) any = 1u;
        }
    }
    if (!any) {                                          /* nothing, or nothing but ghosts: a part is never empty. The hit that
                                                          * would come in first as the energy rises; a part of classes: the class
                                                          * that would; a part that is all ghosts (the percussion of drum and
                                                          * bass): its first ghost */
        uint32_t near = 0xFFFFu, soft = 0xFFFFu, pass, got = 0u;
        for (i = 0; i < n; i++) {
            uint32_t w = th_weight(q, x, &kick, mate, n, i);
            if (rk[i] == 0xFFFFu || !w) continue;
            if (th_level(q, x, w, i) >= TH_O) { if (rk[i] < near) near = rk[i]; }
            else if (rk[i] < soft) soft = rk[i];
        }
        for (pass = 0; pass < 2u && !got; pass++)        /* (a class whose every hit was left out: the class whole) */
            for (i = 0; i < n; i++) {
                uint32_t w = th_weight(q, x, &kick, mate, n, i), s16 = th_s16(x, i);
                if ((th_bar(q, x, i)->never & TB(s16)) || (avoid && kick.lev[i]) || th_beside(t, q, x, n, i, bone, two) || th_shy(t, part, mate, i, th_keyat(t, q, x, part, i))) continue;
                if (near != 0xFFFFu) { if (w && rk[i] == near && th_level(q, x, w, i) >= TH_O) { g->lev[i] = (uint8_t)th_level(q, x, w, i); got = 1u; } }
                else if (best_c < 4u) {
                    if ((s16 & 3u) == best_c && (pass || th_u(t, part, 0x100u + th_keyat(t, q, x, part, i), 2u) >= q->hole)) {
                        g->lev[i] = (uint8_t)(1u + ((q->cls_lev >> (2u * best_c)) & 3u)); rk[i] = 0u; got = 1u;
                    }
                } else if (!some && w && rk[i] == soft) { g->lev[i] = (uint8_t)th_level(q, x, w, i); got = 1u; }
                else got = 1u;                           /* (ghosts, and nothing to add: it stays as it is) */
            }
    }
    if (t->energy && th_native(t)) {
        /* 0.26, a bar of its own: what the part has at NO energy it has at every energy. In 4/4 a style's rules see to
         * it (what is always there has every 16th to stand on); in another bar a 16th may have no step, a kick may sit
         * where the part's ground was, and the one hit that kept the part from being empty would go again when the
         * next ones come in. So the part of energy 0 is made first, and stays under this one. */
        sq_th_t t0 = *t;
        th_grid_t g0;
        t0.energy = 0u;
        th_rhythm_rule(&t0, x, q, func, n, &g0);
        for (i = 0; i < n; i++) {
            if (!g0.lev[i] || g->lev[i] || (th_bar(q, x, i)->never & TB(th_s16(x, i))) || (avoid && kick.lev[i]) || th_beside(t, q, x, n, i, bone, two)) continue;
            g->lev[i] = g0.lev[i]; g->rat[i] = g0.rat[i]; rk[i] = 0u;
        }
    }
    if (q->kick & TH_K_APART)                            /* no two on 16ths next to each other: the one that came in later goes */
        for (i = 1u; i < n; i++) {
            uint32_t fa = (th_fix(t, q, x, i - 1u) & TB(th_s16(x, i - 1u))) || bone[two & th_ab(x, i - 1u)] == th_s16(x, i - 1u);
            uint32_t fb = (th_fix(t, q, x, i) & TB(th_s16(x, i))) || bone[two & th_ab(x, i)] == th_s16(x, i);
            if (!g->lev[i] || !g->lev[i - 1u] || (fa && fb)) continue;
            if (fb || (!fa && rk[i] < rk[i - 1u])) g->lev[i - 1u] = 0u; else g->lev[i] = 0u;
        }
    if (bars < 2u || n < 16u) return;                    /* (a pattern shorter than sixteen 16ths has no room for one) */
    L = n - 16u;                                         /* the last bar: the style's way into the one - on its last four 16ths
                                                          * (L + 12 .. L + 15; in 4/4 L is the last bar's first step, as ever) */
    switch (q->fill) {
    case TH_F_PICK:                                         /* a kick: a pick-up, a roll of it when there is one */
        if (t->energy >= 25u) {
            if (g->lev[L + 15u]) g->rat[L + 15u] = 2u; else g->lev[L + 15u] = TH_X;
            if (t->energy >= 75u && !g->lev[L + 14u]) g->lev[L + 14u] = TH_O;
        }
        break;
    case TH_F_ROLL:                                         /* a clap: a ghost, a hit, an accent that rolls */
        if (!g->lev[L + 13u]) g->lev[L + 13u] = TH_G;
        if (t->energy >= 35u && g->lev[L + 14u] < TH_X) g->lev[L + 14u] = TH_X;
        g->lev[L + 15u] = t->energy >= 35u ? TH_A : TH_G;
        if (t->energy >= 70u) g->rat[L + 15u] = 2u;
        break;
    case TH_F_LATE:                                         /* the last snare an 8th late, or two quick ones after it */
        if (th_u(t, part, 0xF1u, 4u) < 150u) { g->lev[L + 12u] = TH_G; g->lev[L + 13u] = 0u; g->lev[L + 14u] = TH_A; if (!g->lev[L + 15u]) g->lev[L + 15u] = TH_G; }
        else { if (!g->lev[L + 13u]) g->lev[L + 13u] = TH_G; g->lev[L + 14u] = TH_X; g->lev[L + 15u] = TH_X; }
        break;
    case TH_F_TRIP:                                         /* two 16ths, or a roll in three, before the one */
        if (t->energy < 25u) break;
        if (th_u(t, part, 0xF1u, 4u) < 150u) { if (g->lev[L + 14u] < TH_X) g->lev[L + 14u] = TH_X; if (g->lev[L + 15u] < TH_X) g->lev[L + 15u] = TH_X; }
        else { if (g->lev[L + 15u] < TH_X) g->lev[L + 15u] = TH_X; g->rat[L + 15u] = 3u; }
        break;
    case TH_F_HAT:                                          /* the hats close the bar */
        if (t->energy < 30u) break;
        if (!g->lev[L + 14u]) g->lev[L + 14u] = TH_X;
        if (!g->lev[L + 15u]) g->lev[L + 15u] = TH_X;
        if (t->energy >= 60u) g->rat[L + 15u] = 2u;
        break;
    case TH_F_BUSY:                                         /* the percussion fills the second half (of the 4/4 bar the last bar stands for) */
        for (at = n - x->steps; at < n; at++) {
            s = th_s16(x, at);
            if (s >= 8u && !g->lev[at] && th_nib(th_bar(q, x, at)->w, s) && th_u(t, part, 0xF00u + th_pos(x, at), 4u) < 40u + t->energy) g->lev[at] = (uint8_t)((s & 1u) ? TH_O : TH_X);
        }
        break;
    default: break;
    }
}
static void th_rhythm(const sq_th_t *t, const th_bar_t *x, uint8_t func, uint32_t n, th_grid_t *g)
{
    th_rhythm_rule(t, x, th_rule(t, func), func, n, g);
}

/* a crash: on the one of the phrase, and now and then a soft one that leads into the next */
static void th_crash(const sq_th_t *t, const th_bar_t *x, uint32_t n, th_grid_t *g)
{
    uint32_t i;
    for (i = 0; i < SQ_STEPS; i++) { g->lev[i] = 0u; g->rat[i] = 0u; }
    g->lev[0] = TH_X;
    if (n >= 2u * x->steps && n >= 6u && th_u(t, SQ_FUNC_CRASH, 1u, 1u) < 40u + t->energy)
        g->lev[n - ((th_u(t, SQ_FUNC_CRASH, 2u, 1u) & 1u) ? 2u : 6u)] = TH_O;   /* (an 8th, or three, before the end: 14 or 10 of the last bar in 4/4) */
}

static void th_text(const th_grid_t *g, uint32_t n, char *r)
{
    static const char C[5] = {'.', 'g', 'o', 'x', 'X'};
    uint32_t i;
    for (i = 0; i < n; i++) r[i] = !g->lev[i] ? '.' : g->rat[i] >= 2u ? (char)('0' + g->rat[i]) : C[g->lev[i] < 5u ? g->lev[i] : 3u];
    r[n] = 0;
}

/* the held notes: a hit with room after it lasts on ('-'), keeping 0..gap rests before the next */
static void th_holds(const sq_th_t *t, const th_bar_t *x, uint32_t part, uint32_t n, char *r, uint8_t hold, uint8_t hold_max, uint8_t gap)
{
    uint32_t i, j;
    if (!hold) return;
    for (i = 0; i < n; i++) {                            /* (by its place in the bar: the same in every bar, whatever is around it) */
        uint32_t next, room, len;
        if (r[i] == '.' || r[i] == '-') continue;
        for (next = i + 1u; next < n && r[next] == '.'; next++) { }
        room = next - i - 1u;
        if (gap) { uint32_t rest = th_u(t, part, 0x720u + th_pos(x, i), 7u) % ((uint32_t)gap + 1u); room = room > rest ? room - rest : 0u; }
        if (r[i] >= '2' && r[i] <= '4') room = 0u;      /* (a roll keeps its own length) */
        if (room && th_u(t, part, 0x700u + th_pos(x, i), 7u) < (uint32_t)hold + (hold == 255u ? 1u : 0u)) {
            len = hold_max && room > hold_max ? hold_max : room;
            for (j = 1u; j <= len; j++) r[i + j] = '-';
        }
    }
}

/* ------------------------------------------------------------------ the notes */
/* the semitones of step `d` of the key's scale above the root (its seven-note parent: a pentatonic counts in minor) */
static uint32_t th_semi(uint8_t scale, uint32_t d)
{
    uint16_t m = sq_scale_mask(sq_harm_scale(scale));
    uint32_t k = d % 7u, i, c = 0u;
    for (i = 0; i < 12u; i++) if (m & (1u << i)) { if (c == k) return i + 12u * (d / 7u); c++; }
    return 12u * (d / 7u);
}
static char th_hex(uint32_t v) { if (v > 15u) v = 15u; return (char)(v < 10u ? '0' + v : 'a' + (v - 10u)); }

static const void *th_find(const void *tab, uint32_t n, uint32_t size, const sq_th_t *t, uint8_t func, uint8_t fam_func)
{
    uint32_t pass, i;
    uint8_t st = t->style < SQ_TH_STYLES ? t->style : SQ_TH_FREE;
    for (pass = 0; pass < 2u; pass++) {
        uint8_t s = pass ? SQ_TH_FREE : st, f = pass ? fam_func : func;
        for (i = 0; i < n; i++) {
            const uint8_t *e = (const uint8_t *)tab + i * size;
            if (e[0] == s && e[1] == f) return e;
        }
        if (!pass && func != fam_func)                   /* (the style's own rule for the family, before FREE's) */
            for (i = 0; i < n; i++) {
                const uint8_t *e = (const uint8_t *)tab + i * size;
                if (e[0] == s && e[1] == fam_func) return e;
            }
    }
    return tab;
}

/* a line: a tone of the chord for each note, by its PLACE in the bar - a note that the energy adds or takes away leaves
 * the others what they were. Each beat has its tone (the one: the root; a beat: mostly the root, the fifth or the
 * octave); a note off the beat answers its beat's tone (the octave of a root, the root of an octave), or repeats it,
 * or is its own. The same in bars 1 and 3; bars 2 and 4 make a quarter of the choices again. */
static uint32_t th_line_tone(const sq_th_t *t, const th_bar_t *x, const th_line_t *m, uint32_t part, uint32_t at)
{
    uint32_t b = th_ab(x, at), s = th_pos(x, at), beat = th_bpos(x, at), kb = beat, k = s, base;   /* (in 4/4: the bar, the 16th, its beat's 16th) */
    if ((b & 1u) && th_u(t, part, 0x400u + beat, 9u) < 64u) kb = 0x800u + beat;
    if (th_s16(x, at) < 4u && th_u(t, part, 0x10u + kb, 1u) < m->first_root) base = 0u;             /* (the first beat of the bar) */
    else base = th_pick(m->tone, th_u(t, part, 0x40u + kb, 4u) < m->strong ? 3u : 8u, th_u(t, part, 0x50u + kb, 5u));
    if (th_onbeat(x, at)) return base;
    if ((b & 1u) && th_u(t, part, 0x400u + s, 9u) < 64u) k = 0x800u + s;
    if ((base == 0u || base == 2u) && th_off(x, at) <= m->pair && th_u(t, part, 0x20u + k, 2u) < m->octpair) return base == 0u ? 2u : 0u;
    if (th_u(t, part, 0x30u + k, 3u) < m->same) return base;
    return th_pick(m->tone, 8u, th_u(t, part, 0x50u + k, 5u));
}
/* 0.26 THE ANSWER HAS NOTES. Until 0.25 a part answered another by its rhythm alone: it came after the call, with notes
 * of its own. Now (sq_th_t.gen, mate_nt) a line that answers a tune - the bass under the lead - takes the tune's own
 * notes: OFF the beat (on a beat a bass is the ground: its own tone stays), where the tune has no attack and has just
 * played, the line plays the note the tune had `canon` 16ths before (an 8th or a beat: the band's choice) - failing
 * that its last note within a beat. How readily depends on the STYLE's own line: the more its bass uses that note of
 * the chord (the weight of the third, the seventh, the fourth ... in its rule), the more often it takes it - seven
 * times in ten at most, never a note its style never plays (a bass that is all roots stays all roots), never the
 * major seventh (a line plays the sixth for it). By the place: the same at every energy. So a melodic bass picks up
 * the end of the lead's phrase, an octave or two under it. The turn at the pattern's end leads home as ever.
 * (The other part is heard as it is at half the energy: a tune has its notes by their place, so those are the notes it
 * plays at any energy; an arpeggio turns the chord's notes in order, so under one the line takes notes of the chord the
 * arpeggio is turning - at half the energy, the very ones.)
 * Returns the note, semitones above the root (0..11), or 255: no answer here. */
static uint32_t th_answer_note(const sq_th_t *t, const th_bar_t *x, const th_line_t *m, uint32_t part, uint32_t n, uint32_t at)
{
    static const uint8_t DEG[8] = {0u, 4u, 7u, 2u, 6u, 3u, 1u, 5u};
    const uint8_t *mate = t->mate, *mn = t->mate_nt;
    uint32_t canon = 2u + 2u * (th_ub(t, part, 0x90u, 9u) & 1u), k, src = n, pc, w = 0u, total = 0u, chance;
    if (!t->gen || !mate || !mn || mate[at] >= TH_O || th_onbeat(x, at)) return 255u;
    if (canon < n && mate[(at + n - canon) % n] >= TH_O && mn[(at + n - canon) % n] < 16u) src = (at + n - canon) % n;
    for (k = 1u; k <= 4u && k < n && src == n; k++) if (mate[(at + n - k) % n] >= TH_O && mn[(at + n - k) % n] < 16u) src = (at + n - k) % n;
    if (src == n) return 255u;
    pc = (uint32_t)mn[src] % 12u;
    if (pc == 11u) return 255u;
    for (k = 0; k < 8u; k++) {                           /* how much the style's own line uses that note */
        total += m->tone[k];
        if ((DEG[k] == 7u ? 0u : th_semi(t->scale, DEG[k]) % 12u) == pc) w += m->tone[k];
    }
    chance = total ? w * 1500u / total : 0u;
    if (chance > 180u) chance = 180u;
    if (th_u(t, part, 0x98u + th_pos(x, at), 9u) >= chance) return 255u;
    return pc;
}
static void th_line(const sq_th_t *t, const th_bar_t *x, uint8_t func, uint32_t n, char *r, char *nt)
{
    static const uint8_t DEG[8] = {0u, 4u, 7u, 2u, 6u, 3u, 1u, 5u};      /* root fifth octave third seventh fourth second sixth */
    const th_line_t *m = (const th_line_t *)th_find(TH_LINES, sizeof TH_LINES / sizeof TH_LINES[0], sizeof TH_LINES[0], t, func, SQ_FUNC_BASS);
    uint32_t part = 0x100u + func, i, answers = sq_th_mate_family(func) != 255u;
    for (i = 0; i < n; i++) nt[i] = '.';
    nt[n] = 0;
    for (i = 0; i < n; i++) {
        uint32_t s = th_pos(x, i), tone, semi, ans = 255u;
        if (r[i] == '.') continue;
        tone = th_line_tone(t, x, m, part, i);
        if (answers) ans = th_answer_note(t, x, m, part, n, i);         /* 0.26: the note of the part it answers */
        if (n >= 2u * x->steps && n >= 32u && i + 2u >= n && th_u(t, part, 0x60u, 6u) < m->turn) {   /* the last 8th of the pattern: a note that leads home */
            static const uint8_t TURN[4] = {4u, 1u, 6u, 5u};
            tone = TURN[th_u(t, part, 0x61u, 6u) & 3u];
            ans = 255u;
        }
        if (m->roll && th_u(t, part, 0x70u + s, 7u) < m->roll) {
            static const char ROLL[8] = {'2', '2', '2', '4', '4', '4', '3', '3'};
            uint32_t next = i + 1u;
            while (next < n && r[next] == '.') next++;
            if (next - i >= 2u) r[i] = ROLL[th_u(t, part, 0x71u + s, 7u) & 7u];   /* (a roll wants room after it) */
        }
        semi = DEG[tone] == 7u ? 12u : th_semi(t->scale, DEG[tone]);
        if (semi == 11u) semi = th_semi(t->scale, 5u);           /* (a major seventh under a chord: the sixth instead) */
        if (ans != 255u) semi = ans;
        nt[i] = th_hex(semi);
    }
    th_holds(t, x, part, n, r, m->hold, m->hold_max, m->gap);
}

/* chords: the kind of each (what the key makes of the root: a minor or a major triad, its seventh chord, a sus4, a power chord) */
static void th_chords(const sq_th_t *t, const th_bar_t *x, uint8_t func, uint32_t n, char *r, char *nt)
{
    const th_chord_t *m = (const th_chord_t *)th_find(TH_CHORDS, sizeof TH_CHORDS / sizeof TH_CHORDS[0], sizeof TH_CHORDS[0], t, func, SQ_FUNC_CHORD);
    uint32_t part = 0x200u + func, i, third = th_semi(t->scale, 2u), seventh = th_semi(t->scale, 6u);
    char kinds[4], first;
    kinds[0] = third == 4u ? 'M' : 'm';
    kinds[1] = third == 4u ? (seventh == 10u ? '7' : 'N') : 'n';
    kinds[2] = 's';
    kinds[3] = '5';
    first = kinds[th_pick(m->kind, 4u, th_ub(t, part, 0x10u, 1u))];
    for (i = 0; i < n; i++) {                            /* (by its place in the bar, as a line) */
        nt[i] = '.';
        if (r[i] == '.') continue;
        nt[i] = th_u(t, part, 0x20u + th_pos(x, i), 2u) < m->same ? first : kinds[th_pick(m->kind, 4u, th_u(t, part, 0x30u + th_pos(x, i), 3u))];
    }
    nt[n] = 0;
    th_holds(t, x, part, n, r, m->hold, m->hold_max, m->gap);
}

/* the ladder a motif moves on: all seven steps of the scale, or the five of the key's pentatonic (a minor key: the
 * root, the third, the fourth, the fifth, the seventh; a major one: the root, the second, the third, the fifth, the
 * sixth). Rung r -> the step of the scale it is. */
static uint32_t th_rung(uint8_t scale, uint32_t penta, uint32_t r)
{
    static const uint8_t PMIN[5] = {0u, 2u, 3u, 4u, 6u}, PMAJ[5] = {0u, 1u, 2u, 4u, 5u};
    if (!penta) return r;
    return (uint32_t)(th_semi(scale, 2u) == 4u ? PMAJ : PMIN)[r % 5u] + 7u * (r / 5u);
}
/* the rung is a tone of the chord: the motif's weight for the root, the fifth, the third (0: it is not one, or not one
 * this motif stands on) */
static uint32_t th_rung_chord(const th_lead_t *m, uint8_t scale, uint32_t penta, uint32_t r)
{
    uint32_t d = th_rung(scale, penta, r) % 7u;
    if (d == 0u) return r ? ((uint32_t)m->cw[0] + 1u) / 2u : m->cw[0];       /* (the root itself more than its octave) */
    return d == 4u ? m->cw[1] : d == 2u ? m->cw[2] : 0u;
}

/* a motif: a SHAPE over the bar (it falls, it rises, an arch, two notes in turn) on a ladder of notes, and each note a
 * little off its place: a neighbour, now and then a leap; a note on a beat is mostly a tone of the chord (the one
 * always), a note off the beat now and then. A note has its pitch by its PLACE in the bar (as a line: the energy adds notes, the others stay).
 * Four bars are a a' a b: bar 2 begins as bar 1, answers a rung higher or lower and ends open (on the fifth); bar 4 is
 * another shape and comes home (the root, or its octave). Two bars: a a', and a' comes home. */
static void th_lead(const sq_th_t *t, const th_bar_t *x, uint8_t func, uint32_t n, char *r, char *nt)
{
    const th_lead_t *m = (const th_lead_t *)th_find(TH_LEADS, sizeof TH_LEADS / sizeof TH_LEADS[0], sizeof TH_LEADS[0], t, func, SQ_FUNC_LEAD);
    uint32_t part = 0x300u + func, st = x->steps, bars = n / st, b, i, last = n, top = 0u, penta = th_ub(t, part, 1u, 1u) < m->penta;
    const uint8_t *mate = t->gen && sq_th_mate_family(func) != 255u && t->mate_nt ? t->mate : 0;   /* 0.26: the chords it answers */
    uint32_t home_hi = penta ? 5u : 7u, fifth = penta ? 3u : 4u;
    int32_t ans = (th_ub(t, part, 2u, 1u) & 1u) ? 1 : -1;
    while (top < 11u && th_semi(t->scale, th_rung(t->scale, penta, top + 1u)) <= (m->hi < 15u ? m->hi : 15u)) top++;   /* (the text holds 15 semitones above the root) */
    for (i = 0; i < n; i++) { nt[i] = '.'; if (r[i] != '.') last = i; }
    nt[n] = 0;
    for (b = 0; b < bars; b++) {
        uint32_t cls = bars >= 4u ? (b == 1u ? 1u : b == 3u ? 2u : 0u) : (b & 1u);
        uint32_t ck = cls == 2u ? 0x200u : 0u, s, bar_last = st, base, total = 0u, acc = 0u, xx, k, k0, k1;
        uint32_t shape = th_pick(m->shape, 4u, th_ub(t, part, 0x10u + ck, 2u));
        uint32_t span = (uint32_t)m->span_lo + th_ub(t, part, 0x11u + ck, 2u) % ((uint32_t)m->span_hi - m->span_lo + 1u);
        uint32_t pk = 4u + th_ub(t, part, 0x13u + ck, 2u) % 7u, per = 2u + th_ub(t, part, 0x14u + ck, 2u) % 3u;
        if (span > top) span = top;
        if (shape == 3u) span = (span + 1u) / 2u;        /* (two notes in turn: near each other) */
        k0 = shape == 0u ? span : 0u;                    /* it stands on a tone of the chord - the root likeliest, then the fifth,
                                                          * then the third: a shape that falls starts there, the others rise from it */
        k1 = shape == 0u ? top : top - span;
        for (k = k0; k <= k1; k++) total += th_rung_chord(m, t->scale, penta, k);
        xx = th_ub(t, part, 0x12u + ck, 2u) * total / 256u;
        base = k0;
        for (k = k0; k <= k1; k++) { acc += th_rung_chord(m, t->scale, penta, k); if (xx < acc) { base = k; break; } }
        if (shape == 0u) base -= span;
        for (s = 0; s < st; s++) if (r[b * st + s] != '.') bar_last = s;
        for (s = 0; s < st; s++) {
            uint32_t at = b * st + s, key, sp, c16, u, half2 = 2u * s >= st;   /* (half2: the second half of the bar) */
            int32_t rung;
            if (r[at] == '.') continue;
            key = cls == 1u && half2 ? 0x100u + s : ck + s;
            sp = th_u(t, part, 0x20u + key, 3u) < m->rep ? x->beat[s] : s;      /* (it repeats: the place of its beat) */
            if (st != 16u) sp = st > 1u ? sp * 15u / (st - 1u) : 0u;           /* (the shapes are drawn over sixteen places: a bar of another length is laid on them) */
            switch (shape) {
            case 0u: c16 = (base + span) * 16u - span * 16u * sp / 15u; break;
            case 1u: c16 = base * 16u + span * 16u * sp / 15u; break;
            case 2u: c16 = base * 16u + (sp <= pk ? span * 16u * sp / pk : span * 16u * (15u - sp) / (15u - pk)); break;
            default: c16 = base * 16u + ((((sp + pk) / per) & 1u) ? span * 16u : 0u); break;
            }
            rung = (int32_t)((c16 + 8u) / 16u);
            if (cls == 1u && half2) rung += ans;
            u = th_u(t, part, 0x30u + key, 4u);
            if (u < m->leap) rung += (th_u(t, part, 0x40u + key, 5u) & 1u) ? 2 : -2;
            else if (u < (uint32_t)m->leap + m->jit) rung += (th_u(t, part, 0x40u + key, 5u) & 1u) ? 1 : -1;
            if (rung < 0) rung = -rung;                  /* (off the ladder: back in from its end) */
            if (rung > (int32_t)top) rung = 2 * (int32_t)top - rung;
            if (rung < 0) rung = 0;
            if (s == 0u || th_u(t, part, 0x50u + key, 6u) < (((x->starts >> s) & 1u) ? m->chord : m->off)) {   /* the nearest tone of the chord;
                                                          * of two as near, the one the motif likes more, more often */
                int32_t d;
                for (d = 0; d <= (int32_t)top; d++) {
                    uint32_t dn = rung - d >= 0 ? th_rung_chord(m, t->scale, penta, (uint32_t)(rung - d)) : 0u;
                    uint32_t up = d && rung + d <= (int32_t)top ? th_rung_chord(m, t->scale, penta, (uint32_t)(rung + d)) : 0u;
                    if (!dn && !up) continue;
                    if (up && (!dn || th_u(t, part, 0x58u + key, 6u) * (dn + up) >= 256u * dn)) rung += d; else rung -= d;
                    break;
                }
            }
            /* 0.26 THE ANSWER HAS NOTES: a tune that answers the chords OUTLINES the chord that has just been struck - on
             * the 16ths right after it, where the chords are silent: its third, then its fifth, then its seventh (its
             * octave when the chord has none), six times in ten by the place. The rung of the ladder nearest to where
             * the tune was going; a ladder without that note (a pentatonic has no seventh in a major key): as it was */
            if (mate && mate[at] < TH_O && s != 0u && th_u(t, part, 0x70u + key, 8u) < 150u) {
                uint32_t d, want = 255u;
                for (d = 1u; d <= 3u && d <= at && want == 255u; d++)
                    if (mate[at - d] >= TH_O) want = d == 1u ? 2u : d == 2u ? 4u : (t->mate_nt[at - d] == 18u || t->mate_nt[at - d] == 19u || t->mate_nt[at - d] == 20u) ? 6u : 0u;
                if (want != 255u) {
                    int32_t dd, got = -1;
                    for (dd = 0; dd <= (int32_t)top && got < 0; dd++) {
                        if (rung - dd >= 0 && th_rung(t->scale, penta, (uint32_t)(rung - dd)) % 7u == want) got = rung - dd;
                        else if (rung + dd <= (int32_t)top && th_rung(t->scale, penta, (uint32_t)(rung + dd)) % 7u == want) got = rung + dd;
                    }
                    if (got >= 0) rung = got;
                }
            }
            if (th_u(t, part, 0x60u + cls, 7u) < m->cad) {
                if (at == last) rung = (rung * 2 > (int32_t)home_hi && home_hi <= top) ? (int32_t)home_hi : 0;   /* the end: home */
                else if (cls == 1u && s == bar_last && bars >= 4u && fifth <= top) rung = (int32_t)fifth;         /* bar 2 ends open */
            }
            nt[at] = th_hex(th_semi(t->scale, th_rung(t->scale, penta, (uint32_t)rung)));
        }
    }
    th_holds(t, x, part, n, r, m->hold, m->hold_max, m->gap);
}

/* an arpeggio: the tones of the chord (with its seventh, in the genres whose arpeggios have one) in an order; an accent
 * every third note in techno */
static void th_arp(const sq_th_t *t, const th_bar_t *x, uint32_t n, char *r, char *nt)
{
    static const uint8_t TONE[5] = {0u, 2u, 4u, 6u, 7u};
    uint32_t part = 0x400u + SQ_FUNC_ARP, i, ord = 0u, cnt = t->style == SQ_TH_TECHNO || (t->style < 32u && ((TH_DATA_ARP4 >> t->style) & 1u)) ? 4u : 5u;
    uint32_t mode = th_u(t, part, 1u, 1u) % 5u, start = th_u(t, part, 2u, 1u) % cnt, acc = t->style == SQ_TH_TECHNO ? 3u : 0u;
    for (i = 0; i < n; i++) {
        uint32_t k, per, d;
        nt[i] = '.';
        if (i % x->steps == 0u) ord = 0u;
        if (r[i] == '.') continue;
        switch (mode) {
        case 0:  k = (start + ord) % cnt; break;                                    /* up */
        case 1:  k = (start + cnt * 16u - ord) % cnt; break;                        /* down */
        case 2:  per = 2u * (cnt - 1u); k = (start + ord) % per; if (k >= cnt) k = per - k; break;   /* up and down */
        case 3:  k = (ord & 1u) ? cnt - 1u - ((ord >> 1) % (cnt - 1u)) : (ord >> 1) % (cnt - 1u); break;   /* low, high, low, high */
        default: k = th_u(t, part, 0x10u + ord, 3u) % cnt; break;                   /* its own order, the same every bar */
        }
        d = TONE[cnt == 4u && k == 3u ? 4u : k];                                    /* (four tones: the triad and the octave) */
        nt[i] = th_hex(d == 7u ? 12u : th_semi(t->scale, d));
        if (acc && ord % acc == 0u && r[i] == 'x') r[i] = 'X';
        ord++;
    }
    nt[n] = 0;
}

/* ------------------------------------------------------------------ a part */
uint8_t sq_th_mate_family(uint8_t func)
{
    uint8_t fam;
    if (func >= SQ_FUNCS || func == SQ_FUNC_PROG || func == SQ_FUNC_KIT || func == SQ_FUNC_CRASH) return 255u;
    fam = sq_func_family(func);
    if (fam == SQ_FUNC_ARP) return SQ_FUNC_CHORD;        /* an arpeggio, a lead, a voice answer the chords */
    if (fam == SQ_FUNC_PERC) return SQ_FUNC_SNARE;       /* the percussion fills what the snare leaves */
    if (fam == SQ_FUNC_BASS) return SQ_FUNC_ARP;         /* a bass makes room under the lead */
    return 255u;
}
void sq_th_levels(const sq_th_t *t, uint8_t func, uint8_t len, uint8_t *lev)
{
    th_grid_t g;
    th_bar_t x;
    uint32_t i;
    th_ctx(t, &x);
    len = th_len(&x, len);
    for (i = 0; i < SQ_STEPS; i++) g.lev[i] = 0u;
    if (func < SQ_FUNCS && func != SQ_FUNC_PROG && func != SQ_FUNC_KIT) {
        if (func == SQ_FUNC_CRASH) th_crash(t, &x, len, &g); else th_rhythm(t, &x, func, len, &g);
    }
    for (i = 0; i < SQ_STEPS; i++) lev[i] = g.lev[i % len];
}
uint8_t sq_th_steps(const sq_th_t *t, uint8_t bars)
{
    th_bar_t x;
    th_ctx(t, &x);
    if (bars < 1u) bars = 1u;
    if (bars == 3u || bars > 4u) bars = (uint8_t)(bars > 4u ? 4u : 2u);
    while (bars > 1u && (uint32_t)bars * x.steps > SQ_STEPS) bars = (uint8_t)(bars / 2u);
    return (uint8_t)(bars * x.steps);
}
static uint8_t th_part(const sq_th_t *t, uint8_t func, uint8_t len, char *r, char *nt, th_grid_t *g)
{
    th_bar_t x;
    uint8_t kind;
    if (func >= SQ_FUNCS || func == SQ_FUNC_PROG || func == SQ_FUNC_KIT) return 0u;
    th_ctx(t, &x);
    len = th_len(&x, len);
    kind = sq_func_kind(func);
    if (func == SQ_FUNC_CRASH) th_crash(t, &x, len, g);
    else th_rhythm(t, &x, func, len, g);
    th_text(g, len, r);
    nt[0] = 0;
    if (kind == SQ_KIND_CHORD) th_chords(t, &x, func, len, r, nt);
    else if (kind == SQ_KIND_MONO) {
        if (func == SQ_FUNC_ARP) th_arp(t, &x, len, r, nt);
        else if (sq_func_tune(func)) th_lead(t, &x, func, len, r, nt);   /* (0.29: the balafon is a tune too) */
        else th_line(t, &x, func, len, r, nt);
    }
    return len;
}
uint8_t sq_th_part(const sq_th_t *t, uint8_t func, uint8_t len, char *r, char *nt)
{
    th_grid_t g;
    return th_part(t, func, len, r, nt, &g);
}
/* 0.26: the notes of a part alone, a step each, for the part that answers it (sq_th_t.mate_nt): a line, a tune - the
 * semitones above the root, 0..15; chords - 16 + the kind (0 major, 1 minor, 2 a dominant seventh, 3 a major seventh,
 * 4 a minor seventh, 5 a sus4, 6 a power chord); 255 where nothing begins. nts holds SQ_STEPS: the part, then the
 * same again. */
void sq_th_heard(const sq_th_t *t, uint8_t func, uint8_t len, uint8_t *lev, uint8_t *nts)
{
    static const char KIND[7] = {'M', 'm', '7', 'N', 'n', 's', '5'};
    char r[SQ_STEPS + 1u], nt[SQ_STEPS + 1u];
    th_grid_t g;
    uint32_t i, k, n;
    for (i = 0; i < SQ_STEPS; i++) { nts[i] = 255u; if (lev) lev[i] = 0u; }
    n = th_part(t, func, len, r, nt, &g);
    if (!n) return;
    for (i = 0; i < n; i++) {
        char c = nt[0] ? nt[i] : '.';
        if (lev) lev[i] = g.lev[i];
        if (r[i] == '.' || r[i] == '-') continue;
        if (c >= '0' && c <= '9') nts[i] = (uint8_t)(c - '0');
        else if (c >= 'a' && c <= 'f') nts[i] = (uint8_t)(10 + (c - 'a'));
        else for (k = 0; k < 7u; k++) if (c == KIND[k]) nts[i] = (uint8_t)(16u + k);
    }
    for (i = n; i < SQ_STEPS; i++) { nts[i] = nts[i % n]; if (lev) lev[i] = lev[i % n]; }
}
void sq_th_notes(const sq_th_t *t, uint8_t func, uint8_t len, uint8_t *nts) { sq_th_heard(t, func, len, 0, nts); }

uint8_t sq_th_load(sq_step_t *row, const sq_th_t *t, uint8_t func, uint8_t len, uint8_t note)
{
    char r[SQ_STEPS + 1u], nt[SQ_STEPS + 1u];
    uint8_t n = sq_th_part(t, func, len, r, nt);
    if (!n) return 0u;
    return sq_beat_load_text(row, r, sq_func_kind(func) == SQ_KIND_DRUM ? 0 : nt, func, note);
}

uint8_t sq_th_remake(sq_step_t *row, const sq_th_t *from, const sq_th_t *to, uint8_t func, uint8_t len, uint8_t note, sq_step_t *a, sq_step_t *b)
{
    return sq_th_remake_bar(row, from, to, func, len, note, a, b, 0u, 0u);   /* (0.26: no bar to lay it in - it is made in its own, or in sixteens) */
}
uint8_t sq_th_minds_kick(const sq_th_t *t, uint8_t func) { return (uint8_t)((th_rule(t, func)->kick & 15u) && t->kick ? 1u : 0u); }
uint8_t sq_th_remake_bar(sq_step_t *row, const sq_th_t *from, const sq_th_t *to, uint8_t func, uint8_t len, uint8_t note, sq_step_t *a, sq_step_t *b,
                         uint8_t bar_steps, uint32_t bar_beats)
{
    uint32_t i, k, changed = 0u, minds;
    if (sq_th_load(a, from, func, len, note) != len || sq_th_load(b, to, func, len, note) != len) return 0u;
    if (bar_steps && (sq_rebar_len(len, bar_steps, bar_beats) != len || !(bar_steps == 16u && sq_metre_fix(16u, bar_beats) == SQ_BEATS_44))) {
        sq_rebar(a, (uint8_t)(len / 16u), bar_steps, bar_beats);         /* 0.25: the two as the metre's bars, as the pattern was made */
        sq_rebar(b, (uint8_t)(len / 16u), bar_steps, bar_beats);
        len = sq_rebar_len(len, bar_steps, bar_beats);
    }
    minds = sq_th_minds_kick(to, func);
    for (i = 0; i < len; i++) {
        const uint8_t *pa = (const uint8_t *)&a[i], *pb = (const uint8_t *)&b[i], *pr = (const uint8_t *)&row[i];
        uint32_t diff = 0u, off = 0u;
        for (k = 0; k < sizeof(sq_step_t); k++) { if (pa[k] != pb[k]) diff = 1u; if (pr[k] != pb[k]) off = 1u; }
        if (!off || !(diff || minds)) continue;
        row[i] = b[i];
        changed++;
    }
    return (uint8_t)changed;
}

/* ------------------------------------------------------------------ the chords */
/* 1 when the key's own triad on step d has no perfect fifth: a diminished chord (the ii of a minor key, the vii of a
 * major one) or an augmented one (the III of a harmonic minor, the VI of a phrygian dominant) */
static uint8_t th_dim(uint8_t scale, uint32_t d)
{
    uint32_t a = th_semi(scale, d), f = th_semi(scale, d + 4u);
    return (uint8_t)((f - a) % 12u != 7u);
}

/* 1 when the chord of the key on step d can take the colour: the HARMONY builds a colour from the notes of the key, so a
 * ninth or a sus2 wants a major second above the root (not the flat one of a phrygian tonic), a sus4 a perfect fourth
 * (not the sharp one of the VI of a minor key), a 6th a major sixth, a 7th not the major seventh on a minor chord */
static uint8_t th_col_ok(uint8_t scale, uint32_t d, uint32_t col)
{
    uint32_t r = th_semi(scale, d), i2 = th_semi(scale, d + 1u) - r, i3 = th_semi(scale, d + 2u) - r, i4 = th_semi(scale, d + 3u) - r,
             i6 = th_semi(scale, d + 5u) - r, i7 = th_semi(scale, d + 6u) - r;
    switch (col) {
    case SQ_HC_7:    return (uint8_t)!(i3 == 3u && i7 == 11u);
    case SQ_HC_9:    return (uint8_t)(i2 == 2u && !(i3 == 3u && i7 == 11u));
    case SQ_HC_SUS4: return (uint8_t)(i4 == 5u);
    case SQ_HC_SUS2: return (uint8_t)(i2 == 2u);
    case SQ_HC_6:    return (uint8_t)(i6 == 9u);
    default:         return 1u;
    }
}

void sq_th_prog(sq_uprog_t *u, const sq_th_t *t)
{
    static const uint8_t BARS[4] = {1u, 2u, 4u, 8u};
    const th_prog_t *p = &TH_PROGS[t->style < SQ_TH_STYLES ? t->style : SQ_TH_FREE];
    uint32_t part = 0x7100u, n, k, one_col, push;
    uint8_t deg[4], w[7];
    sq_uprog_default(u);
    n = th_pick(p->n_w, 4u, th_u(t, part, 1u, 1u)) + 1u;
    {
    uint32_t home = 0u;                                   /* where home is: the first chord, unless it starts elsewhere */
    deg[0] = 0u;
    if (n >= 2u && th_u(t, part, 2u, 1u) % 100u >= p->first) {   /* not from home: another chord of the key, not a diminished one */
        for (k = 0; k < 7u; k++) w[k] = (uint8_t)(k && !th_dim(t->scale, k) ? 10u : 0u);
        deg[0] = (uint8_t)th_pick(w, 7u, th_u(t, part, 3u, 1u));
        home = n == 2u ? 1u : n - 1u - (th_u(t, part, 6u, 1u) & 1u);       /* ... and home comes later: the last chord, or the one before */
    }
    for (k = 1u; k < n; k++) {
        uint32_t d, total = 0u;
        if (home && k == home) { deg[k] = 0u; continue; }
        if (k + 1u == n && n >= 3u) {                     /* the last of three or four: one that leads home */
            for (d = 0; d < 7u; d++) w[d] = (uint8_t)(d == deg[k - 1u] || d == 0u || th_dim(t->scale, d) ? 0u : p->last_w[d]);
        } else {
            for (d = 0; d < 7u; d++) w[d] = 0u;
            for (d = 1u; d <= 6u; d++) {
                uint32_t to = (deg[k - 1u] + d) % 7u;
                if (th_dim(t->scale, to)) continue;
                if (to == 0u && (home || (n == 4u && k < 3u))) continue;   /* (home has its place; from home, not home again before
                                                                             * the end of four chords) */
                w[to] = p->move_w[d - 1u];
            }
        }
        for (d = 0; d < 7u; d++) total += w[d];
        if (!total) for (d = 0; d < 7u; d++) w[d] = (uint8_t)(d != deg[k - 1u] && !th_dim(t->scale, d) ? 1u : 0u);
        deg[k] = (uint8_t)th_pick(w, 7u, th_u(t, part, 0x10u + k, 2u));
    }
    }
    one_col = th_u(t, part, 4u, 1u) % 100u < p->col_same ? 1u : 0u;
    push = th_pick(p->push_w, 3u, th_u(t, part, 7u, 1u));
    for (k = 0; k < n; k++) {
        uint32_t col = th_pick(p->col_w, SQ_HCS, th_u(t, part, one_col ? 0x20u : 0x20u + k, 3u));
        if (!th_col_ok(t->scale, deg[k], col)) col = col == SQ_HC_9 && th_col_ok(t->scale, deg[k], SQ_HC_7) ? SQ_HC_7 : SQ_HC_TRIAD;
        u->deg[k] = (int8_t)deg[k];
        u->col[k] = (uint8_t)col;
        u->push[k] = (uint8_t)(n >= 2u ? push : 0u);                    /* (one chord: nothing to come in early) */
    }
    u->n = (uint8_t)n;
    u->bars = BARS[th_pick(p->bars_w, 4u, th_u(t, part, 5u, 1u))];
    if (n == 1u) u->bars = 4u;
    while (n * u->bars > 16u) u->bars = (uint8_t)(u->bars / 2u);         /* (the whole round in 16 bars at most) */
}
#undef TB
#undef TW
#undef TW0
#undef TCL
#undef TH_NOCLS
#undef TH_HAND
#undef TL
#undef TH_BEATS
#undef TH_OFFS
#undef TH_EIGHT
#undef TH_N_RULES
