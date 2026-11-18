#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""tools/sgqmid: a project image to a MIDI file and back. The hardware test's project goes out as three tracks at
PPQ 384 with its tempo; the file comes back as TAPE tracks with every note where it was; the image it makes imports
into the simulator (the SysEx import, as the Pi does it) and plays.

    python3 tests/sagga_sgqmid_tests.py
"""
import os
import struct
import subprocess
import sys
import tempfile
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fm1_install as FI                                   # noqa: E402

TOOL = os.path.join(ROOT, "build", "sagga_sgqmid")
FAILS = []
N = [0]


def check(c, what):
    N[0] += 1
    if not c:
        FAILS.append(what)
        print("  FAIL:", what)


def read_smf(path):
    d = open(path, "rb").read()
    assert d[:4] == b"MThd"
    fmt, ntrk, div = struct.unpack(">HHH", d[8:14])
    p, out, tempo = 14, [], None

    def rdvar(p):
        v = 0
        while True:
            b = d[p]; p += 1; v = (v << 7) | (b & 0x7F)
            if not b & 0x80:
                return v, p
    for _ in range(ntrk):
        assert d[p:p + 4] == b"MTrk"
        ln = struct.unpack(">I", d[p + 4:p + 8])[0]
        q, end, t, ev, name, run = p + 8, p + 8 + ln, 0, [], "", 0
        while q < end:
            dt, q = rdvar(q); t += dt; st = d[q]
            if st == 0xFF:
                ty = d[q + 1]; ml, q2 = rdvar(q + 2)
                if ty == 3: name = d[q2:q2 + ml].decode()
                if ty == 0x51: tempo = int.from_bytes(d[q2:q2 + 3], "big")
                q = q2 + ml
                continue
            if st & 0x80: run = st; q += 1
            else: st = run
            d1 = d[q]; q += 1; d2 = 0
            if (st & 0xF0) not in (0xC0, 0xD0): d2 = d[q]; q += 1
            ev.append((t, st, d1, d2))
        out.append((name, ev)); p = end
    return fmt, div, tempo, out


def notes(ev):
    """(on tick, channel, note, vel, duration) from a track's events"""
    on, out = {}, []
    for t, st, d1, d2 in ev:
        if (st & 0xF0) == 0x90 and d2: on[(st & 15, d1)] = (t, d2)
        elif (st & 0xF0) in (0x80, 0x90) and (st & 15, d1) in on:
            t0, v = on.pop((st & 15, d1)); out.append((t0, st & 15, d1, v, t - t0))
    return out


def time_sig(path):
    """(numerator, denominator) of the file's first time signature (None: it has none)"""
    d = open(path, "rb").read()
    i = d.find(b"\xff\x58\x04")
    return None if i < 0 else (d[i + 3], 1 << d[i + 4])


def write_smf(path, ppq, tempo_us, tracks, sig=None):
    """tracks: list of [(tick, status, d1, d2)]; sig: (numerator, log2 of the denominator), 0.25"""
    def var(v):
        b = [v & 0x7F]; v >>= 7
        while v: b.append((v & 0x7F) | 0x80); v >>= 7
        return bytes(reversed(b))
    chunks = []
    tempo = (b"\x00\xff\x58\x04" + bytes([sig[0], sig[1], 24, 8]) if sig else b"") + b"\x00\xff\x51\x03" + tempo_us.to_bytes(3, "big") + b"\x00\xff\x2f\x00"
    chunks.append(b"MTrk" + struct.pack(">I", len(tempo)) + tempo)
    for ev in tracks:
        last, body = 0, b""
        for t, st, d1, d2 in sorted(ev):
            body += var(t - last) + bytes([st, d1, d2]); last = t
        body += b"\x00\xff\x2f\x00"
        chunks.append(b"MTrk" + struct.pack(">I", len(body)) + body)
    open(path, "wb").write(b"MThd" + struct.pack(">IHHH", 6, 1, len(chunks), ppq) + b"".join(chunks))


