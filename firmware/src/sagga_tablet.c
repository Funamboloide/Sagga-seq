/* SPDX-License-Identifier: GPL-3.0-only */
/*
 * SAGGA 0.18 - the tablet: the hub's LIVE page (MIDI channel 12) and what goes back to the hub's pages. Included by
 * dinghy.c after sagga_remote2.c. The tablet has its own track, LFO and cursor (dinghy.c: tab_enter / tab_leave):
 * what it sends acts there, the panel's track and page stay as they are. The channel is the remote's (SAVE K2:
 * REMOTE 13 + 14; with two USB ports on port 2).
 *
 *   channel 12, the tablet's track (a switch: 64 and up on; a tap: acts at 64 and up)
 *   CC 1 MUTE   2 SOLO   3 PATTERN 0-7 (at the QUANTISE)   4 LENGTH 1-64 (at the bar)   5 OCTAVE 0-6 (3 = 0)
 *   CC 6 SWING 50-75   7 GROOVE 0-9   8 GROOVE AMOUNT 0-100
 *   CC 9 MIDI FX 0-4 (READY)   10 ITS AMOUNT 0-24 (12 = 0)   11 FX GO (the READY one starts; none: the one playing stops)
 *   CC 12 ALGO 0-4 (READY on the slot shown)   13 / 14 / 15 its A / B / C (0-127 over the algorithm's range)   16 ALGO GO
 *   CC 17 EUCLID PULSES 1-64   18 ROTATION 0-63   19 EUCLID LIVE (a switch, this track only)
 *   CC 20 ARP 0-12   21 OCTAVES 1-3   22 RATE 0-6 (1/4 1/2 ROLL 1 2 3 4)   23 RUN 0-3 (OFF RETRIG HOLD HOLD+RT)
 *   CC 24 CHORD 0-31   25 FOLLOW (a switch)
 *   CC 26 COOK   27 BEAT   28 PROPOSAL   29 THE PROPOSAL QUEUED   30 RETRIG   31 DICE   32 UNDO   (taps; this track only)
 *   CC 40-55 MUTE of track 1-16 (switches)
 *
 *   back to the hub (two USB ports, on port 2, once the tablet has said something): what the hub's pages show, as it
 *   changes, and slowly all of it again: channel 12 above; channel 13 CC 33-64 (the patterns and lengths), 92-97 (the
 *   tablet's LFO), 101-106 (its track's lanes), 112-118; notes 100-115 (the LFO switches); channel 14 CC 1, 2, 4-11.
 *   The hub's pages take a CC that comes in on a cell's channel and number as the cell's value, and send nothing
 *   back (RaspiMIDIHub's ControllerBase: bidirectional sync). A value the tablet is moving waits until the hand is off it.
 */

#define TB_CH 11u                                       /* MIDI channel 12 (0-based) */
#define FB_HANDS_MS 400u                                /* a value the tablet moved: nothing goes back to it for so long */

static uint8_t tab_live_ch(uint8_t ch) { return (project.live.remote_mode == SQ_RM_13_14 && ch == TB_CH) ? 1u : 0u; }

