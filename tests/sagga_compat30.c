/* SPDX-License-Identifier: GPL-3.0-only */
/* 0.31: an LFO on a track's parameter may aim at a GROUP of tracks - the drums, the bass, the melodic ones, all (target
 * 16-19). The image is 0.30's, nothing added; 0.30 opens a group's LFO as one aimed at a track it does not keep: on T1,
 * switched off (MOD ONLY stays on, as it does). So:
 *   - a project of 0.31 goes 0.31 -> 0.30 -> 0.31 and comes back with its group LFOs off on T1, the rest as it was;
 *   - a project without a group LFO is saved by 0.30 and by 0.31 byte for byte;
 *   - 0.30's own projects open in 0.31 and are saved again byte for byte.
 * Built twice by tests/sagga_compat30.sh: against this core ("write", "check") and against 0.30's as released ("relay",
 * -DOLD30).
 *   write DIR   0.31's projects (c31_N), what must come back after 0.30 (e31_N), projects 0.30 can hold whole (p31_N)
 *   relay DIR   0.30 opens c31_N and saves it again (c30_N), the same with p31_N (q30_N); its own projects (o30_N)
 *   check DIR   0.31 opens c30_N: e31_N's project; q30_N is p31_N byte for byte; o30_N saved again by 0.31 byte for byte */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sagga_seq_core.h"

#define PROJECTS 40u
static sq_project_t a, b;
static uint8_t img[600000], img2[600000];
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
/* a project of chance bytes, put right by the sanitiser (k: which), as the core it is built for has it */
static void chance(sq_project_t *p, uint32_t k)
{
    uint8_t *q = (uint8_t *)p;
    uint32_t i, t, every = 3u + k % 9u;
    rs = (k + 7u) * 2246822519u;
    sq_project_init(p);
    for (i = 0; i < sizeof *p; i++) if (rnd() % (every * 4u) == 0u) q[i] = (uint8_t)rnd();
    for (t = 0; t < SQ_TRACKS; t++) for (i = 0; i < SQ_PATTERNS * SQ_STEPS; i++) p->step[t][i / SQ_STEPS][i % SQ_STEPS].flags &= (uint8_t)~SQ_STEP_GHOST;
    sq_project_sanitize(p);
}

#ifndef OLD30
/* what 0.30 keeps of a project of 0.31: a group's LFO is on T1 and off (MOD ONLY: on) - its lfo_refs_in */
static void lfo_lt31(sq_lfo_t *l)
{
    if (l->dest == SQ_LD_CC || !SQ_LFO_TGROUP(l->target)) return;
    l->target = 0u;
    if (l->dest != SQ_LD_MOD) l->enabled = 0u;
}
static uint32_t less_than_31(sq_project_t *p)
{
    uint32_t i, k, n = 0u;
    for (i = 0; i < SQ_LFOS; i++) { n += SQ_LFO_TGROUP(p->lfo[i].target) && p->lfo[i].dest != SQ_LD_CC; lfo_lt31(&p->lfo[i]); }
    for (k = 0; k < SQ_SNAPS; k++) if (p->snap[k].used) for (i = 0; i < SQ_LFOS; i++) {
        n += SQ_LFO_TGROUP(p->snap[k].lfo[i].target) && p->snap[k].lfo[i].dest != SQ_LD_CC;
        lfo_lt31(&p->snap[k].lfo[i]);
    }
    sq_project_sanitize(p);
    return n;
}
#endif

