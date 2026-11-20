/* SPDX-License-Identifier: GPL-3.0-only */
/*
 * SAGGA VIAGGIO (0.9) - the set from the blank page. Included by dinghy.c after sagga_live.c.
 *
 * The set is made of phrases (4, 8 or 16 bars). What you decide goes into the QUEUE and happens at the next phrase
 * boundary, NOW at the next bar. Every track is EMPTY, PROPOSED (it has phrases that do not play), IN or OUT. "Tira"
 * makes a proposal for a track from the set's genre, in the key, with the role the track has in the genre and the
 * energy of the moment; the proposals are the track's patterns after the one that plays. The ENERGY (0..100) moves the
 * velocity, the filter, the gates, the density of the hits, the depth of the LFOs and the colour of the chords, gliding
 * along the phrase. The MOVES: FILL BREAK RISER DROP HALF DOUBLE THIN SWELL SWAP LOOP, TRANSPOSE, PROG, GENRE, KEY,
 * ENERGY, and INDIETRO through the TRAIL, which keeps every phrase. The grid's VIAGGIO view (sagga_grid.c), the remote
 * on channel 13. The profiles: what the firmware shows and allows (FULL, PALCO; 0.27: SEMPLICE).
 *
 * 0.17: no VIAGGIO mode any more: the journey always runs (at energy 50 with nothing queued it changes nothing), the
 * trail always keeps the phrases (SAVE + white 16 makes them scenes and the song), the MOVES are on the black keys of
 * PERF's third page (the MOSSE: SEL + GLO opens it), and a PROPOSAL is made in SEQ (BEAT held) and queued with PRESETS.
 */

/* ---- the profiles */
typedef struct {
    const char *name;
    uint8_t home_pages;          /* bit per HOME page 0..7 */
    uint32_t moves;              /* bit per SQ_MV_* */
    uint8_t edit_keys;           /* 1: SEQ tools, EDIT / ENV pages, step keys; 0: the panel plays the set only */
    uint8_t viaggio_on;          /* 0.17: PERF on the MOSSE page when the profile is chosen */
    uint8_t remote_mode;         /* SQ_RM_* the profile prefers */
    uint8_t seq_hide;            /* 0.27: bit per SEQ page 0..7 that is hidden while what it starts is not playing */
} vg_profile_t;
#define VG_ALL_MOVES 0xFFFFFFFFu
static const vg_profile_t VG_PROFILE[SQ_PROFILES] = {
    { "FULL",  0xFFu, VG_ALL_MOVES, 1u, 0u, SQ_RM_14, 0u },
    /* PALCO: the set is played, not edited: no SEQ tools, no EDIT / ENV pages; HOME pages 1 (the channel), 3 (the key)
     * and 8 (VIAGGIO); every move; the MOSSE from the start; the remote on 13 + 14. (The grid's views are not gated.) */
    { "PALCO", 0x05u, VG_ALL_MOVES, 0u, 1u, SQ_RM_13_14, 0u },   /* 0.12: VIAGGIO's page is GLO 3, always allowed */
    /* 0.27 SEMPLICE: everything of FULL, but the pages of the lab's generators are hidden - SEQ 2 (the four algorithms)
     * and SEQ 3 (EVOLVE). Nothing is switched off: a page comes back while what it starts plays (an algorithm on the
     * selected track; EVOLVE) */
    { "SEMPLICE", 0xFFu, VG_ALL_MOVES, 1u, 0u, SQ_RM_14, 0x06u },
};
static uint8_t vg_profile = SQ_PROF_FULL;   /* kept in the settings (sagga_store.c) */
static const vg_profile_t *vg_prof(void) { return &VG_PROFILE[vg_profile < SQ_PROFILES ? vg_profile : 0u]; }
static const char *vg_profile_name(void) { return vg_prof()->name; }
static uint8_t vg_allows_move(uint8_t kind) { return (vg_prof()->moves >> (kind & 31u)) & 1u; }
static uint8_t vg_allows_home(uint8_t page) { return (vg_prof()->home_pages >> (page & 7u)) & 1u; }
static uint8_t vg_edit_keys(void) { return vg_prof()->edit_keys; }
static uint8_t vg_seq_shown(uint8_t page)                 /* 0.27: SEMPLICE hides SEQ 2 and 3 while nothing of theirs plays */
{
    uint32_t k;
    if (page >= 8u || !((vg_prof()->seq_hide >> page) & 1u)) return 1u;
    if (page == 2u) return evo_run ? 1u : 0u;
    for (k = 0; k < SQ_ALGO_SLOTS; k++) if (SQ_ALGO_AT(&project.track[selected_track], k)->algo != SQ_ALGO_OFF) return 1u;
    return 0u;
}

static void vg_profile_service(void);

/* ---- the state */
static sq_queue_t vg_q;
static sq_trail_t vg_trail;
static sq_phrase_t vg_ring[SQ_TRAIL] __attribute__((section(".pool")));
static uint8_t vg_bar;                      /* the bar of the phrase, 0..phrase_bars-1 */
static uint8_t vg_now;                      /* NOW: the queue runs at the next bar */
static uint8_t vg_energy_from;              /* the energy the phrase started from (it glides to project.viaggio.energy) */
static uint8_t vg_energy_cur;               /* the energy applied now */
static uint8_t vg_energy_now(void) { return vg_energy_cur; }   /* 0.20: the MOD MATRIX's ENERGY */
static uint8_t vg_riser;                    /* RISER in this phrase */
static uint8_t vg_fill;                     /* FILL in the last bar (fill_active) */
static uint8_t vg_break_left;               /* BREAK: bars to go, 0 none */
static uint16_t vg_break_keep;              /* ... the mutes to put back (the moves of the break write here) */
static int8_t vg_speed;                     /* HALF (-1) / DOUBLE (+1) in this phrase: eff_div_ticks (dinghy.c) reads it */
static uint8_t vg_rec_t = 255u;             /* LOOP: the track recording this phrase */
static uint8_t vg_rec_arm = 255u, vg_rec_short;   /* ... armed for the next phrase (255: none), 4 bars repeated */
static uint8_t vg_prop[SQ_TRACKS];          /* the proposal browsed on each track (a pattern), 255 none */
/* 0.10: every proposal keeps its settings and its role in its slot (0.9 kept one per track and lost it when the
 * encoder browsed: a kick browsed came back as a bass) */
static beat_cfg_t vg_pcfg[SQ_TRACKS][SQ_PATTERNS];
static uint8_t vg_pcfg_has[SQ_TRACKS];      /* bit per pattern: vg_pcfg is valid, the slot is a proposal */
static uint8_t vg_pcfg_role[SQ_TRACKS][SQ_PATTERNS];
static uint8_t vg_pcfg_age[SQ_TRACKS][SQ_PATTERNS];   /* when it was made (the oldest goes first when the slots are full) */
static uint8_t vg_age_n;
static uint8_t vg_loop_has[SQ_TRACKS];      /* LOOP: a hand phrase lives in patterns chain_base .. +chain-1 */
static uint8_t vg_chain[SQ_TRACKS];         /* ... over 4 patterns (16 bars) or 1 */
static uint8_t vg_chain_base[SQ_TRACKS];
static uint8_t vg_chain_on[SQ_TRACKS];      /* ... and the track plays it now (its 64 steps, 1/16, in key) */
typedef struct { uint8_t length, start, division, flags; } vg_tcfg_t;
static vg_tcfg_t vg_loop_cfg[SQ_TRACKS], vg_pre_cfg[SQ_TRACKS];   /* the track as the loop wants it, and as it was before */
static uint8_t vg_pre_pattern[SQ_TRACKS];   /* ... and the pattern it played before the loop */
static uint16_t vg_exit;                    /* tracks leaving at the boundary: the last bar fades */
static uint8_t vg_tira_n[SQ_TRACKS];        /* proposals made on the track (the dice's memory) */
static sq_energy_fx_t vg_fx;                /* what the energy does now */
#define VG_HOLD_MS 450u

/* ---- small helpers */
static uint8_t vg_on(void) { return project.viaggio.on; }
static uint8_t vg_bars(void) { return project.viaggio.phrase_bars ? project.viaggio.phrase_bars : 16u; }
static uint8_t vg_state(uint32_t t) { return project.viaggio.state[t]; }
static void vg_set_state(uint32_t t, uint8_t s) { project.viaggio.state[t] = s; }
static uint8_t vg_track_in(uint32_t t) { return (vg_state(t) == SQ_TS_IN) ? 1u : 0u; }
/* 0.10: the genre of the set IS the project's genre (SEQ + PRESETS, HOME 8 K3) */
static const sq_set_genre_t *vg_genre(void) { return sq_set_genre(project.gen.genre < SQ_SET_GENRES ? project.gen.genre : 0u); }
static uint8_t vg_lib_genre(void) { return vg_genre()->genre; }
static uint8_t vg_set_genre_cur(void) { return project.gen.genre < SQ_SET_GENRES ? project.gen.genre : 0u; }

static uint8_t pattern_empty(uint32_t t, uint8_t pat)
{
    uint32_t i;
    for (i = 0; i < SQ_STEPS; i++) if (project.step[t][pat][i].flags & SQ_STEP_ON) return 0u;
    return 1u;
}
static uint8_t track_has_notes(uint32_t t)
{
    uint8_t pat;
    for (pat = 0; pat < SQ_PATTERNS; pat++) if (!pattern_empty(t, pat)) return 1u;
    return 0u;
}

/* the role a track has: its notes say it (kick, snare, hat, perc, bass, chord, arp), an empty track takes the next
 * free role of the ladder */
/* 0.10: the role the player gave the track (HOME 4 K2) comes first; then a proposal's slot says its role; then the
 * track's drum flag and pen */
static uint8_t vg_role_of(uint32_t t)
{
    uint8_t drum = track_drum(t), note = PEN(t), pat = vg_prop[t] < SQ_PATTERNS ? vg_prop[t] : tr[t].pattern;
    if (project.track[t].role) return (uint8_t)(sq_role_family(project.track[t].role) - 1u);   /* (0.11: a CLAP is on the SNARE's rung) */
    if (vg_pcfg_has[t] & (1u << pat)) return vg_pcfg_role[t][pat];
    return sq_role_for_track(vg_set_genre_cur(), drum, note, 1u, 0u, 0u);
}
static uint8_t vg_track_role(uint32_t t)
{
    uint8_t taken = 0u, i, k = 0u;
    if (project.track[t].role) return (uint8_t)(sq_role_family(project.track[t].role) - 1u);
    if (track_has_notes(t)) return vg_role_of(t);
    if (track_drum(t)) return sq_role_for_track(vg_set_genre_cur(), 1u, PEN(t), 1u, 0u, 0u);   /* a drum set by hand */
    for (i = 0; i < SQ_TRACKS; i++) {
        if (i == t) { k = (uint8_t)(i % SQ_ROLES); continue; }
        if (project.track[i].role) { taken |= (uint8_t)(1u << (sq_role_family(project.track[i].role) - 1u)); continue; }
        if (vg_state(i) == SQ_TS_EMPTY || !track_has_notes(i)) continue;
        taken |= (uint8_t)(1u << vg_role_of(i));
    }
    return sq_role_for_track(vg_set_genre_cur(), 0u, 0u, 0u, k, taken);
}
static uint8_t vg_track_energy(uint32_t t) { return sq_role_energy(vg_set_genre_cur(), vg_track_role(t)); }

