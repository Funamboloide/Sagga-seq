/* SPDX-License-Identifier: GPL-3.0-only */
/* SAGGA SEQ 0.11: the patterns the Raspberry Pi keeps (the grid bridge: tools/sagga_grid_bridge.py, its files in
 * <the projects folder>/patterns, one per genre). Included by dinghy.c after sagga_store.c (one translation unit).
 *
 * The FM-1 has 12 variations of a main part and 6 of the others; the Pi has as many more as it likes (gen_beats.py
 * writes the next 12 / 6, and every pattern saved from the FM-1 goes there too). SEQ + ALG goes on past the last of
 * the FM-1's into the Pi's ("#14/12+PI"); BEAT asks the Pi for that one and loads it when it comes (a part of the
 * genre: the line or the chords on the track's root, like the library's). SEQ + SAVE sends the selected track's loop
 * to the Pi as a new pattern of the genre and of the track's part.
 *
 * SysEx, F0 7D 53 47 CMD ... F7, every byte 7-bit:
 *   60 G P                                    how many patterns of genre G, part P (SQ_FUNC_*)        (to the Pi)
 *   61 G P N N                                that many (14 bits, LSB first)                          (to the FM-1)
 *   62 G P I I                                pattern I (14 bits) of the Pi's, the first is 0         (to the Pi)
 *   63 G P I I LEN HAS TEXT[LEN] NOTES[LEN]   it (LEN 0: none; HAS 0: a drum, no NOTES)               (to the FM-1)
 *   64 G P LEN HAS TEXT[LEN] NOTES[LEN]       a new pattern to keep                                   (to the Pi)
 *   65 G P CODE I I                           kept as pattern I (CODE 0), or not (1: cannot write, 2: not a pattern)
 * TEXT is the library's: . x X o g 2 3 4 -  ; NOTES: a hex semitone above the root (a line), m M n N 7 s 5 (chords). */
#define PIPAT_ASK_MS  2000u          /* the count of a part is asked again after this */
#define PIPAT_WAIT_MS 1500u          /* a pattern asked for that does not come: given up */
enum { SX_PAT_ASK = 0x60, SX_PAT_COUNT = 0x61, SX_PAT_GET = 0x62, SX_PAT = 0x63, SX_PAT_PUT = 0x64, SX_PAT_SAVED = 0x65 };

static uint8_t pi_pat_n[SQ_GENRES][SQ_FUNCS];        /* the Pi's patterns of a part (255: not known yet) */
static uint32_t pi_asked_ms[SQ_GENRES];              /* when a count of the genre was asked last */
static struct { uint8_t on, t, pat, genre, func; uint16_t idx; uint32_t ms; } pi_get;

static void piprog_init(void);                       /* (below: the progressions) */
static void piprog_tick(void);
static void pipat_init(void)
{
    memset(pi_pat_n, 255, sizeof pi_pat_n);
    memset(pi_asked_ms, 0, sizeof pi_asked_ms);
    pi_get.on = 0u;
    piprog_init();
}

static uint8_t pipat_loadable(uint8_t f) { return (uint8_t)(f < SQ_FUNCS && f != SQ_FUNC_PROG && f != SQ_FUNC_KIT); }

static void pipat_ask(uint8_t g, uint8_t f)
{
    uint8_t *q;
    if (g >= SQ_GENRES || !pipat_loadable(f)) return;
    if (pi_asked_ms[g] && (uint32_t)(fm1_ms - pi_asked_ms[g]) < PIPAT_ASK_MS) return;
    pi_asked_ms[g] = fm1_ms ? fm1_ms : 1u;
    q = sx_head(SX_PAT_ASK);
    *q++ = g; *q++ = f; *q++ = 0xF7u;
    sysex_send(sx_out, (uint32_t)(q - sx_out));
}

/* the Pi's patterns of a part as far as it is known (0 until it says; asking it, now and then) */
static uint8_t pipat_count(uint8_t g, uint8_t f)
{
    if (g >= SQ_GENRES || !pipat_loadable(f)) return 0u;
    if (pi_pat_n[g][f] == 255u) { pipat_ask(g, f); return 0u; }
    return pi_pat_n[g][f];
}

