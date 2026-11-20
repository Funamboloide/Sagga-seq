/* SPDX-License-Identifier: GPL-3.0-only */
/*
 * SAGGA PICK (0.12) - choosing with the keys. Included by dinghy.c after handle_encoders, before the screen.
 *
 * A group button held (HOME, GLO, SEQ, ARP, EDIT, ENV, LFO) + SEL + a key sets the knob IN FOCUS of the page shown:
 * the knob last turned on that page (K1 at first; black 11 moves the focus to the next knob). The screen marks it with
 * ">" before its label. What the keys mean depends on the knob:
 *   a list (a mode, a scale, a shape, a genre ...)   whites 1-16 = items 1-16, blacks 1-10 = items 17-26
 *   a count (pulses, hits, bars, a track)             whites 1-16, blacks 17-26
 *   a length in steps (LENGTH, loops, 16ths)          whites 4, 8, 12 .. 64; blacks 3 5 6 7 9 10 11 13 14 15 (polymeters)
 *   a root (the KEY, VIAGGIO's key, a chord's root)   the key is the note: F3 .. G5 (chromatic)
 *   a value in semitones or scale steps (TRANSPOSE, SHIFT, a curve)   F4 = 0, F3 = -12, G5 = +14
 *   a percentage                                      whites 1-10 = 10 .. 100 %, blacks 1-10 = 5, 15 .. 95 %
 *   a note (EDIT + SEL: the step's four notes)        the key is the note, with the keyboard's octave (SEL + OCT)
 *   a CC number                                       26 common CCs: 1 MOD 7 VOL 10 PAN 11 EXPR 71 RES 74 CUTOFF ...
 *   a continuous value (velocity, a CC value ...)     not by key: the knob (the screen says "-")
 * The knob is then turned by the difference, so what a knob does (its messages, its limits, the bar line it waits for)
 * happens the same way. The keys that mean something are lit; the key of the value now blinks.
 *
 * Held half a second with nothing else, a group shows the map of its keys in the message lines.
 *
 * The SEQ keys with a second meaning hold it: UNDO held = REDO, COOK held = the random COOK, KIT (black 7) held =
 * BAND, DICE SEQ (black 1) held = DICE PROG (0.11 had them on SEQ + SEL + the key, which is now PICK).
 */

enum { PG_HOME = 0, PG_GLO, PG_SEQ, PG_ARP, PG_EDIT, PG_ENV, PG_LFO, PG_COUNT };
enum { PK_NONE = 0, PK_LIST, PK_COUNT, PK_LEN, PK_ROOT, PK_SEMI, PK_PCT, PK_NOTE, PK_CC };
typedef struct { uint8_t kind; int32_t lo, hi, step, cur; } pick_t;

#define PICK_PAGES 8u                                   /* (0.13: HOME has 8) */
static uint8_t pick_focus[PG_COUNT][PICK_PAGES];
static uint32_t group_down_ms;                   /* when the group buttons held last changed (the map after 0.5 s) */
static uint32_t group_held_last;
static uint8_t map_shown;                         /* the map is on the screen (so that it is drawn once when due) */

static const uint8_t PICK_CC[26] = {1u, 2u, 5u, 7u, 10u, 11u, 12u, 13u, 71u, 72u, 73u, 74u, 75u, 76u, 77u, 78u,   /* whites */
                                    64u, 65u, 91u, 93u, 16u, 17u, 18u, 19u, 128u, 129u};                          /* blacks: SUSTAIN PORTA REVERB CHORUS GP1-4 BEND AFTERTOUCH */
static const uint8_t PICK_LENB[10] = {3u, 5u, 6u, 7u, 9u, 10u, 11u, 13u, 14u, 15u};

static const char *ui_cell_label(uint32_t i);    /* sagga_ui.c: the label of cell i as the screen shows it (without the mark) */
static void encoders_apply(int32_t dsel, int32_t dalg, int32_t dp, int32_t d1, int32_t d2, int32_t d3, int32_t d4,
                           int32_t f1, int32_t f2, int32_t f3, int32_t f4, int32_t fa, uint32_t held);
static uint8_t vg_bars(void);                    /* sagga_viaggio.c */
static int32_t vg_genre_shown(void);             /* ... the genre queued, else the set's */
static int32_t vg_key_shown(void);               /* ... the key queued, else the project's */

static int pick_group(uint32_t held)
{
    if (held & (1u << BTN_HOME)) return PG_HOME;
    if (held & (1u << BTN_EDIT)) return PG_EDIT;
    if (held & (1u << BTN_ENV)) return PG_ENV;
    if (held & (1u << BTN_LFO)) return PG_LFO;
    if (held & (1u << BTN_SEQ)) return PG_SEQ;
    if (held & (1u << BTN_ARP)) return PG_ARP;
    if (held & (1u << BTN_GLO)) return PG_GLO;
    return -1;
}
static uint32_t pick_group_btn(int g)
{
    static const uint8_t B[PG_COUNT] = {BTN_HOME, BTN_GLO, BTN_SEQ, BTN_ARP, BTN_EDIT, BTN_ENV, BTN_LFO};
    return 1u << B[g];
}
static uint8_t pick_page(int g)
{
    switch (g) {
    case PG_HOME: return home_page;
    case PG_GLO: return perf_page;
    case PG_SEQ: return seq_page;
    case PG_ARP: return arp_page;
    case PG_ENV: return env_lane < SQ_LANES ? env_lane : 0u;
    case PG_LFO: return lfo_page;
    default: return 0u;
    }
}
static uint8_t pick_focus_now(int g) { uint8_t pg = pick_page(g); return pick_focus[g][pg < PICK_PAGES ? pg : 0u] & 3u; }

