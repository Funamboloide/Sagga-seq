/* SCENA - the engine (class-body code: it goes into the code.declaration of the patch's object, and into the host
 * test's class). An insert effect for the Ksoloti Gills: one knob (SCENA) from a break-down (left) through clean
 * (centre) to a build-up (right), like the Scene FX of a Pioneer RMX-1000, with the depth of every part set once on
 * the other nine knobs, like a scene of an Octatrack; MOTO makes it move by itself, in time (MIDI clock or tap).
 *
 * routing (the object's attribute in the Patcher; scena_aux.axp has it set): 0 insert, the dry passes (bit for bit in
 * the centre). 1 aux, for a mixer's send and return: the dry is on the mixer already, so it never comes out here (a
 * copy of it a millisecond or two late would comb the sound like a phaser). Out come the noise, the echo and the
 * reverb, and the loops of ROLL, FREEZE and the fills from their first repeat on (their first pass is the dry). The
 * filter and the crush shape what goes into the echo and the reverb, and the loops.
 *
 * Platform: hw_adc(i), hw_btn(i), hw_led(i, on), hw_setup() come from the patch (scena_platform.h) or the test.
 * No libm, no printf, no doubles: the Cortex-M4 has a single-precision FPU and the patch links almost nothing.
 * SPDX-License-Identifier: GPL-3.0-only */

enum {
    SC_SR = 48000,
    SC_BS = 16,                          /* BUFSIZE */
    SC_ECHO_N = 1 << 18,                 /* 5.46 s a channel */
    SC_ROLL_N = 1 << 17,                 /* 2.73 s a channel: the last beats, for ROLL and FREEZE */
    SC_RV_TOTAL = 2 * (1214 + 1293 + 1389 + 1475 + 605 + 480 + 4 * 23 + 2 * 23),
    SC_FADE = 96                         /* 2 ms at every loop wrap */
};

/* ---------------------------------------------------------------------------------------------- small maths */
static inline float sc_clamp(float x, float a, float b) { return x < a ? a : (x > b ? b : x); }
static inline float sc_abs(float x) { return x < 0.f ? -x : x; }
/* 2^x, x in [-24, 24] (error ~1e-4) */
static inline float sc_exp2(float x) {
    x = sc_clamp(x, -24.f, 24.f);
    int i = (int)x;
    if ((float)i > x) i--;
    float f = x - (float)i;
    float p = 1.f + f * (0.6931472f + f * (0.2402265f + f * (0.0555041f + f * 0.0096181f)));
    float s = 1.f;
    if (i >= 0) { while (i--) s *= 2.f; } else { while (i++) s *= 0.5f; }
    return p * s;
}
/* tan(x) for x in [0, 1.45]: Pade, good to 1.5 % at the top */
static inline float sc_tan(float x) {
    float x2 = x * x;
    return x * (15.f - x2) / (15.f - 6.f * x2);
}
/* a soft clip that stays near 1:1 below 0.5 and never passes 1 */
static inline float sc_soft(float x) {
    x = sc_clamp(x, -3.f, 3.f);
    return x * (27.f + x * x) / (27.f + 9.f * x * x);
}

/* the zero-delay-feedback state variable filter (Simper) */
struct ScSvf { float ic1, ic2; };
struct ScSvfC { float k, a1, a2, a3; };
static inline void sc_svf_set(ScSvfC &c, float fc, float q) {
    fc = sc_clamp(fc, 10.f, 0.45f * SC_SR);
    float g = sc_tan(3.14159265f * fc / SC_SR);
    c.k = 1.f / q;
    c.a1 = 1.f / (1.f + g * (g + c.k));
    c.a2 = g * c.a1;
    c.a3 = g * c.a2;
}
/* returns the low pass; band and high through the pointers */
static inline float sc_svf(ScSvf &s, const ScSvfC &c, float v0, float *band, float *high) {
    float v3 = v0 - s.ic2;
    float v1 = c.a1 * s.ic1 + c.a2 * v3;
    float v2 = s.ic2 + c.a2 * s.ic1 + c.a3 * v3;
    s.ic1 = 2.f * v1 - s.ic1;
    s.ic2 = 2.f * v2 - s.ic2;
    if (band) *band = v1;
    if (high) *high = v0 - c.k * v1 - v2;
    return v2;
}

/* --------------------------------------------------------------------------------------------------- state */
int16_t *echo_l, *echo_r;                /* the echo lines (SDRAM) */
int16_t *roll_l, *roll_r;                /* the last 2.7 s of input (SDRAM) */
float *rv;                               /* the reverb's combs and allpasses (SDRAM) */
uint32_t echo_w, roll_w;
bool roll_rec;

uint32_t rng;
uint32_t blocks;                         /* blocks since start */

/* the knobs */
float pot[10], pot_raw[10], pot_last_move[10];
uint32_t pot_moved_at[10];
int last_pot;                            /* the knob moved last (for the screen), -1 none */
int btn_state[4], btn_cnt[4];
bool btn_down[4], btn_press[4], btn_release[4];

/* MIDI */
float cc_scene, cc_moto;
bool cc_scene_on, cc_moto_on;
float pot_at_cc_scene, pot_at_cc_moto;
bool cc_roll, cc_freeze_toggle, cc_release;

