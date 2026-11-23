#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA HUB 0.20.3, l'esploratore del banco: il piano e il confronto (qui), il giro lo fa il Pi (tools/hub/sagga_banco.py).

1. Il piano:      python3 tests/sagga_explore.py --banco-piano FILE   (make_release lo mette nello zip del hub)
   sessioni nelle situazioni del tablet e del grid (REMOTE 13 + 14 e il grid attaccato, poi la situazione); un gesto su
   due e' una cella di una delle sei pagine SAGGA (il comando che la pagina manda, calcolato con il codice della pagina;
   ogni cella di ogni pagina almeno una volta nel giro), gli altri il pannello e il grid. Il pannello e le sonde sono
   eventi del test dell'FM-1; pagine e grid sono "reali": il Pi li fa passare dal hub e dal bridge.
2. Sul Pi:        la pagina del hub, ESPLORATORE DEL BANCO (o sudo python3 /opt/sagga/hub/sagga_banco.py)
3. Il confronto:  python3 tests/sagga_explore.py --banco raccolta-banco-<data>.json  -> build/explore/RAPPORTO-BANCO.md
   L'FM-1 (0.20.3) ascolta le sue porte durante il test e dice ogni messaggio che ha sentito, dove (il suo ms, il tick
   del clock, la porta): ogni sessione e' rifatta nel simulatore con gli eventi del test dove l'FM-1 li ha presi e quei
   messaggi dove li ha sentiti, e le due macchine devono essere uguali sonda per sonda (SIMULATORE). Poi le strade: ogni
   comando che il Pi ha mandato a una pagina, ogni messaggio del bridge, l'FM-1 lo deve aver sentito (PAGINE, GRID); le
   luci del grid sono quelle che l'FM-1 ha mandato (LUCI); i valori tornano alle pagine (VALORI); il bridge traduce ogni
   pad (PONTE); la matrice (MATRICE).

