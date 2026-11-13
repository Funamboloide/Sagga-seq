/* SPDX-License-Identifier: GPL-3.0-only */
/* The BEAT library: the patterns (sagga_beats_data.h, from tools/gen_beats.py), chord progressions in the key, and the
 * parts that follow them. No hardware: the host tests compile it on its own. */
#include "sagga_beats.h"

typedef struct { uint8_t func, n, note, main; uint16_t first; } lib_part_t;
typedef struct { uint8_t kit[4], swing; uint16_t bpm_lo, bpm_hi; uint8_t scale[3], chord_size, evo_rhy, evo_note, fill; } genre_t;
#include "sagga_beats_data.h"

_Static_assert(SQ_GENRE_BAILEFUNK + 1 == SQ_GENRES, "the SQ_GENRE_* enum names every genre of the library");
_Static_assert(SQ_SET_GENRES == SQ_GENRES, "VIAGGIO has a set genre for every genre of the library (sagga_setgenre_data.h)");
_Static_assert(SQ_FUNC_VOX + 1 == SQ_FUNCS, "SQ_FUNCS counts the parts");
_Static_assert(SQ_FUNC_VOX - SQ_FUNC_CLAP == SQ_ROLE_VOX - SQ_ROLE_CLAP, "a role for every new part, in the same order");

static const char *const FUNC_NAME[SQ_FUNCS] = {"KICK", "SNARE", "HAT", "PERC", "BASS", "CHORD", "ARP", "PROG", "KIT",
    "CLAP", "OPEN HAT", "RIDE", "SHAKER", "CONGA", "TOM", "RIM", "CRASH", "COWBELL", "RUMBLE", "SUB", "LOG DRUM", "STAB",
    "PAD", "PIANO", "LEAD", "VOX"};
static const uint8_t KIND[SQ_FUNCS] = {SQ_KIND_DRUM, SQ_KIND_DRUM, SQ_KIND_DRUM, SQ_KIND_DRUM, SQ_KIND_MONO, SQ_KIND_CHORD,
    SQ_KIND_MONO, SQ_KIND_CHORD, SQ_KIND_DRUM,
    SQ_KIND_DRUM, SQ_KIND_DRUM, SQ_KIND_DRUM, SQ_KIND_DRUM, SQ_KIND_DRUM, SQ_KIND_DRUM, SQ_KIND_DRUM, SQ_KIND_DRUM, SQ_KIND_DRUM,
    SQ_KIND_MONO, SQ_KIND_MONO, SQ_KIND_MONO, SQ_KIND_CHORD, SQ_KIND_CHORD, SQ_KIND_CHORD, SQ_KIND_MONO, SQ_KIND_MONO};
/* the gate of a hit, in % of a step (a held note: its steps) */
static const uint8_t GATE[SQ_FUNCS] = {55u, 55u, 35u, 45u, 85u, 90u, 55u, 90u, 55u,
    50u, 90u, 60u, 30u, 45u, 60u, 35u, 100u, 40u, 70u, 95u, 70u, 35u, 100u, 70u, 80u, 70u};

const char *sq_genre_name(uint8_t genre) { return GENRE_NAME[genre < SQ_GENRES ? genre : 0u]; }
const char *sq_func_name(uint8_t func) { return FUNC_NAME[func < SQ_FUNCS ? func : 0u]; }
uint8_t sq_func_kind(uint8_t func) { return KIND[func < SQ_FUNCS ? func : 0u]; }
uint8_t sq_func_role(uint8_t func)
{
    if (func < SQ_FUNC_PROG) return (uint8_t)(func + 1u);
    if (func == SQ_FUNC_PROG) return SQ_ROLE_CHORD;
    if (func == SQ_FUNC_KIT) return SQ_ROLE_KICK;
    if (func < SQ_FUNCS) return (uint8_t)(SQ_ROLE_CLAP + (func - SQ_FUNC_CLAP));
    return SQ_ROLE_NONE;
}
uint8_t sq_role_func(uint8_t role)
{
    if (role >= SQ_ROLE_KICK && role <= SQ_ROLE_ARP) return (uint8_t)(role - 1u);
    if (role >= SQ_ROLE_CLAP && role < SQ_ROLE_COUNT) return (uint8_t)(SQ_FUNC_CLAP + (role - SQ_ROLE_CLAP));
    return 255u;
}
uint8_t sq_func_family(uint8_t func)
{
    if (func == SQ_FUNC_PROG) return SQ_FUNC_CHORD;
    if (func == SQ_FUNC_KIT) return SQ_FUNC_KICK;
    return (uint8_t)(sq_role_family(sq_func_role(func)) - 1u);
}

