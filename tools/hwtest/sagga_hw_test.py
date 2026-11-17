#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA SEQ on the real FM-1, tested from this computer over USB-MIDI.

    python sagga_hw_test.py [--port NAME] [--yes] [--bars 4] [--out FOLDER]

What it does, in order (the FM-1 connected by USB, SAGGA SEQ running, STOPPED):
  1. finds the FM-1's MIDI ports and prints its identity
  2. EXPORT: asks the project the FM-1 has in memory (SysEx) and keeps it in backup-<time>.sgq
  3. IMPORT: sends the test project hwtest.sgq (made with the simulator, make_assets.py); exports it back and compares
  4. PLAY from the REMOTE (CC 20 on channel 14): four bars of notes and clock are captured and compared with what the
     simulator says the same project must send (hwtest_expected.json): clock rate and jitter, every note of the first
     two bars on channels 1-3 (track 3 is an EXPO RAMP), note-offs, nothing after STOP
  5. MUTE track 1 from the remote and back; the tempo up 8 and down 8; EXPORT while playing is refused
  6. RESTORE: the backup goes back into the FM-1's memory (it shows IMPORTED: SAVE TO KEEP IT; it is your project,
     exactly as it was, in memory: nothing is written to its flash by this program)
Everything the FM-1 sent is in hwtest-<time>.log, with the verdicts: send that file when something fails.

Needs Python 3.9+ with mido and python-rtmidi (run_hw_test.ps1 installs them)."""
import argparse
import json
import os
import re
import statistics
import sys
import threading
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.environ.get("SAGGA_HWTEST_ASSETS", HERE)                              # hwtest.sgq, hwtest_expected.json
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))   # fm1_install.py in the repository
import fm1_install as FI                                                           # noqa: E402

PORT_RE = re.compile(r"fm-1|felucca", re.I)
SX_HEAD = bytes([0xF0, 0x7D, 0x53, 0x47])
SX_EXPORT, SX_DATA, SX_END, SX_STATUS = 0x01, 0x02, 0x03, 0x10
SXS = {0: "OK", 1: "BUSY", 2: "BADCHUNK", 3: "ORDER", 4: "BADIMAGE", 5: "BADPROJECT", 6: "EMPTY", 7: "NOHOST"}
REMOTE_CH = 13                                                                      # channel 14
CC_PLAY, CC_TEMPO_DN, CC_TEMPO_UP, CC_MUTE0 = 20, 30, 31, 48
CHUNK = 256


# ------------------------------------------------------------------------------------------------ MIDI backends
class MidoLink:
    """one in/out pair; every message in goes to on_message(bytes, t) with t = time.perf_counter()"""
    def __init__(self, in_name, out_name):
        import mido
        self.mido, self.name, self.on_message = mido, in_name, None
        self.inp = mido.open_input(in_name, callback=self._rx)
        try:
            rt = getattr(self.inp, "_rt", None)                                   # python-rtmidi: let the clock through
            if rt is not None:
                rt.ignore_types(sysex=False, timing=False, active_sense=True)
        except Exception:
            pass
        self.out = mido.open_output(out_name)
        time.sleep(0.2)

    def _rx(self, msg):
        if self.on_message:
            self.on_message(bytes(msg.bytes()), time.perf_counter())

    def send(self, data):
        if data[0] == 0xF0:
            self.out.send(self.mido.Message("sysex", data=list(data[1:-1])))
        else:
            self.out.send(self.mido.Message.from_bytes(list(data)))

    def close(self):
        for p in (self.inp, self.out):
            try:
                p.close()
            except Exception:
                pass


class MidoBackend:
    def input_names(self):
        import mido
        return list(dict.fromkeys(mido.get_input_names()))

    def output_names(self):
        import mido
        return list(dict.fromkeys(mido.get_output_names()))

    def open(self, in_name, out_name):
        return MidoLink(in_name, out_name)


def pair_output(in_name, outs):
    """the output that belongs to an input: the same name, or Windows' MIDIIN2 (x) -> MIDIOUT2 (x)"""
    if in_name in outs:
        return in_name
    want = re.sub(r"MIDIIN(\d+)", r"MIDIOUT\1", in_name)
    base = lambda n: re.sub(r"\s+\d+$", "", n)                                      # mido numbers the ports on Windows
    same = [o for o in outs if base(o) == base(want)]
    if len(same) == 1:
        return same[0]
    return FI.pair_output(in_name, outs)


