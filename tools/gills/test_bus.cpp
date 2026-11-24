// A merged patch (make_bus.py --fx) on the computer, beside the effect patch as it is: both as the Patcher's C++
// (make_bus.py --cpp), the Gills' knobs, buttons, screen and LEDs faked (HOST_TEST). The same input, the same MIDI
// clock, the same knobs and buttons. With the variations doing nothing the two must sound the same, bit for bit; on
// the variations' page the effect's knobs stay where they were (its panel leaves them), and back on the effect
// nothing jumps (pick-up). tests/run_sagga_tests.sh builds it when the effect patches are given:
//   c++ -std=c++14 -O2 -DHOST_TEST -DEFFECT='"x_effect.cpp"' -DMERGED='"x_figo_scena.cpp"' -DMICROCOSM (or -DCHROMA)
//       tools/gills/test_bus.cpp
// SPDX-License-Identifier: GPL-3.0-only
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <string>
#include <vector>

#define BUFSIZE 16
typedef int32_t int32buffer[BUFSIZE];
typedef int midi_device_t;
#define MIDI_DEVICE_DIN 1
#define HT_SDRAM
int32buffer AudioInputLeft, AudioInputRight, AudioOutputLeft, AudioOutputRight;
int32_t host_pot[10];
bool host_btn[4];
int32_t host_enc;
bool host_esw;
const char *host_line[4];
int32_t host_led[6];

namespace fx {
#include EFFECT
}
namespace mg {
#include MERGED
}

static int FAILS = 0, CHECKS = 0;
static void check(bool c, const std::string &what) {
    CHECKS++;
    if (!c) { FAILS++; printf("  FAIL: %s\n", what.c_str()); }
}
static std::string fmt(const char *f, double a = 0, double b = 0, double c = 0) {
    char s[256];
    snprintf(s, sizeof s, f, a, b, c);
    return s;
}

// the hands on each patch: its knobs (0..1), buttons, encoder
struct Hands { double pot[10]; bool btn[4]; int32_t enc; bool esw; };
static void apply(const Hands &h) {
    for (int i = 0; i < 10; i++) host_pot[i] = ((int32_t)(h.pot[i] * 4095.0 + 0.5)) << 15;
    for (int k = 0; k < 4; k++) host_btn[k] = h.btn[k];
    host_enc = h.enc; host_esw = h.esw;
}

static fx::rootc *A;
static mg::rootc *B;
static Hands HA, HB;
static long T;
static double clock_at;
static uint32_t nseed = 5;
static double wnoise() { nseed = nseed * 1664525u + 1013904223u; return ((int32_t)nseed) / 2147483648.0; }
// a loop: kick, hats, snare, a bass line (24 bits, as a codec gives)
static void loop_at(long t, int32_t &l, int32_t &r) {
    const double bl = 24000;
    double b = t / bl, ph = b - floor(b);
    int step = (int)(b * 4) % 16;
    double s8 = b * 2 - floor(b * 2);
    double kick = ph < 0.25 ? sin(2 * M_PI * (50 + 120 * exp(-ph * 30)) * ph * bl / 48000) * exp(-ph * 9) : 0;
    double hat = wnoise() * exp(-s8 * 40) * 0.25;
    double sn = ((int)b % 2 == 1) ? wnoise() * exp(-ph * 14) * 0.5 : 0;
    static const int notes[16] = {0, 0, 12, 0, 3, 0, 15, 0, 0, 0, 12, 0, 7, 0, 10, 0};
    double f = 55 * pow(2.0, notes[step] / 12.0);
    double bass = sin(2 * M_PI * f * t / 48000) * exp(-(b * 4 - floor(b * 4)) * 3) * 0.35;
    double x = 0.3 * (0.9 * kick + hat + sn + bass);
    l = (int32_t)lrint(x * 134217728.0) & ~15;
    r = (int32_t)lrint((x + 0.03 * hat) * 134217728.0) & ~15;
}
// one block of both; out: how many samples differ
static int block(std::vector<float> *oa = nullptr, std::vector<float> *ob = nullptr) {
    while (clock_at <= T + 16) { A->MidiInHandler(1, 0, 0xF8, 0, 0); B->MidiInHandler(1, 0, 0xF8, 0, 0); clock_at += 1000; }
    int32_t il[16], ir[16], o1[32], o2[32];
    for (int j = 0; j < 16; j++) loop_at(T + j, il[j], ir[j]);
    for (int k = 0; k < 2; k++) {
        memcpy(AudioInputLeft, il, sizeof il); memcpy(AudioInputRight, ir, sizeof ir);
        memset(AudioOutputLeft, 0, sizeof AudioOutputLeft); memset(AudioOutputRight, 0, sizeof AudioOutputRight);
        if (k == 0) { apply(HA); A->dsp(); } else { apply(HB); B->dsp(); }
        int32_t *o = k ? o2 : o1;
        memcpy(o, AudioOutputLeft, 64); memcpy(o + 16, AudioOutputRight, 64);
    }
    int d = 0;
    for (int j = 0; j < 32; j++) if (o1[j] != o2[j]) d++;
    if (oa) for (int j = 0; j < 16; j++) oa->push_back(o1[j] / 134217728.f);
    if (ob) for (int j = 0; j < 16; j++) ob->push_back(o2[j] / 134217728.f);
    T += 16;
    return d;
}
static long run(double sec) { long d = 0; for (long n = 0; n < (long)(sec * 3000); n++) d += block(); return d; }
// the largest difference between the two outputs over that time
static double run_diff(double sec) {
    double m = 0;
    for (long n = 0; n < (long)(sec * 3000); n++) {
        std::vector<float> oa, ob;
        block(&oa, &ob);
        for (size_t i = 0; i < oa.size(); i++) m = std::max(m, (double)fabsf(oa[i] - ob[i]));
    }
    return m;
}
static bool near(float a, float b) { return fabsf(a - b) < 1e-3f; }
// the line the screen of patch B shows (its last k-cycle)
static std::string screen_b(int n) {
    apply(HB);
    std::string s = host_line[n] ? host_line[n] : "(none)";
    return s;
}

