/* SPDX-License-Identifier: GPL-3.0-only */
/*
 * SAGGA BREAK (0.12) - a drum break cut into slices, re-ordered live. Included by dinghy.c after sagga_gen.c.
 *
 * The sampler (an M8, a Digitakt, Simpler ...) has the break on consecutive notes, a slice a note, from the track's
 * PEN note. A track in BREAK mode (HOME 4 K1) plays slices: every step is one (its number in the NOTE cell), the gate
 * is how long it rings, the ratchet a roll, the BEND lane its pitch; the key never touches it.
 *   SEQ 7 BREAK      K1 CHOP (the library, one a white key: 1 STRAIGHT 2 END ROLL 3 RUSH 4 REPEAT 5 DOUBLE 6 HALF
 *                    7 BACKWARDS 8 GHOST 9 LOW 10 HIGH 11 SHUFFLE 12 THINK 13 APACHE 14 SNARES 15 TRIPLE 16 BUILD:
 *                    written over the loop, UNDO takes it back), K2 ROLL (how many steps the dice rolls), K3 SWAP (how
 *                    much of the bar the dice re-orders), K4 SLICES (8, 16, 32: how many the break has)
 *   SEQ + black 1    the dice: the backbone kept (kick on 1 and 3, snare on 2 and 4), the rest re-ordered
 *   COOK / RANDOM    the next chop of the genre's (sq_brk_genre_chop: the library's genre, SEQ + PRESETS) / the dice
 *   ARP (held, or its window)   white 1-16 = chop 1-16: tapped it stays, held it plays while held and the pattern comes
 *                    back when the key goes; black 1 ROLL (the step playing again every 1/16 while held), 2 ROLL 1/32,
 *                    3 HALF, 4 DOUBLE, 5 BACKWARDS, 6 DICE, 7 RESET (STRAIGHT), 8 / 9 the chop after / before
 *   REC + whites     the slices 1-16 played and written (the Pi's pads and the grid play them too)
 *   the grid         the STEP view's note row is the 16 slices
 */

static uint8_t track_break(uint32_t t) { return (project.track[t].flags & SQ_TF_BREAK) ? 1u : 0u; }
static uint8_t brk_slices(uint32_t t) { return (uint8_t)SQ_BRK_SLICES(SQ_BRK_SL(project.track[t].brk_cfg)); }
static uint8_t brk_roll_held;                 /* ARP + black 1 / 2: 1 or 2 repeats a step of the track, 0 none */
static uint8_t brk_roll_t;                    /* ... the track whose step grid the roll follows */
static uint32_t brk_roll_slot;                /* ... the slot (ev[t].slot_start_us) served last */
static uint8_t brk_roll_phase;                /* ... how many repeats this slot got */
static uint8_t brk_roll_note = SQ_NOTE_NONE, brk_roll_ch, brk_roll_vel;
static uint8_t brk_live_t = 255u;             /* ... the track the remembered slice was played on */
static uint8_t brk_roll_sounding = SQ_NOTE_NONE, brk_roll_sounding_ch;   /* a repeat whose note-off is still to come */
static uint32_t brk_roll_off_us;
static uint8_t brk_live_key = 255u;           /* ARP + a white key down: the chop it plays (255 none) */
static uint8_t brk_live_t2, brk_live_chop_was, brk_live_saved;   /* ... its track, the chop before, the pattern before is kept */
static uint32_t brk_live_ms;
static sq_step_t brk_live_prev[SQ_STEPS] __attribute__((section(".pool")));   /* the pattern before the chop held */
static uint8_t brk_live_len;                                                   /* 0.24: ... and the track's length then */

static void brk_say(const char *what, uint32_t t)
{
    char *p = msg_buf;
    p = put_s(p, "BREAK T"); p = put_u(p, t + 1u); p = put_s(p, ": "); p = put_s(p, what); finish(p);
    status_msg(msg_buf);
}