/* the clock */
int32_t ticks;                           /* MIDI clock ticks since START (-1 before the first) */
uint32_t tick_at;                        /* block of the last tick */
float tick_len;                          /* samples per tick, averaged */
uint32_t tick_seen;
bool clk_run;
int32_t ibeat;                           /* the internal clock: beats and fraction */
float ifrac;
float tap_len;                           /* samples per beat from the taps (0: none) */
uint32_t tap_last;
int tap_n;
float beat_len;                          /* samples per beat now */
int32_t beat;                            /* the beat now (since START or boot) */
float frac;                              /* 0..1 inside the beat */
int32_t last16;                          /* the sixteenth now (beat * 4 + n) */
bool on16, onbeat;                       /* a sixteenth / a beat started in this block */
int src;                                 /* 0 internal, 1 tap, 2 MIDI */

/* the scene */
float scene_t, scene;                    /* -1 .. 1 */
float dead;
bool released;
float moto_off_t[3], moto_off[3];       /* MOTO's breathing: filter octaves, echo send, noise */
int fill;                                /* 0 none, 1 roll, 2 echo throw, 3 filter dip */
int32_t fill_end16;
float throw_amt;
float dip_amt, dip_t;

/* the effects */
ScSvf f_l, f_r, fb_l, fb_r, n_l, n_r;
ScSvfC f_c, fb_c, n_c;
float filt_mix, filt_mix_t;
bool filt_hp;                            /* build: the filter is a high pass */
float crush_amt, crush_rate, crush_q, crush_ph, crush_hl, crush_hr;
float noise_lvl;
float echo_time, echo_time_t;           /* samples */
float send, send_t, fbk, fbk_t, ret;
float rv_send, rv_send_t;
float rv_fl[8];                          /* the combs' damping states */
int rv_idx[12];
int rv_len[12];
int rv_base[12];

/* the routing: 0 insert, 1 aux (no dry out) */
int routing;
ScSvf f2_l, f2_r;                        /* aux: the loop's own filter (the dry has f_l, f_r, for the sends) */
float crush2_hl, crush2_hr;              /* aux: the loop's own crush hold */

/* the loop player (ROLL, FREEZE, the fills) */
int lp;                                  /* 0 off, 1 waiting for its start, 2 playing, 3 waiting for its end */
int lp_kind;                             /* 1 roll, 2 freeze, 3 fill */
uint32_t lp_start;
float lp_len, lp_full, lp_pos, lp_rate, lp_gain, lp_gain_t;
float lp_open;                           /* aux: 0 in the loop's first pass (the dry), 1 from its first repeat */
int lp_passes;
int32_t lp_end16;
int roll_div;                            /* sixteenths of a beat: 2 = 1/8, 1 = 1/16; 0 = 1/32 */
int32_t roll_since;
bool freeze_on;

/* the screen */
char line[4][12];
uint32_t disp_at;

/* ------------------------------------------------------------------------------------------------- helpers */
inline uint32_t sc_rand() {
    rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5;
    return rng;
}
inline float sc_frand() { return (float)(sc_rand() >> 8) * (1.f / 16777216.f); }       /* 0..1 */
inline float sc_noise() { return (float)(int32_t)sc_rand() * (1.f / 2147483648.f); }   /* -1..1 */

inline float roll_get(const int16_t *b, float pos) {      /* linear interpolation on the roll buffer */
    int i = (int)pos;
    if ((float)i > pos) i--;
    float f = pos - (float)i;
    float a = b[(uint32_t)i & (SC_ROLL_N - 1)], c = b[(uint32_t)(i + 1) & (SC_ROLL_N - 1)];
    return (a + f * (c - a)) * (1.f / 32768.f);
}

inline float echo_get(const int16_t *b, float back) {     /* `back` samples behind the write head */
    float pos = (float)echo_w - back;
    int i = (int)pos;
    if ((float)i > pos) i--;
    float f = pos - (float)i;
    float a = b[(uint32_t)i & (SC_ECHO_N - 1)], c = b[(uint32_t)(i + 1) & (SC_ECHO_N - 1)];
    return (a + f * (c - a)) * (1.f / 32768.f);
}

static inline int16_t sc_s16(float x) {
    x = sc_clamp(x * 32767.f, -32767.f, 32767.f);
    return (int16_t)x;
}

/* the echo divisions on knob 3, in beats */
static float sc_div(int i) {
    switch (i) {
        case 0: return 0.25f;   /* 1/16 */
        case 1: return 0.5f;    /* 1/8 */
        case 2: return 0.75f;   /* 1/8. */
        case 3: return 1.f;     /* 1/4 */
        case 4: return 1.5f;    /* 1/4. */
        case 5: return 2.f;     /* 1/2 */
        default: return 4.f;    /* 1 bar */
    }
}
static const char *sc_div_name(int i) {
    switch (i) {
        case 0: return "1/16"; case 1: return "1/8"; case 2: return "1/8."; case 3: return "1/4";
        case 4: return "1/4."; case 5: return "1/2"; default: return "1 BAR";
    }
}
inline int echo_div_idx() { int i = (int)(pot[2] * 7.f); return i > 6 ? 6 : i; }