/* ---- the algorithms' A, B, C as 0-127 */
static uint8_t algo_range(uint8_t a, uint8_t k, int32_t *lo, int32_t *hi)
{
    static const uint8_t R[SQ_ALGOS][3][2] = {
        {{0, 0}, {0, 0}, {0, 0}},
        {{0, 100}, {2, 16}, {0, SQ_TM_MODES - 1u}},                  /* TURING: mutation %, length, moves */
        {{0, 255}, {4, 64}, {0, 3}},                                 /* CELL: rule, cells, a new row every */
        {{0, 4}, {0, 63}, {0, 15}},                                  /* ACCENT: which, amount, start */
        {{0, 200}, {10, 100}, {0, 0}},                               /* DENSITY: density %, ghost velocity % */
    };
    if (a >= SQ_ALGOS || k > 2u || R[a][k][0] == R[a][k][1]) return 0u;
    *lo = R[a][k][0]; *hi = R[a][k][1];
    return 1u;
}
static uint8_t algo_field(const sq_algo_t *s, uint8_t k) { return k == 0u ? s->a : k == 1u ? s->b : s->c; }
static uint8_t algo_to_cc(const sq_algo_t *s, uint8_t k)
{
    int32_t lo, hi;
    if (!algo_range(s->algo, k, &lo, &hi)) return 255u;
    return (uint8_t)clamp_i32((((int32_t)algo_field(s, k) - lo) * 127 + (hi - lo) / 2) / (hi - lo), 0, 127);
}
static void tab_algo_abc(uint8_t t, uint8_t k, uint8_t v)
{
    static const char *const N[SQ_ALGOS][3] = {{"", "", ""}, {"MUTATION ", "LENGTH ", "MOVES "}, {"RULE ", "CELLS ", "NEW ROW "},
                                               {"ACCENT ", "AMOUNT ", "START "}, {"DENSITY ", "GHOST VEL ", ""}};
    sq_algo_t *s = algo_edit(t);
    int32_t lo, hi, x;
    char *p = msg_buf;
    if (!algo_range(s->algo, k, &lo, &hi)) { status_msg(s->algo ? "THIS ALGORITHM HAS NO C" : "ALGORITHM OFF: ALGO CHOOSES ONE"); return; }
    x = lo + ((int32_t)v * (hi - lo) + 63) / 127;
    if (k == 0u) s->a = (uint8_t)x; else if (k == 1u) s->b = (uint8_t)x;
    else { s->c = (uint8_t)x; if (s->algo == SQ_ALGO_CELL && s == algo_slot(t)) ca_bars[t][algo_k(t)] = 0u; }
    p = put_s(p, ALGO_NAME[s->algo]); p = put_s(p, " "); p = put_s(p, N[s->algo][k]); p = put_u(p, (uint32_t)x); finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}

/* the MIDI FX amount shown on track t (0.19: of the effect its MIDI FX knob shows, playing or READY), without touching mfx_tmp */
static int8_t tab_mfx_amt(uint32_t t)
{
    uint8_t fx = mfx_shown(t), tm, fb;
    int8_t a = 0;
    if (fx) sq_mfx_get(&project.ext, t, fx, &a, &tm, &fb);
    return a;
}
/* 0.20: the FX AMOUNT knob (0..24): the four of 0.19 as -12..+12, as before; the new ones over their whole range */
static int32_t tab_amt_from(uint32_t t, uint8_t fx, uint8_t v)
{
    int32_t lo, hi;
    sq_mfx_range(fx, 0u, track_in_key(t), &lo, &hi);
    if (fx < SQ_MFXS_019) return clamp_i32((int32_t)v - 12, lo, hi);
    return lo + ((int32_t)(v > 24u ? 24u : v) * (hi - lo) + 12) / 24;
}
static int32_t tab_amt_to(uint32_t t, uint8_t fx, int8_t a)
{
    int32_t lo, hi;
    sq_mfx_range(fx, 0u, track_in_key(t), &lo, &hi);
    if (fx < SQ_MFXS_019 || hi <= lo) return (int32_t)a + 12;
    return (((int32_t)a - lo) * 24 + (hi - lo) / 2) / (hi - lo);
}

static uint16_t tab_mutes(void) { return (uint16_t)(vg_mutes_to_keep() ^ pending_mute); }   /* the mutes as meant */
static void tab_mute(uint8_t t, uint8_t on)
{
    char *p = msg_buf;
    if (((tab_mutes() >> t) & 1u) != on) toggle_mute(t);
    p = put_s(p, "T"); p = put_u(p, (uint32_t)t + 1u);
    p = put_s(p, ((pending_mute >> t) & 1u) ? (on ? " MUTES AT THE QUANTISE" : " BACK AT THE QUANTISE") : on ? " MUTED" : " ON");
    finish(p);
    status_msg(msg_buf);
}
static uint8_t arp_run_of(const sq_track_cfg_t *c) { return (uint8_t)(((c->arp_flags & SQ_AF_HOLD) ? 2u : 0u) | ((c->arp_flags & SQ_AF_RETRIG) ? 1u : 0u)); }

/* a tool, the dice: on the tablet's track only (whatever the SCOPE), now (whatever WHEN says) */
static void tab_tool(uint8_t tool)
{
    uint8_t sc = project.gen.scope;
    project.gen.scope = SQ_SCOPE_THIS;
    if (tool == TOOL_COUNT) dice_roll(DICE_SEQ); else tool_apply_x(tool, 0u);
    project.gen.scope = sc;
    ui_dirty = grid_dirty = 1u;
}

