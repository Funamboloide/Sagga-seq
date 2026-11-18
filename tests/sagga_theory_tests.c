/* SPDX-License-Identifier: GPL-3.0-only
 * SAGGA SEQ, the THEORY engines (firmware/src/sagga_theory.c): what they promise, over many seeds.
 *   cc -std=c11 -Wall -Wextra -Werror -Ifirmware/src tests/sagga_theory_tests.c firmware/src/sagga_seq_core.c \
 *      firmware/src/sagga_beats.c -o build/sagga_theory_tests && build/sagga_theory_tests [SEEDS]
 * The engine is included, not linked: the tests read its rules. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../firmware/src/sagga_theory.c"

static unsigned long checks, failed;
static void fail(const char *what, const sq_th_t *t, uint8_t func, uint8_t len, const char *a, const char *b)
{
    failed++;
    if (failed <= 12u)
        printf("FAIL %s: %s seed %u var %u vary %u energy %u %s len %u\n  %s\n  %s\n", what, sq_th_name(t->style), (unsigned)t->seed,
               (unsigned)t->var, (unsigned)t->vary, (unsigned)t->energy, func < SQ_FUNCS ? sq_func_name(func) : "-", (unsigned)len, a ? a : "", b ? b : "");
}
#define CHECK(c, what, t, func, len, a, b) do { checks++; if (!(c)) fail(what, t, func, len, a, b); } while (0)

static int is_hit(char c) { return c != '.' && c != '-' && c != 0; }
static int is_loud(char c) { return c == 'x' || c == 'X' || c == 'o' || (c >= '2' && c <= '4'); }
static int hexv(char c) { return c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : -1; }
/* 0.26: the bar the tests run in. G_GEN 0: the engines of 0.25 (sixteens, 4/4); 1: a part made IN the bar G_STEPS /
 * G_BEATS. NB(t, bars): the steps of so many bars (16, 32, 64 in 4/4); X: the bar as the engine sees it */
static uint8_t G_GEN, G_STEPS = 16u;
static uint32_t G_BEATS = SQ_BEATS_44;
static sq_th_t th(uint8_t style, uint32_t seed, uint8_t energy, uint32_t var, uint8_t vary)
{
    sq_th_t t;
    memset(&t, 0, sizeof t);
    t.style = style; t.seed = seed; t.energy = energy;
    t.scale = sq_th_scale(&t);
    t.var = var; t.vary = vary;
    if (G_GEN) { t.gen = 1u; t.bar_steps = G_STEPS; t.bar_beats = G_BEATS; }
    return t;
}
static uint8_t NB(const sq_th_t *t, uint8_t bars) { return sq_th_steps(t, bars); }
/* the steps of a pattern of n that the fill of its end can touch are not looked at: from `n - 16` (its last four
 * 16ths), or its last bar when that is longer (the percussion's second half) */
static uint32_t body(const th_bar_t *x, uint32_t n) { uint32_t f = x->steps > 16u ? x->steps : 16u; return n > f ? n - f : 0u; }
static const uint8_t ENERGY[8] = {0u, 10u, 25u, 40u, 60u, 75u, 90u, 100u};
static const uint8_t BARS[3] = {1u, 2u, 4u};
#define TH_N_RULES_T (sizeof TH_RULES / sizeof TH_RULES[0])

/* a part is what the library could have written: its text is valid, the firmware loads it, its notes are in the key */
static void t_text(uint32_t seeds)
{
    uint32_t seed;
    uint8_t st, f, li, e;
    for (st = 0; st < SQ_TH_STYLES; st++)
        for (seed = 1; seed <= seeds; seed++)
            for (f = 0; f < SQ_FUNCS; f++)
                for (li = 0; li < 3u; li++) {
                    uint8_t len, kind = sq_func_kind(f), n, loud = 0u;
                    char r[SQ_STEPS + 1u], nt[SQ_STEPS + 1u], r2[SQ_STEPS + 1u], nt2[SQ_STEPS + 1u];
                    sq_step_t row[SQ_STEPS];
                    sq_th_t t;
                    th_bar_t x;
                    uint32_t i;
                    uint16_t mask;
                    e = ENERGY[(seed + f + li) % 8u];
                    t = th(st, seed, e, (seed % 3u) ? 0u : seed, (uint8_t)((seed * 7u) % 101u));
                    th_ctx(&t, &x);
                    len = NB(&t, BARS[li]);
                    if (li && len == NB(&t, BARS[li - 1u])) continue;       /* (a long bar: four of them do not fit) */
                    mask = sq_scale_mask(sq_harm_scale(t.scale));
                    n = sq_th_part(&t, f, len, r, nt);
                    if (f == SQ_FUNC_PROG || f == SQ_FUNC_KIT) { CHECK(n == 0u, "PROG and KIT are not parts", &t, f, len, 0, 0); continue; }
                    CHECK(n == len && strlen(r) == len, "the length", &t, f, len, r, nt);
                    for (i = 0; i < len; i++) {
                        CHECK(strchr(".-xXog234", r[i]) != 0, "a character of the hits", &t, f, len, r, nt);
                        if (r[i] == '-') CHECK(i > 0u && r[i - 1u] != '.', "a held step after nothing", &t, f, len, r, nt);
                        if (is_loud(r[i])) loud = 1u;
                        if (!is_hit(r[i])) continue;
                        if (kind == SQ_KIND_MONO) {
                            int v = hexv(nt[i]);
                            CHECK(v >= 0, "a note of a line", &t, f, len, r, nt);
                            if (v >= 0) CHECK((mask >> (v % 12)) & 1u, "a note out of the key", &t, f, len, r, nt);
                        } else if (kind == SQ_KIND_CHORD) CHECK(nt[i] && strchr("mMnN75", nt[i]) != 0, "the kind of a chord", &t, f, len, r, nt);
                    }
                    if (kind == SQ_KIND_DRUM) CHECK(nt[0] == 0, "a drum has no notes", &t, f, len, r, nt);
                    else CHECK(strlen(nt) == len, "the length of the notes", &t, f, len, r, nt);
                    {                                   /* (a part whose rule is all ghosts - the percussion of drum and bass - has a ghost) */
                        const th_rule_t *q = th_rule(&t, f);
                        uint8_t can = (uint8_t)(f == SQ_FUNC_CRASH || q->fixA || q->fixx || q->cls[0] || q->cls[1] || q->cls[2] || q->cls[3]), any = 0u;
                        for (i = 0; i < 16u; i++) if (th_nib(q->w, i) > q->soft) can = 1u;
                        if (q->kick & TH_K_LV) {            /* (a rule counted from the library: a place that is not a ghost's, always there or with a weight) */
                            can = 0u;
                            for (i = 0; i < len; i++) if (((th_fix(&t, q, &x, i) >> th_s16(&x, i)) & 1u || th_nib(th_bar(q, &x, i)->w, th_s16(&x, i))) && th_level(q, &x, 15u, i) >= TH_O) can = 1u;
                        }
                        for (i = 0; i < len; i++) if (is_hit(r[i])) any = 1u;
                        if ((q->kick & 15u) == TH_K_AVOID && x.steps < 8u) {   /* (0.26: a rumble is never on a kick - in a bar of a few steps the kick may leave it nowhere to stand) */
                            char kr[SQ_STEPS + 1u], kn[SQ_STEPS + 1u];
                            uint32_t room = 0u;
                            sq_th_part(&t, SQ_FUNC_KICK, len, kr, kn);
                            for (i = 0; i < len; i++) { if (!is_hit(kr[i])) room++; else CHECK(!is_hit(r[i]), "a rumble on a kick", &t, f, len, r, kr); }
                            if (!room) { CHECK(!any, "a rumble with no step free of the kick", &t, f, len, r, kr); can = 0u; any = 1u; }
                        }
                        CHECK(can ? loud : any, "a part is never empty", &t, f, len, r, nt);
                    }
                    CHECK(sq_th_load(row, &t, f, len, 60u) == len, "the firmware loads it", &t, f, len, r, nt);
                    /* the same again, after other parts were made: nothing depends on the order */
                    sq_th_part(&t, (uint8_t)((f + 3u) % SQ_FUNC_PROG), NB(&t, 4u), r2, nt2);
                    sq_th_part(&t, f, len, r2, nt2);
                    CHECK(!strcmp(r, r2) && !strcmp(nt, nt2), "the same seed, the same part", &t, f, len, r, r2);
                }
}

