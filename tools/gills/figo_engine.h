/* FIGO for the Gills - the engine (class-body code: it goes into the variations object after scena_engine.h, and
 * follows SCENA's clock). The same machine as FIGO on norns (tools/norns/figo/figo.lua): the loop comes in and it varies
 * it by itself, in time, one decision a beat. FIGO says how often, CARATTERE goes from dub (long repeats, reverse at
 * half speed, an octave down, tape stops, echoes thrown) to glitch (1/16 and 1/32, rolls that rise, sixteenths
 * shuffled, gates, an octave up), MEMORIA brings back a bar of a few bars ago. Here it goes sample by sample: no
 * softcut, nothing to wait for.
 *
 * The tape: the input, always (FG_N frames, L and R as 16 bits, SDRAM). Voice A is what is heard: the dry (insert; in
 * aux silence, the dry is on the mixer already) or the tape somewhere, at some speed, in a loop. Voice B is MEMORIA,
 * under it. A change is a crossfade that ends where it goes: what it goes to plays whole from its first sample, it
 * fades in over what comes before it, so the attack of a beat is never faded. In aux all of it comes fg_rt samples
 * early, what the way to the mixer and back takes: the repeats land on the dry's grid there.
 *
 * The decisions are taken a beat ahead (on SCENA's beat, for the next one): an event that takes the place of the dry
 * has crossfaded before its beat. The times are frames of the tape (fg_now: the sample now), so a START from SAGGA
 * (the beat count back to 0) changes nothing of what is going on.
 * No libm, no doubles. FG_COLD marks what does not run sample by sample.
 * SPDX-License-Identifier: GPL-3.0-only */

#ifndef FG_BITS
#define FG_BITS 21                       /* 2^21 frames: 43.7 s */
#endif
#ifndef FG_COLD
#define FG_COLD
#endif
#ifndef FG_HOT
#define FG_HOT
#endif
#ifndef FG_FN
#define FG_FN
#endif
#ifndef FG_RO
#define FG_RO
#endif

enum {
    FG_N = 1 << FG_BITS,
    FG_XF = 96,                          /* the crossfade: 2 ms */
    FG_LEAD = FG_XF + SC_BS,             /* a jump starts this early, in the block before */
    /* what A does */
    FG_NONE = 0, FG_R4, FG_R8, FG_R16, FG_R32, FG_ROLL, FG_REV, FG_HALF, FG_STOP, FG_OCT, FG_SHUF, FG_GATE, FG_SKIP,
    FG_KINDS,
    FG_HOLD = 20, FG_TSTOP, FG_SPIN, FG_DRY,
    /* what B does */
    FG_MEMO = 1, FG_ECO = 2
};

struct FgHead { uint32_t i; float f, r; bool dry; };
struct FgVoice {
    FgHead h, o;                         /* the head heard, and the one fading out */
    int xf;                              /* samples of the crossfade left */
    float xr;                            /* 1 / its length */
    bool loop;                           /* h loops [ls, ls + len) */
    uint32_t ls;
    float len;
    float g, gt, gk;                     /* the level of the tape: now, target, slew a sample */
    float rt, rk;                        /* the speed: target, slew a sample (0: none) */
};

uint32_t *fg_tape;
uint32_t fg_now;                         /* the frame of the sample now (written before the heads read) */
uint32_t fg_fill;                        /* frames on the tape */
float fg_xl, fg_xr;                      /* the input now, exact (the tape has it as 16 bits) */
FgVoice fg_a, fg_b;
bool fg_bon;                             /* B plays */
float fg_gate, fg_gate_t;                /* GATE: the level of the dry */
int fg_aux;                              /* 0 insert, 1 aux */
uint32_t fg_rt;                          /* aux: the way to the mixer and back, samples */
ScSvf fg_fl, fg_fr;                      /* B's filter */
ScSvfC fg_fc;
bool fg_fbp;                             /* B's filter: band pass (else low pass) */

/* the knobs, 0..1 (fg_lv 0..1.5) */
float fg_figo, fg_car, fg_mem, fg_lv, fg_lvm;
int fg_phrase;                           /* 8 16 32 */
int fg_out_kind;                         /* the way out (PULITO): 0 auto, 1 tape stop, 2 backspin, 3 dry */

/* the brain */
uint32_t fg_rng;
int32_t fg_poff;                         /* the phrase starts at this beat */
int fg_pb;                               /* the beat in the phrase now */
bool fg_on;                              /* false: PULITO */
bool fg_hold;
bool fg_req_hold, fg_req_unhold, fg_req_out;
int fg_ev;                               /* on A */
uint32_t fg_t0, fg_t1;                   /* its beat, its end (frames of the tape) */
float fg_L, fg_bl;                       /* its beats; the beat then, samples */
int fg_step;
uint32_t fg_tn;                          /* when its next step lands */
int fg_lead;                             /* how early that step starts */
uint32_t fg_ls;                          /* a slice (frames) */
float fg_len;
int fg_x;                                /* GATE's pattern; ROLL: it rises; HOLD: the loop's speed */
int fg_nx;                               /* the next event, starting where this one ends */
uint32_t fg_nx_t0;
float fg_nx_L;
int fg_bev;                              /* on B */
uint32_t fg_bt0, fg_bt1, fg_btn;
int fg_bstep, fg_breps, fg_bn;
float fg_blv, fg_bfc, fg_bh;
int fg_last;                             /* the event shown (a kind, or 0) */
int fg_last_n;                           /* INDIETRO / MEMORIA: how many bars back */
uint32_t fg_bts[64];                     /* the first frame of the last 64 beats */
uint32_t fg_nbt;                         /* how many beats so far */

