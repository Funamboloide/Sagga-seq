/* SPDX-License-Identifier: GPL-3.0-only */
/*
 * SAGGA GRID - a 16 x 8 pad grid (two Launchpad Minis side by side) over the FM-1's single USB MIDI cable.
 * Included by dinghy.c after the editing helpers. The wire protocol and the control map are in
 * docs/SAGGA-GRID.md; a Raspberry Pi script (tools/sagga_grid_bridge.py) translates it to the Launchpads.
 *
 *   to the FM-1   channel 16  Note On/Off   note = y * 16 + x   pad down / up (velocity 0 = up)
 *                 channel 15  CC id 0..31   127 down, 0 up      the 16 top buttons (0-15), 16 side buttons (16-31)
 *                 channel 16  CC 118        127 attach (repaint), 64 keep-alive, 0 detach
 *   from the FM-1 channel 16  Note On       note = y * 16 + x   velocity = LED role (GL_*)
 *                 channel 15  CC id 0..31   value = LED role
 *
 * Nothing is sent until a bridge attaches, and the FM-1 lets go again if it hears nothing for 3.5 s.
 * Tracks therefore use MIDI channels 1-14 only.
 *
 * Fourteen views share the pads; the buttons never change:
 *   top left     PLAY  REC  FILL  UNDO  STEP  PERF  TRACK  SHIFT        (with SHIFT: CONTINUE, PROJ, BANK, FX, CC, LFO, BEAT)
 *                STEP again: the DRUM view (eight tracks at once); CC again: FOLLOW (0.12 PICK: the four knobs of the window open
 *                on the FM-1, their values on the pads); PERF again: the SONG view; TRACK again: TRACK 2 (the
 *                loops of the notes, velocities, gates and the Program Change, 0.5), again: TRACK 3 (voicing, strum, MIDI
 *                FX, the algorithm, long gates, the channel: 0.8); PROJ again: LIB (the library, 0.5); BEAT again: EUCLID
 *                (the bank's eight tracks, live, 0.8)
 *   top right    the tracks of the bank (SHIFT: solo)                     left side: the 8 patterns (SHIFT: copy here)
 *   right side   the 8 scenes (SHIFT: store)
 * SHIFT tapped twice quickly (nothing else pressed) stays held: the grid with one hand; once more lets it go (0.5.1).
 */

#define GR_RESERVE    28u      /* LED messages go out only while this many USB MIDI slots are free: notes and clock keep them */
#define GR_BUDGET     8u       /* LED messages per frame */
#define GR_FRAME_MS   20u
#define GR_REFRESH_MS 100u     /* when nothing changed, one LED is sent again this often: a lost message heals */
#define GR_TIMEOUT_MS 3500u
#define GR_LOOPDONE_MS 4000u   /* after a loop gesture the pads that are still down are ignored for this long at most */

enum { GV_STEP = 0, GV_PERF, GV_TRACK, GV_CC, GV_LFO, GV_BEAT, GV_FX, GV_PROJ, GV_DRUM, GV_SONG, GV_TRACK2, GV_LIB,
       GV_EUCLID, GV_TRACK3, GV_VIAGGIO, GV_REGIA, GV_PICK, GV_COUNT };
static const char *const GV_NAME[GV_COUNT] = {"STEP", "PERF", "TRACK", "CC", "LFO", "BEAT", "FX", "PROJ", "DRUM", "SONG",
                                              "TRACK2", "LIB", "EUCLID", "TRACK3", "VIAGGIO", "REGIA", "FOLLOW"};   /* (0.18: PICK is FOLLOW) */

/* LED roles: the bridge decides the colours (tools/sagga_grid_bridge.py, ROLE_RGB) */
enum { GL_OFF = 0, GL_FAINT, GL_DIM, GL_ON, GL_ACCENT, GL_PLAY, GL_CURSOR, GL_BLUE,
       GL_MUTED, GL_PEND, GL_FILL, GL_WHITE, GL_CYAN, GL_VIOLET, GL_ORANGE, GL_YELLOW,
       GL_TAIL, GL_TIE };                                   /* 0.12: a step a long note covers; a step tied to the next */

/* the 32 buttons: 0-7 left Launchpad top row, 8-15 right Launchpad top row, 16-23 and 24-31 their side columns */
enum { GC_PLAY = 0, GC_REC, GC_FILL, GC_UNDO, GC_VSTEP, GC_VPERF, GC_VTRACK, GC_SHIFT,
       GC_TRK0 = 8, GC_PAT0 = 16, GC_SCN0 = 24 };

static const uint8_t GR_SWING[8]  = {50, 53, 56, 59, 62, 65, 70, 75};
static const uint8_t GR_HUM[8]    = {0, 3, 6, 10, 15, 20, 30, 50};
static const uint8_t GR_GATE[8]   = {12, 25, 37, 50, 62, 75, 87, 100};
/* 0.10: the long gates TRACK 3 row 6 offers: 1.5, 2 .. 6, 8 .. 16, 20 .. 64 steps (a whole 64-step pattern); SHIFT: 17 .. 32 one by one */
static const uint8_t GR_LONG[16]  = {101, 102, 103, 104, 105, 106, 108, 110, 112, 116, 120, 124, 132, 140, 148, 164};
static const int8_t  GR_VOFF[15]  = {-63, -48, -36, -24, -16, -8, -4, 0, 4, 8, 16, 24, 36, 48, 63};
static const int8_t  GR_NUDGE[15] = {-50, -40, -30, -20, -14, -8, -4, 0, 4, 8, 14, 20, 30, 40, 50};
static const int8_t  GR_SHIFT[15] = {-24, -12, -7, -5, -3, -2, -1, 0, 1, 2, 3, 5, 7, 12, 24};
static const uint8_t GR_CCP[16]   = {1, 5, 7, 10, 11, 12, 13, 64, 71, 72, 73, 74, 75, 91, 93, 94};   /* mod, portamento, volume, pan, ... */
static const uint8_t GR_CCLV[4]   = {127, 80, 48, 16};                                              /* the level of the four rows of a CC bar */
static const uint8_t GR_DENS[8]   = {10, 20, 30, 40, 50, 60, 75, 90};                               /* BEAT view: random density */
static const uint8_t GR_HEAT[8]   = {5, 10, 20, 30, 40, 55, 70, 90};                                /* ... COOK heat */
static const uint8_t GR_EVOAMT[7] = {5, 10, 20, 30, 45, 60, 80};                                    /* ... EVOLVE amount */
static const uint8_t GR_BARS[16]  = {1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 16, 20, 24, 32, 48, 64};       /* SONG view: bars of an entry */
/* 0.8 TRACK 3 */
static const uint8_t GR_KEEP[8]   = {20, 30, 40, 50, 60, 70, 85, 100};                              /* ECHO keeps / HARM velocity % */
static const uint8_t GR_MUT[16]   = {0, 2, 5, 10, 15, 20, 30, 40, 50, 60, 70, 80, 90, 95, 98, 100};  /* TURING mutation */
static const uint8_t GR_RULE[16]  = {30, 45, 54, 60, 73, 90, 105, 110, 122, 126, 150, 18, 22, 57, 62, 184};   /* CELL rules */
static const uint8_t GR_CELLS[16] = {4, 6, 8, 10, 12, 14, 16, 20, 24, 28, 32, 40, 48, 56, 60, 64};
static const uint8_t GR_DENSA[16] = {0, 15, 30, 45, 60, 75, 90, 100, 110, 120, 135, 150, 165, 180, 190, 200};   /* DENSITY */

static uint8_t g_view = GV_STEP;
static uint8_t g_follow;                   /* 0.18 FOLLOW: the view goes with the FM-1's page (a view chosen by hand: off) */
static uint8_t g_follow_want = 255u;       /* ... the view the FM-1's page asks for, and since when */
static uint32_t g_follow_ms;
static uint32_t g_ctl_held, g_last_seen;
static uint8_t g_shift_lock;              /* SHIFT tapped twice: it stays held */
static uint8_t g_shift_clean, g_shift_tapped;   /* the SHIFT press held is a bare tap so far / the last one was a bare tap */
static uint32_t g_shift_down, g_shift_up;
static uint8_t g_want[128], g_sent[128], g_cwant[32], g_csent[32];
static uint32_t g_next_frame, g_next_refresh, g_refresh_i;

/* step pads: a pad held, then another one: the loop between them. The first step is put back as it was. */
static uint8_t g_hold_pad = 255u;         /* 0..63 a step pad is held; 254 the loop gesture is done; 255 nothing */
static uint8_t g_hold_flip;               /* the held pad has toggled its step and may still be put back */
static uint32_t g_hold_since, g_loop_done;
static sq_step_t g_hold_prev;
static uint32_t g_down[2];                /* step pads that are down (64 bits; no 64-bit arithmetic on the target) */

#define g_lane env_lane                   /* CC view: the lane being drawn (0.10: the same lane the panel shows) */
static uint16_t g_fx_held, g_fx_latch, g_kill_held, g_kill_latch;   /* FX view: momentary and (with SHIFT) latched */
static uint16_t g_loop_mask = 0xFFFFu;    /* FX view: the tracks the DJ loop takes */
static uint8_t g_temp_held;               /* FX view: TEMP is held on its pad (not latched) */
static uint8_t g_song_sel;                /* SONG view: the entry being edited (len = a new one at the end) */
static uint8_t g_pc_scene;                /* TRACK 2 view: the scene whose Program Change row 4 sets */
static uint8_t g_lib_armed = 255u;        /* LIB view: the file tapped last (tapped again: LOAD) */
static uint8_t g_drum_hold = 255u;        /* DRUM view: the pad held (y * 16 + x), to select its step when held */
static uint8_t g_vg_hold = 255u;          /* 0.9 VIAGGIO view: the track pad held (hold = the dice) */
static uint32_t g_vg_hold_ms;
static uint8_t g_genre_page;
static uint8_t g_part_page, g_var_page;       /* 0.11 BEAT view: the page of the parts (row 2), of the variations (row 3) */              /* BEAT view: genres 1-12 or 13-24 on the first row (0.8) */
static const char *f_gate(uint8_t v);      /* sagga_ui.c */
static uint32_t g_drum_since;
static sq_step_t g_drum_prev;

static void grid_init(void)
{
    grid_attached = 0u;
    grid_fill = 0u;
    grid_fx = 0u;
    grid_kill = 0u;
    g_ctl_held = 0u;
}

static void gr_invalidate(void)
{
    memset(g_sent, 0xFF, sizeof g_sent);
    memset(g_csent, 0xFF, sizeof g_csent);
}

static void gr_fx_sync(void)
{
    grid_fx = (uint16_t)(g_fx_held | g_fx_latch);
    grid_kill = (uint16_t)(g_kill_held | g_kill_latch);
    ui_dirty = grid_dirty = 1u;
}

static void gr_temp_release(void)          /* a TEMP held on the grid ends when its pad can no longer come up */
{
    if (g_temp_held) { g_temp_held = 0u; temp_end(); }
}

static void gr_repeat_release(void)        /* LOOP / REPEAT pads held on the grid: their pad-up will not come */
{
    loop_release_all(0xFFFFu << LP_GRID);
}

static void gr_release_all(void)
{
    gr_temp_release();
    gr_repeat_release();
    g_drum_hold = 255u;
    g_hold_pad = 255u;
    g_vg_hold = 255u;
    g_down[0] = g_down[1] = 0u;
    g_fx_held = g_fx_latch = g_kill_held = g_kill_latch = 0u;
    g_ctl_held = 0u;
    g_shift_lock = 0u;
    grid_fill = 0u;
    gr_fx_sync();
}

static void gr_set_attached(uint8_t on)
{
    if (on) {
        if (!grid_attached) status_msg("GRID ATTACHED");
        grid_attached = 1u;
        g_hold_pad = 255u;
        g_down[0] = g_down[1] = 0u;
        gr_invalidate();
    } else {
        if (grid_attached) status_msg("GRID LOST");
        grid_attached = 0u;
        gr_release_all();                  /* nothing stays held that the grid held: fills, effects, kills */
    }
    ui_dirty = 1u;
}

static void gr_view_go(uint8_t v)
{
    if (v >= GV_COUNT) return;
    if (v != g_view) {
        g_view = v;
        gr_temp_release();
        gr_repeat_release();
        if (v == GV_TRACK2) g_pc_scene = scene_cursor;
        if (v == GV_LIB) { g_lib_armed = 255u; lib_ask_list(); }
        g_drum_hold = 255u;
        g_hold_pad = 255u;
        g_down[0] = g_down[1] = 0u;
        g_fx_held = g_kill_held = 0u;      /* the pad-up of a held effect would go to another view */
        gr_fx_sync();
    }
    ui_dirty = grid_dirty = 1u;
}
/* a view button: that view; 0.18: FOLLOW (SHIFT + STEP twice) goes with the FM-1 from now on, any other stops it */
static void gr_set_view(uint8_t v)
{
    if (v >= GV_COUNT) return;
    gr_view_go(v);
    g_follow = v == GV_PICK ? 1u : 0u;
    g_follow_want = 255u;
    status_msg(v == GV_PICK ? "FOLLOW: THE GRID GOES WITH THE FM-1" : GV_NAME[v]);
}

static const char *gr_view_name(void) { return GV_NAME[g_view]; }

static uint8_t gr_shift(void) { return ((g_ctl_held & (1u << GC_SHIFT)) || g_shift_lock) ? 1u : 0u; }
static uint8_t gr_note_base(void) { return (uint8_t)clamp_i32(48 + 12 * (int32_t)key_octave, 0, 112); }
static sq_step_t *gr_row(void) { return project.step[selected_track][tr[selected_track].pattern]; }
static uint8_t gr_val16(uint32_t x) { return (uint8_t)((x * 127u + 7u) / 15u); }   /* 0..15 -> 0..127 */
static uint8_t gr_pct16(uint32_t x) { return (uint8_t)(((x + 1u) * 100u + 8u) / 16u); }   /* 0..15 -> 6..100 */

/* the note a pad of the note row plays: chromatic from the base, or - on a track that follows a key - the notes of the
 * scale from its first root at or above the base (two octaves and more on the sixteen pads) */
static uint8_t gr_in_key(uint32_t t) { return (track_in_key(t) && project.key_scale != SQ_SC_CHROMATIC) ? 1u : 0u; }

static uint8_t gr_pad_note(uint32_t t, uint32_t x)
{
    uint32_t base = gr_note_base(), n, i;
    uint16_t mask;
    if (track_break(t)) return clamp_note((int32_t)PEN(t) + (int32_t)(x % brk_slices(t)));   /* 0.12: the slices (wrapping on 8) */
    if (!gr_in_key(t)) return clamp_note((int32_t)(base + x));
    mask = sq_scale_mask(project.key_scale);
    n = base + (project.key_root + 12u - base % 12u) % 12u;       /* the first root at or above the base */
    for (i = 0; i < x; i++) {
        do { n++; } while (n < 128u && !((mask >> ((n + 12u - project.key_root) % 12u)) & 1u));
    }
    return n > 127u ? 127u : (uint8_t)n;
}

/* ------------------------------------------------------------ input */

static void gr_copy_pattern(uint8_t dst)
{
    uint8_t t = selected_track, src = tr[t].pattern;
    if (dst == src) { queue_pattern(t, dst); return; }
    undo_begin();
    undo_add(t, dst);
    memcpy(project.step[t][dst], project.step[t][src], sizeof project.step[0][0]);
    status_num("COPIED TO PATTERN ", (uint32_t)dst + 1u);
    ui_dirty = grid_dirty = 1u;
}

