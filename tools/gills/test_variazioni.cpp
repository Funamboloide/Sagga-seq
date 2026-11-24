// VARIAZIONI (FIGO and SCENA together, for the Gills), tested on the computer: the variations object's code
// (scena_engine.h, figo_engine.h, var_engine.h) in two classes, alone and beside an effect, with fake knobs, buttons
// and MIDI. The input tells, sample by sample, when it came in (two ramps, L slow and R fast): every sample of the
// output says which moment of the input it plays, to a tenth of a sample, or that it is none (a crossfade, a level).
//     c++ -std=c++14 -O2 -Itools/gills tools/gills/test_variazioni.cpp -o build/test_variazioni && build/test_variazioni
// SPDX-License-Identifier: GPL-3.0-only
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#define FG_TEST
#define VR_ALONE
class VarA {
public:
#include "scena_engine.h"
#include "figo_engine.h"
#include "var_engine.h"
};
#undef VR_ALONE
#undef VR_FX_NAME
#define VR_FX_NAME "MICROCOSM"
class VarFx {
public:
#include "scena_engine.h"
#include "figo_engine.h"
#include "var_engine.h"
};

static int FAILS = 0, CHECKS = 0;
static void check(bool c, const std::string &what) {
    CHECKS++;
    if (!c) { FAILS++; printf("  FAIL: %s\n", what.c_str()); }
}
static std::string fmt(const char *f, double a = 0, double b = 0, double c = 0, double d = 0) {
    char s[320];
    snprintf(s, sizeof s, f, a, b, c, d);
    return s;
}

/* ------------------------------------------------------------------------------------- the input that says when */
static const long P1 = 1L << 21, P2 = 4096, OFF2 = 1000;
static double ramp(double t, long p) { double x = fmod(t, (double)p); if (x < 0) x += p; return x / p - 0.5; }
static double inL(double t) { return ramp(t, P1); }
static double inR(double t) { return ramp(t + OFF2, P2); }
static int32_t q27(double x) { return (int32_t)lrint(x * 134217728.0) & ~15; }       // a codec gives 24 bits
// the moment of the input that (l, r) plays, or -1: not one (silence, a crossfade, a level)
static double decode(double l, double r) {
    double tc = (l + 0.5) * P1;
    double tf = (r + 0.5) * P2 - OFF2;
    double t = tf + P2 * floor((tc - tf) / P2 + 0.5);
    const double tol = 1.0 / 16384;
    if (fabs(inL(t) - l) > tol || fabs(inR(t) - r) > tol) return -1;
    if (fabs(l) < 1e-9 && fabs(r) < 1e-9) return -1;
    return t;
}

/* ------------------------------------------------------------------------------------------------ the rig */
template <class V> struct Rig {
    V *v = nullptr;
    std::vector<int16_t> el, er, rl, rr;
    std::vector<float> rv;
    std::vector<uint32_t> tape;
    long T = 0;
    double clock_at = -1, clock_step = 0;
    std::vector<double> tick_t;                       // when each clock tick was due (beat k: tick_t[24 k])
    int32_t pot[10];
    bool btn[4];
    int32_t enc = 0;
    bool esw = false;
    std::vector<float> ol, orr;
    std::vector<int32_t> oli, ori;
    bool keep = true;
    char pl[4][24];
    int32_t pled[6];
    char *ln[4];
    int32_t led[6];
    int page_out = 0;
    // the events A starts, as the engine says
    struct Ev { int kind; long t0, t1; float L; int n; };
    std::vector<Ev> evs;
    struct BEv { int kind; long t0, t1; int n; float h; };
    std::vector<BEv> bevs;
    int last_ev = 0;
    uint32_t last_t0 = 0;
    int last_bev = 0;
    uint32_t last_bt0 = 0;
    void boot(int routing, float rt_ms = 1.5f, int phrase = 16, int out_kind = 0, int mono = 0) {
        delete v;
        v = new V();
        el.assign(V::SC_ECHO_N, 0); er.assign(V::SC_ECHO_N, 0);
        rl.assign(V::SC_ROLL_N, 0); rr.assign(V::SC_ROLL_N, 0);
        rv.assign(V::SC_RV_TOTAL, 0.f);
        tape.assign(V::FG_N, 0u);
        v->sc_init(el.data(), er.data(), rl.data(), rr.data(), rv.data());
        v->fg_init(tape.data());
        v->vr_init(routing, mono, rt_ms, phrase, out_kind);
        T = 0; clock_at = -1;
        for (int i = 0; i < 10; i++) pot[i] = 0;
        for (int k = 0; k < 4; k++) btn[k] = false;
        enc = 0; esw = false;
        ol.clear(); orr.clear(); oli.clear(); ori.clear();
        for (int n = 0; n < 4; n++) { snprintf(pl[n], 24, "PANEL LINE %d        ", n + 1); pl[n][21] = 0; }
        for (int k = 0; k < 6; k++) pled[k] = 1000 + k;
        evs.clear(); bevs.clear(); last_ev = 0; last_t0 = 0; last_bev = 0; last_bt0 = 0;
    }
    void knob(int i, double x) { pot[i] = (int32_t)(x * 134217727.0); }
    void start_clock(double bpm) { clock_step = 48000.0 * 60 / bpm / 24; clock_at = (double)T; tick_t.clear(); v->vr_midi(0xFA, 0, 0); }
    void tempo(double bpm) { clock_step = 48000.0 * 60 / bpm / 24; }
    // one block; in(t, l, r) gives the input, fx(t, l, r) the effect's out (beside an effect)
    template <class F, class G> void block(F in, G fx) {
        if (clock_at >= 0) while (clock_at <= T + 16) { v->vr_midi(0xF8, 0, 0); tick_t.push_back(clock_at); clock_at += clock_step; }
        int32_t a[16], b[16], c[16], d[16], o1[16], o2[16];
        for (int j = 0; j < 16; j++) {
            double l, r;
            in(T + j, l, r); a[j] = q27(l); b[j] = q27(r);
            fx(T + j, l, r); c[j] = (int32_t)lrint(l * 134217728.0); d[j] = (int32_t)lrint(r * 134217728.0);
        }
        char *p[4] = {pl[0], pl[1], pl[2], pl[3]};
        v->vr_block(a, b, c, d, o1, o2, pot, btn, enc, esw, p, pled, ln, led);
        page_out = v->vr_page ? 1 : 0;
        if (keep) for (int j = 0; j < 16; j++) {
            ol.push_back(o1[j] / 134217728.f); orr.push_back(o2[j] / 134217728.f);
            oli.push_back(o1[j]); ori.push_back(o2[j]);
        }
        if (v->fg_ev != last_ev || v->fg_t0 != last_t0) {
            if (v->fg_ev != 0) evs.push_back({v->fg_ev, (long)v->fg_t0, (long)v->fg_t1, v->fg_L, v->fg_last_n});
            last_ev = v->fg_ev; last_t0 = v->fg_t0;
        }
        if (v->fg_bev != last_bev || v->fg_bt0 != last_bt0) {
            if (v->fg_bev != 0) bevs.push_back({v->fg_bev, (long)v->fg_bt0, (long)v->fg_bt1, v->fg_bn, v->fg_bh});
            last_bev = v->fg_bev; last_bt0 = v->fg_bt0;
        }
        T += 16;
    }
    template <class F> void run(long n, F in) {
        for (long k = 0; k < n; k += 16) block(in, [](long, double &l, double &r) { l = r = 0; });
    }
    template <class F, class G> void run2(long n, F in, G fx) { for (long k = 0; k < n; k += 16) block(in, fx); }
    // run until the block where a beat starts; then the next beat's first frame, as the brain sees it
    template <class F> uint32_t to_beat(F in) {
        for (int g = 0; g < 100000; g++) {
            run(16, in);
            if (v->onbeat) {
                uint32_t now0 = v->fg_now - 16;
                uint32_t bt = now0 - (uint32_t)(v->frac * v->beat_len + 0.5f);
                return bt + (uint32_t)(v->beat_len + 0.5f);
            }
        }
        return 0;
    }
};
static void when(long t, double &l, double &r) { l = inL((double)t); r = inR((double)t); }