--banco-prova fa 2 e 3 con il simulatore al posto dell'FM-1 (il bridge vero, i ritardi del Pi a caso): deve dire tutto
uguale; poi con le pagine perse dal hub e con un pezzo di quello che l'FM-1 ha sentito perso per strada: deve trovarli.
"""
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sagga_explore as E        # noqa: E402
import sagga_explore_hw as H     # noqa: E402
import sagga_plugin_tests as P   # noqa: E402

S, T = E.S, H.T
sys.path.insert(0, os.path.join(E.ROOT, "tools"))
import sagga_grid_bridge as B    # noqa: E402

PAGES = ("sagga_remote", "sagga_mutes", "sagga_motori", "sagga_break", "sagga_mod", "sagga_live")
R_NAMES = {"sagga_remote": "SAGGA Remote", "sagga_mutes": "SAGGA Mutes", "sagga_motori": "SAGGA Motori",
           "sagga_break": "SAGGA Break", "sagga_mod": "SAGGA Mod", "sagga_live": "SAGGA Live"}
SNAP = 250                        # the grid's lights read after a probe (sagga_banco.SNAP_MS)
HB = 1000                         # the bridge's keep-alive (B.HEARTBEAT_S)
SKIP_CELLS = set()                # (none: the test keeps the slots and the settings shut, RELOAD and the rest are safe)


_RUNNER = []


def runner():
    """the Pi's side (tools/hub/sagga_banco.py), under a name of its own (this file has the same one)"""
    if not _RUNNER:
        import importlib.util
        spec = importlib.util.spec_from_file_location("sagga_banco_pi", os.path.join(E.ROOT, "tools", "hub", "sagga_banco.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _RUNNER.append(m)
    return _RUNNER[0]


# ----------------------------------------------------------------------------------------------------- the pages
_PAGES = {}


def pages():
    """{plugin: (class, [cells])} with the hub's stand-in (the pages' own code)"""
    if not _PAGES:
        P.stub_hub()
        for name in PAGES:
            m, cls = P.load_plugin(name)
            grid = [p for p in cls.params if p.__class__.__name__ == "LayoutGrid"][0]
            _PAGES[name] = (cls, list(grid.cells))
    return _PAGES


def page_messages(name, cell, value):
    """what the page sends when the cell takes value (the page's on_param_change, the hub's binding) -> [(st, d1, d2)]"""
    cls, _ = pages()[name]
    p = cls()
    p.ccs = []
    p.on_param_change(cell, value)
    out = []
    for x in p.ccs:
        if x[0] == "on":
            out.append((0x90 | x[1], x[2], x[3]))
        elif x[0] == "off":
            out.append((0x80 | x[1], x[2], 0))
        else:
            out.append((0xB0 | x[0], x[1], x[2]))
    return out


def _val(v):
    return "True" if v is True else ("False" if v is False else str(int(v)))


def g_page(name, cell, values, label):
    def do(s, t):
        for v in values:
            s.raw(t, "page %s %s %s" % (name, cell, _val(v)))
            t += 60
        return t + 20
    return E.Gesto("pagina %s %s" % (name[6:], label), "tablet", do, tags={"tablet"})


def page_gestures(rnd=None):
    """every cell of every page: a tap presses (the page lets go by itself), a switch on and (another gesture) off, a
    knob one of three values (at random with rnd, else each)"""
    out = []
    for name, (cls, cells) in pages().items():
        for c in cells:
            p, nm = c.param, c.param.name
            if (name, nm) in SKIP_CELLS:
                continue
            kind = p.__class__.__name__
            if kind == "Button":
                if getattr(p, "trigger", False):
                    out.append(g_page(name, nm, (True,), nm))
                else:
                    out.append(g_page(name, nm, (True,), "%s ON" % nm))
                    out.append(g_page(name, nm, (False,), "%s OFF" % nm))
            elif kind in ("Knob", "Fader"):
                lo, hi = int(getattr(p, "min", 0)), int(getattr(p, "max", 127))
                vals = sorted({lo + (hi - lo) // 3, lo + 2 * (hi - lo) // 3, hi})
                for v in ([rnd.choice(vals)] if rnd else vals):
                    out.append(g_page(name, nm, (v,), "%s %d" % (nm, v)))
    return out


# -------------------------------------------------------------------------------------------------------- the plan
def _shifted(src, dst, off):
    """the lines of a Script moved later by off ms (a situation's set-up after the banco's own)"""
    for t, _, line in sorted(src.lines):
        p = line.split(" ", 1)
        dst.lines.append((t + off, len(dst.lines), "%d %s" % (t + off, p[1] if len(p) > 1 else "")))
    dst.pages.update(src.pages)


def banco_situazioni():
    """the tablet's situation, and every other one the FM-1 can do with the tablet and the grid in front: REMOTE 13 +
    14 (SAVE + K2) and the bridge attached first, then the situation's own set-up"""
    out = [x for x in E.SITUAZIONI if x.hw and x.tablet]
    for x in E.SITUAZIONI:
        if not x.hw or x.grid or x.tablet:
            continue

        def setup(s, x=x):
            s.press(150, S.SAVE); s.enc(180, S.K2, 1); s.release(250, S.SAVE)
            s.raw(300, "attach")
            own = S.Script()
            t = int(x.setup(own))
            _shifted(own, s, 300)
            return t + 300
        out.append(E.Situazione(x.name + ", con tablet e grid", setup, grid=True, tablet=True))
    return [x for x in out if H.situation_ok(x)]


def session_plan(sit, gs, name):
    """a session as the Pi plays it: test events (the panel, the probes) and the real ones (pages, grid)"""
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
    test, real = [], []
    for line in lines:
        p = line.split()
        tt, verb, a = int(p[0]) + H.OFF, p[1], p[2:]
        if verb == "pad":
            real.append(["grid", tt, [0x9F, int(a[1]) * 16 + int(a[0]), int(a[2]) if len(a) > 2 else 100]])
        elif verb == "ctl":
            real.append(["grid", tt, [0xBE, int(a[0]), int(a[1]) if len(a) > 1 else 127]])
        elif verb == "attach":
            real.append(["grid_start", tt])
        elif verb in ("hb", "detach"):
            continue                                   # (the bridge keeps the link by itself)
        elif verb == "page":
            v = a[2]
            val = True if v == "True" else (False if v == "False" else int(v))
            real.append(["pagina", tt, a[0], a[1], val, [list(m) for m in page_messages(a[0], a[1], val)]])
        elif verb == "midi":
            real.append(["diretto", tt, [int(a[0], 0), int(a[1]), int(a[2])]])
        else:
            test.append(line)
    ev = H.to_events([x for x in test])
    if ev is None:
        return None
    ev = [(e[0] + H.OFF,) + tuple(e[1:]) for e in ev] + [(tend + 700 + H.OFF, T.END, 0, 0)]
    real.sort(key=lambda r: r[1])
    return {"nome": name, "situazione": sit.name, "gesti": [g.name for g in gs], "eventi": [list(e) for e in ev],
            "sonde": roles, "reali": real}


def piano(n=None, length=40, seed=11):
    """n sessions (None: one for every situation) in the banco's situations (in turn); every other gesture a page, the rest the panel and the grid in
    turn; the pages' gestures in turn over the whole run (with n * length / 2 at least their number: every cell of
    every page at least once), the rest at random"""
    sits = banco_situazioni()
    if n is None:
        n = len(sits)
    every = E.catalogo(grid=True, tablet=False)
    panel = [g for g in every if g.name != "niente" and "andata" not in g.tags and "grid" not in g.tags and not E.fondo(g) and H.gesture_ok(g)]
    grid = [g for g in every if "grid" in g.tags and H.gesture_ok(g)]
    rnd = random.Random(seed)
    pg = page_gestures(rnd)
    rnd.shuffle(pg)
    out, k_pg = [], 0
    for k in range(n):
        sit = sits[k % len(sits)]
        gs = []
        for j in range(length):
            if j % 2 == 1:
                gs.append(pg[k_pg % len(pg)])
                k_pg += 1
            else:
                cand = [g for g in (panel if j % 4 == 0 else grid) if E.fits(g, sit)]
                gs.append(rnd.choice(cand))
        sp = session_plan(sit, gs, "b%03d" % (k + 1))
        while sp and len(sp["eventi"]) > 1000 and len(gs) > 1:   # (the FM-1 keeps the places of 1024 events a session)
            gs = gs[:-1]
            sp = session_plan(sit, gs, "b%03d" % (k + 1))
        if sp:
            out.append(sp)
    return {"versione": 1, "firmware": "0.20.3", "seme": seed, "banco": True, "sessioni": out}


# ------------------------------------------------------------------------------------------------ the comparison
GRID_ST = (0x9F, 0x8F, 0xBE)


def roles_of(midi):
    """the grid's lights (roles) the bridge shows after these messages of the FM-1: [[Launchpad, led, role]]"""
    b = B.Bridge(lambda i, m: None, lambda m: None, model="mk3")
    for m in midi:
        if m[1] in GRID_ST:
            b.fm1_in(m[1:4])
    return sorted([idx, led, r] for (idx, led), r in b.role.items() if r)


def light_changes(midi):
    """{(Launchpad, led): [(ms, role)]}: every change of the grid's lights the bridge would make, fed the FM-1's MIDI"""
    b = B.Bridge(lambda i, m: None, lambda m: None, model="mk3")
    out = {}
    for m in midi:
        if m[1] not in GRID_ST:
            continue
        b.dirty.clear()
        b.fm1_in(m[1:4])
        for k in b.dirty:
            out.setdefault(k, []).append((m[0], b.role.get(k, 0)))
    return out


def role_at(ch, t):
    r = 0
    for ms, role in ch:
        if ms > t:
            break
        r = role
    return r


WIN = 600                         # the lights compared with the simulator: those that stay the same this long before
                                  # and after the snapshot on both machines (the playing step, the chasers, a SHIFT
                                  # held for a moment move on their own, and the two send the grid's changes a few ms apart)


def lights(session, sim):
    """the grid's lights at each snapshot (250 ms after a probe) -> ([(probe, what)] the Pi's bridge did not draw
    what the FM-1 had sent it, [(probe, what)] the FM-1's lights are not the simulator's where both stand still)"""
    hw = session["fm1"]
    go = hw["go_ms"]
    two = (hw.get("hello_prima") or {}).get("usb_ports", 1) >= 2
    remote = lambda m: len(m) < 5 or not two or m[4] == 2       # (0.20.4: the lights come on port 2; old raccolte: all)
    fm = [[go + m[0]] + list(m[1:4]) for m in hw.get("midi") or [] if m[1] in GRID_ST and remote(m)]
    ch_hw = light_changes(fm)
    ch_sim = light_changes(sorted((m for m in sim.get("midi") or [] if remote(m)), key=lambda m: m[0])) if sim is not None else None
    end = fm[-1][0] if fm else go
    bridge, versus = [], []
    for k, snap in sorted((hw.get("luci") or {}).items(), key=lambda kv: int(kv[0])):
        got = [list(x) for x in snap["ruoli"]]
        if "n" in snap:
            want = roles_of(fm[:snap["n"]])
            if want != got:
                d = sorted(set(map(tuple, want)) ^ set(map(tuple, got)))
                bridge.append((int(k), "%d luci diverse da quelle che l'FM-1 aveva mandato (Launchpad, led, ruolo: %s)" % (len(d), d[:3])))
        t = go + snap["t"]
        if ch_sim is None or t + WIN > end:
            continue
        bad = []
        for key in sorted(set(ch_hw) | set(ch_sim)):
            a, b = ch_hw.get(key, []), ch_sim.get(key, [])
            if any(t - WIN < ms <= t + WIN for ms, _ in a + b):
                continue
            if role_at(a, t) != role_at(b, t):
                bad.append((key[0], key[1], role_at(a, t), role_at(b, t)))
        if bad:
            versus.append((int(k), "%d luci diverse (Launchpad, led, FM-1, simulatore: %s)" % (len(bad), bad[:3])))
    return bridge, versus


def roads(session):
    """the roads, message by message: each one the Pi sent (reali_fatti: a page through the hub, the bridge, straight
    to the FM-1) found in what the FM-1 heard (sentiti), within its time; -> (lost [(via, t, msg, what)], heard by
    nobody's road [heard rows])"""
    hw = session["fm1"]
    go = hw["go_ms"]
    heard = [list(h) for h in hw.get("sentiti") or []]
    used = [False] * len(heard)
    lost = []
    # 0.23.1: the FM-1 says what it heard up to its last event (the END): what the Pi sent after it - the bridge's
    # keep-alive, a second later - it never says, and that is no message lost (the 0.23 banco's b001)
    taken = [v[0] for v in (hw.get("presi") or {}).values()]
    end = (max(taken) - go) if taken else None
    for r in sorted(hw.get("reali_fatti") or [], key=lambda r: r[0]):
        t, via, m = r[0], r[1], list(r[2])
        call = r[6] if len(r) > 6 and r[6] else 0
        lo, hi = go + t - 15 - call / 2.0, go + t + 120 + call / 2.0
        k = next((k for k, h in enumerate(heard) if not used[k] and lo <= h[0] <= hi and h[2:5] == m), None)
        if k is None:
            if end is not None and t > end - 20:
                continue                               # (sent after the FM-1's last event: it could not say it)
            what = "%s %s=%s" % (r[3], r[4], r[5]) if via == "pagina" and len(r) > 5 else ""
            lost.append((via, t, m, what))
        else:
            used[k] = True
    return lost, [h for k, h in enumerate(heard) if not used[k]]


def msg_txt(m):
    return "%02X %d %d" % tuple(m[:3])


def said_last(session, w):
    """0.32.1: a cell of VALORI [page, cell, the FM-1's value, the page's] -> (the ms the Pi pressed it last, the ms the
    FM-1 said its value last or None, the ms the FM-1 said any value to the pages last or None), from what the raccolta
    keeps (the Pi's presses, the FM-1's messages on the remote's port); None: the Pi never pressed it"""
    hw = session["fm1"]
    typ = next((t for t, n in R_NAMES.items() if n == w[0]), None)
    press = runner().pressed_last(hw.get("reali_fatti")).get((typ, w[1]))
    if typ is None or press is None:
        return None
    if typ == "sagga_mod" and w[1].startswith("lfo_sw"):
        is_it = lambda m: (m[1] & 0xF0) in (0x80, 0x90) and (m[1] & 15) == 12 and m[2] == 100 + int(w[1][6:])
    else:
        cell = [c for c in pages()[typ][1] if c.param.name == w[1]]
        if not cell:
            return None
        ch, cc = runner().ECHO_BACK.get((typ, w[1]), (cell[0].channel, cell[0].cc))
        is_it = lambda m: m[1] == (0xB0 | ch) and m[2] == cc
    port2 = [m for m in hw.get("midi") or [] if len(m) < 5 or m[4] == 2]
    mine = [m[0] for m in port2 if is_it(m)]
    anyv = [m[0] for m in port2 if (m[1] & 0xF0) == 0xB0 and (m[1] & 15) in (11, 12, 13)]
    return press, (mine[-1] if mine else None), (anyv[-1] if anyv else None)


REGOLE = dict(H.REGOLE_HW)
REGOLE.update({
    "MATRICE": "le celle che servono ci sono, quelle che non devono esserci no",
    "PAGINE": "ogni pagina SAGGA risponde all'API del hub e il suo comando arriva all'FM-1 (l'FM-1 dice di averlo sentito)",
    "GRID": "ogni messaggio del bridge arriva all'FM-1",
    "SENTITI": "l'FM-1 dice tutto quello che ha sentito (senza, il simulatore non rifa' la sessione intera); quello che "
               "non viene dalle pagine ne' dal bridge e' di un altro dispositivo collegato all'FM-1",
    "VALORI": "i valori che l'FM-1 rimanda arrivano alle celle delle pagine",
    "CELLE": "dopo ogni riavvio dell'FM-1 le sue celle sono di nuovo nella matrice (0.20.9: quelle che RaspiMIDIHub perde, il "
             "suo salvataggio automatico mentre l'FM-1 non c'e', le rimette il Pi)",
    "PONTE": "il bridge traduce ogni pad e ogni bottone nel messaggio giusto per l'FM-1",
    "LUCI": "le luci che il bridge accende sono quelle che l'FM-1 chiede",
})


def compare(session):
    hw = session["fm1"]
    found, sim = H.compare(session, heard=hw.get("sentiti"))
    for w in hw.get("errori_pagine") or []:
        found.append(("PAGINE", "ERRORE", w))
    done = hw.get("done") or {}
    if hw.get("go_ms") is not None and done and "reali" in session:      # (the banco's: the whole FM-1's has no roads)
        got = len(hw.get("sentiti") or [])
        partial = "heard" in done and (bool(done.get("heard_lost")) or got < done["heard"])
        lv = "DA GUARDARE" if partial else "ERRORE"          # (a message missing may be one the FM-1 did not say)
        why = " (l'FM-1 non ha detto tutto quello che ha sentito: forse erano li')" if partial else ""
        if "heard" not in done:
            found.append(("SENTITI", "ERRORE", "l'FM-1 non ha ascoltato le porte (SAGGA SEQ prima della 0.20.3?): le pagine e "
                                               "il grid non hanno fatto niente"))
        elif done.get("heard_lost") or got < done["heard"]:
            found.append(("SENTITI", "DA GUARDARE", "l'FM-1 ha sentito %d messaggi, ne ha detti %d%s: il simulatore rifa' la "
                          "sessione senza gli altri" % (done["heard"], got, " (%d non entrati nella sua coda)" % done["heard_lost"]
                                                         if done.get("heard_lost") else "")))
        lost, other = roads(session)
        pg = [x for x in lost if x[0] in ("pagina", "diretto")]
        gr = [x for x in lost if x[0] == "grid"]
        # 0.27's banco: a tap's release lost on the road, its press heard: the FM-1 acts on the press (the pages' taps send 127,
        # then 0 at the same ms) - the road lost a message, the FM-1 did nothing less (the banco's b022: PROPOSAL's 0)
        sent = hw.get("reali_fatti") or []
        rel = [x for x in pg if x[0] == "pagina" and (x[2][0] & 0xF0) == 0xB0 and x[2][2] == 0 and
               any(r[0] == x[1] and list(r[2]) == [x[2][0], x[2][1], 127] for r in sent) and
               not any(y[1] == x[1] and list(y[2]) == [x[2][0], x[2][1], 127] for y in lost)]
        pg = [x for x in pg if x not in rel]
        if rel:
            found.append(("PAGINE", "DA GUARDARE", "%d rilasci di un tasto delle pagine persi per strada, la pressione arrivata "
                          "(l'FM-1 agisce alla pressione): %s" % (len(rel), "; ".join("%s %s a %d ms" % (x[3] or x[0], msg_txt(x[2]), x[1])
                                                                                       for x in rel[:4]))))
        if pg:
            found.append(("PAGINE", lv, "%d comandi delle pagine mai arrivati all'FM-1: %s (la cella pagina -> FM-1 "
                          "nella matrice?)%s" % (len(pg), "; ".join("%s %s a %d ms" % (x[3] or x[0], msg_txt(x[2]), x[1]) for x in pg[:4]), why)))
        if gr:
            found.append(("GRID", lv, "%d messaggi del bridge mai arrivati all'FM-1: %s%s" % (
                len(gr), "; ".join("%s a %d ms" % (msg_txt(x[2]), x[1]) for x in gr[:4]), why)))
        if other:
            found.append(("SENTITI", "VISTO", "%d messaggi da un altro dispositivo (rifatti anche nel simulatore): %s" % (
                len(other), "; ".join("%s porta %d" % (msg_txt(h[2:5]), h[5] + 1) for h in other[:4]))))
    v = hw.get("valori") or {}
    if v.get("sbagliati") and hw.get("midi") and len(hw["midi"][0]) < 5:
        # a raccolta of 0.20.3: the Pi took the values from both ports; on port 1 the STOP sends CC 64 = 0 (sustain off)
        # with CC 123 at the same ms on every channel - not a value for a page (SAGGA Motori l15, SAGGA Mutes k0)
        panic = {(m[1] & 15, m[0]) for m in hw["midi"] if (m[1] & 0xF0) == 0xB0 and m[2] == 123}
        keep = []
        for w in v["sbagliati"]:
            cell = [c for c in pages().get(next((p for p, n in R_NAMES.items() if n == w[0]), ""), (None, []))[1] if c.param.name == w[1]]
            if cell and cell[0].cc == 64:
                last = [m for m in hw["midi"] if m[1] == 0xB0 | cell[0].channel and m[2] == 64]
                if last and (cell[0].channel, last[-1][0]) in panic:
                    continue
            keep.append(w)
        v = dict(v, sbagliati=keep)
    # 0.32.1: a cell the Pi pressed AFTER the FM-1's last word on it is not one that "does not follow" - whether the FM-1
    # took the press, a value from before cannot say (the Pi's side of 0.32.1 leaves them out itself: "dopo"; an older
    # raccolta: from the times it keeps). The banco of 0.32: a grid pad had switched the REMOTE off (b030), a SEED on a
    # pattern that has none (b032)
    later = [(w, None) for w in v.get("dopo") or []]
    if v.get("sbagliati") and "dopo" not in v:
        keep = []
        for w in v["sbagliati"]:
            sl = said_last(session, w)
            if sl and sl[1] is not None and sl[0] > sl[1]:
                later.append((w, sl))
            else:
                keep.append(w)
        v = dict(v, sbagliati=keep)
    if later:
        def why(w, sl):
            sl = sl or said_last(session, w)
            if not sl or sl[2] is None:
                return ""
            return (" (l'FM-1 parla ancora alle pagine, ma non di questa cella: li' non ha un valore da mostrare)" if sl[2] > sl[0] + 1000
                    else " (da li' l'FM-1 non rimanda piu' niente alle pagine: REMOTE spento da un gesto, o la fine della sessione)")
        found.append(("VALORI", "VISTO", "%d celle premute dal Pi dopo l'ultima parola dell'FM-1 su di loro (non si confrontano): %s" % (
            len(later), "; ".join("%s %s%s" % (w[0], w[1], why(w, sl)) for w, sl in later[:5]))))
    kc = hw.get("celle_fm1") or {}                     # 0.20.9: the FM-1's cells after its reboot
    if kc.get("rimesse"):
        found.append(("CELLE", "VISTO", "RaspiMIDIHub aveva perso %d celle dell'FM-1 nel riavvio: il Pi le ha rimesse" % kc["rimesse"]))
    if kc.get("non_tornano"):
        found.append(("CELLE", "ERRORE", "%d celle dell'FM-1 non tornate dopo il riavvio: %s" % (len(kc["non_tornano"]), "; ".join(kc["non_tornano"][:3]))))
    if v.get("sbagliati"):
        found.append(("VALORI", "DA GUARDARE" if kc.get("non_tornano") else "ERRORE", "%d celle su %d non seguono l'FM-1: %s%s" % (
            len(v["sbagliati"]), v.get("controllati", 0), "; ".join("%s %s FM-1 %s, pagina %s" % tuple(x) for x in v["sbagliati"][:5]),
            " (le celle dell'FM-1 non erano tornate)" if kc.get("non_tornano") else "")))
    for w in (hw.get("ponte") or [])[:5]:
        found.append(("PONTE", "ERRORE", "pad %s -> Launchpad %s -> il bridge ha mandato %s" % (w["piano"], w["launchpad"], w["bridge"])))
    for w in (hw.get("proprie") or [])[:5]:
        found.append(("PAGINE", "VISTO", w))
    if hw.get("go_ms") is not None:
        roles = dict(H.probe_events(session))
        bridge, versus = lights(session, sim)
        for i, what in bridge[:3]:
            found.append(("LUCI", "ERRORE", "il bridge, dopo la sonda '%s': %s" % (roles.get(i, i), what)))
        for i, what in versus[:3]:
            found.append(("LUCI", "DA GUARDARE", "dopo la sonda '%s': %s" % (roles.get(i, i), what)))
    return found, sim


def confronta(path, out_md):
    import time
    data = T.load(path)
    t0 = time.time()
    rows, allf = [], []
    for lv, txt in data.get("audit") or []:
        allf.append(({"nome": "-", "situazione": "la matrice"}, ("MATRICE", lv, txt)))
    for s in data["sessioni"]:
        if "fm1" not in s:
            continue
        f, _ = compare(s)
        rows.append((s, f))
        allf += [(s, x) for x in f]
    errs = [x for x in allf if x[1][1] == "ERRORE"]
    seen = [x for x in allf if x[1][1] == "VISTO"]
    facts = data.get("fatti") or {}
    lines = ["# Il banco (FM-1, Pi, grid): cosa ha trovato", "",
             "%s: %d sessioni confrontate con il simulatore in %.0f s. FM-1 %s, hub %s, RaspiMIDIHub %s." % (
                 os.path.basename(path), len(rows), time.time() - t0, facts.get("fm1_version", "?"), facts.get("hub", "?"),
                 facts.get("raspimidihub", "?")), ""]
    if H.versions(facts.get("fm1_version")):           # (0.23.1)
        lines += [H.versions(facts.get("fm1_version")), ""]
        print(H.versions(facts.get("fm1_version")).replace("**", ""))
    lines += ["| regola | casi |", "| --- | --- |"]
    for r in REGOLE:
        lines.append("| %s | %d |" % (r, sum(1 for _, x in allf if x[0] == r)))
    lines.append("")
    for r, what in REGOLE.items():
        fs = [(s, x) for s, x in allf if x[0] == r]
        if not fs:
            continue
        lines += ["## %s: %d" % (r, len(fs)), "", "_%s_" % what, ""]
        for s, x in fs[:40]:
            lines.append("* **%s** (%s, %s): %s" % (s["nome"], s["situazione"], x[1], x[2]))
        lines.append("")
    with open(out_md, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("sagga banco: %d sessioni, %d errori, %d da guardare, %d di tempo (%s)" % (
        len(rows), len(errs), len(allf) - len(errs) - len(seen), len(seen), os.path.relpath(out_md, E.ROOT)))
    for s, x in errs[:20]:
        print("  %s | %s | %s: %s" % (x[0], s["nome"], s["situazione"], x[2][:200]))
    return 1 if errs else 0


# --------------------------------------------------------------------------------------- the simulator as the banco
def run_like_banco(sess, rnd, settings=(2, 0), drop_pages=False, lose_heard=False):
    """the session as the Pi plays it, with the simulator as the FM-1 (listening to its ports, as GO asks): the bridge
    (the real code) and the pages' messages at the plan's times plus the Pi's delays (a page: 5-40 ms, the call to the
    hub, noted at its middle; the grid: 1-3 ms), the keep-alive every second, the grid's lights read 250 ms after each
    probe. drop_pages: the hub loses every page message (the FM-1 never gets them, the runner notes them all the same);
    lose_heard: a frame of what the FM-1 heard lost on the way (both must be found)"""
    port = 2 if settings[0] == 2 else 1
    truth, noted = [], []                     # (t_rel, msg) the FM-1 gets / [t, via, msg, ...] the runner notes
    br_out = []
    bridge = B.Bridge(lambda i, m: None, lambda m: br_out.append(list(m)), model="mk3")
    started, next_hb = False, None

    def beats(upto):
        nonlocal next_hb
        while started and next_hb <= upto:
            truth.append((next_hb + 1, [0xBF, 118, 64]))
            noted.append([round(next_hb, 1), "grid", [0xBF, 118, 64]])
            next_hb += HB
    for r in sorted(sess.get("reali") or [], key=lambda r: r[1]):
        t = r[1]
        beats(t)
        if r[0] == "pagina":
            call = rnd.uniform(10, 60)
            sent = t + rnd.uniform(0.3, 0.9) * call
            for m in r[5]:
                if not drop_pages:
                    truth.append((sent + 1, list(m)))
                noted.append([round(t + call / 2, 1), "pagina", list(m), r[2], r[3], r[4], round(call, 1)])
        elif r[0] == "grid_start":
            started, next_hb = True, t + HB
            truth.append((t + 1, [0xBF, 118, 127]))
            noted.append([t, "grid", [0xBF, 118, 127]])
        elif r[0] == "grid":
            side, lp = runner().lp_message(tuple(r[2]))
            br_out.clear()
            bridge.lp_in(side, lp)
            for m in br_out:
                truth.append((t + rnd.uniform(1, 3), m))
                noted.append([t, "grid", m])
        elif r[0] == "diretto":
            truth.append((t + 1, list(r[2])))
            noted.append([t, "diretto", list(r[2]), "", "", 0, 0])
    beats(sess["eventi"][-1][0])
    text, _ = H.sim_script(sess["eventi"], H.GO_SIM, lcdcost=True, listen=True,
                           extra=[(H.GO_SIM + t, "midi 0x%02X %d %d %d" % (m[0], m[1], m[2], port)) for t, m in truth])
    rec = H.collect(H.run_sim(text, settings=settings))
    rec["reali_fatti"] = sorted(noted, key=lambda x: x[0])
    if lose_heard and len(rec.get("sentiti") or []) > 20:
        del rec["sentiti"][8:20]                  # (a frame of twelve)
    go = rec["go_ms"]
    rec["midi"] = [[m[0] - go] + list(m[1:]) for m in sorted(rec["midi"], key=lambda m: m[0])]   # (the Pi's: ms after GO)
    grid = [m for m in rec["midi"] if m[1] in GRID_ST and (port == 1 or m[4] == 2)]   # (the bridge hears port 2)
    rec["luci"] = {}
    for i, e in enumerate(sess["eventi"]):
        if e[1] == T.PROBE:
            ts = e[0] + SNAP
            n = sum(1 for m in grid if m[0] <= ts)
            rec["luci"][str(i)] = {"t": ts, "n": n, "ruoli": roles_of(grid[:n])}
    rec["hello_prima"] = {"usb_ports": settings[0], "profile": settings[1]}
    rec["valori"] = {"sbagliati": [], "controllati": 0}
    out = dict(sess)
    out["fm1"] = rec
    return out


def prova_tempo(seed):
    """0.23.1, with the simulator as the FM-1 - what the comparison learnt from the 0.23 banco of the real one:
    (1) a dice thrown from the grid that the FM-1 says it heard a ms off (the dice takes its seed from the ms: another
    dice) is TEMPO, found by moving what was heard from the ports; (2) two clock ticks and a note-off taken out of what
    the Pi heard are PERSI, each with its place, and a tick that came 30 ms late is nothing; (3) the bridge's keep-alive
    sent after the FM-1's last event is not a message lost, one sent before it and never heard is. -> [(what, ok)]"""
    import copy
    sit = next(x for x in banco_situazioni() if x.name == "TECHNO band in play, con tablet e grid")
    by = {g.name: g for g in E.catalogo(grid=True, tablet=False)}
    # (each of these presses the view's button first: BEAT, EUCLID, BEAT ... - the third is on the BEAT view, where
    #  pad 5 of row 4 throws all the dice)
    gs = [by[n] for n in ("grid BEAT pad 1,2", "grid BEAT pad 2,2", "grid BEAT pad 5,4", "grid BEAT pad 3,2", "grid BEAT pad 4,2")]
    rec = run_like_banco(session_plan(sit, gs, "t001"), random.Random(seed))
    errs = lambda f: [x for x in f if x[1] == "ERRORE"]
    out = []
    f0, _ = compare(rec)
    out.append(("the session as it is: no error, nothing lost", not errs(f0) and not [x for x in f0 if x[0] in ("PERSI", "GRID")]))
    # (1) the dice's pad, heard a ms later than the FM-1 really took it
    hw = rec["fm1"]
    probes = dict((r, i) for i, r in H.probe_events(rec))
    t1, t2 = hw["presi"][str(probes["gesto 2"])][0], hw["presi"][str(probes["gesto 3"])][0]
    r1 = copy.deepcopy(rec)
    mine = [h for h in r1["fm1"]["sentiti"] if t1 < h[0] <= t2 and h[2] == 0x9F]
    for h in mine:
        h[0] += 1
    f1, _ = compare(r1)
    out.append(("a dice from the grid heard a ms off (%d messages): TEMPO, by what was heard from the ports" % len(mine),
                bool(mine) and not errs(f1) and any(x[0] == "TEMPO" and "i messaggi sentiti dalle porte" in x[2] for x in f1)))
    # (1b) 0.27's banco: ... said 5 ms before the FM-1 really worked it (its pass of the loop: the 0.27 banco's b027, a dice of
    #      the engines' page)
    r1b = copy.deepcopy(rec)
    mine = [h for h in r1b["fm1"]["sentiti"] if t1 < h[0] <= t2 and h[2] == 0x9F]
    for h in mine:
        h[0] -= 5
    f1b, _ = compare(r1b)
    out.append(("0.27's banco: the same dice said 5 ms early (%d messages): TEMPO, by what was heard from the ports" % len(mine),
                bool(mine) and not errs(f1b) and any(x[0] == "TEMPO" and "i messaggi sentiti dalle porte" in x[2] for x in f1b)))
    # (2) two ticks and a note-off never heard; a tick 30 ms late
    r2 = copy.deepcopy(rec)
    midi = r2["fm1"]["midi"]
    mid = midi[len(midi) // 3][0]
    ticks = [k for k, m in enumerate(midi) if m[1] == 0xF8 and m[0] > mid]
    offs = [k for k, m in enumerate(midi) if m[0] > mid and ((m[1] & 0xF0) == 0x80 or ((m[1] & 0xF0) == 0x90 and not m[3])) and (m[1] & 15) < 14]
    gone = sorted([ticks[10], ticks[40]] + offs[2:3], reverse=True)
    want = sorted(int(midi[k][0]) for k in gone if midi[k][1] == 0xF8)
    for k in gone:
        del midi[k]
    f2, _ = compare(r2)
    lost = [x[2] for x in f2 if x[0] == "PERSI"]
    said = [int(v) for v in re.findall(r"\d+", lost[0].split("tick di clock")[1].split(")")[0])] if lost and "tick di clock" in lost[0] else []
    out.append(("two clock ticks%s taken out of what the Pi heard: PERSI, each where it was (%s)" % (" and a note-off" if offs[2:3] else "", lost[:1]),
                len(lost) == 1 and "2 tick di clock" in lost[0] and len(said) == 2 and all(abs(a - b) <= 25 for a, b in zip(said, want))
                and (not offs[2:3] or "1 note-off canale" in lost[0])))
    r3 = copy.deepcopy(rec)
    midi = r3["fm1"]["midi"]
    k = [k for k, m in enumerate(midi) if m[1] == 0xF8 and m[0] > mid][10]
    midi[k][0] += 30
    midi.sort(key=lambda m: m[0])
    f3, _ = compare(r3)
    out.append(("a tick that came 30 ms late: nothing lost", not [x for x in f3 if x[0] in ("PERSI", "CLOCK")]))
    # (3) the bridge's messages around the end
    r4 = copy.deepcopy(rec)
    end = max(v[0] for v in r4["fm1"]["presi"].values()) - r4["fm1"]["go_ms"]
    r4["fm1"]["reali_fatti"].append([end + 138, "grid", [0xBF, 118, 64]])
    f4, _ = compare(r4)
    r5 = copy.deepcopy(rec)
    r5["fm1"]["reali_fatti"].append([end - 900, "grid", [0x9F, 0x11, 100]])
    f5, _ = compare(r5)
    out.append(("the keep-alive after the FM-1's last event: not lost; a pad sent before it and never heard: GRID",
                not [x for x in f4 if x[0] == "GRID"] and len([x for x in f5 if x[0] == "GRID"]) == 1))
    # (4) 0.27's banco: a page's tap (127, then 0 at the same ms): its release lost on the road is to look at, the FM-1 acts on
    #     the press (the 0.27 banco's b022, PROPOSAL); the press lost is an error
    pg = {g.name: g for g in page_gestures()}
    gs = [by["grid BEAT pad 1,2"], pg["pagina live proposal"], by["grid BEAT pad 2,2"]]
    rp = run_like_banco(session_plan(sit, gs, "t002"), random.Random(seed))
    fp, _ = compare(rp)
    taps = [r for r in rp["fm1"].get("reali_fatti") or [] if r[1] == "pagina" and (r[2][0] & 0xF0) == 0xB0]
    press = [r for r in taps if r[2][2] == 127]
    rel = [r for r in taps if r[2][2] == 0 and any(q[0] == r[0] and q[2][:2] == r[2][:2] for q in press)]

    def without(rec_, m):                              # (lost on the road: the FM-1 never heard it, and says one less)
        r_ = copy.deepcopy(rec_)
        hd = r_["fm1"]["sentiti"]
        k = next((k for k, h in enumerate(hd) if h[2:5] == list(m)), None)
        if k is not None:
            del hd[k]
            r_["fm1"]["done"]["heard"] -= 1
        return r_, k is not None
    r6, ok6 = without(rp, rel[0][2]) if rel else (rp, False)
    f6, _ = compare(r6)
    r7, ok7 = without(rp, press[0][2]) if press else (rp, False)
    f7, _ = compare(r7)
    out.append(("0.27's banco: PROPOSAL's release lost on the road: PAGINE to look at, not an error; its press lost: an error",
                not errs(fp) and ok6 and ok7 and not errs(f6) and any(x[0] == "PAGINE" and x[1] == "DA GUARDARE" for x in f6) and
                any(x[0] == "PAGINE" and x[1] == "ERRORE" for x in f7)))
    # (5) 0.32.1, the banco of 0.32 on the real FM-1: a note only the moved replay plays is not lost; a probe read a tick
    #     apart, with the steps alone, makes the one before it timing; a cell the Pi pressed after the FM-1's last word
    both, ghost = H.lost_in_both([("note canale 2 nota 39", 1, [23600]), ("tick di clock", 2, [100, 900])], [("tick di clock", 1, [900])], [])
    b2, g2 = H.lost_in_both([("note canale 2 nota 39", 1, [23600])], [], [])
    b3, g3 = H.lost_in_both([("tick di clock", 1, [100])], [("tick di clock", 1, [100])], [("note canale 2 nota 39", 1, [5])])
    out.append(("0.32.1: lost is what BOTH replays send - a note of the moved replay alone is its own (%s %s | %s %s | %s %s)" % (both, ghost, b2, g2, b3, g3),
                both == [("tick di clock", 1, [100, 900])] and ghost == 2 and b2 == [] and g2 == 1 and b3 == [] and g3 == 1))
    st = [("T1.step", "8", "9"), ("T3.step", "15", "14")]
    out.append(("0.32.1: a probe read a tick apart with the steps alone (or a step's edge) is timing's; with a mute in it, or on the same tick, it is not",
                H.tick_apart_edge(2041, 2040, st) and H.tick_apart_edge(2040, 2041, st + [("T2.pat", "1", "0")])
                and not H.tick_apart_edge(2041, 2040, st + [("G.mute", "0000", "0FFD")]) and not H.tick_apart_edge(2040, 2040, st)
                and not H.tick_apart_edge(2042, 2040, st) and not H.tick_apart_edge(None, 2040, st)))
    gs = [by["grid BEAT pad 1,2"], pg["pagina mod rate 12"], by["grid BEAT pad 2,2"], by["grid BEAT pad 3,2"]]
    rv = run_like_banco(session_plan(sit, gs, "t003"), random.Random(seed))
    press = runner().pressed_last(rv["fm1"]["reali_fatti"]).get(("sagga_mod", "rate"))
    mine = lambda m: len(m) > 4 and m[4] == 2 and m[1] == 0xBC and m[2] == 94
    rv["fm1"]["midi"] = [m for m in rv["fm1"]["midi"] if not (mine(m) and press is not None and m[0] > press)]   # (as with the REMOTE off)
    said = [m for m in rv["fm1"]["midi"] if mine(m)]
    row = ["SAGGA Mod", "rate", 6, 12]
    rv["fm1"]["valori"] = {"sbagliati": [list(row)], "controllati": 9}
    fv1, _ = compare(rv)                                # (the FM-1 said RATE before the press and nothing since: seen)
    rv2 = copy.deepcopy(rv)
    rv2["fm1"]["midi"].append([press + 900.0, 0xBC, 94, 6, 2])   # (... and again after it: its word is the last - an error)
    rv2["fm1"]["midi"].sort(key=lambda m: m[0])
    fv2, _ = compare(rv2)
    rv3 = copy.deepcopy(rv)                             # (the Pi's side of 0.32.1 says it itself: "dopo")
    rv3["fm1"]["valori"] = {"sbagliati": [], "controllati": 8, "dopo": [list(row)]}
    fv3, _ = compare(rv3)
    val = lambda f: [(x[1], x[2][:60]) for x in f if x[0] == "VALORI"]
    out.append(("0.32.1: a cell the Pi pressed after the FM-1's last word on it is seen, not an error; the FM-1 speaking after the press: an error (%s | %s | %s; press %s, said %s)"
                % (val(fv1), val(fv2), val(fv3), press, [m[0] for m in said][-2:]),
                press is not None and bool(said) and said[-1][0] < press
                and [x[1] for x in fv1 if x[0] == "VALORI"] == ["VISTO"] and [x[1] for x in fv2 if x[0] == "VALORI"] == ["ERRORE"]
                and [x[1] for x in fv3 if x[0] == "VALORI"] == ["VISTO"]))
    # (6) 0.32.2, 0.32.1 on the real FM-1: a probe the FM-1 read before the work of its pass was done (a THROW gliding
    #     back: FILTER 27 where the simulator, at that ms, says 26). Read by the simulator that many ms earlier it is
    #     the same: timing, and said. Read 300 ms earlier than it says, no lag explains it: an error
    out.append(("0.32.2: a probe is read again no earlier than the FM-1's own lag and four ms (and never more than fourteen)",
                [H.reread_span(x) for x in (9, None, 1, 0, 40)] == [13, 13, 5, 4, 14]))
    gs = [by["grid BEAT pad 1,2"], pg["pagina mod th_filt 127"], by["grid BEAT pad 2,2"], by["grid BEAT pad 3,2"]]
    rt = run_like_banco(session_plan(sit, gs, "t004"), random.Random(seed))
    ft, _ = compare(rt)
    hw = rt["fm1"]
    rp0 = {int(k): tuple(v) for k, v in hw["presi"].items()}
    key = lambda d_, i: i if i in d_ else str(i)        # (a record just made has numbers for keys, one read from a file has text)
    hp = {int(k): T.probe_dict(v) for k, v in hw["sonde"].items()}
    gliding = [i for i, r in H.probe_events(rt) if i in hp and hp[i].get("G", {}).get("mac", "0/0/0/0").split("/")[-1] != "0"]

    def as_read(i, ms):                                 # (the probe as the simulator shows it `ms` earlier)
        rp = dict(rp0)
        rp[i] = (rp[i][0] - ms,) + tuple(rp[i][1:])
        sim2, _ = H.session_replay(rt, rp, hw.get("sentiti"))
        return sim2["sonde"].get(key(sim2["sonde"], i))
    made = None
    for i in gliding:
        for ms in (5, 4, 3):                            # (within the stand-in's lag, 1 ms, and four)
            raw = as_read(i, ms)
            if raw is not None and H.pdiff(T.probe_dict(raw), hp[i]):
                made = (i, ms, raw)
                break
        if made:
            break
    f8 = f9 = []
    far = False
    if made:
        i, ms, raw = made
        r8 = copy.deepcopy(rt)
        r8["fm1"]["sonde"][key(r8["fm1"]["sonde"], i)] = raw
        f8, _ = compare(r8)
        raw9 = as_read(i, 300)
        far = raw9 is not None and bool(H.pdiff(T.probe_dict(raw9), hp[i]))
        r9 = copy.deepcopy(rt)
        r9["fm1"]["sonde"][key(r9["fm1"]["sonde"], i)] = raw9
        f9, _ = compare(r9)
    tempo = [x[2][-70:] for x in f8 if x[0] == "TEMPO" and "prima di finire il suo giro" in x[2]]
    out.append(("0.32.2: a probe the FM-1 read before its pass's work (a THROW gliding, %s ms): TEMPO, said, no error; read 300 ms early: an error (%s | %s | %s)"
                % (made[1] if made else "-", len(gliding), tempo, [x[0] for x in errs(f9)]),
                not errs(ft) and bool(made) and not errs(f8) and len(tempo) == 1 and far and [x[0] for x in errs(f9)] == ["SIMULATORE"]))
    return out


def prova(n, length, seed, out_md, drop=False, lose=False, fm1=0):
    """the banco with the simulator as the FM-1: every session must come out equal; drop / lose: the first session
    with the pages' messages lost by the hub / a frame of what the FM-1 heard lost (the comparison must say it);
    fm1: that many sessions of the whole FM-1's plan too (the PC explorer's, run by the Pi)"""
    plan = piano(n, length, seed)
    if fm1:
        plan["sessioni"] += H.piano(fm1 - 1, length, seed, tablet=1)["sessioni"]
    rnd = random.Random(seed)
    plan["sessioni"] = [run_like_banco(s, rnd, drop_pages=drop and k == 0, lose_heard=lose and k == 0)
                        for k, s in enumerate(plan["sessioni"])]
    plan["fatti"] = {"fm1_version": "simulatore", "hub": "prova"}
    plan["audit"] = []
    path = os.path.join(os.path.dirname(out_md), "raccolta-banco-prova.json")
    T.save(path, plan)
    return confronta(path, out_md)
