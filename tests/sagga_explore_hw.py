#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA SEQ, l'esploratore sull'FM-1 vero.

1. Il piano (qui, in WSL):        python3 tests/sagga_explore.py --hw-piano build/hwtest/piano.json [--sessioni 20]
   le sessioni a caso dell'esploratore (una situazione, poi 60 gesti, una sonda dopo ognuno) come eventi a tempo:
   premi, lascia, gira, tasti, MASTER, sonda; 0.18: anche il MIDI che entra - il tablet (le pagine del hub: canali 12-14)
   e i pad del grid - come se arrivassero dalla porta del remoto (il PC al posto del Pi).
2. Sull'FM-1 (Windows):           tools/hwtest/run_hw_explore.ps1 piano.json
   per ogni sessione l'FM-1 si riavvia nel test, il PC preme i tasti ai tempi del piano, l'FM-1 dice dove ha preso
   ogni evento (il suo ms e il suo tick di clock) e manda le sonde; il PC tiene tutto in raccolta-<data>.json.
3. Il confronto (qui):            python3 tests/sagga_explore.py --hw raccolta-<data>.json
   ogni sessione rifatta nel simulatore con ogni evento dove l'FM-1 l'ha preso davvero: le due macchine devono essere
   uguali sonda per sonda. Piu' le regole sui dati dell'FM-1: FASE, NOTE APPESE, il clock, le note perse, il firmware
   che si pianta, il ciclo che si ferma. -> build/explore/RAPPORTO-HW.md

Senza FM-1, --hw-prova fa i passi 2 e 3 con il simulatore al posto dell'FM-1 (con il costo dello schermo acceso, come
il vero): deve dire che tutto e' uguale. E' nella suite dei test.
"""
import os
import random
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sagga_explore as E  # noqa: E402

S = E.S
sys.path.insert(0, os.path.join(E.ROOT, "tools", "hwtest"))
import sagga_testport as T  # noqa: E402

OFF = 400                         # the plan's first event, after GO (the PC has sent its first frames by then)
GO_SIM = 3000                     # the stand-in's GO: as an FM-1 a few seconds after its reboot
SX_RE = re.compile(r"^\s*(\d+) ms  SYSEX out ([0-9A-F ]+?)( port 2)?$")


def to_events(lines):
    """host script lines -> [(t, kind, a, b)], or None for a line the PC cannot do (a SysEx, a USB reconnect ...).
    0.18: MIDI that comes in (the tablet's pages, the grid's pads and buttons) as MIDI events on the remote's port"""
    out = []
    for line in lines:
        p = line.split()
        t, verb, a = int(p[0]), p[1], p[2:]
        if verb == "midi":
            st, d1, d2 = int(a[0], 0), int(a[1]), int(a[2])
            out.append((t, T.MIDI) + T.midi_ev(st, d1, d2, T.PORT2 if len(a) > 3 and a[3] == "2" else T.PORT_REMOTE))
        elif verb in ("pad", "ctl", "attach", "detach", "hb"):
            if verb == "pad":
                st, d1, d2 = 0x9F, int(a[1]) * 16 + int(a[0]), int(a[2]) if len(a) > 2 else 100
            elif verb == "ctl":
                st, d1, d2 = 0xBE, int(a[0]), int(a[1]) if len(a) > 1 else 127
            else:
                st, d1, d2 = 0xBF, 118, {"attach": 127, "detach": 0, "hb": 64}[verb]
            out.append((t, T.MIDI) + T.midi_ev(st, d1, d2))
        elif verb == "keys":
            m = int(a[0], 0)
            out.append((t, T.KEYS, m & 0x3FFF, m >> 14))
        elif verb == "press":
            out.append((t, T.PRESS, int(a[0]), 0))
        elif verb == "release":
            out.append((t, T.RELEASE, int(a[0]), 0))
        elif verb == "enc":
            out.append((t, T.ENC, int(a[0]), 8192 + int(a[1])))
        elif verb == "knob":
            out.append((t, T.KNOB, int(a[0]), 0))
        elif verb == "probe":
            out.append((t, T.PROBE, 0, 0))
        else:
            return None
    return out


def gesture_ok(g):
    s = S.Script()
    g.do(s, 1000)
    return to_events(E._lines(s)) is not None


def situation_ok(sit):
    s = S.Script()
    sit.setup(s)
    return to_events(E._lines(s)) is not None


HB_MS = 1500                      # 0.18: the grid's keep-alive, as the bridge sends it (the FM-1 lets go after 3.5 s of silence)


