# SPDX-License-Identifier: GPL-3.0-only
"""The Relitto target (the wavetable synth for the FM-1, 0.2 or later): a USER table baked from the recipe's
harmonics (16 frames, band-limited per octave, the engine's own format), the sound's parameters, the SysEx
that loads both into one of the FM-1's four USER slots, and the sound rendered by the real engine (Relitto's
host mode: the same integer code the chip runs), which is what the previews and the trial-and-error use.

How a recipe becomes a Relitto sound:
  pitched     OSC A = the USER table: frame 15 is the sound's start, frame 0 its end; ENV 2 sweeps the position
              from 15 down to 0 along its own decay (the frames are sampled where that curve puts them)
  drum, bell  the same table built on a fraction f0 / q of the pitch, so that the modes fall on harmonics
              (q picked for the least error in cents); the table's root offset puts the note back in tune
  noise layer OSC B = NOISE, its colour from the noise's centroid, its level following ENV 2 when the noise
              decays faster than the tone; a sound that is only noise plays it on OSC A, through the filter
  pad         frames all alike (its spectrum), two voices 10 cents apart (OSC B the same table, B FINE) or,
              when the noise matters, OSC B = NOISE on the mod wheel (level and colour)
Relitto's source is needed (tools/make_tables.py's table format, tests/host.c for the renders): STRATI_RELITTO
or a `relitto` folder next to the SAGGA SEQ repository."""
import hashlib
import math
import os
import shutil
import subprocess
import tempfile
import wave

import numpy as np

from .audio import SR

# ---- the engine's table format (tools/make_tables.py in Relitto: keep them the same)
FRAMES = 16
HARM = [127, 63, 31, 16, 8, 4, 2, 1]
LG = [9, 8, 7, 6, 6, 6, 6, 6]
NH = HARM[0]
WT_SIZE = FRAMES * sum(1 << lg for lg in LG)          # 19456 int16
WT_N = 8                                               # built-in tables
U_SLOTS = 4
TAB_USER, TAB_NOISE = WT_N, WT_N + U_SLOTS
U_CHUNK = 224
CTRL = SR / 32.0                                       # control steps a second

# ---- the parameters, in the engine's order (engine.c / relitto.c PD[]): name, max, default, CC
PARAMS = [
    ("A_TAB", TAB_NOISE, 0, 20), ("A_POS", 127, 85, 21), ("A_SEMI", 48, 24, 22), ("A_LVL", 127, 110, 23),
    ("B_TAB", TAB_NOISE, 0, 24), ("B_POS", 127, 85, 25), ("B_SEMI", 48, 24, 26), ("B_LVL", 127, 0, 27),
    ("F_MODE", 3, 0, 29), ("CUT", 127, 96, 74), ("RES", 127, 20, 71), ("DRIVE", 127, 0, 102),
    ("F_ENV", 127, 76, 30), ("F_KEY", 127, 64, 31), ("VEL_CUT", 127, 20, 116), ("AT_CUT", 127, 64, 114),
    ("E1A", 127, 8, 73), ("E1D", 127, 80, 75), ("E1S", 127, 100, 79), ("E1R", 127, 60, 72),
    ("E2A", 127, 0, 103), ("E2D", 127, 75, 104), ("E2S", 127, 40, 105), ("E2R", 127, 60, 106),
    ("L_RATE", 127, 70, 107), ("L_SHAPE", 4, 0, 108), ("L_PITCH", 127, 0, 111), ("L_CUT", 127, 64, 110),
    ("E2_POS", 127, 64, 112), ("L_POS", 127, 64, 109), ("MW_POS", 127, 100, 113), ("B_FINE", 100, 50, 28),
    ("BEND", 24, 2, 117), ("VEL_AMP", 127, 64, 115), ("VOL", 127, 100, 7), ("AT_POS", 127, 64, 118),
    ("E2_PITCH", 127, 64, 87), ("E2_BLVL", 127, 64, 88), ("MW_BLVL", 127, 64, 89),
]
NP = len(PARAMS)
PMAX = {n: m for n, m, d, c in PARAMS}
PDEF = {n: d for n, m, d, c in PARAMS}
MODE_LP, MODE_BP, MODE_HP, MODE_NOTCH = 0, 1, 2, 3


