/* SPDX-License-Identifier: GPL-3.0-only
 * SAGGA SEQ 0.11: a project image (.sgq, what EXPORT sends) <-> a standard MIDI file.
 *
 *   sagga_sgqmid sgq2mid IN.sgq OUT.mid [BARS]      every track with notes becomes a MIDI track (its channel):
 *                                                   a TAPE track as it is, a step track as written (its loop
 *                                                   repeated over BARS bars, default 4, with velocity, gate,
 *                                                   nudge, ratchets, swing, transpose; chance / conditions / the
 *                                                   live layer are not played: they are the show, not the score)
 *   sagga_sgqmid mid2sgq IN.mid OUT.sgq [BASE.sgq]  the notes of each MIDI channel become a TAPE track (channel
 *                                                   n -> track n) in a new project, or in BASE's; the loop is the
 *                                                   file's length rounded up to bars (16 at most); the tempo too
 * Built with the firmware's own core (sagga_seq_core.c): the same format, the same limits. PPQ of the files written
 * is 384 (the tape's resolution). Exit: 0 done, 1 bad arguments, 2 cannot read / not a project / not a MIDI file,
 * 3 cannot write. Warnings (notes dropped, bars cut) go to stderr; the rest is converted. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sagga_seq_core.h"

static sq_project_t proj;
static uint8_t img[1u << 16];

/* ------------------------------------------------------------ MIDI file writing */
typedef struct { uint32_t tick; uint8_t st, d1, d2; uint32_t ord; } mev_t;
static mev_t mev[65536];
static uint32_t mev_n, mev_ord;

static void mev_add(uint32_t tick, uint8_t st, uint8_t d1, uint8_t d2)
{
    if (mev_n >= sizeof mev / sizeof mev[0]) return;
    mev[mev_n].tick = tick; mev[mev_n].st = st; mev[mev_n].d1 = d1; mev[mev_n].d2 = d2; mev[mev_n].ord = mev_ord++;
    mev_n++;
}

static int mev_cmp(const void *a, const void *b)
{
    const mev_t *x = a, *y = b;
    if (x->tick != y->tick) return x->tick < y->tick ? -1 : 1;
    /* a note-off before a note-on at the same tick (a repeated note does not get cut) */
    if (((x->st & 0xF0u) == 0x80u) != ((y->st & 0xF0u) == 0x80u)) return (x->st & 0xF0u) == 0x80u ? -1 : 1;
    return x->ord < y->ord ? -1 : x->ord > y->ord;
}

static uint8_t *put32(uint8_t *p, uint32_t v) { *p++ = (uint8_t)(v >> 24); *p++ = (uint8_t)(v >> 16); *p++ = (uint8_t)(v >> 8); *p++ = (uint8_t)v; return p; }
static uint8_t *put16(uint8_t *p, uint32_t v) { *p++ = (uint8_t)(v >> 8); *p++ = (uint8_t)v; return p; }
static uint8_t *putvar(uint8_t *p, uint32_t v)
{
    uint8_t b[5]; int n = 0;
    do { b[n++] = (uint8_t)(v & 0x7Fu); v >>= 7; } while (v);
    while (n--) *p++ = (uint8_t)(b[n] | (n ? 0x80u : 0u));
    return p;
}

static uint8_t trk[1u << 20];

static int write_track(FILE *f, const char *name, uint32_t tempo_us, uint32_t from, uint32_t to)
{
    uint8_t *p = trk + 8, *start = p;
    uint32_t last = 0u, i, n = (uint32_t)strlen(name);
    if (tempo_us) { p = putvar(p, 0u); *p++ = 0xFFu; *p++ = 0x51u; *p++ = 3u; *p++ = (uint8_t)(tempo_us >> 16); *p++ = (uint8_t)(tempo_us >> 8); *p++ = (uint8_t)tempo_us;
                    p = putvar(p, 0u); *p++ = 0xFFu; *p++ = 0x58u; *p++ = 4u; *p++ = 4u; *p++ = 2u; *p++ = 24u; *p++ = 8u; }
    p = putvar(p, 0u); *p++ = 0xFFu; *p++ = 0x03u; p = putvar(p, n); memcpy(p, name, n); p += n;
    for (i = from; i < to; i++) {
        p = putvar(p, mev[i].tick - last); last = mev[i].tick;
        *p++ = mev[i].st; *p++ = mev[i].d1; *p++ = mev[i].d2;
    }
    p = putvar(p, 0u); *p++ = 0xFFu; *p++ = 0x2Fu; *p++ = 0u;
    memcpy(trk, "MTrk", 4); put32(trk + 4, (uint32_t)(p - start));
    return fwrite(trk, 1, (size_t)(p - trk), f) == (size_t)(p - trk) ? 0 : -1;
}

