#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA HUB 0.32.2: the grid bridge's way out, and the closing of a MIDI input that cannot lock up.

On the Pi, 0.32.1, the banco stopped the bridge (`systemctl stop`) and the bridge never ended: it was closing the FM-1's
input as the FM-1 answered. systemd killed it after 90 s and left the service failed; the grid stayed dark until the Pi
was started again. The cause is in python-rtmidi's way of closing an input (tests/sagga_lockup.py has it in small).

  * the lock-up itself, shown: mido's own close() with a message on its way never comes back - and the closings of
    0.32.2 (the bridge's, the installer's, the FM-1 test's) do, with that message and under a device that never pauses;
  * the bridge as a program, with a stand-in for mido whose ports never finish closing: told to stop (SIGTERM, Ctrl-C)
    it says its goodbye and is gone at once, no port closed; the same ports closed, as until 0.32.1, never end;
  * a goodbye that itself never ends: the program is gone by itself after WAY_OUT_S, saying where it was stuck;
  * the service gives it less time than the banco's own patience, and more than the bridge gives itself.
"""
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "hub"))
sys.path.insert(0, os.path.join(ROOT, "tools", "hwtest"))
sys.path.insert(0, HERE)
import sagga_grid_bridge as B          # noqa: E402
import fm1_install as FI               # noqa: E402
import sagga_hw_test as HT             # noqa: E402
import sagga_hw_explore as X           # noqa: E402
import sagga_banco as BT               # noqa: E402  (tests/: the banco's plan and comparison ...)
import sagga_lockup as L               # noqa: E402

R = BT.runner()                         # ... and tools/hub/sagga_banco.py, the banco's runner on the Pi

CHECKS, FAILS = [0], []
BRIDGE = os.path.join(ROOT, "tools", "sagga_grid_bridge.py")


def check(cond, what):
    CHECKS[0] += 1
    if not cond:
        FAILS.append(what)
        print("  FAIL:", what)


def group(name):
    print(name)


# ------------------------------------------------------------------------------------------------ the lock-up, in small
def t_lockup():
    group("the lock-up: mido's close() with a message on its way never comes back; the closings of 0.32.2 do")
    L.lib()                                                   # (compiled once, before the processes start)
    names = ["quiet:mido", "flight:mido", "flight:bridge", "flight:installer", "flight:hwtest", "storm:bridge",
             "storm:installer", "storm:hwtest"]
    procs = {n: subprocess.Popen([sys.executable, os.path.join(HERE, "sagga_lockup.py"), n], stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True) for n in names}
    t0, out, back = time.time(), {}, {}
    for n, p in procs.items():
        try:
            out[n] = p.communicate(timeout=max(0.5, 20.0 - (time.time() - t0)) if n != "flight:mido" else 4.0)[0]
            back[n] = p.returncode
        except subprocess.TimeoutExpired:
            p.kill()
            out[n] = p.communicate()[0]
            back[n] = None                                    # it never came back
    check(back["quiet:mido"] == 0, "nothing comes in: mido's own close() comes back (%s %s)" % (back["quiet:mido"], out["quiet:mido"][-200:]))
    check(back["flight:mido"] is None and "ok" not in out["flight:mido"],
          "a message on its way: mido's own close() NEVER comes back - the thread waits for the interpreter, the closing "
          "for the thread (%s %r)" % (back["flight:mido"], out["flight:mido"][-200:]))
    for which, what in (("bridge", "the bridge's close_inputs"), ("installer", "the installer's close_input"), ("hwtest", "the FM-1 test's close_input")):
        o = out["flight:" + which]
        check(back["flight:" + which] == 0 and "1 call on its way, heard 1" in o and "driver set cancel close delete" in o,
              "... %s comes back: the message on its way is heard, the callback is out before the port closes (%s %r)"
              % (what, back["flight:" + which], o[-200:]))
        o = out["storm:" + which]
        check(back["storm:" + which] == 0 and "60 ports closed" in o,
              "... and under a device that sends every 100 us: sixty ports opened and closed (%s %r)" % (back["storm:" + which], o[-160:]))


# ------------------------------------------------------------------------------------------------ the order, call by call
class Rt:
    def __init__(self, said, name, fail=False):
        self.said, self.name, self.fail = said, name, fail

    def cancel_callback(self):
        self.said.append(("cancel", self.name))
        if self.fail:
            raise RuntimeError("no callback")

    def close_port(self):
        self.said.append(("close_port", self.name))

    def delete(self):
        self.said.append(("delete", self.name))


class RtPort:
    """a port with python-rtmidi under it, as mido makes them"""
    def __init__(self, said, name, fail=False):
        self.said, self.name, self.closed = said, name, False
        self._rt = Rt(said, name, fail)

    def close(self):
        self.said.append(("mido close", self.name))


class PlainPort:
    """a port of another backend, or a test's stand-in"""
    def __init__(self, said, name):
        self.said, self.name = said, name

    def close(self):
        self.said.append(("close", self.name))


def t_order():
    group("the closing, call by call")
    said = []
    ports = [RtPort(said, "a"), None, PlainPort(said, "p"), RtPort(said, "b", fail=True)]
    B.close_inputs(ports, sleep=lambda s: said.append(("sleep", s)))
    check(said == [("sleep", B.BEFORE_S), ("cancel", "a"), ("cancel", "b"), ("sleep", B.SETTLE_S), ("close_port", "a"), ("delete", "a"),
                   ("close", "p"), ("close_port", "b"), ("delete", "b")],
          "a moment, every callback out, a moment, then the ports by the driver - never mido's close(); a port without "
          "the driver: its own close(); a callback that cannot be taken out: closed all the same (%s)" % said)
    check(ports[0].closed and ports[3].closed, "... and mido is told they are closed (its close() and __del__ do nothing more)")
    n = len(said)
    B.close_inputs(ports, sleep=lambda s: said.append(("sleep", s)))
    check(said[n:] == [("close", "p")], "closed a second time: the driver's freed objects are not touched again (%s)" % said[n:])
    said2 = []
    B.close_inputs([PlainPort(said2, "p"), PlainPort(said2, "q")], sleep=lambda s: said2.append(("sleep", s)))
    check(said2 == [("close", "p"), ("close", "q")], "no such driver anywhere: no waiting (%s)" % said2)
    for mod, what in ((FI, "the installer"), (HT, "the FM-1 test")):
        said3 = []
        p = RtPort(said3, "a")
        mod.close_input(p, sleep=lambda s: said3.append(("sleep", s)))
        check(said3 == [("sleep", 0.002), ("cancel", "a"), ("sleep", 0.05), ("close_port", "a"), ("delete", "a")] and p.closed,
              "%s: the same order (%s)" % (what, said3))
        mod.close_input(p, sleep=lambda s: said3.append(("sleep", s)))
        check(len(said3) == 5, "... closed a second time: nothing (the driver's freed object is not touched) (%s)" % said3[5:])
        said4 = []
        mod.close_input(PlainPort(said4, "p"), sleep=lambda s: said4.append(("sleep", s)))
        check(said4 == [("close", "p")], "... a port without the driver: its own close() (%s)" % said4)
    # the links of the two tools close through it
    said5 = []
    link = FI.MidoLink.__new__(FI.MidoLink)
    link.inp, link.out = RtPort(said5, "in"), PlainPort(said5, "out")
    real = FI.time.sleep
    FI.time.sleep = lambda s: None
    try:
        link.close()
    finally:
        FI.time.sleep = real
    check(("mido close", "in") not in said5 and ("close_port", "in") in said5 and said5[-1] == ("close", "out"), "the installer's link: its input by the driver, then its output (%s)" % said5)
    said6 = []
    link = HT.MidoLink.__new__(HT.MidoLink)
    link.inp, link.out = RtPort(said6, "in"), PlainPort(said6, "out")
    real = HT.time.sleep
    HT.time.sleep = lambda s: None
    try:
        X.close_input(link)
        X.close_output(link)
    finally:
        HT.time.sleep = real
    check(said6 == [("cancel", "in"), ("close_port", "in"), ("delete", "in"), ("close", "out")], "the FM-1 test's link, as the explorer closes it (%s)" % said6)
    said8 = []
    bare = types.SimpleNamespace(inp=RtPort(said8, "in"), out=PlainPort(said8, "out"))     # (a link that is only its two ports)
    real = HT.time.sleep
    HT.time.sleep = lambda s: None
    try:
        X.close_input(bare)
        X.close_output(bare)
    finally:
        HT.time.sleep = real
    check(said8 == [("cancel", "in"), ("close_port", "in"), ("delete", "in"), ("close", "out")], "... and a link that has no closing of its own (%s)" % said8)
    for mod, what in ((FI, "the installer's"), (HT, "the FM-1 test's")):         # a link nobody closed
        said7 = []
        link = mod.MidoLink.__new__(mod.MidoLink)
        link.inp, link.out = RtPort(said7, "in"), PlainPort(said7, "out")
        real = mod.time.sleep
        mod.time.sleep = lambda s: None
        try:
            del link
        finally:
            mod.time.sleep = real
        check(("close_port", "in") in said7 and ("mido close", "in") not in said7 and said7[-1] == ("close", "out"),
              "%s link let go of without a close: closed the same way, before mido does it its own (%s)" % (what, said7))
    # the premise of the tuple that takes the place of python-rtmidi's: CPython gives a freed 2-tuple's place to the next one
    same = 0
    for _ in range(200):
        t = (t_order, None)
        at = id(t)
        del t
        s = (B._nothing, None)
        same += id(s) == at
        del s
    check(same == 200, "a tuple of two made as one is freed takes its place (this Python: %d of 200)" % same)
    for _ in range(100):
        B.close_inputs([RtPort([], "x")], sleep=lambda s: None)
    check(0 < len(B.SPARE) <= 64, "the tuples kept: the last few (%d)" % len(B.SPARE))


# ------------------------------------------------------------------------------------------------ the bridge as a program
FAKE_MIDO = r'''
"""a stand-in for mido: two Launchpads and an FM-1; every port writes down what it is sent, and closing one never ends
(FAKE_MIDO_MODE: stuck-send = the FM-1's port never takes the detach; gone = the FM-1's port fails after a while;
bad-open = the FM-1's output does not open). As mido's, a port Python lets go of closes itself."""
import json, os, threading
LOG = os.environ["FAKE_MIDO_LOG"]
MODE = os.environ.get("FAKE_MIDO_MODE", "")
NAMES = ["Launchpad Mini MK3:Launchpad Mini MK3 LPMiniMK3 MIDI In 20:1", "Launchpad Mini MK3:Launchpad Mini MK3 LPMiniMK3 MIDI In 24:1",
         "Felucca 2:Felucca 2 MIDI 1 36:0"]
sent = [0]
DUMP = os.environ.get("FAKE_MIDO_DUMP")              # a file of SysEx messages: a project the FM-1 gives, twice


def note(*a):
    with open(LOG, "a") as f:
        f.write(json.dumps(a) + "\n")


class Message:
    def __init__(self, b): self.b = list(b)
    def bytes(self): return self.b
    @classmethod
    def from_bytes(cls, b): return cls(b)


class Port:
    def __init__(self, name, kind): self.name, self.kind = name, kind

    def send(self, m):
        note("send", self.name, m.bytes())
        if self.name.startswith("Felucca"):
            sent[0] += 1
            if MODE == "stuck-send" and m.bytes() == [0xBF, 118, 0]:
                threading.Event().wait()
            if MODE == "gone" and sent[0] > 3:
                raise OSError("the port is gone")

    def close(self):
        note("close", self.name, self.kind)
        threading.Event().wait()

    def __del__(self):                                        # (as mido's ports: closed when Python lets go of them)
        self.close()


def give(callback):
    import time
    with open(DUMP) as f:
        frames = json.load(f)
    for k in range(2):
        time.sleep(0.6)
        for fr in frames:
            callback(Message(fr))
        note("gave", "Felucca", k)


def get_input_names(): return list(NAMES)
def get_output_names(): return list(NAMES)
def open_input(name, callback=None, virtual=False):
    if DUMP and name.startswith("Felucca"):
        threading.Thread(target=give, args=(callback,), daemon=True).start()
    return Port(name, "in")
def open_output(name, virtual=False):
    if MODE == "bad-open" and name.startswith("Felucca"):
        raise OSError("the FM-1's output does not open")
    return Port(name, "out")
'''
IN_PROCESS = ("import sys; sys.path.insert(0, %r); import sagga_grid_bridge as B; " % os.path.join(ROOT, "tools"))


def run_program(cmd, mode="", sig=signal.SIGTERM, patience=4.0, wait_for="bridge running", before=None, linger=0.3, library=None):
    """the bridge started with the stand-in for mido; once it runs (and `linger` s more), the signal; -> (exit code or
    None when it had to be killed, seconds from the signal to its end, what the ports were sent / asked, stdout,
    stderr). before(folder, env): things to put there first; library: a list that gets the library's files"""
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "mido.py"), "w") as f:
            f.write(FAKE_MIDO)
        log = os.path.join(d, "ports.log")
        env = dict(os.environ, PYTHONPATH=d, FAKE_MIDO_LOG=log, FAKE_MIDO_MODE=mode, SAGGA_CONTROL=os.path.join(d, "control"))
        env.pop("FAKE_MIDO_DUMP", None)
        if before:
            before(d, env)
        p = subprocess.Popen(cmd + ["--dump-dir", os.path.join(d, "lib")], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        lines, errs = [], []
        running = threading.Event()

        def read_out():
            for ln in p.stdout:
                lines.append(ln)
                if wait_for in ln:
                    running.set()
        th = [threading.Thread(target=read_out, daemon=True), threading.Thread(target=lambda: errs.extend(p.stderr), daemon=True)]
        for t in th:
            t.start()
        t_sig = None
        if sig is not None:
            running.wait(15.0)
            time.sleep(linger)                                # (a few turns of its loop)
            t_sig = time.time()
            p.send_signal(sig)
        try:
            rc = p.wait(timeout=patience)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
            rc = None
        took = time.time() - (t_sig or time.time())
        for t in th:
            t.join(2.0)
        said = []
        if os.path.exists(log):
            with open(log) as f:
                said = [json.loads(ln) for ln in f if ln.strip()]
        if library is not None and os.path.isdir(os.path.join(d, "lib")):
            library.extend(sorted(n for n in os.listdir(os.path.join(d, "lib")) if n.endswith(".sgq")))
    return rc, took, said, "".join(lines), "".join(errs), running.is_set()


def goodbye(said):
    """the last message each port got"""
    last = {}
    for kind, name, *rest in said:
        if kind == "send":
            last[name.split(":")[0] + name[-5:]] = rest[0]
    return last


def t_program():
    group("the bridge as a program: told to stop, its goodbye and gone - no port closed")
    rc, took, said, out, err, ran = run_program([sys.executable, "-u", BRIDGE])
    last = goodbye(said)
    fm = [v for k, v in last.items() if k.startswith("Felucca")]
    lps = [v for k, v in last.items() if k.startswith("Launchpad")]
    check(ran and rc == 0 and took < 2.0, "SIGTERM (systemctl stop): it ends, code 0, at once (ran %s, rc %s, %.2f s; %r)" % (ran, rc, took, err[-300:]))
    check(fm == [[0xBF, 118, 0]] and len(lps) == 2 and all(v == B.MK3.HEADER + [0x0E, 0x00, 0xF7] for v in lps),
          "... the FM-1 was told (detach), the Launchpads are dark and back in their own mode (%s %s)" % (fm, lps))
    check(not [x for x in said if x[0] == "close"], "... and no port was closed: the process ended with them open (%s)" % [x for x in said if x[0] == "close"])
    # the check of the check: the same ports, closed as until 0.32.1
    rc2, took2, said2, out2, err2, ran2 = run_program([sys.executable, "-u", "-c", IN_PROCESS + "sys.exit(B.main(sys.argv[1:]))"], patience=3.0)
    check(ran2 and rc2 is None and [x for x in said2 if x[0] == "close"] and goodbye(said2) == last,
          "the same ports closed on the way out, as until 0.32.1: the program never ends (it had to be killed: %s; closing %s)"
          % (rc2, [x[1][:9] for x in said2 if x[0] == "close"]))
    rc3, took3, said3, out3, err3, ran3 = run_program([sys.executable, "-u", BRIDGE], sig=signal.SIGINT)
    check(ran3 and rc3 == 0 and took3 < 2.0 and goodbye(said3) == last and not [x for x in said3 if x[0] == "close"],
          "Ctrl-C: the same (rc %s, %.2f s)" % (rc3, took3))
    rc4, took4, said4, out4, err4, ran4 = run_program([sys.executable, "-u", BRIDGE], mode="gone", sig=None, patience=8.0)
    check(rc4 == 1 and "bridge stopped: OSError" in err4 and not [x for x in said4 if x[0] == "close"],
          "the FM-1's port fails: said, code 1 (the service starts it again), gone without closing (%s %r)" % (rc4, err4[-200:]))
    group("a goodbye that never ends: gone by itself after WAY_OUT_S, saying where")
    rc5, took5, said5, out5, err5, ran5 = run_program(
        [sys.executable, "-u", "-c", IN_PROCESS + "B.WAY_OUT_S = 1.0; B.program(sys.argv[1:])"], mode="stuck-send", patience=8.0)
    check(ran5 and rc5 == 1 and 0.7 < took5 < 5.0, "the FM-1's port never takes the detach: the process ends by itself, code 1, after about WAY_OUT_S (rc %s, %.2f s)" % (rc5, took5))
    check("Timeout" in err5 and "in send" in err5 and "in stop" in err5 and "sagga_grid_bridge.py" in err5,
          "... and its last words are where every thread stood: the journal has them (%r)" % err5[-400:])
    group("the program's other ends")
    with tempfile.TemporaryDirectory() as d:
        bad = os.path.join(d, "not-a-project.sgq")
        with open(bad, "wb") as f:
            f.write(b"not an image")
        rc6, took6, said6, out6, err6, ran6 = run_program([sys.executable, "-u", BRIDGE, "--import", bad], sig=None, patience=8.0)
    check(rc6 == 2 and "not-a-project.sgq" in err6 and not [x for x in said6 if x[0] == "close"],
          "--import of a file that is no project: said, code 2, gone without closing the FM-1's ports (%s %r)" % (rc6, err6[-160:]))
    rc7, took7, said7, out7, err7, ran7 = run_program([sys.executable, "-u", BRIDGE, "--import", "/no/such/file.sgq"], sig=None, patience=8.0)
    check(rc7 == 1 and "FileNotFoundError" in err7 and not [x for x in said7 if x[0] == "close"],
          "--import of a file that is not there: Python's own words, code 1, gone before Python lets go of the ports (%s %r)" % (rc7, err7[-120:]))
    rc8, took8, said8, out8, err8, ran8 = run_program([sys.executable, "-u", BRIDGE], mode="bad-open", sig=None, patience=8.0)
    check(rc8 == 1 and "the FM-1's output does not open" in err8 and not [x for x in said8 if x[0] == "close"],
          "a port that does not open with others open already: said, code 1, gone with them open (%s %r)" % (rc8, err8[-120:]))


def t_program_library():
    group("the bridge as a program: a project the FM-1 gives while another program's word waits is not its library's")
    frames = B.dump_frames(B.PROJECT_MAGIC + bytes(range(256)) * 8)

    def before(d, env):
        os.makedirs(os.path.join(d, "control"))
        with open(os.path.join(d, "dump.json"), "w") as f:
            json.dump(frames, f)
        env["FAKE_MIDO_DUMP"] = os.path.join(d, "dump.json")
        B.export_elsewhere_mark(os.path.join(d, "control"))   # (the banco, a line before it asks the FM-1)
    lib = []
    rc, took, said, out, err, ran = run_program([sys.executable, "-u", BRIDGE], before=before, linger=2.0, library=lib)
    answers = [x[2] for x in said if x[0] == "send" and x[1].startswith("Felucca") and x[2][:5] == B.SX_HEAD + [B.SX_LIB_ANSWER]]
    check(ran and rc == 0 and [x[2] for x in said if x[0] == "gave"] == [0, 1], "(the FM-1 gave its project twice: %s, rc %s; %r)" % ([x for x in said if x[0] == "gave"], rc, err[-200:]))
    check(len(lib) == 1 and out.count("asked for by another program") == 1 and out.count("project from the FM-1 saved") == 1 and len(answers) == 1,
          "the first, with the word waiting: no file, no answer to the FM-1; the second: saved and answered, as always (%s, %d answers)" % (lib, len(answers)))


def t_main_closes():
    group("main() called by a test (no program to end): every input closed by the driver, a synth's too")
    import contextlib
    import io
    said = []
    names = ["Launchpad Mini MK3:Launchpad Mini MK3 LPMiniMK3 MIDI In 20:1", "Launchpad Mini MK3:Launchpad Mini MK3 LPMiniMK3 MIDI In 24:1",
             "Felucca 2:Felucca 2 MIDI 1 36:0", "MicroFreak:MicroFreak MIDI 1 40:0"]
    short = lambda n: n.split(":")[0].split()[0] + n[-5:]

    class Msg:
        def __init__(self, b): self.b = list(b)
        def bytes(self): return self.b
        @classmethod
        def from_bytes(cls, b): return cls(b)
    fm_sends = [0]

    class Out(PlainPort):
        def send(self, m):
            if "Felucca" in self.name:
                fm_sends[0] += 1
                if fm_sends[0] == 3:
                    raise KeyboardInterrupt()                 # (Ctrl-C, a few turns in)
    fake = types.SimpleNamespace(get_input_names=lambda: list(names), get_output_names=lambda: list(names), Message=Msg,
                                 open_input=lambda name, callback=None, virtual=False: RtPort(said, "in " + short(name)),
                                 open_output=lambda name, virtual=False: Out(said, "out " + short(name)))
    clients = {14: "Midi Through", 20: "Launchpad Mini MK3", 24: "Launchpad Mini MK3", 36: "Felucca 2", 40: "MicroFreak"}
    sys.modules["mido"] = fake
    real_clients, real_links, real_sleep = B.alsa_clients, B.alsa_links, B.time.sleep
    B.alsa_clients = lambda *a, **k: dict(clients)            # (a Pi: the synths' ports are opened once and kept)
    B.alsa_links = lambda *a, **k: None
    slept = []
    B.time.sleep = lambda s_: slept.append(s_)
    try:
        with tempfile.TemporaryDirectory() as d:
            cfg = os.path.join(d, "patches.json")
            with open(cfg, "w") as f:
                json.dump({"synths": [{"name": "MF", "port": "MicroFreak", "request": "F0 01 F7"}]}, f)
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = B.main(["--dump-dir", d, "--patches", cfg])
    finally:
        B.alsa_clients, B.alsa_links, B.time.sleep = real_clients, real_links, real_sleep
        del sys.modules["mido"]
    ins = sorted(n for k, n in said if k == "close_port")
    check(rc == 0 and "snapshot patches: MF" in out.getvalue(), "(the bridge ran with its grid and a synth: rc %s; %r %r)" % (rc, out.getvalue()[-200:], err.getvalue()[-200:]))
    check(ins == sorted("in " + short(n) for n in names) and not [x for x in said if x[0] == "mido close"]
          and all(said.index(("cancel", n)) < said.index(("close_port", n)) < said.index(("delete", n)) for n in ins),
          "the four inputs (two Launchpads, the FM-1, the synth): callback out, port closed, driver freed - never mido's close() (%s)" % said)
    check(sorted(n for k, n in said if k == "close") == sorted("out " + short(n) for n in names), "the four outputs: their own close()")
    check(not B.SPARE or len(B.SPARE) <= 64, "(the tuples kept: %d)" % len(B.SPARE))


def t_codes():
    group("program(): main()'s ends, each with its code")
    ins = ["Felucca 2:Felucca 2 MIDI 1 36:0"]
    fake = types.SimpleNamespace(get_input_names=lambda: list(ins), get_output_names=lambda: list(ins))
    sys.modules["mido"] = fake
    real_clients = B.alsa_clients
    B.alsa_clients = lambda *a, **k: None
    import contextlib
    import io
    try:
        def run(args):
            got, out, err = [], io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                B.program(args, leave=got.append)
            return got, out.getvalue(), err.getvalue()
        got, out, err = run(["--list"])
        check(got == [0] and "Felucca 2" in out, "--list: the ports, code 0 (%s)" % got)
        got, out, err = run(["--export", "99"])
        check(got == [2] and "slot 1-8" in err, "a wrong argument: argparse's words, code 2 (%s)" % got)
        got, out, err = run(["--fm1", "NoSuchThing"])
        check(got == [1] and "no port matches --fm1" in err, "no FM-1 and no /proc to wait with: said, code 1 (%s %r)" % (got, err[-80:]))
        real_main = B.main

        def interrupted(argv, leave=None):
            raise KeyboardInterrupt
        B.main = interrupted
        try:
            got, out, err = run([])
        finally:
            B.main = real_main
        check(got == [0], "told to stop while it was starting: code 0, not an error (%s)" % got)

        def broken(argv, leave=None):
            raise RuntimeError("something else")
        B.main = broken
        try:
            got, out, err = run([])
        finally:
            B.main = real_main
        check(got == [1] and "something else" in err, "an error nobody caught: its traceback, code 1 (%s)" % got)
    finally:
        B.alsa_clients = real_clients
        del sys.modules["mido"]


def t_unit():
    group("the service and the banco: who waits how long")
    with open(os.path.join(ROOT, "tools", "sagga-grid-bridge.service")) as f:
        unit = dict(ln.strip().split("=", 1) for ln in f if "=" in ln and not ln.lstrip().startswith("#"))
    stop_s = float(unit.get("TimeoutStopSec", "90"))
    check(B.GOODBYE_S < 1.0 and B.WAY_OUT_S + 2.0 <= stop_s <= R.SYSTEM_S - 2.0,
          "the bridge gives itself %.0f s, systemd gives it %.0f, the banco's `systemctl stop` waits %.0f: each longer "
          "than the one before" % (B.WAY_OUT_S, stop_s, R.SYSTEM_S))
    check(unit.get("Restart") == "always", "the service still starts the bridge again when it ends with an error")
    with open(os.path.join(ROOT, "tools", "sagga-grid-bridge-zynthian.service")) as f:
        zyn = dict(ln.strip().split("=", 1) for ln in f if "=" in ln and not ln.lstrip().startswith("#"))
    check(zyn.get("TimeoutStopSec") == unit.get("TimeoutStopSec"), "the Zynthian's service file: the same time (%s)" % zyn.get("TimeoutStopSec"))
    with open(os.path.join(ROOT, "tools", "hub", "install_hub.sh")) as f:
        sh = f.read()
    check("sagga-grid-bridge.service" in sh and "daemon-reload" in sh, "an update of the hub installs the service file again")


def main():
    only = os.environ.get("SAGGA_ONLY")                      # (a few of them by name, as the simulator's tests)
    for t in (t_order, t_main_closes, t_codes, t_unit, t_lockup, t_program, t_program_library):
        if only and not any(o and o in t.__name__ for o in only.split(",")):
            continue
        t()
    print("sagga way out: %d checks, %d failures" % (CHECKS[0], len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