/* ------------------------------------------------------------------------------------------------ the setup */
void sc_init(int16_t *el, int16_t *er, int16_t *rl, int16_t *rr, float *rvb) {
    echo_l = el; echo_r = er; roll_l = rl; roll_r = rr; rv = rvb;
    for (int i = 0; i < SC_ECHO_N; i++) { echo_l[i] = 0; echo_r[i] = 0; }
    for (int i = 0; i < SC_ROLL_N; i++) { roll_l[i] = 0; roll_r[i] = 0; }
    for (int i = 0; i < SC_RV_TOTAL; i++) rv[i] = 0.f;
    static const int lens[6] = {1214, 1293, 1389, 1475, 605, 480};
    int base = 0;
    for (int ch = 0; ch < 2; ch++) {
        for (int k = 0; k < 6; k++) {
            int n = lens[k] + (ch ? 23 : 0);
            rv_len[ch * 6 + k] = n;
            rv_base[ch * 6 + k] = base;
            rv_idx[ch * 6 + k] = 0;
            base += n;
        }
    }
    for (int i = 0; i < 8; i++) rv_fl[i] = 0.f;
    echo_w = roll_w = 0;
    roll_rec = true;
    rng = 0x9E3779B9u;
    blocks = 0;
    for (int i = 0; i < 10; i++) { pot[i] = pot_raw[i] = pot_last_move[i] = -1.f; pot_moved_at[i] = 0; }
    last_pot = -1;
    for (int i = 0; i < 4; i++) { btn_state[i] = 0; btn_cnt[i] = 0; btn_down[i] = btn_press[i] = btn_release[i] = false; }
    cc_scene = cc_moto = 0.f; cc_scene_on = cc_moto_on = false; cc_roll = cc_freeze_toggle = cc_release = false;
    ticks = -1; tick_at = 0; tick_len = SC_SR * 60.f / 120.f / 24.f; tick_seen = 0; clk_run = false;
    ibeat = 0; ifrac = 0.f; tap_len = 0.f; tap_last = 0; tap_n = 0;
    beat_len = SC_SR * 0.5f; beat = 0; frac = 0.f; last16 = -1; on16 = onbeat = false; src = 0;
    scene_t = scene = 0.f; dead = 0.06f; released = false;
    for (int i = 0; i < 3; i++) moto_off_t[i] = moto_off[i] = 0.f;
    fill = 0; fill_end16 = 0; throw_amt = 0.f; dip_amt = dip_t = 0.f;
    ScSvf z = {0.f, 0.f};
    f_l = f_r = fb_l = fb_r = n_l = n_r = z;
    routing = 0;
    f2_l = f2_r = z;
    crush2_hl = crush2_hr = 0.f;
    lp_open = 0.f;
    sc_svf_set(f_c, 20000.f, 0.707f); sc_svf_set(fb_c, 8000.f, 0.707f); sc_svf_set(n_c, 1000.f, 0.707f);
    filt_mix = filt_mix_t = 0.f; filt_hp = false;
    crush_amt = 0.f; crush_rate = 1.f; crush_q = 0.f; crush_ph = 0.f; crush_hl = crush_hr = 0.f;
    noise_lvl = 0.f;
    echo_time = echo_time_t = beat_len * 0.5f;
    send = send_t = fbk = fbk_t = 0.f; ret = 1.f; rv_send = rv_send_t = 0.f;
    lp = 0; lp_kind = 0; lp_start = 0; lp_len = lp_full = 1.f; lp_pos = 0.f; lp_rate = 1.f; lp_gain = lp_gain_t = 0.f;
    lp_passes = 0; lp_end16 = 0; roll_div = 2; roll_since = 0; freeze_on = false;
    for (int i = 0; i < 4; i++) line[i][0] = 0;
    disp_at = 0;
    rv_tail = 0;
    pwm = 0;
}

/* ------------------------------------------------------------------------------------------------------ MIDI */
void sc_midi(uint8_t status, uint8_t d1, uint8_t d2) {
    if (status == 0xF8) {                                    /* clock */
        uint32_t now = blocks;
        if (tick_seen && now > tick_at) {
            float dt = (float)(now - tick_at) * SC_BS;
            if (dt > 20.f && dt < 6000.f) {                  /* 20 .. 600 bpm */
                if (blocks - tick_seen > 3000) tick_len = dt;        /* the first after a silence: take it */
                else tick_len += (dt - tick_len) * 0.08f;
            }
        }
        tick_at = now;
        tick_seen = now ? now : 1;
        if (clk_run) ticks++;
    } else if (status == 0xFA) {                             /* start */
        clk_run = true; ticks = -1;
    } else if (status == 0xFB) {                             /* continue */
        clk_run = true;
    } else if (status == 0xFC) {                             /* stop */
        clk_run = false;
    } else if (status == 0xF2) {                             /* song position */
        ticks = 6 * (((int32_t)d2 << 7) | d1) - 1;
    } else if ((status & 0xF0) == 0xB0) {                    /* CC 20-24, any channel */
        float v = d2 * (1.f / 127.f);
        if (d1 == 20) { cc_scene = v * 2.f - 1.f; cc_scene_on = true; pot_at_cc_scene = pot[0]; }
        else if (d1 == 21) { cc_moto = v; cc_moto_on = true; pot_at_cc_moto = pot[1]; }
        else if (d1 == 22) { cc_roll = d2 >= 64; }
        else if (d1 == 23) { if (d2 >= 64) cc_freeze_toggle = true; }
        else if (d1 == 24) { if (d2 >= 64) cc_release = true; }
    }
}

