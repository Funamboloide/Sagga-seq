# SPDX-License-Identifier: GPL-3.0-only
"""A recipe as a Surge XT patch (.fxp): what Zynthian loads.

The two layers are Surge's two scenes, played together (scene mode DUAL):
  scene A  the tonal layer. A harmonic sound: a wavetable oscillator whose 16 frames are the harmonics at 16 moments
           of the sound; the Filter EG sweeps the morph through them, so the timbre moves as the original did. An
           unpitched sound with tones (a tom, a bell): its three strongest partials on three sine oscillators, each
           at its own pitch. The Amp EG is the layer's envelope.
  scene B  the noise layer: Surge's noise generator, coloured (Noise Color) and filtered (low or band pass) where
           the noise sat, the Filter EG moving the cutoff as the noise's colour moved; its own Amp EG.

The patch is made from Surge's own "Init Wavetable" (CC0) by changing its parameters, so every other setting is
Surge's default. The units are Surge's (read from its source): times are log2 seconds, cutoffs semitones from A440,
oscillator and mixer levels are cube roots of a gain, the Filter EG modulates the morph at depth 1 (0..1 = the
frames). `simulate()` is this module's own model of that patch (not Surge): it scores the mapping; the real
check is the patch played in Surge (on the Pi: `strati verify`)."""
import os
import re
import struct

import numpy as np

from .audio import SR
from .analysis import HOP, BAND_CENTRES

TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "surge_init_wavetable.fxp")
WT_FRAMES = 16
WT_SAMPLES = 2048
OT_SINE, OT_WAVETABLE = 1, 2
FUT_NONE, FUT_LP12, FUT_BP12 = 0, 1, 6
MS_FILTEREG = 16
SM_SINGLE, SM_DUAL = 0, 2
MS_MODWHEEL = 6


# ------------------------------------------------------------------ the file
def read_fxp(path):
    """(name, xml text, [6 wavetables as (n_samples, n_tables, flags, int16 array) or None], trailing bytes)"""
    d = open(path, "rb").read()
    if d[:4] != b"CcnK" or d[8:12] != b"FPCh":
        raise ValueError("not a Surge patch")
    name = d[28:56].split(b"\0")[0].decode("latin-1")
    c = d[60:]
    if c[:4] != b"sub3":
        raise ValueError("not a Surge sub3 patch")
    xmlsize = struct.unpack("<I", c[4:8])[0]
    wtsize = struct.unpack("<6I", c[8:32])
    xml = c[32:32 + xmlsize].decode("utf-8")
    p = 32 + xmlsize
    wts = []
    for size in wtsize:
        if not size:
            wts.append(None)
            continue
        ns, nt, fl = struct.unpack("<IHH", c[p + 4:p + 12])
        data = np.frombuffer(c[p + 12:p + size], dtype="<i2").copy()
        wts.append((ns, nt, fl, data))
        p += size
    return name, xml, wts, c[p:]


def write_fxp(path, name, xml, wts, trailing=b""):
    """the patch file: CcnK / FPCh header (big endian, as VST2 programs are), then sub3 + xml + wavetables"""
    body = bytearray(b"sub3")
    xb = xml.encode("utf-8")
    sizes = [0 if w is None else 12 + len(w[3]) * 2 for w in wts]
    body += struct.pack("<I", len(xb)) + struct.pack("<6I", *sizes) + xb
    for w in wts:
        if w is None:
            continue
        ns, nt, fl, data = w
        body += b"\0\0\0\0" + struct.pack("<IHH", ns, nt, fl | 4) + np.asarray(data, dtype="<i2").tobytes()
    body += trailing
    nm = name.encode("latin-1", "replace")[:27]
    head = b"FPCh" + struct.pack(">iii", 1, 0x63786533, 1) + struct.pack(">i", 1) + nm.ljust(28, b"\0") + struct.pack(">i", len(body))
    with open(path, "wb") as f:
        f.write(b"CcnK" + struct.pack(">i", len(head) + len(body)) + head + body)