/* the part of a genre; PROG: the first chord part (its rhythms), KIT: the kick */
static const lib_part_t *part_of(uint8_t genre, uint8_t func)
{
    uint32_t i;
    if (genre >= SQ_GENRES || func >= SQ_FUNCS) return 0;
    if (func == SQ_FUNC_KIT) func = SQ_FUNC_KICK;
    for (i = GPART_AT[genre]; i < GPART_AT[genre + 1u]; i++) {
        if (func == SQ_FUNC_PROG ? KIND[GPART[i].func] == SQ_KIND_CHORD : GPART[i].func == func) return &GPART[i];
    }
    return 0;
}

uint8_t sq_genre_parts(uint8_t genre, uint8_t *funcs)
{
    uint32_t i, n = 0u;
    if (genre >= SQ_GENRES) return 0u;
    for (i = GPART_AT[genre]; i < GPART_AT[genre + 1u] && n < SQ_PARTS_MAX; i++) funcs[n++] = GPART[i].func;
    return (uint8_t)n;
}
uint8_t sq_genre_band(uint8_t genre) { return genre < SQ_GENRES ? GBAND[genre] : 0u; }
uint8_t sq_genre_has(uint8_t genre, uint8_t func)
{
    if (func == SQ_FUNC_PROG || func == SQ_FUNC_KIT) return genre < SQ_GENRES ? 1u : 0u;
    return part_of(genre, func) ? 1u : 0u;
}
uint8_t sq_genre_part_for(uint8_t genre, uint8_t func)
{
    uint32_t i;
    uint8_t fam;
    if (genre >= SQ_GENRES || func >= SQ_FUNCS) return 255u;
    if (sq_genre_has(genre, func)) return func;
    fam = sq_func_family(func);
    if (part_of(genre, fam)) return fam;                 /* the family's own (a SNARE for a CLAP) */
    for (i = GPART_AT[genre]; i < GPART_AT[genre + 1u]; i++) if (sq_func_family(GPART[i].func) == fam) return GPART[i].func;
    return 255u;
}
uint8_t sq_part_note(uint8_t genre, uint8_t func)
{
    const lib_part_t *p = part_of(genre, func);
    if (p) return p->note;
    if (func <= SQ_FUNC_PERC) return GENRE[genre < SQ_GENRES ? genre : 0u].kit[func];
    return KIND[func < SQ_FUNCS ? func : 0u] == SQ_KIND_DRUM ? 60u : sq_func_family(func) == SQ_FUNC_BASS ? 36u : 60u;
}
uint8_t sq_part_main(uint8_t genre, uint8_t func) { const lib_part_t *p = part_of(genre, func); return p ? p->main : 0u; }

uint8_t sq_beat_variants(uint8_t genre, uint8_t func)
{
    const lib_part_t *p = part_of(genre, func);
    return p ? p->n : 0u;
}

const char *sq_beat_text(uint8_t genre, uint8_t func, uint8_t var, const char **notes)
{
    const lib_part_t *p = part_of(genre, func);
    const uint32_t *v;
    if (notes) *notes = 0;
    if (!p || var >= p->n) return 0;
    v = VOFF[p->first + var];
    if (notes) *notes = v[1] ? POOL + v[1] : 0;
    return v[0] ? POOL + v[0] : 0;
}

void sq_beat_kit_part(uint8_t genre, uint8_t part, uint8_t *func, uint8_t *note)
{
    if (genre >= SQ_GENRES) genre = 0u;
    if (part > 3u) part = 3u;
    *func = part;                      /* KICK, SNARE, HAT, PERC are functions 0-3 */
    *note = GENRE[genre].kit[part];
}