def defaults():
    return dict(PDEF)


# ---- units (as make_tables.py computes the engine's tables)
def time_param(seconds):
    """an envelope time (-60 dB, or the full rise) as the knob 0..127: 0.5 ms .. 12 s, log"""
    return int(np.clip(round(127 * math.log(max(seconds, 0.0005) / 0.0005) / math.log(24000)), 0, 127))


def param_time(p):
    return 0.0005 * 24000 ** (p / 127.0)


def noise_colour_param(hz):
    """POS of a NOISE oscillator: its one-pole low-pass at hz (150 Hz .. 20 kHz, log)"""
    return int(np.clip(round(127 * math.log(max(hz, 150.0) / 150.0) / math.log(20000 / 150)), 0, 127))


def cutoff_param(hz):
    """CUTOFF: MIDI note 16 .. 129 (20 Hz .. 14 kHz) over 0..127"""
    note = 69 + 12 * math.log2(max(hz, 20.0) / 440.0)
    return int(np.clip(round((note - 16) * 256 / 228.0), 0, 127))


def bipolar_param(x):
    """-1..1 -> 0..127 with 64 = 0"""
    return int(np.clip(round(64 + 64 * x), 0, 127))


def env2_curve(p, t):
    """ENV 2 (0..1) at times t (s) for a gate held throughout, as the engine runs it: a linear attack, then
    an exponential decay to the sustain (-60 dB of the way in the decay time)"""
    ta, td, s = param_time(p["E2A"]), param_time(p["E2D"]), p["E2S"] / 127.0
    e = np.where(t < ta, t / ta, s + (1 - s) * 0.001 ** ((t - ta) / td))
    return np.clip(e, 0.0, 1.0)


def position_curve(p, t):
    """the frame OSC A reads at times t (0..15), from A POS and ENV 2 > POS (the wheel and the LFO at rest)"""
    e = env2_curve(p, t)
    pos = p["A_POS"] * 15.0 / 127.0 + (p["E2_POS"] - 64) * 512 / 32768.0 * e * 15.0
    return np.clip(pos, 0.0, 15.0 - 1e-6)


# ---- the table
def spec_frames_from_amps(amps, harm_index, phases=None):
    """16 frames of harmonic amplitudes (16 x n) at harmonic numbers harm_index (1-based) -> complex spectra
    (NH each) with fixed phases (the same in every frame: the morph between frames is a clean crossfade)"""
    amps = np.asarray(amps, dtype=float)
    out = np.zeros((FRAMES, NH), complex)
    h = np.arange(1, NH + 1)
    if phases is None:
        phases = np.pi * h * (h - 1) / NH                 # Schroeder: a low peak for its loudness
    for k, hk in enumerate(harm_index):
        if 1 <= hk <= NH:
            out[:, hk - 1] += amps[:, k] * np.exp(1j * phases[hk - 1])
    return out


