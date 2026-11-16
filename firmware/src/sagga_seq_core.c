/* SPDX-License-Identifier: GPL-3.0-only */
#include "sagga_seq_core.h"

static void tape_zero_tail(sq_project_t *p);   /* 0.11, below */

/* (no libc here: dinghy.c includes this file and the host tests compile it on its own) */
static void bcopy_(void *d, const void *s, uint32_t n)
{
    uint8_t *dp = (uint8_t *)d;
    const uint8_t *sp = (const uint8_t *)s;
    while (n--) *dp++ = *sp++;
}
static int bdiff_(const void *a, const void *b, uint32_t n)       /* 0 = equal */
{
    const uint8_t *ap = (const uint8_t *)a, *bp = (const uint8_t *)b;
    while (n--) if (*ap++ != *bp++) return 1;
    return 0;
}

uint32_t sq_rng_next(uint32_t *state)
{
    uint32_t x = *state;
    if (!x) x = 0xA341316Cu;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    return x;
}

uint32_t sq_hash3(uint32_t a, uint32_t b, uint32_t c)
{
    uint32_t h = a * 0x9E3779B1u ^ b * 0x85EBCA6Bu ^ c * 0xC2B2AE35u ^ 0x27D4EB2Fu;
    sq_rng_next(&h);
    return sq_rng_next(&h);
}

uint8_t sq_echo_ticks(uint8_t idx)
{
    static const uint8_t T[SQ_ECHO_TIMES] = {3u, 6u, 8u, 9u, 12u, 16u, 18u, 24u};   /* 1/32 1/16 1/8T 1/16. 1/8 1/4T 1/8. 1/4 */
    return T[idx < SQ_ECHO_TIMES ? idx : 6u];
}

uint8_t sq_div_ticks(uint8_t div)
{
    static const uint8_t T[SQ_DIV_COUNT] = {
        96u, /* 1/1 */
        48u, /* 1/2 */
        36u, /* 1/4 dotted */
        24u, /* 1/4 */
        18u, /* 1/8 dotted */
        16u, /* 1/4 triplet */
        12u, /* 1/8 */
         9u, /* 1/16 dotted */
         8u, /* 1/8 triplet */
         6u, /* 1/16 */
         4u, /* 1/16 triplet */
         3u, /* 1/32 */
         2u  /* 1/32 triplet */
    };
    return T[div < SQ_DIV_COUNT ? div : SQ_DIV_1_16];
}

uint8_t sq_condition_pass(uint8_t cond, uint32_t loop_count, uint8_t fill, uint8_t prev_hit)
{
    uint32_t n;
    switch (cond) {
    default:
    case SQ_COND_ALWAYS:   return 1u;
    case SQ_COND_1_2:      return (loop_count & 1u) == 0u;
    case SQ_COND_2_2:      return (loop_count & 1u) == 1u;
    case SQ_COND_1_4:      n = loop_count & 3u; return n == 0u;
    case SQ_COND_2_4:      n = loop_count & 3u; return n == 1u;
    case SQ_COND_3_4:      n = loop_count & 3u; return n == 2u;
    case SQ_COND_4_4:      n = loop_count & 3u; return n == 3u;
    case SQ_COND_FILL:     return fill ? 1u : 0u;
    case SQ_COND_NOT_FILL: return fill ? 0u : 1u;
    case SQ_COND_1_3:      return loop_count % 3u == 0u;
    case SQ_COND_2_3:      return loop_count % 3u == 1u;
    case SQ_COND_3_3:      return loop_count % 3u == 2u;
    case SQ_COND_1_8:      return (loop_count & 7u) == 0u;
    case SQ_COND_FIRST:    return loop_count == 0u;
    case SQ_COND_PRE:      return prev_hit ? 1u : 0u;
    case SQ_COND_NOT_PRE:  return prev_hit ? 0u : 1u;
    }
}

const char *sq_cond_name(uint8_t c)
{
    static const char *const N[SQ_COND_COUNT] = {"ALL", "1:2", "2:2", "1:4", "2:4", "3:4", "4:4", "FILL", "!FILL",
                                                 "1:3", "2:3", "3:3", "1:8", "FIRST", "PRE", "!PRE"};
    return N[c < SQ_COND_COUNT ? c : 0u];
}

uint8_t sq_step_should_play(const sq_step_t *s, uint32_t loop_count, uint8_t fill, uint8_t prev_hit, uint32_t *rng)
{
    uint32_t r;
    if (!(s->flags & SQ_STEP_ON)) return 0u;
    if (!sq_condition_pass(s->condition, loop_count, fill, prev_hit)) return 0u;
    if (s->chance >= 100u) return 1u;
    if (!s->chance) return 0u;
    r = sq_rng_next(rng) % 100u;
    return r < s->chance;
}

uint8_t sq_advance_step(const sq_track_cfg_t *cfg, sq_track_rt_t *rt, uint32_t *rng)
{
    uint8_t len = cfg->length ? cfg->length : 1u;
    uint8_t lo = cfg->start < len ? cfg->start : 0u;       /* the loop is lo .. len-1 */
    uint8_t span = (uint8_t)(len - lo);
    uint8_t wrapped = 0u;

    if (rt->step < lo || rt->step >= len) {                 /* 0.10: outside the loop (it was just shortened): a wrap, not a skip */
        rt->step = cfg->direction == SQ_DIR_REV ? (uint8_t)(len - 1u) : lo;
        rt->ping_dir = 1;
        rt->loop_count++;
        sq_plane_advance(cfg, rt);
        return 1u;
    }

    switch (cfg->direction) {
    default:
    case SQ_DIR_FWD:
        rt->step++;
        if (rt->step >= len) { rt->step = lo; wrapped = 1u; }
        break;

    case SQ_DIR_REV:
        if (rt->step <= lo) { rt->step = (uint8_t)(len - 1u); wrapped = 1u; }
        else rt->step--;
        break;

    case SQ_DIR_PINGPONG:
        if (span <= 1u) { rt->step = lo; wrapped = 1u; break; }
        if (rt->ping_dir >= 0) {
            if (rt->step + 1u >= len) { rt->ping_dir = -1; rt->step = (uint8_t)(len - 2u); wrapped = 1u; }
            else rt->step++;
        } else {
            if (rt->step <= lo) { rt->ping_dir = 1; rt->step = (uint8_t)(lo + 1u); wrapped = 1u; }
            else rt->step--;
        }
        break;

    case SQ_DIR_RANDOM:
        rt->step = (uint8_t)(lo + sq_rng_next(rng) % span);
        if (++rt->advances >= span) { rt->advances = 0u; wrapped = 1u; }
        break;
    }

    if (wrapped) rt->loop_count++;
    sq_plane_advance(cfg, rt);
    return wrapped;
}

/* 0.10: the closed form of the loop. After `ticks` ticks from the tick its first step played on, `steps` steps have
 * begun (ceil(ticks / div)); the track is on the steps-th one of its loop. The same arithmetic the engine's counters
 * make, so a track realigned mid-flight lands exactly where it would have been. */
void sq_track_seek(const sq_track_cfg_t *c, sq_track_rt_t *rt, uint32_t ticks, uint32_t div)
{
    uint8_t len = c->length ? c->length : 1u, lo = c->start < len ? c->start : 0u;
    uint32_t span = (uint32_t)(len - lo), steps, k;
    if (!div) div = 1u;
    steps = (ticks + div - 1u) / div;
    k = steps % span;
    rt->div_accum = (uint16_t)((ticks + div - 1u) % div);
    rt->loop_count = steps / span;
    rt->ping_dir = 1;
    rt->advances = 0u;
    switch (c->direction) {
    case SQ_DIR_REV:      rt->step = (uint8_t)(len - 1u - k); break;
    case SQ_DIR_PINGPONG:
        if (span > 1u) {
            uint32_t period = 2u * (span - 1u), m = steps % period;
            rt->step = (uint8_t)(lo + (m < span ? m : period - m));
            rt->ping_dir = (m < span && !(m == 0u && steps)) ? 1 : -1;   /* (back at the first step it is still coming down) */
            rt->loop_count = steps / period;
        } else rt->step = lo;
        break;
    case SQ_DIR_RANDOM:                                      /* (no closed form: it keeps its step, in the loop) */
        if (rt->step < lo || rt->step >= len) rt->step = lo;
        rt->advances = (uint8_t)k;
        break;
    default:              rt->step = (uint8_t)(lo + k); break;
    }
    sq_plane_seek(c, rt, steps);
}

/* ------------------------------------------------------------------ lengths per parameter */

uint8_t sq_plane_len(const sq_track_cfg_t *c, uint8_t k)
{
    uint8_t l, room;
    if (k >= SQ_PLANES || !c->plen[k]) return 0u;
    room = (uint8_t)(c->start < SQ_STEPS ? SQ_STEPS - c->start : 1u);
    l = c->plen[k] > room ? room : c->plen[k];
    return l ? l : 1u;
}

uint8_t sq_plane_step(const sq_track_cfg_t *c, const sq_track_rt_t *rt, uint8_t k, uint8_t step)
{
    uint8_t l = sq_plane_len(c, k);
    if (!l) return step;
    return (uint8_t)(c->start + rt->ppos[k] % l);
}

void sq_plane_advance(const sq_track_cfg_t *c, sq_track_rt_t *rt)
{
    uint8_t k;
    for (k = 0; k < SQ_PLANES; k++) {
        uint8_t l = sq_plane_len(c, k);
        rt->ppos[k] = l ? (uint8_t)((rt->ppos[k] % l + 1u) % l) : 0u;
    }
}

void sq_plane_seek(const sq_track_cfg_t *c, sq_track_rt_t *rt, uint32_t steps)
{
    uint8_t k;
    for (k = 0; k < SQ_PLANES; k++) {
        uint8_t l = sq_plane_len(c, k);
        rt->ppos[k] = l ? (uint8_t)(steps % l) : 0u;
    }
}

void sq_plane_compose(const sq_track_cfg_t *c, const sq_track_rt_t *rt, const sq_step_t *row, uint8_t step, sq_step_t *out)
{
    uint32_t n;
    const sq_step_t *ns = &row[sq_plane_step(c, rt, SQ_PL_NOTE, step)];
    *out = row[step];
    for (n = 0; n < SQ_POLY; n++) out->note[n] = ns->note[n];
    out->velocity = row[sq_plane_step(c, rt, SQ_PL_VEL, step)].velocity;
    out->length = row[sq_plane_step(c, rt, SQ_PL_GATE, step)].length;
}

/* ------------------------------------------------------------------ defaults */

void sq_step_default(sq_step_t *st)
{
    uint32_t n;
    for (n = 0; n < SQ_POLY; n++) st->note[n] = SQ_NOTE_NONE;
    st->note[0] = 60u;
    st->velocity = 100u;
    st->length = 80u;
    st->chance = 100u;
    st->ratchet = 1u;
    st->condition = SQ_COND_ALWAYS;
    st->flags = 0u;
    for (n = 0; n < SQ_LANES; n++) st->lane[n] = SQ_LANE_NONE;
    st->nudge = 0;
    st->ramp = 0;
}

void sq_track_default(sq_track_cfg_t *c, uint32_t index)
{
    static const uint8_t CC[SQ_LANES] = {74u, 71u, 1u, 11u, 7u, 10u};   /* cutoff, resonance, mod wheel, expression, volume, pan */
    uint32_t n;
    c->channel = (uint8_t)(index % SQ_MIDI_CH);
    c->length = 16u;
    c->start = 0u;
    c->division = SQ_DIV_1_16;
    c->direction = SQ_DIR_FWD;
    c->transpose = 0;
    c->initial_pattern = 0u;
    c->chord_mode = SQ_CHORD_BLOCK;
    c->swing = SQ_SWING_MIN;
    c->vel_offset = 0;
    c->hum_time = 0u;
    c->hum_vel = 0u;
    for (n = 0; n < SQ_LANES; n++) { c->lane_cc[n] = CC[n]; c->lane_base[n] = SQ_LANE_NONE; c->lane_flags[n] = 0u; c->lane_hi[n] = 0u; }
    c->flags = 0u;
    for (n = 0; n < SQ_PLANES; n++) c->plen[n] = 0u;
    c->voicing = SQ_VOICE_CLOSE;
    c->strum = 0;
    c->mfx = SQ_MFX_OFF;
    c->mfx_amt = 0;
    c->mfx_time = 6u;              /* ECHO: a dotted eighth */
    c->mfx_fb = 60u;
    c->euc_pulses = 4u;
    c->euc_rot = 0u;
    sq_algo_default(c, SQ_ALGO_OFF);
    for (n = 0; n < SQ_ALGO_SLOTS - 1u; n++) sq_algo_slot_default(&c->algo2[n], SQ_ALGO_OFF);   /* 0.11 */
    c->brk_chop = 0u; c->brk_cfg = SQ_BRK_DEFAULT;   /* 0.12 */
    c->pen = 60u;
    c->role = SQ_ROLE_NONE;
    c->chord = SQ_CH_OFF;
    c->chord_key = SQ_CK_DIATONIC;
    c->octave = 0;
    c->key_slot = SQ_KEY_FOLLOW;
    c->src_func = c->src_var = 255u;
    c->src_genre = 255u;
    c->follow_mode = SQ_FM_HOLD;
    c->euc_fam = SQ_RF_EUCLID;
    c->arp_rate = 0u;
    c->arp_flags = 0u;
    c->delay_ms = 0;
    sq_expo_default(&c->expo);
    sq_tape_cfg_default(&c->tape);
}

void sq_key_default(sq_key_t *k) { k->root = 0u; k->scale = SQ_SC_CHROMATIC; k->shift = 0; k->reserved = 0u; }

void sq_uprog_tail_default(sq_uprog_t *u)
{
    uint32_t i;
    for (i = 0; i < 8u; i++) { u->semi[i] = 255u; u->shape[i] = SQ_HC_TRIAD; u->dur[i] = 0u; u->push[i] = 0u; }
    u->mood = SQ_MOOD_ANY; u->reserved = 0u;
}
void sq_uprog_default(sq_uprog_t *u)
{
    uint32_t i;
    u->n = 0u; u->bars = 1u;
    for (i = 0; i < 8u; i++) { u->deg[i] = 0; u->col[i] = SQ_HC_TRIAD; }
    sq_uprog_tail_default(u);
}
void sq_uprog_sanitize(sq_uprog_t *u)
{
    uint32_t i;
    if (u->n > 8u) u->n = 0u;
    if (u->bars < 1u || u->bars > 8u) u->bars = 1u;
    for (i = 0; i < 8u; i++) {
        if (u->deg[i] < 0 || u->deg[i] > 6) u->deg[i] = 0;
        if (u->col[i] >= SQ_HCS) u->col[i] = SQ_HC_TRIAD;
        if (u->semi[i] > 11u) u->semi[i] = 255u;                  /* 0.11 */
        if (u->shape[i] >= SQ_HSHAPES) u->shape[i] = SQ_HC_TRIAD;             /* (5: the colour 6; 6.. the shapes OCT ..) */
        if (u->dur[i] > 64u) u->dur[i] = 0u;
        if (u->push[i] > 4u) u->push[i] = 0u;
    }
    if (u->mood >= SQ_MOODS) u->mood = SQ_MOOD_ANY;
    u->reserved = 0u;
}
uint8_t sq_uprog_at(const sq_uprog_t *u, uint32_t bar, uint8_t bars_override, int8_t *deg, uint8_t *col)
{
    uint32_t bpc = bars_override ? bars_override : (u->bars ? u->bars : 1u), k = u->n ? (bar / bpc) % u->n : 0u;
    *deg = u->n ? u->deg[k] : 0;
    *col = u->n ? u->col[k] : (uint8_t)SQ_HC_TRIAD;
    return (uint8_t)k;
}
void sq_uprog_name(const sq_uprog_t *u, uint8_t scale, char *out, uint32_t cap)
{
    uint32_t k = 0u, c;
    char b[12];
    if (!u->n) { if (cap > 2u) { out[0] = '-'; out[1] = '-'; out[2] = 0; } else if (cap) out[0] = 0; return; }
    for (c = 0; c < u->n; c++) {
        const char *q = b;
        sq_hchord_t hc;
        hc.deg = u->deg[c]; hc.col = u->col[c]; hc.semi = u->semi[c]; hc.shape = u->shape[c];
        sq_hchord_name(scale, &hc, b);                       /* (0.11: a root and a shape too) */
        if (c && k + 1u < cap) out[k++] = '-';
        while (*q && k + 1u < cap) out[k++] = *q++;
    }
    out[k] = 0;
}

void sq_algo_default(sq_track_cfg_t *c, uint8_t algo)
{
    static const uint8_t D[SQ_ALGOS][3] = {
        {0u, 0u, 0u},              /* OFF */
        {10u, 8u, SQ_TM_RHYTHM},   /* TURING: 10 % mutation, 8 steps, the rhythm */
        {90u, 16u, 0u},            /* CELL: rule 90, 16 cells, a generation a bar */
        {0u, 32u, 0u},             /* ACCENT: on the beat, half way */
        {100u, 40u, 0u},           /* DENSITY: as written, ghosts at 40 % */
    };
    if (algo >= SQ_ALGOS) algo = SQ_ALGO_OFF;
    c->algo = algo;
    c->algo_a = D[algo][0];
    c->algo_b = D[algo][1];
    c->algo_c = D[algo][2];
}
void sq_algo_slot_default(sq_algo_t *s, uint8_t algo)
{
    sq_track_cfg_t c;
    sq_algo_default(&c, algo);
    s->algo = c.algo; s->a = c.algo_a; s->b = c.algo_b; s->c = c.algo_c;
}
uint8_t sq_track_algo_any(const sq_track_cfg_t *c, uint8_t algo)
{
    uint32_t k;
    for (k = 0; k < SQ_ALGO_SLOTS; k++) if (SQ_ALGO_AT((sq_track_cfg_t *)c, k)->algo == algo) return 1u;
    return 0u;
}

void sq_live_default(sq_live_t *l)
{
    uint32_t i;
    l->quant = SQ_Q_AUTO;
    l->mute_q = 0u;
    l->morph_b = 1u;
    l->remote_ch = 13u;            /* MIDI channel 14 */
    l->master_fn = SQ_MK_TEMPO;
    l->ktrans = 0;
    l->snap_tempo = 0u;
    l->remote_mode = SQ_RM_14;
    l->mute_lo = l->mute_hi = 0u;
    l->scene_cursor = 0u;
    for (i = 0; i < 4u; i++) l->mac[i] = 0;
    l->cc_lead_ms = 0u;
    l->song_tempo = 0u;
    for (i = 0; i < sizeof l->reserved; i++) l->reserved[i] = 0u;
}

static void scene_default(sq_scene_t *sc)
{
    uint32_t t, n;
    sc->mute_mask = 0u;
    for (t = 0; t < SQ_TRACKS; t++) {
        sc->pattern[t] = 0u;
        for (n = 0; n < SQ_LANES; n++) sc->lane[t][n] = SQ_LANE_NONE;
    }
    for (n = 0; n < SQ_CHANNELS; n++) sc->pc[n] = SQ_PC_NONE;
    sc->key_slot = SQ_KEY_FOLLOW;
}

void sq_lfo_default(sq_lfo_t *l)
{
    l->enabled = 0u;
    l->shape = SQ_LFO_SINE;
    l->rate = 6u;                  /* one bar */
    l->depth = 64u;
    l->center = 64u;
    l->phase = 0u;
    l->dest = SQ_LD_CC;
    l->target = 0u;
    l->param = 74u;
    l->flags = 0u;
}

void sq_gen_default(sq_gen_t *g)
{
    uint32_t i;
    g->genre = 0u; g->func = 0u; g->var = 0u;
    g->scope = SQ_SCOPE_THIS;
    g->targets = SQ_GT_RHYTHM;
    g->density = 50u; g->heat = 40u;
    g->evo_amount = 25u; g->evo_every = 2u; g->evo_drift = 0u;
    g->harm_on = 0u; g->genre_mode = SQ_GM_ON; g->harm_prog = 0u; g->harm_bars = 0u;
    g->custom = 0u;
    g->panel_lights = 0u;
    g->when = SQ_WHEN_NOW; g->every = SQ_EVERY_OFF; g->every_tool = 255u; g->lib_len = SQ_LL_16;
    g->harm_genre = 0u; g->harm_lock = 0u; g->harm_free = 0u;
    g->harm_rhythm = SQ_HR_BARS; g->harm_mood = SQ_MOOD_ANY;               /* 0.11 */
    for (i = 0; i < sizeof g->reserved11; i++) g->reserved11[i] = 0u;
}

static void snap_default(sq_snap_t *sn)
{
    uint8_t *b = (uint8_t *)sn;
    uint32_t i;
    for (i = 0; i < sizeof *sn; i++) b[i] = 0u;
}

static void song_default(sq_song_t *sg)
{
    uint32_t i;
    sg->len = 0u;
    sg->loop = 1u;
    for (i = 0; i < SQ_SONG_LEN; i++) { sg->e[i].scene = 0u; sg->e[i].bars = 4u; sg->e[i].bpm = 0u; }
}

void sq_project_init(sq_project_t *p)
{
    uint32_t t, pat, s;
    p->bpm = 128u;
    p->clock_mode = SQ_CLOCK_MASTER;
    p->key_root = 0u;
    p->key_scale = SQ_SC_CHROMATIC;
    p->key_shift = 0;
    p->key_cur = 0u;
    p->reserved0 = 0u;
    for (s = 0; s < SQ_KEYS; s++) sq_key_default(&p->key[s]);
    for (s = 0; s < SQ_CHANNELS; s++) p->device[s] = SQ_DEV_GENERIC;
    for (s = 0; s < SQ_UPROG_SLOTS; s++) sq_uprog_default(&p->uprog[s]);

    for (t = 0; t < SQ_TRACKS; t++) sq_track_default(&p->track[t], t);

    for (s = 0; s < SQ_SCENES; s++) scene_default(&p->scene[s]);
    for (s = 0; s < SQ_LFOS; s++) sq_lfo_default(&p->lfo[s]);
    sq_gen_default(&p->gen);
    song_default(&p->song);
    sq_live_default(&p->live);
    for (s = 0; s < SQ_SNAPS; s++) snap_default(&p->snap[s]);
    sq_viaggio_default(&p->viaggio);
    sq_ext_default(&p->ext);
    sq_theory_default(&p->th);
    for (t = 0; t < SQ_TRACKS; t++) p->tape_cnt[t] = 0u;
    p->tape_n = 0u;
    p->tape_reserved = 0u;
    p->reserved_end = 0u;
    tape_zero_tail(p);
    p->id = 0u;

    for (t = 0; t < SQ_TRACKS; t++)
        for (pat = 0; pat < SQ_PATTERNS; pat++)
            for (s = 0; s < SQ_STEPS; s++)
                sq_step_default(&p->step[t][pat][s]);
}

static int32_t clampi(int32_t v, int32_t lo, int32_t hi) { return v < lo ? lo : v > hi ? hi : v; }
static uint32_t pct(uint32_t *rng) { return sq_rng_next(rng) % 100u; }
static int in_scale(int32_t note, uint8_t root, uint16_t mask);

static void sanitize_step(sq_step_t *s)
{
    uint32_t n;
    for (n = 0; n < SQ_POLY; n++) if (s->note[n] > 127u) s->note[n] = SQ_NOTE_NONE;
    s->velocity = (uint8_t)clampi(s->velocity, 1, 127);
    s->length = sq_gate_sanitize(s->length);
    if (s->chance > 100u) s->chance = 100u;
    s->ratchet = (uint8_t)clampi(s->ratchet, 1, (int32_t)SQ_RATCHET_MAX);
    if (s->condition >= SQ_COND_COUNT) s->condition = SQ_COND_ALWAYS;
    s->flags &= (uint8_t)SQ_STEP_FLAGS;
    for (n = 0; n < SQ_LANES; n++) if (s->lane[n] > 127u) s->lane[n] = SQ_LANE_NONE;
    s->nudge = (int8_t)clampi(s->nudge, -(int32_t)SQ_NUDGE_MAX, (int32_t)SQ_NUDGE_MAX);
    s->ramp = (int8_t)clampi(s->ramp, -100, 100);
}

static void sanitize_algo(sq_algo_t *s)
{
    if (s->algo >= SQ_ALGOS) sq_algo_slot_default(s, SQ_ALGO_OFF);
    switch (s->algo) {
    case SQ_ALGO_TURING:
        if (s->a > 100u) s->a = 100u;
        s->b = (uint8_t)clampi(s->b, 2, 16);
        if (s->c >= SQ_TM_MODES) s->c = SQ_TM_RHYTHM;
        break;
    case SQ_ALGO_CELL:
        s->b = (uint8_t)clampi(s->b, 4, 64);
        if (s->c > 3u) s->c = 0u;
        break;
    case SQ_ALGO_ACCENT:
        if (s->a > 4u) s->a = 0u;
        if (s->b > 63u) s->b = 63u;
        if (s->c > 15u) s->c = 0u;
        break;
    case SQ_ALGO_DENSITY:
        if (s->a > 200u) s->a = 200u;
        s->b = (uint8_t)clampi(s->b, 10, 100);
        s->c = 0u;
        break;
    default:
        s->a = s->b = s->c = 0u;
        break;
    }
}

void sq_track_sanitize(sq_track_cfg_t *c)
{
    uint32_t n;
    if (c->channel >= SQ_CHANNELS) c->channel = (uint8_t)(SQ_MIDI_CH - 1u);
    if (c->length < 1u || c->length > SQ_STEPS) c->length = 16u;
    if (c->start >= c->length) c->start = 0u;
    if (c->division >= SQ_DIV_COUNT) c->division = SQ_DIV_1_16;
    if (c->direction >= SQ_DIR_COUNT) c->direction = SQ_DIR_FWD;
    c->transpose = (int8_t)clampi(c->transpose, (c->flags & SQ_TF_SCALE) ? -24 : -48, (c->flags & SQ_TF_SCALE) ? 24 : 48);
    if (c->initial_pattern >= SQ_PATTERNS) c->initial_pattern = 0u;
    if (SQ_CHORD_MODE(c->chord_mode) >= SQ_CHORD_COUNT) c->chord_mode = SQ_CHORD_BLOCK;
    if (SQ_CHORD_OCTS(c->chord_mode) > 3u) c->chord_mode = SQ_CHORD_PACK(SQ_CHORD_MODE(c->chord_mode), 3u);
    if (c->swing < SQ_SWING_MIN || c->swing > SQ_SWING_MAX) c->swing = SQ_SWING_MIN;
    c->vel_offset = (int8_t)clampi(c->vel_offset, -63, 63);
    if (c->hum_time > SQ_NUDGE_MAX) c->hum_time = SQ_NUDGE_MAX;
    if (c->hum_vel > 50u) c->hum_vel = 50u;
    c->flags &= (uint8_t)SQ_TF_MASK;
    if (c->flags & SQ_TF_DRUM) c->flags &= (uint8_t)~(SQ_TF_SCALE | SQ_TF_FOLLOW);   /* a drum never follows the key */
    if (c->flags & SQ_TF_BREAK) c->flags &= (uint8_t)~(SQ_TF_SCALE | SQ_TF_FOLLOW | SQ_TF_DRUM | SQ_TF_TAPE);   /* 0.12: a break neither */
    for (n = 0; n < SQ_LANES; n++) {
        if (c->lane_cc[n] > SQ_CC_MAX) c->lane_cc[n] = SQ_LANE_NONE;
        if (c->lane_base[n] > 127u) c->lane_base[n] = SQ_LANE_NONE;
        c->lane_flags[n] &= (uint8_t)(SQ_LF_SLIDE | SQ_LF_TRIGLESS | SQ_LF_NRPN);
        if (c->lane_hi[n] > 127u) c->lane_hi[n] = 0u;
    }
    if (c->role >= SQ_ROLE_COUNT) c->role = SQ_ROLE_NONE;
    if (c->chord >= SQ_CH_COUNT) c->chord = SQ_CH_OFF;
    if (c->chord_key >= SQ_CK_COUNT) c->chord_key = SQ_CK_DIATONIC;
    c->octave = (int8_t)clampi(c->octave, -3, 3);
    if (c->key_slot >= SQ_KEYS && c->key_slot != SQ_KEY_FOLLOW) c->key_slot = SQ_KEY_FOLLOW;
    if (c->src_func >= 64u && c->src_func != 255u) c->src_func = 255u;   /* (the library checks the rest) */
    if (c->src_genre >= 64u) c->src_genre = 255u;
    if (c->follow_mode >= SQ_FMS) c->follow_mode = SQ_FM_HOLD;
    if (c->euc_fam >= SQ_RF_COUNT) c->euc_fam = SQ_RF_EUCLID;
    if (c->arp_rate > SQ_ARP_RATE_MAX) c->arp_rate = 0u;
    c->arp_flags &= (uint8_t)(SQ_AF_HOLD | SQ_AF_RETRIG);
    c->delay_ms = (int8_t)clampi(c->delay_ms, -SQ_DELAY_MAX, SQ_DELAY_MAX);
    sq_expo_sanitize(&c->expo);
    if (c->tape.bars < 1u || c->tape.bars > SQ_TAPE_BARS_MAX) c->tape.bars = 4u;
    if (c->tape.quant > 100u) c->tape.quant = 100u;
    c->tape.flags = 0u; c->tape.reserved = 0u;
    for (n = 0; n < SQ_PLANES; n++) if (c->plen[n] > SQ_STEPS) c->plen[n] = 0u;
    if (c->voicing >= SQ_VOICES) c->voicing = SQ_VOICE_CLOSE;
    c->strum = (int8_t)clampi(c->strum, -50, 50);
    if (c->mfx >= SQ_MFXS_019) c->mfx = SQ_MFX_OFF;   /* (the track's own effect is one of the four: 0.18 reads it) */
    switch (c->mfx) {                                  /* each effect its own range */
    case SQ_MFX_HARM:     c->mfx_amt = (int8_t)clampi(c->mfx_amt, -12, 12); break;
    case SQ_MFX_OCTAVE:   c->mfx_amt = (int8_t)clampi(c->mfx_amt, -2, 2); break;
    case SQ_MFX_ECHO:     c->mfx_amt = (int8_t)clampi(c->mfx_amt, 0, 4); break;
    case SQ_MFX_VELOCITY: c->mfx_amt = (int8_t)clampi(c->mfx_amt, -8, 8); break;
    default:              c->mfx_amt = (int8_t)clampi(c->mfx_amt, -12, 12); break;
    }
    if (c->mfx_time >= SQ_ECHO_TIMES) c->mfx_time = 6u;
    c->mfx_fb = (uint8_t)clampi(c->mfx_fb, 10, 100);
    c->euc_pulses = (uint8_t)clampi(c->euc_pulses, 1, SQ_STEPS);
    if (c->euc_rot >= SQ_STEPS) c->euc_rot = 0u;
    for (n = 0; n < SQ_ALGO_SLOTS; n++) sanitize_algo(SQ_ALGO_AT(c, n));   /* 0.11: every slot */
    if (c->brk_chop >= SQ_BRK_CHOPS) c->brk_chop = 0u;                    /* 0.12 */
    if (!c->brk_cfg) c->brk_cfg = SQ_BRK_DEFAULT;                            /* (a 0.11 image has 0 there: the default) */
    if (c->pen > 127u) c->pen = 60u;
}