def set_param(xml, name, value, modroute=None):
    """the value of parameter `name` (and, if given, one modulation routing (source, depth) on it)"""
    pat = re.compile(r'<%s ([^>]*?)(/>|>(.*?)</%s>)' % (re.escape(name), re.escape(name)), re.S)
    m = pat.search(xml)
    if not m:
        raise KeyError(name)
    attrs = m.group(1)
    v = "%d" % value if isinstance(value, (int, np.integer)) and not isinstance(value, bool) else "%.14f" % float(value)
    attrs = re.sub(r'value="[^"]*"', 'value="%s"' % v, attrs, count=1).rstrip()
    if modroute:
        src, depth = modroute
        el = '<%s %s><modrouting source="%d" depth="%.6f" muted="0" source_index="0" /></%s>' % (name, attrs, src, depth, name)
    else:
        el = '<%s %s />' % (name, attrs)
    return xml[:m.start()] + el + xml[m.end():]


def get_param(xml, name):
    m = re.search(r'<%s [^>]*value="([^"]*)"' % re.escape(name), xml)
    return float(m.group(1)) if m else None


# ------------------------------------------------------------------ recipe -> settings (physical units)
def _log2s(sec, lo=-8.0, hi=5.0):
    return float(np.clip(np.log2(max(sec, 1e-4)), lo, hi))


def _decay_param(adsr):
    """Surge's decay (shape 1: the level's square root falls linearly) set so it is 90 % of the way to the sustain
    when the measured exponential decay is"""
    s = adsr["sustain"]
    t90 = adsr["decay"] * np.log(10.0)
    l90 = s + 0.1 * (1.0 - s)
    td = t90 / max(1.0 - np.sqrt(l90), 1e-3)
    return _log2s(td)


def frames_from_recipe(rec, n_frames=WT_FRAMES):
    """the harmonic spectra of the wavetable frames, frame K-1 at the start of the sound and frame 0 at its end:
    frame k plays when the Filter EG (shape 1 decay, sustain 0, length Td) is at k / (K - 1)"""
    H = np.asarray(rec["harm"])
    times = np.asarray(rec["times"])
    td = max(min(rec["duration"], 6.0), 0.05)
    out = np.zeros((n_frames, H.shape[1]))
    for k in range(n_frames):
        v = k / (n_frames - 1)
        t = td * (1.0 - np.sqrt(v))
        i = int(np.clip(np.searchsorted(times, t), 0, len(times) - 1))
        lo, hi = max(0, i - 2), min(len(times), i + 3)
        out[k] = H[lo:hi].mean(axis=0)
    return out, td


def wavetable_from_frames(frames, n_samples=WT_SAMPLES):
    """single cycles (one per frame), each as loud as the others (the Amp EG makes the level); int16"""
    n_frames, nh = frames.shape
    ph = np.arange(n_samples) / n_samples
    rng = np.random.default_rng(7)
    phases = rng.uniform(0, 2 * np.pi, nh)            # (fixed per harmonic: the morph moves levels, not phases)
    phases[0] = 0.0
    cyc = np.zeros((n_frames, n_samples))
    for k in range(n_frames):
        for h in range(nh):
            if frames[k, h] > 0 and h + 1 < n_samples // 2:
                cyc[k] += frames[k, h] * np.sin(2 * np.pi * (h + 1) * ph + phases[h])
        r = np.sqrt(np.mean(cyc[k] ** 2))
        if r > 0:
            cyc[k] /= r
    peak = np.max(np.abs(cyc)) if np.max(np.abs(cyc)) > 0 else 1.0
    return np.round(cyc / peak * 32000).astype(np.int16), peak