def sysex_import_script(img):
    """the frames of a SysEx import (02 chunks, 03 end) as simulator 'sx' lines"""
    lines, cnt = [], (len(img) + 255) // 256
    for i in range(cnt):
        packed = FI.pack7(img[i * 256:(i + 1) * 256])
        frame = [0x7D, 0x53, 0x47, 0x02, i & 127, i >> 7, cnt & 127, cnt >> 7] + list(packed) + [sum(packed) & 127]
        lines.append("sx " + " ".join("%02X" % b for b in frame))
    crc, ln = zlib.crc32(img), len(img)
    end = [0x7D, 0x53, 0x47, 0x03, ln & 127, (ln >> 7) & 127, (ln >> 14) & 127, crc & 127, (crc >> 7) & 127, (crc >> 14) & 127, (crc >> 21) & 127, (crc >> 28) & 127]
    lines.append("sx " + " ".join("%02X" % b for b in end))
    return lines


def main():
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2", "-I" + os.path.join(ROOT, "firmware", "src"),
                    os.path.join(ROOT, "tools", "sgqmid", "sagga_sgqmid.c"), os.path.join(ROOT, "firmware", "src", "sagga_seq_core.c"),
                    os.path.join(ROOT, "firmware", "src", "sagga_beats.c"), "-o", TOOL], check=True)
    d = tempfile.mkdtemp()
    hw = os.path.join(ROOT, "tools", "hwtest", "hwtest.sgq")
    mid = os.path.join(d, "hw.mid")
    print("sgq2mid: the hardware test's project")
    r = subprocess.run([TOOL, "sgq2mid", hw, mid], capture_output=True, text=True)
    check(r.returncode == 0, "the tool converts (%s)" % r.stderr.strip())
    fmt, ppq, tempo, tr = read_smf(mid)
    check(fmt == 1 and ppq == 384 and tempo == 468750, "format 1, PPQ 384, 128 BPM (%s %s %s)" % (fmt, ppq, tempo))
    names = [n for n, _ in tr]
    check(names[1:] == ["T1 ch1", "T2 ch2", "T3 ch3", "T4 ch4 TAPE"], "a track per track with notes, named, the tape marked (%s)" % names)
    n1, n2 = notes(tr[1][1]), notes(tr[2][1])
    check(len(n1) == 16 and [x[0] for x in n1[:4]] == [0, 384, 768, 1152] and all(x[2] == 60 for x in n1), "track 1: four on the floor over 4 bars (%s)" % n1[:4])
    check([x[2] for x in n2[:4]] == [60, 62, 64, 67] and [x[0] for x in n2[:4]] == [0, 96, 192, 288], "track 2: C D E G on four 1/16 (%s)" % n2[:4])
    check(all(x[4] > 0 for x in n1 + n2), "every note has a length")
    n4 = notes(tr[4][1])
    check(len(n4) == 8 and [x[0] for x in n4[:2]] == [96, 960] and n4[0][2] == 48 and n4[0][4] > 0, "track 4: the tape's two notes, repeated over the 4 bars (%s)" % n4[:2])
    print("mid2sgq: a file of two channels with free timing becomes two TAPE tracks")
    ev1 = [(0, 0x90, 60, 100), (380, 0x80, 60, 0), (500, 0x90, 64, 90), (900, 0x80, 64, 0), (1537, 0x90, 67, 80), (1600, 0x80, 67, 0)]
    ev2 = [(10, 0x91, 36, 127), (20, 0x81, 36, 0), (3072 + 5, 0x91, 36, 110), (3072 + 15, 0x81, 36, 0)]
    src = os.path.join(d, "free.mid")
    write_smf(src, 480, 500000, [ev1, ev2])                 # PPQ 480, 120 BPM
    sgq = os.path.join(d, "free.sgq")
    r = subprocess.run([TOOL, "mid2sgq", src, sgq], capture_output=True, text=True)
    check(r.returncode == 0 and "5 notes on 2 tapes, 2 bars, 120 BPM" in r.stderr, "converted: 5 notes, 2 tapes, 2 bars, 120 BPM (%s)" % r.stderr.strip())
    back = os.path.join(d, "back.mid")
    subprocess.run([TOOL, "sgq2mid", sgq, back], check=True, capture_output=True)
    fmt, ppq, tempo, tr = read_smf(back)
    n1, n2 = notes(tr[1][1]), notes(tr[2][1])
    # PPQ 480 -> 384: tick * 384 / 480 = tick * 0.8; the tapes loop over the 2 bars: the first pass is the file
    check(tempo == 500000 and [x[0] for x in n1[:3]] == [0, 400, 1229] and [x[4] for x in n1[:3]] == [304, 320, 51], "track 1 back: starts and lengths scaled to 384 (%s)" % n1[:3])
    check([x[0] for x in n2[:2]] == [8, 2461] and n2[0][3] == 127 and tr[1][0].endswith("TAPE"), "track 2 back: the kick where it was, velocity kept, a TAPE track (%s)" % n2[:2])
    print("the image imports into the simulator and plays")
    import sagga_sim_tests as S
    S.build()
    img = open(sgq, "rb").read()
    s = S.Script()
    t = 100
    for line in sysex_import_script(img):
        s.raw(t, line); t += 20
    s.at(t + 100, "dump", 0)
    t0 = t + 300
    s.tap_btn(t0, S.PLAY)
    bar = 60000.0 / 120 * 4
    log = S.run(s, t0 + int(2.2 * bar))
    st = [x["msg"] for x in log.states]
    check(any("IMPORTED" in m for m in st), "the import is taken (%s)" % st[:1])
    check(log.tapes and log.tapes[0]["n"] == 3 and log.tapes[0]["bars"] == 2, "track 1 is a tape of 3 notes over 2 bars (%s)" % (log.tapes[:1]))
    a = [(round(tt - t0), d1) for tt, d1, _ in log.notes(ch=0, after=t0)]
    b = [(round(tt - t0), d1) for tt, d1, _ in log.notes(ch=1, after=t0)]
    check(len(a) >= 3 and [x[1] for x in a[:3]] == [60, 64, 67] and S.near(a[1][0], 500 / 480 * 500, 3) and S.near(a[2][0], 1537 / 480 * 500, 3),
          "it plays: C at 0, E at 521 ms, G at 1601 ms (%s)" % a[:3])
    check(len(b) >= 2 and S.near(b[0][0], 10 / 480 * 500, 3) and S.near(b[1][0], 3077 / 480 * 500, 3), "channel 2: the kick at 10 ms and at 3205 ms (%s)" % b[:2])
    # 0.25 THE METRE: a file says its time signature; one in 7/8 makes a project in 7/8, its tapes' loops bars of 14 steps
    print("0.25: the metre - 4/4 written as 4/4; a file in 7/8 is a project in 7/8 (the tape's loop: bars of 14 steps), and back")
    check(time_sig(mid) == (4, 4) and time_sig(back) == (4, 4), "a project in 4/4 says 4/4 (%s %s)" % (time_sig(mid), time_sig(back)))
    ev7 = [(0, 0x90, 60, 100), (100, 0x80, 60, 0), (1680 + 20, 0x90, 62, 100), (1680 + 120, 0x80, 62, 0)]   # PPQ 480: a bar of 7/8 is 1680 ticks
    src7, sgq7, back7 = os.path.join(d, "seven.mid"), os.path.join(d, "seven.sgq"), os.path.join(d, "seven-back.mid")
    write_smf(src7, 480, 500000, [ev7], sig=(7, 3))
    r = subprocess.run([TOOL, "mid2sgq", src7, sgq7], capture_output=True, text=True)
    check(r.returncode == 0 and "2 notes on 1 tapes, 2 bars, 120 BPM" in r.stderr, "7/8: the file's two bars are two bars (in 4/4 they would be one) (%s)" % r.stderr.strip())
    subprocess.run([TOOL, "sgq2mid", sgq7, back7, "2"], check=True, capture_output=True)
    fmt, ppq, tempo, tr7 = read_smf(back7)
    n7 = notes(tr7[1][1])
    check(time_sig(back7) == (7, 8) and [x[0] for x in n7] == [0, 1360], "... and back: 7/8, the two notes over its two bars, 2688 ticks (%s %s)" % (time_sig(back7), n7))
    for name, nn, dd, want in (("6/8", 6, 3, (6, 8)), ("3/4", 3, 2, (3, 4)), ("5/4", 5, 2, (5, 4)), ("15/16", 15, 4, (15, 16)), ("9/4 (36 steps: no such bar)", 9, 2, (4, 4))):
        a, b2, c2 = os.path.join(d, "s.mid"), os.path.join(d, "s.sgq"), os.path.join(d, "s2.mid")
        write_smf(a, 480, 500000, [[(0, 0x90, 60, 100), (100, 0x80, 60, 0)]], sig=(nn, dd))
        subprocess.run([TOOL, "mid2sgq", a, b2], check=True, capture_output=True)
        subprocess.run([TOOL, "sgq2mid", b2, c2], check=True, capture_output=True)
        check(time_sig(c2) == want, "a file in %s: the project's metre (%s)" % (name, time_sig(c2)))
    # 0.25 THE POLYRHYTHMS: a track of five steps at 1/4 5:4 is five notes a bar, 307.2 ticks apart
    jt = os.path.join(d, "sgqjson")
    subprocess.run(["cc", "-std=c11", "-O2", "-I" + os.path.join(ROOT, "firmware", "src"), os.path.join(ROOT, "tools", "sgqmid", "sagga_sgqjson.c"),
                    os.path.join(ROOT, "firmware", "src", "sagga_seq_core.c"), os.path.join(ROOT, "firmware", "src", "sagga_beats.c"), "-o", jt], check=True)
    patch, p5, m5 = os.path.join(d, "p5.txt"), os.path.join(d, "p5.sgq"), os.path.join(d, "p5.mid")
    with open(patch, "w") as f:
        f.write("track 0 division - 13\ntrack 0 length - 5\n" + "".join("step 0,0,%d flags - 3\nstep 0,0,%d note 0 %d\n" % (k, k, 60 + k) for k in range(5)))
    subprocess.run([jt, "apply", "new", patch, p5], check=True, capture_output=True)
    subprocess.run([TOOL, "sgq2mid", p5, m5, "2"], check=True, capture_output=True)
    _, _, _, tr5 = read_smf(m5)
    n5 = notes(tr5[1][1])
    check([x[0] for x in n5] == [k * 1536 // 5 for k in range(10)] and [x[2] for x in n5] == [60, 61, 62, 63, 64] * 2,
          "a track at 1/4 5:4: five notes in each bar, where the fifths of the bar fall (%s)" % [x[0] for x in n5[:6]])
    img = open(sgq7, "rb").read()
    s = S.Script()
    t = 100
    for line in sysex_import_script(img):
        s.raw(t, line); t += 20
    s.at(t + 100, "dump", 0)
    t0 = t + 300
    s.tap_btn(t0, S.PLAY)
    log = S.run(s, t0 + int(60 * 125))
    a = [(round(tt - t0), d1) for tt, d1, _ in log.notes(ch=0, after=t0)]
    check(log.metre and log.metre[0]["bar"] == 14 and log.metre[0]["sig"] == "7/8" and log.tapes[0]["bars"] == 2, "in the FM-1: a bar of 14, a tape of 2 bars (%s)" % log.metre[:1])
    check(len(a) >= 4 and [x[1] for x in a[:4]] == [60, 62, 60, 62] and S.near(a[1][0], 1700 / 480 * 500, 3) and S.near(a[2][0], 28 * 125, 3) and S.near(a[3][0], 28 * 125 + 1700 / 480 * 500, 3),
          "it plays: the loop comes round every 28 steps, 3500 ms (%s)" % a[:4])
    print("sgqmid: %d checks, %d failures" % (N[0], len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