static void sanitize_lfo(sq_lfo_t *l)
{
    l->enabled = l->enabled ? 1u : 0u;
    if (l->shape >= SQ_LFO_SHAPES) l->shape = SQ_LFO_SINE;
    if (l->rate >= SQ_LFO_RATES) l->rate = 6u;
    if (l->depth > 127u) l->depth = 127u;
    if (l->center > 127u) l->center = 127u;
    if (l->phase > 127u) l->phase = 127u;
    if (l->dest >= SQ_LD_ALL) l->dest = SQ_LD_CC;
    if (l->target >= (l->dest == SQ_LD_CC ? SQ_CHANNELS : SQ_TRACKS)) l->target = 0u;
    if (l->param > SQ_CC_MAX) l->param = SQ_CC_MAX;
    l->flags &= (uint8_t)(SQ_LF_RETRIG | SQ_LF_INVERT);
}

static void sanitize_snap(sq_snap_t *sn)
{
    uint32_t i;
    if (!sn->used) { snap_default(sn); return; }
    sn->used = 1u;
    if (sn->ccn > SQ_SNAP_CC) sn->ccn = 0u;
    if (sn->bpm < 30u || sn->bpm > 300u) sn->bpm = 128u;
    if (sn->key_root > 11u) sn->key_root = 0u;
    if (sn->key_scale >= SQ_SCALES) sn->key_scale = SQ_SC_CHROMATIC;
    sn->key_shift = (int8_t)clampi(sn->key_shift, -24, 24);
    sn->ktrans = (int8_t)clampi(sn->ktrans, -SQ_KTRANS_MAX, SQ_KTRANS_MAX);
    for (i = 0; i < SQ_TRACKS; i++) if (sn->pattern[i] >= SQ_PATTERNS) sn->pattern[i] = 0u;
    sn->mac[0] = (int8_t)clampi(sn->mac[0], -63, 63);
    sn->mac[1] = (int8_t)clampi(sn->mac[1], -90, 100);
    sn->mac[2] = (int8_t)clampi(sn->mac[2], -25, 25);
    sn->mac[3] = (int8_t)clampi(sn->mac[3], -64, 63);
    sn->harm_on = sn->harm_on ? 1u : 0u;
    if (sn->genre >= 64u) sn->genre = 0u;             /* (the library checks the genre itself) */
    if (sn->harm_prog >= SQ_PROGS_ALL) sn->harm_prog = 0u;
    if (sn->harm_bars > 8u) sn->harm_bars = 0u;
    if (sn->morph_b >= SQ_SCENES) sn->morph_b = 1u;
    if (sn->key_cur >= SQ_KEYS) sn->key_cur = 0u;
    if (sn->harm_genre >= 64u) sn->harm_genre = sn->genre;
    sn->reserved[0] = 0u;
    for (i = 0; i < SQ_TRACKS; i++) sq_track_sanitize(&sn->track[i]);
    for (i = 0; i < SQ_LFOS; i++) sanitize_lfo(&sn->lfo[i]);
    for (i = 0; i < SQ_SNAP_CC; i++) {
        sq_ccv_t *e = &sn->cc[i];
        if (i >= sn->ccn) { e->ch = e->cc = e->val = 0u; continue; }
        e->ch &= 15u; e->cc &= 127u; e->val &= 127u;
    }
}

void sq_project_sanitize(sq_project_t *p)
{
    uint32_t t, n, pat, i;
    if (p->bpm < 30u || p->bpm > 300u) p->bpm = 128u;
    if (p->clock_mode > SQ_CLOCK_SLAVE) p->clock_mode = SQ_CLOCK_MASTER;
    if (p->key_root > 11u) p->key_root = 0u;
    if (p->key_scale >= SQ_SCALES) p->key_scale = SQ_SC_CHROMATIC;
    p->key_shift = (int8_t)clampi(p->key_shift, -24, 24);
    if (p->key_cur >= SQ_KEYS) p->key_cur = 0u;
    p->reserved0 = 0u;
    for (n = 0; n < SQ_KEYS; n++) {
        sq_key_t *k = &p->key[n];
        if (k->root > 11u) k->root = 0u;
        if (k->scale >= SQ_SCALES) k->scale = SQ_SC_CHROMATIC;
        k->shift = (int8_t)clampi(k->shift, -24, 24);
        k->reserved = 0u;
    }
    p->key[p->key_cur].root = p->key_root;             /* the key that plays is its slot */
    p->key[p->key_cur].scale = p->key_scale;
    p->key[p->key_cur].shift = p->key_shift;
    for (n = 0; n < SQ_CHANNELS; n++) if (p->device[n] >= SQ_DEV_COUNT) p->device[n] = SQ_DEV_GENERIC;
    for (n = 0; n < SQ_UPROG_SLOTS; n++) sq_uprog_sanitize(&p->uprog[n]);
    for (t = 0; t < SQ_TRACKS; t++) sq_track_sanitize(&p->track[t]);
    for (n = 0; n < SQ_SCENES; n++) {
        sq_scene_t *sc = &p->scene[n];
        for (t = 0; t < SQ_TRACKS; t++) {
            if (sc->pattern[t] >= SQ_PATTERNS) sc->pattern[t] = 0u;
            for (i = 0; i < SQ_LANES; i++) if (sc->lane[t][i] > 127u) sc->lane[t][i] = SQ_LANE_NONE;
        }
        for (i = 0; i < SQ_CHANNELS; i++) if (sc->pc[i] > 127u) sc->pc[i] = SQ_PC_NONE;
        if (sc->key_slot >= SQ_KEYS && sc->key_slot != SQ_KEY_FOLLOW) sc->key_slot = SQ_KEY_FOLLOW;
    }
    if (p->live.quant >= SQ_QUANTS) p->live.quant = SQ_Q_AUTO;
    p->live.mute_q = p->live.mute_q ? 1u : 0u;
    if (p->live.morph_b >= SQ_SCENES) p->live.morph_b = 1u;
    if (p->live.remote_ch >= SQ_CHANNELS && p->live.remote_ch != SQ_REMOTE_OFF) p->live.remote_ch = 13u;
    if (p->live.master_fn >= SQ_MKS) p->live.master_fn = SQ_MK_TEMPO;
    p->live.ktrans = (int8_t)clampi(p->live.ktrans, -SQ_KTRANS_MAX, SQ_KTRANS_MAX);
    p->live.snap_tempo = p->live.snap_tempo ? 1u : 0u;
    if (p->live.remote_mode >= SQ_RMS) p->live.remote_mode = p->live.remote_ch == SQ_REMOTE_OFF ? SQ_RM_OFF : SQ_RM_14;
    if (p->live.scene_cursor >= SQ_SCENES) p->live.scene_cursor = 0u;
    p->live.mac[0] = (int8_t)clampi(p->live.mac[0], -63, 63);
    p->live.mac[1] = (int8_t)clampi(p->live.mac[1], -90, 100);
    p->live.mac[2] = (int8_t)clampi(p->live.mac[2], -25, 25);
    p->live.mac[3] = (int8_t)clampi(p->live.mac[3], -64, 63);
    if (p->live.cc_lead_ms > SQ_CC_LEAD_MAX) p->live.cc_lead_ms = SQ_CC_LEAD_MAX;
    p->live.song_tempo = p->live.song_tempo ? 1u : 0u;
    for (n = 0; n < sizeof p->live.reserved; n++) p->live.reserved[n] = 0u;
    sq_viaggio_sanitize(&p->viaggio);
    sq_ext_sanitize(&p->ext);
    sq_theory_sanitize(&p->th);
    for (t = 0; t < SQ_TRACKS; t++) sq_mfx_mirror(&p->ext.mfxc[t], &p->track[t]);   /* 0.19: the track shows its chain's first */
    sq_tape_sanitize(p);
    for (n = 0; n < SQ_LFOS; n++) sanitize_lfo(&p->lfo[n]);
    {
        sq_gen_t *g = &p->gen;
        if (g->genre >= 64u) g->genre = 0u;            /* (the library checks the genre itself) */
        if (g->func >= 16u) g->func = 0u;
        if (g->var >= 16u) g->var = 0u;
        if (g->scope >= SQ_SCOPES) g->scope = SQ_SCOPE_THIS;
        g->targets = (uint8_t)((g->targets & (SQ_GT_NOTES | SQ_GT_CC | SQ_GT_LFO)) | SQ_GT_RHYTHM);
        if (g->density > 100u) g->density = 100u;
        g->heat = (uint8_t)clampi(g->heat, 1, 100);
        g->evo_amount = (uint8_t)clampi(g->evo_amount, 1, 100);
        if (g->evo_every >= SQ_EVO_EVERY) g->evo_every = 2u;
        g->evo_drift = g->evo_drift ? 1u : 0u;
        g->harm_on = g->harm_on ? 1u : 0u;
        if (g->genre_mode >= SQ_GMS) g->genre_mode = SQ_GM_ON;
        if (g->harm_prog >= SQ_PROGS_ALL) g->harm_prog = 0u;
        if (g->harm_bars > 8u) g->harm_bars = 0u;
        if (g->panel_lights > 5u) g->panel_lights = 0u;
        if (g->when >= SQ_WHENS) g->when = SQ_WHEN_NOW;
        if (g->every >= SQ_EVERYS) g->every = SQ_EVERY_OFF;
        if (g->every_tool >= 16u && g->every_tool != 255u) g->every_tool = 255u;
        if (g->lib_len >= SQ_LLS) g->lib_len = SQ_LL_16;
        if (g->harm_genre >= 64u) g->harm_genre = g->genre;
        g->harm_lock = g->harm_lock ? 1u : 0u;
        g->harm_free = g->harm_free ? 1u : 0u;      /* (0.16; a 0.15 image: 0) */
        if (g->harm_rhythm >= SQ_HRS) g->harm_rhythm = SQ_HR_BARS;
        if (g->harm_mood >= SQ_MOODS) g->harm_mood = SQ_MOOD_ANY;
        for (n = 0; n < sizeof g->reserved11; n++) g->reserved11[n] = 0u;
    }
    if (p->song.len > SQ_SONG_LEN) p->song.len = 0u;
    p->song.loop = p->song.loop ? 1u : 0u;
    for (n = 0; n < SQ_SONG_LEN; n++) {
        if (p->song.e[n].scene >= SQ_SCENES) p->song.e[n].scene = 0u;
        p->song.e[n].bars = (uint8_t)clampi(p->song.e[n].bars, 1, 64);
        if (p->song.e[n].bpm && (p->song.e[n].bpm < 30u || p->song.e[n].bpm > 300u)) p->song.e[n].bpm = 0u;
    }
    for (n = 0; n < SQ_SNAPS; n++) sanitize_snap(&p->snap[n]);
    for (t = 0; t < SQ_TRACKS; t++)
        for (pat = 0; pat < SQ_PATTERNS; pat++)
            for (i = 0; i < SQ_STEPS; i++) sanitize_step(&p->step[t][pat][i]);
    p->reserved_end = 0u;
}

/* ------------------------------------------------------------------ timing */

int32_t sq_step_offset(uint32_t step_us, uint8_t step_index, uint8_t swing, int8_t nudge)
{
    int32_t d = 0, su = (int32_t)step_us;
    if (swing > SQ_SWING_MAX) swing = SQ_SWING_MAX;
    nudge = (int8_t)clampi(nudge, -(int32_t)SQ_NUDGE_MAX, (int32_t)SQ_NUDGE_MAX);
    /* odd steps sit at swing% of the pair: late by (2 * swing - 100)% of one step */
    if (swing > SQ_SWING_MIN && (step_index & 1u)) d += (su * (2 * (int32_t)swing - 100)) / 100;
    d += (su * (int32_t)nudge) / 100;
    if (d < -(su / 2)) d = -(su / 2);
    if (su && d >= su) d = su - 1;
    return d;
}

uint8_t sq_gate_sanitize(uint8_t v)
{
    if (v < 1u) return 1u;
    if (v > SQ_GATE_LONG_MAX) return SQ_GATE_LONG_MAX;
    return v;
}

uint32_t sq_gate_us(uint8_t encoded, uint32_t step_us, uint32_t slice_us)
{
    uint64_t us;
    encoded = sq_gate_sanitize(encoded);
    if (encoded <= 100u) {
        us = ((uint64_t)slice_us * encoded) / 100u;
    } else if (encoded == 101u) {
        us = ((uint64_t)step_us * 3u) / 2u;
    } else {
        us = (uint64_t)step_us * (uint32_t)(encoded - 100u);
    }
    if (!us) us = 1u;
    if (us > 0xFFFFFFFFu) us = 0xFFFFFFFFu;
    return (uint32_t)us;
}

uint8_t sq_ramp_velocity(uint8_t vel, int8_t ramp, uint8_t i, uint8_t n)
{
    int32_t r = ramp < 0 ? -(int32_t)ramp : (int32_t)ramp, scale, v;
    if (r > 100) r = 100;
    if (n <= 1u || r == 0) return vel;
    if (i >= n) i = (uint8_t)(n - 1u);
    r = r * (int32_t)i / (int32_t)(n - 1u);          /* how far along the roll, in percent of the ramp */
    scale = ramp > 0 ? (100 - (int32_t)ramp) + r : 100 - r;
    v = ((int32_t)vel * scale) / 100;
    return (uint8_t)clampi(v, 1, 127);
}

/* ------------------------------------------------------------------ arpeggio */

uint8_t sq_arp_build(const sq_step_t *s, uint8_t chord_mode, uint8_t *out)
{
    return sq_arp_build_notes(s->note, (uint8_t)SQ_POLY, chord_mode, out);
}

uint8_t sq_arp_build_notes(const uint8_t *notes, uint8_t cnt, uint8_t chord_mode, uint8_t *out)
{
    uint8_t base[SQ_POLY_OUT], list[SQ_ARP_MAX];
    uint8_t k = 0u, i, j, o, n = 0u, m = 0u;
    uint8_t mode = SQ_CHORD_MODE(chord_mode), octs = SQ_CHORD_OCTS(chord_mode);

    if (cnt > SQ_POLY_OUT) cnt = (uint8_t)SQ_POLY_OUT;
    for (i = 0; i < cnt; i++) {
        uint8_t v = notes[i];
        uint8_t dup = 0u;
        if (v == SQ_NOTE_NONE) continue;
        for (j = 0; j < k; j++) if (base[j] == v) dup = 1u;
        if (dup) continue;
        if (mode == SQ_CHORD_ARP_PLAYED) { base[k++] = v; continue; }        /* the order they were entered */
        for (j = k; j > 0u && base[j - 1u] > v; j--) base[j] = base[j - 1u];   /* insertion sort, ascending */
        base[j] = v;
        k++;
    }
    if (!k) return 0u;
    if (octs > 3u) octs = 3u;
    for (o = 0; o < octs; o++)
        for (i = 0; i < k; i++) {
            uint32_t v = (uint32_t)base[i] + 12u * o;
            if (v <= 127u) list[n++] = (uint8_t)v;
        }

    switch (mode) {
    case SQ_CHORD_ARP_DOWN:
        for (i = 0; i < n; i++) out[i] = list[n - 1u - i];
        return n;
    case SQ_CHORD_ARP_UPDN:
        for (i = 0; i < n; i++) out[m++] = list[i];
        for (j = (uint8_t)(n - 1u); n > 2u && j-- > 1u;) out[m++] = list[j];
        return m;
    case SQ_CHORD_ARP_DNUP:
        for (i = 0; i < n; i++) out[m++] = list[n - 1u - i];
        for (j = 1u; n > 2u && j + 1u < n; j++) out[m++] = list[j];
        return m;
    case SQ_CHORD_ARP_UPDN2:
        if (n < 2u) { out[0] = list[0]; return 1u; }
        for (i = 0; i < n; i++) out[m++] = list[i];
        for (i = 0; i < n; i++) out[m++] = list[n - 1u - i];
        return m;
    case SQ_CHORD_ARP_CONV: {
        uint8_t lo = 0u, hi = (uint8_t)(n - 1u);
        while (m < n) {
            out[m++] = list[lo++];
            if (m < n) out[m++] = list[hi--];
        }
        return m;
    }
    case SQ_CHORD_ARP_DIV: {
        int32_t up = (int32_t)(n - 1u) / 2, dn = up - 1;
        out[m++] = list[up++];
        while (m < n) {
            if (up < (int32_t)n) out[m++] = list[up++];
            if (m < n && dn >= 0) out[m++] = list[dn--];
        }
        return m;
    }
    case SQ_CHORD_ARP_THUMB:
        if (n < 2u) { out[0] = list[0]; return 1u; }
        for (i = 1u; i < n; i++) { out[m++] = list[0]; out[m++] = list[i]; }
        return m;
    case SQ_CHORD_ARP_PINKY:
        if (n < 2u) { out[0] = list[0]; return 1u; }
        for (i = 0; i + 1u < n; i++) { out[m++] = list[i]; out[m++] = list[n - 1u]; }
        return m;
    default:    /* UP, RND and WALK (the caller picks), PLAYED (already in the order) */
        for (i = 0; i < n; i++) out[i] = list[i];
        return n;
    }
}

uint8_t sq_voice_notes(const uint8_t *in, uint8_t cnt, uint8_t voicing, uint8_t *out)
{
    uint8_t n = 0u, i, j;
    for (i = 0; i < cnt && n < SQ_POLY_OUT; i++) {
        uint8_t v = in[i], dup = 0u;
        if (v == SQ_NOTE_NONE) continue;
        for (j = 0; j < n; j++) if (out[j] == v) dup = 1u;
        if (dup) continue;
        for (j = n; j > 0u && out[j - 1u] > v; j--) out[j] = out[j - 1u];
        out[j] = v; n++;
    }
    if (n < 2u) return n;
    if (voicing >= SQ_VOICES) voicing = SQ_VOICE_CLOSE;
    if (voicing == SQ_VOICE_INV1 && out[0] <= 115u) out[0] += 12u;
    else if (voicing == SQ_VOICE_INV2) {
        if (out[0] <= 115u) out[0] += 12u;
        if (n > 2u && out[1] <= 115u) out[1] += 12u;
    } else if (voicing == SQ_VOICE_DROP2 && n >= 3u) {
        uint8_t k = (uint8_t)(n - 2u);
        if (out[k] >= 12u) out[k] -= 12u;
    } else if (voicing == SQ_VOICE_OPEN) {
        for (i = 1u; i < n; i += 2u) if (out[i] <= 115u) out[i] += 12u;
    }
    /* transformations may disturb order; sort again for predictable strum/arp direction */
    for (i = 1u; i < n; i++) {
        uint8_t v = out[i];
        for (j = i; j > 0u && out[j - 1u] > v; j--) out[j] = out[j - 1u];
        out[j] = v;
    }
    for (i = 1u; i < n; i++)                     /* (two notes that became one) */
        if (out[i] == out[i - 1u]) { for (j = i; j + 1u < n; j++) out[j] = out[j + 1u]; n--; i--; }
    return n;
}

uint8_t sq_chord_voice(const sq_step_t *s, uint8_t voicing, uint8_t *out)
{
    return sq_voice_notes(s->note, SQ_POLY, voicing, out);
}

/* ---- 0.19 the MIDI FX chain */
const uint8_t SQ_MFX_ORDER[SQ_MFX_N] = {SQ_MFX_VELOCITY, SQ_MFX_OCTAVE, SQ_MFX_HARM, SQ_MFX_ECHO};

void sq_mfx_defaults(uint8_t fx, int8_t *amt, uint8_t *time, uint8_t *fb)
{
    *amt = 0; *time = 6u; *fb = 60u;                   /* (a dotted eighth, 60 %: the track's own defaults) */
    switch (fx) {
    case SQ_MFX_HARM:     *amt = 2; *fb = 75u; break;   /* a third above, a little softer */
    case SQ_MFX_OCTAVE:   *amt = 1; *time = SQ_OCT_ALT; break;
    case SQ_MFX_ECHO:     *amt = 2; break;              /* twice, a dotted eighth */
    case SQ_MFX_VELOCITY: *amt = 3; break;
    case SQ_MFX_CHANCE:   *amt = 70; *time = 0u; *fb = 0u; break;     /* 70 %, note by note */
    case SQ_MFX_RANDOM:   *amt = 2; *time = 16u; *fb = 50u; break;    /* two steps either way, velocity +-16, half the notes */
    case SQ_MFX_FILTER:   *amt = 0; *time = 127u; *fb = 1u; break;    /* every note, every time */
    case SQ_MFX_GATE:     *amt = -2; *time = 0u; *fb = 0u; break;     /* half as long */
    case SQ_MFX_GLITCH:   *amt = 25; *time = SQ_GL_MIX; *fb = 4u; break;   /* a step in four, any kind, four pieces */
    default: break;
    }
}

/* the range of each knob of each effect (knob 0 K2, 1 K3, 2 K4) */
void sq_mfx_range(uint8_t fx, uint8_t knob, uint8_t in_key, int32_t *lo, int32_t *hi)
{
    *lo = 0; *hi = 0;
    switch (fx) {
    case SQ_MFX_HARM:     if (knob == 0u) { *lo = in_key ? -7 : -12; *hi = in_key ? 7 : 12; } else if (knob == 2u) { *lo = 10; *hi = 100; } break;
    case SQ_MFX_OCTAVE:   if (knob == 0u) { *lo = -2; *hi = 2; } else if (knob == 1u) *hi = SQ_OCT_PATTERNS - 1; break;
    case SQ_MFX_ECHO:     if (knob == 0u) *hi = 4; else if (knob == 1u) *hi = SQ_ECHO_TIMES - 1; else { *lo = 10; *hi = 100; } break;
    case SQ_MFX_VELOCITY: if (knob == 0u) { *lo = -8; *hi = 8; } break;
    case SQ_MFX_CHANCE:   if (knob == 0u) *hi = 100; else if (knob == 1u) *hi = 1; break;   /* the chance; NOTE / STEP */
    case SQ_MFX_RANDOM:   if (knob == 0u) *hi = in_key ? 7 : 12; else if (knob == 1u) *hi = 64; else *hi = 100; break;
    case SQ_MFX_FILTER:   if (knob == 0u || knob == 1u) *hi = 127; else { *lo = 1; *hi = 8; } break;
    case SQ_MFX_GATE:     if (knob == 0u) { *lo = -3; *hi = 3; } else if (knob == 1u) *hi = SQ_GATE_FIXED - 1; else *hi = 50; break;
    case SQ_MFX_GLITCH:   if (knob == 0u) *hi = 100; else if (knob == 1u) *hi = SQ_GLITCHES - 1; else { *lo = 1; *hi = 8; } break;
    default: break;
    }
}

static void mfx_clamp(uint8_t fx, int8_t *amt, uint8_t *time, uint8_t *fb)
{
    int32_t lo, hi;
    if (fx < SQ_MFXS_019) {                            /* the four of 0.19, exactly as they were */
        switch (fx) {                                  /* each effect its own range (as sq_track_sanitize) */
        case SQ_MFX_HARM:     *amt = (int8_t)clampi(*amt, -12, 12); break;
        case SQ_MFX_OCTAVE:   *amt = (int8_t)clampi(*amt, -2, 2); if (*time >= SQ_OCT_PATTERNS) *time = SQ_OCT_ALT; break;
        case SQ_MFX_ECHO:     *amt = (int8_t)clampi(*amt, 0, 4); break;
        case SQ_MFX_VELOCITY: *amt = (int8_t)clampi(*amt, -8, 8); break;
        default:              *amt = 0; break;
        }
        if (*time >= SQ_ECHO_TIMES) *time = 6u;
        *fb = (uint8_t)clampi(*fb, 10, 100);
        return;
    }
    sq_mfx_range(fx, 0u, 0u, &lo, &hi); *amt = (int8_t)clampi(*amt, lo, hi);
    sq_mfx_range(fx, 1u, 0u, &lo, &hi); *time = (uint8_t)clampi(*time, lo, hi);
    sq_mfx_range(fx, 2u, 0u, &lo, &hi); *fb = (uint8_t)clampi(*fb, lo, hi);
    if (fx == SQ_MFX_FILTER && *time < (uint8_t)*amt) *time = (uint8_t)*amt;   /* (the highest note is never under the lowest) */
}

/* ---- 0.20: the five new effects and the order */
const uint8_t SQ_MFX_ORDER_DEF[SQ_MFX_ALLN] = {SQ_MFX_FILTER, SQ_MFX_CHANCE, SQ_MFX_VELOCITY, SQ_MFX_RANDOM, SQ_MFX_OCTAVE,
                                              SQ_MFX_HARM, SQ_MFX_GATE, SQ_MFX_GLITCH, SQ_MFX_ECHO};

void sq_mfxd_default(sq_mfxd_t *d)
{
    uint32_t k;
    d->on = 0u;
    for (k = 0; k < SQ_MFX_ALLN; k++) d->order[k] = SQ_MFX_ORDER_DEF[k];
    for (k = 0; k < SQ_MFX_NEW; k++) sq_mfx_defaults((uint8_t)(SQ_MFXS_019 + k), &d->amt[k], &d->time[k], &d->fb[k]);
}

void sq_mfxd_sanitize(sq_mfxd_t *d)
{
    uint32_t k, seen = 0u, ok = 1u;
    d->on &= (uint8_t)((1u << SQ_MFX_NEW) - 1u);
    for (k = 0; k < SQ_MFX_ALLN; k++) {                /* the order: each of the nine once, or the default */
        uint8_t fx = d->order[k];
        if (!fx || fx >= SQ_MFXS || (seen & (1u << fx))) { ok = 0u; break; }
        seen |= 1u << fx;
    }
    if (!ok) for (k = 0; k < SQ_MFX_ALLN; k++) d->order[k] = SQ_MFX_ORDER_DEF[k];
    for (k = 0; k < SQ_MFX_NEW; k++) mfx_clamp((uint8_t)(SQ_MFXS_019 + k), &d->amt[k], &d->time[k], &d->fb[k]);
}

uint8_t sq_mfx_is_on(const sq_ext_t *x, uint32_t t, uint8_t fx)
{
    if (t >= SQ_TRACKS || !fx || fx >= SQ_MFXS) return 0u;
    if (fx < SQ_MFXS_019) return SQ_MFX_ON(&x->mfxc[t], fx);
    return (uint8_t)((x->mfxd[t].on >> (fx - SQ_MFXS_019)) & 1u);
}

void sq_mfx_set_on(sq_ext_t *x, uint32_t t, uint8_t fx, uint8_t on)
{
    if (t >= SQ_TRACKS || !fx || fx >= SQ_MFXS) return;
    if (fx < SQ_MFXS_019) x->mfxc[t].on = (uint8_t)(on ? (x->mfxc[t].on | (1u << fx)) : (x->mfxc[t].on & ~(1u << fx)));
    else { uint8_t b = (uint8_t)(1u << (fx - SQ_MFXS_019)); x->mfxd[t].on = (uint8_t)(on ? (x->mfxd[t].on | b) : (x->mfxd[t].on & ~b)); }
}

void sq_mfx_get(const sq_ext_t *x, uint32_t t, uint8_t fx, int8_t *amt, uint8_t *time, uint8_t *fb)
{
    if (t >= SQ_TRACKS || !fx || fx >= SQ_MFXS) { *amt = 0; *time = 6u; *fb = 60u; return; }
    if (fx < SQ_MFXS_019) { *amt = x->mfxc[t].amt[fx - 1u]; *time = x->mfxc[t].time[fx - 1u]; *fb = x->mfxc[t].fb[fx - 1u]; }
    else { uint32_t k = fx - SQ_MFXS_019; *amt = x->mfxd[t].amt[k]; *time = x->mfxd[t].time[k]; *fb = x->mfxd[t].fb[k]; }
}

void sq_mfx_put(sq_ext_t *x, uint32_t t, uint8_t fx, int8_t amt, uint8_t time, uint8_t fb)
{
    if (t >= SQ_TRACKS || !fx || fx >= SQ_MFXS) return;
    mfx_clamp(fx, &amt, &time, &fb);
    if (fx < SQ_MFXS_019) { x->mfxc[t].amt[fx - 1u] = amt; x->mfxc[t].time[fx - 1u] = time; x->mfxc[t].fb[fx - 1u] = fb; }
    else { uint32_t k = fx - SQ_MFXS_019; x->mfxd[t].amt[k] = amt; x->mfxd[t].time[k] = time; x->mfxd[t].fb[k] = fb; }
}

