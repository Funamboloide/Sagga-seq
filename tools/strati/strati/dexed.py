# SPDX-License-Identifier: GPL-3.0-only
"""The Dexed target (MicroDexed-touch, and the Dexed on Zynthian): a DX7 voice that plays a recipe's harmonic
profile, in a 32-voice bank (.syx) both load.

The voice is algorithm 5: three stacks of two operators (a carrier with a modulator on it). Each stack is a
simple FM spectrum (carrier at the note, modulator at 1, 2, 3 or 4 times it, an index): their sum is fitted to the
profile's harmonics (in dB). The first two stacks are detuned a little, one down and one up: the voice beats, as
a pad of two detuned oscillators does.

The units are the DX7's: an output level step is 0.75 dB, a modulator at 99 gives an index of about 4 pi (an
estimate; the sound to check on the instrument). Envelope rates come from Dexed's envelope code: the time a rate
takes over the full 96 dB range."""
import numpy as np
from scipy.special import jv

from .audio import SR

ALGO_3_STACKS = 4                   # (DX7 algorithm 5, 0-based in the file)
INDEX_AT_99 = 4 * np.pi
MOD_RATIOS = (1, 2, 3, 4)


# ------------------------------------------------------------------ FM spectra, the fit
def fm_harmonics(m, index, n_harm=16):
    """the magnitudes of harmonics 1..n_harm of sin(w t + I sin(m w t)) (carrier at the note, modulator at m x)"""
    amp = np.zeros(n_harm + 1)
    for n in range(-n_harm - 1, n_harm + 2):
        f = 1 + n * m
        a = jv(n, index)
        if f < 0:
            f, a = -f, -a                               # (a negative frequency folds over, its sign turned)
        if 1 <= f <= n_harm:
            amp[f] += a
    return np.abs(amp[1:])


def _model(params, ms, n_harm):
    """the power of each harmonic: the three stacks' powers added (they are detuned: they do not cancel)"""
    p = np.zeros(n_harm)
    for (lv, idx), m in zip(np.reshape(params, (3, 2)), ms):
        p += (abs(lv) * fm_harmonics(m, abs(idx), n_harm)) ** 2
    return p


def fit_profile(profile, n_harm=16, floor_db=-40.0):
    """three stacks' (level, index, modulator ratio) whose sum sounds like the profile: the least dB error over
    its harmonics (the louder ones weigh more), every combination of ratios tried"""
    from scipy.optimize import minimize
    h = np.zeros(n_harm)
    pr = np.asarray(profile, dtype=float)[:n_harm]
    h[:len(pr)] = pr
    h = h / max(h.max(), 1e-12)
    target = 20 * np.log10(np.maximum(h, 10 ** (floor_db / 20)))
    w = 1.0 + (target - floor_db) / -floor_db
    best = None
    combos = sorted({tuple(sorted(c)) for c in np.array(np.meshgrid(*[MOD_RATIOS] * 3)).T.reshape(-1, 3)})
    for ms in combos:
        def err(x):
            got = 10 * np.log10(np.maximum(_model(x, ms, n_harm), 10 ** (floor_db / 10)))
            got = got - got.max()
            return float(np.sum(w * (np.maximum(got, floor_db) - target) ** 2) / np.sum(w))
        for x0 in ([1.0, 1.0, 0.5, 1.5, 0.3, 2.5], [1.0, 0.3, 0.7, 2.0, 0.5, 0.8]):
            r = minimize(err, x0, method="Nelder-Mead", options=dict(maxiter=1500, xatol=1e-3, fatol=1e-4))
            if best is None or r.fun < best[0]:
                best = (r.fun, ms, np.abs(r.x))
    e, ms, x = best
    st = [dict(level=float(x[2 * j]), index=float(min(x[2 * j + 1], INDEX_AT_99)), mod_ratio=int(ms[j])) for j in range(3)]
    top = max(s["level"] for s in st)
    for s in st:
        s["level"] /= max(top, 1e-12)
    return st, float(np.sqrt(e))


# ------------------------------------------------------------------ DX7 units
def level_to_ol(a):
    """an amplitude (1 = full) as a DX7 output level (0..99; 0.75 dB a step)"""
    if a <= 0:
        return 0
    return int(np.clip(round(99 + 20.0 / 0.75 * np.log10(a)), 0, 99))


