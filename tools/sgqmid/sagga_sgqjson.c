/* SPDX-License-Identifier: GPL-3.0-only
 * SAGGA SEQ 0.14: a project image (.sgq) <-> what the web editor reads and writes, built with the firmware's own core.
 * 0.15: the project's name (ext name, 16 characters as numbers), the GROOVE (chain groove / groove_amt), the TAPE
 * tracks' events (read: "tape"; a patch: the tape lines below) and their loop (track tape_bars / tape_quant).
 * 0.19: the MIDI FX chain of each track (mfxc on: a bit per effect, 1 << SQ_MFX_*; amt / time / fb [effect - 1]); the
 * track's mfx .. mfx_fb are its first, set by sanitize (a patch of them alone is undone).
 *
 *   sagga_sgqjson read IN.sgq                    the project as JSON on stdout: every field the editor knows, by name;
 *                                                the steps only where they differ from a new project's (sparse), the
 *                                                schema (each group's fields, sizes, signs) and a new project's step
 *   sagga_sgqjson apply BASE.sgq|new PATCH OUT.sgq   BASE (or a new project) with the changes of PATCH, put through
 *                                                the firmware's sanitize, written as an image: what the FM-1 loads
 *   sagga_sgqjson new OUT.sgq                    a new project
 *
 * A PATCH is text, a change a line:   GROUP INDEXES FIELD ELEM VALUE
 *   GROUP    project key track step scene lfo lfox chain song song_e live ext mfxc (and tape, below)
 *   INDEXES  "-" for project / song / live / ext, else the index (track, scene ...), "t,p,s" for a step
 *   FIELD    a field of the group (the names of the C structs); ELEM: "-", or which element of an array field
 *   VALUE    an integer in the field's type (u8, s8, u16)
 * e.g.  project - bpm - 140  /  track 3 length - 32  /  step 3,0,12 note 0 60  /  song_e 5 bars - 8
 * 0.15, the TAPE tracks' events (a track's are all written again when one changes):
 *   tape T clear - 0              track T's events gone
 *   tape T,ON,DUR,NOTE add - VEL  an event: ON and DUR in tape ticks (384 a beat), the loop's (track tape_bars) taken
 *                                 when it is checked, after the whole patch: one that does not fit is dropped
 * The editor never builds an image: the layout is this program's (offsetof), the limits are sanitize's. The
 * snapshots and VIAGGIO are not touched by a patch: they stay as BASE has them.
 * Exit: 0 done, 1 bad arguments, 2 cannot read / not a project, 3 cannot write, 4 a patch line not understood (its
 * number and why on stderr; nothing is written). */
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sagga_seq_core.h"

static sq_project_t proj, blank;
static uint8_t img[1u << 16];

typedef struct { const char *name; uint32_t off; uint8_t size, sign, n; } fd_t;     /* n: elements (1: a scalar) */
typedef struct {
    const char *name;
    uint32_t off;                /* where the group's first element is in sq_project_t */
    uint32_t stride[3];          /* bytes from one index to the next (dims used: those with count > 0) */
    uint32_t count[3];
    const fd_t *f;
    uint32_t nf;
} grp_t;

#define F(T, m, sg)        {#m, (uint32_t)offsetof(T, m), (uint8_t)sizeof(((T *)0)->m), sg, 1u}
#define A(T, m, el, sg, k) {#m, (uint32_t)offsetof(T, m), (uint8_t)sizeof(el), sg, (uint8_t)(k)}
#define NF(a) ((uint32_t)(sizeof a / sizeof a[0]))

