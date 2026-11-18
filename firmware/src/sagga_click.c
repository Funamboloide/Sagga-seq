/* SPDX-License-Identifier: GPL-3.0-only */
/*
 * SAGGA 0.26, THE CLICK: a metronome and a count before a recording. Included by dinghy.c after sagga_live3.c.
 *
 *   CLICK     SAVE 5 K1: OFF, REC (while REC is on and it plays), PLAY (whenever it plays). A click on every beat of
 *             the METRE - a 7/8 divided 2+2+3 clicks three times a bar, a 6/8 twice - the bar line louder.
 *   COUNT IN  SAVE 5 K2: OFF, 1 BAR, 2 BARS. PLAY with REC on (the FM-1 the clock's master) first counts those bars
 *             of the metre - with the click, whatever K1 says - and starts on the bar line after them: the transport,
 *             the clock and the START to the synths begin there. PLAY again while it counts: nothing starts. A note
 *             played while it counts sounds (if MIDI IN plays the track) and is not written anywhere.
 *   OUT       SAVE 5 K3: FM-1 - the machine's own sound, a short tone (2000 Hz on the bar line, 1000 Hz on a beat) on
 *             its speaker and its line out; or a MIDI channel 1-16: a note on it, the bar line at a higher velocity
 *             (the rim shot or the claves of a drum machine).
 *   LEVEL     SAVE 5 K4: 1-10, how loud (the FM-1's sound; the note's velocity). SEL + K4: the NOTE of a MIDI click.
 *
 * THE FM-1'S OWN SOUND AND TIME. The sound is made by the audio interrupt (app_audio) half a buffer at a time: 256
 * frames, 5.8 ms. A half made now is heard after the one that plays now: asked on its own tick, a click would come out
 * 6 to 12 ms late, and never twice the same. So it is ASKED AHEAD: at every tick of the clock the ticks that begin
 * within the next 12 ms are looked at, and a beat among them is asked for the moment it will fall on (clk_req_at, in
 * the timer's own ticks - the interrupt cannot call sq_micros). The interrupt, when the half it is making holds that
 * moment, begins the click on that very frame. Only the first click after PLAY without a count, which nobody could
 * announce, comes out as soon as it can. A MIDI click is a note like any other: sent on its tick.
 * While nothing sounds the interrupt does what it did since 0.22 - it acknowledges the half and nothing else
 * (platform.c: app_audio_wants) - so a machine with the click off, or on a MIDI channel, is the machine it was.
 */
#ifdef DINGHY_HOST
#define CLK_BLOCK_AT(n) (-(n))                   /* the simulator makes a block when its time has gone by: it began n frames ago */
#else
#define CLK_BLOCK_AT(n) (n)                      /* the FM-1 fills the half that plays after the one playing: it begins n frames from now */
#endif
#define CLK_TICKS_FRAME 544                      /* the timer's ticks a frame: 24 000 000 / 44 100 */
#define CLK_AHEAD_US 12000u                      /* two halves of the audio buffer */
#define CLK_NOTE_US 40000u                       /* a MIDI click's note lasts this long */