// what the output plays at time t (-1 none): the input's moment, the one of the ramps' turns that is before t (or
// a little after: aux plays ahead)
template <class R> static double src_raw(R &g, long t) {
    if (t < 0) return -1;
    size_t i = (size_t)t;
    if (i >= g.ol.size()) return -1;
    double x = decode(g.ol[i], g.orr[i]);
    if (x < 0) return -1;
    x += (double)P1 * floor(((double)t + 4000.0 - x) / (double)P1);
    return x;
}
// the same, but only if the samples before and after it play the moments next to it: a crossfade's mix can look like
// a moment by chance, three in a row do not
template <class R> static double src_at(R &g, long t) {
    double x = src_raw(g, t);
    if (x < 0) return -1;
    double a = src_raw(g, t - 1), b = src_raw(g, t + 1);
    if (a < 0 || b < 0 || fabs(x - a) > 3 || fabs(b - x) > 3) return -1;
    return x;
}
static double pmod(double a, double m) { double x = fmod(a, m); return x < 0 ? x + m : x; }
// FIGO's random numbers (xorshift32, as fg_rand): a state whose next two give sixteenth 15 and "backwards"
static uint32_t xs32(uint32_t &x) { x ^= x << 13; x ^= x >> 17; x ^= x << 5; return x; }
static uint32_t seed_last_backwards() {
    for (uint32_t s = 1; s < 1000000; s++) {
        uint32_t x = s;
        float a = (float)(xs32(x) >> 8) * (1.f / 16777216.f);
        int j = (int)(a * 16.f); if (j >= 16) j = 15;
        float b = (float)(xs32(x) >> 8) * (1.f / 16777216.f);
        if (j == 15 && b < 0.15f) return s;
    }
    return 0;
}
static void sine2(long t, double &l, double &r) { l = 0.5 * sin(2 * M_PI * 110 * t / 48000.0); r = 0.5 * sin(2 * M_PI * 165 * t / 48000.0); }