/* a knob turned with a group held: the focus follows the hand */
static void pick_knob_turned(uint32_t held, int32_t d1, int32_t d2, int32_t d3, int32_t d4)
{
    int g = pick_group(held);
    uint8_t pg;
    if (g < 0) return;
    pg = pick_page(g);
    if (pg >= PICK_PAGES) return;
    pick_focus[g][pg] = d1 ? 0u : d2 ? 1u : d3 ? 2u : d4 ? 3u : pick_focus[g][pg];
}

/* the knob `k` of the page shown of group `g`: what the keys mean for it and the value now (d->cur) */
static void pick_desc(int g, uint32_t k, pick_t *d)
{
    uint32_t t = selected_track;
    sq_track_cfg_t *cfg = &project.track[t];
    sq_step_t *s = &project.step[t][tr[t].pattern][cursor_step];
    uint8_t pg = pick_page(g);
#define PK(kind_, lo_, hi_, step_, cur_) do { d->kind = (kind_); d->lo = (lo_); d->hi = (hi_); d->step = (step_); d->cur = (cur_); return; } while (0)
    d->kind = PK_NONE; d->lo = d->hi = d->cur = 0; d->step = 1;
    if (g == PG_HOME) {
        if (pg == 0u) {
            if (k == 0u) PK(PK_LIST, 0, (int32_t)ch_limit() - 1, 1, cfg->channel);
            if (k == 1u) PK(PK_LEN, 1, 64, 1, len_shown((uint8_t)t));
            if (k == 2u) PK(PK_LIST, 0, SQ_DIV_COUNT - 1, 1, cfg->division);
            { int32_t lim = track_in_key(t) ? 24 : 48; PK(PK_SEMI, -lim, lim, 1, cfg->transpose); }
        } else if (pg == 1u) {
            if (k == 0u) PK(PK_LIST, 0, SQ_DIR_COUNT - 1, 1, cfg->direction);
            if (k == 1u) PK(PK_NONE, 0, 0, 1, cfg->swing);
            if (k == 2u) PK(PK_LIST, -3, 3, 1, cfg->octave);
            PK(PK_LIST, 0, 1, 1, (cfg->flags & SQ_TF_FOLLOW) ? 1 : 0);
        } else if (pg == 2u) {
            if (k == 0u) PK(PK_COUNT, 0, SQ_KEYS - 1, 1, project.key_cur);
            if (k == 1u) PK(PK_ROOT, 0, 11, 1, project.key_root);
            if (k == 2u) PK(PK_LIST, 0, SQ_SCALES - 1, 1, project.key_scale);
            PK(PK_SEMI, -24, 24, 1, project.key_shift);
        } else if (pg == 3u) {
            if (k == 0u) PK(PK_LIST, 0, TRACK_MODES - 1, 1, track_mode(t));
            if (k == 1u) PK(PK_LIST, 0, SQ_ROLE_COUNT - 1, 1, cfg->role);
            if (k == 2u) PK(PK_LIST, 0, SQ_CH_COUNT - 1, 1, cfg->chord);
            PK(PK_LIST, -1, SQ_KEYS - 1, 1, cfg->key_slot == SQ_KEY_FOLLOW ? -1 : (int32_t)cfg->key_slot);
        } else if (pg == 4u) {
            if (k < 3u) PK(PK_LEN, 0, SQ_STEPS, 1, cfg->plen[k == 0u ? SQ_PL_NOTE : k == 1u ? SQ_PL_VEL : SQ_PL_GATE]);
            { uint8_t ch = track_ch((uint8_t)t), pc = project.scene[scene_cursor].pc[ch]; PK(PK_COUNT, 0, 127, 1, pc > 127u ? -1 : (int32_t)pc); }
        } else if (pg == 5u) {
            const sq_track_cfg_t *mv = mfx_view(t);                            /* 0.16: the READY one, if there is one */
            int32_t lo, hi;
            if (k == 0u) PK(PK_LIST, 0, SQ_MFXS - 1, 1, mfx_shown(t));
            if (mv->mfx >= SQ_MFXS_019) {                                      /* 0.20: the new five, each knob its kind */
                uint8_t fx = mv->mfx;
                sq_mfx_range(fx, (uint8_t)(k - 1u), track_in_key(t), &lo, &hi);
                if (k == 1u) {
                    if (fx == SQ_MFX_CHANCE || fx == SQ_MFX_GLITCH) PK(PK_PCT, 0, 100, 5, mv->mfx_amt);
                    if (fx == SQ_MFX_FILTER) PK(PK_NOTE, 0, 127, 1, mv->mfx_amt);
                    PK(PK_LIST, lo, hi, 1, mv->mfx_amt);
                }
                if (k == 2u) {
                    if (fx == SQ_MFX_FILTER) PK(PK_NOTE, 0, 127, 1, mv->mfx_time);
                    if (fx == SQ_MFX_RANDOM) PK(PK_NONE, 0, 64, 1, mv->mfx_time);
                    PK(PK_LIST, lo, hi, 1, mv->mfx_time);
                }
                if (fx == SQ_MFX_CHANCE) PK(PK_NONE, 0, 0, 1, mv->mfx_fb);
                if (hi - lo >= 50) PK(PK_PCT, lo, hi, 5, mv->mfx_fb);
                PK(PK_LIST, lo, hi, 1, mv->mfx_fb);
            }
            if (k == 1u) PK(PK_SEMI, -12, 12, 1, mv->mfx_amt);
            if (k == 2u) PK(PK_LIST, 0, mv->mfx == SQ_MFX_OCTAVE ? SQ_OCT_PATTERNS - 1 : SQ_ECHO_TIMES - 1, 1, mv->mfx_time);
            PK(PK_PCT, 10, 100, 5, mv->mfx_fb);
        } else if (pg == 7u) {                                              /* 0.13 CHAIN LIST */
            const sq_trackx_t *cx = &project.ext.track[t];
            uint8_t e = chain_edit < cx->chain_n ? chain_edit : (uint8_t)(cx->chain_n - 1u);
            if (k == 0u) PK(PK_COUNT, 1, SQ_CHAIN_MAX, 1, cx->chain_n);
            if (k == 1u) PK(PK_COUNT, 1, cx->chain_n, 1, (int32_t)e + 1);
            if (k == 2u) PK(PK_LIST, 0, SQ_PATTERNS - 1, 1, cx->chain_pat[e]);
            PK(PK_COUNT, 1, 8, 1, cx->chain_rep[e]);
        } else {
            if (k == 0u) PK(PK_NONE, 0, 0, 1, cfg->delay_ms);
            if (k == 1u) PK(PK_LIST, 0, 2, 1, chain_mode(t));
            if (track_tape(t)) {
                if (k == 2u) PK(PK_COUNT, 1, SQ_TAPE_BARS_MAX, 1, cfg->tape.bars);
                PK(PK_PCT, 0, 100, 10, cfg->tape.quant);
            }
            if (k == 2u) PK(PK_LIST, 0, SQ_GROOVES - 1, 1, project.ext.track[t].groove);   /* 0.15 GROOVE */
            PK(PK_PCT, 0, 100, 5, project.ext.track[t].groove_amt);
        }
    } else if (g == PG_GLO) {
        if (pg == 1u) {
            if (k == 0u) PK(PK_LIST, 0, 7, 1, tr[t].pending_pattern < SQ_PATTERNS ? tr[t].pending_pattern : tr[t].pattern);
            if (k == 1u) PK(PK_LEN, 1, 64, 1, len_shown((uint8_t)t));
            if (k == 2u) PK(PK_LIST, 0, SQ_SCALES - 1, 1, project.key_scale);
            PK(PK_LIST, 0, 1, 1, project.live.mute_q ? 1 : 0);
        } else if (pg == 2u) {
            if (k == 0u) PK(PK_PCT, 0, 100, 1, project.viaggio.energy);     /* (vg_energy_turn moves by the detent) */
            if (k == 1u) { uint8_t b = vg_bars(); PK(PK_LIST, 0, 2, 1, b <= 4u ? 0 : b <= 8u ? 1 : 2); }
            if (k == 2u) PK(PK_LIST, 0, SQ_SET_GENRES - 1, 1, vg_genre_shown());
            PK(PK_ROOT, 0, 11, 1, vg_key_shown());
        } else if (pg == 3u) {                                             /* 0.25 THE METRE: white 1 = a bar of 3 steps ... */
            uint8_t st = bar_shown();
            if (k == 0u) PK(PK_COUNT, (int32_t)SQ_BAR_MIN, (int32_t)SQ_BAR_MAX, 1, st);
            if (k == 1u && sq_metre_options(st) > 1u) PK(PK_LIST, 0, (int32_t)sq_metre_options(st) - 1, 1, (int32_t)sq_metre_index(st, beats_shown()));
            if (k == 2u) PK(PK_LIST, 0, 1, 1, project.ext.scene_metre_on ? 1 : 0);   /* 0.26 SCENE METRE */
            PK(PK_NONE, 0, 0, 1, 0);
        } else {
            if (k == 0u) PK(PK_NONE, 0, 127, 1, morph_pos);
            if (k == 1u) PK(PK_COUNT, 0, SQ_SCENES - 1, 1, project.live.morph_b);
            if (k == 2u) PK(PK_SEMI, -24, 24, 1, ktrans_target());
            PK(PK_LIST, 0, SQ_QUANTS - 1, 1, project.live.quant);
        }
    } else if (g == PG_SEQ) {
        sq_gen_t *gn = &project.gen;
        if (pg == 0u) {
            if (k == 0u) PK(PK_COUNT, 1, (int32_t)cfg->length - cfg->start, 1, cfg->euc_pulses);
            if (k == 1u) PK(PK_COUNT, 0, (int32_t)cfg->length - cfg->start - 1, 1, cfg->euc_rot);
            if (k == 2u) PK(PK_LIST, 0, SQ_RF_COUNT - 1, 1, cfg->euc_fam);
            PK(PK_PCT, 1, 100, 5, gn->heat);
        } else if (pg == 1u) {
            if (k == 0u) PK(PK_LIST, 0, SQ_ALGOS - 1, 1, algo_shown(t));
            PK(PK_NONE, 0, 0, 1, 0);
        } else if (pg == 2u) {
            if (k == 0u) PK(PK_LIST, 0, GEN_TARGET_SETS - 1, 1, gen_target_index());
            if (k == 1u) PK(PK_PCT, 1, 100, 5, gn->evo_amount);
            if (k == 2u) PK(PK_LIST, 0, SQ_EVO_EVERY - 1, 1, gn->evo_every);
            PK(PK_LIST, 0, SQ_SCOPES - 1, 1, gn->scope);
        } else if (pg == 3u) {
            if (k == 0u) PK(PK_COUNT, SQ_X_HITS_MIN, SQ_X_HITS_MAX, 1, cfg->expo.hits);
            if (k == 1u) PK(PK_SEMI, -8, 8, 1, cfg->expo.curve);
            if (k == 2u) PK(PK_LIST, 0, SQ_X_SPANS - 1, 1, cfg->expo.span);
            PK(PK_LIST, 0, SQ_X_SHAPES - 1, 1, cfg->expo.shape);
        } else if (pg == 4u) {
            if (k == 0u) PK(PK_LIST, 0, SQ_X_VELS - 1, 1, cfg->expo.vel);
            if (k == 1u) PK(PK_PCT, 5, 100, 5, cfg->expo.gate);
            if (k == 2u) PK(PK_PCT, 0, 50, 5, cfg->expo.jitter);
            PK(PK_LIST, 0, SQ_X_NOTES - 1, 1, cfg->expo.notes);
        } else if (pg == 5u) {
            if (k == 0u) PK(PK_PCT, 0, 100, 5, gn->density);
            if (k == 1u) PK(PK_LIST, 0, SQ_WHENS - 1, 1, gn->when);
            if (k == 2u) PK(PK_LIST, 0, SQ_EVERYS - 1, 1, gn->every);
            PK(PK_LIST, 0, SQ_GMS - 1, 1, gn->genre_mode);
        } else {
            if (k == 0u) PK(PK_LIST, 0, SQ_BRK_CHOPS - 1, 1, cfg->brk_chop);
            if (k == 1u) PK(PK_LIST, 0, 7, 1, SQ_BRK_ROLL(cfg->brk_cfg));
            if (k == 2u) PK(PK_LIST, 0, 7, 1, SQ_BRK_SWAP(cfg->brk_cfg));
            PK(PK_LIST, 0, 2, 1, SQ_BRK_SL(cfg->brk_cfg));
        }
    } else if (g == PG_ARP) {
        sq_gen_t *gn = &project.gen;
        if (pg == 0u) {
            if (k == 0u) PK(PK_LIST, 0, SQ_CHORD_COUNT - 1, 1, SQ_CHORD_MODE(cfg->chord_mode));
            if (k == 1u) PK(PK_COUNT, 1, 3, 1, SQ_CHORD_OCTS(cfg->chord_mode));
            if (k == 2u) PK(PK_LIST, 0, SQ_ARP_RATE_MAX, 1, arp_rate_pos(cfg->arp_rate));   /* (0.18: in the knob's order) */
            PK(PK_LIST, 0, 3, 1, ((cfg->arp_flags & SQ_AF_HOLD) ? 2 : 0) | ((cfg->arp_flags & SQ_AF_RETRIG) ? 1 : 0));
        } else if (pg == 1u) {
            if (k == 0u) PK(PK_LIST, 0, SQ_CH_COUNT - 1, 1, cfg->chord);
            if (k == 1u) PK(PK_LIST, 0, SQ_CK_COUNT - 1, 1, cfg->chord_key);
            if (k == 2u) PK(PK_LIST, 0, SQ_VOICES - 1, 1, cfg->voicing);
            PK(PK_NONE, -50, 50, 5, cfg->strum);
        } else if (pg == 2u) {
            if (k == 0u) PK(PK_LIST, 0, 2, 1, harm_state());
            if (k == 1u) PK(PK_LIST, 0, SQ_PROGS_ALL - 1, 1, gn->harm_prog);
            if (k == 2u) { static const uint8_t B[5] = {0u, 1u, 2u, 4u, 8u}; int32_t i = 0; while (i < 4 && B[i] != gn->harm_bars) i++; PK(PK_LIST, 0, 4, 1, i); }
            PK(PK_LIST, 0, 1, 1, (cfg->flags & SQ_TF_FOLLOW) ? 1 : 0);
        } else if (pg == 3u) {
            if (k == 0u) PK(PK_LIST, 0, SQ_FMS - 1, 1, cfg->follow_mode);
            if (k == 1u) PK(PK_LIST, 0, SQ_GENRES, 1, harm_genre_pos());          /* 0.16: FREE, then the genres */
            if (k == 2u) PK(PK_LIST, 0, SQ_MOODS - 1, 1, gn->harm_mood);
            PK(PK_LIST, 0, SQ_HRS - 1, 1, gn->harm_rhythm);
        } else if (pg == 4u) {
            sq_uprog_t *u = &project.uprog[uprog_sel];
            if (k == 0u) PK(PK_COUNT, 0, SQ_UPROG_SLOTS - 1, 1, uprog_sel);
            if (k == 1u) PK(PK_COUNT, 0, 7, 1, uprog_pos);
            if (k == 2u) {                                                  /* (semitones above the key's root: the key of that root picks it) */
                int32_t v = -1;
                if (uprog_pos < u->n) {
                    if (u->semi[uprog_pos] == 255u) { sq_hchord_t x = {u->deg[uprog_pos], u->col[uprog_pos], 255u, 0u}; v = sq_hchord_semi(project.key_scale, &x); }
                    else v = u->semi[uprog_pos];
                }
                PK(PK_ROOT, 0, 11, 2, v);                                        /* step 2: "relative to the key" (pick_target) */
            }
            if (uprog_pos < u->n && u->semi[uprog_pos] == 255u) PK(PK_LIST, 0, SQ_HCS - 1, 1, u->col[uprog_pos]);
            PK(PK_LIST, 0, SQ_HSHAPES - 1, 1, uprog_pos < u->n ? u->shape[uprog_pos] : 0);
        } else {
            sq_uprog_t *u = &project.uprog[uprog_sel];
            if (k == 0u) PK(PK_LIST, 0, SQ_MOODS - 1, 1, u->mood);
            if (k == 1u) PK(PK_LIST, 0, SQ_HRS - 1, 1, uprog_rhythm_r);
            if (k == 2u) PK(PK_LEN, 0, 64, 1, uprog_pos < u->n ? u->dur[uprog_pos] : 0);
            PK(PK_LIST, 0, 4, 1, uprog_pos < u->n ? u->push[uprog_pos] : 0);
        }
    } else if (g == PG_EDIT) {                                            /* EDIT + SEL: the step's notes 1-4 (step_note_turn) */
        if (k < SQ_POLY && s->note[k] != SQ_NOTE_NONE) PK(PK_NOTE, 0, 127, 1, s->note[k]);
        if (k < SQ_POLY && (k == 0u || s->note[k - 1u] != SQ_NOTE_NONE)) PK(PK_NOTE, 0, 127, 1, (k ? (int32_t)s->note[k - 1u] : (int32_t)PEN(t)) - 1);   /* (an empty note: the turn starts from the one before) */
        PK(PK_NONE, 0, 0, 1, 0);
    } else if (g == PG_ENV) {
        uint32_t n = env_lane < SQ_LANES ? env_lane : 0u;
        if (k == 0u) PK(PK_NONE, 0, 0, 1, 0);
        if (k == 1u) PK(PK_CC, 0, SQ_CC_MAX, 1, cfg->lane_cc[n] == SQ_LANE_NONE ? -1 : (int32_t)cfg->lane_cc[n]);
        if (k == 2u) PK(PK_NONE, 0, 0, 1, 0);
        PK(PK_LIST, 0, 7, 1, cfg->lane_flags[n] & 7u);
    } else if (g == PG_LFO) {
        sq_lfo_t *l = &project.lfo[lfo_sel];
        if (pg == 0u) {
            if (k == 0u) PK(PK_LIST, 0, SQ_LFO_SHAPES - 1, 1, l->shape);
            if (k == 1u) PK(PK_LIST, 0, SQ_LFO_RATES - 1, 1, l->rate);
            PK(PK_NONE, 0, 127, 1, k == 2u ? l->depth : l->center);
        } else if (pg == 1u) {
            if (k == 0u) PK(PK_LIST, 0, SQ_LD_ALL - 1, 1, l->dest);
            if (k == 1u && l->dest == SQ_LD_CC) PK(PK_COUNT, 0, (int32_t)ch_limit() - 1, 1, l->target);
            if (k == 1u) PK(PK_COUNT, 0, (int32_t)LFO_TGT_N - 1, 1, lfo_tgt_idx(l->target));   /* (0.31: whites 13-16 the groups) */
            if (k == 2u) PK(PK_CC, 0, SQ_CC_MAX, 1, l->param);
            PK(PK_NONE, 0, 127, 1, l->phase);
        } else if (pg == 2u) {
            if (k == 0u) PK(PK_LIST, 0, 1, 1, l->enabled ? 1 : 0);
            if (k == 1u) PK(PK_LIST, 0, 1, 1, (l->flags & SQ_LF_RETRIG) ? 1 : 0);
            if (k == 2u) PK(PK_LIST, 0, 1, 1, (l->flags & SQ_LF_INVERT) ? 1 : 0);
            PK(PK_COUNT, 1, SQ_TRACKS, 1, project.ext.lfo[lfo_sel].trig ? project.ext.lfo[lfo_sel].trig : 0);   /* 0.13 TRIG: white N = track N (the clock: the knob down) */
        } else if (pg == LFO_PAGE_ENV) {                                  /* 0.20 ENV */
            const sq_lfoe_t *e = &project.ext.lfoe[lfo_sel];
            if (k == 2u) PK(PK_PCT, 0, 100, 5, e->s);
            PK(PK_LIST, 0, SQ_ENV_TIMES - 1, 1, k == 0u ? e->a : k == 1u ? e->d : e->r);
        } else if (pg == LFO_PAGE_MOD) {                                  /* 0.20 MOD MATRIX */
            const sq_mod_t *m = &project.ext.mod[mod_slot];
            if (k == 0u) PK(PK_COUNT, 0, SQ_MODS - 1, 1, mod_slot);
            if (k == 1u) PK(PK_LIST, 0, SQ_MSS - 1, 1, m->src);
            if (k == 2u) PK(PK_LIST, 0, SQ_MDS - 1, 1, m->dst);
            PK(PK_NONE, -100, 100, 5, m->amt);
        } else {                                                          /* 0.13 RATE SEQ */
            const sq_lfox_t *x = &project.ext.lfo[lfo_sel];
            if (k == 0u) PK(PK_COUNT, 1, SQ_RSEQ_MAX, 1, x->seq_n < 2u ? 1 : x->seq_n);   /* (white 1: OFF, white N: N rates) */
            if (k == 1u) PK(PK_LIST, 0, SQ_RES - 1, 1, x->seq_every);
            if (k == 2u) PK(PK_COUNT, 0, (x->seq_n >= 2u ? x->seq_n : SQ_RSEQ_MAX) - 1, 1, rseq_pos);
            PK(PK_LIST, 0, SQ_LFO_RATES - 1, 1, x->seq_rate[rseq_pos & 7u] < SQ_LFO_RATES ? x->seq_rate[rseq_pos & 7u] : l->rate);
        }
    }
#undef PK
}

