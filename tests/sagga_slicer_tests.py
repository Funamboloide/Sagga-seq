#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA SLICER (tools/hub/sagga_slicer.py, 0.13) and the hub's BREAK form (tools/hub/sagga_fw.py): synthetic breaks
whose hits are where we put them; the tempo, the start, the cuts on the hits, the zip, the formats, the errors.

    python3 tests/sagga_slicer_tests.py
"""
import io
import math
import os
import struct
import sys
import threading
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'hub'))
import sagga_slicer as sl          # noqa: E402

FAILS = []
CHECKS = [0]


def check(cond, what):
    CHECKS[0] += 1
    if not cond:
        FAILS.append(what)
        print('  FAIL:', what)


def group(name):
    print(name)


class Rng:
    def __init__(self, seed): self.x = seed

    def next(self):
        self.x = (self.x * 1103515245 + 12345) & 0x7FFFFFFF
        return self.x / float(0x7FFFFFFF) * 2.0 - 1.0


def make_break(rate=44100, bpm=136.0, bars=1, lead_ms=50.0, hits=None, chans=2, tail_ms=0.0, seed=7):
    """float samples per channel; hits: [(16th position, offset ms, kind)] kind k kick, s snare, h hat. Returns (data, hit frames)"""
    if hits is None:
        hits = [(0, 0, 'k'), (2, 0, 'h'), (4, 0, 's'), (6, 0, 'h'), (7, 9, 'h'), (10, 0, 'k'), (11, 6, 'h'), (12, 0, 's'), (14, 0, 'h')]
        hits = [(p + 16 * b, o, k) for b in range(bars) for p, o, k in hits]
    lead = int(rate * lead_ms / 1000.0)
    length = int(round(240.0 * bars / bpm * rate))
    n = lead + length + int(rate * tail_ms / 1000.0)
    mono = [0.0] * n
    rng = Rng(seed)
    at = []
    step = length / (16.0 * bars)
    for pos, off, kind in hits:
        a = lead + int(round(pos * step + off * rate / 1000.0))
        at.append(a)
        dur = int(rate * (0.18 if kind == 'k' else 0.12 if kind == 's' else 0.04))
        amp = 0.9 if kind == 'k' else 0.7 if kind == 's' else 0.35
        for i in range(dur):
            if a + i >= n:
                break
            env = math.exp(-i / (dur / 5.0))
            if kind == 'k':
                v = math.sin(2 * math.pi * (55.0 + 90.0 * math.exp(-i / 800.0)) * i / rate)
            elif kind == 's':
                v = 0.6 * rng.next() + 0.4 * math.sin(2 * math.pi * 190.0 * i / rate)
            else:
                v = rng.next()
            mono[a + i] += amp * env * v
    data = [list(mono) for _ in range(chans)]
    if chans > 1:
        data[1] = [v * 0.8 for v in mono]
    return data, at, lead, length


def wav_bytes(data, rate, fmt=1, bits=16, extensible=False):
    w = sl.Wav(rate, len(data), fmt, bits, data)
    raw = sl.write_wav(w, 0, len(data[0]))
    if bits == 8:                                                    # (write_wav writes 8-bit as 16: build it by hand)
        pcm = bytes(int(max(0, min(255, round(v * 127.0 + 128)))) for fr in zip(*data) for v in fr)
        fmtb = struct.pack('<HHIIHH', 1, len(data), rate, rate * len(data), len(data), 8)
        body = b'WAVE' + b'fmt ' + struct.pack('<I', 16) + fmtb + b'data' + struct.pack('<I', len(pcm)) + pcm + (b'\0' if len(pcm) & 1 else b'')
        return b'RIFF' + struct.pack('<I', len(body)) + body
    if extensible:
        chans, width = len(data), bits // 8
        fmtb = struct.pack('<HHIIHHHHI', 0xFFFE, chans, rate, rate * width * chans, width * chans, bits, 22, bits, 3) + struct.pack('<H', fmt) + b'\x00\x00\x00\x00\x10\x00\x80\x00\x00\xaa\x00\x38\x9b\x71'
        i = raw.index(b'data')
        body = b'WAVE' + b'LIST' + struct.pack('<I', 4) + b'INFO' + b'fmt ' + struct.pack('<I', len(fmtb)) + fmtb + raw[i:]
        return b'RIFF' + struct.pack('<I', len(body)) + body
    return raw


def chunks(raw):
    pos, out = 12, {}
    while pos + 8 <= len(raw):
        cid, size = raw[pos:pos + 4], struct.unpack_from('<I', raw, pos + 4)[0]
        out[cid] = raw[pos + 8:pos + 8 + size]
        pos += 8 + size + (size & 1)
    return out


def t_tempo_start_cuts():
    group('a 1-bar break at 136 BPM after 50 ms of silence: the tempo, the start, the 16 cuts on the hits (two of them late)')
    rate = 44100
    data, at, lead, length = make_break(rate)
    raw = wav_bytes(data, rate)
    zipb, info = sl.slice_break(raw, 'Amen Brother.wav', 16)
    check(abs(info['bpm'] - 136.0) < 0.5 and info['bars'] == 1, 'tempo 136, 1 bar (%s %s)' % (info['bpm'], info['bars']))
    check(abs(info['start_ms'] - 50.0) <= 1.5, 'the start: the first hit, 50 ms in (%s)' % info['start_ms'])
    cuts = [c + info['start_ms'] for c in info['cuts_ms']]
    hit_ms = [a * 1000.0 / rate for a in at]
    step_ms = length * 1000.0 / rate / 16.0
    ok = True
    for k, c in enumerate(cuts):
        g = info['start_ms'] + k * step_ms
        near = [h for h in hit_ms if abs(h - g) <= min(step_ms / 4, 30)]
        if near:
            h = min(near, key=lambda x: abs(x - g))
            ok = ok and (h - 2.5 <= c <= h + 0.3)
        else:
            ok = ok and abs(c - g) <= 1.2
        if not ok:
            print('    cut %d at %.1f ms (grid %.1f, hits near %s)' % (k + 1, c, g, near))
            break
    check(len(cuts) == 16 and ok, 'each cut just before its hit (the late ones too), else on the grid')
    check(info['snapped'].count(True) == 8, 'the cuts moved onto a hit: 8 (%s)' % info['snapped'])
    z = zipfile.ZipFile(io.BytesIO(zipb))
    names = z.namelist()
    want = ['%02d.wav' % (i + 1) for i in range(16)] + ['Amen-Brother-loop.wav', 'Amen-Brother.sfz', 'LEGGIMI.txt']
    check(sorted(names) == sorted(want), 'the zip: 16 slices, the loop, the sfz, LEGGIMI (%s)' % names)
    sl_frames = [sl.read_wav(z.read('%02d.wav' % (i + 1))).frames for i in range(16)]
    loop = z.read('Amen-Brother-loop.wav')
    lw = sl.read_wav(loop)
    check(sum(sl_frames) == lw.frames and abs(lw.frames - length) <= 2, 'the slices add up to the loop, a bar long (%d %d %d)' % (sum(sl_frames), lw.frames, length))
    s1 = sl.read_wav(z.read('01.wav'))
    check(s1.chans == 2 and s1.bits == 16 and s1.rate == rate and s1.fmt == 1, 'the slices keep the format: 16-bit stereo 44.1 kHz')
    cue = chunks(loop).get(b'cue ')
    check(cue and struct.unpack_from('<I', cue)[0] == 16, 'the loop has 16 cue points')
    pts = [struct.unpack_from('<I', cue, 4 + 24 * i + 20)[0] for i in range(16)] if cue else []
    check(pts and pts[0] == 0 and all(b > a for a, b in zip(pts, pts[1:])), 'from 0, in order (%s)' % pts[:4])
    sfz = z.read('Amen-Brother.sfz').decode()
    keys = [int(x.split('key=')[1]) for x in sfz.splitlines() if x.startswith('<region>')]
    check(keys == list(range(36, 52)) and 'off_by=1' in sfz and 'one_shot' in sfz, 'the sfz: C1..D#2, one at a time, one shot (%s)' % keys[:3])
    txt = z.read('LEGGIMI.txt').decode()
    check('136.0 BPM' in txt and 'SEQ 7 SLICES = 16' in txt and 'BREAK' in txt and 'una ogni 1/16' in txt, 'LEGGIMI says the tempo and the FM-1 setup')
    # the slice begins with silence or the hit, never in the middle of the one before: its first samples are quiet
    s3 = sl.read_wav(z.read('03.wav')).data[0]
    check(max(abs(v) for v in s3[:20]) < 0.05, 'slice 3 starts before its hat (%.3f)' % max(abs(v) for v in s3[:20]))


def t_bars_and_formats():
    group('2 bars at 170, given BPM, 24-bit, float, 8-bit, mono, extensible; 8 and 32 slices')
    rate = 48000
    data, at, lead, length = make_break(rate, bpm=170.0, bars=2, lead_ms=0.0)
    _, info = sl.slice_break(wav_bytes(data, rate, bits=24), 'j.wav', 32)
    check(abs(info['bpm'] - 170.0) < 0.5 and info['bars'] == 2 and len(info['cuts_ms']) == 32, '2 bars at 170, 32 slices (%s %s)' % (info['bpm'], info['bars']))
    zipb, info = sl.slice_break(wav_bytes(data, rate, bits=24), 'j.wav', 8)
    w = sl.read_wav(zipfile.ZipFile(io.BytesIO(zipb)).read('01.wav'))
    check(w.bits == 24 and w.rate == 48000 and len(info['cuts_ms']) == 8, '24-bit stays 24-bit; 8 slices')
    check('una ogni 1/4' in zipfile.ZipFile(io.BytesIO(zipb)).read('LEGGIMI.txt').decode(), '8 slices of 2 bars: a quarter each')
    # a 1-bar loop at 85: the rule says 2 bars at 170 (one octave of tempos); BPM 85 given: 1 bar
    d85, _, _, _ = make_break(44100, bpm=85.0, bars=1, lead_ms=0.0)
    _, i1 = sl.slice_break(wav_bytes(d85, 44100), 'h.wav')
    _, i2 = sl.slice_break(wav_bytes(d85, 44100), 'h.wav', bpm=85)
    check(i1['bars'] == 2 and abs(i1['bpm'] - 170) < 0.5 and i2['bars'] == 1 and abs(i2['bpm'] - 85) < 0.01,
          'tempo between 90 and 180 unless given (%s/%s, %s/%s)' % (i1['bpm'], i1['bars'], i2['bpm'], i2['bars']))
    # a tail after the loop: BPM given cuts the loop where it ends
    dt, _, _, length = make_break(44100, bpm=136.0, bars=1, lead_ms=20.0, tail_ms=400.0)
    zb, it = sl.slice_break(wav_bytes(dt, 44100), 't.wav', bpm=136)
    lw = sl.read_wav(zipfile.ZipFile(io.BytesIO(zb)).read('t-loop.wav'))
    check(it['bars'] == 1 and abs(lw.frames - length) <= 2, 'BPM given: the tail after the bar is left out (%d / %d)' % (lw.frames, length))
    dm, _, _, _ = make_break(44100, chans=1)
    zb, im = sl.slice_break(wav_bytes(dm, 44100, fmt=3, bits=32), 'f.wav')
    w = sl.read_wav(zipfile.ZipFile(io.BytesIO(zb)).read('05.wav'))
    check(im['channels'] == 1 and w.fmt == 3 and w.bits == 32 and abs(im['bpm'] - 136) < 0.5, 'float 32 mono: read, written as float')
    _, ie = sl.slice_break(wav_bytes(data, rate, bits=16, extensible=True), 'e.wav')
    check(abs(ie['bpm'] - 170) < 0.5, 'WAVE_FORMAT_EXTENSIBLE, a LIST chunk before fmt: read (%s)' % ie['bpm'])
    zb, i8 = sl.slice_break(wav_bytes(dm, 44100, bits=8), 'b.wav')
    w = sl.read_wav(zipfile.ZipFile(io.BytesIO(zb)).read('01.wav'))
    check(w.bits == 16 and abs(i8['bpm'] - 136) < 0.5, '8-bit: read, the slices 16-bit')
    zb, ip = sl.slice_break(wav_bytes(dm, 44100), 'p.wav', pen=60)
    sfz = zipfile.ZipFile(io.BytesIO(zb)).read('p.sfz').decode()
    check('key=60' in sfz and 'key=75' in sfz and ip['pen'] == 60, 'the first note given: C4 up')


def t_errors():
    group('what it will not cut: not a WAV, silence, too long, a format it does not read, a PEN with no room')
    def err(raw, **kw):
        try:
            sl.slice_break(raw, 'x.wav', **kw)
        except sl.SliceError as e:
            return str(e)
        return None
    check(err(b'hello world, not a wav file at all') is not None, 'not a WAV')
    check('silenzio' in (err(wav_bytes([[0.0] * 44100], 44100)) or ''), 'silence')
    check('lungo' in (err(wav_bytes([[0.1] * (44100 * 70)], 44100)) or ''), 'more than 64 seconds')
    raw = bytearray(wav_bytes([[0.1, -0.1] * 4000], 8000))
    struct.pack_into('<H', raw, 20, 2)                               # ADPCM
    check('formato' in (err(bytes(raw)) or ''), 'ADPCM: not read')
    d, _, _, _ = make_break(44100, chans=1)
    check(err(wav_bytes(d, 44100), n=12) is not None, '12 slices: no')
    check(err(wav_bytes(d, 44100), n=32, pen=100) is not None, 'PEN 100 with 32 slices: no room')


def t_hub_form():
    group('the hub: the BREAK form posts the WAV, the zip comes back; a bad one says why')
    import sagga_fw
    from http.server import ThreadingHTTPServer
    import tempfile
    d = tempfile.mkdtemp()

    class W:
        def write(self, p, data):
            with open(p, 'wb') as f:
                f.write(data)
            return p

        def writable(self):
            import contextlib
            return contextlib.nullcontext()
    st = sagga_fw.State(os.path.join(d, 'fw'), d, writer=W(), pat_writer=W())
    st.probe = lambda: None
    srv = ThreadingHTTPServer(('127.0.0.1', 0), sagga_fw.make_handler(st))
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    port = srv.server_address[1]
    def post(fields, fname, data):
        b = '----sagga13'
        body = b''
        for k, v in fields.items():
            body += ('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (b, k, v)).encode()
        body += ('--%s\r\nContent-Disposition: form-data; name="f"; filename="%s"\r\nContent-Type: audio/wav\r\n\r\n' % (b, fname)).encode() + data + ('\r\n--%s--\r\n' % b).encode()
        req = urllib.request.Request('http://127.0.0.1:%d/api/slice' % port, data=body, method='POST',
                                     headers={'Content-Type': 'multipart/form-data; boundary=%s' % b})
        try:
            r = urllib.request.urlopen(req, timeout=60)
            return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()
    try:
        page = urllib.request.urlopen('http://127.0.0.1:%d/' % port, timeout=10).read().decode()
        check('BREAK IN SLICE' in page and 'action="/api/slice"' in page, 'the page has the BREAK form')
        data, _, _, _ = make_break(44100)
        code, hd, body = post({'slices': '16', 'bpm': '', 'bars': '', 'pen': '36'}, 'amen.wav', wav_bytes(data, 44100))
        check(code == 200 and hd.get('Content-Type') == 'application/zip' and 'amen-16-slice-136bpm.zip' in hd.get('Content-Disposition', ''),
              'a zip comes back, named with the tempo (%s %s)' % (code, hd.get('Content-Disposition')))
        check(code == 200 and len(zipfile.ZipFile(io.BytesIO(body)).namelist()) == 19, 'with the 19 files')
        code, hd, body = post({'slices': '8', 'bpm': '136', 'bars': '1', 'pen': '48'}, 'amen.wav', wav_bytes(data, 44100))
        sfz = zipfile.ZipFile(io.BytesIO(body)).read('amen.sfz').decode() if code == 200 else ''
        check(code == 200 and 'key=48' in sfz and sfz.count('<region>') == 8, 'the form fields count: 8 slices from C3 (%s)' % code)
        code, _, body = post({'slices': '16'}, 'notes.txt', b'just some text')
        check(code == 400 and 'non riesco' in body.decode(), 'not a WAV: 400 and why (%s %s)' % (code, body[:60]))
        code, _, body = post({'slices': '16', 'bpm': 'fast'}, 'amen.wav', wav_bytes(data, 44100))
        check(code == 400 and 'bpm' in body.decode(), 'a BPM that is not a number: 400 (%s)' % body[:60])
    finally:
        srv.shutdown()


def main():
    for t in (t_tempo_start_cuts, t_bars_and_formats, t_errors, t_hub_form):
        try:
            t()
        except Exception as e:
            import traceback
            traceback.print_exc()
            FAILS.append('%s raised %r' % (t.__name__, e))
    print('sagga slicer: %d checks, %d failures' % (CHECKS[0], len(FAILS)))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
