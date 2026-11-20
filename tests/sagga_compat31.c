/* SPDX-License-Identifier: GPL-3.0-only */
/* 0.32: the MASTER knob has a fourth job, the ENERGY (live.master_fn 3, SQ_MK_ENERGY). The image is 0.31's, nothing
 * added; 0.31 opens a project whose knob is on the ENERGY with the knob on the TEMPO (its sanitiser: a job past its
 * three). So:
 *   - a project of 0.32 goes 0.32 -> 0.31 -> 0.32 and comes back with the knob on the TEMPO, the rest as it was;
 *   - a project without the ENERGY is saved by 0.31 and by 0.32 byte for byte;
 *   - 0.31's own projects open in 0.32 and are saved again byte for byte.
 * Built twice by tests/sagga_compat31.sh: against this core ("write", "check") and against 0.31's as released ("relay",
 * -DOLD31).
 *   write DIR   0.32's projects (c32_N), what must come back after 0.31 (e32_N), projects 0.31 can hold whole (p32_N)
 *   relay DIR   0.31 opens c32_N and saves it again (c31_N), the same with p32_N (q31_N); its own projects (o31_N)
 *   check DIR   0.32 opens c31_N: e32_N's project; q31_N is p32_N byte for byte; o31_N saved again by 0.32 byte for byte */
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

#ifndef OLD31
/* what 0.31 keeps of a project of 0.32: the MASTER knob on the TEMPO if it was on the ENERGY */
static uint32_t less_than_32(sq_project_t *p)
{
    uint32_t n = p->live.master_fn == SQ_MK_ENERGY;
    if (n) p->live.master_fn = SQ_MK_TEMPO;
    sq_project_sanitize(p);
    return n;
}
#endif

int main(int argc, char **argv)
{
    uint32_t k, n, bad = 0u;
    long m;
    if (argc != 3) { printf("usage: write|relay|check DIR\n"); return 2; }
#ifdef OLD31
    if (strcmp(argv[1], "relay")) return 2;
    for (k = 0; k < PROJECTS; k++) {
        if ((m = get(argv[2], "c32", k, img, sizeof img)) < 0) return 1;
        if (sq_image_ok(img, (uint32_t)m) || sq_deserialize(&a, img, (uint32_t)m)) { printf("compat: 0.31 refuses project %u\n", k); bad++; continue; }
        n = sq_serialize(&a, img, sizeof img);
        if (!n || put(argv[2], "c31", k, img, n)) return 1;
        if ((m = get(argv[2], "p32", k, img, sizeof img)) < 0) return 1;
        if (sq_image_ok(img, (uint32_t)m) || sq_deserialize(&a, img, (uint32_t)m)) { printf("compat: 0.31 refuses plain project %u\n", k); bad++; continue; }
        n = sq_serialize(&a, img, sizeof img);
        if (!n || put(argv[2], "q31", k, img, n)) return 1;
        chance(&a, k + 100u);
        n = sq_serialize(&a, img, sizeof img);
        if (!n || put(argv[2], "o31", k, img, n)) return 1;
    }
    printf("compat 0.31: %u projects of 0.32 opened and saved again by 0.31, %u refused; %u of its own saved\n", PROJECTS - bad, bad, PROJECTS);
    return bad ? 1 : 0;
#else
    if (!strcmp(argv[1], "write")) {
        uint32_t energy = 0u;
        for (k = 0; k < PROJECTS; k++) {
            chance(&a, k);
            if (k % 2u) a.live.master_fn = SQ_MK_ENERGY;   /* (in half of them, the MASTER knob on the ENERGY) */
            sq_project_sanitize(&a);
            n = sq_serialize(&a, img, sizeof img);
            if (!n || put(argv[2], "c32", k, img, n)) return 1;
            memset(&b, 0x5A, sizeof b);                   /* (0.32 itself: all of it, round its own image) */
            if (sq_deserialize(&b, img, n) || memcmp(&a, &b, sizeof a)) { printf("compat: 0.32 loses something of project %u\n", k); bad++; }
            energy += less_than_32(&a);
            n = sq_serialize(&a, img, sizeof img);
            if (!n || put(argv[2], "e32", k, img, n)) return 1;
            if (put(argv[2], "p32", k, img, n)) return 1;   /* (0.31 can hold it whole: saved again, the same bytes) */
        }
        printf("compat 0.32: %u projects written (%u with the MASTER knob on the ENERGY), %u that 0.32 does not keep whole\n", PROJECTS, energy, bad);
        return bad || energy < PROJECTS / 2u ? 1 : 0;
    }
    if (!strcmp(argv[1], "check")) {
        uint32_t same = 0u, own = 0u;
        for (k = 0; k < PROJECTS; k++) {
            long m2;
            if ((m = get(argv[2], "e32", k, img, sizeof img)) < 0 || sq_deserialize(&a, img, (uint32_t)m)) return 1;
            if ((m = get(argv[2], "c31", k, img, sizeof img)) < 0) return 1;
            memset(&b, 0x5A, sizeof b);
            if (sq_deserialize(&b, img, (uint32_t)m) || memcmp(&a, &b, sizeof a)) {
                const uint8_t *x = (const uint8_t *)&a, *y = (const uint8_t *)&b;
                uint32_t i;
                for (i = 0; i < sizeof a && x[i] == y[i]; i++) ;
                printf("compat: project %u is not what 0.31 keeps of it (first byte %u differs)\n", k, i);
                bad++;
            }
            if ((m = get(argv[2], "p32", k, img, sizeof img)) < 0 || (m2 = get(argv[2], "q31", k, img2, sizeof img2)) < 0) return 1;
            if (m == m2 && !memcmp(img, img2, (size_t)m)) same++;
            else { printf("compat: plain project %u is not saved byte for byte by 0.31 (%ld / %ld bytes)\n", k, m, m2); bad++; }
            if ((m = get(argv[2], "o31", k, img, sizeof img)) < 0 || sq_deserialize(&b, img, (uint32_t)m)) { printf("compat: 0.32 refuses 0.31's project %u\n", k); bad++; continue; }
            n = sq_serialize(&b, img2, sizeof img2);
            if (n == (uint32_t)m && !memcmp(img, img2, n)) own++;
            else { printf("compat: 0.31's project %u is saved otherwise by 0.32 (%ld / %u bytes)\n", k, m, n); bad++; }
        }
        printf("compat 0.32 -> 0.31 -> 0.32: %u projects, %u not right; %u saved byte for byte by both; 0.31's own %u saved again as they were (%s)\n",
               PROJECTS, bad, same, own, bad ? "FAIL" : "ok");
        return bad ? 1 : 0;
    }
    return 2;
#endif
}