#define PICK_NO 0x7FFFFFFF
/* the value key `k` (0..26: wi its white index, bi its black index, or -1) means for this knob, PICK_NO for none */
static int32_t pick_target(const pick_t *d, int wi, int bi, uint32_t k)
{
    int32_t idx = wi >= 0 ? wi : 16 + bi, v;
    if (wi < 0 && bi >= 10) return PICK_NO;                            /* black 11 is the focus key, never a value */
    switch (d->kind) {
    case PK_LIST: case PK_COUNT:
        v = d->lo + idx;
        return v > d->hi ? PICK_NO : v;
    case PK_LEN:
        v = wi >= 0 ? 4 * (wi + 1) : (int32_t)PICK_LENB[bi];
        return v > d->hi || v < d->lo ? PICK_NO : v;
    case PK_ROOT:
        if (d->step == 2) return (int32_t)((SQ_KEY0 + k + 12u - project.key_root) % 12u);   /* above the key's root */
        return (int32_t)((SQ_KEY0 + k) % 12u);
    case PK_NOTE:
        return clamp_i32((int32_t)SQ_KEY0 + (int32_t)k + 12 * (int32_t)key_octave, 0, 127);
    case PK_SEMI:
        return clamp_i32((int32_t)k - 12, d->lo, d->hi);
    case PK_PCT:
        if (wi >= 10) return PICK_NO;
        v = wi >= 0 ? (wi + 1) * 10 : 5 + 10 * bi;
        v = ((v + d->step / 2) / d->step) * d->step;
        return clamp_i32(v, d->lo, d->hi);
    case PK_CC:
        return (int32_t)PICK_CC[idx];
    default:
        return PICK_NO;
    }
}