/* ---------------------------------------------------------------------------------------------- small maths */
FG_FN inline uint32_t fg_rand() { fg_rng ^= fg_rng << 13; fg_rng ^= fg_rng >> 17; fg_rng ^= fg_rng << 5; return fg_rng; }
FG_FN inline float fg_frand() { return (float)(fg_rand() >> 8) * (1.f / 16777216.f); }   /* 0..1 */
FG_FN inline int fg_irand(int n) { int k = (int)(fg_frand() * (float)n); return k >= n ? n - 1 : k; }
/* log2 for x > 0 (error ~1e-4), x^y = 2^(y log2 x) */
FG_FN static inline float fg_log2(float x) {
    union { float f; uint32_t u; } v;
    v.f = x;
    int e = (int)((v.u >> 23) & 255u) - 127;
    v.u = (v.u & 0x007FFFFFu) | 0x3F800000u;
    float m = v.f;
    return (float)e - 1.7417939f + (2.8212026f + (-1.4699568f + (0.44717955f - 0.056570851f * m) * m) * m) * m;
}
FG_FN static inline float fg_pow(float x, float y) { return x <= 0.f ? 0.f : sc_exp2(y * fg_log2(x)); }

/* ------------------------------------------------------------------------------------------------- the tape */
FG_FN static inline int32_t fg_s16(int32_t q27) {
    q27 >>= 12;
    return q27 > 32767 ? 32767 : (q27 < -32768 ? -32768 : q27);
}
FG_FN static inline uint32_t fg_pack(int32_t l, int32_t r) {
    return (uint32_t)(uint16_t)(int16_t)fg_s16(l) | ((uint32_t)(uint16_t)(int16_t)fg_s16(r) << 16);
}
/* frame i: from the tape, or the input itself if it is the frame now (or not there yet) */
#ifdef FG_TEST
uint32_t fg_test_ahead;                  /* (the test: reads of frames not on the tape yet) */
#endif
FG_FN inline void fg_frame(uint32_t i, float &l, float &r) {
    if ((int32_t)(i - fg_now) >= 0) {
#ifdef FG_TEST
        if (i != fg_now) fg_test_ahead++;
#endif
        l = fg_xl; r = fg_xr; return;
    }
    uint32_t w = fg_tape[i & (uint32_t)(FG_N - 1)];
    l = (float)(int16_t)(w & 0xFFFFu) * (1.f / 32768.f);
    r = (float)(int16_t)(w >> 16) * (1.f / 32768.f);
}
FG_FN inline void fg_read(const FgHead &h, float &l, float &r) {
    fg_frame(h.i, l, r);
    if (h.f > 0.f) {
        float l1, r1;
        fg_frame(h.i + 1, l1, r1);
        l += h.f * (l1 - l); r += h.f * (r1 - r);
    }
}
FG_FN static inline void fg_place(FgHead &h, uint32_t base, float off, float r) {   /* h at base + off, speed r */
    int k = (int)off;
    if ((float)k > off) k--;
    h.i = base + (uint32_t)k; h.f = off - (float)k; h.r = r; h.dry = false;
}
FG_FN inline void fg_adv(FgHead &h) {
    if (h.dry) return;
    float f = h.f + h.r;
    int k = (int)f;
    if ((float)k > f) k--;
    h.i += (uint32_t)k; h.f = f - (float)k;
}

/* --------------------------------------------------------------------------------- the voices, sample by sample */
/* what voice v gives now: the dry (dg: how much of it is heard) or the tape (at its level), crossfaded */
FG_FN inline void fg_out(FgVoice &v, float dg, float &l, float &r) {
    v.g += (v.gt - v.g) * v.gk;
    if (v.h.dry) { l = fg_xl * dg; r = fg_xr * dg; }
    else { fg_read(v.h, l, r); l *= v.g; r *= v.g; }
    if (v.xf > 0) {
        float w = (float)v.xf * v.xr, l2, r2;
        if (v.o.dry) { l2 = fg_xl * dg; r2 = fg_xr * dg; }
        else { fg_read(v.o, l2, r2); l2 *= v.g; r2 *= v.g; }
        l += w * (l2 - l); r += w * (r2 - r);
    }
}
/* the loop: the head lands back on its start in FG_XF samples, so the start plays whole (reverse: on its end) */
FG_FN inline void fg_wrap(FgVoice &v, float rel_after, float r) {
    v.o = v.h;
    fg_place(v.h, v.ls, rel_after - (float)FG_XF * r, r);
    v.xf = FG_XF; v.xr = 1.f / (float)FG_XF;
}
/* after the sample: the heads on, the speed's slew, the loop. rd: where the dry is, ahead of the head (aux: fg_rt) */
FG_FN inline void fg_next(FgVoice &v, uint32_t rd) {
    if (!v.h.dry) {
        if (v.rk != 0.f) v.h.r += (v.rt - v.h.r) * v.rk;
        fg_adv(v.h);
    }
    if (v.xf > 0) { fg_adv(v.o); v.xf--; return; }          /* (no wrap while it crossfades: loops are longer) */
    if (!v.loop) return;
    float r = v.h.dry ? 1.f : v.h.r;
    float rel = v.h.dry ? (float)(int32_t)(fg_now + 1 + rd - v.ls) : (float)(int32_t)(v.h.i - v.ls) + v.h.f;
    float x = (float)FG_XF * r;                              /* where it is after the crossfade, minus where now */
    if (r > 0.f) {
        if (rel >= v.len - x) { float a = rel + x; while (a >= v.len) a -= v.len; fg_wrap(v, a, r); }
    } else if (r < 0.f) {
        if (rel <= -x) { float a = rel + x; while (a < 0.f) a += v.len; fg_wrap(v, a, r); }
    }
}

