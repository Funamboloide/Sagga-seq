/* SPDX-License-Identifier: GPL-3.0-only */
/*
 * SAGGA 0.26, THE KEYBOARD'S EXPRESSION. Included by dinghy.c after sagga_click.c, before the MIDI IN.
 *
 * Until 0.25 a keyboard played through the FM-1 lost everything but its notes: the pitch wheel and the aftertouch were
 * dropped, a controller (the pedal, the modulation wheel) only fed LEARN, CC CAPTURE and the MOD MATRIX's CC IN.
 *
 *   THROUGH   Whenever the keyboard's notes are played through (REC on, or MIDI IN ALWAYS: SAVE 4 K4), what it sends
 *             besides them goes where they go - to the channel of the track they play (the selected one; a LOOP's):
 *             the pitch wheel, the channel's aftertouch, a key's own aftertouch (to the note that key plays now),
 *             every controller. LEARN and CC CAPTURE still take a controller first; CC IN still sees it.
 *             What was left ON on a channel is put back there: the pedal's release goes to the channel its press
 *             went to, wherever the track is by then; a wheel left off its centre is centred on the channel it
 *             bent when the next move goes to another; a STOP or a PANIC lets the pedal go, centres the wheel and
 *             takes the aftertouch off on the channels they were left on.
 *   RECORDED  With REC on while it plays, on a track of steps:
 *             - the pitch wheel, the aftertouch and a controller are written in the track's LANES, as the ENV knob
 *               writes them (0.10: the value on the steps as they play, while it moves and 0.4 s after): in the lane
 *               that already sends that control; else in one that is off, or that nobody ever wrote (no value on a
 *               step, no base: a new track's six lanes all have a controller, most never used), which is taken for
 *               it - from the last one, never lane 1 (the FILTER macro's); SLIDE on, so the value glides from step
 *               to step - the screen says which. The switches (64-69), the bank and the data entry, the channel's
 *               mode messages are never given a lane by themselves (a lane set to one by hand records it).
 *             - the PEDAL is not a lane: a pedal is timing, and a value a step cannot keep it (let go and pressed
 *               again inside one step, as a pianist does at every chord, it would read as never let go). The notes
 *               played while it is down are recorded as long as they SOUND - to the pedal's release - on a track of
 *               steps, on a TAPE and in TAKE: played back they need no pedal.
 *             On a TAPE track the wheel and the controllers pass and are not kept (a tape keeps notes).
 */
static uint8_t ped_down;                         /* the pedal is down, as the keyboard said last */
static uint8_t ped_ch = 255u;                    /* the channel its press went to (255: none is held down by us) */
static uint32_t ped_late[4];                     /* the keys let go while it was down: their notes still sound */
static uint8_t bend_ch = 255u, at_ch = 255u;     /* the channel a wheel off its centre, an aftertouch above 0 went to */
static uint8_t thru_lane_said = 255u;            /* the control "no free lane" was said for (once a control) */

static uint8_t thru_track(void) { return (uint8_t)((vg_rec_t < SQ_TRACKS ? vg_rec_t : selected_track) & 15u); }
static uint8_t thru_on(void) { return (uint8_t)(record_arm || project.ext.in_thru); }

/* the name of a control, for the screen: "CC 1", "THE PITCH WHEEL", "THE AFTERTOUCH" */
static char *thru_name(char *p, uint8_t ctl)
{
    if (ctl == SQ_CC_BEND) return put_s(p, "THE PITCH WHEEL");
    if (ctl == SQ_CC_AT) return put_s(p, "THE AFTERTOUCH");
    p = put_s(p, "CC "); return put_u(p, ctl);
}
/* a control that gets a lane by itself when it is recorded and has none */
static uint8_t thru_auto(uint8_t ctl)
{
    if (ctl == SQ_CC_BEND || ctl == SQ_CC_AT) return 1u;
    if (ctl == 0u || ctl == 6u || ctl == 32u || ctl == 38u || (ctl >= 64u && ctl <= 69u) || ctl >= 96u) return 0u;
    return 1u;
}
/* a lane nobody wrote: no value on any step of the track's patterns, no base, none in a scene - and not being recorded */
static uint8_t lane_unused(uint8_t t, uint32_t n)
{
    uint32_t p, k;
    if (project.track[t].lane_base[n] != SQ_LANE_NONE || (lane_rec[t] & (1u << n))) return 0u;
    for (p = 0; p < SQ_SCENES; p++) if (project.scene[p].lane[t][n] != SQ_LANE_NONE) return 0u;
    for (p = 0; p < SQ_PATTERNS; p++)
        for (k = 0; k < SQ_STEPS; k++) if (project.step[t][p][k].lane[n] != SQ_LANE_NONE) return 0u;
    return 1u;
}
/* REC on, it plays, a track of steps: the control's value is written on the steps as they play (arm_step: lane_rec).
 * The lane that sends that control; else one that is off; else one nobody ever wrote (a new track's six lanes all
 * have a controller, most never used) - from the last, never lane 1 (the FILTER macro's). A lane the keyboard records
 * in sends its values on the steps that do not play too: SLIDE if nobody had written it, else TRIGLESS. */