def session_plan(sit, gs, name):
    """the explorer's session (as session_check plays it) as the PC's events; the probes' roles beside"""
    s = S.Script()
    t0 = int(sit.setup(s)) + 600
    b = S.Script()
    t = t0 + 10
    roles = ["inizio", "pronto"]
    for k, g in enumerate(gs):
        t = int(g.do(b, max(t, t0 + 10 + k * 700)))
        b.raw(t0 + (k + 1) * 700 - 20, "probe")
        roles.append("gesto %d" % (k + 1))
    tend = t0 + (len(gs) + 1) * 700 + int(2 * E.BAR_MS)
    b.raw(tend, "probe")
    b.tap_btn(tend + 20, S.PLAY)
    b.raw(tend + 600, "probe")
    roles += ["battuta", "fermo"]
    lines = ["0 probe"] + E._lines(s) + ["%d probe" % t0] + E._lines(b)
    if sit.grid:                                        # (the bridge's keep-alive, the whole session long)
        lines = sorted(lines + ["%d hb" % k for k in range(HB_MS, tend + 600, HB_MS)], key=lambda x: int(x.split()[0]))
    ev = to_events(lines)
    ev = [(e[0] + OFF,) + tuple(e[1:]) for e in ev] + [(tend + 700 + OFF, T.END, 0, 0)]
    return {"nome": name, "situazione": sit.name, "gesti": [g.name for g in gs], "eventi": [list(e) for e in ev],
            "sonde": roles}


def piano(n, length, seed, tablet=0):
    """n sessions, a situation each in turn; 0.18: then `tablet` more in the tablet's situations (the tablet, the grid
    and the panel at once)"""
    sits = [x for x in E.SITUAZIONI if x.hw and situation_ok(x)]
    pool = [g for g in E.catalogo(grid=True, tablet=True) if g.name != "niente" and "andata" not in g.tags and gesture_ok(g)]
    rnd = random.Random(seed)
    out = []
    tab = [x for x in sits if x.tablet]
    for k in range(n + (tablet if tab else 0)):
        sit = sits[k % len(sits)] if k < n else tab[(k - n) % len(tab)]
        cand = [g for g in pool if E.fits(g, sit)]
        gs = [E.pick(rnd, cand, sit) for _ in range(length)]
        sp = session_plan(sit, gs, "s%03d" % (k + 1))
        while len(sp["eventi"]) > 1000 and len(gs) > 1:      # (the FM-1 keeps the places of 1024 events a session)
            gs = gs[:-1]
            sp = session_plan(sit, gs, "s%03d" % (k + 1))
        out.append(sp)
    return {"versione": 1, "firmware": "0.20", "seme": seed, "sessioni": out}


# ------------------------------------------------------------------------------------------------ the simulator as an FM-1

def _sx(t, b):
    return "%d sx %s" % (t, " ".join("%02X" % x for x in b[1:-1]))


def sim_script(events, go_ms, lcdcost=False, replay=None):
    """the host script that does what the runner does: GO, then the frames paced as it paces them. replay: {idx: (ms, gc)}
    = every event where the FM-1 took it (its t from that ms, its tick as gc)"""
    evs = []
    for i, e in enumerate(events):
        e = list(e)
        if replay is not None:
            if i not in replay:
                break                                  # (the FM-1 did not get that far: an abort, a crash)
            ms, gc = replay[i]
            e = [ms - go_ms] + e[1:4] + [gc]
        evs.append(tuple(e))
    lines = []
    if lcdcost:
        lines.append("0 lcdcost")
    lines += [_sx(go_ms - 30, T.hello()), _sx(go_ms, T.go())]
    pacer = T.Pacer(evs)
    last = evs[-1][0] if evs else 0
    now = 5
    while pacer.sent < len(evs) and now < last + 1000:
        f = pacer.next_frame(now, pacer.free_estimate(now))
        if f:
            lines.append(_sx(go_ms + now, f[0]))
            pacer.sent += f[2]
            now += 3
        else:
            now += 50
    lines.append("%d end" % (go_ms + last + 1500))
    return "\n".join(lines) + "\n", len(evs)


