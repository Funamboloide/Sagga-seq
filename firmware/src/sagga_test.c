/* SPDX-License-Identifier: GPL-3.0-only */
/* SAGGA SEQ 0.11: the PC test - the explorer (tests/sagga_explore.py) on the real FM-1.
 *
 * The PC (tools/hwtest/sagga_hw_explore.py) presses the FM-1's buttons, keys and knobs at the times of a plan and reads
 * the whole machine back: the explorer's probe, rendered here (the simulator prints the very same text). Afterwards the
 * explorer plays each session again in the simulator, every event where the FM-1 really took it (its ms and its clock
 * tick), and compares the two: what differs is the hardware (the compiler, the timing), not the plan.
 *
 * Safe by construction:
 *  - it starts only when a hand says yes: OPEN asks on the screen; SEL on the FM-1 = yes, any other key = no;
 *  - every session starts from a reboot into the test (BOOT): no project loaded, no slot read, nothing written to the
 *    flash (platform.c's fl_app_lock refuses the slots and the settings, and the store is off); the PC keeps the project
 *    that was in memory (an EXPORT first) and puts it back at the end (CLOSE: a normal reboot, then an IMPORT);
 *  - a hand on any key or knob stops the test at once; a power-off ends it (tst_noinit is lost).
 *
 * SysEx F0 7D 53 47 ... (numbers 7 bits a byte, low first):
 *   70 sub ...  PC -> FM-1: 0 HELLO; 1 OPEN; 2 BOOT; 3 GO; 4 EV idx*2 n (t*4 kind a*2 b*2 gc*4)*n; 5 CLOSE;
 *               6 AGAIN idx*2 (a probe whose pieces did not all arrive: the last two are kept); 7 TAKEN idx*2 n (where
 *               those events were taken, again: every one of the session is kept); 8 DIAG (0.20.9: the counters since
 *               the boot, to tell where a HELLO with no answer was lost); 9 QUIET (0.23.1: the session is over: the
 *               FM-1 stops, every note off, and takes no more events - so that what DIAG counts stands still while
 *               the PC compares it with what it heard)
 *   71 sub ...  FM-1 -> PC: 0 state booted playing boots*2 fault_vec*5 fault_pc*5 ms*4 usb_ports profile "version"; 1 state (OPEN:
 *               1 asking, then 2 yes / 3 no / 4 no answer / 5 playing: stop first); 2 ok (BOOT); 3 ms*4 (GO: the
 *               test's zero); 4 ok next*2 free (EV); 5 ok (CLOSE); 6 applied*2 late*2 lag*2 lost (DONE: the END event);
 *               7 why (a hand stopped it); 8 (DIAG) 19 numbers of 4 bytes, since the boot: the HELLOs and the test's
 *               frames that came in, the answers the USB had no room for, the ms of the main loop's first pass, the
 *               longest it stood still (ms); the USB's: bus resets, SET_CONFIGURATIONs, the ms of the last, suspends,
 *               starts tried again, OUT packets taken, held back, malformed events, SysEx packets lost to the other
 *               port's, SysEx frames lost because the one before still waited, IN packets sent, the most polls (2 kHz)
 *               one waited for the host, MIDI events dropped with the ring full; the ms now; 0.23.1, 16 more: what
 *               the app sent on port 1 and on port 2 (each: clock ticks, note-ons, note-offs, control changes, the
 *               rest, the bytes of them all and of the SysEx frames), then the output ring's account (events put
 *               into IN packets, dropped unconfigured, thrown away by a bus reset, waiting now); 9 ok (QUIET)
 *   72 idx*2 k last text  the probe event idx asked for, in pieces of 150 characters ("PROBE G ...\n PROBE T1 ...")
 *   73 n (idx*2 ms*4 gc*4)*n  where the events were taken: the FM-1's ms and global_clock
 *   74 seq*2 n (ms*4 gc*4 st d1 d2 cable)*n  0.20.3: the MIDI that came in from the ports, when GO asked to hear them
 *               (GO's byte 1: bit 0): every message the FM-1 played, where (ms, global_clock before it) and from which
 *               port; seq = the number of the first in the session (a gap = some lost on the way). st without bit 7.
 *               DONE then also says how many were heard (*2) and how many did not fit the ring (lost)
 * Event kinds: 1 press (a = button), 2 release, 3 knob (a = encoder, b = detents + 8192), 4 MASTER (a = 0..1023),
 * 5 keys (a | b << 14: the 27 note keys held), 6 probe, 7 end, 8 (0.18) a MIDI message that comes in: a = the status's low 7
 * bits | the port << 7 (0 port 1, 1 port 2, 2 the remote's: port 2 with two, else the only one), b = d1 | d2 << 7 (the
 * tablet's pages, the grid's pads). t: ms after GO. gc: 0x0FFFFFFF = none, else (the
 * simulator replaying the FM-1) the event waits for that clock tick, so it lands between the same two ticks. */