/* what a style says is always there is there, what it says never is never is: at every energy, in every variation
 * (the end apart: the fill may move the last snare). 0.26: in a bar of any metre, at the step that STANDS FOR the 16th
 * the rule speaks of */
static void t_anchors(uint32_t seeds)
{
    uint32_t seed, i;
    uint8_t st, f, e;
    for (st = 0; st < SQ_TH_STYLES; st++)
        for (seed = 1; seed <= seeds; seed++)
            for (f = 0; f < SQ_FUNCS; f++)
                for (e = 0; e < 8u; e++) {
                    sq_th_t t = th(st, seed, ENERGY[e], seed & 1u, (uint8_t)(seed % 101u));
                    const th_rule_t *q;
                    th_grid_t kick;
                    th_bar_t x;
                    char r[SQ_STEPS + 1u], nt[SQ_STEPS + 1u];
                    uint8_t n = NB(&t, 4u);
                    if (f == SQ_FUNC_PROG || f == SQ_FUNC_KIT || f == SQ_FUNC_CRASH) continue;
                    th_ctx(&t, &x);
                    q = th_rule(&t, f);
                    sq_th_part(&t, f, n, r, nt);
                    th_rhythm(&t, &x, SQ_FUNC_KICK, n, &kick);
                    for (i = 0; i < body(&x, n); i++) {
                        uint16_t bit = (uint16_t)(1u << th_s16(&x, i));
                        uint8_t avoided = (uint8_t)((q->kick & 15u) == TH_K_AVOID && kick.lev[i]);
                        if ((th_bar(q, &x, i)->never & bit) || avoided) CHECK(!is_hit(r[i]), "a hit where the style has none", &t, f, n, r, nt);
                        else if (q->kick & TH_K_LV) {   /* (counted from the library: at its place's own level, a roll apart) */
                            static const char LV[5] = {'.', 'g', 'o', 'x', 'X'};
                            if (th_fix(&t, q, &x, i) & bit) CHECK(r[i] == LV[th_level(q, &x, 15u, i)] || (r[i] >= '2' && r[i] <= '4' && (th_bar(q, &x, i)->rollm & bit)), "what a family always plays", &t, f, n, r, nt);
                        }
                        else if (q->fixA & bit) CHECK(r[i] == 'X' || (r[i] >= '2' && r[i] <= '4'), "the accent that is always there", &t, f, n, r, nt);
                        else if (q->fixx & bit) CHECK(is_loud(r[i]), "the hit that is always there", &t, f, n, r, nt);
                    }
                }
}

/* the styles, said plainly (what the rules above must come to). 0.26: in the bar of any metre - the kick of techno on
 * EVERY beat of the bar, the clap of house on the backbeat (the step that stands for beat two, for beat four) ... */
static void t_styles(uint32_t seeds)
{
    uint32_t seed;
    uint8_t e;
    for (seed = 1; seed <= seeds; seed++)
        for (e = 0; e < 8u; e++) {
            char r[SQ_STEPS + 1u], k[SQ_STEPS + 1u], nt[SQ_STEPS + 1u];
            sq_th_t t = th(SQ_TH_TECHNO, seed, ENERGY[e], 0u, 0u);
            th_bar_t x;
            uint32_t i, n = NB(&t, 4u), end;
            th_ctx(&t, &x);
            end = body(&x, n);
            sq_th_part(&t, SQ_FUNC_KICK, (uint8_t)n, k, nt);
            for (i = 0; i < n; i++) if ((th_s16(&x, i) & 3u) == 0u) CHECK(k[i] == 'X' || (i >= end && is_loud(k[i])), "techno: four on the floor (a kick on every beat of the bar)", &t, SQ_FUNC_KICK, (uint8_t)n, k, 0);
            for (i = 0; i < n; i++) if (th_onbeat(&x, i)) CHECK(is_loud(k[i]), "techno: a beat of the bar without its kick", &t, SQ_FUNC_KICK, (uint8_t)n, k, 0);
            sq_th_part(&t, SQ_FUNC_RUMBLE, (uint8_t)n, r, nt);
            for (i = 0; i < n; i++) CHECK(!(is_hit(r[i]) && is_hit(k[i])), "techno: the rumble is never on a kick", &t, SQ_FUNC_RUMBLE, (uint8_t)n, r, k);
            sq_th_part(&t, SQ_FUNC_HAT, (uint8_t)n, r, nt);
            for (i = 0; i < end; i++) if ((th_s16(&x, i) & 3u) == 2u) CHECK(is_loud(r[i]), "techno: the hat on the off-beats", &t, SQ_FUNC_HAT, (uint8_t)n, r, 0);
            t = th(SQ_TH_HOUSE, seed, ENERGY[e], 0u, 0u);
            th_ctx(&t, &x);
            sq_th_part(&t, SQ_FUNC_KICK, (uint8_t)n, k, nt);
            for (i = 0; i < n; i++) if (th_onbeat(&x, i)) CHECK(k[i] == 'X' || (i >= end && is_loud(k[i])), "house: four on the floor", &t, SQ_FUNC_KICK, (uint8_t)n, k, 0);
            sq_th_part(&t, SQ_FUNC_CLAP, (uint8_t)n, r, nt);
            for (i = 0; i < end; i++) if (th_s16(&x, i) == 4u || th_s16(&x, i) == 12u) CHECK(r[i] == 'X', "house: the clap on 2 and 4", &t, SQ_FUNC_CLAP, (uint8_t)n, r, 0);
            t = th(SQ_TH_DNB, seed, ENERGY[e], 0u, 0u);
            th_ctx(&t, &x);
            sq_th_part(&t, SQ_FUNC_KICK, (uint8_t)n, k, nt);
            sq_th_part(&t, SQ_FUNC_SNARE, (uint8_t)n, r, nt);
            for (i = 0; i < end; i++) {
                uint32_t a = th_s16(&x, i);
                if (a == 0u) CHECK(k[i] == 'X', "drum and bass: the kick on the one", &t, SQ_FUNC_KICK, (uint8_t)n, k, r);
                if (a == 10u) CHECK(is_loud(k[i]), "drum and bass: the two-step's second kick", &t, SQ_FUNC_KICK, (uint8_t)n, k, r);
                if (a == 4u || a == 12u) CHECK(r[i] == 'X', "drum and bass: the snare on 2 and 4", &t, SQ_FUNC_SNARE, (uint8_t)n, k, r);
            }
            t = th(SQ_TH_DUBSTEP, seed, ENERGY[e], 0u, 0u);
            th_ctx(&t, &x);
            sq_th_part(&t, SQ_FUNC_KICK, (uint8_t)n, k, nt);
            sq_th_part(&t, SQ_FUNC_SNARE, (uint8_t)n, r, nt);
            {   /* (0.26: a bar with no step for beat three - three beats: ONE two FOUR - carries the snare on a beat it has:
                 *  one accent a bar, on a beat) */
                uint32_t has3 = 0u, b;
                for (i = 0; i < n; i++) if (th_s16(&x, i) == 8u) has3 = 1u;
                for (i = 0; i < end; i++) {
                    uint32_t a = th_s16(&x, i);
                    if (a == 0u) CHECK(k[i] == 'X', "dubstep: the kick on the one", &t, SQ_FUNC_KICK, (uint8_t)n, k, r);
                    if (a == 8u) CHECK(r[i] == 'X', "dubstep: half-time, the snare on 3", &t, SQ_FUNC_SNARE, (uint8_t)n, k, r);
                    if (has3 && (a == 4u || a == 12u)) CHECK(!is_loud(r[i]), "dubstep: no snare on 2 and 4", &t, SQ_FUNC_SNARE, (uint8_t)n, k, r);
                }
                if (!has3)
                    for (b = 0; (b + 1u) * x.steps <= end; b++) {
                        uint32_t acc = 0u;
                        for (i = b * x.steps; i < (b + 1u) * x.steps; i++) if (r[i] == 'X') { acc++; CHECK(th_onbeat(&x, i) && i % x.steps != 0u, "dubstep: the snare carried to a beat of the bar, not the one", &t, SQ_FUNC_SNARE, (uint8_t)n, k, r); }
                        CHECK(acc == 1u, "dubstep: one snare a bar, on a beat it has", &t, SQ_FUNC_SNARE, (uint8_t)n, k, r);
                    }
            }
            sq_th_part(&t, SQ_FUNC_SUB, (uint8_t)n, r, nt);
            for (i = 0; i < n; i++) if (th_s16(&x, i) == 0u) CHECK(r[i] == 'X', "dubstep: the sub on the one", &t, SQ_FUNC_SUB, (uint8_t)n, r, nt);
        }
}

