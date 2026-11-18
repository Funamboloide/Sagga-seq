/* SPDX-License-Identifier: GPL-3.0-only
 * SAGGA SEQ: what the THEORY engines make, as text (the library's own notation), on a computer.
 *   sagga_theory STYLE SEED [VAR VARY ENERGY LEN] [PART ...]
 *   sagga_theory --rules        the rules of every style, a line each (tools/theory/regole.py writes them out in words)
 * STYLE: a genre of the FM-1 by its name (TECHNO, "UK GARAGE" or UKGARAGE, DNB ...) or its number 0..24, or FREE (25).
 * No PART: the style's band (sq_th_band) and its chords.
 *   cc -std=c11 -O2 -Ifirmware/src tools/theory/sagga_theory.c firmware/src/sagga_seq_core.c firmware/src/sagga_beats.c \
 *      -o build/sagga_theory
 * The engine is included, not linked: --rules reads its tables. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../../firmware/src/sagga_theory.c"

static uint8_t func_of(const char *name)
{
    uint8_t f;
    for (f = 0; f < SQ_FUNCS; f++) {
        char b[16];
        const char *n = sq_func_name(f);
        size_t i, j = 0;
        for (i = 0; n[i] && j < 15u; i++) if (n[i] != ' ') b[j++] = n[i];
        b[j] = 0;
        if (!strcmp(b, name) || !strcmp(n, name)) return f;
    }
    if (!strcmp(name, "OHAT")) return SQ_FUNC_OHAT;
    if (!strcmp(name, "LOGDRUM")) return SQ_FUNC_LOGDRUM;
    return 255u;
}

/* a style by its name (spaces and signs do not count, nor the case), by its number, or DNB */
static uint8_t style_of(const char *name)
{
    uint8_t st;
    char want[24];
    size_t i, j = 0;
    for (i = 0; name[i] && j < 23u; i++) if ((name[i] >= 'A' && name[i] <= 'Z') || (name[i] >= '0' && name[i] <= '9')) want[j++] = name[i];
        else if (name[i] >= 'a' && name[i] <= 'z') want[j++] = (char)(name[i] - 32);
    want[j] = 0;
    if (j && want[0] >= '0' && want[0] <= '9') { unsigned long v = strtoul(want, 0, 10); return (uint8_t)(v < SQ_TH_STYLES ? v : 255u); }
    if (!strcmp(want, "DNB") || !strcmp(want, "DRUMANDBASS")) return SQ_TH_DNB;
    for (st = 0; st < SQ_TH_STYLES; st++) {
        char b[24];
        const char *n = sq_th_name(st);
        j = 0;
        for (i = 0; n[i] && j < 23u; i++) if ((n[i] >= 'A' && n[i] <= 'Z') || (n[i] >= '0' && n[i] <= '9')) b[j++] = n[i];
        b[j] = 0;
        if (!strcmp(b, want)) return st;
    }
    return 255u;
}

static void bits(uint16_t m, char on)
{
    uint32_t s;
    for (s = 0; s < 16u; s++) putchar((m >> s) & 1u ? on : '.');
}
static void list(const uint8_t *v, uint32_t n)
{
    uint32_t i;
    for (i = 0; i < n; i++) printf("%s%u", i ? "," : "", (unsigned)v[i]);
}