enum { SX_TST = 0x70, SX_TST_ANS = 0x71, SX_TST_PROBE = 0x72, SX_TST_LOG = 0x73, SX_TST_HEARD = 0x74 };
enum { TQ_HELLO, TQ_OPEN, TQ_BOOT, TQ_GO, TQ_EV, TQ_CLOSE, TQ_DONE, TQ_ABORT };
enum { TK_PRESS = 1, TK_RELEASE, TK_ENC, TK_KNOB, TK_KEYS, TK_PROBE, TK_END, TK_MIDI };
#define TST_Q 64u
#define TST_NOGC 0x0FFFFFFFu
#define TST_PB 7680u                                  /* a probe: ~5.5 KB of text with sixteen tracks */
#define TST_CHUNK 150u                                /* (a SysEx of the app fits the 64 packets of the ring: < 190 B) */
#define TST_LOGN 48u
#define TST_ALL 1024u                                 /* the events of a session whose place is kept for TAKEN */
#define TST_CHUNK_MS 3u                               /* a piece of a probe every 3 ms: the PC's MIDI driver keeps up */
#define TST_HDN 64u                                   /* 0.20.3: messages heard, not yet said to the PC */

typedef struct { uint32_t t, gc; uint16_t a, b; uint8_t kind; } tst_ev_t;
static tst_ev_t tst_q[TST_Q];
static uint8_t tst_qr, tst_qn;
static uint16_t tst_next, tst_head;                   /* the index the PC sends next; the index of the queue's head */
static uint8_t tst_state;                             /* 0 nothing, 1 asking, 2 yes, 3 no, 4 no answer */
static uint8_t tst_go, tst_reboot;
static uint32_t tst_t0, tst_until, tst_pass_ms;
static uint16_t tst_applied, tst_late, tst_lag;
static uint8_t tst_lost;
static struct { uint16_t idx; uint32_t ms, gc; } tst_log[TST_LOGN];
static uint8_t tst_log_n;
static uint32_t tst_log_ms, tst_chunk_ms;
static uint32_t tst_all_ms[TST_ALL], tst_all_gc[TST_ALL];
static char tst_pb[2][TST_PB];
static uint16_t tst_pb_len[2], tst_pb_pos[2], tst_pb_idx[2];
static uint8_t tst_pb_k[2], tst_pb_full[2], tst_pb_turn;
static uint8_t tst_out[200];
static struct { uint32_t ms, gc; uint8_t st, d1, d2, cab; } tst_hd[TST_HDN];
static uint8_t tst_hd_n, tst_hd_lost;
static uint16_t tst_hd_seq, tst_hd_all;              /* the number of the ring's first; every one heard this session */
static uint32_t tst_hd_ms;
static uint32_t tst_hellos, tst_frames, tst_unsent;   /* 0.20.9: since the boot (DIAG) */
static uint32_t tst_first_ms, tst_gap_max, tst_gap_ms;   /* the main loop's first pass, the longest it stood still */

static uint8_t *tst_frame(uint8_t cmd)
{
    uint8_t *q = tst_out;
    *q++ = 0xF0u; *q++ = 0x7Du; *q++ = 0x53u; *q++ = 0x47u; *q++ = cmd;
    return q;
}
static void tst_send(uint8_t *q) { *q++ = 0xF7u; if (sysex_send(tst_out, (uint32_t)(q - tst_out)) != 0) tst_unsent++; }
static void tst_answer(uint8_t sub, uint8_t v) { uint8_t *q = tst_frame(SX_TST_ANS); *q++ = sub; *q++ = (uint8_t)(v & 127u); tst_send(q); }
static uint8_t tst_noinit_ok(void) { return tst_noinit.magic == TST_MAGIC && tst_noinit.check == ~TST_MAGIC; }

/* ---- the probe: the whole machine as key=value, a line for the machine, one a track, one for the FM-1's own numbers.
 * Named fields for what a person would notice; a hash (#) for everything else, so no change goes unseen. "ok" = the track
 * is where its anchor and the clock say (the bar), "-" when that cannot be asked (stopped, a time FX, a DJ LOOP, RANDOM
 * direction, TAPE, a length waiting for the bar, a realign due at the next tick). */
static char *pr_p, *pr_end;
static void pr_c(char c) { if (pr_p < pr_end) *pr_p++ = c; }
static void pr_s(const char *s) { while (*s) pr_c(*s++); }
static void pr_u(uint32_t v) { char b[10]; uint32_t n = 0; do { b[n++] = (char)('0' + v % 10u); v /= 10u; } while (v && n < 10u); while (n) pr_c(b[--n]); }
static void pr_d(int32_t v) { if (v < 0) { pr_c('-'); pr_u((uint32_t)0 - (uint32_t)v); } else pr_u((uint32_t)v); }
static void pr_x(uint32_t v, uint32_t digits) { while (digits--) pr_c("0123456789ABCDEF"[(v >> (4u * digits)) & 15u]); }
static void pr_xm(uint32_t v) { uint32_t d = 1u; while (d < 8u && (v >> (4u * d))) d++; pr_x(v, d); }
static void pr_k(const char *k) { pr_c(' '); pr_s(k); pr_c('='); }
static void pr_ku(const char *k, uint32_t v) { pr_k(k); pr_u(v); }
static void pr_kh(const char *k, const void *p, uint32_t n);
static uint32_t probe_hash(const void *p, uint32_t n)
{
    const uint8_t *b = (const uint8_t *)p;
    uint32_t h = 2166136261u, i;
    for (i = 0; i < n; i++) h = (h ^ b[i]) * 16777619u;
    return h;
}
static void pr_kh(const char *k, const void *p, uint32_t n) { pr_k(k); pr_x(probe_hash(p, n), 8u); }