/* ------------------------------------------------------------------------------------------- knobs, buttons */
void read_hw() {
    for (int i = 0; i < 10; i++) {
        float v = hw_adc(i) * (1.f / 4095.f);
        if (pot_raw[i] < 0.f) { pot_raw[i] = pot[i] = pot_last_move[i] = v; continue; }
        if (sc_abs(v - pot_raw[i]) > 0.004f) pot_raw[i] = v;          /* the ADC's noise stays out */
        pot[i] += (pot_raw[i] - pot[i]) * 0.02f;
        if (sc_abs(pot[i] - pot_last_move[i]) > 0.02f) {             /* a real move: the screen shows it */
            pot_last_move[i] = pot[i];
            pot_moved_at[i] = blocks;
            if (blocks > 3000) last_pot = i;
        }
    }
    if (cc_scene_on && pot_at_cc_scene < 0.f) pot_at_cc_scene = pot[0];   /* (a CC before the first read) */
    if (cc_moto_on && pot_at_cc_moto < 0.f) pot_at_cc_moto = pot[1];
    if (cc_scene_on && sc_abs(pot[0] - pot_at_cc_scene) > 0.03f) cc_scene_on = false;   /* the knob takes it back */
    if (cc_moto_on && sc_abs(pot[1] - pot_at_cc_moto) > 0.03f) cc_moto_on = false;
    for (int i = 0; i < 4; i++) {
        int b = hw_btn(i) ? 1 : 0;
        btn_press[i] = btn_release[i] = false;
        if (b != btn_state[i]) {
            if (++btn_cnt[i] >= 30) {                                   /* 10 ms steady */
                btn_state[i] = b; btn_cnt[i] = 0;
                if (b) btn_press[i] = true; else btn_release[i] = true;
            }
        } else btn_cnt[i] = 0;
        btn_down[i] = btn_state[i] != 0;
    }
}

/* ------------------------------------------------------------------------------------------------ the clock */
void clock_block() {
    bool midi = tick_seen && (blocks - tick_seen) < 1500;             /* a tick in the last half second */
    int32_t prev16 = last16;
    if (midi) {
        src = 2;
        beat_len = tick_len * 24.f;
        if (clk_run && ticks >= 0) {
            float sub = (float)(blocks - tick_at) * SC_BS / tick_len;
            if (sub > 0.99f) sub = 0.99f;
            beat = ticks / 24;
            frac = ((float)(ticks % 24) + sub) * (1.f / 24.f);
        } else {                                                         /* stopped: run free at its tempo */
            ifrac += SC_BS / beat_len;
            while (ifrac >= 1.f) { ifrac -= 1.f; ibeat++; }
            beat = ibeat; frac = ifrac;
        }
    } else {
        src = tap_len > 0.f ? 1 : 0;
        beat_len = tap_len > 0.f ? tap_len : SC_SR * 0.5f;
        ifrac += SC_BS / beat_len;
        while (ifrac >= 1.f) { ifrac -= 1.f; ibeat++; }
        beat = ibeat; frac = ifrac;
    }
    if (midi && clk_run && ticks >= 0) { ibeat = beat; ifrac = frac; }   /* free running goes on from here */
    last16 = beat * 4 + (int32_t)(frac * 4.f);
    if (prev16 >= 0 && last16 < prev16) {                                /* START or a jump back: the counters follow */
        fill_end16 += last16 - prev16;
        roll_since += last16 - prev16;
        lp_end16 += last16 - prev16;
    }
    on16 = (last16 != prev16);
    onbeat = on16 && (last16 % 4 == 0);
}

void tap() {
    uint32_t now = blocks;
    float dt = (float)(now - tap_last) * SC_BS;
    if (tap_last && dt > SC_SR * 0.2f && dt < SC_SR * 2.f) {
        tap_len = tap_n ? tap_len + (dt - tap_len) * 0.5f : dt;
        tap_n++;
        ibeat++; ifrac = 0.f;                                            /* the tap is the beat */
    } else {
        tap_n = 0;
    }
    tap_last = now;
}

/* ----------------------------------------------------------------------------------------- the loop player */
void loop_start(int kind, float len, bool past) {
    lp_kind = kind;
    lp_len = lp_full = sc_clamp(len, 64.f, (float)(SC_ROLL_N / 2));
    lp_start = past ? (roll_w - (uint32_t)lp_len) : roll_w;           /* past: the beat just gone; else from now */
    lp_pos = 0.f; lp_rate = 1.f; lp_passes = past ? 1 : 0;
    lp_gain_t = 1.f;
    lp_open = 0.f;
    lp = 2;
}
void loop_stop() { lp_gain_t = 0.f; lp = 3; }

