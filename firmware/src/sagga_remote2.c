/* SPDX-License-Identifier: GPL-3.0-only */
/*
 * SAGGA 0.12 - the remote's second channel: what the Pi's new pages (SAGGA Motori, Break, Mod) send on MIDI channel 13,
 * beside VIAGGIO's CC 1-32 (sagga_viaggio.c: vg_remote_cc hands CC 33 and up here). Included by dinghy.c after
 * sagga_viaggio.c. The channel is VIAGGIO's remote channel (SAVE K2: REMOTE 13 + 14).
 *
 *   notes 36-51    on a BREAK track the slices 1-16 (a drum rack from C1); on any other track the note itself, played on
 *                  the selected track as the keys play it (ARP held): REC writes it, TAKE remembers it
 *   notes 100-115  LFO 1-16 on (note on) / off (note off): the sixteen switches of SAGGA Mod, all at once
 *   CC 33-48       track 1-16: the pattern (0-7, or 0-127 / 16), at the QUANTISE moment     49-64  track 1-16: LENGTH 1-64
 *   CC 65 ROLL (held), 66 HALF, 67 DOUBLE, 68 BACKWARDS, 69 DICE, 70 RESET, 71 ROLL 1/32 (held): the selected BREAK track
 *   CC 72 CHOP (0-15, or 0-127 / 8), 73 SWAP (0-7 over 0-127), 74 ROLLS (0-7), 75 SLICES (8 / 16 / 32)
 *   CC 76-91       the 16 slices as pads (the value is the velocity; 0 = off): what the notes do, for pages that send CCs only
 *   CC 92 which LFO (0-127 / 8)   93 SHAPE, 94 RATE, 95 DEPTH, 96 DEST, 97 ON / OFF of that LFO
 *   CC 101-106     lane 1-6 of the selected track: the base value, sent at once
 *   CC 107 TAKE    108-111 THROWS: INTENSITY, GATE, SWING, FILTER thrown (they glide back to 0 over a bar)
 *   CC 112 SELECT TRACK (0-127 / 8)    113 MODE (FREE IN KEY DRUM TAPE BREAK)
 *   CC 114 ENERGY  115 GENRE (0-23)    116 KEY (the root, 0-127 / 11)    117 PROGRESSION    118 HARMONY (OFF ON LOCK)
 */

static void remote13_note(uint8_t d1, uint8_t d2, uint8_t on)
{
    uint8_t t = selected_track, note, ch, out;
    d1 &= 127u;
    if (d1 >= 100u && d1 < 116u) {                                    /* 0.12: LFO 1-16 on / off */
        uint8_t n = (uint8_t)(d1 - 100u);
        if (project.lfo[n].enabled != on) { project.lfo[n].enabled = on; lfo_last_valid[n] = 0u; }
        status_msg(on ? "LFO ON" : "LFO OFF");
        ui_dirty = grid_dirty = 1u;
        return;
    }
    if (!on) {                                                        /* the off follows the on it matches */
        if (ext_ch[d1] != 255u) { midi_send(0x80u | ext_ch[d1], ext_out[d1], 0u); ext_ch[d1] = 255u; }
        rec_close_note(d1); tape_rec_off(d1); take_note_off(d1);
        return;
    }
    if (track_break(t)) note = (uint8_t)clamp_i32((int32_t)PEN(t) + (int32_t)((d1 >= 36u ? d1 - 36u : d1) % brk_slices(t)), 0, 127);
    else note = d1;
    ch = track_ch(t); out = key_note(t, note);
    if (ext_ch[d1] != 255u) midi_send(0x80u | ext_ch[d1], ext_out[d1], 0u);
    midi_send(0x90u | ch, out, d2);
    ext_ch[d1] = ch; ext_out[d1] = out;
    if (track_break(t)) brk_live_played(ch, out, d2);
    take_note_on(d1, t, note, d2);
    if (record_arm) {
        if (track_tape(t)) tape_rec_on(d1, t, note, d2);
        else { int stp = record_note(t, key_store(t, note), d2); if (stp >= 0) rec_open_note(d1, t, (uint8_t)stp); }
    }
}

