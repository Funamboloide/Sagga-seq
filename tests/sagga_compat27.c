/* SPDX-License-Identifier: GPL-3.0-only */
/* 0.28: a project goes 0.28 -> 0.27 -> 0.28 and comes back the same, but for what 0.27 has no room for (the notes 5-6,
 * the lanes 7-8 and their settings). Built twice by tests/sagga_compat27.sh: against this core ("write", "check") and
 * against 0.27's as released ("relay", -DOLD27). The projects: many, each made of chance bytes put right by the
 * sanitizer, so that every field of the image is something.
 *   write DIR   the projects as 0.28 saves them (c28_N), and what 0.27 can keep of them, as 0.28 saves it (e28_N)
 *   relay DIR   0.27 opens c28_N, checks it whole, and saves it again (c27_N)
 *   check DIR   0.28 opens c27_N: the project of e28_N, byte for byte */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sagga_seq_core.h"
#ifndef OLD27
#include "sagga_compat_lt30.h"                /* (0.30: what a firmware before it keeps) */
#endif

#define PROJECTS 60u
static sq_project_t a, b;
static uint8_t img[600000];
static uint32_t rs;
static uint32_t rnd(void) { rs = rs * 1103515245u + 12345u; return rs >> 8; }

static int put(const char *dir, const char *what, uint32_t k, const uint8_t *p, uint32_t n)
{
    char path[512];
    FILE *f;
    snprintf(path, sizeof path, "%s/%s_%u", dir, what, k);
    if (!(f = fopen(path, "wb")) || fwrite(p, 1, n, f) != n) { printf("compat: cannot write %s\n", path); return -1; }
    fclose(f);
    return 0;
}
static long get(const char *dir, const char *what, uint32_t k, uint8_t *p, uint32_t cap)
{
    char path[512];
    FILE *f;
    long n;
    snprintf(path, sizeof path, "%s/%s_%u", dir, what, k);
    if (!(f = fopen(path, "rb"))) { printf("compat: cannot read %s\n", path); return -1; }
    n = (long)fread(p, 1, cap, f);
    fclose(f);
    return n;
}

#define OLD_PROJECTS 20u
#ifdef OLD27
/* a project of 0.27 with something on all sixteen tracks: notes, a tape on 15, an LFO aimed at track 15, the mutes */
static void old_fill(sq_project_t *p, uint32_t seed)
{
    uint8_t *q = (uint8_t *)p->step;
    uint32_t i, t;
    rs = seed * 2246822519u;
    sq_project_init(p);
    for (i = 0; i < sizeof p->step; i++) if (rnd() % 11u == 0u) q[i] = (uint8_t)rnd();
    for (t = 0; t < 16u; t++)                         /* (a copy is a run of steps, never chance bits: the image keeps runs) */
        for (i = 0; i < 8u * 64u; i++) p->step[t][i / 64u][i % 64u].flags &= (uint8_t)~SQ_STEP_GHOST;
    for (t = 0; t < 16u; t++) { p->step[t][0][t].flags = SQ_STEP_ON | SQ_STEP_SET; p->step[t][0][t].note[0] = (uint8_t)(40u + t); }
    sq_tape_add(p, 2u, 100u, 50u, 60u, 90u);
    sq_tape_add(p, 14u, 200u, 50u, 61u, 91u);
    sq_tape_add(p, 15u, 300u, 50u, 62u, 92u);
    p->lfo[0].enabled = 1u; p->lfo[0].dest = SQ_LD_VEL; p->lfo[0].target = 14u;
    p->lfo[1].enabled = 1u; p->lfo[1].dest = SQ_LD_GATE; p->lfo[1].target = (uint8_t)(seed % 12u);
    p->scene[0].mute_mask = (uint16_t)(0xF00Fu ^ (seed << 4));
    sq_project_sanitize(p);
}
#endif

#ifndef OLD27
static void fill(sq_project_t *p, uint32_t seed)
{
    uint8_t *q = (uint8_t *)p;
    uint32_t i, every = 3u + seed % 9u;               /* (some projects nearly empty, some full) */
    rs = seed * 2654435761u;
    sq_project_init(p);
    for (i = 0; i < sizeof *p; i++) if (rnd() % (every * 4u) == 0u) q[i] = (uint8_t)rnd();
    sq_project_sanitize(p);
}
/* 0.29: a genre as it comes back from a firmware of 0.28 or before (its own numbers, no chunk 5): BALANI as GQOM */
static uint8_t via_old(uint8_t g) { return sq_genre_from28(sq_genre_to28(g), 0u); }
/* what 0.27 keeps: the notes 5-6 and the lanes 7-8 gone, their settings the defaults; 0.29: BALANI is GQOM */

