// SCENA, tested on the computer: the engine of the Gills patch (scena_engine.h) in a class with fake knobs,
// buttons and LEDs, signals in, the output measured.
//     c++ -std=c++11 -O2 tools/gills/test_scena.cpp -o build/test_scena && build/test_scena
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

static int g_adc[10], g_btn[4], g_led[4];

class Scena {
public:
    static int hw_adc(int i) { return g_adc[i]; }
    static int hw_btn(int i) { return g_btn[i]; }
    static void hw_led(int i, bool on) { g_led[i] = on ? 1 : 0; }
#include "scena_engine.h"
};

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

static std::vector<int16_t> EL, ER, RL, RR;
static std::vector<float> RV;
static Scena *S;
static long T;                                // samples run
static double clock_at = -1, clock_step = 0;   // the MIDI clock: next tick (samples), samples per tick

static void boot() {
    delete S;
    S = new Scena();
    EL.assign(Scena::SC_ECHO_N, 0); ER.assign(Scena::SC_ECHO_N, 0);
    RL.assign(Scena::SC_ROLL_N, 0); RR.assign(Scena::SC_ROLL_N, 0);
    RV.assign(Scena::SC_RV_TOTAL, 0.f);
    for (int i = 0; i < 10; i++) g_adc[i] = 2048;
    g_adc[0] = 2048;                          // SCENA in the middle
    g_adc[1] = 0;                             // MOTO off
    for (int i = 0; i < 4; i++) g_btn[i] = 0;
    S->sc_init(EL.data(), ER.data(), RL.data(), RR.data(), RV.data());
    T = 0;
    clock_at = -1;
}

static void pot(int i, double v) { g_adc[i] = (int)(v * 4095 + 0.5); }

// run n samples: in(t, &l, &r) gives the input; the output goes to ol/or (if given)
template <class F>
static void run(long n, F in, std::vector<float> *ol = nullptr, std::vector<float> *orr = nullptr,
                std::vector<float> *il = nullptr) {
    int32_t a[16], b[16], c[16], d[16];
    for (long done = 0; done < n; done += 16) {
        if (clock_at >= 0) {
            while (clock_at <= T + 16) { S->sc_midi(0xF8, 0, 0); clock_at += clock_step; }
        }
        for (int j = 0; j < 16; j++) {
            float l, r;
            in(T + j, l, r);
            a[j] = (int32_t)lrintf(l * 134217728.f) & ~15;      // a codec gives 24 bits
            b[j] = (int32_t)lrintf(r * 134217728.f) & ~15;
            if (il) il->push_back(a[j] / 134217728.f);
        }
        S->sc_block(a, b, c, d);
        for (int j = 0; j < 16; j++) {
            if (ol) ol->push_back(c[j] / 134217728.f);
            if (orr) orr->push_back(d[j] / 134217728.f);
        }
        T += 16;
    }
}
static void silence(long t, float &l, float &r) { (void)t; l = r = 0.f; }
static uint32_t nseed = 1;
static float wnoise() { nseed = nseed * 1664525u + 1013904223u; return ((int32_t)nseed) * (1.f / 2147483648.f); }

static double rms(const std::vector<float> &v, size_t a, size_t b) {
    double s = 0;
    for (size_t i = a; i < b && i < v.size(); i++) s += v[i] * v[i];
    return std::sqrt(s / std::max<size_t>(1, b - a));
}
static double db(double x) { return 20 * std::log10(x + 1e-12); }

static void start_clock(double bpm) {
    clock_step = 48000.0 * 60 / bpm / 24;
    clock_at = T;
    S->sc_midi(0xFA, 0, 0);
}