/* ------------------------------------------------------------------------------- the voices, block by block */
/* (the times here are where a change lands, in samples of the output: the grid minus fg_rt in aux) */
FG_FN inline uint32_t fg_out_t(uint32_t t) { return t - (fg_aux ? fg_rt : 0u); }
FG_FN static inline int fg_xlen(int32_t d) { return d > 16 ? (int)d : 16; }
/* v lands on tape frame P (+pf) at time T, at speed r: from now it crossfades over what comes before it. No loop
   (the caller sets one after) */
FG_COLD void fg_go(FgVoice &v, uint32_t T, uint32_t P, float pf, float r) {
    int32_t d = (int32_t)(T - fg_now);
    v.o = v.h;
    fg_place(v.h, P, pf - (float)d * r, r);                  /* (late: further on, where it would be) */
    v.xf = fg_xlen(d); v.xr = 1.f / (float)v.xf;
    v.rk = 0.f; v.loop = false;
}
/* v plays from the head (what was just recorded) at speed r, whole by time T */
FG_COLD void fg_go_head(FgVoice &v, uint32_t T, float r) {
    int32_t d = (int32_t)(T - fg_now);
    v.o = v.h;
    fg_place(v.h, fg_now - 2u, 0.f, r);
    v.xf = fg_xlen(d); v.xr = 1.f / (float)v.xf;
    v.rk = 0.f; v.loop = false;
}
/* v back to the dry by time T (B: to silence) */
FG_COLD void fg_go_dry(FgVoice &v, uint32_t T) {
    v.loop = false; v.rk = 0.f;
    if (v.h.dry) return;
    int32_t d = (int32_t)(T - fg_now);
    v.o = v.h;
    v.h.dry = true; v.h.i = fg_now; v.h.f = 0.f; v.h.r = 1.f;
    v.xf = fg_xlen(d); v.xr = 1.f / (float)v.xf;
}
/* v's loop from now: [ls, ls + len). If at T the head would be past the new end it lands on its start then */
FG_COLD void fg_loop_at(FgVoice &v, uint32_t T, uint32_t ls, float len) {
    float r = v.h.dry ? 1.f : v.h.r;
    int32_t d = (int32_t)(T - fg_now);
    uint32_t rd = fg_aux ? fg_rt : 0u;
    float rel = v.h.dry ? (float)(int32_t)(fg_now + rd - ls) : (float)(int32_t)(v.h.i - ls) + v.h.f;
    float relT = rel + (float)d * r;
    v.ls = ls; v.len = len < (float)(3 * FG_XF) ? (float)(3 * FG_XF) : len;
    v.loop = true;
    if (r > 0.f && relT >= v.len - (float)FG_XF * r) {
        float a = relT;
        while (a >= v.len) a -= v.len;
        fg_go(v, T, ls, a, r);
        v.loop = true;
    }
}
FG_COLD void fg_level(FgVoice &v, float to, float samples) {
    v.gt = to;
    v.gk = samples > 1.f ? 6.9078f / samples : 1.f;          /* (one pole: -60 dB in that time) */
    if (v.gk > 1.f) v.gk = 1.f;
}
FG_COLD void fg_speed(FgVoice &v, float to, float samples) {
    v.rt = to;
    v.rk = samples > 1.f ? 6.9078f / samples : 1.f;
    if (v.rk > 1.f) v.rk = 1.f;
}

/* ------------------------------------------------------------------------------------------- the setup */
FG_COLD void fg_init(uint32_t *tape) {
    fg_tape = tape;
    for (uint32_t i = 0; i < (uint32_t)FG_N; i++) fg_tape[i] = 0u;
    fg_now = 0; fg_fill = 0; fg_xl = fg_xr = 0.f;
    FgHead d = {0u, 0.f, 1.f, true};
    fg_a.h = fg_a.o = d; fg_a.xf = 0; fg_a.xr = 1.f; fg_a.loop = false; fg_a.ls = 0; fg_a.len = 1.f;
    fg_a.g = fg_a.gt = 1.f; fg_a.gk = 1.f; fg_a.rt = 1.f; fg_a.rk = 0.f;
    fg_b = fg_a;
    fg_b.g = fg_b.gt = 0.f;
    fg_bon = false;
    fg_gate = fg_gate_t = 1.f;
    fg_aux = 0; fg_rt = 0;
    ScSvf z = {0.f, 0.f};
    fg_fl = fg_fr = z;
    sc_svf_set(fg_fc, 2000.f, 0.7f);
    fg_fbp = false;
    fg_figo = 0.f; fg_car = 0.3f; fg_mem = 0.f; fg_lv = 1.f; fg_lvm = 0.6f;
    fg_phrase = 16; fg_out_kind = 0;
    fg_rng = 0x2545F491u;
    fg_poff = 0; fg_pb = 0;
    fg_on = true; fg_hold = false;
    fg_req_hold = fg_req_unhold = fg_req_out = false;
    fg_ev = FG_NONE; fg_t0 = fg_t1 = 0; fg_L = 1.f; fg_bl = (float)SC_SR * 0.5f;
    fg_step = 0; fg_tn = 0; fg_lead = FG_LEAD; fg_ls = 0; fg_len = 1.f; fg_x = 0;
    fg_nx = FG_NONE; fg_nx_t0 = 0; fg_nx_L = 1.f;
    fg_bev = 0; fg_bt0 = fg_bt1 = fg_btn = 0; fg_bstep = 0; fg_breps = 0; fg_bn = 1;
    fg_blv = 0.f; fg_bfc = 3000.f; fg_bh = 1.f;
    fg_last = 0; fg_last_n = 0;
    for (int i = 0; i < 64; i++) fg_bts[i] = 0;
    fg_nbt = 0;
#ifdef FG_TEST
    fg_test_ahead = 0;
#endif
}