/* ---- channel 12: runs inside tab_enter / tab_leave (selected_track is the tablet's) */
static void live12_cc(uint8_t cc, uint8_t v)
{
    uint8_t t = selected_track, on = v >= 64u ? 1u : 0u;
    sq_track_cfg_t *c = &project.track[t];
    char *p = msg_buf;
    if (cc >= 40u && cc < 56u) { tab_mute((uint8_t)(cc - 40u), on); return; }
    switch (cc) {
    case 1u: tab_mute(t, on); return;
    case 2u:
        if (((solo_mask >> t) & 1u) != on) toggle_solo(t);
        status_msg(on ? "SOLO" : "SOLO OFF");
        return;
    case 3u:
        if (v >= SQ_PATTERNS) return;
        queue_pattern(t, v);
        p = put_s(p, "PATTERN "); p = put_u(p, (uint32_t)v + 1u);
        p = put_s(p, tr[t].pending_pattern < SQ_PATTERNS ? " AT THE QUANTISE" : ""); finish(p);
        status_msg(msg_buf);
        return;
    case 4u: set_length(t, (uint8_t)clamp_i32(v, 1, 64)); return;
    case 5u: track_octave(t, clamp_i32((int32_t)v - 3, -3, 3) - c->octave); return;
    case 6u: c->swing = (uint8_t)clamp_i32(v, SQ_SWING_MIN, SQ_SWING_MAX); status_num("SWING ", c->swing); ui_dirty = grid_dirty = 1u; return;
    case 7u: groove_set(t, v < SQ_GROOVES ? v : (uint8_t)SQ_GROOVE_OFF); ui_dirty = grid_dirty = 1u; return;
    case 8u: groove_amount(t, v); ui_dirty = grid_dirty = 1u; return;
    case 9u: mfx_choose(t, v < SQ_MFXS ? v : (uint8_t)SQ_MFX_OFF); return;
    case 10u: {
        sq_track_cfg_t *m = mfx_view(t);
        if (m->mfx) m->mfx_amt = (int8_t)tab_amt_from(t, m->mfx, v);
        if (m == &mfx_tmp) mfx_keep(t, m);
        p = put_s(p, "FX AMOUNT "); p = put_i(p, m->mfx_amt); finish(p);
        status_msg(msg_buf);
        ui_dirty = grid_dirty = 1u;
        return;
    }
    case 12u: algo_choose(t, v < SQ_ALGOS ? v : (uint8_t)SQ_ALGO_OFF); return;
    case 13u: case 14u: case 15u: tab_algo_abc(t, (uint8_t)(cc - 13u), v); return;
    case 17u: c->euc_pulses = (uint8_t)clamp_i32(v, 1, c->length - c->start); euclid_touch(t); return;
    case 18u: c->euc_rot = (uint8_t)clamp_i32(v, 0, c->length - c->start - 1); euclid_touch(t); return;
    case 19u:
        if (on) c->flags |= SQ_TF_EUC; else c->flags &= (uint8_t)~SQ_TF_EUC;
        euclid_status(t);
        ui_dirty = grid_dirty = 1u;
        return;
    case 20u: {
        uint8_t m = v < SQ_CHORD_COUNT ? v : (uint8_t)SQ_CHORD_BLOCK;
        if (m != SQ_CHORD_BLOCK) arp_last[t] = m;
        chord_set(m, SQ_CHORD_OCTS(c->chord_mode));
        ui_dirty = grid_dirty = 1u;
        return;
    }
    case 21u: chord_set(SQ_CHORD_MODE(c->chord_mode), (uint8_t)clamp_i32(v, 1, 3)); ui_dirty = grid_dirty = 1u; return;
    case 22u:
        c->arp_rate = arp_rate_at(v <= SQ_ARP_RATE_MAX ? v : (uint8_t)SQ_ARP_RATE_MAX);
        p = put_s(p, "ARP RATE "); p = put_s(p, arp_rate_name(c->arp_rate)); finish(p);
        status_msg(msg_buf);
        ui_dirty = grid_dirty = 1u;
        return;
    case 23u: {
        static const char *const RN[4] = {"ARP RUN OFF", "ARP RETRIG", "ARP HOLD", "ARP HOLD + RETRIG"};
        uint8_t r = v < 4u ? v : 3u;
        c->arp_flags = (uint8_t)((c->arp_flags & ~(SQ_AF_HOLD | SQ_AF_RETRIG)) | ((r & 2u) ? SQ_AF_HOLD : 0u) | ((r & 1u) ? SQ_AF_RETRIG : 0u));
        status_msg(RN[r]);
        ui_dirty = grid_dirty = 1u;
        return;
    }
    case 24u:
        c->chord = v < SQ_CH_COUNT ? v : (uint8_t)SQ_CH_OFF;
        p = put_s(p, "CHORD "); p = put_s(p, sq_chord_shape_name(c->chord)); finish(p);
        status_msg(msg_buf);
        ui_dirty = grid_dirty = 1u;
        return;
    case 25u: follow_set(t, on); return;
    default: break;
    }
    if (!on) return;                                    /* the taps: at the press */
    switch (cc) {
    case 11u:
        if (mfx_shown(t) == SQ_MFX_OFF && !mfx_count(t)) status_msg("NOTHING READY: MIDI FX CHOOSES ONE");
        else mfx_go(t);                                 /* 0.19: the effect shown joins the chain, or leaves it; OFF: all stop */
        break;
    case 16u: algo_go(t); break;
    case 26u: tab_tool(TOOL_COOK); break;
    case 27u: tab_tool(TOOL_BEAT); break;
    case 28u: beat_propose(); break;
    case 29u: if (!vg_prop_queue(t)) status_msg("NO PROPOSAL TO QUEUE: PROPOSAL MAKES ONE"); break;
    case 30u: track_retrig(t); break;
    case 31u: tab_tool(TOOL_COUNT); break;
    case 32u: tab_tool(TOOL_UNDO); break;
    default: break;
    }
}

