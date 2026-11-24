/* VARIAZIONI - FIGO and SCENA in one object for the Gills, beside an effect (Microcosm, Chroma) or alone (class-body
 * code, after scena_engine.h and figo_engine.h: it gives SCENA its knobs and buttons, and drives both).
 *
 * The page. Beside an effect the Gills' knobs and buttons belong to the effect (its panel) or to the variations: hold
 * the encoder down for a second without touching anything else and let go, and you are on the other page. On the
 * variations' page the knobs set them, with pick-up: a knob takes its value back when it passes where the value is
 * (the screen shows ~ and an o until then), so nothing jumps; the effect's knobs do the same when you go back. The
 * encoder held is SHIFT there too. MIDI CC 110-119 reach the variations from any page. The screen and the LEDs show
 * the page you are on. Alone (VR_ALONE) the page is always the variations'.
 *
 * Knobs: 1 SCENA, 2 FIGO, 3 CARATTERE, 4 MEMORIA, 5 MOTO, 6 ECO, 7 FEEDBACK, 8 FILTRO, 9 RIVERB, 10 RITORNI; with
 * SHIFT 6 RISON, 7 RUMORE, 8 CRUSH, 9 LIV.MEMORIA, 10 LIVELLO. Buttons: 1 ROLL (held), 2 FREEZE, 3 PULITO (FIGO out,
 * SCENA RELEASE; again: FIGO back), 4 HOLD; SHIFT+1 the phrase starts here, SHIFT+4 TAP, SHIFT+encoder the way back
 * (aux). CC 110 SCENA, 111 MOTO, 112 ROLL, 113 FREEZE, 114 RELEASE, 115 FIGO, 116 CARATTERE, 117 MEMORIA, 118 HOLD,
 * 119 PULITO; alone also SCENA's own 20-24.
 *
 * The sound. insert: the effect -> FIGO -> SCENA -> out (alone: in -> FIGO -> SCENA). aux, a mixer's send and return:
 * out = the effect + FIGO(in) + SCENA(in), each fed by the send; FIGO and SCENA give only what they add (no dry), and
 * nothing at all when nothing happens. With the variations doing nothing the effect comes out as it is, bit for bit.
 * SPDX-License-Identifier: GPL-3.0-only */

#ifndef VR_COLD
#define VR_COLD
#endif
#ifndef VR_HOT
#define VR_HOT
#endif
#ifndef VR_FN
#define VR_FN
#endif
#ifndef VR_RO
#define VR_RO
#endif
#ifndef VR_FX_NAME
#define VR_FX_NAME "EFFETTO"
#endif

enum { VR_NP = 10, VR_NV = 15, VR_LM = 0x7F80000 };

/* SCENA's knobs and buttons: what the page gives it */
int vr_sc_adc[10];
int vr_sc_btn[4];
VR_FN int hw_adc(int i) { return vr_sc_adc[i]; }
VR_FN int hw_btn(int i) { return vr_sc_btn[i]; }
VR_FN void hw_led(int i, bool on) { (void)i; (void)on; }

/* the page */
float vr_val[VR_NV];                     /* the values, 0..1 */
uint8_t vr_pick[VR_NV];                  /* waiting for its knob to pass the value */
float vr_pv[VR_NP], vr_plast[VR_NP], vr_pshow[VR_NP], vr_psh[VR_NP], vr_psnap[VR_NP];
bool vr_page, vr_shift, vr_touched, vr_hint;
uint8_t vr_bst[5], vr_braw[5], vr_bcnt[5];
int32_t vr_bheld[5];
int32_t vr_enc_last, vr_ticks;
int vr_pop, vr_pop_t;                    /* the popup: which value (-1 none, 20 the way back), how long */
char vr_ln[4][24];
int vr_dline, vr_dtick, vr_blink;
int vr_routing, vr_mono;
float vr_rt_ms;                          /* aux: the way to the mixer and back, ms (SHIFT+encoder) */
/* MIDI: the MIDI thread queues, the audio thread applies */
volatile uint32_t vr_qw, vr_qr;
volatile uint32_t vr_q[32];
char vr_hl[24];                          /* the hint line */
/* the audio between FIGO and SCENA */
int32_t vr_tl[SC_BS], vr_tr[SC_BS], vr_fl[SC_BS], vr_fr[SC_BS], vr_xl[SC_BS], vr_xr[SC_BS];