/* 0.24: the copies of track t, in order? (the explorer's rule COPIE.) Every pattern of the track: what is flagged after
 * the loop is the MARK of a pattern's end alone - one step at rest - and then nothing in the loop is flagged. The
 * pattern that plays: its copies are the end of the loop, each the step of the pattern it stands for (the service
 * sees to it within a pass or two of an edit). "-": not looked at - a TAPE track plays no steps, a loop between two
 * steps or a LOOP of the journey holds the track's length for a while. */
static const char *tst_copies_ok(uint32_t t)
{
    const sq_track_cfg_t *c = &project.track[t];
    const sq_step_t *row;
    uint32_t pat, i;
    uint8_t own;
    if (track_tape(t) || (sl_on & (1u << t)) || vg_chain_on[t] || c->start >= c->length) return "-";
    for (pat = 0; pat < SQ_PATTERNS; pat++) {
        uint32_t marks = 0u, in = 0u;
        row = project.step[t][pat];
        for (i = c->start; i < c->length; i++) if (row[i].flags & SQ_STEP_GHOST) in++;
        for (i = c->length; i < SQ_STEPS; i++) if (row[i].flags & SQ_STEP_GHOST) { if (!ghost_mark_(&row[i])) return "0"; marks++; }
        if (marks > 1u || (marks && in)) return "0";
    }
    row = project.step[t][tr[t].pattern];
    own = sq_row_own(row, c->start, c->length);
    if (!own) return "0";
    for (i = own; i < c->length; i++) if (!sq_step_alike(&row[i], &row[c->start + (i - c->start) % (uint32_t)(own - c->start)])) return "0";
    return "1";
}