/* every table of the engine, a line a rule, tab-separated: R a rhythm, L a line, M a motif, C chords, P a progression */
static void rules(void)
{
    uint32_t i, s;
    for (i = 0; i < sizeof TH_RULES / sizeof TH_RULES[0]; i++) {
        const th_rule_t *q = &TH_RULES[i];
        printf("R\t%s\t%s\t%u\t", q->style == 255u ? "+" : sq_th_name(q->style), sq_func_name(q->func), (unsigned)q->pick);   /* (+: the even bars of the rule before) */
        bits(q->fixA, 'X'); putchar('\t'); bits(q->fixx, 'x'); putchar('\t'); bits(q->never, 'x'); putchar('\t');
        for (s = 0; s < 16u; s++) { uint32_t w = th_nib(q->w, s); putchar(w ? (char)(w < 10u ? '0' + w : 'a' + (w - 10u)) : '.'); }
        printf("\t%u\t%u\t%u\t%u\t", (unsigned)q->d_lo, (unsigned)q->d_hi, (unsigned)q->soft, (unsigned)q->soft_lev);
        list(q->cls, 4u);
        printf("\t%u\t%u,%u,%u,%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t", (unsigned)q->cls_e0, 1u + (q->cls_lev & 3u), 1u + ((q->cls_lev >> 2) & 3u),
               1u + ((q->cls_lev >> 4) & 3u), 1u + ((q->cls_lev >> 6) & 3u), (unsigned)q->cls_link, (unsigned)q->hole, (unsigned)(q->cyc & 15u),
               (unsigned)(q->cyc >> 4), (unsigned)q->bar2, (unsigned)q->fill, (unsigned)(q->kick & 15u), (unsigned)(q->kick >> 4));
        /* ... and what only a rule counted from the library has: from energy TH_DATA_MID_E, the rolls, the levels by place */
        bits(q->mid, 'x'); putchar('\t'); bits(q->rollm, 'x'); putchar('\t');
        for (s = 0; s < 16u; s++) putchar("xXog"[(q->lv >> (2u * s)) & 3u]);
        printf("\t%u\t%u\n", (unsigned)(q->roll >> 6) + 1u, (unsigned)(q->roll & 63u) << 2);
    }
    for (i = 0; i < sizeof TH_LINES / sizeof TH_LINES[0]; i++) {
        const th_line_t *m = &TH_LINES[i];
        printf("L\t%s\t%s\t", sq_th_name(m->style), sq_func_name(m->func));
        list(m->tone, 8u);
        printf("\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\n", (unsigned)m->first_root, (unsigned)m->strong, (unsigned)m->octpair, (unsigned)m->pair,
               (unsigned)m->same, (unsigned)m->turn, (unsigned)m->hold, (unsigned)m->hold_max, (unsigned)m->gap, (unsigned)m->roll);
    }
    for (i = 0; i < sizeof TH_LEADS / sizeof TH_LEADS[0]; i++) {
        const th_lead_t *m = &TH_LEADS[i];
        printf("M\t%s\t%s\t%u\t", sq_th_name(m->style), sq_func_name(m->func), (unsigned)m->penta);
        list(m->shape, 4u);
        printf("\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t", (unsigned)m->span_lo, (unsigned)m->span_hi, (unsigned)m->rep, (unsigned)m->jit,
               (unsigned)m->leap, (unsigned)m->chord, (unsigned)m->off, (unsigned)m->cad, (unsigned)m->hold, (unsigned)m->hold_max, (unsigned)m->gap);
        list(m->cw, 3u);
        printf("\t%u\n", (unsigned)m->hi);
    }
    for (i = 0; i < sizeof TH_CHORDS / sizeof TH_CHORDS[0]; i++) {
        const th_chord_t *m = &TH_CHORDS[i];
        printf("C\t%s\t%s\t", sq_th_name(m->style), sq_func_name(m->func));
        list(m->kind, 4u);
        printf("\t%u\t%u\t%u\t%u\n", (unsigned)m->same, (unsigned)m->hold, (unsigned)m->hold_max, (unsigned)m->gap);
    }
    for (i = 0; i < SQ_TH_STYLES; i++) {
        const th_prog_t *p = &TH_PROGS[i];
        printf("P\t%s\t", sq_th_name((uint8_t)i));
        list(p->n_w, 4u); putchar('\t'); list(p->bars_w, 4u); putchar('\t'); list(p->move_w, 6u);
        printf("\t%u\t", (unsigned)p->first);
        list(p->last_w, 7u); putchar('\t'); list(p->col_w, SQ_HCS);
        printf("\t%u\t", (unsigned)p->col_same);
        list(p->scale_w, 6u); putchar('\t'); list(p->push_w, 3u); putchar('\n');
    }
}

