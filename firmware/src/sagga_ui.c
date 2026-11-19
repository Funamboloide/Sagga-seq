/* SPDX-License-Identifier: GPL-3.0-only */
/*
 * SAGGA UI - the screen. Included by dinghy.c after the panel code.
 *
 *   y   0  status      RUN 128 T3 CH3 P1 REC FILL            and the battery on the right (0.5)
 *   y  18  track       LP 1-16 1/16 FWD TR+0 DRUM
 *   y  38  four big parameters, one for each knob K1..K4 (label 16 px, value 32 px)
 *   y 140  context     what the held button is for
 *   y 158  message     what you just did (two lines, wrapped), or the key, the grid view, RCV ...
 *   y 176              ... and the genre and scope of the generators
 *   y 194  states      DICE? EVOLVE SONG TEMP LOOP
 *   y 214  the 16 steps of the page in one slim row (or the tracks, the slots, the FX, the LFOs)
 *
 * (0.4: the strip is one row of small cells, so there is room for two more lines of text.)
 *
 * No title, big letters. The screen is drawn in small pieces, one per pass of the main loop, and only the pieces that
 * changed: a whole-screen redraw is ~110 ms of SPI, and the sequencer clock cannot run meanwhile (at 300 BPM a tick is
 * 8.3 ms: one redraw left the clock 8 ticks behind, "recovered", and asked for another redraw to show the RCV count).
 * A text line costs ~5 ms, a parameter cell ~8 ms, half a row of four steps ~4.5 ms.
 */

#define C_LABEL RGB(135, 135, 150)

enum { UM_STEP = 0, UM_EDIT, UM_ENV, UM_LFO, UM_SEQ, UM_SEL, UM_HOME, UM_FX, UM_PERF, UM_SAVE, UM_ARP, UM_COUNT };   /* (0.17: UM_VIAGGIO gone: the MOSSE are PERF page 3) */

#define UI_LINES 6u
#define UI_COLS  29u                          /* characters on a line (FONT_S is 8 px wide, 232 px) */
typedef struct { char s[32]; uint16_t c; uint8_t bat; } ui_line_t;   /* bat: the battery (line 0), 0 = none */
typedef struct { char lab[18]; char val[10]; uint16_t c; } ui_cell_t;
static ui_line_t ln_want[UI_LINES], ln_shown[UI_LINES];
static ui_cell_t ce_want[4], ce_shown[4];
static uint8_t ln_ok, ce_ok;                  /* bit per line / cell: what is on the glass is known */
static uint32_t cell_shown[16];           /* colour | the note block's bits << 16 (0.12) */
static uint16_t cell_ok;                      /* bit per step cell of the strip */

/* ---- small formatters (a ring of buffers: a few can be alive at once) */
static char fb_[8][16];
static uint8_t fb_i;
static char *fbuf(void) { fb_i = (uint8_t)((fb_i + 1u) & 7u); return fb_[fb_i]; }
static const char *f_u(uint32_t v) { char *b = fbuf(), *p = put_u(b, v); finish(p); return b; }
static const char *f_cc(uint32_t cc) { return cc == SQ_CC_BEND ? "BEND" : cc == SQ_CC_AT ? "AFTERT" : f_u(cc); }   /* 0.10 */
static const char *f_i(int32_t v) { char *b = fbuf(), *p = put_i(b, v); finish(p); return b; }
static const char *f_pct(uint32_t v) { char *b = fbuf(), *p = put_u(b, v); p = put_s(p, "%"); finish(p); return b; }
static const char *f_gate(uint8_t v)
{
    char *b = fbuf(), *p = b;
    if (v <= 100u) { p = put_u(p, v); p = put_s(p, "%"); }
    else if (v == 101u) p = put_s(p, "1.5 STEP");
    else { p = put_u(p, (uint32_t)v - 100u); p = put_s(p, " STEP"); }
    finish(p); return b;
}
static const char *f_spct(int32_t v) { char *b = fbuf(), *p = put_i(b, v); p = put_s(p, "%"); finish(p); return b; }
static const char *f_pre(const char *pre, uint32_t v) { char *b = fbuf(), *p = put_s(b, pre); p = put_u(p, v); finish(p); return b; }
static const char *f_note(uint8_t n)
{
    char *b = fbuf(), *p = b;
    if (n == SQ_NOTE_NONE) return "--";
    p = put_note(p, n);
    finish(p);
    return b;
}
/* the written note, and the note the key makes of it when they differ: "C#3>D3" */
static const char *f_note_key(uint32_t t, uint8_t n)
{
    char *b = fbuf(), *p = b;
    uint8_t o;
    if (n == SQ_NOTE_NONE) return "--";
    p = put_note(p, n);
    o = key_note(t, n);
    if (o != n) { p = put_s(p, ">"); p = put_note(p, o); }
    finish(p);
    return b;
}
static const char *f_onoff(uint32_t on) { return on ? "ON" : "OFF"; }

static void str_copy(char *d, const char *s, uint32_t cap)
{
    uint32_t n = 0;
    while (s[n] && n < cap - 1u) { d[n] = s[n]; n++; }
    d[n] = 0;
}
static int ui_str_eq(const char *a, const char *b)
{
    while (*a && *a == *b) { a++; b++; }
    return *a == *b;
}

static void ui_line(uint32_t i, const char *s, uint16_t c) { str_copy(ln_want[i].s, s, UI_COLS + 1u); ln_want[i].c = c; ln_want[i].bat = 0u; }

/* ---- 0.5: the battery. Three bars on the thresholds of the stock firmware (as Felucca reads the divider on ADC ch3:
 * 531 / 561 / 591), a little hysteresis so that it does not flicker; a bolt beside it while a USB host powers the FM-1
 * (it charges; the bars read a little high then). One line of status when it runs low without USB. */
#define UI_BAT_COLS 25u                       /* line 0 keeps this many characters; the battery takes the rest */
static uint8_t batt_bars(void)
{
    static const int32_t TH[3] = {531, 561, 591};
    static uint8_t lvl = 3u;
    int32_t r = sq_batt_raw;
    if (r <= 0) return 3u;                    /* (not read yet) */
    while (lvl > 0u && r < TH[lvl - 1u] - 3) lvl--;
    while (lvl < 3u && r >= TH[lvl] + 3) lvl++;
    return lvl;
}
static uint8_t batt_usb(void)
{
    sq_usb_stats_t u;
    usb_stats(&u);
    return (u.config && !u.suspended) ? 1u : 0u;
}
static uint8_t batt_code(void) { return (uint8_t)(1u + batt_bars() + (batt_usb() ? 4u : 0u)); }

static void batt_watch(void)                  /* every 30 ms (update_leds): a warning once when it gets low */
{
    static uint8_t warned;
    uint8_t low = (batt_bars() == 0u && !batt_usb()) ? 1u : 0u;
    if (low && !warned) status_msg("BATTERY LOW: CONNECT USB");
    warned = low;
}

/* drawn into the canvas of line 0 (232 x 16), at its right end */
static void ui_draw_batt(uint8_t code)
{
    static const uint8_t BOLT[8] = {0x0C, 0x18, 0x30, 0x7C, 0x18, 0x30, 0x60, 0x40};   /* 7 x 8, bit 6 = the left column */
    uint8_t bars = (uint8_t)((code - 1u) & 3u), usb = (uint8_t)((code - 1u) >> 2);
    uint16_t edge = bars == 0u && !usb ? C_PLAY : C_LABEL, fill = bars == 1u ? C_WARN : C_ON;
    int32_t x0 = 209, y0 = 3, i, r;
    cv_rect(x0, y0, 20, 1, edge);             /* the body, 20 x 10 */
    cv_rect(x0, y0 + 9, 20, 1, edge);
    cv_rect(x0, y0, 1, 10, edge);
    cv_rect(x0 + 19, y0, 1, 10, edge);
    cv_rect(x0 + 20, y0 + 3, 2, 4, edge);     /* the tip */
    for (i = 0; i < (int32_t)bars; i++) cv_rect(x0 + 2 + 6 * i, y0 + 2, 4, 6, fill);
    if (usb)
        for (r = 0; r < 8; r++)
            for (i = 0; i < 7; i++)
                if (BOLT[r] & (0x40u >> i)) cv_rect(x0 - 9 + i, y0 + 1 + r, 1, 1, C_CYAN);
}

/* a message on two lines: broken at the last space that fits */
static void ui_wrap(const char *s, uint16_t c)
{
    uint32_t n = 0u, cut = 0u;
    while (s[n]) n++;
    if (n <= UI_COLS) { ui_line(3, s, c); ui_line(4, "", c); return; }
    for (cut = UI_COLS; cut > 0u && s[cut] != ' '; cut--) {}
    if (!cut) cut = UI_COLS;
    {
        char a[UI_COLS + 1u];
        uint32_t i;
        for (i = 0; i < cut; i++) a[i] = s[i];
        a[cut] = 0;
        ui_line(3, a, c);
    }
    while (s[cut] == ' ') cut++;
    ui_line(4, s + cut, c);
}
static void ui_cell(uint32_t i, const char *lab, const char *val, uint16_t c)
{
    str_copy(ce_want[i].lab, lab, sizeof ce_want[i].lab);
    str_copy(ce_want[i].val, val, sizeof ce_want[i].val);
    ce_want[i].c = c;
}
/* 0.12 PICK: the label of cell i, without the focus mark */
static const char *ui_cell_label(uint32_t i)
{
    const char *l = ce_want[i & 3u].lab;
    if (l[0] == '>' && (l[1] == ' ' || l[1] == '-')) l += 2;
    return l;
}

static uint8_t ui_mode(void)
{
    uint32_t h = eff_held();                                        /* (0.12: the window open counts as held) */
    if (save_down) return UM_SAVE;
    if (h & (1u << BTN_HOME)) return UM_HOME;
    if (h & (1u << BTN_EDIT)) return UM_EDIT;
    if (h & (1u << BTN_ENV)) return UM_ENV;
    if (h & (1u << BTN_LFO)) return UM_LFO;
    if (h & (1u << BTN_SEQ)) return UM_SEQ;
    if (h & (1u << BTN_FX)) return UM_FX;
    if (h & (1u << BTN_ARP)) return UM_ARP;
    if (h & (1u << BTN_GLO)) return UM_PERF;                       /* 0.12: GLO held: its pages (LIVE, TRACK LIVE, the MOSSE) */
    if (perf_mode && (h & (1u << BTN_SEL))) return UM_PERF;       /* PERF + SEL: TRACK LIVE's knobs, the solos (0.12) */
    if (h & (1u << BTN_SEL)) return UM_SEL;
    if (perf_mode) return UM_PERF;
    return UM_STEP;
}

/* the page of GLO shown (PERF + SEL: TRACK LIVE) */
static uint8_t ui_perf_pp(void)
{
    uint32_t hh = in_held();
    return (perf_mode && (hh & (1u << BTN_SEL)) && !(hh & (1u << BTN_GLO))) ? 1u : perf_page;
}