/* the first frame of the beat k beats before frame nt (the next beat): where it really was, if the beats since then
   kept the tempo; else as the tempo says */
FG_COLD uint32_t fg_back(uint32_t nt, int k) {
    if (k >= 1 && k <= 64 && (uint32_t)k <= fg_nbt) {
        uint32_t f = fg_bts[(fg_nbt - (uint32_t)k) & 63u];
        float d = (float)(int32_t)(nt - f) - (float)k * fg_bl;
        if (d < 0.03f * fg_bl && d > -0.03f * fg_bl) return f;
    }
    return nt - (uint32_t)((float)k * fg_bl + 0.5f);
}

/* ------------------------------------------------------------------------------------- what can happen */
/* each event's weight, dub to glitch, as on norns; f: it grows with FIGO to this power; minL: beats at least;
   end: only at the end of a phrase (or, less, of a bar); dry: it cuts the dry (not in aux); div: a repeat */
struct FgKind { float dub, gl, div; uint8_t f, minL, end, dry; };
FG_FN static const FgKind &fg_kind(int k) {
    FG_RO static const FgKind K[FG_KINDS] = {
        {0.f, 0.f, 0.f, 0, 0, 0, 0},
        {1.0f, 0.3f, 1.f, 0, 1, 0, 0},       /* 1/4 */
        {0.8f, 0.8f, 0.5f, 0, 0, 0, 0},      /* 1/8 */
        {0.2f, 1.0f, 0.25f, 1, 0, 0, 0},     /* 1/16 */
        {0.0f, 0.6f, 0.125f, 2, 0, 0, 0},    /* 1/32 */
        {0.2f, 0.8f, 0.f, 1, 1, 0, 0},       /* ROLL */
        {1.0f, 0.5f, 0.f, 0, 0, 0, 0},       /* REVERSE */
        {0.8f, 0.2f, 0.f, 0, 0, 0, 0},       /* OTTAVA - */
        {0.6f, 0.0f, 0.f, 0, 1, 1, 0},       /* TAPE STOP */
        {0.1f, 0.6f, 0.f, 0, 0, 0, 0},       /* OTTAVA + */
        {0.0f, 1.0f, 0.f, 1, 0, 0, 0},       /* SHUFFLE */
        {0.2f, 0.7f, 0.f, 0, 0, 0, 1},       /* GATE */
        {0.5f, 0.5f, 0.f, 0, 1, 0, 0},       /* INDIETRO */
    };
    return K[k > 0 && k < FG_KINDS ? k : 0];
}
FG_FN static const char *fg_name(int k) {
    FG_RO static const char *const N[FG_KINDS] = {"", "1/4", "1/8", "1/16", "1/32", "ROLL", "REVERSE", "OTTAVA -",
                                            "TAPE STOP", "OTTAVA +", "SHUFFLE", "GATE", "INDIETRO"};
    if (k == FG_HOLD) return "HOLD";
    if (k == FG_TSTOP) return "TAPE STOP";
    if (k == FG_SPIN) return "BACKSPIN";
    return N[k > 0 && k < FG_KINDS ? k : 0];
}

/* how likely an event is on beat b of an n-beat phrase: few on the ones, more at the end of bars, most at the end
   of the phrase. Then which, and how long (half a beat, one, two; never past the phrase's end). L: 0 = none */
FG_COLD int fg_pick(int b, int n, float f, float c, float &L) {
    FG_RO static const float W16[16] = {0.3f, 0.7f, 0.8f, 1.3f, 0.4f, 0.7f, 0.8f, 1.5f,
                                  0.4f, 0.7f, 0.8f, 1.3f, 0.6f, 0.9f, 1.4f, 2.6f};
    L = 0.f;
    if (f <= 0.f) return FG_NONE;
    float p = fg_pow(f, 1.6f) * 0.55f * W16[(b * 16 / n) & 15];
    if (p > 0.9f) p = 0.9f;
    if (fg_frand() >= p) return FG_NONE;
    int left = n - b;
    float wl[3] = {0.3f, 0.5f, left == 2 ? 0.9f : 0.2f};
    float ls[3] = {0.5f, 1.f, 2.f};
    float tot = 0.f;
    int nc = 0;
    for (int i = 0; i < 3; i++) if (ls[i] <= (float)(left < 2 ? left : 2)) { tot += wl[i]; nc = i + 1; }
    if (nc == 0) return FG_NONE;
    float r = fg_frand() * tot;
    L = ls[nc - 1];
    for (int i = 0; i < nc; i++) { r -= wl[i]; if (r <= 0.f) { L = ls[i]; break; } }
    bool ends_phrase = (float)b + L == (float)n;
    float eb = (float)b + L;
    bool ends_bar = (eb == (float)(int)eb) && ((int)eb % 4 == 0);
    float ws[FG_KINDS], sum = 0.f;
    ws[0] = 0.f;
    for (int k = 1; k < FG_KINDS; k++) {
        const FgKind &e = fg_kind(k);
        float w = e.dub * (1.f - c) + e.gl * c;
        if (e.f == 1) w *= f; else if (e.f == 2) w *= f * f;
        if (e.minL && L < (float)e.minL) w = 0.f;
        if (e.end && !ends_phrase) w = ends_bar ? w * 0.3f : 0.f;
        if (e.dry && fg_aux) w = 0.f;
        if (e.div > 0.f && fg_aux && (L < 2.f * e.div || e.div * fg_bl < (float)(fg_rt + 3 * FG_XF))) w = 0.f;
        ws[k] = w; sum += w;
    }
    if (sum <= 0.f) { L = 0.f; return FG_NONE; }
    r = fg_frand() * sum;
    for (int k = 1; k < FG_KINDS; k++) { r -= ws[k]; if (r <= 0.f && ws[k] > 0.f) return k; }
    L = 0.f;
    return FG_NONE;
}
/* MEMORIA or ECO, on the first beat of a bar: more likely in the phrase's last bar */
FG_COLD int fg_pick_b(int b, int n, float m, float c, float &L) {
    L = 0.f;
    if (m <= 0.f || b % 4 != 0) return 0;
    bool last = b >= n - 4;
    float p = m * (last ? 0.7f : 0.45f);
    if (p > 0.85f) p = 0.85f;
    if (fg_frand() >= p) return 0;
    float eco_w = (1.f - c) * (last ? 1.5f : 0.6f) + c * 0.3f;
    if (fg_frand() * (1.f + eco_w) < eco_w) { L = (float)(n - b < 4 ? n - b : 4); return FG_ECO; }
    FG_RO static const float ML[3] = {2.f, 4.f, 8.f};
    float l = ML[fg_irand(3)];
    L = l < (float)(n - b) ? l : (float)(n - b);
    return FG_MEMO;
}
/* SHUFFLE, step i: may sixteenth j of the bar before play backwards? It starts at its end, which must be on the tape
   when the crossfade into it starts (the last ones of the bar not at once) */
