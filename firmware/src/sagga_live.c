/* SPDX-License-Identifier: GPL-3.0-only */
/*
 * SAGGA LIVE - the live tools of 0.5. Included by dinghy.c after sagga_store.c.
 *
 *   QUANTISE  when queued patterns, scenes and mutes happen (dinghy.c: quant_tick); set here
 *   MORPH     the CC lanes' base values glide from the scene playing to another scene (the grid's FX view, PERF + SEL
 *             + K3 on the panel, SAGGA REMOTE). A scene keeps the base values it had when it was stored.
 *   LOOP / REPEAT  one gesture, in dinghy.c (loop_press): a tap stays, a hold lands in time
 *   RELOAD    the patterns playing on the scope, and their tracks' settings, back as they were saved (UNDO takes it back)
 *   LEARN     the next CC that comes in sets the CC number of a lane (or of a CC LFO)
 *   REMOTE    commands as Control Changes on MIDI channel 14: the SAGGA REMOTE plugin of RaspiMIDIHub, or any controller
 *             (the map is in docs/SAGGA-SEQ.md and below, remote_cc)
 *   SNAPSHOTS (0.8) eight memories of the whole live state; their synths' sound (CC values captured from the synths,
 *             patches the Raspberry Pi keeps)
 */

/* ---- QUANTISE */
static void quant_flush(void)                  /* what waits for a quantised moment happens now */
{
    uint32_t t;
    if (pending_scene < SQ_SCENES) { apply_scene(pending_scene); pending_scene = SQ_NO_PENDING; }
    if (pending_mute) { mute_mask ^= pending_mute; pending_mute = 0u; vg_states_sync_all(); }   /* (0.12: VIAGGIO's states follow) */
    if (project.live.quant != SQ_Q_NOW) return;
    for (t = 0; t < SQ_TRACKS; t++)
        if (tr[t].pending_pattern < SQ_PATTERNS) { tr[t].pattern = tr[t].pending_pattern; tr[t].pending_pattern = SQ_NO_PENDING; }
}

static void quant_set(uint8_t q)
{
    char *p = msg_buf;
    if (q >= SQ_QUANTS) q = SQ_Q_AUTO;
    project.live.quant = q;
    if (q == SQ_Q_NOW) quant_flush();
    p = put_s(p, "QUANTISE "); p = put_s(p, QUANT_NAME[q]); finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}

static void mute_q_toggle(void)
{
    project.live.mute_q ^= 1u;
    if (!project.live.mute_q) { mute_mask ^= pending_mute; pending_mute = 0u; vg_states_sync_all(); }
    status_msg(project.live.mute_q ? "MUTES WAIT FOR THE QUANTISE" : "MUTES AT ONCE");
    ui_dirty = grid_dirty = 1u;
}

/* ---- Program Change of a scene, for one channel (-1: none). A new one is sent at once, so you hear it. */
static void scene_pc_set(uint8_t s, uint8_t ch, int32_t pc)
{
    char *p = msg_buf;
    if (s >= SQ_SCENES || ch >= ch_limit()) return;
    if (pc > 127) pc = 127;
    project.scene[s].pc[ch] = pc < 0 ? (uint8_t)SQ_PC_NONE : (uint8_t)pc;
    p = put_s(p, "SCENE "); p = put_u(p, (uint32_t)s + 1u); p = put_s(p, " CH"); p = put_u(p, (uint32_t)ch + 1u);
    if (pc < 0) p = put_s(p, " NO PROGRAM");
    else {
        p = put_s(p, " PROGRAM "); p = put_u(p, (uint32_t)pc + 1u);
        midi_send(0xC0u | ch, (uint32_t)pc, 0u);
        pc_last[ch] = (uint8_t)pc;
    }
    finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}

/* ---- MORPH */
static uint8_t morph_value(uint8_t a, uint8_t b, uint8_t pos)
{
    return (uint8_t)(((int32_t)a * (127 - (int32_t)pos) + (int32_t)b * (int32_t)pos + 63) / 127);
}