static void gr_ctl(uint8_t id, uint8_t down)
{
    uint32_t bit = 1u << id;
    uint8_t shift = gr_shift(), bank = (uint8_t)(selected_track & 8u);
    if (down) g_ctl_held |= bit; else g_ctl_held &= ~bit;
    if (id == GC_SHIFT) {                               /* two bare taps: SHIFT stays; once more: it goes */
        if (!down) {
            g_shift_tapped = (g_shift_clean && (uint32_t)(fm1_ms - g_shift_down) < 300u) ? 1u : 0u;
            g_shift_up = fm1_ms;
            g_shift_clean = 0u;
            return;
        }
        g_shift_clean = 0u;
        if (g_shift_lock) { g_shift_lock = 0u; g_shift_tapped = 0u; status_msg("SHIFT OFF"); }
        else if (g_shift_tapped && (uint32_t)(fm1_ms - g_shift_up) < 350u) {
            g_shift_lock = 1u; g_shift_tapped = 0u;
            status_msg("SHIFT STAYS: SHIFT AGAIN TO LET GO");
        } else { g_shift_clean = 1u; g_shift_down = fm1_ms; }
        ui_dirty = grid_dirty = 1u;
        return;
    }
    if (down) { g_shift_clean = 0u; g_shift_tapped = 0u; }   /* (a SHIFT used with something is not a tap) */
    if (id == GC_FILL) {
        if (!down) grid_fill = 0u;
        else if (shift) select_track((uint8_t)(selected_track ^ 8u));       /* SHIFT + FILL: the other eight tracks */
        else grid_fill = 1u;
        ui_dirty = 1u;
        return;
    }
    if (!down) return;

    if (id == GC_PLAY) {
        if (shift) { if (!playing) transport_continue(); }                  /* SHIFT + PLAY: carry on from where it stopped */
        else if (playing) transport_stop();
        else transport_start();
    } else if (id == GC_REC) {
        if (shift) gr_set_view(g_view == GV_PROJ ? GV_LIB : GV_PROJ);              /* PROJ again: LIB */
        else { rec_toggle(); ui_dirty = 1u; }
    } else if (id == GC_UNDO) {
        if (shift) gr_set_view(GV_FX);
        else if (dice_pending) dice_answer(0u);                            /* a dice waits: UNDO puts it back */
        else undo_swap();
    } else if (id == GC_VSTEP) {
        gr_set_view(shift ? (g_view == GV_CC ? GV_PICK : GV_CC) : g_view == GV_STEP ? GV_DRUM : GV_STEP);  /* STEP again: DRUM; CC again: FOLLOW */
    } else if (id == GC_VPERF) {
        /* PERF again: SONG; then VIAGGIO (0.9); then REGIA, once a regista on the Pi has spoken (SysEx 51 or 54). 0.17:
         * PERF first always (the journey always runs) */
        gr_set_view(shift ? GV_LFO : g_view == GV_PERF ? GV_SONG : g_view == GV_SONG ? GV_VIAGGIO :
                    g_view == GV_VIAGGIO ? (rg_active ? GV_REGIA : GV_PERF) :
                    g_view == GV_REGIA ? GV_PERF : GV_PERF);
    } else if (id == GC_VTRACK) {                                           /* TRACK again: TRACK 2, TRACK 3; BEAT again: EUCLID */
        if (shift) gr_set_view(g_view == GV_BEAT ? GV_EUCLID : GV_BEAT);
        else gr_set_view(g_view == GV_TRACK ? GV_TRACK2 : g_view == GV_TRACK2 ? GV_TRACK3 : GV_TRACK);
    } else if (id >= GC_TRK0 && id < GC_TRK0 + 8u) {
        if (shift) toggle_solo((uint8_t)(bank + id - GC_TRK0));
        else select_track((uint8_t)(bank + id - GC_TRK0));
    } else if (id >= GC_PAT0 && id < GC_PAT0 + 8u) {
        if (shift) gr_copy_pattern((uint8_t)(id - GC_PAT0));
        else queue_pattern(selected_track, (uint8_t)(id - GC_PAT0));
    } else if (id >= GC_SCN0) {                            /* the scenes of the cursor's bank (0.9: 1-8 or 9-16) */
        uint8_t sc = (uint8_t)((scene_cursor & 8u) + (id - GC_SCN0));
        if (shift) capture_scene(sc);
        else scene_recall(sc);
    }
}

static void gr_pad_step(uint8_t x, uint8_t y, uint8_t down)
{
    uint8_t t = selected_track;
    sq_track_cfg_t *cfg = &project.track[t];
    sq_step_t *row = gr_row(), *s;
    if (track_tape(t)) { if (down) tape_grid_pad(t, x, y); return; }   /* 0.11 */

    if (y < 4u) {                                       /* the 64 steps of the pattern */
        uint8_t stn = (uint8_t)(y * 16u + x);
        uint32_t bit = 1u << (stn & 31u), *dw = &g_down[stn >> 5];
        s = &row[stn];
        if (!down) {
            *dw &= ~bit;
            if (g_hold_pad == stn || (g_hold_pad == 254u && !g_down[0] && !g_down[1])) g_hold_pad = 255u;
            return;
        }
        *dw |= bit;
        if (gr_shift()) {                               /* SHIFT + step: the pattern ends here */
            set_length(t, (uint8_t)(stn + 1u));
            return;
        }
        if (g_hold_pad == 254u) {                       /* a pad still down from a loop gesture is not a new step */
            if ((uint32_t)(fm1_ms - g_loop_done) < GR_LOOPDONE_MS) return;
            g_hold_pad = 255u;
        }
        if (g_hold_pad < 64u && g_hold_pad != stn && (uint32_t)(fm1_ms - g_hold_since) >= SQ_LOOPHOLD_MS && !span_is_loop()) {
            note_span(t, g_hold_pad, stn, &g_hold_prev);   /* 0.11: the note between the two pads (FX tapped first: the loop) */
            g_hold_pad = 254u;
            g_hold_flip = 0u;
            g_loop_done = fm1_ms;
            return;
        }
        if (g_hold_pad < 64u && g_hold_pad != stn && (uint32_t)(fm1_ms - g_hold_since) >= SQ_LOOPHOLD_MS) {
            char *p = msg_buf;
            row[g_hold_pad] = g_hold_prev;              /* the first pad only selected the start */
            set_loop(t, g_hold_pad, stn);
            cursor_to(cfg->start);
            p = put_s(p, "LOOP "); p = put_u(p, (uint32_t)cfg->start + 1u);
            p = put_s(p, "-"); p = put_u(p, cfg->length); finish(p);
            status_msg(msg_buf);
            g_hold_pad = 254u;
            g_hold_flip = 0u;
            g_loop_done = fm1_ms;
            return;
        }
        cursor_to(stn);
        g_hold_pad = stn;
        g_hold_since = fm1_ms;
        g_hold_prev = *s;
        g_hold_flip = 1u;
        if (s->flags & SQ_STEP_ON) s->flags &= (uint8_t)~SQ_STEP_ON;
        else step_activate(t, s);
        return;
    }

    if (!down) return;
    s = &row[cursor_step];
    switch (y) {
    case 4:  s->velocity = x == 15u ? 127u : (uint8_t)(8u * (x + 1u)); break;
    case 5:
        if (gr_shift()) { if (x < SQ_COND_COUNT) { s->condition = x; status_msg(cond_name(x)); } else return; }   /* SHIFT: the condition */
        else s->chance = gr_pct16(x);
        break;
    case 6:
        if (gr_shift()) {                               /* 0.10 SHIFT: pad 15 PLAIN (no EXPO from here), pad 16 TIE (legato into the next step) */
            if (x == 15u) { s->flags ^= SQ_STEP_TIE; status_msg((s->flags & SQ_STEP_TIE) ? "TIE: THE NOTE HOLDS INTO THE NEXT STEP" : "TIE OFF"); }
            else if (x == 14u) { s->flags ^= SQ_STEP_XOFF; status_msg((s->flags & SQ_STEP_XOFF) ? "STEP PLAIN: NO EXPO FROM HERE" : "STEP IN THE CURVE"); }
            else return;
            s->flags |= SQ_STEP_SET;
            break;
        }
        if (x < 8u) s->ratchet = (uint8_t)(x + 1u); else s->length = GR_GATE[x - 8u];
        break;
    default: {                                          /* the note row; SHIFT adds / removes a chord note */
        uint8_t n = gr_pad_note(t, x), k, hit = 255u, slot = 255u;
        if (gr_shift()) {
            for (k = 0; k < SQ_POLY; k++) {
                if (s->note[k] == n) hit = k;
                if (s->note[k] == SQ_NOTE_NONE && slot == 255u) slot = k;
            }
            if (hit != 255u) {
                uint8_t live = 0u;
                for (k = 0; k < SQ_POLY; k++) if (s->note[k] != SQ_NOTE_NONE) live++;
                if (live > 1u) s->note[hit] = SQ_NOTE_NONE;
            } else s->note[slot != 255u ? slot : (SQ_POLY - 1u)] = n;
        } else {
            for (k = 0; k < SQ_POLY; k++) s->note[k] = SQ_NOTE_NONE;
            s->note[0] = n;
        }
        s->flags |= SQ_STEP_SET;
        PEN(t) = n;
        preview_note(t, n);
        status_note("NOTE ", n);
        break;
    }
    }
    /* 0.5: a note / velocity / gate of a parameter with a loop of its own is not a hit: the step stays as it is */
    if (!((y == 4u && cfg->plen[SQ_PL_VEL]) || (y == 6u && x >= 8u && cfg->plen[SQ_PL_GATE]) || (y == 7u && cfg->plen[SQ_PL_NOTE])))
        step_activate(t, s);
    ui_dirty = grid_dirty = 1u;
}

/* PERF: a row per track of the bank: mute, solo, patterns 1-8, RETRIG, KILL (held; SHIFT: latched), where it plays */
static void gr_pad_perf(uint8_t x, uint8_t y, uint8_t down)
{
    uint8_t t = (uint8_t)((selected_track & 8u) + y);
    uint16_t bit = (uint16_t)(1u << t);
    if (x == 11u) {                                     /* KILL, like the FX view's row 6 */
        if (!down) g_kill_held &= (uint16_t)~bit;
        else {
            if (gr_shift()) g_kill_latch ^= bit; else g_kill_held |= bit;
            track_all_off(t);
        }
        gr_fx_sync();
        return;
    }
    if (!down) return;
    if (x == 0u) toggle_mute(t);
    else if (x == 1u) toggle_solo(t);
    else if (x < 10u) queue_pattern(t, (uint8_t)(x - 2u));
    else if (x == 10u) track_retrig(t);
    else select_track(t);
    ui_dirty = grid_dirty = 1u;
}

static void gr_pad_track(uint8_t x, uint8_t y)
{
    uint8_t t = selected_track;
    sq_track_cfg_t *cfg = &project.track[t];
    sq_step_t *cs = &gr_row()[cursor_step];
    static const int8_t D[4] = {-12, -1, 1, 12};
    switch (y) {
    case 0: if (x == TOOL_UNDO && gr_shift()) undo_redo();                               /* 0.10: SHIFT + UNDO pad = REDO */
            else { if (x == TOOL_COOK && gr_shift()) cook_random = 1u; tool_apply(x); }   /* 0.11: SHIFT + COOK = the random COOK */
            break;
    case 1:
        if (x < SQ_CHORD_COUNT) chord_set(x, SQ_CHORD_OCTS(cfg->chord_mode));
        else chord_set(SQ_CHORD_MODE(cfg->chord_mode), (uint8_t)(x - 12u));
        break;
    case 2:
        if (x < 8u) set_swing(GR_SWING[x]);
        else if (x < 12u) set_direction((uint8_t)(x - 8u));
        else if (gr_shift()) { cfg->transpose = 0; status_msg("TRANSPOSE 0"); }
        else {
            cfg->transpose = (int8_t)clamp_i32((int32_t)cfg->transpose + D[x - 12u], -48, 48);
            { char *p = msg_buf; p = put_s(p, "TRANSPOSE "); p = put_i(p, cfg->transpose); finish(p); status_msg(msg_buf); }
        }
        break;
    case 3:
        if (x < SQ_DIV_COUNT) { set_division(t, x); status_msg(div_name(x)); }
        else if (x == 13u) {                                                       /* FREE, KEY, DRUM, BREAK (0.12; a TAPE: HOME 4 K1) */
            uint8_t m = track_mode(t);
            set_track_mode(t, (uint8_t)(m == 2u ? 4u : m >= 3u ? 0u : m + 1u));
            status_msg(track_mode_name(t));
        }
        break;
    case 4:
        if (gr_shift()) { set_loop_start(t, (uint8_t)(4u * x)); status_num("LOOP START ", (uint32_t)cfg->start + 1u); }
        else set_length(t, (uint8_t)(4u * (x + 1u)));
        break;
    case 5:
        if (x < 8u) { cfg->hum_time = GR_HUM[x]; status_num("HUMAN TIME ", cfg->hum_time); }
        else { cfg->hum_vel = GR_HUM[x - 8u]; status_num("HUMAN VEL ", cfg->hum_vel); }
        break;
    case 6:
        if (x < 15u) { cfg->vel_offset = GR_VOFF[x]; { char *p = msg_buf; p = put_s(p, "VEL "); p = put_i(p, cfg->vel_offset); finish(p); status_msg(msg_buf); } }
        break;
    default:
        if (x < 15u) {
            cs->nudge = GR_NUDGE[x];
            step_activate(t, cs);
            { char *p = msg_buf; p = put_s(p, "NUDGE "); p = put_i(p, cs->nudge); finish(p); status_msg(msg_buf); }
        }
        break;
    }
    ui_dirty = grid_dirty = 1u;
}

static void gr_pad_cc(uint8_t x, uint8_t y)
{
    uint8_t t = selected_track;
    sq_track_cfg_t *cfg = &project.track[t];
    sq_step_t *row = gr_row();
    switch (y) {
    case 0: case 1: case 2: case 3: {                   /* the bar chart: the value of the lane on that step */
        uint8_t stn = (uint8_t)(page * 16u + x), v = row[stn].lane[g_lane], top = 4u, k;
        if (v != SQ_LANE_NONE) for (k = 0; k < 4u; k++) if ((int32_t)v + 16 >= (int32_t)GR_CCLV[k]) { top = k; break; }
        if (v != SQ_LANE_NONE && top == y) row[stn].lane[g_lane] = SQ_LANE_NONE;      /* the same level again: the lock goes */
        else { row[stn].lane[g_lane] = GR_CCLV[y]; step_activate(t, &row[stn]); }
        cursor_to(stn);
        break;
    }
    case 4:
        if (x < SQ_LANES) { g_lane = x; status_num("LANE ", (uint32_t)x + 1u); }   /* 0.10: six lanes (pads 1-6), the pages on 9-12 */
        else if (x >= 8u && x < 12u) { page = (uint8_t)(x - 8u); cursor_step = (uint8_t)(page * 16u); }
        else if (x == 15u) {                            /* clear the lane in the whole pattern */
            uint32_t i;
            undo_begin();
            undo_add(t, tr[t].pattern);
            for (i = 0; i < SQ_STEPS; i++) row[i].lane[g_lane] = SQ_LANE_NONE;
            status_msg("LANE CLEARED");
        }
        break;
    case 5:
        if (gr_shift()) learn_arm(1u, t, g_lane);       /* SHIFT + a CC number: LEARN it from a knob of the synth */
        else { cfg->lane_cc[g_lane] = GR_CCP[x]; status_num("LANE CC ", GR_CCP[x]); }
        break;
    case 6: cfg->lane_base[g_lane] = gr_val16(x); status_num("LANE BASE ", cfg->lane_base[g_lane]); break;
    default:
        if (x == 0u) { cfg->lane_cc[g_lane] = SQ_LANE_NONE; status_msg("LANE OFF"); }
        else if (x == 1u) { cfg->lane_base[g_lane] = SQ_LANE_NONE; status_msg("NO BASE VALUE"); }
        break;
    }
    ui_dirty = grid_dirty = 1u;
}