/* a step track as written: its loop over `bars` bars */
static void step_track_events(uint8_t t, uint32_t bars)
{
    const sq_track_cfg_t *c = &proj.track[t];
    uint8_t pat = c->initial_pattern < SQ_PATTERNS ? c->initial_pattern : 0u;
    const sq_step_t *row = proj.step[t][pat];
    uint32_t step_ticks = (uint32_t)sq_div_ticks(c->division) * (SQ_TAPE_PPQ / 24u);   /* tape ticks a step */
    uint32_t len = c->length ? c->length : 1u, lo = c->start < len ? c->start : 0u, span = len - lo;
    uint32_t loop_ticks = span * step_ticks, total = bars * SQ_TAPE_BAR, pos = 0u, k = 0u;
    uint8_t ch = (uint8_t)(c->channel & 15u);
    if (!loop_ticks) return;
    while (pos < total) {
        const sq_step_t *s = &row[lo + (k % span)];
        uint32_t base = pos, n, r;
        int32_t off = 0;
        if ((s->flags & SQ_STEP_ON) && (s->flags & SQ_STEP_SET)) {
            uint32_t rat = s->ratchet ? s->ratchet : 1u, slice = step_ticks / rat;
            if (c->swing > SQ_SWING_MIN && ((lo + k % span) & 1u)) off += (int32_t)(step_ticks * (2u * c->swing - 100u) / 100u);
            off += (int32_t)step_ticks * s->nudge / 100;
            for (r = 0; r < rat; r++) {
                uint32_t on = (uint32_t)((int32_t)base + off) + r * slice, gate;
                int32_t vel = s->velocity ? s->velocity : 100;
                if (s->length <= 100u) gate = slice * s->length / 100u;
                else if (s->length == 101u) gate = step_ticks * 3u / 2u;
                else gate = step_ticks * (s->length - 100u);
                if (!gate) gate = 1u;
                if (rat > 1u && s->ramp) vel += (int32_t)s->ramp * (int32_t)r / (int32_t)(rat - 1u);
                vel += c->vel_offset;
                if (vel < 1) vel = 1;
                if (vel > 127) vel = 127;
                for (n = 0; n < SQ_POLY; n++) {
                    int32_t note = s->note[n];
                    if (note == SQ_NOTE_NONE) continue;
                    note += c->transpose;
                    if (note < 0 || note > 127) continue;
                    mev_add(on, (uint8_t)(0x90u | ch), (uint8_t)note, (uint8_t)vel);
                    mev_add(on + gate, (uint8_t)(0x80u | ch), (uint8_t)note, 0u);
                }
            }
        }
        pos += step_ticks; k++;
    }
}

static void tape_track_events(uint8_t t, uint32_t bars)
{
    const sq_track_cfg_t *c = &proj.track[t];
    uint32_t len = sq_tape_len(&proj.track[t].tape), total = bars * SQ_TAPE_BAR, rep, i;
    uint16_t first, n;
    uint8_t ch = (uint8_t)(c->channel & 15u);
    sq_tape_range(&proj, t, &first, &n);
    for (rep = 0; rep * len < total; rep++)
        for (i = first; i < (uint32_t)first + n; i++) {
            const sq_tape_ev_t *e = &proj.tape_ev[i];
            int32_t note = (int32_t)e->note + c->transpose;
            uint32_t on = rep * len + e->on;
            if (note < 0 || note > 127 || on >= total) continue;
            mev_add(on, (uint8_t)(0x90u | ch), (uint8_t)note, e->vel);
            mev_add(on + e->dur, (uint8_t)(0x80u | ch), (uint8_t)note, 0u);
        }
}