/* ENERGY fills a part and empties it without moving what is there: every hit of a lower energy is in a higher one, and
 * a note that stays keeps its pitch (a rumble apart where the kick comes in: it is never on a kick) */
static void t_energy(uint32_t seeds)
{
    uint32_t seed, i, moved = 0u, notes = 0u;
    uint8_t st, f, e;
    for (st = 0; st < SQ_TH_STYLES; st++)
        for (seed = 1; seed <= seeds; seed++)
            for (f = 0; f < SQ_FUNCS; f++) {
                char r0[SQ_STEPS + 1u], n0[SQ_STEPS + 1u], k1[SQ_STEPS + 1u], kn[SQ_STEPS + 1u];
                uint8_t kind = sq_func_kind(f);
                if (f == SQ_FUNC_PROG || f == SQ_FUNC_KIT) continue;
                for (e = 0; e < 8u; e++) {
                    sq_th_t t = th(st, seed, ENERGY[e], seed % 2u, (uint8_t)(seed % 90u));
                    char r1[SQ_STEPS + 1u], n1[SQ_STEPS + 1u];
                    uint8_t avoid = (uint8_t)((th_rule(&t, f)->kick & 15u) == TH_K_AVOID), n = NB(&t, 4u);
                    sq_th_part(&t, f, n, r1, n1);
                    sq_th_part(&t, SQ_FUNC_KICK, n, k1, kn);
                    if (e)
                        for (i = 0; i < n; i++) {
                            if (!is_hit(r0[i])) continue;
                            if (avoid && is_hit(k1[i])) continue;
                            CHECK(is_hit(r1[i]), "a hit lost as the energy rises", &t, f, n, r0, r1);
                            if (kind != SQ_KIND_DRUM && f != SQ_FUNC_ARP && is_hit(r1[i])) { notes++; if (n0[i] != n1[i]) moved++; }
                        }
                    memcpy(r0, r1, sizeof r0); memcpy(n0, n1, sizeof n0);
                }
            }
    /* (the last note of a motif's bar comes home, and the last note is another when the energy adds one after it) */
    checks++;
    printf("theory: of %u notes that stay as the energy rises, %u change pitch\n", (unsigned)notes, (unsigned)moved);
    if (moved * 100u > notes * 3u) { failed++; printf("FAIL the notes move with the energy: %u of %u\n", (unsigned)moved, (unsigned)notes); }
}

/* a VARIATION: none at 0 %, more of the part made again the higher it is; the small ones leave the big choices alone;
 * the family of a part (which of the style's rules it follows) is the seed's and stays */
static void t_variation(uint32_t seeds)
{
    static const uint8_t VARY[5] = {10u, 25u, 50u, 75u, 100u};
    uint32_t seed, i, dist[5] = {0u, 0u, 0u, 0u, 0u}, total = 0u, v;
    uint8_t st, f;
    for (st = 0; st < SQ_TH_STYLES; st++)
        for (seed = 1; seed <= seeds; seed++)
            for (f = 0; f < SQ_FUNCS; f++) {
                sq_th_t t = th(st, seed, 60u, 0u, 0u), t2;
                char r[SQ_STEPS + 1u], nt[SQ_STEPS + 1u], r2[SQ_STEPS + 1u], nt2[SQ_STEPS + 1u];
                uint8_t n = NB(&t, 4u);
                if (f == SQ_FUNC_PROG || f == SQ_FUNC_KIT) continue;
                sq_th_part(&t, f, n, r, nt);
                t2 = t; t2.var = 5u; t2.vary = 0u;
                sq_th_part(&t2, f, n, r2, nt2);
                CHECK(!strcmp(r, r2) && !strcmp(nt, nt2), "a variation of 0 % changes nothing", &t2, f, n, r, r2);
                t2 = t; t2.var = 0u; t2.vary = 80u;
                sq_th_part(&t2, f, n, r2, nt2);
                CHECK(!strcmp(r, r2) && !strcmp(nt, nt2), "variation 0 is the seed's own", &t2, f, n, r, r2);
                for (v = 0; v < 5u; v++) {
                    t2 = t; t2.var = 1u + seed % 7u; t2.vary = VARY[v];
                    CHECK(th_rule(&t2, f) == th_rule(&t, f), "a variation keeps the family", &t2, f, n, 0, 0);
                    sq_th_part(&t2, f, n, r2, nt2);
                    for (i = 0; i < n; i++) if (r[i] != r2[i] || (nt[0] && nt[i] != nt2[i])) dist[v]++;
                }
                total += n;
            }
    printf("theory: a variation changes %u %u %u %u %u steps in 1000 at 10 25 50 75 100 %%\n", (unsigned)(dist[0] * 1000u / total), (unsigned)(dist[1] * 1000u / total),
           (unsigned)(dist[2] * 1000u / total), (unsigned)(dist[3] * 1000u / total), (unsigned)(dist[4] * 1000u / total));
    for (v = 1; v < 5u; v++) { checks++; if (dist[v] <= dist[v - 1u]) { failed++; printf("FAIL a larger variation changes less: %u %% -> %u steps, %u %% -> %u\n", VARY[v - 1u], (unsigned)dist[v - 1u], VARY[v], (unsigned)dist[v]); } }
    checks++;
    if (!dist[0] || dist[1] * 2u > dist[4]) { failed++; printf("FAIL a small variation is not small: %u against %u\n", (unsigned)dist[1], (unsigned)dist[4]); }
}

/* the chords: one to four, the whole round in 16 bars, home among them, never a diminished or an augmented chord (home
 * apart: it is what the key makes it), a colour only where the key makes it sound (th_col_ok), and nothing the firmware
 * would have to put right */
static void t_prog(uint32_t seeds)
{
    uint32_t seed, k, kinds[SQ_TH_STYLES][4];
    uint8_t st;
    memset(kinds, 0, sizeof kinds);
    for (st = 0; st < SQ_TH_STYLES; st++)
        for (seed = 1; seed <= seeds * 4u; seed++) {
            sq_th_t t = th(st, seed, 60u, seed % 4u, (uint8_t)(seed % 4u ? 100u : 0u));
            sq_uprog_t u, v;
            uint8_t home = 0u;
            char name[40];
            sq_th_prog(&u, &t);
            sq_uprog_name(&u, t.scale, name, sizeof name);
            CHECK(u.n >= 1u && u.n <= 4u, "one to four chords", &t, 255u, 0u, name, 0);
            CHECK(u.bars == 1u || u.bars == 2u || u.bars == 4u || u.bars == 8u, "the bars a chord", &t, 255u, 0u, name, 0);
            CHECK((uint32_t)u.n * u.bars <= 16u, "the round in 16 bars", &t, 255u, 0u, name, 0);
            for (k = 0; k < u.n; k++) {
                if (u.deg[k] == 0) home = 1u;
                CHECK(u.deg[k] >= 0 && u.deg[k] <= 6 && (u.deg[k] == 0 || !th_dim(t.scale, (uint32_t)u.deg[k])), "a diminished chord", &t, 255u, 0u, name, 0);
                CHECK(u.col[k] < SQ_HCS && th_col_ok(t.scale, (uint32_t)u.deg[k], u.col[k]), "a colour the key does not make", &t, 255u, 0u, name, 0);
                CHECK(u.push[k] <= 2u, "the push", &t, 255u, 0u, name, 0);
                if (k) CHECK(u.deg[k] != u.deg[k - 1u], "the same chord twice in a row", &t, 255u, 0u, name, 0);
            }
            CHECK(home, "home is among the chords", &t, 255u, 0u, name, 0);
            v = u;
            sq_uprog_sanitize(&v);
            CHECK(!memcmp(&u, &v, sizeof u), "the firmware takes it as it is", &t, 255u, 0u, name, 0);
            sq_th_prog(&v, &t);
            CHECK(!memcmp(&u, &v, sizeof u), "the same seed, the same chords", &t, 255u, 0u, name, 0);
            CHECK(sq_th_root(&t) < 12u, "the root", &t, 255u, 0u, name, 0);
            kinds[st][u.n - 1u]++;
        }
    for (st = 0; st < SQ_TH_STYLES; st++)
        printf("theory: %-10s chords in a progression, of %u: one %u, two %u, three %u, four %u\n", sq_th_name(st), (unsigned)(seeds * 4u), (unsigned)kinds[st][0],
               (unsigned)kinds[st][1], (unsigned)kinds[st][2], (unsigned)kinds[st][3]);
}