uint8_t sq_genre_swing(uint8_t genre) { return GENRE[genre < SQ_GENRES ? genre : 0u].swing; }
void sq_genre_bpm(uint8_t genre, uint16_t *lo, uint16_t *hi)
{
    const genre_t *g = &GENRE[genre < SQ_GENRES ? genre : 0u];
    *lo = g->bpm_lo; *hi = g->bpm_hi;
}
uint8_t sq_genre_scale(uint8_t genre, uint8_t i) { return GENRE[genre < SQ_GENRES ? genre : 0u].scale[i < 3u ? i : 0u]; }
uint8_t sq_genre_chord_size(uint8_t genre) { return GENRE[genre < SQ_GENRES ? genre : 0u].chord_size; }
uint8_t sq_genre_hrhythm(uint8_t genre)
{
    static const uint8_t R[SQ_GENRES] = {SQ_HR_BARS, SQ_HR_BARS, SQ_HR_2BARS, SQ_HR_PUSH16, SQ_HR_PUSH16, SQ_HR_PUSH8, SQ_HR_BARS,
        SQ_HR_2BARS, SQ_HR_2BARS, SQ_HR_PUSH16, SQ_HR_332, SQ_HR_332, SQ_HR_BARS, SQ_HR_35, SQ_HR_BARS, SQ_HR_2BARS, SQ_HR_PUSH8,
        SQ_HR_PUSH16, SQ_HR_31, SQ_HR_BARS, SQ_HR_BARS, SQ_HR_BARS, SQ_HR_BARS, SQ_HR_332};
    return R[genre < SQ_GENRES ? genre : 0u];
}
void sq_genre_evolve(uint8_t genre, uint8_t *rhy, uint8_t *note)
{
    const genre_t *g = &GENRE[genre < SQ_GENRES ? genre : 0u];
    *rhy = g->evo_rhy; *note = g->evo_note;
}

static uint8_t hex_val(char c) { return (uint8_t)(c >= 'a' ? 10 + (c - 'a') : c - '0'); }

static uint8_t root_for(uint8_t func, uint8_t note)
{
    int32_t r = note > 127u ? 60 : (int32_t)note, lo = 48, hi = 72;
    uint8_t fam = sq_func_family(func);
    if (fam == SQ_FUNC_BASS) { lo = 24; hi = 48; }        /* a bass lives low: under C3 */
    else if (func == SQ_FUNC_LEAD || func == SQ_FUNC_VOX) { lo = 60; hi = 84; }   /* a lead from middle C */
    while (r >= hi) r -= 12;                              /* chords and arpeggios around middle C */
    while (r < lo) r += 12;
    return (uint8_t)r;
}

static void hit(sq_step_t *s, char c, uint8_t func)
{
    s->flags = SQ_STEP_ON | SQ_STEP_SET;
    s->length = GATE[func < SQ_FUNCS ? func : SQ_FUNC_CHORD];
    s->velocity = c == 'X' ? 124u : c == 'o' ? 75u : c == 'g' ? 45u : 100u;
    if (c >= '2' && c <= '4') s->ratchet = (uint8_t)(c - '0');
}

uint8_t sq_beat_load(sq_step_t *row, uint8_t genre, uint8_t func, uint8_t var, uint8_t note)
{
    return sq_beat_load_len(row, genre, func, var, note, 0u);
}

static uint32_t text_len(const char *r)
{
    uint32_t n = 0u;
    while (r[n] && n < SQ_STEPS) n++;
    return n;
}

static void chord_notes(sq_step_t *s, char kind, uint8_t root)
{
    static const int8_t K[7][4] = {{0, 3, 7, -1}, {0, 4, 7, -1}, {0, 3, 7, 10}, {0, 4, 7, 11}, {0, 4, 7, 10}, {0, 5, 7, -1}, {0, 7, 12, -1}};
    static const char KINDS[7] = {'m', 'M', 'n', 'N', '7', 's', '5'};
    uint32_t k, q = 0u, j = 0u;
    for (k = 0; k < 7u; k++) if (KINDS[k] == kind) q = k;
    for (k = 0; k < SQ_POLY; k++) {
        int32_t v = K[q][k] < 0 ? -1 : (int32_t)root + K[q][k];
        if (v >= 0 && v <= 127) s->note[j++] = (uint8_t)v;
    }
    while (j < SQ_POLY) s->note[j++] = SQ_NOTE_NONE;
}