static const fd_t F_PROJECT[] = {
    F(sq_project_t, bpm, 0), F(sq_project_t, clock_mode, 0), F(sq_project_t, key_root, 0), F(sq_project_t, key_scale, 0),
    F(sq_project_t, key_shift, 1), F(sq_project_t, key_cur, 0), A(sq_project_t, device, uint8_t, 0, SQ_CHANNELS),
};
static const fd_t F_KEY[] = { F(sq_key_t, root, 0), F(sq_key_t, scale, 0), F(sq_key_t, shift, 1) };
static const fd_t F_TRACK[] = {
    F(sq_track_cfg_t, channel, 0), F(sq_track_cfg_t, length, 0), F(sq_track_cfg_t, start, 0), F(sq_track_cfg_t, division, 0),
    F(sq_track_cfg_t, direction, 0), F(sq_track_cfg_t, transpose, 1), F(sq_track_cfg_t, initial_pattern, 0),
    F(sq_track_cfg_t, chord_mode, 0), F(sq_track_cfg_t, swing, 0), F(sq_track_cfg_t, vel_offset, 1),
    F(sq_track_cfg_t, hum_time, 0), F(sq_track_cfg_t, hum_vel, 0),
    A(sq_track_cfg_t, lane_cc, uint8_t, 0, SQ_LANES), A(sq_track_cfg_t, lane_base, uint8_t, 0, SQ_LANES),
    A(sq_track_cfg_t, lane_flags, uint8_t, 0, SQ_LANES), A(sq_track_cfg_t, lane_hi, uint8_t, 0, SQ_LANES),
    F(sq_track_cfg_t, flags, 0), A(sq_track_cfg_t, plen, uint8_t, 0, 3), F(sq_track_cfg_t, voicing, 0),
    F(sq_track_cfg_t, strum, 1), F(sq_track_cfg_t, mfx, 0), F(sq_track_cfg_t, mfx_amt, 1), F(sq_track_cfg_t, mfx_time, 0),
    F(sq_track_cfg_t, mfx_fb, 0), F(sq_track_cfg_t, euc_pulses, 0), F(sq_track_cfg_t, euc_rot, 0), F(sq_track_cfg_t, algo, 0),
    F(sq_track_cfg_t, algo_a, 0), F(sq_track_cfg_t, algo_b, 0), F(sq_track_cfg_t, algo_c, 0), F(sq_track_cfg_t, pen, 0),
    F(sq_track_cfg_t, role, 0), F(sq_track_cfg_t, chord, 0), F(sq_track_cfg_t, octave, 1), F(sq_track_cfg_t, key_slot, 0),
    F(sq_track_cfg_t, euc_fam, 0), F(sq_track_cfg_t, arp_rate, 0), F(sq_track_cfg_t, arp_flags, 0),
    F(sq_track_cfg_t, delay_ms, 1), F(sq_track_cfg_t, chord_key, 0), F(sq_track_cfg_t, follow_mode, 0),
    F(sq_track_cfg_t, brk_chop, 0), F(sq_track_cfg_t, brk_cfg, 0),
    {"tape_bars", (uint32_t)(offsetof(sq_track_cfg_t, tape) + offsetof(sq_tape_cfg_t, bars)), 1u, 0u, 1u},     /* 0.15 */
    {"tape_quant", (uint32_t)(offsetof(sq_track_cfg_t, tape) + offsetof(sq_tape_cfg_t, quant)), 1u, 0u, 1u},
};
static const fd_t F_STEP[] = {
    A(sq_step_t, note, uint8_t, 0, SQ_POLY), F(sq_step_t, velocity, 0), F(sq_step_t, length, 0), F(sq_step_t, chance, 0),
    F(sq_step_t, ratchet, 0), F(sq_step_t, condition, 0), F(sq_step_t, flags, 0), A(sq_step_t, lane, uint8_t, 0, SQ_LANES),
    F(sq_step_t, nudge, 1), F(sq_step_t, ramp, 1),
};
static const fd_t F_SCENE[] = {
    A(sq_scene_t, pattern, uint8_t, 0, SQ_TRACKS), F(sq_scene_t, mute_mask, 0), A(sq_scene_t, pc, uint8_t, 0, SQ_CHANNELS),
    F(sq_scene_t, key_slot, 0),
};
static const fd_t F_LFO[] = {
    F(sq_lfo_t, enabled, 0), F(sq_lfo_t, shape, 0), F(sq_lfo_t, rate, 0), F(sq_lfo_t, depth, 0), F(sq_lfo_t, center, 0),
    F(sq_lfo_t, phase, 0), F(sq_lfo_t, dest, 0), F(sq_lfo_t, target, 0), F(sq_lfo_t, param, 0), F(sq_lfo_t, flags, 0),
};
static const fd_t F_LFOX[] = {
    F(sq_lfox_t, seq_n, 0), F(sq_lfox_t, seq_every, 0), A(sq_lfox_t, seq_rate, uint8_t, 0, SQ_RSEQ_MAX), F(sq_lfox_t, trig, 0),
};
static const fd_t F_CHAIN[] = {
    F(sq_trackx_t, chain_on, 0), F(sq_trackx_t, chain_n, 0), A(sq_trackx_t, chain_pat, uint8_t, 0, SQ_CHAIN_MAX),
    A(sq_trackx_t, chain_rep, uint8_t, 0, SQ_CHAIN_MAX), F(sq_trackx_t, groove, 0), F(sq_trackx_t, groove_amt, 0),   /* 0.15 GROOVE */
};
static const fd_t F_SONG[] = { F(sq_song_t, len, 0), F(sq_song_t, loop, 0) };
static const fd_t F_SONG_E[] = { F(sq_song_entry_t, scene, 0), F(sq_song_entry_t, bars, 0), F(sq_song_entry_t, bpm, 0) };
static const fd_t F_LIVE[] = {
    F(sq_live_t, quant, 0), F(sq_live_t, mute_q, 0), F(sq_live_t, morph_b, 0), F(sq_live_t, master_fn, 0),
    F(sq_live_t, snap_tempo, 0), F(sq_live_t, remote_mode, 0), A(sq_live_t, mac, int8_t, 1, 4),
    F(sq_live_t, cc_lead_ms, 0), F(sq_live_t, song_tempo, 0), F(sq_live_t, mute_lo, 0), F(sq_live_t, mute_hi, 0),
};
static const fd_t F_MFXC[] = {                                                                                       /* 0.19 */
    F(sq_mfxc_t, on, 0), A(sq_mfxc_t, amt, int8_t, 1, SQ_MFX_N), A(sq_mfxc_t, time, uint8_t, 0, SQ_MFX_N), A(sq_mfxc_t, fb, uint8_t, 0, SQ_MFX_N),
};
static const fd_t F_EXT[] = {
    F(sq_ext_t, motion_bars, 0), F(sq_ext_t, kb_mode, 0), F(sq_ext_t, kb_ch, 0), F(sq_ext_t, in_thru, 0),
    A(sq_ext_t, name, uint8_t, 0, SQ_NAME_LEN),                                                                     /* 0.15 */
};