/* the text of the screen for the moment: four lines and four cells */
static void ui_build(void)
{
    char *const b = ui_b, *p;                  /* (0.21: 64 bytes that put_c ends, not the stack) */
    uint8_t mode = ui_mode();
    uint32_t t = selected_track, i;
    sq_track_cfg_t *cfg = &project.track[t];
    sq_step_t *s = &project.step[t][tr[t].pattern][cursor_step];
    uint16_t on = (s->flags & SQ_STEP_ON) ? C_WHITE : C_LABEL;

    /* line 0: the transport */
    p = b;
    p = put_s(p, playing ? "RUN " : "STOP ");
    if (project.clock_mode == SQ_CLOCK_MASTER) p = put_u(p, project.bpm); else p = put_s(p, "EXT");
    p = put_s(p, " T"); p = put_u(p, t + 1u);
    p = put_s(p, " CH"); p = put_u(p, (uint32_t)track_ch(t) + 1u);
    p = put_s(p, " P"); p = put_u(p, (uint32_t)tr[t].pattern + 1u);
    if (record_arm) p = put_s(p, rec_quant ? " RECQ" : " RECF");
    if (fill_active()) p = put_s(p, " FILL");
    finish(p);
    if ((uint32_t)(p - b) > UI_BAT_COLS - 1u) {                 /* (room for the bolt: the short way) */
        p = b;
        p = put_s(p, playing ? "RUN " : "STOP ");
        if (project.clock_mode == SQ_CLOCK_MASTER) p = put_u(p, project.bpm); else p = put_s(p, "EXT");
        p = put_s(p, " T"); p = put_u(p, t + 1u);
        p = put_s(p, " C"); p = put_u(p, (uint32_t)track_ch(t) + 1u);
        p = put_s(p, " P"); p = put_u(p, (uint32_t)tr[t].pattern + 1u);
        if (record_arm) p = put_s(p, rec_quant ? " RQ" : " RF");
        if (fill_active()) p = put_s(p, " FILL");
        finish(p);
    }
    b[UI_BAT_COLS - 1u] = 0;
    ui_line(0, b, playing ? C_PLAY : C_WHITE);
    ln_want[0].bat = batt_code();

    /* line 1: the track */
    p = b;
    if (cfg->start) { p = put_s(p, "LP "); p = put_u(p, (uint32_t)cfg->start + 1u); p = put_s(p, "-"); p = put_u(p, cfg->length); }
    else { p = put_s(p, "LEN "); p = put_u(p, cfg->length); }
    if (len_pend[selected_track]) { p = put_s(p, ">"); p = put_u(p, len_pend[selected_track]); }   /* 0.11: the length that waits for the bar */
    p = put_s(p, " "); p = put_s(p, div_name(cfg->division));
    p = put_s(p, " "); p = put_s(p, dir_name(cfg->direction));
    if (cfg->transpose) { p = put_s(p, " TR"); p = put_i(p, cfg->transpose); }
    if (cfg->octave) { p = put_s(p, " OCT"); p = put_i(p, cfg->octave); }
    if (cfg->chord) { p = put_s(p, " "); p = put_s(p, sq_chord_shape_name(cfg->chord)); }
    if (SQ_CHORD_MODE(cfg->chord_mode) != SQ_CHORD_BLOCK) { p = put_s(p, " "); p = put_s(p, chord_name(SQ_CHORD_MODE(cfg->chord_mode))); }
    if (track_drum(t)) p = put_s(p, " DRUM");
    else if (track_in_key(t)) p = put_s(p, " KEY");
    if (cfg->flags & SQ_TF_FOLLOW) p = put_s(p, " FOL");
    if (cfg->flags & SQ_TF_EUC) p = put_s(p, " EUC");
    if (cfg->algo) { p = put_s(p, " "); p = put_s(p, ALGO_NAME[cfg->algo < SQ_ALGOS ? cfg->algo : 0u]); }
    if (solo_mask & (1u << t)) p = put_s(p, " SOLO");
    else if (!track_audible(t)) p = put_s(p, " MUTE");
    finish(p);
    ui_line(1, b, track_audible(t) ? C_ON : SQ_C_DIM);

    for (i = 0; i < 4u; i++) ui_cell(i, "", "", C_WHITE);
    b[0] = 0;

    switch (mode) {
    case UM_SAVE:                                     /* SAVE: K1 the MASTER knob, K2 the remote, K3 snapshot tempo, slot; page 2; 0.12 page 3 SYSTEM; 0.13 page 4 LIVE IN */
        if (save_page == 4u) {                        /* 0.26 CLICK: the metronome, the count before a recording, where it sounds, how loud */
            const sq_ext_t *x = &project.ext;
            static const char *const CK[SQ_CLICKS] = {"OFF", "REC", "PLAY"};
            ui_cell(0, "CLICK", CK[x->click < SQ_CLICKS ? x->click : 0u], x->click ? (click_wanted() ? C_ON : C_ACCENT) : SQ_C_DIM);
            ui_cell(1, "COUNT IN", !x->count_in ? "OFF" : x->count_in == 1u ? "1 BAR" : "2 BARS", cnt_on ? C_WARN : x->count_in ? C_ACCENT : SQ_C_DIM);
            ui_cell(2, "CLICK OUT", x->click_out ? f_pre("CH ", x->click_out) : "FM-1", x->click_out ? C_ACCENT : C_WHITE);
            ui_cell(3, "LEVEL", f_u(sq_click_level(x)), C_WHITE);
            p = b; p = put_s(p, "SAVE 5/5  CLICK");
            if (x->click_out) { char nm[5]; sq_note_name(sq_click_note(x), nm); p = put_s(p, "  NOTE "); p = put_s(p, nm); p = put_s(p, " (SEL+K4)"); }
            else p = put_s(p, "  ON THE BEATS OF THE METRE");
            finish(p);
            ui_line(2, b, C_WARN);
            break;
        }
        if (save_page == 3u) {
            const sq_ext_t *x = &project.ext;
            static const char *const KB[SQ_KBS] = {"OFF", "TRANSPOSE", "TRANS <C3", "CHORDS", "CHORD <C3"};   /* (0.26: the chords; until 0.25 OFF ALL SPLIT C3. A cell holds nine letters) */
            ui_cell(0, "MOTION", x->motion_bars == 1u ? "1 BAR" : x->motion_bars == 2u ? "2 BARS" : x->motion_bars ? "4 BARS" : "OFF", x->motion_bars ? (record_arm ? C_WARN : C_ON) : SQ_C_DIM);
            ui_cell(1, "KEYBOARD", KB[x->kb_mode < SQ_KBS ? x->kb_mode : 0u], x->kb_mode ? C_ACCENT : SQ_C_DIM);
            ui_cell(2, "KEYB CH", x->kb_ch ? f_u(x->kb_ch) : "ANY", x->kb_mode ? C_WHITE : SQ_C_DIM);
            ui_cell(3, "MIDI IN", x->in_thru ? "ALWAYS" : "REC ONLY", x->in_thru ? C_ON : SQ_C_DIM);
            ui_line(2, x->motion_bars && record_arm ? "SAVE 4/5  MOTION REC: FX + K" : "SAVE 4/5  LIVE IN", C_WARN);
            break;
        }
        if (save_page == 2u) {                        /* the USB link (was HOME + SEL), the button lights */
            sq_usb_stats_t u;
            usb_stats(&u);
            ui_cell(0, usb_ports_want != usb_ports ? "USB PORTS >" : "USB PORTS", usb_ports_want > 1u ? "2" : "1",
                    usb_ports_want != usb_ports ? C_WARN : u.up && u.config && !u.suspended ? C_ON : C_WARN);
            ui_cell(1, "LIGHTS", LIGHTS_NAME[lights_level()], lights_level() ? C_WHITE : SQ_C_DIM);
            p = b; p = put_u(p, u.queued); p = put_s(p, "/64"); finish(p);
            ui_cell(2, "OUT QUEUE", b, u.queued > 48u ? C_WARN : C_WHITE);
            ui_cell(3, "DROPPED", f_u(u.dropped), u.dropped ? C_WARN : C_WHITE);
            p = b; p = put_s(p, "SAVE 3/5  MIDI OUT "); p = put_u(p, diag_out_ps); p = put_s(p, "/S IN "); p = put_u(p, diag_in_ps);
            p = put_s(p, "/S WAIT "); p = put_u(p, u.wait_ms); finish(p);
            ui_line(2, b, C_WARN);
            break;
        }
        if (save_page) {
            uint8_t ch = track_ch(t);
            ui_cell(0, "CC LEAD MS", f_u(project.live.cc_lead_ms), project.live.cc_lead_ms ? C_ACCENT : SQ_C_DIM);
            ui_cell(1, "SONG TEMPO", f_onoff(project.live.song_tempo), project.live.song_tempo ? C_ON : SQ_C_DIM);
            ui_cell(2, f_pre("DEVICE CH", (uint32_t)ch + 1u), sq_device_name(project.device[ch]), project.device[ch] ? C_ACCENT : C_WHITE);
            ui_cell(3, "LONG PATTERNS", project.gen.lib_len == SQ_LL_PHRASE ? "PHRASE" : "COPY", project.gen.lib_len ? C_ACCENT : C_WHITE);
            ui_line(2, "SAVE 2/5  LOCKS AHEAD, SONG TEMPO, SYNTH", C_WARN);
            break;
        }
        ui_cell(0, "MASTER KNOB", MK_NAME[project.live.master_fn < SQ_MKS ? project.live.master_fn : 0u], C_WHITE);
        ui_cell(1, "REMOTE", project.live.remote_mode == SQ_RM_OFF ? "OFF" : project.live.remote_mode == SQ_RM_14 ? "CH 14" : "13+14",
                project.live.remote_mode == SQ_RM_OFF ? SQ_C_DIM : C_ON);
        ui_cell(2, "SNAP TEMPO", f_onoff(project.live.snap_tempo), project.live.snap_tempo ? C_ON : SQ_C_DIM);
        ui_cell(3, "PROFILE", vg_profile_name(), vg_profile ? C_ACCENT : C_WHITE);
        p = b; p = put_s(p, "SLOT "); p = put_u(p, (uint32_t)slot_cur + 1u); p = put_s(p, " ");
        p = put_s(p, slot_info[slot_cur].ok ? (slot_info[slot_cur].seq == store_seq ? "NEWEST" : "USED") : "EMPTY");
        if (slot_info[slot_cur].ok) { p = put_s(p, " "); p = put_u(p, (slot_info[slot_cur].len + 512u) / 1024u); p = put_s(p, "K"); }
        p = put_s(p, "  W16: SAVE JOURNEY"); finish(p);
        ui_line(2, b, C_WARN);
        break;
    case UM_HOME:
        if (home_page == 0u) {
            ui_cell(0, "CHANNEL", f_u((uint32_t)track_ch(t) + 1u), cfg->channel >= ch_limit() ? C_WARN : C_WHITE);
            ui_cell(1, len_pend[selected_track] ? "LENGTH>BAR" : "LENGTH", f_u(len_shown(selected_track)), len_pend[selected_track] ? C_WARN : C_WHITE);
            ui_cell(2, "STEP", div_name(cfg->division), C_WHITE);
            ui_cell(3, track_in_key(t) ? "TRANSP STEPS" : "TRANSPOSE", f_i(cfg->transpose), cfg->transpose ? C_WHITE : SQ_C_DIM);
            ui_line(2, (sl_on & (1u << t)) ? "HOME 1/8 TRACK   STEP LOOP ON (FX+B11: OFF)" : "HOME 1/8 TRACK   ALG: LOOP START", C_WARN);
        } else if (home_page == 1u) {
            ui_cell(0, "DIRECTION", dir_name(cfg->direction), C_WHITE);
            ui_cell(1, "SWING", f_pct(cfg->swing), cfg->swing > SQ_SWING_MIN ? C_WHITE : SQ_C_DIM);
            ui_cell(2, "OCTAVE", f_i(cfg->octave), cfg->octave ? C_ACCENT : SQ_C_DIM);
            ui_cell(3, "FOLLOW", f_onoff(cfg->flags & SQ_TF_FOLLOW), (cfg->flags & SQ_TF_FOLLOW) ? (project.gen.harm_on ? C_ON : C_WARN) : SQ_C_DIM);
            ui_line(2, "HOME 2/8 PLAY  GLO+SEL+OCT: THE OCTAVE LIVE", C_WARN);
        } else if (home_page == 2u) {
            ui_cell(0, "KEY SLOT", f_u((uint32_t)project.key_cur + 1u), C_ACCENT);
            ui_cell(1, "ROOT", sq_root_name(project.key_root), project.key_scale ? C_ACCENT : SQ_C_DIM);
            ui_cell(2, "SCALE", sq_scale_name(project.key_scale), project.key_scale ? C_ACCENT : SQ_C_DIM);
            ui_cell(3, "SHIFT", f_i(project.key_shift), project.key_shift ? C_WHITE : SQ_C_DIM);
            ui_line(2, "HOME 3/8 KEY  16 SLOTS; HOME+ARP: BAKE", C_WARN);
        } else if (home_page == 3u) {                                /* 0.10: mode, role, chord, key slot */
            ui_cell(0, "MODE", track_mode_name(t), track_mode(t) ? C_ON : SQ_C_DIM);
            ui_cell(1, "ROLE", sq_role_name(cfg->role), cfg->role ? C_ACCENT : SQ_C_DIM);
            ui_cell(2, "CHORD", sq_chord_shape_name(cfg->chord), cfg->chord ? C_ACCENT : SQ_C_DIM);
            ui_cell(3, "KEY SLOT", cfg->key_slot == SQ_KEY_FOLLOW ? "FOLLOWS" : f_u((uint32_t)cfg->key_slot + 1u), cfg->key_slot == SQ_KEY_FOLLOW ? SQ_C_DIM : C_ACCENT);
            ui_line(2, track_break(t) ? "HOME 4/8 BREAK: SLICES FROM THE PEN NOTE" : "HOME 4/8 TRACK  ROLE: LIBRARY, COOK, MOSSE", C_WARN);
        } else if (home_page == 6u) {                                /* 0.10 TIMING */
            int8_t dl = cfg->delay_ms;
            uint8_t chain = chain_mode(t), pp = tr[t].pattern;
            ui_cell(0, "DELAY MS", f_i(dl), dl ? C_ACCENT : SQ_C_DIM);
            {
                char cb[10], *q = cb;
                q = put_s(q, "P"); q = put_u(q, (uint32_t)(pp & ~1u) + 1u); q = put_s(q, "+"); q = put_u(q, (uint32_t)(pp | 1u) + 1u); finish(q);
                ui_cell(1, "CHAIN", chain == 2u ? "LIST" : chain ? cb : "OFF", chain ? C_ACCENT : SQ_C_DIM);
            }
            if (track_tape(t)) {
                ui_cell(2, "TAPE BARS", f_u(cfg->tape.bars), C_ACCENT);
                ui_cell(3, "TAPE QUANT", f_pct(cfg->tape.quant), C_WHITE);
            } else {                                                 /* 0.15 GROOVE */
                const sq_trackx_t *gx = &project.ext.track[t];
                ui_cell(2, "GROOVE", sq_groove_name(gx->groove), gx->groove ? C_ACCENT : SQ_C_DIM);
                ui_cell(3, "GROOVE AMT", f_pct(gx->groove_amt), gx->groove && gx->groove_amt ? C_WHITE : SQ_C_DIM);
            }
            ui_line(2, chain == 2u ? "HOME 7/8 TIMING  CHAIN: HOME 8" : chain ? "HOME 7/8 TIMING  CHAIN: TWO PATTERNS AS ONE" : dl < 0 ? "HOME 7/8 TIMING  - EARLY: A SLOW SYNTH" : dl > 0 ? "HOME 7/8 TIMING  + LATE: A FAST SYNTH" : track_tape(t) ? "HOME 7/8 TIMING  K1 LATENCY K2 CHAIN K3 K4 TAPE" : "HOME 7/8 TIMING  K1 LATENCY K2 CHAIN K3 K4 GROOVE", C_WARN);
        } else if (home_page == 7u) {                                /* 0.13 CHAIN LIST */
            const sq_trackx_t *cx = &project.ext.track[t];
            uint8_t e = chain_edit < cx->chain_n ? chain_edit : (uint8_t)(cx->chain_n - 1u), k;
            uint16_t on = cx->chain_on ? C_ACCENT : SQ_C_DIM;
            ui_cell(0, "LENGTH", f_u(cx->chain_n), on);
            p = b; p = put_u(p, (uint32_t)e + 1u); p = put_s(p, "/"); p = put_u(p, cx->chain_n); finish(p);
            ui_cell(1, "ENTRY", b, cx->chain_on ? C_WHITE : SQ_C_DIM);
            ui_cell(2, "PATTERN", f_pre("P", (uint32_t)cx->chain_pat[e] + 1u), on);
            ui_cell(3, "TIMES", f_pre("X", cx->chain_rep[e]), cx->chain_rep[e] > 1u ? on : SQ_C_DIM);
            p = b; p = put_s(p, cx->chain_on ? "HOME 8/8 " : "HOME 8/8 OFF ");
            for (k = 0; k < cx->chain_n; k++) {
                uint8_t now = cx->chain_on && playing && chain_pos[t] == k;
                p = put_s(p, k == e ? ">" : now ? "*" : " ");
                p = put_u(p, (uint32_t)cx->chain_pat[k] + 1u);
                if (cx->chain_rep[k] > 1u) { p = put_s(p, "X"); p = put_u(p, cx->chain_rep[k]); }
            }
            finish(p);
            ui_line(2, b, C_WARN);
        } else if (home_page == 4u) {
            static const char *const LAB[SQ_PLANES] = {"NOTE LOOP", "VEL LOOP", "GATE LOOP"};
            uint8_t ch = track_ch(t), pc = project.scene[scene_cursor].pc[ch];
            for (i = 0; i < SQ_PLANES; i++)
                ui_cell(i, LAB[i], cfg->plen[i] ? f_u(cfg->plen[i]) : "TRACK", cfg->plen[i] ? C_ACCENT : SQ_C_DIM);
            ui_cell(3, f_pre("PROGRAM SC", (uint32_t)scene_cursor + 1u), pc > 127u ? "--" : f_u((uint32_t)pc + 1u), pc > 127u ? SQ_C_DIM : C_WHITE);
            p = b; p = put_s(p, "HOME 5/8 LOOPS  PC CH"); p = put_u(p, (uint32_t)ch + 1u); finish(p);
            ui_line(2, b, C_WARN);
        } else {
            static const char *const ET[SQ_ECHO_TIMES] = {"1/32", "1/16", "1/8T", "1/16.", "1/8", "1/4T", "1/8.", "1/4"};
            static const char *const OP[SQ_OCT_PATTERNS] = {"ALT", "RANDOM", "3RD", "4TH"};
            static const char *const GF[SQ_GATE_FACTORS] = {"X1/4", "X1/2", "X3/4", "X1", "X3/2", "X2", "X4"};
            static const char *const GX[SQ_GATE_FIXED] = {"OFF", "1/32", "1/16", "1/8", "1/4", "1/2", "1 BAR", "2 BARS"};
            static const char *const GL[SQ_GLITCHES] = {"MIX", "STUTTER", "RISE", "JUMP", "CUT"};
            const sq_track_cfg_t *mv = mfx_view(t);                       /* 0.19: the effect K1 shows, playing or READY */
            uint8_t fx = mv->mfx < SQ_MFXS ? mv->mfx : 0u, plays = mfx_on(t, fx);
            uint16_t on = fx ? C_WHITE : SQ_C_DIM;
            const char *l2 = "-", *l3 = "-", *l4 = "-", *v2 = "-", *v3 = "-", *v4 = "-";
            ui_cell(0, !fx ? "MIDI FX" : plays ? "MIDI FX ON" : "MIDI FX READY", MFX_NAME[fx], !fx ? SQ_C_DIM : plays ? C_ACCENT : C_WHITE);
            switch (fx) {                                                  /* 0.20: each effect its three knobs */
            case SQ_MFX_HARM:     l2 = track_in_key(t) ? "INTERVAL STEPS" : "INTERVAL SEMI"; v2 = f_i(mv->mfx_amt); l4 = "VOICE VEL"; v4 = f_pct(mv->mfx_fb); break;
            case SQ_MFX_OCTAVE:   l2 = "OCTAVES"; v2 = f_i(mv->mfx_amt); l3 = "WHICH STEPS"; v3 = OP[mv->mfx_time & 3u]; break;
            case SQ_MFX_ECHO:     l2 = "REPEATS"; v2 = f_i(mv->mfx_amt); l3 = "ECHO TIME"; v3 = ET[mv->mfx_time < SQ_ECHO_TIMES ? mv->mfx_time : 6u];
                                  l4 = "ECHO KEEPS"; v4 = f_pct(mv->mfx_fb); break;
            case SQ_MFX_VELOCITY: l2 = "AMOUNT"; v2 = f_i(mv->mfx_amt); break;
            case SQ_MFX_CHANCE:   l2 = "CHANCE"; v2 = f_pct((uint32_t)mv->mfx_amt); l3 = "EACH"; v3 = mv->mfx_time ? "STEP" : "NOTE"; break;
            case SQ_MFX_RANDOM:   l2 = track_in_key(t) ? "NOTE STEPS" : "NOTE SEMI"; v2 = f_pre("+-", (uint32_t)mv->mfx_amt);
                                  l3 = "VELOCITY"; v3 = f_pre("+-", mv->mfx_time); l4 = "HOW OFTEN"; v4 = f_pct(mv->mfx_fb); break;
            case SQ_MFX_FILTER:   l2 = "LOWEST"; v2 = f_note((uint8_t)mv->mfx_amt); l3 = "HIGHEST"; v3 = f_note(mv->mfx_time);
                                  l4 = "ONE IN"; v4 = mv->mfx_fb > 1u ? f_u(mv->mfx_fb) : "ALL"; break;
            case SQ_MFX_GATE:     l2 = "LENGTH"; v2 = GF[clamp_i32(mv->mfx_amt, -3, 3) + 3]; l3 = "FIXED"; v3 = GX[mv->mfx_time < SQ_GATE_FIXED ? mv->mfx_time : 0u];
                                  l4 = "HUMAN"; v4 = f_pre("+-", mv->mfx_fb); break;
            case SQ_MFX_GLITCH:   l2 = "HOW OFTEN"; v2 = f_pct((uint32_t)mv->mfx_amt); l3 = "KIND"; v3 = GL[mv->mfx_time < SQ_GLITCHES ? mv->mfx_time : 0u];
                                  l4 = "PIECES"; v4 = f_u(mv->mfx_fb); break;
            default: break;
            }
            ui_cell(1, l2, v2, l2[0] != '-' ? on : SQ_C_DIM);
            ui_cell(2, l3, v3, l3[0] != '-' ? on : SQ_C_DIM);
            ui_cell(3, l4, v4, l4[0] != '-' ? on : SQ_C_DIM);
            if (!mfx_count(t)) ui_line(2, echo_global ? "HOME 6/8 MIDI FX  ECHO ALL ON" : "HOME 6/8 MIDI FX", C_WARN);
            else {                                                         /* 0.19: the chain, in the order it plays */
                p = b; p = put_s(p, "HOME 6/8 FX "); p = mfx_chain_put(p, t);
                if (echo_global && !mfx_on(t, SQ_MFX_ECHO)) p = put_s(p, " +ECHO ALL");
                finish(p);
                ui_line(2, b, C_WARN);
            }
        }
        break;
    case UM_EDIT:
        if (in_held() & (1u << BTN_SEL)) {                                   /* 0.12 EDIT + SEL: the notes 1-4 of the step, a knob each */
            static const char *const NL[4] = {"NOTE 1", "NOTE 2", "NOTE 3", "NOTE 4"};
            uint32_t k;
            for (k = 0; k < 4u; k++)
                ui_cell(k, NL[k], s->note[k] == SQ_NOTE_NONE ? "--" : f_note_key(t, s->note[k]), s->note[k] == SQ_NOTE_NONE ? SQ_C_DIM : on);
            p = b; p = put_s(p, "EDIT+SEL STEP "); p = put_u(p, (uint32_t)cursor_step + 1u);
            if (s->note[4] != SQ_NOTE_NONE) {                                /* 0.28: the notes 5 and 6 (played in, not on a knob) */
                p = put_s(p, "  5 "); p = put_note(p, s->note[4]);
                if (s->note[5] != SQ_NOTE_NONE) { p = put_s(p, " 6 "); p = put_note(p, s->note[5]); }
            } else p = put_s(p, "  A KNOB UNDER 0: NO NOTE");
            finish(p);
            ui_line(2, b, C_WARN);
            break;
        }
        ui_cell(0, "GATE", f_gate(s->length), on);
        ui_cell(1, "CONDITION", sq_cond_name(s->condition), on);
        ui_cell(2, "NUDGE", f_spct(s->nudge), on);
        ui_cell(3, "RAMP", f_i(s->ramp), on);
        p = b; p = put_s(p, "EDIT STEP "); p = put_u(p, (uint32_t)cursor_step + 1u); if (s->flags & SQ_STEP_LOCK) p = put_s(p, " LOCK"); if (s->flags & SQ_STEP_XOFF) p = put_s(p, " PLAIN"); if (s->flags & SQ_STEP_TIE) p = put_s(p, " TIE"); if (s->flags & SQ_STEP_SLIDE) p = put_s(p, " SLIDE"); finish(p);
        ui_line(2, b, C_WARN);
        break;
    case UM_ENV: {                                    /* 0.10: one lane a page (OCT turns it): value, CC, base, mode */
        uint32_t n = env_lane < SQ_LANES ? env_lane : 0u;
        uint8_t cc = cfg->lane_cc[n], fl = cfg->lane_flags[n], dev = project.device[track_ch(t)];
        const char *nm = cc <= SQ_CC_MAX ? sq_cc_name(dev, cc) : "";
        char lab[18], *q;
        uint16_t lc = cc == SQ_LANE_NONE ? SQ_C_DIM : C_WHITE;
        int32_t sl;
        q = lab; q = put_s(q, "LOCK STEP "); q = put_u(q, (uint32_t)cursor_step + 1u); finish(q);
        sl = s->lane[n] == SQ_LANE_NONE ? lane_slide_at(t, project.step[t][tr[t].pattern], cursor_step, n) : -1;
        ui_cell(0, lab, s->lane[n] == SQ_LANE_NONE ? (sl >= 0 ? f_u((uint32_t)sl) : "--") : f_u(s->lane[n]), s->lane[n] == SQ_LANE_NONE ? (sl >= 0 ? C_LABEL : SQ_C_DIM) : (cc == SQ_LANE_NONE ? SQ_C_DIM : C_ACCENT));
        q = lab; q = put_s(q, (fl & SQ_LF_NRPN) ? "NRPN " : "CC "); if (nm[0]) q = put_s(q, nm); finish(q);
        if ((fl & SQ_LF_NRPN) && cc <= 127u) { char v[10], *r = v; r = put_u(r, cfg->lane_hi[n]); r = put_s(r, ":"); r = put_u(r, cc); finish(r); ui_cell(1, lab, v, lc); }
        else ui_cell(1, lab, cc == SQ_LANE_NONE ? "OFF" : f_cc(cc), lc);
        ui_cell(2, "BASE", cfg->lane_base[n] == SQ_LANE_NONE ? "--" : f_u(cfg->lane_base[n]), cfg->lane_base[n] == SQ_LANE_NONE ? SQ_C_DIM : lc);
        ui_cell(3, "MODE", (fl & SQ_LF_NRPN) ? "NRPN" : (fl & (SQ_LF_SLIDE | SQ_LF_TRIGLESS)) == (SQ_LF_SLIDE | SQ_LF_TRIGLESS) ? "SLIDE+TL" : (fl & SQ_LF_SLIDE) ? "SLIDE" : (fl & SQ_LF_TRIGLESS) ? "TRIGLESS" : "NORMAL", fl ? C_ACCENT : SQ_C_DIM);
        p = b; p = put_s(p, "ENV LANE "); p = put_u(p, n + 1u); p = put_s(p, "/"); p = put_u(p, SQ_LANES); p = put_s(p, "  ");   /* (0.28: eight) */
        p = put_s(p, learn_kind ? "LEARN: MOVE A SYNTH KNOB" : (record_arm && playing) ? "REC: K1 WRITES THE STEPS" : "ENV+REC: LEARN THE CC"); finish(p);
        ui_line(2, b, learn_kind ? C_PLAY : C_WARN);
        break;
    }
    case UM_LFO: {
        const sq_lfo_t *l = &project.lfo[lfo_sel];
        uint16_t lc = l->enabled ? C_WHITE : SQ_C_DIM;
        if (lfo_page == 0u) {
            ui_cell(0, "SHAPE", lfo_shape_name(l->shape), lc);
            ui_cell(1, "RATE", lfo_rate_name(l->rate), lc);
            ui_cell(2, "DEPTH", f_u(l->depth), lc);
            ui_cell(3, l->dest == SQ_LD_CC ? "CENTER" : "(CENTER)", f_u(l->center), l->dest == SQ_LD_CC ? lc : SQ_C_DIM);
        } else if (lfo_page == 1u) {
            ui_cell(0, "DESTINATION", lfo_dest_name(l->dest), lc);
            ui_cell(1, l->dest == SQ_LD_CC ? "CHANNEL" : "TRACK", f_u((uint32_t)l->target + 1u), lc);
            ui_cell(2, "CC NUMBER", l->dest == SQ_LD_CC ? f_cc(l->param) : "-", l->dest == SQ_LD_CC ? lc : SQ_C_DIM);
            ui_cell(3, "PHASE", f_u(l->phase), lc);
        } else if (lfo_page == 2u) {
            const sq_lfox_t *x = &project.ext.lfo[lfo_sel];
            ui_cell(0, "ENABLED", f_onoff(l->enabled), l->enabled ? C_ON : SQ_C_DIM);
            ui_cell(1, "RESTART", f_onoff(l->flags & SQ_LF_RETRIG), (l->flags & SQ_LF_RETRIG) ? C_ON : SQ_C_DIM);
            ui_cell(2, "INVERT", f_onoff(l->flags & SQ_LF_INVERT), (l->flags & SQ_LF_INVERT) ? C_ON : SQ_C_DIM);
            ui_cell(3, "TRIG", x->trig ? f_pre("T", x->trig) : "CLOCK", x->trig ? C_ON : SQ_C_DIM);   /* 0.13 */
        } else if (lfo_page == LFO_PAGE_ENV) {                       /* 0.20 ENV */
            static const char *const ETN[SQ_ENV_TIMES] = {"0", "1/96", "1/48", "1/32", "1/24", "1/16", "1/16.", "1/8", "1/8.", "1/4", "1/4.",
                                                          "1/2", "1/2.", "1 BAR", "2 BARS", "4 BARS"};
            const sq_lfoe_t *e = &project.ext.lfoe[lfo_sel];
            uint16_t ec = l->shape == SQ_LFO_ENV ? lc : SQ_C_DIM;
            ui_cell(0, "ATTACK", ETN[e->a < SQ_ENV_TIMES ? e->a : 0u], ec);
            ui_cell(1, "DECAY", ETN[e->d < SQ_ENV_TIMES ? e->d : 0u], ec);
            ui_cell(2, "SUSTAIN", f_pct(e->s), ec);
            ui_cell(3, "RELEASE", ETN[e->r < SQ_ENV_TIMES ? e->r : 0u], ec);
        } else if (lfo_page == LFO_PAGE_MOD) {                       /* 0.20 MOD MATRIX */
            static const char *const SN[SQ_MSS] = {"OFF", "LFO ", "MACRO ", "ENERGY", "RANDOM", "VEL T", "CC IN "};
            static const char *const DN[SQ_MDS] = {"OFF", "DEPTH L", "CENTER L", "VEL T", "GATE T", "CHANCE T", "TIMING T", "SWING T", "FX T"};
            static const char *const MAC[4] = {"INTENS", "GATE", "SWING", "FILTER"};
            const sq_mod_t *m = &project.ext.mod[mod_slot];
            uint16_t mc = (m->src && m->dst) ? C_WHITE : SQ_C_DIM;
            char *q;
            ui_cell(0, "SLOT", f_pre("MOD ", (uint32_t)mod_slot + 1u), C_ACCENT);
            q = fbuf();
            { char *z = q; z = put_s(z, SN[m->src < SQ_MSS ? m->src : 0u]);
              if (m->src == SQ_MS_MACRO) z = put_s(z, MAC[m->src_i & 3u]);
              else if (m->src == SQ_MS_LFO || m->src == SQ_MS_VEL) z = put_u(z, (uint32_t)m->src_i + 1u);
              else if (m->src == SQ_MS_CCIN) z = put_u(z, m->src_i);
              finish(z); }
            ui_cell(1, "SOURCE", q, mc);
            q = fbuf();
            { char *z = q; z = put_s(z, DN[m->dst < SQ_MDS ? m->dst : 0u]); if (m->dst) z = put_u(z, (uint32_t)m->dst_i + 1u); finish(z); }
            ui_cell(2, "DESTINATION", q, mc);
            ui_cell(3, "AMOUNT", f_spct(m->amt), mc);
        } else {                                                     /* 0.13 RATE SEQ */
            static const char *const EV[SQ_RES] = {"BEAT", "2 BEATS", "BAR", "2 BARS"};
            const sq_lfox_t *x = &project.ext.lfo[lfo_sel];
            uint8_t on = x->seq_n >= 2u, r = x->seq_rate[rseq_pos & 7u];
            ui_cell(0, "STEPS", on ? f_u(x->seq_n) : "OFF", on ? C_ON : SQ_C_DIM);
            ui_cell(1, "EVERY", EV[x->seq_every < SQ_RES ? x->seq_every : 0u], on ? lc : SQ_C_DIM);
            { char *fb = fbuf(), *q = fb; q = put_u(q, (uint32_t)rseq_pos + 1u); q = put_s(q, "/"); q = put_u(q, on ? x->seq_n : SQ_RSEQ_MAX); finish(q); ui_cell(2, "POSITION", fb, on ? lc : SQ_C_DIM); }
            ui_cell(3, r < SQ_LFO_RATES ? "RATE" : "(RATE)", lfo_rate_name(r < SQ_LFO_RATES ? r : l->rate), on ? lc : SQ_C_DIM);
        }
        p = b; p = put_s(p, "LFO "); p = put_u(p, (uint32_t)lfo_sel + 1u); p = put_s(p, "/16 "); p = put_s(p, f_onoff(l->enabled));
        p = put_s(p, "  PAGE "); p = put_u(p, (uint32_t)lfo_page + 1u); p = put_s(p, "/6");
        if (lfo_page == 3u) p = put_s(p, " RATE SEQ");
        if (lfo_page == LFO_PAGE_ENV) p = put_s(p, " ENV");
        if (lfo_page == LFO_PAGE_MOD) p = put_s(p, " MOD");
        finish(p);
        ui_line(2, b, C_WARN);
        break;
    }
    case UM_SEQ: {
        static const char *const TGT[GEN_TARGET_SETS] = {"RHYTHM", "+NOTES", "+CC", "+N+CC", "+CC+LFO", "ALL"};
        static const char *const SCP[SQ_SCOPES] = {"THIS", "BANK", "ALL", "DRUMS", "MELODIC", "CUSTOM"};
        const sq_gen_t *g = &project.gen;
        uint8_t nv = sq_beat_variants(beat_genre, beat_func), euc = (cfg->flags & SQ_TF_EUC) ? 1u : 0u;
        if (seq_page == 0u) {
            if (cfg->euc_fam == SQ_RF_NUMERIC) {                     /* 0.23.1: K1 picks one of the sixteen base rhythms */
                p = b; p = put_u(p, (uint32_t)sq_numeric_index(cfg->euc_pulses) + 1u); p = put_s(p, " OF 16"); finish(p);
                ui_cell(0, euc ? "NUMERIC LIVE" : "NUMERIC READY", b, euc ? C_ACCENT : C_WHITE);
            } else {
                p = b; p = put_u(p, cfg->euc_pulses); p = put_s(p, "/"); p = put_u(p, (uint32_t)(cfg->length - cfg->start)); finish(p);
                ui_cell(0, euc ? "EUCLID LIVE" : "EUCLID READY", b, euc ? C_ACCENT : C_WHITE);   /* 0.16: off, the knobs set it up */
            }
            ui_cell(1, cfg->euc_fam == SQ_RF_NUMERIC ? "ROTATE" : "EUC ROTATE", f_u(cfg->euc_rot), euc ? C_WHITE : SQ_C_DIM);
            ui_cell(2, "FAMILY", sq_rhythm_name(cfg->euc_fam), cfg->euc_fam ? C_ACCENT : C_WHITE);
            ui_cell(3, "HEAT", f_pct(tool_heat), C_WHITE);
        } else if (seq_page == 1u) {
            static const char *const TM[SQ_TM_MODES] = {"RHYTHM", "NOTES", "BOTH"};
            static const char *const CR[4] = {"1 BAR", "2 BARS", "4 BARS", "LOOP"};
            static const char *const AS[5] = {"BEAT", "OFFBEAT", "POLY3", "SYNC", "RANDOM"};
            const sq_algo_t *al = algo_edit(selected_track);              /* 0.11: the slot shown (SEL + K1 picks it); 0.16: the READY one */
            uint8_t a = al->algo < SQ_ALGOS ? al->algo : 0u, rdy = algo_pend_of(selected_track) ? 1u : 0u;
            static const char *const SLOT[SQ_ALGO_SLOTS] = {"ALGO 1", "ALGO 2", "ALGO 3", "ALGO 4"};
            static const char *const SLOTR[SQ_ALGO_SLOTS] = {"ALGO 1 READY", "ALGO 2 READY", "ALGO 3 READY", "ALGO 4 READY"};
            ui_cell(0, (rdy ? SLOTR : SLOT)[algo_k(selected_track)], ALGO_NAME[a], rdy ? C_WHITE : a ? C_ACCENT : SQ_C_DIM);
            switch (a) {
            case SQ_ALGO_TURING:
                ui_cell(1, "MUTATION", f_pct(al->a), C_WHITE);
                ui_cell(2, "LENGTH", al->b >= SQ_TM_LEN_TRACK ? "TRACK" : f_u(al->b), al->b >= SQ_TM_LEN_TRACK ? C_ACCENT : C_WHITE);   /* (0.25: as long as the track) */
                ui_cell(3, "MOVES", TM[al->c < SQ_TM_MODES ? al->c : 0u], C_WHITE); break;
            case SQ_ALGO_CELL:
                ui_cell(1, "RULE", f_u(al->a), C_WHITE); ui_cell(2, "CELLS", f_u(al->b), C_WHITE);
                ui_cell(3, "NEW ROW EVERY", CR[al->c & 3u], C_WHITE); break;
            case SQ_ALGO_ACCENT:
                ui_cell(1, "ACCENT", AS[al->a % 5u], C_WHITE); ui_cell(2, "AMOUNT", f_u(al->b), C_WHITE);
                ui_cell(3, "START", f_u(al->c), C_WHITE); break;
            case SQ_ALGO_DENSITY:
                ui_cell(1, "DENSITY", f_pct(al->a), C_WHITE); ui_cell(2, "GHOST VEL", f_pct(al->b), C_WHITE);
                ui_cell(3, "", "", SQ_C_DIM); break;
            default:
                ui_cell(1, "A", "-", SQ_C_DIM); ui_cell(2, "B", "-", SQ_C_DIM); ui_cell(3, "C", "-", SQ_C_DIM); break;
            }
        } else if (seq_page == 2u) {
            ui_cell(0, "TARGETS", TGT[gen_target_index()], C_WHITE);
            if (in_held() & (1u << BTN_SEL)) ui_cell(1, "RETURN", f_pct(sq_evo_return(&project.ext, g)), evo_run ? C_ACCENT : C_WHITE);   /* 0.27: SEL + K2 */
            else ui_cell(1, "EVOLVE AMT", f_pct(g->evo_amount), evo_run ? C_ACCENT : C_WHITE);
            ui_cell(2, "EVOLVE EVERY", f_pre("", EVO_BARS[g->evo_every < SQ_EVO_EVERY ? g->evo_every : 0u]), evo_run ? C_ACCENT : C_WHITE);
            ui_cell(3, "SCOPE", SCP[g->scope < SQ_SCOPES ? g->scope : 0u], g->scope ? C_ACCENT : C_WHITE);
        } else if (seq_page == 3u || seq_page == 4u) {   /* 0.10 EXPO */
            static const char *const XS[SQ_X_SHAPES] = {"OFF", "RAMP", "BOUNCE", "SETTLE"};
            static const char *const XSP[SQ_X_SPANS] = {"STEP", "1 BEAT", "2 BEATS", "1 BAR", "2 BARS", "4 BARS"};
            static const char *const XV[SQ_X_VELS] = {"FLAT", "FALL", "RISE", "BOUNCE", "GRACE"};
            static const char *const XN[SQ_X_NOTES] = {"CHORD", "ARP", "ARP +1 OCT", "ARP +2 OCT", "ARP +3 OCT"};
            const sq_expo_t *x = &cfg->expo;
            uint16_t on = x->shape != SQ_XS_OFF ? C_ACCENT : C_WHITE;   /* (0.16: off, set up for K4 to start it) */
            if (seq_page == 3u) {
                ui_cell(0, x->shape == SQ_XS_SETTLE ? "RATE /BEAT" : "EXPO HITS", f_u(x->hits), on);
                ui_cell(1, x->shape == SQ_XS_SETTLE ? "DEPTH" : "CURVE", f_i(x->curve), on);
                ui_cell(2, "SPAN", XSP[x->span < SQ_X_SPANS ? x->span : 0u], on);
                ui_cell(3, "SHAPE", XS[x->shape < SQ_X_SHAPES ? x->shape : 0u], x->shape ? C_ON : SQ_C_DIM);
            } else {
                ui_cell(0, "EXPO VEL", XV[x->vel < SQ_X_VELS ? x->vel : 0u], on);
                ui_cell(1, "GATE", f_pct(x->gate), on);
                ui_cell(2, "JITTER", f_pct(x->jitter), on);
                ui_cell(3, "NOTES", XN[x->notes < SQ_X_NOTES ? x->notes : 0u], on);
            }
        } else if (seq_page == 5u) {                 /* 0.10 TOOLS: density, WHEN, EVERY, the genre's part */
            static const char *const WN[SQ_WHENS] = {"NOW", "BAR", "2 BARS", "4 BARS", "8 BARS", "16 BARS"};
            static const char *const EN[SQ_EVERYS] = {"OFF", "1 BAR", "2 BARS", "4 BARS", "8 BARS", "16 BARS", "32 BARS"};
            static const char *const GN[SQ_GMS] = {"FREE", "ON", "LIVE"};
            ui_cell(0, "RND DENSITY", f_pct(g->density), C_WHITE);
            ui_cell(1, "TOOLS WHEN", WN[g->when < SQ_WHENS ? g->when : 0u], g->when ? C_ACCENT : C_WHITE);
            ui_cell(2, "EVERY", EN[g->every < SQ_EVERYS ? g->every : 0u], g->every ? C_ACCENT : SQ_C_DIM);
            ui_cell(3, "GENRE", GN[g->genre_mode < SQ_GMS ? g->genre_mode : 1u], g->genre_mode == SQ_GM_FREE ? SQ_C_DIM : C_ACCENT);
        } else if (seq_page == 6u) {                 /* 0.12 BREAK: the chop, the dice's rolls and swap, the slices */
            uint8_t bon = track_break(t);
            ui_cell(0, "CHOP", sq_brk_chop(cfg->brk_chop)->name, bon ? C_ACCENT : SQ_C_DIM);
            ui_cell(1, "DICE ROLLS", f_u(SQ_BRK_ROLL(cfg->brk_cfg)), bon ? C_WHITE : SQ_C_DIM);
            ui_cell(2, "DICE SWAP", f_pct((uint32_t)SQ_BRK_SWAP(cfg->brk_cfg) * 100u / 7u), bon ? C_WHITE : SQ_C_DIM);
            ui_cell(3, "SLICES", f_u(SQ_BRK_SLICES(SQ_BRK_SL(cfg->brk_cfg))), bon ? C_WHITE : SQ_C_DIM);
        } else {                                     /* 0.23 THEORY: where the patterns come from, the next seed; this track's */
            const sq_thpat_t *m = &project.th.pat[t][tr[t].pattern];
            uint8_t on = project.th.src != SQ_SRC_LIBRARY ? 1u : 0u;
            ui_cell(0, "SOURCE", project.th.src == SQ_SRC_FREE ? "FREE" : on ? "THEORY" : "LIBRARY", on ? C_ACCENT : C_WHITE);   /* (THEORY while the GENRE mode is FREE: the line below says FREE) */
            ui_cell(1, "NEXT SEED", f_u((uint32_t)project.th.seed + 1u), on ? C_WHITE : SQ_C_DIM);
            ui_cell(2, "TRACK SEED", m->style ? f_u((uint32_t)m->seed + 1u) : "-", m->style ? C_WHITE : SQ_C_DIM);
            ui_cell(3, "VARIATION", m->style ? f_u(m->var) : "-", !m->style ? SQ_C_DIM : m->var ? C_ACCENT : C_WHITE);
        }
        p = b; p = put_s(p, "SEQ "); p = put_u(p, (uint32_t)seq_page + 1u); p = put_s(p, "/8 ");
        if (seq_page == 3u || seq_page == 4u) {
            p = put_s(p, cfg->expo.shape ? "EXPO ON: THE CURVE IS THE RHYTHM" : "EXPO OFF: TURN A KNOB");
        } else if (seq_page == 1u) {                        /* 0.11: the four slots, the one shown marked */
            uint8_t k;
            for (k = 0; k < SQ_ALGO_SLOTS; k++) {
                const sq_algo_t *al = SQ_ALGO_AT(cfg, k);
                static const char *const SHORT[SQ_ALGOS] = {"-", "TUR", "CEL", "ACC", "DEN"};
                p = put_s(p, k == algo_cur[selected_track] ? "[" : " "); p = put_s(p, SHORT[al->algo < SQ_ALGOS ? al->algo : 0u]); p = put_s(p, k == algo_cur[selected_track] ? "]" : " ");
            }
            p = put_s(p, " SEL+K1");
        } else if (seq_page == 5u) {
            p = put_s(p, "TOOLS: WHEN THEY APPLY, HOW OFTEN");
        } else if (seq_page == 6u) {
            p = put_s(p, track_break(t) ? "BREAK  ARP+KEYS: SLICES, BLACK: ROLL.." : "BREAK: HOME 4 K1 MAKES THE TRACK ONE");
        } else if (beat_func != SQ_FUNC_PROG && th_style_now(beat_genre) != 255u) {   /* 0.23 THEORY: the part and the seed it will be made from */
            p = put_s(p, th_style_now(beat_genre) == SQ_TH_FREE ? "FREE" : sq_genre_name(beat_genre)); p = put_s(p, " "); p = put_s(p, sq_func_name(beat_func));
            p = put_s(p, " SEED "); p = put_u(p, (uint32_t)project.th.seed + 1u);
        } else {
            p = put_s(p, sq_genre_name(beat_genre)); p = put_s(p, " "); p = put_s(p, sq_func_name(beat_func));
            if (nv && beat_var >= nv) { p = put_s(p, " #"); p = put_u(p, (uint32_t)beat_var + 1u); p = put_s(p, "/"); p = put_u(p, nv); p = put_s(p, "+PI"); }   /* 0.11 */
            else if (nv) { p = put_s(p, " #"); p = put_u(p, (uint32_t)(beat_var % nv) + 1u); p = put_s(p, "/"); p = put_u(p, nv); }
        }
        finish(p);
        ui_line(2, b, C_WARN);
        break;
    }
    case UM_SEL:
        ui_cell(0, "VEL OFFSET", f_i(cfg->vel_offset), C_WHITE);
        ui_cell(1, "HUMAN TIME", f_pct(cfg->hum_time), C_WHITE);
        ui_cell(2, "HUMAN VEL", f_u(cfg->hum_vel), C_WHITE);
        ui_cell(3, "PEN NOTE", f_note(PEN(t)), C_ACCENT);
        ui_line(2, "SEL+KEYS: NOTES  SEL+ALG: TEMPO", C_WARN);
        break;
    case UM_FX: {                                     /* FX: K1..K4 the macros; the keys: effects, LOOP / REPEAT */
        uint32_t k;
        uint16_t fx = fx_now();
        uint8_t th = (in_held() & (1u << BTN_SEL)) ? 1u : 0u;              /* 0.12: with SEL the knobs are THROWS */
        ui_cell(0, th ? "THROW INTENS" : "INTENSITY", f_i(mac_vel), mac_vel ? C_ACCENT : SQ_C_DIM);
        ui_cell(1, th ? "THROW GATE" : "GATE", f_spct(mac_gate), mac_gate ? C_ACCENT : SQ_C_DIM);
        {   /* SWING: what the selected track swings now, in % of the pair (50 straight, 66 triplets) */
            char lab[18], *q = lab;
            q = put_s(q, th ? "THROW SWING " : "SWING T"); if (!th) q = put_u(q, t + 1u); q = put_s(q, " ");
            q = put_u(q, (uint32_t)clamp_i32((int32_t)cfg->swing + mac_swing, SQ_SWING_MIN, SQ_SWING_MAX)); q = put_s(q, "%"); finish(q);
            ui_cell(2, lab, f_i(mac_swing), mac_swing ? C_ACCENT : SQ_C_DIM);
        }
        ui_cell(3, th ? "THROW FILTER" : "FILTER", f_i(mac_filt), mac_filt ? C_ACCENT : SQ_C_DIM);
        p = b;
        for (k = 0; k < FX_COUNT; k++) if (fx & (1u << k)) { p = put_s(p, FX_NAME[k]); p = put_s(p, " "); }
        if (p == b && project.ext.motion_bars && !th && !throw_on) p = put_s(p, record_arm ? "MOTION REC: TURN K1-K4" : mot_any() ? "MOTION PLAYS  OCT-: WIPE" : "MOTION: REC + K1-K4");   /* 0.13 */
        if (p == b) p = put_s(p, th ? "THROWS: BACK TO 0 IN A BAR" : throw_on ? "THROWS GLIDE BACK  OCT-: 0" : echo_global ? "OCT-:MACROS 0  OCT+:ECHO OFF" : "OCT-:MACROS 0  OCT+:ECHO ALL");
        finish(p);
        ui_line(2, b, C_WARN);
        break;
    }
    case UM_ARP: {
        static const char *const VN[SQ_VOICES] = {"CLOSE", "INV 1", "INV 2", "DROP 2", "OPEN"};
        uint8_t cm = SQ_CHORD_MODE(cfg->chord_mode);
        if (arp_page == 0u) {
            uint8_t r = (uint8_t)(((cfg->arp_flags & SQ_AF_HOLD) ? 2u : 0u) | ((cfg->arp_flags & SQ_AF_RETRIG) ? 1u : 0u));
            static const char *const RN[4] = {"OFF", "RETRIG", "HOLD", "HOLD+RT"};
            ui_cell(0, "ARP", chord_name(cm), cm ? C_ACCENT : SQ_C_DIM);
            ui_cell(1, "OCTAVES", f_pre("X", SQ_CHORD_OCTS(cfg->chord_mode)), cm ? C_WHITE : SQ_C_DIM);
            ui_cell(2, "RATE", arp_rate_name(cfg->arp_rate), cfg->arp_rate ? C_ACCENT : SQ_C_DIM);
            ui_cell(3, "RUN", RN[r], r ? C_ON : SQ_C_DIM);
            ui_line(2, track_break(t) ? "ARP 1/6  WHITES: THE CHOPS (HELD: WHILE HELD)" : cfg->arp_rate ? "ARP 1/6  NOTES A STEP; RUNS ON WHILE THE GATE LASTS" : "ARP 1/6  KEYS PLAY THE TRACK; ROLL: INSIDE ITS STEP", C_WARN);
        } else if (arp_page == 1u) {
            ui_cell(0, "CHORD", sq_chord_shape_name(cfg->chord), cfg->chord ? C_ACCENT : SQ_C_DIM);
            ui_cell(1, "KEY", track_in_key(t) ? sq_chord_key_name(cfg->chord_key) : "FREE TRK", track_in_key(t) && cfg->chord ? C_ACCENT : SQ_C_DIM);
            ui_cell(2, "VOICING", VN[cfg->voicing < SQ_VOICES ? cfg->voicing : 0u], C_ACCENT);
            ui_cell(3, "STRUM", f_spct(cfg->strum), cfg->strum ? C_WHITE : SQ_C_DIM);
            ui_line(2, !cfg->chord ? "ARP 2/6 CHORD  ONE NOTE BECOMES A CHORD (32 SHAPES)" : cfg->chord_key == SQ_CK_STRICT ? "ARP 2/6 CHORD  STRICT: OUT OF KEY = SILENT" : cfg->chord_key == SQ_CK_FREE ? "ARP 2/6 CHORD  FREE: THE EXACT SHAPE, KEY OR NOT" : "ARP 2/6 CHORD  DIATONIC: BUILT ON THE SCALE", C_WARN);
        } else if (arp_page == 2u) {                 /* HARMONY: OFF / ON / LOCK, the progression, bars a chord / rhythm, FOLLOW */
            static const char *const BB[9] = {"PROG", "1 BAR", "2 BARS", "3", "4 BARS", "5", "6", "7", "8 BARS"};
            const sq_gen_t *g = &project.gen;
            char cn[12];
            ui_cell(0, "HARMONY", g->harm_on ? (g->harm_lock ? "LOCK" : "ON") : "OFF", g->harm_on ? (g->harm_lock ? C_WARN : C_ON) : SQ_C_DIM);
            if (piprog_browsing()) {                                          /* 0.11: one of the Pi's: its place among them */
                uint8_t cnt = pi_prog_n[pp.genre][pp.mood];
                p = b; p = put_s(p, "PI "); p = put_u(p, (uint32_t)pp.cur + 1u);
                if (cnt != 255u) { p = put_s(p, "/"); p = put_u(p, cnt); }
                finish(p);
            } else if (g->harm_prog == SQ_PROG_PI) { p = b; p = put_s(p, "DICE/PI"); finish(p); }
            else if (g->harm_prog >= SQ_PROGS) { p = b; p = put_s(p, "USER "); p = put_u(p, (uint32_t)(g->harm_prog - SQ_PROGS) + 1u); finish(p); }
            else { p = b; p = put_u(p, (uint32_t)g->harm_prog + 1u); p = put_s(p, " "); p = put_s(p, sq_genre_name(project.gen.harm_genre)); finish(p); }
            b[9] = 0;
            ui_cell(1, g->harm_mood ? sq_mood_name(g->harm_mood) : "PROGRESSION", b, g->harm_on ? C_ACCENT : C_WHITE);
            if (g->harm_rhythm != SQ_HR_BARS) ui_cell(2, "RHYTHM", sq_hrhythm_name(g->harm_rhythm == SQ_HR_GENRE ? sq_genre_hrhythm(g->harm_genre) : g->harm_rhythm), C_ACCENT);
            else ui_cell(2, "BARS A CHORD", BB[g->harm_bars <= 8u ? g->harm_bars : 0u], C_WHITE);
            ui_cell(3, cfg->follow_mode == SQ_FM_RETRIG ? "FOLLOW RETRIG" : cfg->follow_mode == SQ_FM_LEGATO ? "FOLLOW LEGATO" :
                       cfg->follow_mode == SQ_FM_MELODY ? "FOLLOW MELODY" : cfg->follow_mode == SQ_FM_SMOOTH ? "FOLLOW SMOOTH" : "FOLLOW",
                    f_onoff(cfg->flags & SQ_TF_FOLLOW), (cfg->flags & SQ_TF_FOLLOW) ? C_ON : SQ_C_DIM);
            {   sq_hchord_t hc;                         /* the chord playing, and which one of the progression */
                uint8_t hi = 0u;
                if (harm_chord(&hc, &hi)) {
                    char *q = cn;
                    sq_hchord_name(project.key_scale, &hc, cn);
                    while (*q) q++;
                    p = q; p = put_s(p, " "); p = put_u(p, (uint32_t)hi + 1u); finish(p);
                    str_copy(ce_want[0].val, cn, sizeof ce_want[0].val);
                }
            }
            p = b; p = put_s(p, "ARP 3/6 ");
            harm_name(p, 18u);
            while (*p) p++;
            if (project.gen.harm_on) { p = put_s(p, " "); p = put_s(p, sq_mood_name(harm_mood_of(project.gen.harm_prog))); }
            finish(p);
            ui_line(2, b, C_WARN);
        } else if (arp_page == 3u) {                 /* HARMONY 2: FOLLOW's way, the harmony's genre, the mood, the rhythm */
            const sq_gen_t *g = &project.gen;
            static const char *const FMN[SQ_FMS] = {"HOLD", "RETRIG", "LEGATO", "MELODY", "SMOOTH"};   /* (0.25 MELODY: a tune that knows the chord; 0.26 SMOOTH: chords that move little) */
            ui_cell(0, "FOLLOW MODE", FMN[cfg->follow_mode < SQ_FMS ? cfg->follow_mode : 0u], (cfg->flags & SQ_TF_FOLLOW) ? C_ACCENT : SQ_C_DIM);
            ui_cell(1, "HARM GENRE", g->harm_free ? "FREE" : sq_genre_name(g->harm_genre), g->harm_lock ? C_WARN : C_ACCENT);   /* (0.16 FREE) */
            ui_cell(2, "MOOD", g->harm_mood ? sq_mood_name(g->harm_mood) : "ANY", g->harm_mood ? C_ACCENT : SQ_C_DIM);
            ui_cell(3, "RHYTHM", sq_hrhythm_name(g->harm_rhythm), g->harm_rhythm ? C_ACCENT : C_WHITE);
            ui_line(2, "ARP 4/6 HARMONY 2  FOLLOW, THE HARMONY'S GENRE, MOOD, RHYTHM", C_WARN);
        } else if (arp_page == 4u) {                 /* 0.10 USER PROG; 0.11: any root, any shape */
            const sq_uprog_t *u = &project.uprog[uprog_sel];
            static const char *const CN[SQ_HCS] = {"KEY", "KEY 7", "KEY 9", "KEY SUS4", "KEY SUS2", "KEY 6"};
            char dn[12];
            uint8_t uon = uprog_pos < u->n ? 1u : 0u;
            ui_cell(0, uprog_sel == SQ_UPROGS ? "DICE/PI" : "USER PROG", uprog_sel == SQ_UPROGS ? "5" : f_u((uint32_t)uprog_sel + 1u),
                    project.gen.harm_prog == SQ_PROGS + uprog_sel ? C_ON : C_ACCENT);
            p = b; p = put_u(p, (uint32_t)uprog_pos + 1u); p = put_s(p, "/"); p = put_u(p, u->n); finish(p);
            ui_cell(1, "CHORD", b, uon ? C_WHITE : SQ_C_DIM);
            if (uon) { sq_hchord_t hc; hc.deg = u->deg[uprog_pos]; hc.col = u->col[uprog_pos]; hc.semi = u->semi[uprog_pos]; hc.shape = u->shape[uprog_pos]; sq_hchord_name(project.key_scale, &hc, dn); }
            else { dn[0] = '-'; dn[1] = '-'; dn[2] = 0; }
            ui_cell(2, "ROOT", dn, uon ? C_ACCENT : SQ_C_DIM);
            if (!uon) ui_cell(3, "SHAPE", "--", SQ_C_DIM);
            else if (u->semi[uprog_pos] == 255u) ui_cell(3, "COLOUR", CN[u->col[uprog_pos] < SQ_HCS ? u->col[uprog_pos] : 0u], C_WHITE);
            else ui_cell(3, "SHAPE", u->shape[uprog_pos] <= SQ_HSHAPE_CH ? CN[u->shape[uprog_pos]] : sq_chord_shape_name((uint8_t)(u->shape[uprog_pos] - SQ_HSHAPE_CH)), C_WHITE);
            p = b; p = put_s(p, "ARP 5/6 ");
            sq_uprog_name(&project.uprog[uprog_sel], project.key_scale, p, 20u);
            while (*p) p++;
            finish(p);
            ui_line(2, b, C_WARN);
        } else if (arp_page == 5u) {                 /* 0.11 USER PROG 2: its mood, the lengths of a rhythm, the chord's length, its push */
            const sq_uprog_t *u = &project.uprog[uprog_sel];
            uint8_t uon = uprog_pos < u->n ? 1u : 0u;
            ui_cell(0, "MOOD", u->mood ? sq_mood_name(u->mood) : "GUESSED", project.gen.harm_prog == SQ_PROGS + uprog_sel ? C_ON : C_ACCENT);
            ui_cell(1, "LENGTHS OF", "K2", uon ? C_WHITE : SQ_C_DIM);
            p = b; if (uon && u->dur[uprog_pos]) { p = put_u(p, u->dur[uprog_pos]); p = put_s(p, " 16TH"); } else p = put_s(p, "RHYTHM"); finish(p);
            ui_cell(2, "LENGTH", b, uon ? C_ACCENT : SQ_C_DIM);
            ui_cell(3, "PUSH", uon ? f_u(u->push[uprog_pos]) : "--", uon && u->push[uprog_pos] ? C_ACCENT : SQ_C_DIM);
            p = b; p = put_s(p, "ARP 6/6 CHORD "); p = put_u(p, (uint32_t)uprog_pos + 1u); p = put_s(p, " OF "); p = put_s(p, uprog_sel == SQ_UPROGS ? "DICE/PI" : f_pre("USER ", (uint32_t)uprog_sel + 1u)); finish(p);
            ui_line(2, b, C_WARN);
        }
        break;
    }
    case UM_PERF: {                                   /* 0.12: GLO's pages: 1 LIVE, 2 TRACK LIVE, 3 VIAGGIO */
        uint8_t pp = ui_perf_pp();                    /* (PERF + SEL: TRACK LIVE) */
        if (pp == 1u) {
            ui_cell(0, "PATTERN", tr[t].pending_pattern < SQ_PATTERNS ? f_pre("P", (uint32_t)tr[t].pending_pattern + 1u) : f_pre("P", (uint32_t)tr[t].pattern + 1u),
                    tr[t].pending_pattern < SQ_PATTERNS ? C_WARN : C_WHITE);
            ui_cell(1, len_pend[selected_track] ? "LENGTH>BAR" : "LENGTH", f_u(len_shown(selected_track)), len_pend[selected_track] ? C_WARN : C_WHITE);
            ui_cell(2, "SCALE", sq_scale_name(project.key_scale), project.key_scale ? C_ACCENT : SQ_C_DIM);
            ui_cell(3, "MUTE QUEUE", f_onoff(project.live.mute_q), project.live.mute_q ? C_ACCENT : SQ_C_DIM);
            p = b; p = put_s(p, pp != perf_page ? "PERF+SEL TRACK LIVE  T" : "GLO 2/4 TRACK LIVE  T"); p = put_u(p, t + 1u); finish(p);
            ui_line(2, b, C_WARN);
        } else if (pp == 3u) {                       /* 0.25 THE METRE: the bar in steps, its beats; what it is called; where it is */
            char sig[8], spl[SQ_SPLIT_TEXT];
            uint8_t st = bar_shown(), wait = bar_pend_steps ? 1u : 0u;
            uint32_t bt = beats_shown();
            sq_metre_sig(st, bt, sig); sq_metre_split(st, bt, spl);
            ui_cell(0, wait ? "BAR >" : "BAR", f_u(st), wait ? C_WARN : st != 16u ? C_ACCENT : C_WHITE);
            ui_cell(1, wait ? "BEATS >" : "BEATS", spl, wait ? C_WARN : bt != sq_metre_option(st, 0u) ? C_ACCENT : C_WHITE);
            ui_cell(2, "SCENE METRE", project.ext.scene_metre_on ? "BRING IT" : "OFF", project.ext.scene_metre_on ? C_ACCENT : SQ_C_DIM);   /* 0.26 (the metre's name: the line below) */
            p = b; if (playing) { p = put_u(p, bar_no() + 1u); p = put_s(p, "."); p = put_u(p, bar_into() / 6u + 1u); } else p = put_s(p, "--"); finish(p);
            ui_cell(3, "BAR.STEP", b, playing && bar_into() < 6u ? C_WARN : C_WHITE);
            p = b; p = put_s(p, perf_mode ? "PERF 4/4 METRE " : "GLO 4/4 METRE "); p = put_s(p, sig); p = put_s(p, " = "); p = put_s(p, spl); finish(p);
            ui_line(2, b, C_WARN);                    /* (the beats in full: the cell holds nine letters) */
        } else if (pp == 2u) {                       /* 0.17 the MOSSE: the energy, the phrase, the genre and key (queued) */
            static const char *const VQ2[SQ_VQS] = {"PHRASE", "BAR", "BEAT"};
            int32_t gq = vg_genre_shown(), kq = vg_key_shown();
            ui_cell(0, project.viaggio.energy != vg_energy_cur ? "ENERGY >" : "ENERGY", project.viaggio.energy != vg_energy_cur ? f_u(project.viaggio.energy) : f_u(vg_energy_cur),
                    project.viaggio.energy != vg_energy_cur ? C_WARN : project.viaggio.energy != 50u ? C_ACCENT : C_WHITE);
            p = b; p = put_u(p, (uint32_t)vg_bar + 1u); p = put_s(p, "/"); p = put_u(p, vg_bars()); finish(p);
            ui_cell(1, "PHRASE BAR", b, vg_bar + 1u == vg_bars() ? C_WARN : C_WHITE);
            ui_cell(2, gq != (int32_t)vg_set_genre_cur() ? "GENRE >" : "GENRE", sq_set_genre((uint8_t)gq)->name, gq != (int32_t)vg_set_genre_cur() ? C_WARN : C_ACCENT);
            ui_cell(3, kq != (int32_t)project.key_root ? "KEY >" : "KEY", sq_root_name((uint8_t)kq), kq != (int32_t)project.key_root ? C_WARN : project.key_scale ? C_ACCENT : SQ_C_DIM);
            p = b; p = put_s(p, perf_mode ? "PERF 3/4 MOSSE  AT " : "GLO 3/4 MOSSE  AT "); p = put_s(p, VQ2[project.viaggio.quant < SQ_VQS ? project.viaggio.quant : 0u]);
            if (vg_rec_t < SQ_TRACKS) p = put_s(p, " LOOP REC");
            finish(p);
            ui_line(2, b, C_WARN);
        } else {
            int32_t kt = ktrans_target();
            ui_cell(0, "MORPH", f_pct(((uint32_t)morph_pos * 100u + 63u) / 127u), morph_pos ? C_ACCENT : SQ_C_DIM);
            ui_cell(1, "MORPH TO", f_pre("SCENE ", (uint32_t)project.live.morph_b + 1u), C_WHITE);
            ui_cell(2, ktrans_pend != SQ_KT_NONE ? "TRANSPOSE >" : "TRANSPOSE", f_i(kt), ktrans_pend != SQ_KT_NONE ? C_WARN : kt ? C_ACCENT : SQ_C_DIM);
            ui_cell(3, "QUANTISE", QUANT_NAME[project.live.quant < SQ_QUANTS ? project.live.quant : 0u], project.live.quant ? C_ACCENT : C_WHITE);
            p = b; p = put_s(p, perf_mode ? "PERF SCENE " : "GLO 1/4 SCENE "); p = put_u(p, (uint32_t)scene_cursor + 1u);
            p = put_s(p, pending_scene < SQ_SCENES ? " QUEUED" : "");
            if (project.live.mute_q) p = put_s(p, " MQ");
            if (project.song.len) { p = put_s(p, " SONG:"); p = put_u(p, project.song.len); }
            finish(p);
            ui_line(2, b, C_WARN);
        }
        break;
    }
    default: {
        uint8_t k, c = 0;
        if (track_tape(t)) {                               /* 0.11: a TAPE track has no step under the cursor */
            uint16_t tf, tn;
            sq_tape_range(&project, (uint8_t)t, &tf, &tn);
            ui_cell(0, "TAPE BARS", f_u(project.track[t].tape.bars), C_ACCENT);
            ui_cell(1, "NOTES", f_u(tn), tn ? C_WHITE : SQ_C_DIM);
            ui_cell(2, "TAPE QUANT", f_pct(project.track[t].tape.quant), project.track[t].tape.quant ? C_WHITE : SQ_C_DIM);
            ui_cell(3, "REC", rec_quant ? "QUANTISED" : "FREE", record_arm ? C_ON : SQ_C_DIM);
            ui_line(2, record_arm ? "TAPE: PLAY, REC: WHAT YOU PLAY STAYS" : "TAPE TRACK  (REC TO RECORD, SEQ: TOOLS)", C_ON);
            break;
        }
        if (track_break(t)) {                              /* 0.12: a BREAK track's step is a slice */
            uint8_t sl = sq_brk_slice_of(s, PEN(t), brk_slices(t));
            uint8_t raw = (s->flags & SQ_STEP_SET) && s->note[0] != SQ_NOTE_NONE && s->note[0] >= PEN(t) ? (uint8_t)(s->note[0] - PEN(t) + 1u) : 0u;
            ui_cell(0, "SLICE", sl ? f_u(sl) : raw ? f_u(raw) : "--", (s->flags & SQ_STEP_ON) ? C_ACCENT : SQ_C_DIM);
        } else
        ui_cell(0, (s->flags & SQ_STEP_SET) ? "NOTE" : "NOTE (PEN)", f_note_key(t, (s->flags & SQ_STEP_SET) ? s->note[0] : PEN(t)), (s->flags & SQ_STEP_SET) ? on : SQ_C_DIM);
        ui_cell(1, "VELOCITY", f_u(s->velocity), on);
        ui_cell(2, "CHANCE", f_pct(s->chance), on);
        ui_cell(3, "RATCHET", f_u(s->ratchet), on);
        p = b; p = put_s(p, "STEP "); p = put_u(p, (uint32_t)cursor_step + 1u); p = put_s(p, (s->flags & SQ_STEP_ON) ? " ON " : " OFF ");
        if (s->flags & SQ_STEP_SET) {
            uint32_t more = 0u;
            for (k = 0; k < SQ_POLY; k++) if (s->note[k] != SQ_NOTE_NONE) { if (c < 4u) { p = put_note(p, s->note[k]); p = put_s(p, " "); c++; } else more++; }
            if (more) { p = put_s(p, "+"); p = put_u(p, more); p = put_s(p, " "); }   /* 0.28: a chord of five or six */
        }
        if (s->flags & SQ_STEP_TIE) p = put_s(p, "TIE ");
        if (s->flags & SQ_STEP_SLIDE) p = put_s(p, "SLIDE ");
        p = put_s(p, "PEN "); p = put_note(p, PEN(t));
        finish(p);
        ui_line(2, b, (s->flags & SQ_STEP_ON) ? C_ON : SQ_C_DIM);
        break;
    }
    }

    /* 0.12 PICK: the knob in focus of the group held carries ">" (">-": the keys cannot set that one) */
    if (!save_down) {
        int g = pick_group(eff_held());
        if (g >= 0) pick_mark(g, ce_want[pick_focus_now(g)].lab);
    }

    /* lines 3-4: what you just did, else (0.12) the map of the keys of the button held half a second, else the key,
     * the grid, the clock recoveries; the genre and scope */
    if (msg_text && !time_due(fm1_ms, msg_until)) ui_wrap(msg_text, C_WARN);
    else if (mode == UM_SAVE && !save_page) {         /* 0.15: the name of the project in the slot, and of the one here */
        msg_text = 0;
        p = b; p = put_s(p, "SLOT "); p = put_u(p, (uint32_t)slot_cur + 1u); p = put_s(p, ": ");
        p = put_s(p, !slot_info[slot_cur].ok ? "EMPTY" : slot_info[slot_cur].name[0] ? slot_info[slot_cur].name : "NO NAME");
        finish(p);
        ui_line(3, b, slot_info[slot_cur].ok ? C_CYAN : SQ_C_DIM);
        p = b; p = put_s(p, "NOW: ");
        if (project.ext.name[0]) { char nm[SQ_NAME_LEN + 1u]; memcpy(nm, project.ext.name, SQ_NAME_LEN); nm[SQ_NAME_LEN] = 0; p = put_s(p, nm); }
        else p = put_s(p, "NO NAME");
        p = put_s(p, "  REC: CLEAR");
        finish(p);
        ui_line(4, b, SQ_C_DIM);
    } else if (pick_map_due() && pick_map_any(eff_held(), b, b + 32)) {   /* (b holds 64: two lines of 29) */
        msg_text = 0;
        ui_line(3, b, C_CYAN);
        ui_line(4, b + 32, C_CYAN);
    } else if (mode == UM_PERF && ui_perf_pp() == 2u) {   /* 0.17 the MOSSE: the queue (0.9-0.16: VIAGGIO mode's) */
        uint32_t k;
        msg_text = 0;
        p = b;
        if (!vg_q.n) p = put_s(p, "QUEUE EMPTY  BLACK: THE MOVES, AT THE END OF THE PHRASE");
        else {
            p = put_s(p, vg_now ? "NOW: " : "QUEUE: ");
            for (k = 0; k < vg_q.n && (uint32_t)(p - b) < 44u; k++) {
                const sq_move_t *m = &vg_q.m[k];
                if (sq_move_has_track(m->kind)) { p = put_s(p, "T"); p = put_u(p, (uint32_t)m->a + 1u); p = put_s(p, " "); }
                p = put_s(p, sq_move_name(m->kind));
                if (m->kind == SQ_MV_GENRE) { p = put_s(p, " "); p = put_s(p, sq_set_genre(m->a)->name); }
                p = put_s(p, "  ");
            }
        }
        finish(p);
        ui_wrap(b, vg_q.n ? C_ON : SQ_C_DIM);
    } else if (mode == UM_SAVE && save_page == 2u) {   /* 0.12: the USB link's numbers (SAVE 3) */
        sq_usb_stats_t u;
        usb_stats(&u);
        msg_text = 0;
        p = b; p = put_s(p, "RESET "); p = put_u(p, u.resets); p = put_s(p, " SLEEP "); p = put_u(p, u.suspends);
        p = put_s(p, " STALL "); p = put_u(p, u.stalls); finish(p);
        ui_line(3, b, SQ_C_DIM);
        p = b; p = put_s(p, "MAX WAIT "); p = put_u(p, u.wait_max_ms); p = put_s(p, "MS HELD "); p = put_u(p, u.rx_held);
        p = put_s(p, " BAD "); p = put_u(p, u.rx_bad); finish(p);
        ui_line(4, b, SQ_C_DIM);
    } else {
        static const char *const SCP[SQ_SCOPES] = {"THIS TRACK", "BANK", "ALL", "DRUMS", "MELODIC", "CUSTOM"};
        msg_text = 0;
        p = b;
        p = put_s(p, "KEY"); if (project.key_cur) { p = put_u(p, (uint32_t)project.key_cur + 1u); } p = put_s(p, " ");
        if (project.key_scale == SQ_SC_CHROMATIC && !project.key_shift) p = put_s(p, "OFF");
        else {
            p = put_s(p, sq_root_name(project.key_root)); p = put_s(p, " "); p = put_s(p, sq_scale_name(project.key_scale));
            if (project.key_shift) p = put_i(p, project.key_shift);
        }
        if (grid_attached) { p = put_s(p, " G:"); p = put_s(p, gr_view_name()); }
        if (clock_recoveries) { p = put_s(p, " RCV"); p = put_u(p, clock_recoveries); }
        finish(p);
        ui_line(3, b, SQ_C_DIM);
        p = b;
        p = put_s(p, sq_genre_name(beat_genre)); p = put_s(p, " / "); p = put_s(p, SCP[project.gen.scope < SQ_SCOPES ? project.gen.scope : 0u]);
        finish(p);
        ui_line(4, b, SQ_C_DIM);
    }

    /* line 5: what is going on */
    if (mode == UM_SAVE && save_page == 2u) { ui_line(5, "SEL+K1 TWICE: RECONNECT USB  K2: LIGHTS", C_CYAN); return; }
    p = b;
    if (dice_pending) p = put_s(p, "DICE? +KEEP -BACK ");
    if (evo_run) { p = put_s(p, evo_run == 2u ? "FROZEN " : "EVOLVE "); }
    if (song_on) { p = put_s(p, "SONG "); p = put_u(p, (uint32_t)song_pos + 1u); p = put_s(p, "/"); p = put_u(p, project.song.len); p = put_s(p, " "); }
    if (temp_on) p = put_s(p, "TEMP ");
    if (loop_on) { p = put_s(p, repeat_now() ? "REPEAT " : "LOOP "); p = put_s(p, loop_name(loop_len)); p = put_s(p, " "); }
    if (stop_at_bar) p = put_s(p, "STOP@BAR ");
    if (restart_pend) p = put_s(p, "RESTART ");
    if (ktrans_pend != SQ_KT_NONE) { p = put_s(p, "TR>"); p = put_i(p, ktrans_pend); p = put_s(p, " "); }
    if (mac_vel || mac_gate || mac_swing || mac_filt) p = put_s(p, "MACRO ");
    if (project.ext.motion_bars && playing && (record_arm || mot_any())) p = put_s(p, record_arm ? "MOTION REC " : "MOTION ");   /* 0.13 */
    if (morph_pos) { p = put_s(p, "MORPH "); p = put_u(p, ((uint32_t)morph_pos * 100u + 63u) / 127u); p = put_s(p, "% "); }
    if (learn_kind) p = put_s(p, "LEARN ");
    if (rl_state) p = put_s(p, "RELOAD ");
    if (pending_mute) p = put_s(p, "MUTES WAIT ");
    if (echo_global) p = put_s(p, "ECHO ALL ");
    if (sl_on & (1u << selected_track)) p = put_s(p, "STEP LOOP ");
    if (tool_due_tool < TOOL_COUNT) p = put_s(p, "TOOL WAITS ");
    if (project.gen.every && project.gen.every_tool < TOOL_COUNT) p = put_s(p, "EVERY ");
    if (snap_pend < SQ_SNAPS) { p = put_s(p, "SNAP>"); p = put_u(p, (uint32_t)snap_pend + 1u); p = put_s(p, " "); }
    else if (snap_cur < SQ_SNAPS) { p = put_s(p, "SNAP"); p = put_u(p, (uint32_t)snap_cur + 1u); p = put_s(p, " "); }
    if (snap_capture) p = put_s(p, "CAPTURE ");
    {
        int8_t d;
        uint8_t col;
        if (harm_now(&d, &col)) { char cn[12]; sq_harm_chord_name(project.key_scale, d, col, cn); p = put_s(p, cn); p = put_s(p, " "); }
    }
    finish(p);
    ui_line(5, b, dice_pending ? C_WARN : C_CYAN);
}