VR_FN static bool vr_has_sec(int i) { return i >= 5; }
VR_FN static int vr_target(int i, bool sh) { return (sh && i >= 5) ? 10 + (i - 5) : i; }

VR_COLD void vr_init(int routing, int mono, float rt_ms, int phrase, int out_kind) {
    VR_RO static const float D[VR_NV] = {0.5f, 0.f, 0.3f, 0.f, 0.f, 1.5f / 7.f, 0.4f, 0.6f, 0.4f, 0.7f,
                                   0.3f, 0.3f, 0.4f, 0.6f, 1.f / 1.5f};
    for (int i = 0; i < VR_NV; i++) { vr_val[i] = D[i]; vr_pick[i] = 1; }
    for (int i = 0; i < VR_NP; i++) vr_pv[i] = vr_plast[i] = vr_pshow[i] = vr_psh[i] = vr_psnap[i] = 0.f;
#ifdef VR_ALONE
    vr_page = true;
#else
    vr_page = false;
#endif
    vr_shift = vr_touched = vr_hint = false;
    for (int k = 0; k < 5; k++) { vr_bst[k] = vr_braw[k] = vr_bcnt[k] = 0; vr_bheld[k] = 0; }
    vr_enc_last = 0; vr_ticks = 0;
    vr_pop = -1; vr_pop_t = 0;
    for (int n = 0; n < 4; n++) { for (int i = 0; i < 21; i++) vr_ln[n][i] = ' '; vr_ln[n][21] = 0; }
    for (int i = 0; i < 21; i++) vr_hl[i] = ' ';
    vr_hl[21] = 0;
    vr_dline = 0; vr_dtick = 0; vr_blink = 0;
    vr_routing = routing; vr_mono = mono;
    vr_rt_ms = rt_ms;
    vr_qw = vr_qr = 0u;
    for (int i = 0; i < 10; i++) vr_sc_adc[i] = 0;
    for (int i = 0; i < 4; i++) vr_sc_btn[i] = 0;
    fg_phrase = phrase; fg_out_kind = out_kind;
    routing_set();
}
/* the routing into the engines; the way back in samples */
VR_COLD void routing_set() {
    routing = vr_routing;
    fg_aux = vr_routing;
    uint32_t rt = (uint32_t)(vr_rt_ms * 48.f + 0.5f);
    sc_rt = rt; fg_rt = rt;
}

/* ------------------------------------------------------------------------------------------------- MIDI */
/* from the MIDI thread: only into the queue */
VR_FN void vr_midi(uint8_t status, uint8_t d1, uint8_t d2) {
    uint8_t st = status & 0xF0;
    bool clk = status == 0xF8 || status == 0xFA || status == 0xFB || status == 0xFC || status == 0xF2;
    bool cc = st == 0xB0 && ((d1 >= 110 && d1 <= 119)
#ifdef VR_ALONE
                             || (d1 >= 20 && d1 <= 24)
#endif
                             );
    if (!clk && !cc) return;
    uint32_t w = vr_qw;
    if (w - vr_qr >= 32u) return;
    vr_q[w & 31u] = (uint32_t)status | ((uint32_t)d1 << 8) | ((uint32_t)d2 << 16);
    vr_qw = w + 1u;
}
/* PULITO: FIGO out on the next beat and SCENA clean now; pressed again, FIGO back */
VR_COLD void vr_pulito() {
    if (fg_on) cc_release = true;
    fg_pulito_toggle();
}
VR_COLD void vr_midi_apply() {
    while (vr_qr != vr_qw) {
        uint32_t e = vr_q[vr_qr & 31u];
        vr_qr = vr_qr + 1u;
        uint8_t status = (uint8_t)(e & 255u), d1 = (uint8_t)((e >> 8) & 255u), d2 = (uint8_t)((e >> 16) & 255u);
        if (status >= 0xF0) { sc_midi(status, d1, d2); continue; }
        if (d1 <= 24) { sc_midi(0xB0, d1, d2); continue; }           /* (alone: SCENA's own CCs) */
        if (d1 <= 114) { sc_midi(0xB0, (uint8_t)(d1 - 90), d2); continue; }   /* 110-114: SCENA, as 20-24 */
        float v = (float)d2 * (1.f / 127.f);
        switch (d1) {
            case 115: vr_val[1] = v; vr_pick[1] = 1; break;          /* (the knob takes it back when it passes) */
            case 116: vr_val[2] = v; vr_pick[2] = 1; break;
            case 117: vr_val[3] = v; vr_pick[3] = 1; break;
            case 118: if (d2 >= 64) fg_hold_toggle(); break;
            case 119: if (d2 >= 64) vr_pulito(); break;
            default: break;
        }
    }
}

