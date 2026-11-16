/* SPDX-License-Identifier: GPL-3.0-only
 * SAGGA SEQ: the firmware's library as lines of text, for tools/theory/gen_rules.py (which counts it and writes the
 * rules of the genres the THEORY engines have no hand-made rules for: firmware/src/sagga_theory_data.h).
 *   cc -std=c11 -O2 -Ifirmware/src tools/theory/libdump.c firmware/src/sagga_seq_core.c firmware/src/sagga_beats.c -o build/sagga_libdump
 * G  index  name  bpm_lo  bpm_hi  scale,scale,scale  hrhythm  swing  half_time  band
 * V  genre  func  func_name  kind  family  variation  hits  notes|-
 * P  genre  chords  bars  step,...  colour,...
 * S  scale  name  mask  parent   (bit i of the mask: the note i semitones above the root; the parent: the scale of
 *                                 seven notes the HARMONY builds its chords on)
 * This tool knows nothing of the engines: it is built before their data exist. */
#include <stdio.h>
#include "sagga_beats.h"

int main(void)
{
    uint8_t g, i, v, k;
    for (i = 0; i < SQ_SCALES; i++)
        printf("S\t%u\t%s\t%u\t%u\n", (unsigned)i, sq_scale_name(i), (unsigned)sq_scale_mask(i), (unsigned)sq_harm_scale(i));
    for (g = 0; g < SQ_GENRES; g++) {
        uint8_t parts[SQ_PARTS_MAX], n = sq_genre_parts(g, parts);
        uint16_t lo, hi;
        sq_genre_bpm(g, &lo, &hi);
        printf("G\t%u\t%s\t%u\t%u\t%u,%u,%u\t%u\t%u\t%u\t%u\n", (unsigned)g, sq_genre_name(g), (unsigned)lo, (unsigned)hi, (unsigned)sq_genre_scale(g, 0u),
               (unsigned)sq_genre_scale(g, 1u), (unsigned)sq_genre_scale(g, 2u), (unsigned)sq_genre_hrhythm(g), (unsigned)sq_genre_swing(g),
               (unsigned)sq_set_genre(g)->half_time, (unsigned)sq_genre_band(g));
        for (i = 0; i < n; i++) {
            uint8_t nv = sq_beat_variants(g, parts[i]);
            for (v = 0; v < nv; v++) {
                const char *nt = 0, *r = sq_beat_text(g, parts[i], v, &nt);
                if (!r) continue;
                printf("V\t%u\t%u\t%s\t%u\t%u\t%u\t%s\t%s\n", (unsigned)g, (unsigned)parts[i], sq_func_name(parts[i]), (unsigned)sq_func_kind(parts[i]),
                       (unsigned)sq_func_family(parts[i]), (unsigned)v, r, nt && sq_func_kind(parts[i]) != SQ_KIND_DRUM ? nt : "-");
            }
        }
        for (i = 0; i < SQ_PROGS; i++) {
            const sq_prog_t *p = sq_prog_get(g, i);
            if (!p) continue;
            printf("P\t%u\t%u\t%u\t", (unsigned)g, (unsigned)p->n, (unsigned)p->bars);
            for (k = 0; k < p->n && k < 8u; k++) printf("%s%d", k ? "," : "", (int)p->deg[k]);
            putchar('\t');
            for (k = 0; k < p->n && k < 8u; k++) printf("%s%u", k ? "," : "", (unsigned)p->col[k]);
            putchar('\n');
        }
    }
    return 0;
}