static void thru_rec(uint8_t t, uint8_t ctl, uint8_t v)
{
    sq_track_cfg_t *c = &project.track[t];
    int32_t n, got = -1;
    uint8_t fresh = 0u;
    char *p = msg_buf;
    if (!record_arm || !playing || track_tape(t)) return;
    for (n = (int32_t)SQ_LANES - 1; n >= 0; n--)
        if (c->lane_cc[n] == ctl && !(c->lane_flags[n] & SQ_LF_NRPN)) got = n;
    if (got < 0) {
        if (!thru_auto(ctl)) return;
        for (n = (int32_t)SQ_LANES - 1; n >= 0 && got < 0; n--) if (c->lane_cc[n] == SQ_LANE_NONE) got = n;
        for (n = (int32_t)SQ_LANES - 1; n >= 1 && got < 0; n--) if (lane_unused(t, (uint32_t)n)) got = n;
        if (got < 0) {
            if (thru_lane_said != ctl) { thru_lane_said = ctl; p = put_s(p, "NO FREE LANE FOR "); p = thru_name(p, ctl); finish(p); status_msg(msg_buf); }
            return;
        }
        c->lane_cc[got] = ctl; c->lane_base[got] = SQ_LANE_NONE; c->lane_flags[got] = SQ_LF_SLIDE; c->lane_hi[got] = 0u;
        fresh = 1u;
    } else if (!(lane_rec[t] & (1u << got))) {
        if (!(c->lane_flags[got] & (SQ_LF_SLIDE | SQ_LF_TRIGLESS)))
            c->lane_flags[got] |= (uint8_t)(lane_unused(t, (uint32_t)got) ? SQ_LF_SLIDE : SQ_LF_TRIGLESS);
        fresh = 1u;
    }
    if (fresh) {
        p = put_s(p, "LANE "); p = put_u(p, (uint32_t)got + 1u); p = put_s(p, " RECORDS "); p = thru_name(p, ctl); finish(p);
        status_msg(msg_buf);
        ui_dirty = grid_dirty = 1u;
    }
    lane_rec[t] |= (uint8_t)(1u << got);
    lane_rec_val[t][got] = (uint8_t)(v & 127u);
    lane_rec_ms = fm1_ms;
}
/* a key let go while the pedal holds its note: what records it goes on counting */
static uint8_t ped_holds(uint8_t note)
{
    if (!ped_down) return 0u;
    ped_late[(note >> 5) & 3u] |= 1u << (note & 31u);
    return 1u;
}
/* the notes the pedal held are over: the key struck again (one note), the pedal let go (255: all of them) */
static void ped_release(uint8_t note)
{
    uint32_t n;
    for (n = 0; n < 128u; n++) {
        uint32_t b = 1u << (n & 31u);
        if ((note != 255u && n != note) || !(ped_late[n >> 5] & b)) continue;
        ped_late[n >> 5] &= ~b;
        rec_close_note((uint8_t)n);
        tape_rec_off((uint8_t)n);
        take_note_off((uint8_t)n);
    }
}
/* a STOP, a PANIC: nothing of the keyboard's is left on a channel */
static void thru_expr_off(void)
{
    if (ped_ch != 255u) { midi_send(0xB0u | ped_ch, 64u, 0u); ped_ch = 255u; }
    if (bend_ch != 255u) { midi_send(0xE0u | bend_ch, 0u, 64u); bend_ch = 255u; }
    if (at_ch != 255u) { midi_send(0xD0u | at_ch, 0u, 0u); at_ch = 255u; }
    ped_release(255u);
}
/* a message of the keyboard's that is not a note (MIDI IN): the pedal is followed whatever (the notes' lengths need
 * it); the rest only while its notes are played through */
static void thru_ctl(uint8_t st, uint8_t d1, uint8_t d2)
{
    uint8_t kind = (uint8_t)(st & 0xF0u), t = thru_track(), ch = track_ch(t);
    d1 &= 127u; d2 &= 127u;
    if (kind == 0xB0u && d1 == 64u) {                    /* the pedal */
        if (d2 >= 64u) {
            ped_down = 1u;
            if (thru_on()) { ped_ch = ch; midi_send(0xB0u | ch, 64u, d2); }
        } else {
            ped_down = 0u;
            if (ped_ch != 255u) { midi_send(0xB0u | ped_ch, 64u, d2); ped_ch = 255u; }
            else if (thru_on()) midi_send(0xB0u | ch, 64u, d2);
            ped_release(255u);
        }
        return;
    }
    if (!thru_on()) return;
    if (kind == 0xE0u) {                                 /* the pitch wheel: d2 the coarse value, 64 the centre */
        if (bend_ch != 255u && bend_ch != ch) midi_send(0xE0u | bend_ch, 0u, 64u);
        midi_send(0xE0u | ch, d1, d2);
        bend_ch = (uint8_t)(d2 == 64u && d1 == 0u ? 255u : ch);
        thru_rec(t, SQ_CC_BEND, d2);
    } else if (kind == 0xD0u) {                          /* the channel's aftertouch */
        if (at_ch != 255u && at_ch != ch) midi_send(0xD0u | at_ch, 0u, 0u);
        midi_send(0xD0u | ch, d1, 0u);
        at_ch = (uint8_t)(d1 ? ch : 255u);
        thru_rec(t, SQ_CC_AT, d1);
    } else if (kind == 0xA0u) {                          /* a key's own aftertouch: to the note that key plays now */
        if (ext_ch[d1] != 255u) midi_send(0xA0u | ext_ch[d1], ext_out[d1], d2);
    } else if (kind == 0xB0u) {
        midi_send(0xB0u | ch, d1, d2);
        thru_rec(t, d1, d2);
    }
}
