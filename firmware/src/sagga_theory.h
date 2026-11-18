/* SPDX-License-Identifier: GPL-3.0-only */
#ifndef SAGGA_THEORY_H
#define SAGGA_THEORY_H

#include "sagga_seq_core.h"
#include "sagga_beats.h"

/* SAGGA SEQ 0.23: the THEORY engines. A part is not loaded from the library: it is MADE from the
 * rules of a style - what is always there, what never is, how likely a hit is on each 16th, which 16ths come together,
 * how the bass relates to the kick, which notes a line and a motif use, how the roots of the chords move - and written
 * as the library writes a pattern (the same text: sagga_beats.h), so everything after it is what it was: the steps,
 * the key, the HARMONY and FOLLOW, COOK, SAVE.
 *
 * One SEED is one band: the same seed gives the same parts, whatever else was made before. ENERGY fills a part or
 * thins it without changing what is already there (a choice is a number against a threshold: a higher threshold only
 * adds). A VARIATION makes a share of the choices again (`vary` %), the rest stays: the same part, a little or a lot
 * different. FREE is a style with no genre in it: the metre and the families of the parts, nothing else.
 *
 * Nothing here knows the FM-1: it is the core (the simulator, the Pi's tools and the firmware share it). */
/* A style is a genre of the library, or FREE (SQ_TH_FREE: sagga_seq_core.h, with what a project keeps of a pattern the
 * engines made). Four have rules written by hand; the others have rules counted from the library itself
 * (tools/theory/gen_rules.py -> sagga_theory_data.h). */
#define SQ_TH_TECHNO  SQ_GENRE_TECHNO
#define SQ_TH_HOUSE   SQ_GENRE_HOUSE
#define SQ_TH_DNB     SQ_GENRE_DNB
#define SQ_TH_DUBSTEP SQ_GENRE_DUBSTEP

typedef struct {
    uint8_t style;               /* SQ_TH_* */
    uint8_t energy;              /* 0..100: how full */
    uint8_t vary;                /* 0..100: the share of its choices a variation makes again */
    uint8_t scale;               /* SQ_SC_*: the key's scale (the notes are written in it) */
    uint32_t seed;               /* the band */
    uint32_t var;                /* which variation (0: the seed's own) */
    const uint8_t *kick;         /* the kick that plays with it: its level on each 16th of the pattern (SQ_STEPS of them: 0
                                  * none, 1 a ghost, 2 soft, 3 a hit, 4 an accent). 0: the seed's own kick. A rumble is never
                                  * where it is, a sub leans on it. */
    const uint8_t *mate;         /* 0.25 THE PARTS LISTEN: the part this one ANSWERS, its levels as `kick` (0: nobody). Where
                                  * the other attacks, a hit of this one stays away two times in three; right after an
                                  * attack of the other (the next 16th, or the one after) it is likelier: the answer comes
                                  * after the call. What a part always plays stays (it is still itself). Who answers whom:
                                  * sq_th_mate_family; a part that answers nobody takes no notice of it. */
} sq_th_t;
/* the family (SQ_FUNC_KICK .. SQ_FUNC_ARP) of the part that part `func` answers; 255: it answers nobody. An arpeggio, a
 * lead, a voice: the chords (the stab, the pad, the piano). The percussion: the snare, the clap. A bass: the lead. */
uint8_t sq_th_mate_family(uint8_t func);
/* the rhythm of a part alone, a level a 16th (as `kick` and `mate` want it): lev holds SQ_STEPS; the len 16ths are
 * the part's, the rest of the SQ_STEPS the same again */
void sq_th_levels(const sq_th_t *t, uint8_t func, uint8_t len, uint8_t *lev);

uint8_t sq_th_style(uint8_t genre);          /* the style of a library genre (255: not a genre) */
uint8_t sq_th_genre(uint8_t style);          /* ... and back: the genre whose band and feel a style uses (FREE: 255) */
const char *sq_th_name(uint8_t style);
#define SQ_TH_BAND_MAX SQ_BAND_MAX   /* the parts of a style's band, at most */
uint8_t sq_th_band(uint8_t style, uint8_t *funcs);   /* the parts of its band, in order (the genre's own; FREE: a band of its own); returns how many */
uint8_t sq_th_scale(const sq_th_t *t);       /* a scale the style likes, by the seed */
uint8_t sq_th_root(const sq_th_t *t);        /* ... and a root, 0..11 */
/* The part `func` (SQ_FUNC_*) of the style, `len` steps (16, 32 or 64), as the library writes one: r the hits ('.', 'x',
 * 'X', 'o', 'g', '2'-'4', '-'), nt the notes (hex semitones above the root, or the kind of chord; a drum: nt[0] = 0).
 * Both hold len + 1 characters. Returns len, 0 if the part cannot be made (PROG, KIT). A part the style has no rules
 * for is made by FREE's rules for its family. */
uint8_t sq_th_part(const sq_th_t *t, uint8_t func, uint8_t len, char *r, char *nt);
/* ... and straight into a row, as sq_beat_load_text does (`note`: the track's own note) */
uint8_t sq_th_load(sq_step_t *row, const sq_th_t *t, uint8_t func, uint8_t len, uint8_t note);
/* A pattern the engines made, made again another way (`from` -> `to`: another energy, another variation, another
 * style): only the steps that are not the same in the two are written into `row` - what the player changed elsewhere
 * stays. A part that minds a kick that plays (to->kick: a rumble, a sub) is written whole: the kick may have changed
 * under it. `a`, `b`: two rows to work in (SQ_STEPS). Returns how many steps of `row` changed. */
uint8_t sq_th_remake(sq_step_t *row, const sq_th_t *from, const sq_th_t *to, uint8_t func, uint8_t len, uint8_t note, sq_step_t *a, sq_step_t *b);
/* 0.25: ... of a pattern that was made in the metre's bars (sq_rebar: `len` is still the sixteens it was made in) */
uint8_t sq_th_remake_bar(sq_step_t *row, const sq_th_t *from, const sq_th_t *to, uint8_t func, uint8_t len, uint8_t note, sq_step_t *a, sq_step_t *b,
                         uint8_t bar_steps, uint32_t bar_beats);
uint8_t sq_th_minds_kick(const sq_th_t *t, uint8_t func);   /* 1: the part minds a kick that plays with it (t->kick): a rumble, a sub */
/* a progression of the style: the steps of the key its roots are on, their colours, the bars a chord lasts */
void sq_th_prog(sq_uprog_t *u, const sq_th_t *t);

#endif