static int sgq2mid(const char *in, const char *out, uint32_t bars)
{
    FILE *f = fopen(in, "rb");
    size_t n;
    uint32_t t, ntr = 0u, tempo_us;
    uint8_t hdr[14];
    if (!f) { fprintf(stderr, "cannot read %s\n", in); return 2; }
    n = fread(img, 1, sizeof img, f); fclose(f);
    if (!n || sq_deserialize(&proj, img, (uint32_t)n)) { fprintf(stderr, "%s is not a SAGGA project image\n", in); return 2; }
    if (!bars) {                                             /* the longest tape, 4 at least */
        for (t = 0; t < SQ_TRACKS; t++) if ((proj.track[t].flags & SQ_TF_TAPE) && proj.track[t].tape.bars > bars) bars = proj.track[t].tape.bars;
        if (bars < 4u) bars = 4u;
    }
    tempo_us = proj.bpm ? 60000000u / proj.bpm : 500000u;
    f = fopen(out, "wb");
    if (!f) { fprintf(stderr, "cannot write %s\n", out); return 3; }
    /* which tracks have something */
    for (t = 0; t < SQ_TRACKS; t++) {
        uint32_t before = mev_n;
        if (proj.track[t].flags & SQ_TF_TAPE) tape_track_events((uint8_t)t, bars); else step_track_events((uint8_t)t, bars);
        if (mev_n > before) ntr++;
        mev_n = before;
    }
    memcpy(hdr, "MThd", 4); put32(hdr + 4, 6u); put16(hdr + 8, 1u); put16(hdr + 10, ntr + 1u); put16(hdr + 12, SQ_TAPE_PPQ);
    fwrite(hdr, 1, 14, f);
    {
        char name[40];
        snprintf(name, sizeof name, "SAGGA SEQ %u BPM", (unsigned)proj.bpm);
        write_track(f, name, tempo_us, 0u, 0u);             /* the tempo track */
    }
    for (t = 0; t < SQ_TRACKS; t++) {
        char name[40];
        mev_n = 0u; mev_ord = 0u;
        if (proj.track[t].flags & SQ_TF_TAPE) tape_track_events((uint8_t)t, bars); else step_track_events((uint8_t)t, bars);
        if (!mev_n) continue;
        qsort(mev, mev_n, sizeof mev[0], mev_cmp);
        snprintf(name, sizeof name, "T%u ch%u%s", (unsigned)t + 1u, (unsigned)(proj.track[t].channel & 15u) + 1u, (proj.track[t].flags & SQ_TF_TAPE) ? " TAPE" : "");
        write_track(f, name, 0u, 0u, mev_n);
    }
    fclose(f);
    fprintf(stderr, "%s: %u tracks, %u bars, %u BPM\n", out, (unsigned)ntr, (unsigned)bars, (unsigned)proj.bpm);
    return 0;
}

/* ------------------------------------------------------------ MIDI file reading */
static const uint8_t *mp, *mend;
static uint32_t rd32(void) { uint32_t v = ((uint32_t)mp[0] << 24) | ((uint32_t)mp[1] << 16) | ((uint32_t)mp[2] << 8) | mp[3]; mp += 4; return v; }
static uint32_t rd16(void) { uint32_t v = ((uint32_t)mp[0] << 8) | mp[1]; mp += 2; return v; }
static uint32_t rdvar(void) { uint32_t v = 0u; int k = 0; while (mp < mend && k++ < 4) { uint8_t b = *mp++; v = (v << 7) | (b & 0x7Fu); if (!(b & 0x80u)) break; } return v; }

typedef struct { uint64_t tick; uint8_t ch, note, vel; } non_t;   /* a note-on waiting for its off */

