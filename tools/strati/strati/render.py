# SPDX-License-Identifier: GPL-3.0-only
"""A recipe played back (the reference: what the analysis heard, with no synth in between), and how far two sounds
are from each other. The Norns engine plays exactly this model; the other targets get as close as their synths go."""
import numpy as np

from .audio import SR
from .analysis import BAND_EDGES, N_BANDS, stft_mag, N_FFT, HOP


def _interp_frames(vals, times, n):
    """per-frame values -> per-sample curve of n samples"""
    t = np.arange(n) / SR
    return np.interp(t, np.asarray(times), np.asarray(vals), right=0.0)


def render(rec, f0=None, dur=None, seed=1):
    """the recipe as sound; f0: play it at another pitch (the harmonics follow, the noise stays)"""
    rng = np.random.default_rng(seed)
    times = np.asarray(rec["times"])
    n = int((dur or rec["duration"]) * SR) + HOP
    out = np.zeros(n)
    if rec["harm"] and len(rec["harm"][0]):
        H = np.asarray(rec["harm"])
        base = f0 or rec["f0"]
        ratios = rec.get("ratios") or list(range(1, H.shape[1] + 1))
        t = np.arange(n) / SR
        pe = rec.get("pitch_env")
        bend = 2 ** (pe["semitones"] * np.exp(-t / pe["decay"]) / 12) if pe else np.ones(n)   # (the pitch's curve)
        phase = 2 * np.pi * np.cumsum(bend) / SR
        for k in range(H.shape[1]):
            fk = base * (ratios[k] if k < len(ratios) else k + 1)
            if fk >= SR / 2 * 0.95 or H[:, k].max() <= 0:
                continue
            a = _interp_frames(H[:, k], times, n)
            out += a * np.sin(fk * phase + rng.uniform(0, 2 * np.pi))
    # the noise: white noise shaped band by band, frame by frame
    noise = np.asarray(rec["noise"])
    if noise.size and noise.max() > 0:
        win = np.hanning(N_FFT)
        freqs = np.fft.rfftfreq(N_FFT, 1.0 / SR)
        centres = np.sqrt(BAND_EDGES[:-1] * BAND_EDGES[1:])
        nf = len(times)
        buf = np.zeros(n + N_FFT)
        norm = np.zeros(n + N_FFT)
        for i in range(nf):
            shape = np.interp(np.log(np.maximum(freqs, 1.0)), np.log(centres), noise[i], left=0.0, right=0.0)
            spec = shape * np.exp(1j * rng.uniform(0, 2 * np.pi, len(freqs)))
            # a band's value is what stft_mag reads for noise: sigma * sqrt(6 / N) per bin (Hann); a frame of
            # random phases scaled by N / sqrt(6) has that sigma back, and frames that overlap add up to it when
            # the sum is divided by the root of the windows' squares (they are independent, their powers add)
            frame = np.fft.irfft(spec * (N_FFT / np.sqrt(6.0)), N_FFT) * win
            s = i * HOP - N_FFT // 2
            a, b = max(s, 0), min(s + N_FFT, len(buf))
            buf[a:b] += frame[a - s:b - s]
            norm[a:b] += win[a - s:b - s] ** 2
        out += (buf / np.sqrt(np.maximum(norm, 1e-3)))[:n]
    return out


def bands_db(x, n_bands=40):
    """a log-frequency spectrogram in dB (for comparing two sounds)"""
    M = stft_mag(np.asarray(x, dtype=np.float64))
    freqs = np.fft.rfftfreq(N_FFT, 1.0 / SR)
    edges = np.geomspace(40.0, 16000.0, n_bands + 1)
    out = np.zeros((M.shape[0], n_bands))
    for b in range(n_bands):
        a, c = np.searchsorted(freqs, edges[b]), max(np.searchsorted(freqs, edges[b + 1]), np.searchsorted(freqs, edges[b]) + 1)
        out[:, b] = np.sqrt(np.mean(M[:, a:c] ** 2, axis=1))
    return 20 * np.log10(np.maximum(out, 1e-5))


def distance(a, b):
    """how different two sounds are, in dB: the mean gap of their spectrograms (both at the same loudness, the
    louder parts weigh more). 0 is the same; ~3 is close; over ~10 another sound. (Same loudness: the same energy
    over the time both last; a peak would depend on the partials' phases, which the ear does not hear.)"""
    a = np.asarray(a, dtype=np.float64); b = np.asarray(b, dtype=np.float64)
    n = min(len(a), len(b))
    a = a / max(np.sqrt(np.mean(a[:n] ** 2)), 1e-12); b = b / max(np.sqrt(np.mean(b[:n] ** 2)), 1e-12)
    A, B = bands_db(a), bands_db(b)
    n = min(len(A), len(B))
    A, B = A[:n], B[:n]
    ref = np.maximum(A, B)
    w = np.clip((ref - ref.max() + 60.0) / 60.0, 0.0, 1.0)
    floor = ref.max() - 60.0
    gap = np.abs(np.maximum(A, floor) - np.maximum(B, floor))
    return float(np.sum(w * gap) / max(np.sum(w), 1e-9))