int main() {
#ifdef MICROCOSM
    const char *NAME = "Microcosm";

#else
    const char *NAME = "Chroma";
#endif
    A = new fx::rootc();
    B = new mg::rootc();
    const double K0[10] = {0.5, 0.5, 0.125, 0.95, 0.5, 0.42, 0.2, 0.7, 0.2, 0.1};
    for (int i = 0; i < 10; i++) HA.pot[i] = HB.pot[i] = K0[i];
    for (int k = 0; k < 4; k++) HA.btn[k] = HB.btn[k] = false;
    HA.enc = HB.enc = 0; HA.esw = HB.esw = false;
    apply(HA);
    A->Init(); B->Init();
    T = 0; clock_at = 0;
    A->MidiInHandler(1, 0, 0xFA, 0, 0); B->MidiInHandler(1, 0, 0xFA, 0, 0);
    auto &pa = A->objectinstance_panel_i;
    auto &pb = B->objectinstance_panel_i;
    auto &vb = B->objectinstance_variazioni_i;

    printf("%s and %s with the variations: the same sound while they do nothing\n", NAME, NAME);
    {
        long d = run(4.0);
        check(d == 0, fmt("4 seconds of a loop through both: %.0f samples differ", d));
        HA.pot[0] = HB.pot[0] = 0.85; HA.pot[4] = HB.pot[4] = 0.8;
        d = run(2.0);
        check(d == 0, fmt("two knobs turned on both: %.0f samples differ", d));
        HA.btn[1] = HB.btn[1] = true; d = run(0.15); HA.btn[1] = HB.btn[1] = false; d += run(2.0);
        check(d == 0, fmt("button 2 pressed on both: %.0f samples differ", d));
        HA.btn[0] = HB.btn[0] = true; d = run(0.15); HA.btn[0] = HB.btn[0] = false; d += run(1.0);
        check(d == 0, fmt("button 1 pressed on both: %.0f samples differ", d));
        check(screen_b(0) == std::string(pa.ln[0]), std::string("the screen is the effect's: ") + screen_b(0));
        HA.enc = HB.enc = 2; d = run(0.5);
        check(d == 0, fmt("the encoder turned on both: %.0f samples differ", d));
    }

    printf("the encoder held a second alone: the variations' page; the effect's knobs stay\n");
    float prim0[10];
    {
        HA.esw = HB.esw = true; long d = run(1.1); HA.esw = HB.esw = false; d += run(0.1);
        check(vb.vr_page && pb.pgWas, "on the variations' page (and the panel knows)");
        check(d == 0, fmt("the same sound meanwhile (%.0f samples differ)", d));
        check(screen_b(0).find("FIGO") == 0, std::string("the screen is the variations': ") + screen_b(0));
        for (int i = 0; i < 10; i++) prim0[i] = pb.prim[i];
        // the knobs move on B only: on the page they are the variations'. SCENA's (at 0.85) stays right of its value
        // (0.5), FIGO's and MEMORIA's above theirs (0): they do not take them, nothing plays
        const double K1[10] = {0.9, 0.6, 0.9, 0.5, 0.1, 0.9, 0.95, 0.15, 0.85, 0.6};
        for (int i = 0; i < 10; i++) HB.pot[i] = K1[i];
        d = run(3.0);
        int moved = 0;
        for (int i = 0; i < 10; i++) if (pb.prim[i] != prim0[i]) moved++;
        check(moved == 0, fmt("the effect's values did not move (%.0f did)", moved));
        check(d == 0, fmt("the effect sounds as before, the variations still nothing (%.0f samples differ)", d));
    }

    printf("back to the effect: nothing jumps, a knob takes its value back when it passes it\n");
    {
        HA.esw = HB.esw = true; long d = run(1.1); HA.esw = HB.esw = false; d += run(0.2);
        check(!vb.vr_page && !pb.pgWas, "on the effect's page again");
        int moved = 0;
        for (int i = 0; i < 10; i++) if (pb.prim[i] != prim0[i]) moved++;
        check(moved == 0 && d == 0, fmt("the values where they were (%.0f moved), the same sound (%.0f differ)", moved, d));
        int waiting = 0;
        for (int i = 0; i < 10; i++) if (pb.pickP[i]) waiting++;
        check(waiting >= 8, fmt("the knobs turned on the page wait to pass their values (%.0f)", waiting));
        // knob 2 back to where A has it: it passes the value, follows, and the two are the same again
        HB.pot[1] = HA.pot[1];
        d = run(1.0);
        check(!pb.pickP[1] && near(pb.prim[1], pa.prim[1]), fmt("knob 2 passed its value: it follows (%.4f, %.4f)", pb.prim[1], pa.prim[1]));
        for (int i = 0; i < 10; i++) HB.pot[i] = HA.pot[i];
        run(1.0);
        HA.pot[2] = HB.pot[2] = 0.6;
        run(1.0);
        int same = 0;
        for (int i = 0; i < 10; i++) if (near(pb.prim[i], pa.prim[i])) same++;
        double md = run_diff(1.0);
        check(same == 10, fmt("all the knobs back where A has them: all followed (%.0f of 10)", same));
        check(md < 0.01, fmt("and the two sound the same again (the largest difference %.5f)", md));
    }

    printf("the variations from MIDI on the effect's page: CC 115 FIGO up, events on top of the effect\n");
    {
        std::vector<float> oa, ob;
        B->MidiInHandler(1, 0, 0xB0, 115, 127);
        B->MidiInHandler(1, 0, 0xB0, 116, 64);
        long differ = 0;
        for (long n = 0; n < 3000L * 16; n++) differ += block(&oa, &ob);
        bool nan = false; double pk = 0;
        for (size_t i = 0; i < ob.size(); i++) { if (std::isnan(ob[i])) nan = true; pk = std::max(pk, (double)fabsf(ob[i])); }
        check(vb.fg_figo > 0.99f && differ > 1000, fmt("FIGO 100: the sound changes (%.0f samples differ in 16 s)", differ));
        check(!nan && pk < 2.0, fmt("no NaN, peak %.3f", pk));
        int moved = 0;
        for (int i = 0; i < 10; i++) if (!near(pb.prim[i], pa.prim[i])) moved++;
        check(moved == 0 && !vb.vr_page, "the effect's knobs and page as they were");
        B->MidiInHandler(1, 0, 0xB0, 115, 0);
        run(4.0);
        double md = run_diff(1.0);
        check(md < 0.01, fmt("FIGO 0 again: in aux the effect alone again (the largest difference %.5f)", md));
    }

    printf("%s+variazioni: %d checks, %d failures\n", NAME, CHECKS, FAILS);
    return FAILS ? 1 : 0;
}