/* ------------------------------------------------------------------------------------- knobs and buttons */
VR_COLD int vr_btn(int k, bool raw) {                       /* debounced: 1 pressed, -1 let go */
    uint8_t r = raw ? 1 : 0;
    if (r != vr_braw[k]) { vr_braw[k] = r; vr_bcnt[k] = 0; }
    else if (vr_bcnt[k] < 12) vr_bcnt[k]++;
    if (vr_bcnt[k] == 8 && vr_bst[k] != r) {
        vr_bst[k] = r;
        if (r) { vr_bheld[k] = 0; return 1; }
        return -1;
    }
    if (vr_bst[k]) vr_bheld[k]++;
    return 0;
}
/* on the page: every value waits for its knob, but where they already agree */
VR_COLD void vr_pick_all() {
    for (int i = 0; i < VR_NV; i++) vr_pick[i] = 1;
    for (int i = 0; i < VR_NP; i++) {
        float d = vr_pv[i] - vr_val[i];
        if (d < 0.015f && d > -0.015f) vr_pick[i] = 0;
        vr_plast[i] = vr_pshow[i] = vr_pv[i];
    }
}
VR_COLD void vr_ui(const int32_t *pot, const bool *b, int32_t enc, bool esw) {
    vr_ticks++;
    for (int i = 0; i < VR_NP; i++) {
        float raw = (float)pot[i] * (1.f / 134217728.f);
        raw = raw < 0.f ? 0.f : (raw > 1.f ? 1.f : raw);
        if (vr_ticks < 30) {
            vr_pv[i] = vr_plast[i] = vr_pshow[i] = raw;
#ifdef VR_ALONE
            vr_val[i] = raw; vr_pick[i] = 0;                      /* alone: the knobs say it from the start */
#endif
            continue;
        }
        vr_pv[i] += (raw - vr_pv[i]) * 0.06f;
    }
    /* the encoder switch: SHIFT on the page; held a second alone, and let go: the other page */
    int e = vr_btn(4, esw);
    if (e == 1) {
        vr_touched = false;
        for (int i = 0; i < VR_NP; i++) vr_psnap[i] = vr_pv[i];
    }
    if (vr_bst[4]) {
        for (int i = 0; i < VR_NP; i++) { float d = vr_pv[i] - vr_psnap[i]; if (d > 0.03f || d < -0.03f) vr_touched = true; }
        for (int k = 0; k < 4; k++) if (b[k]) vr_touched = true;
        if (enc != vr_enc_last) vr_touched = true;
    }
    bool toggled = false;
    if (e == -1) {
#ifndef VR_ALONE
        if (!vr_touched && vr_bheld[4] >= 3000) {
            vr_page = !vr_page;
            toggled = true;
            if (vr_page) vr_pick_all();
            vr_pop = -1; vr_pop_t = 0;
        }
#endif
    }
#ifndef VR_ALONE
    vr_hint = vr_bst[4] && !vr_touched && vr_bheld[4] >= 3000;
#endif
    if (!vr_page) {                                         /* the effect's page: the variations only listen to MIDI */
        vr_enc_last = enc;
        vr_shift = false;
        for (int k = 0; k < 4; k++) { vr_btn(k, b[k]); vr_sc_btn[k] = 0; }
        for (int i = 0; i < VR_NP; i++) vr_plast[i] = vr_pv[i];
        return;
    }
    /* SHIFT: the second values wait for their knobs; let go, the first ones of the knobs turned meanwhile */
    bool sh = vr_bst[4] != 0 && !toggled;
    if (sh && !vr_shift) for (int i = 5; i < VR_NP; i++) { vr_pick[vr_target(i, true)] = 1; vr_psh[i] = vr_pv[i]; }
    if (!sh && vr_shift) {
        for (int i = 5; i < VR_NP; i++) {
            float m = vr_pv[i] - vr_psh[i];
            if (m > 0.015f || m < -0.015f) vr_pick[i] = 1;
        }
    }
    vr_shift = sh;
    for (int i = 0; i < VR_NP; i++) {
        float c = vr_pv[i];
        int t = vr_target(i, sh);
        if (vr_pick[t]) {
            float a = vr_plast[i] - vr_val[t], d = c - vr_val[t];
            if ((a <= 0.f && d >= 0.f) || (a >= 0.f && d <= 0.f) || (d < 0.015f && d > -0.015f)) vr_pick[t] = 0;
        }
        if (!vr_pick[t]) vr_val[t] = c;
        float mv = c - vr_pshow[i];
        if ((mv > 0.012f || mv < -0.012f) && vr_ticks > 900) { vr_pshow[i] = c; vr_pop = t; vr_pop_t = 4500; }
        vr_plast[i] = c;
    }
    /* the encoder: with SHIFT the way back (aux), a tenth of a millisecond a click */
    int32_t d = enc - vr_enc_last;
    vr_enc_last = enc;
    if (d && sh) {
        vr_rt_ms += 0.1f * (float)d;
        if (vr_rt_ms < 0.f) vr_rt_ms = 0.f;
        if (vr_rt_ms > 5.f) vr_rt_ms = 5.f;
        routing_set();
        vr_pop = 20; vr_pop_t = 4500;
    }
    /* the buttons */
    int r0 = vr_btn(0, b[0]), r1 = vr_btn(1, b[1]), r2 = vr_btn(2, b[2]), r3 = vr_btn(3, b[3]);
    vr_sc_btn[0] = (vr_bst[0] && !sh) ? 1 : 0;              /* ROLL, held */
    vr_sc_btn[3] = (vr_bst[3] && sh) ? 1 : 0;               /* SHIFT+4: TAP */
    if (r0 == 1 && sh) { fg_align(); vr_pop = 21; vr_pop_t = 3000; }
    if (r1 == 1 && !sh) cc_freeze_toggle = true;            /* FREEZE */
    if (r2 == 1 && !sh) vr_pulito();                        /* PULITO */
    if (r3 == 1 && !sh) fg_hold_toggle();                   /* HOLD */
    (void)r0;
}
/* the values into the engines */
VR_COLD void vr_apply() {
    VR_RO static const uint8_t SC[10] = {0, 4, 5, 6, 7, 10, 11, 12, 8, 9};   /* SCENA's knob i: which value */
    for (int i = 0; i < 10; i++) {
        int v = (int)(vr_val[SC[i]] * 4095.f + 0.5f);
        vr_sc_adc[i] = v < 0 ? 0 : (v > 4095 ? 4095 : v);
    }
    fg_figo = vr_val[1]; fg_car = vr_val[2]; fg_mem = vr_val[3];
    fg_lvm = vr_val[13]; fg_lv = vr_val[14] * 1.5f;
}

