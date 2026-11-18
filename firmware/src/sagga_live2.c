/* SPDX-License-Identifier: GPL-3.0-only */
/*
 * SAGGA 0.12, the live additions: TAKE, the THROWS, the step's four notes by knob. Included by dinghy.c after
 * sagga_break.c.
 *
 *   TAKE      REC held 0.6 s: what you played on the keys (or sent in over MIDI) during the last loop of the selected
 *             track goes into its pattern, REC or not: the FM-1 always remembers the last notes played (TAKE_N of them,
 *             with the clock tick they began and ended on). Quantised to the step (REC QUANTISED) or with the nudge
 *             (REC FREE), the gate as long as the note was held. UNDO takes it back.
 *   THROWS    FX + SEL + K1..K4: the four macros (INTENSITY, GATE, SWING, FILTER) as throws: from the moment the knob
 *             stops they glide back to 0 over a bar. FX + K alone: the macro stays, as always.
 *   EDIT + SEL + K1..K4: note 1..4 of the cursor step (a knob below 0 takes the note away: a chord of as many as you set).
 */

/* ---- TAKE */
#define TAKE_N 96u
typedef struct { uint8_t t, note, vel, src, open, used, on_phase, step; uint32_t on, off; } take_t;   /* on / off: global_clock; step: the one sounding */
static take_t take_ring[TAKE_N];
static uint8_t take_w;
static void take_clear(void) { uint32_t i; for (i = 0; i < TAKE_N; i++) take_ring[i].vel = 0u; take_w = 0u; }   /* at every start: the clock begins again */

