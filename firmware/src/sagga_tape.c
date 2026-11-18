/* SPDX-License-Identifier: GPL-3.0-only
 * SAGGA SEQ 0.11: TAPE tracks. Included by dinghy.c (one translation unit, like sagga_gen.c).
 *
 * A TAPE track keeps what was played, with its timing (384 ticks a beat, SQ_TAPE_PPQ), in a loop of 1..16 bars; the
 * step grid of the track is not played while it is a TAPE. Recording (REC armed, playing): every note from the keys
 * or from MIDI in goes into the tape where it was played, with its length, on top of what is there (overdub). REC
 * QUANTISED puts the start on the nearest 1/16 as it records; REC FREE keeps it. On playback TAPE QUANT (0..100 %,
 * HOME 6/7 K4) pulls every start toward the grid by that much without touching the tape.
 * Tools on a TAPE track: CLEAR, SHIFT LEFT / RIGHT (a 1/16), DOUBLE (the loop twice as long, the notes repeated).
 * Grid STEP view: the 64 pads are the loop, a pad per 1/64 of it; a pad is lit where a note starts, dim where one
 * sounds; tapping a pad erases what starts under it. */

#define TAPE_Q 48u                                   /* notes scheduled inside the current clock tick, and sounding */
typedef struct { uint32_t on_us, off_us; uint8_t t, ch, note, vel, state; } tape_q_t;   /* state: 0 free, 1 waiting, 2 sounding */
static tape_q_t tape_q[TAPE_Q];
#define TAPE_OPEN 16u
typedef struct { uint8_t src, t, note, vel, used; uint32_t on_tick; } tape_open_t;   /* a note being recorded */
static tape_open_t tape_open[TAPE_OPEN];
static uint32_t tape_tick_us;                        /* when the last clock tick happened (the tape position's origin) */
static uint32_t tape_tick_interval, tape_tick_index;   /* ... its length, and which tick it was (global_clock then) */

static uint8_t track_tape(uint32_t t) { return (project.track[t].flags & SQ_TF_TAPE) ? 1u : 0u; }

/* the loop position in tape ticks for track t, now (between clock ticks too) */
static uint32_t tape_pos(uint32_t t, uint32_t now)
{
    uint32_t len = sq_tape_len_p(&project, (uint8_t)t), clk = len / 16u;      /* the loop in clock ticks (0.25: bars of the metre) */
    uint32_t tick = clk ? tape_tick_index % clk : 0u, frac = 0u;
    if (tape_tick_interval) {
        uint32_t el = (uint32_t)(now - tape_tick_us);
        if (el > tape_tick_interval) el = tape_tick_interval;
        frac = el * 16u / tape_tick_interval;
        if (frac > 15u) frac = 15u;
    }
    return (tick * 16u + frac) % len;
}

static void tape_q_off(tape_q_t *q)
{
    if (q->state == 2u) midi_send(0x80u | q->ch, q->note, 0u);
    q->state = 0u;
}

/* the notes of track t that are sounding or waiting: off (a mute, a kill, STOP) */
static void tape_track_off(uint32_t t)
{
    uint32_t i;
    for (i = 0; i < TAPE_Q; i++) if (tape_q[i].state && tape_q[i].t == t) tape_q_off(&tape_q[i]);
}

static void tape_all_off(void)
{
    uint32_t i;
    for (i = 0; i < TAPE_Q; i++) tape_q_off(&tape_q[i]);
    for (i = 0; i < TAPE_OPEN; i++) tape_open[i].used = 0u;
}