static void vg_msg2(const char *a, const char *b)
{
    char *p = msg_buf;
    p = put_s(p, a); p = put_s(p, b); finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}
static void vg_msg_t(const char *a, uint32_t t, const char *b)
{
    char *p = msg_buf;
    p = put_s(p, a); p = put_s(p, "T"); p = put_u(p, t + 1u); p = put_s(p, b); finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}

/* ---- the states of the tracks from what the project holds (VIAGGIO switched on, a project loaded): a track with
 * notes only outside the pattern that plays is a proposal, not a track that plays */
static uint16_t vg_mutes_to_keep(void);
static void vg_state_sync(uint32_t t);
static void vg_states_from_project(void)
{
    uint32_t t;
    for (t = 0; t < SQ_TRACKS; t++) vg_state_sync(t);
}
/* a mute the journey sets: during a BREAK it goes to the mask the break puts back, the break itself stays whole */
static void vg_mute_set(uint32_t t, uint8_t on)
{
    uint16_t bit = (uint16_t)(1u << t);
    if (vg_break_left) { if (on) vg_break_keep |= bit; else vg_break_keep &= (uint16_t)~bit; if (on) mute_mask |= bit; }
    else if (on) mute_mask |= bit;
    else mute_mask &= (uint16_t)~bit;
}
static uint16_t vg_mutes_to_keep(void)      /* the mutes as they are meant (a save, a snapshot): not a break's */
{
    return vg_break_left ? vg_break_keep : mute_mask;
}
static void vg_break_end(void)
{
    if (!vg_break_left) return;
    vg_break_left = 0u;
    mute_mask = vg_break_keep;
    ui_dirty = grid_dirty = 1u;
}

/* ---- the energy as it sounds */
static void vg_energy_apply(uint8_t e)
{
    sq_energy_fx_t was = vg_fx;
    vg_energy_cur = e > 100u ? 100u : e;
    if (!vg_on()) { memset(&vg_fx, 0, sizeof vg_fx); vg_fx.density = 100u; vg_fx.lfo_pct = 100u; }
    else sq_energy_map(vg_energy_cur, &vg_fx);
    if (vg_fx.filt != was.filt) { filt_dirty = 1u; filt_t = 0u; }
    ui_dirty = grid_dirty = 1u;
}
/* what the player adds: velocity (the energy, a track fading out in its last bar), filter, gate, the density */
static int32_t vg_vel_adj(uint32_t t)
{
    int32_t v = vg_fx.vel;
    if (!vg_on()) return 0;
    if ((vg_exit & (1u << t)) && vg_bars() && vg_bar + 1u >= vg_bars()) {         /* the last bar: 0 .. -60 over the bar */
        uint32_t into = bar_into() * 60u / bar_ticks();              /* (0.25: over the metre's bar) */
        v -= (int32_t)into;
    }
    return v;
}
static int32_t vg_filt_adj(void) { return vg_fx.filt; }
static int32_t vg_gate_adj(void) { return vg_fx.gate; }
/* the hits of a track under the energy (tracks with their own DENSITY algorithm keep it); h: a hash of the moment */
static uint8_t vg_density_hit(uint32_t t, uint8_t on, uint32_t rel, uint32_t h, uint8_t *ghost)
{
    uint8_t dens = vg_fx.density;
    if (!vg_on() || sq_track_algo_any(&project.track[t], SQ_ALGO_DENSITY)) return on;   /* (0.11: any slot) */
    if (!track_has_notes(t)) return on;                              /* 0.9.1: no ghosts on a track with nothing in it */
    if (project.th.pat[t][tr[t].pattern].style) dens = 100u;         /* 0.23: a pattern of the engines fills and empties itself (th_service) */
    if (vg_fill && vg_bars() && vg_bar + 1u >= vg_bars()) {           /* the FILL bar: ghost hits on every track, more
                                                                          * in its second half (the patterns' own FILL
                                                                          * conditions play too: fill_active) */
        uint32_t half = bar_into() * 2u >= bar_ticks() ? 1u : 0u;   /* (0.25: the metre's bar) */
        uint8_t fd = (uint8_t)(half ? 160u : 130u);
        if (fd > dens) dens = fd;
    }
    if (dens == 100u) return on;
    if (dens < 100u && vg_role_of(t) == SQ_FUNC_KICK) return on;    /* the kick stays whole */
    return sq_density_hit(on, dens, rel, h, ghost);
}
static uint8_t vg_color7(void) { return vg_on() ? vg_fx.color7 : 0u; }
static uint8_t vg_lfo_pct(void) { return vg_on() ? vg_fx.lfo_pct : 100u; }
static uint8_t vg_expo_hits(uint8_t h) { return vg_on() ? sq_expo_energy_hits(h, vg_energy_cur) : h; }   /* 0.10: the energy on EXPO */

/* ---- the queue */
static int vg_queue(uint8_t kind, uint8_t a, uint8_t b)
{
    if (!vg_allows_move(kind)) { vg_msg2("NOT IN THIS PROFILE: ", sq_move_name(kind)); return -1; }
    if (kind == SQ_MV_RISER && vg_bars() < 8u) { status_msg("RISER NEEDS A PHRASE OF 8 OR 16 BARS"); ui_dirty = 1u; return -1; }
    if (sq_queue_push(&vg_q, kind, a, b) < 0) { status_msg("QUEUE FULL (16)"); ui_dirty = grid_dirty = 1u; return -1; }
    if ((kind == SQ_MV_FILL || kind == SQ_MV_DROP) && playing && vg_bar + 1u >= vg_bars()) vg_fill = 1u;   /* asked in the last bar: now */
    ui_dirty = grid_dirty = 1u;
    return 0;
}
static void vg_cancel_last(void)
{
    if (!vg_q.n) { status_msg("QUEUE EMPTY"); ui_dirty = 1u; return; }
    vg_msg2("CANCELLED ", sq_move_name(vg_q.m[vg_q.n - 1u].kind));
    sq_queue_drop_last(&vg_q);
}

/* ---- "tira": a proposal for a track. kind 0: the first one (the genre's first variant that fits the energy), 1: the
 * dice (another variant, maybe the second genre); the proposal goes into a free pattern after the one that plays. */
static uint8_t vg_slot_busy(uint32_t t, uint8_t c)              /* a slot a proposal may not take */
{
    int i;
    if (c == tr[t].pattern || c == vg_prop[t]) return 1u;
    if (vg_loop_has[t] && c >= vg_chain_base[t] && c < vg_chain_base[t] + vg_chain[t]) return 1u;
    i = sq_queue_find(&vg_q, SQ_MV_IN, (uint8_t)t); if (i >= 0 && vg_q.m[i].b == c) return 1u;
    i = sq_queue_find(&vg_q, SQ_MV_SWAP, (uint8_t)t); if (i >= 0 && vg_q.m[i].b == c) return 1u;
    return 0u;
}
static uint8_t vg_free_pattern(uint32_t t)
{
    uint8_t k, p = tr[t].pattern, best = 255u;
    for (k = 1; k < SQ_PATTERNS; k++) {
        uint8_t c = (uint8_t)((p + k) % SQ_PATTERNS);
        if (vg_slot_busy(t, c)) continue;
        if (pattern_empty(t, c)) return c;
    }
    for (k = 1; k < SQ_PATTERNS; k++) {                           /* none empty: the oldest proposal is replaced (never a pattern written by hand) */
        uint8_t c = (uint8_t)((p + k) % SQ_PATTERNS);
        if (vg_slot_busy(t, c) || !(vg_pcfg_has[t] & (1u << c))) continue;
        if (best == 255u || (uint8_t)(vg_pcfg_age[t][c] - vg_age_n) > (uint8_t)(vg_pcfg_age[t][best] - vg_age_n)) best = c;
    }
    if (best != 255u) return best;
    for (k = 1; k < SQ_PATTERNS; k++) {                           /* all written by hand: the one after the playing one */
        uint8_t c = (uint8_t)((p + k) % SQ_PATTERNS);
        if (!vg_slot_busy(t, c)) return c;
    }
    return (uint8_t)((p + 1u) % SQ_PATTERNS);
}

/* the proposals a track has: its patterns with notes other than the one playing (bit per pattern) */
static uint8_t vg_proposals(uint32_t t)
{
    uint8_t m = 0u, pat;
    for (pat = 0; pat < SQ_PATTERNS; pat++)
        if (pat != tr[t].pattern && !pattern_empty(t, pat)) m |= (uint8_t)(1u << pat);
    return m;
}