#ifndef OLD27
/* 0.29: what 0.28 keeps of what 0.29 added - two MIDI effects (0.28's block holds the nine: ROLL off, ACCENT's values the
 * defaults, the two where the default order has them), five scales (CHROMATIC), three grooves (OFF), four chord shapes
 * (OFF; in a progression the key's triad) */
static void mfxd_via28(sq_mfxd_t *d)
{
    sq_mfxd_t x;
    uint32_t k, n = 0u;
    uint8_t o9[9];
    for (k = 0; k < SQ_MFX_ALLN && n < 9u; k++) if (d->order[k] < SQ_MFXS_020) o9[n++] = d->order[k];
    sq_mfxd_default(&x);
    x.on = (uint8_t)(d->on & 0x1Fu);
    for (k = 0, n = 0u; k < 9u; k++) {
        if (o9[k] == SQ_MFX_ECHO) x.order[n++] = SQ_MFX_ROLL;
        x.order[n++] = o9[k];
        if (o9[k] == SQ_MFX_VELOCITY) x.order[n++] = SQ_MFX_ACCENT;
    }
    for (k = 0; k < 5u; k++) { x.amt[k] = d->amt[k]; x.time[k] = d->time[k]; x.fb[k] = d->fb[k]; }
    sq_mfxd_sanitize(&x);
    *d = x;
}
static void more_via28(sq_project_t *p)
{
    uint32_t t, k, s;
    for (t = 0; t < SQ_TRACKS; t++) {
        mfxd_via28(&p->ext.mfxd[t]);
        if (p->ext.track[t].groove >= SQ_GROOVES28) p->ext.track[t].groove = SQ_GROOVE_OFF;
        if (p->track[t].chord >= SQ_CH_COUNT28) p->track[t].chord = SQ_CH_OFF;
    }
    if (p->key_scale >= SQ_SCALES28) p->key_scale = SQ_SC_CHROMATIC;
    for (k = 0; k < sizeof p->key / sizeof p->key[0]; k++) if (p->key[k].scale >= SQ_SCALES28) p->key[k].scale = SQ_SC_CHROMATIC;
    for (k = 0; k < SQ_UPROG_SLOTS; k++) for (s = 0; s < SQ_HPROG_CH; s++) if (p->uprog[k].shape[s] >= SQ_HSHAPE_CH + SQ_CH_COUNT28) p->uprog[k].shape[s] = SQ_HC_TRIAD;
    for (s = 0; s < SQ_SNAPS; s++) {
        if (!p->snap[s].used) continue;
        if (p->snap[s].key_scale >= SQ_SCALES28) p->snap[s].key_scale = SQ_SC_CHROMATIC;
        for (t = 0; t < SQ_TRACKS; t++) if (p->snap[s].track[t].chord >= SQ_CH_COUNT28) p->snap[s].track[t].chord = SQ_CH_OFF;
    }
}
#endif