/* the band of a style: the genre's own parts in the genre's order, and every one of them can be made */
static void t_band(void)
{
    uint8_t st, i;
    for (st = 0; st < SQ_TH_STYLES; st++) {
        uint8_t funcs[SQ_TH_BAND_MAX], parts[SQ_PARTS_MAX], n = sq_th_band(st, funcs), g = sq_th_genre(st);
        sq_th_t t = th(st, 1u, 60u, 0u, 0u);
        CHECK(n >= 4u && n <= SQ_TH_BAND_MAX, "the size of a band", &t, 255u, 0u, 0, 0);
        if (g != 255u) {
            CHECK(sq_th_style(g) == st, "a style and its genre", &t, 255u, 0u, 0, 0);
            sq_genre_parts(g, parts);
            for (i = 0; i < sq_genre_band(g); i++) CHECK(funcs[i] == parts[i], "the genre's band first", &t, funcs[i], 0u, 0, 0);
        }
        for (i = 0; i < n; i++) {
            char r[SQ_STEPS + 1u], nt[SQ_STEPS + 1u];
            CHECK(sq_th_part(&t, funcs[i], NB(&t, 4u), r, nt) == NB(&t, 4u), "a part of the band", &t, funcs[i], NB(&t, 4u), 0, 0);
        }
    }
}

/* the rules counted from the library (tools/theory/gen_rules.py), as a table: every genre has its own rule for every
 * part of its own; a rule of two bars has its second right after it and no other rule is one; what is always there has
 * no weight; a part whose notes stand apart has no weight beside a hit that is always there (the hit would go again when
 * the other comes in at energy TH_DATA_MID_E) */
static void t_counted(void)
{
    uint32_t i, s;
    uint8_t st, k;
    sq_th_t t = th(SQ_TH_FREE, 1u, 60u, 0u, 0u);
    for (i = 0; i < TH_N_RULES_T; i++) {
        const th_rule_t *q = &TH_RULES[i], *q2;
        if (q->style == 255u) { CHECK(i > 0u && (TH_RULES[i - 1u].kick & TH_K_TWO) && TH_RULES[i - 1u].func == q->func && !(q->kick & TH_K_TWO), "a second bar without its first", &t, q->func, 0u, 0, 0); continue; }
        CHECK(q->style < SQ_TH_STYLES && q->func < SQ_FUNCS, "a rule of no style", &t, 255u, 0u, 0, 0);
        if (q->kick & TH_K_TWO) CHECK(i + 1u < TH_N_RULES_T && TH_RULES[i + 1u].style == 255u, "a first bar without its second", &t, q->func, 0u, 0, 0);
        if (!(q->kick & TH_K_LV)) { CHECK(!q->mid && !q->rollm && !q->lv && !q->roll && !(q->kick & TH_K_TWO), "a rule written by hand with a counted rule's fields", &t, q->func, 0u, 0, 0); continue; }
        q2 = (q->kick & TH_K_TWO) ? q + 1 : q;
        for (k = 0; k < 2u; k++) {
            const th_rule_t *a = k ? q2 : q, *b = k ? q : q2;                 /* (a: this bar; b: the bar before it and after it) */
            uint16_t core = (uint16_t)(a->fixx | a->mid);
            CHECK(!(a->fixx & a->mid) && !a->fixA && !a->never, "a 16th in two of a counted rule's sets", &t, q->func, 0u, 0, 0);
            for (s = 0; s < 16u; s++) {
                uint32_t w = th_nib(a->w, s);
                uint32_t left = s ? (uint32_t)((core >> (s - 1u)) & 1u) : (uint32_t)(((b->fixx | b->mid) >> 15) & 1u);
                uint32_t right = s < 15u ? (uint32_t)((core >> (s + 1u)) & 1u) : (uint32_t)((b->fixx | b->mid) & 1u);
                if ((core >> s) & 1u) CHECK(!w, "a weight on a hit that is always there", &t, q->func, 0u, 0, 0);
                if ((q->kick & TH_K_APART) && w) CHECK(!left && !right, "a weight beside a hit that is always there, in a part whose notes stand apart", &t, q->func, 0u, 0, 0);
            }
        }
    }
    for (st = 0; st < SQ_GENRES; st++) {
        uint8_t parts[SQ_PARTS_MAX], n = sq_genre_parts(st, parts);
        t = th(st, 1u, 60u, 0u, 0u);
        for (k = 0; k < n; k++) {
            if (parts[k] == SQ_FUNC_CRASH) continue;
            if (k < sq_genre_band(st)) CHECK(th_rule(&t, parts[k])->style == st, "a part of a genre's band without a rule of the genre", &t, parts[k], 0u, 0, 0);
        }
    }
}

/* ... and as music: what EVERY variation of the library plays in every bar - the snare of the dembow, the four kicks of
 * trance - the engine plays too, from the energy the whole pattern is in (the last bar apart: its fill) */
static void t_library(uint32_t seeds)
{
    uint32_t seed, i;
    uint8_t st, k, e;
    for (st = 0; st < SQ_GENRES; st++) {
        uint8_t parts[SQ_PARTS_MAX], n = sq_genre_parts(st, parts);
        for (k = 0; k < n; k++) {
            uint8_t f = parts[k], nv = sq_beat_variants(st, f), v;
            uint16_t all = 0xFFFFu;
            sq_th_t t0 = th(st, 1u, 60u, 0u, 0u);
            if (f == SQ_FUNC_CRASH || !(th_rule(&t0, f)->kick & TH_K_LV) || th_rule(&t0, f)->style != st) continue;
            for (v = 0; v < nv; v++) {
                const char *nt = 0, *r = sq_beat_text(st, f, v, &nt);
                size_t len = r ? strlen(r) : 0u, j;
                if (!r) continue;
                for (j = 0; j + 16u <= len; j += 16u) {
                    uint16_t m = 0u;
                    for (i = 0; i < 16u; i++) if (is_hit(r[j + i])) m = (uint16_t)(m | (1u << i));
                    all &= m;
                }
            }
            if (!all) continue;
            for (seed = 1; seed <= seeds; seed++)
                for (e = 2; e < 8u; e++) {
                    sq_th_t t = th(st, seed, ENERGY[e], seed & 1u, (uint8_t)(seed % 101u));
                    char r[SQ_STEPS + 1u], nt[SQ_STEPS + 1u];
                    th_bar_t x;
                    uint8_t n = NB(&t, 4u);
                    th_ctx(&t, &x);
                    sq_th_part(&t, f, n, r, nt);
                    for (i = 0; i < body(&x, n); i++) if ((all >> th_s16(&x, i)) & 1u) CHECK(is_hit(r[i]), "what the library always plays", &t, f, n, r, nt);
                }
        }
    }
}

/* 0.25 THE PARTS LISTEN (sq_th_t.mate): a part that answers another leaves its attacks alone and speaks right after
 * them - fewer of its hits on the other's attacks, more on the 16ths after them, about as many in all, over many seeds
 * -; it is still itself: never empty,
 * what its rule always plays is there, the energy fills it without losing a hit (the other part held still); a part
 * that answers nobody is what it was, whoever is there */