/* the chop written over the loop of the track's playing pattern (UNDO takes it back) */
static void brk_chop_apply(uint32_t t, uint8_t chop)
{
    sq_track_cfg_t *c = &project.track[t];
    sq_step_t *row = project.step[t][tr[t].pattern];
    if (chop >= SQ_BRK_CHOPS) chop = 0u;
    undo_begin();
    undo_add((uint8_t)t, tr[t].pattern);
    c->brk_chop = chop;
    sq_brk_apply(row, c->start, c->length, chop, PEN(t), brk_slices(t));
    activate_row(t, row);
    brk_say(sq_brk_chop(chop)->name, t);
    regia_touched((uint8_t)t);
    ui_dirty = grid_dirty = 1u;
}

static void brk_dice_track(uint32_t t)        /* (dice_seq: inside a dice, the undo and the memory are the dice's) */
{
    sq_track_cfg_t *c = &project.track[t];
    sq_step_t *row = project.step[t][tr[t].pattern];
    sq_brk_dice(row, c->start, c->length, PEN(t), brk_slices(t), (uint8_t)SQ_BRK_SWAP(c->brk_cfg), (uint8_t)SQ_BRK_ROLL(c->brk_cfg),
                tool_heat, &sq_rng_state);
    activate_row(t, row);
}

static void brk_transform(uint32_t t, uint8_t what)   /* 0 HALF, 1 DOUBLE, 2 BACKWARDS */
{
    sq_track_cfg_t *c = &project.track[t];
    sq_step_t *row = project.step[t][tr[t].pattern];
    undo_begin();
    undo_add((uint8_t)t, tr[t].pattern);
    if (what == 0u) sq_brk_half(row, c->start, c->length, PEN(t), brk_slices(t));
    else if (what == 1u) sq_brk_double(row, c->start, c->length, PEN(t), brk_slices(t));
    else sq_brk_backwards(row, c->start, c->length);
    activate_row(t, row);
    brk_say(what == 0u ? "HALF" : what == 1u ? "DOUBLE" : "BACKWARDS", t);
    regia_touched((uint8_t)t);
    ui_dirty = grid_dirty = 1u;
}

/* COOK on a BREAK track (sagga_gen.c, tool_one): the next chop of the library's genre (beat_genre: SEQ + PRESETS), the
 * first when the one written is not the genre's; random (COOK held): another of the genre's, at random */
static uint8_t brk_cook_chop(uint32_t t, uint8_t random)
{
    uint8_t g = beat_genre < SQ_GENRES ? beat_genre : 0u, n = sq_brk_genre_chops(g), i, pos = n, cur = project.track[t].brk_chop;
    if (!n) return 0u;
    for (i = 0; i < n; i++) if (sq_brk_genre_chop(g, i) == cur) { pos = i; break; }
    if (random && n > 1u) {
        uint8_t r = (uint8_t)(sq_rng_next(&sq_rng_state) % (n - 1u));
        pos = pos >= n ? r : (uint8_t)((pos + 1u + r) % n);                  /* (never the one written) */
    } else pos = pos >= n ? 0u : (uint8_t)((pos + 1u) % n);
    return sq_brk_genre_chop(g, pos);
}
static void brk_cook_say(uint32_t t)                                     /* "BREAK T1: END ROLL (JUNGLE 2/7)" */
{
    uint8_t g = beat_genre < SQ_GENRES ? beat_genre : 0u, n = sq_brk_genre_chops(g), i, pos = 0u;
    char *p = msg_buf;
    for (i = 0; i < n; i++) if (sq_brk_genre_chop(g, i) == project.track[t].brk_chop) { pos = (uint8_t)(i + 1u); break; }
    p = put_s(p, "BREAK T"); p = put_u(p, t + 1u); p = put_s(p, ": "); p = put_s(p, sq_brk_chop(project.track[t].brk_chop)->name);
    p = put_s(p, " ("); p = put_s(p, sq_genre_name(g)); p = put_s(p, " "); p = put_u(p, pos); p = put_s(p, "/"); p = put_u(p, n); p = put_s(p, ")");
    finish(p);
    status_msg(msg_buf);
}

