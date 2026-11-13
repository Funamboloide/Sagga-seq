# SPDX-License-Identifier: GPL-3.0-only
"""The Norns target: a recipe made small enough for a voice of the `strati` engine (norns/lib/Engine_Strati.sc),
the file the engine reads, and a model of that voice (for scoring, as for the other targets).

A voice is:
    24 sines: each at its own ratio of the note (harmonics, or a drum's modes), each with its own envelope
    24 noise bands: white noise through a band-pass (SuperCollider's BPF) per band, each with its own envelope
    every envelope: 12 levels at 12 times shared by all (from 0 to the sound's end, dense where it moves); the
    last level holds while the key is down, then a release
The sines follow the note played; the noise stays where it is (a snare's wires do not change with the note).

The file (<name>.strati, plain text, one item per line):
    strati 1
    name
    root note (midi, with cents)          release (s)
    11 segment times (s)
    24 ratios
    24 x 12 sine levels (the 1st sine's 12, then the 2nd's...)
    24 band centres (Hz)                    the bands' rq
    24 x 12 band gains (on SuperCollider's WhiteNoise, uniform -1..1, through BPF)
    (optional) noise RANGE_DB CUT_LO CUT_HI: the noise control (the mod wheel): at 0 the noise is RANGE_DB
        quieter and low-passed at CUT_LO, at 1 as in the file and low-passed at CUT_HI
"""
import numpy as np

from .analysis import BAND_EDGES, BAND_CENTRES, N_BANDS, N_FFT
from .audio import SR

N_SINES = 24
N_POINTS = 12
# the band-passes are half as wide as the bands (a constant fraction of an octave): their skirts overlap less, so
# a noise with peaks keeps them (scored on real sounds: 0.4 to 0.9 dB closer than as wide as the bands)
RQ = float((BAND_EDGES[1] - BAND_EDGES[0]) / BAND_CENTRES[0]) / 2.0


def _times(rec):
    """12 times from 0 to the end: 0, the loudest moment, then denser early (where sounds change) than late"""
    times = np.asarray(rec["times"])
    env = np.sqrt(np.asarray(rec["tonal_env"]) ** 2 + np.asarray(rec["noise_env"]) ** 2)
    end = float(times[-1]) if len(times) else rec["duration"]
    tp = float(times[int(np.argmax(env))]) if len(env) else 0.0
    tp = min(max(tp, 0.002), end * 0.5)
    rest = np.geomspace(tp, end, N_POINTS - 1)
    return np.concatenate([[0.0], rest])