def ol_to_level(ol):
    return 0.0 if ol <= 0 else 10 ** (-(99 - ol) * 0.75 / 20.0)


def index_to_ol(index):
    return level_to_ol(index / INDEX_AT_99)


def rate_time(rate):
    """seconds a DX7 envelope rate takes over the full range (96 dB), from Dexed's env.cc (qrate = rate * 41 / 64;
    a step of (4 + qrate % 4) << (2 + 6 + qrate / 4) in 2^24 per 6 dB, each 64 samples)"""
    q = (int(rate) * 41) >> 6
    inc = (4 + (q & 3)) << (2 + 6 + (q >> 2))
    return (16 * (1 << 24)) / inc * 64 / SR


def time_to_rate(seconds, span_db=96.0):
    """the rate whose fall over span_db takes `seconds` (the nearest)"""
    best = min(range(100), key=lambda r: abs(np.log(max(rate_time(r) * span_db / 96.0, 1e-6)) - np.log(max(seconds, 1e-4))))
    return int(best)


def make_voice(rec, name=None):
    """a DX7 voice (a dict of the fields the bank holds) from a recipe: its first frames' harmonic profile when the
    sound is loudest, its attack and release"""
    H = np.asarray(rec["harm"])
    k = int(np.argmax(np.sum(H ** 2, axis=1))) if H.size else 0
    prof = H[k] / max(H[k].max(), 1e-12) if H.size else np.array([1.0])
    stacks, err = fit_profile(prof)
    a = rec.get("adsr_tonal") or {"attack": 0.01, "release": 0.3, "sustain": 1.0, "decay": 1.0}
    held = rec.get("held") or a.get("sustain", 0) > 0.5
    # the attack: Dexed rises in its log scale, faster at the top; a rise over the last 40 dB reads as the attack
    r1 = time_to_rate(a["attack"], 40.0)
    r4 = time_to_rate(a["release"], 60.0)
    if held:
        r2, r3, l2, l3 = 99, 99, 99, 99
    else:
        r2 = time_to_rate(a.get("decay", 0.5) * np.log(10.0) * 3, 60.0)
        l2 = level_to_ol(max(a.get("sustain", 0.0), 1e-4) ** 0.5) if a.get("sustain", 0) > 0.01 else 0
        r3, l3 = r2, l2
    ops = []
    det = (7 - 3, 7 + 3, 7)                             # (the first two stacks a little apart)
    for j, s in enumerate(stacks):
        car = dict(rates=[r1, r2, r3, r4], levels=[99, l2 if not held else 99, l3 if not held else 99, 0],
                   ol=level_to_ol(s["level"]), coarse=1, fine=0, detune=det[j])
        mod = dict(rates=[r1, r2, r3, r4], levels=[99, 99 if held else l2, 99 if held else l3, 0],
                   ol=index_to_ol(s["index"]), coarse=s["mod_ratio"], fine=0, detune=det[j])
        ops += [car, mod]                               # op1 car, op2 mod, op3 car, op4 mod, op5 car, op6 mod
    nm = (name or rec["name"]).upper()[:10]
    return dict(name=nm, algorithm=ALGO_3_STACKS, feedback=0, ops=ops, transpose=24, fit_db=err, stacks=stacks)


# ------------------------------------------------------------------ the bank file
def _pack_voice(v):
    b = bytearray(128)
    for i in range(6):                                  # (the file holds op6 first)
        op = v["ops"][5 - i]
        o = 17 * i
        b[o:o + 4] = bytes(op["rates"])
        b[o + 4:o + 8] = bytes(op["levels"])
        b[o + 8] = 39                                   # breakpoint C3, no level scaling
        b[o + 9] = 0
        b[o + 10] = 0
        b[o + 11] = 0
        b[o + 12] = (op["detune"] << 3) | 0             # rate scaling 0
        b[o + 13] = 0                                   # no velocity, no amp mod
        b[o + 14] = op["ol"]
        b[o + 15] = (op["coarse"] << 1) | 0             # ratio mode
        b[o + 16] = op["fine"]
    b[102:106] = bytes([99, 99, 99, 99])                # pitch EG: flat
    b[106:110] = bytes([50, 50, 50, 50])
    b[110] = v["algorithm"]
    b[111] = (1 << 3) | v["feedback"]                   # osc key sync on
    b[112:116] = bytes([35, 0, 0, 0])                   # LFO: speed, delay, no pitch or amp depth
    b[116] = (3 << 4) | (0 << 1) | 1                    # pitch mod sens 3, triangle, LFO key sync
    b[117] = v["transpose"]
    b[118:128] = v["name"].ljust(10)[:10].encode("ascii", "replace")
    return bytes(b)