static void ui_draw_line(uint32_t i)
{
    static const uint8_t Y[UI_LINES] = {0, 18, 140, 158, 176, 194};
    cv_begin(232, FONT_S.h, C_BLACK);
    cv_text(0, 0, &FONT_S, ln_want[i].s, ln_want[i].c);
    if (ln_want[i].bat) ui_draw_batt(ln_want[i].bat);
    cv_blit(4, Y[i]);                          /* (no wait: the transfer runs while the loop goes on) */
    ln_shown[i] = ln_want[i];
    ln_ok |= (uint8_t)(1u << i);
}

static void ui_draw_cell(uint32_t i)
{
    static const uint8_t X[4] = {0, 120, 0, 120};
    static const uint8_t Y[4] = {38, 38, 90, 90};
    cv_begin(120, 48, C_BLACK);
    cv_text(6, 0, &FONT_S, ce_want[i].lab, C_LABEL);
    cv_text(6, 16, &FONT_L, ce_want[i].val, ce_want[i].c);
    cv_blit(X[i], Y[i]);
    ce_shown[i] = ce_want[i];
    ce_ok |= (uint8_t)(1u << i);
}

/* the 16 cells of the strip: steps, or tracks, slots, FX, LFOs */
static uint16_t strip_color(uint32_t i)
{
    uint8_t mode = ui_mode();
    if (mode == UM_SAVE) {                     /* the slots on the left half, the SNAPSHOTS on the right */
        if (i < SQ_SLOTS) return i == slot_cur ? C_ACCENT : slot_info[i].ok ? C_ON : SQ_C_DIM;
        i -= SQ_SLOTS;
        if (i >= SQ_SNAPS) return SQ_C_OUT;
        return snap_pend == i ? C_WARN : snap_cur == i ? C_PLAY : project.snap[i].used ? C_CYAN : SQ_C_DIM;
    }
    if (mode == UM_FX) return (fx_now() >> i) & 1u ? C_WARN : SQ_C_DIM;
    if (mode == UM_LFO) return i == lfo_sel ? C_ACCENT : project.lfo[i].enabled ? C_ON : SQ_C_DIM;
    if (mode == UM_PERF || mode == UM_HOME) {
        if (i == selected_track) return C_ACCENT;
        if (solo_mask & (1u << i)) return C_WARN;
        if (!track_audible(i)) return SQ_C_OUT;
        return playing && ev[i].ratchet_left ? C_PLAY : C_ON;
    }
    if (mode == UM_SAVE) return SQ_C_OUT;
    {
        uint8_t stn = (uint8_t)(page * 16u + i);
        sq_step_t *s = &project.step[selected_track][tr[selected_track].pattern][stn];
        const sq_track_cfg_t *c = &project.track[selected_track];
        uint8_t written = (s->flags & SQ_STEP_ON) ? 1u : 0u, heard = live_preview(selected_track, stn);
        uint16_t col = heard ? (written ? C_ON : C_CYAN) : (written && live_active(selected_track) ? C_LABEL : SQ_C_DIM);   /* 0.8: what is heard */
        if (stn < c->start || stn >= c->length) col = (s->flags & SQ_STEP_ON) ? SQ_C_DIM : SQ_C_OUT;
        if (stn == cursor_step) col = C_ACCENT;
        if (playing && stn == ev[selected_track].step_index) col = C_PLAY;
        return col;
    }
}