static uint32_t probe_render(char *buf, uint32_t cap)
{
    uint32_t t;
    sq_hchord_t hc;
    char nm[16];
    const sq_gen_t *g = &project.gen;
    pr_p = buf; pr_end = buf + cap;
    if (harm_chord(&hc, 0)) sq_hchord_name(project.key_scale, &hc, nm); else { nm[0] = '-'; nm[1] = 0; }
    pr_s("PROBE G");
    pr_ku("play", playing); pr_ku("bpm", project.bpm); pr_ku("sel", selected_track + 1u); pr_ku("ui", ui_mode());
    pr_ku("home", home_page); pr_ku("seqp", seq_page); pr_ku("perf", perf_mode); pr_ku("fx", fx_now()); pr_ku("loop", loop_on);
    pr_k("win"); pr_d(win_cur == 255u ? -1 : (int32_t)win_cur);
    pr_ku("vg", vg_mosse_shown());   /* (0.17: the MOSSE page; the journey always runs) */ pr_k("vgspeed"); pr_d(vg_speed); pr_ku("grid", grid_attached); pr_ku("gview", g_view);
    pr_ku("gfollow", g_follow); pr_ku("tab", (uint32_t)foc_tab.track + 1u); pr_ku("tabseen", tab_seen);   /* 0.18: the grid FOLLOWs, the tablet's track */
    pr_ku("genre", g->genre); pr_ku("gmode", g->genre_mode); pr_ku("bfunc", g->func); pr_ku("bvar", g->var);
    pr_ku("harm", g->harm_on); pr_ku("hlock", g->harm_lock); pr_ku("hgenre", g->harm_genre); pr_ku("hprog", g->harm_prog);
    pr_ku("hbars", g->harm_bars); pr_ku("hrhythm", g->harm_rhythm); pr_ku("hmood", g->harm_mood); pr_k("chord"); pr_s(nm);
    pr_ku("key", project.key_cur); pr_ku("root", project.key_root); pr_ku("scale", project.key_scale);
    pr_k("shift"); pr_d(project.key_shift); pr_k("mute"); pr_x(mute_mask, 4u); pr_k("solo"); pr_x(solo_mask, 4u);
    pr_ku("scene", scene_cursor); pr_k("snap"); pr_d(snap_cur == 255u ? -1 : (int32_t)snap_cur);
    pr_k("mac"); pr_d(mac_vel); pr_c('/'); pr_d(mac_gate); pr_c('/'); pr_d(mac_swing); pr_c('/'); pr_d(mac_filt);
    pr_ku("upsel", uprog_sel); pr_ku("uppos", uprog_pos); pr_ku("dice", dice_pending);   /* (0.22: a dice waits: OCT and ALG are its keys) */
    pr_ku("thsrc", project.th.src); pr_ku("thseed", project.th.seed); pr_ku("en", vg_energy_now());   /* 0.23 THEORY: the SOURCE, the next seed, the energy applied now */
    pr_ku("bar", bar_st()); pr_k("beats"); pr_x(bar_bt(), 8u); pr_ku("barpend", bar_pend_steps); pr_ku("mid", metre_id_now());      /* 0.25 THE METRE: the bar in 16ths, its beats, the bar that waits */
    pr_ku("kbc", kb_chord_on); pr_ku("cnt", cnt_on); pr_ku("clk", clk_count); pr_ku("clkl", clk_last); pr_ku("clkt", clk_last_tick);   /* 0.26: the keyboard's chord is the harmony; the count runs; the clicks so far, the last one */
    pr_kh("set26#", &project.ext.click, 6u); pr_kh("smetre#", project.ext.scene_metre, sizeof project.ext.scene_metre);                /* ... the click's settings and SCENE METRE; the scenes' metres */
    pr_kh("uprog#", project.uprog, sizeof project.uprog); pr_kh("keys#", project.key, sizeof project.key);
    pr_kh("scenes#", project.scene, sizeof project.scene); pr_kh("lfo#", project.lfo, sizeof project.lfo);
    pr_kh("song#", &project.song, sizeof project.song); pr_kh("snaps#", project.snap, sizeof project.snap);
    pr_kh("live#", &project.live, sizeof project.live); pr_kh("gen#", &project.gen, sizeof project.gen);
    pr_kh("viaggio#", &project.viaggio, sizeof project.viaggio); pr_kh("dev#", project.device, sizeof project.device);
    pr_kh("tape#", project.tape_ev, sizeof project.tape_ev);
    pr_k("msg"); { const char *m = msg_text ? msg_text : ""; while (*m) { char c = *m++; pr_c((c >= 32 && c < 127) ? c : '?'); } }
    pr_c('\n');
    for (t = 0; t < SQ_TRACKS; t++) {
        const sq_track_cfg_t *c = &project.track[t];
        const char *ok = "-";
        uint32_t k, slots = 0u;
        if (playing && !track_tape(t) && !(loop_on && (loop_mask & (1u << t))) && !fx_now() && !vg_speed && c->direction != SQ_DIR_RANDOM && !len_pend[t] &&
            !(realign_pend & (1u << t)) && !(tup_wait & (1u << t))) {   /* (put in time on the next tick: a slave with no clock yet has none; 0.25: a
                                                                         *  polyrhythm's step that waits for its time between two ticks has not moved it yet) */
            sq_track_rt_t r = tr[t];
            track_seek_to(t, &r, global_clock - tr[t].anchor);
            ok = r.step == tr[t].step ? "1" : "0";
        }
        for (k = 0; k < SQ_ALGO_SLOTS; k++) if (SQ_ALGO_AT(c, k)->algo) slots |= 1u << k;
        pr_s("PROBE T"); pr_u(t + 1u);
        pr_ku("ch", c->channel + 1u); pr_ku("len", c->length); pr_ku("start", c->start); pr_ku("div", c->division);
        pr_ku("dir", c->direction); pr_k("mode"); pr_c("FKDTB"[track_mode(t)]); pr_ku("role", c->role); pr_ku("pen", c->pen);
        pr_ku("chord", c->chord); pr_k("oct"); pr_d(c->octave); pr_k("trans"); pr_d(c->transpose);
        pr_ku("follow", (c->flags & SQ_TF_FOLLOW) != 0u); pr_ku("fm", c->follow_mode); pr_k("flags"); pr_x(c->flags, 2u);
        pr_ku("euc", c->euc_pulses); pr_c('/'); pr_u(c->euc_rot); pr_ku("algo", c->algo); pr_k("slots"); pr_xm(slots);
        pr_ku("mfx", c->mfx); pr_k("mfxon"); pr_x(project.ext.mfxc[t].on, 2u); pr_k("mfxnew"); pr_x(project.ext.mfxd[t].on, 2u); pr_ku("pat", tr[t].pattern + 1u); pr_ku("step", tr[t].step); pr_k("ok"); pr_s(ok);
        pr_ku("lenpend", len_pend[t]); pr_ku("src", c->src_genre); pr_c('/'); pr_u(c->src_func); pr_c('/'); pr_u(c->src_var);
        pr_k("gh"); pr_s(tst_copies_ok(t)); pr_ku("own", sq_row_own(project.step[t][tr[t].pattern], c->start, c->length));   /* 0.24: the copies in order, the pattern's own length */
        {   /* 0.23: what the THEORY engines know of the pattern the track plays: style + 1 (0: not theirs) / seed / variation / its size / energy */
            const sq_thpat_t *m = &project.th.pat[t][tr[t].pattern];
            pr_ku("th", m->style & 31u); pr_c('/'); pr_u(m->seed); pr_c('/'); pr_u(m->var); pr_c('/'); pr_u(SQ_THP_VARY(m)); pr_c('/'); pr_u(m->energy);
            pr_ku("thm", m->metre);                                  /* (0.25: the metre it was made in - G's mid: the metre now -, */
            pr_ku("thk", (th_kept[t] >> tr[t].pattern) & 1u);        /*  and whether it stays in it: the player changed it by hand) */
            pr_ku("thv", ((m->style & 31u) && (m->style & SQ_THP_V26) ? 1u : 0u) + (SQ_THP_NOTES(m) && (m->style & 31u) ? 2u : 0u));   /* 0.26: 1 made in the bar, 3 and its answers have notes */
            pr_ku("thl", (m->style & 31u) ? th_rec_len(m) : 0u);     /* (... the steps it was made of) */
        }
        pr_kh("steps#", project.step[t][tr[t].pattern], sizeof project.step[t][0]);
        pr_kh("pats#", project.step[t], sizeof project.step[t]); pr_kh("cfg#", c, sizeof *c);
        pr_c('\n');
    }
    pr_s("PROBE H"); pr_ku("ms", fm1_ms); pr_ku("gc", global_clock); pr_ku("lag", tst_lag); pr_ku("late", tst_late);
    pr_ku("lost", tst_lost); pr_ku("q", tst_qn); pr_ku("boots", tst_noinit.boots); pr_ku("test", tst_on);
    pr_c('\n');
    return (uint32_t)(pr_p - buf);
}

