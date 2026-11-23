#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA HUB 0.20.3: the banco's explorer on the Pi (tools/hub/sagga_banco.py) against a fake FM-1 that speaks the
test's SysEx and hears its ports (as 0.20.3 does when GO asks), a fake RaspiMIDIHub (its API: the matrix, the pages,
PATCH = a page pressed: its messages reach the FM-1 as the matrix would carry them) and a fake systemctl: the matrix
checked, the synths' cells away during the prova and back at the end (after an interruption too), the pages pressed
through the hub (the user's own binding of a cell followed; a page missing: straight to the FM-1), the bridge with two
Launchpads of ours (every pad and button translated, the lights drawn), what the FM-1 heard matched with what the Pi
sent, the bridge's service stopped and started again, the project back in memory."""
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sagga_hw_explore_tests as HX     # noqa: E402  (the fake FM-1 of the Windows runner's tests)
import sagga_banco as BT                # noqa: E402  (the plan and the comparison)

T = HX.T
R = BT.runner()                         # tools/hub/sagga_banco.py
B = BT.B

CHECKS, FAILS = [0], []


def check(cond, what):
    CHECKS[0] += 1
    if not cond:
        FAILS.append(what)
        print("  FAIL:", what)


def group(name):
    print(name)


# ---------------------------------------------------------------------------------------------------- the fakes
class BancoFM1(HX.FakeFM1):
    """the fake FM-1, 0.20.3: GO with listen = every message from its ports said back (74), where it came; the grid
    attached = a few lights"""
    def __init__(self, deaf=0, **kw):
        super().__init__(two_ports=True, version="0.20.3", **kw)
        self.listen, self.seq, self.got = False, 0, []
        self.deaf = deaf                     # the first `deaf` questions get no key (20 s pass: 4, no answer)
        self.bridge_up_at_yes = None
        self.sysm = None
        self.reboots, self.hellos = 0, 0
        self.deaf_after, self.deaf_now = None, False

    def out2(self, data):
        link = self.links.get(1)
        if link and link.on_message and self.connected():
            link.on_message(bytes(data), time.perf_counter())

    def _yes(self):
        if self.sysm is not None:
            self.bridge_up_at_yes = not any(c[:2] == ["systemctl", "stop"] for c in self.sysm.calls)
        if self.deaf > 0:
            self.deaf -= 1
            self.state = 4
            self.ans(T.OPEN, [4])
            return
        super()._yes()

    def rx(self, data):
        m = list(data)
        if m and m[0] != 0xF0:
            self.got.append(m)
            if self.go_t is not None and self.listen:
                now = self.ms()
                self.out(T.HEAD + [T.SX_TST_HEARD] + T.put7(self.seq, 2) + [1] + T.put7(now, 4) + T.put7(now // 20, 4) +
                         [m[0] & 127, m[1], m[2], 1, 0xF7])
                self.seq += 1
                if m[:3] == [0xBF, 118, 127]:            # (the lights on port 2, as the FM-1 with two ports; on
                    for x in range(4):                   #  port 1 a track 16 note, which is no light)
                        self.out2(bytes([0x9F, 16 * x + x, 3 + x]))
                    self.out2(bytes([0xBE, 7, 5]))
                    self.out2(bytes([0xBE, 27, 6]))
                    self.out(bytes([0x9F, 0x22, 100]))
            return
        if self.deaf_now:
            return                                   # (0.20.9: after a reboot, deaf: the 0.20.8 banco's 4th)
        if m[:4] == T.HEAD and len(m) > 6 and m[4] == T.SX_TST and m[5] == T.HELLO:
            self.hellos += 1
        if m[:4] == T.HEAD and len(m) > 6 and m[4] == T.SX_TST and m[5] == T.DIAG and self.version >= "0.20.9":
            v = dict.fromkeys(T.DIAG_FIELDS, 0)
            v.update(hellos=self.hellos, frames=self.hellos + 1, first_ms=40, resets=1, configs=1, cfg_ms=350, ms=self.ms())
            self.ans(T.DIAG, sum((T.put7(v[k], 4) for k in T.DIAG_FIELDS), []))
            return
        if m[:4] == T.HEAD and len(m) > 6 and m[4] == T.SX_TST and m[5] == T.GO:
            self.listen = len(m) > 7 and bool(m[6] & 1)
            self.seq = 0
        super().rx(data)

    def reboot(self, test):
        self.reboots += 1
        self.hellos = 0
        if self.deaf_after is not None and self.reboots == self.deaf_after:
            self.deaf_now = True
        super().reboot(test)


class CountFM1(HX.CountMixin, BancoFM1):
    """the fake FM-1, 0.23.1: it counts what it sends by port and kind and says it (DIAG); QUIET stops it for good"""
    def __init__(self, eat=None, **kw):
        super().__init__(**kw)
        self.count_init(eat)


FM1, SYNTH, LP = 24, 28, 32
PAGE_CLIENT = {"sagga_remote": 130, "sagga_mutes": 131, "sagga_motori": 132, "sagga_break": 133, "sagga_mod": 134, "sagga_live": 135}


def schema_of(name):
    cls, cells = BT.pages()[name]
    out = []
    for c in cells:
        p = c.param
        kind = p.__class__.__name__.lower()
        out.append({"param": {"name": p.name, "type": kind, "trigger": bool(getattr(p, "trigger", False))}, "channel": c.channel, "cc": c.cc})
    return [{"type": "layoutgrid", "name": "controller", "bindings_param": "cell_bindings", "cells": out}]


class FakeAPI:
    """RaspiMIDIHub's API as sagga_banco.py uses it: the devices, the cells, the pages (a PATCH presses a cell: the
    page's own code makes the messages, the matrix carries them to the FM-1 when the cell page -> FM-1 port 2 is there)"""
    def __init__(self, dev, pages=("sagga_remote", "sagga_mutes", "sagga_motori", "sagga_break", "sagga_mod"), own=None,
                 routing="none", extra_conns=(), launchpad=False):
        self.dev, self.pages, self.own, self.routing = dev, list(pages), own or {}, routing
        self.patches, self.posts, self.deletes, self.synth_during = [], [], [], 0
        self.conns = set()
        for p in self.pages:
            self.conns.add((PAGE_CLIENT[p], 0, FM1, 1))
            self.conns.add((FM1, 1, PAGE_CLIENT[p], 0))
        self.conns |= {(FM1, 0, SYNTH, 0), (SYNTH, 0, FM1, 0)}
        self.conns |= set(extra_conns)
        self.launchpad = launchpad
        self.values = {}
        self.fm1_online = True

    def devices(self):
        ports = [{"port_id": 0, "is_output": True, "is_input": True}, {"port_id": 1, "is_output": True, "is_input": True}]
        out = [{"client_id": FM1, "name": "Felucca", "online": self.fm1_online, "ports": ports, "stable_id": "usb-felucca"},
               {"client_id": SYNTH, "name": "MicroFreak", "online": True, "ports": ports[:1], "stable_id": "usb-microfreak"}]
        if self.launchpad:
            out.append({"client_id": LP, "name": "Launchpad Mini MK3", "online": True, "ports": ports, "stable_id": "usb-lp"})
        for p in self.pages:
            out.append({"client_id": PAGE_CLIENT[p], "name": R.PAGE_NAMES[p], "online": True, "ports": ports[:1],
                        "plugin_type": p, "stable_id": "plugin-%s" % p})
        return out

    def get(self, path):
        if path == "/api/system":
            return {"version": "9.9.9", "default_routing": self.routing}
        if path == "/api/devices":
            return self.devices()
        if path == "/api/connections":
            return [{"id": "%d:%d-%d:%d" % c, "src_client": c[0], "src_port": c[1], "dst_client": c[2], "dst_port": c[3],
                     "filtered": c == (FM1, 0, SYNTH, 0)} for c in sorted(self.conns)]
        if path == "/api/plugins/instances":
            return [{"id": "i-%s" % p, "type": p, "status": "running"} for p in self.pages]
        if path.startswith("/api/plugins/instances/"):
            p = path.rsplit("/i-", 1)[1]
            params = dict(self.values.get(p, {}))
            if p in self.own:
                params["cell_bindings"] = self.own[p]
            return {"id": "i-%s" % p, "type": p, "params": params, "params_schema": schema_of(p)}
        raise IOError("404 %s" % path)

    def patch(self, path, body):
        p = path.rsplit("/i-", 1)[1]
        if p not in self.pages:
            raise IOError("404")
        if any((FM1 in (c[0], c[2])) and SYNTH in (c[0], c[2]) for c in self.conns):
            self.synth_during += 1
        for cell, value in body["params"].items():
            self.patches.append((p, cell, value))
            self.values.setdefault(p, {})[cell] = value
            msgs = BT.page_messages(p, cell, value)
            ov = self.own.get(p, {}).get(cell)
            if ov:
                cls, cells = BT.pages()[p]
                c0 = [c for c in cells if c.param.name == cell][0]
                msgs = [(0xB0 | ov["channel"], ov["cc"], m[2]) if (m[0] & 0xF0) == 0xB0 and m[1] == c0.cc else m for m in msgs]
            if (PAGE_CLIENT[p], 0, FM1, 1) in self.conns:
                for m in msgs:
                    self.dev.rx(bytes(m))
        return {"status": "ok"}

    def delete(self, path):
        cid = path.rsplit("/", 1)[1]
        a, b = cid.split("-")
        c = tuple(int(x) for x in a.split(":")) + tuple(int(x) for x in b.split(":"))
        self.deletes.append(c)
        self.conns.discard(c)
        return {"status": "deleted"}

    def post(self, path, body):
        c = (body["src_client"], body["src_port"], body["dst_client"], body["dst_port"])
        self.posts.append(c)
        self.conns.add(c)
        return {"status": "created"}


class FakeSystem:
    def __init__(self, bridge="active", kernel="", journal=""):
        self.calls, self.bridge, self.kernel, self.journal = [], bridge, kernel, journal

    def __call__(self, cmd):
        self.calls.append(cmd)
        if cmd[0] == "journalctl":                           # (0.23.2: -k the kernel's, -u sagga-grid-bridge the bridge's own)
            out = self.kernel if "-k" in cmd else self.journal
        else:
            out = (self.bridge if "sagga-grid-bridge" in cmd else "active") + "\n"

        class R_:
            stdout = out
            returncode = 0
        return R_()


class LosingAPI(FakeAPI):
    """0.20.9: RaspiMIDIHub as 6.0.0 is: its autosave in the second the FM-1 is away, and the FM-1's cells are gone"""
    def __init__(self, dev, **kw):
        super().__init__(dev, **kw)
        self.lost = 0
        orig = dev.reboot

        def reboot(test):
            orig(test)
            gone = {c for c in self.conns if FM1 in (c[0], c[2])}
            self.lost += len(gone)
            self.conns -= gone
        dev.reboot = reboot


def mini_plan(n=2):
    ses = []
    for k in range(n):
        ev = [[400, T.PROBE, 0, 0], [500, T.PRESS, 3, 0], [520, T.RELEASE, 3, 0], [1500, T.PROBE, 0, 0], [2200, T.PROBE, 0, 0],
              [2300, T.END, 0, 0]]
        reali = [["grid_start", 450],
                 ["pagina", 600, "sagga_mutes", "m0", True, [[0xBD, 48, 127], [0xBD, 48, 0]]],
                 ["grid", 700, [0x9F, 0x23, 100]], ["grid", 760, [0x9F, 0x23, 0]],
                 ["grid", 800, [0xBE, 7, 127]], ["grid", 840, [0xBE, 7, 0]],
                 ["grid", 860, [0xBE, 27, 127]], ["grid", 880, [0xBE, 27, 0]],
                 ["grid", 890, [0x9F, 0x7C, 100]], ["grid", 895, [0x9F, 0x7C, 0]],
                 ["pagina", 900, "sagga_remote", "fill", True, [[0xBD, 23, 127]]],
                 ["pagina", 1000, "sagga_live", "mute", True, [[0xBA, 1, 127]]],
                 ["diretto", 1100, [0xBD, 20, 127]]]
        ses.append({"nome": "b%03d" % (k + 1), "situazione": "prova", "gesti": ["tocca", "pagina", "grid"], "eventi": ev,
                    "sonde": ["inizio", "gesto 1", "fermo"], "reali": reali})
    return {"versione": 1, "firmware": "0.20.3", "seme": 1, "banco": True, "sessioni": ses}


def run_main(dev, api, system, args=(), plan=None, sysfs=None, library=None):
    with tempfile.TemporaryDirectory() as d:
        pp = os.path.join(d, "piano.json")
        T.save(pp, plan or mini_plan())
        cells = os.path.join(d, "sd", "banco", "celle-staccate.json")
        rc = R.main([*args, "--piano", pp, "--out", d, "--celle", cells], backend=HX.FakeBackend(dev), api=api, system=system,
                    wait=lambda s: time.sleep(min(s, 1.2)), sysfs=sysfs or os.path.join(d, "no-sysfs"))
        if library is not None:
            lib = os.path.join(d, "sd")
            library.extend((n, open(os.path.join(lib, n), "rb").read()) for n in os.listdir(lib) if n.endswith(".sgq"))
        rac = [f for f in os.listdir(d) if f.startswith("raccolta-banco-")]
        data = T.load(os.path.join(d, rac[0])) if rac else None
        rep = [f for f in os.listdir(d) if f.startswith("RAPPORTO-BANCO-")]
        report = open(os.path.join(d, rep[0])).read() if rep else ""
        log = open(os.path.join(d, [f for f in os.listdir(d) if f.startswith("banco-") and f.endswith(".log")][0])).read()
        status = T.load(os.path.join(d, "banco.json"))
        left = os.path.exists(cells)
    return rc, data, report, log, status, left


# ---------------------------------------------------------------------------------------------------- the tests
def t_units():
    group("the pieces: a page's cells and the user's bindings, the Launchpad's message of each grid press, the values back")
    data = {"params": {"cell_bindings": {"fill": {"channel": 12, "cc": 99, "on": 100}}}, "params_schema": schema_of("sagga_remote")}
    b = R.page_bindings(data)
    check(b["fill"] == (12, 99, "button", 100, 0) and b["play"][2] == "trigger" and b["morph"][2] == "fader" and len(b) == 71,   # (0.32.1: + SCENES, SNAPS)
          "page_bindings: the schema's cells, the user's binding over one (%s %s)" % (b.get("fill"), len(b)))
    bad = []
    for st, d1, d2 in [(0x9F, y * 16 + x, v) for y in range(8) for x in range(16) for v in (100, 0)] + \
                      [(0xBE, i, v) for i in range(32) for v in (127, 0)]:
        got = []
        br = B.Bridge(lambda i, m: None, lambda m: got.append(list(m)), model="mk3")
        side, lp = R.lp_message((st, d1, d2))
        br.lp_in(side, lp)
        if got != [[st, d1, d2]]:
            bad.append(((st, d1, d2), side, lp, got))
    check(not bad, "every pad (128) and button (32) of the grid: the Launchpad's message the bridge turns back into it (%s)" % bad[:3])

    class VAPI:
        def get(self, path):
            p = path.rsplit("/", 1)[1]
            if p == "mod":
                return {"params": {"lfo_sw3": True, "lfo_sw4": False, "rate": 40}, "params_schema": schema_of("sagga_mod")}
            return {"params": {"fill": True, "temp": False, "swing": 70, "play": False}, "params_schema": schema_of("sagga_remote")}
    fb = {("cc", 13, 23): 127, ("cc", 13, 37): 127, ("cc", 13, 9): 70, ("cc", 13, 20): 127, ("note", 12, 103): 127,
          ("note", 12, 104): 127, ("cc", 12, 94): 41}
    wrong, n, later = R.values_back(VAPI(), {"sagga_remote": "rem", "sagga_mod": "mod"}, fb)
    check(n == 6 and sorted(w[1] for w in wrong) == ["lfo_sw4", "rate", "temp"] and not later,
          "values_back: a switch, a knob, an LFO switch that did not follow; a trigger not asked (%d %s)" % (n, wrong))
    # 0.32.1: who spoke last. The FM-1 said every value at 1000 ms; the Pi pressed RATE at 5000 (after: the page's 40 is
    # the Pi's own, not compared), TEMP at 500 (before: the FM-1's word is the last, still wrong), LFO 4 at 2000 (after)
    when = {k: 1000.0 for k in fb}
    done = [[4950.0, "pagina", [0xBC, 94, 40], "sagga_mod", "rate", 40, 100.0], [450.0, "pagina", [0xBD, 37, 0], "sagga_remote", "temp", False, 100.0],
            [1950.0, "pagina", [0x8C, 104, 0], "sagga_mod", "lfo_sw4", False, 100.0], [100.0, "grid", [0x9F, 1, 100]]]
    pr = R.pressed_last(done)
    check(pr == {("sagga_mod", "rate"): 5000.0, ("sagga_remote", "temp"): 500.0, ("sagga_mod", "lfo_sw4"): 2000.0},
          "pressed_last: the end of the Pi's last press of each cell (%s)" % pr)
    wrong, n, later = R.values_back(VAPI(), {"sagga_remote": "rem", "sagga_mod": "mod"}, fb, when, pr)
    check(n == 4 and [w[1] for w in wrong] == ["temp"] and sorted(w[1] for w in later) == ["lfo_sw4", "rate"],
          "0.32.1 values_back: a cell the Pi pressed after the FM-1's last word is not compared, one pressed before is (%d %s %s)" % (n, wrong, later))
    when[("cc", 12, 94)] = 5400.0                       # (the FM-1 says RATE again after the press: compared again)
    wrong, n, later = R.values_back(VAPI(), {"sagga_remote": "rem", "sagga_mod": "mod"}, fb, when, pr)
    check(n == 5 and sorted(w[1] for w in wrong) == ["rate", "temp"] and [w[1] for w in later] == ["lfo_sw4"],
          "0.32.1 values_back: the FM-1 speaks again after the press: its word is the last (%d %s %s)" % (n, wrong, later))


def t_audit():
    group("the matrix: what must be there, what must not")
    dev = None
    a = FakeAPI(dev)
    f, facts = R.audit(a, services={"raspimidihub": ("active", "active")})
    lv = [x[0] for x in f]
    check("ERRORE" not in lv and facts["porte_fm1"] == 2 and facts["fm1"] == "Felucca",
          "the matrix as it should be: no error (%s)" % f)
    check(any("SAGGA Live" in x[1] for x in f) and any("MicroFreak manda MIDI all'FM-1" in x[1] for x in f),
          "a page not added (seen), a synth that sends to the FM-1 (to look at) (%s)" % f)
    a = FakeAPI(dev, routing="all", extra_conns=[(FM1, 1, SYNTH, 0), (LP, 0, FM1, 1)], launchpad=True)
    a.conns.discard((PAGE_CLIENT["sagga_mutes"], 0, FM1, 1))
    a.conns.discard((FM1, 1, PAGE_CLIENT["sagga_break"], 0))
    f, _ = R.audit(a, services={"sagga-grid-bridge": ("failed", "active")})
    txt = " | ".join("%s: %s" % x for x in f)
    for what, cond in (("Connect all", "Default routing" in txt), ("the cell Mutes -> FM-1 port 2", "manca la cella SAGGA Mutes -> FM-1 porta 2" in txt),
                       ("the cell FM-1 -> Break", "manca la cella FM-1 porta 2 -> SAGGA Break" in txt and "DA GUARDARE: manca la cella FM-1" in txt),
                       ("the Launchpad's cell", "ERRORE: il Launchpad ha una cella" in txt),
                       ("FM-1 port 2 to a synth", "ERRORE: la porta 2 dell'FM-1 va a MicroFreak" in txt),
                       ("the bridge's service", "sagga-grid-bridge e' failed" in txt)):
        check(cond, "audit: %s (%s)" % (what, txt[:300]))

    class Dead:
        def get(self, path):
            raise IOError("connection refused")
    f, _ = R.audit(Dead())
    check(f and f[0][0] == "ERRORE" and "non risponde" in f[0][1], "RaspiMIDIHub down: said (%s)" % f)

    # 0.23.2: Controlla la matrice says the bridge's last lines too (one press, and the file tells how the bridge is)
    def boom(cmd):
        raise OSError("no journalctl here")
    check(R.bridge_lines(boom) == [] and R.bridge_lines(FakeSystem(journal="\n-- No entries --\n")) == [], "the bridge's lines: none where there is no journal")
    many = FakeSystem(journal="".join("[ %d.0] python3[9]: line %d\n" % (k, k) for k in range(60)))
    got = R.bridge_lines(many)
    check(len(got) == 25 and got[-1].endswith("line 59") and got[0].endswith("line 35"), "the bridge's lines: the last 25 (%s)" % got[-1:])
    sysm = FakeSystem(journal="[  7.0] python3[5]: no FM-1 (no port matches --fm1 'fm-1|felucca'): the bridge waits for it\n")
    rc, data, report, log, status, left = run_main(None, FakeAPI(None), sysm, args=("--solo-matrice",))
    check("IL BRIDGE DEL GRID (le sue ultime righe)" in log and "the bridge waits for it" in log and "ripartito" not in log,
          "Controlla la matrice: the bridge's last lines in its log (%s)" % log[-300:])
    rc, data, report, log, status, left = run_main(None, FakeAPI(None), FakeSystem(), args=("--solo-matrice",))
    check("IL BRIDGE DEL GRID" not in log, "no journal: no heading")


def t_prova():
    group("a prova: the pages through the hub, the bridge, the synths away and back, what the FM-1 heard")
    dev = BancoFM1(deaf=1)
    api = FakeAPI(dev, own={"sagga_remote": {"fill": {"channel": 13, "cc": 99}}})
    sysm = FakeSystem(journal="-- Journal begins at Mon 2026-10-26 --\n[  41.2] python3[612]: FM-1: Felucca MIDI 2\n[  41.9] python3[612]: no Launchpads: the bridge runs without the grid\n")
    dev.sysm = sysm
    before = set(api.conns)
    rc, data, report, log, status, left = run_main(dev, api, sysm)
    # 0.23.2: the bridge's own lines in the log - its last ones with the matrix, those of its start at the very end
    jc = [c for c in sysm.calls if c[0] == "journalctl" and "sagga-grid-bridge" in c]
    a_, b_ = log.find("IL BRIDGE DEL GRID (le sue ultime righe)"), log.find("IL BRIDGE DEL GRID (ripartito)")
    check(0 <= log.find("LA MATRICE") < a_ < log.find("il bridge del grid riparte") < log.find("Raccolta:") < b_,
          "0.23.2 the bridge's lines: with the matrix, and after its start, last (%s %s)" % (a_, b_))
    check(log.count("no Launchpads: the bridge runs without the grid") == 2 and "Journal begins" not in log,
          "... its lines as the journal has them, without the journal's own (%s)" % log.count("no Launchpads"))
    check(len(jc) == 2 and jc[0][-2:] == ["-n", "25"] and jc[1][-2] == "-S" and jc[1][-1].startswith("@") and "-k" not in jc[0],
          "... asked of the bridge's unit: the last 25, then since it was started (%s)" % jc)
    check(rc == 0 and data and len(data["sessioni"]) == 2, "two sessions, rc 0 (%s)\n%s" % (rc, log[-1500:]))
    check(status.get("rc") == 0 and status.get("pid") == os.getpid(), "banco.json: the pid, then rc (%s)" % status)
    check(api.synth_during == 0 and (FM1, 0, SYNTH, 0) in api.deletes and (SYNTH, 0, FM1, 0) in api.deletes,
          "the synths' cells away before the first page was pressed (%s %s)" % (api.synth_during, api.deletes))
    check(api.conns == before and not left, "... and back at the end, the file of the cells gone (%s)" % sorted(api.conns ^ before))
    check("aveva un filtro" in log, "a cell with a filter: said to look at it")
    stops = [c for c in sysm.calls if c[:2] in (["systemctl", "stop"], ["systemctl", "start"])]
    check(stops == [["systemctl", "stop", "sagga-grid-bridge"], ["systemctl", "start", "sagga-grid-bridge"]],
          "the bridge's service stopped for the prova, started at the end (%s)" % stops)
    check(dev.bridge_up_at_yes is True and dev.opens == 2 and "(di nuovo)" in log and "nessun tasto premuto" in log,
          "the question asked while the grid is still attached (no GRID LOST over it), and again when nobody "
          "answered (%s %s)" % (dev.bridge_up_at_yes, dev.opens))
    check(dev.imported and dev.boots == 2 and dev.closes == 1, "the project back in memory; a reboot a session, CLOSE (%s %s)" % (dev.boots, dev.closes))
    if not data:
        return
    for s in data["sessioni"]:
        hw = s["fm1"]
        via = {}
        for r in hw["reali_fatti"]:
            via[r[1]] = via.get(r[1], 0) + 1
        check(via.get("pagina") == 3 and via.get("diretto") == 2 and via.get("grid", 0) >= 10,
              "%s: 3 messages through the hub's pages, 2 straight (the page not added, the plan's own), the bridge's %s" % (s["nome"], via))
        fill = [r for r in hw["reali_fatti"] if r[1] == "pagina" and r[4] == "fill"]
        check(fill and fill[0][2] == [0xBD, 99, 127] and any(m[:3] == [0xBD, 99, 127] for m in dev.got),
              "%s: the cell FILL bound by the user to CC 99: that is what the page sends and the Pi notes (%s)" % (s["nome"], fill[:1]))
        check(hw["ponte"] == [] and [0xBF, 118, 127] in [r[2] for r in hw["reali_fatti"] if r[1] == "grid"],
              "%s: the bridge attached and translated every press (%s)" % (s["nome"], hw["ponte"]))
        lost, other = BT.roads(s)
        check(hw["sentiti"] and not lost and not other, "%s: every message the Pi sent was heard by the FM-1, nothing else (%s %s)" % (s["nome"], lost, other))
        bridge, _ = BT.lights(s, None)
        snaps = hw["luci"]
        check(len(snaps) == 3 and any(x["ruoli"] for x in snaps.values()) and not bridge,
              "%s: the grid's lights at each probe, as the FM-1 sent them (%s %s)" % (s["nome"], [len(x["ruoli"]) for x in snaps.values()], bridge))
        check(any("FILL" in w.upper() or "fill" in w for w in hw["proprie"]), "%s: the user's binding said (%s)" % (s["nome"], hw["proprie"]))
    check("LA MATRICE" in log and "SAGGA Live" in log and "| b001 |" in report, "the log and the report (%s)" % report[:200])


def t_interrupted():
    group("a prova that ended without putting the cells back: the next run (or Rimetti) does it; the matrix alone")
    dev = BancoFM1()
    api = FakeAPI(dev)
    with tempfile.TemporaryDirectory() as d:
        cells = os.path.join(d, "celle.json")
        saved, _ = R.fm1_cells(api)
        R.detach(api, [], lambda x: None, cells)
        check(os.path.exists(cells) and not any(SYNTH in (c[0], c[2]) for c in api.conns), "detach: the cells away, the file written")
        api.fm1_online = False
        said = []
        left = R.put_back(api, cells, said.append)
        check(left == 2 and os.path.exists(cells) and any("non e' nella matrice" in x for x in said),
              "the FM-1 not there: the cells stay to put back, the file kept (%s %s)" % (left, said))
        api.fm1_online = True
        rc = R.main(["--rimetti", "--out", d, "--celle", cells], api=api, system=FakeSystem())
        check(rc == 0 and not os.path.exists(cells) and (FM1, 0, SYNTH, 0) in api.conns and (SYNTH, 0, FM1, 0) in api.conns,
              "--rimetti: back, the file gone (%s)" % rc)
        check(T.load(os.path.join(d, "banco.json")).get("modo") == "rimetti", "banco.json says what ran")
        api.conns.discard((PAGE_CLIENT["sagga_mod"], 0, FM1, 1))
        rc = R.main(["--solo-matrice", "--out", d, "--celle", cells], api=api, system=FakeSystem())
        rep = open(os.path.join(d, [f for f in os.listdir(d) if f.startswith("RAPPORTO-BANCO-")][0])).read()
        check(rc == 1 and "manca la cella SAGGA Mod -> FM-1 porta 2" in rep and not api.deletes[2:],
              "--solo-matrice: the missing cell in the report, rc 1, nothing taken away (%s)" % rc)


def t_fm1_plan():
    group("the whole FM-1's plan (the PC explorer's sessions, no real roads) run by the Pi")
    dev = BancoFM1()
    api = FakeAPI(dev)
    plan = HX.plan(2, midi=True)
    plan["firmware"] = "0.20.3"
    rc, data, report, log, status, left = run_main(dev, api, FakeSystem(), plan=plan)
    check(rc == 0 and data and len(data["sessioni"]) == 2 and data["fatti"].get("piano") == "fm1",
          "two sessions, rc 0, the raccolta says which plan (%s %s)" % (rc, data and data.get("fatti")))
    check(data and all(not s["fm1"]["reali_fatti"] and s["fm1"]["sonde"] for s in data["sessioni"]),
          "nothing through the hub nor the bridge, every probe there")
    check("l'FM-1 completo" in log and "FM-1 completo" in report and not left, "the log and the report say it (%s)" % report[:80])


def t_old_firmware():
    group("an FM-1 older than the plan: nothing done, the cells untouched")
    dev = BancoFM1()
    dev.version = "0.20"
    api = FakeAPI(dev)
    before = set(api.conns)
    rc, data, report, log, status, left = run_main(dev, api, FakeSystem())
    check(rc == 3 and "aggiorna l'FM-1" in log and api.conns == before and not api.deletes and status.get("rc") == 3,
          "0.20: refused, rc 3, the matrix as it was (%s)" % rc)


def t_no_yes():
    group("nobody says yes: asked three times, then nothing done (the bridge never stopped, the cells untouched)")
    dev = BancoFM1(deaf=3)
    api = FakeAPI(dev)
    sysm = FakeSystem()
    before = set(api.conns)
    rc, data, report, log, status, left = run_main(dev, api, sysm)
    check(rc == 1 and dev.opens == 3 and "Niente prova" in log and api.conns == before and
          not [c for c in sysm.calls if c[:2] in (["systemctl", "stop"], ["systemctl", "start"])],
          "three questions, rc 1, the bridge and the matrix left alone (%s %s %s)" % (rc, dev.opens, sysm.calls))


def t_lost_cells():
    group("0.20.9: RaspiMIDIHub loses the FM-1's cells at each reboot (its autosave): the Pi puts them back, the pages work")
    dev = BancoFM1()
    api = LosingAPI(dev)
    before = set(api.conns)
    rc, data, report, log, status, left = run_main(dev, api, FakeSystem())
    check(rc == 0 and data and len(data["sessioni"]) == 2 and api.lost >= 20, "two sessions, the cells lost at each reboot (%s %s)" % (rc, api.lost))
    check(api.conns == before and not left, "at the end the matrix as it was (%s)" % sorted(api.conns ^ before))
    for s_ in (data or {}).get("sessioni", []):
        hw = s_["fm1"]
        check(hw["celle_fm1"]["rimesse"] == 10 and not hw["celle_fm1"]["non_tornano"],
              "%s: the 10 cells of the pages put back before the session (%s)" % (s_["nome"], hw["celle_fm1"]))
        via = [r for r in hw["reali_fatti"] if r[1] == "pagina"]
        check(len(via) == 3 and not hw["valori"]["sbagliati"], "%s: the pages through the hub, their values back (%s)" % (s_["nome"], hw["valori"]))
    check("RaspiMIDIHub aveva perso 10 celle dell'FM-1 nel riavvio" in log and "VALORI" not in log and "il Pi le ha rimesse" in report,
          "said in the log and the report (%s)" % report[-300:])
    check(data and data["fatti"].get("celle_rimesse") == 30, "the count in the raccolta: 2 sessions and the CLOSE (%s)" % (data or {}).get("fatti"))


def t_deaf_reboot():
    group("0.20.9: the FM-1 deaf after a reboot (the 0.20.8 banco's 4th): the USB found again, the run goes on; DIAG and the kernel in the log")
    dev = BancoFM1()
    dev.version = "0.20.9"
    dev.deaf_after = 2                               # (the second BOOT)
    api = FakeAPI(dev)
    asked = []
    orig = R.K.usb_reenumerate

    def reenum(path, sysfs, wait=None):
        asked.append(path)
        dev.deaf_now = False                         # (found again: it hears)
        return orig(path, sysfs, wait=lambda s: None, devfs=os.path.join(sysfs, "no-dev"))
    R.K.usb_reenumerate, R.FIRST_WAIT, R.MORE_WAIT = reenum, 3.0, 8.0
    kern = ("[ 812.1] usb 1-1.2: USB disconnect, device number 7\n[ 812.9] usb 1-1.2: new full-speed USB device number 8 using xhci_hcd\n"
            "[ 813.0] systemd[1]: something else\n")
    try:
        with tempfile.TemporaryDirectory() as sy:
            os.makedirs(os.path.join(sy, "1-1.2"))
            for n, v in (("product", "Felucca\n"), ("authorized", "1\n")):
                with open(os.path.join(sy, "1-1.2", n), "w") as f:
                    f.write(v)
            rc, data, report, log, status, left = run_main(dev, api, FakeSystem(kernel=kern), sysfs=sy)
    finally:
        R.K.usb_reenumerate, R.FIRST_WAIT, R.MORE_WAIT = orig, 12.0, 30.0
    check(rc == 0 and data and len(data["sessioni"]) == 2 and asked == ["1-1.2"], "the USB found again once, two sessions (%s %s)\n%s" % (rc, asked, log[-800:]))
    check("il Pi lo fa ritrovare all'USB" in log and "l'FM-1 ha risposto dopo" in log, "said in the log")
    r2 = data and data["sessioni"][1]["fm1"]["riavvio"]
    check(r2 and r2.get("usb_di_nuovo") == ["1-1.2", "authorized"] and r2.get("diag", {}).get("hellos") == 1 and
          r2.get("diag", {}).get("cfg_ms") == 350 and r2.get("kernel_prima"),
          "the second session's reboot: the USB found again, the FM-1's counters (%s)" % (r2,))
    check("kernel: [ 812.1] usb 1-1.2: USB disconnect" in log and "something else" not in log, "the kernel's USB lines in the log, only those")


def t_conti():
    group("0.23.1: the session's account - what the FM-1 says it sent against what the Pi heard: equal, nothing said; two note-offs lost on the way: said, and where")
    dev = CountFM1()
    rc, data, report, log, status, left = run_main(dev, FakeAPI(dev), FakeSystem(kernel="[ 55.0] usb 1-1.2: reset full-speed USB device number 9\n[ 55.1] systemd[1]: x\n"))
    c = [x["fm1"].get("conti") for x in (data or {}).get("sessioni", [])]
    check(rc == 0 and len(c) == 2 and all(c) and dev.quiets == 2, "two sessions, each with its account, QUIET asked twice (%s %s)\n%s" % (rc, dev.quiets, log[-600:]))
    if len(c) == 2 and all(c):
        check(all(x["fermo"] == [True, True] and x["quiet"] == 1 for x in c), "the ports stood still at both ends (%s)" % [x["fermo"] for x in c])
        check(all(x["fm1"] == x["pi"] and x["fm1"]["p1"]["on"] > 0 and x["fm1"]["p1"]["off"] > 0 and x["fm1"]["p2"]["bytes"] > 1000 for x in c),
              "sent and heard are the same numbers, port by port and kind by kind: the notes, the lights, the bytes of the SysEx (%s)" % [(x["fm1"], x["pi"]) for x in c if x["fm1"] != x["pi"]][:1])
        check(all(x["usb"]["tx_ev"] == sum(x["fm1"][p][k] for p in ("p1", "p2") for k in T.OUT_KINDS[:5]) for x in c) and all(x["alsa"] is None for x in c),
              "the ring's account goes with them; no driver counts on this computer (%s)" % (c[0]["usb"],))
        check("CONTI" not in log and all(R.X.counts_verdict(x) == [] for x in c), "nothing to say in the log")
    k = [x["fm1"].get("kernel") for x in (data or {}).get("sessioni", [])]
    check(k and k[0] == ["[ 55.0] usb 1-1.2: reset full-speed USB device number 9"], "the kernel's USB lines of each session kept with it (%s)" % k[:1])
    # two note-offs of port 1 counted by the FM-1 and never arrived
    dev = CountFM1(eat={(0, "off"): 2})
    rc, data, report, log, status, left = run_main(dev, FakeAPI(dev), FakeSystem())
    c = [x["fm1"].get("conti") for x in (data or {}).get("sessioni", [])]
    lost = [x["fm1"]["p1"]["off"] - x["pi"]["p1"]["off"] for x in c if x]
    check(rc == 0 and sum(lost) == 2 and lost[0] in (1, 2), "the account shows them: %s note-offs of port 1 sent and not heard" % lost)
    v = R.X.counts_verdict(c[0]) if c and c[0] else []
    check(v and "porta 1: l'FM-1 ha mandato %d note-off che il programma non ha sentito" % lost[0] in v[0] and "persi dopo l'FM-1" in v[-1],
          "the verdict: which, how many, and that the FM-1 had put them in its USB packets (%s)" % v)
    check("CONTI: porta 1: l'FM-1 ha mandato" in log and "b001" in log, "said in the log, on the session's line (%s)" % [ln for ln in log.splitlines() if "CONTI" in ln][:1])
    # an FM-1 before 0.23.1: no account, no QUIET sent, everything else as before
    dev = BancoFM1()
    dev.version = "0.23"
    seen = []
    orig = dev.rx
    dev.rx = lambda data: (seen.append(list(data)[5]) if list(data)[:5] == T.HEAD + [T.SX_TST] else None, orig(data))[1]
    rc, data, report, log, status, left = run_main(dev, FakeAPI(dev), FakeSystem())
    check(rc == 0 and data and all("conti" not in x["fm1"] for x in data["sessioni"]) and T.QUIET not in seen and "CONTI" not in log,
          "an FM-1 0.23: no account asked (%s)" % sorted(set(seen)))


def t_lost_fm1():
    group("0.20.9: the FM-1 does not come back: the project of before the prova into the hub's library, what to do said")
    dev = BancoFM1()
    dev.deaf_after = 2
    api = FakeAPI(dev)
    R.FIRST_WAIT, R.MORE_WAIT = 2.0, 2.0
    lib = []
    try:
        rc, data, report, log, status, left = run_main(dev, api, FakeSystem(kernel="[ 9.0] usb 1-1.2: device descriptor read/64, error -71\n"), library=lib)
    finally:
        R.FIRST_WAIT, R.MORE_WAIT = 12.0, 30.0
    check(rc == 1 and "non torna nel test" in log and "kernel: [ 9.0] usb 1-1.2: device descriptor" in log,
          "stopped, the kernel's lines said (%s)" % rc)
    check(len(lib) == 1 and lib[0][0].startswith("prima-del-banco-") and lib[0][1] == dev.project,
          "the project of before the prova in the library (%s)" % [n for n, _ in lib])
    check("nella libreria del hub: prima-del-banco-" in log and "Manda all'FM-1" in log and not dev.imported, "said how to put it back")
    check(api.conns >= {(PAGE_CLIENT["sagga_remote"], 0, FM1, 1)} and not left, "the synths' cells back all the same (%s)" % left)


def main():
    for t in (t_units, t_audit, t_prova, t_interrupted, t_fm1_plan, t_old_firmware, t_no_yes, t_lost_cells, t_deaf_reboot, t_conti, t_lost_fm1):
        try:
            t()
        except Exception as e:
            import traceback
            traceback.print_exc()
            FAILS.append("%s raised %r" % (t.__name__, e))
    print("sagga banco: %d checks, %d failures" % (CHECKS[0], len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    rc = main()
    sys.stdout.flush()
    os._exit(rc)
