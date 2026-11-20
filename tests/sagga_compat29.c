/* SPDX-License-Identifier: GPL-3.0-only */
/* 0.30: 32 scenes (0.29: 16), a song of 128 entries (64), 16 snapshots (8), 3072 tape events (1536). The image keeps
 * 0.29's layout and puts the rest in chunk 6, which 0.29 skips. So:
 *   - a project of 0.30 goes 0.30 -> 0.29 -> 0.30 and comes back with what 0.29 keeps of it (tests/sagga_compat_lt30.h);
 *   - a project with nothing 0.29 lacks is saved by 0.29 and by 0.30 byte for byte;
 *   - 0.29's own projects (BALANI, the balafon, ROLL and ACCENT, a 7th progression) open in 0.30 as they were.
 * Built twice by tests/sagga_compat29.sh: against this core ("write", "check") and against 0.29's as released ("relay",
 * -DOLD29).
 *   write DIR   0.30's projects (c30_N), what must come back after 0.29 (e30_N), projects 0.29 can hold whole (p30_N)
 *   relay DIR   0.29 opens c30_N and saves it again (c29_N), the same with p30_N (q29_N); its own projects (o29_N)
 *   check DIR   0.30 opens c29_N: e30_N's project; q29_N is p30_N byte for byte; o29_N opens as 0.29 saved it */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sagga_seq_core.h"
#ifndef OLD29
#include "sagga_compat_lt30.h"
#endif

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
    rs = (k + 1u) * 2654435761u;
    sq_project_init(p);
    for (i = 0; i < sizeof *p; i++) if (rnd() % (every * 4u) == 0u) q[i] = (uint8_t)rnd();
    for (t = 0; t < SQ_TRACKS; t++) for (i = 0; i < SQ_PATTERNS * SQ_STEPS; i++) p->step[t][i / SQ_STEPS][i % SQ_STEPS].flags &= (uint8_t)~SQ_STEP_GHOST;
    sq_project_sanitize(p);
}
/* 0.29's own: BALANI (14), the balafon (26), ROLL and ACCENT on, a genre's 7th progression, a snapshot - the core it is
 * built for keeps them all */
static void own29(sq_project_t *p, uint32_t k)
{
    uint32_t t;
    sq_project_init(p);
    p->gen.genre = 14u; p->gen.harm_genre = (uint8_t)(k % 22u); p->gen.harm_prog = 6u; p->viaggio.set_genre = 14u;
    p->track[k % 12u].role = SQ_ROLE_BALAFON; p->track[k % 12u].src_func = 26u; p->track[3].src_genre = 14u;
    p->ext.mfxd[2].on = (uint8_t)(1u << 5) | (uint8_t)(1u << 6);       /* (ROLL and ACCENT: the 6th and 7th new effects) */
    p->snap[k % 8u].used = 1u;
    for (t = 0; t < SQ_TRACKS; t++) p->snap[k % 8u].track[t] = p->track[t];
    memcpy(p->snap[k % 8u].lfo, p->lfo, sizeof p->lfo);
    p->snap[k % 8u].genre = 14u; p->snap[k % 8u].harm_prog = 7u;
    p->scene[15].pattern[2] = 3u; p->song.len = 64u; p->song.e[63].scene = 15u; p->song.e[63].bars = 8u;
    sq_project_sanitize(p);
}