FG_COLD bool fg_shuf_rev_ok(int j, int i, float sx, float bar) {
    return (float)(j + 1 - i) * sx <= bar - (float)(2 * FG_LEAD) - (float)(fg_aux ? fg_rt : 0u) - 4.f;
}
/* the tape holds what an event wants, `back` frames behind and `ahead` beyond its start */
FG_FN inline bool fg_has(float back) { return back + 4.f * (float)FG_LEAD < (float)fg_fill && back < (float)(FG_N - 4 * FG_LEAD); }

/* -------------------------------------------------------------------------------------------- the events */
/* event k starts at t0 for L beats: what A does, step by step. A step lands at fg_tn; it starts fg_lead early */
FG_COLD bool fg_start(int k, uint32_t t0, float L) {
    float bl = fg_bl, bar = 4.f * bl;
    float dur = L * bl;
    switch (k) {
        case FG_ROLL: if (!fg_has(bl + dur)) return false; break;
        case FG_REV: case FG_HALF: case FG_STOP: if (!fg_has(dur + bl)) return false; break;
        case FG_OCT: if (!fg_has(bl)) return false; break;
        case FG_SHUF: if (!fg_has(bar + dur)) return false; break;
        case FG_SKIP: {
            FG_RO static const int NB[3] = {1, 2, 4};
            int n = NB[fg_irand(3)];
            if (!fg_has((float)n * bar + dur)) { n = 1; if (!fg_has(bar + dur)) return false; }
            fg_last_n = n; fg_ls = fg_back(t0, 4 * n);
            break;
        }
        case FG_HOLD: if (!fg_has(2.f * bl)) return false; break;
        default: if (k >= FG_R4 && k <= FG_R32 && !fg_has(dur)) return false; break;
    }
    fg_ev = k; fg_t0 = t0; fg_L = L; fg_t1 = t0 + (uint32_t)(dur + 0.5f);
    fg_step = 0; fg_tn = t0; fg_lead = FG_LEAD;
    fg_last = k;
    fg_a.g = fg_a.gt = fg_lv; fg_a.gk = 1.f;
    if (k == FG_ROLL) fg_x = (fg_car > 0.6f && fg_figo > 0.5f) ? 1 : 0;
    if (k == FG_GATE) { fg_x = (int)(fg_rand() & 255u) | 0x11; fg_lead = 0; }
    return true;
}
/* the end of what A does: the dry, or the next event if it starts right here (it goes there from what plays); one
   that starts later is set up, A goes dry until then */