static uint8_t take_phase(uint32_t t)             /* where inside the step the clock is now, 0..99 */
{
    uint32_t now = sq_micros(), el = (uint32_t)(now - ev[t].slot_start_us), ph;
    ph = ev[t].slot_dur_us ? el * 100u / ev[t].slot_dur_us : 0u;
    return (uint8_t)(ph > 99u ? 99u : ph);
}
static void take_note_on(uint8_t src, uint8_t t, uint8_t note, uint8_t vel)
{
    take_t *e;
    if (!playing || t >= SQ_TRACKS) return;
    e = &take_ring[take_w];
    take_w = (uint8_t)((take_w + 1u) % TAKE_N);
    e->t = t; e->note = note; e->vel = vel; e->src = src; e->open = 1u; e->used = 0u;
    e->on = global_clock; e->off = global_clock; e->on_phase = take_phase(t); e->step = ev[t].step_index;
}
static void take_note_off(uint8_t src)
{
    uint32_t i;
    for (i = 0; i < TAKE_N; i++) if (take_ring[i].open && take_ring[i].src == src) { take_ring[i].open = 0u; take_ring[i].off = global_clock; }
}
/* the length a note held `ticks` ticks gets on a track whose step is `div` ticks (rec_close_note's rule) */
static uint8_t take_gate(uint32_t ticks, uint32_t div)
{
    if (!div) return 100u;
    if (ticks <= div) { uint32_t pct = (ticks * 100u + div / 2u) / div; return (uint8_t)(pct < 5u ? 5u : pct > 100u ? 100u : pct); }
    { uint32_t steps10 = (ticks * 10u + div / 2u) / div; if (steps10 < 18u) return 101u; { uint32_t n = (steps10 + 5u) / 10u; return (uint8_t)(100u + (n > 64u ? 64u : n)); } }
}
static void take_apply(uint32_t t)
{
    const sq_track_cfg_t *c = &project.track[t];
    sq_step_t *row = project.step[t][tr[t].pattern];
    uint32_t div = base_div_ticks(t), len_ticks = (uint32_t)(c->length - c->start) * div, i, n = 0u;
    if (track_tuplet(t)) {                               /* (0.25: a polyrhythm's loop: its steps are not whole ticks) */
        uint16_t num; uint8_t den;
        div_frac_x(t, 0u, &num, &den);
        len_ticks = ((uint32_t)(c->length - c->start) * num + den / 2u) / den;
    }
    uint32_t from;
    if (!playing || track_tape(t)) { status_msg(track_tape(t) ? "TAKE: A TAPE RECORDS BY ITSELF" : "TAKE: WHILE PLAYING"); return; }
    from = global_clock > len_ticks ? global_clock - len_ticks : 0u;
    for (i = 0; i < TAKE_N; i++) if (take_ring[i].vel && !take_ring[i].used && take_ring[i].t == t && take_ring[i].on >= from && take_ring[i].on < global_clock && take_ring[i].on >= tr[t].anchor) n++;
    if (!n) { status_msg("TAKE: NOTHING PLAYED IN THE LAST LOOP"); return; }
    undo_begin();
    undo_add((uint8_t)t, tr[t].pattern);
    for (i = 0; i < TAKE_N; i++) {
        take_t *e = &take_ring[i];
        sq_step_t *s;
        uint8_t stp, k;
        int8_t nudge = 0;
        uint32_t held;
        if (!e->vel || e->used || e->t != t || e->on < from || e->on >= global_clock || e->on < tr[t].anchor) continue;
        sq_rec_target(e->step, c->start, c->length, c->direction, e->on_phase, rec_quant, &stp, &nudge);   /* as REC places a note */
        if (stp >= c->length || stp < c->start) continue;
        s = &row[stp];
        if (!(s->flags & SQ_STEP_ON) || !(s->flags & SQ_STEP_SET)) { for (k = 0; k < SQ_POLY; k++) s->note[k] = SQ_NOTE_NONE; s->note[0] = key_store(t, e->note); }
        else { for (k = 0; k < SQ_POLY; k++) { if (s->note[k] == key_store(t, e->note)) break; if (s->note[k] == SQ_NOTE_NONE) { s->note[k] = key_store(t, e->note); break; } } }
        s->flags |= SQ_STEP_ON | SQ_STEP_SET;
        s->velocity = e->vel ? e->vel : 100u;
        held = (e->open ? global_clock : e->off) - e->on;
        s->length = take_gate(held ? held : 1u, div);
        s->nudge = (int8_t)clamp_i32(nudge * (int32_t)SQ_NUDGE_MAX / 50, -(int32_t)SQ_NUDGE_MAX, (int32_t)SQ_NUDGE_MAX);
        e->used = 1u;                                                   /* (taken: not twice) */
    }
    activate_row(t, row);
    regia_touched((uint8_t)t);
    { char *p = msg_buf; p = put_s(p, "TAKE: "); p = put_u(p, n); p = put_s(p, " NOTES INTO T"); p = put_u(p, t + 1u); finish(p); status_msg(msg_buf); }
    ui_dirty = grid_dirty = 1u;
}

/* ---- THROWS: a macro marked as a throw glides back to 0 over a bar from its last detent */
static uint8_t throw_on;                           /* bit per macro */
static uint32_t throw_last_ms[4];
static int32_t throw_from[4];
static uint32_t throw_t0[4];
static int32_t macro_get(uint8_t i) { return i == 0u ? mac_vel : i == 1u ? mac_gate : i == 2u ? mac_swing : mac_filt; }
static void throw_mark(uint8_t i, uint8_t th)
{
    i &= 3u;
    if (th) { throw_on |= (uint8_t)(1u << i); throw_last_ms[i] = fm1_ms; throw_t0[i] = 0u; }
    else throw_on &= (uint8_t)~(1u << i);
}
static void throw_service(void)
{
    uint32_t i, bar_ms = 4u * 24u * (60000000u / ((project.bpm ? project.bpm : 120u) * 24u)) / 1000u;
    if (!throw_on) return;
    for (i = 0; i < 4u; i++) {
        int32_t v;
        if (!(throw_on & (1u << i))) continue;
        if ((uint32_t)(fm1_ms - throw_last_ms[i]) < 150u) continue;          /* the knob still turns */
        if (!throw_t0[i]) { throw_t0[i] = fm1_ms; throw_from[i] = macro_get((uint8_t)i); }
        if (!throw_from[i]) { throw_on &= (uint8_t)~(1u << i); continue; }
        {
            uint32_t el = (uint32_t)(fm1_ms - throw_t0[i]);
            if (el >= bar_ms) v = 0;
            else v = throw_from[i] - throw_from[i] * (int32_t)el / (int32_t)bar_ms;   /* (|from| <= 100, el < bar_ms <= 8000: no 64-bit division, the JieLi library has none signed) */
        }
        if (v != macro_get((uint8_t)i)) {
            const char *mt = msg_text; uint32_t mu = msg_until;
            macro_set((uint8_t)i, v);                                   /* (its message only when nothing else is said) */
            if (mt && mt != msg_buf && !time_due(fm1_ms, mu)) { msg_text = mt; msg_until = mu; }
        }
        if (!v) throw_on &= (uint8_t)~(1u << i);
    }
}