static void gr_pad_lfo(uint8_t x, uint8_t y)
{
    sq_lfo_t *l = &project.lfo[lfo_sel];
    switch (y) {
    case 0:
        if (x == lfo_sel) { l->enabled ^= 1u; status_msg(l->enabled ? "LFO ON" : "LFO OFF"); }
        else { lfo_sel = x; status_num("LFO ", (uint32_t)x + 1u); }
        break;
    case 1:
        if (x < 8u) l->shape = x;
        else if (x < 8u + SQ_LD_KINDS) {
            l->dest = (uint8_t)(x - 8u);
            if (l->dest == SQ_LD_CC && l->target >= ch_limit()) l->target = (uint8_t)(ch_limit() - 1u);
            status_msg(lfo_dest_name(l->dest));
        } else if (x == 14u) { l->flags ^= SQ_LF_RETRIG; status_msg((l->flags & SQ_LF_RETRIG) ? "RETRIG ON" : "RETRIG OFF"); }
        else if (x == 15u) { l->flags ^= SQ_LF_INVERT; status_msg((l->flags & SQ_LF_INVERT) ? "INVERTED" : "NOT INVERTED"); }
        break;
    case 2: l->rate = x; status_msg(lfo_rate_name(x)); break;
    case 3: l->depth = gr_val16(x); status_num("DEPTH ", l->depth); break;
    case 4: l->center = gr_val16(x); status_num("CENTER ", l->center); break;
    case 5: l->phase = gr_val16(x); status_num("PHASE ", l->phase); break;
    case 6:
        if (l->dest == SQ_LD_CC) { if (x < ch_limit()) { l->target = x; status_num("CHANNEL ", (uint32_t)x + 1u); } }
        else { l->target = x; status_num("TRACK ", (uint32_t)x + 1u); }
        break;
    default:
        if (gr_shift()) learn_arm(2u, 0u, lfo_sel);     /* SHIFT + a CC number: LEARN */
        else { l->param = GR_CCP[x]; status_num("CC ", GR_CCP[x]); }
        break;
    }
    lfo_last_valid[lfo_sel] = 0u;
    ui_dirty = grid_dirty = 1u;
}

/* BEAT view: the library, the generators and the dice (0.8)
 *   row 0  genres 1-12 (13-24 with the page)   PAGE   LOAD (BEAT)   KIT   DICE ALL
 *   row 1  functions 1-9          scope THIS BANK ALL DRUMS MELODIC CUSTOM   WRITE LIVE
 *   row 2  the genre's progressions 1-6   HARMONY on / off   bars a chord   FOLLOW (this track)   -   variations 1-6
 *   row 3  dice SEQ CC LFO GROOVE ALL   KEEP BACK   -   targets 1-6 (RHYTHM .. ALL)   the roll before / after
 *   row 4  EUCLID pulses 1-16 of this track, live (CUSTOM scope: the tracks of the scope)   (SHIFT: the pattern chosen)
 *   row 5  EUCLID rotation 0-15 of this track
 *   row 6  random density (8)      COOK heat (8)
 *   row 7  EVOLVE  FREEZE  REVERT  DRIFT   every 1 2 4 8 16 bars   amount (7) */
static void gr_pad_beat(uint8_t x, uint8_t y)
{
    sq_track_cfg_t *cfg = &project.track[selected_track];
    switch (y) {
    case 0:
        if (x < 12u) { uint8_t g = (uint8_t)(g_genre_page * 12u + x); if (g < SQ_GENRES) gen_genre_set(g); }
        else if (x == 12u) { g_genre_page = (uint8_t)((g_genre_page + 1u) % ((SQ_GENRES + 11u) / 12u)); status_num("GENRES PAGE ", (uint32_t)g_genre_page + 1u); }
        else if (x == 13u) tool_apply(TOOL_BEAT);
        else if (x == 14u) { if (gr_shift()) beat_band(); else beat_kit(); }   /* 0.10: SHIFT: BAND */
        else dice_roll(DICE_ALL);
        break;
    case 1:
        if (x < 9u) {                                     /* 0.11: the genre's parts, PROG, KIT; more than 9: pages of 8, pad 9 the next page */
            uint8_t l[SQ_PARTS_MAX + 2u], n = beat_list(l), paged = n > 9u ? 1u : 0u, i;
            if (paged && x == 8u) { g_part_page = (uint8_t)((g_part_page + 1u) % ((n + 7u) / 8u)); status_num("PARTS PAGE ", (uint32_t)g_part_page + 1u); }
            else { i = (uint8_t)(paged ? g_part_page * 8u + x : x); if (i < n) gen_func_set(l[i]); }
        }
        else if (x < 9u + SQ_SCOPES) gen_scope_set((uint8_t)(x - 9u));
        else live_write();
        break;
    case 2:
        if (x < SQ_PROGS) harm_prog_set(x);
        else if (x == 6u) harm_toggle();
        else if (x == 7u) harm_bars_turn(1);
        else if (x == 8u) follow_set(selected_track, (cfg->flags & SQ_TF_FOLLOW) ? 0u : 1u);
        else if (x == 9u) { g_var_page ^= 1u; status_msg(g_var_page ? "VARIATIONS 7-12" : "VARIATIONS 1-6"); }   /* 0.11 */
        else if (x >= 10u) {
            uint8_t v = (uint8_t)(g_var_page * 6u + x - 10u), nv = sq_beat_variants(beat_genre, beat_func);
            if (v < nv) { beat_var = v; status_num("VARIATION ", (uint32_t)v + 1u); }
        }
        break;
    case 3:
        if (x < 5u) dice_roll((uint8_t)(DICE_SEQ + x));
        else if (x == 5u) { if (dice_pending) dice_answer(1u); else status_msg("NO DICE TO KEEP"); }
        else if (x == 6u) { if (dice_pending) dice_answer(0u); else status_msg("NO DICE TO PUT BACK"); }
        else if (x >= 8u && x < 8u + GEN_TARGET_SETS) gen_targets_set((uint8_t)(x - 8u));
        else if (x == 14u || x == 15u) { if (dice_pending) dice_browse(x == 14u ? -1 : 1); else status_msg("NO DICE ROLLED"); }
        break;
    case 4:
        if (project.gen.scope == SQ_SCOPE_CUSTOM) gen_custom_toggle(x);
        else { cfg->euc_pulses = (uint8_t)(x + 1u); euclid_touch(selected_track); }
        break;
    case 5: cfg->euc_rot = x; euclid_touch(selected_track); break;
    case 6:
        if (x < 8u) { tool_density = GR_DENS[x]; status_num("RND DENSITY ", tool_density); }
        else { tool_heat = GR_HEAT[x - 8u]; status_num("HEAT ", tool_heat); }
        break;
    default:
        if (x == 0u) evo_toggle();
        else if (x == 1u) evo_freeze();
        else if (x == 2u) evo_revert();
        else if (x == 3u) evo_drift_toggle();
        else if (x < 4u + SQ_EVO_EVERY) { project.gen.evo_every = (uint8_t)(x - 4u); evo_status(); }
        else { project.gen.evo_amount = GR_EVOAMT[x - 9u]; evo_status(); }
        break;
    }
    ui_dirty = grid_dirty = 1u;
}

/* EUCLID view (0.8): the eight tracks of the bank, a row each. Pad 1: EUCLID LIVE on / off; pads 2-16: pulses 1-15 (heard
 * at once if the row's EUCLID LIVE is on; 0.16: off, set up for pad 1 to start it); SHIFT + pads 2-16: the rotation 0-14.
 * The pads show the pulses (the rotation with SHIFT). */
static void gr_pad_euclid(uint8_t x, uint8_t y)
{
    uint8_t t = (uint8_t)((selected_track & 8u) + y);
    sq_track_cfg_t *c = &project.track[t];
    if (x == 0u) {
        c->flags ^= SQ_TF_EUC;
        euclid_status(t);
    } else if (gr_shift()) { c->euc_rot = (uint8_t)(x - 1u); euclid_touch(t); }
    else { c->euc_pulses = x; euclid_touch(t); }
    ui_dirty = grid_dirty = 1u;
}

/* TRACK 3 (0.8): the selected track's newer parameters
 *   row 0  voicing CLOSE INV1 INV2 DROP2 OPEN    strum -50 .. 0 .. +50 % (pads 6-16)
 *   row 1  MIDI FX OFF HARM OCTAVE ECHO VEL (0.16: a tap READY, again: it starts)   amount -5 .. 0 .. +5 (pads 6-16;
 *          HARM in key: steps, free: semitones)
 *   row 2  ECHO time 1/32 .. 1/4 (OCTAVE: ALT RANDOM 3RD 4TH)   ECHO keeps / HARM velocity 20 .. 100 %
 *   row 3  algorithm OFF TURING CELL ACCENT DENSITY (0.16: a tap READY, orange; again: it starts, white; on the one
 *          playing: it stops)   FOLLOW   EUCLID LIVE   the slot   C: TURING moves (rhythm, notes, both),
 *          CELL a new row every (1 2 4 bars, loop), ACCENT starts (0-7)
 *   row 4  A: TURING mutation, CELL rule, ACCENT style, DENSITY (16 levels)
 *   row 5  B: TURING length 2-16, CELL cells, ACCENT amount, DENSITY ghosts' velocity
 *   row 6  the cursor step's long gate: 1.5, 2 .. 6, 8 .. 16, 20 .. 64 steps (SHIFT: 17 .. 32 one by one)
 *   row 7  the MIDI channel 1-16 (15 and 16 with two USB ports) */
static void gr_pad_track3(uint8_t x, uint8_t y)
{
    uint8_t t = selected_track;
    sq_track_cfg_t *c = &project.track[t];
    switch (y) {
    case 0:
        if (x < SQ_VOICES) { static const char *const VN[SQ_VOICES] = {"CLOSE", "INV 1", "INV 2", "DROP 2", "OPEN"}; c->voicing = x; status_msg(VN[x]); }
        else if (x >= 5u) { c->strum = (int8_t)(((int32_t)x - 10) * 10); { char *p = msg_buf; p = put_s(p, "STRUM "); p = put_i(p, c->strum); p = put_s(p, "%"); finish(p); status_msg(msg_buf); } }
        break;
    case 1:
        if (x < SQ_MFXS) mfx_pad(t, x);                 /* 0.16: a tap READY (orange), again: it starts; 0.19: on one that plays: it stops */
        else if (x >= 5u) {
            sq_track_cfg_t *v = mfx_view(t);
            mfx_amount(v, ((int32_t)x - 10) - v->mfx_amt);
            if (v == &mfx_tmp) mfx_keep(t, v);
            { char *p = msg_buf; p = put_s(p, "FX AMOUNT "); p = put_i(p, v->mfx_amt); finish(p); status_msg(msg_buf); }
        }
        break;
    case 2: {
        sq_track_cfg_t *v = mfx_view(t);
        if (x < 8u) {
            if (v->mfx == SQ_MFX_OCTAVE) { if (x < SQ_OCT_PATTERNS) v->mfx_time = x; }
            else v->mfx_time = x;
            status_num("FX TIME ", (uint32_t)x + 1u);
        } else { v->mfx_fb = GR_KEEP[x - 8u]; status_num("FX KEEPS ", v->mfx_fb); }
        if (v == &mfx_tmp) mfx_keep(t, v);
        break;
    }
    case 3: {
        sq_algo_t *al = algo_edit(t);                   /* 0.11: the slot shown; pad 8 goes to the next slot; 0.16: the READY one */
        if (x < SQ_ALGOS) algo_pad(t, x);               /* 0.16: a tap READY, again: it starts (on the one playing: it stops) */
        else if (x == 5u) follow_set(t, (c->flags & SQ_TF_FOLLOW) ? 0u : 1u);
        else if (x == 6u) { c->flags ^= SQ_TF_EUC; euclid_status(t); }
        else if (x == 7u) algo_slot_select(t, (uint8_t)((algo_cur[t] + 1u) % SQ_ALGO_SLOTS));
        else if (x >= 8u) {
            uint8_t v = (uint8_t)(x - 8u);
            if (al->algo == SQ_ALGO_TURING && v < SQ_TM_MODES) al->c = v;
            else if (al->algo == SQ_ALGO_CELL && v < 4u) { al->c = v; if (al == algo_slot(t)) ca_bars[t][algo_k(t)] = 0u; }
            else if (al->algo == SQ_ALGO_ACCENT) al->c = v;
            algo_status(t);
        }
        break;
    }
    case 4: {
        sq_algo_t *al = algo_edit(t);
        if (al->algo == SQ_ALGO_TURING) al->a = GR_MUT[x];
        else if (al->algo == SQ_ALGO_CELL) al->a = GR_RULE[x];
        else if (al->algo == SQ_ALGO_ACCENT) { if (x < 5u) al->a = x; }
        else if (al->algo == SQ_ALGO_DENSITY) al->a = GR_DENSA[x];
        algo_status(t);
        break;
    }
    case 5: {
        sq_algo_t *al = algo_edit(t);
        if (al->algo == SQ_ALGO_TURING) { if (x < 15u) al->b = (uint8_t)(x + 2u); }
        else if (al->algo == SQ_ALGO_CELL) al->b = GR_CELLS[x];
        else if (al->algo == SQ_ALGO_ACCENT) al->b = (uint8_t)(x * 4u + 3u);
        else if (al->algo == SQ_ALGO_DENSITY) al->b = (uint8_t)(10u + x * 6u);
        algo_status(t);
        break;
    }
    case 6: {
        sq_step_t *cs = &gr_row()[cursor_step];
        cs->length = gr_shift() ? (uint8_t)(117u + x) : GR_LONG[x];
        step_activate(t, cs);
        status_msg(f_gate(cs->length));
        break;
    }
    default:
        if (x < ch_limit()) { c->channel = x; status_num("CHANNEL ", (uint32_t)x + 1u); }
        else status_msg("CHANNELS 15-16: TWO USB PORTS (USB PAGE)");
        break;
    }
    ui_dirty = grid_dirty = 1u;
}

/* DRUM view: the eight tracks of the bank, one per row, sixteen steps each (the page; a track of 16 steps always shows
 * them). Tap: the step on / off. Held: that track and that step are selected (the step is put back as it was).
 * SHIFT + pad 1-4: the page; SHIFT + another pad: select the track of that row. */
static uint8_t gr_drum_step(uint32_t t, uint32_t x)
{
    uint32_t pages = ((uint32_t)project.track[t].length + 15u) / 16u;
    if (!pages) pages = 1u;
    return (uint8_t)((page % pages) * 16u + x);
}

static void gr_pad_drum(uint8_t x, uint8_t y, uint8_t down)
{
    uint8_t t = (uint8_t)((selected_track & 8u) + y), stn = gr_drum_step(t, x), id = (uint8_t)(y * 16u + x);
    sq_step_t *s = &project.step[t][tr[t].pattern][stn];
    if (!down) { if (g_drum_hold == id) g_drum_hold = 255u; return; }
    if (gr_shift()) {
        if (x < 4u) { page = x; cursor_step = (uint8_t)(page * 16u); status_num("PAGE ", (uint32_t)x + 1u); }
        else { select_track(t); status_msg(track_mode_name(t)); }
        ui_dirty = grid_dirty = 1u;
        return;
    }
    g_drum_hold = id;
    g_drum_since = fm1_ms;
    g_drum_prev = *s;
    if (s->flags & SQ_STEP_ON) s->flags &= (uint8_t)~SQ_STEP_ON;
    else step_activate(t, s);
    ui_dirty = grid_dirty = 1u;
}

static void gr_drum_service(void)              /* a DRUM pad held long enough selects its track and step */
{
    uint8_t x, y, t, stn;
    if (g_drum_hold >= 128u || (uint32_t)(fm1_ms - g_drum_since) < SQ_HOLD_MS) return;
    x = g_drum_hold & 15u; y = g_drum_hold >> 4;
    t = (uint8_t)((selected_track & 8u) + y);
    stn = gr_drum_step(t, x);
    project.step[t][tr[t].pattern][stn] = g_drum_prev;
    if (t != selected_track) select_track(t);
    cursor_to(stn);
    status_num("STEP ", (uint32_t)stn + 1u);
    g_drum_hold = 254u;                         /* (done: the pad-up has nothing to do) */
    ui_dirty = grid_dirty = 1u;
}