/* the turns that take a value from `cur` to `target` through kstep with `step` (a value between two multiples counts
 * as the one under it when it goes down) */
static int32_t pick_delta(int32_t cur, int32_t target, int32_t step)
{
    int32_t q;
    if (step <= 2) return target - cur;                                 /* (2: PK_ROOT's "relative" mark, a step of one) */
    q = cur >= 0 ? cur / step : -((-cur + step - 1) / step);
    if (target >= cur) return target / step - q;
    return q * step == cur ? target / step - q : target / step - q - 1;
}

static void pick_say(const char *lab, int32_t target, const pick_t *d)
{
    char *p = msg_buf;
    p = put_s(p, "> "); p = put_s(p, lab); p = put_s(p, " ");
    if (d->kind == PK_ROOT) { if (d->step == 2) p = put_s(p, sq_degree_name((uint8_t)target)); else p = put_s(p, sq_root_name((uint8_t)target)); }
    else if (d->kind == PK_NOTE) { if (target < 0) p = put_s(p, "-"); else p = put_note(p, (uint8_t)target); }
    else if (d->kind == PK_PCT) { p = put_u(p, (uint32_t)target); p = put_s(p, "%"); }
    else if (d->kind == PK_LIST || d->kind == PK_COUNT) { p = put_s(p, "#"); p = put_u(p, (uint32_t)(target - d->lo + 1)); }
    else if (d->kind == PK_SEMI) p = put_i(p, target);
    else p = put_u(p, (uint32_t)target);
    finish(p);
    status_msg(msg_buf);
}