static void morph_set(uint8_t pos)
{
    if (pos > 127u) pos = 127u;
    if (pos == morph_pos) return;
    morph_pos = pos;
    morph_dirty = 1u;
    ui_dirty = grid_dirty = 1u;
}

static void morph_target(uint8_t b)
{
    if (b >= SQ_SCENES) return;
    project.live.morph_b = b;
    morph_dirty = 1u;
    status_num("MORPH TO SCENE ", (uint32_t)b + 1u);
    ui_dirty = grid_dirty = 1u;
}

/* every pass: the lanes whose value moved go out (as many as the USB has room for; the rest the next pass). A lane
 * with a lock on the step playing gets its new base value when the lock ends. */
static void morph_service(void)
{
    const sq_scene_t *A = &project.scene[scene_cursor < SQ_SCENES ? scene_cursor : 0u];
    const sq_scene_t *B = &project.scene[project.live.morph_b < SQ_SCENES ? project.live.morph_b : 0u];
    uint32_t t, l;
    if (!morph_dirty) return;
    for (t = 0; t < SQ_TRACKS; t++)
        for (l = 0; l < SQ_LANES; l++) {
            sq_track_cfg_t *c = &project.track[t];
            uint8_t a = A->lane[t][l], b = B->lane[t][l], v;
            if (c->lane_cc[l] == SQ_LANE_NONE || a > 127u || b > 127u) continue;
            v = morph_value(a, b, morph_pos);
            if (c->lane_base[l] == v) continue;
            if (!(ev[t].lane_locked & (1u << l))) {
                if (midi_tx_room() <= 28u) return;
                send_cc(track_ch(t), c->lane_cc[l], lane_val(l, v));
            }
            c->lane_base[l] = v;
        }
    morph_dirty = 0u;
}

/* ---- RELOAD: from the slot the project came from (or went to), or from the image of the last import while it is
 * still in store_img; the tracks of the scope, one per pass */
static uint8_t rl_t;
static uint16_t rl_mask;
static uint32_t rl_pos, rl_crc;
static sq_track_cfg_t rl_cfg;
static sq_step_t rl_row[SQ_STEPS] __attribute__((section(".pool")));

static uint32_t crc_more(uint32_t c, const uint8_t *p, uint32_t n)      /* sq_crc32 in pieces: start with ~0, end with ~ */
{
    uint32_t k;
    while (n--) {
        c ^= *p++;
        for (k = 0; k < 8u; k++) c = c & 1u ? (c >> 1) ^ 0xEDB88320u : c >> 1;
    }
    return c;
}

static void reload_request(void)
{
    if (dice_pending) dice_answer(1u);
    if (tst_booted) { status_msg(TST_SLOTS_OFF); return; }   /* (0.11: the PC test) */
    if (rl_state) return;
    if (rl_src == RL_IMPORT) { rl_mask = gen_mask(); rl_state = 2u; rl_t = 0u; undo_begin(); return; }
    if (rl_src >= SQ_SLOTS || !slot_info[rl_src].ok) { status_msg("NOTHING SAVED TO RELOAD: SAVE FIRST"); return; }
    if (save_state != ST_IDLE || imp_on) { status_msg("SAVING, WAIT"); return; }
    rl_mask = gen_mask();
    rl_len = slot_info[rl_src].len;
    rl_pos = 0u;
    rl_crc = 0xFFFFFFFFu;
    rl_state = 1u;
}

static void reload_track(uint32_t t)
{
    uint8_t pat = tr[t].pattern;
    uint32_t l;
    sq_track_cfg_t *c = &project.track[t];
    sq_track_cfg_t was;
    if (sq_image_track(store_img, rl_len, (uint8_t)t, pat, &rl_cfg, rl_row)) return;
    was = *c;
    undo_add((uint8_t)t, pat);
    memcpy(project.step[t][pat], rl_row, sizeof rl_row);
    *c = rl_cfg;
    track_cfg_back(t, &was);                           /* 0.11: in time (the explorer) */
    for (l = 0; l < SQ_LANES; l++)                     /* the synth's sound back as it was saved */
        if (c->lane_cc[l] != SQ_LANE_NONE && c->lane_base[l] != SQ_LANE_NONE) send_cc(track_ch(t), c->lane_cc[l], lane_val(l, c->lane_base[l]));
}