/* ---- EDIT + SEL + K1..K4: the step's notes one a knob */
static void step_note_turn(uint32_t t, sq_step_t *s, uint32_t k, int32_t d)
{
    int32_t v;
    uint32_t j;
    if (k >= SQ_POLY) return;
    if (s->note[k] == SQ_NOTE_NONE) {
        if (d <= 0) return;
        for (j = k; j > 0u; j--) if (s->note[j - 1u] == SQ_NOTE_NONE) { status_msg("THE NOTE BEFORE IT FIRST"); return; }
        v = (k ? (int32_t)s->note[k - 1u] : (int32_t)PEN(t)) + d - 1;
    } else v = (int32_t)s->note[k] + d;
    if (v < 0) { if (k) { s->note[k] = SQ_NOTE_NONE; for (j = k + 1u; j < SQ_POLY; j++) s->note[j] = SQ_NOTE_NONE; status_num("NOTES ", k); } return; }
    s->note[k] = (uint8_t)clamp_i32(v, 0, 127);
    s->flags |= SQ_STEP_SET;
    if (k == 0u && !track_drum(t) && !track_break(t)) PEN(t) = s->note[0];
    if (!(s->flags & SQ_STEP_ON)) preview_note(t, s->note[k]);
    regia_touched((uint8_t)t);
}

/* ---- 0.12: the long notes and the legato as one block (the screen's strip, the key LEDs, the grid)
 * Bits per step (0..63) of track t's playing pattern: tail (covered by a note begun before), bridge (the gap after the
 * step is inside a note, or the step is TIEd to the next), half (a note of 1.5 steps ends in its first half). A note
 * that runs past the loop's end covers its first steps. Drum tracks and tapes have no blocks. */
static void note_blocks(uint32_t t, uint64_t *tail, uint64_t *bridge, uint64_t *half)
{
    const sq_track_cfg_t *c = &project.track[t];
    const sq_step_t *row = project.step[t][tr[t].pattern];
    uint32_t lo = c->start, n = c->length > lo ? (uint32_t)c->length - lo : 1u, j;
    *tail = *bridge = *half = 0u;
    if (track_tape(t) || track_drum(t)) return;
    for (j = lo; j < c->length; j++) {
        const sq_step_t *s = &row[j];
        uint32_t halves, k;
        if (!(s->flags & SQ_STEP_ON)) continue;
        halves = s->length <= 100u ? 2u : s->length == 101u ? 3u : 2u * ((uint32_t)s->length - 100u);
        if (halves > 2u * n) halves = 2u * n;
        for (k = 1; k < halves; k++) {                                      /* half-step k of the note (0, 1: the hit's own step) */
            uint32_t cell = lo + (j - lo + k / 2u) % n;
            if (k & 1u) { if (k + 1u < halves) *bridge |= (uint64_t)1u << cell; }   /* its second half: the gap after it is inside the note */
            else if (k + 1u < halves) *tail |= (uint64_t)1u << cell;              /* a whole step covered */
            else *half |= (uint64_t)1u << cell;                                     /* the note ends in its first half */
        }
        if (s->flags & SQ_STEP_LEGATO) *bridge |= (uint64_t)1u << j;
    }
}