// a loop to listen to: drums and bass made here, SCENA moved by a hand that goes clean -> build -> break -> roll
static void render(const char *path) {
    boot();
    start_clock(124);
    pot(1, 0.6); pot(2, 2.5 / 7); pot(3, 0.6); pot(4, 0.8); pot(5, 0.4); pot(6, 0.5); pot(7, 0.7); pot(8, 0.6); pot(9, 0.8);
    const double bl = 48000.0 * 60 / 124;
    const long bars = 16, n = (long)(bl * 4 * bars);
    std::vector<int16_t> pcm;
    auto drums = [bl](long t, float &l, float &r) {
        double b = t / bl, ph = b - floor(b);
        int step = (int)(b * 4) % 16;
        double s8 = b * 2 - floor(b * 2);
        float kick = ph < 0.25 ? (float)(sin(2 * M_PI * (50 + 120 * exp(-ph * 30)) * ph * bl / 48000) * exp(-ph * 9)) : 0.f;
        float hat = (float)(wnoise() * exp(-s8 * 40) * 0.25);
        float sn = ((int)b % 2 == 1) ? (float)(wnoise() * exp(-ph * 14) * 0.5 + sin(2 * M_PI * 190 * ph * bl / 48000) * exp(-ph * 20) * 0.3) : 0.f;
        static const int notes[16] = {0, 0, 12, 0, 3, 0, 15, 0, 0, 0, 12, 0, 7, 0, 10, 0};
        double f = 55 * pow(2.0, notes[step] / 12.0);
        double s16 = b * 4 - floor(b * 4);
        float bass = (float)(sin(2 * M_PI * f * t / 48000) * exp(-s16 * 3) * 0.35);
        l = r = 0.33f * (0.9f * kick + hat + sn + bass);
        r += 0.05f * hat;
    };
    for (long done = 0; done < n; done += 16) {
        double bar = (done / bl) / 4;
        double sc;
        if (bar < 4) sc = 0.5;                                    /* clean */
        else if (bar < 8) sc = 0.5 + 0.5 * (bar - 4) / 4;         /* the build-up, slowly to the right */
        else if (bar < 8.25) sc = 0.5;                            /* the drop: clean */
        else if (bar < 12) sc = 0.18;                             /* break-down */
        else sc = 0.62;                                           /* a little build, MOTO moves it */
        pot(0, sc);
        g_btn[0] = (bar >= 7.5 && bar < 8.0) || (bar >= 15.5) ? 1 : 0;   /* ROLL at the end of the build and the end */
        std::vector<float> ol, orr;
        run(16, drums, &ol, &orr);
        for (int j = 0; j < 16; j++) {
            pcm.push_back((int16_t)lrintf(ol[j] * 32767.f));
            pcm.push_back((int16_t)lrintf(orr[j] * 32767.f));
        }
    }
    FILE *f = fopen(path, "wb");
    uint32_t data = (uint32_t)pcm.size() * 2, riff = 36 + data, sr = 48000, br = 48000 * 4, fmtlen = 16;
    uint16_t pcmfmt = 1, ch = 2, ba = 4, bits = 16;
    fwrite("RIFF", 1, 4, f); fwrite(&riff, 4, 1, f); fwrite("WAVEfmt ", 1, 8, f); fwrite(&fmtlen, 4, 1, f);
    fwrite(&pcmfmt, 2, 1, f); fwrite(&ch, 2, 1, f); fwrite(&sr, 4, 1, f); fwrite(&br, 4, 1, f); fwrite(&ba, 2, 1, f);
    fwrite(&bits, 2, 1, f); fwrite("data", 1, 4, f); fwrite(&data, 4, 1, f); fwrite(pcm.data(), 2, pcm.size(), f);
    fclose(f);
    printf("wrote %s (%ld bars at 124 bpm)\n", path, bars);
}