/* ------------------------------------------------------------------------------------------ the controls */
void control_block() {
    /* the scene: the knob (or CC 20), a dead zone in the middle; RELEASE holds it clean until the knob comes back */
    float raw = cc_scene_on ? cc_scene : (pot[0] * 2.f - 1.f);
    if (released) {
        if (sc_abs(raw) < dead) released = false;
        raw = 0.f;
    }
    float u = 0.f;
    if (raw > dead) u = (raw - dead) / (1.f - dead);
    else if (raw < -dead) u = (raw + dead) / (1.f - dead);
    scene_t = u;
    scene += (scene_t - scene) * (released ? 0.05f : 0.01f);
    if (sc_abs(scene - scene_t) < 0.0005f) scene = scene_t;             /* it arrives: clean is exactly clean */
    float b = scene > 0.f ? scene : 0.f;                                /* build */
    float k = scene < 0.f ? -scene : 0.f;                               /* break */
    float a = b + k;
    float moto = cc_moto_on ? cc_moto : pot[1];

    /* MOTO: a new breath every beat, and the fills at the end of bars and phrases */
    if (onbeat) {
        float m = moto * a;
        moto_off_t[0] = (sc_frand() * 2.f - 1.f) * m * 1.2f;           /* filter, octaves */
        moto_off_t[1] = (sc_frand() * 2.f - 1.f) * m * 0.35f;          /* echo send */
        moto_off_t[2] = (sc_frand() * 2.f - 1.f) * m * 0.5f;           /* noise */
        int pb = ((beat % 16) + 16) % 16;
        float p = 0.f;
        if (pb == 15) p = 0.8f; else if (pb % 4 == 3) p = 0.25f;
        p *= moto * (0.4f + 0.6f * a);
        if (!fill && lp == 0 && a > 0.001f && sc_frand() < p) {
            if (b > 0.f && sc_frand() < 0.7f) {
                fill = 1;                                                /* a roll of the last beat's 16ths */
                roll_div = b > 0.6f ? 0 : 1;
                float len = beat_len * (roll_div == 0 ? 0.125f : 0.25f);
                loop_start(3, len, false);
                fill_end16 = last16 + 4;
            } else if (k > 0.f && sc_frand() < 0.6f) {
                fill = 2; throw_amt = 1.f;                               /* an echo thrown */
                fill_end16 = last16 + 2;
            } else {
                fill = 3; dip_t = 1.f;                                   /* the filter dives and comes back */
                fill_end16 = last16 + 4;
            }
        }
    }
    float mo = 3.f / (beat_len / SC_BS);                                 /* about a beat to get there */
    for (int i = 0; i < 3; i++) moto_off[i] += (moto_off_t[i] - moto_off[i]) * mo;
    if (fill && on16 && last16 >= fill_end16) {
        if (fill == 1 && lp_kind == 3 && lp == 2) loop_stop();
        fill = 0; throw_amt = 0.f; dip_t = 0.f;
    }
    dip_amt += (dip_t - dip_amt) * 0.01f;

    /* ROLL (button 1 or CC 22): from the next 16th, the slice repeats; on the build side it shortens every beat */
    bool roll_held = btn_down[0] || cc_roll;
    if (roll_held && (lp == 0 || (lp_kind == 3)) && !freeze_on) {
        if (lp_kind != 1 || lp == 3) {
            if (on16) {
                roll_div = (moto > 0.5f) ? 1 : 2;
                loop_start(1, beat_len * (roll_div == 2 ? 0.5f : 0.25f), false);
                roll_since = last16;
                fill = 0;
            }
        }
    }
    if (lp_kind == 1 && lp == 2) {
        if (onbeat && b > 0.3f && last16 > roll_since && roll_div > 0) {
            roll_div--;
            lp_len = beat_len * (roll_div == 1 ? 0.25f : 0.125f);
        }
        if (!roll_held && on16) loop_stop();
    }

    /* FREEZE (button 2 or CC 23): on the next beat the beat just gone loops; with MOTO it varies by itself */
    if (btn_press[1] || cc_freeze_toggle) {
        cc_freeze_toggle = false;
        freeze_on = !freeze_on;
    }
    if (freeze_on && onbeat && lp_kind != 2) {
        loop_start(2, beat_len, true);
        fill = 0;
    } else if (freeze_on && lp_kind == 2 && lp == 2 && onbeat) {
        float r = sc_frand();
        if (r < moto * 0.6f) {
            float r2 = sc_frand();
            if (r2 < 0.4f) { lp_len = lp_full * 0.5f; lp_rate = 1.f; }
            else if (r2 < 0.65f) { lp_len = lp_full * 0.25f; lp_rate = 1.f; }
            else { lp_len = lp_full; lp_rate = -1.f; }
        } else { lp_len = lp_full; lp_rate = 1.f; }
        if (lp_pos >= lp_len) lp_pos = 0.f;
    } else if (!freeze_on && lp_kind == 2 && lp == 2 && onbeat) {
        loop_stop();
    }

    /* RELEASE (button 3 or CC 24): clean now, the echo rings out */
    if (btn_press[2] || cc_release) {
        cc_release = false;
        released = true;
        fill = 0; throw_amt = 0.f; dip_t = 0.f;
        if (lp == 2 && lp_kind != 2) loop_stop();
    }
    /* TAP (button 4) */
    if (btn_press[3]) tap();

    /* the filter: build = a high pass going up, break = a low pass coming down; FILTRO says how far, MOTO breathes */
    float depth = pot[4];
    float q = 0.6f + pot[5] * pot[5] * 7.f * a;                          /* the resonance grows with the scene */
    float dip = dip_amt * depth;
    if (b > 0.f) {
        filt_hp = true;
        float oct = (b + dip) * depth * 7.f + moto_off[0] * b;          /* 20 Hz .. 2.5 kHz */
        sc_svf_set(f_c, 20.f * sc_exp2(sc_clamp(oct, 0.f, 9.f)), q);
    } else {
        filt_hp = false;
        float oct = (k + dip) * depth * 6.5f - moto_off[0] * k;         /* 20 kHz .. 220 Hz */
        sc_svf_set(f_c, 20000.f * sc_exp2(-sc_clamp(oct, 0.f, 9.f)), q);
    }
    filt_mix_t = (a > 0.001f || dip_amt > 0.01f) ? 1.f : 0.f;

    /* the crush (break): fewer bits, fewer samples */
    float cr = pot[7] * k;
    crush_amt = cr;
    crush_rate = 1.f - cr * 0.92f;
    crush_q = sc_exp2(15.f - cr * 11.f);                                 /* 32768 .. 16 steps */

    /* the noise (build): a hiss that rises */
    noise_lvl = pot[6] * b * b * 0.35f * (1.f + moto_off[2]);
    if (noise_lvl < 0.f) noise_lvl = 0.f;
    sc_svf_set(n_c, 300.f * sc_exp2(b * 5.f), 1.2f);

    /* the echo: time from knob 3 in beats; feedback up to knob 4; build: thinner repeats, break: darker */
    float div = sc_div(echo_div_idx());
    echo_time_t = sc_clamp(div * beat_len, 32.f, (float)(SC_ECHO_N - 64));
    float fbmax = pot[3] * 0.95f;
    if (released) { send_t = 0.f; if (fbk_t > 0.85f) fbk_t = 0.85f; }
    else if (a <= 0.001f) { send_t = 0.f; fbk_t = fbk_t > 0.3f ? fbk_t - 0.0002f : fbk_t; }   /* back to clean: the tail fades */
    else if (b > 0.f) { send_t = b * 0.8f; fbk_t = fbmax * (0.25f + 0.75f * b); }
    else { send_t = k * 0.9f; fbk_t = fbmax * (0.3f + 0.7f * k); }
    if (a > 0.001f) send_t += moto_off[1];
    if (throw_amt > 0.f) { send_t = 1.f; fbk_t = fbmax > 0.5f ? fbmax : 0.5f; }
    send_t = sc_clamp(send_t, 0.f, 1.f);
    if (b > 0.f) sc_svf_set(fb_c, 100.f * sc_exp2(b * 5.f), 0.8f);
    else sc_svf_set(fb_c, 6000.f * sc_exp2(-k * 4.f), 0.8f);
    ret = pot[9];

    /* the reverb (break): the wash under the break-down */
    rv_send_t = released ? 0.f : pot[8] * k;
}