/* ---------------------------------------------------------------------------------------------- the screen */
VR_FN static char *vr_put(char *p, const char *s) { while (*s) *p++ = *s++; return p; }
VR_FN static char *vr_num(char *p, int32_t v, int w) {
    char t[12];
    int n = 0;
    bool neg = v < 0;
    uint32_t u = neg ? (uint32_t)(-v) : (uint32_t)v;
    do { t[n++] = (char)('0' + u % 10u); u /= 10u; } while (u && n < 11);
    if (neg) t[n++] = '-';
    while (w-- > n) *p++ = ' ';
    while (n) *p++ = t[--n];
    return p;
}
VR_FN static void vr_end(char *l, char *p) { char *e = l + 21; while (p < e) *p++ = ' '; *e = 0; }
VR_FN static void vr_right(char *l, const char *s) { int n = 0; while (s[n]) n++; char *p = l + 21 - n; while (*s) *p++ = *s++; }
VR_FN static int32_t vr_pct(float v) { int32_t r = (int32_t)(v * 100.f + 0.5f); return r > 100 ? 100 : (r < 0 ? 0 : r); }

VR_COLD const char *vr_name(int t) {
    VR_RO static const char *const N[VR_NV] = {"SCENA", "FIGO", "CARATTERE", "MEMORIA", "MOTO", "ECO", "FEEDBACK", "FILTRO",
                                         "RIVERB", "RITORNI", "RISON", "RUMORE", "CRUSH", "LIV.MEMORIA", "LIVELLO"};
    return N[t < 0 ? 0 : (t >= VR_NV ? VR_NV - 1 : t)];
}
/* what SCENA does, on the left; its loop on the right */
VR_COLD void vr_scena_line(char *l) {
    char *p = l;
    int s = (int)(scene * 100.f + (scene >= 0.f ? 0.5f : -0.5f));
    if (released) p = vr_put(p, "RELEASE");
    else if (s == 0) p = vr_put(p, routing ? "MANDATA" : "PULITO");
    else { p = vr_put(p, s > 0 ? "BUILD " : "BREAK "); p = vr_num(p, s > 0 ? s : -s, 2); }
    vr_end(l, p);
    if (lp == 2 && lp_kind == 2) vr_right(l, "FREEZE");
    else if (lp == 2 && lp_kind == 1) vr_right(l, roll_div == 2 ? "ROLL 1/8" : (roll_div == 1 ? "ROLL 1/16" : "ROLL 1/32"));
    else if (fill == 1) vr_right(l, "FILL ROLL");
    else if (fill == 2) vr_right(l, "FILL ECO");
    else if (fill == 3) vr_right(l, "FILL DIP");
    else if (freeze_on) vr_right(l, "FREEZE..");
}
/* what FIGO does, on the left; MEMORIA on the right */
VR_COLD void vr_figo_line(char *l) {
    char *p = l;
    if (!fg_on && (fg_ev == FG_NONE || fg_ev == FG_DRY)) p = vr_put(p, routing ? "PULITO (MUTO)" : "PULITO");
    else if (fg_hold || fg_ev == FG_HOLD) p = vr_put(p, "HOLD");
    else if (fg_req_hold) p = vr_put(p, "HOLD..");
    else if (fg_ev != FG_NONE && fg_ev != FG_DRY) {
        p = vr_put(p, fg_name(fg_ev));
        if (fg_ev == FG_SKIP) { *p++ = ' '; p = vr_num(p, fg_last_n, 1); }
    }
    vr_end(l, p);
    if (fg_bev == FG_MEMO) { char t[12]; char *q = vr_put(t, "MEM -"); q = vr_num(q, fg_bn, 1); *q = 0; vr_right(l, t); }
    else if (fg_bev == FG_ECO) vr_right(l, "ECO");
}
VR_COLD void vr_pop_lines(char *l3, char *l4) {
    char *p = l3;
    if (vr_pop == 20) {
        p = vr_put(p, "ANTICIPO (AUX)");
        vr_end(l3, p);
        char t[12]; char *q = vr_num(t, (int32_t)(vr_rt_ms * 10.f + 0.5f) / 10, 1); *q++ = '.';
        *q++ = (char)('0' + (int32_t)(vr_rt_ms * 10.f + 0.5f) % 10); q = vr_put(q, " ms"); *q = 0;
        vr_right(l3, t);
        p = vr_put(l4, routing ? "le ripetizioni prima" : "(solo su un bus)");
        vr_end(l4, p);
        return;
    }
    if (vr_pop == 21) {
        p = vr_put(p, "FRASE: PARTE QUI");
        vr_end(l3, p);
        vr_end(l4, l4);
        return;
    }
    int t = vr_pop;
    float v = vr_val[t];
    p = vr_put(p, vr_name(t));
    vr_end(l3, p);
    char s[16]; char *q = s;
    if (t == 0) {
        float u = v * 2.f - 1.f;
        int n = (int)((u < 0.f ? -u : u) * 100.f + 0.5f);
        if (n < 7) q = vr_put(q, "PULITO");
        else { q = vr_put(q, u > 0.f ? "BUILD " : "BREAK "); q = vr_num(q, n, 2); }
    } else if (t == 5) {
        int i = (int)(v * 7.f); if (i > 6) i = 6;
        q = vr_put(q, sc_div_name(i));
    } else if (t == 14) {
        q = vr_num(q, (int32_t)(v * 150.f + 0.5f), 3);
    } else q = vr_num(q, vr_pct(v), 3);
    if (vr_pick[t]) q = vr_put(q, " ~");
    *q = 0;
    vr_right(l3, s);
    /* the bar, and where the knob is while it waits */
    char *b = l4;
    *b++ = '[';
    int fill_n = (int)(v * 19.f + 0.5f);
    int k = -1;
    for (int i = 0; i < VR_NP; i++) if (vr_target(i, vr_shift) == t) k = i;
    int at = k >= 0 ? (int)(vr_pv[k] * 19.f + 0.5f) : -1;
    for (int i = 0; i < 19; i++) *b++ = (vr_pick[t] && i == at) ? 'o' : (i < fill_n ? '#' : '-');
    *b++ = ']';
    vr_end(l4, b);
}
VR_COLD void vr_draw(int n) {
    char *l = vr_ln[n], *p = l;
    if (n == 0) {
        if (vr_shift) {
            p = vr_put(p, "SHIFT RIS"); p = vr_num(p, vr_pct(vr_val[10]), 2);
            p = vr_put(p, " RUM"); p = vr_num(p, vr_pct(vr_val[11]), 2);
            p = vr_put(p, " CR"); p = vr_num(p, vr_pct(vr_val[12]), 2);
            vr_end(l, p);
        } else {
            p = vr_put(p, "FIGO"); p = vr_num(p, vr_pct(vr_val[1]), 4);
            p = vr_put(p, " C"); p = vr_num(p, vr_pct(vr_val[2]), 2);
            p = vr_put(p, " M"); p = vr_num(p, vr_pct(vr_val[3]), 2);
            vr_end(l, p);
            vr_right(l, routing ? "AUX" : "INS");
        }
        return;
    }
    if (n == 1) {
        if (vr_shift) {
            p = vr_put(p, "LIV.MEM"); p = vr_num(p, vr_pct(vr_val[13]), 4);
            p = vr_put(p, "  LIV"); p = vr_num(p, (int32_t)(vr_val[14] * 150.f + 0.5f), 4);
            vr_end(l, p);
        } else vr_scena_line(l);
        return;
    }
    if (vr_pop_t > 0 && vr_pop >= 0) {
        if (n == 2) vr_pop_lines(vr_ln[2], vr_ln[3]);
        return;
    }
    if (n == 2) {
        int bpm10 = (int)(SC_SR * 600.f / beat_len + 0.5f);
        p = vr_num(p, bpm10 / 10, 3); *p++ = '.'; *p++ = (char)('0' + bpm10 % 10);
        p = vr_put(p, src == 2 ? " MIDI" : (src == 1 ? " TAP" : " INT"));
        vr_end(l, p);
        char t[12]; char *q = vr_put(t, "FRASE ");
        int nb = fg_pb;
        *q++ = (char)('1' + nb / 4 % 8); *q++ = '.'; *q++ = (char)('1' + nb % 4); *q = 0;
        vr_right(l, t);
        return;
    }
    vr_figo_line(l);
}
/* the hint on line 4 while the encoder is held alone: let go and the page changes */
VR_COLD void vr_hint_line(char *l) {
    char *p = vr_put(l, vr_page ? "LASCIA: " VR_FX_NAME : "LASCIA: VARIAZIONI");
    vr_end(l, p);
}