#define PO(m) ((uint32_t)offsetof(sq_project_t, m))
static const grp_t G[] = {
    {"project", 0u, {0}, {0}, F_PROJECT, NF(F_PROJECT)},
    {"key", PO(key), {sizeof(sq_key_t)}, {SQ_KEYS}, F_KEY, NF(F_KEY)},
    {"track", PO(track), {sizeof(sq_track_cfg_t)}, {SQ_TRACKS}, F_TRACK, NF(F_TRACK)},
    {"scene", PO(scene), {sizeof(sq_scene_t)}, {SQ_SCENES}, F_SCENE, NF(F_SCENE)},
    {"lfo", PO(lfo), {sizeof(sq_lfo_t)}, {SQ_LFOS}, F_LFO, NF(F_LFO)},
    {"lfox", PO(ext) + (uint32_t)offsetof(sq_ext_t, lfo), {sizeof(sq_lfox_t)}, {SQ_LFOS}, F_LFOX, NF(F_LFOX)},
    {"chain", PO(ext) + (uint32_t)offsetof(sq_ext_t, track), {sizeof(sq_trackx_t)}, {SQ_TRACKS}, F_CHAIN, NF(F_CHAIN)},
    {"song", PO(song), {0}, {0}, F_SONG, NF(F_SONG)},
    {"song_e", PO(song) + (uint32_t)offsetof(sq_song_t, e), {sizeof(sq_song_entry_t)}, {SQ_SONG_LEN}, F_SONG_E, NF(F_SONG_E)},
    {"live", PO(live), {0}, {0}, F_LIVE, NF(F_LIVE)},
    {"ext", PO(ext), {0}, {0}, F_EXT, NF(F_EXT)},
    {"mfxc", PO(ext) + (uint32_t)offsetof(sq_ext_t, mfxc), {sizeof(sq_mfxc_t)}, {SQ_TRACKS}, F_MFXC, NF(F_MFXC)},   /* 0.19 the MIDI FX chain */
    {"step", PO(step), {sizeof(sq_step_t) * SQ_PATTERNS * SQ_STEPS, sizeof(sq_step_t) * SQ_STEPS, sizeof(sq_step_t)},
     {SQ_TRACKS, SQ_PATTERNS, SQ_STEPS}, F_STEP, NF(F_STEP)},
};
#define NG NF(G)