static void vg_tira(uint8_t t, uint8_t dice)
{
    const sq_set_genre_t *g = vg_genre();
    uint8_t role, pat, genre, n = 0u, nv, var, fn;
    beat_cfg_t cfg;
    char *p;
    if (t >= SQ_TRACKS) return;
    role = vg_track_role(t);
    pat = vg_free_pattern(t);
    genre = (dice && (grand(3u) == 0u)) ? g->genre2 : g->genre;
    {   /* 0.11: the part: the track's own role's if the genre has it, else its family's */
        uint8_t want = project.track[t].role ? sq_role_func(project.track[t].role) : role;
        fn = sq_genre_part_for(genre, want);
        if (fn == 255u) fn = sq_genre_part_for(genre, role);
        if (fn == 255u) return;
    }
    if (!track_has_notes(t)) {                           /* an empty track: the pen of its role (the kit's drum, or an octave) */
        if (role < SQ_FUNC_BASS && fn <= SQ_FUNC_PERC) { uint8_t f2; sq_beat_kit_part(genre, role, &f2, &PEN(t)); }
        else if (role < SQ_FUNC_BASS) PEN(t) = sq_part_note(genre, fn);
        else PEN(t) = start_note(fn, role == SQ_FUNC_BASS ? 36u : role == SQ_FUNC_CHORD ? 55u : 67u);   /* (0.27: with no key, on the root) */
    }
    if (role == SQ_FUNC_PERC && g->afro && (!dice || grand(2u))) {    /* the AFRO / LATIN family for the percussion */
        const sq_afro_t *a = sq_afro((uint8_t)(dice ? grand(SQ_AFRO_N) : vg_tira_n[t] % SQ_AFRO_N));
        n = sq_beat_load_text(project.step[t][pat], a->text, 0, SQ_FUNC_PERC, PEN(t));
        if (n) {
            th_forget(t, pat);                          /* 0.23 */
            made_fit(t, pat, n);                        /* 0.24: for the track as long as it is */
            beat_cfg_for(&project.track[t], genre, SQ_FUNC_PERC, n, PEN(t), &cfg);
            if (a->steps == 12u) cfg.length = 12u;      /* (the bembe' is twelve steps: the track is made twelve when it enters) */
        }
    }
    if (!n) {
        nv = sq_beat_variants(genre, fn);
        if (!nv) return;
        /* the energy chooses the variant: low energy the first (the simplest), high the last; the dice any */
        var = dice ? (uint8_t)grand(nv) : (uint8_t)(((uint32_t)vg_energy_cur * nv) / 101u);
        if (!dice && vg_tira_n[t]) var = (uint8_t)((var + vg_tira_n[t]) % nv);
        if (th_style_now(genre) != 255u) var = dice ? (uint8_t)(1u + grand(250u)) : vg_tira_n[t];   /* 0.23 THEORY: a seed (the energy is the engines' own matter) */
        n = beat_onto_x(t, pat, genre, fn, var, 0u, &cfg);
        if (!n) return;
    }
    vg_prop[t] = pat;
    vg_pcfg[t][pat] = cfg;
    vg_pcfg_role[t][pat] = role;
    vg_pcfg_age[t][pat] = ++vg_age_n;
    vg_pcfg_has[t] |= (uint8_t)(1u << pat);
    vg_tira_n[t]++;
    if (vg_state(t) == SQ_TS_EMPTY) vg_set_state(t, SQ_TS_PROPOSED);
    {   /* "T1 KICK P4 (3/3) READY" (the count: the proposals the track has, this one's place among them) */
        uint8_t m = vg_proposals(t), n = 0u, i = 0u, c;
        for (c = 0; c < SQ_PATTERNS; c++) if (m & (1u << c)) { n++; if (c == pat) i = n; }
        p = msg_buf;
        p = put_s(p, "T"); p = put_u(p, (uint32_t)t + 1u); p = put_s(p, " "); p = put_s(p, sq_func_name(fn));
        p = put_s(p, " P"); p = put_u(p, (uint32_t)pat + 1u);
        if (n > 1u) { p = put_s(p, " ("); p = put_u(p, i); p = put_s(p, "/"); p = put_u(p, n); p = put_s(p, ")"); }
        p = put_s(p, dice ? " DICE" : "");
        p = put_s(p, " READY");                          /* (0.17: the grid, the remote or PRESETS bring it in) */
        finish(p);
        status_msg(msg_buf);
    }
    ui_dirty = grid_dirty = 1u;
}
static void vg_browse(uint8_t t, int32_t d)             /* the ALG encoder: the next / previous proposal */
{
    uint8_t m = vg_proposals(t), k, cur = vg_prop[t] < SQ_PATTERNS ? vg_prop[t] : tr[t].pattern;
    if (!m) { status_msg("NO PROPOSALS: TAP THE TRACK"); ui_dirty = 1u; return; }
    for (k = 1; k <= SQ_PATTERNS; k++) {
        uint8_t c = (uint8_t)((cur + SQ_PATTERNS + (d > 0 ? k : SQ_PATTERNS - k)) % SQ_PATTERNS);
        if (m & (1u << c)) { vg_prop[t] = c; break; }
    }
    {   /* "T1 KICK P5 (3/7)" */
        uint8_t n = 0u, i = 0u, c;
        char *p = msg_buf;
        for (c = 0; c < SQ_PATTERNS; c++) if (m & (1u << c)) { n++; if (c == vg_prop[t]) i = n; }
        p = put_s(p, "T"); p = put_u(p, (uint32_t)t + 1u); p = put_s(p, " "); p = put_s(p, sq_func_name(vg_role_of(t)));
        p = put_s(p, " P"); p = put_u(p, (uint32_t)vg_prop[t] + 1u); p = put_s(p, " ("); p = put_u(p, i); p = put_s(p, "/"); p = put_u(p, n); p = put_s(p, ")");
        finish(p);
        status_msg(msg_buf);
        ui_dirty = grid_dirty = 1u;
    }
}

/* ---- a LOOP's patterns want the track long (64 steps, 1/16, in key); any other pattern wants it as it was.
 * Returns the pattern to play (a pattern inside a 4-pattern loop: its first one). */
static void vg_tcfg_get(uint32_t t, vg_tcfg_t *o) { const sq_track_cfg_t *c = &project.track[t]; o->length = c->length; o->start = c->start; o->division = c->division; o->flags = c->flags; }
static void vg_tcfg_put(uint32_t t, const vg_tcfg_t *o)
{
    sq_track_cfg_t *c = &project.track[t];
    c->length = o->length; c->start = o->start; c->division = o->division; c->flags = o->flags;
    if (tr[t].step >= c->length) tr[t].step = c->start;
}
static uint8_t vg_in_loop(uint32_t t, uint8_t pat) { return (vg_loop_has[t] && pat >= vg_chain_base[t] && pat < vg_chain_base[t] + vg_chain[t]) ? 1u : 0u; }
static uint8_t vg_loop_sync(uint32_t t, uint8_t pat)
{
    if (vg_in_loop(t, pat)) {
        if (!vg_chain_on[t]) { vg_tcfg_get(t, &vg_pre_cfg[t]); vg_tcfg_put(t, &vg_loop_cfg[t]); vg_chain_on[t] = 1u; if (playing) track_realign(t); }
        return vg_chain_base[t];
    }
    if (vg_chain_on[t]) {                                  /* 0.11: the track's own loop back, in time (the explorer) */
        vg_tcfg_put(t, &vg_pre_cfg[t]); vg_chain_on[t] = 0u;
        if (playing) track_realign(t);
    }
    return pat;
}

/* ---- a track enters, leaves, swaps (at the boundary) */
static void vg_enter(uint8_t t, uint8_t pat)
{
    if (t >= SQ_TRACKS) return;
    if (pat >= SQ_PATTERNS) pat = vg_prop[t] < SQ_PATTERNS ? vg_prop[t] : tr[t].pattern;
    if (pattern_empty(t, pat) && vg_proposals(t)) {      /* an empty slot asked: the first proposal */
        uint8_t m = vg_proposals(t), k;
        for (k = 0; k < SQ_PATTERNS; k++) if (m & (1u << k)) { pat = k; break; }
    }
    pat = vg_loop_sync(t, pat);
    if (vg_pcfg_has[t] & (1u << pat)) { beat_cfg_apply(t, pat, &vg_pcfg[t][pat]); vg_pcfg_has[t] &= (uint8_t)~(1u << pat); }   /* (its settings come with it, once) */
    if (pat != tr[t].pattern) { tr[t].pattern = pat; tr[t].pending_pattern = SQ_NO_PENDING; }
    if (playing) track_restart(t);
    vg_mute_set(t, 0u);
    pending_mute &= (uint16_t)~(1u << t);
    solo_mask = 0u;
    vg_set_state(t, SQ_TS_IN);
    if (vg_prop[t] == pat) vg_prop[t] = 255u;
}
static void vg_leave(uint8_t t)
{
    if (t >= SQ_TRACKS) return;
    vg_mute_set(t, 1u);
    pending_mute &= (uint16_t)~(1u << t);
    if (vg_state(t) == SQ_TS_IN) vg_set_state(t, SQ_TS_OUT);
}

/* ---- HALF / DOUBLE: every track's steps twice as long / short for one phrase (eff_div_ticks reads vg_speed, as it
 * reads the FX HALF / DOUBLE; the project's divisions are not touched). Called on a bar line: every track starts
 * its loop there, so the phrase after is on the grid again. */
static void vg_speed_set(int8_t speed)
{
    uint32_t t;
    if (speed == vg_speed) return;
    vg_speed = speed;
    if (playing) for (t = 0; t < SQ_TRACKS; t++) track_restart(t);
}

/* ---- THIN and SWELL */
static void vg_thin(void)
{
    uint32_t k, t;
    for (k = 0; k < 2u; k++) {
        uint8_t best = 255u, in_n = 0u;
        for (t = 0; t < SQ_TRACKS; t++) if (vg_track_in(t)) in_n++;
        if (in_n <= 1u) break;                           /* never the last one */
        for (t = 0; t < SQ_TRACKS; t++)
            if (vg_track_in(t) && (best == 255u || vg_track_energy(t) > vg_track_energy(best))) best = (uint8_t)t;
        if (best == 255u) break;
        vg_leave(best);
    }
}
static void vg_swell(void)
{
    uint32_t k, t;
    for (k = 0; k < 2u; k++) {
        uint8_t best = 255u;
        int32_t bd = 1000;
        for (t = 0; t < SQ_TRACKS; t++) {
            int32_t d;
            if (vg_track_in(t) || vg_state(t) == SQ_TS_EMPTY) continue;
            if (!vg_proposals(t) && pattern_empty(t, tr[t].pattern)) continue;
            d = (int32_t)vg_track_energy(t) - (int32_t)vg_energy_cur;
            if (d < 0) d = -d;
            if (d < bd) { bd = d; best = (uint8_t)t; }
        }
        if (best == 255u) break;
        vg_enter(best, 255u);
    }
}

/* ---- the trail */
static void vg_phrase_now(sq_phrase_t *ph)
{
    uint32_t t;
    for (t = 0; t < SQ_TRACKS; t++) ph->pattern[t] = tr[t].pattern;
    ph->mute = mute_mask;
    for (t = 0; t < SQ_TRACKS; t++) if (!vg_track_in(t)) ph->mute |= (uint16_t)(1u << t);
    ph->energy = project.viaggio.energy;
    ph->key_root = project.key_root; ph->key_scale = project.key_scale;
    ph->set_genre = vg_set_genre_cur();
    ph->prog = project.gen.harm_prog;
    ph->flags = (uint8_t)((project.gen.harm_on ? SQ_PF_HARM : 0u) | (vg_speed < 0 ? SQ_PF_HALF : vg_speed > 0 ? SQ_PF_DOUBLE : 0u) | SQ_PF_BARS_FLAG(vg_bars()));
    ph->bpm = project.bpm;
}
static void vg_set_genre_apply(uint8_t g);
static void vg_phrase_restore(const sq_phrase_t *ph)      /* INDIETRO: the phrase as it was (the tempo stays yours) */
{
    uint32_t t;
    for (t = 0; t < SQ_TRACKS; t++) {
        uint8_t p = vg_loop_sync(t, ph->pattern[t] < SQ_PATTERNS ? ph->pattern[t] : 0u);
        if (p != tr[t].pattern) { tr[t].pattern = p; tr[t].pending_pattern = SQ_NO_PENDING; if (playing) track_restart(t); }
        if (!track_has_notes(t)) { vg_mute_set(t, 0u); vg_set_state(t, SQ_TS_EMPTY); }   /* (nothing to mute) */
        else if (ph->mute & (1u << t)) { vg_mute_set(t, 1u); if (vg_state(t) == SQ_TS_IN) vg_set_state(t, SQ_TS_OUT); }
        else { vg_mute_set(t, 0u); vg_set_state(t, SQ_TS_IN); }
    }
    pending_mute = 0u; solo_mask = 0u;
    project.key_root = ph->key_root > 11u ? 0u : ph->key_root;
    project.key_scale = ph->key_scale < SQ_SCALES ? ph->key_scale : SQ_SC_CHROMATIC;
    key_sync_slot();
    if (ph->set_genre != vg_set_genre_cur()) vg_set_genre_apply(ph->set_genre);
    project.gen.harm_prog = ph->prog < SQ_PROGS_ALL ? ph->prog : 0u;
    project.gen.harm_on = (ph->flags & SQ_PF_HARM) ? 1u : 0u;
    project.viaggio.energy = ph->energy > 100u ? 100u : ph->energy;
    vg_energy_from = project.viaggio.energy;
    vg_energy_apply(project.viaggio.energy);
}