/* store_service, while no save or import runs */
static void reload_step(void)
{
    if (rl_state == 1u) {
        uint32_t k, step = playing ? SQ_STEP_PLAY : SQ_STEP_IDLE;
        if (save_state != ST_IDLE || imp_on || rl_src >= SQ_SLOTS) { rl_state = 0u; return; }
        k = rl_len - rl_pos < step ? rl_len - rl_pos : step;
        if (st_read(area_off(slot_info[rl_src].area) + SQ_SLOT_HEAD + rl_pos, store_img + rl_pos, k)) {
            rl_state = 0u; status_msg("RELOAD FAILED (FLASH)"); return;
        }
        rl_crc = crc_more(rl_crc, store_img + rl_pos, k);
        rl_pos += k;
        if (rl_pos < rl_len) return;
        if (~rl_crc != slot_info[rl_src].crc) { rl_state = 0u; status_msg("RELOAD FAILED (CRC)"); return; }
        rl_state = 2u;
        rl_t = 0u;
        undo_begin();
        return;
    }
    if (rl_state != 2u) return;
    while (rl_t < SQ_TRACKS && !(rl_mask & (1u << rl_t))) rl_t++;
    if (rl_t < SQ_TRACKS) { reload_track(rl_t); rl_t++; return; }
    rl_state = 0u;
    if (evo_run && (evo_mask & rl_mask)) { evo_run = 0u; status_msg("RELOADED (EVOLVE OFF)"); }
    else if (rl_mask == (uint16_t)(1u << selected_track)) status_msg("RELOADED");
    else { char *p = msg_buf; p = put_s(p, "RELOADED "); p = put_u(p, popcount16(rl_mask)); p = put_s(p, " TRACKS"); finish(p); status_msg(msg_buf); }
    ui_dirty = grid_dirty = 1u;
}

/* ---- MIDI LEARN */
static uint8_t learn_kind;                     /* 0 off, 1 a lane of track learn_t, 2 the LFO learn_l */
static uint8_t learn_t, learn_l;
static uint32_t learn_until;
#define SQ_LEARN_MS 10000u

static void learn_arm(uint8_t kind, uint8_t t, uint8_t l)
{
    char *p = msg_buf;
    if (learn_kind == kind && learn_t == t && learn_l == l) { learn_kind = 0u; status_msg("LEARN OFF"); return; }
    learn_kind = kind; learn_t = t; learn_l = l;
    learn_until = fm1_ms + SQ_LEARN_MS;
    p = put_s(p, kind == 1u ? "LEARN LANE " : "LEARN LFO "); p = put_u(p, (uint32_t)l + 1u);
    p = put_s(p, ": MOVE A KNOB OF THE SYNTH"); finish(p);
    status_msg(msg_buf);
    msg_until = learn_until;
    ui_dirty = grid_dirty = 1u;
}