static void strip(sq_project_t *p)
{
    uint32_t t, pat, i, k, s;
    sq_track_cfg_t d;
    p->gen.genre = via_old(p->gen.genre); p->gen.harm_genre = via_old(p->gen.harm_genre); p->viaggio.set_genre = via_old(p->viaggio.set_genre);
    p->gen.harm_prog = sq_prog_from28(sq_prog_to28(p->gen.harm_prog));      /* (0.29: a genre's 7th and 8th progression: 0.27 has six) */
    less_than_30(p);                                 /* (0.30: scenes 17-32, snapshots 9-16, the long song and tapes) */
    more_via28(p);
    for (t = 0; t < SQ_TRACKS; t++) {
        p->track[t].src_genre = via_old(p->track[t].src_genre);
        for (pat = 0; pat < SQ_PATTERNS; pat++) {
            sq_thpat_t *m = &p->th.pat[t][pat];
            if (m->style & 31u) m->style = (uint8_t)((m->style & ~31u) | ((via_old((uint8_t)((m->style & 31u) - 1u)) + 1u) & 31u));
        }
    }
    for (s = 0; s < SQ_SNAPS; s++) {
        if (!p->snap[s].used) continue;
        p->snap[s].genre = via_old(p->snap[s].genre); p->snap[s].harm_genre = via_old(p->snap[s].harm_genre);
        p->snap[s].harm_prog = sq_prog_from28(sq_prog_to28(p->snap[s].harm_prog));
        for (t = 0; t < SQ_TRACKS; t++) p->snap[s].track[t].src_genre = via_old(p->snap[s].track[t].src_genre);
    }
    for (t = 0; t < SQ_TRACKS; t++) {
        sq_track_default(&d, t);
        for (k = 6u; k < SQ_LANES; k++) {
            p->track[t].lane_cc[k] = d.lane_cc[k]; p->track[t].lane_base[k] = d.lane_base[k];
            p->track[t].lane_flags[k] = d.lane_flags[k]; p->track[t].lane_hi[k] = d.lane_hi[k];
            for (s = 0; s < SQ_SNAPS; s++) {
                sq_track_cfg_t *c = &p->snap[s].track[t];
                if (!p->snap[s].used) continue;
                c->lane_cc[k] = d.lane_cc[k]; c->lane_base[k] = d.lane_base[k]; c->lane_flags[k] = d.lane_flags[k]; c->lane_hi[k] = d.lane_hi[k];
            }
            for (s = 0; s < SQ_SCENES; s++) p->scene[s].lane[t][k] = SQ_LANE_NONE;
        }
        for (pat = 0; pat < SQ_PATTERNS; pat++)
            for (i = 0; i < SQ_STEPS; i++) {
                for (k = 4u; k < SQ_POLY; k++) p->step[t][pat][i].note[k] = SQ_NOTE_NONE;
                for (k = 6u; k < SQ_LANES; k++) p->step[t][pat][i].lane[k] = SQ_LANE_NONE;
            }
    }
    sq_project_sanitize(p);
}
#endif