/* ---------------------------------------------------------------------------------------------- the reverb */
inline float rv_comb(int i, float x, float fb, float damp) {
    float *b = rv + rv_base[i];
    int &ix = rv_idx[i];
    float y = b[ix];
    float &st = rv_fl[(i / 6) * 4 + (i % 6)];
    st = y * (1.f - damp) + st * damp;
    b[ix] = x + st * fb;
    if (++ix >= rv_len[i]) ix = 0;
    return y;
}
inline float rv_ap(int i, float x) {
    float *b = rv + rv_base[i];
    int &ix = rv_idx[i];
    float y = b[ix];
    b[ix] = x + y * 0.5f;
    if (++ix >= rv_len[i]) ix = 0;
    return y - x;
}

/* ------------------------------------------------------------------------------------------- the audio block */
void sc_block(const int32_t *inl, const int32_t *inr, int32_t *outl, int32_t *outr) {
    blocks++;
    read_hw();
    clock_block();
    control_block();
    const float IN = 1.f / 134217728.f, OUT = 134217728.f;
    for (int j = 0; j < SC_BS; j++) {
        float xl = inl[j] * IN, xr = inr[j] * IN;
        float wl = 0.f, wr = 0.f;                                    /* aux: the loop alone, what comes out */
        /* the roll buffer: the input, always (paused while a loop holds its slice) */
        if (roll_rec) {
            roll_w = (roll_w + 1) & (SC_ROLL_N - 1);
            roll_l[roll_w] = sc_s16(xl);
            roll_r[roll_w] = sc_s16(xr);
        }
        /* the loop player */
        if (lp) {
            float p = (float)lp_start + lp_pos;
            float yl = roll_get(roll_l, p), yr = roll_get(roll_r, p);
            if (lp_passes > 0) {                                     /* crossfade into the audio before the start */
                if (lp_rate > 0.f && lp_pos > lp_len - SC_FADE) {
                    float w = (lp_pos - (lp_len - SC_FADE)) * (1.f / SC_FADE);
                    float q = p - lp_len;
                    yl += w * (roll_get(roll_l, q) - yl); yr += w * (roll_get(roll_r, q) - yr);
                } else if (lp_rate < 0.f && lp_pos < SC_FADE) {
                    float w = 1.f - lp_pos * (1.f / SC_FADE);
                    float q = p + lp_len;
                    yl += w * (roll_get(roll_l, q) - yl); yr += w * (roll_get(roll_r, q) - yr);
                }
            }
            lp_gain += (lp_gain_t - lp_gain) * 0.02f;
            xl += lp_gain * (yl - xl); xr += lp_gain * (yr - xr);   /* (aux: what goes to the echo and the reverb) */
            if (routing) {                                           /* aux: out from its first repeat (1 ms in) */
                lp_open += ((lp_passes > 0 ? 1.f : 0.f) - lp_open) * 0.02f;
                float g = lp_gain * lp_open;
                wl = g * yl; wr = g * yr;
            }
            lp_pos += lp_rate;
            if (lp_pos >= lp_len) { while (lp_pos >= lp_len) lp_pos -= lp_len; lp_passes++; }
            else if (lp_pos < 0.f) { while (lp_pos < 0.f) lp_pos += lp_len; lp_passes++; }
            if (lp_passes > 0) roll_rec = false;
            if (lp == 3 && lp_gain < 0.001f) { lp = 0; lp_kind = 0; roll_rec = true; }
        }
        /* the filter */
        filt_mix += (filt_mix_t - filt_mix) * 0.002f;
        float bl, hl, br, hr;
        float ll = sc_svf(f_l, f_c, xl, &bl, &hl), lr = sc_svf(f_r, f_c, xr, &br, &hr);
        if (filt_mix > 0.0001f) {
            float yl = filt_hp ? hl : ll, yr = filt_hp ? hr : lr;
            xl += filt_mix * (yl - xl); xr += filt_mix * (yr - xr);
        }
        if (routing) {                                               /* aux: the loop through the same filter */
            float b2l, h2l, b2r, h2r;
            float l2l = sc_svf(f2_l, f_c, wl, &b2l, &h2l), l2r = sc_svf(f2_r, f_c, wr, &b2r, &h2r);
            if (filt_mix > 0.0001f) {
                float yl = filt_hp ? h2l : l2l, yr = filt_hp ? h2r : l2r;
                wl += filt_mix * (yl - wl); wr += filt_mix * (yr - wr);
            }
        }
        /* the crush */
        if (crush_amt > 0.001f) {
            crush_ph += crush_rate;
            if (crush_ph >= 1.f) {
                crush_ph -= 1.f;
                crush_hl = (float)(int32_t)(xl * crush_q) / crush_q;
                crush_hr = (float)(int32_t)(xr * crush_q) / crush_q;
                if (routing) {
                    crush2_hl = (float)(int32_t)(wl * crush_q) / crush_q;
                    crush2_hr = (float)(int32_t)(wr * crush_q) / crush_q;
                }
            }
            xl += crush_amt * (crush_hl - xl); xr += crush_amt * (crush_hr - xr);
            if (routing) { wl += crush_amt * (crush2_hl - wl); wr += crush_amt * (crush2_hr - wr); }
        }
        /* the noise */
        float nl = 0.f, nr = 0.f;
        if (noise_lvl > 0.0001f) {
            float h1, h2;
            sc_svf(n_l, n_c, sc_noise(), 0, &h1);
            sc_svf(n_r, n_c, sc_noise(), 0, &h2);
            nl = noise_lvl * h1; nr = noise_lvl * h2;
            xl += nl; xr += nr;
        }
        /* what goes into the echo and the reverb: what an insert would give (the loop in place of the dry) */
        float sl = xl, sr = xr;
        /* the echo: ping-pong a little, filtered in the loop, soft-clipped so it never runs away */
        send += (send_t - send) * 0.001f;
        fbk += (fbk_t - fbk) * 0.0005f;
        echo_time += (echo_time_t - echo_time) * 0.0002f;
        float dl = echo_get(echo_l, echo_time), dr = echo_get(echo_r, echo_time);
        float el, er;
        if (b_side()) { sc_svf(fb_l, fb_c, dl, 0, &el); sc_svf(fb_r, fb_c, dr, 0, &er); }
        else { el = sc_svf(fb_l, fb_c, dl, 0, 0); er = sc_svf(fb_r, fb_c, dr, 0, 0); }
        echo_w = (echo_w + 1) & (SC_ECHO_N - 1);
        echo_l[echo_w] = sc_s16(sc_soft(send * sl + fbk * (0.7f * el + 0.3f * er)));
        echo_r[echo_w] = sc_s16(sc_soft(send * sr + fbk * (0.7f * er + 0.3f * el)));
        /* the reverb */
        rv_send += (rv_send_t - rv_send) * 0.0005f;
        float rvl = 0.f, rvr = 0.f;
        if (rv_send > 0.0005f || rv_tail > 0) {
            float rin = (sl + sr) * 0.5f * rv_send * 0.3f;
            for (int c = 0; c < 4; c++) { rvl += rv_comb(c, rin, 0.84f, 0.3f); rvr += rv_comb(6 + c, rin, 0.84f, 0.3f); }
            rvl = rv_ap(5, rv_ap(4, rvl)); rvr = rv_ap(11, rv_ap(10, rvr));
            rv_tail = rv_send > 0.0005f ? 3 * SC_SR : rv_tail - 1;
        }
        float ol = (routing ? wl + nl : xl) + ret * (dl + rvl * 0.5f);   /* aux: no dry */
        float orr = (routing ? wr + nr : xr) + ret * (dr + rvr * 0.5f);
        outl[j] = (int32_t)(sc_clamp(ol, -1.f, 0.9999999f) * OUT);
        outr[j] = (int32_t)(sc_clamp(orr, -1.f, 0.9999999f) * OUT);
    }
    leds();
    if (blocks - disp_at >= 150) { disp_at = blocks; screen(); }          /* 20 times a second */
}
int32_t rv_tail;
inline bool b_side() { return scene > 0.f; }

