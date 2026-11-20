/* SPDX-License-Identifier: GPL-3.0-only */
/* 0.30: what a firmware before 0.30 keeps of a project of 0.30 - its first 16 scenes (the scenes 17-32 and their metres:
 * a new project's), the song's first 64 entries (a scene past the 16th: the first one, as 0.29's sanitiser puts it),
 * its first 8 snapshots, the tapes' first 1536 events (each track's count as far as they go), a scene cursor or a
 * MORPH TO past the 16th as 0.29 puts them right. For the compatibility tests (built against the core of today only). */
#ifndef SAGGA_COMPAT_LT30_H
#define SAGGA_COMPAT_LT30_H
#include "sagga_seq_core.h"

static void less_than_30(sq_project_t *p)
{
    static sq_project_t fresh;
    uint32_t k, t, left = 1536u;
    sq_project_init(&fresh);
    for (k = 16u; k < SQ_SCENES; k++) { p->scene[k] = fresh.scene[k]; p->ext.scene_metre[k] = 0u; }
    for (k = 8u; k < SQ_SNAPS; k++) p->snap[k] = fresh.snap[k];
    if (p->song.len > 64u) p->song.len = 64u;
    for (k = 0; k < p->song.len; k++) if (p->song.e[k].scene >= 16u) p->song.e[k].scene = 0u;
    for (t = 0; t < SQ_TRACKS; t++) {
        uint32_t c = p->tape_cnt[t] < left ? p->tape_cnt[t] : left;
        p->tape_cnt[t] = (uint16_t)c;
        left -= c;
    }
    if (p->tape_n > 1536u) p->tape_n = 1536u;
    if (p->live.scene_cursor >= 16u) p->live.scene_cursor = 0u;
    if (p->live.morph_b >= 16u) p->live.morph_b = 1u;
    for (k = 0; k < 8u; k++) if (p->snap[k].morph_b >= 16u) p->snap[k].morph_b = 1u;
    sq_project_sanitize(p);
}
#endif
