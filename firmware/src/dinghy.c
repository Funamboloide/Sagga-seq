/* SPDX-License-Identifier: GPL-3.0-only */
/*
 * SAGGA SEQ 0.7 - MIDI-only performance sequencer for M-VAVE FM-1.
 * Built as an application on top of Dinghy's platform (Felucca/SLOOP lineage).
 *
 * 0.3: sixteen tracks, loops between two steps, early and late steps (the engine looks one step ahead), CC lanes that
 * lock a value to a step, sixteen LFOs, twelve arpeggio modes, live FX and a DJ-style loop, COOK and the BEAT library,
 * REC quantised or free, Song Position Pointer, eight project slots, note names, a screen with big parameters.
 * 0.4: tools on several tracks at once (the scope), COOK / RANDOM on notes, CC and LFOs, the dice, EVOLVE and FREEZE,
 * drum tracks (finger drumming, a drum view on the grid), chord progressions, a library of bass / UK / techno / house /
 * reggaeton / batida / gqom / experimental, TEMP, song mode, tap tempo, step recording.
 * 0.5: lengths per parameter (notes, velocities, gates), QUANTISE for patterns / scenes / mutes, a Program Change per
 * scene and channel, MORPH between the CC values of two scenes, REPEAT (a held loop that lands where the music would be),
 * RELOAD, MIDI LEARN of the CC numbers, the song follows the Song Position, SAGGA REMOTE (commands on MIDI channel 14),
 * the project library on the Raspberry Pi (sagga_live.c).
 * 0.6 foundation: long gates, live Euclid, custom scope, direct PERF solo, step locks and musical EVOLVE.
 * 0.7: clean SGQ7 engine, native voicing/strum, per-track MIDI FX and non-destructive live algorithms.
 * 0.8: SGQ8; the live layer per track (EUCLID LIVE, TURING, CELL, ACCENT, DENSITY) heard and seen as it plays; the
 * HARMONY (a progression of the genre, live: FOLLOW tracks move to its chords); SNAPSHOTS (the whole live state, the synths'
 * CC values, their patches through the Pi); knobs that always find 0 again and turn faster when turned fast; MUTE, KILL
 * and STOP end every note (long ones, strums, echoes); the dice remember sixteen rolls; two USB ports if asked.
 * 0.5.1: one map of the controls (docs/SAGGA-SEQ.md): the held button picks the group, OCT the page, K1-K4 the values,
 * the white keys the steps; no control does what another one already does. LOOP and REPEAT are one gesture (tap: it
 * stays; hold: it lands in time), TRANSPOSE the key (quantised), RETRIG, STOP at the end of the bar, RESTART, the
 * macros (FX + K1-K4), the MASTER knob can be TEMPO, MORPH or FILTER, copy / paste / clear a step (EDIT + black).
 * Files: this one is the engine and the panel; sagga_gen.c the generators; sagga_live.c the live tools of 0.5;
 * sagga_ui.c the screen; sagga_store.c
 * projects in flash and the SysEx dump; sagga_grid.c the two Launchpads (docs/SAGGA-GRID.md); sagga_seq_core.c the
 * logic that needs no hardware and sagga_beats.c the pattern library (both tested on a computer).
 *
 * Package identity FM-1_95N (N = the minor version, tools/build.py): SAGGA SEQ's own, apart from Dinghy's 99N.
 */
#define APP_NAME "SAGGA SEQ"
#define SQ_VERSION "0.28.1"
#define APP_SILENT 1                           /* 0.22: no sound comes out of this app (platform.c: the audio interrupt only acknowledges) -
                                                * 0.26: but the metronome's click, when it is the FM-1's own sound (app_audio_wants) */
#include "platform.c"
#include "sagga_seq_core.c"
#include "sagga_beats.c"
#include "sagga_theory.c"                              /* 0.23: the THEORY engines - a part made from the rules of a style */
_Static_assert(BRK_GENRES == SQ_GENRES, "a BREAK chop list for every genre of the library (sagga_seq_core.c BRK_GENRE)");

/* 0.11 the PC test (sagga_test.c): the buttons, keys and knobs the PC presses, beside the hands' (which stop it). The app
 * reads the panel through in_held() / in_notes(); tst_booted: this boot is the test's (no project, no slots) */
static uint32_t tst_buttons, tst_notes, tst_edges;
static int32_t tst_enc[8];
static uint8_t tst_on, tst_booted, tst_listen;      /* 0.20.3 tst_listen: the PC asked the test to hear the ports too */
static void tst_heard(uint8_t st, uint8_t d1, uint8_t d2, uint8_t cab);   /* ... and to say where each message came */
static uint32_t in_held(void) { return fm1_in.buttons | tst_buttons; }
static uint32_t in_notes(void) { return fm1_in.notes | tst_notes; }
static uint32_t tst_hands(uint32_t edges);           /* the hands' edges while the PC asks or tests: 1 = taken */
static const char TST_SLOTS_OFF[] = "PC TEST: SLOTS OFF";
static void tst_abort(const char *why);
static void tst_sysex_in(const uint8_t *p, uint32_t n);

#define SQ_NO_PENDING    255u
#define SQ_KEY0          53u /* FM-1 key 0 = F3 */
#define SQ_HOLD_MS       380u
#define SQ_LOOPHOLD_MS   300u   /* a step held this long, then another: the loop between them */

#define C_ACCENT RGB(210, 170, 255)
#define C_ON     RGB(110, 220, 170)
#define SQ_C_DIM    RGB(75, 75, 82)
#define SQ_C_OUT    RGB(38, 38, 44)
#define C_WARN   RGB(255, 190, 90)
#define C_PLAY   RGB(255, 100, 100)
#define C_CYAN   RGB(110, 200, 235)

static sq_project_t project __attribute__((section(".pool")));
#define U_ROWS 16u                                   /* 0.10: undo is a ring of 16 pattern rows shared by the last edits */
static sq_step_t undo_row[U_ROWS][SQ_STEPS] __attribute__((section(".pool")));
static sq_step_t clip_row[SQ_STEPS] __attribute__((section(".pool")));      /* COPY / PASTE */
static uint8_t clip_len, clip_valid;
static sq_track_rt_t tr[SQ_TRACKS];

/* the step being played by a track */
typedef struct {
    const sq_step_t *step;
    uint32_t ratchet_next_us;
    uint32_t slice_us;
    uint32_t off_us[SQ_POLY_OUT];
    uint32_t slot_start_us;        /* where the step's slot began (the grid), for REC */
    uint32_t slot_dur_us;
    uint8_t active_note[SQ_POLY_OUT];
    uint8_t active_ch[SQ_POLY_OUT];/* the channel each note went out on: its note-off follows it even if the track moves */
    uint8_t vnote[SQ_POLY_OUT];    /* 0.10: the notes that play (a chord shape may be six: more than a step holds) */
    uint8_t vn;
    uint8_t ratchet_left;
    uint8_t ratchet_total;
    uint8_t first_ratchet;
    uint8_t step_index;            /* the step of the slot, for the screen and for REC */
    uint8_t arp_n;                 /* notes in arp[] (0: the step plays as a block chord) */
    uint8_t arp_pos;               /* the next note of the arpeggio; it keeps running from step to step */
    uint8_t lane_locked;           /* bit per lane: a step has set it, and it has not been put back */
    uint8_t arp[SQ_ARP_OUT];
    sq_step_t buf;                 /* the step as it plays: notes, velocity and gate (0.5: from other steps); 0.8: its notes
                                    * are the MIDI notes that go out (the key, the HARMONY, TURING and the voicing done) */
    uint8_t expo;                  /* 0.10: 1 the slices follow expo_t[] (from first_us); 2 SETTLE: computed as they go */
    uint32_t first_us, span_us;
    uint32_t x_pos;                /* SETTLE: where the hit playing is, us from first_us */
    uint32_t expo_t[SQ_X_HITS_MAX];
    uint8_t x_hits;                /* 0.10: the hits of this span (the energy may have changed them) */
    uint8_t strum_mask;            /* 0.8: notes of a strummed chord that start later (bit per note slot) */
    uint8_t strum_held;            /* ... long notes among them */
    uint8_t strum_note[SQ_POLY_OUT], strum_ch[SQ_POLY_OUT], strum_vel[SQ_POLY_OUT];
    uint32_t strum_on[SQ_POLY_OUT], strum_off[SQ_POLY_OUT];
    uint32_t arp_until_us;         /* 0.10: an arpeggio with a rate runs through the empty steps until here (HOLD: always) */
    uint8_t arp_going;             /* 0.10: the arpeggio was continued into an empty step (no lanes, no new chord) */
    uint8_t arp_wait;              /* 0.18: a slow RATE: the steps to go before the next note */
} track_event_t;

/* a step that starts before its slot (nudge < 0): it is decided one step ahead and waits for its time */
typedef struct {
    const sq_step_t *step;
    uint32_t start_us, dur_us;
    uint8_t state;                 /* 0 nothing, 1 armed, 2 decided not to play */
    uint8_t idx;
    sq_step_t buf;
} pre_event_t;

static track_event_t ev[SQ_TRACKS];
static pre_event_t pre[SQ_TRACKS];
static uint32_t sq_rng_state = 0x53414747u;
static uint32_t global_clock;
static uint32_t lfo_carry;                 /* ticks of the earlier runs: LFOs without RETRIG do not start over */
static uint32_t next_master_clock_us;
static uint32_t last_master_tick_us;
static uint32_t clock_recoveries;
static uint32_t ext_clock_us = 20833u;
static uint32_t last_ext_clock_us;
static uint8_t playing;
static uint8_t record_arm;
static uint8_t rec_quant = 1u;             /* 1 quantised: the nearest step; 0 free: the note keeps its timing */
static uint16_t mute_mask, solo_mask;
static uint8_t pending_scene = SQ_NO_PENDING;
static uint8_t scene_cursor;
static uint8_t selected_track;
static uint8_t cursor_step;
static uint8_t page;
static uint8_t perf_mode;
static int8_t key_octave;
static uint8_t home_page, lfo_page, lfo_sel;
static uint8_t mod_slot;                                /* 0.20: the MOD MATRIX slot LFO page 6 shows */
static uint8_t ui_dirty = 1u;
static uint8_t grid_dirty = 1u;
static uint32_t msg_until;
static const char *msg_text;
static char msg_buf[64];                     /* (two lines of 29 on the screen) */
static char ui_b[64];                        /* 0.21: the screen's lines while they are written (sagga_ui.c: ui_build) */

static uint8_t white_key[16], black_key[11], white_count, black_count;
static uint32_t prev_keys, prev_held;
static uint8_t live_note[27], live_ch[27];
static uint32_t live_held;                 /* keys whose live note is sounding: their note-off is sent whatever REC says */
/* 0.10: REC keeps the length too. A note recorded while playing stays open here until its key / note-off; then its
 * step gets the length it was held: a gate (% of the step) under a step, else 1.5 .. 64 steps. */
#define REC_OPEN_MAX 16u
typedef struct { uint32_t on_us, slot_us; uint8_t src, t, pat, step; } rec_open_t;   /* src: 0..127 a MIDI note, 128+k a key */
static rec_open_t rec_open[REC_OPEN_MAX];
static uint8_t rec_open_n;
static uint8_t ext_ch[128];                /* incoming MIDI notes played through: the channel (255 = not sounding) */
static uint8_t ext_out[128];               /* ... and the note that went out for it (the key may have moved it) */

#define PEN(t) (project.track[t].pen)          /* what a new step plays, per track (0.8: saved with the track) */
static uint8_t undo_valid, undo_track[U_ROWS], undo_pat[U_ROWS], undo_len[U_ROWS], undo_start[U_ROWS];
static uint16_t undo_txn[U_ROWS];                    /* the edit each row belongs to (0: free) */
static sq_thpat_t undo_th[U_ROWS];                   /* 0.23: what the engines knew of the row (it comes back with it) */
static uint16_t u_cur, u_top, u_seq;                 /* the edit being recorded; the newest one UNDO takes; the counter */
static uint8_t seq_page;                   /* SEQ + K1..K4: Euclid / random / heat, then scope and EVOLVE, then harmony */
static uint32_t sq_midi_in_n;              /* MIDI messages received (the diagnostics page counts them a second) */
static uint32_t diag_out_ps, diag_in_ps, diag_next;
static uint32_t srec_ms;                   /* step recording (REC while stopped): the last note, and the cursor moves on */
static uint8_t srec_next;
static void gen_bar_tick(void);            /* sagga_gen.c: EVOLVE, the CELL generations, at bar lines */
static uint8_t live_hit(uint32_t t, uint8_t step, uint8_t written, uint8_t *ghost);   /* sagga_gen.c: the live layer */
static int32_t live_vel(uint32_t t, uint8_t step);
static uint8_t live_hold(uint32_t t, uint8_t step);    /* sagga_gen.c: 0.11 the length of a note an algorithm places */
static int32_t live_note_deg(uint32_t t);
static void live_step_done(uint32_t t);
static void live_loop_done(uint32_t t);
static uint8_t harm_now(int8_t *deg, uint8_t *col);
static uint8_t harm_chord(sq_hchord_t *c, uint8_t *idx);   /* sagga_gen.c: 0.11 the chord playing */
/* 0.26 LIVE CHORDS (KEYBOARD: CHORDS, SAVE 4 K2; sagga_live3.c): the chord the keyboard holds, or held last, IS the
 * harmony's chord - whatever the progression says, and with the HARMONY off too - until the keyboard is given back */
static sq_hchord_t kb_chord;
static uint8_t kb_chord_on;
static void gen_custom_toggle(uint8_t t);
static void song_bar_tick(void);
static void song_start_hook(void);
static uint32_t chord_entry_ms;
static uint32_t knob_ref;
static uint8_t knob_live;
static uint8_t prev_note = SQ_NOTE_NONE, prev_ch;
static uint32_t prev_off_ms;

static uint8_t grid_attached;      /* a Launchpad bridge is talking to us (sagga_grid.c) */
static uint8_t grid_fill;          /* a FILL pad is held on the grid */
static uint16_t grid_fx;           /* FX pads held on the grid */
static uint16_t grid_kill;         /* tracks whose KILL pad is held on the grid */
static int grid_midi_in(uint8_t st, uint8_t d1, uint8_t d2);
static void grid_service(void);
static void grid_init(void);

/* live FX: bit per effect, from the keys of the panel (while FX is held) and the pads of the grid */
enum { FX_FILL = 0, FX_ST2, FX_ST4, FX_ST8, FX_HALF, FX_DOUBLE, FX_REV, FX_FREEZE, FX_RND, FX_OCTUP, FX_OCTDN, FX_FIFTH,
       FX_MAXVEL, FX_STACC, FX_LEGATO, FX_KILL, FX_COUNT };
static const char *const FX_NAME[FX_COUNT] = {"FILL", "ST2", "ST4", "ST8", "HALF", "DBL", "REV", "FRZ", "RND", "O+", "O-",
                                              "5TH", "MAX", "STC", "LEG", "KILL"};
static uint16_t fx_panel;
static uint16_t fx_now(void) { return (uint16_t)(fx_panel | grid_fx); }

/* the DJ loop: from the moment it starts, the tracks come back to where they were every loop_len ticks */
static const uint16_t LOOP_TICKS[8] = {3u, 6u, 12u, 24u, 48u, 96u, 192u, 384u};
static uint8_t loop_on;
static uint16_t loop_len, loop_mask;
static uint32_t loop_t0;
static sq_track_rt_t loop_snap[SQ_TRACKS];

/* LFO working values: what the LFOs that move a track's parameters add now (index = destination - 1) */
static int16_t lfo_mod[SQ_TRACKS][SQ_LD_KINDS - 1u];
static uint8_t lfo_last[SQ_LFOS];
static uint8_t lfo_last_valid[SQ_LFOS];
static uint32_t lfo_sent_ms[SQ_LFOS];
static uint32_t lfo_trig_us[SQ_LFOS];          /* 0.13: when the LFO's track last hit (its TRIG) */
static uint16_t lfo_trig_seen;                 /* ... bit per LFO: it has been hit since PLAY (before: it holds at its end) */
static uint8_t rseq_pos;                       /* 0.13: LFO 4 RATE SEQ: the entry K3 / K4 show */

/* 0.5 (sagga_live.c has the rest) */
static uint16_t pending_mute;              /* mutes that wait for the quantised moment: bit = toggle that track */
static uint8_t morph_pos, morph_dirty;     /* MORPH: 0 the scene playing .. 127 project.live.morph_b */
static uint32_t lp_held;                   /* LOOP / REPEAT: the pads, keys, remote buttons that hold it (see loop_press) */
static uint8_t loop_latched;               /* a LOOP that stays (it was tapped) */
static uint16_t latched_len;
static uint8_t pc_last[SQ_CHANNELS];       /* the Program Change sent last on each channel (255: none yet) */
static uint8_t remote_fill;                /* SAGGA REMOTE: FILL held */
static uint16_t remote_kill;               /* ... the tracks killed while held */
static uint8_t env_lane;                   /* the lane whose knob was turned last with ENV (LEARN on the panel) */
/* 0.5.1 */
#define mac_vel   (project.live.mac[0])    /* FX + K1..K4: the macros (0.10: saved with the project) */
#define mac_gate  (project.live.mac[1])
#define mac_swing (project.live.mac[2])
#define mac_filt  (project.live.mac[3])
static uint8_t filt_dirty, filt_t;         /* the FILTER macro moved: lane 1 of every track goes out again */
/* 0.10: time. The tracks are counters; what the counters should say is sq_track_seek from the track's anchor. After a
 * length change, a loop between two steps, a time FX let go, a loop ended, the tracks are put back where they belong. */
static uint16_t realign_pend;              /* tracks to realign at the next tick */
static uint16_t tup_wait;                  /* 0.25, the polyrhythms: tracks whose step begins before the next tick ... */
static uint32_t tup_at[SQ_TRACKS];         /* ... and when (div_frac_x, tup_service) */
/* 0.25 THE METRE: the bar is sq_bar_steps(&project.gen) 16ths - sixteen until 0.24, whatever the tracks did: a bar line
 * was `global_clock % 96 == 0`. Its lines are counted from bar_origin (a line; 0 at PLAY and after a song position),
 * with bar_base bars before it: a bar changed while it plays begins on a line of the old one (metre_apply). */
static uint32_t bar_origin, bar_base;
/* 0.26 THE CLICK (sagga_click.c): what the main loop asks of the audio interrupt, the MIDI click's note that sounds,
 * the count before a recording */
static volatile uint8_t clk_req, clk_req_level;   /* a click of the FM-1's own sound waits: 1 a beat, 2 the bar line; how loud */
static volatile uint32_t clk_req_at;       /* ... the moment it must begin, in the timer's ticks (fm1_ticks) */
static sq_click_t clk_voice;               /* the click that sounds (the interrupt's alone) */
static uint32_t clk_next;                  /* the first clock tick nobody has looked at yet for a click asked ahead */
static uint8_t clk_off_ch = 255u, clk_off_note;   /* a MIDI click's note: its off ... */
static uint32_t clk_off_us;                /* ... and when */
static uint32_t clk_count, clk_last_tick;  /* the clicks since power-on, the tick the last was for (the probe) */
static uint8_t clk_last;                   /* ... and what it was: 1 a beat, 2 the bar line */
static uint8_t cnt_on;                     /* the count runs */
static uint16_t cnt_pos, cnt_len;          /* its tick, its length in clock ticks */
static uint32_t cnt_next_us, cnt_ahead;    /* when its next tick is due; the first of its ticks no click was asked for yet */
static void click_tick(uint32_t now);
static void click_quiet(void);
static uint8_t bar_pend_steps;             /* a bar asked while it plays waits for the bar line (0: none) ... */
static uint32_t bar_pend_beats;            /* ... with these beats */
/* the project's metre as the machine uses it, read once when it changes - by a knob, a project loaded, anyone
 * (metre_sync: the five bytes compared; the main loop calls it too): the bar's steps, its beats (a mask), its number
 * (sq_metre_id: 0 is 4/4), and the core's grid of the bar (sq_g16: the dice, COOK, the DENSITY, the GROOVE) */
static uint8_t metre_raw[5], metre_known, metre_st = 16u, metre_idn;
static uint32_t metre_bt = SQ_BEATS_44;
static void metre_sync(void)
{
    const sq_gen_t *g = &project.gen;
    if (metre_known && g->bar_steps == metre_raw[0] && !memcmp(g->bar_beats, metre_raw + 1, 4u)) return;
    metre_raw[0] = g->bar_steps; memcpy(metre_raw + 1, g->bar_beats, 4u); metre_known = 1u;
    metre_st = sq_bar_steps(g); metre_bt = sq_bar_beats(g);
    metre_idn = sq_metre_id(metre_st, metre_bt);
    sq_grid_set(metre_st, metre_bt);
}
static uint8_t bar_st(void) { metre_sync(); return metre_st; }             /* the bar in 16ths */
static uint32_t bar_bt(void) { metre_sync(); return metre_bt; }            /* its beats */
static uint8_t metre_id_now(void) { metre_sync(); return metre_idn; }
static uint8_t metre_44(void) { return (uint8_t)(metre_id_now() == 0u); }
static uint32_t bar_ticks(void) { return (uint32_t)bar_st() * 6u; }
static uint32_t bar_into(void) { return (global_clock - bar_origin) % bar_ticks(); }            /* ticks since the bar's line */
static uint32_t bar_no(void) { return bar_base + (global_clock - bar_origin) / bar_ticks(); }   /* the bars since PLAY */
static uint8_t bar_beat_now(void)          /* this tick is a beat's first (a bar line is one) */
{
    uint32_t in = bar_into();
    return (uint8_t)(in % 6u == 0u && ((bar_bt() >> (in / 6u)) & 1u));
}
static uint8_t bar_beat_le(uint8_t s)      /* the first step of the beat step s of the bar is in (4/4: s & ~3) */
{
    uint32_t b = bar_bt();
    if (s >= bar_st()) s = (uint8_t)(bar_st() - 1u);
    while (s && !((b >> s) & 1u)) s--;
    return s;
}
static uint16_t fx_pos_prev;               /* the time FX held at the last tick */
#define FX_POS ((1u << FX_HALF) | (1u << FX_DOUBLE) | (1u << FX_REV) | (1u << FX_FREEZE) | (1u << FX_RND))
static uint16_t sl_on;                     /* 0.10: a loop between two steps is on (bit per track): EXIT puts the loop back */
static sq_ghost_t gh_st[SQ_TRACKS];        /* 0.24: what the copies of the pattern each track plays were made from (ghost_service) */
static uint8_t gh_at;                      /* the track that service looks at next */
static int8_t lens_pend;                   /* 0.25: LONGER (+1) / SHORTER (-1) asked from the tablet waits for the bar (lengths_ask) */
static uint8_t sl_prev_start[SQ_TRACKS], sl_prev_len[SQ_TRACKS];
static uint16_t panic_cc;                  /* 0.10 PANIC: the channels still to get their All Notes Off (paced) */
static uint16_t panic_snd;                 /* ... and All Sound Off too (the PANIC gesture; a STOP leaves the tails) */
static uint32_t panic_ms;                  /* when PANIC was last pressed (0: never) */
static uint32_t glo_down_ms;               /* 0.10: PERF toggles when the button is let go (held + OCT-/+ is the octave) */
static uint8_t glo_used;
static uint8_t selglo_pend;                                /* 0.12: SEL + GLO pressed, waiting for the release (0.17: the MOSSE) */
static void vg_panel_toggle(void);                         /* sagga_viaggio.c */
static uint8_t tie_pend[SQ_TRACKS];        /* 0.10 TIE: the step playing holds into the next one */
static uint8_t lane_rec[SQ_TRACKS];        /* 0.10: lanes being recorded (bit per lane) with REC: the knob writes the step playing */
static uint8_t lane_rec_val[SQ_TRACKS][SQ_LANES];
static uint32_t lane_rec_ms;
static uint8_t tool_due_tool = 255u;       /* 0.10 WHEN: the tool that waits for its bar (255: none) */
static uint32_t tool_due_bar;              /* ... the bar it runs at */
static uint32_t every_next_bar;            /* 0.10 EVERY: the bar the tool runs again at */
#define SQ_KT_NONE 127
static int8_t ktrans_pend = SQ_KT_NONE;    /* TRANSPOSE waiting for the QUANTISE moment */
static uint16_t retrig_mask;               /* RETRIG: these tracks start from their first step at their next step */
static uint8_t restart_pend, stop_at_bar;  /* RESTART (all tracks, at the QUANTISE moment), STOP at the end of the bar */
static uint8_t arp_last[SQ_TRACKS];        /* the arp mode a tap of ARP switches on again (0: UP) */
static uint8_t perf_solo_mode;              /* PERF OCT+ = white keys solo, OCT- = mute */
/* 0.8 */
static uint8_t echo_global;                 /* FX + OCT+: every track echoes (a dotted eighth, twice), until again */
static uint16_t audible_prev = 0xFFFFu;     /* the tracks that could be heard at the last pass (audible_service) */
static uint8_t usb_ports = 1u;              /* USB MIDI ports: 1, or 2 (the grid on the second; the tracks get 15, 16) */
/* the live layer's state (sagga_gen.c): it stays when the knobs turn; it is made again when the algorithm changes */
/* 0.11: the algorithms' state, one per slot of every track (SQ_ALGO_SLOTS) */
static uint64_t tm_reg[SQ_TRACKS][SQ_ALGO_SLOTS];   /* TURING: the register (0.25: up to 64 steps, a track's whole loop) */
static uint8_t tm_len[SQ_TRACKS][SQ_ALGO_SLOTS];    /* ... the steps it has now; bit 7: it was as long as the track (LENGTH TRACK) */
static uint64_t ca_row[SQ_TRACKS][SQ_ALGO_SLOTS];   /* CELL: the generation playing */
static uint8_t algo_seen[SQ_TRACKS][SQ_ALGO_SLOTS]; /* the algorithm the state was made for (255: none yet) */
static uint8_t ca_bars[SQ_TRACKS][SQ_ALGO_SLOTS];   /* CELL: bars since the last generation */
static uint8_t algo_cur[SQ_TRACKS];         /* 0.11: the slot the panel and the grid show and edit (0..3) */
static uint8_t algo_pend[SQ_TRACKS][SQ_ALGO_SLOTS];   /* 0.16: the algorithm READY on a slot, for SEQ + white 6 (0: none) */
static sq_algo_t algo_mem[SQ_TRACKS][SQ_ALGO_SLOTS][SQ_ALGOS];   /* 0.16: the values of each algorithm of a slot (.algo: set) */
static uint8_t live_ghost[SQ_TRACKS];       /* DENSITY: the step playing is a hit it added */
/* SNAPSHOTS (sagga_live.c) */
static uint8_t snap_cur = 255u;             /* the snapshot playing, or stored last (255: none) */
static uint8_t snap_pend = 255u;            /* recalled, waiting for the QUANTISE moment */
static uint8_t snap_capture;                /* CC CAPTURE on: the CCs that come in go into snapshot snap_cur */
static uint8_t snap_tx_on;                  /* a snapshot's sound is being sent */
static void snap_apply(uint8_t n);
static uint8_t snap_cc_in(uint8_t ch, uint8_t cc, uint8_t v);

/* the ornaments of the MIDI effects (HARM, ECHO, the global ECHO): notes that start later. Fixed size: when it is full a
 * new ornament takes the place of the faintest one still waiting (the last repeats of an echo), or is not played if it
 * is the faintest itself; the notes of the patterns (and of a strum) never go through it (0.8). */
#define SQ_DEFER_MAX 128u
typedef struct { uint32_t on_us, off_us; uint8_t track, ch, note, vel, state, glob; } defer_note_t;   /* glob: the global ECHO's */
static defer_note_t defer_note[SQ_DEFER_MAX];

#define SQ_HOLD_MAX 12u
static uint8_t hold_note[SQ_TRACKS][SQ_HOLD_MAX];
static uint8_t hold_ch[SQ_TRACKS][SQ_HOLD_MAX];
static uint32_t hold_off_us[SQ_TRACKS][SQ_HOLD_MAX];
/* 0.11 FOLLOW RETRIG / LEGATO: the step a track's held notes came from, their velocity, the clock tick they began */
static sq_step_t harm_src[SQ_TRACKS];
static uint8_t harm_src_vel[SQ_TRACKS], harm_src_on[SQ_TRACKS];
static uint32_t harm_src_tick[SQ_TRACKS];
static uint8_t save_knob;                  /* a knob was turned with SAVE held: letting SAVE go is not a save */
static uint8_t expo_hold[SQ_TRACKS];       /* 0.10 EXPO: steps of the span playing that still have to pass */
static uint8_t expo_plain[SQ_TRACKS];      /* 0.10: the span running began on a plain step (EDIT + black 5): the steps play as written */
static uint8_t vg_expo_hits(uint8_t h);    /* sagga_viaggio.c */
static void song_seek(uint32_t ticks);     /* sagga_gen.c */
static void undo_redo(void);               /* sagga_gen.c: 0.10 */
static void undo_begin(void);              /* sagga_gen.c: a group of rows UNDO takes back together */
static void undo_add(uint8_t t, uint8_t pat);
static uint8_t track_tape(uint32_t t);     /* sagga_tape.c: 0.11 */
static uint8_t track_drum(uint32_t t);     /* sagga_gen.c */
static void tape_clock_tick(uint32_t now, uint32_t interval);
static void tape_service(uint32_t now);
static void tape_track_off(uint32_t t);
static void tape_all_off(void);
static void tape_rec_on(uint8_t src, uint8_t t, uint8_t note, uint8_t vel);
static void tape_rec_off(uint8_t src);
static void tape_tool(uint8_t t, uint8_t tool);
static void tape_grid_render(uint32_t t);
static void tape_grid_pad(uint32_t t, uint8_t x, uint8_t y);
static void remote_cc(uint8_t cc, uint8_t v);              /* sagga_live.c */
static uint8_t learn_take_v(uint8_t ch, uint8_t cc, uint8_t v);   /* 0.10: the value too */
static uint8_t learn_kind;                                 /* sagga_live.c: LEARN armed (store_loaded clears it) */
static void reload_request(void);
static void transport_stop(void);
static void lib_transport_stopped(void);                   /* sagga_store.c: a library load waiting for STOP */
static void quant_set(uint8_t q);                          /* sagga_live.c */
/* 0.9 sagga_viaggio.c */
static void vg_bar_tick(void);
static void vg_beat_tick(void);            /* 0.10 */
static int32_t vg_vel_adj(uint32_t t);
static int32_t vg_filt_adj(void);
static int32_t vg_gate_adj(void);
static uint8_t vg_density_hit(uint32_t t, uint8_t on, uint32_t rel, uint32_t h, uint8_t *ghost);
static uint8_t vg_color7(void);
static uint8_t vg_lfo_pct(void);
static void vg_transport_start(void);
static void vg_transport_stop(void);
static void vg_reset(void);
static void vg_move_black(int bi, uint8_t sel_held);       /* 0.17: the MOSSE (PERF page 3) */
static uint8_t vg_mosse_shown(void);
static uint8_t vg_move_lit(int bi, uint8_t blink);
static uint8_t perf_page;                                  /* (GLO's page: 0.17 the MOSSE on the third) */
static void vg_pattern_in(uint32_t t);                     /* 0.17: a pattern entered by the hands: a proposal's settings */
static uint8_t vg_prop_queue(uint8_t t);                   /* 0.17 PRESETS: a proposal waiting is queued first */
static void vg_quant_turn(int32_t d);
static void vg_service(void);
static void vg_back(void);
static void vg_cancel_last(void);
static void vg_seed(void);
static void vg_energy_turn(int32_t d);
static void vg_energy_set(uint8_t e);
static void vg_bars_turn(int32_t d);
#ifdef DINGHY_HOST
static void vg_host_dump(void);                            /* the journey, for the tests */
#endif
static void vg_genre_turn(int32_t d);
static void vg_key_turn(int32_t d);
static void vg_prog_turn(int32_t d);
static void vg_browse(uint8_t t, int32_t d);
static void vg_remote_cc(uint8_t cc, uint8_t v);
static uint8_t vg_remote_ch(uint8_t ch);                   /* ch (0..15) is VIAGGIO's remote channel */
static void vg_state_sync(uint32_t t);                     /* 0.12: a track's VIAGGIO state follows the hand */
static void vg_states_sync_all(void);
static void remote13_note(uint8_t d1, uint8_t d2, uint8_t on);   /* sagga_remote2.c: 0.12 the pads on channel 13 */
static void vg_profile_note(void);
static uint8_t vg_seq_shown(uint8_t page);                /* 0.27: SEMPLICE hides SEQ 2 and 3 (sagga_viaggio.c) */
static void vg_profile_boot(void);
/* 0.9 the regista (sagga_viaggio.c) */
static void regia_sysex_in(uint8_t cmd, const uint8_t *p, uint32_t n);
static void regia_bar(void);
static void regia_transport_start(void);
static void regia_service(void);
static void regia_touched(uint8_t t);
static void regia_key_send(uint8_t rule);
static uint8_t g_regia_led[16];
static void rg_frase_apply(void);
static void vg_save_journey(void);
static uint8_t vg_edit_keys(void);
static uint16_t vg_mutes_to_keep(void);                    /* the mutes without a BREAK's silence (a save, a snapshot) */
static uint8_t vg_allows_home(uint8_t page);
static uint8_t vg_fill;                                    /* FILL in the last bar of the phrase */
static uint8_t vg_rec_t;                                   /* LOOP: the track recording this phrase (255: none) */
static uint8_t vg_profile;                                 /* the profile (settings) */
static void mute_q_toggle(void);
static void morph_set(uint8_t pos);
static void morph_target(uint8_t b);
static void scene_pc_set(uint8_t s, uint8_t ch, int32_t pc);
static void learn_arm(uint8_t kind, uint8_t t, uint8_t l);
static void live_service(void);

static int time_due(uint32_t now, uint32_t due) { return (int32_t)(now - due) >= 0; }

#ifdef DINGHY_HOST
#define SQ_LOG_RECOVERY(why) printf("%6u ms  clock recovery (%s)\n", fm1_ms, why)   /* the host tests count them */
#else
#define SQ_LOG_RECOVERY(why) ((void)0)
#endif

/* The sequencer keeps its deadlines (clock tick, note-off, ratchet) as 32-bit microsecond stamps and
 * compares them with time_due(), which is only right if the clock wraps at exactly 2^32 us.
 * fm1_micros() is TIMER4 / 24, so it wraps every 178.96 s (2^32 / 24 us): a deadline stored just
 * before the wrap stays "in the future" for a whole wrap and the clock froze until STOP/PLAY.
 * This one is built from the raw 24 MHz ticks and wraps at 2^32 us (71.6 min).
 * Main loop only (it keeps state), and it must be called at least once every ~170 s. */
static uint32_t sq_micros(void)
{
    static uint32_t last_ticks, rem_ticks, us;
    uint32_t t = fm1_ticks();
    uint32_t d = (uint32_t)(t - last_ticks) + rem_ticks;
    last_ticks = t;
    us += d / FM1_TICKS_PER_US;
    rem_ticks = d % FM1_TICKS_PER_US;
    return us;
}
static int32_t clamp_i32(int32_t v, int32_t lo, int32_t hi) { return v < lo ? lo : v > hi ? hi : v; }
static uint8_t clamp_note(int32_t v) { return (uint8_t)clamp_i32(v, 0, 127); }

/* 0.8: a value that moves `d` steps of `step` lands on a multiple of `step`: 0 (and the middle of every range) can
 * always be reached again, whatever happened at the ends (0.5.1 went 63, 59 ... 3, -1 and never 0) */
static int32_t kstep(int32_t v, int32_t d, int32_t step, int32_t lo, int32_t hi)
{
    int32_t q;
    if (step < 1) step = 1;
    if (!d) return clamp_i32(v, lo, hi);
    q = v >= 0 ? v / step : -((-v + step - 1) / step);           /* floor(v / step) */
    if (d > 0) v = (q + d) * step;
    else v = (q * step == v ? q + d : q + 1 + d) * step;           /* (from between two multiples: the one under counts) */
    return clamp_i32(v, lo, hi);
}

/* 0.8: the encoders turn faster when they are turned fast: detents less than 45 ms apart make a run; after 3 of them a
 * detent counts 2 steps, after 6 it counts 4 (enc_fast says by how much; the values that want it use kstep with it).
 * A slow turn is always one step a detent, and so is a turn back (overshot: the way back is fine). */
static uint32_t enc_last_ms[8];
static uint8_t enc_run[8];
static uint8_t enc_mult[8];
static int8_t enc_dir[8];
static int32_t enc_take(uint32_t e)
{
    int32_t d = fm1_enc_take(e);
    if (d && tst_on) { tst_abort("A KNOB TURNED BY HAND"); d = 0; }   /* (0.11: a hand stops the PC test) */
    if (e < 8u) { d += tst_enc[e]; tst_enc[e] = 0; }
    if (e >= 8u) return d;
    if (d) {
        uint32_t gap = (uint32_t)(fm1_ms - enc_last_ms[e]);
        int32_t n = d < 0 ? -d : d;
        int8_t dir = d < 0 ? -1 : 1;
        enc_last_ms[e] = fm1_ms;
        if (gap < 45u && dir == enc_dir[e]) enc_run[e] = (uint8_t)(enc_run[e] + n > 250 ? 250 : enc_run[e] + n);
        else enc_run[e] = 0u;                                      /* (the first detent of a turn is always one step) */
        enc_dir[e] = dir;
        enc_mult[e] = enc_run[e] >= 6u ? 4u : enc_run[e] >= 3u ? 2u : 1u;
    }
    return d;
}
static int32_t enc_fast(uint32_t e) { return e < 8u && enc_mult[e] ? enc_mult[e] : 1; }
static uint8_t is_black(uint32_t note) { return (uint8_t)((0x54Au >> (note % 12u)) & 1u); }
static uint8_t change_u8(uint8_t v, int32_t d, uint8_t lo, uint8_t hi)
{
    return (uint8_t)clamp_i32((int32_t)v + d, lo, hi);
}

/* the text writers: a message longer than msg_buf is cut (0.7 wrote past its end: "CC CAPTURE ON ..." found it).
 * 0.21: a line of the screen longer than ui_b too. It was 64 bytes of ui_build's stack and nothing cut it: the line
 * of what is going on (DICE? EVOLVE LOOP MACRO MORPH ECHO ALL STEP LOOP ... together) went past its end */
static char *put_c(char *d, char c)
{
    uintptr_t a = (uintptr_t)d;
    if (a == (uintptr_t)msg_buf + sizeof msg_buf - 1u || a == (uintptr_t)ui_b + sizeof ui_b - 1u) return d;   /* (the last byte: the end mark) */
    *d++ = c;
    return d;
}
static char *put_s(char *d, const char *s) { while (*s) d = put_c(d, *s++); return d; }
static char *put_u(char *d, uint32_t v)
{
    char b[10]; uint32_t n = 0;
    if (!v) return put_c(d, '0');
    while (v && n < sizeof b) { b[n++] = (char)('0' + v % 10u); v /= 10u; }
    while (n) d = put_c(d, b[--n]);
    return d;
}
static char *put_i(char *d, int32_t v)
{
    if (v < 0) { d = put_c(d, '-'); v = -v; }
    else d = put_c(d, '+');
    return put_u(d, (uint32_t)v);
}
static char *put_note(char *d, uint8_t n)
{
    char b[8];
    sq_note_name(n, b);
    return put_s(d, b);
}
static void finish(char *p) { *p = 0; }

static uint8_t foc_on;                      /* 0.18: 1 while a command of the tablet runs (on its own track) */
static char msg_tab[72];
static void status_msg(const char *s)
{
    if (foc_on && s) {                          /* 0.18: the tablet's: the screen says so ("TAB T5: LFO ON": its track when the message has none) */
        char *p = msg_tab, *e = msg_tab + sizeof msg_tab - 1u;
        uint32_t tn = (uint32_t)selected_track + 1u;
        *p++ = 'T'; *p++ = 'A'; *p++ = 'B'; *p++ = ' ';
        if (!(s[0] == 'T' && s[1] >= '1' && s[1] <= '9') && !(s[0] == 'B' && s[1] == 'R')) {   /* ("T5 ...", "BREAK T5 ..." say it) */
            *p++ = 'T';
            if (tn >= 10u) *p++ = (char)('0' + tn / 10u);
            *p++ = (char)('0' + tn % 10u); *p++ = ':'; *p++ = ' ';
        }
        while (*s && p < e) {
            if (s[0] == 'S' && s[1] == 'E' && s[2] == 'Q' && s[3] == ' ' && s[4] == '+' && s[5] == ' ' && s[6] == 'W'
                && s[7] == 'H' && s[8] == 'I' && s[9] == 'T' && s[10] == 'E' && s[11] == ' ' && s[12] == '6') {
                *p++ = 'G'; if (p < e) *p++ = 'O';      /* (the tablet's GO is the panel's SEQ + white 6) */
                s += 13;
            } else *p++ = *s++;
        }
        *p = 0;
        s = msg_tab;
    }
    msg_text = s;
    msg_until = fm1_ms + 1600u;
    ui_dirty = 1u;
}
static void status_num(const char *label, uint32_t v)       /* "LEN 24" */
{
    char *p = msg_buf;
    p = put_s(p, label);
    p = put_u(p, v);
    finish(p);
    status_msg(msg_buf);
}
static void status_note(const char *label, uint8_t note)    /* "NOTE C#3" */
{
    char *p = msg_buf;
    p = put_s(p, label);
    p = put_note(p, note);
    finish(p);
    status_msg(msg_buf);
}

static const char *div_name(uint8_t d)
{
    static const char *const N[SQ_DIV_COUNT] = {"1/1", "1/2", "1/4.", "1/4", "1/8.", "1/4T", "1/8", "1/16.",
                                                "1/8T", "1/16", "1/16T", "1/32", "1/32T",
                                                "1/4 5:4", "1/8 5:4", "1/16 5:4", "1/4 7:4", "1/8 7:4", "1/16 7:4"};   /* 0.25: five / seven in the time of four */
    return N[d < SQ_DIV_COUNT ? d : SQ_DIV_1_16];
}
static const char *dir_name(uint8_t d)
{
    static const char *const N[SQ_DIR_COUNT] = {"FWD", "REV", "PING", "RND"};
    return N[d < SQ_DIR_COUNT ? d : 0u];
}
static const char *cond_name(uint8_t c) { return sq_cond_name(c); }
static const char *chord_name(uint8_t m)
{
    static const char *const N[SQ_CHORD_COUNT] = {"BLOCK", "UP", "DOWN", "UP-DN", "DN-UP", "UP&DN", "CONV", "DIV", "RND",
                                                  "WALK", "PLAYED", "THUMB", "PINKY"};
    return N[m < SQ_CHORD_COUNT ? m : 0u];
}
static const char *lfo_shape_name(uint8_t s)
{
    static const char *const N[SQ_LFO_SHAPES] = {"SINE", "TRI", "RAMP+", "RAMP-", "SQUARE", "S&H", "SMOOTH", "DECAY", "ENV"};
    return N[s < SQ_LFO_SHAPES ? s : 0u];
}
static const char *lfo_rate_name(uint8_t r)
{
    static const char *const N[SQ_LFO_RATES] = {"16 BAR", "8 BAR", "4 BAR", "3 BAR", "2 BAR", "1.5 BAR", "1 BAR", "3/4 BAR",
                                                "1/2 BAR", "3/8 BAR", "1/4 BAR", "3/16", "1/8 BAR", "3/32", "1/16", "1/32",
                                                "1/4T", "1/8T", "1/16T", "1/32T"};   /* (0.13: the triplets) */
    return N[r < SQ_LFO_RATES ? r : 6u];
}
static const char *lfo_dest_name(uint8_t d)
{
    static const char *const N[SQ_LD_ALL] = {"CC", "VEL", "GATE", "CHANCE", "TIMING", "SWING", "MOD ONLY"};
    return N[d < SQ_LD_ALL ? d : 0u];
}

static uint8_t ch_limit(void) { return usb_ports > 1u ? (uint8_t)SQ_CHANNELS : (uint8_t)SQ_MIDI_CH; }
/* 0.28.1: an LFO whose DEST changed keeps a target that kind has: CC the channels, the others the twelve tracks (a
 * channel 13-16 kept as the target: the screen said TRACK 14 and the LFO moved track 1) */
static void lfo_target_fit(sq_lfo_t *l)
{
    uint8_t n = l->dest == SQ_LD_CC ? ch_limit() : (uint8_t)SQ_TRACKS;
    if (l->target >= n) l->target = (uint8_t)(n - 1u);
}
static uint8_t track_ch(uint32_t t)
{
    uint8_t c = project.track[t].channel, lim = ch_limit();
    return c >= lim ? (uint8_t)(lim - 1u) : c;
}

/* the key: a track that follows it (SQ_TF_SCALE) plays every note moved by the shift and then to the nearest note of the
 * scale, so changing the root, the scale or the shift (even while it plays) changes every pattern, chord and arpeggio */
static uint8_t track_in_key(uint32_t t) { return (project.track[t].flags & SQ_TF_SCALE) ? 1u : 0u; }
/* 0.10: the key a track plays in: the one that is current, or the slot it is pinned to (HOME 4 K4) */
static const sq_key_t *track_key(uint32_t t)
{
    uint8_t s = project.track[t].key_slot;
    return &project.key[s < SQ_KEYS ? s : project.key_cur];
}
static uint8_t key_note(uint32_t t, int32_t n)       /* the written note as it plays: octave, transpose, the key */
{
    const sq_key_t *k = track_key(t);
    return sq_track_note(&project.track[t], n, k->root, k->scale, k->shift);
}
static uint8_t key_store(uint32_t t, uint8_t n)      /* what is written when a note is played: in the key, not shifted */
{
    const sq_key_t *k = track_key(t);
    return track_in_key(t) ? sq_scale_snap(n, k->root, k->scale) : n;
}
static uint8_t key_root_of(uint32_t t) { return track_key(t)->root; }
static uint8_t key_scale_of(uint32_t t) { return track_key(t)->scale; }
/* the key that plays is slot key_cur: an edit of the key writes the slot, a change of slot brings its key */
static void key_sync_slot(void)
{
    sq_key_t *k = &project.key[project.key_cur < SQ_KEYS ? project.key_cur : 0u];
    k->root = project.key_root; k->scale = project.key_scale; k->shift = project.key_shift;
}
static void key_select_slot(uint8_t s)
{
    const sq_key_t *k;
    if (s >= SQ_KEYS) return;
    key_sync_slot();
    project.key_cur = s;
    k = &project.key[s];
    project.key_root = k->root; project.key_scale = k->scale; project.key_shift = k->shift;
    ui_dirty = grid_dirty = 1u;
}

static uint8_t fill_active(void)
{
    return ((fx_now() & (1u << FX_FILL)) || grid_fill || remote_fill || vg_fill) ? 1u : 0u;
}

/* a lane's / an LFO's value out: a CC, or (0.10) pitch bend (the value is the coarse 7 bits: 64 = centre) or aftertouch */
static void send_cc(uint32_t ch, uint32_t cc, uint32_t v)
{
    if (cc == SQ_CC_BEND) midi_send(0xE0u | ch, v >= 127u ? 127u : 0u, v & 127u);
    else if (cc == SQ_CC_AT) midi_send(0xD0u | ch, v & 127u, 0u);
    else midi_send(0xB0u | ch, cc & 127u, v & 127u);
}
/* 0.10: a lane's value out, as the lane is set: a CC / BEND / AFTERT, or an NRPN (99 MSB, 98 LSB, 6 the value) */
static void lane_send(uint32_t t, uint32_t n, uint32_t v)
{
    const sq_track_cfg_t *c = &project.track[t];
    uint32_t ch = track_ch(t);
    if (n >= SQ_LANES || c->lane_cc[n] == SQ_LANE_NONE) return;
    if ((c->lane_flags[n] & SQ_LF_NRPN) && c->lane_cc[n] <= 127u) {
        midi_send(0xB0u | ch, 99u, c->lane_hi[n] & 127u);
        midi_send(0xB0u | ch, 98u, c->lane_cc[n] & 127u);
        midi_send(0xB0u | ch, 6u, v & 127u);
    } else send_cc(ch, c->lane_cc[n], v);
}
/* 0.10: a stop or a PANIC puts the pitch bend back to the centre and the aftertouch to 0 on the channels that use them */
static void bend_reset(void)
{
    uint32_t t, n, i;
    uint16_t done_b = 0u, done_a = 0u;
    for (t = 0; t < SQ_TRACKS; t++) {
        uint32_t ch = track_ch(t);
        for (n = 0; n < SQ_LANES; n++) {
            uint8_t cc = project.track[t].lane_cc[n];
            if (cc == SQ_CC_BEND && !(done_b & (1u << ch))) { done_b |= (uint16_t)(1u << ch); midi_send(0xE0u | ch, 0u, 64u); }
            if (cc == SQ_CC_AT && !(done_a & (1u << ch))) { done_a |= (uint16_t)(1u << ch); midi_send(0xD0u | ch, 0u, 0u); }
        }
    }
    for (i = 0; i < SQ_LFOS; i++) {
        const sq_lfo_t *l = &project.lfo[i];
        uint32_t ch = l->target < ch_limit() ? l->target : 0u;
        if (!l->enabled || l->dest != SQ_LD_CC) continue;
        if (l->param == SQ_CC_BEND && !(done_b & (1u << ch))) { done_b |= (uint16_t)(1u << ch); midi_send(0xE0u | ch, 0u, 64u); }
        if (l->param == SQ_CC_AT && !(done_a & (1u << ch))) { done_a |= (uint16_t)(1u << ch); midi_send(0xD0u | ch, 0u, 0u); }
    }
}
/* what a lane sends for a value: lane 1 moves with the FILTER macro (FX + K4, the MASTER knob, the remote) */
static uint8_t lane_val(uint32_t l, uint8_t v)
{
    if (l || (!mac_filt && !vg_filt_adj()) || v > 127u) return v;
    return (uint8_t)clamp_i32((int32_t)v + mac_filt + vg_filt_adj(), 0, 127);
}

static void project_sanitize(void)
{
    sq_project_sanitize(&project);
}

/* 0.9: before the project is written (a slot, an export): what plays goes with it. 0.8 forgot the pattern each track
 * was on (initial_pattern was only ever the default), the mutes and the scene: the FM-1 came back on other patterns. */
static void project_prepare_save(void)
{
    uint32_t t;
    uint16_t m = (uint16_t)(vg_mutes_to_keep() ^ pending_mute);   /* (not a BREAK's silence) */
    for (t = 0; t < SQ_TRACKS; t++) project.track[t].initial_pattern = tr[t].pattern;
    project.live.mute_lo = (uint8_t)(m & 0xFFu);
    project.live.mute_hi = (uint8_t)(m >> 8);
    project.live.scene_cursor = scene_cursor < SQ_SCENES ? scene_cursor : 0u;
}

/* boot: every track starts on its saved pattern. A later PLAY keeps the patterns you have chosen. */
static void project_runtime_reset(uint8_t boot)
{
    uint32_t t, n;
    for (t = 0; t < SQ_TRACKS; t++) {
        const sq_track_cfg_t *c = &project.track[t];
        tr[t].step = c->direction == SQ_DIR_REV ? (uint8_t)(c->length - 1u) : c->start;
        if (boot) tr[t].pattern = c->initial_pattern < SQ_PATTERNS ? c->initial_pattern : 0u;
        tr[t].pending_pattern = SQ_NO_PENDING;
        tr[t].ping_dir = 1;
        tr[t].div_accum = (uint16_t)(sq_div_tuplet(c->division) ? 0u : sq_div_ticks(c->division) - 1u);   /* the first tick after the start plays step 1 */
        tr[t].advances = 0u;
        tr[t].prev_hit = 0u;
        tr[t].loop_count = 0u;
        tr[t].anchor = 0u;
        tr[t].ppos[0] = tr[t].ppos[1] = tr[t].ppos[2] = 0u;
        ev[t].step = 0;
        ev[t].ratchet_left = 0u;
        ev[t].ratchet_total = 1u;
        ev[t].first_ratchet = 1u;
        ev[t].expo = 0u;
        expo_hold[t] = 0u;
        expo_plain[t] = 0u;
        ev[t].step_index = c->start;
        ev[t].arp_n = 0u;
        ev[t].arp_pos = 0u;
        ev[t].lane_locked = 0u;
        ev[t].slot_start_us = 0u;
        ev[t].slot_dur_us = 0u;
        pre[t].state = 0u;
        for (n = 0; n < SQ_POLY_OUT; n++) { ev[t].active_note[n] = SQ_NOTE_NONE; ev[t].active_ch[n] = 0u; ev[t].off_us[n] = 0u; }
        for (n = 0; n < SQ_HOLD_MAX; n++) { hold_note[t][n] = SQ_NOTE_NONE; hold_ch[t][n] = 0u; hold_off_us[t][n] = 0u; }
    }
    global_clock = 0u;
    clk_next = 0u;                                     /* 0.26: no click asked yet */
    tup_wait = 0u;
    bar_origin = 0u; bar_base = 0u;                    /* 0.25: the bars are counted from here */
    if (boot) { bar_pend_steps = 0u; bar_pend_beats = 0u; }
    loop_on = 0u; loop_latched = 0u; lp_held = 0u;
    realign_pend = 0u; fx_pos_prev = 0u;
    for (t = 0; t < SQ_TRACKS; t++) { tie_pend[t] = 0u; ev[t].arp_going = 0u; ev[t].arp_until_us = 0u; }
    if (boot) for (t = 0; t < SQ_TRACKS; t++) gh_st[t].pat = 255u;   /* 0.24: another project: nothing is known of its copies */
    if (boot) lens_pend = 0;                                         /* (0.25: nor does a LONGER asked of the other one wait) */
    pending_scene = SQ_NO_PENDING;
    retrig_mask = 0u; restart_pend = 0u; stop_at_bar = 0u;
    if (boot) vg_reset();                        /* 0.9: a project loaded: nothing queued, the trail starts again */
}

static void midi_note_off_track(uint32_t t, uint32_t slot)
{
    uint8_t note = ev[t].active_note[slot];
    if (note != SQ_NOTE_NONE) {
        midi_send(0x80u | ev[t].active_ch[slot], note, 0u);
        ev[t].active_note[slot] = SQ_NOTE_NONE;
        ev[t].off_us[slot] = 0u;
    }
}

static void held_note_off(uint32_t t, uint32_t slot)
{
    if (hold_note[t][slot] != SQ_NOTE_NONE) {
        midi_send(0x80u | hold_ch[t][slot], hold_note[t][slot], 0u);
        hold_note[t][slot] = SQ_NOTE_NONE;
        hold_off_us[t][slot] = 0u;
    }
}

static void held_all_off(uint32_t t)
{
    uint32_t n;
    for (n = 0; n < SQ_HOLD_MAX; n++) held_note_off(t, n);
}

static void held_note_on(uint32_t t, uint8_t ch, uint8_t note, uint8_t vel, uint32_t off_us)
{
    uint32_t n, slot = SQ_HOLD_MAX, earliest = 0u;
    uint32_t earliest_due = 0xFFFFFFFFu;
    /* retriggering the same pitch is explicit: end the old voice first */
    for (n = 0; n < SQ_HOLD_MAX; n++) {
        if (hold_note[t][n] == note && hold_ch[t][n] == ch) { held_note_off(t, n); slot = n; break; }
        if (hold_note[t][n] == SQ_NOTE_NONE && slot == SQ_HOLD_MAX) slot = n;
        if (hold_note[t][n] != SQ_NOTE_NONE && hold_off_us[t][n] < earliest_due) { earliest_due = hold_off_us[t][n]; earliest = n; }
    }
    if (slot == SQ_HOLD_MAX) { slot = earliest; held_note_off(t, slot); }
    midi_send(0x90u | ch, note, vel);
    hold_note[t][slot] = note;
    hold_ch[t][slot] = ch;
    hold_off_us[t][slot] = off_us;
}

/* 0.22: a step's note that starts while the same pitch is still held on the channel (a TIE's 15 ms into the next step,
 * a note the GATE effect made longer than its step) and would outlast it: that voice ends now. Its own end, coming
 * while the new note sounds, cut the new note short: a TIE into the same note left 15 ms of it. A held voice that
 * outlasts the new note is left as it was (a long note with the same note inside) */
static void held_same_off(uint32_t t, uint8_t ch, uint8_t note, uint32_t end_us)
{
    uint32_t n;
    for (n = 0; n < SQ_HOLD_MAX; n++)
        if (hold_note[t][n] == note && hold_ch[t][n] == ch && (int32_t)(hold_off_us[t][n] - end_us) < 0) held_note_off(t, n);
}

static void track_all_off(uint32_t t)
{
    uint32_t n;
    if (t >= SQ_TRACKS) return;                        /* (0.28: the remote's track 13-16) */
    for (n = 0; n < SQ_POLY_OUT; n++) midi_note_off_track(t, n);
    tape_track_off(t);
    ev[t].ratchet_left = 0u;
    expo_hold[t] = 0u;
    ev[t].strum_mask = 0u;                   /* the notes of a strum that have not started yet: they never will */
    ev[t].strum_held = 0u;
}

static void track_hard_off(uint32_t t)
{
    track_all_off(t);
    held_all_off(t);
}

static void preview_stop(void)
{
    if (prev_note != SQ_NOTE_NONE) {
        midi_send(0x80u | prev_ch, prev_note, 0u);
        prev_note = SQ_NOTE_NONE;
    }
}
static void preview_note(uint32_t t, uint8_t note)          /* a short blip so you hear what you entered */
{
    preview_stop();
    prev_ch = track_ch(t);
    prev_note = key_note(t, note);
    midi_send(0x90u | prev_ch, prev_note, 100u);
    prev_off_ms = fm1_ms + 180u;
}

static void thru_expr_off(void);                 /* sagga_expr.c: 0.26 */
static void thru_all_off(void)
{
    uint32_t k;
    thru_expr_off();                         /* 0.26: the keyboard's pedal let go, its wheel centred, on the channels they were left on */
    for (k = 0; k < 27u; k++)
        if (live_held & (1u << k)) midi_send(0x80u | live_ch[k], live_note[k], 0u);
    live_held = 0u;
    for (k = 0; k < 128u; k++)
        if (ext_ch[k] != 255u) { midi_send(0x80u | ext_ch[k], ext_out[k], 0u); ext_ch[k] = 255u; }
}

static void defer_panic(void);
static void defer_cancel_track(uint32_t t);
/* 0.10: the channels' All Notes Off, All Sound Off and sustain up go out as the USB has room (a burst of them after
 * every note's own note-off was what got dropped on a loaded link), a few channels a pass */
static void panic_service(void)
{
    while (panic_cc) {
        uint32_t ch = 0u;
        while (!(panic_cc & (1u << ch))) ch++;
        if (midi_tx_room() <= 6u) return;
        midi_send(0xB0u | ch, 64u, 0u);
        midi_send(0xB0u | ch, 123u, 0u);
        if (panic_snd & (1u << ch)) midi_send(0xB0u | ch, 120u, 0u);
        panic_cc &= (uint16_t)~(1u << ch);
        panic_snd &= (uint16_t)~(1u << ch);
    }
}
static void link_16th(void);               /* sagga_link.c: 0.15 */
static void link_tick(void);
static void porta_all_off(void);           /* sagga_live3.c: 0.13 */
static void aud_stop(void);                /* sagga_link.c: 0.15 */
static void panic_all_x(uint8_t sound)      /* sound: All Sound Off too (the PANIC gesture, a reload) */
{
    uint32_t t;
    preview_stop();
    thru_all_off();
    defer_panic();                           /* 0.8: the echoes and harmonies that wait go too (0.7 forgot them) */
    for (t = 0; t < SQ_TRACKS; t++) { track_hard_off(t); pre[t].state = 0u; tie_pend[t] = 0u; }
    tape_all_off();
    panic_cc = (uint16_t)((1u << ch_limit()) - 1u);   /* (one USB port: 15 and 16 are the grid link) */
    if (sound) panic_snd = panic_cc;
    panic_service();
    bend_reset();
    porta_all_off();                         /* 0.13 SLIDE: the portamento we switched on */
    click_quiet();                           /* 0.26: a click that waited, a MIDI click's note */
    aud_stop();                              /* 0.15: what the Pi's editor plays */
}
static void panic_all(void) { panic_all_x(0u); }

static uint8_t track_audible(uint32_t t)
{
    if (fx_now() & (1u << FX_KILL)) return 0u;
    if ((grid_kill | remote_kill) & (1u << t)) return 0u;
    if (solo_mask) return (solo_mask & (1u << t)) ? 1u : 0u;
    return (mute_mask & (1u << t)) == 0u;
}

/* 0.8: a track that goes silent (MUTE, SOLO of another, KILL, a scene, a snapshot) stops every note it has at once:
 * the ones of the step, the long ones, a strum that has not finished, its echoes. 0.7 let a 16-step note ring on. */
static void audible_service(void)
{
    uint32_t t;
    uint16_t now = 0u, gone;
    for (t = 0; t < SQ_TRACKS; t++) if (track_audible(t)) now |= (uint16_t)(1u << t);
    gone = (uint16_t)(audible_prev & ~now);
    audible_prev = now;
    if (!gone) return;
    for (t = 0; t < SQ_TRACKS; t++)
        if (gone & (1u << t)) { track_hard_off(t); defer_cancel_track(t); pre[t].state = 0u; }
}

static uint32_t master_clock_interval(void)
{
    uint32_t bpm = project.bpm < 30u ? 30u : project.bpm > 300u ? 300u : project.bpm;
    return 60000000u / (bpm * 24u);
}

static uint32_t current_clock_interval(void)
{
    return project.clock_mode == SQ_CLOCK_SLAVE ? ext_clock_us : master_clock_interval();
}

/* the ticks a step of this track lasts: the division, halved or doubled by the FX */
static int8_t vg_speed;                       /* 0.9 VIAGGIO HALF (-1) / DOUBLE (+1) for a phrase (sagga_viaggio.c) */
static uint8_t eff_div_ticks(uint32_t t)
{
    uint32_t d = sq_div_ticks(project.track[t].division);
    uint16_t fx = fx_now();
    if ((fx & (1u << FX_HALF)) || vg_speed < 0) d *= 2u;
    if ((fx & (1u << FX_DOUBLE)) || vg_speed > 0) d = d > 1u ? d / 2u : 1u;
    return (uint8_t)(d > 255u ? 255u : d);
}
/* 0.25 THE POLYRHYTHMS: a track whose step is not a number of ticks (five or seven in the time of four: 96/5 ...). Its
 * step is num / den ticks (the FX and VIAGGIO's HALF / DOUBLE on the num, as on a plain division's ticks). While it
 * plays, tr[].div_accum is how far its next step is, in 1 / den of a tick: under den, the step begins before the next
 * tick - seq_clock_tick says when (tup_at), the main loop plays it then (tup_service), at its own time between two
 * ticks. */
static uint8_t track_tuplet(uint32_t t) { return sq_div_tuplet(project.track[t].division); }
static void div_frac_x(uint32_t t, uint8_t with_fx, uint16_t *num, uint8_t *den)
{
    uint32_t n;
    uint16_t fx = with_fx ? fx_now() : 0u;
    sq_div_frac(project.track[t].division, num, den);
    n = *num;
    if ((fx & (1u << FX_HALF)) || vg_speed < 0) n *= 2u;
    if ((fx & (1u << FX_DOUBLE)) || vg_speed > 0) n = n > 1u ? n / 2u : 1u;
    if (n < (uint32_t)*den) n = *den;                          /* (a step is a tick at least: never two of them begin in one) */
    *num = (uint16_t)(n > 2000u ? 2000u : n);
}
static uint32_t slot_us(uint32_t t)                 /* how long a step of the track lasts now, microseconds */
{
    uint16_t num; uint8_t den;
    if (!track_tuplet(t)) return current_clock_interval() * eff_div_ticks(t);
    div_frac_x(t, 1u, &num, &den);
    return current_clock_interval() * num / den;
}

static uint32_t hash3(uint32_t a, uint32_t b, uint32_t c) { return sq_hash3(a, b, c); }

/* where the step starts, relative to its slot (microseconds, negative = early): swing, nudge, the timing LFOs and the
 * track's humanise. The same step in the same loop always gets the same answer. */
static int32_t step_offset_us(uint32_t t, const sq_step_t *s, uint8_t idx, uint32_t dur)
{
    const sq_track_cfg_t *c = &project.track[t];
    int32_t nudge = (int32_t)s->nudge + lfo_mod[t][SQ_LD_TIMING - 1u];
    int32_t swing = (int32_t)c->swing + lfo_mod[t][SQ_LD_SWING - 1u] + mac_swing;
    int32_t d;
    if (c->hum_time) nudge += (int32_t)(hash3(t, idx, tr[t].loop_count) % (2u * c->hum_time + 1u)) - (int32_t)c->hum_time;
    nudge += sq_groove_time(project.ext.track[t].groove, project.ext.track[t].groove_amt, idx);   /* 0.15 GROOVE */
    d = sq_step_offset(dur, idx, (uint8_t)clamp_i32(swing, SQ_SWING_MIN, SQ_SWING_MAX),
                       (int8_t)clamp_i32(nudge, -(int32_t)SQ_NUDGE_MAX, (int32_t)SQ_NUDGE_MAX));
    if (c->delay_ms || project.live.cc_lead_ms) {           /* 0.10 DELAY: the synth's latency, ms either way; CC LEAD: the
                                                             * locks go out at the slot, the notes this much later */
        d += (int32_t)c->delay_ms * 1000 + (int32_t)project.live.cc_lead_ms * 1000;
        if (d < -((int32_t)dur / 2)) d = -((int32_t)dur / 2);
        if (dur && d >= (int32_t)dur) d = (int32_t)dur - 1;
    }
    return d;
}

/* 0.8: the step as the live layer plays it. EUCLID and the algorithms decide whether it is a hit; a hit on a step that
 * was never written plays the track's own note (0.7 played the empty step's C4 on a drum track); a DENSITY ghost is
 * soft. Returns the step to play (s, or buf with the changes), and *hit. */
static const sq_step_t *live_step(uint32_t t, const sq_step_t *s, sq_step_t *buf, uint8_t *hit)
{
    uint8_t ghost = 0u;
    *hit = live_hit(t, tr[t].step, (s->flags & SQ_STEP_ON) ? 1u : 0u, &ghost);
    live_ghost[t] = ghost;
    if (!*hit) return s;
    if ((s->flags & SQ_STEP_SET) && !ghost) return s;
    *buf = *s;
    if (!(s->flags & SQ_STEP_SET)) {
        uint32_t n;
        for (n = 0; n < SQ_POLY; n++) buf->note[n] = SQ_NOTE_NONE;
        buf->note[0] = PEN(t);
    }
    if (ghost) {
        if (project.track[t].flags & SQ_TF_DRUM) {   /* 0.9.1: a ghost on a drum track is that drum, never the step's C4 */
            uint32_t n;
            for (n = 1; n < SQ_POLY; n++) buf->note[n] = SQ_NOTE_NONE;
            buf->note[0] = PEN(t);
        }
        buf->velocity = (uint8_t)clamp_i32((int32_t)s->velocity * project.track[t].algo_b / 100, 1, 127);
        buf->length = 40u; buf->chance = 100u; buf->condition = SQ_COND_ALWAYS; buf->ratchet = 1u;
    }
    buf->flags |= SQ_STEP_ON | SQ_STEP_SET;
    return buf;
}

static uint8_t step_should_play(uint32_t t, const sq_step_t *s, uint8_t hit)
{
    sq_step_t tmp = *s;
    if (hit) tmp.flags |= SQ_STEP_ON; else tmp.flags &= (uint8_t)~SQ_STEP_ON;
    tmp.chance = (uint8_t)clamp_i32((int32_t)s->chance + lfo_mod[t][SQ_LD_CHANCE - 1u], 0, 100);
    return sq_step_should_play(&tmp, tr[t].loop_count, fill_active(), tr[t].prev_hit, &sq_rng_state);
}

/* ---- the ornaments: the notes the MIDI effects add (HARM, ECHO, the global ECHO), each tagged with its track */
static uint8_t defer_glob;                             /* the ornaments scheduled now belong to the global ECHO */
static void defer_schedule(uint8_t t, uint8_t ch, uint8_t note, uint8_t vel, uint32_t on_us, uint32_t gate)
{
    uint32_t i, pick = SQ_DEFER_MAX;
    uint8_t low = vel;
    for (i = 0; i < SQ_DEFER_MAX; i++) {
        if (!defer_note[i].state) { pick = i; break; }
        if (defer_note[i].state == 1u && defer_note[i].vel < low) { low = defer_note[i].vel; pick = i; }   /* (waiting, fainter) */
    }
    if (pick >= SQ_DEFER_MAX) return;                  /* (full of louder ones: this ornament is not played) */
    defer_note[pick].track = t; defer_note[pick].ch = ch; defer_note[pick].note = note; defer_note[pick].vel = vel;
    defer_note[pick].on_us = on_us; defer_note[pick].off_us = on_us + (gate ? gate : 1u); defer_note[pick].state = 1u;
    defer_note[pick].glob = defer_glob;
}
static void defer_service(uint32_t now)
{
    uint32_t i;
    for (i = 0; i < SQ_DEFER_MAX; i++) {
        defer_note_t *d = &defer_note[i];
        if (d->state == 1u && time_due(now, d->on_us)) { midi_send(0x90u | d->ch, d->note, d->vel); d->state = 2u; }
        if (d->state == 2u && time_due(now, d->off_us)) { midi_send(0x80u | d->ch, d->note, 0u); d->state = 0u; }
    }
}
static void defer_cancel_track(uint32_t t)            /* a track that goes silent: its ornaments with it */
{
    uint32_t i;
    for (i = 0; i < SQ_DEFER_MAX; i++) {
        if (!defer_note[i].state || defer_note[i].track != t) continue;
        if (defer_note[i].state == 2u) midi_send(0x80u | defer_note[i].ch, defer_note[i].note, 0u);
        defer_note[i].state = 0u;
    }
}
static void defer_panic(void)
{
    uint32_t i;
    for (i = 0; i < SQ_DEFER_MAX; i++) {
        if (defer_note[i].state == 2u) midi_send(0x80u | defer_note[i].ch, defer_note[i].note, 0u);
        defer_note[i].state = 0u;
    }
}

/* ---- 0.20: the MIDI FX chain as a pipeline. A note of a slice goes in as one event; each effect that plays, in the
 * track's ORDER (project.ext.mfxd[t].order), changes the events, drops some or adds some (HARM a voice to each one,
 * ECHO the repeats of each, GLITCH a stutter): what comes out is the note itself (event 0, if it is still there) and
 * the ornaments, scheduled. 0.19's VEL CURVE, OCTAVE, HARM, ECHO play as they did (the default order keeps theirs). */
#define MFX_EV_MAX 32u
typedef struct { uint8_t note, vel, drop, glob; uint32_t at, gate; } mfx_ev_t;
static mfx_ev_t mfx_ev[MFX_EV_MAX];
static uint32_t mfx_nev;
static uint8_t mfx_every[SQ_TRACKS];              /* NOTE FILTER: the notes counted, for one of every N */
static int16_t mod_fx[SQ_TRACKS];                 /* 0.20 MOD MATRIX: the FX depth of each track, -100..+100 % */

static int32_t mfx_scale(uint32_t t, int32_t v) { return v * (100 + mod_fx[t]) / 100; }   /* (the FX depth applied) */
static void mfx_add(uint8_t note, uint8_t vel, uint32_t at, uint32_t gate, uint8_t glob)
{
    mfx_ev_t *e;
    if (mfx_nev >= MFX_EV_MAX || !vel) return;
    e = &mfx_ev[mfx_nev++];
    e->note = note; e->vel = vel; e->drop = 0u; e->glob = glob; e->at = at; e->gate = gate ? gate : 1u;
}
/* OCTAVE: the steps it moves (ALT every other one, RANDOM half of them, every 3RD, every 4TH) */
static uint8_t mfx_oct_step(uint32_t t, uint8_t which)
{
    uint8_t i = ev[t].step_index;
    switch (which) {
    case SQ_OCT_RANDOM: return (uint8_t)(hash3(t, i, tr[t].loop_count) & 1u);
    case SQ_OCT_THIRD:  return (uint8_t)((i % 3u) == 2u);
    case SQ_OCT_FOURTH: return (uint8_t)((i & 3u) == 3u);
    default:            return (uint8_t)(i & 1u);
    }
}
static uint8_t mfx_degree(uint32_t t, uint8_t note, int32_t steps)   /* steps of the key (FREE: semitones) */
{
    return track_in_key(t) ? sq_scale_degree(note, project.key_root, project.key_scale, steps) : clamp_note((int32_t)note + steps);
}
static void mfx_echo(uint32_t i, uint32_t repeats, uint8_t time_idx, uint32_t keep_pct, uint8_t glob)
{
    uint32_t k, delay = current_clock_interval() * sq_echo_ticks(time_idx), v = mfx_ev[i].vel, g, gate = mfx_ev[i].gate;
    if (!delay) delay = 1u;
    g = gate < delay ? gate : delay - delay / 8u;      /* (an echo ends before the next one of the same note starts) */
    for (k = 1u; k <= repeats; k++) {
        v = v * keep_pct / 100u;
        if (v < 1u) break;
        mfx_add(mfx_ev[i].note, (uint8_t)v, mfx_ev[i].at + delay * k, g ? g : 1u, glob);
    }
}

/* the chain on one note of track t: 1 when the note itself plays, with *note *vel *gate as the chain left them; the
 * notes it brings go to the ornaments */
static uint8_t mfx_run(uint32_t t, uint8_t ch, uint8_t slice_no, uint8_t *note, uint8_t *vel, uint32_t *gate, uint32_t now)
{
    const sq_mfxd_t *d = &project.ext.mfxd[t];
    uint32_t k, i, n0, h = hash3(t, ev[t].step_index, tr[t].loop_count) ^ ((uint32_t)slice_no * 0x9E3779B1u);
    uint8_t echoed = 0u;
    mfx_nev = 0u;
    mfx_add(*note, *vel ? *vel : 1u, 0u, *gate, 0u);
    for (k = 0; k < SQ_MFX_ALLN; k++) {
        uint8_t fx = d->order[k], tm, fb;
        int8_t a;
        if (!sq_mfx_is_on(&project.ext, t, fx)) continue;
        sq_mfx_get(&project.ext, t, fx, &a, &tm, &fb);
        n0 = mfx_nev;
        switch (fx) {
        case SQ_MFX_FILTER: {                          /* the notes between two; one of every N */
            uint8_t keep = (uint8_t)(fb <= 1u || (mfx_every[t] % fb) == 0u);
            for (i = 0; i < n0; i++) if (!keep || mfx_ev[i].note < (uint8_t)a || mfx_ev[i].note > tm) mfx_ev[i].drop = 1u;
            break;
        }
        case SQ_MFX_CHANCE: {                          /* NOTE: each one its own throw; STEP: one for the whole slice */
            int32_t pass = 100 - clamp_i32(mfx_scale(t, 100 - a), 0, 100);
            if (tm) { if ((int32_t)((h >> 4) % 100u) >= pass) for (i = 0; i < n0; i++) mfx_ev[i].drop = 1u; }
            else for (i = 0; i < n0; i++) if ((int32_t)(sq_rng_next(&sq_rng_state) % 100u) >= pass) mfx_ev[i].drop = 1u;
            break;
        }
        case SQ_MFX_VELOCITY: {
            int32_t c = clamp_i32(mfx_scale(t, a), -8, 8);
            for (i = 0; i < n0; i++) mfx_ev[i].vel = sq_mfx_velocity(mfx_ev[i].vel, (int8_t)c);
            break;
        }
        case SQ_MFX_RANDOM: {                          /* K2 the notes' spread, K3 the velocity's, K4 how often */
            int32_t often = clamp_i32(mfx_scale(t, fb), 0, 100);
            for (i = 0; i < n0; i++) {
                if ((int32_t)(sq_rng_next(&sq_rng_state) % 100u) >= often) continue;
                if (a > 0) mfx_ev[i].note = mfx_degree(t, mfx_ev[i].note, (int32_t)(sq_rng_next(&sq_rng_state) % (2u * (uint32_t)a + 1u)) - a);
                if (tm) mfx_ev[i].vel = (uint8_t)clamp_i32((int32_t)mfx_ev[i].vel + (int32_t)(sq_rng_next(&sq_rng_state) % (2u * tm + 1u)) - (int32_t)tm, 1, 127);
            }
            break;
        }
        case SQ_MFX_OCTAVE:
            if (a && mfx_oct_step(t, tm)) for (i = 0; i < n0; i++) mfx_ev[i].note = clamp_note((int32_t)mfx_ev[i].note + 12 * a);
            break;
        case SQ_MFX_HARM:                              /* a second voice on each note so far: steps of the key (FREE: semitones) */
            if (a) for (i = 0; i < n0; i++) {
                uint8_t n = mfx_degree(t, mfx_ev[i].note, clamp_i32(a, track_in_key(t) ? -7 : -12, track_in_key(t) ? 7 : 12));
                uint32_t v = (uint32_t)mfx_ev[i].vel * (uint32_t)clamp_i32(mfx_scale(t, fb), 1, 100) / 100u;
                if (mfx_ev[i].drop || n == mfx_ev[i].note) continue;
                mfx_add(n, (uint8_t)(v ? v : 1u), mfx_ev[i].at, mfx_ev[i].gate, 0u);
            }
            break;
        case SQ_MFX_GATE: {                            /* times a factor, or a fixed length; K4 a little at random */
            uint32_t fixed = sq_gate_fixed_ticks(tm) * current_clock_interval();
            for (i = 0; i < n0; i++) {
                uint32_t g = fixed ? fixed : mfx_ev[i].gate * sq_gate_factor_x4(a) / 4u;   /* (32 bits: no 64-bit division on the FM-1) */
                if (fb) {                              /* (no signed 64-bit numbers: the JieLi library has no __divdi3) */
                    int32_t r = (int32_t)(sq_rng_next(&sq_rng_state) % (2u * fb + 1u)) - (int32_t)fb;
                    uint32_t g0 = g;
                    g = (uint32_t)clamp_i32((int32_t)g + (int32_t)(g / 100u) * r, 1, 0x7FFFFFFF);
                    /* 0.22: HUMAN alone does not carry the step's note into the next one (it never did: the next step
                     * ended it); a FIXED length or a factor that is longer than the step does (fire_slice) */
                    if (i == 0u && g0 <= ev[t].slice_us && g > ev[t].slice_us) g = ev[t].slice_us;
                }
                mfx_ev[i].gate = g ? g : 1u;
            }
            break;
        }
        case SQ_MFX_GLITCH: {                          /* now and then: STUTTER, RISE, JUMP, CUT (MIX: any of them) */
            int32_t often = clamp_i32(mfx_scale(t, a), 0, 100);
            uint8_t kind = tm;
            if ((int32_t)((h >> 9) % 100u) >= often) break;
            if (kind == SQ_GL_MIX) kind = (uint8_t)(SQ_GL_STUTTER + (h >> 17) % (SQ_GLITCHES - 1u));
            if (kind == SQ_GL_STUTTER || kind == SQ_GL_RISE) {   /* the slice in K4 pieces (2..8), each a repeat */
                uint32_t pcs = fb < 2u ? 2u : fb, per = ev[t].slice_us / pcs, r;
                if (!per) per = 1u;
                for (i = 0; i < n0; i++) {
                    if (mfx_ev[i].drop) continue;
                    if (mfx_ev[i].gate > per * 3u / 5u) mfx_ev[i].gate = per * 3u / 5u + 1u;
                    for (r = 1u; r < pcs; r++)
                        mfx_add(kind == SQ_GL_RISE ? mfx_degree(t, mfx_ev[i].note, (int32_t)r) : mfx_ev[i].note, mfx_ev[i].vel,
                                mfx_ev[i].at + per * r, mfx_ev[i].gate, 0u);
                }
            } else if (kind == SQ_GL_JUMP) {          /* an octave (K4 over 4: two) up or down */
                int32_t o = ((h >> 21) & 1u) ? 12 : -12;
                if (fb > 4u) o *= 2;
                for (i = 0; i < n0; i++) mfx_ev[i].note = clamp_note((int32_t)mfx_ev[i].note + o);
            } else {                                   /* CUT: a click of a note */
                uint32_t g = ev[t].slice_us / (4u * (fb ? fb : 1u)) + 1u;
                for (i = 0; i < n0; i++) if (mfx_ev[i].gate > g) mfx_ev[i].gate = g;
            }
            break;
        }
        case SQ_MFX_ECHO:
            echoed = 1u;
            if (a > 0) {
                uint32_t keep = (uint32_t)clamp_i32(mfx_scale(t, fb), 10, 100);
                for (i = 0; i < n0; i++) if (!mfx_ev[i].drop) mfx_echo(i, (uint32_t)a, tm, keep, 0u);
            }
            break;
        default: break;
        }
    }
    if (!echoed && echo_global) {                      /* FX + OCT+: the global ECHO, when the chain has none of its own */
        n0 = mfx_nev;
        for (i = 0; i < n0; i++) if (!mfx_ev[i].drop) mfx_echo(i, 2u, 6u, 55u, 1u);
    }
    mfx_every[t]++;
    for (i = 1u; i < mfx_nev; i++) {                   /* the ornaments */
        if (mfx_ev[i].drop) continue;
        defer_glob = mfx_ev[i].glob;
        defer_schedule((uint8_t)t, ch, mfx_ev[i].note, mfx_ev[i].vel, now + mfx_ev[i].at, mfx_ev[i].gate);
    }
    defer_glob = 0u;
    if (mfx_ev[0].drop) return 0u;
    *note = mfx_ev[0].note; *vel = mfx_ev[0].vel; *gate = mfx_ev[0].gate;
    return 1u;
}

/* 0.8: the notes of a step as they go out: the key (shift and scale), the HARMONY (a FOLLOW track moves to the chord
 * playing), TURING moving the notes, then the voicing (not for an arpeggio PLAYED: the order is the player's).
 * 0.25 FOLLOW MELODY: a single note is a note of a tune: it is not moved with the chord; `strong` (it is on a beat of
 * the metre, or longer than its step, or held while the chord changes) it goes to the nearest tone of the chord playing,
 * else it plays as written. A step of two notes or more follows as ever.
 * 0.26 FOLLOW SMOOTH: the chord is the one FOLLOW makes of it, its notes in the octaves nearest to the written ones
 * (sq_harm_smooth): the notes two chords share stay, the others move a step or two. */
static uint8_t step_notes_x(uint32_t t, const sq_step_t *s, uint8_t *out, uint8_t strong)
{
    const sq_track_cfg_t *c = &project.track[t];
    uint8_t n = 0u, k, raw[SQ_POLY_OUT], root = key_root_of(t), scale = key_scale_of(t);
    sq_hchord_t hc;
    for (k = 0; k < SQ_POLY; k++)
        if (s->note[k] != SQ_NOTE_NONE) raw[n++] = key_note(t, (int32_t)s->note[k]);
    if (!n) return 0u;
    if (n == 1u && c->chord != SQ_CH_OFF && !(c->flags & SQ_TF_DRUM))   /* 0.10 CHORD: one note becomes the shape (up to 6) */
        n = sq_chord_build(raw[0], c->chord, track_in_key(t) ? c->chord_key : (uint8_t)SQ_CK_FREE, root, scale, raw);
    if ((c->flags & SQ_TF_FOLLOW) && !(c->flags & SQ_TF_DRUM) && harm_chord(&hc, 0)) {   /* 0.11: a root and a shape too */
        if (n == 1u && c->follow_mode == SQ_FM_MELODY) { if (strong) raw[0] = sq_harm_melody(raw[0], root, scale, &hc); }
        else if (c->follow_mode == SQ_FM_SMOOTH) n = sq_harm_smooth(raw, n, root, scale, &hc);   /* 0.26: the nearest notes of the chord */
        else n = sq_harm_apply_chord(raw, n, root, scale, &hc, n >= 2u);
    }
    {
        int32_t td = live_note_deg(t);                 /* TURING on the notes: steps of the key (FREE: semitones) */
        if (td) for (k = 0; k < n; k++)
            raw[k] = track_in_key(t) || (c->flags & SQ_TF_FOLLOW) ? sq_scale_degree(raw[k], root, scale, td)
                                                                  : clamp_note((int32_t)raw[k] + td);
    }
    if (SQ_CHORD_MODE(c->chord_mode) == SQ_CHORD_ARP_PLAYED) {
        uint8_t m = 0u, j, dup;
        for (k = 0; k < n; k++) { dup = 0u; for (j = 0; j < m; j++) if (out[j] == raw[k]) dup = 1u; if (!dup) out[m++] = raw[k]; }
        return m;
    }
    return sq_voice_notes(raw, n, c->voicing, out);
}
static uint8_t step_notes(uint32_t t, const sq_step_t *s, uint8_t *out) { return step_notes_x(t, s, out, 1u); }   /* (a held note, a chord) */
/* 0.25 FOLLOW MELODY: step `idx` of track t is a strong note of its tune: on a beat of the metre (the track's steps
 * counted from where its loop begins, as its row shows them), or longer than its step; 0.26: or a note of the chord
 * that a tune of the engines plays right after the chord (tune_answers, sagga_gen.c) */
static uint8_t tune_answers(uint32_t t, const sq_step_t *s, uint8_t idx);
static uint8_t step_strong(uint32_t t, const sq_step_t *s, uint8_t idx)
{
    uint8_t st = project.track[t].start;
    uint32_t k = idx >= st ? (uint32_t)idx - st : idx;
    return (uint8_t)(s->length > 100u || ((bar_bt() >> (k % bar_st())) & 1u) != 0u || tune_answers(t, s, idx));
}

/* start playing a step: slices (the ratchets, or the notes of the arpeggio) from first_us, span_us apart in all */
static void event_begin(uint32_t t, const sq_step_t *s, uint8_t idx, uint32_t first_us, uint32_t span_us)
{
    const sq_track_cfg_t *cfg = &project.track[t];
    uint16_t fx = fx_now();
    uint8_t slices = s->ratchet < 1u ? 1u : s->ratchet > SQ_RATCHET_MAX ? (uint8_t)SQ_RATCHET_MAX : s->ratchet;
    uint8_t stut = (fx & (1u << FX_ST8)) ? 8u : (fx & (1u << FX_ST4)) ? 4u : (fx & (1u << FX_ST2)) ? 2u : 1u;
    uint8_t notes[SQ_POLY_OUT], n, i;
    ev[t].step_index = idx;                            /* (the notes below may depend on it: TURING) */
    ev[t].arp_going = 0u;
    n = step_notes_x(t, s, notes, step_strong(t, s, idx));
    ev[t].buf = *s;
    for (i = 0; i < SQ_POLY; i++) ev[t].buf.note[i] = i < n ? notes[i] : SQ_NOTE_NONE;
    for (i = 0; i < SQ_POLY_OUT; i++) ev[t].vnote[i] = i < n ? notes[i] : SQ_NOTE_NONE;   /* (the voices that play: up to six) */
    ev[t].vn = n;
    s = &ev[t].buf;
    ev[t].arp_n = 0u;
    if (SQ_CHORD_MODE(cfg->chord_mode) != SQ_CHORD_BLOCK) {
        ev[t].arp_n = sq_arp_build_notes(ev[t].vnote, ev[t].vn, cfg->chord_mode, ev[t].arp);
        if (cfg->arp_rate) {                           /* 0.10: so many notes a step; the arpeggio runs on through the empty steps */
            if (s->ratchet <= 1u) slices = SQ_ARP_PER_STEP(cfg->arp_rate);
            ev[t].arp_wait = (uint8_t)(SQ_ARP_EVERY(cfg->arp_rate) - 1u);   /* 0.18: a slow RATE counts from the chord's step */
            if (cfg->arp_flags & SQ_AF_RETRIG) ev[t].arp_pos = 0u;
            ev[t].arp_until_us = first_us + ((s->length > SQ_GATE_LONG_MIN) ? sq_gate_us(s->length, span_us, span_us) : span_us);
        } else if (ev[t].arp_n > 1u && s->ratchet <= 1u)   /* ROLL: an arpeggio with no ratchet spreads its notes over the step */
            slices = ev[t].arp_n > SQ_RATCHET_MAX ? (uint8_t)SQ_RATCHET_MAX : ev[t].arp_n;
    }
    if (stut > slices) slices = stut;
    ev[t].expo = 0u;
    if (project.track[t].expo.shape != SQ_XS_OFF && !(fx & (1u << FX_FREEZE)) && !(s->flags & SQ_STEP_XOFF) && !expo_plain[t]) {   /* 0.10 EXPO: the hits of the curve */
        sq_expo_t xe = project.track[t].expo;
        const sq_expo_t *x = &xe;
        xe.hits = vg_expo_hits(xe.hits);               /* (VIAGGIO's energy: fewer or more hits) */
        if (x->shape == SQ_XS_SETTLE) {                /* as many hits as the span takes: counted as they go */
            slices = 255u;
            ev[t].expo = 2u;
            ev[t].x_pos = 0u;
            ev[t].x_hits = xe.hits;
        } else {
            slices = x->hits;
            sq_expo_times(x, span_us, ev[t].expo_t, &sq_rng_state);
            ev[t].expo = 1u;
        }
        ev[t].first_us = first_us;
        ev[t].span_us = span_us;
        if (x->notes != SQ_XN_CHORD && !ev[t].arp_n) {   /* ARP: the notes low to high, then their octaves */
            uint8_t m = 0u, oct, k, j, notes2[SQ_POLY_OUT];
            for (k = 0; k < ev[t].vn && k < SQ_POLY_OUT; k++) if (ev[t].vnote[k] != SQ_NOTE_NONE) notes2[m++] = ev[t].vnote[k];
            for (k = 0; k + 1u < m; k++) for (j = (uint8_t)(k + 1u); j < m; j++)
                if (notes2[j] < notes2[k]) { uint8_t tmp = notes2[k]; notes2[k] = notes2[j]; notes2[j] = tmp; }
            for (oct = 0; oct <= (uint8_t)(x->notes - SQ_XN_ARP) && ev[t].arp_n < SQ_ARP_OUT; oct++)
                for (k = 0; k < m && ev[t].arp_n < SQ_ARP_OUT; k++) {
                    int32_t v = (int32_t)notes2[k] + 12 * oct;
                    if (v > 127) continue;
                    ev[t].arp[ev[t].arp_n++] = (uint8_t)v;
                }
            ev[t].arp_pos = 0u;
        }
    }
    ev[t].step = &ev[t].buf;
    ev[t].ratchet_left = slices;
    ev[t].ratchet_total = slices;
    ev[t].slice_us = span_us / slices;
    if (!ev[t].slice_us) ev[t].slice_us = 1u;
    if (ev[t].expo == 1u) ev[t].slice_us = (slices > 1u ? ev[t].expo_t[1] : span_us) - ev[t].expo_t[0];
    if (ev[t].expo == 2u) { sq_expo_t xe = project.track[t].expo; xe.hits = ev[t].x_hits; ev[t].slice_us = sq_expo_settle_gap(&xe, 0u, span_us, current_clock_interval() * 24u, &sq_rng_state); }
    if (!ev[t].slice_us) ev[t].slice_us = 1u;
    ev[t].ratchet_next_us = first_us;
    ev[t].first_ratchet = 1u;
}

/* the clock reached a track's step boundary */
/* the step a track plays now: the step itself, or (0.5) with the notes, velocity, gate of the parameters' own loops */
static const sq_step_t *play_step(uint32_t t, sq_step_t *buf)
{
    const sq_track_cfg_t *c = &project.track[t];
    const sq_step_t *row = project.step[t][tr[t].pattern];
    if (!c->plen[SQ_PL_NOTE] && !c->plen[SQ_PL_VEL] && !c->plen[SQ_PL_GATE]) return &row[tr[t].step];
    sq_plane_compose(c, &tr[t], row, tr[t].step, buf);
    return buf;
}

/* 0.10: the value a lane holds on a step that has no lock: with SLIDE, the glide between the lock before and the lock
 * after (both inside the loop, the loop wrapping); else none */
static int32_t lane_slide_at(uint32_t t, const sq_step_t *row, uint8_t idx, uint32_t n)
{
    const sq_track_cfg_t *c = &project.track[t];
    uint8_t len = c->length, lo = c->start < len ? c->start : 0u, span = (uint8_t)(len - lo);
    uint32_t db = 0u, df = 0u, k;
    int32_t a = -1, b = -1;
    if (!(c->lane_flags[n] & SQ_LF_SLIDE) || span < 2u || idx < lo || idx >= len) return -1;
    for (k = 1; k < span; k++) {                                 /* back */
        uint8_t i = (uint8_t)(lo + (idx - lo + span - k) % span);
        if (row[i].lane[n] != SQ_LANE_NONE) { a = row[i].lane[n]; db = k; break; }
    }
    for (k = 1; k < span; k++) {                                 /* forward */
        uint8_t i = (uint8_t)(lo + (idx - lo + k) % span);
        if (row[i].lane[n] != SQ_LANE_NONE) { b = row[i].lane[n]; df = k; break; }
    }
    if (a < 0 || b < 0) return -1;
    return a + ((b - a) * (int32_t)db) / (int32_t)(db + df);
}

/* the CC locks of a step go out: on its first slice, or (TRIGLESS lanes) when the step is silent too; `mask` = the
 * lanes to look at. A lock holds until a step without one, then the base comes back (SLIDE: the glide between locks). */
static void lanes_send(uint32_t t, const sq_step_t *s, uint8_t idx, uint8_t mask)
{
    const sq_track_cfg_t *cfg = &project.track[t];
    const sq_step_t *row = project.step[t][tr[t].pattern];
    uint32_t n;
    for (n = 0; n < SQ_LANES; n++) {
        uint8_t cc = cfg->lane_cc[n];
        int32_t sl;
        if (cc == SQ_LANE_NONE || !(mask & (1u << n))) continue;
        if (s->lane[n] != SQ_LANE_NONE) {
            lane_send(t, n, lane_val(n, s->lane[n]));
            ev[t].lane_locked |= (uint8_t)(1u << n);
        } else if ((sl = lane_slide_at(t, row, idx, n)) >= 0) {
            lane_send(t, n, lane_val(n, (uint8_t)sl));
            ev[t].lane_locked |= (uint8_t)(1u << n);
        } else if ((ev[t].lane_locked & (1u << n)) && cfg->lane_base[n] != SQ_LANE_NONE) {
            lane_send(t, n, lane_val(n, cfg->lane_base[n]));    /* the lock was for one step: put the value back */
            ev[t].lane_locked &= (uint8_t)~(1u << n);
        } else {
            ev[t].lane_locked &= (uint8_t)~(1u << n);
        }
    }
}
static uint8_t trigless_mask(uint32_t t)             /* the lanes that send on a silent step too: TRIGLESS, and a SLIDE (its glide) */
{
    uint8_t m = 0u, n;
    for (n = 0; n < SQ_LANES; n++) if (project.track[t].lane_flags[n] & (SQ_LF_TRIGLESS | SQ_LF_SLIDE)) m |= (uint8_t)(1u << n);
    return m;
}

/* 0.10: an arpeggio with a rate goes on through a step that does not play (while its chord holds, or always with HOLD) */
static uint8_t arp_continue(uint32_t t, uint32_t now, uint32_t dur)
{
    const sq_track_cfg_t *cfg = &project.track[t];
    if (!cfg->arp_rate || !ev[t].arp_n || SQ_CHORD_MODE(cfg->chord_mode) == SQ_CHORD_BLOCK) return 0u;
    if (!(cfg->arp_flags & SQ_AF_HOLD) && time_due(now, ev[t].arp_until_us)) return 0u;
    if (ev[t].arp_wait) { ev[t].arp_wait--; ev[t].ratchet_left = 0u; return 1u; }   /* 0.18: a slow RATE: no note on this step, the one sounding rings on */
    ev[t].arp_wait = (uint8_t)(SQ_ARP_EVERY(cfg->arp_rate) - 1u);
    ev[t].ratchet_left = ev[t].ratchet_total = SQ_ARP_PER_STEP(cfg->arp_rate);
    ev[t].slice_us = dur / SQ_ARP_PER_STEP(cfg->arp_rate);
    if (!ev[t].slice_us) ev[t].slice_us = 1u;
    ev[t].slot_start_us = now; ev[t].slot_dur_us = dur;
    ev[t].ratchet_next_us = now;
    ev[t].first_ratchet = 0u;                /* (no lanes again, no new chord: the notes are the ones held) */
    ev[t].expo = 0u;
    ev[t].arp_going = 1u;
    return 1u;
}

/* 0.25: an EXPO span in the metre -> its ticks, *into: the ticks since it began. A span of BARS is of the metre's bars,
 * from the bar line; a span of one or two BEATS is counted in quarters from the bar line, the last of a bar cut at the
 * line (4/4: as ever - global_clock % 24, 48, 96 ...) */
static uint16_t expo_span(uint8_t span, uint32_t *into)
{
    uint32_t x = sq_expo_span_ticks(span), bt = bar_ticks(), in = bar_into();
    *into = 0u;
    if (!x) return 0u;
    if (span >= SQ_XSPAN_BAR) { x = (x / 96u) * bt; *into = (global_clock - bar_origin) % x; return (uint16_t)x; }
    *into = in % x;
    if (in - *into + x > bt) x = bt - (in - *into);
    return (uint16_t)x;
}
static void arm_step(uint32_t t, uint32_t now)
{
    sq_step_t tmp, lbuf;
    const sq_step_t *s = play_step(t, &tmp);
    uint32_t dur = slot_us(t), xin = 0u;
    int32_t off;
    uint8_t hit, played = 0u, tl = trigless_mask(t);
    const sq_expo_t *x = &project.track[t].expo;
    uint16_t xspan = x->shape != SQ_XS_OFF && !track_tuplet(t) ? expo_span(x->span, &xin) : 0u;   /* (0.25: a polyrhythm's steps are not ticks: its EXPO is a step's) */
    ev[t].slot_start_us = now;
    ev[t].slot_dur_us = dur;
    ev[t].step_index = tr[t].step; /* UI playhead follows empty steps too */
    if (lane_rec[t]) {                       /* 0.10: REC + an ENV knob: the knob's value is written on the steps as they play */
        if (!record_arm || (uint32_t)(fm1_ms - lane_rec_ms) > 400u) lane_rec[t] = 0u;
        else {
            sq_step_t *w = &project.step[t][tr[t].pattern][tr[t].step];
            uint32_t n;
            for (n = 0; n < SQ_LANES; n++) if (lane_rec[t] & (1u << n)) w->lane[n] = lane_rec_val[t][n];
            w->flags |= SQ_STEP_SET;
            s = play_step(t, &tmp);
            grid_dirty = 1u;
        }
    }

    if (xspan && expo_hold[t]) { expo_hold[t]--; return; }   /* 0.10: inside an EXPO span: its hits keep coming */
    if (xspan && xin == 0u)                                  /* 0.10: a span begins: on a plain step (EDIT + black 5) the steps play as written */
        expo_plain[t] = ((s->flags & SQ_STEP_ON) && (s->flags & SQ_STEP_XOFF)) ? 1u : 0u;

    if (pre[t].state == 1u) {                /* it was decided a step ago, and has started (or starts now) */
        if (pre[t].step) { track_all_off(t); event_begin(t, pre[t].step, pre[t].idx, pre[t].start_us, pre[t].dur_us); }
        pre[t].state = 0u;
        tr[t].prev_hit = 1u;
        return;
    }
    if (pre[t].state == 2u) { pre[t].state = 0u; tr[t].prev_hit = 0u; if (!arp_continue(t, now, dur)) track_all_off(t); if (tl && track_audible(t)) lanes_send(t, s, tr[t].step, tl); return; }

    if (!track_audible(t)) { track_all_off(t); tr[t].prev_hit = 0u; return; }
    s = live_step(t, s, &lbuf, &hit);
    if (step_should_play(t, s, hit)) {
        played = 1u;
        if (xspan && !expo_plain[t] && xin) played = 0u;     /* (inside a span: the span's hits are the rhythm) */
    }
    tr[t].prev_hit = played;
    if (!played) {
        if (!arp_continue(t, now, dur)) track_all_off(t);   /* the step is silent: the arpeggio may run on */
        if (tl) lanes_send(t, s, tr[t].step, tl);           /* 0.10: trigless locks */
        return;
    }
    track_all_off(t);
    if (xspan && !expo_plain[t]) {           /* 0.10 EXPO over more than a step: the boundary step plays the span */
        uint32_t div = eff_div_ticks(t);
        expo_hold[t] = (uint8_t)(xspan > div ? (xspan / div - 1u > 255u ? 255u : xspan / div - 1u) : 0u);
        event_begin(t, s, tr[t].step, now, current_clock_interval() * xspan);
        return;
    }
    off = step_offset_us(t, s, tr[t].step, dur);
    if (off < 0) off = 0;                    /* (nothing to start early from: the first step of a run) */
    if (project.live.cc_lead_ms && off) {    /* 0.10 CC LEAD: the locks now, the notes a little later */
        lanes_send(t, s, tr[t].step, 0xFFu);
        ev[t].lane_locked |= 0x80u;          /* (bit 7: the first slice has had its lanes) */
    }
    event_begin(t, s, tr[t].step, now + (uint32_t)off, dur - (uint32_t)off);
}

/* The track has moved on to its next step. If that step starts before its slot, decide it now and schedule it:
 * boundary is where the next slot begins. */
static void prearm_next(uint32_t t, uint32_t slot_start, uint32_t dur)
{
    sq_step_t tmp, lbuf;
    const sq_step_t *s = play_step(t, &tmp);
    int32_t off;
    uint8_t hit;
    pre[t].state = 0u;
    if (!(s->flags & SQ_STEP_ON)) return;
    if (project.track[t].expo.shape != SQ_XS_OFF && sq_expo_span_ticks(project.track[t].expo.span)) return;   /* 0.10: spans start on the grid */
    off = step_offset_us(t, s, tr[t].step, dur);
    if (off >= 0) return;
    if (!track_audible(t)) { pre[t].state = 2u; return; }
    s = live_step(t, s, &lbuf, &hit);
    if (!step_should_play(t, s, hit)) { pre[t].state = 2u; return; }
    pre[t].buf = *s;
    pre[t].step = &pre[t].buf;
    pre[t].idx = tr[t].step;
    pre[t].dur_us = dur;
    /* 0.10: an EXPO step (span STEP) that starts early spans from where it starts to the end of its slot: its hits
     * fall where the curve says (a grace hit 86 ms before the beat, the main one on it) */
    if (project.track[t].expo.shape != SQ_XS_OFF && !(s->flags & SQ_STEP_XOFF) && !expo_plain[t]) pre[t].dur_us = dur + (uint32_t)(-off);
    pre[t].start_us = slot_start + dur - (uint32_t)(-off);
    pre[t].state = 1u;
}

static void pre_promote(uint32_t t)
{
    track_all_off(t);                        /* the step before ends where this one begins */
    event_begin(t, pre[t].step, pre[t].idx, pre[t].start_us, pre[t].dur_us);
    pre[t].step = 0;                        /* (state stays 1 until its slot begins: arm_step finishes it) */
}

/* a track starts its loop again on this clock tick (QUANTISE: a new pattern from its first step) */
static void track_restart(uint32_t t)
{
    const sq_track_cfg_t *c = &project.track[t];
    tr[t].step = c->direction == SQ_DIR_REV ? (uint8_t)(c->length - 1u) : c->start;
    tr[t].ping_dir = 1;
    tr[t].advances = 0u;
    tr[t].ppos[0] = tr[t].ppos[1] = tr[t].ppos[2] = 0u;
    tr[t].div_accum = (uint16_t)(track_tuplet(t) ? 0u : eff_div_ticks(t) - 1u);   /* (seq_clock_tick adds one: the first step plays now) */
    tup_wait &= (uint16_t)~(1u << t);
    tr[t].anchor = global_clock;                             /* 0.10: from here the track's time is counted */
    tr[t].prev_hit = 0u;
    pre[t].state = 0u;
}

/* 0.10: the track's step of `div` ticks without the time FX (VIAGGIO's HALF / DOUBLE count: they last a phrase) */
static uint8_t base_div_ticks(uint32_t t)
{
    uint32_t d = sq_div_ticks(project.track[t].division);
    if (vg_speed < 0) d *= 2u;
    if (vg_speed > 0) d = d > 1u ? d / 2u : 1u;
    return (uint8_t)(d > 255u ? 255u : d);
}
/* 0.10: the track back where its anchor and the clock say it should be (between two ticks: the next tick is served
 * as usual). Not while a DJ LOOP holds it (the loop's end does it), not a TAPE track (it has no counter). */
/* where track t is `ticks` clock ticks after its anchor, into rt (its time FX aside): a plain division's step is ticks,
 * a polyrhythm's a fraction of them */
static void track_seek_to(uint32_t t, sq_track_rt_t *rt, uint32_t ticks)
{
    if (track_tuplet(t)) {
        uint16_t num; uint8_t den;
        div_frac_x(t, 0u, &num, &den);
        sq_track_seek_frac(&project.track[t], rt, ticks, num, den);
    } else sq_track_seek(&project.track[t], rt, ticks, base_div_ticks(t));
}
static void track_realign(uint32_t t)
{
    if (track_tape(t) || (loop_on && (loop_mask & (1u << t)))) return;
    track_seek_to(t, &tr[t], global_clock - tr[t].anchor);
    tup_wait &= (uint16_t)~(1u << t);
    pre[t].state = 0u;
    if (t == selected_track) ui_dirty = grid_dirty = 1u;
}
static void realign_all(void)
{
    uint32_t t;
    for (t = 0; t < SQ_TRACKS; t++) track_realign(t);
    realign_pend = 0u;
}
/* 0.24: THE LENGTH IS THE TRACK'S, and its eight patterns fit it. A pattern shorter than the track goes round again in
 * the steps the track has more (its COPIES, sq_row_fit); one longer keeps what the track does not play. Whoever changes
 * a track's length calls track_fit with the length it had: the knob and the grid (length_apply), a snapshot, UNDO and
 * the others that put settings back (track_cfg_back), VIAGGIO's LONGER / SHORTER. `but`: the pattern that came back
 * WITH the length (UNDO's row, a dice's, RELOAD's: it is as it was at that length already), 255: none. `old_start`:
 * where the loop began - when that changed too, no copy stands for the step it stood for: the copies of the other
 * patterns are kept as steps (as the service does for the one that plays). Returns the
 * copies of the pattern that plays. (A TAPE track's steps are not played, but they are there for when it is one of
 * steps again: they fit its length as any other's.) */
static void gen_track_fit(uint32_t t, uint8_t old_len, uint8_t old_start);   /* sagga_gen.c: EVOLVE's seed is as long as its track */
static uint8_t track_fit(uint32_t t, uint8_t old_len, uint8_t old_start, uint8_t but)
{
    const sq_track_cfg_t *c = &project.track[t];
    uint32_t pat;
    uint8_t n = 0u;
    for (pat = 0; pat < SQ_PATTERNS; pat++) {
        uint8_t k;
        if (pat != but && old_start != c->start) sq_row_keep(project.step[t][pat]);
        k = sq_row_fit(project.step[t][pat], c->start, pat == but ? c->length : old_len, c->length);
        if (pat == tr[t].pattern) n = k;
    }
    gen_track_fit(t, old_len, old_start);
    gh_st[t].pat = 255u;
    if (t == selected_track) ui_dirty = grid_dirty = 1u;
    return n;
}
/* the copies follow their pattern: a track a pass. A step of the pattern was changed (by anyone: a key, the grid, a
 * tool, a page, an engine): its copies change. A copy was changed: all the copies are the player's steps from now on,
 * the pattern is as long as the track. Not while a loop between two steps holds the track (EXIT brings its loop back). */
static void ghost_service(void)
{
    uint32_t t = gh_at;
    const sq_track_cfg_t *c = &project.track[t];
    gh_at = (uint8_t)((gh_at + 1u) % SQ_TRACKS);
    uint8_t r;
    if (track_tape(t) || (sl_on & (1u << t))) return;
    r = sq_ghost_service(project.step[t][tr[t].pattern], c->start, c->length, tr[t].pattern, &gh_st[t]);
    if (r == SQ_GH_NONE || t != selected_track) return;
    if (r == SQ_GH_KEPT) status_msg("THE COPIES ARE YOUR STEPS NOW");    /* (one of them was written: the pattern is as long as the track) */
    ui_dirty = grid_dirty = 1u;
}

/* 0.11: a track's settings were put back (UNDO, a dice put back, RELOAD, the end of TEMP): if its loop is another (length,
 * start, direction, division, TAPE) and it plays, it goes where the bar says - the explorer found each of these a step or
 * more off; else only back inside its loop. `was`: the settings before they were put back. 0.24: `pat`: the pattern
 * whose steps came back with them (the others fit the length that came back). */
static void track_cfg_back(uint32_t t, const sq_track_cfg_t *was, uint8_t pat)
{
    const sq_track_cfg_t *c = &project.track[t];
    if (c->length != was->length || c->start != was->start) track_fit(t, was->length, was->start, pat);
    else gh_st[t].pat = 255u;                                             /* (a row came back: what its copies were made from is not known) */
    if (playing && (c->length != was->length || c->start != was->start || c->direction != was->direction ||
                    c->division != was->division || (c->flags & SQ_TF_TAPE) != (was->flags & SQ_TF_TAPE)))
        track_realign(t);
    if (tr[t].step >= c->length || tr[t].step < c->start) tr[t].step = c->start;   /* (TAPE, a DJ LOOP: not moved) */
}

/* the Program Changes of a scene: each channel that has one gets it (not again if it already has it) */
static void scene_send_pc(uint8_t s)
{
    uint32_t ch;
    if (s >= SQ_SCENES) return;
    for (ch = 0; ch < ch_limit(); ch++) {                      /* (0.9: channels 15 and 16 too with two ports) */
        uint8_t pc = project.scene[s].pc[ch];
        if (pc > 127u || pc_last[ch] == pc) continue;
        midi_send(0xC0u | ch, pc, 0u);
        pc_last[ch] = pc;
    }
}

static void scene_metre_bring(uint8_t s);  /* 0.26 (below, with the metre) */
static void apply_scene_x(uint8_t s, uint8_t restart)
{
    uint32_t t;
    if (s >= SQ_SCENES) return;
    mute_mask = project.scene[s].mute_mask;
    pending_mute = 0u;
    for (t = 0; t < SQ_TRACKS; t++) {
        uint8_t p = project.scene[s].pattern[t] < SQ_PATTERNS ? project.scene[s].pattern[t] : 0u;
        if (restart && playing && p != tr[t].pattern) track_restart(t);
        tr[t].pattern = p;
        tr[t].pending_pattern = SQ_NO_PENDING;
    }
    scene_cursor = s;
    scene_send_pc(s);
    if (project.scene[s].key_slot < SQ_KEYS && project.scene[s].key_slot != project.key_cur) key_select_slot(project.scene[s].key_slot);   /* 0.10: the scene's key */
    scene_metre_bring(s);                    /* 0.26: ... and its metre */
    morph_pos = 0u;                          /* MORPH starts again from the scene that plays (nothing is sent) */
    ui_dirty = grid_dirty = 1u;
}
static void apply_scene(uint8_t s) { apply_scene_x(s, 0u); }

/* QUANTISE: when the queued changes happen. AUTO is 0.4: a pattern at the end of its track's loop, a scene and a queued
 * mute at the bar. The others: everything at the next beat / bar / 2 / 4 / 8 bars, and a new pattern starts from its
 * first step there. NOW: at once. */
static const char *const QUANT_NAME[SQ_QUANTS] = {"AUTO", "NOW", "BEAT", "BAR", "2 BARS", "4 BARS", "8 BARS"};
/* 0.25: the bars are the metre's (bar_into, bar_no), the beat is one of its beats - a quarter, or three eighths, as the
 * bar divides. Until 0.24: `global_clock % 96`, `% 24`. */
static const uint8_t QUANT_BARS[SQ_QUANTS] = {1u, 0u, 0u, 1u, 2u, 4u, 8u};   /* AUTO NOW BEAT BAR 2 4 8 */
static uint8_t quant_now(void)                         /* this tick is one where the queued changes happen */
{
    uint8_t q = project.live.quant < SQ_QUANTS ? project.live.quant : 0u;
    if (q == SQ_Q_NOW) return 0u;
    if (q == SQ_Q_BEAT) return bar_beat_now();
    return (uint8_t)(bar_into() == 0u && (bar_no() % QUANT_BARS[q]) == 0u);
}
static void ktrans_apply(int32_t target);
static void quant_tick(void)
{
    uint32_t t;
    if (!quant_now()) return;
    if (ktrans_pend != SQ_KT_NONE) ktrans_apply(ktrans_pend);
    if (snap_pend < SQ_SNAPS) { uint8_t n = snap_pend; snap_pend = 255u; snap_apply(n); }   /* a SNAPSHOT that waited */
    if (restart_pend) {                               /* RESTART: every track from its first step, now */
        restart_pend = 0u;
        loop_on = 0u; loop_latched = 0u; lp_held = 0u;
        for (t = 0; t < SQ_TRACKS; t++) track_restart(t);
        ui_dirty = grid_dirty = 1u;
    }
    if (pending_scene < SQ_SCENES) {
        apply_scene_x(pending_scene, project.live.quant != SQ_Q_AUTO);
        pending_scene = SQ_NO_PENDING;
    }
    if (pending_mute) { mute_mask ^= pending_mute; pending_mute = 0u; vg_states_sync_all(); ui_dirty = grid_dirty = 1u; }
    if (project.live.quant == SQ_Q_AUTO) return;
    for (t = 0; t < SQ_TRACKS; t++) {
        if (tr[t].pending_pattern >= SQ_PATTERNS) continue;
        tr[t].pattern = tr[t].pending_pattern;
        tr[t].pending_pattern = SQ_NO_PENDING;
        vg_pattern_in(t);                                /* 0.17: a proposal brings its settings */
        track_restart(t);
        ui_dirty = grid_dirty = 1u;
    }
}

static void loop_restore(void)
{
    uint32_t t;
    for (t = 0; t < SQ_TRACKS; t++) {
        if (!(loop_mask & (1u << t))) continue;
        tr[t].step = loop_snap[t].step;
        tr[t].div_accum = loop_snap[t].div_accum;
        tr[t].ping_dir = loop_snap[t].ping_dir;
        tr[t].advances = loop_snap[t].advances;
        tr[t].loop_count = loop_snap[t].loop_count;
        memcpy(tr[t].ppos, loop_snap[t].ppos, sizeof tr[t].ppos);
        pre[t].state = 0u;                   /* what was decided for the step after is not that step any more */
    }
}

static void tool_bar_tick(void);                      /* sagga_gen.c: 0.10 WHEN / EVERY */
/* 0.11 FOLLOW RETRIG / LEGATO: the chord changed while a track that follows it holds notes: they move to the new chord
 * (RETRIG: all struck again; LEGATO: the notes the two chords share go on, the others are struck before the old ones
 * end: a mono synth slides). The notes keep the end they had. A track that began a note on this very tick is left. */
static void held_note_off(uint32_t t, uint32_t n);
static void harm_revoice(uint32_t t, uint32_t now)
{
    uint8_t notes[SQ_POLY_OUT], n, k, j, ch = track_ch(t), keep[SQ_HOLD_MAX], any = 0u;
    uint32_t end = 0u;
    const sq_track_cfg_t *c = &project.track[t];
    if (!harm_src_on[t] || harm_src_tick[t] == global_clock || !(c->flags & SQ_TF_FOLLOW) || c->follow_mode == SQ_FM_HOLD) return;
    for (k = 0; k < SQ_HOLD_MAX; k++) {
        keep[k] = 0u;
        if (hold_note[t][k] != SQ_NOTE_NONE && hold_ch[t][k] == ch && (int32_t)(hold_off_us[t][k] - now) > 20000) {
            any = 1u;
            if (hold_off_us[t][k] > end) end = hold_off_us[t][k];
        }
    }
    if (!any) { harm_src_on[t] = 0u; return; }
    n = step_notes(t, &harm_src[t], notes);
    for (k = 0; k < SQ_HOLD_MAX; k++) {                       /* the held notes the new chord has too (LEGATO keeps them) */
        if (hold_note[t][k] == SQ_NOTE_NONE || hold_ch[t][k] != ch) continue;
        for (j = 0; j < n; j++) if (notes[j] == hold_note[t][k]) keep[k] = 1u;
    }
    if (c->follow_mode == SQ_FM_RETRIG) {
        for (k = 0; k < SQ_HOLD_MAX; k++) if (hold_note[t][k] != SQ_NOTE_NONE && hold_ch[t][k] == ch) held_note_off(t, k);
        for (j = 0; j < n; j++) held_note_on(t, ch, notes[j], harm_src_vel[t], end);
        return;
    }
    {   uint8_t old[SQ_HOLD_MAX], no = 0u;                     /* LEGATO: the new ones first, then the old ones go */
        for (k = 0; k < SQ_HOLD_MAX; k++) if (hold_note[t][k] != SQ_NOTE_NONE && hold_ch[t][k] == ch && !keep[k]) old[no++] = hold_note[t][k];
        for (j = 0; j < n; j++) {
            uint8_t have = 0u;
            for (k = 0; k < SQ_HOLD_MAX; k++) if (hold_note[t][k] == notes[j] && hold_ch[t][k] == ch) have = 1u;
            if (!have) held_note_on(t, ch, notes[j], harm_src_vel[t], end);
        }
        for (j = 0; j < no; j++)
            for (k = 0; k < SQ_HOLD_MAX; k++) if (hold_note[t][k] == old[j] && hold_ch[t][k] == ch) { held_note_off(t, k); break; }
    }
}
static void harm_tick(uint32_t now)
{
    static int32_t last_id = -1;
    sq_hchord_t c;
    uint8_t idx = 0u;
    int32_t id;
    uint32_t t;
    if (!harm_chord(&c, &idx)) { last_id = -1; return; }
    id = (int32_t)idx << 24 | (int32_t)(uint8_t)c.deg << 16 | (int32_t)c.semi << 8 | (int32_t)c.shape;
    if (id == last_id) return;
    if (last_id >= 0) for (t = 0; t < SQ_TRACKS; t++) harm_revoice(t, now);
    last_id = id;
}
static void length_bar_tick(void);                    /* 0.11: the lengths that wait for the bar */
static void metre_bar_tick(void);                     /* 0.25: the bar that waits for the bar */
static void motion_tick(void);                    /* sagga_live3.c: 0.13 */
static void chain_wrap(uint32_t t);
static void slide_note(uint32_t t, const sq_step_t *s, uint8_t ch, uint32_t now);
/* a step of track t begins at `now` (a clock tick; a polyrhythm's: its own time) and lasts `dur`: it plays, the track
 * moves on to the next */
static void track_step(uint32_t t, uint32_t now, uint32_t dur, uint16_t fx)
{
    uint8_t wrapped;
    sq_track_cfg_t ecfg = project.track[t];
    if (retrig_mask & (1u << t)) {           /* RETRIG: this step is the first one of the loop */
        const sq_track_cfg_t *c = &project.track[t];
        retrig_mask &= (uint16_t)~(1u << t);
        tr[t].step = c->direction == SQ_DIR_REV ? (uint8_t)(c->length - 1u) : c->start;
        tr[t].ping_dir = 1;
        tr[t].advances = 0u;
        tr[t].ppos[0] = tr[t].ppos[1] = tr[t].ppos[2] = 0u;
        tr[t].anchor = global_clock;         /* 0.10 */
        tr[t].prev_hit = 0u;
        pre[t].state = 0u;
        if (t == selected_track) ui_dirty = 1u;
    }
    arm_step(t, now);
    live_step_done(t);                       /* TURING moves on with every step of its track */
    if (!(fx & (1u << FX_FREEZE))) {
        if (fx & (1u << FX_RND)) ecfg.direction = SQ_DIR_RANDOM;
        else if (fx & (1u << FX_REV)) ecfg.direction = ecfg.direction == SQ_DIR_FWD ? SQ_DIR_REV : ecfg.direction == SQ_DIR_REV ? SQ_DIR_FWD : ecfg.direction;
        wrapped = sq_advance_step(&ecfg, &tr[t], &sq_rng_state);
        if (wrapped) live_loop_done(t);
        if (wrapped && tr[t].pending_pattern < SQ_PATTERNS && project.live.quant == SQ_Q_AUTO) {   /* (else quant_tick) */
            tr[t].pattern = tr[t].pending_pattern;
            tr[t].pending_pattern = SQ_NO_PENDING;
            vg_pattern_in(t);                    /* 0.17 */
        } else if (wrapped && project.ext.track[t].chain_on) {
            chain_wrap(t);                       /* 0.13 CHAIN LIST: the next pattern of the list */
        } else if (wrapped && (project.track[t].flags & SQ_TF_CHAIN)) {
            tr[t].pattern ^= 1u;                 /* 0.10 CHAIN: the partner pattern plays next: 128 steps in all */
            if (t == selected_track) ui_dirty = 1u;
        }
    }
    prearm_next(t, now, dur);
    if (t == selected_track) grid_dirty = 1u;
}
/* 0.25: the polyrhythms' steps that waited for their time (every pass of the main loop; `all`: whatever the time - a
 * clock tick came, nothing of the tick before is left over) */
static void tup_service(uint32_t now, uint8_t all)
{
    uint32_t t;
    if (!tup_wait) return;
    for (t = 0; t < SQ_TRACKS; t++) {
        if (!(tup_wait & (1u << t)) || !(all || time_due(now, tup_at[t]))) continue;
        tup_wait &= (uint16_t)~(1u << t);
        if (playing && !track_tape(t)) track_step(t, tup_at[t], slot_us(t), fx_now());
    }
}
static void seq_clock_tick(uint32_t now)
{
    uint32_t t;
    uint16_t fx = fx_now();
    tup_service(now, 1u);                              /* 0.25: a polyrhythm's step of the tick before, if it still waits */

    /* 0.10: time put back in line: a time FX let go (HALF, DOUBLE, REV, FREEZE, RND), a length changed */
    if ((fx_pos_prev & FX_POS) && !(fx & FX_POS)) realign_all();
    fx_pos_prev = (uint16_t)(fx & FX_POS);
    if (realign_pend) { for (t = 0; t < SQ_TRACKS; t++) if (realign_pend & (1u << t)) track_realign(t); realign_pend = 0u; }

    if (bar_into() == 0u && global_clock) {           /* a bar line (0.25: of the metre's bar): STOP if asked, the song, EVOLVE */
        if (stop_at_bar) { stop_at_bar = 0u; transport_stop(); return; }
        metre_bar_tick();                             /* 0.25: a bar that waited for this line begins on it */
        vg_bar_tick();                                /* 0.9: the phrase, the queue at its boundary, the energy */
        regia_bar();                                  /* 0.9: the Pi's phrase that waited, a STATO */
        song_bar_tick();
        length_bar_tick();                            /* 0.11: the lengths that waited for the bar */
        gen_bar_tick();
        tool_bar_tick();                              /* 0.10: a tool that waited for its bar, the one that repeats */
    } else if (bar_beat_now()) vg_beat_tick();        /* 0.10: VIAGGIO's moves at the beat (QUANTISE BEAT; 0.25: the metre's beats) */
    quant_tick();                                     /* then what was queued: scene, mutes, patterns */
    /* 0.24: a loop that changed ON this tick (a length that waited for the bar, a snapshot, a pattern with another
     * loop) plays this tick's step from where the clock says it is. Until 0.23.2 it was put in line at the NEXT tick:
     * the step on the bar line was the old loop's (a track of 19 steps made 32 at a bar played its step 11 there). */
    if (realign_pend) { for (t = 0; t < SQ_TRACKS; t++) if (realign_pend & (1u << t)) track_realign(t); realign_pend = 0u; }
    if (loop_on) {
        uint32_t el = global_clock - loop_t0;
        if (el && (el % loop_len) == 0u) loop_restore();
    }

    tape_clock_tick(now, current_clock_interval());   /* 0.11: the TAPE tracks' notes of this tick */
    for (t = 0; t < SQ_TRACKS; t++) {
        uint8_t div = eff_div_ticks(t);
        if (track_tape(t)) continue;                   /* 0.11: a TAPE track has no steps to play */
        if (track_tuplet(t)) {                         /* 0.25: a polyrhythm: its step begins on this tick, or before the next */
            uint16_t num; uint8_t den;
            div_frac_x(t, 1u, &num, &den);
            if (tr[t].div_accum < den) {
                uint32_t wait = (uint32_t)tr[t].div_accum * current_clock_interval() / den;
                tr[t].div_accum = (uint16_t)(tr[t].div_accum + num);
                if (!wait) track_step(t, now, slot_us(t), fx);
                else { tup_at[t] = now + wait; tup_wait |= (uint16_t)(1u << t); }
            }
            tr[t].div_accum = (uint16_t)(tr[t].div_accum - den);
            continue;
        }
        tr[t].div_accum++;
        if (tr[t].div_accum >= div) {
            tr[t].div_accum = (uint16_t)(tr[t].div_accum >= 2u * div ? tr[t].div_accum % div : tr[t].div_accum - div);
            track_step(t, now, current_clock_interval() * div, fx);
        }
    }
    if (global_clock % 6u == 0u) { harm_tick(now); motion_tick(); link_16th(); }   /* 0.11: a chord that changes on this 16th moves the held notes that follow it; 0.13 MOTION */
    click_tick(now);                                   /* 0.26: the metronome: this tick's beat, or the FM-1's own sound asked ahead */
    global_clock++;
}

/* a note of the step with the FX that move notes (O+, O-, 5TH: still in the key); 0.20: OCTAVE is in the chain (mfx_run) */
static uint8_t fx_note(uint32_t t, uint8_t note, int32_t fxt)
{
    uint8_t v = clamp_note((int32_t)note + fxt);
    if (fxt && track_in_key(t)) v = sq_scale_snap(v, project.key_root, project.key_scale);
    return v;
}

/* 0.13 TRIG: a hit of track t starts the cycle of every LFO it triggers (the sidechain: DECAY, inverted, on a volume) */
static void lfo_hit(uint32_t t, uint32_t now)
{
    uint32_t i;
    for (i = 0; i < SQ_LFOS; i++)
        if (project.ext.lfo[i].trig == t + 1u) { lfo_trig_us[i] = now; lfo_trig_seen |= (uint16_t)(1u << i); }
}
/* 0.20: how long that hit's note is held: an ENV it triggers sustains as long */
static uint32_t lfo_gate_us[SQ_LFOS];
static uint8_t mod_vel_seen[SQ_TRACKS];               /* the last velocity of each track (the MOD MATRIX's VELOCITY) */
static void lfo_gate(uint32_t t, uint32_t gate)
{
    uint32_t i;
    for (i = 0; i < SQ_LFOS; i++) if (project.ext.lfo[i].trig == t + 1u) lfo_gate_us[i] = gate;
}

/* 0.22: the MIDI FX chain made this note longer than the gap to the track's next hit: it goes out as a held note, with its
 * own end, not as a note of the step (those end when the track's next step comes). Until 0.21 the GATE effect's FIXED
 * 1/8 .. 2 BARS and its x3/2, x2, x4 stopped at the next step all the same: a 1/16 whatever was asked */
#define MFX_LONG(ng) ((ng) > gate && (ng) > ev[t].slice_us)
static void fire_slice(uint32_t t, uint32_t now)
{
    const sq_step_t *s = ev[t].step;
    const sq_track_cfg_t *cfg = &project.track[t];
    uint8_t ch = track_ch(t);
    uint16_t fx = fx_now();
    uint32_t gate, n;
    uint8_t slice_no = (uint8_t)(ev[t].ratchet_total - ev[t].ratchet_left), vel, held = 0u;
    int32_t v, fxt = 0;

    if (!track_audible(t)) { ev[t].ratchet_left = 0u; return; }   /* (gone silent in the middle of a step) */
    lfo_hit(t, now);                                   /* 0.13: the LFOs this track triggers start their cycle */
    if (ev[t].expo == 1u) {                            /* 0.10: this hit lasts until the next one (the last: the span's end) */
        uint32_t end = slice_no + 1u < ev[t].ratchet_total ? ev[t].expo_t[slice_no + 1u] : ev[t].span_us;
        ev[t].slice_us = end > ev[t].expo_t[slice_no] ? end - ev[t].expo_t[slice_no] : 1u;
    } else if (ev[t].expo == 2u) {                     /* SETTLE: the gap from where we are */
        { sq_expo_t xe = project.track[t].expo; xe.hits = ev[t].x_hits; ev[t].slice_us = sq_expo_settle_gap(&xe, ev[t].x_pos, ev[t].span_us, current_clock_interval() * 24u, &sq_rng_state); }
        if (ev[t].x_pos + ev[t].slice_us > ev[t].span_us) ev[t].slice_us = ev[t].span_us > ev[t].x_pos ? ev[t].span_us - ev[t].x_pos : 1u;
    }
    if (s->length > 100u) {
        int32_t mod = clamp_i32(100 + mac_gate + vg_gate_adj() + lfo_mod[t][SQ_LD_GATE - 1u], 10, 200);
        gate = sq_gate_us(s->length, ev[t].slot_dur_us, ev[t].slice_us);
        gate = (uint32_t)(((uint64_t)gate * (uint32_t)mod) / 100u);
    } else {
        uint32_t gate_pct = (uint32_t)clamp_i32((((int32_t)(s->length ? s->length : 1u) + lfo_mod[t][SQ_LD_GATE - 1u]) * (100 + mac_gate + vg_gate_adj())) / 100, 1, 100);
        uint8_t hold = ev[t].ratchet_total <= 1u && !ev[t].expo ? live_hold(t, ev[t].step_index) : 0u;
        gate = (ev[t].slice_us * gate_pct) / 100u;
        if (hold > 1u) { gate = (uint32_t)(((uint64_t)ev[t].slot_dur_us * hold * 95u) / 100u); held = 1u; }   /* 0.11: to the next hit the algorithm makes */
    }
    if (ev[t].expo) gate = ev[t].slice_us * project.track[t].expo.gate / 100u;   /* 0.10: EXPO's gate, of the gap */
    if (fx & (1u << FX_STACC)) gate = ev[t].slice_us * 2u / 5u + 1u;      /* 0.8: of the slice (0.7: of the step) */
    if (fx & (1u << FX_LEGATO)) gate = ev[t].slot_dur_us;
    if (!gate) gate = 1u;
    if (fx & (1u << FX_OCTUP)) fxt += 12;
    if (fx & (1u << FX_OCTDN)) fxt -= 12;
    if (fx & (1u << FX_FIFTH)) fxt += 7;

    v = (int32_t)(s->velocity ? s->velocity : 1u) + cfg->vel_offset + lfo_mod[t][SQ_LD_VEL - 1u] + mac_vel + vg_vel_adj(t) + live_vel(t, ev[t].step_index)
        + sq_groove_vel(project.ext.track[t].groove, project.ext.track[t].groove_amt, ev[t].step_index);   /* 0.15 GROOVE */
    if (cfg->hum_vel) v += (int32_t)(sq_rng_next(&sq_rng_state) % (2u * cfg->hum_vel + 1u)) - (int32_t)cfg->hum_vel;
    v = clamp_i32(v, 1, 127);
    vel = sq_ramp_velocity((uint8_t)v, s->ramp, slice_no, ev[t].ratchet_total);
    if (ev[t].expo == 1u) vel = sq_expo_vel(&project.track[t].expo, vel, slice_no);
    if (ev[t].expo == 2u) vel = sq_expo_vel(&project.track[t].expo, vel, (ev[t].x_pos * (project.track[t].expo.hits - 1u)) / (ev[t].span_us ? ev[t].span_us : 1u));
    if (fx & (1u << FX_MAXVEL)) vel = 127u;
    mod_vel_seen[t] = vel;                             /* 0.20: the MOD MATRIX's VELOCITY of this track */
    lfo_gate(t, gate);                                 /* 0.20: an ENV it triggers holds this long */

    for (n = 0; n < SQ_POLY_OUT; n++) midi_note_off_track(t, n);
    ev[t].strum_mask = 0u;                             /* (a strum of the slice before that has not finished: it ends) */
    ev[t].strum_held = 0u;

    if (ev[t].first_ratchet) {
        if (!(ev[t].lane_locked & 0x80u)) lanes_send(t, s, ev[t].step_index, 0xFFu);   /* (CC LEAD sent them already) */
        ev[t].lane_locked &= 0x7Fu;
        ev[t].first_ratchet = 0u;
    }
    if (slice_no == 0u) slide_note(t, s, ch, now);    /* 0.13 SLIDE: the portamento for this note (CC 65 before it) */
    /* 0.10 TIE: the last slice of a tied step holds into the next step (15 ms over its line: a mono synth slides) */
    if ((s->flags & SQ_STEP_LEGATO) && ev[t].ratchet_left == 1u && !ev[t].expo)
        gate = ev[t].slot_start_us + ev[t].slot_dur_us + 15000u - now;

    if (ev[t].arp_n) {                 /* ARP: one note per slice */
        uint8_t mode = SQ_CHORD_MODE(cfg->chord_mode), i;
        harm_src_on[t] = 0u;           /* (0.11: an arpeggio's notes do not move with the chords) */
        if (mode == SQ_CHORD_ARP_RND) i = (uint8_t)(sq_rng_next(&sq_rng_state) % ev[t].arp_n);
        else if (mode == SQ_CHORD_ARP_WALK) {
            int32_t p = (int32_t)(ev[t].arp_pos % ev[t].arp_n), d = (sq_rng_next(&sq_rng_state) & 1u) ? 1 : -1;
            p += d;
            if (p < 0) p = 1 < ev[t].arp_n ? 1 : 0;
            if (p >= (int32_t)ev[t].arp_n) p = ev[t].arp_n > 1u ? (int32_t)ev[t].arp_n - 2 : 0;
            i = (uint8_t)p;
        } else i = (uint8_t)(ev[t].arp_pos % ev[t].arp_n);
        {
            uint8_t note = fx_note(t, ev[t].arp[i], fxt), nv = vel;
            uint32_t ng;
            ev[t].arp_pos = (uint8_t)((mode == SQ_CHORD_ARP_RND || mode == SQ_CHORD_ARP_WALK) ? i : (i + 1u) % ev[t].arp_n);
            if (cfg->arp_rate && s->length > 100u && !(s->flags & SQ_STEP_LEGATO)) gate = ev[t].slice_us * SQ_ARP_EVERY(cfg->arp_rate) * 4u / 5u;   /* (a long gate holds the chord, not the note; 0.18: a slow RATE's note lasts its steps) */
            ng = gate;
            if (mfx_run(t, ch, slice_no, &note, &nv, &ng, now)) {   /* 0.20: the MIDI FX chain (it may drop the note) */
                if (fx & (1u << FX_MAXVEL)) nv = 127u;
                if (((s->length > 100u || held) && !cfg->arp_rate) || (s->flags & SQ_STEP_LEGATO) || MFX_LONG(ng)) held_note_on(t, ch, note, nv, now + ng);
                else {
                    held_same_off(t, ch, note, now + ng);
                    midi_send(0x90u | ch, note, nv);
                    ev[t].active_note[0] = note;
                    ev[t].active_ch[0] = ch;
                    ev[t].off_us[0] = now + ng;
                }
            }
        }
    } else {                           /* BLOCK: the whole chord (STRUM: one note after the other) */
        uint8_t vn = ev[t].vn < SQ_POLY_OUT ? ev[t].vn : (uint8_t)SQ_POLY_OUT;
        harm_src_on[t] = 0u;
        if ((s->length > 100u || held || (s->flags & SQ_STEP_LEGATO)) && (cfg->flags & SQ_TF_FOLLOW) && !cfg->strum && cfg->follow_mode != SQ_FM_HOLD) {
            harm_src[t] = *s; harm_src_vel[t] = vel; harm_src_on[t] = 1u; harm_src_tick[t] = global_clock;   /* 0.11: it may move with the chords */
        }
        for (n = 0; n < vn; n++) {
            uint32_t src = cfg->strum < 0 ? vn - 1u - n : n, delay = 0u, ng = gate;
            uint8_t note = fx_note(t, ev[t].vnote[src], fxt), bit = (uint8_t)(1u << src), nv = vel;
            if (cfg->strum && vn > 1u) {
                uint32_t spread = (ev[t].slice_us * (uint32_t)(cfg->strum < 0 ? -cfg->strum : cfg->strum)) / 100u;
                delay = (spread * n) / (vn - 1u);
            }
            if (!mfx_run(t, ch, slice_no, &note, &nv, &ng, now + delay)) continue;   /* 0.20: the chain (it may drop the note) */
            if (fx & (1u << FX_MAXVEL)) nv = 127u;
            if (delay) {                               /* later in its own slot of the track: MUTE and STOP end it too */
                ev[t].strum_note[src] = note; ev[t].strum_ch[src] = ch; ev[t].strum_vel[src] = nv;
                ev[t].strum_on[src] = now + delay; ev[t].strum_off[src] = now + delay + ng;
                ev[t].strum_mask |= bit;
                if (s->length > 100u || held || (s->flags & SQ_STEP_LEGATO) || MFX_LONG(ng)) ev[t].strum_held |= bit;
            } else if (s->length > 100u || held || (s->flags & SQ_STEP_LEGATO) || MFX_LONG(ng)) held_note_on(t, ch, note, nv, now + ng);
            else {
                held_same_off(t, ch, note, now + ng);
                midi_send(0x90u | ch, note, nv);
                ev[t].active_note[src] = note;
                ev[t].active_ch[src] = ch;
                ev[t].off_us[src] = now + ng;
            }
        }
    }
    ev[t].ratchet_left--;
    if (ev[t].expo == 1u && ev[t].ratchet_left) ev[t].ratchet_next_us = ev[t].first_us + ev[t].expo_t[slice_no + 1u];
    else if (ev[t].expo == 2u) {
        ev[t].x_pos += ev[t].slice_us;
        if (ev[t].x_pos + 2000u >= ev[t].span_us) ev[t].ratchet_left = 0u;   /* the span is full */
        else ev[t].ratchet_next_us = ev[t].first_us + ev[t].x_pos;
    } else ev[t].ratchet_next_us += ev[t].slice_us;
}

static void strum_service(uint32_t t, uint32_t now)
{
    uint32_t n;
    for (n = 0; n < SQ_POLY_OUT; n++) {
        uint8_t bit = (uint8_t)(1u << n);
        if (!(ev[t].strum_mask & bit) || !time_due(now, ev[t].strum_on[n])) continue;
        ev[t].strum_mask &= (uint8_t)~bit;
        if (ev[t].strum_held & bit) {
            ev[t].strum_held &= (uint8_t)~bit;
            held_note_on(t, ev[t].strum_ch[n], ev[t].strum_note[n], ev[t].strum_vel[n], ev[t].strum_off[n]);
        } else {
            midi_note_off_track(t, n);
            held_same_off(t, ev[t].strum_ch[n], ev[t].strum_note[n], ev[t].strum_off[n]);
            midi_send(0x90u | ev[t].strum_ch[n], ev[t].strum_note[n], ev[t].strum_vel[n]);
            ev[t].active_note[n] = ev[t].strum_note[n];
            ev[t].active_ch[n] = ev[t].strum_ch[n];
            ev[t].off_us[n] = ev[t].strum_off[n];
        }
    }
}

static void service_track_events(uint32_t now)
{
    uint32_t t, n;
    tup_service(now, 0u);                              /* 0.25: the polyrhythms' steps, at their own time */
    for (t = 0; t < SQ_TRACKS; t++) {
        if (pre[t].state == 1u && pre[t].step && time_due(now, pre[t].start_us)) pre_promote(t);
        for (n = 0; n < SQ_POLY_OUT; n++)
            if (ev[t].active_note[n] != SQ_NOTE_NONE && time_due(now, ev[t].off_us[n]))
                midi_note_off_track(t, n);
        for (n = 0; n < SQ_HOLD_MAX; n++)
            if (hold_note[t][n] != SQ_NOTE_NONE && time_due(now, hold_off_us[t][n]))
                held_note_off(t, n);
        if (ev[t].strum_mask) strum_service(t, now);
        while (ev[t].ratchet_left && time_due(now, ev[t].ratchet_next_us)) fire_slice(t, now);
    }
    defer_service(now);
    tape_service(now);
}

/* ---- 0.20 the MOD MATRIX: each slot's source now, -1000..+1000 (the unipolar ones 0..+1000) */
static int16_t lfo_out[SQ_LFOS];                      /* each LFO's output, -1000..+1000 (ENV 0..+1000), from its last pass */
static int16_t mod_depth[SQ_LFOS], mod_center[SQ_LFOS];   /* what the matrix adds to the LFOs, -1000..+1000 */
static uint8_t cc_in_val[128];                        /* the last value of each CC from MIDI IN (CC IN) */
static uint8_t vg_energy_now(void);                   /* sagga_viaggio.c */
static int32_t mod_src(const sq_mod_t *m, uint32_t slot)
{
    switch (m->src) {
    case SQ_MS_LFO:    return lfo_out[m->src_i & 15u];
    case SQ_MS_MACRO:  return m->src_i == 0u ? mac_vel * 1000 / 63 : m->src_i == 1u ? mac_gate * 10 : m->src_i == 2u ? mac_swing * 40 : mac_filt * 1000 / 64;
    case SQ_MS_ENERGY: return ((int32_t)vg_energy_now() - 50) * 20;
    case SQ_MS_RANDOM: return (int32_t)(hash3(global_clock / 6u, slot, 0x5EEDu) % 2001u) - 1000;   /* a new value each 16th */
    case SQ_MS_VEL:    return (int32_t)mod_vel_seen[m->src_i % SQ_TRACKS] * 1000 / 127;
    case SQ_MS_CCIN:   return (int32_t)cc_in_val[m->src_i & 127u] * 1000 / 127;
    default:           return 0;
    }
}
static void mod_service(void)
{
    uint32_t i;
    memset(mod_depth, 0, sizeof mod_depth); memset(mod_center, 0, sizeof mod_center); memset(mod_fx, 0, sizeof mod_fx);
    for (i = 0; i < SQ_MODS; i++) {
        const sq_mod_t *m = &project.ext.mod[i];
        int32_t c;
        uint32_t k = m->dst_i & 15u;
        if (m->src == SQ_MS_OFF || m->dst == SQ_MD_OFF || !m->amt) continue;
        c = mod_src(m, i) * m->amt / 100;
        switch (m->dst) {
        case SQ_MD_DEPTH:  mod_depth[k] = (int16_t)clamp_i32(mod_depth[k] + c, -1000, 1000); break;
        case SQ_MD_CENTER: mod_center[k] = (int16_t)clamp_i32(mod_center[k] + c, -1000, 1000); break;
        case SQ_MD_VEL:    lfo_mod[k][SQ_LD_VEL - 1u] = (int16_t)(lfo_mod[k][SQ_LD_VEL - 1u] + c * 63 / 1000); break;
        case SQ_MD_GATE:   lfo_mod[k][SQ_LD_GATE - 1u] = (int16_t)(lfo_mod[k][SQ_LD_GATE - 1u] + c * 50 / 1000); break;
        case SQ_MD_CHANCE: lfo_mod[k][SQ_LD_CHANCE - 1u] = (int16_t)(lfo_mod[k][SQ_LD_CHANCE - 1u] + c * 50 / 1000); break;
        case SQ_MD_TIMING: lfo_mod[k][SQ_LD_TIMING - 1u] = (int16_t)(lfo_mod[k][SQ_LD_TIMING - 1u] + c * 25 / 1000); break;
        case SQ_MD_SWING:  lfo_mod[k][SQ_LD_SWING - 1u] = (int16_t)(lfo_mod[k][SQ_LD_SWING - 1u] + c * 25 / 1000); break;
        case SQ_MD_FX:     mod_fx[k] = (int16_t)clamp_i32(mod_fx[k] + c / 10, -100, 100); break;
        default: break;
        }
    }
}

static void lfo_send_cc(uint32_t i, const sq_lfo_t *l, uint8_t v)
{
    if ((!lfo_last_valid[i] || v != lfo_last[i]) && (uint32_t)(fm1_ms - lfo_sent_ms[i]) >= 8u && midi_tx_room() > 24u) {
        send_cc(l->target < ch_limit() ? l->target : 0u, l->param, v);
        lfo_last[i] = v;
        lfo_last_valid[i] = 1u;
        lfo_sent_ms[i] = fm1_ms;
    }
}
static void lfo_track_add(const sq_lfo_t *l, int32_t o)   /* o: -63 .. +63, on the parameter of its track */
{
    uint32_t t = l->target < SQ_TRACKS ? l->target : 0u;
    if (vg_lfo_pct() < 100u) o = o * (int32_t)vg_lfo_pct() / 100;
    switch (l->dest) {
    case SQ_LD_VEL:    break;                                             /* +-63 */
    case SQ_LD_GATE:   o = o * 50 / 64; break;
    case SQ_LD_CHANCE: o = o * 50 / 64; break;
    case SQ_LD_TIMING: o = o * 25 / 64; break;
    default:           o = (o + 64) * 25 / 128; break;                    /* swing: 0 .. +25 */
    }
    lfo_mod[t][l->dest - 1u] = (int16_t)(lfo_mod[t][l->dest - 1u] + o);
}
static uint32_t ticks256(uint32_t us, uint32_t interval)   /* a time in clock ticks x 256 (at most 65535 ticks) */
{
    uint32_t q = us / interval;
    if (q > 65535u) return 65535u * 256u;
    return q * 256u + (us % interval) * 256u / interval;
}
/* 0.20 ENV: the envelope's level (0..65535) as the LFO's output: up from CENTER by DEPTH (INVERT: down) */
static void env_out(uint32_t i, const sq_lfo_t *l, uint32_t lvl)
{
    int32_t sgn = (l->flags & SQ_LF_INVERT) ? -1 : 1, amt = (int32_t)(lvl * l->depth / 65535u);   /* 0..127 */
    lfo_out[i] = (int16_t)(sgn * amt * 1000 / 127);
    if (l->dest == SQ_LD_CC) {
        if (vg_lfo_pct() < 100u) amt = amt * (int32_t)vg_lfo_pct() / 100;
        lfo_send_cc(i, l, (uint8_t)clamp_i32((int32_t)l->center + sgn * amt, 0, 127));
    } else if (l->dest < SQ_LD_KINDS) lfo_track_add(l, sgn * amt / 2);
}

/* ---- LFOs: sixteen of them, locked to the clock (a tick plus the part of it that has passed) */
static void lfo_service(uint32_t now)
{
    uint32_t i, since, interval, tick, frac;
    uint32_t last_tick = project.clock_mode == SQ_CLOCK_SLAVE ? last_ext_clock_us : last_master_tick_us;
    memset(lfo_mod, 0, sizeof lfo_mod);
    if (!playing) { memset(lfo_out, 0, sizeof lfo_out); mod_service(); return; }   /* (0.20: ready for the first step) */
    mod_service();                                    /* 0.20: the MOD MATRIX (the LFO sources from their last pass) */
    interval = current_clock_interval();
    since = (uint32_t)(now - last_tick);
    if (since > interval) since = interval;
    frac = interval ? ((since << 10) / interval) << 6 : 0u;
    if (frac > 65535u) frac = 65535u;
    for (i = 0; i < SQ_LFOS; i++) {
        sq_lfo_t lb = project.lfo[i];
        const sq_lfo_t *l = &lb;
        const sq_lfox_t *x = &project.ext.lfo[i];
        uint32_t fr = frac;
        if (!l->enabled) { lfo_out[i] = 0; continue; }
        lb.depth = (uint8_t)clamp_i32((int32_t)lb.depth + mod_depth[i] * 127 / 1000, 0, 127);    /* 0.20 MOD MATRIX */
        lb.center = (uint8_t)clamp_i32((int32_t)lb.center + mod_center[i] * 64 / 1000, 0, 127);
        lb.rate = sq_lfo_rate_at(&project.lfo[i], x, global_clock);          /* 0.13 RATE SEQ: the rate of this beat / bar */
        tick = global_clock + ((l->flags & SQ_LF_RETRIG) ? 0u : lfo_carry);
        if (x->seq_n >= 2u) tick = sq_lfo_seq_tick(x, global_clock);        /* (each rate starts its cycle) */
        if (x->trig) {                                                        /* 0.13 TRIG: from the track's last hit, once */
            uint32_t cyc = sq_lfo_ticks(lb.rate);
            if (!(lfo_trig_seen & (1u << i)) || !interval) { tick = cyc - 1u; fr = 65535u; }
            else {
                uint32_t el = (uint32_t)(now - lfo_trig_us[i]);
                tick = el / interval;
                fr = ((el % interval) << 10) / interval << 6;
                if (fr > 65535u) fr = 65535u;
                if (tick >= cyc) { tick = cyc - 1u; fr = 65535u; }            /* the end of its cycle: it stays there */
            }
        }
        if (l->shape == SQ_LFO_ENV) {                                         /* 0.20 ENV: the level of the envelope */
            const sq_lfoe_t *e = &project.ext.lfoe[i];
            uint32_t lvl = 0u;                                                /* (ticks x 256: 32 bits, the FM-1 has no 64-bit division) */
            if (x->trig) {
                if ((lfo_trig_seen & (1u << i)) && interval) lvl = sq_env_level(e, ticks256((uint32_t)(now - lfo_trig_us[i]), interval), ticks256(lfo_gate_us[i], interval));
            } else {                                                          /* the clock: once a cycle of its RATE, held half */
                uint32_t cyc = sq_lfo_ticks(lb.rate);
                lvl = sq_env_level(e, (tick % cyc) * 256u + (fr >> 8), cyc * 128u);
            }
            env_out(i, l, lvl);
            continue;
        }
        if (l->dest == SQ_LD_CC) {
            uint8_t v = sq_lfo_cc(l, (uint8_t)i, tick, (uint16_t)fr);
            lfo_out[i] = (int16_t)clamp_i32(((int32_t)v - (int32_t)l->center) * 1000 / 64, -1000, 1000);
            if (vg_lfo_pct() < 100u) v = (uint8_t)clamp_i32((int32_t)l->center + ((int32_t)v - (int32_t)l->center) * (int32_t)vg_lfo_pct() / 100, 0, 127);
            lfo_send_cc(i, l, v);
        } else if (l->dest == SQ_LD_MOD) {                                   /* 0.20 MOD ONLY: a source, nothing sent */
            lfo_out[i] = (int16_t)clamp_i32(sq_lfo_offset(l, (uint8_t)i, tick, (uint16_t)fr) * 1000 / 63, -1000, 1000);
        } else if (l->dest < SQ_LD_KINDS) {
            int32_t o = sq_lfo_offset(l, (uint8_t)i, tick, (uint16_t)fr);       /* -63 .. +63 */
            lfo_out[i] = (int16_t)clamp_i32(o * 1000 / 63, -1000, 1000);
            lfo_track_add(l, o);
        }
    }
}

/* ---- transport */
/* the tracks where they are at clock tick `ticks`, having begun at tick `from` (0: the start; 0.26: the bar line a
 * song's scene brought another metre on - every track began again there) */
static void seek_tracks(uint32_t from, uint32_t ticks)
{
    uint32_t t, el = ticks >= from ? ticks - from : 0u;
    for (t = 0; t < SQ_TRACKS; t++) {
        tr[t].anchor = from;
        if (track_tuplet(t)) { uint16_t num; uint8_t den; sq_div_frac(project.track[t].division, &num, &den); sq_track_seek_frac(&project.track[t], &tr[t], el, num, den); }
        else sq_track_seek(&project.track[t], &tr[t], el, sq_div_ticks(project.track[t].division));
        pre[t].state = 0u;
    }
}
static void seek_ticks(uint32_t ticks)          /* Song Position Pointer: where every track is after `ticks` ticks */
{
    seek_tracks(0u, ticks);
    global_clock = ticks;
    clk_next = ticks;
    tup_wait = 0u;
    bar_origin = 0u; bar_base = 0u;                    /* 0.25: a song position is counted in the bar as it is now, from the song's start */
}

static void transport_reset(void)
{
    uint32_t now;
    cnt_on = 0u;                                       /* 0.26: a count that ran is over (whoever starts the transport) */
    panic_all();
    lfo_carry += global_clock;
    lfo_trig_seen = 0u;                                /* 0.13: the TRIG LFOs wait for their track's first hit */
    project_runtime_reset(0u);
    memset(lfo_last_valid, 0, sizeof lfo_last_valid);
    now = sq_micros();
    next_master_clock_us = now;
    last_master_tick_us = now;
    grid_dirty = ui_dirty = 1u;
}

static void take_clear(void);                    /* sagga_live2.c: 0.12 */
static void brk_roll_clear(void);                /* sagga_break.c: 0.12 */
static void rep_clear(void);                     /* sagga_break.c: 0.13 */
static void chain_start(void);                   /* sagga_live3.c: 0.13 */
static void transport_start(void)
{
    transport_reset();
    take_clear();                                /* 0.12: TAKE remembers this run's notes only (the clock starts again) */
    rec_open_n = 0u;                             /* 0.10: notes still open from before do not get a length now */
    tape_all_off();
    song_start_hook();                           /* the song (if it is on) starts from its first scene */
    chain_start();                               /* 0.13: the CHAIN LISTs from their first entry */
    scene_send_pc(scene_cursor);                 /* the synths get the scene's programs (the ones they do not have yet) */
    playing = 1u;
    vg_transport_start();                        /* 0.9: the phrase starts with the transport */
    regia_transport_start();
    if (project.clock_mode == SQ_CLOCK_MASTER) midi_send(0xFAu, 0u, 0u);
    ui_dirty = 1u;
}

static void transport_continue(void)             /* from where it stopped; the receiver is told where that is */
{
    uint32_t now = sq_micros(), beats = global_clock / 6u;
    if (project.clock_mode == SQ_CLOCK_MASTER) {
        midi_send(0xF2u, beats & 127u, (beats >> 7) & 127u);
        midi_send(0xFBu, 0u, 0u);
    }
    next_master_clock_us = now;
    last_master_tick_us = now;
    cnt_on = 0u; clk_next = global_clock;        /* 0.26: no count; the click from this tick */
    realign_all();                               /* 0.11: what changed while it was stopped (a direction, settings put back)
                                                  * goes where the clock is: CONTINUE carries on in time (the explorer) */
    playing = 1u;
    ui_dirty = grid_dirty = 1u;
}

static void transport_stop_x(uint8_t send_fc)     /* the master's STOP, and the slave's when 0xFC comes (0.9: one body) */
{
    uint8_t had_loop = loop_on;
    playing = 0u;
    loop_on = 0u; loop_latched = 0u; lp_held = 0u;
    if (had_loop) realign_all();                 /* 0.11: a DJ LOOP ends with the STOP: the tracks where the clock is, so a
                                                  * CONTINUE carries on in time (the explorer) */
    retrig_mask = 0u; restart_pend = 0u; stop_at_bar = 0u;
    if (ktrans_pend != SQ_KT_NONE) ktrans_apply(ktrans_pend);     /* (what was queued is done) */
    if (snap_pend < SQ_SNAPS) { uint8_t n = snap_pend; snap_pend = 255u; snap_apply(n); }
    mute_mask ^= pending_mute;                   /* what was queued is done */
    pending_mute = 0u;
    vg_states_sync_all();                        /* 0.12: the mutes just applied, in VIAGGIO's states */
    metre_bar_tick();                            /* 0.25: the bar that waited for a bar (playing is 0: no track begins again) */
    length_bar_tick();                           /* 0.11: the lengths that waited for a bar */
    vg_transport_stop();
    brk_roll_clear(); rep_clear();               /* 0.12: a ROLL held through the stop ends here (0.13: a REPEAT too) */
    panic_all();
    if (send_fc && project.clock_mode == SQ_CLOCK_MASTER) midi_send(0xFCu, 0u, 0u);
    ui_dirty = grid_dirty = 1u;
    lib_transport_stopped();
}
static void transport_stop(void) { transport_stop_x(1u); }

static void service_master_clock(uint32_t now)
{
    uint32_t interval, guard = 0u;
    if (!playing || project.clock_mode != SQ_CLOCK_MASTER) return;
    interval = master_clock_interval();

    /* RUN is alive but the sequencer clock stopped progressing:
       recover automatically instead of requiring STOP/PLAY. */
    if (last_master_tick_us &&
        (uint32_t)(now - last_master_tick_us) > 500000u) {
        next_master_clock_us = now;
        last_master_tick_us = now;
        clock_recoveries++;
        SQ_LOG_RECOVERY("stalled");
        ui_dirty = 1u;
    }

    while (playing && time_due(now, next_master_clock_us) && guard < 8u) {
        uint32_t tick_at = next_master_clock_us;
        guard++;
        midi_send(0xF8u, 0u, 0u);
        seq_clock_tick(tick_at);
        last_master_tick_us = tick_at;
        next_master_clock_us = tick_at + interval;
    }

    /* Do not create a huge burst after a long UI/input stall. */
    if (playing && guard == 8u && time_due(now, next_master_clock_us)) {
        next_master_clock_us = now + interval;
        last_master_tick_us = now;
        clock_recoveries++;
        SQ_LOG_RECOVERY("8 ticks behind");
        ui_dirty = 1u;
    }
}

/* ---- LOOP and REPEAT: one gesture (0.5.1). A length is pressed (a black key with FX held, a pad of the grid's FX view,
 * a button of the remote): from that moment the tracks come back to where they were every `ticks` ticks.
 *   let go quickly (a tap)       LOOP: it stays. The same length tapped again, or EXIT, ends it (0.10: the tracks land
 *                                where they would have been, like REPEAT; 0.3 went on from the loop).
 *   held longer than 0.3 s       REPEAT: let go, and every track is where it would have been without it
 *                                (track_realign): the music lands in time.
 *   held over a LOOP             the length while it is held; let go, the LOOP goes on at its length.
 * The sources (bits of lp_held): grid pads 0-15, the panel's black keys 16-23, the remote's buttons 24-27. */
#define SQ_REPEAT_MS 300u
#define LP_GRID   0u
#define LP_PANEL  16u
#define LP_REMOTE 24u
#define LP_SRCS   28u
static uint32_t lp_t[LP_SRCS];

/* the eight lengths of a LOOP (the black keys, the grid): 1/32 .. 1/2, then 1, 2, 4 BARS - 0.25: bars of the metre */
static uint16_t loop_ticks(uint32_t i) { return (uint16_t)(i < 5u ? LOOP_TICKS[i] : i < 8u ? bar_ticks() << (i - 5u) : 0u); }
static const char *loop_name(uint16_t ticks)
{
    static char b[12];
    switch (ticks) {
    case 2:   return "1/32T";
    case 3:   return "1/32";
    case 4:   return "1/16T";
    case 6:   return "1/16";
    case 8:   return "1/8T";
    case 12:  return "1/8";
    case 16:  return "1/4T";
    case 24:  return "1/4";
    case 48:  return "1/2";
    default: {
        char *p = b;
        p = put_u(p, ticks / bar_ticks());              /* (0.25: the metre's bar) */
        p = put_s(p, ticks >= 2u * bar_ticks() ? " BARS" : " BAR");
        finish(p);
        return b;
    }
    }
}

static uint8_t repeat_now(void)                  /* a REPEAT is held (for the screen and the grid) */
{
    uint32_t i;
    for (i = 0; i < LP_SRCS; i++)
        if ((lp_held & (1u << i)) && (uint32_t)(fm1_ms - lp_t[i]) >= SQ_REPEAT_MS) return 1u;
    return 0u;
}

static void loop_off(void)                        /* 0.10: the tracks land where they would be without the loop (0.3 went on from the loop) */
{
    uint16_t m = loop_mask;
    uint32_t t;
    loop_on = 0u; loop_latched = 0u; lp_held = 0u;
    for (t = 0; t < SQ_TRACKS; t++) if (m & (1u << t)) track_realign(t);
    ui_dirty = grid_dirty = 1u;
}

/* 0.10: EXIT ends the DJ loop, or else the loop between two steps of the selected track (its length comes back) */
static void loop_exit(void)
{
    if (loop_on) { loop_off(); status_msg("LOOP OFF: IN TIME"); return; }
    if (sl_on & (1u << selected_track)) {
        sq_track_cfg_t *c = &project.track[selected_track];
        c->start = sl_prev_start[selected_track];
        c->length = sl_prev_len[selected_track] ? sl_prev_len[selected_track] : 16u;
        if (c->start >= c->length) c->start = 0u;
        sl_on &= (uint16_t)~(1u << selected_track);
        realign_pend |= (uint16_t)(1u << selected_track);
        if (!playing) track_realign(selected_track);
        status_msg("STEP LOOP OFF");
        ui_dirty = grid_dirty = 1u;
        return;
    }
    status_msg("NO LOOP");
}

static void repeat_end(void)                      /* the tracks land where they would be without the loop */
{
    if (!loop_on) return;
    loop_off();
    status_msg("REPEAT OFF: IN TIME");
}

static void loop_press(uint16_t ticks, uint8_t src, uint16_t mask)
{
    uint32_t t;
    if (src >= LP_SRCS) return;
    if (!playing) { status_msg("PLAY FIRST"); return; }
    if (!mask) mask = 0xFFFFu;
    if (loop_on && loop_latched && !lp_held && loop_len == ticks) { loop_exit(); return; }    /* the same again: off */
    if (!loop_on) {                                /* the loop starts here: remember where every track is */
        loop_t0 = global_clock;
        loop_mask = mask;
        for (t = 0; t < SQ_TRACKS; t++) loop_snap[t] = tr[t];
        loop_on = 1u;
        loop_latched = 0u;
    } else if (mask & ~loop_mask) {                /* more tracks join: they come back to where they are now */
        for (t = 0; t < SQ_TRACKS; t++)
            if ((mask & ~loop_mask) & (1u << t)) loop_snap[t] = tr[t];
        loop_mask |= mask;
    }
    if (ticks != loop_len && (global_clock - loop_t0) >= ticks) {   /* shorter, already past its end: from its start, now */
        loop_restore();
        loop_t0 = global_clock;
    }
    loop_len = ticks;
    lp_held |= 1u << src;
    lp_t[src] = fm1_ms;
    status_msg(loop_name(ticks));
    ui_dirty = grid_dirty = 1u;
}

static void loop_release(uint8_t src)
{
    uint32_t bit = 1u << src;
    if (src >= LP_SRCS || !(lp_held & bit)) return;
    lp_held &= ~bit;
    if (!loop_on) return;
    if ((uint32_t)(fm1_ms - lp_t[src]) < SQ_REPEAT_MS) {          /* a tap: the LOOP stays */
        loop_latched = 1u;
        latched_len = loop_len;
        ui_dirty = grid_dirty = 1u;
        return;
    }
    if (lp_held) return;                           /* another one still holds it */
    if (loop_latched) {                            /* a REPEAT over a LOOP: the LOOP goes on at its length */
        if (loop_len != latched_len && (global_clock - loop_t0) >= latched_len) { loop_restore(); loop_t0 = global_clock; }
        loop_len = latched_len;
        status_msg(loop_name(loop_len));
        ui_dirty = grid_dirty = 1u;
        return;
    }
    repeat_end();
}

static void loop_release_all(uint32_t mask)       /* sources whose key-up will not come (a view changed, the grid left) */
{
    uint32_t i;
    for (i = 0; i < LP_SRCS; i++) if ((lp_held & mask) & (1u << i)) loop_release((uint8_t)i);
}

/* ---- 0.5.1: RETRIG, RESTART, STOP at the end of the bar */
static void track_retrig(uint8_t t)              /* the track starts its loop again at its next step */
{
    if (t >= SQ_TRACKS) return;
    if (!playing) { status_msg("PLAY FIRST"); return; }
    retrig_mask |= (uint16_t)(1u << t);
    status_num("RETRIG T", (uint32_t)t + 1u);
    grid_dirty = 1u;
}

static void restart_all(void)                    /* every track from its first step, at the QUANTISE moment */
{
    if (!playing) { status_msg("PLAY FIRST"); return; }
    if (project.live.quant == SQ_Q_NOW) { retrig_mask = 0xFFFFu; status_msg("RESTART"); return; }
    restart_pend ^= 1u;
    status_msg(restart_pend ? "RESTART AT THE QUANTISE" : "RESTART CANCELLED");
    ui_dirty = grid_dirty = 1u;
}

static void stop_bar_toggle(void)
{
    if (!playing) return;
    stop_at_bar ^= 1u;
    status_msg(stop_at_bar ? "STOP AT THE END OF THE BAR" : "STOP CANCELLED");
    ui_dirty = grid_dirty = 1u;
}

/* ---- editing helpers (the panel and the grid share them) */

/* a step that becomes active for the first time takes the track's pen note (what you entered last) */
static void step_activate(uint32_t t, sq_step_t *s)
{
    regia_touched((uint8_t)t);                          /* 0.9: changed by hand */
    s->flags |= SQ_STEP_ON;
    if (!(s->flags & SQ_STEP_SET)) {
        s->note[0] = PEN(t);
        s->flags |= SQ_STEP_SET;
    }
}

static void select_track(uint8_t t)
{
    if (t >= SQ_TRACKS) return;                        /* (0.28: twelve tracks; a key or a pad of 13-16 does nothing) */
    selected_track = t;
    page = (uint8_t)(tr[t].step / 16u);
    cursor_step = (uint8_t)(page * 16u);
    srec_next = 0u;
    chord_entry_ms = fm1_ms - 1000u;
    ui_dirty = grid_dirty = 1u;
}

static void cursor_to(uint8_t stn)
{
    cursor_step = stn > 63u ? 63u : stn;
    page = cursor_step / 16u;
    srec_next = 0u;                    /* step recording goes on from here */
    chord_entry_ms = fm1_ms - 1000u;   /* (a note entered next is a new one, not a chord with the step before) */
    ui_dirty = grid_dirty = 1u;
}

static void queue_pattern(uint8_t t, uint8_t p)
{
    if (p >= SQ_PATTERNS || t >= SQ_TRACKS) return;
    if (!playing || project.live.quant == SQ_Q_NOW) {          /* QUANTISE NOW: at once, where the track is */
        tr[t].pattern = p;
        tr[t].pending_pattern = SQ_NO_PENDING;
        pre[t].state = 0u;
        vg_pattern_in(t);                                      /* 0.17 */
    } else tr[t].pending_pattern = p != tr[t].pattern ? p : SQ_NO_PENDING;
    ui_dirty = grid_dirty = 1u;
}

/* solo: the tracks that go silent stop their notes now; the others play on (0.3 stopped every note) */
/* 0.28: the other bank of the tracks (1-8, 9-12): the same place in it, or its last track */
static uint8_t track_other_bank(uint8_t t)
{
    uint8_t n = (uint8_t)(t ^ 8u);
    return n < SQ_TRACKS ? n : (uint8_t)(SQ_TRACKS - 1u);
}

static void toggle_solo(uint8_t t)
{
    uint32_t k;
    uint16_t before = 0u;
    if (t >= SQ_TRACKS) return;
    for (k = 0; k < SQ_TRACKS; k++) if (track_audible(k)) before |= (uint16_t)(1u << k);
    solo_mask ^= (uint16_t)(1u << t);
    for (k = 0; k < SQ_TRACKS; k++)
        if ((before & (1u << k)) && !track_audible(k)) { track_hard_off(k); pre[k].state = 0u; }
    ui_dirty = grid_dirty = 1u;
}

/* a mute: at once, or (MUTE QUEUE on, while playing) at the next quantised moment, the bar on AUTO; pressed again
 * before then, it is taken back */
static void toggle_mute(uint8_t t)
{
    if (t >= SQ_TRACKS) return;
    if (playing && project.live.mute_q && project.live.quant != SQ_Q_NOW) pending_mute ^= (uint16_t)(1u << t);
    else { mute_mask ^= (uint16_t)(1u << t); vg_state_sync(t); }
    ui_dirty = grid_dirty = 1u;
}

/* 0.11: a new direction, and the track where the bar says it is going that way (FWD -> REV -> FWD lands where it would
 * have been; the explorer found it a step or two off). RANDOM has no place to be. */
static void direction_set(uint32_t t, uint8_t d)
{
    if (d >= SQ_DIR_COUNT || d == project.track[t].direction) return;
    project.track[t].direction = d;
    if (playing && d != SQ_DIR_RANDOM) track_realign(t);
}
static void set_direction(uint8_t d)
{
    if (d >= SQ_DIR_COUNT) return;
    direction_set(selected_track, d);
    status_msg(dir_name(d));
}

static void chord_set(uint8_t mode, uint8_t octs)
{
    sq_track_cfg_t *c = &project.track[selected_track];
    char *p = msg_buf;
    if (mode >= SQ_CHORD_COUNT) mode = SQ_CHORD_BLOCK;
    if (octs < 1u) octs = 1u;
    if (octs > 3u) octs = 3u;
    c->chord_mode = SQ_CHORD_PACK(mode, octs);
    p = put_s(p, mode == SQ_CHORD_BLOCK ? "" : "ARP ");
    p = put_s(p, chord_name(mode));
    if (mode != SQ_CHORD_BLOCK) { p = put_s(p, " X"); p = put_u(p, octs); }
    finish(p);
    status_msg(msg_buf);
}

/* 0.10 PERF + OCT: the track an octave up or down, at once (the notes to come) */
static void track_octave(uint8_t t, int32_t d)
{
    sq_track_cfg_t *c = &project.track[t];
    char *p = msg_buf;
    if (track_drum(t)) { status_msg("A DRUM TRACK HAS NO OCTAVE"); return; }
    c->octave = (int8_t)clamp_i32((int32_t)c->octave + d, -3, 3);
    p = put_s(p, "T"); p = put_u(p, (uint32_t)t + 1u); p = put_s(p, " OCTAVE "); p = put_i(p, c->octave); finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}

static void set_swing(uint8_t v)
{
    project.track[selected_track].swing = (uint8_t)clamp_i32(v, SQ_SWING_MIN, SQ_SWING_MAX);
    status_num("SWING ", project.track[selected_track].swing);
}

static void set_bpm_to(int32_t bpm)
{
    if (project.clock_mode != SQ_CLOCK_MASTER) { status_msg("EXTERNAL CLOCK"); return; }
    project.bpm = (uint16_t)clamp_i32(bpm, 30, 300);
    knob_live = 0u;                    /* the knob has to be moved before it takes the tempo back */
    knob_ref = fm1_knob;
    ui_dirty = 1u;
}
static void set_bpm(int32_t d) { set_bpm_to((int32_t)project.bpm + d); }

/* 0.10: a track whose loop changed is put back in line at the next tick (stopped: now) */
static void track_changed(uint8_t t)
{
    if (playing) realign_pend |= (uint16_t)(1u << t); else track_realign(t);
    ui_dirty = grid_dirty = 1u;
}
static void set_division(uint8_t t, uint8_t div)
{
    if (div >= SQ_DIV_COUNT) return;
    project.track[t].division = div;
    tr[t].div_accum = (uint16_t)(tr[t].div_accum % sq_div_ticks(div));   /* no burst of steps after a shorter division */
    tup_wait &= (uint16_t)~(1u << t);
    track_changed(t);
}

/* the loop of a track: steps first..last (0-based, inclusive). 0.10: the length it had comes back with EXIT. */
static void set_loop(uint8_t t, uint8_t first, uint8_t last)
{
    sq_track_cfg_t *c = &project.track[t];
    if (first > last) { uint8_t x = first; first = last; last = x; }
    if (last > 63u) last = 63u;
    if (!(sl_on & (1u << t))) { sl_prev_start[t] = c->start; sl_prev_len[t] = c->length; sl_on |= (uint16_t)(1u << t); }
    c->start = first;
    c->length = (uint8_t)(last + 1u);
    if (tr[t].step < first || tr[t].step > last) tr[t].step = first;
    track_changed(t);
}

/* 0.11: the length of a track changes IN TIME. While it plays, the new length waits for the bar line (len_pend), then
 * the track is realigned from its anchor: it lands where the clock says, never out of phase - 0.24: on the bar line
 * itself (seq_clock_tick). 0.24: every pattern of the track fits the new length (track_fit): what the track has more
 * is the pattern again, from the pattern's own steps, whatever lengths came before (0.11 repeated "the length when
 * the knob began to turn", in the pattern that played only: 16, 19 at a bar, then 32 repeated the nineteen). */
static uint8_t len_pend[SQ_TRACKS];        /* the length that waits for the bar (0: none) */
static uint8_t len_shown(uint8_t t) { return len_pend[t] ? len_pend[t] : project.track[t].length; }
static uint8_t length_apply(uint8_t t, uint8_t len)      /* returns the copies in the pattern that plays */
{
    sq_track_cfg_t *c = &project.track[t];
    uint8_t old = c->length, st = c->start, n;
    uint32_t pat;
    len = (uint8_t)clamp_i32(len, 1, 64);
    if (sl_on & (1u << t))                                               /* (a length set by hand is not a step loop: its loop is the track's, */
        for (pat = 0; pat < SQ_PATTERNS; pat++) sq_row_keep(project.step[t][pat]);   /*  the steps as they are) */
    sl_on &= (uint16_t)~(1u << t);
    c->length = len;
    if (c->start >= c->length) c->start = (uint8_t)(c->length - 1u);
    n = track_fit(t, old, st, 255u);
    track_changed(t);
    return n;
}
/* what the screen says of a length: "LENGTH 32: THE 16 STEPS REPEAT" when the pattern goes round in it */
static void length_say(uint8_t t, uint8_t copies, const char *tail)
{
    const sq_track_cfg_t *c = &project.track[t];
    char *p = msg_buf;
    p = put_s(p, "LENGTH "); p = put_u(p, c->length);
    if (copies && copies < c->length) { p = put_s(p, ": THE "); p = put_u(p, (uint32_t)c->length - copies - c->start); p = put_s(p, " STEPS REPEAT"); }
    p = put_s(p, tail);
    finish(p);
    status_msg(msg_buf);
}
static void set_length(uint8_t t, uint8_t len)
{
    if (t >= SQ_TRACKS) return;
    len = (uint8_t)clamp_i32(len, 1, 64);
    if (!playing || track_tape(t)) { len_pend[t] = 0u; length_say(t, length_apply(t, len), ""); }
    else {
        char *p = msg_buf;
        len_pend[t] = len == project.track[t].length ? 0u : len;
        p = put_s(p, "LENGTH "); p = put_u(p, len); p = put_s(p, len_pend[t] ? " AT THE BAR" : ""); finish(p);
        status_msg(msg_buf);
    }
    ui_dirty = grid_dirty = 1u;
}
/* 0.25: LONGER / SHORTER asked from the tablet (channel 12 CC 61 / 60): every track twice / half as long, as the MOSSE's
 * moves do (vg_lengths) - but at the next BAR, as a length turned on the tablet is, not at the phrase's end; stopped: at
 * once. The opposite asked while one waits takes it back. */
static void vg_lengths(int32_t dir);              /* sagga_viaggio.c */
static void lengths_ask(int32_t dir)
{
    if (!playing) { lens_pend = 0; vg_lengths(dir); return; }
    if (lens_pend && (lens_pend > 0) != (dir > 0)) {
        status_msg(lens_pend > 0 ? "CANCELLED: LONGER" : "CANCELLED: SHORTER");
        lens_pend = 0;
        return;
    }
    lens_pend = (int8_t)(dir > 0 ? 1 : -1);
    status_msg(dir > 0 ? "LONGER AT THE BAR" : "SHORTER AT THE BAR");
}
static void length_bar_tick(void)                 /* every bar line: the lengths that waited */
{
    uint32_t t;
    if (lens_pend) { int32_t d = lens_pend; lens_pend = 0; vg_lengths(d); }
    for (t = 0; t < SQ_TRACKS; t++)
        if (len_pend[t]) {
            uint8_t l = len_pend[t], n;
            len_pend[t] = 0u;
            n = length_apply((uint8_t)t, l);
            if (t == selected_track) length_say((uint8_t)t, n, "");
        }
}
/* 0.25 THE METRE CHANGES. The bar is `steps` 16ths from this tick on - a bar line when it plays (metre_bar_tick: the
 * old bar's line it waited for; the bars go on being counted) - with these beats. The tracks that were a number of
 * bars long are that number of the new bars (as many as fit 64 steps): their patterns are cut by the loop, whole after
 * it, or go round again in the steps the track has more - nothing is rewritten, and the old bar gives them back. A
 * track of any other length (the player's polymetre) stays. While it plays every track begins again on the line: a
 * new metre is counted from its first bar. */
static void metre_say(uint8_t follow, const char *tail)
{
    char sig[8], spl[SQ_SPLIT_TEXT], *p = msg_buf;
    uint8_t steps = sq_bar_steps(&project.gen);
    uint32_t beats = sq_bar_beats(&project.gen);
    sq_metre_sig(steps, beats, sig); sq_metre_split(steps, beats, spl);
    p = put_s(p, "BAR "); p = put_u(p, steps); p = put_s(p, ": "); p = put_s(p, sig);
    if (spl[1]) { p = put_s(p, " "); p = put_s(p, spl); }
    if (follow) { p = put_s(p, ", "); p = put_u(p, follow); p = put_s(p, follow == 1u ? " TRACK FOLLOWS" : " TRACKS FOLLOW"); }
    p = put_s(p, tail);
    finish(p);
    status_msg(msg_buf);
}
static uint8_t metre_put(uint8_t steps, uint32_t beats)   /* the bar, and the tracks that are a number of bars long -> how many of them followed */
{
    uint8_t old = bar_st(), n = 0u;
    uint32_t t;
    sq_bar_set(&project.gen, steps, beats);
    metre_sync();
    steps = bar_st();
    for (t = 0; t < SQ_TRACKS && steps != old; t++) {
        const sq_track_cfg_t *c = &project.track[t];
        uint8_t want = track_tape(t) ? 0u : sq_metre_follow(c->length, c->start, old, steps);
        if (!want) continue;
        len_pend[t] = 0u;
        length_apply((uint8_t)t, want);
        n++;
    }
    return n;
}
static void metre_apply(uint8_t steps, uint32_t beats)
{
    uint8_t n;
    uint32_t t;
    bar_pend_steps = 0u;
    bar_base = bar_no();                               /* (the bars so far, counted in the old bar) */
    bar_origin = global_clock;
    n = metre_put(steps, beats);
    if (playing) {
        loop_on = 0u; loop_latched = 0u; lp_held = 0u;
        for (t = 0; t < SQ_TRACKS; t++) track_restart(t);
    }
    metre_say(n, "");
    ui_dirty = grid_dirty = 1u;
}
static uint8_t bar_shown(void) { return bar_pend_steps ? bar_pend_steps : sq_bar_steps(&project.gen); }
static uint32_t beats_shown(void) { return bar_pend_steps ? bar_pend_beats : sq_bar_beats(&project.gen); }
static void metre_ask(uint8_t steps, uint32_t beats)   /* the knobs, the tablet: at once when stopped, else at the bar line */
{
    if (steps < SQ_BAR_MIN || steps > SQ_BAR_MAX) steps = 16u;
    beats = sq_metre_fix(steps, beats);
    if (!playing) { metre_apply(steps, beats); return; }
    if (steps == sq_bar_steps(&project.gen) && beats == sq_bar_beats(&project.gen)) {
        bar_pend_steps = 0u;
        metre_say(0u, "");
        return;
    }
    bar_pend_steps = steps; bar_pend_beats = beats;
    {
        char sig[8], spl[SQ_SPLIT_TEXT], *p = msg_buf;
        sq_metre_sig(steps, beats, sig); sq_metre_split(steps, beats, spl);
        p = put_s(p, "BAR "); p = put_u(p, steps); p = put_s(p, ": "); p = put_s(p, sig);
        if (spl[1]) { p = put_s(p, " "); p = put_s(p, spl); }
        p = put_s(p, " AT THE BAR"); finish(p);
        status_msg(msg_buf);
    }
    ui_dirty = 1u;
}
static void metre_bar_tick(void)                       /* every bar line: the bar that waited */
{
    if (bar_pend_steps) metre_apply(bar_pend_steps, bar_pend_beats);
}
/* 0.26 THE METRE WITH THE SCENE (GLO 4 K3: SCENE METRE). A scene stored while it is on keeps the metre it was stored
 * in (capture_scene), and brings it back when it comes: at once when nothing plays; on the bar line it comes at (a
 * scene queued for the bar, an entry of the song) from that very bar; one that comes in the middle of a bar (QUANTISE
 * NOW or BEAT, a pad of the grid) at the bar's end - the metre never begins in the middle of a bar. So a song changes
 * metre with its scenes. Off (as every project until 0.25): a scene leaves the metre alone, and stores none. */
static void scene_metre_bring(uint8_t s)
{
    uint8_t st = 16u, id;
    uint32_t bt = SQ_BEATS_44;
    if (s >= SQ_SCENES || !project.ext.scene_metre_on) return;
    id = project.ext.scene_metre[s];
    if (!id || !sq_metre_of((uint8_t)(id - 1u), &st, &bt)) return;
    if (st == sq_bar_steps(&project.gen) && bt == sq_bar_beats(&project.gen)) { bar_pend_steps = 0u; return; }   /* (it is the bar already: none waits) */
    if (!playing || bar_into() == 0u) metre_apply(st, bt);
    else metre_ask(st, bt);
}
static uint8_t scene_metre_now(void)                   /* what a scene stored now keeps: the metre shown (the one that waits for the bar, if one does) */
{
    uint8_t id;
    if (!project.ext.scene_metre_on) return 0u;
    id = sq_metre_id(bar_shown(), beats_shown());
    return (uint8_t)(id == 255u ? 0u : id + 1u);       /* (a bar divided from outside has no number: the scene leaves the metre) */
}
static void scene_metre_toggle(uint8_t on)
{
    project.ext.scene_metre_on = on ? 1u : 0u;
    status_msg(on ? "SCENES BRING THEIR METRE (STORE THEM IN IT)" : "SCENES LEAVE THE METRE ALONE");
    ui_dirty = 1u;
}

/* a pattern came from the library (or a snapshot, a scene) with a loop of its own: no length waits any more, the
 * track goes where the clock says it is (not back to its first step at some odd moment) */
static void track_loaded(uint8_t t)
{
    len_pend[t] = 0u;
    track_changed(t);
}

static void set_loop_start(uint8_t t, uint8_t st)
{
    sq_track_cfg_t *c = &project.track[t];
    uint8_t was = c->start;
    c->start = st >= c->length ? (uint8_t)(c->length - 1u) : st;
    if (c->start != was) track_fit(t, c->length, was, 255u);   /* 0.24: the loop begins elsewhere: the copies of its patterns are steps */
    track_changed(t);
}

/* ---- the key (scale, root, shift): see key_note() */
static uint8_t bake_ask;
static uint32_t bake_until;

static void key_toast(void)
{
    char *p = msg_buf;
    key_sync_slot();                                    /* 0.10: whoever changed key_root / scale / shift, the slot has it */
    p = put_s(p, "KEY "); p = put_u(p, (uint32_t)project.key_cur + 1u); p = put_s(p, ": "); p = put_s(p, sq_root_name(project.key_root)); p = put_s(p, " "); p = put_s(p, sq_scale_name(project.key_scale));
    if (project.key_shift) { p = put_s(p, " "); p = put_i(p, project.key_shift); }
    finish(p);
    status_msg(msg_buf);
    grid_dirty = 1u;
}
static void set_key_root(int32_t d) { project.key_root = (uint8_t)(((int32_t)project.key_root + d % 12 + 12) % 12); key_sync_slot(); key_toast(); }
static void set_key_scale(int32_t d) { project.key_scale = change_u8(project.key_scale, d, 0u, SQ_SCALES - 1u); key_sync_slot(); key_toast(); }
static void set_key_shift(int32_t d) { project.key_shift = (int8_t)clamp_i32((int32_t)project.key_shift + d, -24, 24); key_sync_slot(); key_toast(); }
/* 0.10: HOME 3 K1: the key slot that plays (its key comes with it) */
static void set_key_slot(int32_t d)
{
    key_select_slot(change_u8(project.key_cur, d, 0u, SQ_KEYS - 1u));
    { char *p = msg_buf; p = put_s(p, "KEY SLOT "); p = put_u(p, (uint32_t)project.key_cur + 1u); p = put_s(p, ": ");
      p = put_s(p, sq_root_name(project.key_root)); p = put_s(p, " "); p = put_s(p, sq_scale_name(project.key_scale)); finish(p); status_msg(msg_buf); }
}
/* BAKE: the notes that sound become the notes that are written. Asks twice: it cannot be undone. */
static void key_bake(void)
{
    if (bake_ask && !time_due(fm1_ms, bake_until)) {
        uint32_t n = sq_project_bake_scale(&project);
        bake_ask = 0u;
        status_num("KEY BAKED, CHANGED ", n);
        ui_dirty = grid_dirty = 1u;
    } else {
        bake_ask = 1u;
        bake_until = fm1_ms + 3000u;
        status_msg("BAKE THE KEY INTO THE PATTERNS? AGAIN");
    }
}

/* 0.10 FX + ARP: BAKE the macros. What they add is written down: INTENSITY into the velocities of the steps that are on,
 * GATE into their gates (the percent ones), SWING into every track's swing, FILTER into the base of lane 1 of every track
 * that has one; then the four macros are 0 and the music is the same. Asks twice (the patterns: UNDO has them). */
static uint8_t mbake_ask;
static uint32_t mbake_until;
static void macros_bake(void)
{
    uint32_t t, pat, i, n = 0u;
    if (!(mbake_ask && !time_due(fm1_ms, mbake_until))) {
        if (!mac_vel && !mac_gate && !mac_swing && !mac_filt) { status_msg("MACROS ARE 0: NOTHING TO BAKE"); return; }
        mbake_ask = 1u; mbake_until = fm1_ms + 3000u;
        status_msg("BAKE THE MACROS INTO THE PATTERNS? AGAIN");
        return;
    }
    mbake_ask = 0u;
    undo_begin();
    for (t = 0; t < SQ_TRACKS; t++) {
        sq_track_cfg_t *c = &project.track[t];
        if (mac_vel || mac_gate) {
            for (pat = 0; pat < SQ_PATTERNS; pat++) {
                sq_step_t *row = project.step[t][pat];
                uint8_t touched = 0u;
                for (i = 0; i < SQ_STEPS; i++) {
                    sq_step_t *s = &row[i];
                    if (!(s->flags & SQ_STEP_ON)) continue;
                    if (mac_vel) s->velocity = (uint8_t)clamp_i32((int32_t)s->velocity + mac_vel, 1, 127);
                    if (mac_gate && s->length <= 100u) s->length = (uint8_t)clamp_i32(((int32_t)s->length * (100 + mac_gate)) / 100, 1, 100);
                    touched = 1u;
                }
                if (touched) { undo_add((uint8_t)t, (uint8_t)pat); n++; }
            }
        }
        if (mac_swing) c->swing = (uint8_t)clamp_i32((int32_t)c->swing + mac_swing, (int32_t)SQ_SWING_MIN, (int32_t)SQ_SWING_MAX);
        if (mac_filt && c->lane_base[0] != SQ_LANE_NONE) c->lane_base[0] = (uint8_t)clamp_i32((int32_t)c->lane_base[0] + mac_filt, 0, 127);
    }
    mac_vel = mac_gate = mac_swing = 0;
    if (mac_filt) { mac_filt = 0; filt_dirty = 1u; filt_t = 0u; }
    if (project.live.master_fn == SQ_MK_FILTER) { knob_live = 0u; knob_ref = fm1_knob; }
    status_num("MACROS BAKED, PATTERNS ", n);
    ui_dirty = grid_dirty = 1u;
}

/* ---- 0.5.1: TRANSPOSE the key (PERF + K3, the grid's FX view row 3, the remote). The root and the shift move together,
 * so every track IN KEY plays its music in the new key, exactly (FREE and DRUM tracks stay where they are). It waits for
 * the QUANTISE moment like a scene (stopped, or QUANTISE NOW: at once). project.live.ktrans says how far it has gone. */
static uint8_t any_in_key(void)
{
    uint32_t t;
    for (t = 0; t < SQ_TRACKS; t++) if (track_in_key(t)) return 1u;
    return 0u;
}
static void ktrans_apply(int32_t target)
{
    int32_t d;
    char *p = msg_buf;
    target = clamp_i32(target, -SQ_KTRANS_MAX, SQ_KTRANS_MAX);
    d = target - project.live.ktrans;
    project.key_root = (uint8_t)(((int32_t)project.key_root + d % 12 + 12) % 12);
    project.key_shift = (int8_t)clamp_i32((int32_t)project.key_shift + d, -24, 24);
    key_sync_slot();
    project.live.ktrans = (int8_t)target;
    ktrans_pend = SQ_KT_NONE;
    p = put_s(p, "TRANSPOSE "); p = put_i(p, target); p = put_s(p, ": "); p = put_s(p, sq_root_name(project.key_root));
    p = put_s(p, " "); p = put_s(p, sq_scale_name(project.key_scale)); finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}
static int32_t ktrans_target(void) { return ktrans_pend != SQ_KT_NONE ? ktrans_pend : project.live.ktrans; }
static void ktrans_set(int32_t target)
{
    char *p = msg_buf;
    target = clamp_i32(target, -SQ_KTRANS_MAX, SQ_KTRANS_MAX);
    if (!any_in_key()) status_msg("NO TRACK IN KEY: HOME PAGE 3, K4");
    if (!playing || project.live.quant == SQ_Q_NOW) { ktrans_apply(target); return; }
    ktrans_pend = target == project.live.ktrans ? (int8_t)SQ_KT_NONE : (int8_t)target;
    if (!any_in_key()) return;
    p = put_s(p, "TRANSPOSE "); p = put_i(p, target); p = put_s(p, " QUEUED"); finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}

/* ---- 0.5.1: the macros, FX + K1..K4 (also the remote, and FILTER on the MASTER knob). They act on every track while
 * they are away from 0; FX + OCT- puts them all back to 0. They are not saved. */
static int32_t macro_put(uint8_t i, int32_t v)     /* (0.13: MOTION plays them back through here, without a word) */
{
    switch (i) {
    case 0:  mac_vel = (int8_t)clamp_i32(v, -63, 63); return mac_vel;
    case 1:  mac_gate = (int8_t)clamp_i32(v, -90, 100); return mac_gate;
    case 2:  mac_swing = (int8_t)clamp_i32(v, -25, 25); return mac_swing;
    default: if ((int8_t)clamp_i32(v, -64, 63) != mac_filt) { mac_filt = (int8_t)clamp_i32(v, -64, 63); filt_dirty = 1u; filt_t = 0u; }
             return mac_filt;
    }
}
static void mot_touch(uint8_t i);                 /* sagga_live3.c: 0.13 MOTION, the hand moved macro i */
static void macro_set(uint8_t i, int32_t v)
{
    static const char *const NAME[4] = {"INTENSITY ", "GATE ", "SWING ", "FILTER "};
    char *p = msg_buf;
    v = macro_put(i, v);
    mot_touch(i);
    p = put_s(p, NAME[i & 3u]); p = put_i(p, v); if (i == 1u) p = put_s(p, "%"); finish(p);
    status_msg(msg_buf);
    ui_dirty = 1u;
}
static uint8_t mot_any(void);                     /* sagga_live3.c */
static void mot_clear(void);
static void macros_zero(void)
{
    mac_vel = mac_gate = mac_swing = 0;
    if (mac_filt) { mac_filt = 0; filt_dirty = 1u; filt_t = 0u; }
    if (project.live.master_fn == SQ_MK_FILTER) { knob_live = 0u; knob_ref = fm1_knob; }   /* (the knob must move before it takes over again) */
    if (mot_any()) { mot_clear(); status_msg("MACROS 0, THE MOTION WIPED"); ui_dirty = grid_dirty = 1u; return; }   /* 0.13 */
    status_msg("MACROS 0");
    ui_dirty = grid_dirty = 1u;
}
/* 0.10 FX + OCT+ again: off, and the repeats that have not started yet go too */
static void echo_global_set(uint8_t on)
{
    uint32_t i;
    echo_global = on ? 1u : 0u;
    if (!on) for (i = 0; i < SQ_DEFER_MAX; i++) if (defer_note[i].state == 1u && defer_note[i].glob) defer_note[i].state = 0u;
    status_msg(on ? "ECHO ALL ON (FX+OCT+ AGAIN: OFF)" : "ECHO ALL OFF");
    ui_dirty = grid_dirty = 1u;
}
/* the FILTER macro moved: lane 1 of every track goes out again with it (a lane locked on the step playing gets it when
 * the lock ends); a few tracks a pass, as the USB has room */
static void filt_service(void)
{
    if (!filt_dirty) return;
    while (filt_t < SQ_TRACKS) {
        const sq_track_cfg_t *c = &project.track[filt_t];
        if (c->lane_cc[0] != SQ_LANE_NONE && c->lane_base[0] != SQ_LANE_NONE && !(ev[filt_t].lane_locked & 1u)) {
            if (midi_tx_room() <= 28u) return;
            send_cc(track_ch(filt_t), c->lane_cc[0], lane_val(0u, c->lane_base[0]));
        }
        filt_t++;
    }
    filt_dirty = 0u;
}

/* ---- 0.8: the MIDI effects of a track (HOME page 6). 0.16: an effect is set up before it plays, as the algorithms.
 * 0.19: a CHAIN - the four can play together, always in the order VEL CURVE, OCTAVE, HARM, ECHO (project.ext.mfxc,
 * saved with the project: each effect keeps its values). K1 shows one of them. Not playing, it is READY: K2-K4 set
 * it up, SEQ + white 6 adds it to the chain (the key that starts EUCLID and the algorithms: with K1 just turned it acts
 * on the MIDI FX). Playing: K2-K4 change it live, and SEQ + white 6 right after K1 found it (no K2-K4 in between) takes
 * it out. K1 on OFF: SEQ + white 6 stops them all. The track's mfx .. mfx_fb are its chain's first (sq_mfx_mirror). */
static uint8_t mfx_sel[SQ_TRACKS];              /* the effect K1 shows (SQ_MFX_*, OFF) */
static uint8_t mfx_pend[SQ_TRACKS];             /* 1: SEQ + white 6 acts on the effect shown (K1 just chose it) */
static sq_track_cfg_t mfx_tmp;                  /* the shown effect's values, as the knobs, the screen and the grid see them */
static uint8_t mfx_on(uint32_t t, uint8_t fx) { return sq_mfx_is_on(&project.ext, t, fx); }
static uint8_t mfx_count(uint32_t t) { return sq_mfx_count(&project.ext, t); }
static void mfx_load(uint32_t t, uint8_t fx, sq_track_cfg_t *o)
{
    int8_t a; uint8_t tm, fb;
    o->mfx = fx < SQ_MFXS ? fx : (uint8_t)SQ_MFX_OFF;
    if (o->mfx) { sq_mfx_get(&project.ext, t, o->mfx, &a, &tm, &fb); o->mfx_amt = a; o->mfx_time = tm; o->mfx_fb = fb; }
    else { o->mfx_amt = 0; o->mfx_time = 6u; o->mfx_fb = 60u; }
}
static void mfx_mirror(uint32_t t) { sq_mfx_mirror(&project.ext.mfxc[t < SQ_TRACKS ? t : 0u], &project.track[t < SQ_TRACKS ? t : 0u]); }
/* the shown effect's values (mfx_tmp, changed by a knob, the grid or the tablet) back into the chain */
static void mfx_keep(uint32_t t, const sq_track_cfg_t *v)
{
    if (v->mfx == SQ_MFX_OFF || v->mfx >= SQ_MFXS || t >= SQ_TRACKS) return;
    sq_mfx_put(&project.ext, t, v->mfx, v->mfx_amt, v->mfx_time, v->mfx_fb);
    mfx_mirror(t);
}
static uint8_t mfx_shown(uint32_t t) { return t < SQ_TRACKS && mfx_sel[t] < SQ_MFXS ? mfx_sel[t] : (uint8_t)SQ_MFX_OFF; }
static sq_track_cfg_t *mfx_view(uint32_t t) { mfx_load(t, mfx_shown(t), &mfx_tmp); return &mfx_tmp; }
static void mfx_sel_reset(void)                 /* a project loaded: K1 shows each track's first effect, nothing READY */
{
    uint32_t t, k;
    for (t = 0; t < SQ_TRACKS; t++) {
        mfx_sel[t] = SQ_MFX_OFF; mfx_pend[t] = 0u;
        for (k = 0; k < SQ_MFX_ALLN; k++) if (mfx_on(t, project.ext.mfxd[t].order[k])) { mfx_sel[t] = project.ext.mfxd[t].order[k]; break; }
    }
}
static const char *const MFX_NAME[SQ_MFXS] = {"OFF", "HARM", "OCTAVE", "ECHO", "VEL CURVE", "CHANCE", "RANDOM", "NOTE FILTER", "GATE", "GLITCH"};
static const char *const MFX_SHORT[SQ_MFXS] = {"OFF", "HARM", "OCT", "ECHO", "VEL", "CHNC", "RND", "FILT", "GATE", "GLIT"};
/* the chain as it plays, in the track's order: "VEL+OCT+HARM+ECHO" (nothing: "OFF"); with `also` (not OFF) that effect
 * too, playing or not, and ">" between them (the order) */
static char *mfx_chain_put2(char *p, uint32_t t, uint8_t also)
{
    uint32_t k, n = 0u;
    for (k = 0; k < SQ_MFX_ALLN; k++) {
        uint8_t fx = project.ext.mfxd[t].order[k];
        if (!mfx_on(t, fx) && fx != also) continue;
        if (n++) p = put_s(p, also ? ">" : "+");
        p = put_s(p, MFX_SHORT[fx]);
    }
    if (!n) p = put_s(p, "OFF");
    return p;
}
static char *mfx_chain_put(char *p, uint32_t t) { return mfx_chain_put2(p, t, SQ_MFX_OFF); }
static void mfx_say(uint32_t t, const char *what, uint8_t fx, const char *tail)
{
    char *p = msg_buf;
    p = put_s(p, "T"); p = put_u(p, t + 1u); p = put_s(p, " MIDI FX "); p = put_s(p, MFX_NAME[fx < SQ_MFXS ? fx : 0u]);
    p = put_s(p, what); if (tail) p = put_s(p, tail); finish(p);
    status_msg(msg_buf);
}
static void mfx_say_chain(uint32_t t, const char *what, uint8_t fx)   /* ... and the chain, when it is more than that one */
{
    char *p = msg_buf;
    p = put_s(p, "T"); p = put_u(p, t + 1u); p = put_s(p, " MIDI FX "); p = put_s(p, MFX_NAME[fx < SQ_MFXS ? fx : 0u]); p = put_s(p, what);
    if (mfx_count(t) > 1u || (mfx_count(t) == 1u && !mfx_on(t, fx))) { p = put_s(p, ": "); p = mfx_chain_put(p, t); }
    finish(p);
    status_msg(msg_buf);
}
static void mfx_choose(uint32_t t, uint8_t fx)
{
    if (t >= SQ_TRACKS) return;
    if (fx >= SQ_MFXS) fx = SQ_MFX_OFF;
    mfx_sel[t] = fx;
    if (fx == SQ_MFX_OFF) {
        char *p = msg_buf;
        mfx_pend[t] = mfx_count(t) ? 1u : 0u;
        p = put_s(p, "T"); p = put_u(p, t + 1u); p = put_s(p, " MIDI FX ");
        if (mfx_count(t)) { p = mfx_chain_put(p, t); p = put_s(p, mfx_count(t) > 1u ? " STOP AT SEQ + WHITE 6" : " STOPS AT SEQ + WHITE 6"); }
        else p = put_s(p, "OFF");
        finish(p);
        status_msg(msg_buf);
    } else if (mfx_on(t, fx)) { mfx_pend[t] = 1u; mfx_say(t, " PLAYS: SEQ + WHITE 6 TAKES IT OUT", fx, 0); }
    else { mfx_pend[t] = 1u; mfx_say(t, " READY: SEQ + WHITE 6", fx, 0); }
    ui_dirty = grid_dirty = 1u;
}
/* SEQ + white 6 with K1 just turned (the tablet's FX GO, the grid's pad tapped again): the effect shown joins the chain
 * with its values, or leaves it; OFF shown: they all stop */
static void mfx_go(uint32_t t)
{
    uint8_t fx = mfx_shown(t);
    if (t >= SQ_TRACKS) return;
    if (fx == SQ_MFX_OFF) {
        if (mfx_count(t)) {
            char *p = msg_buf;
            p = put_s(p, "T"); p = put_u(p, t + 1u); p = put_s(p, " MIDI FX "); p = mfx_chain_put(p, t);
            p = put_s(p, mfx_count(t) > 1u ? " STOP" : " STOPS"); finish(p);
            project.ext.mfxc[t].on = 0u; project.ext.mfxd[t].on = 0u;
            status_msg(msg_buf);
        }
    } else if (mfx_on(t, fx)) { sq_mfx_set_on(&project.ext, t, fx, 0u); mfx_say_chain(t, " STOPS", fx); }
    else { sq_mfx_set_on(&project.ext, t, fx, 1u); mfx_say_chain(t, " STARTS", fx); }
    mfx_pend[t] = 0u;
    mfx_mirror(t);
    ui_dirty = grid_dirty = 1u;
}
/* 0.20: SEL + K1 in HOME 6: the effect shown plays earlier (left) or later (right) in the chain */
static void mfx_order(uint32_t t, int32_t d)
{
    uint8_t fx = mfx_shown(t);
    char *p = msg_buf;
    if (t >= SQ_TRACKS || !d) return;
    if (fx == SQ_MFX_OFF) { status_msg("ORDER: K1 SHOWS AN EFFECT FIRST"); return; }
    sq_mfx_order_move(&project.ext, t, fx, d);
    p = put_s(p, "T"); p = put_u(p, t + 1u); p = put_s(p, " ORDER "); p = mfx_chain_put2(p, t, fx); finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}
/* the grid's pads of TRACK 3 row 2: a tap on one that plays: it stops; on another: READY (orange), again: it starts
 * (OFF, again: they all stop) */
static void mfx_pad(uint32_t t, uint8_t fx)
{
    if (t >= SQ_TRACKS) return;
    if (fx && fx < SQ_MFXS && mfx_on(t, fx)) { mfx_sel[t] = fx; mfx_go(t); }
    else if (fx == mfx_shown(t) && mfx_pend[t]) mfx_go(t);
    else mfx_choose(t, fx);
}
static void mfx_amount(sq_track_cfg_t *c, int32_t d)
{
    int32_t lo, hi, step = (c->mfx == SQ_MFX_CHANCE || c->mfx == SQ_MFX_GLITCH) ? 5 : 1;   /* (the percentages, 5 at a time) */
    sq_mfx_range(c->mfx, 0u, track_in_key(selected_track), &lo, &hi);
    c->mfx_amt = (int8_t)clamp_i32((int32_t)c->mfx_amt + d * step, lo, hi);
}
/* 0.20: K3 and K4 of the effect shown, each its range */
static void mfx_knob34(sq_track_cfg_t *c, uint8_t knob, int32_t d, int32_t f)
{
    int32_t lo, hi;
    sq_mfx_range(c->mfx, knob, track_in_key(selected_track), &lo, &hi);
    if (knob == 1u) c->mfx_time = (uint8_t)kstep(c->mfx_time, d, c->mfx == SQ_MFX_RANDOM || c->mfx == SQ_MFX_FILTER ? f : 1, lo, hi);
    else c->mfx_fb = (uint8_t)kstep(c->mfx_fb, d, (hi - lo) >= 50 ? 5 * f : 1, lo, hi);
    if (c->mfx == SQ_MFX_FILTER && c->mfx_time < (uint8_t)c->mfx_amt) c->mfx_time = (uint8_t)c->mfx_amt;
}

/* ---- the MASTER knob: TEMPO (the default), MORPH or FILTER (SAVE + K1; the grid's PROJ view). It takes over only
 * after you move it, so a loaded project, a changed function or a new scene never jumps. */
static const char *const MK_NAME[SQ_MKS] = {"TEMPO", "MORPH", "FILTER"};
static void morph_set(uint8_t pos);
static void master_fn_set(uint8_t fn)
{
    char *p = msg_buf;
    project.live.master_fn = fn < SQ_MKS ? fn : (uint8_t)SQ_MK_TEMPO;
    knob_live = 0u;
    knob_ref = fm1_knob;
    p = put_s(p, "MASTER KNOB: "); p = put_s(p, MK_NAME[project.live.master_fn]); finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}
static void knob_service(void)
{
    int32_t k = (int32_t)fm1_knob, d = k - (int32_t)knob_ref, v;
    uint8_t fn = project.live.master_fn;
    if (d < 0) d = -d;
    if (fn == SQ_MK_TEMPO && project.clock_mode != SQ_CLOCK_MASTER) { knob_ref = (uint32_t)k; knob_live = 0u; return; }
    if (!knob_live) {
        if (d < 24) return;
        knob_live = 1u;
    } else if (d < 4 && !((k <= 2 || k >= 1021) && d)) return;
    knob_ref = (uint32_t)k;
    k = clamp_i32(k, 0, 1023);
    if (fn == SQ_MK_MORPH) morph_set((uint8_t)((k * 127 + 511) / 1023));
    else if (fn == SQ_MK_FILTER) {
        v = (k * 127 + 511) / 1023 - 64;
        if (v >= -2 && v <= 2) v = 0;                  /* 0.8: a little dead zone in the middle: 0 is easy to find */
        if (v != mac_filt) { mac_filt = (int8_t)clamp_i32(v, -64, 63); filt_dirty = 1u; filt_t = 0u; ui_dirty = 1u; }
    } else {
        uint32_t bpm = 30u + ((uint32_t)k * 270u + 511u) / 1023u;
        if (bpm != project.bpm) { project.bpm = (uint16_t)bpm; ui_dirty = 1u; }
    }
}

/* ---- 0.5.1: the arpeggio. ARP tapped: on / off (back to the mode it had); ARP held + K1 / K2: the mode, the octaves */
static void arp_toggle(void)
{
    sq_track_cfg_t *c = &project.track[selected_track];
    uint8_t m = SQ_CHORD_MODE(c->chord_mode);
    if (m != SQ_CHORD_BLOCK) { arp_last[selected_track] = m; chord_set(SQ_CHORD_BLOCK, SQ_CHORD_OCTS(c->chord_mode)); }
    else chord_set(arp_last[selected_track] && arp_last[selected_track] < SQ_CHORD_COUNT ? arp_last[selected_track] : (uint8_t)SQ_CHORD_ARP_UP,
                   SQ_CHORD_OCTS(c->chord_mode));
    ui_dirty = grid_dirty = 1u;
}

/* A step: EDIT + black 1 LOCK, 2 COPY, 3 PASTE, 4 CLEAR, 5 PLAIN, 6 TIE, 7 SLIDE (0.13). */
static sq_step_t step_clip;
static uint8_t step_clip_ok;


#include "sagga_gen.c"
static uint8_t drum_track_n(uint8_t i);              /* (0.13 NOTE REPEAT, below) */
static int record_note(uint8_t t, uint8_t note, uint8_t vel);
static void rec_close_note(uint8_t src);
#include "sagga_break.c"                              /* 0.12: the slices of a drum break */
#include "sagga_live2.c"                              /* 0.12: TAKE, the THROWS, the step's notes by knob */
#include "sagga_live3.c"                              /* 0.13: KEYBOARD, MIDI IN, MOTION, SLIDE, CHAIN LIST */
#include "sagga_click.c"                              /* 0.26: THE CLICK - the metronome, the count before a recording */
#include "sagga_expr.c"                               /* 0.26: the keyboard's pedal, wheels and aftertouch go where its notes go, and are recorded */

/* EDIT + black 2 / 3 / 4: COPY, PASTE, CLEAR the cursor step (UNDO takes PASTE and CLEAR back); 5 PLAIN, 6 TIE, 7 SLIDE */
static void step_tool(int bi)
{
    uint8_t t = selected_track, pat = tr[t].pattern;
    sq_step_t *s = &project.step[t][pat][cursor_step];
    if (bi == 0) { s->flags ^= SQ_STEP_LOCK; status_msg((s->flags & SQ_STEP_LOCK) ? "STEP LOCKED: EVOLVE/DICE IGNORE IT" : "STEP UNLOCKED"); ui_dirty = grid_dirty = 1u; return; }
    if (bi == 4) { s->flags ^= SQ_STEP_XOFF; status_msg((s->flags & SQ_STEP_XOFF) ? "STEP PLAIN: NO EXPO FROM HERE" : "STEP IN THE CURVE"); ui_dirty = grid_dirty = 1u; return; }   /* 0.10 */
    if (bi == 5) { s->flags = (uint8_t)((s->flags ^ SQ_STEP_TIE) & ~SQ_STEP_SLIDE); status_msg((s->flags & SQ_STEP_TIE) ? "TIE: THE NOTE HOLDS INTO THE NEXT STEP (LEGATO)" : "TIE OFF"); ui_dirty = grid_dirty = 1u; return; }   /* 0.10 */
    if (bi == 6) {                                                         /* 0.13 SLIDE: TIE, and the next note glides */
        if (track_drum(t) || track_break(t)) { status_msg("SLIDE: A MELODIC TRACK'S STEP"); return; }
        s->flags = (uint8_t)((s->flags ^ SQ_STEP_SLIDE) & ~SQ_STEP_TIE);
        status_msg((s->flags & SQ_STEP_SLIDE) ? "SLIDE: GLIDES INTO THE NEXT NOTE (CC 65)" : "SLIDE OFF");
        regia_touched(t);
        ui_dirty = grid_dirty = 1u;
        return;
    }
    if (bi == 1) { step_clip = *s; step_clip_ok = 1u; status_num("STEP COPIED ", (uint32_t)cursor_step + 1u); return; }
    if (bi == 2 && !step_clip_ok) { status_msg("NO STEP COPIED"); return; }
    if (bi != 2 && bi != 3) return;
    undo_begin();
    undo_add(t, pat);
    if (bi == 2) { *s = step_clip; status_num("STEP PASTED ", (uint32_t)cursor_step + 1u); }
    else { sq_step_default(s); status_num("STEP CLEARED ", (uint32_t)cursor_step + 1u); }
    ui_dirty = grid_dirty = 1u;
}

static uint8_t scene_metre_now(void);
static void capture_scene(uint8_t s)
{
    uint32_t t;
    if (s >= SQ_SCENES) return;
    project.scene[s].mute_mask = mute_mask;
    for (t = 0; t < SQ_TRACKS; t++) {
        uint32_t l;
        project.scene[s].pattern[t] = tr[t].pattern;
        for (l = 0; l < SQ_LANES; l++) project.scene[s].lane[t][l] = project.track[t].lane_base[l];   /* for MORPH */
    }
    project.scene[s].key_slot = project.key_cur;                /* 0.10: the scene brings its key back */
    project.ext.scene_metre[s] = scene_metre_now();             /* 0.26: ... and its metre (SCENE METRE off: none) */
    if (project.ext.scene_metre[s]) {
        char sig[8], *p = msg_buf;
        sq_metre_sig(bar_shown(), beats_shown(), sig);
        p = put_s(p, "SCENE STORED "); p = put_u(p, (uint32_t)s + 1u); p = put_s(p, " IN "); p = put_s(p, sig); finish(p);
        status_msg(msg_buf);
    } else status_num("SCENE STORED ", (uint32_t)s + 1u);
}

static void scene_recall(uint8_t s)
{
    if (s >= SQ_SCENES) return;
    scene_cursor = s;
    if (playing && project.live.quant != SQ_Q_NOW) { pending_scene = s; status_num("SCENE QUEUED ", (uint32_t)s + 1u); }
    else apply_scene(s);
    ui_dirty = grid_dirty = 1u;
}

/* REC while playing: where the note belongs. QUANT: the nearest step. FREE: the nearest step, with the timing of the
 * note in its nudge (early or late).
 * REC while stopped: step recording. The note goes on the cursor step and the cursor moves on to the next step of the
 * loop; notes played together (within 80 ms) make a chord on the same step. */
#define SQ_SREC_CHORD_MS 80u
static void rec_open_note(uint8_t src, uint8_t t, uint8_t stp)
{
    rec_open_t *o;
    uint32_t i;
    if (!playing || !ev[t].slot_dur_us) return;
    for (i = 0; i < rec_open_n; i++) if (rec_open[i].src == src) break;     /* the same note again: start over */
    if (i == rec_open_n) {
        if (rec_open_n == REC_OPEN_MAX) { i = 0u; rec_open[0] = rec_open[--rec_open_n]; }   /* full: the oldest goes */
        else rec_open_n++;
    }
    o = &rec_open[i];
    o->on_us = sq_micros(); o->slot_us = ev[t].slot_dur_us;
    o->src = src; o->t = t; o->pat = tr[t].pattern; o->step = stp;
}

static void rec_close_note(uint8_t src)
{
    uint32_t i, dur, steps10;
    for (i = 0; i < rec_open_n; i++) if (rec_open[i].src == src) break;
    if (i == rec_open_n) return;
    {
        rec_open_t o = rec_open[i];
        sq_step_t *s = &project.step[o.t][o.pat][o.step];
        rec_open[i] = rec_open[--rec_open_n];
        if (!(s->flags & SQ_STEP_ON) || !o.slot_us) return;             /* the step went away meanwhile */
        dur = (uint32_t)(sq_micros() - o.on_us);
        if (dur <= o.slot_us) {                                         /* a gate: % of the step, 5 .. 100 */
            uint32_t pct = (dur * 100u + o.slot_us / 2u) / o.slot_us;
            s->length = (uint8_t)(pct < 5u ? 5u : pct > 100u ? 100u : pct);
        } else {
            steps10 = (uint32_t)(((uint64_t)dur * 10u + o.slot_us / 2u) / o.slot_us);   /* tenths of a step */
            if (steps10 < 18u) s->length = 101u;                        /* 1.5 steps */
            else { uint32_t n = (steps10 + 5u) / 10u; s->length = (uint8_t)(100u + (n > 64u ? 64u : n)); }
        }
        grid_dirty = ui_dirty = 1u;
    }
}

static int record_note(uint8_t t, uint8_t note, uint8_t vel)   /* the step it went to, or -1 */
{
    sq_step_t *s;
    uint32_t n;
    uint8_t stp, fresh = 1u;
    int8_t nudge = 0;
    if (!record_arm || t >= SQ_TRACKS) return -1;
    if (cnt_on) return -1;                                          /* 0.26: a note played during the count is written nowhere */
    if (playing) {
        uint32_t now = sq_micros(), el = (uint32_t)(now - ev[t].slot_start_us), phase;
        phase = ev[t].slot_dur_us ? el * 100u / ev[t].slot_dur_us : 0u;
        if (phase > 99u) phase = 99u;
        sq_rec_target(ev[t].step_index, project.track[t].start, project.track[t].length, project.track[t].direction,
                      (uint8_t)phase, rec_quant, &stp, &nudge);
    } else {
        const sq_track_cfg_t *c = &project.track[t];
        uint8_t chord = (uint32_t)(fm1_ms - srec_ms) < SQ_SREC_CHORD_MS ? 1u : 0u;
        srec_ms = fm1_ms;
        if (srec_next && !chord) {                                  /* the next step of the loop */
            uint8_t nx = (uint8_t)(cursor_step + 1u);
            if (nx >= c->length || nx < c->start) nx = c->start;
            cursor_step = nx;
            page = cursor_step / 16u;
        }
        if (cursor_step >= c->length || cursor_step < c->start) { cursor_step = c->start; page = cursor_step / 16u; }
        fresh = chord ? 0u : 1u;
        srec_next = 1u;
        stp = cursor_step;
    }
    s = &project.step[t][tr[t].pattern][stp];
    if (!(s->flags & SQ_STEP_SET) || !(s->flags & SQ_STEP_ON) || (!playing && fresh)) {   /* the note played is its note */
        for (n = 0; n < SQ_POLY; n++) s->note[n] = SQ_NOTE_NONE;
        s->flags |= SQ_STEP_SET;
        s->nudge = nudge;
    }
    step_activate(t, s);
    s->velocity = vel ? vel : 100u;
    for (n = 0; n < SQ_POLY; n++) {
        if (s->note[n] == note) break;
        if (s->note[n] == SQ_NOTE_NONE) { s->note[n] = note; break; }
    }
    if (!(project.track[t].flags & SQ_TF_DRUM)) PEN(t) = note;     /* (a drum track's note is which drum it is) */
    if (!playing || t == selected_track) { cursor_step = stp; page = cursor_step / 16u; }
    grid_dirty = ui_dirty = 1u;
    return (int)stp;
}

/* drum tracks: a drum machine. With REC armed on a drum track the white keys are the drum tracks of the project (key 1
 * the first drum track, key 2 the second...), each on its own channel and its own note; an incoming note goes to the
 * drum track that plays that note. */
static uint8_t drum_track_n(uint8_t i)              /* the i-th drum track, or 255 */
{
    uint32_t t;
    for (t = 0; t < SQ_TRACKS; t++)
        if (project.track[t].flags & SQ_TF_DRUM) { if (!i) return (uint8_t)t; i--; }
    return 255u;
}
static uint8_t drum_track_for_note(uint8_t note)    /* the drum track (its bank first) whose note this is, or 255 */
{
    uint32_t k, b = selected_track & 8u;
    for (k = 0; k < SQ_TRACKS; k++) {
        uint32_t t = (b + k) % SQ_TRACKS;
        if ((project.track[t].flags & SQ_TF_DRUM) && PEN(t) == note) return (uint8_t)t;
    }
    return 255u;
}

/* 0.18: the tablet (the remote on channels 14 and 13: the hub's pages) has its own track, its own LFO and cursor: what
 * it sends acts there, and the panel's track, page and cursor stay as they are. The grid follows the panel. */
typedef struct { uint8_t track, page, cursor, lfo, srec; uint32_t chord_ms; } focus_t;
static focus_t foc_tab, foc_keep;
static void focus_get(focus_t *f) { f->track = selected_track; f->page = page; f->cursor = cursor_step; f->lfo = lfo_sel; f->srec = srec_next; f->chord_ms = chord_entry_ms; }
static void focus_put(const focus_t *f) { selected_track = f->track < SQ_TRACKS ? f->track : 0u; page = f->page; cursor_step = f->cursor; lfo_sel = f->lfo; srec_next = f->srec; chord_entry_ms = f->chord_ms; }
static void tab_enter(void) { focus_get(&foc_keep); focus_put(&foc_tab); foc_on = 1u; }
static void tab_leave(void) { focus_get(&foc_tab); focus_put(&foc_keep); foc_on = 0u; ui_dirty = grid_dirty = 1u; }
static uint8_t tab_live_ch(uint8_t ch);             /* sagga_tablet.c: channel 12, the hub's LIVE page */
static void live12_cc(uint8_t cc, uint8_t v);
static void fb_heard(uint8_t st, uint8_t d1, uint8_t d2);
static void fb_hub_here(void);                          /* 0.20.8 (sagga_tablet.c): something came in on port 2 */
/* a message of the tablet (the remote's channels 12, 13, 14), or 0 */
static uint8_t tab_takes(uint8_t st)
{
    uint8_t ch = st & 15u, ty = st & 0xF0u;
    if (ty == 0xB0u) return (ch == project.live.remote_ch || vg_remote_ch(ch) || tab_live_ch(ch)) ? 1u : 0u;
    return ((ty == 0x90u || ty == 0x80u) && vg_remote_ch(ch)) ? 1u : 0u;
}
static void tab_cmd(uint8_t st, uint8_t d1, uint8_t d2)
{
    uint8_t ch = st & 15u, ty = st & 0xF0u;
    tab_enter();
    if (ty != 0xB0u) remote13_note(d1, d2, ty == 0x90u && d2);   /* 0.12: the Pi's pads on channel 13: the tablet track's slices or notes */
    else if (ch == project.live.remote_ch) remote_cc(d1, d2);    /* SAGGA REMOTE (sagga_live.c) */
    else if (vg_remote_ch(ch)) vg_remote_cc(d1, d2);             /* 0.9: channel 13 (SAVE + K2) */
    else live12_cc(d1, d2);                                      /* 0.18: channel 12, LIVE */
    tab_leave();
    fb_heard(st, d1, d2);                                        /* (what goes back to the hub: those cells know it) */
}

/* one message that came in on USB port `cab` (0 port 1, 1 port 2); 0.18: also the PC test's MIDI events (sagga_test.c) */
static void midi_in_one(uint32_t now, uint8_t st, uint8_t d1, uint8_t d2, uint8_t cab)
{
    {
        if (usb_ports > 1u) {                       /* 0.8: two USB ports. Port 2: the grid and the remote, nothing else */
            if (cab == 1u) {
                fb_hub_here();                      /* 0.20.8: the hub is there (the bridge's keep-alive, a page) */
                if (!grid_midi_in(st, d1, d2) && tab_takes(st)) tab_cmd(st, d1, d2);   /* the remote, the tablet's pages */
                return;
            }                                       /* port 1 (and the TRS jack): 16 channels of synths, the clock */
        } else if (grid_midi_in(st, d1, d2)) return;   /* one port: channels 15 and 16 are the grid link */
        if (st == 0xF8u) {
            if (project.clock_mode == SQ_CLOCK_SLAVE) {
                if (last_ext_clock_us) {
                    uint32_t d = now - last_ext_clock_us;
                    if (d > 1000u && d < 100000u) ext_clock_us = (ext_clock_us * 7u + d) / 8u;
                }
                last_ext_clock_us = now;
                if (playing) seq_clock_tick(now);
            }
        } else if (st == 0xF2u) {
            if (project.clock_mode == SQ_CLOCK_SLAVE) {
                uint32_t ticks = (((uint32_t)d2 << 7) | d1) * 6u;
                seek_ticks(ticks);
                song_seek(ticks);                       /* 0.5: the song goes there too */
                ui_dirty = grid_dirty = 1u;
            }
        } else if (usb_ports < 2u && tab_takes(st)) {
            tab_cmd(st, d1, d2);                        /* SAGGA REMOTE, channels 12-14 (with two ports: on port 2); 0.18: the tablet's track */
        } else if ((st & 0xF0u) == 0xB0u && learn_take_v(st & 15u, d1, d2)) {
            /* MIDI LEARN took it */
        } else if ((st & 0xF0u) == 0xB0u && snap_cc_in(st & 15u, d1, d2)) {
            /* 0.8: CC CAPTURE took it into the snapshot */
        } else if ((st & 0xF0u) == 0xB0u) {
            if (!project.ext.kb_ch || (st & 15u) == project.ext.kb_ch - 1u) cc_in_val[d1 & 127u] = (uint8_t)(d2 & 127u);   /* 0.20: the MOD MATRIX's CC IN */
            thru_ctl(st, d1, d2);                       /* 0.26: ... and it goes where the keyboard's notes go (the pedal, the wheel) */
        } else if ((st & 0xF0u) == 0xE0u || (st & 0xF0u) == 0xD0u || (st & 0xF0u) == 0xA0u) {
            thru_ctl(st, d1, d2);                       /* 0.26: the pitch wheel, the aftertouch (until 0.25: dropped) */
        } else if (st == 0xFAu && project.clock_mode == SQ_CLOCK_SLAVE) {
            transport_reset(); song_start_hook(); chain_start(); scene_send_pc(scene_cursor); playing = 1u;
            vg_transport_start(); regia_transport_start(); ui_dirty = 1u;    /* (0.9: as the master's start) */
        } else if (st == 0xFBu && project.clock_mode == SQ_CLOCK_SLAVE) {
            realign_all();                              /* (0.11: as the master's CONTINUE) */
            playing = 1u; ui_dirty = 1u;
        } else if (st == 0xFCu && project.clock_mode == SQ_CLOCK_SLAVE) {
            transport_stop_x(0u);                       /* (0.9: the same stop as the master's, without the 0xFC) */
        } else if ((st & 0xF0u) == 0x90u && d2 && kb_takes(st, d1 & 127u)) {
            kb_down(d1 & 127u);                         /* 0.13 KEYBOARD: the note transposes the key (SAVE 4 K2) */
        } else if (((st & 0xF0u) == 0x80u || ((st & 0xF0u) == 0x90u && !d2)) && kb_up(d1 & 127u)) {
            /* (its off: taken too) */
        } else if ((st & 0xF0u) == 0x90u && d2) {
            {   /* 0.12: TAKE remembers what comes in, REC or not (the track it would record on) */
                uint8_t tt = (uint8_t)((vg_rec_t < SQ_TRACKS ? vg_rec_t : selected_track) & 15u);
                if (project.track[tt].flags & SQ_TF_DRUM) { uint8_t dt = drum_track_for_note(d1); if (dt < SQ_TRACKS) tt = dt; }
                take_note_on(d1 & 127u, tt, d1 & 127u, d2);
            }
            ped_release((uint8_t)(d1 & 127u));           /* 0.26: the key struck again while the pedal held its note: that note is over */
            if (record_arm || project.ext.in_thru) {     /* (0.13 MIDI IN ALWAYS: it plays without REC; REC records it) */
                uint8_t t = (uint8_t)((vg_rec_t < SQ_TRACKS ? vg_rec_t : selected_track) & 15u), ch, out;   /* (0.9: a LOOP records on its track) */
                if (project.track[t].flags & SQ_TF_DRUM) {          /* a drum pad controller: each note to its drum track */
                    uint8_t dt = drum_track_for_note(d1);
                    if (dt < SQ_TRACKS) t = dt;
                }
                ch = track_ch(t); out = key_note(t, d1);
                if (ext_ch[d1 & 127u] != 255u) midi_send(0x80u | ext_ch[d1 & 127u], ext_out[d1 & 127u], 0u);
                midi_send(0x90u | ch, out, d2);
                ext_ch[d1 & 127u] = ch;
                ext_out[d1 & 127u] = out;
                if (record_arm && track_tape(t)) tape_rec_on(d1 & 127u, t, d1 & 127u, d2);   /* 0.11 */
                else if (record_arm) {
                    int stp = record_note(t, key_store(t, d1), d2);
                    if (stp >= 0) rec_open_note(d1 & 127u, t, (uint8_t)stp);
                }
            }
        } else if ((st & 0xF0u) == 0x80u || ((st & 0xF0u) == 0x90u && !d2)) {
            if (ext_ch[d1 & 127u] != 255u) {           /* the off follows the on, even if REC was switched off meanwhile */
                midi_send(0x80u | ext_ch[d1 & 127u], ext_out[d1 & 127u], 0u);
                ext_ch[d1 & 127u] = 255u;
            }
            if (!ped_holds((uint8_t)(d1 & 127u))) {    /* 0.26: with the pedal down the note sounds on: its length is counted to the pedal's release */
                rec_close_note(d1 & 127u);             /* 0.10: the length it was held */
                tape_rec_off(d1 & 127u);               /* 0.11 */
                take_note_off(d1 & 127u);              /* 0.12 */
            }
        }
    }
}

static void handle_midi_in(uint32_t now)
{
    uint8_t st, d1, d2;
    while (midi_get(&st, &d1, &d2)) {
        sq_midi_in_n++;
        if (tst_booted) {                           /* 0.11: the PC test hears only its own SysEx (the same run each time); */
            if (!tst_listen) continue;              /* 0.20.3: unless the PC asked to hear the ports too (the Pi's banco: */
            tst_heard(st, d1, d2, midi_cable());    /* the hub's pages, the bridge): played, and where it came said to the */
        }                                           /* PC, which replays it there in the simulator */
        midi_in_one(now, st, d1, d2, midi_cable());
    }
}

static void init_key_maps(void)
{
    uint32_t k;
    white_count = black_count = 0u;
    for (k = 0; k < 27u; k++) {
        if (is_black(SQ_KEY0 + k)) {
            if (black_count < 11u) black_key[black_count] = (uint8_t)k;
            black_count++;
        } else {
            if (white_count < 16u) white_key[white_count] = (uint8_t)k;
            white_count++;
        }
    }
}

static int key_is_in(const uint8_t *a, uint32_t n, uint32_t k)
{
    uint32_t i; for (i = 0; i < n; i++) if (a[i] == k) return (int)i; return -1;
}

/* SEL + keys: put notes on the cursor step (it lights), and that note is the PEN: what the next step lit will play.
 * Keys pressed close together make a chord (up to 6 notes; 0.27: 4). A drum track's pen is which drum it is: left alone. */
static void note_entry(uint32_t k)
{
    uint32_t t = selected_track;
    sq_step_t *s = &project.step[t][tr[t].pattern][cursor_step];
    uint8_t note = clamp_note((int32_t)SQ_KEY0 + (int32_t)k + 12 * key_octave);
    uint32_t n;
    int fresh = (uint32_t)(fm1_ms - chord_entry_ms) > 450u;
    chord_entry_ms = fm1_ms;
    if (fresh) {
        for (n = 0; n < SQ_POLY; n++) s->note[n] = SQ_NOTE_NONE;
        s->note[0] = note;
    } else {
        for (n = 0; n < SQ_POLY; n++) {
            if (s->note[n] == note) break;
            if (s->note[n] == SQ_NOTE_NONE) { s->note[n] = note; break; }
        }
        if (n == SQ_POLY) status_msg("CHORD FULL (6 NOTES)");
    }
    s->flags |= SQ_STEP_ON | SQ_STEP_SET;
    if (!track_drum(t)) PEN(t) = note;
    regia_touched((uint8_t)t);
    preview_note(t, note);
    ui_dirty = grid_dirty = 1u;
}

/* a step key held, then another one: 0.11 the NOTE between them - the first of the two plays, as long as from it to
 * the second (both counted: steps 5 and 8 make a note of 4 steps); FX tapped first (FX pressed and let go alone),
 * the LOOP between them (0.10's gesture). The step held is put back as it was before it was pressed. */
static uint8_t hold_key = 255u, hold_step;
static uint32_t hold_since;
static sq_step_t hold_prev;
#define SQ_SPAN_ARM_MS 8000u
static uint8_t span_loop_arm;              /* SEL + FX tapped (0.12; FX alone before): the next two-step gesture is a loop */
static uint32_t span_arm_ms;
static uint8_t span_is_loop(void)
{
    uint8_t l = span_loop_arm && (uint32_t)(fm1_ms - span_arm_ms) < SQ_SPAN_ARM_MS;
    span_loop_arm = 0u;
    return l;
}
static void set_loop(uint8_t t, uint8_t first, uint8_t last);
/* the note of a two-step gesture: steps a (held) and b of track t; a_prev: step a before it was pressed */
static void note_span(uint8_t t, uint8_t a, uint8_t b, const sq_step_t *a_prev)
{
    sq_step_t *row = project.step[t][tr[t].pattern], *s;
    uint8_t first = a < b ? a : b, last = a < b ? b : a, n = (uint8_t)(last - first + 1u);
    char *p = msg_buf;
    row[a] = *a_prev;
    s = &row[first];
    if (!(s->flags & SQ_STEP_ON)) step_activate(t, s);
    s->length = sq_gate_steps(n);
    s->flags = (uint8_t)((s->flags | SQ_STEP_SET) & ~SQ_STEP_LEGATO);
    if (s->ratchet > 1u) s->ratchet = 1u;                  /* (a held note is one note) */
    cursor_step = first;
    regia_touched(t);
    p = put_s(p, "NOTE "); p = put_u(p, (uint32_t)first + 1u); p = put_s(p, "-"); p = put_u(p, (uint32_t)last + 1u);
    p = put_s(p, ": "); p = put_u(p, n); p = put_s(p, n == 1u ? " STEP" : " STEPS"); finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}

static void step_key_down(uint32_t k, int wi)
{
    uint8_t stn = (uint8_t)(page * 16u + (uint8_t)wi);
    sq_step_t *s = &project.step[selected_track][tr[selected_track].pattern][stn];
    if (hold_key < 27u && (uint32_t)(fm1_ms - hold_since) >= SQ_LOOPHOLD_MS && !span_is_loop()) {
        note_span(selected_track, hold_step, stn, &hold_prev);    /* 0.11: the note between them */
        hold_key = 254u;
        return;
    }
    if (hold_key < 27u && (uint32_t)(fm1_ms - hold_since) >= SQ_LOOPHOLD_MS) {
        project.step[selected_track][tr[selected_track].pattern][hold_step] = hold_prev;
        set_loop(selected_track, hold_step, stn);
        cursor_step = project.track[selected_track].start;
        page = cursor_step / 16u;
        {
            char *p = msg_buf;
            p = put_s(p, "LOOP "); p = put_u(p, (uint32_t)project.track[selected_track].start + 1u);
            p = put_s(p, "-"); p = put_u(p, project.track[selected_track].length); finish(p);
            status_msg(msg_buf);
        }
        hold_key = 254u;                                   /* this gesture is over */
        return;
    }
    if (hold_key == 254u) return;
    hold_key = (uint8_t)k;
    hold_step = stn;
    hold_since = fm1_ms;
    hold_prev = *s;
    cursor_step = stn;
    if (s->flags & SQ_STEP_ON) { s->flags &= (uint8_t)~SQ_STEP_ON; regia_touched(selected_track); }
    else step_activate(selected_track, s);
    ui_dirty = grid_dirty = 1u;
}

/* PERF: black 1-8 the scenes (SEL: store), 9 all on, 10 only the selected track, 11 invert the mutes.
 * With HOME: the song. 1-8 add that scene (the same one again: four bars more), 9 loop on / off, 10 take the last one
 * away, 11 clear it. 0.17: on the third page (the MOSSE) the black keys are the moves (sagga_viaggio.c). */
static void perf_black(int bi, uint8_t sel_held, uint8_t home_held)
{
    if (!home_held && perf_page == 2u) { vg_move_black(bi, sel_held); ui_dirty = grid_dirty = 1u; return; }
    if (home_held) {
        if (bi < 8) song_append((uint8_t)((scene_cursor & 8u) + (uint8_t)bi));
        else if (bi == 8) song_loop_toggle();
        else if (bi == 9) song_drop_last();
        else song_clear();
    } else if (bi < 8) {                                   /* 0.9: scenes of the bank the cursor is in (1-8 or 9-16) */
        uint8_t sc = (uint8_t)((scene_cursor & 8u) + (uint8_t)bi);
        if (sel_held) capture_scene(sc); else scene_recall(sc);
    }
    else if (bi == 8) { mute_mask = 0u; solo_mask = 0u; pending_mute = 0u; vg_states_sync_all(); }
    else if (bi == 9) { mute_mask = (uint16_t)(SQ_TRACK_BITS & ~(1u << selected_track)); solo_mask = 0u; pending_mute = 0u; vg_states_sync_all(); }
    else { mute_mask = (uint16_t)(~mute_mask & SQ_TRACK_BITS); pending_mute = 0u; vg_states_sync_all(); }
    ui_dirty = grid_dirty = 1u;
}

/* SEQ + a black key: 1-5 the dice (SEQ, CC, LFO, GROOVE, ALL), 6 the scope, 7 KIT (held: BAND), 8 DRIFT, 9 EVOLVE,
 * 10 FREEZE, 11 REVERT (0.12: black 1 held = DICE PROG, black 7 held = BAND: sagga_pick.c) */
static void harm_dice(void);                      /* sagga_gen.c: 0.11 DICE PROG */
static void seq_black(int bi)
{
    if (bi < 5) dice_roll((uint8_t)(DICE_SEQ + bi));
    else if (bi == 5) gen_scope_set((uint8_t)((project.gen.scope + 1u) % SQ_SCOPES));
    else if (bi == 6) beat_kit();
    else if (bi == 7) evo_drift_toggle();
    else if (bi == 8) evo_toggle();
    else if (bi == 9) evo_freeze();
    else evo_revert();
}

/* the black keys with nothing held: tracks 1-8 of the bank, 9 the other bank, 10 mute and 11 solo of the selected track */
static void track_black(int bi)
{
    if (bi < 8) select_track((uint8_t)((selected_track & 8u) + (uint8_t)bi));    /* (0.28: in 9-12, black 5-8 nothing) */
    else if (bi == 8) select_track(track_other_bank(selected_track));
    else if (bi == 9) toggle_mute(selected_track);
    else toggle_solo(selected_track);
}

static uint8_t rec_used = 1u;             /* 0.12: REC is held and did its job (a combo, TAKE); letting it go is not a tap */
static uint32_t rec_down_ms;

/* ---- 0.12 the WINDOWS: a tap on HOME, SEQ, EDIT, ENV, LFO, ARP or FX keeps the button "held" until it is tapped
 * again or another window opens (GLO's window is PERF, as it was; SAVE has none: a tap saves). Everything a held
 * button means the window means too: the knobs and the screen, the keys, OCT for the pages, SEL + a key for PICK. A
 * button really held always wins over the window, and lets it be when it goes. A tap: pressed and let go within 600 ms
 * with nothing else happening (another button, a key, a knob). With SEL held the tap is the one of 0.11: SEL + ARP the
 * arpeggio on / off, SEL + FX the next two steps are a LOOP. */
#define WIN_BTNS ((1u << BTN_HOME) | (1u << BTN_SEQ) | (1u << BTN_EDIT) | (1u << BTN_ENV) | (1u << BTN_LFO) | (1u << BTN_ARP) | (1u << BTN_FX))
#define GROUP_BTNS (WIN_BTNS | (1u << BTN_GLO) | (1u << BTN_SAVE))
static uint8_t win_cur = 255u;             /* the window open: a BTN_, or 255 */
static uint8_t win_pend = 255u;            /* the window button pressed alone, waiting for its release */
static uint8_t win_used, win_sel;          /* ... something else happened meanwhile; SEL was held when it went down */
static uint32_t win_down_ms;
static uint32_t eff_held(void)             /* the buttons held, the window's among them when no group button is */
{
    uint32_t h = in_held();
    if (win_cur != 255u && !(h & GROUP_BTNS)) h |= 1u << win_cur;
    return h;
}
static void win_open(uint8_t btn)
{
    if ((btn == BTN_SEQ || btn == BTN_EDIT || btn == BTN_ENV) && !vg_edit_keys()) { status_msg("NOT IN THIS PROFILE (SAVE + K4: FULL)"); ui_dirty = 1u; return; }
    win_cur = btn;
    perf_mode = 0u;
    ui_dirty = grid_dirty = 1u;
}
static void win_close(void)
{
    if (win_cur == 255u) return;
    win_cur = 255u;
    ui_dirty = grid_dirty = 1u;
}
static void win_tap(uint8_t btn, uint8_t sel)
{
    if (sel) {                                                      /* SEL + a tap: what the tap alone did in 0.11 */
        if (btn == BTN_ARP) arp_toggle();
        else if (btn == BTN_FX && !fx_now()) {
            span_loop_arm = (uint8_t)!span_loop_arm; span_arm_ms = fm1_ms;
            status_msg(span_loop_arm ? "LOOP: HOLD A STEP, PRESS ANOTHER" : "TWO STEPS: A NOTE AGAIN");
        }
        return;
    }
    if (win_cur == btn) win_close(); else win_open(btn);
}
/* handle_buttons: the edges `b` and the releases `rel` of this pass, `held` what is down now */
static void win_buttons(uint32_t b, uint32_t rel, uint32_t held)
{
    if (b) {
        if (win_pend != 255u && (b & ~(1u << win_pend))) win_used = 1u;        /* another button: not a tap */
        if ((b & WIN_BTNS) && !(b & (b - 1u)) && !(held & ~b & ~(1u << BTN_SEL))) {   /* one of them, nothing else down (SEL apart) */
            uint8_t i = 0u;
            while (!((b >> i) & 1u)) i++;
            win_pend = i; win_down_ms = fm1_ms; win_used = 0u; win_sel = (held & (1u << BTN_SEL)) ? 1u : 0u;
        }
    }
    if (win_pend != 255u && (rel & (1u << win_pend))) {
        if (!win_used && (uint32_t)(fm1_ms - win_down_ms) < 600u) win_tap(win_pend, win_sel);
        win_pend = 255u;
    }
}

/* The keys. The button held decides what they do (0.5.1):
 *   nothing      white: the steps (held + another: a loop)      black: tracks, bank, mute, solo
 *   SEL          the keys are notes for the cursor step
 *   HOME         white: track 1-16                                black: as with nothing held (PERF: the song)
 *   EDIT, ENV    white: the cursor goes to that step (it is not switched)   EDIT + black 2-4: COPY, PASTE, CLEAR the step
 *   SEQ          white: the 16 tools                              black: dice, scope, KIT, DRIFT, EVOLVE, FREEZE, REVERT
 *   FX           white: the effects while held                    black 1-8: LOOP (tap) / REPEAT (hold), 9 RESTART,
 *                                                                 10 STOP at the end of the bar, 11 EXIT the loop
 *   LFO          white: that LFO on / off
 *   PERF (GLO)   white: mutes (SEL: solo)                         black: scenes (SEL: store), all on, only this, invert
 *   SAVE         white 1-8: the slot                              black 1-8: SNAPSHOT (SEL: store), 9 CC CAPTURE,
 *                                                                 10 SEND the snapshot's sound, 11 the synths' PATCHES (Pi) */
static void slot_pick(uint8_t s);                 /* sagga_store.c */
static void snap_recall(uint8_t n);               /* sagga_live.c: SNAPSHOTS */
static void snap_store(uint8_t n);
static void snap_capture_toggle(void);
static void snap_send(void);
static void snap_patches(void);
static int pick_group(uint32_t held);              /* sagga_pick.c: 0.12 */
static void pick_key(uint32_t held, int g, uint32_t k);
static uint8_t seqhold_is(int wi, int bi);
static void seqhold_down(uint32_t k);
static void seqhold_up(uint32_t k);
static void handle_keys(uint32_t keys)
{
    uint32_t down = keys & ~prev_keys, up = prev_keys & ~keys, k, held = eff_held();   /* (0.12: the window counts as held) */
    uint8_t sel_held = (held & (1u << BTN_SEL)) ? 1u : 0u;
    int pick_g = sel_held ? pick_group(held) : -1;        /* 0.12: a group + SEL: the keys set the knob in focus */
    prev_keys = keys;
    if (down && win_pend != 255u) win_used = 1u;         /* 0.12: a key with the button: not a tap */
    if (down && (held & (1u << BTN_GLO))) { glo_used = 1u; selglo_pend = 0u; }   /* (a key: GLO was a modifier, not SEL + GLO) */
    if (up) brk_white_up(up);                              /* 0.12: a chop held on a white key let go */
    if (up) for (k = 0; k < 27u; k++) if (up & (1u << k)) seqhold_up(k);   /* 0.12: UNDO, COOK, DICE, KIT act when let go */

    for (k = 0; k < 27u; k++)                              /* a live note ends when its key does, REC or not */
        if ((up & live_held) & (1u << k)) {
            midi_send(0x80u | live_ch[k], live_note[k], 0u);
            live_held &= ~(1u << k);
            rec_close_note((uint8_t)(128u + k));           /* 0.10: the length it was held */
            tape_rec_off((uint8_t)(128u + k));             /* 0.11 */
            take_note_off((uint8_t)(128u + k));            /* 0.12 */
        }
    if (hold_key < 27u && (up & (1u << hold_key))) hold_key = 255u;
    if (up && brk_roll_held) { for (k = 0; k < 2u; k++) if (up & (1u << black_key[k])) brk_black_up((int)k); }   /* 0.12 */
    if (up) rep_up(up);                                    /* 0.13: NOTE REPEAT let go */
    if (hold_key == 254u && !(keys & (0x7FFFFFFu))) hold_key = 255u;
    for (k = 0; k < 8u; k++)                               /* a LOOP / REPEAT key let go (FX may be up already) */
        if ((up & (1u << black_key[k])) && (lp_held & (1u << (LP_PANEL + k)))) loop_release((uint8_t)(LP_PANEL + k));

    if (held & (1u << BTN_FX)) {                           /* FX held: the white keys are momentary effects */
        uint16_t m = 0u;
        for (k = 0; k < 16u; k++) if (keys & (1u << white_key[k])) m |= (uint16_t)(1u << k);
        if (m != fx_panel) { fx_panel = m; ui_dirty = grid_dirty = 1u; }
    } else if (fx_panel) { fx_panel = 0u; ui_dirty = grid_dirty = 1u; }

    /* REC: the keys play and record (with FX, SEQ, LFO, HOME, EDIT, ENV held, or in PERF, they keep their jobs). On a
     * drum track the white keys are the drum tracks, each its own note on its own channel. */
    {
        uint8_t arp_play = (held & (1u << BTN_ARP)) && !sel_held ? 1u : 0u;   /* 0.12: ARP held: the keys play the track (no REC needed) */
        if ((record_arm || arp_play) && (!perf_mode || vg_rec_t < SQ_TRACKS || arp_play) && pick_g < 0 && !(held & (1u << BTN_GLO)) &&
            !(held & ((1u << BTN_FX) | (1u << BTN_SEQ) | (1u << BTN_LFO) | (1u << BTN_HOME) | (1u << BTN_EDIT) | (1u << BTN_ENV) | (1u << BTN_SAVE)))) {
            uint8_t rec_track = vg_rec_t < SQ_TRACKS ? vg_rec_t : selected_track;
            uint8_t drum = track_drum(rec_track), brk = track_break(rec_track);
            for (k = 0; k < 27u; k++) {
                if (down & (1u << k)) {
                    int wi = key_is_in(white_key, 16u, k), bi = key_is_in(black_key, 11u, k);
                    uint8_t t = rec_track, note;
                    if (brk && bi >= 0 && arp_play) { brk_black(t, bi); continue; }   /* 0.12: ARP + black: the break's live moves */
                    if (drum && bi >= 0 && bi < 4 && arp_play && vg_rec_t >= SQ_TRACKS) { rep_black(t, bi); continue; }   /* 0.13: ARP + black 1-4: NOTE REPEAT */
                    if (brk && wi >= 0 && arp_play) { brk_white(t, (uint8_t)wi, k); continue; }   /* 0.12: ARP + white: chop 1-16 (held: while held) */
                    if (brk && wi >= 0) note = (uint8_t)clamp_i32((int32_t)PEN(t) + (int32_t)(wi % brk_slices(t)), 0, 127);   /* 0.12: REC + white: a slice */
                    else if (brk) note = (uint8_t)clamp_i32((int32_t)PEN(t) + (int32_t)((16u + (uint32_t)bi) % brk_slices(t)), 0, 127);   /* REC + black: slices 17-27 (32 slices) */
                    else if (drum && wi >= 0) {
                        if (vg_rec_t < SQ_TRACKS) note = PEN(t);        /* 0.9: a LOOP on a drum track: every white key is its drum */
                        else {
                            t = drum_track_n((uint8_t)wi);
                            if (t >= SQ_TRACKS) continue;
                            note = PEN(t);
                        }
                    } else note = clamp_note((int32_t)SQ_KEY0 + (int32_t)k + 12 * key_octave);
                    live_note[k] = key_note(t, note);
                    live_ch[k] = track_ch(t);
                    live_held |= 1u << k;
                    midi_send(0x90u | live_ch[k], live_note[k], 100u);
                    if (brk) brk_live_played(live_ch[k], live_note[k], 100u);
                    take_note_on((uint8_t)(128u + k), t, note, 100u);  /* 0.12: TAKE remembers what was played */
                    if (!record_arm) continue;
                    if (track_tape(t)) tape_rec_on((uint8_t)(128u + k), t, note, 100u);   /* 0.11 */
                    else {
                        int stp = record_note(t, key_store(t, note), 100u);
                        if (stp >= 0) rec_open_note((uint8_t)(128u + k), t, (uint8_t)stp);
                    }
                }
            }
            return;
        }
    }

    for (k = 0; k < 27u; k++) if (down & (1u << k)) {
        int wi = key_is_in(white_key, 16u, k);
        int bi = key_is_in(black_key, 11u, k);
        if (held & (1u << BTN_SAVE)) {                         /* SAVE + a key: a slot, a SNAPSHOT */
            save_knob = 1u;                                    /* (letting SAVE go is not a save then) */
            if (wi >= 0 && wi < (int)8) { slot_pick((uint8_t)wi); status_num("SLOT ", (uint32_t)wi + 1u); }
            else if (wi == 15) vg_save_journey();                 /* 0.9: SAVE + white 16 = SALVA VIAGGIO */
            else if (bi >= 0 && bi < 8) { if (sel_held) snap_store((uint8_t)bi); else snap_recall((uint8_t)bi); }
            else if (bi == 8) snap_capture_toggle();
            else if (bi == 9) snap_send();
            else if (bi == 10) snap_patches();
            continue;
        }
        if (!vg_edit_keys() && (held & ((1u << BTN_SEQ) | (1u << BTN_EDIT) | (1u << BTN_ENV)))) {   /* 0.9: PALCO */
            status_msg("NOT IN THIS PROFILE (SAVE + K4: FULL)"); ui_dirty = 1u;
            continue;
        }
        if (pick_g >= 0) { pick_key(held, pick_g, k); continue; }   /* 0.12 PICK: the key sets the knob in focus */
        if (held & (1u << BTN_SEQ)) {                          /* SEQ + a white key: a tool; + a black key: dice, EVOLVE */
            if (wi >= 0 && (keys & (1u << black_key[5]))) { gen_custom_toggle((uint8_t)wi); continue; }
            if (seqhold_is(wi, bi)) seqhold_down(k);           /* 0.12: UNDO COOK DICE KIT when let go; held 0.6 s: REDO, random COOK, DICE PROG, BAND */
            else if (wi == (int)TOOL_EUC && seq_page == 1u && !track_tape(selected_track)) algo_go(selected_track);   /* 0.16: on SEQ 2 the algorithm starts / stops */
            else if (wi == (int)TOOL_EUC && mfx_pend[selected_track]) mfx_go(selected_track);   /* 0.16: a MIDI FX READY (HOME 6) starts */
            else if (wi >= 0 && wi < (int)TOOL_COUNT) tool_apply((uint8_t)wi);
            else if (bi >= 0) seq_black(bi);
            continue;
        }
        if (held & (1u << BTN_FX)) {                           /* FX + a black key: LOOP / REPEAT, RESTART, STOP, EXIT */
            if (bi >= 0 && bi < 8) loop_press(loop_ticks((uint32_t)bi), (uint8_t)(LP_PANEL + bi), sel_held ? (uint16_t)(1u << selected_track) : 0xFFFFu);
            else if (bi == 8) restart_all();
            else if (bi == 9) stop_bar_toggle();
            else if (bi == 10) loop_exit();
            continue;
        }
        if (held & (1u << BTN_LFO)) {                          /* LFO + a white key: pick that LFO and switch it */
            if (wi >= 0) {
                lfo_sel = (uint8_t)wi;
                project.lfo[wi].enabled ^= 1u;
                lfo_last_valid[wi] = 0u;
                status_msg(project.lfo[wi].enabled ? "LFO ON" : "LFO OFF");
                ui_dirty = 1u;
            }
            continue;
        }
        if (held & (1u << BTN_HOME)) {                         /* HOME + a white key: that track, 1-16 */
            if (wi >= 0 && wi < (int)SQ_TRACKS) { select_track((uint8_t)wi); status_num("TRACK ", (uint32_t)wi + 1u); }
            else if (bi >= 0) { if (perf_mode) perf_black(bi, sel_held, 1u); else track_black(bi); }
            continue;
        }
        if (held & ((1u << BTN_EDIT) | (1u << BTN_ENV))) {     /* EDIT / ENV + a white key: the cursor, the step untouched */
            if (wi >= 0) { cursor_to((uint8_t)(page * 16u + (uint8_t)wi)); status_num("STEP ", (uint32_t)cursor_step + 1u); }
            else if (bi >= 0 && (held & (1u << BTN_EDIT))) step_tool(bi);
            continue;
        }
        if (held & (1u << BTN_GLO)) {                          /* 0.12: GLO held: the PERF keys, in any mode (mutes, scenes) */
            if (wi >= 0) { if (perf_solo_mode) toggle_solo((uint8_t)wi); else toggle_mute((uint8_t)wi); }
            else if (bi >= 0) perf_black(bi, 0u, 0u);   /* (GLO + SEL + a key is PICK: on the MOSSE the long BREAK is PERF + SEL + black 2) */
            continue;
        }
        if (perf_mode) {
            if (wi >= 0) {
                if (sel_held || perf_solo_mode) toggle_solo((uint8_t)wi); else toggle_mute((uint8_t)wi);
            } else if (bi >= 0) perf_black(bi, sel_held, 0u);
            continue;
        }
        if (sel_held) { note_entry(k); continue; }

        if (bi >= 0) track_black(bi);
        else if (wi >= 0) step_key_down(k, wi);
    }
}

static void slot_turn(int32_t d);                 /* sagga_store.c */
static void save_turn(int32_t d);
static void save_pressed(void);
static void store_tap_clear(void);               /* 0.15 */
static void save_released(uint32_t held);
static uint8_t save_tick(void);
static void pipat_tick(void);                     /* sagga_pipat.c: 0.11 the Pi's patterns */
static uint8_t pipat_count(uint8_t g, uint8_t f);
static uint8_t pipat_loadable(uint8_t f);

/* The encoders. The button held decides what K1..K4 do; OCT- / OCT+ turn the page of that button:
 *   nothing   the cursor step: note, velocity, chance, ratchet          SEL     velocity offset, humanise time / vel, pen note
 *   EDIT      gate, condition, nudge, ramp                              ENV     the 4 CC lanes (lock / CC number / base)
 *   HOME      1 channel, length, step, transpose   2 direction, swing, FOLLOW the harmony, HARMONY on / off
 *             3 root, scale, shift, mode (FREE / KEY / DRUM)   4 the loops of the notes, velocities, gates, the program
 *             5 MIDI FX: effect, amount, time / which steps, velocity kept
 *   ARP       arp mode, octaves, voicing, strum                         LFO     shape ... (three pages)
 *   SEQ       1 EUCLID pulses, rotation (live, this track), density, heat   2 ALGORITHM, A, B, C (this track)
 *             3 targets, EVOLVE amount, EVOLVE every, scope   4 HARMONY on / off, progression, bars a chord, FOLLOW
 *   FX        the macros: INTENSITY, GATE, SWING, FILTER (FX + OCT-: back to 0)
 *   SAVE      K1 what the MASTER knob does, K2 the remote (channel 14), K3 snapshots bring the tempo; PRESETS: the slot
 *   PERF      MORPH, MORPH TO, TRANSPOSE (quantised), QUANTISE       PERF + SEL   pattern, length, scale, MUTE QUEUE
 *   SAVE 3      SYSTEM: K1 one or two USB ports (SEL + K1 twice: reconnect, and it is so), K2 the button lights
 * 0.8: values with a middle or a 0 always reach it again (kstep), and they move faster when the knob turns fast. */
static uint8_t usb_ports_want = 1u;               /* the USB page: what the next reconnect presents */
static void usb_ports_note(void);
static void usb_reconnect_ask(void);
#define LIGHTS_N 5u
static const char *const LIGHTS_NAME[LIGHTS_N] = {"OFF", "LOW", "MID", "HIGH", "MAX"};
static uint8_t lights_level(void);
static void lights_apply(void);
static void euclid_touch(uint8_t t);              /* sagga_gen.c */
static void algo_choose(uint8_t t, uint8_t a);
static void algo_go(uint8_t t);
static void algo_slot_select(uint8_t t, uint8_t k);
static sq_algo_t *algo_slot(uint32_t t);
static void harm_toggle(void);
static void harm_prog_set(uint8_t i);
static void harm_bars_turn(int32_t d);
static void follow_set(uint8_t t, uint8_t on);
static void dice_browse(int32_t d);
static uint8_t dice_pending;
static uint8_t arp_page, save_page;               /* 0.12: ARP has six pages (the chords and the harmony), SAVE three */
/* 0.18 the RATE knob's order: 1/4, 1/2, ROLL, 1, 2, 3, 4 - left of ROLL slower, right faster, as in 0.10-0.17 (the values
 * stay those of 0.10: 0 ROLL, 1-4, then 5 1/2, 6 1/4) */
static const uint8_t ARP_RATE_ORDER[SQ_ARP_RATE_MAX + 1u] = {SQ_ARP_R_QUARTER, SQ_ARP_R_HALF, 0u, 1u, 2u, 3u, 4u};
static uint8_t arp_rate_at(uint8_t pos) { return ARP_RATE_ORDER[pos <= SQ_ARP_RATE_MAX ? pos : 0u]; }
static uint8_t arp_rate_pos(uint8_t r) { uint8_t i; for (i = 0; i <= SQ_ARP_RATE_MAX; i++) if (ARP_RATE_ORDER[i] == r) return i; return 2u; }
static const char *arp_rate_name(uint8_t r) { static const char *const N[SQ_ARP_RATE_MAX + 1u] = {"ROLL", "1", "2", "3", "4", "1/2", "1/4"}; return N[r <= SQ_ARP_RATE_MAX ? r : 0u]; }
static uint8_t perf_page;                         /* 0.12: GLO (PERF) has three: LIVE, TRACK LIVE, VIAGGIO (0.17: the MOSSE) */

/* 0.12: the knobs of GLO's three pages (GLO held, or PERF mode without holding it) */
static void glo_page_knobs(uint8_t page, int32_t d1, int32_t d2, int32_t d3, int32_t d4, int32_t f1, int32_t f2)
{
    if (page == 1u) {                              /* 2 TRACK LIVE: pattern, length, scale, MUTE QUEUE */
        if (d1) queue_pattern(selected_track, change_u8(tr[selected_track].pending_pattern < SQ_PATTERNS ? tr[selected_track].pending_pattern : tr[selected_track].pattern, d1, 0u, 7u));
        if (d2) set_length(selected_track, (uint8_t)kstep(len_shown(selected_track), d2, f2, 1, 64));
        if (d3) set_key_scale(d3);
        if (d4 && ((d4 > 0) != (project.live.mute_q != 0u))) mute_q_toggle();
    } else if (page == 3u) {                       /* 4 THE METRE (0.25): the bar in steps, its beats */
        if (d1) metre_ask((uint8_t)kstep(bar_shown(), d1, f1, (int32_t)SQ_BAR_MIN, (int32_t)SQ_BAR_MAX), 0u);   /* (a new bar: its usual beats) */
        if (d2) {
            uint8_t st = bar_shown(), n = sq_metre_options(st), i = sq_metre_index(st, beats_shown());
            if (n < 2u) status_msg("THIS BAR HAS ONE WAY ONLY");
            else metre_ask(st, sq_metre_option(st, change_u8(i < n ? i : 0u, d2, 0u, (uint8_t)(n - 1u))));
        }
        if (d3 && ((d3 > 0) != (project.ext.scene_metre_on != 0u))) scene_metre_toggle((uint8_t)(d3 > 0));   /* 0.26: the scenes bring their metre */
    } else if (page == 2u) {                       /* 3 the MOSSE (0.17; VIAGGIO until 0.16): energy, phrase, genre, key */
        if (d1) vg_energy_turn(d1 * f1);
        while (d2) { vg_bars_turn(d2 > 0 ? 1 : -1); d2 += d2 > 0 ? -1 : 1; }   /* (one step a detent: PICK turns it by several) */
        if (d3) vg_genre_turn(d3);
        if (d4) vg_key_turn(d4);
    } else {                                       /* 1 LIVE: MORPH, MORPH TO, TRANSPOSE, QUANTISE */
        if (d1) morph_set((uint8_t)kstep(morph_pos, d1, 4 * f1, 0, 127));
        if (d2) morph_target(change_u8(project.live.morph_b, d2, 0u, SQ_SCENES - 1u));
        if (d3) ktrans_set(ktrans_target() + d3);
        if (d4) quant_set(change_u8(project.live.quant, d4, 0u, SQ_QUANTS - 1u));
    }
    if (d1 || d2 || d3 || d4) ui_dirty = grid_dirty = 1u;
}
#define HOME_PAGES 8u                                  /* 0.13: 8 CHAIN LIST */
#define SEQ_PAGES 8u
#define ARP_PAGES 6u
#define SAVE_PAGES 5u                                  /* 0.13: 4 LIVE IN; 0.26: 5 CLICK */
#define PERF_PAGES 4u                                  /* 0.25: 4 THE METRE */
#define LFO_PAGES 6u                                   /* 0.13: 4 RATE SEQ; 0.20: 5 ENV, 6 MOD */
#define LFO_PAGE_ENV 4u
#define LFO_PAGE_MOD 5u
static uint8_t uprog_sel, uprog_pos;              /* 0.10: SEQ 8: the user progression being written, the chord */
static void uprog_note(void);
/* 0.11: the root of the chord at uprog_pos: "--" (the progression ends here), I bII II ... VII; a chord written by its
 * step of the key (0.10) becomes the same root and its colour the first time it turns */
static void uprog_root_turn(sq_uprog_t *u, int32_t d)
{
    uint8_t k = uprog_pos;
    int32_t v;
    if (k < u->n && u->semi[k] == 255u) {
        sq_hchord_t x = {u->deg[k], u->col[k], 255u, 0u};
        u->semi[k] = sq_hchord_semi(project.key_scale, &x);
        u->shape[k] = u->col[k];
    }
    v = k < u->n ? (int32_t)u->semi[k] : -1;
    v = clamp_i32(v + d, -1, 11);
    if (v < 0) { if (u->n > k) u->n = k; }
    else {
        uint32_t j;
        for (j = u->n; j < k; j++) { u->deg[j] = 0; u->col[j] = SQ_HC_TRIAD; u->semi[j] = 0u; u->shape[j] = SQ_HC_TRIAD; u->dur[j] = 0u; u->push[j] = 0u; }
        if (u->n <= k) { u->shape[k] = SQ_HC_TRIAD; u->dur[k] = 0u; u->push[k] = 0u; u->n = (uint8_t)(k + 1u); }
        u->semi[k] = (uint8_t)v;
    }
    uprog_note();
}
/* 0.16 EDIT + ARP: the progression that plays (the genre's, the player's, DICE/PI's) copied into a USER slot, so that it
 * can be changed on ARP 5 / 6: the slot ARP 5 K1 shows, else the first empty one; over one that holds a progression:
 * asked twice. The copy plays from then on, as it was (a genre's keeps its steps and colours: it moves with the key) */
static uint32_t pcopy_ask_ms;
static uint8_t pcopy_ask_to = 255u;
static void prog_copy(void)
{
    const sq_gen_t *g = &project.gen;
    uint8_t from = g->harm_prog, to = 255u, k;
    sq_uprog_t u;
    char *p = msg_buf;
    if (uprog_sel < SQ_UPROGS && from != SQ_PROGS + uprog_sel) to = uprog_sel;
    else for (k = 0; k < SQ_UPROGS; k++) if (!project.uprog[k].n && from != SQ_PROGS + k) { to = k; break; }
    if (to == 255u) { status_msg("COPY: CHOOSE A USER SLOT ON ARP 5 K1"); return; }
    if (from >= SQ_PROGS) u = project.uprog[(from - SQ_PROGS) % SQ_UPROG_SLOTS];
    else {
        const sq_prog_t *pg = sq_prog_get(g->harm_genre, from);
        memset(&u, 0, sizeof u);
        u.n = pg->n > SQ_HPROG_CH ? (uint8_t)SQ_HPROG_CH : pg->n;
        u.bars = pg->bars;
        for (k = 0; k < SQ_HPROG_CH; k++) {
            u.deg[k] = k < u.n ? pg->deg[k] : 0; u.col[k] = k < u.n ? pg->col[k] : SQ_HC_TRIAD;
            u.semi[k] = 255u; u.shape[k] = u.col[k];
        }
    }
    if (!u.n) { status_msg("COPY: NO PROGRESSION PLAYS"); return; }
    if (project.uprog[to].n && !(pcopy_ask_to == to && pcopy_ask_ms && (uint32_t)(fm1_ms - pcopy_ask_ms) < 3000u)) {
        pcopy_ask_to = to; pcopy_ask_ms = fm1_ms ? fm1_ms : 1u;
        p = put_s(p, "COPY OVER USER "); p = put_u(p, (uint32_t)to + 1u); p = put_s(p, ": EDIT+ARP AGAIN"); finish(p);
        status_msg(msg_buf);
        return;
    }
    pcopy_ask_to = 255u;
    project.uprog[to] = u;
    piprog_leave();
    project.gen.harm_prog = (uint8_t)(SQ_PROGS + to);
    uprog_sel = to; uprog_pos = 0u;
    p = put_s(p, "COPIED TO USER "); p = put_u(p, (uint32_t)to + 1u); p = put_s(p, ": ARP 5 TO CHANGE IT"); finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}

static void uprog_shape_turn(sq_uprog_t *u, int32_t d)
{
    uint8_t k = uprog_pos;
    int32_t v;
    if (u->semi[k] == 255u) {                                         /* (by its step: the colours, as 0.10) */
        u->col[k] = change_u8(u->col[k], d, 0u, SQ_HCS - 1u);
        uprog_note();
        return;
    }
    v = clamp_i32((int32_t)u->shape[k] + d, 0, SQ_HSHAPES - 1);       /* (5 is the colour 6; the shapes from OCT on) */
    u->shape[k] = (uint8_t)v;
    uprog_note();
}
/* USER PROG, SEL + K2: the lengths and pushes of one of the HARMONY's rhythms written into the chords (then each its own) */
static uint8_t uprog_rhythm_r;                   /* the rhythm last written (0.12 PICK reads it) */
static void uprog_rhythm_turn(sq_uprog_t *u, int32_t d)
{
    sq_hprog_t h;
    uint8_t k, r;
    char *p = msg_buf;
    r = uprog_rhythm_r = change_u8(uprog_rhythm_r, d, 0u, SQ_HRS - 1u);
    if (r == SQ_HR_GENRE) r = uprog_rhythm_r = d > 0 ? SQ_HR_PUSH16 : SQ_HR_BARS;
    for (k = 0; k < u->n; k++) { u->dur[k] = 0u; u->push[k] = 0u; }
    sq_hprog_user(&h, u, 0u, r);
    for (k = 0; k < u->n; k++) { u->dur[k] = r == SQ_HR_BARS ? 0u : h.dur[k]; u->push[k] = h.push[k]; }
    p = put_s(p, "LENGTHS: "); p = put_s(p, sq_hrhythm_name(r)); finish(p);
    status_msg(msg_buf);
}
static void every_arm(void);                      /* sagga_gen.c */
static void genre_mode_note(void);
static void uprog_note(void)
{
    char *p = msg_buf;
    p = put_s(p, "USER PROG "); p = put_u(p, (uint32_t)uprog_sel + 1u); p = put_s(p, ": ");
    sq_uprog_name(&project.uprog[uprog_sel], project.key_scale, p, 36u);
    while (*p) p++;
    finish(p);
    status_msg(msg_buf);
}

static void pick_knob_turned(uint32_t held, int32_t d1, int32_t d2, int32_t d3, int32_t d4);   /* sagga_pick.c */
static void encoders_apply(int32_t dsel, int32_t dalg, int32_t dp, int32_t d1, int32_t d2, int32_t d3, int32_t d4,
                           int32_t f1, int32_t f2, int32_t f3, int32_t f4, int32_t fa, uint32_t held);
static void handle_encoders(void)
{
    int32_t dsel = enc_take(ENC_SELECT), dalg = enc_take(ENC_ALGORITHM), dp = enc_take(ENC_PRESETS);
    int32_t d1 = enc_take(ENC_KNOB1), d2 = enc_take(ENC_KNOB2), d3 = enc_take(ENC_KNOB3), d4 = enc_take(ENC_KNOB4);
    int32_t f1 = enc_fast(ENC_KNOB1), f2 = enc_fast(ENC_KNOB2), f3 = enc_fast(ENC_KNOB3), f4 = enc_fast(ENC_KNOB4);
    int32_t fa = enc_fast(ENC_ALGORITHM);
    uint32_t held = eff_held();                                           /* (0.12: the window counts as held) */
    if ((dsel || dalg || dp || d1 || d2 || d3 || d4) && win_pend != 255u) win_used = 1u;   /* 0.12: a knob with the button: not a tap */
    if (d1 || d2 || d3 || d4) pick_knob_turned(held, d1, d2, d3, d4);   /* 0.12: the knob in focus follows the hand */
    encoders_apply(dsel, dalg, dp, d1, d2, d3, d4, f1, f2, f3, f4, fa, held);
}
/* the knobs' work; 0.12 PICK calls it too, with the turns that take the knob in focus to the key's value */
static void encoders_apply(int32_t dsel, int32_t dalg, int32_t dp, int32_t d1, int32_t d2, int32_t d3, int32_t d4,
                           int32_t f1, int32_t f2, int32_t f3, int32_t f4, int32_t fa, uint32_t held)
{
    const uint32_t GROUPS = (1u << BTN_HOME) | (1u << BTN_EDIT) | (1u << BTN_ENV) | (1u << BTN_LFO) | (1u << BTN_SEQ) |
                            (1u << BTN_FX) | (1u << BTN_ARP) | (1u << BTN_SEL) | (1u << BTN_SAVE);
    sq_track_cfg_t *cfg;
    sq_step_t *s;
    if (!vg_edit_keys() && (held & ((1u << BTN_SEQ) | (1u << BTN_EDIT) | (1u << BTN_ENV))) && (d1 || d2 || d3 || d4 || dp || dalg)) {
        status_msg("NOT IN THIS PROFILE (SAVE + K4: FULL)"); ui_dirty = 1u;   /* 0.9 PALCO: no editing by the knobs either */
        return;
    }
    if (held & (1u << BTN_SAVE)) {                     /* SAVE: the slot, the MASTER knob, the remote, snapshot tempo; page 2: lead, song tempo, device */
        if (dp) save_turn(dp);
        if (save_page == 4u) {                         /* 0.26 CLICK: the metronome, the count, where it sounds, how loud (SEL + K4: its note) */
            click_knobs(d1, d2, d3, d4, (uint8_t)((held & (1u << BTN_SEL)) != 0u));
            if (d1 || d2 || d3 || d4) { save_knob = 1u; ui_dirty = 1u; }
            return;
        }
        if (save_page == 3u) {                         /* 0.13 LIVE IN: MOTION, the KEYBOARD's transpose, its channel, MIDI IN */
            sq_ext_t *x = &project.ext;
            if (d1) {
                static const uint8_t MB[4] = {0u, 1u, 2u, 4u};
                uint8_t i = x->motion_bars == 4u ? 3u : x->motion_bars;
                x->motion_bars = MB[change_u8(i, d1, 0u, 3u)];
                if (!x->motion_bars) status_msg("MOTION OFF (WHAT WAS WRITTEN STAYS)");
                else { char *p = msg_buf; p = put_s(p, "MOTION "); p = put_u(p, x->motion_bars); p = put_s(p, x->motion_bars > 1u ? " BARS: REC + FX K" : " BAR: REC + FX K"); finish(p); status_msg(msg_buf); }
            }
            if (d2) {
                static const char *const KBM[SQ_KBS] = {"KEYBOARD: NOTES AS NOTES", "KEYBOARD: ITS NOTES TRANSPOSE THE KEY", "KEYBOARD: BELOW C3 TRANSPOSES, ABOVE PLAYS",
                                                        "KEYBOARD: ITS CHORDS ARE THE HARMONY", "KEYBOARD: CHORDS BELOW C3, ABOVE PLAYS"};
                x->kb_mode = change_u8(x->kb_mode, d2, 0u, SQ_KBS - 1u);
                if (!SQ_KB_IS_CHORD(x->kb_mode)) kb_chord_on = 0u;       /* 0.26: the harmony is the progression's again */
                status_msg(KBM[x->kb_mode]);
            }
            if (d3) { x->kb_ch = change_u8(x->kb_ch, d3, 0u, 16u); if (x->kb_ch) status_num("KEYBOARD ON CHANNEL ", x->kb_ch); else status_msg("KEYBOARD: ANY CHANNEL"); }
            if (d4) { x->in_thru = d4 > 0 ? 1u : 0u; status_msg(x->in_thru ? "MIDI IN PLAYS THE TRACK, REC OR NOT" : "MIDI IN PLAYS WITH REC ONLY"); }
            if (d1 || d2 || d3 || d4) { save_knob = 1u; ui_dirty = 1u; }
            return;
        }
        if (save_page == 2u) {                         /* 0.12 SYSTEM: the USB ports (SEL + K1: reconnect now), the button lights */
            if (d1 && (held & (1u << BTN_SEL))) usb_reconnect_ask();
            else if (d1) { usb_ports_want = d1 > 0 ? 2u : 1u; usb_ports_note(); }
            if (d2) { project.gen.panel_lights = (uint8_t)(change_u8(lights_level(), d2, 0u, LIGHTS_N - 1u) + 1u); lights_apply(); status_msg(LIGHTS_NAME[lights_level()]); }
            if (d1 || d2) { save_knob = 1u; ui_dirty = 1u; }
            return;
        }
        if (save_page) {
            if (d1) { project.live.cc_lead_ms = (uint8_t)kstep(project.live.cc_lead_ms, d1, f1, 0, (int32_t)SQ_CC_LEAD_MAX); status_num("CC LEAD MS ", project.live.cc_lead_ms); }
            if (d2) { project.live.song_tempo = d2 > 0 ? 1u : 0u; status_msg(project.live.song_tempo ? "THE SONG SETS THE TEMPO" : "THE SONG KEEPS THE TEMPO"); }
            if (d3) { uint8_t ch = track_ch(selected_track); project.device[ch] = change_u8(project.device[ch], d3, 0u, SQ_DEV_COUNT - 1u); status_msg(sq_device_name(project.device[ch])); }
            if (d4) { project.gen.lib_len = change_u8(project.gen.lib_len, d4, 0u, SQ_LLS - 1u); status_msg(project.gen.lib_len == SQ_LL_PHRASE ? "LONG PATTERNS: A PHRASE (THE NEXT ONE, A FILL)" : "LONG PATTERNS: THE PATTERN REPEATS"); }
            if (d1 || d2 || d3 || d4) { save_knob = 1u; ui_dirty = 1u; }
            return;
        }
        if (d1) { master_fn_set(change_u8(project.live.master_fn, d1, 0u, SQ_MKS - 1u)); save_knob = 1u; }
        if (d2) {                                      /* 0.9: OFF, 14, 13 + 14 (VIAGGIO on 13) */
            project.live.remote_mode = change_u8(project.live.remote_mode, d2, 0u, SQ_RMS - 1u);
            project.live.remote_ch = project.live.remote_mode == SQ_RM_OFF ? (uint8_t)SQ_REMOTE_OFF : 13u;
            status_msg(project.live.remote_mode == SQ_RM_OFF ? "REMOTE OFF: CH 13 AND 14 ARE TRACK CHANNELS" :
                       project.live.remote_mode == SQ_RM_14 ? "REMOTE ON CH 14" : "REMOTE ON CH 14 + VIAGGIO ON CH 13");
            save_knob = 1u;
            ui_dirty = 1u;
        }
        if (d4) {                                      /* 0.9: the profile */
            static const uint8_t ORD[SQ_PROFILES] = {SQ_PROF_FULL, SQ_PROF_SEMPLICE, SQ_PROF_PALCO};   /* 0.27: the knob goes FULL, SEMPLICE, PALCO */
            uint8_t k = 0u;
            while (k + 1u < SQ_PROFILES && ORD[k] != vg_profile) k++;
            vg_profile = ORD[change_u8(k, d4, 0u, SQ_PROFILES - 1u)];
            vg_profile_note();
            save_knob = 1u;
            ui_dirty = grid_dirty = 1u;
        }
        if (d3) {
            project.live.snap_tempo = d3 > 0 ? 1u : 0u;
            status_msg(project.live.snap_tempo ? "SNAPSHOTS BRING THEIR TEMPO" : "SNAPSHOTS KEEP THE TEMPO");
            save_knob = 1u;
            ui_dirty = 1u;
        }
        return;
    }

    if (dsel) {
        if (held & (1u << BTN_LFO)) { lfo_sel = change_u8(lfo_sel, dsel, 0u, SQ_LFOS - 1u); ui_dirty = 1u; }
        else if (held & (1u << BTN_SEQ)) beat_func_turn(dsel);   /* 0.11: the genre's parts, PROG, KIT */
        else select_track(change_u8(selected_track, dsel, 0u, SQ_TRACKS - 1u));
    }
    cfg = &project.track[selected_track];

    if ((held & (1u << BTN_GLO)) && !(held & (GROUPS & ~(1u << BTN_SEL)))) {   /* 0.12: GLO held: its three pages (in VIAGGIO mode too) */
        if (d1 || d2 || d3 || d4 || dalg || dp) { glo_used = 1u; selglo_pend = 0u; }
        if (dp && perf_page == 2u && !(held & (1u << BTN_SEL))) vg_prog_turn(dp);   /* 0.17 the MOSSE: PRESETS the progression, in the queue */
        else if (dp) { scene_cursor = change_u8(scene_cursor, dp, 0u, SQ_SCENES - 1u); ui_dirty = 1u; }
        if (dalg && (held & (1u << BTN_SEL))) set_bpm_to(kstep(project.bpm, dalg, fa, 30, 300));   /* SEL + ALG: the tempo */
        else if (dalg && perf_page == 2u) vg_quant_turn(dalg);           /* 0.17 the MOSSE: ALG, when the moves happen */
        glo_page_knobs(perf_page, d1, d2, d3, d4, f1, f2);
        return;
    }

    if (dalg && dice_pending && !(held & GROUPS)) { dice_browse(dalg); dalg = 0; }   /* 0.8: a dice waits: ALG the rolls */
    if (perf_mode && !(held & (GROUPS & ~(1u << BTN_SEL)))) {   /* PERF mode: GLO's pages without holding it; SEL + knobs: TRACK LIVE, as in 0.11 */
        uint8_t mosse = perf_page == 2u && !(held & (1u << BTN_SEL)) ? 1u : 0u;
        if (d1 || d2 || d3 || d4 || dalg || dp) glo_used = 1u;
        if (dp && mosse) vg_prog_turn(dp);                                 /* 0.17 the MOSSE: PRESETS the progression, in the queue */
        else if (dp) { scene_cursor = change_u8(scene_cursor, dp, 0u, SQ_SCENES - 1u); ui_dirty = 1u; }
        if (dalg && (held & (1u << BTN_SEL))) set_bpm_to(kstep(project.bpm, dalg, fa, 30, 300));   /* SEL + ALG: the tempo */
        else if (dalg && mosse) vg_quant_turn(dalg);                      /* 0.17 the MOSSE: ALG, when the moves happen */
        glo_page_knobs((held & (1u << BTN_SEL)) ? 1u : perf_page, d1, d2, d3, d4, f1, f2);
        return;
    }

    if (dp) {
        if (held & (1u << BTN_SEQ)) gen_genre_set((uint8_t)clamp_i32((int32_t)beat_genre + dp, 0, SQ_GENRES - 1));   /* SEQ + PRESETS: genre */
        else if (!vg_prop_queue(selected_track))                             /* 0.17: a proposal waiting: PRESETS queues it first */
            queue_pattern(selected_track, change_u8(tr[selected_track].pending_pattern < SQ_PATTERNS ? tr[selected_track].pending_pattern : tr[selected_track].pattern, dp, 0u, 7u));
    }
    if (dalg) {
        if (held & (1u << BTN_HOME)) set_loop_start(selected_track, change_u8(cfg->start, dalg, 0u, 63u));
        else if ((held & (1u << BTN_SEQ)) && beat_func != SQ_FUNC_PROG && th_style_now(beat_genre) != 255u) {   /* 0.23 THEORY: SEQ + ALG the seed */
            project.th.seed = (uint16_t)kstep(project.th.seed, dalg, fa, 0, (int32_t)SQ_TH_SEEDS - 1);
            ui_dirty = grid_dirty = 1u;
        }
        else if (held & (1u << BTN_SEQ)) {                                     /* SEQ + ALG: the variation (0.11: on into the Pi's) */
            uint8_t nv = sq_beat_variants(beat_genre, beat_func), npi = pipat_count(beat_genre, beat_func);
            beat_var = nv ? (uint8_t)clamp_i32((int32_t)beat_var + dalg, 0, (int32_t)nv + npi - 1) : 0u;
            if (nv && beat_var == nv - 1u && dalg > 0 && !npi && pipat_loadable(beat_func)) status_msg("THE LAST IN THE FM-1 (THE PI'S: ASKED)");
            ui_dirty = grid_dirty = 1u;
        }
        else if (held & (1u << BTN_SEL)) set_bpm_to(kstep(project.bpm, dalg, fa, 30, 300));   /* SEL + ALG: tempo */
        else cursor_to((uint8_t)kstep(cursor_step, dalg, fa, 0, 63));
    }

    s = &project.step[selected_track][tr[selected_track].pattern][cursor_step];
    if (held & (1u << BTN_HOME)) {
        if (home_page == 0u) {                                           /* TRACK: channel, length, step, transpose */
            if (d1) cfg->channel = change_u8(cfg->channel, d1, 0u, (uint8_t)(ch_limit() - 1u));
            if (d2) set_length(selected_track, (uint8_t)kstep(len_shown(selected_track), d2, f2, 1, 64));
            if (d3) set_division(selected_track, change_u8(cfg->division, d3, 0u, SQ_DIV_COUNT - 1u));
            if (d4) {                                                           /* 0.10: steps of the scale when IN KEY */
                int32_t lim = track_in_key(selected_track) ? 24 : 48;
                cfg->transpose = (int8_t)kstep(cfg->transpose, d4, f4, -lim, lim);
            }
        } else if (home_page == 1u) {                                           /* PLAY: direction, swing, octave, FOLLOW */
            if (d1) direction_set(selected_track, change_u8(cfg->direction, d1, 0u, SQ_DIR_COUNT - 1u));
            if (d2) cfg->swing = (uint8_t)kstep(cfg->swing, d2, f2, SQ_SWING_MIN, SQ_SWING_MAX);
            if (d3) cfg->octave = (int8_t)clamp_i32((int32_t)cfg->octave + d3, -3, 3);
            if (d4) follow_set(selected_track, d4 > 0 ? 1u : 0u);
        } else if (home_page == 2u) {                                           /* KEY: the slot, root, scale, shift */
            if (d1) set_key_slot(d1);
            if (d2) set_key_root(d2);
            if (d3) set_key_scale(d3);
            if (d4) set_key_shift(d4);
        } else if (home_page == 3u) {                                           /* 0.10 TRACK: mode, role, chord, key slot */
            if (d1) {                                                           /* FREE / IN KEY / DRUM / TAPE */
                set_track_mode(selected_track, change_u8(track_mode(selected_track), d1, 0u, TRACK_MODES - 1u));
                status_msg(track_mode_name(selected_track));
            }
            if (d2) { cfg->role = change_u8(cfg->role, d2, 0u, SQ_ROLE_COUNT - 1u); status_msg(sq_role_name(cfg->role)); }
            if (d3) { cfg->chord = change_u8(cfg->chord, d3, 0u, SQ_CH_COUNT - 1u); status_msg(cfg->chord ? sq_chord_shape_name(cfg->chord) : "CHORD OFF: THE NOTES AS WRITTEN"); }
            if (d4) {
                int32_t v = cfg->key_slot == SQ_KEY_FOLLOW ? -1 : (int32_t)cfg->key_slot;
                v = clamp_i32(v + d4, -1, (int32_t)SQ_KEYS - 1);
                cfg->key_slot = v < 0 ? (uint8_t)SQ_KEY_FOLLOW : (uint8_t)v;
                status_msg(v < 0 ? "KEY: FOLLOWS THE SLOT THAT PLAYS" : "KEY: PINNED TO THIS SLOT");
            }
        } else if (home_page == 4u) {                                           /* lengths per parameter, the program */
            if (d1) cfg->plen[SQ_PL_NOTE] = change_u8(cfg->plen[SQ_PL_NOTE], d1, 0u, SQ_STEPS);
            if (d2) cfg->plen[SQ_PL_VEL] = change_u8(cfg->plen[SQ_PL_VEL], d2, 0u, SQ_STEPS);
            if (d3) cfg->plen[SQ_PL_GATE] = change_u8(cfg->plen[SQ_PL_GATE], d3, 0u, SQ_STEPS);
            if (d4) {
                uint8_t ch = track_ch(selected_track), pc = project.scene[scene_cursor].pc[ch];
                int32_t v = pc > 127u ? -1 : (int32_t)pc;
                scene_pc_set(scene_cursor, ch, kstep(v, d4, f4, -1, 127));
            }
        } else if (home_page == 5u) {                                           /* the MIDI effect */
            sq_track_cfg_t *v;
            if (d1 && (held & (1u << BTN_SEL))) { mfx_order(selected_track, d1); d1 = 0; }   /* 0.20: SEL + K1 the ORDER */
            if (d1) mfx_choose(selected_track, change_u8(mfx_shown(selected_track), d1, 0u, SQ_MFXS - 1u));   /* 0.16: READY; 0.19: the one shown */
            v = mfx_view(selected_track);                                       /* (the shown effect's values, READY or playing) */
            if (d2) mfx_amount(v, d2);
            if (d2 && v->mfx == SQ_MFX_CHANCE) {                                /* 0.27: CHANCE says who it works on */
                char *p = msg_buf;
                p = put_s(p, "T"); p = put_u(p, (uint32_t)selected_track + 1u); p = put_s(p, " CHANCE "); p = put_u(p, (uint32_t)(uint8_t)v->mfx_amt); p = put_s(p, "%: THIS TRACK ONLY"); finish(p);
                status_msg(msg_buf);
            }
            if (d3) mfx_knob34(v, 1u, d3, f3);
            if (d4) mfx_knob34(v, 2u, d4, f4);
            if (d2 || d3 || d4) {
                mfx_keep(selected_track, v);
                if (mfx_on(selected_track, v->mfx)) mfx_pend[selected_track] = 0u;   /* 0.19: changed live, not taken out */
            }
        } else if (home_page == 7u) {                                           /* 0.13 CHAIN LIST */
            chain_knobs(d1, d2, d3, d4);
        } else if (home_page == 6u) {                                           /* 0.10 TIMING: the synth's latency; CHAIN; the tape */
            if (d1) cfg->delay_ms = (int8_t)kstep(cfg->delay_ms, d1, f1, -SQ_DELAY_MAX, SQ_DELAY_MAX);
            if (d2) chain_mode_set(selected_track, change_u8(chain_mode(selected_track), d2, 0u, 2u));   /* 0.13: OFF, PAIR, LIST */
            if (track_tape(selected_track)) {                                   /* a TAPE track: its loop and quantise */
                if (d3) { cfg->tape.bars = (uint8_t)kstep(cfg->tape.bars, d3, 1, 1, (int32_t)SQ_TAPE_BARS_MAX); sq_tape_sanitize(&project); }
                if (d4) cfg->tape.quant = (uint8_t)kstep(cfg->tape.quant, d4, 10, 0, 100);
            } else {                                                            /* 0.15 GROOVE: the template, how much */
                if (d3) groove_set(selected_track, change_u8(project.ext.track[selected_track].groove, d3, 0u, SQ_GROOVES - 1u));
                if (d4) groove_amount(selected_track, kstep(project.ext.track[selected_track].groove_amt, d4, 5 * f4, 0, 100));
            }
        }
        if (d1 || d2 || d3 || d4) ui_dirty = grid_dirty = 1u;
    } else if ((held & (1u << BTN_EDIT)) && (held & (1u << BTN_SEL))) {   /* 0.12 EDIT + SEL: the four notes of the step, one a knob */
        int32_t dn[4] = {d1, d2, d3, d4}, fn[4] = {f1, f2, f3, f4};
        uint32_t k;
        for (k = 0; k < 4u; k++) if (dn[k]) step_note_turn(selected_track, s, k, dn[k] * fn[k]);
        if (d1 || d2 || d3 || d4) ui_dirty = grid_dirty = 1u;
    } else if (held & (1u << BTN_EDIT)) {
        if (d1) s->length = (uint8_t)clamp_i32((int32_t)s->length + d1 * f1, 1, SQ_GATE_LONG_MAX);
        if (d2) s->condition = change_u8(s->condition, d2, 0u, SQ_COND_COUNT - 1u);
        if (d3) s->nudge = (int8_t)kstep(s->nudge, d3, f3, -(int32_t)SQ_NUDGE_MAX, (int32_t)SQ_NUDGE_MAX);
        if (d4) s->ramp = (int8_t)kstep(s->ramp, d4, 5 * f4, -100, 100);
        if (d1 || d2 || d3 || d4) {
            if (d2 || d3 || d4 || !cfg->plen[SQ_PL_GATE]) step_activate(selected_track, s);   /* (a gate of a gate loop: not a hit) */
            ui_dirty = grid_dirty = 1u;
        }
    } else if (held & (1u << BTN_ENV)) {                                      /* 0.10: one lane a page: value on the step, CC, base, mode */
        uint32_t n = env_lane < SQ_LANES ? env_lane : 0u;
        if (d1) {                                                             /* the lock on the cursor step (from the base, or 64) */
            int32_t x = s->lane[n] == SQ_LANE_NONE ? -1 : (int32_t)s->lane[n];
            uint8_t was = s->lane[n];
            if (x < 0 && d1 > 0) x = kstep(cfg->lane_base[n] != SQ_LANE_NONE ? (int32_t)cfg->lane_base[n] : 64, d1 - 1, f1, 0, 127);
            else if (x >= 0) x = kstep(x, d1, f1, -1, 127);                   /* (a detent under 0 takes the lock away) */
            s->lane[n] = x < 0 ? SQ_LANE_NONE : (uint8_t)x;
            if (s->lane[n] != was) s->flags |= SQ_STEP_SET;                   /* (a lock does not light the step: TRIGLESS sends it; 0.27: a turn
                                                                                 that writes nothing leaves the step as it was - a copy stays one) */
            if (record_arm && playing) lane_rec[selected_track] |= (uint8_t)(1u << n);   /* REC: the knob writes the steps as they play */
            if (record_arm && playing && x >= 0) lane_rec_val[selected_track][n] = (uint8_t)x;
            lane_rec_ms = fm1_ms;
        }
        if (d2 && (held & (1u << BTN_SEL))) cfg->lane_hi[n] = (uint8_t)kstep(cfg->lane_hi[n], d2, f2, 0, 127);   /* NRPN: the MSB */
        else if (d2) {
            int32_t x = cfg->lane_cc[n] == SQ_LANE_NONE ? -1 : (int32_t)cfg->lane_cc[n];
            x = kstep(x, d2, f2, -1, (int32_t)SQ_CC_MAX);                      /* (128 BEND, 129 AFTERTOUCH) */
            cfg->lane_cc[n] = x < 0 ? SQ_LANE_NONE : (uint8_t)x;
        }
        if (d3) {                                                             /* the base: from 64 when there is none */
            int32_t x = cfg->lane_base[n] == SQ_LANE_NONE ? -1 : (int32_t)cfg->lane_base[n];
            if (x < 0 && d3 > 0) x = kstep(64, d3 - 1, f3, 0, 127);
            else if (x >= 0) x = kstep(x, d3, f3, -1, 127);
            cfg->lane_base[n] = x < 0 ? SQ_LANE_NONE : (uint8_t)x;
            if (x >= 0) lane_send(selected_track, n, lane_val((uint8_t)n, (uint8_t)x));
        }
        if (d4) {                                                             /* the mode: NORMAL, SLIDE, TRIGLESS, SLIDE+TRIGLESS, NRPN ... */
            uint8_t m = cfg->lane_flags[n] & 7u;
            m = change_u8(m, d4, 0u, 7u);
            cfg->lane_flags[n] = m;
            status_msg((m & SQ_LF_NRPN) ? "NRPN: K2 THE LSB, LANE HI (SEL+K2) THE MSB" : (m & SQ_LF_SLIDE) ? "SLIDE: THE VALUE GLIDES TO THE NEXT LOCK" : (m & SQ_LF_TRIGLESS) ? "TRIGLESS: A LOCK IS SENT ON A SILENT STEP TOO" : "LANE NORMAL");
        }
        if (d1 || d2 || d3 || d4) ui_dirty = grid_dirty = 1u;
    } else if (held & (1u << BTN_LFO)) {
        sq_lfo_t *l = &project.lfo[lfo_sel];
        if (lfo_page == 0u) {
            if (d1) l->shape = change_u8(l->shape, d1, 0u, SQ_LFO_SHAPES - 1u);
            if (d2) l->rate = change_u8(l->rate, d2, 0u, SQ_LFO_RATES - 1u);
            if (d3) l->depth = (uint8_t)kstep(l->depth, d3, f3, 0, 127);
            if (d4) l->center = (uint8_t)kstep(l->center, d4, f4, 0, 127);
        } else if (lfo_page == 1u) {
            if (d1) { l->dest = change_u8(l->dest, d1, 0u, SQ_LD_ALL - 1u); lfo_target_fit(l); }   /* 0.20: + MOD ONLY */
            if (d2) l->target = change_u8(l->target, d2, 0u, l->dest == SQ_LD_CC ? (uint8_t)(ch_limit() - 1u) : SQ_TRACKS - 1u);
            if (d3) l->param = (uint8_t)kstep(l->param, d3, f3, 0, (int32_t)SQ_CC_MAX);
            if (d4) l->phase = (uint8_t)kstep(l->phase, d4, f4, 0, 127);
        } else if (lfo_page == 2u) {
            sq_lfox_t *x = &project.ext.lfo[lfo_sel];
            if (d1) l->enabled = d1 > 0 ? 1u : 0u;
            if (d2) l->flags = d2 > 0 ? (uint8_t)(l->flags | SQ_LF_RETRIG) : (uint8_t)(l->flags & ~SQ_LF_RETRIG);
            if (d3) l->flags = d3 > 0 ? (uint8_t)(l->flags | SQ_LF_INVERT) : (uint8_t)(l->flags & ~SQ_LF_INVERT);
            if (d4) {                                                         /* 0.13 TRIG: the clock, or a track's hits */
                x->trig = change_u8(x->trig, d4, 0u, SQ_TRACKS);
                if (x->trig) { char *p = msg_buf; p = put_s(p, "TRIG: T"); p = put_u(p, x->trig); p = put_s(p, " HITS START IT (DECAY+INVERT: DUCK)"); finish(p); status_msg(msg_buf); }
                else status_msg("TRIG: THE CLOCK");
            }
        } else if (lfo_page == LFO_PAGE_ENV) {                                /* 0.20 ENV: ATTACK, DECAY, SUSTAIN, RELEASE */
            sq_lfoe_t *e = &project.ext.lfoe[lfo_sel];
            if (d1) e->a = change_u8(e->a, d1, 0u, SQ_ENV_TIMES - 1u);
            if (d2) e->d = change_u8(e->d, d2, 0u, SQ_ENV_TIMES - 1u);
            if (d3) e->s = (uint8_t)kstep(e->s, d3, 5 * f3, 0, 100);
            if (d4) e->r = change_u8(e->r, d4, 0u, SQ_ENV_TIMES - 1u);
            if ((d1 || d2 || d3 || d4) && l->shape != SQ_LFO_ENV) status_msg("ENV: SHAPE ENV ON PAGE 1 MAKES IT PLAY");
        } else if (lfo_page == LFO_PAGE_MOD) {                                /* 0.20 MOD MATRIX: slot, source, destination, amount */
            sq_mod_t *m;
            uint8_t sel = (held & (1u << BTN_SEL)) ? 1u : 0u;
            if (d1) mod_slot = change_u8(mod_slot, d1, 0u, SQ_MODS - 1u);
            m = &project.ext.mod[mod_slot];
            if (d2 && sel) m->src_i = (uint8_t)kstep(m->src_i, d2, m->src == SQ_MS_CCIN ? f2 : 1, 0, sq_mod_src_count(m->src) - 1);   /* SEL + K2: which one */
            else if (d2) { m->src = change_u8(m->src, d2, 0u, SQ_MSS - 1u); if (m->src_i >= sq_mod_src_count(m->src)) m->src_i = 0u; }
            if (d3 && sel) m->dst_i = change_u8(m->dst_i, d3, 0u, (uint8_t)(sq_mod_dst_count(m->dst) - 1u));   /* SEL + K3: which one */
            else if (d3) { m->dst = change_u8(m->dst, d3, 0u, SQ_MDS - 1u); if (m->dst_i >= sq_mod_dst_count(m->dst)) m->dst_i = 0u; }
            if (d4) m->amt = (int8_t)kstep(m->amt, d4, 5 * f4, -100, 100);
        } else {                                                              /* 0.13 RATE SEQ: STEPS, EVERY, the entry, its rate */
            sq_lfox_t *x = &project.ext.lfo[lfo_sel];
            if (d1) {
                int32_t v = (int32_t)(x->seq_n < 2u ? 0u : x->seq_n) + d1;
                v = clamp_i32(v, 0, SQ_RSEQ_MAX);
                if (v == 1) v = d1 > 0 ? 2 : 0;                              /* (one rate is no sequence) */
                x->seq_n = (uint8_t)v;
                if (rseq_pos >= (x->seq_n ? x->seq_n : 1u)) rseq_pos = 0u;
            }
            if (d2) x->seq_every = change_u8(x->seq_every, d2, 0u, SQ_RES - 1u);
            if (d3) rseq_pos = change_u8(rseq_pos, d3, 0u, (uint8_t)((x->seq_n >= 2u ? x->seq_n : SQ_RSEQ_MAX) - 1u));
            if (d4) {
                uint8_t r = x->seq_rate[rseq_pos & 7u] < SQ_LFO_RATES ? x->seq_rate[rseq_pos & 7u] : l->rate;
                x->seq_rate[rseq_pos & 7u] = change_u8(r, d4, 0u, SQ_LFO_RATES - 1u);
            }
        }
        if (d1 || d2 || d3 || d4) { lfo_last_valid[lfo_sel] = 0u; ui_dirty = 1u; }
    } else if (held & (1u << BTN_ARP)) {                                  /* 0.12: 1 ARP, 2 CHORD, 3 HARMONY, 4 HARMONY 2, 5 USER PROG, 6 USER PROG 2 */
        uint8_t m = SQ_CHORD_MODE(cfg->chord_mode);
        uint8_t t = selected_track;
        sq_gen_t *g = &project.gen;
        if (arp_page == 2u) {                                                 /* HARMONY: OFF / ON / LOCK, the progression, bars a chord, FOLLOW */
            if (d1) harm_state_set(change_u8(harm_state(), d1, 0u, 2u));
            if (d2) harm_prog_turn(d2);
            if (d3) harm_bars_turn(d3);
            if (d4) follow_set(t, d4 > 0 ? 1u : 0u);
        } else if (arp_page == 3u) {                                          /* HARMONY 2: FOLLOW's way, the harmony's genre, the mood, the rhythm */
            if (d1) follow_mode_set(t, change_u8(cfg->follow_mode, d1, 0u, SQ_FMS - 1u));
            if (d2) harm_genre_turn(d2);                                      /* 0.16: FREE, then the genres */
            if (d3) harm_mood_set(change_u8(g->harm_mood, d3, 0u, SQ_MOODS - 1u));
            if (d4) harm_rhythm_set(change_u8(g->harm_rhythm, d4, 0u, SQ_HRS - 1u));
        } else if (arp_page == 4u) {                                          /* USER PROG: which, the chord, its root, its shape */
            sq_uprog_t *u = &project.uprog[uprog_sel];
            if (d1) { uprog_sel = change_u8(uprog_sel, d1, 0u, SQ_UPROG_SLOTS - 1u); uprog_pos = 0u; uprog_note(); }
            if (d2) { uprog_pos = change_u8(uprog_pos, d2, 0u, 7u); uprog_note(); }
            if (d3) uprog_root_turn(u, d3);
            if (d4 && uprog_pos < u->n) uprog_shape_turn(u, d4);
        } else if (arp_page == 5u) {                                          /* USER PROG 2: its mood, the lengths of a rhythm, the chord's length, its push */
            sq_uprog_t *u = &project.uprog[uprog_sel];
            if (d1) { u->mood = change_u8(u->mood, d1, 0u, SQ_MOODS - 1u); { char *p = msg_buf; p = put_s(p, "MOOD "); p = put_s(p, u->mood ? sq_mood_name(u->mood) : "GUESSED"); if (!u->mood && u->n) { sq_hprog_t h; sq_hprog_user(&h, u, 0u, SQ_HR_BARS); p = put_s(p, ": "); p = put_s(p, sq_mood_name(sq_hprog_mood(&h, project.key_scale))); } finish(p); status_msg(msg_buf); } }
            if (d2) uprog_rhythm_turn(u, d2);
            if (d3 && uprog_pos < u->n) { u->dur[uprog_pos] = (uint8_t)clamp_i32((int32_t)u->dur[uprog_pos] + d3 * f3, 0, 64); uprog_note(); }
            if (d4 && uprog_pos < u->n) { u->push[uprog_pos] = change_u8(u->push[uprog_pos], d4, 0u, 4u); uprog_note(); }
        } else if (arp_page == 0u) {                                                 /* ARP: mode, octaves, RATE, RUN */
            if (d1) {
                m = change_u8(m, d1, 0u, SQ_CHORD_COUNT - 1u);
                if (m != SQ_CHORD_BLOCK) arp_last[selected_track] = m;
                chord_set(m, SQ_CHORD_OCTS(cfg->chord_mode));
            }
            if (d2) chord_set(m, change_u8(SQ_CHORD_OCTS(cfg->chord_mode), d2, 1u, 3u));
            if (d3) {                                                         /* 0.18: 1/4, 1/2, ROLL, 1, 2, 3, 4 */
                cfg->arp_rate = arp_rate_at((uint8_t)clamp_i32((int32_t)arp_rate_pos(cfg->arp_rate) + d3, 0, SQ_ARP_RATE_MAX));
                status_msg(!cfg->arp_rate ? "ARP ROLL: THE CHORD INSIDE THE STEP" : SQ_ARP_EVERY(cfg->arp_rate) > 1u ? (cfg->arp_rate == SQ_ARP_R_HALF ? "ARP RATE 1/2: A NOTE EVERY 2 STEPS" : "ARP RATE 1/4: A NOTE EVERY 4 STEPS") : "ARP RATE: NOTES A STEP (RUNS ON)");
            }
            if (d4) {                                                         /* RUN: OFF, RETRIG, HOLD, HOLD+RETRIG */
                uint8_t r = (uint8_t)(((cfg->arp_flags & SQ_AF_HOLD) ? 2u : 0u) | ((cfg->arp_flags & SQ_AF_RETRIG) ? 1u : 0u));
                r = change_u8(r, d4, 0u, 3u);
                cfg->arp_flags = (uint8_t)((cfg->arp_flags & ~(SQ_AF_HOLD | SQ_AF_RETRIG)) | ((r & 2u) ? SQ_AF_HOLD : 0u) | ((r & 1u) ? SQ_AF_RETRIG : 0u));
                status_msg(r == 3u ? "HOLD + RETRIG: RUNS ON, A NEW CHORD STARTS IT OVER" : r == 2u ? "HOLD: THE ARPEGGIO RUNS ON TO THE NEXT CHORD" : r == 1u ? "RETRIG: A NEW CHORD STARTS IT FROM ITS FIRST NOTE" : "RUN OFF: THE ARPEGGIO STOPS WITH ITS GATE");
            }
        } else {                                                              /* CHORD: shape, key, voicing, strum */
            if (d1) { cfg->chord = change_u8(cfg->chord, d1, 0u, SQ_CH_COUNT - 1u); status_msg(cfg->chord ? sq_chord_shape_name(cfg->chord) : "CHORD OFF: THE NOTES AS WRITTEN"); }
            if (d2) { cfg->chord_key = change_u8(cfg->chord_key, d2, 0u, SQ_CK_COUNT - 1u); status_msg(cfg->chord_key == SQ_CK_STRICT ? "STRICT: THE SHAPE, NOTES OUT OF THE KEY SILENT" : cfg->chord_key == SQ_CK_FREE ? "FREE: THE SHAPE AS IT IS, OUT OF THE KEY TOO" : "DIATONIC: THE CHORD BUILT ON THE SCALE"); }
            if (d3) cfg->voicing = change_u8(cfg->voicing, d3, 0u, SQ_VOICES - 1u);
            if (d4) cfg->strum = (int8_t)kstep(cfg->strum, d4, 5 * f4, -50, 50);
        }
        if (d1 || d2 || d3 || d4) ui_dirty = grid_dirty = 1u;
    } else if (held & (1u << BTN_FX)) {                                   /* the macros; 0.12: with SEL the THROWS (they spring back) */
        uint8_t th = (held & (1u << BTN_SEL)) ? 1u : 0u;
        if (d1) { macro_set(0u, kstep(mac_vel, d1, f1, -63, 63)); throw_mark(0u, th); }
        if (d2) { macro_set(1u, kstep(mac_gate, d2, 5 * f2, -90, 100)); throw_mark(1u, th); }
        if (d3) { macro_set(2u, kstep(mac_swing, d3, f3, -25, 25)); throw_mark(2u, th); }
        if (d4) { macro_set(3u, kstep(mac_filt, d4, 2 * f4, -64, 63)); throw_mark(3u, th); }
    } else if (held & (1u << BTN_SEQ)) {                                  /* the generators, eight pages */
        sq_gen_t *g = &project.gen;
        uint8_t t = selected_track;
        if (seq_page == 0u) {                                             /* EUCLID (live, this track): pulses, rotation, family; HEAT */
            if (d1) { cfg->euc_pulses = (uint8_t)clamp_i32((int32_t)cfg->euc_pulses + d1, 1, cfg->length - cfg->start); euclid_touch(t); }
            if (d2) { cfg->euc_rot = (uint8_t)clamp_i32((int32_t)cfg->euc_rot + d2, 0, cfg->length - cfg->start - 1); euclid_touch(t); }
            if (d3) {                                             /* 0.23.1: the family says what its knobs do */
                static const char *const FAM[SQ_RF_COUNT] = {"EUCLID: K1 HITS SPREAD EVENLY, K2 TURNS THEM", "TRESILLO: K1 HITS IN 3-3-2, K2 TURNS THEM",
                                                             "NUMERIC: K1 PICKS 1 OF 16 RHYTHMS, K2 TURNS IT"};
                cfg->euc_fam = change_u8(cfg->euc_fam, d3, 0u, SQ_RF_COUNT - 1u); euclid_touch(t);
                status_msg(FAM[cfg->euc_fam < SQ_RF_COUNT ? cfg->euc_fam : 0u]);
            }
            if (d4) g->heat = (uint8_t)kstep(g->heat, d4, 5 * f4, 1, 100);
        } else if (seq_page == 1u) {                                      /* the ALGORITHMS of this track: 0.11 four slots, SEL + K1 picks one */
            if (d1 && (held & (1u << BTN_SEL))) algo_slot_select(t, change_u8(algo_cur[t], d1, 0u, SQ_ALGO_SLOTS - 1u));
            else if (d1) algo_choose(t, change_u8(algo_shown(t), d1, 0u, SQ_ALGOS - 1u));   /* 0.16: READY, not yet playing */
            if (d2 || d3 || d4) algo_turn(t, d2, d3, d4, f2, f3, f4);
        } else if (seq_page == 2u) {                                      /* EVOLVE, and the scope */
            if (d1) gen_targets_set(change_u8(gen_target_index(), d1, 0u, GEN_TARGET_SETS - 1u));
            if (d2 && (held & (1u << BTN_SEL))) evo_return_turn(d2, f2);   /* 0.27: SEL + K2, the RETURN (0: DRIFT) */
            else if (d2) g->evo_amount = (uint8_t)kstep(g->evo_amount, d2, 5 * f2, 1, 100);
            if (d3) g->evo_every = change_u8(g->evo_every, d3, 0u, SQ_EVO_EVERY - 1u);
            if (d4) gen_scope_set(change_u8(g->scope, d4, 0u, SQ_SCOPES - 1u));
        } else if (seq_page == 3u || seq_page == 4u) {                    /* 0.10 EXPO, two pages (this track) */
            sq_expo_t *x = &cfg->expo;
            if (seq_page == 3u) {
                if (d1) x->hits = (uint8_t)clamp_i32((int32_t)x->hits + d1, (int32_t)SQ_X_HITS_MIN, (int32_t)SQ_X_HITS_MAX);
                if (d2) x->curve = (int8_t)kstep(x->curve, d2, f2, -8, 8);
                if (d3) x->span = change_u8(x->span, d3, 0u, SQ_X_SPANS - 1u);
                if (d4) x->shape = change_u8(x->shape, d4, 0u, SQ_X_SHAPES - 1u);
                if ((d1 || d2 || d3) && x->shape == SQ_XS_OFF) status_msg("EXPO READY: K4 SHAPE STARTS IT");   /* 0.16: set up, not on (0.10-0.15: on, RAMP) */
            } else {
                if (d1) x->vel = change_u8(x->vel, d1, 0u, SQ_X_VELS - 1u);
                if (d2) x->gate = (uint8_t)kstep(x->gate, d2, 5 * f2, 5, 100);
                if (d3) x->jitter = (uint8_t)kstep(x->jitter, d3, 5 * f3, 0, 50);
                if (d4) x->notes = change_u8(x->notes, d4, 0u, SQ_X_NOTES - 1u);
            }
            /* (a span playing finishes as it was; the new settings take the next one) */
        } else if (seq_page == 5u) {                                      /* 0.10 TOOLS: density, WHEN, EVERY, GENRE mode */
            if (d1) g->density = (uint8_t)kstep(g->density, d1, 5 * f1, 0, 100);
            if (d2) { g->when = change_u8(g->when, d2, 0u, SQ_WHENS - 1u); status_msg(g->when ? "TOOLS WAIT FOR THE BAR LINE" : "TOOLS APPLY AT ONCE"); }
            if (d3) { g->every = change_u8(g->every, d3, 0u, SQ_EVERYS - 1u); every_arm(); }
            if (d4) { g->genre_mode = change_u8(g->genre_mode, d4, 0u, SQ_GMS - 1u); genre_mode_note(); }
        } else if (seq_page == 6u) {                                      /* 0.12 BREAK: the chop, the rolls, how much the dice swaps, the slices */
            break_knobs(t, d1, d2, d3, d4, f2, f3);
        } else {                                                          /* 0.23 THEORY: the source, the next seed; this track's seed and variation */
            th_knobs(t, d1, d2, d3, d4, f2, f3);
        }
        if (d1 || d2 || d3 || d4) ui_dirty = grid_dirty = 1u;
    } else if (held & (1u << BTN_SEL)) {                                  /* the mix of the track */
        if (d1) cfg->vel_offset = (int8_t)kstep(cfg->vel_offset, d1, f1, -63, 63);
        if (d2) cfg->hum_time = (uint8_t)kstep(cfg->hum_time, d2, f2, 0, SQ_NUDGE_MAX);
        if (d3) cfg->hum_vel = (uint8_t)kstep(cfg->hum_vel, d3, f3, 0, 50);
        if (d4) { PEN(selected_track) = change_u8(PEN(selected_track), d4 * f4, 0u, 127u); status_note("PEN ", PEN(selected_track)); }
        if (d1 || d2 || d3 || d4) ui_dirty = grid_dirty = 1u;
    } else {
        if (d1) {                                                         /* 0.10: the note, lit or not; a new step starts from the pen */
            uint8_t base = (s->flags & SQ_STEP_SET) && s->note[0] != SQ_NOTE_NONE ? s->note[0] : PEN(selected_track);
            s->note[0] = change_u8(base, d1 * f1, 0u, 127u);
            s->flags |= SQ_STEP_SET;
            if (!track_drum(selected_track)) PEN(selected_track) = s->note[0];
            if (!(s->flags & SQ_STEP_ON)) preview_note(selected_track, s->note[0]);
            regia_touched(selected_track);
        }
        if (d2) s->velocity = (uint8_t)kstep(s->velocity, d2, f2, 1, 127);
        if (d3) s->chance = (uint8_t)kstep(s->chance, d3, f3, 0, 100);
        if (d4) s->ratchet = change_u8(s->ratchet, d4, 1u, SQ_RATCHET_MAX);
        if (d1 || d2 || d3 || d4) {
            /* a velocity of a loop of its own is not a hit: the step stays as it is (a note never lights a step: 0.10) */
            if (d3 || d4 || (d2 && !cfg->plen[SQ_PL_VEL])) step_activate(selected_track, s);
            ui_dirty = grid_dirty = 1u;
        }
    }
}

static void rec_toggle(void)
{
    record_arm ^= 1u;
    srec_next = 0u;                                /* step recording starts on the cursor step */
    if (record_arm && !playing) status_msg(track_drum(selected_track) ? "STEP REC: WHITE KEYS = DRUMS" : "STEP REC: FROM THE CURSOR");
}

/* ---- the backlight of the 14 buttons: always lit dimly, so their names can be read; a button that is held or
 * whose function is on is lit fully. HOME + EDIT (0.12: SAVE 3 K2 too): OFF, LOW, MID, HIGH (the default), MAX. Kept in
 * the project (project.gen.panel_lights, 0 = never set). */
static uint8_t lights_level(void)
{
    uint8_t v = project.gen.panel_lights;
    return (v && v <= LIGHTS_N) ? (uint8_t)(v - 1u) : 3u;
}
static void lights_apply(void)
{
#ifndef DINGHY_HOST
    static const uint16_t NS[LIGHTS_N] = {0u, 1000u, 2000u, 4000u, 6000u};   /* the pulse a frame (ns): a lit LED ~95 us */
    uint32_t p, r;
    uint8_t lvl = lights_level();
    for (p = 0; p < FM1_NCOL; p++) {
        uint8_t m = 0u;
        for (r = 1; r < 5u; r++)
            if (lvl && FM1_KEYMAP[r][p] >= 0 && FM1_KEYMAP[r][p] < 14) m |= (uint8_t)(1u << r);
        fm1_led_bg[p] = m;
    }
    fm1_led_bg_ns = NS[lvl];
#endif
}
static void lights_next(void)
{
    char *p = msg_buf;
    uint8_t lvl = (uint8_t)((lights_level() + 1u) % LIGHTS_N);
    project.gen.panel_lights = (uint8_t)(lvl + 1u);
    lights_apply();
    p = put_s(p, "BUTTON LIGHTS "); p = put_s(p, LIGHTS_NAME[lvl]); finish(p);
    status_msg(msg_buf);
}

/* ---- SAVE 3 SYSTEM: the USB page; SEL + K1 twice: the FM-1 drops off the USB and comes back (as pulling the cable) */
static uint8_t usbrc_ask;
static uint32_t usbrc_until;
static uint8_t usb_cfg_seen, usb_cfg_last;
/* the FM-1's own settings (not the project's): the USB ports. One flash sector, saved only when they change */
typedef struct { uint8_t ver, usb_ports, profile, reserved[5]; } sq_settings_t;   /* 0.9: ver 2 adds the profile */
static void settings_store(void)
{
    sq_settings_t st;
    if (tst_booted) return;                            /* (0.11: the PC test writes nothing) */
    memset(&st, 0, sizeof st);
    st.ver = 2u; st.usb_ports = usb_ports; st.profile = vg_profile;
    if (playing) transport_stop();                     /* (a sector erase keeps the interrupts off ~45 ms) */
    settings_save(&st, sizeof st);
}
static void settings_restore(void)
{
    sq_settings_t st;
    if (settings_load(&st, sizeof st) == 0 && (st.ver == 1u || st.ver == 2u)) {
        if (st.usb_ports == 2u) usb_ports = 2u;
        if (st.ver == 2u && st.profile < SQ_PROFILES) vg_profile = st.profile;
    }
    usb_ports_want = usb_ports;
    if (usb_ports > 1u) usb_set_ports(usb_ports);     /* (app_usb_early did it before the host looked: the same) */
}
/* platform.c, before usb_start: the host sees one or two ports from the first moment (no reconnect at power-on) */
static void app_usb_early(void)
{
    sq_settings_t st;
    if (settings_load(&st, sizeof st) == 0 && st.ver == 1u && st.usb_ports == 2u) usb_set_ports(2u);
}
/* 0.8: the control port: the grid, the remote, the Pi's SysEx (port 2 with two ports, else the only one) */
#define CTL_CABLE (usb_ports > 1u ? 1u : 0u)
static void ctl_send(uint32_t st, uint32_t d1, uint32_t d2) { midi_send_c(CTL_CABLE, st, d1, d2); }
static void usb_ports_note(void)
{
    if (usb_ports_want == usb_ports) status_msg(usb_ports > 1u ? "USB: 2 PORTS (GRID ON PORT 2), AS NOW" : "USB: 1 PORT, AS NOW");
    else status_msg(usb_ports_want > 1u ? "USB 2 PORTS AT THE RECONNECT: SEL + K1 TWICE" : "USB 1 PORT AT THE RECONNECT: SEL + K1 TWICE");
    ui_dirty = 1u;
}
static void usb_reconnect_ask(void)
{
    if (usbrc_ask && !time_due(fm1_ms, usbrc_until)) {
        usbrc_ask = 0;
        panic_all();
        if (usb_ports_want != usb_ports) {             /* 0.8: one or two ports, as the USB page says */
            usb_ports = usb_ports_want;
            usb_set_ports(usb_ports);
            settings_store();
        }
        usb_reconnect();
        status_msg("USB OFF, BACK IN A MOMENT");
    } else {
        usbrc_ask = 1;
        usbrc_until = fm1_ms + 3000u;
        status_msg("RECONNECT USB? SEL + K1 AGAIN");
    }
}
/* every 30 ms: the host has configured the FM-1 again (a reconnect, a sleep, a new cable): no note stays on there */
static void usb_watch(void)
{
    sq_usb_stats_t u;
    uint32_t ch;
    usb_stats(&u);
    if (u.config && !usb_cfg_last && usb_cfg_seen)
        for (ch = 0; ch < ch_limit(); ch++) midi_send(0xB0u | ch, 123u, 0u);
    if (u.config) usb_cfg_seen = 1u;
    usb_cfg_last = u.config;
}

static void handle_buttons(void)
{
    uint32_t rel, b = fm1_input_edges(&rel), held;
    if (tst_hands(b)) b = 0u;                                  /* 0.11: SEL says yes to the PC test, a hand stops it */
    b |= tst_edges; tst_edges = 0u;
    held = in_held();
    rel = prev_held & ~held;                                   /* (released: from the held bits, the same on the host) */
    prev_held = held;
    win_buttons(b, rel, held);                                 /* 0.12: a tap on a group button opens / closes its window */
    if ((b & (1u << BTN_EDIT)) && (held & (1u << BTN_HOME))) lights_next();   /* HOME + EDIT: the button lights */
    if (b & (1u << BTN_SAVE)) save_pressed();                  /* (0.15: before REC: SAVE + REC pressed in one pass is a CLEAR) */
    if (b & (1u << BTN_PLAY)) {
        if (held & (1u << BTN_HOME)) {                         /* HOME + PLAY: master / slave clock */
            if (playing) transport_stop();
            project.clock_mode ^= 1u;
            knob_live = 0u; knob_ref = fm1_knob;
            status_msg(project.clock_mode == SQ_CLOCK_MASTER ? "CLOCK MASTER" : "CLOCK SLAVE (EXT)");
        } else if (held & (1u << BTN_SEL)) {                   /* SEL + PLAY: carry on from where it stopped (0.17: on the MOSSE, the seed) */
            if (vg_mosse_shown() && !playing) vg_seed();
            else if (!playing) transport_continue();
        } else if (playing) transport_stop();
        else transport_start_ask();                            /* (0.26: after the COUNT IN, when REC is on and one is asked) */
    }
    if (b & (1u << BTN_REC)) {
        rec_used = 1u;
        if (held & (1u << BTN_ENV)) learn_arm(1u, selected_track, env_lane);  /* ENV + REC: LEARN the lane's CC */
        else if ((held & (1u << BTN_LFO)) && lfo_page == LFO_PAGE_MOD) learn_arm(3u, 0u, mod_slot);   /* 0.20: the MOD slot's CC IN */
        else if (held & (1u << BTN_LFO)) learn_arm(2u, 0u, lfo_sel);        /* LFO + REC: LEARN the LFO's CC */
        else if (held & (1u << BTN_HOME)) tap_tempo();                      /* HOME + REC: tap tempo */
        else if (held & (1u << BTN_SEL)) { rec_quant ^= 1u; status_msg(rec_quant ? "REC QUANTISED" : "REC FREE (KEEPS TIMING)"); }
        else if (held & (1u << BTN_SAVE)) { save_knob = 1u; store_tap_clear(); }        /* 0.15 SAVE + REC: clear the slot (asks twice) */
        else { rec_down_ms = fm1_ms; rec_used = 0u; }                       /* 0.12: a tap arms (at the release), a hold is TAKE */
        ui_dirty = 1u;
    }
    if ((held & (1u << BTN_REC)) && !rec_used && (uint32_t)(fm1_ms - rec_down_ms) >= 600u) { rec_used = 1u; take_apply(selected_track); ui_dirty = 1u; }
    if ((rel & (1u << BTN_REC)) && !rec_used) { rec_used = 1u; rec_toggle(); ui_dirty = 1u; }
    if (b & (1u << BTN_GLO)) {                                  /* PERF: a tap = the mode on / off (held: its pages, the PERF keys) */
        glo_down_ms = fm1_ms; glo_used = 0u;
        if (held & (1u << BTN_HOME)) { song_toggle(); glo_used = 1u; }                        /* HOME + GLO: the song on / off */
        else if (held & (1u << BTN_SEL)) { selglo_pend = 1u; glo_used = 1u; }                 /* 0.17 SEL + GLO: the MOSSE (PERF page 3) on / off */
        ui_dirty = grid_dirty = 1u;
    }
    if (rel & (1u << BTN_GLO)) {
        if (selglo_pend) { selglo_pend = 0u; vg_panel_toggle(); }
        else if (!glo_used && (uint32_t)(fm1_ms - glo_down_ms) < 600u) {
            perf_mode ^= 1u;
            if (perf_mode) win_close();                         /* 0.12: PERF is GLO's window: the one open goes */
        }
        glo_used = 1u;
        ui_dirty = grid_dirty = 1u;
    }
    if ((b & (1u << BTN_SEQ)) && vg_edit_keys()) { perf_mode = 0u; ui_dirty = grid_dirty = 1u; }   /* (0.17: PALCO has no SEQ: its MOSSE stay) */
    if (b & (1u << BTN_ARP)) {                                  /* ARP: a tap = its window (0.12; SEL + ARP: the arpeggio on / off) */
        if (held & (1u << BTN_HOME)) key_bake();                /* HOME + ARP: bake the key (asks twice) */
        else if (held & (1u << BTN_FX)) macros_bake();          /* 0.10 FX + ARP: bake the macros (asks twice) */
        else if (held & (1u << BTN_EDIT)) prog_copy();          /* 0.16 EDIT + ARP: the progression playing into a USER slot */
        ui_dirty = 1u;
    }
    if ((b & ((1u << BTN_FX) | (1u << BTN_HOME))) && (held & (1u << BTN_FX)) && (held & (1u << BTN_HOME))) {   /* PANIC (once a gesture) */
        if (playing && panic_ms && (uint32_t)(fm1_ms - panic_ms) < 2000u) { transport_stop(); status_msg("PANIC: STOPPED TOO"); panic_ms = 0u; }   /* twice: the transport stops */
        else { panic_all_x(1u); status_msg(playing ? "PANIC: ALL OFF (AGAIN: STOP)" : "PANIC: ALL NOTES AND SOUND OFF"); panic_ms = fm1_ms ? fm1_ms : 1u; }
    }
    if (rel & (1u << BTN_SAVE)) save_released(held);

    {   /* OCT- / OCT+: 0.12 the window's pages count as the button's (eh: the buttons held, the window among them) */
        uint32_t eh = eff_held();
        const uint32_t NOGRP = (1u << BTN_HOME) | (1u << BTN_EDIT) | (1u << BTN_ENV) | (1u << BTN_LFO) | (1u << BTN_SEQ) | (1u << BTN_FX) | (1u << BTN_ARP) | (1u << BTN_SEL);
        if ((b & ((1u << BTN_OCT_DOWN) | (1u << BTN_OCT_UP))) && dice_pending &&
            !(eh & ((1u << BTN_SEL) | (1u << BTN_FX) | (1u << BTN_HOME) | (1u << BTN_EDIT) | (1u << BTN_ENV) | (1u << BTN_LFO) | (1u << BTN_ARP) | (1u << BTN_SAVE)))) {
            dice_answer((b & (1u << BTN_OCT_UP)) ? 1u : 0u);                  /* a dice waits: OCT+ keeps it, OCT- puts it back */
            b &= ~((1u << BTN_OCT_DOWN) | (1u << BTN_OCT_UP));
        }
        if (b & (1u << BTN_OCT_DOWN)) {
            if ((held & (1u << BTN_GLO)) && (held & (1u << BTN_SEL))) { track_octave(selected_track, -1); glo_used = 1u; selglo_pend = 0u; }   /* 0.12 GLO + SEL + OCT-: the track an octave down */
            else if (held & (1u << BTN_GLO)) { perf_page = perf_page ? (uint8_t)(perf_page - 1u) : 0u; glo_used = 1u; selglo_pend = 0u; }        /* 0.12 GLO + OCT: its pages */
            else if (perf_mode && !(eh & NOGRP)) perf_page = perf_page ? (uint8_t)(perf_page - 1u) : 0u;                                          /* 0.12 PERF: GLO's pages (its window) */
            else if (perf_mode && !(eh & (NOGRP & ~(1u << BTN_SEL)))) { perf_solo_mode = 0u; status_msg("PERF WHITE KEYS: MUTE"); }             /* 0.12 PERF + SEL + OCT-: the whites mute */
            else if (eh & (1u << BTN_SEL)) key_octave = (int8_t)clamp_i32((int32_t)key_octave - 1, -3, 3);
            else if (eh & (1u << BTN_ARP)) arp_page = arp_page ? (uint8_t)(arp_page - 1u) : 0u;
            else if (eh & (1u << BTN_SAVE)) { save_page = save_page ? (uint8_t)(save_page - 1u) : 0u; save_knob = 1u; }
            else if (eh & (1u << BTN_FX)) macros_zero();                     /* FX + OCT-: the macros back to 0 */
            else if (eh & (1u << BTN_SEQ)) { uint8_t q = seq_page; do { q = q ? (uint8_t)(q - 1u) : 0u; } while (q && !vg_seq_shown(q)); seq_page = q; }   /* (0.27: SEMPLICE skips SEQ 2, 3) */
            else if (eh & (1u << BTN_ENV)) env_lane = env_lane ? (uint8_t)(env_lane - 1u) : 0u;
            else if (eh & (1u << BTN_HOME)) { uint8_t h = home_page; do { h = h ? (uint8_t)(h - 1u) : 0u; } while (h && !vg_allows_home(h)); if (vg_allows_home(h)) home_page = h; }
            else if (eh & (1u << BTN_LFO)) lfo_page = lfo_page ? (uint8_t)(lfo_page - 1u) : 0u;
            else { if (page) page--; cursor_step = (uint8_t)(page * 16u); }
            ui_dirty = grid_dirty = 1u;
        }
        if (b & (1u << BTN_OCT_UP)) {
            if ((held & (1u << BTN_GLO)) && (held & (1u << BTN_SEL))) { track_octave(selected_track, 1); glo_used = 1u; selglo_pend = 0u; }    /* 0.12 GLO + SEL + OCT+: the track an octave up */
            else if (held & (1u << BTN_GLO)) { perf_page = perf_page < PERF_PAGES - 1u ? (uint8_t)(perf_page + 1u) : (uint8_t)(PERF_PAGES - 1u); glo_used = 1u; selglo_pend = 0u; }
            else if (perf_mode && !(eh & NOGRP)) perf_page = perf_page < PERF_PAGES - 1u ? (uint8_t)(perf_page + 1u) : (uint8_t)(PERF_PAGES - 1u);
            else if (perf_mode && !(eh & (NOGRP & ~(1u << BTN_SEL)))) { perf_solo_mode = 1u; status_msg("PERF WHITE KEYS: SOLO"); }             /* 0.12 PERF + SEL + OCT+: the whites solo */
            else if (eh & (1u << BTN_SEL)) key_octave = (int8_t)clamp_i32((int32_t)key_octave + 1, -3, 3);
            else if (eh & (1u << BTN_ARP)) arp_page = arp_page < ARP_PAGES - 1u ? (uint8_t)(arp_page + 1u) : (uint8_t)(ARP_PAGES - 1u);
            else if (eh & (1u << BTN_SAVE)) { save_page = save_page < SAVE_PAGES - 1u ? (uint8_t)(save_page + 1u) : (uint8_t)(SAVE_PAGES - 1u); save_knob = 1u; }
            else if (eh & (1u << BTN_FX)) echo_global_set(echo_global ? 0u : 1u);   /* FX + OCT+: the global ECHO on / off */
            else if (eh & (1u << BTN_SEQ)) { uint8_t q = seq_page; do { q = q < SEQ_PAGES - 1u ? (uint8_t)(q + 1u) : (uint8_t)(SEQ_PAGES - 1u); } while (q < SEQ_PAGES - 1u && !vg_seq_shown(q)); seq_page = q; }
            else if (eh & (1u << BTN_ENV)) env_lane = env_lane < SQ_LANES - 1u ? (uint8_t)(env_lane + 1u) : (uint8_t)(SQ_LANES - 1u);
            else if (eh & (1u << BTN_HOME)) { uint8_t h = home_page; do { h = h < HOME_PAGES - 1u ? (uint8_t)(h + 1u) : (uint8_t)(HOME_PAGES - 1u); } while (h < HOME_PAGES - 1u && !vg_allows_home(h)); if (vg_allows_home(h)) home_page = h; }
            else if (eh & (1u << BTN_LFO)) lfo_page = lfo_page < LFO_PAGES - 1u ? (uint8_t)(lfo_page + 1u) : (uint8_t)(LFO_PAGES - 1u);
            else { if (page < 3u) page++; cursor_step = (uint8_t)(page * 16u); }
            ui_dirty = grid_dirty = 1u;
        }
    }
    {   /* what the screen shows while a button is held (0.12: or a window is open): redraw when it changes */
        static uint32_t last_bits;
        uint32_t bits = eff_held() & ~((1u << BTN_PLAY) | (1u << BTN_REC));
        if (grid_fill) bits |= 0x80000000u;
        if (bits != last_bits) { last_bits = bits; ui_dirty = 1u; }
    }
    if (save_tick()) ui_dirty = 1u;
    pipat_tick();                                      /* 0.11: a pattern asked of the Pi that does not come */
}

#include "sagga_pick.c"                               /* 0.12: choosing with the keys, the key maps, the SEQ keys held */
#include "sagga_store.c"
#include "sagga_link.c"                               /* 0.15: the Pi's editor follows the music, plays what you touch */
#include "sagga_pipat.c"
#include "sagga_live.c"
#include "sagga_viaggio.c"
#include "sagga_remote2.c"                            /* 0.12: channel 13, CC 33 and up, the pads */
#include "sagga_tablet.c"                             /* 0.18: channel 12 (the LIVE page), what goes back to the hub */
#include "sagga_grid.c"
#include "sagga_tape.c"
#include "sagga_ui.c"

/* 0.12: the white keys of the steps a long note (or a TIE) covers, in the glow layer: the note reads as one block */
static void leds_note_tails(void)
{
    uint16_t tail, bridge, half;
    uint32_t i;
    strip_notes(&tail, &bridge, &half);
    for (i = 0; i < 16u; i++) if ((tail | half) & (1u << i)) fm1_led_key_dim(KEY_LED(white_key[i]), 1);
}

static void update_leds(void)
{
    uint32_t k, i, held = eff_held();                           /* (0.12: the window counts as held: its keys, its button lit) */
    uint8_t blink = (uint8_t)((fm1_ms / 250u) & 1u);
    for (k = 0; k < 27u; k++) { fm1_led_key(KEY_LED(k), 0); fm1_led_key_dim(KEY_LED(k), 0); }
    if ((held & (1u << BTN_SEL)) && pick_group(held) >= 0) {   /* 0.12 PICK: the keys that mean something; the value now blinks */
        pick_leds(pick_group(held), blink);
    } else if (held & (1u << BTN_SAVE)) {                      /* the slots on the whites; the snapshots on the blacks */
        for (i = 0; i < 8u; i++) fm1_led_key(KEY_LED(white_key[i]), i == slot_cur ? 1 : 0);
        for (i = 0; i < SQ_SNAPS; i++) fm1_led_key(KEY_LED(black_key[i]), snap_pend == i ? blink : (snap_cur == i && project.snap[i].used) ? 1 : 0);
        fm1_led_key(KEY_LED(black_key[8]), snap_capture ? blink : 0);
    } else if (held & (1u << BTN_FX)) {
        for (i = 0; i < 16u; i++) fm1_led_key(KEY_LED(white_key[i]), (fx_now() >> i) & 1u);
        for (i = 0; i < 8u; i++) fm1_led_key(KEY_LED(black_key[i]), loop_on && loop_len == loop_ticks(i));
        fm1_led_key(KEY_LED(black_key[8]), restart_pend ? blink : 0u);
        fm1_led_key(KEY_LED(black_key[9]), stop_at_bar ? blink : 0u);
        fm1_led_key(KEY_LED(black_key[10]), loop_on);
    } else if (held & (1u << BTN_HOME)) {                      /* the track selected, 1-16; PERF: the song on the blacks */
        for (i = 0; i < SQ_TRACKS; i++) fm1_led_key(KEY_LED(white_key[i]), i == selected_track);   /* (0.28: whites 13-16 dark) */
        if (perf_mode) {
            for (i = 0; i < project.song.len; i++)                 /* (0.9: the scenes of the cursor's bank) */
                if ((project.song.e[i].scene & 8u) == (scene_cursor & 8u)) fm1_led_key(KEY_LED(black_key[project.song.e[i].scene & 7u]), 1);
            fm1_led_key(KEY_LED(black_key[8]), project.song.loop);
        }
    } else if (held & ((1u << BTN_EDIT) | (1u << BTN_ENV))) {  /* the steps, the cursor blinks; EDIT: black 2-4 COPY, PASTE, CLEAR */
        uint8_t base = (uint8_t)(page * 16u);
        for (i = 0; i < 16u; i++) {
            sq_step_t *s = &project.step[selected_track][tr[selected_track].pattern][base + i];
            fm1_led_key(KEY_LED(white_key[i]), base + i == cursor_step ? blink : (s->flags & SQ_STEP_ON) != 0u);
        }
        leds_note_tails();                                     /* 0.12: the keys a long note covers glow */
        if (held & (1u << BTN_EDIT)) {
            fm1_led_key(KEY_LED(black_key[0]), (project.step[selected_track][tr[selected_track].pattern][cursor_step].flags & SQ_STEP_LOCK) != 0u);
            fm1_led_key(KEY_LED(black_key[1]), 1);
            fm1_led_key(KEY_LED(black_key[2]), step_clip_ok);
            fm1_led_key(KEY_LED(black_key[3]), 1);
            {   /* 0.13: PLAIN, TIE, SLIDE lit on the cursor step that has them */
                uint8_t f = project.step[selected_track][tr[selected_track].pattern][cursor_step].flags;
                fm1_led_key(KEY_LED(black_key[4]), (f & SQ_STEP_XOFF) != 0u);
                fm1_led_key(KEY_LED(black_key[5]), (f & SQ_STEP_TIE) != 0u);
                fm1_led_key(KEY_LED(black_key[6]), (f & SQ_STEP_SLIDE) != 0u);
            }
        }
    } else if (held & (1u << BTN_LFO)) {
        for (i = 0; i < 16u; i++) fm1_led_key(KEY_LED(white_key[i]), project.lfo[i].enabled || i == lfo_sel);
    } else if ((held & (1u << BTN_ARP)) && track_break(selected_track)) {   /* 0.12: the chops on the whites (the pattern's blinks), the moves */
        for (i = 0; i < 16u; i++) fm1_led_key(KEY_LED(white_key[i]), i == project.track[selected_track].brk_chop ? blink : (brk_live_key == white_key[i]));
        fm1_led_key(KEY_LED(black_key[0]), brk_roll_held == 1u);
        fm1_led_key(KEY_LED(black_key[1]), brk_roll_held == 2u);
        for (i = 2; i < 9u; i++) fm1_led_key(KEY_LED(black_key[i]), 1);
    } else if (held & (1u << BTN_ARP)) {                        /* 0.12: the keys play the track: the ones down are lit */
        for (k = 0; k < 27u; k++) if (in_notes() & (1u << k)) fm1_led_key(KEY_LED(k), 1);
        if (track_drum(selected_track) && playing) for (i = 0; i < 4u; i++) fm1_led_key(KEY_LED(black_key[i]), rep_rate == i + 1u ? blink : 1);   /* 0.13: NOTE REPEAT's rates (the one held blinks) */
    } else if (held & (1u << BTN_SEQ)) {
        for (i = 0; i < TOOL_COUNT; i++) fm1_led_key(KEY_LED(white_key[i]), i == TOOL_UNDO ? undo_valid : i == TOOL_RAND && dice_pending && dice_kind == DICE_RANDOM ? blink : 1u);   /* (0.27: RANDOM waiting: it blinks, as a dice) */
        for (i = 0; i < 5u; i++) fm1_led_key(KEY_LED(black_key[i]), dice_pending && dice_kind == DICE_SEQ + i ? blink : 0u);
        fm1_led_key(KEY_LED(black_key[5]), project.gen.scope != SQ_SCOPE_THIS);
        fm1_led_key(KEY_LED(black_key[7]), evo_drifts());   /* (0.27: RETURN at 0) */
        fm1_led_key(KEY_LED(black_key[8]), evo_run != 0u);
        fm1_led_key(KEY_LED(black_key[9]), evo_run == 2u);
    } else if (perf_mode || (held & (1u << BTN_GLO))) {        /* (0.12: GLO held shows the PERF keys in any mode) */
        for (i = 0; i < SQ_TRACKS; i++) fm1_led_key(KEY_LED(white_key[i]), perf_solo_mode ? ((solo_mask >> i) & 1u) : (((pending_mute >> i) & 1u) ? blink : track_audible(i)));
        if (perf_page == 2u) for (i = 0; i < 11u; i++) fm1_led_key(KEY_LED(black_key[i]), vg_move_lit((int)i, blink));   /* 0.17 the MOSSE: what waits */
        else for (i = 0; i < 8u; i++) { uint32_t sc = (scene_cursor & 8u) + i; fm1_led_key(KEY_LED(black_key[i]), pending_scene == sc ? blink : scene_cursor == sc); }
    } else if (record_arm) {
        if (track_drum(selected_track))                        /* the drum keys */
            for (i = 0; i < 16u; i++) fm1_led_key(KEY_LED(white_key[i]), drum_track_n((uint8_t)i) < SQ_TRACKS);
        for (k = 0; k < 27u; k++) if (in_notes() & (1u << k)) fm1_led_key(KEY_LED(k), 1);
    } else {                                                   /* the steps as they are heard (EUCLID, the algorithm) */
        uint8_t base = (uint8_t)(page * 16u);
        for (i = 0; i < 16u; i++) fm1_led_key(KEY_LED(white_key[i]), live_preview(selected_track, (uint8_t)(base + i)));
        leds_note_tails();                                     /* 0.12: the keys a long note covers glow */
        for (i = 0; i < 8u; i++) fm1_led_key(KEY_LED(black_key[i]), (selected_track & 7u) == i);
        fm1_led_key(KEY_LED(black_key[8]), (selected_track & 8u) != 0u);
        fm1_led_key(KEY_LED(black_key[9]), (mute_mask >> selected_track) & 1u);
        fm1_led_key(KEY_LED(black_key[10]), (solo_mask >> selected_track) & 1u);
    }
    /* the buttons: full when held or on; the others glow (the backlight, lights_apply) */
#define HELD(btn) ((held >> (btn)) & 1u)
    fm1_led_key(BTN_PLAY, playing || HELD(BTN_PLAY) || (cnt_on && ((fm1_ms / 125u) & 1u)));   /* (0.26: it blinks while the count runs) */
    fm1_led_key(BTN_REC, record_arm || HELD(BTN_REC));
    fm1_led_key(BTN_GLO, song_on ? blink : (perf_mode || HELD(BTN_GLO)));
    fm1_led_key(BTN_ARP, SQ_CHORD_MODE(project.track[selected_track].chord_mode) != SQ_CHORD_BLOCK || HELD(BTN_ARP));
    fm1_led_key(BTN_FX, fx_now() != 0u || loop_on || echo_global || HELD(BTN_FX));
    fm1_led_key(BTN_LFO, project.lfo[lfo_sel].enabled || HELD(BTN_LFO));
    fm1_led_key(BTN_SEQ, dice_pending ? blink : (evo_run == 1u || HELD(BTN_SEQ)));
    fm1_led_key(BTN_HOME, HELD(BTN_HOME));
    fm1_led_key(BTN_EDIT, HELD(BTN_EDIT));
    fm1_led_key(BTN_ENV, HELD(BTN_ENV));
    fm1_led_key(BTN_SEL, HELD(BTN_SEL));
    fm1_led_key(BTN_SAVE, HELD(BTN_SAVE));
    fm1_led_key(BTN_OCT_DOWN, HELD(BTN_OCT_DOWN));
    fm1_led_key(BTN_OCT_UP, HELD(BTN_OCT_UP));
#undef HELD
    {
        static uint8_t lights_shown = 255u;
        if (lights_level() != lights_shown) { lights_shown = lights_level(); lights_apply(); }
    }
    usb_watch();
    batt_watch();
    {   /* the battery on the screen: redrawn when it changes */
        static uint8_t bat_shown;
        uint8_t bc = batt_code();
        if (bc != bat_shown) { bat_shown = bc; ui_dirty = 1u; }
    }
}

#include "sagga_test.c"                             /* 0.11: the PC test, and the probe it shares with the simulator */

#ifdef DINGHY_HOST
/* the tests read a pattern back: "steps T1 P1 0-16 1A2B3C4D mode K pen 60 ON:x...x..." (the hash covers every byte of the
 * 64 steps of the pattern playing) */
/* 0.11 the explorer (tests/sagga_explore.py): the probe (sagga_test.c), a line each with the time before it */
static void app_host_probe(void)
{
    static char b[TST_PB];
    uint32_t n = probe_render(b, sizeof b - 1u), i = 0u;
    b[n] = 0;
    while (i < n) {
        uint32_t e = i;
        while (e < n && b[e] != '\n') e++;
        printf("%6u ms  %.*s\n", fm1_ms, (int)(e - i), b + i);
        i = e + 1u;
    }
}

/* the simulator: "T theory STYLE SEED VAR VARY ENERGY PAT" - a band MADE by the THEORY engines, for the tools that
 * write out what they make (tools/theory/render.py) and for the tests. PAT 0: a new band - the SOURCE on THEORY, the
 * style's genre (FREE: GENRE FREE), a key of the seed's, the genre's tempo, four progressions of the style in USER 1-4
 * with the HARMONY on USER 1, the machine's ENERGY, the band onto tracks 1.. as BAND makes it. PAT 1-7: pattern PAT + 1
 * of the same tracks made from the seed, the variation and the energy given, and scene PAT + 1 plays it.
 * "T scene N [K]": scene N + 1 (K: with the player's progression K + 1). "T energy E": the machine's energy, at once. */
static void app_host_theory(int packed, int seed)
{
    uint8_t style = (uint8_t)(packed & 31), pat = (uint8_t)((packed >> 5) & 15), energy = (uint8_t)((packed >> 9) & 127);
    uint8_t vary = (uint8_t)((packed >> 16) & 127), var = (uint8_t)((packed >> 24) & 127), g, t, k, n, funcs[SQ_TH_BAND_MAX];
    uint16_t lo, hi, sd = (uint16_t)((uint32_t)seed % SQ_TH_SEEDS);
    if (style >= SQ_TH_STYLES || pat >= SQ_PATTERNS) return;
    g = sq_th_genre(style);
    if (g >= SQ_GENRES) g = beat_genre;                 /* (FREE has no genre: the one that is set stays, and gives the kit its notes) */
    n = sq_th_band(style, funcs);
    if (n > SQ_TRACKS) n = (uint8_t)SQ_TRACKS;
    project.th.src = SQ_SRC_THEORY;
    if (pat == 0u) {
        sq_th_t p;
        memset(&p, 0, sizeof p);
        p.style = style; p.seed = sd;
        project.key_scale = sq_th_scale(&p);
        project.key_root = sq_th_root(&p);
        key_sync_slot();
        beat_genre = g; project.gen.genre = g;
        project.gen.genre_mode = style == SQ_TH_FREE ? SQ_GM_FREE : SQ_GM_ON;
        sq_genre_bpm(g, &lo, &hi);
        project.bpm = (uint16_t)(style == SQ_TH_FREE ? 120u : (lo + hi) / 2u);
        knob_live = 0u; knob_ref = fm1_knob;
        p.scale = project.key_scale; p.energy = energy;
        for (k = 0; k < SQ_UPROGS; k++) {                /* USER 1: the seed's own chords; 2-4: three more of the style */
            p.var = k; p.vary = (uint8_t)(k ? 100u : 0u);
            sq_th_prog(&project.uprog[k], &p);
        }
        project.gen.harm_on = 1u;
        project.gen.harm_bars = 0u;
        project.viaggio.energy = energy > 100u ? 100u : energy;
        vg_energy_from = project.viaggio.energy;
        vg_energy_apply(project.viaggio.energy);
        project.th.seed = sd;
        for (t = 0; t < n; t++) {
            PEN(t) = sq_part_note(g, funcs[t]);
            project.track[t].length = 64u; project.track[t].start = 0u;   /* (0.24: the length is the track's: four bars) */
            beat_onto_x(t, 0u, g, funcs[t], 0u, 1u, 0);
            activate_row(t, project.step[t][0]);
        }
        project.gen.harm_prog = (uint8_t)SQ_PROGS;
        for (k = 0; k < SQ_SCENES; k++) for (t = 0; t < SQ_TRACKS; t++) project.scene[k].pattern[t] = 0u;
    } else {
        for (t = 0; t < n; t++) {
            th_make(t, pat, style, funcs[t], sd, var, vary, energy, 64u);
            activate_row(t, project.step[t][pat]);
            project.scene[pat].pattern[t] = pat;
        }
    }
    ui_dirty = grid_dirty = 1u;
}
/* 0.26: the pattern every track plays becomes one that 0.25 made - what the engines keep of it says so (not made in
 * the bar, no notes in its answers) and it is made again that way: a band of a project of 0.25, for the tests */
static void app_host_thold(void)
{
    uint32_t t;
    for (t = 0; t < SQ_TRACKS; t++) {
        sq_thpat_t *m = &project.th.pat[t][tr[t].pattern];
        if (!(m->style & 31u)) continue;
        m->style = (uint8_t)(m->style & 0x7Fu);
        m->vary = (uint8_t)(m->vary & 127u);
        if (th_again((uint8_t)t, tr[t].pattern)) activate_row(t, project.step[t][tr[t].pattern]);
    }
    ui_dirty = grid_dirty = 1u;
}
static void app_host_scene(int s, int prog)
{
    if (prog >= 0 && prog < (int)SQ_UPROGS) harm_prog_set((uint8_t)(SQ_PROGS + (uint32_t)prog));
    if (s >= 0 && s < (int)SQ_SCENES) scene_recall((uint8_t)s);
}
static void app_host_energy(int e)
{
    project.viaggio.energy = (uint8_t)(e < 0 ? 0 : e > 100 ? 100 : e);
    vg_energy_from = project.viaggio.energy;
    vg_energy_apply(project.viaggio.energy);
}

static void app_host_dump(int t)
{
    const sq_step_t *row;
    const uint8_t *b;
    uint32_t h = 2166136261u, i;
    if (t < 0 || t >= (int)SQ_TRACKS) return;
    row = project.step[t][tr[t].pattern];
    b = (const uint8_t *)row;
    for (i = 0; i < sizeof project.step[0][0]; i++) h = (h ^ b[i]) * 16777619u;
    printf("%6u ms  steps T%d P%u %u-%u %08X mode %c pen %u ON:", fm1_ms, t + 1, (unsigned)tr[t].pattern + 1u,
           (unsigned)project.track[t].start, (unsigned)project.track[t].length, (unsigned)h, "FKDTB"[track_mode((uint32_t)t)],
           (unsigned)PEN(t));
    for (i = 0; i < project.track[t].length; i++) putchar((row[i].flags & SQ_STEP_ON) ? 'x' : '.');
    putchar('\n');
    /* 0.24: the copies: the pattern's own length in the loop, and the whole row (x a step that plays, g a copy that
     * plays, r a copy at rest - after the loop: the mark of the pattern's end) */
    printf("%6u ms  copies T%d own %u ROW:", fm1_ms, t + 1, (unsigned)sq_row_own(row, project.track[t].start, project.track[t].length));
    for (i = 0; i < SQ_STEPS; i++) putchar((row[i].flags & SQ_STEP_GHOST) ? ((row[i].flags & SQ_STEP_ON) ? 'g' : 'r') : (row[i].flags & SQ_STEP_ON) ? 'x' : '.');
    putchar('\n');
    /* 0.26: the row's notes as the engines write them - a step's note above the track's root (0..f), '*' a chord,
     * '?' another note, '.' a step that does not play */
    printf("%6u ms  rownt T%d NT:", fm1_ms, t + 1);
    for (i = 0; i < project.track[t].length; i++) {
        int32_t d = (int32_t)row[i].note[0] - (int32_t)gen_root_note((uint32_t)t);
        putchar(!(row[i].flags & SQ_STEP_ON) || row[i].note[0] > 127u ? '.' : row[i].note[1] <= 127u ? '*' : d >= 0 && d < 16 ? "0123456789abcdef"[d] : '?');
    }
    putchar('\n');
    {   /* 0.11: the tape of the track */
        uint16_t tf, tn, k;
        sq_tape_range(&project, (uint8_t)t, &tf, &tn);
        printf("%6u ms  tape T%d bars %u quant %u n %u:", fm1_ms, t + 1, (unsigned)project.track[t].tape.bars, (unsigned)project.track[t].tape.quant, (unsigned)tn);
        for (k = 0; k < tn && k < 32u; k++) printf(" %u/%u/%u/%u", (unsigned)project.tape_ev[tf + k].on, (unsigned)project.tape_ev[tf + k].dur,
                                                   (unsigned)project.tape_ev[tf + k].note, (unsigned)project.tape_ev[tf + k].vel);
        putchar('\n');
    }
    {   /* 0.8: what the tests need to see beside the steps: the live layer, the harmony, the snapshots, the message */
        const sq_track_cfg_t *c = &project.track[t];
        printf("%6u ms  state T%d flags %u euc %u/%u algo %u %u %u %u mfx %u %d harm %u %u %u %u snap %d %d %u mac %d %d %d %d HEARD:",
               fm1_ms, t + 1, (unsigned)c->flags, (unsigned)c->euc_pulses, (unsigned)c->euc_rot, (unsigned)c->algo,
               (unsigned)c->algo_a, (unsigned)c->algo_b, (unsigned)c->algo_c, (unsigned)c->mfx, (int)c->mfx_amt,
               (unsigned)project.gen.harm_on, (unsigned)project.gen.genre, (unsigned)project.gen.harm_prog,
               (unsigned)project.gen.harm_bars, snap_cur == 255u ? -1 : (int)snap_cur, snap_pend == 255u ? -1 : (int)snap_pend,
               (unsigned)snap_capture, (int)mac_vel, (int)mac_gate, (int)mac_swing, (int)mac_filt);
        for (i = 0; i < c->length; i++) putchar(i < c->start ? ' ' : live_preview((uint32_t)t, (uint8_t)i) ? 'x' : '.');
        printf(" MSG:%s\n", msg_text ? msg_text : "");
        {   /* 0.19: the MIDI FX chain */
            const sq_mfxc_t *m = &project.ext.mfxc[t];
            printf("%6u ms  mfxc T%d on %u sel %u pend %u amt %d %d %d %d time %u %u %u %u fb %u %u %u %u\n", fm1_ms, t + 1, (unsigned)m->on,
                   (unsigned)mfx_sel[t], (unsigned)mfx_pend[t], (int)m->amt[0], (int)m->amt[1], (int)m->amt[2], (int)m->amt[3],
                   (unsigned)m->time[0], (unsigned)m->time[1], (unsigned)m->time[2], (unsigned)m->time[3],
                   (unsigned)m->fb[0], (unsigned)m->fb[1], (unsigned)m->fb[2], (unsigned)m->fb[3]);
        }
        {   /* 0.20: the new five and the order */
            const sq_mfxd_t *m = &project.ext.mfxd[t];
            uint32_t k;
            printf("%6u ms  mfxd T%d on %u order", fm1_ms, t + 1, (unsigned)m->on);
            for (k = 0; k < SQ_MFX_ALLN; k++) printf(" %u", (unsigned)m->order[k]);
            printf(" amt"); for (k = 0; k < SQ_MFX_NEW; k++) printf(" %d", (int)m->amt[k]);
            printf(" time"); for (k = 0; k < SQ_MFX_NEW; k++) printf(" %u", (unsigned)m->time[k]);
            printf(" fb"); for (k = 0; k < SQ_MFX_NEW; k++) printf(" %u", (unsigned)m->fb[k]);
            printf(" modfx %d\n", (int)mod_fx[t]);
        }
    }
    {   /* 0.10: the track's new settings, the key slots, the tools' schedule, the lanes, the genre mode */
        const sq_track_cfg_t *c = &project.track[t];
        const sq_key_t *k = track_key((uint32_t)t);
        printf("%6u ms  cfg T%d role %u chord %u oct %d keyslot %d trans %d div %u len %u key %u/%u/%d cur %u genre %u mode %u when %u every %u/%u lib %u "
               "arp %u/%u fam %u prog %u lanes", fm1_ms, t + 1, (unsigned)c->role, (unsigned)c->chord, (int)c->octave,
               c->key_slot == SQ_KEY_FOLLOW ? -1 : (int)c->key_slot, (int)c->transpose, (unsigned)c->division, (unsigned)c->length,
               (unsigned)k->root, (unsigned)k->scale, (int)k->shift, (unsigned)project.key_cur, (unsigned)project.gen.genre,
               (unsigned)project.gen.genre_mode, (unsigned)project.gen.when, (unsigned)project.gen.every, (unsigned)project.gen.every_tool,
               (unsigned)project.gen.lib_len, (unsigned)c->arp_rate, (unsigned)c->arp_flags, (unsigned)c->euc_fam, (unsigned)project.gen.harm_prog);
        for (i = 0; i < SQ_LANES; i++) printf(" %u/%u/%u/%u", (unsigned)c->lane_cc[i], (unsigned)c->lane_flags[i], (unsigned)c->lane_hi[i], (unsigned)c->lane_base[i]);
        printf(" cclead %u tempo %u mac %d %d %d %d ck %u\n", (unsigned)project.live.cc_lead_ms, (unsigned)project.live.song_tempo,
               (int)project.live.mac[0], (int)project.live.mac[1], (int)project.live.mac[2], (int)project.live.mac[3], (unsigned)c->chord_key);
    }
    {   /* 0.11: the harmony's own genre and lock, the length that waits for the bar, where the track's time is counted from */
        uint32_t k;
        printf("%6u ms  v11 T%d harmgenre %u lock %u lenpend %u anchor %u step %u slot %u algos", fm1_ms, t + 1, (unsigned)project.gen.harm_genre,
               (unsigned)project.gen.harm_lock, (unsigned)len_pend[t], (unsigned)tr[t].anchor, (unsigned)tr[t].step, (unsigned)algo_cur[t]);
        for (k = 0; k < SQ_ALGO_SLOTS; k++) { const sq_algo_t *a = SQ_ALGO_AT(&project.track[t], k); printf(" %u/%u/%u/%u", a->algo, a->a, a->b, a->c); }
        printf(" win %d chop %u\n", win_cur == 255u ? -1 : (int)win_cur, (unsigned)project.track[t].brk_chop);   /* 0.12: the window open, the chop */
    }
    {   /* 0.13: the CHAIN LIST, the KEYBOARD, MIDI IN, the MOTION (cells written a macro), the portamento, the LFO shown */
        const sq_trackx_t *cx = &project.ext.track[t];
        const sq_lfox_t *lx = &project.ext.lfo[lfo_sel];
        uint32_t k, m, nrec[4] = {0u, 0u, 0u, 0u};
        for (m = 0; m < 4u; m++) for (k = 0; k < SQ_MOTION_CELLS; k++) if (project.ext.motion[m][k] != (int8_t)SQ_MOTION_NONE) nrec[m]++;
        printf("%6u ms  v13 T%d chain %u pos %u left %u list", fm1_ms, t + 1, (unsigned)cx->chain_on, (unsigned)chain_pos[t], (unsigned)chain_left[t]);
        for (k = 0; k < cx->chain_n; k++) printf(" %u/%u", (unsigned)cx->chain_pat[k] + 1u, (unsigned)cx->chain_rep[k]);
        printf(" kb %u/%u thru %u ktrans %d motion %u rec %u %u %u %u porta %u lfo %u seq %u/%u trig %u\n", (unsigned)project.ext.kb_mode,
               (unsigned)project.ext.kb_ch, (unsigned)project.ext.in_thru, (int)project.live.ktrans, (unsigned)project.ext.motion_bars,
               (unsigned)nrec[0], (unsigned)nrec[1], (unsigned)nrec[2], (unsigned)nrec[3], (unsigned)porta_ch, (unsigned)lfo_sel + 1u,
               (unsigned)lx->seq_n, (unsigned)lx->seq_every, (unsigned)lx->trig);
    }
    {   /* 0.15: the GROOVE of the track, the project's name, the slots' names, the link to the Pi's editor */
        const sq_trackx_t *cx = &project.ext.track[t];
        uint32_t k;
        char nm[SQ_NAME_LEN + 1u];
        memcpy(nm, project.ext.name, SQ_NAME_LEN); nm[SQ_NAME_LEN] = 0;
        printf("%6u ms  v15 T%d groove %u amt %u swing %u name [%s] link %u sent %u aud %u hfree %u hgenre %u hprog %u up", fm1_ms, t + 1, (unsigned)cx->groove,
               (unsigned)cx->groove_amt, (unsigned)project.track[t].swing, nm, (unsigned)link_on, (unsigned)link_sent, (unsigned)aud_n,
               (unsigned)project.gen.harm_free, (unsigned)project.gen.harm_genre, (unsigned)project.gen.harm_prog);
        for (k = 0; k < SQ_UPROG_SLOTS; k++) printf(" %u", (unsigned)project.uprog[k].n);
        printf(" slots");
        for (k = 0; k < SQ_SLOTS; k++) printf(" %u:%s[%s]", (unsigned)k + 1u, slot_info[k].ok ? "ok" : "-", slot_info[k].name);
        printf("\n");
    }
    {   /* 0.16: the algorithms READY on the track's slots, what the knobs set (the READY one or the one playing) */
        uint32_t k;
        const sq_algo_t *e = algo_edit(t);
        printf("%6u ms  v16 T%d pend", fm1_ms, t + 1);
        for (k = 0; k < SQ_ALGO_SLOTS; k++) printf(" %u", (unsigned)algo_pend[t][k]);
        printf(" shown %u edit %u/%u/%u/%u euc %u %u/%u\n", (unsigned)algo_shown(t), e->algo, e->a, e->b, e->c,
               (unsigned)((project.track[t].flags & SQ_TF_EUC) ? 1u : 0u), (unsigned)project.track[t].euc_pulses, (unsigned)project.track[t].euc_rot);
    }
    {   /* 0.11: the HARMONY's progression, rhythm, mood, the track's FOLLOW way, the chord now, the player's five */
        uint32_t k, j;
        sq_hchord_t hc;
        char nm[16];
        if (harm_chord(&hc, 0)) sq_hchord_name(project.key_scale, &hc, nm); else { nm[0] = '-'; nm[1] = 0; }
        printf("%6u ms  harm11 T%d prog %u rhythm %u mood %u pmood %u fm %u chord %s U", fm1_ms, t + 1, (unsigned)project.gen.harm_prog,
               (unsigned)project.gen.harm_rhythm, (unsigned)project.gen.harm_mood, (unsigned)harm_mood_of(project.gen.harm_prog),
               (unsigned)project.track[t].follow_mode, nm);
        for (k = 0; k < SQ_UPROG_SLOTS; k++) {
            const sq_uprog_t *u = &project.uprog[k];
            printf(" %u/%u:", (unsigned)u->n, (unsigned)u->mood);
            for (j = 0; j < u->n && j < 8u; j++) printf("%s%u.%u.%u.%u", j ? "," : "", (unsigned)u->semi[j], (unsigned)(u->semi[j] == 255u ? u->col[j] : u->shape[j]), (unsigned)u->dur[j], (unsigned)u->push[j]);
            if (!u->n) putchar('-');
        }
        putchar('\n');
    }
    {   /* 0.23: what the engines know of the pattern the track plays, the source and the next seed */
        const sq_thpat_t *m = &project.th.pat[t][tr[t].pattern];
        printf("%6u ms  theory T%d P%u style %u len %u func %u seed %u var %u vary %u energy %u src %u next %u now %u\n", fm1_ms, t + 1,
               (unsigned)tr[t].pattern + 1u, (unsigned)(m->style & 31u), (unsigned)(m->style ? SQ_THP_LEN(m) : 0u), (unsigned)m->func, (unsigned)m->seed,
               (unsigned)m->var, (unsigned)SQ_THP_VARY(m), (unsigned)m->energy, (unsigned)project.th.src, (unsigned)project.th.seed, (unsigned)vg_energy_now());
        printf("%6u ms  thmade T%d bar %u notes %u steps %u\n", fm1_ms, t + 1, (unsigned)((m->style & 31u) && (m->style & SQ_THP_V26) ? 1u : 0u),   /* 0.26: made in the bar, its answers with notes */
               (unsigned)((m->style & 31u) ? SQ_THP_NOTES(m) : 0u), (unsigned)((m->style & 31u) ? th_rec_len(m) : 0u));
        printf("%6u ms  thmetre T%d made %u now %u kept %u\n", fm1_ms, t + 1, (unsigned)m->metre, (unsigned)metre_id_now(),   /* 0.25: the metre it was made in */
               (unsigned)((th_kept[t] >> tr[t].pattern) & 1u));
    }
    {   /* 0.25: the metre: the bar in steps, its beats; the bar now and the tick in it; the bar that waits */
        char sig[8], spl[SQ_SPLIT_TEXT];
        sq_metre_sig(sq_bar_steps(&project.gen), sq_bar_beats(&project.gen), sig);
        sq_metre_split(sq_bar_steps(&project.gen), sq_bar_beats(&project.gen), spl);
        printf("%6u ms  metre T%d bar %u beats %08X no %u into %u pend %u %08X raw %u SIG:%s SPLIT:%s\n", fm1_ms, t + 1, (unsigned)sq_bar_steps(&project.gen),
               (unsigned)sq_bar_beats(&project.gen), (unsigned)bar_no(), (unsigned)bar_into(), (unsigned)bar_pend_steps,
               (unsigned)(bar_pend_steps ? bar_pend_beats : 0u), (unsigned)project.gen.bar_steps, sig, spl);
    }
    vg_host_dump();
}
#endif

/* (app_audio: sagga_click.c - 0.26: the metronome's click is the one sound this firmware makes) */

static void app_main(void)
{
    uint32_t now, led_next = 0u;
    init_key_maps();
    memset(ext_ch, 255, sizeof ext_ch);
    memset(pc_last, 255, sizeof pc_last);
    chord_entry_ms = fm1_ms - 1000u;
    if (tst_boot_begin()) {                            /* 0.11: the PC test's reboot (sagga_test.c): as a power-on, but */
        settings_restore();                            /* no project and no slot (the settings: the USB ports, the profile, */
        sq_project_init(&project);                     /* as always; HELLO tells the PC, the simulator takes the same) */
        store_scan();                                  /* (what is where: the store knows, though it is off) */
        memset(slot_info, 0, sizeof slot_info);
        project_id_check();
    } else {
        settings_restore();
        store_boot();
    }
    project_sanitize();
    project_runtime_reset(1u);
    vg_profile_boot();                                 /* 0.9: PALCO starts in VIAGGIO */
    pipat_init();                                      /* 0.11: the Pi's patterns: none known yet */
    grid_init();
    knob_ref = fm1_knob;
    next_master_clock_us = sq_micros();
    last_master_tick_us = next_master_clock_us;
    tab_fb_reset();                                    /* 0.18: nothing goes to the hub before the tablet speaks */
    lcd_fill(0, 0, 240, 240, C_BLACK);
    status_msg(tst_booted ? "PC TEST: A HAND ON A KEY STOPS IT" : "SAGGA SEQ " SQ_VERSION);   /* (the first thing on the screen) */
    msg_until = fm1_ms + 3000u;

    for (;;) {
        platform_poll();

        /* Give the sequencer clock priority over UI/input work. */
        now = sq_micros();
        count_service(now);                            /* 0.26: the count before a recording: its last tick starts the transport */
        service_master_clock(now);
        click_service(now);                            /* 0.26: a MIDI click's note ends */
        lfo_service(now);
        service_track_events(now);

        handle_midi_in(now);
        tst_service();                                 /* 0.11: what the PC presses, now (sagga_test.c) */
        handle_buttons();
        handle_keys(in_notes());
        handle_encoders();
        knob_service();
        brk_service();                                 /* 0.12: the live ROLL of a break */
        rep_service();                                 /* 0.13: NOTE REPEAT on a drum track */
        throw_service();                               /* 0.12: the throws spring back */
        pick_tick();                                   /* 0.12: the key map after half a second */
        seqhold_tick();                                /* 0.12: UNDO / COOK / DICE / KIT held */
        audible_service();                             /* 0.8: what went silent stops now */

        /* Input processing may have taken time: refresh the timestamp. */
        now = sq_micros();
        service_master_clock(now);
        service_track_events(now);

        if (prev_note != SQ_NOTE_NONE && time_due(fm1_ms, prev_off_ms)) preview_stop();
        link_tick();                                   /* 0.15: the Pi's editor: positions, what it plays */
        grid_service();
        tab_fb_service();                              /* 0.18: the hub's pages follow the FM-1 */
        store_service();
        live_service();
        vg_service();                                  /* 0.9: a track key held = the dice */
        metre_sync();                                  /* 0.25: the metre as it is now, whoever changed it */
        th_service();                                  /* 0.23: the engines' patterns follow the energy (0.25: and the metre), a track a pass */
        ghost_service();                               /* 0.24: the copies of a pattern follow it, a track a pass */
        regia_service();                               /* 0.9: STATO, TOCCATA, REGIA TASTO to the Pi */

        /* one piece of the screen per pass: the clock is served between pieces (see the screen, sagga_ui.c). 0.22: and
         * only when the panel has taken the piece before (lcd_idle): the loop never waits for pixels */
        if (!lcd_idle()) { }
        else if (ui_dirty) { if (!draw_screen_step()) { ui_dirty = 0u; grid_dirty = 1u; } }
        else if (grid_dirty) { if (!draw_grid_step()) grid_dirty = 0u; }
        if (msg_text && time_due(fm1_ms, msg_until)) { msg_text = 0; ui_dirty = 1u; }
        if (time_due(fm1_ms, led_next)) { update_leds(); led_next = fm1_ms + 30u; }
        if (time_due(fm1_ms, diag_next)) {                 /* the MIDI rates of the USB page, once a second */
            static uint32_t last_out, last_in;
            diag_out_ps = sq_midi_out_n - last_out; last_out = sq_midi_out_n;
            diag_in_ps = sq_midi_in_n - last_in; last_in = sq_midi_in_n;
            diag_next = fm1_ms + 1000u;
            if ((in_held() & (1u << BTN_HOME)) && (in_held() & (1u << BTN_SEL))) ui_dirty = 1u;
        }
    }
}