static void tst_probe_take(uint16_t idx)
{
    uint32_t i = tst_pb_full[0] ? (tst_pb_full[1] ? 2u : 1u) : 0u;
    if (i > 1u) { tst_lost++; return; }                 /* (both still on their way: never with probes 0.7 s apart) */
    tst_pb_len[i] = (uint16_t)probe_render(tst_pb[i], TST_PB);
    tst_pb_pos[i] = 0u; tst_pb_k[i] = 0u; tst_pb_idx[i] = idx; tst_pb_full[i] = 1u;
    if (!tst_pb_full[i ^ 1u]) tst_pb_turn = (uint8_t)i;
    tst_lag = 0u;                                       /* (the worst pass since the probe before) */
}

/* ---- the events */
static void tst_log_flush(uint8_t force)
{
    uint8_t *q;
    uint32_t i, n;
    if (!tst_log_n || (!force && tst_log_n < 8u && !time_due(fm1_ms, tst_log_ms + 40u))) return;
    n = tst_log_n < 12u ? tst_log_n : 12u;
    q = tst_frame(SX_TST_LOG);
    *q++ = (uint8_t)n;
    for (i = 0; i < n; i++) { sx_put7(&q, tst_log[i].idx, 2u); sx_put7(&q, tst_log[i].ms, 4u); sx_put7(&q, tst_log[i].gc, 4u); }
    *q++ = 0xF7u;
    if ((force || tst_log_n >= TST_LOGN - 12u ? sysex_send(tst_out, (uint32_t)(q - tst_out)) : sysex_try_send(tst_out, (uint32_t)(q - tst_out))) != 0) return;
    for (i = n; i < tst_log_n; i++) tst_log[i - n] = tst_log[i];
    tst_log_n = (uint8_t)(tst_log_n - n);
    tst_log_ms = fm1_ms;
}

/* 0.20.3: a message from the ports, heard while the PC listens (dinghy.c handle_midi_in, before it is played) */
static void tst_heard(uint8_t st, uint8_t d1, uint8_t d2, uint8_t cab)
{
    if (!tst_on || !tst_go) return;
    tst_hd_all++;
    if (tst_hd_n >= TST_HDN) { if (tst_hd_lost < 127u) tst_hd_lost++; return; }
    if (!tst_hd_n) tst_hd_ms = fm1_ms;
    tst_hd[tst_hd_n].ms = fm1_ms; tst_hd[tst_hd_n].gc = global_clock;
    tst_hd[tst_hd_n].st = st; tst_hd[tst_hd_n].d1 = d1; tst_hd[tst_hd_n].d2 = d2; tst_hd[tst_hd_n].cab = cab;
    tst_hd_n++;
}

static void tst_heard_flush(uint8_t force)
{
    uint8_t *q;
    uint32_t i, n;
    if (!tst_hd_n || (!force && tst_hd_n < 8u && !time_due(fm1_ms, tst_hd_ms + 20u))) return;
    n = tst_hd_n < 12u ? tst_hd_n : 12u;
    q = tst_frame(SX_TST_HEARD);
    sx_put7(&q, tst_hd_seq, 2u);
    *q++ = (uint8_t)n;
    for (i = 0; i < n; i++) {
        sx_put7(&q, tst_hd[i].ms, 4u); sx_put7(&q, tst_hd[i].gc, 4u);
        *q++ = (uint8_t)(tst_hd[i].st & 127u); *q++ = (uint8_t)(tst_hd[i].d1 & 127u); *q++ = (uint8_t)(tst_hd[i].d2 & 127u);
        *q++ = (uint8_t)(tst_hd[i].cab & 127u);
    }
    *q++ = 0xF7u;
    if ((force || tst_hd_n >= TST_HDN - 12u ? sysex_send(tst_out, (uint32_t)(q - tst_out)) : sysex_try_send(tst_out, (uint32_t)(q - tst_out))) != 0) return;
    for (i = n; i < tst_hd_n; i++) tst_hd[i - n] = tst_hd[i];
    tst_hd_n = (uint8_t)(tst_hd_n - n);
    tst_hd_seq = (uint16_t)(tst_hd_seq + n);
    tst_hd_ms = fm1_ms;
}

static void tst_done(void)
{
    uint8_t *q;
    while (tst_log_n) { uint8_t was = tst_log_n; tst_log_flush(1u); if (tst_log_n == was) break; }
    while (tst_hd_n) { uint8_t was = tst_hd_n; tst_heard_flush(1u); if (tst_hd_n == was) break; }
    q = tst_frame(SX_TST_ANS);
    *q++ = TQ_DONE;
    sx_put7(&q, tst_applied, 2u); sx_put7(&q, tst_late, 2u); sx_put7(&q, tst_lag, 2u); *q++ = (uint8_t)(tst_lost & 127u);
    if (tst_listen) { sx_put7(&q, tst_hd_all, 2u); *q++ = tst_hd_lost; }   /* (0.20.3) */
    tst_send(q);
}