/* a CC came in (not the grid's, not the remote's): taken if LEARN waits for one */
static uint8_t learn_take_v(uint8_t ch, uint8_t cc, uint8_t v)
{
    char *p = msg_buf;
    (void)ch;
    if (!learn_kind) return 0u;
    if (time_due(fm1_ms, learn_until)) { learn_kind = 0u; return 0u; }
    if (cc > 127u) return 0u;
    if (learn_kind == 1u) {
        sq_track_cfg_t *c = &project.track[learn_t];
        const char *nm;
        c->lane_cc[learn_l] = cc;
        c->lane_flags[learn_l] &= (uint8_t)~SQ_LF_NRPN;
        if (c->lane_base[learn_l] == SQ_LANE_NONE && v <= 127u) c->lane_base[learn_l] = v;   /* 0.10: where the knob is becomes the base */
        env_lane = learn_l;
        p = put_s(p, "T"); p = put_u(p, (uint32_t)learn_t + 1u); p = put_s(p, " LANE "); p = put_u(p, (uint32_t)learn_l + 1u);
        nm = sq_cc_name(project.device[track_ch(learn_t)], cc);
        if (nm[0]) { p = put_s(p, " "); p = put_s(p, nm); }
    } else {
        sq_lfo_t *l = &project.lfo[learn_l];
        l->dest = SQ_LD_CC;
        if (l->target >= ch_limit()) l->target = (uint8_t)(ch_limit() - 1u);
        l->param = cc;
        lfo_last_valid[learn_l] = 0u;
        p = put_s(p, "LFO "); p = put_u(p, (uint32_t)learn_l + 1u);
    }
    p = put_s(p, " = CC "); p = put_u(p, cc); finish(p);
    learn_kind = 0u;
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
    return 1u;
}
static uint8_t learn_take(uint8_t ch, uint8_t cc) { return learn_take_v(ch, cc, 255u); }

static void learn_service(void)
{
    if (learn_kind && time_due(fm1_ms, learn_until)) { learn_kind = 0u; status_msg("LEARN: NOTHING CAME"); }
}

/* ---- SAGGA REMOTE: Control Changes on project.live.remote_ch (MIDI channel 14). Values: a knob 0..127; a button
 * pressed 64..127, let go 0..63.
 *   1 MORPH position   2 MORPH to scene 1-8 (0-7)   3 ENERGY (0.9)   4 EVOLVE amount   5 heat   6 QUANTISE (0-6)
 *   7 INTENSITY   8 GATE   9 SWING   10 FILTER (the macros, 64 = 0)   11 TRANSPOSE (12 = 0: 0..24 = -12..+12)
 *   20 PLAY / STOP   21 CONTINUE   22 RELOAD   23 FILL (held)   24-27 LOOP / REPEAT 1/4 1/8 1/16 1/32 (tap / hold)
 *   28 scene -1   29 scene +1   30 tempo -1   31 tempo +1   32 TAP   33 EVOLVE   34 FREEZE   35 REVERT   36 UNDO
 *   37 TEMP (held)   38 PANIC   39 MUTE QUEUE on / off   40-47 scene 1-8   48-63 mute track 1-16
 *   64-79 kill track 1-16 (held)   80-84 dice SEQ CC LFO GROOVE ALL   85 keep the dice   86 put it back
 *   87 STOP at the end of the bar   88 RESTART   89 EXIT the loop   90-105 RETRIG track 1-16
 *   0.8: 106-113 SNAPSHOT 1-8   114 CC CAPTURE on / off   115 SEND the snapshot's sound   116 PATCHES (the Pi)
 *   117 HARMONY on / off   118 the global ECHO on / off   119 WRITE LIVE   12-19 store SNAPSHOT 1-8
 *   (120-127 are the channel mode messages of MIDI: never commands; a PANIC's CC 123 on every channel must not store) */
static uint8_t remote_temp;