/* 0.11: the held notes: a hit followed by '-' lasts as many steps (a ratchet keeps its gate) */
static void hold_steps(sq_step_t *row, const char *r, uint32_t n)
{
    uint32_t i, last = n;
    for (i = 0; i < n && r[i]; i++) {
        if (r[i] == '-') {
            if (last < n && row[last].ratchet <= 1u) {
                uint8_t span = (uint8_t)(i - last + 1u);
                row[last].length = sq_gate_steps(span);
            }
        } else if (r[i] != '.') last = i;
        else last = n;
    }
}

/* `n` steps of a pattern from its text at `r` (and the notes at `nt`), the root already in range; a text shorter
 * than n leaves the rest of the steps at rest */
static void load_steps(sq_step_t *row, const char *r, const char *nt, uint32_t n, uint8_t func, uint8_t root)
{
    uint32_t i, m = 0u;
    uint8_t kind = sq_func_kind(func);
    while (m < n && r[m]) m++;
    for (i = 0; i < n; i++) {
        sq_step_t *s = &row[i];
        char c = i < m ? r[i] : '.';
        sq_step_default(s);
        if (c == '.' || c == '-') continue;
        hit(s, c, func);
        if (kind == SQ_KIND_MONO) {
            uint32_t v = (uint32_t)root + hex_val(nt[i]);
            s->note[0] = (uint8_t)(v > 127u ? 127u : v);
        } else if (kind == SQ_KIND_CHORD) {
            chord_notes(s, nt[i], root);
        } else {
            s->note[0] = root;
        }
    }
    hold_steps(row, r, m);
}

static uint8_t root_of(uint8_t func, uint8_t note)
{
    return sq_func_kind(func) != SQ_KIND_DRUM ? root_for(func, note) : (note > 127u ? 60u : note);
}

uint8_t sq_part_root(uint8_t func, uint8_t note) { return root_of(func, note); }
char sq_chord_kind_of(const uint8_t *notes)
{
    static const int8_t K[7][4] = {{0, 3, 7, -1}, {0, 4, 7, -1}, {0, 3, 7, 10}, {0, 4, 7, 11}, {0, 4, 7, 10}, {0, 5, 7, -1}, {0, 7, 12, -1}};
    static const char KINDS[7] = {'m', 'M', 'n', 'N', '7', 's', '5'};
    uint8_t v[SQ_POLY], n = 0u, i, j, k;
    for (i = 0; i < SQ_POLY; i++) if (notes[i] <= 127u) v[n++] = notes[i];
    for (i = 1; i < n; i++) for (j = i; j > 0 && v[j - 1u] > v[j]; j--) { uint8_t x = v[j]; v[j] = v[j - 1u]; v[j - 1u] = x; }
    for (k = 0; k < 7u; k++) {
        uint8_t m = 0u, ok = 1u;
        for (i = 0; i < 4u && K[k][i] >= 0; i++) m++;
        if (m != n) continue;
        for (i = 0; i < m; i++) if ((int32_t)v[i] - (int32_t)v[0] != K[k][i]) ok = 0u;
        if (ok) return KINDS[k];
    }
    if (n >= 2u && (v[1] - v[0]) == 4u) return 'M';                  /* (else: a major or a minor by its third) */
    return 'm';
}
static uint8_t loadable(uint8_t func) { return (uint8_t)(func < SQ_FUNCS && func != SQ_FUNC_PROG && func != SQ_FUNC_KIT); }