static int dims(const grp_t *g) { return g->count[2] ? 3 : g->count[1] ? 2 : g->count[0] ? 1 : 0; }

static long get_v(const sq_project_t *p, uint32_t at, const fd_t *f)
{
    const uint8_t *b = (const uint8_t *)p + at;
    if (f->size == 2) { uint16_t v; memcpy(&v, b, 2); return f->sign ? (long)(int16_t)v : (long)v; }
    return f->sign ? (long)(int8_t)*b : (long)*b;
}
static void set_v(sq_project_t *p, uint32_t at, const fd_t *f, long v)
{
    uint8_t *b = (uint8_t *)p + at;
    if (f->size == 2) { uint16_t u = (uint16_t)v; memcpy(b, &u, 2); }
    else *b = (uint8_t)v;
}

static void put_field(const sq_project_t *p, uint32_t base, const fd_t *f)
{
    uint32_t e;
    printf("\"%s\":", f->name);
    if (f->n == 1u) { printf("%ld", get_v(p, base + f->off, f)); return; }
    putchar('[');
    for (e = 0; e < f->n; e++) printf("%s%ld", e ? "," : "", get_v(p, base + f->off + e * f->size, f));
    putchar(']');
}
static void put_elem(const sq_project_t *p, const grp_t *g, uint32_t base)
{
    uint32_t i;
    putchar('{');
    for (i = 0; i < g->nf; i++) { if (i) putchar(','); put_field(p, base, &g->f[i]); }
    putchar('}');
}

/* the core's names of a list, for the editor's menus (the page's own lists - divisions, LFO shapes ... - are the
 * panel's, from dinghy.c: tests/sagga_editor_tests.py checks them) */
static void put_names(const char *key, const char *(*fn)(uint8_t), uint32_t n, int comma)
{
    uint32_t i;
    printf("%s\"%s\":[", comma ? "," : "", key);
    for (i = 0; i < n; i++) {
        const char *s = fn((uint8_t)i);
        putchar(i ? ',' : ' ');
        putchar('"');
        for (; *s; s++) { if (*s == '"' || *s == '\\') putchar('\\'); putchar(*s); }
        putchar('"');
    }
    putchar(']');
}

static int read_image(const char *path, sq_project_t *p)
{
    FILE *f = fopen(path, "rb");
    size_t n;
    if (!f) { fprintf(stderr, "cannot read %s\n", path); return 2; }
    n = fread(img, 1, sizeof img, f);
    fclose(f);
    if (!n || sq_deserialize(p, img, (uint32_t)n)) { fprintf(stderr, "%s is not a SAGGA project image\n", path); return 2; }
    return 0;
}