static void tst_apply(const tst_ev_t *e, uint16_t idx)
{
    uint32_t gc = global_clock;                         /* (0.18: where it was taken: before it - a MIDI event acts at once,
                                                         *  and a grid's BAR jump moves the clock itself) */
    switch (e->kind) {
    case TK_PRESS:   if (e->a < 14u) { tst_buttons |= 1u << e->a; tst_edges |= 1u << e->a; } break;
    case TK_RELEASE: if (e->a < 14u) tst_buttons &= ~(1u << e->a); break;
    case TK_ENC:     if (e->a < 8u) tst_enc[e->a] += (int32_t)e->b - 8192; break;
    case TK_KNOB:    tst_knob_on = 1u; tst_knob_v = e->a > 1023u ? 1023u : e->a; fm1_knob = tst_knob_v; break;
    case TK_KEYS:    tst_notes = ((uint32_t)e->a | (uint32_t)e->b << 14) & 0x7FFFFFFu; break;
    case TK_PROBE:   tst_probe_take(idx); break;
    case TK_MIDI: {                                 /* 0.18: as if it came in (the PC is the tablet, the grid) */
        uint8_t code = (uint8_t)(e->a >> 7), cab = code == 2u ? (uint8_t)CTL_CABLE : (uint8_t)(code & 1u);
        midi_in_one(sq_micros(), (uint8_t)(0x80u | (e->a & 0x7Fu)), (uint8_t)(e->b & 127u), (uint8_t)((e->b >> 7) & 127u), cab);
        break;
    }
    default: break;
    }
    if (idx < TST_ALL) { tst_all_ms[idx] = fm1_ms; tst_all_gc[idx] = gc; }
    if (tst_log_n < TST_LOGN) {
        if (!tst_log_n) tst_log_ms = fm1_ms;
        tst_log[tst_log_n].idx = idx; tst_log[tst_log_n].ms = fm1_ms; tst_log[tst_log_n].gc = gc;
        tst_log_n++;
    }
    tst_applied++;
    if (e->kind == TK_END) tst_done();
}

static void tst_abort(const char *why)
{
    if (!tst_on) return;
    tst_on = 0u; tst_go = 0u; tst_qn = 0u;
    tst_buttons = tst_notes = tst_edges = 0u;
    memset(tst_enc, 0, sizeof tst_enc);
    tst_knob_on = 0u;                                   /* (the MASTER is the hand's again) */
    status_msg(why);
    msg_until = fm1_ms + 8000u;
    tst_answer(TQ_ABORT, 1u);
}

/* the hands' button edges: while the PC asks, SEL = yes and anything else = no; while it tests, any = stop */
static uint32_t tst_hands(uint32_t edges)
{
    if (!edges) return 0u;
    if (tst_state == 1u) {
        tst_state = edges == (1u << BTN_SEL) ? 2u : 3u;
        status_msg(tst_state == 2u ? "PC TEST: YES" : "PC TEST: NO");
        tst_until = fm1_ms + 60000u;                    /* (a yes not used within a minute is forgotten) */
        tst_answer(TQ_OPEN, tst_state);
        return 1u;
    }
    if (tst_on) { tst_abort("PC TEST STOPPED: A KEY BY HAND"); return 1u; }
    return 0u;
}

/* app_main, before the project: 1 = this boot is the test's (tst_noinit says so) */
static uint8_t tst_boot_begin(void)
{
    if (!tst_noinit_ok()) return 0u;
    tst_noinit.boots++;
    tst_booted = 1u; tst_on = 1u; tst_state = 2u;
    fl_app_lock = 1u;                                   /* the slots and the settings: never written (platform.c) */
    tst_knob_on = 1u; tst_knob_v = 512u; fm1_knob = 512u;   /* the MASTER where the simulator has it */
    return 1u;
}