int main(int argc, char **argv)
{
    uint32_t k, n, bad = 0u;
    long m;
    if (argc != 3) { printf("usage: write|relay|check DIR\n"); return 2; }
#ifdef OLD30
    if (strcmp(argv[1], "relay")) return 2;
    for (k = 0; k < PROJECTS; k++) {
        if ((m = get(argv[2], "c31", k, img, sizeof img)) < 0) return 1;
        if (sq_image_ok(img, (uint32_t)m) || sq_deserialize(&a, img, (uint32_t)m)) { printf("compat: 0.30 refuses project %u\n", k); bad++; continue; }
        n = sq_serialize(&a, img, sizeof img);
        if (!n || put(argv[2], "c30", k, img, n)) return 1;
        if ((m = get(argv[2], "p31", k, img, sizeof img)) < 0) return 1;
        if (sq_image_ok(img, (uint32_t)m) || sq_deserialize(&a, img, (uint32_t)m)) { printf("compat: 0.30 refuses plain project %u\n", k); bad++; continue; }
        n = sq_serialize(&a, img, sizeof img);
        if (!n || put(argv[2], "q30", k, img, n)) return 1;
        chance(&a, k + 100u);
        n = sq_serialize(&a, img, sizeof img);
        if (!n || put(argv[2], "o30", k, img, n)) return 1;
    }
    printf("compat 0.30: %u projects of 0.31 opened and saved again by 0.30, %u refused; %u of its own saved\n", PROJECTS - bad, bad, PROJECTS);
    return bad ? 1 : 0;
#else
    if (!strcmp(argv[1], "write")) {
        uint32_t groups = 0u;
        for (k = 0; k < PROJECTS; k++) {
            uint32_t t, s;
            chance(&a, k);
            if (k % 2u) {                                 /* (in half of them, LFOs on the groups - in a snapshot too) */
                a.lfo[k % 16u].dest = (uint8_t)(SQ_LD_VEL + k % 5u); a.lfo[k % 16u].target = (uint8_t)(SQ_LFO_TG0 + k % 4u); a.lfo[k % 16u].enabled = 1u;
                a.lfo[(k + 5u) % 16u].dest = SQ_LD_MOD; a.lfo[(k + 5u) % 16u].target = (uint8_t)(SQ_LFO_TG0 + (k + 1u) % 4u); a.lfo[(k + 5u) % 16u].enabled = 1u;
                a.lfo[(k + 9u) % 16u].dest = SQ_LD_CC; a.lfo[(k + 9u) % 16u].target = (uint8_t)(k % 16u);   /* (CC: a channel - as before) */
                s = k % SQ_SNAPS;
                a.snap[s].used = 1u;
                for (t = 0; t < SQ_TRACKS; t++) a.snap[s].track[t] = a.track[t];
                memcpy(a.snap[s].lfo, a.lfo, sizeof a.lfo);
                a.snap[s].lfo[(k + 2u) % 16u].dest = SQ_LD_GATE; a.snap[s].lfo[(k + 2u) % 16u].target = (uint8_t)(SQ_LFO_TG0 + SQ_TG_MELODIC);
                a.snap[s].lfo[(k + 2u) % 16u].enabled = 1u;
            }
            sq_project_sanitize(&a);
            n = sq_serialize(&a, img, sizeof img);
            if (!n || put(argv[2], "c31", k, img, n)) return 1;
            memset(&b, 0x5A, sizeof b);                   /* (0.31 itself: all of it, round its own image) */
            if (sq_deserialize(&b, img, n) || memcmp(&a, &b, sizeof a)) { printf("compat: 0.31 loses something of project %u\n", k); bad++; }
            groups += less_than_31(&a);
            n = sq_serialize(&a, img, sizeof img);
            if (!n || put(argv[2], "e31", k, img, n)) return 1;
            if (put(argv[2], "p31", k, img, n)) return 1;   /* (0.30 can hold it whole: saved again, the same bytes) */
        }
        printf("compat 0.31: %u projects written (%u LFOs on a group), %u that 0.31 does not keep whole\n", PROJECTS, groups, bad);
        return bad || groups < PROJECTS ? 1 : 0;
    }
    if (!strcmp(argv[1], "check")) {
        uint32_t same = 0u, own = 0u;
        for (k = 0; k < PROJECTS; k++) {
            long m2;
            if ((m = get(argv[2], "e31", k, img, sizeof img)) < 0 || sq_deserialize(&a, img, (uint32_t)m)) return 1;
            if ((m = get(argv[2], "c30", k, img, sizeof img)) < 0) return 1;
            memset(&b, 0x5A, sizeof b);
            if (sq_deserialize(&b, img, (uint32_t)m) || memcmp(&a, &b, sizeof a)) {
                const uint8_t *x = (const uint8_t *)&a, *y = (const uint8_t *)&b;
                uint32_t i;
                for (i = 0; i < sizeof a && x[i] == y[i]; i++) ;
                printf("compat: project %u is not what 0.30 keeps of it (first byte %u differs)\n", k, i);
                bad++;
            }
            if ((m = get(argv[2], "p31", k, img, sizeof img)) < 0 || (m2 = get(argv[2], "q30", k, img2, sizeof img2)) < 0) return 1;
            if (m == m2 && !memcmp(img, img2, (size_t)m)) same++;
            else { printf("compat: plain project %u is not saved byte for byte by 0.30 (%ld / %ld bytes)\n", k, m, m2); bad++; }
            if ((m = get(argv[2], "o30", k, img, sizeof img)) < 0 || sq_deserialize(&b, img, (uint32_t)m)) { printf("compat: 0.31 refuses 0.30's project %u\n", k); bad++; continue; }
            n = sq_serialize(&b, img2, sizeof img2);
            if (n == (uint32_t)m && !memcmp(img, img2, n)) own++;
            else { printf("compat: 0.30's project %u is saved otherwise by 0.31 (%ld / %u bytes)\n", k, m, n); bad++; }
        }
        printf("compat 0.31 -> 0.30 -> 0.31: %u projects, %u not right; %u saved byte for byte by both; 0.30's own %u saved again as they were (%s)\n",
               PROJECTS, bad, same, own, bad ? "FAIL" : "ok");
        return bad ? 1 : 0;
    }
    return 2;
#endif
}