/* SONG view
 *   row 0  the 16 entries (tap: edit it; SHIFT: the song jumps there)
 *   row 1  scenes 1-8 for the entry (on the free entry after the last: a new one)
 *   row 2  its bars: 1 2 3 4 5 6 7 8 10 12 16 20 24 32 48 64
 *   row 3  SONG on / off, LOOP, INSERT (a copy after it), DELETE ... SHIFT + last pad: CLEAR
 *   rows 4-7  the song bar by bar (64 bars); tap: the song jumps to that bar's entry */
static uint8_t gr_song_entry_at(uint32_t bar)   /* the entry playing at bar `bar` of the song, or 255 */
{
    uint32_t i, b = 0u;
    for (i = 0; i < project.song.len; i++) { b += project.song.e[i].bars; if (bar < b) return (uint8_t)i; }
    return 255u;
}

static void gr_pad_song(uint8_t x, uint8_t y)
{
    sq_song_t *sg = &project.song;
    if (g_song_sel > sg->len) g_song_sel = sg->len;
    switch (y) {
    case 0: {                                             /* (0.9: 64 entries, 16 a page: the page of the one chosen) */
        uint8_t e = (uint8_t)((g_song_sel & ~15u) + x);
        if (e > sg->len || e >= SQ_SONG_LEN) break;
        if (gr_shift() && e < sg->len) { if (song_on) { song_wait = 0u; song_play_entry(e); song_status(); } else status_msg("SONG IS OFF"); }
        else { g_song_sel = e; status_num("SONG ENTRY ", (uint32_t)e + 1u); }
        break;
    }
    case 1:
        if (x >= SQ_SCENES) break;
        if (g_song_sel >= sg->len) { song_append(x); g_song_sel = (uint8_t)(sg->len - 1u); }
        else { sg->e[g_song_sel].scene = x; status_num("ENTRY SCENE ", (uint32_t)x + 1u); }
        break;
    case 2: song_set_bars(g_song_sel, GR_BARS[x]); break;
    case 3:
        if (x == 0u) song_toggle();
        else if (x == 1u) song_loop_toggle();
        else if (x == 2u) song_insert(g_song_sel);
        else if (x == 3u) song_delete(g_song_sel);
        else if (x == 12u || x == 13u) {                  /* the page of entries: 1-16, 17-32, 33-48, 49-64 */
            int32_t base = (int32_t)(g_song_sel & ~15u) + (x == 12u ? -16 : 16);
            if (base < 0 || base > (int32_t)sg->len || base >= (int32_t)SQ_SONG_LEN) break;
            g_song_sel = (uint8_t)base;
            status_num("SONG ENTRIES FROM ", (uint32_t)base + 1u);
        }
        else if (x == 15u && gr_shift()) { song_clear(); g_song_sel = 0u; }
        break;
    default: {
        uint8_t e = gr_song_entry_at((uint32_t)(y - 4u) * 16u + x);
        if (e == 255u) break;
        g_song_sel = e;
        if (song_on) { song_wait = 0u; song_play_entry(e); song_status(); }
        else status_num("SONG ENTRY ", (uint32_t)e + 1u);
        break;
    }
    }
    ui_dirty = grid_dirty = 1u;
}

/* FX view (0.5.1)
 *   row 1  the 16 effects while held (SHIFT: latched)
 *   row 2  LOOP / REPEAT: 1/32 1/16 1/8 1/4 1/2 1 2 4 bars (1-8), 1/32T 1/16T 1/8T 1/4T (9-12), ECHO all (14), EXIT (16).
 *          A tap: the LOOP stays (the same pad again: off). Held: REPEAT, let go and it lands in time.
 *   row 3  TRANSPOSE the key -7 .. +8 (pad 8 = 0), at the QUANTISE moment
 *   row 4  the tracks LOOP / REPEAT take          row 5  MORPH from the scene playing (1) to MORPH TO (16)
 *   row 6  KILL track 1-16 while held (SHIFT: latched)
 *   row 7  MORPH TO scene 1-8, QUANTISE AUTO NOW BEAT BAR 2 4 8 BARS (9-15), MUTE QUEUE (16)
 *   row 8  TEMP (held; SHIFT: latched), RELOAD, RESTART, STOP at the end of the bar, SNAPSHOTS 1-8 (5-12; SHIFT: store),
 *          CC CAPTURE (13), SEND (14), PATCHES (15), PANIC (16) */
static const uint16_t GR_LOOP_T[4] = {2u, 4u, 8u, 16u};          /* the triplet lengths of row 2 */
static uint16_t gr_loop_ticks(uint8_t x) { return x < 8u ? LOOP_TICKS[x] : x < 12u ? GR_LOOP_T[x - 8u] : 0u; }

static void gr_pad_fx(uint8_t x, uint8_t y, uint8_t down)
{
    uint16_t bit = (uint16_t)(1u << x);
    if (y == 0u) {
        if (!down) g_fx_held &= (uint16_t)~bit;
        else if (gr_shift()) g_fx_latch ^= bit;
        else g_fx_held |= bit;
        gr_fx_sync();
        return;
    }
    if (y == 5u) {
        if (!down) g_kill_held &= (uint16_t)~bit;
        else {
            if (gr_shift()) g_kill_latch ^= bit; else g_kill_held |= bit;
            track_all_off(x);                           /* the notes of that track stop now */
        }
        gr_fx_sync();
        return;
    }
    if (y == 1u) {                                      /* LOOP (tap) / REPEAT (hold), the tracks of row 4 */
        uint16_t ticks = gr_loop_ticks(x);
        if (x == 15u) { if (down) loop_exit(); return; }
        if (x == 13u) {                                 /* 0.8: the global ECHO */
            if (down) { echo_global ^= 1u; status_msg(echo_global ? "ECHO: EVERY TRACK, A DOTTED EIGHTH" : "ECHO OFF"); ui_dirty = grid_dirty = 1u; }
            return;
        }
        if (!ticks) return;
        if (down) loop_press(ticks, (uint8_t)(LP_GRID + x), g_loop_mask ? g_loop_mask : 0xFFFFu);
        else loop_release((uint8_t)(LP_GRID + x));
        return;
    }
    if (y == 7u && x == 0u) {                           /* TEMP: what changes while it is held goes back (SHIFT: latch) */
        if (down) {
            if (gr_shift()) { if (temp_on) { g_temp_held = 0u; temp_end(); } else temp_begin(); }
            else if (!temp_on) { temp_begin(); g_temp_held = 1u; }
        } else if (g_temp_held) { g_temp_held = 0u; temp_end(); }
        ui_dirty = grid_dirty = 1u;
        return;
    }
    if (!down) return;
    if (y == 2u) {
        ktrans_set((int32_t)x - 7);                     /* TRANSPOSE: pad 8 is 0 */
    } else if (y == 3u) {
        g_loop_mask ^= bit;
    } else if (y == 4u) {                               /* MORPH, from the scene playing (pad 1) to the target (16) */
        morph_set((uint8_t)((x * 127u + 7u) / 15u));
    } else if (y == 6u) {
        if (x < 8u) morph_target(x);                    /* MORPH to scene 1-8 */
        else if (x < 15u) quant_set((uint8_t)(x - 8u)); /* QUANTISE: AUTO NOW BEAT BAR 2 4 8 BARS */
        else mute_q_toggle();                           /* MUTE QUEUE */
    } else if (y == 7u) {
        if (x == 1u) reload_request();                  /* RELOAD the patterns playing on the scope */
        else if (x == 2u) restart_all();
        else if (x == 3u) stop_bar_toggle();
        else if (x >= 4u && x < 12u) { if (gr_shift()) snap_store((uint8_t)(x - 4u)); else snap_recall((uint8_t)(x - 4u)); }   /* 0.8 */
        else if (x == 12u) snap_capture_toggle();
        else if (x == 13u) snap_send();
        else if (x == 14u) snap_patches();
        else if (x == 15u) { panic_all_x(1u); status_msg("PANIC"); }
    }
    ui_dirty = grid_dirty = 1u;
}

static void gr_jump(uint8_t bar)                        /* a bar of the song: the tracks go there (SPP goes out if we are the master) */
{
    uint32_t ticks = (uint32_t)bar * 96u, beats = ticks / 6u;
    loop_on = 0u; loop_latched = 0u; lp_held = 0u;
    seek_ticks(ticks);
    song_seek(ticks);                                   /* 0.5: the song follows */
    if (project.clock_mode == SQ_CLOCK_MASTER) midi_send(0xF2u, beats & 127u, (beats >> 7) & 127u);
    status_num("BAR ", (uint32_t)bar + 1u);
}

static void gr_pad_proj(uint8_t x, uint8_t y)
{
    uint32_t i;
    switch (y) {
    case 0: if (x < 12u) { project.key_root = x; key_toast(); } break;
    case 1: project.key_scale = x; key_toast(); break;
    case 2: if (x < 15u) { project.key_shift = GR_SHIFT[x]; key_toast(); } break;
    case 3:                                             /* the mode of track x: FREE, IN KEY, DRUM */
        set_track_mode(x, (uint8_t)((track_mode(x) + 1u) % 3u));
        { char *p = msg_buf; p = put_s(p, "T"); p = put_u(p, (uint32_t)x + 1u); p = put_s(p, " "); p = put_s(p, track_mode_name(x)); finish(p); status_msg(msg_buf); }
        break;
    case 4:
        if (x < SQ_MKS) master_fn_set(x);              /* the MASTER knob: TEMPO, MORPH, FILTER */
        else if (x == 4u) {                             /* the remote: OFF, CH 14, 13 + 14 (0.9: as SAVE + K2) */
            project.live.remote_mode = (uint8_t)((project.live.remote_mode + 1u) % SQ_RMS);
            project.live.remote_ch = project.live.remote_mode == SQ_RM_OFF ? (uint8_t)SQ_REMOTE_OFF : 13u;
            status_msg(project.live.remote_mode == SQ_RM_OFF ? "REMOTE OFF: CH 13 AND 14 ARE TRACK CHANNELS" :
                       project.live.remote_mode == SQ_RM_14 ? "REMOTE ON CH 14" : "REMOTE ON CH 14 + VIAGGIO ON CH 13");
        }
        else if (x == 13u) key_bake();
        else if (x == 14u) {                            /* every track but the drum tracks follows the key */
            for (i = 0; i < SQ_TRACKS; i++) if (!track_drum(i)) project.track[i].flags |= SQ_TF_SCALE;
            status_msg("ALL BUT DRUMS FOLLOW THE KEY");
        } else if (x == 15u) {
            for (i = 0; i < SQ_TRACKS; i++) project.track[i].flags &= (uint8_t)~SQ_TF_SCALE;
            status_msg("NO TRACK FOLLOWS THE KEY");
        }
        break;
    case 5:
        if (x < SQ_SLOTS) { slot_pick(x); status_num("SLOT ", (uint32_t)x + 1u); }
        else if (x == 8u) store_tap_save();
        else if (x == 9u) store_tap_load();
        else if (x == 11u) sx_export(-1);               /* the project to the Pi (the bridge saves it to a file) */
        break;
    case 6:
        if (x == 0u) set_bpm(-10);
        else if (x == 1u) set_bpm(-1);
        else if (x == 2u) set_bpm(1);
        else if (x == 3u) set_bpm(10);
        else if (x == 4u) tap_tempo();
        else if (x == 5u) { rec_quant ^= 1u; status_msg(rec_quant ? "REC QUANTISED" : "REC FREE (KEEPS TIMING)"); }
        else if (x == 6u) {
            if (playing) transport_stop();
            project.clock_mode ^= 1u;
            knob_live = 0u; knob_ref = fm1_knob;
            status_msg(project.clock_mode == SQ_CLOCK_MASTER ? "CLOCK MASTER" : "CLOCK SLAVE (EXT)");
        } else if (x == 8u) { mute_mask = 0u; solo_mask = 0u; pending_mute = 0u; status_msg("ALL TRACKS AUDIBLE"); }
        break;
    default: gr_jump(x); break;
    }
    ui_dirty = grid_dirty = 1u;
}

/* TRACK 2 (0.5): the loops of the notes, velocities, gates (rows 1-3: 1-16 steps, SHIFT 17-32; the length it has
 * again: back to the track's loop), the Program Change of the track's channel in a scene (row 4: 1-16, SHIFT 17-32;
 * again: none), the scene it is for (row 5: 1-8; 16 sends that scene's programs now), the three loops playing (6-8) */
static void gr_pad_track2(uint8_t x, uint8_t y)
{
    uint8_t t = selected_track, v = (uint8_t)(x + 1u + (gr_shift() ? 16u : 0u)), ch = track_ch(t);
    sq_track_cfg_t *cfg = &project.track[t];
    static const char *const PL[SQ_PLANES] = {"NOTE LOOP ", "VELOCITY LOOP ", "GATE LOOP "};
    if (y < SQ_PLANES) {
        cfg->plen[y] = cfg->plen[y] == v ? 0u : v;
        if (cfg->plen[y]) status_num(PL[y], cfg->plen[y]);
        else { char *p = msg_buf; p = put_s(p, PL[y]); p = put_s(p, "= THE TRACK'S"); finish(p); status_msg(msg_buf); }
    } else if (y == 3u) {
        uint8_t pc = (uint8_t)(v - 1u);
        scene_pc_set(g_pc_scene, ch, project.scene[g_pc_scene].pc[ch] == pc ? -1 : (int32_t)pc);
    } else if (y == 4u) {
        if (x < SQ_SCENES) { g_pc_scene = x; status_num("PROGRAMS OF SCENE ", (uint32_t)x + 1u); }
        else if (x == 15u) {
            memset(pc_last, 255, sizeof pc_last);       /* (sent again even where it is) */
            scene_send_pc(g_pc_scene);
            status_num("PROGRAMS SENT, SCENE ", (uint32_t)g_pc_scene + 1u);
        }
    }
    ui_dirty = grid_dirty = 1u;
}

/* LIB (0.5): the files on the Raspberry Pi. Rows 1-4: 64 files (tap: choose it; tap again: LOAD, while playing it loads at
 * STOP). Row 8: PREVIOUS, NEXT (the setlist: load the file before / after the one loaded), REFRESH (4), SAVE AS A NEW FILE
 * (8), SAVE OVER the chosen file (9, twice), LOAD the chosen file (16). */
static void gr_pad_lib(uint8_t x, uint8_t y)
{
    if (y < 4u) {
        uint8_t i = (uint8_t)(y * 16u + x);
        if (i >= lib_n) return;
        if (i == g_lib_armed) lib_load(i);
        else { lib_sel = i; g_lib_armed = i; lib_ask_over = 0u; lib_toast("FILE ", i); }
    } else if (y == 7u) {
        switch (x) {
        case 0u:  lib_next(-1); break;
        case 1u:  lib_next(1); break;
        case 3u:  lib_ask_list(); break;
        case 7u:  lib_save(-1); break;
        case 8u:  lib_save(lib_sel); break;
        case 15u: lib_load(lib_sel); break;
        default:  break;
        }
    }
    ui_dirty = grid_dirty = 1u;
}

/* ---- 0.9 the VIAGGIO view: a row for everything that counts in the set (docs/SAGGA-GRID.md)
 *   1 the bars of the phrase (tap: NOW)       2 the tracks: EMPTY / PROPOSED / IN / OUT (tap: tira / open, hold: dice, SHIFT: the role)
 *   3 the queue per track (tap: in / out)     4 the moves (FILL BREAK RISER DROP HALF DOUBLE THIN SWELL SWAP LOOP NOW, 15 cancel)
 *   5 the energy (tap: the target)            6 the proposals of the selected track (tap: SWAP / IN; pad 16: the dice)
 *   7 the progression (tap: in the queue)     8 the trail (tap: INDIETRO up to there) */