/* BEAT on a variation past the FM-1's: ask the Pi; it is loaded when it comes */
static void pipat_get(uint8_t t, uint8_t g, uint8_t f, uint16_t idx)
{
    uint8_t *q;
    char *p = msg_buf;
    if (t >= SQ_TRACKS || track_tape(t)) return;
    pi_get.on = 1u; pi_get.t = t; pi_get.pat = tr[t].pattern; pi_get.genre = g; pi_get.func = f; pi_get.idx = idx;
    pi_get.ms = fm1_ms;
    q = sx_head(SX_PAT_GET);
    *q++ = g; *q++ = f; sx_put7(&q, idx, 2u); *q++ = 0xF7u;
    sysex_send(sx_out, (uint32_t)(q - sx_out));
    p = put_s(p, "PI: "); p = put_s(p, sq_func_name(f)); p = put_s(p, " #");
    p = put_u(p, (uint32_t)sq_beat_variants(g, f) + idx + 1u); p = put_s(p, " ..."); finish(p);
    status_msg(msg_buf);
}

static void pipat_tick(void)
{
    piprog_tick();
    if (pi_get.on && (uint32_t)(fm1_ms - pi_get.ms) > PIPAT_WAIT_MS) {
        pi_get.on = 0u;
        status_msg("PI: NO ANSWER (THE GRID BRIDGE?)");
    }
}

/* the pattern came: onto the track it was asked for, as the library's would go */
static void pipat_loaded(const uint8_t *text, const uint8_t *notes, uint8_t n)
{
    static char r[SQ_STEPS + 1u], nt[SQ_STEPS + 1u];
    uint8_t t = pi_get.t, f = pi_get.func, g = pi_get.genre, len, note, nv, i, want = lib_len_steps();
    sq_track_cfg_t *c = &project.track[t];
    sq_step_t *row = project.step[t][pi_get.pat < SQ_PATTERNS ? pi_get.pat : tr[t].pattern];
    beat_cfg_t o;
    char *p = msg_buf;
    for (i = 0; i < n; i++) { r[i] = (char)text[i]; nt[i] = notes ? (char)notes[i] : '.'; }
    r[n] = nt[n] = 0;
    note = sq_func_kind(f) != SQ_KIND_DRUM ? gen_root_note(t) : PEN(t);
    undo_begin();
    undo_add(t, pi_get.pat);
    len = sq_beat_load_text(row, r, notes ? nt : 0, f, note);
    if (!len) { status_msg("PI: NOT A PATTERN OF THIS PART"); return; }
    if (len < want && want % len == 0u) { for (i = len; i < want; i++) row[i] = row[i % len]; len = want; }   /* (the library's length: repeated) */
    beat_cfg_for(c, g, f, len, note, &o);
    beat_cfg_apply(t, &o);
    nv = sq_beat_variants(g, f);
    c->src_func = f; c->src_var = (uint8_t)(nv ? nv - 1u : 0u);     /* (COOK walks on to the FM-1's first) */
    c->src_genre = g;
    if (!c->role) c->role = sq_func_role(f);
    harm_follow_genre(g);
    track_loaded(t);
    activate_row(t, row);
    p = put_s(p, sq_genre_name(g)); p = put_s(p, " "); p = put_s(p, sq_func_name(f)); p = put_s(p, " #");
    p = put_u(p, (uint32_t)nv + pi_get.idx + 1u); p = put_s(p, " (PI)"); finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}

static void pipat_in(uint8_t cmd, const uint8_t *p, uint32_t n)
{
    uint8_t g, f;
    if (n < 2u) return;
    g = p[0]; f = p[1];
    if (g >= SQ_GENRES || f >= SQ_FUNCS) return;
    if (cmd == SX_PAT_COUNT && n >= 4u) {
        uint32_t k = sx_get7(p + 2, 2u);
        pi_pat_n[g][f] = (uint8_t)(k > 250u ? 250u : k);
        ui_dirty = grid_dirty = 1u;
    } else if (cmd == SX_PAT && n >= 6u) {
        uint32_t idx = sx_get7(p + 2, 2u), len = p[4], has = p[5];
        if (!pi_get.on || g != pi_get.genre || f != pi_get.func || idx != pi_get.idx) return;   /* (not the one asked for) */
        pi_get.on = 0u;
        if (!len || len > SQ_STEPS || n < 6u + len * (has ? 2u : 1u)) { status_msg("PI: NO SUCH PATTERN"); return; }
        pipat_loaded(p + 6, has ? p + 6 + len : 0, (uint8_t)len);
    } else if (cmd == SX_PAT_SAVED && n >= 5u) {
        char *q = msg_buf;
        uint32_t idx = sx_get7(p + 3, 2u);
        if (p[2]) { status_msg(p[2] == 1u ? "PI: COULD NOT WRITE THE PATTERN" : "PI: NOT A PATTERN"); return; }
        if (idx < 250u) pi_pat_n[g][f] = (uint8_t)(idx + 1u);
        q = put_s(q, "ON THE PI: "); q = put_s(q, sq_genre_name(g)); q = put_s(q, " "); q = put_s(q, sq_func_name(f));
        q = put_s(q, " #"); q = put_u(q, (uint32_t)sq_beat_variants(g, f) + idx + 1u); finish(q);
        status_msg(msg_buf);
    }
}