/* 0.12: the long notes and the legato as one block. A note of N steps: its cell, then the cells it covers in the tail
 * colour and the gaps between them filled; 1.5 steps: half of the next cell too; TIE: the block welds to the next cell
 * (the gap filled). Bits per cell of the page shown: tail (the cell is covered), bridge (the gap on its right is
 * filled), half (its left half is covered). Steps that wrap past the loop's end cover its first steps. */
#define C_TAIL RGB(40, 110, 80)
static void strip_notes(uint16_t *tail, uint16_t *bridge, uint16_t *half)
{
    uint64_t tl, br, hf;
    uint32_t base = page * 16u;
    note_blocks(selected_track, &tl, &br, &hf);
    *tail = (uint16_t)(tl >> base); *bridge = (uint16_t)(br >> base); *half = (uint16_t)(hf >> base);
}

/* the strip: one row of sixteen slim cells (15 px each), drawn in four pieces of four; draws the first piece that
 * differs from what is on the glass. Returns 1 if it drew something (call again), 0 when it is all up to date. */
#define UI_STRIP_Y 214u
/* the sixteen cells as they should be: the colour, and (<< 16) the block bits: 1 the gap on the right filled, 2 the
 * left half covered, 4 the gap on the left filled */
static void strip_cells(uint32_t col[16])
{
    uint16_t tail = 0u, bridge = 0u, half = 0u;
    uint8_t mode = ui_mode();
    uint8_t steps = (mode == UM_STEP || mode == UM_EDIT || mode == UM_ENV || mode == UM_SEQ || mode == UM_SEL || mode == UM_ARP) ? 1u : 0u;
    uint32_t c;
    if (steps) strip_notes(&tail, &bridge, &half);
    for (c = 0; c < 16u; c++) {
        uint32_t fl = 0u;
        uint16_t k = strip_color(c);
        if (steps && (tail & (1u << c)) && (k == SQ_C_DIM || k == C_LABEL)) k = C_TAIL;      /* covered, not a hit of its own */
        if (steps && (bridge & (1u << c))) fl |= 1u;
        if (steps && (half & (1u << c)) && (k == SQ_C_DIM || k == C_LABEL)) fl |= 2u;
        if (steps && c && (bridge & (1u << (c - 1u)))) fl |= 4u;                              /* the gap on its left is filled */
        col[c] = (uint32_t)k | (fl << 16);
    }
}
static uint8_t draw_grid_step(void)
{
    uint32_t h, i, col[16];
    strip_cells(col);
    for (h = 0; h < 4u; h++) {
        uint32_t c0 = h * 4u;
        int diff = 0;
        for (i = 0; i < 4u; i++)
            if (!(cell_ok & (1u << (c0 + i))) || cell_shown[c0 + i] != col[c0 + i]) diff = 1;
        if (!diff) continue;
        cv_begin(60, 24, C_BLACK);
        for (i = 0; i < 4u; i++) {
            int32_t x = (int32_t)i * 15 + 1;
            uint16_t k = (uint16_t)col[c0 + i];
            uint32_t fl = col[c0 + i] >> 16;
            cv_rect(x, 2, 12, 18, k);
            if (fl & 2u) cv_rect(x, 2, 6, 18, C_TAIL);                                           /* half a step more */
            if (fl & 1u) cv_rect(x + 12, 6, 3, 10, C_TAIL);                                      /* the gap on the right */
            if ((fl & 4u) && i == 0u) cv_rect(0, 6, 1, 10, C_TAIL);                              /* (the last pixel of the gap before this piece) */
            if (((c0 + i) & 3u) == 0u) cv_rect(x, 21, 12, 2, C_LABEL);     /* a mark on every beat */
            cell_shown[c0 + i] = col[c0 + i];
            cell_ok |= (uint16_t)(1u << (c0 + i));
        }
        cv_blit(h * 60u, UI_STRIP_Y);
        return 1u;
    }
    return 0u;
}