int main(int argc, char **argv)
{
    uint32_t k, n, bad = 0u;
    long m;
    if (argc != 3) { printf("usage: write|relay|check DIR\n"); return 2; }
#ifdef OLD29
    if (strcmp(argv[1], "relay")) return 2;
    for (k = 0; k < PROJECTS; k++) {
        if ((m = get(argv[2], "c30", k, img, sizeof img)) < 0) return 1;
        if (sq_image_ok(img, (uint32_t)m) || sq_deserialize(&a, img, (uint32_t)m)) { printf("compat: 0.29 refuses project %u\n", k); bad++; continue; }
        n = sq_serialize(&a, img, sizeof img);
        if (!n || put(argv[2], "c29", k, img, n)) return 1;
        if ((m = get(argv[2], "p30", k, img, sizeof img)) < 0) return 1;
        if (sq_image_ok(img, (uint32_t)m) || sq_deserialize(&a, img, (uint32_t)m)) { printf("compat: 0.29 refuses plain project %u\n", k); bad++; continue; }
        n = sq_serialize(&a, img, sizeof img);
        if (!n || put(argv[2], "q29", k, img, n)) return 1;
        own29(&a, k);
        n = sq_serialize(&a, img, sizeof img);
        if (!n || put(argv[2], "o29", k, img, n)) return 1;
    }
    printf("compat 0.29: %u projects of 0.30 opened and saved again by 0.29, %u refused; %u of its own saved\n", PROJECTS - bad, bad, PROJECTS);
    return bad ? 1 : 0;
#else
    if (!strcmp(argv[1], "write")) {
        for (k = 0; k < PROJECTS; k++) {
            uint32_t t, i;
            chance(&a, k);
            if (k % 2u) {                                 /* (in half of them, everything 0.30 added, past 0.29's room) */
                a.scene[16u + k % 16u].pattern[1] = 5u; a.scene[31].mute_mask = 0x0F0u; a.ext.scene_metre[20] = 3u;
                a.song.len = (uint8_t)(70u + k); for (i = 60u; i < a.song.len; i++) { a.song.e[i].scene = (uint8_t)(i % 32u); a.song.e[i].bars = (uint8_t)(1u + i % 8u); }
                a.snap[8u + k % 8u].used = 1u; a.snap[15].used = 1u;
                for (t = 0; t < SQ_TRACKS; t++) { a.snap[8u + k % 8u].track[t] = a.track[t]; a.snap[15].track[t] = a.track[t]; }
                a.snap[15].track[2].role = SQ_ROLE_BALAFON; a.snap[15].genre = 14u; a.snap[15].harm_prog = 7u;
                a.live.scene_cursor = 25u;
                while (a.tape_n < 1536u + 200u + k) if (sq_tape_add(&a, (uint8_t)(a.tape_n % SQ_TRACKS), (uint16_t)(a.tape_n * 7u % 6144u), 12u, 60u, 90u)) break;
            }
            sq_project_sanitize(&a);
            n = sq_serialize(&a, img, sizeof img);
            if (!n || put(argv[2], "c30", k, img, n)) return 1;
            memset(&b, 0x5A, sizeof b);                   /* (0.30 itself: all of it, round its own image) */
            if (sq_deserialize(&b, img, n) || memcmp(&a, &b, sizeof a)) { printf("compat: 0.30 loses something of project %u\n", k); bad++; }
            less_than_30(&a);
            n = sq_serialize(&a, img, sizeof img);
            if (!n || put(argv[2], "e30", k, img, n)) return 1;
            if (put(argv[2], "p30", k, img, n)) return 1;   /* (0.29 can hold it whole: saved again, the same bytes) */
        }
        printf("compat 0.30: %u projects written, %u that 0.30 does not keep whole\n", PROJECTS, bad);
        return bad ? 1 : 0;
    }
    if (!strcmp(argv[1], "check")) {
        uint32_t same = 0u;
        for (k = 0; k < PROJECTS; k++) {
            long m2;
            if ((m = get(argv[2], "e30", k, img, sizeof img)) < 0 || sq_deserialize(&a, img, (uint32_t)m)) return 1;
            if ((m = get(argv[2], "c29", k, img, sizeof img)) < 0) return 1;
            memset(&b, 0x5A, sizeof b);
            if (sq_deserialize(&b, img, (uint32_t)m) || memcmp(&a, &b, sizeof a)) {
                const uint8_t *x = (const uint8_t *)&a, *y = (const uint8_t *)&b;
                uint32_t i;
                for (i = 0; i < sizeof a && x[i] == y[i]; i++) ;
                printf("compat: project %u is not what 0.29 keeps of it (first byte %u differs)\n", k, i);
                bad++;
            }
            if ((m = get(argv[2], "p30", k, img, sizeof img)) < 0 || (m2 = get(argv[2], "q29", k, img2, sizeof img2)) < 0) return 1;
            if (m == m2 && !memcmp(img, img2, (size_t)m)) same++;
            else { printf("compat: plain project %u is not saved byte for byte by 0.29 (%ld / %ld bytes)\n", k, m, m2); bad++; }
            if ((m = get(argv[2], "o29", k, img, sizeof img)) < 0 || sq_deserialize(&b, img, (uint32_t)m)) { printf("compat: 0.30 refuses 0.29's project %u\n", k); bad++; continue; }
            own29(&a, k);                                 /* (0.29's own, as 0.30 makes it: the same) */
            if (memcmp(&a, &b, sizeof a)) { printf("compat: 0.29's project %u opens otherwise in 0.30\n", k); bad++; }
        }
        printf("compat 0.30 -> 0.29 -> 0.30: %u projects, %u not right; %u saved byte for byte by both; 0.29's own as they were (%s)\n",
               PROJECTS, bad, same, bad ? "FAIL" : "ok");
        return bad ? 1 : 0;
    }
    return 2;
#endif
}