static void remote_cc(uint8_t cc, uint8_t v)
{
    uint8_t on = v >= 64u ? 1u : 0u;
    switch (cc) {
    case 1u: morph_set(v); return;
    case 2u: morph_target(v < SQ_SCENES ? v : (uint8_t)(v / 8u)); return;   /* (0.9: 16 scenes: 0-15, or 0-127 / 8) */
    case 3u: vg_energy_set((uint8_t)(((uint32_t)v * 100u + 63u) / 127u)); return;   /* 0.9: the energy */
    case 4u: project.gen.evo_amount = (uint8_t)(1u + (uint32_t)v * 99u / 127u); ui_dirty = 1u; return;
    case 5u: project.gen.heat = (uint8_t)(1u + (uint32_t)v * 99u / 127u); ui_dirty = 1u; return;
    case 6u: quant_set(v < SQ_QUANTS ? v : (uint8_t)((uint32_t)v * SQ_QUANTS / 128u)); return;
    case 7u: macro_set(0u, (int32_t)v - 64); return;
    case 8u: macro_set(1u, v < 64u ? ((int32_t)v - 64) * 90 / 64 : ((int32_t)v - 64) * 100 / 63); return;
    case 9u: macro_set(2u, ((int32_t)v - 64) * 25 / 63); return;
    case 10u: macro_set(3u, (int32_t)v - 64); return;
    case 11u: ktrans_set((int32_t)v - SQ_KTRANS_MAX); return;
    case 23u: remote_fill = on; ui_dirty = grid_dirty = 1u; return;
    case 24u: case 25u: case 26u: case 27u: {
        static const uint16_t RT[4] = {24u, 12u, 6u, 3u};
        uint8_t src = (uint8_t)(LP_REMOTE + cc - 24u);
        if (on) { if (!(lp_held & (1u << src))) loop_press(RT[cc - 24u], src, 0xFFFFu); }
        else loop_release(src);
        return;
    }
    case 37u:
        if (on && !temp_on) { temp_begin(); remote_temp = 1u; }
        else if (!on && remote_temp) { remote_temp = 0u; temp_end(); }
        return;
    default: break;
    }
    if (cc >= 64u && cc < 80u) {
        uint16_t bit = (uint16_t)(1u << (cc - 64u));
        if (on) { remote_kill |= bit; track_all_off(cc - 64u); } else remote_kill &= (uint16_t)~bit;
        ui_dirty = grid_dirty = 1u;
        return;
    }
    if (!on) return;
    switch (cc) {
    case 20u: if (playing) transport_stop(); else transport_start(); break;
    case 21u: if (!playing) transport_continue(); break;
    case 22u: reload_request(); break;
    case 28u: scene_recall(scene_cursor ? (uint8_t)(scene_cursor - 1u) : 0u); break;
    case 29u: scene_recall(scene_cursor < SQ_SCENES - 1u ? (uint8_t)(scene_cursor + 1u) : (uint8_t)(SQ_SCENES - 1u)); break;
    case 30u: set_bpm(-1); break;
    case 31u: set_bpm(1); break;
    case 32u: tap_tempo(); break;
    case 33u: evo_toggle(); break;
    case 34u: evo_freeze(); break;
    case 35u: evo_revert(); break;
    case 36u: if (dice_pending) dice_answer(0u); else undo_swap(); break;
    case 38u: panic_all_x(1u); status_msg("PANIC"); break;
    case 39u: mute_q_toggle(); break;
    case 85u: dice_answer(1u); break;
    case 86u: dice_answer(0u); break;
    case 87u: stop_bar_toggle(); break;
    case 88u: restart_all(); break;
    case 89u: loop_exit(); break;
    case 114u: snap_capture_toggle(); break;
    case 115u: snap_send(); break;
    case 116u: snap_patches(); break;
    case 117u: harm_toggle(); break;
    case 118u: echo_global ^= 1u; status_msg(echo_global ? "ECHO: EVERY TRACK, A DOTTED EIGHTH" : "ECHO OFF"); break;
    case 119u: live_write(); break;
    default:
        if (cc >= 106u && cc < 114u) snap_recall((uint8_t)(cc - 106u));
        else if (cc >= 12u && cc < 20u) snap_store((uint8_t)(cc - 12u));
        else if (cc >= 90u && cc < 106u) track_retrig((uint8_t)(cc - 90u));
        else if (cc >= 40u && cc < 48u) scene_recall((uint8_t)(cc - 40u));
        else if (cc >= 48u && cc < 64u) toggle_mute((uint8_t)(cc - 48u));
        else if (cc >= 80u && cc < 85u) dice_roll((uint8_t)(DICE_SEQ + cc - 80u));
        break;
    }
    ui_dirty = grid_dirty = 1u;
}