/* ---- back to the hub. The items: four rows of sixteen (the patterns, the lengths, the mutes, the LFO switches), then one by one */
enum { FB_PAT = 0, FB_LEN = 16, FB_MUTE = 32, FB_LSW = 48, FB_ONE = 64 };
#define FBF_SCALED 1u                                   /* 0-127 over another range: the hub keeps the value it sent */
typedef struct { uint8_t ch, num, flags; } fb_one_t;
static const fb_one_t FB_ONES[] = {
    {TB_CH, 1, 0}, {TB_CH, 2, 0}, {TB_CH, 3, 0}, {TB_CH, 4, 0}, {TB_CH, 5, 0}, {TB_CH, 6, 0}, {TB_CH, 7, 0}, {TB_CH, 8, 0},
    {TB_CH, 9, 0}, {TB_CH, 10, 0}, {TB_CH, 12, 0}, {TB_CH, 13, FBF_SCALED}, {TB_CH, 14, FBF_SCALED}, {TB_CH, 15, FBF_SCALED},
    {TB_CH, 17, 0}, {TB_CH, 18, 0}, {TB_CH, 19, 0}, {TB_CH, 20, 0}, {TB_CH, 21, 0}, {TB_CH, 22, 0}, {TB_CH, 23, 0},
    {TB_CH, 24, 0}, {TB_CH, 25, 0},
    {12, 92, 0}, {12, 93, 0}, {12, 94, 0}, {12, 95, 0}, {12, 96, 0}, {12, 97, 0},
    {12, 101, 0}, {12, 102, 0}, {12, 103, 0}, {12, 104, 0}, {12, 105, 0}, {12, 106, 0},
    {12, 112, 0}, {12, 113, 0}, {12, 114, FBF_SCALED}, {12, 115, 0}, {12, 116, 0}, {12, 117, 0}, {12, 118, 0},
    {13, 1, 0}, {13, 2, 0}, {13, 4, FBF_SCALED}, {13, 5, FBF_SCALED}, {13, 6, 0}, {13, 7, 0}, {13, 8, FBF_SCALED},
    {13, 9, FBF_SCALED}, {13, 10, 0}, {13, 11, 0},
};
#define FB_N (FB_ONE + (uint32_t)(sizeof FB_ONES / sizeof FB_ONES[0]))
static uint8_t tab_seen;                                /* the tablet has said something since the FM-1 started */
static uint8_t fb_last[FB_N];                           /* what the hub shows, as far as the FM-1 knows (255: not known) */
static uint16_t fb_touch[FB_N];                         /* when the tablet last moved it (ms, 16 bits) */
static uint8_t fb_pos, fb_ref;
static uint32_t fb_next_ms, fb_ref_ms;