static void t_mate(uint32_t seeds)
{
    static const uint8_t FAMS[3] = {SQ_FUNC_ARP, SQ_FUNC_PERC, SQ_FUNC_BASS}, MATE[3] = {SQ_FUNC_CHORD, SQ_FUNC_SNARE, SQ_FUNC_ARP};
    uint32_t seed, i, k, on_with[3] = {0u, 0u, 0u}, on_alone[3] = {0u, 0u, 0u}, rest_with[3] = {0u, 0u, 0u}, rest_alone[3] = {0u, 0u, 0u};
    uint32_t all_with[3] = {0u, 0u, 0u}, all_alone[3] = {0u, 0u, 0u};
    uint8_t st, f, e;
    CHECK(sq_th_mate_family(SQ_FUNC_LEAD) == SQ_FUNC_CHORD && sq_th_mate_family(SQ_FUNC_VOX) == SQ_FUNC_CHORD && sq_th_mate_family(SQ_FUNC_ARP) == SQ_FUNC_CHORD
          && sq_th_mate_family(SQ_FUNC_PERC) == SQ_FUNC_SNARE && sq_th_mate_family(SQ_FUNC_CONGA) == SQ_FUNC_SNARE && sq_th_mate_family(SQ_FUNC_BASS) == SQ_FUNC_ARP
          && sq_th_mate_family(SQ_FUNC_SUB) == SQ_FUNC_ARP && sq_th_mate_family(SQ_FUNC_KICK) == 255u && sq_th_mate_family(SQ_FUNC_SNARE) == 255u
          && sq_th_mate_family(SQ_FUNC_HAT) == 255u && sq_th_mate_family(SQ_FUNC_PAD) == 255u && sq_th_mate_family(SQ_FUNC_CRASH) == 255u
          && sq_th_mate_family(SQ_FUNC_PROG) == 255u && sq_th_mate_family(200u) == 255u, "who answers whom", 0, 0u, 0u, 0, 0);
    for (st = 0; st < SQ_TH_STYLES; st++)
        for (seed = 1; seed <= seeds; seed++)
            for (f = 0; f < SQ_FUNCS; f++) {
                uint8_t fam = sq_th_mate_family(f), lev[SQ_STEPS], lv2[SQ_STEPS], mf = 255u, n, n1;
                char r0[SQ_STEPS + 1u], n0[SQ_STEPS + 1u], ra[SQ_STEPS + 1u], na[SQ_STEPS + 1u], rm[SQ_STEPS + 1u], nm[SQ_STEPS + 1u];
                sq_th_t t = th(st, seed, 60u, seed % 2u, (uint8_t)(seed % 90u)), tm;
                th_bar_t x;
                if (f == SQ_FUNC_PROG || f == SQ_FUNC_KIT) continue;
                th_ctx(&t, &x);
                n = NB(&t, 4u); n1 = NB(&t, 1u);
                for (k = 0; k < 3u; k++) if (fam == MATE[k]) mf = (uint8_t)k;
                tm = t; tm.energy = 50u;
                sq_th_levels(&tm, fam == 255u ? SQ_FUNC_CHORD : fam == SQ_FUNC_ARP ? SQ_FUNC_LEAD : fam, n, lev);
                {   /* (the levels are the part's own text) */
                    sq_th_part(&tm, fam == 255u ? SQ_FUNC_CHORD : fam == SQ_FUNC_ARP ? SQ_FUNC_LEAD : fam, n, rm, nm);
                    for (i = 0; i < n; i++) CHECK((lev[i] != 0u) == (rm[i] != '.' && rm[i] != '-') || rm[i] == '-', "the levels are not the part", &tm, fam, n, rm, 0);
                    sq_th_levels(&tm, fam == 255u ? SQ_FUNC_CHORD : fam == SQ_FUNC_ARP ? SQ_FUNC_LEAD : fam, n1, lv2);
                    for (i = n1; i < SQ_STEPS; i++) CHECK(lv2[i] == lv2[i % n1], "one bar, again and again", &tm, fam, n1, 0, 0);
                    {   /* 0.26: heard once - the same levels, and the notes of the text */
                        uint8_t hl[SQ_STEPS], hn[SQ_STEPS], on[SQ_STEPS];
                        sq_th_heard(&tm, fam == 255u ? SQ_FUNC_CHORD : fam == SQ_FUNC_ARP ? SQ_FUNC_LEAD : fam, n, hl, hn);
                        sq_th_notes(&tm, fam == 255u ? SQ_FUNC_CHORD : fam == SQ_FUNC_ARP ? SQ_FUNC_LEAD : fam, n, on);
                        CHECK(!memcmp(hl, lev, sizeof hl) && !memcmp(hn, on, sizeof hn), "heard once: not the levels and the notes", &tm, fam, n, rm, nm);
                        for (i = 0; i < n; i++) {
                            int v = hexv(nm[i]);
                            if (rm[i] == '.' || rm[i] == '-' || !nm[0]) CHECK(hn[i] == 255u, "a note heard where nothing begins (or of a drum)", &tm, fam, n, rm, nm);
                            else if (v >= 0) CHECK(hn[i] == (uint8_t)v, "a note heard is not the note", &tm, fam, n, rm, nm);
                            else CHECK(hn[i] >= 16u && hn[i] <= 22u && "Mm7Nns5"[hn[i] - 16u] == nm[i], "a chord heard is not the chord", &tm, fam, n, rm, nm);
                        }
                    }
                }
                sq_th_part(&t, f, n, ra, na);
                t.mate = lev;
                sq_th_part(&t, f, n, rm, nm);
                if (fam == 255u) { CHECK(!strcmp(ra, rm) && !strcmp(na, nm), "a part that answers nobody changed with someone there", &t, f, n, ra, rm); continue; }
                {
                    const th_rule_t *q = th_rule(&t, f);
                    uint32_t any = 0u;
                    for (i = 0; i < n; i++) {
                        uint32_t bit = 1u << th_s16(&x, i);
                        if (is_hit(rm[i])) any = 1u;
                        if (i < body(&x, n) && !(q->kick & TH_K_APART) && ((th_bar(q, &x, i)->fixA | th_bar(q, &x, i)->fixx) & bit) && !(th_bar(q, &x, i)->never & bit) && (q->kick & 15u) != TH_K_AVOID)
                            CHECK(is_hit(rm[i]), "what the part always plays is gone", &t, f, n, ra, rm);
                        if (lev[i] >= TH_O) { on_with[mf] += is_hit(rm[i]); on_alone[mf] += is_hit(ra[i]); }
                        else if (lev[(i + n - 1u) % n] >= TH_O || lev[(i + n - 2u) % n] >= TH_O) { rest_with[mf] += is_hit(rm[i]); rest_alone[mf] += is_hit(ra[i]); }
                        all_with[mf] += is_hit(rm[i]); all_alone[mf] += is_hit(ra[i]);
                    }
                    CHECK(any, "a part that answers is empty", &t, f, n, ra, rm);
                }
                for (e = 0; e < 8u; e++) {                /* the energy, the other part held still */
                    sq_th_t t2 = th(st, seed, ENERGY[e], seed % 2u, (uint8_t)(seed % 90u));
                    char r1[SQ_STEPS + 1u], n1t[SQ_STEPS + 1u], k1[SQ_STEPS + 1u], kn[SQ_STEPS + 1u];
                    uint8_t avoid = (uint8_t)((th_rule(&t2, f)->kick & 15u) == TH_K_AVOID);
                    t2.mate = lev;
                    sq_th_part(&t2, f, n, r1, n1t);
                    { sq_th_t tk = t2; tk.mate = 0; sq_th_part(&tk, SQ_FUNC_KICK, n, k1, kn); }
                    if (e) for (i = 0; i < n; i++) if (is_hit(r0[i]) && !(avoid && is_hit(k1[i]))) CHECK(is_hit(r1[i]), "a hit lost as the energy rises, answering", &t2, f, n, r0, r1);
                    memcpy(r0, r1, sizeof r0); memcpy(n0, n1t, sizeof n0);
                }
                (void)FAMS;
            }
    for (k = 0; k < 3u; k++) {
        static const char *const WHO[3] = {"the arpeggios, leads and voices against the chords", "the percussion against the snare", "the basses against the lead"};
        checks += 3u;
        printf("theory: %s: on the other's attacks %u hits (alone %u), right after them %u (alone %u), in all %u (alone %u)\n", WHO[k], (unsigned)on_with[k],
               (unsigned)on_alone[k], (unsigned)rest_with[k], (unsigned)rest_alone[k], (unsigned)all_with[k], (unsigned)all_alone[k]);
        if (!(on_with[k] * 10u < on_alone[k] * 8u)) { failed++; printf("FAIL %s: it does not leave the other's attacks alone\n", WHO[k]); }
        if (!(rest_with[k] > rest_alone[k])) { failed++; printf("FAIL %s: it does not answer after the other's attacks\n", WHO[k]); }
        if (!(all_with[k] * 100u > all_alone[k] * 85u && all_with[k] * 100u < all_alone[k] * 110u)) { failed++; printf("FAIL %s: answering made it another part (as busy as alone, give or take: no)\n", WHO[k]); }
    }
}