static int cmd_read(const char *in)
{
    uint32_t gi, i, t, pt, s, first = 1u;
    int r = read_image(in, &proj);
    if (r) return r;
    printf("{\"version\":1,\"tape_n\":%u", (unsigned)proj.tape_n);
    printf(",\"tape_cnt\":[");
    for (t = 0; t < SQ_TRACKS; t++) printf("%s%u", t ? "," : "", (unsigned)proj.tape_cnt[t]);
    printf("],\"tape_len\":[");
    for (t = 0; t < SQ_TRACKS; t++) printf("%s%u", t ? "," : "", (unsigned)sq_tape_len(&proj.track[t].tape));
    printf("],\"tape\":[");                                  /* 0.15: [track, on, dur, note, vel], track by track, by start */
    for (t = 0; t < SQ_TRACKS; t++) {
        uint16_t first, cnt;
        uint32_t k;
        sq_tape_range(&proj, (uint8_t)t, &first, &cnt);
        for (k = first; k < (uint32_t)first + cnt; k++) {
            const sq_tape_ev_t *e = &proj.tape_ev[k];
            printf("%s[%u,%u,%u,%u,%u]", k ? "," : "", (unsigned)t, (unsigned)e->on, (unsigned)e->dur, (unsigned)e->note, (unsigned)e->vel);
        }
    }
    printf("],\"snaps\":[");
    for (t = 0; t < SQ_SNAPS; t++) printf("%s%u", t ? "," : "", (unsigned)proj.snap[t].used);
    printf("]");
    printf(",\"schema\":{");
    for (gi = 0; gi < NG; gi++) {
        const grp_t *g = &G[gi];
        printf("%s\"%s\":{\"dims\":[", gi ? "," : "", g->name);
        for (i = 0; i < (uint32_t)dims(g); i++) printf("%s%u", i ? "," : "", (unsigned)g->count[i]);
        printf("],\"fields\":[");
        for (i = 0; i < g->nf; i++) printf("%s[\"%s\",%u,%u,%u]", i ? "," : "", g->f[i].name, g->f[i].size, g->f[i].sign, g->f[i].n);
        printf("]}");
    }
    printf("}");
    for (gi = 0; gi < NG; gi++) {
        const grp_t *g = &G[gi];
        int d = dims(g);
        if (d == 3) continue;
        printf(",\"%s\":", g->name);
        if (d == 0) { put_elem(&proj, g, g->off); continue; }
        putchar('[');
        for (i = 0; i < g->count[0]; i++) { if (i) putchar(','); put_elem(&proj, g, g->off + i * g->stride[0]); }
        putchar(']');
    }
    /* the steps that differ from a new project's (each with its place) */
    printf(",\"step_default\":");
    put_elem(&blank, &G[NG - 1u], G[NG - 1u].off);
    printf(",\"steps\":[");
    for (t = 0; t < SQ_TRACKS; t++)
        for (pt = 0; pt < SQ_PATTERNS; pt++)
            for (s = 0; s < SQ_STEPS; s++) {
                if (!memcmp(&proj.step[t][pt][s], &blank.step[t][pt][s], sizeof(sq_step_t))) continue;
                printf("%s[%u,%u,%u,", first ? "" : ",", (unsigned)t, (unsigned)pt, (unsigned)s);
                put_elem(&proj, &G[NG - 1u], G[NG - 1u].off + t * G[NG - 1u].stride[0] + pt * G[NG - 1u].stride[1] + s * G[NG - 1u].stride[2]);
                putchar(']');
                first = 0u;
            }
    printf("],\"names\":{");
    put_names("role", sq_role_name, SQ_ROLE_COUNT, 0);
    put_names("chord", sq_chord_shape_name, SQ_CH_COUNT, 1);
    put_names("chord_key", sq_chord_key_name, SQ_CK_COUNT, 1);
    put_names("condition", sq_cond_name, SQ_COND_COUNT, 1);
    put_names("scale", sq_scale_long_name, SQ_SCALES, 1);
    put_names("root", sq_root_name, 12u, 1);
    put_names("device", sq_device_name, SQ_DEV_COUNT, 1);
    put_names("euc_fam", sq_rhythm_name, SQ_RF_COUNT, 1);
    put_names("groove", sq_groove_name, SQ_GROOVES, 1);
    printf("}}\n");
    return 0;
}