def run_sim(text, testboot=True, settings=None):
    """settings: (USB ports, profile), the FM-1's own settings (HELLO says them), else the simulator's (1, the first)"""
    env = dict(os.environ, HOST_NOWAV="1")
    if testboot:
        env["HOST_TESTBOOT"] = "1"
    if settings:
        env["HOST_SETTINGS"] = "%d,%d" % tuple(settings)
    with tempfile.TemporaryDirectory() as d:
        sp = os.path.join(d, "s.txt")
        with open(sp, "w") as f:
            f.write(text)
        p = subprocess.run([E.BIN, os.path.join(d, "o"), sp], capture_output=True, text=True, cwd=E.ROOT, env=env, timeout=900)
    return p.stdout


def collect(out):
    """the simulator's output -> a session record as the runner keeps one (go, presi, sonde, midi, done)"""
    rec = {"go_ms": None, "presi": {}, "sonde": {}, "midi": [], "done": None, "abort": None, "answers": []}
    pr = T.Probes()
    for line in out.splitlines():
        m = SX_RE.match(line)
        if m:
            a = T.parse(bytes(int(x, 16) for x in m.group(2).split()))
            if not a:
                continue
            if a[0] == "probe":
                pr.add(*a[1])
            elif a[0] == "log":
                for idx, ms, gc in a[1]:
                    rec["presi"][str(idx)] = [ms, gc]
            elif a[0] == "go":
                rec["go_ms"] = a[1]
            elif a[0] == "hello":
                rec["hello_prima"] = a[1]
            elif a[0] == "done":
                rec["done"] = a[1]
            elif a[0] == "abort":
                rec["abort"] = a[1]
            continue
        m = E.MIDI_RE.match(line)
        if m:
            rec["midi"].append([int(m.group(1)), int(m.group(2), 16), int(m.group(3)), int(m.group(4))])
    rec["sonde"] = {str(k): v for k, v in pr.done.items()}
    return rec


def run_like_fm1(plan_session, lcdcost=True, settings=None):
    text, _ = sim_script(plan_session["eventi"], GO_SIM, lcdcost=lcdcost)
    rec = collect(run_sim(text, settings=settings))
    out = dict(plan_session)
    out["fm1"] = rec
    return out


# ---------------------------------------------------------------------------------------------------------- the comparison

def pdiff(a, b):
    """every field that differs between two probes, the track's step and the message too ([] = the same machine)"""
    out = []
    for who in ["G"] + ["T%d" % t for t in range(1, 17)]:
        x, y = a.get(who, {}), b.get(who, {})
        for k in sorted(set(x) | set(y)):
            if x.get(k) != y.get(k):
                out.append(("%s.%s" % (who, k), x.get(k), y.get(k)))
    return out


def msg_expiry(x):
    """the message line: one machine still shows it, the other has let it go (it lasts 1.6 s from when the key was
    read, and the boot one 3 s from the boot: the FM-1 reads its keys a few ms later and boots longer) = timing"""
    f, a, b = x
    return f == "G.msg" and (not a or not b)


def steps_only(d):
    """the steps moved, or a track's "ok" could not be asked on one side ("-": a realign due at the next tick, a length
    waiting for the bar): where the probe fell, not what the machine does"""
    return bool(d) and all(f.endswith(".step") or (f.endswith(".ok") and "-" in (a, b)) for f, a, b in d)


def edge_fields(d):
    """the steps moved, and with them only what a step's edge carries: the pattern a queue switched at the loop's end
    (pat, steps#): equal again later, this is the edge seen from its two sides"""
    return any(f.endswith(".step") for f, a, b in d) and all(f.split(".")[-1] in ("step", "pat", "steps#") for f, a, b in d)


def at_step_edge(d, sp):
    """every difference is a track's step, the FM-1 one step behind or ahead of the simulator on all of them, the
    same way: the probe was read on the tick a step starts (the order of the two inside that tick)"""
    if not all(f.endswith(".step") for f, a, b in d):
        return False
    dirs = set()
    for f, a, b in d:
        try:
            sa, sb = int(a), int(b)
            ln = int(sp.get(f.split(".")[0], {}).get("len", 64)) or 64
        except (TypeError, ValueError):
            return False
        dd = (sb - sa) % ln
        if dd == 1:
            dirs.add(1)
        elif dd == ln - 1:
            dirs.add(-1)
        else:
            return False
    return len(dirs) == 1


def probe_events(session):
    """the indices of the probe events, in order, with their roles"""
    idx = [i for i, e in enumerate(session["eventi"]) if e[1] == T.PROBE]
    return list(zip(idx, session.get("sonde") or ["?"] * len(idx)))