uint8_t sq_mfx_count(const sq_ext_t *x, uint32_t t)
{
    uint8_t fx, n = 0u;
    for (fx = 1u; fx < SQ_MFXS; fx++) n = (uint8_t)(n + sq_mfx_is_on(x, t, fx));
    return n;
}

int sq_mfx_order_pos(const sq_ext_t *x, uint32_t t, uint8_t fx)
{
    uint32_t k;
    if (t >= SQ_TRACKS) return -1;
    for (k = 0; k < SQ_MFX_ALLN; k++) if (x->mfxd[t].order[k] == fx) return (int)k;
    return -1;
}

void sq_mfx_order_move(sq_ext_t *x, uint32_t t, uint8_t fx, int32_t d)
{
    int p = sq_mfx_order_pos(x, t, fx);
    uint8_t *o;
    if (p < 0 || !d) return;
    o = x->mfxd[t].order;
    while (d < 0 && p > 0) { uint8_t a = o[p - 1]; o[p - 1] = o[p]; o[p] = a; p--; d++; }
    while (d > 0 && p + 1 < (int)SQ_MFX_ALLN) { uint8_t a = o[p + 1]; o[p + 1] = o[p]; o[p] = a; p++; d--; }
}

uint32_t sq_gate_fixed_ticks(uint8_t idx)
{
    static const uint8_t T[SQ_GATE_FIXED] = {0u, 3u, 6u, 12u, 24u, 48u, 96u, 192u};
    return T[idx < SQ_GATE_FIXED ? idx : 0u];
}

uint32_t sq_gate_factor_x4(int8_t idx)
{
    static const uint8_t F[SQ_GATE_FACTORS] = {1u, 2u, 3u, 4u, 6u, 8u, 16u};
    return F[clampi(idx, -3, 3) + 3];
}

/* ---- 0.20 ENVELOPES */
uint32_t sq_env_ticks(uint8_t idx)
{
    static const uint16_t T[SQ_ENV_TIMES] = {0u, 1u, 2u, 3u, 4u, 6u, 9u, 12u, 18u, 24u, 36u, 48u, 72u, 96u, 192u, 384u};
    return T[idx < SQ_ENV_TIMES ? idx : 0u];
}

/* (32 bits only: the FM-1's library has no 64-bit division. Times in ticks x 256, levels on 10 bits, then x 64) */
static uint32_t env_ad(const sq_lfoe_t *e, uint32_t el)   /* ATTACK then DECAY to SUSTAIN, held there: 0..1023 */
{
    uint32_t a = sq_env_ticks(e->a) * 256u, d = sq_env_ticks(e->d) * 256u, s = (uint32_t)e->s * 1023u / 100u;
    if (el < a) return el * 1023u / a;
    el -= a;
    if (el < d) return 1023u - (1023u - s) * el / d;
    return s;
}

uint32_t sq_env_level(const sq_lfoe_t *e, uint32_t el, uint32_t gate)
{
    uint32_t r = sq_env_ticks(e->r) * 256u, at;
    if (el < gate) return env_ad(e, el) * 64u;
    at = env_ad(e, gate);                              /* the level when the note ended, then the release */
    el -= gate;
    if (!r || el >= r) return 0u;
    return at * (r - el) / r * 64u;
}

/* ---- 0.20 MOD MATRIX */
uint8_t sq_mod_src_count(uint8_t src)
{
    switch (src) {
    case SQ_MS_LFO: return SQ_LFOS;
    case SQ_MS_MACRO: return 4u;
    case SQ_MS_VEL: return SQ_TRACKS;
    case SQ_MS_CCIN: return 128u;
    default: return 1u;
    }
}

uint8_t sq_mod_dst_count(uint8_t dst)
{
    if (dst == SQ_MD_OFF || dst >= SQ_MDS) return 1u;
    return dst == SQ_MD_DEPTH || dst == SQ_MD_CENTER ? (uint8_t)SQ_LFOS : (uint8_t)SQ_TRACKS;
}

void sq_mod_sanitize(sq_mod_t *m)
{
    if (m->src >= SQ_MSS) m->src = SQ_MS_OFF;
    if (m->dst >= SQ_MDS) m->dst = SQ_MD_OFF;
    if (m->src_i >= sq_mod_src_count(m->src)) m->src_i = 0u;
    if (m->dst_i >= sq_mod_dst_count(m->dst)) m->dst_i = 0u;
    m->amt = (int8_t)clampi(m->amt, -100, 100);
}

void sq_mfx_sanitize(sq_mfxc_t *m)
{
    uint32_t k;
    m->on &= (uint8_t)SQ_MFX_ALL;
    for (k = 0; k < SQ_MFX_N; k++) mfx_clamp((uint8_t)(k + 1u), &m->amt[k], &m->time[k], &m->fb[k]);
}

void sq_mfx_mirror(const sq_mfxc_t *m, sq_track_cfg_t *c)
{
    uint8_t fx;
    for (fx = 1u; fx < SQ_MFXS_019; fx++) if (SQ_MFX_ON(m, fx)) break;
    if (fx < SQ_MFXS_019) { c->mfx = fx; c->mfx_amt = m->amt[fx - 1u]; c->mfx_time = m->time[fx - 1u]; c->mfx_fb = m->fb[fx - 1u]; }
    else { c->mfx = SQ_MFX_OFF; c->mfx_amt = 0; c->mfx_time = 6u; c->mfx_fb = 60u; }
}

void sq_mfx_from_track(const sq_track_cfg_t *c, sq_mfxc_t *m)
{
    uint32_t k;
    m->on = 0u;
    for (k = 0; k < SQ_MFX_N; k++) sq_mfx_defaults((uint8_t)(k + 1u), &m->amt[k], &m->time[k], &m->fb[k]);
    if (c->mfx != SQ_MFX_OFF && c->mfx < SQ_MFXS_019) {
        k = c->mfx - 1u;
        m->on = (uint8_t)(1u << c->mfx);
        m->amt[k] = c->mfx_amt; m->time[k] = c->mfx_time; m->fb[k] = c->mfx_fb;
        mfx_clamp(c->mfx, &m->amt[k], &m->time[k], &m->fb[k]);
    }
}

uint8_t sq_mfx_velocity(uint8_t vel, int8_t amount)
{
    int32_t v = vel, a = amount;
    if (a > 0) v += ((127 - v) * a) / 8;      /* positive bends upward */
    else if (a < 0) v += (v * a) / 8;         /* negative bends downward */
    return (uint8_t)clampi(v, 1, 127);
}


void sq_euclid(uint8_t pulses, uint8_t len, uint8_t rot, uint8_t *bits)
{
    uint32_t i;
    if (len > SQ_STEPS) len = (uint8_t)SQ_STEPS;
    if (!len) return;
    if (pulses > len) pulses = len;
    for (i = 0; i < len; i++) {
        uint32_t src = (i + len - (rot % len)) % len;
        bits[i] = (uint8_t)(((src * pulses) % len) < pulses ? 1u : 0u);
    }
}

uint8_t sq_euclid_hit(uint8_t pulses, uint8_t len, uint8_t rot, uint8_t i)
{
    uint32_t src;
    if (!len) return 0u;
    if (len > SQ_STEPS) len = (uint8_t)SQ_STEPS;
    if (pulses > len) pulses = len;
    i = (uint8_t)(i % len);
    src = ((uint32_t)i + len - (rot % len)) % len;
    return (uint8_t)(((src * pulses) % len) < pulses ? 1u : 0u);
}

/* ------------------------------------------------------------------ 0.8 the algorithms */

uint32_t sq_turing_step(uint32_t reg, uint8_t len, uint8_t mutation, uint32_t rnd)
{
    uint32_t mask, out;
    if (len < 2u) len = 2u;
    if (len > 32u) len = 32u;
    mask = len == 32u ? 0xFFFFFFFFu : ((1u << len) - 1u);
    reg &= mask;
    out = reg & 1u;
    if ((rnd % 100u) < mutation) out ^= 1u;
    return ((reg >> 1) | (out << (len - 1u))) & mask;
}

uint64_t sq_cell_next(uint64_t row, uint8_t cells, uint8_t rule)
{
    uint64_t neu = 0u, mask;
    uint32_t i;
    if (cells < 3u) cells = 3u;
    if (cells > 64u) cells = 64u;
    mask = cells == 64u ? ~(uint64_t)0 : (((uint64_t)1u << cells) - 1u);
    row &= mask;
    for (i = 0; i < cells; i++) {
        uint32_t l = (uint32_t)((row >> ((i + cells - 1u) % cells)) & 1u), c = (uint32_t)((row >> i) & 1u);
        uint32_t r = (uint32_t)((row >> ((i + 1u) % cells)) & 1u);
        if ((rule >> ((l << 2) | (c << 1) | r)) & 1u) neu |= (uint64_t)1u << i;
    }
    if (!neu) neu = (uint64_t)1u << (cells / 2u);      /* never silent: a single cell starts it again */
    return neu;
}

int32_t sq_accent(uint8_t style, uint8_t amount, uint8_t offset, uint32_t i, uint32_t rnd)
{
    int32_t amt = amount > 63u ? 63 : (int32_t)amount;
    uint32_t j = i + offset;
    switch (style) {
    default:
    case 0: return (j & 3u) == 0u ? amt : -amt / 3;                        /* BEAT: the quarters */
    case 1: return (j & 3u) == 2u ? amt : -amt / 4;                        /* OFFBEAT: the eighths between */
    case 2: return (j % 3u) == 0u ? amt : -amt / 4;                        /* POLY3: every third step, across the bar */
    case 3: { uint32_t k = j & 7u; return (k == 0u || k == 3u || k == 6u) ? amt : -amt / 3; }   /* SYNC: 3 + 3 + 2 */
    case 4: return (rnd & 3u) == 0u ? amt : 0;                             /* RANDOM */
    }
}

uint8_t sq_density_hit(uint8_t written, uint8_t density, uint32_t i, uint32_t h, uint8_t *ghost)
{
    uint32_t p = h % 100u;
    *ghost = 0u;
    if (density == 100u) return written;
    if (density < 100u) {
        if (!written) return 0u;
        if ((i & 3u) == 0u) return p < 2u * (uint32_t)density ? 1u : 0u;   /* the beat goes last */
        return p < density ? 1u : 0u;
    }
    if (written) return 1u;
    {
        uint32_t add = (uint32_t)density - 100u;
        if (add > 100u) add = 100u;
        if ((i & 3u) == 0u) add /= 2u;                                     /* new hits between the beats first */
        else if ((i & 3u) == 2u) add = add * 3u / 4u;
        if (p < add) { *ghost = 1u; return 1u; }
    }
    return 0u;
}

/* ------------------------------------------------------------------ pattern tools */

void sq_row_clear(sq_step_t *row)
{
    uint32_t i;
    for (i = 0; i < SQ_STEPS; i++) sq_step_default(&row[i]);
}

void sq_row_reverse(sq_step_t *row, uint8_t len)
{
    uint32_t i, j;
    sq_step_t t;
    if (len > SQ_STEPS) len = (uint8_t)SQ_STEPS;
    for (i = 0, j = len; i + 1u < j; i++, j--) {
        t = row[i]; row[i] = row[j - 1u]; row[j - 1u] = t;
    }
}

void sq_row_shift(sq_step_t *row, uint8_t len, int8_t dir)
{
    uint32_t i;
    sq_step_t t;
    if (len > SQ_STEPS) len = (uint8_t)SQ_STEPS;
    if (len < 2u) return;
    if (dir > 0) {
        t = row[len - 1u];
        for (i = len - 1u; i > 0u; i--) row[i] = row[i - 1u];
        row[0] = t;
    } else {
        t = row[0];
        for (i = 0; i + 1u < len; i++) row[i] = row[i + 1u];
        row[len - 1u] = t;
    }
}

void sq_row_random(sq_step_t *row, uint8_t len, uint8_t density, uint32_t *rng)
{
    uint32_t i;
    if (len > SQ_STEPS) len = (uint8_t)SQ_STEPS;
    for (i = 0; i < len; i++) {
        if ((sq_rng_next(rng) % 100u) < density) row[i].flags |= SQ_STEP_ON;
        else row[i].flags &= (uint8_t)~SQ_STEP_ON;
    }
}

void sq_row_euclid(sq_step_t *row, uint8_t len, uint8_t pulses, uint8_t rot)
{
    uint8_t bits[SQ_STEPS];
    uint32_t i;
    if (len > SQ_STEPS) len = (uint8_t)SQ_STEPS;
    sq_euclid(pulses, len, rot, bits);
    for (i = 0; i < len; i++) {
        if (bits[i]) row[i].flags |= SQ_STEP_ON;
        else row[i].flags &= (uint8_t)~SQ_STEP_ON;
    }
}

void sq_row_invert(sq_step_t *row, uint8_t len)
{
    uint32_t i;
    if (len > SQ_STEPS) len = (uint8_t)SQ_STEPS;
    for (i = 0; i < len; i++) row[i].flags ^= SQ_STEP_ON;
}

void sq_row_humanize(sq_step_t *row, uint8_t len, uint32_t *rng)
{
    uint32_t i;
    if (len > SQ_STEPS) len = (uint8_t)SQ_STEPS;
    for (i = 0; i < len; i++) {
        sq_step_t *s = &row[i];
        if (!(s->flags & SQ_STEP_ON)) continue;
        s->velocity = (uint8_t)clampi((int32_t)s->velocity + (int32_t)(sq_rng_next(rng) % 17u) - 8, 1, 127);
        s->nudge = (int8_t)clampi((int32_t)s->nudge + (int32_t)(sq_rng_next(rng) % 7u) - 3, -(int32_t)SQ_NUDGE_MAX, (int32_t)SQ_NUDGE_MAX);
    }
}


void sq_row_cook(sq_step_t *row, uint8_t len, uint8_t heat, uint32_t *rng)
{
    static const uint8_t GATES[4] = {25u, 50u, 80u, 100u};
    uint32_t i, swaps;
    uint8_t ref = 255u;
    if (len > SQ_STEPS) len = (uint8_t)SQ_STEPS;
    if (heat > 100u) heat = 100u;
    if (!heat || !len) return;
    for (i = 0; i < len; i++) if ((row[i].flags & (SQ_STEP_ON | SQ_STEP_SET)) == (SQ_STEP_ON | SQ_STEP_SET)) { ref = (uint8_t)i; break; }

    for (i = 0; i < len; i++) {
        sq_step_t *s = &row[i];
        uint8_t beat = (i & 3u) == 0u, first = i == 0u;
        uint32_t p = first ? 0u : beat ? heat / 10u : heat / 3u;      /* the offbeats move first */
        if (pct(rng) < p) {
            if (s->flags & SQ_STEP_ON) s->flags &= (uint8_t)~SQ_STEP_ON;
            else {
                s->flags |= SQ_STEP_ON;
                if (!(s->flags & SQ_STEP_SET)) {                      /* a new hit plays what the pattern plays */
                    uint32_t n;
                    s->velocity = (uint8_t)(60u + sq_rng_next(rng) % 50u);
                    if (ref != 255u) {                                /* (no programmed step: the caller's pen note) */
                        for (n = 0; n < SQ_POLY; n++) s->note[n] = row[ref].note[n];
                        s->flags |= SQ_STEP_SET;
                    }
                }
            }
        }
        if (!(s->flags & SQ_STEP_ON)) continue;
        if (pct(rng) < heat / 2u) {
            int32_t span = (int32_t)(heat / 4u);
            s->velocity = (uint8_t)clampi((int32_t)s->velocity + (int32_t)(sq_rng_next(rng) % (uint32_t)(2 * span + 1)) - span, 20, 127);
        }
        if (pct(rng) < heat / 10u) s->velocity = 127u;
        if (!beat && pct(rng) < heat / 12u) s->ratchet = (uint8_t)(2u + sq_rng_next(rng) % 3u);
        else if (s->ratchet > 1u && pct(rng) < heat / 6u) s->ratchet = 1u;
        if (pct(rng) < heat / 5u) s->length = GATES[sq_rng_next(rng) % 4u];
        if (!first && pct(rng) < heat / 15u) s->condition = (uint8_t)(1u + sq_rng_next(rng) % 6u);
        else if (s->condition != SQ_COND_ALWAYS && pct(rng) < heat / 8u) s->condition = SQ_COND_ALWAYS;
        if (!beat && pct(rng) < heat / 12u) s->chance = (uint8_t)(50u + sq_rng_next(rng) % 41u);
        else if (s->chance < 100u && pct(rng) < heat / 10u) s->chance = 100u;
    }

    swaps = heat / 12u;                                               /* the same notes in a different order */
    while (swaps--) {
        uint32_t a = sq_rng_next(rng) % len, b = sq_rng_next(rng) % len, n;
        if (a == b || !(row[a].flags & SQ_STEP_ON) || !(row[b].flags & SQ_STEP_ON)) continue;
        for (n = 0; n < SQ_POLY; n++) { uint8_t t = row[a].note[n]; row[a].note[n] = row[b].note[n]; row[b].note[n] = t; }
    }
}

uint8_t sq_row_double(sq_step_t *row, uint8_t len, uint8_t room)
{
    uint32_t i, nl;
    if (room > SQ_STEPS) room = (uint8_t)SQ_STEPS;
    if (len < 1u) len = 1u;
    if (len >= room) return room;
    nl = 2u * len;
    if (nl > room) nl = room;                          /* (a loop that starts late has less room after it) */
    for (i = len; i < nl; i++) row[i] = row[i - len];
    return (uint8_t)nl;
}

uint8_t sq_row_extend(sq_step_t *row, uint8_t start, uint8_t period, uint8_t from, uint8_t new_len)
{
    uint32_t i, span;
    if (new_len > SQ_STEPS) new_len = (uint8_t)SQ_STEPS;
    if (period < 1u) period = 1u;
    if (start >= period) start = (uint8_t)(period - 1u);
    if (from < period) from = period;
    if (new_len <= from) return 0u;
    for (i = from; i < new_len; i++) if (row[i].flags & SQ_STEP_ON) return 0u;   /* something is written there: it comes back */
    span = (uint32_t)period - start;
    for (i = from; i < new_len; i++) row[i] = row[start + (i - start) % span];
    return (uint8_t)(new_len - from);
}

static uint8_t pent_or(uint8_t scale) { return scale == SQ_SC_CHROMATIC ? (uint8_t)SQ_SC_PENT_MINOR : scale; }

void sq_row_cook_notes(sq_step_t *row, uint8_t len, uint8_t heat, uint8_t root, uint8_t scale, uint32_t *rng)
{
    uint32_t i, n;
    if (len > SQ_STEPS) len = (uint8_t)SQ_STEPS;
    if (heat > 100u) heat = 100u;
    scale = pent_or(scale);                             /* no key: the notes move in the minor pentatonic */
    for (i = 0; i < len; i++) {
        sq_step_t *s = &row[i];
        int32_t deg = 0, oct = 0;
        if (!(s->flags & SQ_STEP_ON) || !(s->flags & SQ_STEP_SET)) continue;
        if (pct(rng) < heat / 3u) {
            deg = (pct(rng) < 75u) ? 1 : 2;
            if (sq_rng_next(rng) & 1u) deg = -deg;
        }
        if (pct(rng) < heat / 15u) oct = (sq_rng_next(rng) & 1u) ? 12 : -12;
        if (!deg && !oct) continue;
        for (n = 0; n < SQ_POLY; n++) {
            int32_t v;
            if (s->note[n] == SQ_NOTE_NONE) continue;
            v = (int32_t)sq_scale_degree(s->note[n], root, scale, deg) + oct;
            if (v < 0 || v > 127) v -= oct;
            s->note[n] = (uint8_t)v;
        }
        for (n = 1; n < SQ_POLY; n++) {                 /* (two notes that became one) */
            uint32_t k;
            for (k = 0; k < n; k++) if (s->note[n] != SQ_NOTE_NONE && s->note[k] == s->note[n]) s->note[n] = SQ_NOTE_NONE;
        }
    }
}

void sq_row_cook_lanes(sq_step_t *row, uint8_t len, uint8_t heat, uint8_t lane_mask, const uint8_t *base, uint32_t *rng)
{
    uint32_t i, l;
    int32_t span;
    if (len > SQ_STEPS) len = (uint8_t)SQ_STEPS;
    if (heat > 100u) heat = 100u;
    span = 4 + (int32_t)heat * 60 / 100;               /* how far a value moves at most */
    for (l = 0; l < SQ_LANES; l++) {
        int32_t b = base && base[l] <= 127u ? (int32_t)base[l] : 64;
        if (!(lane_mask & (1u << l))) continue;
        for (i = 0; i < len; i++) {
            sq_step_t *s = &row[i];
            int32_t r = (int32_t)(sq_rng_next(rng) % (uint32_t)(2 * span + 1)) - span;
            if (!(s->flags & SQ_STEP_ON)) continue;
            if (s->lane[l] != SQ_LANE_NONE) {
                if (pct(rng) < heat / 10u) s->lane[l] = SQ_LANE_NONE;
                else if (pct(rng) < heat / 2u) s->lane[l] = (uint8_t)clampi((int32_t)s->lane[l] + r, 0, 127);
            } else if (pct(rng) < heat / 4u) {
                s->lane[l] = (uint8_t)clampi(b + r, 0, 127);
            }
        }
    }
}

void sq_row_random_notes(sq_step_t *row, uint8_t len, uint8_t center, uint8_t root, uint8_t scale, uint32_t *rng)
{
    uint32_t i, n;
    if (len > SQ_STEPS) len = (uint8_t)SQ_STEPS;
    if (center > 127u) center = 60u;
    scale = pent_or(scale);
    for (i = 0; i < len; i++) {
        sq_step_t *s = &row[i];
        int32_t v;
        if (!(s->flags & SQ_STEP_ON)) continue;
        v = (int32_t)center + (int32_t)(sq_rng_next(rng) % 15u) - 7;      /* an octave and a bit around the pen note */
        v = clampi(v, 0, 127);
        for (n = 0; n < SQ_POLY; n++) s->note[n] = SQ_NOTE_NONE;
        s->note[0] = sq_scale_snap((uint8_t)v, root, scale);
        s->flags |= SQ_STEP_SET;
    }
}

void sq_row_random_lanes(sq_step_t *row, uint8_t len, uint8_t density, uint8_t lane_mask, uint32_t *rng)
{
    uint32_t i, l;
    if (len > SQ_STEPS) len = (uint8_t)SQ_STEPS;
    for (l = 0; l < SQ_LANES; l++) {
        if (!(lane_mask & (1u << l))) continue;
        for (i = 0; i < len; i++) {
            sq_step_t *s = &row[i];
            if (!(s->flags & SQ_STEP_ON)) continue;
            s->lane[l] = pct(rng) < density ? (uint8_t)(sq_rng_next(rng) % 128u) : SQ_LANE_NONE;
        }
    }
}

/* ------------------------------------------------------------------ REC */

void sq_rec_target(uint8_t cur, uint8_t start, uint8_t len, uint8_t dir, uint8_t phase_pct, uint8_t quantize,
                   uint8_t *step_out, int8_t *nudge_out)
{
    uint8_t step = cur;
    int32_t nudge;
    if (!len) len = 1u;
    if (start >= len) start = 0u;
    if (step < start || step >= len) step = start;
    if (phase_pct > 99u) phase_pct = 99u;
    if (phase_pct >= 50u && dir == SQ_DIR_FWD) {
        step = (uint8_t)(step + 1u >= len ? start : step + 1u);
        nudge = (int32_t)phase_pct - 100;                              /* -50 .. -1: it was played early */
    } else if (phase_pct >= 50u && dir == SQ_DIR_REV) {
        step = step <= start ? (uint8_t)(len - 1u) : (uint8_t)(step - 1u);
        nudge = (int32_t)phase_pct - 100;
    } else {
        nudge = phase_pct > SQ_NUDGE_MAX ? (int32_t)SQ_NUDGE_MAX : (int32_t)phase_pct;   /* ping-pong / random: no way to know the next */
    }
    if (quantize) nudge = 0;
    *step_out = step;
    *nudge_out = (int8_t)nudge;
}

/* ------------------------------------------------------------------ LFO */

uint16_t sq_lfo_ticks(uint8_t rate)
{
    static const uint16_t T[SQ_LFO_RATES] = {1536u, 768u, 384u, 288u, 192u, 144u, 96u, 72u,
                                             48u, 36u, 24u, 18u, 12u, 9u, 6u, 3u,
                                             16u, 8u, 4u, 2u};          /* 0.13: 1/4T 1/8T 1/16T 1/32T */
    return T[rate < SQ_LFO_RATES ? rate : 6u];
}

static uint32_t hash32(uint32_t c, uint32_t idx)
{
    uint32_t x = c * 0x9E3779B1u + idx * 0x85EBCA6Bu + 0x68E31DA4u;
    x ^= x >> 15; x *= 0x2C1B3C6Du; x ^= x >> 12; x *= 0x297A2D39u; x ^= x >> 15;
    return x;
}

static int32_t sine_q(uint32_t p16)       /* p16: 0..65535 = one turn; the result -127..127 */
{
    static const uint8_t Q[65] = {0, 3, 6, 9, 12, 16, 19, 22, 25, 28, 31, 34, 37, 40, 43, 46, 49, 51, 54, 57, 60,
                                  63, 65, 68, 71, 73, 76, 78, 81, 83, 85, 88, 90, 92, 94, 96, 98, 100, 102, 104,
                                  106, 107, 109, 111, 112, 113, 115, 116, 117, 118, 120, 121, 122, 122, 123, 124,
                                  125, 125, 126, 126, 126, 127, 127, 127, 127};
    uint32_t q = (p16 >> 14) & 3u, x = p16 & 0x3FFFu;       /* quadrant, position inside it (14 bits) */
    uint32_t i, f, v;
    if (q & 1u) x = 0x4000u - x;                           /* the 2nd and 4th quadrants run backwards */
    i = x >> 8; f = x & 0xFFu;                              /* 64 steps of 256 */
    v = (uint32_t)Q[i] * (256u - f) + (uint32_t)Q[i + 1u > 64u ? 64u : i + 1u] * f;
    v = (v + 128u) >> 8;
    return q >= 2u ? -(int32_t)v : (int32_t)v;
}

int16_t sq_lfo_wave(const sq_lfo_t *l, uint8_t index, uint32_t tick, uint16_t frac16)
{
    uint32_t cyc = sq_lfo_ticks(l->rate), a, p, q, c;
    int32_t v;
    a = (tick % cyc) * 65536u + frac16;
    p = a / cyc;                                            /* 0..65535 */
    q = p + (uint32_t)l->phase * 512u;
    c = tick / cyc + (q >> 16);                             /* which cycle (the random shapes change with it) */
    p = q & 0xFFFFu;
    switch (l->shape) {
    default:
    case SQ_LFO_SINE:    v = sine_q(p); break;
    case SQ_LFO_TRI:     v = p < 32768u ? -128 + (int32_t)(p >> 7) : 127 - (int32_t)((p - 32768u) >> 7); break;
    case SQ_LFO_RAMP_UP: v = (int32_t)(p >> 8) - 128; break;
    case SQ_LFO_RAMP_DN: v = 127 - (int32_t)(p >> 8); break;
    case SQ_LFO_SQUARE:  v = p < 32768u ? 127 : -128; break;
    case SQ_LFO_SH:      v = (int32_t)((hash32(c, index) >> 8) & 255u) - 128; break;
    case SQ_LFO_SMOOTH: {
        int32_t x = (int32_t)((hash32(c, index) >> 8) & 255u) - 128, y = (int32_t)((hash32(c + 1u, index) >> 8) & 255u) - 128;
        int32_t t = (int32_t)(p >> 8), s = (t * t * (768 - 2 * t)) >> 16;      /* smoothstep, 0..256 */
        v = x + ((y - x) * s) / 256;
        break;
    }
    case SQ_LFO_DECAY:
    case SQ_LFO_ENV: {                                      /* (0.20 ENV: the firmware draws it from its notes; here a decay) */
        int32_t u = 255 - (int32_t)(p >> 8);
        v = ((u * u) >> 8) - 128;
        break;
    }
    }
    v = clampi(v, -128, 127);
    if (l->flags & SQ_LF_INVERT) v = -1 - v;
    return (int16_t)v;
}

uint8_t sq_lfo_cc(const sq_lfo_t *l, uint8_t index, uint32_t tick, uint16_t frac16)
{
    int32_t w = sq_lfo_wave(l, index, tick, frac16);
    return (uint8_t)clampi((int32_t)l->center + (w * (int32_t)l->depth) / 128, 0, 127);
}

/* ---- 0.13 */
void sq_ext_default(sq_ext_t *x)
{
    uint32_t i, k;
    uint8_t *b = (uint8_t *)x;
    for (i = 0; i < sizeof *x; i++) b[i] = 0u;
    for (i = 0; i < SQ_LFOS; i++) {
        x->lfo[i].seq_every = SQ_RE_BEAT;
        for (k = 0; k < SQ_RSEQ_MAX; k++) x->lfo[i].seq_rate[k] = SQ_RSEQ_OWN;
    }
    for (i = 0; i < SQ_TRACKS; i++) {
        x->track[i].chain_n = 1u;
        for (k = 0; k < SQ_CHAIN_MAX; k++) { x->track[i].chain_pat[k] = (uint8_t)(k < SQ_PATTERNS ? k : 0u); x->track[i].chain_rep[k] = 1u; }
    }
    for (i = 0; i < 4u; i++) for (k = 0; k < SQ_MOTION_CELLS; k++) x->motion[i][k] = (int8_t)SQ_MOTION_NONE;
    for (i = 0; i < SQ_TRACKS; i++)                    /* 0.19: no MIDI FX plays; each one's values when first chosen */
        for (k = 0; k < SQ_MFX_N; k++) sq_mfx_defaults((uint8_t)(k + 1u), &x->mfxc[i].amt[k], &x->mfxc[i].time[k], &x->mfxc[i].fb[k]);
    for (i = 0; i < SQ_TRACKS; i++) sq_mfxd_default(&x->mfxd[i]);   /* 0.20 */
    for (i = 0; i < SQ_LFOS; i++) { x->lfoe[i].a = 1u; x->lfoe[i].d = 7u; x->lfoe[i].s = 0u; x->lfoe[i].r = 5u; }   /* a short pluck */
    for (i = 0; i < SQ_MODS; i++) x->mod[i].amt = 50;
}