/* a clock tick: schedule the notes of every TAPE track whose (quantised) start falls in this tick */
static void tape_clock_tick(uint32_t now, uint32_t interval)
{
    uint32_t t, i, k;
    tape_tick_us = now;
    tape_tick_interval = interval;
    tape_tick_index = global_clock - bar_origin;       /* (0.25: the loop begins on a bar line - the first, or the one a new metre began on) */
    for (t = 0; t < SQ_TRACKS; t++) {
        const sq_tape_cfg_t *c = &project.track[t].tape;
        uint32_t len, clk, pos;
        uint16_t first, n;
        if (!track_tape(t)) continue;
        len = sq_tape_len_p(&project, (uint8_t)t); clk = len / 16u;
        pos = (tape_tick_index % clk) * 16u;
        if (!track_audible(t) || (mute_mask & (1u << t))) continue;
        sq_tape_range(&project, (uint8_t)t, &first, &n);
        for (i = first; i < (uint32_t)first + n; i++) {
            const sq_tape_ev_t *e = &project.tape_ev[i];
            uint32_t q = sq_tape_quantised(e->on, c->quant, len), d;
            if (q < pos || q >= pos + 16u) continue;
            d = q - pos;
            for (k = 0; k < TAPE_Q; k++) if (!tape_q[k].state) break;
            if (k == TAPE_Q) return;                     /* full: the rest of this tick is lost (48 notes in 20 ms) */
            {
                const sq_track_cfg_t *cfg = &project.track[t];
                int32_t v = (int32_t)e->vel + cfg->vel_offset + mac_vel;
                uint32_t gate = (uint32_t)((uint64_t)e->dur * interval / 16u);
                tape_q_t *qq = &tape_q[k];
                if (project.track[t].delay_ms > 0) d += 0u;    /* (the DELAY of a TAPE track: late only, below) */
                qq->on_us = now + d * interval / 16u + (project.track[t].delay_ms > 0 ? (uint32_t)project.track[t].delay_ms * 1000u : 0u);
                qq->off_us = qq->on_us + (gate ? gate : 1u);
                qq->t = (uint8_t)t; qq->ch = track_ch(t);
                qq->note = key_note(t, e->note);
                qq->vel = (uint8_t)clamp_i32(v, 1, 127);
                qq->state = 1u;
            }
        }
    }
}

static void tape_service(uint32_t now)
{
    uint32_t i;
    for (i = 0; i < TAPE_Q; i++) {
        tape_q_t *q = &tape_q[i];
        if (q->state == 1u && time_due(now, q->on_us)) {
            uint32_t k;
            for (k = 0; k < TAPE_Q; k++)                 /* the same note sounding on the channel: off first (no stuck pair) */
                if (k != i && tape_q[k].state == 2u && tape_q[k].ch == q->ch && tape_q[k].note == q->note) tape_q_off(&tape_q[k]);
            midi_send(0x90u | q->ch, q->note, q->vel);
            q->state = 2u;
        }
        if (q->state == 2u && time_due(now, q->off_us)) tape_q_off(q);
    }
}

/* ---- recording */
static void tape_rec_on(uint8_t src, uint8_t t, uint8_t note, uint8_t vel)
{
    uint32_t i, slot = TAPE_OPEN;
    if (!playing) return;
    for (i = 0; i < TAPE_OPEN; i++) {
        if (tape_open[i].used && tape_open[i].src == src) { slot = i; break; }
        if (!tape_open[i].used && slot == TAPE_OPEN) slot = i;
    }
    if (slot == TAPE_OPEN) slot = 0u;
    tape_open[slot].used = 1u; tape_open[slot].src = src; tape_open[slot].t = t;
    tape_open[slot].note = note; tape_open[slot].vel = vel ? vel : 100u;
    tape_open[slot].on_tick = tape_pos(t, sq_micros());
}

static void tape_rec_off(uint8_t src)
{
    uint32_t i, len, now_tick, dur, on;
    for (i = 0; i < TAPE_OPEN; i++) if (tape_open[i].used && tape_open[i].src == src) break;
    if (i == TAPE_OPEN) return;
    tape_open[i].used = 0u;
    if (!playing || !track_tape(tape_open[i].t)) return;
    len = sq_tape_len_p(&project, tape_open[i].t);
    now_tick = tape_pos(tape_open[i].t, sq_micros());
    on = tape_open[i].on_tick;
    dur = (now_tick + len - on) % len;
    if (!dur) dur = 1u;
    if (rec_quant) on = sq_tape_quantised((uint16_t)on, 100u, len);   /* REC QUANTISED: the start on the 1/16 */
    if (sq_tape_add(&project, tape_open[i].t, (uint16_t)on, (uint16_t)dur, tape_open[i].note, tape_open[i].vel) < 0)
        status_msg("TAPE FULL");
    grid_dirty = ui_dirty = 1u;
}