/* the LEDs of the page: 1 the beat, 2 FIGO plays (dim: MEMORIA), 3 SCENA build (blue) / break (red),
   4 HOLD or a loop of SCENA (blue), SHIFT or PULITO (red, PULITO blinks) */
VR_COLD void vr_leds(int32_t *led) {
    float bb = scene > 0.f ? scene : 0.f, kk = scene < 0.f ? -scene : 0.f;
    vr_blink = (vr_blink + 1) % 1500;
    bool aon = !(fg_a.h.dry && fg_a.xf == 0 && !fg_a.loop) || fg_gate_t < 1.f;
    led[0] = frac < 0.12f ? VR_LM : 0;
    led[1] = aon ? VR_LM : (fg_bon ? VR_LM / 6 : 0);
    led[2] = (int32_t)(bb * (float)VR_LM);
    led[3] = (int32_t)(kk * (float)VR_LM);
    led[4] = (fg_hold || fg_ev == FG_HOLD || lp == 2 || freeze_on) ? VR_LM : 0;
    led[5] = (vr_shift || (!fg_on && vr_blink < 750) || (released && vr_blink < 750)) ? VR_LM : 0;
}

/* -------------------------------------------------------------------------------------------- the block */
/* in: what comes in; fx: the effect's out (alone: nothing). lines and leds in: the effect's panel; out: what the
   screen and the LEDs show */