static int mid2sgq(const char *in, const char *out, const char *base)
{
    static uint8_t file[1u << 22];
    static non_t open_[2048];
    uint8_t keep_bars[SQ_TRACKS] = {0};
    FILE *f = fopen(in, "rb");
    size_t n;
    uint32_t fmt, ntrk, div, k, tempo_us = 500000u, dropped = 0u, cut = 0u, total = 0u;
    uint64_t longest = 0u;
    uint16_t used[SQ_CHANNELS] = {0};
    if (!f) { fprintf(stderr, "cannot read %s\n", in); return 2; }
    n = fread(file, 1, sizeof file, f); fclose(f);
    if (n < 14 || memcmp(file, "MThd", 4)) { fprintf(stderr, "%s is not a MIDI file\n", in); return 2; }
    sq_project_init(&proj);
    if (base) {
        FILE *b = fopen(base, "rb");
        size_t bn = b ? fread(img, 1, sizeof img, b) : 0u;
        if (b) fclose(b);
        if (!bn || sq_deserialize(&proj, img, (uint32_t)bn)) { fprintf(stderr, "%s is not a SAGGA project image\n", base); return 2; }
    }
    mp = file + 8; mend = file + n;
    fmt = rd16(); ntrk = rd16(); div = rd16();
    if (div & 0x8000u) { fprintf(stderr, "SMPTE timing is not handled\n"); return 2; }
    if (!div) div = 96u;
    (void)fmt;
    for (k = 0; k < ntrk && mp + 8 <= mend; k++) {
        uint32_t len, i, nopen = 0u;
        const uint8_t *tend;
        uint64_t tick = 0u;
        uint8_t running = 0u;
        if (memcmp(mp, "MTrk", 4)) break;
        mp += 4; len = rd32(); tend = mp + len; if (tend > mend) tend = mend;
        while (mp < tend) {
            uint32_t dt = rdvar();
            uint8_t st, d1, d2 = 0u;
            tick += dt;
            if (mp >= tend) break;
            st = *mp;
            if (st == 0xFFu) {                               /* meta */
                uint8_t type = mp[1]; uint32_t ml;
                mp += 2; ml = rdvar();
                if (type == 0x51u && ml == 3u) tempo_us = ((uint32_t)mp[0] << 16) | ((uint32_t)mp[1] << 8) | mp[2];
                mp += ml;
                continue;
            }
            if (st == 0xF0u || st == 0xF7u) { uint32_t sl; mp++; sl = rdvar(); mp += sl; continue; }
            if (st & 0x80u) { running = st; mp++; } else st = running;
            if (!st) { mp++; continue; }
            d1 = *mp++;
            if ((st & 0xF0u) != 0xC0u && (st & 0xF0u) != 0xD0u) d2 = *mp++;
            if ((st & 0xF0u) == 0x90u && d2) {
                if (nopen < sizeof open_ / sizeof open_[0]) { open_[nopen].tick = tick; open_[nopen].ch = st & 15u; open_[nopen].note = d1; open_[nopen].vel = d2; nopen++; }
            } else if ((st & 0xF0u) == 0x80u || ((st & 0xF0u) == 0x90u && !d2)) {
                for (i = 0; i < nopen; i++) if (open_[i].ch == (st & 15u) && open_[i].note == d1) break;
                if (i < nopen) {
                    uint64_t on = open_[i].tick * SQ_TAPE_PPQ / div, off = tick * SQ_TAPE_PPQ / div, dur = off > on ? off - on : 1u;
                    uint8_t t = open_[i].ch;                 /* channel n -> track n */
                    if (off > longest) longest = off;
                    if (on < SQ_TAPE_BARS_MAX * SQ_TAPE_BAR) {
                        if (dur > 65535u) dur = 65535u;
                        if (!used[t]) {                  /* the first note of a channel: its track becomes (or stays) a TAPE, emptied */
                            keep_bars[t] = (base && (proj.track[t].flags & SQ_TF_TAPE)) ? proj.track[t].tape.bars : 0u;
                            proj.track[t].flags = (uint8_t)((proj.track[t].flags | SQ_TF_TAPE) & ~(SQ_TF_DRUM | SQ_TF_FOLLOW));
                            proj.track[t].channel = t; proj.track[t].tape.bars = SQ_TAPE_BARS_MAX; sq_tape_clear(&proj, t); used[t] = 1u;
                        }
                        if (sq_tape_add(&proj, t, (uint16_t)on, (uint16_t)dur, open_[i].note, open_[i].vel) < 0) dropped++; else total++;
                    } else cut++;
                    open_[i] = open_[--nopen];
                }
            }
        }
        mp = tend;
    }
    /* the loops: the file's length rounded up to bars, 16 at most, the same for every tape (they loop together) */
    {
        uint32_t bars = (uint32_t)((longest + SQ_TAPE_BAR - 1u) / SQ_TAPE_BAR), t;
        if (bars < 1u) bars = 1u;
        if (bars > SQ_TAPE_BARS_MAX) { bars = SQ_TAPE_BARS_MAX; }
        for (t = 0; t < SQ_TRACKS; t++) if (used[t]) proj.track[t].tape.bars = (uint8_t)(keep_bars[t] > bars ? keep_bars[t] : bars);   /* (with a base: a tape never shrinks) */
        sq_tape_sanitize(&proj);                              /* (notes past the loop go: counted above as cut) */
        if (tempo_us) { uint32_t bpm = (60000000u + tempo_us / 2u) / tempo_us; if (bpm < 30u) bpm = 30u; if (bpm > 300u) bpm = 300u; proj.bpm = (uint16_t)bpm; }
        n = sq_serialize(&proj, img, sizeof img);
        if (!n) { fprintf(stderr, "the project does not fit an image (too many notes)\n"); return 3; }
        f = fopen(out, "wb");
        if (!f || fwrite(img, 1, n, f) != n) { fprintf(stderr, "cannot write %s\n", out); if (f) fclose(f); return 3; }
        fclose(f);
        fprintf(stderr, "%s: %u notes on %u tapes, %u bars, %u BPM%s%s\n", out, (unsigned)total,
                (unsigned)(used[0] + used[1] + used[2] + used[3] + used[4] + used[5] + used[6] + used[7] + used[8] + used[9] + used[10] + used[11] + used[12] + used[13] + used[14] + used[15]),
                (unsigned)bars, (unsigned)proj.bpm, dropped ? " (TAPE FULL: notes dropped)" : "", cut ? " (past 16 bars: notes cut)" : "");
    }
    return 0;
}

int main(int argc, char **argv)
{
    if (argc >= 4 && !strcmp(argv[1], "sgq2mid")) return sgq2mid(argv[2], argv[3], argc > 4 ? (uint32_t)atoi(argv[4]) : 0u);
    if (argc >= 4 && !strcmp(argv[1], "mid2sgq")) return mid2sgq(argv[2], argv[3], argc > 4 ? argv[4] : 0);
    fprintf(stderr, "usage: sagga_sgqmid sgq2mid IN.sgq OUT.mid [BARS]\n       sagga_sgqmid mid2sgq IN.mid OUT.sgq [BASE.sgq]\n");
    return 1;
}