/* group `g` held, SEL held, key `k` down */
static void pick_key(uint32_t held, int g, uint32_t k)
{
    int wi = key_is_in(white_key, 16u, k), bi = key_is_in(black_key, 11u, k);
    uint8_t pg = pick_page(g), f;
    pick_t d;
    int32_t target, dd[4] = {0, 0, 0, 0};
    const char *msg_was = msg_text;
    uint32_t until_was = msg_until;
    if (pg >= PICK_PAGES) pg = 0u;
    if (bi == 10) {                                                     /* black 11: the focus to the next knob */
        pick_focus[g][pg] = (uint8_t)((pick_focus[g][pg] + 1u) & 3u);
        { char *p = msg_buf; p = put_s(p, "FOCUS > "); p = put_s(p, ui_cell_label(pick_focus[g][pg])); finish(p); status_msg(msg_buf); }
        ui_dirty = 1u;
        return;
    }
    f = pick_focus[g][pg] & 3u;
    pick_desc(g, f, &d);
    if (d.kind == PK_NONE) { char *p = msg_buf; p = put_s(p, ui_cell_label(f)); p = put_s(p, ": BY THE KNOB (BLACK 11: NEXT KNOB)"); finish(p); status_msg(msg_buf); return; }
    target = pick_target(&d, wi, bi, k);
    if (target == PICK_NO) { char *p = msg_buf; p = put_s(p, ui_cell_label(f)); p = put_s(p, ": "); p = put_u(p, (uint32_t)(d.hi - d.lo + 1)); p = put_s(p, " CHOICES"); finish(p); status_msg(msg_buf); return; }
    if (g == PG_ARP && pick_page(g) == 2u && f == 1u) {                 /* the progression: straight to it (K2 walks by mood and asks the Pi) */
        piprog_leave();
        harm_prog_set((uint8_t)target);
    } else if (g == PG_LFO && pick_page(g) == 3u && f == 0u) {          /* 0.13 RATE SEQ STEPS: white 1 OFF, white N: N rates */
        project.ext.lfo[lfo_sel].seq_n = (uint8_t)(target < 2 ? 0 : target);
        if (rseq_pos >= (target < 2 ? SQ_RSEQ_MAX : (uint32_t)target)) rseq_pos = 0u;
        ui_dirty = 1u;
    } else if (target != d.cur) {
        dd[f] = pick_delta(d.cur, target, d.step);
        encoders_apply(0, 0, 0, dd[0], dd[1], dd[2], dd[3], 1, 1, 1, 1, 1, g == PG_EDIT ? held : held & ~(1u << BTN_SEL));   /* (EDIT + SEL knobs: the notes) */
    }
    if (msg_text == msg_was && msg_until == until_was) {                /* the knob said nothing: say where it landed */
        pick_t now;
        pick_desc(g, f, &now);
        pick_say(ui_cell_label(f), now.kind == PK_NONE ? target : now.cur, &d);
    }
    ui_dirty = grid_dirty = 1u;
}