/* ------------------------------------------------------------------------------------------------ the LEDs */
uint32_t pwm;
void leds() {
    pwm = (pwm + 1) & 15;
    float b = scene > 0.f ? scene : 0.f, k = scene < 0.f ? -scene : 0.f;
    hw_led(0, (float)pwm < b * 16.f);                                   /* LED 3 blue: build */
    hw_led(1, (float)pwm < k * 16.f);                                   /* LED 3 red: break */
    hw_led(2, frac < 0.12f);                                             /* LED 4 blue: the beat */
    hw_led(3, lp == 2 || freeze_on || (released && (blocks & 512)));    /* LED 4 red: a loop, or RELEASE */
}

/* ---------------------------------------------------------------------------------------------- the screen */
static void sc_puts(char *d, const char *s, int at) {      /* writes s at column `at`, line is 11 wide */
    while (*s && at < 11) d[at++] = *s++;
}
static void sc_num(char *d, int v, int right) {             /* an integer, right-aligned ending at column `right` */
    char tmp[8];
    int n = 0;
    bool neg = v < 0;
    if (neg) v = -v;
    do { tmp[n++] = (char)('0' + v % 10); v /= 10; } while (v && n < 6);
    if (neg) tmp[n++] = '-';
    for (int i = 0; i < n && right - i >= 0; i++) d[right - i] = tmp[i];
}
static void sc_clear(char *d) { for (int i = 0; i < 11; i++) d[i] = ' '; d[11] = 0; }