/* ---- the genre, the seed */
static void gen_genre_changed(uint8_t g, uint8_t act);       /* sagga_gen.c: the one genre of the machine */
static void vg_set_genre_apply(uint8_t g)
{
    if (g >= SQ_SET_GENRES) return;
    gen_genre_changed(g, 1u);                                 /* (sets gen.genre and viaggio.set_genre, reloads what follows the genre; the harmony follows unless locked) */
    vg_msg2("GENRE ", vg_genre()->name);
}
static void vg_seed(void)                                   /* SEL + PLAY, stopped: the dice on genre, key and tempo */
{
    uint16_t lo, hi;
    uint8_t g = (uint8_t)grand(SQ_SET_GENRES);
    char *p = msg_buf;
    if (playing) { status_msg("THE SEED IS THROWN IN THE SILENCE: STOP FIRST"); ui_dirty = 1u; return; }
    vg_set_genre_apply(g);
    project.key_root = (uint8_t)grand(12u);
    project.key_scale = sq_genre_scale(vg_lib_genre(), (uint8_t)grand(3u));
    if (project.key_scale == SQ_SC_CHROMATIC) project.key_scale = SQ_SC_MINOR;
    key_sync_slot();
    sq_genre_bpm(vg_lib_genre(), &lo, &hi);
    if (project.clock_mode == SQ_CLOCK_MASTER) { project.bpm = (uint16_t)(lo + grand((uint32_t)(hi - lo + 1u))); knob_live = 0u; knob_ref = fm1_knob; }
    p = put_s(p, "SEED: "); p = put_s(p, vg_genre()->name); p = put_s(p, " "); p = put_s(p, sq_root_name(project.key_root));
    p = put_s(p, " "); p = put_s(p, sq_scale_name(project.key_scale)); p = put_s(p, " "); p = put_u(p, project.bpm); finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}

/* ---- LOOP: a track records the next phrase with the hands */
static void vg_loop_begin(uint8_t t)
{
    uint8_t pat, k;
    vg_tcfg_t cfg;
    if (vg_chain_on[t]) vg_loop_sync(t, 255u);               /* an older loop of this track: its settings go back first */
    vg_loop_has[t] = 0u;
    vg_pre_pattern[t] = tr[t].pattern;
    pat = vg_free_pattern(t);
    if (!vg_rec_short && vg_bars() >= 8u) {                /* the whole phrase: four patterns in a chain (16 bars) */
        uint8_t base = 255u;
        for (k = 0; k + 4u <= SQ_PATTERNS; k++) {
            uint8_t j, ok = 1u;
            for (j = 0; j < 4u; j++) if ((uint8_t)(k + j) == tr[t].pattern || !pattern_empty(t, (uint8_t)(k + j))) ok = 0u;
            if (ok) { base = k; break; }
        }
        if (base == 255u) base = tr[t].pattern < 4u ? 4u : 0u;   /* none free: the half the playing pattern is not in */
        for (k = 0; k < 4u; k++) { sq_row_clear(project.step[t][base + k]); vg_pcfg_has[t] &= (uint8_t)~(1u << (base + k)); }
        vg_chain[t] = 4u; vg_chain_base[t] = base;
        pat = base;
    } else { vg_chain[t] = 1u; vg_chain_base[t] = pat; sq_row_clear(project.step[t][pat]); vg_pcfg_has[t] &= (uint8_t)~(1u << pat); }
    vg_loop_has[t] = 1u;
    vg_tcfg_get(t, &cfg);                                  /* what the loop wants: 64 steps of 1/16 (4 bars), in key */
    cfg.length = 64u; cfg.start = 0u; cfg.division = SQ_DIV_1_16;
    if (!track_drum(t)) cfg.flags |= SQ_TF_SCALE;
    vg_loop_cfg[t] = cfg;
    pat = vg_loop_sync(t, pat);
    tr[t].pattern = pat; tr[t].pending_pattern = SQ_NO_PENDING;
    if (playing) track_restart(t);
    vg_mute_set(t, 0u);
    vg_set_state(t, SQ_TS_IN);
    vg_rec_t = t;
    record_arm = 1u;
    select_track(t);
    vg_msg_t("LOOP: PLAY ", t, " NOW");
}
static void vg_loop_close(void)
{
    uint8_t t = vg_rec_t;
    if (t >= SQ_TRACKS) return;
    record_arm = 0u;
    vg_rec_t = 255u;
    {   /* nothing played into the loop's patterns: the loop is forgotten, the track goes back to what it was */
        uint8_t k, any = 0u;
        for (k = 0; k < vg_chain[t]; k++) if (!pattern_empty(t, (uint8_t)(vg_chain_base[t] + k))) any = 1u;
        if (!any) {
            uint8_t pat = vg_pre_pattern[t];
            vg_loop_has[t] = 0u;
            vg_loop_sync(t, pat);
            if (pat != tr[t].pattern) { tr[t].pattern = pat; tr[t].pending_pattern = SQ_NO_PENDING; if (playing) track_restart(t); }
            if (!track_has_notes(t)) vg_set_state(t, SQ_TS_EMPTY);
            else if (pattern_empty(t, pat)) vg_set_state(t, SQ_TS_PROPOSED);
            vg_msg_t("LOOP: NOTHING PLAYED ON ", t, "");
            return;
        }
    }
    activate_row(t, project.step[t][tr[t].pattern]);
    vg_set_state(t, SQ_TS_IN);
    vg_msg_t("LOOP CLOSED: ", t, " LOOPS");
}
static void vg_chain_tick(void)                             /* every 4 bars a chained track moves to its next pattern */
{
    uint32_t t;
    for (t = 0; t < SQ_TRACKS; t++)                        /* a hand (PERF, the grid) took the track off its loop: let it go */
        if (vg_chain_on[t] && !vg_in_loop(t, tr[t].pattern)) vg_loop_sync(t, tr[t].pattern);
    if (vg_bar % 4u) return;
    for (t = 0; t < SQ_TRACKS; t++) {
        uint8_t p;
        if (!vg_chain_on[t] || vg_chain[t] <= 1u) continue;
        p = (uint8_t)(vg_chain_base[t] + ((vg_bar / 4u) % vg_chain[t]));
        if (p >= SQ_PATTERNS || p == tr[t].pattern) continue;
        tr[t].pattern = p; tr[t].pending_pattern = SQ_NO_PENDING;
        if (playing) track_restart(t);
    }
}

/* ---- the boundary: the queue runs */
static uint8_t vg_silence_guard(uint16_t was_in)
{
    uint32_t t;
    uint8_t best = 255u;
    for (t = 0; t < SQ_TRACKS; t++) if (vg_track_in(t)) return 0u;
    for (t = 0; t < SQ_TRACKS; t++)
        if ((was_in & (1u << t)) && (best == 255u || vg_track_energy(t) > vg_track_energy(best))) best = (uint8_t)t;
    if (best == 255u) return 0u;
    vg_enter(best, tr[best].pattern);
    vg_msg_t("NO SILENCE BY MISTAKE: ", best, " STAYS");
    return 1u;
}

/* 0.24 LONGER / SHORTER (SEL + DOUBLE / SEL + HALF on the MOSSE, SHIFT + the pad on the grid): the LENGTH of every
 * track at once, twice or half - not the speed. Longer: each pattern goes round again in what its track has more
 * (track_fit: its copies - or what was written there, or what a SHORTER had left waiting). Shorter: the tracks play
 * their first half, the rest waits after the loop and comes back with LONGER. A track that cannot (twice would pass
 * 64 steps; an odd number of steps has no half) stays as it is, with its own loop; a TAPE track has no steps; a track
 * in a LOOP of the journey has that loop's length. Every track lands where the clock says (length_apply). */
static void vg_lengths(int32_t dir)
{
    uint32_t t, n = 0u, stay = 0u;
    char *p = msg_buf;
    for (t = 0; t < SQ_TRACKS; t++) {
        const sq_track_cfg_t *c = &project.track[t];
        uint32_t span = c->length > c->start ? (uint32_t)c->length - c->start : 1u, want;
        if (track_tape(t) || vg_chain_on[t]) continue;
        if (dir > 0) want = c->start + 2u * span;
        else want = (span & 1u) ? 0u : c->start + span / 2u;
        if (!want || want > SQ_STEPS) { stay++; continue; }
        len_pend[t] = 0u;
        length_apply((uint8_t)t, (uint8_t)want);
        n++;
    }
    p = put_s(p, dir > 0 ? "LONGER: " : "SHORTER: "); p = put_u(p, n); p = put_s(p, dir > 0 ? " TRACKS TWICE AS LONG" : " TRACKS HALF AS LONG");
    if (stay) { p = put_s(p, ", "); p = put_u(p, stay); p = put_s(p, " STAY"); }
    finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}

static void vg_run_queue(uint8_t boundary)              /* boundary 0: NOW, or stopped: the phrase playing is not in the trail yet */
{
    uint32_t i, t;
    uint16_t was_in = 0u;
    uint8_t had_break = vg_break_left ? 1u : 0u, had_moves = vg_q.n ? 1u : 0u;
    vg_states_from_project();                                /* 0.17: the states as the hands left them (PERF, scenes, patterns) */
    for (t = 0; t < SQ_TRACKS; t++) if (vg_track_in(t)) was_in |= (uint16_t)(1u << t);
    for (i = 0; i < vg_q.n; i++) {
        const sq_move_t *m = &vg_q.m[i];
        switch (m->kind) {
        case SQ_MV_IN:   vg_enter(m->a, m->b); break;
        case SQ_MV_OUT:  vg_leave(m->a); break;
        case SQ_MV_SWAP: if (vg_track_in(m->a) || vg_state(m->a) == SQ_TS_OUT) vg_enter(m->a, m->b); break;
        case SQ_MV_BREAK: {
            uint8_t bars = m->b ? m->b : 1u;
            if (!vg_break_left) vg_break_keep = mute_mask;   /* (a break in a break: the first one's mutes come back) */
            for (t = 0; t < SQ_TRACKS; t++) if (t != m->a) mute_mask |= (uint16_t)(1u << t);
            if (bars > vg_break_left) vg_break_left = bars;
            break;
        }
        case SQ_MV_DROP:
            for (t = 0; t < SQ_TRACKS; t++) if (vg_state(t) != SQ_TS_EMPTY && !vg_track_in(t)) vg_enter((uint8_t)t, 255u);
            project.viaggio.energy = 100u;
            vg_energy_from = 100u;
            break;
        case SQ_MV_HALF: vg_speed_set(-1); break;
        case SQ_MV_DOUBLE: vg_speed_set(1); break;
        case SQ_MV_LONGER: vg_lengths(1); break;         /* 0.24 */
        case SQ_MV_SHORTER: vg_lengths(-1); break;
        case SQ_MV_TRANSPOSE: ktrans_apply((int32_t)m->a - SQ_KTRANS_MAX); break;
        case SQ_MV_PROG:                                 /* (0.17: the HARMONY stays as the hands left it: queued only when it was on) */
            project.gen.harm_prog = m->a < SQ_PROGS_ALL ? m->a : 0u;
            break;
        case SQ_MV_GENRE: vg_set_genre_apply(m->a); break;
        case SQ_MV_THIN: vg_thin(); break;
        case SQ_MV_SWELL: vg_swell(); break;
        case SQ_MV_LOOP: vg_rec_arm = m->a; vg_rec_short = m->b; break;
        case SQ_MV_KEY:
            if (m->a < 12u) project.key_root = m->a;
            if (m->b < SQ_SCALES) project.key_scale = m->b;
            key_sync_slot();
            break;
        case SQ_MV_ENERGY: project.viaggio.energy = m->a > 100u ? 100u : m->a; break;
        case SQ_MV_BACK: {                               /* the phrase n before the one playing: it plays again, and the
                                                          * dead ends after it are forgotten. At a boundary the phrase that
                                                          * ended is index 0 of the trail; before one it is not there yet */
            uint32_t n = (m->a ? m->a : 1u) - (boundary ? 0u : 1u);
            const sq_phrase_t *ph = sq_trail_get(&vg_trail, vg_ring, n);
            if (ph) { sq_phrase_t keep = *ph; sq_trail_drop(&vg_trail, n); vg_phrase_restore(&keep); }
            break;
        }
        default: break;
        }
    }
    {   /* 0.10: a run before the boundary (QUANTISE BAR / BEAT, NOW) leaves the moves of the phrase itself waiting: a RISER */
        sq_move_t keep[SQ_MOVES];
        uint8_t nk = 0u;
        if (!boundary) for (i = 0; i < vg_q.n; i++) if (vg_q.m[i].kind == SQ_MV_RISER) keep[nk++] = vg_q.m[i];
        sq_queue_clear(&vg_q);
        for (i = 0; i < nk; i++) sq_queue_push(&vg_q, keep[i].kind, keep[i].a, keep[i].b);
    }
    if (had_moves && !had_break && !vg_break_left) vg_silence_guard(was_in);   /* (0.17: only a silence the moves made: the hands may want one) */
    vg_exit = 0u;
    vg_fill = 0u; if (boundary) vg_riser = 0u;
}