/* 0.15: tape T clear - 0  /  tape T,ON,DUR,NOTE add - VEL */
static int tape_line(char **tok, unsigned no)
{
    unsigned long x[4] = {0, 0, 0, 0};
    char *q = tok[1], *e;
    int k, n = !strcmp(tok[2], "add") ? 4 : !strcmp(tok[2], "clear") ? 1 : 0;
    long v;
    if (!n || strcmp(tok[3], "-")) { fprintf(stderr, "patch line %u: tape T clear - 0 / tape T,ON,DUR,NOTE add - VEL\n", no); return 4; }
    for (k = 0; k < n; k++) {
        x[k] = strtoul(q, &e, 10);
        if (e == q || (k < n - 1 ? *e != ',' : *e != '\0')) { fprintf(stderr, "patch line %u: tape %s\n", no, tok[1]); return 4; }
        q = e + 1;
    }
    v = strtol(tok[4], &e, 10);
    if (e == tok[4] || *e) { fprintf(stderr, "patch line %u: %s is not a number\n", no, tok[4]); return 4; }
    if (x[0] >= SQ_TRACKS) { fprintf(stderr, "patch line %u: no track %lu\n", no, x[0]); return 4; }
    if (n == 1) { sq_tape_clear(&proj, (uint8_t)x[0]); return 0; }
    if (x[1] >= SQ_TAPE_BARS_MAX * SQ_TAPE_BAR || x[2] < 1u || x[2] > SQ_TAPE_BARS_MAX * SQ_TAPE_BAR || x[3] > 127u || v < 1 || v > 127) {
        fprintf(stderr, "patch line %u: a tape event out of range\n", no); return 4;
    }
    /* (added at the end of the track's events, in the patch's order; written before the loop is known: the order and
     * the loop are the core's to sort out when the patch is through) */
    if (proj.tape_n >= SQ_TAPE_MAX) { fprintf(stderr, "patch line %u: the tape is full (%u events)\n", no, (unsigned)SQ_TAPE_MAX); return 4; }
    {
        uint16_t first, cnt;
        uint32_t i, at;
        sq_tape_ev_t ev;
        ev.on = (uint16_t)x[1]; ev.dur = (uint16_t)x[2]; ev.note = (uint8_t)x[3]; ev.vel = (uint8_t)v;
        sq_tape_range(&proj, (uint8_t)x[0], &first, &cnt);
        at = (uint32_t)first + cnt;
        while (at > first && proj.tape_ev[at - 1u].on > ev.on) at--;
        for (i = proj.tape_n; i > at; i--) proj.tape_ev[i] = proj.tape_ev[i - 1u];
        proj.tape_ev[at] = ev;
        proj.tape_n++;
        proj.tape_cnt[x[0]]++;
    }
    return 0;
}