FG_COLD void fg_end() {
    fg_gate_t = 1.f;
    fg_ev = FG_NONE;
    int k = fg_nx;
    fg_nx = FG_NONE;
    int32_t gap = (int32_t)(fg_nx_t0 - fg_t1);
    bool here = k != FG_NONE && gap <= 32 && gap >= -32;
    if (!here) fg_go_dry(fg_a, fg_out_t(fg_t1));
    if (k != FG_NONE && !fg_start(k, fg_nx_t0, fg_nx_L) && here) fg_go_dry(fg_a, fg_out_t(fg_t1));
}
/* one step of the event on A, when it is due */
FG_COLD void fg_step_a() {
    uint32_t T = fg_out_t(fg_tn);
    float bl = fg_bl;
    if (fg_tn == fg_t1 && fg_step >= 0 && fg_ev != FG_HOLD) {
        if (fg_ev == FG_GATE) fg_gate_t = 1.f;
        fg_end();
        return;
    }
    switch (fg_ev) {
        case FG_R4: case FG_R8: case FG_R16: case FG_R32: {
            /* the slice that starts on the beat plays (it is the dry), then repeats until the end */
            float s = fg_kind(fg_ev).div * bl;
            fg_go_dry(fg_a, T);
            fg_loop_at(fg_a, T, fg_t0, s);
            fg_tn = fg_t1;
            break;
        }
        case FG_ROLL: {
            /* 1/4, 1/8, 1/16, 1/32 a quarter of the event each; with glitch it rises too, in the second half */
            FG_RO static const float D[4] = {1.f, 0.5f, 0.25f, 0.125f};
            if (fg_step == 0) fg_go_dry(fg_a, T);
            fg_loop_at(fg_a, T, fg_t0, D[fg_step] * bl);
            if (fg_step == 2 && fg_x) fg_speed(fg_a, 1.5f, fg_L * bl * 0.5f);
            fg_step++;
            fg_tn = fg_step < 4 ? fg_t0 + (uint32_t)(fg_L * bl * (float)fg_step * 0.25f + 0.5f) : fg_t1;
            break;
        }
        case FG_REV: {
            /* what was just played, backwards (dub: at half speed) */
            fg_go_head(fg_a, T, fg_car < 0.35f ? -0.5f : -1.f);
            fg_tn = fg_t1;
            break;
        }
        case FG_HALF:
            fg_go_head(fg_a, T, 0.5f);                       /* an octave down: it falls behind, never past the head */
            fg_tn = fg_t1;
            break;
        case FG_STOP: case FG_TSTOP: {
            /* the tape slows down to almost nothing; at the end the level goes too */
            float d = fg_L * bl;
            if (fg_step == 0) {
                fg_go_head(fg_a, T, 1.f);
                fg_speed(fg_a, 0.03f, d * 0.85f);
                fg_step = 1;
                fg_tn = fg_t0 + (uint32_t)(d * 0.75f + 0.5f);
                fg_lead = 0;
            } else {
                fg_level(fg_a, 0.f, d * 0.22f);
                fg_tn = fg_t1; fg_lead = FG_LEAD;
            }
            break;
        }
        case FG_SPIN:
            /* backspin: backwards, faster and faster */
            fg_go_head(fg_a, T, -1.f);
            fg_speed(fg_a, -2.5f, bl * 0.15f);
            fg_tn = fg_t1;
            break;
        case FG_OCT: {
            /* an octave up: the last half beat at double speed, over and over */
            float h = bl * 0.5f;
            uint32_t ls = fg_t0 - (uint32_t)(h + 0.5f);
            fg_go(fg_a, T, ls, 0.f, 2.f);
            fg_a.ls = ls; fg_a.len = h; fg_a.loop = true;
            fg_tn = fg_t1;
            break;
        }
        case FG_SHUF: {
            /* the sixteenths of the bar just gone, in a new order (some backwards) */
            float sx = bl * 0.25f, bar = 4.f * bl;
            int j = fg_irand(16);
            uint32_t ls = fg_back(fg_t0, 4) + (uint32_t)((float)j * sx + 0.5f);
            bool rev = fg_frand() < 0.15f && fg_shuf_rev_ok(j, fg_step, sx, bar);
            if (rev) fg_go(fg_a, T, ls, sx, -1.f);
            else fg_go(fg_a, T, ls, 0.f, 1.f);
            fg_a.ls = ls; fg_a.len = sx; fg_a.loop = true;
            fg_step++;
            int steps = (int)(fg_L * 4.f + 0.5f);
            fg_tn = fg_step < steps ? fg_t0 + (uint32_t)((float)fg_step * sx + 0.5f) : fg_t1;
            break;
        }
        case FG_GATE: {
            /* the dry cut in sixteenths: the first of each beat always plays */
            float sx = bl * 0.25f;
            fg_gate_t = ((fg_x >> (fg_step % 8)) & 1) ? 1.f : 0.f;
            fg_step++;
            int steps = (int)(fg_L * 4.f + 0.5f);
            fg_tn = fg_step < steps ? fg_t0 + (uint32_t)((float)fg_step * sx + 0.5f) : fg_t1;
            if (fg_tn == fg_t1) fg_lead = 256;                   /* (the dry whole again by the end: 5 ms before) */
            break;
        }
        case FG_SKIP:
            /* what played 1, 2 or 4 bars ago, in time, in place of the loop */
            fg_go(fg_a, T, fg_ls, 0.f, 1.f);
            fg_tn = fg_t1;
            break;
        case FG_HOLD: {
            /* the beat just gone, over and over; with FIGO up it varies by itself on every beat. Let go: the dry on
               this beat */
            if (fg_req_unhold) {
                fg_req_unhold = false; fg_hold = false;
                fg_t1 = fg_tn;
                fg_end();
                break;
            }
            float L = bl;
            uint32_t ls = fg_ls;
            float r = 1.f, len = L;
            if (fg_step > 0 && fg_frand() < fg_figo * 0.7f) {
                float x = fg_frand();
                if (x < 0.45f) { FG_RO static const float DV[3] = {0.5f, 0.25f, 0.125f}; len = L * DV[fg_irand(fg_car > 0.5f ? 3 : 2)]; }
                else if (x < 0.7f) r = -1.f;
                else if (x < 0.85f) r = fg_car > 0.5f ? 2.f : 0.5f;
            }
            if (r < 0.f) fg_go(fg_a, T, ls, len, r);
            else fg_go(fg_a, T, ls, 0.f, r);
            fg_a.ls = ls; fg_a.len = len; fg_a.loop = true;
            fg_x = r > 1.5f ? 2 : (r < 0.f ? -1 : 1);
            fg_step++;
            fg_tn = fg_tn + (uint32_t)(bl + 0.5f);
            fg_t1 = fg_tn;                                   /* (it goes on until it is let go) */
            break;
        }
        case FG_DRY:
            fg_end();
            break;
        default:
            fg_end();
            break;
    }
}

/* MEMORIA (a bar of 1, 2, 4 or 8 bars ago, under, filtered, left and right swapped) and ECO (the coming half beat
   repeated, darker and quieter each time) on B */
