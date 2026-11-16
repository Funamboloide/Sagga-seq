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
static sq_th_t th(uint8_t style, uint32_t seed, uint8_t energy, uint32_t var, uint8_t vary)
{
    sq_th_t t;
    memset(&t, 0, sizeof t);
    t.style = style; t.seed = seed; t.energy = energy;
    t.scale = sq_th_scale(&t);
    t.var = var; t.vary = vary;
    return t;
}
static const uint8_t ENERGY[8] = {0u, 10u, 25u, 40u, 60u, 75u, 90u, 100u};
static const uint8_t LENS[3] = {16u, 32u, 64u};
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
                    uint8_t len = LENS[li], kind = sq_func_kind(f), n, loud = 0u;
                    char r[SQ_STEPS + 1u], nt[SQ_STEPS + 1u], r2[SQ_STEPS + 1u], nt2[SQ_STEPS + 1u];
                    sq_step_t row[SQ_STEPS];
                    sq_th_t t;
                    uint32_t i;
                    uint16_t mask;
                    e = ENERGY[(seed + f + li) % 8u];
                    t = th(st, seed, e, (seed % 3u) ? 0u : seed, (uint8_t)((seed * 7u) % 101u));
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
                            for (i = 0; i < len; i++) if (((th_fix(&t, q, i) >> (i & 15u)) & 1u || th_nib(th_bar(q, i)->w, i & 15u)) && th_level(q, 15u, i) >= TH_O) can = 1u;
                        }
                        for (i = 0; i < len; i++) if (is_hit(r[i])) any = 1u;
                        CHECK(can ? loud : any, "a part is never empty", &t, f, len, r, nt);
                    }
                    CHECK(sq_th_load(row, &t, f, len, 60u) == len, "the firmware loads it", &t, f, len, r, nt);
                    /* the same again, after other parts were made: nothing depends on the order */
                    sq_th_part(&t, (uint8_t)((f + 3u) % SQ_FUNC_PROG), 64u, r2, nt2);
                    sq_th_part(&t, f, len, r2, nt2);
                    CHECK(!strcmp(r, r2) && !strcmp(nt, nt2), "the same seed, the same part", &t, f, len, r, r2);
                }
}

/* what a style says is always there is there, what it says never is never is: at every energy, in every variation
 * (the last bar apart: the fill may move the last snare) */
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
                    char r[SQ_STEPS + 1u], nt[SQ_STEPS + 1u];
                    if (f == SQ_FUNC_PROG || f == SQ_FUNC_KIT || f == SQ_FUNC_CRASH) continue;
                    q = th_rule(&t, f);
                    sq_th_part(&t, f, 64u, r, nt);
                    th_rhythm(&t, SQ_FUNC_KICK, 4u, &kick);
                    for (i = 0; i < 48u; i++) {
                        uint16_t bit = (uint16_t)(1u << (i & 15u));
                        uint8_t avoided = (uint8_t)((q->kick & 15u) == TH_K_AVOID && kick.lev[i]);
                        if ((th_bar(q, i)->never & bit) || avoided) CHECK(!is_hit(r[i]), "a hit where the style has none", &t, f, 64u, r, nt);
                        else if (q->kick & TH_K_LV) {   /* (counted from the library: at its place's own level, a roll apart) */
                            static const char LV[5] = {'.', 'g', 'o', 'x', 'X'};
                            if (th_fix(&t, q, i) & bit) CHECK(r[i] == LV[th_level(q, 15u, i)] || (r[i] >= '2' && r[i] <= '4' && (th_bar(q, i)->rollm & bit)), "what a family always plays", &t, f, 64u, r, nt);
                        }
                        else if (q->fixA & bit) CHECK(r[i] == 'X' || (r[i] >= '2' && r[i] <= '4'), "the accent that is always there", &t, f, 64u, r, nt);
                        else if (q->fixx & bit) CHECK(is_loud(r[i]), "the hit that is always there", &t, f, 64u, r, nt);
                    }
                }
}