int main(int argc, char **argv)
{
    uint32_t k, n, bad = 0u;
    long m;
    if (argc != 3) { printf("usage: write|relay|check DIR\n"); return 2; }
#ifdef OLD27
    if (strcmp(argv[1], "relay")) return 2;
    for (k = 0; k < OLD_PROJECTS; k++) {              /* 0.27's own projects, with all sixteen tracks used */
        old_fill(&a, k + 101u);
        n = sq_serialize(&a, img, sizeof img);
        if (!n || put(argv[2], "o27", k, img, n) || put(argv[2], "o27s", k, (const uint8_t *)a.step, 12u * sizeof a.step[0])) return 1;
        {   /* what 0.28 must make of it: the first twelve tracks' tapes; the LFO aimed at track 15 stops */
            uint32_t t, ev = 0u;
            uint8_t side[8];
            for (t = 0; t < 12u; t++) ev += a.tape_cnt[t];
            side[0] = (uint8_t)(ev & 0xFFu); side[1] = (uint8_t)(ev >> 8);
            side[2] = a.lfo[0].enabled; side[3] = a.lfo[1].enabled; side[4] = a.lfo[1].target;
            side[5] = (uint8_t)(a.scene[0].mute_mask & 0xFFu); side[6] = (uint8_t)(a.scene[0].mute_mask >> 8); side[7] = 0u;
            if (put(argv[2], "o27x", k, side, 8u)) return 1;
        }
    }
    for (k = 0; k < PROJECTS; k++) {
        if ((m = get(argv[2], "c28", k, img, sizeof img)) < 0) return 1;
        if (sq_image_ok(img, (uint32_t)m) || sq_deserialize(&a, img, (uint32_t)m)) { printf("compat: 0.27 refuses project %u\n", k); bad++; continue; }
        n = sq_serialize(&a, img, sizeof img);
        if (!n || put(argv[2], "c27", k, img, n)) return 1;
    }
    printf("compat 0.27: %u projects of 0.28 opened and saved again by 0.27, %u refused\n", PROJECTS - bad, bad);
    return bad ? 1 : 0;
#else
    if (!strcmp(argv[1], "write")) {
        for (k = 0; k < PROJECTS; k++) {
            fill(&a, k + 1u);
            n = sq_serialize(&a, img, sizeof img);
            if (!n || put(argv[2], "c28", k, img, n)) return 1;
            strip(&a);
            n = sq_serialize(&a, img, sizeof img);
            if (!n || put(argv[2], "e28", k, img, n)) return 1;
        }
        printf("compat 0.28: %u projects written\n", PROJECTS);
        return 0;
    }
    if (!strcmp(argv[1], "check")) {
        for (k = 0; k < PROJECTS; k++) {
            if ((m = get(argv[2], "e28", k, img, sizeof img)) < 0 || sq_deserialize(&a, img, (uint32_t)m)) return 1;
            if ((m = get(argv[2], "c27", k, img, sizeof img)) < 0) return 1;
            memset(&b, 0x5A, sizeof b);
            if (sq_deserialize(&b, img, (uint32_t)m) || memcmp(&a, &b, sizeof a)) {
                const uint8_t *x = (const uint8_t *)&a, *y = (const uint8_t *)&b;
                uint32_t i;
                for (i = 0; i < sizeof a && x[i] == y[i]; i++) ;
                printf("compat: project %u is not the same after 0.27 (first byte %u differs)\n", k, i);
                bad++;
            }
        }
        printf("compat 0.28 -> 0.27 -> 0.28: %u projects, %u not the same\n", PROJECTS, bad);
        for (k = 0; k < OLD_PROJECTS; k++) {          /* 0.27's projects with sixteen tracks: the first twelve kept */
            static sq_step_t st27[12][SQ_PATTERNS][SQ_STEPS];
            struct { uint8_t note[4], velocity, length, chance, ratchet, condition, flags, lane[6]; int8_t nudge, ramp; } __attribute__((packed)) *o;
            uint8_t side[8];
            uint32_t t, pat, i, j, same = 1u, ev;
            if ((m = get(argv[2], "o27", k, img, sizeof img)) < 0 || sq_deserialize(&b, img, (uint32_t)m)) { printf("compat: 0.28 refuses 0.27's project %u\n", k); bad++; continue; }
            if (get(argv[2], "o27s", k, (uint8_t *)st27, sizeof st27) != (long)(12u * SQ_PATTERNS * SQ_STEPS * 18u) || get(argv[2], "o27x", k, side, 8u) != 8) return 1;
            o = (void *)st27;
            for (t = 0; t < 12u; t++)
                for (pat = 0; pat < SQ_PATTERNS; pat++)
                    for (i = 0; i < SQ_STEPS; i++, o++) {
                        const sq_step_t *x = &b.step[t][pat][i];
                        for (j = 0; j < 4u; j++) same &= x->note[j] == o->note[j];
                        for (j = 0; j < 6u; j++) same &= x->lane[j] == o->lane[j];
                        same &= x->velocity == o->velocity && x->length == o->length && x->chance == o->chance && x->ratchet == o->ratchet &&
                                x->condition == o->condition && x->flags == o->flags && x->nudge == o->nudge && x->ramp == o->ramp &&
                                x->note[4] == SQ_NOTE_NONE && x->note[5] == SQ_NOTE_NONE && x->lane[6] == SQ_LANE_NONE && x->lane[7] == SQ_LANE_NONE;
                    }
            ev = (uint32_t)side[0] | ((uint32_t)side[1] << 8);
            same &= b.tape_n == ev;
            same &= b.lfo[0].enabled == 0u && b.lfo[1].enabled == side[3] && b.lfo[1].target == side[4];   /* (LFO 1 aims at 15: it stops) */
            same &= b.scene[0].mute_mask == (((uint32_t)side[5] | ((uint32_t)side[6] << 8)) & 0x0FFFu);
            if (!same) {
                printf("compat: 0.27's project %u: tracks 1-12 not as they were, or 13-16 not left out (tape %u/%u lfo %u %u/%u %u/%u mute %04x)\n", k,
                       b.tape_n, ev, b.lfo[0].enabled, b.lfo[1].enabled, side[3], b.lfo[1].target, side[4], b.scene[0].mute_mask);
                bad++;
            }
        }
        printf("compat 0.27 -> 0.28: %u projects with sixteen tracks, the first twelve kept, the rest left out (%s)\n", OLD_PROJECTS, bad ? "FAIL" : "ok");
        return bad ? 1 : 0;
    }
    return 2;
#endif
}
