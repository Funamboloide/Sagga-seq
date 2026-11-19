#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA SEQ 0.11: the Windows runner of the explorer on the FM-1 (tools/hwtest/sagga_hw_explore.py) against a fake
FM-1 that speaks the test's SysEx (firmware/src/sagga_test.c): the consent, the reboots (the ports go and come back),
the paced events and their answers, probes and logs that lose pieces on the way (AGAIN, TAKEN), a hand that stops it,
the project back at the end. The firmware's side of the same protocol is tested in the simulator (t011_pc_test)."""
import os
import random
import sys
import tempfile
import threading
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "hwtest"))
import sagga_testport as T      # noqa: E402
import sagga_hw_explore as R    # noqa: E402
import fm1_install as FI        # noqa: E402

CHECKS, FAILS = [0], []


def check(cond, what):
    CHECKS[0] += 1
    if not cond:
        FAILS.append(what)
        print("  FAIL:", what)


class FakeFM1:
    """the FM-1 as the PC sees it over USB: one port, its own ms, the test's state machine"""
    def __init__(self, lose=0.0, abort_in_session=None, seed=3, two_ports=False, version="0.18.1"):
        self.version = version
        self.rnd = random.Random(seed)
        self.two = two_ports                 # (as the user's: the answers come back on the second port, MIDIIN2)
        self.links, self.open_ends = {}, {}
        self.lose, self.abort_in = lose, abort_in_session
        self.up_at = 0.0                     # perf_counter when it is on the USB again
        self.link = None
        self.boot_t = time.perf_counter()
        self.booted = 0
        self.state = 0
        self.project = b"SGQB" + bytes(range(200))
        self.imported = []
        self.opens = self.boots = self.closes = self.sessions = 0
        self.q, self.go_t, self.presi, self.kept = [], None, {}, {}
        self.lock = threading.Lock()
        threading.Thread(target=self._run, daemon=True).start()

    def ms(self):
        return int((time.perf_counter() - self.boot_t) * 1000)

    def connected(self):
        return time.perf_counter() >= self.up_at

    def out(self, data):
        cable = 1 if self.two and data[0] == 0xF0 else 0
        link = self.links.get(cable)
        if link and link.on_message and self.connected():
            link.on_message(bytes(data), time.perf_counter())

    def ans(self, sub, payload):
        self.out(T.HEAD + [T.SX_TST_ANS, sub] + list(payload) + [0xF7])

    def reboot(self, test):
        def later():                         # (as the FM-1: 80 ms after its answer it is gone from the USB)
            self.booted, self.state = (1, 2) if test else (0, 0)
            self.up_at = time.perf_counter() + 1.0
            self.boot_t = time.perf_counter()
            self.q, self.go_t = [], None
            self.links = {}
        threading.Timer(0.08, later).start()

    def rx(self, data):
        m = list(data)
        if m[:4] != T.HEAD:
            return
        cmd, p = m[4], m[5:-1]
        if cmd == 0x01:                      # EXPORT
            packed = FI.pack7(self.project)
            self.out(T.HEAD + [0x02, 0, 0, 1, 0] + list(packed) + [sum(packed) & 127, 0xF7])
            crc, n = zlib.crc32(self.project), len(self.project)
            self.out(T.HEAD + [0x03, n & 127, (n >> 7) & 127, (n >> 14) & 127] + T.put7(crc, 5) + [0xF7])
            return
        if cmd == 0x02:                      # IMPORT chunk
            self.imported.append(bytes(FI.unpack7(p[4:-1])))
            self.out(T.HEAD + [0x10, 0, 0xF7])
            return
        if cmd == 0x03:
            self.out(T.HEAD + [0x10, 0, 0xF7])
            return
        if cmd != T.SX_TST:
            return
        sub, q = p[0], p[1:]
        if sub == T.HELLO:
            self.ans(T.HELLO, [self.state, self.booted, 0] + T.put7(self.boots, 2) + [0] * 10 + T.put7(self.ms(), 4) + [1, 0] + list(self.version.encode()))
        elif sub == T.OPEN:
            self.opens += 1
            self.ans(T.OPEN, [1])
            threading.Timer(0.3, self._yes).start()
        elif sub == T.BOOT:
            if self.state == 2 or self.booted:
                self.ans(T.BOOT, [1])
                self.boots += 1
                self.reboot(True)
            else:
                self.ans(T.BOOT, [0])
        elif sub == T.GO:
            with self.lock:
                self.go_t, self.q, self.presi, self.kept = self.ms(), [], {}, {}
                self.next = 0
                self.sessions += 1
            self.ans(T.GO, T.put7(self.go_t, 4))
        elif sub == T.EV:
            idx, n = T.get7(q[0:2]), q[2]
            with self.lock:
                ok = idx == self.next and len(self.q) + n <= T.QUEUE
                if ok:
                    for i in range(n):
                        s = q[3 + 13 * i: 16 + 13 * i]
                        self.q.append((idx + i, T.get7(s[0:4]), s[4]))
                    self.next += n
                if self.rnd.random() < self.lose:          # an answer lost: the PC sends the frame again
                    return
                self.ans(T.EV, [1 if ok else 0] + T.put7(self.next, 2) + [T.QUEUE - len(self.q)])
        elif sub == 6:                                     # AGAIN
            i = T.get7(q[0:2])
            if i in self.kept:
                self._send_probe(i, self.kept[i], lose=False)
        elif sub == 7:                                     # TAKEN
            i, n = T.get7(q[0:2]), q[2]
            ent = [(k,) + tuple(self.presi[k]) for k in range(i, i + n) if k in self.presi]
            self._send_log(ent, lose=False)
        elif sub == T.CLOSE:
            self.closes += 1
            if self.booted:
                self.ans(T.CLOSE, [1])
                self.reboot(False)
            else:
                self.ans(T.CLOSE, [0])

    def _yes(self):
        self.state = 2
        self.ans(T.OPEN, [2])

    def _send_log(self, ent, lose=True):
        for k in range(0, len(ent), 12):
            part = ent[k:k + 12]
            if lose and self.rnd.random() < self.lose:
                continue
            body = [len(part)]
            for idx, ms, gc in part:
                body += T.put7(idx, 2) + T.put7(ms, 4) + T.put7(gc, 4)
            self.out(T.HEAD + [T.SX_TST_LOG] + body + [0xF7])

    def _send_probe(self, idx, text, lose=True):
        pieces = [text[i:i + 150] for i in range(0, len(text), 150)]
        for k, piece in enumerate(pieces):
            if lose and self.rnd.random() < self.lose:
                continue
            self.out(T.HEAD + [T.SX_TST_PROBE] + T.put7(idx, 2) + [k, 1 if k == len(pieces) - 1 else 0] + list(piece.encode()) + [0xF7])

    def _run(self):
        while True:
            time.sleep(0.002)
            if not self.connected() or self.go_t is None:
                continue
            now = self.ms()
            taken = []
            with self.lock:
                while self.q and now >= self.go_t + self.q[0][1]:
                    taken.append(self.q.pop(0))
            for idx, t, kind in taken:
                self.presi[idx] = (now, now // 20)
                if kind == T.PROBE:
                    play = "1"
                    text = "PROBE G play=%s msg=\nPROBE T1 ok=1 step=%d\nPROBE H lag=3 ms=%d\n" % (play, idx, now) + "x" * 400 + "\n"
                    self.kept[idx] = text
                    if len(self.kept) > 2:
                        del self.kept[min(self.kept)]
                    self._send_probe(idx, text)
                if self.abort_in == self.sessions and idx == 5:
                    self.ans(T.ABORT, [1])
                    self.go_t = None
                    break
                if kind == T.END:
                    ent = sorted((k,) + v for k, v in self.presi.items())
                    self._send_log(ent[-12:])
                    self.ans(T.DONE, T.put7(len(self.presi), 2) + T.put7(0, 2) + T.put7(3, 2) + [0])
            if taken and self.go_t is not None:
                self._send_log([(i,) + self.presi[i] for i, _, _ in taken])
            for _ in range(int(self.rnd.random() * 2)):
                self.out(bytes([0x90, 60, 100]))
                self.out(bytes([0x80, 60, 0]))


class CountMixin:
    """0.23.1 on a fake FM-1: it counts what it sends by port and kind and says it (DIAG, its 16 more numbers); QUIET
    stops it for good. eat = {(port index, kind): n}: messages it counts as sent that never reach the computer"""
    def count_init(self, eat=None):
        self.version = "0.23.1"
        self.sent = [T.Tally(), T.Tally()]
        self.eat = dict(eat or {})
        self.quiets = 0

    def _deliver(self, cable, data):
        link = self.links.get(cable)
        if not (link and link.on_message and self.connected()):
            return
        self.sent[cable].add(bytes(data))
        k = T.out_kind(bytes(data))
        if k and self.eat.get((cable, k), 0) > 0:
            self.eat[(cable, k)] -= 1                 # (counted, and never there)
            return
        link.on_message(bytes(data), time.perf_counter())

    def out(self, data):
        self._deliver(1 if self.two and data[0] == 0xF0 else 0, data)

    def out2(self, data):
        self._deliver(1, data)

    def rx(self, data):
        m = list(data)
        test = m[:4] == T.HEAD and len(m) > 6 and m[4] == T.SX_TST and not getattr(self, "deaf_now", False)
        if test and m[5] == T.DIAG:
            v = dict.fromkeys(T.DIAG_FIELDS + T.DIAG_MORE, 0)
            v.update(hellos=getattr(self, "hellos", 1), frames=getattr(self, "hellos", 1) + 1, first_ms=40, resets=1, configs=1, cfg_ms=350, ms=self.ms())
            for i in (0, 1):
                for k in T.OUT_KINDS:
                    v["p%d_%s" % (i + 1, k)] = self.sent[i].n[k]
            v["tx_ev"] = sum(self.sent[i].n[k] for i in (0, 1) for k in T.OUT_KINDS[:5])
            self.ans(T.DIAG, sum((T.put7(v[k], 4) for k in T.DIAG_FIELDS + T.DIAG_MORE), []))
            return
        if test and m[5] == T.QUIET:
            self.quiets += 1
            self.go_t = None                          # (stopped: not a note more)
            self.ans(T.QUIET, [1])
            return
        super().rx(data)


class CountFM1(CountMixin, FakeFM1):
    def __init__(self, eat=None, **kw):
        super().__init__(**kw)
        self.count_init(eat)


class FakeEnd:
    """an input or output of the Windows driver (WinMM), as the user's PC showed it: one opener at a time ("error
    creating Windows MM MIDI ... port" while another handle is open, a handle to the FM-1 from before its reboot too,
    until it is closed); an input closed while its device is gone hangs for ever (the first run); an output closed
    then just goes"""
    def __init__(self, dev, kind, cable):
        key = (kind, cable)
        if dev.open_ends.get(key) is not None:
            raise IOError("Midi%sWinMM::openPort: error creating Windows MM MIDI %s port." % (
                "In" if kind == "in" else "Out", "input" if kind == "in" else "output"))
        self.dev, self.kind, self.key, self.gen, self.callback = dev, kind, key, dev.boot_t, None
        dev.open_ends[key] = self

    def close(self):
        time.sleep(0.05)
        if self.kind == "in" and (not self.dev.connected() or self.dev.boot_t != self.gen):
            threading.Event().wait()
        if self.dev.open_ends.get(self.key) is self:
            del self.dev.open_ends[self.key]


class FakeLink:
    def __init__(self, dev, cable):
        self.dev, self.cable, self.on_message = dev, cable, None
        self.inp = FakeEnd(dev, "in", cable)
        try:
            self.out = FakeEnd(dev, "out", cable)
        except IOError:
            self.inp.close()
            raise
        dev.links[cable] = self

    def send(self, data):
        if not self.dev.connected() or self.dev.links.get(self.cable) is not self:
            raise IOError("the device is gone")
        self.dev.rx(bytes(data))

    def close(self):
        self.inp.close()
        self.out.close()


class FakeBackend:
    def __init__(self, dev):
        self.dev = dev

    def input_names(self):
        if not self.dev.connected():
            return []
        return ["Felucca 0", "MIDIIN2 (Felucca) 1", "StudioRack 2"] if self.dev.two else ["Felucca 0"]

    def output_names(self):
        if not self.dev.connected():
            return []
        return ["Felucca 1", "MIDIOUT2 (Felucca) 2", "StudioRack 3"] if self.dev.two else ["Felucca 1"]

    def open(self, i, o):
        if not self.dev.connected():
            raise IOError("no device")
        return FakeLink(self.dev, 1 if i.startswith("MIDIIN2") else 0)


def fake_rtmidi(dev):
    """a python-rtmidi module whose ports are the fake FM-1's (the runner's own backend, RtBackend, through it)"""
    import types
    mod = types.ModuleType("rtmidi")
    mod.live, mod.most = 0, 0                    # 0.20.6: the ALSA clients alive now, and the most at once

    def born():
        mod.live += 1
        mod.most = max(mod.most, mod.live)

    class _Client:
        def delete(self):
            if not getattr(self, "_gone", False):
                self._gone = True
                mod.live -= 1

    class _Feed:
        def __init__(self, q):
            self.q = q

        def on_message(self, data, t):
            self.q.append(list(data))

    class MidiIn(_Client):
        def __init__(self, queue_size_limit=1024):
            self.q, self.gen = [], None
            born()

        def get_ports(self):
            return FakeBackend(dev).input_names()

        def ignore_types(self, **kw):
            pass

        def open_port(self, i):
            name = self.get_ports()[i]
            cable = 1 if name.startswith("MIDIIN2") else 0
            self.end = FakeEnd(dev, "in", cable)
            dev.links[cable] = _Feed(self.q)

        def get_message(self):
            return (self.q.pop(0), 0.0) if self.q else None

        def close_port(self):
            self.end.close()

    class MidiOut(_Client):
        def __init__(self):
            self.gen = None
            born()

        def get_ports(self):
            return FakeBackend(dev).output_names()

        def open_port(self, i):
            self.gen = dev.boot_t
            self.end = FakeEnd(dev, "out", 1 if self.get_ports()[i].startswith("MIDIOUT2") else 0)

        def send_message(self, m):
            if not dev.connected() or dev.boot_t != self.gen:
                raise IOError("the device is gone")
            dev.rx(bytes(m))

        def close_port(self):
            self.end.close()
    mod.MidiIn, mod.MidiOut = MidiIn, MidiOut
    return mod


def plan(n=2, midi=False):
    ses = []
    for k in range(n):
        ev = [[100, T.PROBE, 0, 0]]
        for j in range(30):
            ev.append([150 + 40 * j, T.PRESS, 3, 0])
            ev.append([165 + 40 * j, T.RELEASE, 3, 0])
        if midi:                             # (0.18: a command of the tablet, as a MIDI event)
            ev.append([1450, T.MIDI] + list(T.midi_ev(0xBB, 20, 1)))
        ev += [[1500, T.PROBE, 0, 0], [1900, T.PROBE, 0, 0], [2000, T.END, 0, 0]]
        ses.append({"nome": "s%03d" % (k + 1), "situazione": "vuoto, fermo", "gesti": ["tocca SEL"] * 30, "eventi": ev,
                    "sonde": ["inizio", "battuta", "fermo"]})
    return {"versione": 1, "firmware": "0.18.1", "sessioni": ses}


def run(dev, n=2, backend=None, midi=False):
    with tempfile.TemporaryDirectory() as d:
        pp = os.path.join(d, "piano.json")
        T.save(pp, plan(n, midi))
        rc = R.main([pp, "--si", "--out", d], backend=backend or FakeBackend(dev), wait=lambda s: time.sleep(min(s, 1.2)))
        rac = [f for f in os.listdir(d) if f.startswith("raccolta-")]
        data = T.load(os.path.join(d, rac[0])) if rac else None
        log = open(os.path.join(d, [f for f in os.listdir(d) if f.startswith("hwexplore-")][0])).read()
        backups = [f for f in os.listdir(d) if f.startswith("backup-")]
    return rc, data, log, backups


def rules_of_the_comparison():
    """the comparison forgives timing (a step's edge, a message's last ms, a key read a few ms later), not a difference
    that stays: one session played by the simulator as the FM-1, then its probes touched"""
    import copy
    import re
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import sagga_explore_hw as H
    H.E.build()
    plan = H.piano(1, 14, 5)["sessioni"][0]
    s0 = H.run_like_fm1(plan, lcdcost=False)
    errs = lambda f: [x for x in f if x[1] == "ERRORE"]
    f, _ = H.compare(s0)
    check(not errs(f), "the simulator against itself: no error (%s)" % errs(f)[:1])
    idx = [i for i, _ in H.probe_events(s0)]
    k = idx[len(idx) // 2]

    def touched(fn, keys):
        s = copy.deepcopy(s0)
        for i in keys:
            s["fm1"]["sonde"][str(i)] = fn(s["fm1"]["sonde"][str(i)])
        return errs(H.compare(s)[0])
    # a pattern that stays different from the middle on: an error
    e = touched(lambda t: re.sub(r"(PROBE T2 [^\n]*?steps#=)([0-9A-F]{8})", lambda m: m.group(1) + "DEADBEEF", t), [i for i in idx if i >= k])
    check(e and e[0][0] == "SIMULATORE" and "steps#" in e[0][2], "a pattern different from the middle on: SIMULATORE (%s)" % e[:1])
    # a step one on at one probe only: the edge of a step, no error
    def step_on(t):
        return re.sub(r"(PROBE T(\d+) [^\n]*?len=(\d+)[^\n]*? step=)(\d+)", lambda m: m.group(1) + str((int(m.group(4)) + 1) % int(m.group(3))), t)
    e = touched(step_on, [k])
    check(not e, "every track one step on at one probe only: timing, no error (%s)" % e[:1])
    # a step one on from the middle to the end: not timing
    e = touched(step_on, [i for i in idx if i >= k and i != idx[-1]])
    check(e and e[0][0] == "SIMULATORE", "the steps one on from the middle to the end: SIMULATORE (%s)" % e[:1])
    # 0.20.9: the steps one on with the probe read a tick later (its gc), at three probes, then another difference: that
    # one is the first, not the steps (the FM-1 completo's s006); the steps and the tick one on to the end: an error
    def tick_on(t):
        return re.sub(r"(PROBE H [^\n]*?gc=)(\d+)", lambda m: m.group(1) + str(int(m.group(2)) + 1), step_on(t))
    pos = idx.index(k)
    roles = dict(H.probe_events(s0))
    s3 = copy.deepcopy(s0)
    for i in idx[pos:pos + 3]:
        s3["fm1"]["sonde"][str(i)] = tick_on(s3["fm1"]["sonde"][str(i)])
    for i in idx[pos + 3:]:
        s3["fm1"]["sonde"][str(i)] = re.sub(r"(PROBE T2 [^\n]*?steps#=)([0-9A-F]{8})", lambda m: m.group(1) + "DEADBEEF", s3["fm1"]["sonde"][str(i)])
    e = errs(H.compare(s3)[0])
    check(e and "'%s'" % roles[idx[pos + 3]] in e[0][2] and "steps#" in e[0][2],
          "the steps and the tick one on at three probes, then a pattern: the pattern's probe is the first (%s)" % e[:1])
    e = touched(tick_on, idx[pos:])
    check(e and e[0][0] == "SIMULATORE" and "'%s'" % roles[k] in e[0][2], "the steps and the tick one on to the end: SIMULATORE (%s)" % e[:1])
    # the message still on one side: no error; two different messages: an error
    km = [i for i in idx if re.search(r"msg=[^\n]", s0["fm1"]["sonde"][str(i)])]
    km = km[len(km) // 2] if km else k
    e = touched(lambda t: re.sub(r"msg=[^\n]*", "msg=", t), [km])
    e2 = touched(lambda t: re.sub(r"msg=[^\n]*", "msg=SOMETHING ELSE", t), [km])
    check(not e and e2 and "G.msg" in e2[0][2], "a message gone on one side: timing; another message: an error (%s / %s)" % (e[:1], e2[:1]))
    # 0.13: a track's "ok" that one side could not ask ("-") at one probe: timing; from the middle to the end: an error
    # ("vuoto, in play": a track is asked; 0.28: the first seed whose session asks a track to its last probe - with
    # ENV's eight pages the catalog's gestures changed, and seed 5's session stopped the music half way)
    for seed in range(5, 40):
        sp = H.run_like_fm1(H.piano(2, 14, seed)["sessioni"][1], lcdcost=False)
        idp = [i for i, _ in H.probe_events(sp)]
        asked = {t: [i for i in idp if re.search(r"PROBE T%d [^\n]*? ok=[01]" % t, sp["fm1"]["sonde"][str(i)])] for t in range(1, 13)}
        tk = max(asked, key=lambda t: len(asked[t]))
        has_ok = asked[tk]
        if len(has_ok) >= 6 and has_ok[-1] == idp[-1]:
            break

    def ok_dash(t):
        return re.sub(r"(PROBE T%d [^\n]*? ok=)[01]" % tk, lambda m: m.group(1) + "-", t)
    ko = has_ok[len(has_ok) // 2] if has_ok else idp[0]

    def touched_play(fn, keys):
        s = copy.deepcopy(sp)
        for i in keys:
            s["fm1"]["sonde"][str(i)] = fn(s["fm1"]["sonde"][str(i)])
        return errs(H.compare(s)[0])
    e = touched_play(ok_dash, [ko])
    e2 = touched_play(ok_dash, [i for i in has_ok if i >= ko])
    check(len(has_ok) > 2 and not e and e2 and "T%d.ok" % tk in e2[0][2], "T%d ok '-' at one probe: timing; to the end: an error (%s / %s)" % (tk, e[:1], e2[:1]))
    # 0.13: the FM-1's boot message still on at the first probe (PC TEST ...): not COSTRUZIONE, and G.msg still compared
    i0 = idx[0]
    s1 = copy.deepcopy(s0)
    s1["fm1"]["sonde"][str(i0)] = re.sub(r"msg=[^\n]*", "msg=PC TEST: A HAND ON A KEY STOPS IT", s1["fm1"]["sonde"][str(i0)])
    f1 = H.compare(s1)[0]
    s2 = copy.deepcopy(s1)
    s2["fm1"]["sonde"][str(km)] = re.sub(r"msg=[^\n]*", "msg=SOMETHING ELSE", s2["fm1"]["sonde"][str(km)])
    f2 = errs(H.compare(s2)[0])
    check(not [x for x in f1 if x[0] == "COSTRUZIONE"] and not errs(f1) and f2 and "G.msg" in f2[0][2],
          "the boot message at the first probe: no COSTRUZIONE, and a later message still compared (%s / %s)" % (f1[:1], f2[:1]))


def rules_027():
    """After 0.27, what the comparison learnt from the 0.27 banco and FM-1 completo on the real FM-1: a probe read a clock
    tick apart, whatever it shows, equal again at the very next probe (s021, b020); a polyrhythm's step one apart for
    probes in a row, equal again later (b024); the notes of the window's last 40 ms (b007). And still an error when the
    difference stays."""
    import copy
    import re
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import sagga_explore_hw as H
    H.E.build()
    errs = lambda f: [x for x in f if x[1] == "ERRORE"]
    plan = H.piano(1, 14, 5)["sessioni"][0]
    s0 = H.run_like_fm1(plan, lcdcost=False)
    idx = [i for i, _ in H.probe_events(s0)]
    k = idx[len(idx) // 2]
    pos = idx.index(k)

    def touched(base, fn, keys):
        s = copy.deepcopy(base)
        for i in keys:
            s["fm1"]["sonde"][str(i)] = fn(s["fm1"]["sonde"][str(i)])
        return errs(H.compare(s)[0])

    def tick_mac(t):                                   # (the probe a tick later, and a THROW's macro a step on)
        t = re.sub(r"(PROBE H [^\n]*?gc=)(\d+)", lambda m: m.group(1) + str(int(m.group(2)) + 1), t)
        return re.sub(r"(PROBE G [^\n]*?mac=)([^ \n]*)", lambda m: m.group(1) + "0/0/0/-10", t)
    e = touched(s0, tick_mac, [k])
    e2 = touched(s0, tick_mac, [k, idx[pos + 1]])
    e3 = touched(s0, lambda t: re.sub(r"(PROBE G [^\n]*?mac=)([^ \n]*)", lambda m: m.group(1) + "0/0/0/-10", t), [k])
    check(not e and e2 and e3 and "G.mac" in e3[0][2],
          "a probe read a tick apart with the macro a step on, equal at the next: timing; at two probes, or without the tick: "
          "an error (%s / %s / %s)" % (e[:1], e2[:1], e3[:1]))
    # the polyrhythm (track 5 at 1/16 7:4)
    sit = next(x for x in H.E.SITUAZIONI if x.name.startswith("0.25 i poliritmi"))
    by = {g.name: g for g in H.E.catalogo(veloce=True)}
    gs = [g for g in by.values() if H.gesture_ok(g)][:10]
    sp = H.run_like_fm1(H.session_plan(sit, gs, "p001"), lcdcost=False)
    ip = [i for i, _ in H.probe_events(sp)]
    f0 = errs(H.compare(sp)[0])
    t5 = [i for i in ip if re.search(r"PROBE T5 [^\n]*? div=1[3-8] ", sp["fm1"]["sonde"][str(i)])]

    def t5_on(t):
        return re.sub(r"(PROBE T5 [^\n]*?len=(\d+)[^\n]*? step=)(\d+)", lambda m: m.group(1) + str((int(m.group(3)) + 1) % int(m.group(2))), t)
    mid = len(ip) // 3
    e = touched(sp, t5_on, ip[mid:mid + 5])
    e2 = touched(sp, t5_on, ip[mid:-1])
    def t2_on(t):
        return re.sub(r"(PROBE T2 [^\n]*?len=(\d+)[^\n]*? step=)(\d+)", lambda m: m.group(1) + str((int(m.group(3)) + 1) % int(m.group(2))), t)
    e3 = touched(sp, t2_on, ip[mid:mid + 5])
    check(not f0 and len(t5) >= len(ip) - 2 and not e and e2 and e3,
          "track 5 at 7:4 one step on for five probes, equal later: timing; to the end: an error; a plain track (T2) five "
          "probes: an error (%s %s / %s / %s / %s)" % (f0[:1], len(t5), e[:1], e2[:1], e3[:1]))
    # the notes at the window's end: the FM-1's last 30 ms of MIDI not heard (the Pi closed its ports) - the band, its
    # MIDI as the runner keeps it (from the FM-1's GO; the simulator as the FM-1 keeps its own ms)
    s0 = copy.deepcopy(sp)
    s0["fm1"]["midi"] = [[m[0] - sp["fm1"]["go_ms"]] + list(m[1:]) for m in sp["fm1"]["midi"]]
    f00 = [x for x in H.compare(s0)[0] if x[0] in ("NOTE", "PERSI")]
    s1 = copy.deepcopy(s0)
    midi = s1["fm1"]["midi"]
    ons = [m for m in midi if (m[1] & 0xF0) == 0x90 and m[3]]
    steps = sorted(set(m[0] for m in ons))
    many = [t for t in steps if sum(1 for m in ons if m[0] == t) >= 2]
    cut = many[-1] if many else steps[-1]
    s1["fm1"]["midi"] = [m for m in midi if m[0] < cut - 25]
    last = s1["fm1"]["midi"][-1][0]
    f1 = [x for x in H.compare(s1)[0] if x[0] == "NOTE"]
    s2 = copy.deepcopy(s0)
    s2["fm1"]["midi"] = [m for m in midi if not ((m[1] & 0xF0) == 0x90 and m[3] and m[0] in steps[len(steps) // 2:len(steps) // 2 + 2])]
    f2 = [x for x in H.compare(s2)[0] if x[0] in ("NOTE", "PERSI")]
    check(not f00 and many and cut - last <= 40 and not f1 and f2, "a step of notes just after the last message heard: the window's "
          "edge; notes gone in the middle: still found (%s / %s / %s)" % (f00[:1], f1[:1], f2[:1]))


def counts_account():
    """0.23.1: the session's account - DIAG's 16 more numbers, the tally of a port, the verdict that says where"""
    base = [0] * len(T.DIAG_FIELDS)
    more = list(range(1, len(T.DIAG_MORE) + 1))
    frame = lambda nums: bytes(T.HEAD + [T.SX_TST_ANS, T.DIAG] + sum((T.put7(x, 4) for x in nums), []) + [0xF7])
    old, new = T.parse(frame(base)), T.parse(frame(base + more))
    check(old[0] == "diag" and len(old[1]) == len(T.DIAG_FIELDS) and "p1_ticks" not in old[1], "DIAG of an FM-1 before 0.23.1: its 19 numbers")
    check(new[1]["p1_ticks"] == 1 and new[1]["p1_bytes"] == 6 and new[1]["p2_ticks"] == 7 and new[1]["tx_ev"] == 13 and new[1]["tx_ring"] == 16,
          "DIAG from 0.23.1: 16 more, by name (%s)" % {k: new[1][k] for k in T.DIAG_MORE})
    check(T.parse(bytes(T.HEAD + [T.SX_TST_ANS, T.QUIET, 1, 0xF7])) == ("quiet", 1) and list(T.quiet()) == T.HEAD + [T.SX_TST, T.QUIET, 0xF7], "QUIET and its answer")
    tl = T.Tally()
    for m in ([0xF8], [0x90, 60, 100], [0x90, 60, 0], [0x80, 61, 0], [0xB3, 7, 1], [0xE0, 0, 64], [0xC1, 5], [0xFA], [0xF0, 0x7D, 1, 2, 0xF7]):
        tl.add(bytes(m))
    check(tl.snapshot() == {"ticks": 1, "on": 1, "off": 2, "cc": 1, "other": 3, "bytes": 1 + 3 + 3 + 3 + 3 + 3 + 2 + 1 + 5},
          "a port's tally: a note-on of velocity 0 is a note-off, START and the rest are 'other', a SysEx only its bytes (%s)" % tl.snapshot())
    k0 = dict(ticks=2414, on=1200, off=1200, cc=300, other=4, bytes=2414 + 3 * 2700 + 4)
    z = dict.fromkeys(T.OUT_KINDS, 0)
    usb = dict(tx_ev=5118, tx_drop=0, tx_noconf=0, tx_flush=0, tx_pkts=4000, resets=0, configs=0, suspends=0, tx_ring=0, tx_ring_prima=0, tx_wait_max=3)

    def acc(heard, fermo=(True, True), usb_=None, alsa=None):
        return {"fermo": list(fermo), "attesa": 0.4, "quiet": 1, "fm1": {"p1": dict(k0), "p2": dict(z)}, "pi": {"p1": dict(k0, **heard), "p2": dict(z)},
                "usb": dict(usb, **(usb_ or {})), "alsa": alsa}
    V = R.counts_verdict
    check(V(None) == [] and V(acc({})) == [], "nothing asked, or the same numbers: nothing said")
    v = V(acc({"ticks": 2411}))
    check(len(v) == 2 and v[0] == "porta 1: l'FM-1 ha mandato 3 tick del clock che il programma non ha sentito" and "persi dopo l'FM-1" in v[1],
          "three ticks sent and not heard, no driver counts: after the FM-1 (%s)" % v)
    v = V(acc({"ticks": 2411, "off": 1198}, alsa={"rx": [k0["bytes"], 0], "over": [0, 0], "pool": 0}))
    check(len(v) == 2 and "3 tick del clock, 2 note-off" in v[0] and "ha ricevuto tutti i byte" in v[1] and "nel computer" in v[1],
          "the driver has every byte: lost in the computer, after the driver (%s)" % v)
    v = V(acc({"ticks": 2411}, alsa={"rx": [k0["bytes"] - 3, 0], "over": [0, 0], "pool": None}))
    check(len(v) == 2 and "mancano 3 byte sulla porta 1" in v[1] and "fra l'FM-1 e il computer" in v[1], "the driver is three bytes short: lost on the way (%s)" % v)
    v = V(acc({"ticks": 2411}, alsa={"rx": [k0["bytes"], 0], "over": [0, 0], "pool": 3}))
    check(any("ALSA ha scartato 3 eventi" in x for x in v), "ALSA's pool was full: said (%s)" % v)
    v = V(acc({"on": 1198}, usb_={"tx_ev": 5116, "tx_drop": 2}))
    check(any("dentro l'FM-1: 2 messaggi scartati" in x and "2 con l'anello pieno" in x for x in v) and not any("persi dopo" in x for x in v),
          "two dropped with the ring full: inside the FM-1 (%s)" % v)
    v = V(acc({"on": 1198}, usb_={"tx_ev": 5116}))
    check(any("i conti non tornano" in x for x in v), "the FM-1's own account does not add up: said (%s)" % v)
    v = V(acc({"ticks": 2411}, usb_={"resets": 1, "configs": 1}))
    check(any("1 reset del bus, 1 configurazioni" in x for x in v), "a bus reset in the session: said (%s)" % v)
    check(V(acc({"ticks": 2411}, fermo=(False, True))) == [], "a port that never stood still: its counts are not compared")
    v = V(acc({"cc": 303}))
    check(len(v) == 1 and "il programma ha sentito 3 CC in piu'" in v[0] and R.counts_missing(acc({"cc": 303})) == 0,
          "heard more than sent: said as it is, and nothing is missing (%s)" % v)
    check(R.counts_missing(acc({"ticks": 2411, "off": 1198})) == 5 and R.counts_missing(acc({"ticks": 2411}, fermo=(False, True))) == 0 and R.counts_missing(None) == 0,
          "how many are missing: on the ports that stood still")
    # the runner with an FM-1 that counts: every session has its account, equal on both sides; two notes lost: said
    for two in (False, True):
        dev = CountFM1(two_ports=two)
        rc, data, log, backups = run(dev)
        c = [x["fm1"].get("conti") for x in (data or {}).get("sessioni", [])]
        check(rc == 0 and len(c) == 2 and all(c) and all(x["fm1"] == x["pi"] and x["fermo"] == [True, True] and x["fm1"]["p1"]["on"] > 0 for x in c)
              and dev.quiets == 2 and "CONTI" not in log,
              "%s: both sessions with their account, sent = heard, QUIET asked (%s)" % ("two ports" if two else "one port", [(x["fm1"], x["pi"]) for x in c if x and x["fm1"] != x["pi"]][:1]))
        if c and c[0]:
            check((c[0]["fm1"]["p2"]["bytes"] > 500) == two and (c[0]["fm1"]["p1"]["bytes"] > 500), "... the test's SysEx bytes on port %d" % (2 if two else 1))
    dev = CountFM1(two_ports=True, eat={(0, "on"): 2})
    rc, data, log, backups = run(dev)
    c = [x["fm1"].get("conti") for x in (data or {}).get("sessioni", [])]
    lost = sum(x["fm1"]["p1"]["on"] - x["pi"]["p1"]["on"] for x in c if x)
    check(rc == 0 and lost == 2 and "CONTI: porta 1: l'FM-1 ha mandato" in log and "note che il programma non ha sentito" in log,
          "two note-ons counted by the FM-1 and never arrived: in the account and in the log (%s)" % [ln for ln in log.splitlines() if "CONTI" in ln][:1])
    dev = FakeFM1()                                      # (an FM-1 before 0.23.1: nothing asked)
    rc, data, log, backups = run(dev)
    check(rc == 0 and data and all("conti" not in x["fm1"] for x in data["sessioni"]), "an old FM-1: no account")


def main():
    print("sagga hw explore: the runner against a fake FM-1")
    counts_account()
    dev = FakeFM1()
    rc, data, log, backups = run(dev)
    check(rc == 0, "a clean run: 0 (%s)" % rc)
    check(dev.opens == 1 and dev.boots == 2 and dev.closes == 1, "one consent, a reboot a session, one CLOSE (%d %d %d)" % (dev.opens, dev.boots, dev.closes))
    check(backups and dev.imported and dev.imported[0] == dev.project, "the project kept before and put back after")
    check(data and len(data["sessioni"]) == 2, "both sessions in the collection")
    for s in (data or {}).get("sessioni", []):
        r = s["fm1"]
        check(len(r["presi"]) == len(s["eventi"]) and len(r["sonde"]) == 3 and r["done"], "%s: every event placed, every probe whole (%d %d)" % (s["nome"], len(r["presi"]), len(r["sonde"])))
        check(r["go_ms"] is not None and any(m[1] == 0x90 for m in r["midi"]), "%s: GO answered, the notes kept" % s["nome"])
    # as on the user's PC: two USB ports (the answers on MIDIIN2), a driver that hangs when closed after its device left
    dev = FakeFM1(two_ports=True)
    rc, data, log, backups = run(dev)
    check(rc == 0 and backups and dev.imported, "two ports: the project kept (EXPORT answered on MIDIIN2) and put back (%s)" % rc)
    check(data and len(data["sessioni"]) == 2 and all(len(s["fm1"]["sonde"]) == 3 for s in data["sessioni"]),
          "two ports: both sessions, every probe, no hang at the reboots")
    # the same through the runner's own backend (python-rtmidi without callbacks), here with a fake rtmidi module
    dev = FakeFM1(two_ports=True)
    saved = sys.modules.get("rtmidi")
    fake = fake_rtmidi(dev)
    sys.modules["rtmidi"] = fake
    try:
        rc, data, log, backups = run(dev, n=4, backend=R.default_backend())
    finally:
        if saved is not None:
            sys.modules["rtmidi"] = saved
        else:
            del sys.modules["rtmidi"]
    check(rc == 0 and backups and dev.imported and data and all(len(s["fm1"]["sonde"]) == 3 for s in data["sessioni"]),
          "python-rtmidi, polled: the same run, no hang (%s)" % rc)
    check(fake.live == 0 and fake.most <= 6, "0.20.6: every rtmidi client ended (an ALSA client each on Linux): none left "
          "after four sessions and their reconnects, at most %d at once (%d left)" % (fake.most, fake.live))
    # pieces lost on the way: AGAIN and TAKEN bring them back; lost answers: the frame again
    dev = FakeFM1(lose=0.15, seed=9)
    rc, data, log, _ = run(dev)
    recs = [s["fm1"] for s in data["sessioni"]] if data else []
    check(rc == 0 and len(recs) == 2, "with pieces lost: still a run (%s)" % rc)
    check(all(len(r["presi"]) == len(s["eventi"]) for r, s in zip(recs, data["sessioni"])), "every event's place, asked again where lost (%s)" % [len(r["presi"]) for r in recs])
    check(all(len(r["sonde"]) == 3 for r in recs), "every probe whole, asked again where a piece was lost (%s)" % [len(r["sonde"]) for r in recs])
    check(sum(r["di_nuovo"] for r in recs) > 0 and sum(r["rimandati"] for r in recs) > 0, "(it did ask again: %s probes, %s frames)" % ([r["di_nuovo"] for r in recs], [r["rimandati"] for r in recs]))
    # a hand on the FM-1: the run stops there, the project comes back
    dev = FakeFM1(abort_in_session=1)
    rc, data, log, _ = run(dev, n=3)
    check(data and len(data["sessioni"]) == 1 and data["sessioni"][0]["fm1"]["abort"] is not None, "a hand stops the run after that session")
    check(dev.closes == 1 and dev.imported, "and the FM-1 is put back")
    check("fermato da una mano" in log, "the log says why")
    # 0.18: a plan with the tablet's MIDI events wants a firmware that knows them: an older one is not touched
    dev = FakeFM1(version="0.17")
    rc, data, log, backups = run(dev, midi=True)
    check(rc == 3 and not data and not backups and dev.opens == 0 and "serve SAGGA SEQ 0.18.1" in log,
          "a plan with MIDI events and a 0.17 FM-1: refused before anything (%s)" % rc)
    dev = FakeFM1()
    rc, data, log, _ = run(dev, n=1, midi=True)
    check(rc == 0 and data and len(data["sessioni"]) == 1, "the same plan and a 0.18.1 FM-1: it runs (%s)" % rc)
    rules_of_the_comparison()
    rules_027()
    print("sagga hw explore: %d checks, %d failures" % (CHECKS[0], len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