/* SEQ + SAVE: the selected track's loop to the Pi, a new pattern of the genre (the machine's) and of the track's part */
static void pipat_save(void)
{
    static uint8_t text[SQ_STEPS], notes[SQ_STEPS];
    uint8_t t = selected_track, f, kind, root, len, i, has;
    const sq_track_cfg_t *c = &project.track[t];
    const sq_step_t *row = project.step[t][tr[t].pattern];
    uint8_t *q;
    char *p = msg_buf;
    if (track_tape(t)) { status_msg("A TAPE TRACK: NO STEPS TO SAVE"); return; }
    f = c->role ? sq_role_func(c->role) : sq_beat_role(track_drum(t), PEN(t));
    if (f == SQ_FUNC_PROG) f = SQ_FUNC_CHORD;
    if (!pipat_loadable(f)) { status_msg("NO PART: GIVE THE TRACK A ROLE (HOME 4 K2)"); return; }
    kind = sq_func_kind(f);
    root = sq_part_root(f, kind != SQ_KIND_DRUM ? gen_root_note(t) : PEN(t));
    len = (uint8_t)(c->length > c->start ? (uint8_t)(c->length - c->start) : 1u);
    for (i = 0; i < len; i++) { text[i] = '.'; notes[i] = '.'; }
    for (i = 0; i < len; i++) {
        const sq_step_t *s = &row[c->start + i];
        uint8_t span, k;
        if (!(s->flags & SQ_STEP_ON)) continue;
        text[i] = (uint8_t)(s->ratchet >= 2u && s->ratchet <= 4u ? '0' + s->ratchet : s->velocity >= 115u ? 'X' : s->velocity >= 90u ? 'x' : s->velocity >= 55u ? 'o' : 'g');
        if (kind == SQ_KIND_MONO) {
            int32_t d = (int32_t)(s->note[0] <= 127u ? s->note[0] : root) - (int32_t)root;
            while (d < 0) d += 12;
            while (d > 15) d -= 12;
            notes[i] = (uint8_t)(d < 10 ? '0' + d : 'a' + d - 10);
        } else if (kind == SQ_KIND_CHORD) notes[i] = (uint8_t)sq_chord_kind_of(s->note);
        span = sq_gate_span(s->length);
        for (k = 1u; k < span && i + k < len && !(row[c->start + i + k].flags & SQ_STEP_ON); k++) text[i + k] = '-';
    }
    for (i = 0; i < len; i++) if (text[i] != '.' && text[i] != '-') break;
    if (i == len) { status_msg("NOTHING WRITTEN TO SAVE"); return; }
    has = kind != SQ_KIND_DRUM ? 1u : 0u;
    q = sx_head(SX_PAT_PUT);
    *q++ = beat_genre; *q++ = f; *q++ = len; *q++ = has;
    for (i = 0; i < len; i++) *q++ = text[i];
    if (has) for (i = 0; i < len; i++) *q++ = notes[i];
    *q++ = 0xF7u;
    sysex_send(sx_out, (uint32_t)(q - sx_out));
    p = put_s(p, "TO THE PI: "); p = put_s(p, sq_genre_name(beat_genre)); p = put_s(p, " "); p = put_s(p, sq_func_name(f)); finish(p);
    status_msg(msg_buf);
}