def reduce(rec):
    """the voice's numbers from a recipe (a dict; write() puts it in a file, simulate() plays it)"""
    times = np.asarray(rec["times"])
    pts = _times(rec)
    out = dict(name=rec["name"], root=float(rec["midi"]) if rec.get("midi") else 60.0, release=0.0,
               seg=np.diff(pts).tolist(), ratios=[1.0] * N_SINES,
               sines=np.zeros((N_SINES, N_POINTS)), bands=BAND_CENTRES.tolist(), rq=RQ,
               gains=np.zeros((N_BANDS, N_POINTS)))
    # the sines: the spectrum's shape from the harmonics, the loudness from the fine envelope (no STFT smear)
    H = np.asarray(rec["harm"]) if rec["harm"] and len(rec["harm"][0]) else np.zeros((len(times), 0))
    if H.shape[1]:
        norm = np.sqrt(np.sum(H ** 2, axis=1))
        shape = H / np.maximum(norm[:, None], 1e-12)
        A = shape * np.asarray(rec["tonal_env"])[:, None]
        energy = np.sum(A ** 2, axis=0)
        ratios = rec.get("ratios") or list(range(1, H.shape[1] + 1))
        u = rec.get("unison_cents") or 0.0
        if u:
            # a voice of two detuned copies (as the pad was): the 12 strongest partials, each as two sines a
            # little under and over it, each with half the power
            keep = sorted(np.argsort(-energy)[:N_SINES // 2], key=lambda k: ratios[k])
            for i, k in enumerate(keep):
                for j, sgn in enumerate((-1.0, 1.0)):
                    out["ratios"][2 * i + j] = float(ratios[k] * 2 ** (sgn * u / 1200.0))
                    out["sines"][2 * i + j] = np.interp(pts, times, A[:, k]) / np.sqrt(2.0)
        else:
            keep = sorted(np.argsort(-energy)[:N_SINES], key=lambda k: ratios[k])
            for i, k in enumerate(keep):
                out["ratios"][i] = float(ratios[k])
                out["sines"][i] = np.interp(pts, times, A[:, k])
    # the noise: what each band's band-pass must give so that, all of them together (their skirts overlap), the
    # noise has the spectrum the STFT read. In the STFT's units (a white noise of variance v reads v * 6 / N per
    # bin, squared), WhiteNoise (variance 1/3) through BPF j with gain g reads g^2 |H_j(f)|^2 * 2 / N at bin f:
    # the bands' powers are a matrix times the gains squared, solved (never negative) at every point in time
    Nz = np.asarray(rec["noise"])
    if Nz.size and Nz.max() > 0:
        K, widths = _band_matrix(RQ)
        p_stft = np.sqrt(np.sum(Nz ** 2 * widths[None, :], axis=1) / 3.0)      # the noise's rms per the STFT
        want = np.asarray(rec["noise_env"]) / np.sqrt(2.0)                    # per the fine envelope
        scale = np.where(p_stft > 1e-9, want / np.maximum(p_stft, 1e-12), 0.0)
        from scipy.optimize import nnls
        for i, tp in enumerate(pts):
            m = np.array([np.interp(tp, times, Nz[:, b] * scale) for b in range(N_BANDS)])
            u, _ = nnls(K, widths * m ** 2)
            out["gains"][:, i] = np.sqrt(u)
    # the release: as fitted (a one-shot ends by itself; a held one fades this long)
    a = rec.get("adsr_tonal") or rec.get("adsr_noise") or {}
    out["release"] = float(min(max(a.get("release", 0.2), 0.02), 8.0))
    # a held sound with a noise control (a pad): the control's range, so the engine maps the mod wheel as here
    if rec.get("control") == "noise":
        from .pad import CTRL_RANGE_DB, CTRL_CUT
        out["control"] = [CTRL_RANGE_DB, CTRL_CUT[0], CTRL_CUT[1]]
    return out


_K = {}


def _band_matrix(rq):
    """K[b, j]: the power filter j's output (gain 1, on WhiteNoise) puts in band b, in the STFT's units"""
    if rq not in _K:
        freqs = np.fft.rfftfreq(N_FFT, 1.0 / SR)
        lo = np.searchsorted(freqs, BAND_EDGES[:-1]); hi = np.searchsorted(freqs, BAND_EDGES[1:])
        widths = np.maximum(1, hi - lo)
        z = np.exp(-1j * 2 * np.pi * freqs / SR)
        K = np.zeros((N_BANDS, N_BANDS))
        for j, fc in enumerate(BAND_CENTRES):
            b_, a_ = _bpf(fc, rq)
            H = (b_[0] + b_[1] * z + b_[2] * z * z) / (a_[0] + a_[1] * z + a_[2] * z * z)
            P = np.abs(H) ** 2 * 2.0 / N_FFT
            for b in range(N_BANDS):
                K[b, j] = P[lo[b]:max(hi[b], lo[b] + 1)].sum()
        _K[rq] = (K, widths)
    return _K[rq]


def _bpf(fc, rq):
    """SuperCollider's BPF as a biquad (RBJ band-pass, 0 dB at the centre; rq = bandwidth / centre)"""
    w0 = 2 * np.pi * min(fc, SR * 0.45) / SR
    alpha = np.sin(w0) * np.sinh(np.log(2) / 2 * _bw_oct(rq) * w0 / np.sin(w0))
    b_ = np.array([alpha, 0, -alpha]); a_ = np.array([1 + alpha, -2 * np.cos(w0), 1 - alpha])
    return b_ / a_[0], a_ / a_[0]


def write(red, path):
    f = lambda v: " ".join("%.6g" % float(x) for x in np.ravel(v))
    lines = ["strati 1", red["name"].replace("\n", " "), "%s %s" % (f([red["root"]]), f([red["release"]])),
             f(red["seg"]), f(red["ratios"]), f(red["sines"]), "%s %s" % (f(red["bands"]), f([red["rq"]])), f(red["gains"])]
    if red.get("control"):
        lines.append("noise " + f(red["control"]))
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")


def read(path):
    with open(path) as fh:
        L = fh.read().split("\n")
    nums = lambda s: [float(v) for v in s.split()]
    assert L[0] == "strati 1"
    root, rel = nums(L[2])
    b = nums(L[6])
    out = dict(name=L[1], root=root, release=rel, seg=nums(L[3]), ratios=nums(L[4]),
               sines=np.array(nums(L[5])).reshape(N_SINES, N_POINTS), bands=b[:N_BANDS], rq=b[N_BANDS],
               gains=np.array(nums(L[7])).reshape(N_BANDS, N_POINTS))
    if len(L) > 8 and L[8].startswith("noise "):
        out["control"] = nums(L[8][6:])
    return out


def simulate(red, note=None, dur=None, seed=5, gate=None, ctrl=None, parts=False):
    """the voice as the engine plays it: SinOsc per sine, BPF on WhiteNoise per band, linear envelopes; gate: when
    the key is let go (s; default: at the envelope's end), then the release; ctrl: the noise control (a value or
    a per-sample curve), for a sound that has one"""
    from scipy.signal import lfilter
    pts = np.concatenate([[0.0], np.cumsum(red["seg"])])
    gate = float(pts[-1]) if gate is None else gate
    dur = dur or (gate + red["release"])
    n = int(dur * SR)
    t = np.arange(n) / SR
    hz = 440.0 * 2 ** (((note if note is not None else red["root"]) - 69.0) / 12.0)
    rng = np.random.default_rng(seed)

    def env(levels):
        e = np.interp(t, pts, levels)
        if gate < dur:                                  # (EnvGen: from where it is, to 0 in the release time)
            at = float(np.interp(gate, pts, levels))
            e = np.where(t < gate, e, np.maximum(at * (1.0 - (t - gate) / max(red["release"], 1e-3)), 0.0))
        return e
    tonal = np.zeros(n)
    for r, lv in zip(red["ratios"], red["sines"]):
        if lv.max() <= 0 or hz * r >= 20000.0:
            continue
        tonal += env(lv) * np.sin(2 * np.pi * hz * r * t + rng.uniform(0, 2 * np.pi))
    noise = np.zeros(n)
    for fc, g in zip(red["bands"], red["gains"]):
        if g.max() <= 0:
            continue
        w = rng.uniform(-1.0, 1.0, n)
        b_, a_ = _bpf(fc, red["rq"])
        noise += env(g) * lfilter(b_, a_, w)
    if red.get("control") and ctrl is not None:
        rng_db, lo, hi = red["control"]
        c = np.clip(np.broadcast_to(np.asarray(ctrl, dtype=float), (n,)) if np.ndim(ctrl) == 0 else np.asarray(ctrl)[:n], 0, 1)
        gain = 10 ** (-(1.0 - c) * rng_db / 20.0)
        cut = lo * (hi / lo) ** c
        noise = _lpf_varying(noise, cut) * gain
    return (tonal, noise) if parts else tonal + noise


def _lpf_varying(x, cut, block=256):
    """SuperCollider's LPF (2nd-order Butterworth) with its cutoff moving (per block)"""
    from scipy.signal import lfilter
    y = np.zeros_like(x)
    zi = np.zeros(2)
    for s0 in range(0, len(x), block):
        fc = float(np.clip(cut[min(s0, len(cut) - 1)], 20.0, SR * 0.45))
        wc = np.tan(np.pi * fc / SR)
        k = np.sqrt(2.0)
        a0 = 1 + k * wc + wc * wc
        b_ = np.array([wc * wc, 2 * wc * wc, wc * wc]) / a0
        a_ = np.array([1.0, 2 * (wc * wc - 1) / a0, (1 - k * wc + wc * wc) / a0])
        y[s0:s0 + block], zi = lfilter(b_, a_, x[s0:s0 + block], zi=zi)
    return y


def _bw_oct(rq):
    """an rq (bandwidth / centre) as a bandwidth in octaves"""
    return 2 * np.arcsinh(rq / 2) / np.log(2)