int main(int argc, char **argv) {
    if (argc > 2 && std::string(argv[1]) == "--render") { render(argv[2]); return 0; }
    printf("in the middle: what goes in comes out, bit for bit, whatever the other knobs say\n");
    {
        boot();
        for (int i = 1; i < 10; i++) pot(i, (i * 37 % 100) / 100.0);
        pot(1, 0.8);
        std::vector<float> o, in;
        nseed = 7;
        run(48000 * 3, [](long t, float &l, float &r) { (void)t; l = wnoise() * 0.7f; r = wnoise() * 0.7f; }, &o, nullptr, &in);
        size_t diff = 0;
        for (size_t i = 0; i < o.size(); i++) if (o[i] != in[i]) diff++;
        check(diff == 0, fmt("clean is clean (%.0f samples differ)", (double)diff));
    }

    printf("build-up: the high pass climbs, the hiss comes, the echo opens\n");
    {
        boot();
        pot(4, 1.0); pot(5, 0.0); pot(6, 0.0); pot(3, 0.0); pot(9, 0.0);
        pot(0, 1.0);
        std::vector<float> o;
        run(48000, [](long t, float &l, float &r) { l = r = 0.5f * sinf(2 * 3.14159265f * 50 * t / 48000.f); }, &o);
        double att = db(rms(o, 36000, 48000) / (0.5 / std::sqrt(2.0)));
        check(att < -30, fmt("a 50 Hz tone is cut on the right (%.1f dB)", att));
        boot();
        pot(4, 1.0); pot(6, 1.0); pot(3, 0.0); pot(9, 0.0); pot(0, 1.0);
        std::vector<float> on;
        run(48000, silence, &on);
        check(rms(on, 24000, 48000) > 0.01, fmt("the noise rises with RUMORE (rms %.3f)", rms(on, 24000, 48000)));
        pot(0, 0.5);
        std::vector<float> on2;
        run(48000, silence, &on2);
        check(rms(on2, 24000, 48000) < 1e-6, "back in the middle: no noise");
    }

    printf("break-down: the low pass comes down, the crush, the reverb's wash\n");
    {
        boot();
        pot(4, 1.0); pot(5, 0.0); pot(7, 0.0); pot(8, 0.0); pot(3, 0.0);
        pot(0, 0.0);
        std::vector<float> o;
        run(48000, [](long t, float &l, float &r) { l = r = 0.5f * sinf(2 * 3.14159265f * 5000 * t / 48000.f); }, &o);
        double att = db(rms(o, 36000, 48000) / (0.5 / std::sqrt(2.0)));
        check(att < -40, fmt("a 5 kHz tone is cut on the left (%.1f dB)", att));
        boot();
        pot(4, 0.0); pot(7, 1.0); pot(0, 0.0); pot(3, 0.0); pot(8, 0.0); pot(9, 0.0);
        std::vector<float> oc;
        run(48000, [](long t, float &l, float &r) { l = r = 0.5f * sinf(2 * 3.14159265f * 440 * t / 48000.f); }, &oc);
        // the crush: steps in the wave (count distinct values in a period window)
        int changes = 0;
        for (size_t i = 40001; i < 41000; i++) if (oc[i] != oc[i - 1]) changes++;
        check(changes < 400, fmt("CRUSH holds samples (%.0f changes in 1000)", (double)changes));
        boot();
        pot(4, 0.0); pot(7, 0.0); pot(8, 1.0); pot(9, 1.0); pot(3, 0.0);
        pot(0, 0.0);
        std::vector<float> orv;
        run(24000, [](long t, float &l, float &r) { l = r = (t % 12000 < 2400) ? 0.5f * sinf(t * 0.05f) : 0.f; }, &orv);
        check(rms(orv, 21000, 24000) > 0.003, fmt("RIVERB leaves a tail after the sound (rms %.4f)", rms(orv, 21000, 24000)));
    }

    printf("the echo: in time with the clock, repeats that fade; RELEASE: clean now, the tail rings out\n");
    {
        boot();
        start_clock(120);
        pot(2, 3.5 / 7);                  // 1/4
        pot(3, 0.5); pot(9, 1.0); pot(4, 0.0); pot(6, 0.0); pot(8, 0.0);
        pot(0, 0.85);
        run(48000 * 2, silence);
        std::vector<float> o;
        long t0 = T;
        run(48000 * 2, [t0](long t, float &l, float &r) { l = r = (t - t0 < 48) ? 0.8f : 0.f; }, &o);
        // the first repeat about a beat (24000 samples) later
        size_t best = 0; float bv = 0;
        for (size_t i = 20000; i < 28000; i++) if (fabsf(o[i]) > bv) { bv = fabsf(o[i]); best = i; }
        check(bv > 0.05 && labs((long)best - 24000) < 200, fmt("a repeat after a beat (at %.0f, %.3f)", (double)best, bv));
        float bv2 = 0;
        for (size_t i = 44000; i < 52000 && i < o.size(); i++) bv2 = std::max(bv2, fabsf(o[i]));
        check(bv2 < bv && bv2 > 0.005, fmt("the next one quieter (%.3f < %.3f)", bv2, bv));
        // RELEASE: a second of sound into the echo, then RELEASE and silence
        nseed = 3;
        run(48000, [](long t, float &l, float &r) { (void)t; l = r = wnoise() * 0.5f; });
        g_btn[2] = 1; run(48 * 16, silence); g_btn[2] = 0;
        check(S->released, "RELEASE pressed: clean");
        std::vector<float> o2;
        run(24000, silence, &o2);
        check(rms(o2, 0, 24000) > 0.01, fmt("the echo still rings after RELEASE (rms %.4f)", rms(o2, 0, 24000)));
        run(48000 * 4, silence);
        std::vector<float> o3, in3;
        run(4800, [](long t, float &l, float &r) { l = r = 0.3f * sinf(t * 0.01f); }, &o3, nullptr, &in3);
        double d = 0;
        for (size_t i = 0; i < o3.size(); i++) d = std::max(d, (double)fabsf(o3[i] - in3[i]));
        check(d < 0.01, fmt("after the tail, released = clean, with the knob still on the right (%.4f)", d));
        pot(0, 0.5); run(4800, silence);
        check(!S->released, "the knob back in the middle takes it back");
        pot(0, 1.0); run(48000, silence);
        check(S->scene > 0.5, "and to the right again: the build-up again");
    }

    printf("the MIDI clock: the tempo, the screen\n");
    {
        boot();
        start_clock(128);
        pot(2, 1.5 / 7);                  // 1/8
        run(48000 * 2, silence);
        check(S->src == 2, "the source is MIDI");
        double bl = S->beat_len;
        check(fabs(bl - 48000 * 60.0 / 128) < 30, fmt("128 bpm measured (%.1f samples a beat, %.1f wanted)", bl, 48000 * 60.0 / 128));
        check(fabs(S->echo_time_t - bl * 0.5) < 20, "the echo at 1/8 of it");
        S->screen();
        check(std::string(S->line[1]).find("128.0 MIDI") != std::string::npos, std::string("the screen says the tempo: ") + S->line[1]);
        check(std::string(S->line[0]).find("PULITO") != std::string::npos, std::string("and PULITO: ") + S->line[0]);
        pot(3, 0.6); run(48000 * 2, silence);
        S->screen();
        check(std::string(S->line[2]).find("FEEDBACK") != std::string::npos && std::string(S->line[2]).find("60") != std::string::npos,
              std::string("a knob moved: its name and value (") + S->line[2] + ")");
        clock_at = -1;                    // the clock goes away: back to the internal one, same tempo kept? (tap/internal)
        run(48000, silence);
        check(S->src == 0, "no clock: internal");
    }

    printf("ROLL: from the next sixteenth the slice repeats; let go, the dry is back\n");
    {
        boot();
        start_clock(120);
        pot(3, 0.0); pot(9, 0.0);
        run(48000, silence);
        auto ramp = [](long t, float &l, float &r) { l = r = (float)((t % 40000) / 40000.0 - 0.5); };
        std::vector<float> o, in;
        g_btn[0] = 1;
        run(48000, ramp, &o, nullptr, &in);
        check(S->lp == 2 && S->lp_kind == 1, "rolling");
        // a slice of 1/8 beat = 12000 samples: the output repeats with that period in the second half
        double err = 0; int n = 0;
        for (size_t i = 36000; i < 47000; i++) { err += fabs(o[i] - o[i - 12000]); n++; }
        check(err / n < 0.01, fmt("the output repeats every 1/8 beat (mean diff %.4f)", err / n));
        g_btn[0] = 0;
        std::vector<float> o2, in2;
        run(24000, ramp, &o2, nullptr, &in2);
        double d = 0;
        for (size_t i = 12000; i < 24000; i++) d = std::max(d, (double)fabsf(o2[i] - in2[i]));
        check(d < 0.002, fmt("let go: the dry again (max diff %.4f)", d));
        check(S->lp == 0, "the loop player is off");
    }

    printf("FREEZE: the beat just gone, over and over, until pressed again\n");
    {
        boot();
        start_clock(120);
        pot(3, 0.0); pot(9, 0.0); pot(1, 0.0);
        auto ramp = [](long t, float &l, float &r) { l = r = (float)((t % 70000) / 70000.0 - 0.5); };
        run(48000 * 2, ramp);
        g_btn[1] = 1; run(48 * 16, ramp); g_btn[1] = 0;
        std::vector<float> o;
        run(48000 * 2, ramp, &o);
        check(S->lp == 2 && S->lp_kind == 2, "frozen");
        double err = 0; int n = 0;
        for (size_t i = 60000; i < 90000; i++) { err += fabs(o[i] - o[i - 24000]); n++; }
        check(err / n < 0.01, fmt("the output repeats every beat (mean diff %.4f)", err / n));
        g_btn[1] = 1; run(48 * 16, ramp); g_btn[1] = 0;
        std::vector<float> o2, in2;
        run(48000, ramp, &o2, nullptr, &in2);
        double d = 0;
        for (size_t i = 30000; i < 48000; i++) d = std::max(d, (double)fabsf(o2[i] - in2[i]));
        check(d < 0.002 && S->lp == 0, fmt("pressed again: the dry from the next beat (%.4f)", d));
    }

    printf("MOTO: the fills come by themselves, at the ends of bars and phrases, only off the middle\n");
    {
        boot();
        start_clock(120);
        pot(1, 1.0); pot(3, 0.6); pot(4, 0.7); pot(9, 0.8);
        pot(0, 0.75);
        int fills = 0, wrong = 0, last = 0;
        long phrase_beats[16] = {0};
        for (int blk = 0; blk < 48000 * 64 / 16; blk++) {
            run(16, [](long t, float &l, float &r) { l = r = 0.2f * sinf(t * 0.02f); });
            if (S->fill && !last) {
                fills++;
                int pb = ((S->beat % 16) + 16) % 16;
                phrase_beats[pb]++;
                if (!(pb == 15 || pb % 4 == 3)) wrong++;
            }
            last = S->fill;
        }
        check(fills >= 3, fmt("fills in 32 bars (%.0f)", fills));
        check(wrong == 0, fmt("all on the last beat of a bar or phrase (%.0f elsewhere)", wrong));
        boot();
        start_clock(120);
        pot(1, 1.0); pot(0, 0.5);
        int f2 = 0;
        for (int blk = 0; blk < 48000 * 32 / 16; blk++) { run(16, silence); if (S->fill) f2++; }
        check(f2 == 0, "in the middle MOTO does nothing");
    }

    printf("CC 20 moves the scene; the knob takes it back\n");
    {
        boot();
        S->sc_midi(0xB0, 20, 127);
        run(48000, silence);
        check(S->scene > 0.8, fmt("CC 20 = 127: build-up (%.2f)", S->scene));
        pot(0, 0.3);
        run(48000, silence);
        check(S->scene < -0.3, fmt("the knob moved: it wins (%.2f)", S->scene));
    }

    printf("no blow-up: everything up, white noise in, twenty seconds\n");
    {
        boot();
        start_clock(140);
        for (int i = 1; i < 10; i++) pot(i, 1.0);
        double peak = 0, sum = 0; long n = 0; bool nan = false;
        for (int side = 0; side < 2; side++) {
            pot(0, side ? 1.0 : 0.0);
            std::vector<float> o;
            nseed = 11;
            run(48000 * 10, [](long t, float &l, float &r) { (void)t; l = wnoise() * 0.9f; r = wnoise() * 0.9f; }, &o);
            for (float x : o) { if (std::isnan(x)) nan = true; peak = std::max(peak, (double)fabsf(x)); sum += x * x; n++; }
        }
        check(!nan, "no NaN");
        check(peak <= 1.0, fmt("never past full scale (%.3f)", peak));
        check(std::sqrt(sum / n) < 0.9, fmt("not stuck at full scale (rms %.3f)", std::sqrt(sum / n)));
    }

    printf("TAP: the tempo from the taps when no clock comes\n");
    {
        boot();
        for (int i = 0; i < 4; i++) {
            g_btn[3] = 1; run(48 * 30, silence); g_btn[3] = 0;
            run(48000 * 60 / 100 - 48 * 30, silence);
        }
        check(S->src == 1 && fabs(S->beat_len - 28800) < 200, fmt("100 bpm tapped (%.0f samples a beat)", S->beat_len));
    }

    printf("scena: %d checks, %d failures\n", CHECKS, FAILS);
    return FAILS ? 1 : 0;
}
