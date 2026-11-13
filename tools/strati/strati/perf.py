# SPDX-License-Identifier: GPL-3.0-only
"""A performance played through a target's patch (in its model): the notes as they were, the noise control as it
moved. What `strati pad` writes as previews, and how its targets are scored against the original."""
import numpy as np

from .audio import SR
from . import dexed, norns, surge
from .pad import ctrl_gain_cut


def ctrl_samples(perf, n):
    t = np.arange(n) / SR
    return np.interp(t, perf["ctrl_times"], perf["ctrl"])


def play(perf, voice, tail=2.0, ctrl=None):
    """every note through voice(note, gate_s, n_samples, ctrl_curve) -> samples, at its time"""
    n = int((perf["duration"] + tail) * SR)
    out = np.zeros(n)
    c_all = ctrl_samples(perf, n) if ctrl is None else ctrl[:n]
    for a, b, note in perf["notes"]:
        s = int(a * SR)
        gate = max(b - a, 0.05)
        m = min(n - s, int((gate + tail) * SR))
        if m <= 0:
            continue
        y = voice(note, gate, m, c_all[s:s + m])[:m]
        out[s:s + len(y)] += y
    return out


def norns_voice(red, cents=0.0):
    def v(note, gate, n, c):
        return norns.simulate(red, note=note + cents / 100.0, gate=gate, dur=n / SR, ctrl=c, seed=note * 31 + int(gate * 100))[:n]
    return v


def dexed_voice(dv, cents=0.0):
    def v(note, gate, n, c):
        return dexed.simulate(dv, note, gate, n / SR, cents=cents)[:n]
    return v


def surge_voice(p, cents=0.0):
    """the Surge model with what a pad patch uses: the wavetable's frame (two detuned voices), the amp EG, the noise
    through its tilt and low-pass, level and cutoff on the mod wheel (scene-level: the same curve)"""
    from scipy.signal import lfilter
    A, B = p["scenes"].get("A"), p["scenes"].get("B")

    def v(note, gate, n, c):
        f0 = 440.0 * 2 ** ((note - 69 + cents / 100.0) / 12.0)
        t = np.arange(n) / SR
        out = np.zeros(n)
        rng = np.random.default_rng(note * 7 + n)
        if A:
            amp = surge._eg_curve(A["amp_eg"], n, gate) * p["level_tonal"] ** 3
            fr = A["frames"][-1]
            fr = fr / max(np.sqrt(np.sum(fr ** 2) / 2.0), 1e-12)
            uni = A.get("unison")
            dets = [(-uni["detune"], 1 / np.sqrt(2)), (uni["detune"], 1 / np.sqrt(2))] if uni else [(0.0, 1.0)]
            for d, g in dets:
                fu = f0 * 2 ** (d / 12.0)
                ph0 = rng.uniform(0, 2 * np.pi)
                for h in range(len(fr)):
                    if fu * (h + 1) >= SR / 2 or fr[h] <= 0:
                        continue
                    out += g * amp * fr[h] * np.sin(2 * np.pi * fu * (h + 1) * t + ph0 * (h + 1))
        if B:
            wh = B.get("wheel") or dict(level=0.0, cutoff=0.0)
            lvl = (B["level"] + wh["level"] * c) ** 3
            amp = surge._eg_curve(B["amp_eg"], n, gate) * lvl * 2.0
            w = rng.standard_normal(n)
            col = B["color"]
            if col != 0:
                w = lfilter([1, -0.9 * np.sign(col)], [1], w) * abs(col) + w * (1 - abs(col))
            cut = 440.0 * 2 ** ((B["cutoff"] + wh["cutoff"] * c) / 12.0)
            out += amp * norns._lpf_varying(w, cut)
        return out
    return v


def highpass(x, fc=250.0):
    from scipy.signal import butter, sosfilt
    return sosfilt(butter(4, fc / (SR / 2), "high", output="sos"), x)


def match_level(y, ref):
    """y at ref's loudness (rms over 250 Hz: the parts the patch plays)"""
    a = np.sqrt(np.mean(highpass(ref) ** 2))
    b = np.sqrt(np.mean(highpass(y[:len(ref)]) ** 2))
    return y * (a / max(b, 1e-12))