/* 0.9: a pattern from its text (the AFRO / LATIN family, a pattern the Pi sends); `nt` may be 0 for drums */
uint8_t sq_beat_load_text(sq_step_t *row, const char *r, const char *nt, uint8_t func, uint8_t note)
{
    uint32_t n, i;
    if (!r || !loadable(func)) return 0u;
    if (sq_func_kind(func) != SQ_KIND_DRUM && !nt) return 0u;
    n = text_len(r);
    if (n != 12u && n != 16u && n != 24u && n != 32u && n != 48u && n != 64u) {   /* (what the Pi sends is checked) */
        if (!n) return 0u;
    }
    for (i = 0; i < n; i++) {
        char c = r[i];
        if (c != '.' && c != '-' && c != 'x' && c != 'X' && c != 'o' && c != 'g' && (c < '2' || c > '4')) return 0u;
        if (nt && c != '.' && c != '-' && !nt[i]) return 0u;
        if (nt && c != '.' && c != '-' && sq_func_kind(func) == SQ_KIND_MONO && !((nt[i] >= '0' && nt[i] <= '9') || (nt[i] >= 'a' && nt[i] <= 'f'))) return 0u;
    }
    load_steps(row, r, nt, n, func, root_of(func, note));
    return (uint8_t)n;
}

/* 0.10: the genre's fill on the last bar of a tiled drum pattern: the final two 16ths roll (the genre's ratchet) where
 * they already hit, else gain a hit; a kick only on the very last one (the pick-up into the next bar), so it stays
 * spare. 0.11: not for the cymbals and the shaker (a crash does not roll). */
static void fill_bar(sq_step_t *bar, uint8_t genre, uint8_t func, uint8_t root)
{
    uint8_t r = GENRE[genre].fill, i, fam = sq_func_family(func);
    if (func == SQ_FUNC_CRASH || func == SQ_FUNC_RIDE || func == SQ_FUNC_OHAT || func == SQ_FUNC_SHAKER || func == SQ_FUNC_COWBELL) return;
    for (i = 14u; i < 16u; i++) {
        sq_step_t *s = &bar[i];
        if (s->flags & SQ_STEP_ON) { s->ratchet = r; continue; }
        if (fam == SQ_FUNC_KICK && i == 14u) continue;
        hit(s, i == 15u && fam != SQ_FUNC_KICK ? 'X' : 'x', func);
        if (fam == SQ_FUNC_SNARE || fam == SQ_FUNC_HAT) s->ratchet = r;   /* a roll into the one */
        s->note[0] = root;
    }
}

uint8_t sq_beat_load_len(sq_step_t *row, uint8_t genre, uint8_t func, uint8_t var, uint8_t note, uint8_t len)
{
    const char *nt, *r, *nt2, *r2;
    uint32_t n, n2, bars, b, nb, off;
    uint8_t root, nv;
    if (!loadable(func)) return 0u;                   /* PROG and KIT are made elsewhere */
    r = sq_beat_text(genre, func, var, &nt);
    if (!r || (sq_func_kind(func) != SQ_KIND_DRUM && !nt)) return 0u;
    if (!len) return sq_beat_load_text(row, r, nt, func, note);
    if (len != 16u && len != 32u && len != 64u) len = 16u;
    root = root_of(func, note);
    n = text_len(r);
    if (n >= len) { load_steps(row, r, nt, len, func, root); return len; }   /* as written, or its first bars */
    bars = len / 16u;
    nb = n / 16u; if (!nb) nb = 1u;                   /* the variant's own bars, repeated in turn */
    for (b = 0; b + 1u < bars; b++) {
        off = (b % nb) * 16u;
        load_steps(row + b * 16u, r + off, nt ? nt + off : 0, 16u, func, root);
    }
    nv = sq_beat_variants(genre, func);               /* the last bar: the next variant's, the bar the span reaches */
    r2 = sq_beat_text(genre, func, (uint8_t)((var + 1u) % (nv ? nv : 1u)), &nt2);
    if (!r2) { r2 = r; nt2 = nt; }
    n2 = text_len(r2);
    nb = n2 / 16u; if (!nb) nb = 1u;
    off = ((bars - 1u) % nb) * 16u;
    load_steps(row + (bars - 1u) * 16u, r2 + off, nt2 ? nt2 + off : 0, 16u, func, root);
    if (sq_func_kind(func) == SQ_KIND_DRUM) fill_bar(row + (bars - 1u) * 16u, genre, func, root);
    return len;
}

/* ---- 0.8 progressions */