/* builds the screen, then draws the first piece that differs from what is on the glass.
 * Returns 1 if it drew something (call again), 0 when all is up to date. */
static uint8_t draw_screen_step(void)
{
    uint32_t i;
    ui_build();
    for (i = 0; i < 2u; i++)
        if (!(ln_ok & (1u << i)) || ln_shown[i].c != ln_want[i].c || ln_shown[i].bat != ln_want[i].bat || !ui_str_eq(ln_shown[i].s, ln_want[i].s)) { ui_draw_line(i); return 1u; }
    for (i = 0; i < 4u; i++)
        if (!(ce_ok & (1u << i)) || ce_shown[i].c != ce_want[i].c || !ui_str_eq(ce_shown[i].val, ce_want[i].val) || !ui_str_eq(ce_shown[i].lab, ce_want[i].lab)) { ui_draw_cell(i); return 1u; }
    for (i = 2; i < UI_LINES; i++)
        if (!(ln_ok & (1u << i)) || ln_shown[i].c != ln_want[i].c || !ui_str_eq(ln_shown[i].s, ln_want[i].s)) { ui_draw_line(i); return 1u; }
    return 0u;
}

#ifdef DINGHY_HOST
/* the tests: the screen as text, after a build ("T ui"): the six lines, the four cells (label|value) */
static void app_host_ui(void)
{
    uint32_t i, col[16];
    ui_build();
    for (i = 0; i < UI_LINES; i++) printf("%6u ms  UI L%u %s\n", fm1_ms, (unsigned)i, ln_want[i].s);
    for (i = 0; i < 4u; i++) printf("%6u ms  UI C%u %s|%s\n", fm1_ms, (unsigned)i, ce_want[i].lab, ce_want[i].val);
    /* the strip: a letter a cell (X on, t tail, h half, . dim, o out, c cursor, p play, C cyan, L written-not-heard,
     * a accent, w warn, ? other) and '-' when the gap on its right is filled (a long note goes on, a TIE) */
    strip_cells(col);
    printf("%6u ms  UI S ", fm1_ms);
    for (i = 0; i < 16u; i++) {
        uint16_t k = (uint16_t)col[i];
        uint32_t fl = col[i] >> 16;
        char ch = k == C_ON ? 'X' : k == C_TAIL ? 't' : k == SQ_C_DIM ? ((fl & 2u) ? 'h' : '.') : k == SQ_C_OUT ? 'o' : k == C_ACCENT ? 'c' :
                  k == C_PLAY ? 'p' : k == C_CYAN ? 'C' : k == C_LABEL ? 'L' : k == C_WARN ? 'w' : '?';
        putchar(ch);
        putchar((fl & 1u) ? '-' : ' ');
    }
    putchar('\n');
}
#endif