static void gr_pad_viaggio(uint8_t x, uint8_t y, uint8_t down)
{
    if (y == 1u) {                                        /* a track: tap now, the dice if it is held; SHIFT: its role (0.10) */
        if (down && gr_shift()) {
            sq_track_cfg_t *c = &project.track[x];
            char *p = msg_buf;
            c->role = (uint8_t)((c->role + 1u) % SQ_ROLE_COUNT);
            select_track(x);
            p = put_s(p, "T"); p = put_u(p, (uint32_t)x + 1u); p = put_s(p, " ROLE "); p = put_s(p, sq_role_name(c->role)); finish(p); status_msg(msg_buf);
            ui_dirty = grid_dirty = 1u;
            return;
        }
        if (down) { g_vg_hold = x; g_vg_hold_ms = fm1_ms; vg_track_tap(x); }
        else if (g_vg_hold == x) g_vg_hold = 255u;
        return;
    }
    if (!down) return;
    switch (y) {
    case 0u: vg_now_tap(); break;
    case 2u: vg_track_queue(x); break;
    case 3u:
        if (x < 11u) vg_black(x, gr_shift());
        else if (x == 14u) vg_back();
        else if (x == 15u) vg_cancel_last();
        break;
    case 4u: vg_energy_set((uint8_t)((x * 100u + 7u) / 15u)); status_num("ENERGY ", project.viaggio.energy); break;
    case 5u:
        if (x < SQ_PATTERNS) {
            uint8_t t = selected_track;
            if (x == tr[t].pattern) { status_msg("THAT ONE PLAYS"); break; }
            if (pattern_empty(t, x)) { status_msg("EMPTY: TAP THE TRACK FOR A PROPOSAL"); break; }
            vg_prop[t] = x;                                   /* (0.10: the slot keeps its settings) */
            if (vg_track_in(t)) { if (!vg_queue(SQ_MV_SWAP, t, x)) vg_msg_t("QUEUED: SWAP ", t, ""); }
            else if (!vg_queue(SQ_MV_IN, t, x)) vg_msg_t("QUEUED: ", t, " IN");
        } else if (x == 15u) vg_tira(selected_track, 1u);
        break;
    case 6u:
        if (x < SQ_PROGS_ALL) { int q = sq_queue_find(&vg_q, SQ_MV_PROG, 0u); vg_prog_turn((int32_t)x - (int32_t)(q >= 0 ? vg_q.m[q].a : project.gen.harm_prog)); }
        break;
    case 7u: {
        uint32_t back = 15u - x;                          /* pad 16 = the phrase playing, 15 = one back ... */
        if (!back) { status_msg("THIS PHRASE"); break; }
        if (back > vg_trail.n) { status_msg("THE TRAIL IS SHORTER"); break; }
        if (!vg_queue(SQ_MV_BACK, (uint8_t)back, 0u)) { char *p = msg_buf; p = put_s(p, "QUEUED: BACK "); p = put_u(p, back); finish(p); status_msg(msg_buf); }
        break;
    }
    default: break;
    }
    ui_dirty = grid_dirty = 1u;
}
static void gr_vg_service(void)                          /* a track pad held: the dice */
{
    if (g_vg_hold < SQ_TRACKS && (uint32_t)(fm1_ms - g_vg_hold_ms) >= VG_HOLD_MS) { vg_tira(g_vg_hold, 1u); g_vg_hold = 255u; }
}

/* ---- 0.9 the REGIA view: the Pi's rules (SysEx 54 REGIA LED): row 1 the 16 rules, tap = on / off (SysEx 55) */
static uint8_t g_regia_led[16];                          /* 0 off, 1 on, 2 passing (what the Pi said last) */
static void regia_key_send(uint8_t rule);                /* sagga_store.c */
static void gr_pad_regia(uint8_t x, uint8_t y, uint8_t down)
{
    if (!down || y) return;
    regia_key_send(x);
    g_regia_led[x] = g_regia_led[x] ? 0u : 1u;             /* shown at once; the Pi confirms */
    status_num("REGIA RULE ", (uint32_t)x + 1u);
    grid_dirty = 1u;
}

/* 0.12 PICK view, 0.18 FOLLOW: the four knobs of the page open on the FM-1 (a group held or its window, else PERF's,
 * else HOME's), a knob a row: pads 1-16 of rows 1-4 are the white keys of PICK (items 1-16, lengths 4..64, the notes
 * ...); the pad of the value now is white. A knob the keys cannot set: a faint row. Rows 5-8, 0.18: the same knobs
 * across the sixteen tracks when they are a track's (the FM-1's track white, the tracks with its value lit, the others
 * faint; a tap: that track gets the value, SHIFT + a tap: the FM-1 goes to that track); a knob that is no track's has
 * the values of the black keys there, as PICK had (items 17-26, the odd lengths). */
static int gr_pick_group(void)
{
    int g = pick_group(eff_held());
    return g >= 0 ? g : perf_mode ? PG_GLO : PG_HOME;
}
/* which knobs of a page are a track's (bit k = knob k): HOME, GLO, SEQ, ARP, EDIT, ENV (a page a lane), LFO */
static const uint8_t GR_PT[PG_COUNT][PICK_PAGES] = {
    {0xEu, 0xFu, 0x0u, 0xFu, 0x7u, 0xFu, 0xFu, 0x0u},          /* HOME (not the channel, nor a scene's PROGRAM: a synth's; 2: the key; 7: CHAIN LIST's places) */
    {0x0u, 0x3u, 0x0u},                                         /* PERF: page 2's PATTERN and LENGTH */
    {0x7u, 0x0u, 0x0u, 0xFu, 0xFu, 0x0u, 0xFu, 0xFu},          /* SEQ: EUCLID (not HEAT), EXPO, the BREAK */
    {0xFu, 0xFu, 0x8u, 0x1u, 0x0u, 0x0u},                       /* ARP: the arp, the chord, FOLLOW, its way */
    {0x0u},                                                     /* EDIT: a step's notes */
    {0xAu, 0xAu, 0xAu, 0xAu, 0xAu, 0xAu},                       /* ENV: the lane's CC and its mode */
    {0x0u},                                                     /* LFO */
};
static uint8_t gr_pt(int g, uint32_t k)
{
    uint8_t pg = pick_page(g);
    return (g >= 0 && g < PG_COUNT && pg < PICK_PAGES && ((GR_PT[g][pg] >> k) & 1u)) ? 1u : 0u;
}
static void gr_desc_of(int g, uint32_t k, uint8_t t, pick_t *d)   /* knob k as track t has it */
{
    uint8_t keep = selected_track;
    selected_track = t;
    pick_desc(g, k, d);
    selected_track = keep;
}
/* track t gets the value the FM-1's track has on knob k (through the knob, as a turn would) */
static void gr_follow_copy(int g, uint32_t k, uint8_t t)
{
    pick_t me, it;
    uint8_t keep = selected_track;
    int32_t dd[4] = {0, 0, 0, 0};
    char *p;
    pick_desc(g, k, &me);
    gr_desc_of(g, k, t, &it);
    if (t != keep && it.cur != me.cur) {
        selected_track = t;
        dd[k & 3u] = pick_delta(it.cur, me.cur, me.step);
        encoders_apply(0, 0, 0, dd[0], dd[1], dd[2], dd[3], 1, 1, 1, 1, 1, pick_group_btn(g));
        selected_track = keep;
    }
    p = msg_buf; p = put_s(p, "T"); p = put_u(p, (uint32_t)t + 1u); p = put_s(p, " "); p = put_s(p, ui_cell_label(k & 3u));
    p = put_s(p, " AS T"); p = put_u(p, (uint32_t)keep + 1u); finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}
static void gr_pad_pick(uint8_t x, uint8_t y)
{
    int g = gr_pick_group();
    uint8_t pg = pick_page(g);
    uint32_t key;
    if (y >= 4u && gr_pt(g, y & 3u)) {                                 /* 0.18: a track's knob across the tracks */
        if (gr_shift()) select_track(x);
        else gr_follow_copy(g, y & 3u, x);
        return;
    }
    if (y >= 4u && x >= 10u) return;                                   /* (black 11 is the FM-1's focus key: no value) */
    key = y < 4u ? white_key[x] : black_key[x];
    if (pg >= PICK_PAGES) pg = 0u;
    pick_focus[g][pg] = (uint8_t)(y & 3u);
    pick_key(pick_group_btn(g) | (1u << BTN_SEL), g, key);
}
/* FOLLOW: the view the FM-1 asks for - its steps, PERF (the MOSSE: VIAGGIO), the LFOs, the FX, the lanes (ENV), else
 * the knobs of its page (this view); SAVE: as it is. A change waits a quarter of a second (a button tapped in passing) */
static uint8_t gr_follow_view(void)
{
    uint32_t h = eff_held();
    int g = pick_group(h);
    if (h & (1u << BTN_SAVE)) return g_view;
    if (h & (1u << BTN_FX)) return GV_FX;
    if (g == PG_LFO) return GV_LFO;
    if (g == PG_ENV) return GV_CC;
    if (g == PG_EDIT) return GV_STEP;
    if (g == PG_GLO || (g < 0 && perf_mode)) return perf_page == 2u ? GV_VIAGGIO : GV_PERF;
    if (g >= 0) return GV_PICK;
    return GV_STEP;
}
static void gr_follow_tick(void)
{
    uint8_t w;
    if (!g_follow) return;
    w = gr_follow_view();
    if (w == g_view) { g_follow_want = 255u; return; }
    if (w != g_follow_want) { g_follow_want = w; g_follow_ms = fm1_ms; return; }
    if ((uint32_t)(fm1_ms - g_follow_ms) >= 250u && !g_down[0] && !g_down[1]) { gr_view_go(w); g_follow_want = 255u; }
}
static void gr_pad(uint8_t x, uint8_t y, uint8_t down)
{
    if (down) { g_shift_clean = 0u; g_shift_tapped = 0u; }
    if (g_view == GV_VIAGGIO) { gr_pad_viaggio(x, y, down); return; }
    if (g_view == GV_REGIA) { gr_pad_regia(x, y, down); return; }
    if (g_view == GV_STEP) { gr_pad_step(x, y, down); return; }
    if (g_view == GV_FX) { gr_pad_fx(x, y, down); return; }
    if (g_view == GV_DRUM) { gr_pad_drum(x, y, down); return; }
    if (g_view == GV_PERF) { gr_pad_perf(x, y, down); return; }
    if (!down) return;
    switch (g_view) {
    case GV_TRACK: gr_pad_track(x, y); break;
    case GV_EUCLID: gr_pad_euclid(x, y); break;
    case GV_TRACK3: gr_pad_track3(x, y); break;
    case GV_CC:    gr_pad_cc(x, y); break;
    case GV_LFO:   gr_pad_lfo(x, y); break;
    case GV_BEAT:  gr_pad_beat(x, y); break;
    case GV_SONG:  gr_pad_song(x, y); break;
    case GV_TRACK2: gr_pad_track2(x, y); break;
    case GV_LIB:   gr_pad_lib(x, y); break;
    case GV_PICK:  gr_pad_pick(x, y); break;
    default:       gr_pad_proj(x, y); break;
    }
}

static int grid_midi_in(uint8_t st, uint8_t d1, uint8_t d2)
{
    uint8_t ch = st & 15u, type = st & 0xF0u;
    if (st >= 0xF0u || (ch != 14u && ch != 15u)) return 0;       /* not ours */
    g_last_seen = fm1_ms ? fm1_ms : 1u;
    if (ch == 15u) {                                               /* MIDI channel 16: pads */
        if (type == 0xB0u && d1 == 118u) {
            if (d2 >= 64u) { if (!grid_attached || d2 == 127u) gr_set_attached(1u); }
            else if (grid_attached) gr_set_attached(0u);
        } else if ((type == 0x90u || type == 0x80u) && grid_attached && d1 < 128u) {
            uint8_t down = (type == 0x90u && d2) ? 1u : 0u, x = d1 & 15u, y = d1 >> 4;
            if (y < 8u) gr_pad(x, y, down);
        }
    } else if (type == 0xB0u && d1 < 32u && grid_attached) {       /* MIDI channel 15: buttons */
        gr_ctl(d1, d2 >= 64u);
    }
    return 1;
}

/* ------------------------------------------------------------ LEDs */

static void gr_put(uint32_t x, uint32_t y, uint8_t role) { g_want[y * 16u + x] = role; }

/* a bar of n pads from x0: lit up to idx (the top one brighter) */
static void gr_bar(uint32_t y, uint32_t x0, uint32_t n, int32_t idx, uint8_t on, uint8_t top)
{
    uint32_t i;
    for (i = 0; i < n; i++) gr_put(x0 + i, y, (int32_t)i < idx ? on : (int32_t)i == idx ? top : GL_FAINT);
}

/* one pad of n lit (the value), the middle one marked */
static void gr_spot(uint32_t y, uint32_t n, int32_t idx, uint32_t mid)
{
    uint32_t i;
    for (i = 0; i < n; i++) gr_put(i, y, (int32_t)i == idx ? GL_CURSOR : i == mid ? GL_DIM : GL_FAINT);
}

static int32_t gr_nearest(const int8_t *tab, uint32_t n, int32_t v)
{
    uint32_t i, best = 0u;
    int32_t bd = 1000;
    for (i = 0; i < n; i++) {
        int32_t d = (int32_t)tab[i] - v;
        if (d < 0) d = -d;
        if (d < bd) { bd = d; best = i; }
    }
    return (int32_t)best;
}

static int32_t gr_nearest_u(const uint8_t *tab, uint32_t n, int32_t v)
{
    uint32_t i, best = 0u;
    int32_t bd = 1000;
    for (i = 0; i < n; i++) {
        int32_t d = (int32_t)tab[i] - v;
        if (d < 0) d = -d;
        if (d < bd) { bd = d; best = i; }
    }
    return (int32_t)best;
}

static void gr_render_step(void)
{
    uint32_t t = selected_track, x, y, k;
    sq_track_cfg_t *cfg = &project.track[t];
    sq_step_t *row = gr_row(), *cs = &row[cursor_step];
    uint8_t inkey = gr_in_key(t), shift = gr_shift();
    uint16_t mask = sq_scale_mask(project.key_scale);
    if (track_tape(t)) { tape_grid_render(t); return; }   /* 0.11 */

    {
        uint64_t tail, bridge, half;
        note_blocks(t, &tail, &bridge, &half);                                               /* 0.12: the long notes as blocks */
        for (y = 0; y < 4u; y++) for (x = 0; x < 16u; x++) {
            uint32_t stn = y * 16u + x;
            sq_step_t *s = &row[stn];
            uint8_t on = (s->flags & SQ_STEP_ON) ? 1u : 0u, role, heard = live_preview(t, (uint8_t)stn);
            if (stn >= cfg->length || stn < cfg->start) role = on ? GL_BLUE : GL_OFF;
            else if (heard) role = on ? (s->velocity >= 110u ? GL_ACCENT : GL_ON) : GL_CYAN;   /* 0.8: cyan, a hit the live layer adds */
            else role = on ? GL_DIM : GL_FAINT;                                                  /* ... dim, a hit it takes away */
            if (!on && ((tail | half) & ((uint64_t)1u << stn)) && (role == GL_FAINT || role == GL_DIM)) role = GL_TAIL;
            if (on && (s->flags & SQ_STEP_LEGATO) && stn < cfg->length && stn >= cfg->start) role = GL_TIE;
            if (stn == cursor_step) role = on ? GL_CURSOR : GL_ORANGE;
            if (playing && stn < cfg->length && ev[t].step_index == stn) role = GL_PLAY;
            gr_put(x, y, role);
        }
    }
    gr_bar(4, 0, 16, ((int32_t)cs->velocity + 7) / 8 - 1, GL_ON, GL_ACCENT);
    if (shift) for (x = 0; x < 16u; x++) gr_put(x, 5, x >= SQ_COND_COUNT ? GL_OFF : cs->condition == x ? GL_WHITE : GL_VIOLET);
    else gr_bar(5, 0, 16, ((int32_t)cs->chance * 16 + 99) / 100 - 1, GL_CYAN, GL_WHITE);
    if (shift) {                                        /* 0.10: pad 15 PLAIN, pad 16 TIE */
        for (x = 0; x < 14u; x++) gr_put(x, 6, GL_OFF);
        gr_put(14, 6, (cs->flags & SQ_STEP_XOFF) ? GL_WHITE : GL_FAINT);
        gr_put(15, 6, (cs->flags & SQ_STEP_TIE) ? GL_WHITE : GL_FAINT);
    } else {
        gr_bar(6, 0, 8, (int32_t)cs->ratchet - 1, GL_ORANGE, GL_YELLOW);
        gr_bar(6, 8, 8, ((int32_t)cs->length * 8 - 1) / 100, GL_BLUE, GL_WHITE);
    }
    for (x = 0; x < 16u; x++) {
        uint8_t n = gr_pad_note(t, x), role;
        if (inkey) role = ((n + 12u - project.key_root) % 12u) == 0u ? GL_WHITE : ((mask >> ((n + 12u - project.key_root) % 12u)) & 1u) ? GL_DIM : GL_FAINT;
        else role = (n % 12u) == 0u ? GL_WHITE : is_black(n) ? GL_FAINT : GL_DIM;
        for (k = 0; k < SQ_POLY; k++) if (cs->note[k] == n) role = GL_CURSOR;
        gr_put(x, 7, role);
    }
}