/* ---- tools (tool_apply hands a TAPE track here) */
static void tape_tool(uint8_t t, uint8_t tool)
{
    sq_tape_cfg_t *c = &project.track[t].tape;
    uint32_t len = sq_tape_len_p(&project, t);
    if (tool == TOOL_CLEAR) { status_num("TAPE CLEARED: NOTES ", sq_tape_clear(&project, t)); }
    else if (tool == TOOL_SHL) { sq_tape_shift(&project, t, -(int32_t)(SQ_TAPE_PPQ / 4u)); status_msg("TAPE: A 1/16 EARLIER"); }
    else if (tool == TOOL_SHR) { sq_tape_shift(&project, t, (int32_t)(SQ_TAPE_PPQ / 4u)); status_msg("TAPE: A 1/16 LATER"); }
    else if (tool == TOOL_DOUBLE) {
        uint16_t first, n;
        uint32_t i;
        if (c->bars * 2u > SQ_TAPE_BARS_MAX) { status_msg("TAPE: 16 BARS IS THE MOST"); return; }
        sq_tape_range(&project, t, &first, &n);
        if (n > SQ_TAPE_MAX - project.tape_n) { status_msg("TAPE FULL"); return; }
        c->bars = (uint8_t)(c->bars * 2u);
        for (i = 0; i < n; i++) {                        /* the copies start past the old loop: they sit after the originals */
            sq_tape_ev_t e = project.tape_ev[first + i];
            sq_tape_add(&project, t, (uint16_t)(e.on + len), e.dur, e.note, e.vel);
        }
        status_num("TAPE DOUBLED: BARS ", c->bars);
    }
    else { status_msg("NOT ON A TAPE TRACK"); return; }
    grid_dirty = ui_dirty = 1u;
}

/* ---- the grid STEP view of a TAPE track: 64 pads = the loop */
static void tape_grid_render(uint32_t t)
{
    const sq_tape_cfg_t *c = &project.track[t].tape;
    uint32_t len = sq_tape_len_p(&project, (uint8_t)t), pos = playing ? tape_pos(t, sq_micros()) : 0xFFFFFFFFu, x, y, i;
    uint16_t first, n;
    uint8_t role[64];
    for (i = 0; i < 64u; i++) role[i] = GL_FAINT;
    sq_tape_range(&project, (uint8_t)t, &first, &n);
    for (i = first; i < (uint32_t)first + n; i++) {
        const sq_tape_ev_t *e = &project.tape_ev[i];
        uint32_t a = (uint32_t)e->on * 64u / len, b = ((uint32_t)e->on + e->dur) * 64u / len, k;
        for (k = a + 1u; k <= b && k < a + 64u; k++) if (role[k % 64u] == GL_FAINT) role[k % 64u] = GL_DIM;
        role[a % 64u] = e->vel >= 110u ? GL_ACCENT : GL_ON;
    }
    if (pos != 0xFFFFFFFFu) role[(pos * 64u / len) % 64u] = GL_PLAY;
    for (y = 0; y < 4u; y++) for (x = 0; x < 16u; x++) gr_put(x, y, role[y * 16u + x]);
    for (x = 0; x < 16u; x++) gr_put(x, 4, x < c->bars ? GL_WHITE : GL_FAINT);              /* row 5: the bars */
    gr_bar(5, 0, 16, ((int32_t)c->quant * 16 + 99) / 100 - 1, GL_CYAN, GL_WHITE);            /* row 6: TAPE QUANT */
    for (x = 0; x < 16u; x++) gr_put(x, 6, GL_OFF);
    for (x = 0; x < 16u; x++) gr_put(x, 7, x == 0u ? GL_ORANGE : x == 1u ? GL_ORANGE : x == 2u ? GL_ORANGE : x == 3u ? GL_ORANGE : GL_OFF);   /* CLEAR SHL SHR DOUBLE */
}

static void tape_grid_pad(uint32_t t, uint8_t x, uint8_t y)
{
    sq_tape_cfg_t *c = &project.track[t].tape;
    uint32_t len = sq_tape_len_p(&project, (uint8_t)t);
    if (y < 4u) {                                        /* erase what starts under the pad */
        uint32_t i = (uint32_t)y * 16u + x, a = i * len / 64u, b = (i + 1u) * len / 64u;
        uint32_t gone = sq_tape_erase(&project, (uint8_t)t, a, b);
        if (gone) status_num("TAPE: ERASED ", gone);
    } else if (y == 4u) {                                /* the bars */
        c->bars = (uint8_t)(x + 1u);
        status_num("TAPE BARS ", c->bars);
        sq_tape_sanitize(&project);                      /* (notes past a shorter loop go) */
    } else if (y == 5u) {                                /* TAPE QUANT */
        c->quant = (uint8_t)((x + 1u) * 100u / 16u);
        if (x == 0u) c->quant = 0u;
        status_num("TAPE QUANT % ", c->quant);
    } else if (y == 7u && x < 4u) {
        static const uint8_t TT[4] = {TOOL_CLEAR, TOOL_SHL, TOOL_SHR, TOOL_DOUBLE};
        tape_tool((uint8_t)t, TT[x]);
    }
    grid_dirty = ui_dirty = 1u;
}