FG_COLD bool fg_start_b(int k, uint32_t t0, float L) {
    float bl = fg_bl, bar = 4.f * bl;
    if (k == FG_MEMO) {
        FG_RO static const int NB[4] = {1, 2, 4, 8};
        int n = NB[fg_irand(4)];
        while (n > 1 && !fg_has((float)n * bar + L * bl)) n >>= 1;
        if (!fg_has((float)n * bar + L * bl)) return false;
        float r = (fg_car > 0.8f && fg_frand() < 0.3f && (float)n * bar > L * bl + 0.1f * SC_SR) ? 2.f : 1.f;
        fg_bn = n; fg_bh = r;
    } else {
        fg_bh = fg_car < 0.5f ? bl * 0.75f : bl * 0.5f;
        if (!fg_has(fg_bh * 2.f)) return false;
    }
    fg_bev = k; fg_bt0 = t0; fg_bt1 = t0 + (uint32_t)(L * bl + 0.5f);
    fg_bstep = 0; fg_btn = k == FG_ECO ? t0 + (uint32_t)(fg_bh + 0.5f) : t0;
    fg_bon = true;
    return true;
}
FG_COLD void fg_b_filter(bool bp, float fc, float q) {
    fg_fbp = bp;
    sc_svf_set(fg_fc, fc, q);
}
FG_COLD void fg_step_b() {
    uint32_t T = fg_out_t(fg_btn);
    float bl = fg_bl;
    if (fg_bev == FG_MEMO) {
        if (fg_bstep == 0) {
            float c = fg_car;
            if (c < 0.5f) fg_b_filter(false, 700.f + 2600.f * c, 0.667f);
            else fg_b_filter(true, 1200.f + 3000.f * (c - 0.5f) * 2.f, 0.833f);
            uint32_t P = fg_back(fg_bt0, 4 * fg_bn);
            fg_go(fg_b, T, P, 0.f, fg_bh);
            fg_b.g = 0.f;
            fg_level(fg_b, fg_lvm * (0.4f + 0.6f * fg_mem), bl * 0.5f);
            fg_bstep = 1;
            float L = (float)(int32_t)(fg_bt1 - fg_bt0) / bl;
            fg_btn = fg_bt0 + (uint32_t)((L - 1.f) * bl + 0.5f);
        } else if (fg_bstep == 1) {
            fg_level(fg_b, 0.f, bl);
            fg_bstep = 2;
            fg_btn = fg_bt1;
        } else {
            fg_go_dry(fg_b, T);
            fg_bev = 0;
        }
        return;
    }
    /* ECO */
    if (fg_bstep == 0) {
        fg_b_filter(false, 3000.f, 0.667f);
        fg_bfc = 3000.f;
        fg_go(fg_b, T, fg_bt0, 0.f, 1.f);
        fg_b.ls = fg_bt0; fg_b.len = fg_bh; fg_b.loop = true;
        fg_blv = fg_lvm * (0.5f + 0.5f * fg_mem);
        fg_b.g = 0.f;
        fg_level(fg_b, fg_blv, 0.005f * SC_SR);
        float span = (float)(int32_t)(fg_bt1 - fg_bt0) - fg_bh;
        fg_breps = (int)(span / fg_bh);
        if (fg_breps < 2) fg_breps = 2;
        fg_bstep = 1;
        fg_btn = fg_btn + (uint32_t)(fg_bh + 0.5f);
    } else if (fg_bstep <= fg_breps) {
        /* every repeat darker and quieter; the last one fades out */
        fg_blv *= 0.7f; fg_bfc *= 0.75f;
        if (fg_bstep == fg_breps) fg_level(fg_b, 0.f, fg_bh);
        else fg_level(fg_b, fg_blv, fg_bh * 0.5f);
        fg_b_filter(false, fg_bfc, 0.667f);
        fg_bstep++;
        fg_btn = fg_btn + (uint32_t)(fg_bh + 0.5f);
    } else {
        fg_go_dry(fg_b, T);
        fg_bev = 0;
    }
    (void)bl;
}
FG_COLD void fg_stop_b(float samples) {
    if (!fg_bon) return;
    fg_level(fg_b, 0.f, samples);
    fg_bev = 0;
}

/* --------------------------------------------------------------------------------------------- the brain */
/* on SCENA's beat: what happens on the next one */
FG_COLD void fg_brain() {
    float blen = beat_len;
    uint32_t bt = fg_now - (uint32_t)(frac * blen + 0.5f);   /* this beat's first frame */
    fg_bts[fg_nbt & 63u] = bt;
    fg_nbt++;
    if (fg_nbt > 8) {                                        /* the beats' own pace, steadier than the ticks' */
        float l8 = (float)(int32_t)(bt - fg_bts[(fg_nbt - 9u) & 63u]) * 0.125f;
        float e = l8 - blen;
        if (e < 0.02f * blen && e > -0.02f * blen) blen = l8;
    }
    uint32_t nt = bt + (uint32_t)(blen + 0.5f);              /* the next one's */
    int n = fg_phrase;
    int32_t pb = beat - fg_poff;
    int b = (int)(((pb % n) + n) % n);
    fg_pb = b;
    int nb = (b + 1) % n;
    fg_bl = blen;
    if (fg_req_out) {                                        /* PULITO: out on the next beat, then the dry */
        fg_req_out = false;
        fg_nx = FG_NONE; fg_req_hold = false; fg_req_unhold = false; fg_hold = false;
        fg_stop_b(0.2f * SC_SR);
        int kind = fg_out_kind;
        if (kind == 0) kind = fg_car < 0.5f ? 1 : 2;
        fg_ev = FG_NONE;
        if (kind == 1) { if (fg_start(FG_TSTOP, nt, 1.f)) return; }
        else if (kind == 2) { if (fg_start(FG_SPIN, nt, 0.5f)) return; }
        fg_ev = FG_DRY; fg_t0 = nt; fg_t1 = nt; fg_tn = nt; fg_step = 0; fg_lead = FG_LEAD; fg_last = 0;
        return;
    }
    if (fg_req_hold) {                                       /* HOLD: from the next beat, the beat just gone */
        fg_req_hold = false;
        fg_nx = FG_NONE;
        fg_ls = bt;
        int was = fg_ev;
        fg_ev = FG_NONE;
        if (fg_start(FG_HOLD, nt, 1.f)) { fg_hold = true; fg_ls = bt; }
        else fg_ev = was;
        return;
    }
    if (fg_hold || fg_ev == FG_HOLD || fg_ev == FG_TSTOP || fg_ev == FG_SPIN || fg_ev == FG_DRY) return;
    if (!fg_on || fg_nbt <= 4) return;                       /* (a few beats first: the tempo, some tape) */
    if (fg_nx == FG_NONE && (fg_ev == FG_NONE || (int32_t)(fg_t1 - nt) <= 32)) {
        float L;
        int k = fg_pick(nb, n, fg_figo, fg_car, L);
        if (k != FG_NONE) {
            if (fg_ev == FG_NONE) fg_start(k, nt, L);
            else { fg_nx = k; fg_nx_t0 = nt; fg_nx_L = L; }
        }
    }
    if (!fg_bev && !(fg_bon && fg_b.g > 0.001f)) {
        float L;
        int k = fg_pick_b(nb, n, fg_mem, fg_car, L);
        if (k) fg_start_b(k, nt, L);
    }
}