static void gr_render_perf(void)
{
    uint32_t y, x, b = selected_track & 8u;
    for (y = 0; y < 8u; y++) {
        uint32_t t = b + y;
        sq_track_cfg_t *cfg = &project.track[t];
        uint8_t sel = t == selected_track;
        uint32_t pos = playing ? (uint32_t)ev[t].step_index * 4u / (cfg->length ? cfg->length : 1u) : 99u;
        gr_put(0, y, (pending_mute & (1u << t)) ? GL_PEND : (mute_mask & (1u << t)) ? GL_MUTED : GL_ON);
        gr_put(1, y, ((solo_mask >> t) & 1u) ? GL_YELLOW : GL_FAINT);
        for (x = 0; x < 8u; x++)
            gr_put(2u + x, y, tr[t].pattern == x ? (sel ? GL_ACCENT : GL_ON)
                              : tr[t].pending_pattern == x ? GL_PEND : (sel ? GL_DIM : GL_FAINT));
        gr_put(10, y, (retrig_mask & (1u << t)) ? GL_PEND : GL_BLUE);                       /* RETRIG */
        gr_put(11, y, (grid_kill & (1u << t)) ? GL_PLAY : GL_ORANGE);                      /* KILL */
        for (x = 0; x < 4u; x++) gr_put(12u + x, y, pos == x ? GL_PLAY : (sel ? GL_DIM : GL_FAINT));
    }
}

static void gr_render_viaggio(void)
{
    uint32_t x, t = selected_track, k;
    uint8_t bars = vg_bars(), m = vg_proposals(t);
    for (x = 0; x < 16u; x++) {                            /* row 1: the bars */
        if (x >= bars) gr_put(x, 0, GL_OFF);
        else gr_put(x, 0, (playing && x == vg_bar) ? GL_PLAY : x < vg_bar ? GL_ON : (vg_fill && x + 1u == bars) ? GL_FILL : GL_FAINT);
    }
    for (x = 0; x < 16u; x++) {                            /* row 2: the tracks; row 3: the queue */
        uint8_t st = vg_state(x), role;
        int q;
        role = st == SQ_TS_EMPTY ? GL_FAINT : st == SQ_TS_PROPOSED ? GL_DIM : st == SQ_TS_IN ? GL_ON : GL_MUTED;
        if (x == t) role = st == SQ_TS_IN ? GL_ACCENT : GL_CURSOR;
        if (vg_rec_t == x) role = GL_PLAY;
        gr_put(x, 1, role);
        q = sq_queue_find(&vg_q, SQ_MV_IN, (uint8_t)x);
        if (q < 0) q = sq_queue_find(&vg_q, SQ_MV_OUT, (uint8_t)x);
        if (q < 0) q = sq_queue_find(&vg_q, SQ_MV_SWAP, (uint8_t)x);
        if (q < 0) q = sq_queue_find(&vg_q, SQ_MV_LOOP, (uint8_t)x);
        gr_put(x, 2, q >= 0 ? GL_PEND : st == SQ_TS_IN ? GL_DIM : st == SQ_TS_EMPTY ? GL_OFF : GL_FAINT);
    }
    for (x = 0; x < 16u; x++) {                            /* row 4: the moves */
        uint8_t kind = x < 11u ? VG_BLACK_MOVE[x] : 0u, role = GL_OFF;
        if (x < 10u) role = sq_queue_find(&vg_q, kind, selected_track) >= 0 ? GL_PEND : vg_allows_move(kind) ? GL_DIM : GL_OFF;
        else if (x == 10u) role = vg_now ? GL_PEND : vg_q.n ? GL_CYAN : GL_FAINT;
        else if (x == 14u) role = vg_trail.n ? GL_VIOLET : GL_FAINT;
        else if (x == 15u) role = vg_q.n ? GL_ORANGE : GL_FAINT;
        gr_put(x, 3, role);
    }
    for (x = 0; x < 16u; x++) {                            /* row 5: the energy applied, the target */
        uint32_t lv = (x * 100u + 7u) / 15u;
        uint8_t role = lv <= vg_energy_cur ? GL_ON : GL_FAINT;
        if (project.viaggio.energy != vg_energy_cur && lv > vg_energy_cur && lv <= project.viaggio.energy) role = GL_PEND;
        if (project.viaggio.energy > vg_energy_cur && lv > project.viaggio.energy && lv - 7u <= project.viaggio.energy) role = GL_PEND;
        gr_put(x, 4, role);
    }
    for (x = 0; x < 16u; x++) {                            /* row 6: the proposals of the selected track */
        uint8_t role = GL_OFF;
        if (x < SQ_PATTERNS) role = x == tr[t].pattern ? GL_PLAY : (m & (1u << x)) ? (x == vg_prop[t] ? GL_ACCENT : GL_DIM) : GL_OFF;
        else if (x == 15u) role = GL_ORANGE;
        gr_put(x, 5, role);
    }
    {                                                      /* row 7: the progressions, the chord playing */
        int q = sq_queue_find(&vg_q, SQ_MV_PROG, 0u);
        uint8_t hi = harm_index(), pn;                     /* (0.10: pads 1-6 the genre's progressions, 7-10 the player's) */
        if (project.gen.harm_prog >= SQ_PROGS) pn = project.uprog[(project.gen.harm_prog - SQ_PROGS) % SQ_UPROGS].n;
        else pn = sq_prog_get(vg_lib_genre(), project.gen.harm_prog)->n;
        for (x = 0; x < 16u; x++) {
            uint8_t role = GL_OFF;
            if (x < SQ_PROGS_ALL) role = (q >= 0 && vg_q.m[q].a == x) ? GL_PEND : x == project.gen.harm_prog ? (project.gen.harm_on ? GL_ACCENT : GL_CURSOR) : x >= SQ_PROGS ? (project.uprog[x - SQ_PROGS].n ? GL_VIOLET : GL_FAINT) : GL_DIM;
            else if (x >= 10u && x - 10u < pn) role = (project.gen.harm_on && playing && x - 10u == hi) ? GL_CYAN : GL_FAINT;
            gr_put(x, 6, role);
        }
    }
    for (x = 0; x < 16u; x++) {                            /* row 8: the trail, the phrase playing on the right */
        uint32_t back = 15u - x;
        int q = sq_queue_find(&vg_q, SQ_MV_BACK, 0u);
        uint8_t role = !back ? GL_PLAY : back <= vg_trail.n ? GL_DIM : GL_OFF;
        if (q >= 0 && back == vg_q.m[q].a) role = GL_PEND;
        gr_put(x, 7, role);
    }
    (void)k;
}

static void gr_render_regia(void)
{
    uint32_t x;
    for (x = 0; x < 16u; x++) gr_put(x, 0, g_regia_led[x] == 2u ? GL_PLAY : g_regia_led[x] ? GL_ON : GL_DIM);
}

static void gr_render_track(void)
{
    uint32_t t = selected_track, x, sw = 0u;
    sq_track_cfg_t *cfg = &project.track[t];
    sq_step_t *cs = &gr_row()[cursor_step];
    uint8_t mode = SQ_CHORD_MODE(cfg->chord_mode), octs = SQ_CHORD_OCTS(cfg->chord_mode);

    for (x = 0; x < TOOL_COUNT; x++) gr_put(x, 0, x == TOOL_UNDO ? (undo_valid ? GL_CURSOR : GL_FAINT) : x == TOOL_PASTE ? (clip_valid ? GL_ORANGE : GL_FAINT) : GL_ORANGE);
    for (x = 0; x < SQ_CHORD_COUNT; x++) gr_put(x, 1, mode == x ? GL_WHITE : GL_VIOLET);
    for (x = 13; x < 16u; x++) gr_put(x, 1, octs == x - 12u ? GL_WHITE : GL_BLUE);
    for (x = 0; x < 8u; x++) if (cfg->swing >= GR_SWING[x]) sw = x;
    gr_bar(2, 0, 8, (int32_t)sw, GL_YELLOW, GL_WHITE);
    for (x = 0; x < SQ_DIR_COUNT; x++) gr_put(8u + x, 2, cfg->direction == x ? GL_WHITE : GL_BLUE);
    for (x = 12; x < 16u; x++) gr_put(x, 2, GL_VIOLET);
    for (x = 0; x < 16u; x++) gr_put(x, 3, x >= SQ_DIV_COUNT ? GL_OFF : cfg->division == x ? GL_WHITE : GL_DIM);
    gr_put(13, 3, track_drum(t) ? GL_ORANGE : track_in_key(t) ? GL_CYAN : GL_FAINT);
    if (gr_shift()) for (x = 0; x < 16u; x++) gr_put(x, 4, x == cfg->start / 4u ? GL_YELLOW : x * 4u < cfg->start ? GL_FAINT : GL_DIM);
    else gr_bar(4, 0, 16, ((int32_t)cfg->length + 3) / 4 - 1, GL_ON, GL_ACCENT);
    for (x = 0; x < 8u; x++) {
        gr_put(x, 5, cfg->hum_time == GR_HUM[x] ? GL_WHITE : cfg->hum_time > GR_HUM[x] ? GL_CYAN : GL_FAINT);
        gr_put(8u + x, 5, cfg->hum_vel == GR_HUM[x] ? GL_WHITE : cfg->hum_vel > GR_HUM[x] ? GL_CYAN : GL_FAINT);
    }
    gr_spot(6, 15, gr_nearest(GR_VOFF, 15u, cfg->vel_offset), 7u);
    gr_spot(7, 15, gr_nearest(GR_NUDGE, 15u, cs->nudge), 7u);
    gr_put(15, 6, GL_OFF);
    gr_put(15, 7, GL_OFF);
}

static void gr_render_cc(void)
{
    uint32_t t = selected_track, x, y;
    sq_track_cfg_t *cfg = &project.track[t];
    sq_step_t *row = gr_row();

    for (x = 0; x < 16u; x++) {
        uint32_t stn = (uint32_t)page * 16u + x;
        sq_step_t *s = &row[stn];
        uint8_t v = s->lane[g_lane], on = (s->flags & SQ_STEP_ON) ? 1u : 0u, top = 4u;
        if (v != SQ_LANE_NONE) for (y = 0; y < 4u; y++) if ((int32_t)v + 16 >= (int32_t)GR_CCLV[y]) { top = (uint8_t)y; break; }
        for (y = 0; y < 4u; y++) {
            uint8_t role = GL_OFF;
            if (v != SQ_LANE_NONE && y >= top) role = !on ? GL_DIM : y == top ? GL_ACCENT : GL_ON;
            else if (y == 3u) role = stn == cursor_step ? GL_ORANGE : (stn >= cfg->start && stn < cfg->length) ? GL_FAINT : GL_OFF;
            if (playing && y == 3u && ev[t].step_index == stn && v == SQ_LANE_NONE) role = GL_PLAY;
            gr_put(x, y, role);
        }
    }
    for (x = 0; x < SQ_LANES; x++) gr_put(x, 4, x == g_lane ? GL_CURSOR : cfg->lane_cc[x] != SQ_LANE_NONE ? GL_ON : GL_FAINT);
    gr_put(6, 4, GL_OFF); gr_put(7, 4, GL_OFF);
    for (x = 0; x < 4u; x++) gr_put(8u + x, 4, page == x ? GL_ACCENT : GL_DIM);
    for (x = 12u; x < 15u; x++) gr_put(x, 4, GL_OFF);
    gr_put(15, 4, GL_ORANGE);
    for (x = 0; x < 16u; x++) gr_put(x, 5, cfg->lane_cc[g_lane] == GR_CCP[x] ? GL_WHITE : GL_VIOLET);
    if (gr_shift()) for (x = 0; x < 16u; x++) gr_put(x, 5, learn_kind == 1u && learn_t == t && learn_l == g_lane ? GL_PEND : GL_CYAN);
    if (cfg->lane_base[g_lane] == SQ_LANE_NONE) for (x = 0; x < 16u; x++) gr_put(x, 6, GL_FAINT);
    else gr_bar(6, 0, 16, ((int32_t)cfg->lane_base[g_lane] * 15 + 63) / 127, GL_CYAN, GL_WHITE);
    gr_put(0, 7, cfg->lane_cc[g_lane] == SQ_LANE_NONE ? GL_WHITE : GL_ORANGE);
    gr_put(1, 7, cfg->lane_base[g_lane] == SQ_LANE_NONE ? GL_WHITE : GL_ORANGE);
}

static void gr_render_pick(void)
{
    static const uint8_t KC[4] = {GL_ON, GL_BLUE, GL_VIOLET, GL_ORANGE};
    int g = gr_pick_group();
    uint32_t x, y;
    for (y = 0; y < 8u; y++) {
        pick_t d;
        pick_desc(g, y & 3u, &d);
        if (y >= 4u && gr_pt(g, y & 3u)) {                             /* 0.18: across the tracks */
            for (x = 0; x < 16u; x++) {
                pick_t e;
                if (x == selected_track) { gr_put((uint8_t)x, (uint8_t)y, GL_WHITE); continue; }
                gr_desc_of(g, y & 3u, (uint8_t)x, &e);
                gr_put((uint8_t)x, (uint8_t)y, e.cur == d.cur ? KC[y & 3u] : GL_FAINT);
            }
            continue;
        }
        for (x = 0; x < 16u; x++) {
            uint8_t role = GL_OFF;
            if (y < 4u || x < 10u) {
                uint32_t key = y < 4u ? white_key[x] : black_key[x];
                int wi = key_is_in(white_key, 16u, key), bi = key_is_in(black_key, 11u, key);
                if (d.kind == PK_NONE) role = GL_FAINT;
                else { int32_t v = pick_target(&d, wi, bi, key); if (v != PICK_NO) role = v == d.cur ? GL_WHITE : KC[y & 3u]; }
            }
            gr_put((uint8_t)x, (uint8_t)y, role);
        }
    }
}