void screen() {
    for (int i = 0; i < 4; i++) sc_clear(line[i]);
    int s = (int)(scene * 100.f + (scene >= 0.f ? 0.5f : -0.5f));
    if (released) sc_puts(line[0], "RELEASE", 0);
    else if (s == 0) sc_puts(line[0], routing ? "MANDATA" : "PULITO", 0);
    else { sc_puts(line[0], s > 0 ? "BUILD" : "BREAK", 0); sc_num(line[0], s > 0 ? s : -s, 10); }
    int bpm10 = (int)(SC_SR * 600.f / beat_len + 0.5f);
    sc_num(line[1], bpm10 / 10, 2);
    line[1][3] = '.';
    line[1][4] = (char)('0' + bpm10 % 10);
    sc_puts(line[1], src == 2 ? "MIDI" : (src == 1 ? "TAP" : "INT"), 6);
    static const char *names[10] = {"SCENA", "MOTO", "ECO", "FEEDBACK", "FILTRO", "RISON", "RUMORE", "CRUSH",
                                    "RIVERB", "RITORNI"};
    if (last_pot >= 0 && blocks - pot_moved_at[last_pot] < 6000) {
        sc_puts(line[2], names[last_pot], 0);
        if (last_pot == 2) { const char *n = sc_div_name(echo_div_idx()); int l = 0; while (n[l]) l++; sc_puts(line[2], n, 11 - l); }
        else sc_num(line[2], (int)(pot[last_pot] * 100.f + 0.5f), 10);
    } else {
        int pb = ((beat % 16) + 16) % 16;
        sc_puts(line[2], "FRASE", 0);
        line[2][7] = (char)('1' + pb / 4);
        line[2][8] = '.';
        line[2][9] = (char)('1' + pb % 4);
    }
    if (lp == 2 && lp_kind == 2) sc_puts(line[3], "FREEZE", 0);
    else if (lp == 2 && lp_kind == 1) {
        sc_puts(line[3], "ROLL", 0);
        sc_puts(line[3], roll_div == 2 ? "1/8" : (roll_div == 1 ? "1/16" : "1/32"), 6);
    } else if (fill == 1) sc_puts(line[3], "FILL ROLL", 0);
    else if (fill == 2) sc_puts(line[3], "FILL ECO", 0);
    else if (fill == 3) sc_puts(line[3], "FILL DIP", 0);
    else if (freeze_on) sc_puts(line[3], "FREEZE..", 0);
}