def compare(session):
    """-> (findings [(rule, level, what)], the replay's record)"""
    hw = session["fm1"]
    found = []
    if hw.get("errore"):
        found.append(("MORTO", "ERRORE", hw["errore"]))
    hello = hw.get("hello_dopo") or {}
    if hello.get("fault_pc"):
        found.append(("MORTO", "ERRORE", "il firmware si e' piantato (vettore %X, PC %08X)" % (hello.get("fault_vec", 0), hello["fault_pc"])))
    if hw.get("abort") is not None:
        found.append(("FERMATO", "DA GUARDARE", "fermato da una mano sull'FM-1"))
    if hw.get("go_ms") is None:
        found.append(("MORTO", "ERRORE", "l'FM-1 non ha risposto a GO"))
        return found, None
    replay = {int(k): tuple(v) for k, v in hw["presi"].items()}
    hp = hw.get("hello_prima") or {}
    settings = (hp.get("usb_ports", 1), hp.get("profile", 0)) if "usb_ports" in hp else None

    def replay_sim(rp):
        text, n = sim_script(session["eventi"], hw["go_ms"], replay=rp)
        return collect(run_sim(text, settings=settings)), n

    sim, n = replay_sim(replay)
    probes = probe_events(session)
    hw_p = {int(k): T.probe_dict(v) for k, v in hw["sonde"].items()}
    sim_p = {int(k): T.probe_dict(v) for k, v in sim["sonde"].items()}
    common = [(i, r) for i, r in probes if i in hw_p and i in sim_p]
    missing = [r for i, r in probes if i < n and i not in hw_p]
    if missing:
        found.append(("SONDE", "DA GUARDARE", "%d sonde non arrivate dall'FM-1 (%s)" % (len(missing), ", ".join(missing[:4]))))
    # fields that differ at the very first probe are how the two are built, not what they do (a struct laid out
    # otherwise by the FM-1's compiler: its hash): left out, and said
    systematic = set()
    if common:
        i0 = common[0][0]
        systematic = {x[0] for x in pdiff(sim_p[i0], hw_p[i0]) if not msg_expiry(x)}   # (0.13: a message one shows and the
                                                       #  other has let go - the FM-1's PC TEST boot line - is timing)
        if systematic:
            found.append(("COSTRUZIONE", "DA GUARDARE", "diversi gia' alla prima sonda, lasciati fuori: %s" % ", ".join(sorted(systematic)[:8])))

    def diffs_of(sp):
        return [(i, role, [x for x in pdiff(sp[i], hw_p[i]) if x[0] not in systematic and not msg_expiry(x)])
                for i, role in common if i in sp]

    first = None
    timing = 0
    shifted = []                                       # (the gesture, ms): the FM-1 read its keys that much later
    diffs = diffs_of(sim_p)
    n_ = 0
    while n_ < len(diffs):
        i, role, d = diffs[n_]
        if d and (steps_only(d) or edge_fields(d)) and \
                (role == "fermo" or any(not e for _, _, e in diffs[n_ + 1:n_ + 4])):   # (equal again within three probes)
            timing += 1                                # (the steps only, and equal again later: the probe fell on a step's
            n_ += 1                                    #  edge, or a loop / the STOP took the step on the other side of it)
            continue
        if not d:
            n_ += 1
            continue
        # a difference: the gesture before this probe, its events a few ms later or earlier (the FM-1 reads the keys
        # on its scan, REC and TAKE write at the ms): one that makes this probe the FM-1's is timing, and stays
        prev = max([j for j, _ in probes if j < i] or [-1])
        evs = [j for j in range(prev + 1, i) if j in replay]
        hit = None
        if evs and len(shifted) < 8:
            for ms in (1, 2, 3, -1, -2, -3, 4, 5, 6, 8, -4, -6, -8, 10, 12, 15):
                rp = dict(replay)
                for j in evs:
                    rp[j] = (rp[j][0] + ms,) + tuple(rp[j][1:])
                sim2, _ = replay_sim(rp)
                sp2 = {int(k): T.probe_dict(v) for k, v in sim2["sonde"].items()}
                if i in sp2 and not [x for x in pdiff(sp2[i], hw_p[i]) if x[0] not in systematic and not msg_expiry(x)]:
                    hit = (ms, rp, sim2, sp2)
                    break
        if hit:
            ms, replay, sim, sim_p = hit
            shifted.append((role, ms))
            diffs = diffs_of(sim_p)
            continue
        first = (i, role, d)
        break
    if shifted or timing:
        found.append(("TEMPO", "VISTO", "%s%s" % (
            ("%d sonde sul confine di uno step (gli step soli, poi di nuovo uguali); " % timing) if timing else "",
            ("tasti letti dall'FM-1 qualche ms dopo (o prima), e con quello uguali: " + ", ".join("%s %+d ms" % x for x in shifted)) if shifted else "")))
    if first:
        i, role, d = first
        k = role.split()[-1] if role.startswith("gesto") else None
        upto = session["gesti"][:int(k)] if k else session["gesti"]
        what = "; ".join("%s FM-1 %s, simulatore %s" % (f, b, a) for f, a, b in d[:6]) + (" (e altri %d)" % (len(d) - 6) if len(d) > 6 else "")
        found.append(("SIMULATORE", "ERRORE", "dalla sonda '%s' l'FM-1 e' diverso dal simulatore: %s (gli ultimi gesti: %s)" %
                      (role, what, " -> ".join(upto[-6:]))))
    # the rules on the FM-1's own data
    roles = dict((r, i) for i, r in probes)
    pb = hw_p.get(roles.get("battuta"))
    if pb and pb.get("G", {}).get("play") == "1":
        late = ["T%d" % t for t in range(1, 17) if pb.get("T%d" % t, {}).get("ok") == "0"]
        if late:
            found.append(("FASE", "ERRORE", "fuori fase alla fine: " + ", ".join(late)))
    pf = hw_p.get(roles.get("fermo"))
    if hw.get("done") and pf and pf.get("G", {}).get("play") == "0":      # (the last PLAY may have started it again)
        seen = lambda k: any(p.get("G", {}).get(k) == "1" for p in hw_p.values())   # (0.18: the grid's lights, the tablet's LFO switches)
        hung = E.hung_notes([tuple(m) for m in hw["midi"]], grid=seen("grid"), tablet=seen("tabseen"))
        if hung:
            found.append(("NOTE APPESE", "ERRORE", ", ".join(hung[:6])))
    seen = lambda k: any(p.get("G", {}).get(k) == "1" for p in hw_p.values())
    grid_on, tab_on = seen("grid"), seen("tabseen")
    music = lambda m: not (grid_on and (m[1] & 15) == 15) and not (tab_on and (m[1] & 15) == 12 and 100 <= m[2] < 116)
    notes = lambda midi: sum(1 for m in midi if (m[1] & 0xF0) == 0x90 and m[3] and music(m))   # (0.18: not the grid's lights, nor the tablet's LFO switches)
    clocks = lambda midi: sum(1 for m in midi if m[1] == 0xF8)
    if hw.get("done") and len(sim["sonde"]) and len(hw["sonde"]) == len(sim["sonde"]) and hw["midi"]:
        # the PC hears the FM-1 until it closes the ports for the next session, on its own clock (its 0 is the FM-1's
        # GO): the simulator's MIDI only up to there counts (it plays on 1.5 s after the last event)
        upto = hw["midi"][-1][0] + hw["go_ms"] + 30
        smidi = [m for m in sim["midi"] if m[0] <= upto]
        nh, ns = notes(hw["midi"]), notes(smidi)
        if abs(nh - ns) > 1:                           # (one note on the edge of the window)
            found.append(("NOTE", "ERRORE", "%d note dall'FM-1, %d dal simulatore" % (nh, ns)))
        ch, cs = clocks(hw["midi"]), clocks(smidi)
        if abs(ch - cs) > 2:
            found.append(("CLOCK", "ERRORE", "%d tick di clock dall'FM-1, %d dal simulatore" % (ch, cs)))
    lags = [int(p.get("H", {}).get("lag", 0)) for p in hw_p.values()]
    if lags and max(lags) > 60:
        found.append(("CICLO", "DA GUARDARE", "il ciclo principale si e' fermato fino a %d ms" % max(lags)))
    lost = (hw.get("done") or {}).get("lost", 0)
    if lost:
        found.append(("SONDE", "DA GUARDARE", "%d sonde perse dall'FM-1" % lost))
    return found, sim