/* the moves that act before the boundary: the last bar (FILL, the exits), the last four (RISER) */
static void vg_prepare_last_bars(void)
{
    uint32_t i, t;
    uint8_t last = (uint8_t)(vg_bars() - 1u);
    if (vg_bar == last) {
        for (i = 0; i < vg_q.n; i++) {
            const sq_move_t *m = &vg_q.m[i];
            if (m->kind == SQ_MV_FILL || m->kind == SQ_MV_DROP) vg_fill = 1u;
            if (m->kind == SQ_MV_OUT && m->a < SQ_TRACKS) vg_exit |= (uint16_t)(1u << m->a);
            if (m->kind == SQ_MV_THIN) {                   /* the two that will go: they fade too */
                uint8_t k, in_n = 0u, gone = 0u;
                for (t = 0; t < SQ_TRACKS; t++) if (vg_track_in(t)) in_n++;
                for (k = 0; k < 2u && (uint32_t)in_n > (uint32_t)gone + 1u; k++) {
                    uint8_t best = 255u;
                    for (t = 0; t < SQ_TRACKS; t++)
                        if (vg_track_in(t) && !(vg_exit & (1u << t)) && (best == 255u || vg_track_energy(t) > vg_track_energy(best))) best = (uint8_t)t;
                    if (best == 255u) break;
                    vg_exit |= (uint16_t)(1u << best); gone++;
                }
            }
        }
        if (vg_break_left) vg_exit = 0u;                   /* in a BREAK the exits are not soft */
    }
    if (vg_bars() >= 8u && vg_bar + 4u >= vg_bars() && !vg_riser)
        for (i = 0; i < vg_q.n; i++) if (vg_q.m[i].kind == SQ_MV_RISER) vg_riser = 1u;
}

/* ---- every bar line (dinghy.c: seq_clock_tick), before the tracks move */
static void vg_bar_tick(void)
{
    uint8_t bars = vg_bars();
    if (!vg_on()) return;
    if (vg_break_left && --vg_break_left == 0u) { vg_break_left = 1u; vg_break_end(); }
    vg_bar++;
    if (vg_bar >= bars || vg_now || (project.viaggio.quant != SQ_VQ_PHRASE && vg_q.n)) {   /* 0.10: QUANTISE BAR / BEAT: every bar too */
        uint8_t boundary = vg_bar >= bars ? 1u : 0u;
        vg_now = 0u;
        if (boundary) {
            sq_phrase_t ph;
            vg_states_from_project();                      /* 0.17: the phrase as it was heard */
            vg_phrase_now(&ph);
            sq_trail_push(&vg_trail, vg_ring, &ph);
            project.viaggio.phrase_count = (uint8_t)((project.viaggio.phrase_count + 1u) % SQ_TRAIL);
            if (vg_rec_t < SQ_TRACKS) vg_loop_close();
            if (vg_speed) vg_speed_set(0);                 /* HALF / DOUBLE last one phrase */
            vg_energy_from = vg_riser ? project.viaggio.energy : vg_energy_cur;   /* (a riser's peak is not where the next phrase starts) */
        }
        vg_run_queue(boundary);
        if (boundary) {
            vg_bar = 0u;
            if (vg_rec_arm < SQ_TRACKS) { vg_loop_begin(vg_rec_arm); vg_rec_arm = 255u; }
            if (project.viaggio.energy == 100u && vg_energy_from == 100u) vg_energy_apply(100u);
        }
    }
    vg_prepare_last_bars();
    vg_chain_tick();
    {   /* the energy of this bar: the glide, or the riser */
        uint8_t e = sq_energy_glide(vg_energy_from, project.viaggio.energy, vg_bar, bars);
        if (vg_riser) e = sq_energy_riser(e, vg_bar, bars);
        vg_energy_apply(e);
    }
    ui_dirty = grid_dirty = 1u;
}

/* 0.10 QUANTISE BEAT: every beat that is not a bar line (dinghy.c: seq_clock_tick) the queue runs */
static void vg_beat_tick(void)
{
    if (!vg_on() || project.viaggio.quant != SQ_VQ_BEAT || !vg_q.n) return;
    vg_run_queue(0u);
    ui_dirty = grid_dirty = 1u;
}
static void vg_quant_turn(int32_t d)
{
    static const char *const N[SQ_VQS] = {"AT THE PHRASE BOUNDARY", "AT EVERY BAR", "AT EVERY BEAT"};
    project.viaggio.quant = change_u8(project.viaggio.quant, d, 0u, SQ_VQS - 1u);
    vg_msg2("MOVES ", N[project.viaggio.quant]);
}

/* the transport starts: the phrase starts with it */
static void vg_transport_start(void)
{
    vg_bar = 0u; vg_now = 0u;
    vg_fill = 0u; vg_exit = 0u; vg_riser = 0u;
    vg_break_end();
    vg_speed = 0;
    vg_energy_from = project.viaggio.energy;
    vg_energy_apply(project.viaggio.energy);
    if (vg_rec_arm < SQ_TRACKS && vg_on()) { vg_loop_begin(vg_rec_arm); vg_rec_arm = 255u; }
}
static void vg_transport_stop(void)
{
    if (vg_rec_t < SQ_TRACKS) vg_loop_close();
    vg_break_end();
    vg_speed = 0;
    vg_exit = 0u; vg_fill = 0u; vg_riser = 0u;
}

/* 0.17 the MOSSE: PERF's third page (SEL + GLO; the profile PALCO starts there). The journey itself always runs. */
static uint8_t vg_mosse_shown(void) { return (perf_mode || (in_held() & (1u << BTN_GLO))) && perf_page == 2u ? 1u : 0u; }
static void vg_mosse_open(void)
{
    win_close();
    perf_mode = 1u; perf_page = 2u;
    status_msg("MOSSE: BLACK = MOVES AT THE PHRASE, WHITE = MUTES");
    ui_dirty = grid_dirty = 1u;
}

/* a project loaded or new: nothing is queued, the trail starts again */
static void vg_reset(void)
{
    uint32_t t;
    sq_queue_clear(&vg_q);
    sq_trail_init(&vg_trail);
    vg_bar = 0u; vg_now = 0u; vg_riser = 0u; vg_fill = 0u;
    vg_break_left = 0u; vg_speed = 0; vg_rec_t = 255u; vg_rec_arm = 255u; vg_exit = 0u;
    record_arm = 0u;
    for (t = 0; t < SQ_TRACKS; t++) { vg_prop[t] = 255u; vg_pcfg_has[t] = 0u; vg_loop_has[t] = 0u; vg_chain_on[t] = 0u; vg_chain[t] = 1u; vg_chain_base[t] = 0u; vg_tira_n[t] = 0u; }
    project.viaggio.set_genre = vg_set_genre_cur();
    project.viaggio.on = 1u;                                  /* 0.17: always */
    vg_states_from_project();
    vg_energy_from = project.viaggio.energy;
    vg_energy_apply(project.viaggio.energy);
}

/* ---- SALVA VIAGGIO: the phrases that lasted longest become scenes, in a row, as the song */
static void vg_save_journey(void)
{
    uint8_t sel[SQ_SCENES], bars[SQ_SCENES], n, k;
    char *p = msg_buf;
    n = (uint8_t)sq_trail_scenes(&vg_trail, vg_ring, vg_bars(), SQ_SCENES, sel, bars);
    if (!n) { status_msg("NOTHING IN THE TRAIL YET"); ui_dirty = 1u; return; }
    for (k = 0; k < n; k++) {
        const sq_phrase_t *ph = sq_trail_get(&vg_trail, vg_ring, vg_trail.n - 1u - sel[k]);
        sq_scene_t *sc = &project.scene[k];
        uint32_t t, l;
        if (!ph) continue;
        sc->mute_mask = ph->mute;
        for (t = 0; t < SQ_TRACKS; t++) {
            sc->pattern[t] = ph->pattern[t] < SQ_PATTERNS ? ph->pattern[t] : 0u;
            for (l = 0; l < SQ_LANES; l++) sc->lane[t][l] = project.track[t].lane_base[l];
        }
        project.song.e[k].scene = k;
        project.song.e[k].bars = bars[k];
    }
    project.song.len = n;
    project.song.loop = 0u;
    p = put_s(p, "SET SAVED: "); p = put_u(p, n); p = put_s(p, " SCENES AND THE SONG (NOW SAVE THE PROJECT)");   /* (0.30: was JOURNEY) */
    finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}

/* ---- the panel in VIAGGIO mode: the white keys are the tracks, the black keys the moves */
static const uint8_t VG_BLACK_MOVE[11] = {SQ_MV_FILL, SQ_MV_BREAK, SQ_MV_RISER, SQ_MV_DROP, SQ_MV_HALF, SQ_MV_DOUBLE,
                                          SQ_MV_THIN, SQ_MV_SWELL, SQ_MV_SWAP, SQ_MV_LOOP, 0u /* NOW */};