/* the LEDs while a group and SEL are held: the keys that mean something, the key of the value now blinking */
static void pick_leds(int g, uint8_t blink)
{
    pick_t d;
    uint32_t k;
    uint8_t f = pick_focus_now(g);
    pick_desc(g, f, &d);
    for (k = 0; k < 27u; k++) {
        int wi = key_is_in(white_key, 16u, k), bi = key_is_in(black_key, 11u, k);
        int32_t v;
        if (bi == 10) { fm1_led_key(KEY_LED(k), 1); continue; }         /* the focus key */
        if (d.kind == PK_NONE) continue;
        v = pick_target(&d, wi, bi, k);
        if (v == PICK_NO) continue;
        fm1_led_key(KEY_LED(k), v == d.cur ? blink : 1u);
    }
}

/* the mark before the label of the knob in focus: "> LENGTH" (">-" when the keys cannot set it); `l` holds 18 */
static void pick_mark(int g, char *l)
{
    uint8_t f = pick_focus_now(g);
    uint32_t n = 0u;
    pick_t d;
    pick_desc(g, f, &d);
    while (l[n]) n++;
    if (n > 15u) n = 15u;                                               /* (two columns for the mark: the label cut) */
    l[n + 2u] = 0;
    while (n > 0u) { l[n + 1u] = l[n - 1u]; n--; }
    l[0] = '>'; l[1] = d.kind == PK_NONE ? '-' : ' ';
}