REGOLE_HW = {
    "MORTO": "il firmware non si pianta, non si riavvia da solo, risponde",
    "SIMULATORE": "l'FM-1 fa quello che fa il simulatore con gli stessi eventi negli stessi punti: una differenza e' "
                  "il compilatore, l'hardware o una cosa che dipende dal tempo (da capire: mandami la raccolta)",
    "FASE": "due battute dopo i gesti ogni traccia e' dove la battuta dice",
    "NOTE APPESE": "dopo lo STOP ogni nota accesa e' spenta",
    "NOTE": "le note che escono dall'USB sono quelle del simulatore (nessuna persa per strada)",
    "CLOCK": "i tick di clock sono quelli del simulatore",
    "CICLO": "il ciclo principale non si ferma piu' di 60 ms (lo schermo, il salvataggio ...)",
    "SONDE": "ogni sonda arriva",
    "COSTRUZIONE": "le due macchine partono uguali",
    "FERMATO": "nessuna mano sull'FM-1 durante il test",
    "TEMPO": "visto, non un errore: una sonda sul confine di uno step, o un gesto che l'FM-1 ha letto pochi ms dopo "
             "(i tasti si leggono a ogni giro di scansione, REC e TAKE scrivono al millisecondo): con quei ms il simulatore "
             "fa la stessa cosa",
}


