#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA SEQ, l'esploratore: prova il firmware come lo proverebbe una persona, ma tutto e in fretta.

Il firmware vero (firmware/src/dinghy.c) gira nel simulatore (tests/host.c). Per ogni SITUAZIONE (vuoto, una band in
play, l'armonia su LOCK, VIAGGIO, PERF, il grid attaccato ...) il simulatore la prepara una volta, poi si copia
(fork) una volta per ogni GESTO del catalogo: ogni tasto, ogni tasto tenuto + un altro, ogni manopola su ogni pagina
(con e senza SEL), ogni tasto della tastiera con ogni modificatore, i gesti a due step, il MASTER, i pad del grid in
ogni vista. Ogni copia fa il suo gesto e guarda la macchina (app_host_probe: tutto lo stato, campo per campo) subito
dopo, dopo due battute, e dopo lo STOP. Una copia che non fa niente ("niente") dice cosa cambia da solo con il tempo:
l'effetto di un gesto e' la differenza con quella.

Poi le REGOLE (REGOLE qui sotto: si leggono e si aggiungono) dicono cosa non deve succedere: sfogliare che cambia la
musica o l'armonia, un canale cambiato da chi non deve, l'armonia che cambia sotto LOCK, una traccia fuori fase con
la battuta, note appese dopo lo STOP, il clock che salta, MIDI non valido, il firmware che muore, una manopola che
girata avanti e indietro non torna dov'era. E per ogni gesto la MAPPA DEGLI EFFETTI: cosa cambia, in quali situazioni.

Poi (--coppie) i gesti a due a due, il secondo misurato contro il primo da solo, e (--sessioni) sessioni lunghe a
caso, che quando trovano qualcosa si accorciano da sole fino ai gesti che bastano a farlo succedere.

    python3 tests/sagga_explore.py                  (tutto: le situazioni, i gesti, le coppie, 200 sessioni)
    python3 tests/sagga_explore.py --veloce         (per la suite dei test: poche situazioni, i gesti principali)
    python3 tests/sagga_explore.py --solo "TECHNO band in play" --gesto "SEQ+PRESETS +1" --vedi
    SAGGA_SIM_CFLAGS="-fsanitize=address,undefined -g" python3 tests/sagga_explore.py    (anche gli errori di memoria)

Scrive build/explore/RAPPORTO.md (cosa ha trovato, come rifarlo), build/explore/EFFETTI.md (la mappa) e
build/explore/rapporto.json; esce con 1 se una regola di tipo ERRORE e' violata.
"""
import argparse
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sagga_sim_tests as S  # noqa: E402

ROOT = S.ROOT
OUT_DIR = os.path.join(ROOT, "build", "explore")
BIN = os.path.join(tempfile.gettempdir(), "sagga_explore_%d" % os.getpid())
BAR_MS = 4 * 24 * S.TICK_US / 1000.0          # a bar at 128 BPM, 1875 ms

BTN_NAME = {S.OCT_DOWN: "OCT-", S.OCT_UP: "OCT+", S.FX: "FX", S.SEL: "SEL", S.ENV: "ENV", S.LFO: "LFO", S.EDIT: "EDIT",
            S.GLO: "GLO", S.HOME: "HOME", S.SAVE: "SAVE", S.ARP: "ARP", S.SEQ: "SEQ", S.PLAY: "PLAY", S.REC: "REC"}
ENC_NAME = {S.E_SEL: "SELECT", S.E_ALG: "ALG", S.K1: "K1", S.K2: "K2", S.K3: "K3", S.K4: "K4", S.E_PRE: "PRESETS"}
PAGES = {S.HOME: 8, S.SEQ: 8, S.ENV: 8, S.LFO: 6, S.ARP: 6, S.SAVE: 5, S.GLO: 4}   # 0.28: ENV 8 (the lanes); 0.26: SAVE 5 THE CLICK; 0.12 (HOME 8 -> GLO 3, SEQ 4 / 8 -> ARP 3-6); 0.13: HOME 8 CHAIN LIST, LFO 4 RATE SEQ, SAVE 4 LIVE IN; 0.20: LFO 5 ENV, 6 MOD; 0.23: SEQ 8 THEORY
MODS = [S.HOME, S.SEQ, S.ENV, S.LFO, S.ARP, S.SAVE, S.FX, S.SEL, S.EDIT, S.GLO]
SEL_MODS = (S.HOME, S.SEQ, S.EDIT, S.FX, S.GLO, S.SAVE)    # the groups with SEL + knob variants (0.12: EDIT notes, FX throws, GLO tempo, SAVE 3 reconnect)


def key_name(mask):
    for i in range(16):
        if mask == S.wk(i):
            return "bianco %d" % (i + 1)
    for i in range(11):
        if mask == S.bk(i):
            return "nero %d" % (i + 1)
    return "tasti %X" % mask


ALL_KEYS = [S.wk(i) for i in range(16)] + [S.bk(i) for i in range(11)]

# ------------------------------------------------------------------------------------------------------------ the gestures


class Gesto:
    """a gesture: a name a person can read and do, a kind for the rules, the events (do(s, t) -> the time it ends)"""

    def __init__(self, name, kind, do, tags=()):
        self.name, self.kind, self.do, self.tags = name, kind, do, set(tags)


def _page_to(s, t, mod, page):
    """with `mod` held: down to the first page (the pages stop there), then up to `page`"""
    for _ in range(PAGES.get(mod, 1) - 1):
        s.tap_btn(t, S.OCT_DOWN, hold=15); t += 30
    for _ in range(page):
        s.tap_btn(t, S.OCT_UP, hold=15); t += 30
    return t


def g_btn(b):
    def do(s, t):
        s.tap_btn(t, b, hold=40)
        return t + 60
    kind = "trasporto" if b == S.PLAY else "registra" if b == S.REC else "modo" if b == S.GLO else "sfoglia"
    return Gesto("tocca %s" % BTN_NAME[b], kind, do)       # (0.12: a tap on HOME SEQ EDIT ENV LFO ARP FX opens its window: the screen only)


WIN_BTNS = (S.HOME, S.SEQ, S.EDIT, S.ENV, S.LFO, S.ARP, S.FX)   # 0.12: the buttons with a window (a tap keeps them "held")


def g_win_key(b, k):
    """0.12: the window of `b` opened with a tap, a key, the window closed with another tap"""
    def do(s, t):
        s.tap_btn(t, b, hold=40); t += 200
        s.tap_key(t, k, hold=40); t += 120
        s.tap_btn(t, b, hold=40)
        return t + 100
    return Gesto("finestra %s+%s" % (BTN_NAME[b], key_name(k)), "comando", do)


def g_win_enc(b, e, d):
    """0.12: the window of `b` opened with a tap, the encoder, the window closed"""
    def do(s, t):
        s.tap_btn(t, b, hold=40); t += 200
        s.enc(t, e, d); t += 150
        s.tap_btn(t, b, hold=40)
        return t + 100
    kind = "sfoglia" if b == S.SEQ and e in (S.E_PRE, S.E_SEL, S.E_ALG) else "modifica"
    return Gesto("finestra %s %s %+d" % (BTN_NAME[b], ENC_NAME[e], d), kind, do)


def g_win_oct(b, up):
    """0.12: the window of `b`, OCT+ / OCT- turns its pages, the window closed"""
    def do(s, t):
        s.tap_btn(t, b, hold=40); t += 200
        s.tap_btn(t, S.OCT_UP if up else S.OCT_DOWN, hold=30); t += 100
        s.tap_btn(t, b, hold=40)
        return t + 100
    return Gesto("finestra %s, %s" % (BTN_NAME[b], "OCT+" if up else "OCT-"), "comando" if b == S.FX else "sfoglia", do)


def g_mod_btn(m, b):
    def do(s, t):
        s.press(t, m); s.tap_btn(t + 30, b, hold=30); s.release(t + 100, m)
        return t + 130
    kind = "sfoglia" if b in (S.OCT_UP, S.OCT_DOWN) and m in PAGES else "comando"
    if m == S.FX and b in (S.OCT_UP, S.OCT_DOWN):
        kind = "comando"
    if m == S.SEL and b in (S.OCT_UP, S.OCT_DOWN):
        kind = "sfoglia"                                   # (the keyboard's octave)
    return Gesto("%s+%s" % (BTN_NAME[m], BTN_NAME[b]), kind, do)


def g_mods_btn(mods, b, kind="comando"):
    """two buttons held, a third tapped (0.12: GLO + SEL + OCT: the live octave)"""
    def do(s, t):
        for i, m in enumerate(mods):
            s.press(t + 30 * i, m)
        t += 30 * len(mods)
        s.tap_btn(t, b, hold=30); t += 60
        for i, m in enumerate(reversed(mods)):
            s.release(t + 20 * i, m)
        return t + 20 * len(mods) + 30
    return Gesto("+".join(BTN_NAME[m] for m in mods) + "+" + BTN_NAME[b], kind, do)


def g_hold_btn(b, ms):
    """a button held `ms` ms (0.12: REC 0.7 s = TAKE)"""
    def do(s, t):
        s.press(t, b); s.release(t + ms, b)
        return t + ms + 60
    return Gesto("tieni %s" % BTN_NAME[b], "comando", do)


def g_hold_mod_btn(m, b, ms):
    def do(s, t):
        s.press(t, m); s.press(t + 30, b); s.release(t + 30 + ms, b); s.release(t + 60 + ms, m)
        return t + ms + 120
    return Gesto("%s, tieni %s" % (BTN_NAME[m], BTN_NAME[b]), "comando", do)


def g_enc(e, d):
    def do(s, t):
        s.enc(t, e, d)
        return t + 40
    kind = "sfoglia" if e in (S.E_SEL, S.E_ALG) else "modifica"
    return Gesto("%s %+d" % (ENC_NAME[e], d), kind, do)


def g_mod_enc(m, page, e, d, sel=False, back=False):
    """M held (on page `page`), SEL held too when `sel`, the encoder d; `back`: then -d (there and back)"""
    def do(s, t):
        s.press(t, m); t += 30
        t = _page_to(s, t, m, page)
        if sel:
            s.press(t, S.SEL); t += 30
        s.enc(t, e, d); t += 150
        if back:
            s.enc(t, e, -d); t += 150
        if sel:
            s.release(t, S.SEL); t += 30
        s.release(t, m)
        return t + 40
    pg = (" %d" % (page + 1)) if m in PAGES else ""
    name = "%s%s %s%s %+d" % (BTN_NAME[m], pg, "SEL+" if sel else "", ENC_NAME[e], d) + (" e ritorno" if back else "")
    kind = "modifica"
    if m == S.SEQ and not sel and e in (S.E_PRE, S.E_SEL, S.E_ALG):
        kind = "sfoglia"                                   # SEQ + PRESETS / SELECT / ALG: the library's genre, part, variation
    return Gesto(name, kind, do, tags={"andata"} if back else ())


def g_mod_key(mods, k):
    def do(s, t):
        for i, m in enumerate(mods):
            s.press(t + 30 * i, m)
        t += 30 * len(mods) + 10
        s.tap_key(t, k, hold=40); t += 70
        for i, m in enumerate(reversed(mods)):
            s.release(t + 20 * i, m)
        return t + 20 * len(mods) + 20
    name = "+".join(BTN_NAME[m] for m in mods) + ("+" if mods else "tocca ") + key_name(k)
    kind = "comando" if mods else "modifica"
    return Gesto(name, kind, do)


def g_two_steps(i, j, fx=False):
    """hold white i, press white j (0.11: the note between them; SEL + FX tapped first (0.12; FX alone before): the loop)"""
    def do(s, t):
        if fx:
            s.press(t, S.SEL); s.tap_btn(t + 30, S.FX, hold=30); s.release(t + 100, S.SEL); t += 160
        s.keys(t, S.wk(i)); s.keys(t + 250, S.wk(i) | S.wk(j)); s.keys(t + 320, S.wk(i)); s.keys(t + 380, 0)
        return t + 420
    return Gesto("%stieni bianco %d + bianco %d" % ("SEL+FX, poi " if fx else "", i + 1, j + 1), "modifica", do)


def g_knob(v):
    def do(s, t):
        s.knob(t, v)
        return t + 40
    return Gesto("MASTER a %d" % v, "modifica", do)


def g_save_twice():
    def do(s, t):
        s.tap_btn(t, S.SAVE, hold=30); s.tap_btn(t + 300, S.SAVE, hold=30)
        return t + 360
    return Gesto("SAVE, SAVE (salva)", "comando", do)


GRID_VIEWS = {                                             # from STEP: the view buttons to get there
    "STEP": [], "DRUM": [(S.GC_VSTEP, 0)], "CC": [(S.GC_VSTEP, 1)], "PICK": [(S.GC_VSTEP, 1), (S.GC_VSTEP, 1)], "PERF": [(S.GC_VPERF, 0)],
    "SONG": [(S.GC_VPERF, 0), (S.GC_VPERF, 0)], "LFO": [(S.GC_VPERF, 1)], "TRACK": [(S.GC_VTRACK, 0)],
    "TRACK2": [(S.GC_VTRACK, 0), (S.GC_VTRACK, 0)], "TRACK3": [(S.GC_VTRACK, 0), (S.GC_VTRACK, 0), (S.GC_VTRACK, 0)],
    "BEAT": [(S.GC_VTRACK, 1)], "EUCLID": [(S.GC_VTRACK, 1), (S.GC_VTRACK, 1)], "PROJ": [(S.GC_REC, 1)],
    "FX": [(S.GC_UNDO, 1)],
    "VIAGGIO": [(S.GC_VPERF, 0), (S.GC_VPERF, 0), (S.GC_VPERF, 0)],   # (0.22: PERF, SONG, VIAGGIO; no test tapped its pads)
}


def _grid_view(s, t, view):
    for c, sh in GRID_VIEWS[view]:
        if sh:
            S.shift(s, t, 1); s.ctl(t + 10, c, hold=20); S.shift(s, t + 40, 0); t += 60
        else:
            s.ctl(t, c, hold=20); t += 40
    return t


def g_pad(view, x, y, shift=False):
    def do(s, t):
        t = _grid_view(s, t, view)
        if shift:
            S.shift(s, t, 1); t += 20
        s.pad(t, x, y, hold=60); t += 80
        if shift:
            S.shift(s, t, 0); t += 20
        return t + 20
    return Gesto("grid %s %spad %d,%d" % (view, "SHIFT+" if shift else "", x + 1, y + 1), "griglia", do, tags={"grid"})


def g_ctl(c, shift=False):
    names = {S.GC_PLAY: "PLAY", S.GC_REC: "REC", S.GC_FILL: "FILL", S.GC_UNDO: "UNDO", S.GC_VSTEP: "STEP",
             S.GC_VPERF: "PERF", S.GC_VTRACK: "TRACK"}
    def do(s, t):
        if shift:
            S.shift(s, t, 1); t += 20
        s.ctl(t, c, hold=30); t += 50
        if shift:
            S.shift(s, t, 0); t += 20
        return t + 20
    nm = names.get(c) or ("traccia %d" % (c - S.GC_TRK0 + 1) if c < S.GC_PAT0 else "pattern %d" % (c - S.GC_PAT0 + 1) if c < S.GC_SCN0 else "scena %d" % (c - S.GC_SCN0 + 1))
    kind = "trasporto" if c == S.GC_PLAY else "griglia"
    return Gesto("grid %s%s" % ("SHIFT+" if shift else "", nm), kind, do, tags={"grid"})


# 0.18: the tablet - the hub's pages, as MIDI on the remote's port (channel 12 SAGGA Live, channel 13 the tablet's TRACK).
# A knob: its value; a switch: on, off; a tap: pressed and let go. (RETRIG, CC 30, puts a track off the bar on purpose.)
TAB_KNOBS = [(3, "PATTERN", (1, 3)), (4, "LENGTH", (8, 32)), (5, "OCTAVE", (2, 5)), (6, "SWING", (58, 66)), (7, "GROOVE", (1, 3)),
             (8, "GROOVE AMT", (40,)), (9, "MIDI FX", (3, 1)), (10, "FX AMOUNT", (14, 9)), (12, "ALGO", (1, 2)), (13, "A", (40,)),
             (14, "B", (90,)), (15, "C", (127,)), (17, "PULSES", (3, 7)), (18, "ROTATION", (2,)), (20, "ARP", (1, 8)),
             (21, "OCTAVES", (2,)), (22, "RATE", (0, 4)), (23, "RUN", (2, 3)), (24, "CHORD", (5, 13)),
             (56, "SOURCE", (0, 1, 2)), (57, "NEXT SEED", (4, 60)), (58, "SEED", (9, 100)), (59, "VARIATION", (2, 40)),   # 0.23: the THEORY engines
             (62, "LANE 7", (30, 100)), (63, "LANE 8", (64,))]                  # 0.28.1: SAGGA Mod's lanes 7 and 8 (the base values)
TAB_SWITCHES = [(1, "MUTE"), (2, "SOLO"), (19, "EUCLID"), (25, "FOLLOW"), (40, "MUTE 1"), (47, "MUTE 8")]
TAB_TAPS = [(11, "FX GO"), (16, "ALGO GO"), (26, "COOK"), (27, "BEAT"), (28, "PROPOSAL"), (29, "QUEUE"), (31, "DICE"), (32, "UNDO"),
            (60, "SHORTER"), (61, "LONGER")]              # (0.25: every track's length, at the bar)


def g_tab(ch, cc, vals, name):
    def do(s, t):
        for v in vals:
            s.raw(t, "midi 0x%02X %d %d 2" % (0xB0 | ch, cc, v)); t += 40
        return t + 20
    return Gesto("tablet %s" % name, "tablet", do, tags={"tablet"})


def tablet_gestures():
    out = [g_tab(12, 112, (v,), "TRACK %d" % (v + 1)) for v in (2, 9)]
    out += [g_tab(11, cc, (v,), "%s %d" % (nm, v)) for cc, nm, vals in TAB_KNOBS for v in vals]
    out += [g_tab(11, cc, (v,), "%s %s" % (nm, "ON" if v else "OFF")) for cc, nm in TAB_SWITCHES for v in (127, 0)]
    out += [g_tab(11, cc, (127, 0), nm) for cc, nm in TAB_TAPS]
    return out


def fits(g, sit):
    """a gesture of the grid needs a situation with the grid attached, one of the tablet one with the tablet (0.18)"""
    return (("grid" not in g.tags) or sit.grid) and (("tablet" not in g.tags) or sit.tablet)


def pick(rnd, cand, sit):
    """a gesture at random; 0.18, with the tablet: the panel, the tablet and the grid a third each (the grid's pads
    are thousands, the tablet's commands a few dozen: else a session would hardly touch the tablet)"""
    if not sit.tablet:
        return rnd.choice(cand)
    groups = [[g for g in cand if not ({"grid", "tablet"} & g.tags)], [g for g in cand if "tablet" in g.tags],
              [g for g in cand if "grid" in g.tags]]
    return rnd.choice(rnd.choice([x for x in groups if x]))


def niente():
    return Gesto("niente", "niente", lambda s, t: t)


def catalogo(veloce=False, grid=False, tablet=False):
    """every gesture, in the order a person would try them"""
    out = [niente()]
    out += [g_btn(b) for b in BTN_NAME]
    out += [g_enc(e, d) for e in ENC_NAME for d in (1, -1)]
    for m in MODS:
        for b in BTN_NAME:
            if b != m and b != S.PLAY or (m == S.SEL and b == S.PLAY):
                out.append(g_mod_btn(m, b))
    for m in MODS:
        for page in range(PAGES.get(m, 1)):
            for e in ENC_NAME:
                for d in (1, -1):
                    out.append(g_mod_enc(m, page, e, d))
                    if m in SEL_MODS:
                        out.append(g_mod_enc(m, page, e, d, sel=True))
                out.append(g_mod_enc(m, page, e, 1, back=True))
                out.append(g_mod_enc(m, page, e, -1, back=True))
                if m in SEL_MODS:
                    out.append(g_mod_enc(m, page, e, 1, sel=True, back=True))
                    out.append(g_mod_enc(m, page, e, -1, sel=True, back=True))
    for mods in ([], [S.HOME], [S.SEQ], [S.SEQ, S.SEL], [S.FX], [S.EDIT], [S.ENV], [S.LFO], [S.SEL], [S.GLO], [S.ARP], [S.SAVE],
                 [S.HOME, S.SEL], [S.ARP, S.SEL], [S.GLO, S.SEL], [S.EDIT, S.SEL], [S.ENV, S.SEL], [S.LFO, S.SEL], [S.FX, S.SEL], [S.SAVE, S.SEL]):
        for k in ALL_KEYS:
            out.append(g_mod_key(mods, k))
    for b in WIN_BTNS:                                                       # 0.12: the windows: a tap, a key / a knob / a page, a tap
        for k in ALL_KEYS:
            out.append(g_win_key(b, k))
        for e in (S.K1, S.K2, S.K3, S.K4):
            for d in (1, -1):
                out.append(g_win_enc(b, e, d))
        out.append(g_win_oct(b, True))
        out.append(g_win_oct(b, False))
    out.append(g_mods_btn([S.GLO, S.SEL], S.OCT_UP))                        # 0.12: the live octave (a command: the music moves)
    out.append(g_mods_btn([S.GLO, S.SEL], S.OCT_DOWN))
    out.append(g_hold_btn(S.REC, 700))                                       # TAKE
    out.append(g_hold_mod_btn(S.SEL, S.GLO, 700))                            # (0.12-0.16 the journey off; 0.17 the MOSSE)
    for b in (S.ARP, S.SEQ):                                                 # (ARP held 0.7 s alone; SEQ + a key held: the hold variants)
        out.append(g_hold_btn(b, 700))
    for i, j in ((0, 3), (2, 5), (4, 11), (0, 15), (7, 8)):
        out.append(g_two_steps(i, j))
        out.append(g_two_steps(i, j, fx=True))
    out += [g_knob(v) for v in (0, 300, 700, 1023)]
    out.append(g_save_twice())
    if grid:
        out += [g_ctl(c, sh) for c in list(range(8)) + [S.GC_TRK0 + 1, S.GC_PAT0 + 1, S.GC_SCN0 + 1] for sh in (False, True) if c != S.GC_SHIFT]
        for view in GRID_VIEWS:
            for y in range(8):
                for x in range(16):
                    out.append(g_pad(view, x, y))
                    if not veloce and view in ("STEP", "BEAT", "TRACK3", "PERF"):
                        out.append(g_pad(view, x, y, shift=True))
    if tablet:
        out += tablet_gestures()
    if veloce:                                       # the main ones: SEQ and HOME pages, the keys with SEQ, the gestures
        keep = []
        for g in out:
            n = g.name
            if g.kind == "griglia" and not re.match(r"grid (BEAT|STEP) pad \d+,[1-4]$", n):
                continue
            if re.match(r"(ENV|LFO|SAVE)\b", n) or "e ritorno" in n and not n.startswith(("SEQ", "HOME", "ARP", "GLO")):
                continue
            if n.startswith("finestra") and not re.match(r"finestra (SEQ|HOME|ARP)\b", n):
                continue
            keep.append(g)
        out = keep
    names = set()
    for g in out:
        assert g.name not in names, g.name
        names.add(g.name)
    return out

# ------------------------------------------------------------------------------------------------------------ the situations


def _band(s, t):
    """BAND: SEQ + black 7 HELD (0.12; a tap is the KIT). Until 0.21 this was 0.11's gesture, SEQ + SEL + black 7, which
    since 0.12 does something else: every situation "with a band" was an empty project (setup_check now says so)"""
    s.press(t, S.SEQ); s.tap_key(t + 30, S.bk(6), hold=700); s.release(t + 800, S.SEQ)
    return t + 900


def _genre(s, t, k):
    s.press(t, S.SEQ); s.enc(t + 30, S.E_PRE, k); s.release(t + 80, S.SEQ)
    return t + 120


def _play(s, t):
    s.tap_btn(t, S.PLAY)
    return t + 60


def _mosse(s, t):
    """SEL + GLO, a tap: the MOSSE (and the studio again)"""
    s.press(t, S.SEL); s.tap_btn(t + 30, S.GLO); s.release(t + 90, S.SEL)
    return t + 150


def _longer(s, t, n):
    """0.24: the MOSSE's LONGER (SEL + black 6) n times - stopped: at once - every track twice as long; the studio again"""
    t = _mosse(s, t)
    for _ in range(n):
        s.press(t, S.SEL); s.tap_key(t + 30, S.bk(5)); s.release(t + 100, S.SEL); t += 160
    return _mosse(s, t)


class Situazione:
    def __init__(self, name, setup, grid=False, tablet=False, hw=True, band=True, lens=None, want=None):
        self.name, self.setup, self.grid, self.tablet = name, setup, grid, tablet
        self.want = want or {}                      # (0.25: {track, or "G": {a value of the probe: what its name promises}}: checked too)
        self.band = band                            # (0.22: it starts from a BAND: situazioni_vere checks that it is there)
        self.hw = hw                                # (False: never on the FM-1 by the PC: a USB reconnect in its set-up)
        self.lens = lens or {}                      # (0.24: {track: (length, the pattern's own steps)} its name promises: checked too)


def sit_vuoto(s):
    return 200


def sit_vuoto_play(s):
    return _play(s, 200)


def sit_techno(s):
    t = _band(s, 200)
    return _play(s, t + 100)


def sit_house_lock(s):
    t = _genre(s, 200, 3)                                   # HOUSE
    t = _band(s, t)
    t = S.harm_knobs(s, t, [(S.K1, 1)])                     # HARMONY (ARP 3): ON -> LOCK
    t = S.pg(s, t, S.ARP, 0)
    return _play(s, t + 100)


def sit_amapiano_fermo(s):
    t = _genre(s, 200, 17)
    return _band(s, t) + 100


def sit_user_prog(s):
    t = _band(s, 200)
    t = S.uprog_knobs(s, t, [(S.K3, 1), (S.K2, 1), (S.K3, 9), (S.K2, 1), (S.K3, 11), (S.K2, 1), (S.K3, 1)])   # USER 1: i bVI bVII i (ARP 5)
    t = S.harm_knobs(s, t, [(S.K2, 6)])                     # HARMONY (ARP 3): USER 1
    s.enc(t, S.E_SEL, 7); t += 60                           # track 8 (the band's bass or chords)
    t = S.harm2_knobs(s, t, [(S.K1, 1), (S.K4, 4)])         # HARMONY 2 (ARP 4): RETRIG, 3+3+2
    t = S.pg(s, t, S.ARP, 0)
    s.enc(t, S.E_SEL, -7); t += 60
    return _play(s, t + 100)


def sit_viaggio(s):
    """0.17: SEL + GLO, the MOSSE (PERF page 3: the black keys are the journey's moves); until 0.16 VIAGGIO mode"""
    t = _band(s, 200)
    s.press(t, S.SEL); s.tap_btn(t + 30, S.GLO); s.release(t + 90, S.SEL); t += 150
    return _play(s, t)


def sit_perf(s):
    t = _band(s, 200)
    s.tap_btn(t, S.GLO); t += 80
    return _play(s, t)


def sit_genre_live(s):
    t = _band(s, 200)
    t = S.tools_knobs(s, t, [(S.K4, 1)])                    # TOOLS (SEQ 6): GENRE ON -> LIVE
    t = S.pg(s, t, S.SEQ, 0)
    return _play(s, t + 100)


def sit_break(s):
    """0.12: a JUNGLE band, track 1 a BREAK (HOME 4 K1 to BREAK), the AMEN ROLL chop, playing"""
    t = _genre(s, 200, 8)                                   # JUNGLE
    t = _band(s, t)
    t = S.pg(s, t, S.HOME, 3, encs=[(S.K1, 4)])             # the mode: FREE -> BREAK (4 clicks)
    t = S.pg(s, t, S.HOME, 0)
    t = S.break_knobs(s, t, [(S.K1, 2)])                    # SEQ 7: the chop after STRAIGHT, twice
    t = S.pg(s, t, S.SEQ, 0)
    return _play(s, t + 100)


def sit_note_loop(s):
    t = s.steps(200, [0, 2, 4, 6, 8, 10, 12, 14])
    s.keys(t, S.wk(1)); s.keys(t + 250, S.wk(1) | S.wk(5)); s.keys(t + 320, S.wk(1)); s.keys(t + 380, 0); t += 450   # a long note
    t = _play(s, t + 100)
    s.tap_btn(t, S.FX, hold=30); t += 80
    s.keys(t, S.wk(3)); s.keys(t + 250, S.wk(3) | S.wk(9)); s.keys(t + 320, S.wk(3)); s.keys(t + 380, 0)   # a loop 4-10
    return t + 450


def sit_013_live(s):
    """0.13: a band; track 1 a CHAIN LIST of three (P1, P2 x2, P3); MOTION 1 bar, the KEYBOARD on, MIDI IN ALWAYS;
    track 8 with a SLIDE on step 1; in play"""
    t = _band(s, 200)
    t = S.home_page(s, t, 6, [(S.K2, 2)])                   # HOME 7 K2: CHAIN LIST
    t = S.home_page(s, t, 7, [(S.K1, 2), (S.K2, 1), (S.K4, 1)])
    t = S.save4(s, t, [(S.K1, 1), (S.K2, 1), (S.K4, 1)])    # SAVE 4: MOTION 1 BAR, KEYBOARD ALL, MIDI IN ALWAYS
    s.enc(t, S.E_SEL, 7); t += 60
    s.press(t, S.EDIT); s.tap_key(t + 30, S.wk(0)); s.tap_key(t + 100, S.bk(6)); s.release(t + 160, S.EDIT); t += 220
    s.enc(t, S.E_SEL, -7); t += 60
    return _play(s, t + 100)


def sit_013_lfo(s):
    """0.13: a band, LFO 1 with a RATE SEQ of three and TRIG on track 1, in play"""
    t = _band(s, 200)
    s.press(t, S.LFO); s.tap_key(t + 30, S.wk(0)); s.release(t + 100, S.LFO); t += 160
    t = S.pg(s, t, S.LFO, 3, [(S.K1, 3), (S.K4, 4), (S.K3, 1), (S.K4, 6)])
    t = S.pg(s, t, S.LFO, 2, [(S.K4, 1)])
    return _play(s, t + 100)


def sit_020_fx(s):
    """0.20: a band; track 1 with NOTE FILTER, CHANCE, RANDOM, GLITCH and ECHO in the chain, GLITCH moved first; LFO 1 an
    ENV on track 1; MOD 1: RANDOM on track 2's FX, MOD 2: LFO 1 on track 3's velocity; in play"""
    t = _band(s, 200)
    for fx, enc in ((7, [(S.K4, 2)]), (5, [(S.K2, -4)]), (6, []), (9, [(S.K2, 5)]), (3, [])):
        t = S.home_page(s, t, 5, [(S.K1, -9), (S.K1, fx)] + enc)
        t = S.seq_page(s, t, 0, keys=[S.wk(5)])
    t = S.pg(s, t, S.HOME, 5, [(S.K1, -9), (S.K1, 9)])
    t = S.pg(s, t, S.HOME, 5, [(S.K1, -8)], sel=True)
    s.press(t, S.LFO); s.tap_key(t + 30, S.wk(0)); s.release(t + 100, S.LFO); t += 160
    t = S.pg(s, t, S.LFO, 0, [(S.K1, 8)])
    t = S.pg(s, t, S.LFO, 2, [(S.K4, 1)])
    t = S.pg(s, t, S.LFO, 5, [(S.K2, 4), (S.K3, 8)])
    t = S.pg(s, t, S.LFO, 5, [(S.K3, 1)], sel=True)
    t = S.pg(s, t, S.LFO, 5, [(S.K1, 1), (S.K2, 1), (S.K3, 3)])
    t = S.pg(s, t, S.LFO, 5, [(S.K3, 2)], sel=True)
    return _play(s, t + 100)


def sit_grid(s):
    s.raw(150, "attach")
    t = _band(s, 300)
    return _play(s, t + 100)


def sit_tablet(s):                                          # 0.18: REMOTE 13 + 14 (SAVE + K2), the grid, the band
    s.press(150, S.SAVE); s.enc(180, S.K2, 1); s.release(250, S.SAVE)
    s.raw(300, "attach")
    t = _band(s, 400)
    return _play(s, t + 100)


def sit_tablet2(s):                                         # ... with USB PORTS 2: the values go back to the hub on port 2
    s.press(150, S.SAVE); s.enc(180, S.K2, 1); s.release(250, S.SAVE)
    t = S.usb2(s, 400)
    s.raw(t, "attach")
    t = _band(s, t + 100)
    return _play(s, t + 100)


def _theory(s, t):
    """0.23: SEQ 8 K1, the SOURCE on THEORY - BEAT, KIT, BAND and the dice MAKE their patterns; back on SEQ 1"""
    t = S.pg(s, t, S.SEQ, 7, [(S.K1, 1)])
    return S.pg(s, t, S.SEQ, 0)


def sit_theory_techno(s):
    """0.23: THEORY, a TECHNO band the engines made (rules written by hand), in play"""
    t = _theory(s, 200)
    t = _band(s, t)
    return _play(s, t + 100)


def sit_theory_live(s):
    """0.23: THEORY, REGGAETON (rules counted from the library), GENRE LIVE (a change of genre makes the band again), in play"""
    t = _genre(s, 200, 10)
    t = _theory(s, t)
    t = S.tools_knobs(s, t, [(S.K4, 1)])                    # TOOLS (SEQ 6): GENRE ON -> LIVE
    t = S.pg(s, t, S.SEQ, 0)
    t = _band(s, t)
    return _play(s, t + 100)


def sit_theory_free(s):
    """0.23: the SOURCE on FREE (SEQ 8 K1, two clicks: the engines with the rules of no genre): a band of no genre, four
    bars a pattern (the answers, the fills), stopped. Until 0.23 LIBRARY LENGTH 64 (SAVE 2 K4) made them four bars;
    0.24: the length is the TRACK's - every track 64 steps first (the MOSSE's LONGER, twice). (0.24 as it was first
    written left this set-up alone: SAVE 2 K4 is LONG PATTERNS now, the tracks stayed 16 steps, and the situation
    explored one bar under the name of four; `lens` is there so that a name cannot say that again)"""
    t = _longer(s, 200, 2)
    t = S.pg(s, t, S.SEQ, 7, [(S.K1, 2)])                   # LIBRARY -> THEORY -> FREE
    t = S.pg(s, t, S.SEQ, 0)
    return _band(s, t) + 100


def sit_theory_mosse(s):
    """0.23: THEORY, a HOUSE band, the MOSSE (SEL + GLO): the journey's moves - RISER, DROP, the energy - fill and empty
    what the engines made; in play"""
    t = _genre(s, 200, 3)
    t = _theory(s, t)
    t = _band(s, t)
    s.press(t, S.SEL); s.tap_btn(t + 30, S.GLO); s.release(t + 90, S.SEL); t += 150
    return _play(s, t)


def sit_theory_tablet(s):
    """0.23: THEORY, an AMAPIANO band (counted rules, eleven parts), the tablet and the grid, in play"""
    s.press(150, S.SAVE); s.enc(180, S.K2, 1); s.release(250, S.SAVE)
    s.raw(300, "attach")
    t = _genre(s, 400, 17)
    t = _theory(s, t)
    t = _band(s, t)
    return _play(s, t + 100)


def sit_024_lengths(s):
    """0.24: the length is the track's. A TECHNO band (the library's patterns: 16 steps each); track 1 at 32 (its second
    bar the pattern's COPIES), track 8 at 19 (three copies: the polymetre); the MOSSE with the moves AT THE BAR (ALG),
    so that a move asked - LONGER and SHORTER too - is there when the probe looks, two bars on; in play"""
    t = _band(s, 200)
    t = S.pg(s, t, S.HOME, 0, [(S.K2, 16)])                 # track 1: LENGTH 32 (stopped: at once)
    s.enc(t, S.E_SEL, 7); t += 60                           # track 8
    t = S.pg(s, t, S.HOME, 0, [(S.K2, 3)])                  # ... LENGTH 19
    s.enc(t, S.E_SEL, -7); t += 60
    t = _mosse(s, t)
    s.enc(t, S.E_ALG, 1); t += 60                           # the moves: at the BAR
    return _play(s, t + 100)


def sit_025_78(s):
    """0.25: THE METRE. A bar of 14 steps - 7/8 as 2+2+3 (GLO 4 K1 two down; stopped: at once) -; THEORY, a TECHNO band
    the engines make in it (their sixteens re-barred); track 2 at 28 (two bars: the second the pattern's copies), track
    8 at 19 (a polymetre against the 14); the MOSSE with the moves AT THE BAR, so that what is asked is there when the
    probe looks; in play"""
    t = S.pg(s, 200, S.GLO, 3, [(S.K1, -2)])
    t = _theory(s, t)
    t = _band(s, t)
    s.enc(t, S.E_SEL, 1); t += 60                           # track 2
    t = S.pg(s, t, S.HOME, 0, [(S.K2, 14)])                 # ... LENGTH 28
    s.enc(t, S.E_SEL, 6); t += 60                           # track 8
    t = S.pg(s, t, S.HOME, 0, [(S.K2, 5)])                  # ... LENGTH 19
    s.enc(t, S.E_SEL, -7); t += 60
    t = _mosse(s, t)
    s.enc(t, S.E_ALG, 1); t += 60                           # the moves: at the BAR
    return _play(s, t + 100)


def sit_025_54(s):
    """0.25: 5/4 - a bar of 20 steps, five quarters (GLO 4 K1 four up) -, the library's HOUSE band in it, the harmony
    on (a chord a bar of 20); track 1 at 40 (two bars); in play"""
    t = S.pg(s, 200, S.GLO, 3, [(S.K1, 4)])
    t = _genre(s, t, 3)                                     # HOUSE
    t = _band(s, t)
    t = S.pg(s, t, S.HOME, 0, [(S.K2, 20)])                 # track 1: LENGTH 40
    t = S.harm_knobs(s, t, [(S.K1, 1)])                     # HARMONY (ARP 3): ON
    t = S.pg(s, t, S.ARP, 0)
    return _play(s, t + 100)


def sit_026(s):
    """0.26: a bar of 20 steps (5/4); the SOURCE on FREE: a band the engines make IN five, its answers with notes (the
    bass under the arpeggio, the lead over the chords, FOLLOW MELODY); the scenes bring their metre (GLO 4 K3); THE
    CLICK while it plays, a note on MIDI channel 10 (SAVE 5); the keyboard's chords are the harmony (SAVE 4: CHORDS);
    in play"""
    t = S.pg(s, 200, S.GLO, 3, [(S.K1, 4), (S.K3, 1)])      # the bar: 20; SCENE METRE: BRING IT
    t = S.pg(s, t, S.SEQ, 7, [(S.K1, 2)])                   # LIBRARY -> THEORY -> FREE
    t = _band(s, t)
    t = S.pg(s, t, S.SAVE, 4, [(S.K1, 2), (S.K3, 10)])      # SAVE 5: CLICK PLAY, CLICK OUT channel 10
    t = S.pg(s, t, S.SAVE, 3, [(S.K2, 3)])                  # SAVE 4: KEYBOARD CHORDS
    t = S.pg(s, t, S.SAVE, 0)
    t = S.pg(s, t, S.SEQ, 0)
    return _play(s, t + 100)


def sit_027(s):
    """0.27: the profile SEMPLICE (SAVE 1 K4: the lab's pages hidden while off); a band of the engines with no key (the
    arpeggio on the root with the rest); EVOLVE running with RETURN 50 (SEQ 3 SEL + K2: half way between EVOLVE and
    DRIFT), on the bank; in play"""
    t = S.pg(s, 200, S.SEQ, 7, [(S.K1, 1)])                 # THEORY
    t = _band(s, t)
    t = S.pg(s, t, S.SEQ, 0, keys=[S.bk(5)])                # the SCOPE: the bank
    t = S.pg(s, t, S.SEQ, 2, [(S.K3, 2)])                   # EVOLVE every 16 bars (it runs, but changes nothing while a
                                                            # gesture is looked at: a change of its would be the gesture's) ...
    t = S.pg(s, t, S.SEQ, 2, [(S.K2, -10)], sel=True)       # ... RETURN 50
    t = S.pg(s, t, S.SEQ, 0, keys=[S.bk(8)])                # ... on
    t = S.pg(s, t, S.SAVE, 0, [(S.K4, 1)])                  # SEMPLICE (SEQ 3 stays: EVOLVE runs)
    return _play(s, t + 100)


def sit_028(s):
    """0.28: twelve tracks, six notes, eight lanes. A TECHNO band; track 12 selected (the bank of 9-12, which has four),
    a chord of six notes on its step 1 (SEL + six keys), locks on its lanes 7 and 8 (ENV 7 and 8, K1); in play"""
    t = _band(s, 200)
    s.press(t, S.HOME); s.tap_key(t + 30, S.wk(11)); s.release(t + 100, S.HOME); t += 160      # track 12
    s.press(t, S.SEL)
    cur = 0
    for i, b in enumerate((7, 9, 11, 12, 14, 16)):                  # C4 D4 E4 F4 G4 A4, 60 ms apart: one chord
        cur |= 1 << b
        s.keys(t + 50 + 60 * i, cur)
    s.keys(t + 450, 0); s.release(t + 500, S.SEL); t += 560
    t = S.pg(s, t, S.ENV, 6, [(S.K1, 20)])                         # lane 7: a lock on step 1
    t = S.pg(s, t, S.ENV, 7, [(S.K1, 30)])                         # lane 8: a lock
    t = S.pg(s, t, S.ENV, 0)
    return _play(s, t + 100)


def sit_025_poly(s):
    """0.25: the POLYRHYTHMS. A TECHNO band; track 3 at 1/4 5:4 with a loop of five steps (five in the bar), track 5
    at 1/16 7:4 (seven in a quarter), track 1 with a TURING as long as the track (LENGTH TRACK) running; in play"""
    t = _band(s, 200)
    s.enc(t, S.E_SEL, 2); t += 60                           # track 3
    t = S.pg(s, t, S.HOME, 0, [(S.K2, -11), (S.K3, 4)])     # ... LENGTH 5, 1/4 5:4
    s.enc(t, S.E_SEL, 2); t += 60                           # track 5
    t = S.pg(s, t, S.HOME, 0, [(S.K3, 9)])                  # ... 1/16 7:4
    s.enc(t, S.E_SEL, -4); t += 60
    t = S.pg(s, t, S.SEQ, 1, [(S.K1, 1), (S.K3, 20)], keys=[S.wk(5)])   # track 1: TURING, LENGTH TRACK, started
    t = S.pg(s, t, S.SEQ, 0)
    return _play(s, t + 100)


def sit_025_melody(s):
    """0.25: THE MELODY KNOWS THE CHORD. The SOURCE on FREE: its band has a LEAD on track 8, which follows as a MELODY
    (the makers give a tune that way; BAND starts the harmony); the harmony on a USER progression i bVI bVII i that
    changes inside the bar (3+3+2), so that the lead's long notes meet the changes; track 8 left selected: the track's
    knobs turn on the tune; in play"""
    t = S.pg(s, 200, S.SEQ, 7, [(S.K1, 2)])                 # LIBRARY -> THEORY -> FREE
    t = S.pg(s, t, S.SEQ, 0)
    t = _band(s, t)
    t = S.uprog_knobs(s, t, [(S.K3, 1), (S.K2, 1), (S.K3, 9), (S.K2, 1), (S.K3, 11), (S.K2, 1), (S.K3, 1)])   # USER 1: i bVI bVII i (ARP 5)
    t = S.harm_knobs(s, t, [(S.K2, 6)])                     # HARMONY (ARP 3): USER 1 (the band left it ON)
    t = S.harm2_knobs(s, t, [(S.K4, 4)])                    # HARMONY 2 (ARP 4): 3+3+2
    t = S.pg(s, t, S.ARP, 0)
    s.enc(t, S.E_SEL, 7); t += 60                           # track 8: the LEAD
    return _play(s, t + 100)


SITUAZIONI = [
    Situazione("vuoto, fermo", sit_vuoto, band=False),
    Situazione("vuoto, in play", sit_vuoto_play, band=False),
    Situazione("TECHNO band in play", sit_techno),
    Situazione("HOUSE band, armonia LOCK, in play", sit_house_lock),
    Situazione("AMAPIANO band, fermo", sit_amapiano_fermo),
    Situazione("progressione USER, FOLLOW RETRIG, 3+3+2, in play", sit_user_prog),
    Situazione("GENRE LIVE, band in play", sit_genre_live),
    Situazione("BREAK sulla traccia 1, band in play", sit_break),
    Situazione("MOSSE in play", sit_viaggio),
    Situazione("PERF in play", sit_perf),
    Situazione("note lunghe e loop fra due step, in play", sit_note_loop, band=False),
    Situazione("0.13 CHAIN LIST, MOTION, KEYBOARD, SLIDE, in play", sit_013_live),
    Situazione("0.13 LFO RATE SEQ e TRIG, band in play", sit_013_lfo),
    Situazione("0.20 MIDI FX nuovi in catena, ENV, MOD MATRIX, band in play", sit_020_fx),
    Situazione("grid attaccato, band in play", sit_grid, grid=True),
    Situazione("0.18 tablet e grid, band in play", sit_tablet, grid=True, tablet=True),
    Situazione("0.18 tablet e grid, 2 porte USB, band in play", sit_tablet2, grid=True, tablet=True, hw=False),
    Situazione("0.23 THEORY: TECHNO band dei motori, in play", sit_theory_techno),
    Situazione("0.23 THEORY: REGGAETON (regole contate), GENRE LIVE, in play", sit_theory_live),
    Situazione("0.23 THEORY: SOURCE FREE (nessun genere), pattern di 4 battute, fermo", sit_theory_free,
               lens={1: (64, 64), 2: (64, 64), 8: (64, 64)}),
    Situazione("0.23 THEORY: AMAPIANO, tablet e grid, in play", sit_theory_tablet, grid=True, tablet=True),
    Situazione("0.23 THEORY: HOUSE, le MOSSE (RISER, DROP, energia), in play", sit_theory_mosse),
    Situazione("0.24 le lunghezze: traccia 1 da 32 e traccia 8 da 19 con le copie, le MOSSE alla battuta, in play", sit_024_lengths,
               lens={1: (32, 16), 2: (16, 16), 8: (19, 16)}),
    Situazione("0.25 il metro: 7/8 (2+2+3), band dei motori THEORY, traccia 2 da 28 e traccia 8 da 19, le MOSSE alla battuta, in play", sit_025_78,
               lens={1: (14, 14), 2: (28, 14), 8: (19, 14)}),
    Situazione("0.25 il metro: 5/4, HOUSE band della libreria, armonia, traccia 1 da 40, in play", sit_025_54,
               lens={1: (40, 20), 2: (20, 20)}),
    Situazione("0.25 i poliritmi: traccia 3 a 1/4 5:4 (5 step), traccia 5 a 1/16 7:4, TURING lungo la traccia, band in play", sit_025_poly,
               lens={3: (5, 5), 5: (16, 16)}),
    Situazione("0.25 la melodia conosce l'accordo: band FREE dei motori, armonia USER 3+3+2, il LEAD (traccia 8) in MELODY, in play", sit_025_melody,
               want={8: {"fm": 3, "follow": 1}, "G": {"harm": 1, "hlock": 0}}),
    Situazione("0.26 i motori nella battuta: 5/4, band FREE nata in cinque, il CLICK su un canale MIDI, KEYBOARD CHORDS, le scene portano il metro, in play", sit_026,
               lens={1: (20, 20), 5: (20, 20)}, want={8: {"fm": 3, "thv": 3}, 5: {"thv": 3}, "G": {"harm": 1}}),
    Situazione("0.27 il profilo SEMPLICE: band dei motori senza tonalita', EVOLVE ogni 16 battute con RITORNO 50 sul banco, in play", sit_027,
               want={"G": {"prof": 2, "evo": 1, "ret": 50}}),
    Situazione("0.28 dodici tracce: la traccia 12 (la banca 9-12), un accordo di sei note, i lock delle lane 7 e 8, band in play", sit_028,
               want={12: {"poly": 6, "lx": 1}, "G": {"sel": 12}}),
]

# ------------------------------------------------------------------------------------------------------------ running

T_AFTER = 1000                                    # the probes, ms after the fork: "dopo" ...
T_BAR = T_AFTER + int(2 * BAR_MS)                 # ... "dopo due battute" ...
T_STOP = T_BAR + 60                               # ... STOP (if it was playing) ...
T_STILL = T_STOP + 500                            # ... "fermo"
PROBES = (("dopo", T_AFTER), ("battuta", T_BAR), ("fermo", T_STILL))


def build():
    """the simulator of this repository's firmware, or of another tree's (SAGGA_EXPLORE_ROOT: its firmware/ with
    tests/host.c beside it, and an app_host_probe of its own: how 0.10 is explored)"""
    fw = os.environ.get("SAGGA_EXPLORE_ROOT", ROOT)
    extra = os.environ.get("SAGGA_SIM_CFLAGS", "").split()
    cmd = ["cc", "-O2", "-w"] + extra + ["-DDINGHY_HOST", '-DAPP_VER="test"', "-I" + fw + "/firmware/src",
                                          "-I" + fw + "/firmware/gen", "-o", BIN, fw + "/firmware/src/dinghy.c"]
    subprocess.run(cmd, check=True, cwd=fw)


def _lines(s):
    return [line for _, _, line in sorted(s.lines)]


def _keep_grid(sit, sc, t_from, t_to):
    """the bridge's keep-alive, every second, while a situation with the grid runs. Without it the FM-1 lets the grid
    go after 3.5 s (GR_TIMEOUT_MS): until 0.21 the explorer's grid was there for the first seconds only, and what a
    branch did after them it did without a grid (the plans for the FM-1 and for the banco always had it)"""
    if sit.grid:
        for t in range((int(t_from) // 1000 + 1) * 1000, int(t_to), 1000):
            sc.raw(t, "hb")


def script_for(sit, branches, settle=600):
    """the situation's setup, then a fork with each branch: (name, [gestures], playing?) -> the script text, the fork time"""
    s = S.Script()
    t0 = int(sit.setup(s)) + settle
    _keep_grid(sit, s, 0, t0)
    out = _lines(s)
    out.append("%d probe" % t0)
    out.append("%d fork" % t0)
    for name, gs, playing in branches:
        b = S.Script()
        t = t0 + 10
        off = (len(gs) - 1) * T_AFTER                     # (two gestures: the second a T_AFTER later, the probes too)
        for k, g in enumerate(gs):
            t = int(g.do(b, max(t, t0 + 10 + k * T_AFTER)))
        for _, when in PROBES:
            b.raw(t0 + when + off, "probe")
        if playing:
            b.tap_btn(t0 + T_STOP + off, S.PLAY)
        _keep_grid(sit, b, t0, t0 + T_STILL + 20 + off)
        out.append("%d branch %s" % (t0, name))
        out += _lines(b)
        out.append("%d endbranch" % (t0 + T_STILL + 20 + off))
    out.append("%d join" % t0)
    out.append("%d end" % (t0 + 50))
    return "\n".join(out) + "\n", t0


PROBE_RE = re.compile(r"^\s*(\d+) ms  PROBE (G|T\d+|H) (.*)$")
MIDI_RE = re.compile(r"^\s*(\d+) ms  MIDI out ([0-9A-F]{2}) (\d+) (\d+)")


def parse_probe(rest):
    d = {}
    if " msg=" in rest:
        rest, msg = rest.split(" msg=", 1)
        d["msg"] = msg
    for kv in rest.split():
        k, _, v = kv.partition("=")
        d[k] = v
    return d


def run_script(text, timeout=900):
    env = dict(os.environ, HOST_NOWAV="1")
    with tempfile.TemporaryDirectory() as d:
        sp = os.path.join(d, "s.txt")
        with open(sp, "w") as f:
            f.write(text)
        p = subprocess.run([BIN, os.path.join(d, "o"), sp], capture_output=True, text=True, cwd=ROOT, env=env, timeout=timeout)
    return p.stdout, p.stderr


def situazioni_vere(sits, empty_row):
    """a situation is what it says: one that starts from a BAND has something written on five tracks at least. Until
    0.21 the band's gesture here was 0.11's (SEQ + SEL + black 7), which 0.12 gave to something else: fourteen
    situations out of seventeen explored an empty project, in the simulator and on the FM-1, and nothing said so"""
    bad = []
    for sit in sits:
        if not sit.band and not sit.lens and not sit.want:
            continue
        base, _ = parse_run(run_script(script_for(sit, [])[0])[0])
        n = sum(1 for k, v in base.items() if k[:1] == "T" and isinstance(v, dict) and v.get("steps#") not in (None, empty_row))
        if sit.band and n < 5:
            bad.append("%s: %d tracce con qualcosa di scritto (una band ne ha almeno 5)" % (sit.name, n))
        for tk, (ln, own) in sorted(sit.lens.items()):      # 0.24: the lengths its name promises
            tr = base.get("T%d" % tk, {})
            if (tr.get("len"), tr.get("own")) != (str(ln), str(own)):
                bad.append("%s: la traccia %d e' lunga %s step e il suo pattern %s (il nome dice %d e %d)" % (
                    sit.name, tk, tr.get("len"), tr.get("own"), ln, own))
        for tk, vals in sorted(sit.want.items(), key=str):  # 0.25: what else its name promises - of a track, or ("G") of the machine
            who = "G" if tk == "G" else "T%d" % tk
            tr = base.get(who, {})
            for key, val in sorted(vals.items()):
                if tr.get(key) != str(val):
                    bad.append("%s: %s ha %s = %s (il nome dice %s)" % (sit.name, "la macchina" if tk == "G" else "la traccia %d" % tk, key, tr.get(key), val))
    return bad


def parse_run(out):
    """-> base probe {G:.., T1:..}, {branch: {"probes": [{G:..}...], "midi": [(t, st, d1, d2)], "died": str}}"""
    base, cur, branches = {}, None, {}
    probe = None
    for line in out.splitlines():
        if line.startswith("BRANCH "):
            cur = {"probes": [], "midi": [], "died": None}
            branches[line[7:]] = cur
            probe = None
            continue
        if line.startswith("BRANCH-DIED "):
            name = line[12:].rsplit(" ", 2)[0]
            if name in branches:
                branches[name]["died"] = line[12:]
            continue
        if line.startswith("BRANCH-END"):
            cur = None
            continue
        m = PROBE_RE.match(line)
        if m:
            who, d = m.group(2), parse_probe(m.group(3))
            if who == "G":
                probe = {"t": int(m.group(1)), "G": d}
                if cur is not None:
                    cur["probes"].append(probe)
                else:
                    base = probe
            elif probe is not None:
                probe[who] = d
            continue
        if cur is not None:
            m = MIDI_RE.match(line)
            if m:
                cur["midi"].append((int(m.group(1)), int(m.group(2), 16), int(m.group(3)), int(m.group(4))))
    return base, branches

# ------------------------------------------------------------------------------------------------------------ the rules

# what a person hears and keeps (a change of these is a change of the music); the rest: where things are on screen
MUSIC_G = ["harm", "hlock", "hgenre", "hprog", "hbars", "hrhythm", "hmood", "chord", "key", "root", "scale", "shift",
           "mute", "solo", "bpm", "mac", "uprog#", "keys#", "scenes#", "lfo#", "song#", "snaps#", "tape#", "dev#",
           "bar", "beats"]                        # (0.25: the metre is music)
HARM_G = ["harm", "hlock", "hgenre", "hprog", "hbars", "hrhythm", "hmood", "chord"]
TRACK_SKIP = {"step", "ok"}                       # (a track's place: the phase rule looks at it)
EMPTY_ROW = None                                  # the hash of an empty pattern (from the empty situation)


def diff(a, b, fields_g=None):
    """the fields that differ between two probes: [("G.genre", old, new), ("T3.ch", ...)]"""
    out = []
    if not a or not b:
        return out
    for k in (fields_g if fields_g is not None else sorted(set(a["G"]) | set(b["G"]))):
        if k in ("msg",):
            continue
        if a["G"].get(k) != b["G"].get(k):
            out.append(("G." + k, a["G"].get(k), b["G"].get(k)))
    for t in range(1, 17):
        ta, tb = a.get("T%d" % t, {}), b.get("T%d" % t, {})
        for k in sorted(set(ta) | set(tb)):
            if k in TRACK_SKIP:
                continue
            if ta.get(k) != tb.get(k):
                out.append(("T%d.%s" % (t, k), ta.get(k), tb.get(k)))
    return out


def motori_stale(pf):
    """MOTORI on a probe taken stopped: the tracks whose engines' pattern is not as the machine is"""
    stale = []
    mid = pf["G"].get("mid")
    for t in range(1, 17):
        tp = pf.get("T%d" % t, {})
        th = (tp.get("th") or "0/0/0/0/0").split("/")
        if len(th) != 5 or not th[0].isdigit() or int(th[0]) > 26:
            stale.append("T%d: th=%s" % (t, tp.get("th")))
        elif th[0] != "0" and tp.get("mode") not in ("T", "B"):
            if mid is not None and tp.get("thm") is not None and tp["thm"] != mid:    # 0.25: made in another metre
                if tp.get("thk") != "1":
                    stale.append("T%d: fatto nel metro %s, la macchina e' nel metro %s" % (t, tp["thm"], mid))
            elif th[4] != pf["G"]["en"]:
                stale.append("T%d: fatto a energia %s, la macchina e' a %s" % (t, th[4], pf["G"]["en"]))
    return stale


def is_music(field):
    g, _, k = field.partition(".")
    return k in MUSIC_G if g == "G" else True


# the gestures that may change the harmony (by hand, or by loading something of a genre)
# (SEQ + black 1-5: DICE SEQ CC LFO GROOVE ALL - ALL may pick a progression; black 7: KIT; white 10 BEAT, 11 PROG; SEQ +
#  SEL + black 1: DICE PROG, black 7: BAND; 0.12: the harmony is ARP 3 / 4 (HARMONY, HARMONY 2), the user progressions ARP 5
#  / 6, PICK (ARP + SEL + a key) sets those knobs by key; GLO 3 K3 is the set's genre: a move (stopped it happens
#  at once), and the harmony follows a genre that is played, as with a load; 0.16: EDIT + ARP copies the progression into a
#  USER slot, which plays from then on; 0.17: PRESETS on the MOSSE (GLO 3) is the progression, a move of the set)
HARM_OK = re.compile(r"^(EDIT\+ARP$|ARP [34] (SEL\+)?K[1-4]|ARP [3456]\+?SEL\+(bianco|nero) |ARP [56] |SEQ\+(SEL\+)?nero (1|5|7)$|SEQ\+(SEL\+)?bianco (10|11)$|"
                     r"finestra SEQ\+nero (1|5|7)$|finestra SEQ\+bianco (10|11)$|finestra ARP K[1-4] |grid PICK pad |"
                     r"GLO 3 (SEL\+)?K3 |GLO 3 PRESETS |grid BEAT|grid PERF|grid SONG|grid VIAGGIO|grid (SHIFT\+)?scena|grid pattern|grid TRACK (SHIFT\+)?pad (10|11),1$|"
                     r"HOME\+SAVE|SAVE, SAVE|tablet (DICE|BEAT)$)")      # (0.18: the tablet's DICE and BEAT are SEQ's)
HARM_OK_LOCK = re.compile(r"^(EDIT\+ARP$|ARP [34] (SEL\+)?K[1-4]|ARP [3456]\+?SEL\+(bianco|nero) |ARP [56] |SEQ\+SEL\+nero 1|HOME\+SAVE|SAVE, SAVE|finestra ARP K[1-4] )")
# the gestures that may change a track's MIDI channel
CH_OK = re.compile(r"^(HOME 1 (SEL\+)?K1|HOME\+SEL\+(bianco|nero) |HOME\+SAVE|finestra HOME K1 |grid TRACK3 (SHIFT\+)?pad \d+,8|grid (SHIFT\+)?scena|"
                   r"grid PICK pad \d+,1$)")      # (0.12: the PICK view's row 1 is K1 of the page open: HOME 1's CHANNEL when no window is)


class Finding:
    def __init__(self, rule, level, sit, gesto, what):
        self.rule, self.level, self.sit, self.gesto, self.what = rule, level, sit, gesto, what

    def key(self):
        return (self.rule, self.sit, self.gesto)

    def as_dict(self):
        return dict(regola=self.rule, livello=self.level, situazione=self.sit, gesto=self.gesto, cosa=self.what)


REGOLE = {
    "SFOGLIARE": ("ERRORE", "sfogliare (pagine, cursore, traccia, la libreria: genere, parte, variazione) non deve cambiare la musica "
                            "ne' l'armonia: solo cio' che e' sullo schermo"),
    "ARMONIA": ("ERRORE", "l'armonia (genere dell'armonia, progressione, accordo) cambia solo a mano (ARP 3-6, DICE PROG, EDIT + ARP) o "
                          "caricando qualcosa di un genere (BEAT, KIT, BAND, PROG, una scena, uno snapshot, un progetto)"),
    "LOCK": ("ERRORE", "con l'armonia su LOCK solo ARP 3-6, DICE PROG ed EDIT + ARP la cambiano"),
    "CANALE": ("ERRORE", "il canale MIDI di una traccia lo cambia solo chi deve (HOME 1 K1, il grid TRACK 3, uno "
                         "snapshot, un progetto caricato)"),
    "NOTE SCRITTE": ("ERRORE", "BAND e KIT non cambiano la nota di una traccia dove e' scritto qualcosa"),
    "FASE": ("ERRORE", "due battute dopo qualunque gesto ogni traccia e' dove la battuta dice (la 0.9 le lasciava spostate)"),
    "COPIE": ("ERRORE", "0.24: due battute dopo qualunque gesto le copie di ogni pattern sono a posto - nel pattern che suona sono "
                        "la fine del loop e ognuna e' lo step del pattern che sta ripetendo; dopo il loop, in ogni pattern, c'e' "
                        "solo il segno di dove il pattern finisce (uno step in pausa)"),
    "NOTE APPESE": ("ERRORE", "dopo lo STOP ogni nota accesa e' spenta"),
    "CLOCK": ("ERRORE", "il clock MIDI non salta: tanti tick quanti ne fa il tempo, se il gesto non e' il tempo o lo STOP"),
    "MIDI": ("ERRORE", "solo MIDI valido: dati a 7 bit, note e CC sui canali 1-16"),
    "MORTO": ("ERRORE", "il firmware non muore (crash, errore di memoria con i sanitizer)"),
    "RITORNO": ("DA GUARDARE", "una manopola girata di uno e poi indietro di uno rimette la musica dov'era (in almeno uno dei "
                               "due versi: in fondo alla scala un verso non si muove)"),
    "MOTORI": ("ERRORE", "0.23: da fermo ogni pattern fatto dai motori THEORY e' all'ENERGIA della macchina (lo riempie e lo svuota "
                         "il servizio dei motori, qualunque gesto sia stato fatto), e cio' che i motori sanno di lui e' uno stile che esiste; "
                         "0.25: ed e' nel METRO della macchina (il servizio lo rifa' quando il metro cambia), a meno che non sia stato "
                         "cambiato a mano: quello resta nel suo metro, e li' l'energia non lo tocca"),
}


# what the rules see and is meant so: (rule, the gesture, why). These go to the report's last section, not counted.
ACCETTATI = [
    # (0.16: EUCLID's knobs and the progression's no longer switch EUCLID LIVE / the HARMONY on: they set them up, READY)
    ("RITORNO", r"^HOME 7 (SEL\+)?K2 ", "CHAIN acceso e spento: se la fine del loop cade in mezzo, la traccia e' gia' passata al pattern dopo"),
    ("RITORNO", r"^(HOME|ENV) \d (SEL\+)?PRESETS ", "il pattern in coda cambia alla fine del loop: con un loop di due step la fine cade fra l'andata e il ritorno"),   # (0.28: ENV 7 and 8, reached later, fall there too)
    ("RITORNO", r"^GLO 3 (SEL\+)?K3 ", "il genere di VIAGGIO porta con se' il genere dell'armonia: tornato indietro, l'armonia resta sul genere del set"),
    # 0.24, seen with the first situation that has a pattern's COPIES in its loop: a fourth field, the only fields that
    # may differ (anything else there and back with the loop's start is still to look at)
    ("RITORNO", r"^HOME \d (SEL\+)?ALG ", "0.24: l'inizio del loop che si sposta fa diventare step le copie del pattern (nessuna starebbe "
     "piu' al posto dello step che ripeteva); tornato indietro la musica e' la stessa, ma sono step e non piu' copie: il pattern "
     "e' lungo quanto il loop (T.own)", r"^T\d+\.own "),
    # 0.25, seen with the first situation that leaves a melody's track selected: the pen is the last note set
    ("RITORNO", r"^EDIT SEL\+K[1-4] ", "0.25: la nota di uno step girata e rimessa lascia la PENNA su quella nota (la penna e' l'ultima nota "
     "scritta: SEL + K4); lo step e la musica sono quelli di prima (T.pen)", r"^T\d+\.pen "),
    # 0.28, seen in a pair of the full round: the genre of the MOSSE (K3, a move, which HARM_OK knows) waits for the end
    # of the phrase; ALG right after it brings the moves to the bar, so the genre - and the harmony that follows it -
    # arrives inside the two bars the probe looks at. The change is K3's
    ("ARMONIA", r"^GLO 3 (SEL\+)?K3 [^,]*, poi (GLO 3 )?(SEL\+)?ALG ", "0.28: il genere delle MOSSE (K3, una mossa) aspetta la fine della "
     "frase; ALG subito dopo porta le mosse alla battuta, e il genere - con l'armonia che lo segue - arriva dentro le due battute "
     "che la sonda guarda: il cambio e' di K3 (G.hgenre)", r"^G\.hgenre "),
]


def accepted(f):
    for rule, rx, why, *only in ACCETTATI:
        if f.rule == rule and re.match(rx, f.gesto) and (not only or all(re.match(only[0], w) for w in f.what.split("; "))):
            return why
    return None


def pair_returns(findings):
    """RITORNO counts only when neither +1 then -1 nor -1 then +1 comes back (at the end of a range one way does not move)"""
    out, ret = [], {}
    for f in findings:
        if f.rule == "RITORNO":
            ret.setdefault((f.sit, f.gesto.replace("+1 e ritorno", "e ritorno").replace("-1 e ritorno", "e ritorno")), []).append(f)
        else:
            out.append(f)
    for (sit, name), fs in ret.items():
        if len({f.gesto for f in fs}) >= 2:
            f = fs[0]
            out.append(Finding("RITORNO", f.level, sit, name.replace(" e ritorno", " +1 / -1 e ritorno"), f.what))
    return out


def tracks_written(base):
    return {t for t in range(1, 17) if "T%d" % t in base and base["T%d" % t].get("steps#") != EMPTY_ROW}   # (0.28: twelve in the probe)


def check_branch(sit, g, base, br, null, findings, label=None, off=0):
    """the rules on one branch; `null`: the branch that did nothing (what time alone does); `label`: the name the finding
    gets (a pair: "A, poi B"; the rules look at g.name, the gesture measured); `off`: the probes' delay (a pair)"""
    name = g.name
    shown = label or name
    found = []
    effects = _check(sit, g, base, br, null, found, off)
    for f in found:
        f.gesto = shown
    findings.extend(found)
    return effects


def _check(sit, g, base, br, null, findings, off):
    name = g.name
    if br.get("died"):
        findings.append(Finding("MORTO", "ERRORE", sit.name, name, br["died"]))
        return []
    probes = br["probes"]
    nprobes = null["probes"] if null else []
    effects = []
    for (label, _), p, q in zip(PROBES, probes, nprobes):
        d = diff(q, p)
        effects += [(label, f, a, b) for f, a, b in d]
    if len(probes) < len(PROBES):
        findings.append(Finding("MORTO", "ERRORE", sit.name, name, "il ramo non e' arrivato alla fine (%d controlli su %d)" % (len(probes), len(PROBES))))
        return effects
    after = [(f, a, b) for lab, f, a, b in effects if lab in ("dopo", "battuta")]
    music = [(f, a, b) for f, a, b in after if is_music(f) or f.endswith(("pen", "ch"))]
    base_playing = base["G"].get("play") == "1"
    # SFOGLIARE: a browse gesture that changes the music (the genre of the library, its part and variation are not music)
    if g.kind == "sfoglia":
        bad = music
        if base["G"].get("gmode") == "2" and re.match(r"^SEQ \d PRESETS", name):
            bad = []                                   # (GENRE LIVE: the genre reloads the band at the bar: wanted)
        if bad:
            findings.append(Finding("SFOGLIARE", "ERRORE", sit.name, name, _fmt(bad)))
    # ARMONIA / LOCK
    harm = [(f, a, b) for f, a, b in after if f in ("G.hgenre", "G.hprog", "G.harm", "G.hlock")]
    locked = base["G"].get("hlock") == "1"
    live_genre = base["G"].get("gmode") == "2" and "PRESETS" in name     # (GENRE LIVE: a genre change reloads: wanted)
    mosse_prog = base["G"].get("vg") == "1" and re.match(r"^PRESETS ", name)   # (0.17: on the MOSSE PRESETS is the progression, a move)
    # 0.24: on the MOSSE K3 is the GENRE, a move too (GLO 3 K3 with GLO held, which HARM_OK knows): the harmony follows
    # the set's genre unless it is locked. Nothing saw it until a situation had the moves AT THE BAR: at the phrase's end
    # (the others) a move asked is still in the queue when the probe looks, two bars on
    mosse_genre = base["G"].get("vg") == "1" and not locked and re.match(r"^K3 ", name)
    if harm and g.kind not in ("sfoglia", "dado") and not live_genre and not mosse_prog and not mosse_genre:
        if locked and not HARM_OK_LOCK.match(name):
            findings.append(Finding("LOCK", "ERRORE", sit.name, name, _fmt(harm)))
        elif not locked and not HARM_OK.match(name):
            findings.append(Finding("ARMONIA", "ERRORE", sit.name, name, _fmt(harm)))
    # CANALE
    ch = [(f, a, b) for f, a, b in after if f.endswith(".ch")]
    if ch and not CH_OK.match(name):                         # (0.17: no VIAGGIO mode, whose K4 was the track's channel)
        findings.append(Finding("CANALE", "ERRORE", sit.name, name, _fmt(ch)))
    # NOTE SCRITTE
    if re.match(r"^SEQ\+(SEL\+)?nero 7$", name):
        written = tracks_written(base)
        pen = [(f, a, b) for f, a, b in after if f.endswith(".pen") and int(f[1:].split(".")[0]) in written]
        if pen:
            findings.append(Finding("NOTE SCRITTE", "ERRORE", sit.name, name, _fmt(pen)))
    # FASE: two bars on, every track where its anchor says
    pb = probes[1]
    if pb["G"].get("play") == "1":
        late = ["T%d (step %s)" % (t, pb["T%d" % t].get("step")) for t in range(1, 17) if pb.get("T%d" % t, {}).get("ok") == "0"]
        if late:
            findings.append(Finding("FASE", "ERRORE", sit.name, name, "fuori fase dopo due battute: " + ", ".join(late)))
    # COPIE (0.24): two bars on (and at the end), every track's copies in order
    for k, when in ((1, "dopo due battute"), (2, "alla fine")):
        bad = ["T%d" % t for t in range(1, 17) if probes[k].get("T%d" % t, {}).get("gh") == "0"]
        if bad:
            findings.append(Finding("COPIE", "ERRORE", sit.name, name, "copie fuori posto %s: %s" % (when, ", ".join(bad))))
            break
    # NOTE APPESE: after the STOP (when it stopped), every note off
    pf = probes[2]
    if pf["G"].get("play") == "0":
        hung = hung_notes(br["midi"], grid=base["G"].get("grid") == "1", tablet=br_tab(br, base))
        if hung:
            findings.append(Finding("NOTE APPESE", "ERRORE", sit.name, name, ", ".join(hung[:8]) + (" ..." if len(hung) > 8 else "")))
    # MOTORI (0.23): stopped, the engines' patterns are at the machine's energy; a record is of a style there is.
    # 0.25: ... and in the machine's metre (mid: the metre now; thm: the one the pattern was made in), but one the
    # player changed by hand (thk): that one stays in its metre, and the energy leaves it alone there
    if pf["G"].get("play") == "0" and "en" in pf["G"]:
        stale = motori_stale(pf)
        if stale:
            findings.append(Finding("MOTORI", "ERRORE", sit.name, name, "; ".join(stale[:6])))
    # CLOCK: the ticks between the fork and the STOP, as many as the branch that did nothing
    if base_playing and null and probes[0]["G"].get("play") == "1" and probes[1]["G"].get("play") == "1" \
            and probes[0]["G"].get("bpm") == base["G"].get("bpm") and g.kind != "trasporto" and "MASTER" not in name:
        t_stop = base["t"] + T_STOP + off
        n1 = sum(1 for m in br["midi"] if m[1] == 0xF8 and m[0] < t_stop)
        n0 = sum(1 for m in null["midi"] if m[1] == 0xF8 and m[0] < t_stop)
        if abs(n1 - n0) > 2:
            findings.append(Finding("CLOCK", "ERRORE", sit.name, name, "%d tick di clock invece di %d" % (n1, n0)))
    # MIDI
    bad = [m for m in br["midi"] if m[2] > 127 or m[3] > 127 or m[1] < 0x80]
    if bad:
        findings.append(Finding("MIDI", "ERRORE", sit.name, name, "byte non validi: %s" % bad[:3]))
    # RITORNO: there and back (the named fields: a hash also sees the values a knob keeps where nothing uses them)
    if "andata" in g.tags:
        back = [(f, a, b) for f, a, b in after if is_music(f) and "#" not in f and not f.endswith(("src", ".poly", ".lx"))]   # (0.28: poly
        # and lx, as the hashes, see the step a knob wrote and wrote back - SET, a lock at the value it had - not the music)
        if back:
            findings.append(Finding("RITORNO", "DA GUARDARE", sit.name, name, _fmt(back)))
    return effects


def br_tab(br, base):
    """the tablet has spoken (0.18): in the machine before, or in any probe of the branch"""
    if base.get("G", {}).get("tabseen") == "1":
        return True
    pr = br.get("probes") or []
    pr = pr.values() if isinstance(pr, dict) else pr
    return any(isinstance(p, dict) and p.get("G", {}).get("tabseen") == "1" for p in pr)


def hung_notes(midi, grid=False, tablet=False):
    """the notes still on at the end: a note-on without its note-off (All Notes Off / All Sound Off end a channel's).
    With the grid: channel 16 is the Launchpads' lights, not notes. 0.18, once the tablet has spoken: notes 100-115 on
    channel 13 are its LFO switches (an LFO on), not music"""
    on = {}
    for tm, st, d1, d2 in midi:
        hi, ch = st & 0xF0, st & 15
        if grid and ch == 15:
            continue
        if tablet and ch == 12 and 100 <= d1 < 116 and hi in (0x80, 0x90):
            continue
        if hi == 0x90 and d2:
            on[(ch, d1)] = on.get((ch, d1), 0) + 1
        elif (hi == 0x80 or (hi == 0x90 and not d2)) and on.get((ch, d1), 0) > 0:
            on[(ch, d1)] -= 1
        elif hi == 0xB0 and d1 in (120, 123):
            for k in [k for k in on if k[0] == ch]:
                on[k] = 0
    return ["canale %d nota %d" % (c + 1, n) for (c, n), v in sorted(on.items()) if v > 0]


def _fmt(changes, n=6):
    out = ["%s %s -> %s" % (f, a, b) for f, a, b in changes[:n]]
    if len(changes) > n:
        out.append("(e altri %d)" % (len(changes) - n))
    return "; ".join(out)

# ------------------------------------------------------------------------------------------------------------ the passes


def explore_situation(sit, gestures, chunk=400, each=None):
    """every gesture in a situation; -> (base, {gesture: branch}). With `each(base, null, results_of_a_chunk)` the
    branches go to it a chunk at a time and are not kept (the memory of one chunk, not of the whole catalogue)"""
    gestures = [g for g in gestures if fits(g, sit)]
    probe_txt, _ = script_for(sit, [])
    base, _ = parse_run(run_script(probe_txt)[0])
    playing = base.get("G", {}).get("play") == "1"
    results = {}
    for i in range(0, len(gestures), chunk):
        part = gestures[i:i + chunk]
        if part[0].name != "niente":
            part = [niente()] + part                  # (each run its own "nothing": the same machine)
        text, _ = script_for(sit, [(g.name, [g], playing) for g in part])
        out, err = run_script(text)
        _, brs = parse_run(out)
        del out, err, text
        got = {}
        for g in part:
            br = brs.get(g.name) or {"probes": [], "midi": [], "died": "il ramo non ha scritto niente"}
            got.setdefault(g.name, br)
        del brs
        if each:
            each(base, got.get("niente"), got)
        else:
            for k, v in got.items():
                results.setdefault(k, v)
    return base, results


def pass_singoli(sits, gestures, jobs, findings, effects_map):
    t0 = time.time()
    by_name = {g.name: g for g in gestures}

    def one(sit):
        fs, eff_map, cnt = [], {}, [0]

        def each(base, null, got):                    # the rules on a chunk, then the chunk goes
            for name, br in got.items():
                g = by_name.get(name)
                if g is None or name == "niente":
                    continue
                cnt[0] += 1
                for lab, f, a, b in check_branch(sit, g, base, br, null, fs):
                    if lab != "fermo":
                        eff_map.setdefault(name, {}).setdefault(f, set()).add(sit.name)
        explore_situation(sit, gestures, each=each)
        print("  ... %s: %d gesti" % (sit.name, cnt[0]), file=sys.stderr, flush=True)
        return fs, eff_map, cnt[0]

    with ThreadPoolExecutor(max_workers=jobs) as ex:
        done = list(ex.map(one, sits))
    n = 0
    for fs, eff_map, cnt in done:
        findings.extend(fs)
        n += cnt
        for name, fields in eff_map.items():
            for f, names in fields.items():
                effects_map.setdefault(name, {}).setdefault(f, set()).update(names)
    return n, time.time() - t0


def pass_coppie(sits, gestures, jobs, findings, rnd, n_pairs):
    """two gestures: B measured against A alone (the machine A left, the same time gone by)"""
    firsts = [g for g in gestures if g.kind in ("comando", "modifica", "griglia") and not g.tags or (g.kind == "griglia" and "andata" not in g.tags)]
    seconds = [g for g in gestures if g.kind == "sfoglia" or re.match(r"^(ARP 3 |SEQ\+(SEL\+)?nero|SEQ\+bianco)", g.name)]
    t0 = time.time()
    count = [0]

    def one(sit):
        local = []
        cand_a = [g for g in firsts if fits(g, sit)]
        cand_b = [g for g in seconds if fits(g, sit)]
        pairs = list({(x.name, y.name): (x, y) for x, y in ((rnd.choice(cand_a), rnd.choice(cand_b)) for _ in range(n_pairs))}.values())
        base, _ = parse_run(run_script(script_for(sit, [])[0])[0])
        playing = base.get("G", {}).get("play") == "1"
        firsts_used = sorted({x.name: x for x, _ in pairs}.values(), key=lambda g: g.name)
        branches = [("A " + x.name, [x, niente()], playing) for x in firsts_used]
        branches += [("A " + x.name + " | B " + y.name, [x, y], playing) for x, y in pairs]
        res = {}
        for i in range(0, len(branches), 300):
            _, brs = parse_run(run_script(script_for(sit, branches[i:i + 300])[0])[0])
            res.update(brs)
        for x, y in pairs:
            br, alone = res.get("A " + x.name + " | B " + y.name), res.get("A " + x.name)
            if not br or not alone or not alone["probes"]:
                continue
            after_a = dict(alone["probes"][0], t=base["t"])          # (the machine as A left it: the flags the rules ask)
            yy = y
            # 0.22: a dice waits after A (the probe says so: the dice of a pattern, of a break ...): OCT keeps it or puts
            # it back and ALG goes through its rolls, whatever B's name says (a page turned with OCT is one of them)
            if after_a.get("G", {}).get("dice") == "1" and (y.kind == "sfoglia" or re.search(r"OCT|ALG", y.name)):
                yy = Gesto(y.name, "dado", y.do, y.tags)
            elif re.match(r"^(finestra )?SEQ\+(SEL\+)?nero [1-5]$", x.name) and (y.kind == "sfoglia" or re.search(r"OCT|ALG", y.name) or
                                                                         (y.name.split(" ")[0] in ("SEQ", "HOME", "ARP", "LFO", "ENV", "SAVE", "GLO") and re.match(r"^\w+ \d", y.name))):   # (0.12: the window's DICE too; a page reached with OCT)
                yy = Gesto(y.name, "dado", y.do, y.tags)                # (a dice waits: OCT keeps or puts it back, ALG goes through the rolls)
            elif after_a.get("G", {}).get("vg") == "1" and re.match(r"^ALG [+-]1$", y.name):
                yy = Gesto(y.name, "comando", y.do, y.tags)             # (0.26: A opened the MOSSE - there ALG says WHEN a move waits for: a command, not a page turned)
            check_branch(sit, yy, after_a, br, alone, local, label="%s, poi %s" % (x.name, y.name), off=T_AFTER)
            count[0] += 1
        return local

    with ThreadPoolExecutor(max_workers=jobs) as ex:
        for local in ex.map(one, sits):
            findings.extend(local)
    return count[0], time.time() - t0


def session_check(sit, gs, rnd_seed):
    """a session: the gestures one after the other, a probe after each; -> findings (rules that need no 'nothing' branch)"""
    s = S.Script()
    t0 = int(sit.setup(s)) + 600
    _keep_grid(sit, s, 0, t0)
    lines = _lines(s)
    b = S.Script()
    t = t0 + 10
    for k, g in enumerate(gs):
        t = int(g.do(b, max(t, t0 + 10 + k * 700)))
        b.raw(t0 + (k + 1) * 700 - 20, "probe")
    tend = t0 + (len(gs) + 1) * 700 + int(2 * BAR_MS)
    b.raw(tend, "probe")
    b.tap_btn(tend + 20, S.PLAY)
    b.raw(tend + 600, "probe")
    _keep_grid(sit, b, t0, tend + 650)
    text = "\n".join(lines + ["%d probe" % t0, "%d fork" % t0, "%d branch sessione" % t0] + _lines(b) +
                     ["%d endbranch" % (tend + 650), "%d join" % t0, "%d end" % (t0 + 10)]) + "\n"
    out, _ = run_script(text)
    base, brs = parse_run(out)
    br = brs.get("sessione") or {"probes": [], "midi": [], "died": "niente"}
    found = []
    if br.get("died") or len(br["probes"]) < len(gs) + 2:
        found.append(("MORTO", br.get("died") or "la sessione non e' arrivata alla fine"))
        return found
    pb = br["probes"][-2]
    if pb["G"].get("play") == "1":
        late = ["T%d" % t for t in range(1, 17) if pb.get("T%d" % t, {}).get("ok") == "0"]
        if late:
            first = None                                     # (the gesture after which the first of them went out of time)
            for k, p in enumerate(br["probes"][:len(gs)]):
                if any(p.get(x, {}).get("ok") == "0" for x in late):
                    first = k
                    break
            where = (" (dal gesto %d, %s)" % (first + 1, gs[first].name)) if first is not None else ""
            found.append(("FASE", "fuori fase alla fine: " + ", ".join(late) + where))
    for pc, when in ((br["probes"][-2], "dopo due battute"), (br["probes"][-1], "alla fine")):   # COPIE (0.24)
        bad = ["T%d" % t for t in range(1, 17) if pc.get("T%d" % t, {}).get("gh") == "0"]
        if bad:
            first = None                                     # (the gesture after which the first of them had its copies out of place)
            for k, p in enumerate(br["probes"][:len(gs)]):
                if any(p.get(x, {}).get("gh") == "0" for x in bad):
                    first = k
                    break
            where = (" (dal gesto %d, %s)" % (first + 1, gs[first].name)) if first is not None else ""
            found.append(("COPIE", "copie fuori posto %s: %s%s" % (when, ", ".join(bad), where)))
            break
    if br["probes"][-1]["G"].get("play") == "0":
        hung = hung_notes(br["midi"], grid=base["G"].get("grid") == "1", tablet=br_tab(br, base))
        if hung:
            found.append(("NOTE APPESE", ", ".join(hung[:6])))
        if "en" in br["probes"][-1]["G"]:                    # MOTORI (0.25: at the end of a session too)
            stale = motori_stale(br["probes"][-1])
            if stale:
                found.append(("MOTORI", "; ".join(stale[:6])))
    bad = [m for m in br["midi"] if m[2] > 127 or m[3] > 127]
    if bad:
        found.append(("MIDI", "byte non validi: %s" % bad[:3]))
    return found


def shrink(sit, gs, rule):
    """the fewest of the session's gestures that still break `rule` (delta debugging: halves, quarters ... then one at a
    time; the session is cut first after the gesture where it broke, when that is known)"""
    def fails(seq):
        return bool(seq) and any(r == rule for r, _ in session_check(sit, seq, 0))
    cur = list(gs)
    m = None
    for r, what in session_check(sit, cur, 0):
        mm = re.search(r"\(dal gesto (\d+),", what) if r == rule else None
        if mm:
            m = int(mm.group(1))
    if m and fails(cur[:m]):
        cur = cur[:m]
    n = 2
    while len(cur) >= 2:
        size = max(1, len(cur) // n)
        chunks = [cur[i:i + size] for i in range(0, len(cur), size)]
        for i in range(len(chunks)):
            trial = [g for j, c in enumerate(chunks) if j != i for g in c]
            if fails(trial):
                cur, n = trial, max(n - 1, 2)
                break
        else:
            if size == 1:
                break
            n = min(len(cur), n * 2)
    return cur


def pass_sessioni(sits, gestures, jobs, findings, rnd, n_sessions, length):
    pool = [g for g in gestures if g.name != "niente" and "andata" not in g.tags]
    t0 = time.time()
    plans = []
    for k in range(n_sessions):
        sit = sits[k % len(sits)]
        cand = [g for g in pool if fits(g, sit)]
        plans.append((sit, [pick(rnd, cand, sit) for _ in range(length)]))

    def one(plan):
        sit, gs = plan
        out = []
        for rule, what in session_check(sit, gs, 0):
            short = shrink(sit, gs, rule)
            out.append(Finding(rule, REGOLE[rule][0], sit.name, " -> ".join(g.name for g in short), what))
        return out

    with ThreadPoolExecutor(max_workers=jobs) as ex:
        for local in ex.map(one, plans):
            findings.extend(local)
    return len(plans), time.time() - t0

# ------------------------------------------------------------------------------------------------------------ the report


def report(findings, effects_map, stats, path_md, path_fx, path_json):
    seen, uniq, acc = set(), [], {}
    for f in findings:
        if f.key() in seen:
            continue
        seen.add(f.key())
        why = accepted(f)
        if why:
            acc.setdefault((f.rule, why), set()).add(f.gesto)
            continue
        uniq.append(f)
    by_rule = {}
    for f in uniq:
        by_rule.setdefault(f.rule, []).append(f)
    lines = ["# SAGGA SEQ, l'esploratore: cosa ha trovato", "",
             "%s. Il firmware del repository, nel simulatore." % time.strftime("%Y-%m-%d %H:%M"), ""]
    for k, v in stats:
        lines.append("* %s: %s" % (k, v))
    lines += ["", "| regola | tipo | casi |", "| --- | --- | --- |"]
    for r, (lvl, what) in REGOLE.items():
        lines.append("| %s | %s | %d |" % (r, lvl, len(by_rule.get(r, []))))
    lines.append("")
    for r, (lvl, what) in REGOLE.items():
        fs = by_rule.get(r, [])
        if not fs:
            continue
        lines += ["## %s (%s): %d" % (r, lvl, len(fs)), "", "_%s_" % what, ""]
        for f in fs[:60]:
            lines.append("* **%s** / %s: %s" % (f.sit, f.gesto, f.what))
            lines.append("  rifallo: `python3 tests/sagga_explore.py --solo \"%s\" --gesto \"%s\" --vedi`" % (f.sit, f.gesto.split(" -> ")[0].split(", poi ")[0].replace(" / -1 e ritorno", " e ritorno")))
        if len(fs) > 60:
            lines.append("* (e altri %d: rapporto.json)" % (len(fs) - 60))
        lines.append("")
    if acc:
        lines += ["## Visti e voluti", "", "_Le regole li vedono, ma sono il firmware come deve essere (ACCETTATI in "
                  "tests/sagga_explore.py)._", ""]
        for (rule, why), gs in sorted(acc.items()):
            lines.append("* %s: %s (%d gesti: %s)" % (rule, why, len(gs), ", ".join(sorted(gs)[:4]) + (" ..." if len(gs) > 4 else "")))
        lines.append("")
    with open(path_md, "w") as f:
        f.write("\n".join(lines) + "\n")
    fx = ["# SAGGA SEQ, la mappa degli effetti", "",
          "Per ogni gesto, cosa cambia rispetto a non fare niente (dopo il gesto e due battute dopo), e in quante "
          "situazioni. G.* la macchina, Tn.* la traccia n.", ""]
    for name in sorted(effects_map):
        fields = effects_map[name]
        if not fields:
            continue
        fx.append("* **%s**: %s" % (name, ", ".join("%s (%d)" % (k, len(v)) for k, v in sorted(fields.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:14])))
    with open(path_fx, "w") as f:
        f.write("\n".join(fx) + "\n")
    with open(path_json, "w") as f:
        json.dump(dict(stats=dict(stats), findings=[x.as_dict() for x in uniq],
                       effects={k: {f: sorted(v) for f, v in d.items()} for k, d in effects_map.items()}), f, indent=1, ensure_ascii=False)
    return uniq


def vedi(sit, g):
    """one gesture in one situation, all of it: the probes before / after against doing nothing, the MIDI"""
    text, _ = script_for(sit, [("niente", [niente()], True), (g.name, [g], True)])
    base, brs = parse_run(run_script(text)[0])
    playing = base["G"].get("play") == "1"
    text, _ = script_for(sit, [("niente", [niente()], playing), (g.name, [g], playing)])
    out, err = run_script(text)
    base, brs = parse_run(out)
    print("situazione: %s; gesto: %s" % (sit.name, g.name))
    print("prima: " + " ".join("%s=%s" % kv for kv in base["G"].items() if kv[0] in ("play", "genre", "hgenre", "hprog", "chord", "harm", "hlock", "msg")))
    br, null = brs.get(g.name), brs.get("niente")
    if not br:
        print("il ramo non ha scritto niente"); return
    for (lab, _), p, q in zip(PROBES, br["probes"], null["probes"]):
        d = diff(q, p)
        print("%-8s msg=%r" % (lab, p["G"].get("msg", "")))
        for f, a, b in d:
            print("          %s: %s -> %s" % (f, a, b))
    notes = [m for m in br["midi"] if (m[1] & 0xF0) in (0x80, 0x90)]
    print("note mandate: %d (niente: %d)" % (len(notes), len([m for m in null["midi"] if (m[1] & 0xF0) in (0x80, 0x90)])))
    if err.strip():
        print(err[-3000:])


def main(argv):
    global EMPTY_ROW
    ap = argparse.ArgumentParser(description="SAGGA SEQ, l'esploratore")
    ap.add_argument("--veloce", action="store_true", help="poche situazioni e i gesti principali (per la suite dei test)")
    ap.add_argument("--solo", help="solo questa situazione (il nome intero, o un pezzo: tutte quelle che lo contengono)")
    ap.add_argument("--gesto", help="solo questo gesto (con --solo e --vedi: tutto quello che fa)")
    ap.add_argument("--vedi", action="store_true", help="mostra un gesto per intero")
    ap.add_argument("--coppie", type=int, default=None, help="quante coppie di gesti per situazione (0: nessuna)")
    ap.add_argument("--sessioni", type=int, default=None, help="quante sessioni a caso (0: nessuna)")
    ap.add_argument("--lunghe", type=int, default=60, help="gesti per sessione")
    ap.add_argument("--seme", type=int, default=11, help="il seme del caso (le stesse coppie e sessioni a ogni giro)")
    ap.add_argument("--jobs", type=int, default=max(1, min(4, os.cpu_count() or 1)))   # (at most 4: each holds a simulator and a chunk)
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--uscita", default=OUT_DIR, help="dove scrivere il rapporto (build/explore)")
    ap.add_argument("--hw-piano", metavar="FILE", help="l'FM-1 vero: scrive il piano (--sessioni, --lunghe, --seme) per "
                                                         "tools/hwtest/run_hw_explore.ps1")
    ap.add_argument("--hw", metavar="RACCOLTA", help="l'FM-1 vero: confronta la raccolta del PC con il simulatore -> RAPPORTO-HW.md")
    ap.add_argument("--hw-tablet", type=int, default=0, metavar="N", help="con --hw-piano: N sessioni in piu' con il "
                    "tablet e il grid (0.18: le pagine del hub e i pad come MIDI dalla porta del remoto)")
    ap.add_argument("--hw-prova", action="store_true", help="il piano e il confronto con il simulatore al posto dell'FM-1")
    ap.add_argument("--sessione", help="con --hw: solo questa sessione (con --vedi: sonda per sonda)")
    ap.add_argument("--banco-piano", metavar="FILE", help="il banco (0.20.3: FM-1, Pi e grid): scrive il piano per il Pi "
                    "(--sessioni, --lunghe, --seme; make_release lo mette nello zip del hub)")
    ap.add_argument("--banco", metavar="RACCOLTA", help="il banco: confronta la raccolta del Pi con il simulatore -> RAPPORTO-BANCO.md")
    ap.add_argument("--banco-prova", action="store_true", help="il banco con il simulatore al posto dell'FM-1 (deve dire tutto "
                    "uguale) e poi con i messaggi delle pagine persi per strada (deve trovarlo)")
    a = ap.parse_args(argv)
    if a.banco_piano or a.banco or a.banco_prova:
        import sagga_banco as BC
        if a.banco_piano:
            # (0.24: a session for every situation of the banco - 21 with the lengths' one; it was 20, and one more
            #  situation would have stayed out of the plan without a word)
            plan = BC.piano(a.sessioni if a.sessioni is not None else len(BC.banco_situazioni()), a.lunghe if a.lunghe != 60 else 40, a.seme)
            os.makedirs(os.path.dirname(os.path.abspath(a.banco_piano)), exist_ok=True)
            BC.T.save(a.banco_piano, plan)
            dur = sum(s["eventi"][-1][0] for s in plan["sessioni"]) / 1000.0
            print("piano del banco: %d sessioni, %d gesti sulle pagine, circa %d minuti (con i riavvii) -> %s" % (
                len(plan["sessioni"]), sum(1 for s in plan["sessioni"] for g in s["gesti"] if g.startswith("pagina")),
                (dur + 12 * len(plan["sessioni"])) / 60 + 1, a.banco_piano))
            return 0
        if not a.no_build:
            build()
        os.makedirs(a.uscita, exist_ok=True)
        try:
            if a.banco_prova:
                n, ln = (a.sessioni if a.sessioni is not None else 4), (a.lunghe if a.lunghe != 60 else 24)
                rc = BC.prova(n, ln, a.seme, os.path.join(a.uscita, "RAPPORTO-BANCO-PROVA.md"), fm1=3)   # (+3 of the whole FM-1's)
                rc2 = BC.prova(1, ln, a.seme, os.path.join(a.uscita, "RAPPORTO-BANCO-PERSI.md"), drop=True)
                print("sagga banco, le pagine perse: %s" % ("trovate" if rc2 else "NON TROVATE"))
                rc3 = BC.prova(1, ln, a.seme + 1, os.path.join(a.uscita, "RAPPORTO-BANCO-SORDO.md"), lose=True)
                print("sagga banco, quello che l'FM-1 ha sentito perso per strada: %s" % ("trovato" if rc3 else "NON TROVATO"))
                tempo = BC.prova_tempo(a.seme)             # 0.23.1: the ms of what was heard, what was lost, the end
                for what, ok in tempo:
                    if not ok:
                        print("  FAIL: " + what)
                print("sagga banco, il tempo e i persi (0.23.1): %d prove, %s" % (len(tempo), "a posto" if all(ok for _, ok in tempo) else "NON A POSTO"))
                return rc or (0 if rc2 and rc3 and all(ok for _, ok in tempo) else 1)
            return BC.confronta(a.banco, os.path.join(a.uscita, "RAPPORTO-BANCO.md"))
        finally:
            try:
                os.unlink(BIN)
            except OSError:
                pass
    if a.hw_piano or a.hw or a.hw_prova:
        import sagga_explore_hw as H
        if a.hw_piano:
            plan = H.piano(a.sessioni if a.sessioni is not None else H.situazioni_n(), a.lunghe, a.seme, tablet=a.hw_tablet)   # (0.24: every situation once; it was 20)
            dest = a.hw_piano
            if not dest.endswith(".json"):                 # a folder: the plan and what Windows needs to run it
                os.makedirs(dest, exist_ok=True)
                import shutil
                for f in ("sagga_hw_explore.py", "sagga_testport.py", "sagga_hw_test.py", "run_hw_explore.ps1", "LEGGIMI.md"):
                    shutil.copy(os.path.join(ROOT, "tools", "hwtest", f), dest)
                shutil.copy(os.path.join(ROOT, "tools", "fm1_install.py"), dest)
                dest = os.path.join(dest, "piano.json")
            os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
            H.T.save(dest, plan)
            a.hw_piano = dest
            dur = sum(s["eventi"][-1][0] for s in plan["sessioni"]) / 1000.0
            print("piano: %d sessioni da %d gesti, %d eventi, circa %d minuti sull'FM-1 (con i riavvii) -> %s" % (
                len(plan["sessioni"]), a.lunghe, sum(len(s["eventi"]) for s in plan["sessioni"]),
                (dur + 8 * len(plan["sessioni"])) / 60 + 1, a.hw_piano))
            return 0
        if not a.no_build:
            build()
        os.makedirs(a.uscita, exist_ok=True)
        try:
            if a.hw_prova:
                return H.prova(a.sessioni if a.sessioni is not None else 6, a.lunghe if a.lunghe != 60 else 30, a.seme,
                               os.path.join(a.uscita, "RAPPORTO-HW-PROVA.md"))
            return H.confronta(a.hw, os.path.join(a.uscita, "RAPPORTO-HW.md"), only=a.sessione, show=a.vedi)
        finally:
            try:
                os.unlink(BIN)
            except OSError:
                pass
    if not a.no_build:
        build()
    sits = SITUAZIONI if not a.veloce else [SITUAZIONI[0], SITUAZIONI[2], SITUAZIONI[3], SITUAZIONI[5], SITUAZIONI[10],
                                            SITUAZIONI[18],     # (0.23: + THEORY with counted rules and GENRE LIVE)
                                            SITUAZIONI[22],     # (0.24: + the lengths, the copies, the moves at the bar)
                                            SITUAZIONI[23],     # (0.25: + the metre: 7/8, the engines' band in it)
                                            SITUAZIONI[-1]]     # (0.28: + twelve tracks - the bank of 9-12 -, six notes, eight lanes)
    if a.solo:
        sits = [x for x in SITUAZIONI if x.name == a.solo] or [x for x in SITUAZIONI if a.solo in x.name]   # (0.23: or every one with this in its name)
        if not sits:
            print("situazioni: " + "; ".join(x.name for x in SITUAZIONI)); return 2
    gestures = catalogo(veloce=a.veloce, grid=any(x.grid for x in sits), tablet=any(x.tablet for x in sits))
    if a.gesto:
        gs = [g for g in gestures if g.name == a.gesto]
        if not gs:
            print("nessun gesto si chiama cosi'. Qualcuno: " + "; ".join(g.name for g in gestures[:40])); return 2
        if a.vedi:
            vedi(sits[0], gs[0]); return 0
        gestures = [niente()] + gs
    # the empty row's hash (a pattern with nothing written), from the empty machine
    base, _ = parse_run(run_script(script_for(SITUAZIONI[0], [])[0])[0])
    EMPTY_ROW = base["T1"]["steps#"]
    rnd = random.Random(a.seme)
    findings, effects_map, stats = [], {}, []
    false_sits = situazioni_vere(SITUAZIONI, EMPTY_ROW)       # (all of them, every time: the plans for the FM-1 use them all)
    for x in false_sits:
        print("SITUAZIONE FALSA: " + x)
    n, dt = pass_singoli(sits, gestures, a.jobs, findings, effects_map)
    stats.append(("gesti provati da soli", "%d (%d gesti x %d situazioni) in %.0f s" % (n, len(gestures) - 1, len(sits), dt)))
    pairs = a.coppie if a.coppie is not None else (0 if a.gesto else (40 if a.veloce else 400))
    if pairs:
        n, dt = pass_coppie(sits, gestures, a.jobs, findings, rnd, pairs)
        stats.append(("coppie di gesti", "%d in %.0f s" % (n, dt)))
    sess = a.sessioni if a.sessioni is not None else (0 if a.gesto else (10 if a.veloce else 200))
    if sess:
        n, dt = pass_sessioni(sits, gestures, a.jobs, findings, rnd, sess, a.lunghe)
        stats.append(("sessioni a caso", "%d da %d gesti in %.0f s" % (n, a.lunghe, dt)))
    findings = pair_returns(findings)
    os.makedirs(a.uscita, exist_ok=True)
    uniq = report(findings, effects_map, stats, os.path.join(a.uscita, "RAPPORTO.md"), os.path.join(a.uscita, "EFFETTI.md"),
                  os.path.join(a.uscita, "rapporto.json"))
    errs = [f for f in uniq if f.level == "ERRORE"]
    warns = [f for f in uniq if f.level != "ERRORE"]
    print("sagga explore: %s; %d errori, %d da guardare (%s)" % ("; ".join("%s %s" % kv for kv in stats), len(errs), len(warns),
                                                                 os.path.relpath(os.path.join(a.uscita, "RAPPORTO.md"), ROOT)))
    for f in errs[:20]:
        print("  %s | %s | %s: %s" % (f.rule, f.sit, f.gesto, f.what[:160]))
    try:
        os.unlink(BIN)
    except OSError:
        pass
    return 1 if errs or false_sits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