/* every pass of the main loop, before the buttons */
static void tst_service(void)
{
    uint32_t now = fm1_ms, guard = 0u;
    if (tst_pass_ms && now - tst_pass_ms > tst_lag) tst_lag = (uint16_t)(now - tst_pass_ms > 65535u ? 65535u : now - tst_pass_ms);
    tst_pass_ms = now;
    if (!tst_first_ms) tst_first_ms = now ? now : 1u;   /* 0.20.9 (DIAG): since the boot, never zeroed by GO */
    else if (now - tst_gap_ms > tst_gap_max) tst_gap_max = now - tst_gap_ms;
    tst_gap_ms = now;
    if (tst_state == 1u) {
        if (fm1_in.notes) { tst_state = 3u; status_msg("PC TEST: NO"); tst_answer(TQ_OPEN, 3u); }
        else if (time_due(now, tst_until)) { tst_state = 4u; status_msg("PC TEST: NO ANSWER"); tst_answer(TQ_OPEN, 4u); }
    } else if (tst_state == 2u && !tst_booted && !tst_reboot && time_due(now, tst_until)) tst_state = 0u;
    if (tst_reboot && time_due(now, tst_until)) platform_test_reboot();
    if (tst_on && (fm1_in.buttons || fm1_in.notes)) tst_abort("PC TEST STOPPED: A KEY BY HAND");
    while (tst_on && tst_go && tst_qn && guard++ < 16u) {
        const tst_ev_t *e = &tst_q[tst_qr];
        int32_t late = (int32_t)(now - (tst_t0 + e->t));
        if (e->gc == TST_NOGC) {
            if (late < 0) break;
        } else if (late < 50) {                         /* the simulator replaying: between the same two ticks */
            uint8_t ticks = playing && project.clock_mode == SQ_CLOCK_MASTER;
            if (late < -1 || global_clock < e->gc) break;
            /* a ms early only when the next tick comes before the next pass: else it would land after that tick */
            if (late == -1 && !(ticks && global_clock == e->gc && time_due(sq_micros() + 1000u, next_master_clock_us))) break;
        }
        if (late > 5) tst_late++;
        tst_apply(e, tst_head);
        tst_qr = (uint8_t)((tst_qr + 1u) % TST_Q); tst_qn--; tst_head++;
    }
    tst_log_flush(0u);
    tst_heard_flush(0u);
    {   /* a piece of the probe that waits, when the ring has room for it (the sequencer never waits for the PC) */
        uint32_t i = tst_pb_turn;
        if (tst_pb_full[i] && time_due(now, tst_chunk_ms + TST_CHUNK_MS)) {
            uint32_t n = tst_pb_len[i] - tst_pb_pos[i], k;
            uint8_t *q = tst_frame(SX_TST_PROBE);
            if (n > TST_CHUNK) n = TST_CHUNK;
            sx_put7(&q, tst_pb_idx[i], 2u);
            *q++ = (uint8_t)(tst_pb_k[i] & 127u);
            *q++ = tst_pb_pos[i] + n >= tst_pb_len[i] ? 1u : 0u;
            for (k = 0; k < n; k++) *q++ = (uint8_t)(tst_pb[i][tst_pb_pos[i] + k] & 127);
            *q++ = 0xF7u;
            if (sysex_try_send(tst_out, (uint32_t)(q - tst_out)) == 0) {
                tst_chunk_ms = now;
                tst_pb_pos[i] = (uint16_t)(tst_pb_pos[i] + n); tst_pb_k[i]++;
                if (tst_pb_pos[i] >= tst_pb_len[i]) { tst_pb_full[i] = 0u; if (tst_pb_full[i ^ 1u]) tst_pb_turn = (uint8_t)(i ^ 1u); }
            }
        }
    }
}

