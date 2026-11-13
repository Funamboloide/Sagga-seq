/* SPDX-License-Identifier: GPL-3.0-only */
/*
 * SAGGA 0.13, the live additions. Included by dinghy.c after sagga_live2.c.
 *
 *   KEYBOARD  SAVE 4 K2/K3: a keyboard on the MIDI IN transposes the key (TRANSPOSE, as PERF + K3): the note played,
 *             taken from the key's root as it was before any transpose, is how far (-5 .. +6). ALL: every note of the
 *             channel; SPLIT: the notes below C3, the ones above play (and record) as before. It waits for QUANTISE.
 *   MIDI IN   SAVE 4 K4 ALWAYS: the notes that come in play on the selected track even without REC (REC still records).
 *   MOTION    SAVE 4 K1: 1, 2 or 4 bars. With REC on, what FX + K1..K4 (and the remote, and a THROW gliding back) do to
 *             the macros is written into the loop, a 16th a cell; then it plays back. The hand wins while it turns
 *             (and 0.3 s after). FX + OCT- (MACROS 0) wipes the motion too.
 *   SLIDE     EDIT + black 7: the step holds into the next (as TIE) and the next note glides: portamento on (CC 65 127)
 *             before it, off (CC 65 0) before the first note that does not slide. The synth sets the glide's time.
 *   CHAIN     HOME 7 K2 LIST, HOME 8: up to 8 patterns, each 1..8 times, one after the other (each at the end of the
 *             loop before). PLAY starts the list from its first entry; a pattern chosen by hand that is in the list
 *             goes on from there, one that is not switches the list off.
 */

/* ---- KEYBOARD: the transpose from a keyboard on the MIDI IN */
static uint32_t kb_held[4];                      /* the notes the transpose took (their off is taken too) */
static uint8_t kb_takes(uint8_t st, uint8_t note)
{
    const sq_ext_t *x = &project.ext;
    if (!x->kb_mode) return 0u;
    if (x->kb_ch && (uint8_t)(st & 15u) != (uint8_t)(x->kb_ch - 1u)) return 0u;
    if (x->kb_mode == SQ_KB_SPLIT && note >= SQ_KB_SPLIT_NOTE) return 0u;
    return 1u;
}
static void kb_down(uint8_t note)
{
    int32_t base = ((int32_t)project.key_root - (int32_t)project.live.ktrans % 12 + 24) % 12;   /* the root before the transpose */
    kb_held[(note >> 5) & 3u] |= 1u << (note & 31u);
    ktrans_set(sq_kb_transpose(note, (uint8_t)base));
}
static uint8_t kb_up(uint8_t note)
{
    uint32_t b = 1u << (note & 31u), *w = &kb_held[(note >> 5) & 3u];
    if (!(*w & b)) return 0u;
    *w &= ~b;
    return 1u;
}

/* ---- MOTION */
static uint8_t mot_live;                         /* bit per macro: the hand (or a throw) moved it just now */
static uint32_t mot_ms[4];
static void mot_touch(uint8_t i) { i &= 3u; mot_live |= (uint8_t)(1u << i); mot_ms[i] = fm1_ms; }
static uint8_t mot_any(void)
{
    uint32_t i, k;
    for (i = 0; i < 4u; i++) for (k = 0; k < SQ_MOTION_CELLS; k++) if (project.ext.motion[i][k] != (int8_t)SQ_MOTION_NONE) return 1u;
    return 0u;
}
static void mot_clear(void)
{
    uint32_t i, k;
    for (i = 0; i < 4u; i++) for (k = 0; k < SQ_MOTION_CELLS; k++) project.ext.motion[i][k] = (int8_t)SQ_MOTION_NONE;
}
static uint32_t mot_cells(void) { return project.ext.motion_bars ? 16u * project.ext.motion_bars : 0u; }
static uint32_t mot_pos(void) { uint32_t n = mot_cells(); return n ? (global_clock / 6u) % n : 0u; }
/* a 16th line (seq_clock_tick, before the tick moves on): write where the hand is, else play what was written */
static void motion_tick(void)
{
    uint32_t i, pos;
    if (!project.ext.motion_bars || !playing) return;
    pos = mot_pos();
    for (i = 0; i < 4u; i++) {
        int8_t *cell = &project.ext.motion[i][pos];
        uint8_t bit = (uint8_t)(1u << i);
        if ((mot_live & bit) && (uint32_t)(fm1_ms - mot_ms[i]) >= 300u && !(throw_on & bit)) mot_live &= (uint8_t)~bit;
        if (mot_live & bit) {                                       /* the hand wins; with REC its move goes in */
            if (record_arm) *cell = (int8_t)macro_get((uint8_t)i);
            continue;
        }
        if (*cell != (int8_t)SQ_MOTION_NONE && *cell != macro_get((uint8_t)i)) { macro_put((uint8_t)i, *cell); ui_dirty = 1u; }
    }
}

