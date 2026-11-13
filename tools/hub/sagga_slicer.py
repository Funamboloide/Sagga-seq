#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA SLICER (0.13): a drum break (a WAV loop) cut into 8, 16 or 32 slices for a sampler, ready for a SAGGA BREAK track.

It finds where the break starts (the silence before it goes), how many bars it is and its tempo (a power of two of bars
that puts it between 90 and 180 BPM; or the BPM / bars you give), cuts it on the 16th grid of the loop and moves each cut
onto the hit that is next to it (so no slice begins in the middle of an attack), at a zero crossing, with a short fade at
the end. Out comes a zip:

    01.wav .. NN.wav      the slices, in the source's format (8-bit becomes 16-bit)
    <name>-loop.wav       the loop from its start, with a cue point at every slice (samplers that read cues slice it alone)
    <name>.sfz            the slices on the keys from the PEN note up (C1 = 36 unless said), one at a time (a new one
                          cuts the one playing): sfizz, Zynthian, Sforzando ... load it as it is
    LEGGIMI.txt           the tempo, the bars, where each slice is, and what to set on the FM-1

Standard library only: it runs on the Pi with the hub (sagga_fw.py: the BREAK section of the page) or anywhere:

    python3 sagga_slicer.py amen.wav [--slices 16] [--bpm 136] [--bars 1] [--pen 36] [-o amen-16.zip]
