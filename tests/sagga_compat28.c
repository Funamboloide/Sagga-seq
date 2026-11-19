/* SPDX-License-Identifier: GPL-3.0-only */
/* 0.29: the genres are 22 (0.28: 25), the progressions of a genre 8 (0.28: 6). A project goes 0.29 -> 0.28 -> 0.29 and
 * comes back the same, but for BALANI, which 0.28 keeps as AFRO HOUSE and 0.29 reads back as GQOM (an image saved by 0.28
 * has no chunk 5), and a genre's 7th or 8th progression, which comes back as its 1st; and 0.28's own projects, each of
 * its 25 genres in every place a genre is kept, open in 0.29 with the genre that took it in (GRIME as DUBSTEP, BASSLINE
 * as UK GARAGE, AFRO HOUSE as GQOM, AMAPIANO as REGGAETON), each of its 11 progressions as the same one (the player's
 * and the Pi's two places on). Built twice by tests/sagga_compat28.sh: against this core ("write", "check") and against
 * 0.28's as released ("relay", -DOLD28).
 *   write DIR   0.29's projects (c29_N) and what must come back after 0.28 (e29_N)
 *   relay DIR   0.28 opens c29_N and saves it again (c28_N); and saves projects of its own genres (o28_G)
 *   check DIR   0.29 opens c28_N: e29_N's project byte for byte; and o28_G: the genres as they map */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sagga_seq_core.h"

#define PROJECTS 40u
#define OLD_GENRES 25u
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
/* one genre g of the firmware it is built for in every place a project keeps one (a snapshot too, a THEORY pattern);
 * the progression pr (0.28's: 0..10) the project's and the snapshot's */
static void genre_fill(sq_project_t *p, uint8_t g, uint8_t g2, uint8_t pr)
{
    uint32_t t;
    sq_project_init(p);
    p->gen.genre = g; p->gen.harm_genre = g2; p->viaggio.set_genre = g; p->gen.harm_prog = pr;
    p->track[0].src_genre = g; p->track[1].src_genre = g2;
    p->th.pat[0][0].seed = 5u; p->th.pat[0][0].style = SQ_THP_PACK(g, 16u); p->th.pat[0][0].func = 0u;
    p->snap[0].used = 1u;
    for (t = 0; t < SQ_TRACKS; t++) p->snap[0].track[t] = p->track[t];
    memcpy(p->snap[0].lfo, p->lfo, sizeof p->lfo);
    p->snap[0].genre = g2; p->snap[0].harm_genre = g; p->snap[0].track[2].src_genre = g; p->snap[0].harm_prog = (uint8_t)(10u - pr);
    sq_project_sanitize(p);
}