/* 0.23: the THEORY block */
void sq_theory_default(sq_theory_t *h)
{
    uint32_t i;
    uint8_t *b = (uint8_t *)h;
    for (i = 0; i < sizeof *h; i++) b[i] = 0u;
}
void sq_thpat_sanitize(sq_thpat_t *m)
{
    if (!(m->style & 31u) || (m->style & 31u) > SQ_TH_STYLES || (m->style & 0x80u) || ((m->style >> 5) & 3u) > 2u) {
        m->seed = 0u; m->style = 0u; m->func = 0u; m->var = 0u; m->vary = 0u; m->energy = 0u; m->reserved = 0u;   /* not the engines': nothing kept */
        return;
    }
    if (m->func >= 64u) m->func = 0u;                    /* (the library checks the rest: a part the engines cannot make is not made) */
    if (m->vary > 100u) m->vary = 100u;
    if (m->energy > 100u) m->energy = 100u;
    m->reserved = 0u;
}
void sq_theory_sanitize(sq_theory_t *h)
{
    uint32_t t, pat;
    if (h->src >= SQ_SRCS) h->src = SQ_SRC_LIBRARY;
    h->reserved = 0u;
    if (h->seed >= SQ_TH_SEEDS) h->seed = 0u;
    for (t = 0; t < SQ_TRACKS; t++)
        for (pat = 0; pat < SQ_PATTERNS; pat++) sq_thpat_sanitize(&h->pat[t][pat]);
}

void sq_ext_sanitize(sq_ext_t *x)
{
    static const int8_t LO[4] = {-63, -90, -25, -64}, HI[4] = {63, 100, 25, 63};
    uint32_t i, k;
    for (i = 0; i < SQ_LFOS; i++) {
        sq_lfox_t *l = &x->lfo[i];
        if (l->seq_n == 1u || l->seq_n > SQ_RSEQ_MAX) l->seq_n = 0u;
        if (l->seq_every >= SQ_RES) l->seq_every = SQ_RE_BEAT;
        for (k = 0; k < SQ_RSEQ_MAX; k++) if (l->seq_rate[k] >= SQ_LFO_RATES && l->seq_rate[k] != SQ_RSEQ_OWN) l->seq_rate[k] = SQ_RSEQ_OWN;
        if (l->trig > SQ_TRACKS) l->trig = 0u;
        l->reserved = 0u;
    }
    for (i = 0; i < SQ_TRACKS; i++) {
        sq_trackx_t *c = &x->track[i];
        c->chain_on = c->chain_on ? 1u : 0u;
        if (c->chain_n < 1u || c->chain_n > SQ_CHAIN_MAX) c->chain_n = 1u;
        for (k = 0; k < SQ_CHAIN_MAX; k++) {
            if (c->chain_pat[k] >= SQ_PATTERNS) c->chain_pat[k] = 0u;
            if (c->chain_rep[k] < 1u || c->chain_rep[k] > 8u) c->chain_rep[k] = 1u;
        }
        if (c->groove >= SQ_GROOVES) c->groove = SQ_GROOVE_OFF;
        if (c->groove_amt > 100u) c->groove_amt = 100u;
    }
    if (x->motion_bars != 1u && x->motion_bars != 2u && x->motion_bars != 4u) x->motion_bars = 0u;
    if (x->kb_mode >= SQ_KBS) x->kb_mode = SQ_KB_OFF;
    if (x->kb_ch > 16u) x->kb_ch = 0u;
    x->in_thru = x->in_thru ? 1u : 0u;
    for (i = 0; i < 4u; i++)
        for (k = 0; k < SQ_MOTION_CELLS; k++)
            if (x->motion[i][k] != (int8_t)SQ_MOTION_NONE) x->motion[i][k] = (int8_t)clampi(x->motion[i][k], LO[i], HI[i]);
    for (i = 0; i < sizeof x->reserved; i++) x->reserved[i] = 0u;
    sq_name_sanitize(x->name, SQ_NAME_LEN);
    for (i = 0; i < SQ_TRACKS; i++) sq_mfx_sanitize(&x->mfxc[i]);   /* 0.19 */
    for (i = 0; i < SQ_TRACKS; i++) sq_mfxd_sanitize(&x->mfxd[i]);  /* 0.20 */
    for (i = 0; i < SQ_LFOS; i++) {
        sq_lfoe_t *e = &x->lfoe[i];
        if (e->a >= SQ_ENV_TIMES) e->a = 1u;
        if (e->d >= SQ_ENV_TIMES) e->d = 7u;
        if (e->r >= SQ_ENV_TIMES) e->r = 5u;
        if (e->s > 100u) e->s = 100u;
    }
    for (i = 0; i < SQ_MODS; i++) sq_mod_sanitize(&x->mod[i]);
}