"""
import argparse
import array
import io
import math
import os
import re
import struct
import sys
import zipfile

SLICES = (8, 16, 32)
BPM_LO, BPM_HI = 90.0, 180.0           # the tempo found is a power of two of bars inside this (one octave: one answer)
MAX_SECONDS = 64.0


class SliceError(ValueError):
    pass


# ---- WAV in / out
class Wav:
    """a decoded WAV: rate, channels, the sample format to write back (fmt 1 or 3, bits), the samples as floats per channel"""
    def __init__(self, rate, chans, fmt, bits, data):
        self.rate, self.chans, self.fmt, self.bits, self.data = rate, chans, fmt, bits, data

    @property
    def frames(self):
        return len(self.data[0]) if self.data else 0


def _native(a):
    if sys.byteorder != 'little':
        a.byteswap()
    return a


def read_wav(raw):
    """bytes of a RIFF/WAVE file -> Wav. PCM 8/16/24/32-bit and float 32-bit, also as WAVE_FORMAT_EXTENSIBLE"""
    if len(raw) < 12 or raw[:4] != b'RIFF' or raw[8:12] != b'WAVE':
        raise SliceError('non è un file WAV (RIFF/WAVE)')
    pos, fmt, data = 12, None, None
    while pos + 8 <= len(raw):
        cid, size = raw[pos:pos + 4], struct.unpack_from('<I', raw, pos + 4)[0]
        body = raw[pos + 8:pos + 8 + size]
        if cid == b'fmt ':
            if len(body) < 16:
                raise SliceError('WAV: chunk fmt troppo corto')
            tag, chans, rate, _, align, bits = struct.unpack_from('<HHIIHH', body)
            if tag == 0xFFFE and len(body) >= 26:
                tag = struct.unpack_from('<H', body, 24)[0]      # (the sub-format GUID begins with the real tag)
            fmt = (tag, chans, rate, align, bits)
        elif cid == b'data':
            data = body
        pos += 8 + size + (size & 1)
    if fmt is None or data is None:
        raise SliceError('WAV senza fmt o senza data')
    tag, chans, rate, align, bits = fmt
    if chans < 1 or chans > 8 or rate < 8000 or rate > 192000:
        raise SliceError('WAV: %d canali a %d Hz?' % (chans, rate))
    width = bits // 8
    if tag == 1 and bits in (8, 16, 24, 32):
        pass
    elif tag == 3 and bits == 32:
        pass
    else:
        raise SliceError('WAV: formato %d a %d bit non letto (serve PCM 8/16/24/32 o float 32)' % (tag, bits))
    if align != width * chans:
        raise SliceError('WAV: block align %d non torna' % align)
    n = len(data) // align
    if n < rate // 20:
        raise SliceError('WAV troppo corto')
    if n > MAX_SECONDS * rate:
        raise SliceError('WAV troppo lungo (più di %d secondi): un break è qualche battuta' % MAX_SECONDS)
    data = data[:n * align]
    if tag == 3:
        flat = list(_native(array.array('f', data)))
    elif bits == 16:
        flat = [v / 32768.0 for v in _native(array.array('h', data))]
    elif bits == 32:
        flat = [v / 2147483648.0 for v in _native(array.array('i', data))]
    elif bits == 8:
        flat = [(v - 128) / 128.0 for v in data]
    else:                                                       # 24-bit: three bytes, little endian, signed
        b = data
        flat = [((b[i] | (b[i + 1] << 8) | (b[i + 2] << 16)) - ((b[i + 2] & 0x80) << 17)) / 8388608.0 for i in range(0, len(b), 3)]
    chs = [flat[c::chans] for c in range(chans)]
    return Wav(rate, chans, tag, 16 if (tag == 1 and bits == 8) else bits, chs)


def _encode(w, a, b, fade_in=0, fade_out=0):
    """frames a..b of w as the data of a WAV of w's format, with linear fades (frames)"""
    n = b - a
    if n <= 0:
        return b''
    gains = None
    if fade_in or fade_out:
        gains = [1.0] * n
        for i in range(min(fade_in, n)):
            gains[i] = min(gains[i], (i + 1) / float(fade_in + 1))
        for i in range(min(fade_out, n)):
            gains[n - 1 - i] = min(gains[n - 1 - i], (i + 1) / float(fade_out + 1))
    inter = []
    for i in range(n):
        g = gains[i] if gains else 1.0
        for c in range(w.chans):
            inter.append(w.data[c][a + i] * g)
    if w.fmt == 3:
        out = array.array('f', inter)
        return _native(out).tobytes()
    if w.bits == 16:
        out = array.array('h', (max(-32768, min(32767, int(round(v * 32768.0)))) for v in inter))
        return _native(out).tobytes()
    if w.bits == 32:
        out = array.array('i', (max(-2147483648, min(2147483647, int(round(v * 2147483648.0)))) for v in inter))
        return _native(out).tobytes()
    o = bytearray()
    for v in inter:                                             # 24-bit
        x = max(-8388608, min(8388607, int(round(v * 8388608.0)))) & 0xFFFFFF
        o += bytes((x & 255, (x >> 8) & 255, x >> 16))
    return bytes(o)


def write_wav(w, a, b, fade_in=0, fade_out=0, cues=None, labels=None):
    """a WAV file (bytes) of frames a..b of w; cues: frame positions (from a) for a cue chunk and its labels"""
    pcm = _encode(w, a, b, fade_in, fade_out)
    width = w.bits // 8
    fmt = struct.pack('<HHIIHH', w.fmt, w.chans, w.rate, w.rate * width * w.chans, width * w.chans, w.bits)
    chunks = [b'fmt ' + struct.pack('<I', len(fmt)) + fmt, b'data' + struct.pack('<I', len(pcm)) + pcm + (b'\0' if len(pcm) & 1 else b'')]
    if cues:
        body = struct.pack('<I', len(cues))
        for i, f in enumerate(cues):
            body += struct.pack('<II4sIII', i + 1, f, b'data', 0, 0, f)
        chunks.append(b'cue ' + struct.pack('<I', len(body)) + body)
        adtl = b'adtl'
        for i, name in enumerate(labels or []):
            t = name.encode('ascii', 'replace') + b'\0'
            if len(t) & 1:
                t += b'\0'
            adtl += b'labl' + struct.pack('<I', 4 + len(name) + 1) + struct.pack('<I', i + 1) + t
        chunks.append(b'LIST' + struct.pack('<I', len(adtl)) + adtl)
    body = b'WAVE' + b''.join(chunks)
    return b'RIFF' + struct.pack('<I', len(body)) + body