static void fb_item(uint32_t k, uint8_t *ch, uint8_t *num, uint8_t *note, uint8_t *flags)
{
    *note = 0u; *flags = 0u;
    if (k < FB_LEN) { *ch = 12u; *num = (uint8_t)(33u + k); }
    else if (k < FB_MUTE) { *ch = 12u; *num = (uint8_t)(49u + k - FB_LEN); }
    else if (k < FB_LSW) { *ch = TB_CH; *num = (uint8_t)(40u + k - FB_MUTE); }
    else if (k < FB_ONE) { *ch = 12u; *num = (uint8_t)(100u + k - FB_LSW); *note = 1u; }
    else { const fb_one_t *o = &FB_ONES[k - FB_ONE]; *ch = o->ch; *num = o->num; *flags = o->flags; }
}
static uint8_t u7(int32_t v) { return (uint8_t)clamp_i32(v, 0, 127); }
/* what item k's cell should show now (255: nothing to show) */
static uint8_t fb_value(uint32_t k)
{
    uint8_t ch, num, note, fl, tt = foc_tab.track < SQ_TRACKS ? foc_tab.track : 0u, ls = foc_tab.lfo < SQ_LFOS ? foc_tab.lfo : 0u;
    const sq_track_cfg_t *c = &project.track[tt];
    const sq_lfo_t *l = &project.lfo[ls];
    fb_item(k, &ch, &num, &note, &fl);
    if (ch != 13u && project.live.remote_mode != SQ_RM_13_14) return 255u;   /* (channels 12 and 13: REMOTE 13 + 14) */
    if (k < FB_LEN) return tr[k].pending_pattern < SQ_PATTERNS ? tr[k].pending_pattern : tr[k].pattern;
    if (k < FB_MUTE) return len_shown((uint8_t)(k - FB_LEN));
    if (k < FB_LSW) return ((tab_mutes() >> (k - FB_MUTE)) & 1u) ? 127u : 0u;
    if (k < FB_ONE) return project.lfo[k - FB_LSW].enabled ? 127u : 0u;
    if (ch == TB_CH) {
        switch (num) {
        case 1: return ((tab_mutes() >> tt) & 1u) ? 127u : 0u;
        case 2: return ((solo_mask >> tt) & 1u) ? 127u : 0u;
        case 3: return tr[tt].pending_pattern < SQ_PATTERNS ? tr[tt].pending_pattern : tr[tt].pattern;
        case 4: return len_shown(tt);
        case 5: return u7((int32_t)c->octave + 3);
        case 6: return c->swing;
        case 7: return project.ext.track[tt].groove;
        case 8: return project.ext.track[tt].groove_amt;
        case 9: return mfx_shown(tt);
        case 10: return u7(tab_amt_to(tt, mfx_shown(tt), tab_mfx_amt(tt)));
        case 12: return algo_shown(tt);
        case 13: case 14: case 15: return algo_to_cc(algo_edit(tt), (uint8_t)(num - 13u));
        case 17: return c->euc_pulses;
        case 18: return c->euc_rot;
        case 19: return (c->flags & SQ_TF_EUC) ? 127u : 0u;
        case 20: return SQ_CHORD_MODE(c->chord_mode);
        case 21: return SQ_CHORD_OCTS(c->chord_mode);
        case 22: return arp_rate_pos(c->arp_rate);
        case 23: return arp_run_of(c);
        case 24: return c->chord;
        case 25: return (c->flags & SQ_TF_FOLLOW) ? 127u : 0u;
        default: return 255u;
        }
    }
    if (ch == 12u) {
        if (num >= 101u && num <= 106u) return c->lane_base[num - 101u] <= 127u ? c->lane_base[num - 101u] : 255u;
        switch (num) {
        case 92: return ls;
        case 93: return l->shape;
        case 94: return l->rate;
        case 95: return l->depth;
        case 96: return l->dest;
        case 97: return l->enabled ? 127u : 0u;
        case 112: return tt;
        case 113: return track_mode(tt);
        case 114: return u7(((int32_t)project.viaggio.energy * 127 + 50) / 100);
        case 115: return (uint8_t)vg_genre_shown();
        case 116: return (uint8_t)vg_key_shown();
        case 117: return project.gen.harm_prog < SQ_PROGS_ALL ? project.gen.harm_prog : 255u;
        case 118: return harm_state();
        default: return 255u;
        }
    }
    if (project.live.remote_ch == SQ_REMOTE_OFF) return 255u;
    switch (num) {                                      /* channel 14 */
    case 1: return morph_pos;
    case 2: return project.live.morph_b < 8u ? project.live.morph_b : 255u;   /* (the page's MORPH TO: scenes 1-8) */
    case 4: return u7(((int32_t)project.gen.evo_amount - 1) * 127 / 99);
    case 5: return u7(((int32_t)project.gen.heat - 1) * 127 / 99);
    case 6: return project.live.quant;
    case 7: return u7((int32_t)mac_vel + 64);
    case 8: return u7(mac_gate < 0 ? 64 + ((int32_t)mac_gate * 64 - 45) / 90 : 64 + ((int32_t)mac_gate * 63 + 50) / 100);
    case 9: return u7(64 + ((int32_t)mac_swing * 63 + (mac_swing < 0 ? -12 : 12)) / 25);
    case 10: return u7((int32_t)mac_filt + 64);
    case 11: return u7(ktrans_target() + SQ_KTRANS_MAX);
    default: return 255u;
    }
}
static void fb_send(uint32_t k, uint8_t v)
{
    uint8_t ch, num, note, fl;
    fb_item(k, &ch, &num, &note, &fl);
    if (note) midi_send_c(1u, v ? 0x90u | ch : 0x80u | ch, num, v ? 127u : 0u);
    else midi_send_c(1u, 0xB0u | ch, num, v);
}