/* ARP + white key `wi` (key `k`) on BREAK track t: chop wi + 1 now. Let go within 0.6 s it stays (as the knob writes it);
 * held longer, the pattern as it was comes back when the key goes. A second key while one is held: its chop, the same
 * pattern underneath. */
static void brk_white(uint32_t t, uint8_t wi, uint32_t k)
{
    if (brk_live_key == 255u || brk_live_t2 != t) {                    /* the first key of the gesture: keep what is there */
        memcpy(brk_live_prev, project.step[t][tr[t].pattern], sizeof brk_live_prev);
        brk_live_len = project.track[t].length;                         /* 0.24 */
        brk_live_chop_was = project.track[t].brk_chop;
        brk_live_saved = 1u;
        brk_live_ms = fm1_ms;
    }
    brk_live_key = (uint8_t)k; brk_live_t2 = (uint8_t)t;
    brk_chop_apply(t, (uint8_t)(wi % SQ_BRK_CHOPS));
}
static void brk_white_up(uint32_t up)
{
    uint32_t t = brk_live_t2;
    if (brk_live_key == 255u || !(up & (1u << brk_live_key))) return;
    brk_live_key = 255u;
    if (!brk_live_saved || t >= SQ_TRACKS) return;
    brk_live_saved = 0u;
    if ((uint32_t)(fm1_ms - brk_live_ms) < 600u) return;                /* a tap: the chop stays */
    undo_begin();                                                       /* held: back to the pattern before (UNDO: the chop again) */
    undo_add((uint8_t)t, tr[t].pattern);
    memcpy(project.step[t][tr[t].pattern], brk_live_prev, sizeof brk_live_prev);
    if (brk_live_len != project.track[t].length)                        /* 0.24: the track's length changed under the key: the pattern fits it */
        sq_row_fit(project.step[t][tr[t].pattern], project.track[t].start, brk_live_len, project.track[t].length);
    gh_st[t].pat = 255u;
    project.track[t].brk_chop = brk_live_chop_was;
    activate_row(t, project.step[t][tr[t].pattern]);
    brk_say("BACK", t);
    regia_touched((uint8_t)t);
    ui_dirty = grid_dirty = 1u;
}

/* SEQ 7: the knobs */
static void break_knobs(uint32_t t, int32_t d1, int32_t d2, int32_t d3, int32_t d4, int32_t f2, int32_t f3)
{
    sq_track_cfg_t *c = &project.track[t];
    uint8_t sl = (uint8_t)SQ_BRK_SL(c->brk_cfg), roll = (uint8_t)SQ_BRK_ROLL(c->brk_cfg), swap = (uint8_t)SQ_BRK_SWAP(c->brk_cfg);
    (void)f2; (void)f3;
    if (d1) {
        if (!track_break(t)) { status_msg("HOME 4 K1: MAKE THE TRACK A BREAK FIRST"); return; }
        brk_chop_apply(t, change_u8(c->brk_chop, d1, 0u, SQ_BRK_CHOPS - 1u));
    }
    if (d2) { roll = change_u8(roll, d2, 0u, 7u); status_num("DICE ROLLS ", roll); }
    if (d3) { swap = change_u8(swap, d3, 0u, 7u); status_num("DICE SWAPS % ", (uint32_t)swap * 100u / 7u); }
    if (d4) { sl = change_u8(sl, d4, 0u, 2u); status_num("BREAK SLICES ", SQ_BRK_SLICES(sl)); }
    c->brk_cfg = SQ_BRK_PACK(sl, roll, swap);
}