INIT = dict(name="INIT VOICE", algorithm=0, feedback=0, transpose=24,
            ops=[dict(rates=[99, 99, 99, 99], levels=[99, 99, 99, 0], ol=99 if i == 0 else 0, coarse=1, fine=0, detune=7)
                 for i in range(6)])


def write_bank(voices, path):
    """a DX7 32-voice bulk dump: the voices, then INIT VOICEs"""
    data = b"".join(_pack_voice(voices[i] if i < len(voices) else INIT) for i in range(32))
    chk = (-sum(data)) & 0x7F
    with open(path, "wb") as f:
        f.write(bytes([0xF0, 0x43, 0x00, 0x09, 0x20, 0x00]) + data + bytes([chk, 0xF7]))


def read_bank(path):
    raw = open(path, "rb").read()
    assert raw[:6] == bytes([0xF0, 0x43, 0x00, 0x09, 0x20, 0x00]) and raw[-1] == 0xF7 and len(raw) == 4104
    data = raw[6:6 + 4096]
    assert ((-sum(data)) & 0x7F) == raw[4102], "checksum"
    out = []
    for i in range(32):
        b = data[128 * i:128 * (i + 1)]
        ops = []
        for j in range(6):
            o = 17 * (5 - j)
            ops.append(dict(rates=list(b[o:o + 4]), levels=list(b[o + 4:o + 8]), ol=b[o + 14], coarse=b[o + 15] >> 1,
                            fine=b[o + 16], detune=b[o + 12] >> 3))
        out.append(dict(name=b[118:128].decode("ascii", "replace"), algorithm=b[110], feedback=b[111] & 7,
                        transpose=b[117], ops=ops))
    return out


# ------------------------------------------------------------------ the model (for scoring and listening)
def _eg(op, n, gate):
    """an operator's envelope, linear in dB (as the DX7's), attack to L1 at R1, then L2 L3, release at R4"""
    t = np.arange(n) / SR
    lv = lambda l: -96.0 * (1.0 - l / 99.0)             # (a level step as dB, roughly)
    ta = rate_time(op["rates"][0]) * 40.0 / 96.0
    rel = rate_time(op["rates"][3])
    db = np.where(t < ta, -40.0 * (1.0 - t / max(ta, 1e-4)), lv(op["levels"][2]))
    at = float(np.interp(gate, t, db)) if gate < t[-1] else db[-1]
    db = np.where(t < gate, db, at - (t - gate) / max(rel, 1e-4) * 96.0)
    return np.where(db < -95.0, 0.0, 10 ** (db / 20.0))


def simulate(v, note, gate, dur, cents=0.0):
    """the voice played: three stacks, each sin(carrier + I sin(modulator)), detune ~1 cent a step (an estimate)"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    hz = 440.0 * 2 ** ((note - 69 + cents / 100.0) / 12.0)
    rng = np.random.default_rng(note)
    for j in range(3):
        car, mod = v["ops"][2 * j], v["ops"][2 * j + 1]
        f = hz * 2 ** ((car["detune"] - 7) * 1.0 / 1200.0)
        I = INDEX_AT_99 * ol_to_level(mod["ol"]) * _eg(mod, n, gate)
        ph = 2 * np.pi * f * t + rng.uniform(0, 2 * np.pi)
        out += ol_to_level(car["ol"]) * _eg(car, n, gate) * np.sin(ph + I * np.sin(mod["coarse"] * (ph - ph[0]) + rng.uniform(0, 6.28)))
    return out
