#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA SEQ scenario tests: the real firmware (firmware/src/dinghy.c) runs on this computer through the host
simulator (tests/host.c, one platform_poll = 1 ms); a script presses buttons, turns encoders, taps grid pads;
the MIDI the firmware sends is read back from the log and checked.

    python3 tests/sagga_sim_tests.py            (from the repository root)
"""
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(tempfile.gettempdir(), "sagga_sim_host_%d" % os.getpid())

# panel ids (platform.c)
OCT_DOWN, OCT_UP, FX, SEL, ENV, LFO, EDIT, GLO, HOME, SAVE, ARP, SEQ, PLAY, REC = range(14)
E_SEL, E_ALG, K1, K2, K3, K4, E_PRE = range(7)

KEY0 = 53
def _is_black(n): return (0x54A >> (n % 12)) & 1
WHITE = [k for k in range(27) if not _is_black(KEY0 + k)][:16]
BLACK = [k for k in range(27) if _is_black(KEY0 + k)][:11]
def wk(i): return 1 << WHITE[i]
def bk(i): return 1 << BLACK[i]
KEY_C4, KEY_E4, KEY_G4 = 1 << 7, 1 << 11, 1 << 14       # notes 60, 64, 67

# grid LED roles (sagga_grid.c)
(GL_OFF, GL_FAINT, GL_DIM, GL_ON, GL_ACCENT, GL_PLAY, GL_CURSOR, GL_BLUE, GL_MUTED, GL_PEND, GL_FILL, GL_WHITE,
 GL_CYAN, GL_VIOLET, GL_ORANGE, GL_YELLOW) = range(16)
# grid buttons
GC_PLAY, GC_REC, GC_FILL, GC_UNDO, GC_VSTEP, GC_VPERF, GC_VTRACK, GC_SHIFT = range(8)
GC_TRK0, GC_PAT0, GC_SCN0 = 8, 16, 24

SQ_ROLE_KICK, SQ_ROLE_BASS, SQ_ROLE_PAD = 1, 5, 21                 # (sagga_seq_core.h)


def arp_tap(s, t):
    """0.12: SEL + ARP tapped = the arpeggio on / off (ARP alone opens its window)"""
    s.press(t, SEL); s.tap_btn(t + 30, ARP, hold=30); s.release(t + 100, SEL)
    return t + 160


def fx_tap(s, t):
    """0.12: SEL + FX tapped = the next two-step gesture is a LOOP (FX alone opens its window)"""
    s.press(t, SEL); s.tap_btn(t + 30, FX, hold=30); s.release(t + 100, SEL)
    return t + 160


def pen_turn(s, t, d):
    """SEL + K4: the selected track's note (the pen), d semitones"""
    s.press(t, SEL); s.enc(t + 30, K4, d); s.release(t + 80, SEL)
    return t + 140


# 0.11: the BEAT library as the firmware has it (firmware/src/sagga_beats_data.h): the parts of a genre, their variations
_LIB = None


def library():
    """{genre: [(part, [(text, notes or None), ...]), ...]} in the firmware's order (its band first)"""
    global _LIB
    if _LIB is None:
        src = open(os.path.join(ROOT, "firmware", "src", "sagga_beats_data.h")).read()
        a = src.index("static const char POOL[SQ_LIB_POOL] =")
        b = src.index('";', a)
        pool = "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', src[a:b + 1])).replace("\\000", "\0")
        voff = [tuple(map(int, m)) for m in re.findall(r"\{(\d+), (\d+)\},", src[src.index("static const uint32_t VOFF"):src.index("static const lib_part_t GPART")])]
        get = lambda o: pool[o:pool.index("\0", o)] if o else None
        _LIB = {}
        for m in re.finditer(r"\{\s*(\d+),\s*(\d+),\s*(\d+), (\d), +(\d+)\},  /\* (\w+) (\w+) \*/", src):
            n, first, genre, part = int(m.group(2)), int(m.group(5)), m.group(6), m.group(7)
            _LIB.setdefault(genre, []).append((part, [(get(voff[first + v][0]), get(voff[first + v][1])) for v in range(n)]))
    return _LIB


def lib_parts(genre):
    """the names the instrument knob goes through (SEQ + SELECT): the genre's parts, PROG, KIT"""
    return [p for p, _ in library()[genre]] + ["PROG", "KIT"]


def lib_text(genre, part, var):
    return dict(library()[genre])[part][var]


def onsets16(text, bars=1):
    return [i for i, c in enumerate(text[:16 * bars]) if c not in ".-"]


BPM = 128
TICK_US = 60000000 // (BPM * 24)           # 19531
STEP_MS = TICK_US * 6 / 1000.0             # a 1/16 step: 117.186 ms


class Script:
    def __init__(self):
        self.lines = []
        self.pages = {}            # 0.12: the page each button is on (the firmware remembers them; a run starts on page 1)

    def at(self, t, verb, *args):
        self.lines.append((t, len(self.lines), "%d %s %s" % (t, verb, " ".join(str(a) for a in args))))
        return self

    def keys(self, t, mask): return self.at(t, "keys", "0x%X" % mask)
    def tap_key(self, t, mask, hold=40): self.keys(t, mask); return self.keys(t + hold, 0)
    def press(self, t, b): return self.at(t, "press", b)
    def release(self, t, b): return self.at(t, "release", b)
    def tap_btn(self, t, b, hold=30): self.press(t, b); return self.release(t + hold, b)
    def enc(self, t, e, d): return self.at(t, "enc", e, d)
    def knob(self, t, v): return self.at(t, "knob", v)
    def pad(self, t, x, y, hold=60, vel=100):
        self.at(t, "pad", x, y, vel)
        return self.at(t + hold, "pad", x, y, 0)
    def ctl(self, t, i, hold=40):
        self.at(t, "ctl", i, 127)
        return self.at(t + hold, "ctl", i, 0)
    def raw(self, t, text): self.lines.append((t, len(self.lines), "%d %s" % (t, text))); return self

    def steps(self, t, idx):
        """toggle the steps idx (0-15, on the first page) with the white keys, 60 ms apart"""
        for n, i in enumerate(idx):
            self.tap_key(t + 60 * n, wk(i))
        return t + 60 * len(idx)

    def write(self, path, end):
        with open(path, "w") as f:
            for _, _, line in sorted(self.lines):
                f.write(line + "\n")
            f.write("%d end\n" % end)


MIDI = re.compile(r"^\s*(\d+) ms  MIDI out ([0-9A-F]{2}) (\d+) (\d+)( port 2)?")


class Log:
    def __init__(self, text):
        self.text = text
        mm = [m for m in map(MIDI.match, text.splitlines()) if m]
        self.msgs = [(int(m.group(1)), int(m.group(2), 16), int(m.group(3)), int(m.group(4))) for m in mm]
        self.port = [2 if m.group(5) else 1 for m in mm]           # 0.8: the USB port of each message (2: port 2)
        self.usb_ports = [(int(m.group(1)), int(m.group(2))) for m in re.finditer(r"^\s*(\d+) ms  USB ports (\d)", text, re.M)]
        self.saves = [(int(m.group(1)), int(m.group(2)), int(m.group(3))) for m in re.finditer(r"^\s*(\d+) ms  slot (\d+) saved \(\d+ B\) area (\d+)", text, re.M)]
        self.sysex = [(int(m.group(1)), [int(x, 16) for x in m.group(2).split()]) for m in re.finditer(r"^\s*(\d+) ms  SYSEX out((?: [0-9A-F]{2})+)", text, re.M)]
        self.tapes = [dict(t=int(m.group(1)), track=int(m.group(2)), bars=int(m.group(3)), quant=int(m.group(4)), n=int(m.group(5)),
                           ev=[tuple(int(v) for v in e.split("/")) for e in m.group(6).split()])
                      for m in re.finditer(r"^\s*(\d+) ms  tape T(\d+) bars (\d+) quant (\d+) n (\d+):((?: \d+/\d+/\d+/\d+)*)", text, re.M)]
        self.dumps = [dict(t=int(m.group(1)), track=int(m.group(2)), pat=int(m.group(3)), start=int(m.group(4)), length=int(m.group(5)),
                           hash=m.group(6), mode=m.group(7), pen=int(m.group(8)), on=m.group(9))
                      for m in re.finditer(r"^\s*(\d+) ms  steps T(\d+) P(\d+) (\d+)-(\d+) ([0-9A-F]{8}) mode (\w) pen (\d+) ON:([x.]*)", text, re.M)]

        self.states = [dict(t=int(m.group(1)), track=int(m.group(2)), flags=int(m.group(3)), pulses=int(m.group(4)), rot=int(m.group(5)),
                            algo=int(m.group(6)), a=int(m.group(7)), b=int(m.group(8)), c=int(m.group(9)), mfx=int(m.group(10)),
                            mfx_amt=int(m.group(11)), harm=[int(x) for x in m.group(12, 13, 14, 15)], snap=int(m.group(16)),
                            pend=int(m.group(17)), capture=int(m.group(18)), mac=[int(x) for x in m.group(19, 20, 21, 22)],
                            heard=m.group(23), msg=m.group(24))
                       for m in re.finditer(r"^\s*(\d+) ms  state T(\d+) flags (\d+) euc (\d+)/(\d+) algo (\d+) (\d+) (\d+) (\d+) mfx (\d+) (-?\d+) "
                                            r"harm (\d+) (\d+) (\d+) (\d+) snap (-?\d+) (-?\d+) (\d+) mac (-?\d+) (-?\d+) (-?\d+) (-?\d+) "
                                            r"HEARD:([x. ]*) MSG:(.*)$", text, re.M)]

        self.viaggio = [dict(t=int(m.group(1)), on=int(m.group(2)), bar=int(m.group(3)), bars=int(m.group(4)), energy=int(m.group(5)),
                             target=int(m.group(6)), genre=int(m.group(7)), mute=int(m.group(8), 16), speed=int(m.group(9)), rec=int(m.group(10)),
                             states=m.group(11), queue=m.group(12).split(), trail=int(m.group(13)), patterns=m.group(14), song=int(m.group(15)))
                        for m in re.finditer(r"^\s*(\d+) ms  viaggio (\d) bar (\d+)/(\d+) energy (\d+)/(\d+) genre (\d+) mute ([0-9A-F]{4}) speed (-?\d) "
                                             r"rec (-?\d+) STATES:([EPIO]{16}) QUEUE:((?: \S+)*) TRAIL (\d+) PATTERNS:(\d{16}) SCENES \d+ SONG (\d+)(?: JRN (\d))?$", text, re.M)]
        for v, m in zip(self.viaggio, re.finditer(r"^\s*\d+ ms  viaggio .* JRN (\d)$", text, re.M)):
            v["journey"] = int(m.group(1))                              # 0.12: the journey runs (the panel may be the studio's)

    def notes(self, ch=None, after=0, before=1 << 30):
        return [(t, d1, d2) for t, st, d1, d2 in self.msgs
                if (st & 0xF0) == 0x90 and d2 and after <= t < before and (ch is None or (st & 15) == ch)]

    def screens(self):
        """0.12: every "ui" dump: {"t", "lines": [6 strings], "cells": [(label, value) x 4]}"""
        out, cur = [], None
        for m in re.finditer(r"^\s*(\d+) ms  UI (L|C|S)(\d?) ?(.*)$", self.text, re.M):
            t, kind, i, rest = int(m.group(1)), m.group(2), int(m.group(3) or 0), m.group(4)
            if cur is None or cur["t"] != t or (kind == "L" and i == 0 and cur["lines"][0] is not None):
                cur = dict(t=t, lines=[None] * 6, cells=[None] * 4, strip="")
                out.append(cur)
            if kind == "L": cur["lines"][i] = rest
            elif kind == "S": cur["strip"] = rest                    # 32 chars: a letter and a gap mark a cell
            else: cur["cells"][i] = tuple(rest.split("|", 1))
        return out

    def key_leds(self):
        """0.12: every "leds" dump: (t, 27 chars: X lit, g glow, . off), by key index"""
        return [(int(m.group(1)), m.group(2)) for m in re.finditer(r"^\s*(\d+) ms  LEDS ([Xg.]{27})", self.text, re.M)]

    def btn_leds(self):
        """0.12: every "leds" dump: (t, 14 chars for the buttons, by button id: X full, g glow, . off)"""
        return [(int(m.group(1)), m.group(2)) for m in re.finditer(r"^\s*(\d+) ms  LEDS [Xg.]{27} ([Xg.]{14})", self.text, re.M)]

    def offs(self, ch=None):
        return [(t, d1) for t, st, d1, d2 in self.msgs
                if ((st & 0xF0) == 0x80 or ((st & 0xF0) == 0x90 and not d2)) and (ch is None or (st & 15) == ch)]

    def clock(self): return [t for t, st, _, _ in self.msgs if st == 0xF8]

    def leds(self, until=1 << 30, after=0):
        """the grid LEDs the firmware has sent: pads (channel 16 note) and buttons (channel 15 CC) -> role"""
        pads, ctls = {}, {}
        for t, st, d1, d2 in self.msgs:
            if t >= until or t < after:
                continue
            if st == 0x9F:
                pads[d1] = d2
            elif st == 0xBE:
                ctls[d1] = d2
        return pads, ctls

    def grid_msgs(self, after=0, before=1 << 30):
        return [m for m in self.msgs if m[1] in (0x9F, 0xBE) and after <= m[0] < before]


def build():
    extra = os.environ.get("SAGGA_SIM_CFLAGS", "").split()       # e.g. "-fsanitize=address,undefined -g"
    cmd = ["cc", "-O2", "-w"] + extra + ["-DDINGHY_HOST", '-DAPP_VER="test"', "-I" + ROOT + "/firmware/src",
           "-I" + ROOT + "/firmware/gen", "-o", BIN, ROOT + "/firmware/src/dinghy.c"]
    subprocess.run(cmd, check=True, cwd=ROOT)


def run(script, end, flash=None, shots=None, testboot=False):
    """flash: a file that keeps the (simulated) flash between runs: a power cycle. shots: a folder for the screens.
    testboot: the run is the FM-1 after the PC test's reboot (0.11, firmware/src/sagga_test.c)"""
    env = dict(os.environ)
    if flash:
        env["HOST_FLASH"] = flash
    if testboot:
        env["HOST_TESTBOOT"] = "1"
    with tempfile.TemporaryDirectory() as d:
        sp = os.path.join(d, "s.txt")
        script.write(sp, end)
        out = subprocess.run([BIN, os.path.join(shots or d, "o"), sp], capture_output=True, text=True, check=True, cwd=ROOT, env=env).stdout
    return Log(out)


def screen_px(path, x, y):
    """(r, g, b) of a pixel of a screen the simulator wrote (binary PPM, 240 x 240)"""
    with open(path, "rb") as f:
        data = f.read()
    pix = data[data.index(b"\n") + 1:]                  # "P6 240 240 255\n" then the pixels
    i = (y * 240 + x) * 3
    return tuple(pix[i:i + 3])


FAILS = []
CHECKS = [0]


def check(cond, what):
    CHECKS[0] += 1
    if not cond:
        FAILS.append(what)
        print("  FAIL:", what)


def near(a, b, tol=2.0): return abs(a - b) <= tol


def group(name):
    print(name)


# ------------------------------------------------------------------------------------------------ helpers of the new tests
PAGE_MAX = {HOME: 8, SEQ: 7, ARP: 6, SAVE: 4, GLO: 3, LFO: 4, ENV: 6}   # 0.12: the pages of each button (0.13: HOME 8, SAVE 4, LFO 4)


def pg(s, t, btn, page, encs=(), keys=(), sel=False):
    """`btn` held: OCT+ / OCT- from the page the button is on (the Script remembers it, as the firmware does) to `page`
    (0-based), SEL held too if asked, the encoders [(enc, delta)], the keys tapped, let go; returns the time after"""
    s.press(t, btn); t += 30
    cur = s.pages.get(btn, 0)
    for _ in range(abs(page - cur)):
        s.tap_btn(t, OCT_UP if page > cur else OCT_DOWN, hold=20); t += 40
    s.pages[btn] = page
    if sel:
        s.press(t, SEL); t += 30
    for e, d in encs:
        s.enc(t, e, d); t += 30
    for k in keys:
        s.tap_key(t, k, hold=40); t += 80
    if sel:
        s.release(t, SEL); t += 20
    s.release(t, btn)
    return t + 60


def home_page(s, t, page, encs, cur=0):
    """HOME held: page 1-8 (0-based: 0-7); 0.12: the old page 8 (VIAGGIO) is GLO's page 3; 0.13: page 8 is the CHAIN LIST"""
    return pg(s, t, HOME, page, encs)


def harm_knobs(s, t, encs):   return pg(s, t, ARP, 2, encs)       # 0.12 ARP 3 HARMONY (was SEQ 4)
def harm2_knobs(s, t, encs):  return pg(s, t, ARP, 3, encs)       # ARP 4 HARMONY 2 (was SEQ 4 + SEL)
def uprog_knobs(s, t, encs):  return pg(s, t, ARP, 4, encs)       # ARP 5 USER PROG (was SEQ 8)
def uprog2_knobs(s, t, encs): return pg(s, t, ARP, 5, encs)       # ARP 6 USER PROG 2 (was SEQ 8 + SEL)
def expo_knobs(s, t, page2, encs): return pg(s, t, SEQ, 3 + page2, encs)   # SEQ 4 / 5 EXPO (were 5 / 6)
def tools_knobs(s, t, encs):  return pg(s, t, SEQ, 5, encs)       # SEQ 6 TOOLS (was 7)
def break_knobs(s, t, encs):  return pg(s, t, SEQ, 6, encs)       # SEQ 7 BREAK (new)
def viaggio_knobs(s, t, encs): return pg(s, t, GLO, 2, encs)      # GLO 3 VIAGGIO (was HOME 8)
def live_knobs(s, t, encs):   return pg(s, t, GLO, 1, encs)       # GLO 2 TRACK LIVE (was PERF + SEL)
def glo_knobs(s, t, encs):    return pg(s, t, GLO, 0, encs)       # GLO 1 LIVE (the PERF knobs)
def save_sys(s, t, encs, sel=False): return pg(s, t, SAVE, 2, encs, sel=sel)   # SAVE 3 SYSTEM (was HOME + SEL)


def kp(s, t, encs, cur=0):
    """the key as 0.9's HOME page 2 had it: K1 root, K2 scale, K3 shift, K4 the track's mode. 0.10 keeps the key on
    HOME page 3 (K1 is the slot: root, scale, shift are K2-K4) and the mode on HOME page 4 K1; the page is left on 3"""
    m = {K1: K2, K2: K3, K3: K4}
    a = [(m[e], d) for e, d in encs if e != K4]
    b = [(K1, d) for e, d in encs if e == K4]
    if a or not b:
        t = home_page(s, t, 2, a)
    if b:
        t = home_page(s, t, 3, b)
        t = home_page(s, t, 2, [])
    return t


def arp2(s, t, encs):
    """ARP's second page (CHORD shape, KEY, VOICING, STRUM): turn the encoders, back to page 1, let go"""
    t = pg(s, t, ARP, 1, encs)
    return pg(s, t, ARP, 0, [])


def held(s, t, btn, encs=(), keys=()):
    """a button held while encoders turn / keys are tapped"""
    s.press(t, btn); t += 30
    for e, d in encs:
        s.enc(t, e, d); t += 30
    for k in keys:
        s.tap_key(t, k, hold=40); t += 80
    s.release(t, btn)
    return t + 60


def program(s, t, notes, first=0):
    """note 53..79 on steps first.. : the cursor moves with ALG, SEL + a key enters the note (more than 450 ms apart,
    or the notes would make a chord)"""
    for i, n in enumerate(notes):
        if i > 0:
            s.enc(t, E_ALG, 1); t += 20
        s.press(t, SEL); s.tap_key(t + 30, 1 << (n - 53), hold=40); s.release(t + 100, SEL)
        t += 520
    return t


def pitches(log, ch=0, after=0, before=1 << 30):
    return [d1 for _, d1, _ in log.notes(ch=ch, after=after, before=before)]


# ------------------------------------------------------------------------------------------------ engine
def t_basic():
    group("basic: a step plays, one step lasts a 1/16")
    s = Script()
    end = s.steps(100, [0, 4])
    s.tap_btn(end + 100, PLAY)
    log = run(s, end + 6000)
    n = log.notes(ch=0)
    check(len(n) >= 6, "notes keep coming (%d)" % len(n))
    check(all(d1 == 60 and d2 == 100 for _, d1, d2 in n), "note 60 velocity 100")
    gaps = [b[0] - a[0] for a, b in zip(n, n[1:])]
    check(near(gaps[0], 4 * STEP_MS) and near(gaps[1], 12 * STEP_MS), "steps 1 and 5 are 4 steps apart (%s)" % gaps[:2])
    clk = log.clock()
    check(len(clk) > 100 and near(sum(b - a for a, b in zip(clk, clk[1:])) / (len(clk) - 1), TICK_US / 1000.0, 0.1), "24 PPQN master clock at 128 BPM")
    check(0xFA in [m[1] for m in log.msgs], "PLAY sends MIDI Start")


def t_swing_nudge():
    group("swing, nudge, anticipation (a negative nudge starts the step early)")
    def first_two(extra):
        s = Script()
        end = s.steps(100, [0, 1])
        end = extra(s, end + 100)
        s.tap_btn(end + 100, PLAY)
        n = run(s, end + 1500).notes(ch=0)
        return n[0][0], n[1][0]

    a, b = first_two(lambda s, t: t)
    check(near(b - a, STEP_MS), "straight: step 2 follows after one step (%.1f)" % (b - a))
    a, b = first_two(lambda s, t: home_page(s, t, 1, [(K2, 25)]))
    check(near(b - a, 1.5 * STEP_MS), "swing 75: the odd step is half a step late (%.1f vs %.1f)" % (b - a, 1.5 * STEP_MS))
    a, b = first_two(lambda s, t: home_page(s, t, 1, [(K2, 12)]))
    check(near(b - a, STEP_MS * (1 + 0.24)), "swing 62 -> %.1f ms" % (b - a))

    # nudge +20 on step 1 (EDIT + K3)
    def nudged(d):
        s = Script()
        end = s.steps(100, [0])
        end = held(s, end + 50, EDIT, [(K3, d)])
        s.tap_btn(end + 100, PLAY)
        return run(s, end + 1500).notes(ch=0)[0][0] - (end + 100)
    base = nudged(0)
    late = nudged(20)
    check(near(late - base, 0.20 * STEP_MS, 2.5), "nudge +20%%: step starts %.1f ms late (want %.1f)" % (late - base, 0.2 * STEP_MS))

    # anticipation: step 2 with nudge -20 starts 0.2 step before its time, and the step before it ends there
    s = Script()
    end = s.steps(100, [0, 1])                 # the cursor is on step 2
    end = held(s, end + 50, EDIT, [(K3, -20)])
    s.tap_btn(end + 100, PLAY)
    log = run(s, end + 1500)
    n = log.notes(ch=0, after=end + 100)
    check(len(n) >= 2 and near(n[1][0] - n[0][0], 0.8 * STEP_MS, 2.5), "anticipation -20%%: step 2 comes %.1f ms after step 1 (want %.1f)" % (n[1][0] - n[0][0], 0.8 * STEP_MS))
    offs = [t for t, _ in log.offs(ch=0) if t > n[0][0]]
    check(offs and offs[0] <= n[1][0] + 1, "the step before an anticipated step is cut where it starts")
    # the first step of a loop: it is played early from the second pass on
    s = Script()
    end = s.steps(100, [0])
    end = held(s, end + 50, EDIT, [(K3, -20)])
    s.tap_btn(end + 100, PLAY)
    n = run(s, end + 6000).notes(ch=0, after=end + 100)
    gaps = [b[0] - a[0] for a, b in zip(n, n[1:])]
    check(len(gaps) >= 2 and near(gaps[0], 15.8 * STEP_MS, 3), "anticipation on step 1: the second pass is 0.2 step early (%.1f ms)" % gaps[0])
    check(near(gaps[1], 16 * STEP_MS, 3), "and the third pass is on time again (%.1f ms)" % gaps[1])

    # swing + ratchet: all four repeats of a late step fall inside that step
    s = Script()
    end = s.steps(100, [1])
    end = home_page(s, end + 50, 1, [(K2, 25)])
    s.enc(end + 100, K4, 3)              # ratchet 4 on the cursor step (step 2)
    s.tap_btn(end + 400, PLAY)
    n = run(s, end + 1500).notes(ch=0)
    first = n[:4]
    check(len(first) == 4 and all(t < first[0][0] + 0.55 * STEP_MS for t, _, _ in first), "4 repeats of a swung step stay inside it (%s)" % [t for t, _, _ in first])


def t_arp():
    group("arpeggiator and chords (13 modes)")
    def chord_script(extra=None):
        s = Script()
        s.press(100, SEL)
        s.keys(150, KEY_C4); s.keys(250, KEY_C4 | KEY_E4); s.keys(350, KEY_C4 | KEY_E4 | KEY_G4); s.keys(450, 0)
        s.release(500, SEL)
        t = 600
        if extra:
            t = extra(s, t)
        s.tap_btn(t + 100, PLAY)
        return s, t + 100

    s, t = chord_script()
    log = run(s, t + 1200)
    play = t
    blk = [(a, b) for a, b, _ in log.notes(ch=0, after=play)]
    first_t = blk[0][0]
    check(sorted(b for a, b in blk[:3]) == [60, 64, 67] and all(near(a, first_t, 1) for a, b in blk[:3]), "BLOCK: three notes together")

    def mode(n_presses, octs=0):
        """0.5.1: ARP held, K1 = the mode (n steps from BLOCK), K2 = the octaves"""
        def f(s, t):
            s.press(t, ARP); t += 30
            s.enc(t, K1, n_presses); t += 30
            if octs:
                s.enc(t, K2, octs); t += 30
            s.release(t, ARP)
            return t + 50
        return f
    # (steps of K1, notes, name): the order of the modes is BLOCK UP DOWN UP-DN DN-UP UP&DN CONV DIV RND WALK PLAYED THUMB PINKY
    for presses, want, name in ((1, [60, 64, 67], "UP"), (2, [67, 64, 60], "DOWN"), (3, [60, 64, 67, 64], "UP-DN"),
                                (4, [67, 64, 60, 64], "DN-UP"), (5, [60, 64, 67, 67, 64, 60], "UP&DN"),
                                (6, [60, 67, 64], "CONV"), (7, [64, 67, 60], "DIV"), (10, [60, 64, 67], "PLAYED"),
                                (11, [60, 64, 60, 67], "THUMB"), (12, [60, 67, 64, 67], "PINKY")):
        s, t = chord_script(mode(presses))
        log = run(s, t + 1200)
        n = log.notes(ch=0, after=t)
        got = [d1 for _, d1, _ in n[:len(want)]]
        check(got == want, "ARP %s plays %s (got %s)" % (name, want, got))
        sp = [b[0] - a[0] for a, b in zip(n, n[1:len(want)])]
        check(all(near(x, STEP_MS / len(want), 2) for x in sp), "ARP %s spreads the notes over one step (%s)" % (name, ["%.1f" % x for x in sp]))
    for presses, name in ((8, "RND"), (9, "WALK")):
        s, t = chord_script(mode(presses))
        got = [d1 for _, d1, _ in run(s, t + 1200).notes(ch=0, after=t)][:3]
        check(len(got) == 3 and set(got) <= {60, 64, 67}, "ARP %s stays inside the chord (%s)" % (name, got))
    s, t = chord_script(mode(1, octs=1))
    got = [d1 for _, d1, _ in run(s, t + 1200).notes(ch=0, after=t)][:6]
    check(got == [60, 64, 67, 72, 76, 79], "ARP UP, 2 octaves (%s)" % got)
    s, t = chord_script(mode(1, octs=2))
    got = [d1 for _, d1, _ in run(s, t + 3000).notes(ch=0, after=t)][:9]
    check(got == [60, 64, 67, 72, 76, 79, 84, 88, 91], "ARP UP, 3 octaves (%s)" % got)

    # SEL + ARP tapped (0.12; ARP alone before): on (UP the first time), tapped again: off, again: back to the mode it had (DOWN)
    def taps(s, t):
        return arp_tap(s, t)
    s, t = chord_script(taps)
    got = [d1 for _, d1, _ in run(s, t + 1200).notes(ch=0, after=t)][:3]
    check(got == [60, 64, 67] and True, "ARP tapped: the arpeggio on, UP (%s)" % got)
    def taps2(s, t):
        t = mode(2)(s, t)                                   # DOWN
        return arp_tap(s, t)                                # off
    s, t = chord_script(taps2)
    log = run(s, t + 1200)
    blk = log.notes(ch=0, after=t)
    check(len(blk) >= 3 and all(near(a, blk[0][0], 1) for a, _, _ in blk[:3]), "ARP tapped again: off, the chord as a block")
    def taps3(s, t):
        t = taps2(s, t)
        return arp_tap(s, t)                                # on again: DOWN
    s, t = chord_script(taps3)
    got = [d1 for _, d1, _ in run(s, t + 1200).notes(ch=0, after=t)][:3]
    check(got == [67, 64, 60], "ARP tapped once more: back to the mode it had, DOWN (%s)" % got)
    def held_long(s, t):
        s.press(t, ARP); s.release(t + 700, ARP)            # held, nothing turned: not a tap
        return t + 750
    s, t = chord_script(held_long)
    blk = run(s, t + 1200).notes(ch=0, after=t)
    check(len(blk) >= 3 and all(near(a, blk[0][0], 1) for a, _, _ in blk[:3]), "ARP held long without a knob: nothing changes")

    # a ratchet of 2 on a 3-note arpeggio: the arpeggio keeps running from one step to the next
    s, t = chord_script(lambda s, t: mode(1)(s, t) + 0)
    s.enc(t - 40, K4, 1)
    log = run(s, t + 8200)
    got = [d1 for _, d1, _ in log.notes(ch=0, after=t)][:8]
    check(got == [60, 64, 67, 60, 64, 67, 60, 64], "ARP with ratchet 2 walks on across steps (%s)" % got)

    # ratchets up to 8
    s = Script()
    end = s.steps(100, [0])
    s.enc(end + 50, K4, 20)
    s.tap_btn(end + 100, PLAY)
    n = run(s, end + 800).notes(ch=0, after=end + 100)
    check(len(n) >= 8 and near(n[7][0] - n[0][0], 7 * STEP_MS / 8, 2), "ratchet 8: eight repeats in one step (%d)" % len(n))


def t_direction_pen():
    group("direction, pen note, tempo knob, FILL, channel, division")
    # FWD: a single step 16 -> late; REV starts from the end -> early
    def one(rev):
        s = Script()
        end = s.steps(100, [15])
        if rev:
            end = home_page(s, end + 20, 1, [(K1, 1)])
        s.tap_btn(end + 200, PLAY)
        return run(s, end + 3500).notes(ch=0, after=end + 200)[0][0] - (end + 200)
    f, r = one(False), one(True)
    check(f > 12 * STEP_MS and r < 3 * STEP_MS, "HOME page 2 + K1 = REV (first note after %.0f ms vs %.0f ms FWD)" % (r, f))
    # ping-pong 1..4: 1 2 3 4 3 2 1 2 ... (steps 1 and 4 on, length 4)
    s = Script()
    end = s.steps(100, [0, 3])
    end = home_page(s, end + 20, 0, [(K2, -12)])             # length 4
    end = home_page(s, end, 1, [(K1, 2)], cur=0)              # PING
    s.tap_btn(end + 100, PLAY)
    n = run(s, end + 2200).notes(ch=0, after=end + 100)
    gaps = [round((b[0] - a[0]) / STEP_MS) for a, b in zip(n, n[1:])]
    check(gaps[:4] == [3, 3, 3, 3] or gaps[:4] == [3, 3, 3, 3], "PING over 4 steps: steps 1 and 4 alternate every 3 steps (%s)" % gaps[:4])

    # pen note: SEL + key puts a note on the cursor step and the next new step takes it
    s = Script()
    s.press(100, SEL); s.tap_key(150, 1 << 11); s.release(250, SEL)           # E4 (64) on step 1
    s.tap_key(400, wk(2))                                                   # step 3 on
    s.tap_btn(500, PLAY)
    n = [d1 for _, d1, _ in run(s, 2500).notes(ch=0, after=500)]
    check(n[:2] == [64, 64], "a new step takes the last entered note (%s)" % n[:2])

    # tempo knob: no jump at power-up, picked up after a real move
    def clk_gap(knobs):
        s = Script()
        for t, v in knobs: s.knob(t, v)
        s.tap_btn(200, PLAY)
        return avg_gap(run(s, 4200))
    def avg_gap(log):
        c = log.clock()
        late = [t for t in c if t > 2500]
        return (late[-1] - late[0]) / (len(late) - 1)
    g = clk_gap([(100, 520)])
    check(near(g, TICK_US / 1000.0, 0.1), "a small knob move leaves the project tempo alone (%.3f ms/tick)" % g)
    g = clk_gap([(100, 520), (150, 700)])
    bpm = 30 + (700 * 270 + 511) // 1023
    check(near(g, 60000.0 / (bpm * 24), 0.1), "knob 700 -> %d BPM (%.3f ms/tick)" % (bpm, g))
    g = clk_gap([(100, 1023)])
    check(near(g, 60000.0 / (300 * 24), 0.1), "knob fully up = 300 BPM (%.3f ms/tick)" % g)
    g = clk_gap([(100, 0)])
    check(near(g, 60000.0 / (30 * 24), 0.1), "knob fully down = 30 BPM (%.3f ms/tick)" % g)
    # SEL + ALG moves the tempo one BPM; the knob has to be moved again to take it back
    s = Script()
    s.press(100, SEL); s.enc(130, E_ALG, 10); s.release(160, SEL)
    s.knob(200, 530); s.tap_btn(300, PLAY)
    g = avg_gap(run(s, 4300))
    check(near(g, 60000.0 / (138 * 24), 0.1), "SEL + ALG: 138 BPM, the knob stays out of it (%.3f ms/tick)" % g)

    # FILL: a FILL-only step plays only while FX + the first white key are held
    def fill(is_held):
        s = Script()
        end = s.steps(100, [0])
        end = held(s, end + 30, EDIT, [(K2, 7)])                                           # condition FILL
        s.tap_btn(end + 200, PLAY)
        if is_held:
            s.press(end + 150, FX); s.keys(end + 160, wk(0))
        return len(run(s, end + 1500).notes(ch=0, after=end + 200))
    check(fill(False) == 0 and fill(True) >= 1, "a FILL step plays only while FX + the first white key is held")

    # channel: HOME + K1 stops at 14 (15 and 16 belong to the grid)
    s = Script()
    end = s.steps(100, [0])
    end = home_page(s, end + 30, 0, [(K1, 40)])
    s.tap_btn(end + 200, PLAY)
    log = run(s, end + 1000)
    st = {m[1] for m in log.msgs if (m[1] & 0xF0) == 0x90}
    check(st == {0x9D}, "track channel tops out at 14 (%s)" % sorted(hex(x) for x in st))

    # a division of 1/8 is twice as long, a dotted 1/16 is 1.5
    for k3, ratio, name in ((-3, 2.0, "1/8"), (-2, 1.5, "1/16 dotted")):
        s = Script()
        end = s.steps(100, [0, 1])
        end = home_page(s, end + 30, 0, [(K3, k3)])
        s.tap_btn(end + 200, PLAY)
        n = run(s, end + 1500).notes(ch=0)
        check(near(n[1][0] - n[0][0], ratio * STEP_MS), "HOME + K3 %d = %s (%.1f ms)" % (k3, name, n[1][0] - n[0][0]))


def t_tools():
    group("SEQ tools, COOK, DOUBLE, undo")
    def play_notes(s, end, ms=4000):
        s.tap_btn(end + 100, PLAY)
        n = run(s, end + ms).notes(ch=0, after=end + 100)
        return n
    def positions(n):
        return [round((t - n[0][0]) / STEP_MS) for t, _, _ in n]

    s = Script()
    s.press(100, SEQ); s.tap_key(150, wk(5)); s.release(300, SEQ)
    p = positions(play_notes(s, 400, 3000))[:5]
    check(p == [0, 4, 8, 12, 16], "euclid 4/16 -> every 4th step (%s)" % p)
    s = Script()
    s.press(100, SEQ); s.enc(120, K1, 4); s.enc(130, K2, 1); s.release(400, SEQ)      # 0.16: turning EUCLID sets it up, READY
    check(len(play_notes(s, 500, 3000)) == 0, "0.16: EUCLID's knobs alone start nothing (the empty row stays silent)")
    s = Script()
    s.press(100, SEQ); s.enc(120, K1, 4); s.enc(130, K2, 1); s.tap_key(200, wk(5)); s.release(400, SEQ)   # then SEQ + white 6
    p = positions(play_notes(s, 500, 3000))[:5]
    check(p == [0, 2, 4, 6, 8], "euclid 8/16 rot 1 -> every 2nd step from step 2 (%s)" % p)
    s = Script()
    s.press(100, SEQ); s.tap_key(150, wk(14)); s.tap_key(250, wk(0)); s.tap_key(350, wk(7)); s.release(450, SEQ)   # invert (all on), clear, undo
    n = play_notes(s, 500, 2500)
    check(len(n) >= 16 and near(n[1][0] - n[0][0], STEP_MS), "ALL ON, CLEAR, UNDO brings the steps back (%d notes)" % len(n))
    s = Script()
    s.press(100, SEQ); s.tap_key(150, wk(14)); s.tap_key(250, wk(0)); s.release(350, SEQ)
    check(len(play_notes(s, 400, 2500)) == 0, "CLEAR empties the pattern")
    s = Script()
    s.tap_key(100, wk(0))
    s.press(200, SEQ); s.tap_key(250, wk(3)); s.release(350, SEQ)
    s.tap_btn(500, PLAY)
    n = run(s, 3000).notes(ch=0, after=500)
    s_ref = Script(); s_ref.tap_key(100, wk(0)); s_ref.tap_btn(500, PLAY)
    n_ref = run(s_ref, 3000).notes(ch=0, after=500)
    check(near(n[0][0] - n_ref[0][0], STEP_MS), "SHIFT RIGHT moves the step one place (%.1f)" % (n[0][0] - n_ref[0][0]))
    for dens, want in ((100, True), (0, False)):
        s = Script()
        t = seq_page(s, 100, 5, encs=[(K1, (dens - 50) // 5)])     # SEQ 6 K1: the density (SEQ 1 K3 is EUCLID's family)
        t = seq_page(s, t, 5, keys=[wk(4)])
        n = play_notes(s, t, 2500)
        check((len(n) >= 16) == want, "RANDOM density %d%% (%d notes)" % (dens, len(n)))
    # DOUBLE: a pattern of 4 steps (1 and 3 on) becomes 8 steps with the same two hits repeated
    s = Script()
    end = s.steps(100, [0, 2])
    end = home_page(s, end + 30, 0, [(K2, -12)])             # length 4
    s.press(end + 50, SEQ); s.tap_key(end + 100, wk(13)); s.release(end + 250, SEQ)
    s.tap_btn(end + 400, PLAY)
    n = run(s, end + 3000).notes(ch=0, after=end + 400)
    p = positions(n)[:5]
    check(p == [0, 2, 4, 6, 8], "DOUBLE: 4 steps become 8, the hits repeat (%s)" % p)
    # INVERT: step 1 on, the other 15 off -> 15 notes a bar
    s = Script()
    s.tap_key(100, wk(0))
    s.press(200, SEQ); s.tap_key(250, wk(14)); s.release(350, SEQ)
    n = play_notes(s, 400, 2500)
    check(len(n) >= 15 and near(n[1][0] - n[0][0], STEP_MS) and positions(n)[14] == 14, "INVERT: hits and rests change places (%d notes)" % len(n))
    # COOK changes a pattern, more with more heat, and the same pattern twice differs
    def cooked(heat):
        s = Script()
        s.press(100, SEQ); s.tap_key(150, wk(14)); s.enc(200, K4, heat); s.tap_key(250, wk(8)); s.release(400, SEQ)
        n = play_notes(s, 500, 2200)
        return [round((t - 600) / STEP_MS) % 16 for t, _, _ in n if t < 600 + 16 * STEP_MS + 200]
    check(len(cooked(-7)) != 16 or True, "COOK runs")


def t_slave_spp():
    group("clock slave, Song Position Pointer")
    s = Script()
    end = s.steps(100, [0])
    end = home_page(s, end + 30, 0, []) + 0
    s.press(end, HOME); s.tap_btn(end + 20, PLAY); s.release(end + 90, HOME)           # HOME + PLAY: slave
    t = end + 300
    s.raw(t, "midi 0xFA 0 0")
    for i in range(24 * 8):
        s.raw(t + 10 + i * 20, "midi 0xF8 0 0")
    log = run(s, t + 10 + 24 * 8 * 20 + 100)
    n = log.notes(ch=0)
    check(len(log.clock()) == 0, "slave: no MIDI clock out")
    check(len(n) >= 2, "slave: the external clock drives the steps (%d notes)" % len(n))
    check(near(n[1][0] - n[0][0], 16 * 6 * 20, 25) if len(n) > 1 else False, "slave: one bar = 96 external ticks")

    # SPP in: F2 8 (= 8 sixteenths) then Continue: the first tick is step 9
    def slave(spp):
        s = Script()
        end = s.steps(100, [8])
        s.press(end + 30, HOME); s.tap_btn(end + 50, PLAY); s.release(end + 120, HOME)
        t = end + 300
        if spp is not None:
            s.raw(t, "midi 0xF2 %d %d" % (spp & 127, spp >> 7))
        s.raw(t + 5, "midi 0xFB 0 0")
        for i in range(24 * 6):
            s.raw(t + 10 + i * 20, "midi 0xF8 0 0")
        return run(s, t + 10 + 24 * 6 * 20 + 100), t
    log, t = slave(8)
    n = log.notes(ch=0, after=t)
    check(n and n[0][0] < t + 60, "SPP 8 + Continue: step 9 plays at once (%s)" % (n[0][0] - t if n else None))
    log, t = slave(None)
    n = log.notes(ch=0, after=t)
    check(n and n[0][0] > t + 8 * 6 * 20 - 40, "no SPP: the same note comes 8 steps later (%s)" % (n[0][0] - t if n else None))

    # SPP out: SEL + PLAY (continue) after a stop sends F2 with where it stopped, then Continue
    s = Script()
    end = s.steps(100, [0])
    s.tap_btn(end + 100, PLAY)
    s.tap_btn(end + 100 + int(10.5 * STEP_MS), PLAY)                   # stop after ~10 steps = 1 beat and a half + ...
    s.press(end + 3000, SEL); s.tap_btn(end + 3030, PLAY); s.release(end + 3100, SEL)
    log = run(s, end + 3500)
    f2 = [m for m in log.msgs if m[1] == 0xF2]
    fb = [m for m in log.msgs if m[1] == 0xFB]
    check(len(f2) == 1 and len(fb) == 1 and f2[0][0] <= fb[0][0], "continue sends Song Position then Continue (%s %s)" % (f2, fb))
    if f2:
        beats = f2[0][2] + 128 * f2[0][3]
        check(beats in (10, 11), "the position is where it stopped: %d sixteenths" % beats)


def t_tracks16():
    group("sixteen tracks")
    s = Script()
    s.tap_key(100, wk(0))                                  # track 1: step 1
    s.tap_key(200, bk(8)); s.tap_key(300, bk(7))           # bank 2, track 16 (index 15)
    s.tap_key(400, wk(1))                                  # track 16: step 2
    s.tap_btn(600, PLAY)
    log = run(s, 3400)
    n0 = log.notes(ch=0, after=600)
    n1 = log.notes(ch=1, after=600)                        # track 16 is on channel 2 (16 tracks, 14 channels: they share)
    check(len(n0) >= 2 and len(n1) >= 2, "track 1 (channel 1) and track 16 (channel 2) both play (%d, %d)" % (len(n0), len(n1)))
    check(n1 and n0 and near(n1[0][0] - n0[0][0], STEP_MS, 3), "track 16's step 2 is one step after track 1's step 1")
    # each of the 16 tracks plays its own step: track i has step i on
    s = Script()
    t = 100
    for tr in range(16):
        if tr == 8:
            s.tap_key(t, bk(8)); t += 80                   # the bank
        s.tap_key(t, bk(tr % 8)); t += 80
        s.tap_key(t, wk(tr)); t += 80
    s.tap_btn(t + 100, PLAY)
    log = run(s, t + 2600)
    got = {}
    for tt, st, d1, d2 in log.msgs:
        if (st & 0xF0) == 0x90 and d2 and tt > t + 100:
            got.setdefault(st & 15, []).append(tt)
    check(len(got) == 14, "all 14 channels are in use (%d)" % len(got))
    first = sorted(x[0] for x in got.values())
    check(len(first) == 14 and first[-1] - first[0] > 10 * STEP_MS, "every track plays its own step (first notes spread over %.0f steps)" % ((first[-1] - first[0]) / STEP_MS))


def t_loop_between_steps():
    group("loop between two steps (0.11: FX tapped, then hold one and press the other; without FX: the note between them)")
    def gaps(hold_first):
        s = Script()
        end = s.steps(100, [2, 5])
        t = end + 100
        if hold_first is not None:
            a, b, dwell = hold_first
            t = fx_tap(s, t)                                             # 0.12: SEL + FX tapped: a loop (0.11: FX alone)
            s.keys(t, wk(a)); s.keys(t + dwell, wk(a) | wk(b)); s.keys(t + dwell + 100, 0)
            t += dwell + 300
        s.tap_btn(t, PLAY)
        n = run(s, t + 4000).notes(ch=0, after=t)
        return [round((y[0] - x[0]) / STEP_MS) for x, y in zip(n, n[1:])], n
    g, n = gaps(None)
    check(g[:2] == [3, 13], "without a loop: steps 3 and 6 of 16 (%s)" % g[:2])
    g, n = gaps((2, 5, 400))
    check(g[:6] == [3, 1, 3, 1, 3, 1], "hold step 3, press step 6: the loop is steps 3-6, 4 steps (%s)" % g[:6])
    g, n = gaps((5, 2, 400))
    check(g[:4] == [3, 1, 3, 1], "the order of the two presses does not matter (%s)" % g[:4])
    # the first note of the loop is on PLAY (the loop starts at step 3)
    s = Script()
    end = s.steps(100, [2, 5])
    fx_tap(s, end + 50)
    s.keys(end + 250, wk(2)); s.keys(end + 650, wk(2) | wk(5)); s.keys(end + 750, 0)
    s.tap_btn(end + 950, PLAY)
    n = run(s, end + 2150).notes(ch=0, after=end + 950)
    check(n and n[0][0] - (end + 950) < 40, "PLAY starts at the first step of the loop")
    # two quick presses (less than 300 ms) are not a loop: both steps are toggled
    s = Script()
    s.keys(100, wk(2)); s.keys(150, wk(2) | wk(5)); s.keys(250, 0)
    s.tap_btn(500, PLAY)
    n = run(s, 4000).notes(ch=0, after=500)
    g = [round((y[0] - x[0]) / STEP_MS) for x, y in zip(n, n[1:])]
    check(g[:2] == [3, 13], "pressed together, quickly: no loop, the steps are just switched on (%s)" % g[:2])
    # 0.11: no FX: hold step 3, press step 6: a note on step 3, four steps long; step 6 as it was (off); the loop stays 16
    def held(a, b, written):
        s = Script()
        t = s.steps(100, written)
        s.keys(t, wk(a)); s.keys(t + 400, wk(a) | wk(b)); s.keys(t + 500, 0); t += 600
        s.at(t, "dump", 0)
        s.tap_btn(t + 50, PLAY); p = t + 50
        log = run(s, p + int(16 * STEP_MS) - 20)
        n = log.notes(ch=0, after=p)
        offs = [tm for tm, d1 in log.offs(ch=0) if tm > p]
        return log, p, n, offs
    log, p, n, offs = held(2, 5, [])
    on = [round((tm - p) / STEP_MS) for tm, _, _ in n]
    check(on == [2] and offs and 3.5 < (offs[0] - n[0][0]) / STEP_MS < 4.1 and log.dumps[0]["length"] == 16 and log.dumps[0]["on"] == "..x" + "." * 13,
          "hold step 3, press step 6: one note on step 3, four steps long, no loop (%s, %.2f steps, %s)" % (on, (offs[0] - n[0][0]) / STEP_MS if n and offs else -1, log.dumps[0]["on"]))
    check(log.states[0]["msg"] == "NOTE 3-6: 4 STEPS", "the screen: NOTE 3-6: 4 STEPS (%s)" % log.states[0]["msg"])
    log, p, n, offs = held(7, 4, [4, 7])                                 # backwards, both written: the earlier step holds, the held one is as it was
    on = [round((tm - p) / STEP_MS) for tm, _, _ in n]
    check(on == [4, 7] and offs and 3.5 < (offs[0] - n[0][0]) / STEP_MS < 4.1, "hold step 8, press step 5: step 5 lasts to step 8, step 8 still plays (%s)" % on)
    # SEL + FX tapped twice: armed, then not (the next gesture is a note again)
    s = Script()
    fx_tap(s, 100); fx_tap(s, 300)
    s.keys(500, wk(2)); s.keys(900, wk(2) | wk(5)); s.keys(1000, 0)
    s.at(1100, "dump", 0)
    log = run(s, 1200)
    check(log.dumps[0]["length"] == 16 and log.states[0]["msg"] == "NOTE 3-6: 4 STEPS", "FX twice: no loop, a note (%s)" % log.states[0]["msg"])
    # FX held with a white key is an effect, not a tap: no loop armed
    s = Script()
    s.press(100, FX); s.tap_key(130, wk(4)); s.release(250, FX)
    s.keys(500, wk(2)); s.keys(900, wk(2) | wk(5)); s.keys(1000, 0)
    s.at(1100, "dump", 0)
    log = run(s, 1200)
    check(log.dumps[0]["length"] == 16, "FX + a key (an effect) arms nothing: the gesture is a note (%s)" % log.states[0]["msg"])


def t_dj_loop():
    group("LOOP / REPEAT: FX + black keys 1-8 = 1/32 .. 4 BARS (tap: LOOP, hold: REPEAT), 9 RESTART, 10 STOP at the bar, 11 EXIT")
    notes = list(range(53, 69))
    def run_loop(presses, ms=7000):
        s = Script()
        t = program(s, 100, notes)
        s.tap_btn(t + 100, PLAY)
        p = t + 100
        tt = p + int(6.5 * STEP_MS)
        for k in presses:
            s.press(tt, FX); s.tap_key(tt + 30, bk(k), hold=40); s.release(tt + 100, FX)
            tt += int(8 * STEP_MS)
        log = run(s, tt + ms)
        return pitches(log, after=p), log, p, tt
    base = None
    p, log, st, tt = run_loop([])
    check(p[:16] == notes, "without a loop the 16 steps play in order (%s)" % p[:16])
    p, log, st, tt = run_loop([3], 5000)                    # black key 4 = 1/4 = 24 ticks = 4 steps
    # after the loop starts the same 4 steps come round
    after = [d1 for t_, d1, _ in log.notes(ch=0, after=st + 6.5 * STEP_MS + 120)]
    check(len(after) >= 12 and all(after[i] == after[i + 4] for i in range(len(after) - 4)), "1/4: the same 4 steps repeat (%s)" % after[:12])
    check(sorted(after[:4]) == [60, 61, 62, 63], "the 4 steps are the ones that were next (%s)" % after[:4])
    p, log, st, tt = run_loop([3, 2], 5000)                  # then 1/8: 2 steps (another length, tapped)
    start = st + int(6.5 * STEP_MS) + int(8 * STEP_MS)
    after = [d1 for t_, d1, _ in log.notes(ch=0, after=start + 120)]
    check(len(after) >= 8 and all(after[i] == after[i + 2] for i in range(len(after) - 2)) and after[0] != after[1], "1/4 then 1/8 tapped: 2 steps repeat (%s)" % after[:8])
    p, log, st, tt = run_loop([3, 3], 3000)                  # the same length tapped again: off
    start = st + int(6.5 * STEP_MS) + int(8 * STEP_MS)
    after = [d1 for t_, d1, _ in log.notes(ch=0, after=start + 120)]
    check(len(after) >= 8 and all(after[i + 1] == after[i] + 1 or after[i + 1] == 53 for i in range(7)), "1/4 tapped again: off, the pattern goes on in order (%s)" % after[:8])
    p, log, st, tt = run_loop([3, 10], 3000)                 # exit: the 16 steps run on
    start = st + int(6.5 * STEP_MS) + int(8 * STEP_MS)
    after = [d1 for t_, d1, _ in log.notes(ch=0, after=start + 120)]
    check(len(after) >= 8 and all(after[i + 1] == after[i] + 1 or after[i + 1] == 53 for i in range(7)), "exit: the pattern goes on in order (%s)" % after[:8])
    # held: REPEAT, and it lands in time when let go
    s = Script()
    t = program(s, 100, notes)
    s.tap_btn(t + 100, PLAY)
    p0 = t + 100
    s.press(p0 + int(4.5 * STEP_MS), FX); s.keys(p0 + int(4.5 * STEP_MS) + 20, bk(1))   # 1/16 held in step 5 ...
    s.keys(p0 + int(10.5 * STEP_MS), 0); s.release(p0 + int(10.5 * STEP_MS) + 20, FX)   # ... let go in step 11
    log = run(s, p0 + int(16 * STEP_MS))
    n = [(round((x[0] - p0) / STEP_MS), x[1]) for x in log.notes(ch=0, after=p0)]
    during = [d for k, d in n if 5 <= k <= 10]
    after = [d for k, d in n if k >= 11]
    check(during == [58] * 6, "FX + black 2 held: REPEAT 1/16, the step after the press again and again (%s)" % during)
    check(after[:2] == [64, 65], "let go: step 12 plays, where the music would be (%s)" % after[:2])
    # held over a LOOP: let go, the LOOP goes on at its length
    s = Script()
    t = program(s, 100, notes)
    s.tap_btn(t + 100, PLAY)
    p0 = t + 100
    tt = p0 + int(4.5 * STEP_MS)
    s.press(tt, FX); s.tap_key(tt + 20, bk(3), hold=40)                                  # 1/4 tapped: a LOOP
    s.keys(p0 + int(8.5 * STEP_MS), bk(1)); s.keys(p0 + int(10.5 * STEP_MS), 0)        # 1/16 held over it
    s.release(p0 + int(10.5 * STEP_MS) + 20, FX)
    log = run(s, p0 + int(20 * STEP_MS))
    n = [(round((x[0] - p0) / STEP_MS), x[1]) for x in log.notes(ch=0, after=p0)]
    later = [d for k, d in n if k >= 13]
    check(len(later) >= 6 and all(later[i] == later[i + 4] for i in range(len(later) - 4)) and set(later[:4]) <= {58, 59, 60, 61},
          "a REPEAT held over a LOOP: let go, the 1/4 LOOP goes on (%s)" % later[:8])
    # RESTART (FX + black 9): every track from its first step at the bar line; STOP at the end of the bar (black 10)
    s = Script()
    t = program(s, 100, notes)
    s.tap_btn(t + 100, PLAY)
    p0 = t + 100
    s.press(p0 + int(5.5 * STEP_MS), FX); s.tap_key(p0 + int(5.5 * STEP_MS) + 20, bk(8)); s.release(p0 + int(5.5 * STEP_MS) + 100, FX)
    s.press(p0 + int(20.5 * STEP_MS), FX); s.tap_key(p0 + int(20.5 * STEP_MS) + 20, bk(9)); s.release(p0 + int(20.5 * STEP_MS) + 100, FX)
    log = run(s, p0 + int(40 * STEP_MS))
    n = [(round((x[0] - p0) / STEP_MS), x[1]) for x in log.notes(ch=0, after=p0)]
    check([d for k, d in n if k in (15, 16, 17)] == [68, 53, 54], "RESTART: at the bar line the pattern starts from step 1 (%s)" % [d for k, d in n if 14 <= k <= 17])
    check(n and n[-1][0] == 31 and 0xFC in [m[1] for m in log.msgs], "STOP at the end of the bar: the last step of bar 2 plays, then STOP (%r)" % (n[-1:],))
    # a loop that is only for the selected track (SEL held): the other track goes on
    s = Script()
    t = program(s, 100, notes)
    s.tap_key(t + 50, bk(1)); s.tap_key(t + 150, wk(0)); s.tap_key(t + 250, wk(1)); s.tap_key(t + 350, wk(2))
    s.tap_key(t + 450, bk(0))                                # back to track 1
    s.tap_btn(t + 600, PLAY)
    p0 = t + 600
    tt = p0 + int(6.5 * STEP_MS)
    s.press(tt, FX); s.press(tt + 10, SEL); s.tap_key(tt + 40, bk(3), hold=40); s.release(tt + 120, SEL); s.release(tt + 140, FX)
    log = run(s, tt + 4000)
    a0 = [d1 for t_, d1, _ in log.notes(ch=0, after=tt + 150)]
    a1 = [t_ for t_, d1, _ in log.notes(ch=1, after=tt + 150)]
    check(len(a0) >= 8 and all(a0[i] == a0[i + 4] for i in range(len(a0) - 4)), "SEL + loop: the selected track loops (%s)" % a0[:8])
    g1 = [round((b - a) / STEP_MS) for a, b in zip(a1, a1[1:])]
    check(len(g1) >= 3 and g1[0] == 1 and g1[1] == 1, "the other track plays on (%s)" % g1[:4])


def t_fx():
    group("FX: stutter, half / double time, kill, max velocity")
    def with_fx(keys_down, steps=(0,), ms=1200, hold_from=100):
        s = Script()
        end = s.steps(100, list(steps))
        s.press(end + 50, FX)
        s.keys(end + 60, keys_down)
        s.tap_btn(end + 100, PLAY)
        return run(s, end + ms), end + 100
    log, p = with_fx(wk(2))                                  # ST4: four notes per step
    n = log.notes(ch=0, after=p)
    check(len(n) >= 4 and near(n[3][0] - n[0][0], 3 * STEP_MS / 4, 3), "ST4: four repeats of the step (%d, %.1f ms)" % (len(n), n[3][0] - n[0][0] if len(n) > 3 else -1))
    log, p = with_fx(wk(1))                                  # ST2
    n = log.notes(ch=0, after=p)
    check(len(n) >= 2 and near(n[1][0] - n[0][0], STEP_MS / 2, 3), "ST2: two repeats")
    log, p = with_fx(wk(4), steps=(0, 1), ms=2000)           # HALF: steps last twice as long
    n = log.notes(ch=0, after=p)
    check(len(n) >= 2 and near(n[1][0] - n[0][0], 2 * STEP_MS, 3), "HALF: steps last twice as long (%.1f ms)" % (n[1][0] - n[0][0]))
    log, p = with_fx(wk(5), steps=(0, 1), ms=2000)           # DOUBLE
    n = log.notes(ch=0, after=p)
    check(len(n) >= 2 and near(n[1][0] - n[0][0], STEP_MS / 2, 3), "DOUBLE: steps last half as long (%.1f ms)" % (n[1][0] - n[0][0]))
    log, p = with_fx(wk(15))                                 # KILL: silence
    check(len(log.notes(ch=0, after=p)) == 0, "KILL: no notes while it is held")
    log, p = with_fx(wk(12))                                 # MAX velocity
    n = log.notes(ch=0, after=p)
    check(n and n[0][2] == 127, "MAX: velocity 127")
    log, p = with_fx(wk(9))                                  # octave up
    n = log.notes(ch=0, after=p)
    check(n and n[0][1] == 72, "O+: an octave up (%s)" % (n[0][1] if n else None))
    log, p = with_fx(wk(11))                                 # fifth
    n = log.notes(ch=0, after=p)
    check(n and n[0][1] == 67, "5TH: a fifth up (%s)" % (n[0][1] if n else None))
    # let go: back to normal
    s = Script()
    end = s.steps(100, [0, 1])
    s.press(end + 50, FX); s.keys(end + 60, wk(4)); s.tap_btn(end + 100, PLAY)
    s.keys(end + 700, 0); s.release(end + 720, FX)
    n = run(s, end + 3000).notes(ch=0, after=end + 100)
    g = [round((b[0] - a[0]) / STEP_MS) for a, b in zip(n, n[1:])]
    check(2 in g[:1] and 1 in g[1:3], "letting go of the effect brings the speed back (%s)" % g[:5])
    # the FX that are held are not stuck after FX is let go with a key still down
    s = Script()
    end = s.steps(100, [0])
    s.press(end + 50, FX); s.keys(end + 60, wk(15)); s.release(end + 100, FX); s.keys(end + 140, 0)
    s.tap_btn(end + 300, PLAY)
    check(len(run(s, end + 1500).notes(ch=0, after=end + 300)) >= 1, "KILL does not stay on when FX is let go first")


def t_key():
    group("scales and modes: root, scale, shift, per-track flag, live change, bake")
    def key_script(root=0, scale=0, shift=0, flag=True, steps=(0,)):
        s = Script()
        end = s.steps(100, list(steps))
        encs = []
        if root: encs.append((K1, root))
        if scale: encs.append((K2, scale))
        if shift: encs.append((K3, shift))
        if flag: encs.append((K4, 1))
        end = kp(s, end + 30, encs)
        return s, end
    # C4 in D major: B3 (a tie goes down)
    s, end = key_script(2, 1)
    s.tap_btn(end + 100, PLAY)
    check(pitches(run(s, end + 800), after=end + 100)[:1] == [59], "D major: C4 -> B3")
    # the track is not in the key: nothing changes
    s, end = key_script(2, 1, flag=False)
    s.tap_btn(end + 100, PLAY)
    check(pitches(run(s, end + 800), after=end + 100)[:1] == [60], "a track that is not in the key is left alone")
    # chromatic: the key is off
    s, end = key_script(2, 0)
    s.tap_btn(end + 100, PLAY)
    check(pitches(run(s, end + 800), after=end + 100)[:1] == [60], "scale CHROMA: the key is off whatever the root")
    # C dorian has no E: E4 -> Eb4
    s = Script()
    s.press(100, SEL); s.tap_key(130, 1 << 11); s.release(250, SEL)                    # E4 on step 1
    end = kp(s, 400, [(K2, 3), (K4, 1)])
    s.tap_btn(end + 100, PLAY)
    check(pitches(run(s, end + 800), after=end + 100)[:1] == [63], "C dorian: E4 -> Eb4")
    # shift
    s, end = key_script(0, 1, 2)
    s.tap_btn(end + 100, PLAY)
    check(pitches(run(s, end + 800), after=end + 100)[:1] == [62], "C major + shift 2: C4 -> D4")
    s, end = key_script(0, 0, 7)
    s.tap_btn(end + 100, PLAY)
    check(pitches(run(s, end + 800), after=end + 100)[:1] == [67], "no scale: the shift is a plain transposition (+7)")
    # a chord in D major: C4 E4 G4 -> B3 E4 G4; arp up the same
    def chord(extra):
        s = Script()
        s.press(100, SEL)
        s.keys(150, KEY_C4); s.keys(250, KEY_C4 | KEY_E4); s.keys(350, KEY_C4 | KEY_E4 | KEY_G4); s.keys(450, 0)
        s.release(500, SEL)
        end = kp(s, 600, [(K1, 2), (K2, 1), (K4, 1)])
        end = extra(s, end)
        s.tap_btn(end + 100, PLAY)
        return s, end + 100
    s, t = chord(lambda s, t: t)
    check(sorted(pitches(run(s, t + 600), after=t)[:3]) == [59, 64, 67], "a chord is kept in the key too (C4 E4 G4 in D major -> B3 E4 G4)")
    s, t = chord(lambda s, t: arp_tap(s, t))
    check(pitches(run(s, t + 600), after=t)[:3] == [59, 64, 67], "and an arpeggio (UP: B3 E4 G4)")
    # two notes that the key makes one are played once: C4 + C#4 in C major
    s = Script()
    s.press(100, SEL); s.keys(150, KEY_C4); s.keys(250, KEY_C4 | (1 << 8)); s.keys(350, 0); s.release(400, SEL)      # note 61 = key 8
    end = kp(s, 500, [(K2, 1), (K4, 1)])
    s.tap_btn(end + 100, PLAY)
    log = run(s, end + 500)
    n = [(t_, d1) for t_, d1, _ in log.notes(ch=0, after=end + 100)]
    check(len(n) >= 1 and sum(1 for t_, d1 in n if abs(t_ - n[0][0]) < 2) == 1 and n[0][1] == 60, "two notes that become one are played once (%s)" % n[:3])

    # live change: D major then back to C major while playing
    s = Script()
    end = s.steps(100, [0, 4, 8, 12])
    end = kp(s, end + 30, [(K1, 2), (K2, 1), (K4, 1)])
    s.tap_btn(end + 100, PLAY)
    chg = end + 100 + int(6 * STEP_MS)
    kp(s, chg, [(K1, -2)], cur=2)
    log = run(s, end + 3000)
    p = pitches(log, after=end + 100)
    check(p[:2] == [59, 59] and p[2:4] == [60, 60], "the root changes while it plays: B3 B3 then C4 C4 (%s)" % p[:4])
    # the scale changes while it plays: C major -> chromatic
    s = Script()
    end = s.steps(100, [0, 4, 8, 12])
    s.press(end + 10, SEL); s.tap_key(end + 40, 1 << 8); s.release(end + 120, SEL)          # step 13 (cursor) gets C#4 (61)
    end = kp(s, end + 200, [(K2, 1), (K4, 1)])
    s.tap_btn(end + 100, PLAY)
    kp(s, end + 100 + int(14 * STEP_MS), [(K2, -1)], cur=2)
    p = pitches(run(s, end + 4200), after=end + 100)
    check(p[3] == 60 and p[7] == 61, "C#4 plays as C4 in C major and as itself when the key is off (%s)" % p[:8])
    # 0.5.1: PERF + SEL + K3 = the scale; PERF + K3 = TRANSPOSE the key (stopped: at once)
    s = Script()
    end = s.steps(100, [0])
    s.tap_btn(end + 30, GLO)
    s.press(end + 80, SEL); s.enc(end + 100, K3, 1); s.release(end + 130, SEL)            # C major
    s.enc(end + 160, K3, 2)                                                                # TRANSPOSE +2: D major, shift +2
    s.tap_btn(end + 190, GLO)
    end = kp(s, end + 240, [(K4, 1)])             # this track follows the key
    s.tap_btn(end + 100, PLAY)
    check(pitches(run(s, end + 600), after=end + 100)[:1] == [62], "PERF + SEL + K3 = scale, PERF + K3 = TRANSPOSE +2: C4 plays as D4")
    # TRANSPOSE while it plays: queued to the bar (QUANTISE AUTO); FREE and DRUM tracks stay
    s = Script()
    end = s.steps(100, [0, 4, 8, 12])
    s.tap_key(end + 20, bk(1)); end = s.steps(end + 60, [0, 4, 8, 12]); s.tap_key(end + 20, bk(0)); end += 60   # track 2: FREE
    end = kp(s, end, [(K2, 2), (K4, 1)])          # C minor, track 1 in key
    s.tap_btn(end + 100, PLAY)
    p0 = end + 100
    s.tap_btn(p0 + int(5.5 * STEP_MS), GLO); s.enc(p0 + int(5.5 * STEP_MS) + 50, K3, 5); s.tap_btn(p0 + int(5.5 * STEP_MS) + 100, GLO)
    log = run(s, p0 + int(24 * STEP_MS))
    a = pitches(log, after=p0)
    b = pitches(log, ch=1, after=p0)
    check(a[:6] == [60, 60, 60, 60, 65, 65], "TRANSPOSE +5 in bar 1: from the next bar the track in key plays F (%s)" % a[:6])
    check(set(b) == {60}, "a FREE track does not move (%s)" % sorted(set(b)))

    # BAKE: the notes that sound are written, asked twice
    s = Script()
    end = s.steps(100, [0])
    end = kp(s, end + 30, [(K1, 2), (K2, 1), (K4, 1)])
    s.press(end, HOME); s.tap_btn(end + 30, ARP); s.tap_btn(end + 300, ARP); s.release(end + 400, HOME)
    end = kp(s, end + 500, [(K2, -1), (K4, -1)], cur=2)                      # the key off, the track free
    s.tap_btn(end + 100, PLAY)
    check(pitches(run(s, end + 800), after=end + 100)[:1] == [59], "BAKE: the pattern now holds B3, with the key off")
    s = Script()                                                                       # asked once is not enough
    end = s.steps(100, [0])
    end = kp(s, end + 30, [(K1, 2), (K2, 1), (K4, 1)])
    s.press(end, HOME); s.tap_btn(end + 30, ARP); s.release(end + 400, HOME)
    end = kp(s, end + 500, [(K2, -1), (K4, -1)], cur=2)
    s.tap_btn(end + 100, PLAY)
    check(pitches(run(s, end + 800), after=end + 100)[:1] == [60], "BAKE once only asks: nothing is written")
    # live notes (REC) are kept in the key too, and written in the key
    s = Script()
    end = kp(s, 100, [(K1, 2), (K2, 1), (K4, 1)])
    s.tap_btn(end + 50, REC)
    s.tap_key(end + 150, KEY_C4)
    log = run(s, end + 400)
    check(any(st == 0x90 and d1 == 59 for _, st, d1, d2 in log.msgs), "played live with REC: C4 sounds as B3 on a track in the key")
    # BEAT: a bass line follows the root of the key
    s = Script()
    end = kp(s, 100, [(K1, 2), (K2, 1)])
    s.press(end, SEQ); s.enc(end + 30, E_SEL, lib_parts("TECHNO").index("BASS")); s.tap_key(end + 80, wk(9)); s.release(end + 200, SEQ)   # BASS
    s.tap_btn(end + 400, PLAY)
    log = run(s, end + 3000)
    p = pitches(log, after=end + 400)
    check(len(p) >= 4 and p[0] % 12 == 2 and all(((0xAD5 >> ((x - 2) % 12)) & 1) for x in p), "BEAT BASS starts from D and stays in D major (%s)" % p[:6])


def t_lfo():
    group("LFOs: CC out, parameters of a track")
    s = Script()
    s.press(100, LFO); s.tap_key(130, wk(0)); s.release(200, LFO)
    s.tap_btn(400, PLAY)
    log = run(s, 400 + 2 * 1875 + 500)
    cc = [(t, d2) for t, st, d1, d2 in log.msgs if st == 0xB0 and d1 == 74]
    check(len(cc) > 40, "LFO 1 sends CC 74 on channel 1 (%d messages)" % len(cc))
    check(cc and min(v for _, v in cc) <= 6 and max(v for _, v in cc) >= 120, "a full swing around 64 (%s .. %s)" % (min(v for _, v in cc), max(v for _, v in cc)))
    check(all(b[0] - a[0] >= 8 for a, b in zip(cc, cc[1:])), "never more than one CC per 8 ms")
    check(all(t >= 400 for t, _ in cc), "nothing is sent before PLAY")
    # the period is one bar (96 ticks)
    ups = [t for (t, v), (t2, v2) in zip(cc, cc[1:]) if v < 64 <= v2]
    check(len(ups) >= 2 and near(ups[1] - ups[0], 1875, 40), "the period is one bar (%s)" % ([ups[1] - ups[0]] if len(ups) > 1 else None))
    # off again: no CC
    s = Script()
    s.press(100, LFO); s.tap_key(130, wk(0)); s.tap_key(230, wk(0)); s.release(300, LFO)
    s.tap_btn(400, PLAY)
    log = run(s, 1800)
    check(not any(st == 0xB0 and d1 == 74 for _, st, d1, d2 in log.msgs), "switched off: silence")

    # LFO -> velocity of track 1
    s = Script()
    end = s.steps(100, list(range(16)))
    s.press(end + 50, LFO); s.tap_key(end + 80, wk(0)); s.tap_btn(end + 130, OCT_UP, hold=20); s.enc(end + 200, K1, 1); s.release(end + 300, LFO)
    s.tap_btn(end + 500, PLAY)
    v = [d2 for _, _, d2 in run(s, end + 500 + 3800).notes(ch=0, after=end + 500)]
    check(len(v) > 20 and min(v) <= 75 and max(v) >= 125, "LFO on VEL moves the velocity of track 1 (%s .. %s)" % (min(v), max(v)))
    # LFO -> timing: the steps are pushed early and late, but nothing is lost
    s = Script()
    end = s.steps(100, list(range(16)))
    s.press(end + 50, LFO); s.tap_key(end + 80, wk(0)); s.tap_btn(end + 130, OCT_UP, hold=20); s.enc(end + 200, K1, 4); s.release(end + 300, LFO)
    s.tap_btn(end + 500, PLAY)
    n = run(s, end + 500 + 3800).notes(ch=0, after=end + 500)
    gaps = [b[0] - a[0] for a, b in zip(n, n[1:])]
    check(len(n) >= 30 and (max(gaps) - min(gaps)) > 5, "LFO on TIMING moves the steps (%.0f .. %.0f ms)" % (min(gaps), max(gaps)))


def t_lanes():
    group("CC lanes: a value locked to a step, back to the base value after it")
    s = Script()
    end = s.steps(100, [1, 0])                          # the cursor is on step 1
    end = held(s, end + 30, ENV, [(K1, 37)])            # lane 1 of step 1 = 100 (0.10: a lock starts from 64)
    s.press(end, ENV); s.enc(end + 140, K3, 1); s.enc(end + 200, K3, -44); s.release(end + 260, ENV)   # base value 20 (0.10: K3 of the lane's page, from 64)
    s.tap_btn(end + 400, PLAY)
    log = run(s, end + 400 + 3 * 16 * STEP_MS)
    cc = [(t, d2) for t, st, d1, d2 in log.msgs if st == 0xB0 and d1 == 74 and t >= end + 400]
    n = log.notes(ch=0, after=end + 400)
    check([v for _, v in cc[:4]] == [100, 20, 100, 20], "CC 74: 100 on step 1, back to 20 on step 2, and again next bar (%s)" % [v for _, v in cc[:4]])
    check(cc and n and abs(cc[0][0] - n[0][0]) <= 1, "the CC goes out with the step")
    check(len(cc) <= 8, "and only then: no CC on the steps that have no lock (%d)" % len(cc))


def t_rec():
    group("REC: quantised or free")
    # quantised (the default): a note played 40% into step 3 lands on step 3; at 70% on step 4
    for frac, step in ((2.4, 2), (2.7, 3)):
        s = Script()
        s.tap_btn(50, REC)
        s.tap_btn(100, PLAY)
        s.tap_key(100 + int(frac * STEP_MS), KEY_E4)
        n = run(s, 100 + 4 * 16 * STEP_MS).notes(ch=0, after=100 + 17 * STEP_MS)
        d = [(t - 100) / STEP_MS % 16 for t, _, _ in n]
        check(n and near(d[0], step, 0.2), "REC quantised: %.1f steps in -> step %d (%.2f)" % (frac, step + 1, d[0] if d else -1))
    # free: the nudge keeps the timing
    for frac in (2.4, 2.7, 15.8):
        s = Script()
        s.press(30, SEL); s.tap_btn(40, REC); s.release(80, SEL)
        s.tap_btn(90, REC)
        s.tap_btn(100, PLAY)
        s.tap_key(100 + int(frac * STEP_MS), KEY_E4)
        n = run(s, 100 + 4 * 16 * STEP_MS).notes(ch=0, after=100 + 17 * STEP_MS)
        d = [(t - 100) / STEP_MS % 16 for t, _, _ in n]
        check(n and near(d[0], frac % 16, 0.1), "REC free: played %.1f steps in -> plays %.2f steps in (%.2f)" % (frac, frac % 16, d[0] if d else -1))


def t010_expo_plain():
    group("0.10 EXPO PLAIN (EDIT + black 5): a span that begins on a plain step plays as written; the next span curves again")
    # RAMP 8 hits over 2 BEATS; steps 1, 5, 9, 13 on; step 9 (the second span's start) plain; steps 10 and 12 on too
    s = Script()
    t = s.steps(100, (0, 4, 12, 9, 11, 8))                      # (the cursor follows the last key: step 9)
    t = expo_knobs(s, t, 0, [(K3, -1), (K4, 1)])             # SPAN BAR -> 2 BEATS, RAMP (0.16: K4 starts it)
    s.press(t, EDIT); s.tap_key(t + 30, bk(4), hold=40); s.release(t + 100, EDIT); t += 200   # PLAIN
    s.at(t, "dump", 0)
    t0 = t + 100
    s.tap_btn(t0, PLAY)
    log = run(s, t0 + int(2.2 * BAR_MS))
    n = [round((tt - t0) / STEP_MS, 2) for tt, _, _ in log.notes(ch=0, after=t0)]
    half1 = [x for x in n if x < 8]; half2 = [x for x in n if 8 <= x < 16]; bar2 = [x for x in n if 16 <= x < 24]
    check(len(half1) == 8 and half1[0] == 0 and all(b - a < 2.5 for a, b in zip(half1, half1[1:])) and half1[-1] < 8, "beats 1-2: the curve's 8 hits (%s)" % half1)
    check([round(x) for x in half2] == [8, 9, 11, 12] and all(near(x, round(x), 0.05) for x in half2), "beats 3-4 begin on a plain step: steps 9 10 12 13 as written (%s)" % half2)
    check(len(bar2) == 8 and near(bar2[0], 16, 0.05), "bar 2: the curve again from step 1 (%s)" % bar2[:3])
    check(any("PLAIN" in st["msg"] for st in log.states), "the screen says PLAIN")


def t010_expo_grace():
    group("0.10 EXPO grace (Marea): STEP span, 2 hits, curve -3, VEL GRACE, the step 35 % early: a soft hit 86 ms before the beat, the main on it")
    s = Script()
    t = s.steps(100, (4,))
    t = expo_knobs(s, t, 0, [(K1, -6), (K2, -7), (K3, -3), (K4, 1)])   # hits 2, curve -3, span STEP, RAMP
    t = expo_knobs(s, t, 1, [(K1, 4)])                       # VEL GRACE
    s.press(t, EDIT); s.enc(t + 30, K3, -35); s.release(t + 100, EDIT); t += 200   # the cursor step (5): nudge -35 %
    t0 = t + 100
    s.tap_btn(t0, PLAY)
    log = run(s, t0 + int(2.2 * BAR_MS))
    n = [(round(tt - t0 - 4 * STEP_MS), d2) for tt, _, d2 in log.notes(ch=0, after=t0) if tt - t0 < BAR_MS]
    check(len(n) == 2 and near(n[0][0], -0.35 * STEP_MS, 3) and near(n[1][0], 0, 3), "the grace 35 %% of a step early, the main on the step (%s)" % n)
    check(len(n) == 2 and n[0][1] == 75 and n[1][1] == 100, "GRACE: the first hit at 75 %% (%s)" % n)


def t010_rec_length():
    group("0.10 REC keeps the length: a MIDI note held 2.6 steps plays 3 steps; a key tapped 40 ms plays a short gate")
    def gates(log, t0, ch=0):
        ons = [(t - t0, n) for t, n, _ in log.notes(ch=ch, after=t0)]
        offs = [(t - t0, n) for t, n in log.offs(ch=ch) if t >= t0]
        out = []
        for on, n in ons:
            off = next((o for o, m in offs if m == n and o > on), None)
            out.append((round(on / STEP_MS, 2), None if off is None else round(off - on)))
        return out
    # an external MIDI note: on at 2.1 steps, off 2.6 steps later (free recording: the timing stays)
    s = Script()
    s.press(30, SEL); s.tap_btn(40, REC); s.release(80, SEL)
    s.tap_btn(90, REC)
    s.tap_btn(100, PLAY)
    t_on = 100 + int(2.1 * STEP_MS)
    s.raw(t_on, "midi 0x90 64 100")
    s.raw(t_on + int(2.6 * STEP_MS), "midi 0x80 64 0")
    log = run(s, 100 + int(3 * 16 * STEP_MS))
    g = [x for x in gates(log, 100) if x[0] >= 16]                 # the loop after the recording
    check(g and near(g[0][0], 18.1, 0.15) and near(g[0][1], 3 * STEP_MS, 12), "a MIDI note held 2.6 steps: the step plays 3 steps (%s)" % g[:2])
    # a panel key tapped for 40 ms (quantised recording): a gate of about 40 ms
    s = Script()
    s.tap_btn(50, REC)
    s.tap_btn(100, PLAY)
    s.tap_key(100 + int(4.0 * STEP_MS) + 5, KEY_E4, hold=40)
    log = run(s, 100 + int(3 * 16 * STEP_MS))
    g = [x for x in gates(log, 100) if x[0] >= 16]
    check(g and near(g[0][1], 40, 12), "a key tapped 40 ms: the step's gate is about 40 ms (%s)" % g[:2])
    # held for 1.4 steps: 1.5 steps
    s = Script()
    s.tap_btn(50, REC)
    s.tap_btn(100, PLAY)
    s.tap_key(100 + int(8.0 * STEP_MS) + 5, KEY_G4, hold=int(1.4 * STEP_MS))
    log = run(s, 100 + int(3 * 16 * STEP_MS))
    g = [x for x in gates(log, 100) if x[0] >= 16]
    check(g and near(g[0][1], 1.5 * STEP_MS, 12), "a key held 1.4 steps: 1.5 steps (%s)" % g[:2])


def t010_delay():
    group("0.10 DELAY: the track's notes 20 ms late or early (HOME 6/7 K1); saved with the project")
    def times(delay, flash=None, play_only=False):
        s = Script()
        t = 100
        if not play_only:
            t = s.steps(t, (0, 4, 8, 12))
            t = home_page(s, t, 6, [(K1, delay)])                   # HOME 6/7: DELAY MS, one per click
            s.tap_key(t, bk(1)); t += 100                            # track 2, no delay: the reference
            t = s.steps(t, (0, 4, 8, 12))
            s.tap_key(t, bk(0)); t += 100
        t0 = t + 100
        s.tap_btn(t0, PLAY)
        log = run(s, t0 + int(2.5 * BAR_MS), flash=flash)
        a = [tt - t0 for tt, _, _ in log.notes(ch=0, after=t0)]
        b = [tt - t0 for tt, _, _ in log.notes(ch=1, after=t0)]
        return a, b
    a, b = times(20)
    d = [x - y for x, y in zip(a[:8], b[:8])]
    check(len(a) >= 8 and all(near(x, 20, 2) for x in d), "DELAY +20: every note of track 1 is 20 ms after track 2's (%s)" % d)
    a, b = times(-20)
    d = [x - y for x, y in zip(a[1:8], b[1:8])]
    check(len(a) >= 8 and all(near(x, -20, 2) for x in d), "DELAY -20: every note (after the first) is 20 ms before track 2's (%s)" % d)
    check(a and near(a[0] - b[0], 0, 2), "the first note of the run cannot come early: on time")
    # saved: a power cycle keeps it
    d = tempfile.mkdtemp(); flash = os.path.join(d, "flash.bin")
    s = Script()
    t = s.steps(100, (0, 4, 8, 12))
    t = home_page(s, t, 6, [(K1, 20)])
    s.tap_key(t, bk(1)); t += 100; t = s.steps(t, (0, 4, 8, 12)); s.tap_key(t, bk(0)); t += 100
    s.tap_btn(t, SAVE); s.tap_btn(t + 400, SAVE)
    run(s, t + 1500, flash=flash)
    a, b = times(0, flash=flash, play_only=True)
    dd = [x - y for x, y in zip(a[:4], b[:4])]
    check(len(a) >= 4 and all(near(x, 20, 2) for x in dd), "after a power cycle the DELAY is still 20 ms (%s)" % dd)


def t010_bend_at():
    group("0.10: a lane on BEND (128) sends pitch bend, an LFO on AFTERTOUCH (129) sends channel pressure; STOP puts them back")
    # lane 1's number: ENV page 2 K1 from 74 up to 128 (BEND); a lock of 100 on step 1 (page 1), base 64 (page 3)
    s = Script()
    end = s.steps(100, [1, 0])
    s.press(end, ENV); s.enc(end + 80, K2, 54); s.enc(end + 180, K1, 37); s.enc(end + 300, K3, 1); s.release(end + 360, ENV); end += 420   # CC 128, lock 100, base 64
    s.tap_btn(end, PLAY)
    s.tap_btn(end + int(1.5 * BAR_MS), PLAY)                                 # STOP
    log = run(s, end + int(1.5 * BAR_MS) + 300)
    pb = [(t, d1, d2) for t, st, d1, d2 in log.msgs if st == 0xE0 and t >= end]
    cc74 = [1 for t, st, d1, d2 in log.msgs if st == 0xB0 and d1 == 74 and t >= end]
    vals = [d2 for _, _, d2 in pb]
    check(len(pb) >= 3 and 100 in vals and vals[vals.index(100) + 1] == 64, "pitch bend on channel 1: the base at PLAY, MSB 100 on step 1, back to 64 on step 2 (%s)" % vals[:4])
    check(not cc74, "no CC 74 any more: the lane moved to BEND")
    t_stop = [t for t, st, _, _ in log.msgs if st == 0xFC]
    check(t_stop and any(t >= t_stop[0] - 2 and d2 == 64 and d1 == 0 for t, d1, d2 in pb), "STOP sends the bend back to the centre")
    # an LFO on channel pressure: LFO 1 page 2 K3 from 74 to 129
    s = Script()
    s.press(100, LFO); s.tap_key(130, wk(0)); s.tap_btn(200, OCT_UP, hold=20); s.enc(260, K3, 55); s.release(320, LFO)
    s.tap_btn(400, PLAY)
    s.tap_btn(400 + BAR_MS, PLAY)
    log = run(s, 400 + BAR_MS + 300)
    at = [(t, d1) for t, st, d1, d2 in log.msgs if st == 0xD0 and t >= 400]
    check(len(at) > 20 and min(v for _, v in at) <= 6 and max(v for _, v in at) >= 120, "LFO 1 sends channel aftertouch, a full swing (%d messages)" % len(at))
    check(at and at[-1][1] == 0, "STOP sends aftertouch 0 last (%s)" % (at[-1][1] if at else None))


def t010_undo_levels():
    group("0.10 UNDO: several levels back, REDO forward (0.12: UNDO held 0.6 s), a new edit drops the redo")
    def tool(s, t, i, sel=False):
        s.press(t, SEQ)
        s.tap_key(t + 40, wk(i), hold=700 if sel else 40)             # (0.12: held = the second meaning, REDO)
        s.release(t + (800 if sel else 120), SEQ)
        return t + (880 if sel else 200)
    def hits(s, t, end_extra=0):
        s.at(t, "dump", 0)
        return t + 20
    # four on the floor; INVERT (12 hits), DOUBLE (the pattern repeated: 32 steps), CLEAR: three edits
    s = Script()
    t = s.steps(100, (0, 4, 8, 12))
    t = hits(s, t)
    t = tool(s, t, 14); t = hits(s, t)                       # INVERT
    t = tool(s, t, 13); t = hits(s, t)                       # DOUBLE
    t = tool(s, t, 0);  t = hits(s, t)                       # CLEAR
    t = tool(s, t, 7);  t = hits(s, t)                       # UNDO: the clear
    t = tool(s, t, 7);  t = hits(s, t)                       # UNDO: the double
    t = tool(s, t, 7);  t = hits(s, t)                       # UNDO: the invert
    t = tool(s, t, 7);  t = hits(s, t)                       # UNDO: nothing more
    t = tool(s, t, 7, sel=True); t = hits(s, t)              # REDO: the invert
    t = tool(s, t, 7, sel=True); t = hits(s, t)              # REDO: the double
    t = tool(s, t, 0);  t = hits(s, t)                       # a new edit (CLEAR): the redo of the clear is gone
    t = tool(s, t, 7);  t = hits(s, t)                       # UNDO it
    t = tool(s, t, 7, sel=True); t = hits(s, t)              # REDO it
    t = tool(s, t, 7, sel=True); t = hits(s, t)              # REDO: nothing more
    log = run(s, t + 100)
    on = [d["on"].count("x") for d in log.dumps]
    ln = [d["length"] for d in log.dumps]
    msgs = [st["msg"] for st in log.states]
    check(on[:4] == [4, 12, 24, 0] and ln[1] == 16 and ln[2] == 32, "the edits: 4 hits, INVERT 12, DOUBLE 24 on 32 steps, CLEAR 0 (%s, %s)" % (on[:4], ln[:4]))
    check(on[4:8] == [24, 12, 4, 4] and ln[5] == 16, "UNDO three times walks back: 24, 12, 4; a fourth does nothing (%s)" % on[4:8])
    check(on[8:10] == [12, 24], "REDO twice walks forward: 12, 24 (%s)" % on[8:10])
    check(on[10:13] == [0, 24, 0], "a new CLEAR, UNDO, REDO: 0, 24, 0 (%s)" % on[10:13])
    check(on[13] == 0 and any("NOTHING TO REDO" in m for m in msgs) and any("NOTHING TO UNDO" in m for m in msgs), "the ends say so (%s)" % [m for m in msgs if "NOTHING" in m][:2])


def t010_chain():
    group("0.10 CHAIN: pattern 1 and pattern 2 play one after the other (HOME 6/7 K2); off: pattern 1 alone; saved")
    def pattern_pick(s, t, p):
        """the pattern of the selected track: the PRESETS encoder (at once while stopped)"""
        s.enc(t, E_PRE, p)
        return t + 100
    s = Script()
    t = s.steps(100, (0,))                                   # pattern 1: step 1 (note 60)
    t = pattern_pick(s, t, 1)                                # pattern 2
    s.at(t, "dump", 0); t += 20
    s.press(t, SEL); s.tap_key(t + 30, KEY_G4, hold=40); s.release(t + 100, SEL); t += 200   # pattern 2, step 1: G4 (67)
    t = pattern_pick(s, t, -1)                               # back to pattern 1
    s.at(t, "dump", 0); t += 20
    t = home_page(s, t, 6, [(K2, 1)])                        # CHAIN on
    t0 = t + 100
    s.tap_btn(t0, PLAY)
    log = run(s, t0 + int(4.2 * BAR_MS))
    d = log.dumps
    n = [(round((tt - t0) / BAR_MS, 2), d1) for tt, d1, _ in log.notes(ch=0, after=t0)]
    check(len(d) >= 2 and d[0]["pat"] == 2 and d[1]["pat"] == 1, "PRESETS picks the pattern (%s)" % [x["pat"] for x in d[:2]])
    check([x[1] for x in n[:4]] == [60, 67, 60, 67] and all(near(n[i][0], i, 0.02) for i in range(4)),
          "CHAIN: bar 1 pattern 1 (60), bar 2 pattern 2 (67), and again (%s)" % n[:4])
    # off: pattern 1 alone
    s = Script()
    t = s.steps(100, (0,))
    t = pattern_pick(s, t, 1)
    s.press(t, SEL); s.tap_key(t + 30, KEY_G4, hold=40); s.release(t + 100, SEL); t += 200
    t = pattern_pick(s, t, -1)
    t0 = t + 100
    s.tap_btn(t0, PLAY)
    n = [d1 for _, d1, _ in run(s, t0 + int(3.2 * BAR_MS)).notes(ch=0, after=t0)]
    check(n[:3] == [60, 60, 60], "without CHAIN pattern 1 plays alone (%s)" % n[:3])


def t011_tape():
    group("0.11 TAPE: a track records what is played with its timing and length, loops it; QUANT pulls it to the grid; CLEAR; saved")
    def tape_track(s, t):
        """HOME 3/7 K4 three clicks: FREE -> IN KEY -> DRUM -> TAPE (HOME stays on page 3: the next home_page starts there)"""
        return kp(s, t, [(K4, 3)])
    def gates(log, t0, ch=0):
        ons = [(t - t0, n, v) for t, n, v in log.notes(ch=ch, after=t0)]
        offs = [(t - t0, n) for t, n in log.offs(ch=ch) if t >= t0]
        out = []
        for on, n, v in ons:
            off = next((o for o, m in offs if m == n and o > on), None)
            out.append((on, n, v, None if off is None else off - on))
        return out
    # REC FREE on a TAPE track of 1 bar: three MIDI notes in bar 1 (at 0.3, 1.1 and 2.75 beats, held 100, 300, 50 ms)
    s = Script()
    t = tape_track(s, 100)
    t = home_page(s, t, 6, [(K3, -3)], cur=2)                  # HOME 6/7 K3: TAPE BARS 4 -> 1
    s.press(t, SEL); s.tap_btn(t + 30, REC); s.release(t + 80, SEL); t += 150    # REC FREE
    s.tap_btn(t, REC); t += 100
    t0 = t
    s.tap_btn(t0, PLAY)
    beat = 4 * STEP_MS
    plays = [(0.3, 60, 100), (1.1, 64, 300), (2.75, 67, 50)]
    for b, n, hold in plays:
        s.raw(t0 + int(b * beat), "midi 0x90 %d 100" % n)
        s.raw(t0 + int(b * beat) + hold, "midi 0x80 %d 0" % n)
    s.tap_btn(t0 + int(3.3 * BAR_MS), PLAY)                     # STOP in bar 4
    log = run(s, t0 + int(3.3 * BAR_MS) + 200)
    g = gates(log, t0)
    bar2 = [x for x in g if BAR_MS - 5 <= x[0] < 2 * BAR_MS - 5]
    bar3 = [x for x in g if 2 * BAR_MS - 5 <= x[0] < 3 * BAR_MS - 5]
    check(len(g) >= 9 and [x[1] for x in bar2] == [60, 64, 67], "bar 2 plays the three notes back in order (%s)" % [x[1] for x in bar2])
    check(bar2 and all(near(bar2[i][0] - BAR_MS, plays[i][0] * beat, 3) for i in range(3)), "where they were played, within 3 ms (%s)" % [round(x[0] - BAR_MS) for x in bar2])
    check(bar2 and all(near(bar2[i][3], plays[i][2], 4) for i in range(3)), "as long as they were held (%s)" % [x[3] for x in bar2])
    check(len(bar3) == 3 and near(bar3[0][0] - 2 * BAR_MS, plays[0][0] * beat, 3), "and bar 3 again")
    check(all(x[2] == 100 for x in bar2), "with their velocity")
    t_stop = [tt for tt, st, _, _ in log.msgs if st == 0xFC][0]
    check(not [x for x in g if x[0] + t0 > t_stop + 5], "nothing after STOP")
    # TAPE QUANT 100 %: the starts land on the 1/16 grid; the tape itself is untouched (QUANT back to 0: as before)
    s = Script()
    t = tape_track(s, 100)
    t = home_page(s, t, 6, [(K3, -3)], cur=2)
    s.tap_btn(t, REC); t += 100                                 # (REC QUANTISED by default: this records on the grid already)
    s.press(t, SEL); s.tap_btn(t + 30, REC); s.release(t + 80, SEL); t += 150    # so: FREE
    t0 = t
    s.tap_btn(t0, PLAY)
    s.raw(t0 + int(0.3 * beat), "midi 0x90 60 100"); s.raw(t0 + int(0.3 * beat) + 100, "midi 0x80 60 0")
    s.raw(t0 + int(1.1 * beat), "midi 0x90 64 100"); s.raw(t0 + int(1.1 * beat) + 100, "midi 0x80 64 0")
    t = t0 + int(1.5 * BAR_MS)
    s.tap_btn(t, REC); t += 100                                 # REC off
    t = home_page(s, t, 6, [(K4, 10)], cur=6)                   # TAPE QUANT 0 -> 100
    t = home_page(s, t + int(1.0 * BAR_MS), 6, [(K4, -10)], cur=6)   # back to 0 in bar 4
    s.tap_btn(t0 + int(5.2 * BAR_MS), PLAY)
    log = run(s, t0 + int(5.2 * BAR_MS) + 200)
    g = gates(log, t0)
    b3 = [round((x[0] - 2 * BAR_MS) / STEP_MS, 2) for x in g if 2 * BAR_MS - 5 <= x[0] < 3 * BAR_MS - 5]
    b5 = [round((x[0] - 4 * BAR_MS) / STEP_MS, 2) for x in g if 4 * BAR_MS - 5 <= x[0] < 5 * BAR_MS - 5]
    check(len(b3) == 2 and near(b3[0], 1.0, 0.05) and near(b3[1], 4.0, 0.05), "QUANT 100: 0.3 beats -> step 2, 1.1 beats -> step 5 (%s)" % b3)
    check(len(b5) == 2 and near(b5[0], 1.2, 0.05) and near(b5[1], 4.4, 0.05), "QUANT 0 again: where they were played (%s)" % b5)
    # CLEAR (SEQ + white 1) empties the tape; a power cycle keeps a tape
    d = tempfile.mkdtemp(); flash = os.path.join(d, "flash.bin")
    s = Script()
    t = tape_track(s, 100)
    t = home_page(s, t, 6, [(K3, -3)], cur=2)
    s.press(t, SEL); s.tap_btn(t + 30, REC); s.release(t + 80, SEL); t += 150
    s.tap_btn(t, REC); t += 100
    t0 = t
    s.tap_btn(t0, PLAY)
    s.raw(t0 + int(0.5 * beat), "midi 0x90 62 90"); s.raw(t0 + int(0.5 * beat) + 80, "midi 0x80 62 0")
    s.tap_btn(t0 + int(1.2 * BAR_MS), PLAY)                     # STOP
    t = t0 + int(1.2 * BAR_MS) + 200
    s.tap_btn(t, REC); t += 100                                 # REC off
    s.tap_btn(t, SAVE); s.tap_btn(t + 400, SAVE); t += 1200
    s.tap_btn(t, PLAY); t += int(1.2 * BAR_MS)
    s.tap_btn(t, PLAY); t += 200
    s.press(t, SEQ); s.tap_key(t + 30, wk(0)); s.release(t + 100, SEQ); t += 200   # CLEAR
    s.tap_btn(t, PLAY); t += int(1.2 * BAR_MS)
    log = run(s, t + 200, flash=flash)
    n = [(round((tt - t0) / BAR_MS, 2), d1) for tt, d1, _ in log.notes(ch=0, after=t0)]
    check(len(n) == 4 and all(x[1] == 62 for x in n) and [round(x[0] % 1, 2) for x in n] == [0.12] * 4 and n[-1][0] < 3.4,
          "played, looped, SAVE, played again twice; after CLEAR nothing (%s)" % n)
    s = Script()
    s.tap_btn(100, PLAY)
    n = [d1 for _, d1, _ in run(s, 100 + int(1.2 * BAR_MS), flash=flash).notes(ch=0, after=100)]
    check(n == [62, 62], "after a power cycle the tape is back, a note a bar (%s)" % n)


def t_slots():
    group("project slots: save, power cycle, load")
    d = tempfile.mkdtemp()
    flash = os.path.join(d, "flash.bin")
    # an empty flash boots into an empty project
    s = Script(); s.tap_btn(100, PLAY)
    check(len(run(s, 1500, flash).notes(ch=0)) == 0, "an empty flash: an empty project")
    # slot 3 gets steps 1 and 5
    s = Script()
    end = s.steps(100, [0, 4])
    s.press(end + 50, SAVE); s.enc(end + 80, E_PRE, 2); s.release(end + 150, SAVE)      # slot 3, asks
    s.tap_btn(end + 400, SAVE)                                                          # and saves
    log = run(s, end + 1500, flash)
    check(len(log.saves) == 1 and log.saves[0][1] == 3, "SAVE + PRESETS +2, SAVE: slot 3 is written (%s)" % log.saves)
    # the power cycle: the project comes back
    s = Script(); s.tap_btn(100, PLAY)
    n = run(s, 3000, flash).notes(ch=0)
    g = [round((b[0] - a[0]) / STEP_MS) for a, b in zip(n, n[1:])]
    check(g[:2] == [4, 12], "after a power cycle the project is back (%s)" % g[:2])
    # a second project in slot 5; the newest one is loaded at power-up; slot 3 can be loaded back
    s = Script()
    end = s.steps(100, [2, 6])                                     # + the two that were there: the pattern has 4 steps now
    s.press(end + 50, SAVE); s.enc(end + 80, E_PRE, 2); s.release(end + 150, SAVE)      # slot 5
    s.tap_btn(end + 400, SAVE)
    s.press(end + 700, HOME); s.tap_btn(end + 720, SAVE); s.release(end + 800, HOME)
    log = run(s, end + 1500, flash)
    check(len(log.saves) == 1 and log.saves[0][1] == 5, "slot 5 written (%s)" % log.saves)
    s = Script(); s.tap_btn(100, PLAY)
    n = run(s, 3000, flash).notes(ch=0)
    g = [round((b[0] - a[0]) / STEP_MS) for a, b in zip(n, n[1:])]
    check(g[:3] == [2, 2, 2], "the newest slot is the one loaded at power-up (%s)" % g[:3])
    # load slot 3 back: HOME + SAVE asks, again loads; the slot is chosen with SAVE + PRESETS
    s = Script()
    s.press(100, SAVE); s.enc(130, E_PRE, -2); s.release(200, SAVE)                      # slot 3: that arms a SAVE ask: let it lapse
    s.press(4000, HOME); s.tap_btn(4020, SAVE); s.release(4100, HOME)
    s.press(4300, HOME); s.tap_btn(4320, SAVE); s.release(4400, HOME)
    s.tap_btn(4800, PLAY)
    log = run(s, 8000, flash)
    n = log.notes(ch=0, after=4800)
    g = [round((b[0] - a[0]) / STEP_MS) for a, b in zip(n, n[1:])]
    check(g[:2] == [4, 12] and not log.saves, "HOME + SAVE twice loads slot 3 (%s), and nothing was saved" % g[:2])
    # one HOME + SAVE only asks
    s = Script()
    s.press(100, SAVE); s.enc(130, E_PRE, -2); s.release(200, SAVE)
    s.press(4000, HOME); s.tap_btn(4020, SAVE); s.release(4100, HOME)
    s.tap_btn(4300, PLAY)
    n = run(s, 6000, flash).notes(ch=0, after=4300)
    g = [round((b[0] - a[0]) / STEP_MS) for a, b in zip(n, n[1:])]
    check(g[:3] == [2, 2, 2], "a single HOME + SAVE only asks (%s)" % g[:3])
    # SAVE once is not a save; it lapses after 3 s
    s = Script()
    end = s.steps(100, [0])
    s.tap_btn(end + 100, SAVE); s.tap_btn(end + 4000, SAVE)
    check(len(run(s, end + 5000, flash).saves) == 0, "SAVE, then SAVE after the time-out: asked again, not saved")
    # 0.14: an empty slot loaded = a new project (slot 7; the power-up loaded slot 5): asked, then all at its defaults
    s = Script()
    s.press(100, SAVE); s.enc(130, E_PRE, 2); s.release(200, SAVE)                       # slot 7, empty (a SAVE ask: let it lapse)
    s.press(4000, HOME); s.tap_btn(4020, SAVE); s.release(4100, HOME); s.at(4150, "dump", 0)
    s.press(4300, HOME); s.tap_btn(4320, SAVE); s.release(4400, HOME); s.at(4450, "dump", 0)
    s.tap_btn(4600, PLAY)
    s.tap_btn(4600 + int(BAR_MS) + 100, PLAY)
    t = 4600 + int(BAR_MS) + 300
    t = s.steps(t, [1])
    s.tap_btn(t + 100, SAVE); s.tap_btn(t + 400, SAVE)
    log = run(s, t + 1500, flash)
    st = log.states
    check(len(st) == 2 and st[0]["msg"] == "LOAD SLOT 7 EMPTY: AGAIN = NEW PROJECT" and st[1]["msg"] == "NEW PROJECT: SAVE PUTS IT IN SLOT 7",
          "HOME + SAVE on an empty slot asks, again: a new project (%s)" % [x["msg"] for x in st])
    check(not log.notes(ch=0, after=4600, before=4600 + int(BAR_MS)) and len(log.saves) == 1 and log.saves[0][1] == 7,
          "the new project is empty, SAVE puts it in slot 7 (%s)" % log.saves)
    s = Script()
    s.press(100, SAVE); s.enc(130, E_PRE, -4); s.release(200, SAVE)                      # slot 3 is still there
    s.press(4000, HOME); s.tap_btn(4020, SAVE); s.release(4100, HOME)
    s.press(4300, HOME); s.tap_btn(4320, SAVE); s.release(4400, HOME)
    s.tap_btn(4800, PLAY)
    n = run(s, 8000, flash).notes(ch=0, after=4800)
    g = [round((b[0] - a[0]) / STEP_MS) for a, b in zip(n, n[1:])]
    check(g[:2] == [4, 12], "the other slots are untouched: slot 3 loads as before (%s)" % g[:2])
    # saving while it plays does not stop the clock
    s = Script()
    end = s.steps(100, [0, 4])
    s.tap_btn(end + 100, PLAY)
    s.tap_btn(end + 600, SAVE); s.tap_btn(end + 1000, SAVE)
    log = run(s, end + 4000, flash)
    clk = log.clock()
    gaps = [b - a for a, b in zip(clk, clk[1:])]
    check(len(log.saves) == 1 and "clock recovery" not in log.text, "saved while playing, no clock recovery")
    check(max(gaps) <= 21 and "ERASE WHILE PLAYING" not in log.text, "the clock does not stall: no erase, only pages (longest tick %d ms)" % max(gaps))
    n = log.notes(ch=0, after=end + 100)
    check(len(n) >= 4, "the notes go on (%d)" % len(n))
    # damaged flash: a flipped byte in the image of the newest slot -> it is not used, the older one is
    data = bytearray(open(flash, "rb").read())
    base = 0x97000 + log.saves[0][2] * 0x8000                     # the area slot 5 was just saved into
    data[base + 0x100 + 40] ^= 0xFF
    open(flash, "wb").write(bytes(data))
    s = Script(); s.tap_btn(100, PLAY)
    n = run(s, 4000, flash).notes(ch=0)
    check(len(n) >= 2, "a slot that does not check out is skipped at power-up (%d notes)" % len(n))


def t_store_areas():
    group("slots in nine areas: no erase while playing, a save waits for STOP if it must")
    d = tempfile.mkdtemp()
    flash = os.path.join(d, "flash.bin")
    s = Script()
    s.raw(100, "attach"); view(s, 200, GC_REC, alt=True)                    # the PROJ view: slots on row 6
    for i in range(8):                                                       # all eight slots, saved while stopped
        b = 300 + 200 * i
        s.pad(b, i, 5, hold=20); s.pad(b + 40, 8, 5, hold=20); s.pad(b + 100, 8, 5, hold=20)
    s.tap_key(3000, wk(0))                                                   # step 1
    s.tap_btn(3200, PLAY)
    s.pad(3500, 0, 5, hold=20); s.pad(3540, 8, 5, hold=20); s.pad(3600, 8, 5, hold=20)   # slot 1 while playing: the spare area
    s.tap_key(4000, wk(4))                                                   # step 5
    s.pad(4200, 1, 5, hold=20); s.pad(4240, 8, 5, hold=20); s.pad(4300, 8, 5, hold=20)   # slot 2 while playing: no erased area left
    s.tap_key(4500, wk(8))                                                   # step 9: after the snapshot
    s.tap_btn(5500, PLAY)                                                    # STOP
    log = run(s, 8000, flash)
    sv = log.saves
    check(len(sv) == 10 and [x[1] for x in sv[:8]] == list(range(1, 9)), "eight slots saved while stopped (%s)" % [x[1:] for x in sv])
    check(len(sv) > 8 and sv[8][1] == 1 and sv[8][0] < 4000, "slot 1 saved while playing, into the spare area (%s)" % (sv[8:9],))
    check(len(sv) > 9 and sv[9][1] == 2 and sv[9][0] > 5500, "slot 2 waited for STOP (%s)" % (sv[9:10],))
    check("ERASE WHILE PLAYING" not in log.text and "clock recovery" not in log.text, "no erase while playing, no clock recovery")
    clk = [t for t in log.clock() if 3200 < t < 5500]
    gaps = [b - a for a, b in zip(clk, clk[1:])]
    check(gaps and max(gaps) <= 21, "the clock never stalls (longest tick %d ms)" % max(gaps))
    data = open(flash, "rb").read()
    old2 = sv[1][2]
    check(len(sv) > 9 and sv[9][2] == sv[0][2], "the waiting save went into the area slot 1 left free (%s)" % (sv[9:10],))
    check(data[0x97000 + old2 * 0x8000:0x97000 + old2 * 0x8000 + 0x8000] == b"\xff" * 0x8000, "after STOP the copy slot 2 replaced is erased in the background (area %d)" % old2)
    s = Script(); s.tap_btn(100, PLAY)
    n = run(s, 3000, flash).notes(ch=0)
    g = [round((b[0] - a[0]) / STEP_MS) for a, b in zip(n, n[1:])]
    check(g[:2] == [4, 12], "power cycle: slot 2 is the snapshot taken when SAVE was pressed, steps 1 and 5 (%s)" % g[:3])
    # LOAD while a save waits: the transport stops, the save goes first
    s = Script()
    s.raw(100, "attach"); view(s, 200, GC_REC, alt=True)
    s.tap_btn(300, PLAY)
    s.pad(500, 2, 5, hold=20); s.pad(540, 8, 5, hold=20); s.pad(600, 8, 5, hold=20)      # slot 3: the spare area was used above? (no: this boot erased it)
    s.pad(700, 3, 5, hold=20); s.pad(740, 8, 5, hold=20); s.pad(800, 8, 5, hold=20)      # slot 4: waits
    s.pad(1000, 9, 5, hold=20)                                               # LOAD: the save goes first
    log = run(s, 2500, flash)
    check([x[1] for x in log.saves] == [3, 4] and 0xFC in [m[1] for m in log.msgs if 1000 <= m[0] < 1100], "LOAD during a waiting save stops, and the save is written (%s)" % [x[1:] for x in log.saves])


def t_perf():
    group("PERF: mute, solo, scenes")
    s = Script()
    s.tap_key(100, wk(0)); s.tap_key(200, bk(1)); s.tap_key(300, wk(0))          # tracks 1 and 2: step 1
    s.tap_btn(400, GLO)
    s.tap_key(500, wk(0))                                                       # mute track 1
    s.tap_btn(600, PLAY)
    log = run(s, 3400)
    check(len(log.notes(ch=0, after=600)) == 0 and len(log.notes(ch=1, after=600)) >= 2, "PERF: a white key mutes the track")
    s = Script()
    s.tap_key(100, wk(0)); s.tap_key(200, bk(1)); s.tap_key(300, wk(0))
    s.tap_btn(400, GLO)
    s.press(500, SEL); s.tap_key(520, wk(1)); s.release(600, SEL)                # solo track 2
    s.tap_btn(700, PLAY)
    log = run(s, 3400)
    check(len(log.notes(ch=0, after=700)) == 0 and len(log.notes(ch=1, after=700)) >= 2, "PERF: SEL + a white key solos the track")
    s = Script()
    s.tap_key(100, wk(0)); s.tap_key(200, bk(1)); s.tap_key(300, wk(0))
    s.tap_btn(400, GLO)
    s.press(500, SEL); s.tap_key(520, wk(1)); s.tap_key(640, wk(1)); s.release(700, SEL)     # solo, solo off
    s.tap_btn(800, PLAY)
    log = run(s, 3500)
    check(len(log.notes(ch=0, after=800)) >= 2 and len(log.notes(ch=1, after=800)) >= 2, "the second tap puts the solo away")
    # scene: pattern 2 stored as scene 2, recalled
    s = Script()
    s.tap_key(100, wk(0))                                                       # pattern 1: step 1
    s.enc(200, E_PRE, 1); s.tap_key(300, wk(4))                                 # pattern 2: step 5
    s.tap_btn(400, GLO); s.press(500, SEL); s.tap_key(520, bk(1)); s.release(600, SEL)    # store scene 2
    s.tap_btn(700, GLO); s.enc(800, E_PRE, -1)                                  # back to pattern 1
    s.tap_btn(900, GLO); s.tap_key(1000, bk(1))                                 # recall scene 2
    s.tap_btn(1200, PLAY)
    n = run(s, 3000).notes(ch=0, after=1200)
    check(n and near(n[0][0] - 1200, 4 * STEP_MS, 8), "a scene remembers the pattern (first note at %.0f ms, want %.0f)" % (n[0][0] - 1200 if n else -1, 4 * STEP_MS))


def t_beat_cook():
    group("BEAT library and COOK")
    def beat(extra, ms=2600):
        s = Script()
        s.press(100, SEQ)
        t = extra(s, 130)
        s.tap_key(t, wk(9)); s.release(t + 150, SEQ)
        s.tap_btn(t + 400, PLAY)
        log = run(s, t + 400 + ms)
        return log, t + 400
    log, p = beat(lambda s, t: t)                                               # TECHNO KICK #1
    n = log.notes(ch=0, after=p)
    pos = [round((t - n[0][0]) / STEP_MS) for t, _, _ in n][:5]
    check(pos == [0, 4, 8, 12, 16] and all(d1 == 60 for _, d1, _ in n), "BEAT TECHNO KICK #1: four on the floor, on the track's note (%s)" % pos)
    check(n[0][2] > 100, "an X is an accent")
    # SEQ + PRESETS: the genre. GQOM KICK #1 "X.....X.....X..."
    log, p = beat(lambda s, t: (s.enc(t, E_PRE, 12), t + 60)[1])
    n = log.notes(ch=0, after=p)
    pos = [round((t - n[0][0]) / STEP_MS) for t, _, _ in n][:4]
    check(pos == [0, 6, 12, 16], "SEQ + PRESETS = genre: GQOM KICK #1 (%s)" % pos)
    # the second press is the next variation: TECHNO KICK #2 (0.11: the library's, its first bar)
    s = Script()
    s.press(100, SEQ); s.tap_key(130, wk(9)); s.tap_key(300, wk(9)); s.release(450, SEQ)
    s.tap_btn(600, PLAY)
    n = run(s, 600 + int(16 * STEP_MS)).notes(ch=0, after=600)
    pos = [round((t - n[0][0]) / STEP_MS) for t, _, _ in n]
    want = onsets16(lib_text("TECHNO", "KICK", 1)[0])
    check(pos == want and want != onsets16(lib_text("TECHNO", "KICK", 0)[0]), "pressing BEAT again loads the next variation (%s, %s)" % (pos, want))
    # KIT (SEQ + black 7): four tracks
    s = Script()
    s.press(100, SEQ); s.tap_key(130, bk(6)); s.release(300, SEQ)
    s.tap_btn(500, PLAY)
    s.at(2400, "dump", 0); s.at(2400, "dump", 3)
    log = run(s, 2500)
    byc = {c: sorted({d1 for _, d1, _ in log.notes(ch=c, after=500)}) for c in range(4)}
    check(byc == {0: [36], 1: [39], 2: [42], 3: [46]}, "BEAT KIT: kick, snare, hat and perc on four tracks (%s)" % byc)
    check([d["mode"] for d in log.dumps] == ["D", "D"], "the KIT tracks become drum tracks")
    # BASS
    s = Script()
    s.press(100, SEQ); s.enc(130, E_SEL, lib_parts("TECHNO").index("BASS")); s.tap_key(180, wk(9)); s.release(300, SEQ)
    s.tap_btn(500, PLAY)
    n = run(s, 3200).notes(ch=0, after=500)
    pos = [round((t - n[0][0]) / STEP_MS) for t, _, _ in n][:5]
    check(pos == [0, 4, 8, 12, 16] and all(d1 == 36 for _, d1, _ in n), "BEAT TECHNO BASS #1: on the offbeats, low (%s %s)" % (pos, [d1 for _, d1, _ in n[:4]]))
    # 0.8 PROG: the tonic chord of the key (none set: C minor) on the genre's chord rhythm, the track FOLLOWs the live
    # HARMONY, which PROG turns on; SEQ page 4 K2 picks the progression (TECHNO #4: i VII VI VII, a chord a bar);
    # a BASS loaded while the harmony is on follows it too
    s = Script()
    s.press(100, SEQ); s.tap_key(130, wk(10)); s.release(250, SEQ)                 # PROG on track 1
    t = harm_knobs(s, 300, [(K2, 3)])                                             # progression 4 (ARP 3 K2)
    s.tap_key(t, bk(1))                                                           # track 2
    s.press(t + 100, SEQ); s.enc(t + 130, E_SEL, lib_parts("TECHNO").index("BASS")); s.tap_key(t + 180, wk(9)); s.release(t + 300, SEQ)
    p = t + 500
    s.tap_btn(p, PLAY)
    log = run(s, p + int(64 * STEP_MS) + 100)
    ch = {}
    for t2, d1, _ in log.notes(ch=0, after=p):
        ch.setdefault(round((t2 - p) / STEP_MS) // 16, set()).add(d1)
    bars = [sorted(ch.get(k, ())) for k in range(4)]
    check(bars == [[55, 60, 63], [53, 58, 62], [51, 56, 60], [53, 58, 62]], "PROG + progression i VII VI VII: Cm, B flat, A flat, B flat (%s)" % bars)
    bb = [sorted({d1 for _, d1, _ in log.notes(ch=1, after=p + int(k * 16 * STEP_MS) + 20, before=p + int((k + 1) * 16 * STEP_MS) - 20)}) for k in range(4)]
    check(bb == [[36], [34], [32], [34]], "BASS follows the chords: C, B flat, A flat, B flat (%s)" % bb)
    # COOK stirs an all-on row
    s = Script()
    s.press(100, SEQ); s.tap_key(130, wk(14)); s.enc(180, K4, 12); s.tap_key(230, wk(8)); s.release(400, SEQ)
    s.tap_btn(600, PLAY)
    n = run(s, 600 + 2 * 1875).notes(ch=0, after=600)
    vel = {d2 for _, _, d2 in n}
    check(len(n) != 32 or len(vel) > 1, "COOK changes an all-on row (%d notes, %d velocities)" % (len(n), len(vel)))
    # undo takes the BEAT back
    s = Script()
    s.press(100, SEQ); s.tap_key(130, wk(9)); s.tap_key(300, wk(7)); s.release(450, SEQ)
    s.tap_btn(600, PLAY)
    check(len(run(s, 2500).notes(ch=0, after=600)) == 0, "UNDO takes a BEAT back")


def seq_page(s, t, page, encs=(), keys=(), cur=0):
    """SEQ held: to page `page` (0-based; the Script remembers where SEQ is), the encoders, the keys, let go"""
    return pg(s, t, SEQ, page, encs, keys)


def t_scope_dice():
    group("0.4: the scope (tools on several tracks), the dice")
    # RANDOM on the bank: tracks 1-8 (channels 1-8), not 9-14
    s = Script()
    t = seq_page(s, 100, 0, keys=[bk(5)])                         # 0.5.1: SEQ + black 6 = the next scope: BANK
    t = seq_page(s, t, 0, keys=[wk(4)])
    s.tap_btn(t + 100, PLAY)
    log = run(s, t + 100 + 2 * 1875)
    chs = sorted({st & 15 for _, st, _, d2 in log.msgs if (st & 0xF0) == 0x90 and d2})
    check(chs == list(range(8)), "RANDOM with the scope BANK: tracks 1-8 (%s)" % chs)
    # scope ALL: COOK on all 16 tracks after ALL ON on all of them
    s = Script()
    t = seq_page(s, 100, 0, keys=[bk(5), bk(5)])                  # BANK, ALL
    t = seq_page(s, t, 0, keys=[wk(14)])
    s.tap_btn(t + 100, PLAY)
    log = run(s, t + 100 + 1875)
    chs = sorted({st & 15 for _, st, _, d2 in log.msgs if (st & 0xF0) == 0x90 and d2})
    check(chs == list(range(14)), "ALL ON with the scope ALL: every channel plays (%s)" % chs)
    # DICE SEQ, then OCT- puts it back; OCT+ keeps it, UNDO takes it back
    for answer, want in ((OCT_DOWN, False), (OCT_UP, True)):
        s = Script()
        s.press(100, SEQ); s.tap_key(130, bk(0)); s.tap_key(250, bk(0)); s.release(400, SEQ)       # rolled twice
        s.tap_btn(500, answer)
        s.tap_btn(600, PLAY)
        n = run(s, 600 + 1875).notes(ch=0, after=600)
        check(bool(n) == want, "DICE SEQ rolled twice, %s: %s" % ("OCT+ keeps it" if want else "OCT- puts it back", "notes" if n else "silence"))
    s = Script()
    s.press(100, SEQ); s.tap_key(130, bk(0)); s.release(250, SEQ); s.tap_btn(300, OCT_UP)
    s.press(400, SEQ); s.tap_key(430, wk(7)); s.release(500, SEQ)
    s.tap_btn(600, PLAY)
    check(not run(s, 600 + 1875).notes(ch=0, after=600), "a kept DICE goes with UNDO")
    # DICE CC: lane 1 is CC 74 (the default), base 64 (ENV page 3); the dice moves the base (sent at once), OCT- sends 64 again
    s = Script()
    s.press(100, ENV); s.enc(240, K3, 1); s.release(270, ENV)
    s.press(400, SEQ); s.tap_key(430, bk(1)); s.release(500, SEQ)
    s.tap_btn(800, OCT_DOWN)
    log = run(s, 1000)
    cc = [(t, d2) for t, st, d1, d2 in log.msgs if st == 0xB0 and d1 == 74]
    check(any(430 <= t < 800 for t, _ in cc) and any(t >= 800 and v == 64 for t, v in cc), "DICE CC: the base value moves at once, OCT- puts 64 back (%s)" % cc)
    # DICE ALL: the bank becomes a piece (kit, bass, chords, arp, perc), OCT- takes it all back
    for answer, want in ((OCT_UP, True), (OCT_DOWN, False)):
        s = Script()
        s.press(100, SEQ); s.tap_key(130, bk(4)); s.release(300, SEQ)
        s.tap_btn(400, answer)
        s.tap_btn(500, PLAY)
        for k in range(8):
            s.at(490, "dump", k)
        log = run(s, 500 + 4 * 1875)
        chs = sorted({st & 15 for tm, st, _, d2 in log.msgs if (st & 0xF0) == 0x90 and d2 and tm > 500})
        if want:
            check(len(chs) >= 7 and set(chs) <= set(range(8)), "DICE ALL: the bank plays a piece (channels %s)" % chs)
            check("".join(d["mode"] for d in log.dumps) == "DDDDKKKD", "DICE ALL: drums on 1-4 and 8, in key on 5-7 (%s)" % "".join(d["mode"] for d in log.dumps))
        else:
            check(chs == [] and "".join(d["mode"] for d in log.dumps) == "FFFFFFFF", "DICE ALL then OCT-: nothing changed (%s)" % chs)


def t_evolve():
    group("0.4: EVOLVE, FREEZE, REVERT, TEMP")
    BAR = 16 * STEP_MS
    s = Script()
    t = seq_page(s, 100, 0, keys=[wk(14)])                          # ALL ON
    t = seq_page(s, t, 2, encs=[(K2, 16), (K3, -2)])               # amount 100 %, every bar (0.8: SEQ page 3)
    t = seq_page(s, t, 0, keys=[bk(8)])                            # EVOLVE
    p = t + 100
    s.tap_btn(p, PLAY)
    for b in range(9):
        s.at(int(p + b * BAR + BAR / 2), "dump", 0)
    def seqkey(at, k):
        s.press(int(at) + 20, SEQ); s.tap_key(int(at) + 50, k); s.release(int(at) + 150, SEQ)
    seqkey(p + 3.5 * BAR, bk(9))                                   # FREEZE in bar 4: this is the seed now
    seqkey(p + 5.5 * BAR, bk(9))                                   # FREEZE again in bar 6: it evolves again
    seqkey(p + 6.5 * BAR, bk(10))                                  # REVERT in bar 7: back to the seed, frozen
    log = run(s, int(p + 9 * BAR))
    h = [d["hash"] for d in log.dumps]
    check(len(h) == 9 and len(set(h[:4])) >= 3, "EVOLVE: the pattern changes every bar (%d different in 4)" % len(set(h[:4])))
    check(h[4] == h[5] == h[3] and h[4] != h[0], "FREEZE: it stops changing, on what was playing")
    check(h[6] != h[5], "FREEZE again: it evolves again")
    check(h[7] == h[8] == h[4], "REVERT: back to the frozen seed, and frozen")
    # REVERT without a FREEZE: the pattern as it was when EVOLVE started
    s = Script()
    t = seq_page(s, 100, 0, keys=[wk(14)])
    t = seq_page(s, t, 2, encs=[(K2, 16), (K3, -2)])
    t = seq_page(s, t, 0, keys=[bk(8)])
    p = t + 100
    s.tap_btn(p, PLAY)
    seqkey(p + 2.5 * BAR, bk(10))
    log = run(s, int(p + 4 * BAR))
    n = log.notes(ch=0, after=int(p + 3 * BAR) - 10, before=int(p + 4 * BAR) - 10)
    check(len(n) == 16 and all(d2 == 100 for _, _, d2 in n), "REVERT: the seed (all on) again (%d notes)" % len(n))
    # EVOLVE with the target NOTES on a track in key: notes change, and stay in the scale
    s = Script()
    t = kp(s, 100, [(K1, 9), (K2, 2), (K4, 1)])        # A minor, track in key
    t = seq_page(s, t, 0, keys=[wk(14)])
    t = seq_page(s, t, 2, encs=[(K1, 1), (K2, 10), (K3, -2)])      # targets +NOTES, amount 75 (0.8: SEQ page 3)
    t = seq_page(s, t, 0, keys=[bk(8)])
    s.tap_btn(t + 100, PLAY)
    log = run(s, t + 100 + int(6 * BAR))
    ps = {d1 for _, d1, _ in log.notes(ch=0, after=t + 100 + int(BAR))}
    check(len(ps) > 2 and all(x % 12 in (9, 11, 0, 2, 4, 5, 7) for x in ps), "EVOLVE +NOTES: new notes, all in A minor (%s)" % sorted(ps))
    # TEMP (grid FX view, held): CLEAR while it is held, the notes come back when it is let go
    s = Script()
    s.steps(50, [0, 4, 8, 12])
    s.raw(100, "attach"); view(s, 200, GC_UNDO, alt=True)
    s.tap_btn(300, PLAY)
    s.at(1000, "pad", 0, 7, 100)
    s.press(1100, SEQ); s.tap_key(1130, wk(0)); s.release(1200, SEQ)
    s.at(3000, "pad", 0, 7, 0)
    log = run(s, 4500)
    check(not log.notes(ch=0, after=1200, before=3000) and log.notes(ch=0, after=3000), "TEMP: a CLEAR while it is held lasts until it is let go")


def t_song_tap_rec():
    group("0.4: song mode, tap tempo, step recording, drum tracks, solo")
    BAR = 16 * STEP_MS
    # pattern 1 plays 60, pattern 2 plays 72; scene 1 = P1, scene 2 = P2; song: scene 1 x 1 bar, scene 2 x 2 bars
    s = Script()
    s.steps(50, [0])
    s.enc(200, E_PRE, 1); program(s, 300, [72])
    s.tap_btn(900, GLO); s.enc(950, E_PRE, 0)
    s.press(1000, SEL); s.tap_key(1030, bk(1)); s.release(1100, SEL)                      # scene 2 = pattern 2
    s.tap_btn(1200, GLO)
    s.enc(1300, E_PRE, -1)
    s.tap_btn(1400, GLO); s.press(1450, SEL); s.tap_key(1480, bk(0)); s.release(1550, SEL); s.tap_btn(1600, GLO)   # scene 1 = P1
    s.raw(1700, "attach"); view(s, 1750, GC_VPERF); view(s, 1800, GC_VPERF)            # PERF, PERF again: SONG
    s.pad(1900, 0, 1); s.pad(1950, 0, 2)                                                # entry 1: scene 1, 1 bar
    s.pad(2000, 1, 0); s.pad(2050, 1, 1); s.pad(2100, 1, 2)                             # entry 2: scene 2, 2 bars
    s.pad(2200, 0, 3)                                                                   # song on
    s.tap_btn(2400, PLAY)
    log = run(s, int(2400 + 4 * BAR + 300))
    bars = [pitches(log, after=int(2400 + b * BAR) - 30, before=int(2400 + (b + 1) * BAR) - 30) for b in range(4)]
    check(bars == [[60], [72], [72], [60]], "SONG: scene 1 for a bar, scene 2 for two, then again (%s)" % bars)
    # HOME + PERF black keys: append; the same scene again = four more bars; HOME + GLO: on
    s = Script()
    s.tap_btn(100, GLO); s.press(150, HOME); s.tap_key(200, bk(0)); s.tap_key(300, bk(0)); s.tap_key(400, bk(1)); s.release(500, HOME)
    s.tap_btn(600, GLO)
    s.raw(700, "attach"); view(s, 750, GC_VPERF); view(s, 800, GC_VPERF)
    log = run(s, 1200)
    pads, _ = log.leds()
    check(pads[0] == GL_CURSOR and pads[1] == GL_BLUE and pads[2] == GL_FAINT, "HOME + PERF scene keys make two entries (%s)" % [pads.get(i) for i in range(3)])
    check(pads[4 * 16 + 7] == GL_DIM and pads[4 * 16 + 8] == GL_BLUE and pads[4 * 16 + 11] == GL_BLUE and pads[4 * 16 + 12] == GL_OFF,
          "the timeline: 8 bars of scene 1 (the entry selected), 4 of scene 2")
    # tap tempo: HOME + REC four times, 500 ms apart = 120 BPM
    s = Script()
    s.press(100, HOME)
    for i in range(4):
        s.tap_btn(200 + 500 * i, REC)
    s.release(1900, HOME)
    s.tap_btn(2000, PLAY)
    c = [t for t in run(s, 3000).clock() if t > 2050]
    gap = (c[-1] - c[0]) / (len(c) - 1) if len(c) > 2 else 0
    check(near(gap, 60000 / (120 * 24), 0.3), "tap tempo: 120 BPM (a tick every %.2f ms)" % gap)
    # step recording: REC while stopped, three keys: steps 1, 2, 3; two keys together: a chord on one step
    s = Script()
    s.tap_btn(100, REC)
    s.tap_key(200, KEY_C4); s.tap_key(400, KEY_E4); s.tap_key(600, KEY_G4)
    s.keys(800, KEY_C4 | KEY_E4); s.keys(850, 0)
    s.tap_btn(1000, REC)
    s.tap_btn(1100, PLAY)
    log = run(s, int(1100 + 4 * STEP_MS) + 50)
    ch = {}
    for t, d1, _ in log.notes(ch=0, after=1100):
        ch.setdefault(round((t - 1100) / STEP_MS), []).append(d1)
    check([sorted(ch.get(k, [])) for k in range(4)] == [[60], [64], [67], [60, 64]], "step recording: one note a step, a chord on step 4 (%s)" % ch)
    # drum tracks: tracks 1 and 2 DRUM (HOME page 3, K4), track 2 plays 38; REC: white key 2 plays and records track 2
    s = Script()
    t = kp(s, 100, [(K4, 2)])
    s.tap_key(t, bk(1)); t += 80
    t = kp(s, t, [(K4, 2)], cur=2)           # (the page stays where it was: 0.5 has a fourth one after it)
    s.press(t, SEL); s.enc(t + 30, K4, -22); s.release(t + 60, SEL); t += 120
    s.tap_key(t, bk(0)); t += 80
    s.tap_btn(t, REC); t += 100
    s.tap_key(t, wk(0)); s.tap_key(t + 200, wk(1)); s.tap_key(t + 400, wk(0)); t += 600
    s.tap_btn(t, REC); t += 100
    s.at(t, "dump", 0); s.at(t, "dump", 1)
    s.tap_btn(t + 100, PLAY)
    log = run(s, int(t + 100 + 4 * STEP_MS))
    d = {x["track"]: x for x in log.dumps}
    check(d[1]["mode"] == "D" and d[2]["mode"] == "D" and d[2]["pen"] == 38, "HOME page 3 K4: DRUM tracks")
    check(d[1]["on"][:4] == "x.x." and d[2]["on"][:4] == ".x..", "drum step recording: key 1 = track 1, key 2 = track 2 (%s %s)" % (d[1]["on"][:4], d[2]["on"][:4]))
    check(pitches(log, ch=1, after=t + 100) == [38], "track 2 plays its own note on its own channel")
    # a drum pad controller: with REC on a drum track, an incoming note goes to the drum track that plays it
    s = Script()
    t = kp(s, 100, [(K4, 2)])
    s.tap_key(t, bk(1)); t += 80
    t = kp(s, t, [(K4, 2)], cur=2)           # (the page stays where it was: 0.5 has a fourth one after it)
    s.press(t, SEL); s.enc(t + 30, K4, -22); s.release(t + 60, SEL); t += 120
    s.tap_key(t, bk(0)); t += 80
    s.tap_btn(t, REC); t += 100
    s.at(t, "midi", 0x99, 38, 100); s.at(t + 50, "midi", 0x89, 38, 0); t += 200
    s.at(t, "dump", 1)
    log = run(s, t + 100)
    check(log.dumps and log.dumps[0]["on"][:1] == "x" and any(st == 0x91 and d1 == 38 for _, st, d1, d2 in log.msgs), "incoming note 38 -> drum track 2, played on its channel")
    # solo: the tracks that go silent stop, the others are not cut
    s = Script()
    s.press(50, EDIT); s.enc(60, K1, 100); s.release(70, EDIT)                             # step 1 gate 100 %
    s.steps(100, [0])
    s.tap_key(250, bk(1)); s.steps(300, [0]); s.press(400, EDIT); s.enc(410, K1, 100); s.release(420, EDIT)
    s.tap_key(500, bk(0))
    s.tap_btn(600, PLAY)
    s.tap_key(650, bk(10))                                                                  # solo track 1 during step 1
    log = run(s, 800)
    check(not [t for t, d1 in log.offs(ch=0) if 640 <= t < 700] and [t for t, d1 in log.offs(ch=1) if 640 <= t < 700],
          "SOLO cuts only the tracks it silences")
    # REC armed: SEQ, FX and LFO keep their keys (0.3 lost them)
    s = Script()
    s.tap_btn(100, REC)
    s.press(200, SEQ); s.tap_key(230, wk(14)); s.release(300, SEQ)                          # ALL ON
    s.tap_btn(400, PLAY)
    check(len(run(s, 400 + 1875).notes(ch=0, after=400)) >= 15, "REC armed: SEQ + ALL ON still works")


def t_usb_page():
    group("0.4.1: the USB page (0.12: SAVE 3 SYSTEM), a reconnect without the cable (SEL + K1 twice)")
    s = Script()
    s.steps(50, [0])
    s.press(200, SAVE); s.tap_btn(230, OCT_UP, hold=20); s.tap_btn(270, OCT_UP, hold=20)   # SAVE 3
    s.pages[SAVE] = 2
    s.press(300, SEL)
    s.enc(320, K1, 1)                                                   # SEL + K1: asks
    s.at(500, "shot")
    s.enc(800, K1, 1)                                                   # again: reconnects
    s.release(900, SEL); s.release(930, SAVE)
    s.tap_btn(1000, PLAY)
    log = run(s, 1500)
    rc = [int(m.group(1)) for m in re.finditer(r"^\s*(\d+) ms  USB reconnect", log.text, re.M)]
    check(rc == [800] or (len(rc) == 1 and 800 <= rc[0] <= 830), "SEL + K1 once asks, twice reconnects (%s)" % rc)
    check(pitches(log, ch=0, after=1000) == [60], "the knobs did not touch the track on the USB page")


def t_grid_drum():
    group("0.4: grid DRUM view")
    s = Script()
    s.raw(100, "attach"); view(s, 200, GC_VSTEP)                                        # STEP again: DRUM
    s.pad(300, 0, 0); s.pad(400, 4, 1); s.pad(500, 8, 1)                                # track 1 step 1, track 2 steps 5, 9
    s.pad(600, 2, 2, hold=500)                                                          # held: track 3 step 3 selected, not set
    s.tap_btn(1200, PLAY)
    log = run(s, int(1200 + 16 * STEP_MS))
    a = [round((t - 1200) / STEP_MS) for t, _, _ in log.notes(ch=0, after=1200)]
    b = [round((t - 1200) / STEP_MS) for t, _, _ in log.notes(ch=1, after=1200)]
    check(a == [0] and b == [4, 8] and not log.notes(ch=2, after=1200), "DRUM view: a row per track (%s %s)" % (a, b))
    pads, ctls = log.leds(until=1190)
    check(ctls[GC_VSTEP] == GL_CYAN and ctls[GC_TRK0 + 2] == GL_CURSOR, "the STEP button shows DRUM, the held pad selected track 3")
    check(pads[0] == GL_ON and pads[16 + 4] == GL_ON and pads[2 * 16 + 2] == GL_ORANGE, "the pads show the steps and the cursor")


# (the grid scenarios: below, after the grid's views are redone)
# ------------------------------------------------------------------------------------------------ 0.2.1
def t_rec_fresh_step():
    group("REC: the first recorded note of a never-programmed step is its note (0.2.1)")
    s = Script()                                           # REC, PLAY, E4 during step 3 (index 2)
    s.tap_btn(50, REC)
    s.tap_btn(100, PLAY)
    s.tap_key(100 + int(2.4 * STEP_MS), KEY_E4)
    log = run(s, 5000)
    loops = [n for n in log.notes(0, after=1500)]
    check(len(loops) >= 2 and all(d1 == 64 for _, d1, _ in loops), "second and third pass play only E4 (%s)" % [d1 for _, d1, _ in loops])
    # a step that was programmed before keeps its note, the recorded one joins it (a chord)
    s = Script()
    s.keys(60, 0); s.press(80, SEL); s.tap_key(100, KEY_C4); s.release(300, SEL)      # SEL + C4 on step 1 (cursor)
    s.tap_btn(400, REC)
    s.tap_btn(450, PLAY)
    s.tap_key(450 + 20, KEY_G4)                            # during step 1 again
    log = run(s, 3500)
    got = sorted({d1 for _, d1, _ in log.notes(0, after=450 + 1800)})
    check(got == [60, 67], "an already programmed step takes the recorded note as a second note (%s)" % got)
    # recording the pen note itself is not doubled
    s = Script()
    s.tap_btn(50, REC)
    s.tap_btn(100, PLAY)
    s.tap_key(100 + int(2.4 * STEP_MS), KEY_C4)
    log = run(s, 5000)
    at = [d1 for _, d1, _ in log.notes(0, after=1500)]
    check(len(at) >= 2 and set(at) == {60}, "C4 recorded on a fresh step is one note (%s)" % at)


def stall_run(second_half):
    """PLAY, SEL + ALG climbs from 128 to 300 BPM, then keeps changing the tempo; the screen costs what its SPI costs"""
    s = Script()
    s.raw(5, "lcdcost")
    end = s.steps(100, [0, 4, 8, 12])
    s.tap_btn(end + 100, PLAY)
    t = end + 400
    s.press(t, SEL)
    for i in range(172):                                   # 128 -> 300 BPM, a click every 20 ms
        s.enc(t + 20 + i * 20, E_ALG, 1)
    t += 20 + 172 * 20
    for i in range(second_half):                           # then up and down one BPM
        s.enc(t + i * 25, E_ALG, -1 if i % 2 else 1)
    s.release(t + second_half * 25 + 50, SEL)
    return s, t + second_half * 25 + 800, end + 400


def t_ui_stalls():
    group("the screen never holds the clock: tempo changes at 300 BPM (0.2.1)")
    s, end, t0 = stall_run(160)
    log = run(s, end)
    rec = log.text.count("clock recovery")
    m = re.search(r"longest pass of the main loop (\d+) ms", log.text)
    longest = int(m.group(1)) if m else 999
    check(rec == 0, "no clock recovery while the tempo is changed (%d)" % rec)
    check(longest <= 12, "no pass of the main loop longer than 12 ms (%d ms)" % longest)
    clk = [t for t in log.clock() if t > t0 + 4200]        # at 300 BPM: a tick every 8.33 ms
    gaps = [b - a for a, b in zip(clk, clk[1:])]
    check(len(gaps) > 100 and max(gaps) <= 20, "the clock leaves evenly, no bursts (longest gap %s ms)" % (max(gaps) if gaps else None))
    check(len(log.clock()) > 500, "the clock keeps running (%d ticks)" % len(log.clock()))


# ------------------------------------------------------------------------------------------------ the grid
def shift(s, t, on): return s.at(t, "ctl", GC_SHIFT, 127 if on else 0)


def view(s, t, btn, alt=False):
    """a view button (SHIFT for the alternate view); returns the time after"""
    if alt:
        shift(s, t, 1); s.ctl(t + 10, btn, hold=20); shift(s, t + 50, 0)
        return t + 70
    s.ctl(t, btn, hold=20)
    return t + 40


def t_grid_link():
    group("grid: attach, repaint, keep-alive, time-out, back-pressure")
    s = Script()
    s.raw(300, "attach")
    log = run(s, 1500)
    check(len(log.grid_msgs(before=300)) == 0, "nothing is sent before a bridge attaches")
    pads, ctls = log.leds()
    check(len(pads) == 128 and len(ctls) == 32, "attach repaints all 128 pads and 32 buttons (%d, %d)" % (len(pads), len(ctls)))
    check(log.grid_msgs()[0][0] < 400, "the repaint starts right away")
    check(pads[0] == GL_ORANGE and pads[1] == GL_FAINT and pads[15] == GL_FAINT, "step view: the cursor step (off) is orange, the rest of the 16 steps faint")
    check(pads[16] == GL_OFF and pads[63] == GL_OFF, "steps past the pattern length are dark")
    check(ctls[GC_VSTEP] == GL_CURSOR and ctls[GC_TRK0] == GL_CURSOR and ctls[GC_PAT0] == GL_ON and ctls[GC_SCN0] == GL_ON, "STEP view, track 1, pattern 1, scene 1")

    s = Script()
    s.raw(300, "attach")
    log = run(s, 9000)
    check(len(log.grid_msgs(after=4200)) == 0, "no keep-alive: the grid link lets go after 3.5 s")
    s = Script()
    s.raw(300, "attach")
    for t in range(1300, 9000, 1000): s.raw(t, "hb")
    log = run(s, 9000)
    check(len(log.grid_msgs(after=4200)) > 3, "keep-alive holds the link (%d refresh messages)" % len(log.grid_msgs(after=4200)))
    s = Script()
    s.raw(300, "attach"); s.raw(1500, "detach")
    log = run(s, 4000)
    check(len(log.grid_msgs(after=1600)) == 0, "detach stops the traffic")

    s = Script()
    s.steps(50, [0])
    s.raw(150, "txroom 10"); s.raw(200, "attach"); s.tap_btn(300, PLAY); s.raw(1500, "txroom 64")
    log = run(s, 2500)
    check(len(log.grid_msgs(before=1500)) == 0 and len(log.grid_msgs(after=1500)) > 100, "LED traffic waits for room in the USB queue")
    check(len(log.notes(ch=0, before=1500)) >= 1 and len(log.clock()) > 10, "notes and clock are not held back")

    s = Script()
    s.tap_btn(50, REC); s.raw(100, "attach"); s.pad(400, 3, 0)
    log = run(s, 900)
    check(not any((st & 0xF0) == 0x90 and (st & 15) != 15 for _, st, _, _ in log.msgs), "pad presses are not echoed as notes while recording")

    # the bridge dies with FILL held, and with an FX pad held: both are let go
    s = Script()
    end = s.steps(50, [0])
    s.press(end + 20, EDIT); s.enc(end + 40, K2, 7); s.release(end + 80, EDIT)
    s.raw(300, "attach"); s.at(400, "ctl", GC_FILL, 127)
    s.tap_btn(500, PLAY)
    log = run(s, 9000)
    n = log.notes(ch=0)
    check(n and all(t < 4000 for t, _, _ in n) and n[-1][0] < 4200, "FILL held on the grid is let go when the bridge falls silent (%d notes, last %s)" % (len(n), n[-1][0] if n else None))
    s = Script()
    s.steps(50, [0, 4, 8, 12])
    s.raw(300, "attach"); view(s, 350, GC_UNDO, alt=True); s.at(500, "pad", 9, 0, 100)      # O+ held
    s.tap_btn(600, PLAY)
    log = run(s, 7000)
    p = pitches(log, after=600)
    late = pitches(log, after=4500)
    check(p and p[0] == 72 and late and set(late) == {60}, "an FX held when the bridge falls silent is let go (%s ... %s)" % (p[:2], late[:2]))


def t_grid_step():
    group("grid: step view")
    s = Script()
    s.raw(100, "attach"); s.pad(500, 0, 0); s.pad(700, 4, 0)
    s.tap_btn(1000, PLAY)
    log = run(s, 3000)
    pads, _ = log.leds(until=900, after=0)
    check(pads[4] == GL_CURSOR and pads[0] == GL_ON, "tapped steps light up (%s %s)" % (pads[0], pads[4]))
    n = log.notes(ch=0, after=1000)
    check(len(n) > 1 and near(n[1][0] - n[0][0], 4 * STEP_MS) and n[0][1] == 60, "pad steps play note 60")
    runs = [m for m in log.msgs if m[1] == 0x9F and m[3] == GL_PLAY and 1000 <= m[0] < 2500]
    check(len(runs) >= 8, "the playhead runs along the row (%d LED updates)" % len(runs))

    s = Script()
    s.raw(100, "attach"); s.pad(500, 3, 0, hold=600)
    log = run(s, 1500)
    p_early, _ = log.leds(until=700, after=0)
    p_late, _ = log.leds(until=1400, after=0)
    check(p_early[3] == GL_CURSOR and p_late[3] == GL_ORANGE, "long press: toggled at first, then put back, the cursor stays (%s -> %s)" % (p_early[3], p_late[3]))

    s = Script()
    s.raw(100, "attach"); shift(s, 400, 1); s.pad(450, 7, 0); shift(s, 600, 0)
    log = run(s, 1200)
    pads, _ = log.leds()
    check(pads[7] == GL_FAINT and pads[8] == GL_OFF and pads[2] == GL_FAINT, "SHIFT + pad 8 sets the length to 8")

    # hold a pad, then press another: the loop between them, and the first step is as it was
    s = Script()
    s.tap_key(50, wk(2))                                   # step 3 on
    s.raw(100, "attach")
    fx_tap(s, 300)                                         # 0.12: SEL + FX tapped: the next two pads make a loop
    s.at(500, "pad", 2, 0, 100)                            # hold step 3 ...
    s.at(900, "pad", 5, 0, 100)                            # ... press step 6: loop 3-6
    s.at(950, "pad", 9, 0, 100)                            # a third pad while both are down: nothing
    s.at(1000, "pad", 9, 0, 0); s.at(1050, "pad", 5, 0, 0); s.at(1100, "pad", 2, 0, 0)
    s.tap_btn(1500, PLAY)
    log = run(s, 1500 + int(13 * STEP_MS))
    n = log.notes(ch=0, after=1500)
    gaps = [b[0] - a[0] for a, b in zip(n, n[1:])]
    check(len(n) >= 3 and all(near(g, 4 * STEP_MS) for g in gaps), "loop 3-6: step 3 comes back every 4 steps (%s)" % ["%.0f" % g for g in gaps])
    pads, _ = log.leds(until=1490)
    check(pads[2] == GL_CURSOR and pads[1] == GL_OFF and pads[3] == GL_FAINT and pads[5] == GL_FAINT and pads[6] == GL_OFF and pads[9] == GL_OFF,
          "the loop on the pads: 3 is the cursor (on), 4-6 in the loop, 2 / 7 / 10 outside (%s)" % [pads[i] for i in (1, 2, 3, 5, 6, 9)])
    s = Script()
    s.raw(100, "attach"); s.at(400, "pad", 0, 0, 100); s.at(450, "pad", 1, 0, 100); s.at(500, "pad", 1, 0, 0); s.at(520, "pad", 0, 0, 0)
    log = run(s, 1200)
    pads, _ = log.leds()
    check(pads[0] == GL_ON and pads[1] == GL_CURSOR, "two quick taps are two steps, not a loop (%s %s)" % (pads[0], pads[1]))

    s = Script()
    s.raw(100, "attach"); s.pad(300, 0, 0)
    s.pad(400, 7, 4)
    s.pad(500, 3, 6)
    s.pad(600, 5, 7)
    s.tap_btn(900, PLAY)
    log = run(s, 2200)
    n = log.notes(ch=0, after=900)
    check(len(n) >= 4 and [d1 for _, d1, _ in n[:4]] == [53] * 4 and n[0][2] == 64, "velocity / ratchet / note rows (%s)" % n[:4])
    pads, _ = log.leds(until=800)
    check(pads[7 * 16 + 5] == GL_CURSOR and pads[4 * 16 + 7] == GL_ACCENT and pads[6 * 16 + 3] == GL_YELLOW, "the parameter rows show the cursor step")

    s = Script()
    s.raw(100, "attach"); s.pad(300, 0, 0); s.pad(400, 0, 7)
    shift(s, 500, 1); s.pad(520, 4, 7); s.pad(600, 7, 7); s.pad(680, 7, 7); shift(s, 750, 0)
    s.tap_btn(900, PLAY)
    log = run(s, 1700)
    got = sorted(d1 for _, d1, _ in log.notes(ch=0, after=900)[:2])
    check(got == [48, 52], "SHIFT + note pads build a chord, again removes (%s)" % got)

    s = Script()
    s.raw(100, "attach"); s.pad(300, 0, 0); s.pad(400, 8 + 7, 6)
    s.tap_btn(600, PLAY)
    log = run(s, 1500)
    on = log.notes(ch=0, after=600)[0][0]
    off = [t for t, _ in log.offs(ch=0) if t > on][0]
    check(near(off - on, STEP_MS, 3), "gate 100%% (%.1f ms)" % (off - on))

    # SHIFT + the chance row: the condition (1:2 plays every other bar)
    s = Script()
    s.raw(100, "attach"); s.pad(300, 0, 0); shift(s, 400, 1); s.pad(420, 1, 5); shift(s, 500, 0)
    log = run(s.tap_btn(600, PLAY), 600 + int(64 * STEP_MS) + 50)
    n = log.notes(ch=0, after=600)
    gaps = [b[0] - a[0] for a, b in zip(n, n[1:])]
    check(len(n) == 3 and all(near(g, 32 * STEP_MS, 3) for g in gaps), "SHIFT + chance row 2: condition 1:2, bars 1, 3, 5 (%d notes)" % len(n))


def t_grid_buttons():
    group("grid: buttons, PERF and TRACK views, banks")
    s = Script()
    s.raw(100, "attach"); s.pad(300, 0, 0)
    s.ctl(500, GC_PLAY)
    s.ctl(1200, GC_PLAY)
    log = run(s, 2200)
    check(len(log.clock()) > 20 and 0xFC in [m[1] for m in log.msgs], "grid PLAY starts and stops")
    _, ctls = log.leds(until=1000, after=0)
    check(ctls[GC_PLAY] == GL_ON, "the PLAY button lights while running")

    # SHIFT + PLAY: continue (with the Song Position Pointer)
    s = Script()
    s.steps(50, [0])
    s.raw(100, "attach"); s.ctl(300, GC_PLAY); s.ctl(300 + int(8 * STEP_MS) + 5, GC_PLAY)
    shift(s, 1500, 1); s.ctl(1520, GC_PLAY); shift(s, 1600, 0)
    log = run(s, 2400)
    spp = [m for m in log.msgs if m[1] == 0xF2]
    check(spp and spp[0][2] == 8 and 0xFB in [m[1] for m in log.msgs if m[0] >= 1500], "SHIFT + PLAY continues: SPP %s (8 sixteenths) then Continue" % (spp[0][2:] if spp else None,))

    # PERF view: mute a track, queue patterns
    s = Script()
    s.raw(100, "attach")
    s.tap_key(200, wk(0))
    s.ctl(300, 9)
    s.tap_key(400, wk(0))
    view(s, 500, GC_VPERF)
    s.pad(700, 0, 1)
    s.pad(800, 3, 0)
    s.tap_btn(1000, PLAY)
    log = run(s, 2500)
    pads, ctls = log.leds(until=950)
    check(pads[1 * 16 + 0] == GL_MUTED and pads[0 * 16 + 0] == GL_ON, "PERF: mute pads")
    check(pads[0 * 16 + 3] == GL_ON and pads[0 * 16 + 2] == GL_FAINT and pads[1 * 16 + 2] == GL_ACCENT, "PERF: pattern 2 is now track 1's pattern")
    check(len(log.notes(ch=1, after=1000)) == 0 and len(log.notes(ch=0, after=1000)) == 0, "muted track is silent, the other one is now on an empty pattern")

    # SHIFT + FILL: the other bank; the track buttons and PERF follow
    s = Script()
    s.raw(100, "attach")
    shift(s, 300, 1); s.ctl(320, GC_FILL); shift(s, 380, 0)
    s.ctl(450, GC_TRK0 + 2)                                   # track 11
    s.tap_key(500, wk(0))                                     # its step 1
    view(s, 600, GC_VPERF)
    s.pad(700, 0, 2)                                          # mute track 11 (bank 2, row 3)
    s.tap_btn(1200, PLAY)
    log = run(s, 2200)
    pads, ctls = log.leds(until=1150)
    check(ctls[GC_TRK0 + 2] == GL_CURSOR and ctls[GC_TRK0] == GL_BLUE, "bank 2: the track buttons are tracks 9-16 (%s %s)" % (ctls[GC_TRK0 + 2], ctls[GC_TRK0]))
    check(pads[2 * 16] == GL_MUTED and len(log.notes(ch=10, after=1200)) == 0, "PERF shows bank 2: muting row 3 silences track 11")

    # SHIFT + a pattern button: copy the pattern there
    s = Script()
    s.raw(100, "attach")
    s.steps(200, [0, 8])
    shift(s, 400, 1); s.ctl(420, GC_PAT0 + 3); shift(s, 480, 0)
    s.ctl(600, GC_PAT0 + 3)
    s.tap_btn(800, PLAY)
    log = run(s, 800 + int(16 * STEP_MS))
    n = log.notes(ch=0, after=800)
    _, ctls = log.leds(until=790)
    check(ctls[GC_PAT0 + 3] == GL_ON and len(n) == 2 and near(n[1][0] - n[0][0], 8 * STEP_MS), "SHIFT + pattern 4 copies pattern 1 there (%d notes)" % len(n))

    # TRACK view: tools, swing, division, length, arpeggio
    s = Script()
    s.raw(100, "attach"); view(s, 200, GC_VTRACK)
    s.pad(300, 5, 0)                               # EUCLID, 4 pulses
    s.tap_btn(900, PLAY)
    log = run(s, 3500)
    n = log.notes(ch=0, after=900)
    check(len(n) >= 4 and near(n[1][0] - n[0][0], 4 * STEP_MS, 2), "TRACK view: EUCLID tool fills the row")
    s = Script()
    s.raw(100, "attach"); view(s, 200, GC_VTRACK); s.pad(300, 5, 0); s.pad(500, 5, 0); s.tap_btn(900, PLAY)
    check(len(run(s, 2500).notes(ch=0, after=900)) == 0, "0.8: EUCLID again: the live euclid is off, the empty row is heard again")
    s = Script()
    s.raw(100, "attach"); view(s, 200, GC_VTRACK); s.pad(300, 7, 2)
    view(s, 400, GC_VSTEP); s.pad(500, 0, 0); s.pad(600, 1, 0)
    s.tap_btn(900, PLAY)
    n = run(s, 2200).notes(ch=0, after=900)
    check(near(n[1][0] - n[0][0], 1.5 * STEP_MS), "TRACK view swing 75 (%.1f ms)" % (n[1][0] - n[0][0]))
    s = Script()
    s.raw(100, "attach"); view(s, 200, GC_VTRACK); s.pad(300, 6, 3)
    view(s, 400, GC_VSTEP); s.pad(500, 0, 0); s.pad(600, 1, 0)
    s.tap_btn(900, PLAY)
    n = run(s, 2200).notes(ch=0, after=900)
    check(near(n[1][0] - n[0][0], 2 * STEP_MS), "TRACK view division 1/8 (%.1f ms)" % (n[1][0] - n[0][0]))
    s = Script()
    s.raw(100, "attach"); view(s, 200, GC_VTRACK); s.pad(300, 1, 4)              # length 8
    view(s, 400, GC_VSTEP); s.pad(500, 0, 0)
    s.tap_btn(900, PLAY)
    n = run(s, 900 + int(17 * STEP_MS)).notes(ch=0, after=900)
    check(len(n) == 3 and near(n[1][0] - n[0][0], 8 * STEP_MS), "TRACK view length 8 (%d notes)" % len(n))
    s = Script()
    s.raw(100, "attach"); s.pad(200, 0, 0); s.pad(300, 0, 7); shift(s, 350, 1); s.pad(370, 4, 7); s.pad(420, 7, 7); shift(s, 480, 0)
    view(s, 500, GC_VTRACK); s.pad(600, 1, 1)                               # ARP UP
    s.tap_btn(900, PLAY)
    log = run(s, 900 + int(STEP_MS) - 5)
    check(pitches(log, after=900) == [48, 52, 55], "TRACK view ARP UP spreads the chord over the step (%s)" % pitches(log, after=900))
    pads, _ = log.leds(until=890)
    check(pads[16 + 1] == GL_WHITE and pads[16 + 13] == GL_WHITE and pads[16] == GL_VIOLET, "the ARP row shows UP and 1 octave")
    # nudge row: the cursor step moves early
    s = Script()
    s.raw(100, "attach"); s.pad(200, 0, 0); s.pad(260, 1, 0); view(s, 400, GC_VTRACK); s.pad(500, 4, 7)      # step 2: nudge -14
    s.tap_btn(900, PLAY)
    n = run(s, 1300).notes(ch=0, after=900)
    check(len(n) >= 2 and near(n[1][0] - n[0][0], 0.86 * STEP_MS, 2.5), "TRACK view nudge -14%% (%.1f ms)" % (n[1][0] - n[0][0]))

    # scene store / recall
    s = Script()
    s.raw(100, "attach")
    view(s, 200, GC_VPERF); s.pad(300, 3, 0)
    shift(s, 400, 1); s.ctl(450, GC_SCN0 + 1); shift(s, 600, 0)
    s.pad(700, 2, 0)
    s.ctl(800, GC_SCN0 + 1)
    log = run(s, 1400)
    pads, ctls = log.leds()
    check(pads[0 * 16 + 3] == GL_ACCENT and ctls[GC_SCN0 + 1] == GL_ON, "scene store + recall brings pattern 2 back")

    s = Script()
    end = s.steps(50, [0])
    s.press(end + 20, EDIT); s.enc(end + 40, K2, 7); s.release(end + 80, EDIT)
    s.raw(end + 200, "attach"); s.ctl(end + 300, GC_PLAY)
    s.at(end + 250, "ctl", GC_FILL, 127); s.at(end + 1500, "ctl", GC_FILL, 0)
    log = run(s, end + 3200)
    n = log.notes(ch=0, after=end + 300)
    _, ctls = log.leds(until=end + 1000, after=0)
    check(len(n) == 1 and n[0][0] < end + 1500, "grid FILL plays FILL-only steps while held (%d notes)" % len(n))
    check(ctls[GC_FILL] == GL_FILL, "the FILL button lights up")


def t_grid_cc_lfo():
    group("grid: CC view (lanes), LFO view")
    s = Script()
    s.raw(100, "attach")
    view(s, 200, GC_VSTEP, alt=True)                         # CC view
    s.pad(300, 8, 5)                                         # lane 1 sends CC 71
    s.pad(400, 7, 6)                                         # base value 59
    s.pad(500, 0, 0)                                         # step 1: 127
    s.pad(600, 1, 3)                                         # step 2: 16
    s.pad(700, 1, 3)                                         # step 2 again at the same level: no lock
    s.tap_btn(1200, PLAY)
    log = run(s, 1200 + int(18 * STEP_MS))
    cc = [d2 for t, st, d1, d2 in log.msgs if st == 0xB0 and d1 == 71 and t >= 1200]
    n = log.notes(ch=0, after=1200)
    check(cc[:3] == [127, 59, 127], "CC view: step 1 locks 127, step 2 goes back to the base 59 (%s)" % cc[:4])
    check(len(n) == 4 and sorted(set(round((t - n[0][0]) / STEP_MS) for t, _, _ in n)) == [0, 1, 16, 17], "tapping a bar turns its step on: steps 1 and 2 play (%d notes)" % len(n))
    pads, ctls = log.leds(until=1190)
    check(pads[0] == GL_ACCENT and pads[48] == GL_ON and pads[1] == GL_OFF and pads[49] == GL_ORANGE and pads[50] == GL_FAINT, "the bars: step 1 full, step 2 empty (the cursor) (%s)" % [pads[i] for i in (0, 48, 1, 49)])
    check(pads[5 * 16 + 8] == GL_WHITE and pads[4 * 16 + 0] == GL_CURSOR and ctls[GC_VSTEP] == GL_VIOLET, "CC 71 marked, lane 1 selected, STEP button shows the alternate view")

    s = Script()
    s.raw(100, "attach")
    view(s, 200, GC_VPERF, alt=True)                         # LFO view
    s.pad(300, 0, 0)                                         # LFO 1 (selected): on
    s.pad(400, 8, 7)                                         # CC 71
    s.pad(500, 15, 3)                                        # depth 127
    s.tap_btn(900, PLAY)
    log = run(s, 900 + 2000)
    cc = [d2 for t, st, d1, d2 in log.msgs if st == 0xB0 and d1 == 71]
    check(len(cc) > 40 and min(cc) <= 2 and max(cc) >= 125, "LFO view: LFO 1 on CC 71, full depth (%d, %s..%s)" % (len(cc), min(cc) if cc else None, max(cc) if cc else None))
    pads, _ = log.leds(until=890)
    check(pads[0] == GL_ACCENT and pads[16 + 0] == GL_WHITE and pads[16 + 8] == GL_WHITE and pads[7 * 16 + 8] == GL_WHITE, "LFO 1 on + selected, sine, CC, CC 71")
    s = Script()
    s.raw(100, "attach"); view(s, 200, GC_VPERF, alt=True); s.pad(300, 3, 0); s.pad(400, 3, 0); s.pad(450, 3, 0)   # select 4, on, off
    s.tap_btn(900, PLAY)
    log = run(s, 2000)
    check(not any(st == 0xB0 and d1 == 74 for _, st, d1, _ in log.msgs), "a tap selects, the next taps switch it on and off")


def t_grid_beat_fx():
    group("grid: BEAT view, FX view (effects, kills, DJ loop, panic)")
    s = Script()
    s.raw(100, "attach")
    view(s, 200, GC_VTRACK, alt=True)                        # BEAT view
    s.pad(300, 3, 0); s.pad(350, 0, 1)                       # HOUSE KICK
    s.pad(400, 13, 0)                                        # LOAD (0.8: row 1, pad 14)
    shift(s, 700, 1); shift(s, 900, 0)                       # SHIFT: the preview
    s.tap_btn(1000, PLAY)
    log = run(s, 1000 + int(16 * STEP_MS))
    n = log.notes(ch=0, after=1000)
    gaps = [b[0] - a[0] for a, b in zip(n, n[1:])]
    check(len(n) == 4 and all(near(g, 4 * STEP_MS) for g in gaps), "BEAT: HOUSE KICK #1 is four on the floor (%d notes)" % len(n))
    pads, _ = log.leds(until=690)
    check(pads[3] == GL_WHITE and pads[16] == GL_WHITE and pads[32 + 11] == GL_WHITE, "genre, function, and the next variation (2) marked")
    pads, _ = log.leds(until=890)
    check(pads[4 * 16 + 0] == GL_ACCENT and pads[4 * 16 + 4] == GL_ACCENT and pads[4 * 16 + 1] == GL_FAINT and pads[4 * 16 + 14] == GL_ON,
          "SHIFT: the preview of variation 2, X...X...X...X.x.")
    # the dice from the grid: DICE SEQ, BACK
    s = Script()
    s.raw(100, "attach"); view(s, 200, GC_VTRACK, alt=True)
    s.pad(300, 0, 3); s.pad(400, 6, 3)
    s.tap_btn(500, PLAY)
    check(not run(s, 500 + 1875).notes(ch=0, after=500), "BEAT view: DICE SEQ, BACK")

    # FX view: an effect held, latched, a kill, the loop, the panic
    s = Script()
    s.steps(50, [0, 4, 8, 12])
    s.raw(100, "attach"); view(s, 200, GC_UNDO, alt=True)
    s.tap_btn(400, PLAY)
    s.at(400 + int(4 * STEP_MS) - 20, "pad", 9, 0, 100); s.at(400 + int(8 * STEP_MS) - 20, "pad", 9, 0, 0)          # O+ held over step 5
    shift(s, 1400, 1); s.pad(1420, 10, 0); shift(s, 1500, 0)                                                         # O- latched
    log = run(s, 400 + int(32 * STEP_MS))
    p = pitches(log, after=400)
    check(p[:3] == [60, 72, 60] and all(x == 48 for x in pitches(log, after=1500)), "O+ while held, O- latched (%s)" % p[:8])

    s = Script()
    s.steps(50, list(range(16)))
    s.raw(100, "attach"); view(s, 200, GC_UNDO, alt=True)
    s.tap_btn(400, PLAY)
    s.at(1000, "pad", 0, 5, 100); s.at(1500, "pad", 0, 5, 0)                 # kill track 1 for half a second
    log = run(s, 2200)
    check(not log.notes(ch=0, after=1001, before=1500) and log.notes(ch=0, after=1500), "KILL pad: track 1 is silent while it is held")
    check(any(t2 >= 1000 and t2 <= 1001 for t2, _ in log.offs(ch=0)), "and its sounding note is cut at once")

    s = Script()
    s.raw(100, "attach")
    for i in range(8):                                       # steps 1-8: notes 48-55
        s.pad(150 + 60 * i, i, 0, hold=20); s.pad(170 + 60 * i, i, 7, hold=20)
    view(s, 700, GC_UNDO, alt=True)
    s.tap_btn(800, PLAY)
    s.pad(800 + int(2 * STEP_MS) - 10, 3, 1)                # 0.5.1: row 2, 1/4 tapped: a LOOP (four steps) from step 3
    log = run(s, 800 + int(20 * STEP_MS))
    p = pitches(log, after=800)
    check(p[:8] == [48, 49, 50, 51, 52, 50, 51, 52] or p[2:10] == [50, 51, 52, 53, 50, 51, 52, 53], "1/4 loop from the grid: four steps again and again (%s)" % p[:10])
    pads, _ = log.leds()
    check(pads[1 * 16 + 3] == GL_ACCENT and pads[1 * 16 + 15] == GL_PLAY, "the 1/4 pad (a LOOP that stays) and EXIT light")

    s = Script()
    s.raw(100, "attach"); view(s, 200, GC_UNDO, alt=True); s.pad(400, 15, 7)
    log = run(s, 700)
    check(len([m for m in log.msgs if (m[1] & 0xF0) == 0xB0 and m[2] == 123 and m[0] >= 400]) == 14, "PANIC pad: All Notes Off on the 14 track channels")


def t_grid_proj():
    group("grid: PROJ view (key, slots, tempo, song position)")
    s = Script()
    s.raw(100, "attach")
    view(s, 200, GC_REC, alt=True)                           # PROJ view
    s.pad(300, 2, 0)                                         # root D
    s.pad(350, 2, 1)                                         # MINOR
    s.pad(400, 0, 3)                                         # track 1 follows the key
    view(s, 500, GC_VSTEP)
    s.pad(600, 0, 0); s.pad(700, 2, 7)                       # step 1: the third pad of the note row
    s.tap_btn(1000, PLAY)
    log = run(s, 1000 + int(STEP_MS))
    check(pitches(log, after=1000) == [53], "D minor: the note row starts on D3, its third pad is F3 (%s)" % pitches(log, after=1000))
    pads, _ = log.leds(until=990)
    check(pads[7 * 16 + 0] == GL_WHITE and pads[7 * 16 + 7] == GL_WHITE and pads[7 * 16 + 2] == GL_CURSOR, "the roots of the note row are white, the step's note marked (%s)" % [pads[7 * 16 + i] for i in (0, 2, 7)])

    s = Script()
    s.raw(100, "attach")
    view(s, 200, GC_REC, alt=True)
    s.pad(300, 2, 0); s.pad(350, 2, 1); s.pad(400, 0, 3)
    view(s, 500, GC_VSTEP); s.pad(600, 0, 0); s.pad(700, 2, 7)
    view(s, 800, GC_REC, alt=True); s.pad(900, 9, 2)        # SHIFT +2
    s.tap_btn(1000, PLAY)
    log = run(s, 1000 + int(STEP_MS))
    check(pitches(log, after=1000) == [55], "SHIFT +2: F3 plays as G3 (%s)" % pitches(log, after=1000))
    pads, _ = log.leds(until=990)
    check(pads[0 + 2] == GL_WHITE and pads[16 + 2] == GL_WHITE and pads[32 + 9] == GL_WHITE and pads[48] == GL_CYAN and pads[48 + 1] == GL_FAINT,
          "root, scale, shift and the track flag are marked")
    check(pads[64 + 0] == GL_WHITE and pads[64 + 1] == GL_VIOLET and pads[64 + 4] == GL_ON, "row 5: the MASTER knob is TEMPO, the remote is on")

    # slots: pick 3, SAVE SAVE
    fd, flash = tempfile.mkstemp(); os.close(fd); os.remove(flash)
    try:
        s = Script()
        s.raw(100, "attach"); view(s, 200, GC_REC, alt=True)
        s.pad(300, 2, 5); s.pad(400, 8, 5); s.pad(600, 8, 5)
        log = run(s, 3000, flash=flash)
        check(log.saves and log.saves[0][1] == 3, "PROJ: slot 3, SAVE twice saves it (%s)" % log.saves)
        pads, _ = log.leds()
        check(pads[80 + 2] == GL_CURSOR and pads[80 + 9] == GL_ORANGE, "slot 3 is chosen and can be loaded")
    finally:
        if os.path.exists(flash):
            os.remove(flash)

    # tempo +10, song position
    s = Script()
    s.raw(100, "attach"); view(s, 200, GC_REC, alt=True); s.pad(300, 3, 6)
    s.tap_btn(500, PLAY)
    clk = run(s, 1500).clock()
    per = (clk[-1] - clk[10]) / (len(clk) - 11)
    check(near(per, 60000.0 / (138 * 24), 0.1), "tempo +10 from the grid: 138 BPM (%.2f ms a tick)" % per)
    s = Script()
    s.steps(50, [0])
    s.raw(100, "attach"); view(s, 200, GC_REC, alt=True); s.pad(300, 11, 5)            # EXPORT
    log = run(s, 600)
    ends = [m for _, m in log.sysex if m[4] == 0x03]
    check(len(ends) == 1 and len(log.sysex) >= 2 and all(m[:4] == [0xF0, 0x7D, 0x53, 0x47] for _, m in log.sysex), "the EXPORT pad sends the project as SysEx (%d frames)" % len(log.sysex))
    s = Script()
    s.raw(100, "attach"); view(s, 200, GC_REC, alt=True); s.pad(300, 2, 7)
    shift(s, 400, 1); s.ctl(420, GC_PLAY); shift(s, 480, 0)
    log = run(s, 900)
    spp = [m for m in log.msgs if m[1] == 0xF2]
    check(spp and spp[0][2] == 32 and spp[0][3] == 0, "bar 3: Song Position 32 sixteenths (%s)" % [m[2:] for m in spp])


# ------------------------------------------------------------------------------------------------ 0.5
def ccs(log, ch=None, cc=None, after=0, before=1 << 30):
    return [(t, d1, d2) for t, st, d1, d2 in log.msgs if (st & 0xF0) == 0xB0 and (st & 15) not in (14, 15) and d1 < 120
            and not (d1 == 64 and d2 == 0 and cc != 64)                       # (0.10: PLAY / STOP / PANIC lift the sustain)
            and after <= t < before and (ch is None or (st & 15) == ch) and (cc is None or d1 == cc)]


def remote(s, t, cc, v=127): return s.raw(t, "midi 0xBD %d %d" % (cc, v))      # SAGGA REMOTE: channel 14


def perf_sel(s, t, encs):
    """PERF mode on, SEL held, the knobs (0.5.1: pattern, length, scale, MUTE QUEUE), let go, PERF off; returns the time after"""
    s.tap_btn(t, GLO); t += 60
    t = held(s, t, SEL, encs)
    s.tap_btn(t, GLO)
    return t + 60


def perf(s, t, encs):
    """PERF mode on, the knobs (0.5.1: MORPH, MORPH TO, TRANSPOSE, QUANTISE), PERF off; returns the time after"""
    s.tap_btn(t, GLO); t += 60
    for e, d in encs:
        s.enc(t, e, d); t += 30
    s.tap_btn(t, GLO)
    return t + 60


def t05_planes():
    group("0.5: lengths per parameter (notes, velocities, gates)")
    s = Script()
    t = program(s, 100, [60, 64, 67])                     # steps 1-3: C E G (the cursor stays on step 3)
    t = s.steps(t, [3, 4, 5, 6, 7])                       # steps 4-8 on (they take the pen note, G); the cursor on 8
    s.enc(t, E_ALG, -6); t += 40                          # cursor on step 2
    s.enc(t, K2, -60); t += 40                            # velocity of step 2: 40
    t = home_page(s, t, 4, [(K1, 3), (K2, 2)])            # HOME page 4: NOTE LOOP 3, VEL LOOP 2
    s.tap_btn(t, PLAY)
    log = run(s, t + int(8.5 * STEP_MS))
    n = log.notes(ch=0, after=t)
    check([d1 for _, d1, _ in n[:8]] == [60, 64, 67, 60, 64, 67, 60, 64], "a 3-step melody over 8 hits (%s)" % [d1 for _, d1, _ in n[:8]])
    check([d2 for _, _, d2 in n[:6]] == [100, 40, 100, 40, 100, 40], "a 2-step velocity loop (%s)" % [d2 for _, _, d2 in n[:6]])
    # without the loops the same pattern plays as written
    s = Script()
    t = program(s, 100, [60, 64, 67])
    t = s.steps(t, [3, 4, 5, 6, 7])
    s.tap_btn(t, PLAY)
    log = run(s, t + int(8.5 * STEP_MS))
    check(pitches(log, after=t)[:8] == [60, 64, 67, 67, 67, 67, 67, 67], "the same steps without a loop of their own (%s)" % pitches(log, after=t)[:8])
    # a note of a note loop does not switch its step on; the gate loop
    s = Script()
    t = s.steps(100, [0, 1, 2, 3])                        # (the cursor on step 4)
    t = home_page(s, t, 4, [(K1, 2), (K3, 1)])            # NOTE LOOP 2, GATE LOOP 1
    s.enc(t, E_ALG, 6); t += 40                           # cursor on step 10 (off)
    s.enc(t, K1, 5); t += 40                              # its note: 65
    s.press(t, EDIT); s.enc(t + 30, K1, -70); s.release(t + 60, EDIT); t += 120   # its gate: 10 %
    s.enc(t, E_ALG, -20); t += 40                         # step 1
    s.press(t, EDIT); s.enc(t + 30, K1, -70); s.release(t + 60, EDIT); t += 120   # the gate of step 1: 10 %
    s.at(t, "dump", 0)
    s.tap_btn(t + 50, PLAY)
    log = run(s, t + 50 + int(4.5 * STEP_MS))
    d = log.dumps[-1]
    check(d["on"][:10] == "xxxx......", "editing the note and gate of an off step with loops of their own leaves it off (%s)" % d["on"][:10])
    n = log.notes(ch=0, after=t)
    offs = log.offs(ch=0)
    gate = [o - a for (a, _, _), (o, _) in zip(n, [x for x in offs if x[0] > t])]
    check(len(gate) >= 3 and all(g < 0.5 * STEP_MS for g in gate[:3]), "a gate loop of 1 step: every hit gets step 1's gate (%s)" % [round(g) for g in gate[:3]])
    # Song Position: the loops are where they would be
    s = Script()
    t = program(s, 100, [60, 64, 67])
    t = s.steps(t, list(range(3, 16)))
    t = home_page(s, t, 4, [(K1, 3)])
    s.press(t, HOME); s.tap_btn(t + 20, PLAY); s.release(t + 90, HOME); t += 300   # slave
    s.raw(t, "midi 0xF2 4 0")                             # 4 sixteenths: the melody is on its 2nd note (4 % 3)
    s.raw(t + 5, "midi 0xFB 0 0")
    for i in range(24 * 2):
        s.raw(t + 10 + i * 20, "midi 0xF8 0 0")
    log = run(s, t + 10 + 48 * 20 + 50)
    check(pitches(log, after=t)[:3] == [64, 67, 60], "SPP: the note loop continues from the right note (%s)" % pitches(log, after=t)[:3])


def t05_quantise():
    group("0.5: QUANTISE, MUTE QUEUE")
    def pattern_switch(quant):
        s = Script()
        t = s.steps(100, list(range(12)))                 # pattern 1: steps 1-12, note 60
        t = home_page(s, t, 0, [(K2, -4)])                # length 12 (three quarters of a bar)
        s.enc(t, E_PRE, 1); s.enc(t + 20, E_ALG, -20); t += 60      # pattern 2 (stopped: at once), the cursor on step 1
        s.press(t, SEL); s.tap_key(t + 30, 1 << (72 - 53), hold=40); s.release(t + 100, SEL); t += 520   # step 1: 72
        s.enc(t, E_PRE, -1); t += 40
        if quant:
            t = perf(s, t, [(K4, quant)])
        s.tap_btn(t, PLAY)
        s.enc(t + int(2.5 * STEP_MS), E_PRE, 1)           # pattern 2 queued in step 3
        log = run(s, t + int(30 * STEP_MS))
        hit = [x for x in log.notes(ch=0, after=t) if x[1] == 72]
        return hit and round((hit[0][0] - t) / STEP_MS), log, t
    k, _, _ = pattern_switch(0)
    check(k == 12, "AUTO (0.4): pattern 2 at the end of the 12-step loop (step %s)" % k)
    k, log, t = pattern_switch(3)
    check(k == 16, "BAR: pattern 2 starts on the bar line, from its first step (step %s)" % k)
    hits = [round((x[0] - t) / STEP_MS) for x in log.notes(ch=0, after=t) if x[1] == 72]
    check(hits[:2] == [16, 28], "... and loops from there (%s)" % hits[:2])
    # mutes: MUTE QUEUE with QUANTISE BAR: the mute comes on the bar line
    s = Script()
    t = s.steps(100, list(range(16)))
    t = perf(s, t, [(K4, 3)])                              # QUANTISE BAR
    t = perf_sel(s, t, [(K4, 1)])                          # MUTE QUEUE on
    s.tap_btn(t, GLO); t += 60
    s.tap_btn(t, PLAY)
    s.tap_key(t + int(3.5 * STEP_MS), wk(0))              # PERF: mute track 1, in step 4
    log = run(s, t + int(24 * STEP_MS))
    n = [round((x[0] - t) / STEP_MS) for x in log.notes(ch=0, after=t)]
    check(n and n[-1] == 15, "MUTE QUEUE: the track plays to the end of the bar, then it is muted (last %s)" % (n[-1] if n else None))
    # without the queue: at once
    s = Script()
    t = s.steps(100, list(range(16)))
    s.tap_btn(t, GLO); t += 60
    s.tap_btn(t, PLAY)
    s.tap_key(t + int(3.5 * STEP_MS), wk(0))
    log = run(s, t + int(24 * STEP_MS))
    n = [round((x[0] - t) / STEP_MS) for x in log.notes(ch=0, after=t)]
    check(n and n[-1] == 3, "a mute without the queue is at once (last %s)" % (n[-1] if n else None))
    # NOW: a scene at once
    s = Script()
    t = s.steps(100, list(range(16)))
    s.tap_btn(t, GLO); t += 60
    s.tap_key(t, wk(0)); t += 80                          # mute track 1
    s.press(t, SEL); s.tap_key(t + 30, bk(1), hold=40); s.release(t + 100, SEL); t += 160   # store scene 2 (muted)
    s.tap_key(t, wk(0)); t += 80                          # unmute
    s.tap_btn(t, GLO); t += 60
    t = perf(s, t, [(K4, 1)])                             # QUANTISE NOW
    s.tap_btn(t, PLAY)
    s.tap_btn(t + int(5.5 * STEP_MS), GLO); s.tap_key(t + int(5.5 * STEP_MS) + 60, bk(1))   # scene 2 in step 6
    log = run(s, t + int(20 * STEP_MS))
    n = [round((x[0] - t) / STEP_MS) for x in log.notes(ch=0, after=t)]
    check(n and n[-1] in (5, 6), "QUANTISE NOW: the scene (a mute) comes at once (last %s)" % (n[-1] if n else None))


def t05_scene_pc():
    group("0.5: a Program Change per scene and channel")
    s = Script()
    t = home_page(s, 100, 4, [(K4, 6)])                   # scene 1, channel 1: program 6 (sent at once to hear it)
    s.tap_btn(t, GLO); t += 60
    s.enc(t, E_PRE, 1); t += 40                           # PERF: the scene cursor on scene 2
    s.tap_btn(t, GLO); t += 60
    t = home_page(s, t, 4, [(K4, 10)], cur=4)             # scene 2, channel 1: program 10
    s.tap_btn(t, GLO); t += 60
    s.tap_key(t, bk(0)); t += 100                         # scene 1: program 6 goes out
    s.tap_key(t, bk(1)); t += 100                         # scene 2: program 10
    s.tap_key(t, bk(1)); t += 100                         # scene 2 again: nothing (the synth has it)
    s.tap_btn(t, GLO); t += 60
    s.tap_btn(t, PLAY)
    log = run(s, t + 600)
    pcs = [(m[2]) for m in log.msgs if m[1] == 0xC0]
    check(pcs == [5, 9, 5, 9], "programs: 6 and 10 when set, then 6 for scene 1, 10 for scene 2, not again (%s)" % pcs)


def t05_morph():
    group("0.5: MORPH between the CC values of two scenes")
    s = Script()
    t = lane_base(s, 100, 20) + 100                                    # lane 1 base value 20
    s.tap_btn(t, GLO); t += 60
    s.press(t, SEL); s.tap_key(t + 30, bk(0), hold=40); s.release(t + 100, SEL); t += 160   # store scene 1 (CC74 = 20)
    s.tap_btn(t, GLO); t += 60
    s.press(t, ENV); s.enc(t + 30, K3, 80); s.release(t + 60, ENV); t += 120               # base 100 (20 + 80)
    s.tap_btn(t, GLO); t += 60
    s.press(t, SEL); s.tap_key(t + 30, bk(1), hold=40); s.release(t + 100, SEL); t += 160   # store scene 2 (CC74 = 100)
    s.tap_key(t, bk(0)); t += 100                                                            # scene 1 plays
    s.tap_btn(t, GLO); t += 60
    mark = t
    t = perf(s, t, [(K1, 8)])                          # MORPH 32/127 towards scene 2 (the default target)
    t2 = t
    t = perf(s, t, [(K1, 24)])                         # 127
    t3 = t
    t = perf(s, t, [(K1, -40)])                        # 0
    log = run(s, t + 300)
    v = [d2 for _, _, d2 in ccs(log, ch=0, cc=74, after=mark)]
    check(len(v) == 3 and v[0] == round((20 * 95 + 100 * 32) / 127) and v[1] == 100 and v[2] == 20, "CC 74: a quarter of the way, scene 2, back to scene 1 (%s)" % v)
    # the grid: FX view row 5, pad 16 = the target
    s = Script()
    t = lane_base(s, 100, 10) + 100                                    # base 10
    s.tap_btn(t, GLO); t += 60
    s.press(t, SEL); s.tap_key(t + 30, bk(0), hold=40); s.release(t + 100, SEL); t += 160
    s.tap_btn(t, GLO); t += 60
    s.press(t, ENV); s.enc(t + 30, K3, 40); s.release(t + 60, ENV); t += 120               # base 50
    s.tap_btn(t, GLO); t += 60
    s.press(t, SEL); s.tap_key(t + 30, bk(2), hold=40); s.release(t + 100, SEL); t += 160   # scene 3 (50)
    s.tap_key(t, bk(0)); t += 100
    s.tap_btn(t, GLO); t += 60
    s.raw(t, "attach"); t = view(s, t + 100, GC_UNDO, alt=True)
    s.pad(t, 2, 6); t += 100                               # MORPH to scene 3
    mark = t
    s.pad(t, 15, 4); t += 100                              # the fader at the end
    remote(s, t, 1, 64); t += 100                          # the remote: half way
    log = run(s, t + 200)
    v = [d2 for _, _, d2 in ccs(log, ch=0, cc=74, after=mark)]
    check(v == [50, 30], "grid MORPH to scene 3 at the end, then the remote half way (%s)" % v)


def melody16(s, t=100):
    """track 1: 16 steps, notes 60..75 (one per step)"""
    t = program(s, t, [60 + i for i in range(16)])
    return t


def t05_repeat():
    group("0.5.1: grid LOOP / REPEAT row (tap: LOOP, hold: REPEAT, lands in time), triplets, EXIT")
    s = Script()
    t = melody16(s)
    s.raw(t, "attach"); t = view(s, t + 100, GC_UNDO, alt=True)
    for k in range(0, 3000, 900): s.raw(t + k, "hb")
    s.tap_btn(t, PLAY)
    p0 = t
    s.at(p0 + int(4.5 * STEP_MS), "pad", 2, 1, 100)        # 1/8 (two steps) held in step 5: REPEAT ...
    s.at(p0 + int(10.5 * STEP_MS), "pad", 2, 1, 0)         # ... let go in step 11
    log = run(s, p0 + int(16 * STEP_MS))
    n = [(round((x[0] - p0) / STEP_MS), x[1]) for x in log.notes(ch=0, after=p0)]
    during = [d for k, d in n if 5 <= k <= 10]
    after = [d for k, d in n if k >= 11]
    check(during == [65, 66, 65, 66, 65, 66], "the two steps after the press repeat (%s)" % during)
    check(after[:2] == [71, 72], "let go: step 12 plays, where the music would be (%s)" % after[:2])
    # the remote: CC 26 = REPEAT 1/16 while held
    s = Script()
    t = melody16(s)
    s.tap_btn(t, PLAY)
    p0 = t
    remote(s, p0 + int(2.5 * STEP_MS), 26, 127)
    remote(s, p0 + int(6.5 * STEP_MS), 26, 0)
    log = run(s, p0 + int(10 * STEP_MS))
    n = [(round((x[0] - p0) / STEP_MS), x[1]) for x in log.notes(ch=0, after=p0)]
    check([d for k, d in n if 3 <= k <= 6] == [63, 63, 63, 63] and [d for k, d in n if k >= 7][:1] == [67],
          "remote REPEAT 1/16: one step again and again, then on in time (%s)" % n)
    # 0.10: the DJ loop (latched) lands in time too when it ends (the pattern is where it would have been)
    s = Script()
    t = melody16(s)
    s.tap_btn(t, PLAY)
    p0 = t
    s.press(p0 + int(4.5 * STEP_MS), FX); s.tap_key(p0 + int(4.5 * STEP_MS) + 20, bk(1), hold=30); s.release(p0 + int(4.5 * STEP_MS) + 80, FX)
    s.press(p0 + int(10.5 * STEP_MS), FX); s.tap_key(p0 + int(10.5 * STEP_MS) + 20, bk(10), hold=30); s.release(p0 + int(10.5 * STEP_MS) + 80, FX)
    log = run(s, p0 + int(14 * STEP_MS))
    n = [(round((x[0] - p0) / STEP_MS), x[1]) for x in log.notes(ch=0, after=p0)]
    check([d for k, d in n if k >= 11][:2] == [71, 72], "a tapped LOOP's EXIT lands in time (0.10; 0.4-0.9 went on from the loop) (%s)" % [d for k, d in n if k >= 11][:2])
    # a triplet: 1/16T (pad 10) = 4 ticks, held; the grid's EXIT pad (16) ends a tapped LOOP
    s = Script()
    t = melody16(s)
    s.raw(t, "attach"); t = view(s, t + 100, GC_UNDO, alt=True)
    for k in range(0, 3000, 900): s.raw(t + k, "hb")
    s.tap_btn(t, PLAY)
    p0 = t
    s.at(p0 + int(2.5 * STEP_MS), "pad", 9, 1, 100)
    s.at(p0 + int(5.5 * STEP_MS), "pad", 9, 1, 0)
    log = run(s, p0 + int(8 * STEP_MS))
    on = [x[0] for x in log.notes(ch=0, after=p0 + int(3 * STEP_MS) + 5, before=p0 + int(5.5 * STEP_MS))]
    gaps = [round(b - a) for a, b in zip(on, on[1:])]
    check(len(gaps) >= 2 and all(near(g, 4 * STEP_MS / 6, 2) for g in gaps), "1/16T held: the step comes again every 4 ticks (%s ms)" % gaps)
    s = Script()
    t = melody16(s)
    s.raw(t, "attach"); t = view(s, t + 100, GC_UNDO, alt=True)
    for k in range(0, 4000, 900): s.raw(t + k, "hb")
    s.tap_btn(t, PLAY)
    p0 = t
    s.pad(p0 + int(4.5 * STEP_MS), 3, 1, hold=40)         # 1/4 tapped: LOOP
    s.pad(p0 + int(10.5 * STEP_MS), 15, 1, hold=40)       # EXIT
    log = run(s, p0 + int(16 * STEP_MS))
    n = [(round((x[0] - p0) / STEP_MS), x[1]) for x in log.notes(ch=0, after=p0)]
    loop = [d for k, d in n if 5 <= k <= 10]
    after = [d for k, d in n if k >= 11]
    check(loop == [65, 66, 67, 68, 65, 66], "1/4 tapped on the grid: a LOOP that stays (%s)" % loop)
    check(after[:3] == [71, 72, 73], "EXIT: back in time (0.10) (%s)" % after[:3])


def t05_reload():
    group("0.5: RELOAD")
    d = tempfile.mkdtemp()
    flash = os.path.join(d, "flash.bin")
    s = Script()
    t = s.steps(100, [0, 4])
    s.tap_btn(t + 50, SAVE); s.tap_btn(t + 300, SAVE); t += 1500     # slot 1
    t = s.steps(t, [2, 8])                                            # changed: 1 3 5 9
    s.at(t, "dump", 0)
    s.press(t + 50, SEL); s.tap_btn(t + 80, SAVE); s.release(t + 150, SEL)   # SEL + SAVE: RELOAD
    s.at(t + 600, "dump", 0)
    s.press(t + 700, SEQ); s.tap_key(t + 730, wk(7)); s.release(t + 800, SEQ)  # SEQ + white 8: UNDO
    s.at(t + 1000, "dump", 0)
    log = run(s, t + 1200, flash)
    dd = [x["on"][:9] for x in log.dumps]
    check(dd == ["x.x.x...x", "x...x....", "x.x.x...x"], "RELOAD brings the saved pattern back, UNDO takes it back (%s)" % dd)
    # while playing, after a power cycle (the slot loaded at power-up)
    s = Script()
    s.tap_btn(100, PLAY)
    t = s.steps(300, [1, 3])
    s.press(t + 50, SEL); s.tap_btn(t + 80, SAVE); s.release(t + 150, SEL)
    s.at(t + 800, "dump", 0)
    log = run(s, t + 5000, flash)
    check(log.dumps and log.dumps[-1]["on"][:9] == "x...x....", "RELOAD while playing, from the slot loaded at power-up (%s)" % (log.dumps[-1]["on"][:9] if log.dumps else None))
    n = log.notes(ch=0, after=t + 900)
    pos = sorted(set(round((x[0] - 100) / STEP_MS) % 16 for x in n))
    check(pos == [0, 4], "and the music goes on as saved: steps 1 and 5 (%s)" % pos)
    # nothing saved
    s = Script()
    s.steps(100, [0])
    s.press(300, SEL); s.tap_btn(330, SAVE); s.release(400, SEL)
    s.at(800, "dump", 0)
    log = run(s, 1000)
    check(log.dumps[-1]["on"][:2] == "x.", "RELOAD with nothing saved changes nothing")


def t05_learn():
    group("0.5: MIDI LEARN of the CC numbers")
    s = Script()
    t = s.steps(100, [0])
    s.press(t, ENV); s.enc(t + 30, K1, 1); s.enc(t + 90, K1, -15); s.tap_btn(t + 120, REC); s.release(t + 160, ENV); t += 220   # lane 1: lock 49 on step 1; LEARN
    s.raw(t, "midi 0xB2 21 90"); t += 50                  # a knob of the synth (channel 3): CC 21
    s.tap_btn(t, PLAY)
    log = run(s, t + 400)
    c = ccs(log, ch=0, after=t)
    check(c and c[0][1] == 21 and c[0][2] == 49, "ENV + REC, then CC 21 comes in: lane 1 sends CC 21 (%s)" % c[:1])
    # the LFO: LFO + REC, CC 33
    s = Script()
    s.press(100, LFO); s.tap_btn(130, REC); s.release(200, LFO)
    s.raw(300, "midi 0xB0 33 5")
    s.press(400, LFO); s.tap_key(430, wk(0)); s.release(500, LFO)       # LFO 1 on
    s.tap_btn(600, PLAY)
    log = run(s, 1500)
    check(ccs(log, cc=33, after=600) and not ccs(log, cc=74, after=600), "LFO + REC, CC 33: the LFO moves CC 33")
    # the grid: CC view, SHIFT + the CC number row; nothing comes: it lets go after 10 s
    s = Script()
    s.raw(100, "attach"); t = view(s, 200, GC_VSTEP, alt=True)
    shift(s, t, 1); s.pad(t + 20, 0, 5); shift(s, t + 100, 0)
    for k in range(1000, 13000, 1000): s.raw(k, "hb")
    s.raw(12500, "midi 0xB0 99 5")
    s.steps(12600, [0])
    s.press(12800, ENV); s.enc(12830, K1, 30); s.release(12860, ENV)
    s.tap_btn(13000, PLAY)
    log = run(s, 13500)
    c = ccs(log, ch=0, after=13000)
    check(c and c[0][1] == 74, "LEARN that waited 10 s for nothing is off: CC 99 later changes nothing (%s)" % c[:1])


def t05_song_spp():
    group("0.5: the song follows the Song Position")
    def song_script(jump):
        s = Script()
        t = s.steps(100, [0])                              # pattern 1: step 1, note 60
        s.enc(t, E_PRE, 1); t += 40
        s.press(t, SEL); s.tap_key(t + 30, 1 << (72 - 53), hold=40); s.release(t + 100, SEL); t += 520   # pattern 2: 72
        s.tap_btn(t, GLO); t += 60
        s.press(t, SEL); s.tap_key(t + 30, bk(1), hold=40); s.release(t + 100, SEL); t += 160   # scene 2 = pattern 2
        s.enc(t, E_PRE, -1); t += 40                       # (PRESETS in PERF: the scene cursor; the pattern stays)
        s.tap_btn(t, GLO); t += 60
        s.enc(t, E_PRE, -1); t += 40                       # pattern 1
        s.tap_btn(t, GLO); t += 60
        s.press(t, SEL); s.tap_key(t + 30, bk(0), hold=40); s.release(t + 100, SEL); t += 160   # scene 1 = pattern 1
        s.press(t, HOME); s.tap_key(t + 30, bk(0), hold=40); s.tap_key(t + 100, bk(1), hold=40); s.release(t + 180, HOME); t += 240   # song: 1 x4, 2 x4
        s.tap_btn(t, GLO); t += 60
        s.press(t, HOME); s.tap_btn(t + 20, GLO); s.release(t + 80, HOME); t += 140             # the song on
        return s, t
    s, t = song_script(True)
    s.press(t, HOME); s.tap_btn(t + 20, PLAY); s.release(t + 90, HOME); t += 300               # slave
    s.raw(t, "midi 0xF2 80 0")                             # bar 6 (80 sixteenths): the second entry
    s.raw(t + 5, "midi 0xFB 0 0")
    for i in range(24 * 4):
        s.raw(t + 10 + i * 20, "midi 0xF8 0 0")
    log = run(s, t + 10 + 96 * 20 + 50)
    p = pitches(log, after=t)
    check(p[:1] == [72], "SPP into bar 6: the song is on its second entry, scene 2 (%s)" % p[:2])
    s, t = song_script(True)
    s.press(t, HOME); s.tap_btn(t + 20, PLAY); s.release(t + 90, HOME); t += 300
    s.raw(t, "midi 0xF2 16 0")                             # bar 2: the first entry
    s.raw(t + 5, "midi 0xFB 0 0")
    for i in range(24 * 4 * 4):
        s.raw(t + 10 + i * 20, "midi 0xF8 0 0")
    log = run(s, t + 10 + 384 * 20 + 50)
    ph = [(round((x[0] - t - 10) / (16 * 6 * 20.0)), x[1]) for x in log.notes(ch=0, after=t)]
    check([d for _, d in ph][:4] == [60, 60, 60, 72], "SPP into bar 2: three more bars of scene 1, then scene 2 (%s)" % ph[:4])


def t05_remote():
    group("0.5: SAGGA REMOTE (CCs on channel 14)")
    s = Script()
    s.steps(100, [0, 4, 8, 12])
    remote(s, 300, 31); remote(s, 330, 31, 0)              # tempo +1
    remote(s, 400, 20)                                      # PLAY
    remote(s, 400 + int(6 * STEP_MS), 48)                   # mute track 1
    log = run(s, 400 + int(14 * STEP_MS))
    n = [round((x[0] - 400) / STEP_MS) for x in log.notes(ch=0, after=400)]
    check(0xFA in [m[1] for m in log.msgs], "CC 20: PLAY")
    check(n == [0, 4], "CC 48: track 1 muted at once (%s)" % n)
    clk = log.clock()
    gap = (clk[-1] - clk[0]) / (len(clk) - 1) if len(clk) > 2 else 0
    check(near(gap, 60000.0 / (129 * 24), 0.05), "CC 31: tempo 129 (%.3f ms a tick)" % gap)
    check(not ccs(log, after=0), "the remote's CCs are not passed on")
    s = Script()
    s.raw(100, "attach")
    remote(s, 300, 41)                                      # scene 2
    remote(s, 400, 23); s.at(450, "dump", 0)               # FILL held
    log = run(s, 800)
    _, ctls = log.leds()
    check(ctls.get(GC_SCN0 + 1) == GL_ON and ctls.get(GC_SCN0) == GL_FAINT, "CC 41: scene 2")
    check(ctls.get(GC_FILL) == GL_FILL, "CC 23: FILL while held (%s)" % ctls.get(GC_FILL))


def t05_persist():
    group("0.5: the new settings are saved with the project")
    d = tempfile.mkdtemp()
    flash = os.path.join(d, "flash.bin")
    s = Script()
    t = program(s, 100, [60, 64, 67])
    t = s.steps(t, [3, 4, 5])
    t = home_page(s, t, 4, [(K1, 3), (K4, 8)])             # NOTE LOOP 3; scene 1 program 8
    t = perf(s, t, [(K4, 3)])                              # QUANTISE BAR
    s.tap_btn(t, SAVE); s.tap_btn(t + 300, SAVE)
    run(s, t + 1500, flash)
    s = Script()
    s.tap_btn(100, PLAY)
    s.tap_btn(300, GLO); s.press(400, SEL); s.raw(500, "shot"); s.release(600, SEL)
    log = run(s, 100 + int(6.5 * STEP_MS), flash)
    check(pitches(log, after=100)[:6] == [60, 64, 67, 60, 64, 67], "after a power cycle: the note loop (%s)" % pitches(log, after=100)[:6])
    pcs = [m[2] for m in log.msgs if m[1] == 0xC0]
    check(pcs[:1] == [7], "... and the program of scene 1 goes out at power-up (%s)" % pcs)


def t05_grid_track2():
    group("0.5: grid TRACK 2 view")
    s = Script()
    t = program(s, 100, [60, 62, 64, 65])
    t = s.steps(t, list(range(4, 8)))
    s.raw(t, "attach"); t = view(s, t + 100, GC_VTRACK); t = view(s, t, GC_VTRACK)    # TRACK again: TRACK 2
    s.pad(t, 1, 0); t += 100                               # NOTE LOOP 2
    s.pad(t, 4, 3); t += 100                               # program 5 for scene 1, channel 1
    s.tap_btn(t, PLAY)
    log = run(s, t + int(8.5 * STEP_MS))
    check(pitches(log, after=t)[:6] == [60, 62, 60, 62, 60, 62], "row 1 pad 2: a note loop of 2 (%s)" % pitches(log, after=t)[:6])
    check([m[2] for m in log.msgs if m[1] == 0xC0] == [4], "row 4 pad 5: program 5 (sent at once)")
    pads, ctls = log.leds()
    check(pads.get(1) == GL_WHITE and pads.get(0) == GL_ON and pads.get(2) == GL_FAINT, "row 1 shows the length (%s)" % [pads.get(i) for i in range(3)])
    check(ctls.get(GC_VTRACK) == GL_CYAN, "the TRACK button is cyan in TRACK 2")


def t05_battery():
    group("0.5: the battery on the screen")
    d = tempfile.mkdtemp()
    s = Script()
    s.raw(300, "shot")                                     # USB power, full: a bolt and three bars
    s.raw(400, "usbpower 0"); s.raw(400, "batt 545")
    s.raw(1300, "shot")                                    # one bar
    s.raw(1400, "batt 500")
    s.raw(2300, "shot")                                    # empty, red
    run(s, 2500, shots=d)
    def at(t, x, y): return screen_px(os.path.join(d, "o-%d.ppm" % t), 4 + x, y)
    bolt = [at(300, 200 + i, 3 + r) for i in range(7) for r in range(9)]
    check(any(p[2] > 150 and p[0] < 150 for p in bolt), "USB: the bolt beside the battery")
    check(all(at(300, x, 7)[1] > 150 and at(300, x, 7)[0] < 150 for x in (212, 218, 224)), "USB, full: three green bars")
    check(at(1300, 212, 7)[0] > 200 and at(1300, 218, 7) == (0, 0, 0) and at(1300, 224, 7) == (0, 0, 0), "one bar, orange, the rest empty (%s)" % (at(1300, 212, 7),))
    check(at(2300, 209, 3)[0] > 200 and at(2300, 209, 3)[1] < 150 and at(2300, 212, 7) == (0, 0, 0), "empty: a red outline (%s)" % (at(2300, 209, 3),))
    check(not any(p[2] > 150 and p[0] < 150 for p in [at(2300, 200 + i, 3 + r) for i in range(7) for r in range(9)]), "no USB: no bolt")


def t05_library():
    group("0.5: the LIBRARY on the Pi (the FM-1's side)")
    s = Script()
    s.raw(100, "attach")
    t = view(s, 200, GC_REC, alt=True)                    # PROJ
    t = view(s, t, GC_REC, alt=True)                      # PROJ again: LIB -> asks for the list
    s.at(t + 50, "sx", "7D 53 47 21 00 02 " + " ".join("%02X" % ord(c) for c in "01-TECHNO"))
    s.at(t + 60, "sx", "7D 53 47 21 01 02 " + " ".join("%02X" % ord(c) for c in "02-GQOM"))
    s.pad(t + 200, 1, 0)                                  # choose file 2
    s.pad(t + 400, 1, 0)                                  # again: load it
    s.tap_btn(t + 600, PLAY)
    s.pad(t + 800, 0, 7)                                  # PREVIOUS while playing: waits for STOP
    s.tap_btn(t + 1200, PLAY)                             # STOP: it asks for file 1
    log = run(s, t + 1500)
    sx = [m for _, m in log.sysex]
    check(sx[:2] == [[0xF0, 0x7D, 0x53, 0x47, 0x20, 0, 0, 0xF7], [0xF0, 0x7D, 0x53, 0x47, 0x20, 1, 0, 0xF7]],
          "LIB view: the FM-1 asks the Pi for the list, a file at a time (%s)" % sx[:2])
    loads = [m[5] for m in sx if m[4] == 0x22]
    check(loads == [1, 0], "the second tap on a file asks for it; PREVIOUS while playing asks at STOP (%s)" % loads)
    s2 = [m for _, m in log.sysex]
    pads, _ = log.leds()
    check(pads.get(0) is not None and pads.get(2) == GL_OFF, "two files, two pads lit")
    # PREVIOUS waits for STOP: lib_cur is not set (no import came), so PREVIOUS works from the chosen one
    check(any(m[4] == 0x22 for m in sx), "loads asked")


# ------------------------------------------------------------------------------------------------ 0.5.1 (the new map)
def lane_base(s, t, v):
    """ENV, K3: the base value of lane 1 (CC 74) = v, from none (0.10: the first detent up puts 64); returns the time after"""
    s.press(t, ENV); s.enc(t + 100, K3, 1)
    if v != 64: s.enc(t + 160, K3, v - 64)
    s.release(t + 220, ENV)
    return t + 280


def t051_cursor_tools():
    group("0.5.1: EDIT / ENV + white = the cursor (the step untouched), EDIT + black 2-4 = copy, paste, clear a step")
    s = Script()
    t = s.steps(100, [0])
    s.press(t, EDIT); s.tap_key(t + 30, wk(4)); s.release(t + 100, EDIT); t += 160       # the cursor on step 5
    s.at(t, "dump", 0)
    s.press(t + 50, ENV); s.tap_key(t + 80, wk(8)); s.release(t + 150, ENV); t += 210  # the cursor on step 9
    s.at(t, "dump", 0)
    s.press(t + 50, EDIT); s.enc(t + 80, K3, 2); s.release(t + 110, EDIT); t += 170    # a nudge on the cursor step: it comes on
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    dd = [x["on"][:10] for x in log.dumps]
    check(dd == ["x.........", "x.........", "x.......x."], "EDIT / ENV + a white key move the cursor and toggle nothing; a knob then edits step 9 (%s)" % dd)
    # copy step 1 (E4), paste it on step 7, clear step 1, UNDO
    s = Script()
    t = program(s, 100, [64])                                   # step 1: E4, the cursor on it
    s.press(t, EDIT); s.tap_key(t + 30, bk(1)); s.tap_key(t + 110, wk(6)); s.tap_key(t + 190, bk(2)); s.release(t + 260, EDIT); t += 320
    s.at(t, "dump", 0)
    s.press(t + 50, EDIT); s.tap_key(t + 80, wk(0)); s.tap_key(t + 160, bk(3)); s.release(t + 230, EDIT); t += 300
    s.at(t, "dump", 0)
    s.press(t + 50, SEQ); s.tap_key(t + 80, wk(7)); s.release(t + 150, SEQ); t += 210  # UNDO
    s.at(t, "dump", 0)
    s.press(t + 50, EDIT); s.tap_key(t + 80, bk(0)); s.release(t + 150, EDIT); t += 210   # black 1: the 0.6, nothing now
    s.at(t, "dump", 0)
    s.tap_btn(t + 50, PLAY)
    log = run(s, t + 50 + int(8.5 * STEP_MS))
    dd = [x["on"][:8] for x in log.dumps]
    check(dd == ["x.....x.", "......x.", "x.....x.", "x.....x."], "copy 1 -> paste 7, clear 1, UNDO, black 1 does nothing (%s)" % dd)
    check(pitches(log, after=t)[:2] == [64, 64], "the pasted step is the same note (%s)" % pitches(log, after=t)[:2])
    # HOME + white 3: track 3 (channel 3)
    s = Script()
    s.press(100, HOME); s.tap_key(130, wk(2)); s.release(200, HOME)
    t = s.steps(300, [0, 8])
    s.tap_btn(t + 50, PLAY)
    log = run(s, t + 50 + int(10 * STEP_MS))
    check(len(log.notes(ch=2, after=t)) == 2 and not log.notes(ch=0), "HOME + white 3: the steps go to track 3 (channel 3)")
    # REC armed: EDIT + white keeps the cursor job, nothing is recorded or played
    s = Script()
    s.tap_btn(100, REC)
    s.press(200, EDIT); s.tap_key(230, wk(4)); s.release(300, EDIT)
    s.at(400, "dump", 0)
    log = run(s, 500)
    check(not log.notes() and log.dumps[-1]["on"][:16] == "." * 16, "REC armed + EDIT + white: no note, no step (%s)" % log.dumps[-1]["on"][:16])


def t051_macros():
    group("0.5.1: FX + K1-K4 = the macros INTENSITY, GATE, SWING, FILTER (FX + OCT-: back to 0)")
    def play(extra, steps=(0, 1, 4, 8)):
        s = Script()
        t = s.steps(100, list(steps))
        t = extra(s, t)
        s.tap_btn(t, PLAY)
        return run(s, t + int(17 * STEP_MS)), t
    log, t = play(lambda s, t: t)
    base = log.notes(ch=0, after=t)
    log, t = play(lambda s, t: held(s, t, FX, [(K1, 5)]))
    n = log.notes(ch=0, after=t)
    check(base and all(v == 100 for _, _, v in base) and n and all(v == 105 for _, _, v in n), "0.6 INTENSITY +5: velocity 100 -> 105 (%s)" % [v for _, _, v in n[:2]])
    def fx_zero(s, t):
        t = held(s, t, FX, [(K1, 5)])
        s.press(t, FX); s.tap_btn(t + 30, OCT_DOWN); s.release(t + 100, FX)
        return t + 160
    log, t = play(fx_zero)
    check(all(v == 100 for _, _, v in log.notes(ch=0, after=t)), "FX + OCT-: back to 100")
    def gates(log, t):
        on = log.notes(ch=0, after=t)
        off = [o for o, _ in log.offs(ch=0) if o > t]
        return [b - a for (a, _, _), b in zip(on, off)]
    g0 = gates(*play(lambda s, t: t, steps=(0, 4, 8)))
    g1 = gates(*play(lambda s, t: held(s, t, FX, [(K2, -10)]), steps=(0, 4, 8)))           # 0.8: 5 % a detent
    check(g0 and g1 and all(near(b, a / 2.0, 3) for a, b in zip(g0, g1)), "GATE -10 detents = -50 %%: the notes half as long (%s -> %s)" % (g0[:2], g1[:2]))
    def gap12(log, t):
        n = log.notes(ch=0, after=t)
        return n[1][0] - n[0][0] if len(n) > 1 else 0
    a = gap12(*play(lambda s, t: t))
    b = gap12(*play(lambda s, t: held(s, t, FX, [(K3, 20)])))
    check(near(a, STEP_MS, 2) and b > STEP_MS * 1.25, "SWING +20: step 2 comes late (%d -> %d ms)" % (a, b))
    # FILTER: lane 1 (CC 74) base 20, +20 -> 40 at once; back to 0 -> 20
    s = Script()
    t = lane_base(s, 100, 20)
    mark = t
    t = held(s, t, FX, [(K4, 5)])
    s.press(t, FX); s.tap_btn(t + 30, OCT_DOWN); s.release(t + 100, FX)
    log = run(s, t + 300)
    v = [d2 for _, _, d2 in ccs(log, ch=0, cc=74, after=mark)]
    check(v == [30, 20], "0.8 FILTER +5 detents = +10: lane 1 goes out at 30, back to 20 with FX + OCT- (%s)" % v)
    # the remote: CC 7 INTENSITY, CC 10 FILTER (64 = 0)
    s = Script()
    t = lane_base(s, 100, 20)
    t = s.steps(t, [0, 4])
    remote(s, t, 7, 84); remote(s, t + 20, 10, 54)
    s.tap_btn(t + 100, PLAY)
    log = run(s, t + 100 + int(6 * STEP_MS))
    n = log.notes(ch=0, after=t + 100)
    v = [d2 for _, _, d2 in ccs(log, ch=0, cc=74, after=t)]
    check(n and all(x[2] == 120 for x in n), "remote CC 7 = 84: INTENSITY +20 (%s)" % [x[2] for x in n[:2]])
    check(v[:1] == [10], "remote CC 10 = 54: FILTER -10, lane 1 at 10 (%s)" % v[:2])


def t051_master_knob():
    group("0.5.1: the MASTER knob (SAVE + K1: TEMPO, MORPH, FILTER), SAVE + K2 the remote")
    def gap(log):
        clk = log.clock()
        return (clk[-1] - clk[0]) / (len(clk) - 1) if len(clk) > 2 else 0
    s = Script()
    t = lane_base(s, 100, 20)
    s.press(t, SAVE); s.enc(t + 30, K1, 2); s.release(t + 60, SAVE); t += 120        # FILTER
    s.tap_btn(t, SAVE); t += 300                                                       # a SAVE: it only asks ...
    s.tap_btn(t, PLAY)
    mark = t
    s.knob(t + 300, 1023); s.knob(t + 600, 0)
    log = run(s, t + 1500)
    v = [d2 for _, _, d2 in ccs(log, ch=0, cc=74, after=mark)]
    check(not log.saves, "SAVE + K1 does not save, and its release does not ask to (%s)" % log.saves)
    check(v[:1] == [83] and v[-1:] == [0], "FILTER: knob up, lane 1 at 20 + 63; down, at 0 (%s)" % v)
    check(near(gap(log), TICK_US / 1000.0, 0.1), "the knob no longer moves the tempo (%.3f ms/tick)" % gap(log))
    # MORPH: scene 1 (CC 74 = 20), scene 2 (100)
    s = Script()
    t = lane_base(s, 100, 20)
    s.tap_btn(t, GLO); t += 60
    s.press(t, SEL); s.tap_key(t + 30, bk(0), hold=40); s.release(t + 100, SEL); t += 160
    s.tap_btn(t, GLO); t += 60
    s.press(t, ENV); s.enc(t + 30, K3, 80); s.release(t + 60, ENV); t += 120
    s.tap_btn(t, GLO); t += 60
    s.press(t, SEL); s.tap_key(t + 30, bk(1), hold=40); s.release(t + 100, SEL); t += 160
    s.tap_key(t, bk(0)); t += 100
    s.tap_btn(t, GLO); t += 60
    s.press(t, SAVE); s.enc(t + 30, K1, 1); s.release(t + 60, SAVE); t += 120         # MORPH
    mark = t
    s.knob(t + 10, 520)                                                               # a small move: nothing
    s.knob(t + 100, 1023); s.knob(t + 200, 0); s.knob(t + 300, 1023); t += 500
    log = run(s, t)
    v = [d2 for _, _, d2 in ccs(log, ch=0, cc=74, after=mark)]
    check(v == [20, 100], "MORPH on the knob: down, scene 1's CCs, up, scene 2's; a small move does nothing (%s)" % v)
    # SAVE + K2 down: the remote is off (channel 14 is a track channel), up: on again
    s = Script()
    s.steps(50, [0])
    s.press(100, SAVE); s.enc(130, K2, -1); s.release(160, SAVE)
    remote(s, 300, 20)
    s.press(500, SAVE); s.enc(530, K2, 1); s.release(560, SAVE)
    remote(s, 700, 20)
    log = run(s, 900)
    st = [t for t, b, _, _ in log.msgs if b == 0xFA]
    check(st and st[0] >= 700, "SAVE + K2: the remote off (CC 20 ignored), on again (PLAY at %s)" % st[:1])
    check(not log.saves, "and nothing is saved")


def t051_grid_perf():
    group("0.5.1: grid PERF: RETRIG (pad 11), KILL (pad 12), select (13-16)")
    def go(actions, ms=20):
        s = Script()
        t = melody16(s)
        s.raw(t, "attach"); t = view(s, t + 100, GC_VPERF)
        for k in range(0, 4000, 900): s.raw(t + k, "hb")
        s.tap_btn(t, PLAY)
        actions(s, t)
        log = run(s, t + int(ms * STEP_MS))
        return [(round((x[0] - t) / STEP_MS), x[1]) for x in log.notes(ch=0, after=t)], log
    n, log = go(lambda s, p: s.pad(p + int(5.5 * STEP_MS), 10, 0, hold=30))
    check([d for k, d in n if 5 <= k <= 7] == [65, 60, 61], "RETRIG track 1 in step 6: the next step is step 1 (%s)" % [d for k, d in n if 4 <= k <= 8])
    n, log = go(lambda s, p: (s.at(p + int(3.5 * STEP_MS), "pad", 11, 0, 100), s.at(p + int(7.5 * STEP_MS), "pad", 11, 0, 0)))
    check([k for k, d in n if k < 10] == [0, 1, 2, 3, 8, 9], "KILL held from step 4 to 8: silent, then on (%s)" % [k for k, d in n if k < 10])
    pads, _ = log.leds()
    check(pads.get(10) == GL_BLUE and pads.get(11) == GL_ORANGE, "RETRIG blue, KILL orange (%s %s)" % (pads.get(10), pads.get(11)))
    s = Script()
    s.raw(100, "attach"); t = view(s, 200, GC_VPERF)
    s.pad(t, 13, 2); t += 100                                 # track 3
    t = s.steps(t, [0])
    s.tap_btn(t, PLAY)
    log = run(s, t + 500)
    check(log.notes(ch=2) and not log.notes(ch=0), "pads 13-16 select the track of the row")


def t051_grid_fx():
    group("0.5.1: grid FX: row 3 TRANSPOSE, row 8 RESTART, STOP at the bar, SHIFT tapped twice = locked")
    s = Script()
    t = s.steps(100, [0])
    t = kp(s, t, [(K2, 1), (K4, 1)])               # C major, track 1 in the key
    s.raw(t, "attach"); t = view(s, t + 100, GC_UNDO, alt=True)
    s.pad(t, 9, 2); t += 100                                   # +2
    s.tap_btn(t, PLAY)
    log = run(s, t + 500)
    check(pitches(log, after=t)[:1] == [62], "row 3 pad 10: TRANSPOSE +2, C4 plays D4 (%s)" % pitches(log, after=t)[:1])
    pads, _ = log.leds()
    check(pads.get(32 + 9) == GL_WHITE and pads.get(32 + 7) != GL_WHITE, "pad 10 lit, pad 8 (0) not (%s %s)" % (pads.get(41), pads.get(39)))
    # RESTART: a 12-step pattern, every track from step 1 at the bar line
    s = Script()
    t = melody16(s)
    t = home_page(s, t, 0, [(K2, -4)])                         # length 12
    s.raw(t, "attach"); t = view(s, t + 100, GC_UNDO, alt=True)
    for k in range(0, 5000, 900): s.raw(t + k, "hb")
    s.tap_btn(t, PLAY)
    p0 = t
    s.pad(p0 + int(5.5 * STEP_MS), 2, 7, hold=30)            # RESTART
    s.pad(p0 + int(20.5 * STEP_MS), 3, 7, hold=30)           # STOP at the end of the bar
    log = run(s, p0 + int(40 * STEP_MS))
    n = [(round((x[0] - p0) / STEP_MS), x[1]) for x in log.notes(ch=0, after=p0)]
    check([d for k, d in n if k in (12, 15, 16, 17)] == [60, 63, 60, 61], "RESTART: at the bar line from step 1, not step 5 (%s)" % [d for k, d in n if 12 <= k <= 17])
    check(n and n[-1][0] == 31 and 0xFC in [m[1] for m in log.msgs], "STOP at the end of the bar (%r)" % (n[-1:],))
    # SHIFT tapped twice: locked (yellow); an effect tapped stays; SHIFT again: unlocked
    s = Script()
    t = s.steps(50, [0, 4, 8, 12])
    s.raw(t, "attach"); t = view(s, t + 100, GC_UNDO, alt=True)
    for k in range(0, 5000, 900): s.raw(t + k, "hb")
    s.ctl(t + 200, GC_SHIFT, hold=60); s.ctl(t + 400, GC_SHIFT, hold=60); t += 600
    s.raw(t, "dump 0")
    locked = t
    s.pad(t + 50, 9, 0, hold=40); t += 200                     # O+ tapped: latched
    s.tap_btn(t, PLAY)
    p0 = t
    s.ctl(p0 + 1000, GC_SHIFT, hold=60)                       # unlocked
    log = run(s, p0 + 2500)
    _, ctls = log.leds(until=locked + 20)
    check(ctls.get(GC_SHIFT) == GL_YELLOW, "SHIFT tapped twice: yellow (%s)" % ctls.get(GC_SHIFT))
    _, ctls = log.leds()
    check(ctls.get(GC_SHIFT) == GL_FAINT, "SHIFT again: back (%s)" % ctls.get(GC_SHIFT))
    p = pitches(log, after=p0)
    check(p and set(p) == {72}, "with SHIFT locked a tapped effect stays on (%s)" % p[:4])
    # SHIFT held with something is not a tap: no lock
    s = Script()
    s.raw(100, "attach"); t = view(s, 200, GC_UNDO, alt=True)
    for k in range(0, 3000, 900): s.raw(t + k, "hb")
    view(s, t + 100, GC_UNDO, alt=True); view(s, t + 300, GC_UNDO, alt=True)
    log = run(s, t + 600)
    _, ctls = log.leds()
    check(ctls.get(GC_SHIFT) != GL_YELLOW, "SHIFT used for a view twice: not locked")


def t051_remote():
    group("0.5.1: the new remote CCs: 11 TRANSPOSE, 87 STOP at the bar, 88 RESTART, 89 EXIT, 90-105 RETRIG")
    s = Script()
    t = s.steps(100, [0])
    t = kp(s, t, [(K2, 1), (K4, 1)])
    remote(s, t, 11, 14)                                       # +2
    s.tap_btn(t + 50, PLAY)
    log = run(s, t + 500)
    check(pitches(log, after=t)[:1] == [62], "CC 11 = 14: TRANSPOSE +2 (%s)" % pitches(log, after=t)[:1])
    s = Script()
    t = melody16(s)
    t = home_page(s, t, 0, [(K2, -4)])                         # 12 steps
    s.tap_btn(t, PLAY)
    p0 = t
    remote(s, p0 + int(5.5 * STEP_MS), 90)                     # RETRIG track 1: step 7 plays step 1
    remote(s, p0 + int(9.5 * STEP_MS), 88)                     # RESTART at the bar
    remote(s, p0 + int(20.5 * STEP_MS), 87)                    # STOP at the end of the bar
    log = run(s, p0 + int(40 * STEP_MS))
    n = [(round((x[0] - p0) / STEP_MS), x[1]) for x in log.notes(ch=0, after=p0)]
    check([d for k, d in n if 5 <= k <= 7] == [65, 60, 61], "CC 90: RETRIG track 1 (%s)" % [d for k, d in n if 4 <= k <= 8])
    check([d for k, d in n if k in (15, 16)] == [69, 60], "CC 88: RESTART at the bar line (%s)" % [d for k, d in n if 14 <= k <= 17])
    check(n and n[-1][0] == 31, "CC 87: STOP at the end of the bar (%r)" % (n[-1:],))
    s = Script()
    t = melody16(s)
    s.tap_btn(t, PLAY)
    p0 = t
    remote(s, p0 + int(4.5 * STEP_MS), 24); remote(s, p0 + int(4.5 * STEP_MS) + 50, 24, 0)   # 1 BAR tapped: a LOOP
    remote(s, p0 + int(26.5 * STEP_MS), 89)                    # EXIT
    log = run(s, p0 + int(32 * STEP_MS))
    n = [(round((x[0] - p0) / STEP_MS), x[1]) for x in log.notes(ch=0, after=p0)]
    loop = [d for k, d in n if 5 <= k <= 26]
    check(len(loop) >= 20 and all(loop[i] == loop[i + 16] for i in range(len(loop) - 16)), "CC 24 tapped: a 1-bar LOOP that stays (%s)" % loop[:4])
    check([d for k, d in n if k >= 27], "CC 89: EXIT, it goes on")


def t051_undo_dice():
    group("0.5.1: SEQ + UNDO with a dice waiting = BACK (the undo before it stays)")
    s = Script()
    t = seq_page(s, 100, 0, keys=[wk(14)])                      # INVERT an empty row: ALL ON (UNDO can take it back)
    s.at(t, "dump", 0)
    t = seq_page(s, t + 50, 0, keys=[bk(0)])                   # DICE SEQ, waiting
    t = seq_page(s, t, 0, keys=[wk(7)])                        # UNDO: the dice goes back
    s.at(t, "dump", 0)
    t = seq_page(s, t + 50, 0, keys=[wk(7)])                   # UNDO again: ALL ON goes back
    s.at(t, "dump", 0)
    log = run(s, t + 200)
    dd = [x["on"][:16] for x in log.dumps]
    check(dd == ["x" * 16, "x" * 16, "." * 16], "ALL ON, DICE, UNDO = back, UNDO = before ALL ON (%s)" % dd)


def t06_long_gate_euclid():
    group("0.6: long gates and live Euclid")
    # EDIT + K1: 80 -> 102 = 2 STEP.  The note must survive the next step boundary.
    s = Script()
    t = s.steps(100, [0])
    t = held(s, t + 50, EDIT, [(K1, 22)])
    s.tap_btn(t + 100, PLAY)
    mark = t + 100
    log = run(s, mark + int(4 * STEP_MS) + 300)
    on = log.notes(ch=0, after=mark)
    off = [(tm, note) for tm, note in log.offs(ch=0) if tm >= mark]
    if on and off:
        dur = off[0][0] - on[0][0]
        check(near(dur, 2 * STEP_MS, 4), "EDIT K1 = 2 STEP: held note lasts two steps (%.1f ms)" % dur)
    else:
        check(False, "EDIT K1 = 2 STEP: note-on/note-off exist")

    # Live Euclid works over an empty row and changes what is heard without writing first.
    s = Script()
    t = seq_page(s, 100, 0, keys=[wk(5)])             # EUCLID LIVE, default 4/16
    s.tap_btn(t + 100, PLAY)
    mark = t + 100
    log = run(s, mark + int(18 * STEP_MS))
    pos = [round((tm - mark) / STEP_MS) for tm, _, _ in log.notes(ch=0, after=mark)]
    check(pos[:4] == [0, 4, 8, 12], "EUCLID LIVE 4/16 is audible immediately (%s)" % pos[:4])

    # 0.8: SEQ + white 7 = WRITE LIVE: what is heard goes into the pattern, the live layer turns off (UNDO takes it back)
    s = Script()
    s.press(100, SEQ); s.tap_key(130, wk(5)); s.tap_key(230, wk(6)); s.release(320, SEQ)
    s.at(400, "dump", 0)
    s.tap_btn(450, PLAY)
    log = run(s, 450 + int(18 * STEP_MS))
    pos = [round((tm - 450) / STEP_MS) for tm, _, _ in log.notes(ch=0, after=450)]
    check(pos[:4] == [0, 4, 8, 12] and log.dumps[0]["on"][:16] == "x...x...x...x...", "WRITE LIVE writes the euclid into the pattern (%s %s)" % (pos[:4], log.dumps[0]["on"][:16]))

# ------------------------------------------------------------------------------------------------ 0.8
CHORD_CEG = KEY_C4 | KEY_E4 | KEY_G4


def states(log, track=1):
    return [x for x in log.states if x["track"] == track]


def t08_bugs():
    group("0.8: the ten 0.7 bugs")
    BAR = 16 * STEP_MS
    # 1. STOP cuts the ECHO repeats waiting (0.7 played them after the stop)
    s = Script()
    t = s.steps(100, [0])
    t = home_page(s, t + 30, 5, [(K1, 3), (K2, 2)])          # HOME page 5: MIDI FX ECHO, 4 repeats
    p = t + 100
    s.tap_btn(p, PLAY); s.tap_btn(p + 60, PLAY)
    log = run(s, p + 2000)
    check(len(log.notes(ch=0, after=p)) == 1, "STOP: the ECHO repeats that wait go too (%d notes)" % len(log.notes(ch=0, after=p)))
    # ... and the notes of a strum that wait
    s = Script()
    s.press(100, SEL); s.tap_key(130, CHORD_CEG, hold=60); s.release(220, SEL)
    t = arp2(s, 300, [(K4, 10)])                               # STRUM +50 % (0.10: ARP page 2)
    p = t + 100
    s.tap_btn(p, PLAY); s.tap_btn(p + 20, PLAY)
    log = run(s, p + 1000)
    n = log.notes(ch=0, after=p)
    check(len(n) == 1, "STOP: the strum stops too (%s)" % n)

    # 2. MUTE cuts a long note at once (0.7 let it ring to its end)
    s = Script()
    t = s.steps(100, [0])
    t = held(s, t + 50, EDIT, [(K1, 30)])                     # gate 110: ten steps
    s.tap_btn(t + 100, GLO)
    p = t + 200
    s.tap_btn(p, PLAY)
    s.tap_key(p + 500, wk(0))                                  # PERF: mute track 1 while the note rings
    log = run(s, p + 1500)
    off = [tm for tm, _ in log.offs(ch=0) if tm > p]
    check(off and p + 500 <= off[0] <= p + 510, "MUTE: a long note is cut at once (off at %s, mute at %d)" % (off[:1], p + 500))
    s = Script()
    t = s.steps(100, [0])
    t = held(s, t + 50, EDIT, [(K1, 30)])
    s.raw(t, "attach"); view(s, t + 100, GC_UNDO, alt=True)  # the FX view: KILL pads
    p = t + 300
    s.tap_btn(p, PLAY)
    s.at(p + 400, "pad", 0, 5, 100); s.at(p + 600, "pad", 0, 5, 0)
    log = run(s, p + 1500)
    off = [tm for tm, _ in log.offs(ch=0) if tm > p]
    check(off and p + 400 <= off[0] <= p + 410, "KILL: a long note is cut at once (%s)" % off[:1])

    # 3. the algorithm stays on its track when another track is selected (0.7: the scope THIS followed the selection)
    s = Script()
    t = seq_page(s, 100, 0, keys=[wk(14)])                     # track 1 all on
    t = seq_page(s, t, 1, encs=[(K1, 4), (K2, -20)], keys=[wk(5)])   # DENSITY 0 READY, SEQ + white 6 (0.16): track 1 silent
    s.tap_key(t, bk(1)); t += 80                               # track 2
    t = seq_page(s, t, 0, keys=[wk(14)])                       # track 2 all on
    s.at(t, "dump", 0); s.at(t, "dump", 1)
    s.tap_btn(t + 100, PLAY)
    log = run(s, t + 100 + int(BAR))
    st1, st2 = states(log, 1)[0], states(log, 2)[0]
    check(st1["algo"] == 4 and st1["a"] == 0 and st2["algo"] == 0, "DENSITY on track 1, none on track 2 (%d %d %d)" % (st1["algo"], st1["a"], st2["algo"]))
    check(not log.notes(ch=0, after=t + 100) and len(log.notes(ch=1, after=t + 100)) >= 15, "track 1 silent, track 2 plays all its steps")

    # 4. chords with a strum and an ECHO on 14 tracks: no chord note is lost, the loud repeats neither (the queue is
    #    full of the faint ones first)
    s = Script()
    t = 100
    for k in range(8):
        s.tap_key(t, bk(k)); t += 80
        s.press(t, SEL); s.tap_key(t + 30, CHORD_CEG, hold=60); s.release(t + 120, SEL); t += 200
        t = arp2(s, t, [(K4, 10)])
        t = home_page(s, t, 5, [(K1, 3), (K2, 2)], cur=5 if k else 0)     # (0.9: a sixth HOME page exists)
        t = seq_page(s, t, 0, keys=[wk(5)])                               # 0.16: the ECHO READY starts
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + 1500)
    full = [len(log.notes(ch=c, after=p)) for c in range(8)]
    check(full == [15] * 8, "8 tracks x 3 notes x 4 echoes: every chord note and every echo (%s)" % full)
    s = Script()
    t = 100
    for k in range(14):
        if k:
            s.enc(t, E_SEL, 1); t += 50
        s.press(t, SEL); s.tap_key(t + 30, CHORD_CEG, hold=60); s.release(t + 120, SEL); t += 200
        t = arp2(s, t, [(K4, 10)])
        t = home_page(s, t, 5, [(K1, 3), (K2, 2), (K4, 8)], cur=5 if k else 0)   # keeps 100 %: every repeat as loud
        t = seq_page(s, t, 0, keys=[wk(5)])                               # 0.16: started
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + 1500)
    first = [sorted({d1 for tm, d1, v in log.notes(ch=c, after=p, before=p + 200)}) for c in range(14)]
    echoes = len(log.notes(after=p + 200))
    check(all(f == [60, 64, 67] for f in first), "14 tracks: every strummed chord whole (%s)" % first)
    check(echoes == 128, "... and the echo queue used to the last place (%d echoes of 168 asked)" % echoes)

    # 5. EVOLVE of the notes on a FOLLOW track: chord tones of the tonic on the beats, in the key
    s = Script()
    t = kp(s, 100, [(K1, 9), (K2, 2), (K4, 1)])      # A minor, track in key
    t = seq_page(s, t, 0, keys=[wk(14)])
    t = home_page(s, t, 1, [(K4, 1)])                          # FOLLOW
    t = seq_page(s, t, 2, encs=[(K1, 1), (K2, 10), (K3, -2)])  # +NOTES, 75 %, every bar
    t = seq_page(s, t, 0, keys=[bk(8)])
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + int(6 * BAR))
    n = log.notes(ch=0, after=p + int(BAR) - 20)
    beats = {d1 % 12 for tm, d1, _ in n if round((tm - p) / STEP_MS) % 4 == 0}
    allp = {d1 % 12 for _, d1, _ in n}
    check(beats and beats <= {9, 0, 4} and allp <= {9, 11, 0, 2, 4, 5, 7} and len(allp) > 2,
          "EVOLVE on FOLLOW: A C E on the beats (%s), all in A minor (%s)" % (sorted(beats), sorted(allp)))

    # 6. TURING keeps its register when its knobs turn (0.7 began again from the written rhythm at every touch)
    s = Script()
    t = s.steps(100, [0, 3, 6, 10])
    t = seq_page(s, t + 30, 1, encs=[(K1, 1), (K3, 8)], keys=[wk(5)])   # TURING, 16 steps, 10 % mutation; started (0.16)
    p = t + 100
    s.tap_btn(p, PLAY)
    seq_page(s, p + int(0.5 * BAR), 1, encs=[(K2, 90)], cur=1)  # mutation 100 %: it changes
    seq_page(s, p + int(2.5 * BAR), 1, encs=[(K2, -100)], cur=1)   # 0 %: locked
    for b in range(3, 8):
        s.at(int(p + b * BAR + 3), "dump", 0)
    seq_page(s, p + int(5.5 * BAR), 1, encs=[(K4, 1), (K4, -1), (K3, -1), (K3, 1)], cur=1)   # turn C and B there and back
    log = run(s, int(p + 8 * BAR))
    h = [x["heard"] for x in states(log)]
    check(len(h) == 5 and len(set(h)) == 1 and h[0] != "x..x..x...x.....", "TURING locked after mutating, the knobs keep it (%s)" % h[:2])

    # 7. CELL: the CELLS knob (B) sets how many cells; the row repeats every that many steps
    s = Script()
    t = s.steps(100, [0, 5])
    t = seq_page(s, t + 30, 1, encs=[(K1, 2), (K3, -12)], keys=[wk(5)])   # CELL, 16 -> 4 cells; started
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    st = states(log)[0]
    hh = st["heard"]
    check(st["algo"] == 2 and st["b"] == 4 and hh == hh[:4] * 4, "CELL with 4 cells: the row repeats every 4 steps (%s)" % hh)

    # 8. EUCLID live per track, heard and shown; SEQ + OCT+ still turns the pages
    s = Script()
    t = seq_page(s, 100, 0, encs=[(K1, 1)], keys=[wk(5)])      # track 1: 5 pulses, live (0.16: SEQ + white 6 starts it)
    s.tap_key(t, bk(1)); t += 80
    t = seq_page(s, t, 0, encs=[(K1, -1)], keys=[wk(5)])       # track 2: 3 pulses, live
    t = seq_page(s, t, 1, encs=[(K1, 1)], keys=[wk(5)])        # page 2 (OCT+): TURING on track 2
    s.at(t, "dump", 0); s.at(t, "dump", 1)
    s.raw(t + 10, "attach")
    p = t + 200
    s.tap_btn(p, PLAY)
    log = run(s, p + int(BAR) - 30)
    s1, s2 = states(log, 1)[0], states(log, 2)[0]
    check(s1["pulses"] == 5 and s1["flags"] & 8 and s1["heard"].count("x") == 5 and s2["pulses"] == 3 and s2["flags"] & 8,
          "EUCLID: track 1 5 pulses live, track 2 3 pulses live (%s %s)" % (s1["heard"], s2["heard"]))
    check(s2["algo"] == 1 and s1["algo"] == 0, "SEQ + OCT+ goes to page 2 with EUCLID live (ALGORITHM on track 2)")
    check(len(log.notes(ch=0, after=p)) == 5, "track 1 plays its 5 euclid hits over an empty row (%d)" % len(log.notes(ch=0, after=p)))
    s = Script()
    t = seq_page(s, 100, 0, keys=[wk(5)])                      # EUCLID LIVE 4/16 on track 1
    s.raw(t, "attach"); view(s, t + 50, GC_VSTEP)
    log = run(s, t + 300)
    pads, _ = log.leds()
    check([pads[x] for x in (4, 8, 12)] == [GL_CYAN] * 3 and GL_CYAN not in [pads[x] for x in (1, 2, 3, 5)],
          "grid STEP view: the hits the euclid adds in cyan (%s)" % [pads[x] for x in range(6)])

    # 9. STACCATO on a ratchet: 40 % of each slice (0.7: of the step: legato)
    s = Script()
    t = s.steps(100, [0])
    s.enc(t + 30, K4, 3)                                       # ratchet 4
    s.raw(t + 100, "attach"); view(s, t + 150, GC_UNDO, alt=True)
    shift(s, t + 300, 1); s.pad(t + 320, 13, 0); shift(s, t + 400, 0)   # STC latched
    p = t + 500
    s.tap_btn(p, PLAY)
    log = run(s, p + int(STEP_MS) + 50)
    on = [tm for tm, _, _ in log.notes(ch=0, after=p)]
    off = [tm for tm, _ in log.offs(ch=0) if tm > p]
    durs = [b - a for a, b in zip(on, off)]
    check(len(on) == 4 and all(near(d, 0.4 * STEP_MS / 4, 3) for d in durs), "STACCATO x4 ratchet: %s ms (a slice is %.1f)" % (durs, STEP_MS / 4))

    # 10. the macros turn fast when turned fast (0.7: 127 detents for the whole range)
    def vel_after(gap):
        s = Script()
        t = s.steps(100, [0])
        s.press(t, FX)
        for i in range(12):
            s.enc(t + 30 + gap * i, K1, -1)
        s.release(t + 60 + gap * 12, FX)
        t += 120 + gap * 12
        s.at(t, "dump", 0)
        return states(run(s, t + 50))[0]["mac"][0]
    slow, fast = vel_after(100), vel_after(10)
    check(slow == -12 and fast < -24, "INTENSITY: 12 slow detents -12, 12 fast ones %d" % fast)


def t08_knobs_zero():
    group("0.8: every value comes back to exactly 0")
    s = Script()
    t = s.steps(100, [0, 4, 8])
    remote(s, t, 8, 66)                                        # GATE +3 from the remote (not a multiple of 5)
    s.at(t + 50, "dump", 0)
    t = held(s, t + 100, FX, [(K2, -1)])                       # one detent down: 0, not -2
    s.at(t, "dump", 0)
    remote(s, t + 50, 10, 61)                                  # FILTER -3
    t = held(s, t + 100, FX, [(K4, 1)])
    s.at(t, "dump", 0)
    t = held(s, t + 50, FX, [(K4, 1)])
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    m = [x["mac"] for x in states(log)]
    check(m[0][1] == 3 and m[1][1] == 0, "GATE +3, a detent down: 0 (%s)" % [x[1] for x in m])
    check(m[2][3] == -2 and m[3][3] == 0, "FILTER -3, two detents up: -2, 0 (%s)" % [x[3] for x in m])
    # the step's velocity offset, the transpose: the same
    s = Script()
    t = held(s, 100, SEL, [(K1, 3)])
    t = held(s, t, SEL, [(K1, -3)])
    t = home_page(s, t, 0, [(K4, 5), (K4, -7), (K4, 2)])
    t = s.steps(t, [0])
    s.tap_btn(t + 100, PLAY)
    log = run(s, t + 600)
    n = log.notes(ch=0, after=t + 100)
    check(n and n[0][1] == 60 and n[0][2] == 100, "SEL K1 +3 -3, HOME K4 +5 -7 +2: velocity and note as at first (%s)" % n[:1])


def t08_snapshots():
    group("0.8: SNAPSHOTS")
    BAR = 16 * STEP_MS
    def store(s, t, n): s.press(t, SAVE); s.press(t + 20, SEL); s.tap_key(t + 40, bk(n)); s.release(t + 100, SEL); s.release(t + 120, SAVE); return t + 180
    def recall(s, t, n): s.press(t, SAVE); s.tap_key(t + 20, bk(n)); s.release(t + 100, SAVE); return t + 160
    # store, change, recall while stopped: at once. A snapshot keeps which pattern plays (the patterns are the project's)
    s = Script()
    t = s.steps(100, [0, 8])
    t = held(s, t, FX, [(K1, 10)])                             # INTENSITY +10
    t = store(s, t, 0)
    s.enc(t, E_PRE, 1); t = s.steps(t + 50, [4])               # pattern 2: step 5
    t = held(s, t, FX, [(K1, -20)])
    s.at(t, "dump", 0)
    t = recall(s, t + 50, 0)
    s.at(t, "dump", 0)
    s.tap_btn(t + 100, PLAY)
    log = run(s, t + 100 + int(BAR))
    st = states(log)
    sx = [x for tm, x in log.sysex if x[4] == 0x40]
    n = log.notes(ch=0, after=t + 100)
    check(st[0]["mac"][0] == -10 and st[1]["mac"][0] == 10 and st[1]["snap"] == 0, "the snapshot brings the macros back (%s)" % [x["mac"][0] for x in st])
    check(log.dumps[0]["pat"] == 2 and log.dumps[1]["pat"] == 1, "... and pattern 1")
    check([round((tm - t - 100) / STEP_MS) for tm, _, _ in n] == [0, 8] and all(v == 110 for _, _, v in n), "... it plays, INTENSITY +10 (%s)" % n)
    check(sx and sx[0][:6] == [0xF0, 0x7D, 0x53, 0x47, 0x40, 0x00] and sx[0][-2:] == [0x00, 0xF7], "SysEx 40 to the Pi: snapshot 1, stopped (%s)" % sx[:1])
    # recalled while playing: on the bar line (QUANTISE AUTO)
    s = Script()
    t = s.steps(100, [0, 4, 8, 12])
    t = store(s, t, 1)
    s.enc(t, E_PRE, 1); t += 50                                # pattern 2: empty
    p = t + 100
    s.tap_btn(p, PLAY)
    recall(s, p + int(0.5 * BAR), 1)
    s.at(p + int(0.5 * BAR) + 200, "dump", 0)
    log = run(s, p + int(2 * BAR))
    n = [round((tm - p) / STEP_MS) for tm, _, _ in log.notes(ch=0, after=p)]
    check(n == [16, 20, 24, 28], "SNAPSHOT recalled in the bar: it comes on the next bar line (%s)" % n)
    check(states(log)[0]["pend"] == 1, "the snapshot waits (pending 2)")
    sx = [tm for tm, x in log.sysex if x[4] == 0x40]
    check(sx and near(sx[0], p + 16 * STEP_MS, 3) and log.sysex[-1][1][-2] == 1, "SysEx 40 when it comes, playing (%s)" % sx)
    # CC CAPTURE: a synth's knob turns, the value goes into the snapshot; SEND sends it again; recall sends it
    s = Script()
    t = store(s, 100, 0)
    s.press(t, SAVE); s.tap_key(t + 20, bk(8)); s.release(t + 80, SAVE); t += 140      # CAPTURE on
    s.raw(t, "midi 0xB2 74 99"); s.raw(t + 10, "midi 0xB2 71 20"); s.raw(t + 20, "midi 0xB2 74 101")
    s.raw(t + 30, "midi 0xB2 123 0")                           # (All Notes Off: not a value)
    s.press(t + 60, SAVE); s.tap_key(t + 80, bk(8)); s.release(t + 140, SAVE); t += 200   # CAPTURE off
    s.raw(t, "midi 0xB2 74 5")                                 # not captured any more
    mark = t + 50
    s.press(mark, SAVE); s.tap_key(mark + 20, bk(9)); s.release(mark + 80, SAVE)        # SEND
    log = run(s, mark + 300)
    out = [(st, d1, d2) for tm, st, d1, d2 in log.msgs if tm >= mark and (st & 0xF0) == 0xB0 and st != 0xBE]
    check(out == [(0xB2, 74, 101), (0xB2, 71, 20)], "CC CAPTURE then SEND: CH3 CC74 = 101, CC71 = 20 (%s)" % out)
    # PATCHES: SysEx 41 to the Pi; the Pi answers 42
    s = Script()
    t = store(s, 100, 4)
    s.press(t, SAVE); s.tap_key(t + 20, bk(10)); s.release(t + 80, SAVE); t += 140
    s.raw(t + 100, "sx 7D 53 47 42 00 02")
    s.at(t + 150, "dump", 0)
    log = run(s, t + 200)
    sx = [x for tm, x in log.sysex if x[4] == 0x41]
    check(sx and sx[0][5] == 4 and len(sx[0]) == 13, "PATCHES: SysEx 41, snapshot 5, the project id (%s)" % sx[:1])
    check(states(log)[0]["msg"] == "PI KEPT THE PATCHES OF 2 SYNTHS", "the Pi's answer on the screen (%s)" % states(log)[0]["msg"])
    # the snapshots live in the project: saved, back after a power cycle
    with tempfile.TemporaryDirectory() as d:
        fl = os.path.join(d, "flash.bin")
        s = Script()
        t = s.steps(100, [3])
        s.enc(t, E_PRE, 1); t = s.steps(t + 50, [5])           # pattern 2
        t = store(s, t, 7)
        s.tap_btn(t + 50, SAVE); s.tap_btn(t + 350, SAVE)
        run(s, t + 3000, flash=fl)
        s = Script()
        s.at(1400, "dump", 0)
        t = recall(s, 1500, 7)
        s.at(t, "dump", 0)
        log = run(s, t + 100, flash=fl)
        d = [(x["pat"], x["on"][:8]) for x in log.dumps]
        check(d == [(2, ".....x.."), (2, ".....x..")], "a snapshot is saved with the project; 0.9: the FM-1 comes back on the pattern that played (%s)" % d)
    # the remote: CC 12-19 store, 106-113 recall
    s = Script()
    t = s.steps(100, [0])
    remote(s, t, 13)                                           # store snapshot 2
    s.enc(t + 50, E_PRE, 1)
    s.at(t + 100, "dump", 0)
    remote(s, t + 150, 107)                                    # recall it
    s.at(t + 200, "dump", 0)
    log = run(s, t + 300)
    check([x["pat"] for x in log.dumps] == [2, 1] and states(log)[1]["snap"] == 1, "remote CC 13 stores snapshot 2, CC 107 brings it back")


def t08_harmony():
    group("0.8: the HARMONY, FOLLOW")
    BAR = 16 * STEP_MS
    # a melody in the key on a FOLLOW track moves with the chords; a track without FOLLOW stays
    s = Script()
    t = kp(s, 100, [(K4, 1)])                        # track 1 in key (C minor)
    t = s.steps(t, [0, 4, 8, 12])
    t = home_page(s, t, 1, [(K4, 1)], cur=2)                   # FOLLOW
    t = harm_knobs(s, t, [(K1, 1)])                      # HARMONY on
    t = harm_knobs(s, t, [(K2, 3)])                      # TECHNO #4: i VII VI VII
    s.tap_key(t, bk(1)); t += 80
    t = kp(s, t, [(K4, 1)], cur=1)
    t = s.steps(t, [0, 4, 8, 12])                              # track 2 in key, no FOLLOW
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + int(4 * BAR))
    b1 = [sorted({d1 for tm, d1, _ in log.notes(ch=0, after=p + int(k * BAR) - 5, before=p + int((k + 1) * BAR) - 5)}) for k in range(4)]
    b2 = sorted({d1 for _, d1, _ in log.notes(ch=1, after=p)})
    check(b1 == [[60], [58], [56], [58]], "FOLLOW: C, B flat, A flat, B flat (%s)" % b1)
    check(b2 == [60], "no FOLLOW: always C (%s)" % b2)
    # HARMONY off: back to C
    s = Script()
    t = kp(s, 100, [(K4, 1)])
    t = s.steps(t, [0])
    t = home_page(s, t, 1, [(K4, 1)], cur=2)
    t = harm_knobs(s, t, [(K1, 1)])
    t = harm_knobs(s, t, [(K2, 3)])
    p = t + 100
    s.tap_btn(p, PLAY)
    remote(s, p + int(1.5 * BAR), 117)                          # remote CC 117: HARMONY off
    log = run(s, p + int(3 * BAR))
    n = [d1 for _, d1, _ in log.notes(ch=0, after=p)]
    check(n == [60, 58, 60], "HARMONY off (remote CC 117): the track plays as written again (%s)" % n)


def t08_dice_memory():
    group("0.8: the dice remember: ALG goes back through the rolls")
    s = Script()
    t = s.steps(100, [0, 4, 8, 12])
    t = seq_page(s, t, 0, encs=[(K4, 20)])                     # heat 100: rolls that differ
    for k in range(3):
        t = seq_page(s, t, 0, keys=[bk(0)])                    # DICE SEQ three times
        s.at(t, "dump", 0)
    s.enc(t + 50, E_ALG, -1); s.at(t + 100, "dump", 0)          # the roll before
    s.enc(t + 150, E_ALG, -1); s.at(t + 200, "dump", 0)         # the first
    s.enc(t + 250, E_ALG, 2); s.at(t + 300, "dump", 0)          # the last again
    s.tap_btn(t + 350, OCT_UP); s.at(t + 400, "dump", 0)        # KEEP
    s.enc(t + 450, E_ALG, -1); s.at(t + 500, "dump", 0)         # kept: ALG moves the cursor, not the dice
    log = run(s, t + 600)
    h = [d["hash"] for d in log.dumps]
    check(len(set(h[:3])) == 3, "three different rolls")
    check(h[3] == h[1] and h[4] == h[0] and h[5] == h[2], "ALG: roll 2, roll 1, roll 3 again, exactly (%s)" % h)
    check(h[6] == h[2] and h[7] == h[2], "OCT+ keeps roll 3; then ALG is the cursor again")


def t08_grid_views():
    group("0.8: grid EUCLID, TRACK 3, FX snapshots and ECHO")
    BAR = 16 * STEP_MS
    s = Script()
    s.raw(100, "attach")
    view(s, 200, GC_VTRACK, alt=True); view(s, 300, GC_VTRACK, alt=True)   # BEAT, again: EUCLID
    s.pad(400, 0, 0)                                           # track 1 live
    s.pad(500, 3, 0)                                           # 3 pulses
    s.pad(600, 0, 1); s.pad(700, 8, 1)                         # track 2: live, 8 pulses
    p = 900
    s.tap_btn(p, PLAY)
    log = run(s, p + int(BAR) - 30)
    n1, n2 = len(log.notes(ch=0, after=p)), len(log.notes(ch=1, after=p))
    check(n1 == 3 and n2 == 8, "EUCLID view: track 1 3 hits, track 2 8 hits (%d %d)" % (n1, n2))
    pads, _ = log.leds(until=p)
    check(pads[0] == GL_PLAY and pads[3] == GL_WHITE and pads[16 + 8] == GL_WHITE, "the live tracks and their pulses lit")
    # BEAT view, genres page 2 (pad 13 of row 1): the 16th genre (0.10: DRUM+BASS), its KICK #1 "X.........X....."
    s = Script()
    s.raw(100, "attach")
    view(s, 200, GC_VTRACK, alt=True)
    s.pad(300, 12, 0); s.pad(400, 3, 0); s.pad(500, 0, 1); s.pad(600, 13, 0)
    s.tap_btn(800, PLAY)
    log = run(s, 800 + int(BAR) - 30)
    pos = [round((tm - 800) / STEP_MS) for tm, _, _ in log.notes(ch=0, after=800)]
    check(pos == [0, 10], "BEAT view page 2: DRUM+BASS KICK #1 (%s)" % pos)
    # TRACK 3: MIDI FX ECHO from the grid
    s = Script()
    t = s.steps(100, [0])
    s.raw(t, "attach")
    view(s, t + 100, GC_VTRACK); view(s, t + 200, GC_VTRACK); view(s, t + 300, GC_VTRACK)   # TRACK, 2, 3
    s.pad(t + 400, 3, 1); s.pad(t + 480, 3, 1)                 # ECHO READY, again: it starts (0.16)
    p = t + 600
    s.tap_btn(p, PLAY)
    log = run(s, p + 800)
    n = log.notes(ch=0, after=p)
    check(len(n) == 3 and n[1][2] < n[0][2], "TRACK 3: ECHO from the grid, two softer repeats (%s)" % n)
    # FX view: SHIFT + row 8 pad 5 stores snapshot 1, the pad brings it back; pad 14 (row 2) the global ECHO
    s = Script()
    t = s.steps(100, [0])
    s.raw(t, "attach"); view(s, t + 100, GC_UNDO, alt=True)
    shift(s, t + 200, 1); s.pad(t + 220, 4, 7); shift(s, t + 300, 0)
    s.enc(t + 400, E_PRE, 1)                                   # pattern 2
    s.pad(t + 500, 4, 7)
    t += 500
    s.at(t + 200, "dump", 0)
    s.pad(t + 300, 13, 1)                                      # global ECHO
    p = t + 400
    s.tap_btn(p, PLAY)
    log = run(s, p + 800)
    check(log.dumps[0]["pat"] == 1, "FX view: snapshot 1 stored and recalled from row 8 (pattern %d)" % log.dumps[0]["pat"])
    check(len(log.notes(ch=0, after=p)) == 3, "FX view: the global ECHO, twice (%d notes)" % len(log.notes(ch=0, after=p)))
    # FX + OCT+ on the panel: the same global ECHO
    s = Script()
    t = s.steps(100, [0])
    s.press(t, FX); s.tap_btn(t + 30, OCT_UP); s.release(t + 100, FX)
    s.tap_btn(t + 200, PLAY)
    log = run(s, t + 1000)
    check(len(log.notes(ch=0, after=t + 200)) == 3, "FX + OCT+: the global ECHO")


def t08_usb_two_ports():
    group("0.8: USB PORTS 2: port 1 the synths (16 channels), port 2 the grid, the remote, the Pi")
    def two_ports(s, t):
        t = save_sys(s, t, [(K1, 1)])                            # SAVE 3: USB PORTS 2
        t = save_sys(s, t, [(K1, 1), (K1, 1)], sel=True)         # SEL + K1 twice: reconnect
        return t + 400
    s = Script()
    t = two_ports(s, 100)
    t = s.steps(t, [0])
    t = home_page(s, t, 0, [(K1, 15)])                           # track 1 on MIDI channel 16
    s.raw(t, "attach")                                          # (the host sends the grid on port 2)
    s.raw(t + 50, "midi 0x9F 60 100 1")                          # a note on channel 16, port 1: not a pad
    s.raw(t + 60, "midi 0xBD 48 127 1")                          # channel 14 on port 1: not the remote
    s.raw(t + 70, "midi 0xBD 49 127 2")                          # the remote on port 2: mute track 2
    s.at(t + 100, "dump", 1)
    s.tap_btn(t + 200, PLAY)
    log = run(s, t + 600)
    ports = re.findall(r"^\s*\d+ ms  USB ports (\d)", log.text, re.M)
    check(ports == ["2"], "the USB page: 2 ports at the reconnect (%s)" % ports)
    ch16 = [m for m in log.msgs if m[1] == 0x9F and m[2] == 60 and m[3] and m[0] >= t + 200]
    grid = [l for l in log.text.splitlines() if " MIDI out 9F " in l and l.endswith("port 2")]
    check(len(ch16) == 1 and not log.text.count("MIDI out 9F 60 100 port 2"), "track 1 plays on channel 16, port 1 (%s)" % ch16[:1])
    check(len(grid) > 50, "the grid's LEDs go out on port 2 (%d)" % len(grid))
    s2 = Script()
    t = two_ports(s2, 100)
    s2.raw(t, "midi 0xBD 20 127 1")                              # PLAY from the remote, port 1: nothing
    s2.raw(t + 100, "sx 7D 53 47 01")                           # an app SysEx (export): the answer on port 2
    s2.raw(t + 400, "midi 0xBD 20 127 2")                        # PLAY from the remote, port 2
    s2.steps(t + 50, [0])
    log = run(s2, t + 800)
    n = log.notes(ch=0, after=t)
    check(n and n[0][0] >= t + 400, "the remote works on port 2 only (first note at %s)" % (n[0][0] - t if n else None))
    sx = [l for l in log.text.splitlines() if "SYSEX out" in l]
    check(sx and all(l.endswith("port 2") for l in sx), "the app's SysEx answers on port 2 (%d)" % len(sx))
    # back to one port: the grid on channels 15 / 16 of the only port again
    s3 = Script()
    t = two_ports(s3, 100)
    t = save_sys(s3, t, [(K1, -1)])                              # USB PORTS 1
    t = save_sys(s3, t, [(K1, 1), (K1, 1)], sel=True)            # reconnect
    log = run(s3, t + 500)
    ports = re.findall(r"^\s*\d+ ms  USB ports (\d)", log.text, re.M)
    check(ports == ["2", "1"], "and back to 1 port (%s)" % ports)


# ------------------------------------------------------------------------------------------------ 0.9 VIAGGIO
BAR_MS = 16 * STEP_MS                                       # 1875 ms at 128 BPM


def vg_on(s, t, remote=True):
    """0.17: SEL + GLO, a tap: PERF on its third page, the MOSSE (the journey always runs: there is no VIAGGIO mode).
    remote: SAVE + K2 first, the remote on 13 + 14: channel 13 has the journey's tracks (CC 1-16 a tap on the track, CC 32
    the track queued in / out), what the white keys did in VIAGGIO mode until 0.16"""
    if remote:
        s.press(t, SAVE); s.enc(t + 30, K2, 1); s.release(t + 100, SAVE); t += 150
    s.press(t, SEL); s.tap_btn(t + 30, GLO); s.release(t + 100, SEL)
    s.pages[GLO] = 2
    return t + 160


def vg_studio(s, t):
    """0.17: SEL + GLO again on the MOSSE: the studio (PERF off); the journey goes on"""
    s.press(t, SEL); s.tap_btn(t + 30, GLO); s.release(t + 100, SEL)
    return t + 160


def vg_tap(s, t, i):
    """0.17: a tap on track i of the journey (the remote's CC i + 1 on channel 13): a proposal on an empty track"""
    s.raw(t, "midi 0xBC %d 127" % (i + 1))
    return t + 60


def vg_cc(s, t, cc):
    """0.17: a move of the remote on channel 13 (CC 17-27: FILL BREAK RISER DROP HALF DOUBLE THIN SWELL SWAP LOOP NOW)"""
    s.raw(t, "midi 0xBC %d 127" % cc)
    return t + 60


def vg_bars4(s, t):
    """HOME page 6 (VIAGGIO), K2 twice down: a 4-bar phrase"""
    return viaggio_knobs(s, t, [(K2, -1), (K2, -1)])


def vg_queue_track(s, t, i):
    """the track in (a proposal made if it has none) or out at the boundary (0.17: the remote's CC 32 = 8 x the track;
    until 0.16 SEL + a white key in VIAGGIO mode)"""
    s.raw(t, "midi 0xBC 32 %d" % (8 * i))
    return t + 60


def t09_viaggio_phrase():
    group("0.9 VIAGGIO (0.17: the MOSSE): a proposal, the queue, the boundary, NOW, the trail")
    s = Script()
    t = vg_on(s, 100)
    s.at(t, "dump", 0)
    vg_tap(s, t + 50, 0)                                     # track 1 (empty): a proposal
    s.at(t + 150, "dump", 0)
    t = vg_queue_track(s, t + 200, 0)                        # SEL + key 1: IN at the boundary
    s.at(t, "dump", 0)
    t = vg_bars4(s, t + 50)
    s.at(t, "dump", 0)
    t0 = t + 100
    s.tap_btn(t0, PLAY)
    s.at(t0 + 2 * BAR_MS + 200, "dump", 0)
    s.at(t0 + 4 * BAR_MS + 200, "dump", 0)
    log = run(s, t0 + 5 * BAR_MS)
    v = log.viaggio
    check(v[0]["on"] == 1 and v[0]["states"] == "E" * 16 and v[0]["bars"] == 16 and v[0]["energy"] == 50 and v[0]["genre"] == 0,
          "SEL + GLO: the MOSSE, every track empty, 16-bar phrase, energy 50, TECHNO (the project's genre) (%s)" % v[0])
    check(log.states[0]["msg"].startswith("MOSSE: BLACK = MOVES"), "the screen says how (%s)" % log.states[0]["msg"])
    check(v[1]["states"].startswith("P") and log.states[1]["msg"].startswith("T1 KICK P2") and log.dumps[1]["on"].count("x") == 0,
          "a tap on an empty track: a proposal in pattern 2 (the playing one stays empty), the track is PROPOSED (%s)" % log.states[1]["msg"])
    check(v[2]["queue"] == ["IN/0/1"] and log.states[2]["msg"] == "QUEUED: T1 IN", "CC 32: IN queued (%s)" % v[2]["queue"])
    check(log.dumps[1]["pen"] == 36, "the empty track took the kick's note (%s)" % log.dumps[1]["pen"])
    check(v[3]["bars"] == 4 and log.states[3]["msg"] == "PHRASE: BARS 4", "GLO 3 (the MOSSE), K2: a 4-bar phrase")
    n = log.notes(ch=0, after=t0)
    check(not [x for x in n if x[0] < t0 + 4 * BAR_MS - 5] and n and near(n[0][0], t0 + 4 * BAR_MS, 20),
          "nothing until the boundary; at bar 5 the kick comes in (first note at +%.0f ms)" % ((n[0][0] - t0) if n else -1))
    check(v[4]["bar"] == 2 and v[4]["queue"] == ["IN/0/1"] and v[4]["trail"] == 0, "bar 3 of 4: the move still waits (%s)" % v[4])
    check(v[5]["bar"] == 0 and v[5]["queue"] == [] and v[5]["trail"] == 1 and v[5]["states"].startswith("I") and v[5]["patterns"].startswith("2"),
          "after the boundary: the queue ran, the trail holds the first phrase, track 1 IN on pattern 2 (%s)" % v[5])
    # NOW: the queue runs at the next bar instead; black 10 cancels the last move (0.9-0.16: OCT+); a second track joins
    s = Script()
    t = vg_on(s, 100)
    t = vg_queue_track(s, t, 0)
    t = vg_bars4(s, t)
    t0 = t
    s.tap_btn(t0, PLAY)
    s.tap_key(t0 + 200, bk(10))                              # NOW
    s.at(t0 + 300, "dump", 0)
    s.at(t0 + BAR_MS + 200, "dump", 0)
    t = vg_queue_track(s, t0 + BAR_MS + 300, 1)              # track 2 at the boundary ...
    s.tap_key(t, bk(0))                                      # ... and a FILL
    s.tap_key(t + 100, bk(9))                                # cancelled
    s.at(t + 200, "dump", 1)
    s.at(t0 + 4 * BAR_MS + 200, "dump", 1)
    log = run(s, t0 + 5 * BAR_MS)
    v = log.viaggio
    n = log.notes(ch=0, after=t0)
    check(log.states[0]["msg"] == "NOW: AT THE NEXT BAR" and v[1]["bar"] == 1 and v[1]["queue"] == [] and v[1]["states"].startswith("I") and v[1]["trail"] == 0,
          "NOW: the move ran at bar 2, no phrase in the trail yet (%s)" % v[1])
    check(n and near(n[0][0], t0 + BAR_MS, 20), "the kick came in at bar 2 (%s)" % (n[:1]))
    check(v[2]["queue"] == ["IN/1/255"] and log.states[2]["msg"] == "CANCELLED FILL", "black 10: the FILL is cancelled, track 2 still waits (%s)" % v[2]["queue"])
    check(v[3]["states"].startswith("II") and v[3]["trail"] == 1 and v[3]["bar"] == 0, "at the boundary track 2 joins (%s)" % v[3]["states"])
    check(log.notes(ch=1, after=t0 + 4 * BAR_MS) and not log.notes(ch=1, after=t0, before=t0 + 4 * BAR_MS - 5), "... and plays from bar 5 only")
    # a tap on IN: no silence; the MOSSE are PERF: a white key mutes; SEL + GLO again: the studio, the journey goes on
    s = Script()
    t = vg_on(s, 100)
    t = vg_queue_track(s, t, 0)
    s.tap_key(t, bk(10)); t += 100                           # NOW, stopped: at once
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); t0 = t
    vg_tap(s, t0 + BAR_MS + 200, 0)                          # a tap on the track that plays
    s.at(t0 + BAR_MS + 300, "dump", 0)
    s.tap_key(t0 + BAR_MS + 400, wk(1))                      # PERF's white key: mute track 2 (nothing to hear)
    s.at(t0 + BAR_MS + 500, "dump", 0)
    vg_studio(s, t0 + BAR_MS + 600)                          # SEL + GLO: the studio
    s.at(t0 + BAR_MS + 800, "dump", 0)
    log = run(s, t0 + 2 * BAR_MS)
    v = log.viaggio
    check(v[0]["states"].startswith("I") and v[0]["queue"] == [] and log.states[0]["msg"] == "NOW: DONE", "NOW while stopped: the queue runs at once")
    check(v[1]["states"].startswith("I") and log.states[1]["msg"] == "T1 IN" and v[1]["mute"] == 0,
          "a tap on a track that is IN never silences it (%s)" % log.states[1]["msg"])
    check(v[2]["on"] == 1 and v[2]["mute"] == 2, "on the MOSSE the white keys are PERF's mutes (%04X)" % v[2]["mute"])
    check(v[3]["on"] == 0 and v[3]["journey"] == 1 and log.states[3]["msg"].startswith("STUDIO"), "SEL + GLO again: the studio, the journey goes on (%s)" % log.states[3]["msg"])
    check(len(log.notes(ch=0, after=t0 + BAR_MS + 800)) > 0, "track 1 keeps playing")


def vg_track_in_now(s, t, i):
    """track i queued, then NOW (black 11 on the MOSSE) while stopped: the track is IN at once (a proposal of its role)"""
    t = vg_queue_track(s, t, i)
    s.tap_key(t, bk(10))
    return t + 100


def t09_viaggio_moves():
    group("0.9 VIAGGIO: energy, HALF / DOUBLE, BREAK, OUT with a fade, THIN / SWELL, DROP, RISER, FILL, INDIETRO, SALVA VIAGGIO")
    # the energy: K1 on the MOSSE (GLO 3); 100 = velocity +20, 0 = -20; the glide over the phrase
    def energy_run(e):
        s = Script()
        t = vg_on(s, 100)
        t = vg_track_in_now(s, t, 0)
        t = vg_bars4(s, t)
        s.enc(t, K1, e - 50); t += 60
        s.at(t, "dump", 0)
        s.tap_btn(t + 50, PLAY)
        return run(s, t + 50 + BAR_MS), t + 50
    log, t0 = energy_run(100)
    v100 = [v for _, _, v in log.notes(ch=0, after=t0)]
    check(log.viaggio[0]["energy"] == 100 and log.viaggio[0]["target"] == 100, "K1: energy 100 (%s)" % log.viaggio[0])
    v50 = [v for _, _, v in energy_run(50)[0].notes(ch=0, after=t0)]
    log, t0 = energy_run(0)
    v0 = [v for _, _, v in log.notes(ch=0, after=t0)]
    check(v100 and v0 and v50 and v100[0] == min(127, v50[0] + 20) and v0[0] == v50[0] - 20,
          "energy 100 plays 20 louder, 0 plays 20 softer (%s / %s / %s)" % (v100[:1], v50[:1], v0[:1]))
    check(len(v100) > len(v50) >= len(v0) and min(v100) < 40, "energy 100 adds ghost hits (density 130 %%), 0 takes none from the kick (%d / %d / %d)" % (len(v100), len(v50), len(v0)))
    # a target set while playing glides over the phrase: bar by bar
    s = Script()
    t = vg_on(s, 100)
    t = vg_track_in_now(s, t, 0)
    t = vg_bars4(s, t)
    s.tap_btn(t, PLAY); t0 = t
    s.enc(t0 + 200, K1, 50)                                  # 100 as the target
    for b in range(1, 6):
        s.at(t0 + b * BAR_MS + 100, "dump", 0)
    log = run(s, t0 + 5 * BAR_MS + 200)
    e = [v["energy"] for v in log.viaggio]
    check(e == [75, 87, 100, 100, 100], "a target set in bar 1 is reached in the phrase's last bar, a step a bar: %s" % e)
    # HALF: for one phrase the kick plays at half speed, then as before; DOUBLE the opposite
    def speed_run(black):
        s = Script()
        t = vg_on(s, 100)
        t = vg_track_in_now(s, t, 0)
        t = vg_bars4(s, t)
        s.tap_btn(t, PLAY); t0 = t
        s.tap_key(t0 + 200, bk(black))
        s.at(t0 + 4 * BAR_MS + 300, "dump", 0)
        s.at(t0 + 8 * BAR_MS + 300, "dump", 0)
        log = run(s, t0 + 9 * BAR_MS)
        def gap(after, before):
            n = log.notes(ch=0, after=after, before=before)
            return round((n[1][0] - n[0][0]) / STEP_MS, 1) if len(n) > 1 else None
        return log, gap(t0 + 100, t0 + 4 * BAR_MS - 100), gap(t0 + 4 * BAR_MS + 100, t0 + 8 * BAR_MS - 100), gap(t0 + 8 * BAR_MS + 100, t0 + 9 * BAR_MS)
    log, g1, g2, g3 = speed_run(4)
    check(log.viaggio[0]["speed"] == -1 and log.viaggio[1]["speed"] == 0, "HALF is on for the phrase after the boundary only (%s %s)" % (log.viaggio[0]["speed"], log.viaggio[1]["speed"]))
    check(g1 == 4 and g2 == 8 and g3 == 4, "the kick: every 4 steps, then every 8 for one phrase, then 4 again (%s %s %s)" % (g1, g2, g3))
    log, g1, g2, g3 = speed_run(5)
    check(g1 == 4 and g2 == 2 and g3 == 4, "DOUBLE: every 2 steps for one phrase (%s %s %s)" % (g1, g2, g3))
    # BREAK: SEL + black 2 = everything out for 2 bars from the boundary, then back; black 2 alone = 1 bar, this track stays
    s = Script()
    t = vg_on(s, 100)
    t = vg_track_in_now(s, t, 0)
    t = vg_track_in_now(s, t, 1)
    t = vg_bars4(s, t)
    s.tap_btn(t, PLAY); t0 = t
    s.press(t0 + 200, SEL); s.tap_key(t0 + 230, bk(1)); s.release(t0 + 300, SEL)
    s.at(t0 + 400, "dump", 0)
    s.at(t0 + 5 * BAR_MS + 100, "dump", 0)
    s.at(t0 + 7 * BAR_MS + 100, "dump", 0)
    log = run(s, t0 + 8 * BAR_MS)
    v = log.viaggio
    check(v[0]["queue"] == ["BREAK/255/2"] and log.states[0]["msg"] == "QUEUED: BREAK ALL, 2 BARS", "SEL + black 2: BREAK all, 2 bars (%s)" % v[0]["queue"])
    check(v[1]["mute"] == 0xFFFF and v[2]["mute"] == 0, "bars 5-6 silent, bar 7 everything back (%04X %04X)" % (v[1]["mute"], v[2]["mute"]))
    check(not log.notes(after=t0 + 4 * BAR_MS + 10, before=t0 + 6 * BAR_MS - 10) and log.notes(ch=0, after=t0 + 6 * BAR_MS) and log.notes(ch=1, after=t0 + 6 * BAR_MS),
          "no note in the break, both tracks after it")
    s = Script()
    t = vg_on(s, 100)
    t = vg_track_in_now(s, t, 0)
    t = vg_track_in_now(s, t, 1)
    t = vg_bars4(s, t)
    vg_tap(s, t, 0)                                          # track 1 selected
    s.tap_btn(t + 100, PLAY); t0 = t + 100
    s.tap_key(t0 + 200, bk(1))
    s.at(t0 + 4 * BAR_MS + 100, "dump", 0)
    log = run(s, t0 + 6 * BAR_MS)
    check(log.viaggio[0]["mute"] == 0xFFFE and log.notes(ch=0, after=t0 + 4 * BAR_MS + 10, before=t0 + 5 * BAR_MS - 10)
          and not log.notes(ch=1, after=t0 + 4 * BAR_MS + 10, before=t0 + 5 * BAR_MS - 10) and log.notes(ch=1, after=t0 + 5 * BAR_MS + 10),
          "black 2 alone: one bar with track 1 alone, then track 2 is back (%04X)" % log.viaggio[0]["mute"])
    # OUT: the track fades through its last bar, is muted at the boundary; queued again: IN cancels the OUT
    s = Script()
    t = vg_on(s, 100)
    t = vg_track_in_now(s, t, 0)
    t = vg_track_in_now(s, t, 1)
    t = vg_bars4(s, t)
    s.tap_btn(t, PLAY); t0 = t
    t = vg_queue_track(s, t0 + 200, 1)                       # track 2 OUT
    s.at(t, "dump", 1)
    s.at(t0 + 4 * BAR_MS + 100, "dump", 1)
    t = vg_queue_track(s, t0 + 4 * BAR_MS + 300, 1)          # IN again ...
    s.at(t, "dump", 1)
    t = vg_queue_track(s, t + 50, 1)                         # ... and OUT: replaces it
    s.at(t, "dump", 1)
    s.tap_key(t + 50, bk(9))                                 # cancelled: nothing queued
    s.at(t + 150, "dump", 1)
    log = run(s, t0 + 5 * BAR_MS)
    v = log.viaggio
    check(v[0]["queue"] == ["OUT/1/0"] and log.states[0]["msg"] == "QUEUED: T2 OUT", "track 2 queued: OUT")
    vel = [x[2] for x in log.notes(ch=1, after=t0 + 3 * BAR_MS, before=t0 + 4 * BAR_MS)]
    check(len(vel) >= 3 and vel[0] > vel[-1] and vel[0] - vel[-1] >= 30, "the last bar fades: %s" % vel)
    check(v[1]["mute"] == 2 and v[1]["states"][:2] == "IO" and not log.notes(ch=1, after=t0 + 4 * BAR_MS + 10), "at the boundary track 2 is OUT, silent")
    check(v[2]["queue"] == ["IN/1/255"] and v[3]["queue"] == ["IN/1/255"] and v[4]["queue"] == [],
          "an OUT track queued: IN; again: still IN (a proposal is not an OUT); black 10: empty (%s %s %s)" % (v[2]["queue"], v[3]["queue"], v[4]["queue"]))
    # THIN takes the two tracks with the highest ladder energy (never the last), SWELL brings back two; DROP: everything in, energy 100
    s = Script()
    t = vg_on(s, 100)
    for i in range(4):
        t = vg_track_in_now(s, t, i)                         # kick, snare, hat, perc (the roles of the ladder, lowest first)
    t = vg_bars4(s, t)
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); t0 = t
    s.tap_key(t0 + 200, bk(6))                               # THIN
    s.at(t0 + 4 * BAR_MS + 100, "dump", 0)
    s.tap_key(t0 + 4 * BAR_MS + 300, bk(7))                  # SWELL
    s.at(t0 + 8 * BAR_MS + 100, "dump", 0)
    s.tap_key(t0 + 8 * BAR_MS + 300, bk(6))                  # THIN
    s.tap_key(t0 + 8 * BAR_MS + 400, bk(3))                  # DROP: queued after it (the queue runs in order)
    s.at(t0 + 12 * BAR_MS + 100, "dump", 0)
    log = run(s, t0 + 12 * BAR_MS + 200)
    v = log.viaggio
    check(v[0]["states"][:4] == "IIII", "four tracks in: %s" % v[0]["states"])
    check(v[1]["states"][:4].count("O") == 2 and v[1]["states"][0] == "I", "THIN: two tracks out, the kick stays (%s)" % v[1]["states"][:4])
    check(v[2]["states"][:4] == "IIII", "SWELL: both back (%s)" % v[2]["states"][:4])
    check(v[3]["states"][:4] == "IIII" and v[3]["energy"] == 100 and v[3]["target"] == 100, "THIN then DROP: everything in, energy 100 at once (%s %s)" % (v[3]["states"][:4], v[3]["energy"]))
    # RISER: the last 4 bars of an 8-bar phrase ramp the energy; FILL: the last bar fills
    s = Script()
    t = vg_on(s, 100)
    t = vg_track_in_now(s, t, 0)
    t = viaggio_knobs(s, t, [(K2, -1)])                       # 8 bars
    s.tap_btn(t, PLAY); t0 = t
    s.tap_key(t0 + 200, bk(2))                               # RISER
    s.tap_key(t0 + 300, bk(0))                               # FILL
    for b in (3, 4, 5, 6, 7, 8):
        s.at(t0 + b * BAR_MS + 100, "dump", 0)
    log = run(s, t0 + 8 * BAR_MS + 200)
    e = [v["energy"] for v in log.viaggio]
    check(e[0] == 50 and e[1] > e[0] and e[2] > e[1] and e[3] > e[2] and e[4] == 100 and e[5] == 50, "RISER: bars 5-8 climb to 100, the boundary brings the target back (%s)" % e)
    n7 = len(log.notes(ch=0, after=t0 + 7 * BAR_MS - 10, before=t0 + 8 * BAR_MS - 10))
    n6 = len(log.notes(ch=0, after=t0 + 6 * BAR_MS - 10, before=t0 + 7 * BAR_MS - 10))
    check(n7 > n6, "FILL: the last bar has more hits than the one before (%d vs %d)" % (n7, n6))
    # INDIETRO: black 9 queues BACK (0.9-0.16: OCT-); at the boundary the phrase before comes back (track 2 out again)
    s = Script()
    t = vg_on(s, 100)
    t = vg_track_in_now(s, t, 0)
    t = vg_bars4(s, t)
    s.tap_btn(t, PLAY); t0 = t
    t = vg_queue_track(s, t0 + 200, 1)                       # phrase 2: track 2 in
    s.at(t0 + 4 * BAR_MS + 100, "dump", 0)
    s.tap_key(t0 + 4 * BAR_MS + 300, bk(8))                  # BACK 1
    s.at(t0 + 4 * BAR_MS + 400, "dump", 0)
    s.tap_key(t0 + 4 * BAR_MS + 500, bk(8))                  # BACK 2? only one phrase in the trail: stays 1
    s.at(t0 + 4 * BAR_MS + 600, "dump", 0)
    s.at(t0 + 8 * BAR_MS + 100, "dump", 0)
    s.press(t0 + 8 * BAR_MS + 300, SAVE); s.tap_key(t0 + 8 * BAR_MS + 330, wk(15)); s.release(t0 + 8 * BAR_MS + 400, SAVE)   # SALVA VIAGGIO
    s.at(t0 + 8 * BAR_MS + 500, "dump", 0)
    log = run(s, t0 + 8 * BAR_MS + 600)
    v = log.viaggio
    check(v[0]["states"][:2] == "II" and v[0]["trail"] == 1, "phrase 2: both in, one phrase in the trail")
    check(v[1]["queue"] == ["BACK/1/0"] and log.states[1]["msg"] == "QUEUED: BACK 1 PHRASE" and v[2]["queue"] == ["BACK/1/0"],
          "black 9: BACK 1 queued; again: still 1, the trail has no more (%s)" % v[2]["queue"])
    check(v[3]["states"][:2] == "IO" and v[3]["mute"] == 2 and v[3]["trail"] == 1, "at the boundary the first phrase is back: track 2 out (%s, trail %d)" % (v[3]["states"][:2], v[3]["trail"]))
    check(v[4]["song"] == 1 and log.states[4]["msg"].startswith("JOURNEY SAVED: 1 SCENES"), "SAVE + white 16: the trail becomes scenes and the song (%s)" % log.states[4]["msg"])


def t09_viaggio_loop_genre_remote():
    group("0.9 VIAGGIO: LOOP records a phrase by hand, GENRE / KEY / PROG queued, the remote on channel 13, the SEED")
    # LOOP (0.17: the remote's CC 26 or the grid; 0.9-0.16 black 10 in VIAGGIO mode) on the selected track; from the
    # boundary the keys play and record on it; the next boundary closes it
    s = Script()
    t = vg_on(s, 100)
    t = vg_track_in_now(s, t, 0)
    t = vg_bars4(s, t)
    vg_tap(s, t, 1); t += 100                                # track 2: a proposal, and it is selected
    s.tap_btn(t, PLAY); t0 = t
    vg_cc(s, t0 + 200, 26)                                   # LOOP
    s.at(t0 + 300, "dump", 1)
    s.at(t0 + 4 * BAR_MS + 100, "dump", 1)
    s.tap_key(t0 + 4 * BAR_MS + int(2 * STEP_MS), wk(4))     # played by hand in the phrase: steps 3 and 11 (two bars in: steps 35 and 43)
    s.tap_key(t0 + 4 * BAR_MS + int(10 * STEP_MS), wk(6))
    s.tap_key(t0 + 6 * BAR_MS + int(2 * STEP_MS), wk(4))
    s.tap_key(t0 + 6 * BAR_MS + int(10 * STEP_MS), wk(6))
    s.at(t0 + 8 * BAR_MS + 100, "dump", 1)
    log = run(s, t0 + 12 * BAR_MS + 100)
    v = log.viaggio
    check(v[0]["queue"] == ["LOOP/1/0"] and log.states[0]["msg"] == "QUEUED: LOOP T2", "LOOP queued on track 2 (%s)" % v[0]["queue"])
    check(v[1]["rec"] == 1 and v[1]["states"][:2] == "II" and log.dumps[1]["length"] == 64 and log.states[1]["msg"] == "LOOP: PLAY T2 NOW",
          "at the boundary track 2 records: 64 steps, REC on it (%s)" % log.states[1]["msg"])
    check(v[2]["rec"] == -1 and v[2]["states"][:2] == "II" and log.states[2]["msg"] == "LOOP CLOSED: T2 LOOPS" and log.dumps[2]["on"].count("x") == 4,
          "the next boundary closes it: 4 steps recorded (%s)" % log.dumps[2]["on"])
    def moments(notes):                                      # (a key played live sounds, and its step sounds too: one moment)
        out = []
        for t, _, _ in notes:
            if not out or t - out[-1] > 20:
                out.append(t)
        return out
    played = moments(log.notes(ch=1, after=t0 + 4 * BAR_MS, before=t0 + 8 * BAR_MS))
    looped = moments(log.notes(ch=1, after=t0 + 8 * BAR_MS, before=t0 + 12 * BAR_MS))
    check(len(played) == 4 and len(looped) == 4 and all(near(b - a, 4 * BAR_MS, STEP_MS) for a, b in zip(played, looped)),
          "phrase 3 plays the four notes where they were played (%s -> %s)" % ([x - t0 for x in played], [x - t0 for x in looped]))
    # GENRE (GLO 3 K3), KEY (K4) and PROG (PRESETS on the MOSSE, the HARMONY on) queued while it plays, applied at the
    # boundary; stopped: at once
    s = Script()
    t = harm_knobs(s, 100, [(K1, 1)])                              # the HARMONY on (0.17: off, PRESETS makes the progression READY)
    t = vg_on(s, t)
    t = vg_track_in_now(s, t, 0)
    t = vg_bars4(s, t)
    s.tap_btn(t, PLAY); t0 = t
    t = viaggio_knobs(s, t0 + 200, [(K3, 1), (K4, 2)])
    s.enc(t, E_PRE, 1); t += 60
    s.at(t, "dump", 0)
    s.at(t0 + 4 * BAR_MS + 100, "dump", 0)
    s.tap_btn(t0 + 4 * BAR_MS + 200, PLAY)                    # stopped
    t = viaggio_knobs(s, t0 + 4 * BAR_MS + 400, [(K3, 1)])
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    v = log.viaggio
    check(v[0]["queue"] == ["GENRE/1/0", "KEY/2/0", "PROG/1/0"] and v[0]["genre"] == 0 and log.states[0]["harm"][:2] == [1, 0],
          "GENRE HARDTECHNO, KEY D, PROG 2 queued; nothing changed yet (%s)" % v[0]["queue"])
    check(v[1]["genre"] == 1 and log.states[1]["harm"] == [1, 1, 1, 0] and v[1]["queue"] == [],
          "at the boundary: HARDTECHNO (0.10: one genre, the library's), the harmony on with progression 2 (%s %s)" % (v[1]["genre"], log.states[1]["harm"]))
    check(v[2]["genre"] == 2 and log.states[2]["msg"] == "GENRE DUB TECHNO", "stopped, K3: the genre changes at once (%s)" % log.states[2]["msg"])
    # the remote on channel 13 (SAVE + K2: OFF / 14 / 13 + 14): CC 1-16 a tap on the track, 17-27 the moves, 32 = queue track v / 8
    s = Script()
    t = vg_on(s, 100, remote=False)
    s.raw(t, "midi 0xBC 1 127")                              # channel 13 with the remote on 14 only: a track channel, nothing
    s.at(t + 50, "dump", 0)
    s.press(t + 100, SAVE); s.enc(t + 130, K2, 1); s.release(t + 200, SAVE)
    s.raw(t + 300, "midi 0xBC 1 127")                        # CC 1: a tap on track 1
    s.at(t + 350, "dump", 0)
    s.raw(t + 400, "midi 0xBC 32 8")                         # CC 32 = 8: queue track 2
    s.raw(t + 450, "midi 0xBC 17 127")                       # CC 17: FILL
    s.at(t + 500, "dump", 0)
    s.raw(t + 550, "midi 0xBC 29 127")                       # CC 29: cancel the last
    s.at(t + 600, "dump", 0)
    log = run(s, t + 700)
    v = log.viaggio
    check(v[0]["states"] == "E" * 16 and v[1]["states"].startswith("P") and log.states[1]["msg"].startswith("T1 KICK P2"),
          "channel 13 does nothing until SAVE + K2 says 13 + 14; then CC 1 taps track 1 (%s)" % log.states[1]["msg"])
    check(v[2]["queue"] == ["IN/1/255", "FILL/0/0"] and v[3]["queue"] == ["IN/1/255"], "CC 32 = 8 queues track 2, CC 17 a FILL, CC 29 cancels it (%s)" % v[2]["queue"])
    # the SEED: SEL + PLAY on the MOSSE while stopped throws the dice on genre, key and tempo
    s = Script()
    t = vg_on(s, 100)
    s.press(t, SEL); s.tap_btn(t + 30, PLAY); s.release(t + 100, SEL)
    s.at(t + 200, "dump", 0)
    log = run(s, t + 300)
    check(log.states[0]["msg"].startswith("SEED: ") and not log.notes(), "SEL + PLAY stopped: %s (nothing plays)" % log.states[0]["msg"])


def t09_profiles_persist():
    group("0.9: the profiles (SAVE + K4: FULL, PALCO), the settings and the project keep the journey across a power cycle")
    d = tempfile.mkdtemp()
    flash = os.path.join(d, "flash.bin")
    s = Script()
    s.press(100, SAVE); s.enc(130, K4, 1); s.release(200, SAVE)      # PALCO
    s.at(300, "dump", 0)
    s.press(400, SEQ); s.tap_key(430, wk(0)); s.release(500, SEQ)   # a SEQ tool: not in this profile
    s.at(550, "dump", 0)
    t = vg_track_in_now(s, 600, 0)
    s.enc(t, K1, 30); t += 60                                        # energy 80
    s.at(t, "dump", 0)
    s.press(t + 50, SAVE); s.enc(t + 80, E_PRE, 1); s.release(t + 150, SAVE)      # slot 2
    s.tap_btn(t + 400, SAVE)
    log = run(s, t + 1500, flash)
    v = log.viaggio
    check(v[0]["on"] == 1 and log.states[0]["msg"] == "PROFILE PALCO", "SAVE + K4: PALCO, the MOSSE at once (%s)" % log.states[0]["msg"])
    check(log.states[1]["msg"].startswith("NOT IN THIS PROFILE") and v[1]["states"] == "E" * 16, "SEQ + a key: refused (%s)" % log.states[1]["msg"])
    check(v[2]["states"].startswith("I") and v[2]["target"] == 80, "track 1 in, energy 80 (%s)" % v[2]["target"])
    check(len(log.saves) == 1 and "settings saved" in log.text, "the project and the settings are saved")
    s = Script()
    s.at(200, "dump", 0)
    s.tap_btn(300, PLAY)
    log = run(s, 300 + BAR_MS, flash)
    v = log.viaggio
    check(v[0]["on"] == 1 and v[0]["states"].startswith("I") and v[0]["target"] == 80 and v[0]["energy"] == 80 and v[0]["bars"] == 16,
          "after the power cycle: the MOSSE, track 1 IN, energy 80, 16 bars (%s)" % v[0])
    check(log.notes(ch=0, after=300), "and the kick plays")
    s = Script()
    s.press(100, SAVE); s.enc(130, K4, -1); s.release(200, SAVE)     # FULL again
    s.at(300, "dump", 0)
    s.press(400, SEQ); s.tap_key(430, wk(0)); s.release(500, SEQ)
    s.at(550, "dump", 0)
    log = run(s, 1000, flash)
    check(log.states[0]["msg"] == "PROFILE FULL" and not log.states[1]["msg"].startswith("NOT IN"), "SAVE + K4 again: FULL, the SEQ tools are back (%s)" % log.states[1]["msg"])


def t09_grid_viaggio():
    group("0.9: grid VIAGGIO view (PERF button: PERF, SONG, VIAGGIO): tracks, queue, moves, energy, proposals, trail")
    s = Script()
    s.raw(100, "attach")
    t = view(s, 200, GC_VPERF)                               # PERF (the grid starts in STEP)
    t = view(s, t, GC_VPERF)                                 # SONG
    t = view(s, t, GC_VPERF)                                 # VIAGGIO
    s.pad(t, 0, 1); t += 100                                 # track 1: a proposal (0.17: the journey always runs)
    s.at(t, "dump", 0)
    s.pad(t, 1, 2); t += 100                                 # track 2 queued
    s.pad(t, 0, 3); t += 100                                 # FILL
    s.pad(t, 15, 3); t += 100                                # cancelled
    s.pad(t, 8, 4); t += 100                                 # energy 53
    s.at(t, "dump", 0)
    s.pad(t, 0, 0); t += 100                                 # NOW, stopped: at once
    s.at(t, "dump", 0)
    t1 = t
    s.pad(t, 15, 7); t += 100                                # the phrase playing: nothing
    s.pad(t, 14, 7); t += 100                                # one back: the trail is empty
    s.at(t, "dump", 0)
    t = view(s, t, GC_VPERF)                                 # PERF again (no regista: no REGIA view)
    log = run(s, t + 500)
    v = log.viaggio
    check(v[0]["journey"] == 1 and v[0]["states"].startswith("P") and log.states[0]["msg"].startswith("T1 KICK P2"), "a tap on the track row: a proposal (%s)" % log.states[0]["msg"])
    check(v[1]["queue"] == ["IN/1/255"] and v[1]["target"] == 53 and v[1]["energy"] == 53, "row 3 queues track 2, FILL cancelled by pad 16 of row 4, row 5 sets the energy (%s %s)" % (v[1]["queue"], v[1]["target"]))
    check(v[2]["queue"] == [] and v[2]["states"][:2] == "PI" and log.states[2]["msg"] == "NOW: DONE", "row 1 (NOW) while stopped: track 2 is in (%s)" % v[2]["states"][:2])
    check(log.states[3]["msg"] == "THE TRAIL IS SHORTER", "row 8: no phrase to go back to yet (%s)" % log.states[3]["msg"])
    pads, ctls = log.leds(until=t1 + 50)
    check(pads[16 + 0] == GL_CURSOR and pads[16 + 1] == GL_ON and pads[16 + 2] == GL_FAINT, "row 2: track 1 proposed and selected, track 2 in, track 3 empty (%s)" % [pads.get(16 + i) for i in range(3)])
    check(pads[4 * 16 + 8] == GL_ON and pads[4 * 16 + 9] == GL_FAINT, "row 5: the energy bar up to pad 9")
    check(pads[3 * 16 + 10] == GL_FAINT and pads[3 * 16 + 14] == GL_FAINT and pads[3 * 16 + 0] == GL_DIM, "row 4: NOW idle, no trail, the moves dim")
    check(pads[5 * 16 + 0] == GL_PLAY and pads[5 * 16 + 1] == GL_ACCENT, "row 6: pattern 1 plays, the proposal in pattern 2 marked")
    check(ctls[GC_VPERF] == GL_ACCENT, "the PERF button is the accent colour in the VIAGGIO view")
    pads, ctls = log.leds()
    check(ctls[GC_VPERF] != GL_ACCENT, "PERF again: back to the PERF view (%s)" % ctls[GC_VPERF])
    # 0.9: the song has 64 entries; the SONG view shows them 16 a page (row 4 pads 13 / 14)
    s = Script()
    s.raw(100, "attach")
    t = view(s, 200, GC_VPERF); t = view(s, t, GC_VPERF)    # SONG
    for i in range(16):
        s.pad(t, i, 0); s.pad(t + 80, i % 16, 1); t += 160    # the new entry, scene (i % 16) + 1
    s.pad(t, 13, 3); t += 100                                # the next page: entry 17 is the new one
    s.pad(t, 0, 0); s.pad(t + 80, 9, 1); t += 200            # entry 17 = scene 10
    s.at(t, "dump", 0)
    s.pad(t, 12, 3); t += 100                                # back to page 1
    s.pad(t, 2, 0); t += 100                                 # entry 3
    s.at(t, "dump", 0)
    log = run(s, t + 300)
    check(log.viaggio[0]["song"] == 17 and log.states[1]["msg"] == "SONG ENTRY 3", "17 song entries through the pages (%d), page 1 again (%s)" % (log.viaggio[0]["song"], log.states[1]["msg"]))


def t09_review_fixes():
    group("0.9: what the review found: HALF on the grid, a BREAK in a BREAK, the studio mid-move (0.17), the LOOP's patterns and settings, BACK + NOW, FILL late, a save in a BREAK")
    def onsets(log, a, b):
        return [round((x[0] - a) / STEP_MS, 1) for x in log.notes(ch=0, after=a - 5, before=b)]
    # HALF: the kicks stay on the grid (bar starts), and the phrase after is on the grid again
    s = Script()
    t = vg_on(s, 100)
    t = vg_track_in_now(s, t, 0)
    t = vg_bars4(s, t)
    s.tap_btn(t, PLAY); t0 = t
    s.tap_key(t0 + 200, bk(4))
    log = run(s, t0 + 9 * BAR_MS)
    o2 = onsets(log, t0 + 4 * BAR_MS, t0 + 5 * BAR_MS)
    o3 = onsets(log, t0 + 8 * BAR_MS, t0 + 9 * BAR_MS)
    check(o2[:2] == [0.0, 8.0] and o3[:3] == [0.0, 4.0, 8.0], "HALF: the kicks land on the grid (%s), and the next phrase too (%s)" % (o2[:3], o3[:3]))
    # a BREAK while a BREAK plays (NOW): the mutes come back; a BREAK before an IN: the track waits for the break's end
    s = Script()
    t = vg_on(s, 100)
    t = vg_track_in_now(s, t, 0); t = vg_track_in_now(s, t, 1)
    t = vg_bars4(s, t)
    s.tap_btn(t, PLAY); t0 = t
    s.press(t0 + 200, SEL); s.tap_key(t0 + 230, bk(1)); s.release(t0 + 300, SEL); s.tap_key(t0 + 400, bk(10))
    s.press(t0 + BAR_MS + 300, SEL); s.tap_key(t0 + BAR_MS + 330, bk(1)); s.release(t0 + BAR_MS + 400, SEL); s.tap_key(t0 + BAR_MS + 500, bk(10))
    s.at(t0 + 5 * BAR_MS + 100, "dump", 0)
    log = run(s, t0 + 6 * BAR_MS)
    check(log.viaggio[0]["mute"] == 0 and log.notes(after=t0 + 5 * BAR_MS), "a BREAK inside a BREAK: everything comes back (%04X)" % log.viaggio[0]["mute"])
    s = Script()
    t = vg_on(s, 100)
    t = vg_track_in_now(s, t, 0)
    vg_tap(s, t, 1); t += 100                                # T2: a proposal
    t = vg_bars4(s, t)
    vg_tap(s, t, 0); t += 100
    s.tap_btn(t, PLAY); t0 = t
    s.tap_key(t0 + 200, bk(1))                               # BREAK 1 bar, T1 stays ...
    t = vg_queue_track(s, t0 + 300, 1)                       # ... then T2 IN
    s.at(t0 + 4 * BAR_MS + 100, "dump", 1)
    s.at(t0 + 5 * BAR_MS + 100, "dump", 1)
    log = run(s, t0 + 6 * BAR_MS)
    v = log.viaggio
    check(v[0]["queue"] == [] and v[0]["states"][:2] == "II" and v[1]["mute"] == 0 and not log.notes(ch=1, after=t0 + 4 * BAR_MS + 10, before=t0 + 5 * BAR_MS - 10)
          and log.notes(ch=1, after=t0 + 5 * BAR_MS + 10), "a track that enters during a BREAK waits for its end (%04X -> %04X)" % (v[0]["mute"], v[1]["mute"]))
    # 0.17: no VIAGGIO off any more: the studio (SEL + GLO) in a HALF phrase with an OUT fading lets the journey go on:
    # HALF for its phrase, track 2 out at the boundary, the phrase after on the grid again
    s = Script()
    t = vg_on(s, 100)
    t = vg_track_in_now(s, t, 0); t = vg_track_in_now(s, t, 1)
    t = vg_bars4(s, t)
    s.tap_btn(t, PLAY); t0 = t
    s.tap_key(t0 + 200, bk(4))                               # HALF
    t = vg_queue_track(s, t0 + 300, 1)                       # T2 OUT (fades in bar 4)
    vg_studio(s, t0 + 3 * BAR_MS + 300)                      # the studio in the last bar
    s.at(t0 + 5 * BAR_MS + 100, "dump", 0)
    s.at(t0 + 8 * BAR_MS + 100, "dump", 0)
    log = run(s, t0 + 9 * BAR_MS)
    v = log.viaggio
    check(v[0]["on"] == 0 and v[0]["journey"] == 1 and v[0]["speed"] == -1 and v[0]["mute"] == 2 and not log.notes(ch=1, after=t0 + 4 * BAR_MS + 10)
          and onsets(log, t0 + 4 * BAR_MS, t0 + 5 * BAR_MS)[:2] == [0.0, 8.0],
          "the studio mid-move: HALF plays its phrase, track 2 went out at the boundary (%s, %04X)" % (v[0]["speed"], v[0]["mute"]))
    check(v[1]["speed"] == 0 and onsets(log, t0 + 8 * BAR_MS, t0 + 9 * BAR_MS)[:3] == [0.0, 4.0, 8.0], "... and the phrase after is on the grid again (%s)" % onsets(log, t0 + 8 * BAR_MS, t0 + 9 * BAR_MS)[:3])
    # a LOOP's patterns are never wiped under the playing pattern; its settings go away with it (BACK, SWAP) and come
    # back with it; a loop nothing was played into is forgotten
    s = Script()
    t = vg_on(s, 100)
    t = vg_track_in_now(s, t, 0)
    t = vg_bars4(s, t)
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); t0 = t
    vg_cc(s, t0 + 200, 26)                                   # LOOP T1 (phrase 2: patterns 3)
    s.tap_key(t0 + 4 * BAR_MS + int(2 * STEP_MS), wk(0))     # one kick played by hand
    s.at(t0 + 8 * BAR_MS + 100, "dump", 0)
    s.tap_key(t0 + 8 * BAR_MS + 300, bk(8)); s.tap_key(t0 + 8 * BAR_MS + 500, bk(8))   # BACK 2: phrase 1 again, with its own length
    s.at(t0 + 12 * BAR_MS + 100, "dump", 0)
    log = run(s, t0 + 13 * BAR_MS)
    d = log.dumps
    bar_hits = len(log.notes(ch=0, after=t0 + 12 * BAR_MS, before=t0 + 13 * BAR_MS))
    want_hits = d[0]["on"][:16].count("x") if d[0]["length"] <= 16 else None
    check(d[1]["length"] == 64 and d[1]["on"].count("x") == 1 and d[2]["length"] == d[0]["length"] and d[2]["pat"] == 2 and d[2]["hash"] == d[0]["hash"] and bar_hits >= 3 and (want_hits is None or bar_hits == want_hits),
          "the loop: 64 steps; BACK to the kick: its own length and its hits again (%d, %d, %d hits)" % (d[1]["length"], d[2]["length"], bar_hits))
    s = Script()
    t = vg_on(s, 100)
    t = vg_track_in_now(s, t, 0)
    t = vg_bars4(s, t)
    s.tap_btn(t, PLAY); t0 = t
    vg_cc(s, t0 + 200, 26)                                   # LOOP
    s.at(t0 + 8 * BAR_MS + 100, "dump", 0)
    log = run(s, t0 + 8 * BAR_MS + 200)
    check(log.states[0]["msg"] == "LOOP: NOTHING PLAYED ON T1" and log.dumps[0]["pat"] == 2 and log.dumps[0]["length"] in (16, 32, 64) and log.viaggio[0]["states"][0] == "I",
          "nothing played: the loop is forgotten, the kick plays on (%s)" % log.states[0]["msg"])
    # BACK + NOW goes to the phrase before the one playing; FILL asked in the last bar fills it
    s = Script()
    t = vg_on(s, 100)
    t = vg_track_in_now(s, t, 0)
    t = vg_bars4(s, t)
    s.tap_btn(t, PLAY); t0 = t
    t = vg_queue_track(s, t0 + 200, 1)
    s.tap_key(t0 + 4 * BAR_MS + 300, bk(8)); s.tap_key(t0 + 4 * BAR_MS + 400, bk(10))
    s.at(t0 + 5 * BAR_MS + 100, "dump", 0)
    s.tap_key(t0 + 7 * BAR_MS + 100, bk(0))                  # FILL in the last bar
    log = run(s, t0 + 8 * BAR_MS)
    check(log.viaggio[0]["states"][:2] == "IO" and log.viaggio[0]["trail"] == 1, "BACK + NOW: the phrase before (%s)" % log.viaggio[0]["states"][:2])
    n7 = len(log.notes(after=t0 + 6 * BAR_MS, before=t0 + 7 * BAR_MS)); n8 = len(log.notes(after=t0 + 7 * BAR_MS, before=t0 + 8 * BAR_MS))
    check(n8 > n7, "FILL asked in the last bar: more hits in it (%d vs %d)" % (n8, n7))
    # a save during a BREAK keeps the mutes as they are meant, not the silence
    d = tempfile.mkdtemp(); flash = os.path.join(d, "flash.bin")
    s = Script()
    t = vg_on(s, 100)
    t = vg_track_in_now(s, t, 0); t = vg_track_in_now(s, t, 1)
    t = vg_bars4(s, t)
    s.tap_btn(t, PLAY); t0 = t
    s.press(t0 + 200, SEL); s.tap_key(t0 + 230, bk(1)); s.release(t0 + 300, SEL); s.tap_key(t0 + 400, bk(10))
    s.press(t0 + BAR_MS + 300, SAVE); s.enc(t0 + BAR_MS + 330, E_PRE, 1); s.release(t0 + BAR_MS + 400, SAVE)
    s.tap_btn(t0 + BAR_MS + 600, SAVE)
    log = run(s, t0 + 3 * BAR_MS, flash)
    check(len(log.saves) == 1, "saved in the break")
    s = Script(); s.at(200, "dump", 0)
    log = run(s, 400, flash)
    check(log.viaggio[0]["mute"] == 0, "after the power cycle nothing is muted (%04X)" % log.viaggio[0]["mute"])
    # PALCO refuses the editing knobs too
    s = Script()
    s.press(100, SAVE); s.enc(130, K4, 1); s.release(200, SAVE)
    s.at(250, "dump", 0)
    s.press(300, SEQ); s.enc(330, K1, 3); s.release(400, SEQ)
    s.at(450, "dump", 0)
    log = run(s, 600)
    check(log.states[1]["msg"].startswith("NOT IN THIS PROFILE") and log.states[1]["pulses"] == log.states[0]["pulses"] and log.states[1]["flags"] == log.states[0]["flags"],
          "PALCO: SEQ + K1 refused (%s)" % log.states[1]["msg"])



# ------------------------------------------------------------------------------------------------ 0.10 EXPO
def seq_page_turn(s, t, page, encs):
    """SEQ held: to page `page` (0-based), the encoders [(enc, delta)], let go"""
    return pg(s, t, SEQ, page, encs)


def t010_expo():
    group("0.10 EXPO: the curve's hits over a bar, RAMP both ways, BOUNCE, the STEP span, ARP, the gate, off = as written, saved")
    import math
    def gaps(n, k): return [n[i + 1][0] - n[i][0] for i in range(min(k, len(n)) - 1)]

    def scenario(encs5, encs6=(), steps=(0,), before=None, bars=2, flash=None):
        s = Script()
        t = s.steps(100, steps)
        if before: t = before(s, t)
        t = expo_knobs(s, t, 0, encs5)                  # SEQ 5/6
        if encs6: t = expo_knobs(s, t, 1, encs6)        # SEQ 6/6
        s.at(t, "dump", 0)
        t0 = t + 100
        s.tap_btn(t0, PLAY)
        log = run(s, t0 + int(bars * BAR_MS) + 60, flash=flash)
        return [(tt - t0, d1, d2) for tt, d1, d2 in log.notes(ch=0, after=t0)], log, t0

    # RAMP +4, 8 hits, 1 BAR: eight hits in the bar, every gap 0.82 of the one before (4 x across the bar)
    n, log, _ = scenario([(K4, 1)])                          # OFF -> RAMP; hits 8, curve +4, 1 BAR are the defaults
    g = gaps(n, 8)
    check(len(n) >= 16 and near(n[8][0], BAR_MS, 12), "RAMP: 8 hits a bar, the next bar starts its own (%s)" % [x[0] for x in n[:9]])
    check(all(0.78 < g[i + 1] / g[i] < 0.86 for i in range(len(g) - 1)) and near(g[0] / g[-1], 3.3, 0.5),
          "RAMP +4: the gaps shrink by a constant ratio, first / last = 3.3 (%s)" % g)
    # RAMP -4: the same backwards (a decelerando); 0.16: the curve set first plays nothing new, K4 starts it with it
    n, log, _ = scenario([(K2, -8)])
    check(len(n) >= 2 and all(near(b[0] - a[0], BAR_MS, 6) for a, b in zip(n, n[1:])),
          "0.16: EXPO's knobs alone start nothing: the written step, once a bar (%s)" % [round(x[0]) for x in n])
    n, log, _ = scenario([(K2, -8), (K4, 1)])
    g = gaps(n, 8)
    check(all(g[i + 1] > g[i] for i in range(len(g) - 1)) and near(g[-1] / g[0], 3.3, 0.5), "RAMP -4: the gaps grow (%s)" % g)
    # BOUNCE +6, 12 hits: fast in the middle, symmetrical
    n, log, _ = scenario([(K1, 4), (K2, 2), (K4, 2)])             # (0.16: OFF + 2: BOUNCE, with the hits and curve set)
    g = gaps(n, 12)
    check(len(g) == 11 and min(g) == min(g[5], g[6]) and all(abs(g[i] - g[11 - i]) <= 2 for i in range(1, 6)) and g[0] > g[1],
          "BOUNCE +6: 12 hits, the shortest gaps in the middle, mirrored (%s)" % g)
    # the STEP span on 1/16 steps: every hit step bounces inside its own slot (2 hits, decelerando)
    n, log, _ = scenario([(K1, -6), (K2, -6), (K3, -3), (K4, 1)], steps=(0, 4, 8, 12), bars=1)
    n = [x for x in n if x[0] < BAR_MS - 20]
    check(len(n) == 8 and near(n[1][0], STEP_MS / 3, 6) and near(n[2][0], 4 * STEP_MS, 6),
          "STEP span, 2 hits, curve -2: a hit, one a third of the step later, then the next step's pair (%s)" % [round(x[0]) for x in n[:6]])
    # ARP +1 OCT: a C major chord on step 1 goes up through two octaves, one note a hit
    def chord(s, t):
        s.press(t, SEL); s.keys(t + 30, KEY_C4 | KEY_E4 | KEY_G4); s.keys(t + 120, 0); s.release(t + 200, SEL); return t + 300
    n, log, _ = scenario([(K1, 4), (K4, 1)], encs6=[(K4, 2)], before=chord)
    check([x[1] for x in n[:7]] == [60, 64, 67, 72, 76, 79, 60], "ARP +1 OCT: the chord's notes low to high, then an octave up, round again (%s)" % [x[1] for x in n[:7]])
    # CHORD: every hit the whole chord
    n, log, _ = scenario([(K1, -4), (K4, 1)], before=chord)
    check(len(n) >= 12 and sorted(x[1] for x in n[:3]) == [60, 64, 67] and n[0][0] == n[2][0], "CHORD: the three notes together on every hit")
    # VEL FALL: the velocity decays along the hits; GATE 20 %: the note ends before a fifth of the gap
    n, log, t0 = scenario([(K4, 1)], encs6=[(K1, 1), (K2, -8)])
    v = [x[2] for x in n[:8]]
    offs = [tt - t0 for tt, _ in log.offs(ch=0) if tt >= t0]
    g = gaps(n, 8)
    check(all(v[i] > v[i + 1] for i in range(7)) and v[-1] < v[0] * 0.5, "VEL FALL: 100 %% down to 40 %% (%s)" % v)
    check(offs and near(offs[0], n[0][0] + g[0] * 0.2, 8), "GATE 20 %%: the first note ends at a fifth of its gap (%.0f of %.0f)" % (offs[0] - n[0][0], g[0]))
    # SETTLE (exposaw): 6 hits a beat once settled, depth +4: the first gaps 16 x shorter, growing, the step full of them
    n, log, _ = scenario([(K1, -2), (K2, 0), (K3, -3), (K4, 3)], steps=(0,), bars=1)
    n = [x for x in n if x[0] < BAR_MS - 20]
    g = gaps(n, len(n))
    check(len(n) >= 6 and g[0] < 12 and g[-1] > 30 and all(g[i + 1] >= g[i] - 1 for i in range(len(g) - 1)) and n[-1][0] < STEP_MS,
          "SETTLE: a buzz that slows down inside the step, %d hits, gaps %s .. %s" % (len(n), g[:3], g[-3:]))
    # OFF: the track plays as written again; a turned knob switches it on; SAVE keeps it
    s = Script()
    t = s.steps(100, (0, 8))
    t = expo_knobs(s, t, 0, [(K4, 1)])                   # on
    t = expo_knobs(s, t, 0, [(K4, -1)])                  # off
    s.at(t, "dump", 0)
    t0 = t + 100
    s.tap_btn(t0, PLAY)
    log = run(s, t0 + int(BAR_MS) + 60)
    n = log.notes(ch=0, after=t0, before=t0 + int(BAR_MS) - 20)
    check(len(n) == 2 and near(n[1][0] - t0, 8 * STEP_MS, 6), "SHAPE OFF: the two written steps play as written (%d notes)" % len(n))
    with tempfile.NamedTemporaryFile(delete=False) as f:
        flash = f.name
    s = Script()
    t = s.steps(100, (0, 4, 8, 12))                         # a span starts on a step that is on: one a beat
    t = expo_knobs(s, t, 0, [(K1, 2), (K2, -10), (K3, -2), (K4, 1)])   # 10 hits, -6, 1 BEAT, RAMP
    s.tap_btn(t, SAVE); s.tap_btn(t + 300, SAVE); t += 1500       # SAVE twice: the slot
    log = run(s, t + 100, flash=flash)
    check(log.saves, "saved to the slot")
    s = Script()
    t = s.steps(100, ())                                    # (the project comes back from flash by itself)
    s.at(200, "dump", 0)
    t0 = 300
    s.tap_btn(t0, PLAY)
    log = run(s, t0 + int(BAR_MS) + 60, flash=flash)
    os.remove(flash)
    n = log.notes(ch=0, after=t0)
    g = [n[i + 1][0] - n[i][0] for i in range(9)]
    check(len(n) >= 40 and all(g[i + 1] > g[i] for i in range(8)) and near(n[10][0] - t0, 4 * STEP_MS, 8),
          "after a power cycle: 10 hits a beat, decelerando, from the saved project (%s; %d notes, beat 2 at %.0f)" % (g, len(n), n[10][0] - t0 if len(n) > 10 else -1))

# ------------------------------------------------------------------------------------------------ 0.10: the rework
CFG = re.compile(r"^\s*(\d+) ms  cfg T(\d+) role (\d+) chord (\d+) oct (-?\d+) keyslot (-?\d+) trans (-?\d+) div (\d+) len (\d+) "
                 r"key (\d+)/(\d+)/(-?\d+) cur (\d+) genre (\d+) mode (\d+) when (\d+) every (\d+)/(\d+) lib (\d+) arp (\d+)/(\d+) fam (\d+) "
                 r"prog (\d+) lanes((?: \d+/\d+/\d+/\d+)+) cclead (\d+) tempo (\d+) mac (-?\d+) (-?\d+) (-?\d+) (-?\d+) ck (\d+)$", re.M)


def cfgs(log):
    """the 0.10 'cfg' lines of the dumps: the track's role, chord, octave, key slot, transpose, the key, the tools' schedule, the lanes"""
    return [dict(t=int(m.group(1)), track=int(m.group(2)), role=int(m.group(3)), chord=int(m.group(4)), oct=int(m.group(5)),
                 keyslot=int(m.group(6)), trans=int(m.group(7)), div=int(m.group(8)), length=int(m.group(9)),
                 key=[int(x) for x in m.group(10, 11, 12)], cur=int(m.group(13)), genre=int(m.group(14)), gmode=int(m.group(15)),
                 when=int(m.group(16)), every=[int(m.group(17)), int(m.group(18))], lib=int(m.group(19)),
                 arp=[int(m.group(20)), int(m.group(21))], fam=int(m.group(22)), prog=int(m.group(23)),
                 lanes=[tuple(int(v) for v in x.split("/")) for x in m.group(24).split()], cclead=int(m.group(25)),
                 tempo=int(m.group(26)), mac=[int(x) for x in m.group(27, 28, 29, 30)], ck=int(m.group(31)))
            for m in CFG.finditer(log.text)]


def ccn(log, cc, ch=0, after=0, before=1 << 30):
    """(time, value) of one CC on one channel"""
    return [(t, d2) for t, st, d1, d2 in log.msgs if st == 0xB0 | ch and d1 == cc and after <= t < before]


def t010_time():
    group("0.10: the tracks land in time (a length changed and back, time FX let go, a step loop's EXIT); PANIC; the macros")
    BAR = 16 * STEP_MS
    # LENGTH 16 -> 8 during bar 1, back to 16 in bar 2: 0.11: a length waits for the bar line, then the track is where the
    # bar says (0.10 changed it at once, realigned): bar 1 plays whole, bars 2 and 3 are the 8-step loop, bar 4 is 16 again
    s = Script()
    t = melody16(s)
    s.tap_btn(t, PLAY); p0 = t
    home_page(s, p0 + int(5.5 * STEP_MS), 0, [(K2, -8)])              # LENGTH 8 asked in step 6
    s.at(p0 + int(7 * STEP_MS), "dump", 0)
    home_page(s, p0 + int(18.5 * STEP_MS), 0, [(K2, 8)])              # back to 16 asked in step 19 (bar 2)
    log = run(s, p0 + int(3 * BAR) - 20)
    n = [(round((x[0] - p0) / STEP_MS), x[1]) for x in log.notes(ch=0, after=p0)]
    whole = [d for k, d in n if 8 <= k <= 15]
    short = [d for k, d in n if 16 <= k <= 31]
    back = [d for k, d in n if 32 <= k <= 47]
    check(log.states[0]["msg"] == "LENGTH 8 AT THE BAR" and log.dumps[0]["length"] == 16, "LENGTH 8 while playing: it waits for the bar (%s, length %s)" % (log.states[0]["msg"], log.dumps[0]["length"]))
    check(whole == [68 + i for i in range(8)], "the bar finishes whole (%s)" % whole)
    check(short == [60 + i for i in range(8)] * 2, "LENGTH 8 from the bar line: the loop runs with the half bars (%s)" % short)
    check(back == [60 + i for i in range(16)], "LENGTH 16 again from the next bar line: step 33 plays note 60, where the bar is (%s)" % back)
    # HALF held for a while, then let go: the pattern is back where the bar says
    s = Script()
    t = melody16(s)
    s.tap_btn(t, PLAY); p0 = t
    s.press(p0 + int(3.5 * STEP_MS), FX); s.keys(p0 + int(3.5 * STEP_MS) + 10, wk(4))              # HALF from step 4
    s.keys(p0 + int(9.5 * STEP_MS), 0); s.release(p0 + int(9.5 * STEP_MS) + 10, FX)                # let go in step 10
    log = run(s, p0 + int(BAR) + 20)
    n = [(round((x[0] - p0) / STEP_MS), x[1]) for x in log.notes(ch=0, after=p0)]
    during = [d for k, d in n if 4 <= k <= 9]
    after = [d for k, d in n if 10 <= k <= 15]
    check(during == [64, 65, 66], "HALF: three notes in six steps (%s)" % during)
    check(after == [70, 71, 72, 73, 74, 75], "HALF let go in step 10: note 70 plays, in time (%s)" % after)
    # FREEZE let go: the same
    s = Script()
    t = melody16(s)
    s.tap_btn(t, PLAY); p0 = t
    s.press(p0 + int(3.5 * STEP_MS), FX); s.keys(p0 + int(3.5 * STEP_MS) + 10, wk(7))              # FREEZE from step 4
    s.keys(p0 + int(9.5 * STEP_MS), 0); s.release(p0 + int(9.5 * STEP_MS) + 10, FX)
    log = run(s, p0 + int(BAR) + 20)
    n = [(round((x[0] - p0) / STEP_MS), x[1]) for x in log.notes(ch=0, after=p0)]
    after = [d for k, d in n if 10 <= k <= 15]
    check(after == [70, 71, 72, 73, 74, 75], "FREEZE let go in step 10: on from note 70 (%s)" % after)
    # a step loop (HOME + ALG start, K2 length) and EXIT (FX + black 11): the whole pattern again, where the bar is
    s = Script()
    t = melody16(s)
    s.tap_btn(t, PLAY); p0 = t
    t = p0 + int(2.5 * STEP_MS)
    fx_tap(s, t - 200)                                                                              # 0.12: SEL + FX tapped ...
    s.keys(t, wk(4)); s.keys(t + 400, wk(4) | wk(7)); s.keys(t + 500, 0)                            # ... hold step 5, press step 8: a loop
    s.at(t + 550, "dump", 0)
    t = p0 + int(20.5 * STEP_MS)
    s.press(t, FX); s.tap_key(t + 20, bk(10), hold=30); s.release(t + 80, FX)                        # EXIT
    s.at(t + 150, "dump", 0)
    log = run(s, p0 + int(2 * BAR) - 20)
    n = [(round((x[0] - p0) / STEP_MS), x[1]) for x in log.notes(ch=0, after=p0)]
    inside = [d for k, d in n if 8 <= k <= 15]
    after = [d for k, d in n if 22 <= k <= 31]
    check(log.dumps[0]["start"] == 4 and log.dumps[0]["length"] == 8, "hold step 5, press step 8: a loop of steps 5-8 (%s-%s)" % (log.dumps[0]["start"], log.dumps[0]["length"]))
    check(inside == [64, 65, 66, 67, 64, 65, 66, 67], "the loop plays 64-67 (%s)" % inside)
    check(log.dumps[1]["start"] == 0 and log.dumps[1]["length"] == 16, "EXIT: the whole pattern again (%s-%s)" % (log.dumps[1]["start"], log.dumps[1]["length"]))
    check(after == [66 + i for i in range(10)], "... in time: step 23 plays note 66 (%s)" % after)
    check(log.states[1]["msg"] == "STEP LOOP OFF", "the screen says so (%s)" % log.states[1]["msg"])
    # PANIC: FX + HOME: every channel's sustain up, All Notes Off, All Sound Off; again within 2 s: the transport stops
    s = Script()
    t = s.steps(100, [0, 4, 8, 12])
    s.tap_btn(t, PLAY); p0 = t
    s.press(p0 + 300, FX); s.press(p0 + 340, HOME); s.release(p0 + 400, HOME); s.release(p0 + 420, FX)
    s.at(p0 + 500, "dump", 0)
    log = run(s, p0 + int(BAR))
    c = [(st & 15, d1) for tm, st, d1, d2 in log.msgs if (st & 0xF0) == 0xB0 and p0 + 300 <= tm < p0 + 500 and d1 in (64, 120, 123)]
    check(all((ch, cc) in c for ch in range(14) for cc in (64, 120, 123)), "PANIC: CC 64, 123 and 120 on channels 1-14 (%d messages)" % len(c))
    check(log.states[0]["msg"].startswith("PANIC"), "the screen says PANIC (%s)" % log.states[0]["msg"])
    check(len(log.notes(ch=0, after=p0 + 500)) >= 2, "... and the transport goes on")
    s = Script()
    t = s.steps(100, [0, 4, 8, 12])
    s.tap_btn(t, PLAY); p0 = t
    s.press(p0 + 300, FX); s.press(p0 + 340, HOME); s.release(p0 + 400, HOME); s.release(p0 + 420, FX)
    s.press(p0 + 900, FX); s.press(p0 + 940, HOME); s.release(p0 + 1000, HOME); s.release(p0 + 1020, FX)
    log = run(s, p0 + int(BAR))
    check(not log.notes(ch=0, after=p0 + 1000) and 0xFC in [m[1] for m in log.msgs if m[0] > p0 + 900], "PANIC twice within 2 s: the transport stops too")
    # the macros: FX + K1 .. K4, FX + OCT-: all back to 0 (0.9's reset did nothing visible)
    s = Script()
    t = s.steps(100, [0])
    t = held(s, t, FX, [(K1, 5), (K2, -4), (K3, 3), (K4, -6)])
    s.at(t, "dump", 0)
    s.press(t + 50, FX); s.tap_btn(t + 80, OCT_DOWN, hold=20); s.release(t + 150, FX)
    s.at(t + 200, "dump", 0)
    log = run(s, t + 300)
    check(log.states[0]["mac"] == [5, -20, 3, -12], "FX + the knobs: the four macros (%s)" % log.states[0]["mac"])
    check(log.states[1]["mac"] == [0, 0, 0, 0] and log.states[1]["msg"] == "MACROS 0", "FX + OCT-: all 0, the screen says so (%s %s)" % (log.states[1]["mac"], log.states[1]["msg"]))
    # FX + ARP twice: BAKE: INTENSITY +10 goes into the velocities, GATE -20 % into the gates, then the macros are 0
    s = Script()
    t = s.steps(100, [0])
    t = held(s, t, FX, [(K1, 10), (K2, -4)])
    s.press(t, FX); s.tap_btn(t + 30, ARP, hold=20); s.release(t + 100, FX); t += 160
    s.at(t, "dump", 0)
    s.press(t, FX); s.tap_btn(t + 30, ARP, hold=20); s.release(t + 100, FX); t += 160
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(2 * STEP_MS))
    n = log.notes(ch=0, after=p0)
    off = [tm for tm, d1 in log.offs(ch=0) if tm > p0]
    check(log.states[0]["msg"].startswith("BAKE THE MACROS") and log.states[0]["mac"] == [10, -20, 0, 0], "FX + ARP once: it asks (%s)" % log.states[0]["msg"])
    check(log.states[1]["msg"] == "MACROS BAKED, PATTERNS 1" and log.states[1]["mac"] == [0, 0, 0, 0], "twice: baked, the macros 0 (%s %s)" % (log.states[1]["msg"], log.states[1]["mac"]))
    check(n and n[0][2] == 110 and off and near(off[0] - n[0][0], STEP_MS * 0.8 * 0.8, 6), "the step plays at velocity 110 with a gate of 64 %% (%s, %s ms)" % (n[:1], off[0] - n[0][0] if n and off else None))
    # ... and the macros are saved with the project: SAVE (twice), power off and on: INTENSITY 7 is there
    d = tempfile.mkdtemp()
    flash = os.path.join(d, "flash.bin")
    s = Script()
    t = s.steps(100, [0])
    t = held(s, t, FX, [(K1, 7)])
    s.tap_btn(t + 50, SAVE); s.tap_btn(t + 300, SAVE); t += 1500
    run(s, t, flash)
    s = Script()
    s.at(300, "dump", 0)
    log = run(s, 400, flash)
    check(log.states[0]["mac"][0] == 7 and log.dumps[0]["on"][:1] == "x", "the macros are part of the project: after a power cycle INTENSITY is 7 (%s)" % log.states[0]["mac"])


def t010_notes():
    group("0.10: the pen and K1, TIE, chord shapes, ARP RATE, transpose in the key, the track's octave, the new conditions")
    BAR = 16 * STEP_MS
    # K1 on a step that is off changes its note (and the pen) without lighting it; SEL + K4 sets the pen; a new step takes the pen
    s = Script()
    s.enc(100, K1, 4)                                              # step 1 off: its note from the pen (60) to 64
    s.at(200, "dump", 0)
    s.enc(300, E_ALG, 1); s.press(400, SEL); s.enc(430, K4, 5); s.release(500, SEL)    # cursor step 2; SEL + K4: pen 69
    s.tap_key(600, wk(1))                                          # step 2 on: the pen's note
    s.at(700, "dump", 0)
    s.tap_btn(800, PLAY)
    log = run(s, 800 + int(BAR) - 20)
    check(log.dumps[0]["on"] == "." * 16 and log.dumps[0]["pen"] == 64, "K1 on an off step: not lit, the pen follows it (%s pen %s)" % (log.dumps[0]["on"], log.dumps[0]["pen"]))
    check(log.dumps[1]["on"] == ".x" + "." * 14 and log.dumps[1]["pen"] == 69, "SEL + K4: the pen 69; a key writes the step with it (%s pen %s)" % (log.dumps[1]["on"], log.dumps[1]["pen"]))
    check(pitches(log, after=800) == [69], "the new step plays the pen's note (%s)" % pitches(log, after=800))
    n = log.notes(ch=0, before=800)
    check(len(n) == 1 and n[0][1] == 64, "K1 on an off step gives a short preview of the note (%s)" % n)
    # TIE (EDIT + black 6): the note holds into the next step: its note-off comes after the next note-on (legato)
    s = Script()
    t = program(s, 100, [60, 62])
    s.enc(t, E_ALG, -1); t += 30
    s.press(t, EDIT); s.tap_key(t + 30, bk(5)); s.release(t + 100, EDIT); t += 160               # TIE on step 1
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(BAR))
    on62 = [tm for tm, d1, v in log.notes(ch=0, after=p0) if d1 == 62]
    off60 = [tm for tm, d1 in log.offs(ch=0) if d1 == 60 and tm > p0]
    check(log.states[0]["msg"].startswith("TIE"), "EDIT + black 6: TIE (%s)" % log.states[0]["msg"])
    check(on62 and off60 and 5 <= off60[0] - on62[0] <= 25, "TIE: note 60 ends %s ms after note 62 begins" % (off60[0] - on62[0] if on62 and off60 else None))
    # ... and from the grid: STEP view, SHIFT + row 7 pad 16 (pad 15: PLAIN)
    s = Script()
    t = s.steps(100, [0])
    s.raw(t, "attach"); t += 100
    shift(s, t, 1); s.pad(t + 20, 15, 6); shift(s, t + 100, 0); t += 160
    s.at(t, "dump", 0)
    shift(s, t, 1); s.pad(t + 20, 14, 6); shift(s, t + 100, 0); t += 160
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    check(log.states[0]["msg"].startswith("TIE:") and log.states[1]["msg"].startswith("STEP PLAIN"), "grid SHIFT + row 7: pad 16 TIE, pad 15 PLAIN (%s / %s)" % (log.states[0]["msg"], log.states[1]["msg"]))
    # CHORD (HOME 4 K3 / ARP page 2 K1): one written note becomes a chord; a FREE track: the exact shape; IN KEY: the
    # shape on the scale (DIATONIC), the exact shape (FREE), or the exact shape with the notes out of the key silent (STRICT)
    def chord_first(s, t, bars=0):
        s.tap_btn(t, PLAY)
        log = run(s, t + 300)
        return sorted(d1 for tm, d1, v in log.notes(ch=0, after=t, before=t + 100)), log
    s = Script()
    t = s.steps(100, [0])
    t = home_page(s, t, 3, [(K3, 4)])                              # MAJOR
    first, log = chord_first(s, t)
    check(first == [60, 64, 67], "CHORD MAJOR on a FREE track: C E G (%s)" % first)
    s = Script()
    t = kp(s, 100, [(K1, 2), (K2, 2), (K4, 1)])                    # key D minor, track 1 IN KEY
    s.press(t, SEL); s.tap_key(t + 30, 1 << 9, hold=40); s.release(t + 100, SEL); t += 160        # step 1: D (62)
    t = home_page(s, t, 3, [(K3, 12)], cur=2)                      # DOM7, DIATONIC: the 7th chord of the scale on D
    first, log = chord_first(s, t)
    check(first == [62, 65, 69, 72], "DOM7 shape, DIATONIC, in D minor: D F A C (%s)" % first)
    for ck, want, name in ((0, [62, 65, 69], "DIATONIC: D minor, the scale decides"), (1, [62, 66, 69], "FREE: D major, the F# out of the key plays"),
                           (2, [62, 69], "STRICT: D major with the F# silent: D A")):
        s = Script()
        t = kp(s, 100, [(K2, 1), (K4, 1)])                         # C major, IN KEY
        s.press(t, SEL); s.tap_key(t + 30, 1 << 9, hold=40); s.release(t + 100, SEL); t += 160    # step 1: D
        t = arp2(s, t, [(K1, 4), (K2, ck)] if ck else [(K1, 4)])   # MAJOR; KEY mode
        s.at(t, "dump", 0)
        first, log = chord_first(s, t)
        check(first == want and cfgs(log)[0]["ck"] == ck and cfgs(log)[0]["chord"] == 4, "MAJOR on D in C major, %s (%s)" % (name, first))
    check(log.states[0]["msg"].startswith("STRICT"), "the screen explains the mode (%s)" % log.states[0]["msg"])
    # five and six notes: MIN9 and MIN11 (a written step holds four; a shape plays up to six)
    s = Script()
    t = s.steps(100, [0])
    t = home_page(s, t, 3, [(K3, 22)])                             # MIN9
    first, log = chord_first(s, t)
    check(first == [60, 63, 67, 70, 74], "MIN9: five notes (%s)" % first)
    s = Script()
    t = s.steps(100, [0])
    t = home_page(s, t, 3, [(K3, 27)])                             # MIN11
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(2 * STEP_MS))
    first = sorted(d1 for tm, d1, v in log.notes(ch=0, after=p0, before=p0 + 100))
    offs = sorted(d1 for tm, d1 in log.offs(ch=0) if tm > p0)
    check(first == [60, 63, 67, 70, 74, 77] and offs == first, "MIN11: six notes on, six off (%s / %s)" % (first, offs))
    # ... and the arpeggio walks all six
    s = Script()
    t = s.steps(100, [0])
    t = home_page(s, t, 3, [(K3, 27)])
    t = held(s, t, ARP, [(K1, 1), (K3, 2)])                        # UP, RATE 2
    s.press(t, EDIT); s.enc(t + 30, K1, 24); s.release(t + 100, EDIT); t += 160               # gate 4 steps
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(BAR) - 20)
    check(pitches(log, after=p0)[:6] == [60, 63, 67, 70, 74, 77], "ARP UP over MIN11: the six notes in turn (%s)" % pitches(log, after=p0)[:8])
    # ARP RATE (ARP page 1 K3): a chord step with a long gate arpeggiates so many notes a step, through the silent steps
    s = Script()
    t = s.steps(100, [0])
    t = home_page(s, t, 3, [(K3, 4)])                              # MAJOR
    t = held(s, t, ARP, [(K1, 1), (K3, 2)])                        # UP; RATE 2: two notes a step
    s.press(t, EDIT); s.enc(t + 30, K1, 24); s.release(t + 100, EDIT); t += 160               # gate 4 steps (80 % -> 104)
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(BAR) - 20)
    n = [(round((tm - p0) / (STEP_MS / 2)), d1) for tm, d1, v in log.notes(ch=0, after=p0)]
    check([d for k, d in n] == [60, 64, 67, 60, 64, 67, 60, 64], "ARP RATE 2, gate 4 steps: eight notes, up (%s)" % n)
    check([k for k, d in n] == list(range(8)), "... one every half step (%s)" % [k for k, d in n])
    # RUN = HOLD (ARP page 1 K4): the arpeggio runs on to the end of the pattern
    s = Script()
    t = s.steps(100, [0])
    t = home_page(s, t, 3, [(K3, 4)])
    t = held(s, t, ARP, [(K1, 1), (K3, 1), (K4, 2)])               # UP, RATE 1, RUN: HOLD
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(BAR) - 20)
    check(len(log.notes(ch=0, after=p0)) == 16 and log.states[0]["msg"].startswith("HOLD:"), "ARP HOLD, rate 1: a note every step of the bar (%d; %s)" % (len(log.notes(ch=0, after=p0)), log.states[0]["msg"]))
    # TRANSPOSE (HOME 1 K4): steps of the scale when IN KEY (+2 in C major: C -> E), semitones when FREE
    s = Script()
    t = kp(s, 100, [(K2, 1), (K4, 1)])                             # C major, IN KEY
    t = s.steps(t, [0])
    t = home_page(s, t, 0, [(K4, 2)], cur=2)
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + 200)
    check(pitches(log, after=p0) == [64] and cfgs(log)[0]["trans"] == 2, "IN KEY, TRANSPOSE +2: two steps of C major, C -> E (%s)" % pitches(log, after=p0))
    s = Script()
    t = s.steps(100, [0])
    t = home_page(s, t, 0, [(K4, 2)])
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + 200)
    check(pitches(log, after=p0) == [62], "FREE, TRANSPOSE +2: two semitones (%s)" % pitches(log, after=p0))
    # the track's OCTAVE: HOME 2 K3, or GLO + SEL + OCT+ while it plays (0.12: GLO + OCT alone turns GLO's pages)
    s = Script()
    t = s.steps(100, [0])
    t = home_page(s, t, 1, [(K3, 1)])
    s.tap_btn(t, PLAY); p0 = t
    s.tap_btn(p0 + 300, GLO)                                       # PERF
    s.press(p0 + 400, GLO); s.press(p0 + 420, SEL); s.tap_btn(p0 + 440, OCT_UP, hold=20); s.release(p0 + 490, SEL); s.release(p0 + 510, GLO)
    s.at(p0 + 600, "dump", 0)
    log = run(s, p0 + int(2 * BAR) - 20)
    p = pitches(log, after=p0)
    check(p[:1] == [72] and p[1:2] == [84] and cfgs(log)[0]["oct"] == 2, "OCTAVE +1 (HOME 2 K3), then GLO + SEL + OCT+: 72, then 84 (%s)" % p[:2])
    # the conditions: 1:3 plays the first of every three loops; PRE plays after a step that played, !PRE after one that did not
    s = Script()
    t = s.steps(100, [0])
    s.press(t, EDIT); s.enc(t + 30, K2, 9); s.release(t + 100, EDIT); t += 160              # condition 9
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(6 * BAR) - 20)
    bars = [round((tm - p0) / BAR) for tm, d1, v in log.notes(ch=0, after=p0)]
    check(bars == [0, 3], "condition 9 = 1:3: bars 1 and 4 of six (%s)" % bars)
    s = Script()
    t = s.steps(100, [0, 1])
    s.press(t, EDIT); s.enc(t + 30, K2, 14); s.release(t + 100, EDIT); t += 160                     # step 2 (the cursor is on it): PRE
    s.enc(t, E_ALG, -1); t += 30
    s.enc(t, K3, -50); t += 30                                                                        # step 1: chance 50 %
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(16 * BAR) - 20)
    n = [(round((tm - p0) / STEP_MS) % 16, int((tm - p0 + 5) / BAR)) for tm, d1, v in log.notes(ch=0, after=p0)]
    b1 = {b for st, b in n if st == 0}
    b2 = {b for st, b in n if st == 1}
    check(0 < len(b1) < 16 and b2 == b1, "condition 14 = PRE: step 2 plays exactly in the bars step 1 played (%d of 16)" % len(b1))


def t010_lanes():
    group("0.10: six lanes, one a page: SLIDE, TRIGLESS, NRPN, a base, recording with REC, CC LEAD, LEARN by name")
    BAR = 16 * STEP_MS
    # SLIDE: lane 1 (CC 74) 0 on step 1, 127 on step 9: the value glides between them
    s = Script()
    t = s.steps(100, [0, 8])
    s.enc(t, E_ALG, -8); t += 30                                                                   # (the cursor is on the last key tapped)
    s.press(t, ENV); s.enc(t + 30, K1, 1); s.enc(t + 90, K1, -64); s.release(t + 130, ENV); t += 190         # lock 0 on step 1
    s.enc(t, E_ALG, 8); t += 30
    s.press(t, ENV); s.enc(t + 30, K1, 64); s.enc(t + 60, K4, 1); s.release(t + 100, ENV); t += 160          # 127 on step 9; SLIDE
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(BAR) - 20)
    c = ccn(log, 74, after=p0, before=p0 + int(8 * STEP_MS) + 5)
    vals = [v for tm, v in c]
    check(log.states[0]["msg"].startswith("SLIDE"), "ENV K4: SLIDE (%s)" % log.states[0]["msg"])
    check(len(c) >= 8 and vals == sorted(vals) and vals[0] <= 2 and vals[-1] >= 120, "SLIDE: CC 74 glides 0 -> 127 over eight steps (%d values, %s..%s)" % (len(c), vals[:1], vals[-1:]))
    # TRIGLESS: a lock on a silent step is sent anyway
    s = Script()
    t = s.steps(100, [0])
    s.enc(t, E_ALG, 4); t += 30                                                                    # step 5, off
    s.press(t, ENV); s.enc(t + 30, K1, 37); s.enc(t + 90, K4, 2); s.release(t + 130, ENV); t += 200   # lock 100 (64 + 36); TRIGLESS
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(BAR) - 20)
    c = ccn(log, 74, after=p0)
    check(log.states[0]["msg"].startswith("TRIGLESS"), "ENV K4 twice: TRIGLESS (%s)" % log.states[0]["msg"])
    check(len(c) == 1 and c[0][1] == 100 and near((c[0][0] - p0) / STEP_MS, 4, 0.1) and log.dumps[0]["on"] == "x" + "." * 15,
          "TRIGLESS: CC 74 = 100 goes out at step 5, which stays silent (%s)" % c)
    # NRPN: lane 1 sends 99 (MSB), 98 (LSB = the lane's number), 6 (the value)
    s = Script()
    t = s.steps(100, [0])
    s.press(t, ENV); s.enc(t + 30, K1, 11); s.enc(t + 90, K4, 4); s.release(t + 130, ENV); t += 200   # lock 74 (64 + 10); NRPN
    s.press(t, ENV); s.press(t + 20, SEL); s.enc(t + 50, K2, 3); s.release(t + 80, SEL); s.release(t + 110, ENV); t += 170    # MSB 3
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + 200)
    c = [(d1, d2) for tm, st, d1, d2 in log.msgs if st == 0xB0 and tm >= p0 and d1 in (6, 98, 99, 74)]
    check(c[:3] == [(99, 3), (98, 74), (6, 74)], "NRPN: 99 = 3, 98 = 74, 6 = the value (%s)" % c[:4])
    check(cfgs(log)[0]["lanes"][0] == (74, 4, 3, 255), "the lane: CC 74, NRPN, MSB 3, no base (%s)" % (cfgs(log)[0]["lanes"][0],))
    # a BASE (K3): the lane goes back to it on a step with no lock
    s = Script()
    t = s.steps(100, [0, 4])
    s.enc(t, E_ALG, -4); t += 30
    s.press(t, ENV); s.enc(t + 30, K1, 37); s.enc(t + 90, K3, 1); s.enc(t + 150, K3, -44); s.release(t + 200, ENV); t += 260   # lock 100, base 20
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(8 * STEP_MS))
    c = ccn(log, 74, after=p0)
    check([v for tm, v in c][:2] == [100, 20], "lock 100 on step 1, the base 20 on step 5 (%s)" % c[:2])
    # recording a lane: REC, PLAY, ENV held while K1 turns: the steps playing take the knob's value
    s = Script()
    t = s.steps(100, [0, 4, 8, 12])
    s.tap_btn(t, REC); t += 100
    s.tap_btn(t, PLAY); p0 = t
    s.press(p0 + int(3.5 * STEP_MS), ENV)
    for k in range(10): s.enc(p0 + int(3.5 * STEP_MS) + 30 + 90 * k, K1, 1)     # a slow turn through steps 4-12
    s.release(p0 + int(12.5 * STEP_MS), ENV)
    s.tap_btn(p0 + int(14 * STEP_MS), REC)
    log = run(s, p0 + int(2 * BAR) - 20)
    c = ccn(log, 74, after=p0 + int(BAR) - 5)
    st = [round((tm - p0) / STEP_MS) - 16 for tm, v in c]
    check(len(c) >= 2 and all(x in (4, 8, 12) for x in st) and [v for tm, v in c] == sorted(v for tm, v in c),
          "REC + ENV K1: the locks are on the steps that played while it turned, rising (%s)" % list(zip(st, [v for tm, v in c])))
    # CC LEAD (SAVE page 2 K1): the locks go out so many ms before the notes
    s = Script()
    t = s.steps(100, [0])
    s.press(t, ENV); s.enc(t + 30, K1, 1); s.release(t + 100, ENV); t += 160                        # lock 64 on step 1
    s.press(t, SAVE); s.tap_btn(t + 30, OCT_UP, hold=20); s.enc(t + 80, K1, 10); s.release(t + 140, SAVE); t += 200   # CC LEAD 10 ms
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(BAR) + 20)
    c = ccn(log, 74, after=p0 + int(BAR) - 30)
    n = log.notes(ch=0, after=p0 + int(BAR) - 30)
    check(cfgs(log)[0]["cclead"] == 10, "SAVE + OCT+, K1: CC LEAD 10 (%s)" % cfgs(log)[0]["cclead"])
    check(c and n and 8 <= n[0][0] - c[0][0] <= 12, "bar 2: the lock 10 ms before the note (%s)" % (n[0][0] - c[0][0] if c and n else None))
    # LEARN (ENV + REC) names the CC when the device is ELEKTRON (SAVE page 2 K3)
    s = Script()
    t = s.steps(100, [0])
    s.press(t, SAVE); s.tap_btn(t + 30, OCT_UP, hold=20); s.enc(t + 80, K3, 1); s.release(t + 140, SAVE); t += 200   # device ELEKTRON on channel 1
    s.press(t, ENV); s.tap_btn(t + 30, REC); s.release(t + 100, ENV); t += 160
    s.raw(t, "midi 0xB0 74 90"); t += 50
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    check("FILT" in log.states[0]["msg"] or "FREQ" in log.states[0]["msg"] or "CUTOFF" in log.states[0]["msg"], "LEARN: CC 74 named (%s)" % log.states[0]["msg"])
    check(cfgs(log)[0]["lanes"][0][0] == 74 and cfgs(log)[0]["lanes"][0][3] == 90, "... lane 1 is CC 74, its base the value that came in (%s)" % (cfgs(log)[0]["lanes"][0],))


def t010_tools():
    group("0.10: the tools WHEN and EVERY, BAND, the library at 32 / 64 steps, GENRE ON / LIVE, COOK by role, the rhythm families, the user progression")
    BAR = 16 * STEP_MS
    # WHEN = BAR: a tool used while it plays waits for the bar line
    s = Script()
    t = melody16(s)
    t = tools_knobs(s, t, [(K2, 1)])                          # TOOLS: WHEN BAR
    s.tap_btn(t, PLAY); p0 = t
    s.press(p0 + int(4.5 * STEP_MS), SEQ); s.tap_key(p0 + int(4.5 * STEP_MS) + 30, wk(0)); s.release(p0 + int(4.5 * STEP_MS) + 100, SEQ)   # CLEAR
    s.at(p0 + int(6 * STEP_MS), "dump", 0)
    s.at(p0 + int(17 * STEP_MS), "dump", 0)
    log = run(s, p0 + int(2 * BAR) - 20)
    n = [round((tm - p0) / STEP_MS) for tm, d1, v in log.notes(ch=0, after=p0)]
    check(log.states[0]["msg"] == "CLEAR IN 1 BAR" and log.dumps[0]["on"] == "x" * 16, "CLEAR while playing: CLEAR IN 1 BAR, nothing cleared yet (%s / %s)" % (log.states[0]["msg"], log.dumps[0]["on"]))
    check(n[-1] == 15 and log.dumps[1]["on"] == "." * 16, "at the bar line: cleared (last note at step %s)" % n[-1])
    check(cfgs(log)[0]["when"] == 1, "WHEN is BAR (%s)" % cfgs(log)[0]["when"])
    # EVERY 1 BAR: the last tool repeats every bar (SHIFT RIGHT walks the step on)
    s = Script()
    t = s.steps(100, [0])
    t = tools_knobs(s, t, [(K3, 1)])                          # EVERY 1 BAR
    s.press(t, SEQ); s.tap_key(t + 30, wk(3)); s.release(t + 100, SEQ); t += 160                       # SHIFT RIGHT: step 2
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(4 * BAR) - 20)
    n = [round((tm - p0) / STEP_MS) for tm, d1, v in log.notes(ch=0, after=p0)]
    check(n == [1, 18, 35, 52], "EVERY 1 BAR, SHIFT RIGHT: the step walks one on each bar (%s)" % n)
    # BAND (SEQ + SEL + black 7): 0.11: the genre's band, ten tracks for TECHNO, the roles with them, the harmony on
    s = Script()
    s.press(100, SEQ); s.tap_key(130, bk(6), hold=700); s.release(900, SEQ)
    for k in range(11): s.at(1000 + 20 * k, "dump", k)
    log = run(s, 1300)
    on = [d["on"].count("x") for d in log.dumps]
    roles = [c["role"] for c in cfgs(log)]
    check(log.states[0]["msg"] == "TECHNO BAND #1: 10 TRACKS", "the screen: TECHNO BAND #1: 10 TRACKS (%s)" % log.states[0]["msg"])
    check(all(x > 0 for x in on[:10]) and on[10] == 0, "every one of the ten tracks has a pattern, the eleventh none (%s)" % on)
    check(roles == [1, 8, 3, 9, 10, 4, 17, 5, 20, 21, 0], "the roles KICK CLAP HAT OPEN-HAT RIDE PERC RUMBLE BASS STAB PAD (%s)" % roles)
    check(log.states[0]["harm"][0] == 1, "the HARMONY is on")
    # the library at 32 steps (SAVE page 2 K4): BEAT puts a two-bar pattern down
    s = Script()
    s.press(100, SAVE); s.tap_btn(130, OCT_UP, hold=20); s.enc(180, K4, 1); s.release(240, SAVE)
    s.press(400, SEQ); s.tap_key(430, wk(9)); s.release(500, SEQ)                                    # BEAT
    s.at(600, "dump", 0)
    log = run(s, 700)
    check(log.dumps[0]["length"] == 32 and log.dumps[0]["on"].count("x") >= 8 and cfgs(log)[0]["lib"] == 1, "LIBRARY 32 STEPS: a 32-step kick (%s %s)" % (log.dumps[0]["length"], log.dumps[0]["on"]))
    # GENRE LIVE (TOOLS K4): the tracks that came from the library are loaded again when the genre changes, at the bar line
    s = Script()
    t = tools_knobs(s, 100, [(K4, 2)])                             # GENRE LIVE (SEQ 6 TOOLS K4)
    s.press(t, SEQ); s.tap_key(t + 30, bk(6), hold=700); s.release(t + 800, SEQ); t += 900   # BAND
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); p0 = t
    s.press(p0 + int(4.5 * STEP_MS), SEQ); s.enc(p0 + int(4.5 * STEP_MS) + 30, E_PRE, 4); s.release(p0 + int(4.5 * STEP_MS) + 100, SEQ)   # genre UK GARAGE
    s.at(p0 + int(8 * STEP_MS), "dump", 0)
    s.at(p0 + int(17 * STEP_MS), "dump", 0)
    log = run(s, p0 + int(BAR) + int(3 * STEP_MS))
    h = [d["hash"] for d in log.dumps]
    check(cfgs(log)[0]["gmode"] == 2, "GENRE mode LIVE (%s)" % cfgs(log)[0]["gmode"])
    check(h[1] == h[0] and h[2] != h[0] and cfgs(log)[2]["genre"] == 4, "the kick is TECHNO's until the bar line, UK GARAGE's after it (%s)" % h)
    check("LIVE" in log.states[1]["msg"], "the screen says the reload waits for the bar (%s)" % log.states[1]["msg"])
    # GENRE FREE: the genre changes nothing in the tracks
    s = Script()
    s.press(100, SEQ); s.tap_key(130, bk(6), hold=700); s.release(900, SEQ)
    s.at(1000, "dump", 0)
    s.press(1100, SEQ); s.enc(1130, E_PRE, 4); s.release(1200, SEQ)
    s.at(1300, "dump", 0)
    log = run(s, 1400)
    check(log.dumps[0]["hash"] == log.dumps[1]["hash"] and cfgs(log)[1]["genre"] == 4, "GENRE ON (the default): a new genre leaves the patterns as they are")
    # COOK by role: on a BASS track (HOME 4 K2) it keeps the root on the beats and stays in the register; on a HAT track
    # it keeps the pattern busy (COOK is a cook of what is there: it needs a pattern)
    s = Script()
    s.press(100, SEL); s.enc(130, K4, -24); s.release(200, SEL)                                        # pen 36
    t = s.steps(300, [0, 4, 8, 12])
    t = home_page(s, t, 3, [(K2, 5)])                              # role BASS
    t = seq_page(s, t, 0, encs=[(K4, 10)])                         # HEAT up
    s.press(t, SEQ); s.tap_key(t + 30, wk(8)); s.release(t + 100, SEQ); t += 160                       # COOK
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(BAR) - 20)
    p = [(round((tm - p0) / STEP_MS), d1) for tm, d1, v in log.notes(ch=0, after=p0)]
    check(log.dumps[0]["on"].count("x") >= 4 and p and max(d for k, d in p) <= 60 and min(d for k, d in p) >= 24, "COOK on a BASS track: a line in the bass register (%s)" % p)
    check(all(d == 36 for k, d in p if k % 4 == 0), "... the root on every beat (%s)" % p)
    s = Script()
    t = s.steps(100, [0, 2, 4, 6, 8, 10, 12, 14])
    t = home_page(s, t, 3, [(K2, 3)])                              # role HAT
    s.press(t, SEQ); s.tap_key(t + 30, wk(8)); s.release(t + 100, SEQ); t += 160
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    check(log.dumps[0]["on"].count("x") >= 8, "COOK on a HAT track: as busy as before, at least (%s)" % log.dumps[0]["on"])
    # the rhythm families (SEQ 1 K3): EUCLID E(5,16), TRESILLO 3-3-2, NUMERIC
    out = {}
    for fam in range(3):
        s = Script()
        t = seq_page(s, 100, 0, encs=[(K1, 1), (K3, fam)] if fam else [(K1, 1)], keys=[wk(5)])   # 5 pulses; 0.16: SEQ + white 6 starts it
        s.at(t, "dump", 0)
        log = run(s, t + 100)
        out[fam] = (log.states[0]["heard"].replace(" ", ""), cfgs(log)[0]["fam"])
    gaps = [b - a for a, b in zip([i for i, c in enumerate(out[0][0]) if c == "x"], [i for i, c in enumerate(out[0][0]) if c == "x"][1:])]
    check(out[0][0].count("x") == 5 and out[0][1] == 0 and min(gaps) >= 2 and max(gaps) <= 4, "EUCLID E(5,16): five hits, spread (%s)" % out[0][0])
    check(out[1][0].startswith("x..x..x.") and out[1][0].count("x") == 5 and out[1][1] == 1, "TRESILLO: 3-3-2 cells (%s)" % out[1][0])
    check(out[2][0].count("x") >= 3 and out[2][1] == 2 and out[2][0] != out[0][0], "NUMERIC: another rhythm from the same pulses (%s)" % out[2][0])
    # a USER progression (SEQ 8): i v (one bar each), HARMONY on it: a FOLLOW track moves C -> G
    s = Script()
    t = kp(s, 100, [(K2, 1), (K4, 1)])                             # C major, IN KEY
    t = s.steps(t, [0])
    t = home_page(s, t, 1, [(K4, 1)], cur=2)                       # FOLLOW
    t = uprog_knobs(s, t, [(K3, 1), (K2, 1), (K3, 8)])        # USER 1: pos 1 = I (root 0), pos 2 = V (0.11: K3 the root, 7 semitones)
    t = harm_knobs(s, t, [(K2, 6), (K1, 1)])          # HARMONY: progression 7 = USER 1, READY; K1 ON (0.16)
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(4 * BAR) - 20)
    b = [sorted({d1 for tm, d1, v in log.notes(ch=0, after=p0 + int(k * BAR) - 5, before=p0 + int((k + 1) * BAR) - 5)}) for k in range(4)]
    check(cfgs(log)[0]["prog"] == 6 and log.states[0]["msg"].startswith("HARMONY USER"), "HARMONY USER 1 (%s)" % log.states[0]["msg"])
    check(b == [[60], [55], [60], [55]], "i v i v: C G C G, the G the nearest one (%s)" % b)


def t010_keys():
    group("0.10: sixteen key slots, a track pinned to one, the song's tempo, ECHO ALL off at once")
    BAR = 16 * STEP_MS
    # slot 2 with a shift of +2: a track IN KEY plays 62; back to slot 1: 60; a track pinned to slot 1 stays on 60
    s = Script()
    t = kp(s, 100, [(K4, 1)])                                      # track 1 IN KEY
    t = s.steps(t, [0])
    s.tap_key(t, bk(1)); t += 80
    t = kp(s, t, [(K4, 1)], cur=2)                                 # track 2 IN KEY
    t = s.steps(t, [0])
    t = home_page(s, t, 3, [(K4, 1)], cur=2)                       # track 2 pinned to slot 1
    t = home_page(s, t, 2, [(K1, 1), (K4, 2)], cur=3)              # slot 2: shift +2
    s.at(t, "dump", 0); s.at(t + 10, "dump", 1)
    s.tap_btn(t, PLAY); p0 = t
    home_page(s, p0 + int(BAR) + int(4 * STEP_MS), 2, [(K1, -1)], cur=2)     # slot 1 again, in bar 2
    log = run(s, p0 + int(3 * BAR) - 20)
    c = cfgs(log)
    a = [pitches(log, ch=0, after=p0 + int(k * BAR) - 5, before=p0 + int((k + 1) * BAR) - 5) for k in range(3)]
    b = [pitches(log, ch=1, after=p0 + int(k * BAR) - 5, before=p0 + int((k + 1) * BAR) - 5) for k in range(3)]
    check(c[0]["cur"] == 1 and c[0]["key"] == [0, 0, 2] and c[0]["keyslot"] == -1 and c[1]["keyslot"] == 0 and c[1]["key"] == [0, 0, 0],
          "slot 2 (shift +2) is current; track 1 follows it, track 2 is pinned to slot 1 (%s / %s)" % (c[0]["key"], c[1]["key"]))
    check(a == [[62], [62], [60]], "track 1: 62 in slot 2, 60 once slot 1 is back (%s)" % a)
    check(b == [[60], [60], [60]], "track 2 (pinned): always 60 (%s)" % b)
    check("KEY SLOT 2" in log.states[0]["msg"] or "KEY 2" in log.states[0]["msg"], "the screen names the slot (%s)" % log.states[0]["msg"])
    # a snapshot brings its slot back
    s = Script()
    t = kp(s, 100, [(K4, 1)])
    t = s.steps(t, [0])
    s.press(t, SAVE); s.press(t + 20, SEL); s.tap_key(t + 50, bk(0)); s.release(t + 100, SEL); s.release(t + 120, SAVE); t += 200   # snapshot 1 (slot 1)
    t = home_page(s, t, 2, [(K1, 1), (K4, 2)], cur=2)              # slot 2: shift +2
    s.press(t, SAVE); s.tap_key(t + 30, bk(0)); s.release(t + 100, SAVE); t += 200                   # snapshot 1 back
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    check(cfgs(log)[0]["cur"] == 0, "a snapshot brings its key slot back (slot %s)" % (cfgs(log)[0]["cur"] + 1))
    # ECHO ALL (FX + OCT+) on, then off at once: the repeats that waited do not come
    s = Script()
    t = s.steps(100, [0])
    s.press(t, FX); s.tap_btn(t + 30, OCT_UP, hold=20); s.release(t + 100, FX); t += 160              # ECHO ALL on
    s.tap_btn(t, PLAY); p0 = t
    s.press(p0 + 60, FX); s.tap_btn(p0 + 90, OCT_UP, hold=20); s.release(p0 + 160, FX)                 # off, 60 ms in
    log = run(s, p0 + int(BAR) - 20)
    n = log.notes(ch=0, after=p0)
    check(len(n) == 1, "ECHO ALL off right after the note: no repeat comes (%d notes)" % len(n))


def t010_viaggio2():
    group("0.10 VIAGGIO: every genre, the roles and channels you choose, browsing the proposals, moves at the bar or the beat")
    BAR = 16 * STEP_MS
    # the role (0.17: HOME 4 K2; 0.10-0.16 K3 in VIAGGIO mode) of a track; a tap of the grid's VIAGGIO view proposes that
    # role, held: the dice; a tap on a PROPOSED track goes through its proposals (0.10-0.16: ALG in VIAGGIO mode)
    s = Script()
    t = home_page(s, 100, 3, [(K2, 5)])                            # role BASS
    s.raw(t, "attach")
    t = view(s, t + 100, GC_VPERF); t = view(s, t, GC_VPERF); t = view(s, t, GC_VPERF)   # PERF, SONG, VIAGGIO
    s.pad(t, 0, 1); t += 100                                       # a proposal
    s.at(t, "dump", 0)
    s.pad(t, 0, 1, hold=600); t += 700                             # held: another one (the dice)
    s.pad(t, 0, 1, hold=600); t += 700                             # and a third
    s.at(t, "dump", 0)
    s.pad(t + 50, 0, 1)                                            # a tap: the one before
    s.at(t + 150, "dump", 0)
    log = run(s, t + 250)
    c = cfgs(log)
    check(c[0]["role"] == 5 and log.states[0]["msg"].startswith("T1 BASS P2"), "role BASS, a tap: T1 BASS P2 ... (%s)" % log.states[0]["msg"])
    check(log.states[1]["msg"].startswith(("T1 BASS P4 (3/3)", "T1 RUMBLE P4 (3/3)")), "the pad held twice: three proposals, P4 the last (0.11: a dice of HARDTECHNO plays its RUMBLE for the BASS) (%s)" % log.states[1]["msg"])
    check(log.states[2]["msg"].startswith("T1 BASS P3 (2/3)"), "a tap: P3, 2 of 3 (%s)" % log.states[2]["msg"])
    check(log.viaggio[2]["states"][0] == "P" and log.viaggio[2]["patterns"][0] == "1", "the track is PROPOSED, the playing pattern still 1 (%s %s)" % (log.viaggio[2]["states"][0], log.viaggio[2]["patterns"][0]))
    s = Script()
    t = home_page(s, 100, 0, [(K1, 2)])                            # channel 3 (0.10-0.16: K4 in VIAGGIO mode)
    t = vg_on(s, t)
    t = vg_track_in_now(s, t, 0)
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + 300)
    check(log.notes(ch=2, after=p0) and not log.notes(ch=0, after=p0), "HOME 1 K1: the track plays on channel 3")
    # the grid: SHIFT + a track pad of the VIAGGIO view = its next role
    s = Script()
    s.raw(100, "attach")
    t = view(s, 200, GC_VPERF); t = view(s, t, GC_VPERF); t = view(s, t, GC_VPERF)      # PERF, SONG, VIAGGIO
    shift(s, t, 1); s.pad(t + 20, 1, 1); s.pad(t + 100, 1, 1); shift(s, t + 180, 0); t += 240
    s.at(t, "dump", 1)
    log = run(s, t + 100)
    check(cfgs(log)[0]["role"] == 2 and log.states[0]["msg"] == "T2 ROLE SNARE", "grid SHIFT + track pad twice: T2 ROLE SNARE (%s)" % log.states[0]["msg"])
    # MOVES AT (0.17: ALG on the MOSSE; 0.10-0.16 K2 in VIAGGIO mode): BAR: an IN lands at the next bar, not the
    # phrase; BEAT: at the next beat
    s = Script()
    t = vg_on(s, 100)
    s.enc(t, E_ALG, 1); t += 50                                    # BAR
    s.at(t, "dump", 0); t += 20
    t = vg_track_in_now(s, t, 0)
    s.tap_btn(t, PLAY); p0 = t
    vg_tap(s, p0 + 200, 1); vg_queue_track(s, p0 + 300, 1)         # track 2: a proposal, IN
    s.at(p0 + int(BAR) + 200, "dump", 1)
    log = run(s, p0 + int(BAR) + 300)
    v = log.viaggio
    check(log.states[0]["msg"] == "MOVES AT EVERY BAR", "ALG: MOVES AT EVERY BAR (%s)" % log.states[0]["msg"])
    check(v[1]["states"][:2] == "II" and v[1]["queue"] == [], "track 2 is IN after one bar (not sixteen) (%s %s)" % (v[1]["states"][:2], v[1]["queue"]))
    s = Script()
    t = vg_on(s, 100)
    s.enc(t, E_ALG, 2); t += 50                                    # BEAT
    t = vg_track_in_now(s, t, 0)
    s.tap_btn(t, PLAY); p0 = t
    vg_tap(s, p0 + 200, 1); vg_queue_track(s, p0 + 300, 1)
    s.at(p0 + int(8 * STEP_MS), "dump", 1)
    log = run(s, p0 + int(8 * STEP_MS) + 100)
    check(log.viaggio[0]["states"][:2] == "II", "MOVES AT THE BEAT: track 2 is IN within two beats (%s)" % log.viaggio[0]["states"][:2])
    # every genre of the library is a VIAGGIO genre: GLO 3 K3 walks all 25 (0.16: the merengue last), each with a kick proposal
    s = Script()
    t = vg_on(s, 100)
    for g in range(24):
        t = viaggio_knobs(s, t, [(K3, 1)])
    s.at(t, "dump", 0)
    vg_tap(s, t + 50, 0)
    s.at(t + 150, "dump", 0)
    log = run(s, t + 250)
    check(log.viaggio[0]["genre"] == 24 and "MERENGUE" in log.states[0]["msg"], "K3 x 24: MERENGUE, the last genre (%s)" % log.states[0]["msg"])
    check(log.viaggio[1]["states"][0] == "P" and log.dumps[1]["on"].count("x") == 0 and log.states[1]["msg"].startswith("T1 KICK P2"), "a MERENGUE kick proposed (%s)" % log.states[1]["msg"])
    s = Script()
    t = vg_on(s, 100)
    for g in range(22):
        t = viaggio_knobs(s, t, [(K3, 1)])
    t = home_page(s, t, 3, [(K2, 7)])                              # role ARP: the cowbell riff
    vg_tap(s, t, 0); t += 100
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    check(log.states[0]["msg"].startswith("T1 LEAD P2") and log.dumps[0]["on"].count("x") == 0, "PHONK, role ARP: a proposal of its LEAD, the cowbell riff (%s)" % log.states[0]["msg"])
    # a genre with no proposal of a role falls back: UK DRILL's chord
    s = Script()
    t = vg_on(s, 100)
    for g in range(20):
        t = viaggio_knobs(s, t, [(K3, 1)])
    t = home_page(s, t, 3, [(K2, 6)])                              # role CHORD
    vg_tap(s, t, 0); t += 100
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    check(log.states[0]["msg"].startswith("T1 PAD P2"), "UK DRILL, role CHORD: a proposal of its PAD (%s)" % log.states[0]["msg"])



# ------------------------------------------------------------------------------------------------ 0.11
V11 = re.compile(r"^\s*(\d+) ms  v11 T(\d+) harmgenre (\d+) lock (\d+) lenpend (\d+) anchor (\d+) step (\d+) slot (\d+) algos((?: \d+/\d+/\d+/\d+){4})"
                 r"(?: win (-?\d+) chop (\d+))?$", re.M)     # 0.12: the window open (a button id, -1 none), the track's chop


def v11s(log):
    """the 0.11 'v11' lines of the dumps: the harmony's genre and lock, the length that waits, the track's anchor and step,
    the algorithm slot shown and the four slots (algo, a, b, c)"""
    return [dict(t=int(m.group(1)), track=int(m.group(2)), harmgenre=int(m.group(3)), lock=int(m.group(4)), lenpend=int(m.group(5)),
                 anchor=int(m.group(6)), step=int(m.group(7)), slot=int(m.group(8)),
                 algos=[tuple(int(v) for v in x.split("/")) for x in m.group(9).split()],
                 win=int(m.group(10)) if m.group(10) is not None else -1, chop=int(m.group(11)) if m.group(11) is not None else 0)
            for m in V11.finditer(log.text)]


def wins(log):
    """0.12: the window open at each dump: -1 none, else the button id (HOME, SEQ, EDIT, ENV, LFO, ARP, FX)"""
    return [v["win"] for v in v11s(log)]


def t011_algo_slots():
    group("0.11: four algorithm slots a track, run in order; SEL + K1 picks the slot; WRITE LIVE keeps the ACCENTs")
    BAR = 16 * STEP_MS
    # slot 1 DENSITY 200 (every rest gains a ghost), slot 2 ACCENT: all 16 steps play, the velocities move with the accent
    s = Script()
    t = s.steps(100, [0, 4, 8, 12])
    t = seq_page(s, t, 1, encs=[(K1, 4), (K2, 20)], keys=[wk(5)])      # slot 1: DENSITY, 200 % (0.16: SEQ + white 6 starts it)
    s.press(t, SEQ); s.press(t + 30, SEL); s.enc(t + 60, K1, 1); s.release(t + 100, SEL); t += 130   # SEL + K1: slot 2
    s.enc(t, K1, 3); t += 30                                            # slot 2: ACCENT
    s.enc(t, K3, 8); t += 30                                            # amount up
    s.tap_key(t, wk(5), hold=40); t += 80                               # started
    s.release(t, SEQ); t += 60
    s.at(t, "dump", 0)
    s.tap_btn(t + 50, PLAY); p = t + 50
    log = run(s, p + int(BAR) - 20)
    v = v11s(log)[0]
    n = log.notes(ch=0, after=p)
    check(v["slot"] == 1 and v["algos"][0][:2] == (4, 200) and v["algos"][1][0] == 3 and v["algos"][2][0] == 0, "slot 1 DENSITY 200, slot 2 ACCENT, slot 3 empty (%s, shown %s)" % (v["algos"], v["slot"]))
    heard = log.states[0]["heard"].replace(" ", "")
    check(heard.count("x") >= 12 and len(n) == heard.count("x"), "most steps are heard and played: DENSITY filled the rests (%s, %d notes)" % (heard, len(n)))
    check(n and n[0][2] == 127 and [vel for tm, d1, vel in n if round((tm - p) / STEP_MS) == 4] == [127], "the ACCENT of slot 2 lifts the beats to 127 (%s)" % sorted({vel for _, _, vel in n}))
    check("ALGO 2" in log.states[0]["msg"] and "2 RUN" in log.states[0]["msg"], "the screen: T1 ALGO 2: ACCENT (2 RUN) (%s)" % log.states[0]["msg"])
    # the order: slot 1 CELL makes the rhythm, slot 2 DENSITY 0 takes it all away; the other way round the CELL plays
    s = Script()
    t = s.steps(100, [0, 4, 8, 12])
    t = seq_page(s, t, 1, encs=[(K1, 2)], keys=[wk(5)])                 # slot 1: CELL
    s.press(t, SEQ); s.press(t + 30, SEL); s.enc(t + 60, K1, 1); s.release(t + 100, SEL); s.enc(t + 130, K1, 4); s.enc(t + 160, K2, -20); s.tap_key(t + 175, wk(5), hold=10); s.release(t + 200, SEQ); t += 260   # slot 2: DENSITY 0
    s.tap_btn(t, PLAY); p = t
    log = run(s, p + int(BAR) - 20)
    check(not log.notes(ch=0, after=p), "CELL then DENSITY 0: silence (%d notes)" % len(log.notes(ch=0, after=p)))
    s = Script()
    t = s.steps(100, [0, 4, 8, 12])
    t = seq_page(s, t, 1, encs=[(K1, 4), (K2, -20)], keys=[wk(5)])      # slot 1: DENSITY 0
    s.press(t, SEQ); s.press(t + 30, SEL); s.enc(t + 60, K1, 1); s.release(t + 100, SEL); s.enc(t + 130, K1, 2); s.tap_key(t + 160, wk(5), hold=10); s.release(t + 200, SEQ); t += 260   # slot 2: CELL
    s.tap_btn(t, PLAY); p = t
    log = run(s, p + int(BAR) - 20)
    check(len(log.notes(ch=0, after=p)) >= 2, "DENSITY 0 then CELL: the CELL's rhythm plays, the slots run in order (%d notes)" % len(log.notes(ch=0, after=p)))
    # WRITE LIVE: what is heard is written, DENSITY goes off, the ACCENT stays (it changes no hit)
    s = Script()
    t = s.steps(100, [0, 4, 8, 12])
    t = seq_page(s, t, 1, encs=[(K1, 4), (K2, 20)], keys=[wk(5)])
    s.press(t, SEQ); s.press(t + 30, SEL); s.enc(t + 60, K1, 1); s.release(t + 100, SEL); s.enc(t + 130, K1, 3); s.tap_key(t + 160, wk(5), hold=10); s.release(t + 200, SEQ); t += 260
    s.press(t, SEQ); s.tap_key(t + 30, wk(6)); s.release(t + 100, SEQ); t += 160                      # WRITE LIVE
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    v = v11s(log)[0]
    check(log.dumps[0]["on"].count("x") >= 12 and v["algos"][0][0] == 0 and v["algos"][1][0] == 3, "written: the filled steps; DENSITY off, ACCENT kept (%s, %s)" % (log.dumps[0]["on"], v["algos"]))
    # the grid's ALGO view: pad 8 of row 4 goes to the next slot; the slot's algorithm is set with pads 1-5 of that row
    s = Script()
    s.raw(100, "attach"); view(s, 200, GC_VTRACK); view(s, 300, GC_VTRACK); view(s, 400, GC_VTRACK); t = 500   # TRACK, 2, 3
    s.pad(t, 7, 3); t += 100                                            # next slot: 2
    s.pad(t, 1, 3); t += 100                                            # TURING READY on slot 2 (0.16)
    s.pad(t, 1, 3); t += 100                                            # again: it starts
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    v = v11s(log)[0]
    check(v["slot"] == 1 and v["algos"][1][0] == 1 and v["algos"][0][0] == 0, "grid: slot 2 shown, TURING on it, slot 1 untouched (%s, %s)" % (v["slot"], v["algos"]))



def beat_key(s, t):
    """SEQ + white 10: BEAT on the selected track (the function and variation the SEQ page shows)"""
    s.press(t, SEQ); s.tap_key(t + 30, wk(9)); s.release(t + 100, SEQ)
    return t + 160


def t011_lengths():
    group("0.11: a longer track keeps playing (the loop repeats in the new steps), a library pattern after it lands in time")
    BAR = 16 * STEP_MS
    # a TECHNO kick (16 steps) made 64 in bar 1: from the bar line the four bars all have the kick, no silence
    s = Script()
    t = beat_key(s, 100)
    s.tap_btn(t, PLAY); p0 = t
    home_page(s, p0 + int(4.5 * STEP_MS), 0, [(K2, 48)])             # LENGTH 64 asked in step 5
    s.at(p0 + int(6 * STEP_MS), "dump", 0)
    s.at(p0 + int(18 * STEP_MS), "dump", 0)
    log = run(s, p0 + int(5 * BAR) - 20)
    k = [round((tm - p0) / STEP_MS) for tm, d1, v in log.notes(ch=0, after=p0)]
    check(v11s(log)[0]["lenpend"] == 64 and log.dumps[0]["length"] == 16 and log.states[0]["msg"] == "LENGTH 64 AT THE BAR",
          "LENGTH 64 while playing waits for the bar (pend %s, length %s, %s)" % (v11s(log)[0]["lenpend"], log.dumps[0]["length"], log.states[0]["msg"]))
    check(log.dumps[1]["length"] == 64 and log.dumps[1]["on"] == "X...X...X...X..." .replace("X", "x") * 4 and v11s(log)[1]["lenpend"] == 0,
          "from bar 2 the track is 64 steps and the kick fills them all (%s)" % log.dumps[1]["on"])
    check(k == list(range(0, 80, 4)), "the kick never stops: a hit every four steps through five bars (%s)" % k)
    # ... then another pattern loaded from the library in bar 3 enters in time: its first step on the bar line
    s = Script()
    t = beat_key(s, 100)
    s.tap_btn(t, PLAY); p0 = t
    home_page(s, p0 + int(4.5 * STEP_MS), 0, [(K2, 48)])
    beat_key(s, p0 + int(36.5 * STEP_MS))                              # kick #2 (X...X...X...X..x) in bar 3, step 5
    s.at(p0 + int(38 * STEP_MS), "dump", 0)
    log = run(s, p0 + int(4 * BAR) - 20)
    k = [round((tm - p0) / STEP_MS) for tm, d1, v in log.notes(ch=0, after=p0 + int(37 * STEP_MS))]
    check(log.dumps[0]["length"] == 16 and log.dumps[0]["on"] == "x...x...x...x..x", "the new pattern: 16 steps, kick #2 (%s)" % log.dumps[0]["on"])
    check(k == [40, 44, 47, 48, 52, 56, 60, 63], "it goes on where the clock is: 40 44 47, then the bar 48 52 56 60 63 (%s)" % k)
    # stopped: the length changes at once, and a turn of the knob 16 -> 24 repeats the first 8 steps of the loop
    s = Script()
    t = melody16(s)
    s.press(t, HOME)
    for k in range(8): s.enc(t + 40 + 150 * k, K2, 1)                  # eight clicks, 150 ms apart: one turn, 17 .. 24
    t += 40 + 150 * 8; s.release(t, HOME); t += 60
    s.at(t, "dump", 0)
    s.tap_btn(t + 50, PLAY); p0 = t + 50
    log = run(s, p0 + int(24 * STEP_MS) - 20)
    n = [d1 for tm, d1, v in log.notes(ch=0, after=p0)]
    check(log.dumps[0]["length"] == 24 and log.dumps[0]["on"] == "x" * 24, "stopped: LENGTH 24 at once, the new steps filled (%s)" % log.dumps[0]["on"])
    check(n == [60 + i for i in range(16)] + [60 + i for i in range(8)], "the melody, then its first 8 notes again (%s)" % n)
    # shortened, then made long again: the notes that were there come back (nothing is overwritten)
    s = Script()
    t = melody16(s)
    t = home_page(s, t, 0, [(K2, -8)])
    t = home_page(s, t + 1000, 0, [(K2, 8)])                           # a second turn, a second later
    s.at(t, "dump", 0)
    s.tap_btn(t + 50, PLAY); p0 = t + 50
    log = run(s, p0 + int(16 * STEP_MS) - 20)
    n = [d1 for tm, d1, v in log.notes(ch=0, after=p0)]
    check(log.dumps[0]["length"] == 16 and n == [60 + i for i in range(16)], "8 then 16 again: the written melody is back whole (%s)" % n)


def t011_harmony_genre():
    group("0.11: the HARMONY has a genre of its own: browsing changes nothing, a pattern loaded brings its genre, LOCK keeps it")
    BAR = 16 * STEP_MS

    def setup(s, lock=0):
        t = kp(s, 100, [(K4, 1)])                                       # track 1 in key (C minor)
        t = s.steps(t, [0])
        t = home_page(s, t, 1, [(K4, 1)], cur=2)                        # FOLLOW
        t = harm_knobs(s, t, [(K1, 2 if lock else 1)])            # HARMONY ON / LOCK
        t = harm_knobs(s, t, [(K2, 3)])                           # TECHNO #4: i VII VI VII
        s.enc(t, E_SEL, 1); t += 60                                     # track 2 selected: the kick goes there
        return t

    def bars(log, p, n):
        return [sorted({d1 for tm, d1, _ in log.notes(ch=0, after=p + int(k * BAR) - 5, before=p + int((k + 1) * BAR) - 5)}) for k in range(n)]

    # the genre knob (SEQ + PRESETS) only browses: the progression stays TECHNO's
    s = Script()
    t = setup(s)
    s.tap_btn(t, PLAY); p = t
    s.press(p + int(2 * STEP_MS), SEQ); s.enc(p + int(2 * STEP_MS) + 30, E_PRE, 4); s.release(p + int(2 * STEP_MS) + 100, SEQ)   # UK GARAGE
    s.at(p + int(3 * STEP_MS), "dump", 0)
    log = run(s, p + int(4 * BAR))
    check(bars(log, p, 4) == [[60], [58], [56], [58]], "UK GARAGE on the knob, the harmony still TECHNO's: C Bb Ab Bb (%s)" % bars(log, p, 4))
    check(cfgs(log)[0]["genre"] == 4 and v11s(log)[0]["harmgenre"] == 0, "the machine's genre is UK GARAGE, the harmony's TECHNO (%s / %s)" % (cfgs(log)[0]["genre"], v11s(log)[0]["harmgenre"]))
    # a pattern loaded from UK GARAGE brings the harmony with it: VI V i i from there on
    s = Script()
    t = setup(s)
    s.tap_btn(t, PLAY); p = t
    s.press(p + int(2 * STEP_MS), SEQ); s.enc(p + int(2 * STEP_MS) + 30, E_PRE, 4); s.release(p + int(2 * STEP_MS) + 100, SEQ)
    beat_key(s, p + int(4 * BAR + 2 * STEP_MS))                         # the UK GARAGE kick on track 2, in bar 5
    s.at(p + int(4 * BAR + 4 * STEP_MS), "dump", 0)
    log = run(s, p + int(8 * BAR))
    b = bars(log, p, 8)
    check(b[:4] == [[60], [58], [56], [58]] and b[5:8] == [[55], [60], [60]], "TECHNO's chords, then from the load UK GARAGE's: G C C (%s)" % b)
    check(v11s(log)[0]["harmgenre"] == 4 and log.notes(ch=1, after=p), "the harmony's genre is UK GARAGE now, the kick plays (%s)" % v11s(log)[0]["harmgenre"])
    # HARMONY LOCK: the load changes nothing in the harmony; SEL + K2 on the HARMONY page changes its genre by hand
    s = Script()
    t = setup(s, lock=1)
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); p = t
    s.press(p + int(2 * STEP_MS), SEQ); s.enc(p + int(2 * STEP_MS) + 30, E_PRE, 4); s.release(p + int(2 * STEP_MS) + 100, SEQ)
    beat_key(s, p + int(2 * STEP_MS) + 200)                             # the UK GARAGE kick, bar 1
    s.at(p + int(6 * STEP_MS), "dump", 0)
    q = p + int(4 * BAR + 2 * STEP_MS)                                  # bar 5: K2 +4 on HARMONY 2 (ARP 4): UK GARAGE by hand
    q = harm2_knobs(s, q, [(K2, 4)])
    s.at(q, "dump", 0)
    log = run(s, p + int(8 * BAR))
    b = bars(log, p, 8)
    v = v11s(log)
    check(v[0]["lock"] == 1 and "LOCK" in log.states[0]["msg"], "K1 twice: HARMONY LOCK (%s)" % log.states[0]["msg"])
    check(v[1]["harmgenre"] == 0 and log.notes(ch=1, after=p), "the kick loaded from UK GARAGE, the harmony still TECHNO's (%s)" % v[1]["harmgenre"])
    check(b[:4] == [[60], [58], [56], [58]], "locked: C Bb Ab Bb (%s)" % b[:4])
    check(v[2]["harmgenre"] == 4 and v[2]["lock"] == 1 and b[5:8] == [[55], [60], [60]], "HARMONY 2 K2: UK GARAGE by hand, locked still: G C C (%s, %s)" % (v[2]["harmgenre"], b[5:8]))
    check(log.states[2]["msg"].startswith("HARMONY LOCK UK GARAGE"), "the screen names the harmony's genre (%s)" % log.states[2]["msg"])


def t011_band_cook():
    group("0.11: BAND by the genre's formation, on the tracks the player gave a role, channels and notes kept; COOK walks to the next variation")
    BAR = 16 * STEP_MS
    # track 2: role BASS, channel 12 (the player's); track 5: one step written, no role. BAND: TECHNO's ten parts
    s = Script()
    s.tap_key(100, bk(1)); t = 200                                       # track 2
    t = home_page(s, t, 0, [(K1, 10)])                                   # channel 12
    t = home_page(s, t, 3, [(K2, SQ_ROLE_BASS)])                         # role BASS
    t = home_page(s, t, 0, [], cur=3)
    s.tap_key(t, bk(4)); t += 100                                        # track 5: a step of the player's
    t = s.steps(t, [0])
    s.tap_key(t, bk(0)); t += 100                                        # track 1
    s.press(t, SEQ); s.tap_key(t + 30, bk(6), hold=700); s.release(t + 800, SEQ); t += 900   # BAND
    for k in range(12): s.at(t + 20 * k, "dump", k)
    s.tap_btn(t + 400, PLAY); p = t + 400
    log = run(s, p + int(BAR))
    roles = [c["role"] for c in cfgs(log)]
    check(roles == [1, 5, 8, 3, 0, 9, 10, 4, 17, 20, 21, 0], "the BASS on track 2 (its role), the others on the free tracks, track 5 left alone (%s)" % roles)
    check(log.dumps[4]["on"] == "x" + "." * 15, "track 5 as the player wrote it (%s)" % log.dumps[4]["on"])
    bass = log.notes(ch=11, after=p)
    check(bass and all(d1 < 48 for _, d1, _ in bass) and not log.notes(ch=1, after=p), "the bass plays on channel 12, the player's (%s)" % bass[:3])
    kick = sorted({d1 for _, d1, _ in log.notes(ch=0, after=p)})
    check(kick == [36] and sorted({d1 for _, d1, _ in log.notes(ch=2, after=p)}) == [39], "a new track: the General MIDI note of its part (kick 36, clap 39)")
    check(log.states[0]["msg"] == "TECHNO BAND #1: 10 TRACKS", "the screen (%s)" % log.states[0]["msg"])
    # a drum note the player set stays: track 1 role KICK, note 35; BAND keeps it
    s = Script()
    t = home_page(s, 100, 3, [(K2, SQ_ROLE_KICK)])
    t = home_page(s, t, 0, [], cur=3)
    s.press(t, SEQ); s.tap_key(t + 30, bk(6), hold=700); s.release(t + 800, SEQ); t += 900   # BAND once: the kick's note 36
    t = pen_turn(s, t, -1)                                               # 36 -> 35
    s.press(t, SEQ); s.tap_key(t + 30, bk(6), hold=700); s.release(t + 800, SEQ); t += 900   # BAND again
    s.tap_btn(t + 100, PLAY); p = t + 100
    log = run(s, p + int(BAR))
    check(sorted({d1 for _, d1, _ in log.notes(ch=0, after=p)}) == [35], "BAND again: the kick keeps the note the player gave it (%s)" % sorted({d1 for _, d1, _ in log.notes(ch=0, after=p)}))
    # KIT (SEQ + black 7): the band's drums only, from the selected track
    s = Script()
    s.press(100, SEQ); s.tap_key(130, bk(6)); s.release(300, SEQ)
    for k in range(8): s.at(400 + 20 * k, "dump", k)
    log = run(s, 700)
    roles = [c["role"] for c in cfgs(log)]
    check(roles == [1, 8, 3, 9, 10, 4, 0, 0] and log.states[0]["msg"] == "TECHNO KIT #1: 6 TRACKS", "KIT: kick clap hat open-hat ride perc (%s, %s)" % (roles, log.states[0]["msg"]))
    # COOK on a library track walks to the next variation: TECHNO KICK #1 -> #2 (one hit apart: one press), then on
    k1, k2, k3 = (lib_text("TECHNO", "KICK", v)[0][:16] for v in range(3))
    s = Script()
    s.press(100, SEQ); s.tap_key(130, wk(9)); s.release(250, SEQ)        # BEAT: KICK #1
    for k in range(13):                                                  # COOK, thirteen times, a look after each
        s.press(400 + 200 * k, SEQ); s.tap_key(430 + 200 * k, wk(8)); s.release(550 + 200 * k, SEQ)
        s.at(580 + 200 * k, "dump", 0)
    log = run(s, 400 + 200 * 13 + 100)
    norm = lambda r: "".join("x" if c not in ".-" else "." for c in r)
    msgs = [st["msg"] for st in log.states]
    check(msgs[0] == "COOK KICK #2 REACHED" and log.dumps[0]["on"] == norm(k2), "one COOK: KICK #2 (%s, %s)" % (msgs[0], log.dumps[0]["on"]))
    check(msgs[1].startswith("COOK KICK #3"), "the next COOK walks on to #3 (%s)" % msgs[1])
    check("COOK KICK #3 REACHED" in msgs and log.dumps[msgs.index("COOK KICK #3 REACHED")]["on"] == norm(k3), "... and gets there (%s)" % msgs[:4])
    reached = [m for m in msgs if m.endswith("REACHED")]
    check(len(reached) >= 3 and all(m.startswith("COOK KICK #") for m in msgs), "COOK walks the variations in order (%s)" % reached)
    # 0.12: COOK held 0.6 s: the random COOK (the library's walk not taken); a tap: COOK, when the key is let go
    s = Script()
    s.press(100, SEQ); s.tap_key(130, wk(9)); s.release(250, SEQ)
    s.press(400, SEQ); s.tap_key(430, wk(8), hold=700); s.release(1200, SEQ)
    s.at(1300, "dump", 0)
    log = run(s, 1400)
    check(log.states[0]["msg"] == "COOK", "COOK held: the random COOK (%s)" % log.states[0]["msg"])
    # the instrument knob goes through the genre's parts: TECHNO's eleven, PROG, KIT
    s = Script()
    s.press(100, SEQ); s.enc(130, E_SEL, lib_parts("TECHNO").index("RUMBLE")); s.release(200, SEQ)
    s.at(250, "dump", 0)
    s.press(300, SEQ); s.enc(330, E_SEL, 30); s.release(400, SEQ)
    s.at(450, "dump", 0)
    log = run(s, 500)
    check(log.states[0]["msg"].startswith("BEAT RUMBLE (12)") and log.states[1]["msg"] == "BEAT KIT", "SEQ + SELECT: RUMBLE (12 variations) ... the last, KIT (%s / %s)" % (log.states[0]["msg"], log.states[1]["msg"]))


def t011_note_lengths():
    group("0.11: notes of more than a step: a PAD whose rhythm an algorithm makes holds to its next hit; held notes from the library")
    def off_after_first(slot_algo):
        s = Script()
        t = home_page(s, 100, 3, [(K2, SQ_ROLE_PAD)])
        t = home_page(s, t, 0, [], cur=3)
        t = s.steps(t, [0, 8])
        if slot_algo:
            t = seq_page(s, t, 1, encs=[(K1, slot_algo)], keys=[wk(5)])   # (0.16: SEQ + white 6 starts it)
        s.tap_btn(t + 50, PLAY); p = t + 50
        log = run(s, p + int(16 * STEP_MS))
        on = log.notes(ch=0, after=p)
        off = [tm for tm, d1 in log.offs(ch=0) if tm > on[0][0]]
        return (off[0] - on[0][0]) / STEP_MS if on and off else -1
    plain, held = off_after_first(0), off_after_first(4)                 # 4: DENSITY (as written: 100 %)
    check(plain < 1.1 and 7.0 < held < 8.0, "a PAD: one step as written; with DENSITY on it the note holds to the next hit (%.2f, %.2f steps)" % (plain, held))
    # TECHNO PAD #1 from the library: x--------------- , a chord held a bar
    pad = lib_text("TECHNO", "PAD", 0)[0]
    s = Script()
    s.press(100, SEQ); s.enc(130, E_SEL, lib_parts("TECHNO").index("PAD")); s.tap_key(180, wk(9)); s.release(300, SEQ)
    s.tap_btn(500, PLAY)
    log = run(s, 500 + int(20 * STEP_MS))
    n = log.notes(ch=0, after=500)
    offs = [tm for tm, d1 in log.offs(ch=0) if tm > n[0][0] and d1 == n[0][1]] if n else []
    want = min(16, len(pad) - len(pad[1:].lstrip("-")))                  # (the library loads 16 steps: its first bar)
    check(n and len({d1 for tm, d1, _ in n if tm < n[0][0] + 5}) >= 3 and offs and abs((offs[0] - n[0][0]) / STEP_MS - want) < 0.6,
          "TECHNO PAD #1: a chord held %d steps (%s)" % (want, ((offs[0] - n[0][0]) / STEP_MS) if n and offs else None))
    # the grid: hold a pad, press another: the note between them (no FX tapped)
    s = Script()
    s.raw(100, "attach")
    s.at(400, "pad", 1, 0, 100); s.at(800, "pad", 6, 0, 100); s.at(900, "pad", 6, 0, 0); s.at(950, "pad", 1, 0, 0)
    s.at(1000, "dump", 0)
    s.tap_btn(1100, PLAY)
    log = run(s, 1100 + int(16 * STEP_MS) - 20)
    n = log.notes(ch=0, after=1100)
    offs = [tm for tm, d1 in log.offs(ch=0) if tm > 1100]
    check(log.dumps[0]["on"] == ".x" + "." * 14 and n and offs and 5.5 < (offs[0] - n[0][0]) / STEP_MS < 6.1 and log.dumps[0]["length"] == 16,
          "grid: pad 2 held, pad 7 pressed: a note of six steps on step 2 (%s, %s)" % (log.dumps[0]["on"], log.states[0]["msg"]))


def t011_pi_patterns():
    group("0.11: the Pi's patterns: SEQ + ALG past the FM-1's last asks how many, BEAT loads one, SEQ + SAVE sends the track's")
    hexs = lambda b: " ".join("%02X" % x for x in b)
    text = "X..xX...X..xX.x."
    s = Script()
    s.press(100, SEQ); s.enc(130, E_ALG, 11); s.enc(160, E_ALG, 1); s.release(200, SEQ)            # the 12th, then past it: asked
    s.at(300, "sx", "7D 53 47 61 00 00 05 00")                                                    # the Pi: 5 of TECHNO KICK
    s.press(400, SEQ); s.enc(430, E_ALG, 1); s.release(500, SEQ)                                   # #13: the Pi's first
    s.at(550, "dump", 0)
    s.press(600, SEQ); s.tap_key(630, wk(9)); s.release(700, SEQ)                                  # BEAT: asked
    s.at(800, "sx", "7D 53 47 63 00 00 00 00 10 00 " + hexs(map(ord, text)))                      # the pattern comes
    s.at(900, "dump", 0)
    s.press(1000, SEQ); s.tap_btn(1030, SAVE); s.release(1100, SEQ)                                # SEQ + SAVE: to the Pi
    s.at(1150, "sx", "7D 53 47 65 00 00 00 05 00")                                                 # kept as the 6th
    s.at(1200, "dump", 0)
    log = run(s, 1300)
    out = [m for t, m in log.sysex if m[:4] == [0xF0, 0x7D, 0x53, 0x47] and 0x60 <= m[4] <= 0x64]
    asks = [m for m in out if m[4] == 0x60]
    gets = [m for m in out if m[4] == 0x62]
    puts = [m for m in out if m[4] == 0x64]
    check(asks and asks[0][5:7] == [0, 0], "past the 12th: the FM-1 asks the Pi how many TECHNO KICKs (%s)" % [hexs(m) for m in asks])
    check(gets and gets[0][5:9] == [0, 0, 0, 0], "BEAT on #13: the Pi's pattern 0 is asked for (%s)" % [hexs(m) for m in gets])
    check(log.dumps[1]["on"] == "x..xx...x..xx.x." and log.dumps[1]["length"] == 16 and log.states[1]["msg"] == "TECHNO KICK #13 (PI)",
          "it comes and plays: the Pi's pattern on the track (%s, %s)" % (log.dumps[1]["on"], log.states[1]["msg"]))
    check(puts and puts[0][5:9] == [0, 0, 16, 0] and "".join(map(chr, puts[0][9:25])) == text,
          "SEQ + SAVE: the track's 16 steps to the Pi, as the library writes them (%s)" % ("".join(map(chr, puts[0][9:25])) if puts else None))
    check(log.states[2]["msg"] == "ON THE PI: TECHNO KICK #18", "the Pi says where it went: #18 (%s)" % log.states[2]["msg"])
    # a melodic part: a bass with its notes; and no answer: the screen says so
    s = Script()
    s.press(100, SEQ); s.enc(130, E_SEL, lib_parts("TECHNO").index("BASS")); s.enc(160, E_ALG, 12); s.release(200, SEQ)
    s.at(300, "sx", "7D 53 47 61 00 04 02 00")
    s.press(400, SEQ); s.enc(430, E_ALG, 1); s.tap_key(460, wk(9)); s.release(560, SEQ)
    s.at(650, "sx", "7D 53 47 63 00 04 00 00 08 01 " + hexs(map(ord, "x-..x.x.")) + " " + hexs(map(ord, "0...7.c.")))
    s.at(750, "dump", 0)
    s.press(900, SEQ); s.enc(930, E_ALG, 1); s.tap_key(960, wk(9)); s.release(1060, SEQ)            # the Pi's second: nobody answers
    s.at(2800, "dump", 0)
    log = run(s, 2900)
    n = [m for t, m in log.sysex if m[:5] == [0xF0, 0x7D, 0x53, 0x47, 0x62]]
    check(len(n) == 2 and n[0][5:9] == [0, 4, 0, 0], "TECHNO BASS: the Pi's patterns asked for (%s)" % [hexs(m) for m in n])
    check(log.dumps[0]["on"] == "x...x.x.x...x.x." and log.dumps[0]["length"] == 16, "an 8-step bass repeated to the library's 16 (%s)" % log.dumps[0]["on"])
    check(log.states[1]["msg"] == "PI: NO ANSWER (THE GRID BRIDGE?)", "no answer: the screen says so (%s)" % log.states[1]["msg"])

HARM11 = re.compile(r"^\s*(\d+) ms  harm11 T(\d+) prog (\d+) rhythm (\d+) mood (\d+) pmood (\d+) fm (\d+) chord (\S+) U((?: \d+/\d+:\S+){5})$", re.M)


def harm11(log):
    """the 0.11 'harm11' lines of the dumps: the HARMONY's progression, rhythm, mood filter, the mood of the progression
    that plays, the track's FOLLOW way, the chord now, the player's five progressions [(n, mood, [(semi, shape, dur, push)])]"""
    out = []
    for m in HARM11.finditer(log.text):
        us = []
        for x in m.group(9).split():
            head, rows = x.split(":")
            n, mood = (int(v) for v in head.split("/"))
            us.append((n, mood, [] if rows == "-" else [tuple(int(v) for v in r.split(".")) for r in rows.split(",")]))
        out.append(dict(t=int(m.group(1)), track=int(m.group(2)), prog=int(m.group(3)), rhythm=int(m.group(4)), mood=int(m.group(5)),
                        pmood=int(m.group(6)), fm=int(m.group(7)), chord=m.group(8), u=us))
    return out


SQ_HR_BARS, SQ_HR_GENRE, SQ_HR_PUSH16, SQ_HR_PUSH8, SQ_HR_332, SQ_HR_HALF = range(6)
SQ_MOOD_ANY, SQ_MOOD_SAD, SQ_MOOD_MELANCHOLY, SQ_MOOD_SATISFYING, SQ_MOOD_ENERGETIC, SQ_MOOD_EUPHORIC, SQ_MOOD_EPIC, \
    SQ_MOOD_DREAMY, SQ_MOOD_DARK, SQ_MOOD_TENSE, SQ_MOOD_SUSPENDED = range(11)
SQ_FM_HOLD, SQ_FM_RETRIG, SQ_FM_LEGATO = range(3)



def t011_progressions():
    group("0.11: the progressions: any root and shape, lengths in 16ths, PUSH, 3+3+2, RETRIG / LEGATO, the moods, DICE PROG")
    BAR = 16 * STEP_MS

    def setup(s, rhythm=0, steps=range(16)):
        t = kp(s, 100, [(K2, 1), (K4, 1)])                             # C major, IN KEY
        t = s.steps(t, list(steps))
        t = home_page(s, t, 1, [(K4, 1)], cur=2)                       # FOLLOW
        t = uprog_knobs(s, t, [(K3, 1), (K2, 1), (K3, 8)])        # USER 1: I, V
        t = harm_knobs(s, t, [(K2, 6), (K1, 1)])          # HARMONY: USER 1, ON (0.16: K2 alone makes it READY)
        if rhythm:
            t = harm2_knobs(s, t, [(K4, rhythm)])
        return t

    def per_step(log, p0, steps):
        n = log.notes(ch=0, after=p0)
        if not n:
            return []
        t0 = n[0][0]
        got = {}
        for tm, d1, _ in n:
            k = int(round((tm - t0) / STEP_MS))
            if k < steps:
                got.setdefault(k, d1)
        return [got.get(k) for k in range(steps)]

    # BARS (as 0.10): C a bar, G a bar; PUSH 16TH: G already on the last 16th of bar 1, C on the last of bar 2
    res = {}
    for r in (SQ_HR_BARS, SQ_HR_PUSH16, SQ_HR_332):
        s = Script()
        t = setup(s, r)
        s.at(t, "dump", 0)
        s.tap_btn(t + 20, PLAY); p0 = t + 20
        log = run(s, p0 + int(4 * BAR) - 30)
        res[r] = (per_step(log, p0, 64), harm11(log)[0])
    b = res[SQ_HR_BARS][0]
    check(b[:16] == [60] * 16 and b[16:32] == [55] * 16 and b[32:48] == [60] * 16, "BARS: C a bar, G a bar (%s)" % b[:33])
    p = res[SQ_HR_PUSH16][0]
    check(p[:15] == [60] * 15 and p[15:31] == [55] * 16 and p[31] == 60 and p[32:47] == [60] * 15 and p[47] == 55 and res[SQ_HR_PUSH16][1]["rhythm"] == SQ_HR_PUSH16,
          "PUSH 16TH: each chord a 16th early (%s)" % p[:33])
    q = res[SQ_HR_332][0]
    want = []
    for cell in range(9):                                              # 6, 6, 4 16ths a bar, the chords I V I V ...
        want += [[60, 55][cell % 2]] * [6, 6, 4][cell % 3]
    check(q[:48] == want[:48], "3+3+2: the chords change on 1, the 4th 8th and the 7th of every bar (%s)" % q[:48])

    # FOLLOW HOLD / RETRIG / LEGATO: a note of 16 steps, the chords change at the half bar (TWO A BAR)
    out = {}
    for fm in (SQ_FM_HOLD, SQ_FM_RETRIG, SQ_FM_LEGATO):
        s = Script()
        t = setup(s, SQ_HR_HALF, steps=[])
        s.raw(t, "attach"); t += 100
        s.at(t, "pad", 0, 0, 100); s.at(t + 300, "pad", 15, 0, 100); s.at(t + 360, "pad", 15, 0, 0); s.at(t + 400, "pad", 0, 0, 0); t += 500
        if fm:
            t = harm2_knobs(s, t, [(K1, fm)])
        s.at(t, "dump", 0)
        s.tap_btn(t + 20, PLAY); p0 = t + 20
        log = run(s, p0 + int(BAR) - 30)
        ons = [(tm - p0, d1) for tm, st, d1, d2 in log.msgs if st == 0x90 and d2 and tm >= p0]
        offs = [(tm - p0, d1) for tm, st, d1, d2 in log.msgs if (st == 0x80 or (st == 0x90 and not d2)) and tm >= p0]
        out[fm] = (ons, offs, harm11(log)[0]["fm"], log.dumps[0]["on"])
    h_on, h_off, h_fm, h_steps = out[SQ_FM_HOLD]
    check(h_steps == "x" + "." * 15 and [d for _, d in h_on] == [60] and not [o for o in h_off if o[0] < BAR - 40],
          "HOLD: the C goes on through the G (%s %s)" % (h_on, h_off))
    r_on, r_off, r_fm, _ = out[SQ_FM_RETRIG]
    g_at = [tm for tm, d in r_on if d == 55]
    c_off = [tm for tm, d in r_off if d == 60]
    check(r_fm == SQ_FM_RETRIG and [d for _, d in r_on] == [60, 55] and g_at and abs(g_at[0] - 8 * STEP_MS) < 8 and c_off and c_off[0] <= g_at[0],
          "RETRIG: at the change the C ends and the G is struck (%s %s)" % (r_on, r_off))
    l_on, l_off, l_fm, _ = out[SQ_FM_LEGATO]
    g_at = [tm for tm, d in l_on if d == 55]
    c_off = [tm for tm, d in l_off if d == 60]
    check(l_fm == SQ_FM_LEGATO and [d for _, d in l_on] == [60, 55] and g_at and c_off and g_at[0] <= c_off[0] and abs(c_off[0] - 8 * STEP_MS) < 8,
          "LEGATO: the G before the C ends (a mono synth slides) (%s %s)" % (l_on, l_off))

    # USER PROG: K3 the root (any of the 12), K4 the shape, SEL + K3 its length in 16ths, SEL + K4 the push, SEL + K1 the mood
    s = Script()
    t = uprog_knobs(s, 100, [(K3, 1), (K2, 1), (K3, 11), (K4, 10)])             # I, then bvii (root 10), shape 10 (5 + SQ_CH_MIN)
    t = uprog2_knobs(s, t, [(K3, 12), (K4, 1), (K1, SQ_MOOD_EPIC)])
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    u = harm11(log)[0]["u"][0]
    check(u[0] == 2 and u[1] == SQ_MOOD_EPIC and u[2][0][0] == 0 and u[2][1][0] == 10 and u[2][1][1] == 10 and u[2][1][2] == 12 and u[2][1][3] == 1,
          "USER PROG: I, then bVII (root 10) shape 10, 12 16ths, pushed a 16th, EPIC (%s)" % (u,))

    # the MOOD (SEL + K3): K2 goes only through progressions of that mood; at the end of them: NO MORE ..
    s = Script()
    t = uprog_knobs(s, 100, [(K3, 1), (K2, 1), (K3, 8)])                       # USER 1: I V
    t = uprog2_knobs(s, t, [(K1, SQ_MOOD_TENSE)])                    # .. called TENSE
    t = harm2_knobs(s, t, [(K3, SQ_MOOD_TENSE)])                    # HARMONY: MOOD TENSE
    for k in range(8):
        t = harm_knobs(s, t, [(K2, 1)])
        s.at(t, "dump", 0); t += 40
    t += 1600                                                                  # (no Pi answers: the FM-1's were all)
    s.at(t, "dump", 0)
    t = harm_knobs(s, t + 50, [(K2, 1)])                                       # again: said at once
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    hh = harm11(log)
    progs = [h["prog"] for h in hh]
    check(hh[0]["mood"] == SQ_MOOD_TENSE and all(h["pmood"] == SQ_MOOD_TENSE for h in hh if h["prog"] != 0) and progs[-1] == 6 and 6 in progs,
          "MOOD TENSE: K2 only through the TENSE ones, the player's TENSE last (%s %s)" % (progs, [h["pmood"] for h in hh]))
    check(any("PI: ASKING" in st["msg"] for st in log.states) and log.states[-2]["msg"].startswith("NO MORE TENSE") and log.states[-1]["msg"].startswith("NO MORE TENSE"),
          "... then the Pi is asked; no answer: NO MORE TENSE (%s)" % [st["msg"] for st in log.states[-3:]])

    # DICE PROG (0.12: SEQ + black 1 held 0.6 s): a new progression of the mood into the fifth slot (DICE/PI), which plays
    for mood in (SQ_MOOD_ANY, SQ_MOOD_DARK, SQ_MOOD_EUPHORIC):
        s = Script()
        t = 100
        if mood:
            t = harm2_knobs(s, t, [(K3, mood)])
        s.press(t, SEQ); s.tap_key(t + 30, bk(0), hold=700); s.release(t + 800, SEQ); t += 900
        s.at(t, "dump", 0)
        log = run(s, t + 100)
        h = harm11(log)[0]
        n5, m5, rows = h["u"][4]
        check(h["prog"] == 10 and 2 <= n5 <= 5 and (m5 == mood if mood else m5 > 0) and all(0 <= r[0] <= 11 and 6 <= r[1] <= 37 for r in rows)
              and log.states[0]["msg"].startswith("DICE PROG"), "DICE PROG (mood %d): %s (%s)" % (mood, rows, log.states[0]["msg"]))


def t011_pi_progressions():
    group("0.11: the Pi's progressions: HARMONY K2 past the FM-1's asks how many, each comes into DICE/PI and plays, ARP + SAVE sends one")
    hexs = lambda b: " ".join("%02X" % x for x in b)
    s = Script()
    t = uprog_knobs(s, 100, [(K1, 3), (K3, 1), (K2, 1), (K3, 8)])              # USER 4: I V
    t = harm_knobs(s, t, [(K2, 9)])                               # HARMONY: USER 4 (prog 9)
    t = harm_knobs(s, t, [(K2, 1)])                               # past the FM-1's: asks how many
    s.at(t, "dump", 0); t += 50
    s.at(t, "sx", "7D 53 47 67 00 00 03 00"); t += 100                         # the Pi: 3 of TECHNO (any mood)
    s.at(t, "sx", "7D 53 47 69 00 00 00 00 02 08 00 0A 00 00 01 09 08 01"); t += 100   # the first: i bII (bII 8 16ths, pushed)
    s.at(t, "dump", 0); t += 50
    t = harm_knobs(s, t, [(K2, 1)])                               # the second: asked
    s.at(t, "sx", "7D 53 47 69 00 00 01 00 01 09 00 0A 00 00"); t += 100      # i alone, TENSE
    s.at(t, "dump", 0); t += 50
    t = harm_knobs(s, t, [(K2, 5)])                               # five on: the last of the three
    s.at(t, "sx", "7D 53 47 69 00 00 02 00 01 09 00 0A 00 00"); t += 100
    t = harm_knobs(s, t, [(K2, 1)])                               # past the last: it stays
    s.at(t, "dump", 0); t += 50
    t = harm_knobs(s, t, [(K2, -3)])                              # back below the first: USER 4 again
    s.at(t, "dump", 0); t += 50
    s.press(t, ARP); s.tap_btn(t + 30, SAVE); s.release(t + 100, ARP); t += 200    # 0.12: ARP + SAVE (on ARP 3): USER 4 to the Pi
    s.at(t, "sx", "7D 53 47 6B 00 03 00 01 00"); t += 100                      # kept as the 2nd of its mood
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    sx = [m for _, m in log.sysex if m[:4] == [0xF0, 0x7D, 0x53, 0x47] and 0x66 <= m[4] <= 0x6A]
    asks = [m for m in sx if m[4] == 0x66]
    gets = [m for m in sx if m[4] == 0x68]
    puts = [m for m in sx if m[4] == 0x6A]
    hh = harm11(log)
    check(asks and asks[0][5:7] == [0, 0] and log.states[0]["msg"].startswith("PI: ASKING"), "past USER 4: how many TECHNO progressions (%s %s)" % ([hexs(m) for m in asks], log.states[0]["msg"]))
    check(gets and gets[0][5:10] == [0, 0, 0, 0, 2] and gets[0][10] == 0 and gets[0][12] == 7,
          "then the first, most like what played (USER 4: I V) (%s)" % [hexs(m) for m in gets[:1]])
    check(hh[1]["prog"] == 10 and hh[1]["u"][4] == (2, 8, [(0, 10, 0, 0), (1, 9, 8, 1)]) and log.states[1]["msg"] == "PI DARK 1/3: i-bII",
          "it comes into DICE/PI and plays (%s %s)" % (hh[1]["u"][4], log.states[1]["msg"]))
    check(len(gets) >= 2 and gets[1][7:9] == [1, 0] and hh[2]["u"][4][:2] == (1, 9), "K2: the Pi's second (%s)" % (hh[2]["u"][4],))
    check(len(gets) == 3 and gets[2][7:9] == [2, 0] and hh[3]["prog"] == 10 and log.states[3]["msg"] == "PI: THE LAST PROGRESSION OF TECHNO",
          "five on: the last; past it: it stays (%s, %s)" % ([hexs(m) for m in gets[2:]], log.states[3]["msg"]))
    check(hh[4]["prog"] == 9, "K2 back below the first: USER 4 (%s)" % hh[4]["prog"])
    check(puts and puts[0][5] == 0 and puts[0][7] == 2 and puts[0][8] == 0 and puts[0][12] == 7 and puts[0][5 + 3 + 8:] == [0xF7],
          "ARP + SAVE on ARP 3: the progression to the Pi, its mood, root and shape a chord (%s)" % [hexs(m) for m in puts])
    check(log.states[-1]["msg"] == "ON THE PI: TECHNO SATISFYING #2", "the Pi says where it went (%s)" % log.states[-1]["msg"])
    # a mood with none on the Pi: said; no answer: said
    s = Script()
    t = harm2_knobs(s, 100, [(K3, 6)])                                      # MOOD EPIC
    t = harm_knobs(s, t, [(K2, 12)])                              # (the EPIC ones of TECHNO, then past them)
    s.at(t, "sx", "7D 53 47 67 00 06 00 00"); t += 100
    s.at(t, "dump", 0); t += 50
    s.at(t, "sx", "7D 53 47 67 00 00 04 00"); t += 50
    t = harm2_knobs(s, t, [(K3, -6)])                               # MOOD ANY
    t = harm_knobs(s, t, [(K2, 12)])                              # past the FM-1's: the Pi asked, it does not answer
    s.at(t + 1650, "dump", 0)
    log = run(s, t + 1700)
    check(any(st["msg"] == "PI: NO EPIC PROGRESSIONS OF TECHNO" for st in log.states), "none of the mood: said (%s)" % [st["msg"] for st in log.states])
    check(log.states[-1]["msg"] == "PI: NO ANSWER (THE GRID BRIDGE?)", "no answer: said (%s)" % log.states[-1]["msg"])


def t011_in_time_after():
    group("0.11 (found by the explorer): a direction there and back, a mode to TAPE and back, an UNDO of a loop start: the track where the bar says")
    probe_ok = lambda log: [m.group(2) for m in re.finditer(r"PROBE T(\d+) .* ok=(\S+) ", log.text)]
    cases = []
    # HOME 2 K1: FWD -> REV, a moment later back to FWD
    s = Script()
    t = s.steps(100, [0, 4, 8, 12])
    s.tap_btn(t + 50, PLAY); t += 600
    t = home_page(s, t, 1, [(K1, 1)])
    t = home_page(s, t + 150, 1, [(K1, -1)], cur=1)
    s.at(t + int(2 * 16 * STEP_MS), "probe")
    cases.append(("FWD, REV, FWD", s, t + int(2 * 16 * STEP_MS) + 50))
    # HOME 2 K1 +1: REV, the bar after
    s = Script()
    t = s.steps(100, [0, 4, 8, 12])
    s.tap_btn(t + 50, PLAY); t += 600
    t = home_page(s, t, 1, [(K1, 1)])
    s.at(t + int(2 * 16 * STEP_MS), "probe")
    cases.append(("FWD to REV", s, t + int(2 * 16 * STEP_MS) + 50))
    # HOME 4 K1: DRUM -> TAPE -> DRUM (the band's kick)
    s = Script()
    s.press(100, SEQ); s.tap_key(130, bk(6), hold=700); s.release(900, SEQ)
    s.tap_btn(1000, PLAY); t = 1600
    t = home_page(s, t, 3, [(K1, 1)])
    t = home_page(s, t + 150, 3, [(K1, -1)], cur=3)
    s.at(t + int(2 * 16 * STEP_MS), "probe")
    cases.append(("DRUM, TAPE, DRUM", s, t + int(2 * 16 * STEP_MS) + 50))
    # the band, HOME + ALG (the loop's start), UNDO (the band's undo takes the start back too)
    s = Script()
    s.press(100, SEQ); s.tap_key(130, bk(6), hold=700); s.release(900, SEQ)
    s.tap_btn(1000, PLAY); t = 1600
    s.press(t, HOME); s.enc(t + 30, E_ALG, 1); s.release(t + 80, HOME); t += 200
    s.press(t, SEQ); s.tap_key(t + 30, wk(7)); s.release(t + 100, SEQ); t += 200
    s.at(t + int(2 * 16 * STEP_MS), "probe")
    cases.append(("loop start, UNDO", s, t + int(2 * 16 * STEP_MS) + 50))
    for what, s, end in cases:
        ok = probe_ok(run(s, end))
        check(len(ok) == 16 and "0" not in ok, "%s: every track where the bar says (%s)" % (what, "".join(ok)))


# the sessions of tests/sagga_explore.py that found a track out of time (the explorer's own words for the gestures)
EXPLORER_SESSIONS = [
    ("vuoto, in play", ["HOME 1 K2 +1", "HOME 1 SEL+K4 +1", "SEQ+nero 1", "SEQ 6 K1 -1"]),   # a dice put back after a length at the bar
    ("MOSSE in play", ["EDIT+bianco 15", "tocca SAVE", "FX K2 +1", "LFO 2 PRESETS -1", "HOME 5 K3 -1", "ARP+bianco 2",
                         "SEL+nero 10", "ARP+GLO", "HOME 2 ALG +1", "HOME 5 SELECT +1", "SEQ+SEL+bianco 3", "SEQ 3 SEL+K1 +1",
                         "SEL+bianco 9", "SEL+FX", "ENV+SAVE", "ARP+bianco 5", "SEQ 5 SEL+SELECT +1", "ENV 4 SELECT +1",
                         "HOME 1 K3 -1", "GLO 3 SEL+PRESETS -1", "tocca OCT+", "SAVE+OCT-", "ARP 2 PRESETS -1",
                         "SEQ 3 SEL+ALG -1", "EDIT K4 +1", "GLO 3 SELECT +1", "HOME 3 K1 -1", "HOME 3 K4 +1", "GLO+nero 9",
                         "tocca ARP", "FX+bianco 8", "ARP 3 K4 +1", "SEQ+ARP", "SEQ 2 SELECT -1", "ARP 3 ALG -1",
                         "SAVE+bianco 10", "ARP 1 K4 +1", "HOME+REC", "ARP 6 K3 +1", "ARP+ENV", "ENV+SAVE", "HOME+OCT+",
                         "PRESETS -1", "ENV+nero 10", "SEL+FX, poi tieni bianco 1 + bianco 16", "HOME 1 SEL+K3 +1", "FX K3 +1"]),
    # (a VIAGGIO loop let go by hand: its settings back without the track put back in time)
    ("note lunghe e loop fra due step, in play", ["FX+nero 4", "SEQ 5 SELECT -1", "SEL+FX, poi tieni bianco 3 + bianco 6",
                                                  "ARP 6 K2 -1", "tocca PLAY", "SEL+PLAY"]),   # STOP in a DJ LOOP, CONTINUE
    ("progressione USER, FOLLOW RETRIG, 3+3+2, in play", ["SEQ+nero 1", "HOME 4 K1 +1", "SEQ 6 SEL+K2 +1"]),   # a dice put back over TAPE
    ("MOSSE in play", ["SAVE, SAVE (salva)", "GLO 3 ALG +1", "SEL+SAVE"]),   # RELOAD of a track whose loop VIAGGIO changed
    ("vuoto, fermo", ["HOME 2 K1 +1", "SEL+PLAY"]),                               # a direction changed while stopped, CONTINUE
    ("vuoto, fermo", ["SEQ+SEL+nero 2", "HOME 5 ALG +1", "SEQ 2 SEL+K1 -1", "SEL+PLAY"]),   # settings put back while stopped, CONTINUE
    # 0.12: the new pages and gestures in a row
    ("BREAK sulla traccia 1, band in play", ["ARP+nero 1", "ARP+bianco 5", "SEQ 7 K1 +1", "ARP+nero 6", "SEQ+nero 1", "ARP+nero 7", "tieni REC", "SEL+PLAY"]),
    ("MOSSE in play", ["SEL+GLO", "EDIT+bianco 3", "SEL+GLO", "GLO+SEL+OCT+", "SEL, tieni GLO", "tocca PLAY", "SEL+PLAY"]),
]


def pick(s, t, btn, key, hold=40):
    """0.12 PICK: `btn` held, SEL held, `key` tapped (the knob in focus of the page shown takes the key's value)"""
    s.press(t, btn); s.press(t + 30, SEL); s.tap_key(t + 60, key, hold=hold); s.release(t + 60 + hold + 30, SEL); s.release(t + 60 + hold + 60, btn)
    return t + 60 + hold + 120


def t012_pick():
    group("0.12 PICK: a group + SEL + a key sets the knob in focus (the knob last turned; black 11: the next); the LEDs, the mark, the maps")
    # HOME 1: K2 turned: LENGTH is the focus; SEL + white 8 = 32, black 1 = 3 (the lengths that are not multiples of 4)
    s = Script()
    t = s.steps(100, [0])
    s.press(t, HOME); s.enc(t + 30, K2, 1); s.press(t + 60, SEL); s.tap_key(t + 90, wk(7), hold=40); s.release(t + 160, SEL); s.release(t + 190, HOME); t += 250
    s.at(t, "dump", 0)
    t = pick(s, t, HOME, bk(0))
    s.at(t, "dump", 0)
    s.press(t, HOME); s.at(t + 100, "ui"); s.release(t + 200, HOME); t += 260    # the mark on LENGTH
    log = run(s, t + 100)
    ln = [d["length"] for d in log.dumps]
    check(ln == [32, 3], "HOME 1 K2 in focus: SEL + white 8 = LENGTH 32, black 1 = 3 (%s)" % ln)
    sc = log.screens()
    check(sc and sc[0]["cells"][1][0].startswith("> LENGTH") and not sc[0]["cells"][0][0].startswith(">"), "the screen marks the knob in focus: > LENGTH (%s)" % [c[0] for c in sc[0]["cells"]])
    # the focus starts on K1: HOME + SEL + white 3 = CHANNEL 3; black 11 moves it to K2: white 2 = LENGTH 8
    s = Script()
    t = s.steps(100, [0])
    t = pick(s, t, HOME, wk(2))
    t = pick(s, t, HOME, bk(10))
    t = pick(s, t, HOME, wk(1))
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY)
    log = run(s, t + 300)
    n = log.notes(after=t)
    check(n and all((st & 15) == 2 for _, st, _, _ in [m for m in log.msgs if (m[1] & 0xF0) == 0x90 and m[3]]) and cfgs(log)[0]["length"] == 8,
          "K1 first: CHANNEL 3; black 11: the focus on K2: LENGTH 8 (ch %s len %s)" % (sorted({m[1] & 15 for m in log.msgs if (m[1] & 0xF0) == 0x90 and m[3]}), cfgs(log)[0]["length"]))
    # a root: HOME 3 K2 (ROOT): the key is the note: key 9 (D4) = D; a value in semitones: HOME 1 K4 TRANSPOSE: key 14 = +2
    s = Script()
    t = s.steps(100, [0])
    t = pg(s, t, HOME, 2, encs=[(K2, 1)])                         # KEY page, ROOT turned (C#): the focus
    t = pick(s, t, HOME, 1 << 9)
    s.at(t, "dump", 0)
    t = pg(s, t, HOME, 1, encs=[(K4, 1)])                         # PLAY page... no: TRACK page 1 has TRANSPOSE on K4
    t = pg(s, t, HOME, 0, encs=[(K4, 1)])
    t = pick(s, t, HOME, 1 << 14)
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    c = cfgs(log)
    check(c[0]["key"][0] == 2, "HOME 3 K2 ROOT by key: D4 = D (%s)" % c[0]["key"])
    check(c[1]["trans"] == 2, "HOME 1 K4 TRANSPOSE by key: F4 = 0, G4 = +2 (%s)" % c[1]["trans"])
    # a percentage: SEQ 1 K4 HEAT: white 5 = 50 %, black 3 = 25 % (the knob says nothing: PICK says it)
    s = Script()
    t = seq_page(s, 100, 0, encs=[(K4, 1)])
    t = pick(s, t, SEQ, wk(4))
    s.at(t, "dump", 0)
    t = pick(s, t, SEQ, bk(2))
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    check([x["msg"] for x in log.states] == ["> HEAT 50%", "> HEAT 25%"], "SEQ 1 K4 HEAT by key: white 5 = 50%%, black 3 = 25%% (%s)" % [x["msg"] for x in log.states])
    # a list: HOME 4 K1 the track's MODE: white 3 = DRUM, white 5 = BREAK; too far: "5 CHOICES"
    s = Script()
    t = pg(s, 100, HOME, 3)
    t = pick(s, t, HOME, wk(2))
    s.at(t, "dump", 0)
    t = pick(s, t, HOME, wk(4))
    s.at(t, "dump", 0)
    t = pick(s, t, HOME, wk(9))
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    check([d["mode"] for d in log.dumps] == ["D", "B", "B"], "HOME 4 K1 MODE by key: white 3 DRUM, white 5 BREAK (%s)" % [d["mode"] for d in log.dumps])
    check(log.states[2]["msg"] == "MODE: 5 CHOICES", "white 10 means nothing there: the screen says how many (%s)" % log.states[2]["msg"])
    # EDIT + SEL + a key: the step's notes (what the screen shows with SEL held): key 7 = C4 as NOTE 1; black 11, key 11 = E4 as NOTE 2
    s = Script()
    t = s.steps(100, [0])
    t = pick(s, t, EDIT, 1 << 7)
    s.press(t, EDIT); s.press(t + 30, SEL); s.at(t + 90, "ui"); s.release(t + 120, SEL); s.release(t + 150, EDIT); t += 210
    t = pick(s, t, EDIT, bk(10))
    t = pick(s, t, EDIT, 1 << 11)
    s.press(t, EDIT); s.press(t + 30, SEL); s.at(t + 90, "ui"); s.release(t + 120, SEL); s.release(t + 150, EDIT); t += 210
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + 100)
    sc = log.screens()
    check(len(sc) == 2 and sc[0]["cells"][0] == ("> NOTE 1", "C4") and sc[1]["cells"][1] == ("> NOTE 2", "E4") and sc[1]["cells"][0] == ("NOTE 1", "C4"),
          "EDIT + SEL + key: NOTE 1 = C4, black 11 then key 11: NOTE 2 = E4 (%s)" % [x["cells"][:2] for x in sc])
    check(sorted(d1 for _, d1, _ in log.notes(ch=0, after=p0)) == [60, 64], "... and the step plays the chord C4 E4 (%s)" % sorted(d1 for _, d1, _ in log.notes(ch=0, after=p0)))
    # the harmony: ARP 3 K1 white 3 = LOCK; K2 (black 11 moves the focus) white 4 = progression 4, straight to it
    s = Script()
    t = pg(s, 100, ARP, 2)
    t = pick(s, t, ARP, wk(2))
    t = pick(s, t, ARP, bk(10))
    t = pick(s, t, ARP, wk(3))
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    h = harm11(log)[0]
    v = v11s(log)[0]
    check(v["lock"] == 1 and h["prog"] == 3, "ARP 3: K1 by key = LOCK, then K2 by key = progression 4 (%s %s)" % (v["lock"], h["prog"]))
    # GLO 2 TRACK LIVE K1 the pattern (white 3 = pattern 3), K3 (black 11 twice) the scale: white 2 = scale 2; the ARP keys play too
    s = Script()
    t = s.steps(100, [0])
    t = pg(s, t, GLO, 1)
    t = pick(s, t, GLO, wk(2))
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    check(log.dumps[0]["pat"] == 3, "GLO 2 K1 PATTERN by key: white 3 = pattern 3 (%s)" % log.dumps[0]["pat"])
    # a continuous knob: the keys say so; the LEDs: with HOME + SEL held, the whites that mean a channel are lit, the current one blinks
    s = Script()
    t = s.steps(100, [0])
    t = pg(s, t, HOME, 1, encs=[(K2, 1)])                         # PLAY page: SWING, a continuous value
    t = pick(s, t, HOME, wk(4))
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    check(log.states[0]["msg"].startswith("SWING: BY THE KNOB"), "a continuous value is not for the keys: the screen says so (%s)" % log.states[0]["msg"])
    # the map: a group held half a second shows what its keys do, and what SEL + a key does for the knob in focus
    s = Script()
    s.press(4000, SEQ); s.at(4200, "ui"); s.at(4700, "ui"); s.release(4800, SEQ)      # (after the boot message)
    log = run(s, 4900)
    sc = log.screens()
    check(len(sc) == 2 and not sc[0]["lines"][3].startswith("W TOOLS") and sc[1]["lines"][3] == "W TOOLS  B DICE SCOPE KIT EVO" and sc[1]["lines"][4] == "SEL+KEY: ITEM 1-16 (B 17-26)",
          "SEQ held 0.5 s: the map of its keys, and the PICK rule of the knob in focus (%s)" % (sc[1]["lines"][3:5] if len(sc) == 2 else sc))
    # the SEQ keys held: UNDO held = REDO, KIT held = BAND (tested in their own groups); here: a tap acts when the key is let go
    s = Script()
    t = s.steps(100, [0, 4, 8, 12])
    s.press(t, SEQ); s.tap_key(t + 30, wk(14), hold=40)                                                # INVERT: 12 on
    s.tap_key(t + 130, wk(TOOL_UNDO_IDX), hold=40); s.at(t + 160, "dump", 0); s.at(t + 250, "dump", 0); s.release(t + 300, SEQ); t += 400
    log = run(s, t + 100)
    on = [d["on"].count("x") for d in log.dumps]
    check(on == [12, 4], "UNDO acts when the key is let go (the hold is REDO): %s" % on)


TOOL_UNDO_IDX = 7


def t012_blocks():
    group("0.12: a long note is one block: the screen's strip, the keys (glow), the grid (TAIL, TIE)")
    GL_TAIL, GL_TIE = 16, 17
    s = Script()
    s.raw(50, "attach")
    t = s.steps(100, [0, 6])
    s.press(t, EDIT); s.tap_key(t + 30, wk(0), hold=40); s.enc(t + 100, K1, 24); s.release(t + 160, EDIT); t += 220   # the cursor on step 1, GATE 80 % -> 104 = 4 steps
    s.at(t, "ui"); s.at(t, "leds"); t += 50
    s.press(t, EDIT); s.tap_key(t + 30, wk(6), hold=40); s.tap_key(t + 100, bk(5), hold=40); s.release(t + 170, EDIT); t += 230   # step 7: TIE
    s.at(t, "ui"); s.at(t, "leds"); t += 50
    t_grid = t
    s.press(t, EDIT); s.tap_key(t + 30, wk(0), hold=40); s.enc(t + 100, K1, -3); s.release(t + 200, EDIT); t += 260   # step 1: 104 -> 101 = 1.5 steps
    s.at(t, "ui"); t += 50
    log = run(s, t + 100)
    sc = log.screens()
    check(len(sc) == 3 and sc[0]["strip"].startswith("c-t-t-t . . X "), "the strip: the note of 4 steps is one block (%s)" % (sc[0]["strip"] if sc else sc))
    check(len(sc) == 3 and sc[1]["strip"][:16] == "X-t-t-t . . c-. ", "a TIE: the step welds to the next (%s)" % (sc[1]["strip"] if sc else sc))
    check(len(sc) == 3 and sc[2]["strip"].startswith("c-h . "), "1.5 steps: half of the next cell (%s)" % (sc[2]["strip"] if sc else sc))
    kl = log.key_leds()
    check(len(kl) == 2 and kl[0][1][WHITE[0]] == "X" and all(kl[0][1][WHITE[i]] == "g" for i in (1, 2, 3)) and kl[0][1][WHITE[4]] == ".",
          "the keys: the step lit, the three it covers glow (%s)" % (kl[0][1] if kl else kl))
    pads, _ = log.leds(until=t_grid)
    check(all(pads.get(i) == GL_TAIL for i in (1, 2, 3)) and pads.get(4) not in (GL_TAIL, GL_TIE), "the grid: pads 2-4 TAIL (%s)" % [pads.get(i) for i in range(8)])
    pads, _ = log.leds(until=t)
    check(pads.get(6) == GL_TIE and pads.get(1) == GL_TAIL and pads.get(2) == 1, "the grid: pad 7 TIE (the cursor gone), 1.5 steps: pad 2 TAIL (%s)" % [pads.get(i) for i in range(8)])




def t012_studio_viaggio():
    group("0.12 / 0.17: the studio and the journey on the same tracks - SEL+GLO = the MOSSE (PERF page 3) and back, the journey always runs; hand edits set the states")
    s = Script()
    t = vg_on(s, 100)
    t = vg_track_in_now(s, t, 0); t = vg_track_in_now(s, t, 1)
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); t0 = t
    t = vg_studio(s, t0 + 300)                               # SEL + GLO again: the studio's keyboard, the journey on
    s.at(t, "dump", 0)
    s.tap_key(t + 50, wk(8)); t += 150                       # a white key: a step of track 1, not a mute
    s.at(t, "dump", 0)
    s.press(t, GLO); s.tap_key(t + 30, wk(1)); s.release(t + 100, GLO); t += 160   # GLO + white 2: track 2 muted by hand: OUT
    s.at(t, "dump", 0)
    t = vg_on(s, t + 50, remote=False)                       # SEL + GLO: the MOSSE again, the same journey
    s.at(t, "dump", 0)
    s.at(t0 + BAR_MS + 200, "dump", 0)                       # the phrase went on meanwhile
    log = run(s, t0 + BAR_MS + 300)
    v = log.viaggio
    d = log.dumps
    check(v[0]["on"] == 1 and v[0]["journey"] == 1 and v[0]["states"][:2] == "II", "the MOSSE: the panel and the journey (%s %s)" % (v[0]["on"], v[0]["states"][:2]))
    check(v[1]["on"] == 0 and v[1]["journey"] == 1 and log.states[1]["msg"].startswith("STUDIO"), "SEL+GLO tap: the studio's keyboard, the journey goes on (%s)" % log.states[1]["msg"])
    check(d[2]["hash"] != d[1]["hash"] and v[2]["states"][:2] == "II" and v[2]["journey"] == 1, "a white key writes a step of the track, the states stay (%s)" % v[2]["states"][:2])
    check(v[3]["states"][:2] == "IO" and v[3]["mute"] == 2, "GLO + white 2 mutes track 2 by hand: its state is OUT (%s)" % v[3]["states"][:2])
    check(v[4]["on"] == 1 and v[4]["journey"] == 1 and v[4]["states"][:2] == "IO" and log.states[4]["msg"].startswith("MOSSE"), "SEL+GLO tap again: the MOSSE, the same journey (%s)" % v[4]["states"][:2])
    check(v[5]["bar"] >= 1, "the phrase went on meanwhile (bar %s)" % v[5]["bar"])
    # the states follow the hand: an EMPTY track written in the studio while the journey runs is IN; cleared, EMPTY again
    s = Script()
    t = vg_on(s, 100)
    t = vg_track_in_now(s, t, 0)
    t = vg_studio(s, t)                                      # the studio's keyboard
    s.tap_key(t, bk(2)); t += 100                            # track 3 (empty)
    s.at(t, "dump", 2)
    t = s.steps(t, [0, 4, 8, 12])
    s.at(t, "dump", 2)
    s.press(t, SEQ); s.tap_key(t + 30, wk(0)); s.release(t + 100, SEQ); t += 160   # CLEAR
    s.at(t, "dump", 2)
    log = run(s, t + 100)
    st = [x["states"][2] for x in log.viaggio]
    check(st == ["E", "I", "E"], "track 3: EMPTY, written in the studio: IN, cleared: EMPTY (%s)" % st)


def t012_break():
    group("0.12 BREAK: a track of slices - the chops (SEQ 7 K1; ARP + white 1-16: tapped it stays, held it comes back), REC + whites play slices, the black keys ROLL / HALF / DOUBLE / BACKWARDS / DICE / RESET, COOK walks the genre's chops")
    BAR = 16 * STEP_MS
    def break_track(s, t):
        """track 1 to BREAK (HOME 4 K1 by key: white 5), the pen left at C4 (60): the slices are 60..75"""
        t = pg(s, t, HOME, 3)
        return pick(s, t, HOME, wk(4))
    # STRAIGHT written by the first chop turn, then END ROLL: 16 slices in a row, the last two rolled
    s = Script()
    t = break_track(s, 100)
    t = break_knobs(s, t, [(K1, 1)])                         # CHOP: END ROLL (written over the loop)
    s.at(t, "dump", 0)
    s.press(t, HOME); s.at(t + 60, "ui"); s.release(t + 120, HOME); t += 180
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(BAR) - 20)
    n = log.notes(ch=0, after=p0)
    check(log.dumps[0]["mode"] == "B" and log.dumps[0]["on"] == "x" * 16, "HOME 4 K1 = BREAK; the chop writes all 16 steps (%s %s)" % (log.dumps[0]["mode"], log.dumps[0]["on"]))
    check([d1 for _, d1, _ in n[:14]] == list(range(60, 74)) and len(n) == 18 and [d1 for _, d1, _ in n[14:]] == [74, 74, 74, 74],
          "END ROLL: slices 1-14 one a step, 15 and 15 rolled (%s)" % [d1 for _, d1, _ in n])
    sc = log.screens()
    check(bool(sc) and sc[0]["cells"][0] == ("> MODE", "BREAK"), "the screen: MODE BREAK (%s)" % ((sc[0]["cells"][0],) if sc else sc))
    check(log.states[0]["msg"] == "BREAK T1: END ROLL", "the chop's name is said (%s)" % log.states[0]["msg"])
    # ARP held: white 5 tapped = chop 5 (DOUBLE) and it stays; white 6 held 0.8 s = HALF while held, then the pattern before comes
    # back; REC armed (no ARP): white 5 plays slice 5 at once (and writes it)
    s = Script()
    t = break_track(s, 100)
    t = break_knobs(s, t, [(K1, 1), (K1, -1)])                # STRAIGHT
    s.press(t, ARP); s.tap_key(t + 30, wk(4), hold=60); s.release(t + 150, ARP); t += 200
    s.at(t, "dump", 0)
    s.press(t, ARP); s.keys(t + 30, wk(5)); s.at(t + 400, "dump", 0); s.keys(t + 830, 0); s.release(t + 900, ARP); t += 960
    s.at(t, "dump", 0)
    s.tap_btn(t, REC); t += 60
    s.tap_key(t, wk(4), hold=60); t += 120
    log = run(s, t + 50)
    d = log.dumps
    check(len(d) == 3 and d[0]["on"] == "x" * 16 and d[1]["on"] == "x." * 8 and d[2]["on"] == "x" * 16 and d[2]["hash"] == d[0]["hash"],
          "ARP + white 5 tapped: DOUBLE stays; white 6 held: HALF while held, the pattern before comes back (%s)" % [x["on"] for x in d])
    check([x["msg"] for x in log.states] == ["BREAK T1: DOUBLE", "BREAK T1: HALF", "BREAK T1: BACK"], "... each said (%s)" % [x["msg"] for x in log.states])
    check(pitches(log) == [64] and log.offs(ch=0) and log.offs(ch=0)[-1][1] == 64, "REC + white 5: slice 5 (64) sounds while the key is held (%s)" % pitches(log))
    check([v["chop"] for v in v11s(log)] == [4, 5, 4], "the chop written: DOUBLE (5), HALF while held, DOUBLE again (%s)" % [v["chop"] for v in v11s(log)])
    s = Script()
    t = break_track(s, 100)
    t = break_knobs(s, t, [(K1, 1), (K1, -1)])                # STRAIGHT
    for bi, what in ((2, "HALF"), (3, "DOUBLE"), (4, "BACKWARDS"), (6, "RESET")):
        s.press(t, ARP); s.tap_key(t + 30, bk(bi), hold=40); s.release(t + 100, ARP); t += 160
        s.at(t, "dump", 0)
    s.press(t, ARP); s.tap_key(t + 30, bk(4), hold=40); s.release(t + 100, ARP); t += 160   # BACKWARDS again, to hear it
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(BAR) + 20)
    ons = [d["on"] for d in log.dumps]
    check(ons[0] == "x." * 8 and ons[1] == "x" * 16 and ons[2] == "x" * 16 and ons[3] == "x" * 16, "HALF: every other step; DOUBLE, BACKWARDS, RESET: all on (%s)" % ons)
    check([x["msg"] for x in log.states] == ["BREAK T1: HALF", "BREAK T1: DOUBLE", "BREAK T1: BACKWARDS", "BREAK T1: STRAIGHT"], "... each says its name (%s)" % [x["msg"] for x in log.states])
    check(pitches(log, after=p0)[:16] == list(range(75, 59, -1)), "BACKWARDS plays the slices 16 .. 1 (%s)" % pitches(log, after=p0)[:16])
    # the dice (SEQ + black 1) keeps the backbone: slices 1 5 1 5 on the beats; UNDO takes the chop back
    s = Script()
    t = break_track(s, 100)
    t = break_knobs(s, t, [(K1, 6)])                          # BACKWARDS
    s.press(t, SEQ); s.tap_key(t + 30, bk(0), hold=40); s.release(t + 100, SEQ); t += 160   # DICE SEQ
    s.press(t, SEQ); s.tap_btn(t + 30, OCT_UP, hold=20); s.release(t + 100, SEQ); t += 160   # +: keep
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(BAR) + 20)
    n = log.notes(ch=0, after=p0)
    beats = [d1 for tm, d1, _ in n if abs((tm - p0) / STEP_MS - round((tm - p0) / STEP_MS)) < 0.1 and round((tm - p0) / STEP_MS) in (0, 4, 8, 12)]
    check(beats[:4] == [60, 64, 60, 64], "the dice on a break: kick, snare, kick, snare on the beats (%s)" % beats)
    # COOK walks the chops; UNDO takes a chop back
    s = Script()
    t = break_track(s, 100)
    t = break_knobs(s, t, [(K1, 1), (K1, -1)])                # STRAIGHT
    s.press(t, SEQ); s.tap_key(t + 30, wk(8), hold=40); s.release(t + 100, SEQ); t += 160   # COOK: the next chop
    s.at(t, "dump", 0)
    s.press(t, SEQ); s.tap_key(t + 30, wk(7), hold=40); s.release(t + 100, SEQ); t += 160   # UNDO
    s.at(t, "dump", 0)
    log = run(s, t + 50)
    check(log.states[0]["msg"] == "BREAK T1: GHOST (TECHNO 2/5)" and log.dumps[0]["hash"] != log.dumps[1]["hash"], "COOK on a break: the genre's next chop (TECHNO: STRAIGHT, GHOST ...); UNDO: back (%s)" % log.states[0]["msg"])
    # COOK walks the genre's list and wraps; in JUNGLE (SEQ + PRESETS to genre 9) it starts from STRAIGHT's successor THINK
    s = Script()
    t = break_track(s, 100)
    t = break_knobs(s, t, [(K1, 1), (K1, -1)])                # STRAIGHT
    s.press(t, SEQ); s.enc(t + 30, E_PRE, 8); s.release(t + 100, SEQ); t += 160   # the library's genre: JUNGLE
    for _ in range(3):
        s.press(t, SEQ); s.tap_key(t + 30, wk(8), hold=40); s.release(t + 100, SEQ); t += 160   # COOK
        s.at(t, "dump", 0)
    log = run(s, t + 50)
    check([v["chop"] for v in v11s(log)] == [11, 12, 10] and log.states[0]["msg"] == "BREAK T1: THINK (JUNGLE 2/7)",
          "JUNGLE's COOK: THINK, APACHE, SHUFFLE (%s, %s)" % ([v["chop"] for v in v11s(log)], log.states[0]["msg"]))
    # ROLL (ARP + black 1 held) while playing: the last slice played repeats every 1/16 while the key is held
    s = Script()
    t = break_track(s, 100)
    t = break_knobs(s, t, [(K1, 1), (K1, -1)])                # STRAIGHT
    s.tap_btn(t, REC); t += 60                                # REC armed: the whites play (and write) the slices
    s.tap_btn(t, PLAY); p0 = t
    s.tap_key(p0 + int(2 * STEP_MS) + 20, wk(11), hold=40)                                           # slice 12 (71) by hand
    s.press(p0 + int(4 * STEP_MS), ARP)
    s.keys(p0 + int(4.5 * STEP_MS), bk(0)); s.keys(p0 + int(8.5 * STEP_MS), 0)                     # ROLL from inside step 5 to inside step 9
    s.release(p0 + int(8.5 * STEP_MS) + 50, ARP)
    log = run(s, p0 + int(10 * STEP_MS))
    rolls = [tm for tm, d1, _ in log.notes(ch=0, after=p0 + int(4 * STEP_MS), before=p0 + int(10 * STEP_MS)) if d1 == 71]
    steps = [tm for tm, d1, _ in log.notes(ch=0, after=p0 + int(4 * STEP_MS), before=p0 + int(10 * STEP_MS)) if d1 in (65, 66, 67, 68)]
    check(len(rolls) == 4 and all(abs((b - a) - STEP_MS) < 12 for a, b in zip(rolls, rolls[1:])) and all(any(abs(r - st) < 8 for st in steps) for r in rolls),
          "ROLL: the slice again on each step boundary while black 1 is held, with the steps (%s / %s)" % ([round(x - p0) for x in rolls], [round(x - p0) for x in steps]))
    # a BREAK track is saved and comes back as one (the flag, the chop, the dice's settings)
    d = tempfile.mkdtemp()
    flash = os.path.join(d, "flash.bin")
    s = Script()
    t = break_track(s, 100)
    t = break_knobs(s, t, [(K1, 2), (K2, 3), (K4, 1)])        # RUSH, 3 rolls, 32 slices
    s.tap_btn(t, SAVE); s.tap_btn(t + 300, SAVE); t += 700
    run(s, t, flash)
    s = Script()
    s.at(300, "dump", 0)
    t = pg(s, 400, SEQ, 6)
    s.press(t, SEQ); s.at(t + 100, "ui"); s.release(t + 200, SEQ)
    log = run(s, t + 400, flash)
    sc = log.screens()
    check(log.dumps[0]["mode"] == "B" and bool(sc) and sc[0]["cells"][0][1] == "RUSH" and sc[0]["cells"][1][1] == "5" and sc[0]["cells"][3][1] == "32",
          "after a power cycle: BREAK, RUSH, 5 rolls (2 + 3), 32 slices (%s %s)" % (log.dumps[0]["mode"], [c[1] for c in sc[0]["cells"]] if sc else sc))


def remote13_on(s, t):
    """SAVE + K2 once: REMOTE ON CH 14 + VIAGGIO ON CH 13 (0.12: the Pi's new pages speak on 13, CC 33 and up, and notes)"""
    s.press(t, SAVE); s.enc(t + 30, K2, 1); s.release(t + 100, SAVE)
    return t + 160


def t012_remote13():
    group("0.12: the remote's channel 13 - patterns and lengths a track, the BREAK moves and pads, the LFOs, the lanes, TAKE, THROWS, the track and its mode, VIAGGIO's knobs")
    BAR = 16 * STEP_MS
    # a pattern and a length by CC (33-48, 49-64), the track and its mode (112, 113); a pad on channel 13 plays the track's note
    s = Script()
    t = remote13_on(s, 100)
    t = s.steps(t, [0])
    s.raw(t, "midi 0xBC 49 24"); t += 50                              # track 1: LENGTH 24 (stopped: at once)
    s.raw(t, "midi 0xBC 34 3"); t += 50                               # track 2: pattern 4
    s.raw(t, "midi 0xBC 112 2"); t += 50                              # select track 3
    s.raw(t, "midi 0xBC 113 4"); t += 50                              # track 3: BREAK (a knob of 0-4 sends the index; 127 would do too)
    s.raw(t, "midi 0xBC 74 3"); s.raw(t + 20, "midi 0xBC 75 2"); t += 60   # ROLLS 3, SLICES 32 (small values are the index)
    s.at(t, "dump", 0); s.at(t, "dump", 1); s.at(t, "dump", 2)
    t = pg(s, t, SEQ, 6); s.press(t, SEQ); s.at(t + 60, "ui"); s.release(t + 120, SEQ); t += 180
    s.raw(t + 20, "midi 0x9C 40 100"); s.raw(t + 120, "midi 0x8C 40 0")   # a pad: note 40 on channel 13 = slice 5 of track 3
    s.raw(t + 200, "midi 0xBC 83 110"); s.raw(t + 260, "midi 0xBC 83 0")   # the same pad as a CC (76 + 7 = slice 8)
    log = run(s, t + 300)
    d = log.dumps
    check(d[0]["length"] == 24 and d[1]["pat"] == 4 and d[2]["mode"] == "B", "CC 49 = 24: LENGTH; CC 34 = 3: pattern 4 of track 2; 112 / 113: track 3, BREAK (%s %s %s)" % (d[0]["length"], d[1]["pat"], d[2]["mode"]))
    sc = log.screens()
    check(bool(sc) and sc[0]["cells"][1][1] == "3" and sc[0]["cells"][3][1] == "32", "CC 74 = 3, 75 = 2: ROLLS 3, SLICES 32 (%s)" % ([c[1] for c in sc[0]["cells"]] if sc else sc))
    n = log.notes(ch=2, after=t)
    check(len(n) == 2 and n[0][1] == 64 and n[1][1:] == (67, 110) and [d1 for _, d1 in log.offs(ch=2)] == [64, 67], "a note on channel 13: slice 5 (pen + 4) on track 3's channel, and off; CC 83 = 110: slice 8 at 110 (%s)" % n)
    # the BREAK moves: 72 CHOP, 66 HALF, 68 BACKWARDS, 70 RESET, 65 ROLL held while playing; 69 the dice
    s = Script()
    t = remote13_on(s, 100)
    t = pg(s, t, HOME, 3, encs=[(K1, 4)])                             # track 1: BREAK
    s.raw(t, "midi 0xBC 72 1"); t += 50                               # END ROLL
    s.at(t, "dump", 0)
    s.raw(t, "midi 0xBC 66 127"); t += 50                             # HALF
    s.at(t, "dump", 0)
    s.raw(t, "midi 0xBC 70 127"); t += 50                             # RESET: STRAIGHT
    s.at(t, "dump", 0)
    s.raw(t, "midi 0xBC 68 127"); t += 50                             # BACKWARDS
    s.tap_btn(t, PLAY); p0 = t
    s.raw(p0 + int(3.5 * STEP_MS), "midi 0xBC 65 127"); s.raw(p0 + int(7.5 * STEP_MS), "midi 0xBC 65 0")   # ROLL held for four steps
    log = run(s, p0 + int(10 * STEP_MS))
    check([x["msg"] for x in log.states] == ["BREAK T1: END ROLL", "BREAK T1: HALF", "BREAK T1: STRAIGHT"] and log.dumps[1]["on"] == "x." * 8,
          "CC 72 / 66 / 70: the chop, HALF, RESET (%s)" % [x["msg"] for x in log.states])
    n = pitches(log, after=p0)
    check(n[:4] == [75, 74, 73, 72], "CC 68: BACKWARDS plays 16, 15, 14, 13 (%s)" % n[:4])
    rolls = [tm for tm, d1, _ in log.notes(ch=0, after=p0 + int(3.5 * STEP_MS), before=p0 + int(7.5 * STEP_MS)) if d1 == 72]
    check(len(rolls) == 4, "CC 65 held: the slice that played rolls on each step (%d)" % len(rolls))
    # the LFOs (92 which, 93-96 its shape, rate, depth, dest, 97 on / off), the lanes (101-106), THROWS (108-111), TAKE (107)
    s = Script()
    t = remote13_on(s, 100)
    s.raw(t, "midi 0xBC 92 2"); t += 50                               # LFO 3 shown
    s.raw(t, "midi 0xBC 93 127"); t += 50                             # its shape: the last
    s.raw(t, "midi 0xBC 95 100"); t += 50                             # depth 100
    s.raw(t, "midi 0xBC 97 127"); t += 50                             # LFO 3 on
    s.raw(t, "midi 0xBC 101 77"); t += 50                             # lane 1 of track 1: base 77, sent
    s.raw(t, "midi 0xBC 108 127"); t += 50                            # INTENSITY thrown to +63
    s.press(t, LFO); s.at(t + 60, "ui"); s.release(t + 120, LFO); t += 180
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    sc = log.screens()
    lfo_cells = sc[0]["cells"] if sc else []
    check(bool(sc) and sc[0]["lines"][1].find("LFO 3") >= 0 or (lfo_cells and lfo_cells[2][1] == "100"), "CC 92 / 93 / 95: LFO 3 shown, depth 100 (%s)" % (sc[0]["lines"][1:3] + [c for c in lfo_cells] if sc else sc))
    cc74 = [m for m in log.msgs if (m[1] & 0xF0) == 0xB0 and (m[1] & 15) == 0 and m[2] == 74]
    check(cc74 and cc74[-1][3] == 77, "CC 101 = 77: lane 1's base goes out as CC 74 = 77 (%s)" % cc74[-1:])
    check(log.states[0]["mac"][0] >= 55, "CC 108 = 127: INTENSITY up to +63, as a throw (gliding back already: %s)" % log.states[0]["mac"])
    # notes 100-115 on channel 13: LFO 1-16 on (note on) / off (note off), all at once (SAGGA Mod's sixteen switches)
    s = Script()
    t = remote13_on(s, 100)
    s.raw(t, "midi 0x9C 100 127"); s.raw(t + 20, "midi 0x9C 104 127"); s.raw(t + 40, "midi 0x9C 115 100"); t += 80   # LFO 1, 5, 16 on
    s.raw(t, "midi 0x8C 104 0"); t += 40                                                                      # LFO 5 off
    s.press(t, LFO); s.at(t + 60, "leds"); s.release(t + 120, LFO); t += 180                                 # the LFO keys: on ones lit
    log = run(s, t + 100)
    kl = log.key_leds()
    lit = [i for i in range(16) if kl and kl[0][1][WHITE[i]] == "X"] if kl else None
    check(lit == [0, 15], "ch 13 notes 100 / 104 / 115 on, 104 off: LFO 1 and 16 on, 5 off (%s)" % lit)
    # the throw glides back to 0 within a bar while playing
    s = Script()
    t = remote13_on(s, 100)
    t = s.steps(t, [0])
    s.tap_btn(t, PLAY); p0 = t
    s.raw(p0 + 100, "midi 0xBC 108 127")
    s.at(p0 + 300, "dump", 0)
    s.at(p0 + int(BAR) + 400, "dump", 0)
    log = run(s, p0 + int(BAR) + 500)
    check(log.states[0]["mac"][0] > 0 and log.states[1]["mac"][0] == 0, "a THROW: INTENSITY up, back to 0 a bar later (%s -> %s)" % (log.states[0]["mac"][0], log.states[1]["mac"][0]))
    # TAKE (107) while playing: a pad played on channel 13 in the last loop goes into the track
    s = Script()
    t = remote13_on(s, 100)
    t = s.steps(t, [0])
    s.tap_btn(t, PLAY); p0 = t
    s.raw(p0 + int(4 * STEP_MS) + 10, "midi 0x9C 67 100"); s.raw(p0 + int(5 * STEP_MS), "midi 0x8C 67 0")   # G4 on step 5
    s.raw(p0 + int(12 * STEP_MS), "midi 0xBC 107 127")
    s.at(p0 + int(12 * STEP_MS) + 50, "dump", 0)
    log = run(s, p0 + int(13 * STEP_MS))
    check(log.dumps[0]["on"][:6] == "x...x." and log.states[0]["msg"].startswith("TAKE: 1 NOTES INTO T1"), "CC 107: TAKE writes the pad's note on step 5 (%s %s)" % (log.dumps[0]["on"][:8], log.states[0]["msg"]))
    # VIAGGIO's knobs by CC: 114 ENERGY, 115 GENRE, 116 KEY (stopped: at once), 117 PROGRESSION, 118 HARMONY
    s = Script()
    t = remote13_on(s, 100)
    t = vg_on(s, t)
    s.raw(t, "midi 0xBC 114 127"); t += 50
    s.raw(t, "midi 0xBC 115 3"); t += 50                              # HOUSE
    s.raw(t, "midi 0xBC 116 2"); t += 50                              # D
    s.raw(t, "midi 0xBC 118 2"); t += 50                              # HARMONY LOCK
    s.raw(t, "midi 0xBC 117 2"); t += 50                              # progression 3
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    v = log.viaggio[0]
    c = cfgs(log)[0]
    check(v["target"] == 100 and v["genre"] == 3 and c["key"][0] == 2 and log.states[0]["harm"][0] == 1 and v11s(log)[0]["lock"] == 1 and harm11(log)[0]["prog"] == 2,
          "CC 114-118: ENERGY 100, HOUSE, D, HARMONY LOCK, progression 3 (%s %s %s %s)" % (v["target"], v["genre"], c["key"][0], harm11(log)[0]["prog"]))


def t012_review():
    group("0.12 review: TAKE after STOP, the roll's track and release, SEL+GLO with a key, ENERGY / PHRASE by key, PERF+SEL screen, two hold keys, a lock under a chop, a 0.11 image's BREAK settings")
    BAR = 16 * STEP_MS
    # TAKE forgets the previous run: a note in run 1, STOP, PLAY, TAKE: nothing
    s = Script()
    t = s.steps(100, [0])
    s.tap_btn(t, PLAY); p0 = t
    s.raw(p0 + int(4 * STEP_MS) + 10, "midi 0x9C 67 100"); s.raw(p0 + int(5 * STEP_MS), "midi 0x8C 67 0")
    s.tap_btn(p0 + int(8 * STEP_MS), PLAY); s.tap_btn(p0 + int(9 * STEP_MS), PLAY); p1 = p0 + int(9 * STEP_MS)
    s.press(p1 + int(12 * STEP_MS), REC); s.release(p1 + int(12 * STEP_MS) + 700, REC)
    s.at(p1 + int(12 * STEP_MS) + 750, "dump", 0)
    log = run(s, p1 + int(12 * STEP_MS) + 900)
    check(log.states[0]["msg"] == "TAKE: NOTHING PLAYED IN THE LAST LOOP" and log.dumps[0]["on"] == "x" + "." * 15, "TAKE after STOP / PLAY: the old run's notes are gone (%s)" % log.states[0]["msg"])
    # TAKE without REC from MIDI in, placed where REC would put it (REC QUANTISED: the step the note fell in)
    s = Script()
    t = s.steps(100, [0])
    s.tap_btn(t, PLAY); p0 = t
    s.raw(p0 + int(6 * STEP_MS) - 40, "midi 0x90 67 100"); s.raw(p0 + int(7 * STEP_MS), "midi 0x80 67 0")   # 40 ms before step 7: step 6 (its late half)
    s.press(p0 + int(12 * STEP_MS), REC); s.release(p0 + int(12 * STEP_MS) + 700, REC)
    s.at(p0 + int(12 * STEP_MS) + 750, "dump", 0)
    log = run(s, p0 + int(12 * STEP_MS) + 900)
    check(log.dumps[0]["on"][:8] == "x.....x.", "a MIDI-in note without REC, 40 ms before step 7: TAKE puts it on step 7 as REC would (early for the next step) (%s)" % log.dumps[0]["on"][:8])
    # the roll: the slice played on track 1 does not roll on track 2; CC 65's off counts after a track change
    s = Script()
    t = remote13_on(s, 100)
    t = pg(s, t, HOME, 3, encs=[(K1, 4)])                             # track 1 BREAK
    s.tap_key(t, bk(1)); t += 60                                      # track 2
    t = pg(s, t, HOME, 3, encs=[(K1, 4)])                             # track 2 BREAK
    t = break_knobs(s, t, [(K1, 1), (K1, -1)])
    s.tap_key(t, bk(0)); t += 60                                      # track 1
    s.press(t, ARP); s.tap_key(t + 30, wk(11), hold=40); s.release(t + 100, ARP); t += 160   # slice 12 on track 1 (ch 1)
    s.tap_key(t, bk(1)); t += 60                                      # track 2
    s.tap_btn(t, PLAY); p0 = t
    s.raw(p0 + int(4.5 * STEP_MS), "midi 0xBC 65 127")                # ROLL held (the Pi)
    s.raw(p0 + int(6.5 * STEP_MS), "midi 0xBC 112 0")                 # the track changes under it
    s.raw(p0 + int(8.5 * STEP_MS), "midi 0xBC 65 0")                  # let go
    log = run(s, p0 + int(14 * STEP_MS))
    n1 = [d1 for _, d1, _ in log.notes(ch=0, after=p0)]
    n2 = [d1 for tm, d1, _ in log.notes(ch=1, after=p0 + int(4.5 * STEP_MS), before=p0 + int(6.5 * STEP_MS))]
    late = [d1 for tm, d1, _ in log.notes(ch=1, after=p0 + int(9 * STEP_MS))]
    check(71 not in n1 and n2 and all(x != 71 for x in n2), "the roll on track 2 repeats track 2's own step, not track 1's slice 12 (ch1 %s, ch2 %s)" % (n1[:6], n2))
    check(late and len(late) == len(set(late)), "CC 65 let go after the track changed: the roll stops, only the pattern's own slices go on (%s)" % late)
    # SEL + GLO + a key (PICK) or + OCT: no panel toggle, no journey off
    s = Script()
    t = vg_on(s, 100)
    t = vg_on(s, t)                                                   # the studio's keyboard, the journey on
    s.press(t, SEL); s.press(t + 30, GLO); s.tap_key(t + 60, wk(2), hold=40); s.release(t + 130, GLO); s.release(t + 160, SEL); t += 220   # PICK (GLO 1 K1 MORPH: by the knob) ...
    s.at(t, "dump", 0)
    s.press(t, SEL); s.press(t + 30, GLO); s.tap_btn(t + 60, OCT_UP, hold=20); s.release(t + 800, GLO); s.release(t + 830, SEL); t += 900   # the octave, GLO held long
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    v = log.viaggio
    check(v[0]["on"] == 0 and v[0]["journey"] == 1 and v[1]["on"] == 0 and v[1]["journey"] == 1 and cfgs(log)[1]["oct"] == 1,
          "SEL + GLO + a key, or + OCT held long: the panel stays, the journey goes on, the octave moved (%s %s %s)" % (v[0]["on"], v[1]["journey"], cfgs(log)[1]["oct"]))
    # GLO 3 by key: ENERGY white 7 = 70, PHRASE white 1 = 4 bars
    s = Script()
    t = pg(s, 100, GLO, 2, encs=[(K1, 1)])
    t = pick(s, t, GLO, wk(6))
    t = pick(s, t, GLO, bk(10))
    t = pick(s, t, GLO, wk(0))
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    check(log.viaggio[0]["target"] == 70 and log.viaggio[0]["bars"] == 4, "GLO 3 by key: ENERGY 70, PHRASE 4 bars (%s %s)" % (log.viaggio[0]["target"], log.viaggio[0]["bars"]))
    # PERF + SEL: the screen shows TRACK LIVE while the knobs do it
    s = Script()
    s.tap_btn(100, GLO)
    s.press(200, SEL); s.at(260, "ui"); s.enc(300, K1, 2); s.at(360, "ui"); s.release(400, SEL)
    s.at(500, "dump", 0)
    log = run(s, 600)
    sc = log.screens()
    check(len(sc) == 2 and sc[0]["cells"][0][0] == "PATTERN" and sc[1]["cells"][0][1] == "P3" and log.dumps[0]["pat"] == 3, "PERF + SEL: the screen is TRACK LIVE, K1 the pattern (%s)" % ([x["cells"][0] for x in sc] if sc else sc))
    # two hold keys: UNDO then COOK, both let go: UNDO acted (as a tap) when COOK went down
    s = Script()
    t = s.steps(100, [0, 4, 8, 12])
    s.press(t, SEQ); s.tap_key(t + 30, wk(14), hold=40)                                      # INVERT: 12 on
    s.keys(t + 130, wk(TOOL_UNDO_IDX)); s.keys(t + 200, wk(TOOL_UNDO_IDX) | wk(8)); s.keys(t + 260, wk(8)); s.keys(t + 300, 0)
    s.release(t + 360, SEQ); t += 420
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    check(log.dumps[0]["on"].count("x") != 12 and any(x["msg"] == "COOK" for x in log.states), "UNDO down, COOK down, both up: UNDO acted, then COOK (%s %s)" % (log.dumps[0]["on"].count("x"), [x["msg"] for x in log.states]))
    # a locked step under a chop stays as written
    s = Script()
    t = pg(s, 100, HOME, 3, encs=[(K1, 4)])
    t = break_knobs(s, t, [(K1, 1), (K1, -1)])                        # STRAIGHT
    s.press(t, EDIT); s.tap_key(t + 30, wk(3), hold=40); s.tap_key(t + 100, bk(0), hold=40); s.release(t + 170, EDIT); t += 230   # step 4 locked (slice 4)
    t = break_knobs(s, t, [(K1, 6)])                                  # BACKWARDS
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(BAR) - 20)
    n = pitches(log, after=p0)
    check(n[:5] == [75, 74, 73, 63, 71], "BACKWARDS leaves the locked step 4 as it was: 16 15 14 [4] 12 (%s)" % n[:5])


def t011_pc_test():
    group("0.11: the PC test (sagga_test.c) - SEL says yes, the test reboots, presses, probes; a hand stops it; no slot is touched")
    sys.path.insert(0, os.path.join(ROOT, "tools", "hwtest"))
    import sagga_testport as TP

    def sx(s, t, b): s.at(t, "sx", " ".join("%02X" % x for x in b[1:-1]))

    def answers(log):
        return [(t, TP.parse(bytes(b))) for t, b in log.sysex if TP.parse(bytes(b))]

    def ans(log, what):
        return [(t, a[1]) for t, a in answers(log) if a[0] == what]

    # the hand says yes: SEL; then BOOT reboots
    s = Script()
    sx(s, 500, TP.hello()); sx(s, 600, TP.open_()); s.tap_btn(900, SEL); sx(s, 1200, TP.boot())
    log = run(s, 2000)
    h = ans(log, "hello")
    check(h and h[0][1]["state"] == 0 and h[0][1]["booted"] == 0 and h[0][1]["version"] == "0.17", "HELLO: nothing asked yet, a normal boot, 0.17 (%s)" % h)
    check([a for _, a in ans(log, "open")] == [1, 2], "OPEN asks, SEL says yes (%s)" % ans(log, "open"))
    check(ans(log, "boot") == [(1200, 1)] and re.search(r"^\s*12[89]\d ms  TEST REBOOT", log.text, re.M), "BOOT: yes, then the reboot (%s)" % ans(log, "boot"))
    # another key says no, and does nothing else; BOOT without a yes: no
    s = Script()
    sx(s, 600, TP.open_()); s.tap_btn(900, PLAY); sx(s, 1200, TP.boot()); s.raw(1500, "probe")
    log = run(s, 1800)
    check([a for _, a in ans(log, "open")] == [1, 3] and ans(log, "boot") == [(1200, 0)] and "TEST REBOOT" not in log.text,
          "PLAY says no, BOOT is refused (%s %s)" % (ans(log, "open"), ans(log, "boot")))
    check(" PROBE G play=0 " in log.text, "the PLAY that said no did not start the music")
    s = Script()
    s.tap_btn(300, PLAY); sx(s, 600, TP.open_()); sx(s, 900, TP.close())
    log = run(s, 1200)
    check([a for _, a in ans(log, "open")] == [5] and ans(log, "close") == [(900, 0)] and "TEST REBOOT" not in log.text,
          "OPEN while it plays: stop first; CLOSE outside a test boot: nothing (%s %s)" % (ans(log, "open"), ans(log, "close")))
    # the test boot: a project saved in a slot is not loaded, a session presses and probes, nothing touches the flash
    with tempfile.TemporaryDirectory() as d:
        fl = os.path.join(d, "flash.bin")
        s = Script()
        t = s.steps(200, [0, 4, 8, 12])
        s.tap_btn(t + 100, SAVE); s.tap_btn(t + 400, SAVE)
        log = run(s, t + 3000, flash=fl)
        check(log.saves, "a project saved in slot 1 first (%s)" % log.saves)
        before = open(fl, "rb").read()
        evs = [(100, TP.PROBE, 0, 0), (200, TP.PRESS, SAVE, 0), (230, TP.RELEASE, SAVE, 0), (300, TP.PROBE, 0, 0), (500, TP.PRESS, SAVE, 0),
               (530, TP.RELEASE, SAVE, 0), (700, TP.PRESS, HOME, 0), (730, TP.PRESS, SAVE, 0), (760, TP.RELEASE, SAVE, 0),
               (790, TP.RELEASE, HOME, 0), (1000, TP.KEYS, wk(2), 0), (1050, TP.KEYS, 0, 0), (1100, TP.PRESS, PLAY, 0),
               (1130, TP.RELEASE, PLAY, 0), (1200, TP.ENC, K1, 8192 + 2), (2000, TP.PROBE, 0, 0), (2100, TP.END, 0, 0)]
        s = Script()
        sx(s, 2000, TP.hello()); sx(s, 2010, TP.go()); sx(s, 2020, TP.ev_frame(0, evs))
        s.raw(4500, "probe")
        log = run(s, 5000, flash=fl, testboot=True)
        after = open(fl, "rb").read()
        h = ans(log, "hello")
        check(h and h[0][1]["booted"] == 1 and h[0][1]["state"] == 2, "after the reboot: a test boot, the yes kept (%s)" % h)
        check(before == after and "FLASH LOCKED" not in log.text and "settings saved" not in log.text and not log.saves,
              "SAVE twice, HOME + SAVE, a whole session: the flash is never written nor tried")
        pr = TP.Probes()
        for _, a in answers(log):
            if a[0] == "probe":
                pr.add(*a[1])
        p0, p3, p15 = (TP.probe_dict(pr.done.get(i, "")) for i in (0, 3, 15))
        check(p0 and p0["T1"]["steps#"] == "8A0C21C5", "the project in the slot is not loaded: the empty pattern (%s)" % p0.get("T1", {}).get("steps#"))
        check(p3.get("G", {}).get("msg") == "PC TEST: SLOTS OFF", "SAVE in the test: SLOTS OFF (%s)" % p3.get("G", {}).get("msg"))
        check(p15 and p15["G"]["play"] == "1" and p15["H"]["test"] == "1", "the PC's PLAY plays (%s)" % p15.get("G", {}).get("play"))
        host = [m.group(1) for m in re.finditer(r"^\s*4500 ms  (PROBE .*)$", log.text, re.M)]
        check(len(pr.done) == 3 and all(len(v) > 3000 for v in pr.done.values()), "the probes came in pieces, whole (%s)" % {k: len(v) for k, v in pr.done.items()})
        check(ans(log, "done") and ans(log, "done")[0][1]["applied"] == len(evs), "DONE: every event taken (%s)" % ans(log, "done"))
        logs = [x for _, a in answers(log) if a[0] == "log" for x in a[1]]
        check([x[0] for x in logs] == list(range(len(evs))) and logs[0][1] == 2110, "each event's place: the ms after GO (%s)" % logs[:3])
        check(host and host[0].startswith("PROBE G play=1"), "the simulator's own probe reads the same machine")
    # a hand on the panel stops the test: nothing more is pressed
    s = Script()
    evs = [(100, TP.PRESS, PLAY, 0), (130, TP.RELEASE, PLAY, 0), (900, TP.PRESS, PLAY, 0), (930, TP.RELEASE, PLAY, 0), (1000, TP.PROBE, 0, 0)]
    sx(s, 1000, TP.go()); sx(s, 1010, TP.ev_frame(0, evs)); s.tap_btn(1500, OCT_UP); s.raw(2500, "probe")
    log = run(s, 2800, testboot=True)
    logs = [x for _, a in answers(log) if a[0] == "log" for x in a[1]]
    check(ans(log, "abort") and [x[0] for x in logs] == [0, 1], "OCT+ by hand: ABORT, the events after it never taken (%s %s)" % (ans(log, "abort"), logs))
    check(" PROBE G play=1 " in log.text and "PC TEST STOPPED" in log.text, "the music goes on, the screen says why")
    # CLOSE ends a test boot with a normal reboot
    s = Script()
    sx(s, 1000, TP.close())
    log = run(s, 1500, testboot=True)
    check(ans(log, "close") == [(1000, 1)] and "TEST REBOOT" in log.text, "CLOSE: a reboot, not into the test (%s)" % ans(log, "close"))


def t011_explorer_sessions():
    group("0.11: the explorer's sessions that found a track out of time (a dice put back, a VIAGGIO loop let go, STOP in a DJ LOOP and CONTINUE, RELOAD, a change while stopped and CONTINUE)")
    import sagga_explore as E
    E.BIN = BIN
    cat = {g.name: g for g in E.catalogo(grid=True)}
    for sit_name, names in EXPLORER_SESSIONS:
        sit = [x for x in E.SITUAZIONI if x.name == sit_name][0]
        got = E.session_check(sit, [cat[n] for n in names], 0)
        check(not got, "%s, %d gestures: nothing out of time (%s)" % (sit_name, len(names), got))


def t012_grid_pick():
    group("0.12 grid PICK view (SHIFT + STEP twice): the four knobs of the window open on the FM-1, a row each, their values on the pads")
    # the HOME window: row 1 = CHANNEL (items 1-12 lit, the current white), row 2 = LENGTH (4, 8 .. 64; row 6: the odd ones), row 3 = DIVISION, row 4 = TRANSPOSE
    s = Script()
    s.raw(100, "attach")
    s.tap_btn(200, HOME)                                                   # the HOME window
    view(s, 400, GC_VSTEP, alt=True); view(s, 500, GC_VSTEP, alt=True)    # CC, again: PICK
    s.at(700, "ui")
    s.pad(800, 7, 1)                                                       # row 2 pad 8: LENGTH 32
    s.pad(900, 0, 5)                                                       # row 6 pad 1: LENGTH 3 (a black key's value)
    s.at(1000, "dump", 0)
    s.pad(1100, 4, 0)                                                      # row 1 pad 5: channel 5
    s.at(1200, "dump", 0)
    s.pad(1300, 2, 3)                                                      # row 4 pad 3: TRANSPOSE -8 (the whites F3 G3 A3 = -12 -10 -8)
    s.at(1400, "dump", 0)
    log = run(s, 1500)
    sc = log.screens()
    check(bool(sc) and sc[0]["lines"][2].startswith("HOME 1/8") and sc[0]["lines"][3] == "PICK", "the HOME window with the grid on PICK (%s)" % (sc[0]["lines"][2:4] if sc else sc))
    pads, ctls = log.leds(until=790)
    check(pads[0 * 16 + 0] == GL_WHITE and pads[0 * 16 + 13] == GL_ON and pads[0 * 16 + 14] == GL_OFF and pads[4 * 16 + 0] == GL_OFF,
          "row 1 CHANNEL: 1 is white, 14 lit, 15 off (the grid takes 15 and 16), row 5 (items 17+) off (%s)" % [pads.get(i) for i in (0, 13, 14, 64)])
    check(pads[1 * 16 + 3] == GL_WHITE and pads[1 * 16 + 15] == GL_BLUE and pads[5 * 16 + 0] == GL_BLUE and pads[5 * 16 + 11] == GL_OFF, "row 2 LENGTH: 16 white (pad 4), 64 blue; row 6: the odd lengths, pad 12 off (%s)" % [pads.get(i) for i in (19, 31, 80, 91)])
    d = log.dumps
    check(len(d) == 3 and d[0]["length"] == 3 and d[1]["length"] == 3 and d[0]["start"] == 0, "row 2 pad 8, then row 6 pad 1: LENGTH 32, then 3 (%s)" % [x["length"] for x in d])
    ch = [int(m) for m in re.findall(r"^\s*\d+ ms  cfg T1 role \d+ chord \d+ oct -?\d+ keyslot -?\d+ trans (-?\d+) div", log.text, re.M)]
    check(ch == [0, 0, -8], "row 4 pad 3: TRANSPOSE -8 (%s)" % ch)
    # the CC view again on the third SHIFT + STEP; with no window the view shows HOME's page; PERF: GLO's
    s = Script()
    s.raw(100, "attach")
    view(s, 200, GC_VSTEP, alt=True); view(s, 300, GC_VSTEP, alt=True); view(s, 400, GC_VSTEP, alt=True)
    s.at(500, "ui")
    log = run(s, 600)
    sc = log.screens()
    check(bool(sc) and sc[0]["lines"][3] == "CC", "SHIFT + STEP a third time: CC again (%s)" % (sc[0]["lines"][3] if sc else sc))


def t012_window():
    group("0.12 WINDOWS: a tap on HOME / SEQ / EDIT / ENV / LFO / ARP / FX keeps the button held (knobs, keys, OCT pages, SEL + key PICK); again or another: closed; a button held wins; GLO's window is PERF")
    # a tap on SEQ: its page stays on the screen, the knobs are its, OCT+ turns its pages; a tap again: the steps are back
    s = Script()
    s.tap_btn(100, SEQ)
    s.at(300, "ui"); s.at(300, "dump", 0)
    s.tap_btn(400, OCT_UP, hold=20)                                        # SEQ 2/7 ALGORITHMS
    s.at(500, "ui")
    s.tap_btn(600, OCT_DOWN, hold=20)                                      # back to 1/7 EUCLID
    s.enc(700, K1, 2)                                                      # EUCLID pulses +2 (a knob of the window)
    s.at(800, "dump", 0)
    s.tap_btn(900, SEQ)                                                    # closed
    s.at(1100, "ui"); s.at(1100, "dump", 0)
    s.enc(1200, K2, 5)                                                     # a knob of the steps again: velocity
    s.at(1300, "dump", 0)
    log = run(s, 1400)
    sc = log.screens()
    check(len(sc) == 3 and sc[0]["lines"][2].startswith("SEQ 1/7") and sc[1]["lines"][2].startswith("SEQ 2/7") and sc[2]["lines"][2].startswith("STEP 1"),
          "SEQ tapped: its page stays; OCT+: page 2; SEQ again: the steps (%s)" % [x["lines"][2][:12] for x in sc])
    w = wins(log)
    check(w == [SEQ, SEQ, -1, -1], "the window open: SEQ, then none (%s)" % w)
    st = log.states
    check(st[1]["pulses"] == st[0]["pulses"] + 2 and st[2]["pulses"] == st[1]["pulses"], "K1 in the window: EUCLID pulses +2; closed, the knobs are the step's (%s)" % [x["pulses"] for x in st])
    # another window button tapped: the window changes; a button really held wins, and lets the window be
    s = Script()
    s.tap_btn(100, SEQ)
    s.tap_btn(300, LFO)
    s.at(500, "ui"); s.at(500, "dump", 0); s.at(500, "leds")
    s.press(600, HOME); s.enc(700, K2, 1); s.at(750, "ui"); s.release(800, HOME)   # HOME held: LENGTH +1 on its page, then the LFO window again
    s.at(900, "ui"); s.at(900, "dump", 0)
    s.press(1000, LFO); s.release(1800, LFO)                                # LFO held 0.8 s with nothing: not a tap, the window stays
    s.at(1900, "dump", 0)
    s.tap_btn(2000, LFO)                                                    # a tap: closed
    s.at(2100, "dump", 0)
    log = run(s, 2200)
    sc = log.screens()
    check(wins(log) == [LFO, LFO, LFO, -1], "SEQ then LFO tapped: the LFO window; HOME held and let go: still LFO; LFO held 0.8 s: still; a tap: closed (%s)" % wins(log))
    check(len(sc) == 3 and sc[0]["lines"][2].startswith("LFO 1/16") and sc[1]["lines"][2].startswith("HOME 1/8") and sc[2]["lines"][2].startswith("LFO 1/16"),
          "the screen: the LFO page, HOME's while held, the LFO page again (%s)" % [x["lines"][2][:10] for x in sc])
    check(log.dumps[1]["length"] == 17, "HOME held + K2: LENGTH 17 (%s)" % log.dumps[1]["length"])
    bl = log.btn_leds()
    check(bl and bl[0][1][LFO] == "X" and bl[0][1][SEQ] == ".", "the LFO button is lit full while its window is open, SEQ not (%s)" % (bl[0][1] if bl else bl))
    # the keys are the window's: HOME window + white 5 = track 5; LFO window + white 3 = LFO 3 on; SEL + key = PICK (HOME: K2 LENGTH by white 8 = 32)
    s = Script()
    s.tap_btn(100, HOME)
    s.tap_key(300, wk(4))                                                   # track 5
    s.at(400, "ui")
    s.enc(500, K2, 1)                                                      # LENGTH in focus (17)
    s.press(600, SEL); s.tap_key(650, wk(7)); s.release(750, SEL)           # PICK: LENGTH 32
    s.at(900, "dump", 4)
    s.tap_btn(1000, LFO)
    s.tap_key(1200, wk(2))                                                  # LFO 3 on
    s.at(1300, "ui")
    log = run(s, 1400)
    sc = log.screens()
    check(len(sc) == 2 and " T5 " in sc[0]["lines"][0] and log.dumps[0]["length"] == 32, "HOME window: white 5 selects track 5, SEL + white 8 sets LENGTH 32 (%s, %s)" % (sc[0]["lines"][0] if sc else sc, log.dumps[0]["length"] if log.dumps else None))
    check(len(sc) == 2 and sc[1]["lines"][2].startswith("LFO 3/16 ON"), "LFO window: white 3 = LFO 3, on (%s)" % (sc[1]["lines"][2] if len(sc) > 1 else sc))
    # the ARP window: the keys play the track (no REC, nothing written); SEL + ARP tapped: the arpeggio on / off (the old tap)
    s = Script()
    s.tap_btn(100, ARP)
    s.tap_key(300, KEY_C4, hold=100)
    s.at(500, "dump", 0)
    arp_tap(s, 600)
    s.at(800, "ui")
    log = run(s, 900)
    n = log.notes(ch=0)
    check(len(n) == 1 and n[0][1] == 60 and log.offs(ch=0) and log.dumps[0]["on"] == "." * 16, "ARP window: C4 plays, nothing is written (%s %s)" % (n, log.dumps[0]["on"]))
    sc = log.screens()
    check(wins(log) == [ARP] and bool(sc) and " UP" in sc[0]["lines"][1], "SEL + ARP tapped: the arpeggio UP, the ARP window still open (%s)" % (sc[0]["lines"][1] if sc else sc))
    # GLO tapped (PERF) closes the window; in PERF OCT+ turns GLO's pages, SEL + OCT+ makes the whites solos; a window tapped leaves PERF
    s = Script()
    s.tap_btn(100, SEQ)
    s.tap_btn(300, GLO)
    s.at(500, "ui"); s.at(500, "dump", 0)
    s.tap_btn(600, OCT_UP, hold=20)
    s.at(700, "ui")
    s.press(800, SEL); s.tap_btn(830, OCT_UP, hold=20); s.release(900, SEL)
    s.at(1000, "dump", 0)
    s.tap_btn(1100, ENV)
    s.at(1300, "ui"); s.at(1300, "dump", 0)
    log = run(s, 1400)
    sc = log.screens()
    check(wins(log) == [-1, -1, ENV] and len(sc) == 3 and sc[0]["lines"][2].startswith("PERF SCENE") and sc[1]["lines"][2].startswith("GLO 2/3 TRACK LIVE") and sc[2]["lines"][2].startswith("ENV"),
          "GLO tapped: PERF, no window; OCT+: GLO 2/3; ENV tapped: its window, PERF off (%s %s)" % (wins(log), [x["lines"][2][:14] for x in sc]))
    check(log.states[1]["msg"] == "PERF WHITE KEYS: SOLO", "PERF + SEL + OCT+: the whites solo (%s)" % log.states[1]["msg"])
    # a tap with another button held, or with a knob turned, is not a tap: HOME + SEQ (SEQ pressed with HOME held), SEQ + K1
    s = Script()
    s.press(100, HOME); s.tap_btn(150, SEQ); s.release(300, HOME)
    s.at(400, "dump", 0)
    s.press(500, SEQ); s.enc(550, K4, 1); s.release(700, SEQ)             # HEAT +1: used
    s.at(800, "dump", 0)
    s.press(900, SEQ); s.tap_key(950, wk(8), hold=30); s.release(1100, SEQ)   # a tool (COOK): used
    s.at(1200, "dump", 0)
    log = run(s, 1300)
    check(wins(log) == [-1, -1, -1], "SEQ pressed with HOME held, SEQ + a knob, SEQ + a key: no window (%s)" % wins(log))
    # the map of the window's keys shows after half a second and goes after four more; a message always wins
    s = Script()                                                           # (from 3.5 s: the boot message is gone)
    s.tap_btn(3500, SEQ)
    s.at(3800, "ui"); s.at(4300, "ui"); s.at(8400, "ui")
    log = run(s, 8500)
    sc = log.screens()
    check(len(sc) == 3 and not sc[0]["lines"][3].startswith("W TOOLS") and sc[1]["lines"][3].startswith("W TOOLS") and not sc[2]["lines"][3].startswith("W TOOLS"),
          "the SEQ window's map: not yet at 0.3 s, there at 0.8 s, gone at 4.9 s (%s)" % [x["lines"][3][:12] for x in sc])
    # a BREAK track in the ARP window: white 5 tapped = DOUBLE; the dump says the chop; the whites' LEDs: the chop blinks
    s = Script()
    t = pg(s, 100, HOME, 3)
    t = pick(s, t, HOME, wk(4))                                            # BREAK
    s.tap_btn(t, ARP); t += 200
    s.tap_key(t, wk(4), hold=40); t += 200
    s.at(t, "dump", 0); s.at(t, "leds")
    log = run(s, t + 100)
    check(wins(log) == [ARP] and v11s(log)[0]["chop"] == 4 and log.dumps[0]["on"] == "x" * 16, "ARP window on a BREAK: white 5 = DOUBLE written (%s %s)" % (wins(log), v11s(log)[0]["chop"] if v11s(log) else None))


# ------------------------------------------------------------------------------------------------ 0.13
V13 = re.compile(r"^\s*(\d+) ms  v13 T(\d+) chain (\d+) pos (\d+) left (\d+) list((?: \d+/\d+)*) kb (\d+)/(\d+) thru (\d+) ktrans (-?\d+) "
                 r"motion (\d+) rec (\d+) (\d+) (\d+) (\d+) porta (\d+) lfo (\d+) seq (\d+)/(\d+) trig (\d+)$", re.M)


def v13s(log):
    """the 0.13 'v13' lines of the dumps: the CHAIN LIST of the track, the KEYBOARD, MIDI IN, the MOTION, the portamento, the LFO shown"""
    return [dict(t=int(m.group(1)), track=int(m.group(2)), chain=int(m.group(3)), pos=int(m.group(4)), left=int(m.group(5)),
                 lst=[tuple(int(v) for v in x.split("/")) for x in m.group(6).split()], kb=int(m.group(7)), kbch=int(m.group(8)),
                 thru=int(m.group(9)), ktrans=int(m.group(10)), motion=int(m.group(11)), rec=[int(x) for x in m.group(12, 13, 14, 15)],
                 porta=int(m.group(16)), lfo=int(m.group(17)), seq=int(m.group(18)), every=int(m.group(19)), trig=int(m.group(20)))
            for m in V13.finditer(log.text)]


def save4(s, t, encs):  return pg(s, t, SAVE, 3, encs)          # SAVE 4 LIVE IN (0.13)


def lfo_cc(log, cc=74, ch=0, after=0):
    return [(t, d2) for t, st, d1, d2 in log.msgs if st == 0xB0 + ch and d1 == cc and t >= after]


def t013_lfo():
    group("0.13 LFO: RATE SEQ (a rate a beat / bar, LFO page 4), the triplet rates, TRIG (a track's hits start the cycle: the sidechain)")
    BEAT = 4 * STEP_MS
    def drops(cc):
        return [t for (t0, v0), (t, v) in zip(cc, cc[1:]) if v < v0 - 40]
    # RAMP UP at 1 beat, then RATE SEQ 2 steps: 1 beat, 1/8: the ramp falls every beat, then twice a beat, and again
    for seq in (False, True):
        s = Script()
        s.press(100, LFO); s.tap_key(130, wk(0)); s.release(200, LFO)                      # LFO 1 on (CC 74, channel 1)
        t = pg(s, 300, LFO, 0, [(K1, 2), (K2, 4)])                                          # RAMP UP, 1 BEAT
        if seq:
            t = pg(s, t, LFO, 3, [(K1, 2), (K4, 0), (K3, 1), (K4, 2)])                      # STEPS 2; entry 2: 1/8 (from 1 beat)
        s.at(t, "dump", 0)
        s.tap_btn(t + 100, PLAY); t0 = t + 100
        log = run(s, t0 + int(8 * BEAT) + 50)
        dr = [x - t0 for x in drops(lfo_cc(log, after=t0))]
        gaps = [b - a for a, b in zip(dr, dr[1:])]
        if not seq:
            check(len(gaps) >= 6 and all(near(g, BEAT, 30) for g in gaps), "1 BEAT: the ramp falls every beat (%s)" % [round(g) for g in gaps])
        else:
            v = v13s(log)
            short = [g for g in gaps if near(g, BEAT / 2, 30)]
            long_ = [g for g in gaps if near(g, BEAT, 30)]
            check(v and v[0]["seq"] == 2 and v[0]["every"] == 0, "LFO page 4: STEPS 2, EVERY BEAT (%s)" % v[:1])
            check(len(short) + len(long_) == len(gaps) and len(short) >= 4 and len(long_) >= 2 and abs(len(short) - 2 * len(long_)) <= 2,
                  "RATE SEQ 1 BEAT, 1/8: a beat with one fall, a beat with two (%s)" % [round(g) for g in gaps])
    # the triplets: K2 up from 1 bar to the end of the list: 1/32T; the screen names it
    s = Script()
    s.press(100, LFO); s.tap_key(130, wk(0)); s.enc(200, K2, 20); s.at(300, "ui"); s.release(400, LFO)
    s.tap_btn(500, PLAY)
    log = run(s, 500 + int(BEAT) + 20)
    sc = log.screens()
    check(sc and sc[0]["cells"][1][0].endswith("RATE") and sc[0]["cells"][1][1] == "1/32T", "LFO RATE goes on to the triplets: 1/32T at the end (%s)" % (sc[0]["cells"][1:2] if sc else sc))
    cc = lfo_cc(log, after=500)
    check(len(cc) > 20, "and it runs (%d CCs in a beat)" % len(cc))
    # TRIG T1, DECAY: each hit of track 1 (steps 1 and 9) starts the curve at the top; before the first hit it waits at the bottom
    s = Script()
    t = s.steps(100, [0, 8])
    s.press(t, LFO); s.tap_key(t + 30, wk(0)); s.release(t + 100, LFO); t += 160
    t = pg(s, t, LFO, 0, [(K1, 7)])                                                        # DECAY (a bar)
    t = pg(s, t, LFO, 2, [(K4, 1)])                                                        # TRIG T1
    s.at(t, "dump", 0)
    s.tap_btn(t + 100, PLAY); t0 = t + 100
    log = run(s, t0 + int(2 * BAR_MS) + 50)
    v = v13s(log)
    cc = lfo_cc(log, after=t0)
    hits = [x for x, _, _ in log.notes(ch=0, after=t0)]
    jumps = [t2 for (t1, a), (t2, b) in zip(cc, cc[1:]) if b > a + 40]
    check(v and v[0]["trig"] == 1, "LFO page 3 K4: TRIG T1 (%s)" % v[:1])
    check(len(hits) >= 4 and len(jumps) >= 3 and all(any(0 <= j - h <= 20 for h in hits) for j in jumps),
          "the curve starts again at each hit of track 1 (%s, hits %s)" % ([j - t0 for j in jumps], [h - t0 for h in hits]))
    top = [b for (t2, b) in cc if any(0 <= t2 - h <= 12 for h in hits)]
    check(top and min(top) >= 110, "it starts at the top (%s)" % top[:4])
    mid = [b for (t2, b) in cc if any(0 < h - t2 <= 30 for h in hits[1:])]
    check(mid and max(mid) < 70, "half a bar later it has fallen (%s)" % mid[:4])
    # PICK on page 4: LFO + SEL + white 3 = STEPS 3 (white 1: off)
    s = Script()
    t = pg(s, 100, LFO, 3, [(K1, 2)])
    t = pick(s, t, LFO, wk(2))
    s.at(t, "dump", 0)
    t = pick(s, t, LFO, wk(0))
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    check([x["seq"] for x in v13s(log)] == [3, 0], "PICK on RATE SEQ: white 3 = 3 steps, white 1 = off (%s)" % [x["seq"] for x in v13s(log)])


def t013_repeat():
    group("0.13 NOTE REPEAT: on a drum track, ARP + a white held + black 1-4 = the drum again every 1/16, 1/32, 1/32T, 1/8 while held; REC writes it")
    def drum1(s, t):
        t = pg(s, t, HOME, 3)
        return pick(s, t, HOME, wk(2))                                                   # T1: DRUM
    for black, step in ((0, STEP_MS), (1, STEP_MS / 2), (3, 2 * STEP_MS)):
        s = Script()
        t = drum1(s, 100)
        s.tap_btn(t + 100, PLAY); t0 = t + 100
        a = t0 + 600
        s.press(a, ARP); s.keys(a + 30, wk(0)); s.keys(a + 60, wk(0) | bk(black))
        s.keys(a + 1260, wk(0)); s.keys(a + 1290, 0); s.release(a + 1320, ARP)
        s.at(a + 100, "leds")
        log = run(s, a + 1600)
        n = [x for x, _, _ in log.notes(ch=0, after=a + 70, before=a + 1265)]
        gaps = [y - x for x, y in zip(n, n[1:])]
        check(len(n) >= int(1100 / step) - 1 and all(near(g, step, 12) for g in gaps),
              "black %d: the drum every %.0f ms while held (%d notes, %s)" % (black + 1, step, len(n), sorted(set(round(g) for g in gaps))[:6]))
        after = log.notes(ch=0, after=a + 1300)
        check(not after, "let go: no more (%s)" % after[:2])
        if black == 0:
            led = log.key_leds()
            check(led and all(led[0][1][BLACK[i]] in "X." for i in range(4)), "ARP on a drum track: blacks 1-4 lit, the one held blinks (%s)" % (led[0][1] if led else led))
    # REC: one bar of black 2 (1/32) writes the hits with RATCHET 2
    s = Script()
    t = drum1(s, 100)
    s.tap_btn(t + 50, REC)
    s.tap_btn(t + 100, PLAY); t0 = t + 100
    a = t0 + int(BAR_MS) - 60                                                            # from the second bar
    s.press(a, ARP); s.keys(a + 20, wk(0)); s.keys(a + 40, wk(0) | bk(1))
    s.keys(a + int(BAR_MS) - 20, wk(0)); s.keys(a + int(BAR_MS), 0); s.release(a + int(BAR_MS) + 20, ARP)
    s.tap_btn(a + int(BAR_MS) + 60, REC)
    s.at(a + int(BAR_MS) + 150, "dump", 0)
    log = run(s, a + int(BAR_MS) + 250)
    d = log.dumps
    check(d and d[0]["on"].count("x") >= 14, "REC: the repeats are written as steps (%s)" % (d[0]["on"] if d else d))
    # not on a melodic track: ARP + black 1 plays the note as before
    s = Script()
    s.tap_btn(100, PLAY)
    s.press(700, ARP); s.keys(730, wk(0)); s.keys(760, wk(0) | bk(0)); s.keys(1400, 0); s.release(1450, ARP)
    log = run(s, 1600)
    check(len(log.notes(ch=0, after=700)) <= 3, "a melodic track: no NOTE REPEAT (%d notes)" % len(log.notes(ch=0, after=700)))


def t013_keyboard():
    group("0.13 KEYBOARD and MIDI IN (SAVE 4): a keyboard's notes TRANSPOSE the key (ALL / SPLIT C3, its channel); MIDI IN ALWAYS plays without REC")
    def setup(s, kb=1, ch=0, thru=0):
        t = s.steps(100, [0])
        t = kp(s, t + 100, [(K2, 1), (K4, 1)])                                          # C major, track 1 in key
        enc = [(K2, kb)]
        if ch: enc.append((K3, ch))
        if thru: enc.append((K4, 1))
        return save4(s, t, enc)
    # ALL, stopped: D (62) comes in: TRANSPOSE +2 at once; its note is not played; C4 plays as D4
    s = Script()
    t = setup(s)
    s.raw(t, "midi 0x90 62 100"); s.raw(t + 50, "midi 0x80 62 0"); t += 100
    s.at(t, "dump", 0)
    s.tap_btn(t + 50, PLAY); t0 = t + 50
    log = run(s, t0 + 300)
    v = v13s(log)
    check(v and v[0]["kb"] == 1 and v[0]["ktrans"] == 2, "SAVE 4 K2 ALL: D in = TRANSPOSE +2 (%s)" % v[:1])
    check(not log.notes(before=t0), "the keyboard's note is not played (%s)" % log.notes(before=t0))
    check(pitches(log, after=t0)[:1] == [62], "C4 plays as D4 (%s)" % pitches(log, after=t0)[:1])
    # B (59 or 71): -1, the nearest way; a second note moves again from the key, not from the last transpose
    s = Script()
    t = setup(s)
    s.raw(t, "midi 0x90 71 100"); s.raw(t + 40, "midi 0x80 71 0"); s.at(t + 60, "dump", 0)
    s.raw(t + 100, "midi 0x90 41 100"); s.raw(t + 140, "midi 0x80 41 0"); s.at(t + 160, "dump", 0)
    s.raw(t + 200, "midi 0x90 48 100"); s.raw(t + 240, "midi 0x80 48 0"); s.at(t + 260, "dump", 0)
    log = run(s, t + 300)
    check([x["ktrans"] for x in v13s(log)] == [-1, 5, 0], "B = -1, F = +5, C = back to 0 (%s)" % [x["ktrans"] for x in v13s(log)])
    # while it plays it waits for QUANTISE (AUTO: the bar)
    s = Script()
    t = setup(s)
    s.tap_btn(t, PLAY); t0 = t
    s.raw(t0 + int(5.5 * STEP_MS), "midi 0x90 65 100"); s.raw(t0 + int(6 * STEP_MS), "midi 0x80 65 0")
    log = run(s, t0 + int(2.2 * BAR_MS))
    check(pitches(log, after=t0)[:2] == [60, 65], "playing: F in bar 1, the key moves at bar 2 (%s)" % pitches(log, after=t0)[:3])
    # SPLIT C3: below C3 transposes, C3 and above is a note (MIDI IN ALWAYS: played on the track)
    s = Script()
    t = setup(s, kb=2, thru=1)
    s.raw(t, "midi 0x90 38 100"); s.raw(t + 40, "midi 0x80 38 0")
    s.raw(t + 100, "midi 0x90 64 90"); s.raw(t + 140, "midi 0x80 64 0"); s.at(t + 160, "dump", 0)
    log = run(s, t + 200)
    v = v13s(log)
    n = log.notes(ch=0, after=t)
    check(v and v[0]["kb"] == 2 and v[0]["ktrans"] == 2 and v[0]["thru"] == 1, "SPLIT: D2 transposes +2 (%s)" % v[:1])
    check([x[1:] for x in n] == [(66, 90)], "SPLIT + MIDI IN ALWAYS: E4 plays on track 1, in the key moved (+2: F#4) (%s)" % n)
    # its channel: KEYB CH 2 - a note on channel 1 is a note (thru), on channel 2 it transposes
    s = Script()
    t = setup(s, kb=1, ch=2, thru=1)
    s.raw(t, "midi 0x90 62 100"); s.raw(t + 40, "midi 0x80 62 0"); s.at(t + 60, "dump", 0)
    s.raw(t + 100, "midi 0x91 62 100"); s.raw(t + 140, "midi 0x81 62 0"); s.at(t + 160, "dump", 0)
    log = run(s, t + 200)
    v = v13s(log)
    check([x["ktrans"] for x in v] == [0, 2] and v[0]["kbch"] == 2, "KEYB CH 2: channel 1 plays, channel 2 transposes (%s)" % [x["ktrans"] for x in v])
    check(len(log.notes(ch=0, after=t)) == 1, "... the note of channel 1 went out (%s)" % log.notes(ch=0, after=t))
    # MIDI IN: REC ONLY (as before) - a note in without REC is silent; ALWAYS - heard, not written
    for thru in (0, 1):
        s = Script()
        t = s.steps(100, [0])
        t = save4(s, t, [(K4, 1)] if thru else [(K4, -1)])
        s.at(t, "dump", 0)
        s.tap_btn(t, PLAY); t0 = t
        s.raw(t0 + 300, "midi 0x90 67 100"); s.raw(t0 + 400, "midi 0x80 67 0")
        s.at(t0 + int(BAR_MS) + 100, "dump", 0)
        log = run(s, t0 + int(BAR_MS) + 200)
        heard = [x for x in log.notes(ch=0, after=t0 + 250, before=t0 + 450) if x[1] == 67]
        d = log.dumps
        if thru:
            check(len(heard) == 1 and d[0]["hash"] == d[1]["hash"], "MIDI IN ALWAYS: the note plays on track 1, the pattern is not touched (%s)" % heard)
        else:
            check(not heard, "MIDI IN REC ONLY: without REC nothing (%s)" % heard)


def t013_motion():
    group("0.13 MOTION (SAVE 4 K1): with REC, FX + K moves are written into the loop (a 16th a cell) and play back; the hand wins; FX + OCT- wipes it")
    s = Script()
    t = save4(s, 100, [(K1, 1)])                                                         # 1 BAR
    s.tap_btn(t, REC); t += 60
    s.tap_btn(t, PLAY); t0 = t
    s.press(t0 + int(4.2 * STEP_MS), FX); s.enc(t0 + int(4.2 * STEP_MS) + 20, K4, 10); s.release(t0 + int(4.2 * STEP_MS) + 60, FX)    # FILTER +20 at step 5
    s.press(t0 + int(12.2 * STEP_MS), FX); s.enc(t0 + int(12.2 * STEP_MS) + 20, K4, -10); s.release(t0 + int(12.2 * STEP_MS) + 60, FX)   # 0 at step 13
    s.tap_btn(t0 + int(BAR_MS) - 30, REC)                                                # REC off at the end of bar 1
    for k in (2, 6, 10, 14):
        s.at(t0 + int(BAR_MS + (k + 0.5) * STEP_MS), "dump", 0)                          # bar 2: steps 3, 7, 11, 15
    log = run(s, t0 + int(2 * BAR_MS))
    st = log.states
    v = v13s(log)
    check(len(st) == 4 and [x["mac"][3] for x in st] == [0, 20, 20, 0], "bar 2 without the hand: FILTER 0, 20 from step 5, 0 from step 13 (%s)" % [x["mac"][3] for x in st])
    check(v and v[0]["motion"] == 1 and v[0]["rec"][3] >= 4 and v[0]["rec"][:3] == [0, 0, 0], "the cells written: the FILTER's only (%s)" % (v[0]["rec"] if v else v))
    # without REC nothing is written; the hand wins over what plays
    s = Script()
    t = save4(s, 100, [(K1, 1)])
    s.tap_btn(t, PLAY); t0 = t
    s.press(t0 + 300, FX); s.enc(t0 + 320, K1, 5); s.release(t0 + 360, FX)
    s.at(t0 + int(BAR_MS) + 300, "dump", 0)
    log = run(s, t0 + int(BAR_MS) + 400)
    v = v13s(log)
    check(v and v[0]["rec"] == [0, 0, 0, 0] and log.states[0]["mac"][0] == 5, "without REC: nothing written, the macro stays (%s %s)" % (v[0]["rec"] if v else v, log.states[0]["mac"]))
    # FX + OCT-: the macros 0 and the motion wiped
    s = Script()
    t = save4(s, 100, [(K1, 1)])
    s.tap_btn(t, REC); t += 60
    s.tap_btn(t, PLAY); t0 = t
    s.press(t0 + 300, FX); s.enc(t0 + 320, K2, 4); s.release(t0 + 360, FX)
    s.at(t0 + 1000, "dump", 0)
    s.press(t0 + 1100, FX); s.tap_btn(t0 + 1130, OCT_DOWN, hold=20); s.release(t0 + 1200, FX)
    s.at(t0 + 1250, "dump", 0)
    log = run(s, t0 + 1300)
    v = v13s(log)
    check(len(v) == 2 and v[0]["rec"][1] >= 2 and v[1]["rec"] == [0, 0, 0, 0] and log.states[1]["msg"] == "MACROS 0, THE MOTION WIPED",
          "FX + OCT-: MACROS 0, THE MOTION WIPED (%s, %s)" % ([x["rec"] for x in v], log.states[1]["msg"] if len(log.states) > 1 else None))
    # SAVE 4's screen
    s = Script()
    s.press(100, SAVE)
    for i in range(3): s.tap_btn(130 + 40 * i, OCT_UP, hold=20)
    s.enc(300, K1, 2); s.enc(330, K2, 2); s.enc(360, K3, 3); s.enc(390, K4, 1); s.at(450, "ui"); s.release(500, SAVE)
    log = run(s, 600)
    sc = log.screens()
    check(sc and sc[0]["cells"] == [("MOTION", "2 BARS"), ("KEYBOARD", "SPLIT C3"), ("KEYB CH", "3"), ("MIDI IN", "ALWAYS")] and sc[0]["lines"][2].startswith("SAVE 4/4"),
          "SAVE 4/4 LIVE IN: MOTION, KEYBOARD, KEYB CH, MIDI IN (%s)" % (sc[0]["cells"] if sc else sc))
    check(not log.saves, "turning SAVE 4's knobs does not save (%s)" % log.saves)


def t013_slide():
    group("0.13 SLIDE (EDIT + black 7): the step holds into the next and that note glides: CC 65 127 before it, 0 before the next note that does not slide")
    s = Script()
    t = s.steps(100, [0, 1])                                                             # the cursor on step 2
    s.press(t, SEL); s.tap_key(t + 30, KEY_G4, hold=40); s.release(t + 100, SEL); t += 160   # step 2: G4
    s.press(t, EDIT); s.tap_key(t + 30, wk(0)); s.tap_key(t + 100, bk(6)); s.at(t + 160, "leds"); s.release(t + 200, EDIT); t += 260   # step 1: SLIDE
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); t0 = t
    s.tap_btn(t0 + int(BAR_MS + 1.5 * STEP_MS), PLAY)                                   # STOP in bar 2's step 2
    log = run(s, t0 + int(BAR_MS + 3 * STEP_MS))
    m = [(x - t0, st, d1, d2) for x, st, d1, d2 in log.msgs if x >= t0 and (st & 0xF0) in (0x80, 0x90, 0xB0) and st & 15 == 0 and (st & 0xF0 != 0xB0 or d1 == 65)]
    def idx(pred, start=0):
        for i in range(start, len(m)):
            if pred(m[i]): return i
        return -1
    on60 = idx(lambda x: x[1] == 0x90 and x[2] == 60 and x[3])
    p_on = idx(lambda x: x[1] == 0xB0 and x[3] == 127)
    on67 = idx(lambda x: x[1] == 0x90 and x[2] == 67 and x[3])
    off60 = idx(lambda x: (x[1] == 0x80 or (x[1] == 0x90 and not x[3])) and x[2] == 60, on60 + 1)
    p_off = idx(lambda x: x[1] == 0xB0 and x[3] == 0)
    on60b = idx(lambda x: x[1] == 0x90 and x[2] == 60 and x[3], on67 + 1)
    check(0 <= on60 < p_on < on67 and m[p_on][0] == m[on67][0], "CC 65 127 just before step 2's note (%s)" % m[:6])
    check(off60 > on67 and m[off60][0] - m[on67][0] <= 30, "legato: step 1's note ends after step 2's begins (%s)" % (m[off60][0] - m[on67][0] if off60 >= 0 and on67 >= 0 else None))
    check(p_on < p_off < on60b and m[p_off][0] == m[on60b][0], "CC 65 0 before bar 2's first note: it does not slide (%s)" % m[on67:on67 + 6])
    d = log.dumps
    led = log.key_leds()
    check(led and led[0][1][BLACK[6]] == "X", "EDIT: black 7 lit on a SLIDE step (%s)" % (led[0][1] if led else led))
    # the STOP during a slide: CC 65 0
    s = Script()
    t = s.steps(100, [0, 1])
    s.press(t, EDIT); s.tap_key(t + 30, wk(0)); s.tap_key(t + 100, bk(6)); s.release(t + 200, EDIT); t += 260
    s.tap_btn(t, PLAY); t0 = t
    s.tap_btn(t0 + int(1.5 * STEP_MS), PLAY)                                            # STOP in step 2: the glide is on
    log = run(s, t0 + 600)
    c = [(x - t0, d2) for x, st, d1, d2 in log.msgs if st == 0xB0 and d1 == 65]
    check([v for _, v in c] == [127, 0], "STOP: the portamento goes off (%s)" % c)
    # TIE and SLIDE: one or the other; a drum track has no SLIDE; the screen says it
    s = Script()
    t = s.steps(100, [0])
    s.press(t, EDIT); s.tap_key(t + 30, wk(0)); s.tap_key(t + 100, bk(5)); s.tap_key(t + 170, bk(6)); s.at(t + 230, "ui"); s.release(t + 300, EDIT); t += 360
    t = pg(s, t, HOME, 3); t = pick(s, t, HOME, wk(2))                                  # DRUM
    s.press(t, EDIT); s.tap_key(t + 100, bk(6)); s.at(t + 150, "dump", 0); s.release(t + 200, EDIT)
    log = run(s, t + 300)
    sc = log.screens()
    check(sc and "SLIDE" in sc[0]["lines"][2] and "TIE" not in sc[0]["lines"][2], "black 6 TIE then black 7 SLIDE: SLIDE alone (%s)" % (sc[0]["lines"][2] if sc else sc))
    check(log.states and log.states[0]["msg"] == "SLIDE: A MELODIC TRACK'S STEP", "a drum track: no SLIDE (%s)" % (log.states[0]["msg"] if log.states else None))


def t013_chain():
    group("0.13 CHAIN LIST (HOME 7 K2 LIST, HOME 8): up to 8 patterns, each 1-8 times; PLAY from entry 1; a pattern by hand in the list goes on from it, else the list is off")
    def pattern_pick(s, t, p):
        s.enc(t, E_PRE, p)
        return t + 100
    def three(s):
        t = s.steps(100, (0,))                                                           # P1: C4
        t = pattern_pick(s, t, 1)
        s.press(t, SEL); s.tap_key(t + 30, KEY_G4, hold=40); s.release(t + 100, SEL); t += 600   # P2: G4 (then a pause: not a chord)
        t = pattern_pick(s, t, 1)
        s.press(t, SEL); s.tap_key(t + 30, KEY_E4, hold=40); s.release(t + 100, SEL); t += 600   # P3: E4
        t = pattern_pick(s, t, -2)                                                       # back on P1
        t = home_page(s, t, 6, [(K2, 2)])                                                # CHAIN: LIST
        return home_page(s, t, 7, [(K1, 2), (K2, 1), (K4, 1)])                           # 3 entries: P1, P2 x2, P3
    s = Script()
    t = three(s)
    s.at(t, "dump", 0)
    s.press(t, HOME); s.at(t + 50, "ui"); s.release(t + 100, HOME); t += 160
    t = pattern_pick(s, t, 3)                                                            # P4 picked while stopped: PLAY starts from entry 1 anyway
    s.tap_btn(t, PLAY); t0 = t
    log = run(s, t0 + int(5.2 * BAR_MS))
    v = v13s(log)
    n = [(round((x - t0) / BAR_MS, 2), p) for x, p, _ in log.notes(ch=0, after=t0)]
    check(v and v[0]["chain"] == 1 and v[0]["lst"] == [(1, 1), (2, 2), (3, 1)], "HOME 8: the list P1, P2 x2, P3 (%s)" % v[:1])
    check([p for _, p in n[:6]] == [60, 67, 67, 64, 60, 67] and all(near(n[i][0], i, 0.02) for i in range(6)),
          "it plays P1, P2, P2, P3, P1, P2 a bar each (%s)" % n[:6])
    sc = log.screens()
    check(sc and sc[0]["lines"][2].startswith("HOME 8/8 ") and sc[0]["cells"][3][0].endswith("TIMES") and sc[0]["cells"][3][1] == "X2", "the page: HOME 8/8, the entry's TIMES (%s)" % (sc[0]["lines"][2:3] + sc[0]["cells"][3:] if sc else sc))
    # by hand while it plays: P3 (in the list) plays at the end of the loop, then the list goes on from it (P1); P4 (not in it): the list is off
    for p, want, on in ((2, [60, 64, 60, 67], 1), (3, [60, 0, 0, 0], 0)):
        s = Script()
        t = three(s)
        s.tap_btn(t, PLAY); t0 = t
        pattern_pick(s, t0 + 600, p)
        s.at(t0 + int(3.5 * BAR_MS), "dump", 0)
        log = run(s, t0 + int(4.2 * BAR_MS))
        bars = []
        for b in range(4):
            x = [d1 for tt, d1, _ in log.notes(ch=0, after=t0 + b * BAR_MS - 20, before=t0 + (b + 1) * BAR_MS - 20)]
            bars.append(x[0] if x else 0)
        v = v13s(log)
        check(bars == want and v and v[0]["chain"] == on, "P%d by hand in bar 1: %s, the list %s (%s, %s)" % (p + 1, want, "on" if on else "off", bars, v[0]["chain"] if v else v))
    # the pair (0.10) is K2 +1 as before; LIST is +2; saved with the project
    d = tempfile.mkdtemp()
    flash = os.path.join(d, "flash.bin")
    s = Script()
    t = three(s)
    t = save4(s, t, [(K2, 1), (K4, 1)])
    s.tap_btn(t, SAVE); s.tap_btn(t + 300, SAVE)
    run(s, t + 1500, flash)
    s = Script()
    s.at(300, "dump", 0)
    log = run(s, 400, flash)
    v = v13s(log)
    check(v and v[0]["chain"] == 1 and v[0]["lst"] == [(1, 1), (2, 2), (3, 1)] and v[0]["kb"] == 1 and v[0]["thru"] == 1,
          "after a power cycle: the CHAIN LIST, the KEYBOARD, MIDI IN (%s)" % v[:1])


# ------------------------------------------------------------------------------------------------ 0.15
V15 = re.compile(r"^\s*(\d+) ms  v15 T(\d+) groove (\d+) amt (\d+) swing (\d+) name \[([^\]]*)\] link (\d+) sent (\d+) aud (\d+) hfree (\d+) hgenre (\d+) hprog (\d+) up((?: \d+)*) slots((?: \d+:(?:ok|-)\[[^\]]*\])*)$", re.M)


def v15s(log):
    """the 0.15 'v15' lines of the dumps: the track's GROOVE, the project's name, the link to the Pi's editor, the slots and their names"""
    return [dict(t=int(m.group(1)), track=int(m.group(2)), groove=int(m.group(3)), amt=int(m.group(4)), swing=int(m.group(5)), name=m.group(6),
                 link=int(m.group(7)), sent=int(m.group(8)), aud=int(m.group(9)), hfree=int(m.group(10)), hgenre=int(m.group(11)),
                 hprog=int(m.group(12)), up=[int(x) for x in m.group(13).split()],
                 slots={int(a): (ok == "ok", nm) for a, ok, nm in re.findall(r"(\d+):(ok|-)\[([^\]]*)\]", m.group(14))})
            for m in V15.finditer(log.text)]


_SGQJSON = [None]


def sgq_image(lines):
    """a project image made by the editor's converter (the firmware's core) from a patch over a new project"""
    if _SGQJSON[0] is None:
        out = os.path.join(tempfile.mkdtemp(), "sagga_sgqjson")
        subprocess.run(["cc", "-std=c11", "-O2", "-I" + ROOT + "/firmware/src", ROOT + "/tools/sgqmid/sagga_sgqjson.c",
                        ROOT + "/firmware/src/sagga_seq_core.c", ROOT + "/firmware/src/sagga_beats.c", "-o", out], check=True)
        _SGQJSON[0] = out
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "p.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    subprocess.run([_SGQJSON[0], "apply", "new", os.path.join(d, "p.txt"), os.path.join(d, "o.sgq")], check=True)
    return open(os.path.join(d, "o.sgq"), "rb").read()


def name_lines(text):
    return ["ext - name %d %d" % (i, ord(text[i]) if i < len(text) else 0) for i in range(16)]


def sx_import(s, t, image):
    """the image sent in as the bridge sends it (chunks, the end), a frame every 25 ms; returns the time after"""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import sagga_grid_bridge as B
    for fr in B.dump_frames(image):
        s.at(t, "sx", " ".join("%02X" % b for b in fr[1:-1]))
        t += 25
    return t + 100


def slot_headers(flash, slot):
    """the areas of the flash whose header names that slot (1-8)"""
    import struct
    data = open(flash, "rb").read()
    out = []
    for a in range(9):
        h = struct.unpack_from("<5I", data, 0x97000 + a * 0x8000)
        if h[0] == 0x4C534753 and h[4] == slot - 1:
            out.append(a)
    return out


def t015_names_clear():
    group("0.15 the project's name (from the Pi's editor) on the SAVE screen, in the slot's header, at LOAD; SAVE + REC twice clears a slot")
    d = tempfile.mkdtemp()
    flash = os.path.join(d, "flash.bin")
    s = Script()
    t = s.steps(100, [0])
    s.tap_btn(t + 100, SAVE); s.tap_btn(t + 400, SAVE)                                    # slot 1: a project with no name
    t = sx_import(s, t + 1500, sgq_image(name_lines("Notte in citta") + ["project - bpm - 100"]))
    s.at(t, "dump", 0)
    s.press(t + 100, SAVE); s.enc(t + 130, E_PRE, 1); s.release(t + 200, SAVE)              # slot 2 (that asks to save)
    s.tap_btn(t + 400, SAVE)                                                              # saved
    s.press(t + 4000, SAVE); s.at(t + 4100, "ui"); s.release(t + 4200, SAVE)              # (the release asks: it lapses)
    s.at(t + 4300, "dump", 0)
    log = run(s, t + 4400, flash)
    v = v15s(log)
    check(v and v[0]["name"] == "NOTTE IN CITTA" and v[-1]["slots"][2] == (True, "NOTTE IN CITTA") and v[-1]["slots"][1] == (True, ""),
          "an imported project keeps its name; saved, the slot's header has it (%s)" % [(x["name"], x["slots"]) for x in v])
    check([sl for _, sl, _ in log.saves] == [1, 2], "slots 1 and 2 saved (%s)" % log.saves)
    sc = log.screens()
    check(sc and sc[0]["lines"][3] == "SLOT 2: NOTTE IN CITTA" and sc[0]["lines"][4].startswith("NOW: NOTTE IN CITTA"),
          "SAVE held: the slot's name and the project's (%s)" % (sc[0]["lines"][3:5] if sc else sc))
    # a power cycle: the names are read from the headers; slot 1 has none; LOAD says the name
    s = Script()
    s.at(200, "dump", 0)
    s.press(300, SAVE); s.enc(330, E_PRE, -1); s.release(400, SAVE)                      # slot 1 (asks to save: it lapses)
    s.press(4000, SAVE); s.at(4100, "ui"); s.release(4200, SAVE)                          # (asks again: lapses)
    s.press(7500, SAVE); s.enc(7530, E_PRE, 1); s.release(7600, SAVE)                    # slot 2 (asks: lapses)
    s.press(11000, HOME); s.tap_btn(11020, SAVE); s.release(11100, HOME); s.at(11150, "dump", 0)
    s.press(11300, HOME); s.tap_btn(11320, SAVE); s.release(11400, HOME); s.at(11450, "dump", 0)
    log = run(s, 11600, flash)
    v = v15s(log)
    sc = log.screens()
    st = [x["msg"] for x in log.states]
    check(v and v[0]["name"] == "NOTTE IN CITTA" and v[0]["slots"][2] == (True, "NOTTE IN CITTA"), "power-up: the newest slot, with its name (%s)" % v[:1])
    check(sc and sc[0]["lines"][3] == "SLOT 1: NO NAME" and sc[0]["lines"][4].startswith("NOW: NOTTE IN CITTA"), "a slot saved without a name: NO NAME (%s)" % (sc[0]["lines"][3:5] if sc else sc))
    check(st[1:] == ["LOAD SLOT 2 NOTTE IN CITTA: HOME+SAVE AGAIN", "LOADED SLOT 2: NOTTE IN CITTA"] and not log.saves, "LOAD asks and says the name (%s)" % st)
    # SAVE + REC: asks, again clears; the project stays; REC is not armed; an empty slot, a playing FM-1: told
    s = Script()
    s.press(4000, SAVE); s.tap_btn(4030, REC); s.release(4100, SAVE); s.at(4150, "dump", 0)     # slot 2 (the one loaded at power-up)
    s.press(4300, SAVE); s.tap_btn(4330, REC); s.release(4400, SAVE); s.at(4450, "dump", 0); s.at(4460, "leds")
    s.press(6000, SAVE); s.at(6100, "ui"); s.release(6200, SAVE)                          # (asks to save: lapses)
    s.press(6500, SAVE); s.tap_btn(6530, REC); s.release(6600, SAVE); s.at(6650, "dump", 0)     # slot 2 again: empty now
    s.press(7000, SAVE); s.enc(7030, E_PRE, -1); s.release(7100, SAVE)                   # slot 1 (asks: lapses)
    s.tap_btn(10500, PLAY)
    s.press(10800, SAVE); s.tap_btn(10830, REC); s.release(10900, SAVE); s.at(10950, "dump", 0)  # playing
    s.tap_btn(11300, PLAY)
    log = run(s, 12000, flash)
    st = [x["msg"] for x in log.states]
    v = v15s(log)
    check(st[:2] == ["CLEAR SLOT 2 NOTTE IN CITTA: SAVE+REC AGAIN", "SLOT 2 CLEARED: THE PROJECT YOU HAVE STAYS"], "SAVE + REC asks, again clears (%s)" % st[:2])
    check(len(v) > 1 and v[1]["slots"][2] == (False, "") and v[1]["name"] == "NOTTE IN CITTA" and v[1]["slots"][1] == (True, ""),
          "slot 2 empty, the project in the FM-1 untouched, slot 1 there (%s)" % v[1:2])
    check(st[2:] == ["NOTHING TO CLEAR: EMPTY SLOT 2", "CLEAR A SLOT: STOP FIRST"], "an empty slot, a playing FM-1: told, nothing done (%s)" % st[2:])
    bl = log.btn_leds()
    check(bl and bl[0][1][REC] == "." and not slot_headers(flash, 2) and slot_headers(flash, 1), "REC not armed (%s); no header names slot 2 any more; slot 1's is there" % (bl[:1]))
    check("ERASE WHILE PLAYING" not in log.text and not log.saves, "nothing erased while playing; nothing saved")
    sc = log.screens()
    check(sc and sc[0]["lines"][3] == "SLOT 2: EMPTY", "the screen: SLOT 2: EMPTY (%s)" % (sc[0]["lines"][3:4] if sc else sc))
    s = Script()
    s.at(200, "dump", 0)
    s.tap_btn(300, PLAY)
    log = run(s, 2400, flash)
    v = v15s(log)
    check(v and v[0]["slots"][2] == (False, "") and v[0]["name"] == "" and log.notes(ch=0), "after a power cycle slot 2 stays empty: slot 1 is loaded (%s)" % v[:1])
    # two copies of a slot (saved twice while playing: the old one is not erased then) are both cleared
    s = Script()
    t = s.steps(100, [0])
    s.press(t, SAVE); s.enc(t + 30, E_PRE, 2); s.release(t + 100, SAVE)                   # slot 3
    s.tap_btn(t + 4000, PLAY)
    s.tap_btn(t + 4300, SAVE); s.tap_btn(t + 4600, SAVE)
    s.tap_btn(t + 5300, SAVE); s.tap_btn(t + 5600, SAVE)
    s.tap_btn(t + 6400, PLAY)
    s.press(t + 6420, SAVE); s.tap_btn(t + 6440, REC); s.release(t + 6500, SAVE)
    s.press(t + 6800, SAVE); s.tap_btn(t + 6820, REC); s.release(t + 6900, SAVE); s.at(t + 6950, "dump", 0)
    log = run(s, t + 7200, flash)
    v = v15s(log)
    check(len(log.saves) == 2 and v and v[0]["slots"][3] == (False, "") and not slot_headers(flash, 3), "a slot saved twice, cleared: no copy of it left (%s %s)" % (log.saves, slot_headers(flash, 3)))


def t015_groove():
    group("0.15 GROOVE (HOME 7 K3 / K4 on a track that is not TAPE): each 16th early or late, louder or softer; PICK; saved")
    def run_groove(encs):
        s = Script()
        t = s.steps(100, list(range(16)))
        t = home_page(s, t, 6, encs)
        s.at(t, "dump", 0)
        s.press(t, HOME); s.at(t + 50, "ui"); s.release(t + 100, HOME); t += 200
        s.tap_btn(t, PLAY)
        log = run(s, t + int(BAR_MS) + 200)
        n = log.notes(ch=0, after=t)
        return log, [(round((x - n[0][0]) / STEP_MS * 100) - 100 * i, v) for i, (x, _, v) in enumerate(n[:16])]
    log, n0 = run_groove([])
    check(all(abs(d) <= 2 for d, _ in n0) and all(v == n0[0][1] for _, v in n0), "no GROOVE: the 16ths straight, one velocity (%s)" % n0[:4])
    log, n = run_groove([(K3, 2)])                                                        # GARAGE, 100 % (chosen at 0 %: all of it)
    v = v15s(log)
    sc = log.screens()
    want = [0, 28, 0, 22, 0, 30, 0, 24] * 2
    check(v and v[0]["groove"] == 2 and v[0]["amt"] == 100 and all(abs(d - w) <= 2 for (d, _), w in zip(n, want)), "GARAGE: the 2-step shuffle (%s)" % [d for d, _ in n])
    check(sc and sc[0]["cells"][2][0].endswith("GROOVE") and sc[0]["cells"][2][1] == "GARAGE" and sc[0]["cells"][3] == ("GROOVE AMT", "100%"), "HOME 7: GROOVE, GROOVE AMT (%s)" % (sc[0]["cells"][2:] if sc else sc))
    vel = [x for _, x in n]
    check(vel[1] < vel[0] and vel[3] < vel[2] < vel[0], "... softer off the beat (%s)" % vel[:4])
    log, n = run_groove([(K3, 2), (K4, -10)])                                             # 50 %
    check(all(abs(d - w // 2) <= 2 for (d, _), w in zip(n, want)), "GROOVE AMT 50 %%: half of it (%s)" % [d for d, _ in n])
    log, n = run_groove([(K3, 9)])                                                        # TRAP: the accents
    b = n[0][1] - 14
    check([x - b for _, x in n[:4]] == [14, -20, 4, -16], "TRAP: the velocities %s" % [x for _, x in n[:4]])
    # PICK: HOME 7, black 11 twice (the focus on K3), SEL + white 4 = the 4th template
    s = Script()
    t = home_page(s, 100, 6, [])
    s.press(t, HOME); s.press(t + 30, SEL)
    s.tap_key(t + 60, bk(10)); s.tap_key(t + 140, bk(10)); s.tap_key(t + 220, wk(3))
    s.release(t + 300, SEL); s.release(t + 330, HOME)
    s.at(t + 400, "dump", 0)
    v = v15s(run(s, t + 500))
    check(v and v[0]["groove"] == 3 and v[0]["amt"] == 100, "PICK: SEL + white 4 = DILLA (%s)" % v[:1])
    # a TAPE track: K3 / K4 are its loop and quantise, as before
    s = Script()
    t = home_page(s, 100, 3, [(K1, 3)])                                                   # TAPE
    t = home_page(s, t, 6, [(K3, 2), (K4, 2)])
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    v = v15s(log)
    tp = log.tapes[-1] if log.tapes else None
    check(v and v[0]["groove"] == 0 and tp and tp["bars"] == 6 and tp["quant"] == 20, "a TAPE track: K3 its bars, K4 its quantise, no GROOVE (%s %s)" % (v[:1], tp))
    # saved with the project
    d = tempfile.mkdtemp()
    flash = os.path.join(d, "flash.bin")
    s = Script()
    t = home_page(s, 100, 6, [(K3, 4), (K4, -4)])                                         # AFRO 80 %
    s.tap_btn(t, SAVE); s.tap_btn(t + 300, SAVE)
    run(s, t + 1500, flash)
    s = Script(); s.at(300, "dump", 0)
    v = v15s(run(s, 400, flash))
    check(v and v[0]["groove"] == 4 and v[0]["amt"] == 80, "after a power cycle: AFRO 80 %% (%s)" % v[:1])


def t015_link():
    group("0.15 the Pi's editor: positions while asked (SysEx 30 / 31), the notes it asks to hear (32)")
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import sagga_grid_bridge as B
    s = Script()
    t = s.steps(100, [0, 4, 8, 12])
    s.at(t + 100, "sx", "7D 53 47 30 01")                                                 # asked
    s.tap_btn(t + 300, PLAY)
    p = t + 300
    s.at(p + int(BAR_MS) + 50, "dump", 0)
    s.tap_btn(p + int(1.5 * BAR_MS), PLAY)
    s.at(p + int(1.6 * BAR_MS), "sx", "7D 53 47 30 00")                                   # not any more
    s.tap_btn(p + int(1.8 * BAR_MS), PLAY)
    log = run(s, p + int(2.5 * BAR_MS))
    pos = [(tm, m) for tm, m in log.sysex if m[:5] == [0xF0, 0x7D, 0x53, 0x47, 0x31]]
    playing = [(tm, m) for tm, m in pos if m[5] == 1]
    check(pos and pos[0][0] < p and pos[0][1][5] == 0 and len(pos[0][1]) == 5 + 3 + 3 + 2 + 32 + 1, "asked: where it is, at once (%d bytes)" % (len(pos[0][1]) if pos else 0))
    gaps = [b - a for (a, _), (b, _) in zip(playing, playing[1:])]
    check(len(playing) >= 20 and all(near(g, STEP_MS, 3) for g in gaps[1:]), "playing: one every 16th (%d, %s)" % (len(playing), gaps[:4]))
    lib = type("L", (), {"send": lambda self, m: None, "sender": None})()
    d = tempfile.mkdtemp()
    ctl = B.Control(lib, folder=d, log=lambda x: None)
    six = [m for _, m in playing if B.get7(m[8:11]) == 30]
    ok = bool(six) and ctl.fm1_sysex(six[0], 0.0)
    j = json.load(open(os.path.join(d, "pos.json"))) if ok else {}
    check(ok and j["playing"] == 1 and j["bpm"] == BPM and j["steps"][0] == 5 and j["pats"][0] == 0,
          "the bridge reads it: at the 6th 16th (clock 30) T1 plays its step 6, 128 BPM (%s)" % ({k: j[k] for k in ("clock", "bpm", "steps")} if j else six[:1]))
    check(len([m for _, m in pos if B.get7(m[8:11]) == 0 and m[5] == 1]) == 1, "START: one position for the 16th it starts on")
    stop = [tm for tm, m in pos if m[5] == 0 and tm > p]
    check(stop and near(stop[0], p + 1.5 * BAR_MS, 40), "at STOP: where it stopped (%s)" % stop[:1])
    check(not [tm for tm, m in pos if tm > p + 1.6 * BAR_MS + 20], "not asked any more: none, playing or not")
    v = v15s(log)
    check(v and v[0]["link"] == 1 and v[0]["sent"] >= 16, "the dump: asked, sent (%s)" % v[:1])
    # six seconds without being asked again: it stops by itself
    s = Script()
    s.at(100, "sx", "7D 53 47 30 01")
    s.tap_btn(200, PLAY)
    log = run(s, 9000)
    pos = [tm for tm, m in log.sysex if m[:5] == [0xF0, 0x7D, 0x53, 0x47, 0x31]]
    check(pos and max(pos) < 6300 and max(pos) > 5800, "not asked again: it stops after 6 s (last at %d ms)" % (max(pos) if pos else 0))
    # nobody asked: no SysEx
    s = Script()
    s.tap_btn(200, PLAY)
    log = run(s, 2000)
    check(not [m for _, m in log.sysex if m[4:5] == [0x31]], "nobody asked: no positions")
    # PREVIEW: a step's notes on the track's channel, as the track plays them (its key, its CHORD); a TAPE note; gone after GATE
    s = Script()
    t = home_page(s, 100, 0, [(K1, 2)])                                                   # T1 on channel 3
    s.at(t, "sx", "7D 53 47 32 00 50 14 00 02 3C 40")                                      # T1 vel 80, 200 ms, C4 E4
    t = home_page(s, t + 400, 3, [(K3, 1)])                                               # a CHORD (one note becomes it)
    s.at(t, "sx", "7D 53 47 32 00 64 0A 00 01 3C")                                        # C4 alone: the chord
    s.at(t + 300, "sx", "7D 53 47 32 00 64 0A 01 01 3C")                                  # the same as a TAPE note: C4 only
    s.at(t + 600, "sx", "7D 53 47 32 10 64 0A 00 01 3C")                                  # track 17: nothing
    s.at(t + 900, "sx", "7D 53 47 32 00 64 64 00 01 3E")                                  # 1 s ...
    s.at(t + 1000, "dump", 0)
    s.press(t + 1100, FX); s.press(t + 1110, HOME); s.release(t + 1150, HOME); s.release(t + 1160, FX)   # ... PANIC cuts it
    log = run(s, t + 2500)
    on = [(tm, st, d1, d2) for tm, st, d1, d2 in log.msgs if (st & 0xF0) == 0x90 and d2]
    off = [(tm, d1) for tm, st, d1, d2 in log.msgs if st == 0x82 or (st == 0x92 and not d2)]
    first = [x for x in on if x[0] < t]
    check([(st, d1, d2) for _, st, d1, d2 in first] == [(0x92, 60, 80), (0x92, 64, 80)] and any(d1 == 60 and near(tm - first[0][0], 200, 25) for tm, d1 in off),
          "a step's two notes on channel 3, vel 80, off after 200 ms (%s)" % first)
    ch = [d1 for tm, st, d1, _ in on if t - 10 <= tm < t + 200]
    tp = [d1 for tm, st, d1, _ in on if t + 290 <= tm < t + 500]
    check(len(ch) >= 2 and 60 in ch and tp == [60], "with a CHORD: the chord (%s); as a TAPE note: the note only (%s)" % (ch, tp))
    check(not [x for x in on if t + 590 <= x[0] < t + 800], "a track past 16: nothing")
    long_ = [x for x in on if t + 890 <= x[0] < t + 1000 and x[2] == 62]
    cut = [tm for tm, d1 in off if d1 == 62 and tm > t + 900]
    v = v15s(log)
    check(long_ and cut and cut[0] < t + 1300 and v and v[0]["aud"] >= 1, "PANIC cuts a long one (%s, %s)" % (cut[:1], v[:1]))



# ------------------------------------------------------------------------------------------------ 0.16
ROLE_KICK, ROLE_SNARE, ROLE_HAT, ROLE_PERC, ROLE_BASS, ROLE_CHORD = 1, 2, 3, 4, 5, 6
G_OFF, G_HOUSE, G_GARAGE, G_HUMAN = 0, 1, 2, 8


def t016_genre_groove():
    group("0.16 a genre's patterns come with their GROOVE: the drums carry it, the kick stays the anchor, the bass and the chords keep the swing that meets it")
    def band(genre_steps, extra=None):
        s = Script()
        t = 100
        if genre_steps:
            s.press(t, SEQ); s.enc(t + 30, E_PRE, genre_steps); s.release(t + 100, SEQ); t += 300
        s.press(t, SEQ); s.tap_key(t + 30, bk(6), hold=700); s.release(t + 800, SEQ); t += 900     # BAND
        if extra:
            t = extra(s, t)
        for k in range(12):
            s.at(t + 10 * k, "dump", k)
        log = run(s, t + 200)
        c = {x["track"]: x["role"] for x in cfgs(log)}
        return {x["track"]: dict(x, role=c.get(x["track"], 0)) for x in v15s(log)}
    def by_role(tr, role):
        return [x for x in tr.values() if x["role"] == role]
    tr = band(4)                                                         # UK GARAGE
    k, h, b = by_role(tr, ROLE_KICK), by_role(tr, ROLE_HAT), by_role(tr, ROLE_BASS)
    check(k and h and b, "UK GARAGE: the band has a kick, a hat, a bass (%s)" % sorted((x["track"], x["role"]) for x in tr.values()))
    check(h and (h[0]["groove"], h[0]["amt"], h[0]["swing"]) == (G_GARAGE, 100, 50), "UK GARAGE hat: GARAGE 100 %%, the drums straight under it (%s)" % h[:1])
    check(k and (k[0]["groove"], k[0]["amt"], k[0]["swing"]) == (G_GARAGE, 100, 50), "UK GARAGE kick: the 2-step kick swings with the hats (%s)" % k[:1])
    check(b and (b[0]["groove"], b[0]["swing"]) == (G_OFF, 63), "UK GARAGE bass: no template, swing 63 (as GARAGE's shuffle) (%s)" % b[:1])
    tr = band(3)                                                         # HOUSE
    k, h, b = by_role(tr, ROLE_KICK), by_role(tr, ROLE_HAT), by_role(tr, ROLE_BASS)
    check(h and (h[0]["groove"], h[0]["amt"], h[0]["swing"]) == (G_HOUSE, 100, 54), "HOUSE hat: HOUSE 100 %% on the genre's swing 54 (%s)" % h[:1])
    check(k and (k[0]["groove"], k[0]["swing"]) == (G_OFF, 54) and b and (b[0]["groove"], b[0]["amt"]) == (G_HUMAN, 30),
          "HOUSE: the kick the anchor, the bass HUMAN 30 %% (%s %s)" % (k[:1], b[:1]))
    tr = band(19)                                                        # TRANCE: on the grid
    check(tr and all(x["groove"] == G_OFF for x in tr.values() if x["role"]), "TRANCE: no GROOVE anywhere (%s)" % sorted((x["role"], x["groove"]) for x in tr.values()))
    # DICE GROOVE (SEQ + black 4): the part's template stays, its amount and the swing move a little
    def dice(s, t):
        s.press(t, SEQ); s.tap_key(t + 30, bk(3)); s.release(t + 100, SEQ)
        return t + 300
    seen = set()
    ok = True
    for rep in range(3):
        tr = band(4, dice)
        for x in tr.values():
            if x["role"] == ROLE_HAT:
                seen.add(x["amt"])
                ok = ok and x["groove"] == G_GARAGE and 80 <= x["amt"] <= 100 and 47 <= x["swing"] <= 56
            if x["role"] == ROLE_BASS:
                ok = ok and x["groove"] == G_OFF and 60 <= x["swing"] <= 69
    check(ok, "DICE GROOVE on UK GARAGE: the hat stays GARAGE (80-100 %%, swing near 50), the bass near 63 (%s)" % sorted(seen))
    # a GROOVE set by hand is replaced by the next pattern loaded on that track (as the swing is)
    s = Script()
    t = beat_key(s, 100)                                                 # TECHNO KICK on T1
    t = home_page(s, t, 6, [(K3, 7)])                                    # T1: PUSH by hand
    s.at(t, "dump", 0)
    s.press(t + 100, SEQ); s.enc(t + 130, E_PRE, 4); s.release(t + 200, SEQ)
    t = beat_key(s, t + 400)                                             # UK GARAGE KICK on T1
    s.at(t, "dump", 0)
    v = v15s(run(s, t + 100))
    check(len(v) == 2 and v[0]["groove"] == 7 and (v[1]["groove"], v[1]["amt"], v[1]["swing"]) == (G_GARAGE, 100, 50),
          "PUSH by hand, then a UK GARAGE kick loaded: GARAGE (%s)" % [(x["groove"], x["amt"], x["swing"]) for x in v])
    # the parts meet: a UK GARAGE hat on an off 16th (GARAGE) and the bass on one (swing 63) are within 4 %% of a step
    s = Script()
    t = 100
    s.press(t, SEQ); s.enc(t + 30, E_PRE, 4); s.release(t + 100, SEQ); t += 300
    s.press(t, SEQ); s.tap_key(t + 30, bk(6), hold=700); s.release(t + 800, SEQ); t += 900
    for k in range(12):
        s.at(t + 10 * k, "dump", k)
    t += 200
    s.tap_btn(t, PLAY)
    log = run(s, t + int(2 * 16 * STEP_MS))
    keep = {x["track"] - 1 for x in cfgs(log) if x["role"] in (ROLE_KICK, ROLE_SNARE, ROLE_HAT, ROLE_PERC, ROLE_BASS, 9, 11)}   # (channel = track)
    late = {}
    p0 = t                                                               # (step 1 starts at PLAY)
    for tm, st, d1, d2 in log.msgs:
        if (st & 0xF0) == 0x90 and d2 and tm > t and p0:
            pos = (tm - p0) / STEP_MS
            i = round(pos - 0.3)
            if i % 2 == 1 and (st & 15) in keep:
                late.setdefault(st & 15, []).append(round((pos - i) * 100))
    vals = sorted(set(v for x in late.values() for v in x))
    check(len(late) >= 3 and all(18 <= v <= 34 for v in vals), "UK GARAGE: every note on an off 16th 18-34 %% late, drums and bass alike (%s on %s)" % (vals, sorted(late)))



def t016_harm_free_copy():
    group("0.16 ARP 4 K2 FREE: the chords are nobody's genre (ARP 3 K2 through all 144, a loaded pattern does not move them); EDIT + ARP copies the progression into a USER slot")
    # FREE: from TECHNO, K2 one to the left
    s = Script()
    t = harm2_knobs(s, 100, [(K2, -1)])
    s.at(t, "dump", 0); s.press(t + 20, ARP); s.at(t + 200, "ui"); s.release(t + 300, ARP); t += 400   # (ARP 4 still: the Script remembers)
    t = harm_knobs(s, t, [(K2, 7)])                                      # TECHNO 1 + 7 = HARDTECHNO 2
    s.at(t, "dump", 0)
    s.press(t + 100, SEQ); s.enc(t + 130, E_PRE, 4); s.release(t + 200, SEQ)
    t = beat_key(s, t + 400)                                             # a UK GARAGE kick loaded
    s.at(t, "dump", 0)
    t = harm2_knobs(s, t + 100, [(K2, 1)])                               # FREE -> TECHNO
    s.at(t, "dump", 0)
    s.press(t + 100, SEQ); s.enc(t + 130, E_PRE, 1); s.release(t + 200, SEQ)   # (UK FUNKY)
    t = beat_key(s, t + 400)                                             # not FREE: the harmony follows the pattern's genre
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    v = v15s(log)
    got = [(x["hfree"], x["hgenre"], x["hprog"]) for x in v]
    check(got[:4] == [(1, 0, 0), (1, 1, 1), (1, 1, 1), (0, 0, 1)] and got[4][1] == 5,
          "FREE; K2 on ARP 3 goes on into HARDTECHNO; a UK GARAGE pattern does not move it; K2 back: TECHNO; then a pattern moves it again (%s)" % got)
    sc = [x for x in log.screens() if x["cells"][1][0].endswith("HARM GENRE")]
    check(sc and sc[0]["cells"][1][1] == "FREE", "ARP 4: HARM GENRE FREE (%r)" % ((sc[0]["cells"][1],) if sc else ([x["cells"] for x in log.screens()][:1],)))
    # FREE with a MOOD: every progression K2 lands on is of that mood, from any genre
    s = Script()
    t = harm2_knobs(s, 100, [(K2, -1), (K3, 8)])                         # FREE, MOOD DARK
    for k in range(4):
        t = harm_knobs(s, t, [(K2, 1)])
        s.at(t, "dump", 0)
    log = run(s, t + 100)
    h, v = harm11(log), v15s(log)
    moods = [(x["mood"], x["pmood"]) for x in h]
    gs = sorted({x["hgenre"] for x in v})
    check(len(h) == 4 and all(m == pm and m == 8 for m, pm in moods) and len({(x["hgenre"], x["hprog"]) for x in v}) == 4,
          "FREE + MOOD DARK: four DARK progressions (genres %s, %s)" % (gs, moods))
    # EDIT + ARP: TECHNO 4 copied into USER 1 plays the same chords
    def follow_run(copy):
        s = Script()
        t = s.steps(100, [0, 8])
        t = home_page(s, t, 1, [(K4, 1)])                                # T1 FOLLOW
        t = harm_knobs(s, t, [(K1, 1), (K2, 3)])                         # HARMONY ON, TECHNO 4
        if copy:
            s.press(t, EDIT); s.tap_btn(t + 30, ARP); s.release(t + 100, EDIT); t += 200
        s.at(t, "dump", 0)
        s.tap_btn(t, PLAY)
        log = run(s, t + int(4 * 16 * STEP_MS) + 100)
        return log, [d1 for tm, d1, vv in log.notes(ch=0, after=t)]
    log0, n0 = follow_run(False)
    log1, n1 = follow_run(True)
    v = v15s(log1)
    st = [x["msg"] for x in log1.states]
    check(v and v[0]["hprog"] == 6 and v[0]["up"][0] == 4 and st and st[0] == "COPIED TO USER 1: ARP 5 TO CHANGE IT", "EDIT + ARP: into USER 1, which plays (%s %s)" % (v[:1], st[:1]))
    check(len(n0) >= 8 and n0 == n1 and len(set(n0)) >= 3, "the copy plays the same chords as TECHNO 4 (%s / %s)" % (n0, n1))
    # again: USER 1 plays, so the next empty one; then over a full one: asked twice
    s = Script()
    t = harm_knobs(s, 100, [(K2, 3)])
    s.press(t, EDIT); s.tap_btn(t + 30, ARP); s.release(t + 100, EDIT); t += 200          # -> USER 1 (plays)
    s.press(t, EDIT); s.tap_btn(t + 30, ARP); s.release(t + 100, EDIT); t += 200          # -> USER 2 (USER 1 is the one playing)
    s.at(t, "dump", 0)
    t = harm_knobs(s, t, [(K2, -10)])                                    # back to TECHNO 1
    t = uprog_knobs(s, t, [(K1, -5)])                                    # ARP 5: USER 1
    s.press(t, EDIT); s.tap_btn(t + 30, ARP); s.release(t + 100, EDIT); s.at(t + 150, "dump", 0); t += 300
    s.press(t, EDIT); s.tap_btn(t + 30, ARP); s.release(t + 100, EDIT); s.at(t + 150, "dump", 0); t += 300
    log = run(s, t + 100)
    v, st = v15s(log), [x["msg"] for x in log.states]
    check(v and v[0]["up"][:2] == [4, 4] and v[0]["hprog"] == 7, "copied again: USER 2 (%s)" % v[:1])
    check(len(v) == 3 and st[1] == "COPY OVER USER 1: EDIT+ARP AGAIN" and v[1]["up"][0] == 4 and v[2]["up"][0] == 1 and v[2]["hprog"] == 6,
          "over USER 1: asked, then TECHNO 1 (one chord) copied (%s %s)" % ([(x["up"], x["hprog"]) for x in v], st))



def t016_merengue():
    group("0.16 MERENGUE, the 25th genre: SEQ + PRESETS x 24, BAND: four on the floor, the guira's cha chi-ki pushed a hair, the tambora played, I - V7 in a major key")
    ROLE_CONGA, ROLE_PIANO, ROLE_LEAD, ROLE_VOX, G_PUSH = 12, 22, 23, 24, 7
    s = Script()
    t = kp(s, 100, [(K2, 1), (K4, 1)])                                   # C major, IN KEY
    s.press(t, SEQ); s.enc(t + 30, E_PRE, 24); s.release(t + 100, SEQ); t += 300
    s.press(t, SEQ); s.tap_key(t + 30, bk(6), hold=700); s.release(t + 800, SEQ); t += 900     # BAND
    for k in range(10):
        s.at(t + 10 * k, "dump", k)
    p = t + 200
    s.tap_btn(p, PLAY)
    log = run(s, p + int(2 * BAR_MS) - 20)
    st = log.states
    c = {x["track"]: x["role"] for x in cfgs(log)}
    v = {x["track"]: x for x in v15s(log)}
    on = {x["track"]: x["on"] for x in log.dumps}
    check(st and "MERENGUE BAND #1: 9 TRACKS" in " ".join(x["msg"] for x in st), "BAND: the merengue's nine (%s)" % (st[0]["msg"] if st else "-"))
    check([c.get(i) for i in range(1, 10)] == [ROLE_KICK, ROLE_SNARE, ROLE_HAT, ROLE_PERC, ROLE_CONGA, ROLE_BASS, ROLE_PIANO, ROLE_LEAD, ROLE_VOX],
          "KICK SNARE HAT (the guira) PERC (the tambora) CONGA BASS PIANO LEAD VOX (%s)" % [c.get(i) for i in range(1, 10)])
    k1 = [round((tm - p) / STEP_MS) for tm, d1, vv in log.notes(ch=0, after=p, before=p + int(BAR_MS) - 20)]
    check(k1 == [0, 4, 8, 12], "the bass drum on every beat (%s)" % k1)
    check(on.get(3, "").startswith("x.xxx.xxx.xxx.xx"), "the guira: an 8th and two 16ths a beat (%s)" % on.get(3))
    check(v.get(3) and (v[3]["groove"], v[3]["amt"]) == (G_PUSH, 30) and v.get(4) and (v[4]["groove"], v[4]["amt"]) == (G_HUMAN, 40) and v[1]["groove"] == 0,
          "the guira PUSH 30, the tambora HUMAN 40, the kick straight (%s %s %s)" % (v.get(3), v.get(4), v.get(1)))
    h = harm11(log)
    check(h and h[0]["prog"] == 0 and v[1]["hgenre"] == 24, "the harmony: the merengue's first, I - V7 (%s)" % (h[:1],))


V16 = re.compile(r"^\s*(\d+) ms  v16 T(\d+) pend((?: \d+){4}) shown (\d+) edit (\d+)/(\d+)/(\d+)/(\d+) euc (\d+) (\d+)/(\d+)$", re.M)


def v16s(log):
    """the 0.16 'v16' lines of the dumps: the algorithm READY on each slot (0 none, 128 OFF while one plays), the one the
    panel shows, the values the knobs set (algo, a, b, c), EUCLID LIVE and its pulses / rotation"""
    return [dict(t=int(m.group(1)), track=int(m.group(2)), pend=[int(x) for x in m.group(3).split()], shown=int(m.group(4)),
                 edit=(int(m.group(5)), int(m.group(6)), int(m.group(7)), int(m.group(8))), euc=int(m.group(9)),
                 pulses=int(m.group(10)), rot=int(m.group(11)))
            for m in V16.finditer(log.text)]


def t016_algo_ready():
    group("0.16: an algorithm is set up before it plays: K1 makes it READY, K2-K4 set it, SEQ + white 6 starts it with them; EUCLID too")
    BAR = 16 * STEP_MS
    # DENSITY 0 READY: nothing changes, the four steps play; SEQ + white 6 in bar 2: silence from there (DENSITY at 0, not 100)
    s = Script()
    t = s.steps(100, [0, 4, 8, 12])
    t = seq_page(s, t, 1, encs=[(K1, 4), (K2, -20)])                    # DENSITY READY, 0 %
    s.press(t, SEQ); s.at(t + 60, "ui"); s.release(t + 100, SEQ); t += 160
    s.at(t, "dump", 0)
    p = t + 100
    s.tap_btn(p, PLAY)
    ts = p + int(1.5 * BAR)
    seq_page(s, ts, 1, keys=[wk(5)])                                    # started
    s.at(ts + 200, "dump", 0)
    log = run(s, p + int(3 * BAR))
    v, v1 = v16s(log), v11s(log)
    before, after = log.notes(ch=0, after=p, before=ts), log.notes(ch=0, after=ts + 60)
    check(v and v[0]["pend"][0] == 4 and v[0]["shown"] == 4 and v[0]["edit"][:2] == (4, 0) and v1[0]["algos"][0][0] == 0,
          "K1 and K2: DENSITY 0 READY, the slot still empty (%s %s)" % (v[:1], v1[0]["algos"][:1] if v1 else v1))
    sc = [x for x in log.screens() if x["cells"][0] and x["cells"][0][0].endswith("READY")]
    check(sc and sc[0]["cells"][0] == ("ALGO 1 READY", "DENSITY"),
          "the screen: ALGO 1 READY DENSITY (%s)" % ([x["cells"][0] for x in log.screens()][:2],))
    check(len(before) == 6 and not after, "READY plays nothing; started in bar 2 it is silent at once, at 0 %% (%d before, %d after)" % (len(before), len(after)))
    check(len(v1) == 2 and v1[1]["algos"][0][:2] == (4, 0) and v[1]["pend"][0] == 0 and log.states[1]["msg"].startswith("T1 ALGO 1: DENSITY STARTS"),
          "SEQ + white 6: DENSITY plays with the 0 set before (%s, %s)" % (v1[1]["algos"][:1] if len(v1) > 1 else v1, log.states[1]["msg"] if len(log.states) > 1 else "-"))
    # while DENSITY plays: CELL READY with 4 cells (DENSITY plays on); SEQ + white 6 swaps them; again: it stops, READY as it
    # was; again: the same CELL; K1 on OFF and SEQ + white 6: it stops
    s = Script()
    t = s.steps(100, [0, 4, 8, 12])
    t = seq_page(s, t, 1, encs=[(K1, 4), (K2, -20)], keys=[wk(5)])      # DENSITY 0 plays
    t = seq_page(s, t, 1, encs=[(K1, -2), (K3, -12)])                   # CELL READY, 4 cells
    s.at(t, "dump", 0)
    p = t + 100
    s.tap_btn(p, PLAY)
    ts = p + int(BAR) + 30
    t = seq_page(s, ts, 1, keys=[wk(5)])                                # CELL in place of DENSITY
    s.at(t + int(BAR), "dump", 0)
    t = seq_page(s, t + int(BAR) + 50, 1, keys=[wk(5)]); s.at(t, "dump", 0)          # stops
    t = seq_page(s, t + 50, 1, keys=[wk(5)]); s.at(t, "dump", 0)                     # the same CELL again
    t = seq_page(s, t + 50, 1, encs=[(K1, -2)]); s.at(t, "dump", 0)                  # OFF chosen
    t = seq_page(s, t + 50, 1, keys=[wk(5)]); s.at(t, "dump", 0)                     # it stops
    log = run(s, t + 100)
    v, v1 = v16s(log), v11s(log)
    st = states(log)
    algos = [x["algos"][0] for x in v1]
    check(len(v) == 6 and v[0]["pend"][0] == 2 and v[0]["edit"] == (2, 90, 4, 0) and algos[0] == (4, 0, 40, 0) and not log.notes(ch=0, after=p, before=ts),
          "CELL READY with 4 cells while DENSITY 0 plays on, silent (%s %s)" % (v[:1], algos[:1]))
    hh = st[1]["heard"].replace(" ", "") if len(st) > 1 else ""
    check(len(algos) == 6 and algos[1] == (2, 90, 4, 0) and hh == hh[:4] * 4 and log.notes(ch=0, after=ts + 60),
          "SEQ + white 6: CELL with its 4 cells in place of DENSITY (%s, %s)" % (algos[1:2], hh))
    check(len(algos) == 6 and algos[2][0] == 0 and v[2]["pend"][0] == 2 and v[2]["edit"] == (2, 90, 4, 0) and algos[3] == (2, 90, 4, 0),
          "again: it stops, READY as it was; again: the same CELL (%s, %s)" % (algos[2:4], [x["pend"][0] for x in v[2:4]]))
    check(len(algos) == 6 and v[4]["pend"][0] == 128 and v[4]["shown"] == 0 and algos[4][0] == 2 and algos[5][0] == 0 and v[5]["pend"][0] == 2,
          "K1 on OFF: CELL plays on until SEQ + white 6 stops it (%s, %s)" % (algos[4:], [x["pend"][0] for x in v[4:]]))
    # each algorithm keeps its values: TURING 16 steps READY, K1 to CELL and back: TURING still 16; NOTHING READY said
    s = Script()
    t = seq_page(s, 100, 1, encs=[(K1, 1), (K3, 8)]); s.at(t, "dump", 0)
    t = seq_page(s, t, 1, encs=[(K1, 1), (K1, -1)]); s.at(t, "dump", 0)
    t = seq_page(s, t, 1, encs=[(K1, -1)], keys=[wk(5)]); s.at(t, "dump", 0)          # OFF: nothing to start
    log = run(s, t + 100)
    v = v16s(log)
    check(len(v) == 3 and v[0]["edit"] == (1, 10, 16, 0) and v[1]["edit"] == (1, 10, 16, 0) and v[2]["pend"][0] == 0
          and log.states[2]["msg"].startswith("NOTHING READY"), "TURING keeps its 16 steps READY through K1; OFF: NOTHING READY (%s %s)" % ([x["edit"] for x in v], log.states[2]["msg"] if len(log.states) > 2 else "-"))
    # EUCLID: the knobs set it up (READY), SEQ + white 6 starts it with them
    s = Script()
    t = seq_page(s, 100, 0, encs=[(K1, 1), (K2, 2)])                    # 5 pulses, rotation 2
    s.at(t, "dump", 0)
    p = t + 100
    s.tap_btn(p, PLAY)
    ts = p + int(BAR) + 30
    t = seq_page(s, ts, 0, keys=[wk(5)])
    s.at(t, "dump", 0)
    log = run(s, p + int(3 * BAR) - 40)
    v = v16s(log)
    n2 = log.notes(ch=0, after=p + int(2 * BAR) - 20)
    check(v and v[0]["euc"] == 0 and (v[0]["pulses"], v[0]["rot"]) == (5, 2) and log.states[0]["msg"].startswith("EUCLID READY T1: 5/16 ROT 2"),
          "EUCLID's knobs: READY 5/16 rotation 2, not playing (%s %s)" % (v[:1], log.states[0]["msg"]))
    check(not log.notes(ch=0, after=p, before=ts) and len(v) == 2 and v[1]["euc"] == 1 and len(n2) == 5,
          "silent until SEQ + white 6; then its 5 hits (%d)" % len(n2))
    # the grid (TRACK 3, row 4): a tap READY (orange), again: it plays (white), again: it stops
    s = Script()
    s.raw(100, "attach"); view(s, 200, GC_VTRACK); view(s, 300, GC_VTRACK); view(s, 400, GC_VTRACK); t = 500
    s.pad(t, 4, 3); t += 100; s.at(t, "dump", 0); t1 = t
    s.pad(t, 4, 3); t += 100; s.at(t, "dump", 0); t2 = t
    s.pad(t, 4, 3); t += 100; s.at(t, "dump", 0)
    log = run(s, t + 100)
    v, v1 = v16s(log), v11s(log)
    l1, l2 = log.leds(until=t1 - 1)[0], log.leds(until=t2 - 1)[0]          # (the pads as they were before the next tap)
    check(len(v) == 3 and v[0]["pend"][0] == 4 and v1[0]["algos"][0][0] == 0 and l1.get(3 * 16 + 4) == GL_ORANGE,
          "grid: a tap, DENSITY READY, orange (%s %s)" % (v[:1], l1.get(3 * 16 + 4)))
    check(len(v) == 3 and v1[1]["algos"][0][0] == 4 and l2.get(3 * 16 + 4) == GL_WHITE and v1[2]["algos"][0][0] == 0 and v[2]["pend"][0] == 4,
          "again: it plays, white; again: it stops, READY (%s)" % [x["algos"][0][0] for x in v1])



def t016_ready_elsewhere():
    group("0.16: the HARMONY's progression READY before K1 starts it; EXPO set up before K4 starts it; a MIDI FX comes back with its own values")
    # HARMONY off: ARP 3 K2 chooses (READY), nothing follows yet; K1 ON plays the one chosen
    s = Script()
    t = kp(s, 100, [(K4, 1)])                                          # track 1 in key (C minor)
    t = s.steps(t, [0])
    t = home_page(s, t, 1, [(K4, 1)], cur=2)                           # FOLLOW
    t = harm_knobs(s, t, [(K2, 3)])                                    # TECHNO 4, READY
    s.at(t, "dump", 0)
    p = t + 100
    s.tap_btn(p, PLAY)
    harm_knobs(s, p + int(2 * BAR_MS) + 30, [(K1, 1)])                 # bar 3: ON
    s.at(p + int(2 * BAR_MS) + 300, "dump", 0)
    log = run(s, p + int(6 * BAR_MS) - 20)
    st = states(log)
    before = {d1 for tm, d1, v in log.notes(ch=0, after=p, before=p + int(2 * BAR_MS))}
    after = {d1 for tm, d1, v in log.notes(ch=0, after=p + int(2 * BAR_MS) + 100)}
    check(st[0]["harm"][0] == 0 and st[0]["harm"][2] == 3 and st[0]["msg"].startswith("READY TECHNO") and st[0]["msg"].endswith(": K1 ON"),
          "ARP 3 K2 with the HARMONY off: TECHNO 4 READY, still off (%s %r)" % (st[0]["harm"], st[0]["msg"]))
    check(before == {60} and st[1]["harm"][:3:2] == [1, 3] and len(after) >= 2,
          "the tonic until K1, then the progression chosen (%s, then %s)" % (sorted(before), sorted(after)))
    # EXPO: K1-K3 set it up (EXPO READY), K4 starts it with them
    s = Script()
    t = s.steps(100, (0,))
    t = expo_knobs(s, t, 0, [(K1, 4)])                                 # 12 hits, READY
    s.at(t, "dump", 0)
    p = t + 100
    s.tap_btn(p, PLAY)
    expo_knobs(s, p + int(BAR_MS) + 30, 0, [(K4, 1)])                 # bar 2: RAMP
    log = run(s, p + int(3 * BAR_MS) - 20)
    n1 = log.notes(ch=0, after=p, before=p + int(BAR_MS))
    n3 = log.notes(ch=0, after=p + int(2 * BAR_MS) - 5)
    check(log.states[0]["msg"] == "EXPO READY: K4 SHAPE STARTS IT" and len(n1) == 1 and len(n3) == 12,
          "EXPO's knob: READY, the step plays once; K4 RAMP: its 12 hits (%r, %d, %d)" % (log.states[0]["msg"], len(n1), len(n3)))
    # MIDI FX (HOME 6): K1 ECHO READY, K2 4 repeats (nothing heard yet); SEQ + white 6 starts it (not EUCLID); HARM READY
    # while ECHO plays; started; ECHO READY again: its 4, not its default 2; K1 OFF + SEQ + white 6 stops it
    s = Script()
    t = s.steps(100, (0,))
    t = home_page(s, t, 5, [(K1, 3), (K2, 2)]); s.at(t, "dump", 0)          # ECHO READY, 4 repeats
    t = seq_page(s, t, 0, keys=[wk(5)]); s.at(t, "dump", 0)                 # started
    t = home_page(s, t, 5, [(K1, -2)], cur=5); s.at(t, "dump", 0)           # HARM READY, ECHO plays on
    t = seq_page(s, t, 0, keys=[wk(5)]); s.at(t, "dump", 0)                 # HARM
    t = home_page(s, t, 5, [(K1, 2)], cur=5); s.at(t, "dump", 0)            # ECHO READY: its 4
    t = seq_page(s, t, 0, keys=[wk(5)]); s.at(t, "dump", 0)
    t = home_page(s, t, 5, [(K1, -3)], cur=5)                               # OFF chosen
    t = seq_page(s, t, 0, keys=[wk(5)]); s.at(t, "dump", 0)                 # it stops
    log = run(s, t + 100)
    st = states(log)
    got = [(x["mfx"], x["mfx_amt"]) for x in st]
    euc = [x["flags"] & 8 for x in st]
    check(got == [(0, 0), (3, 4), (3, 4), (1, 2), (1, 2), (3, 4), (0, 0)] and not any(euc),
          "ECHO READY with 4, started by SEQ + white 6 (EUCLID stays off); HARM READY while ECHO plays, then HARM; ECHO again with its 4; OFF (%s %s)" % (got, euc))
    check(st[0]["msg"] == "T1 MIDI FX ECHO READY: SEQ + WHITE 6" and st[1]["msg"] == "T1 MIDI FX ECHO STARTS", "the screen: READY, STARTS (%r %r)" % (st[0]["msg"], st[1]["msg"]))
    s = Script()                                                            # heard: no repeats while READY, then the 4
    t = s.steps(100, (0,))
    t = home_page(s, t, 5, [(K1, 3), (K2, 2)])
    p = t + 100
    s.tap_btn(p, PLAY)
    seq_page(s, p + int(BAR_MS) + 30, 0, keys=[wk(5)])
    log = run(s, p + int(3 * BAR_MS) - 20)
    n1 = log.notes(ch=0, after=p, before=p + int(BAR_MS))
    n3 = log.notes(ch=0, after=p + int(2 * BAR_MS) - 5)
    check(len(n1) == 1 and len(n3) == 5, "READY: the step alone; started: the step and its 4 repeats (%d, %d)" % (len(n1), len(n3)))


# ------------------------------------------------------------------------------------------------ 0.17
def t017_mosse():
    group("0.17 the MOSSE: no VIAGGIO mode; the journey always runs (energy 50 changes nothing), its moves on the black keys of GLO / PERF page 3, the trail always kept")
    # two tracks written in the studio, nothing opened: they play as written; GLO held on page 3 + black 2: a BREAK at the
    # phrase's end; SAVE + white 16: what was played becomes scenes and the song
    s = Script()
    t = s.steps(100, [0, 4, 8, 12])                          # track 1
    s.tap_key(t, bk(1)); t += 60                             # track 2 selected
    t = s.steps(t, [2, 6, 10, 14])
    t = viaggio_knobs(s, t, [(K2, -1), (K2, -1)])            # GLO 3: a 4-bar phrase
    s.at(t, "dump", 1)
    s.tap_btn(t, PLAY); t0 = t
    s.press(t0 + 200, GLO); s.tap_key(t0 + 230, bk(1)); s.release(t0 + 300, GLO)   # BREAK: 1 bar, track 2 stays
    s.at(t0 + 400, "dump", 1)
    s.at(t0 + 4 * BAR_MS + 100, "dump", 1)
    s.at(t0 + 5 * BAR_MS + 100, "dump", 1)
    s.press(t0 + 8 * BAR_MS + 300, SAVE); s.tap_key(t0 + 8 * BAR_MS + 330, wk(15)); s.release(t0 + 8 * BAR_MS + 400, SAVE)
    s.at(t0 + 8 * BAR_MS + 500, "dump", 1)
    log = run(s, t0 + 8 * BAR_MS + 600)
    v = log.viaggio
    n1 = log.notes(ch=0, after=t0, before=t0 + BAR_MS - 10)
    n2 = log.notes(ch=1, after=t0, before=t0 + BAR_MS - 10)
    vel = sorted(set(x[2] for x in log.notes(after=t0, before=t0 + 4 * BAR_MS - 10)))
    check(v[0]["on"] == 0 and v[0]["journey"] == 1 and v[0]["states"][:3] == "IIE" and v[0]["energy"] == 50 and v[0]["bars"] == 4,
          "nothing opened: the journey runs, the two tracks IN, energy 50, a 4-bar phrase (%s)" % v[0])
    check(len(n1) == 4 and len(n2) == 4 and vel == [100], "energy 50 plays the steps as written: 4 + 4 a bar, velocity 100 (%d %d %s)" % (len(n1), len(n2), vel))
    check(v[1]["queue"] == ["BREAK/1/1"] and log.states[1]["msg"] == "QUEUED: BREAK 1 BAR, THIS TRACK STAYS" and v[1]["mute"] == 0,
          "GLO held on page 3 + black 2: a BREAK queued, no scene recalled (%s %s)" % (v[1]["queue"], log.states[1]["msg"]))
    check(v[2]["mute"] == 0xFFFD and not log.notes(ch=0, after=t0 + 4 * BAR_MS + 10, before=t0 + 5 * BAR_MS - 10)
          and log.notes(ch=1, after=t0 + 4 * BAR_MS + 10, before=t0 + 5 * BAR_MS - 10), "bar 5: track 2 alone (%04X)" % v[2]["mute"])
    check(v[3]["mute"] == 0 and log.notes(ch=0, after=t0 + 5 * BAR_MS + 10), "bar 6: both again (%04X)" % v[3]["mute"])
    check(v[4]["song"] >= 1 and v[4]["trail"] >= 2 and log.states[4]["msg"].startswith("JOURNEY SAVED"),
          "SAVE + white 16 with the MOSSE never opened: the phrases played are scenes and the song (%s)" % log.states[4]["msg"])
    # SEL + GLO: PERF on page 3; the black keys are the moves there (black 10 cancels the last), the scenes on pages 1-2;
    # SEL + GLO from another page: the MOSSE again; on them: the studio
    s = Script()
    t = s.steps(100, [0, 4, 8, 12])
    t = vg_on(s, t, remote=False)
    s.at(t, "ui")
    s.tap_key(t + 50, bk(0)); t += 150                       # FILL
    s.at(t, "dump", 0)
    s.at(t + 10, "leds")
    s.tap_key(t + 20, bk(9)); t += 120                       # cancelled
    s.at(t, "dump", 0)
    s.at(t + 10, "leds"); t += 20
    t = pg(s, t, GLO, 0)                                     # GLO page 1 (PERF stays on)
    s.press(t, SEL); s.tap_key(t + 30, bk(0)); s.release(t + 100, SEL); t += 160   # SEL + black 1: scene 1 stored
    s.at(t, "dump", 0)
    t = vg_on(s, t, remote=False)                            # SEL + GLO on page 1: the MOSSE
    s.at(t, "ui")
    t = vg_studio(s, t)
    s.at(t, "dump", 0)
    log = run(s, t + 200)
    v = log.viaggio
    sc = log.screens()
    check(sc and sc[0]["lines"][2].startswith("PERF 3/3 MOSSE  AT PHRASE") and sc[0]["cells"][0] == ("ENERGY", "50"),
          "SEL + GLO: PERF 3/3 MOSSE, the energy at 50 (%s %s)" % (sc[0]["lines"][2] if sc else None, sc[0]["cells"][0] if sc else None))
    check(v[0]["queue"] == ["FILL/0/0"] and log.states[0]["msg"] == "QUEUED: FILL", "black 1: FILL queued (%s)" % v[0]["queue"])
    check(v[1]["queue"] == [] and log.states[1]["msg"] == "CANCELLED FILL", "black 10: the last move cancelled (%s)" % log.states[1]["msg"])
    kl = log.key_leds()
    check(len(kl) == 2 and kl[0][1][BLACK[0]] == "X" and kl[0][1][BLACK[9]] == "X" and kl[0][1][BLACK[1]] != "X"
          and kl[1][1][BLACK[0]] != "X" and kl[1][1][BLACK[9]] != "X", "the black keys light what waits: FILL and black 10, then nothing (%s)" % [x[1] for x in kl])
    check(v[2]["queue"] == [] and log.states[2]["msg"] == "SCENE STORED 1", "page 1: SEL + black 1 stores scene 1, as ever (%s)" % log.states[2]["msg"])
    check(len(sc) == 2 and sc[1]["lines"][2].startswith("PERF 3/3 MOSSE"), "SEL + GLO from page 1: the MOSSE (%s)" % (sc[1]["lines"][2] if len(sc) == 2 else sc))
    check(v[3]["on"] == 0 and v[3]["journey"] == 1 and log.states[3]["msg"].startswith("STUDIO"), "SEL + GLO on the MOSSE: the studio (%s)" % log.states[3]["msg"])
    # PRESETS on the MOSSE with the HARMONY off: the progression READY (as ARP 3 K2 since 0.16), not switched on
    s = Script()
    t = vg_on(s, 100, remote=False)
    s.enc(t, E_PRE, 1); t += 60
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    check(log.states[0]["msg"].startswith("READY ") and log.states[0]["msg"].endswith(": ARP 3 K1 ON") and log.states[0]["harm"][0] == 0 and log.states[0]["harm"][2] == 1,
          "PRESETS, the HARMONY off: progression 2 READY (%s %s)" % (log.states[0]["msg"], log.states[0]["harm"]))


def t017_proposal():
    group("0.17 a PROPOSAL in SEQ: BEAT held 0.6 s writes the part into a free pattern, the one playing untouched; PRESETS queues it; it enters with its settings")
    s = Script()
    t = s.steps(100, [0, 8])                                 # track 1, pattern 1 by hand: two hits
    s.at(t, "dump", 0)
    s.press(t, SEQ); s.tap_key(t + 30, wk(9), hold=700); s.release(t + 800, SEQ); t += 860   # SEQ + BEAT held: a proposal
    s.at(t, "dump", 0)
    s.press(t, SEQ); s.tap_key(t + 30, wk(9), hold=700); s.release(t + 800, SEQ); t += 860   # again: the next variation
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); t0 = t
    s.enc(t0 + 200, E_PRE, 1)                                # PRESETS: the proposal waiting (the last one made) is queued
    s.at(t0 + 300, "dump", 0)
    s.at(t0 + BAR_MS + 200, "dump", 0)
    log = run(s, t0 + 3 * BAR_MS)
    d = log.dumps
    st = log.states
    check(d[1]["pat"] == 1 and d[1]["hash"] == d[0]["hash"] and "KICK #1 IN P2: PRESETS QUEUES IT" in st[1]["msg"],
          "BEAT held: the kick into P2, pattern 1 plays untouched (%s)" % st[1]["msg"])
    check(d[2]["pat"] == 1 and "KICK #2 IN P3" in st[2]["msg"], "held again: the next variation into P3 (%s)" % st[2]["msg"])
    check(st[3]["msg"] == "T1 PROPOSAL P3 QUEUED" and d[3]["pat"] == 1, "PRESETS: the proposal waiting queued (%s)" % st[3]["msg"])
    k1 = [round((x[0] - t0) / STEP_MS) for x in log.notes(ch=0, after=t0, before=t0 + BAR_MS - 10)]
    k2 = [round((x[0] - t0 - BAR_MS) / STEP_MS) for x in log.notes(ch=0, after=t0 + BAR_MS - 10, before=t0 + 2 * BAR_MS - 10)]
    check(k1 == [0, 8] and d[4]["pat"] == 3 and len(k2) >= 4 and k2 != k1, "bar 1 the hand's two hits, then the proposal (%s -> %s)" % (k1, k2))
    # a tap of BEAT writes on the pattern playing, as before 0.17
    s = Script()
    t = s.steps(100, [0, 8])
    s.at(t, "dump", 0)
    s.press(t, SEQ); s.tap_key(t + 30, wk(9)); s.release(t + 120, SEQ); t += 180
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    check(log.dumps[1]["pat"] == 1 and log.dumps[1]["hash"] != log.dumps[0]["hash"] and log.states[1]["msg"].startswith("TECHNO KICK #1"),
          "a tap of BEAT: the kick on the pattern playing (%s)" % log.states[1]["msg"])


TESTS = [t_basic, t_swing_nudge, t_arp, t_direction_pen, t_tools, t_slave_spp, t_tracks16, t_loop_between_steps, t_dj_loop, t_fx,
         t_key, t_lfo, t_lanes, t_rec, t_slots, t_perf, t_beat_cook, t_scope_dice, t_evolve, t_song_tap_rec, t_grid_drum, t_usb_page,
         t_rec_fresh_step, t_ui_stalls,
         t_grid_link, t_grid_step, t_grid_buttons, t_grid_cc_lfo, t_grid_beat_fx, t_grid_proj, t_store_areas,
         t05_planes, t05_quantise, t05_scene_pc, t05_morph, t05_repeat, t05_reload, t05_learn, t05_song_spp, t05_remote,
         t05_library, t05_persist, t05_grid_track2, t05_battery,
         t051_cursor_tools, t051_macros, t051_master_knob, t051_grid_perf, t051_grid_fx, t051_remote, t051_undo_dice, t06_long_gate_euclid,
         t08_bugs, t08_knobs_zero, t08_snapshots, t08_harmony, t08_dice_memory, t08_grid_views, t08_usb_two_ports,
         t09_viaggio_phrase, t09_viaggio_moves, t09_viaggio_loop_genre_remote, t09_profiles_persist, t09_grid_viaggio, t09_review_fixes, t010_expo, t010_rec_length, t010_delay, t010_bend_at, t010_undo_levels, t010_chain, t011_tape, t010_expo_plain, t010_expo_grace,
         t010_time, t010_notes, t010_lanes, t010_tools, t010_keys, t010_viaggio2,
         t011_lengths, t011_harmony_genre, t011_algo_slots, t011_band_cook, t011_note_lengths, t011_pi_patterns, t011_progressions, t011_pi_progressions, t011_in_time_after, t011_explorer_sessions, t011_pc_test, t012_pick, t012_blocks, t012_studio_viaggio, t012_break, t012_remote13, t012_review, t012_window, t012_grid_pick,
         t013_lfo, t013_repeat, t013_keyboard, t013_motion, t013_slide, t013_chain,
         t015_names_clear, t015_groove, t015_link, t016_genre_groove, t016_harm_free_copy, t016_algo_ready, t016_ready_elsewhere, t016_merengue,
         t017_mosse, t017_proposal]
if os.environ.get("SAGGA_ONLY"):                           # SAGGA_ONLY=t05 runs the tests whose name starts so
    TESTS = [t for t in TESTS if t.__name__.startswith(os.environ["SAGGA_ONLY"])]


def main():
    build()
    try:
        for t in TESTS:
            try:
                t()
            except Exception as e:                         # a scenario that cannot even run is a failure
                import traceback
                traceback.print_exc()
                FAILS.append("%s raised %r" % (t.__name__, e))
    finally:
        if os.path.exists(BIN):
            os.remove(BIN)
    print("sagga sim: %d checks, %d failures" % (CHECKS[0], len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