int main() {
    const double BL = 24000;             // a beat at 120 BPM
    const int XF = VarA::FG_XF, LEAD = VarA::FG_LEAD;
    Rig<VarA> A;
    Rig<VarFx> F;

    printf("the input that says when: decoded back to a tenth of a sample, silence is none\n");
    {
        double worst = 0; int bad = 0;
        for (long t = 0; t < 3000000; t += 37) {
            double l = (q27(inL(t)) >> 12) / 32768.0, r = (q27(inR(t)) >> 12) / 32768.0;   // as the tape has it
            double s = decode(l, r);
            if (s < 0) bad++; else { s += (double)P1 * floor(((double)t + 4000.0 - s) / (double)P1); worst = std::max(worst, fabs(s - t)); }
        }
        check(bad == 0 && worst < 0.2, fmt("every frame of the tape decodes (%.0f not, worst %.3f samples)", bad, worst));
        check(decode(0, 0) < 0, "silence is no moment");
        check(decode(0.3 * inL(1000) + 0.7 * inL(90000), 0.3 * inR(1000) + 0.7 * inR(90000)) < 0, "a mix of two is none");
    }

    printf("alone, insert, FIGO 0 and MEMORIA 0, SCENA in the middle: what comes in goes out, bit for bit\n");
    {
        A.boot(0);
        A.knob(0, 0.5);
        A.start_clock(120);
        A.run(48000 * 20, when);
        long diff = 0;
        for (long t = 0; t < (long)A.oli.size(); t++) {
            if (A.oli[t] != q27(inL(t)) || A.ori[t] != q27(inR(t))) diff++;
        }
        check(diff == 0, fmt("20 seconds, %.0f samples differ", diff));
        check(A.evs.empty() && A.bevs.empty(), "nothing happened");
    }

    printf("alone, aux, all at zero: nothing at all comes out\n");
    {
        A.boot(1);
        A.knob(0, 0.5);
        A.start_clock(120);
        A.run(48000 * 10, when);
        double pk = 0;
        for (size_t i = 0; i < A.ol.size(); i++) pk = std::max(pk, (double)std::max(fabsf(A.ol[i]), fabsf(A.orr[i])));
        check(pk == 0.0, fmt("silence (peak %.7f)", pk));
    }

    // one event of kind k, L beats, started by hand on a beat (FIGO 0: the brain starts none)
    double fbl = BL;                     // FIGO's beat when the event started (it measures the clock)
    auto force = [&](auto &R, int routing, int k, float L, double car, long warm_beats, uint32_t &t0) {
        R.boot(routing);
        R.knob(0, 0.5); R.knob(1, 0.0); R.knob(2, car); R.knob(3, 0.0);
        R.start_clock(120);
        R.run((long)(BL * warm_beats), when);
        t0 = R.to_beat(when);
        fbl = R.v->fg_bl;
        bool ok = R.v->fg_start(k, t0, L);
        R.run((long)(BL * (L + 2)), when);
        return ok;
    };

    printf("FIGO measures the beat over the last 8: within a sample of the clock's\n");
    {
        uint32_t t0;
        force(A, 0, VarA::FG_R8, 1.f, 0.5, 12, t0);
        check(fabs(fbl - BL) < 1.0, fmt("120 BPM: %.2f samples a beat (%.0f wanted)", fbl, BL));
    }

    printf("the repeats (insert): the slice that starts on the beat is the dry, then it repeats, whole from its first\n"
           "sample, until the end; then the dry again\n");
    {
        const int kinds[4] = {VarA::FG_R4, VarA::FG_R8, VarA::FG_R16, VarA::FG_R32};
        const double divs[4] = {1, 0.5, 0.25, 0.125};
        for (int q = 0; q < 4; q++) {
            uint32_t t0;
            float L = q == 0 ? 2.f : 1.f;
            bool ok = force(A, 0, kinds[q], L, 0.5, 12, t0);
            double s = divs[q] * fbl;
            long t1 = (long)t0 + (long)(L * fbl + 0.5);
            int dry_bad = 0, rep_bad = 0, rep_n = 0, none = 0, after_bad = 0, att_bad = 0;
            for (long t = (long)t0 - 2000; t < t1 + 6000; t++) {
                double x = src_at(A, t);
                if (t < (long)t0 + (long)s - LEAD) { if (x != (double)t) dry_bad++; continue; }
                if (t >= (long)t0 + (long)s && t < t1 - LEAD) {
                    double e = (double)t0 + pmod((double)(t - (long)t0), s);
                    double before_wrap = s - pmod((double)(t - (long)t0), s);
                    if (before_wrap <= XF + 1) continue;                     // (the crossfade into the next start)
                    if (x < 0) { none++; continue; }
                    rep_n++;
                    if (fabs(x - e) > 0.3) rep_bad++;
                    if (pmod((double)(t - (long)t0), s) < 1.0 && fabs(src_raw(A, t) - e) > 0.3) att_bad++;
                    continue;
                }
                if (t >= t1 + 2) { if (x != (double)t) after_bad++; }
            }
            check(ok && dry_bad == 0, std::string(VarA::fg_name(kinds[q])) + fmt(": the first slice is the dry, exact (%.0f not)", dry_bad));
            check(rep_n > 1000 && rep_bad == 0 && none < rep_n / 50,
                  std::string(VarA::fg_name(kinds[q])) + fmt(": then it repeats, sample for sample (%.0f of %.0f off, %.0f mixed)", rep_bad, rep_n, none));
            check(att_bad == 0, std::string(VarA::fg_name(kinds[q])) + fmt(": every repeat whole from its first sample (%.0f not)", att_bad));
            check(after_bad == 0, std::string(VarA::fg_name(kinds[q])) + fmt(": and the dry again after (%.0f not)", after_bad));
        }
    }

    printf("the repeats (aux, the way back 1.5 ms): silent while the dry plays its slice on the mixer, then the slice\n"
           "72 samples early, so that it lands on the mixer's grid; silence after\n");
    {
        const int kinds[3] = {VarA::FG_R4, VarA::FG_R8, VarA::FG_R16};
        const double divs[3] = {1, 0.5, 0.25};
        for (int q = 0; q < 3; q++) {
            uint32_t t0;
            float L = 2.f;
            bool ok = force(A, 1, kinds[q], L, 0.5, 12, t0);
            double s = divs[q] * fbl, rt = 72;
            long t1 = (long)t0 + (long)(L * fbl + 0.5);
            int loud = 0, rep_bad = 0, rep_n = 0, after = 0;
            for (long t = (long)t0 - 2000; t < t1 + 6000; t++) {
                double x = src_at(A, t);
                float a = std::max(fabsf(A.ol[t]), fabsf(A.orr[t]));
                if (t < (long)t0 + (long)(s - rt) - XF - 2) { if (a != 0.f) loud++; continue; }
                if (t >= (long)t0 + (long)(s - rt) && t < t1 - (long)rt - LEAD) {
                    double ph = pmod((double)(t - (long)t0) + rt, s);
                    if (s - ph <= XF + 1) continue;
                    double e = (double)t0 + ph;
                    if (x < 0) continue;
                    rep_n++;
                    if (fabs(x - e) > 0.3) rep_bad++;
                    continue;
                }
                if (t >= t1 - (long)rt + 2) { if (a != 0.f) after++; }
            }
            std::string nm = VarA::fg_name(kinds[q]);
            check(ok && loud == 0, nm + fmt(" aux: nothing before the first repeat (%.0f samples not silent)", loud));
            check(rep_n > 1000 && rep_bad == 0, nm + fmt(" aux: the slice a slice later, 72 samples early (%.0f of %.0f off)", rep_bad, rep_n));
            check(after == 0, nm + fmt(" aux: silence after (%.0f not)", after));
        }
    }

    printf("the other events, one at a time (insert): what each plays, never what is not on the tape yet\n");
    {
        uint32_t t0;
        // REVERSE: backwards (car 0.5: at speed -1; car 0.2: -0.5), from what was just played
        for (int half = 0; half < 2; half++) {
            bool ok = force(A, 0, VarA::FG_REV, 1.f, half ? 0.2 : 0.5, 12, t0);
            double want = half ? -0.5 : -1.0;
            long t1 = (long)t0 + (long)BL;
            int n = 0, bad = 0, ahead = 0;
            for (long t = (long)t0; t < t1 - LEAD - 1; t++) {
                double x = src_at(A, t), y = src_at(A, t + 1);
                if (x < 0 || y < 0) continue;
                n++;
                if (fabs((y - x) - want) > 0.05) bad++;
                if (x > (double)t - 1) ahead++;
            }
            check(ok && n > 20000 && bad == 0 && ahead == 0,
                  fmt(half ? "REVERSE (dub): at -0.5, backwards from what just played (%.0f samples, %.0f off, %.0f ahead)"
                           : "REVERSE: at -1, backwards from what just played (%.0f samples, %.0f off, %.0f ahead)", n, bad, ahead));
        }
        // OTTAVA -: half speed, from the head; it falls behind
        {
            bool ok = force(A, 0, VarA::FG_HALF, 1.f, 0.5, 12, t0);
            long t1 = (long)t0 + (long)BL;
            int n = 0, bad = 0, ahead = 0;
            for (long t = (long)t0; t < t1 - LEAD - 1; t++) {
                double x = src_at(A, t), y = src_at(A, t + 1);
                if (x < 0 || y < 0) continue;
                n++;
                if (fabs((y - x) - 0.5) > 0.05) bad++;
                if (x > (double)t - 1) ahead++;
            }
            check(ok && n > 20000 && bad == 0 && ahead == 0, fmt("OTTAVA -: at half speed, behind the head (%.0f, %.0f off, %.0f ahead)", n, bad, ahead));
        }
        // OTTAVA +: the last half beat at double speed, over and over
        {
            bool ok = force(A, 0, VarA::FG_OCT, 1.f, 0.5, 12, t0);
            long t1 = (long)t0 + (long)BL;
            double h = BL / 2;
            int n = 0, out = 0, sl = 0;
            for (long t = (long)t0; t < t1 - LEAD - 1; t++) {
                double x = src_at(A, t), y = src_at(A, t + 1);
                if (x < 0) continue;
                n++;
                if (x < (double)t0 - h - 2 * XF - 2 || x >= (double)t0) out++;
                if (y >= 0 && fabs((y - x) - 2.0) > 0.05 && fabs((y - x) + h - 2.0) > 0.05) sl++;
            }
            check(ok && n > 20000 && out == 0 && sl < 50, fmt("OTTAVA +: the last half beat, at double speed (%.0f, %.0f outside, %.0f not at 2)", n, out, sl));
        }
        // TAPE STOP: it slows down to almost nothing, then fades (at the end of a phrase: by hand here)
        {
            bool ok = force(A, 0, VarA::FG_STOP, 1.f, 0.5, 12, t0);
            double prev = 1.1; int up = 0, n = 0, ahead = 0;
            double first = 0, last = 0;
            for (long t = (long)t0 + 200; t < (long)t0 + (long)(BL * 0.7); t += 200) {
                double x = src_at(A, t), y = src_at(A, t + 1);
                if (x < 0 || y < 0) continue;
                double sp = y - x;
                if (n == 0) first = sp;
                last = sp;
                if (sp > prev + 0.01) up++;
                prev = sp; n++;
                if (x > (double)t - 1) ahead++;
            }
            float tail = 0;
            for (long t = (long)t0 + (long)BL - 300; t < (long)t0 + (long)BL - 120; t++) tail = std::max(tail, fabsf(A.ol[t] - (float)inL(t)));
            check(ok && n > 50 && up == 0 && first > 0.8 && last < 0.25 && ahead == 0,
                  fmt("TAPE STOP: slower and slower (%.2f to %.2f, %.0f faster steps, %.0f ahead)", first, last, up, ahead));
        }
        // SHUFFLE: every sixteenth one of the bar just gone, whole, forwards or backwards
        {
            bool ok = force(A, 0, VarA::FG_SHUF, 1.f, 1.0, 12, t0);
            double sx = fbl / 4, bar = (double)(int32_t)(t0 - A.v->fg_back(t0, 4));
            int bad = 0, n = 0, steps_ok = 0;
            for (int i = 0; i < 4; i++) {
                long a = (long)t0 + (long)(i * sx), b = (long)t0 + (long)((i + 1) * sx) - LEAD - 2;
                double j0 = -1; int nn = 0, bb = 0;
                for (long t = a + 2; t < b; t++) {
                    double x = src_at(A, t);
                    if (x < 0) continue;
                    double rel = x - ((double)t0 - bar);
                    if (rel < -XF - 2 || rel >= bar + 2) { bb++; continue; }
                    double j = floor((rel + 1) / sx);
                    if (j0 < 0) j0 = j;
                    nn++;
                    if (fabs(j - j0) > 0.5 && pmod(rel, sx) > XF + 2 && pmod(rel, sx) < sx - XF - 2) bb++;
                }
                n += nn; bad += bb;
                if (nn > 2000 && bb == 0) steps_ok++;
            }
            check(ok && steps_ok == 4 && bad == 0, fmt("SHUFFLE: four sixteenths of the bar before (%.0f good, %.0f off of %.0f)", steps_ok, bad, n));
        }
        // INDIETRO: what played 1, 2 or 4 bars ago, in time
        {
            bool ok = force(A, 0, VarA::FG_SKIP, 1.f, 0.5, 20, t0);
            int n = 0, bad = 0;
            double back = -1;
            for (long t = (long)t0; t < (long)t0 + (long)BL - LEAD; t++) {
                double x = src_at(A, t);
                if (x < 0) continue;
                double d = (double)t - x;
                if (back < 0) back = d;
                n++;
                if (fabs(d - back) > 0.3) bad++;
            }
            double bars = back / (4 * BL);
            check(ok && n > 20000 && bad == 0 && (fabs(bars - 1) < 5e-4 || fabs(bars - 2) < 5e-4 || fabs(bars - 4) < 5e-4),
                  fmt("INDIETRO: %.4f bars back, in time (%.0f samples, %.0f off)", bars, n, bad));
        }
        // GATE: the dry cut in sixteenths, the first of each beat always there
        {
            bool ok = force(A, 0, VarA::FG_GATE, 1.f, 0.5, 12, t0);
            int pat = A.v->fg_x;
            double sx = fbl / 4;
            int good = 0;
            for (int i = 0; i < 4; i++) {
                long mid = (long)t0 + (long)(i * sx + sx * 0.6);
                bool on = (pat >> i) & 1;
                double x = src_at(A, mid);
                bool ok_i = on ? x == (double)mid : fabsf(A.ol[mid]) < 0.002f;
                if (ok_i) good++;
            }
            check(ok && good == 4 && (pat & 1), fmt("GATE: on and off by the pattern, the first on (%.0f of 4)", good));
        }
        // ROLL: 1/4, 1/8, 1/16, 1/32 of the first beat, a quarter of the event each
        {
            bool ok = force(A, 0, VarA::FG_ROLL, 2.f, 0.3, 12, t0);
            double L = 2;
            int out = 0, n = 0, per_bad = 0, per_n = 0;
            const double D[4] = {1, 0.5, 0.25, 0.125};
            for (long t = (long)t0; t < (long)t0 + (long)(L * BL) - LEAD; t++) {
                double x = src_at(A, t);
                if (x < 0) continue;
                n++;
                if (x < (double)t0 - 2 * XF - 2 || x >= (double)t0 + BL) out++;
                int q = (int)((t - (long)t0) / (L * BL / 4));
                double len = D[q < 4 ? q : 3] * fbl;
                long t2 = t + (long)len;
                if (q >= 1 && t2 < (long)t0 + (long)((q + 1) * L * BL / 4) - LEAD) {
                    double y = src_at(A, t2);
                    if (y >= 0) { per_n++; if (fabs(y - x) > 0.3) per_bad++; }
                }
            }
            check(ok && n > 30000 && out == 0, fmt("ROLL: only the event's first beat (%.0f samples, %.0f outside)", n, out));
            check(per_n > 10000 && per_bad == 0, fmt("ROLL: each quarter repeats its slice (%.0f of %.0f off)", per_bad, per_n));
        }
    }

    printf("HOLD: from the next beat the beat just gone, over and over; let go, the dry on a beat\n");
    {
        A.boot(0);
        A.knob(0, 0.5); A.knob(1, 0.0); A.knob(2, 0.5); A.knob(3, 0.0);
        A.start_clock(120);
        A.run((long)(BL * 8), when);
        uint32_t nt = A.to_beat(when);
        A.v->fg_hold_toggle();
        A.run((long)(BL * 0.5), when);
        uint32_t bt = nt - (uint32_t)BL;                  // hmm: the brain sees it on the next beat
        A.run((long)(BL * 5), when);
        // from the beat after the press: the beat before it, repeated
        int n = 0, out = 0;
        long from = (long)nt + (long)BL;
        double lo = (double)(from - (long)BL), hi = (double)from;
        for (long t = from; t < from + (long)(BL * 3); t++) {
            double x = src_at(A, t);
            if (x < 0) continue;
            n++;
            if (x < lo - 2 * XF - 2 || x >= hi + 1) out++;
        }
        check(n > 60000 && out == 0, fmt("held: the same beat for 3 beats (%.0f samples, %.0f outside)", n, out));
        (void)bt;
        A.v->fg_hold_toggle();
        A.run((long)(BL * 2.5), when);
        long tend = (long)A.T;
        int dry = 0, m = 0;
        for (long t = tend - (long)BL; t < tend - 1; t++) { double x = src_at(A, t); m++; if (x == (double)t) dry++; }
        check(dry == m, fmt("let go: the dry again (%.0f of %.0f)", dry, m));
    }

    printf("PULITO: out with a tape stop or a backspin on the next beat, then the dry; FIGO 100 does nothing until VIA\n");
    {
        for (int kind = 1; kind <= 3; kind++) {
            A.boot(0, 1.5f, 16, kind);
            A.knob(0, 0.5); A.knob(1, 1.0); A.knob(2, 0.5); A.knob(3, 0.0);
            A.start_clock(120);
            A.run((long)(BL * 12), when);
            A.to_beat(when);
            A.v->vr_pulito();
            size_t n0 = A.evs.size();
            A.run((long)(BL * 3), when);
            bool out_ev = false;
            for (size_t i = n0; i < A.evs.size(); i++)
                if (A.evs[i].kind == (kind == 1 ? VarA::FG_TSTOP : (kind == 2 ? VarA::FG_SPIN : VarA::FG_DRY))) out_ev = true;
            size_t n1 = A.evs.size();
            long t_a = (long)A.T;
            A.run((long)(BL * 32), when);
            int dry = 0, m = 0;
            for (long t = t_a; t < (long)A.T - 1; t++) { m++; if (src_at(A, t) == (double)t) dry++; }
            check(out_ev && A.evs.size() == n1 && dry == m,
                  fmt(kind == 1 ? "tape stop, then 32 beats of dry and no event (%.0f of %.0f dry, %.0f events)"
                     : kind == 2 ? "backspin, then 32 beats of dry and no event (%.0f of %.0f dry, %.0f events)"
                                 : "dry at once, then 32 beats of dry and no event (%.0f of %.0f dry, %.0f events)",
                      dry, m, (double)(A.evs.size() - n1)));
            A.v->vr_pulito();
            A.run((long)(BL * 32), when);
            check(A.evs.size() > n1 + 3, fmt("VIA: the events again (%.0f in 32 beats)", (double)(A.evs.size() - n1)));
        }
    }

    // the brain, FIGO up: what happens, where, and that it plays only the tape that is there
    int stop_wrong = 0, aux_wrong = 0;                // (set by brain: TAPE STOP off a bar's end; in aux GATE, lone slices)
    auto brain = [&](auto &R, int routing, double car, double figo, long beats, double bpm, int &events, int &bad_grid,
                     int &past_phrase, int &ahead, int &stale, int &gap_bad, int &kinds) {
        R.boot(routing);
        R.knob(0, 0.5); R.knob(1, figo); R.knob(2, car); R.knob(3, 0.0);
        R.start_clock(bpm);
        double bl = 48000.0 * 60 / bpm;
        R.run((long)(bl * beats), when);
        events = (int)R.evs.size();
        ahead = (int)R.v->fg_test_ahead;
        bad_grid = past_phrase = stale = gap_bad = 0;
        int seen[64] = {0};
        for (auto &e : R.evs) {
            seen[e.kind & 63] = 1;
            double b = (double)e.t0 / bl;                    // the clock started at 0: beats are multiples of bl
            if (fabs(b - floor(b + 0.5)) * bl > 48) bad_grid++;
            long beat = (long)floor(b + 0.5);
            double inph = (double)(beat % 16) + e.L;
            if (inph > 16.001) past_phrase++;
            if (e.kind == VarA::FG_STOP && fmod(inph, 4.0) > 0.001) stop_wrong++;
            if (routing && e.kind == VarA::FG_GATE) aux_wrong++;
            static const double DIV[5] = {0, 1, 0.5, 0.25, 0.125};
            if (routing && e.kind >= VarA::FG_R4 && e.kind <= VarA::FG_R32 && e.L < 2 * DIV[e.kind] - 1e-6) aux_wrong++;
        }
        kinds = 0;
        for (int k = 0; k < 64; k++) kinds += seen[k];
        double rd = routing ? 72 : 0;
        std::vector<char> fade(R.T + 16, 0);
        for (auto &e : R.evs) {
            long a = -1, z = -1;
            if (e.kind == VarA::FG_STOP || e.kind == VarA::FG_TSTOP) { a = e.t0 + (long)((e.t1 - e.t0) * 0.7); z = e.t1 + 200; }
            if (e.kind == VarA::FG_GATE) { a = e.t0 - 200; z = e.t1 + 400; }
            for (long t = std::max(0L, a); t < z && t < (long)fade.size(); t++) fade[t] = 1;
        }
        for (long t = (long)(bl * 4); t < (long)R.T; t++) {
            if (fade[t]) continue;
            double x = src_at(R, t);
            if (x < 0) continue;
            if (x > (double)t + 2) ahead++;          // (a crossfade's first samples can look one sample on)
            if (x < (double)t - (4 * 4 * bl + 3 * bl)) stale++;
        }
        // between the events: the dry (insert) or silence (aux)
        for (size_t i = 0; i + 1 < R.evs.size(); i++) {
            long a = std::max(R.evs[i].t1, std::min(R.evs[i + 1].t0, R.evs[i].t1 + 40)) + 16;
            long b = R.evs[i + 1].t0 - LEAD - 8 - (long)rd;
            if (R.evs[i + 1].kind >= VarA::FG_R4 && R.evs[i + 1].kind <= VarA::FG_R32) b = R.evs[i + 1].t0 + 200 - (long)rd;
            for (long t = a; t < b && t < (long)R.T; t++) {
                if (routing == 0) { if (src_at(R, t) != (double)t) gap_bad++; }
                else if (R.ol[t] != 0.f) gap_bad++;
            }
        }
    };

    printf("the brain, FIGO 100: events on the beats, never past the phrase, only the tape that is there,\n"
           "and the dry (or, in aux, silence) between them; at 90, 120 and 174 BPM, dub and glitch\n");
    {
        const double bpms[3] = {90, 120, 174};
        for (int routing = 0; routing < 2; routing++)
            for (int bi = 0; bi < 3; bi++)
                for (int ci = 0; ci < 2; ci++) {
                    int ev, grid, past, ahead, stale, gap, kinds;
                    double car = ci ? 0.9 : 0.1;
                    brain(A, routing, car, 1.0, 96, bpms[bi], ev, grid, past, ahead, stale, gap, kinds);
                    std::string w = std::string(routing ? "aux " : "insert ") + fmt("%.0f bpm ", bpms[bi]) + (ci ? "glitch: " : "dub: ");
                    check(ev > 25 && kinds >= 5, w + fmt("%.0f events, %.0f kinds", ev, kinds));
                    check(grid == 0 && past == 0, w + fmt("on the beat (%.0f not), not past the phrase (%.0f)", grid, past));
                    check(ahead == 0 && stale == 0, w + fmt("never a frame not on the tape yet (%.0f reads), never an old one (%.0f)", ahead, stale));
                    check(gap == 0, w + fmt("the dry between the events (%.0f samples not)", gap));
                    check(stop_wrong == 0, w + fmt("TAPE STOP only at the end of a bar or phrase (%.0f not)", stop_wrong));
                    if (routing) check(aux_wrong == 0, w + fmt("no GATE, no repeat with only its first slice (%.0f)", aux_wrong));
                    stop_wrong = aux_wrong = 0;
                }
    }

    printf("more FIGO, more events; most at the end of the phrase\n");
    {
        int ev_lo, ev_hi, g, p, a, s, gb, k;
        brain(A, 0, 0.5, 0.3, 256, 120, ev_lo, g, p, a, s, gb, k);
        brain(A, 0, 0.5, 1.0, 256, 120, ev_hi, g, p, a, s, gb, k);
        int end_ph = 0, first = 0;
        for (auto &e : A.evs) {
            long beat = (long)floor((double)e.t0 / BL + 0.5) % 16;
            if (beat >= 12) end_ph++;
            if (beat == 0 || beat == 4 || beat == 8) first++;
        }
        check(ev_hi > ev_lo * 2, fmt("FIGO 30: %.0f events, FIGO 100: %.0f", ev_lo, ev_hi));
        check(end_ph > first * 2, fmt("in the last bar of the phrase %.0f, on the ones %.0f", end_ph, first));
    }

    printf("START from SAGGA in the middle of an event: it ends when it was going to; the next ones on the new beats\n");
    {
        A.boot(0);
        A.knob(0, 0.5); A.knob(1, 1.0); A.knob(2, 0.5); A.knob(3, 0.0);
        A.start_clock(120);
        A.run((long)(BL * 40), when);
        // wait for an event that lasts 2 beats, START in its middle
        long t_start = -1;
        for (int g = 0; g < 4000 && t_start < 0; g++) {
            A.run(16, when);
            if (A.v->fg_ev != 0 && A.v->fg_L >= 2.f && (long)A.T > (long)A.v->fg_t0 + (long)(BL * 0.7)) {
                A.start_clock(120);                         // (a START: the beat count back to 0, the clock from now)
                t_start = (long)A.T;
            }
        }
        long t1 = A.evs.empty() ? 0 : A.evs.back().t1;
        size_t n0 = A.evs.size();
        A.run((long)(BL * 32), when);
        int off = 0;
        for (size_t i = n0; i < A.evs.size(); i++) {
            if (A.evs[i].t0 < t_start + (long)(2 * BL)) continue;      // (decided before it)
            double b = (double)(A.evs[i].t0 - t_start) / BL;
            if (fabs(b - floor(b + 0.5)) * BL > 48) off++;
        }
        int dry_after = 0, m = 0;
        long nxt = A.evs.size() > n0 ? A.evs[n0].t0 - LEAD - 8 : (long)A.T;
        for (long t = t1 + 8; t < nxt && t < t1 + (long)BL; t++) { m++; if (src_at(A, t) == (double)t) dry_after++; }
        check(t_start > 0 && A.evs.size() > n0 + 5, fmt("events go on after START (%.0f)", (double)(A.evs.size() - n0)));
        check(off == 0, fmt("all on the beats counted from START (%.0f not)", off));
        check(m == 0 || dry_after == m, fmt("the event cut by START ended as it was going to, the dry after it (%.0f of %.0f)", dry_after, m));
    }

    printf("MEMORIA: a bar of 1, 2, 4 or 8 bars ago under the dry, on a bar's first beat; ECO: the half beat after\n"
           "the dry, again and again, quieter each time\n");
    {
        // the input: a short tone, a different pitch every bar; MEMORIA brings back the one of n bars ago
        auto tones = [](long t, double &l, double &r) {
            long bar = t / 96000;
            double f = 200.0 + 37.0 * (bar % 13);
            double ph = (double)(t % 96000) / 48000;
            l = r = 0.3 * sin(2 * M_PI * f * t / 48000.0) * (ph < 1.5 ? 1 : 0);
        };
        A.boot(0);
        A.knob(0, 0.5); A.knob(1, 0.0); A.knob(2, 0.2); A.knob(3, 1.0);
        A.start_clock(120);
        A.run((long)(BL * 4 * 48), tones);
        int memo = 0, eco = 0, on_bar = 0, good = 0, eco_good = 0;
        for (auto &e : A.bevs) {
            double b = (double)e.t0 / BL;
            if (fabs(b - floor(b + 0.5)) * BL < 48 && ((long)floor(b + 0.5)) % 4 == 0) on_bar++;
            if (e.kind == VarA::FG_MEMO) {
                memo++;
                // what MEMORIA added (out - in) has the pitch of the bar n bars before: count its zero crossings
                if (e.h > 1.5f) { good++; continue; }                  // (at double speed: an octave up, not checked)
                long a = e.t0 + (long)(BL * 0.6), z = std::min(e.t0 + (long)(BL * 2.4), e.t1 - (long)BL);
                int cross = 0; double prev = 0;
                for (long t = a; t < z && t < (long)A.T; t++) {
                    double l, r;
                    tones(t, l, r);
                    double d = A.ol[t] - l;
                    if ((prev < 0 && d >= 0) || (prev > 0 && d <= 0)) cross++;
                    if (d != 0) prev = d;
                }
                double f = cross / 2.0 / ((z - a) / 48000.0);
                long bar = (long)floor((double)(e.t0 + BL) / 96000.0) - e.n;
                double want = 200.0 + 37.0 * (bar % 13);
                if (fabs(f - want) < 8) good++;
                else printf("    MEMORIA -%d at %ld: %.1f Hz, the bar then had %.1f\n", e.n, e.t0, f, want);
            } else {
                eco++;
                long a = e.t0 + (long)e.h + 400, z = a + (long)e.h - 800;
                double sxy = 0, sxx = 0, syy = 0, lv1 = 0, lv2 = 0;
                for (long t = a; t < z && t + (long)e.h < (long)A.T; t++) {
                    double l, r, lb, rb;
                    tones(t, l, r); tones(t - (long)e.h, lb, rb);
                    double d = A.ol[t] - l;
                    sxy += d * lb; sxx += d * d; syy += lb * lb;
                    double l2, r2; tones(t + (long)e.h, l2, r2);
                    double d2 = A.ol[t + (long)e.h] - l2;
                    lv1 += d * d; lv2 += d2 * d2;
                }
                if (sxx > 0 && syy > 0 && sxy / sqrt(sxx * syy) > 0.5 && lv2 < lv1) eco_good++;
            }
        }
        check(memo + eco > 8, fmt("MEMORIA %.0f times, ECO %.0f", memo, eco));
        check(on_bar == memo + eco, fmt("on the first beat of a bar (%.0f of %.0f)", on_bar, memo + eco));
        check(memo == 0 || good >= memo * 3 / 4, fmt("MEMORIA plays the bar of n bars ago (%.0f of %.0f)", good, memo));
        check(eco == 0 || eco_good >= eco * 3 / 4, fmt("ECO repeats the half beat, quieter each time (%.0f of %.0f)", eco_good, eco));
    }

    printf("the tempo drifts (120 to 123 BPM in 16 beats): INDIETRO 4 bars back starts on the beat that was there\n");
    {
        A.boot(0);
        A.knob(0, 0.5); A.knob(1, 0.0); A.knob(2, 0.5); A.knob(3, 0.0);
        A.start_clock(120);
        A.run((long)(BL * 8), when);
        double bpm = 120;
        for (int b = 0; b < 16; b++) { bpm += 3.0 / 16; A.tempo(bpm); A.run((long)(48000.0 * 60 / bpm), when); }
        uint32_t t0 = A.to_beat(when);
        bool ok = false;
        for (int g = 0; g < 50 && !ok; g++) { ok = A.v->fg_start(VarA::FG_SKIP, t0, 1.f) && A.v->fg_last_n == 4; if (!ok) A.v->fg_ev = 0; }
        double got = (double)(int32_t)(A.v->fg_ls - t0), tempo = -16.0 * A.v->fg_bl;
        A.run((long)(BL * 2), when);
        // the beat at t0 and the one 16 before it, by the clock's ticks (beat k: its 24 k-th tick)
        long B = -1; double best = 1e18;
        for (size_t k = 0; 24 * k < A.tick_t.size(); k++) {
            double d = fabs(A.tick_t[24 * k] - (double)t0);
            if (d < best) { best = d; B = (long)k; }
        }
        double want = B >= 16 ? A.tick_t[24 * (B - 16)] - A.tick_t[24 * B] : 1e9;
        double heard = 1e9;                                   // and what is heard, past the crossfade
        for (long t = (long)t0 + 200; t < (long)t0 + 3000 && heard > 1e8; t++) { double x = src_at(A, t); if (x >= 0) heard = x - (double)t; }
        check(ok && best < 48 && fabs(got - want) < 32 && fabs(heard - got) < 2,
              fmt("4 bars back: %.0f samples from the beat that was, heard %.0f (by the tempo alone: %.0f)",
                  got - want, heard - want, tempo - want));
        double b4 = (double)(int32_t)(A.v->fg_back(t0, 4) - t0), b16 = (double)(int32_t)(A.v->fg_back(t0, 16) - t0);
        double w4 = B >= 4 ? A.tick_t[24 * (B - 4)] - A.tick_t[24 * B] : 1e9;
        check(fabs(b4 - w4) < 32 && fabs(b16 - want) < 32,
              fmt("asked again two beats on (as SHUFFLE does): 1 bar back %.0f, 4 bars back %.0f samples from the beats", b4 - w4, b16 - want));
    }

    printf("a START in the middle of a beat: INDIETRO 4 bars back, across it, lands on a beat that was there\n");
    {
        A.boot(0);
        A.knob(0, 0.5); A.knob(1, 0.0); A.knob(2, 0.5); A.knob(3, 0.0);
        A.start_clock(120);
        A.run((long)(BL * 12.5), when);
        std::vector<double> old = A.tick_t;
        A.start_clock(120);                                   // START again, half a beat on
        A.run((long)(BL * 8), when);
        uint32_t t0 = A.to_beat(when);
        bool ok = false;
        for (int g = 0; g < 50 && !ok; g++) { ok = A.v->fg_start(VarA::FG_SKIP, t0, 1.f) && A.v->fg_last_n == 4; if (!ok) A.v->fg_ev = 0; }
        A.run((long)(BL * 2), when);                          // (the tick of t0's beat comes)
        long B = -1; double best = 1e18;
        for (size_t k = 0; 24 * k < A.tick_t.size(); k++) {
            double d = fabs(A.tick_t[24 * k] - (double)t0);
            if (d < best) { best = d; B = (long)k; }
        }
        long m = (long)((old.size() - 1) / 24);               // the last beat before the START
        long j = m - 15 + B;                                  // 16 beats back, the START's short one among them
        // (relative to t0: the engine's beats are a block or two before the ticks, its t0 too)
        double want = j >= 0 ? old[24 * j] - A.tick_t[24 * B] : -1e9, got = (double)(int32_t)(A.v->fg_ls - t0),
               tempo = -16.0 * A.v->fg_bl;
        check(ok && best < 48 && fabs(got - want) < 32,
              fmt("on beat %.0f of before the START: %.0f samples from it (by the tempo it would be %.0f, off the grid)",
                  (double)j, got - want, tempo - want));
    }

    printf("MEMORIA at double speed (glitch, at times): never a frame not on the tape yet\n");
    {
        A.boot(0);
        A.knob(0, 0.5); A.knob(1, 0.0); A.knob(2, 0.95); A.knob(3, 1.0);
        A.start_clock(120);
        A.run((long)(BL * 4 * 64), when);
        int doubles = 0;
        for (auto &e : A.bevs) if (e.kind == VarA::FG_MEMO && e.h > 1.5f) doubles++;
        check(doubles > 0 && A.v->fg_test_ahead == 0, fmt("%.0f at double speed, %.0f reads not on the tape", doubles, A.v->fg_test_ahead));
    }

    printf("no clicks: a sine in, FIGO 100 and MEMORIA 100, dub and glitch, insert and aux: every step a small one\n");
    {
        double nested = 0;
        for (int routing = 0; routing < 2; routing++)
            for (int ci = 0; ci < 2; ci++) {
                A.boot(routing);
                A.knob(0, 0.5); A.knob(1, 1.0); A.knob(2, ci ? 0.9 : 0.1); A.knob(3, 1.0);
                A.start_clock(128);
                auto sine = [](long t, double &l, double &r) { l = 0.5 * sin(2 * M_PI * 110 * t / 48000.0); r = 0.5 * sin(2 * M_PI * 165 * t / 48000.0); };
                A.run((long)(48000.0 * 60 / 128 * 64), sine);
                double worst = 0; long at = 0;
                for (size_t i = 1; i < A.ol.size(); i++) {
                    double d = std::max(fabs(A.ol[i] - A.ol[i - 1]), fabs(A.orr[i] - A.orr[i - 1]));
                    if (d > worst) { worst = d; at = (long)i; }
                }
                // a 165 Hz sine at 0.5 moves 0.011 a sample at most; a crossfade of 96 samples between any two of its
                // moments, 0.5 / 96 more; a hard jump would be up to 1
                check(worst < 0.04, std::string(routing ? "aux " : "insert ") + (ci ? "glitch" : "dub") +
                      fmt(": the largest step %.4f (at %.0f), %.0f changes in a crossfade (%.0f in two)", worst, (double)at,
                          A.v->fg_test_nested, A.v->fg_test_third));
                nested += A.v->fg_test_nested;
            }
        check(nested > 0, fmt("(and the case is there: %.0f changes came in a crossfade)", nested));
    }

    printf("one event right where the one before ends: a TAPE STOP, then a repeat; a repeat, then GATE\n");
    {
        auto sine = [](long t, double &l, double &r) { l = 0.5 * sin(2 * M_PI * 110 * t / 48000.0); r = 0.5 * sin(2 * M_PI * 165 * t / 48000.0); };
        // k1 on a beat, k2 right at its end (8 samples on, as the brain does it), FIGO 0 otherwise
        auto pair = [&](int k1, float L1, int k2, float L2, bool use_sine, uint32_t &t0, uint32_t &t0b) {
            A.boot(0);
            A.knob(0, 0.5); A.knob(1, 0.0); A.knob(2, 0.5); A.knob(3, 0.0);
            A.start_clock(120);
            if (use_sine) A.run((long)(BL * 12), sine); else A.run((long)(BL * 12), when);
            t0 = use_sine ? A.to_beat(sine) : A.to_beat(when);
            bool ok = A.v->fg_start(k1, t0, L1);
            A.v->fg_nx = k2; A.v->fg_nx_t0 = A.v->fg_t1 + 8; A.v->fg_nx_L = L2;
            t0b = A.v->fg_nx_t0;
            if (use_sine) A.run((long)(BL * (L1 + L2 + 2)), sine); else A.run((long)(BL * (L1 + L2 + 2)), when);
            return ok;
        };
        uint32_t t0, t0b;
        bool ok = pair(VarA::FG_STOP, 1.f, VarA::FG_R8, 1.f, true, t0, t0b);
        double worst = 0;
        for (long t = (long)t0 - 2000; t < (long)t0b + (long)BL + 2000; t++)
            worst = std::max(worst, (double)std::max(fabs(A.ol[t] - A.ol[t - 1]), fabs(A.orr[t] - A.orr[t - 1])));
        check(ok && worst < 0.04, fmt("TAPE STOP, then 1/8: no click where the stopped tape goes (largest step %.4f)", worst));
        ok = pair(VarA::FG_STOP, 1.f, VarA::FG_R8, 1.f, false, t0, t0b);
        double s = 0.5 * A.v->fg_bl;
        int n = 0, bad = 0;
        for (long t = (long)t0b + (long)s + 200; t < (long)t0b + (long)(2 * s) - LEAD - 4; t++) {
            double x = src_at(A, t);
            n++;
            if (fabs(x - ((double)t0b + pmod((double)(t - (long)t0b), s))) > 0.3) bad++;
        }
        check(ok && n > 10000 && bad == 0, fmt("and the 1/8 repeats at its level, not the stopped tape's (%.0f of %.0f off)", bad, n));
        ok = pair(VarA::FG_R8, 1.f, VarA::FG_GATE, 1.f, false, t0, t0b);
        n = 0; bad = 0;
        for (long t = (long)t0b + 2; t < (long)t0b + (long)(0.25 * A.v->fg_bl) - 300; t++) {
            n++;
            if (src_at(A, t) != (double)t) bad++;
        }
        check(ok && n > 5000 && bad == 0, fmt("1/8, then GATE: the GATE cuts the dry, the repeat is gone (%.0f of %.0f not the dry)", bad, n));
    }

    printf("MEMORIA left and right swapped; ECO quieter each time, the last one to nothing; PULITO takes MEMORIA too\n");
    {
        // a tone on the left only: MEMORIA's is louder on the right
        auto toneL = [](long t, double &l, double &r) { l = 0.3 * sin(2 * M_PI * (200.0 + 37.0 * ((t / 96000) % 13)) * t / 48000.0); r = 0; };
        A.boot(0);
        A.knob(0, 0.5); A.knob(1, 0.0); A.knob(2, 0.2); A.knob(3, 0.0);
        A.start_clock(120);
        A.run((long)(BL * 4 * 6), toneL);
        uint32_t t0 = A.to_beat(toneL);
        bool ok = A.v->fg_start_b(VarA::FG_MEMO, t0, 4.f);
        A.run((long)(BL * 5), toneL);
        double el = 0, er = 0;
        for (long t = (long)t0 + (long)BL; t < (long)t0 + (long)(BL * 3); t++) {
            double l, r; toneL(t, l, r);
            el += (A.ol[t] - l) * (A.ol[t] - l); er += (A.orr[t] - r) * (A.orr[t] - r);
        }
        check(ok && er > 1e-3 && er > 9 * el, fmt("a tone on the left only: MEMORIA %.1f times louder on the right", sqrt(er / std::max(el, 1e-12))));
        // ECO in aux (what comes out is ECO alone): every repeat quieter, the last fades to nothing
        A.boot(1);
        A.knob(0, 0.5); A.knob(1, 0.0); A.knob(2, 0.2); A.knob(3, 0.0);
        A.start_clock(120);
        A.run((long)(BL * 4 * 3), sine2);
        t0 = A.to_beat(sine2);
        ok = A.v->fg_start_b(VarA::FG_ECO, t0, 4.f);
        A.run((long)(BL * 6), sine2);
        double bh = A.v->fg_bh, rt = 72;
        int reps = A.v->fg_breps;
        std::vector<double> rms;
        for (int k = 1; k <= reps + 1; k++) {
            double e = 0; long n = 0;
            for (long t = (long)(t0 + k * bh - rt) + 300; t < (long)(t0 + (k + 1) * bh - rt) - 300; t++) { e += A.ol[t] * A.ol[t]; n++; }
            rms.push_back(sqrt(e / std::max(n, 1L)));
        }
        double tail = 0; long tn = 0;
        for (long t = (long)(t0 + (reps + 1.75) * bh - rt); t < (long)(t0 + (reps + 2) * bh - rt) - 120; t++) { tail += A.ol[t] * A.ol[t]; tn++; }
        tail = sqrt(tail / std::max(tn, 1L));
        int down = 0;
        for (int k = 1; k < reps; k++) if (rms[k] < rms[k - 1] * 0.9) down++;
        check(ok && reps >= 2 && rms[0] > 0.05 && down == reps - 1 && tail < 0.05 * rms[0],
              fmt("ECO: %.0f repeats, %.0f each quieter, the end of the last at %.3f of the first", reps, down, tail / std::max(rms[0], 1e-9)));
        // PULITO (going out dry here) during a long MEMORIA: it fades with FIGO
        A.boot(1, 1.5f, 16, 3);
        A.knob(0, 0.5); A.knob(1, 0.0); A.knob(2, 0.2); A.knob(3, 0.0);
        A.start_clock(120);
        A.run((long)(BL * 4 * 6), sine2);
        t0 = A.to_beat(sine2);
        ok = A.v->fg_start_b(VarA::FG_MEMO, t0, 8.f);
        A.run((long)(BL * 2), sine2);
        float during = 0;
        for (long t = (long)t0 + (long)BL; t < (long)A.T; t++) during = std::max(during, std::max(fabsf(A.ol[t]), fabsf(A.orr[t])));
        A.v->vr_pulito();
        A.run((long)(BL * 8), sine2);
        float pk = 0;
        for (long t = (long)t0 + (long)(BL * 3) + 14400; t < (long)t0 + (long)(BL * 9); t++) pk = std::max(pk, std::max(fabsf(A.ol[t]), fabsf(A.orr[t])));
        check(ok && during > 0.05f && pk < 0.002f, fmt("PULITO during MEMORIA (%.2f): 0.3 s after its beat, peak %.4f", during, pk));
    }

    printf("SHUFFLE never plays backwards a sixteenth whose end is not on the tape yet\n");
    {
        A.boot(0);
        A.knob(0, 0.5); A.knob(1, 0.0); A.knob(2, 1.0); A.knob(3, 0.0);
        A.start_clock(120);
        A.run((long)(BL * 12), when);
        uint32_t t0 = A.to_beat(when);
        bool ok = A.v->fg_start(VarA::FG_SHUF, t0, 1.f);
        uint32_t seed = seed_last_backwards();
        A.v->fg_rng = seed;                                    // (the first step: the bar's last sixteenth, backwards)
        A.run((long)(BL * 3), when);
        int fw = 0, n = 0;
        for (long t = (long)t0 + 200; t < (long)t0 + (long)(BL / 4) - LEAD - 4; t++) {
            double x = src_at(A, t), y = src_at(A, t + 1);
            if (x < 0 || y < 0) continue;
            n++;
            if (fabs((y - x) - 1.0) < 0.05) fw++;
        }
        check(ok && seed && n > 4000 && fw == n && A.v->fg_test_ahead == 0,
              fmt("the last sixteenth asked backwards at the first step: forwards (%.0f of %.0f), %.0f reads not on the tape", fw, n, A.v->fg_test_ahead));
    }

    printf("no blow-up: everything up, white noise, FIGO and MEMORIA 100, SCENA all over, ROLL and FREEZE\n");
    {
        for (int routing = 0; routing < 2; routing++) {
            A.boot(routing);
            for (int i = 0; i < 10; i++) A.knob(i, 1.0);
            A.start_clock(140);
            uint32_t ns = 7;
            auto noise = [&ns](long, double &l, double &r) {
                ns = ns * 1664525u + 1013904223u; l = (int32_t)ns / 2147483648.0 * 0.9;
                ns = ns * 1664525u + 1013904223u; r = (int32_t)ns / 2147483648.0 * 0.9;
            };
            bool nan = false; double pk = 0;
            for (int side = 0; side < 4; side++) {
                A.knob(0, side & 1 ? 1.0 : 0.0);
                A.btn[0] = side == 2; A.btn[1] = side == 3;
                A.ol.clear(); A.orr.clear(); A.oli.clear(); A.ori.clear();
                A.run(48000 * 6, noise);
                for (size_t i = 0; i < A.ol.size(); i++) {
                    if (std::isnan(A.ol[i]) || std::isnan(A.orr[i])) nan = true;
                    pk = std::max(pk, (double)std::max(fabsf(A.ol[i]), fabsf(A.orr[i])));
                }
            }
            check(!nan && pk <= 2.01, fmt(routing ? "aux: no NaN, peak %.3f" : "insert: no NaN, peak %.3f", pk));
        }
    }

    printf("beside an effect: the page is the effect's at first, the screen and the LEDs are its panel's\n");
    {
        F.boot(1);
        F.start_clock(120);
        auto fx = [](long t, double &l, double &r) { l = 0.3 * sin(t * 0.01); r = 0.3 * cos(t * 0.013); };
        F.run2(48000, when, fx);
        check(F.page_out == 0, "the effect's page");
        check(F.ln[0] == F.pl[0] && F.ln[3] == F.pl[3], "the screen: the panel's lines");
        check(F.led[0] == F.pled[0] && F.led[5] == F.pled[5], "the LEDs: the panel's");
        // the knobs move: the variations do not
        for (int i = 0; i < 10; i++) F.knob(i, 0.9);
        F.run2(48000, when, fx);
        check(F.v->vr_val[1] == 0.f && fabsf(F.v->vr_val[0] - 0.5f) < 1e-6f, "the knobs on the effect's page leave the variations as they are");
    }

    printf("beside an effect, the variations doing nothing: the effect comes out as it is, bit for bit\n");
    {
        for (int routing = 0; routing < 2; routing++) {
            F.boot(routing);
            F.start_clock(120);
            uint32_t ns = 3;
            auto fx = [&ns](long, double &l, double &r) {   // any 27 bits, not only a codec's 24
                ns = ns * 1664525u + 1013904223u; l = ((int32_t)ns >> 4) / 134217728.0;
                ns = ns * 1664525u + 1013904223u; r = ((int32_t)ns >> 4) / 134217728.0;
            };
            F.keep = false;
            long diff = 0;
            for (long k = 0; k < 48000L * 12; k += 16) {
                uint32_t keep_ns = ns;
                F.keep = true; F.ol.clear(); F.orr.clear(); F.oli.clear(); F.ori.clear();
                long t0 = F.T;
                F.block(when, fx);
                ns = keep_ns;
                for (int j = 0; j < 16; j++) {
                    double l, r; fx(t0 + j, l, r);
                    if (F.oli[j] != (int32_t)lrint(l * 134217728.0) || F.ori[j] != (int32_t)lrint(r * 134217728.0)) diff++;
                }
                (void)t0;
            }
            check(diff == 0, fmt(routing ? "aux: 12 seconds, %.0f samples differ" : "insert: 12 seconds, %.0f samples differ", diff));
        }
    }

    printf("the page: the encoder held a second alone and let go; shorter, or with something touched, nothing\n");
    {
        F.boot(1);
        F.start_clock(120);
        auto fx = [](long, double &l, double &r) { l = r = 0; };
        F.run2(48000, when, fx);
        F.esw = true; F.run2(48 * 800, when, fx); F.esw = false; F.run2(48 * 60, when, fx);
        check(F.page_out == 0, "0.8 seconds: still the effect's page");
        F.esw = true; F.run2(48 * 1100, when, fx);
        check(std::string(F.ln[3]).find("LASCIA: VARIAZIONI") == 0, std::string("held a second: the screen says so: ") + F.ln[3]);
        F.esw = false; F.run2(48 * 60, when, fx);
        check(F.page_out == 1, "a second alone and let go: the variations' page");
        check(F.ln[0] == F.v->vr_ln[0] && std::string(F.ln[0]).find("FIGO") == 0, std::string("its screen: ") + F.ln[0]);
        auto press = [&](int k) { F.btn[k] = true; F.run2(48 * 60, when, fx); F.btn[k] = false; F.run2(48 * 60, when, fx); };
        press(3);
        check(F.v->fg_req_hold || F.v->fg_hold, "button 4 on the page: HOLD");
        press(3);
        press(1);
        bool fr = F.v->freeze_on;
        press(1);
        check(fr && !F.v->freeze_on, "button 2: FREEZE, and off again");
        press(2);
        bool pu = !F.v->fg_on;
        press(2);
        check(pu && F.v->fg_on, "button 3: PULITO, and FIGO back");
        F.run2(48 * 400, when, fx);
        F.esw = true; F.run2(48 * 300, when, fx);
        F.knob(4, 0.7); F.run2(48 * 900, when, fx);
        F.esw = false; F.run2(48 * 60, when, fx);
        check(F.page_out == 1, "held with a knob turned: SHIFT, not the page");
        F.esw = true; F.run2(48 * 300, when, fx);
        F.btn[1] = true; F.run2(48 * 100, when, fx); F.btn[1] = false;
        F.run2(48 * 900, when, fx);
        F.esw = false; F.run2(48 * 60, when, fx);
        check(F.page_out == 1, "held with a button pressed: not the page");
        F.esw = true; F.run2(48 * 1100, when, fx);
        check(std::string(F.ln[3]).find("LASCIA: MICROCOSM") == 0, std::string("and back: ") + F.ln[3]);
        F.esw = false; F.run2(48 * 60, when, fx);
        check(F.page_out == 0, "a second alone again: the effect's page");
    }

    printf("the page: the knobs take their values back when they pass them (pick-up); SHIFT has its own\n");
    {
        F.boot(1);
        F.start_clock(120);
        auto fx = [](long, double &l, double &r) { l = r = 0; };
        for (int i = 0; i < 10; i++) F.knob(i, 0.8);
        F.run2(48000, when, fx);
        F.esw = true; F.run2(48 * 1100, when, fx); F.esw = false; F.run2(48 * 60, when, fx);
        check(F.page_out == 1, "on the page");
        F.knob(1, 0.6); F.run2(48 * 300, when, fx);
        check(F.v->vr_val[1] == 0.f && F.v->vr_pick[1], fmt("FIGO's knob at 0.6, its value 0: waits (%.2f)", F.v->vr_val[1]));
        check(std::string(F.ln[2]).find("FIGO") == 0 && std::string(F.ln[2]).find("~") != std::string::npos
              && std::string(F.ln[3]).find("o") != std::string::npos,
              std::string("the screen shows it waiting: ") + F.ln[2] + " / " + F.ln[3]);
        F.knob(1, 0.0); F.run2(48 * 200, when, fx);
        F.knob(1, 0.35); F.run2(48 * 300, when, fx);
        check(!F.v->vr_pick[1] && fabsf(F.v->vr_val[1] - 0.35f) < 0.02f, fmt("past 0 and up: it follows (%.2f)", F.v->vr_val[1]));
        check(fabsf(F.v->fg_figo - 0.35f) < 0.02f, "and FIGO hears it");
        // SHIFT: knob 7 is RUMORE
        float rum = F.v->vr_val[11];
        F.esw = true; F.run2(48 * 100, when, fx);
        F.knob(6, rum); F.run2(48 * 100, when, fx);
        F.knob(6, 0.9); F.run2(48 * 300, when, fx);
        F.esw = false; F.run2(48 * 60, when, fx);
        check(fabsf(F.v->vr_val[11] - 0.9f) < 0.02f && F.page_out == 1, fmt("SHIFT + knob 7: RUMORE %.2f, still on the page", F.v->vr_val[11]));
        check(fabsf(F.v->vr_val[6] - 0.4f) < 1e-6f, fmt("and FEEDBACK (knob 7 without SHIFT) as it was (%.2f)", F.v->vr_val[6]));
        F.knob(6, 0.2); F.run2(48 * 300, when, fx);
        F.esw = true; F.run2(48 * 200, when, fx);
        check(fabsf(F.v->vr_val[11] - 0.9f) < 0.02f, fmt("SHIFT again, knob 7 now at 0.2: RUMORE waits at %.2f", F.v->vr_val[11]));
        F.esw = false; F.run2(48 * 60, when, fx);
        // back to the effect: the values stay
        float fg = F.v->vr_val[1];
        F.esw = true; F.run2(48 * 1100, when, fx); F.esw = false; F.run2(48 * 60, when, fx);
        for (int i = 0; i < 10; i++) F.knob(i, 0.1);
        F.run2(48000, when, fx);
        check(F.page_out == 0 && F.v->vr_val[1] == fg, "on the effect's page again the values stay");
    }

    printf("MIDI CC 110-119 from any page; CC 20-24 are the effect's beside it, SCENA's alone\n");
    {
        F.boot(0);
        F.start_clock(120);
        auto fx = [](long, double &l, double &r) { l = r = 0; };
        F.run2(48000, when, fx);
        F.v->vr_midi(0xB0, 115, 127); F.v->vr_midi(0xB2, 116, 64); F.v->vr_midi(0xB0, 117, 0);
        F.run2(480, when, fx);
        check(fabsf(F.v->fg_figo - 1.f) < 1e-6f && fabsf(F.v->fg_car - 64.f / 127) < 1e-6f, "CC 115 FIGO, 116 CARATTERE (any channel)");
        for (int k = 1; k <= 16; k++) F.v->vr_midi(0xB0, 117, (uint8_t)k);
        F.run2(480, when, fx);
        check(fabsf(F.v->fg_mem - 16.f / 127) < 1e-6f, fmt("16 CCs between two blocks: all, in order (MEMORIA %.0f of 127)", F.v->fg_mem * 127));
        F.v->vr_midi(0xB0, 110, 127);
        F.run2(48000, when, fx);
        check(F.v->scene > 0.8f, fmt("CC 110: SCENA to the build-up (%.2f)", F.v->scene));
        F.v->vr_midi(0xB0, 20, 0);
        F.run2(48000, when, fx);
        check(F.v->scene > 0.8f, "CC 20 does nothing here (it is the effect's)");
        F.v->vr_midi(0xB0, 118, 127);
        F.run2((long)(BL * 2), when, fx);
        check(F.v->fg_hold || F.v->fg_ev == VarFx::FG_HOLD, "CC 118: HOLD");
        F.v->vr_midi(0xB0, 118, 127);
        F.run2((long)(BL * 2), when, fx);
        check(!F.v->fg_hold && F.v->fg_ev != VarFx::FG_HOLD, "CC 118 again: let go");
        F.v->vr_midi(0xB0, 119, 127);
        F.run2((long)(BL * 0.5), when, fx);
        check(!F.v->fg_on && F.v->released, "CC 119: FIGO PULITO and SCENA RELEASE");
        A.boot(0);
        A.knob(0, 0.5);
        A.start_clock(120);
        A.run(48000, when);
        A.v->vr_midi(0xB0, 20, 0);
        A.run(48000, when);
        check(A.v->scene < -0.8f, fmt("alone: CC 20 moves SCENA (%.2f)", A.v->scene));
    }

    printf("the way back on the page: SHIFT + encoder, a tenth of a millisecond a click\n");
    {
        F.boot(1, 1.5f);
        F.start_clock(120);
        auto fx = [](long, double &l, double &r) { l = r = 0; };
        F.run2(48000, when, fx);
        F.esw = true; F.run2(48 * 1100, when, fx); F.esw = false; F.run2(48 * 60, when, fx);
        F.esw = true; F.run2(48 * 100, when, fx);
        F.enc = 3; F.run2(48 * 100, when, fx);
        F.esw = false; F.run2(48 * 100, when, fx);
        check(fabsf(F.v->vr_rt_ms - 1.8f) < 1e-4f && F.v->fg_rt == 86 && F.v->sc_rt == 86 && F.page_out == 1,
              fmt("three clicks: %.1f ms, %.0f samples, still on the page", F.v->vr_rt_ms, F.v->fg_rt));
    }

    printf("variazioni: %d checks, %d failures\n", CHECKS, FAILS);
    return FAILS ? 1 : 0;
}
