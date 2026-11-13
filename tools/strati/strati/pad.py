# SPDX-License-Identifier: GPL-3.0-only
"""A pad (or any held, chordal part) out of a recording: which notes play when, the timbre of one voice (its
harmonics, its detune), how a voice swells, and the noise bed under it with its filter moving.

How: the spectrogram (long frames: a pad moves slowly) is explained as notes plus noise. Every note is the same
voice played at its pitch (one harmonic profile, shared: so a fifth's harmonics are not taken for notes of their
own), and the noise is 24 smooth bands. Notes and noise are solved frame by frame (never negative), then the
voice's profile from all the frames, and again (a few rounds). The tuning comes first: a record is rarely at 440.

The result is a dict (`analyse_pad`), from which `voice_recipe` makes an ordinary recipe of one held note (for the
patches) and `performance` the chords and the noise filter's curve (to play the patches as the original went)."""
import numpy as np
from scipy.optimize import nnls

from .audio import SR
from .analysis import BAND_EDGES, BAND_CENTRES, N_BANDS

N_FFT = 8192
HOP = 2048
F_MAX = 6000.0
N_HARM = 16


def _stft(x):
    w = np.hanning(N_FFT)
    n = 1 + max(0, (len(x) - N_FFT) // HOP)
    idx = np.arange(N_FFT)[None, :] + HOP * np.arange(n)[:, None]
    return np.abs(np.fft.rfft(x[idx] * w, axis=1)) * (2.0 / w.sum())


def tuning_cents(M, freqs):
    """the recording's tuning against A440, in cents (-50..50): the strong peaks' offsets from the semitones"""
    s = M.mean(axis=0)
    db = 20 * np.log10(np.maximum(s, 1e-12))
    pk = [i for i in range(3, len(s) - 3) if 80 < freqs[i] < 2000 and s[i] == s[i - 3:i + 4].max() and db[i] > db.max() - 35]
    if not pk:
        return 0.0
    pk = np.array(pk)
    # (the peak's exact bin: a parabola on the log magnitude)
    a, b, c = np.log(s[pk - 1]), np.log(s[pk]), np.log(s[pk + 1])
    d = 0.5 * (a - c) / np.where(np.abs(a - 2 * b + c) > 1e-12, a - 2 * b + c, 1.0)
    f = (pk + np.clip(d, -0.5, 0.5)) * SR / N_FFT
    cents = 1200 * np.log2(f / 440.0)
    off = np.mod(cents + 50, 100) - 50
    w = s[pk]
    ang = np.angle(np.sum(w * np.exp(2j * np.pi * off / 100)))
    return float(ang / (2 * np.pi) * 100)


def _kernel(freqs, fk, detune_frac):
    """a partial at fk as the STFT shows it: the window's main lobe, widened by the voice's detune"""
    df = SR / N_FFT
    sig = np.sqrt(0.55 ** 2 + (fk * detune_frac / df) ** 2)
    return np.exp(-0.5 * ((freqs - fk) / (sig * df)) ** 2)


def _noise_basis(freqs):
    """24 smooth bands (triangles in log frequency, overlapping): a noise's spectrum is a mix of them"""
    lf = np.log(np.maximum(freqs, 1.0))
    lc = np.log(BAND_CENTRES)
    step = lc[1] - lc[0]
    return np.clip(1.0 - np.abs(lf[:, None] - lc[None, :]) / step, 0.0, 1.0)


def _whiten(M, freqs, pct=50):
    """the spectrum over its own floor (a running median a third of an octave wide): peaks stand out, a noise
    bed reads ~1 wherever it is, loud or soft, bright or dark"""
    out = np.zeros_like(M)
    lf = np.log2(np.maximum(freqs, 1.0))
    # (the median window in bins grows with the frequency: done in a few octave slices)
    for lo_oct in np.arange(4.5, 14.5, 0.5):
        sel = (lf >= lo_oct) & (lf < lo_oct + 0.5)
        if not sel.any():
            continue
        idx = np.nonzero(sel)[0]
        width = max(5, int(round(freqs[idx[0]] * (2 ** (1 / 6) - 1) / (SR / N_FFT))) | 1)
        from scipy.ndimage import percentile_filter
        a, b = max(idx[0] - width, 0), min(idx[-1] + width + 1, M.shape[1])
        med = percentile_filter(M[:, a:b], pct, size=(1, width), mode='nearest')
        out[:, idx] = M[:, idx] / np.maximum(med[:, idx - a], 1e-9)
    return out


def _salience(P, freqs, f0, n_harm=12):
    """how much of a note is there: its harmonics' peaks (the strongest bin within 3 % of each), weighted down
    slowly with the harmonic number"""
    df = SR / N_FFT
    s = 0.0
    for k in range(1, n_harm + 1):
        fk = f0 * k
        if fk > F_MAX:
            break
        lo, hi = int(fk * 0.985 / df), int(np.ceil(fk * 1.015 / df)) + 1
        s += P[lo:hi].max() * 0.86 ** (k - 1)
    return s


def analyse_pad(x, note_lo=28, note_hi=90, split=52, max_notes=7, stop=0.25, log=None):
    """the notes frame by frame (the strongest, its harmonics taken out, the next...), the timbres of the voice
    under `split` (bass) and over it (pad), and the noise bed in 24 bands"""
    x = np.asarray(x, dtype=np.float64)
    x = x / max(np.max(np.abs(x)), 1e-9)
    M = _stft(x)
    freqs = np.fft.rfftfreq(N_FFT, 1.0 / SR)
    T = M.shape[0]
    cents = tuning_cents(M, freqs)
    notes = np.arange(note_lo, note_hi + 1)
    f0s = 440.0 * 2 ** ((notes - 69 + cents / 100.0) / 12.0)
    Wt = _whiten(M, freqs)
    P0 = np.maximum(Wt - 1.0, 0.0)                          # (what stands over the floor)
    df = SR / N_FFT
    A = np.zeros((len(notes), T))
    for t in range(T):
        P = P0[t].copy()
        first = None
        for _ in range(max_notes):
            sal = np.array([_salience(P, freqs, f) for f in f0s])
            i = int(np.argmax(sal))
            if sal[i] <= 0 or (first is not None and sal[i] < stop * first):
                break
            first = first or sal[i]
            A[i, t] = sal[i]
            # its harmonics out (spectral smoothness: a harmonic is taken down to the mean of its neighbours, so a
            # partial shared with another note keeps that note's share)
            amps = []
            for k in range(1, 13):
                fk = f0s[i] * k
                if fk > F_MAX:
                    break
                lo, hi = int(fk * 0.985 / df), int(np.ceil(fk * 1.015 / df)) + 1
                amps.append((lo, hi, P[lo:hi].max()))
            for j, (lo, hi, a) in enumerate(amps):
                nb = [amps[m][2] for m in (j - 1, j + 1) if 0 <= m < len(amps)]
                keep = min(a, np.mean(nb)) if (nb and j > 0) else 0.0
                P[lo - 1:hi + 1] = np.minimum(P[lo - 1:hi + 1], keep * 0.5)
    floor = M / np.maximum(Wt, 1e-9)
    # the noise bed: a low percentile of the spectrum (a chord's partials, many and close, lift a median; a quarter
    # of the bins are under the noise's own level almost always), scaled back to the noise's median (Rayleigh: the
    # 25th percentile is 0.644 of the median)
    nfloor = M / np.maximum(_whiten(M, freqs, pct=25), 1e-9) / 0.644
    noise = np.zeros((N_BANDS, T))
    for b in range(N_BANDS):
        a_, c_ = np.searchsorted(freqs, BAND_EDGES[b]), np.searchsorted(freqs, BAND_EDGES[b + 1])
        if c_ > a_:
            noise[b] = np.sqrt(np.mean(nfloor[:, a_:c_] ** 2, axis=1))
    times = (np.arange(T) * HOP + N_FFT / 2) / SR
    out = dict(cents=cents, times=times, noise=noise, band_hz=BAND_CENTRES, duration=len(x) / SR, voices={})
    above = np.maximum(M - floor, 0.0)                      # (a partial's own amplitude: what stands over the floor)
    for name, sel in (("bass", notes < split), ("pad", notes >= split)):
        v = dict(notes=notes[sel], f0s=f0s[sel], A=A[sel])
        v["profile"], v["level"] = _profile(above, freqs, v, piano_roll(v))
        out["voices"][name] = v
        if log:
            log('%s: profile %s' % (name, np.round(v["profile"][:8], 2)))
    return out


def _profile(M, freqs, v, roll, n_harm=N_HARM):
    """a voice's harmonics against its fundamental: the median, over every note it plays, of each harmonic's
    peak over the fundamental's, where no other note of the same moment has a partial within 3 % (M: the
    spectrum over its floor); and the median fundamental (the voice's loudness)"""
    df = SR / N_FFT
    ratios = [[] for _ in range(n_harm)]
    firsts = []                                             # (the fundamentals' amplitudes: the voice's level)
    for t in range(roll.shape[1]):
        act = np.nonzero(roll[:, t])[0]
        if not len(act):
            continue
        others = lambda i: [v["f0s"][j] for j in act if j != i]
        for i in act:
            f0 = v["f0s"][i]
            pk = lambda f: M[t, int(f * 0.99 / df):int(np.ceil(f * 1.01 / df)) + 1].max()
            a1 = pk(f0)
            if a1 <= 0:
                continue
            firsts.append(a1)
            for k in range(1, n_harm + 1):
                fk = f0 * k
                if fk > F_MAX:
                    break
                if any(abs(fk / (fo * m) - 1) < 0.03 for fo in others(i) for m in range(1, 16)):
                    continue
                ratios[k - 1].append(pk(fk) / a1)
    h = np.array([np.median(r) if len(r) >= 3 else 0.0 for r in ratios])
    h[0] = 1.0
    return h, (float(np.median(firsts)) if firsts else 0.0)


# ------------------------------------------------------------------ from the solution: chords, curves
def piano_roll(v, rel=0.25, smooth_s=0.5, min_frames=4):
    """which notes of a voice play in which frame: the notes' strengths averaged over half a second (a frame alone
    hears the noise too), and the strong ones against the moment's strongest, held for a while"""
    from scipy.ndimage import uniform_filter1d
    A = uniform_filter1d(v["A"], max(1, int(round(smooth_s * SR / HOP))), axis=1, mode='nearest')
    top = A.max(axis=0, keepdims=True)
    on = (A > rel * np.maximum(top, 1e-12)) & (top > 0.15 * A.max())
    # two notes a semitone apart in one pad chord are mostly one note heard twice (a detuned voice, a noisy
    # frame): the weaker goes
    for t in range(on.shape[1]):
        for i in np.argsort(-A[:, t]):
            if on[i, t]:
                for j in (i - 1, i + 1):
                    if 0 <= j < on.shape[0] and A[j, t] < A[i, t]:
                        on[j, t] = False
    out = on.copy()
    for i in range(on.shape[0]):                            # runs shorter than min_frames out
        row = on[i]
        t = 0
        while t < len(row):
            if row[t]:
                e = t
                while e < len(row) and row[e]:
                    e += 1
                if e - t < min_frames:
                    out[i, t:e] = False
                t = e
            else:
                t += 1
    return out


def chords(p, voice="pad", roll=None, min_s=1.5):
    """[(start s, end s, [notes])]: stretches where the same notes play; a stretch under min_s joins the
    neighbour it shares more notes with"""
    v = p["voices"][voice]
    roll = piano_roll(v) if roll is None else roll
    times = p["times"]
    hop = HOP / SR
    segs = []
    for t in range(roll.shape[1]):
        s = frozenset(int(n) for n in v["notes"][roll[:, t]])
        if segs and segs[-1][2] == s:
            segs[-1][1] = t
        else:
            segs.append([t, t, s])
    while len(segs) > 1:
        lens = [(b - a + 1) * hop for a, b, _ in segs]
        i = int(np.argmin(lens))
        if lens[i] >= min_s:
            break
        def share(j):
            return len(segs[i][2] & segs[j][2]) / max(1, len(segs[i][2] | segs[j][2])) if 0 <= j < len(segs) else -1
        j = i - 1 if share(i - 1) >= share(i + 1) else i + 1
        a, b = min(segs[i][0], segs[j][0]), max(segs[i][1], segs[j][1])
        keep = segs[j][2] if lens[j] >= lens[i] else segs[i][2]
        segs[min(i, j)] = [a, b, keep]
        del segs[max(i, j)]
        # (neighbours with the same notes become one)
        k = 0
        while k < len(segs) - 1:
            if segs[k][2] == segs[k + 1][2]:
                segs[k][1] = segs[k + 1][1]
                del segs[k + 1]
            else:
                k += 1
    return [(float(times[a] - hop / 2), float(times[b] + hop / 2), sorted(s)) for a, b, s in segs]


def noise_curve(p, f_lo=700.0):
    """the noise bed over time: its level and a low-pass cutoff (Hz) that best explains its shape above f_lo (under
    it, bass and drums share the floor) against its most open loud moment (a 2-pole low-pass, 300 Hz..16 kHz)"""
    Nz = p["noise"]                                         # (bands, T)
    sel = BAND_CENTRES >= f_lo
    level = np.sqrt(np.sum(Nz[sel] ** 2, axis=0))
    loud = level > 0.25 * level.max()
    cent = np.array([np.sum(Nz[sel, t] * BAND_CENTRES[sel]) / max(Nz[sel, t].sum(), 1e-12) for t in range(Nz.shape[1])])
    open_t = int(np.argmax(np.where(loud, cent, 0.0)))
    ref = np.median(Nz[sel][:, max(open_t - 2, 0):open_t + 3], axis=1) + 1e-12
    cands = np.geomspace(300.0, 16000.0, 100)
    lp = lambda fc: 1.0 / np.sqrt(1.0 + (BAND_CENTRES[sel] / fc) ** 4)
    cut = np.zeros(Nz.shape[1])
    for t in range(Nz.shape[1]):
        sv = Nz[sel, t] + 1e-12
        best = None
        for fc in cands:
            m = ref * lp(fc)
            g = np.exp(np.mean(np.log(sv) - np.log(m)))
            e = np.mean((np.log(sv) - np.log(g * m)) ** 2)
            if best is None or e < best[0]:
                best = (e, fc)
        cut[t] = best[1]
    from scipy.ndimage import median_filter
    cut = np.exp(median_filter(np.log(cut), size=7, mode='nearest'))
    return dict(times=p["times"], level=level, cutoff=cut, loud=loud, ref_shape=ref / ref.max(), open_t=open_t)


def voice_envelope(p, voice="pad", roll=None):
    """how a voice swells and fades: the median rise (10 -> 90 %) and fall of the notes' activations, in seconds"""
    v = p["voices"][voice]
    roll = piano_roll(v) if roll is None else roll
    A = v["A"]
    hop = HOP / SR
    rises, falls = [], []
    for i in range(A.shape[0]):
        row = roll[i]
        t = 0
        while t < len(row):
            if row[t]:
                e = t
                while e < len(row) and row[e]:
                    e += 1
                seg = A[i, max(t - 2, 0):min(e + 4, len(row))]
                pk = seg.max()
                if pk > 0 and e - t >= 4:
                    j10 = np.argmax(seg > 0.1 * pk); j90 = np.argmax(seg > 0.9 * pk)
                    rises.append(max(j90 - j10, 0) * hop)
                    after = seg[np.argmax(seg):]
                    j = np.argmax(after < 0.1 * pk) if (after < 0.1 * pk).any() else len(after)
                    falls.append(j * hop)
                t = e
            else:
                t += 1
    return dict(attack=float(np.median(rises)) if rises else 0.5, release=float(np.median(falls)) if falls else 1.0)


# ------------------------------------------------------------------ the pad as a patch, and how it was played
CTRL_RANGE_DB = 14.0                    # the noise control: from fully open (1) to this much quieter (0)
CTRL_CUT = (2500.0, 16000.0)            # ...and its low-pass from here (0) to here (1)


def noise_control(p, f_lo=700.0):
    """the noise bed's movement as one control 0..1 (1: as open and loud as it gets): its level above f_lo,
    against its loudest (the 95th percentile), over CTRL_RANGE_DB"""
    nc = noise_curve(p, f_lo)
    db = 20 * np.log10(np.maximum(nc["level"], 1e-9))
    top = np.percentile(db[nc["loud"]], 95) if nc["loud"].any() else db.max()
    from scipy.ndimage import uniform_filter1d
    c = np.clip(1.0 + (db - top) / CTRL_RANGE_DB, 0.0, 1.0)
    c = uniform_filter1d(c, max(1, int(round(0.5 * SR / HOP))), mode='nearest')
    return dict(times=p["times"], value=c, open_t=nc["open_t"])


def ctrl_gain_cut(c):
    """the noise's gain and low-pass cutoff (Hz) for a control value (the same in every target)"""
    c = np.clip(c, 0.0, 1.0)
    return 10 ** (-(1.0 - c) * CTRL_RANGE_DB / 20.0), CTRL_CUT[0] * (CTRL_CUT[1] / CTRL_CUT[0]) ** c


def voice_recipe(p, name="pad", voice="pad", attack=0.3, release=0.8, chord_size=4, unison_cents=10.0, f_hp=250.0):
    """one held note of the pad as an ordinary recipe (what every target is made from): its harmonics, its noise
    at the control's top (shared among a chord's notes), a swell in, a sustain, a fade out"""
    from .analysis import HOP as RHOP, N_FFT as RN_FFT
    v = p["voices"][voice]
    roll = piano_roll(v)
    played = v["notes"][roll.any(axis=1)]
    root = int(np.median(played)) if len(played) else 60
    f0 = 440.0 * 2 ** ((root - 69 + p["cents"] / 100.0) / 12.0)
    h = np.asarray(v["profile"], dtype=float)
    nh = int(min(len(h), 18000.0 // f0))
    amps = h[:nh] * v["level"]
    # the noise: its shape at the most open moment, at the control's top, above f_hp (under it the floor is the
    # bass and the drums'), in the recipe's units (per-bin amplitudes of a 4096-point frame: x sqrt(8192 / 4096))
    nc = noise_curve(p)
    t0 = nc["open_t"]
    ref = np.median(p["noise"][:, max(t0 - 3, 0):t0 + 4], axis=1) * np.sqrt(N_FFT / RN_FFT)
    ref = np.where(BAND_CENTRES >= f_hp, ref, ref * (BAND_CENTRES / f_hp) ** 2)
    ref = ref / np.sqrt(chord_size)
    dur = attack + 3.0
    T = int(dur * SR / RHOP)
    times = np.arange(T) * RHOP / SR
    env = np.clip(times / max(attack, 1e-3), 0.0, 1.0)
    harm = env[:, None] * amps[None, :]
    noise = env[:, None] * ref[None, :]
    tonal_env = env * np.sqrt(np.sum(amps ** 2))
    from .analysis import N_FFT as NF
    widths = np.array([max(1, np.searchsorted(np.fft.rfftfreq(NF, 1.0 / SR), BAND_EDGES[b + 1]) -
                          np.searchsorted(np.fft.rfftfreq(NF, 1.0 / SR), BAND_EDGES[b])) for b in range(N_BANDS)])
    noise_env = env * np.sqrt(np.sum(ref ** 2 * widths) / 3.0) * np.sqrt(2.0)
    et, en = float(np.sum(tonal_env ** 2)), float(np.sum(noise_env ** 2))
    adsr = dict(attack=attack, decay=1.0, sustain=1.0, release=release, peak=1.0)
    return dict(version=1, name=name, sr=SR, hop=RHOP, duration=float(dur), pitched=True, f0=float(f0), confidence=1.0,
                midi=float(root + p["cents"] / 100.0), modal=False, times=times.tolist(), harm=harm.tolist(),
                ratios=[float(k) for k in range(1, nh + 1)], band_hz=BAND_CENTRES.tolist(), noise=noise.tolist(),
                noise_centroid=[float(np.sum(ref * BAND_CENTRES) / max(ref.sum(), 1e-12))] * T,
                tonal_env=tonal_env.tolist(), noise_env=noise_env.tolist(),
                mix=dict(tonal=float(np.sqrt(et / max(et + en, 1e-18))), noise=float(np.sqrt(en / max(et + en, 1e-18)))),
                adsr_tonal=adsr, adsr_noise=dict(adsr), transient_rms=0.0, held=True, unison_cents=unison_cents,
                control="noise")


def performance(p, voice="pad"):
    """how the original played the pad: notes [(start s, end s, midi note)] and the noise control's curve"""
    ev = []
    for a, b, notes in chords(p, voice):
        for n in notes:
            ev.append((max(a, 0.0), b, int(n)))
    nc = noise_control(p)
    return dict(notes=ev, ctrl_times=nc["times"].tolist(), ctrl=nc["value"].tolist(), duration=p["duration"],
                cents=p["cents"])
