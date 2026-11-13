#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The hardware test program (tools/hwtest/sagga_hw_test.py) against a fake FM-1: two USB-MIDI ports named as
Windows names them, the updater's handshake, the project SysEx (export, import with acknowledgements, BUSY while
playing), the REMOTE on channel 14 (PLAY, MUTE, TEMPO), clock and notes from hwtest_expected.json. The fake plays at
four times the project's tempo (a scaled expected file) so the whole run takes seconds.

    python3 tests/sagga_hwtest_tests.py
"""
import json
import os
import sys
import tempfile
import threading
import time
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = os.path.join(ROOT, "tools", "hwtest")
sys.path.insert(0, HW)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fm1_install as FI                                   # noqa: E402

SPEED = 4


class FakeLink:
    def __init__(self, dev, cable):
        self.dev, self.cable, self.on_message = dev, cable, None

    def send(self, data):
        self.dev.rx(self.cable, bytes(data))

    def emit(self, data):
        if self.on_message:
            self.on_message(bytes(data), time.perf_counter())

    def close(self):
        pass


class FakeBackend:
    INS = ["Microsoft GS Wavetable Synth 0", "Felucca 1", "MIDIIN2 (Felucca) 2"]
    OUTS = ["Felucca 0", "MIDIOUT2 (Felucca) 1"]

    def __init__(self, dev):
        self.dev = dev

    def input_names(self): return list(self.INS)
    def output_names(self): return list(self.OUTS)

    def open(self, in_name, out_name):
        cable = 1 if "MIDIIN2" in in_name else 0
        link = FakeLink(self.dev, cable)
        self.dev.links[cable] = link
        return link


class FakeFM1:
    """SAGGA SEQ as the test sees it: control port = cable 1 (USB PORTS 2), synths on cable 0"""
    def __init__(self, image, exp):
        self.image, self.exp = image, exp
        self.links = {}
        self.playing = False
        self.bpm = exp["bpm"]
        self.mute = set()
        self.imp = None                                    # (chunks, cnt)
        self.thread = None
        self.lock = threading.Lock()
        self.log = []

    def out(self, cable, data):
        l = self.links.get(cable)
        if l:
            l.emit(data)

    def rx(self, cable, d):
        if d[0] == 0xF0:
            if d == FI.HS_QUERY:                           # the platform: any port
                ident = bytes([0, 0x59, 0x11, 0, 0, 0]) + b"FM-1_910".ljust(27, b"\0") + b"\0"
                self.out(cable, bytes([0xF0]) + bytes(FI.pack7(ident)) + bytes([0xF7]))
                return
            if cable != 1:
                return                                     # the app's SysEx: control port only
            if d[1:4] != b"\x7D\x53\x47":
                return
            self.app_sysex(d[4], d[5:-1])
            return
        if cable == 1 and (d[0] & 0xF0) == 0xB0 and (d[0] & 15) == 13 and d[2] >= 64:
            self.remote(d[1])

    def status(self, code, idx=0x3FFF):
        self.out(1, bytes([0xF0, 0x7D, 0x53, 0x47, 0x10, code, idx & 127, idx >> 7, 0xF7]))

    def app_sysex(self, cmd, body):
        if cmd == 0x01:
            if self.playing:
                self.status(1, 0)
                return
            img = self.image
            cnt = (len(img) + 255) // 256
            for i in range(cnt):
                packed = FI.pack7(img[i * 256:(i + 1) * 256])
                self.out(1, bytes([0xF0, 0x7D, 0x53, 0x47, 0x02, i & 127, i >> 7, cnt & 127, cnt >> 7]) + bytes(packed) + bytes([sum(packed) & 127, 0xF7]))
            crc, ln = zlib.crc32(img), len(img)
            self.out(1, bytes([0xF0, 0x7D, 0x53, 0x47, 0x03, ln & 127, (ln >> 7) & 127, (ln >> 14) & 127,
                               crc & 127, (crc >> 7) & 127, (crc >> 14) & 127, (crc >> 21) & 127, (crc >> 28) & 127, 0xF7]))
        elif cmd == 0x02:
            idx, cnt = body[0] | body[1] << 7, body[2] | body[3] << 7
            data, sm = body[4:-1], body[-1]
            if self.playing:
                self.imp = None; self.status(1, idx); return
            if sum(data) & 127 != sm:
                self.status(2, idx); return
            if idx == 0:
                self.imp = ({}, cnt)
            if not self.imp or idx != len(self.imp[0]) or cnt != self.imp[1]:
                self.status(3, idx); return
            self.imp[0][idx] = bytes(FI.unpack7(data))
            self.status(0, idx)
        elif cmd == 0x03:
            ln = body[0] | body[1] << 7 | body[2] << 14
            crc = (body[3] | body[4] << 7 | body[5] << 14 | body[6] << 21 | body[7] << 28) & 0xFFFFFFFF
            if not self.imp or len(self.imp[0]) != self.imp[1]:
                self.status(4); return
            img = b"".join(self.imp[0][i] for i in range(self.imp[1]))[:ln]
            self.imp = None
            if len(img) != ln or zlib.crc32(img) != crc or img[:4] not in (b"SGQB", b"SGQA"):
                self.status(4); return
            self.image = img
            self.log.append(("import", ln))
            self.status(0)

    def remote(self, cc):
        if cc == 20:
            if self.playing:
                self.stop()
            else:
                self.start()
        elif cc == 31:
            self.bpm += 1
        elif cc == 30:
            self.bpm -= 1
        elif 48 <= cc < 64:
            self.mute ^= {cc - 48}

    def start(self):
        self.playing = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        self.playing = False
        self.thread.join()

    def run(self):
        """ticks at the current tempo; the notes of hwtest_expected.json by tick, over and over every two bars"""
        exp = self.exp
        tick_ms0 = 60000.0 / exp["bpm"] / 24                  # the expected file's own tick: note times -> ticks
        sched = []
        for ch_s, ns in exp["notes_2bars"].items():
            for t_ms, note, vel in ns:
                sched.append((int(round(t_ms / tick_ms0)), int(ch_s) - 1, note, vel))
        sched.sort()
        self.out(0, bytes([0xFA]))
        tick, t_next, pending = 0, time.perf_counter(), []
        while self.playing:
            now = time.perf_counter()
            if now < t_next:
                time.sleep(min(0.002, t_next - now))
                continue
            self.out(0, bytes([0xF8]))
            k = tick % 192
            for tk, ch, note, vel in sched:
                if tk == k and ch not in self.mute:
                    self.out(0, bytes([0x90 | ch, note, vel]))
                    pending.append((tick + 2, ch, note))
            for p in [p for p in pending if p[0] <= tick]:
                self.out(0, bytes([0x80 | p[1], p[2], 0]))
                pending.remove(p)
            tick += 1
            t_next += 60.0 / self.bpm / 24
        for p in pending:
            self.out(0, bytes([0x80 | p[1], p[2], 0]))
        self.out(0, bytes([0xFC]))


def main():
    import sagga_hw_test as T
    with open(os.path.join(HW, "hwtest.sgq"), "rb") as f:
        test_img = f.read()
    with open(os.path.join(HW, "hwtest_expected.json")) as f:
        exp = json.load(f)
    # the scaled expected file: the fake plays SPEED x faster
    fast = dict(exp)
    fast["bpm"] = exp["bpm"] * SPEED
    fast["bar_ms"] = exp["bar_ms"] / SPEED
    fast["clock_ms"] = exp["clock_ms"] / SPEED
    fast["notes_2bars"] = {ch: [(round(t / SPEED, 2), n, v) for t, n, v in ns] for ch, ns in exp["notes_2bars"].items()}
    fast["tempo_test"] = dict(exp["tempo_test"], bpm_before=exp["bpm"] * SPEED, bpm_after_up=exp["bpm"] * SPEED + 8, bpm_after_down=exp["bpm"] * SPEED)
    fails = 0
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "hwtest_expected.json"), "w") as f:
            json.dump(fast, f)
        with open(os.path.join(d, "hwtest.sgq"), "wb") as f:
            f.write(test_img)
        T.ASSETS = d
        # the FM-1 holds another project: the test image with another BPM byte
        other = bytearray(test_img); other[8] = 0x70
        d1, d2, d3 = [os.path.join(d, x) for x in ("run1", "run2", "run3")]
        for x in (d1, d2, d3):
            os.mkdir(x)
        dev = FakeFM1(bytes(other), fast)
        rc = T.main(["--yes", "--out", d1, "--bars", "2"], backend=FakeBackend(dev))
        log = open([os.path.join(d1, x) for x in os.listdir(d1) if x.startswith("hwtest-")][0]).read()
        print("---- the run against the fake FM-1 returned %d" % rc)
        def check(c, what):
            nonlocal fails
            print("  %s  %s" % ("ok  " if c else "FAIL", what))
            if not c:
                fails += 1
        check(rc == 0, "the run passes against a faithful fake")
        check("FAIL" not in log.split("checks,")[0].replace("failed", ""), "no FAIL line in the log")
        check("control port: MIDIIN2 (Felucca) 2; synth port: Felucca 1" in log, "the control port is port 2, the synth port is port 1")
        check("identity: FM-1_910" in log, "the identity came from the handshake")
        backups = [x for x in os.listdir(d1) if x.startswith("backup-")]
        check(len(backups) == 1 and open(os.path.join(d1, backups[0]), "rb").read() == bytes(other), "the backup is the project the FM-1 had")
        check(dev.image == bytes(other) and [x for x in dev.log if x[0] == "import"][-1][1] == len(other), "RESTORE put it back (the last import is the backup)")
        check("ROUND TRIP: the image comes back identical" in log and "PASS  ROUND TRIP" in log, "the test image round-trips")
        check("PASS  EXPO RAMP" in log, "the EXPO gaps are checked")
        check("PASS  MUTE track 1" in log, "the mute test passes")
        check("PASS  TEMPO" in log, "the tempo test passes")
        check("PASS  EXPORT while playing is refused (BUSY)" in log, "BUSY while playing")
        # a playing FM-1 at the start: the program stops and says so
        dev2 = FakeFM1(bytes(other), fast)
        dev2.start()
        rc2 = T.main(["--yes", "--out", d2], backend=FakeBackend(dev2))
        dev2.stop()
        check(rc2 == 1, "a playing FM-1 at the start: refused (%d)" % rc2)
        # a wrong fake: it drops channel 2 and plays track 1 late; the test must see both
        class Lame(FakeFM1):
            def out(self, cable, data):
                if cable == 0 and len(data) == 3 and (data[0] & 15) == 1:
                    return
                super().out(cable, data)
        dev3 = Lame(bytes(other), fast)
        rc3 = T.main(["--yes", "--out", d3, "--bars", "2"], backend=FakeBackend(dev3))
        log3 = open([os.path.join(d3, x) for x in os.listdir(d3) if x.startswith("hwtest-")][0]).read()
        check(rc3 == 1 and "FAIL  channel 2:" in log3, "a firmware that drops channel 2 fails the run (%d)" % rc3)
    print("sagga hwtest: %d failures" % fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