const sq_prog_t *sq_prog_get(uint8_t genre, uint8_t i)
{
    if (genre >= SQ_GENRES) genre = 0u;
    return &PROGS[genre][i < SQ_PROGS ? i : 0u];
}

void sq_prog_name(uint8_t genre, uint8_t i, uint8_t scale, char *out, uint32_t cap)
{
    const sq_prog_t *pg = sq_prog_get(genre, i);
    uint32_t k = 0u, c;
    char b[12];
    for (c = 0; c < pg->n; c++) {
        const char *q = b;
        sq_harm_chord_name(scale, pg->deg[c], pg->col[c], b);
        if (c && k + 1u < cap) out[k++] = '-';
        while (*q && k + 1u < cap) out[k++] = *q++;
    }
    out[k] = 0;
}

uint8_t sq_prog_at(uint8_t genre, uint8_t i, uint32_t bar, uint8_t bars_override, int8_t *deg, uint8_t *col)
{
    const sq_prog_t *pg = sq_prog_get(genre, i);
    uint32_t bpc = bars_override ? bars_override : (pg->bars ? pg->bars : 1u), k = pg->n ? (bar / bpc) % pg->n : 0u;
    *deg = pg->n ? pg->deg[k] : 0;
    *col = pg->n ? pg->col[k] : SQ_HC_TRIAD;
    return (uint8_t)k;
}

uint8_t sq_tonic_chord(uint8_t root, uint8_t scale, uint8_t center, uint8_t size, uint8_t *out)
{
    uint8_t hs = sq_harm_scale(scale), n = 0u;
    int32_t k, j;
    if (size < 3u) size = 3u;
    if (size > SQ_POLY) size = (uint8_t)SQ_POLY;
    if (center > 115u) center = 115u;
    if (center < 12u) center = 12u;
    for (k = 0; k < (int32_t)size; k++) {
        int32_t v = sq_scale_nth(center, root, hs, 2 * k), dup = 0;
        while (v - (int32_t)center >= 6) v -= 12;       /* close voicing: every note within a tritone of the centre */
        while ((int32_t)center - v > 6) v += 12;
        if (v < 0 || v > 127) continue;
        for (j = 0; j < (int32_t)n; j++) if (out[j] == v) dup = 1;
        if (dup) continue;
        for (j = n; j > 0 && out[j - 1] > v; j--) out[j] = out[j - 1];   /* ascending */
        out[j] = (uint8_t)v;
        n++;
    }
    return n;
}

uint8_t sq_beat_chords(sq_step_t *row, uint8_t genre, uint8_t var, uint8_t root, uint8_t scale, uint8_t center)
{
    const char *r, *nt;
    uint32_t i, n = 0u, k;
    uint8_t chord[SQ_POLY], m, nv;
    if (genre >= SQ_GENRES) genre = 0u;
    nv = sq_beat_variants(genre, SQ_FUNC_PROG);
    r = sq_beat_text(genre, SQ_FUNC_PROG, (uint8_t)(nv && var < nv ? var : 0u), &nt);
    if (!r) return 0u;
    n = text_len(r);
    m = sq_tonic_chord(root, scale, center, sq_genre_chord_size(genre), chord);
    for (i = 0; i < n; i++) {
        sq_step_t *s = &row[i];
        sq_step_default(s);
        if (r[i] == '.' || r[i] == '-') continue;
        hit(s, r[i], SQ_FUNC_CHORD);
        for (k = 0; k < SQ_POLY; k++) s->note[k] = k < m ? chord[k] : SQ_NOTE_NONE;
    }
    hold_steps(row, r, n);
    return (uint8_t)n;
}

uint8_t sq_beat_role(uint8_t drum, uint8_t note)
{
    if (drum) {
        if (note == 35u || note == 36u) return SQ_FUNC_KICK;
        if (note >= 37u && note <= 40u) return SQ_FUNC_SNARE;
        if (note == 42u || note == 44u || note == 46u) return SQ_FUNC_HAT;
        return SQ_FUNC_PERC;
    }
    if (note < 48u) return SQ_FUNC_BASS;
    if (note < 60u) return SQ_FUNC_PROG;
    return SQ_FUNC_ARP;
}