/* ---- SLIDE: portamento on the channel (CC 65) for the note after a SLIDE step */
static uint16_t porta_ch;                        /* the channels it was switched on (we only switch off what we switched on) */
static uint16_t slide_from;                      /* bit per track: its step before slid into the one now */
static uint32_t slide_until[SQ_TRACKS];
static void slide_note(uint32_t t, const sq_step_t *s, uint8_t ch, uint32_t now)
{
    uint8_t want = (slide_from & (1u << t)) && !time_due(now, slide_until[t]) ? 1u : 0u;
    if (want != ((porta_ch >> (ch & 15u)) & 1u)) {
        send_cc(ch, 65u, want ? 127u : 0u);
        porta_ch ^= (uint16_t)(1u << (ch & 15u));
    }
    if ((s->flags & SQ_STEP_SLIDE) && !track_drum(t) && !track_break(t)) {
        slide_from |= (uint16_t)(1u << t);
        slide_until[t] = ev[t].slot_start_us + ev[t].slot_dur_us + 25000u;   /* (the next step's note, a little late too) */
    } else slide_from &= (uint16_t)~(1u << t);
}
static void porta_all_off(void)
{
    uint32_t ch;
    slide_from = 0u;
    if (!porta_ch) return;
    for (ch = 0; ch < 16u; ch++) if (porta_ch & (1u << ch)) send_cc((uint8_t)ch, 65u, 0u);
    porta_ch = 0u;
}

/* ---- CHAIN LIST */
static uint8_t chain_pos[SQ_TRACKS], chain_left[SQ_TRACKS], chain_set[SQ_TRACKS];   /* chain_set: the pattern the list put there */
static uint8_t chain_edit;                       /* HOME 8: the entry the knobs change */
static void chain_begin(uint32_t t)              /* the list switched on: from where the track is (in the list or not) */
{
    const sq_trackx_t *c = &project.ext.track[t];
    int k = sq_chain_find(c, tr[t].pattern);
    chain_pos[t] = k >= 0 ? (uint8_t)k : 255u;    /* (not in it: the list starts at the end of this loop) */
    chain_left[t] = k >= 0 ? c->chain_rep[k] : 1u;
    chain_set[t] = tr[t].pattern;
}
static void chain_start(void)                    /* PLAY: every list from its first entry */
{
    uint32_t t;
    for (t = 0; t < SQ_TRACKS; t++) {
        const sq_trackx_t *c = &project.ext.track[t];
        if (!c->chain_on) continue;
        chain_pos[t] = 0u;
        chain_left[t] = c->chain_rep[0];
        tr[t].pattern = chain_set[t] = c->chain_pat[0];
        tr[t].pending_pattern = SQ_NO_PENDING;
    }
}
/* the end of track t's loop: the next pattern of its list */
static void chain_wrap(uint32_t t)
{
    sq_trackx_t *c = &project.ext.track[t];
    uint8_t p;
    if (tr[t].pattern != chain_set[t]) {          /* chosen by hand, a scene: the list goes on from it, if it is there */
        int k = sq_chain_find(c, tr[t].pattern);
        if (k < 0) {
            char *q = msg_buf;
            c->chain_on = 0u;
            q = put_s(q, "T"); q = put_u(q, t + 1u); q = put_s(q, " CHAIN LIST OFF: P"); q = put_u(q, (uint32_t)tr[t].pattern + 1u); q = put_s(q, " IS NOT IN IT"); finish(q);
            status_msg(msg_buf);
            return;
        }
        chain_pos[t] = (uint8_t)k;
        chain_left[t] = c->chain_rep[k];
    }
    p = sq_chain_next(c, &chain_pos[t], &chain_left[t]);
    tr[t].pattern = chain_set[t] = p;
    if (t == selected_track) ui_dirty = 1u;
}
static uint8_t chain_mode(uint32_t t)            /* HOME 7 K2: 0 OFF, 1 the pair (0.10), 2 the list */
{
    return project.ext.track[t].chain_on ? 2u : (project.track[t].flags & SQ_TF_CHAIN) ? 1u : 0u;
}
static void chain_mode_set(uint32_t t, uint8_t m)
{
    sq_track_cfg_t *cfg = &project.track[t];
    cfg->flags &= (uint8_t)~SQ_TF_CHAIN;
    project.ext.track[t].chain_on = 0u;
    if (m == 1u) cfg->flags |= SQ_TF_CHAIN;
    else if (m == 2u) { project.ext.track[t].chain_on = 1u; chain_begin(t); }
    status_msg(m == 1u ? "CHAIN: THIS PATTERN + ITS PARTNER, 128 STEPS" : m == 2u ? "CHAIN LIST: HOME 8 WRITES IT" : "CHAIN OFF");
}
static void chain_knobs(int32_t d1, int32_t d2, int32_t d3, int32_t d4)   /* HOME 8 */
{
    sq_trackx_t *c = &project.ext.track[selected_track];
    char *p = msg_buf;
    if (chain_edit >= c->chain_n) chain_edit = (uint8_t)(c->chain_n - 1u);
    if (d1) { c->chain_n = change_u8(c->chain_n, d1, 1u, SQ_CHAIN_MAX); if (chain_edit >= c->chain_n) chain_edit = (uint8_t)(c->chain_n - 1u); }
    if (d2) chain_edit = change_u8(chain_edit, d2, 0u, (uint8_t)(c->chain_n - 1u));
    if (d3) c->chain_pat[chain_edit] = change_u8(c->chain_pat[chain_edit], d3, 0u, SQ_PATTERNS - 1u);
    if (d4) c->chain_rep[chain_edit] = change_u8(c->chain_rep[chain_edit], d4, 1u, 8u);
    if (!(d1 || d2 || d3 || d4)) return;
    p = put_s(p, "ENTRY "); p = put_u(p, (uint32_t)chain_edit + 1u); p = put_s(p, ": P"); p = put_u(p, (uint32_t)c->chain_pat[chain_edit] + 1u);
    p = put_s(p, " X"); p = put_u(p, c->chain_rep[chain_edit]);
    if (!c->chain_on) p = put_s(p, " (HOME 7 K2: LIST)");
    finish(p);
    status_msg(msg_buf);
}