/* the map of a group's keys, two lines of 29 characters, when it is held half a second with nothing happening */
static const char *pick_kind_help(const pick_t *d)
{
    switch (d->kind) {
    case PK_LIST: case PK_COUNT: return "SEL+KEY: ITEM 1-16 (B 17-26)";
    case PK_LEN: return "SEL+W 4,8..64  B 3,5,6,7,9..";
    case PK_ROOT: return "SEL+KEY: THE NOTE F3-G5";
    case PK_SEMI: return "SEL+KEY: F4=0 F3=-12 G5=+14";
    case PK_PCT: return "SEL+W1-10 10-100%  B 5-95%";
    case PK_NOTE: return "SEL+KEY: THE NOTE (OCT: 8VA)";
    case PK_CC: return "SEL+KEY: MOD VOL PAN CUTOFF..";
    default: return "SEL+B11 NEXT KNOB  THIS: TURN";
    }
}
static void pick_map_lines(int g, char *l1, char *l2)
{
    static const char *const L1[PG_COUNT] = {
        "W TRACK  B TRK BANK MUTE SOLO",                /* HOME */
        "W MUTE/SOLO  B SCENES ALL INV",                /* GLO */
        "W TOOLS  B DICE SCOPE KIT EVO",                /* SEQ */
        "KEYS PLAY TRACK, REC WRITES",                  /* ARP */
        "W CURSOR  B LOCK COPY PASTE..",                /* EDIT */
        "W CURSOR  B1-8 THE LANE",                      /* ENV (0.32: the black keys) */
        "W LFO ON/OFF  B1-6 THE PAGE",                  /* LFO */
    };
    /* 0.32: the black keys that had nothing, on line 2 while SEL is not held (with SEL: what PICK does, as before) */
    static const char *const L2[PG_COUNT] = { 0, 0, 0, 0, "B8 FORCE 9/10 MOVE 11 EXTRAS", "B9 RAMP UP 10 DOWN 11 CLEAR", "B7CPY 8PST 9OFF 10FREE 11RST" };
    pick_t d;
    uint8_t f = pick_focus_now(g);
    char *p;
    pick_desc(g, f, &d);
    p = put_s(l1, g == PG_ARP && track_break(selected_track) ? "W CHOP 1-16  B ROLL HALF DBL" :
                  g == PG_ARP && track_drum(selected_track) ? "W PLAY  B1-4 REPEAT (PLAYING)" :
                  g == PG_EDIT ? "B LCK CPY PST CLR PLN TIE SLD" :
                  g == PG_GLO && perf_page == 2u ? "B FIL BRK RIS DRP HLF DBL ..." : L1[g]);   /* (0.13; 0.17 the MOSSE) */
    *p = 0;
    p = put_s(l2, L2[g] && !(eff_held() & (1u << BTN_SEL)) ? L2[g] : pick_kind_help(&d));
    *p = 0;
}