static uint8_t click_wanted(void)
{
    return (uint8_t)(project.ext.click == SQ_CLICK_PLAY || (project.ext.click == SQ_CLICK_REC && record_arm));
}
static uint32_t clk_lead_ticks(uint32_t interval)       /* the clock ticks that make CLK_AHEAD_US */
{
    uint32_t n = 1u;
    if (!interval) return 1u;
    while (n < 6u && n * interval < CLK_AHEAD_US) n++;
    return n;
}
/* what tick `in` of a bar is (ticks since its line): 0 nothing, 1 a beat of the metre, 2 the bar line */
static uint8_t clk_kind(uint32_t in)
{
    if (in % 6u || !((bar_bt() >> (in / 6u)) & 1u)) return 0u;
    return (uint8_t)(in ? 1u : 2u);
}
static void clk_said(uint8_t kind, uint32_t tick)
{
    clk_count++; clk_last = kind; clk_last_tick = tick;
}
/* the FM-1's own sound, to begin at `at_us` (sq_micros' time; the past: as soon as it can) */
static void clk_ask(uint8_t kind, uint32_t at_us, uint32_t tick)
{
    uint32_t nowu = sq_micros();
    clk_req = 0u;
    clk_req_level = sq_click_level(&project.ext);
    clk_req_at = fm1_ticks() + (uint32_t)((int32_t)(at_us - nowu)) * FM1_TICKS_PER_US;
    clk_req = kind;
    clk_said(kind, tick);
#ifdef DINGHY_HOST
    printf("%6u ms  CLICK %s tick %u in %d us\n", fm1_ms, kind == 2u ? "bar" : "beat", (unsigned)tick, (int)(int32_t)(at_us - nowu));
#endif
}
/* a MIDI click: the note, now */
static void clk_midi(uint8_t kind, uint32_t now, uint32_t tick)
{
    uint8_t ch = (uint8_t)(project.ext.click_out - 1u), note = sq_click_note(&project.ext);
    if (ch >= ch_limit()) ch = (uint8_t)(ch_limit() - 1u);                    /* (one USB port: 15 and 16 are the grid's) */
    if (clk_off_ch != 255u) midi_send(0x80u | clk_off_ch, clk_off_note, 0u);
    midi_send(0x90u | ch, note, sq_click_vel(&project.ext, (uint8_t)(kind == 2u)));
    clk_off_ch = ch; clk_off_note = note; clk_off_us = now + CLK_NOTE_US;
    clk_said(kind, tick);
}
/* nothing sounds, nothing waits (a stop, a panic) */
static void click_quiet(void)
{
    clk_req = 0u;
    if (clk_off_ch != 255u) { midi_send(0x80u | clk_off_ch, clk_off_note, 0u); clk_off_ch = 255u; }
}
/* every pass of the main loop: a MIDI click's note ends */
static void click_service(uint32_t now)
{
    if (clk_off_ch != 255u && time_due(now, clk_off_us)) { midi_send(0x80u | clk_off_ch, clk_off_note, 0u); clk_off_ch = 255u; }
}
/* every tick of the clock while it plays (seq_clock_tick, at its end: the bar and its beats are what this tick left
 * them), `now` the tick's own time */
static void click_tick(uint32_t now)
{
    uint32_t g = global_clock, interval, n, k;
    uint8_t kind;
    if (!click_wanted()) { clk_next = g + 1u; return; }
    if (project.ext.click_out) {
        kind = clk_kind((g - bar_origin) % bar_ticks());
        if (kind) clk_midi(kind, now, g);
        clk_next = g + 1u;
        return;
    }
    interval = current_clock_interval();
    n = clk_lead_ticks(interval);
    if ((int32_t)(clk_next - g) < 0) clk_next = g;       /* (nobody looked at this tick: the first after PLAY, the click just switched on) */
    for (k = clk_next; (int32_t)(k - (g + n)) <= 0; k++) {
        kind = clk_kind((k - bar_origin) % bar_ticks());
        if (kind) clk_ask(kind, now + (k - g) * interval, k);
    }
    clk_next = g + n + 1u;
}

/* ---- the count */
static void count_cancel(void)
{
    if (!cnt_on) return;
    cnt_on = 0u;
    click_quiet();
    status_msg("COUNT IN STOPPED");
    ui_dirty = grid_dirty = 1u;
}
static void count_begin(void)
{
    cnt_len = (uint16_t)((uint32_t)project.ext.count_in * bar_ticks());
    cnt_pos = 0u; cnt_ahead = 0u;
    cnt_next_us = sq_micros() + CLK_AHEAD_US + 3000u;    /* (its first click can still be put on its frame) */
    cnt_on = 1u;
    status_msg(project.ext.count_in > 1u ? "COUNT IN: 2 BARS" : "COUNT IN: 1 BAR");
    ui_dirty = grid_dirty = 1u;
}
/* what tick p of the count is: its bars are the metre's; past its end: the first ticks of what plays after it */
static uint8_t cnt_kind(uint32_t p)
{
    if (p >= cnt_len && !click_wanted()) return 0u;
    return clk_kind((p >= cnt_len ? p - cnt_len : p) % bar_ticks());
}
/* PLAY, to start: at once - or, with REC on and a COUNT IN (the FM-1 the master of the clock), after the count */
static void transport_start_ask(void)
{
    if (cnt_on) { count_cancel(); return; }
    if (record_arm && project.ext.count_in && project.clock_mode == SQ_CLOCK_MASTER) count_begin();
    else transport_start();
}
/* every pass of the main loop: the count's ticks, at the tempo; after the last the transport starts, on time */
static void count_service(uint32_t now)
{
    uint32_t interval, guard = 0u;
    if (!cnt_on) return;
    if (playing || project.clock_mode != SQ_CLOCK_MASTER) { cnt_on = 0u; return; }   /* (something else started it: no count) */
    interval = master_clock_interval();
    while (cnt_on && time_due(now, cnt_next_us) && guard++ < 8u) {
        uint32_t at = cnt_next_us, n, k;
        uint8_t kind;
        if (cnt_pos >= cnt_len) {                        /* the count is over: this tick is the transport's first */
            cnt_on = 0u;
            transport_start();
            next_master_clock_us = at; last_master_tick_us = at;
            clk_next = cnt_ahead > cnt_len ? cnt_ahead - cnt_len : 0u;   /* (the clicks already asked for: not asked again) */
            return;
        }
        kind = cnt_kind(cnt_pos);
        if (kind) {                                      /* the screen counts: the bar and the beat */
            char *p = msg_buf;
            uint32_t in = cnt_pos % bar_ticks(), s, beat = 0u;
            for (s = 0; s <= in / 6u; s++) if ((bar_bt() >> s) & 1u) beat++;
            p = put_s(p, "COUNT IN "); p = put_u(p, cnt_pos / bar_ticks() + 1u); p = put_s(p, "."); p = put_u(p, beat); finish(p);
            status_msg(msg_buf);
            ui_dirty = 1u;
        }
        if (project.ext.click_out) { if (kind) clk_midi(kind, at, cnt_pos); }
        else {
            n = clk_lead_ticks(interval);
            if (cnt_ahead < cnt_pos) cnt_ahead = cnt_pos;
            for (k = cnt_ahead; k <= cnt_pos + n; k++) {
                kind = cnt_kind(k);
                if (kind) clk_ask(kind, at + (k - cnt_pos) * interval, k);
            }
            cnt_ahead = cnt_pos + n + 1u;
        }
        cnt_pos++;
        cnt_next_us = at + interval;
    }
}

