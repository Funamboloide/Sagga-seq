# SPDX-License-Identifier: GPL-3.0-only
"""From a sound to its layers.

A sound (a note, a hit) is described as three layers that a synth can rebuild:
  tonal  the harmonics of the pitch: their amplitudes as they change in time (and how far each is from k x f0)
  noise  what is left when the harmonics are taken out: its spectrum in bands, as it changes in time
  shape  the envelope of each layer (attack, decay to a sustain level, release) fitted to what was measured

A stem (a longer file) is first cut where sounds begin; similar sounds are grouped and the clearest one of each group
is analysed: a stem gives one recipe per different sound in it (at most MAX_SOUNDS).

The result is a "recipe" (a dict, saved as JSON): what every target (Surge, the MDT, the M8, the Norns engine) is
made from. Nothing here depends on a target."""
import numpy as np

from .audio import SR

N_FFT = 4096                 # 93 ms: enough to tell the harmonics of a low note apart
HOP = 256                    # 5.8 ms between analysis frames
MAX_HARM = 96                # harmonics kept (fewer when they pass 18 kHz; a bass at 50 Hz: up to 4.8 kHz)
N_BANDS = 24                 # noise bands, log spaced
BAND_LO, BAND_HI = 40.0, 18000.0
MAX_SOUNDS = 8               # different sounds taken from one stem
F0_LO, F0_HI = 30.0, 2000.0

BAND_EDGES = np.geomspace(BAND_LO, BAND_HI, N_BANDS + 1)
BAND_CENTRES = np.sqrt(BAND_EDGES[:-1] * BAND_EDGES[1:])