def _wave_of(c, n, nh):
    Y = np.zeros(n // 2 + 1, complex)
    Y[1:nh + 1] = -1j * c[:nh] * (n / 2)
    if nh == n // 2:
        Y[nh] = Y[nh].real
    return np.fft.irfft(Y, n)


def bake(frames):
    """complex spectra (16 x NH) -> the table as the engine reads it (int16[WT_SIZE]), and each frame's rms
    (level 0, after the baking: for the levels)"""
    frames = [c / max(np.abs(_wave_of(c, 4096, NH)).max(), 1e-9) if np.abs(c).max() > 0 else c for c in frames]
    levels = [[_wave_of(c, 1 << lg, nh) for c in frames] for lg, nh in zip(LG, HARM)]
    peak = max(np.abs(w).max() for lv in levels for w in lv)
    g = 32000 / max(peak, 1e-9)
    data = np.concatenate([np.round(w * g) for lv in levels for w in lv]).astype(np.int16)
    rms = np.array([np.sqrt(np.mean((w * g / 32768.0) ** 2)) for w in levels[0]])
    return data, rms


def pick_q(ratios, weights, q_max=8):
    """the fraction of the pitch the table is built on, so that modes at `ratios` fall on harmonics: the q
    with the least weighted error in cents; (q, the harmonic of each mode)"""
    best = None
    for q in range(1, q_max + 1):
        hs = [int(round(r * q)) for r in ratios]
        if any(h < 1 or h > NH for h in hs) or len(set(hs)) < len(hs):
            continue
        err = sum(w * abs(1200 * math.log2(h / (r * q))) for r, w, h in zip(ratios, weights, hs))
        err += 0.5 * q                                   # (a smaller q keeps more harmonics under Nyquist)
        if best is None or err < best[0]:
            best = (err, q, hs)
    if best is None:
        return 1, [max(1, min(NH, int(round(r)))) for r in ratios]
    return best[1], best[2]


# ---- recipe -> the sound
def plan(rec):
    """the sound: parameters (ints, by name), the table, its root offset, which source OSC B is, the note"""
    p = defaults()
    p["F_ENV"] = 64; p["VEL_CUT"] = 0; p["F_KEY"] = 0   # (the filter stays where it is put)
    p["E2_POS"] = 64; p["MW_POS"] = 64; p["CUT"] = 127; p["RES"] = 0
    times = np.asarray(rec["times"])
    H = np.asarray(rec["harm"]) if rec["harm"] and len(rec["harm"][0]) else np.zeros((len(times), 0))
    tonal = rec["mix"]["tonal"] > 0.05 and H.size > 0 and (rec["pitched"] or rec.get("modal"))
    noise_share = rec["mix"]["noise"]
    # a second oscillator for the noise when it is a real part of the sound (ENV 2 then serves it or the frames,
    # not both: a click at the start of a long tone is left to the table's first frame)
    noisy = noise_share > (0.3 if tonal else 0.08)
    if tonal and rec.get("pitch_env") and noise_share < 0.35:
        noisy = False                                     # (a sweep smears into the residual: not a noise)
    held = bool(rec.get("held"))
    midi = rec.get("midi") or 60.0
    note = int(round(midi))
    root = int(round((midi - note) * 256))
    out = dict(name=rec["name"][:12].upper(), note=note, b_source="none", notes=[])
    # the amp envelope
    a = rec.get("adsr_tonal") if tonal else rec.get("adsr_noise")
    a = a or dict(attack=0.01, decay=0.3, sustain=0.0, release=0.1)
    p["E1A"] = time_param(a["attack"])
    p["E1D"] = time_param(6.9 * a["decay"])
    p["E1S"] = int(np.clip(round(127 * a["sustain"]), 0, 127))
    p["E1R"] = time_param(3.5 * a["release"]) if (held or a["sustain"] > 0.05) else time_param(0.05)
    # ENV 2: the noise's decay when it has one of its own, else the tone's spread over the sound
    dur = float(rec["duration"])
    an = rec.get("adsr_noise") or a
    pe = rec.get("pitch_env") if tonal else None
    env2_for = "frames"
    if held:
        mode = "swell" if a["attack"] > 0.08 else "static"
    elif pe:
        mode = "decay"; t_env = 6.9 * pe["decay"]; env2_for = "pitch"   # (the pitch's fall rules ENV 2)
    elif noisy and tonal and an["decay"] < 0.6 * a["decay"]:
        mode = "decay"; t_env = 6.9 * an["decay"]; env2_for = "noise"
    else:
        mode = "decay"; t_env = 2.3 * dur                 # frame 1 at 90 % of the sound
    if mode == "decay":
        p["E2A"] = 0; p["E2D"] = time_param(t_env); p["E2S"] = 0; p["E2R"] = p["E1R"]
        if tonal:
            p["A_POS"] = 1; p["E2_POS"] = 127
    elif mode == "swell":
        p["E2A"] = time_param(a["attack"]); p["E2D"] = time_param(0.1); p["E2S"] = 127; p["E2R"] = p["E1R"]
        if tonal:
            p["A_POS"] = 127; p["E2_POS"] = 0
    else:
        p["E2A"] = 0; p["E2D"] = time_param(0.1); p["E2S"] = 127; p["E2R"] = p["E1R"]
        p["A_POS"] = 64; p["E2_POS"] = 64
    # the table: the harmonics sampled where ENV 2 puts each frame
    table, frame_rms, harm_index = None, None, None
    if tonal:
        p["A_TAB"] = TAB_USER                             # (the writer puts the slot in)
        ratios = rec.get("ratios") or list(range(1, H.shape[1] + 1))
        strength = np.sqrt(np.sum(H ** 2, axis=0))
        if rec.get("modal"):
            q, harm_index = pick_q(ratios, strength / max(strength.max(), 1e-12))
            root += int(round(-12 * math.log2(q) * 256))
            out["notes"].append("modes on harmonics %s of f0/%d" % (harm_index, q))
        else:
            harm_index = [max(1, int(round(r))) for r in ratios]
        if mode == "static":
            k = int(np.argmax(np.sum(H ** 2, axis=1)))
            amps = np.repeat(H[k][None, :], FRAMES, axis=0)
        else:
            grid = np.linspace(0.0, max(dur, 0.01), 2000)
            pos = position_curve(p, grid)
            amps = np.zeros((FRAMES, H.shape[1]))
            tf = np.zeros(FRAMES)
            top = int(np.argmax(pos))                 # (in both modes the position falls from 15: after the attack's dip)
            for f in range(FRAMES):                   # the moment the position passes each frame, on its way down
                hit = np.nonzero(pos[top:] <= f)[0] + top
                tf[f] = grid[hit[0]] if len(hit) else grid[-1]
            # each frame: the harmonics averaged over its own stretch of the sound (half way to the frames next
            # to it; one STFT frame at the least): a spike in one frame would ring for the whole stretch
            edges = np.concatenate([[max(tf[15], 0.0)], (tf[1:] + tf[:-1]) / 2.0, [max(tf[0], grid[-1])]])
            for f in range(FRAMES):
                a, b = min(edges[f], edges[f + 1]), max(edges[f], edges[f + 1])
                i0 = int(np.clip(np.searchsorted(times, a), 0, len(times) - 1))
                i1 = int(np.clip(np.searchsorted(times, b), i0 + 1, len(times)))
                amps[f] = H[i0:i1].mean(axis=0)
            amps[15] = H[:max(2, int(0.02 * SR / rec["hop"]))].max(axis=0) if mode == "decay" else amps[15]   # (the start: its peak, not a mean over silence)
            out["frame_times"] = tf
        spec = spec_frames_from_amps(amps, harm_index)
        table, frame_rms = bake(spec)
        out["frames_amps"] = amps
    # the levels: the layers' peaks (the recipe's envelopes are sums of amplitudes: rms = /sqrt 2), the table's
    # frames at full level, the NOISE source at a sine's rms (0.707), the engine's 0.3 a voice
    tonal_rms = (np.asarray(rec["tonal_env"]).max() / math.sqrt(2)) if tonal else 0.0
    noise_rms = (np.percentile(np.asarray(rec["noise_env"]), 95) / math.sqrt(2)) if noisy else 0.0   # (not a click's spike)
    if tonal:
        k = int(np.argmax(np.asarray(rec["tonal_env"])))
        t_peak = float(times[k]) if len(times) else 0.0
        f_peak = position_curve(p, np.array([t_peak]))[0] if mode != "static" else 8.0
        r = frame_rms[int(round(f_peak))] if frame_rms is not None else 0.5
        lvl_a = tonal_rms / max(r, 1e-6)
    else:
        lvl_a = 0.0
    lvl_n = noise_rms / 0.707
    top = max(lvl_a, lvl_n, 1e-9)
    scale = 127.0 / top                                   # (the louder layer at full: the 16-bit output's floor well down)
    p["VOL"] = 127
    p["A_LVL"] = int(np.clip(round(lvl_a * scale), 0, 127))
    nz = int(np.clip(round(lvl_n * scale), 0, 127))
    # the noise
    if noisy:
        Nz = np.asarray(rec["noise"])
        env = np.asarray(rec["noise_env"])
        loud = env > env.max() * 0.1
        cent = np.asarray(rec["noise_centroid"])
        c_early = float(np.median(cent[:max(3, len(cent) // 10)]))
        c_late = float(np.median(cent[loud][-max(3, loud.sum() // 3):])) if loud.any() else c_early
        avg = (Nz[loud] if loud.any() else Nz).mean(axis=0)
        if tonal:
            p["B_TAB"] = TAB_NOISE
            p["B_POS"] = noise_colour_param(max(c_early, c_late) * 1.5)
            p["B_LVL"] = nz
            out["b_source"] = "noise"
            if env2_for == "noise":
                p["E2_BLVL"] = 127                        # (the noise follows ENV 2: it goes first)
                out["notes"].append("noise on ENV 2 (decay %.0f ms)" % (1000 * an["decay"]))
        else:
            p["A_TAB"] = TAB_NOISE
            p["A_POS"] = noise_colour_param(max(c_early, c_late) * 1.5)
            p["A_LVL"] = nz
            p["E2_POS"] = 64
            out["b_source"] = "none"
            spread = float(np.sum(avg > avg.max() * 0.3)) / len(avg)
            if spread < 0.35:                               # a narrow noise: the filter as a band-pass on it
                p["F_MODE"] = MODE_BP; p["CUT"] = cutoff_param(c_late); p["RES"] = 60
            else:
                p["F_MODE"] = MODE_LP; p["CUT"] = cutoff_param(min(14000.0, c_late * 2.5)); p["RES"] = 10
            if c_early > c_late * 1.3:                      # it darkens: ENV 2 on the cutoff
                semis = 12 * math.log2(c_early / c_late)
                p["F_ENV"] = bipolar_param(min(semis, 96.0) / 96.0)
                p["E2_POS"] = 64
    # a pad: two voices a little apart (when OSC B is free), the noise on the wheel
    if rec.get("unison_cents") and out["b_source"] == "none" and tonal:
        p["B_TAB"] = TAB_USER                             # (the writer puts the slot in)
        p["B_POS"] = p["A_POS"]; p["B_LVL"] = p["A_LVL"]
        p["B_FINE"] = int(np.clip(round(50 + rec["unison_cents"]), 0, 100))
        out["b_source"] = "unison"
    if rec.get("control") == "noise" and out["b_source"] == "noise":
        from .pad import CTRL_RANGE_DB
        p["MW_BLVL"] = bipolar_param(1 - 10 ** (-CTRL_RANGE_DB / 20.0))   # wheel down: that much quieter
        p["MW_POS"] = 96                                  # (and darker: NOISE's colour follows the wheel)
        p["B_POS"] = max(0, p["B_POS"] - 24)
        out["notes"].append("mod wheel: the noise's level and colour")
    if pe and mode == "decay":
        p["E2_PITCH"] = bipolar_param(np.clip(pe["semitones"] / 48.0, -1, 1))
        out["notes"].append("pitch: %+.1f semitones falling in %.0f ms (ENV 2)" % (pe["semitones"], 1000 * pe["decay"]))
    out.update(params=p, table=table, root=int(np.clip(root, -32768, 32767)), mode=mode,
               gate=2.0 if held else max(0.05, dur))
    return out


# ---- the SysEx
def pack7(data):
    out, acc, nb = [], 0, 0
    for b in data:
        acc |= b << nb
        nb += 8
        while nb >= 7:
            out.append(acc & 0x7F)
            acc >>= 7
            nb -= 7
    if nb:
        out.append(acc & 0x7F)
    return bytes(out)


def put7(v, n):
    return bytes((v >> (7 * i)) & 0x7F for i in range(n))


def crc32(data):
    import zlib
    return zlib.crc32(bytes(data)) & 0xFFFFFFFF


HEAD = bytes([0xF0, 0x7D, 0x52, 0x4C])


def sysex_messages(pl, slot=0):
    """the messages that load the sound into USER slot `slot` (0..3): BEGIN, the table in 224-byte frames, END;
    a sound without a table (noise only) sends its parameters alone"""
    p = dict(pl["params"])
    if p["A_TAB"] < TAB_NOISE and pl.get("table") is not None:
        p["A_TAB"] = TAB_USER + slot
    if p["B_TAB"] == TAB_USER:
        p["B_TAB"] = TAB_USER + slot
    vals = bytes(int(np.clip(round(p[n]), 0, m)) for n, m, d, c in PARAMS)
    if pl.get("table") is None:
        return [HEAD + bytes([0x20, NP]) + vals + bytes([0xF7])]
    raw = np.asarray(pl["table"], dtype="<i2").tobytes()
    name = pl["name"].encode("ascii", "replace")[:12].ljust(12, b" ")
    name = bytes(b & 0x7F for b in name)
    msgs = [HEAD + bytes([0x01, slot]) + name + bytes([NP]) + vals + put7(pl["root"] + 32768, 3) + put7(len(raw), 3)
            + put7(crc32(raw), 5) + bytes([0xF7])]
    for i in range(0, len(raw), U_CHUNK):
        msgs.append(HEAD + bytes([0x02]) + put7(i // U_CHUNK, 2) + pack7(raw[i:i + U_CHUNK]) + bytes([0xF7]))
    msgs.append(HEAD + bytes([0x03, 0xF7]))
    return msgs


def write_syx(pl, path, slot=0):
    with open(path, "wb") as f:
        for m in sysex_messages(pl, slot):
            f.write(m)


def sheet(pl):
    """the sound as knob values, page by page (to dial it in by hand, or to read what strati did)"""
    p = pl["params"]
    names = {TAB_NOISE: "NOISE"}
    for u in range(U_SLOTS):
        names[TAB_USER + u] = "USER %d" % (u + 1)
    tab = lambda v: names.get(v, ["BASIC", "PULSE", "VOWEL", "COMB", "FOLD", "SYNC", "FM", "CHAOS"][v] if v < WT_N else str(v))
    bi = lambda v: "%+d" % (v - 64)
    ms = lambda v: "%.0f ms" % (1000 * param_time(v)) if param_time(v) < 1 else "%.2f s" % param_time(v)
    L = ["%s   (note %d, root %+.2f semitones, OSC B: %s)" % (pl["name"], pl["note"], pl["root"] / 256.0, pl["b_source"])]
    L += ["  " + n for n in pl.get("notes", [])]
    L.append("OSC A     TABLE %s  POS %d  SEMI %+d  LEVEL %d" % (tab(p["A_TAB"]), p["A_POS"], p["A_SEMI"] - 24, p["A_LVL"]))
    L.append("OSC B     TABLE %s  POS %d  SEMI %+d  LEVEL %d" % (tab(p["B_TAB"]), p["B_POS"], p["B_SEMI"] - 24, p["B_LVL"]))
    L.append("FILTER    MODE %s  CUTOFF %d  RESO %d  DRIVE %d" % (["LP", "BP", "HP", "NOTCH"][p["F_MODE"]], p["CUT"], p["RES"], p["DRIVE"]))
    L.append("FILT MOD  ENV2>CUT %s  KEYTRACK %d  VEL>CUT %d  AT>CUT %s" % (bi(p["F_ENV"]), p["F_KEY"], p["VEL_CUT"], bi(p["AT_CUT"])))
    L.append("AMP ENV   A %s  D %s  S %d  R %s" % (ms(p["E1A"]), ms(p["E1D"]), p["E1S"], ms(p["E1R"])))
    L.append("MOD ENV   A %s  D %s  S %d  R %s" % (ms(p["E2A"]), ms(p["E2D"]), p["E2S"], ms(p["E2R"])))
    L.append("POS MOD   ENV2>POS %s  LFO>POS %s  MW>POS %s  AT>POS %s" % (bi(p["E2_POS"]), bi(p["L_POS"]), bi(p["MW_POS"]), bi(p["AT_POS"])))
    L.append("MOD 2     ENV2>PIT %s  ENV2>B %s  MW>B %s  B FINE %+d" % (bi(p["E2_PITCH"]), bi(p["E2_BLVL"]), bi(p["MW_BLVL"]), p["B_FINE"] - 50))
    L.append("VOICE     BEND %d  VEL>AMP %d  VOLUME %d" % (p["BEND"], p["VEL_AMP"], p["VOL"]))
    return "\n".join(L) + "\n"


# ---- the real engine (Relitto's host mode)
def find_relitto():
    here = os.path.dirname(os.path.abspath(__file__))
    for c in (os.environ.get("STRATI_RELITTO"), os.path.join(here, "..", "..", "..", "..", "relitto"),
              os.path.join(here, "..", "relitto")):
        if c and os.path.isfile(os.path.join(c, "firmware", "src", "relitto.c")):
            return os.path.abspath(c)
    return None


_BIN = {}


def host_binary(relitto_dir=None, build_dir=None):
    """the host build of Relitto (compiled once per source version); None when the source or cc is missing"""
    rd = relitto_dir or find_relitto()
    if not rd:
        return None
    if rd in _BIN:
        return _BIN[rd]
    src = [os.path.join(rd, "firmware", "src", f) for f in ("relitto.c", "engine.c", "platform.c")] + \
          [os.path.join(rd, "tests", "host.c"), os.path.join(rd, "firmware", "gen", "relitto_wt.h")]
    h = hashlib.sha1()
    for f in src:
        if os.path.isfile(f):
            with open(f, "rb") as fh:
                h.update(fh.read())
    bd = build_dir or os.path.join(tempfile.gettempdir(), "strati-relitto")
    os.makedirs(bd, exist_ok=True)
    exe = os.path.join(bd, "relitto-" + h.hexdigest()[:12])
    if not os.path.isfile(exe):
        cmd = ["cc", "-O2", "-w", "-DDINGHY_HOST", '-DAPP_VER="strati"', "-I" + os.path.join(rd, "firmware", "src"),
               "-I" + os.path.join(rd, "firmware", "gen"), "-o", exe, os.path.join(rd, "firmware", "src", "relitto.c")]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError("relitto host build failed:\n" + r.stderr)
    _BIN[rd] = exe
    return exe


def script_text(events, syx_path=None, voices=8, end_ms=None):
    """a host script: the SysEx first (one message a millisecond), the voices, then events [(ms, status, d1, d2)]"""
    L = []
    if syx_path:
        L.append("0 syx %s" % syx_path)
    if voices != 4:                                       # GLO twice: SYSTEM; KNOB 1 = voices
        L += ["5 btn 7", "10 btn 7", "15 enc 2 %d" % (voices - 4), "20 btn 8"]
    for t, st, d1, d2 in sorted(events, key=lambda e: e[0]):
        L.append("%d midi 0x%02X %d %d" % (int(t), st, d1, d2))
    L.append("%d end" % int(end_ms if end_ms is not None else (max(e[0] for e in events) + 500 if events else 1000)))
    return "\n".join(L) + "\n"


def run_host(exe, script, syx_msgs=None, workdir=None):
    """runs the script (a text, with `SYX` standing for the SysEx file) -> mono float32 at SR, the host's log.
    Without a `workdir` the run has a folder of its own in the temporary files, and takes it away when it is done
    (until SAGGA SEQ 0.24's tree it stayed there: a WAV a render, hundreds a run of the tests, gigabytes in a few
    days - a full disk)"""
    wd = workdir or tempfile.mkdtemp(prefix="strati-rl-")
    try:
        syx = os.path.join(wd, "sound.syx")
        if syx_msgs:
            with open(syx, "wb") as f:
                for m in syx_msgs:
                    f.write(m)
        sp = os.path.join(wd, "script.txt")
        with open(sp, "w") as f:
            f.write(script.replace("SYX", syx))
        out = os.path.join(wd, "out")
        r = subprocess.run([exe, out, sp], capture_output=True, text=True, cwd=wd)
        if r.returncode:
            raise RuntimeError("relitto host run failed:\n" + r.stderr + r.stdout)
        with wave.open(out + ".wav", "rb") as w:
            raw = w.readframes(w.getnframes())
        y = np.frombuffer(raw, "<i2").astype(np.float32).reshape(-1, 2).mean(axis=1) / 32768.0
        return y, r.stdout
    finally:
        if not workdir:
            shutil.rmtree(wd, ignore_errors=True)


SX_MS = 260                                               # the SysEx takes ~180 ms of script time; the note after


def render(pl, exe, note=None, gate=None, dur=None, vel=127, slot=0, wheel=None, voices=4):
    """the sound played once by the real engine: note on at SX_MS, off after gate s; wheel: [(s, 0..1)]"""
    note = pl["note"] if note is None else note
    gate = gate if gate is not None else max(0.05, float(pl.get("gate", 1.0)))
    dur = dur if dur is not None else gate + 1.0
    ev = [(SX_MS, 0x90, note, vel), (SX_MS + int(gate * 1000), 0x80, note, 0)]
    for t, v in (wheel or []):
        ev.append((SX_MS + int(t * 1000) - 1, 0xB0, 1, int(np.clip(round(v * 127), 0, 127))))
    script = script_text(ev, "SYX", voices=voices, end_ms=SX_MS + int(dur * 1000))
    y, log = run_host(exe, script, sysex_messages(pl, slot))
    return y[int(SX_MS * SR / 1000):], log


def play_performance(pl, exe, perf, slot=0, voices=8, tail=1.5):
    """a performance (strati.pad: notes and the control curve) through the real engine"""
    ev = []
    for a, b, n in perf["notes"]:
        ev.append((SX_MS + int(a * 1000), 0x90, int(n), 110))
        ev.append((SX_MS + int(b * 1000) - 1, 0x80, int(n), 0))
    ct, cv = perf.get("ctrl_times", []), perf.get("ctrl", [])
    last = None
    for t in np.arange(0.0, perf["duration"], 0.05):
        v = int(np.clip(round(127 * np.interp(t, ct, cv)), 0, 127)) if len(ct) else 127
        if v != last:
            ev.append((SX_MS + int(t * 1000), 0xB0, 1, v))
            last = v
    script = script_text(ev, "SYX", voices=voices, end_ms=SX_MS + int((perf["duration"] + tail) * 1000))
    y, log = run_host(exe, script, sysex_messages(pl, slot))
    return y[int(SX_MS * SR / 1000):]


KNOBS = [                                                 # what the trial and error turns: (name, step)
    ("E1A", 8), ("E1D", 8), ("E1S", 16), ("E1R", 8), ("E2D", 8), ("A_LVL", 12), ("B_LVL", 12), ("B_POS", 12),
    ("CUT", 12), ("RES", 16), ("F_ENV", 12), ("E2_POS", 12), ("A_POS", 12), ("E2_PITCH", 8), ("DRIVE", 12),
]


def refine(pl, exe, target, budget=30.0, gate=None, log=None):
    """the sound's knobs nudged against the original, played by the real engine each time"""
    from .refine import refine as _refine
    from .render import distance
    p0 = {k: float(v) for k, v in pl["params"].items()}
    plan2 = dict(pl, params=p0)
    knobs = [(("params", n), float(s), 0.0, float(PMAX[n])) for n, s in KNOBS
             if not (n.startswith("B_") and pl["b_source"] == "none") and not (n == "E2_PITCH" and not pl.get("notes"))]
    n = len(target)

    def sim(q):
        qq = dict(q, params={k: int(round(v)) for k, v in q["params"].items()})
        y, _ = render(qq, exe, gate=gate, dur=n / SR + 0.05)
        return y[:n]
    best, score, start = _refine(plan2, target, sim, knobs, budget=budget, log=log)
    best["params"] = {k: int(round(v)) for k, v in best["params"].items()}
    return best, score, start