/* once a block, after SCENA's clock: the brain on the beat, the steps that are due */
FG_COLD void fg_krate() {
    if (onbeat) fg_brain();
    for (int g = 0; g < 4 && fg_ev != FG_NONE; g++) {
        if ((int32_t)(fg_out_t(fg_tn) - fg_now) > fg_lead) break;
        fg_step_a();
    }
    for (int g = 0; g < 4 && fg_bev; g++) {
        if ((int32_t)(fg_out_t(fg_btn) - fg_now) > FG_LEAD) break;
        fg_step_b();
    }
    if (fg_bon && !fg_bev && fg_b.h.dry && fg_b.xf == 0) fg_bon = false;
    if (fg_bon && !fg_bev && fg_b.g < 0.0005f && fg_b.gt == 0.f) { fg_go_dry(fg_b, fg_now + 16); fg_b.xf = 0; fg_bon = false; }
}

/* HOLD (toggle), PULITO / VIA (toggle), the phrase from here */
FG_COLD void fg_hold_toggle() {
    if (fg_req_hold) fg_req_hold = false;                    /* (asked and not started yet: never mind) */
    else if (fg_hold || fg_ev == FG_HOLD) fg_req_unhold = true;
    else fg_req_hold = true;
}
FG_COLD void fg_pulito_toggle() {
    if (fg_on) { fg_on = false; fg_req_out = true; fg_req_hold = false; }
    else fg_on = true;
}
FG_COLD void fg_align() { fg_poff = beat; }

/* ---------------------------------------------------------------------------------------------- the audio */
/* in: what FIGO gets (insert: the chain; aux: the send). out: insert, the dry or the events in its place; aux, the
   events alone. The tape records the input always. Nothing going on: the input comes out as it is (insert) */
FG_HOT void fg_audio(const int32_t *inl, const int32_t *inr, int32_t *outl, int32_t *outr) {
    const float IN = 1.f / 134217728.f, OUT = 134217728.f;
    bool aidle = fg_a.h.dry && fg_a.xf == 0 && !fg_a.loop && fg_gate == 1.f && fg_gate_t == 1.f;
    uint32_t rd = fg_aux ? fg_rt : 0u;
    float dg = fg_aux ? 0.f : 1.f;
    for (int j = 0; j < SC_BS; j++) {
        fg_tape[fg_now & (uint32_t)(FG_N - 1)] = fg_pack(inl[j], inr[j]);
        if (aidle && !fg_bon) {
            outl[j] = fg_aux ? 0 : inl[j];
            outr[j] = fg_aux ? 0 : inr[j];
            fg_now++;
            continue;
        }
        fg_xl = inl[j] * IN; fg_xr = inr[j] * IN;
        float al, ar;
        if (aidle) { al = fg_xl * dg; ar = fg_xr * dg; }
        else {
            fg_gate += (fg_gate_t - fg_gate) * 0.036f;              /* (-60 dB in 4 ms) */
            float d = fg_gate - fg_gate_t;
            if (d < 0.0001f && d > -0.0001f) fg_gate = fg_gate_t;
            fg_out(fg_a, dg * fg_gate, al, ar);
            fg_next(fg_a, rd);
        }
        if (fg_bon) {
            float bl, br, hb;
            fg_out(fg_b, 0.f, bl, br);
            fg_next(fg_b, rd);
            float lp = sc_svf(fg_fl, fg_fc, bl, &hb, 0);
            bl = fg_fbp ? hb : lp;
            lp = sc_svf(fg_fr, fg_fc, br, &hb, 0);
            br = fg_fbp ? hb : lp;
            al += 0.15f * bl + 0.85f * br;                   /* the left of then on the right */
            ar += 0.85f * bl + 0.15f * br;
        }
        outl[j] = (int32_t)(sc_clamp(al, -1.f, 0.9999999f) * OUT);
        outr[j] = (int32_t)(sc_clamp(ar, -1.f, 0.9999999f) * OUT);
        fg_now++;
    }
    fg_fill = fg_fill + SC_BS > (uint32_t)FG_N ? (uint32_t)FG_N : fg_fill + SC_BS;
}