/* the styles, said plainly (what the rules above must come to) */
static void t_styles(uint32_t seeds)
{
    uint32_t seed, b;
    uint8_t e;
    for (seed = 1; seed <= seeds; seed++)
        for (e = 0; e < 8u; e++) {
            char r[SQ_STEPS + 1u], k[SQ_STEPS + 1u], nt[SQ_STEPS + 1u];
            sq_th_t t = th(SQ_TH_TECHNO, seed, ENERGY[e], 0u, 0u);
            uint32_t i;
            sq_th_part(&t, SQ_FUNC_KICK, 64u, k, nt);
            for (b = 0; b < 4u; b++) CHECK(k[b * 16u] == 'X' && k[b * 16u + 4u] == 'X' && k[b * 16u + 8u] == 'X' && k[b * 16u + 12u] == 'X', "techno: four on the floor", &t, SQ_FUNC_KICK, 64u, k, 0);
            sq_th_part(&t, SQ_FUNC_RUMBLE, 64u, r, nt);
            for (i = 0; i < 64u; i++) CHECK(!(is_hit(r[i]) && is_hit(k[i])), "techno: the rumble is never on a kick", &t, SQ_FUNC_RUMBLE, 64u, r, k);
            sq_th_part(&t, SQ_FUNC_HAT, 64u, r, nt);
            for (b = 0; b < 3u; b++) CHECK(is_loud(r[b * 16u + 2u]) && is_loud(r[b * 16u + 6u]) && is_loud(r[b * 16u + 10u]) && is_loud(r[b * 16u + 14u]), "techno: the hat on the off-beats", &t, SQ_FUNC_HAT, 64u, r, 0);
            t = th(SQ_TH_HOUSE, seed, ENERGY[e], 0u, 0u);
            sq_th_part(&t, SQ_FUNC_KICK, 64u, k, nt);
            for (b = 0; b < 4u; b++) CHECK(k[b * 16u] == 'X' && k[b * 16u + 4u] == 'X' && k[b * 16u + 8u] == 'X' && k[b * 16u + 12u] == 'X', "house: four on the floor", &t, SQ_FUNC_KICK, 64u, k, 0);
            sq_th_part(&t, SQ_FUNC_CLAP, 64u, r, nt);
            for (b = 0; b < 3u; b++) CHECK(r[b * 16u + 4u] == 'X' && r[b * 16u + 12u] == 'X', "house: the clap on 2 and 4", &t, SQ_FUNC_CLAP, 64u, r, 0);
            t = th(SQ_TH_DNB, seed, ENERGY[e], 0u, 0u);
            sq_th_part(&t, SQ_FUNC_KICK, 64u, k, nt);
            sq_th_part(&t, SQ_FUNC_SNARE, 64u, r, nt);
            for (b = 0; b < 3u; b++) CHECK(k[b * 16u] == 'X' && is_loud(k[b * 16u + 10u]) && r[b * 16u + 4u] == 'X' && r[b * 16u + 12u] == 'X', "drum and bass: the two-step", &t, SQ_FUNC_SNARE, 64u, k, r);
            t = th(SQ_TH_DUBSTEP, seed, ENERGY[e], 0u, 0u);
            sq_th_part(&t, SQ_FUNC_KICK, 64u, k, nt);
            sq_th_part(&t, SQ_FUNC_SNARE, 64u, r, nt);
            for (b = 0; b < 3u; b++) CHECK(k[b * 16u] == 'X' && r[b * 16u + 8u] == 'X' && !is_loud(r[b * 16u + 4u]) && !is_loud(r[b * 16u + 12u]), "dubstep: half-time, the snare on 3", &t, SQ_FUNC_SNARE, 64u, k, r);
            sq_th_part(&t, SQ_FUNC_SUB, 64u, r, nt);
            for (b = 0; b < 4u; b++) CHECK(r[b * 16u] == 'X', "dubstep: the sub on the one", &t, SQ_FUNC_SUB, 64u, r, nt);
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
                    uint8_t avoid = (uint8_t)((th_rule(&t, f)->kick & 15u) == TH_K_AVOID);
                    sq_th_part(&t, f, 64u, r1, n1);
                    sq_th_part(&t, SQ_FUNC_KICK, 64u, k1, kn);
                    if (e)
                        for (i = 0; i < 64u; i++) {
                            if (!is_hit(r0[i])) continue;
                            if (avoid && is_hit(k1[i])) continue;
                            CHECK(is_hit(r1[i]), "a hit lost as the energy rises", &t, f, 64u, r0, r1);
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
                if (f == SQ_FUNC_PROG || f == SQ_FUNC_KIT) continue;
                sq_th_part(&t, f, 64u, r, nt);
                t2 = t; t2.var = 5u; t2.vary = 0u;
                sq_th_part(&t2, f, 64u, r2, nt2);
                CHECK(!strcmp(r, r2) && !strcmp(nt, nt2), "a variation of 0 % changes nothing", &t2, f, 64u, r, r2);
                t2 = t; t2.var = 0u; t2.vary = 80u;
                sq_th_part(&t2, f, 64u, r2, nt2);
                CHECK(!strcmp(r, r2) && !strcmp(nt, nt2), "variation 0 is the seed's own", &t2, f, 64u, r, r2);
                for (v = 0; v < 5u; v++) {
                    t2 = t; t2.var = 1u + seed % 7u; t2.vary = VARY[v];
                    CHECK(th_rule(&t2, f) == th_rule(&t, f), "a variation keeps the family", &t2, f, 64u, 0, 0);
                    sq_th_part(&t2, f, 64u, r2, nt2);
                    for (i = 0; i < 64u; i++) if (r[i] != r2[i] || (nt[0] && nt[i] != nt2[i])) dist[v]++;
                }
                total += 64u;
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
            CHECK(sq_th_part(&t, funcs[i], 64u, r, nt) == 64u, "a part of the band", &t, funcs[i], 64u, 0, 0);
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
                    sq_th_part(&t, f, 64u, r, nt);
                    for (i = 0; i < 48u; i++) if ((all >> (i & 15u)) & 1u) CHECK(is_hit(r[i]), "what the library always plays", &t, f, 64u, r, nt);
                }
        }
    }
}

int main(int argc, char **argv)
{
    uint32_t seeds = argc > 1 ? (uint32_t)strtoul(argv[1], 0, 0) : 120u;
    t_counted();
    t_library(seeds);
    t_text(seeds);
    t_anchors(seeds);
    t_styles(seeds);
    t_energy(seeds);
    t_variation(seeds);
    t_prog(seeds);
    t_band();
    if (failed) { printf("theory: %lu of %lu checks FAILED\n", failed, checks); return 1; }
    printf("theory: all %lu checks passed (%u seeds a style)\n", checks, (unsigned)seeds);
    return 0;
}