/* ---- 0.11: the progressions the Pi keeps (tools/hub/sagga_progs.py: <the projects folder>/progressions, a file a genre,
 * each progression with its mood). SEQ 4 K2 goes on past the FM-1's progressions (the genre's six, the player's four, the
 * DICE/PI one) into the Pi's of the HARMONY's genre and of the MOOD chosen (ANY: all), the most like the progression
 * that played first; each comes into the fifth slot (DICE/PI) and plays. K2 back below the first: the one before. On
 * SEQ 4 (the progression playing) and SEQ 8 (the one being written) SEQ + SAVE sends it to the Pi, with its mood.
 *
 * SysEx (7-bit; SEMI 0..11 the root above the key's, SHAPE 6..36 SQ_HSHAPE_CH + SQ_CH_*, DUR 0..64 16ths, PUSH 0..4):
 *   66 G M                                           how many of genre G, mood M (0: all)          (to the Pi)
 *   67 G M N N                                       that many (14 bits)                           (to the FM-1)
 *   68 G M I I R (SEMI SHAPE)[R]                     the I-th, in order of likeness to the R chords  (to the Pi)
 *   69 G M I I N MOOD (SEMI SHAPE DUR PUSH)[N]       it (N 0: none)                                (to the FM-1)
 *   6A G MOOD N (SEMI SHAPE DUR PUSH)[N]             a new one to keep                             (to the Pi)
 *   6B G MOOD CODE I I                               kept as the I-th of its mood (CODE 0), or not (1, 2)   */
enum { SX_PROG_ASK = 0x66, SX_PROG_COUNT = 0x67, SX_PROG_GET = 0x68, SX_PROG = 0x69, SX_PROG_PUT = 0x6A, SX_PROG_SAVED = 0x6B };

static uint8_t pi_prog_n[SQ_GENRES][SQ_MOODS];        /* (255: not known yet) */
static uint32_t pi_prog_asked_ms;
static uint8_t pi_prog_quiet;                         /* the Pi did not answer the last time: asked, not waited for */
static struct {
    int16_t cur;                 /* the Pi's progression playing as K2 browses them (-1: not browsing them) */
    uint8_t from;                /* harm_prog before K2 went into the Pi's */
    uint8_t want, on, genre, mood;
    uint16_t idx;
    uint32_t ms;
    uint8_t refn, ref_semi[SQ_HPROG_CH], ref_shape[SQ_HPROG_CH];
} pp = {-1, 0, 0, 0, 0, 0, 0, 0, 0, {0}, {0}};

static void piprog_init(void)
{
    memset(pi_prog_n, 255, sizeof pi_prog_n);
    pi_prog_asked_ms = 0u;
    pi_prog_quiet = 0u;
    pp.cur = -1; pp.on = 0u; pp.want = 0u;
}
static void piprog_leave(void) { pp.cur = -1; pp.want = 0u; pp.on = 0u; }
static uint8_t piprog_browsing(void) { return (uint8_t)(pp.cur >= 0 && project.gen.harm_prog == SQ_PROG_PI); }

static void piprog_ask(uint8_t g, uint8_t m)
{
    uint8_t *q;
    if (pi_prog_asked_ms && (uint32_t)(fm1_ms - pi_prog_asked_ms) < 300u) return;
    pi_prog_asked_ms = fm1_ms ? fm1_ms : 1u;
    q = sx_head(SX_PROG_ASK);
    *q++ = g; *q++ = m; *q++ = 0xF7u;
    sysex_send(sx_out, (uint32_t)(q - sx_out));
}

static void piprog_get(uint16_t k)
{
    uint8_t *q, i;
    char *p = msg_buf;
    pp.on = 1u; pp.idx = k; pp.ms = fm1_ms;
    q = sx_head(SX_PROG_GET);
    *q++ = pp.genre; *q++ = pp.mood; sx_put7(&q, k, 2u); *q++ = pp.refn;
    for (i = 0; i < pp.refn; i++) { *q++ = pp.ref_semi[i]; *q++ = pp.ref_shape[i]; }
    *q++ = 0xF7u;
    sysex_send(sx_out, (uint32_t)(q - sx_out));
    p = put_s(p, "PI: PROGRESSION "); p = put_u(p, (uint32_t)k + 1u); p = put_s(p, " ..."); finish(p);
    status_msg(msg_buf);
}