# ------------------------------------------------------------------ small tools
def stft_mag(x):
    """magnitude frames (T, N_FFT/2+1), amplitude-calibrated: a sine of amplitude a reads ~a at its bin"""
    win = np.hanning(N_FFT).astype(np.float64)
    pad = np.concatenate([np.zeros(N_FFT // 2), x, np.zeros(N_FFT)])
    n = 1 + max(0, (len(pad) - N_FFT) // HOP)
    idx = np.arange(N_FFT)[None, :] + HOP * np.arange(n)[:, None]
    frames = pad[idx] * win[None, :]
    return np.abs(np.fft.rfft(frames, axis=1)) * (2.0 / win.sum())


def peak_amp(M, j):
    """the amplitude of the sine whose peak is at bins j (one per frame): a parabola through the log magnitudes of
    the bin and its neighbours (the Hann window loses up to 1.4 dB between bins)"""
    return peak_interp(M, j)[0]


def peak_interp(M, j):
    """(amplitude, exact bin) of the sine peaking at bins j: the parabola's top (a bin is 10.8 Hz: a note's
    frequency read from bins alone would be off by up to a third of a semitone at 100 Hz)"""
    T = M.shape[0]
    r = np.arange(T)
    j = np.clip(j, 1, M.shape[1] - 2)
    a, b, c = (np.log(np.maximum(M[r, j - 1], 1e-12)), np.log(np.maximum(M[r, j], 1e-12)), np.log(np.maximum(M[r, j + 1], 1e-12)))
    den = a - 2 * b + c
    d = np.where(np.abs(den) > 1e-12, 0.5 * (a - c) / np.where(np.abs(den) > 1e-12, den, 1.0), 0.0)
    d = np.clip(d, -0.5, 0.5)
    return np.exp(b - 0.25 * (a - c) * d), j + d


def frame_times(n):
    return np.arange(n) * HOP / SR


def rms_env(x, win=256):
    """RMS in windows of `win` samples centred on each HOP (a window of two periods of the note: no ripple)"""
    c = np.concatenate([[0.0], np.cumsum(np.asarray(x, dtype=np.float64) ** 2)])
    n = 1 + len(x) // HOP
    centre = np.arange(n) * HOP
    a = np.clip(centre - win // 2, 0, len(x))
    b = np.clip(centre + win // 2, 0, len(x))
    b = np.maximum(b, a + 1)
    return np.sqrt(np.maximum(c[np.minimum(b, len(x))] - c[a], 0.0) / (b - a))


def yin_f0(x, sr=SR, frame=2048, hop=512, thresh=0.15):
    """(f0 per frame or 0, aperiodicity per frame): the YIN method"""
    tau_min, tau_max = int(sr / F0_HI), min(int(sr / F0_LO), frame - 1)
    f0s, aps = [], []
    for start in range(0, max(1, len(x) - 2 * frame), hop):
        s = x[start:start + 2 * frame]
        if len(s) < 2 * frame:
            break
        if np.sqrt(np.mean(s * s)) < 1e-4:
            f0s.append(0.0); aps.append(1.0); continue
        # difference function via autocorrelation
        a = s[:frame]
        d = np.empty(tau_max + 1)
        d[0] = 0.0
        e0 = np.sum(a * a)
        cs = np.concatenate([[0.0], np.cumsum(s * s)])
        corr = np.fft.irfft(np.fft.rfft(s, 4 * frame) * np.conj(np.fft.rfft(a, 4 * frame)))[:tau_max + 1]
        for tau in range(1, tau_max + 1):
            d[tau] = e0 + (cs[tau + frame] - cs[tau]) - 2 * corr[tau]
        cmnd = np.ones_like(d)
        run = np.cumsum(d[1:])
        cmnd[1:] = d[1:] * np.arange(1, tau_max + 1) / np.maximum(run, 1e-12)
        tau = None
        for t in range(tau_min, tau_max):
            if cmnd[t] < thresh:
                while t + 1 < tau_max and cmnd[t + 1] < cmnd[t]:
                    t += 1
                tau = t
                break
        if tau is None:
            t = tau_min + int(np.argmin(cmnd[tau_min:tau_max]))
            f0s.append(0.0); aps.append(float(cmnd[t])); continue
        # parabolic refinement
        if 1 <= tau < tau_max:
            y0, y1, y2 = cmnd[tau - 1], cmnd[tau], cmnd[tau + 1]
            den = y0 - 2 * y1 + y2
            tau_f = tau + (0.5 * (y0 - y2) / den if abs(den) > 1e-12 else 0.0)
        else:
            tau_f = float(tau)
        f0s.append(sr / tau_f); aps.append(float(cmnd[tau]))
    return np.array(f0s), np.array(aps)


def hz_to_midi(f):
    return 69.0 + 12.0 * np.log2(f / 440.0)


# ------------------------------------------------------------------ envelopes
def fit_adsr(env, times):
    """attack / decay / sustain (0..1 of the peak) / release fitted to an amplitude envelope:
    a linear rise to the peak, then s + (1 - s) * exp(-(t - ta) / tau) to the end; the release is the fade of the
    last part (a sound that ends on its own: short)"""
    env = np.asarray(env, dtype=np.float64)
    if len(env) < 3 or env.max() <= 0:
        return dict(attack=0.002, decay=0.2, sustain=0.0, release=0.05, peak=0.0)
    peak = float(env.max())
    peak_i = int(np.nonzero(env >= 0.95 * peak)[0][0])           # (the first time it gets there: a held level is not a later peak)
    above = np.nonzero(env[:peak_i + 1] >= 0.1 * peak)[0]
    t0 = times[above[0]] if len(above) else 0.0
    attack = max(0.0005, float(times[peak_i] - t0))
    tail = env[peak_i:] / peak
    tt = times[peak_i:] - times[peak_i]
    if len(tail) < 4:
        return dict(attack=attack, decay=0.05, sustain=float(tail[-1]), release=0.02, peak=peak)
    best = (1e18, 0.0, 0.1)
    w = np.sqrt(np.maximum(tail, 1e-4))            # (the loud part counts more)
    for s in np.linspace(0.0, 0.95, 39):
        for tau in np.geomspace(0.003, 20.0, 60):
            m = s + (1 - s) * np.exp(-tt / tau)
            err = float(np.sum(w * (np.log(m + 1e-3) - np.log(tail + 1e-3)) ** 2))
            if err < best[0]:
                best = (err, s, tau)
    _, s, tau = best
    # the release: how fast the last 10 % fades from its level (a sound that stops: short)
    n_end = max(3, len(tail) // 10)
    end = tail[-n_end:]
    if end[0] > 1e-3 and end[-1] < end[0] * 0.5:
        release = float(tt[-1] - tt[-n_end]) / max(np.log(end[0] / max(end[-1], 1e-4)), 1e-3) * 2.0
    else:
        release = 0.05 if s < 0.05 else 0.3
    return dict(attack=attack, decay=float(tau), sustain=float(s), release=float(min(max(release, 0.01), 8.0)), peak=peak)


def find_modes(M, freqs, n_max=6):
    """the tones of an unpitched sound (a tom, a kick's body, a bell, a snare's shell): peaks of its first 150 ms
    that stand 12 dB over the spectrum around them, low to high"""
    early = M[: max(1, int(0.15 * SR / HOP))].mean(axis=0)
    db = 20 * np.log10(np.maximum(early, 1e-9))
    k = 24
    pad = np.concatenate([np.full(k, db[0]), db, np.full(k, db[-1])])
    med = np.array([np.median(pad[i:i + 2 * k + 1]) for i in range(len(db))])
    top = db.max()
    cand = [i for i in range(2, len(db) - 2) if freqs[i] > 30.0 and freqs[i] < 12000.0 and db[i] >= db[i - 1] and db[i] >= db[i + 1]
            and db[i] - med[i] > 12.0 and db[i] > top - 40.0]
    cand.sort(key=lambda i: -db[i])
    out = []
    for i in cand:
        a, b, c = early[i - 1], early[i], early[i + 1]
        la, lb, lc = np.log(max(a, 1e-12)), np.log(max(b, 1e-12)), np.log(max(c, 1e-12))
        den = la - 2 * lb + lc
        f = float((i + (0.5 * (la - lc) / den if abs(den) > 1e-12 else 0.0)) * SR / N_FFT)
        if all(abs(f - g) > 0.04 * g for g in out):
            out.append(f)
        if len(out) >= n_max:
            break
    return sorted(out)


def pitch_envelope(x, f0_hint=0.0):
    """a pitch that falls (a kick, a tom) or rises into its note: (the note's final Hz, semitones at the start,
    the decay in s) or None. The YIN track against its last voiced part, an exponential fitted to the offset."""
    n = min(len(x), int(1.5 * SR))
    frame, hop = (1024, 128) if 0 < f0_hint < 120.0 else (512, 64)   # (short windows: a sweep is fast)
    if n < 2 * frame + hop:
        return None
    f0s, aps = yin_f0(x[:n], frame=frame, hop=hop, thresh=0.2)
    f0s, aps = np.asarray(f0s), np.asarray(aps)
    t = (np.arange(len(f0s)) * hop + frame) / SR
    v = (f0s > 0) & (aps < 0.3)
    if f0_hint > 0:
        v &= (f0s > f0_hint / 4.5) & (f0s < f0_hint * 4.5)
    if v.sum() < 5:
        return None
    iv = np.nonzero(v)[0]
    tail = iv[-max(2, len(iv) * 2 // 5):]
    f_end = float(np.median(f0s[tail]))
    if f_end <= 0:
        return None
    s = np.where(v, 12 * np.log2(np.maximum(f0s, 1e-3) / f_end), 0.0)
    s0_raw = float(s[iv[0]])
    if abs(s0_raw) < 1.0:
        return None
    # the frames from the start while the offset keeps its sign and is still over a third of a semitone
    keep = []
    for i in iv:
        if np.sign(s[i]) != np.sign(s0_raw) or abs(s[i]) < 0.33:
            break
        keep.append(i)
    if len(keep) < 3:
        return None
    keep = np.array(keep)
    A = np.vstack([np.ones(len(keep)), -t[keep]]).T
    coef, _, _, _ = np.linalg.lstsq(A, np.log(np.abs(s[keep])), rcond=None)
    s0 = float(np.sign(s0_raw) * np.exp(coef[0]))
    tau = float(1.0 / max(coef[1], 1e-3))
    # the fit extrapolated to t = 0 (the track's first frame is already a window in); a pitch that steps (an
    # octave error at the start, a second note) or drifts over seconds is not an envelope: the curve must fit
    fit = s0 * np.exp(-t[keep] / tau)
    if abs(s0) < 1.0 or abs(s0) > 60.0 or tau > 1.0 or tau < 0.005 or np.mean(np.abs(s[keep] - fit)) > 0.25 * abs(s0):
        return None
    return dict(f_end=f_end, semitones=s0, decay=tau)


# ------------------------------------------------------------------ one sound
def analyse_sound(x, name="sound"):
    """the recipe of one sound (x: mono float at SR, starting at its onset)"""
    x = np.asarray(x, dtype=np.float64)
    x = x[:int(SR * 6.0)]                                   # (a sound longer than 6 s: its first 6 s)
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    if peak <= 1e-6:
        raise ValueError("silent")
    x = x / peak
    dur = len(x) / SR

    # the pitch: YIN on the body (after the first 30 ms of attack)
    body = x[int(0.03 * SR):int(min(dur, 1.5) * SR)] if dur > 0.08 else x
    f0s, aps = yin_f0(body)
    voiced = f0s[(f0s > 0) & (aps < 0.25)]
    conf = float(len(voiced) / max(1, len(f0s)))
    f0 = float(np.median(voiced)) if len(voiced) else 0.0
    pitched = f0 > 0 and conf >= 0.4
    pe = pitch_envelope(x, f0) if (pitched or conf >= 0.25) else None
    if pe:
        f0 = pe["f_end"]
        pitched = True

    M = stft_mag(x)
    T = M.shape[0]
    times = frame_times(T)
    freqs = np.fft.rfftfreq(N_FFT, 1.0 / SR)
    binhz = SR / N_FFT

    harm = np.zeros((T, 0))
    ratios = []
    resid = M.copy()
    modes = [] if pitched else find_modes(M, freqs)
    if modes:                                           # a drum's or a bell's tones: partials that are not harmonics
        f0 = modes[0]
        harm = np.zeros((T, len(modes)))
        for k, fm in enumerate(modes):
            j0 = int(round(fm / binhz))
            lo, hi = max(j0 - 2, 1), min(j0 + 3, M.shape[1] - 1)
            j = np.argmax(M[:, lo:hi], axis=1) + lo
            harm[:, k] = peak_amp(M, j)
            ratios.append(round(fm / f0, 4))
            for t in range(T):
                a, b = max(j[t] - 3, 0), min(j[t] + 4, M.shape[1])
                around = np.concatenate([M[t, max(a - 8, 0):a], M[t, b:b + 8]])
                resid[t, a:b] = np.minimum(resid[t, a:b], np.median(around) if len(around) else 0.0)
    if pitched:
        H = int(min(MAX_HARM, 18000.0 // max(f0 * (2 ** (max(pe["semitones"], 0) / 12) if pe else 1.0), 1.0)))
        harm = np.zeros((T, H))
        ratios = []
        # the pitch frame by frame: the note, or the envelope's curve into it
        f0_t = np.full(T, f0) if not pe else f0 * 2 ** (pe["semitones"] * np.exp(-times / pe["decay"]) / 12)
        # where the pitch moves within one STFT window (93 ms), a partial smears over many bins: its amplitude
        # is then the energy of the band it sweeps (a Hann main lobe holds 1.5 x the sine's a^2), not a peak
        half = N_FFT / (2.0 * SR)
        f_lo = f0 * 2 ** (pe["semitones"] * np.exp(-(times + half) / pe["decay"]) / 12) if pe else f0_t
        f_hi = f0 * 2 ** (pe["semitones"] * np.exp(-np.maximum(times - half, 0.0) / pe["decay"]) / 12) if pe else f0_t
        if pe and pe["semitones"] < 0:
            f_lo, f_hi = f_hi, f_lo
        swept = np.zeros(T, bool)
        for k in range(1, H + 1):
            if pe:
                # (a band never past the midpoints to the neighbouring harmonics at the window's centre)
                lo_t = np.clip((np.maximum(k * f_lo * 0.97, (k - 0.5) * f0_t) / binhz).astype(int), 1, M.shape[1] - 2)
                hi_t = np.clip(np.ceil(np.minimum(k * f_hi * 1.03, (k + 0.5) * f0_t) / binhz).astype(int) + 1, 2, M.shape[1] - 1)
                hi_t = np.maximum(hi_t, lo_t + 1)
                j = np.array([lo_t[t] + int(np.argmax(M[t, lo_t[t]:max(hi_t[t], lo_t[t] + 1)])) for t in range(T)])
                swept = (hi_t - lo_t) > 6
            else:
                fc = k * f0
                lo, hi = int(fc * 0.97 / binhz), int(np.ceil(fc * 1.03 / binhz)) + 1
                lo, hi = max(lo, 1), min(hi, M.shape[1] - 1)
                if hi <= lo:
                    continue
                seg = M[:, lo:hi]
                j = np.argmax(seg, axis=1) + lo
            harm[:, k - 1], jx = peak_interp(M, j)
            if swept.any():
                for t in np.nonzero(swept)[0]:
                    harm[t, k - 1] = np.sqrt(np.sum(M[t, lo_t[t]:hi_t[t]] ** 2) / 1.5)
                    jx[t] = k * f0_t[t] / binhz
            # the partial's frequency where it is loud (bells and strings are not exactly k x f0)
            loud = harm[:, k - 1] > 0.1 * harm[:, k - 1].max() if harm[:, k - 1].max() > 0 else None
            ratios.append(float(np.median(jx[loud] * binhz / f0_t[loud])) if loud is not None and loud.any() else float(k))
            # the harmonic out of the residual: its main lobe (+-3 bins, or the band it swept) down to the level around it
            for t in range(T):
                a, b = (max(j[t] - 3, 0), min(j[t] + 4, M.shape[1])) if not swept[t] else (lo_t[t], hi_t[t])
                floor = np.median(np.concatenate([M[t, max(a - 8, 0):a], M[t, b:b + 8]])) if b + 8 < M.shape[1] else M[t, a:b].min()
                resid[t, a:b] = np.minimum(resid[t, a:b], floor)
        # unvoiced start (the attack's noise) stays in the residual; harmonics under the noise are not harmonics
        nfloor = np.array([np.median(resid[t]) for t in range(T)])
        harm = np.where(harm > 2.0 * nfloor[:, None], harm, 0.0)

    # the noise in bands: the residual's rms per band (amplitude per bin)
    noise = np.zeros((T, N_BANDS))
    for b in range(N_BANDS):
        a, c = np.searchsorted(freqs, BAND_EDGES[b]), np.searchsorted(freqs, BAND_EDGES[b + 1])
        if c > a:
            noise[:, b] = np.sqrt(np.mean(resid[:, a:c] ** 2, axis=1))
    # energies: the harmonics' sum, and the noise's (a band's bins, all of them)
    widths = np.array([max(1, np.searchsorted(freqs, BAND_EDGES[b + 1]) - np.searchsorted(freqs, BAND_EDGES[b])) for b in range(N_BANDS)])
    tonal_env = np.sqrt(np.sum(harm ** 2, axis=1)) if harm.size else np.zeros(T)
    noise_env = np.sqrt(np.sum(noise ** 2 * widths[None, :], axis=1)) * 0.5
    tot = tonal_env.max() + noise_env.max() + 1e-12

    # the envelopes in time: the STFT smears them over 93 ms, so their shape comes from a 6 ms RMS, shared between
    # the layers as the STFT says (an attack of 3 ms reads as 3 ms)
    fine = rms_env(x, int(max(HOP, 2.0 * SR / f0)) if pitched else HOP)[:T] * np.sqrt(2.0)
    if len(fine) < T:
        fine = np.concatenate([fine, np.zeros(T - len(fine))])
    # the share of each layer, frame by frame, both measured in the same STFT (so smeared alike): a sine of
    # amplitude a has power a^2 / 2; the residual's power comes from its bins (Parseval, with the window's sums)
    win = np.hanning(N_FFT)
    tonal_p = np.sum(harm ** 2, axis=1) / 2.0 if harm.size else np.zeros(T)
    noise_p = np.sum(resid ** 2, axis=1) * win.sum() ** 2 / (2.0 * N_FFT * np.sum(win ** 2))
    share = np.clip(tonal_p / np.maximum(tonal_p + noise_p, 1e-18), 0.0, 1.0)
    tonal_env = fine * np.sqrt(share)
    noise_env = fine * np.sqrt(1.0 - share)
    tot = tonal_env.max() + noise_env.max() + 1e-12

    # the end of the sound: where both layers are 60 dB under their peaks (and never past the file)
    alive = np.nonzero((tonal_env > tonal_env.max() * 1e-3) | (noise_env > noise_env.max() * 1e-3))[0]
    T_end = int(alive[-1]) + 1 if len(alive) else T
    T_end = max(min(T_end, int(len(x) / HOP)), 4)
    harm, noise, tonal_env, noise_env, times = harm[:T_end], noise[:T_end], tonal_env[:T_end], noise_env[:T_end], times[:T_end]

    # the noise's colour over time: centroid (Hz) and tilt (dB per octave)
    cent = np.zeros(T_end)
    for t in range(T_end):
        p = noise[t] ** 2 * widths
        cent[t] = float(np.exp(np.sum(p * np.log(BAND_CENTRES)) / p.sum())) if p.sum() > 0 else 1000.0

    e_all = max(float(np.sum(tonal_env ** 2) + np.sum(noise_env ** 2)), 1e-18)     # (the layers' share of the energy)

    # the attack: the energy in the first 20 ms that neither layer explains (a click, a pick, a breath)
    n20 = int(0.02 * SR)
    tr_rms = float(np.sqrt(np.mean(x[:n20] ** 2)))

    rec = dict(
        version=1, name=name, sr=SR, hop=HOP, duration=float(T_end * HOP / SR),
        pitched=bool(pitched), f0=f0, confidence=conf,
        midi=float(hz_to_midi(f0)) if f0 > 0 and (pitched or modes) else None, modal=bool(modes),
        times=[round(float(t), 5) for t in times],
        harm=np.round(harm, 6).tolist(), ratios=[round(r, 4) for r in ratios],
        band_hz=[round(float(f), 1) for f in BAND_CENTRES], noise=np.round(noise, 6).tolist(),
        noise_centroid=[round(float(c), 1) for c in cent],
        tonal_env=np.round(tonal_env, 6).tolist(), noise_env=np.round(noise_env, 6).tolist(),
        mix=dict(tonal=float(np.sqrt(np.sum(tonal_env ** 2) / e_all)), noise=float(np.sqrt(np.sum(noise_env ** 2) / e_all))),
        adsr_tonal=fit_adsr(tonal_env, times) if (pitched or modes) else None,
        adsr_noise=fit_adsr(noise_env, times),
        transient_rms=tr_rms,
        pitch_env=dict(semitones=round(pe["semitones"], 2), decay=round(pe["decay"], 4)) if pe else None,
    )
    return rec


# ------------------------------------------------------------------ a stem: where sounds begin, which are different
def onsets(x):
    """sample positions where a sound begins: spectral flux, adaptive threshold, at least 60 ms apart"""
    n = 1024
    hop = 256
    win = np.hanning(n)
    if len(x) < n:
        return [0]
    idx = np.arange(n)[None, :] + hop * np.arange(1 + (len(x) - n) // hop)[:, None]
    S = np.log1p(100.0 * np.abs(np.fft.rfft(x[idx] * win, axis=1)))
    flux = np.concatenate([[0.0], np.sum(np.maximum(S[1:] - S[:-1], 0.0), axis=1)])
    k = 16
    med = np.array([np.median(flux[max(0, i - k):i + k + 1]) for i in range(len(flux))])
    thr = med + 0.3 * flux.std() + 1e-9
    # a sound begins where it gets louder: a click where a sound is cut off (to silence) is no beginning
    c = np.concatenate([[0.0], np.cumsum(np.asarray(x, dtype=np.float64) ** 2)])
    w = int(0.03 * SR)

    def louder(pos):
        a, b = max(pos - w, 0), min(pos + w, len(x))
        before = (c[pos] - c[a]) / max(pos - a, 1)
        after = (c[b] - c[pos]) / max(b - pos, 1)
        return after > 2.0 * before + 1e-12

    out, last = [], -10 ** 9
    for i in range(1, len(flux) - 1):
        if flux[i] > thr[i] and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1] and (i - last) * hop > 0.06 * SR \
                and louder(min(i * hop + hop, len(x))):
            out.append(max(0, i * hop - hop))
            last = i
    if not out or out[0] > 0.05 * SR and np.max(np.abs(x[:out[0]])) > 0.1 * np.max(np.abs(x)):
        out = [0] + out
    return out


def cut_sounds(x):
    """the sounds of a file: (start, end) pairs, each from an onset to the next (at most 4 s)"""
    on = onsets(x)
    segs = []
    for i, s in enumerate(on):
        e = on[i + 1] if i + 1 < len(on) else len(x)
        e = min(e, s + int(4.0 * SR))
        if e - s > int(0.04 * SR):
            segs.append((s, e))
    return segs or [(0, len(x))]


def sound_key(seg):
    """a coarse description to group alike sounds: (pitched, note, brightness in octaves, length in octaves)"""
    f0s, aps = yin_f0(seg[:int(0.5 * SR)])
    v = f0s[(f0s > 0) & (aps < 0.25)]
    note = float(hz_to_midi(np.median(v))) if len(v) >= max(2, len(f0s) // 3) else None
    m = min(8192, len(seg))
    spec = np.abs(np.fft.rfft(seg[:m] * np.hanning(m))) if m >= 64 else np.ones(10)
    fr = np.fft.rfftfreq(m, 1.0 / SR) if m >= 64 else np.linspace(0, SR / 2, 10)
    cent = float(np.sum(fr * spec) / max(spec.sum(), 1e-12))
    return (note is not None, note, float(np.log2(max(cent, 50.0))), float(np.log2(max(len(seg) / SR, 0.02))))


def alike(k1, k2):
    """the same sound played again: the same pitch (or both unpitched), brightness within half an octave,
    length within a factor of 1.6"""
    if k1[0] != k2[0]:
        return False
    if k1[0] and abs(k1[1] - k2[1]) > 0.5:
        return False
    return abs(k1[2] - k2[2]) < 0.5 and abs(k1[3] - k2[3]) < 0.7


def analyse_file(x, name="file"):
    """the recipes of a file: one for a one-shot, up to MAX_SOUNDS (the different ones) for a stem"""
    segs = cut_sounds(x)
    if len(segs) == 1:
        s, e = segs[0]
        rec = analyse_sound(x[s:e], name)
        rec["source"] = [int(s), int(e)]
        return [rec]
    groups = []                                         # [key of the first, (level, start, end) of the loudest]
    for s, e in segs:
        seg = x[s:e]
        k = sound_key(seg)
        lvl = float(np.max(np.abs(seg)))
        for g in groups:
            if alike(g[0], k):
                if lvl > g[1][0]:
                    g[1] = (lvl, s, e)
                break
        else:
            groups.append([k, (lvl, s, e)])
    best = sorted((g[1] for g in groups), key=lambda g: -g[0])[:MAX_SOUNDS]
    best.sort(key=lambda g: g[1])
    out = []
    for i, (_, s, e) in enumerate(best):
        try:
            rec = analyse_sound(x[s:e], "%s-%02d" % (name, i + 1))
            rec["source"] = [int(s), int(e)]            # (where in the file: the sound it is scored against)
            out.append(rec)
        except ValueError:
            pass
    return out