/* ---- the sound (the audio interrupt; on a computer the simulator's loop) */
static uint8_t app_audio_wants(void) { return (uint8_t)(clk_req || clk_voice.on); }
static void app_audio(int32_t *out, uint32_t n)
{
    uint8_t rq = clk_req;
    uint32_t from = 0u;
    if (rq) {                                            /* a click waits: does it begin in this block? */
        int32_t dt = (int32_t)(clk_req_at - fm1_ticks());
        int32_t fr = dt / CLK_TICKS_FRAME - CLK_BLOCK_AT((int32_t)n);
        if (fr < (int32_t)n) {
            from = fr > 0 ? (uint32_t)fr : 0u;
            sq_click_start(&clk_voice, (uint8_t)(rq == 2u), clk_req_level);
            clk_req = 0u;
        }
    }
    if (clk_voice.on) sq_click_render(&clk_voice, out, n, from);
}

/* ---- SAVE 5: the knobs */
static void click_knobs(int32_t d1, int32_t d2, int32_t d3, int32_t d4, uint8_t sel)
{
    sq_ext_t *x = &project.ext;
    char *p = msg_buf;
    if (d1) {
        static const char *const N[SQ_CLICKS] = {"CLICK OFF", "CLICK WHILE REC IS ON", "CLICK WHENEVER IT PLAYS"};
        x->click = change_u8(x->click, d1, 0u, SQ_CLICKS - 1u);
        if (!x->click) click_quiet();
        status_msg(N[x->click]);
    }
    if (d2) {
        x->count_in = change_u8(x->count_in, d2, 0u, SQ_COUNT_IN_MAX);
        status_msg(!x->count_in ? "NO COUNT IN" : x->count_in == 1u ? "COUNT IN 1 BAR: REC, THEN PLAY" : "COUNT IN 2 BARS: REC, THEN PLAY");
    }
    if (d3) {
        click_quiet();
        x->click_out = change_u8(x->click_out, d3, 0u, ch_limit());
        if (!x->click_out) status_msg("CLICK: THE FM-1'S OWN SOUND");
        else { p = put_s(p, "CLICK: NOTE "); p = put_u(p, sq_click_note(x)); p = put_s(p, " ON CHANNEL "); p = put_u(p, x->click_out); finish(p); status_msg(msg_buf); }
    }
    if (d4 && sel) {
        char nm[5];
        x->click_note = (uint8_t)clamp_i32((int32_t)sq_click_note(x) + d4, 1, 127);
        sq_note_name(x->click_note, nm);
        p = put_s(p, "CLICK NOTE "); p = put_u(p, x->click_note); p = put_s(p, " "); p = put_s(p, nm); finish(p);
        status_msg(msg_buf);
    } else if (d4) {
        x->click_level = (uint8_t)clamp_i32((int32_t)sq_click_level(x) + d4, 1, (int32_t)SQ_CLICK_LEVELS);
        status_num("CLICK LEVEL ", x->click_level);
    }
}