/* ---- 0.8 SNAPSHOTS. SAVE + black 1-8 brings snapshot 1-8 back (at the QUANTISE moment, as a scene), SAVE + SEL + black
 * stores it: the patterns playing, the mutes and solos, the macros, the key and TRANSPOSE, the HARMONY, every track's
 * settings (channel, loop, swing, voicing, MIDI FX, EUCLID, the algorithm, the CC lanes' base values ...), the LFOs, the
 * tempo if SAVE + K3 says so. Its sound goes out with it: the lanes' base values, and the synths' own CC values that
 * CC CAPTURE (SAVE + black 9) took from them while their knobs turned; SEND (black 10) sends it all again. PATCHES
 * (black 11) asks the Raspberry Pi to keep the synths' patches (SysEx) for this snapshot: it sends them back when the
 * snapshot comes back (tools/sagga_grid_bridge.py, docs/SAGGA-SEQ.md). */
static uint8_t snap_tx_t, snap_tx_l, snap_tx_i;   /* sending a snapshot's sound, a few messages a pass */
static void snap_pi(uint8_t cmd, uint8_t n);     /* sagga_store.c: a SysEx to the Pi about snapshot n */

static void snap_status(const char *what, uint8_t n)
{
    char *p = msg_buf;
    p = put_s(p, what); p = put_u(p, (uint32_t)n + 1u); finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}

static void snap_store(uint8_t n)
{
    sq_snap_t *sn = &project.snap[n];
    uint32_t t;
    if (n >= SQ_SNAPS) return;
    if (!sn->used) sn->ccn = 0u;                     /* (a snapshot stored again keeps the synth CC values it took) */
    sn->used = 1u;
    sn->bpm = project.bpm;
    sn->key_root = project.key_root; sn->key_scale = project.key_scale; sn->key_shift = project.key_shift;
    sn->key_cur = project.key_cur;
    sn->ktrans = project.live.ktrans;
    for (t = 0; t < SQ_TRACKS; t++) { sn->pattern[t] = tr[t].pattern; sn->track[t] = project.track[t]; }
    sn->mute = (uint16_t)(vg_mutes_to_keep() ^ pending_mute); sn->solo = solo_mask;   /* (0.9: not a BREAK's silence) */
    sn->mac[0] = mac_vel; sn->mac[1] = mac_gate; sn->mac[2] = mac_swing; sn->mac[3] = mac_filt;
    sn->harm_on = project.gen.harm_on; sn->genre = project.gen.genre;
    sn->harm_prog = project.gen.harm_prog; sn->harm_bars = project.gen.harm_bars;
    sn->harm_genre = project.gen.harm_genre;                                        /* 0.11 */
    sn->morph_b = project.live.morph_b;
    memset(sn->reserved, 0, sizeof sn->reserved);
    memcpy(sn->lfo, project.lfo, sizeof sn->lfo);
    snap_cur = n;
    snap_status("SNAPSHOT STORED ", n);
}

static void snap_send(void)                       /* the snapshot's sound out again (and its patches, from the Pi) */
{
    if (snap_cur >= SQ_SNAPS || !project.snap[snap_cur].used) { status_msg("NO SNAPSHOT: SAVE+SEL+BLACK STORES ONE"); return; }
    snap_tx_on = 1u; snap_tx_t = 0u; snap_tx_l = 0u; snap_tx_i = 0u;
    snap_pi(0x40u, snap_cur);
    snap_status("SNAPSHOT SOUND SENT ", snap_cur);
}