static void vg_now_tap(void)                              /* NOW: the queue at the next bar (stopped: at once) */
{
    if (!vg_q.n) { status_msg("QUEUE EMPTY: NOTHING TO DO NOW"); ui_dirty = 1u; return; }
    if (!playing) { vg_run_queue(0u); vg_energy_from = project.viaggio.energy; vg_energy_apply(project.viaggio.energy); status_msg("NOW: DONE"); }
    else { vg_now = 1u; status_msg("NOW: AT THE NEXT BAR"); }
    ui_dirty = grid_dirty = 1u;
}
static void vg_track_tap(uint8_t t)
{
    if (t >= SQ_TRACKS) return;
    select_track(t);
    switch (vg_state(t)) {
    case SQ_TS_EMPTY: vg_tira(t, 0u); break;
    case SQ_TS_PROPOSED:                                 /* 0.10: a tap selects it and says what it has; the hold throws the dice */
        if (vg_proposals(t)) vg_browse(t, 0); else vg_tira(t, 0u);
        break;
    default:                                             /* IN or OUT: the track and its proposals */
        if (!vg_proposals(t)) vg_msg_t("", t, vg_track_in(t) ? " IN" : " OUT");
        else vg_msg_t("", t, vg_track_in(t) ? " IN, WITH PROPOSALS" : " OUT, WITH PROPOSALS");
        break;
    }
}
static void vg_track_queue(uint8_t t)                     /* SEL + a white key: in or out at the boundary */
{
    if (t >= SQ_TRACKS) return;
    if (vg_track_in(t)) { if (!vg_queue(SQ_MV_OUT, t, 0u)) vg_msg_t("QUEUED: ", t, " OUT"); }
    else if (vg_state(t) == SQ_TS_EMPTY) { vg_tira(t, 0u); if (!vg_queue(SQ_MV_IN, t, 255u)) vg_msg_t("QUEUED: ", t, " IN"); }
    else if (!vg_queue(SQ_MV_IN, t, vg_prop[t])) vg_msg_t("QUEUED: ", t, " IN");
}
static void vg_black(uint8_t bi, uint8_t sel_held)
{
    uint8_t kind;
    if (bi >= 11u) return;
    kind = VG_BLACK_MOVE[bi];
    if (!kind) { vg_now_tap(); return; }
    switch (kind) {
    case SQ_MV_BREAK: if (!vg_queue(kind, sel_held ? 255u : selected_track, sel_held ? 2u : 1u)) vg_msg2("QUEUED: BREAK ", sel_held ? "ALL, 2 BARS" : "1 BAR, THIS TRACK STAYS"); break;
    case SQ_MV_SWAP:
        if (vg_prop[selected_track] >= SQ_PATTERNS) { vg_msg_t("NO PROPOSAL ON ", selected_track, ": TAP IT FIRST"); break; }
        if (!vg_queue(kind, selected_track, vg_prop[selected_track])) vg_msg_t("QUEUED: SWAP ", selected_track, "");
        break;
    case SQ_MV_LOOP: if (!vg_queue(kind, selected_track, sel_held)) vg_msg_t("QUEUED: LOOP ", selected_track, sel_held ? " 4 BARS" : ""); break;
    case SQ_MV_HALF: case SQ_MV_DOUBLE:                  /* 0.24: with SEL not the speed: the LENGTH of every track (SHORTER / LONGER) */
        if (sel_held) kind = kind == SQ_MV_HALF ? SQ_MV_SHORTER : SQ_MV_LONGER;
        if (!playing && sel_held) { vg_lengths(kind == SQ_MV_LONGER ? 1 : -1); break; }   /* (stopped: at once, as the LENGTH knob) */
        {   /* (its opposite waiting in the queue: the two are no more, and the screen says so) */
            uint8_t opp = kind == SQ_MV_HALF ? SQ_MV_DOUBLE : kind == SQ_MV_DOUBLE ? SQ_MV_HALF : kind == SQ_MV_LONGER ? SQ_MV_SHORTER : SQ_MV_LONGER;
            uint8_t had = (uint8_t)(sq_queue_find(&vg_q, opp, 0u) >= 0);
            if (!vg_queue(kind, 0u, 0u)) vg_msg2(had ? "CANCELLED: " : "QUEUED: ", sq_move_name(had ? opp : kind));
        }
        break;
    case SQ_MV_THIN: if (!vg_queue(kind, 0u, 0u)) vg_msg2("QUEUED: THIN - ", "THE WHOLE SET, 2 TRACKS OUT"); break;   /* 0.27: who it works on */
    case SQ_MV_SWELL: if (!vg_queue(kind, 0u, 0u)) vg_msg2("QUEUED: SWELL - ", "THE WHOLE SET, 2 TRACKS IN"); break;
    default: if (!vg_queue(kind, 0u, 0u)) vg_msg2("QUEUED: ", sq_move_name(kind)); break;
    }
}
static void vg_service(void) { vg_profile_service(); }
static void vg_back(void)                                  /* OCT-: INDIETRO, in the queue */
{
    int i = sq_queue_find(&vg_q, SQ_MV_BACK, 0u);
    uint8_t n = i >= 0 ? (uint8_t)(vg_q.m[i].a + 1u) : 1u;
    if (!vg_trail.n) { status_msg("THE TRAIL IS EMPTY"); ui_dirty = 1u; return; }
    if (n > vg_trail.n) n = vg_trail.n;
    if (!vg_queue(SQ_MV_BACK, n, 0u)) { char *p = msg_buf; p = put_s(p, "QUEUED: BACK "); p = put_u(p, n); p = put_s(p, n == 1u ? " PHRASE" : " PHRASES"); finish(p); status_msg(msg_buf); }
}
/* 0.17 the MOSSE's key lights: a move waiting in the queue lit (9: INDIETRO; 10: anything to cancel), NOW blinking
 * while it waits for the bar */
static uint8_t vg_move_lit(int bi, uint8_t blink)
{
    uint32_t i;
    uint8_t kind = bi >= 0 && bi < 8 ? VG_BLACK_MOVE[bi] : bi == 8 ? SQ_MV_BACK : 0u;
    if (bi == 9) return vg_q.n ? 1u : 0u;
    if (bi == 10) return vg_now ? blink : 0u;
    for (i = 0; kind && i < vg_q.n; i++)
        if (vg_q.m[i].kind == kind || (kind == SQ_MV_HALF && vg_q.m[i].kind == SQ_MV_SHORTER) || (kind == SQ_MV_DOUBLE && vg_q.m[i].kind == SQ_MV_LONGER)) return 1u;
    return 0u;
}
/* 0.17 the MOSSE on the panel (PERF page 3, or GLO held on page 3): black 1 FILL, 2 BREAK (SEL: all, 2 bars), 3 RISER,
 * 4 DROP, 5 HALF, 6 DOUBLE, 7 THIN, 8 SWELL, 9 INDIETRO, 10 the last move cancelled, 11 NOW */
static void vg_move_black(int bi, uint8_t sel_held)
{
    if (bi < 0 || bi > 10) return;
    if (bi < 8) vg_black((uint8_t)bi, sel_held);
    else if (bi == 8) vg_back();
    else if (bi == 9) vg_cancel_last();
    else vg_now_tap();
}
/* 0.27: the screen says what the ENERGY works on - the whole set (velocity, filter, gate, how many hits), and the
 * patterns the engines made, which fill and empty with it ("MORE FULL, MORE EMPTY": four hands, the map) */
static void vg_energy_say(void)
{
    char *p = msg_buf;
    uint32_t t, n = 0u;
    for (t = 0; t < SQ_TRACKS; t++) if (project.th.pat[t][tr[t].pattern].style && !track_tape(t) && !track_break(t)) n++;
    p = put_s(p, "ENERGY "); p = put_u(p, project.viaggio.energy); p = put_s(p, ": THE WHOLE SET");
    if (n) { p = put_s(p, " + "); p = put_u(p, n); p = put_s(p, n == 1u ? " ENGINE PART" : " ENGINE PARTS"); }
    finish(p);
    status_msg(msg_buf);
}
static void vg_energy_turn(int32_t d)                       /* K1 on HOME page 0: the target */
{
    project.viaggio.energy = (uint8_t)clamp_i32((int32_t)project.viaggio.energy + d, 0, 100);
    if (!playing) { vg_energy_from = project.viaggio.energy; vg_energy_apply(project.viaggio.energy); }
    vg_energy_say();
    ui_dirty = grid_dirty = 1u;
}
static void vg_energy_set(uint8_t e)                       /* the remote, the grid: glides from here */
{
    project.viaggio.energy = e > 100u ? 100u : e;
    if (!playing) { vg_energy_from = project.viaggio.energy; vg_energy_apply(project.viaggio.energy); }
    ui_dirty = grid_dirty = 1u;
}
static void vg_bars_turn(int32_t d)
{
    uint8_t b = vg_bars();
    if (d > 0) b = b < 8u ? 8u : 16u; else b = b > 8u ? 8u : 4u;
    project.viaggio.phrase_bars = b;
    if (vg_bar >= b) vg_bar = (uint8_t)(b - 1u);
    status_num("PHRASE: BARS ", b);
    ui_dirty = grid_dirty = 1u;
}
static void vg_genre_turn(int32_t d)
{
    int i = sq_queue_find(&vg_q, SQ_MV_GENRE, 0u);
    uint8_t cur = i >= 0 ? vg_q.m[i].a : vg_set_genre_cur();
    cur = (uint8_t)(((int32_t)cur + d + SQ_SET_GENRES * 4) % SQ_SET_GENRES);
    if (cur == vg_set_genre_cur()) { if (i >= 0) sq_queue_remove(&vg_q, (uint32_t)i); vg_msg2("GENRE STAYS ", vg_genre()->name); return; }
    if (!playing) { vg_set_genre_apply(cur); return; }
    if (!vg_queue(SQ_MV_GENRE, cur, 0u)) vg_msg2("QUEUED: GENRE ", sq_set_genre(cur)->name);
}
static int32_t vg_genre_shown(void) { int i = sq_queue_find(&vg_q, SQ_MV_GENRE, 0u); return i >= 0 ? (int32_t)vg_q.m[i].a : (int32_t)vg_set_genre_cur(); }   /* 0.12 PICK */
static int32_t vg_key_shown(void) { int i = sq_queue_find(&vg_q, SQ_MV_KEY, 0u); return i >= 0 ? (int32_t)vg_q.m[i].a : (int32_t)project.key_root; }
static void vg_key_turn(int32_t d)
{
    int i = sq_queue_find(&vg_q, SQ_MV_KEY, 0u);
    uint8_t root = i >= 0 ? vg_q.m[i].a : project.key_root;
    root = (uint8_t)(((int32_t)root + d + 24) % 12);
    if (!playing) { project.key_root = root; key_sync_slot(); key_toast(); return; }
    if (!vg_queue(SQ_MV_KEY, root, project.key_scale)) vg_msg2("QUEUED: KEY ", sq_root_name(root));
}
static void vg_prog_turn(int32_t d)                         /* the PRESETS encoder: the progression, in the queue */
{
    int i = sq_queue_find(&vg_q, SQ_MV_PROG, 0u);
    uint8_t cur = i >= 0 ? vg_q.m[i].a : project.gen.harm_prog;
    char name[24];
    cur = (uint8_t)(((int32_t)cur + d + SQ_PROGS_ALL * 4) % SQ_PROGS_ALL);
    /* (0.29: DICE/PI is the fifth slot, the Pi's - its own chords and its own name: it read the first user slot's) */
    if (cur >= SQ_PROGS) sq_uprog_name(&project.uprog[cur - SQ_PROGS], project.key_scale, name, sizeof name);
    else sq_prog_name(vg_lib_genre(), cur, project.key_scale, name, sizeof name);
    if (!project.gen.harm_on) { project.gen.harm_prog = cur; harm_say("READY ", ": ARP 3 K1 ON"); ui_dirty = grid_dirty = 1u; return; }   /* 0.17: the HARMONY off: READY, as in 0.16 (0.9-0.16 here: switched on) */
    if (!playing) { project.gen.harm_prog = cur; vg_msg2(cur == SQ_PROG_PI ? "DICE/PI " : cur >= SQ_PROGS ? "USER PROG " : "PROG ", name); return; }
    if (!vg_queue(SQ_MV_PROG, cur, 0u)) vg_msg2(cur == SQ_PROG_PI ? "QUEUED: DICE/PI " : "QUEUED: PROG ", name);
}