/* what the tablet sent: those cells show it already (a value that goes in another range: as it stands now) */
static void fb_heard(uint8_t st, uint8_t d1, uint8_t d2)
{
    uint8_t ch = st & 15u, isnote = (st & 0xF0u) == 0x90u || (st & 0xF0u) == 0x80u, on = (st & 0xF0u) == 0x90u && d2;
    uint32_t k;
    tab_seen = 1u;
    for (k = 0; k < FB_N; k++) {
        uint8_t c, num, note, fl;
        fb_item(k, &c, &num, &note, &fl);
        if (c != ch || num != d1 || note != isnote) continue;
        fb_touch[k] = (uint16_t)fm1_ms;
        fb_last[k] = (fl & FBF_SCALED) ? fb_value(k) : note ? (on ? 127u : 0u) : d2;
    }
}

static void tab_fb_reset(void)
{
    uint32_t k;
    for (k = 0; k < FB_N; k++) { fb_last[k] = 255u; fb_touch[k] = (uint16_t)(fm1_ms - 10000u); }
    tab_seen = 0u;
}

/* every pass: a few items that changed go to the hub (USB room left for the clock and the notes); every 40 ms one item
 * is sent again whatever (the whole set every few seconds: a hub that restarted, a page that came back) */
static void tab_fb_service(void)
{
    uint32_t i, sent = 0u;
    if (!tab_seen || usb_ports < 2u || project.live.remote_ch == SQ_REMOTE_OFF) return;
    if (!time_due(fm1_ms, fb_next_ms)) return;
    fb_next_ms = fm1_ms + 1u;
    for (i = 0; i < 16u && sent < 4u; i++) {
        uint32_t k = fb_pos;
        uint8_t v;
        fb_pos = (uint8_t)((fb_pos + 1u) % FB_N);
        if (midi_tx_room() <= 32u) break;
        if ((uint16_t)((uint16_t)fm1_ms - fb_touch[k]) < FB_HANDS_MS) continue;   /* the hand is on it */
        v = fb_value(k);
        if (v == 255u || v == fb_last[k]) continue;
        fb_send(k, v);
        fb_last[k] = v;
        sent++;
    }
    if (time_due(fm1_ms, fb_ref_ms)) {
        fb_ref_ms = fm1_ms + 40u;
        if ((uint16_t)((uint16_t)fm1_ms - fb_touch[fb_ref]) >= FB_HANDS_MS) fb_last[fb_ref] = 255u;
        fb_ref = (uint8_t)((fb_ref + 1u) % FB_N);
    }
}