static void gr_render_lfo(void)
{
    uint32_t x;
    const sq_lfo_t *l = &project.lfo[lfo_sel];
    for (x = 0; x < SQ_LFOS; x++) {
        uint8_t en = project.lfo[x].enabled;
        gr_put(x, 0, x == lfo_sel ? (en ? GL_ACCENT : GL_CURSOR) : en ? GL_ON : GL_FAINT);
    }
    for (x = 0; x < 8u; x++) gr_put(x, 1, l->shape == x ? GL_WHITE : GL_VIOLET);
    for (x = 0; x < SQ_LD_KINDS; x++) gr_put(8u + x, 1, l->dest == x ? GL_WHITE : GL_BLUE);
    gr_put(14, 1, (l->flags & SQ_LF_RETRIG) ? GL_WHITE : GL_FAINT);
    gr_put(15, 1, (l->flags & SQ_LF_INVERT) ? GL_WHITE : GL_FAINT);
    gr_bar(2, 0, 16, l->rate, GL_ON, GL_ACCENT);
    gr_bar(3, 0, 16, ((int32_t)l->depth * 15 + 63) / 127, GL_ORANGE, GL_YELLOW);
    gr_bar(4, 0, 16, ((int32_t)l->center * 15 + 63) / 127, GL_CYAN, GL_WHITE);
    gr_bar(5, 0, 16, ((int32_t)l->phase * 15 + 63) / 127, GL_BLUE, GL_WHITE);
    for (x = 0; x < 16u; x++) gr_put(x, 6, (l->dest == SQ_LD_CC && x >= ch_limit()) ? GL_OFF : l->target == x ? GL_WHITE : GL_DIM);
    for (x = 0; x < 16u; x++) gr_put(x, 7, l->param == GR_CCP[x] ? GL_WHITE : GL_VIOLET);
    if (gr_shift()) for (x = 0; x < 16u; x++) gr_put(x, 7, learn_kind == 2u && learn_l == lfo_sel ? GL_PEND : GL_CYAN);
}

static void gr_render_beat(void)
{
    uint32_t x, nv = sq_beat_variants(beat_genre, beat_func), ti = gen_target_index();
    const sq_gen_t *g = &project.gen;
    const sq_track_cfg_t *cfg = &project.track[selected_track];
    uint8_t harm = g->harm_on, mine = 1u;
    for (x = 0; x < 16u; x++) {
        if (x < 12u) { uint32_t gn = g_genre_page * 12u + x; gr_put(x, 0, gn >= SQ_GENRES ? GL_OFF : gn == beat_genre ? GL_WHITE : GL_DIM); }
        else gr_put(x, 0, x == 12u ? (g_genre_page == 2u ? GL_VIOLET : g_genre_page ? GL_CYAN : GL_BLUE) :   /* (0.16: page 3, the merengue) */
                      x == 13u ? GL_ACCENT : x == 14u ? GL_ORANGE : GL_PLAY);
        if (x < 9u) {
            uint8_t l[SQ_PARTS_MAX + 2u], n = beat_list(l), paged = n > 9u ? 1u : 0u, i = (uint8_t)(paged ? g_part_page * 8u + x : x);
            if (paged && x == 8u) gr_put(x, 1, g_part_page ? GL_CYAN : GL_BLUE);
            else gr_put(x, 1, i >= n ? GL_OFF : l[i] == beat_func ? GL_WHITE : l[i] == SQ_FUNC_PROG || l[i] == SQ_FUNC_KIT ? GL_ORANGE :
                              i < sq_genre_band(beat_genre) ? GL_VIOLET : GL_DIM);   /* (the band violet, the parts kept dim) */
        }
        else if (x < 9u + SQ_SCOPES) gr_put(x, 1, g->scope == x - 9u ? GL_WHITE : GL_BLUE);
        else gr_put(x, 1, live_active(selected_track) ? GL_ORANGE : GL_FAINT);               /* WRITE LIVE */
        if (x < SQ_PROGS) gr_put(x, 2, mine && g->harm_prog == x ? (harm ? GL_CYAN : GL_WHITE) : GL_DIM);
        else if (x == 6u) gr_put(x, 2, harm ? GL_ON : GL_FAINT);
        else if (x == 7u) gr_put(x, 2, g->harm_bars ? GL_YELLOW : GL_BLUE);
        else if (x == 8u) gr_put(x, 2, (cfg->flags & SQ_TF_FOLLOW) ? GL_CYAN : GL_FAINT);
        else if (x == 9u) gr_put(x, 2, nv > 6u ? (g_var_page ? GL_CYAN : GL_BLUE) : GL_OFF);
        else if (x >= 10u) { uint32_t v = g_var_page * 6u + x - 10u; gr_put(x, 2, v >= nv ? GL_OFF : (beat_var % (nv ? nv : 1u)) == v ? GL_WHITE : GL_VIOLET); }
        if (x < 5u) gr_put(x, 3, dice_pending && dice_kind == DICE_SEQ + x ? GL_PLAY : GL_ORANGE);
        else if (x == 5u || x == 6u) gr_put(x, 3, dice_pending ? (x == 5u ? GL_ON : GL_MUTED) : GL_FAINT);
        else if (x >= 8u && x < 8u + GEN_TARGET_SETS) gr_put(x, 3, x - 8u == ti ? GL_WHITE : x - 8u < ti ? GL_CYAN : GL_FAINT);
        else if (x == 14u) gr_put(x, 3, dice_pending && dhist_pos > 0u ? GL_YELLOW : GL_FAINT);
        else if (x == 15u) gr_put(x, 3, dice_pending && dhist_pos + 1u < dhist_n ? GL_YELLOW : GL_FAINT);
    }
    if (gr_shift()) {                                   /* the pattern chosen, 32 steps over two rows */
        const char *notes, *text = nv ? sq_beat_text(beat_genre, beat_func, (uint8_t)(beat_var % nv), &notes) : 0;
        uint32_t i, end = 0u;
        for (i = 0; i < 32u; i++) {
            char c = (text && !end) ? text[i] : '\0';
            uint8_t role = GL_OFF;
            if (!c) end = 1u;
            else if (c == 'X') role = GL_ACCENT;
            else if (c == 'x') role = GL_ON;
            else if (c == 'o' || c == 'g') role = GL_DIM;
            else if (c >= '2' && c <= '4') role = GL_YELLOW;
            else if (c == '.') role = GL_FAINT;
            gr_put(i & 15u, 4u + (i >> 4), role);
        }
    } else {
        uint8_t euc = (cfg->flags & SQ_TF_EUC) ? 1u : 0u;
        if (g->scope == SQ_SCOPE_CUSTOM) {
            uint16_t cm = gen_custom_mask();
            for (x = 0; x < 16u; x++) gr_put(x, 4, (cm & (1u << x)) ? GL_WHITE : GL_FAINT);
        } else gr_bar(4, 0, 16, (int32_t)cfg->euc_pulses - 1, euc ? GL_CYAN : GL_ORANGE, GL_YELLOW);
        for (x = 0; x < 16u; x++) gr_put(x, 5, cfg->euc_rot == x ? GL_YELLOW : GL_FAINT);
    }
    gr_bar(6, 0, 8, gr_nearest_u(GR_DENS, 8u, tool_density), GL_CYAN, GL_WHITE);
    gr_bar(6, 8, 8, gr_nearest_u(GR_HEAT, 8u, tool_heat), GL_ORANGE, GL_WHITE);
    gr_put(0, 7, evo_run == 1u ? GL_PLAY : evo_run ? GL_ON : GL_DIM);
    gr_put(1, 7, evo_run == 2u ? GL_CYAN : GL_FAINT);
    gr_put(2, 7, evo_run ? GL_ORANGE : GL_FAINT);
    gr_put(3, 7, project.gen.evo_drift ? GL_YELLOW : GL_FAINT);
    for (x = 0; x < SQ_EVO_EVERY; x++) gr_put(4u + x, 7, project.gen.evo_every == x ? GL_WHITE : GL_BLUE);
    gr_bar(7, 9, 7, gr_nearest_u(GR_EVOAMT, 7u, project.gen.evo_amount), GL_VIOLET, GL_WHITE);
}

static void gr_render_euclid(void)
{
    uint32_t y, x, b = selected_track & 8u;
    uint8_t sh = gr_shift();
    for (y = 0; y < 8u; y++) {
        uint32_t t = b + y;
        const sq_track_cfg_t *c = &project.track[t];
        uint8_t euc = (c->flags & SQ_TF_EUC) ? 1u : 0u, sel = t == selected_track;
        gr_put(0, y, euc ? (track_audible(t) ? GL_PLAY : GL_MUTED) : sel ? GL_DIM : GL_FAINT);
        for (x = 1; x < 16u; x++) {
            uint8_t role;
            if (sh) role = c->euc_rot == x - 1u ? GL_YELLOW : GL_FAINT;
            else role = x < c->euc_pulses ? (euc ? GL_CYAN : GL_DIM) : x == c->euc_pulses ? (euc ? GL_WHITE : GL_ORANGE) : GL_FAINT;
            gr_put(x, y, role);
        }
    }
}

static void gr_render_track3(void)
{
    static const uint8_t SLOTC[SQ_ALGO_SLOTS] = {GL_FAINT, GL_BLUE, GL_CYAN, GL_WHITE};
    uint32_t t = selected_track, x;
    const sq_track_cfg_t *c = &project.track[t];
    const sq_algo_t *al = algo_edit(t);               /* 0.16: the READY one's values, if there is one */
    uint8_t run = algo_slot(t)->algo, shown = algo_shown(t);
    const sq_step_t *cs = &gr_row()[cursor_step];
    const sq_track_cfg_t *mv = mfx_view(t);             /* 0.16: the READY MIDI FX's values, if there is one */
    int32_t strum = (c->strum + (c->strum < 0 ? -5 : 5)) / 10, amt = mv->mfx_amt;
    for (x = 0; x < 16u; x++) {
        gr_put(x, 0, x < SQ_VOICES ? (c->voicing == x ? GL_WHITE : GL_VIOLET) : (int32_t)x - 10 == strum ? GL_WHITE : x == 10u ? GL_DIM : GL_FAINT);
        gr_put(x, 1, x < SQ_MFXS ? (mfx_on(t, x) ? GL_WHITE : mfx_shown(t) == x ? GL_ORANGE : GL_VIOLET)   /* 0.16: orange READY; 0.19: white, every one that plays */
                     : !mv->mfx ? GL_OFF : (int32_t)x - 10 == amt ? GL_WHITE : x == 10u ? GL_DIM : GL_FAINT);
        if (x < 8u) gr_put(x, 2, (mv->mfx == SQ_MFX_OCTAVE && x >= SQ_OCT_PATTERNS) ? GL_OFF : mv->mfx_time == x ? GL_WHITE : GL_BLUE);
        else gr_put(x, 2, GR_KEEP[x - 8u] <= mv->mfx_fb ? (GR_KEEP[x - 8u] == mv->mfx_fb ? GL_WHITE : GL_CYAN) : GL_FAINT);
        if (x < SQ_ALGOS) gr_put(x, 3, run == x && x ? GL_WHITE : shown == x ? GL_ORANGE : GL_VIOLET);   /* 0.16: orange READY */
        else if (x == 5u) gr_put(x, 3, (c->flags & SQ_TF_FOLLOW) ? GL_CYAN : GL_FAINT);
        else if (x == 6u) gr_put(x, 3, (c->flags & SQ_TF_EUC) ? GL_CYAN : GL_FAINT);
        else if (x == 7u) gr_put(x, 3, SLOTC[algo_cur[t] < SQ_ALGO_SLOTS ? algo_cur[t] : 0u]);   /* 0.11: which slot (tap: the next) */
        else if (x >= 8u) {
            uint8_t v = (uint8_t)(x - 8u), n = al->algo == SQ_ALGO_TURING ? SQ_TM_MODES : al->algo == SQ_ALGO_CELL ? 4u : al->algo == SQ_ALGO_ACCENT ? 8u : 0u;
            gr_put(x, 3, v >= n ? GL_OFF : al->c == v ? GL_WHITE : GL_BLUE);
        }
    }
    switch (al->algo) {                                 /* rows 4 and 5: A and B as bars */
    case SQ_ALGO_TURING:  gr_bar(4, 0, 16, gr_nearest_u(GR_MUT, 16u, al->a), GL_ORANGE, GL_WHITE);
                          gr_bar(5, 0, 15, (int32_t)al->b - 2, GL_CYAN, GL_WHITE); break;
    case SQ_ALGO_CELL:    for (x = 0; x < 16u; x++) gr_put(x, 4, GR_RULE[x] == al->a ? GL_WHITE : GL_VIOLET);
                          gr_bar(5, 0, 16, gr_nearest_u(GR_CELLS, 16u, al->b), GL_CYAN, GL_WHITE); break;
    case SQ_ALGO_ACCENT:  for (x = 0; x < 5u; x++) gr_put(x, 4, al->a == x ? GL_WHITE : GL_VIOLET);
                          gr_bar(5, 0, 16, (int32_t)al->b / 4, GL_ORANGE, GL_WHITE); break;
    case SQ_ALGO_DENSITY: gr_bar(4, 0, 16, gr_nearest_u(GR_DENSA, 16u, al->a), GL_ORANGE, GL_WHITE);
                          gr_bar(5, 0, 16, ((int32_t)al->b - 10) / 6, GL_CYAN, GL_WHITE); break;
    default: break;
    }
    {   /* row 6: the long gate of the cursor step (1.5 .. 64 steps; SHIFT 17 .. 32) */
        int32_t g = -1;
        if (cs->length > 100u) g = gr_shift() ? (int32_t)cs->length - 117 : gr_nearest_u(GR_LONG, 16u, (int32_t)cs->length);
        for (x = 0; x < 16u; x++) gr_put(x, 6, (int32_t)x == g ? GL_WHITE : (int32_t)x < g ? GL_BLUE : GL_FAINT);
    }
    for (x = 0; x < 16u; x++) gr_put(x, 7, x >= ch_limit() ? GL_OFF : track_ch(t) == x ? GL_WHITE : GL_DIM);
}

static void gr_render_drum(void)
{
    uint32_t y, x, b = selected_track & 8u;
    uint8_t shift = gr_shift();
    for (y = 0; y < 8u; y++) {
        uint32_t t = b + y;
        const sq_track_cfg_t *c = &project.track[t];
        sq_step_t *row = project.step[t][tr[t].pattern];
        uint8_t aud = track_audible(t), sel = t == selected_track;
        for (x = 0; x < 16u; x++) {
            uint8_t stn = gr_drum_step(t, x), role;
            sq_step_t *s = &row[stn];
            uint8_t on = (s->flags & SQ_STEP_ON) ? 1u : 0u, heard = live_preview(t, stn);
            if (stn >= c->length || stn < c->start) role = on ? GL_BLUE : GL_OFF;
            else if (heard) role = !aud ? GL_MUTED : !on ? GL_CYAN : s->velocity >= 110u ? GL_ACCENT : GL_ON;
            else role = on ? GL_DIM : sel ? GL_DIM : GL_FAINT;
            if (sel && stn == cursor_step) role = on ? GL_CURSOR : GL_ORANGE;
            if (playing && ev[t].step_index == stn && stn < c->length) role = GL_PLAY;
            gr_put(x, y, role);
        }
    }
    if (shift) for (x = 0; x < 4u; x++) gr_put(x, 0, page == x ? GL_YELLOW : GL_VIOLET);
}

static void gr_render_song(void)
{
    static const uint8_t ECOL[4] = {GL_ON, GL_BLUE, GL_CYAN, GL_VIOLET};
    const sq_song_t *sg = &project.song;
    uint32_t x, y, bar = 0u, playbar = 999u;
    if (g_song_sel > sg->len) g_song_sel = sg->len;
    if (song_on && !song_wait) { for (x = 0; x < song_pos && x < sg->len; x++) bar += sg->e[x].bars; playbar = bar + song_bar; }
    for (x = 0; x < 16u; x++) {
        uint32_t e = (g_song_sel & ~15u) + x;
        uint8_t role = e < sg->len ? ECOL[e & 3u] : e == sg->len && e < SQ_SONG_LEN ? GL_FAINT : GL_OFF;
        if (song_on && e == song_pos && e < sg->len) role = GL_PLAY;
        if (e == g_song_sel) role = GL_CURSOR;
        gr_put(x, 0, role);
    }
    for (x = 0; x < SQ_SCENES; x++)
        gr_put(x, 1, g_song_sel < sg->len && sg->e[g_song_sel].scene == x ? GL_WHITE : GL_DIM);
    if (g_song_sel < sg->len) gr_bar(2, 0, 16, gr_nearest_u(GR_BARS, 16u, sg->e[g_song_sel].bars), GL_ON, GL_WHITE);
    gr_put(0, 3, song_on ? GL_PLAY : GL_DIM);
    gr_put(1, 3, sg->loop ? GL_ON : GL_FAINT);
    gr_put(2, 3, g_song_sel < sg->len ? GL_ORANGE : GL_FAINT);
    gr_put(3, 3, g_song_sel < sg->len ? GL_MUTED : GL_FAINT);
    gr_put(12, 3, g_song_sel >= 16u ? GL_BLUE : GL_FAINT);
    gr_put(13, 3, (g_song_sel & ~15u) + 16u <= sg->len && (g_song_sel & ~15u) + 16u < SQ_SONG_LEN ? GL_BLUE : GL_FAINT);
    gr_put(15, 3, gr_shift() ? GL_PLAY : GL_FAINT);
    for (y = 0; y < 4u; y++) for (x = 0; x < 16u; x++) {
        uint32_t b = y * 16u + x;
        uint8_t e = gr_song_entry_at(b), role = e == 255u ? GL_OFF : ECOL[e & 3u];
        if (e != 255u && e == g_song_sel) role = GL_DIM;
        if (b == playbar) role = GL_PLAY;
        gr_put(x, 4u + y, role);
    }
}