static void snap_apply(uint8_t n)
{
    const sq_snap_t *sn = &project.snap[n];
    uint32_t t;
    if (n >= SQ_SNAPS || !sn->used) return;
    for (t = 0; t < SQ_TRACKS; t++) {
        sq_track_cfg_t *c = &project.track[t];
        uint8_t p = sn->pattern[t] < SQ_PATTERNS ? sn->pattern[t] : 0u, div = c->division, len = c->length, st = c->start;
        *c = sn->track[t];
        sq_mfx_mirror(&project.ext.mfxc[t], c);          /* 0.19: the MIDI FX chain is the track's, not a snapshot's */
        if (c->division != div) tr[t].div_accum = (uint16_t)(tr[t].div_accum % sq_div_ticks(c->division));
        if (playing && p != tr[t].pattern && project.live.quant != SQ_Q_AUTO) track_restart(t);
        if (p != tr[t].pattern) pre[t].state = 0u;         /* (a step decided ahead on the old pattern: forgotten) */
        tr[t].pattern = p;
        tr[t].pending_pattern = SQ_NO_PENDING;
        if (tr[t].step >= c->length || tr[t].step < c->start) tr[t].step = c->start;
        if (c->length != len || c->start != st || c->division != div) track_loaded((uint8_t)t);   /* 0.11: another loop: in time */
    }
    mute_mask = sn->mute; solo_mask = sn->solo; pending_mute = 0u;
    mac_vel = sn->mac[0]; mac_gate = sn->mac[1]; mac_swing = sn->mac[2];
    if (mac_filt != sn->mac[3]) { mac_filt = sn->mac[3]; filt_dirty = 1u; filt_t = 0u; }
    if (sn->key_cur < SQ_KEYS && sn->key_cur != project.key_cur) key_select_slot(sn->key_cur);
    project.key_root = sn->key_root; project.key_scale = sn->key_scale; project.key_shift = sn->key_shift;
    key_sync_slot();
    project.live.ktrans = sn->ktrans; ktrans_pend = SQ_KT_NONE;
    project.gen.harm_on = sn->harm_on; project.gen.genre = sn->genre;
    project.gen.harm_prog = sn->harm_prog; project.gen.harm_bars = sn->harm_bars;
    if (!project.gen.harm_lock) project.gen.harm_genre = sn->harm_genre < SQ_GENRES ? sn->harm_genre : sn->genre;   /* 0.11 (a snapshot is the player's own act: it brings its harmony, unless locked) */
    project.live.morph_b = sn->morph_b;
    memcpy(project.lfo, sn->lfo, sizeof project.lfo);
    memset(lfo_last_valid, 0, sizeof lfo_last_valid);
    if (project.live.snap_tempo && project.clock_mode == SQ_CLOCK_MASTER) { project.bpm = sn->bpm; knob_live = 0u; knob_ref = fm1_knob; }
    snap_cur = n;
    snap_tx_on = 1u; snap_tx_t = 0u; snap_tx_l = 0u; snap_tx_i = 0u;   /* its sound goes out (snap_service) */
    snap_pi(0x40u, n);                              /* the Pi sends the patches it keeps for it */
    snap_status("SNAPSHOT ", n);
}

static void snap_recall(uint8_t n)
{
    if (n >= SQ_SNAPS) return;
    if (!project.snap[n].used) { snap_status("EMPTY: SAVE+SEL+BLACK STORES SNAPSHOT ", n); return; }
    if (playing && project.live.quant != SQ_Q_NOW) {
        snap_pend = snap_pend == n ? (uint8_t)255u : n;   /* (the same again before its moment: taken back) */
        if (snap_pend == n) snap_status("SNAPSHOT QUEUED ", n); else status_msg("SNAPSHOT CANCELLED");
        ui_dirty = grid_dirty = 1u;
        return;
    }
    snap_apply(n);
}

static void snap_capture_toggle(void)
{
    if (!snap_capture && (snap_cur >= SQ_SNAPS || !project.snap[snap_cur].used)) { status_msg("STORE A SNAPSHOT FIRST (SAVE+SEL+BLACK)"); return; }
    snap_capture ^= 1u;
    if (snap_capture) snap_status("CC CAPTURE ON: TURN THE SYNTHS' KNOBS. SNAPSHOT ", snap_cur);
    else status_msg("CC CAPTURE OFF");
    ui_dirty = grid_dirty = 1u;
}