/* ARP held, a black key, on a BREAK track */
static void brk_black(uint32_t t, int bi)
{
    switch (bi) {
    case 0: case 1:
        brk_roll_held = bi == 0 ? 1u : 2u;
        brk_roll_t = (uint8_t)t;
        brk_roll_slot = ev[t].slot_start_us;                           /* from the next step boundary: on the grid ... */
        brk_roll_phase = (ev[t].slot_dur_us && (uint32_t)(sq_micros() - ev[t].slot_start_us) < ev[t].slot_dur_us / 4u) ? 0u : brk_roll_held;   /* ... unless one just went by */
        if (brk_roll_note == SQ_NOTE_NONE || brk_live_t != t) {   /* nothing played by hand on this track: the step that plays */
            const sq_step_t *s = ev[t].step ? ev[t].step : &project.step[t][tr[t].pattern][tr[t].step];
            brk_roll_note = key_note(t, (s->flags & SQ_STEP_SET) && s->note[0] != SQ_NOTE_NONE ? s->note[0] : PEN(t));
            brk_roll_ch = track_ch(t); brk_roll_vel = 100u; brk_live_t = (uint8_t)t;
        }
        status_msg(bi == 0 ? "ROLL 1/16 (HOLD)" : "ROLL 1/32 (HOLD)");
        break;
    case 2: brk_transform(t, 0u); break;
    case 3: brk_transform(t, 1u); break;
    case 4: brk_transform(t, 2u); break;
    case 5: dice_roll(DICE_SEQ); break;
    case 6: brk_chop_apply(t, 0u); break;
    case 7: brk_chop_apply(t, (uint8_t)((project.track[t].brk_chop + 1u) % SQ_BRK_CHOPS)); break;
    case 8: brk_chop_apply(t, (uint8_t)((project.track[t].brk_chop + SQ_BRK_CHOPS - 1u) % SQ_BRK_CHOPS)); break;
    default: break;
    }
}
static void brk_roll_off(void)                /* the repeat sounding ends */
{
    if (brk_roll_sounding != SQ_NOTE_NONE) { midi_send(0x80u | brk_roll_sounding_ch, brk_roll_sounding, 0u); brk_roll_sounding = SQ_NOTE_NONE; }
}
static void brk_black_up(int bi) { if (bi == 0 || bi == 1) { brk_roll_held = 0u; brk_roll_off(); } }
static void brk_roll_clear(void)              /* STOP, a project loaded: nothing remembered, nothing held */
{
    brk_roll_held = 0u; brk_roll_off(); brk_roll_note = SQ_NOTE_NONE; brk_live_t = 255u;
}

/* a slice played by hand (ARP + a white key; the keys with REC too, the Pi's pads): remembered for ROLL */
static void brk_live_played(uint8_t ch, uint8_t note, uint8_t vel) { brk_roll_note = note; brk_roll_ch = ch; brk_roll_vel = vel; brk_live_t = selected_track; }

/* every pass: the live ROLL repeats the slice on the track's step grid (once a step, or twice: 1/32) while the key is
 * held: the repeats fall where the steps fall, swing and all; each repeat rings for half its time (a gate, for samplers
 * that want one) */
static void brk_service(void)
{
    uint32_t t = brk_roll_t, now = sq_micros();
    if (brk_roll_sounding != SQ_NOTE_NONE && (int32_t)(now - brk_roll_off_us) >= 0) brk_roll_off();
    if (!brk_roll_held || !playing || brk_roll_note == SQ_NOTE_NONE || t >= SQ_TRACKS || !ev[t].slot_dur_us) return;
    if (ev[t].slot_start_us != brk_roll_slot) { brk_roll_slot = ev[t].slot_start_us; brk_roll_phase = 0u; }
    if (brk_roll_phase == 0u || (brk_roll_held == 2u && brk_roll_phase == 1u && (uint32_t)(now - ev[t].slot_start_us) >= ev[t].slot_dur_us / 2u)) {
        brk_roll_off();
        midi_send(0x90u | brk_roll_ch, brk_roll_note, brk_roll_vel);
        brk_roll_sounding = brk_roll_note; brk_roll_sounding_ch = brk_roll_ch;
        brk_roll_off_us = now + ev[t].slot_dur_us / (brk_roll_held == 2u ? 4u : 2u);
        brk_roll_phase++;
    }
}