# ---- the analysis
def _mono(w):
    if w.chans == 1:
        return w.data[0]
    k = 1.0 / w.chans
    return [sum(v) * k for v in zip(*w.data)]


def envelope(mono, hop):
    """energy a hop (sum of squares)"""
    return [sum(x * x for x in mono[i:i + hop]) for i in range(0, len(mono), hop)]


def onsets(env):
    """onset strength a hop: how much the log energy grew over the hop before (0 when it fell)"""
    eps = 1e-9
    peak = max(env) if env else 0.0
    floor = peak * 1e-5 + eps                                    # (-50 dB under the loudest hop: no onsets in the silence)
    out = [0.0]
    for i in range(1, len(env)):
        a, b = max(env[i - 1], floor), max(env[i], floor)
        out.append(max(0.0, math.log(b / a)))
    return out


def find_start(mono, rate):
    """(the first frame of the break, its first hit): the hit is the first sample above 3 % of the peak; the break
    starts a millisecond before it, at a zero crossing (the tempo is counted from the hit: the loop is a whole bar)"""
    peak = max(abs(x) for x in mono) if mono else 0.0
    if peak <= 1e-6:
        raise SliceError('il file è silenzio')
    thr = 0.03 * peak
    hit = next(k for k, x in enumerate(mono) if abs(x) >= thr)
    i = max(0, hit - rate // 1000)
    return zero_cross(mono, i, rate // 500, back_only=True), hit


def zero_cross(mono, i, span, back_only=False):
    """the frame nearest i (within span; back_only: not after i) where the signal crosses zero, else the quietest"""
    lo, hi = max(1, i - span), min(len(mono) - 1, i if back_only else i + span)
    if lo > hi:
        return i
    cross = [k for k in range(lo, hi + 1) if (mono[k - 1] <= 0.0 < mono[k]) or (mono[k - 1] >= 0.0 > mono[k])]
    if cross:
        return min(cross, key=lambda k: abs(k - i))
    return min(range(lo, hi + 1), key=lambda k: (abs(mono[k]), abs(k - i)))


def refine(mono, a, b, mini=32):
    """the frame (to `mini`) between a and b where the energy grows the most from the frames before it: a hit's start"""
    best, bv, prev = a, 0.0, None
    for k in range(a, b, mini):
        e = sum(x * x for x in mono[k:k + mini]) + 1e-12
        if prev is not None and e / prev > bv:
            best, bv = k, e / prev
        prev = e
    return best


def tempo(length_s, bpm=None, bars=None):
    """(bpm, bars) of a loop length_s long: what is given, else the power of two of bars that falls in BPM_LO..BPM_HI"""
    if bpm and bars:
        return float(bpm), int(bars)
    if bars:
        return 240.0 * bars / length_s, int(bars)
    if bpm:
        b = max(1, int(round(length_s * bpm / 240.0)))
        return float(bpm), b
    b = 1
    while 240.0 * b / length_s < BPM_LO and b < 64:
        b *= 2
    while 240.0 * b / length_s >= BPM_HI and b > 1:
        b //= 2
    bp = 240.0 * b / length_s
    if not (BPM_LO * 0.5 <= bp <= BPM_HI * 2):
        raise SliceError('non trovo un tempo sensato (%.1f BPM per %d battute): dimmi BPM o battute' % (bp, b))
    return bp, b


def slice_points(w, n=16, bpm=None, bars=None):
    """-> dict(start, end, bpm, bars, cuts=[frames], snapped=[bool]): the cuts of the loop, the first one its start"""
    if n not in SLICES:
        raise SliceError('le slice sono 8, 16 o 32')
    mono = _mono(w)
    rate = w.rate
    start, hit = find_start(mono, rate)
    if bpm or bars:
        b0 = bars
        if bpm and not bars:
            b0 = max(1, int(round((w.frames - hit) / rate * bpm / 240.0)))
        length = int(round(240.0 * b0 / bpm * rate)) if bpm else w.frames - hit
        bp, b = tempo(length / float(rate), bpm, b0)
        length = int(round(240.0 * b / bp * rate))
    else:
        length = w.frames - hit
        bp, b = tempo(length / float(rate))
    end = min(w.frames, start + length)
    hop = max(64, rate // 200)                                   # 5 ms
    env = envelope(mono, hop)
    od = onsets(env)
    big = max(od) if od else 0.0
    step = length / float(n)
    reach = int(min(step / 4.0, 0.03 * rate))                    # a cut moves at most a quarter of a slice (30 ms)
    cuts, snapped = [start], [False]
    for k in range(1, n):
        g = start + int(round(k * step))
        lo, hi = (g - reach) // hop, (g + reach) // hop
        best, bv = None, 0.25 * big
        for h in range(max(1, lo), min(len(od) - 1, hi) + 1):
            if od[h] > bv and od[h] >= od[h - 1] and od[h] >= od[h + 1]:
                best, bv = h, od[h]
        c = g
        if best is not None:                                      # the hop the hit grew in: where in it, to 32 frames
            h = refine(mono, max(start + 1, (best - 1) * hop), min(w.frames - 1, (best + 1) * hop))
            c = zero_cross(mono, max(start + 1, h - rate // 2000), rate // 2000, back_only=True)   # half a millisecond before
        else:
            c = zero_cross(mono, c, rate // 1000)
        c = max(c, cuts[-1] + hop)
        if c >= end:
            c = min(g, end - 1)
        cuts.append(c)
        snapped.append(best is not None)
    return dict(start=start, end=end, bpm=bp, bars=b, cuts=cuts, snapped=snapped, rate=rate)


# ---- the package
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def note_name(n):
    return '%s%d' % (NOTE_NAMES[n % 12], n // 12 - 1)


def slice_len_name(sixteenths):
    """how long a slice is, as a note value: 1/16, 1/8, 1/32 ..., else in sixteenths"""
    names = {0.25: '1/64', 0.5: '1/32', 1.0: '1/16', 2.0: '1/8', 4.0: '1/4', 8.0: '1/2', 16.0: 'battuta'}
    return names.get(sixteenths, '%g sedicesimi' % sixteenths)


def safe_name(name):
    base = os.path.splitext(os.path.basename(name or 'break'))[0]
    base = re.sub(r'[^A-Za-z0-9._-]+', '-', base).strip('-.') or 'break'
    return base[:40]


def slice_break(raw, name='break.wav', n=16, bpm=None, bars=None, pen=36):
    """the WAV bytes -> (zip bytes, info dict)"""
    if not 0 <= pen <= 127 - n:
        raise SliceError('la nota PEN %d non lascia posto a %d slice' % (pen, n))
    w = read_wav(raw)
    p = slice_points(w, n, bpm, bars)
    base = safe_name(name)
    cuts, end, rate = p['cuts'], p['end'], w.rate
    bounds = list(zip(cuts, cuts[1:] + [end]))
    fade_out = max(1, rate * 3 // 1000)                          # 3 ms at the end of each slice
    z = io.BytesIO()
    rows = []
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for i, (a, b) in enumerate(bounds):
            fi = 0 if a == p['start'] else max(1, rate // 4000)   # (a quarter of a millisecond: the cut is at a zero crossing anyway)
            zf.writestr('%02d.wav' % (i + 1), write_wav(w, a, b, fade_in=fi, fade_out=min(fade_out, (b - a) // 4)))
            rows.append((i + 1, pen + i, a - p['start'], b - a, p['snapped'][i]))
        zf.writestr('%s-loop.wav' % base, write_wav(w, p['start'], end, fade_out=fade_out,
                                                    cues=[a - p['start'] for a, _ in bounds],
                                                    labels=['SLICE %d' % (i + 1) for i in range(len(bounds))]))
        sfz = ['// SAGGA SEQ break: %s, %.1f BPM, %d %s, %d slices from %s (%d)' % (base, p['bpm'], p['bars'],
               'battuta' if p['bars'] == 1 else 'battute', n, note_name(pen), pen),
               '<group> group=1 off_by=1 off_mode=fast loop_mode=one_shot amp_veltrack=60']
        for i in range(len(bounds)):
            sfz.append('<region> sample=%02d.wav key=%d' % (i + 1, pen + i))
        zf.writestr('%s.sfz' % base, '\n'.join(sfz) + '\n')
        ms = lambda f: f * 1000.0 / rate
        txt = ['SAGGA SLICER - %s' % base, '',
               'tempo: %.1f BPM, %d %s (%.3f s dal primo colpo)' % (p['bpm'], p['bars'], 'battuta' if p['bars'] == 1 else 'battute', (end - p['start']) / float(rate)),
               'inizio: %.1f ms nel file (il silenzio prima e\' tolto)' % ms(p['start']),
               'slice: %d, una ogni %s' % (n, slice_len_name(16.0 * p['bars'] / n)), '',
               'SULL\'FM-1',
               '  la traccia: HOME 4 K1 = BREAK; la sua nota PEN = %s (%d), la prima slice' % (note_name(pen), pen),
               '  SEQ 7 SLICES = %d; il tempo del progetto: %.0f (o quello che vuoi: le slice seguono il sequencer)' % (n, p['bpm']),
               '  il campionatore sul canale della traccia: %s.sfz (sfizz, Zynthian, Sforzando ...) cosi\' com\'e\',' % base,
               '  oppure 01.wav .. %02d.wav su note consecutive da %s, una alla volta (la nuova taglia quella che suona);' % (n, note_name(pen)),
               '  oppure %s-loop.wav, se il campionatore legge i cue: ogni slice e\' un cue' % base, '',
               'slice  nota   da (ms)   lunga (ms)  sul colpo',
               ]
        for i, note, a, length, sn in rows:
            txt.append('%5d  %-5s %9.1f  %10.1f  %s' % (i, note_name(note), ms(a), ms(length), 'si' if sn else '-'))
        zf.writestr('LEGGIMI.txt', '\n'.join(txt) + '\n')
    info = dict(name=base, bpm=round(p['bpm'], 2), bars=p['bars'], slices=n, start_ms=round(p['start'] * 1000.0 / rate, 2),
                cuts_ms=[round((a - p['start']) * 1000.0 / rate, 2) for a in cuts], snapped=p['snapped'], rate=rate,
                channels=w.chans, bits=w.bits, pen=pen)
    return z.getvalue(), info


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('wav')
    ap.add_argument('--slices', type=int, default=16, choices=SLICES)
    ap.add_argument('--bpm', type=float, default=None)
    ap.add_argument('--bars', type=int, default=None)
    ap.add_argument('--pen', type=int, default=36, help='the key of slice 1 (36 = C1)')
    ap.add_argument('-o', '--out', default=None)
    a = ap.parse_args(argv)
    try:
        with open(a.wav, 'rb') as f:
            data, info = slice_break(f.read(), a.wav, a.slices, a.bpm, a.bars, a.pen)
    except (OSError, SliceError) as e:
        print('sagga_slicer: %s' % e, file=sys.stderr)
        return 1
    out = a.out or '%s-%d.zip' % (info['name'], a.slices)
    with open(out, 'wb') as f:
        f.write(data)
    print('%s: %.1f BPM, %d bars, %d slices from %s -> %s' % (info['name'], info['bpm'], info['bars'], info['slices'], note_name(info['pen']), out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