static void remote13_cc(uint8_t cc, uint8_t v)
{
    uint8_t on = v >= 64u ? 1u : 0u, t = selected_track;
    sq_track_cfg_t *cfg = &project.track[t];
    if (cc >= 33u && cc < 49u) { queue_pattern((uint8_t)(cc - 33u), v < SQ_PATTERNS ? v : (uint8_t)(v >> 4)); return; }
    if (cc >= 49u && cc < 65u) { set_length((uint8_t)(cc - 49u), (uint8_t)clamp_i32(v, 1, 64)); return; }
    if (cc >= 76u && cc < 92u) { remote13_note((uint8_t)(36u + cc - 76u), v, v ? 1u : 0u); return; }   /* the pads as CCs */
    if (cc >= 101u && cc < 107u) {
        uint32_t n = cc - 101u;
        cfg->lane_base[n] = v;
        lane_send(t, n, lane_val((uint8_t)n, v));
        ui_dirty = grid_dirty = 1u;
        return;
    }
    switch (cc) {
    case 65u: if (!on) brk_black_up(0); else if (track_break(t)) brk_black(t, 0); return;   /* (the off counts whatever track is selected now) */
    case 71u: if (!on) brk_black_up(1); else if (track_break(t)) brk_black(t, 1); return;
    case 72u: if (track_break(t)) brk_chop_apply(t, (uint8_t)(v < SQ_BRK_CHOPS ? v : v / 8u)); else status_msg("CHOP: HOME 4 K1 MAKES THE TRACK A BREAK"); return;   /* (0-15, or 0-127 / 8) */
    case 73u: cfg->brk_cfg = SQ_BRK_PACK(SQ_BRK_SL(cfg->brk_cfg), SQ_BRK_ROLL(cfg->brk_cfg), v < 8u ? v : (uint32_t)v * 8u / 128u); status_num("DICE SWAPS % ", (uint32_t)SQ_BRK_SWAP(cfg->brk_cfg) * 100u / 7u); return;
    case 74u: cfg->brk_cfg = SQ_BRK_PACK(SQ_BRK_SL(cfg->brk_cfg), v < 8u ? v : (uint32_t)v * 8u / 128u, SQ_BRK_SWAP(cfg->brk_cfg)); status_num("DICE ROLLS ", SQ_BRK_ROLL(cfg->brk_cfg)); return;
    case 75u: cfg->brk_cfg = SQ_BRK_PACK(v < 3u ? v : v < 43u ? 0u : v < 86u ? 1u : 2u, SQ_BRK_ROLL(cfg->brk_cfg), SQ_BRK_SWAP(cfg->brk_cfg)); status_num("BREAK SLICES ", SQ_BRK_SLICES(SQ_BRK_SL(cfg->brk_cfg))); return;
    case 92u: lfo_sel = (uint8_t)(v < SQ_LFOS ? v : v / 8u); ui_dirty = 1u; return;
    case 93u: project.lfo[lfo_sel].shape = (uint8_t)(v < SQ_LFO_SHAPES ? v : (uint32_t)v * SQ_LFO_SHAPES / 128u); lfo_last_valid[lfo_sel] = 0u; ui_dirty = 1u; return;
    case 94u: project.lfo[lfo_sel].rate = (uint8_t)(v < SQ_LFO_RATES ? v : (uint32_t)v * SQ_LFO_RATES / 128u); lfo_last_valid[lfo_sel] = 0u; ui_dirty = 1u; return;
    case 95u: project.lfo[lfo_sel].depth = v; lfo_last_valid[lfo_sel] = 0u; ui_dirty = 1u; return;
    case 96u: {
        sq_lfo_t *l = &project.lfo[lfo_sel];
        l->dest = (uint8_t)(v < SQ_LD_KINDS ? v : (uint32_t)v * SQ_LD_KINDS / 128u);
        if (l->dest == SQ_LD_CC && l->target >= ch_limit()) l->target = (uint8_t)(ch_limit() - 1u);
        lfo_last_valid[lfo_sel] = 0u; ui_dirty = 1u;
        return;
    }
    case 97u: project.lfo[lfo_sel].enabled = on; lfo_last_valid[lfo_sel] = 0u; ui_dirty = grid_dirty = 1u; return;
    case 108u: macro_set(0u, (int32_t)v - 64); throw_mark(0u, 1u); return;
    case 109u: macro_set(1u, v < 64u ? ((int32_t)v - 64) * 90 / 64 : ((int32_t)v - 64) * 100 / 63); throw_mark(1u, 1u); return;
    case 110u: macro_set(2u, ((int32_t)v - 64) * 25 / 63); throw_mark(2u, 1u); return;
    case 111u: macro_set(3u, (int32_t)v - 64); throw_mark(3u, 1u); return;
    case 112u: select_track((uint8_t)(v < SQ_TRACKS ? v : v / 8u)); return;
    case 113u: set_track_mode(t, (uint8_t)(v < TRACK_MODES ? v : (uint32_t)v * TRACK_MODES / 128u)); status_msg(track_mode_name(t)); ui_dirty = grid_dirty = 1u; return;
    case 114u: vg_energy_set((uint8_t)(((uint32_t)v * 100u + 63u) / 127u)); return;
    case 115u: { int32_t want = v < SQ_SET_GENRES ? v : (int32_t)((uint32_t)v * SQ_SET_GENRES / 128u); int32_t d = want - vg_genre_shown(); if (d) vg_genre_turn(d); return; }
    case 116u: { int32_t want = v < 12u ? v : (int32_t)((uint32_t)v * 12u / 128u); int32_t d = want - vg_key_shown(); if (d) vg_key_turn(d); return; }
    case 117u: piprog_leave(); harm_prog_set((uint8_t)(v < SQ_PROGS_ALL ? v : (uint32_t)v * SQ_PROGS_ALL / 128u)); ui_dirty = 1u; return;
    case 118u: harm_state_set((uint8_t)(v < 3u ? v : (uint32_t)v * 3u / 128u)); ui_dirty = 1u; return;
    default: break;
    }
    if (!on) return;
    switch (cc) {
    case 66u: if (track_break(t)) brk_transform(t, 0u); break;
    case 67u: if (track_break(t)) brk_transform(t, 1u); break;
    case 68u: if (track_break(t)) brk_transform(t, 2u); break;
    case 69u: dice_roll(DICE_SEQ); break;
    case 70u: if (track_break(t)) brk_chop_apply(t, 0u); break;
    case 107u: take_apply(t); break;
    default: break;
    }
    ui_dirty = grid_dirty = 1u;
}