VR_HOT void vr_block(const int32_t *inl, const int32_t *inr, const int32_t *fxl, const int32_t *fxr,
              int32_t *outl, int32_t *outr, const int32_t *pot, const bool *b, int32_t enc, bool esw,
              char *const *pline, const int32_t *pled, char **line, int32_t *led) {
    vr_midi_apply();
    vr_ui(pot, b, enc, esw);
    vr_apply();
    sc_krate();
    fg_krate();
    const int32_t *xl = inl, *xr = vr_mono ? inl : inr;
    if (vr_routing == 0) {
#ifdef VR_ALONE
        const int32_t *cl = xl, *cr = xr;
#else
        const int32_t *cl = fxl, *cr = fxr;
#endif
        fg_audio(cl, cr, vr_tl, vr_tr);
        sc_audio(vr_tl, vr_tr, outl, outr);
        /* SCENA doing nothing gives the same in float; then what came is what goes (bit for bit) */
        const float IN = 1.f / 134217728.f, OUT = 134217728.f;
        for (int j = 0; j < SC_BS; j++) {
            if (outl[j] == (int32_t)(sc_clamp(vr_tl[j] * IN, -1.f, 0.9999999f) * OUT)) outl[j] = vr_tl[j];
            if (outr[j] == (int32_t)(sc_clamp(vr_tr[j] * IN, -1.f, 0.9999999f) * OUT)) outr[j] = vr_tr[j];
        }
    } else {
        fg_audio(xl, xr, vr_fl, vr_fr);
        sc_audio(xl, xr, vr_xl, vr_xr);
        for (int j = 0; j < SC_BS; j++) {
#ifdef VR_ALONE
            outl[j] = vr_fl[j] + vr_xl[j];
            outr[j] = vr_fr[j] + vr_xr[j];
#else
            outl[j] = fxl[j] + vr_fl[j] + vr_xl[j];
            outr[j] = fxr[j] + vr_fr[j] + vr_xr[j];
#endif
        }
    }
    /* the screen: one line every 40 blocks */
    if (vr_pop_t > 0) vr_pop_t--;
    if (++vr_dtick >= 40) {
        vr_dtick = 0;
        if (vr_page) vr_draw(vr_dline);
        vr_dline = (vr_dline + 1) & 3;
    }
    if (vr_hint) vr_hint_line(vr_hl);
    if (vr_page) {
        for (int n = 0; n < 4; n++) line[n] = vr_ln[n];
        vr_leds(led);
    } else {
        for (int n = 0; n < 4; n++) line[n] = pline[n];
        for (int k = 0; k < 6; k++) led[k] = pled[k];
    }
    if (vr_hint) line[3] = vr_hl;
}
