/* SPDX-License-Identifier: GPL-3.0-only */
/*
 * SAGGA LINK (0.15) - the Pi's web editor follows the music and plays what you touch. Included by dinghy.c after
 * sagga_store.c (whose app_sysex hands it 30 and 32). Every frame is F0 7D 53 47 CMD ... F7, every byte 7-bit:
 *
 *   30 ON                    (from the Pi) 1: send the positions for the next LINK_SUB_MS (the Pi asks again while a
 *                            page watches), 0: stop
 *   31 PLAY SCENE SONG CLK*3 BPM*2 (STEP PAT)*16          (to the Pi) where everything is: every 16th while asked (and
 *                            at START / STOP). SONG 127: no song; CLK: the clock ticks since START (24 a beat, 21 bits:
 *                            a TAPE track's place in its loop); then each track's step (0..63) and the pattern it plays
 *   32 T VEL GATE FLAGS N NOTE*N                          (from the Pi) play these notes on track T as the track plays
 *                            a step (its channel, key, CHORD, voicing) for GATE * 10 ms; FLAGS bit 0: a TAPE note (the
 *                            key only)
 *
 * Nothing goes out unless the Pi asked (a computer on the port sees no SysEx it did not want); a position that finds
 * the USB busy is skipped (sysex_try_send: the sequencer never waits for the host).
 */
enum { SX_POS_SUB = 0x30, SX_POS = 0x31, SX_PREVIEW = 0x32 };
#define LINK_SUB_MS 6000u

static uint8_t link_on, link_play_last = 255u;
static uint32_t link_until;
#define LINK_TRACKS 16u                          /* 0.28: the message keeps sixteen places (the last four 0): a Pi of 0.27 reads it */
static uint8_t link_out[5u + 3u + 3u + 2u + 2u * LINK_TRACKS + 1u];
static uint8_t aud_note[SQ_POLY_OUT], aud_ch, aud_n;   /* the notes the editor asked to hear, sounding */
static uint32_t aud_off_ms;
static uint32_t link_sent;                              /* (the simulator's dump: positions sent) */

static void link_pos_send(void)
{
    uint8_t *q = link_out;
    uint32_t t, clk = (global_clock - bar_origin) & 0x1FFFFFu, bpm = project.bpm;   /* (0.25: counted from the bar line the metre began on - a tape's loop too) */
    *q++ = 0xF0u; *q++ = 0x7Du; *q++ = 0x53u; *q++ = 0x47u; *q++ = SX_POS;
    *q++ = playing ? 1u : 0u;
    *q++ = (uint8_t)(scene_cursor & 127u);
    *q++ = song_on ? (uint8_t)(song_pos & 127u) : 127u;
    *q++ = (uint8_t)(clk & 127u); *q++ = (uint8_t)((clk >> 7) & 127u); *q++ = (uint8_t)((clk >> 14) & 127u);
    *q++ = (uint8_t)(bpm & 127u); *q++ = (uint8_t)((bpm >> 7) & 127u);
    for (t = 0; t < LINK_TRACKS; t++) {                /* playing: the step sounding (tr[].step is the next one by now) */
        *q++ = t < SQ_TRACKS ? (uint8_t)((playing ? ev[t].step_index : tr[t].step) & 127u)
             : t == LINK_TRACKS - 1u && song_on ? 1u : 0u;   /* 0.32.1: the sixteenth place says the song is on - since 0.30 a
                                                              * song has 128 entries, and its last one is 127, as "no song" is */
        *q++ = t < SQ_TRACKS ? (uint8_t)(tr[t].pattern & 127u) : 0u;
    }
    *q++ = 0xF7u;
    link_play_last = playing;                          /* (START / STOP: this one says it) */
    if (sysex_try_send(link_out, (uint32_t)(q - link_out)) == 0) link_sent++;
}

/* every 16th (the clock's) */
static void link_16th(void)
{
    if (link_on) link_pos_send();
}

static void aud_stop(void)
{
    uint32_t k;
    for (k = 0; k < aud_n; k++) midi_send(0x80u | aud_ch, aud_note[k], 0u);
    aud_n = 0u;
}

/* once a pass of the main loop */
static void link_tick(void)
{
    if (link_on && time_due(fm1_ms, link_until)) link_on = 0u;
    if (link_on && playing != link_play_last) { link_play_last = playing; link_pos_send(); }
    if (aud_n && time_due(fm1_ms, aud_off_ms)) aud_stop();
}

static void link_preview(const uint8_t *p, uint32_t n)
{
    uint8_t out[SQ_POLY_OUT], t, cnt, m = 0u, vel, k;
    if (n < 5u) return;
    t = p[0];
    cnt = p[4] > SQ_POLY ? (uint8_t)SQ_POLY : p[4];
    if (t >= SQ_TRACKS || !cnt || n < 5u + cnt) return;
    aud_stop();
    if (p[3] & 1u) {                                   /* a TAPE note: as the tape plays it */
        for (k = 0; k < cnt; k++) out[m++] = key_note(t, (int32_t)p[5u + k]);
    } else {                                           /* a step: as the track plays it */
        sq_step_t st;
        sq_step_default(&st);
        for (k = 0; k < SQ_POLY; k++) st.note[k] = k < cnt ? (uint8_t)(p[5u + k] & 127u) : (uint8_t)SQ_NOTE_NONE;
        st.flags |= SQ_STEP_ON | SQ_STEP_SET;
        m = step_notes_x(t, &st, out, 0u);              /* (0.25 FOLLOW MELODY: a note of the tune as it is written) */
    }
    if (!m) return;
    aud_ch = track_ch(t);
    vel = (uint8_t)clamp_i32(p[1], 1, 127);
    for (k = 0; k < m && k < SQ_POLY_OUT; k++) { midi_send(0x90u | aud_ch, out[k], vel); aud_note[k] = out[k]; }
    aud_n = k;
    aud_off_ms = fm1_ms + (uint32_t)clamp_i32(p[2], 1, 100) * 10u;
}

static void link_sysex_in(uint8_t cmd, const uint8_t *p, uint32_t n)
{
    if (cmd == SX_POS_SUB) {
        uint8_t was = link_on;
        link_on = n && p[0] ? 1u : 0u;
        link_until = fm1_ms + LINK_SUB_MS;
        if (link_on && !was) { link_play_last = playing; link_pos_send(); }    /* (where it is, at once) */
    } else if (cmd == SX_PREVIEW) link_preview(p, n);
}