/* ------------------------------------------------------------------ 0.26 */
/* THE ENGINES OF 0.25, BIT FOR BIT: every part they make in 4/4 - all the styles, 24 seeds, every part, three lengths,
 * three energies, three variations, alone, with a kick, with a part to answer -, their levels, their chords, key and
 * root, as one number. The number of 0.25 (taken from its sources before 0.26 touched the engines): a pattern of an old
 * project is made again from its seed, so the engines must go on making THAT pattern. */
static uint32_t h32(uint32_t h, const char *s) { while (*s) { h ^= (uint8_t)*s++; h *= 16777619u; } return h; }
static uint32_t golden(uint8_t gen)
{
    uint32_t style, seed, func, li, ei, vi, km, acc = 2166136261u;
    static const uint8_t LEN[3] = {16, 32, 64}, EN[3] = {0, 50, 100};
    static const uint32_t VAR[3][2] = {{0, 0}, {1, 30}, {2, 80}};
    uint8_t kick[SQ_STEPS], mate[SQ_STEPS];
    for (style = 0; style < SQ_TH_STYLES; style++) for (seed = 0; seed < 24u; seed++) {
        uint32_t line = 2166136261u;
        for (func = 0; func < SQ_FUNCS; func++) for (li = 0; li < 3u; li++) for (ei = 0; ei < 3u; ei++) for (vi = 0; vi < 3u; vi++) for (km = 0; km < 3u; km++) {
            sq_th_t t;
            char r[SQ_STEPS + 1u], nt[SQ_STEPS + 1u];
            uint32_t i;
            memset(&t, 0, sizeof t);
            t.style = (uint8_t)style; t.energy = EN[ei]; t.vary = (uint8_t)VAR[vi][1]; t.var = VAR[vi][0]; t.seed = seed * 37u + 5u;
            t.scale = (uint8_t)(seed % 3u == 0u ? SQ_SC_MINOR : seed % 3u == 1u ? SQ_SC_MAJOR : SQ_SC_DORIAN);
            if (gen) { t.gen = 1u; t.bar_steps = (uint8_t)(gen == 1u ? 16u : 0u); t.bar_beats = gen == 1u ? SQ_BEATS_44 : 0u; }
            for (i = 0; i < SQ_STEPS; i++) { kick[i] = (uint8_t)((i & 3u) == 0u ? 3u : (i % 7u) == 3u ? 2u : 0u); mate[i] = (uint8_t)((i % 5u) == 0u ? 3u : (i % 11u) == 4u ? 4u : 0u); }
            t.kick = km == 1u ? kick : 0; t.mate = km == 2u ? mate : 0;
            r[0] = nt[0] = 0;
            if (!sq_th_part(&t, (uint8_t)func, LEN[li], r, nt)) continue;
            line = h32(h32(line, r), nt);
            if (km == 0u && vi == 0u) { uint8_t lev[SQ_STEPS]; sq_th_levels(&t, (uint8_t)func, LEN[li], lev); for (i = 0; i < SQ_STEPS; i++) line = (line ^ lev[i]) * 16777619u; }
        }
        {   sq_th_t t; sq_uprog_t u; uint32_t i; memset(&t, 0, sizeof t); t.style = (uint8_t)style; t.seed = seed * 37u + 5u; t.scale = SQ_SC_MINOR; t.energy = 50u;
            sq_th_prog(&u, &t); for (i = 0; i < sizeof u; i++) line = (line ^ ((const uint8_t *)&u)[i]) * 16777619u;
            line = (line ^ sq_th_scale(&t)) * 16777619u; line = (line ^ sq_th_root(&t)) * 16777619u; }
        acc = (acc ^ line) * 16777619u;
    }
    return acc;
}
static void t_golden(void)
{
    uint32_t g0 = golden(0u), g1 = golden(1u), g2 = golden(2u);
    checks += 3u;
    if (g0 != 0x729bc746u) { failed++; printf("FAIL the engines of 0.25 are not what they were: %08x, not 729bc746\n", (unsigned)g0); }
    /* ... and a part made IN a bar of 4/4 (with no notes to answer) is the same part: the bar said, or left to be 4/4 */
    if (g1 != g0) { failed++; printf("FAIL a part made in the bar of 4/4 is not the part of 0.25: %08x\n", (unsigned)g1); }
    if (g2 != g0) { failed++; printf("FAIL a part made in a bar that is not said (4/4) is not the part of 0.25: %08x\n", (unsigned)g2); }
}

/* THE BAR (th_ctx, the engines' view of sq_metre_native): in every bar there is, every way it divides - a step stands
 * for a 16th of a 4/4 bar; a beat of the 4/4 bar begins where a beat of the engines' begins and nowhere else; the one
 * is the one; the pattern's steps are bars of the metre (one, two, four: as many as fit); the two ways to feel an odd
 * bar are both there over the seeds, and a band has ONE (its seed's: every part of it the same) */
static void t_bars(void)
{
    uint8_t st, k, s, sv_gen = G_GEN, sv_st = G_STEPS;
    uint32_t sv_bt = G_BEATS, seed, both = 0u, odd = 0u;
    G_GEN = 1u;
    for (st = SQ_BAR_MIN; st <= SQ_BAR_MAX; st++)
        for (k = 0; k < sq_metre_options(st); k++) {
            uint32_t ways = 0u, diff = 0u;
            uint8_t a0[SQ_BAR_MAX];
            G_STEPS = st; G_BEATS = sq_metre_option(st, k);
            for (seed = 1; seed <= 24u; seed++) {
                sq_th_t t = th((uint8_t)(seed % SQ_TH_STYLES), seed, 60u, 0u, 0u), t2;
                th_bar_t x, x2;
                uint8_t n1 = NB(&t, 1u), n2 = NB(&t, 2u), n4 = NB(&t, 4u);
                char r[SQ_STEPS + 1u], nt[SQ_STEPS + 1u];
                th_ctx(&t, &x);
                CHECK(x.steps == st && (x.per == 1u || x.per == 2u || x.per == 4u), "the bar the engines see", &t, 255u, st, 0, 0);
                CHECK(n1 == st && (n2 == 2u * st || (2u * st > SQ_STEPS && n2 == st)) && (n4 == 4u * st || (4u * st > SQ_STEPS && n4 == n2)), "one, two, four bars: as many as fit", &t, 255u, st, 0, 0);
                CHECK(n4 % st == 0u && n4 <= SQ_STEPS, "a pattern is bars of the metre", &t, 255u, n4, 0, 0);
                for (s = 0; s < st; s++) {
                    CHECK(x.a16[s] < 16u / x.per, "a step stands for a 16th of the 4/4 bar", &t, 255u, s, 0, 0);
                    CHECK((((x.starts >> s) & 1u) != 0u) == ((x.a16[s] & 3u) == 0u), "a beat begins where the engines' beat begins, nowhere else", &t, 255u, s, 0, 0);
                    CHECK(x.beat[s] <= s && ((x.starts >> x.beat[s]) & 1u), "the beat a step is in", &t, 255u, s, 0, 0);
                }
                CHECK(x.a16[0] == 0u && th_s16(&x, 0u) == 0u && (x.starts & 1u), "the one is the one", &t, 255u, 0u, 0, 0);
                for (s = 0; s < n4; s++) CHECK(th_s16(&x, s) < 16u && th_pos(&x, s) < (uint32_t)st * x.per && th_bpos(&x, s) <= th_pos(&x, s), "a step's place", &t, 255u, s, 0, 0);
                if (seed == 1u) memcpy(a0, x.a16, st);
                else if (memcmp(a0, x.a16, st)) diff = 1u;
                ways |= 1u << (th_u0(&t, 0x7000u, 3u, 1u) & 1u);
                t2 = t; t2.energy = 10u; t2.var = 3u; t2.vary = 100u;      /* (the way is the band's: not the energy's, not a variation's) */
                th_ctx(&t2, &x2);
                CHECK(!memcmp(x.a16, x2.a16, st) && x.starts == x2.starts, "the bar is the band's: the same at every energy, in every variation", &t, 255u, st, 0, 0);
                CHECK(sq_th_part(&t, SQ_FUNC_KICK, n4, r, nt) == n4 && strlen(r) == n4, "a kick in the bar", &t, SQ_FUNC_KICK, n4, r, 0);
            }
            CHECK(ways == 3u, "both ways to feel a bar, over the seeds", 0, 255u, st, 0, 0);
            odd++; both += diff;
        }
    printf("theory: %u bars (3 to 32 steps, every way they divide): %u of them are felt in two ways over the seeds\n", (unsigned)odd, (unsigned)both);
    checks++;
    if (both * 4u < odd) { failed++; printf("FAIL the two ways are the same in nearly every bar: %u of %u\n", (unsigned)both, (unsigned)odd); }
    G_GEN = sv_gen; G_STEPS = sv_st; G_BEATS = sv_bt;
}