static void gr_render_fx(void)
{
    uint32_t x;
    int32_t kt = ktrans_target();
    for (x = 0; x < 16u; x++) {
        uint16_t lt = gr_loop_ticks((uint8_t)x);
        gr_put(x, 0, (fx_now() >> x) & 1u ? GL_PLAY : x == FX_FILL ? GL_FILL : GL_ORANGE);
        if (lt) gr_put(x, 1, loop_on && loop_len == lt ? (lp_held ? GL_PLAY : GL_ACCENT) : x < 8u ? GL_YELLOW : GL_CYAN);
        {   /* TRANSPOSE: where the key is (white), where it is going (blinking), 0 marked */
            int32_t v = (int32_t)x - 7;
            gr_put(x, 2, v == kt && ktrans_pend != SQ_KT_NONE ? GL_PEND : v == project.live.ktrans ? GL_WHITE : v == 0 ? GL_DIM : GL_VIOLET);
        }
        gr_put(x, 3, ((g_loop_mask >> x) & 1u) ? (x == selected_track ? GL_ACCENT : GL_ON) : GL_FAINT);
        gr_put(x, 5, (grid_kill >> x) & 1u ? GL_PLAY : !track_audible(x) ? GL_MUTED : x == selected_track ? GL_CURSOR : GL_DIM);
    }
    gr_put(15, 1, loop_on ? GL_PLAY : GL_FAINT);                                          /* EXIT */
    gr_put(13, 1, echo_global ? GL_PLAY : GL_BLUE);                                       /* 0.8: ECHO */
    for (x = 0; x < 8u; x++) {
        gr_put(x, 6, project.live.morph_b == x ? GL_WHITE : scene_cursor == x ? GL_ON : GL_DIM);   /* MORPH to */
        gr_put(8u + x, 6, x == 7u ? (project.live.mute_q ? GL_ORANGE : GL_FAINT) : project.live.quant == x ? GL_WHITE : GL_BLUE);
    }
    gr_bar(4, 0, 16, ((int32_t)morph_pos * 15 + 63) / 127, GL_VIOLET, GL_WHITE);          /* MORPH */
    gr_put(0, 7, temp_on ? GL_PLAY : GL_CYAN);
    gr_put(1, 7, rl_state ? GL_PEND : rl_src != 255u ? GL_ORANGE : GL_FAINT);              /* RELOAD */
    gr_put(2, 7, restart_pend ? GL_PEND : playing ? GL_ORANGE : GL_FAINT);                 /* RESTART */
    gr_put(3, 7, stop_at_bar ? GL_PEND : playing ? GL_MUTED : GL_FAINT);                   /* STOP at the end of the bar */
    for (x = 0; x < SQ_SNAPS; x++)                                                         /* 0.8: SNAPSHOTS */
        gr_put(4u + x, 7, snap_pend == x ? GL_PEND : snap_cur == x && project.snap[x].used ? GL_PLAY : project.snap[x].used ? GL_CYAN : gr_shift() ? GL_ORANGE : GL_FAINT);
    gr_put(12, 7, snap_capture ? GL_PEND : GL_VIOLET);
    gr_put(13, 7, snap_cur < SQ_SNAPS ? GL_ON : GL_FAINT);
    gr_put(14, 7, snap_cur < SQ_SNAPS ? GL_YELLOW : GL_FAINT);
    gr_put(15, 7, GL_PLAY);
}

static void gr_render_proj(void)
{
    static const uint8_t BLACK[12] = {0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0};
    uint32_t x, bar = playing ? (global_clock / 96u) % 16u : 99u;
    for (x = 0; x < 12u; x++) gr_put(x, 0, project.key_root == x ? GL_WHITE : BLACK[x] ? GL_FAINT : GL_DIM);
    for (x = 0; x < SQ_MKS; x++) gr_put(x, 4, project.live.master_fn == x ? GL_WHITE : GL_VIOLET);   /* the MASTER knob */
    gr_put(4, 4, project.live.remote_mode == SQ_RM_OFF ? GL_FAINT : project.live.remote_mode == SQ_RM_14 ? GL_ON : GL_ACCENT);   /* the remote: 14, 13 + 14 */
    for (x = 0; x < 16u; x++) {
        gr_put(x, 1, project.key_scale == x ? GL_WHITE : GL_VIOLET);
        gr_put(x, 3, track_drum(x) ? GL_ORANGE : track_in_key(x) ? GL_CYAN : GL_FAINT);
        gr_put(x, 7, bar == x ? GL_PLAY : GL_FAINT);
    }
    for (x = 0; x < 15u; x++) gr_put(x, 2, project.key_shift == GR_SHIFT[x] ? GL_WHITE : GR_SHIFT[x] == 0 ? GL_DIM : GL_FAINT);
    gr_put(13, 4, bake_ask ? GL_PEND : GL_ORANGE);
    gr_put(14, 4, GL_BLUE);
    gr_put(15, 4, GL_BLUE);
    for (x = 0; x < SQ_SLOTS; x++) gr_put(x, 5, x == slot_cur ? GL_CURSOR : slot_info[x].ok ? GL_ON : GL_FAINT);
    gr_put(8, 5, ask_kind == 1u ? GL_PEND : GL_ORANGE);
    gr_put(9, 5, ask_kind == 2u ? GL_PEND : slot_info[slot_cur].ok ? GL_ORANGE : GL_FAINT);
    gr_put(11, 5, playing ? GL_FAINT : GL_CYAN);
    gr_put(0, 6, GL_BLUE); gr_put(1, 6, GL_BLUE); gr_put(2, 6, GL_BLUE); gr_put(3, 6, GL_BLUE);
    gr_put(4, 6, (fm1_ms - tap_last) < 2000u ? GL_PLAY : GL_YELLOW);
    gr_put(5, 6, rec_quant ? GL_ON : GL_DIM);
    gr_put(6, 6, project.clock_mode == SQ_CLOCK_MASTER ? GL_ON : GL_CYAN);
    gr_put(8, 6, (mute_mask || solo_mask) ? GL_ORANGE : GL_FAINT);
}

/* a value 1..128 on 16 pads: a bar to it, its colour the page (1-16 green, 17-32 cyan, 33-48 blue, 49-64 violet ...) */
static uint8_t gr_len_role(uint32_t v, uint32_t x)
{
    static const uint8_t PAGE_ROLE[4] = {GL_ON, GL_CYAN, GL_BLUE, GL_VIOLET};
    uint32_t pg, idx;
    if (!v) return GL_FAINT;
    pg = (v - 1u) / 16u; idx = (v - 1u) % 16u;
    return x < idx ? PAGE_ROLE[pg & 3u] : x == idx ? GL_WHITE : GL_FAINT;
}

static void gr_render_track2(void)
{
    uint32_t t = selected_track, x, k;
    const sq_track_cfg_t *cfg = &project.track[t];
    uint8_t ch = track_ch(t), pc = project.scene[g_pc_scene].pc[ch];
    for (k = 0; k < SQ_PLANES; k++) for (x = 0; x < 16u; x++) gr_put(x, k, gr_len_role(cfg->plen[k], x));
    for (x = 0; x < 16u; x++) gr_put(x, 3, pc > 127u ? GL_FAINT : gr_len_role((uint32_t)pc + 1u, x));
    for (x = 0; x < SQ_SCENES; x++) gr_put(x, 4, g_pc_scene == x ? GL_WHITE : scene_cursor == x ? GL_ON : GL_DIM);
    gr_put(15, 4, GL_ORANGE);
    for (k = 0; k < SQ_PLANES; k++) {
        uint8_t l = sq_plane_len(cfg, (uint8_t)k), pos = l ? (uint8_t)(tr[t].ppos[k] % l) : 0u;
        for (x = 0; x < 16u; x++) {
            uint8_t role;
            if (!l) role = (playing && ev[t].step_index == cfg->start + x) ? GL_DIM : GL_OFF;
            else role = x >= l ? GL_OFF : (playing && ((pos + l - 1u) % l) == x) ? GL_PLAY : GL_FAINT;   /* (the one playing: one behind) */
            gr_put(x, 5u + k, role);
        }
    }
}

static void gr_render_lib(void)
{
    uint32_t i;
    for (i = 0; i < 64u; i++) {
        uint8_t role = i >= lib_n ? GL_OFF : i == lib_wait ? GL_PEND : i == lib_sel ? GL_CURSOR : i == lib_cur ? GL_ON : GL_DIM;
        gr_put(i & 15u, i >> 4, role);
    }
    gr_put(0, 7, GL_BLUE);
    gr_put(1, 7, GL_BLUE);
    gr_put(3, 7, GL_CYAN);
    gr_put(7, 7, playing ? GL_FAINT : GL_ORANGE);
    gr_put(8, 7, lib_ask_over ? GL_PEND : playing || !lib_n ? GL_FAINT : GL_ORANGE);
    gr_put(15, 7, lib_n ? GL_PLAY : GL_FAINT);
}

static void gr_render_ctl(void)
{
    uint32_t i;
    uint8_t sh = gr_shift(), bank = (uint8_t)(selected_track >> 3);
    memset(g_cwant, 0, sizeof g_cwant);
    g_cwant[GC_PLAY] = sh ? GL_ORANGE : playing ? GL_ON : GL_DIM;
    g_cwant[GC_REC] = sh ? (g_view == GV_PROJ ? GL_VIOLET : g_view == GV_LIB ? GL_CYAN : GL_ORANGE) : record_arm ? GL_PLAY : GL_DIM;
    g_cwant[GC_FILL] = sh ? GL_ORANGE : fill_active() ? GL_FILL : GL_DIM;
    g_cwant[GC_UNDO] = sh ? (g_view == GV_FX ? GL_VIOLET : GL_ORANGE) : dice_pending ? GL_PEND : undo_valid ? GL_CURSOR : GL_FAINT;
    g_cwant[GC_VSTEP]  = g_view == GV_STEP  ? GL_CURSOR : g_view == GV_CC   ? GL_VIOLET : g_view == GV_DRUM ? GL_CYAN : g_view == GV_PICK ? GL_YELLOW : sh ? GL_ORANGE : GL_DIM;
    g_cwant[GC_VPERF]  = g_view == GV_PERF  ? GL_CURSOR : g_view == GV_LFO  ? GL_VIOLET : g_view == GV_SONG ? GL_CYAN :
                         g_view == GV_VIAGGIO ? GL_ACCENT : g_view == GV_REGIA ? GL_WHITE : sh ? GL_ORANGE : GL_DIM;
    g_cwant[GC_VTRACK] = g_view == GV_TRACK ? GL_CURSOR : g_view == GV_BEAT || g_view == GV_EUCLID ? GL_VIOLET :
                         g_view == GV_TRACK2 || g_view == GV_TRACK3 ? GL_CYAN : sh ? GL_ORANGE : GL_DIM;
    g_cwant[GC_SHIFT] = g_shift_lock ? GL_YELLOW : sh ? GL_WHITE : g_follow ? GL_CYAN : GL_FAINT;   /* (0.18: cyan while it FOLLOWs) */
    for (i = 0; i < 8u; i++) {
        uint32_t t = (uint32_t)bank * 8u + i;
        g_cwant[GC_TRK0 + i] = t == selected_track ? GL_CURSOR
                             : ((solo_mask >> t) & 1u) ? GL_YELLOW
                             : !track_audible(t) ? GL_MUTED : bank ? GL_BLUE : GL_DIM;
        g_cwant[GC_PAT0 + i] = tr[selected_track].pattern == i ? GL_ON
                             : tr[selected_track].pending_pattern == i ? GL_PEND : sh ? GL_ORANGE : GL_FAINT;
        g_cwant[GC_SCN0 + i] = pending_scene == (scene_cursor & 8u) + i ? GL_PEND : scene_cursor == (scene_cursor & 8u) + i ? GL_ON : sh ? GL_ORANGE : GL_FAINT;
    }
}

static void gr_flush(void)
{
    uint32_t i, budget = GR_BUDGET;
    for (i = 0; i < 128u && budget; i++) {
        if (g_want[i] == g_sent[i]) continue;
        if (midi_tx_room() <= GR_RESERVE) return;
        ctl_send(0x9Fu, i, g_want[i]);
        g_sent[i] = g_want[i];
        budget--;
    }
    for (i = 0; i < 32u && budget; i++) {
        if (g_cwant[i] == g_csent[i]) continue;
        if (midi_tx_room() <= GR_RESERVE) return;
        ctl_send(0xBEu, i, g_cwant[i]);
        g_csent[i] = g_cwant[i];
        budget--;
    }
    if (budget == GR_BUDGET && time_due(fm1_ms, g_next_refresh) && midi_tx_room() > GR_RESERVE) {
        g_next_refresh = fm1_ms + GR_REFRESH_MS;
        i = g_refresh_i++ % 160u;
        if (i < 128u) ctl_send(0x9Fu, i, g_want[i]);
        else ctl_send(0xBEu, i - 128u, g_cwant[i - 128u]);
    }
}

static void grid_service(void)
{
    if (!grid_attached) return;
    if ((uint32_t)(fm1_ms - g_last_seen) > GR_TIMEOUT_MS) { gr_set_attached(0u); return; }

    if (g_hold_pad < 64u && g_hold_flip && (uint32_t)(fm1_ms - g_hold_since) >= SQ_HOLD_MS) {
        project.step[selected_track][tr[selected_track].pattern][g_hold_pad] = g_hold_prev;   /* held: it was a "select", not a toggle */
        g_hold_flip = 0u;
        status_num("STEP ", (uint32_t)g_hold_pad + 1u);
        ui_dirty = grid_dirty = 1u;
    }

    gr_follow_tick();                                   /* 0.18 FOLLOW */
    if (g_view == GV_DRUM) gr_drum_service();
    if (g_view == GV_VIAGGIO) gr_vg_service();

    if (!time_due(fm1_ms, g_next_frame)) return;
    g_next_frame = fm1_ms + GR_FRAME_MS;
    memset(g_want, 0, sizeof g_want);
    switch (g_view) {
    case GV_STEP:  gr_render_step(); break;
    case GV_PERF:  gr_render_perf(); break;
    case GV_TRACK: gr_render_track(); break;
    case GV_CC:    gr_render_cc(); break;
    case GV_LFO:   gr_render_lfo(); break;
    case GV_BEAT:  gr_render_beat(); break;
    case GV_FX:    gr_render_fx(); break;
    case GV_DRUM:  gr_render_drum(); break;
    case GV_SONG:  gr_render_song(); break;
    case GV_TRACK2: gr_render_track2(); break;
    case GV_LIB:   gr_render_lib(); break;
    case GV_EUCLID: gr_render_euclid(); break;
    case GV_TRACK3: gr_render_track3(); break;
    case GV_VIAGGIO: gr_render_viaggio(); break;
    case GV_REGIA: gr_render_regia(); break;
    case GV_PICK:  gr_render_pick(); break;
    default:       gr_render_proj(); break;
    }
    gr_render_ctl();
    gr_flush();
}