/* K2 past the FM-1's last: into the Pi's (1), or there are none (0: the caller says so) */
static uint8_t piprog_enter(void)
{
    sq_hprog_t h;
    uint8_t g = project.gen.harm_genre, m = project.gen.harm_mood, i;
    if (g >= SQ_GENRES || m >= SQ_MOODS) return 0u;
    pp.genre = g; pp.mood = m;
    if (pp.cur < 0) {                                              /* (what is playing now: the one they are like) */
        pp.from = project.gen.harm_prog;
        harm_hprog_of(project.gen.harm_prog, &h);
        pp.refn = h.nc ? h.nc : h.n;
        if (pp.refn > SQ_HPROG_CH) pp.refn = SQ_HPROG_CH;
        for (i = 0; i < pp.refn; i++) sq_hchord_explicit(project.key_scale, &h.c[i], &pp.ref_semi[i], &pp.ref_shape[i]);
    }
    if (pi_prog_n[g][m] == 255u) {
        piprog_ask(g, m);
        if (pi_prog_quiet) return 0u;
        pp.want = 1u;
        status_msg("PI: ASKING FOR ITS PROGRESSIONS ...");
        return 1u;
    }
    if (!pi_prog_n[g][m]) return 0u;
    pp.cur = 0;
    piprog_get(0u);
    return 1u;
}

/* K2 while the Pi's play: the next / the one before; below the first, back to the FM-1's */
static void piprog_turn(int32_t d)
{
    int32_t k = (int32_t)pp.cur + d, n = pi_prog_n[pp.genre][pp.mood] == 255u ? 0 : pi_prog_n[pp.genre][pp.mood];
    if (k < 0) {
        uint8_t back = pp.from;
        piprog_leave();
        harm_prog_set(back);
        return;
    }
    if (k >= n) {
        char *p = msg_buf;
        k = n - 1;
        p = put_s(p, "PI: THE LAST "); if (pp.mood) { p = put_s(p, sq_mood_name(pp.mood)); p = put_s(p, " "); }
        p = put_s(p, "PROGRESSION OF "); p = put_s(p, sq_genre_name(pp.genre)); finish(p);
        status_msg(msg_buf);
        if (k < 0 || k == pp.cur) return;
    }
    pp.cur = (int16_t)k;
    piprog_get((uint16_t)k);
}

static void piprog_tick(void)
{
    if (pp.on && (uint32_t)(fm1_ms - pp.ms) > PIPAT_WAIT_MS) { pp.on = 0u; status_msg("PI: NO ANSWER (THE GRID BRIDGE?)"); }
    if (pp.want && pi_prog_asked_ms && (uint32_t)(fm1_ms - pi_prog_asked_ms) > PIPAT_WAIT_MS) {
        pp.want = 0u;
        pi_prog_quiet = 1u;
        if (pp.mood) {                                              /* (no Pi: as far as the FM-1's of the mood go) */
            char *p = msg_buf;
            p = put_s(p, "NO MORE "); p = put_s(p, sq_mood_name(pp.mood)); p = put_s(p, " (SEQ+SEL+BLACK 1: DICE PROG)"); finish(p);
            status_msg(msg_buf);
        } else status_msg("PI: NO ANSWER (THE GRID BRIDGE?)");
    }
}

static void piprog_loaded(uint8_t mood, const uint8_t *rows, uint8_t n)
{
    sq_uprog_t *u = &project.uprog[SQ_UPROGS];
    uint8_t k;
    char *p = msg_buf;
    sq_uprog_default(u);
    u->n = n;
    for (k = 0; k < n; k++) { u->semi[k] = rows[4u * k]; u->shape[k] = rows[4u * k + 1u]; u->dur[k] = rows[4u * k + 2u]; u->push[k] = rows[4u * k + 3u]; }
    u->mood = mood;
    sq_uprog_sanitize(u);
    project.gen.harm_prog = SQ_PROG_PI;
    project.gen.harm_on = 1u;
    p = put_s(p, "PI "); if (u->mood) { p = put_s(p, sq_mood_name(u->mood)); p = put_s(p, " "); }
    p = put_u(p, (uint32_t)pp.idx + 1u); p = put_s(p, "/"); p = put_u(p, pi_prog_n[pp.genre][pp.mood] == 255u ? 0u : pi_prog_n[pp.genre][pp.mood]);
    p = put_s(p, ": "); sq_uprog_name(u, project.key_scale, p, 40u);
    while (*p) p++;
    finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}