# ------------------------------------------------------------------------------------------------ the FM-1
class Port:
    def __init__(self, link, label):
        self.link, self.label = link, label
        self.events = []                                                           # (t, bytes)
        self.lock = threading.Lock()
        self.tally = None                    # 0.23.1: counts everything that comes in, if one is given (.add(bytes))
        link.on_message = self._rx

    def _rx(self, data, t):
        with self.lock:
            self.events.append((t, data))
            if self.tally is not None:
                self.tally.add(data)

    def take(self):
        with self.lock:
            ev, self.events = self.events, []
        return ev

    def wait_sysex(self, timeout, head=SX_HEAD):
        """the next SysEx frame starting with head, or None"""
        end = time.perf_counter() + timeout
        while True:
            with self.lock:
                for i, (t, d) in enumerate(self.events):
                    if d[0] == 0xF0 and d.startswith(head):
                        del self.events[i]
                        return d
            if time.perf_counter() >= end:
                return None
            time.sleep(0.005)

    def send(self, data):
        self.link.send(bytes(data))


class Report:
    def __init__(self, path):
        self.lines, self.fails, self.warns, self.n = [], [], [], 0
        self.f = open(path, "w", encoding="utf-8")

    def say(self, s):
        print(s, flush=True)
        self.f.write(s + "\n")
        self.f.flush()

    def check(self, cond, what, warn=False):
        self.n += 1
        tag = "PASS" if cond else ("WARN" if warn else "FAIL")
        if not cond:
            (self.warns if warn else self.fails).append(what)
        self.say("  %s  %s" % (tag, what))
        return cond

    def raw(self, title, port, events, t0=None):
        self.f.write("---- %s (%s): %d messages\n" % (title, port.label, len(events)))
        for t, d in events:
            self.f.write("%10.3f  %s\n" % ((t - (t0 if t0 else t)) * 1000.0, " ".join("%02X" % b for b in d)))
        self.f.flush()

    def close(self):
        self.f.close()


def pack7(data):
    return FI.pack7(data)


def export(port, slot=None, timeout=3.0):
    """ask the project (or a slot); returns (image or None, status code or None)"""
    port.take()
    req = SX_HEAD + bytes([SX_EXPORT] + ([slot] if slot is not None else [])) + b"\xF7"
    port.send(req)
    chunks, end, status = {}, None, None
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        f = port.wait_sysex(0.2)
        if f is None:
            if end or status is not None:
                break
            continue
        cmd, body = f[4], f[5:-1]
        if cmd == SX_STATUS:
            status = body[0]
            break
        if cmd == SX_DATA:
            idx, cnt = body[0] | body[1] << 7, body[2] | body[3] << 7
            data, sm = body[4:-1], body[-1]
            if sum(data) & 0x7F != sm:
                return None, "BADSUM"
            chunks[idx] = (cnt, bytes(FI.unpack7(data)))
        elif cmd == SX_END:
            ln = body[0] | body[1] << 7 | body[2] << 14
            crc = (body[3] | body[4] << 7 | body[5] << 14 | body[6] << 21 | body[7] << 28) & 0xFFFFFFFF
            end = (ln, crc)
            break
    if status is not None:
        return None, SXS.get(status, status)
    if not end or 0 not in chunks:
        return None, "NOANSWER"
    cnt = chunks[0][0]
    if any(i not in chunks for i in range(cnt)):
        return None, "MISSING CHUNK"
    img = b"".join(chunks[i][1] for i in range(cnt))[:end[0]]
    if len(img) != end[0] or zlib.crc32(img) != end[1]:
        return None, "CRC"
    return img, "OK"


def import_image(port, img, say=None):
    """send an image as an import; returns the final status name"""
    cnt = (len(img) + CHUNK - 1) // CHUNK
    for idx in range(cnt):
        piece = img[idx * CHUNK:(idx + 1) * CHUNK]
        packed = pack7(piece)
        frame = SX_HEAD + bytes([SX_DATA, idx & 127, idx >> 7, cnt & 127, cnt >> 7]) + bytes(packed) + bytes([sum(packed) & 127, 0xF7])
        for attempt in range(4):
            port.take()
            port.send(frame)
            ans = port.wait_sysex(1.0)
            if ans is None:
                continue
            if ans[4] == SX_STATUS and ans[5] == 0:
                break
            if ans[4] == SX_STATUS and ans[5] == 2:                                 # BADCHUNK: again
                continue
            return SXS.get(ans[5], "?") if ans[4] == SX_STATUS else "ODD ANSWER"
        else:
            return "NO ANSWER AT CHUNK %d" % idx
    crc = zlib.crc32(img)
    end = SX_HEAD + bytes([SX_END, len(img) & 127, (len(img) >> 7) & 127, (len(img) >> 14) & 127,
                           crc & 127, (crc >> 7) & 127, (crc >> 14) & 127, (crc >> 21) & 127, (crc >> 28) & 127, 0xF7])
    port.take()
    port.send(end)
    ans = port.wait_sysex(2.0)
    if ans is None:
        return "NO ANSWER AT END"
    return SXS.get(ans[5], "?") if ans[4] == SX_STATUS else "ODD ANSWER"