/* a CC from a synth while CC CAPTURE is on: its value goes into the snapshot (the lanes on that CC take it as base) */
static uint8_t snap_cc_in(uint8_t ch, uint8_t cc, uint8_t v)
{
    sq_snap_t *sn;
    uint32_t i, t, l;
    if (!snap_capture || snap_cur >= SQ_SNAPS) return 0u;
    if (cc >= 120u || cc == 6u || cc == 38u || (cc >= 96u && cc <= 101u)) return 0u;   /* (modes, RPN / NRPN: not values) */
    sn = &project.snap[snap_cur];
    for (i = 0; i < sn->ccn; i++) if (sn->cc[i].ch == ch && sn->cc[i].cc == cc) break;
    if (i >= sn->ccn) {
        if (sn->ccn >= SQ_SNAP_CC) { status_msg("SNAPSHOT CC FULL (48)"); return 1u; }
        sn->cc[i].ch = ch; sn->cc[i].cc = cc;
        sn->ccn++;
    }
    sn->cc[i].val = v;
    for (t = 0; t < SQ_TRACKS; t++) {
        sq_track_cfg_t *c = &project.track[t];
        if (track_ch(t) != ch) continue;
        for (l = 0; l < SQ_LANES; l++) if (c->lane_cc[l] == cc) { c->lane_base[l] = v; sn->track[t].lane_base[l] = v; }
    }
    {
        char *p = msg_buf;
        p = put_s(p, "CAPTURED CH"); p = put_u(p, (uint32_t)ch + 1u); p = put_s(p, " CC"); p = put_u(p, cc);
        p = put_s(p, " = "); p = put_u(p, v); finish(p);
        status_msg(msg_buf);
    }
    return 1u;
}

static void snap_patches(void)
{
    if (snap_cur >= SQ_SNAPS || !project.snap[snap_cur].used) { status_msg("STORE A SNAPSHOT FIRST (SAVE+SEL+BLACK)"); return; }
    snap_pi(0x41u, snap_cur);
    snap_status("PI: KEEPING THE SYNTHS' PATCHES FOR SNAPSHOT ", snap_cur);
    msg_until = fm1_ms + 4000u;
}

/* a lane of a track on channel ch sends cc with its base value (then the captured value is not sent twice) */
static uint8_t snap_lane_sends(uint8_t ch, uint8_t cc)
{
    uint32_t t, l;
    for (t = 0; t < SQ_TRACKS; t++) {
        const sq_track_cfg_t *c = &project.track[t];
        if (track_ch(t) != ch) continue;
        for (l = 0; l < SQ_LANES; l++)
            if (c->lane_cc[l] == cc && c->lane_base[l] != SQ_LANE_NONE && !(ev[t].lane_locked & (1u << l))) return 1u;
    }
    return 0u;
}

/* every pass: the snapshot's sound, as the USB has room: the lanes' base values, then the captured CC values */
static void snap_service(void)
{
    const sq_snap_t *sn;
    if (!snap_tx_on) return;
    if (snap_cur >= SQ_SNAPS) { snap_tx_on = 0u; return; }
    sn = &project.snap[snap_cur];
    while (snap_tx_t < SQ_TRACKS) {
        const sq_track_cfg_t *c = &project.track[snap_tx_t];
        while (snap_tx_l < SQ_LANES) {
            uint8_t l = snap_tx_l;
            if (c->lane_cc[l] != SQ_LANE_NONE && c->lane_base[l] != SQ_LANE_NONE && !(ev[snap_tx_t].lane_locked & (1u << l))) {
                if (midi_tx_room() <= 28u) return;
                send_cc(track_ch(snap_tx_t), c->lane_cc[l], lane_val(l, c->lane_base[l]));
            }
            snap_tx_l++;
        }
        snap_tx_l = 0u;
        snap_tx_t++;
    }
    while (snap_tx_i < sn->ccn && snap_tx_i < SQ_SNAP_CC) {
        const sq_ccv_t *v = &sn->cc[snap_tx_i];
        if (!snap_lane_sends(v->ch, v->cc)) {
            if (midi_tx_room() <= 28u) return;
            send_cc(v->ch, v->cc, v->val);
        }
        snap_tx_i++;
    }
    snap_tx_on = 0u;
}

/* every pass of the main loop */
static void live_service(void)
{
    morph_service();
    filt_service();
    learn_service();
    snap_service();
}