/* THE ANSWER HAS NOTES (sq_th_t.mate_nt): a bass under a tune takes the tune's notes - off the beat, where the tune has
 * no attack, the note it had an 8th or a beat before (else its last within a beat), never the major seventh, never a
 * note the style's own line never plays; a tune over chords plays, right after a chord and where the chords are silent,
 * a note of the chord: its third, its fifth, its seventh (the octave when it has none). The RHYTHM is what it was
 * without the notes; a note that is not an answer is the note it was; a part that answers nobody takes no notice; and
 * without `gen`, or without the notes, nothing changes at all. */
static void t_answers(uint32_t seeds)
{
    static const uint8_t DEG[8] = {0u, 4u, 7u, 2u, 6u, 3u, 1u, 5u};
    uint32_t seed, i, k, bass_notes = 0u, bass_ans = 0u, tune_notes = 0u, tune_ans = 0u, bands = 0u, bands_bass = 0u, bands_tune = 0u, moved = 0u, kept = 0u;
    uint8_t st, e;
    for (st = 0; st < SQ_TH_STYLES; st++)
        for (seed = 1; seed <= seeds; seed++) {
            static const uint8_t TUNES[3] = {SQ_FUNC_LEAD, SQ_FUNC_VOX, SQ_FUNC_ARP}, LINES[2] = {SQ_FUNC_BASS, SQ_FUNC_SUB}, CHORDS[3] = {SQ_FUNC_CHORD, SQ_FUNC_PAD, SQ_FUNC_STAB};
            sq_th_t t = th(st, seed, ENERGY[seed % 8u], seed % 2u, (uint8_t)(seed % 90u)), tm, tc;
            th_bar_t x;
            uint8_t n, clev[SQ_STEPS], cnt[SQ_STEPS], tlev[SQ_STEPS], tnt[SQ_STEPS], tune = TUNES[seed % 3u], line = LINES[(seed / 3u) % 2u], chord = CHORDS[(seed / 6u) % 3u];
            char r0[SQ_STEPS + 1u], n0[SQ_STEPS + 1u], r1[SQ_STEPS + 1u], n1[SQ_STEPS + 1u], rt[SQ_STEPS + 1u], ntt[SQ_STEPS + 1u];
            uint16_t mask = sq_scale_mask(sq_harm_scale(t.scale));
            uint8_t got_b = 0u, got_t = 0u;
            if (!t.gen) { t.gen = 1u; t.bar_steps = 16u; t.bar_beats = SQ_BEATS_44; }   /* (in 4/4 too: the notes are the engines' of 0.26) */
            th_ctx(&t, &x);
            n = NB(&t, 4u);
            /* the chords as heard; the tune as heard - hearing the chords, its answers with notes; the bass under it */
            tc = t; tc.energy = 50u;
            sq_th_heard(&tc, chord, n, clev, cnt);
            tm = t; tm.energy = 50u; tm.mate = clev; tm.mate_nt = cnt;
            sq_th_heard(&tm, tune, n, tlev, tnt);
            /* ---- the tune over the chords, at its own energy */
            tm = t; tm.mate = clev; tm.mate_nt = 0;
            sq_th_part(&tm, tune, n, r0, n0);
            tm.mate_nt = cnt;
            sq_th_part(&tm, tune, n, r1, n1);
            if (tune == SQ_FUNC_ARP) CHECK(!strcmp(r0, r1) && !strcmp(n0, n1), "an arpeggio turns the chord: the chords' notes change nothing in it", &tm, tune, n, n0, n1);
            else {
                uint32_t third = th_semi(t.scale, 2u), fifth = th_semi(t.scale, 4u), seventh = th_semi(t.scale, 6u), last = n, last2 = n;
                CHECK(!strcmp(r0, r1), "the notes of the chords changed the tune's rhythm", &tm, tune, n, r0, r1);
                for (i = 0; i < n; i++) if (is_hit(r1[i])) { last = i; if (i >= x.steps && i < 2u * x.steps) last2 = i; }
                for (i = 0; i < n; i++) {
                    int v0 = hexv(n0[i]), v1 = hexv(n1[i]);
                    if (!is_hit(r1[i])) continue;
                    tune_notes++;
                    CHECK(v1 >= 0 && ((mask >> (v1 % 12)) & 1u), "a tune's note out of the key", &tm, tune, n, r1, n1);
                    if (v0 == v1) continue;
                    if (i == last || i == last2) continue;        /* (where a phrase ends the cadence has the last word: home, or bar 2 left open) */
                    {   /* an answer: the chords silent here, struck one to three 16ths before in the pattern; the note is the chord's */
                        uint32_t d, hit = 0u, sev = 0u, pc = (uint32_t)(v1 % 12);
                        for (d = 1u; d <= 3u && d <= i && !hit; d++) if (clev[i - d] >= TH_O) { hit = d; sev = (uint32_t)(cnt[i - d] == 18u || cnt[i - d] == 19u || cnt[i - d] == 20u); }
                        tune_ans++; got_t = 1u;
                        CHECK(clev[i] < TH_O && hit && i % x.steps != 0u, "a tune's note changed where it answers no chord", &tm, tune, n, n0, n1);
                        if (hit == 1u) CHECK(pc == third % 12u, "right after the chord: its third", &tm, tune, n, n0, n1);
                        else if (hit == 2u) CHECK(pc == fifth % 12u, "two 16ths after the chord: its fifth", &tm, tune, n, n0, n1);
                        else if (hit == 3u) CHECK(pc == (sev ? seventh % 12u : 0u), "three 16ths after the chord: its seventh (its octave when it has none)", &tm, tune, n, n0, n1);
                    }
                }
            }
            /* ---- the bass under the tune */
            tm = t; tm.mate = tlev; tm.mate_nt = 0;
            sq_th_part(&tm, line, n, r0, n0);
            tm.mate_nt = tnt;
            sq_th_part(&tm, line, n, r1, n1);
            sq_th_part(&t, tune, n, rt, ntt);
            for (i = 0; i < n; i++) {                    /* (a roll is by the place: the same with and without the notes) */
                CHECK(is_hit(r0[i]) == is_hit(r1[i]) && (r0[i] == '-') == (r1[i] == '-'), "the notes of the tune changed the bass's rhythm", &tm, line, n, r0, r1);
            }
            {
                const th_line_t *m = (const th_line_t *)th_find(TH_LINES, sizeof TH_LINES / sizeof TH_LINES[0], sizeof TH_LINES[0], &t, line, SQ_FUNC_BASS);
                uint32_t canon = 2u + 2u * (th_ub(&t, 0x100u + line, 0x90u, 9u) & 1u);
                for (i = 0; i < n; i++) {
                    int v0 = hexv(n0[i]), v1 = hexv(n1[i]);
                    uint32_t w = 0u, src = n, pc;
                    if (!is_hit(r1[i])) continue;
                    bass_notes++;
                    CHECK(v1 >= 0 && ((mask >> (v1 % 12)) & 1u), "a bass's note out of the key", &tm, line, n, r1, n1);
                    if (v0 == v1) continue;
                    bass_ans++; got_b = 1u;
                    pc = (uint32_t)(v1 % 12);
                    if (canon < n && tlev[(i + n - canon) % n] >= TH_O && tnt[(i + n - canon) % n] < 16u) src = (i + n - canon) % n;
                    for (k = 1u; k <= 4u && k < n && src == n; k++) if (tlev[(i + n - k) % n] >= TH_O && tnt[(i + n - k) % n] < 16u) src = (i + n - k) % n;
                    CHECK(tlev[i] < TH_O && !th_onbeat(&x, i), "a bass's note changed on a beat, or under an attack of the tune", &tm, line, n, n0, n1);
                    CHECK(src != n && (uint32_t)tnt[src] % 12u == pc, "the bass's answer is not the tune's note", &tm, line, n, n1, 0);
                    CHECK(pc != 11u, "the bass took a major seventh", &tm, line, n, n1, 0);
                    for (k = 0; k < 8u; k++) if ((DEG[k] == 7u ? 0u : th_semi(t.scale, DEG[k]) % 12u) == pc) w += m->tone[k];
                    CHECK(w > 0u, "the bass took a note its style never plays", &tm, line, n, n1, 0);
                    CHECK(v1 < 12, "the bass's answer is not in its own octave", &tm, line, n, n1, 0);
                }
            }
            /* ---- the energy: the other part held still, a note that stays keeps its pitch - an answer too (by its place) */
            for (e = 0; e < 8u; e++) {
                sq_th_t t2 = tm;
                t2.energy = ENERGY[e];
                sq_th_part(&t2, line, n, r1, n1);
                if (e) for (i = 0; i < n; i++) if (is_hit(r0[i]) && is_hit(r1[i])) { kept++; if (n0[i] != n1[i]) moved++; }
                memcpy(r0, r1, sizeof r0); memcpy(n0, n1, sizeof n0);
            }
            /* ---- who answers nobody takes no notice of the notes; without `gen` the notes are not looked at */
            {
                sq_th_t ta = t;
                ta.mate = tlev; ta.mate_nt = 0;
                sq_th_part(&ta, chord, n, r0, n0);
                ta.mate_nt = tnt;
                sq_th_part(&ta, chord, n, r1, n1);
                CHECK(!strcmp(r0, r1) && !strcmp(n0, n1), "the chords answer nobody: notes or not", &ta, chord, n, n0, n1);
                if (x.steps == 16u && x.per == 1u && x.starts == SQ_BEATS_44) {
                    ta = t; ta.gen = 0u; ta.bar_steps = 0u; ta.bar_beats = 0u; ta.mate = tlev; ta.mate_nt = 0;
                    sq_th_part(&ta, line, n, r0, n0);
                    ta.mate_nt = tnt;
                    sq_th_part(&ta, line, n, r1, n1);
                    CHECK(!strcmp(r0, r1) && !strcmp(n0, n1), "the engines of 0.25 do not look at the notes", &ta, line, n, n0, n1);
                }
            }
            bands++; bands_bass += got_b; bands_tune += got_t;
        }
    printf("theory: the answers have notes: of %u notes of a bass under a tune, %u are the tune's (in %u bands of %u); of %u notes of a tune over chords, %u are the chord's (in %u bands);"
           " of %u bass notes that stay as the energy rises, %u change pitch\n", (unsigned)bass_notes, (unsigned)bass_ans, (unsigned)bands_bass, (unsigned)bands,
           (unsigned)tune_notes, (unsigned)tune_ans, (unsigned)bands_tune, (unsigned)kept, (unsigned)moved);
    checks += 3u;
    if (bass_ans * 100u < bass_notes) { failed++; printf("FAIL the bass hardly ever takes a note of the tune\n"); }
    if (tune_ans * 100u < tune_notes) { failed++; printf("FAIL the tune hardly ever plays the chord's notes\n"); }
    if (moved * 100u > kept * 3u) { failed++; printf("FAIL the bass's notes move with the energy: %u of %u\n", (unsigned)moved, (unsigned)kept); }
}