def plan(rec):
    """the patch's settings in Surge's units, from a recipe (a dict any test can look at)"""
    p = dict(name=rec["name"][:27], scenes={})
    has_tonal = rec["mix"]["tonal"] > 0.05 and rec.get("adsr_tonal")
    # a pitched sound keeps its noise only when it is a real part of it (a breath, a pick, a hammer): under 0.15 it
    # is the analysis' leftover, and a second layer would only blur the patch
    has_noise = rec["mix"]["noise"] > (0.15 if rec["pitched"] and not rec.get("modal") else 0.08)
    midi = rec.get("midi") or 60.0
    p["root_note"] = int(round(midi))
    p["fine_semitones"] = float(midi - round(midi))
    if has_tonal:
        a = rec["adsr_tonal"]
        A = dict(amp_eg=dict(attack=_log2s(a["attack"]), decay=_decay_param(a), sustain=float(a["sustain"]),
                             release=_log2s(a["release"])))
        if rec.get("modal"):
            H = np.asarray(rec["harm"])
            strength = H.max(axis=0)
            top = sorted(np.argsort(-strength)[:3])
            A["kind"] = "modes"
            A["modes"] = [dict(semitones=float(12 * np.log2(rec["ratios"][k])) + p["fine_semitones"],
                               level=float(np.cbrt(strength[k] / strength.max()))) for k in top]
        else:
            frames, td = frames_from_recipe(rec)
            A["kind"] = "wavetable"
            A["frames"] = frames
            A["morph_eg"] = dict(attack=-8.0, decay=_log2s(td), sustain=0.0, release=_log2s(0.5))
        p["scenes"]["A"] = A
    if has_noise:
        a = rec["adsr_noise"]
        noise = np.asarray(rec["noise"])
        env = np.asarray(rec["noise_env"])
        loud = env > env.max() * 0.1
        cent = np.asarray(rec["noise_centroid"])
        c_early = float(np.median(cent[:max(3, int(0.03 * SR / HOP))]))
        c_late = float(np.median(cent[loud][-max(3, loud.sum() // 3):])) if loud.any() else c_early
        avg = (noise[loud] if loud.any() else noise).mean(axis=0)
        db = 20 * np.log10(np.maximum(avg, 1e-9))
        oct_ = np.log2(BAND_CENTRES)
        slope = float(np.polyfit(oct_, db, 1)[0])            # dB per octave of the noise's spectrum
        spread = float(np.sum(avg > avg.max() * 0.3)) / len(avg)
        ftype = FUT_BP12 if spread < 0.35 else FUT_LP12
        cut_hz = c_late if ftype == FUT_BP12 else min(18000.0, c_late * 2.5)
        envmod = float(np.clip(12 * np.log2(max(c_early, 30.0) / max(c_late, 30.0)), -96, 96))
        # the cutoff's movement takes about as long as the noise's own decay
        B = dict(amp_eg=dict(attack=_log2s(a["attack"]), decay=_decay_param(a), sustain=float(a["sustain"]),
                             release=_log2s(a["release"])),
                 color=float(np.clip(slope / 6.0, -1.0, 1.0)), filter_type=ftype,
                 cutoff=float(np.clip(12 * np.log2(cut_hz / 440.0), -60, 70)), envmod=envmod,
                 filter_eg=dict(attack=-8.0, decay=_decay_param(dict(sustain=0.0, decay=a["decay"])), sustain=0.0, release=-2.0))
        p["scenes"]["B"] = B
    # the layers' balance: the measured peaks, as Surge's cube-root levels (the noise generator is about twice as
    # loud as a full-scale wavetable cycle of the same RMS; NOISE_TRIM is that guess, checked by `strati verify`)
    NOISE_TRIM = 0.5
    t, n = rec["mix"]["tonal"], rec["mix"]["noise"]
    big = max(t, n * NOISE_TRIM, 1e-9)
    p["level_tonal"] = float(np.cbrt(t / big)) if has_tonal else 0.0
    if has_noise:
        p["scenes"]["B"]["level"] = float(np.cbrt(n * NOISE_TRIM / big))
    # a pad: two detuned voices per note, and the noise on the mod wheel (down: quieter and darker)
    if has_tonal and rec.get("unison_cents") and p["scenes"]["A"]["kind"] == "wavetable":
        p["scenes"]["A"]["unison"] = dict(voices=2, detune=float(rec["unison_cents"]) / 100.0)
    if has_noise and rec.get("control") == "noise":
        from .pad import CTRL_RANGE_DB, CTRL_CUT
        B = p["scenes"]["B"]
        B["filter_type"] = FUT_LP12
        top = B["level"]
        low = top * 10 ** (-CTRL_RANGE_DB / 60.0)       # (the level is a cube root: -14 dB is a third of it)
        B["level"] = float(low)
        B["cutoff"] = float(12 * np.log2(CTRL_CUT[0] / 440.0))
        B["envmod"] = 0.0
        B["wheel"] = dict(level=float(top - low), cutoff=float(12 * np.log2(CTRL_CUT[1] / CTRL_CUT[0])))
        B["amp_eg"] = dict(A["amp_eg"]) if has_tonal else B["amp_eg"]
    return p


# ------------------------------------------------------------------ settings -> the patch
def build_xml_and_tables(p, template=TEMPLATE):
    name, xml, wts, trail = read_fxp(template)
    wts = list(wts)
    A, B = p["scenes"].get("A"), p["scenes"].get("B")
    xml = re.sub(r'<meta name="[^"]*" category="[^"]*" comment="[^"]*" author="[^"]*"',
                 '<meta name="%s" category="STRATI" comment="made by strati from a sample" author="strati"' % p["name"].replace('"', "'"),
                 xml, count=1)
    both = bool(A and B)
    xml = set_param(xml, "scenemode", SM_DUAL if both else SM_SINGLE)
    scenes = []
    if A:
        scenes.append(("a", A, "tonal"))
    if B:
        scenes.append(("b" if A else "a", B, "noise"))
    for sc, S, kind in scenes:
        x = sc + "_"
        for i in (1, 2, 3):
            xml = set_param(xml, x + "mute_o%d" % i, 1)
        xml = set_param(xml, x + "mute_noise", 1)
        xml = set_param(xml, x + "filter1_type", FUT_NONE)
        xml = set_param(xml, x + "filter2_type", FUT_NONE)
        eg = S["amp_eg"]
        for k, v in (("attack", eg["attack"]), ("decay", eg["decay"]), ("sustain", eg["sustain"]), ("release", eg["release"])):
            xml = set_param(xml, x + "env2_" + k, v)
        if kind == "tonal" and S["kind"] == "wavetable":
            xml = set_param(xml, x + "osc1_type", OT_WAVETABLE)
            xml = set_param(xml, x + "mute_o1", 0)
            xml = set_param(xml, x + "level_o1", p["level_tonal"])
            xml = set_param(xml, x + "osc1_pitch", p["fine_semitones"])
            xml = set_param(xml, x + "osc1_param0", 0.0, modroute=(MS_FILTEREG, 1.0))
            if S.get("unison"):
                xml = set_param(xml, x + "osc1_param5", S["unison"]["detune"])
                xml = set_param(xml, x + "osc1_param6", S["unison"]["voices"])
            me = S["morph_eg"]
            for k, v in (("attack", me["attack"]), ("decay", me["decay"]), ("sustain", me["sustain"]), ("release", me["release"])):
                xml = set_param(xml, x + "env1_" + k, v)
            table, _ = wavetable_from_frames(S["frames"])
            wts[0 if sc == "a" else 3] = (WT_SAMPLES, WT_FRAMES, 4, table.reshape(-1))
            xml = re.sub(r'(<osc_extra_sc%d_osc0 [^>]*wavetable_display_name=")[^"]*"' % (0 if sc == "a" else 1),
                         r'\g<1>%s"' % p["name"][:20].replace('"', "'"), xml, count=1)
        elif kind == "tonal":
            for i, m in enumerate(S["modes"][:3], 1):
                xml = set_param(xml, x + "osc%d_type" % i, OT_SINE)
                xml = set_param(xml, x + "mute_o%d" % i, 0)
                xml = set_param(xml, x + "osc%d_pitch" % i, m["semitones"])
                xml = set_param(xml, x + "level_o%d" % i, m["level"] * p["level_tonal"])
        else:
            xml = set_param(xml, x + "mute_noise", 0)
            wh = S.get("wheel")
            xml = set_param(xml, x + "level_noise", S["level"], modroute=(MS_MODWHEEL, wh["level"]) if wh else None)
            xml = set_param(xml, x + "noisecol", S["color"])
            xml = set_param(xml, x + "filter1_type", S["filter_type"])
            xml = set_param(xml, x + "filter1_cutoff", S["cutoff"], modroute=(MS_MODWHEEL, wh["cutoff"]) if wh else None)
            xml = set_param(xml, x + "filter1_envmod", S["envmod"])
            fe = S["filter_eg"]
            for k, v in (("attack", fe["attack"]), ("decay", fe["decay"]), ("sustain", fe["sustain"]), ("release", fe["release"])):
                xml = set_param(xml, x + "env1_" + k, v)
    # oscillators that are not wavetables carry no table (Surge writes none for them)
    for idx, (sc, i) in enumerate([(s, o) for s in "ab" for o in (1, 2, 3)]):
        if int(get_param(xml, "%s_osc%d_type" % (sc, i))) != OT_WAVETABLE:
            wts[idx] = None
    return xml, wts, trail


def write_patch(rec, path, template=TEMPLATE):
    p = plan(rec)
    xml, wts, trail = build_xml_and_tables(p, template)
    write_fxp(path, p["name"], xml, wts, trail)
    return p


# ------------------------------------------------------------------ the model of the patch (a score, not Surge)
def _eg_curve(eg, n, gate_s):
    """Surge's ADSR (attack linear, decay with shape 1, release linear) sampled per sample, the gate held gate_s"""
    a, d, r = 2.0 ** eg["attack"], 2.0 ** eg["decay"], 2.0 ** eg["release"]
    s = eg["sustain"]
    t = np.arange(n) / SR
    out = np.where(t < a, t / a, 0.0)
    td = t - a
    dec = np.maximum(1.0 - td / d, np.sqrt(s)) ** 2
    out = np.where(t >= a, dec, out)
    held = t < gate_s
    at_off = np.interp(gate_s, t, out) if gate_s < t[-1] else out[-1]
    rel = np.maximum(at_off - (t - gate_s) / r * 1.0, 0.0)
    return np.where(held, out, rel)


def simulate(p, f0, dur):
    """an approximation of the patch's sound (this module's model of Surge's parts), for scoring the mapping"""
    n = int(dur * SR)
    out = np.zeros(n)
    t = np.arange(n) / SR
    rng = np.random.default_rng(3)
    A, B = p["scenes"].get("A"), p["scenes"].get("B")
    if A:
        amp = _eg_curve(A["amp_eg"], n, dur) * p["level_tonal"] ** 3
        if A["kind"] == "wavetable":
            pos = _eg_curve(A["morph_eg"], n, dur) * (WT_FRAMES - 1)
            fr = A["frames"]
            norm = np.sqrt(np.sum(fr ** 2, axis=1) / 2.0)
            fr = fr / np.maximum(norm[:, None], 1e-12)
            lo = np.floor(pos).astype(int); hi = np.minimum(lo + 1, WT_FRAMES - 1); w = pos - lo
            for h in range(fr.shape[1]):
                if f0 * (h + 1) >= SR / 2:
                    break
                a_h = fr[lo, h] * (1 - w) + fr[hi, h] * w
                out += amp * a_h * np.sin(2 * np.pi * f0 * (h + 1) * t)
        else:
            for m in A["modes"]:
                out += amp * m["level"] ** 3 * np.sin(2 * np.pi * f0 * 2 ** ((m["semitones"] - p["fine_semitones"]) / 12) * t)
    if B:
        from scipy.signal import lfilter
        amp = _eg_curve(B["amp_eg"], n, dur) * B["level"] ** 3 * 2.0
        w = rng.standard_normal(n)
        c = B["color"]
        if c != 0:                                          # a first-order tilt: brighter or darker
            w = lfilter([1, -0.9 * np.sign(c)], [1], w) * abs(c) + w * (1 - abs(c))
        feg = _eg_curve(B["filter_eg"], n, dur)
        y = np.zeros(n)
        blk = 64
        zi = np.zeros(2)
        for s0 in range(0, n, blk):
            fc = 440.0 * 2 ** ((B["cutoff"] + B["envmod"] * feg[s0]) / 12.0)
            fc = min(max(fc, 20.0), SR * 0.45)
            wc = np.tan(np.pi * fc / SR); q = 0.707
            k = 1 / q
            a0 = 1 + k * wc + wc * wc
            if B["filter_type"] == FUT_BP12:
                b_ = np.array([k * wc, 0, -k * wc]) / a0
            else:
                b_ = np.array([wc * wc, 2 * wc * wc, wc * wc]) / a0
            a_ = np.array([1, 2 * (wc * wc - 1) / a0, (1 - k * wc + wc * wc) / a0])
            seg, zi = lfilter(b_, a_, w[s0:s0 + blk], zi=zi)
            y[s0:s0 + blk] = seg
        out += amp * y
    return out