/* SysEx 70 from the PC (sagga_store.c app_sysex) */
static void tst_sysex_in(const uint8_t *p, uint32_t n)
{
    uint8_t *q;
    if (n < 1u) return;
    tst_frames++;
    switch (p[0]) {
    case TQ_HELLO:
        tst_hellos++;
        q = tst_frame(SX_TST_ANS);
        *q++ = TQ_HELLO; *q++ = tst_state; *q++ = tst_booted; *q++ = playing ? 1u : 0u;
        sx_put7(&q, tst_noinit_ok() ? tst_noinit.boots : 0u, 2u);
        sx_put7(&q, tst_noinit_ok() ? tst_noinit.fault_vec : 0u, 5u); sx_put7(&q, tst_noinit_ok() ? tst_noinit.fault_pc : 0u, 5u);
        sx_put7(&q, fm1_ms, 4u);
        *q++ = usb_ports; *q++ = (uint8_t)(vg_profile & 127u);
        { const char *v = SQ_VERSION; while (*v) *q++ = (uint8_t)*v++; }
        tst_send(q);
        break;
    case TQ_OPEN:
        if (tst_booted || tst_state == 2u) { tst_answer(TQ_OPEN, 2u); break; }
        if (playing) { tst_answer(TQ_OPEN, 5u); status_msg("PC TEST: STOP FIRST"); break; }
        tst_state = 1u; tst_until = fm1_ms + 20000u;
        status_msg("PC TEST? SEL = YES, ANOTHER KEY = NO");
        msg_until = tst_until;
        tst_answer(TQ_OPEN, 1u);
        break;
    case TQ_BOOT:
        if (!(tst_booted || tst_state == 2u) || (playing && !tst_booted) || tst_reboot) { tst_answer(TQ_BOOT, 0u); break; }
        if (playing) transport_stop();
        panic_all();
        if (!tst_noinit_ok()) { tst_noinit.boots = 0u; tst_noinit.fault_vec = tst_noinit.fault_pc = 0u; }
        tst_noinit.magic = TST_MAGIC; tst_noinit.check = ~TST_MAGIC;
        tst_answer(TQ_BOOT, 1u);
        status_msg("PC TEST: REBOOT");
        tst_reboot = 1u; tst_until = fm1_ms + 80u;     /* (the answer goes out first) */
        break;
    case TQ_GO:
        if (!tst_booted || !tst_on) { tst_answer(TQ_GO, 0u); break; }
        tst_t0 = fm1_ms; tst_go = 1u; tst_qn = 0u; tst_qr = 0u; tst_next = tst_head = 0u;
        tst_noinit.fault_vec = tst_noinit.fault_pc = 0u;   /* (a crash from here on is this session's) */
        tst_applied = tst_late = tst_lag = 0u; tst_lost = 0u; tst_log_n = 0u;
        tst_listen = n >= 2u && (p[1] & 1u);            /* 0.20.3: hear the ports too (the banco) */
        tst_hd_n = 0u; tst_hd_lost = 0u; tst_hd_seq = tst_hd_all = 0u;
        q = tst_frame(SX_TST_ANS); *q++ = TQ_GO; sx_put7(&q, tst_t0, 4u); tst_send(q);
        break;
    case TQ_EV: {
        uint32_t idx, cnt, i, free = TST_Q - tst_qn, ok = 0u;
        if (tst_on && tst_go && n >= 4u) {
            idx = sx_get7(p + 1, 2u); cnt = p[3];
            if (idx == tst_next && cnt <= free && n >= 4u + 13u * cnt) {
                for (i = 0; i < cnt; i++) {
                    const uint8_t *s = p + 4u + 13u * i;
                    tst_ev_t *e = &tst_q[(tst_qr + tst_qn) % TST_Q];
                    e->t = sx_get7(s, 4u); e->kind = s[4]; e->a = (uint16_t)sx_get7(s + 5, 2u); e->b = (uint16_t)sx_get7(s + 7, 2u);
                    e->gc = sx_get7(s + 9, 4u);
                    tst_qn++;
                }
                tst_next = (uint16_t)(tst_next + cnt);
                ok = 1u;
            }
        }
        q = tst_frame(SX_TST_ANS); *q++ = TQ_EV; *q++ = (uint8_t)ok; sx_put7(&q, tst_next, 2u); *q++ = (uint8_t)(TST_Q - tst_qn); tst_send(q);
        break;
    }
    case 6: {                                           /* AGAIN: a probe still kept, from its first piece */
        uint32_t idx = n >= 3u ? sx_get7(p + 1, 2u) : 0xFFFFu, i;
        for (i = 0; i < 2u; i++)
            if (tst_pb_len[i] && tst_pb_idx[i] == idx && !tst_pb_full[i]) {
                tst_pb_pos[i] = 0u; tst_pb_k[i] = 0u; tst_pb_full[i] = 1u;
                if (!tst_pb_full[i ^ 1u]) tst_pb_turn = (uint8_t)i;
            }
        break;
    }
    case 7: {                                           /* TAKEN: where these events were taken, again */
        uint32_t idx = n >= 4u ? sx_get7(p + 1, 2u) : TST_ALL, cnt = n >= 4u ? p[3] : 0u, i, k;
        while (cnt && idx < TST_ALL && idx < tst_head) {
            uint32_t m = cnt < 12u ? cnt : 12u;
            if (idx + m > tst_head) m = tst_head - idx;
            q = tst_frame(SX_TST_LOG);
            *q++ = (uint8_t)m;
            for (k = 0; k < m; k++) { i = idx + k; sx_put7(&q, i, 2u); sx_put7(&q, tst_all_ms[i], 4u); sx_put7(&q, tst_all_gc[i], 4u); }
            tst_send(q);
            idx += m; cnt -= m;
        }
        break;
    }
    case 8: {                                           /* 0.20.9 DIAG: the counters since the boot */
        uint32_t d[USB_DIAG_N], i;
        usb_diag(d);
        q = tst_frame(SX_TST_ANS); *q++ = 8u;
        sx_put7(&q, tst_hellos, 4u); sx_put7(&q, tst_frames, 4u); sx_put7(&q, tst_unsent, 4u);
        sx_put7(&q, tst_first_ms, 4u); sx_put7(&q, tst_gap_max, 4u);
        for (i = 0u; i < USB_DIAG_N; i++) sx_put7(&q, d[i], 4u);
        sx_put7(&q, fm1_ms, 4u);
        {   /* 0.23.1: what the app sent, by port and kind, and the output ring's own account (the tools before it stop reading at the ms) */
            uint32_t d2[USB_DIAG2_N], k;
            usb_diag2(d2);
            for (i = 0u; i < 2u; i++) for (k = 0u; k < SQ_OUT_KINDS; k++) sx_put7(&q, sq_out_cnt[i][k], 4u);
            for (i = 0u; i < USB_DIAG2_N; i++) sx_put7(&q, d2[i], 4u);
        }
        tst_send(q);
        break;
    }
    case 9:                                             /* 0.23.1 QUIET: the session is over - stopped, every note off, no event taken any more: DIAG's counts stand still */
        if (!tst_booted || !tst_on) { tst_answer(9u, 0u); break; }
        tst_go = 0u; tst_qn = 0u;
        if (playing) transport_stop();
        panic_all();
        tst_answer(9u, 1u);
        break;
    case TQ_CLOSE:
        if (!tst_booted) { tst_state = 0u; tst_answer(TQ_CLOSE, 0u); break; }   /* (only a test boot is ended by a reboot) */
        if (playing) transport_stop();
        panic_all();
        tst_noinit.magic = tst_noinit.check = 0u;
        tst_answer(TQ_CLOSE, 1u);
        status_msg("PC TEST: OVER");
        tst_reboot = 1u; tst_until = fm1_ms + 80u;
        break;
    default: break;
    }
}