/* the map for whatever is held: a PICK group, else FX, SAVE or SEL alone; 0 when nothing is held. l1, l2 hold 32 */
static uint8_t pick_map_any(uint32_t held, char *l1, char *l2)
{
    int g = pick_group(held);
    const char *a = 0, *b = 0;
    if (g >= 0 && !(held & (1u << BTN_SAVE))) { pick_map_lines(g, l1, l2); return 1u; }
    if (held & (1u << BTN_SAVE)) { a = "W SLOT 9/10SNP 11-15 PI 16SET"; b = "B SNAP SEL+B STORE 9CAP 10SND"; }   /* (0.30: the bank; the set, was JOURNEY;
                                                                    * 0.32: 11-15 the Pi's - EXPORT, the pattern, the progression, the setlist) */
    else if (held & (1u << BTN_FX)) { a = "W: FX  B: LOOPS RESTART STOP"; b = "B11 EXIT  SEL+K: THROWS"; }
    else if (held & (1u << BTN_SEL)) { a = "KEYS: STEP NOTE  OCT: OCTAVE"; b = "SEL+GLO: MOSSE  SEL+PLAY: GO"; }
    if (!a) return 0u;
    { char *p = put_s(l1, a); *p = 0; p = put_s(l2, b); *p = 0; }
    return 1u;
}

/* every pass: the map comes when a group has been held half a second; in a window (0.12: nothing really held) it stays
 * four seconds, then the key and the genre lines come back */
static void pick_tick(void)
{
    uint32_t held = eff_held() & ((1u << BTN_HOME) | (1u << BTN_GLO) | (1u << BTN_SEQ) | (1u << BTN_ARP) | (1u << BTN_EDIT) | (1u << BTN_ENV) | (1u << BTN_LFO) | (1u << BTN_FX) | (1u << BTN_SAVE) | (1u << BTN_SEL));
    if (held != group_held_last) { group_held_last = held; group_down_ms = fm1_ms; if (map_shown) { map_shown = 0u; ui_dirty = 1u; } }
    if (held && map_shown == 0u && (uint32_t)(fm1_ms - group_down_ms) >= 500u) { map_shown = 1u; ui_dirty = 1u; }
    if (map_shown == 1u && !(in_held() & GROUP_BTNS) && (uint32_t)(fm1_ms - group_down_ms) >= 4500u) { map_shown = 2u; ui_dirty = 1u; }
}
static uint8_t pick_map_due(void) { return map_shown == 1u; }

/* ---- the SEQ keys that hold a second meaning: UNDO / REDO, COOK / random COOK, KIT / BAND, DICE SEQ / DICE PROG,
 * 0.17 BEAT / a PROPOSAL (sagga_viaggio.c) */
static void beat_propose(void);
static uint8_t seqhold_key = 255u;               /* the key (0..26) down with SEQ, waiting */
static uint32_t seqhold_ms;
static uint8_t seqhold_done;
static uint8_t seqhold_is(int wi, int bi) { return (wi == TOOL_UNDO || wi == TOOL_COOK || wi == TOOL_BEAT || bi == 0 || bi == 6) ? 1u : 0u; }
static void seqhold_fire(uint32_t k, uint8_t held_long)
{
    int wi = key_is_in(white_key, 16u, k), bi = key_is_in(black_key, 11u, k);
    if (wi == TOOL_UNDO) { if (held_long) undo_redo(); else tool_apply(TOOL_UNDO); }
    else if (wi == TOOL_COOK) { if (held_long) { cook_random = 1u; tool_apply(TOOL_COOK); } else tool_apply(TOOL_COOK); }
    else if (wi == TOOL_BEAT) { if (held_long) beat_propose(); else tool_apply(TOOL_BEAT); }
    else if (bi == 0) { if (held_long) harm_dice(); else dice_roll(DICE_SEQ); }
    else if (bi == 6) { if (held_long) beat_band(); else beat_kit(); }
}
static void seqhold_down(uint32_t k)
{
    if (seqhold_key != 255u && seqhold_key != k && !seqhold_done) seqhold_fire(seqhold_key, 0u);   /* a second key: the first was a tap */
    seqhold_key = (uint8_t)k; seqhold_ms = fm1_ms; seqhold_done = 0u;
}
static void seqhold_up(uint32_t k)
{
    if (seqhold_key != k) return;
    if (!seqhold_done) seqhold_fire(k, 0u);
    seqhold_key = 255u;
}
static void seqhold_tick(void)
{
    if (seqhold_key == 255u || seqhold_done) return;
    if (!(eff_held() & (1u << BTN_SEQ))) {                                 /* SEQ let go a moment before the key: the tap still counts */
        uint32_t k = seqhold_key;
        seqhold_key = 255u;
        seqhold_fire(k, 0u);
        ui_dirty = grid_dirty = 1u;
        return;
    }
    if ((uint32_t)(fm1_ms - seqhold_ms) >= 600u) { seqhold_done = 1u; seqhold_fire(seqhold_key, 1u); ui_dirty = grid_dirty = 1u; }
}