int main(int argc, char **argv)
{
    sq_th_t t;
    sq_uprog_t u;
    uint8_t parts[SQ_TH_BAND_MAX + 8u], n = 0u, i, len = 64u, st;
    char name[40];
    const char *mate_style = 0, *mate_seed = 0, *mate_part = 0;
    if (argc == 2 && !strcmp(argv[1], "--rules")) { rules(); return 0; }
    if (argc > 5 && !strcmp(argv[1], "--mate")) {        /* 0.25: the part the parts answer is of another style and seed (a track that was there) */
        mate_style = argv[2]; mate_seed = argv[3]; mate_part = argv[4];
        argv += 4; argc -= 4;
    }
    if (argc < 3) { fprintf(stderr, "usage: sagga_theory STYLE SEED [VAR VARY ENERGY LEN] [PART ...]\n       sagga_theory --rules\n"
                                    "the parts given (else the style's band) are the tracks in their order: each answers the first other one of the family it answers\n"
                                    "       sagga_theory --mate STYLE SEED PART STYLE SEED ...   the part they answer is that one (a track of another band)\n"); return 2; }
    memset(&t, 0, sizeof t);
    st = style_of(argv[1]);
    if (st == 255u) { fprintf(stderr, "no such style: %s\n", argv[1]); return 2; }
    t.style = st;
    t.seed = (uint32_t)strtoul(argv[2], 0, 0);
    t.var = argc > 3 ? (uint32_t)strtoul(argv[3], 0, 0) : 0u;
    t.vary = (uint8_t)(argc > 4 ? atoi(argv[4]) : 0);
    t.energy = (uint8_t)(argc > 5 ? atoi(argv[5]) : 60);
    if (argc > 6) len = (uint8_t)atoi(argv[6]);
    t.scale = sq_th_scale(&t);
    if (argc > 7) {
        int a;
        for (a = 7; a < argc && n < sizeof parts; a++) { uint8_t f = func_of(argv[a]); if (f != 255u) parts[n++] = f; }
    } else n = sq_th_band(st, parts);
    sq_th_prog(&u, &t);
    sq_uprog_name(&u, t.scale, name, sizeof name);
    {
        uint16_t lo, hi;
        sq_genre_bpm(sq_th_genre(st) != 255u ? sq_th_genre(st) : SQ_GENRE_TECHNO, &lo, &hi);
        printf("# %s seed %u var %u vary %u energy %u: %u BPM, key %s %s, chords %s, %u bars a chord, push %u\n", sq_th_name(st), (unsigned)t.seed,
               (unsigned)t.var, (unsigned)t.vary, (unsigned)t.energy, (unsigned)(sq_th_genre(st) != 255u ? (lo + hi) / 2u : 120u),
               sq_root_name(sq_th_root(&t)), sq_scale_name(t.scale), name, (unsigned)u.bars, (unsigned)u.push[0]);
    }
    for (i = 0; i < n; i++) {
        char r[SQ_STEPS + 1u], nt[SQ_STEPS + 1u];
        uint8_t lev[SQ_STEPS], fam = sq_th_mate_family(parts[i]), k;
        /* 0.25 THE PARTS LISTEN: a part answers the first OTHER part of the list (the tracks, in their order) that is
         * of the family it answers, as that one is at half the energy - what the FM-1 does with the tracks of a band.
         * A part alone on the command line answers nobody. */
        t.mate = 0;
        if (mate_part && fam != 255u && func_of(mate_part) != 255u && sq_func_family(func_of(mate_part)) == fam && style_of(mate_style) != 255u) {
            sq_th_t m;
            uint8_t j, any = 0u;
            memset(&m, 0, sizeof m);
            m.style = style_of(mate_style); m.seed = (uint32_t)strtoul(mate_seed, 0, 0); m.energy = 50u; m.scale = t.scale;
            sq_th_levels(&m, func_of(mate_part), len, lev);
            for (j = 0; j < SQ_STEPS; j++) if (lev[j]) any = 1u;
            if (any) t.mate = lev;
            fam = 255u;
        }
        for (k = 0; k < n && fam != 255u; k++) {
            sq_th_t m = t;
            uint8_t j, any = 0u;
            if (k == i || sq_func_family(parts[k]) != fam) continue;
            m.energy = 50u; m.kick = 0; m.mate = 0;
            sq_th_levels(&m, parts[k], len, lev);
            for (j = 0; j < SQ_STEPS; j++) if (lev[j]) any = 1u;
            if (any) t.mate = lev;
            break;
        }
        if (!sq_th_part(&t, parts[i], len, r, nt)) continue;
        printf("%s\t%s\t%s\n", sq_func_name(parts[i]), r, nt[0] ? nt : "-");
    }
    return 0;
}