def confronta(path, out_md, only=None, show=False):
    data = T.load(path)
    sessions = data["sessioni"]
    if only:
        sessions = [s for s in sessions if s["nome"] == only]
    t0 = time.time()
    rows, allf = [], []
    for s in sessions:
        if "fm1" not in s:
            continue
        f, sim = compare(s)
        rows.append((s, f))
        allf += [(s, x) for x in f]
        if show and sim is not None:
            hw_p = {int(k): T.probe_dict(v) for k, v in s["fm1"]["sonde"].items()}
            sim_p = {int(k): T.probe_dict(v) for k, v in sim["sonde"].items()}
            for i, role in probe_events(s):
                if i in hw_p and i in sim_p:
                    d = pdiff(sim_p[i], hw_p[i])
                    print("%-10s %s" % (role, "uguali" if not d else "; ".join("%s FM-1 %s, simulatore %s" % (f_, b, a) for f_, a, b in d[:12])))
    errs = [x for x in allf if x[1][1] == "ERRORE"]
    seen = [x for x in allf if x[1][1] == "VISTO"]
    lines = ["# SAGGA SEQ sull'FM-1 vero: cosa ha trovato", "",
             "%s. %s: %d sessioni confrontate con il simulatore in %.0f s." % (time.strftime("%Y-%m-%d %H:%M"), os.path.basename(path),
                                                                           len(rows), time.time() - t0), ""]
    hello = data.get("fm1") or {}
    if hello:
        lines += ["FM-1: SAGGA SEQ %s, %s." % (hello.get("version", "?"), data.get("quando", "")), ""]
    lines += ["| regola | casi |", "| --- | --- |"]
    for r in REGOLE_HW:
        lines.append("| %s | %d |" % (r, sum(1 for _, x in allf if x[0] == r)))
    lines.append("")
    for r, what in REGOLE_HW.items():
        fs = [(s, x) for s, x in allf if x[0] == r]
        if not fs:
            continue
        lines += ["## %s: %d" % (r, len(fs)), "", "_%s_" % what, ""]
        for s, x in fs[:40]:
            lines.append("* **%s** (%s, %s): %s" % (s["nome"], s["situazione"], x[1], x[2]))
            lines.append("  da vicino: `python3 tests/sagga_explore.py --hw %s --sessione %s --vedi`" % (os.path.basename(path), s["nome"]))
        lines.append("")
    with open(out_md, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("sagga explore hw: %d sessioni, %d errori, %d da guardare, %d di tempo (%s)" % (len(rows), len(errs), len(allf) - len(errs) - len(seen),
                                                                                       len(seen), os.path.relpath(out_md, E.ROOT)))
    for s, x in errs[:20]:
        print("  %s | %s | %s: %s" % (x[0], s["nome"], s["situazione"], x[2][:200]))
    return 1 if errs else 0


def prova(n, length, seed, out_md, lcdcost=True):
    """steps 2 and 3 with the simulator in the FM-1's place: everything must come out equal"""
    plan = piano(n, length, seed, tablet=2)          # (0.18: two with the tablet and the grid, MIDI events)
    # (every other one with the FM-1's settings the other way: two USB ports, another profile)
    plan["sessioni"] = [run_like_fm1(s, lcdcost=lcdcost, settings=(2, k % 3) if k % 2 else None) for k, s in enumerate(plan["sessioni"])]
    plan["fm1"] = {"version": "simulatore"}
    path = os.path.join(os.path.dirname(out_md), "raccolta-prova.json")
    T.save(path, plan)
    return confronta(path, out_md)