static void piprog_in(uint8_t cmd, const uint8_t *p, uint32_t n)
{
    uint8_t g, m;
    if (n < 2u) return;
    g = p[0]; m = p[1];
    if (g >= SQ_GENRES || m >= SQ_MOODS) return;
    pi_prog_quiet = 0u;
    if (cmd == SX_PROG_COUNT && n >= 4u) {
        uint32_t k = sx_get7(p + 2, 2u);
        pi_prog_n[g][m] = (uint8_t)(k > 250u ? 250u : k);
        if (pp.want && g == pp.genre && m == pp.mood) {
            pp.want = 0u;
            if (pi_prog_n[g][m]) { pp.cur = 0; piprog_get(0u); }
            else {
                char *q = msg_buf;
                q = put_s(q, "PI: NO "); if (m) { q = put_s(q, sq_mood_name(m)); q = put_s(q, " "); }
                q = put_s(q, "PROGRESSIONS OF "); q = put_s(q, sq_genre_name(g)); finish(q);
                status_msg(msg_buf);
            }
        }
        ui_dirty = 1u;
    } else if (cmd == SX_PROG && n >= 6u) {
        uint32_t idx = sx_get7(p + 2, 2u), cnt = p[4], mood = p[5];
        if (!pp.on || g != pp.genre || m != pp.mood || idx != pp.idx) return;   /* (not the one asked for) */
        pp.on = 0u;
        if (!cnt || cnt > SQ_HPROG_CH || mood >= SQ_MOODS || n < 6u + 4u * cnt) { status_msg("PI: NO SUCH PROGRESSION"); return; }
        piprog_loaded((uint8_t)mood, p + 6, (uint8_t)cnt);
    } else if (cmd == SX_PROG_SAVED && n >= 5u) {
        char *q = msg_buf;
        uint32_t idx = sx_get7(p + 3, 2u);
        if (p[2]) { status_msg(p[2] == 1u ? "PI: COULD NOT WRITE THE PROGRESSION" : "PI: NOT A PROGRESSION"); return; }
        pi_prog_n[g][m] = 255u; pi_prog_n[g][0] = 255u;          /* (counted again when asked) */
        q = put_s(q, "ON THE PI: "); q = put_s(q, sq_genre_name(g)); q = put_s(q, " "); q = put_s(q, sq_mood_name(m));
        q = put_s(q, " #"); q = put_u(q, idx + 1u); finish(q);
        status_msg(msg_buf);
    }
}

/* 0.12: ARP + SAVE on ARP 5 / 6 (the player's progression being written) or any other ARP page (the progression playing):
 * to the Pi, a progression of the HARMONY's genre with its mood (the player's, else the machine's guess); the lengths as
 * the player wrote them (a progression the rhythm times goes with none: the HARMONY's rhythm decides there too) */
static void piprog_save(void)
{
    sq_hprog_t h;
    const sq_uprog_t *u = 0;
    uint8_t g = project.gen.harm_genre, mood, n, k, *q;
    char *p = msg_buf;
    if (arp_page >= 4u) u = &project.uprog[uprog_sel];
    else if (project.gen.harm_prog >= SQ_PROGS) u = &project.uprog[(project.gen.harm_prog - SQ_PROGS) % SQ_UPROG_SLOTS];
    if (u) {
        if (!u->n) { status_msg("NOTHING WRITTEN TO SAVE"); return; }
        sq_hprog_user(&h, u, 0u, SQ_HR_BARS);
        mood = u->mood ? u->mood : sq_hprog_mood(&h, project.key_scale);
    } else {
        harm_hprog_of(project.gen.harm_prog, &h);
        mood = sq_hprog_mood(&h, project.key_scale);
    }
    n = h.nc ? h.nc : h.n;
    if (n > SQ_HPROG_CH) n = SQ_HPROG_CH;
    if (!n || g >= SQ_GENRES) { status_msg("NOTHING WRITTEN TO SAVE"); return; }
    q = sx_head(SX_PROG_PUT);
    *q++ = g; *q++ = mood < SQ_MOODS ? mood : 0u; *q++ = n;
    for (k = 0; k < n; k++) {
        uint8_t sm, sh;
        sq_hchord_explicit(project.key_scale, &h.c[k], &sm, &sh);
        *q++ = sm; *q++ = sh;
        *q++ = u ? u->dur[k] : 0u; *q++ = u ? u->push[k] : 0u;
    }
    *q++ = 0xF7u;
    sysex_send(sx_out, (uint32_t)(q - sx_out));
    p = put_s(p, "TO THE PI: "); p = put_s(p, sq_genre_name(g)); p = put_s(p, " "); p = put_s(p, sq_mood_name(mood)); finish(p);
    status_msg(msg_buf);
}