void sq_name_sanitize(char *n, uint32_t len)
{
    static const char OK[] = " -_.+#&!'()/:";
    uint32_t i, k = 0u, end = 0u, j;
    for (i = 0; i < len; i++) {
        uint8_t c = (uint8_t)n[i], ok = 0u;
        if (c == 0u || c == 0xFFu) break;
        if (c >= 'a' && c <= 'z') c = (uint8_t)(c - 32u);
        if ((c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')) ok = 1u;
        for (j = 0; !ok && OK[j]; j++) if (c == (uint8_t)OK[j]) ok = 1u;
        if (!ok) c = '_';
        if (c == ' ' && !k) continue;              /* (no space in front) */
        n[k++] = (char)c;
        if (c != ' ') end = k;
    }
    for (i = end; i < len; i++) n[i] = 0;          /* (nor at the end) */
}

/* ---- 0.15 GROOVE: a 16th each, the bar's 16 */
static const char *const GROOVE_NAME[SQ_GROOVES] = {"OFF", "HOUSE", "GARAGE", "DILLA", "AFRO", "SAMBA", "LAID BACK", "PUSH", "HUMAN", "TRAP"};
static const int8_t GROOVE_T[SQ_GROOVES][16] = {
    {0},
    {0, 6, 2, 6, 0, 6, 2, 6, 0, 6, 2, 6, 0, 6, 2, 6},                              /* HOUSE: the 16ths a touch late */
    {0, 28, 0, 22, 0, 30, 0, 24, 0, 28, 0, 22, 0, 30, 0, 24},                      /* GARAGE: the 2-step shuffle */
    {0, 20, -10, 14, 6, 24, -12, 16, 0, 18, -8, 12, 8, 26, -14, 18},               /* DILLA: drunk, never twice the same */
    {0, 4, -2, 6, 2, 4, 0, 8, 0, 4, -2, 6, 2, 4, 0, 8},                            /* AFRO: 3 + 3 + 2, pushed */
    {0, -8, 2, -12, 0, -8, 2, -12, 0, -8, 2, -12, 0, -8, 2, -12},                  /* SAMBA: the second and fourth 16th early */
    {0, 10, 8, 14, 0, 10, 8, 14, 0, 10, 8, 14, 0, 10, 8, 14},                      /* LAID BACK: behind the beat */
    {0, -6, -8, -12, 0, -6, -8, -12, 0, -6, -8, -12, 0, -6, -8, -12},              /* PUSH: ahead of it */
    {0, 3, -2, 4, -3, 2, 1, -4, 2, -1, 3, -2, 0, 4, -3, 1},                        /* HUMAN: a player's small misses */
    {0, 2, 0, 4, 0, 2, 0, 4, 0, 2, 0, 4, 0, 2, 0, 4},                              /* TRAP: tight, the accents do it */
};
static const int8_t GROOVE_V[SQ_GROOVES][16] = {
    {0},
    {6, -14, 10, -12, 6, -14, 10, -12, 6, -14, 10, -12, 6, -14, 10, -12},
    {8, -18, 2, -12, 8, -18, 2, -12, 8, -18, 2, -12, 8, -18, 2, -12},
    {8, -16, -2, -10, 4, -18, 0, -8, 8, -14, -4, -12, 2, -20, 2, -6},
    {12, -10, -8, 10, -10, -6, 10, -8, 12, -10, -8, 10, -10, -6, 10, -8},
    {10, -12, -4, 8, 10, -12, -4, 8, 10, -12, -4, 8, 10, -12, -4, 8},
    {4, -10, -2, -8, 4, -10, -2, -8, 4, -10, -2, -8, 4, -10, -2, -8},
    {6, -8, 0, 8, 6, -8, 0, 8, 6, -8, 0, 8, 6, -8, 0, 8},
    {4, -6, 2, -4, 3, -5, 1, -3, 5, -6, 2, -4, 2, -5, 3, -2},
    {14, -20, 4, -16, 14, -20, 4, -16, 14, -20, 4, -16, 14, -20, 4, -16},
};
const char *sq_groove_name(uint8_t g) { return GROOVE_NAME[g < SQ_GROOVES ? g : 0u]; }
int32_t sq_groove_time(uint8_t g, uint8_t amt, uint32_t step)
{
    if (g >= SQ_GROOVES || !amt) return 0;
    return ((int32_t)GROOVE_T[g][step & 15u] * (int32_t)(amt > 100u ? 100u : amt)) / 100;
}
int32_t sq_groove_vel(uint8_t g, uint8_t amt, uint32_t step)
{
    if (g >= SQ_GROOVES || !amt) return 0;
    return ((int32_t)GROOVE_V[g][step & 15u] * (int32_t)(amt > 100u ? 100u : amt)) / 100;
}

uint32_t sq_rseq_ticks(uint8_t every)
{
    static const uint8_t T[SQ_RES] = {24u, 48u, 96u, 192u};
    return T[every < SQ_RES ? every : 0u];
}

uint8_t sq_lfo_rate_at(const sq_lfo_t *l, const sq_lfox_t *x, uint32_t tick)
{
    uint8_t r;
    if (!x || x->seq_n < 2u) return l->rate;
    r = x->seq_rate[(tick / sq_rseq_ticks(x->seq_every)) % x->seq_n];
    return r < SQ_LFO_RATES ? r : l->rate;
}

uint32_t sq_lfo_seq_tick(const sq_lfox_t *x, uint32_t tick)
{
    if (!x || x->seq_n < 2u) return tick;
    return tick % sq_rseq_ticks(x->seq_every);
}

uint8_t sq_chain_next(const sq_trackx_t *c, uint8_t *pos, uint8_t *left)
{
    uint8_t n = c->chain_n >= 1u && c->chain_n <= SQ_CHAIN_MAX ? c->chain_n : 1u;
    if (*pos >= n) { *pos = 0u; *left = c->chain_rep[0]; return c->chain_pat[0]; }
    if (*left > 1u) { (*left)--; return c->chain_pat[*pos]; }
    *pos = (uint8_t)((*pos + 1u) % n);
    *left = c->chain_rep[*pos] ? c->chain_rep[*pos] : 1u;
    return c->chain_pat[*pos];
}

int sq_chain_find(const sq_trackx_t *c, uint8_t pattern)
{
    uint32_t k;
    for (k = 0; k < c->chain_n && k < SQ_CHAIN_MAX; k++) if (c->chain_pat[k] == pattern) return (int)k;
    return -1;
}

int32_t sq_kb_transpose(uint8_t note, uint8_t base_root)
{
    int32_t d = ((int32_t)(note % 12u) - (int32_t)(base_root % 12u) + 24) % 12;
    return d > 6 ? d - 12 : d;
}

int16_t sq_lfo_offset(const sq_lfo_t *l, uint8_t index, uint32_t tick, uint16_t frac16)
{
    int32_t w = sq_lfo_wave(l, index, tick, frac16);
    return (int16_t)((w * (int32_t)l->depth) / 256);
}

/* ------------------------------------------------------------------ scales */

#define B_(i) (1u << (i))
static const uint16_t SCALE_MASK[SQ_SCALES] = {
    0xFFFu,                                                                       /* chromatic */
    B_(0) | B_(2) | B_(4) | B_(5) | B_(7) | B_(9) | B_(11),                       /* major */
    B_(0) | B_(2) | B_(3) | B_(5) | B_(7) | B_(8) | B_(10),                       /* minor */
    B_(0) | B_(2) | B_(3) | B_(5) | B_(7) | B_(9) | B_(10),                       /* dorian */
    B_(0) | B_(1) | B_(3) | B_(5) | B_(7) | B_(8) | B_(10),                       /* phrygian */
    B_(0) | B_(2) | B_(4) | B_(6) | B_(7) | B_(9) | B_(11),                       /* lydian */
    B_(0) | B_(2) | B_(4) | B_(5) | B_(7) | B_(9) | B_(10),                       /* mixolydian */
    B_(0) | B_(1) | B_(3) | B_(5) | B_(6) | B_(8) | B_(10),                       /* locrian */
    B_(0) | B_(2) | B_(3) | B_(5) | B_(7) | B_(8) | B_(11),                       /* harmonic minor */
    B_(0) | B_(2) | B_(3) | B_(5) | B_(7) | B_(9) | B_(11),                       /* melodic minor */
    B_(0) | B_(2) | B_(4) | B_(7) | B_(9),                                        /* pentatonic major */
    B_(0) | B_(3) | B_(5) | B_(7) | B_(10),                                       /* pentatonic minor */
    B_(0) | B_(3) | B_(5) | B_(6) | B_(7) | B_(10),                               /* blues */
    B_(0) | B_(2) | B_(4) | B_(6) | B_(8) | B_(10),                               /* whole tone */
    B_(0) | B_(1) | B_(4) | B_(5) | B_(7) | B_(8) | B_(10),                       /* phrygian dominant */
    B_(0) | B_(2) | B_(3) | B_(7) | B_(8),                                        /* hirajoshi */
};

uint16_t sq_scale_mask(uint8_t scale) { return SCALE_MASK[scale < SQ_SCALES ? scale : 0u]; }

const char *sq_scale_name(uint8_t scale)
{
    static const char *const N[SQ_SCALES] = {"CHROMA", "MAJOR", "MINOR", "DORIAN", "PHRYG", "LYDIAN", "MIXOLY", "LOCRIAN",
                                             "H.MINOR", "M.MINOR", "PENT.+", "PENT.-", "BLUES", "WHOLE", "PHR.DOM", "HIRAJO"};
    return N[scale < SQ_SCALES ? scale : 0u];
}

const char *sq_scale_long_name(uint8_t scale)
{
    static const char *const N[SQ_SCALES] = {"CHROMATIC (OFF)", "MAJOR (IONIAN)", "MINOR (AEOLIAN)", "DORIAN", "PHRYGIAN",
                                             "LYDIAN", "MIXOLYDIAN", "LOCRIAN", "HARMONIC MINOR", "MELODIC MINOR",
                                             "PENTATONIC MAJOR", "PENTATONIC MINOR", "BLUES", "WHOLE TONE",
                                             "PHRYGIAN DOMINANT", "HIRAJOSHI"};
    return N[scale < SQ_SCALES ? scale : 0u];
}

const char *sq_root_name(uint8_t root)
{
    static const char *const N[12] = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};
    return N[root % 12u];
}

static int in_scale(int32_t note, uint8_t root, uint16_t mask)
{
    return (int)((mask >> ((uint32_t)(note + 120 - (int32_t)(root % 12u)) % 12u)) & 1u);
}

uint8_t sq_scale_snap(uint8_t note, uint8_t root, uint8_t scale)
{
    uint16_t mask = sq_scale_mask(scale);
    int32_t d;
    if (note > 127u || mask == 0xFFFu || !mask) return note;
    for (d = 0; d <= 6; d++) {
        int32_t lo = (int32_t)note - d, hi = (int32_t)note + d;
        if (lo >= 0 && in_scale(lo, root, mask)) return (uint8_t)lo;
        if (d && hi <= 127 && in_scale(hi, root, mask)) return (uint8_t)hi;
    }
    return note;
}

uint8_t sq_scale_apply(int32_t note, uint8_t root, uint8_t scale, int8_t shift)
{
    note += shift;
    if (note < 0) note = 0;
    if (note > 127) note = 127;
    return sq_scale_snap((uint8_t)note, root, scale);
}

uint8_t sq_scale_degree(int32_t note, uint8_t root, uint8_t scale, int32_t deg)
{
    uint16_t mask = sq_scale_mask(scale);
    int32_t v = clampi(note, 0, 127), dir = deg < 0 ? -1 : 1, k;
    if (!mask) mask = 0xFFFu;
    v = sq_scale_snap((uint8_t)v, root, scale);
    for (k = deg < 0 ? -deg : deg; k > 0; k--) {
        int32_t w = v, guard;
        for (guard = 0; guard < 12; guard++) {
            w += dir;
            if (w < 0 || w > 127) { w = v; break; }
            if (in_scale(w, root, mask)) break;
        }
        v = w;
    }
    return (uint8_t)v;
}

uint8_t sq_scale_nth(uint8_t base, uint8_t root, uint8_t scale, int32_t n)
{
    uint16_t mask = sq_scale_mask(scale);
    int32_t iv[12], cnt = 0, i, r0, oct, idx, v;
    if (!mask) mask = 0xFFFu;
    for (i = 0; i < 12; i++) if ((mask >> i) & 1u) iv[cnt++] = i;
    r0 = (int32_t)(base > 127u ? 60u : base);
    r0 -= ((r0 - (int32_t)(root % 12u)) % 12 + 12) % 12;   /* the root at or under base */
    oct = n >= 0 ? n / cnt : -((-n + cnt - 1) / cnt);
    idx = n - oct * cnt;
    v = r0 + 12 * oct + iv[idx];
    while (v < 0) v += 12;
    while (v > 127) v -= 12;
    return (uint8_t)v;
}

/* the scale as a list of intervals; returns how many (a scale with no notes: chromatic) */
static uint32_t scale_iv(uint8_t scale, int32_t *iv)
{
    uint16_t mask = sq_scale_mask(scale);
    uint32_t cnt = 0u, i;
    if (!mask) mask = 0xFFFu;
    for (i = 0; i < 12u; i++) if ((mask >> i) & 1u) iv[cnt++] = (int32_t)i;
    return cnt;
}

static int32_t floordiv(int32_t a, int32_t b) { return a >= 0 ? a / b : -((-a + b - 1) / b); }

int32_t sq_scale_index(uint8_t note, uint8_t root, uint8_t scale)
{
    int32_t iv[12], rel = (int32_t)(note > 127u ? 60u : note) - (int32_t)(root % 12u), oct, pc, k = 0;
    uint32_t cnt = scale_iv(scale, iv), i;
    oct = floordiv(rel, 12);
    pc = rel - 12 * oct;
    for (i = 0; i < cnt; i++) if (iv[i] <= pc) k = (int32_t)i;   /* (a note outside the scale: the one under it) */
    return oct * (int32_t)cnt + k;
}

uint8_t sq_scale_at(int32_t index, uint8_t root, uint8_t scale)
{
    int32_t iv[12], cnt = (int32_t)scale_iv(scale, iv), oct = floordiv(index, cnt), v;
    v = (int32_t)(root % 12u) + 12 * oct + iv[index - oct * cnt];
    while (v < 0) v += 12;
    while (v > 127) v -= 12;
    return (uint8_t)v;
}

/* ------------------------------------------------------------------ 0.8 harmony */

uint8_t sq_harm_scale(uint8_t scale)
{
    int32_t iv[12];
    if (scale_iv(scale, iv) == 7u) return scale;
    switch (scale) {
    case SQ_SC_PENT_MAJOR: return SQ_SC_MAJOR;
    case SQ_SC_WHOLE:      return SQ_SC_LYDIAN;
    default:               return SQ_SC_MINOR;          /* no key, pentatonic minor, blues, hirajoshi */
    }
}

static int32_t mod7(int32_t v) { return ((v % 7) + 7) % 7; }

uint8_t sq_harm_apply(uint8_t *notes, uint8_t n, uint8_t root, uint8_t scale, int8_t deg, uint8_t color, uint8_t chord)
{
    int32_t idx[SQ_POLY_OUT], d = mod7(deg);
    uint8_t hs = sq_harm_scale(scale), i, j, m = 0u;
    if (n > SQ_POLY_OUT) n = (uint8_t)SQ_POLY_OUT;
    if (!d && color == SQ_HC_TRIAD) return n;
    if (d > 3) d -= 7;                                   /* the nearer way: down a third rather than up a sixth */
    for (i = 0; i < n; i++) if (notes[i] != SQ_NOTE_NONE) { idx[m] = sq_scale_index(notes[i], root, hs); m++; }
    if (chord && m >= 2u && (color == SQ_HC_7 || color == SQ_HC_9 || color == SQ_HC_6)) {
        int32_t want = color == SQ_HC_7 ? 6 : color == SQ_HC_9 ? 1 : 5, have = 0, hi = idx[0], add;
        for (i = 0; i < m; i++) { if (mod7(idx[i]) == want) have = 1; if (idx[i] > hi) hi = idx[i]; }
        if (!have) {
            if (m < SQ_POLY_OUT) {                       /* room: the colour on top of the chord */
                add = hi + mod7(want - mod7(hi));
                if (add == hi) add += 7;
                idx[m++] = add;
            } else {                                     /* full: it takes the fifth's place, or a doubled note's */
                int32_t r = -1;
                for (i = 0; i < m && r < 0; i++) for (j = 0; j < i; j++) if (mod7(idx[j]) == mod7(idx[i])) { r = i; break; }
                for (i = 0; i < m && r < 0; i++) if (mod7(idx[i]) == 4) r = i;
                if (r < 0) { r = 0; for (i = 1; i < m; i++) if (idx[i] > idx[r]) r = i; }
                add = idx[r] + mod7(want - mod7(idx[r]));
                if (add - idx[r] > 3) add -= 7;          /* the nearest one */
                idx[r] = add;
            }
        }
    }
    for (i = 0; i < m; i++) {
        if (color == SQ_HC_SUS4 && mod7(idx[i]) == 2) idx[i]++;
        else if (color == SQ_HC_SUS2 && mod7(idx[i]) == 2) idx[i]--;
        idx[i] += d;
    }
    for (i = 0, j = 0; i < m; i++) {                     /* (two notes that became one: one is enough) */
        uint8_t v = sq_scale_at(idx[i], root, hs), k, dup = 0u;
        for (k = 0; k < j; k++) if (notes[k] == v) dup = 1u;
        if (!dup) notes[j++] = v;
    }
    for (i = j; i < n; i++) notes[i] = SQ_NOTE_NONE;
    return j;
}

void sq_harm_chord_name(uint8_t scale, int8_t deg, uint8_t color, char *out)
{
    static const char *const UP[7] = {"I", "II", "III", "IV", "V", "VI", "VII"};
    static const char *const LO[7] = {"i", "ii", "iii", "iv", "v", "vi", "vii"};
    static const char *const COL[SQ_HCS] = {"", "7", "9", "sus4", "sus2", "6"};
    int32_t iv[12], d = mod7(deg), third, fifth;
    uint8_t hs = sq_harm_scale(scale);
    const char *nm, *c;
    uint32_t k = 0;
    scale_iv(hs, iv);
    third = ((iv[(d + 2) % 7] - iv[d]) % 12 + 12) % 12;
    fifth = ((iv[(d + 4) % 7] - iv[d]) % 12 + 12) % 12;
    nm = third == 3 ? LO[d] : UP[d];
    while (*nm) out[k++] = *nm++;
    if (fifth == 6) out[k++] = 'o';                      /* diminished */
    else if (fifth == 8) out[k++] = '+';                 /* augmented */
    c = COL[color < SQ_HCS ? color : 0u];
    while (*c && k < 9u) out[k++] = *c++;
    out[k] = 0;
}

/* ------------------------------------------------------------------ 0.11 HARMONY: roots, shapes, rhythms, moods */
static const int8_t CHORD_SEMI[SQ_CH_COUNT][SQ_POLY_OUT];   /* (below, with the chord shapes) */
const char *sq_hrhythm_name(uint8_t r)
{
    static const char *const N[SQ_HRS] = {"BARS", "GENRE", "PUSH 16TH", "PUSH 8TH", "3+3+2", "TWO A BAR", "3+5", "3+1", "2 BARS"};
    return N[r < SQ_HRS ? r : 0u];
}
/* a rhythm's lengths (16ths, cycled over the chords) and push; 0 lengths: a chord every `bars` */
static void hrhythm(uint8_t r, const uint8_t **d, uint8_t *n, uint8_t *push)
{
    static const uint8_t R332[3] = {6u, 6u, 4u}, RHALF[2] = {8u, 8u}, R35[2] = {6u, 10u}, R31[2] = {12u, 4u}, R2B[1] = {32u};
    *d = 0; *n = 0u; *push = 0u;
    switch (r) {
    case SQ_HR_PUSH16: *push = 1u; break;
    case SQ_HR_PUSH8:  *push = 2u; break;
    case SQ_HR_332:    *d = R332; *n = 3u; break;
    case SQ_HR_HALF:   *d = RHALF; *n = 2u; break;
    case SQ_HR_35:     *d = R35; *n = 2u; break;
    case SQ_HR_31:     *d = R31; *n = 2u; break;
    case SQ_HR_2BARS:  *d = R2B; *n = 1u; break;
    default: break;
    }
}
void sq_hprog_lib(sq_hprog_t *h, const int8_t *deg, const uint8_t *col, uint8_t n, uint8_t bars, uint8_t rhythm)
{
    const uint8_t *d;
    uint8_t m, push, k, rows;
    hrhythm(rhythm, &d, &m, &push);
    if (n > SQ_HPROG_CH) n = SQ_HPROG_CH;
    if (!bars) bars = 1u;
    if (bars > 4u) bars = 4u;                                 /* (64 16ths: the longest a chord is) */
    rows = n;
    if (m > 1u && n) while (rows % m) rows = (uint8_t)(rows + n);   /* (the lengths and the chords come round together) */
    h->n = rows; h->nc = n;
    for (k = 0; k < rows; k++) {
        uint8_t i = (uint8_t)(k % n);
        h->c[k].deg = deg[i]; h->c[k].col = col[i]; h->c[k].semi = 255u; h->c[k].shape = col[i];
        h->dur[k] = m ? d[k % m] : (uint8_t)(16u * bars);
        h->push[k] = push;
    }
}
void sq_hprog_user(sq_hprog_t *h, const sq_uprog_t *u, uint8_t bars, uint8_t rhythm)
{
    uint8_t k, n = u->n > SQ_HPROG_CH ? SQ_HPROG_CH : u->n, own = 0u;
    for (k = 0; k < n; k++) if (u->dur[k]) own = 1u;
    /* the player's own lengths: one round of the chords, each its length (a chord without one: the rhythm's first) */
    sq_hprog_lib(h, u->deg, u->col, n, bars ? bars : u->bars, own ? SQ_HR_BARS : rhythm);
    if (own && n) {
        const uint8_t *d;
        uint8_t m, push;
        hrhythm(rhythm, &d, &m, &push);
        for (k = 0; k < n; k++) { if (m) h->dur[k] = d[k % m]; h->push[k] = push; }
    }
    for (k = 0; k < h->n; k++) {
        uint8_t i = (uint8_t)(k % (n ? n : 1u));
        if (u->semi[i] <= 11u) { h->c[k].semi = u->semi[i]; h->c[k].shape = u->shape[i]; }
        if (u->dur[i]) h->dur[k] = u->dur[i];                 /* the player's own length wins */
        if (u->dur[i] || u->push[i]) h->push[k] = u->push[i];
    }
}
uint32_t sq_hprog_len(const sq_hprog_t *h)
{
    uint32_t k, t = 0u;
    for (k = 0; k < h->n; k++) t += h->dur[k] ? h->dur[k] : 16u;
    return t;
}
uint8_t sq_hprog_at(const sq_hprog_t *h, uint32_t pos, sq_hchord_t *c)
{
    uint32_t len = sq_hprog_len(h), t, k, start = 0u, best = 0u;
    if (!h->n || !len) { c->deg = 0; c->col = SQ_HC_TRIAD; c->semi = 255u; c->shape = SQ_HC_TRIAD; return 0u; }
    t = pos % len;
    if (h->push[0] && t >= len - h->push[0]) { *c = h->c[0]; return 0u; }   /* the first chord, pushed: the end of the round */
    for (k = 0; k < h->n; k++) {
        uint32_t from = start > h->push[k] ? start - h->push[k] : 0u;
        if (t >= from) best = k;
        start += h->dur[k] ? h->dur[k] : 16u;
    }
    *c = h->c[best];
    return (uint8_t)(h->nc ? best % h->nc : best);
}

/* the step of the scale a root (semitones above the key's) is, or -1 */
static int32_t semi_degree(uint8_t hs, uint8_t semi)
{
    int32_t iv[12], d;
    scale_iv(hs, iv);
    for (d = 0; d < 7; d++) if (((iv[d] % 12) + 12) % 12 == semi) return d;
    return -1;
}
static uint8_t col_shape(uint8_t col)                    /* a colour on a root out of the key: a major chord with it */
{
    static const uint8_t S[SQ_HCS] = {SQ_CH_MAJ, SQ_CH_7, SQ_CH_9, SQ_CH_SUS4, SQ_CH_SUS2, SQ_CH_MAJ6};
    return S[col < SQ_HCS ? col : 0u];
}
/* the chord shape (SQ_CH_*) a chord is, or 0 when it is the key's own (by its step) */
static uint8_t chord_shape(uint8_t hs, const sq_hchord_t *c, int32_t *deg)
{
    *deg = c->deg;
    if (c->semi == 255u) return 0u;
    if (c->shape <= SQ_HSHAPE_CH) {
        int32_t d = semi_degree(hs, c->semi);
        if (d >= 0) { *deg = d; return 0u; }
        return col_shape(c->shape);
    }
    return (uint8_t)(c->shape - SQ_HSHAPE_CH);
}
uint8_t sq_hchord_semi(uint8_t scale, const sq_hchord_t *c)
{
    int32_t iv[12];
    if (c->semi <= 11u) return c->semi;
    scale_iv(sq_harm_scale(scale), iv);
    return (uint8_t)(((iv[mod7(c->deg)] % 12) + 12) % 12);
}
/* a shape's interval for a place of the tonic's chord (0 root, 1 ninth, 2 third, 3 eleventh, 4 fifth, 5 thirteenth,
 * 6 seventh: the steps of the scale), -1 if it has none */
static int32_t shape_tone(uint8_t sh, int32_t place)
{
    const int8_t *iv = CHORD_SEMI[sh < SQ_CH_COUNT ? sh : SQ_CH_MAJ];
    int32_t k, lo, hi, alt = -1;
    switch (place) {
    case 0: return 0;
    case 2: lo = 2; hi = 5; break;                       /* the third (a sus: its second or fourth) */
    case 4: lo = 6; hi = 8; break;
    case 6: lo = 9; hi = 11; break;                      /* (a 6th counts only in a dim7) */
    case 1: lo = 13; hi = 14; alt = 2; break;
    case 3: lo = 17; hi = 17; alt = 5; break;
    default: lo = 21; hi = 21; alt = 9; break;
    }
    for (k = 1; k < (int32_t)SQ_POLY_OUT && iv[k] >= 0; k++) {
        if (place == 6 && iv[k] == 9 && sh != SQ_CH_DIM7) continue;
        if (place == 2 && (iv[k] == 2 || iv[k] == 5)) { int32_t j, has3 = 0; for (j = 1; j < (int32_t)SQ_POLY_OUT && iv[j] >= 0; j++) if (iv[j] == 3 || iv[j] == 4) has3 = 1; if (has3) continue; }
        if (iv[k] >= lo && iv[k] <= hi) return iv[k];
        if (alt >= 0 && iv[k] == alt) return iv[k];
    }
    return -1;
}
static int32_t nearest_pc(int32_t note, int32_t pc)
{
    int32_t v = note - ((note - pc) % 12 + 12) % 12;          /* the pc at or under the note */
    if (note - v > 6) v += 12;
    while (v < 0) v += 12;
    while (v > 127) v -= 12;
    return v;
}
uint8_t sq_harm_apply_chord(uint8_t *notes, uint8_t n, uint8_t root, uint8_t scale, const sq_hchord_t *c, uint8_t chord)
{
    uint8_t hs = sq_harm_scale(scale), sh, i, j, m = 0u, out[SQ_POLY_OUT], have6 = 0u, have1 = 0u;
    int32_t deg, rt, lo = 127;
    sh = chord_shape(hs, c, &deg);
    if (!sh) return sq_harm_apply(notes, n, root, scale, (int8_t)deg, c->semi == 255u ? c->col : c->shape, chord);
    if (n > SQ_POLY_OUT) n = (uint8_t)SQ_POLY_OUT;
    rt = (int32_t)root + c->semi;
    for (i = 0; i < n; i++) {
        int32_t place, tone, v;
        uint8_t k, dup = 0u;
        if (notes[i] == SQ_NOTE_NONE) continue;
        place = ((sq_scale_index(notes[i], root, hs) % 7) + 7) % 7;
        tone = shape_tone(sh, place);
        if (tone < 0) tone = place == 6 || place == 1 || place == 3 || place == 5 ? shape_tone(sh, 4) : 0;   /* (none: the fifth, or the root) */
        if (tone < 0) tone = 7;
        if (place == 6) have6 = 1u;
        if (place == 1) have1 = 1u;
        v = nearest_pc(notes[i], (rt + tone) % 12);
        for (k = 0; k < m; k++) if (out[k] == v) dup = 1u;
        if (!dup) { out[m++] = (uint8_t)v; if (v < lo) lo = v; }
    }
    if (chord && m >= 3u && m < SQ_POLY_OUT) {                /* a chord: the shape's seventh or ninth on top, when it has one */
        int32_t t7 = shape_tone(sh, 6), t9 = shape_tone(sh, 1), hi = 0, add = -1;
        for (i = 0; i < m; i++) if (out[i] > hi) hi = out[i];
        if (t7 >= 0 && !have6) add = t7; else if (t9 >= 0 && !have1) add = t9;
        if (add >= 0) {
            int32_t v = nearest_pc(hi, (rt + add) % 12);
            while (v <= hi) v += 12;
            if (v <= 127) {
                for (j = 0; j < m && out[j] != v; j++) continue;
                if (j == m) out[m++] = (uint8_t)v;
            }
        }
    }
    for (i = 0; i < m; i++) notes[i] = out[i];
    for (i = m; i < n; i++) notes[i] = SQ_NOTE_NONE;
    (void)lo;
    return m;
}
uint8_t sq_hchord_quality(uint8_t scale, const sq_hchord_t *c, uint8_t *ext)
{
    uint8_t hs = sq_harm_scale(scale), sh;
    int32_t deg;
    *ext = 0u;
    sh = chord_shape(hs, c, &deg);
    if (!sh) {                                            /* the key's own: the scale says */
        int32_t iv[12], d = mod7(deg), third, fifth;
        uint8_t col = c->semi == 255u ? c->col : c->shape;
        scale_iv(hs, iv);
        third = ((iv[(d + 2) % 7] - iv[d]) % 12 + 12) % 12;
        fifth = ((iv[(d + 4) % 7] - iv[d]) % 12 + 12) % 12;
        if (col == SQ_HC_7) { int32_t sev = ((iv[(d + 6) % 7] - iv[d]) % 12 + 12) % 12; *ext = sev == 11 ? 3u : 1u; }
        if (col == SQ_HC_9) *ext = 4u;
        if (col == SQ_HC_SUS4 || col == SQ_HC_SUS2) return 4u;
        return fifth == 6 ? 2u : fifth == 8 ? 3u : third == 3 ? 1u : 0u;
    }
    {
        const int8_t *iv = CHORD_SEMI[sh];
        uint8_t k, q = 0u, three = 0u, fl = 0u;
        for (k = 1; k < SQ_POLY_OUT && iv[k] >= 0; k++) {
            if (iv[k] == 3) three = 1u;
            if (iv[k] == 4) three = 2u;
            if (iv[k] == 6) fl |= 1u;
            if (iv[k] == 8) fl |= 2u;
            if (iv[k] == 10) *ext |= 1u;
            if (iv[k] == 11) *ext |= 3u;
            if (iv[k] >= 13) *ext |= 4u;
        }
        if (!three) q = 4u;
        else if (fl & 1u) q = 2u;
        else if (fl & 2u) q = 3u;
        else q = three == 1u ? 1u : 0u;
        return q;
    }
}
/* a chord as a root and one of the 32 shapes, whatever it was written as (a step of the key with a colour: the notes the
 * key gives it, matched to the shape that has them) - how it goes to the Pi, which keeps progressions without a key */
void sq_hchord_explicit(uint8_t scale, const sq_hchord_t *c, uint8_t *semi, uint8_t *shape)
{
    uint8_t hs = sq_harm_scale(scale), sh, col, k, j, best = SQ_CH_MAJ, ext, q;
    int32_t deg, iv[12], want[SQ_POLY_OUT], nw = 0, d;
    *semi = sq_hchord_semi(scale, c);
    sh = chord_shape(hs, c, &deg);
    if (sh) { *shape = (uint8_t)(SQ_HSHAPE_CH + sh); return; }
    col = c->semi == 255u ? c->col : c->shape;
    scale_iv(hs, iv);
    d = mod7(deg);
#define REL(j) ((iv[(d + (j)) % 7] + 12 * ((d + (j)) / 7)) - iv[d])
    want[nw++] = 0;
    want[nw++] = col == SQ_HC_SUS4 ? REL(3) : col == SQ_HC_SUS2 ? REL(1) : REL(2);
    want[nw++] = REL(4);
    if (col == SQ_HC_6) want[nw++] = REL(5);
    if (col == SQ_HC_7 || col == SQ_HC_9) want[nw++] = REL(6);
    if (col == SQ_HC_9) want[nw++] = REL(1) + 12;
#undef REL
    for (k = 1; k < SQ_CH_COUNT; k++) {                 /* the shape with just these notes */
        uint8_t same = 1u, cnt = 0u;
        for (j = 0; j < SQ_POLY_OUT && CHORD_SEMI[k][j] >= 0; j++) cnt++;
        if (cnt != (uint8_t)nw) continue;
        for (j = 0; j < cnt && same; j++) {
            int32_t i2, hit = 0;
            for (i2 = 0; i2 < nw; i2++) if (want[i2] == CHORD_SEMI[k][j]) hit = 1;
            if (!hit) same = 0u;
        }
        if (same) { *shape = (uint8_t)(SQ_HSHAPE_CH + k); return; }
    }
    q = sq_hchord_quality(scale, c, &ext);              /* (none: the nearest by its kind) */
    if (q == 1u) best = ext & 4u ? SQ_CH_MIN9 : (ext & 1u) ? SQ_CH_MIN7 : SQ_CH_MIN;
    else if (q == 2u) best = (ext & 1u) ? SQ_CH_M7B5 : SQ_CH_DIM;
    else if (q == 3u) best = SQ_CH_AUG;
    else if (q == 4u) best = col == SQ_HC_SUS2 ? SQ_CH_SUS2 : SQ_CH_SUS4;
    else best = ext & 4u ? SQ_CH_9 : (ext & 2u) ? SQ_CH_MAJ7 : (ext & 1u) ? SQ_CH_7 : SQ_CH_MAJ;
    *shape = (uint8_t)(SQ_HSHAPE_CH + best);
}

static const char *const ROM[12] = {"I", "bII", "II", "bIII", "III", "IV", "#IV", "V", "bVI", "VI", "bVII", "VII"};
const char *sq_degree_name(uint8_t semi) { return ROM[semi % 12u]; }   /* 0.12: a root's name, semitones above the key's */
void sq_hchord_name(uint8_t scale, const sq_hchord_t *c, char *out)
{
    static const char *const SUF[SQ_CH_COUNT] = {"", "8", "5", "5", "", "", "o", "+", "sus2", "sus4", "6", "6", "7", "7",
        "maj7", "mM7", "o7", "m7b5", "7sus4", "add9", "add9", "9", "9", "maj9", "9sus4", "6/9", "6/9", "11", "13", "7sh", "sh", ""};
    uint8_t hs = sq_harm_scale(scale), sh, semi, ext, q, k = 0u;
    int32_t deg;
    const char *a, *b;
    sh = chord_shape(hs, c, &deg);
    if (!sh) { sq_harm_chord_name(scale, (int8_t)deg, c->semi == 255u ? c->col : c->shape, out); return; }
    semi = c->semi % 12u;
    q = sq_hchord_quality(scale, c, &ext);
    for (a = ROM[semi]; *a && k < 11u; a++) {
        char ch = *a;
        if ((q == 1u || q == 2u) && ch >= 'A' && ch <= 'Z') ch = (char)(ch - 'A' + 'a');   /* minor, diminished: small */
        out[k++] = ch;
    }
    for (b = SUF[sh]; *b && k < 11u; b++) out[k++] = *b;
    out[k] = 0;
}

const char *sq_mood_name(uint8_t m)
{
    static const char *const N[SQ_MOODS] = {"ANY", "SAD", "MELANCHOLY", "SATISFYING", "ENERGETIC", "EUPHORIC", "EPIC",
                                            "DREAMY", "DARK", "TENSE", "SUSPENDED"};
    return N[m < SQ_MOODS ? m : 0u];
}
/* what a progression is, scored for each mood; the highest wins (ties: the earlier mood) */
uint8_t sq_hprog_mood(const sq_hprog_t *h, uint8_t scale)
{
    int32_t sc[SQ_MOODS], minor = 0, major = 0, sus = 0, dim = 0, colour = 0, k, best = SQ_MOOD_SAD, roots = 0, fast = 0;
    uint8_t semis[SQ_HPROG_MAX], q[SQ_HPROG_MAX], seen = 0u, key_minor;
    uint16_t rootmask = 0u;
    int32_t nc = h->nc ? h->nc : h->n;                       /* (one round of the chords) */
    if (!nc) return SQ_MOOD_ANY;
    for (k = 0; k < SQ_MOODS; k++) sc[k] = 0;
    key_minor = (uint8_t)(((sq_scale_mask(scale) >> 3) & 1u) && !((sq_scale_mask(scale) >> 4) & 1u));
    if (scale == SQ_SC_CHROMATIC) key_minor = 1u;
    for (k = 0; k < nc; k++) {
        uint8_t ext;
        semis[k] = sq_hchord_semi(scale, &h->c[k]);
        q[k] = sq_hchord_quality(scale, &h->c[k], &ext);
        if (q[k] == 1u) minor++; else if (q[k] == 0u) major++; else if (q[k] == 4u) sus++; else dim++;
        if (ext & 6u) colour++;
        if (!((rootmask >> semis[k]) & 1u)) { rootmask |= (uint16_t)(1u << semis[k]); roots++; }
        if (h->dur[k] && h->dur[k] <= 8u) fast++;
        (void)seen;
    }
    if (roots <= 1) { sc[SQ_MOOD_DARK] += 6; sc[SQ_MOOD_TENSE] += 2; }
    if (key_minor) { sc[SQ_MOOD_SAD] += 2 + minor; sc[SQ_MOOD_MELANCHOLY] += 1 + minor; sc[SQ_MOOD_DARK] += 1; }
    else { sc[SQ_MOOD_EUPHORIC] += 2 + major; sc[SQ_MOOD_SATISFYING] += 1 + major; sc[SQ_MOOD_ENERGETIC] += major; }
    if ((rootmask & (1u << 8)) && (rootmask & (1u << 10))) sc[SQ_MOOD_EPIC] += 6;             /* the bVI and the bVII */
    else if (rootmask & (1u << 8)) { sc[SQ_MOOD_EPIC] += 2; sc[SQ_MOOD_SAD] += 2; }
    if (rootmask & (1u << 1)) { sc[SQ_MOOD_DARK] += 4; sc[SQ_MOOD_TENSE] += 3; }              /* the bII (phrygian) */
    if (rootmask & (1u << 6)) sc[SQ_MOOD_TENSE] += 5;                                         /* the tritone */
    if (dim) sc[SQ_MOOD_TENSE] += 3 * dim;
    if (sus) sc[SQ_MOOD_SUSPENDED] += 4 * sus;
    if (colour) { sc[SQ_MOOD_DREAMY] += 3 * colour; sc[SQ_MOOD_MELANCHOLY] += colour; }
    if (fast) { sc[SQ_MOOD_ENERGETIC] += 3 * fast; }
    for (k = 0; k + 1 < nc; k++) {                                                 /* V to I, the cadence */
        if (semis[k] == 7u && semis[k + 1] == 0u) { sc[SQ_MOOD_SATISFYING] += 5; if (q[k] == 0u && key_minor) sc[SQ_MOOD_EPIC] += 1; }
        if (semis[k] == 5u && semis[k + 1] == 0u) sc[SQ_MOOD_SATISFYING] += 2;               /* the plagal one */
    }
    if (nc >= 2 && semis[nc - 1] == 7u && semis[0] == 0u) sc[SQ_MOOD_SATISFYING] += 3;    /* round: V back to I */
    if (!key_minor && (rootmask & (1u << 9)) && (rootmask & (1u << 5)) && (rootmask & (1u << 7))) sc[SQ_MOOD_EUPHORIC] += 5;   /* I V vi IV */
    if (key_minor && (rootmask & (1u << 5)) && !(rootmask & (1u << 8)) && major && !(rootmask & (1u << 10))) sc[SQ_MOOD_MELANCHOLY] += 3;   /* the dorian IV */
    if (key_minor && (rootmask & (1u << 3)) && (rootmask & (1u << 10)) && (rootmask & (1u << 8))) sc[SQ_MOOD_MELANCHOLY] += 2;
    if (!key_minor && minor >= 2) sc[SQ_MOOD_MELANCHOLY] += 2;
    for (k = SQ_MOOD_SAD; k < SQ_MOODS; k++) if (sc[k] > sc[best]) best = k;
    return (uint8_t)best;
}

/* DICE PROG's shapes: per mood, rows of {root (semitones above the key's), chord shape}; 255 ends a row */
typedef struct { uint8_t semi, shape; } dice_chord_t;
static const dice_chord_t DICE_PROGS[SQ_MOODS - 1u][3][5] = {
    /* SAD */        {{{0, SQ_CH_MIN}, {8, SQ_CH_MAJ}, {3, SQ_CH_MAJ}, {10, SQ_CH_MAJ}, {255, 0}}, {{0, SQ_CH_MIN}, {5, SQ_CH_MIN}, {8, SQ_CH_MAJ}, {7, SQ_CH_MIN}, {255, 0}}, {{0, SQ_CH_MIN}, {5, SQ_CH_MIN}, {0, SQ_CH_MIN}, {7, SQ_CH_MIN}, {255, 0}}},
    /* MELANCHOLY */ {{{0, SQ_CH_MIN7}, {5, SQ_CH_MAJ}, {0, SQ_CH_MIN7}, {5, SQ_CH_MAJ}, {255, 0}}, {{0, SQ_CH_MIN9}, {3, SQ_CH_MAJ7}, {10, SQ_CH_MAJ}, {5, SQ_CH_MIN7}, {255, 0}}, {{9, SQ_CH_MIN7}, {5, SQ_CH_MAJ7}, {0, SQ_CH_MAJ}, {7, SQ_CH_MAJ}, {255, 0}}},
    /* SATISFYING */ {{{0, SQ_CH_MAJ}, {5, SQ_CH_MAJ}, {7, SQ_CH_MAJ}, {0, SQ_CH_MAJ}, {255, 0}}, {{2, SQ_CH_MIN7}, {7, SQ_CH_7}, {0, SQ_CH_MAJ7}, {0, SQ_CH_MAJ7}, {255, 0}}, {{0, SQ_CH_MIN}, {5, SQ_CH_MIN}, {7, SQ_CH_7}, {0, SQ_CH_MIN}, {255, 0}}},
    /* ENERGETIC */  {{{0, SQ_CH_MIN}, {10, SQ_CH_MAJ}, {8, SQ_CH_MAJ}, {10, SQ_CH_MAJ}, {255, 0}}, {{0, SQ_CH_POWER}, {3, SQ_CH_POWER}, {5, SQ_CH_POWER}, {3, SQ_CH_POWER}, {255, 0}}, {{0, SQ_CH_MAJ}, {7, SQ_CH_MAJ}, {9, SQ_CH_MIN}, {5, SQ_CH_MAJ}, {255, 0}}},
    /* EUPHORIC */   {{{0, SQ_CH_MAJ}, {7, SQ_CH_MAJ}, {9, SQ_CH_MIN}, {5, SQ_CH_MAJ}, {255, 0}}, {{9, SQ_CH_MIN}, {5, SQ_CH_MAJ}, {0, SQ_CH_MAJ}, {7, SQ_CH_MAJ}, {255, 0}}, {{5, SQ_CH_MAJ}, {7, SQ_CH_MAJ}, {9, SQ_CH_MIN}, {0, SQ_CH_MAJ}, {255, 0}}},
    /* EPIC */       {{{0, SQ_CH_MIN}, {8, SQ_CH_MAJ}, {10, SQ_CH_MAJ}, {0, SQ_CH_MIN}, {255, 0}}, {{8, SQ_CH_MAJ}, {10, SQ_CH_MAJ}, {0, SQ_CH_MIN}, {0, SQ_CH_MIN}, {255, 0}}, {{0, SQ_CH_MIN}, {3, SQ_CH_MAJ}, {10, SQ_CH_MAJ}, {8, SQ_CH_MAJ}, {255, 0}}},
    /* DREAMY */     {{{0, SQ_CH_MAJ7}, {5, SQ_CH_MAJ7}, {255, 0}}, {{0, SQ_CH_MAJ9}, {9, SQ_CH_MIN9}, {5, SQ_CH_MAJ7}, {4, SQ_CH_MIN7}, {255, 0}}, {{0, SQ_CH_MIN9}, {5, SQ_CH_9}, {255, 0}}},
    /* DARK */       {{{0, SQ_CH_MIN}, {255, 0}}, {{0, SQ_CH_MIN}, {1, SQ_CH_MAJ}, {255, 0}}, {{0, SQ_CH_MIN}, {0, SQ_CH_MIN}, {8, SQ_CH_MAJ}, {1, SQ_CH_MAJ}, {255, 0}}},
    /* TENSE */      {{{0, SQ_CH_MIN}, {6, SQ_CH_DIM}, {255, 0}}, {{0, SQ_CH_MIN}, {1, SQ_CH_MAJ}, {6, SQ_CH_M7B5}, {7, SQ_CH_7}, {255, 0}}, {{0, SQ_CH_DIM7}, {3, SQ_CH_DIM7}, {255, 0}}},
    /* SUSPENDED */  {{{0, SQ_CH_SUS2}, {5, SQ_CH_SUS2}, {255, 0}}, {{0, SQ_CH_SUS4}, {10, SQ_CH_SUS2}, {5, SQ_CH_SUS4}, {7, SQ_CH_7SUS4}, {255, 0}}, {{0, SQ_CH_9SUS4}, {8, SQ_CH_SUS2}, {255, 0}}},
};
void sq_uprog_dice(sq_uprog_t *u, uint8_t mood, uint8_t minor_key, uint8_t rhythm, uint32_t *rng)
{
    const dice_chord_t *row;
    uint8_t m = mood, n = 0u, k, rot;
    if (m == SQ_MOOD_ANY || m >= SQ_MOODS) m = (uint8_t)(1u + sq_rng_next(rng) % (SQ_MOODS - 1u));
    row = DICE_PROGS[m - 1u][sq_rng_next(rng) % 3u];
    while (n < 5u && row[n].semi != 255u) n++;
    sq_uprog_default(u);
    rot = (uint8_t)(n > 2u && sq_rng_next(rng) % 3u == 0u ? sq_rng_next(rng) % n : 0u);   /* now and then from another chord */
    for (k = 0; k < n; k++) {
        const dice_chord_t *c = &row[(k + rot) % n];
        uint8_t semi = c->semi, sh = c->shape;
        if (!minor_key && m <= SQ_MOOD_MELANCHOLY && semi == 0u && sh == SQ_CH_MIN) sh = SQ_CH_MIN;   /* (a sad one stays minor) */
        if (sq_rng_next(rng) % 4u == 0u) {               /* a colour now and then */
            if (sh == SQ_CH_MIN) sh = sq_rng_next(rng) & 1u ? SQ_CH_MIN7 : SQ_CH_MADD9;
            else if (sh == SQ_CH_MAJ) sh = m == SQ_MOOD_DREAMY ? SQ_CH_MAJ9 : (sq_rng_next(rng) & 1u ? SQ_CH_MAJ7 : SQ_CH_ADD9);
        }
        u->semi[k] = semi;
        u->shape[k] = (uint8_t)(SQ_HSHAPE_CH + sh);
        u->deg[k] = 0; u->col[k] = SQ_HC_TRIAD;
    }
    u->n = n;
    u->bars = n <= 2u ? 2u : 1u;
    if (rhythm == SQ_HR_BARS && sq_rng_next(rng) % 4u == 0u)   /* a turn of the last chord, half as long, now and then */
        for (k = 0; k < n; k++) u->dur[k] = (uint8_t)(k + 1u == n ? 8u : 16u * u->bars);
    u->mood = m;
}

/* ------------------------------------------------------------------ 0.8 EVOLVE with the theory */

/* the tone of the tonic chord (steps 0, 2, 4 of the scale; 0 and 4 for a bass) nearest to `ref` */
static uint8_t chord_tone_near(uint8_t ref, uint8_t root, uint8_t hs, uint8_t bass, uint32_t pick)
{
    static const int8_t TONES[3] = {0, 2, 4};
    int32_t ri = sq_scale_index(ref, root, hs), base = ri - mod7(ri), best = -1, bd = 1000, o, k;
    if (bass) {                                          /* a bass: the root, now and then the fifth */
        int32_t t = (pick % 100u) < 72u ? 0 : 4;
        for (o = -1; o <= 1; o++) {
            int32_t v = sq_scale_at(base + 7 * o + t, root, hs), dd = v - (int32_t)ref;
            if (dd < 0) dd = -dd;
            if (dd < bd) { bd = dd; best = v; }
        }
        return (uint8_t)best;
    }
    for (o = -1; o <= 1; o++)
        for (k = 0; k < 3; k++) {
            int32_t v = sq_scale_at(base + 7 * o + TONES[k], root, hs), dd = v - (int32_t)ref;
            if (dd < 0) dd = -dd;
            if (dd && (pick % 3u) == (uint32_t)k) dd -= 1;   /* (a little variety between equally near tones) */
            if (dd < bd) { bd = dd; best = v; }
        }
    return (uint8_t)best;
}

void sq_row_evolve_notes(sq_step_t *row, uint8_t len, uint8_t amount, uint8_t root, uint8_t scale, uint8_t bass,
                         uint8_t center, uint32_t *rng)
{
    uint8_t ks = pent_or(scale), hs = sq_harm_scale(scale), prev = SQ_NOTE_NONE;
    uint32_t i, n;
    if (len > SQ_STEPS) len = (uint8_t)SQ_STEPS;
    if (amount > 100u) amount = 100u;
    if (center > 115u || center < 12u) center = 60u;
    for (i = 0; i < len; i++) {
        sq_step_t *s = &row[i];
        uint8_t cnt = 0u, strong = (i & 3u) == 0u, v;
        for (n = 0; n < SQ_POLY; n++) if (s->note[n] != SQ_NOTE_NONE) cnt++;
        if (!(s->flags & SQ_STEP_ON) || !(s->flags & SQ_STEP_SET) || !cnt) continue;
        if ((s->flags & SQ_STEP_LOCK) || pct(rng) >= amount) {
            if (cnt == 1u) prev = s->note[0];
            continue;
        }
        if (cnt >= 2u) {                                 /* a chord: the next inversion towards the centre */
            uint8_t lo = 0u, hi = 0u;
            if (pct(rng) >= 40u) continue;
            for (n = 0; n < SQ_POLY; n++) {
                if (s->note[n] == SQ_NOTE_NONE) continue;
                if (s->note[lo] == SQ_NOTE_NONE || s->note[n] < s->note[lo]) lo = (uint8_t)n;
                if (s->note[hi] == SQ_NOTE_NONE || s->note[n] > s->note[hi]) hi = (uint8_t)n;
            }
            if (s->note[lo] < center && s->note[lo] <= 115u) s->note[lo] = (uint8_t)(s->note[lo] + 12u);
            else if (s->note[hi] >= 12u) s->note[hi] = (uint8_t)(s->note[hi] - 12u);
            for (n = 1; n < SQ_POLY; n++) {
                uint32_t k;
                for (k = 0; k < n; k++) if (s->note[n] != SQ_NOTE_NONE && s->note[k] == s->note[n]) s->note[n] = SQ_NOTE_NONE;
            }
            continue;
        }
        {
            uint8_t ref = prev != SQ_NOTE_NONE ? prev : s->note[0];
            if (bass) {
                if (strong) v = chord_tone_near(s->note[0], root, hs, 1u, sq_rng_next(rng));
                else {
                    uint32_t r = pct(rng);
                    if (r < 30u) v = (uint8_t)(ref + 12u <= 127u && ref < center ? ref + 12u : ref >= 12u ? ref - 12u : ref);
                    else if (r < 75u) v = sq_scale_degree(ref, root, ks, (sq_rng_next(rng) & 1u) ? 1 : -1);   /* walking */
                    else v = chord_tone_near(ref, root, hs, 1u, 0u);
                }
            } else if (strong) v = chord_tone_near(ref, root, hs, 0u, sq_rng_next(rng));
            else {
                int32_t step = pct(rng) < 72u ? 1 : 2, dir = (sq_rng_next(rng) & 1u) ? 1 : -1;
                if ((int32_t)ref > (int32_t)center + 5) dir = -1;                  /* back towards the centre */
                else if ((int32_t)ref < (int32_t)center - 5) dir = 1;
                v = pct(rng) < 6u ? ref : sq_scale_degree(ref, root, ks, dir * step);
            }
            if (prev != SQ_NOTE_NONE) {                  /* a leap of more than a fifth comes back by an octave */
                while ((int32_t)v - (int32_t)prev > 7 && v >= 12u) v = (uint8_t)(v - 12u);
                while ((int32_t)prev - (int32_t)v > 7 && v <= 115u) v = (uint8_t)(v + 12u);
            }
            s->note[0] = v;
            prev = v;
        }
    }
}

uint32_t sq_project_bake_scale(sq_project_t *p)
{
    uint32_t t, pat, i, n, k, changed = 0u;
    for (t = 0; t < SQ_TRACKS; t++) {
        if (!(p->track[t].flags & SQ_TF_SCALE)) continue;
        for (pat = 0; pat < SQ_PATTERNS; pat++)
            for (i = 0; i < SQ_STEPS; i++) {
                sq_step_t *s = &p->step[t][pat][i];
                for (n = 0; n < SQ_POLY; n++) {
                    uint8_t v;
                    if (s->note[n] == SQ_NOTE_NONE) continue;
                    v = sq_scale_apply(s->note[n], p->key_root, p->key_scale, p->key_shift);
                    for (k = 0; k < n; k++) if (s->note[k] == v) { v = SQ_NOTE_NONE; break; }   /* two notes became one */
                    if (v != s->note[n]) { s->note[n] = v; changed++; }
                }
            }
    }
    p->key_shift = 0;
    return changed;
}

/* ------------------------------------------------------------------ names */

void sq_note_name(uint8_t note, char *out)
{
    static const char N[12][3] = {"C ", "C#", "D ", "D#", "E ", "F ", "F#", "G ", "G#", "A ", "A#", "B "};
    int32_t oct;
    uint32_t k = 0;
    if (note > 127u) { out[0] = '-'; out[1] = '-'; out[2] = '-'; out[3] = 0; return; }
    out[k++] = N[note % 12u][0];
    if (N[note % 12u][1] != ' ') out[k++] = N[note % 12u][1];
    oct = (int32_t)(note / 12u) - 1;
    if (oct < 0) { out[k++] = '-'; oct = -oct; }
    out[k++] = (char)('0' + oct);
    out[k] = 0;
}

/* ------------------------------------------------------------------ saved projects */

uint32_t sq_crc32(const uint8_t *p, uint32_t n)
{
    uint32_t c = 0xFFFFFFFFu, k;
    while (n--) {
        c ^= *p++;
        for (k = 0; k < 8u; k++) c = c & 1u ? (c >> 1) ^ 0xEDB88320u : c >> 1;
    }
    return ~c;
}

typedef struct { uint8_t *p; uint32_t pos, cap; int bad; } wr_t;
static void wr_put(wr_t *w, const void *src, uint32_t n)
{
    if (w->bad || w->pos + n > w->cap) { w->bad = 1; return; }
    bcopy_(w->p + w->pos, src, n);
    w->pos += n;
}

typedef struct { const uint8_t *p; uint32_t pos, len; int bad; } rd_t;
static void rd_get(rd_t *r, void *dst, uint32_t n)
{
    if (r->bad || r->pos + n > r->len) { r->bad = 1; return; }
    bcopy_(dst, r->p + r->pos, n);
    r->pos += n;
}

/* a step is written as the bytes that differ from an empty step: a 24-bit mask (bit k = byte k, low byte first), then
 * those bytes. A hit is ~7 bytes instead of 18. */
typedef char sq_step_is_18_bytes[(sizeof(sq_step_t) == 18u) ? 1 : -1];
typedef char sq_track_size[(sizeof(sq_track_cfg_t) == 96u) ? 1 : -1];
typedef char sq_algo_size[(sizeof(sq_algo_t) == 4u) ? 1 : -1];
typedef char sq_ext_size[(sizeof(sq_ext_t) == 1508u && sizeof(sq_ext_t) % 4u == 0u && __builtin_offsetof(sq_ext_t, name) == SQ_EXT_014 &&
                          __builtin_offsetof(sq_ext_t, mfxc) == SQ_EXT_018 && __builtin_offsetof(sq_ext_t, mfxd) == SQ_EXT_019) ? 1 : -1];
typedef char sq_mfxc_size[(sizeof(sq_mfxc_t) == 13u && sizeof(sq_mfxd_t) == 25u && sizeof(sq_lfoe_t) == 4u && sizeof(sq_mod_t) == 5u) ? 1 : -1];
typedef char sq_snap_head_size[(sizeof(sq_snap_t) == SQ_SNAP_HEAD + SQ_TRACKS * sizeof(sq_track_cfg_t) +
                                SQ_LFOS * sizeof(sq_lfo_t) + SQ_SNAP_CC * sizeof(sq_ccv_t)) ? 1 : -1];

static void wr_step(wr_t *w, const sq_step_t *s, const sq_step_t *def)
{
    const uint8_t *a = (const uint8_t *)s, *d = (const uint8_t *)def;
    uint32_t k, m = 0u;
    uint8_t mb[3];
    for (k = 0; k < sizeof *s; k++) if (a[k] != d[k]) m |= 1u << k;
    mb[0] = (uint8_t)(m & 0xFFu); mb[1] = (uint8_t)((m >> 8) & 0xFFu); mb[2] = (uint8_t)(m >> 16);
    wr_put(w, mb, 3);
    for (k = 0; k < sizeof *s; k++) if (m & (1u << k)) wr_put(w, &a[k], 1);
}
static void rd_step(rd_t *r, sq_step_t *s, const sq_step_t *def)
{
    uint8_t mb[3] = {0, 0, 0}, *a = (uint8_t *)s;
    uint32_t k, m;
    rd_get(r, mb, 3);
    m = (uint32_t)mb[0] | ((uint32_t)mb[1] << 8) | ((uint32_t)mb[2] << 16);
    *s = *def;
    for (k = 0; k < sizeof *s; k++) if (m & (1u << k)) rd_get(r, &a[k], 1);
}
static void rd_skip(rd_t *r, uint32_t n)
{
    if (r->bad || r->pos + n > r->len) { r->bad = 1; return; }
    r->pos += n;
}
/* a track's settings: all of them, or the 80 bytes a 0.10 image holds (what came after is left as it was: defaults) */
static void rd_track(rd_t *r, sq_track_cfg_t *c, uint8_t old)
{
    uint32_t n;
    if (!old) { rd_get(r, c, sizeof *c); return; }
    rd_get(r, c, SQ_TRACK_CFG_A);
    for (n = 0; n < SQ_ALGO_SLOTS - 1u; n++) sq_algo_slot_default(&c->algo2[n], SQ_ALGO_OFF);
    c->src_genre = 255u;
    c->follow_mode = SQ_FM_HOLD;
    c->brk_chop = 0u; c->brk_cfg = SQ_BRK_DEFAULT;
}
/* 0.11: the player's progressions and the generators' settings of a 0.10 image: the bytes it has, the rest new */
static void rd_uprogs(rd_t *r, sq_uprog_t *u, uint8_t old)
{
    uint32_t i;
    if (!old) { rd_get(r, u, (uint32_t)sizeof(sq_uprog_t) * SQ_UPROG_SLOTS); return; }
    for (i = 0; i < SQ_UPROG_SLOTS; i++) {
        sq_uprog_default(&u[i]);
        if (i < SQ_UPROGS) { rd_get(r, &u[i], SQ_UPROG_A); sq_uprog_tail_default(&u[i]); }
    }
}
static void rd_gen(rd_t *r, sq_gen_t *g, uint8_t old)
{
    uint32_t i;
    if (!old) { rd_get(r, g, sizeof *g); return; }
    rd_get(r, g, SQ_GEN_A);
    g->harm_rhythm = SQ_HR_BARS; g->harm_mood = SQ_MOOD_ANY;
    for (i = 0; i < sizeof g->reserved11; i++) g->reserved11[i] = 0u;
}

/* SGQA (0.10): the project's settings at their sizes, the snapshots (a track or the LFOs equal to the project's are
 * not written again), the patterns, sparse, the tape events, then the chunks (none yet: the end mark). */
uint32_t sq_serialize(const sq_project_t *p, uint8_t *out, uint32_t cap)
{
    wr_t w;
    sq_step_t def;
    uint32_t magic = SQ_SAVE_MAGIC, t, pat, i, n;
    uint8_t b, smask = 0u, nb[2];
    w.p = out; w.pos = 0; w.cap = cap; w.bad = 0;
    sq_step_default(&def);
    wr_put(&w, &magic, 4);
    wr_put(&w, &p->id, 4);
    wr_put(&w, &p->bpm, 2);
    b = p->clock_mode; wr_put(&w, &b, 1);
    wr_put(&w, &p->key_root, 1);
    wr_put(&w, &p->key_scale, 1);
    wr_put(&w, &p->key_shift, 1);
    wr_put(&w, &p->key_cur, 1);
    wr_put(&w, p->key, sizeof p->key);
    wr_put(&w, p->device, sizeof p->device);
    wr_put(&w, p->uprog, sizeof p->uprog);
    wr_put(&w, p->track, sizeof p->track);
    wr_put(&w, p->scene, sizeof p->scene);
    wr_put(&w, p->lfo, sizeof p->lfo);
    wr_put(&w, &p->gen, sizeof p->gen);
    wr_put(&w, &p->song, sizeof p->song);
    wr_put(&w, &p->live, sizeof p->live);
    wr_put(&w, &p->viaggio, sizeof p->viaggio);
    wr_put(&w, p->tape_cnt, sizeof p->tape_cnt);
    for (i = 0; i < SQ_SNAPS; i++) if (p->snap[i].used) smask |= (uint8_t)(1u << i);
    wr_put(&w, &smask, 1);
    for (i = 0; i < SQ_SNAPS; i++) {
        const sq_snap_t *sn = &p->snap[i];
        uint8_t tm[2] = {0, 0}, lf;
        if (!(smask & (1u << i))) continue;
        wr_put(&w, sn, SQ_SNAP_HEAD);
        for (t = 0; t < SQ_TRACKS; t++) if (bdiff_(&sn->track[t], &p->track[t], sizeof p->track[0])) tm[t >> 3] |= (uint8_t)(1u << (t & 7u));
        wr_put(&w, tm, 2);
        for (t = 0; t < SQ_TRACKS; t++) if (tm[t >> 3] & (1u << (t & 7u))) wr_put(&w, &sn->track[t], sizeof sn->track[t]);
        lf = (uint8_t)bdiff_(sn->lfo, p->lfo, sizeof p->lfo);
        wr_put(&w, &lf, 1);
        if (lf) wr_put(&w, sn->lfo, sizeof sn->lfo);
        wr_put(&w, sn->cc, (uint32_t)(sn->ccn <= SQ_SNAP_CC ? sn->ccn : 0u) * (uint32_t)sizeof(sq_ccv_t));
    }
    for (t = 0; t < SQ_TRACKS; t++) {
        uint8_t pmask = 0u;
        for (pat = 0; pat < SQ_PATTERNS; pat++)
            for (i = 0; i < SQ_STEPS; i++)
                if (bdiff_(&p->step[t][pat][i], &def, sizeof def)) { pmask |= (uint8_t)(1u << pat); break; }
        wr_put(&w, &pmask, 1);
        for (pat = 0; pat < SQ_PATTERNS; pat++) {
            uint8_t m[8] = {0, 0, 0, 0, 0, 0, 0, 0};
            if (!(pmask & (1u << pat))) continue;
            for (i = 0; i < SQ_STEPS; i++)
                if (bdiff_(&p->step[t][pat][i], &def, sizeof def)) m[i >> 3] |= (uint8_t)(1u << (i & 7u));
            wr_put(&w, m, 8);
            for (i = 0; i < SQ_STEPS; i++)
                if (m[i >> 3] & (1u << (i & 7u))) wr_step(&w, &p->step[t][pat][i], &def);
        }
    }
    n = p->tape_n > SQ_TAPE_MAX ? SQ_TAPE_MAX : p->tape_n;             /* the tapes' events */
    nb[0] = (uint8_t)(n & 0xFFu); nb[1] = (uint8_t)(n >> 8);
    wr_put(&w, nb, 2);
    if (n) wr_put(&w, p->tape_ev, n * sizeof(sq_tape_ev_t));
    {   /* 0.13: chunk 1, sq_ext_t, when it is not the default (a 0.12 project's image stays as 0.12 wrote it) */
        sq_ext_t xd;
        sq_ext_default(&xd);
        if (bdiff_(&p->ext, &xd, sizeof xd)) {
            uint8_t h[3] = {SQ_CHUNK_EXT, (uint8_t)(sizeof xd & 0xFFu), (uint8_t)(sizeof xd >> 8)};
            wr_put(&w, h, 3);
            wr_put(&w, &p->ext, sizeof p->ext);
        }
    }
    {   /* 0.23: chunk 2, the THEORY block, when it says something: the source, the seed, the patterns the engines made */
        uint32_t n = 0u, tk, pk;
        for (tk = 0; tk < SQ_TRACKS; tk++) for (pk = 0; pk < SQ_PATTERNS; pk++) if (p->th.pat[tk][pk].style) n++;
        if (n || p->th.src || p->th.seed) {
            uint32_t len = 4u + n * (2u + (uint32_t)sizeof(sq_thpat_t));
            uint8_t h[7];
            h[0] = SQ_CHUNK_TH; h[1] = (uint8_t)(len & 0xFFu); h[2] = (uint8_t)(len >> 8);
            h[3] = p->th.src; h[4] = (uint8_t)(p->th.seed & 0xFFu); h[5] = (uint8_t)(p->th.seed >> 8); h[6] = (uint8_t)n;
            wr_put(&w, h, 7);
            for (tk = 0; tk < SQ_TRACKS; tk++)
                for (pk = 0; pk < SQ_PATTERNS; pk++) {
                    uint8_t at[2];
                    if (!p->th.pat[tk][pk].style) continue;
                    at[0] = (uint8_t)tk; at[1] = (uint8_t)pk;
                    wr_put(&w, at, 2);
                    wr_put(&w, &p->th.pat[tk][pk], sizeof(sq_thpat_t));
                }
        }
    }
    b = 0u; wr_put(&w, &b, 1);                        /* the end of the chunks */
    return w.bad ? 0u : w.pos;
}

/* SGQB / SGQA reader: the whole project, or one track and pattern for RELOAD. */
static int sq_parse(const uint8_t *in, uint32_t len, sq_project_t *p, uint8_t want_t, uint8_t want_pat,
                    sq_track_cfg_t *cfg, sq_step_t *row, sq_thpat_t *th)
{
    rd_t r;
    sq_step_t def, tmp;
    uint32_t magic = 0, t, pat, i, ev, ext_n = 0u;
    uint8_t b = 0, smask = 0u, nb[2] = {0u, 0u}, old;
    r.p = in; r.pos = 0; r.len = len; r.bad = 0;
    sq_step_default(&def);
    rd_get(&r, &magic, 4);
    if (r.bad || (magic != SQ_SAVE_MAGIC && magic != SQ_SAVE_MAGICA)) return -1;
    old = magic == SQ_SAVE_MAGICA ? 1u : 0u;          /* a 0.10 image: what SGQB keeps in its reserved bytes is made up */

    if (p) {
        sq_project_init(p);
        rd_get(&r, &p->id, 4);
        rd_get(&r, &p->bpm, 2);
        rd_get(&r, &b, 1); p->clock_mode = b;
        rd_get(&r, &p->key_root, 1);
        rd_get(&r, &p->key_scale, 1);
        rd_get(&r, &p->key_shift, 1);
        rd_get(&r, &p->key_cur, 1);
        rd_get(&r, p->key, sizeof p->key);
        rd_get(&r, p->device, sizeof p->device);
        rd_uprogs(&r, p->uprog, old);
        for (t = 0; t < SQ_TRACKS; t++) rd_track(&r, &p->track[t], old);
        rd_get(&r, p->scene, sizeof p->scene);
        rd_get(&r, p->lfo, sizeof p->lfo);
        rd_gen(&r, &p->gen, old);
        rd_get(&r, &p->song, sizeof p->song);
        rd_get(&r, &p->live, sizeof p->live);
        rd_get(&r, &p->viaggio, sizeof p->viaggio);
        rd_get(&r, p->tape_cnt, sizeof p->tape_cnt);
        if (old) { p->gen.harm_genre = p->gen.genre; p->gen.harm_lock = 0u; }   /* 0.10: one genre for all */
    } else {
        rd_skip(&r, 4u + 2u + 1u + 4u + (uint32_t)sizeof(p->key) + (uint32_t)sizeof(p->device) + (old ? SQ_UPROG_A * SQ_UPROGS : (uint32_t)sizeof(p->uprog)));
        for (t = 0; t < SQ_TRACKS; t++) {
            if (cfg && t == want_t) { sq_track_default(cfg, t); rd_track(&r, cfg, old); }
            else rd_skip(&r, old ? SQ_TRACK_CFG_A : (uint32_t)sizeof(sq_track_cfg_t));
        }
        rd_skip(&r, SQ_SCENES * (uint32_t)sizeof(sq_scene_t) + SQ_LFOS * (uint32_t)sizeof(sq_lfo_t));
        rd_skip(&r, (old ? SQ_GEN_A : (uint32_t)sizeof(sq_gen_t)) + (uint32_t)sizeof(sq_song_t) + (uint32_t)sizeof(sq_live_t) +
                    (uint32_t)sizeof(sq_viaggio_t) + SQ_TRACKS * 2u);
    }
    rd_get(&r, &smask, 1);
    for (i = 0; i < SQ_SNAPS && !r.bad; i++) {
        uint8_t head[SQ_SNAP_HEAD], tm[2] = {0, 0}, lf = 0u;
        sq_snap_t *sn = p ? &p->snap[i] : 0;
        if (!(smask & (1u << i))) continue;
        rd_get(&r, head, SQ_SNAP_HEAD);
        if (r.bad || head[1] > SQ_SNAP_CC) return -2;   /* (head[1]: the CC values that follow) */
        if (sn) {
            bcopy_(sn, head, SQ_SNAP_HEAD);
            if (old) sn->harm_genre = sn->genre;
            for (t = 0; t < SQ_TRACKS; t++) sn->track[t] = p->track[t];
            bcopy_(sn->lfo, p->lfo, sizeof p->lfo);
        }
        rd_get(&r, tm, 2);
        for (t = 0; t < SQ_TRACKS; t++) {
            if (!(tm[t >> 3] & (1u << (t & 7u)))) continue;
            if (sn) rd_track(&r, &sn->track[t], old); else rd_skip(&r, old ? SQ_TRACK_CFG_A : (uint32_t)sizeof(sq_track_cfg_t));
        }
        rd_get(&r, &lf, 1);
        if (lf) { if (sn) rd_get(&r, sn->lfo, sizeof sn->lfo); else rd_skip(&r, SQ_LFOS * (uint32_t)sizeof(sq_lfo_t)); }
        if (sn) rd_get(&r, sn->cc, (uint32_t)head[1] * (uint32_t)sizeof(sq_ccv_t));
        else rd_skip(&r, (uint32_t)head[1] * (uint32_t)sizeof(sq_ccv_t));
    }
    if (row) for (i = 0; i < SQ_STEPS; i++) row[i] = def;
    for (t = 0; t < SQ_TRACKS && !r.bad; t++) {
        uint8_t pmask = 0u;
        rd_get(&r, &pmask, 1);
        for (pat = 0; pat < SQ_PATTERNS && !r.bad; pat++) {
            uint8_t m[8];
            if (!(pmask & (1u << pat))) continue;
            rd_get(&r, m, 8);
            for (i = 0; i < SQ_STEPS && !r.bad; i++) {
                sq_step_t *dst;
                if (!(m[i >> 3] & (1u << (i & 7u)))) continue;
                dst = p ? &p->step[t][pat][i] : (row && t == want_t && pat == want_pat) ? &row[i] : &tmp;
                rd_step(&r, dst, &def);
            }
        }
    }
    rd_get(&r, nb, 2);                                /* the tapes' events */
    ev = (uint32_t)nb[0] | ((uint32_t)nb[1] << 8);
    if (ev > SQ_TAPE_MAX) return -2;
    if (p) { rd_get(&r, p->tape_ev, ev * sizeof(sq_tape_ev_t)); p->tape_n = (uint16_t)ev; }
    else rd_skip(&r, ev * (uint32_t)sizeof(sq_tape_ev_t));
    for (;;) {                                        /* the chunks: 1 = 0.13's sq_ext_t; the others skipped */
        uint8_t h[3] = {0, 0, 0};
        uint32_t n;
        rd_get(&r, h, 1);
        if (r.bad || !h[0]) break;
        rd_get(&r, h + 1, 2);
        n = (uint32_t)h[1] | ((uint32_t)h[2] << 8);
        if (r.bad) break;
        if (h[0] == SQ_CHUNK_EXT && p) {             /* (a longer one, from later: its first bytes are ours) */
            uint32_t k = n < (uint32_t)sizeof p->ext ? n : (uint32_t)sizeof p->ext;
            rd_get(&r, &p->ext, k);
            rd_skip(&r, n - k);
            ext_n = k;
        } else if (h[0] == SQ_CHUNK_TH && (p || th) && n >= 4u) {   /* 0.23 (what a later one adds after the patterns: skipped) */
            uint8_t hd[4] = {0u, 0u, 0u, 0u};
            uint32_t k, used = 4u;
            rd_get(&r, hd, 4);
            if (p) {
                p->th.src = hd[0];
                p->th.seed = (uint16_t)((uint32_t)hd[1] | ((uint32_t)hd[2] << 8));
            }
            for (k = 0; k < hd[3] && used + 2u + (uint32_t)sizeof(sq_thpat_t) <= n && !r.bad; k++) {
                uint8_t at[2] = {255u, 255u};
                sq_thpat_t m;
                rd_get(&r, at, 2);
                rd_get(&r, &m, sizeof m);
                used += 2u + (uint32_t)sizeof m;
                if (r.bad || at[0] >= SQ_TRACKS || at[1] >= SQ_PATTERNS) continue;
                if (p) p->th.pat[at[0]][at[1]] = m;
                else if (at[0] == want_t && at[1] == want_pat) *th = m;   /* (one pattern asked: RELOAD) */
            }
            rd_skip(&r, n - used);
        } else rd_skip(&r, n);
    }
    if (r.bad) return -2;
    if (p && ext_n < SQ_EXT_019)                       /* 0.19: an image from before the MIDI FX chain: its tracks' one effect */
        for (t = 0; t < SQ_TRACKS; t++) sq_mfx_from_track(&p->track[t], &p->ext.mfxc[t]);
    if (p) sq_project_sanitize(p);
    return 0;
}

int sq_image_ok(const uint8_t *in, uint32_t len) { return sq_parse(in, len, 0, 0u, 0u, 0, 0, 0); }

int sq_deserialize(sq_project_t *p, const uint8_t *in, uint32_t len) { return sq_parse(in, len, p, 0u, 0u, 0, 0, 0); }

int sq_image_track_th(const uint8_t *in, uint32_t len, uint8_t t, uint8_t pat, sq_track_cfg_t *cfg, sq_step_t *row, sq_thpat_t *th)
{
    int rc;
    uint32_t i;
    if (t >= SQ_TRACKS || pat >= SQ_PATTERNS) return -1;
    if (th) { th->seed = 0u; th->style = 0u; th->func = 0u; th->var = 0u; th->vary = 0u; th->energy = 0u; th->reserved = 0u; }
    rc = sq_parse(in, len, 0, t, pat, cfg, row, th);
    if (rc) return rc;
    if (th) sq_thpat_sanitize(th);
    sq_track_sanitize(cfg);
    for (i = 0; i < SQ_STEPS; i++) sanitize_step(&row[i]);
    return 0;
}
int sq_image_track(const uint8_t *in, uint32_t len, uint8_t t, uint8_t pat, sq_track_cfg_t *cfg, sq_step_t *row)
{
    return sq_image_track_th(in, len, t, pat, cfg, row, 0);
}

/* ------------------------------------------------------------------ 0.9 VIAGGIO: the pure parts */

void sq_viaggio_default(sq_viaggio_t *v)
{
    uint32_t i;
    v->on = 1u;                    /* 0.17: the journey always runs (it is neutral at energy 50, nothing queued) */
    v->phrase_bars = 16u;
    v->energy = 50u;
    v->set_genre = 0u;             /* (kept equal to the project's genre) */
    for (i = 0; i < SQ_TRACKS; i++) v->state[i] = SQ_TS_EMPTY;
    v->phrase_count = 0u;
    v->quant = SQ_VQ_PHRASE;
    for (i = 0; i < sizeof v->reserved; i++) v->reserved[i] = 0u;
}

void sq_viaggio_sanitize(sq_viaggio_t *v)
{
    uint32_t i;
    if (!v->on) v->energy = 50u;   /* 0.17: a project saved with VIAGGIO off plays as it did: energy 50 (neutral) */
    v->on = 1u;
    if (v->phrase_bars != 4u && v->phrase_bars != 8u && v->phrase_bars != 16u) v->phrase_bars = 16u;
    if (v->energy > 100u) v->energy = 100u;
    if (v->set_genre >= SQ_SET_GENRES) v->set_genre = 0u;
    for (i = 0; i < SQ_TRACKS; i++) if (v->state[i] > SQ_TS_OUT) v->state[i] = SQ_TS_EMPTY;
    if (v->phrase_count >= SQ_TRAIL) v->phrase_count = 0u;
    if (v->quant >= SQ_VQS) v->quant = SQ_VQ_PHRASE;
    for (i = 0; i < sizeof v->reserved; i++) v->reserved[i] = 0u;
}

/* ---- the queue */
uint8_t sq_move_has_track(uint8_t kind)
{
    return (kind == SQ_MV_IN || kind == SQ_MV_OUT || kind == SQ_MV_SWAP || kind == SQ_MV_LOOP) ? 1u : 0u;
}

const char *sq_move_name(uint8_t kind)
{
    static const char *const N[SQ_MOVE_KINDS] = {"-", "IN", "OUT", "SWAP", "FILL", "BREAK", "RISER", "DROP", "HALF",
                                                 "DOUBLE", "TRANSPOSE", "PROG", "GENRE", "THIN", "SWELL", "LOOP", "KEY",
                                                 "ENERGY", "BACK"};
    return N[kind < SQ_MOVE_KINDS ? kind : 0u];
}

void sq_queue_clear(sq_queue_t *q) { q->n = 0u; }

void sq_queue_remove(sq_queue_t *q, uint32_t i)
{
    if (i >= q->n) return;
    for (; i + 1u < q->n; i++) q->m[i] = q->m[i + 1u];
    q->n--;
}

void sq_queue_drop_last(sq_queue_t *q) { if (q->n) q->n--; }

int sq_queue_find(const sq_queue_t *q, uint8_t kind, uint8_t a)
{
    uint32_t i;
    for (i = 0; i < q->n; i++)
        if (q->m[i].kind == kind && (!sq_move_has_track(kind) || q->m[i].a == a)) return (int)i;
    return -1;
}

int sq_queue_push(sq_queue_t *q, uint8_t kind, uint8_t a, uint8_t b)
{
    int i;
    if (!kind || kind >= SQ_MOVE_KINDS) return -1;
    if (q->n > SQ_MOVES) q->n = 0u;
    if (kind == SQ_MV_IN || kind == SQ_MV_OUT) {                  /* IN cancels an OUT of the track, and the other way */
        i = sq_queue_find(q, kind == SQ_MV_IN ? SQ_MV_OUT : SQ_MV_IN, a);
        if (i >= 0) { sq_queue_remove(q, (uint32_t)i); return 0; }
    }
    if (kind == SQ_MV_HALF || kind == SQ_MV_DOUBLE) {             /* HALF after DOUBLE: neither */
        i = sq_queue_find(q, kind == SQ_MV_HALF ? SQ_MV_DOUBLE : SQ_MV_HALF, 0u);
        if (i >= 0) { sq_queue_remove(q, (uint32_t)i); return 0; }
    }
    i = sq_queue_find(q, kind, a);
    if (i >= 0) { q->m[i].a = a; q->m[i].b = b; return 0; }       /* the same move again: the new values */
    if (q->n >= SQ_MOVES) return -1;
    q->m[q->n].kind = kind; q->m[q->n].a = a; q->m[q->n].b = b;
    q->n++;
    return 0;
}

/* ---- the trail */
void sq_trail_init(sq_trail_t *t) { t->head = 0u; t->n = 0u; }

void sq_trail_push(sq_trail_t *t, sq_phrase_t *ring, const sq_phrase_t *ph)
{
    ring[t->head] = *ph;
    t->head = (uint8_t)((t->head + 1u) % SQ_TRAIL);
    if (t->n < SQ_TRAIL) t->n++;
}

const sq_phrase_t *sq_trail_get(const sq_trail_t *t, const sq_phrase_t *ring, uint32_t back)
{
    uint32_t i;
    if (back >= t->n) return 0;
    i = (t->head + SQ_TRAIL - 1u - back) % SQ_TRAIL;
    return &ring[i];
}

void sq_trail_drop(sq_trail_t *t, uint32_t n)
{
    if (n > t->n) n = t->n;
    t->head = (uint8_t)((t->head + SQ_TRAIL - n) % SQ_TRAIL);
    t->n = (uint8_t)(t->n - n);
}

static int phrase_same(const sq_phrase_t *a, const sq_phrase_t *b)
{
    uint32_t i;
    for (i = 0; i < SQ_TRACKS; i++) if (a->pattern[i] != b->pattern[i]) return 0;
    return a->mute == b->mute && a->set_genre == b->set_genre && a->prog == b->prog && a->key_root == b->key_root &&
           a->key_scale == b->key_scale;
}

uint32_t sq_trail_scenes(const sq_trail_t *t, const sq_phrase_t *ring, uint8_t phrase_bars, uint32_t cap,
                         uint8_t *out, uint8_t *bars)
{
    /* runs of equal phrases, oldest first; if there are more than `cap`, the shortest runs are dropped one at a time */
    uint8_t ri[SQ_TRAIL];
    uint16_t rb[SQ_TRAIL];
    uint32_t runs = 0u, i, k;
    if (!t->n || !cap) return 0u;
    for (i = 0; i < t->n; i++) {
        const sq_phrase_t *ph = sq_trail_get(t, ring, t->n - 1u - i);     /* oldest first */
        uint8_t pb = (ph->flags & 0x30u) ? SQ_PF_BARS(ph->flags) : phrase_bars;   /* the phrase's own length (0: the caller's) */
        if (runs && phrase_same(ph, sq_trail_get(t, ring, t->n - 1u - (uint32_t)ri[runs - 1u]))) {
            rb[runs - 1u] = (uint16_t)(rb[runs - 1u] + pb);
            continue;
        }
        ri[runs] = (uint8_t)i; rb[runs] = pb; runs++;
    }
    while (runs > cap) {
        uint32_t worst = 0u;
        for (i = 1; i < runs; i++) if (rb[i] < rb[worst]) worst = i;
        for (i = worst; i + 1u < runs; i++) { ri[i] = ri[i + 1u]; rb[i] = rb[i + 1u]; }
        runs--;
    }
    for (k = 0; k < runs; k++) { out[k] = ri[k]; bars[k] = (uint8_t)(rb[k] > SQ_SONG_BARS_MAX ? SQ_SONG_BARS_MAX : rb[k]); }
    return runs;
}

/* ---- the energy */
void sq_energy_map(uint8_t e, sq_energy_fx_t *o)
{
    int32_t d = (int32_t)(e > 100u ? 100u : e) - 50;              /* -50..+50 */
    o->vel = (int8_t)(d * 20 / 50);
    o->filt = (int8_t)(d * 40 / 50);
    o->gate = (int8_t)(d * 10 / 50);
    o->density = (uint8_t)(d < 0 ? 100 + d * 40 / 50 : 100 + d * 30 / 50);
    o->lfo_pct = (uint8_t)(e >= 50u ? 100u : 50u + e);           /* 0.17: 50 neutral (the journey always runs); under it shallower */
    o->color7 = e >= 70u ? 1u : 0u;
}

uint8_t sq_energy_glide(uint8_t from, uint8_t to, uint8_t bar, uint8_t bars)
{
    int32_t f = from > 100u ? 100 : from, t = to > 100u ? 100 : to;
    if (!bars || bar >= bars) return (uint8_t)t;
    return (uint8_t)(f + (t - f) * ((int32_t)bar + 1) / (int32_t)bars);
}

uint8_t sq_energy_riser(uint8_t base, uint8_t bar, uint8_t bars)
{
    uint32_t start = bars > 4u ? (uint32_t)bars - 4u : 0u, span = bars > 4u ? 4u : bars;
    if (!bars || bar < start) return base > 100u ? 100u : base;
    return sq_energy_glide(base, 100u, (uint8_t)(bar - start), (uint8_t)span);
}

/* ---- the genres of the set and the roles. The ladder: at what energy a role enters. Roles in the order of
 * sagga_beats.h: KICK SNARE HAT PERC BASS CHORD ARP. 0.10: one entry per genre of the library, generated with it. */
#include "sagga_setgenre_data.h"

const sq_set_genre_t *sq_set_genre(uint8_t i) { return &SET_GENRE[i < SQ_SET_GENRES ? i : 0u]; }

uint8_t sq_role_energy(uint8_t set_genre, uint8_t role)
{
    const sq_set_genre_t *g = sq_set_genre(set_genre);
    return g->ladder[role < SQ_ROLES ? role : 0u];
}

uint8_t sq_role_for_track(uint8_t set_genre, uint8_t drum, uint8_t note, uint8_t has_notes, uint8_t i, uint8_t taken)
{
    const sq_set_genre_t *g = sq_set_genre(set_genre);
    uint8_t order[SQ_ROLES], n = 0u, k, j;
    if (has_notes) {                                   /* a track with notes keeps the role its notes say */
        if (drum) {
            if (note == 35u || note == 36u) return 0u;
            if (note >= 37u && note <= 40u) return 1u;
            if (note == 42u || note == 44u || note == 46u) return 2u;
            return 3u;
        }
        return note < 48u ? 4u : note < 60u ? 5u : 6u;
    }
    for (k = 0; k < SQ_ROLES; k++) {                   /* the roles by the energy they need, lowest first */
        uint8_t best = 255u;
        for (j = 0; j < SQ_ROLES; j++) {
            uint8_t used = 0u, m;
            for (m = 0; m < n; m++) if (order[m] == j) used = 1u;
            if (!used && (best == 255u || g->ladder[j] < g->ladder[best])) best = j;
        }
        order[n++] = best;
    }
    for (k = 0; k < SQ_ROLES; k++) {                   /* the i-th free one; past the end they repeat */
        uint8_t r = order[(i + k) % SQ_ROLES];
        if (!(taken & (1u << r))) return r;
    }
    return order[i % SQ_ROLES];
}

/* ---- AFRO / LATIN: the percussion of the family. 16 steps: a 16th each; 12 steps: an eighth triplet each (12/8). */
static const sq_afro_t AFRO[SQ_AFRO_N] = {
    { "TRESILLO",   "X..x..x.X..x..x.", 16u },        /* 3+3+2, twice */
    { "SON 3-2",    "X..x..x...x.x...", 16u },
    { "SON 2-3",    "..x.x...X..x..x.", 16u },
    { "RUMBA",      "X..x...x..x.x...", 16u },
    { "CASCARA",    "x.xx.x.xx.x.xx.x", 16u },
    { "BOSSA",      "X..x..x..x..x...", 16u },        /* E(5,16) */
    { "CINQUILLO",  "X.xx.xx.X.xx.xx.", 16u },
    { "BEMBE",      "X.x.xx.x.x.x", 12u },            /* the 12/8 bell */
};

const sq_afro_t *sq_afro(uint8_t i) { return &AFRO[i < SQ_AFRO_N ? i : 0u]; }

/* ------------------------------------------------------------------ 0.10 EXPO: the pure parts */

void sq_expo_default(sq_expo_t *x)
{
    uint32_t i;
    x->shape = SQ_XS_OFF;
    x->hits = 8u;
    x->curve = 4;
    x->span = SQ_XSPAN_BAR;
    x->vel = SQ_XV_FLAT;
    x->gate = 60u;
    x->jitter = 0u;
    x->notes = SQ_XN_CHORD;
    for (i = 0; i < sizeof x->reserved; i++) x->reserved[i] = 0u;
}

void sq_expo_sanitize(sq_expo_t *x)
{
    if (x->shape >= SQ_X_SHAPES) x->shape = SQ_XS_OFF;
    if (x->hits < SQ_X_HITS_MIN) x->hits = SQ_X_HITS_MIN;
    if (x->hits > SQ_X_HITS_MAX) x->hits = SQ_X_HITS_MAX;
    if (x->curve < -8) x->curve = -8;
    if (x->curve > 8) x->curve = 8;
    if (x->span >= SQ_X_SPANS) x->span = SQ_XSPAN_BAR;
    if (x->vel >= SQ_X_VELS) x->vel = SQ_XV_FLAT;
    if (x->gate < 5u) x->gate = 5u;
    if (x->gate > 100u) x->gate = 100u;
    if (x->jitter > 50u) x->jitter = 50u;
    if (x->notes >= SQ_X_NOTES) x->notes = SQ_XN_CHORD;
}

uint16_t sq_expo_span_ticks(uint8_t span)
{
    static const uint16_t T[SQ_X_SPANS] = {0u, 24u, 48u, 96u, 192u, 384u};
    return T[span < SQ_X_SPANS ? span : 0u];
}

/* 2^(e / 64) in Q16, e in -1024 .. 1024 (the curve never asks for more than 2^4 either way) */
static uint32_t pow2_q16(int32_t e)
{
    static const uint16_t P[64] = {                    /* round(32768 * 2^(i / 64)) */
        32768, 33125, 33486, 33850, 34219, 34591, 34968, 35349, 35734, 36123, 36516, 36914, 37316, 37722, 38133, 38548,
        38968, 39392, 39821, 40255, 40693, 41136, 41584, 42037, 42495, 42958, 43425, 43898, 44376, 44859, 45348, 45842,
        46341, 46846, 47356, 47871, 48393, 48920, 49452, 49991, 50535, 51085, 51642, 52204, 52773, 53347, 53928, 54515,
        55109, 55709, 56316, 56929, 57549, 58176, 58809, 59449, 60097, 60751, 61413, 62081, 62757, 63441, 64132, 64830};
    int32_t ip = e >> 6, fp = e & 63;                   /* (an arithmetic shift floors: the fraction is 0..63) */
    uint32_t v = (uint32_t)P[fp] << 1;                  /* Q16 */
    if (ip >= 0) return ip > 15 ? v << 15 : v << ip;
    return -ip > 16 ? 0u : v >> (-ip);
}

void sq_expo_times(const sq_expo_t *x, uint32_t span_us, uint32_t *out, uint32_t *rng)
{
    uint32_t n = x->hits < SQ_X_HITS_MIN ? SQ_X_HITS_MIN : x->hits > SQ_X_HITS_MAX ? SQ_X_HITS_MAX : x->hits;
    uint32_t w[SQ_X_HITS_MAX], total = 0u, cum = 0u, k;
    int32_t c = x->curve < -8 ? -8 : x->curve > 8 ? 8 : x->curve;
    /* the gaps: hit k lasts w[k]; log2 of the gap moves by c / 2 (8 = 4 octaves = 16 x) across the span */
    for (k = 0; k < n; k++) {
        int32_t e;
        if (x->shape == SQ_XS_BOUNCE) {
            int32_t d = 2 * (int32_t)k - ((int32_t)n - 1);        /* twice the distance from the middle */
            if (d < 0) d = -d;
            e = -(c * 32 * (((int32_t)n - 1) - d)) / ((int32_t)n - 1);   /* + : short gaps in the middle */
        } else {
            e = -(c * 32 * (int32_t)k) / ((int32_t)n - 1);       /* + : the gaps shrink: an accelerando */
        }
        w[k] = pow2_q16(e);
        total += w[k];
    }
    if (!total) total = 1u;
    for (k = 0; k < n; k++) {
        out[k] = (uint32_t)(((uint64_t)span_us * cum) / total);
        cum += w[k];
    }
    if (x->jitter && rng) {                              /* the inner hits move at random, never past their neighbours */
        for (k = 1; k < n; k++) {
            uint32_t gap = (k + 1u < n ? out[k + 1u] : span_us) - out[k], room = out[k] - out[k - 1u];
            uint32_t lim = (gap < room ? gap : room) * x->jitter / 100u;
            int32_t d;
            if (!lim) continue;
            d = (int32_t)(sq_rng_next(rng) % (2u * lim + 1u)) - (int32_t)lim;
            out[k] = (uint32_t)((int32_t)out[k] + d);
        }
    }
}

uint8_t sq_expo_vel(const sq_expo_t *x, uint8_t vel, uint32_t k)
{
    uint32_t n = x->hits < SQ_X_HITS_MIN ? SQ_X_HITS_MIN : x->hits, pos, v;
    if (k >= n) k = n - 1u;
    pos = (k * 100u) / (n - 1u);                        /* 0 .. 100 along the hits */
    switch (x->vel) {
    case SQ_XV_FALL:   v = (uint32_t)vel * (100u - pos * 60u / 100u) / 100u; break;      /* 100 % .. 40 % */
    case SQ_XV_RISE:   v = (uint32_t)vel * (40u + pos * 60u / 100u) / 100u; break;       /* 40 % .. 100 % */
    case SQ_XV_BOUNCE: { uint32_t d = pos > 50u ? pos - 50u : 50u - pos;                 /* loud in the middle */
                         v = (uint32_t)vel * (100u - d * 120u / 100u) / 100u; break; }
    case SQ_XV_GRACE:  v = k == 0u ? (uint32_t)vel * 3u / 4u : vel; break;                /* a grace note first (Marea's stab) */
    default:           v = vel; break;
    }
    return (uint8_t)(v < 1u ? 1u : v > 127u ? 127u : v);
}

uint32_t sq_expo_settle_gap(const sq_expo_t *x, uint32_t pos_us, uint32_t span_us, uint32_t beat_us, uint32_t *rng)
{
    uint32_t hits = x->hits < SQ_X_HITS_MIN ? SQ_X_HITS_MIN : x->hits > SQ_X_HITS_MAX ? SQ_X_HITS_MAX : x->hits;
    uint32_t p1 = beat_us / hits, half = span_us / 4u, env_q16, gap;
    int32_t depth = x->curve < 0 ? -x->curve : x->curve, e;
    if (!half) half = 1u;
    if (x->curve >= 0) {                                /* 1 at the start, halving every quarter of the span */
        env_q16 = pos_us >= 16u * half ? 0u : pow2_q16(-(int32_t)((pos_us * 64u) / half));
    } else {                                            /* a rise over the first quarter, then the same decay */
        env_q16 = pos_us < half ? (pos_us << 16) / half
                : pos_us - half >= 16u * half ? 0u : pow2_q16(-(int32_t)(((pos_us - half) * 64u) / half));
    }
    e = -(int32_t)(((uint32_t)depth * 64u * env_q16) >> 16);   /* octaves x env, in 1/64 */
    gap = (uint32_t)(((uint64_t)p1 * pow2_q16(e)) >> 16);
    if (x->jitter && rng) {
        uint32_t lim = gap * x->jitter / 100u;
        if (lim) gap = (uint32_t)((int32_t)gap + (int32_t)(sq_rng_next(rng) % (2u * lim + 1u)) - (int32_t)lim);
    }
    return gap < 2000u ? 2000u : gap;                   /* never under 2 ms: MIDI has to get through */
}


uint8_t sq_expo_energy_hits(uint8_t hits, uint8_t energy)
{
    uint32_t h = hits;
    if (energy > 100u) energy = 100u;
    if (energy < 50u) h = (h * (50u + energy) + 50u) / 100u;             /* 0: a half */
    else h = h + (h * (energy - 50u) + 25u) / 50u;                        /* 100: twice */
    if (h < SQ_X_HITS_MIN) h = SQ_X_HITS_MIN;
    if (h > SQ_X_HITS_MAX) h = SQ_X_HITS_MAX;
    return (uint8_t)h;
}

/* ------------------------------------------------------------------ 0.11 TAPE */

void sq_tape_cfg_default(sq_tape_cfg_t *c) { c->bars = 4u; c->quant = 0u; c->flags = 0u; c->reserved = 0u; }

static void tape_zero_tail(sq_project_t *p)             /* the slots past tape_n are zero: an image compares whole */
{
    uint32_t i;
    for (i = p->tape_n; i < SQ_TAPE_MAX; i++) { p->tape_ev[i].on = 0u; p->tape_ev[i].dur = 0u; p->tape_ev[i].note = 0u; p->tape_ev[i].vel = 0u; }
}

uint32_t sq_tape_len(const sq_tape_cfg_t *c)
{
    uint32_t b = c->bars ? c->bars : 1u;
    if (b > SQ_TAPE_BARS_MAX) b = SQ_TAPE_BARS_MAX;
    return b * SQ_TAPE_BAR;
}

uint16_t sq_tape_quantised(uint16_t on, uint8_t quant, uint32_t len)
{
    uint32_t grid = SQ_TAPE_PPQ / 4u, nearest, pos = on;
    int32_t d;
    if (!quant || !len) return on;
    if (quant > 100u) quant = 100u;
    nearest = ((pos + grid / 2u) / grid) * grid;
    d = (int32_t)nearest - (int32_t)pos;
    pos = (uint32_t)((int32_t)pos + d * (int32_t)quant / 100);
    if (pos >= len) pos -= len;
    return (uint16_t)pos;
}

void sq_tape_range(const sq_project_t *p, uint8_t t, uint16_t *first, uint16_t *n)
{
    uint32_t i, f = 0u;
    for (i = 0; i < t && i < SQ_TRACKS; i++) f += p->tape_cnt[i];
    if (f > p->tape_n) f = p->tape_n;
    *first = (uint16_t)f;
    *n = t < SQ_TRACKS ? (uint16_t)(f + p->tape_cnt[t] <= p->tape_n ? p->tape_cnt[t] : p->tape_n - f) : 0u;
}

void sq_tape_sanitize(sq_project_t *p)
{
    uint32_t i, t, out = 0u, f = 0u;
    for (t = 0; t < SQ_TRACKS; t++) {
        sq_tape_cfg_t *c = &p->track[t].tape;
        if (c->bars < 1u || c->bars > SQ_TAPE_BARS_MAX) c->bars = 4u;
        if (c->quant > 100u) c->quant = 100u;
        c->flags = 0u; c->reserved = 0u;
    }
    if (p->tape_n > SQ_TAPE_MAX) p->tape_n = SQ_TAPE_MAX;
    for (t = 0; t < SQ_TRACKS; t++) {                     /* the counts must add up; the events must be sound and in order */
        uint32_t len = sq_tape_len(&p->track[t].tape), n = p->tape_cnt[t], kept = 0u, last = 0u;
        if (f + n > p->tape_n) n = p->tape_n - f;
        for (i = f; i < f + n; i++) {
            sq_tape_ev_t e = p->tape_ev[i];
            if (e.note > 127u || e.vel < 1u || e.vel > 127u || e.dur < 1u || e.on >= len || e.on < last) continue;
            if (e.dur > len) e.dur = (uint16_t)len;
            last = e.on;
            p->tape_ev[out++] = e;
            kept++;
        }
        f += n;
        p->tape_cnt[t] = (uint16_t)kept;
    }
    p->tape_n = (uint16_t)out;
    p->tape_reserved = 0u;
    tape_zero_tail(p);
}

int sq_tape_add(sq_project_t *p, uint8_t t, uint16_t on, uint16_t dur, uint8_t note, uint8_t vel)
{
    uint16_t first, n;
    uint32_t i, at, len;
    sq_tape_ev_t e;
    if (t >= SQ_TRACKS || p->tape_n >= SQ_TAPE_MAX) return -1;
    len = sq_tape_len(&p->track[t].tape);
    if (on >= len) on = (uint16_t)(on % len);
    if (!dur) dur = 1u;
    if (dur > len) dur = (uint16_t)len;
    e.on = on; e.dur = dur; e.note = note & 127u; e.vel = vel ? (uint8_t)(vel & 127u) : 100u;
    sq_tape_range(p, t, &first, &n);
    at = (uint32_t)first + n;
    while (at > first && p->tape_ev[at - 1u].on > on) at--;   /* after the last event that starts no later */
    for (i = p->tape_n; i > at; i--) p->tape_ev[i] = p->tape_ev[i - 1u];
    p->tape_ev[at] = e;
    p->tape_n++;
    p->tape_cnt[t]++;
    return 0;
}

uint32_t sq_tape_erase(sq_project_t *p, uint8_t t, uint32_t a, uint32_t b)
{
    uint16_t first, n;
    uint32_t i, out, gone = 0u;
    if (t >= SQ_TRACKS) return 0u;
    sq_tape_range(p, t, &first, &n);
    out = first;
    for (i = first; i < (uint32_t)first + n; i++) {
        if (p->tape_ev[i].on >= a && p->tape_ev[i].on < b) { gone++; continue; }
        p->tape_ev[out++] = p->tape_ev[i];
    }
    if (gone) {
        for (i = (uint32_t)first + n; i < p->tape_n; i++) p->tape_ev[out++] = p->tape_ev[i];
        p->tape_n = (uint16_t)(p->tape_n - gone);
        p->tape_cnt[t] = (uint16_t)(p->tape_cnt[t] - gone);
        tape_zero_tail(p);
    }
    return gone;
}

uint32_t sq_tape_clear(sq_project_t *p, uint8_t t) { return sq_tape_erase(p, t, 0u, 0xFFFFFFFFu); }

void sq_tape_shift(sq_project_t *p, uint8_t t, int32_t d)
{
    uint16_t first, n;
    uint32_t i, len, j;
    if (t >= SQ_TRACKS || !d) return;
    len = sq_tape_len(&p->track[t].tape);
    sq_tape_range(p, t, &first, &n);
    d %= (int32_t)len;
    if (d < 0) d += (int32_t)len;
    for (i = first; i < (uint32_t)first + n; i++) {
        uint32_t on = ((uint32_t)p->tape_ev[i].on + (uint32_t)d) % len;
        p->tape_ev[i].on = (uint16_t)on;
    }
    /* the order by start again (a rotation: an insertion sort over the block is enough) */
    for (i = (uint32_t)first + 1u; i < (uint32_t)first + n; i++) {
        sq_tape_ev_t e = p->tape_ev[i];
        for (j = i; j > first && p->tape_ev[j - 1u].on > e.on; j--) p->tape_ev[j] = p->tape_ev[j - 1u];
        p->tape_ev[j] = e;
    }
}

/* ------------------------------------------------------------------ 0.10 roles, chord shapes, rhythm families */

const char *sq_role_name(uint8_t role)
{
    static const char *const N[SQ_ROLE_COUNT] = {"NONE", "KICK", "SNARE", "HAT", "PERC", "BASS", "CHORD", "ARP",
        "CLAP", "OPEN HAT", "RIDE", "SHAKER", "CONGA", "TOM", "RIM", "CRASH", "COWBELL", "RUMBLE", "SUB", "LOG DRUM",
        "STAB", "PAD", "PIANO", "LEAD", "VOX"};
    return N[role < SQ_ROLE_COUNT ? role : 0u];
}
uint8_t sq_role_family(uint8_t role)
{
    static const uint8_t F[SQ_ROLE_COUNT] = {SQ_ROLE_NONE, SQ_ROLE_KICK, SQ_ROLE_SNARE, SQ_ROLE_HAT, SQ_ROLE_PERC, SQ_ROLE_BASS,
        SQ_ROLE_CHORD, SQ_ROLE_ARP,
        SQ_ROLE_SNARE /* CLAP */, SQ_ROLE_HAT /* OPEN HAT */, SQ_ROLE_HAT /* RIDE */, SQ_ROLE_HAT /* SHAKER */,
        SQ_ROLE_PERC /* CONGA */, SQ_ROLE_PERC /* TOM */, SQ_ROLE_SNARE /* RIM */, SQ_ROLE_PERC /* CRASH */,
        SQ_ROLE_PERC /* COWBELL */, SQ_ROLE_BASS /* RUMBLE */, SQ_ROLE_BASS /* SUB */, SQ_ROLE_BASS /* LOG DRUM */,
        SQ_ROLE_CHORD /* STAB */, SQ_ROLE_CHORD /* PAD */, SQ_ROLE_CHORD /* PIANO */, SQ_ROLE_ARP /* LEAD */,
        SQ_ROLE_ARP /* VOX */};
    return F[role < SQ_ROLE_COUNT ? role : 0u];
}
uint8_t sq_role_melodic(uint8_t role) { uint8_t f = sq_role_family(role); return (uint8_t)(f >= SQ_ROLE_BASS); }

const char *sq_chord_shape_name(uint8_t shape)
{
    static const char *const N[SQ_CH_COUNT] = {"OFF", "OCTAVE", "POWER", "5-8", "MAJOR", "MINOR", "DIM", "AUG", "SUS2", "SUS4",
        "MAJ6", "MIN6", "DOM7", "MIN7", "MAJ7", "MINMAJ7", "DIM7", "M7B5", "7SUS4", "ADD9", "MINADD9", "DOM9", "MIN9", "MAJ9",
        "9SUS4", "6/9", "MIN6/9", "MIN11", "DOM13", "SHELL7", "MINSHELL", "1-3-5-8"};
    return N[shape < SQ_CH_COUNT ? shape : 0u];
}
const char *sq_chord_key_name(uint8_t ck)
{
    static const char *const N[SQ_CK_COUNT] = {"DIATONIC", "FREE", "STRICT"};
    return N[ck < SQ_CK_COUNT ? ck : 0u];
}

/* the shapes: steps of the seven-note scale (in the key), or semitones (FREE, or no key; POWER and OCTAVE always) */
/* the shapes as semitones above the note (-1 ends); DIATONIC turns each interval into steps of the scale */
static const int8_t CHORD_SEMI[SQ_CH_COUNT][SQ_POLY_OUT] = {
    {0, -1, -1, -1, -1, -1},     /* OFF */
    {0, 12, -1, -1, -1, -1},     /* OCTAVE */
    {0, 7, -1, -1, -1, -1},      /* POWER */
    {0, 7, 12, -1, -1, -1},      /* 5-8: the techno stab */
    {0, 4, 7, -1, -1, -1},       /* MAJOR */
    {0, 3, 7, -1, -1, -1},       /* MINOR */
    {0, 3, 6, -1, -1, -1},       /* DIM */
    {0, 4, 8, -1, -1, -1},       /* AUG */
    {0, 2, 7, -1, -1, -1},       /* SUS2 */
    {0, 5, 7, -1, -1, -1},       /* SUS4 */
    {0, 4, 7, 9, -1, -1},        /* MAJ6 */
    {0, 3, 7, 9, -1, -1},        /* MIN6 */
    {0, 4, 7, 10, -1, -1},       /* DOM7 */
    {0, 3, 7, 10, -1, -1},       /* MIN7: house, garage, dub techno */
    {0, 4, 7, 11, -1, -1},       /* MAJ7: amapiano, deep house */
    {0, 3, 7, 11, -1, -1},       /* MINMAJ7 */
    {0, 3, 6, 9, -1, -1},        /* DIM7 */
    {0, 3, 6, 10, -1, -1},       /* M7B5: half-diminished */
    {0, 5, 7, 10, -1, -1},       /* 7SUS4 */
    {0, 4, 7, 14, -1, -1},       /* ADD9 */
    {0, 3, 7, 14, -1, -1},       /* MINADD9: trance */
    {0, 4, 7, 10, 14, -1},       /* DOM9 */
    {0, 3, 7, 10, 14, -1},       /* MIN9: house, drum and bass */
    {0, 4, 7, 11, 14, -1},       /* MAJ9 */
    {0, 5, 7, 10, 14, -1},       /* 9SUS4: UK garage, house */
    {0, 4, 7, 9, 14, -1},        /* 6/9 */
    {0, 3, 7, 9, 14, -1},        /* MIN6/9 */
    {0, 3, 7, 10, 14, 17},       /* MIN11 */
    {0, 4, 7, 10, 14, 21},       /* DOM13 */
    {0, 4, 10, -1, -1, -1},      /* SHELL7: root, third, seventh */
    {0, 3, 10, -1, -1, -1},      /* MINSHELL: the minor stab */
    {0, 4, 7, 12, -1, -1},       /* 1-3-5-8 */
};
/* a semitone interval as steps of a seven-note scale (0..21: the unison to the 13th) */
static const int8_t SEMI_STEP[22] = {0, 1, 1, 2, 2, 3, 4, 4, 5, 5, 6, 6, 7, 8, 8, 9, 9, 10, 11, 11, 12, 12};

uint8_t sq_chord_build(uint8_t note, uint8_t shape, uint8_t ck, uint8_t root, uint8_t scale, uint8_t *out)
{
    uint8_t n = 0u, k, j, hs = sq_harm_scale(scale);
    uint16_t mask = sq_scale_mask(scale);
    int32_t idx = 0, delta = 0;
    uint8_t by_scale;
    if (note > 127u) return 0u;
    if (shape >= SQ_CH_COUNT || shape == SQ_CH_OFF) { out[0] = note; return 1u; }
    if (ck >= SQ_CK_COUNT || scale == SQ_SC_CHROMATIC) ck = SQ_CK_FREE;
    by_scale = (ck == SQ_CK_DIATONIC && shape != SQ_CH_OCT && shape != SQ_CH_POWER && shape != SQ_CH_5_8) ? 1u : 0u;
    if (by_scale) { idx = sq_scale_index(note, root, hs); delta = (int32_t)note - (int32_t)sq_scale_at(idx, root, hs); }
    for (k = 0; k < SQ_POLY_OUT; k++) {
        int32_t v;
        int8_t d = CHORD_SEMI[shape][k];
        if (d < 0) break;
        if (by_scale) v = (int32_t)sq_scale_at(idx + SEMI_STEP[d], root, hs) + delta;
        else v = (int32_t)note + d;
        if (v < 0 || v > 127) continue;
        if (ck == SQ_CK_STRICT && k && !((mask >> ((uint32_t)(v + 120 - (int32_t)root) % 12u)) & 1u)) continue;   /* out of the key: silent */
        for (j = 0; j < n; j++) if (out[j] == (uint8_t)v) break;
        if (j < n) continue;
        out[n++] = (uint8_t)v;
    }
    return n ? n : (uint8_t)((out[0] = note), 1u);
}

uint8_t sq_track_note(const sq_track_cfg_t *c, int32_t note, uint8_t root, uint8_t scale, int8_t shift)
{
    int32_t v = note + 12 * (int32_t)c->octave;
    if (c->flags & SQ_TF_SCALE) {
        if (c->transpose) v = sq_scale_degree(v, root, scale, c->transpose);   /* steps of the scale */
        return sq_scale_apply(v, root, scale, shift);
    }
    v += c->transpose;
    return (uint8_t)clampi(v, 0, 127);
}

const char *sq_rhythm_name(uint8_t fam)
{
    static const char *const N[SQ_RF_COUNT] = {"EUCLID", "TRESILLO", "NUMERIC"};
    return N[fam < SQ_RF_COUNT ? fam : 0u];
}

static uint32_t prime_nth(uint32_t n)                     /* the n-th prime, n >= 1 (1: 2) */
{
    uint32_t c = 0u, v = 1u;
    if (!n) n = 1u;
    while (c < n) {
        uint32_t d, p = 1u;
        v++;
        for (d = 2u; d * d <= v; d++) if (v % d == 0u) { p = 0u; break; }
        if (p) c++;
    }
    return v;
}

void sq_rhythm(uint8_t fam, uint8_t pulses, uint8_t len, uint8_t rot, uint8_t *bits)
{
    uint8_t i;
    if (!len) return;
    if (len > SQ_STEPS) len = SQ_STEPS;
    if (fam == SQ_RF_TRESILLO) {                          /* groups of 3, a 2 to close each half (3-3-2): `pulses` kept */
        uint8_t tmp[SQ_STEPS], pos = 0u, k = 0u, half = (uint8_t)(len % 8u == 0u ? 8u : len);
        for (i = 0; i < len; i++) tmp[i] = 0u;
        while (pos < len) {
            uint8_t left = (uint8_t)(half - pos % half), g = left >= 5u ? 3u : left >= 2u ? 2u : left;   /* 3 3 2 */
            if (k < pulses) tmp[pos] = 1u;
            k++;
            pos = (uint8_t)(pos + g);
        }
        for (i = 0; i < len; i++) bits[(i + rot) % len] = tmp[i];
    } else if (fam == SQ_RF_NUMERIC) {                    /* the pulses-th prime in binary, the low bit first */
        uint32_t p = prime_nth(pulses), nb = 0u, v = p;
        while (v) { nb++; v >>= 1; }
        for (i = 0; i < len; i++) bits[(i + rot) % len] = (uint8_t)((p >> (i % nb)) & 1u);
    } else sq_euclid(pulses, len, rot, bits);
}

uint8_t sq_rhythm_hit(uint8_t fam, uint8_t pulses, uint8_t len, uint8_t rot, uint8_t i)
{
    uint8_t bits[SQ_STEPS];
    if (fam == SQ_RF_EUCLID) return sq_euclid_hit(pulses, len, rot, i);
    if (!len || i >= len) return 0u;
    sq_rhythm(fam, pulses, len, rot, bits);
    return bits[i];
}

void sq_row_rhythm(sq_step_t *row, uint8_t len, uint8_t fam, uint8_t pulses, uint8_t rot)
{
    uint8_t bits[SQ_STEPS], i;
    if (fam == SQ_RF_EUCLID) { sq_row_euclid(row, len, pulses, rot); return; }
    if (!len) return;
    if (len > SQ_STEPS) len = SQ_STEPS;
    sq_rhythm(fam, pulses, len, rot, bits);
    for (i = 0; i < len; i++) {
        if (bits[i]) row[i].flags |= SQ_STEP_ON | SQ_STEP_SET; else row[i].flags &= (uint8_t)~SQ_STEP_ON;
    }
}

/* COOK by role (see the header). `len` steps of a 16th: the beats are every fourth step. */
static void row_on(sq_step_t *s, uint8_t vel) { s->flags |= SQ_STEP_ON | SQ_STEP_SET; s->velocity = vel; }
void sq_row_cook_role(sq_step_t *row, uint8_t len, uint8_t heat, uint8_t role, uint8_t root, uint8_t scale, uint32_t *rng)
{
    uint8_t i, lowest = 255u;
    uint32_t h = heat > 100u ? 100u : heat;              /* the chance a step is touched, in % */
    if (!len) return;
    if (role == SQ_ROLE_NONE || role >= SQ_ROLE_COUNT) { sq_row_cook(row, len, heat, rng); return; }
    role = sq_role_family(role);                         /* 0.11: a CLAP cooks as a SNARE, a PAD as a CHORD ... */
    for (i = 0; i < len; i += 4u)                        /* the root of a melodic part: its lowest note on a beat (a pickup below it is not the root) */
        if ((row[i].flags & SQ_STEP_ON) && row[i].note[0] < lowest) lowest = row[i].note[0];
    if (lowest > 127u) for (i = 0; i < len; i++) if ((row[i].flags & SQ_STEP_ON) && row[i].note[0] < lowest) lowest = row[i].note[0];
    for (i = 0; i < len; i++) {
        sq_step_t *s = &row[i];
        uint8_t beat = (uint8_t)(i % 4u == 0u), on = (uint8_t)((s->flags & SQ_STEP_ON) != 0u);
        if (s->flags & SQ_STEP_LOCK) continue;
        switch (role) {
        case SQ_ROLE_KICK:                                /* the beats stay; pickups before them come and go */
            if (beat) { if (on) s->velocity = (uint8_t)clampi((int32_t)s->velocity + (int32_t)(pct(rng) % 9u) - 4, 90, 127); break; }
            if (!on && (i % 4u == 3u || i % 4u == 2u) && pct(rng) < h / 4u) row_on(s, (uint8_t)(70u + pct(rng) % 20u));
            else if (on && pct(rng) < h / 3u) s->flags &= (uint8_t)~SQ_STEP_ON;
            break;
        case SQ_ROLE_SNARE:                               /* the backbeat stays; ghosts and rolls around it */
            if (i % 8u == 4u) { if (on && pct(rng) < h / 2u) s->ratchet = (uint8_t)(pct(rng) < 30u ? 2u : 1u); break; }
            if (!on && (i & 1u) && pct(rng) < h / 3u) { row_on(s, (uint8_t)(28u + pct(rng) % 18u)); s->length = 40u; }
            else if (on && s->velocity < 60u && pct(rng) < h / 2u) s->flags &= (uint8_t)~SQ_STEP_ON;
            if (!on && i % 8u == 3u && h >= 60u && pct(rng) < h / 3u) { row_on(s, 60u); s->ratchet = 3u; s->ramp = 60; }   /* a roll into the backbeat */
            break;
        case SQ_ROLE_HAT:                                 /* offbeats open, accents move, ratchets at heat */
            if (on) {
                if (pct(rng) < h / 2u) s->velocity = (uint8_t)((i & 2u) ? 64u + pct(rng) % 30u : 96u + pct(rng) % 32u);
                if (pct(rng) < h / 5u) s->ratchet = (uint8_t)(2u + pct(rng) % 2u); else if (pct(rng) < h / 4u) s->ratchet = 1u;
                if (i % 4u == 2u && pct(rng) < h / 4u) s->length = (uint8_t)(s->length >= 90u ? 40u : 100u);   /* an open hat on the "and" */
            } else if (pct(rng) < h / 4u) { row_on(s, (uint8_t)(50u + pct(rng) % 30u)); s->length = 30u; }
            break;
        case SQ_ROLE_PERC:                                /* syncopation: hits slide a step, come and go */
            if (on && pct(rng) < h / 3u && i + 1u < len && !(row[i + 1u].flags & SQ_STEP_ON) && !(row[i + 1u].flags & SQ_STEP_LOCK)) {
                row[i + 1u] = *s; s->flags &= (uint8_t)~SQ_STEP_ON; i++;
            } else if (!on && !beat && pct(rng) < h / 5u) row_on(s, (uint8_t)(60u + pct(rng) % 40u));
            else if (on && pct(rng) < h / 5u) s->flags &= (uint8_t)~SQ_STEP_ON;
            break;
        case SQ_ROLE_BASS:                                /* root on the beats; fifths, octaves and pickups between */
            if (lowest > 127u) break;
            if (on && beat && pct(rng) < h / 2u) s->note[0] = lowest;
            else if (on && !beat && pct(rng) < h / 2u) {
                uint32_t r = pct(rng);
                s->note[0] = r < 50u ? sq_scale_degree(lowest, root, scale, 4) : r < 80u ? (uint8_t)clampi((int32_t)lowest + 12, 0, 127) : lowest;
            }
            if (!on && i + 1u < len && (i + 1u) % 4u == 0u && pct(rng) < h / 4u) {   /* a pickup into the beat */
                row_on(s, (uint8_t)(80u + pct(rng) % 20u)); s->note[0] = sq_scale_degree(lowest, root, scale, pct(rng) < 50u ? -1 : 4); s->length = 50u;
            } else if (on && !beat && pct(rng) < h / 5u) s->flags &= (uint8_t)~SQ_STEP_ON;
            if (on && pct(rng) < h / 3u) s->length = (uint8_t)(30u + pct(rng) % 60u);
            break;
        case SQ_ROLE_CHORD:                               /* the roots stay: the rhythm and the length change (stab / pad) */
            if (on && pct(rng) < h / 3u) s->length = (uint8_t)(s->length > 60u ? 25u + pct(rng) % 20u : 90u + pct(rng) % 11u);
            if (on && !beat && pct(rng) < h / 4u && i + 1u < len && !(row[i + 1u].flags & SQ_STEP_ON)) { row[i + 1u] = *s; s->flags &= (uint8_t)~SQ_STEP_ON; i++; }
            else if (on && pct(rng) < h / 6u) s->flags &= (uint8_t)~SQ_STEP_ON;
            if (on && pct(rng) < h / 3u) s->velocity = (uint8_t)clampi((int32_t)s->velocity + (int32_t)(pct(rng) % 21u) - 10, 40, 127);
            break;
        default:                                          /* ARP: the order of the notes, the gaps, an octave now and then */
            if (on && pct(rng) < h / 2u && i + 1u < len && (row[i + 1u].flags & SQ_STEP_ON) && !(row[i + 1u].flags & SQ_STEP_LOCK)) {
                uint8_t tmp = s->note[0]; s->note[0] = row[i + 1u].note[0]; row[i + 1u].note[0] = tmp;
            }
            if (on && pct(rng) < h / 6u) s->note[0] = (uint8_t)clampi((int32_t)s->note[0] + (pct(rng) < 50u ? 12 : -12), 0, 127);
            if (on && pct(rng) < h / 5u) s->flags &= (uint8_t)~SQ_STEP_ON;
            else if (!on && pct(rng) < h / 5u && lowest <= 127u) { row_on(s, (uint8_t)(80u + pct(rng) % 30u)); s->note[0] = sq_scale_degree(lowest, root, scale, (int32_t)(pct(rng) % 8u)); s->length = 60u; }
            break;
        }
    }
}

/* ------------------------------------------------------------------ 0.11 COOK towards the next variation, the length of the notes */
static uint8_t step_same(const sq_step_t *a, const sq_step_t *b)
{
    uint8_t aon = (uint8_t)((a->flags & SQ_STEP_ON) != 0u), bon = (uint8_t)((b->flags & SQ_STEP_ON) != 0u);
    if (aon != bon) return 0u;
    if (!aon) return 1u;
    return (uint8_t)(a->note[0] == b->note[0] && a->note[1] == b->note[1] && a->note[2] == b->note[2]
                     && a->velocity == b->velocity && a->length == b->length && a->ratchet == b->ratchet);
}
static uint8_t place_weight(uint32_t i)                  /* how weak a place is: 3 a 16th, 2 an "and", 1 a beat, 0 the one */
{
    return (uint8_t)(i % 16u == 0u ? 0u : i % 4u == 0u ? 1u : i % 2u == 0u ? 2u : 3u);
}
uint8_t sq_gate_steps(uint8_t steps)
{
    if (steps <= 1u) return 100u;
    if (steps > 64u) steps = 64u;
    return (uint8_t)(100u + steps);
}
uint8_t sq_gate_span(uint8_t encoded)
{
    return (uint8_t)(encoded > SQ_GATE_LONG_MIN && encoded <= SQ_GATE_LONG_MAX ? encoded - 100u : 1u);
}
uint8_t sq_row_approach(sq_step_t *row, const sq_step_t *target, uint8_t len, uint8_t steps, uint32_t *rng)
{
    uint8_t order[SQ_STEPS], n = 0u, w, k, left = 0u;
    uint32_t i;
    if (len > SQ_STEPS) len = (uint8_t)SQ_STEPS;
    for (w = 4u; w-- > 0u; ) {                           /* the weak places first; in a group, a random order */
        uint8_t first = n;
        for (i = 0; i < len; i++) if (place_weight(i) == w && !(row[i].flags & SQ_STEP_LOCK) && !step_same(&row[i], &target[i])) order[n++] = (uint8_t)i;
        for (k = (uint8_t)(n - first); k > 1u; k--) {
            uint8_t j = (uint8_t)(first + sq_rng_next(rng) % k), tmp = order[first + k - 1u];
            order[first + k - 1u] = order[j]; order[j] = tmp;
        }
    }
    for (k = 0; k < n && k < steps; k++) {
        sq_step_t *s = &row[order[k]];
        const sq_step_t *t = &target[order[k]];
        uint8_t keep_lanes[SQ_LANES], f = (uint8_t)(s->flags & ~(SQ_STEP_ON | SQ_STEP_LEGATO));
        uint32_t l;
        for (l = 0; l < SQ_LANES; l++) keep_lanes[l] = s->lane[l];   /* (the CC locks the player set stay) */
        *s = *t;
        s->flags = (uint8_t)(f | (t->flags & (SQ_STEP_ON | SQ_STEP_LEGATO)) | SQ_STEP_SET);
        for (l = 0; l < SQ_LANES; l++) if (keep_lanes[l] != SQ_LANE_NONE) s->lane[l] = keep_lanes[l];
    }
    for (i = 0; i < len; i++) if (!(row[i].flags & SQ_STEP_LOCK) && !step_same(&row[i], &target[i])) left++;
    return left;
}

void sq_row_phrase_gates(sq_step_t *row, uint8_t len, uint8_t role, uint8_t heat, uint32_t *rng)
{
    uint32_t i, h = heat > 100u ? 100u : heat, phrase = 0u;
    uint8_t fam = sq_role_family(role);
    if (!len || !sq_role_melodic(role)) return;
    for (i = 0; i < len; i++) {
        sq_step_t *s = &row[i];
        uint32_t gap = 1u, j;
        if (!(s->flags & SQ_STEP_ON) || (s->flags & SQ_STEP_LOCK) || s->ratchet > 1u) continue;
        if (s->length > SQ_GATE_LONG_MIN) continue;     /* (two steps or more already: the player's, or the library's) */
        for (j = i + 1u; j < len && !(row[j].flags & SQ_STEP_ON); j++) gap++;
        if (j >= len) {                                  /* the last note: to the loop's end, and as far again at most */
            uint32_t k;
            for (k = 0; k < len && !(row[k].flags & SQ_STEP_ON); k++) gap++;
        }
        if (gap > 64u) gap = 64u;
        phrase++;
        switch (role) {
        case SQ_ROLE_PAD:                                /* held to the next chord */
            s->length = gap >= 2u ? sq_gate_steps((uint8_t)gap) : 100u;
            break;
        case SQ_ROLE_STAB:
            s->length = (uint8_t)(20u + sq_rng_next(rng) % 25u);
            break;
        case SQ_ROLE_SUB:                                /* a sub holds */
            s->length = gap >= 2u ? sq_gate_steps((uint8_t)gap) : 95u;
            break;
        default:
            if (fam == SQ_ROLE_BASS) {                   /* on the beat long (to the next note), between short; now and then a slide */
                if (i % 4u == 0u && gap >= 2u && sq_rng_next(rng) % 100u < 40u + h / 2u) s->length = sq_gate_steps((uint8_t)(gap > 4u ? 4u : gap));
                else s->length = (uint8_t)(i % 2u ? 35u + sq_rng_next(rng) % 25u : 60u + sq_rng_next(rng) % 30u);
                if (gap == 1u && sq_rng_next(rng) % 100u < h / 4u) s->flags |= SQ_STEP_TIE;
            } else if (fam == SQ_ROLE_CHORD) {           /* CHORD, PIANO: a stab or a held chord, a little of both */
                if (gap >= 3u && sq_rng_next(rng) % 100u < 35u + h / 3u) s->length = sq_gate_steps((uint8_t)(gap - 1u));
                else s->length = (uint8_t)(40u + sq_rng_next(rng) % 45u);
            } else if (role == SQ_ROLE_LEAD || role == SQ_ROLE_VOX) {   /* phrases: the note before a long rest, or every fourth, is held */
                if (gap >= 3u || (phrase % 4u == 0u && gap >= 2u)) s->length = sq_gate_steps((uint8_t)(gap > 8u ? 8u : gap));
                else if (gap == 1u && sq_rng_next(rng) % 100u < h / 3u) { s->length = 100u; s->flags |= SQ_STEP_TIE; }
                else s->length = (uint8_t)(55u + sq_rng_next(rng) % 40u);
            } else {                                     /* ARP: short, the last of a run a bit longer */
                s->length = (uint8_t)(gap >= 2u ? 70u + sq_rng_next(rng) % 25u : 35u + sq_rng_next(rng) % 30u);
            }
            break;
        }
    }
}

/* ------------------------------------------------------------------ 0.10 the synths' CC names */
#include "sagga_devices.h"

const char *sq_device_name(uint8_t dev)
{
    static const char *const N[SQ_DEV_COUNT] = {"GENERIC", "ELEKTRON"};
    return N[dev < SQ_DEV_COUNT ? dev : 0u];
}

const char *sq_cc_name(uint8_t dev, uint8_t cc)
{
    const sq_ccname_t *tab = CC_GENERIC;
    uint32_t n = sizeof CC_GENERIC / sizeof CC_GENERIC[0], i;
    if (dev == SQ_DEV_ELEKTRON) { tab = CC_ELEKTRON; n = sizeof CC_ELEKTRON / sizeof CC_ELEKTRON[0]; }
    for (i = 0; i < n; i++) if (tab[i].cc == cc) return tab[i].name;
    return "";
}

/* ---- 0.12 BREAK: the chops */
#define R(...) (uint16_t)(__VA_ARGS__)
static const sq_brk_chop_t BRK_CHOP[SQ_BRK_CHOPS] = {
    {"STRAIGHT",  { 1, 2, 3, 4,  5, 6, 7, 8,  9,10,11,12, 13,14,15,16}, 0x0000u, 0x1111u, 100u},
    {"END ROLL",  { 1, 2, 3, 4,  5, 6, 7, 8,  9,10,11,12, 13,14,15,15}, 0xC000u, 0x1111u, 100u},
    {"RUSH",      { 1, 2, 3, 4,  5, 5, 5, 5,  9,10,11,12, 13,13,13,13}, 0xE0E0u, 0x1111u, 100u},
    {"REPEAT",    { 1, 2, 3, 4,  5, 6, 7, 8,  1, 2, 3, 4,  5, 6, 7, 8}, 0x0000u, 0x1111u, 100u},
    {"DOUBLE",    { 1, 3, 5, 7,  9,11,13,15,  1, 3, 5, 7,  9,11,13,15}, 0x0000u, 0x0505u, 100u},
    {"HALF",      { 1, 0, 2, 0,  3, 0, 4, 0,  5, 0, 6, 0,  7, 0, 8, 0}, 0x0000u, 0x0101u, 102u},
    {"BACKWARDS", {16,15,14,13, 12,11,10, 9,  8, 7, 6, 5,  4, 3, 2, 1}, 0x0000u, 0x8888u, 100u},
    {"GHOST",     { 1, 2, 0, 4,  5, 0, 7, 0,  9, 0,11,12, 13, 0,15, 0}, 0x0000u, 0x1111u, 100u},
    {"LOW",       { 1, 0, 0, 0,  0, 0, 0, 0,  9, 0,11, 0,  0, 0, 0, 0}, 0x0000u, 0x0101u, 100u},
    {"HIGH",      { 0, 2, 3, 4,  0, 6, 7, 8,  0,10,11,12,  0,14,15,16}, 0x0000u, 0x0000u, 100u},
    {"SHUFFLE",   { 1, 2, 7, 8,  5, 6, 3, 4,  9,10,15,16, 13,14,11,12}, 0x0000u, 0x1111u, 100u},
    {"THINK",     { 1, 2, 1, 2,  5, 6, 5, 6,  9,10, 9,10, 13,14,13,14}, 0x0000u, 0x1111u, 100u},
    {"APACHE",    { 1, 2, 3, 4,  5, 6, 1, 2,  9,10,11,12, 13,14, 5, 6}, 0x0000u, 0x1111u, 100u},
    {"SNARES",    { 1, 2, 3, 4,  5, 6, 7, 5,  9,10,11,12, 13,14, 5,13}, 0x0000u, 0x9191u, 100u},
    {"TRIPLE",    { 1, 2, 3, 1,  2, 3, 5, 6,  7, 5, 6, 7,  9,10,11,13}, 0x0000u, 0x1249u, 100u},
    {"BUILD",     { 1, 1, 1, 1,  5, 5, 5, 5,  9, 9, 9, 9, 13,13,13,13}, 0xF000u, 0x1111u, 100u},
};
#undef R
const sq_brk_chop_t *sq_brk_chop(uint8_t i) { return &BRK_CHOP[i < SQ_BRK_CHOPS ? i : 0u]; }

/* the chops of each genre (the order of sagga_beats_data.h's GENRE_NAME), the ones that belong to it, in the order COOK
 * walks them: the first byte is how many, then the chops (0 STRAIGHT 1 END ROLL 2 RUSH 3 REPEAT 4 DOUBLE 5 HALF
 * 6 BACKWARDS 7 GHOST 8 LOW 9 HIGH 10 SHUFFLE 11 THINK 12 APACHE 13 SNARES 14 TRIPLE 15 BUILD) */
#define BRK_GENRES 25u                     /* (SQ_GENRES: the core does not include the library) */
static const uint8_t BRK_GENRE[BRK_GENRES][8] = {
    {5, 0, 7, 5, 8, 1},              /* TECHNO: straight, ghosts, half, the low end, the end roll */
    {5, 0, 4, 2, 15, 1},             /* HARDTECHNO: straight, double, rush, build, end roll */
    {4, 0, 5, 7, 8},                 /* DUB TECHNO: straight, half, ghosts, low */
    {4, 0, 7, 10, 1},                /* HOUSE: straight, ghosts, shuffle, end roll */
    {5, 10, 7, 13, 11, 1},           /* UK GARAGE: shuffle, ghosts, snares, think, end roll */
    {4, 10, 14, 7, 13},              /* UK FUNKY: shuffle, triple, ghosts, snares */
    {5, 5, 7, 8, 13, 1},             /* GRIME: half, ghosts, low, snares, end roll */
    {5, 5, 8, 7, 13, 15},            /* DUBSTEP: half, low, ghosts, snares, build */
    {7, 0, 11, 12, 10, 13, 14, 1},   /* JUNGLE: straight, think, apache, shuffle, snares, triple, end roll */
    {4, 10, 7, 3, 1},                /* BASSLINE: shuffle, ghosts, repeat, end roll */
    {4, 0, 7, 3, 13},                /* REGGAETON: straight, ghosts, repeat, snares */
    {4, 14, 10, 7, 2},               /* BATIDA: triple, shuffle, ghosts, rush */
    {4, 5, 8, 7, 15},                /* GQOM: half, low, ghosts, build */
    {6, 6, 10, 2, 9, 14, 15},        /* EXPERIMENT: backwards, shuffle, rush, high, triple, build */
    {5, 0, 4, 3, 7, 1},              /* ELECTRO: straight, double, repeat, ghosts, end roll */
    {7, 0, 11, 12, 4, 13, 1, 2},     /* DRUM+BASS: straight, think, apache, double, snares, end roll, rush */
    {4, 10, 7, 14, 8},               /* AFRO HOUSE: shuffle, ghosts, triple, low */
    {4, 5, 7, 8, 10},                /* AMAPIANO: half, ghosts, low, shuffle */
    {6, 14, 2, 3, 4, 13, 15},        /* FOOTWORK: triple, rush, repeat, double, snares, build */
    {4, 0, 4, 15, 1},                /* TRANCE: straight, double, build, end roll */
    {5, 5, 7, 13, 14, 8},            /* UK DRILL: half, ghosts, snares, triple, low */
    {5, 4, 2, 15, 3, 1},             /* HARDCORE: double, rush, build, repeat, end roll */
    {4, 5, 8, 7, 13},                /* PHONK: half, low, ghosts, snares */
    {5, 14, 10, 13, 3, 2},           /* BAILE FUNK: triple, shuffle, snares, repeat, rush */
    {4, 0, 10, 3, 1},                /* MERENGUE: straight, shuffle, repeat, end roll */
};
uint8_t sq_brk_genre_chops(uint8_t genre) { return BRK_GENRE[genre < BRK_GENRES ? genre : 0u][0]; }
uint8_t sq_brk_genre_chop(uint8_t genre, uint8_t pos)
{
    const uint8_t *g = BRK_GENRE[genre < BRK_GENRES ? genre : 0u];
    return g[1u + (pos < g[0] ? pos : 0u)];
}

void sq_brk_step(sq_step_t *row, uint8_t i, uint8_t slice, uint8_t pen, uint8_t n_slices, uint8_t gate, uint8_t vel)
{
    sq_step_t *s = &row[i];
    uint32_t k;
    if (!n_slices) n_slices = 16u;
    if (!slice) { s->flags &= (uint8_t)~SQ_STEP_ON; return; }
    s->note[0] = (uint8_t)clampi((int32_t)pen + (int32_t)((slice - 1u) % n_slices), 0, 127);
    for (k = 1; k < SQ_POLY; k++) s->note[k] = SQ_NOTE_NONE;
    s->flags |= SQ_STEP_ON | SQ_STEP_SET;
    s->flags &= (uint8_t)~SQ_STEP_LEGATO;
    s->length = gate;
    s->velocity = vel;
}

void sq_brk_apply(sq_step_t *row, uint8_t start, uint8_t length, uint8_t chop, uint8_t pen, uint8_t n_slices)
{
    const sq_brk_chop_t *c = sq_brk_chop(chop);
    uint32_t i;
    for (i = start; i < length && i < SQ_STEPS; i++) {
        uint32_t k = (i - start) & 15u;
        uint8_t acc = (uint8_t)((c->acc >> k) & 1u);
        if (row[i].flags & SQ_STEP_LOCK) continue;                          /* a locked step stays as written */
        sq_brk_step(row, (uint8_t)i, c->sl[k], pen, n_slices, c->gate, acc ? 115u : 95u);
        row[i].ratchet = (uint8_t)(((c->roll >> k) & 1u) ? 2u : 1u);
    }
}

uint8_t sq_brk_slice_of(const sq_step_t *s, uint8_t pen, uint8_t n_slices)
{
    if (!(s->flags & SQ_STEP_ON) || s->note[0] == SQ_NOTE_NONE || s->note[0] < pen) return 0u;
    if (!n_slices) n_slices = 16u;
    if ((uint32_t)(s->note[0] - pen) >= n_slices) return 0u;
    return (uint8_t)(s->note[0] - pen + 1u);
}

void sq_brk_dice(sq_step_t *row, uint8_t start, uint8_t length, uint8_t pen, uint8_t n_slices, uint8_t swap, uint8_t roll,
                 uint8_t heat, uint32_t *rng)
{
    static const uint8_t HATS[12] = {2, 3, 4, 6, 7, 8, 10, 11, 12, 14, 15, 16};
    uint32_t i, bar0, nbars = 0u, b;
    if (!n_slices) n_slices = 16u;
    for (i = start; i < length && i < SQ_STEPS; i++) {
        uint32_t k = (i - start) & 15u;
        uint8_t backbone = (k & 3u) == 0u ? 1u : 0u;       /* 1, 5, 9, 13 */
        uint8_t cur = sq_brk_slice_of(&row[i], pen, n_slices);
        uint8_t sl = cur;
        if (row[i].flags & SQ_STEP_LOCK) continue;                          /* a locked step stays as written */
        if (backbone) sl = (k == 0u || k == 8u) ? 1u : 5u;
        else if ((sq_rng_next(rng) % 8u) < swap) {
            uint32_t r = sq_rng_next(rng) % 100u;
            if (r < 6u + heat / 10u) sl = (uint8_t)(1u + (sq_rng_next(rng) & 1u) * 4u);   /* a stray kick or snare */
            else if (r < 12u) sl = 0u;                                                   /* a rest */
            else sl = HATS[sq_rng_next(rng) % 12u];
        } else if (!sl) sl = (uint8_t)(k + 1u);                                          /* an empty step: its own slice */
        sq_brk_step(row, (uint8_t)i, sl, pen, n_slices, 100u, backbone ? (uint8_t)(110u + heat / 10u) : (uint8_t)(80u + sq_rng_next(rng) % 20u));
        row[i].ratchet = 1u;
    }
    /* the rolls: before the backbone (steps 4, 8, 12, 16 of a bar), the last ones first, more with heat */
    nbars = (uint32_t)(length > start ? (length - start + 15u) / 16u : 1u);
    for (b = 0; b < nbars; b++) {
        static const uint8_t PRE[4] = {15, 7, 11, 3};
        uint32_t n = roll, k;
        bar0 = start + b * 16u;
        for (k = 0; k < 4u && n; k++) {
            uint32_t i2 = bar0 + PRE[k];
            if (i2 >= length || i2 >= SQ_STEPS || (row[i2].flags & SQ_STEP_LOCK)) continue;
            if (!(row[i2].flags & SQ_STEP_ON)) sq_brk_step(row, (uint8_t)i2, (uint8_t)(PRE[k] + 1u), pen, n_slices, 100u, 90u);
            row[i2].ratchet = (uint8_t)(heat > 60u && (sq_rng_next(rng) & 1u) ? 4u : 2u);
            n--;
        }
        for (k = 0; k < 16u && n; k++) {                      /* more than four: anywhere */
            uint32_t i2 = bar0 + (sq_rng_next(rng) & 15u);
            if (i2 >= length || i2 >= SQ_STEPS || row[i2].ratchet > 1u || !(row[i2].flags & SQ_STEP_ON) || (row[i2].flags & SQ_STEP_LOCK)) continue;
            row[i2].ratchet = 2u;
            n--;
        }
    }
}

void sq_brk_half(sq_step_t *row, uint8_t start, uint8_t length, uint8_t pen, uint8_t n_slices)
{
    uint8_t sl[SQ_STEPS], vel[SQ_STEPS];
    uint32_t i, n = length > start ? (uint32_t)(length - start) : 0u;
    for (i = 0; i < n; i++) { sl[i] = sq_brk_slice_of(&row[start + i], pen, n_slices); vel[i] = row[start + i].velocity; }
    for (i = 0; i < n; i++) {
        uint8_t v = (i & 1u) ? 0u : sl[i / 2u];
        if (row[start + i].flags & SQ_STEP_LOCK) continue;
        sq_brk_step(row, (uint8_t)(start + i), v, pen, n_slices, 102u, vel[i / 2u]);
        if (v) row[start + i].ratchet = 1u;
    }
}
void sq_brk_double(sq_step_t *row, uint8_t start, uint8_t length, uint8_t pen, uint8_t n_slices)
{
    uint8_t sl[SQ_STEPS], vel[SQ_STEPS];
    uint32_t i, n = length > start ? (uint32_t)(length - start) : 0u;
    for (i = 0; i < n; i++) { sl[i] = sq_brk_slice_of(&row[start + i], pen, n_slices); vel[i] = row[start + i].velocity; }
    for (i = 0; i < n; i++) {
        uint32_t src = (i * 2u) % (n ? n : 1u);
        if (row[start + i].flags & SQ_STEP_LOCK) continue;
        sq_brk_step(row, (uint8_t)(start + i), sl[src], pen, n_slices, 100u, vel[src]);
    }
}
void sq_brk_backwards(sq_step_t *row, uint8_t start, uint8_t length)
{
    uint32_t i, n = length > start ? (uint32_t)(length - start) : 0u;
    for (i = 0; i < n / 2u; i++) {
        sq_step_t t = row[start + i];
        if ((row[start + i].flags & SQ_STEP_LOCK) || (row[start + n - 1u - i].flags & SQ_STEP_LOCK)) continue;   /* locked: not moved */
        row[start + i] = row[start + n - 1u - i];
        row[start + n - 1u - i] = t;
    }
}