/* the whole battery in one bar */
static void battery(uint32_t seeds, const char *what)
{
    unsigned long c0 = checks, f0 = failed;
    t_library(seeds);
    t_text(seeds);
    t_anchors(seeds);
    t_styles(seeds);
    t_energy(seeds);
    t_variation(seeds);
    t_band();
    t_mate(seeds > 60u ? 60u : seeds);
    t_answers(seeds > 60u ? 60u : seeds);
    printf("theory: %s: %lu checks, %lu failed\n", what, checks - c0, failed - f0);
}

int main(int argc, char **argv)
{
    uint32_t seeds = argc > 1 ? (uint32_t)strtoul(argv[1], 0, 0) : 120u, small = seeds / 6u ? seeds / 6u : 1u;
    static const struct { uint8_t steps, opt; const char *name; } BARS_T[] = {
        {14u, 0u, "7/8"}, {14u, 1u, "7/8, another way"}, {14u, 2u, "7/8, a third way"}, {20u, 0u, "5/4"}, {12u, 0u, "12 steps (3/4 or 6/8), the usual way"},
        {12u, 1u, "12 steps, the other way"}, {10u, 0u, "5/8"}, {10u, 1u, "5/8, the other way"}, {18u, 0u, "9/8"}, {24u, 0u, "24 steps (12/8 or 6/4)"}, {22u, 0u, "11/8"},
        {28u, 0u, "7/4"}, {8u, 0u, "2/4"}, {6u, 0u, "3/8"}, {15u, 0u, "15/16"}, {16u, 1u, "16 steps, not four quarters"}, {32u, 0u, "32 steps"}, {3u, 0u, "3 steps"}};
    const char *only = argc > 2 ? argv[2] : 0;           /* (a bar alone, by a piece of its name: "7/8", "5/4" ...) */
    uint32_t k;
    if (!only) {
        t_counted();
        t_prog(seeds);
        t_golden();
        t_bars();
        battery(seeds, "4/4, the engines of 0.25");
        G_GEN = 1u; G_STEPS = 16u; G_BEATS = SQ_BEATS_44;
        battery(small, "4/4, made in the bar");
    }
    G_GEN = 1u;
    for (k = 0; k < sizeof BARS_T / sizeof BARS_T[0]; k++) {
        char sig[8], split[SQ_SPLIT_TEXT], what[80];
        if (BARS_T[k].opt >= sq_metre_options(BARS_T[k].steps) || (only && !strstr(BARS_T[k].name, only))) continue;
        G_STEPS = BARS_T[k].steps; G_BEATS = sq_metre_option(G_STEPS, BARS_T[k].opt);
        sq_metre_sig(G_STEPS, G_BEATS, sig); sq_metre_split(G_STEPS, G_BEATS, split);
        snprintf(what, sizeof what, "%s (%s, %s)", BARS_T[k].name, sig, split);
        battery(only ? seeds : k < 4u ? (seeds / 3u ? seeds / 3u : 1u) : small, what);
    }
    G_GEN = 0u; G_STEPS = 16u; G_BEATS = SQ_BEATS_44;
    if (failed) { printf("theory: %lu of %lu checks FAILED\n", failed, checks); return 1; }
    printf("theory: all %lu checks passed (%u seeds a style)\n", checks, (unsigned)seeds);
    return 0;
}