/* ---- 0.13 NOTE REPEAT: on a DRUM track, ARP (held, or its window) + black 1 / 2 / 3 / 4 held: the drum keys held strike
 * again once a step / twice a step / three times a step / every other step, on the selected track's grid, while the
 * black is held (1/16, 1/32, 1/32T, 1/8 on a 1/16 track). REC writes them: a hit a step, or the step with that ratchet. */
static uint8_t rep_rate, rep_t = 255u, rep_done, rep_par;   /* the black held 1..4 (0: none), the grid's track, the hits
                                                             * of this step done, the steps that strike (every other) */
static uint32_t rep_slot;
static uint8_t rep_factor(void) { return rep_rate == 2u ? 2u : rep_rate == 3u ? 3u : 1u; }
static void rep_black(uint32_t t, int bi)
{
    static const char *const N[4] = {"REPEAT 1/16 (HOLD)", "REPEAT 1/32 (HOLD)", "REPEAT 1/32T (HOLD)", "REPEAT 1/8 (HOLD)"};
    uint32_t el, dur = ev[t].slot_dur_us;
    rep_rate = (uint8_t)(bi + 1); rep_t = (uint8_t)t;
    rep_slot = ev[t].slot_start_us;
    el = (uint32_t)(sq_micros() - ev[t].slot_start_us);
    rep_done = dur ? (uint8_t)(el * rep_factor() / dur + 1u) : 255u;   /* (the hits of this step gone by: from the next one) */
    if (rep_rate == 4u) { rep_par = (uint8_t)((ev[t].step_index + 1u) & 1u); rep_done = 255u; }
    status_msg(N[bi & 3]);
}
static void rep_up(uint32_t up)
{
    if (rep_rate && (up & (1u << black_key[rep_rate - 1u]))) rep_rate = 0u;
}
static void rep_clear(void) { rep_rate = 0u; }
/* one strike of every drum key held */
static void rep_strike(uint8_t first)
{
    uint32_t k;
    for (k = 0; k < 16u; k++) {
        uint32_t key = white_key[k];
        uint8_t dt, note;
        if (!(live_held & (1u << key))) continue;
        dt = vg_rec_t < SQ_TRACKS ? vg_rec_t : drum_track_n((uint8_t)k);
        if (dt >= SQ_TRACKS) continue;
        midi_send(0x80u | live_ch[key], live_note[key], 0u);
        midi_send(0x90u | live_ch[key], live_note[key], 100u);
        note = PEN(dt);
        if (record_arm && first) {
            int stp = record_note(dt, note, 100u);
            if (stp >= 0 && rep_factor() > 1u) { project.step[dt][tr[dt].pattern][stp].ratchet = rep_factor(); }
            if (stp >= 0) rec_close_note((uint8_t)(128u + key));      /* (a drum: no length to keep) */
        }
    }
}
static void rep_service(void)
{
    uint32_t t = rep_t, now, el, dur;
    uint8_t f;
    if (!rep_rate || !playing || t >= SQ_TRACKS || !(dur = ev[t].slot_dur_us)) return;
    if (ev[t].slot_start_us != rep_slot) {
        rep_slot = ev[t].slot_start_us;
        rep_done = (rep_rate == 4u && ((ev[t].step_index & 1u) != rep_par)) ? 255u : 0u;
    }
    if (rep_done == 255u) return;
    f = rep_factor();
    if (rep_done >= f) return;
    now = sq_micros();
    el = (uint32_t)(now - ev[t].slot_start_us);
    if (el * f >= (uint32_t)rep_done * dur) { rep_strike(rep_done == 0u ? 1u : 0u); rep_done++; }
}