int main(int argc, char **argv)
{
    uint32_t k, n, bad = 0u;
    long m;
    if (argc != 3) { printf("usage: write|relay|check DIR\n"); return 2; }
#ifdef OLD28
    if (strcmp(argv[1], "relay")) return 2;
    for (k = 0; k < PROJECTS; k++) {
        if ((m = get(argv[2], "c29", k, img, sizeof img)) < 0) return 1;
        if (sq_image_ok(img, (uint32_t)m) || sq_deserialize(&a, img, (uint32_t)m)) { printf("compat: 0.28 refuses project %u\n", k); bad++; continue; }
        n = sq_serialize(&a, img, sizeof img);
        if (!n || put(argv[2], "c28", k, img, n)) return 1;
    }
    for (k = 0; k < OLD_GENRES; k++) {                /* 0.28's own projects, one of its genres each */
        genre_fill(&a, (uint8_t)k, (uint8_t)((k + 7u) % OLD_GENRES), (uint8_t)(k % 11u));
        n = sq_serialize(&a, img, sizeof img);
        if (!n || put(argv[2], "o28", k, img, n)) return 1;
    }
    printf("compat 0.28: %u projects of 0.29 opened and saved again by 0.28, %u refused; %u of its own genres saved\n", PROJECTS - bad, bad, OLD_GENRES);
    return bad ? 1 : 0;
#else
    if (!strcmp(argv[1], "write")) {
        for (k = 0; k < PROJECTS; k++) {
            uint8_t *q = (uint8_t *)&a;
            uint32_t i, t, s, every = 3u + k % 9u;
            rs = (k + 1u) * 2654435761u;
            sq_project_init(&a);
            for (i = 0; i < sizeof a; i++) if (rnd() % (every * 4u) == 0u) q[i] = (uint8_t)rnd();
            for (t = 0; t < SQ_TRACKS; t++) for (i = 0; i < SQ_PATTERNS * SQ_STEPS; i++) a.step[t][i / SQ_STEPS][i % SQ_STEPS].flags &= (uint8_t)~SQ_STEP_GHOST;
            if (k % 2u) { a.gen.genre = (uint8_t)(k % 22u); a.track[k % SQ_TRACKS].src_genre = 14u; a.viaggio.set_genre = 14u; }   /* (BALANI in half of them) */
            a.gen.harm_prog = (uint8_t)(k % SQ_PROGS_ALL);                  /* (every progression, the 7th and 8th too) */
            for (s = 0; s < SQ_SNAPS; s++) a.snap[s].harm_prog = (uint8_t)((k + 3u * s) % SQ_PROGS_ALL);
            sq_project_sanitize(&a);
            n = sq_serialize(&a, img, sizeof img);
            if (!n || put(argv[2], "c29", k, img, n)) return 1;
            /* what comes back: BALANI as GQOM wherever a genre is kept */
#define VO(x) ((x) = sq_genre_from28(sq_genre_to28(x), 0u))
            VO(a.gen.genre); VO(a.gen.harm_genre); VO(a.viaggio.set_genre);
            a.gen.harm_prog = sq_prog_from28(sq_prog_to28(a.gen.harm_prog));
            for (t = 0; t < SQ_TRACKS; t++) {
                VO(a.track[t].src_genre);
                for (i = 0; i < SQ_PATTERNS; i++) {
                    sq_thpat_t *mm = &a.th.pat[t][i];
                    if (mm->style & 31u) mm->style = (uint8_t)((mm->style & ~31u) | ((sq_genre_from28(sq_genre_to28((uint8_t)((mm->style & 31u) - 1u)), 0u) + 1u) & 31u));
                }
            }
            for (s = 0; s < SQ_SNAPS; s++) if (a.snap[s].used) {
                VO(a.snap[s].genre); VO(a.snap[s].harm_genre);
                a.snap[s].harm_prog = sq_prog_from28(sq_prog_to28(a.snap[s].harm_prog));
                for (t = 0; t < SQ_TRACKS; t++) VO(a.snap[s].track[t].src_genre);
            }
#undef VO
            n = sq_serialize(&a, img, sizeof img);
            if (!n || put(argv[2], "e29", k, img, n)) return 1;
        }
        printf("compat 0.29: %u projects written\n", PROJECTS);
        return 0;
    }
    if (!strcmp(argv[1], "check")) {
        for (k = 0; k < PROJECTS; k++) {
            if ((m = get(argv[2], "e29", k, img, sizeof img)) < 0 || sq_deserialize(&a, img, (uint32_t)m)) return 1;
            if ((m = get(argv[2], "c28", k, img, sizeof img)) < 0) return 1;
            memset(&b, 0x5A, sizeof b);
            if (sq_deserialize(&b, img, (uint32_t)m) || memcmp(&a, &b, sizeof a)) {
                const uint8_t *x = (const uint8_t *)&a, *y = (const uint8_t *)&b;
                uint32_t i;
                for (i = 0; i < sizeof a && x[i] == y[i]; i++) ;
                printf("compat: project %u is not the same after 0.28 (first byte %u differs)\n", k, i);
                bad++;
            }
        }
        printf("compat 0.29 -> 0.28 -> 0.29: %u projects, %u not the same (BALANI as GQOM, PROG 7 and 8 as PROG 1)\n", PROJECTS, bad);
        for (k = 0; k < OLD_GENRES; k++) {
            uint8_t g = sq_genre_from28((uint8_t)k, 0u), g2 = sq_genre_from28((uint8_t)((k + 7u) % OLD_GENRES), 0u);
            uint8_t pr = (uint8_t)(k % 11u), want = pr < 6u ? pr : (uint8_t)(pr + 2u), want2 = (uint8_t)(10u - pr) < 6u ? (uint8_t)(10u - pr) : (uint8_t)(12u - pr);
            if ((m = get(argv[2], "o28", k, img, sizeof img)) < 0 || sq_deserialize(&b, img, (uint32_t)m)) { printf("compat: 0.29 refuses 0.28's genre %u\n", k); bad++; continue; }
            if (b.gen.genre != g || b.gen.harm_genre != g2 || b.viaggio.set_genre != g || b.track[0].src_genre != g || b.track[1].src_genre != g2 ||
                SQ_THP_STYLE(&b.th.pat[0][0]) != g || b.snap[0].genre != g2 || b.snap[0].harm_genre != g || b.snap[0].track[2].src_genre != g ||
                b.gen.harm_prog != want || b.snap[0].harm_prog != want2) {
                printf("compat: 0.28's genre %u opens as %u %u %u %u %u style %u snap %u %u %u, progression %u %u (want %u, %u; %u %u)\n", k, b.gen.genre, b.gen.harm_genre,
                       b.viaggio.set_genre, b.track[0].src_genre, b.track[1].src_genre, SQ_THP_STYLE(&b.th.pat[0][0]), b.snap[0].genre,
                       b.snap[0].harm_genre, b.snap[0].track[2].src_genre, b.gen.harm_prog, b.snap[0].harm_prog, g, g2, want, want2);
                bad++;
            }
        }
        printf("compat 0.28 -> 0.29: %u genres of 0.28, each where it went, and its 11 progressions (%s)\n", OLD_GENRES, bad ? "FAIL" : "ok");
        return bad ? 1 : 0;
    }
    return 2;
#endif
}