static int patch_line(char *line, unsigned no)
{
    char *tok[6];
    int nt = 0, d, k;
    uint32_t gi, fi, idx[3] = {0, 0, 0}, at, elem = 0u;
    long v, lo, hi;
    const grp_t *g = 0;
    const fd_t *f = 0;
    char *p = strtok(line, " \t\r\n");
    while (p && nt < 6) { tok[nt++] = p; p = strtok(0, " \t\r\n"); }
    if (!nt || tok[0][0] == '#') return 0;
    if (nt != 5 || p) { fprintf(stderr, "patch line %u: five words: GROUP INDEXES FIELD ELEM VALUE\n", no); return 4; }
    if (!strcmp(tok[0], "tape")) return tape_line(tok, no);
    for (gi = 0; gi < NG; gi++) if (!strcmp(tok[0], G[gi].name)) g = &G[gi];
    if (!g) { fprintf(stderr, "patch line %u: no group %s\n", no, tok[0]); return 4; }
    d = dims(g);
    if (d == 0) { if (strcmp(tok[1], "-")) { fprintf(stderr, "patch line %u: %s has no index\n", no, g->name); return 4; } }
    else {
        char *q = tok[1];
        for (k = 0; k < d; k++) {
            char *e;
            unsigned long x = strtoul(q, &e, 10);
            if (e == q || x >= g->count[k] || (k < d - 1 ? *e != ',' : *e != '\0')) { fprintf(stderr, "patch line %u: index %s out of %s\n", no, tok[1], g->name); return 4; }
            idx[k] = (uint32_t)x;
            q = e + 1;
        }
    }
    for (fi = 0; fi < g->nf; fi++) if (!strcmp(tok[2], g->f[fi].name)) f = &g->f[fi];
    if (!f) { fprintf(stderr, "patch line %u: %s has no field %s\n", no, g->name, tok[2]); return 4; }
    if (f->n > 1u) {
        char *e;
        unsigned long x = strtoul(tok[3], &e, 10);
        if (e == tok[3] || *e || x >= f->n) { fprintf(stderr, "patch line %u: %s.%s has %u elements\n", no, g->name, f->name, f->n); return 4; }
        elem = (uint32_t)x;
    } else if (strcmp(tok[3], "-")) { fprintf(stderr, "patch line %u: %s.%s is not an array\n", no, g->name, f->name); return 4; }
    {
        char *e;
        v = strtol(tok[4], &e, 10);
        if (e == tok[4] || *e) { fprintf(stderr, "patch line %u: %s is not a number\n", no, tok[4]); return 4; }
    }
    lo = f->sign ? (f->size == 2 ? -32768L : -128L) : 0L;
    hi = f->sign ? (f->size == 2 ? 32767L : 127L) : (f->size == 2 ? 65535L : 255L);
    if (v < lo || v > hi) { fprintf(stderr, "patch line %u: %ld out of %ld..%ld\n", no, v, lo, hi); return 4; }
    at = g->off;
    for (k = 0; k < d; k++) at += idx[k] * g->stride[k];
    set_v(&proj, at + f->off + elem * f->size, f, v);
    return 0;
}

static int write_image(const char *out)
{
    uint32_t n;
    FILE *f;
    sq_project_sanitize(&proj);
    n = sq_serialize(&proj, img, sizeof img);
    if (!n) { fprintf(stderr, "the project does not fit an image\n"); return 3; }
    f = fopen(out, "wb");
    if (!f || fwrite(img, 1, n, f) != n) { fprintf(stderr, "cannot write %s\n", out); if (f) fclose(f); return 3; }
    fclose(f);
    return 0;
}

static int cmd_apply(const char *base, const char *patch, const char *out)
{
    static char line[512];
    unsigned no = 0u;
    FILE *f;
    int r;
    if (!strcmp(base, "new")) sq_project_init(&proj);
    else if ((r = read_image(base, &proj)) != 0) return r;
    f = fopen(patch, "r");
    if (!f) { fprintf(stderr, "cannot read %s\n", patch); return 2; }
    while (fgets(line, sizeof line, f)) {
        no++;
        if ((r = patch_line(line, no)) != 0) { fclose(f); return r; }
    }
    fclose(f);
    return write_image(out);
}

int main(int argc, char **argv)
{
    sq_project_init(&blank);
    if (argc == 3 && !strcmp(argv[1], "read")) return cmd_read(argv[2]);
    if (argc == 5 && !strcmp(argv[1], "apply")) return cmd_apply(argv[2], argv[3], argv[4]);
    if (argc == 3 && !strcmp(argv[1], "new")) { sq_project_init(&proj); return write_image(argv[2]); }
    fprintf(stderr, "usage: sagga_sgqjson read IN.sgq | apply BASE.sgq|new PATCH OUT.sgq | new OUT.sgq\n");
    return 1;
}