def remote(port, cc, v=127):
    port.send(bytes([0xB0 | REMOTE_CH, cc, v]))
    time.sleep(0.03)
    port.send(bytes([0xB0 | REMOTE_CH, cc, 0]))


# ------------------------------------------------------------------------------------------------ the captured stream
class Capture:
    def __init__(self, events):
        self.ev = events
        self.start = next((t for t, d in events if d[0] == 0xFA), None)
        self.stop = next((t for t, d in events if d[0] == 0xFC), None)

    def rel(self, t):
        return (t - self.start) * 1000.0

    def clocks(self, a_ms=None, b_ms=None):
        c = [self.rel(t) for t, d in self.ev if d[0] == 0xF8 and self.start is not None and t >= self.start]
        return [x for x in c if (a_ms is None or x >= a_ms) and (b_ms is None or x < b_ms)]

    def notes(self, ch=None, a_ms=None, b_ms=None):
        out = []
        for t, d in self.ev:
            if len(d) == 3 and (d[0] & 0xF0) == 0x90 and d[2] and self.start is not None and t >= self.start:
                if ch is None or (d[0] & 15) == ch:
                    x = self.rel(t)
                    if (a_ms is None or x >= a_ms) and (b_ms is None or x < b_ms):
                        out.append((x, d[1], d[2]))
        return out

    def offs(self):
        return [self.rel(t) for t, d in self.ev if len(d) == 3 and ((d[0] & 0xF0) == 0x80 or ((d[0] & 0xF0) == 0x90 and not d[2]))
                and self.start is not None and t >= self.start]

    def bpm(self, a_ms, b_ms):
        c = self.clocks(a_ms, b_ms)
        if len(c) < 3:
            return 0.0
        return 60000.0 / 24 / ((c[-1] - c[0]) / (len(c) - 1))


def play_for(ctl, syn, seconds, during=()):
    """PLAY, do the (at_seconds, fn) things, STOP; returns the synth port's events of that time"""
    syn.take()
    t0 = time.perf_counter()
    remote(ctl, CC_PLAY)
    todo = sorted(during)
    while time.perf_counter() - t0 < seconds:
        if todo and time.perf_counter() - t0 >= todo[0][0]:
            todo.pop(0)[1]()
        time.sleep(0.005)
    remote(ctl, CC_PLAY)
    time.sleep(0.4)
    return syn.take()


# ------------------------------------------------------------------------------------------------ main
def find_ports(backend, want, rep):
    ins, outs = backend.input_names(), backend.output_names()
    rep.say("MIDI inputs: %s" % ins)
    cands = [n for n in ins if (want and want.lower() in n.lower()) or (not want and PORT_RE.search(n))]
    ports = []
    for n in cands:
        o = pair_output(n, outs)
        if not o:
            rep.say("  %s: no output to pair with" % n)
            continue
        try:
            ports.append(Port(backend.open(n, o), n))
        except Exception as e:
            rep.say("  %s: cannot open (%s)" % (n, e))
    return ports