/* ---- the remote on channel 13: CC 1-16 tap on the track, 17-27 the moves, 28 INDIETRO, 29 cancel, 30 the phrase,
 * 31 the progression; the energy is CC 3 of channel 14 (sagga_live.c) */
static void remote13_cc(uint8_t cc, uint8_t v);           /* sagga_remote2.c: 0.12, CC 33 and up */
static void vg_remote_cc(uint8_t cc, uint8_t v)
{
    uint8_t on = v >= 64u ? 1u : 0u;
    if (cc >= 33u) { remote13_cc(cc, v); return; }           /* 0.12: the Pi's new pages (with or without the journey) */
    if (!vg_on()) return;
    if (cc >= 1u && cc <= 16u) { if (on) vg_track_tap((uint8_t)(cc - 1u)); return; }
    if (cc >= 17u && cc <= 27u) { if (on) vg_black((uint8_t)(cc - 17u), 0u); return; }
    if (cc == 32u) { uint8_t t = (uint8_t)(v / 8u); if (t < SQ_TRACKS) vg_track_queue(t); return; }   /* 32: queue track v / 8 (any value) */
    if (!on) return;
    switch (cc) {
    case 28u: vg_back(); break;
    case 29u: vg_cancel_last(); break;
    case 30u: vg_bars_turn(v >= 96u ? 1 : -1); break;
    case 31u: vg_prog_turn(1); break;
    default: break;
    }
}

static uint8_t vg_remote_ch(uint8_t ch) { return (project.live.remote_mode == SQ_RM_13_14 && ch == 12u) ? 1u : 0u; }

/* the profile: chosen with SAVE + K4 (kept in the settings when SAVE is let go, or at the next STOP) */
static uint8_t vg_profile_dirty;
static void vg_profile_note(void)
{
    const vg_profile_t *pr = vg_prof();
    vg_profile_dirty = 1u;
    if (pr->viaggio_on) { perf_mode = 1u; perf_page = 2u; }      /* 0.17: the MOSSE */
    if (project.live.remote_mode != pr->remote_mode && pr->remote_mode == SQ_RM_13_14) {
        project.live.remote_mode = SQ_RM_13_14; project.live.remote_ch = 13u;
    }
    if (!vg_allows_home(home_page)) home_page = 0u;
    if (vg_profile == SQ_PROF_SEMPLICE) vg_msg2("PROFILE SEMPLICE: ", "SEQ 2 AND 3 HIDDEN WHILE OFF");   /* 0.27 */
    else vg_msg2("PROFILE ", pr->name);
}
static void vg_profile_boot(void)
{
    const vg_profile_t *pr = vg_prof();
    if (pr->viaggio_on) { perf_mode = 1u; perf_page = 2u; }      /* 0.17: the MOSSE */
    if (!vg_allows_home(home_page)) home_page = 0u;
}
static void vg_profile_service(void)                       /* the settings, when it is safe (nothing plays) */
{
    if (vg_profile_dirty && !playing && !save_down) { vg_profile_dirty = 0u; settings_store(); }
}


#ifdef DINGHY_HOST
/* the tests (tests/sagga_sim_tests.py, Log.viaggio): one line with the journey's state */
static void vg_host_dump(void)
{
    uint32_t k;
    printf("%6u ms  viaggio %u bar %u/%u energy %u/%u genre %u mute %04X speed %d rec %d STATES:", fm1_ms, (unsigned)vg_mosse_shown(),
           (unsigned)vg_bar, (unsigned)vg_bars(), (unsigned)vg_energy_cur, (unsigned)project.viaggio.energy,
           (unsigned)vg_set_genre_cur(), (unsigned)mute_mask, (int)vg_speed, vg_rec_t < SQ_TRACKS ? (int)vg_rec_t : -1);
    for (k = 0; k < SQ_TRACKS; k++) putchar("EPIO"[vg_state(k) & 3u]);
    printf(" QUEUE:");
    for (k = 0; k < vg_q.n; k++) printf(" %s/%u/%u", sq_move_name(vg_q.m[k].kind), (unsigned)vg_q.m[k].a, (unsigned)vg_q.m[k].b);
    printf(" TRAIL %u PATTERNS:", (unsigned)vg_trail.n);
    for (k = 0; k < SQ_TRACKS; k++) printf("%u", (unsigned)tr[k].pattern + 1u);
    printf(" SCENES %u SONG %u JRN %u\n", (unsigned)SQ_SCENES, (unsigned)project.song.len, (unsigned)project.viaggio.on);
}
#endif


/* ================================================================ 0.9 the REGISTA: SysEx with the Pi (docs/SAGGA-SEQ.md)
 * Every frame F0 7D 53 47 CMD ... F7, 7-bit bytes. Sent without waiting (sysex_try_send): what does not fit goes at
 * the next bar; the sequencer never waits for the host.
 *   50 STATO    FM-1 -> Pi  BAR*2 SCENE SNAP ROOT SCALE DEG+64 COL HARM PBAR PBARS ENERGY GENRE QUEUE PLAY
 *                           at every bar line, at a change of scene, snapshot or chord. BAR: bars since PLAY (14 bits);
 *                           SNAP 127 = none; DEG+64: the chord's step of the key; PBAR: the bar of the phrase (0..);
 *                           GENRE: the set genre; QUEUE: moves waiting
 *   51 FRASE    Pi -> FM-1  T BARS N (STEP NOTE VEL LEN)*N: a phrase onto track T's playing pattern at the next bar
 *                           (UNDO takes it back). BARS 1-4 = the pattern's length in bars of 16 steps; LEN 1..100 the
 *                           gate %, 0 = the whole step and the next (a long note)
 *   52 RISPOSTA FM-1 -> Pi  T CODE: 0 written, 1 busy (one is waiting), 2 the track is locked (LOOP records on it, or
 *                           every step is STEP LOCK), 3 the frame is broken
 *   53 TOCCATA  FM-1 -> Pi  T: the track was changed by hand (its generation goes back to 0)
 *   54 REGIA LED Pi -> FM-1 L*16: 0 off, 1 on, 2 passing: the REGIA view of the grid
 *   55 REGIA TASTO FM-1 -> Pi  R: rule R tapped on the grid */
enum { SX_STATO = 0x50, SX_FRASE = 0x51, SX_RISPOSTA = 0x52, SX_TOCCATA = 0x53, SX_REGIA_LED = 0x54, SX_REGIA_KEY = 0x55 };
static uint8_t rg_active;                   /* the Pi has spoken as the regista (a FRASE or a REGIA LED came): we talk */
static uint8_t rg_stato_due;                /* a STATO waits to go */
static uint8_t rg_last_scene = 255u, rg_last_snap = 255u, rg_last_chord = 255u;
static uint16_t rg_touched;                 /* TOCCATA to send, bit per track */
static uint16_t rg_bar;                     /* bars since PLAY */
static uint8_t rg_frase_t = 255u, rg_frase_bars, rg_frase_n;    /* a FRASE waiting for the bar line */
static uint8_t rg_frase[64][4] __attribute__((section(".pool")));
static uint8_t rg_key_pend = 255u;          /* a REGIA TASTO to send */
static uint8_t rg_risp_t = 255u, rg_risp_code;   /* a RISPOSTA to send (the newest one, if the queue was full) */

static int rg_send1(uint8_t cmd, uint8_t a, uint8_t b, uint8_t nb)
{
    uint8_t *q = sx_head(cmd);
    *q++ = (uint8_t)(a & 127u);
    if (nb > 1u) *q++ = (uint8_t)(b & 127u);
    *q++ = 0xF7u;
    return sysex_try_send(sx_out, (uint32_t)(q - sx_out));
}
static void rg_risposta(uint8_t t, uint8_t code)          /* sent by regia_service: it waits for room, never lost */
{
    if (rg_send1(SX_RISPOSTA, t, code, 2u) == 0) return;
    rg_risp_t = t; rg_risp_code = code;
}

static void rg_stato_send(void)
{
    uint8_t *q = sx_head(SX_STATO);
    int8_t deg = 0;
    uint8_t col = 0u, harm = harm_now(&deg, &col);
    sx_put7(&q, rg_bar, 2u);
    *q++ = (uint8_t)(scene_cursor & 127u);
    *q++ = snap_cur < SQ_SNAPS ? snap_cur : 127u;
    *q++ = project.key_root;
    *q++ = project.key_scale;
    *q++ = (uint8_t)((deg + 64) & 127);
    *q++ = col;
    *q++ = harm;
    *q++ = vg_bar;
    *q++ = vg_bars();
    *q++ = vg_energy_cur;
    *q++ = vg_set_genre_cur();
    *q++ = vg_q.n;
    *q++ = playing ? 1u : 0u;
    *q++ = 0xF7u;
    if (sysex_try_send(sx_out, (uint32_t)(q - sx_out)) == 0) rg_stato_due = 0u;
}

