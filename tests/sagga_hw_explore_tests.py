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
import sagga_hw_test as HT      # noqa: E402
import fm1_install as FI        # noqa: E402

CHECKS, FAILS = [0], []


def check(cond, what):
    CHECKS[0] += 1
    if not cond:
        FAILS.append(what)
        print("  FAIL:", what)


class FakeFM1:
    """the FM-1 as the PC sees it over USB: one port, its own ms, the test's state machine"""
    def __init__(self, lose=0.0, abort_in_session=None, seed=3, two_ports=False):
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
            self.ans(T.HELLO, [self.state, self.booted, 0] + T.put7(self.boots, 2) + [0] * 10 + T.put7(self.ms(), 4) + [1, 0] + list(b"0.15"))
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

    class _Feed:
        def __init__(self, q):
            self.q = q

        def on_message(self, data, t):
            self.q.append(list(data))

    class MidiIn:
        def __init__(self, queue_size_limit=1024):
            self.q, self.gen = [], None

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

    class MidiOut:
        def __init__(self):
            self.gen = None

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


def plan(n=2):
    ses = []
    for k in range(n):
        ev = [[100, T.PROBE, 0, 0]]
        for j in range(30):
            ev.append([150 + 40 * j, T.PRESS, 3, 0])
            ev.append([165 + 40 * j, T.RELEASE, 3, 0])
        ev += [[1500, T.PROBE, 0, 0], [1900, T.PROBE, 0, 0], [2000, T.END, 0, 0]]
        ses.append({"nome": "s%03d" % (k + 1), "situazione": "vuoto, fermo", "gesti": ["tocca SEL"] * 30, "eventi": ev,
                    "sonde": ["inizio", "battuta", "fermo"]})
    return {"versione": 1, "sessioni": ses}


def run(dev, n=2, backend=None):
    with tempfile.TemporaryDirectory() as d:
        pp = os.path.join(d, "piano.json")
        T.save(pp, plan(n))
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
    # the message still on one side: no error; two different messages: an error
    km = [i for i in idx if re.search(r"msg=[^\n]", s0["fm1"]["sonde"][str(i)])]
    km = km[len(km) // 2] if km else k
    e = touched(lambda t: re.sub(r"msg=[^\n]*", "msg=", t), [km])
    e2 = touched(lambda t: re.sub(r"msg=[^\n]*", "msg=SOMETHING ELSE", t), [km])
    check(not e and e2 and "G.msg" in e2[0][2], "a message gone on one side: timing; another message: an error (%s / %s)" % (e[:1], e2[:1]))
    # 0.13: a track's "ok" that one side could not ask ("-") at one probe: timing; from the middle to the end: an error
    def ok_dash(t):
        return re.sub(r"(PROBE T3 [^\n]*? ok=)[01]", lambda m: m.group(1) + "-", t)
    sp = H.run_like_fm1(H.piano(2, 14, 5)["sessioni"][1], lcdcost=False)          # ("vuoto, in play": a track is asked)
    idp = [i for i, _ in H.probe_events(sp)]
    has_ok = [i for i in idp if re.search(r"PROBE T3 [^\n]*? ok=[01]", sp["fm1"]["sonde"][str(i)])]
    ko = has_ok[len(has_ok) // 2] if has_ok else idp[0]

    def touched_play(fn, keys):
        s = copy.deepcopy(sp)
        for i in keys:
            s["fm1"]["sonde"][str(i)] = fn(s["fm1"]["sonde"][str(i)])
        return errs(H.compare(s)[0])
    e = touched_play(ok_dash, [ko])
    e2 = touched_play(ok_dash, [i for i in has_ok if i >= ko])
    check(has_ok and not e and e2 and "T3.ok" in e2[0][2], "T3 ok '-' at one probe: timing; to the end: an error (%s / %s)" % (e[:1], e2[:1]))
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


def main():
    print("sagga hw explore: the runner against a fake FM-1")
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
    sys.modules["rtmidi"] = fake_rtmidi(dev)
    try:
        rc, data, log, backups = run(dev, backend=R.default_backend())
    finally:
        if saved is not None:
            sys.modules["rtmidi"] = saved
        else:
            del sys.modules["rtmidi"]
    check(rc == 0 and backups and dev.imported and data and all(len(s["fm1"]["sonde"]) == 3 for s in data["sessioni"]),
          "python-rtmidi, polled: the same run, no hang (%s)" % rc)
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
    rules_of_the_comparison()
    print("sagga hw explore: %d checks, %d failures" % (CHECKS[0], len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