def main(argv=None, backend=None):
    ap = argparse.ArgumentParser(description="SAGGA SEQ on the real FM-1, tested over USB-MIDI")
    ap.add_argument("--port", help="part of the FM-1's MIDI port name (default: any FM-1 / Felucca)")
    ap.add_argument("--yes", action="store_true", help="do not ask before replacing the project in memory")
    ap.add_argument("--bars", type=int, default=4, help="bars of the play test (4)")
    ap.add_argument("--out", default=HERE, help="folder for the log and the backup")
    a = ap.parse_args(argv)
    backend = backend or MidoBackend()
    ts = time.strftime("%Y%m%d-%H%M%S")
    rep = Report(os.path.join(a.out, "hwtest-%s.log" % ts))
    with open(os.path.join(ASSETS, "hwtest_expected.json")) as f:
        exp = json.load(f)
    with open(os.path.join(ASSETS, "hwtest.sgq"), "rb") as f:
        test_img = f.read()
    bar = exp["bar_ms"]
    rep.say("SAGGA SEQ hardware test, %s" % ts)

    try:
        ports = find_ports(backend, a.port, rep)
    except Exception as e:                                  # (mido or python-rtmidi missing: said in the log too)
        rep.say("cannot list the MIDI ports: %s: %s" % (type(e).__name__, e))
        rep.say("install them for this Python: py -3.12 -m pip install mido python-rtmidi")
        rep.close()
        return 4
    if not ports:
        rep.say("no FM-1 found: is it on, connected by USB, with SAGGA SEQ running? (--port NAME to choose a port)")
        return 3
    rep.say("ports: %s" % [p.label for p in ports])
    # identity (the platform answers the updater's handshake on any port)
    ident = None
    for p in ports:
        p.take()
        p.send(FI.HS_QUERY)
        f = p.wait_sysex(1.0, head=bytes([0xF0]))
        if f:
            ident = FI.parse_identity(f)
            if ident:
                break
    rep.check(ident is not None, "identity: %s" % (ident.text if ident else "no answer to the handshake"))
    # the control port: the one that answers the export
    ctl, backup = None, None
    for p in ports:
        img, st = export(p)
        if st in ("OK", "BUSY", "EMPTY"):
            ctl, backup = p, img
            if st == "BUSY":
                rep.say("the FM-1 is playing: STOP it and run this again")
                rep.close()
                return 1
            break
    if ctl is None:
        rep.say("no port answered the SysEx export: is SAGGA SEQ 0.5 or later running?")
        rep.close()
        return 1
    syn = ports[0] if len(ports) == 1 else next(p for p in ports if p is not ctl)
    rep.say("control port: %s; synth port: %s" % (ctl.label, syn.label))
    rep.check(backup is not None and backup[:4] in (b"SGQB", b"SGQA"), "EXPORT: the project in memory came out as a SGQB image (%d bytes)" % (len(backup) if backup else 0))
    if backup:
        bpath = os.path.join(a.out, "backup-%s.sgq" % ts)
        with open(bpath, "wb") as f:
            f.write(backup)
        rep.say("  kept in %s" % bpath)
    if not a.yes:
        print("The test project replaces the one in the FM-1's memory for a few minutes; the backup goes back at the end.")
        if input("Go on? [y/N] ").strip().lower() != "y":
            rep.close()
            return 1

    # IMPORT the test project, export it back
    st = import_image(ctl, test_img)
    rep.check(st == "OK", "IMPORT: the test project went in (%s)" % st)
    img2, st = export(ctl)
    rep.check(img2 is not None and st == "OK", "EXPORT after the import answers (%s)" % st)
    if img2:
        same = img2 == test_img
        rep.check(same, "ROUND TRIP: the image comes back identical (%d / %d bytes%s)" %
                  (len(img2), len(test_img), "" if same else ", first difference at %d" % next((i for i in range(min(len(img2), len(test_img))) if img2[i] != test_img[i]), min(len(img2), len(test_img)))), warn=True)

    # PLAY: the bars, the clock, the notes
    bars = max(2, a.bars)
    ev = play_for(ctl, syn, bars * bar / 1000.0 + 0.05)
    cap = Capture(ev)
    rep.raw("PLAY %d bars" % bars, syn, ev, cap.start)
    rep.check(cap.start is not None, "PLAY from the remote sends MIDI Start")
    if cap.start is None:
        rep.say("  nothing came on the synth port: with USB PORTS 2 the synth port is port 1; check the routing in the computer")
    else:
        rep.check(cap.stop is not None, "STOP from the remote sends MIDI Stop")
        bpm = cap.bpm(50, (bars - 0.2) * bar)
        rep.check(abs(bpm - exp["bpm"]) <= exp["bpm"] * 0.01, "clock: %.2f BPM (project: %d)" % (bpm, exp["bpm"]))
        c = cap.clocks(0, (bars - 0.2) * bar)
        d = [b - a_ for a_, b in zip(c, c[1:])]
        jit = statistics.pstdev(d) if len(d) > 2 else 0.0
        rep.check(jit < 3.0, "clock jitter: %.2f ms std, max gap %.1f ms (USB timing; the FM-1's own is tighter)" % (jit, max(d) if d else 0), warn=True)
        rep.check(abs(len(cap.clocks(0, bars * bar - 5)) - bars * 96) <= 3, "clock count: %d in %d bars (%d)" % (len(cap.clocks(0, bars * bar - 5)), bars, bars * 96))
        for ch_s, want in exp["notes_2bars"].items():
            ch = int(ch_s) - 1
            got = cap.notes(ch=ch, b_ms=2 * bar - 5)
            ok_n = len(got) == len(want)
            ok_p = ok_n and all(g[1] == w[1] and g[2] == w[2] for g, w in zip(got, want))
            dev = max((abs(g[0] - w[0]) for g, w in zip(got, want)), default=0.0)
            ok_t = ok_n and dev <= 25.0
            rep.check(ok_n and ok_p and ok_t, "channel %d: %d notes in 2 bars (%d expected), pitches %s, max time deviation %.1f ms" %
                      (ch + 1, len(got), len(want), "ok" if ok_p else "DIFFER: got %s" % [g[1] for g in got][:16], dev))
        g3 = cap.notes(ch=2, b_ms=bar - 5)
        gaps = [b[0] - a_[0] for a_, b in zip(g3, g3[1:])]
        rep.check(len(gaps) >= 6 and all(gaps[i + 1] < gaps[i] for i in range(len(gaps) - 1)),
                  "EXPO RAMP on track 3: the gaps shrink through the bar (%s)" % [round(x) for x in gaps])
        ons, offs = cap.notes(), cap.offs()
        rep.check(len(ons) == len(offs), "every note-on has a note-off (%d on, %d off)" % (len(ons), len(offs)))
        late = [n for n in cap.notes() if cap.stop is not None and n[0] > cap.rel(cap.stop) + 5]
        rep.check(not late, "no note after STOP (%d)" % len(late))

    # MUTE track 1 from the remote: a bar of silence on channel 1, then back
    mt = exp["mute_test"]
    ev = play_for(ctl, syn, 6 * bar / 1000.0 + 0.05,
                  during=[(mt["mute_at_bar"] * bar / 1000.0, lambda: remote(ctl, CC_MUTE0)),
                          (mt["unmute_at_bar"] * bar / 1000.0, lambda: remote(ctl, CC_MUTE0))])
    cap = Capture(ev)
    rep.raw("MUTE test", syn, ev, cap.start)
    if cap.start is not None:
        bars_with = sorted(set(int(n[0] // bar) for n in cap.notes(ch=0, b_ms=6 * bar - 5)))
        rep.check(bars_with == mt["ch1_bars_with_notes"], "MUTE track 1 at bar %.1f, back at %.1f: channel 1 plays in bars %s (expected %s)" %
                  (mt["mute_at_bar"], mt["unmute_at_bar"], bars_with, mt["ch1_bars_with_notes"]))
    else:
        rep.check(False, "MUTE test: no Start")

    # TEMPO from the remote
    tt = exp["tempo_test"]
    n = tt["presses"]
    def up():
        for _ in range(n):
            remote(ctl, CC_TEMPO_UP)
    def down():
        for _ in range(n):
            remote(ctl, CC_TEMPO_DN)
    ev = play_for(ctl, syn, 5 * bar / 1000.0 + 0.05, during=[(1.0 * bar / 1000.0, up), (3.0 * bar / 1000.0, down)])
    cap = Capture(ev)
    rep.raw("TEMPO test", syn, ev, cap.start)
    if cap.start is not None:
        b_up, b_dn = cap.bpm(1.5 * bar, 2.8 * bar), cap.bpm(3.6 * bar, 4.8 * bar)
        rep.check(abs(b_up - tt["bpm_after_up"]) <= 1.5 and abs(b_dn - tt["bpm_after_down"]) <= 1.5,
                  "TEMPO +%d then -%d: %.1f then %.1f BPM (expected %d, %d)" % (n, n, b_up, b_dn, tt["bpm_after_up"], tt["bpm_after_down"]))
    else:
        rep.check(False, "TEMPO test: no Start")

    # EXPORT while playing is refused
    syn.take()
    remote(ctl, CC_PLAY)
    time.sleep(0.3)
    img, st = export(ctl, timeout=1.5)
    remote(ctl, CC_PLAY)
    time.sleep(0.3)
    rep.check(img is None and st == "BUSY", "EXPORT while playing is refused (%s)" % st)

    # RESTORE
    if backup:
        st = import_image(ctl, backup)
        rep.check(st == "OK", "RESTORE: your project is back in memory (%s); the FM-1 says IMPORTED: SAVE TO KEEP IT" % st)
    rep.say("")
    rep.say("%d checks, %d failed, %d warnings" % (rep.n, len(rep.fails), len(rep.warns)))
    for w in rep.fails:
        rep.say("  FAIL: " + w)
    for w in rep.warns:
        rep.say("  WARN: " + w)
    rep.say("log: %s" % rep.f.name)
    rep.close()
    for p in ports:
        p.link.close()
    return 0 if not rep.fails else 1


if __name__ == "__main__":
    sys.exit(main())