/* a FRASE from the Pi: kept until the bar line */
static void rg_frase_in(const uint8_t *p, uint32_t n)
{
    uint32_t i, cnt;
    if (n < 3u) return;
    if (p[0] >= SQ_TRACKS || p[1] < 1u || p[1] > 4u || p[2] > 64u || n < 3u + 4u * (uint32_t)p[2]) { rg_risposta(p[0] < SQ_TRACKS ? p[0] : 0u, 3u); return; }
    if (rg_frase_t < SQ_TRACKS) { rg_risposta(p[0], 1u); return; }
    if (vg_rec_t == p[0]) { rg_risposta(p[0], 2u); return; }
    cnt = p[2];
    for (i = 0; i < cnt; i++) {
        const uint8_t *e = p + 3u + 4u * i;
        if (e[0] >= 16u * p[1] || e[1] > 127u || e[2] > 127u || e[3] > 100u) { rg_risposta(p[0], 3u); return; }
        rg_frase[i][0] = e[0]; rg_frase[i][1] = e[1]; rg_frase[i][2] = e[2] ? e[2] : 100u; rg_frase[i][3] = e[3];
    }
    rg_frase_t = p[0]; rg_frase_bars = p[1]; rg_frase_n = (uint8_t)cnt;
    if (!playing) rg_frase_apply();
}
static void rg_frase_apply(void)
{
    uint8_t t = rg_frase_t, pat, len, i, locked = 1u;
    sq_step_t *row;
    sq_track_cfg_t *c;
    if (t >= SQ_TRACKS) return;
    rg_frase_t = 255u;
    pat = tr[t].pattern;
    row = project.step[t][pat];
    c = &project.track[t];
    len = (uint8_t)(16u * rg_frase_bars);
    for (i = 0; i < len; i++) if (!(row[i].flags & SQ_STEP_LOCK)) locked = 0u;
    if (locked || vg_rec_t == t) { rg_risposta(t, 2u); return; }
    undo_begin();
    undo_add(t, pat);
    th_forget(t, pat);                                  /* 0.23 */
    for (i = 0; i < len; i++) if (!(row[i].flags & SQ_STEP_LOCK)) sq_step_default(&row[i]);
    for (i = 0; i < rg_frase_n; i++) {
        sq_step_t *s = &row[rg_frase[i][0]];
        if (s->flags & SQ_STEP_LOCK) continue;
        s->note[0] = rg_frase[i][1];
        s->velocity = rg_frase[i][2];
        s->length = rg_frase[i][3] ? rg_frase[i][3] : 102u;            /* 0: two steps long */
        s->flags |= SQ_STEP_ON | SQ_STEP_SET;
    }
    {   /* 0.24: the phrase is steps of its own and brings its bars: the track's other patterns fit them, in time */
        uint8_t old = c->length, st = c->start;
        sq_row_keep(row);
        c->length = len; c->start = 0u;
        if (old != len || st) { track_fit(t, old, st, pat); track_loaded(t); }
    }
    if (c->division != SQ_DIV_1_16) c->division = SQ_DIV_1_16;
    if (tr[t].step >= c->length) tr[t].step = 0u;
    if (vg_on() && vg_state(t) == SQ_TS_EMPTY) vg_set_state(t, (mute_mask & (1u << t)) ? SQ_TS_PROPOSED : SQ_TS_IN);
    rg_risposta(t, 0u);
    ui_dirty = grid_dirty = 1u;
}

static void rg_regia_led_in(const uint8_t *p, uint32_t n)
{
    uint32_t i;
    for (i = 0; i < 16u && i < n; i++) g_regia_led[i] = p[i] > 2u ? 0u : p[i];
    grid_dirty = 1u;
}
static void regia_key_send(uint8_t rule) { rg_key_pend = (uint8_t)(rule & 15u); }
/* 0.12: a track the hand touched while the journey is on takes the state its contents and its mute say: EMPTY, IN, OUT
 * (PROPOSED when the playing pattern is empty but others are not); THIN, SWELL, the energy and the proposals see it */
static void vg_state_sync(uint32_t t)
{
    if (t >= SQ_TRACKS) return;
    if (!track_has_notes(t)) vg_set_state(t, SQ_TS_EMPTY);
    else if (vg_mutes_to_keep() & (1u << t)) { if (vg_state(t) != SQ_TS_PROPOSED) vg_set_state(t, SQ_TS_OUT); }   /* (0.17: not a BREAK's mutes) */
    else if (pattern_empty(t, tr[t].pattern)) vg_set_state(t, SQ_TS_PROPOSED);
    else vg_set_state(t, SQ_TS_IN);
}
static void vg_states_sync_all(void) { vg_states_from_project(); }
static void regia_touched(uint8_t t) { if (t < SQ_TRACKS) { rg_touched |= (uint16_t)(1u << t); vg_state_sync(t); } }

/* 0.17 SEL + GLO, a tap: PERF on the MOSSE page; again: the studio (the steps) */
static void vg_panel_toggle(void)
{
    if (perf_mode && perf_page == 2u) { perf_mode = 0u; status_msg("STUDIO (SEL+GLO: THE MOSSE)"); ui_dirty = grid_dirty = 1u; }
    else vg_mosse_open();
}

/* 0.17: a track's pattern changed by the hands (PRESETS, at the QUANTISE, at the loop's end): a proposal entering
 * brings its settings, once (as when the journey brings it in) */
static void vg_pattern_in(uint32_t t)
{
    uint8_t pat;
    if (t >= SQ_TRACKS) return;
    pat = tr[t].pattern;
    if (pat < SQ_PATTERNS && (vg_pcfg_has[t] & (1u << pat))) {
        uint8_t st = project.track[t].start, len = project.track[t].length;
        beat_cfg_apply((uint8_t)t, pat, &vg_pcfg[t][pat]);
        vg_pcfg_has[t] &= (uint8_t)~(1u << pat);
        if (project.track[t].start != st || project.track[t].length != len)
            track_changed((uint8_t)t);                  /* 0.28.1: another loop (a proposal starts on step 1): where the bar
                                                         * says, from the next tick - the explorer found a track with START 2
                                                         * a step off (put in line here, inside the tick that wrapped: a tick off) */
        else if (tr[t].step >= project.track[t].length) tr[t].step = project.track[t].start;
    }
    if (vg_prop[t] == pat) vg_prop[t] = 255u;
    vg_state_sync(t);
}

/* 0.17 PRESETS with nothing held: a proposal waiting on the track is queued first (it plays at the QUANTISE) */
static uint8_t vg_prop_queue(uint8_t t)
{
    uint8_t pp = t < SQ_TRACKS ? vg_prop[t] : 255u;
    char *p = msg_buf;
    if (pp >= SQ_PATTERNS || pp == tr[t].pattern || tr[t].pending_pattern < SQ_PATTERNS || pattern_empty(t, pp)) return 0u;
    queue_pattern(t, pp);
    p = put_s(p, "T"); p = put_u(p, (uint32_t)t + 1u); p = put_s(p, " PROPOSAL P"); p = put_u(p, (uint32_t)pp + 1u);
    p = put_s(p, playing && project.live.quant != SQ_Q_NOW ? " QUEUED" : " PLAYS"); finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
    return 1u;
}

/* 0.17 SEQ + BEAT held 0.6 s: a PROPOSAL. What BEAT would write on the selected track (SEQ's genre, part and variation)
 * goes into a free pattern of it (an empty one, else its oldest proposal; never one written by hand), the pattern
 * playing untouched; its settings wait for it. PRESETS queues it; held again: the next variation. */
static void beat_propose(void)
{
    uint8_t t = selected_track, fn = beat_func, nv, v, pat = 255u, k, n;
    beat_cfg_t cfg;
    char *p = msg_buf;
    if (track_tape(t) || track_break(t)) { status_msg("NO PROPOSALS ON A TAPE OR BREAK TRACK"); ui_dirty = 1u; return; }
    if (fn == SQ_FUNC_KIT || fn == SQ_FUNC_PROG || fn >= SQ_FUNCS) { status_msg("A PROPOSAL IS ONE PART (SEQ + SEL ENC: THE PART)"); ui_dirty = 1u; return; }
    nv = sq_beat_variants(beat_genre, fn);
    if (!nv) { status_msg("NO PATTERN"); ui_dirty = 1u; return; }
    v = (uint8_t)(beat_var % nv);
    for (k = 1; k < SQ_PATTERNS && pat == 255u; k++) {         /* an empty pattern after the one playing */
        uint8_t c = (uint8_t)((tr[t].pattern + k) % SQ_PATTERNS);
        if (!vg_slot_busy(t, c) && tr[t].pending_pattern != c && pattern_empty(t, c)) pat = c;
    }
    if (pat == 255u) {                                          /* none: the oldest proposal */
        uint8_t best = 255u;
        for (k = 1; k < SQ_PATTERNS; k++) {
            uint8_t c = (uint8_t)((tr[t].pattern + k) % SQ_PATTERNS);
            if (vg_slot_busy(t, c) || tr[t].pending_pattern == c || !(vg_pcfg_has[t] & (1u << c))) continue;
            if (best == 255u || (uint8_t)(vg_pcfg_age[t][c] - vg_age_n) > (uint8_t)(vg_pcfg_age[t][best] - vg_age_n)) best = c;
        }
        pat = best;
    }
    if (pat == 255u) { status_msg("NO FREE PATTERN ON THIS TRACK FOR A PROPOSAL"); ui_dirty = 1u; return; }
    undo_begin();
    undo_add(t, pat);
    sq_row_clear(project.step[t][pat]);
    n = beat_onto_x(t, pat, beat_genre, fn, v, 0u, &cfg);
    if (!n) { status_msg("NO PATTERN"); ui_dirty = 1u; return; }
    vg_prop[t] = pat;
    vg_pcfg[t][pat] = cfg;
    vg_pcfg_role[t][pat] = (uint8_t)(sq_role_family(sq_func_role(fn)) - 1u);
    vg_pcfg_age[t][pat] = ++vg_age_n;
    vg_pcfg_has[t] |= (uint8_t)(1u << pat);
    vg_state_sync(t);
    beat_var = (uint8_t)((v + 1u) % nv);
    p = put_s(p, "PROPOSAL "); p = put_s(p, sq_func_name(fn)); p = put_s(p, " #"); p = put_u(p, (uint32_t)v + 1u);
    p = put_s(p, " IN P"); p = put_u(p, (uint32_t)pat + 1u); p = put_s(p, ": PRESETS QUEUES IT"); finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}

/* the SysEx of the regista that come in (sagga_store.c: app_sysex) */
static void regia_sysex_in(uint8_t cmd, const uint8_t *p, uint32_t n)
{
    if (!rg_active) { rg_active = 1u; rg_stato_due = 1u; }
    if (cmd == SX_FRASE) rg_frase_in(p, n);
    else if (cmd == SX_REGIA_LED) rg_regia_led_in(p, n);
}

/* every bar line (dinghy.c: seq_clock_tick): the phrase that waited, a STATO */
static void regia_bar(void)
{
    rg_bar++;
    if (rg_frase_t < SQ_TRACKS) rg_frase_apply();
    rg_stato_due = 1u;
}
static void regia_transport_start(void) { rg_bar = 0u; rg_stato_due = 1u; }

/* every pass: what waits to go out, one frame a pass */
static void regia_service(void)
{
    uint8_t ch = 255u;
    int8_t deg;
    uint8_t col;
    if (!rg_active) { rg_touched = 0u; rg_key_pend = 255u; rg_stato_due = 0u; return; }   /* no regista: silence */
    if (harm_now(&deg, &col)) ch = (uint8_t)(deg + 64);
    if (scene_cursor != rg_last_scene || snap_cur != rg_last_snap || ch != rg_last_chord) {
        rg_last_scene = scene_cursor; rg_last_snap = snap_cur; rg_last_chord = ch;
        rg_stato_due = 1u;
    }
    if (rg_risp_t < SQ_TRACKS) { if (rg_send1(SX_RISPOSTA, rg_risp_t, rg_risp_code, 2u) == 0) rg_risp_t = 255u; return; }
    if (rg_key_pend < 16u) { if (rg_send1(SX_REGIA_KEY, rg_key_pend, 0u, 1u) == 0) rg_key_pend = 255u; return; }
    if (rg_touched) {
        uint8_t t;
        for (t = 0; t < SQ_TRACKS; t++) if (rg_touched & (1u << t)) { if (rg_send1(SX_TOCCATA, t, 0u, 1u) == 0) rg_touched &= (uint16_t)~(1u << t); return; }
    }
    if (rg_stato_due) rg_stato_send();
}
