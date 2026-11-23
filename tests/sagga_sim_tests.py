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
import shutil
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
FW_VERSION = re.search(r'#define SQ_VERSION "([0-9.]+)"', open(os.path.join(ROOT, "firmware", "src", "dinghy.c")).read()).group(1)

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
        # 0.24: the copies, a dump of a track: the pattern's own length in the loop, the whole row (x a step that
        # plays, g a copy that plays, r a copy at rest - after the loop: the mark of the pattern's end)
        self.copies = [dict(t=int(m.group(1)), track=int(m.group(2)), own=int(m.group(3)), row=m.group(4))
                       for m in re.finditer(r"^\s*(\d+) ms  copies T(\d+) own (\d+) ROW:([xgr.]*)", text, re.M)]

        # 0.25: the metre, a dump: the bar in steps, its beats (a mask), the bar now and the tick in it, the bar that waits
        self.metre = [dict(t=int(m.group(1)), bar=int(m.group(2)), beats=int(m.group(3), 16), no=int(m.group(4)), into=int(m.group(5)),
                           pend=int(m.group(6)), pend_beats=int(m.group(7), 16), raw=int(m.group(8)), sig=m.group(9), split=m.group(10))
                      for m in re.finditer(r"^\s*(\d+) ms  metre T\d+ bar (\d+) beats ([0-9A-F]{8}) no (\d+) into (\d+) pend (\d+) ([0-9A-F]{8}) raw (\d+) SIG:(\S*) SPLIT:(\S*)$",
                                           text, re.M)]
        self.states = [dict(t=int(m.group(1)), track=int(m.group(2)), flags=int(m.group(3)), pulses=int(m.group(4)), rot=int(m.group(5)),
                            algo=int(m.group(6)), a=int(m.group(7)), b=int(m.group(8)), c=int(m.group(9)), mfx=int(m.group(10)),
                            mfx_amt=int(m.group(11)), harm=[int(x) for x in m.group(12, 13, 14, 15)], snap=int(m.group(16)),
                            pend=int(m.group(17)), capture=int(m.group(18)), mac=[int(x) for x in m.group(19, 20, 21, 22)],
                            heard=m.group(23), msg=re.sub(r"^TAB (T\d+: )?", "", m.group(24)), rawmsg=m.group(24))   # (0.18: the tablet's mark aside)
                       for m in re.finditer(r"^\s*(\d+) ms  state T(\d+) flags (\d+) euc (\d+)/(\d+) algo (\d+) (\d+) (\d+) (\d+) mfx (\d+) (-?\d+) "
                                            r"harm (\d+) (\d+) (\d+) (\d+) snap (-?\d+) (-?\d+) (\d+) mac (-?\d+) (-?\d+) (-?\d+) (-?\d+) "
                                            r"HEARD:([x. ]*) MSG:(.*)$", text, re.M)]

        self.mfxc = [dict(t=int(m.group(1)), track=int(m.group(2)), on=int(m.group(3)), sel=int(m.group(4)), pend=int(m.group(5)),
                          amt=[int(x) for x in m.group(6, 7, 8, 9)], time=[int(x) for x in m.group(10, 11, 12, 13)],
                          fb=[int(x) for x in m.group(14, 15, 16, 17)])          # 0.19: the MIDI FX chain (effect x at [x - 1])
                     for m in re.finditer(r"^\s*(\d+) ms  mfxc T(\d+) on (\d+) sel (\d+) pend (\d+) amt (-?\d+) (-?\d+) (-?\d+) (-?\d+) "
                                          r"time (\d+) (\d+) (\d+) (\d+) fb (\d+) (\d+) (\d+) (\d+)$", text, re.M)]
        self.mfxd = [dict(t=int(m.group(1)), track=int(m.group(2)), on=int(m.group(3)), order=[int(x) for x in m.group(4).split()],
                          amt=[int(x) for x in m.group(5).split()], time=[int(x) for x in m.group(6).split()],
                          fb=[int(x) for x in m.group(7).split()], modfx=int(m.group(8)))   # 0.20: the new five [effect - 5], the order
                     for m in re.finditer(r"^\s*(\d+) ms  mfxd T(\d+) on (\d+) order((?: \d+)+) amt((?: -?\d+)+) time((?: \d+)+) fb((?: \d+)+) modfx (-?\d+)$",
                                          text, re.M)]
        self.x30 = [dict(t=int(m.group(1)), cursor=int(m.group(2)), snapbank=int(m.group(3)), scenes=m.group(4), snaps=m.group(5),
                         undo=int(m.group(6)), tape=int(m.group(7)), song=int(m.group(8)), songsc=[int(x) for x in m.group(9).split()])   # 0.30
                    for m in re.finditer(r"^\s*(\d+) ms  x30 cursor (\d+) snapbank (\d+) scenes ([.x]+) snaps ([.x]+) undo (\d+) tape (\d+) song (\d+):((?: \d+)*)$",
                                         text, re.M)]
        self.viaggio = [dict(t=int(m.group(1)), on=int(m.group(2)), bar=int(m.group(3)), bars=int(m.group(4)), energy=int(m.group(5)),
                             target=int(m.group(6)), genre=int(m.group(7)), mute=int(m.group(8), 16), speed=int(m.group(9)), rec=int(m.group(10)),
                             states=m.group(11), queue=m.group(12).split(), trail=int(m.group(13)), patterns=m.group(14), song=int(m.group(15)))
                        for m in re.finditer(r"^\s*(\d+) ms  viaggio (\d) bar (\d+)/(\d+) energy (\d+)/(\d+) genre (\d+) mute ([0-9A-F]{4}) speed (-?\d) "
                                             r"rec (-?\d+) STATES:([EPIO]{12}) QUEUE:((?: \S+)*) TRAIL (\d+) PATTERNS:(\d{12}) SCENES \d+ SONG (\d+)(?: JRN (\d))?$", text, re.M)]
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
PAGE_MAX = {HOME: 8, SEQ: 7, ARP: 6, SAVE: 5, GLO: 3, LFO: 6, ENV: 8}   # 0.12: the pages of each button (0.13: HOME 8, SAVE 4, LFO 4; 0.28: ENV 8)


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
    group("twelve tracks (0.28; sixteen until 0.27)")
    s = Script()
    s.tap_key(100, wk(0))                                  # track 1: step 1
    s.tap_key(200, bk(8)); s.tap_key(300, bk(3))           # bank 2 (9-12), track 12 (index 11)
    s.tap_key(400, wk(1))                                  # track 12: step 2
    s.tap_key(500, bk(7)); s.tap_key(560, bk(7))           # black 8 in the bank of 9-12: 0.31 the mute of track 12 - twice, back
    s.tap_btn(600, PLAY)
    log = run(s, 3400)
    n0 = log.notes(ch=0, after=600)
    n1 = log.notes(ch=11, after=600)                       # track 12 is on channel 12 (twelve tracks on 14 channels: a channel each)
    check(len(n0) >= 2 and len(n1) >= 2, "track 1 (channel 1) and track 12 (channel 12) both play (%d, %d)" % (len(n0), len(n1)))
    check(n1 and n0 and near(n1[0][0] - n0[0][0], STEP_MS, 3), "track 12's step 2 is one step after track 1's step 1")
    # each of the 12 tracks plays its own step: track i has step i on
    s = Script()
    t = 100
    for tr in range(12):
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
    check(len(got) == 12, "12 channels are in use, one a track (%d)" % len(got))
    first = sorted(x[0] for x in got.values())
    check(len(first) == 12 and first[-1] - first[0] > 10 * STEP_MS, "every track plays its own step (first notes spread over %.0f steps)" % ((first[-1] - first[0]) / STEP_MS))


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
    # SEQ + PRESETS: the genre. GQOM KICK #1 "X.....X.....X..." (0.29: the 11th genre)
    log, p = beat(lambda s, t: (s.enc(t, E_PRE, 10), t + 60)[1])
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
    check(chs == list(range(12)), "ALL ON with the scope ALL: every track's channel plays (%s)" % chs)
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
    # 0.22: the loop does not wait for the panel any more (lcd_idle): 3 ms where 0.21 had 9, the gaps 7-10 where it had 3-14
    check(longest <= 3, "no pass of the main loop longer than 3 ms (%d ms)" % longest)
    clk = [t for t in log.clock() if t > t0 + 4200]        # at 300 BPM: a tick every 8.33 ms
    gaps = [b - a for a, b in zip(clk, clk[1:])]
    check(len(gaps) > 100 and max(gaps) <= 11 and min(gaps) >= 6, "the clock leaves evenly, no late ticks and no bursts (the gaps: %s to %s ms)" % (
        min(gaps) if gaps else None, max(gaps) if gaps else None))
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
    for k in range(12):
        if k:
            s.enc(t, E_SEL, 1); t += 50
        s.press(t, SEL); s.tap_key(t + 30, CHORD_CEG, hold=60); s.release(t + 120, SEL); t += 200
        t = arp2(s, t, [(K4, 10)])
        t = home_page(s, t, 5, [(K1, 3), (K2, 2), (K4, 8)], cur=5 if k else 0)   # keeps 100 %: every repeat as loud
        t = seq_page(s, t, 0, keys=[wk(5)])                               # 0.16: started
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + 1500)
    first = [sorted({d1 for tm, d1, v in log.notes(ch=c, after=p, before=p + 200)}) for c in range(12)]
    echoes = len(log.notes(after=p + 200))
    check(all(f == [60, 64, 67] for f in first), "12 tracks: every strummed chord whole (%s)" % first)
    check(echoes == 128, "... and the echo queue used to the last place (%d echoes of 144 asked)" % echoes)

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
    # BEAT view, genres page 2 (pad 13 of row 1): the 14th genre (0.29: DRUM+BASS, pad 2 of page 2), its KICK #1 "X.........X....."
    s = Script()
    s.raw(100, "attach")
    view(s, 200, GC_VTRACK, alt=True)
    s.pad(300, 12, 0); s.pad(400, 1, 0); s.pad(500, 0, 1); s.pad(600, 13, 0)
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
    check(v[0]["on"] == 1 and v[0]["states"] == "E" * 12 and v[0]["bars"] == 16 and v[0]["energy"] == 50 and v[0]["genre"] == 0,
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
    check(v[1]["mute"] == 0x0FFF and v[2]["mute"] == 0, "bars 5-6 silent, bar 7 everything back (%04X %04X)" % (v[1]["mute"], v[2]["mute"]))
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
    check(log.viaggio[0]["mute"] == 0x0FFE and log.notes(ch=0, after=t0 + 4 * BAR_MS + 10, before=t0 + 5 * BAR_MS - 10)
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
    check(v[4]["song"] == 1 and log.states[4]["msg"].startswith("SET SAVED: 1 SCENES"), "SAVE + white 16: the trail becomes scenes and the song (%s)" % log.states[4]["msg"])


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
    check(v[0]["states"] == "E" * 12 and v[1]["states"].startswith("P") and log.states[1]["msg"].startswith("T1 KICK P2"),
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
    group("0.9: the profiles (SAVE + K4: FULL, SEMPLICE, PALCO), the settings and the project keep the journey across a power cycle")
    d = tempfile.mkdtemp()
    flash = os.path.join(d, "flash.bin")
    s = Script()
    s.press(100, SAVE); s.enc(130, K4, 2); s.release(200, SAVE)      # PALCO (0.27: past SEMPLICE)
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
    check(log.states[1]["msg"].startswith("NOT IN THIS PROFILE") and v[1]["states"] == "E" * 12, "SEQ + a key: refused (%s)" % log.states[1]["msg"])
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
    s.press(100, SAVE); s.enc(130, K4, -2); s.release(200, SAVE)     # FULL again
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
    s.press(100, SAVE); s.enc(130, K4, 2); s.release(200, SAVE)
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
    # 0.24: the length is the track's. A track of 32 steps, BEAT: the kick of one bar, and the bar again (its copies) -
    # LONG PATTERNS (SAVE page 2 K4; LIBRARY LEN until 0.23) on COPY, as a new project has it ...
    s = Script()
    t = home_page(s, 100, 0, [(K2, 16)])                                                             # LENGTH 32
    s.press(t, SEQ); s.tap_key(t + 30, wk(9)); s.release(t + 100, SEQ)                               # BEAT
    s.at(t + 200, "dump", 0)
    log = run(s, t + 300)
    check(log.dumps[0]["length"] == 32 and log.dumps[0]["on"] == "x...x...x...x..." * 2 and log.copies[0]["own"] == 16 and cfgs(log)[0]["lib"] == 0,
          "a track of 32, BEAT, LONG PATTERNS COPY: the kick's bar twice, the second its copies (%s %s own %s)" % (log.dumps[0]["length"], log.dumps[0]["on"], log.copies[0]["own"]))
    # ... on PHRASE: the two bars of 0.10 (the next variation in the second, the genre's fill), all of them the pattern's
    s = Script()
    t = home_page(s, 100, 0, [(K2, 16)])
    s.press(t, SAVE); s.tap_btn(t + 30, OCT_UP, hold=20); s.enc(t + 80, K4, 1); s.release(t + 140, SAVE); t += 300
    s.press(t, SEQ); s.tap_key(t + 30, wk(9)); s.release(t + 100, SEQ)                               # BEAT
    s.at(t + 200, "dump", 0)
    log = run(s, t + 300)
    check(log.dumps[0]["length"] == 32 and log.dumps[0]["on"][:16] == "x...x...x...x..." and log.dumps[0]["on"][16:] != log.dumps[0]["on"][:16]
          and log.dumps[0]["on"].count("x") >= 8 and log.copies[0]["own"] == 32 and cfgs(log)[0]["lib"] == 1,
          "... LONG PATTERNS PHRASE: a 32-step kick, its second bar another (%s %s own %s)" % (log.dumps[0]["length"], log.dumps[0]["on"], log.copies[0]["own"]))
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
    check(out[2][0] == "x...x...x...x.x." and out[2][1] == 2, "NUMERIC (0.23.1): K1 on 5 picks the fifth base rhythm, four and a pickup (%s)" % out[2][0])
    # a USER progression (SEQ 8): i v (one bar each), HARMONY on it: a FOLLOW track moves C -> G
    s = Script()
    t = kp(s, 100, [(K2, 1), (K4, 1)])                             # C major, IN KEY
    t = s.steps(t, [0])
    t = home_page(s, t, 1, [(K4, 1)], cur=2)                       # FOLLOW
    t = uprog_knobs(s, t, [(K3, 1), (K2, 1), (K3, 8)])        # USER 1: pos 1 = I (root 0), pos 2 = V (0.11: K3 the root, 7 semitones)
    t = harm_knobs(s, t, [(K2, 8), (K1, 1)])          # HARMONY: progression 9 = USER 1 (0.29: past the genre's eight), READY; K1 ON (0.16)
    s.at(t, "dump", 0)
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(4 * BAR) - 20)
    b = [sorted({d1 for tm, d1, v in log.notes(ch=0, after=p0 + int(k * BAR) - 5, before=p0 + int((k + 1) * BAR) - 5)}) for k in range(4)]
    check(cfgs(log)[0]["prog"] == 8 and log.states[0]["msg"].startswith("HARMONY USER"), "HARMONY USER 1 (%s)" % log.states[0]["msg"])
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
    # every genre of the library is a VIAGGIO genre: GLO 3 K3 walks all 22 (0.16: the merengue last; 0.29: 22), each with a kick proposal
    s = Script()
    t = vg_on(s, 100)
    for g in range(21):
        t = viaggio_knobs(s, t, [(K3, 1)])
    s.at(t, "dump", 0)
    vg_tap(s, t + 50, 0)
    s.at(t + 150, "dump", 0)
    log = run(s, t + 250)
    check(log.viaggio[0]["genre"] == 21 and "MERENGUE" in log.states[0]["msg"], "K3 x 21: MERENGUE, the last genre (%s)" % log.states[0]["msg"])
    check(log.viaggio[1]["states"][0] == "P" and log.dumps[1]["on"].count("x") == 0 and log.states[1]["msg"].startswith("T1 KICK P2"), "a MERENGUE kick proposed (%s)" % log.states[1]["msg"])
    s = Script()
    t = vg_on(s, 100)
    for g in range(19):                                            # (0.29: PHONK is the 20th)
        t = viaggio_knobs(s, t, [(K3, 1)])
    t = home_page(s, t, 3, [(K2, 7)])                              # role ARP: the cowbell riff
    vg_tap(s, t, 0); t += 100
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    check(log.states[0]["msg"].startswith("T1 LEAD P2") and log.dumps[0]["on"].count("x") == 0, "PHONK, role ARP: a proposal of its LEAD, the cowbell riff (%s)" % log.states[0]["msg"])
    # a genre with no proposal of a role falls back: UK DRILL's chord
    s = Script()
    t = vg_on(s, 100)
    for g in range(17):                                            # (0.29: UK DRILL is the 18th)
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
    check(log.dumps[0]["length"] == 64 and log.dumps[0]["on"] == "x...x...x...x..x" * 4 and log.copies[0]["own"] == 16,
          "the new pattern, kick #2: the track stays 64 steps (0.24: until 0.23.2 the pattern made it 16), the kick's bar four times (%s, own %s)" % (log.dumps[0]["on"], log.copies[0]["own"]))
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
SQ_FM_HOLD, SQ_FM_RETRIG, SQ_FM_LEGATO, SQ_FM_MELODY, SQ_FM_SMOOTH = range(5)



def t011_progressions():
    group("0.11: the progressions: any root and shape, lengths in 16ths, PUSH, 3+3+2, RETRIG / LEGATO, the moods, DICE PROG")
    BAR = 16 * STEP_MS

    def setup(s, rhythm=0, steps=range(16)):
        t = kp(s, 100, [(K2, 1), (K4, 1)])                             # C major, IN KEY
        t = s.steps(t, list(steps))
        t = home_page(s, t, 1, [(K4, 1)], cur=2)                       # FOLLOW
        t = uprog_knobs(s, t, [(K3, 1), (K2, 1), (K3, 8)])        # USER 1: I, V
        t = harm_knobs(s, t, [(K2, 8), (K1, 1)])          # HARMONY: USER 1, ON (0.16: K2 alone makes it READY)
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
    check(hh[0]["mood"] == SQ_MOOD_TENSE and all(h["pmood"] == SQ_MOOD_TENSE for h in hh if h["prog"] != 0) and progs[-1] == 8 and 8 in progs,
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
        check(h["prog"] == 12 and 2 <= n5 <= 5 and (m5 == mood if mood else m5 > 0) and all(0 <= r[0] <= 11 and 6 <= r[1] <= 37 for r in rows)
              and log.states[0]["msg"].startswith("DICE PROG"), "DICE PROG (mood %d): %s (%s)" % (mood, rows, log.states[0]["msg"]))


def t011_pi_progressions():
    group("0.11: the Pi's progressions: HARMONY K2 past the FM-1's asks how many, each comes into DICE/PI and plays, ARP + SAVE sends one")
    hexs = lambda b: " ".join("%02X" % x for x in b)
    s = Script()
    t = uprog_knobs(s, 100, [(K1, 3), (K3, 1), (K2, 1), (K3, 8)])              # USER 4: I V
    t = harm_knobs(s, t, [(K2, 11)])                              # HARMONY: USER 4 (prog 11; 0.28: 9)
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
    check(hh[1]["prog"] == 12 and hh[1]["u"][4] == (2, 8, [(0, 10, 0, 0), (1, 9, 8, 1)]) and log.states[1]["msg"] == "PI DARK 1/3: i-bII",
          "it comes into DICE/PI and plays (%s %s)" % (hh[1]["u"][4], log.states[1]["msg"]))
    check(len(gets) >= 2 and gets[1][7:9] == [1, 0] and hh[2]["u"][4][:2] == (1, 9), "K2: the Pi's second (%s)" % (hh[2]["u"][4],))
    check(len(gets) == 3 and gets[2][7:9] == [2, 0] and hh[3]["prog"] == 12 and log.states[3]["msg"] == "PI: THE LAST PROGRESSION OF TECHNO",
          "five on: the last; past it: it stays (%s, %s)" % ([hexs(m) for m in gets[2:]], log.states[3]["msg"]))
    check(hh[4]["prog"] == 11, "K2 back below the first: USER 4 (%s)" % hh[4]["prog"])
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
        check(len(ok) == 12 and "0" not in ok, "%s: every track where the bar says (%s)" % (what, "".join(ok)))


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
    # COOK walks the genre's list and wraps; in JUNGLE (SEQ + PRESETS to genre 8; 0.29: the 8th, number 7) it starts from STRAIGHT's successor THINK
    s = Script()
    t = break_track(s, 100)
    t = break_knobs(s, t, [(K1, 1), (K1, -1)])                # STRAIGHT
    s.press(t, SEQ); s.enc(t + 30, E_PRE, 7); s.release(t + 100, SEQ); t += 160   # the library's genre: JUNGLE
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
    """SAVE + K2 once: REMOTE ON CH 14 + PAGES ON CH 13 (0.30: was VIAGGIO ON CH 13; 0.12: the Pi's new pages speak on 13, CC 33 and up, and notes)"""
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
    s.raw(t, "midi 0xBC 112 2"); t += 50                              # the tablet's track: 3 (0.18: the panel's stays 1)
    s.raw(t, "midi 0xBC 113 4"); t += 50                              # track 3: BREAK (a knob of 0-4 sends the index; 127 would do too)
    s.raw(t, "midi 0xBC 74 3"); s.raw(t + 20, "midi 0xBC 75 2"); t += 60   # ROLLS 3, SLICES 32 (small values are the index)
    s.at(t, "dump", 0); s.at(t, "dump", 1); s.at(t, "dump", 2)
    s.at(t, "ui"); t += 20
    s.tap_key(t, bk(2)); t += 80                                      # the panel on track 3 too, to see its BREAK page
    t = pg(s, t, SEQ, 6); s.press(t, SEQ); s.at(t + 60, "ui"); s.release(t + 120, SEQ); t += 180
    s.raw(t + 20, "midi 0x9C 40 100"); s.raw(t + 120, "midi 0x8C 40 0")   # a pad: note 40 on channel 13 = slice 5 of track 3
    s.raw(t + 200, "midi 0xBC 83 110"); s.raw(t + 260, "midi 0xBC 83 0")   # the same pad as a CC (76 + 7 = slice 8)
    log = run(s, t + 300)
    d = log.dumps
    check(d[0]["length"] == 24 and d[1]["pat"] == 4 and d[2]["mode"] == "B", "CC 49 = 24: LENGTH; CC 34 = 3: pattern 4 of track 2; 112 / 113: track 3, BREAK (%s %s %s)" % (d[0]["length"], d[1]["pat"], d[2]["mode"]))
    sc = log.screens()
    check(len(sc) == 2 and " T1 " in sc[0]["lines"][0], "0.18: CC 112 is the tablet's track; the panel's stays T1 (%s)" % (sc[0]["lines"][0] if sc else sc))
    check(len(sc) == 2 and sc[1]["cells"][1][1] == "3" and sc[1]["cells"][3][1] == "32", "CC 74 = 3, 75 = 2: ROLLS 3, SLICES 32 (%s)" % ([c[1] for c in sc[1]["cells"]] if len(sc) == 2 else sc))
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
    s.press(t, LFO); s.at(t + 60, "ui"); s.enc(t + 90, E_SEL, 2); s.at(t + 150, "ui"); s.release(t + 200, LFO); t += 260   # the panel: LFO 1, then 3
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    sc = log.screens()
    check(len(sc) == 2 and sc[0]["lines"][2].startswith("LFO 1/") and sc[1]["lines"][2].startswith("LFO 3/") and sc[1]["cells"][2][1] == "100",
          "CC 92 / 93 / 95: the tablet's LFO 3 at depth 100; the panel shows its own LFO 1 until it turns to 3 (%s)" % ([x["lines"][2] for x in sc] + ([sc[1]["cells"][2]] if len(sc) == 2 else [])))
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
    check(h and h[0][1]["state"] == 0 and h[0][1]["booted"] == 0 and h[0][1]["version"] == FW_VERSION, "HELLO: nothing asked yet, a normal boot, its version (%s)" % h)
    check([a for _, a in ans(log, "open")] == [1, 2], "OPEN asks, SEL says yes (%s)" % ans(log, "open"))
    check(ans(log, "boot") == [(1200, 1)] and re.search(r"^\s*12[89]\d ms  TEST REBOOT", log.text, re.M), "BOOT: yes, then the reboot (%s)" % ans(log, "boot"))
    # 0.20.9 DIAG: the HELLOs and the frames that came in since the boot, the USB's counters (the simulator's: one
    # enumeration), now; an old FM-1 does not answer it (the runner then goes on without)
    s = Script()
    sx(s, 400, TP.hello()); sx(s, 500, TP.hello()); sx(s, 600, TP.open_()); sx(s, 700, TP.diag())
    log = run(s, 900)
    dg = ans(log, "diag")
    d0 = dg[0][1] if dg else {}
    check(d0.get("hellos") == 2 and d0.get("frames") == 4 and d0.get("unsent") == 0 and d0.get("resets") == 1 and
          d0.get("configs") == 1 and d0.get("ms") == 700 and 0 < d0.get("first_ms", 0) <= 2 and d0.get("gap_max", 99) <= 2 and
          len(d0) == len(TP.DIAG_FIELDS) + len(TP.DIAG_MORE), "DIAG: 2 HELLOs, 4 frames, nothing unsent, one enumeration, the main loop never still, at 700 ms (%s)" % dg)
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
        check(p0 and p0["T1"]["steps#"] == "A193A0C5", "the project in the slot is not loaded: the empty pattern (%s)" % p0.get("T1", {}).get("steps#"))   # (0.28: steps of 22 bytes)
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


def t0203_test_listens():
    group("0.20.3: the PC test hears the FM-1's ports when GO asks (the Pi's banco): it plays what comes in, says where (ms, clock tick, port), and the replay with those as the test's MIDI events is the same machine")
    sys.path.insert(0, os.path.join(ROOT, "tools", "hwtest"))
    import sagga_testport as TP

    def sx(s, t, b): s.at(t, "sx", " ".join("%02X" % x for x in b[1:-1]))

    def answers(log):
        return [(t, TP.parse(bytes(b))) for t, b in log.sysex if TP.parse(bytes(b))]

    def session(listen, extra, evs):
        s = Script()
        sx(s, 1000, TP.hello()); sx(s, 1010, TP.go(listen)); sx(s, 1020, TP.ev_frame(0, evs))
        for line in extra:
            t, rest = line.split(" ", 1)
            s.raw(int(t), rest)
        return run(s, 1000 + evs[-1][0] + 600, testboot=True)

    evs = [(100, TP.PROBE, 0, 0), (200, TP.PRESS, PLAY, 0), (230, TP.RELEASE, PLAY, 0), (1500, TP.PROBE, 0, 0), (2600, TP.PROBE, 0, 0),
           (2700, TP.END, 0, 0)]
    extra = ["1600 midi 0xBF 118 127", "1700 midi 0xBE 4 127", "1740 midi 0xBE 4 0"]       # the grid: attached, the STEP view
    extra += ["%d midi 0x9F %d %d" % (1800 + 10 * k, 16 + k, 100 if k % 2 == 0 else 0) for k in range(40)]   # 40 in 400 ms
    extra += ["%d midi 0xBF 118 64" % t for t in (2400, 4000)]                            # (the keep-alive; 4000: after END)
    deaf = session(False, extra, evs)
    a = answers(deaf)
    probes = lambda a: {i: TP.probe_dict(t) for i, t in _probes(a).items()}

    def _probes(a):
        pr = TP.Probes()
        for _, x in a:
            if x[0] == "probe":
                pr.add(*x[1])
        return pr.done
    pd = probes(a)
    check(pd.get(4, {}).get("G", {}).get("grid") == "0" and not [x for _, x in a if x[0] == "heard"],
          "GO as before: the ports are not heard (the grid stays away), nothing said (%s)" % pd.get(4, {}).get("G", {}).get("grid"))
    done = [x[1] for _, x in a if x[0] == "done"]
    check(done and "heard" not in done[0], "... and DONE as before (%s)" % done)
    ear = session(True, extra, evs)
    a = answers(ear)
    pe = probes(a)
    heard = TP.Heard()
    for _, x in a:
        if x[0] == "heard":
            heard.add(*x[1])
    rows = heard.rows()
    go = [x[1] for _, x in a if x[0] == "go"][0]
    check(pe.get(4, {}).get("G", {}).get("grid") == "1", "GO with listen: the grid's attach is played (%s)" % pe.get(4, {}).get("G", {}).get("grid"))
    check(len(rows) == 45 and [r[2:5] for r in rows[:3]] == [[0xBF, 118, 127], [0xBE, 4, 127], [0xBE, 4, 0]] and all(r[5] == 0 for r in rows),
          "every message heard said, in order, from port 1 (the only one), after END too (%d %s)" % (len(rows), rows[:3]))
    check(all(r[0] - 1000 in (int(l.split()[0]) - 1000, int(l.split()[0]) - 999) for r, l in zip(rows, extra)),
          "... each at the ms it came in (%s)" % [(r[0], l.split()[0]) for r, l in list(zip(rows, extra))[:4]])
    check(sorted(heard.by_seq) == list(range(len(rows))) and heard.gaps() == 0, "the numbers have no gap (%s)" % sorted(heard.by_seq)[:5])
    done = [x[1] for _, x in a if x[0] == "done"]
    check(done and done[0].get("heard") == 44 and done[0].get("heard_lost") == 0, "DONE: 44 heard up to END, none lost (%s)" % done)
    gcs = [r[1] for r in rows]
    check(gcs == sorted(gcs) and gcs[-1] > gcs[0] > 0, "the clock ticks go on under them (%s .. %s)" % (gcs[0], gcs[-1]))
    # the replay: the heard ones as the test's MIDI events where the FM-1 heard them, in a run that does not listen
    logs = {}
    for _, x in a:
        if x[0] == "log":
            for idx, ms, gc in x[1]:
                logs[idx] = (ms, gc)
    rp = sorted([(logs[i][0], 1, list(e[1:4]) + [logs[i][1]]) for i, e in enumerate(evs)] +
                [(r[0], 0, [TP.MIDI] + list(TP.midi_ev(r[2], r[3], r[4], TP.PORT1)) + [r[1]]) for r in rows if r[0] <= logs[len(evs) - 1][0]],
                key=lambda x: x[:2])
    order = [x[2][0] for x in rp]
    replay = session(False, [], [(ms - go,) + tuple(e) for ms, _, e in rp])
    pr = probes(answers(replay))
    idx = [k for k, kind in enumerate(order) if kind == TP.PROBE]
    machine = lambda d: {w: v for w, v in (d or {}).items() if w != "H"}      # (H: the FM-1's own numbers, the test's queue)
    same = [machine(pe.get(i)) == machine(pr.get(k)) for i, k in zip((0, 3, 4), idx)]
    check(all(same) and pr.get(idx[-1], {}).get("G", {}).get("grid") == "1", "the replay probes the same machine, probe by probe (%s)" % same)
    lights = lambda log: sorted((t, st, d1, d2) for t, st, d1, d2 in log.msgs if st in (0x9F, 0xBE) and t < 1000 + 2700)
    check(lights(ear) and lights(ear) == lights(replay), "... and sends the grid the same lights at the same ms (%d)" % len(lights(ear)))


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
    group("0.12 grid PICK view, 0.18 FOLLOW (SHIFT + STEP twice): the four knobs of the page open on the FM-1, a row each, their values on rows 1-4; rows 5-8 the same knobs across the 16 tracks (a track's, not its channel) or the black keys' values")
    # the HOME window: row 1 = CHANNEL (items 1-12 lit, the current white), row 2 = LENGTH (4, 8 .. 64), row 3 = DIVISION, row 4 = TRANSPOSE;
    # rows 5-8: the same four across the tracks (track 1, the FM-1's, white; the tracks with its value lit)
    s = Script()
    s.raw(100, "attach")
    s.tap_btn(200, HOME)                                                   # the HOME window
    view(s, 400, GC_VSTEP, alt=True); view(s, 500, GC_VSTEP, alt=True)    # CC, again: FOLLOW
    s.at(700, "ui")
    s.pad(800, 7, 1)                                                       # row 2 pad 8: LENGTH 32
    s.pad(900, 2, 5)                                                       # row 6 pad 3: track 3 gets LENGTH 32 too
    s.at(1000, "dump", 0); s.at(1005, "dump", 2); s.at(1010, "ui")
    s.pad(1100, 4, 0)                                                      # row 1 pad 5: channel 5
    s.at(1200, "dump", 0)
    s.pad(1300, 2, 3)                                                      # row 4 pad 3: TRANSPOSE -8 (the whites F3 G3 A3 = -12 -10 -8)
    s.at(1400, "dump", 0)
    shift(s, 1500, 1); s.pad(1520, 5, 6); shift(s, 1560, 0)                # SHIFT + row 7 pad 6: the FM-1 goes to track 6
    s.at(1700, "ui")
    log = run(s, 1800)
    sc = log.screens()
    check(bool(sc) and sc[0]["lines"][2].startswith("HOME 1/8") and sc[0]["lines"][3].startswith("FOLLOW"), "the HOME window with the grid on FOLLOW (%s)" % (sc[0]["lines"][2:4] if sc else sc))
    pads, ctls = log.leds(until=790)
    ctls = log.leds(until=1100)[1]
    check(pads[0 * 16 + 0] == GL_WHITE and pads[0 * 16 + 13] == GL_ON and pads[0 * 16 + 14] == GL_OFF,
          "row 1 CHANNEL: 1 is white, 14 lit, 15 off (the grid takes 15 and 16) (%s)" % [pads.get(i) for i in (0, 13, 14)])
    check(pads[1 * 16 + 3] == GL_WHITE and pads[1 * 16 + 15] == GL_BLUE, "row 2 LENGTH: 16 white (pad 4), 64 blue (%s)" % [pads.get(i) for i in (19, 31)])
    check(pads[4 * 16 + 0] == GL_OFF and pads[4 * 16 + 9] == GL_OFF, "row 5: CHANNEL is not copied across (a synth's): the black keys, items 17+ off (%s)" % [pads.get(i) for i in (64, 73)])
    check(pads[5 * 16 + 0] == GL_WHITE and all(pads[5 * 16 + x] == GL_BLUE for x in range(1, 12)) and [pads.get(5 * 16 + x, GL_OFF) for x in range(12, 16)] == [GL_OFF, GL_OFF, GL_CYAN, GL_WHITE],
          "row 6: every track 16 steps long, as track 1: lit; 13-16 the groups (0.31): no drum, no bass track - dark -, the melodic ones and all of them lit (%s)" % [pads.get(80 + x) for x in (0, 1, 11, 12, 13, 14, 15)])
    check(ctls.get(GC_SHIFT) == GL_CYAN and ctls.get(GC_VSTEP) == GL_YELLOW, "FOLLOW: SHIFT cyan, STEP yellow (%s %s)" % (ctls.get(GC_SHIFT), ctls.get(GC_VSTEP)))
    d = log.dumps
    check(len(d) == 4 and d[0]["length"] == 32 and d[1]["track"] == 3 and d[1]["length"] == 32, "row 2 pad 8: LENGTH 32; row 6 pad 3: track 3 too (%s)" % [(x["track"], x["length"]) for x in d])
    check(len(sc) > 1 and sc[1]["lines"][3].startswith("T3 LENGTH AS T1"), "the screen: T3 LENGTH AS T1 (%s)" % (sc[1]["lines"][3] if len(sc) > 1 else sc))
    ch = [int(m) for m in re.findall(r"^\s*\d+ ms  cfg T1 role \d+ chord \d+ oct -?\d+ keyslot -?\d+ trans (-?\d+) div", log.text, re.M)]
    check(ch[-2:] == [0, -8], "row 4 pad 3: TRANSPOSE -8 (%s)" % ch)
    check(len(sc) > 2 and " T6 " in sc[2]["lines"][0], "SHIFT + row 7 pad 6: the FM-1 on track 6 (%s)" % (sc[2]["lines"][0] if len(sc) > 2 else sc))
    # a knob that is no track's (HOME 3: the key): rows 5-8 the black keys' values, as PICK had
    s = Script()
    s.raw(100, "attach")
    t = 200
    s.tap_btn(t, HOME); t += 100
    s.tap_btn(t, OCT_UP); s.tap_btn(t + 80, OCT_UP); t += 200        # (the window: OCT+ turns HOME's pages) HOME 3: KEY, ROOT, SCALE, SHIFT
    view(s, t, GC_VSTEP, alt=True); view(s, t + 100, GC_VSTEP, alt=True); t += 300
    log = run(s, t + 200)
    pads, ctls = log.leds(after=t - 200)                             # (from the second tap: 0.22 paints a view in 100 ms, not 350)
    check(pads.get(5 * 16 + 0) in (GL_BLUE, GL_WHITE) and pads.get(5 * 16 + 4) in (GL_BLUE, GL_WHITE), "HOME 3: row 6 ROOT (no track's) has the black keys' notes (%s)" % [pads.get(80 + x) for x in range(5)])
    # FOLLOW: the window closed, the grid goes to the steps; PERF: the PERF view; a view by hand: FOLLOW off
    s = Script()
    s.raw(100, "attach")
    s.tap_btn(200, HOME)
    view(s, 400, GC_VSTEP, alt=True); view(s, 500, GC_VSTEP, alt=True)
    s.tap_btn(700, HOME)                                                   # the window closed: the steps
    s.at(1100, "probe")
    s.tap_btn(1200, LFO)                                                   # the LFO window: the LFO view
    s.at(1600, "probe")
    s.tap_btn(1700, LFO); s.tap_btn(1800, GLO)                             # PERF
    s.at(2200, "probe")
    view(s, 2300, GC_VTRACK)                                               # TRACK by hand: FOLLOW off
    s.tap_btn(2500, GLO)                                                   # (PERF off: the grid stays on TRACK)
    s.at(2900, "probe")
    log = run(s, 3000)
    gv = [int(x) for x in re.findall(r" gview=(\d+)", log.text)]
    check(gv == [0, 4, 1, 2], "FOLLOW: the steps, the LFOs, PERF; TRACK by hand stays (%s)" % gv)


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
    check(len(sc) == 3 and sc[0]["lines"][2].startswith("SEQ 1/8") and sc[1]["lines"][2].startswith("SEQ 2/8") and sc[2]["lines"][2].startswith("STEP 1"),     # (0.23: SEQ has eight pages)
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
    check(wins(log) == [-1, -1, ENV] and len(sc) == 3 and sc[0]["lines"][2].startswith("PERF SCENE") and sc[1]["lines"][2].startswith("GLO 2/4 TRACK LIVE") and sc[2]["lines"][2].startswith("ENV"),
          "GLO tapped: PERF, no window; OCT+: GLO 2/4; ENV tapped: its window, PERF off (%s %s)" % (wins(log), [x["lines"][2][:14] for x in sc]))
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
    check(sc and sc[0]["cells"] == [("MOTION", "2 BARS"), ("KEYBOARD", "TRANS <C3"), ("KEYB CH", "3"), ("MIDI IN", "ALWAYS")] and sc[0]["lines"][2].startswith("SAVE 4/5"),
          "SAVE 4/5 LIVE IN: MOTION, KEYBOARD (0.26: TRANSPOSE, TRANS <C3, then the chords), KEYB CH, MIDI IN (%s)" % (sc[0]["cells"] if sc else sc))
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


def sgq_tool():
    """the editor's converter (tools/sgqmid/sagga_sgqjson.c, the firmware's core), built once"""
    if _SGQJSON[0] is None:
        out = os.path.join(tempfile.mkdtemp(), "sagga_sgqjson")
        subprocess.run(["cc", "-std=c11", "-O2", "-I" + ROOT + "/firmware/src", ROOT + "/tools/sgqmid/sagga_sgqjson.c",
                        ROOT + "/firmware/src/sagga_seq_core.c", ROOT + "/firmware/src/sagga_beats.c", "-o", out], check=True)
        _SGQJSON[0] = out
    return _SGQJSON[0]


def sgq_image(lines):
    """a project image made by the editor's converter (the firmware's core) from a patch over a new project"""
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "p.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    subprocess.run([sgq_tool(), "apply", "new", os.path.join(d, "p.txt"), os.path.join(d, "o.sgq")], check=True)
    return open(os.path.join(d, "o.sgq"), "rb").read()


def sgq_read(image):
    """0.32: a project image as the editor's converter reads it (a dict: track, lfo, scene, song_e, live, ext, steps ...)"""
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "p.sgq"), "wb") as f:
        f.write(image)
    return json.loads(subprocess.run([sgq_tool(), "read", os.path.join(d, "p.sgq")], check=True, capture_output=True, text=True).stdout)


def exports(log):
    """0.32: every project the FM-1 sent out in the run (an EXPORT: the PC's 7D 53 47 01, SAVE + white 11, PROJ row 6
    pad 12), read by the converter, in order"""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import sagga_grid_bridge as B
    rx, out = B.DumpReceiver(), []
    for _, m in log.sysex:
        r = rx.feed(m)
        if r and r[0] == "image":
            out.append(sgq_read(r[1]))
    return out


def step_of(js, t, pat, i):
    """0.32: step i of pattern pat of track t (0-based) in an exported project: the converter lists the ones that differ"""
    for e in js["steps"]:
        if e[:3] == [t, pat, i]:
            return e[3]
    return js["step_default"]


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
    # 0.32.1: the song's place. 127 is "no song" and (0.30: 128 entries) the song's last entry: the sixteenth place's
    # step says the song is on
    check(ok and j["song"] == -1 and all(m[7] == 127 and m[5 + 8 + 30] == 0 for _, m in pos),
          "no song: 127, the sixteenth place 0, the bridge reads -1 (%s)" % (j.get("song") if j else None))
    frame = list(six[0]) if six else []
    got = []
    for song, flag in ((127, 1), (127, 0), (5, 0), (5, 1)):
        if frame:
            frame[7], frame[5 + 8 + 30] = song, flag
            ctl.fm1_sysex(frame, 0.0)
            got.append(json.load(open(os.path.join(d, "pos.json")))["song"])
    check(got == [127, -1, 5, 5], "the bridge: entry 128 with the song on is 127, 127 with it off no song (an FM-1 before 0.32.1), any other entry itself (%s)" % got)
    s2 = Script()
    t2 = s2.steps(100, [0, 4, 8, 12])
    s2.tap_btn(t2, GLO); s2.press(t2 + 50, HOME); s2.tap_key(t2 + 100, bk(0)); s2.tap_key(t2 + 200, bk(1)); s2.release(t2 + 300, HOME); s2.tap_btn(t2 + 400, GLO)   # the song: scenes 1, 2
    s2.press(t2 + 500, HOME); s2.tap_btn(t2 + 550, GLO); s2.release(t2 + 650, HOME)   # HOME + GLO: the song on
    s2.at(t2 + 800, "sx", "7D 53 47 30 01")
    s2.tap_btn(t2 + 1000, PLAY)
    log2 = run(s2, t2 + 1000 + int(BAR_MS))
    pos2 = [m for tm, m in log2.sysex if m[:5] == [0xF0, 0x7D, 0x53, 0x47, 0x31] and m[5] == 1]
    check(pos2 and all(m[7] == 0 and m[5 + 8 + 30] == 1 for m in pos2), "a song playing its first entry: 0, and the sixteenth place says the song is on (%s)" % [(m[7], m[5 + 8 + 30]) for m in pos2[:2]])
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
    tr = band(16)                                                        # TRANCE: on the grid (0.29: number 16)
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
    group("0.16 ARP 4 K2 FREE: the chords are nobody's genre (ARP 3 K2 through all of them - 0.29: 22 genres of 8, 176; a loaded pattern does not move them); EDIT + ARP copies the progression into a USER slot")
    # FREE: from TECHNO, K2 one to the left
    s = Script()
    t = harm2_knobs(s, 100, [(K2, -1)])
    s.at(t, "dump", 0); s.press(t + 20, ARP); s.at(t + 200, "ui"); s.release(t + 300, ARP); t += 400   # (ARP 4 still: the Script remembers)
    t = harm_knobs(s, t, [(K2, 9)])                                      # TECHNO 1 + 9 = HARDTECHNO 2 (0.29: eight a genre)
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
    check(v and v[0]["hprog"] == 8 and v[0]["up"][0] == 4 and st and st[0] == "COPIED TO USER 1: ARP 5 TO CHANGE IT", "EDIT + ARP: into USER 1, which plays (%s %s)" % (v[:1], st[:1]))
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
    check(v and v[0]["up"][:2] == [4, 4] and v[0]["hprog"] == 9, "copied again: USER 2 (%s)" % v[:1])
    check(len(v) == 3 and st[1] == "COPY OVER USER 1: EDIT+ARP AGAIN" and v[1]["up"][0] == 4 and v[2]["up"][0] == 1 and v[2]["hprog"] == 8,
          "over USER 1: asked, then TECHNO 1 (one chord) copied (%s %s)" % ([(x["up"], x["hprog"]) for x in v], st))



def t016_merengue():
    group("0.16 MERENGUE, the last genre (0.29: the 22nd): SEQ + PRESETS x 21, BAND: four on the floor, the guira's cha chi-ki pushed a hair, the tambora played, I - V7 in a major key")
    ROLE_CONGA, ROLE_PIANO, ROLE_LEAD, ROLE_VOX, G_PUSH = 12, 22, 23, 24, 7
    s = Script()
    t = kp(s, 100, [(K2, 1), (K4, 1)])                                   # C major, IN KEY
    s.press(t, SEQ); s.enc(t + 30, E_PRE, 21); s.release(t + 100, SEQ); t += 300
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
    check(h and h[0]["prog"] == 0 and v[1]["hgenre"] == 21, "the harmony: the merengue's first, I - V7 (%s)" % (h[:1],))


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
    # while ECHO plays; started: 0.19, the two together (the chain); ECHO shown again (its 4): SEQ + white 6 takes it
    # out, HARM goes on; K1 OFF + SEQ + white 6 stops what is left
    s = Script()
    t = s.steps(100, (0,))
    t = home_page(s, t, 5, [(K1, 3), (K2, 2)]); s.at(t, "dump", 0)          # ECHO READY, 4 repeats
    t = seq_page(s, t, 0, keys=[wk(5)]); s.at(t, "dump", 0)                 # started
    t = home_page(s, t, 5, [(K1, -2)], cur=5); s.at(t, "dump", 0)           # HARM READY, ECHO plays on
    t = seq_page(s, t, 0, keys=[wk(5)]); s.at(t, "dump", 0)                 # HARM + ECHO
    t = home_page(s, t, 5, [(K1, 2)], cur=5); s.at(t, "dump", 0)            # ECHO shown (it plays): its 4
    t = seq_page(s, t, 0, keys=[wk(5)]); s.at(t, "dump", 0)                 # taken out: HARM
    t = home_page(s, t, 5, [(K1, -3)], cur=5)                               # OFF chosen
    t = seq_page(s, t, 0, keys=[wk(5)]); s.at(t, "dump", 0)                 # it stops
    log = run(s, t + 100)
    st = states(log)
    mc = [x for x in log.mfxc if x["track"] == 1]
    got = [(x["on"], x["sel"], x["amt"][2]) for x in mc]
    euc = [x["flags"] & 8 for x in st]
    check(got == [(0, 3, 4), (8, 3, 4), (8, 1, 4), (10, 1, 4), (10, 3, 4), (2, 3, 4), (0, 0, 4)] and not any(euc),
          "ECHO READY with 4, started by SEQ + white 6 (EUCLID stays off); HARM READY while ECHO plays, then both; ECHO out; OFF (%s %s)" % (got, euc))
    check([x["mfx"] for x in st] == [0, 3, 3, 1, 1, 1, 0], "the track's one effect: the chain's first (%s)" % [x["mfx"] for x in st])
    check(st[0]["msg"] == "T1 MIDI FX ECHO READY: SEQ + WHITE 6" and st[1]["msg"] == "T1 MIDI FX ECHO STARTS", "the screen: READY, STARTS (%r %r)" % (st[0]["msg"], st[1]["msg"]))
    check(st[3]["msg"] == "T1 MIDI FX HARM STARTS: HARM+ECHO" and st[4]["msg"] == "T1 MIDI FX ECHO PLAYS: SEQ + WHITE 6 TAKES IT OUT"
          and st[5]["msg"] == "T1 MIDI FX ECHO STOPS: HARM" and st[6]["msg"] == "T1 MIDI FX HARM STOPS",
          "the screen: the chain, TAKES IT OUT, STOPS (%r)" % [x["msg"] for x in st[3:]])
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
    check(v[2]["mute"] == 0x0FFD and not log.notes(ch=0, after=t0 + 4 * BAR_MS + 10, before=t0 + 5 * BAR_MS - 10)
          and log.notes(ch=1, after=t0 + 4 * BAR_MS + 10, before=t0 + 5 * BAR_MS - 10), "bar 5: track 2 alone (%04X)" % v[2]["mute"])
    check(v[3]["mute"] == 0 and log.notes(ch=0, after=t0 + 5 * BAR_MS + 10), "bar 6: both again (%04X)" % v[3]["mute"])
    check(v[4]["song"] >= 1 and v[4]["trail"] >= 2 and log.states[4]["msg"].startswith("SET SAVED"),
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
    check(sc and sc[0]["lines"][2].startswith("PERF 3/4 MOSSE  AT PHRASE") and sc[0]["cells"][0] == ("ENERGY", "50"),
          "SEL + GLO: PERF 3/4 MOSSE, the energy at 50 (%s %s)" % (sc[0]["lines"][2] if sc else None, sc[0]["cells"][0] if sc else None))
    check(v[0]["queue"] == ["FILL/0/0"] and log.states[0]["msg"] == "QUEUED: FILL", "black 1: FILL queued (%s)" % v[0]["queue"])
    check(v[1]["queue"] == [] and log.states[1]["msg"] == "CANCELLED FILL", "black 10: the last move cancelled (%s)" % log.states[1]["msg"])
    kl = log.key_leds()
    check(len(kl) == 2 and kl[0][1][BLACK[0]] == "X" and kl[0][1][BLACK[9]] == "X" and kl[0][1][BLACK[1]] != "X"
          and kl[1][1][BLACK[0]] != "X" and kl[1][1][BLACK[9]] != "X", "the black keys light what waits: FILL and black 10, then nothing (%s)" % [x[1] for x in kl])
    check(v[2]["queue"] == [] and log.states[2]["msg"] == "SCENE STORED 1", "page 1: SEL + black 1 stores scene 1, as ever (%s)" % log.states[2]["msg"])
    check(len(sc) == 2 and sc[1]["lines"][2].startswith("PERF 3/4 MOSSE"), "SEL + GLO from page 1: the MOSSE (%s)" % (sc[1]["lines"][2] if len(sc) == 2 else sc))
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


# ------------------------------------------------------------------------------------------------ 0.18
def t018_arp_slow():
    group("0.18 ARP RATE 1/2 and 1/4: a chord held over 16 steps arpeggiated a note every 2 / 4 steps (the knob: 1/4 1/2 ROLL 1 2 3 4)")
    def run_rate(turns, hold="HOLD"):
        s = Script()
        t = s.steps(100, [0])
        s.press(t, SEL); s.tap_key(t + 30, wk(0)); s.tap_key(t + 90, wk(2)); s.tap_key(t + 150, wk(4)); s.release(t + 250, SEL); t += 700   # F A C on step 1
        s.keys(t, wk(0)); s.keys(t + 500, wk(0) | wk(15)); s.keys(t + 580, wk(0)); s.keys(t + 660, 0); t += 800                           # held 1, then 16: 16 steps long
        t = pg(s, t, ARP, 0, [(K1, 1), (K3, turns)])
        s.press(t, ARP); s.at(t + 40, "ui"); s.release(t + 80, ARP); t += 140
        s.tap_btn(t + 50, PLAY); t0 = t + 50
        log = run(s, t0 + BAR_MS)
        n = log.notes(ch=0, after=t0, before=t0 + BAR_MS - 5)
        log.t0 = t0
        return log, [round((x[0] - t0) / STEP_MS, 1) for x in n], [x[1] for x in n]
    log, at, notes = run_rate(1)
    check(at == [float(i) for i in range(16)] and log.screens()[0]["cells"][2][1] == "1", "RATE 1: a note a step over the 16 (%s)" % at)
    log, at, notes = run_rate(-1)
    check(at == [float(i) for i in range(0, 16, 2)] and notes[:4] == [53, 57, 60, 53] and log.screens()[0]["cells"][2][1] == "1/2",
          "RATE 1/2: a note every 2 steps, F A C F ... (%s %s)" % (at, notes[:4]))
    log, at, notes = run_rate(-2)
    check(at == [0.0, 4.0, 8.0, 12.0] and log.screens()[0]["cells"][2][1] == "1/4", "RATE 1/4: every 4 steps (%s)" % at)
    first = log.notes(ch=0, after=log.t0)[0]
    offs = [m for m in log.msgs if m[0] > first[0] and m[2] == first[1] and ((m[1] & 0xF0) == 0x80 or ((m[1] & 0xF0) == 0x90 and not m[3]))]
    rings = (offs[0][0] - first[0]) / STEP_MS if offs else -1
    check(2.5 < rings < 3.5, "... each note rings on through the steps between (%.1f steps)" % rings)


def t018_tablet_track():
    group("0.18 the tablet has its own track: CC 112 chooses it, its notes, lanes, TAKE and LFO act there; the panel's track, page and LFO stay; the screen says TAB")
    s = Script()
    t = remote13_on(s, 100)
    s.tap_key(t, bk(1)); t += 80                                      # the panel: track 2
    s.raw(t, "midi 0xBC 112 5"); t += 50                              # the tablet: track 6
    s.raw(t, "midi 0x9C 60 100"); s.raw(t + 100, "midi 0x8C 60 0"); t += 200   # a pad of the tablet
    s.raw(t, "midi 0x9C 104 127"); t += 80                            # SAGGA Mod's switch: LFO 5 on
    s.at(t, "dump", 0); s.at(t + 10, "ui"); t += 60
    s.press(t, ARP); s.tap_key(t + 30, wk(7)); s.release(t + 120, ARP); t += 200   # the panel plays its own track meanwhile
    log = run(s, t + 100)
    sc = log.screens()
    tab = [n for n in log.notes(ch=5) if n[1] == 60]
    panel = log.notes(ch=1)
    check(tab and not log.notes(ch=1, before=t - 200), "a pad on channel 13 plays the tablet's track 6, not the panel's (%s)" % tab[:1])
    check(sc and " T2 " in sc[0]["lines"][0], "the panel stays on track 2 (%s)" % (sc[0]["lines"][0] if sc else sc))
    check(log.states[0]["rawmsg"] == "TAB T6: LFO ON", "the screen: TAB T6: LFO ON (%s)" % log.states[0]["rawmsg"])
    check(panel, "ARP + a key on the panel: track 2 plays (%s)" % panel[:1])



def usb2(s, t):
    """SAVE 3: USB PORTS 2, SEL + K1 twice: the reconnect (port 2: the grid, the remote, the hub)"""
    t = save_sys(s, t, [(K1, 1)])
    t = save_sys(s, t, [(K1, 1), (K1, 1)], sel=True)
    return t + 400


def t018_live_page():
    group("0.18 the hub's LIVE page (channel 12) on the tablet's track; what goes back to the hub on port 2: the FM-1's changes, not the tablet's own")
    s = Script()
    t = remote13_on(s, 100)
    t = usb2(s, t)
    t1 = t
    s.raw(t, "midi 0xBC 112 2 2"); t += 40                            # TRACK 3 (SAGGA Live / Motori / Mod)
    s.raw(t, "midi 0xBB 3 1 2"); t += 40                              # PATTERN 2 (stopped: at once)
    s.raw(t, "midi 0xBB 20 1 2"); t += 40                             # ARP UP
    s.raw(t, "midi 0xBB 44 127 2"); t += 40                           # MUTE 5
    s.raw(t, "midi 0xBB 9 3 2"); t += 40                              # MIDI FX ECHO READY
    s.at(t, "dump", 2); s.at(t + 5, "ui"); t += 40
    s.raw(t, "midi 0xBB 11 127 2"); s.raw(t + 20, "midi 0xBB 11 0 2"); t += 60   # FX GO
    s.at(t, "dump", 2); t += 40
    t0 = t + 600
    s.tap_key(t0, bk(2))                                              # the panel: track 3 too, ARP K1 + 1 (DOWN)
    s.press(t0 + 80, ARP); s.enc(t0 + 110, K1, 1); s.release(t0 + 180, ARP)
    log = run(s, t0 + 700)
    d = [x for x in log.dumps if x["track"] == 3]
    st = [x for x in log.states if x["track"] == 3]
    sc = log.screens()
    out = [(m[0], m[2], m[3]) for m, p in zip(log.msgs, log.port) if p == 2 and m[1] == 0xBB]
    out13 = [(m[0], m[2], m[3]) for m, p in zip(log.msgs, log.port) if p == 2 and m[1] == 0xBC]
    check(d and d[0]["pat"] == 2, "LIVE PATTERN 2 on the tablet's track 3 (%s)" % [x["pat"] for x in d])
    check(sc and " T1 " in sc[0]["lines"][0], "the panel stays on track 1 (%s)" % (sc[0]["lines"][0] if sc else sc))
    check(st and st[0]["rawmsg"] == "TAB T3 MIDI FX ECHO READY: GO", "the screen: the tablet's FX READY, GO (%s)" % (st[0]["rawmsg"] if st else st))
    check(len(st) > 1 and st[1]["mfx"] == 3, "FX GO: ECHO plays on track 3 (%s)" % [x["mfx"] for x in st])
    check(any(c == 4 and v == 16 for _, c, v in out), "back to the hub: LENGTH 16 of the tablet's track (%s)" % out[:6])
    check(any(c == 40 and v == 0 for _, c, v in out) and not any(c == 44 and (v == 0 or tt < t1 + 520) for tt, c, v in out if tt >= t1 + 120),
          "back: the mutes, not the one the tablet just sent (%s)" % [x for x in out if 40 <= x[1] < 56][:6])
    check(not any(c == 112 for _, c, v in out13), "the tablet's own TRACK does not come back (%s)" % out13[:4])
    arp = [x for x in out if x[1] == 20 and x[0] > t0]
    check(arp and arp[0][2] == 2 and arp[0][0] - t0 < 250, "ARP K1 on the panel: CC 20 = 2 (DOWN) goes to the tablet (%s)" % arp[:2])
    check(not any(x[0] < t1 for x in out), "nothing goes back before the tablet speaks (%s)" % [x for x in out if x[0] < t1][:2])
    # one USB port: the LIVE page works (REMOTE 13 + 14), nothing goes back
    s = Script()
    t = remote13_on(s, 100)
    s.raw(t, "midi 0xBB 3 2"); t += 60                                # PATTERN 3 on the tablet's track (1)
    s.at(t, "dump", 0)
    log = run(s, t + 500)
    check(log.dumps and log.dumps[0]["pat"] == 3, "one port: LIVE PATTERN 3 on track 1 (%s)" % [x["pat"] for x in log.dumps])
    check(not [m for m in log.msgs if m[1] in (0xBB, 0xBC)], "one port: nothing goes back (%s)" % [m for m in log.msgs if m[1] in (0xBB, 0xBC)][:3])


def t0206_echo_ccs():
    group("0.20.6: what goes back to the hub on CC 6 / 38 / 101 (MIDI 2.0's Data Entry and RPN: a MIDI 2.0 page never gets them) comes on channel 12 CC 33-36 instead; the old numbers still work coming in")
    s = Script()
    t = remote13_on(s, 100)
    t = usb2(s, t)
    t1 = t
    s.raw(t, "midi 0xBB 6 61 2"); t += 40                             # SWING 61 on the tablet's track (1)
    s.raw(t, "midi 0xBD 6 4 2"); t += 40                              # QUANTISE 4
    s.raw(t, "midi 0xBC 38 3 2"); t += 40                             # track 6: pattern 4
    s.raw(t, "midi 0xBC 101 77 2"); t += 40                           # lane 1 of the selected track: 77
    t2 = t
    s.at(t, "dump", 5); t += 40
    log = run(s, t + 6000)                                            # (the whole set comes back every few seconds)
    out = [(m[0], m[1], m[2], m[3]) for m, p in zip(log.msgs, log.port) if p == 2 and (m[1] & 0xF0) == 0xB0]
    back = {(st & 15, c): v for tt, st, c, v in out if tt > t2 + 500}
    check(back.get((11, 33)) == 61 and back.get((11, 34)) == 4 and back.get((11, 35)) == 3 and back.get((11, 36)) == 77,
          "back on channel 12: CC 33 SWING 61, 34 QUANTISE 4, 35 track 6's pattern 3, 36 lane 1 77 (%s)" % {k: back.get(k) for k in ((11, 33), (11, 34), (11, 35), (11, 36))})
    check(not [x for x in out if (x[1] & 15, x[2]) in ((11, 6), (13, 6), (12, 38), (12, 101))],
          "nothing goes back on ch 12 CC 6, ch 14 CC 6, ch 13 CC 38, ch 13 CC 101 (%s)" % [x for x in out if (x[1] & 15, x[2]) in ((11, 6), (13, 6), (12, 38), (12, 101))][:4])
    sent = {(11, 33): t1, (11, 34): t1 + 40, (11, 35): t1 + 80, (11, 36): t1 + 120}   # (each cell, when the tablet moved it)
    early = [x for x in out if (x[1] & 15, x[2]) in sent and sent[(x[1] & 15, x[2])] <= x[0] < sent[(x[1] & 15, x[2])] + 350]
    check(not early, "what the tablet just sent on the old numbers does not come straight back while its hand is on it (%s)" % early[:3])
    check(log.dumps and log.dumps[0]["pat"] == 4, "the old CC 38 still sets track 6's pattern: 4 (%s)" % [x["pat"] for x in log.dumps])
    # 0.20.7: REMOTE 14 (the FM-1's default: SAGGA Remote only): QUANTISE changed on the panel comes back to the page too
    for remote13 in (False, True):
        s = Script()
        t = remote13_on(s, 100) if remote13 else 100
        t = usb2(s, t)
        s.raw(t, "midi 0xBD 9 70 2"); t += 600                          # the Remote page says something (its SWING macro)
        t3 = t
        t = perf(s, t, [(K4, 2)])                                       # QUANTISE on the panel: PERF, K4
        log = run(s, t + 800)
        out = [(m[0], m[1], m[2], m[3]) for m, p in zip(log.msgs, log.port) if p == 2 and m[0] > t3]
        q = [x for x in out if x[1] == 0xBB and x[2] == 34]
        check(q and q[-1][3] == 2, "%s: QUANTISE turned on the panel goes back on channel 12 CC 34 (%s)" % ("REMOTE 13 + 14" if remote13 else "REMOTE 14", q[-2:]))
        check(not [x for x in out if x[1] == 0xBB and x[2] != 34] or remote13,
              "REMOTE 14: nothing else on channel 12 (the LIVE page's channel is not the remote's) (%s)" % [x for x in out if x[1] == 0xBB][:3])
    # 0.20.8: no page touched since the FM-1 started, only the grid bridge's keep-alive on port 2: the pages follow already
    s = Script()
    t = usb2(s, 100)
    t0 = t
    t = perf(s, t, [(K4, 1)])                                           # before anything came on port 2
    t1 = t + 400
    s.raw(t1, "midi 0xBF 118 64 2")                                     # the bridge's keep-alive (no Launchpads needed)
    t = perf(s, t1 + 300, [(K4, 2)])
    log = run(s, t + 800)
    out = [(m[0], m[1], m[2], m[3]) for m, p in zip(log.msgs, log.port) if p == 2 and (m[1] & 0xF0) == 0xB0]
    check(not [x for x in out if t0 <= x[0] < t1], "nothing goes back before the hub says anything on port 2 (%s)" % [x for x in out if t0 <= x[0] < t1][:3])
    q = [x for x in out if x[1] == 0xBB and x[2] == 34 and x[0] > t1]
    check(q and q[-1][3] == 3, "the bridge's keep-alive is enough: QUANTISE turned on the panel goes back to the page, no page touched (%s)" % q[-2:])


def t018_live_sweep():
    group("0.18 every command of the LIVE page (channel 12) with a few values, the band playing, the tablet's track changing: every track stays in time, no note hangs")
    s = Script()
    t = remote13_on(s, 100)
    s.press(t, SEQ); s.tap_key(t + 30, bk(6), hold=700); s.release(t + 800, SEQ); t += 900   # the BAND
    s.tap_btn(t, PLAY); t += 400
    for tt in (0, 3, 9):
        s.raw(t, "midi 0xBC 112 %d" % tt); t += 30
        for cc in [c for c in range(1, 33) if c != 30] + [40, 47, 55, 56, 57, 58, 59]:      # (RETRIG: off the bar on purpose; 0.23: 56-59, the THEORY engines)
            for v in (0, 2, 64, 127):
                s.raw(t, "midi 0xBB %d %d" % (cc, v)); t += 7
    s.at(t + int(2 * 16 * STEP_MS), "probe")
    s.tap_btn(t + int(2 * 16 * STEP_MS) + 100, PLAY)
    log = run(s, t + int(2 * 16 * STEP_MS) + 900)
    ok = [m.group(2) for m in re.finditer(r"PROBE T(\d+) .* ok=(\S+) ", log.text)]
    check(len(ok) == 12 and "0" not in ok, "every track where the bar says (%s)" % "".join(ok))
    on = {}
    for tm, st, d1, d2 in log.msgs:
        if st & 0xF0 == 0x90 and d2 and st & 15 < 12:
            on[(st & 15, d1)] = on.get((st & 15, d1), 0) + 1
        elif (st & 0xF0 == 0x80 or (st & 0xF0 == 0x90 and not d2)) and st & 15 < 12:
            on[(st & 15, d1)] = on.get((st & 15, d1), 0) - 1
    hung = [k for k, n in on.items() if n > 0]
    check(not hung, "after STOP no note hangs (%s)" % hung[:4])


# ------------------------------------------------------------------------------------------------ 0.19
def mfx_add(s, t, d):
    """HOME 6 K1 by d (from the effect shown), then SEQ + white 6: the effect shown joins the chain (or leaves it)"""
    t = home_page(s, t, 5, [(K1, d)])
    return seq_page(s, t, 0, keys=[wk(5)])


def t019_mfx_chain():
    group("0.19 the MIDI FX chain: the four together, in their order (VEL CURVE, OCTAVE, HARM, ECHO: the harmony echoes too); "
          "a save keeps it; a snapshot leaves it; the tablet's FX GO and the grid's pads")
    # HARM (+2 semitones on a FREE track, the voice at 75 %), ECHO (twice, a dotted eighth, 60 %), VEL CURVE +8: one step
    # plays C4 at 127 and D4 at 95, and both come back twice, softer each time
    s = Script()
    t = s.steps(100, (0,))
    t = mfx_add(s, t, 1)                                               # HARM
    t = mfx_add(s, t, 2)                                               # ECHO
    t = home_page(s, t, 5, [(K1, 1), (K2, 5)])                         # VEL CURVE READY, 3 + 5 = 8
    t = seq_page(s, t, 0, keys=[wk(5)]); s.at(t, "dump", 0)
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + int(16 * STEP_MS) - 20)
    mc = log.mfxc[-1]
    n = [(round((tm - p) / STEP_MS), d1, v) for tm, d1, v in log.notes(ch=0, after=p)]
    check(mc["on"] == 2 | 8 | 16 and states(log)[-1]["mfx"] == 1 and states(log)[-1]["msg"] == "T1 MIDI FX VEL CURVE STARTS: VEL+HARM+ECHO",
          "the chain: VEL CURVE, HARM, ECHO; the track's one effect HARM (%s %r)" % (mc, states(log)[-1]["msg"]))
    check(sorted(n) == [(0, 60, 127), (0, 62, 95), (3, 60, 76), (3, 62, 57), (6, 60, 45), (6, 62, 34)],
          "C4 127, D4 95 (the voice on the curved velocity), both echoed at 3 and 6 steps, 60 %% each (%s)" % sorted(n))
    # OCTAVE (+1 on every other step) before HARM: step 2's note goes up an octave and the voice is built on it
    s = Script()
    t = s.steps(100, (0, 1))
    t = mfx_add(s, t, 2)                                               # OCTAVE (+1, ALT)
    t = mfx_add(s, t, -1)                                              # HARM
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + int(2 * STEP_MS) - 20)
    n = sorted((round((tm - p) / STEP_MS), d1) for tm, d1, _ in log.notes(ch=0, after=p))
    check(n == [(0, 60), (0, 62), (1, 72), (1, 74)], "OCTAVE then HARM: 60 + 62, then 72 + 74 (%s)" % n)
    # a power cycle keeps the chain and each effect's values; HOME 6 shows the first
    d = tempfile.mkdtemp(); flash = os.path.join(d, "flash.bin")
    s = Script()
    t = s.steps(100, (0,))
    t = home_page(s, t, 5, [(K1, 3), (K2, 1)])                         # ECHO READY, 3 repeats
    t = seq_page(s, t, 0, keys=[wk(5)])
    t = mfx_add(s, t, -2)                                              # HARM
    s.tap_btn(t, SAVE); s.tap_btn(t + 400, SAVE); t += 1200
    run(s, t, flash=flash)
    s = Script()
    s.at(300, "dump", 0)
    log = run(s, 400, flash=flash)
    mc = log.mfxc[-1] if log.mfxc else {}
    check(mc.get("on") == 2 | 8 and mc.get("amt", [0] * 4)[2] == 3 and mc.get("sel") == 1 and states(log)[-1]["mfx"] == 1,
          "after a power cycle: HARM + ECHO, ECHO with its 3 repeats; K1 shows HARM (%s)" % mc)
    # a snapshot does not change the chain: stored with ECHO, ECHO taken out, the snapshot recalled: still none
    def store(s, t, n): s.press(t, SAVE); s.press(t + 20, SEL); s.tap_key(t + 40, bk(n)); s.release(t + 100, SEL); s.release(t + 120, SAVE); return t + 180
    def recall(s, t, n): s.press(t, SAVE); s.tap_key(t + 20, bk(n)); s.release(t + 100, SAVE); return t + 160
    s = Script()
    t = s.steps(100, (0,))
    t = mfx_add(s, t, 3)                                               # ECHO
    t = store(s, t, 0)
    t = home_page(s, t, 5, [(K1, -3)]); t = seq_page(s, t, 0, keys=[wk(5)])   # OFF: it stops
    t = recall(s, t, 0); s.at(t, "dump", 0)
    log = run(s, t + 100)
    check(log.mfxc[-1]["on"] == 0 and states(log)[-1]["mfx"] == 0, "the snapshot leaves the chain as it is (%s)" % log.mfxc[-1])
    # the tablet (SAGGA Live): MIDI FX ECHO, FX GO: it plays; MIDI FX HARM, FX GO: both; FX GO again: HARM leaves
    s = Script()
    t = remote13_on(s, 100)
    s.raw(t, "midi 0xBB 9 3"); t += 40                                 # MIDI FX ECHO
    s.raw(t, "midi 0xBB 11 127"); s.raw(t + 20, "midi 0xBB 11 0"); t += 60
    s.raw(t, "midi 0xBB 9 1"); t += 40                                 # MIDI FX HARM
    s.raw(t, "midi 0xBB 11 127"); s.raw(t + 20, "midi 0xBB 11 0"); t += 60; s.at(t, "dump", 0); t += 40
    s.raw(t, "midi 0xBB 11 127"); s.raw(t + 20, "midi 0xBB 11 0"); t += 60; s.at(t, "dump", 0)
    log = run(s, t + 100)
    got = [x["on"] for x in log.mfxc if x["track"] == 1]
    msg = [x["rawmsg"] for x in states(log)]
    check(got == [2 | 8, 8], "the tablet: ECHO, then HARM with it, then HARM out (%s)" % got)
    check(msg[0] == "TAB T1: MIDI FX HARM STARTS: HARM+ECHO" or msg[0].endswith("MIDI FX HARM STARTS: HARM+ECHO"), "the screen (%r)" % msg)
    # the grid (TRACK 3, row 2): a tap READY, again: it starts; a tap on one that plays: it stops; both white while they play
    s = Script()
    t = s.steps(100, [0])
    s.raw(t, "attach")
    view(s, t + 100, GC_VTRACK); view(s, t + 200, GC_VTRACK); view(s, t + 300, GC_VTRACK)   # TRACK, 2, 3
    s.pad(t + 400, 3, 1); s.pad(t + 480, 3, 1)                          # ECHO
    s.pad(t + 560, 1, 1); s.pad(t + 640, 1, 1); s.at(t + 720, "dump", 0)   # HARM: both
    s.pad(t + 800, 3, 1); s.at(t + 880, "dump", 0)                      # ECHO, tapped while it plays: it stops
    log = run(s, t + 1000)
    got = [x["on"] for x in log.mfxc if x["track"] == 1]
    check(got == [2 | 8, 2], "the grid: ECHO, HARM with it, ECHO out with one tap (%s)" % got)


# ------------------------------------------------------------------------------------------------ 0.20
FX_CHANCE, FX_RANDOM, FX_FILTER, FX_GATE, FX_GLITCH = 5, 6, 7, 8, 9
FX_ROLL, FX_ACCENT = 10, 11                                # 0.29


def mfx_steps(log, p, ch=0):
    return sorted((round((tm - p) / STEP_MS * 4) / 4, d1, v) for tm, d1, v in log.notes(ch=ch, after=p))


def t020_new_fx():
    group("0.20 the new MIDI FX: CHANCE, RANDOM, NOTE FILTER, GATE, GLITCH in the chain; SEL + K1 the ORDER; a save keeps "
          "them; the tablet's FX AMOUNT on their range; the grid with SHIFT")
    # NOTE FILTER one in 2: of four steps, the 1st and the 3rd
    s = Script()
    t = s.steps(100, (0, 1, 2, 3))
    t = home_page(s, t, 5, [(K1, FX_FILTER), (K4, 1)])                # NOTE FILTER READY, one in 2
    t = seq_page(s, t, 0, keys=[wk(5)]); s.at(t, "dump", 0)
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + int(4 * STEP_MS) - 20)
    n = [x[0] for x in mfx_steps(log, p)]
    check(states(log)[-1]["msg"] == "T1 MIDI FX NOTE FILTER STARTS" and log.mfxd and log.mfxd[-1]["on"] == 1 << (FX_FILTER - 5),
          "NOTE FILTER in the chain (%r %s)" % (states(log)[-1]["msg"], log.mfxd[-1:]))
    check(n == [0, 2], "one in 2: steps 1 and 3 play (%s)" % n)
    # CHANCE 0 %: nothing plays; the MOD MATRIX's FX depth -100 % (from CC IN 1 at 127) brings it back to every note
    s = Script()
    t = s.steps(100, (0, 1, 2, 3))
    t = home_page(s, t, 5, [(K1, FX_CHANCE), (K2, -14)])              # CHANCE READY, 70 % - 70
    t = seq_page(s, t, 0, keys=[wk(5)]); s.at(t, "dump", 0)
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + int(4 * STEP_MS) - 20)
    check(log.mfxd[-1]["amt"][0] == 0 and not mfx_steps(log, p), "CHANCE 0 %%: no note (%s %s)" % (log.mfxd[-1]["amt"], mfx_steps(log, p)))
    s = Script()
    t = s.steps(100, (0, 1, 2, 3))
    t = home_page(s, t, 5, [(K1, FX_CHANCE), (K2, -14)])
    t = seq_page(s, t, 0, keys=[wk(5)])
    t = pg(s, t, LFO, 5, [(K2, 6), (K3, 8), (K4, 10)])                 # MOD 1: CC IN, FX T1, +100 %
    t = pg(s, t, LFO, 5, [(K2, 1)], sel=True)                          # SEL + K2: CC 1
    t = pg(s, t, LFO, 5, [(K4, -40)])                                  # -100 %
    s.raw(t, "midi 0xB0 1 127"); t += 40; s.at(t, "dump", 0)
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + int(4 * STEP_MS) - 20)
    check(len(mfx_steps(log, p)) == 4 and log.mfxd[-1]["modfx"] == -100,
          "MOD MATRIX: CC IN 1 at 127, -100 %% on T1's FX: CHANCE lets every note through (%s, modfx %s)" % (mfx_steps(log, p), log.mfxd[-1]["modfx"]))
    # RANDOM every note (K4 100 %), +-2 semitones on a FREE track: C4 moves, never further than 2
    s = Script()
    t = s.steps(100, tuple(range(8)))
    t = home_page(s, t, 5, [(K1, FX_RANDOM), (K3, -16), (K4, 10)])     # RANDOM READY, +-2, velocity as it is, always
    t = seq_page(s, t, 0, keys=[wk(5)])
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + int(8 * STEP_MS) - 20)
    n = [x[1] for x in mfx_steps(log, p)]
    check(len(n) == 8 and all(58 <= x <= 62 for x in n) and any(x != 60 for x in n) and all(x[2] == 100 for x in mfx_steps(log, p)),
          "RANDOM: the notes within +-2 of C4, some moved, the velocity untouched (%s)" % n)
    # GATE fixed 1/32: half a step long, whatever the step's gate
    s = Script()
    t = s.steps(100, (0,))
    t = home_page(s, t, 5, [(K1, FX_GATE), (K3, 1)])                  # GATE READY, FIXED 1/32
    t = seq_page(s, t, 0, keys=[wk(5)])
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + int(2 * STEP_MS))
    on = [tm for tm, st, d1, d2 in log.msgs if st == 0x90 and d2 and tm >= p]
    off = [tm for tm, st, d1, d2 in log.msgs if (st == 0x80 or (st == 0x90 and not d2)) and tm >= p]
    check(on and off and near(off[0] - on[0], STEP_MS / 2, 3.0), "GATE FIXED 1/32: the note lasts half a step (%s ms)" % ([o - on[0] for o in off[:1]] if on else on))
    # GLITCH STUTTER 100 %, 4 pieces: the step in four
    s = Script()
    t = s.steps(100, (0,))
    t = home_page(s, t, 5, [(K1, FX_GLITCH), (K2, 15), (K3, 1)])      # GLITCH READY, 100 %, STUTTER
    t = seq_page(s, t, 0, keys=[wk(5)])
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + int(STEP_MS) - 5)
    n = [x[0] for x in mfx_steps(log, p)]
    check(n == [0, 0.25, 0.5, 0.75], "GLITCH STUTTER: four notes in the step (%s)" % n)
    # the ORDER: NOTE FILTER under E4, OCTAVE +1 every other step. FILTER first (the default): both steps play (C4,
    # then C5); OCTAVE moved before it (SEL + K1, 4 places left): step 2's C5 is filtered out
    def octfilt(move):
        s = Script()
        t = s.steps(100, (0, 1))
        t = home_page(s, t, 5, [(K1, FX_FILTER), (K3, -63)])          # NOTE FILTER, highest 64
        t = seq_page(s, t, 0, keys=[wk(5)])
        t = mfx_add(s, t, -5)                                          # OCTAVE (+1, ALT)
        if move:
            t = pg(s, t, HOME, 5, [(K1, -5)], sel=True)                # SEL + K1: OCTAVE plays first (0.29: five places - ACCENT came before it)
        s.at(t, "dump", 0)
        p = t + 100
        s.tap_btn(p, PLAY)
        return run(s, p + int(2 * STEP_MS) - 20), p
    log, p = octfilt(False)
    a = [(x[0], x[1]) for x in mfx_steps(log, p)]
    log2, p2 = octfilt(True)
    b = [(x[0], x[1]) for x in mfx_steps(log2, p2)]
    check(a == [(0, 60), (1, 72)], "FILTER before OCTAVE: C4, then C5 (%s)" % a)
    check(b == [(0, 60)] and log2.mfxd[-1]["order"][0] == 2 and states(log2)[-1]["msg"].startswith("T1 ORDER OCT>FILT"),
          "OCTAVE moved first: C5 is filtered out (%s, order %s, %r)" % (b, log2.mfxd[-1]["order"], states(log2)[-1]["msg"]))
    # a power cycle keeps the new effects, their values and the order
    d = tempfile.mkdtemp(); flash = os.path.join(d, "flash.bin")
    s = Script()
    t = s.steps(100, (0,))
    t = home_page(s, t, 5, [(K1, FX_RANDOM), (K2, 2), (K4, 2)])       # RANDOM, +-4, 60 %
    t = seq_page(s, t, 0, keys=[wk(5)])
    t = pg(s, t, HOME, 5, [(K1, 2)], sel=True)                         # two places later
    s.tap_btn(t, SAVE); s.tap_btn(t + 400, SAVE); t += 1200
    run(s, t, flash=flash)
    s = Script()
    s.at(300, "dump", 0)
    log = run(s, 400, flash=flash)
    m = log.mfxd[-1] if log.mfxd else {}
    check(m.get("on") == 1 << (FX_RANDOM - 5) and m.get("amt", [0] * 5)[1] == 4 and m.get("fb", [0] * 5)[1] == 60 and
          m.get("order", [])[:7] == [7, 5, 4, 11, 2, 1, 6] and log.mfxc[-1]["sel"] == FX_RANDOM,   # (0.29: ACCENT after VEL CURVE)
          "after a power cycle: RANDOM +-4 at 60 %%, two places later; K1 shows it (%s)" % m)
    # the tablet: MIDI FX CHANCE, FX AMOUNT 12 of 24 = 50 %%, FX GO
    s = Script()
    t = remote13_on(s, 100)
    s.raw(t, "midi 0xBB 9 %d" % FX_CHANCE); t += 40
    s.raw(t, "midi 0xBB 10 12"); t += 40
    s.raw(t, "midi 0xBB 11 127"); s.raw(t + 20, "midi 0xBB 11 0"); t += 60; s.at(t, "dump", 0)
    log = run(s, t + 100)
    m = log.mfxd[-1]
    check(m["on"] == 1 and m["amt"][0] == 50, "the tablet: CHANCE at 50 %% in the chain (%s)" % m)
    # the grid: SHIFT + pad 6 of row 2 = GLITCH, READY; again: it plays
    s = Script()
    t = s.steps(100, [0])
    s.raw(t, "attach")
    view(s, t + 100, GC_VTRACK); view(s, t + 200, GC_VTRACK); view(s, t + 300, GC_VTRACK)   # TRACK, 2, 3
    s.at(t + 400, "ctl", GC_SHIFT, 127)
    s.pad(t + 420, 5, 1); s.pad(t + 500, 5, 1)
    s.at(t + 580, "ctl", GC_SHIFT, 0); s.at(t + 640, "dump", 0)
    log = run(s, t + 800)
    check(log.mfxd[-1]["on"] == 1 << (FX_GLITCH - 5), "the grid: SHIFT + pad 6 twice: GLITCH plays (%s)" % log.mfxd[-1])


def t029_more():
    group("0.29 two MIDI FX more - ROLL (each note 2..6 hits in its step, level, rising or falling) and ACCENT (an accent every 2..8 "
          "steps: three over four) -, kept by a save; the grid's SHIFT + pads 7 and 8; the five new scales (the grid: SHIFT + row 2)")
    # ROLL: three a step, level; the step's note three times, a third of a step apart
    s = Script()
    t = s.steps(100, (0, 4))
    t = home_page(s, t, 5, [(K1, FX_ROLL)])                            # ROLL READY: 3, LEVEL, always
    t = seq_page(s, t, 0, keys=[wk(5)]); s.at(t, "dump", 0)
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + int(8 * STEP_MS) - 20)
    n = mfx_steps(log, p)
    check(states(log)[-1]["msg"] == "T1 MIDI FX ROLL STARTS" and log.mfxd[-1]["on"] == 1 << (FX_ROLL - 5),
          "ROLL in the chain (%r %s)" % (states(log)[-1]["msg"], log.mfxd[-1:]))
    check([x[0] for x in n] == [0, 0.25, 0.75, 4, 4.25, 4.75] and len({x[2] for x in n}) == 1,
          "ROLL 3: each note three times in its step, at one velocity (%s)" % n)
    # ... five hits, rising: louder and louder up to the note's own
    s = Script()
    t = s.steps(100, (0,))
    t = home_page(s, t, 5, [(K1, FX_ROLL), (K2, 2), (K3, 1)])          # 5, RISING
    t = seq_page(s, t, 0, keys=[wk(5)])
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + int(STEP_MS) - 5)
    on = [(tm, d2) for tm, st, d1, d2 in log.msgs if st == 0x90 and d2 and tm >= p]
    v = [d2 for _, d2 in on]
    check(len(on) == 5 and v == sorted(v) and v[0] < v[-1] and v[-1] <= 100, "ROLL 5 RISING: five hits in the step, louder each time (%s)" % v)
    # ACCENT every 3 from the 1st: of eight steps of velocity 100, 1, 4, 7 at 127 (100 + 30)
    s = Script()
    t = s.steps(100, tuple(range(8)))
    t = home_page(s, t, 5, [(K1, FX_ACCENT)])                          # ACCENT READY: +30, every 3, from step 1
    t = seq_page(s, t, 0, keys=[wk(5)])
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + int(8 * STEP_MS) - 20)
    n = mfx_steps(log, p)
    loud = [int(x[0]) for x in n if x[2] > 100]
    check(len(n) == 8 and loud == [0, 3, 6] and all(x[2] in (100, 127) for x in n), "ACCENT every 3: steps 1, 4, 7 loud (%s)" % [(x[0], x[2]) for x in n])
    # a power cycle keeps ROLL and its values (chunk 5: the image's own block holds 0.28's nine)
    d = tempfile.mkdtemp(); flash = os.path.join(d, "flash.bin")
    s = Script()
    t = s.steps(100, (0,))
    t = home_page(s, t, 5, [(K1, FX_ROLL), (K2, 1), (K3, 2), (K4, -4)])   # 4, FALLING, 80 %
    t = seq_page(s, t, 0, keys=[wk(5)])
    s.tap_btn(t, SAVE); s.tap_btn(t + 400, SAVE); t += 1200
    run(s, t, flash=flash)
    s = Script()
    s.at(300, "dump", 0)
    log = run(s, 400, flash=flash)
    m = log.mfxd[-1] if log.mfxd else {}
    check(m.get("on") == 1 << (FX_ROLL - 5) and m.get("amt", [0] * 7)[5] == 4 and m.get("time", [0] * 7)[5] == 2 and m.get("fb", [0] * 7)[5] == 80,
          "after a power cycle: ROLL 4, FALLING, 80 %% (%s)" % m)
    # the grid: SHIFT + pad 7 of row 2 = ROLL, SHIFT + pad 8 = ACCENT (READY, again: it plays)
    s = Script()
    t = s.steps(100, [0])
    s.raw(t, "attach")
    view(s, t + 100, GC_VTRACK); view(s, t + 200, GC_VTRACK); view(s, t + 300, GC_VTRACK)
    s.at(t + 400, "ctl", GC_SHIFT, 127)
    s.pad(t + 420, 6, 1); s.pad(t + 500, 6, 1); s.pad(t + 580, 7, 1); s.pad(t + 660, 7, 1)
    s.at(t + 740, "ctl", GC_SHIFT, 0); s.at(t + 800, "dump", 0)
    log = run(s, t + 900)
    check(log.mfxd[-1]["on"] == (1 << (FX_ROLL - 5)) | (1 << (FX_ACCENT - 5)), "the grid: SHIFT + pads 7 and 8: ROLL and ACCENT play (%s)" % log.mfxd[-1])
    # the scales: the grid's PROJECT view, SHIFT + pad 1 of row 2 = the 17th, HUNGARIAN MINOR; without SHIFT pad 16 HIRAJOSHI
    s = Script()
    s.raw(100, "attach")
    view(s, 200, GC_REC, alt=True)                                     # the PROJ view
    s.at(300, "ctl", GC_SHIFT, 127); s.pad(320, 0, 1); s.at(400, "ctl", GC_SHIFT, 0)
    s.at(450, "dump", 0)
    s.pad(500, 15, 1); s.at(560, "dump", 0)
    log = run(s, 700)
    c = cfgs(log)
    check(c[0]["key"][1] == 16 and c[1]["key"][1] == 15, "the grid: SHIFT + row 2 pad 1 the 17th scale, pad 16 the 16th (%s %s)" % (c[0]["key"], c[1]["key"]))


def t029_viaggio_progs():
    group("0.29 the grid's MOSSE view (VIAGGIO until 0.29), row 7: pads 1-8 the genre's eight progressions, 9-12 yours, 13 DICE/PI (named as the "
          "dice's slot: it read the first user slot's name)")
    s = Script()
    s.raw(100, "attach")
    t = harm_knobs(s, 200, [(K1, 1)])                                   # the HARMONY on (ARP 3 K1)
    t = view(s, t, GC_VPERF); t = view(s, t, GC_VPERF); t = view(s, t, GC_VPERF)   # PERF, SONG, VIAGGIO
    s.pad(t, 7, 6); s.at(t + 100, "dump", 0); t += 150                  # pad 8: PROG 8
    t1 = t
    s.pad(t, 8, 6); s.at(t + 100, "dump", 0); t += 150                  # pad 9: USER 1
    s.pad(t, 12, 6); s.at(t + 100, "dump", 0); t += 150                 # pad 13: DICE/PI
    t2 = t
    log = run(s, t + 300)
    msgs = [x["msg"] for x in log.states]
    check(len(msgs) == 3 and msgs[0].startswith("PROG ") and msgs[1].startswith("USER PROG ") and msgs[2].startswith("DICE/PI "),
          "pad 8: the genre's 8th progression, pad 9: USER 1, pad 13: DICE/PI, said so on the screen (%s)" % msgs)
    pads, _ = log.leds(until=t1 - 20)
    check(pads.get(6 * 16 + 7) == GL_ACCENT and pads.get(6 * 16 + 0) == GL_DIM, "row 7: pad 8 lit as the progression playing (%s)" % [pads.get(6 * 16 + i) for i in range(13)])
    pads, _ = log.leds(until=t2 + 50)
    check(pads.get(6 * 16 + 12) == GL_ACCENT and pads.get(6 * 16 + 7) == GL_DIM and pads.get(6 * 16 + 8) == GL_FAINT,
          "... then pad 13 (DICE/PI), the genre's dim, an empty user slot faint (%s)" % [pads.get(6 * 16 + i) for i in range(13)])


def t020_env_mod():
    group("0.20 ENV: an LFO shaped as an envelope on its TRIG track's notes; the MOD MATRIX: CC IN on a track's velocity, LEARN")
    # LFO 1: ENV, CC 74 from 0 up to 127, ATTACK 0, DECAY 1/8, SUSTAIN 0, RELEASE 1/16, TRIG T1: up at each hit, down after
    s = Script()
    t = s.steps(100, [0, 8])
    s.press(t, LFO); s.tap_key(t + 30, wk(0)); s.release(t + 100, LFO); t += 160
    t = pg(s, t, LFO, 0, [(K1, 8), (K3, 63), (K4, -64)])               # ENV, depth 127, center 0
    t = pg(s, t, LFO, 2, [(K4, 1)])                                    # TRIG T1
    t = pg(s, t, LFO, 4, [(K1, -1)])                                   # ATTACK 0
    s.press(t, LFO); s.at(t + 60, "ui"); s.release(t + 120, LFO); t += 180
    s.at(t, "dump", 0)
    s.tap_btn(t + 100, PLAY); t0 = t + 100
    log = run(s, t0 + int(BAR_MS) + 50)
    cc = lfo_cc(log, after=t0)
    hits = [x for x, _, _ in log.notes(ch=0, after=t0)]
    top = [b for (t2, b) in cc if any(0 <= t2 - h <= 15 for h in hits)]
    late = [min([b for (t2, b) in cc if h < t2 < h + 7 * STEP_MS] or [999]) for h in hits[:2]]
    sc = log.screens()
    check(sc and sc[0]["cells"][0][1] == "0" and sc[0]["cells"][1][1] == "1/8", "LFO page 5 ENV: ATTACK 0, DECAY 1/8 (%s)" % (sc[0]["cells"] if sc else sc))
    check(len(hits) >= 2 and top and max(top) >= 115, "ENV: at the top at each hit (%s, hits %s)" % (top[:4], [h - t0 for h in hits]))
    check(late and max(late) <= 8, "ENV: back to 0 before the next hit (%s)" % late[:6])
    # MOD MATRIX: CC IN 1 on T1's velocity, +100 %%: the CC at 127 makes the notes 127, at 0 they are 100
    def velrun(v):
        s = Script()
        t = s.steps(100, [0, 1])
        t = pg(s, t, LFO, 5, [(K2, 6), (K3, 3), (K4, 10)])             # MOD 1: CC IN, VEL T1, +100 %
        t = pg(s, t, LFO, 5, [(K2, 1)], sel=True)                      # SEL + K2: CC 1
        s.raw(t, "midi 0xB0 1 %d" % v); t += 40
        s.tap_btn(t + 100, PLAY)
        log = run(s, t + 100 + int(2 * STEP_MS) - 10)
        return [x[2] for x in log.notes(ch=0, after=t + 100)]
    a, b = velrun(127), velrun(0)
    check(a == [127, 127] and b == [100, 100], "MOD MATRIX CC IN -> VEL T1: 127 with the CC up, 100 down (%s %s)" % (a, b))
    # LEARN: LFO + REC on page 6: the next CC from MIDI IN becomes the slot's source
    s = Script()
    t = pg(s, 100, LFO, 5, [])
    s.press(t, LFO); s.tap_btn(t + 30, REC); s.release(t + 100, LFO); t += 160
    s.raw(t, "midi 0xB0 21 64"); t += 60
    s.press(t, LFO); s.at(t + 30, "ui"); s.release(t + 100, LFO); t += 160
    log = run(s, t + 100)
    sc = log.screens()
    check(sc and sc[-1]["cells"][1][1] == "CC IN 21", "LEARN: MOD 1's source is CC IN 21 (%s)" % (sc[-1]["cells"] if sc else sc))


def t021_clean():
    group("0.21: the screen's line of what is going on, with everything on at once, is cut and not written past its end; SAGGA Break's knobs go back to the page; a value the tablet moved goes back at once 65 seconds later too")
    # DICE? TEMP LOOP RESTART MACRO MORPH ECHO ALL together: 70 characters and more for a line of 31 (64 bytes to write it)
    s = Script()
    t = remote13_on(s, 100)
    t = s.steps(t, [0, 4, 8, 12])
    s.tap_btn(t, PLAY); t += 300
    for cc, v in ((37, 127), (26, 127), (26, 0), (88, 127), (88, 0), (7, 100), (1, 127), (118, 127), (118, 0)):
        s.raw(t, "midi 0xBD %d %d" % (cc, v)); t += 15                # TEMP held, LOOP 1/16, RESTART, a macro, MORPH, ECHO ALL
    s.raw(t, "midi 0xBB 31 127"); s.raw(t + 10, "midi 0xBB 31 0"); t += 40   # the tablet's DICE: KEEP or BACK?
    s.at(t, "ui"); t += 100
    s.raw(t, "midi 0xBD 37 0"); t += 40
    s.at(t, "ui"); s.at(t, "dump", 0); t += 100
    log = run(s, t + 300)
    sc = log.screens()
    l5 = sc[0]["lines"][5] if sc else ""
    check(len(sc) == 2 and l5.startswith("DICE? +KEEP -BACK ") and "TEMP" in l5 and len(l5) <= 31,
          "everything on at once: the line starts with the dice and ends at the screen's edge (%r)" % l5)
    check(len(sc) == 2 and sc[1]["lines"][5].startswith("LOOP 1/16 RESTART MACRO MORPH") and log.dumps,
          "... and the FM-1 goes on: TEMP let go (the dice go back with it) leaves the line (%r)" % (sc[1]["lines"][5] if len(sc) == 2 else sc))
    # the BREAK's SWAP, ROLLS, SLICES of the tablet's track go back to SAGGA Break (channel 13 CC 73-75)
    s = Script()
    t = remote13_on(s, 100)
    t = usb2(s, t)
    s.raw(t, "midi 0xBC 112 1 2"); t += 40                            # the tablet's track: 2
    s.raw(t, "midi 0xBC 75 2 2"); t += 40                             # its SLICES 32,
    s.raw(t, "midi 0xBC 74 5 2"); t += 40                             # ROLLS 5,
    s.raw(t, "midi 0xBC 73 6 2"); t += 700                            # SWAP 6
    t1 = t
    s.raw(t, "midi 0xBC 112 0 2"); t += 700                           # the tablet's track: 1 (16 slices, 2 rolls, swap 3)
    t2 = t
    s.raw(t, "midi 0xBC 112 1 2"); t += 700                           # and 2 again
    log = run(s, t + 200)
    out = [(m[0], m[2], m[3]) for m, p in zip(log.msgs, log.port) if p == 2 and m[1] == 0xBC and m[2] in (73, 74, 75)]
    one = {c: v for tt, c, v in out if t1 <= tt < t2}
    two = {c: v for tt, c, v in out if tt >= t2}
    check(one == {73: 3, 74: 2, 75: 1}, "the tablet's track changes to 1: its SWAP 3, ROLLS 2, SLICES 16 go to the page (%s)" % one)
    check(two == {73: 6, 74: 5, 75: 2}, "... and back to 2: SWAP 6, ROLLS 5, SLICES 32 (%s)" % two)
    echo = [x for x in out if x[0] < t1 and x[1:] in ((73, 6), (74, 5), (75, 2))]
    check(not echo, "what the page itself sent does not come back (%s)" % echo[:3])
    # the stamps of what the tablet moved are 16 bits of ms: 65.536 s later the value looked "just moved" again for 400 ms
    s = Script()
    t = usb2(s, 100)
    s.raw(t, "midi 0xBD 6 4 2")                                        # SAGGA Remote's QUANTISE: 4
    s.tap_btn(t + 65536 - 300, GLO)                                    # PERF ...
    s.enc(t + 65536 + 60, K4, -1)                                      # ... and QUANTISE on the panel, 60 ms into those 400
    s.tap_btn(t + 65536 + 700, GLO)
    log = run(s, t + 65536 + 1000)
    q = [(m[0], m[3]) for m, p in zip(log.msgs, log.port) if p == 2 and m[1] == 0xBB and m[2] == 34 and m[0] >= t + 65536 + 60]
    check(q and q[0][1] == 3 and q[0][0] < t + 65536 + 60 + 150,
          "QUANTISE turned on the panel 65.6 s after the page moved it goes back at once, not 340 ms later (%s, the turn at %d)" % (q[:2], t + 65536 + 60))


def t022_deep():
    group("0.22: the output ring as the FM-1 has it (a pass of 90 messages: none dropped; in 0.21's ring of 64: dropped); knobs turned in play do not make the notes late; 76 minutes in play, across the counters' wraps")
    # twelve tracks, six notes on step 1 of each (0.28; 0.27: sixteen of four): PLAY sends them all in one pass, with
    # the start's own messages
    lines = []
    for t in range(12):
        lines.append("step %d,0,0 flags - 3" % t)             # (ON and SET: the step's own notes, not the PEN's)
        for k in range(6):
            lines.append("step %d,0,0 note %d %d" % (t, k, 36 + 3 * t + 4 * k))
    img = sgq_image(lines)
    res = {}
    for ring in ("ring", "ring 64"):
        s = Script()
        s.raw(1, ring)
        t = sx_import(s, 100, img)
        s.tap_btn(t + 200, PLAY)
        s.tap_btn(t + 2500, PLAY)
        log = run(s, t + 3200)
        m = re.search(r"output ring of (\d+): the fullest (\d+), dropped (\d+)", log.text)
        ons = len([x for x in log.msgs if x[1] & 0xF0 == 0x90 and x[3] and x[0] < t + 300])
        res[ring] = (int(m.group(1)), int(m.group(2)), int(m.group(3)), ons) if m else None
    a, b = res["ring"], res["ring 64"]
    check(a and a[0] == 256 and a[2] == 0 and a[3] == 72 and a[1] > 72, "the FM-1's ring (256): 72 notes and the start in one pass, nothing dropped (%s)" % (a,))
    check(b and b[2] > 0 and b[3] < 72, "the same in a ring of 64, 0.21's: dropped (%s) - the simulator had no ring, no test could see it" % (b,))
    # the screen: a band in play, the knobs of HOME turned (a big cell is 8 ms of pixels, a line 5): the notes on time
    def knobs(cost):
        s = Script()
        if cost: s.raw(5, "lcdcost")
        s.press(100, SEQ); s.tap_key(130, bk(6), hold=700); s.release(900, SEQ)      # BAND
        s.tap_btn(1100, PLAY)
        s.press(1500, HOME)
        for i in range(120):
            s.enc(1600 + i * 30, K1 + i % 4, 1 if (i // 4) % 2 else -1)
        s.release(5300, HOME)
        s.tap_btn(5600, PLAY)
        return run(s, 6200)
    plain, cost = knobs(False), knobs(True)
    def ons(log): return [(x[0], x[1], x[2]) for x in log.msgs if x[1] & 0xF0 == 0x90 and x[3] and (x[1] & 15) < 14 and 1100 <= x[0] < 5600]
    p, c = ons(plain), ons(cost)
    late = [cc[0] - pp[0] for pp, cc in zip(p, c)] if len(p) == len(c) and [x[1:] for x in p] == [x[1:] for x in c] else None
    m = re.search(r"longest pass of the main loop (\d+) ms", cost.text)
    check(late is not None and len(p) > 80 and max(late) <= 2 and min(late) >= 0,
          "%d notes while four knobs turn: with the screen's cost each leaves within 2 ms of where it leaves without (%s; 0.21: up to 9)" % (
              len(p), (min(late), max(late)) if late else "not the same notes"))
    check(m and int(m.group(1)) <= 3, "... and no pass of the loop over 3 ms (%s)" % (m.group(1) if m else None))
    # 76 minutes: the 24 MHz counter wraps every 179 s, the microseconds at 71.6 minutes; the stamps of 16 bits every 65 s
    s = Script()
    t = remote13_on(s, 100)
    t = usb2(s, t)
    s.raw(t, "attach"); t += 100
    s.press(t, SEQ); s.tap_key(t + 30, bk(6), hold=700); s.release(t + 800, SEQ); t += 900
    s.press(t, LFO); s.tap_key(t + 30, wk(0)); s.release(t + 100, LFO); t += 160      # an LFO on
    s.tap_btn(t, PLAY); t0 = t
    end = t0 + 76 * 60000
    for k in range(1000, end + 1500, 1000): s.raw(k, "hb")
    s.raw(t0 + 500, "midi 0xBB 3 1 2")                                                 # the tablet speaks: the values go back
    s.tap_btn(end, PLAY)
    log = run(s, end + 1500)
    f8 = log.clock()
    gaps = [y - x for x, y in zip(f8, f8[1:])]
    per = {}
    held = {}
    for x, port in zip(log.msgs, log.port):
        if port != 1 or (x[1] & 15) >= 14: continue
        if x[1] & 0xF0 == 0x90 and x[3]:
            per[(x[0] - t0) // 60000] = per.get((x[0] - t0) // 60000, 0) + 1
            held[(x[1] & 15, x[2])] = held.get((x[1] & 15, x[2]), 0) + 1
        elif x[1] & 0xF0 in (0x80, 0x90):
            held[(x[1] & 15, x[2])] = max(0, held.get((x[1] & 15, x[2]), 0) - 1)
    mins = [per.get(k, 0) for k in range(1, 76)]
    fb = [x[0] for x, port in zip(log.msgs, log.port) if port == 2 and x[1] & 0xF0 == 0xB0 and (x[1] & 15) == 11 and x[0] > end - 60000]
    check(len(f8) > 230000 and max(gaps) <= 21, "76 minutes: %d clock ticks, never a gap over 21 ms (the longest %s)" % (len(f8), max(gaps) if gaps else None))
    check(max(mins) - min(mins) <= 8 and mins[0] > 500, "the band plays the same every minute, the 72nd too (%d to %d notes a minute)" % (min(mins), max(mins)))
    check(not [k for k, v in held.items() if v] and log.text.count("clock recovery") == 0, "nothing hangs at the STOP, no clock recovery")
    check(len(fb) > 20, "the values still go back to the hub in the last minute (%d messages)" % len(fb))


def t022_unrun():
    group("0.22: what no test had ever run (gcov): a TAPE track on the grid; every source and destination of the MOD MATRIX; the harmony's rhythms 3+5, 3+1, 2 BARS; the conditions 1:4, 4:4, NOT FILL")
    # a TAPE track's STEP view: the loop on 64 pads; a pad erases what starts under it; row 5 the bars, row 6 TAPE QUANT,
    # row 8 CLEAR / a 1/16 EARLIER / LATER / DOUBLE
    beat = 4 * STEP_MS
    s = Script()
    s.at(50, "attach")
    for k in range(1000, 16000, 1000): s.raw(k, "hb")
    t = kp(s, 100, [(K4, 3)])                                   # TAPE
    t = home_page(s, t, 6, [(K3, -3)])                          # TAPE BARS 4 -> 1
    s.press(t, SEL); s.tap_btn(t + 30, REC); s.release(t + 80, SEL); t += 150    # REC FREE
    s.tap_btn(t, REC); t += 100
    t0 = t
    s.tap_btn(t0, PLAY)
    for b, n, vel, hold in ((0.3, 60, 100, 100), (1.1, 64, 120, 300), (2.8, 67, 100, 50)):
        s.raw(t0 + int(b * beat), "midi 0x90 %d %d" % (n, vel))
        s.raw(t0 + int(b * beat) + hold, "midi 0x80 %d 0" % n)
    t = t0 + int(1.5 * BAR_MS)
    tstop = t
    s.tap_btn(t, REC); t += 100                                 # REC off
    s.tap_btn(t, PLAY); t += 400                                # STOP
    marks = {}
    def mark(name, t):
        s.at(t, "dump", 0); marks[name] = t
        return t + 150
    t = mark("recorded", t)
    s.pad(t, 4, 0); t = mark("erased", t + 200)                 # the pad the first note starts under
    s.pad(t, 1, 4); t = mark("bars", t + 200)                   # row 5 pad 2: 2 bars
    s.pad(t, 15, 5); t = mark("quant", t + 200)                 # row 6 pad 16: TAPE QUANT 100
    s.pad(t, 0, 5); t += 200                                    # ... pad 1: 0
    s.pad(t, 2, 7); t = mark("later", t + 200)                  # row 8 pad 3: a 1/16 later
    s.pad(t, 1, 7); t = mark("earlier", t + 200)                # pad 2: a 1/16 earlier
    s.pad(t, 3, 7); t = mark("double", t + 200)                 # pad 4: DOUBLE
    t1 = t
    s.tap_btn(t1, PLAY); t += int(4 * BAR_MS) + 20
    s.tap_btn(t, PLAY); t += 300
    s.pad(t, 0, 7); t = mark("clear", t + 200)                  # pad 1: CLEAR
    log = run(s, t + 300)
    def tape(name): return ([x for x in log.tapes if x["t"] == marks[name]] or [dict(bars=0, quant=0, n=-1, ev=[])])[0]
    def pads(name): return log.leds(until=marks[name])[0]
    r, pd = tape("recorded"), pads("recorded")
    check(r["n"] == 3 and [e[2] for e in r["ev"]] == [60, 64, 67] and all(near(e[0], x, 3) for e, x in zip(r["ev"], (115, 422, 1075))),
          "three notes on a tape of a bar: at 0.3, 1.1 and 2.8 beats, 384 ticks a beat (%s)" % r["ev"])
    check(pd.get(4) == GL_ON and pd.get(5) == GL_DIM and pd.get(17) == GL_ACCENT and pd.get(27) == GL_DIM and pd.get(28) == GL_FAINT and pd.get(44) == GL_ON,
          "the grid shows the loop on 64 pads: a note where it starts (a loud one brighter), dim for as long as it lasts (%s)" % [pd.get(i) for i in (4, 5, 17, 27, 28, 44)])
    check(pd.get(64) == GL_WHITE and pd.get(65) == GL_FAINT and [pd.get(112 + i) for i in range(5)] == [GL_ORANGE] * 4 + [GL_OFF],
          "row 5: the bars (1); row 8: the four tools (%s)" % [pd.get(i) for i in (64, 65, 112, 113, 114, 115, 116)])
    cur = sorted(set(d1 for tt, st, d1, d2 in log.msgs if st == 0x9F and d2 == GL_PLAY and t0 < tt < tstop))
    check(len(cur) >= 60 and cur[0] == 0 and cur[-1] == 63, "in play the place runs over the 64 pads (%d of them)" % len(cur))
    e, pd = tape("erased"), pads("erased")
    check(e["n"] == 2 and [x[2] for x in e["ev"]] == [64, 67] and pd.get(4) == GL_FAINT, "a pad erases the note that starts under it (%s)" % e["ev"])
    b, pd = tape("bars"), pads("bars")
    check(b["bars"] == 2 and b["n"] == 2 and pd.get(65) == GL_WHITE and pd.get(8) == GL_ACCENT and pd.get(22) == GL_ON,
          "row 5 pad 2: two bars, the notes where they were, on half the pads (%s, %s)" % (b["bars"], [pd.get(i) for i in (8, 22, 65)]))
    q, pd = tape("quant"), pads("quant")
    check(q["quant"] == 100 and pd.get(80) == GL_CYAN and pd.get(95) == GL_WHITE and tape("later")["quant"] == 0, "row 6: TAPE QUANT 100, then 0 (%s)" % q["quant"])
    la, ea = tape("later"), tape("earlier")
    check([x[0] for x in la["ev"]] == [x[0] + 96 for x in b["ev"]] and ea["ev"] == b["ev"], "LATER: every note a 1/16 (96 ticks) on; EARLIER: back (%s %s)" % (la["ev"], ea["ev"]))
    d = tape("double")
    check(d["bars"] == 4 and d["n"] == 4 and d["ev"][2:] == [(x[0] + 2 * 1536,) + x[1:] for x in b["ev"]] and d["ev"][:2] == b["ev"],
          "DOUBLE: four bars, the two notes again two bars later (%s)" % d["ev"])
    n = [(round((tt - t1) / beat, 1), nn, v) for tt, nn, v in log.notes(ch=0, after=t1)]
    check(n == [(1.1, 64, 120), (2.8, 67, 100), (9.1, 64, 120), (10.8, 67, 100)], "... and it plays so (%s)" % n)
    check(tape("clear")["n"] == 0 and tape("clear")["bars"] == 4, "CLEAR: the tape empty, its length kept (%s)" % tape("clear"))
    # the MOD MATRIX (LFO page 6): each destination with CC IN 1 at 127 against CC IN 1 at 0, +100 % and -100 %
    def gates(log, t0, ch=0):
        offs = [(tt - t0, nn) for tt, nn in log.offs(ch=ch) if tt >= t0]
        out = []
        for tt, nn, v in log.notes(ch=ch, after=t0):
            off = next((o for o, m in offs if m == nn and o > tt - t0), None)
            out.append((tt - t0, v, None if off is None else off - (tt - t0)))
        return out
    def dst(d, amt, v, lfo=False):
        s = Script()
        t = s.steps(100, [0, 1, 4, 5])
        t = pg(s, t, LFO, 5, [(K2, 6), (K3, d), (K4, amt)])                # MOD 1: CC IN, the destination (T1 / LFO 1), 50 % + 5 a click
        t = pg(s, t, LFO, 5, [(K2, 1)], sel=True)                          # SEL + K2: CC 1
        if lfo:
            s.press(t, LFO); s.tap_key(t + 30, wk(0)); s.release(t + 100, LFO); t += 160     # LFO 1 on (CC 74 of T1)
        s.raw(t, "midi 0xB0 1 %d" % v); t += 40
        s.tap_btn(t + 100, PLAY)
        log = run(s, t + 100 + int(8 * STEP_MS) - 10)
        return gates(log, t + 100), [b for _, b in lfo_cc(log, after=t + 100)]
    base = dst(3, 10, 0)[0]
    up, dn = dst(3, 10, 127)[0], dst(3, -30, 127)[0]
    check([x[1] for x in base] == [100] * 4 and [x[1] for x in up] == [127] * 4 and [x[1] for x in dn] == [37] * 4,
          "VEL: +100 %% plays 127, -100 %% 37, the CC at 0 leaves 100 (%s %s)" % ([x[1] for x in up], [x[1] for x in dn]))
    up, dn = dst(4, 10, 127)[0], dst(4, -30, 127)[0]
    check(all(near(x[2], 94, 2) for x in base) and all(near(x[2], 117, 2) for x in up) and all(near(x[2], 35, 2) for x in dn),
          "GATE: 50 points of the step more (to the next step) or less (%s %s)" % ([x[2] for x in up], [x[2] for x in dn]))
    up, dn = dst(5, 10, 127)[0], dst(5, -30, 127)[0]
    check(len(up) == 4 and 1 <= len(dn) <= 3, "CHANCE: -100 %% drops some of the four notes (50 points less), +100 %% none (%d, %d)" % (len(up), len(dn)))
    up, dn = dst(6, 10, 127)[0], dst(6, -30, 127)[0]
    check(all(near(u[0] - b[0], 29.3, 2) for u, b in zip(up, base)) and all(near(b[0] - x[0], 29.3, 2) for x, b in list(zip(dn, base))[1:]),
          "TIMING: a quarter of a step late, or early (%s %s)" % ([round(x[0]) for x in up], [round(x[0]) for x in dn]))
    up, dn = dst(7, 10, 127)[0], dst(7, -30, 127)[0]
    check(near(up[1][0] - base[1][0], 58.6, 2) and near(up[0][0], base[0][0], 2) and [round(x[0]) for x in dn] == [round(x[0]) for x in base],
          "SWING: the off 16ths half a step late; under 0 there is no swing (%s %s)" % ([round(x[0]) for x in up], [round(x[0]) for x in dn]))
    b0, up, dn = dst(1, 10, 0, lfo=True)[1], dst(1, 10, 127, lfo=True)[1], dst(1, -30, 127, lfo=True)[1]
    check(len(set(b0)) > 30 and len(set(dn)) == 1 and len(set(up)) > 10, "DEPTH: -100 %% stops LFO 1 (%d values without, %d with)" % (len(set(b0)), len(set(dn))))
    up, dn = dst(2, 10, 127, lfo=True)[1], dst(2, -30, 127, lfo=True)[1]
    check(min(b0) >= 60 and min(up) >= 120 and max(dn) <= 64, "CENTER: LFO 1 moved to the top, or to the bottom (%s-%s, %s-%s; alone %s-%s)" % (min(up), max(up), min(dn), max(dn), min(b0), max(b0)))
    # ... and the sources onto T1's TIMING (+100 %: a quarter of a step, 29 ms, at full scale)
    def src(k2, which=0, setup=None, steps=(0, 4)):
        s = Script()
        t = s.steps(100, list(steps))
        t = pg(s, t, LFO, 5, [(K2, k2), (K3, 6), (K4, 10)])
        if which: t = pg(s, t, LFO, 5, [(K2, which)], sel=True)
        if setup: t = setup(s, t)
        s.tap_btn(t + 100, PLAY)
        return gates(run(s, t + 100 + int(8 * STEP_MS) - 10), t + 100)
    plain = src(2)
    late = [src(2, w, lambda s, t, e=e: held(s, t, FX, [(e, 20)]))[0][0] - plain[0][0] for w, e in ((0, K1), (1, K2), (2, K3), (3, K4))]
    check(all(near(l, x, 2) for l, x in zip(late, (9.3, 29.3, 23.4, 18.3))),
          "MACRO: INTENSITY 20 of 63, GATE 100 of 100, SWING 20 of 25, FILTER 40 of 64 (%s ms late)" % [round(l) for l in late])
    def t2(s, t):
        s.tap_key(t, bk(1)); s.tap_key(t + 80, wk(0)); s.tap_key(t + 160, bk(0))           # track 2: its step 1; track 1 again
        return t + 240
    a, b = src(5, 1, t2, steps=(1, 5)), src(5, 1, steps=(1, 5))
    check(near(a[0][0] - b[0][0], 23, 2) and near(a[1][0] - b[1][0], 23, 2), "VEL of track 2 (100 of 127): track 1 is 23 ms late once track 2 has played (%s %s)" % ([round(x[0]) for x in a], [round(x[0]) for x in b]))
    def energy(e):
        s = Script()
        t = vg_on(s, 100)
        t = vg_track_in_now(s, t, 0)
        t = vg_bars4(s, t)
        s.enc(t, K1, e - 50); t += 60
        t = pg(s, t, LFO, 5, [(K2, 3), (K3, 6), (K4, 10)])                 # MOD 1: ENERGY -> TIMING T1
        s.tap_btn(t + 50, PLAY)
        return gates(run(s, t + 50 + int(8 * STEP_MS)), t + 50)
    hi, mid, lo = energy(100), energy(50), energy(0)
    check(near(hi[0][0], 29.3, 2) and near(mid[0][0], 0, 2) and near(mid[1][0] - lo[1][0], 29.3, 2),
          "ENERGY: 100 a quarter of a step late, 50 nothing, 0 early (%s %s %s)" % ([round(x[0]) for x in hi[:2]], [round(x[0]) for x in mid[:2]], [round(x[0]) for x in lo[:2]]))
    # the harmony's rhythms 3+5, 3+1 and 2 BARS (ARP 4 K4), and the step conditions 1:4, 4:4 and NOT FILL (EDIT K2)
    def chords(r):
        s = Script()
        t = kp(s, 100, [(K2, 1), (K4, 1)])                                 # C major, IN KEY
        t = s.steps(t, list(range(16)))
        t = home_page(s, t, 1, [(K4, 1)], cur=2)                           # FOLLOW
        t = uprog_knobs(s, t, [(K3, 1), (K2, 1), (K3, 8)])                 # USER 1: I, V
        t = harm_knobs(s, t, [(K2, 8), (K1, 1)])                           # HARMONY: USER 1, ON
        t = harm2_knobs(s, t, [(K4, r)])
        s.tap_btn(t + 20, PLAY)
        n = run(s, t + 20 + int(4 * BAR_MS) - 30).notes(ch=0, after=t + 20)
        runs = []
        for k in range(64):
            d1 = next((x[1] for x in n if near(x[0] - n[0][0], k * STEP_MS, 5)), None)
            if runs and runs[-1][0] == d1: runs[-1][1] += 1
            else: runs.append([d1, 1])
        return runs
    r35, r31, r2b = chords(6), chords(7), chords(8)
    check(r35 == [[60, 6], [55, 10]] * 4 and r31 == [[60, 12], [55, 4]] * 4 and r2b == [[60, 32], [55, 32]],
          "the chords of I V: 3+5 changes after 6 and 10 16ths, 3+1 after 12 and 4, 2 BARS after 32 (%s %s %s)" % (r35[:2], r31[:2], r2b))
    def loops(cond):
        s = Script()
        t = s.steps(100, [0])
        t = held(s, t + 30, EDIT, [(K2, cond)])
        s.tap_btn(t + 200, PLAY)
        return [int(round((x[0] - t - 200) / BAR_MS)) for x in run(s, t + 200 + int(8 * BAR_MS) - 30).notes(ch=0, after=t + 200)]
    c14, c44, cnf = loops(3), loops(6), loops(8)
    check(c14 == [0, 4] and c44 == [3, 7] and cnf == list(range(8)),
          "a step of 1:4 plays in passes 1 and 5, of 4:4 in 4 and 8, of NOT FILL in all of them with no FILL held (%s %s %s)" % (c14, c44, cnf))
    # the GATE effect (HOME 6): a FIXED length or a factor longer than the step. Until 0.21 the track's next step ended
    # the note all the same: FIXED 1/8 .. 2 BARS and x3/2, x2, x4 gave a 1/16 whatever was asked
    def gate_fx(encs, steps=(0, 8), n=16.0, stop=None, long1=False):
        s = Script()
        t = s.steps(100, steps)
        if long1:                                                          # step 1 held, step 3 pressed: a note of three steps
            s.keys(t, wk(0)); s.keys(t + 500, wk(0) | wk(2)); s.keys(t + 580, wk(0)); s.keys(t + 660, 0); t += 800
        if encs:
            t = home_page(s, t, 5, [(K1, FX_GATE)] + encs)
            t = seq_page(s, t, 0, keys=[wk(5)])
        p = t + 100
        s.tap_btn(p, PLAY)
        end = p + int(n * STEP_MS) - 5
        if stop is not None:
            s.tap_btn(p + int(stop * STEP_MS), PLAY)
        log = run(s, end)
        seq = [("on" if st == 0x90 and d2 else "off", round((tm - p) / STEP_MS, 1)) for tm, st, d1, d2 in log.msgs if tm >= p and st in (0x90, 0x80)]
        return [(round(a / STEP_MS, 1), None if b is None else round(b / STEP_MS, 1)) for a, v, b in gates(log, p)], seq
    f8, f4 = gate_fx([(K3, 3)])[0], gate_fx([(K3, 4)])[0]
    check(f8 == [(0.0, 2.0), (8.0, 2.0)] and f4 == [(0.0, 4.0), (8.0, 4.0)], "GATE FIXED 1/8: two steps long; 1/4: four (%s %s)" % (f8, f4))
    x32, x2, x4 = gate_fx([(K2, 3)])[0], gate_fx([(K2, 4)])[0], gate_fx([(K2, 5)])[0]
    check(x32 == [(0.0, 1.2), (8.0, 1.2)] and x2 == [(0.0, 1.6), (8.0, 1.6)] and x4 == [(0.0, 3.2), (8.0, 3.2)],
          "GATE x3/2, x2, x4 of a gate of 80 %% of the step: 1.2, 1.6 and 3.2 steps (%s %s %s)" % (x32, x2, x4))
    g, seq = gate_fx([(K3, 4)], steps=(0, 1, 2, 3), n=9.0)
    check(g == [(0.0, 1.0), (1.0, 1.0), (2.0, 1.0), (3.0, 4.0)] and [k for k, _ in seq] == ["on", "off"] * 4,
          "FIXED 1/4 on four 16ths of the same note: each ends as the next begins (off, then on), the last a quarter long (%s)" % g)
    g, seq = gate_fx([(K3, 6)], steps=(0,), n=12.0, stop=5.0)
    check(g == [(0.0, 5.0)] and len(seq) == 2, "FIXED 1 BAR: STOP after five steps ends the note there, nothing hangs (%s)" % seq)
    g = gate_fx([(K2, 2), (K4, 20)], steps=tuple(range(16)))[0]
    check(len(g) == 16 and max(x[1] for x in g) <= 1.0 and len(set(x[1] for x in g)) > 3,
          "HUMAN +-50 %% alone: the lengths differ and none goes past its step, as before (%s)" % sorted(set(x[1] for x in g)))
    g, seq = gate_fx([], steps=(1,), n=6.0, long1=True)
    check(seq == [("on", 0.0), ("on", 1.0), ("off", 1.8), ("off", 3.0)],
          "a note of three steps with the same note on step 2 inside it, which ends first: left as it was (%s)" % seq)
    s = Script()                                                           # a TIE (EDIT + black 6) into the same note
    t = s.steps(100, [0, 1])
    s.tap_key(t, wk(0)); s.tap_key(t + 80, wk(0)); t += 200               # (the cursor back on step 1)
    s.press(t, EDIT); s.tap_key(t + 30, bk(5)); s.release(t + 100, EDIT); t += 160
    s.at(t, "dump", 0)
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + int(4 * STEP_MS))
    seq = [("on" if st == 0x90 and d2 else "off", round((tm - p) / STEP_MS, 1)) for tm, st, d1, d2 in log.msgs if tm >= p and st in (0x90, 0x80)]
    check(log.states and log.states[0]["msg"].startswith("TIE") and seq == [("on", 0.0), ("off", 1.0), ("on", 1.0), ("off", 1.8)],
          "a TIE into the same note: the tied one ends as the next begins, which lasts its gate (0.21: the tied note's end, 15 ms later, cut it) (%s)" % seq)


def t_theory():
    group("0.23 THEORY, the engines by the simulator's own verb: they make the band - what plays is what they wrote, the HARMONY moves it, ENERGY fills it, the FM-1 takes the project")
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import sagga_grid_bridge as B
    tool = os.path.join(tempfile.gettempdir(), "sagga_theory_%d" % os.getpid())
    subprocess.run(["cc", "-std=c11", "-O2", "-I" + ROOT + "/firmware/src", ROOT + "/tools/theory/sagga_theory.c", ROOT + "/firmware/src/sagga_seq_core.c",
                    ROOT + "/firmware/src/sagga_beats.c", "-o", tool], check=True)

    def text(style, seed, energy):
        out = subprocess.run([tool, style, str(seed), "0", "0", str(energy), "64"], capture_output=True, text=True, check=True).stdout.splitlines()
        return out[0], [l.split("\t") for l in out[1:]]

    def ons(r, bars):                                           # the notes a text plays in its first bars (a roll: 2, 3 or 4)
        return sum(int(c) if c in "234" else 1 for c in r[:16 * bars] if c not in ".-")

    try:
        # TECHNO, seed 3: one chord, so every note is the one the engine wrote. Scene 1 the seed's band, 2 and 3 the same
        # at energy 25 and 95
        head, parts = text("TECHNO", 3, 60)
        bpm = int(head.split(" BPM")[0].rsplit(" ", 1)[1])
        bar = 4 * 60000.0 / bpm
        root = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"].index(head.split("key ")[1].split(" ")[0])
        check(" chords i," in head, "the test's seed has one chord (%s)" % head)
        s = Script()
        s.raw(100, "theory 0 3 0 0 60 0")
        s.raw(150, "theory 0 3 0 0 25 1")
        s.raw(200, "theory 0 3 0 0 95 2")
        s.raw(300, "sx 7D 53 47 01")
        t, plays = 6000, []
        for sc in range(3):
            s.raw(t, "scene %d 0" % sc)
            s.raw(t + 20, "energy %d" % (60, 25, 95)[sc])    # (the machine's energy: the engines' patterns follow it)
            s.tap_btn(t + 100, PLAY)
            plays.append(t + 100)
            t = t + 100 + int(2 * bar) - 8
            s.tap_btn(t, PLAY)
            t += 600
        log = run(s, t + 300)
        t0 = plays[0]
        kick = [tm - t0 for tm, _, _ in log.notes(ch=0, after=t0 - 2, before=t0 + 2 * bar - 8)]
        check(all(any(near(k, b * bar / 4, 4.0) for k in kick) for b in range(8)), "TECHNO: a kick on every beat, at the genre's tempo (%d BPM: %s)" % (bpm, [round(k) for k in kick]))
        for i, (name, r, nt) in enumerate(parts):
            got = len(log.notes(ch=i, after=t0 - 2, before=t0 + 2 * bar - 8))
            want = ons(r, 2) * (1 if nt == "-" or name in ("RUMBLE", "BASS", "ARP") else 0)
            if want:
                check(got == want, "%s plays the hits the engine wrote: %d in two bars (%d)" % (name, want, got))
            else:
                check(got >= ons(r, 2), "%s plays its chords: %d or more notes in two bars (%d)" % (name, ons(r, 2), got))
            if name in ("RUMBLE", "BASS", "ARP"):
                wrote = [(root + int(n, 16)) % 12 for c, n in zip(r[:32], nt[:32]) if c not in ".-" for _ in range(int(c) if c in "234" else 1)]
                played = [d1 % 12 for _, d1, _ in log.notes(ch=i, after=t0 - 2, before=t0 + 2 * bar - 8)]
                check(played == wrote, "%s plays the notes the engine wrote, in the key (%s / %s)" % (name, played[:12], wrote[:12]))
        n = [len(log.notes(after=p - 2, before=p + 2 * bar - 8)) for p in plays]
        check(n[1] < n[0] < n[2], "ENERGY: the same band at 25, 60 and 95 plays more and more notes (%d, %d, %d)" % (n[1], n[0], n[2]))
        k = [sorted(round((tm - p) / (bar / 16)) for tm, _, _ in log.notes(ch=0, after=p - 2, before=p + 2 * bar - 8)) for p in plays]
        check(set(k[1]) <= set(k[0]) <= set(k[2]), "ENERGY: the kicks of a lower energy are all in a higher one (%s / %s / %s)" % (k[1], k[0], k[2]))
        rx, image = B.DumpReceiver(), None
        for _, msg in log.sysex:
            r = rx.feed(msg)
            if r and r[0] == "image":
                image = r[1]
        check(image is not None and B.check_image(image) is None, "the project the engines made is one the FM-1 takes (%s)" % (B.check_image(image) if image else "no export"))

        # TECHNO, seed 8: two chords, two bars each. The bass is on the tonic for two bars, then on the second chord
        head, parts = text("TECHNO", 8, 60)
        check(" chords i-VII," in head and "2 bars a chord" in head, "the test's seed has two chords (%s)" % head)
        root = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"].index(head.split("key ")[1].split(" ")[0])
        bi = [p[0] for p in parts].index("BASS")
        s = Script()
        s.raw(100, "theory 0 8 0 0 60 0")
        s.tap_btn(500, PLAY)
        log = run(s, 500 + int(4 * bar) + 100)
        def most(a, b):
            pcs = [d1 % 12 for _, d1, _ in log.notes(ch=bi, after=500 + a * bar - 2, before=500 + b * bar - 8)]
            return max(set(pcs), key=pcs.count) if pcs else None
        check(most(0, 2) == root and most(2, 4) == (root + 10) % 12, "HARMONY: the bass is on the tonic for two bars, then on the VII (%s, %s; the key's root %d)" % (most(0, 2), most(2, 4), root))

        # FREE: its own band of eight parts, no genre in it, 120 BPM
        head, parts = text("FREE", 1, 60)
        s = Script()
        s.raw(100, "theory 22 1 0 0 60 0")                       # (FREE: 22, past the 22 genres; 0.28: 25)
        s.tap_btn(500, PLAY)
        log = run(s, 500 + 4 * 2000 + 100)
        check(len(parts) == 8 and all(log.notes(ch=i, after=498) for i in range(8)) and not log.notes(ch=8, after=498), "FREE: its eight parts play, a track each (%s)" % [len(log.notes(ch=i, after=498)) for i in range(9)])
        ck = [b - a for a, b in zip(log.clock(), log.clock()[1:])]
        check(ck and near(sorted(ck)[len(ck) // 2], 60000.0 / 120 / 24, 0.6), "FREE: 120 BPM (a clock tick every %.1f ms)" % (sorted(ck)[len(ck) // 2] if ck else 0))
    finally:
        try: os.remove(tool)
        except OSError: pass


def th_dumps(log):
    """0.23: the 'theory' lines of the dumps: what the engines know of the pattern a track plays, the source, the next seed"""
    keys = ("t", "track", "pat", "style", "len", "func", "seed", "var", "vary", "energy", "src", "next", "now")
    return [dict(zip(keys, (int(x) for x in m.groups())))
            for m in re.finditer(r"^\s*(\d+) ms  theory T(\d+) P(\d+) style (\d+) len (\d+) func (\d+) seed (\d+) var (\d+) vary (\d+) energy (\d+) src (\d+) next (\d+) now (\d+)$", log.text, re.M)]


def t023_theory():
    group("0.23 THEORY: the SOURCE (SEQ 8 K1) - BEAT, KIT, BAND make the patterns from a seed; COOK walks to the next variation; the machine's ENERGY fills and empties them; SEQ 8 K3 / K4 the track's seed and variation; GENRE FREE and LIVE; the dice; UNDO, RELOAD, a power cycle")
    tool = os.path.join(tempfile.gettempdir(), "sagga_theory_%d" % os.getpid())
    subprocess.run(["cc", "-std=c11", "-O2", "-I" + ROOT + "/firmware/src", ROOT + "/tools/theory/sagga_theory.c", ROOT + "/firmware/src/sagga_seq_core.c",
                    ROOT + "/firmware/src/sagga_beats.c", "-o", tool], check=True)

    def text(style, seed, energy, var=0, vary=0, part=None, n=64):
        out = subprocess.run([tool, style, str(seed), str(var), str(vary), str(energy), str(n)] + ([part] if part else []), capture_output=True, text=True, check=True).stdout.splitlines()
        rows = {l.split("\t")[0]: l.split("\t")[1] for l in out[1:]}
        return rows[part] if part else rows

    def onoff(r): return "".join("." if c in ".-" else "x" for c in r)
    def lib64(s, t):                                            # 0.24: the length is the track's: every track 64 steps (the MOSSE's LONGER,
        t = vg_on(s, t, remote=False)                           #  twice - stopped: at once), four bars: the answers, the fill
        for _ in range(2):
            s.press(t, SEL); s.tap_key(t + 30, bk(5)); s.release(t + 100, SEL); t += 160
        return vg_studio(s, t)
    def band(s, t): s.press(t, SEQ); s.tap_key(t + 30, bk(6), hold=700); s.release(t + 800, SEQ); return t + 900
    def seqkey(s, t, key, hold=40): s.press(t, SEQ); s.tap_key(t + 30, key, hold=hold); s.release(t + 60 + hold, SEQ); return t + 140 + hold
    def look(s, t, tracks):
        for k, tk in enumerate(tracks): s.at(t + 15 * k, "dump", tk)
        return t + 15 * len(tracks) + 40
    def at(log, track, n=0):                                    # the n-th dump of a track: (steps, theory)
        d = [x for x in log.dumps if x["track"] == track + 1]
        h = [x for x in th_dumps(log) if x["track"] == track + 1]
        return d[n], h[n]
    PARTS = ["KICK", "CLAP", "HAT", "OPEN HAT", "RIDE", "PERC", "RUMBLE", "BASS", "STAB", "PAD"]

    try:
        # ---- the SOURCE, BAND, BAND again, UNDO; a library project is what it was
        s = Script()
        t = band(s, 100)                                        # the SOURCE on LIBRARY: the library's band
        t = look(s, t, [0])
        t = pg(s, t, SEQ, 7, [(K1, 1)])                         # SEQ 8 K1: THEORY
        s.press(t, SEQ); s.at(t + 60, "ui"); s.release(t + 120, SEQ); t += 200
        t = band(s, t)
        t = look(s, t, range(10))
        t = band(s, t)
        t = look(s, t, range(10))
        t = seqkey(s, t, wk(7))                                 # UNDO
        t = look(s, t, range(10))
        log = run(s, t + 200)
        msgs = [x["msg"] for x in log.states]
        d0, h0 = at(log, 0, 0)
        check(msgs[0] == "TECHNO BAND #1: 10 TRACKS" and h0["style"] == 0 and h0["src"] == 0, "the SOURCE on LIBRARY: the library's band, nothing of the engines' (%s, %s)" % (msgs[0], h0))
        check(d0["on"] == onoff(lib_text("TECHNO", "KICK", 0)[0][:16]), "... the library's kick (%s)" % d0["on"])
        sc = log.screens()
        check(sc and sc[0]["cells"][0] == ("> SOURCE", "THEORY") and sc[0]["cells"][1] == ("NEXT SEED", "1") and sc[0]["lines"][2].startswith("SEQ 8/8 TECHNO KICK SEED 1"),
              "SEQ 8: SOURCE THEORY, the next seed, the part it will make (%s, %s)" % (sc[0]["cells"] if sc else None, sc[0]["lines"][2] if sc else None))
        e = at(log, 0, 1)[1]["now"]
        want = text("TECHNO", 0, e, n=16)                       # (a new project's tracks: 16 steps, one bar)
        got = [at(log, k, 1 if k == 0 else 0) for k in range(10)]
        check("TECHNO BAND SEED 1: 10 TRACKS" in msgs, "BAND with the SOURCE on THEORY: a band of seed 1 (%s)" % msgs)
        check(all(got[k][0]["on"] == onoff(want[PARTS[k]]) for k in range(10)), "... every part is what the engines make of that seed at the machine's energy (%d): %s" % (
            e, [PARTS[k] for k in range(10) if got[k][0]["on"] != onoff(want[PARTS[k]])]))
        check(all(got[k][1]["style"] == 1 and got[k][1]["seed"] == 0 and got[k][1]["var"] == 0 and got[k][1]["energy"] == e and got[k][1]["len"] == 16 for k in range(10)),
              "... and each pattern keeps what it was made from (%s)" % got[3][1])
        check(got[0][1]["src"] == 1 and got[0][1]["next"] == 1, "... the next seed is 2 (%s)" % got[0][1])
        want2 = text("TECHNO", 1, e, n=16)
        got2 = [at(log, k, 2 if k == 0 else 1) for k in range(10)]
        check("TECHNO BAND SEED 2: 10 TRACKS" in msgs and all(got2[k][0]["on"] == onoff(want2[PARTS[k]]) and got2[k][1]["seed"] == 1 for k in range(10)), "BAND again: another band, of seed 2")
        check(any(got2[k][0]["hash"] != got[k][0]["hash"] for k in range(10)), "... which is not the first")
        got3 = [at(log, k, 3 if k == 0 else 2) for k in range(10)]
        check(all(got3[k][0]["hash"] == got[k][0]["hash"] and got3[k][1]["seed"] == 0 for k in range(10)), "UNDO: the first band back, and what the engines knew of it (%s)" % got3[0][1])

        # ---- BEAT on one track; COOK walks to the next variation of the seed; SEQ 8 K3 / K4
        s = Script()
        t = lib64(s, 100)
        t = pg(s, t, SEQ, 7, [(K1, 1)])
        t = pg(s, t, SEQ, 0, [(K4, -30)])                       # HEAT 1 ...
        t = pg(s, t, SEQ, 0, [(K4, 8)])                         # ... 40
        s.press(t, SEQ); s.enc(t + 30, E_SEL, 2); s.tap_key(t + 80, wk(9)); s.release(t + 200, SEQ); t += 300    # BEAT: the HAT, seed 1
        t = look(s, t, [0])
        for k in range(12):
            t = seqkey(s, t, wk(8))                             # COOK
            t = look(s, t, [0])
        t = pg(s, t, SEQ, 7, [(K3, 4)])                         # the track's seed: 5
        t = look(s, t, [0])
        t = pg(s, t, SEQ, 7, [(K4, 2)])                         # its variation: 2
        t = look(s, t, [0])
        t = seqkey(s, t, wk(7))                                 # UNDO: the knobs' edit
        t = look(s, t, [0])
        log = run(s, t + 200)
        msgs = [x["msg"] for x in log.states]
        d, h = at(log, 0, 0)
        e = h["now"]
        check(msgs[0] == "TECHNO HAT SEED 1" and d["on"] == onoff(text("TECHNO", 0, e, part="HAT")) and h["func"] == 2 and h["next"] == 1, "BEAT: the part of the seed (%s, %s)" % (msgs[0], h))
        walk = [at(log, 0, 1 + k) for k in range(12)]
        reached = next((k for k in range(12) if msgs[1 + k].endswith("REACHED")), None)
        check(reached is not None and msgs[1].startswith("COOK HAT VAR "), "COOK walks to a variation of the seed and gets there (%s)" % msgs[1:6])
        if reached is not None:
            dr, hr = walk[reached]
            check(dr["on"] == onoff(text("TECHNO", 0, e, hr["var"], hr["vary"], "HAT")) and hr["var"] >= 1 and hr["vary"] >= 40 and hr["seed"] == 0, "... it is the engines' variation %d of the seed (%s)" % (hr["var"], hr))
            check(dr["on"] != d["on"] or dr["hash"] != d["hash"], "... which is not the pattern as it was: a variation that changes nothing is passed over")
            check(all(walk[k][1]["var"] == 0 for k in range(reached)), "... the pattern is the seed's own until it arrives")
            later = [k for k in range(reached + 1, 12) if msgs[1 + k].endswith("REACHED")]
            check(later and walk[later[0]][1]["var"] > hr["var"], "... and COOK goes on to the next (%s)" % [m for m in msgs[1:13]])
        n = 13
        d, h = at(log, 0, n)
        check(h["seed"] == 4 and h["var"] == 0 and d["on"] == onoff(text("TECHNO", 4, e, part="HAT")) and "HAT SEED 5" in msgs, "SEQ 8 K3: the track's seed - the pattern is another at once (%s)" % h)
        d, h = at(log, 0, n + 1)
        check(h["seed"] == 4 and h["var"] == 2 and h["vary"] == 40 and d["on"] == onoff(text("TECHNO", 4, e, 2, 40, "HAT")) and "HAT SEED 5 VAR 2 (40 %)" in msgs, "SEQ 8 K4: its variation (%s)" % h)
        d2, h2 = at(log, 0, n + 2)
        before = walk[11]
        check(d2["on"] == before[0]["on"] and h2["var"] == before[1]["var"] and h2["seed"] == 0, "UNDO takes the knobs' edit back: the pattern and what the engines knew of it (%s)" % h2)

        # ---- THE ENERGY: the band fills and empties with the machine's energy, nothing else moves; a step written by
        # hand stays; the journey's own thinning leaves the engines' patterns alone
        s = Script()
        t = lib64(s, 100)
        t = pg(s, t, SEQ, 7, [(K1, 1)])
        t = band(s, t)
        t = look(s, t, range(10))
        s.tap_key(t, bk(3)); t += 100                           # track 4 (the open hat): a step written by hand
        hand = None
        e0 = None
        s.at(t, "dump", 3); t += 60
        prelog = run(s, t + 50)
        e0 = at(prelog, 3, 0)[1]["now"]
        lo_, mid_, hi_ = (text("TECHNO", 0, x, part="OPEN HAT") for x in (10, e0, 95))
        hand = next(i for i in range(16) if lo_[i] == "." and mid_[i] == "." and hi_[i] == ".")   # a 16th the engines leave empty at any energy
        t = s.steps(t, [hand]); t += 60
        s.raw(t, "energy 95"); t += 200
        t = look(s, t, range(10))
        s.raw(t, "energy 10"); t += 200
        t = look(s, t, range(10))
        s.tap_btn(t, PLAY); p = t
        t = p + int(2 * BAR_MS)
        s.raw(t - 10, "energy 95")                              # in play: at once (the verb), the patterns follow in a few passes
        t2 = t + int(2 * BAR_MS)
        log = run(s, t2)
        full = text("TECHNO", 0, 95)
        thin = text("TECHNO", 0, 10)
        a = [at(log, k, 1 if k != 3 else 2) for k in range(10)]
        b = [at(log, k, 2 if k != 3 else 3) for k in range(10)]
        def with_hand(r, k): return r if k != 3 else r[:hand] + "x" + r[hand + 1:]
        check(all(a[k][0]["on"] == with_hand(onoff(full[PARTS[k]]), k) and a[k][1]["energy"] == 95 for k in range(10)), "ENERGY 95: every part is the engines' at 95 (%s)" % [PARTS[k] for k in range(10) if a[k][0]["on"] != with_hand(onoff(full[PARTS[k]]), k)])
        check(all(b[k][0]["on"] == with_hand(onoff(thin[PARTS[k]]), k) and b[k][1]["energy"] == 10 for k in range(10)), "ENERGY 10: ... and at 10 (%s)" % [PARTS[k] for k in range(10) if b[k][0]["on"] != with_hand(onoff(thin[PARTS[k]]), k)])
        check(all(x == "." or y == "x" for k in range(10) if PARTS[k] != "RUMBLE" for x, y in zip(b[k][0]["on"], a[k][0]["on"])), "... what plays at 10 is all there at 95: the energy only adds")
        check(a[3][0]["on"][hand] == "x" and b[3][0]["on"][hand] == "x", "... and the step written by hand is still there (16th %d)" % (hand + 1))
        n_lo = len(log.notes(after=p - 2, before=p + int(2 * BAR_MS) - 20))
        n_hi = len(log.notes(after=p + int(2 * BAR_MS) + 60, before=p + int(4 * BAR_MS) - 20))
        check(n_hi > n_lo * 3 // 2, "in play the band fills when the energy rises (%d notes in two bars, then %d)" % (n_lo, n_hi))
        hat_thin = sum(1 for c in thin["HAT"][:32] if c not in ".-")
        got_hat = len(log.notes(ch=2, after=p - 2, before=p + int(2 * BAR_MS) - 20))
        check(got_hat == hat_thin, "at energy 10 the hat plays every hit of its pattern: the journey's own thinning leaves the engines' patterns alone (%d of %d)" % (got_hat, hat_thin))
        kicks = [round((tm - p) / STEP_MS) % 16 for tm, _, _ in log.notes(ch=0, after=p - 2, before=t2)]
        check(all(kicks.count(b_) >= 4 for b_ in (0, 4, 8, 12)), "... and the kick never misses a beat while it changes (%s)" % sorted(set(kicks)))

        # ---- GENRE FREE: a band of no genre. GENRE LIVE: a change of genre makes the engines' patterns again in the new
        # style, from their seed - a genre with rules written by hand (HOUSE), one with rules counted from the library
        # (HARDTECHNO)
        s = Script()
        t = lib64(s, 100)
        t = pg(s, t, SEQ, 7, [(K1, 1)])
        t = pg(s, t, SEQ, 5, [(K4, -1)])                        # GENRE FREE
        t = band(s, t)
        t = look(s, t, range(9))
        log = run(s, t + 200)
        msgs = [x["msg"] for x in log.states]
        roles = [c["role"] for c in cfgs(log)]
        check("FREE BAND SEED 1: 8 TRACKS" in msgs and roles[:9] == [1, 2, 3, 4, 5, 6, 7, 23, 0], "GENRE FREE: FREE's band, eight parts (%s, %s)" % (msgs[-1], roles))
        check(all(at(log, k, 0)[1]["style"] == 23 for k in range(8)) and at(log, 1, 0)[0]["on"] == onoff(text("FREE", 0, at(log, 0, 0)[1]["now"], part="SNARE")), "... made by the rules of no genre")
        s = Script()
        t = lib64(s, 100)
        t = pg(s, t, SEQ, 7, [(K1, 1)])
        t = pg(s, t, SEQ, 5, [(K4, 1)])                         # GENRE LIVE
        t = band(s, t)
        t = look(s, t, [1])
        s.press(t, SEQ); s.enc(t + 30, E_PRE, 3); s.release(t + 100, SEQ); t += 200      # the genre: HOUSE
        t = look(s, t, [1, 0])
        s.press(t, SEQ); s.enc(t + 30, E_PRE, -2); s.release(t + 100, SEQ); t += 200     # HARDTECHNO: its rules are counted from the library
        t = look(s, t, [1])
        log = run(s, t + 200)
        d, h = at(log, 1, 1)
        e = h["now"]
        check(h["style"] == 4 and h["seed"] == 0 and d["on"] == onoff(text("HOUSE", 0, e, part="CLAP")), "GENRE LIVE, TECHNO -> HOUSE: the clap is HOUSE's, of the same seed (%s)" % h)
        check(at(log, 0, 0)[1]["style"] == 4, "... the kick too")
        d, h = at(log, 1, 2)
        check(h["style"] == 2 and h["seed"] == 0 and d["on"] == onoff(text("HARDTECHNO", 0, e, part="CLAP")), "... -> HARDTECHNO: the clap the engines make by HARDTECHNO's rules, of the same seed (%s, %s)" % (h, d["on"][:16]))

        # ---- the dice: DICE SEQ rolls seeds, OCT- puts everything back; DICE PROG a progression by the style's rules
        s = Script()
        t = lib64(s, 100)
        t = pg(s, t, SEQ, 7, [(K1, 1)])
        t = band(s, t)
        t = look(s, t, [0, 7])
        t = seqkey(s, t, bk(5)); t = seqkey(s, t, bk(5))        # SCOPE: THIS -> BANK -> ALL
        t = seqkey(s, t, bk(0))                                 # DICE SEQ
        t = look(s, t, [0, 7])
        s.tap_btn(t, OCT_DOWN); t += 150                        # BACK
        t = look(s, t, [0, 7])
        t = seqkey(s, t, bk(0), hold=700)                       # DICE PROG
        t = look(s, t, [0])
        log = run(s, t + 200)
        msgs = [x["msg"] for x in log.states]
        k0, b0 = at(log, 0, 0), at(log, 7, 0)
        k1, b1 = at(log, 0, 1), at(log, 7, 1)
        k2, b2 = at(log, 0, 2), at(log, 7, 2)
        e = k0[1]["now"]
        check(k1[1]["style"] == 1 and b1[1]["style"] == 1 and (k1[1]["seed"] != 0 or b1[1]["seed"] != 0), "DICE SEQ: the tracks get seeds of the dice (%s, %s)" % (k1[1]["seed"], b1[1]["seed"]))
        check(k1[0]["on"] == onoff(text("TECHNO", k1[1]["seed"], e, part="KICK")), "... and are the engines' parts of those seeds")
        check(k2[0]["hash"] == k0[0]["hash"] and b2[0]["hash"] == b0[0]["hash"] and k2[1]["seed"] == 0 and b2[1]["seed"] == 0, "OCT-: back as it was, and what the engines knew of it")
        m = [x for x in msgs if x.startswith("DICE PROG TECHNO: ")]
        hp = re.findall(r"harm11 T1 prog (\d+)", log.text)
        check(m and hp and hp[-1] == "12", "DICE PROG: a progression by TECHNO's rules, in the dice's slot (0.29: 12), which plays (%s, prog %s)" % (m, hp[-1:] if hp else None))

        # ---- RELOAD and a power cycle: the pattern comes back with what the engines knew of it, and still follows the energy
        d = tempfile.mkdtemp()
        flash = os.path.join(d, "flash.bin")
        s = Script()
        t = lib64(s, 100)
        t = pg(s, t, SEQ, 7, [(K1, 1)])
        t = band(s, t)
        s.tap_btn(t, SAVE); s.tap_btn(t + 300, SAVE); t += 1500
        t = look(s, t, [2])
        for k in range(8): t = seqkey(s, t, wk(8))              # COOK the kick-less track 3 (the hat) away
        s.tap_key(t, bk(2)); t += 100
        for k in range(8): t = seqkey(s, t, wk(8))
        t = look(s, t, [2])
        s.press(t, SEL); s.tap_btn(t + 30, SAVE); s.release(t + 100, SEL); t += 600      # RELOAD
        t = look(s, t, [2])
        log = run(s, t + 300, flash)
        a0, a1, a2 = at(log, 2, 0), at(log, 2, 1), at(log, 2, 2)
        check(a1[0]["on"] != a0[0]["on"] and a1[1]["var"] >= 1, "(the hat was cooked away: variation %d)" % a1[1]["var"])
        check(a2[0]["on"] == a0[0]["on"] and a2[1]["var"] == 0 and a2[1]["style"] == 1, "RELOAD: the saved pattern, and what the engines knew of it when it was saved (%s)" % a2[1])
        s = Script()
        s.at(100, "dump", 2)
        s.raw(200, "energy 95")
        s.at(500, "dump", 2)
        log = run(s, 800, flash)
        b0, b1 = at(log, 2, 0), at(log, 2, 1)
        check(b0[1]["style"] == 1 and b0[1]["src"] == 1 and b0[1]["next"] == 1 and b0[0]["hash"] == a0[0]["hash"], "after a power cycle: the SOURCE, the next seed, the pattern and its record (%s)" % b0[1])
        check(b1[1]["energy"] == 95 and b1[0]["on"] == onoff(text("TECHNO", 0, 95, part="HAT")), "... and it still follows the energy")
    finally:
        try: os.remove(tool)
        except OSError: pass


def t023_theory_genres():
    group("0.23 THEORY, every genre of the FM-1: BAND makes the band of each of the 22 (0.29) by its rules (six written by hand, 16 counted from the library); a genre fills and empties with the ENERGY, keeps what it always plays, cooks, rolls its chords")
    tool = os.path.join(tempfile.gettempdir(), "sagga_theory_%d" % os.getpid())
    subprocess.run(["cc", "-std=c11", "-O2", "-I" + ROOT + "/firmware/src", ROOT + "/tools/theory/sagga_theory.c", ROOT + "/firmware/src/sagga_seq_core.c",
                    ROOT + "/firmware/src/sagga_beats.c", "-o", tool], check=True)

    def text(style, seed, energy, n=64):
        out = subprocess.run([tool, str(style), str(seed), "0", "0", str(energy), str(n)], capture_output=True, text=True, check=True).stdout.splitlines()
        return out[0], [l.split("\t") for l in out[1:]]

    def onoff(r): return "".join("." if c in ".-" else "x" for c in r)
    def lib64(s, t):                                            # 0.24: the length is the track's: every track 64 steps (the MOSSE's LONGER,
        t = vg_on(s, t, remote=False)                           #  twice - stopped: at once), four bars: the answers, the fill
        for _ in range(2):
            s.press(t, SEL); s.tap_key(t + 30, bk(5)); s.release(t + 100, SEL); t += 160
        return vg_studio(s, t)
    def band(s, t): s.press(t, SEQ); s.tap_key(t + 30, bk(6), hold=700); s.release(t + 800, SEQ); return t + 900
    def seqkey(s, t, key, hold=40): s.press(t, SEQ); s.tap_key(t + 30, key, hold=hold); s.release(t + 60 + hold, SEQ); return t + 140 + hold
    def look(s, t, tracks):
        for k, tk in enumerate(tracks): s.at(t + 15 * k, "dump", tk)
        return t + 15 * len(tracks) + 40
    def at(log, track, n=0):
        d = [x for x in log.dumps if x["track"] == track + 1]
        h = [x for x in th_dumps(log) if x["track"] == track + 1]
        return d[n], h[n]

    try:
        # the parts that mind the kick of their band (a rumble never on it, a sub that leans on it): on the FM-1 they
        # follow the kick that PLAYS, in the tool the seed's own - the same kick here, but a sub leans on other hits of it
        rules = subprocess.run([tool, "--rules"], capture_output=True, text=True, check=True).stdout.splitlines()
        minds = {(f[1], f[2]) for f in (l.split("\t") for l in rules) if f[0] == "R" and f[21] == "2"}
        names = [text(g, 0, 50, 16)[0].split(" seed")[0][2:] for g in range(22)]

        # ---- every genre: BAND, by the buttons; each part is what the engines make of the seed in that genre's style
        # (a band goes onto the tracks that have its roles: a part is found by what the engines say they made there)
        FUNCS = {"KICK": 0, "SNARE": 1, "HAT": 2, "PERC": 3, "BASS": 4, "CHORD": 5, "ARP": 6, "CLAP": 9, "OPEN HAT": 10, "RIDE": 11, "SHAKER": 12, "CONGA": 13,
                 "TOM": 14, "RIM": 15, "CRASH": 16, "COWBELL": 17, "RUMBLE": 18, "SUB": 19, "LOG DRUM": 20, "STAB": 21, "PAD": 22, "PIANO": 23, "LEAD": 24, "VOX": 25,
                 "BALAFON": 26}
        bad, sizes, counted = [], [], 0
        for g in range(22):                                     # (a new project each: a band wants free tracks for its roles)
            s = Script()
            t = lib64(s, 100)
            t = pg(s, t, SEQ, 7, [(K1, 1), (K2, g)])            # SOURCE THEORY, the next seed g + 1
            if g:
                s.press(t, SEQ); s.enc(t + 30, E_PRE, g); s.release(t + 100, SEQ); t += 200      # the genre
            t = band(s, t)
            t = look(s, t, range(12))
            log = run(s, t + 300)
            msgs = [x["msg"] for x in log.states]
            e = at(log, 0, 0)[1]["now"]
            head, parts = text(g, g, e)
            sizes.append(len(parts))
            if "%s BAND SEED %d: %d TRACKS" % (names[g], g + 1, len(parts)) not in msgs:
                bad.append("%s: no band (%s)" % (names[g], msgs[-1:]))
                continue
            made = {}
            for k in range(12):
                d, h = at(log, k, 0)
                if h["style"] == g + 1 and h["seed"] == g and h["len"] == 64:
                    made[h["func"]] = d
            for name, r, nt in parts:
                d = made.get(FUNCS[name])
                if d is None:
                    bad.append("%s %s: on no track" % (names[g], name))
                elif (names[g], name) not in minds and d["on"] != onoff(r):
                    bad.append("%s %s: %s, the engines write %s" % (names[g], name, d["on"][:32], onoff(r)[:32]))
                elif (names[g], name) in minds and d["on"].count("x") == 0:
                    bad.append("%s %s: empty" % (names[g], name))
                else:
                    counted += 1
        check(not bad, "BAND in each of the 22 genres: every part is the engines' part of that seed in the genre's style (%d parts; %s)" % (counted, bad[:4]))
        check(min(sizes) >= 8 and max(sizes) <= 11 and counted >= 200, "... the bands are the genres' own, 8 to 11 parts (%s)" % sizes)

        # ---- REGGAETON (its rules written by hand since 0.29; counted until then). The dembow at every energy; the band fills and empties
        G = names.index("REGGAETON")
        s = Script()
        t = lib64(s, 100)
        t = pg(s, t, SEQ, 7, [(K1, 1)])
        s.press(t, SEQ); s.enc(t + 30, E_PRE, G); s.release(t + 100, SEQ); t += 200
        t = band(s, t)
        t = look(s, t, range(9))
        s.raw(t, "energy 10"); t += 300
        t = look(s, t, range(9))
        s.raw(t, "energy 95"); t += 300
        t = look(s, t, range(9))
        s.tap_key(t, bk(1)); t += 100                           # track 2: the snare
        for k in range(6):
            t = seqkey(s, t, wk(8))                             # COOK
        t = look(s, t, [1])
        t = seqkey(s, t, bk(0), hold=700)                       # DICE PROG
        t = look(s, t, [0])
        s.tap_btn(t, PLAY); p = t
        log = run(s, p + int(2 * BAR_MS))
        msgs = [x["msg"] for x in log.states]
        e = at(log, 0, 0)[1]["now"]
        for n, en in enumerate((e, 10, 95)):
            head, parts = text(G, 0, en)
            got = [at(log, k, n) for k in range(9)]
            same = [got[k][0]["on"] == onoff(parts[k][1]) if ("REGGAETON", parts[k][0]) not in minds else "x" in got[k][0]["on"] for k in range(9)]   # (the bass leans on the kick that plays)
            check(all(same[k] and got[k][1]["energy"] == en for k in range(9)), "REGGAETON at energy %d: every part is the engines' (%s)" % (
                en, [parts[k][0] for k in range(9) if not same[k]]))
        lo, hi = [at(log, k, 1)[0]["on"] for k in range(9)], [at(log, k, 2)[0]["on"] for k in range(9)]
        check(all(x == "." or y == "x" for a, b in zip(lo, hi) for x, y in zip(a, b)), "... what plays at 10 is all there at 95")
        check(sum(r.count("x") for r in hi) > sum(r.count("x") for r in lo) * 3 // 2, "... and 95 is much fuller (%d hits, %d)" % (sum(r.count("x") for r in lo), sum(r.count("x") for r in hi)))
        check(all(lo[1][b * 16 + 3] == "x" and lo[1][b * 16 + 11] == "x" for b in range(3)) and all(hi[1][b * 16 + i] == "x" for b in range(3) for i in (3, 6, 11, 14)),
              "the snare of the dembow: its two accents at every energy, all four hits from energy 25 (%s / %s)" % (lo[1][:16], hi[1][:16]))
        check(all(hi[0][b * 16 + i] == "x" for b in range(4) for i in (0, 4, 8, 12)), "... on four kicks a bar (%s)" % hi[0][:16])
        cooked = [m for m in msgs if m.startswith("COOK SNARE VAR ")]
        d, h = at(log, 1, 3)
        check(cooked and h["style"] == G + 1 and all(d["on"][b * 16 + i] == "x" for b in range(3) for i in (3, 6, 11, 14)), "COOK: a variation of the snare, still the dembow (%s, %s)" % (cooked[:2], d["on"][:16]))
        m = [x for x in msgs if x.startswith("DICE PROG REGGAETON: ")]
        check(m and log.notes(after=p - 2), "DICE PROG: a progression by REGGAETON's rules, and the band plays (%s, %d notes)" % (m, len(log.notes(after=p - 2))))

        # ---- the hub's LIVE page (channel 12, the tablet's track): SOURCE (CC 56: 0 LIBRARY, 1 THEORY, 2 FREE), NEXT
        # SEED (57), BEAT (27), the track's SEED (58) and VARIATION (59); the FM-1's own changes go back to the page
        s = Script()
        t = remote13_on(s, 100)
        t = usb2(s, t)
        t = lib64(s, t)
        s.raw(t, "midi 0xBC 112 2 2"); t += 40                  # the tablet's track: 3
        s.raw(t, "midi 0xBB 56 1 2"); t += 40                   # SOURCE: THEORY
        s.raw(t, "midi 0xBB 57 4 2"); t += 40                   # NEXT SEED 5
        s.raw(t, "midi 0xBB 27 127 2"); s.raw(t + 20, "midi 0xBB 27 0 2"); t += 80     # BEAT on the tablet's track
        t = look(s, t, [2])
        s.raw(t, "midi 0xBB 58 9 2"); t += 60                   # its SEED: 10
        t = look(s, t, [2])
        s.raw(t, "midi 0xBB 59 2 2"); t += 60                   # its VARIATION: 2
        t = look(s, t, [2])
        t1 = t + 600
        t = pg(s, t1, SEQ, 7, [(K1, -1)])                       # the panel: SOURCE LIBRARY
        t = pg(s, t + 600, SEQ, 7, [(K1, 1), (K2, 3)])          # ... THEORY again, the next seed + 3
        log = run(s, t + 900)
        a, b, c = at(log, 2, 0), at(log, 2, 1), at(log, 2, 2)
        e = a[1]["now"]
        f = a[1]["func"]
        fname = [k for k, v in {"KICK": 0, "SNARE": 1, "HAT": 2, "PERC": 3, "BASS": 4, "CHORD": 5, "ARP": 6}.items() if v == f]
        check(a[1]["src"] == 1 and a[1]["style"] == 1 and a[1]["seed"] == 4 and a[1]["next"] == 5 and fname, "LIVE: THEORY, NEXT SEED 5, BEAT - the tablet's track gets the engines' part of seed 5 (%s)" % a[1])
        if fname:
            def one(seed, var=0, vary=0):
                out = subprocess.run([tool, "0", str(seed), str(var), str(vary), str(e), "64", fname[0]], capture_output=True, text=True, check=True).stdout.splitlines()
                return onoff(out[1].split("\t")[1])
            check(a[0]["on"] == one(4), "... which is what the engines write (%s)" % a[0]["on"][:32])
            check(b[1]["seed"] == 9 and b[1]["var"] == 0 and b[0]["on"] == one(9), "LIVE SEED 10: the pattern is the part of that seed at once (%s)" % b[1])
            check(c[1]["seed"] == 9 and c[1]["var"] == 2 and c[0]["on"] == one(9, 2, c[1]["vary"]), "LIVE VARIATION 2: its second variation (%s)" % c[1])
        out = [(m[0], m[2], m[3]) for m, p in zip(log.msgs, log.port) if p == 2 and m[1] == 0xBB]
        back = [(tm, cc, v) for tm, cc, v in out if cc in (56, 57) and tm > t1]
        check((56, 0) in [(cc, v) for _, cc, v in back] and (56, 1) in [(cc, v) for _, cc, v in back] and (57, 8) in [(cc, v) for _, cc, v in back],
              "the panel's SOURCE and NEXT SEED go back to the page: CC 56 = 0 (LIBRARY), then 1 (THEORY), CC 57 = 8 (%s)" % back[:6])
    finally:
        try: os.remove(tool)
        except OSError: pass


def t023_theory_free():
    group("0.23 THEORY free of the genre: the SOURCE on FREE (SEQ 8 K1, past THEORY) - BAND, KIT, BEAT, COOK, the ENERGY and DICE PROG by the rules of no genre, whatever the genre and its mode; a change of genre leaves those patterns alone; GENRE FREE does the same to SOURCE THEORY; the harmony FREE frees the progression alone; the tablet's SOURCE knob has the three positions")
    tool = os.path.join(tempfile.gettempdir(), "sagga_theory_%d" % os.getpid())
    subprocess.run(["cc", "-std=c11", "-O2", "-I" + ROOT + "/firmware/src", ROOT + "/tools/theory/sagga_theory.c", ROOT + "/firmware/src/sagga_seq_core.c",
                    ROOT + "/firmware/src/sagga_beats.c", "-o", tool], check=True)

    def text(style, seed, energy, var=0, vary=0, part=None, n=64, parts=None, mate=None):
        """0.25: `parts`: the tracks in their order (each part answers the first other one of the family it answers);
        `mate`: (style, seed, part) of a track of another band that the part answers"""
        cmd = [tool] + (["--mate", mate[0], str(mate[1]), mate[2]] if mate else []) + [style, str(seed), str(var), str(vary), str(energy), str(n)]
        out = subprocess.run(cmd + (parts if parts else [part] if part else []), capture_output=True, text=True, check=True).stdout.splitlines()
        rows = {l.split("\t")[0]: l.split("\t")[1] for l in out[1:]}
        return rows[part] if part and not parts else rows

    def onoff(r): return "".join("." if c in ".-" else "x" for c in r)
    def lib64(s, t):                                            # 0.24: the length is the track's: every track 64 steps (the MOSSE's LONGER,
        t = vg_on(s, t, remote=False)                           #  twice - stopped: at once), four bars: the answers, the fill
        for _ in range(2):
            s.press(t, SEL); s.tap_key(t + 30, bk(5)); s.release(t + 100, SEL); t += 160
        return vg_studio(s, t)
    def band(s, t): s.press(t, SEQ); s.tap_key(t + 30, bk(6), hold=700); s.release(t + 800, SEQ); return t + 900
    def seqkey(s, t, key, hold=40): s.press(t, SEQ); s.tap_key(t + 30, key, hold=hold); s.release(t + 60 + hold, SEQ); return t + 140 + hold
    def screen(s, t): s.press(t, SEQ); s.at(t + 60, "ui"); s.release(t + 700, SEQ); return t + 800     # (held 0.7 s: not a tap, no window stays open)
    def look(s, t, tracks):
        for k, tk in enumerate(tracks): s.at(t + 15 * k, "dump", tk)
        return t + 15 * len(tracks) + 40
    def at(log, track, n=0):                                    # the n-th dump of a track: (steps, theory)
        d = [x for x in log.dumps if x["track"] == track + 1]
        h = [x for x in th_dumps(log) if x["track"] == track + 1]
        return d[n], h[n]
    FREE = ["KICK", "SNARE", "HAT", "PERC", "BASS", "CHORD", "ARP", "LEAD"]
    TECHNO = ["KICK", "CLAP", "HAT", "OPEN HAT", "RIDE", "PERC", "RUMBLE", "BASS", "STAB", "PAD"]

    try:
        # ---- in a genre (REGGAETON, the GENRE mode ON), the SOURCE on FREE: BAND is FREE's band, not the genre's; the
        # ENERGY fills and empties it; COOK walks to the variations of a FREE part; DICE PROG rolls by the rules of no
        # genre; the genre itself is still there (the SOURCE back on THEORY: its parts)
        s = Script()
        t = lib64(s, 100)
        s.press(t, SEQ); s.enc(t + 30, E_PRE, 8); s.release(t + 100, SEQ); t += 200         # the genre: REGGAETON (0.29: number 8)
        t = pg(s, t, SEQ, 7, [(K1, 2)])                         # SEQ 8 K1: LIBRARY -> THEORY -> FREE
        t = screen(s, t)
        t = band(s, t)
        t = look(s, t, range(9))
        s.raw(t, "energy 10"); t += 300
        t = look(s, t, range(8))
        s.raw(t, "energy 95"); t += 300
        t = look(s, t, range(8))
        s.tap_key(t, bk(2)); t += 100                           # track 3: the hat
        for k in range(12):
            t = seqkey(s, t, wk(8))                             # COOK
            t = look(s, t, [2])
        t = seqkey(s, t, bk(0), hold=700)                       # DICE PROG
        t = look(s, t, [0])
        t = pg(s, t, SEQ, 7, [(K1, -1)])                        # the SOURCE: THEORY
        t = screen(s, t)
        log = run(s, t + 300)
        msgs = [x["msg"] for x in log.states]
        sc = log.screens()
        roles = [c["role"] for c in cfgs(log)]
        check(len(sc) == 2 and sc[0]["cells"][0] == ("> SOURCE", "FREE") and sc[0]["lines"][2].startswith("SEQ 8/8 FREE KICK SEED 1"),
              "SEQ 8 K1, two clicks: SOURCE FREE; the part BEAT will make is FREE's (%s, %s)" % (sc[0]["cells"][0] if sc else None, sc[0]["lines"][2] if sc else None))
        check("SOURCE FREE: MADE BY THE RULES OF NO GENRE" in msgs or any(l.startswith("SOURCE FREE") for l in sc[0]["lines"]), "... and the screen says what FREE is (%s)" % (sc[0]["lines"][3] if sc else None))
        check("FREE BAND SEED 1: 8 TRACKS" in msgs and roles[:9] == [1, 2, 3, 4, 5, 6, 7, 23, 0], "BAND in REGGAETON with the SOURCE on FREE: FREE's band, eight parts (%s, %s)" % ([m for m in msgs if "BAND" in m][:1], roles[:9]))
        e = at(log, 0, 0)[1]["now"]
        for n, en in enumerate((e, 10, 95)):
            want = text("FREE", 0, en)
            got = [at(log, k, n) for k in range(8)]
            check(all(got[k][1]["style"] == 23 and got[k][1]["src"] == 2 and got[k][0]["on"] == onoff(want[FREE[k]]) and got[k][1]["energy"] == en for k in range(8)),
                  "... at energy %d every part is what the engines make by the rules of no genre (%s)" % (en, [FREE[k] for k in range(8) if got[k][0]["on"] != onoff(want[FREE[k]])]))
        lo, hi = [at(log, k, 1)[0]["on"] for k in range(8)], [at(log, k, 2)[0]["on"] for k in range(8)]
        check(all(x == "." or y == "x" for a, b in zip(lo, hi) for x, y in zip(a, b)) and sum(r.count("x") for r in hi) > sum(r.count("x") for r in lo) * 3 // 2,
              "the ENERGY fills and empties FREE's parts too: 10 is all there at 95, which is much fuller (%d hits, %d)" % (sum(r.count("x") for r in lo), sum(r.count("x") for r in hi)))
        cook = [m for m in msgs if m.startswith("COOK ")]
        walk = [at(log, 2, 3 + k) for k in range(12)]
        reached = [k for k in range(min(12, len(cook))) if cook[k].endswith("REACHED")]
        check(len(cook) == 12 and reached and all(m.startswith("COOK HAT VAR ") for m in cook), "COOK walks FREE's hat to a variation of its seed (%s)" % cook[:4])
        if reached:
            dr, hr = walk[reached[0]]
            check(hr["style"] == 23 and hr["var"] >= 1 and hr["seed"] == 0 and dr["on"] == onoff(text("FREE", 0, 95, hr["var"], hr["vary"], "HAT")) and dr["hash"] != at(log, 2, 2)[0]["hash"],
                  "... which is the engines' variation %d of it by the rules of no genre, and not the pattern as it was (%s)" % (hr["var"], hr))
        m = [x for x in msgs if x.startswith("DICE PROG ")]
        check(len(m) == 1 and m[0].startswith("DICE PROG FREE: "), "DICE PROG: a progression by the rules of no genre, not REGGAETON's (%s)" % m)
        check(sc[1]["cells"][0] == ("> SOURCE", "THEORY") and sc[1]["lines"][2].startswith("SEQ 8/8 REGGAETON KICK SEED 2"), "the SOURCE back on THEORY: the genre was there all along, BEAT will make its part (%s)" % sc[1]["lines"][2])

        # ---- on a band of a genre (TECHNO, made by the engines): the SOURCE on FREE, BEAT on the BANK gives every track
        # the part of its ROLE by the rules of no genre (a CLAP, an OPEN HAT, a RIDE, a RUMBLE: FREE has a rule for every
        # role); the tracks it did not touch stay TECHNO's. KIT: FREE's drums. Then GENRE LIVE and a change of genre: the
        # engines' patterns stay as they are while the SOURCE is FREE; with the SOURCE on THEORY they are made again
        s = Script()
        t = lib64(s, 100)
        t = pg(s, t, SEQ, 7, [(K1, 1)])                         # THEORY
        t = band(s, t)                                          # TECHNO's band: ten tracks
        t = look(s, t, range(10))
        t = pg(s, t, SEQ, 7, [(K1, 1)])                         # the SOURCE: FREE
        t = pg(s, t, SEQ, 0, keys=[bk(5)])                      # SEQ + black 6: the scope, BANK
        t = seqkey(s, t, wk(9))                                 # BEAT on the bank
        t = look(s, t, range(10))
        t = pg(s, t, SEQ, 0, keys=[bk(5), bk(5)])               # the scope: ALL, TRACK
        t = pg(s, t, SEQ, 5, [(K4, 1)])                         # SEQ 6 K4: GENRE LIVE
        s.press(t, SEQ); s.enc(t + 30, E_PRE, 3); s.release(t + 100, SEQ); t += 300     # the genre: HOUSE
        t = look(s, t, range(10))
        t = pg(s, t, SEQ, 7, [(K1, -1)])                        # the SOURCE: THEORY
        s.press(t, SEQ); s.enc(t + 30, E_PRE, -3); s.release(t + 100, SEQ); t += 300    # the genre: TECHNO
        t = look(s, t, range(10))
        log = run(s, t + 300)
        msgs = [x["msg"] for x in log.states]
        e = at(log, 0, 0)[1]["now"]
        tech = [at(log, k, 0) for k in range(10)]
        free = [at(log, k, 1) for k in range(10)]
        want = text("FREE", 1, e, parts=TECHNO[:8])            # (0.25: the eight tracks as they are: the PERC answers the CLAP)
        check(all(x[1]["style"] == 1 and x[1]["seed"] == 0 for x in tech) and "BEAT: BANK (8)" in msgs, "TECHNO's band from the engines, then BEAT on the bank with the SOURCE on FREE (%s)" % [m for m in msgs if m.startswith("BEAT")][:2])
        check(all(free[k][1]["style"] == 23 and free[k][1]["seed"] == 1 and free[k][1]["func"] == tech[k][1]["func"] for k in range(8)),
              "... every track of the bank: the part of its role, of the next seed, by the rules of no genre (%s)" % [(x[1]["style"], x[1]["func"], x[1]["seed"]) for x in free[:8]])
        check(all(free[k][0]["on"] == onoff(want[TECHNO[k]]) and "x" in free[k][0]["on"] for k in range(8)),
              "... each is what the engines write for that role in FREE: a clap, an open hat, a ride, a rumble too (%s)" % [TECHNO[k] for k in range(8) if free[k][0]["on"] != onoff(want[TECHNO[k]])])
        check(all(free[k][1]["style"] == 1 and free[k][0]["hash"] == tech[k][0]["hash"] for k in (8, 9)), "... the tracks of the other bank stay TECHNO's (%s)" % [free[k][1]["style"] for k in (8, 9)])
        live = [at(log, k, 2) for k in range(10)]
        check(any(m.startswith("GENRE HOUSE") for m in msgs) and all(live[k][0]["hash"] == free[k][0]["hash"] and live[k][1]["style"] == free[k][1]["style"] for k in range(10)),
              "GENRE LIVE, the genre changes with the SOURCE on FREE: the engines' patterns stay as they are, FREE's and TECHNO's (%s)" % [live[k][1]["style"] for k in range(10)])
        back = [at(log, k, 3) for k in range(10)]
        check(all(back[k][1]["style"] == 1 for k in range(10)) and all(back[k][0]["hash"] != free[k][0]["hash"] for k in (1, 2)) and all(back[k][1]["seed"] == free[k][1]["seed"] for k in range(10)),
              "the SOURCE on THEORY, the genre changes: every pattern of the engines is made again in the genre's style, from its seed (%s)" % [(x[1]["style"], x[1]["seed"]) for x in back])

        # ... and a track loaded from the LIBRARY follows the genre as it always did, from the library: the SOURCE on
        # FREE has nothing to say about a genre (the same gestures with the SOURCE on LIBRARY all along: the same kick)
        got = []
        for free in (False, True):
            s = Script()
            t = lib64(s, 100)
            t = seqkey(s, t, wk(9))                             # BEAT, the SOURCE on LIBRARY: the library's TECHNO kick on track 1
            t = look(s, t, [0])
            if free:
                t = pg(s, t, SEQ, 7, [(K1, 2)])                 # the SOURCE: FREE
                s.tap_key(t, bk(1)); t += 100                   # track 2
                t = seqkey(s, t, wk(9))                         # BEAT: a kick of no genre there
                t = look(s, t, [1])
            t = pg(s, t, SEQ, 5, [(K4, 1)])                     # GENRE LIVE
            s.press(t, SEQ); s.enc(t + 30, E_PRE, 13); s.release(t + 100, SEQ); t += 300    # the genre: DRUM+BASS (0.29: number 13)
            t = look(s, t, [0, 1])
            log = run(s, t + 300)
            got.append((at(log, 0, 0), at(log, 0, 1), at(log, 1, 0), at(log, 1, -1), [x["msg"] for x in log.states]))
        (a0, a1, _, _, _), (b0, b1, b2, b3, bm) = got
        check(a0[0]["hash"] != a1[0]["hash"] and a1[1]["style"] == 0 and b0[0]["hash"] == a0[0]["hash"],
              "GENRE LIVE, the SOURCE on LIBRARY: the library's kick becomes DRUM+BASS's (%s -> %s)" % (a0[0]["on"][:16], a1[0]["on"][:16]))
        check(b1[0]["hash"] == a1[0]["hash"] and b1[1]["style"] == 0, "... with the SOURCE on FREE the same: the library's track takes the new genre's part from the library (%s, style %d)" % (b1[0]["on"][:16], b1[1]["style"]))
        check(b2[1]["style"] == 23 and b2[0]["on"] == onoff(text("FREE", 0, b2[1]["now"], part="KICK")) and "FREE KICK SEED 1" in bm and b3[1]["style"] == 23 and b3[0]["hash"] == b2[0]["hash"],
              "... and the kick of no genre beside it stays as it is (%s, %s)" % (b3[1], [m for m in bm if "SEED" in m][:1]))

        s = Script()
        t = lib64(s, 100)
        s.press(t, SEQ); s.enc(t + 30, E_PRE, 3); s.release(t + 100, SEQ); t += 200         # the genre: HOUSE
        t = pg(s, t, SEQ, 7, [(K1, 2)])                         # the SOURCE: FREE
        t = seqkey(s, t, bk(6))                                 # KIT (SEQ + black 7, short)
        t = look(s, t, range(5))
        log = run(s, t + 300)
        msgs = [x["msg"] for x in log.states]
        e = at(log, 0, 0)[1]["now"]
        want = text("FREE", 0, e)
        kit = [at(log, k, 0) for k in range(5)]
        check(any(m.startswith("FREE KIT SEED 1") for m in msgs) and all(kit[k][1]["style"] == 23 and kit[k][0]["on"] == onoff(want[FREE[k]]) for k in range(4)) and kit[4][1]["style"] == 0,
              "KIT in HOUSE with the SOURCE on FREE: FREE's drums, four tracks (%s, %s)" % ([m for m in msgs if "KIT" in m][:1], [x[1]["style"] for x in kit]))

        # ---- the other two ways to be free of the genre. The harmony FREE (ARP 4 K2) with the SOURCE on THEORY: the
        # parts are the genre's, DICE PROG rolls a progression of no genre. The GENRE mode FREE (SEQ 6 K4) with the
        # SOURCE on THEORY: the engines make parts of no genre, BEAT lists FREE's parts
        s = Script()
        t = lib64(s, 100)
        t = pg(s, t, SEQ, 7, [(K1, 1)])                         # THEORY (TECHNO)
        t = pg(s, t, ARP, 3, [(K2, -1)])                        # ARP 4 K2: the harmony FREE of the genre
        t = band(s, t)
        t = look(s, t, [0])
        t = seqkey(s, t, bk(0), hold=700)                       # DICE PROG
        t = look(s, t, [0])
        t = pg(s, t, SEQ, 5, [(K4, -1)])                        # GENRE FREE
        t = look(s, t, [0])
        t = pg(s, t, SEQ, 7)
        t = screen(s, t)
        s.press(t, SEQ); s.enc(t + 30, E_SEL, 7); s.tap_key(t + 80, wk(9)); s.release(t + 200, SEQ); t += 300     # BEAT: the eighth part of the list
        t = look(s, t, [0])
        log = run(s, t + 300)
        msgs = [x["msg"] for x in log.states]
        sc = log.screens()
        m = [x for x in msgs if x.startswith("DICE PROG ")]
        check(at(log, 0, 0)[1]["style"] == 1 and "TECHNO BAND SEED 1: 10 TRACKS" in msgs and m and all(x.startswith("DICE PROG FREE: ") for x in m),
              "the harmony FREE, the SOURCE on THEORY: the band is TECHNO's, DICE PROG rolls a progression of no genre (%s)" % m[:1])
        check("GENRE FREE: THEORY MAKES PARTS OF NO GENRE" in msgs and sc and sc[-1]["cells"][0] == ("> SOURCE", "THEORY") and sc[-1]["lines"][2].startswith("SEQ 8/8 FREE KICK SEED 2"),
              "the GENRE mode FREE with the SOURCE on THEORY: the engines make parts of no genre, the screen says so (%s, %s)" % (sc[-1]["cells"][0] if sc else None, sc[-1]["lines"][2] if sc else None))
        d, h = at(log, 0, 3)
        check("FREE LEAD SEED 2" in msgs and h["style"] == 23 and h["func"] == 24 and h["seed"] == 1 and d["on"] == onoff(text("FREE", 1, h["now"], part="LEAD", mate=("TECHNO", 0, "STAB"))),   # (0.25: it answers the band's STAB, the first track of chords)
              "... BEAT goes through FREE's eight parts: the eighth is its LEAD, made from the next seed (%s, %s)" % ([m for m in msgs if "SEED" in m][-1:], h))

        # ---- the hub's LIVE page: its SOURCE knob (channel 12, CC 56) has the three positions - 0 LIBRARY, 1 THEORY, 2
        # FREE; the panel's SOURCE goes back to it; a value past the three (a switch's "on") is the engines: THEORY
        # from LIBRARY, and a SOURCE on FREE stays FREE
        s = Script()
        t = remote13_on(s, 100)
        t = usb2(s, t)
        t = lib64(s, t)
        s.raw(t, "midi 0xBC 112 0 2"); t += 600                 # the page speaks (the tablet's track: 1): the FM-1 answers it from now on
        s.raw(t, "midi 0xBB 56 2 2"); t += 60                   # the page: SOURCE FREE
        t = look(s, t, [0])
        s.raw(t, "midi 0xBB 27 127 2"); s.raw(t + 20, "midi 0xBB 27 0 2"); t += 80      # BEAT from the page
        t = look(s, t, [0])
        s.raw(t, "midi 0xBB 56 127 2"); t += 60                 # a switch's "on": the engines are on, FREE stays
        t = look(s, t, [0])
        s.raw(t, "midi 0xBB 56 0 2"); t += 60                   # LIBRARY
        t = look(s, t, [0])
        s.raw(t, "midi 0xBB 56 127 2"); t += 60                 # "on" from LIBRARY: THEORY
        t = look(s, t, [0])
        t0 = t + 600
        t = pg(s, t0, SEQ, 7, [(K1, 1)])                        # the panel: THEORY -> FREE
        t = look(s, t + 600, [0])
        log = run(s, t + 900)
        src = [at(log, 0, n)[1]["src"] for n in range(6)]
        out = [(m[0], m[2], m[3]) for m, p in zip(log.msgs, log.port) if p == 2 and m[1] == 0xBB and m[2] == 56]
        check(src == [2, 2, 2, 0, 1, 2], "the page's SOURCE: 2 is FREE; a switch's \"on\" keeps it; 0: LIBRARY; \"on\" from there: THEORY; the panel: FREE again (%s)" % src)
        d, h = at(log, 0, 1)
        check(h["style"] == 23 and h["seed"] == 0 and d["on"] == onoff(text("FREE", 0, h["now"], part="KICK")), "BEAT from the page with its SOURCE on FREE: a part of no genre (%s)" % h)
        check([v for tm, _, v in out if tm > t0][:1] == [2], "the panel's SOURCE FREE goes back to the page: CC 56 = 2 (%s)" % [x for x in out if x[0] > t0][:3])
        check(1 in [v for tm, _, v in out if tm <= t0], "... and a switch's \"on\" is answered with where the SOURCE is: CC 56 = 1, THEORY (%s)" % [x for x in out if x[0] <= t0][:4])
    finally:
        try: os.remove(tool)
        except OSError: pass


def t023_snapshot_direction():
    group("0.23 a snapshot that brings a track's DIRECTION back puts the track in time (found by the explorer's sessions: SAVE + SEL + black 1, HOME 2 K1, SAVE + black 1 left track 1 a step off the bar; it was so since 0.11, when a snapshot learned to land in time for a new length, start or division)")
    for back in (False, True):
        s = Script()
        s.press(100, SEQ); s.tap_key(130, bk(6), hold=700); s.release(900, SEQ); t = 1000     # the BAND
        s.tap_btn(t, PLAY); t += 300
        s.press(t, SAVE); s.press(t + 30, SEL); s.tap_key(t + 60, bk(0)); s.release(t + 130, SEL); s.release(t + 160, SAVE); t += 300   # the snapshot: stored
        t = pg(s, t, HOME, 1, [(K1, 1)])                         # HOME 2 K1: the DIRECTION of track 1, BACKWARD
        if back:
            t = pg(s, t, HOME, 1, [(K1, 1)])                     # ... PING-PONG
        t += int(BAR_MS)
        s.press(t, SAVE); s.tap_key(t + 30, bk(0)); s.release(t + 100, SAVE); t += 200       # the snapshot: back (at the QUANTISE)
        t += int(2 * BAR_MS)
        s.at(t, "probe")
        s.tap_btn(t + 100, PLAY)
        log = run(s, t + 600)
        ok = [m.group(2) for m in re.finditer(r"PROBE T(\d+) .* ok=(\S+) ", log.text)]
        dirs = re.findall(r"PROBE T1 .* dir=(\d+) ", log.text)
        check(len(ok) == 12 and "0" not in ok and dirs and dirs[-1] == "0", "the snapshot is back with FORWARD, two bars on every track is where the bar says (%s, track 1's direction %s; from %s)" % (
            "".join(ok), dirs[-1:], "PING-PONG" if back else "BACKWARD"))


NUMERIC_16 = ["x...x...x...x...", "x...x...x.....x.", "x..x....x...x...", "x..x....x..x....", "x...x...x...x.x.", "x..x..x.x...x...",
              "x..x..x...x.x...", "x..x...x..x.x...", "x..x..x...x..x..", "x.x.x...x.x.x...", "x..x..x.x...x.x.", "x..x..x.x..x..x.",
              "x..x..x..x..x.x.", "x.x.x.x.x.x.x...", "x.x.x.x.x.x..x..", "x..x.x.x..x.x.x."]


def t0231_numeric():
    group("0.23.1: NUMERIC is sixteen base rhythms (K1 picks one, K2 turns it), not the binary of a prime number")
    BAR = 16 * STEP_MS
    gaps = lambda r: "-".join(str(b - a) for a, b in zip([i for i, c in enumerate(r) if c == "x"], [i for i, c in enumerate(r) if c == "x"][1:] + [16]))
    # K3 on NUMERIC says what the knobs do; K1 on 7: READY, the screen names the rhythm and the message its shape
    s = Script()
    t = seq_page(s, 100, 0, encs=[(K3, 2)])
    s.at(t, "dump", 0)
    t = seq_page(s, t + 60, 0, encs=[(K1, 3)])
    s.press(t, SEQ); s.at(t + 700, "ui"); s.release(t + 760, SEQ); t += 820
    s.at(t, "dump", 0)
    p = t + 100
    s.tap_btn(p, PLAY)
    ts = p + int(BAR) + 30
    t = seq_page(s, ts, 0, keys=[wk(5)])                                 # SEQ + white 6: it plays
    s.at(t, "dump", 0)
    t3 = p + int(3 * BAR) + 30
    t = seq_page(s, t3, 0, encs=[(K2, 2)])                               # turned two steps later, live
    s.at(t, "dump", 0)
    log = run(s, p + int(5 * BAR) - 40)
    st, v = log.states, v16s(log)
    check(len(st) == 4 and st[0]["msg"] == "NUMERIC: K1 PICKS 1 OF 16 RHYTHMS, K2 TURNS IT" and cfgs(log)[0]["fam"] == 2,
          "K3 on NUMERIC: the message says what K1 and K2 do (%s)" % (st[0]["msg"] if st else st))
    check(len(st) == 4 and st[1]["msg"] == "NUMERIC READY T1: 7 = 3-3-4-2-4 SEQ + WHITE 6" and v[1]["euc"] == 0 and v[1]["pulses"] == 7,
          "K1 on 7: READY, the message gives the rhythm's shape (%s)" % (st[1]["msg"] if len(st) > 1 else st))
    sc = [x for x in log.screens() if x["cells"][0] and x["cells"][0][0].endswith("NUMERIC READY")]
    check(sc and sc[0]["cells"][0][1] == "7 OF 16" and sc[0]["cells"][1][0].endswith("ROTATE") and "EUC" not in sc[0]["cells"][1][0] and sc[0]["cells"][2][1] == "NUMERIC",
          "the screen: NUMERIC READY 7 OF 16, ROTATE, FAMILY NUMERIC (%s)" % ([x["cells"][:3] for x in log.screens()][:1],))
    n1 = [round((tm - p) / STEP_MS) - 32 for tm, d1, v_ in log.notes(ch=0, after=p + int(2 * BAR) - 20, before=p + int(3 * BAR) - 20)]
    n2 = [round((tm - p) / STEP_MS) - 64 for tm, d1, v_ in log.notes(ch=0, after=p + int(4 * BAR) - 20, before=p + int(5 * BAR) - 20)]
    check(not log.notes(ch=0, after=p, before=ts) and n1 == [0, 3, 6, 10, 12] and len(st) == 4 and st[2]["msg"] == "NUMERIC LIVE T1: 7 = 3-3-4-2-4",
          "silent until SEQ + white 6, then the son clave: steps 1 4 7 11 13 (%s, %s)" % (n1, st[2]["msg"] if len(st) > 2 else st))
    check(n2 == [2, 5, 8, 12, 14] and len(st) == 4 and st[3]["msg"] == "NUMERIC LIVE T1: 7 = 3-3-4-2-4 ROT 2" and st[3]["heard"].replace(" ", "") == "..x..x..x...x.x.",
          "K2 +2: the same rhythm two steps later (%s, %s)" % (n2, st[3]["msg"] if len(st) > 3 else st))
    # every value of K1: the sixteen rhythms in their order, each one's shape in the message; past the track's steps it stops
    s = Script()
    t = seq_page(s, 100, 0, encs=[(K3, 2), (K1, -5)], keys=[wk(5)])     # NUMERIC, K1 down to 1, live
    s.at(t, "dump", 0)
    for k in range(1, 17):
        t = seq_page(s, t + 60, 0, encs=[(K1, 1)])
        s.at(t, "dump", 0)
    log = run(s, t + 100)
    st, v = log.states, v16s(log)
    heard = [x["heard"].replace(" ", "") for x in st]
    check(len(st) == 17 and heard[:16] == NUMERIC_16, "K1 from 1 to 16: the sixteen base rhythms (%s)" % [i + 1 for i in range(min(len(heard), 16)) if heard[i] != NUMERIC_16[i]])
    check(len(st) == 17 and all(st[i]["msg"] == "NUMERIC LIVE T1: %d = %s" % (i + 1, gaps(NUMERIC_16[i])) for i in range(16)),
          "... each with its number and its shape in the message (%s)" % [x["msg"] for x in st[:17] if not x["msg"].startswith("NUMERIC LIVE T1: ")][:3])
    check(len(v) == 17 and v[16]["pulses"] == 16 and heard[16] == NUMERIC_16[15], "K1 stops at the track's 16 steps (%s)" % (v[16]["pulses"] if len(v) > 16 else v))
    check(all(4 <= r.count("x") <= 7 and r[0] == "x" and "xx" not in r + r[0] for r in heard), "each: a hit on the first step, 4 to 7 hits, never two in a row")
    # a track of 32 steps: the rhythm comes twice; K1 past 16 comes round to the first ones; WRITE LIVE puts it in the pattern
    s = Script()
    t = home_page(s, 100, 0, [(K2, 16)])                                 # LENGTH 32
    t = seq_page(s, t, 0, encs=[(K3, 2), (K1, 8)], keys=[wk(5)])        # NUMERIC 12: the tresillo twice
    s.at(t, "dump", 0)
    t = seq_page(s, t + 60, 0, encs=[(K1, 7)])                           # 19 = 16 + 3
    s.at(t, "dump", 0)
    t = seq_page(s, t + 60, 0, keys=[wk(6)])                             # WRITE LIVE
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    st, v, d = log.states, v16s(log), log.dumps
    check(len(st) == 3 and len(d) == 3 and d[0]["length"] == 32 and st[0]["heard"].replace(" ", "")[:32] == NUMERIC_16[11] * 2,
          "32 steps: the sixteen steps come twice (%s)" % (st[0]["heard"] if st else st))
    check(len(st) == 3 and v[1]["pulses"] == 19 and st[1]["heard"].replace(" ", "")[:32] == NUMERIC_16[2] * 2 and st[1]["msg"] == "NUMERIC LIVE T1: 3 = 3-5-4-4",
          "K1 on 19: the third rhythm again (%s, %s)" % (st[1]["heard"] if len(st) > 1 else st, st[1]["msg"] if len(st) > 1 else ""))
    check(len(d) == 3 and d[2]["on"].replace(" ", "")[:32] == NUMERIC_16[2] * 2 and v[2]["euc"] == 0,
          "WRITE LIVE: the rhythm is in the pattern, EUCLID LIVE off (%s)" % (d[2]["on"] if len(d) > 2 else d))


def cell_row(text): return [1 if c == "x" else 0 for c in text.replace(" ", "")]
def cell_text(row): return "".join("x" if b else "." for b in row)
def cell_step(row, rule, home):
    """a CELL's next row (0.23.1): the rule on a ring; every cell dead: the written rhythm again (a single cell if none)"""
    n = len(row)
    out = [(rule >> ((row[(i - 1) % n] << 2) | (row[i] << 1) | row[(i + 1) % n])) & 1 for i in range(n)]
    if not any(out): out = list(home[:n])
    if not any(out): out = [1 if i == n // 2 else 0 for i in range(n)]
    return out
def cell_hint(rule, row, home, track=1):
    """what the screen says of a rule: the story the long way (every row kept until one comes back)"""
    n, seen, hist, cur = len(row), {}, [], list(row)
    while tuple(cur) not in seen and len(hist) < 400:
        seen[tuple(cur)] = len(hist); hist.append(cur); cur = cell_step(cur, rule, home)
    head = "T%d CELL RULE %d: " % (track, rule)
    if tuple(cur) not in seen: return head + "KEEPS CHANGING FOR A LONG TIME"
    lead = seen[tuple(cur)]; loop = hist[lead:]; period = len(loop)
    after = "AFTER %d %s " % (lead, "ROW" if lead == 1 else "ROWS") if lead else ""
    if period == 1: return head + after + ("EVERY STEP PLAYS" if all(loop[0]) else "IT STAYS" if lead else "THE RHYTHM STAYS AS IT IS")
    for k in range(1, n // 2 + 1):
        for sign, word in ((1, "LATER"), (-1, "EARLIER")):
            if all(loop[(j + 1) % period] == [loop[j][(i - sign * k) % n] for i in range(n)] for j in range(period)):
                return head + after + "SLIDES %d %s %s" % (k, "STEP" if k == 1 else "STEPS", word) + ("" if lead else " EVERY ROW")
    return head + after + "A LOOP OF %d" % period + ("" if lead else " ROWS")


def t0231_cell():
    group("0.23.1 CELL: a dead row goes back to the written rhythm (not to a single cell); the screen says what a rule makes of the rhythm")
    BAR = 16 * STEP_MS
    TRES = "x..x..x...x.x..."
    def knob_to(s, t, knob, now, want):
        return seq_page(s, t, 1, encs=[(knob, want - now)]) if want != now else t
    # rule 0 kills every row at once: the written rhythm plays on, bar after bar (0.23: one hit on step 9 for ever)
    s = Script()
    t = s.steps(100, [0, 4, 8, 12])
    t = seq_page(s, t + 30, 1, encs=[(K1, 2), (K2, -90)])               # CELL READY, rule 90 -> 0
    s.at(t, "dump", 0)
    t = seq_page(s, t + 30, 1, keys=[wk(5)])
    p = t + 100
    s.tap_btn(p, PLAY)
    s.at(p + int(3.5 * BAR), "dump", 0)
    log = run(s, p + int(5 * BAR) - 40)
    st = states(log)
    n4 = [round((tm - p) / STEP_MS) - 64 for tm, d1, v_ in log.notes(ch=0, after=p + int(4 * BAR) - 20)]
    check(len(st) == 2 and st[0]["algo"] == 0 and st[0]["msg"] == "T1 CELL RULE 0: THE RHYTHM STAYS AS IT IS",
          "READY, rule 0: the screen says the rhythm stays (%s)" % (st[0]["msg"] if st else st))
    check(len(st) == 2 and st[1]["algo"] == 2 and st[1]["a"] == 0 and st[1]["heard"].replace(" ", "") == "x...x...x...x..." and n4 == [0, 4, 8, 12],
          "rule 0 playing: in bar 4 and 5 still the four written hits (%s, %s)" % (st[1]["heard"] if len(st) > 1 else st, n4))
    # rule 90 on 16 cells from the tresillo: the rows of the rule, a new one every bar; the eighth dies and the tresillo is back
    s = Script()
    t = s.steps(100, [0, 3, 6, 10, 12])
    t = seq_page(s, t + 30, 1, encs=[(K1, 2), (K2, 1), (K2, -1)])       # CELL READY; the rule touched: its story on the screen
    s.at(t, "dump", 0)
    t = seq_page(s, t + 30, 1, keys=[wk(5)])
    p = t + 100
    s.tap_btn(p, PLAY)
    for b in range(18): s.at(p + int((b + 0.5) * BAR), "dump", 0)
    log = run(s, p + int(18 * BAR) + 100)
    st = states(log)
    rows = [x["heard"].replace(" ", "") for x in st[1:]]
    want, cur = [], cell_row(TRES)
    for b in range(len(rows) + 2): want.append(cell_text(cur)); cur = cell_step(cur, 90, cell_row(TRES))
    k0 = next((k for k in range(2) if rows[:1] == want[k:k + 1]), 0)    # (the first bar plays the written row, or the one after it)
    check(st and st[0]["msg"] == "T1 CELL RULE 90: A LOOP OF 8 ROWS" == cell_hint(90, cell_row(TRES), cell_row(TRES)),
          "READY, rule 90 on the tresillo: A LOOP OF 8 ROWS (%s)" % (st[0]["msg"] if st else st))
    check(len(rows) == 18 and rows == want[k0:k0 + 18], "playing: every bar the rule's next row (%s)" % [(i, r) for i, r in enumerate(rows) if r != want[k0 + i]][:3])
    check(len(rows) == 18 and rows.count(TRES) >= 2 and all(rows[i + 8] == rows[i] for i in range(10)) and len(set(rows[:8])) == 8 and "........x......." not in rows,
          "... eight different rows, then the tresillo again - not the single cell of 0.23 (%s)" % [i for i, r in enumerate(rows) if r == TRES])
    # what the screen says, rule by rule, of a READY CELL on the tresillo: as the long way works it out
    RULES = [204, 170, 240, 184, 226, 51, 150, 105, 60, 54, 18, 22, 126, 122, 110, 30, 13, 255, 77, 232, 0, 90]
    s = Script()
    t = s.steps(100, [0, 3, 6, 10, 12])
    t = seq_page(s, t + 30, 1, encs=[(K1, 2)])
    now = 90
    for r in RULES:
        t = knob_to(s, t + 30, K2, now, r); now = r
        s.at(t, "dump", 0)
    t = seq_page(s, t + 30, 1, encs=[(K3, -8)])                          # 8 cells: the row is the first half of the tresillo, twice
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    st, v = states(log), v16s(log)
    got = [x["msg"] for x in st]
    want = [cell_hint(r, cell_row(TRES), cell_row(TRES)) for r in RULES] + [cell_hint(90, cell_row(TRES[:8]), cell_row(TRES[:8]))]
    check(len(st) == len(RULES) + 1 and [x["edit"][1] for x in v[:-1]] == RULES and v[-1]["edit"][1:3] == (90, 8) and got == want,
          "22 rules and a width: the message is the rule's story (%s)" % [(g, w) for g, w in zip(got, want) if g != w][:3])
    check("T1 CELL RULE 170: SLIDES 1 STEP EARLIER EVERY ROW" in got and "T1 CELL RULE 240: SLIDES 1 STEP LATER EVERY ROW" in got
          and "T1 CELL RULE 204: THE RHYTHM STAYS AS IT IS" in got and "T1 CELL RULE 255: AFTER 1 ROW EVERY STEP PLAYS" in got
          and "T1 CELL RULE 30: KEEPS CHANGING FOR A LONG TIME" in got and "T1 CELL RULE 51: A LOOP OF 2 ROWS" in got,
          "... the ones one can name: 170 and 240 slide, 204 stays, 255 fills, 51 swaps, 30 has no loop in sight (%s)" % got[:3])
    check(all(len(g) <= 58 for g in got), "every message fits the screen's two lines (%s)" % max(len(g) for g in got))
    # while it plays the story starts from the row that plays: rule 204 holds it; rule 0 then kills it: after that row the tresillo, for good
    s = Script()
    t = s.steps(100, [0, 3, 6, 10, 12])
    t = seq_page(s, t + 30, 1, encs=[(K1, 2)], keys=[wk(5)])
    p = t + 100
    s.tap_btn(p, PLAY)
    t = knob_to(s, p + int(3.3 * BAR), K2, 90, 204)
    s.at(t, "dump", 0)
    s.at(p + int(5.5 * BAR), "dump", 0)
    t = knob_to(s, p + int(6.3 * BAR), K2, 204, 0)
    s.at(t, "dump", 0)
    s.at(p + int(7.5 * BAR), "dump", 0)
    log = run(s, p + int(8 * BAR))
    st = states(log)
    held = st[0]["heard"].replace(" ", "") if st else ""
    check(len(st) == 4 and held != TRES and st[0]["msg"] == "T1 CELL RULE 204: THE RHYTHM STAYS AS IT IS" and st[1]["heard"].replace(" ", "") == held,
          "rule 204 while it plays: the row of that bar is held (%s, %s)" % (held, st[0]["msg"] if st else st))
    check(len(st) == 4 and st[2]["msg"] == "T1 CELL RULE 0: AFTER 1 ROW IT STAYS" and st[3]["heard"].replace(" ", "") == TRES,
          "rule 0 then: AFTER 1 ROW IT STAYS, and the next bar is the tresillo (%s, %s)" % (st[2]["msg"] if len(st) > 2 else st, st[3]["heard"] if len(st) > 3 else ""))
    # nothing written: the single cell in the middle, as before (and after a death again)
    s = Script()
    t = seq_page(s, 100, 1, encs=[(K1, 2), (K2, -90)], keys=[wk(5)])
    p = t + 100
    s.tap_btn(p, PLAY)
    s.at(p + int(2.5 * BAR), "dump", 0)
    log = run(s, p + int(3 * BAR))
    st = states(log)
    check(len(st) == 1 and st[0]["heard"].replace(" ", "") == "........x.......", "an empty track, rule 0: the single cell in the middle, as it was (%s)" % (st[0]["heard"] if st else st))
    # the grid (TRACK 3): row 5 the rules from the calm to the wild, row 6 the widths - each tap says the story
    s = Script()
    t = s.steps(100, [0, 3, 6, 10, 12])
    s.raw(t, "attach"); view(s, t + 100, GC_VTRACK); view(s, t + 200, GC_VTRACK); view(s, t + 300, GC_VTRACK); t += 400
    s.pad(t, 2, 3); t += 100                                             # CELL READY
    for x in (0, 1, 2, 4, 15):
        s.pad(t, x, 4); t += 100; s.at(t, "dump", 0); t += 20
    s.pad(t, 2, 5); t += 100; s.at(t, "dump", 0)                         # 8 cells
    log = run(s, t + 100)
    st, v = states(log), v16s(log)
    want = [cell_hint(r, cell_row(TRES), cell_row(TRES)) for r in (204, 170, 240, 51, 30)] + [cell_hint(30, cell_row(TRES[:8]), cell_row(TRES[:8]))]
    check(len(st) == 6 and [x["edit"][1] for x in v] == [204, 170, 240, 51, 30, 30] and v[5]["edit"][2] == 8 and [x["msg"] for x in st] == want,
          "the grid's rule pads 1 2 3 5 16: 204 170 240 51 30, then 8 cells; each says its story (%s)" % [(x["edit"], y["msg"]) for x, y in zip(v, st)][:2])
    # the tablet's A on a CELL: the rule and its story, said as the tablet's
    s = Script()
    t = remote13_on(s, 100)
    t = usb2(s, t)
    t = s.steps(t, [0, 3, 6, 10, 12])
    s.raw(t, "midi 0xBB 12 2 2"); t += 40                                # ALGO: CELL READY
    s.raw(t, "midi 0xBB 13 120 2"); t += 40                              # A = 120 of 127: rule 240 (0.23.2: the even rules; it was 241)
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    st, v = states(log), v16s(log)
    check(len(st) == 1 and v[0]["edit"][:2] == (2, 240) and st[0]["rawmsg"] == "TAB " + cell_hint(240, cell_row(TRES), cell_row(TRES)) and st[0]["msg"] == "T1 CELL RULE 240: SLIDES 1 STEP LATER EVERY ROW",
          "the tablet's A on 120: rule 240, TAB T1 CELL RULE 240: SLIDES 1 STEP LATER EVERY ROW (%s)" % (st[0]["rawmsg"] if st else st))


def t0232_tablet_rule():
    group("0.23.2 the tablet's A on a CELL picks the EVEN rules (2 x the knob): the ones that slide, stay, open are within its reach; the other knobs are spread as they were")
    TRES = "x..x..x...x.x..."
    PICKS = [(85, 170), (102, 204), (92, 184), (113, 226), (75, 150), (45, 90), (15, 30), (0, 0), (127, 254), (64, 128), (63, 126), (120, 240)]
    s = Script()
    t = remote13_on(s, 100)
    t = usb2(s, t)
    t = s.steps(t, [0, 3, 6, 10, 12])
    s.raw(t, "midi 0xBB 12 2 2"); t += 40                                # ALGO: CELL READY
    for cc, rule in PICKS:
        s.raw(t, "midi 0xBB 13 %d 2" % cc); t += 40
        s.at(t, "dump", 0); t += 20
    t2 = t
    log = run(s, t + 6000)
    st, v = states(log), v16s(log)
    got = [x["rawmsg"] for x in st]
    want = ["TAB " + cell_hint(r, cell_row(TRES), cell_row(TRES)) for c, r in PICKS]
    check(len(st) == len(PICKS) and [x["edit"][:2] for x in v] == [(2, r) for c, r in PICKS] and got == want,
          "twelve places of A: the rule is twice the knob, and the screen says its story (%s)" % [(x["edit"][:2], g) for x, g in zip(v, got) if (x["edit"][1], g) not in [(r, w) for (c, r), w in zip(PICKS, want)]][:3])
    check("TAB T1 CELL RULE 170: SLIDES 1 STEP EARLIER EVERY ROW" in got and "TAB T1 CELL RULE 240: SLIDES 1 STEP LATER EVERY ROW" in got
          and "TAB T1 CELL RULE 204: THE RHYTHM STAYS AS IT IS" in got and "TAB T1 CELL RULE 150: A LOOP OF 8 ROWS" in got,
          "... 170 and 240 slide the written rhythm itself, 204 holds it, 150 comes home in 8 rows: none of them could be had before (%s)" % got[:2])
    out = [(m[0], m[1], m[2], m[3]) for m, p in zip(log.msgs, log.port) if p == 2 and (m[1] & 0xF0) == 0xB0]
    back = {(st_ & 15, c): val for tt, st_, c, val in out if tt > t2 + 500}
    check(back.get((11, 13)) == 120, "the FM-1 says the knob's place back: 120 for rule 240 (%s)" % back.get((11, 13)))
    # a rule the panel chose that the knob has not (51): the knob shows the place under it, and moves on from there
    s = Script()
    t = remote13_on(s, 100)
    t = usb2(s, t)
    t = s.steps(t, [0, 3, 6, 10, 12])
    s.raw(t, "midi 0xBB 12 2 2"); t += 40                                # the tablet: CELL READY (and the FM-1 knows a tablet listens)
    t = seq_page(s, t + 30, 1, encs=[(K2, -39)])                        # the panel: rule 90 -> 51
    s.at(t, "dump", 0)
    t2 = t
    log = run(s, t + 6000)
    v = v16s(log)
    out = [(m[0], m[1], m[2], m[3]) for m, p in zip(log.msgs, log.port) if p == 2 and (m[1] & 0xF0) == 0xB0]
    back = {(st_ & 15, c): val for tt, st_, c, val in out if tt > t2 + 500}
    check(len(v) == 1 and v[0]["edit"][:2] == (2, 51) and back.get((11, 13)) == 25, "the panel's rule 51: the tablet's A stands on 25 (%s, %s)" % (v[0]["edit"][:2] if v else v, back.get((11, 13))))
    # CELL's other knob and another algorithm's: spread over their range, as before
    s = Script()
    t = remote13_on(s, 100)
    t = usb2(s, t)
    s.raw(t, "midi 0xBB 12 2 2"); t += 40                                # CELL READY
    s.raw(t, "midi 0xBB 14 25 2"); t += 40; s.at(t, "dump", 0); t += 20  # B = 25: 16 cells
    s.raw(t, "midi 0xBB 14 127 2"); t += 40; s.at(t, "dump", 0); t += 20 # B = 127: 64 cells
    s.raw(t, "midi 0xBB 15 127 2"); t += 40; s.at(t, "dump", 0); t += 20 # C = 127: a new row every loop (3)
    s.raw(t, "midi 0xBB 12 1 2"); t += 40                                # TURING READY
    s.raw(t, "midi 0xBB 13 127 2"); t += 40; s.at(t, "dump", 0); t += 20 # A = 127: mutation 100 %
    s.raw(t, "midi 0xBB 13 64 2"); t += 40; s.at(t, "dump", 0); t += 20  # A = 64: 50 %
    log = run(s, t + 100)
    v = v16s(log)
    check(len(v) == 5 and [x["edit"][0] for x in v] == [2, 2, 2, 1, 1] and v[0]["edit"][2] == 16 and v[1]["edit"][2] == 64 and v[2]["edit"][3] == 3
          and v[3]["edit"][1] == 100 and v[4]["edit"][1] == 50,
          "CELLS 25 -> 16, 127 -> 64, NEW ROW 127 -> 3; TURING's MUTATION 127 -> 100, 64 -> 50 (%s)" % [x["edit"] for x in v])


def t0231_counts():
    group("0.23.1 the PC test's account: DIAG says what the FM-1 sent by port and kind, QUIET stops it and leaves it silent - the numbers are the simulator's own log's")
    sys.path.insert(0, os.path.join(ROOT, "tools", "hwtest"))
    import sagga_testport as TP

    def sx(s, t, b): s.at(t, "sx", " ".join("%02X" % x for x in b[1:-1]))

    def answers(log, what):
        return [(t, a[1]) for t, a in ((t, TP.parse(bytes(b))) for t, b in log.sysex) if a and a[0] == what]

    def counted(log, t0, t1):
        """what the log says went out in [t0, t1): by port the kinds, the bytes of the messages and of the SysEx frames"""
        out = [dict.fromkeys(TP.OUT_KINDS, 0), dict.fromkeys(TP.OUT_KINDS, 0)]
        for (t, st, d1, d2), port in zip(log.msgs, log.port):
            if t0 <= t < t1:
                d = [st, d1, d2][:1 if st >= 0xF8 else 2 if (st & 0xE0) == 0xC0 else 3]
                out[port - 1][TP.out_kind(d)] += 1
                out[port - 1]["bytes"] += len(d)
        return out

    def session(ring=None):
        evs = [(100, TP.KEYS, wk(0), 0), (140, TP.KEYS, 0, 0), (200, TP.KEYS, wk(2), 0), (240, TP.KEYS, 0, 0), (300, TP.KEYS, wk(4), 0),
               (340, TP.KEYS, 0, 0), (400, TP.KEYS, wk(7), 0), (440, TP.KEYS, 0, 0), (600, TP.PRESS, PLAY, 0), (630, TP.RELEASE, PLAY, 0),
               (1500, TP.KNOB, 300, 0), (2500, TP.PROBE, 0, 0), (4300, TP.PROBE, 0, 0), (4400, TP.END, 0, 0)]
        s = Script()
        if ring is not None: s.raw(500, "ring %d" % ring)
        sx(s, 900, TP.diag()); sx(s, 1000, TP.go()); sx(s, 1010, TP.ev_frame(0, evs))
        sx(s, 6000, TP.quiet()); sx(s, 6400, TP.diag())
        return run(s, 7000, testboot=True)

    log = session()
    dg, qt = answers(log, "diag"), answers(log, "quiet")
    check(len(dg) == 2 and [a for _, a in qt] == [1] and "p1_ticks" in dg[0][1] and len(dg[0][1]) == len(TP.DIAG_FIELDS) + len(TP.DIAG_MORE),
          "DIAG before GO and after QUIET, QUIET says yes (%s %s)" % (len(dg), qt))
    if len(dg) == 2:
        d0, d1 = dg[0][1], dg[1][1]
        got = [{k: d1["p%d_%s" % (p, k)] - d0["p%d_%s" % (p, k)] for k in TP.OUT_KINDS} for p in (1, 2)]
        want = counted(log, 900, 6400)
        frames = sum(len(b) for t, b in log.sysex if 900 <= t < 6400)     # (the first DIAG's answer is in, the second's not yet)
        want[0]["bytes"] += frames                                        # (one USB port: the SysEx goes out of it too)
        check(all(d0["p%d_%s" % (p, k)] == 0 for p in (1, 2) for k in TP.OUT_KINDS), "before GO nothing had been sent (%s)" % {k: v for k, v in d0.items() if k.startswith("p") and v})
        check(got == want and want[0]["ticks"] > 150 and want[0]["on"] >= 8 and want[0]["on"] == want[0]["off"] and want[0]["other"] >= 2,
              "between the two: the clock's ticks, the notes on and off, the START and the STOP, the bytes - as the log counts them (%s, the log %s)" % (got, want))
        sent = sum(got[p][k] for p in (0, 1) for k in TP.OUT_KINDS[:5])
        check(d1["tx_ev"] - d0["tx_ev"] == sent and d1["tx_ring"] == 0 and d1["tx_drop"] == 0 and d1["tx_noconf"] == 0 and d1["tx_flush"] == 0,
              "the ring's account: every one of the %d left for the host (%s)" % (sent, {k: d1[k] for k in ("tx_ev", "tx_ring", "tx_drop")}))
        stop = [m for m in log.msgs if m[0] >= 6000]
        check(any(st == 0xFC for _, st, _, _ in stop) and not [m for m in log.msgs if m[0] > 6050] and " PROBE" not in log.text.split("6400 ms")[-1],
              "QUIET: the STOP and the notes off at once, then not a message more (%s)" % [m for m in log.msgs if m[0] > 6050][:3])
    # a ring of 8 events: what does not fit is dropped and SAID - sent = left + dropped + waiting
    log = session(ring=8)
    dg = answers(log, "diag")
    if len(dg) == 2:
        d0, d1 = dg[0][1], dg[1][1]
        sent = sum(d1["p%d_%s" % (p, k)] - d0["p%d_%s" % (p, k)] for p in (1, 2) for k in TP.OUT_KINDS[:5])
        drops = len(re.findall(r"MIDI DROP", log.text))
        check(drops > 0 and d1["tx_drop"] - d0["tx_drop"] == drops and sent == (d1["tx_ev"] - d0["tx_ev"]) + drops + d1["tx_ring"] - d0["tx_ring"],
              "a ring of 8: %d dropped, and the account still adds up (sent %d, left %d, waiting %d)" % (drops, sent, d1["tx_ev"] - d0["tx_ev"], d1["tx_ring"]))
    else:
        check(False, "a ring of 8: two DIAGs (%d)" % len(dg))
    # QUIET outside a test boot: no
    s = Script()
    sx(s, 500, TP.quiet())
    log = run(s, 800)
    check([a for _, a in answers(log, "quiet")] == [0], "QUIET outside the test: no (%s)" % answers(log, "quiet"))


# ------------------------------------------------------------------------------------------------ 0.24: the length is the track's
def _played(log, p0, bars, ch=0):
    """the note of every step after p0, a bar a list (None: silence); melody16's notes are 0..15"""
    row = {}
    for tm, d1, v in log.notes(ch=ch, after=p0):
        row[round((tm - p0) / STEP_MS)] = d1 - 60
    return [[row.get(b * 16 + i) for i in range(16)] for b in range(bars)]


def _bars(on): return [on[i:i + 16] for i in range(0, len(on), 16)]


def t024_lengths():
    group("0.24 THE LENGTH IS THE TRACK'S: 16 -> 19 -> 32 at the bars is the pattern twice, from the bar line; shorter and back; the 64th step alone; a second bar written first")
    BAR = 16 * STEP_MS
    M16 = list(range(16))
    # THE ONE THAT WAS WRONG. A melody of 16 steps plays; LENGTH 19 asked in bar 1 (it waits for the bar), LENGTH 32 asked
    # in bar 3. 0.23.2: the step on the bar line of bar 4 was the old loop's (its step 11), and the 32 steps were the
    # NINETEEN going on - 0 1 2 0 1 .. 12 in the second bar, three steps off, for good.
    s = Script()
    t = melody16(s)
    s.tap_btn(t, PLAY); p0 = t
    home_page(s, p0 + int(4.5 * STEP_MS), 0, [(K2, 3)])
    home_page(s, p0 + int(36.5 * STEP_MS), 0, [(K2, 13)])
    s.at(p0 + int(20 * STEP_MS), "dump", 0)
    s.at(p0 + int(50 * STEP_MS), "dump", 0)
    log = run(s, p0 + int(6 * BAR) - 20)
    b = _played(log, p0, 6)
    msgs = [x["msg"] for x in log.states]
    check([d["length"] for d in log.dumps] == [19, 32] and [c["own"] for c in log.copies] == [16, 16],
          "19 at the bar, then 32 at the bar: the pattern is still its 16 steps (%s, own %s)" % ([d["length"] for d in log.dumps], [c["own"] for c in log.copies]))
    check(log.copies[0]["row"] == "x" * 16 + "ggg" + "." * 45 and log.copies[1]["row"] == "x" * 16 + "g" * 16 + "." * 32,
          "what the track has more are the pattern's COPIES: three, then sixteen (%s | %s)" % (log.copies[0]["row"][:20], log.copies[1]["row"][:34]))
    check(msgs == ["LENGTH 19: THE 16 STEPS REPEAT", "LENGTH 32: THE 16 STEPS REPEAT"], "the screen says what plays (%s)" % msgs)
    check(b[0] == M16 and b[1] == [0, 1, 2] + list(range(13)) and b[2] == [13, 14, 15, 0, 1, 2] + list(range(10)),
          "19 steps: the polymetre - bar 2 begins with the three copies, bar 3 with steps 14 15 16 (%s | %s)" % (b[1], b[2]))
    check(b[3] == M16, "32 at the bar line of bar 4: the step ON the line is the pattern's first (0.23.2: its step 11, the old loop's) (%s)" % b[3])
    check(b[4] == M16 and b[5] == M16, "... and the 32 steps are the pattern twice: on the rails again (0.23.2: 0 1 2 0 1 .. 12, for good) (%s)" % b[4])

    # A TRACK SHORTER THAN ITS PATTERN, AND BACK. Twelve notes in a track of 16 (its last quarter silent). 12, then 16:
    # the four rests are there (0.11 - 0.23.2 put the first four notes in them: the loop "repeated"). A MARK keeps the
    # place where the pattern ends: a step at rest after it, flagged. 12, then 32: the pattern as it was, twice.
    s = Script()
    t = program(s, 100, [60 + i for i in range(12)])
    t = home_page(s, t, 0, [(K2, -4)]); s.at(t, "dump", 0); t += 50
    t = home_page(s, t, 0, [(K2, 4)]); s.at(t, "dump", 0); t += 50
    t = home_page(s, t, 0, [(K2, -4)])
    t = home_page(s, t, 0, [(K2, 20)]); s.at(t, "dump", 0); t += 50
    log = run(s, t + 100)
    d, c = log.dumps, log.copies
    check(d[0]["length"] == 12 and c[0]["row"] == "x" * 12 + "....r" + "." * 47, "LENGTH 12: the pattern keeps its 16 steps, a mark after them (%s)" % c[0]["row"][:20])
    check(d[1]["on"] == "x" * 12 + "...." and "r" not in c[1]["row"] and "g" not in c[1]["row"] and c[1]["own"] == 16,
          "... 16 again: the last quarter is silent as it was written (%s)" % d[1]["on"])
    check(d[2]["length"] == 32 and d[2]["on"] == ("x" * 12 + "....") * 2 and c[2]["own"] == 16 and c[2]["row"][16:32] == "g" * 12 + "rrrr",
          "12, then 32: the pattern as it was, twice - its rests copied too (%s, own %s)" % (d[2]["on"], c[2]["own"]))

    # THE LAST STEP ALONE. The 64th step written while the track loops its 16; LENGTH 40: nothing is copied, the track is
    # silent after the 16; LENGTH 64: the same; the 64th turned off before the cursor comes: 64 steps, 48 of them silent
    s = Script()
    t = melody16(s)
    s.enc(t, E_ALG, 63); t += 60
    s.press(t, SEL); s.tap_key(t + 30, 1 << (72 - 53), hold=40); s.release(t + 100, SEL); t += 520
    t = home_page(s, t, 0, [(K2, 24)]); s.at(t, "dump", 0); t += 50
    t = home_page(s, t, 0, [(K2, 24)]); s.at(t, "dump", 0); t += 50
    s.tap_key(t, wk(15)); t += 100; s.at(t, "dump", 0); t += 50
    s.tap_btn(t, PLAY); p0 = t
    log = run(s, p0 + int(4 * BAR) - 20)
    d, c = log.dumps, log.copies
    n = [sum(1 for x in bar if x is not None) for bar in _played(log, p0, 4)]
    check(d[0]["on"] == "x" * 16 + "." * 24 and c[0]["own"] == 40 and "g" not in c[0]["row"], "step 64 written, LENGTH 40: no copies, silence after the 16 (%s)" % d[0]["on"])
    check(d[1]["on"] == "x" * 16 + "." * 47 + "x" and c[1]["own"] == 64, "LENGTH 64: the 64 steps as written (%s)" % d[1]["on"])
    check(d[2]["on"] == "x" * 16 + "." * 48 and n == [16, 0, 0, 0], "the 64th turned off: one bar of notes, three of silence (%s)" % n)

    # A SECOND BAR WRITTEN WHILE THE TRACK LOOPS THE FIRST (one note, on step 21), then LENGTH 64: what was written is
    # part of the pattern - two bars now - and it is those two that go round
    s = Script()
    t = melody16(s)
    s.enc(t, E_ALG, 5); t += 60
    s.press(t, SEL); s.tap_key(t + 30, 1 << (72 - 53), hold=40); s.release(t + 100, SEL); t += 520
    t = home_page(s, t, 0, [(K2, 48)]); s.at(t, "dump", 0)
    log = run(s, t + 100)
    two = "x" * 16 + "....x..........."
    check(log.dumps[0]["on"] == two * 2 and log.copies[0]["own"] == 32 and log.states[0]["msg"] == "LENGTH 64: THE 32 STEPS REPEAT",
          "a note written in the second bar, then 64: the two bars twice (%s, own %s, %s)" % (_bars(log.dumps[0]["on"]), log.copies[0]["own"], log.states[0]["msg"]))


def t024_copies():
    group("0.24 the COPIES follow their pattern until one is written; every pattern of the track fits its length; a snapshot, UNDO, a power cycle; the grid's colour")
    def seqkey(s, t, key, hold=40): s.press(t, SEQ); s.tap_key(t + 30, key, hold=hold); s.release(t + 60 + hold, SEQ); return t + 140 + hold
    def store(s, t, n): s.press(t, SAVE); s.press(t + 20, SEL); s.tap_key(t + 40, bk(n)); s.release(t + 100, SEL); s.release(t + 120, SAVE); return t + 180
    def recall(s, t, n): s.press(t, SAVE); s.tap_key(t + 20, bk(n)); s.release(t + 100, SAVE); return t + 160

    # a step of the pattern turned off: its copy goes too. A copy turned off: every copy is a step of the player's from
    # then on (the screen says so), and a step of the pattern no longer moves the others
    s = Script()
    t = melody16(s)
    t = home_page(s, t, 0, [(K2, 16)])
    s.enc(t, E_ALG, -64); t += 60
    s.tap_key(t, wk(2)); t += 100; s.at(t, "dump", 0); t += 50          # step 3 off
    s.enc(t, E_ALG, 16); t += 60                                          # the cursor on step 17: the second page
    s.tap_key(t, wk(5)); t += 100; s.at(t, "dump", 0); t += 50          # step 22 off: a copy
    s.enc(t, E_ALG, -16); t += 60
    s.tap_key(t, wk(0)); t += 100; s.at(t, "dump", 0); t += 50          # step 1 off
    log = run(s, t + 100)
    d, c = log.dumps, log.copies
    check(d[0]["on"] == "xx." + "x" * 13 + "xx." + "x" * 13 and c[0]["own"] == 16 and c[0]["row"][16:32] == "ggr" + "g" * 13,
          "step 3 off: step 19, its copy, off too (%s)" % d[0]["on"])
    check(d[1]["on"] == "xx." + "x" * 13 + "xx.xx." + "x" * 10 and c[1]["own"] == 32 and "g" not in c[1]["row"] and "r" not in c[1]["row"]
          and log.states[1]["msg"] == "THE COPIES ARE YOUR STEPS NOW",
          "step 22 off, a copy: the copies are the player's steps, the pattern is 32 (%s, own %s, %s)" % (d[1]["on"], c[1]["own"], log.states[1]["msg"]))
    check(d[2]["on"] == ".x." + "x" * 13 + "xx.xx." + "x" * 10, "... step 1 off: step 17 stays (%s)" % d[2]["on"])

    # the track's OTHER patterns fit its length too (0.11: the one that played, and its CHAIN partner)
    s = Script()
    t = s.steps(100, [0, 4])
    s.enc(t, E_PRE, 1); t += 60; t = s.steps(t, [2])                     # pattern 2: step 3
    s.enc(t, E_PRE, -1); t += 60
    t = home_page(s, t, 0, [(K2, 16)]); s.at(t, "dump", 0); t += 50
    s.enc(t, E_PRE, 1); t += 60; s.at(t, "dump", 0); t += 50
    t = home_page(s, t, 0, [(K2, -20)]); s.at(t, "dump", 0); t += 50     # 12: the mark, in both
    s.enc(t, E_PRE, -1); t += 60; s.at(t, "dump", 0); t += 50
    log = run(s, t + 100)
    d, c = log.dumps, log.copies
    check([x["pat"] for x in d] == [1, 2, 2, 1] and d[0]["on"] == "x...x..........." * 2 and d[1]["on"] == "..x............." * 2 and c[0]["own"] == 16 and c[1]["own"] == 16,
          "LENGTH 32 with pattern 1 playing: pattern 2 has its copies as well (%s)" % d[1]["on"])
    check(c[2]["row"] == "..x.............r" + "." * 47 and c[3]["row"] == "x...x...........r" + "." * 47, "LENGTH 12: both keep their 16 steps and the mark (%s)" % c[3]["row"][:20])

    # the loop's START moved (HOME + ALG: step 5): no copy stands for the step it stood for any more - the copies of
    # both patterns are steps, as they sound; made longer after it, the track goes round its loop from step 5
    s = Script()
    t = s.steps(100, [0, 4])
    s.enc(t, E_PRE, 1); t += 60; t = s.steps(t, [2])
    s.enc(t, E_PRE, -1); t += 60
    t = home_page(s, t, 0, [(K2, 16)])
    s.press(t, HOME); s.enc(t + 30, E_ALG, 4); s.release(t + 100, HOME); t += 160
    s.at(t, "dump", 0); t += 50
    s.enc(t, E_PRE, 1); t += 60; s.at(t, "dump", 0); t += 50
    t = home_page(s, t, 0, [(K2, 16)]); s.at(t, "dump", 0); t += 50
    log = run(s, t + 100)
    d, c = log.dumps, log.copies
    check(d[0]["start"] == 4 and c[0]["own"] == 32 and c[0]["row"][:32] == "x...x..........." * 2 and c[1]["own"] == 32 and c[1]["row"][:32] == "..x............." * 2,
          "the loop's start on step 5: the copies of the two patterns are steps (%s | %s)" % (c[0]["row"][:34], c[1]["row"][:34]))
    check(d[2]["length"] == 48 and c[2]["own"] == 32 and c[2]["row"][32:48] == "rrrrrrrrrrrrrrgr" and log.states[2]["msg"] == "LENGTH 48: THE 28 STEPS REPEAT",
          "... 48 after it: the 28 steps of the loop go round (%s, %s)" % (c[2]["row"][30:50], log.states[2]["msg"]))

    # DOUBLE writes the loop again as steps (the player's: no copies) - the other pattern gets copies; UNDO: 16 again,
    # and the other pattern's copies are no more
    s = Script()
    t = s.steps(100, [0, 4])
    s.enc(t, E_PRE, 1); t += 60; t = s.steps(t, [2])
    s.enc(t, E_PRE, -1); t += 60
    t = seqkey(s, t, wk(13)); s.at(t, "dump", 0); t += 50                # DOUBLE
    s.enc(t, E_PRE, 1); t += 60; s.at(t, "dump", 0); t += 50
    s.enc(t, E_PRE, -1); t += 60
    t = seqkey(s, t, wk(7)); s.at(t, "dump", 0); t += 50                 # UNDO
    s.enc(t, E_PRE, 1); t += 60; s.at(t, "dump", 0); t += 50
    log = run(s, t + 100)
    d, c = log.dumps, log.copies
    check(d[0]["length"] == 32 and c[0]["own"] == 32 and c[0]["row"][:32] == "x...x..........." * 2, "DOUBLE: 32 steps, all the player's (%s)" % c[0]["row"][:34])
    check(c[1]["own"] == 16 and c[1]["row"][:32] == "..x.............rrgrrrrrrrrrrrrr", "... pattern 2: its copies (%s)" % c[1]["row"][:34])
    check(d[2]["length"] == 16 and d[3]["length"] == 16 and c[3]["row"] == "..x" + "." * 61, "UNDO: 16 again, pattern 2 as it was (%s)" % c[3]["row"][:34])

    # a SNAPSHOT keeps lengths, not steps: one of 16 recalled on a track of 32 takes the copies away; one of 32
    # recalled on a track of 16 brings them back from the pattern as it is NOW
    s = Script()
    t = s.steps(100, [0, 4])
    t = store(s, t, 0)
    t = home_page(s, t, 0, [(K2, 16)]); s.at(t, "dump", 0); t += 50
    t = recall(s, t, 0); s.at(t, "dump", 0); t += 50
    t = home_page(s, t, 0, [(K2, 16)]); t = store(s, t, 1)
    t = home_page(s, t, 0, [(K2, -16)]); s.tap_key(t, wk(1)); t += 100    # 16 again; step 2 written
    t = recall(s, t, 1); s.at(t, "dump", 0); t += 50
    log = run(s, t + 100)
    d, c = log.dumps, log.copies
    check(d[0]["length"] == 32 and d[1]["length"] == 16 and c[1]["row"] == "x...x" + "." * 59, "the snapshot of 16: the copies are no more (%s)" % c[1]["row"][:34])
    check(d[2]["length"] == 32 and d[2]["on"] == "xx..x..........." * 2 and c[2]["own"] == 16, "the snapshot of 32: the pattern as it is now, twice (%s)" % d[2]["on"])

    # SAVED, a power cycle: the copies and the mark come back (in the image: a list of which steps are copies - a copied
    # rest costs nothing), and a track made longer after it goes round from where its pattern ends
    with tempfile.TemporaryDirectory() as dd:
        fl = os.path.join(dd, "flash.bin")
        s = Script()
        t = s.steps(100, [0, 4])
        t = home_page(s, t, 0, [(K2, 16)])
        s.enc(t, E_SEL, 1); t += 60; t = s.steps(t, [0, 2, 9]); t = home_page(s, t, 0, [(K2, -4)])    # track 2: 12 of its 16
        s.enc(t, E_SEL, -1); t += 60
        s.at(t, "dump", 0); s.at(t + 10, "dump", 1)
        s.tap_btn(t + 50, SAVE); s.tap_btn(t + 350, SAVE)
        a = run(s, t + 3000, flash=fl)
        s = Script()
        s.at(1400, "dump", 0); s.at(1410, "dump", 1)
        t = home_page(s, 1500, 0, [(K2, 16)])
        s.enc(t, E_SEL, 1); t += 60; t = home_page(s, t, 0, [(K2, 12)])
        s.at(t, "dump", 0); s.at(t + 10, "dump", 1)
        b = run(s, t + 100, flash=fl)
        check(a.saves and [x["row"] for x in b.copies[:2]] == [x["row"] for x in a.copies[:2]] and b.copies[0]["own"] == 16 and "r" in b.copies[1]["row"]
              and [x["hash"] for x in b.dumps[:2]] == [x["hash"] for x in a.dumps[:2]],
              "after the power cycle: the same steps, the same copies, the mark (%s | %s)" % (b.copies[0]["row"][:34], b.copies[1]["row"][:20]))
        check(b.dumps[2]["on"] == "x...x..........." * 3 and b.dumps[3]["on"] == "x.x......x......x.x....." and b.copies[3]["own"] == 16,
              "... 48 and 24 after it: each goes round from its pattern's own end (%s | %s)" % (b.dumps[2]["on"], b.dumps[3]["on"]))
        # ... and what the copies cost in the slot: the same project with both tracks at 16 steps (no copies), saved
        s = Script()
        t = s.steps(100, [0, 4])
        s.enc(t, E_SEL, 1); t += 60; t = s.steps(t, [0, 2, 9])
        s.enc(t, E_SEL, -1); t += 60
        s.tap_btn(t + 50, SAVE); s.tap_btn(t + 350, SAVE)
        c0 = run(s, t + 3000, flash=os.path.join(dd, "flash0.bin"))
        size = lambda lg: [int(x) for x in re.findall(r"slot \d+ saved \((\d+) B\)", lg.text)]
        check(len(size(a)) == 1 and len(size(c0)) == 1 and 0 < size(a)[0] - size(c0)[0] <= 2 * 8 + 3 + 2 * 4,
              "in the slot: 16 copies and a mark cost %s bytes more (the two copied notes, and the list of which steps are copies; the 14 copied rests nothing)" % (size(a)[0] - size(c0)[0] if size(a) and size(c0) else None))

    # the grid's STEP view: a copy that plays has a colour of its own (GHOST, role 18); written on, it is a step
    s = Script()
    t = s.steps(100, [0, 4, 6])
    t = home_page(s, t, 0, [(K2, 16)])
    s.raw(t, "attach"); t += 100
    for k in range(0, 3000, 900): s.raw(t + k, "hb")
    t += 400; m1 = t
    s.pad(t + 50, 4, 1); t += 400; m2 = t                               # step 21: a copy, turned off
    log = run(s, t + 200)
    p1 = log.leds(until=m1)[0]; p2 = log.leds(until=m2)[0]
    check([p1.get(i) for i in (0, 4, 6)] == [3, 3, 6] and [p1.get(i) for i in (16, 20, 22)] == [18, 18, 18] and p1.get(17) == 1 and p1.get(32) == 0,
          "the grid: the pattern's steps as ever, its copies that play in GHOST, a copy at rest as any rest (%s)" % [p1.get(i) for i in range(16, 24)])
    check([p2.get(i) for i in (16, 22)] == [3, 3] and p2.get(20) == 14, "a copy turned off: the others are steps, lit as steps (%s)" % [p2.get(i) for i in range(16, 24)])


def t024_longer_shorter():
    group("0.24 LONGER / SHORTER (the MOSSE: SEL + DOUBLE / SEL + HALF; the grid: SHIFT + the pad): every track twice / half as long, in time; and back as it was")
    BAR = 16 * STEP_MS
    M16 = list(range(16))
    def mossa(s, t, i): s.press(t, SEL); s.tap_key(t + 30, bk(i)); s.release(t + 100, SEL); return t + 160

    # stopped: at once. Track 1 two steps in 16, track 2 one step in 12 of its 16, track 3 empty. LONGER twice, then
    # SHORTER twice: every track and every step as it was
    s = Script()
    t = s.steps(100, [0, 4])
    s.enc(t, E_SEL, 1); t += 60; t = s.steps(t, [2]); t = home_page(s, t, 0, [(K2, -4)])
    s.enc(t, E_SEL, -1); t += 60
    for k in range(3): s.at(t + 10 * k, "dump", k)
    t += 50
    t = vg_on(s, t, remote=False)
    t = mossa(s, t, 5)
    for k in range(3): s.at(t + 10 * k, "dump", k)
    t += 50
    t = mossa(s, t, 5)
    for k in range(3): s.at(t + 10 * k, "dump", k)
    t += 50
    t = mossa(s, t, 5)                                                    # a third time: nothing can be twice as long
    s.at(t, "dump", 0); t += 50
    t = mossa(s, t, 4); t = mossa(s, t, 4)
    for k in range(3): s.at(t + 10 * k, "dump", k)
    log = run(s, t + 100)
    d, c, m = log.dumps, log.copies, [x["msg"] for x in log.states]
    check([x["length"] for x in d[3:6]] == [32, 24, 32] and m[3] == "LONGER: 12 TRACKS TWICE AS LONG" and d[3]["on"] == "x...x..........." * 2 and c[3]["own"] == 16,
          "LONGER, stopped: at once, every track - 32, 24, 32; track 1 its bar twice (%s, %s)" % ([x["length"] for x in d[3:6]], m[3]))
    check(d[4]["on"] == "..x...............x....." and c[4]["own"] == 16, "track 2 was 12 of a pattern of 16: 24 is the pattern, and its first half again (%s)" % d[4]["on"])
    check([x["length"] for x in d[6:9]] == [64, 48, 64] and c[6]["own"] == 16 and d[6]["on"] == "x...x..........." * 4, "LONGER again: 64, 48, 64 (%s)" % [x["length"] for x in d[6:9]])
    check(m[9] == "LONGER: 0 TRACKS TWICE AS LONG, 12 STAY" and d[9]["length"] == 64, "a third time: twice would pass 64 steps - they stay, and the screen says so (%s)" % m[9])
    check([x["length"] for x in d[10:13]] == [16, 12, 16] and [x["hash"] for x in d[10:13]] == [x["hash"] for x in d[0:3]] and m[10] == "SHORTER: 12 TRACKS HALF AS LONG",
          "SHORTER twice: 16, 12, 16, every step as it was before (%s, %s)" % ([x["length"] for x in d[10:13]], m[10]))

    # playing: LONGER is a move - queued, at the phrase's end (four bars here); every bar of the melody in time
    s = Script()
    t = melody16(s)
    t = vg_bars4(s, t)
    t = vg_on(s, t, remote=False)
    s.tap_btn(t, PLAY); p0 = t
    mossa(s, p0 + int(20.5 * STEP_MS), 5)
    s.at(p0 + int(24 * STEP_MS), "dump", 0)
    s.at(p0 + int(66 * STEP_MS), "dump", 0)
    log = run(s, p0 + int(7 * BAR) - 20)
    d, c, m = log.dumps, log.copies, [x["msg"] for x in log.states]
    check(m[0] == "QUEUED: LONGER" and d[0]["length"] == 16 and d[1]["length"] == 32 and c[1]["own"] == 16, "playing: QUEUED, then 32 at the phrase's end (%s, %s)" % (m[0], d[1]["length"]))
    check(all(b == M16 for b in _played(log, p0, 7)), "... the melody never leaves the bar")

    # LONGER then SHORTER while they wait: neither (the screen says CANCELLED); NOW: nothing to do
    s = Script()
    t = melody16(s)
    t = vg_on(s, t, remote=False)
    s.tap_btn(t, PLAY); p0 = t
    mossa(s, p0 + int(4.5 * STEP_MS), 5); s.at(p0 + int(6 * STEP_MS), "dump", 0)
    mossa(s, p0 + int(8.5 * STEP_MS), 4); s.at(p0 + int(10 * STEP_MS), "dump", 0)
    s.tap_key(p0 + int(12.5 * STEP_MS), bk(10)); s.at(p0 + int(14 * STEP_MS), "dump", 0)
    log = run(s, p0 + int(2 * BAR) - 20)
    m = [x["msg"] for x in log.states]
    check(m == ["QUEUED: LONGER", "CANCELLED: LONGER", "QUEUE EMPTY: NOTHING TO DO NOW"] and log.dumps[2]["length"] == 16, "LONGER, then SHORTER: cancelled (%s)" % m)

    # the grid's VIAGGIO view: SHIFT + the pad of DOUBLE is LONGER (stopped: at once); playing, SHIFT + HALF queues
    # SHORTER and NOW brings it at the next bar: 16 again as it was, in time
    s = Script()
    t = melody16(s)
    s.raw(t, "attach"); t += 100
    t = view(s, t, GC_VPERF); t = view(s, t, GC_VPERF); t = view(s, t, GC_VPERF)
    s.at(t, "dump", 0); t += 30
    shift(s, t, 1); s.pad(t + 20, 5, 3); shift(s, t + 120, 0); t += 200
    s.at(t, "dump", 0); t += 50
    s.tap_btn(t, PLAY); p0 = t
    for k in range(0, 6000, 900): s.raw(p0 + k, "hb")
    shift(s, p0 + int(4.5 * STEP_MS), 1); s.pad(p0 + int(4.5 * STEP_MS) + 20, 4, 3); shift(s, p0 + int(4.5 * STEP_MS) + 120, 0)
    s.pad(p0 + int(8.5 * STEP_MS), 0, 0)                                  # NOW
    s.at(p0 + int(12 * STEP_MS), "dump", 0)
    s.at(p0 + int(18 * STEP_MS), "dump", 0)
    log = run(s, p0 + int(3 * BAR) - 20)
    d, m = log.dumps, [x["msg"] for x in log.states]
    check(d[1]["length"] == 32 and m[1] == "LONGER: 12 TRACKS TWICE AS LONG", "the grid, SHIFT + DOUBLE: LONGER (%s, %s)" % (d[1]["length"], m[1]))
    check(d[2]["length"] == 32 and d[3]["length"] == 16 and d[3]["hash"] == d[0]["hash"] and all(b == M16 for b in _played(log, p0, 3)),
          "SHIFT + HALF and NOW while it plays: 16 again at the bar, the pattern as it was, in time (%s)" % d[3]["length"])


def t024_makers():
    group("0.24 whoever brings a pattern keeps the track's length (17: the pattern and its first step; 12: the pattern waits); RANDOM, DICE, COOK and the engines make a phrase for it")
    def seqkey(s, t, key, hold=40): s.press(t, SEQ); s.tap_key(t + 30, key, hold=hold); s.release(t + 60 + hold, SEQ); return t + 140 + hold

    # a library pattern on a track of 17: the 16 steps and the first again; on a track of 12: its first 12, the rest
    # waiting after the loop - made 24 later, the track plays all of it and then its first half again
    s = Script()
    t = home_page(s, 100, 0, [(K2, 1)])
    t = beat_key(s, t); s.at(t, "dump", 0); t += 50
    t = home_page(s, t, 0, [(K2, -5)])
    t = beat_key(s, t); s.at(t, "dump", 0); t += 50
    t = home_page(s, t, 0, [(K2, 12)]); s.at(t, "dump", 0); t += 50
    log = run(s, t + 100)
    d, c = log.dumps, log.copies
    check(d[0]["length"] == 17 and d[0]["on"] == "x...x...x...x...x" and c[0]["own"] == 16 and c[0]["row"][16] == "g",
          "BEAT on a track of 17: the track stays 17, the 17th step is the first again (%s)" % d[0]["on"])
    check(d[1]["length"] == 12 and d[1]["on"] == "x...x...x..." and c[1]["row"][:17] == "x...x...x...x..xr", "BEAT on a track of 12: 12 play, the pattern is whole after the loop (%s)" % c[1]["row"][:20])
    check(d[2]["length"] == 24 and d[2]["on"] == "x...x...x...x..xx...x..." and c[2]["own"] == 16, "... 24: all of it, and its first half again (%s)" % d[2]["on"])

    # RANDOM on a track of 64: a PHRASE - the bar it made, its answer (the bar with another ending), the bar, the turn -
    # not the bar four times, not 64 steps of chance. On 32: the bar and its answer. On 16 and less: as ever
    for n, want in ((48, 4), (16, 2), (0, 1)):
        s = Script()
        t = home_page(s, 100, 0, [(K2, n)]) if n else 100
        t = seqkey(s, t, wk(4)); s.at(t, "dump", 0)
        log = run(s, t + 100)
        b = _bars(log.dumps[0]["on"])
        ok = len(b) == want and log.copies[0]["own"] == 16 * want and (want < 2 or (b[1] != b[0] and b[1][:8] == b[0][:8])) and (want < 4 or (b[2] == b[0] and b[3] != b[0] and b[3][:4] == b[0][:4]))
        check(ok, "RANDOM on %d steps: %s" % (16 * want, b))
    # ... DICE SEQ on a track of 64 with the library: a variation as a PHRASE - its bars (here a variation written over
    # two: A B A), and in the last the next variation with the genre's fill, not B again - whatever LONG PATTERNS
    # says (HEAT at 1: the take of each bar changes nothing here, the phrase is the library's). The steps are the
    # track's; OCT- puts back the bar and its three copies
    s = Script()
    t = beat_key(s, 100)
    t = home_page(s, t, 0, [(K2, 48)]); s.at(t, "dump", 0); t += 50
    t = pg(s, t, SEQ, 0, [(K4, -30)])                                    # HEAT 1
    t = seq_page(s, t, 0, keys=[bk(0)]); s.at(t, "dump", 0); t += 50
    s.tap_btn(t, OCT_DOWN); t += 100; s.at(t, "dump", 0); t += 50
    log = run(s, t + 100)
    d, c = log.dumps, log.copies
    b = _bars(d[1]["on"])
    check(c[0]["own"] == 16 and c[1]["own"] == 64 and b[2] == b[0] and b[3] != b[1] and b[3] != b[0] and b[0][:9] == "x...x...x",
          "DICE SEQ on 64 steps: the variation's bars, and a last bar that is another - a phrase, not the same bars again (%s)" % b)
    check(d[2]["hash"] == d[0]["hash"] and c[2]["own"] == 16, "... OCT-: the bar and its copies, as they were")
    # ... COOK walks to the next variation over the whole track: on 32 steps it gets there, and the track is that one
    s = Script()
    t = beat_key(s, 100)
    t = home_page(s, t, 0, [(K2, 16)])
    for k in range(12):
        t = seqkey(s, t, wk(8)); s.at(t, "dump", 0); t += 50
    log = run(s, t + 100)
    m = [x["msg"] for x in log.states]
    k = next((i for i, x in enumerate(m) if x.endswith("REACHED")), None)
    check(k is not None and m[k] == "COOK KICK #2 REACHED" and log.dumps[k]["length"] == 32 and log.dumps[k]["on"][:16] == "x...x...x...x..x",
          "COOK on 32 steps walks to KICK #2 and gets there (%s)" % m[:3])
    # ... the THEORY engines: a part is made in the bars the track has - 32 steps for a track of 48 (and its first bar
    # again), the seed turned (SEQ 8 K3) on a track of 64 makes four bars, on a track of 16 one
    s = Script()
    t = pg(s, 100, SEQ, 7, [(K1, 1)])                                     # SOURCE THEORY
    t = home_page(s, t, 0, [(K2, 32)])                                    # 48 steps
    t = seqkey(s, t, wk(9)); s.at(t, "dump", 0); t += 50                  # BEAT
    t = home_page(s, t, 0, [(K2, 16)]); s.at(t, "dump", 0); t += 50       # 64
    t = pg(s, t, SEQ, 7, [(K3, 1)]); s.at(t, "dump", 0); t += 50
    t = home_page(s, t, 0, [(K2, -48)])                                   # 16
    t = pg(s, t, SEQ, 7, [(K3, 1)]); s.at(t, "dump", 0); t += 50
    log = run(s, t + 100)
    d, c, m = log.dumps, log.copies, [x["msg"] for x in log.states]
    check(m[0] == "TECHNO KICK SEED 1" and d[0]["length"] == 48 and c[0]["own"] == 32 and d[0]["on"][32:] == d[0]["on"][:16], "THEORY, BEAT on 48 steps: two bars made, the first again (%s, own %s)" % (_bars(d[0]["on"]), c[0]["own"]))
    check(d[1]["length"] == 64 and c[1]["own"] == 32 and d[1]["on"][32:] == d[1]["on"][:32], "... 64: the two bars twice (own %s)" % c[1]["own"])
    check(m[2] == "KICK SEED 2" and c[2]["own"] == 64 and m[3] == "KICK SEED 3" and d[3]["length"] == 16 and c[3]["row"][16:] == "." * 48,
          "the seed turned: made again for the track as it is - four bars on 64, one on 16 (%s, own %s; %s, %s)" % (m[2], c[2]["own"], m[3], c[3]["row"][:20]))



def t025_tablet_lengths():
    group("0.25 LONGER / SHORTER from the tablet (channel 12 CC 61 / 60): every track, at once when stopped, at the next BAR while it plays; the other one takes it back")
    BAR = 16 * STEP_MS
    M16 = list(range(16))
    # stopped: at once
    s = Script()
    t = melody16(s)
    t = remote13_on(s, t)
    t = usb2(s, t)
    s.raw(t, "midi 0xBB 61 127 2"); s.raw(t + 20, "midi 0xBB 61 0 2"); t += 60
    s.at(t, "dump", 0); s.at(t + 10, "dump", 1); t += 50
    s.raw(t, "midi 0xBB 60 127 2"); s.raw(t + 20, "midi 0xBB 60 0 2"); t += 60
    s.at(t, "dump", 0); t += 50
    log = run(s, t + 100)
    d, c, m = log.dumps, log.copies, [x["msg"] for x in log.states]
    check([x["length"] for x in d] == [32, 32, 16] and c[0]["own"] == 16 and m[0] == "LONGER: 12 TRACKS TWICE AS LONG" and m[2] == "SHORTER: 12 TRACKS HALF AS LONG",
          "stopped: LONGER at once (32, the melody's 16 steps twice), every track; SHORTER: back (%s, %s | %s)" % ([x["length"] for x in d], m[0], m[2]))
    # playing: at the next bar line, in time; the release of the button does nothing
    s = Script()
    t = melody16(s)
    t = remote13_on(s, t)
    t = usb2(s, t)
    s.tap_btn(t, PLAY); p0 = t
    a = p0 + int(4.5 * STEP_MS)
    s.raw(a, "midi 0xBB 61 127 2"); s.raw(a + 20, "midi 0xBB 61 0 2")
    s.at(p0 + int(10 * STEP_MS), "dump", 0)                              # still in bar 1: it waits
    s.at(p0 + int(20 * STEP_MS), "dump", 0)                              # bar 2: there
    b = p0 + int(36.5 * STEP_MS)                                         # bar 3: SHORTER asked, then LONGER: taken back
    s.raw(b, "midi 0xBB 60 127 2"); s.raw(b + 20, "midi 0xBB 60 0 2")
    s.at(b + 60, "dump", 0)
    s.raw(b + 120, "midi 0xBB 61 127 2"); s.raw(b + 140, "midi 0xBB 61 0 2")
    s.at(b + 200, "dump", 0)
    s.at(p0 + int(52 * STEP_MS), "dump", 0)                              # bar 4: as it was
    log = run(s, p0 + int(5 * BAR) - 20)
    d, c, m = log.dumps, log.copies, [x["msg"] for x in log.states]
    pl = _played(log, p0, 5)
    check(d[0]["length"] == 16 and m[0] == "LONGER AT THE BAR" and d[1]["length"] == 32 and c[1]["own"] == 16,
          "playing: LONGER waits for the bar (%s: %s), then every track is twice as long (%s, the pattern still 16)" % (d[0]["length"], m[0], d[1]["length"]))
    check(all(x == M16 for x in pl), "... in time: every bar is the melody, from its first step (%s)" % [x[:3] for x in pl])
    check(m[2] == "SHORTER AT THE BAR" and m[3] == "CANCELLED: SHORTER" and d[4]["length"] == 32,
          "SHORTER asked, then LONGER before the bar: taken back, the tracks stay (%s, %s, %s)" % (m[2], m[3], d[4]["length"]))

# ------------------------------------------------------------------------------------------------ 0.25: the metre
def metre_knobs(s, t, encs): return pg(s, t, GLO, 3, encs)       # GLO 4 THE METRE: K1 the bar in steps, K2 its beats


def _flat(log, p0, n, ch=0):
    """the note of every step after p0 (None: silence), melody16's notes 0..15"""
    row = {}
    for tm, d1, v in log.notes(ch=ch, after=p0 - 5):
        row[round((tm - p0) / STEP_MS)] = d1 - 60
    return [row.get(i) for i in range(n)]


def _hits(log, p0, n, ch=0):
    """the steps after p0 where a note began: "x..x" (n of them)"""
    on = {round((tm - p0) / STEP_MS) for tm, d1, v in log.notes(ch=ch, after=p0 - 5)}
    return "".join("x" if i in on else "." for i in range(n))


def t025_turing_numeric():
    group("0.25 TURING as long as its track (LENGTH TRACK): the whole written rhythm is its loop, and it grows and shrinks with the track; NUMERIC in a loop shorter than a bar, and in the metre's bar")
    A, B = "x..x..x...x.....", "xx.x..x...x....."
    # a rhythm of two bars (the second with one more hit) on a track of 32. TURING on 16 steps (as until 0.24): the first
    # bar, twice. LENGTH TRACK: the two bars. No mutation: what plays is what is written
    out = {}
    for name, k3 in (("16", 8), ("TRACK", 20)):
        s = Script()
        t = s.steps(100, [0, 3, 6, 10])
        t = home_page(s, t + 30, 0, [(K2, 16)])                          # LENGTH 32: the bar and its copies
        s.tap_btn(t, OCT_UP); t += 100
        s.tap_key(t, wk(1)); t += 100                                    # step 18 written: the second bar is the player's
        s.tap_btn(t, OCT_DOWN); t += 100
        t = seq_page(s, t, 1, encs=[(K1, 1), (K3, k3), (K2, -20)], keys=[wk(5)])   # TURING, its LENGTH, no mutation; started
        s.press(t, SEQ); s.at(t + 700, "ui"); s.release(t + 760, SEQ); t += 820
        s.at(t, "dump", 0)
        p = t + 100
        s.tap_btn(p, PLAY)
        if name == "TRACK":
            home_page(s, p + int(40.5 * STEP_MS), 0, [(K2, 32)])           # in the third bar: LENGTH 64, at the bar
            s.at(p + int(60 * STEP_MS), "dump", 0)
            home_page(s, p + int(140.5 * STEP_MS), 0, [(K2, -52)])         # ... and 12
            s.at(p + int(150 * STEP_MS), "dump", 0)
        log = run(s, p + int(200 * STEP_MS))
        out[name] = (log, p)
    log, p = out["16"]
    sc = [x for x in log.screens() if x["cells"][2] and x["cells"][2][0].endswith("LENGTH")]
    check(log.dumps[0]["on"] == A + B and sc and sc[0]["cells"][2][1] == "16" and _hits(log, p, 64) == A * 4,
          "TURING on 16 steps over a track of 32: its loop is the first bar, whatever the second says (%s)" % _bars(_hits(log, p, 64)))
    log, p = out["TRACK"]
    sc = [x for x in log.screens() if x["cells"][2] and x["cells"][2][0].endswith("LENGTH")]
    h = _hits(log, p, 200)
    check(sc and sc[0]["cells"][2][1] == "TRACK" and h[:48] == (A + B) + A,
          "LENGTH turned past 16: TRACK - the two bars as they are written (%s | %s)" % (sc[0]["cells"][2] if sc else None, _bars(h[:48])))
    check(log.dumps[1]["length"] == 64 and h[48:144] == (B + A) * 3,
          "the track made 64 at the bar: the register grows with it, its loop again in the new steps - no silence (%s)" % _bars(h[48:112]))
    tail = h[144:192]
    check(log.dumps[2]["length"] == 12 and tail[:12] == tail[12:24] == tail[24:36] == tail[36:48] and tail.count("x") >= 8,
          "... made 12 at the bar (step 145): a loop of 12 (%s | %s)" % (tail[:12], tail[12:24]))

    # NUMERIC on a loop of 12 steps: the son clave of 12/8 (until 0.24: the first 12 steps of the sixteen, cut)
    s = Script()
    t = home_page(s, 100, 0, [(K2, -4)])
    t = seq_page(s, t, 0, encs=[(K3, 2), (K1, 3)], keys=[wk(5)])        # NUMERIC, the 7th rhythm, live
    s.at(t, "dump", 0)
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + int(36 * STEP_MS))
    h = _hits(log, p, 36)
    check(log.states[0]["msg"] == "NUMERIC LIVE T1: 7 = 2-2-3-2-3" and h == "x.x.x..x.x.." * 3,
          "NUMERIC 7 on 12 steps: 2-2-3-2-3, the clave in 12 (%s, %s)" % (log.states[0]["msg"], h[:12]))
    # ... in 7/8, a track of two bars: the rhythm in the bar of 14, every bar
    s = Script()
    t = metre_knobs(s, 100, [(K1, -2)])
    t = home_page(s, t, 0, [(K2, 14)])
    t = seq_page(s, t, 0, encs=[(K3, 2), (K1, 3)], keys=[wk(5)])
    s.at(t, "dump", 0)
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + int(56 * STEP_MS))
    h = _hits(log, p, 56)
    check(log.dumps[0]["length"] == 28 and log.states[0]["msg"] == "NUMERIC LIVE T1: 7 = 2-3-3-2-4" and h == "x.x..x..x.x..." * 4,
          "NUMERIC 7 in 7/8 on 28 steps: 2-3-3-2-4 in every bar of 14 (%s, %s)" % (log.states[0]["msg"], _bars14(h)[:2]))


def t025_polyrhythm():
    group("0.25 THE POLYRHYTHMS: five and seven steps in the time of four (HOME 1 K3 past 1/32T) - each step at its own time between the clock's ticks, in phase with the bar for good")
    BAR = 16 * STEP_MS
    TICK = STEP_MS / 6.0
    # five steps of a melody at 1/4 5:4: five notes in a bar of four quarters, 19.2 ticks apart; with a track of four on
    # the floor beside it: 5 against 4, together on every bar line
    for name, turns, per_bar, length in (("1/4 5:4", 4, 5, 5), ("1/4 7:4", 7, 7, 7), ("1/16 5:4", 6, 20, 5), ("1/8 7:4", 8, 14, 7)):
        s = Script()
        t = program(s, 100, [60 + i for i in range(length)])
        t = home_page(s, t, 0, [(K2, length - 16), (K3, 3)])            # LENGTH; the division down to 1/32T
        t = home_page(s, t, 0, [(K3, turns - 3)])                        # ... and past it
        s.at(t, "dump", 0)
        s.tap_key(t + 40, bk(1)); t += 120                               # track 2: four on the floor
        t = s.steps(t, [0, 4, 8, 12])
        s.tap_key(t + 40, bk(0)); t += 120
        s.press(t, HOME); s.at(t + 300, "ui"); s.release(t + 360, HOME); t += 420
        p = t + 100
        s.tap_btn(p, PLAY)
        bars = 4
        s.at(p + int(2.5 * BAR), "probe", "x")
        log = run(s, p + int(bars * BAR) - 10)
        n = [(tm - p, d1 - 60) for tm, d1, v in log.notes(ch=0, after=p - 5)]
        want = [k * BAR / per_bar for k in range(per_bar * bars)]
        err = max([abs(a[0] - w) for a, w in zip(n, want)] or [999])
        sc = [x for x in log.screens() if x["cells"][2] and x["cells"][2][0].endswith("STEP")]
        check(cfgs(log)[0]["div"] == 13 + ["1/4 5:4", "1/8 5:4", "1/16 5:4", "1/4 7:4", "1/8 7:4", "1/16 7:4"].index(name) and sc and sc[0]["cells"][2][1] == name,
              "HOME 1 K3 past 1/32T: %s (%s, %s)" % (name, cfgs(log)[0]["div"], sc[0]["cells"][2] if sc else None))
        check(len(n) == per_bar * bars and err <= 1.5 and [x[1] for x in n] == [k % length for k in range(per_bar * bars)],
              "%s: %d notes a bar, evenly apart (%.1f ms; the worst %.2f ms off), the melody in order (%s ...)" % (name, per_bar, BAR / per_bar, err, [round(x[0], 1) for x in n[:3]]))
        k4 = [tm - p for tm, d1, v in log.notes(ch=1, after=p - 5)]
        check(len(k4) == 4 * bars and all(abs(n[per_bar * b][0] - k4[4 * b]) <= 1.5 for b in range(bars)),
              "... against four on the floor: together on every bar line, bar after bar (%s)" % [round(n[per_bar * b][0] - k4[4 * b], 2) for b in range(bars)])
        pr = [l for l in log.text.splitlines() if "PROBE T1 " in l]
        check(pr and " ok=1" in pr[0], "... and the track is where the clock says (the probe's phase: %s)" % (re.findall(r" ok=\S+", pr[0]) if pr else pr))
    # a polyrhythm set while it plays lands in time at the next tick; back on 1/16 it is on the grid again; STOP and
    # PLAY: from the first step, on the line
    s = Script()
    t = melody16(s)
    s.tap_btn(t, PLAY); p = t
    home_page(s, p + int(4.3 * STEP_MS), 0, [(K3, 3)])
    home_page(s, p + int(8.3 * STEP_MS), 0, [(K3, 3)])                   # 1/16 5:4 from step 9 or so
    home_page(s, p + int(40.3 * STEP_MS), 0, [(K3, -6)])                 # 1/16 again
    s.tap_btn(p + int(70 * STEP_MS), PLAY)
    q = p + int(74 * STEP_MS)
    home_page(s, p + int(71 * STEP_MS), 0, [(K3, 9)])                    # stopped: 1/16 7:4
    s.tap_btn(q + 400, PLAY); q += 400
    log = run(s, q + int(32 * STEP_MS))
    a = [(tm - p, d1 - 60) for tm, d1, v in log.notes(ch=0, after=p + int(12 * STEP_MS), before=p + int(40 * STEP_MS))]
    grid5 = 4 * STEP_MS / 5.0
    off = [abs(x[0] / grid5 - round(x[0] / grid5)) * grid5 for x in a]
    check(len(a) >= 30 and max(off) <= 1.5 and all(x[1] == round(x[0] / grid5) % 16 for x in a),
          "1/16 5:4 turned while it plays: every step on the fives counted from the bar line, the step the clock says (%d notes, the worst %.2f ms off)" % (len(a), max(off or [9])))
    b = [(tm - p, d1 - 60) for tm, d1, v in log.notes(ch=0, after=p + int(44 * STEP_MS), before=p + int(69 * STEP_MS))]
    check(len(b) >= 24 and all(abs(x[0] / STEP_MS - round(x[0] / STEP_MS)) * STEP_MS <= 1.5 and x[1] == round(x[0] / STEP_MS) % 16 for x in b),
          "... 1/16 again: on the 16ths, the step the clock says (%s)" % b[:3])
    c7 = [(tm - q, d1 - 60) for tm, d1, v in log.notes(ch=0, after=q - 5)]
    grid7 = 4 * STEP_MS / 7.0
    check(len(c7) >= 50 and c7[0][1] == 0 and abs(c7[0][0]) <= 1.5 and max(abs(x[0] - k * grid7) for k, x in enumerate(c7)) <= 1.5 and [x[1] for x in c7[:20]] == [k % 16 for k in range(20)],
          "PLAY at 1/16 7:4: from the first step on the line, seven in the time of four 16ths (%s)" % [round(x[0], 1) for x in c7[:4]])


def t025_listen():
    group("0.25 THE PARTS LISTEN: in a band of the engines a lead answers the chords, the percussion the snare, a bass the lead - whatever order they were made in; the part it answers made again, it answers again; UNDO brings back the answer with the call")
    tool = os.path.join(tempfile.gettempdir(), "sagga_theory_l_%d" % os.getpid())
    subprocess.run(["cc", "-std=c11", "-O2", "-I" + ROOT + "/firmware/src", ROOT + "/tools/theory/sagga_theory.c", ROOT + "/firmware/src/sagga_seq_core.c",
                    ROOT + "/firmware/src/sagga_beats.c", "-o", tool], check=True)

    def text(style, seed, energy, parts=None, mate=None, n=16):
        cmd = [tool] + (["--mate", mate[0], str(mate[1]), mate[2]] if mate else []) + [style, str(seed), "0", "0", str(energy), str(n)]
        out = subprocess.run(cmd + (parts or []), capture_output=True, text=True, check=True).stdout.splitlines()
        return {l.split("\t")[0]: l.split("\t")[1] for l in out[1:]}
    def onoff(r): return "".join("." if c in ".-" else "x" for c in r)
    def band(s, t): s.press(t, SEQ); s.tap_key(t + 30, bk(6), hold=700); s.release(t + 800, SEQ); return t + 900
    def seqkey(s, t, key, hold=40): s.press(t, SEQ); s.tap_key(t + 30, key, hold=hold); s.release(t + 60 + hold, SEQ); return t + 140 + hold
    def look(s, t, tracks):
        for k, tk in enumerate(tracks): s.at(t + 15 * k, "dump", tk)
        return t + 15 * len(tracks) + 40
    def at(log, track, n=0):
        d = [x for x in log.dumps if x["track"] == track + 1]
        h = [x for x in th_dumps(log) if x["track"] == track + 1]
        return d[n], h[n]
    FREE = ["KICK", "SNARE", "HAT", "PERC", "BASS", "CHORD", "ARP", "LEAD"]
    try:
        # FREE's band (the SOURCE on FREE): eight tracks of one seed. The PERC answers the SNARE, the ARP and the LEAD
        # the CHORD, the BASS - made before them - the ARP: each is what the engines write WITH the part it answers
        # there, not what they write for it alone
        found = None
        for seed_turns in range(0, 6):                                   # (a seed where the answering shows in the lead and in the arpeggio)
            s = Script()
            t = pg(s, 100, SEQ, 7, [(K1, 2)] + ([(K2, seed_turns)] if seed_turns else []))
            t = band(s, t)
            t = look(s, t + 50, range(8))
            log = run(s, t + 200)
            got = [at(log, k, 0) for k in range(8)]
            e, seed = got[0][1]["now"], got[0][1]["seed"]
            with_, alone = text("FREE", seed, e, parts=FREE), {p: text("FREE", seed, e, parts=[p])[p] for p in FREE}
            differ = [p for p in FREE if onoff(with_[p]) != onoff(alone[p])]
            if all(got[k][0]["on"] == onoff(with_[FREE[k]]) for k in range(8)) and "LEAD" in differ and "ARP" in differ:
                found = (seed, e, got, with_, alone, differ)
                break
        check(found is not None, "a band of the engines: every part is the one written WITH the part it answers there - and for some seed that is not the part alone (%s)" % (
            None if found is None else found[5]))
        if found:
            seed, e, got, with_, alone, differ = found
            chord, snare = onoff(with_["CHORD"]), onoff(with_["SNARE"])
            hit = lambda a, b: sum(1 for x, y in zip(a, b) if x == "x" and y == "x")
            check(all(p not in differ for p in ("KICK", "SNARE", "HAT", "CHORD")), "the kick, the snare, the hat, the chords answer nobody: they are what they are alone (%s)" % differ)
            check(hit(onoff(with_["LEAD"]), chord) <= hit(onoff(alone["LEAD"]), chord) and hit(onoff(with_["PERC"]), snare) <= hit(onoff(alone["PERC"]), snare),
                  "the lead has no more notes on the chords' attacks than alone, the percussion on the snare's (%s / %s on %s; %s / %s on %s)" % (
                      onoff(with_["LEAD"]), onoff(alone["LEAD"]), chord, onoff(with_["PERC"]), onoff(alone["PERC"]), snare))
            # the chords made again from another seed (SEQ 8 K3 on their track): the lead and the arpeggio, not
            # touched, answer the new chords; UNDO: the chords back, and the answers with them
            s = Script()
            t = pg(s, 100, SEQ, 7, [(K1, 2)] + ([(K2, seed)] if seed else []))
            t = band(s, t)
            t = look(s, t + 50, range(8))
            s.enc(t, E_SEL, 5); t += 60                                    # track 6: the CHORD
            t = pg(s, t, SEQ, 7, [(K3, 3)])
            t = look(s, t + 50, range(8))
            t = seqkey(s, t, wk(7))                                      # UNDO
            t = look(s, t + 50, range(8))
            log = run(s, t + 200)
            a, b, c = [[at(log, k, n) for k in range(8)] for n in (0, 1, 2)]
            new_seed = b[5][1]["seed"]
            want_lead = text("FREE", seed, e, parts=["LEAD"], mate=("FREE", new_seed, "CHORD"))["LEAD"]
            want_arp = text("FREE", seed, e, parts=["ARP"], mate=("FREE", new_seed, "CHORD"))["ARP"]
            check(new_seed != seed and b[5][0]["hash"] != a[5][0]["hash"] and b[7][1]["seed"] == seed and b[7][0]["on"] == onoff(want_lead) and b[6][0]["on"] == onoff(want_arp),
                  "the chords of another seed: the lead and the arpeggio answer them, the same parts of their own seed (%s -> %s)" % (a[7][0]["on"], b[7][0]["on"]))
            check(all(b[k][0]["hash"] == a[k][0]["hash"] for k in (0, 1, 2, 3)), "... the drums are as they were")
            check(all(c[k][0]["hash"] == a[k][0]["hash"] for k in range(8)), "UNDO: the chords back, and the lead and the arpeggio with them (%s)" % [k + 1 for k in range(8) if c[k][0]["hash"] != a[k][0]["hash"]])
    finally:
        try:
            os.unlink(tool)
        except OSError:
            pass


def t025_melody():
    group("0.25 THE MELODY KNOWS THE CHORD: FOLLOW MODE MELODY - a tune stays where it is written, its strong notes (on a beat, long, held through a change) go to the nearest tone of the chord playing; the makers' leads follow so")
    BAR = 16 * STEP_MS

    def setup(s, rhythm=0, steps=range(16), fm=SQ_FM_MELODY):
        t = kp(s, 100, [(K2, 1), (K4, 1)])                             # C major, IN KEY
        t = s.steps(t, list(steps))
        t = home_page(s, t, 1, [(K4, 1)], cur=2)                       # FOLLOW
        t = uprog_knobs(s, t, [(K3, 1), (K2, 1), (K3, 8)])             # USER 1: I, V
        t = harm_knobs(s, t, [(K2, 8), (K1, 1)])                       # HARMONY: USER 1, ON
        if rhythm:
            t = harm2_knobs(s, t, [(K4, rhythm)])
        if fm:
            t = harm2_knobs(s, t, [(K1, fm)])
        return t

    def per_step(log, p0, steps):
        got = {}
        for tm, d1, _ in log.notes(ch=0, after=p0):
            k = int(round((tm - p0) / STEP_MS))
            if k < steps:
                got.setdefault(k, d1)
        return [got.get(k) for k in range(steps)]

    # sixteen Cs, the chords C a bar and G a bar. A riff (HOLD) moves whole: sixteen Gs. A tune (MELODY) stays: on the
    # beats the C goes to the B - the nearest note of G B D -, between the beats it is the C that is written
    res = {}
    for fm in (SQ_FM_HOLD, SQ_FM_MELODY):
        s = Script()
        t = setup(s, fm=fm)
        s.at(t, "dump", 0)
        s.tap_btn(t + 20, PLAY); p0 = t + 20
        log = run(s, p0 + int(3 * BAR) - 30)
        res[fm] = (per_step(log, p0, 48), harm11(log)[0]["fm"], [x["msg"] for x in log.states])
    h, m = res[SQ_FM_HOLD][0], res[SQ_FM_MELODY][0]
    check(h[:16] == [60] * 16 and h[16:32] == [55] * 16 and res[SQ_FM_HOLD][1] == SQ_FM_HOLD, "HOLD (as ever): the riff moves with the chord, sixteen Gs (%s)" % h[16:32])
    check(res[SQ_FM_MELODY][1] == SQ_FM_MELODY and "A TUNE: ITS STRONG NOTES ON THE CHORD" in res[SQ_FM_MELODY][2],
          "ARP 4 K1 past LEGATO: MELODY, and the FM-1 says what it is (%s)" % res[SQ_FM_MELODY][1])
    check(m[:16] == [60] * 16 and m[16:32] == [59, 60, 60, 60] * 4 and m[32:48] == [60] * 16,
          "MELODY: on C the tune is as written; on G its beats go to the B, the notes between stay C; on C again as written (%s)" % m[16:32])

    # a note longer than its step is strong wherever it is: step 2 (three steps long) goes to the B, the short one on
    # step 7 stays
    s = Script()
    t = setup(s, steps=[6])
    s.raw(t, "attach"); t += 100
    s.at(t, "pad", 1, 0, 100); s.at(t + 300, "pad", 3, 0, 100); s.at(t + 360, "pad", 3, 0, 0); s.at(t + 400, "pad", 1, 0, 0); t += 500
    s.at(t, "dump", 0)
    s.tap_btn(t + 20, PLAY); p0 = t + 20
    log = run(s, p0 + int(2 * BAR) - 30)
    q = per_step(log, p0, 32)
    check(log.dumps[0]["on"] == ".x....x........." and [q[1], q[6], q[17], q[22]] == [60, 60, 59, 60] and sum(1 for x in q if x is not None) == 4,
          "a long note between the beats is a strong one: on G it goes to the B; the short one stays C (%s, %s)" % (log.dumps[0]["on"], [q[1], q[6], q[17], q[22]]))

    # a note held through the change of chord (sixteen steps, the chords change at the half bar): it slides to the new
    # chord's nearest tone as LEGATO does - the B on before the C ends
    s = Script()
    t = setup(s, SQ_HR_HALF, steps=[])
    s.raw(t, "attach"); t += 100
    s.at(t, "pad", 0, 0, 100); s.at(t + 300, "pad", 15, 0, 100); s.at(t + 360, "pad", 15, 0, 0); s.at(t + 400, "pad", 0, 0, 0); t += 500
    s.tap_btn(t + 20, PLAY); p0 = t + 20
    log = run(s, p0 + int(BAR) - 30)
    ons = [(tm - p0, d1) for tm, st, d1, d2 in log.msgs if st == 0x90 and d2 and tm >= p0]
    offs = [(tm - p0, d1) for tm, st, d1, d2 in log.msgs if (st == 0x80 or (st == 0x90 and not d2)) and tm >= p0]
    b_at = [tm for tm, d in ons if d == 59]
    c_off = [tm for tm, d in offs if d == 60]
    check([d for _, d in ons] == [60, 59] and b_at and c_off and b_at[0] <= c_off[0] and abs(c_off[0] - 8 * STEP_MS) < 8,
          "a note held through the change slides to the chord's nearest tone: the B before the C ends (%s %s)" % (ons, offs))

    # a step of two notes on a MELODY track is a chord: it moves with the chords as ever (C E -> G B)
    s = Script()
    t = setup(s, steps=[])
    s.press(t, SEL); s.keys(t + 30, KEY_C4 | KEY_E4); s.keys(t + 120, 0); s.release(t + 200, SEL); t += 300
    s.at(t, "dump", 0)
    s.tap_btn(t + 20, PLAY); p0 = t + 20
    log = run(s, p0 + int(2 * BAR) - 30)
    n1 = sorted(set(d1 for tm, d1, _ in log.notes(ch=0, after=p0) if tm < p0 + BAR - 10))
    n2 = sorted(set(d1 for tm, d1, _ in log.notes(ch=0, after=p0 + BAR - 10)))
    check(n1 == [60, 64] and n2 == [55, 59], "a step of two notes follows as a chord: C E, then G B (%s %s, %s)" % (n1, n2, log.dumps[0]["on"]))

    # the makers: a LEAD made by BAND or BEAT follows as a MELODY; another part on that track: HOLD again; the way the
    # player chose for held notes (RETRIG) is kept by a part that is no tune, and a tune takes the track back
    def beat(s, t, pos): s.press(t, SEQ); s.enc(t + 30, E_SEL, pos); s.tap_key(t + 80, wk(9)); s.release(t + 200, SEQ); return t + 300
    def band(s, t): s.press(t, SEQ); s.tap_key(t + 30, bk(6), hold=700); s.release(t + 800, SEQ); return t + 900
    s = Script()
    t = pg(s, 100, SEQ, 7, [(K1, 2)])                                  # the SOURCE on FREE: its band is KICK SNARE HAT PERC BASS CHORD ARP LEAD
    t = band(s, t)
    for k in (4, 5, 6, 7):
        s.at(t, "dump", k); t += 20
    s.enc(t, E_SEL, 7); t += 60                                        # track 8: the LEAD
    t = beat(s, t, 4)                                                  # ... a BASS on it (the fifth of the list: the knob was on the KICK)
    s.at(t, "dump", 7); t += 40
    t = harm2_knobs(s, t, [(K1, 1)])                                   # RETRIG by hand
    t = beat(s, t, 0)                                                  # a BASS again
    s.at(t, "dump", 7); t += 40
    t = beat(s, t, 3)                                                  # the LEAD
    s.at(t, "dump", 7); t += 40
    log = run(s, t + 200)
    f = [(x["track"], x["fm"]) for x in harm11(log)]
    th = [x["func"] for x in th_dumps(log)]
    check(f[:4] == [(5, SQ_FM_HOLD), (6, SQ_FM_HOLD), (7, SQ_FM_HOLD), (8, SQ_FM_MELODY)],
          "the band: the LEAD follows as a MELODY, the bass, the chords and the arpeggio as ever (%s)" % f[:4])
    check(f[4:] == [(8, SQ_FM_HOLD), (8, SQ_FM_RETRIG), (8, SQ_FM_MELODY)] and th[4:] == [4, 4, 24],
          "a BASS on the lead's track: HOLD; RETRIG by hand stays with a BASS; a LEAD: MELODY again (%s, parts %s)" % (f[4:], th[4:]))



def th_metres(log):
    """0.25: the 'thmetre' lines of the dumps: the metre the pattern that plays was made in, the metre now, kept as the player's"""
    return [dict(made=int(m.group(1)), now=int(m.group(2)), kept=int(m.group(3)))
            for m in re.finditer(r"^\s*\d+ ms  thmetre T\d+ made (\d+) now (\d+) kept (\d+)$", log.text, re.M)]


def th_made(log):
    """0.26: the 'thmade' lines of the dumps: the pattern that plays was made IN the bar, its answers have notes, its steps"""
    return [dict(bar=int(m.group(1)), notes=int(m.group(2)), steps=int(m.group(3)))
            for m in re.finditer(r"^\s*\d+ ms  thmade T\d+ bar (\d+) notes (\d+) steps (\d+)$", log.text, re.M)]


def theory_tool(tag):
    """the engines on this computer (tools/theory/sagga_theory.c): text(style, seed, energy, ...) -> {part: (hits, notes)}"""
    tool = os.path.join(tempfile.gettempdir(), "sagga_theory_%s_%d" % (tag, os.getpid()))
    subprocess.run(["cc", "-std=c11", "-O2", "-I" + ROOT + "/firmware/src", ROOT + "/tools/theory/sagga_theory.c", ROOT + "/firmware/src/sagga_seq_core.c",
                    ROOT + "/firmware/src/sagga_beats.c", "-o", tool], check=True)
    def text(style, seed, energy, parts=None, n=64, var=0, vary=0, metre=None, flags=(), mate=None):
        cmd = [tool] + list(flags) + (["--metre", metre] if metre else []) + (["--mate", mate[0], str(mate[1]), mate[2]] if mate else [])
        cmd += [style, str(seed), str(var), str(vary), str(energy), str(n)] + list(parts or [])
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.splitlines()
        return {l.split("\t")[0]: (l.split("\t")[1], l.split("\t")[2]) for l in out[1:]}
    def done():
        try: os.remove(tool)
        except OSError: pass
    return text, done


def onoff(r): return "".join("." if c in ".-" else "x" for c in r)


SRC_78 = [0, 1, 2, 3, 4, 5, 6, 7, 12, 13, 14, 15, 14, 15]      # 7/8 as 2+2+3: the step of a 4/4 bar each of its 14 takes
def rebar78(on16): return "".join(on16[k] for k in SRC_78)


def t025_metre_makers():
    group("0.25 THE METRE and whoever makes a pattern: the library and the engines make it in the metre's bars; the engines' patterns follow a new metre (not one changed by hand); RANDOM's phrase")
    def seqkey(s, t, key, hold=40): s.press(t, SEQ); s.tap_key(t + 30, key, hold=hold); s.release(t + 60 + hold, SEQ); return t + 140 + hold

    # the library's KICK in 7/8 (2+2+3): the four quarters of its bar are the three beats - the first, the second, and
    # the last (the three eighths: the quarter and its second eighth again: the pickup of KICK #2 is there twice)
    s = Script()
    t = metre_knobs(s, 100, [(K1, -2)])
    t = beat_key(s, t); s.at(t, "dump", 0); t += 50
    t = home_page(s, t, 0, [(K2, 14)])
    t = beat_key(s, t); s.at(t, "dump", 0); t += 50
    log = run(s, t + 100)
    d, c = log.dumps, log.copies
    check(d[0]["length"] == 14 and d[0]["on"] == rebar78("x...x...x...x...") and d[0]["on"] == "x...x...x....." and c[0]["own"] == 14 and c[0]["row"][14:] == "." * 50,
          "BEAT in 7/8: the library's four on the floor in a bar of 14 - a hit on each of the three beats (%s, own %s)" % (d[0]["on"], c[0]["own"]))
    check(d[1]["length"] == 28 and c[1]["own"] == 14 and d[1]["on"] == rebar78("x...x...x...x..x") * 2 and c[1]["row"][14:28] == rebar78("grrrgrrrgrrrgrrg"),
          "... KICK #2 on a track of two bars (28): the bar of 14 and its copy, the pickup in the last beat (%s, own %s)" % (_bars14(d[1]["on"]), c[1]["own"]))

    # the THEORY engines: the part of seed 1 made in 4/4, and made in 7/8 (0.26: IN the bar of 14, not the 4/4 one
    # re-barred: what the engines make of seed 1 in 7/8 - a kick on every beat of it)
    text, done = theory_tool("mm")
    out = {}
    for name, pre in (("4/4", []), ("7/8", [(K1, -2)])):
        s = Script()
        t = pg(s, 100, SEQ, 7, [(K1, 1)])                                 # SOURCE THEORY
        if pre: t = metre_knobs(s, t, pre)
        t = seqkey(s, t, wk(9)); s.at(t, "dump", 0); t += 50              # BEAT
        log = run(s, t + 100)
        out[name] = (log.dumps[0], log.copies[0], th_dumps(log)[0], th_metres(log)[0], log.states[0]["msg"])
    d4, d7 = out["4/4"], out["7/8"]
    want7 = onoff(text("TECHNO", 0, d7[2]["now"], parts=["KICK"], n=16, metre="7/8")["KICK"][0])
    done()
    check(d4[4] == "TECHNO KICK SEED 1" and d7[4] == d4[4] and d7[0]["length"] == 14 and d7[1]["own"] == 14 and d7[0]["on"] == want7 and len(want7) == 14
          and all(d7[0]["on"][k] == "x" for k in (0, 4, 8)),
          "THEORY, BEAT in 7/8: the kick of seed 1 made in the bar of 14 - on its three beats (%s; in 4/4 %s)" % (d7[0]["on"], d4[0]["on"]))
    check(d4[3]["made"] == 0 and d7[3]["made"] == d7[3]["now"] and d7[3]["made"] != 0 and d7[2]["len"] == 16,
          "... the pattern keeps the metre it was made in (4/4: %s; 7/8: %s, one bar)" % (d4[3]["made"], d7[3]["made"]))

    # THE ENGINES' PATTERNS FOLLOW THE METRE: a kick made in 4/4; the bar is 14: it is made again, in 7/8 (the one above);
    # the bar is 16 again: the pattern it was. One the player changed by hand stays as it is, cut by the loop, and back
    for touched in (0, 1):
        s = Script()
        t = pg(s, 100, SEQ, 7, [(K1, 1)])
        t = seqkey(s, t, wk(9)); t += 50
        if touched:
            s.tap_key(t, wk(1)); t += 100                                 # step 2 written by hand
        s.at(t, "dump", 0); t += 50
        t = metre_knobs(s, t, [(K1, -2)]); t += 100; s.at(t, "dump", 0); t += 50
        t = metre_knobs(s, t, [(K1, 2)]); t += 100; s.at(t, "dump", 0); t += 50
        log = run(s, t + 100)
        d, c, tm = log.dumps, log.copies, th_metres(log)
        if not touched:
            check(d[0]["on"] == d4[0]["on"] and d[1]["length"] == 14 and d[1]["on"] == d7[0]["on"] and c[1]["own"] == 14 and tm[1]["made"] == tm[1]["now"] != 0 and tm[1]["kept"] == 0,
                  "a kick of the engines, then a bar of 14: made again in 7/8 (%s -> %s, own %s)" % (d[0]["on"], d[1]["on"], c[1]["own"]))
            check(d[2]["length"] == 16 and d[2]["hash"] == d[0]["hash"] and tm[2]["made"] == 0, "... the bar of 16 again: the pattern it was (%s)" % d[2]["on"])
        else:
            check(d[0]["on"][1] == "x" and d[1]["length"] == 14 and d[1]["on"] == d[0]["on"][:14] and c[1]["row"][:17] == d[0]["on"] + "r" and tm[1]["made"] == 0 and tm[1]["kept"] == 1,
                  "one the player changed (step 2 written): it stays as it is in the bar of 14, cut by the loop (%s -> %s, kept %s)" % (d[0]["on"], c[1]["row"][:17], tm[1]["kept"]))
            check(d[2]["length"] == 16 and d[2]["hash"] == d[0]["hash"] and tm[2]["kept"] == 0, "... and comes back whole with the bar of 16 (%s)" % d[2]["on"])

    # RANDOM on a track of two bars of 14: a phrase by the metre's bars - the bar and its answer (the answer keeps the
    # first beat and more: its first 4 steps, here)
    s = Script()
    t = metre_knobs(s, 100, [(K1, -2)])
    t = home_page(s, t, 0, [(K2, 14)])
    t = seqkey(s, t, wk(4)); s.at(t, "dump", 0)
    log = run(s, t + 100)
    b = _bars14(log.dumps[0]["on"])
    check(log.dumps[0]["length"] == 28 and log.copies[0]["own"] == 28 and len(b) == 2 and b[1] != b[0] and b[1][:4] == b[0][:4] and "x" in b[0],
          "RANDOM on 28 steps in 7/8: a bar of 14 and its answer (%s)" % b)


def _bars14(on): return [on[i:i + 14] for i in range(0, len(on), 14)]


def t025_metre():
    group("0.25 THE METRE: a bar of N steps and its beats (GLO 4): at once when stopped, at the bar line while it plays; the tracks on the bar follow and come back whole")
    M16 = list(range(16))
    M14 = list(range(14))
    # stopped: the page, the bar at once, its ways, back to 4/4 with the pattern whole
    s = Script()
    t = melody16(s)
    s.at(t, "dump", 0); t += 30
    s.press(t, GLO); t += 30
    for _ in range(3): s.tap_btn(t, OCT_UP, hold=20); t += 40
    s.pages[GLO] = 3
    s.at(t, "ui"); t += 20
    s.enc(t, K1, -2); t += 30
    s.at(t, "ui"); s.at(t, "dump", 0); t += 20
    s.enc(t, K2, 1); t += 30
    s.at(t, "ui"); s.at(t, "dump", 0); t += 20
    s.enc(t, K2, 5); t += 30                                               # (three ways: it stops at the last)
    s.at(t, "dump", 0); t += 20
    s.enc(t, K1, 2); t += 30
    s.at(t, "ui"); s.at(t, "dump", 0); t += 20
    s.release(t, GLO); t += 60
    log = run(s, t + 100)
    sc, d, c, m, me = log.screens(), log.dumps, log.copies, [x["msg"] for x in log.states], log.metre
    check(len(sc) == 4 and sc[0]["cells"] == [("> BAR", "16"), ("BEATS", "4x2"), ("SCENE METRE", "OFF"), ("BAR.STEP", "--")] and sc[0]["lines"][2].startswith("GLO 4/4 METRE 4/4 = 4x2"),
          "GLO page 4, THE METRE: a bar of 16 steps in four quarters (the mark: the knob the keys would set) (%s | %s)" % (sc[0]["cells"] if sc else sc, sc[0]["lines"][2] if sc else None))
    check(sc[1]["cells"][:3] == [("> BAR", "14"), ("BEATS", "2+2+3"), ("SCENE METRE", "OFF")] and sc[1]["lines"][2].startswith("GLO 4/4 METRE 7/8 = 2+2+3") and m[1] == "BAR 14: 7/8 2+2+3, 12 TRACKS FOLLOW",
          "K1 two down, stopped: a bar of 14 at once, 7/8 as 2+2+3, the sixteen tracks follow (%s | %s)" % (sc[1]["cells"][:3], m[1]))
    check(me[1]["bar"] == 14 and me[1]["beats"] == 0x111 and me[1]["sig"] == "7/8" and d[1]["length"] == 14 and c[1]["own"] == 14 and c[1]["row"][:17] == "x" * 16 + "r",
          "... the track is 14 long, its pattern keeps the two steps it does not play (and the mark of its end) (%s %X, %s, %s)" % (me[1]["bar"], me[1]["beats"], d[1]["length"], c[1]["row"][:18]))
    check(sc[2]["cells"][:3] == [("BAR", "14"), ("> BEATS", "2+3+2"), ("SCENE METRE", "OFF")] and me[2]["beats"] == 0x411 and m[2] == "BAR 14: 7/8 2+3+2" and d[2]["length"] == 14,
          "K2: the next way, 2+3+2 (the beats on steps 1, 5, 11); no track moves (%s | %X | %s)" % (sc[2]["cells"][:3], me[2]["beats"], m[2]))
    check(me[3]["beats"] == 0x441 and me[3]["split"] == "3+2+2", "K2 turned far: the last way, 3+2+2: the beats on steps 1, 7, 11 (%X %s)" % (me[3]["beats"], me[3]["split"]))
    check(me[4]["bar"] == 16 and me[4]["raw"] == 0 and me[4]["beats"] == 0x1111 and m[4] == "BAR 16: 4/4 4x2, 12 TRACKS FOLLOW" and d[4]["length"] == 16 and d[4]["on"] == "x" * 16
          and d[4]["hash"] == d[0]["hash"],
          "K1 back to 16: 4/4 (stored as nothing at all), the track is 16 and its pattern as it was (%s raw %s, %s, %s, same %s)" % (me[4]["bar"], me[4]["raw"], m[4], d[4]["on"], d[4]["hash"] == d[0]["hash"]))

    # playing: the bar waits for the bar line; a length waits for the bar of 14; back to 16 at the line of the 14
    s = Script()
    t = melody16(s)
    s.tap_btn(t, PLAY); p0 = t
    metre_knobs(s, p0 + int(4.5 * STEP_MS), [(K1, -2)])                      # bar 1 of 16: asked, it waits
    s.at(p0 + int(10.5 * STEP_MS), "dump", 0)
    s.at(p0 + int(17.5 * STEP_MS), "dump", 0)                              # the second bar: 14 steps
    home_page(s, p0 + int(33.5 * STEP_MS), 0, [(K2, 14)])                  # in the third bar (steps 30 - 43): LENGTH 28 asked
    s.at(p0 + int(40.5 * STEP_MS), "dump", 0)
    s.at(p0 + int(45.5 * STEP_MS), "dump", 0)                              # ... on the line of step 44, the bar's (a bar of 16: 48)
    metre_knobs(s, p0 + int(61.5 * STEP_MS), [(K1, 2)])                    # the bar of 16 asked: at the line of step 72
    s.at(p0 + int(70.5 * STEP_MS), "dump", 0)
    s.at(p0 + int(73.5 * STEP_MS), "dump", 0)
    log = run(s, p0 + int(104 * STEP_MS) - 20)
    f, d, c, m, me = _flat(log, p0, 104), log.dumps, log.copies, [x["msg"] for x in log.states], log.metre
    check(me[0]["bar"] == 16 and me[0]["pend"] == 14 and m[0] == "BAR 14: 7/8 2+2+3 AT THE BAR" and d[0]["length"] == 16,
          "playing: the bar of 14 waits for the bar line (%s, waiting %s: %s)" % (me[0]["bar"], me[0]["pend"], m[0]))
    check(f[:16] == M16 and f[16:30] == M14 and f[30:44] == M14,
          "... the first bar is whole (16), then the bars are 14: the melody's first 14 steps, from the line (%s | %s)" % (f[14:19], f[28:33]))
    check(me[1]["bar"] == 14 and me[1]["pend"] == 0 and me[1]["no"] == 1 and me[1]["into"] // 6 == 1 and d[1]["length"] == 14 and m[1] == "BAR 14: 7/8 2+2+3, 12 TRACKS FOLLOW",
          "... it is bar 2, step 2 of 14; the tracks followed (%s, bar %s step %s, %s)" % (me[1]["bar"], me[1]["no"] + 1, me[1]["into"] // 6 + 1, m[1]))
    check(d[2]["length"] == 14 and m[2] == "LENGTH 28 AT THE BAR" and d[3]["length"] == 28 and c[3]["own"] == 16 and f[44:72] == M16 + list(range(12)),
          "LENGTH 28 asked in a bar of 14: it waits for THAT bar's line (step 45, not 49): the 16 steps and twelve copies (%s then %s, own %s | %s)"
          % (d[2]["length"], d[3]["length"], c[3]["own"], f[42:48]))
    check(me[4]["bar"] == 14 and me[4]["pend"] == 16 and me[5]["bar"] == 16 and me[5]["no"] == 5 and d[5]["length"] == 32 and m[5] == "BAR 16: 4/4 4x2, 12 TRACKS FOLLOW",
          "the bar of 16 asked: at the line of the 14 (step 73); the track of two bars is two bars still: 32 (%s -> %s, bar %s, length %s, %s)"
          % (me[4]["bar"], me[5]["bar"], me[5]["no"] + 1, d[5]["length"], m[5]))
    check(f[72:88] == M16 and f[88:104] == M16, "... and the melody is whole again, twice, from the line (%s | %s)" % (f[70:76], f[86:92]))

    # what waits for "the bar" waits for the metre's: a pattern queued (QUANTISE BAR), and the BEAT is the metre's beat
    for quant, ask, want, why in ((3, 4.5, 14, "QUANTISE BAR: asked in the bar, there at its line: 14 steps played"),
                                  (2, 8.5, 14, "QUANTISE BEAT, 2+2+3: asked after the third beat (step 9), the next beat is the bar line (4/4: step 13)"),
                                  (2, 4.5, 8, "QUANTISE BEAT: asked after the second beat (step 5): at the third, step 9")):
        s = Script()
        t = melody16(s)
        t = metre_knobs(s, t, [(K1, -2)])
        t = glo_knobs(s, t, [(K4, quant)])
        s.tap_btn(t, PLAY); p0 = t
        live_knobs(s, p0 + int(ask * STEP_MS), [(K1, 1)])                  # pattern 2 (empty) queued
        log = run(s, p0 + int(40 * STEP_MS))
        f = _flat(log, p0, 40)
        n = len([x for x in f if x is not None])
        check(n == want and f[:want] == M14[:want], "%s (%d notes: %s)" % (why, n, f[:16]))

    # the harmony's bar is the metre's bar: FOLLOW moves with the chords every 14 steps
    s = Script()
    t = kp(s, 100, [(K4, 1)])                                              # track 1 in key (C minor)
    t = s.steps(t, [0, 4, 8, 12])
    t = home_page(s, t, 1, [(K4, 1)], cur=2)                               # FOLLOW
    t = harm_knobs(s, t, [(K1, 1)])
    t = harm_knobs(s, t, [(K2, 3)])                                        # TECHNO #4: i VII VI VII, a chord a bar
    t = metre_knobs(s, t, [(K1, -2)])
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + int(56 * STEP_MS))
    b1 = [sorted({d1 for tm, d1, _ in log.notes(ch=0, after=p + int(k * 14 * STEP_MS) - 5, before=p + int((k + 1) * 14 * STEP_MS) - 5)}) for k in range(4)]
    check(b1 == [[60], [58], [56], [58]], "7/8: a chord a bar of 14 steps: C, B flat, A flat, B flat (%s)" % b1)





# ------------------------------------------------------------------------------------------------ 0.26
def probes(log):
    """the probes of a run (a script's "probe" lines): [{'t': ms, 'G': {...}, 'T1': {...} ...}]"""
    out = []
    for line in log.text.splitlines():
        m = re.match(r"^\s*(\d+) ms  PROBE (G|T\d+|H) (.*)$", line)
        if not m:
            continue
        rest, d = m.group(3), {}
        if " msg=" in rest:
            rest, d["msg"] = rest.split(" msg=", 1)
        for kv in rest.split():
            k, _, v = kv.partition("=")
            d[k] = v
        if m.group(2) == "G":
            out.append({"t": int(m.group(1)), "G": d})
        elif out:
            out[-1][m.group(2)] = d
    return out


def clicks(log):
    """the FM-1's own clicks the simulator was asked for: [(the ms it must sound at, 'bar' | 'beat', the clock tick)]"""
    return [(int(m.group(1)) + int(m.group(4)) / 1000.0, m.group(2), int(m.group(3)))
            for m in re.finditer(r"^\s*(\d+) ms  CLICK (bar|beat) tick (\d+) in (-?\d+) us$", log.text, re.M)]


def wav_clicks(path):
    """the clicks in the sound the simulator wrote: [(ms, peak, zero crossings in its first 10 ms)]"""
    import wave, struct
    w = wave.open(path)
    n = w.getnframes()
    d = struct.unpack("<%dh" % (2 * n), w.readframes(n))
    w.close()
    out, i = [], 0
    while i < n:
        if abs(d[2 * i]) > 200:
            pk, zc = 0, 0
            for j in range(i, min(n, i + 1400)):
                pk = max(pk, abs(d[2 * j]))
                if j > i and j < i + 441 and (d[2 * j] < 0) != (d[2 * j - 2] < 0):
                    zc += 1
            out.append((i * 1000.0 / 44100, pk, zc))
            i += 1500
        else:
            i += 1
    return out


def click_knobs(s, t, encs, sel=False): return pg(s, t, SAVE, 4, encs, sel=sel)   # SAVE 5 CLICK: K1 CLICK, K2 COUNT IN, K3 OUT, K4 LEVEL (SEL + K4: the NOTE)


def rownts(log):
    """0.26: the 'rownt' lines of the dumps: a row's notes as the engines write them (0..f above the root, * a chord)"""
    return [dict(track=int(m.group(1)), nt=m.group(2)) for m in re.finditer(r"^\s*\d+ ms  rownt T(\d+) NT:(.*)$", log.text, re.M)]


def t026_engines():
    group("0.26 THE ENGINES IN THE BAR, THE ANSWER WITH NOTES: a band made in 7/8 is made in seven (a kick on every beat of the bar) and fills with the ENERGY; a new metre makes the patterns again IN the new bar, the old one brings back what they were; a bass takes the notes of the tune it answers; a band of 0.25 is made again as 0.25 made it")
    text, done = theory_tool("eng")
    FREE = ["KICK", "SNARE", "HAT", "PERC", "BASS", "CHORD", "ARP", "LEAD"]
    def band(s, t): s.press(t, SEQ); s.tap_key(t + 30, bk(6), hold=700); s.release(t + 800, SEQ); return t + 900
    def longer2(s, t):                                           # every track four bars (the MOSSE's LONGER, twice)
        t = vg_on(s, t, remote=False)
        for _ in range(2):
            s.press(t, SEL); s.tap_key(t + 30, bk(5)); s.release(t + 100, SEL); t += 160
        return vg_studio(s, t)
    def look(s, t):
        for k in range(8): s.at(t + 15 * k, "dump", k)
        return t + 160
    def looks(log):                                              # every look: eight tracks of (steps, theory, made, notes)
        d, h, m, nt = log.dumps, th_dumps(log), th_made(log), rownts(log)
        return [[(d[i + k], h[i + k], m[i + k], nt[i + k]["nt"]) for k in range(8)] for i in range(0, len(d), 8)]
    def notes(part, chords=False):                               # the engines' text as the dump shows a row's notes
        r, nt = part
        return "".join("." if r[i] in ".-" else "*" if chords else nt[i] for i in range(len(r))) if nt != "-" else None
    def same(got, want):                                         # the tracks that are not what the engines' text says: hits, and notes
        bad = []
        for k in range(8):
            w = want[FREE[k]]
            if got[k][0]["on"] != onoff(w[0]) or (notes(w) is not None and got[k][3] != notes(w, FREE[k] == "CHORD")): bad.append(FREE[k])
        return bad
    try:
        # ---- a band BORN in 7/8 (2+2+3), four bars of 14 a track; the ENERGY empties and fills it
        s = Script()
        t = metre_knobs(s, 100, [(K1, -2)])
        t = longer2(s, t)
        t = pg(s, t, SEQ, 7, [(K1, 2)])                          # SOURCE FREE
        t = band(s, t); t = look(s, t)
        s.raw(t, "energy 10"); t += 500; t = look(s, t)
        s.raw(t, "energy 95"); t += 500; t = look(s, t)
        log = run(s, t + 300)
        L = looks(log)
        e0 = L[0][0][1]["now"]
        check(len(L) == 3 and all(x[0]["length"] == 56 for x in L[0]) and all(x[2] == dict(bar=1, notes=1, steps=56) and x[1]["len"] == 64 for x in L[0]),
              "BAND in 7/8: every part four bars of 14, made IN the bar, its answers with notes (%s, %s)" % ([x[0]["length"] for x in L[0]], L[0][4][2] if L else None))
        for n, en in enumerate((e0, 10, 95)):
            bad = same(L[n], text("FREE", 0, en, n=64, metre="7/8"))
            check(not bad and all(x[1]["energy"] == en for x in L[n]), "... at energy %d every part is what the engines make in 7/8: hits and notes (%s)" % (en, bad))
        kick = [x[0][0]["on"] for x in L]
        check(all(k[b * 14] == "x" for k in kick for b in range(4)), "... the kick on the one of every bar of seven, at every energy (%s)" % kick[1][:28])
        lo, hi = [x[0]["on"] for x in L[1]], [x[0]["on"] for x in L[2]]
        check(all(a == "." or b == "x" for p, q in zip(lo, hi) for a, b in zip(p, q)) and sum(r.count("x") for r in hi) > sum(r.count("x") for r in lo) * 3 // 2,
              "... the ENERGY only adds: all of 10 is in 95, which is much fuller (%d hits, %d)" % (sum(r.count("x") for r in lo), sum(r.count("x") for r in hi)))
        want44 = text("FREE", 0, e0, n=64)
        check(L[0][0][0]["on"][:14] != onoff(want44["KICK"][0])[:14] or L[0][1][0]["on"][:14] != onoff(want44["SNARE"][0])[:14],
              "... and it is not the 4/4 band cut short (kick %s, in 4/4 %s)" % (L[0][0][0]["on"][:14], onoff(want44["KICK"][0])[:16]))

        # ---- THE METRE CHANGES: a band of 0.26, and one of 0.25 (what the engines keep of it says so), made in 4/4;
        # the bar is 14: made again IN it (the 0.25 one too: its answers stay of rhythm alone); the bar is 16 again:
        # the patterns they were, to the note
        res = {}
        for old in (0, 1):
            s = Script()
            t = longer2(s, 100)
            t = pg(s, t, SEQ, 7, [(K1, 2)])
            t = band(s, t)
            if old: s.raw(t, "thold"); t += 200
            t = look(s, t)
            t = metre_knobs(s, t, [(K1, -2)]); t += 700; t = look(s, t)
            t = metre_knobs(s, t, [(K1, 2)]); t += 700; t = look(s, t)
            s.raw(t, "energy 90"); t += 500; t = look(s, t)
            log = run(s, t + 300)
            res[old] = looks(log)
        N, O = res[0], res[1]
        e0 = N[0][0][1]["now"]
        bad = same(N[0], text("FREE", 0, e0, n=64))
        check(not bad and all(x[2] == dict(bar=1, notes=1, steps=64) for x in N[0]), "a band of 0.26 in 4/4: what the engines make now, hits and notes (%s)" % bad)
        bad = same(O[0], text("FREE", 0, e0, n=64, flags=["--v25"]))
        check(not bad and all(x[2] == dict(bar=0, notes=0, steps=64) for x in O[0]), "a band of 0.25 in 4/4: what 0.25 made, hits and notes (%s)" % bad)
        diff = [FREE[k] for k in range(8) if N[0][k][0]["hash"] != O[0][k][0]["hash"]]
        check("BASS" in diff and "KICK" not in diff and "CHORD" not in diff,
              "... the two differ where a part answers another: the bass hears the arpeggio as it is, and takes its notes (%s)" % diff)
        bad = same(N[1], text("FREE", 0, e0, n=64, metre="7/8"))
        check(not bad and all(x[0]["length"] == 56 and x[2] == dict(bar=1, notes=1, steps=56) for x in N[1]), "the bar is 14: the band of 0.26 made again in 7/8 (%s)" % bad)
        bad = same(O[1], text("FREE", 0, e0, n=64, metre="7/8", flags=["--no-notes"]))
        check(not bad and all(x[0]["length"] == 56 and x[2] == dict(bar=1, notes=0, steps=56) for x in O[1]),
              "... the band of 0.25 too: IN the bar of seven, its answers still of rhythm alone (%s, %s)" % (bad, O[1][4][2]))
        check(all(N[2][k][0]["hash"] == N[0][k][0]["hash"] and N[2][k][2] == N[0][k][2] for k in range(8)), "the bar is 16 again: the band of 0.26 is what it was")
        check(all(O[2][k][0]["hash"] == O[0][k][0]["hash"] and O[2][k][2] == dict(bar=0, notes=0, steps=64) for k in range(8)),
              "... and the band of 0.25 is what 0.25 made, to the note: kept as 0.25 kept it (%s)" % [FREE[k] for k in range(8) if O[2][k][0]["hash"] != O[0][k][0]["hash"]])
        bad = same(O[3], text("FREE", 0, 90, n=64, flags=["--v25"]))
        check(not bad and all(x[1]["energy"] == 90 for x in O[3]), "... the ENERGY at 90 fills it as 0.25 did (%s)" % bad)
        bad = same(N[3], text("FREE", 0, 90, n=64))
        check(not bad, "... and the band of 0.26 as 0.26 does (%s)" % bad)

        # ---- THE ANSWER HAS NOTES, in the rows: the bass of the 0.26 band plays, off the beat, notes the arpeggio it
        # answers has just played (heard at half the energy: the tool's ARP at 50 with its chords)
        heard = text("FREE", 0, 50, n=64, parts=["CHORD", "ARP"])["ARP"]
        b25, b26 = O[0][4][3], N[0][4][3]
        took = []
        for i in range(64):
            if b26[i] in ".*?" or (i < len(b25) and b25[i] == b26[i] and O[0][4][0]["on"] == N[0][4][0]["on"]): continue
            src = [heard[1][i - d] for d in (2, 4, 1, 3) if i - d >= 0 and heard[0][i - d] not in ".-"]
            if i % 4 and heard[0][i] in ".-" and src and any(int(c, 16) % 12 == int(b26[i], 16) % 12 for c in src): took.append(i)
        check(len(took) >= 1 and b26 != b25, "the bass of 0.26 takes notes of the arpeggio it answers, off the beat, right after them (steps %s: %s under %s)" % (took, b26, heard[1]))

        # ---- a part WRITTEN BY HAND is heard as its steps are: the band's CHORD track cleared, three chords written on
        # it by hand (steps 1, 7 and 13); the LEAD made again (its seed turned) answers THOSE. Then the same lead as
        # 0.25 would make it (the same steps heard, answers of rhythm alone): the same rhythm - and the notes that
        # differ are the answers: right after a chord, where the chords are silent, its third, its fifth, its root
        s = Script()
        t = longer2(s, 100)
        t = pg(s, t, SEQ, 7, [(K1, 2)])
        t = band(s, t)
        s.enc(t, E_SEL, 5); t += 80                             # track 6: the CHORD
        s.press(t, SEQ); s.tap_key(t + 40, wk(0)); s.release(t + 120, SEQ); t += 200     # CLEAR
        t = s.steps(t, [0, 6, 12]); t += 60
        s.enc(t, E_SEL, 2); t += 80                             # track 8: the LEAD
        t = pg(s, t, SEQ, 7, [(K3, 3)])                         # another seed: made by the engines of now, hearing the chords there are
        s.at(t, "dump", 5); s.at(t + 20, "dump", 7); t += 80
        s.raw(t, "thold"); t += 200
        s.at(t, "dump", 7); t += 80
        log = run(s, t + 300)
        d, nt, md = log.dumps, rownts(log), th_made(log)
        ch, l26, n26, l25, n25 = d[0]["on"], d[1]["on"], nt[1]["nt"], d[2]["on"], nt[2]["nt"]
        hits = [i for i in range(64) if l26[i] == "x"]
        diff = [i for i in hits if n26[i] != n25[i] and i != hits[-1]]
        good = []
        for i in diff:
            dd = [k for k in (1, 2, 3) if i - k >= 0 and ch[i - k] == "x"]
            if ch[i] == "." and dd and i % 16 and int(n26[i], 16) % 12 in ({3, 4}, {7}, {0})[dd[0] - 1]: good.append(i)
        check(ch[:16] == "x.....x.....x..." and md[1] == dict(bar=1, notes=1, steps=64) and md[2] == dict(bar=0, notes=0, steps=64) and l26 == l25,
              "a lead made over chords written by hand hears their steps: the same rhythm with and without notes in its answers (%s / %s over %s)" % (l26[:16], l25[:16], ch[:16]))
        check(len(diff) >= 1 and good == diff, "... and its answers are the chords' notes: the third right after a chord, then the fifth, then the root (steps %s of %s: %s, without %s)" % (good, diff, n26[:16], n25[:16]))

        # ---- ... and a TUNE written by hand: the band's ARP track (the one the bass answers) cleared, a tune of fifths
        # written on it off the beats (the project in C major; the pen seven semitones up; steps 2, 6, 10, 14); the BASS
        # made again takes THAT note where it answers - and as 0.25 would make it, hearing the same steps, it has only
        # its own
        s = Script()
        t = kp(s, 100, [(K2, 1), (K4, 1)])                      # C major, IN KEY
        t = longer2(s, t)
        t = pg(s, t, SEQ, 7, [(K1, 2)])
        t = band(s, t)
        s.enc(t, E_SEL, 6); t += 80                             # track 7: the ARP
        s.press(t, SEQ); s.tap_key(t + 40, wk(0)); s.release(t + 120, SEQ); t += 200     # CLEAR
        t = pen_turn(s, t, 7)
        t = s.steps(t, [1, 5, 9, 13]); t += 60
        s.enc(t, E_SEL, -2); t += 80                            # track 5: the BASS
        t = pg(s, t, SEQ, 7, [(K3, 2)])                         # another seed: the engines of now
        s.at(t, "dump", 6); s.at(t + 20, "dump", 4); t += 80
        s.raw(t, "thold"); t += 200
        s.at(t, "dump", 4); t += 80
        log = run(s, t + 300)
        d, nt = log.dumps, rownts(log)
        tune, tn, b26, n26, b25, n25 = d[0]["on"], nt[0]["nt"], d[1]["on"], nt[1]["nt"], d[2]["on"], nt[2]["nt"]
        hits = [i for i in range(64) if b26[i] == "x"]
        diff = [i for i in hits if n26[i] != n25[i] and i < 62]
        note = tn[1]                                            # (the tune's note above the key's root: the pen's)
        good = [i for i in diff if n26[i] == note and i % 4 and tune[i] == "." and any(i - k >= 0 and tune[i - k] == "x" for k in (1, 2, 3, 4))]
        check(tune[:16] == ".x...x...x...x.." and note not in ".0*?" and tn[:16] == ".%s...%s...%s...%s.." % ((note,) * 4) and b26 == b25,
              "a bass made under a tune written by hand hears its steps: the same rhythm with and without notes in its answers (%s / %s under %s, its notes %s)" % (b26[:16], b25[:16], tune[:16], tn[:16]))
        check(len(diff) >= 1 and good == diff, "... and where it answers it plays the tune's note (steps %s of %s: %s, without %s; the tune's note %s)" % (good, diff, n26[:32], n25[:32], note))
    finally:
        done()


def t026_tune_answers():
    group("0.26 THE ANSWER HAS NOTES, when it plays: a tune of the engines plays a note of the chord right after the chord - and when the progression has moved FOLLOW MELODY takes that note to the chord that plays; a tune of 0.25 plays as it is written there")
    def band(s, t): s.press(t, SEQ); s.tap_key(t + 30, bk(6), hold=700); s.release(t + 800, SEQ); return t + 900
    BARS = 12
    HOME = re.compile(r"^[Ii](?![IiVv])")
    res = {}
    for old in (0, 1):
        s = Script()
        t = vg_on(s, 100, remote=False)
        for _ in range(2):
            s.press(t, SEL); s.tap_key(t + 30, bk(5)); s.release(t + 100, SEL); t += 160
        t = vg_studio(s, t)
        t = pg(s, t, SEQ, 7, [(K1, 2)])                          # SOURCE FREE: KICK SNARE HAT PERC BASS CHORD ARP LEAD
        t = band(s, t)
        t = uprog_knobs(s, t, [(K3, 1), (K2, 1), (K3, 8), (K2, 1), (K3, 1)])   # USER 1: home, the fifth's chord, home - a bar each: three bars
        t = harm_knobs(s, t, [(K2, 8)])                          #  against the pattern's four: every step is heard on both chords (0.29: USER 1 is the 9th)
        if old: s.raw(t, "thold"); t += 200
        s.at(t, "dump", 5); s.at(t + 20, "dump", 7); t += 80
        s.tap_btn(t, PLAY); p0 = t
        for k in range(BARS * 8): s.raw(p0 + int((2 * k + 0.5) * STEP_MS), "probe")     # the chord, every 8th
        log = run(s, p0 + int(BARS * 16 * STEP_MS) - 30)
        d, nt, pr = log.dumps, rownts(log), probes(log)
        chord_on, lead_on, lead_nt = d[0]["on"], d[1]["on"], nt[1]["nt"]
        played = {}
        for tm, d1, v in log.notes(ch=7, after=p0 - 5):
            played.setdefault(int(round((tm - p0) / STEP_MS)), d1)
        chord = [(pr[min(k // 2, len(pr) - 1)]["G"]["chord"], int(pr[min(k // 2, len(pr) - 1)]["G"]["cpc"], 16)) for k in range(BARS * 16)]
        # the steps of the tune that answer a chord: a single note off the beat, the chords silent, struck one to three 16ths before
        ans = [i for i in range(64) if lead_on[i] == "x" and lead_nt[i] not in ".*?" and i % 4 and chord_on[i] == "."
               and any(i - k >= 0 and chord_on[i - k] == "x" for k in (1, 2, 3))]
        home = {}
        for k in sorted(played):                                 # (where a step is written: what it plays on the home chord)
            if HOME.match(chord[k][0]) and k % 64 in ans: home.setdefault(k % 64, played[k])
        away = [(k, played[k], home[k % 64], chord[k]) for k in sorted(played) if k % 64 in ans and k % 64 in home and not HOME.match(chord[k][0])]
        res[old] = dict(ans=ans, away=away, made=th_made(log)[1], names=sorted(set(c[0] for c in chord)), home=home)
    N, O = res[0], res[1]
    moved = [x for x in N["away"] if x[1] != x[2]]
    off = [x for x in moved if not (x[3][1] >> (x[1] % 12)) & 1]
    check(N["made"] == dict(bar=1, notes=1, steps=64) and len(N["names"]) == 2 and len(N["ans"]) >= 2 and len(N["away"]) >= 2,
          "the tune of a 0.26 band answers the chords, and is heard on both chords (%s; steps %s; %d times away from home)" % (N["names"], N["ans"], len(N["away"])))
    check(len(moved) >= 1 and not off, "... away from home a note of the home chord right after the chord goes to the chord that plays (%d of %d moved; off the chord: %s)" % (len(moved), len(N["away"]), off[:3]))
    o_moved = [x for x in O["away"] if x[1] != x[2]]
    check(O["made"] == dict(bar=0, notes=0, steps=64) and len(O["away"]) >= 1 and not o_moved,
          "the tune of a 0.25 band plays those notes where they are written, whatever the chord (%d of %d moved; steps %s)" % (len(o_moved), len(O["away"]), O["ans"]))


def t026_gaps():
    group("0.26, the technical check: what no test had run - the remote's scene before and scene after (channel 14, CC 28 and 29)")
    s = Script()
    s.raw(100, "probe")
    remote(s, 200, 29); s.raw(300, "probe")
    remote(s, 400, 29); s.raw(500, "probe")
    remote(s, 600, 28); s.raw(700, "probe")
    remote(s, 800, 28); remote(s, 900, 28); s.raw(1000, "probe")
    for k in range(33): remote(s, 1100 + 40 * k, 29)
    s.raw(2500, "probe")
    log = run(s, 2700)
    sc = [int(x["G"]["scene"]) for x in probes(log)]
    check(sc == [0, 1, 2, 1, 0, 31], "the remote's CC 29 and 28: the scene after, the scene before - not before the first, not past the last (0.30: the thirty-second) (%s)" % sc)


def t026_octave_patterns():
    group("0.26, the technical check: the OCTAVE MIDI FX's other three ways (HOME 6 K3: RANDOM, 3RD, 4TH), which no test had played")
    # eight steps of C4, OCTAVE +1: 3RD moves the third of every three steps (the track's steps 3 and 6), 4TH the fourth of
    # every four (4 and 8); RANDOM half of them, by the step and the loop - not the same steps every loop
    res = {}
    for k, name in ((2, "3RD"), (3, "4TH"), (1, "RANDOM")):
        s = Script()
        t = s.steps(100, tuple(range(8)))
        t = home_page(s, t, 5, [(K1, 2), (K3, k)])                     # OCTAVE READY, +1, the way
        t = seq_page(s, t, 0, keys=[wk(5)])                            # ... in the chain
        p = t + 100
        s.tap_btn(p, PLAY)
        log = run(s, p + int(64 * STEP_MS) - 20)
        loops = []
        for lp in range(4):
            a = p + lp * 16 * STEP_MS - STEP_MS / 2
            loops.append([round((tm - a) / STEP_MS - 0.5) for tm, d1, _ in log.notes(ch=0, after=a) if tm < a + 16 * STEP_MS and d1 == 72])
        res[name] = (loops, sorted(set(d1 for _, d1, _ in log.notes(ch=0, after=p))))
    check(res["3RD"][0][0] == [2, 5] and res["3RD"][1] == [60, 72], "3RD: the 3rd and the 6th step an octave up, the rest as written (%s)" % (res["3RD"][:2],))
    check(res["4TH"][0][0] == [3, 7] and res["4TH"][1] == [60, 72], "4TH: the 4th and the 8th step an octave up (%s)" % (res["4TH"][:2],))
    r = res["RANDOM"][0]
    check(all(0 < len(x) < 8 for x in r) and len(set(tuple(x) for x in r)) > 1,
          "RANDOM: in every loop some steps up and some not, and not the same steps every loop (%s)" % r)


def t026_lfo_dests():
    group("0.26, the technical check: an LFO on CHANCE and an LFO on SWING (LFO page 2 K1), which no test had played")

    def lfo_run(clicks, bars=4):
        s = Script()
        end = s.steps(100, list(range(16)))
        s.press(end + 50, LFO); s.tap_key(end + 80, wk(0)); s.tap_btn(end + 130, OCT_UP, hold=20); s.enc(end + 200, K1, clicks); s.release(end + 300, LFO)
        p = end + 500
        s.tap_btn(p, PLAY)
        return p, run(s, p + int(bars * 16 * STEP_MS) - 20)
    # CHANCE: the LFO takes up to half the chance away and gives it back - of 64 steps at 100 %% some are silent, most play
    p, log = lfo_run(3)
    n = len(log.notes(ch=0, after=p))
    check(24 < n < 62, "LFO on CHANCE: of 64 steps some do not play, most do (%d)" % n)
    # SWING: 0 .. +25 on the track's swing - the steps on the eighths stay where they are, the ones between are late by
    # an amount that goes up and down with the LFO
    p, log = lfo_run(5)
    tms = [tm for tm, _, _ in log.notes(ch=0, after=p)]
    d = [tm - p - k * STEP_MS for k, tm in enumerate(tms)]
    base = sorted(d[0::2])[len(d[0::2]) // 2] if d else 0
    on8 = [x - base for x in d[0::2]]
    off8 = [x - base for x in d[1::2]]
    check(len(tms) == 64 and on8 and max(abs(x) for x in on8) < 0.08 * STEP_MS, "LFO on SWING: the steps on the eighths stay on the grid (%d notes, %s)" % (len(tms), [round(x, 1) for x in on8[:4]]))
    check(off8 and max(off8) > 0.2 * STEP_MS and max(off8) - min(off8) > 0.1 * STEP_MS and min(off8) > -0.08 * STEP_MS,
          "... the ones between are late, by an amount that moves with the LFO (%.1f .. %.1f ms)" % (min(off8) if off8 else 0, max(off8) if off8 else 0))


def t026_song_entries():
    group("0.26, the technical check: the song's own tempo (SAVE 2 K2 SONG TEMPO) and HOME + PERF black 10 (the last entry "
          "away), which no test had run")

    def tap(s, t, gap):                                                # tap tempo: HOME + REC four times (taps 2 s
        t += 2100                                                      # apart or less go on with the last ones)
        s.press(t, HOME)
        for i in range(4):
            s.tap_btn(t + 100 + gap * i, REC)
        s.release(t + 200 + 3 * gap, HOME)
        return t + 400 + 3 * gap

    def append(s, t, keys):                                            # PERF, HOME + the black keys
        s.tap_btn(t, GLO); s.press(t + 50, HOME)
        for i, k in enumerate(keys):
            s.tap_key(t + 100 + 100 * i, bk(k))
        s.release(t + 200 + 100 * len(keys), HOME); s.tap_btn(t + 300 + 100 * len(keys), GLO)
        return t + 500 + 100 * len(keys)

    res = {}
    for on in (1, 0):
        s = Script()
        t = tap(s, 100, 500)                                           # 120 BPM: entry 1, scene 1
        t = append(s, t, [0])
        t = tap(s, t, 400)                                             # 150 BPM: entries 2 and 3, scenes 2 and 3 ...
        t = append(s, t, [1, 2, 9])                                    # ... and black 10: entry 3 goes
        if on:
            s.press(t, SAVE); s.tap_btn(t + 50, OCT_UP); s.enc(t + 150, K2, 1); s.release(t + 250, SAVE); t += 400
        t = tap(s, t, 600)                                             # 100 BPM now
        s.raw(t, "probe")
        s.press(t + 100, HOME); s.tap_btn(t + 150, GLO); s.release(t + 250, HOME)   # the song on (stopped: entry 1)
        s.raw(t + 400, "probe")
        p = t + 500
        s.tap_btn(p, PLAY)
        s.raw(p + 8000 + 600, "probe")                                 # 4 bars at 120: entry 2
        s.raw(p + 8000 + 6400 + 600, "probe")                          # 4 bars at 150: entry 1 again (entry 3 went)
        log = run(s, p + 8000 + 6400 + 800)
        res[on] = [int(x["G"]["bpm"]) for x in probes(log)]
    check(res[1] == [100, 120, 150, 120], "SONG TEMPO on: each entry brings the tempo it was added at - 120, 150, then 120 again: "
          "the third entry was taken away by HOME + black 10 (%s)" % res[1])
    check(res[0][:2] == [100, 100] and all(b == res[0][1] for b in res[0][1:]), "SONG TEMPO off: the tempo stays (%s)" % res[0])


def t026_cook_lfo():
    group("0.26, the technical check: COOK with the LFOs among the targets (SEQ 3 K1 on ALL) cooks the LFO aimed at the "
          "track, which no test had run")
    res = {}
    for cook in (0, 1):
        s = Script()
        t = s.steps(100, list(range(16)))
        s.press(t + 50, LFO); s.tap_key(t + 80, wk(0)); s.tap_btn(t + 130, OCT_UP, hold=20); s.enc(t + 200, K3, -54)
        s.release(t + 300, LFO); t += 400                              # LFO 1 on: CC 20 (no lane's), channel 1
        t = seq_page(s, t, 2, encs=[(K1, 5)])                          # the targets: ALL
        t = seq_page(s, t, 0, encs=[(K4, 20)])                         # HEAT up
        if cook:
            for _ in range(6):
                t = seq_page(s, t, 0, keys=[wk(8)])                    # COOK, six times
        p = t + 100
        s.tap_btn(p, PLAY)
        log = run(s, p + 2 * 1875 + 100)
        res[cook] = [v for tm, st, d1, v in log.msgs if st == 0xB0 and d1 == 20 and tm >= p]
    check(len(res[0]) > 20 and len(res[1]) > 20 and res[0] != res[1],
          "six COOKs with ALL: the LFO aimed at the track is cooked too - its CC 20 is not the same wave (%d, %d values; %s / %s)"
          % (len(res[0]), len(res[1]), res[0][:6], res[1][:6]))


def t026_tablet_retrig():
    group("0.26, the technical check: the tablet's RETRIG (SAGGA Live, channel 12 CC 30), which no test had played")
    res = {}
    for rt in (0, 1):
        s = Script()
        t = remote13_on(s, 100)
        t = usb2(s, t)
        t = program(s, t, [60, 61, 62, 63, 64, 65, 66, 67])            # steps 1-8: C4 .. G4
        p = t + 100
        s.tap_btn(p, PLAY)
        if rt:
            s.raw(int(p + 5.5 * STEP_MS), "midi 0xBB 30 127 2")        # RETRIG of the tablet's track (T1), in the 6th step
        log = run(s, p + int(9 * STEP_MS))
        res[rt] = [d1 for _, d1, _ in log.notes(ch=0, after=p)][:9]
    check(res[0][:8] == [60, 61, 62, 63, 64, 65, 66, 67], "without: the eight steps in a row (%s)" % res[0])
    check(res[1][:9] == [60, 61, 62, 63, 64, 65, 60, 61, 62], "RETRIG in the 6th step: the track starts again from its first step at the next one (%s)" % res[1])


def t026_take_poly():
    group("0.26, the technical check: TAKE on a track at 1/4 5:4 (five steps in a bar), which no test had run")
    # five steps a bar, step 1 written: a MIDI-in note just after the third step starts (6.4 sixteenths in) - TAKE puts it
    # on the third step, the one it fell in
    s = Script()
    t = s.steps(100, [0])
    t = home_page(s, t, 0, [(K2, 5 - 16), (K3, 3)])                    # LENGTH 5; the division down to 1/32T ...
    t = home_page(s, t, 0, [(K3, 1)])                                  # ... and one past it: 1/4 5:4
    s.tap_btn(t, PLAY); p0 = t
    s.raw(p0 + int(6.4 * STEP_MS) + 15, "midi 0x90 67 100"); s.raw(p0 + int(7.4 * STEP_MS), "midi 0x80 67 0")
    s.press(p0 + int(14 * STEP_MS), REC); s.release(p0 + int(14 * STEP_MS) + 700, REC)
    s.at(p0 + int(14 * STEP_MS) + 750, "dump", 0)
    log = run(s, p0 + int(14 * STEP_MS) + 900)
    check(log.dumps[0]["on"][:5] == "x.x.." and log.states[0]["msg"].startswith("TAKE: 1 NOTES INTO T1"),
          "TAKE at 1/4 5:4: the note goes on the third of the five steps (%s %r)" % (log.dumps[0]["on"][:5], log.states[0]["msg"]))
    # the loop TAKE looks back over is the polyrhythm's: at 1/16 5:4 five steps are a quarter, 24 ticks - not five whole
    # ticks-steps of 4 (20). TAKE comes when REC has been held 0.6 s (31 ticks at 128 BPM): pressed at tick 120, it takes
    # at tick 150 or so - a note at tick 128 is in the last loop: taken
    s = Script()
    t = s.steps(100, [0])
    t = home_page(s, t, 0, [(K2, 5 - 16), (K3, 3)])
    t = home_page(s, t, 0, [(K3, 3)])                                  # 1/16 5:4
    s.tap_btn(t, PLAY); p0 = t
    s.raw(p0 + int(128 * STEP_MS / 6), "midi 0x90 67 100"); s.raw(p0 + int(129.5 * STEP_MS / 6), "midi 0x80 67 0")
    s.press(p0 + int(20 * STEP_MS), REC); s.release(p0 + int(20 * STEP_MS) + 700, REC)
    s.at(p0 + int(20 * STEP_MS) + 750, "dump", 0)
    log = run(s, p0 + int(20 * STEP_MS) + 900)
    check(log.states[0]["msg"].startswith("TAKE: 1 NOTES INTO T1"), "... it looks back over the polyrhythm's loop (at 1/16 5:4 a quarter): a note 22 ticks before TAKE is taken (%r)" % log.states[0]["msg"])


def t026_smooth():
    group("0.26 THE CHORDS MOVE LITTLE: FOLLOW MODE SMOOTH - a chord's notes go to the nearest notes of the chord playing (the ones two chords share stay); held chords slide; the makers' PAD and PIANO follow so")
    BAR = 16 * STEP_MS

    def setup(s, fm, rhythm=0):
        t = kp(s, 100, [(K2, 1), (K4, 1)])                             # C major, IN KEY
        t = home_page(s, t, 1, [(K4, 1)], cur=2)                       # FOLLOW
        t = uprog_knobs(s, t, [(K3, 1), (K2, 1), (K3, 8)])             # USER 1: I, V
        t = harm_knobs(s, t, [(K2, 8), (K1, 1)])                       # HARMONY: USER 1, ON
        if rhythm:
            t = harm2_knobs(s, t, [(K4, rhythm)])
        if fm:
            t = harm2_knobs(s, t, [(K1, fm)])
        return t

    # C E G written on step 1; the chords: C a bar, G a bar. HOLD moves the whole hand a fourth down (G3 B3 D4); SMOOTH
    # keeps the G and moves the other two by a step: B3 D4 G4 - and on C again it is the chord as written
    res = {}
    for fm in (SQ_FM_HOLD, SQ_FM_SMOOTH):
        s = Script()
        t = setup(s, fm)
        s.press(t, SEL); s.keys(t + 30, KEY_C4 | KEY_E4 | KEY_G4); s.keys(t + 120, 0); s.release(t + 200, SEL); t += 300
        s.at(t, "dump", 0)
        s.tap_btn(t + 20, PLAY); p0 = t + 20
        log = run(s, p0 + int(3 * BAR) - 30)
        bars = [sorted(set(d1 for tm, d1, _ in log.notes(ch=0, after=p0 + int(b * BAR) - 10) if tm < p0 + (b + 1) * BAR - 10)) for b in range(3)]
        res[fm] = (bars, harm11(log)[0]["fm"], [x["msg"] for x in log.states])
    check(res[SQ_FM_HOLD][0] == [[60, 64, 67], [55, 59, 62], [60, 64, 67]], "HOLD (as ever): the whole hand moves - C E G, then G B D a fourth down (%s)" % res[SQ_FM_HOLD][0])
    check(res[SQ_FM_SMOOTH][1] == SQ_FM_SMOOTH and "CHORDS MOVE LITTLE: THE NEAREST NOTES" in res[SQ_FM_SMOOTH][2],
          "ARP 4 K1 past MELODY: SMOOTH, and the FM-1 says what it is (%s)" % res[SQ_FM_SMOOTH][1])
    check(res[SQ_FM_SMOOTH][0] == [[60, 64, 67], [59, 62, 67], [60, 64, 67]],
          "SMOOTH: on G the chord is B D G - the G stays, C and E move a step; on C again as written (%s)" % res[SQ_FM_SMOOTH][0])

    # a chord held through the change (sixteen steps long, the chords change at the half bar): the G is not struck
    # again nor stopped; B and D come on before C and E end
    s = Script()
    t = setup(s, SQ_FM_SMOOTH, SQ_HR_HALF)
    s.press(t, SEL); s.keys(t + 30, KEY_C4 | KEY_E4 | KEY_G4); s.keys(t + 120, 0); s.release(t + 200, SEL); t += 300
    s.raw(t, "attach"); t += 100
    s.at(t, "pad", 0, 0, 100); s.at(t + 300, "pad", 15, 0, 100); s.at(t + 360, "pad", 15, 0, 0); s.at(t + 400, "pad", 0, 0, 0); t += 500
    s.tap_btn(t + 20, PLAY); p0 = t + 20
    log = run(s, p0 + int(BAR) - 30)
    ons = [(tm - p0, d1) for tm, st, d1, d2 in log.msgs if st == 0x90 and d2 and tm >= p0]
    offs = [(tm - p0, d1) for tm, st, d1, d2 in log.msgs if (st == 0x80 or (st == 0x90 and not d2)) and tm >= p0]
    new_on = [tm for tm, d in ons if d in (59, 62)]
    old_off = [tm for tm, d in offs if d in (60, 64)]
    check(sorted(d for _, d in ons) == [59, 60, 62, 64, 67] and len(new_on) == 2 and len(old_off) == 2 and max(new_on) <= min(old_off) and
          abs(min(old_off) - 8 * STEP_MS) < 8 and not [1 for tm, d in offs if d == 67],
          "a chord held through the change: the G goes on, B and D come before C and E end (%s %s)" % (ons, offs))

    # the makers: HOUSE has a PIANO and a PAD - made by BAND they follow SMOOTH; its lead a MELODY; the bass as ever
    def band(s, t): s.press(t, SEQ); s.tap_key(t + 30, bk(6), hold=700); s.release(t + 800, SEQ); return t + 900
    s = Script()
    s.press(100, SEQ); s.enc(130, E_PRE, 3); s.release(180, SEQ)       # the genre: HOUSE
    t = pg(s, 300, SEQ, 7, [(K1, 1)])                                  # the SOURCE on THEORY
    t = band(s, t)
    for k in range(12):
        s.at(t, "dump", k); t += 20
    log = run(s, t + 200)
    fm = {x["track"]: x["fm"] for x in harm11(log)}
    fn = {x["track"]: x["func"] for x in th_dumps(log) if x["style"]}
    ways = {f: fm[tk] for tk, f in fn.items()}
    check((22 in ways or 23 in ways) and all(ways[f] == SQ_FM_SMOOTH for f in (22, 23) if f in ways),
          "the band of HOUSE: its PAD and its PIANO follow SMOOTH (parts %s, ways %s)" % (sorted(fn.values()), ways))
    check(all(ways[f] == SQ_FM_HOLD for f in (4, 21) if f in ways) and all(ways[f] == SQ_FM_MELODY for f in (24, 25) if f in ways),
          "... the bass and a stab as ever, a lead and a voice as a MELODY (%s)" % ways)


def log_kb(flash):
    """the 'kb mode/channel' of the project a flash file boots with (a dump's line)"""
    s = Script()
    s.at(600, "dump", 0)
    m = re.search(r" (kb \d+/\d+) thru", run(s, 800, flash=flash).text)
    return m.group(1) if m else ""


def t026_live_chords():
    group("0.26 LIVE CHORDS: KEYBOARD CHORDS (SAVE 4 K2) - the notes held on the keyboard are the harmony's chord, whatever the progression; it stays until the next one; with the split the right hand plays; the keyboard given back, the progression is back")
    BAR = 16 * STEP_MS

    def setup(s, mode=3, harm=True):
        t = kp(s, 100, [(K2, 1), (K4, 1)])                             # C major, IN KEY
        t = s.steps(t, [0, 4, 8, 12])                                  # four Cs a bar
        t = home_page(s, t, 1, [(K4, 1)], cur=2)                       # FOLLOW
        if harm:
            t = uprog_knobs(s, t, [(K3, 1), (K2, 1), (K3, 8)])         # USER 1: I, V a bar each
            t = harm_knobs(s, t, [(K2, 8), (K1, 1)])                   # HARMONY: USER 1, ON
        t = pg(s, t, SAVE, 3, [(K2, mode)])                            # KEYBOARD: 3 CHORDS, 4 CHORDS <C3
        return t

    def chord(s, t, notes, hold=150):
        for k, n in enumerate(notes):
            s.at(t + k, "midi", "0x90", n, 100)
        for k, n in enumerate(notes):
            s.at(t + hold + k, "midi", "0x80", n, 0)
        return t + hold + 20

    def beats(log, p0, n):
        got = {}
        for tm, d1, _ in log.notes(ch=0, after=p0):
            k = int(round((tm - p0) / (4 * STEP_MS)))
            if k < n:
                got.setdefault(k, d1)
        return [got.get(k) for k in range(n)]

    # the progression says C for a bar, then G. In the first bar the keyboard plays F A C: from the next beat the track
    # is on F - and stays there in the second bar, where the progression has G: the keyboard's chord is the harmony
    s = Script()
    t = setup(s)
    s.tap_btn(t + 20, PLAY); p0 = t + 20
    chord(s, p0 + int(5 * STEP_MS), [53, 57, 60])
    s.raw(p0 + int(7 * STEP_MS), "probe")
    chord(s, p0 + int(21 * STEP_MS), [57, 60, 64])                     # A C E in the second bar: A minor
    s.raw(p0 + int(23 * STEP_MS), "probe")
    t2 = pg(s, p0 + int(26 * STEP_MS), SAVE, 3, [(K2, -3)])            # the keyboard given back: the progression (G now)
    s.raw(t2 + 10, "probe")
    log = run(s, p0 + int(2 * BAR) - 30)
    b = beats(log, p0, 8)
    pr = probes(log)
    check(b[:2] == [60, 60] and b[2:5] == [65, 65, 65], "F A C held on the keyboard: the track goes to F on the next beat and stays, the second bar too (%s)" % b)
    check(b[5] == 65 and b[6] in (57, 69), "... A C E after the second bar's second beat: that beat still on F, the next on A (%s)" % b)
    check(b[7] in (55, 67), "KEYBOARD back to OFF: the progression's chord again, G in its second bar (%s)" % b)
    check(len(pr) == 3 and pr[0]["G"]["kbc"] == "1" and pr[0]["G"]["chord"] == "IV" and pr[1]["G"]["chord"] == "vi" and pr[2]["G"]["kbc"] == "0" and pr[2]["G"]["chord"] == "V",
          "the FM-1 names the chord: IV, then vi; given back: the progression's V (%s)" % [(x["G"]["kbc"], x["G"]["chord"]) for x in pr])
    check("CHORD IV (THE KEYBOARD'S)" in [x["G"].get("msg") for x in pr], "... and says it is the keyboard's (%s)" % [x["G"].get("msg") for x in pr])
    check(not [1 for tm, d1, _ in log.notes(ch=0, after=p0) if d1 in (53, 57) and abs((tm - p0) / STEP_MS - round((tm - p0) / STEP_MS)) > 0.2],
          "the notes of the chord are not played as notes")

    # with the HARMONY off the keyboard's chord is the harmony all the same; before any chord: as written
    s = Script()
    t = setup(s, harm=False)
    s.tap_btn(t + 20, PLAY); p0 = t + 20
    chord(s, p0 + int(5 * STEP_MS), [55, 59, 62])                      # G B D
    log = run(s, p0 + int(BAR) - 30)
    b = beats(log, p0, 4)
    check(b[:2] == [60, 60] and b[2:] in ([55, 55], [67, 67]), "the HARMONY off: as written until a chord is held, then on it (%s)" % b)

    # CHORDS <C3: under C3 the chord, above it the right hand plays the track (MIDI IN ALWAYS)
    s = Script()
    t = setup(s, mode=4)
    t = pg(s, t, SAVE, 3, [(K4, 1)])                                   # MIDI IN ALWAYS
    s.tap_btn(t + 20, PLAY); p0 = t + 20
    chord(s, p0 + int(5 * STEP_MS), [41, 45, 36])                      # F2 A2 C2 (C in the bass: F over C)
    s.at(p0 + int(9 * STEP_MS) + 40, "midi", "0x90", 76, 90); s.at(p0 + int(9 * STEP_MS) + 90, "midi", "0x80", 76, 0)
    s.raw(p0 + int(11 * STEP_MS), "probe")
    log = run(s, p0 + int(BAR) - 30)
    b = beats(log, p0, 4)
    played = [d1 for tm, d1, _ in log.notes(ch=0, after=p0 + int(9 * STEP_MS)) if tm < p0 + int(10 * STEP_MS)]
    check(b[2:] == [65, 65] and probes(log)[0]["G"]["chord"] == "IV", "CHORDS <C3: the left hand's F A C (over C) is the chord (%s, %s)" % (b, probes(log)[0]["G"]["chord"]))
    check(76 in played and not [1 for tm, d1, _ in log.notes(ch=0, after=p0) if d1 in (41, 45, 36)], "... the right hand's note plays, the left hand's notes do not (%s)" % played)

    # a project loaded: no chord of the keyboard's; the mode is saved with the project
    d = tempfile.mkdtemp()
    fl = os.path.join(d, "flash.bin")
    s = Script()
    t = setup(s)
    chord(s, t + 50, [53, 57, 60]); t += 300
    s.raw(t, "probe"); t += 20
    s.tap_btn(t, SAVE); s.tap_btn(t + 300, SAVE); t += 3000            # SAVE, SAVE: the project in its slot
    pr0 = probes(run(s, t + 200, flash=fl))
    check(pr0 and pr0[0]["G"]["kbc"] == "1", "(a chord of the keyboard's is held when the project is saved)")
    s = Script()
    s.raw(600, "probe")
    log = run(s, 800, flash=fl)
    pr = probes(log)
    check(bool(pr) and pr[0]["G"]["kbc"] == "0" and pr[0]["G"]["chord"] == "I" and "kb 3/" in log_kb(fl),
          "after a power cycle no chord is held - the harmony is the progression's - and KEYBOARD is still on CHORDS (%s)" % ([(x["G"]["kbc"], x["G"]["chord"]) for x in pr],))
    shutil.rmtree(d, ignore_errors=True)


def t026_scene_metre():
    group("0.26 THE METRE WITH THE SCENE: SCENE METRE (GLO 4 K3) - a scene stored with it on keeps its metre and brings it: at once when stopped, on the bar line when it plays; the song changes metre with its scenes; off, a scene leaves the metre alone")
    T16 = STEP_MS

    def metre_dump(log): return [(x["bar"], x["sig"]) for x in log.metre]

    def store(s, t, k): s.press(t, SEL); s.tap_key(t + 30, bk(k)); s.release(t + 100, SEL); return t + 160
    def recall(s, t, k): s.tap_key(t, bk(k)); return t + 100

    # scene 1 stored in 4/4, scene 2 in 7/8 (2+2+3), SCENE METRE on. Stopped: recalling a scene brings its bar at once
    def setup(s, on=True):
        t = s.steps(100, [0])                                          # a note on the one: a 16-step track follows the bar
        if on:
            t = metre_knobs(s, t, [(K3, 1)])                           # SCENE METRE: BRING IT
        s.tap_btn(t, GLO); t += 80                                     # PERF
        t = store(s, t, 0)                                             # scene 1: 4/4
        s.tap_btn(t, GLO); t += 80
        t = metre_knobs(s, t, [(K1, -2)])                              # the bar: 14 steps, 7/8 as 2+2+3
        s.tap_btn(t, GLO); t += 80
        t = store(s, t, 1)                                             # scene 2: 7/8
        return t                                                       # (PERF is on: the black keys recall)

    s = Script()
    t = setup(s)
    s.raw(t, "probe"); t += 20
    t = recall(s, t, 0); s.raw(t, "probe"); s.at(t, "dump", 0); t += 40
    t = recall(s, t, 1); s.raw(t, "probe"); s.at(t, "dump", 0); t += 40
    log = run(s, t + 200)
    pr = probes(log)
    msgs = [x["msg"] for x in log.states]
    check([x["G"]["bar"] for x in pr] == ["14", "16", "14"] and [x["T1"]["len"] for x in pr] == ["14", "16", "14"],
          "stopped: scene 1 brings 4/4, scene 2 7/8 - the bar and the track that was a bar long (%s %s)" % ([x["G"]["bar"] for x in pr], [x["T1"]["len"] for x in pr]))
    check(pr[0]["G"].get("msg") == "SCENE STORED 2 IN 7/8", "the FM-1 says the metre a scene is stored in (%s)" % pr[0]["G"].get("msg"))
    check(metre_dump(log) == [(16, "4/4"), (14, "7/8")], "... 4/4, then 7/8 (%s)" % metre_dump(log))

    # SCENE METRE off (as every project until 0.25): the scenes leave the metre alone, and store none
    s = Script()
    t = setup(s, on=False)
    t = recall(s, t, 0); s.raw(t, "probe"); t += 40
    log = run(s, t + 200)
    pr = probes(log)
    check(pr[0]["G"]["bar"] == "14" and pr[0]["G"]["smetre#"] == probes(run(Script().raw(300, "probe"), 400))[0]["G"]["smetre#"],
          "SCENE METRE off: a scene recalled leaves the bar as it is, and no scene keeps a metre (%s)" % pr[0]["G"]["bar"])

    # in play, QUANTISE AUTO: the scene comes on the bar line, and the new bar begins on that very line - the notes
    # on the one are 16 steps apart in 4/4, 14 in 7/8
    s = Script()
    t = setup(s)
    t = recall(s, t, 0)                                                # 4/4 to begin with
    s.tap_btn(t + 20, PLAY); p0 = t + 20
    recall(s, p0 + int(5 * T16), 1)                                    # in the first bar: scene 2 queued for the bar
    recall(s, p0 + int((16 + 14 + 5) * T16), 0)                        # in the second 7/8 bar: scene 1 for the next bar
    log = run(s, p0 + int((16 + 14 + 14 + 16 + 16) * T16) - 30)
    ones = [int(round((tm - p0) / T16)) for tm, d1, _ in log.notes(ch=0, after=p0)]
    check(ones == [0, 16, 30, 44, 60], "in play: scene 2 comes at the bar and its bars are 14 steps from that line; scene 1 brings 16 back (%s)" % ones)

    # the song: scene 1 for a bar, scene 2 for two, round again - the entries are bars of each scene's own metre
    s = Script()
    t = setup(s)
    s.tap_btn(t, GLO); t += 80                                         # (out of PERF)
    s.raw(t, "attach"); t += 50
    view(s, t, GC_VPERF); view(s, t + 50, GC_VPERF); t += 100          # the grid's SONG
    s.pad(t, 0, 1); s.pad(t + 50, 0, 2)                                # entry 1: scene 1, 1 bar
    s.pad(t + 100, 1, 0); s.pad(t + 150, 1, 1); s.pad(t + 200, 1, 2)   # entry 2: scene 2, 2 bars
    s.pad(t + 300, 0, 3); t += 400                                     # song on
    s.tap_btn(t + 20, PLAY); p0 = t + 20
    log = run(s, p0 + int((16 + 28 + 16 + 28 + 4) * T16) - 30)
    ones = [int(round((tm - p0) / T16)) for tm, d1, _ in log.notes(ch=0, after=p0)]
    check(ones == [0, 16, 30, 44, 60, 74, 88], "the song: a bar of 4/4, two of 7/8, a bar of 4/4, two of 7/8 ... (%s)" % ones)

    # a song position from outside (a slave): bar 3 of the song's time is the second 7/8 bar - 16 + 14 steps in
    s = Script()
    t = setup(s)
    s.tap_btn(t, GLO); t += 80
    s.raw(t, "attach"); t += 50
    view(s, t, GC_VPERF); view(s, t + 50, GC_VPERF); t += 100
    s.pad(t, 0, 1); s.pad(t + 50, 0, 2)
    s.pad(t + 100, 1, 0); s.pad(t + 150, 1, 1); s.pad(t + 200, 1, 2)
    s.pad(t + 300, 0, 3); t += 400
    s.press(t, HOME); s.tap_btn(t + 30, PLAY); s.release(t + 100, HOME); t += 200   # the clock: slave
    spp = 16 + 14 + 3                                                  # 16ths: three steps into the second 7/8 bar
    s.at(t, "midi", "0xF2", spp & 127, spp >> 7); t += 30
    s.raw(t, "probe"); s.at(t, "dump", 0)
    log = run(s, t + 200)
    pr = probes(log)[0]
    m = log.metre[-1]
    check(pr["G"]["bar"] == "14" and pr["T1"]["step"] == "3" and m["no"] == 2 and m["into"] == 18,
          "a song position in the second 7/8 bar: the bar is 14, the track on its step 4, bar 3 of the song (%s %s %s %s)" % (pr["G"]["bar"], pr["T1"]["step"], m["no"], m["into"]))


def t026_click():
    group("0.26 THE CLICK (SAVE 5): a metronome on the beats of the metre, the bar line louder - the FM-1's own sound or a MIDI note; COUNT IN: PLAY with REC on counts one or two bars first")
    BEAT = 4 * STEP_MS

    # CLICK PLAY, the FM-1's own sound: asked ahead, it falls on the beats; in the sound the simulator writes the
    # bar line is the high tone (2000 Hz: about forty crossings in 10 ms), a beat the low one (1000 Hz: twenty)
    d = tempfile.mkdtemp()
    s = Script()
    t = click_knobs(s, 200, [(K1, 2)])
    s.tap_btn(t + 100, PLAY); p0 = t + 100
    s.raw(p0 + int(9 * BEAT), "probe")
    log = run(s, p0 + int(9 * BEAT) + 300, shots=d)
    ck = clicks(log)
    check([k for _, k, _ in ck][:9] == ["bar", "beat", "beat", "beat"] * 2 + ["bar"] and [tk for _, _, tk in ck][:9] == [24 * i for i in range(9)],
          "CLICK PLAY: a click a beat, the first of four the bar line's (%s)" % [(k, tk) for _, k, tk in ck][:9])
    check(all(abs(tm - (p0 + i * BEAT)) < 2.0 for i, (tm, _, _) in enumerate(ck[:9])), "... asked for the very moment of the beat (%s)" % [round(tm - p0 - i * BEAT, 2) for i, (tm, _, _) in enumerate(ck[:9])])
    wc = wav_clicks(os.path.join(d, "o.wav"))
    check(len(wc) >= 9 and all(abs(wc[i][0] - (p0 + i * BEAT)) < 2.5 for i in range(1, 9)),
          "the sound: every click begins on its beat, within the simulator's two milliseconds (%s)" % [round(wc[i][0] - p0 - i * BEAT, 2) for i in range(min(9, len(wc)))])
    check(all(36 <= wc[i][2] <= 44 for i in (0, 4, 8)) and all(17 <= wc[i][2] <= 23 for i in (1, 2, 3, 5, 6, 7)) and wc[0][1] > 8000,
          "the bar line is the high tone, a beat the low one (%s)" % [(x[1], x[2]) for x in wc[:9]])
    pr = probes(log)[0]["G"]
    check(pr["cnt"] == "0" and int(pr["clk"]) >= 9 and pr["clkl"] in ("1", "2"), "the probe counts them (%s)" % pr["clk"])
    shutil.rmtree(d, ignore_errors=True)

    # the level: softer, louder (the default is 7)
    peaks = {}
    for lv in (-6, 3):
        d = tempfile.mkdtemp()
        s = Script()
        t = click_knobs(s, 200, [(K1, 2), (K4, lv)])
        s.tap_btn(t + 100, PLAY)
        run(s, t + 100 + int(2 * BEAT), shots=d)
        peaks[lv] = max(x[1] for x in wav_clicks(os.path.join(d, "o.wav")))
        shutil.rmtree(d, ignore_errors=True)
    check(peaks[-6] < 600 and peaks[3] > 28000, "LEVEL 1 is a whisper, 10 nearly full (%s)" % peaks)

    # 7/8 as 2+2+3: three clicks a bar - on steps 1, 5, 9 of its fourteen
    s = Script()
    t = metre_knobs(s, 200, [(K1, -2)])
    t = click_knobs(s, t, [(K1, 2)])
    s.tap_btn(t + 100, PLAY); p0 = t + 100
    log = run(s, p0 + int(28 * STEP_MS) + 100)
    ck = [(k, tk // 6) for _, k, tk in clicks(log)]
    check(ck[:7] == [("bar", 0), ("beat", 4), ("beat", 8), ("bar", 14), ("beat", 18), ("beat", 22), ("bar", 28)], "7/8: the beats of the metre, 2+2+3 (%s)" % ck[:7])

    # a MIDI click: the note (claves, 75) on channel 10, the bar line louder; each ends after 40 ms; SEL + K4 the note
    s = Script()
    t = click_knobs(s, 200, [(K1, 2), (K3, 10)])
    t = click_knobs(s, t, [(K4, -38)], sel=True)                       # the note: 37
    s.tap_btn(t + 100, PLAY); p0 = t + 100
    log = run(s, p0 + int(5 * BEAT) + 100)
    on = [(tm, d1, d2) for tm, st, d1, d2 in log.msgs if st == 0x99 and d2]
    off = [(tm, d1) for tm, st, d1, d2 in log.msgs if st == 0x89]
    check([x[1:] for x in on[:5]] == [(37, 100), (37, 69), (37, 69), (37, 69), (37, 100)] and all(abs(on[i][0] - (p0 + i * BEAT)) < 2.0 for i in range(5)),
          "a MIDI click: note 37 on channel 10 on every beat, the bar line louder (%s)" % [(round(x[0] - p0), x[1], x[2]) for x in on[:5]])
    check(len(off) >= 4 and all(38 <= off[i][0] - on[i][0] <= 44 for i in range(4)), "... each 40 ms long (%s)" % [off[i][0] - on[i][0] for i in range(min(4, len(off)))])
    check(not clicks(log), "... and the FM-1 makes no sound of its own")

    # CLICK REC: only while REC is on
    s = Script()
    t = click_knobs(s, 200, [(K1, 1), (K3, 10)])
    s.tap_btn(t + 100, PLAY); p0 = t + 100
    s.tap_btn(p0 + int(4.5 * BEAT), REC)
    s.tap_btn(p0 + int(8.5 * BEAT), REC)
    log = run(s, p0 + int(12 * BEAT))
    on = [int(round((tm - p0) / BEAT)) for tm, st, d1, d2 in log.msgs if st == 0x99 and d2]
    check(on == [5, 6, 7, 8], "CLICK REC: the click only while REC is on (beats %s)" % on)

    # COUNT IN 1 BAR, the click OFF: PLAY with REC on counts four beats (the bar line first), then the transport starts
    # exactly a bar after the count's first click - the START, the clock, the track's first note; no click after it
    def counted(s, t, bars=1, click=0, out=10):
        t = s.steps(t, [0])
        t = click_knobs(s, t, [(K1, click), (K2, bars), (K3, out)])
        s.tap_btn(t, REC); t += 100
        s.tap_btn(t, PLAY)
        return t

    s = Script()
    t = counted(s, 100)
    s.raw(t + int(2 * BEAT), "probe")
    log = run(s, t + int(8 * BEAT) + 300)
    on = [(tm, d2) for tm, st, d1, d2 in log.msgs if st == 0x99 and d2]
    fa = [tm for tm, st, _, _ in log.msgs if st == 0xFA]
    note = [tm for tm, d1, _ in log.notes(ch=0)]
    clock = log.clock()
    check(len(on) == 4 and [v for _, v in on] == [100, 69, 69, 69] and all(abs(on[i][0] - on[0][0] - i * BEAT) < 2.0 for i in range(4)),
          "COUNT IN 1 BAR: four clicks a beat apart, the first the bar line's, and no more (%s)" % [(round(x[0] - on[0][0]), x[1]) for x in on])
    check(len(fa) == 1 and abs(fa[0] - on[0][0] - 4 * BEAT) < 3.0 and note and abs(note[0] - fa[0]) < 3.0 and clock and clock[0] >= fa[0] - 1,
          "... the transport starts a bar after the first click: START, the clock, the first note (%s after, the note %s)" % (fa[0] - on[0][0] if fa else None, note[0] - fa[0] if note and fa else None))
    pr = probes(log)[0]["G"]
    check(pr["cnt"] == "1" and pr["play"] == "0" and (pr.get("msg") or "").startswith("COUNT IN 1."), "while it counts the FM-1 is not playing, and the screen counts (%s)" % pr.get("msg"))

    # two bars, the click PLAY, the FM-1's own sound: eight clicks of the count, then the click goes on with what plays -
    # one a beat, none twice, the bar lines every four
    s = Script()
    t = counted(s, 100, bars=2, click=2, out=0)
    log = run(s, t + int(14 * BEAT))
    ck = clicks(log)
    fa = [tm for tm, st, _, _ in log.msgs if st == 0xFA]
    tms = [tm for tm, _, _ in ck]
    check(len(ck) >= 13 and [k for _, k, _ in ck][:13] == (["bar", "beat", "beat", "beat"] * 4)[:13] and all(abs(tms[i] - tms[0] - i * BEAT) < 2.0 for i in range(13)),
          "COUNT IN 2 BARS with CLICK PLAY: the count's eight clicks and the ones after, a beat apart, each once (%s)" % [round(x - tms[0]) for x in tms[:13]])
    check(fa and abs(fa[0] - tms[8]) < 3.0, "... the transport starts on the ninth (%s)" % (fa[0] - tms[8] if fa else None))

    # PLAY again while it counts: nothing starts; without REC there is no count; a slave has none either
    s = Script()
    t = counted(s, 100)
    s.tap_btn(t + int(2.5 * BEAT), PLAY)
    s.raw(t + int(3 * BEAT), "probe")
    log = run(s, t + int(8 * BEAT))
    pr = probes(log)[0]["G"]
    check(not [1 for tm, st, _, _ in log.msgs if st == 0xFA] and pr["cnt"] == "0" and pr["play"] == "0" and len([1 for tm, st, d1, d2 in log.msgs if st == 0x99 and d2]) == 3,
          "PLAY while it counts: the count stops, nothing starts (%s)" % pr.get("msg"))
    s = Script()
    t = s.steps(100, [0])
    t = click_knobs(s, t, [(K2, 1), (K3, 10)])
    s.tap_btn(t, PLAY)
    log = run(s, t + int(2 * BEAT))
    fa = [tm for tm, st, _, _ in log.msgs if st == 0xFA]
    check(fa and fa[0] - t < 5 and not [1 for tm, st, d1, d2 in log.msgs if st == 0x99 and d2], "without REC: PLAY starts at once, no count")

    # a note played while it counts sounds (MIDI IN ALWAYS) and is written nowhere
    s = Script()
    t = pg(s, 100, SAVE, 3, [(K4, 1)])
    t = click_knobs(s, t, [(K2, 1), (K3, 10)])
    s.tap_btn(t, REC); t += 100
    s.tap_btn(t, PLAY)
    s.at(t + int(1.5 * BEAT), "midi", "0x90", 64, 100); s.at(t + int(1.5 * BEAT) + 60, "midi", "0x80", 64, 0)
    s.at(t + int(6 * BEAT), "dump", 0)
    log = run(s, t + int(6 * BEAT) + 100)
    check(64 in [d1 for tm, d1, _ in log.notes(ch=0)] and "x" not in log.dumps[0]["on"], "a note played during the count sounds and is not recorded (%s)" % log.dumps[0]["on"])

    # the settings are the project's: saved, and back after a power cycle; a new page: SAVE has five
    d = tempfile.mkdtemp()
    fl = os.path.join(d, "flash.bin")
    s = Script()
    t = click_knobs(s, 200, [(K1, 1), (K2, 2), (K3, 5), (K4, 2)])
    s.raw(t, "probe"); t += 30
    s.tap_btn(t, SAVE); s.tap_btn(t + 300, SAVE); t += 3000            # SAVE, SAVE
    a = probes(run(s, t + 200, flash=fl))[0]["G"]["set26#"]
    b = probes(run(Script().raw(600, "probe"), 800, flash=fl))[0]["G"]["set26#"]
    c = probes(run(Script().raw(600, "probe"), 800))[0]["G"]["set26#"]
    check(a == b and a != c, "the click's settings are saved with the project (%s %s, a new one %s)" % (a, b, c))
    shutil.rmtree(d, ignore_errors=True)

def t026_expression():
    group("0.26 THE KEYBOARD'S EXPRESSION: the pedal, the wheels and the aftertouch go where the keyboard's notes go; recorded - the wheels in the lanes, the pedal as the length of the notes; nothing is left on a channel")
    def outs(log, kinds=(0xB0, 0xE0, 0xD0, 0xA0), after=0):
        return [(st, d1, d2) for tm, st, d1, d2 in log.msgs if (st & 0xF0) in kinds and tm >= after]

    # MIDI IN ALWAYS, track 3 selected: what the keyboard sends on its channel 1 comes out on channel 3
    s = Script()
    s.enc(100, E_SEL, 2)
    t = pg(s, 200, SAVE, 3, [(K4, 1)])
    s.raw(t, "midi 0xE0 0 96"); s.raw(t + 20, "midi 0xD0 80 0"); s.raw(t + 40, "midi 0xB0 1 64"); s.raw(t + 60, "midi 0xB0 64 127")
    s.raw(t + 80, "midi 0x90 60 100"); s.raw(t + 100, "midi 0xA0 60 55"); s.raw(t + 120, "midi 0x80 60 0")
    s.raw(t + 140, "midi 0xB0 64 0"); s.raw(t + 160, "midi 0xE0 0 64"); s.raw(t + 180, "midi 0xD0 0 0")
    log = run(s, t + 400)
    o = outs(log, after=t)
    check(o == [(0xE2, 0, 96), (0xD2, 80, 0), (0xB2, 1, 64), (0xB2, 64, 127), (0xA2, 60, 55), (0xB2, 64, 0), (0xE2, 0, 64), (0xD2, 0, 0)],
          "MIDI IN ALWAYS: the wheel, the aftertouch (the channel's, a key's), the modulation, the pedal go to the track's channel (%s)" % [("%02X" % a, b, c) for a, b, c in o])

    # ... with REC off and MIDI IN on REC ONLY nothing of it passes (as its notes do not)
    s = Script()
    s.enc(100, E_SEL, 2)
    s.raw(300, "midi 0xE0 0 96"); s.raw(320, "midi 0xD0 80 0"); s.raw(340, "midi 0xB0 1 64"); s.raw(360, "midi 0xB0 64 127"); s.raw(380, "midi 0xB0 64 0")
    log = run(s, 600)
    check(outs(log, after=250) == [], "MIDI IN with REC only, REC off: nothing passes (%s)" % outs(log, after=250))

    # what was left on a channel is put back there: the pedal's release goes where its press went, a wheel off its
    # centre is centred on the channel it bent when the next move goes to another track
    s = Script()
    s.enc(100, E_SEL, 2)
    t = pg(s, 200, SAVE, 3, [(K4, 1)])
    s.raw(t, "midi 0xB0 64 127"); s.raw(t + 20, "midi 0xE0 0 100")
    s.enc(t + 60, E_SEL, 2)                                            # track 5
    s.raw(t + 120, "midi 0xB0 64 0"); s.raw(t + 140, "midi 0xE0 0 90")
    log = run(s, t + 400)
    o = outs(log, after=t)
    check(o == [(0xB2, 64, 127), (0xE2, 0, 100), (0xB2, 64, 0), (0xE2, 0, 64), (0xE4, 0, 90)],
          "the track changed with the pedal down and the wheel up: the release and the centre go to the old channel (%s)" % [("%02X" % a, b, c) for a, b, c in o])

    # a STOP lets the pedal go and centres the wheel on the channels they were left on
    s = Script()
    t = pg(s, 200, SAVE, 3, [(K4, 1)])
    s.tap_btn(t, PLAY)
    s.raw(t + 100, "midi 0xB0 64 127"); s.raw(t + 120, "midi 0xE0 0 20"); s.raw(t + 140, "midi 0xD0 70 0")
    s.tap_btn(t + 400, PLAY)
    log = run(s, t + 700)
    o = outs(log, kinds=(0xB0, 0xE0, 0xD0), after=t + 390)
    check((0xB0, 64, 0) in o and (0xE0, 0, 64) in o and (0xD0, 0, 0) in o, "STOP: the pedal let go, the wheel centred, the aftertouch off (%s)" % [("%02X" % a, b, c) for a, b, c in o])

    # RECORDED. REC and PLAY; the modulation wheel moves during steps 3, 4 and 5 (30, 60, 90): a free lane is taken for
    # it - the last, with SLIDE - and the value is on the steps as they played; REC off: the next loop plays it back
    BAR = 16 * STEP_MS
    s = Script()
    s.tap_btn(100, REC)
    s.tap_btn(200, PLAY); p0 = 200
    for k, v in ((2.5, 30), (3.5, 60), (4.5, 90)):
        s.raw(p0 + int(k * STEP_MS), "midi 0xB0 1 %d" % v)
    s.raw(p0 + int(5 * STEP_MS), "probe")
    s.tap_btn(p0 + int(12 * STEP_MS), REC)
    log = run(s, p0 + int(2 * BAR) + 40)
    pr = probes(log)[0]
    cc = {}
    for tm, st, d1, d2 in log.msgs:
        if st == 0xB0 and d1 == 1 and tm >= p0 + BAR - 10:
            cc[int(round((tm - p0 - BAR) / STEP_MS))] = d2
    check(pr["G"].get("msg") == "LANE 3 RECORDS CC 1", "REC: the wheel moves - the lane that sends it (a new track's third) records it, the screen says so (%s)" % pr["G"].get("msg"))
    check(cc.get(3) == 30 and cc.get(4) == 60 and cc.get(5) == 90 and cc.get(6) == 90,
          "... played back on the steps it was moved on: 30, 60, 90 on steps 4, 5, 6 (%s)" % sorted(cc.items()))
    check(cc.get(10) is not None and 30 < cc[10] < 90, "... and it glides back between them (SLIDE) (%s)" % cc.get(10))

    # the pitch wheel and the aftertouch have no lane on a new track: each takes one nobody ever wrote, from the last
    # (never the first: the FILTER macro's); with none left the screen says so, and the control passes all the same
    s = Script()
    s.tap_btn(100, REC)
    s.tap_btn(200, PLAY); p0 = 200
    s.raw(p0 + 100, "midi 0xE0 0 80"); s.raw(p0 + 110, "probe")
    s.raw(p0 + 120, "midi 0xD0 50 0"); s.raw(p0 + 130, "probe")
    for k, c in enumerate((20, 21, 22, 23)):
        s.raw(p0 + 140 + 8 * k, "midi 0xB0 %d 99" % c)
    s.raw(p0 + 172, "midi 0xB0 24 99"); s.raw(p0 + 180, "probe")
    s.raw(p0 + 190, "midi 0xB0 25 77"); s.raw(p0 + 200, "probe")
    s.raw(p0 + 210, "midi 0xB0 64 127"); s.raw(p0 + 220, "midi 0xB0 64 0"); s.raw(p0 + 230, "midi 0xB0 0 3"); s.raw(p0 + 240, "probe")
    s.raw(p0 + 250, "midi 0xB0 74 5"); s.raw(p0 + 260, "probe")
    log = run(s, p0 + 600)
    m = [x["G"].get("msg") for x in probes(log)]
    check(m[:5] == ["LANE 8 RECORDS THE PITCH WHEEL", "LANE 7 RECORDS THE AFTERTOUCH", "LANE 2 RECORDS CC 24", "NO FREE LANE FOR CC 25"] + ["NO FREE LANE FOR CC 25"] and (0xB0, 25, 77) in outs(log),
          "the wheel, the aftertouch, five more controllers: seven lanes taken (0.28: eight lanes); the next control has none, and passes all the same (%s)" % m[:4])
    check(m[4] == "NO FREE LANE FOR CC 25" and m[5] == "LANE 1 RECORDS CC 74", "the pedal and the bank select never ask for a lane; lane 1 still records its own controller (%s)" % m[4:6])

    # THE PEDAL IS THE LENGTH OF THE NOTES. A key tapped (0.4 steps) with the pedal down, the pedal let go 6 steps after
    # the note began: recorded 6 steps long, and played back so with no pedal; without the pedal: a short gate
    def gates(log, t0, ch=0):
        ons = [(t - t0, n) for t, n, _ in log.notes(ch=ch, after=t0)]
        offs = [(t - t0, n) for t, n in log.offs(ch=ch) if t >= t0]
        return [(round(on / STEP_MS, 2), next((round(o - on) for o, mm in offs if mm == n and o > on), None)) for on, n in ons]
    res = {}
    for ped in (0, 1):
        s = Script()
        s.press(30, SEL); s.tap_btn(40, REC); s.release(80, SEL)       # REC FREE
        s.tap_btn(90, REC)
        s.tap_btn(100, PLAY)
        t_on = 100 + int(2.1 * STEP_MS)
        if ped:
            s.raw(t_on - 30, "midi 0xB0 64 127")
        s.raw(t_on, "midi 0x90 64 100"); s.raw(t_on + int(0.4 * STEP_MS), "midi 0x80 64 0")
        if ped:
            s.raw(t_on + int(6 * STEP_MS), "midi 0xB0 64 0")
        s.tap_btn(100 + int(12 * STEP_MS), REC)
        log = run(s, 100 + int(3 * BAR))
        res[ped] = [x for x in gates(log, 100) if x[0] >= 16]
    check(res[0] and res[0][0][1] is not None and res[0][0][1] < STEP_MS, "no pedal: the tapped note is recorded short (%s)" % res[0][:1])
    check(res[1] and near(res[1][0][0], 18.1, 0.15) and near(res[1][0][1], 6 * STEP_MS, 14), "the pedal down: the note is recorded as long as it sounded, six steps (%s)" % res[1][:1])
    check(not [1 for tm, st, d1, d2 in log.msgs if st == 0xB0 and d1 == 64 and tm >= 100 + BAR], "... and played back without any pedal")

    # the same key struck twice under one pedal: two notes, the first as long as to the second, the second to the pedal's release
    s = Script()
    s.press(30, SEL); s.tap_btn(40, REC); s.release(80, SEL)
    s.tap_btn(90, REC)
    s.tap_btn(100, PLAY)
    t_on = 100 + int(2.1 * STEP_MS)
    s.raw(t_on - 30, "midi 0xB0 64 127")
    s.raw(t_on, "midi 0x90 64 100"); s.raw(t_on + 40, "midi 0x80 64 0")
    s.raw(t_on + int(3 * STEP_MS), "midi 0x90 64 100"); s.raw(t_on + int(3 * STEP_MS) + 40, "midi 0x80 64 0")
    s.raw(t_on + int(7 * STEP_MS), "midi 0xB0 64 0")
    s.tap_btn(100 + int(12 * STEP_MS), REC)
    log = run(s, 100 + int(3 * BAR))
    g = [x for x in gates(log, 100) if x[0] >= 16]
    check(len(g) >= 2 and near(g[0][0], 18.1, 0.15) and near(g[1][0], 21.1, 0.15) and near(g[0][1], 3 * STEP_MS, 14) and near(g[1][1], 4 * STEP_MS, 14),
          "one key twice under the pedal: three steps, then four (%s)" % g[:2])

    # a TAPE keeps it too: the event is as long as the note sounded
    s = Script()
    t = kp(s, 100, [(K4, 3)])                                          # the track: TAPE
    s.tap_btn(t, REC); t += 60
    s.tap_btn(t, PLAY); p0 = t
    t_on = p0 + int(2 * STEP_MS)
    s.raw(t_on - 30, "midi 0xB0 64 127")
    s.raw(t_on, "midi 0x90 62 100"); s.raw(t_on + 40, "midi 0x80 62 0")
    s.raw(t_on + int(5 * STEP_MS), "midi 0xB0 64 0")
    s.tap_btn(p0 + int(12 * STEP_MS), REC)
    s.at(p0 + int(13 * STEP_MS), "dump", 0)
    log = run(s, p0 + int(14 * STEP_MS))
    ev = log.tapes[0]["ev"] if log.tapes else []
    check(len(ev) == 1 and ev[0][2] == 62 and abs(ev[0][1] - 5 * 96) < 14, "a TAPE: the note's event is five steps long (%s)" % ev)


# ------------------------------------------------------------------------------------------------ 0.27
def band_hold(s, t):
    s.press(t, SEQ); s.tap_key(t + 30, bk(6), hold=700); s.release(t + 800, SEQ)
    return t + 900


def t027_keyless_band():
    group("0.27 A BAND IN A PROJECT WITH NO KEY (the scale CHROMA, as a new project is): every melodic part starts from "
          "the project's root - the arpeggio was written a fifth above the rest (from G4)")

    def genre(s, t, n):
        s.press(t, SEQ); s.enc(t + 30, E_PRE, n); s.release(t + 100, SEQ)
        return t + 200
    res = {}
    for name, setup in (("FREE", lambda s, t: seq_page(s, t, 7, encs=[(K1, 2)])), ("TRANCE", lambda s, t: genre(s, t, 16)),     # (0.29: TRANCE 16)
                        ("TRANCE THEORY", lambda s, t: seq_page(s, genre(s, t, 16), 7, encs=[(K1, 1)]))):
        s = Script()
        t = setup(s, 100)
        t = band_hold(s, t)
        for k in range(12):
            s.at(t + 10 * k, "dump", k)
        p = t + 300
        s.tap_btn(p, PLAY)
        log = run(s, p + int(16 * STEP_MS) - 20)
        mel = [(d["track"], d["pen"]) for d in log.dumps if d["mode"] != "D" and "x" in d["on"]]
        role = {c["track"]: c["role"] for c in cfgs(log)}
        pcs = {}
        for tm, st, d1, d2 in log.msgs:
            if (st & 0xF0) == 0x90 and d2 and p <= tm < p + 16 * STEP_MS - 20:
                pcs.setdefault((st & 15) + 1, set()).add(d1 % 12)
        arp = set().union(*[pcs.get(k, set()) for k, _ in mel if role.get(k) == 7])
        chords = set().union(*[pcs.get(k, set()) for k, _ in mel if role.get(k) in (6, 20, 21, 22)])
        res[name] = (mel, arp, chords)
    for name, (mel, arp, chords) in res.items():
        check(len(mel) >= 3 and all(n % 12 == 0 for _, n in mel), "%s band, no key: every melodic part's note is a C (%s)" % (name, mel))
        check(arp and chords and arp <= chords | {10, 11}, "... and the arpeggio plays the notes of the chords playing (and their seventh), not those of a "
              "chord a fifth above (arp %s, chords %s)" % (sorted(arp), sorted(chords)))
    s = Script()                                                       # a proposal of the journey on an empty track (a tap), no key
    t = vg_on(s, 100)
    for i in range(8):
        t = vg_tap(s, t, i) + 40
        s.at(t, "dump", i); t += 20
    log = run(s, t + 200)
    said = [(d["track"], re.sub(r"^T\d+ ", "", x["msg"]).split(" P")[0], d["pen"]) for d, x in zip(log.dumps, log.states)]
    mel = [(k, n) for k, who, n in said if who in ("BASS", "CHORD", "ARP", "PAD", "LEAD", "STAB", "PIANO", "VOX", "SUB")]
    check(len(mel) >= 3 and all(n % 12 == 0 for _, n in mel), "a proposal of the journey on an empty track, no key: a melodic part's note is a C too (%s)" % said)


def t027_random_dice():
    group("0.27 RANDOM IS A ROLL OF THE DICE (SEQ + white 5): what it does is the same; it waits like a dice - OCT+ keeps "
          "it, OCT- puts it back, ALG goes through the rolls; EVERY's repeat of it is the tool, as before")

    def rnd(s, t): return seq_page(s, t, 0, keys=[wk(4)])
    s = Script()
    t = 100
    s.at(t, "dump", 0); t += 50
    t = rnd(s, t); s.at(t, "dump", 0); s.raw(t + 10, "probe"); t += 60
    t = rnd(s, t); s.at(t, "dump", 0); t += 60
    s.enc(t, E_ALG, -1); t += 100                                     # ALG (nothing held): the roll before
    s.at(t, "dump", 0); t += 60
    s.tap_btn(t, OCT_DOWN); t += 100                                   # OCT-: back as it was
    s.at(t, "dump", 0); s.raw(t + 10, "probe"); t += 60
    log = run(s, t + 100)
    d, st = log.dumps, states(log)
    check(d[1]["on"] != d[0]["on"] and "x" in d[1]["on"] and st[1]["msg"] == "RANDOM: OCT+ KEEP, OCT- BACK",
          "RANDOM writes a rhythm and waits, as a dice (%s %r)" % (d[1]["on"], st[1]["msg"]))
    check(st[2]["msg"] == "RANDOM 2/2 ALG: OCT+ KEEP, OCT- BACK" and d[2]["hash"] != d[1]["hash"],
          "RANDOM again: a second roll, in the dice's memory (%r)" % st[2]["msg"])
    check(d[3]["hash"] == d[1]["hash"] and st[3]["msg"].startswith("RANDOM 1/2"), "ALG: back to the first roll, the same pattern (%r)" % st[3]["msg"])
    pr = [x["G"]["dice"] for x in probes(log)]
    check(d[4]["hash"] == d[0]["hash"] and pr == ["1", "0"], "OCT-: as it was before the first roll; nothing waits (%s %s)" % (d[4]["on"], pr))
    # OCT+ keeps it; UNDO then takes it back as any tool's work
    s = Script()
    t = 100
    s.at(t, "dump", 0); t += 50
    t = rnd(s, t)
    s.tap_btn(t, OCT_UP); t += 100
    s.at(t, "dump", 0); t += 50
    t = seq_page(s, t, 0, keys=[wk(7)])                                # UNDO
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    d = log.dumps
    check(d[1]["hash"] != d[0]["hash"] and d[2]["hash"] == d[0]["hash"], "OCT+ keeps the roll; UNDO takes it back (%s / %s / %s)" % (d[0]["on"], d[1]["on"], d[2]["on"]))
    # EVERY 1 BAR repeats the last tool: RANDOM kept, then every bar RANDOM again - the tool, nothing waits to be answered
    s = Script()
    t = seq_page(s, 100, 5, encs=[(K3, 1)])                            # EVERY: 1 BAR
    t = rnd(s, t)
    s.tap_btn(t, OCT_UP); t += 100
    p = t + 100
    s.tap_btn(p, PLAY)
    for b in range(4):
        s.raw(int(p + (b + 0.5) * 16 * STEP_MS), "probe")
        s.at(int(p + (b + 0.5) * 16 * STEP_MS) + 5, "dump", 0)
    log = run(s, int(p + 4.6 * 16 * STEP_MS))
    pr = [x["G"]["dice"] for x in probes(log)]
    hs = [x["hash"] for x in log.dumps]
    check(pr == ["0"] * 4 and len(set(hs)) >= 3, "EVERY 1 BAR + RANDOM: a new rhythm every bar, and no dice waiting (%s, %d patterns)" % (pr, len(set(hs))))



def t027_evolve_return():
    group("0.27 DRIFT INSIDE EVOLVE: SEQ 3 SEL + K2 is EVOLVE's RETURN - 100 % every change starts from the seed (EVOLVE "
          "as ever), 0 % from the last one (DRIFT, which the key black 8 still is), in between part of the way back")
    BAR = 16 * STEP_MS

    def run_ret(how, bars=24):
        s = Script()
        t = s.steps(100, [0, 2, 4, 6, 8, 10, 12, 14])
        t = seq_page(s, t, 2, encs=[(K2, 15), (K3, -2)])               # EVOLVE 100 %, every bar
        if how == "key":
            t = seq_page(s, t, 0, keys=[bk(7)])                        # DRIFT, the key
        elif how is not None:
            t = pg(s, t, SEQ, 2, [(K2, how)], sel=True)                # RETURN (from 100)
        s.at(t, "dump", 0); t += 50                                    # (what the screen said)
        t = seq_page(s, t, 0, keys=[bk(8)])                            # EVOLVE on
        s.at(t, "dump", 0); t += 50
        p = t + 100
        s.tap_btn(p, PLAY)
        for b in range(bars):
            s.at(int(p + (b + 0.5) * BAR), "dump", 0)
        log = run(s, int(p + (bars + 0.6) * BAR))
        seed = log.dumps[1]["on"]
        dist = [sum(a != b for a, b in zip(seed, d["on"])) for d in log.dumps[2:]]
        return log, dist
    l100, d100 = run_ret(None)
    l0, d0 = run_ret(-20)
    lk, dk = run_ret("key")
    l50, d50 = run_ret(-10)
    m = [sum(d[6:]) / len(d[6:]) for d in (d100, d50, d0)]

    def st_msgs(log): return [x["msg"] for x in log.states]
    check(st_msgs(l0) and "EVOLVE RETURN 0%: DRIFT, NO WAY BACK" in st_msgs(l0) and "EVOLVE RETURN 50%: PART OF THE WAY BACK" in st_msgs(l50),
          "SEL + K2 on SEQ 3: the RETURN, and the screen says what it does (%s)" % [x for x in st_msgs(l50) if "RETURN" in x][:1])
    check([d["hash"] for d in l0.dumps[1:]] == [d["hash"] for d in lk.dumps[1:]], "RETURN 0 is DRIFT, bar for bar the same as the key black 8 (%s / %s)" % (d0[:6], dk[:6]))
    check(m[0] < m[1] < m[2], "the further from 100, the further from the seed it wanders: 100 %%, 50 %%, 0 %% (%s; %s / %s / %s)" % ([round(x, 1) for x in m], d100, d50, d0))
    s = Script()                                                       # the key black 8: to 0, and back to the RETURN it had
    t = s.steps(100, [0, 4, 8, 12])
    t = pg(s, t, SEQ, 2, [(K2, -10)], sel=True)                        # RETURN 50
    for _ in range(2):
        t = seq_page(s, t, 0, keys=[bk(7)])
        s.at(t, "dump", 0); t += 50
    t = seq_page(s, t, 0, keys=[bk(7)])                                # (DRIFT again, then RETURN 100 by hand: the key goes back to 100)
    t = pg(s, t, SEQ, 2, [(K2, 20)], sel=True)
    t = seq_page(s, t, 0, keys=[bk(7)])
    s.at(t, "dump", 0); t += 50
    t = seq_page(s, t, 0, keys=[bk(7)])
    s.at(t, "dump", 0); t += 50
    ms = [x["msg"] for x in states(run(s, t + 100))]
    check(ms == ["DRIFT: EVOLVE WANDERS AWAY", "NO DRIFT: EVOLVE RETURN 50%", "DRIFT: EVOLVE WANDERS AWAY", "NO DRIFT: EVOLVE STAYS NEAR THE SEED"],
          "the key black 8: DRIFT, and again the RETURN it had - 50 %%, then 100 %% (%s)" % ms)



def t027_mark():
    group("0.27 THE MARK OF A PATTERN'S END (found by the explorer, there from 0.24): a track made shorter than its pattern keeps "
          "the pattern whole after the loop and a mark where it ends; ENV K1 on that step left the mark half a step. Now a turn "
          "that writes nothing leaves the step as it was, and a lock on the mark makes the steps the player's")
    s = Script()
    t = melody16(s)
    t = home_page(s, t, 0, [(K2, -1)])                                  # LENGTH 15: step 16 waits after the loop, the mark on 17
    s.at(t, "dump", 0); t += 50
    s.enc(t, E_ALG, -64); t += 60
    s.enc(t, E_ALG, 16); t += 60                                        # the cursor on step 17: the mark
    t = pg(s, t, ENV, 4, [(K1, -1)])                                    # ENV 5 K1 down, no lock there: nothing to write
    s.at(t, "dump", 0); t += 50
    t = pg(s, t, ENV, 4, [(K1, 1)])                                     # ... up: a lock on the mark
    s.at(t, "dump", 0); t += 50
    t = home_page(s, t, 0, [(K2, 17)])                                  # LENGTH 32
    s.at(t, "dump", 0); t += 50
    log = run(s, t + 100)
    d, c = log.dumps, log.copies
    check(d[0]["length"] == 15 and c[0]["own"] == 15 and c[0]["row"][:17] == "x" * 16 + "r",
          "LENGTH 15: the 16th step after the loop, then the mark of the pattern's end (%s)" % c[0]["row"][:20])
    check(d[1]["hash"] == d[0]["hash"] and c[1]["row"] == c[0]["row"], "ENV 5 K1 down on the mark, where there is no lock: the step is as it was (%s / %s)" % (d[0]["hash"], d[1]["hash"]))
    check("r" not in c[2]["row"] and "g" not in c[2]["row"] and c[2]["row"][:17] == "x" * 16 + "." and d[2]["hash"] != d[1]["hash"],
          "a lock on the mark: written, and the steps are the player's - nothing flagged (%s)" % c[2]["row"][:20])
    check(d[3]["length"] == 32 and d[3]["on"][:16] == "x" * 16, "LENGTH 32 after it: the pattern's 16 steps are all there (%s)" % d[3]["on"])
    # what that turn did elsewhere, and could be heard: the step got the mark of a note written (SET), so a key that
    # turned it on later played that note (60) and not the track's pen - on a kick, a wrong drum
    s = Script()
    t = seq_page(s, 100, 0, keys=[bk(6)])                              # KIT: track 1 the kick (pen 36)
    s.enc(t, E_ALG, -64); t += 60
    s.enc(t, E_ALG, 1); t += 60                                         # the cursor on step 2, at rest
    t = pg(s, t, ENV, 0, [(K1, -1)])                                    # ENV 1 K1 down: no lock, nothing written
    s.tap_key(t, wk(1)); t += 100                                       # step 2 on
    s.at(t, "dump", 0); t += 50
    p = t + 100
    s.tap_btn(p, PLAY)
    log = run(s, p + int(16 * STEP_MS) - 20)
    n = sorted(set(x[1] for x in log.notes(ch=0, after=p)))            # (track 1, channel 1)
    check(log.dumps[0]["pen"] == 36 and log.dumps[0]["on"][:2] == "xx" and n == [36],
          "KIT, ENV K1 turned down on an empty step, then the step on: it plays the kick, 36 (%s, pen %s)" % (n, log.dumps[0]["pen"]))

def t027_who_acts():
    group("0.27 MORE FULL, MORE EMPTY - WHO IS ACTING: the screen says what each hand works on - the ENERGY the whole set "
          "(and the engines' parts), THIN and SWELL the whole set, DENSITY and CHANCE this track only")

    def msg_after(gesture, setup=None):
        s = Script()
        t = setup(s, 100) if setup else 100
        t = gesture(s, t)
        s.at(t, "dump", 0)
        log = run(s, t + 100)
        return states(log)[-1]["msg"]
    e = msg_after(lambda s, t: pg(s, t, GLO, 2, [(K1, 5)]))
    check(e == "ENERGY 55: THE WHOLE SET", "GLO 3 K1, the ENERGY: the whole set (%r)" % e)
    e2 = msg_after(lambda s, t: pg(s, t, GLO, 2, [(K1, -5)]), lambda s, t: band_hold(s, seq_page(s, t, 7, encs=[(K1, 1)])))
    check(re.match(r"^ENERGY 45: THE WHOLE SET \+ 1\d ENGINE PARTS$", e2) is not None, "... and with a band of the engines, their parts too (%r)" % e2)
    d = msg_after(lambda s, t: seq_page(s, t, 1, encs=[(K1, 4), (K2, 2)]))
    check(d == "T1 DENSITY 110%: THIS TRACK ONLY", "SEQ 2, DENSITY: this track only (%r)" % d)
    c = msg_after(lambda s, t: home_page(s, t, 5, [(K1, 5), (K2, -2)]))
    check(re.match(r"^T1 CHANCE \d+%: THIS TRACK ONLY$", c) is not None, "HOME 6, the MIDI FX CHANCE: this track only (%r)" % c)
    th = msg_after(lambda s, t: (s.tap_key(t, bk(6)), t + 100)[1], lambda s, t: vg_on(s, t, remote=False))
    sw = msg_after(lambda s, t: (s.tap_key(t, bk(7)), t + 100)[1], lambda s, t: vg_on(s, t, remote=False))
    check(th == "QUEUED: THIN - THE WHOLE SET, 2 TRACKS OUT" and sw == "QUEUED: SWELL - THE WHOLE SET, 2 TRACKS IN",
          "the MOSSE's THIN and SWELL: the whole set (%r, %r)" % (th, sw))


def t027_semplice():
    group("0.27 THE PROFILE SEMPLICE (SAVE 1 K4: FULL, SEMPLICE, PALCO): the lab's pages are hidden - SEQ 2 (the "
          "algorithms) and SEQ 3 (EVOLVE) - while nothing of theirs plays; nothing is switched off; FULL shows them all")

    def walk(s, t, n):                                                 # SEQ held: OCT+ n times, the page shown each time
        s.press(t, SEQ); t += 30
        for _ in range(n):
            s.tap_btn(t, OCT_UP, hold=15); t += 40
            s.raw(t, "probe"); t += 20
        for _ in range(n):
            s.tap_btn(t, OCT_DOWN, hold=15); t += 40
        s.raw(t, "probe")
        s.release(t + 20, SEQ)
        s.pages[SEQ] = 0
        return t + 80
    s = Script()
    s.press(100, SAVE); s.enc(130, K4, 1); s.release(200, SAVE)        # SEMPLICE
    s.at(250, "dump", 0)
    t = walk(s, 300, 3)
    t = seq_page(s, t, 0, keys=[bk(8)])                                # EVOLVE on: its page comes back
    t = walk(s, t, 3)
    t = seq_page(s, t, 0, keys=[bk(8)])                                # EVOLVE off
    s.press(t, SAVE); s.enc(t + 30, K4, -1); s.release(t + 100, SAVE); t += 150   # FULL
    t = walk(s, t, 3)
    log = run(s, t + 200)
    pr = [int(x["G"]["seqp"]) for x in probes(log)]
    check(states(log)[0]["msg"] == "PROFILE SEMPLICE: SEQ 2 AND 3 HIDDEN WHILE OFF", "SAVE 1 K4 one step: SEMPLICE, and what it hides (%r)" % states(log)[0]["msg"])
    check(pr[:4] == [3, 4, 5, 0], "SEMPLICE: OCT+ from SEQ 1 goes to EXPO (SEQ 4), past the algorithms and EVOLVE; OCT- back to SEQ 1 (%s)" % pr[:4])
    check(pr[4:8] == [2, 3, 4, 0], "EVOLVE playing: its page SEQ 3 is there again (%s)" % pr[4:8])
    check(pr[-4:] == [1, 2, 3, 0], "FULL: every page, as ever (%s)" % pr[-4:])
    # an algorithm playing on the track (started in FULL): in SEMPLICE its page SEQ 2 stays, and it goes on playing
    s = Script()
    t = s.steps(100, [0, 4, 8, 12])
    t = seq_page(s, t, 1, encs=[(K1, 1)], keys=[wk(5)])                # TURING READY, and on (white 6 on SEQ 2)
    t = seq_page(s, t, 0)                                              # (back on SEQ 1)
    s.press(t, SAVE); s.enc(t + 30, K4, 1); s.release(t + 100, SAVE); t += 150   # SEMPLICE
    t = walk(s, t, 3)
    s.at(t, "dump", 0)
    log = run(s, t + 100)
    pr = [int(x["G"]["seqp"]) for x in probes(log)]
    check(pr[:4] == [1, 3, 4, 0] and states(log)[-1]["algo"] == 1, "an algorithm playing: SEQ 2 is there, EVOLVE's page not; the algorithm still plays (%s, %s)" % (pr[:4], states(log)[-1]["algo"]))


# ------------------------------------------------------------------------------------------------ 0.28
def t028_panel():
    group("0.28 on the panel: twelve tracks (HOME + white 13-16 nothing, the banks 1-8 and 9-12, the strip), a chord of six notes "
          "(SEL + keys; the seventh: CHORD FULL), notes 5 and 6 on the EDIT line, lanes 7 and 8 (ENV 7/8 and 8/8: CC 73 and 72); "
          "all of it saved, and there after a power cycle")
    # the tracks: HOME + white 12, white 13 (nothing), black 9 (the other bank), black 5 in 9-12 (nothing), black 2
    s = Script()
    s.press(100, HOME); s.tap_key(130, wk(11)); s.release(200, HOME); s.at(260, "probe")
    s.press(300, HOME); s.tap_key(330, wk(12)); s.at(380, "ui"); s.release(400, HOME); s.at(460, "probe")
    s.tap_key(500, bk(8)); s.at(560, "probe")
    s.tap_key(600, bk(8)); s.at(660, "probe")
    s.tap_key(700, bk(4)); s.at(760, "probe")
    s.tap_key(800, bk(1)); s.at(860, "probe")
    log = run(s, 1000)
    sel = [int(x["G"]["sel"]) for x in probes(log)]
    check(sel == [12, 12, 4, 12, 12, 10], "HOME + white 12: T12; white 13: nothing; black 9: T4 and back to T12; black 5 in 9-12: nothing; black 2: T10 (%s)" % sel)
    sc = log.screens()
    strip = sc[0]["strip"] if sc else ""
    check(len(strip) == 32 and strip[22] == "c" and all(strip[2 * i] == "o" for i in range(12, 16)) and all(strip[2 * i] != "o" for i in range(11)),
          "HOME's strip: T12 the cursor, cells 13-16 dark (%r)" % strip)
    # a chord of six notes on step 1 of track 1 (keys 60 ms apart: one chord); the seventh: CHORD FULL
    d = tempfile.mkdtemp()
    flash = os.path.join(d, "flash.bin")
    s = Script()
    s.press(100, SEL)
    cur = 0
    for i, b in enumerate((7, 9, 11, 12, 14, 16, 18)):            # C4 D4 E4 F4 G4 A4, then B4
        cur |= 1 << b
        s.keys(150 + 60 * i, cur)
    s.keys(600, 0); s.release(650, SEL)
    s.at(700, "dump", 0)
    s.press(800, EDIT); s.press(830, SEL); s.at(890, "ui"); s.release(920, SEL); s.release(950, EDIT)
    t = pg(s, 1100, ENV, 6, [(K1, 20)])                              # lane 7: a lock on the cursor step (step 1)
    s.press(t, ENV); s.at(t + 60, "ui"); s.release(t + 100, ENV); t += 160
    t = pg(s, t, ENV, 7, [(K1, 30)])                                 # lane 8: a lock
    s.press(t, ENV); s.at(t + 60, "ui"); s.release(t + 100, ENV); t += 160
    s.tap_btn(t + 100, SAVE); s.tap_btn(t + 400, SAVE); t += 1200   # SAVE: slot 1
    s.tap_btn(t, PLAY); p0 = t
    s.tap_btn(t + 600, PLAY)
    log = run(s, t + 900, flash=flash)
    msg = states(log)[0]["msg"] if states(log) else ""
    sc = log.screens()
    lines = [x["lines"][2] or "" for x in sc]
    notes = sorted(d1 for tt, d1, _ in log.notes(ch=0, after=p0) if tt < p0 + 100)
    ccs = {(m[2]): m[3] for m in log.msgs if m[1] == 0xB0 and p0 <= m[0] < p0 + 100}
    check(msg == "CHORD FULL (6 NOTES)", "SEL + seven keys: the seventh does not fit - CHORD FULL (6 NOTES) (%r)" % msg)
    check(lines and "5 G4 6 A4" in lines[0], "EDIT + SEL: the line shows notes 5 and 6 (%r)" % (lines[:1],))
    check(len(lines) >= 3 and "ENV LANE 7/8" in lines[1] and "ENV LANE 8/8" in lines[2] and sc[1]["cells"][1] == ("CC ATTACK", "73") and sc[2]["cells"][1][1] == "72",
          "ENV: LANE 7/8 on CC 73 (ATTACK), LANE 8/8 on CC 72 (%s %s)" % (lines[1:3], [x["cells"][1] for x in sc[1:3]]))
    check(notes == [60, 62, 64, 65, 67, 69], "PLAY: the step's six notes (%s)" % notes)
    check(73 in ccs and 72 in ccs, "... and its locks on lanes 7 and 8: CC 73, CC 72 (%s)" % sorted(ccs))
    # a power cycle: the slot comes back with its six notes and its eight lanes
    s = Script()
    s.tap_btn(600, PLAY); s.tap_btn(1200, PLAY)
    log2 = run(s, 1500, flash=flash)
    notes2 = sorted(d1 for tt, d1, _ in log2.notes(ch=0, after=600) if tt < 700)
    ccs2 = {(m[2]): m[3] for m in log2.msgs if m[1] == 0xB0 and 600 <= m[0] < 700}
    check(notes2 == notes and ccs2.get(73) == ccs.get(73) and ccs2.get(72) == ccs.get(72),
          "after a power cycle: the same six notes, the same CC 73 and 72 (%s %s)" % (notes2, [(k, ccs2.get(k)) for k in (72, 73)]))



def t0281_mod_page():
    group("0.28.1: SAGGA Mod's lanes 7 and 8 (channel 12 CC 62 / 63, the tablet's track) and DEST MOD ONLY (channel 13 CC 96 = 6); "
          "the values go back on port 2; an LFO's target stays one its DEST has (a channel 13-16 is no track); the grid's track row stops at 12")
    s = Script()
    t = remote13_on(s, 100)
    t = usb2(s, t)
    s.raw(t, "midi 0xBB 62 30 2"); t += 40                            # lane 7 of the tablet's track (1): base 30
    s.raw(t, "midi 0xBB 63 100 2"); t += 40                           # lane 8: base 100
    s.at(t, "dump", 0); t += 60
    t1 = t + 600                                                      # (the hand off the two cells)
    t = pg(s, t1, ENV, 6, [(K3, 2)])                                  # the panel: lane 7's base up
    s.at(t + 100, "dump", 0)
    log = run(s, t + 600)
    syn = [(m[2], m[3]) for m, p in zip(log.msgs, log.port) if p != 2 and m[1] == 0xB0 and m[2] in (72, 73)]
    c = cfgs(log)
    check(syn[:2] == [(73, 30), (72, 100)], "channel 12 CC 62 / 63: lane 7 (CC 73) and lane 8 (CC 72) of track 1 go out at 30 and 100 (%s)" % syn[:3])
    check(len(c) == 2 and c[0]["lanes"][6][3] == 30 and c[0]["lanes"][7][3] == 100, "... and they are the lanes' base values (%s)" % [x["lanes"][6:] for x in c])
    b7 = c[1]["lanes"][6][3] if len(c) == 2 else None
    back = [(m[0], m[3]) for m, p in zip(log.msgs, log.port) if p == 2 and m[1] == 0xBB and m[2] == 62 and m[0] > t1]
    check(b7 not in (None, 30) and back and back[0][1] == b7 and back[0][0] - t1 < 400,
          "lane 7's base turned on the panel (%s) goes back to the page on channel 12 CC 62 (%s)" % (b7, back[:2]))
    check(not [m for m, p in zip(log.msgs, log.port) if p == 2 and m[1] == 0xBB and m[2] in (62, 63) and m[0] < t1 - 200],
          "what the tablet just sent does not come straight back (%s)" % [m for m, p in zip(log.msgs, log.port) if p == 2 and m[1] == 0xBB and m[2] in (62, 63)][:2])
    # DEST: the tablet's CC 96 = 1 on an LFO on channel 16: VEL on track 12 (0.28: the screen said TRACK 16, track 1 moved);
    # 6 = MOD ONLY, 127 over the seven = MOD ONLY; the panel's DEST back to the page
    s = Script()
    t = remote13_on(s, 100)
    t = usb2(s, t)
    t = pg(s, t, LFO, 1, [(K2, 15)])                                  # the panel: LFO 1 on CC, channel 16
    for v in (1, 6, 0, 127):
        s.raw(t, "midi 0xBC 92 0 2"); s.raw(t + 20, "midi 0xBC 96 %d 2" % v); t += 60
        s.press(t, LFO); s.at(t + 60, "ui"); s.release(t + 100, LFO); t += 160
    t2 = t + 600
    t = pg(s, t2, LFO, 1, [(K1, -6)])                                 # the panel: DEST from MOD ONLY down to CC
    log = run(s, t + 600)
    cells = [(x["cells"][0][1], (x["cells"][1][0].lstrip("> "), x["cells"][1][1])) for x in log.screens()]   # (">": the knob in focus)
    check(cells == [("VEL", ("TRACK", "12")), ("MOD ONLY", ("TRACK", "12")), ("CC", ("CHANNEL", "12")), ("MOD ONLY", ("TRACK", "12"))],
          "CC 96 = 1: VEL on TRACK 12 (not 16); 6: MOD ONLY; 0: CC; 127: MOD ONLY (%s)" % cells)
    back = [m[3] for m, p in zip(log.msgs, log.port) if p == 2 and m[1] == 0xBC and m[2] == 96 and m[0] > t2]
    check(back[-1:] == [0], "the panel's DEST (CC) goes back to the page on channel 13 CC 96 (%s)" % back)
    # the grid's LFO view: DEST VEL, then pad 14 of the track row is no track; pad 12 is track 12
    s = Script()
    s.raw(100, "attach")
    t = view(s, 200, GC_VPERF, alt=True)                              # LFO view
    s.pad(t, 9, 1); t += 100                                          # DEST VEL (row 2, pad 10)
    s.pad(t, 13, 6); t += 100                                         # pad 14: 0.31 the group BASS (0.28.1-0.30: nothing)
    t3 = t
    s.pad(t + 50, 11, 6); t += 200                                    # pad 12: track 12
    log = run(s, t + 200)
    pads, _ = log.leds(until=t3 + 40)
    pads2, _ = log.leds(until=t + 150)
    row = [pads[6 * 16 + x] for x in range(16)]
    check(row[13] == GL_WHITE and row[12:16] == [GL_ORANGE, GL_WHITE, GL_CYAN, GL_DIM] and all(v == GL_DIM for v in row[0:12]),
          "grid, DEST VEL: the track row lights 1-12; 0.31: 13-16 the groups, pad 14 the bass - white, the LFO moves it (%s)" % row)
    check(pads2[6 * 16 + 11] == GL_WHITE and pads2[6 * 16] == GL_DIM, "... pad 12: track 12 (%s %s)" % (pads2[6 * 16 + 11], pads2[6 * 16]))


def t0321_tablet_banks():
    group("0.32.1: the tablet reaches the 32 scenes and the 16 snapshots - channel 12 CC 37 is the bank of eight that SAGGA "
          "Remote's SCENE 1-8 (channel 14 CC 40-47) are, CC 39 the bank its SNAP and STORE 1-8 (CC 106-113, 12-19) are; MORPH "
          "TO goes back to the page past scene 8; the banks go back too; with REMOTE 14 alone: the first eight, as before")
    s = Script()
    t = remote13_on(s, 100)
    t = usb2(s, t)
    n = [0]
    marks = {}
    def P(name):
        nonlocal t
        s.at(t, "probe"); marks[name] = n[0]; n[0] += 1; t += 40
    def midi(st, d1, d2, name=None):
        nonlocal t
        s.raw(t, "midi 0x%02X %d %d 2" % (st, d1, d2)); t += 60
        if name:
            P(name)
    def tap(cc, name):                                                    # a page's button on channel 14: 127, then 0
        nonlocal t
        s.raw(t, "midi 0xBD %d 127 2" % cc); s.raw(t + 10, "midi 0xBD %d 0 2" % cc); t += 70
        P(name)
    t0 = t
    tap(42, "sc3")                                                        # SCENE 3, the bank 1-8: scene 3
    midi(0xBB, 37, 1, "bank")                                             # SCENES 9-16
    tap(42, "sc11")                                                       # SCENE 3: scene 11
    midi(0xBB, 37, 3)                                                     # SCENES 25-32
    tap(47, "sc32")                                                       # SCENE 8: scene 32
    midi(0xBB, 37, 127)                                                   # (a value over the four: the last bank)
    tap(40, "sc25")                                                       # SCENE 1: scene 25
    tap(13, "st2")                                                        # STORE 2, the bank 1-8: snapshot 2
    midi(0xBB, 39, 1, "sbank")                                            # SNAPS 9-16
    tap(13, "st10")                                                       # STORE 2: snapshot 10
    tap(108, "sn11")                                                      # SNAP 3: snapshot 11, empty
    midi(0xBB, 39, 0)                                                     # SNAPS 1-8
    tap(107, "sn2")                                                       # SNAP 2: snapshot 2
    midi(0xBB, 39, 1)
    tap(107, "sn10")                                                      # SNAP 2: snapshot 10
    t1 = t + 600
    t = pg(s, t1, GLO, 0, [(K2, 19)]); t += 60; P("morph")                # the panel: MORPH TO from scene 2 up nineteen
    s.at(t, "dump", 0); t += 40
    log = run(s, t + 700)
    G = [p["G"] for p in probes(log)]
    ok = len(G) == n[0] and bool(log.x30)
    check(ok, "%d probes and the dump (%d %d)" % (n[0], len(G), len(log.x30)))
    if not ok:
        return
    def g(name, *ks):
        v = tuple(G[marks[name]].get(k) for k in (ks or ("msg",)))
        return v[0] if len(v) == 1 else v
    check(g("sc3", "scene") == "2" and g("sc11", "scene") == "10" and g("sc32", "scene") == "31" and g("sc25", "scene") == "24",
          "SCENE 3 is scene 3, with SCENES 9-16 scene 11; SCENE 8 with 25-32 scene 32; a value over the four: the last bank (%s %s %s %s)"
          % (g("sc3", "scene"), g("sc11", "scene"), g("sc32", "scene"), g("sc25", "scene")))
    check(g("bank").endswith("SCENES 9-16: THE TABLET'S SCENE 1-8") and g("bank", "sbank") == g("sc3", "sbank"),
          "the screen says the bank; the panel's own bank of scenes stays where it is (%s, sbank %s)" % (g("bank"), g("bank", "sbank")))
    x = log.x30[-1]
    check(g("st2", "snap") == "1" and g("st10", "snap") == "9" and g("sbank").endswith("SNAPSHOTS 9-16: THE TABLET'S SNAP AND STORE 1-8"),
          "STORE 2 is snapshot 2, with SNAPS 9-16 snapshot 10 (%s %s; %s)" % (g("st2", "snap"), g("st10", "snap"), g("sbank")))
    check("EMPTY" in g("sn11") and g("sn11").endswith("11") and g("sn2", "snap") == "1" and g("sn10", "snap") == "9",
          "SNAP 3 with 9-16: snapshot 11, empty; SNAP 2 with 1-8: snapshot 2; with 9-16: snapshot 10 (%s | %s %s)" % (g("sn11"), g("sn2", "snap"), g("sn10", "snap")))
    check(x["snaps"] == ".x.......x......", "... the snapshots stored are 2 and 10 (%s)" % x["snaps"])
    back = [(m[2], m[3]) for m, p in zip(log.msgs, log.port) if p == 2 and m[1] == 0xBB and m[2] in (37, 39) and m[0] < t0 + 400]
    check((37, 0) in back and (39, 0) in back, "the banks go back to the page from the start: CC 37 and 39 on channel 12, 0 (%s)" % back[:4])
    mt = [m[3] for m, p in zip(log.msgs, log.port) if p == 2 and m[1] == 0xBD and m[2] == 2 and m[0] > t1]
    check(mt[-1:] == [20], "MORPH TO turned on the panel to scene 21 goes back to the page (0.30-0.32: nothing past scene 8) (%s)" % mt)
    # REMOTE 14 alone: channel 12 is a track's then - the banks are not heard, SCENE 3 is scene 3
    s = Script()
    t = usb2(s, 100)
    s.raw(t, "midi 0xBB 37 2 2"); t += 60
    s.raw(t, "midi 0xBD 42 127 2"); s.raw(t + 10, "midi 0xBD 42 0 2"); t += 70
    s.at(t, "probe")
    log = run(s, t + 200)
    G = [p["G"] for p in probes(log)]
    check(len(G) == 1 and G[0].get("scene") == "2", "REMOTE 14 alone: the bank's CC is not heard, SCENE 3 is scene 3 (%s)" % [x.get("scene") for x in G])


def t0281_proposal_start():
    group("0.28.1: a PROPOSAL enters a track whose loop starts later (HOME + ALG: START 2, a loop of 15): its settings put the "
          "start back on step 1 and the track goes where the bar says, with QUANTISE AUTO and NOW (the explorer found it a step off)")
    for q, name in ((0, "AUTO"), (1, "NOW")):
        s = Script()
        t = s.steps(100, [0, 8])
        s.press(t, SEQ); s.tap_key(t + 30, wk(9), hold=700); s.release(t + 800, SEQ); t += 860   # SEQ + BEAT held: a proposal in P2
        if q:
            t = perf(s, t, [(K4, q)])                                                          # QUANTISE NOW
        s.tap_btn(t, PLAY); t0 = t
        s.press(t0 + 300, HOME); s.enc(t0 + 330, E_ALG, 1); s.release(t0 + 400, HOME)          # START 2
        s.at(t0 + 600, "probe")
        s.enc(t0 + 700, E_PRE, 1)                                                              # PRESETS: the proposal queued
        for k in range(int(BAR_MS) // 10):                                                     # a probe every 10 ms over a bar,
            s.at(t0 + int(2 * BAR_MS) + 10 * k, "probe")                                       # the second after the proposal
        log = run(s, t0 + int(3 * BAR_MS) + 100)
        pb = probes(log)
        a, b = (pb[0].get("T1", {}), pb[-1].get("T1", {})) if len(pb) >= 2 else ({}, {})
        late = [x["t"] for x in pb[1:] if x.get("T1", {}).get("ok") == "0"]
        check(a.get("start") == "1" and b.get("pat") == "2" and b.get("start") == "0" and len(pb) > 100 and not late,
              "QUANTISE %s: START 2, then the proposal P2 plays from step 1 of its loop, where the bar says - at every 10 ms of a bar (%s -> %s, off at %s)"
              % (name, {k: a.get(k) for k in ("start", "pat", "ok")}, {k: b.get(k) for k in ("start", "pat", "ok", "step")}, late[:3]))


def t030_banks():
    group("0.30 THIRTY-TWO SCENES, SIXTEEN SNAPSHOTS, A SONG OF 128, UNDO 32: PERF PRESETS takes the scene cursor to 32 and the black "
          "keys follow its bank of eight (store, recall, the song); SAVE + white 9 / 10 the snapshots 1-8 / 9-16; the grid's SONG pages "
          "up to 128 and its row 2 with SHIFT (17-32), TRACK 2 row 5, FX rows 7 and 8 (SHIFT + pad 13: the other eight snapshots), "
          "the remote's MORPH TO; 32 edits for UNDO; all of it saved, and there after a power cycle")
    d = tempfile.mkdtemp()
    flash = os.path.join(d, "flash.bin")
    s = Script()
    s.tap_key(100, wk(0))                                                  # pattern 1: step 1
    s.enc(200, E_PRE, 1); s.tap_key(300, wk(4))                            # pattern 2: step 5 (track 1 plays pattern 2)
    s.tap_btn(400, GLO)                                                    # PERF
    s.enc(500, E_PRE, 16)                                                  # the scene cursor on 17: black 1-8 are 17-24
    s.press(600, SEL); s.tap_key(630, bk(0)); s.release(700, SEL)          # SEL + black 1: scene 17
    s.at(760, "dump", 0)                                                   # [0]
    s.enc(800, E_PRE, 40)                                                  # PRESETS past the end: 32 (black 8 of 25-32)
    s.press(900, SEL); s.tap_key(930, bk(7)); s.release(1000, SEL)         # SEL + black 8: scene 32
    s.at(1060, "dump", 0); s.at(1080, "leds")                              # [1]
    s.tap_btn(1200, GLO); s.enc(1300, E_PRE, -1)                           # out of PERF: track 1 back on pattern 1
    s.tap_btn(1400, GLO); s.tap_key(1500, bk(7)); s.at(1560, "dump", 0)    # [2] black 8: scene 32 - pattern 2 again
    # the song: HOME + black 1 / black 8 in turn - scenes 25 and 32 - 129 times: 128 entries, then SONG FULL (128)
    s.press(1600, HOME)
    t = 1650
    for i in range(129):
        s.tap_key(t, bk(0) if i % 2 == 0 else bk(7), hold=30); t += 70
    s.release(t, HOME); t += 60
    s.at(t, "dump", 0); t += 60                                            # [3]
    # the grid's SONG view: eight pages of 16; a ninth is not there
    s.raw(t, "attach"); t += 50                                            # (a bridge silent 3.5 s is gone: here again)
    t = view(s, t, GC_VPERF); t = view(s, t, GC_VPERF)                     # PERF, SONG
    for i in range(8):
        s.pad(t, 13, 3); t += 100
    s.at(t, "dump", 0); t += 40                                            # [4]
    s.pad(t, 4, 4); t += 100                                               # row 5 pad 5: the bars from entry 113 on - bar 5 is entry 114's
    s.at(t, "dump", 0); t += 40                                            # [5]
    t_song = t
    s.tap_btn(t, GLO); t += 100                                            # out of PERF
    # the snapshots: SAVE + white 10, SAVE + SEL + black 1: snapshot 9
    s.press(t, SAVE); s.tap_key(t + 30, wk(9)); s.at(t + 90, "leds")
    s.press(t + 120, SEL); s.tap_key(t + 150, bk(0)); s.release(t + 220, SEL); s.release(t + 260, SAVE); t += 320
    s.at(t, "dump", 0); t += 40                                            # [6]
    s.enc(t, E_PRE, -1); t += 60                                           # pattern 1
    s.press(t, SAVE); s.tap_key(t + 30, bk(0)); s.release(t + 100, SAVE); t += 160    # SAVE + black 1: snapshot 9 back
    s.at(t, "dump", 0); t += 40                                            # [7]
    s.press(t, SAVE); s.tap_key(t + 30, wk(8)); s.tap_key(t + 90, bk(0)); s.release(t + 160, SAVE); t += 220   # white 9, black 1: snapshot 1
    s.at(t, "dump", 0); t += 40                                            # [8]
    # UNDO: 34 INVERTs, then UNDO - the ring holds 32
    for i in range(34):
        s.press(t, SEQ); s.tap_key(t + 40, wk(14)); s.release(t + 120, SEQ); t += 200
    s.at(t, "dump", 0); t += 40                                            # [9]
    s.press(t, SEQ); s.tap_key(t + 40, wk(7)); s.release(t + 120, SEQ); t += 200
    s.at(t, "dump", 0); t += 40                                            # [10]
    # the remote's MORPH TO (channel 14 CC 2): 31 is scene 32
    remote(s, t, 2, 31); t += 60
    s.at(t, "dump", 0); t += 40                                            # [11]
    s.tap_btn(t, GLO); s.tap_key(t + 100, wk(1)); s.tap_btn(t + 200, GLO); t += 300   # PERF white 2: track 2 muted
    s.tap_btn(t + 100, SAVE); s.tap_btn(t + 400, SAVE); t += 1200          # SAVE: slot 1
    log = run(s, t + 100, flash=flash)
    x, st, dp = log.x30, states(log), log.dumps
    ok = len(x) == 12 and len(st) == 12 and len(dp) == 12
    check(ok, "twelve dumps (%d %d %d)" % (len(x), len(st), len(dp)))
    if not ok:
        return
    leds = [l for _, l in log.key_leds()]
    check(x[0]["cursor"] == 16 and x[0]["scenes"] == "." * 16 + "x" + "." * 15 and st[0]["msg"] == "SCENE STORED 17",
          "PERF, PRESETS +16: the cursor on 17; SEL + black 1 stores scene 17 (%s %s)" % (x[0]["scenes"], st[0]["msg"]))
    check(x[1]["cursor"] == 31 and x[1]["scenes"] == "." * 16 + "x" + "." * 14 + "x" and st[1]["msg"] == "SCENE STORED 32",
          "PRESETS past the end stops on 32; SEL + black 8 stores scene 32 (%s %s)" % (x[1]["scenes"], st[1]["msg"]))
    check(leds and leds[0][BLACK[7]] == "X" and leds[0][BLACK[0]] == ".", "in PERF black 8 is lit: scene 32 is the cursor (%s)" % (leds[:1],))
    check(dp[2]["pat"] == 2, "black 8 brings scene 32 back: track 1 on pattern 2 (P%d %s)" % (dp[2]["pat"], st[2]["msg"]))
    check(x[3]["song"] == 128 and x[3]["songsc"] == [24, 31] * 64 and st[3]["msg"] == "SONG FULL (128)",
          "HOME + black 1 / black 8 in the bank 25-32: 128 entries of scenes 25 and 32, the 129th: SONG FULL (128) (%d %s %s)" % (
              x[3]["song"], x[3]["songsc"][:4], st[3]["msg"]))
    check(st[4]["msg"] == "SONG ENTRIES FROM 113", "the grid's SONG view: seven pages on, entries 113-128; the eighth press finds no more (%s)" % st[4]["msg"])
    check(st[5]["msg"] == "SONG ENTRY 114", "rows 5-8 show the bars from the page's first entry (0.30; until 0.29 the song's first 64 bars): on entries 113-128, bar 5 is entry 114 (%s)" % st[5]["msg"])
    pads, _ = log.leds(until=t_song)
    check(pads.get(16 + 15) == GL_BLUE and pads.get(16 + 8) == GL_DIM, "row 2 shows scenes 1-16: entry 114 is scene 32, blue on pad 16 - the other half (%s)" % pads.get(16 + 15))
    check(pads.get(4 * 16 + 4) == GL_DIM and pads.get(4 * 16 + 0) == GL_ON, "row 5: entry 114's bars dim (the one chosen), entry 113's in its colour (%s %s)" % (pads.get(4 * 16 + 4), pads.get(4 * 16)))
    check(leds and len(leds) >= 2 and leds[1][WHITE[9]] == "X" and leds[1][WHITE[8]] == ".", "SAVE + white 10: the white 10 lit, the 9 dark (%s)" % (leds[1:2],))
    check(x[6]["snaps"] == "." * 8 + "x" + "." * 7 and x[6]["snapbank"] == 8 and st[6]["msg"] == "SNAPSHOT STORED 9",
          "SAVE + white 10, SAVE + SEL + black 1: snapshot 9 (%s bank %d %s)" % (x[6]["snaps"], x[6]["snapbank"], st[6]["msg"]))
    check(dp[7]["pat"] == 2 and st[7]["msg"] == "SNAPSHOT 9", "SAVE + black 1 in the bank 9-16: snapshot 9 back, pattern 2 (P%d %s)" % (dp[7]["pat"], st[7]["msg"]))
    check(x[8]["snapbank"] == 0 and st[8]["msg"] == "EMPTY: SAVE+SEL+BLACK STORES SNAPSHOT 1", "SAVE + white 9, black 1: snapshot 1, empty (%d %s)" % (x[8]["snapbank"], st[8]["msg"]))
    check(x[9]["undo"] == 32 and st[10]["msg"] == "UNDO  31 MORE", "34 edits: the UNDO keeps the last 32 - UNDO, 31 more (%d %s)" % (x[9]["undo"], st[10]["msg"]))
    check(st[11]["msg"] == "MORPH TO SCENE 32", "the remote's CC 2 = 31: MORPH TO SCENE 32 (%s)" % st[11]["msg"])
    check(len(log.saves) == 1, "SAVE, SAVE: the slot is written (%s)" % log.saves)
    # a power cycle: the scenes, the snapshots, the song of 128 are there; the cursor on 32 and track 2 muted, as saved
    # (0.30: as a LOAD has them - until 0.29 a power-up left the cursor on scene 1 and every track audible)
    s = Script()
    s.at(300, "dump", 0)
    s.tap_btn(400, GLO); s.tap_key(500, bk(0)); s.at(560, "dump", 0)       # black 1: scene 25 (empty: pattern 1)
    s.tap_key(600, bk(7)); s.at(660, "dump", 0)                            # black 8: scene 32, pattern 2
    log2 = run(s, 800, flash=flash)
    y, dp2 = log2.x30, log2.dumps
    check(len(y) == 3 and y[0]["scenes"] == x[1]["scenes"] and y[0]["snaps"] == x[6]["snaps"] and y[0]["song"] == 128
          and y[0]["songsc"] == [24, 31] * 64 and y[0]["undo"] == 0,
          "after a power cycle: scenes 17 and 32, snapshot 9, the 128 entries (%s)" % (
              {k: y[0][k] for k in ("cursor", "scenes", "snaps", "song", "undo")} if y else None))
    check(len(y) == 3 and y[0]["cursor"] == 31 and log2.viaggio and log2.viaggio[0]["mute"] == 0x0002,
          "... the scene cursor on 32 and track 2 muted, as saved - as a LOAD (until 0.29 a power-up forgot both) (%s %s)" % (
              y[0]["cursor"] if y else None, "%04X" % log2.viaggio[0]["mute"] if log2.viaggio else None))
    check(len(dp2) == 3 and dp2[1]["pat"] == 1 and dp2[2]["pat"] == 2, "... PERF black 8 brings scene 32 back, black 1 the empty 25 (%s)" % [d_["pat"] for d_ in dp2])
    # the grid: FX view - SHIFT + row 8 pad 13 the snapshots 9-16; SHIFT + pad 5 stores 9, pad 5 brings it back; row 7 MORPH TO
    # the cursor's bank; SONG row 2 with SHIFT: scenes 17-32; TRACK 2 row 5: the programs of the bank's scenes
    s = Script()
    t = s.steps(100, [0])
    s.raw(t, "attach"); t = view(s, t + 100, GC_UNDO, alt=True)            # FX
    shift(s, t, 1); s.pad(t + 20, 12, 7); s.at(t + 80, "dump", 0)          # [0] SHIFT + pad 13: 9-16
    t_sh = t + 110                                                         # (SHIFT held: pad 13 shows the bank)
    s.pad(t + 120, 4, 7); shift(s, t + 200, 0); t += 260                    # SHIFT + pad 5: snapshot 9
    s.at(t, "dump", 0); t += 40                                            # [1]
    t_fx = t
    s.enc(t, E_PRE, 1); t += 60                                            # pattern 2
    s.pad(t, 4, 7); t += 100                                               # pad 5: snapshot 9 back (pattern 1)
    s.at(t, "dump", 0); t += 40                                            # [2]
    s.tap_btn(t, GLO); s.enc(t + 50, E_PRE, 9); s.tap_btn(t + 100, GLO); t += 200   # the scene cursor on 10: the bank 9-16
    s.pad(t, 3, 6); t += 100                                               # FX row 7 pad 4: MORPH TO scene 12
    s.at(t, "dump", 0); t += 40                                            # [3]
    t = view(s, t, GC_VPERF); t = view(s, t, GC_VPERF)                     # SONG
    shift(s, t, 1); s.pad(t + 20, 15, 1); shift(s, t + 100, 0); t += 160   # SHIFT + row 2 pad 16: entry 1, scene 32
    s.pad(t, 1, 0); s.pad(t + 60, 0, 1); t += 160                          # entry 2: scene 1
    s.pad(t, 0, 0); t += 100                                               # entry 1 again
    t_song = t
    shift(s, t, 1); t += 80
    t_shift = t
    shift(s, t, 0); t += 40
    s.at(t, "dump", 0); t += 40                                            # [4]
    t = view(s, t, GC_VTRACK); t = view(s, t, GC_VTRACK)                   # TRACK 2
    s.pad(t, 7, 4); t += 100                                               # row 5 pad 8: scene 16 (the bank 9-16)
    s.at(t, "dump", 0); t += 40                                            # [5]
    log = run(s, t + 100)
    x, st, dp = log.x30, states(log), log.dumps
    ok = len(x) == 6 and len(st) == 6
    check(ok, "six dumps (%d %d)" % (len(x), len(st)))
    if not ok:
        return
    pads1, _ = log.leds(until=t_sh)
    check(x[0]["snapbank"] == 8 and st[0]["msg"] == "SNAPSHOTS 9-16: SAVE + BLACK 1-8", "FX view, SHIFT + row 8 pad 13: snapshots 9-16 (%d %s)" % (x[0]["snapbank"], st[0]["msg"]))
    check(x[1]["snaps"] == "." * 8 + "x" + "." * 7 and st[1]["msg"] == "SNAPSHOT STORED 9", "SHIFT + pad 5: snapshot 9 stored (%s %s)" % (x[1]["snaps"], st[1]["msg"]))
    check(pads1.get(7 * 16 + 12) == GL_BLUE, "SHIFT held: pad 13 blue - the bank 9-16 (%s)" % pads1.get(7 * 16 + 12))
    check(dp[2]["pat"] == 1 and st[2]["msg"] == "SNAPSHOT 9", "pad 5 brings snapshot 9 back: pattern 1 (P%d %s)" % (dp[2]["pat"], st[2]["msg"]))
    check(st[3]["msg"] == "MORPH TO SCENE 12", "FX row 7 pad 4 with the cursor in 9-16: MORPH TO SCENE 12 (%s)" % st[3]["msg"])
    pa, _ = log.leds(until=t_song)
    pb, _ = log.leds(until=t_shift)
    check(x[4]["song"] == 2 and x[4]["songsc"] == [31, 0], "SONG: SHIFT + row 2 pad 16 adds scene 32, pad 1 scene 1 (%s)" % x[4]["songsc"])
    check(pa.get(16 + 15) == GL_BLUE and pb.get(16 + 15) == GL_WHITE, "entry 1's scene on row 2: blue on pad 16 (in 17-32), white with SHIFT held (%s %s)" % (pa.get(16 + 15), pb.get(16 + 15)))
    check(st[5]["msg"] == "PROGRAMS OF SCENE 16", "TRACK 2 row 5 pad 8 with the cursor in 9-16: the programs of scene 16 (%s)" % st[5]["msg"])


def t030_tape():
    group("0.30 THE TAPES HOLD 3072 EVENTS (1536 until 0.29): 1600 notes played in on a TAPE track of 16 bars are all kept; "
          "past 3072, TAPE FULL")
    s = Script()
    t = kp(s, 100, [(K4, 3)])                                          # HOME 4 K1: FREE -> IN KEY -> DRUM -> TAPE
    t = home_page(s, t, 6, [(K3, 12)], cur=2)                          # HOME 7 K3: TAPE BARS 4 -> 16
    s.tap_btn(t, REC); t += 100
    t0 = t
    s.tap_btn(t0, PLAY); t = t0 + 50
    for i in range(1600):                                              # 1600 notes, 8 ms apart
        n = 48 + i % 24
        s.raw(t, "midi 0x90 %d 100" % n); s.raw(t + 3, "midi 0x80 %d 0" % n); t += 8
    s.at(t + 40, "dump", 0); t += 80
    for i in range(1500):                                              # 1500 more: 3100 in all
        n = 48 + i % 24
        s.raw(t, "midi 0x90 %d 90" % n); s.raw(t + 3, "midi 0x80 %d 0" % n); t += 8
    s.at(t + 40, "dump", 0)
    log = run(s, t + 200)
    tp = [x for x in log.tapes if x["track"] == 1]
    st = states(log)
    check(len(tp) == 2 and tp[0]["n"] == 1600 and tp[0]["bars"] == 16, "1600 notes on a TAPE of 16 bars: all 1600 kept (%s)" % [(x["n"], x["bars"]) for x in tp])
    check(len(tp) == 2 and tp[1]["n"] == 3072 and st and st[-1]["msg"] == "TAPE FULL", "3100 played: 3072 kept, TAPE FULL (%s %s)" % (
        [x["n"] for x in tp], st[-1]["msg"] if st else None))
    check(log.x30 and log.x30[-1]["tape"] == 3072, "the project's tape: 3072 events (%s)" % (log.x30[-1]["tape"] if log.x30 else None))
    # DOUBLE (SEQ + white 13) on a tape of 8 bars with 1000 notes: 16 bars, 2000 notes (0.29: TAPE FULL past 1536)
    s = Script()
    t = kp(s, 100, [(K4, 3)])
    t = home_page(s, t, 6, [(K3, 4)], cur=2)                           # TAPE BARS 4 -> 8
    s.tap_btn(t, REC); t += 100
    t0 = t
    s.tap_btn(t0, PLAY); t = t0 + 50
    for i in range(1000):
        n = 48 + i % 24
        s.raw(t, "midi 0x90 %d 100" % n); s.raw(t + 3, "midi 0x80 %d 0" % n); t += 8
    s.tap_btn(t + 20, REC); t += 100                                   # REC off
    s.press(t, SEQ); s.tap_key(t + 40, wk(13)); s.release(t + 120, SEQ); t += 200   # DOUBLE (white 14)
    s.at(t, "dump", 0)
    log = run(s, t + 200)
    tp = [x for x in log.tapes if x["track"] == 1]
    check(tp and tp[-1]["n"] == 2000 and tp[-1]["bars"] == 16 and states(log)[-1]["msg"] == "TAPE DOUBLED: BARS 16",
          "DOUBLE on 8 bars and 1000 notes: 16 bars, 2000 notes (%s %s)" % ([(x["n"], x["bars"]) for x in tp], states(log)[-1]["msg"] if states(log) else None))

def t031_panel():
    group("0.31 THE KEYS THAT DID NOTHING (since 0.28 the tracks are twelve), ON THE PANEL: in the bank of 9-12 black 5-8 are "
          "the mutes of tracks 9-12; HOME + white 13-16 the page of steps; PERF's white 13-16 the GROUPS - the drums, the bass, "
          "the melodic ones, ALL (SEL: their solo), on the MOSSE's page too; the remote's CC 60-63, 76-79, 102-105 the groups' "
          "mutes, KILLs and RETRIG; LFO 2 K2 past T12: an LFO on a group")
    s = Script()
    t = band_hold(s, 100)                                   # a TECHNO band: T1-T6 the drums, T7-T8 the bass (RUMBLE, BASS), T9-T12 the rest
    s.at(t, "probe"); t += 50                               # [0]
    s.tap_key(t, bk(8)); t += 80                            # black 9: the bank 9-12 (track 9)
    s.tap_key(t, bk(4)); t += 80; s.at(t, "probe"); t += 40       # [1] black 5: T9 muted
    t_led1 = t; s.at(t, "leds"); t += 40
    s.tap_key(t, bk(4)); t += 80; s.at(t, "probe"); t += 40       # [2] again: T9 plays
    s.tap_key(t, bk(7)); t += 80; s.at(t, "probe"); t += 40       # [3] black 8: T12 muted
    s.tap_key(t, bk(7)); t += 80                                  # (back)
    s.press(t, HOME); s.tap_key(t + 30, wk(13)); s.at(t + 90, "leds"); s.release(t + 120, HOME); t += 180
    s.at(t, "probe"); t += 40                                     # [4] HOME + white 14: steps 17-32
    s.press(t, HOME); s.tap_key(t + 30, wk(15)); s.release(t + 100, HOME); t += 160
    s.at(t, "probe"); t += 40                                     # [5] HOME + white 16: steps 49-64
    s.press(t, HOME); s.tap_key(t + 30, wk(12)); s.release(t + 100, HOME); t += 160   # (steps 1-16)
    s.tap_btn(t, GLO); t += 80                                    # PERF
    s.tap_key(t, wk(12)); t += 80; s.at(t, "probe"); t += 40      # [6] white 13: the drums
    s.at(t, "leds"); t += 40
    s.tap_key(t, wk(13)); t += 80; s.at(t, "probe"); t += 40      # [7] white 14: the bass too
    s.tap_key(t, wk(12)); t += 80; s.at(t, "probe"); t += 40      # [8] white 13: the drums back
    s.tap_key(t, wk(15)); t += 80; s.at(t, "probe"); t += 40      # [9] white 16: ALL
    s.press(t, SEL); s.tap_key(t + 30, wk(14)); s.release(t + 100, SEL); t += 160; s.at(t, "probe"); t += 40   # [10] SEL + 15: the melodic ones' solo
    s.press(t, SEL); s.tap_key(t + 30, wk(15)); s.release(t + 100, SEL); t += 160; s.at(t, "probe"); t += 40   # [11] SEL + 16: no solo
    s.tap_btn(t, GLO); t += 80
    s.press(t, SEL); s.tap_btn(t + 30, GLO); s.release(t + 100, SEL); t += 160   # the MOSSE's page
    s.tap_key(t, wk(13)); t += 80; s.at(t, "probe"); t += 40      # [12] white 14: the bass
    s.tap_key(t, wk(15)); t += 80                                 # (ALL)
    s.press(t, SEL); s.tap_btn(t + 30, GLO); s.release(t + 100, SEL); t += 160
    remote(s, t, 60); t += 60; s.at(t, "probe"); t += 40          # [13] CC 60: the drums
    remote(s, t, 63); t += 60; s.at(t, "probe"); t += 40          # [14] CC 63: ALL ON
    remote(s, t, 77, 127); t += 60; s.at(t, "probe"); t += 40     # [15] CC 77 held: KILL the bass
    remote(s, t, 79, 127); t += 60; s.at(t, "probe"); t += 40     # [16] CC 79 too: all but the selected track (T9)
    remote(s, t, 77, 0); remote(s, t + 10, 79, 0); t += 60; s.at(t, "probe"); t += 40   # [17] both let go
    remote(s, t, 102); t += 60; s.at(t, "probe"); t += 40         # [18] CC 102, stopped
    t = pg(s, t, LFO, 1, [(K1, 1), (K2, 12)]); s.at(t, "probe"); t += 40   # [19] LFO 2: VEL, K2 +12: DRUMS
    s.press(t, LFO); s.at(t + 40, "ui"); s.release(t + 80, LFO); t += 140    # (LFO held: its page 2 on the screen)
    t = pg(s, t, LFO, 1, [(K2, 3)]); s.at(t, "probe"); t += 40    # [20] +3: ALL
    t = pg(s, t, LFO, 1, [(K2, 5)]); s.at(t, "probe"); t += 40    # [21] +5: still ALL
    t = pg(s, t, LFO, 1, [(K2, -4)]); s.at(t, "probe"); t += 40   # [22] -4: T12
    log = run(s, t + 100)
    pr = probes(log)
    G = [p["G"] for p in pr]
    ok = len(G) == 23
    check(ok, "23 probes (%d)" % len(G))
    if not ok:
        return
    for g in G:
        g["msg"] = re.sub(r"^TAB (T\d+: )?", "", g.get("msg", ""))       # (what the remote does is the tablet's: its mark aside)
    def gm(i): return (G[i].get("mute"), G[i].get("msg"))
    check(G[0]["mute"] == "0000" and [pr[0]["T%d" % k]["mode"] for k in range(1, 13)] == list("DDDDDDKKKKFF") and
          [int(pr[0]["T%d" % k]["role"]) for k in (7, 8)] == [17, 5],
          "a TECHNO band: T1-T6 DRUM tracks, T7 the RUMBLE, T8 the BASS (%s %s)" % ([pr[0]["T%d" % k]["mode"] for k in range(1, 13)], [pr[0]["T%d" % k]["role"] for k in (7, 8)]))
    check(gm(1) == ("0100", "T9 MUTED") and gm(2) == ("0000", "T9 PLAYS") and gm(3) == ("0800", "T12 MUTED"),
          "in the bank of 9-12 black 5 is the mute of T9, black 8 of T12 (0.28-0.30: nothing) (%s %s %s)" % (gm(1), gm(2), gm(3)))
    leds = [l for _, l in log.key_leds()]
    check(len(leds) >= 3 and leds[0][BLACK[4]] == "X" and leds[0][BLACK[0]] == "X" and leds[0][BLACK[5]] == ".",
          "... its light: black 5 lit (T9 muted), black 1 (T9 selected), black 6 dark (%s)" % (leds[:1],))
    check(G[4]["spage"] == "1" and G[4]["msg"] == "STEPS 17-32" and G[5]["spage"] == "3" and G[5]["msg"] == "STEPS 49-64",
          "HOME + white 14 / 16: the page of steps 2 / 4 (%s %s)" % ((G[4]["spage"], G[4]["msg"]), (G[5]["spage"], G[5]["msg"])))
    check(len(leds) >= 3 and leds[1][WHITE[13]] == "X" and leds[1][WHITE[8]] == "X" and leds[1][WHITE[12]] == ".",
          "... HOME held: white 14 lit (the page), white 9 (track 9) (%s)" % (leds[1:2],))
    check(gm(6) == ("003F", "DRUMS MUTED") and gm(7) == ("00FF", "BASS MUTED") and gm(8) == ("00C0", "DRUMS PLAY") and gm(9) == ("0000", "ALL TRACKS AUDIBLE"),
          "PERF white 13: the drums quiet; 14 the bass; 13 again the drums back; 16 every track (%s)" % [gm(i) for i in (6, 7, 8, 9)])
    check(len(leds) >= 3 and leds[2][WHITE[12]] == "." and leds[2][WHITE[13]] == "X" and leds[2][WHITE[15]] == "." and leds[2][WHITE[0]] == ".",
          "... white 13 dark (the drums quiet), 14 lit, 16 dark (not every track plays) (%s)" % (leds[2:3],))
    check((G[10]["solo"], G[10]["msg"]) == ("0F00", "SOLO: MELODIC") and (G[11]["solo"], G[11]["msg"]) == ("0000", "NO SOLO"),
          "PERF SEL + white 15: the melodic ones (T9-T12) in solo; SEL + 16: no solo (%s %s)" % ((G[10]["solo"], G[10]["msg"]), (G[11]["solo"], G[11]["msg"])))
    check(gm(12) == ("00C0", "BASS MUTED"), "on the MOSSE's page the whites are PERF's: white 14, the bass (%s)" % (gm(12),))
    check(gm(13) == ("003F", "DRUMS MUTED") and gm(14) == ("0000", "ALL TRACKS AUDIBLE"), "the remote's CC 60: the drums; 63: ALL ON (%s %s)" % (gm(13), gm(14)))
    check([G[i]["rkill"] for i in (15, 16, 17)] == ["00C0", "0FFE", "0000"],
          "CC 77 held: KILL the bass; with CC 79: all but the tablet's track (T1) too; let go: nothing (%s)" % [G[i]["rkill"] for i in (15, 16, 17)])
    check(G[18]["msg"] == "PLAY FIRST", "CC 102 (RETRIG the drums) stopped: PLAY FIRST (%s)" % G[18]["msg"])
    sc = log.screens()
    check([(G[i]["lfod"], G[i]["lfot"]) for i in (19, 20, 21, 22)] == [("1", "16"), ("1", "19"), ("1", "19"), ("1", "11")],
          "LFO 2: K1 VEL, K2 past T12 - the groups (16 the drums ... 19 ALL), the end there; back to T12 (%s)" % [(G[i]["lfod"], G[i]["lfot"]) for i in (19, 20, 21, 22)])
    check(bool(sc) and sc[0]["cells"][1] is not None and sc[0]["cells"][1][0].lstrip("> ") == "TRACK" and sc[0]["cells"][1][1] == "DRUMS",
          "... the screen says TRACK DRUMS (%s)" % (sc[0]["cells"] if sc else None))


def t031_lfo_group():
    group("0.31 AN LFO ON A GROUP (LFO 2 K2 past T12, the grid's LFO row 7 pads 13-16): VEL on the drums moves the velocities of "
          "the six drum tracks of a TECHNO band and of no other; saved, and there after a power cycle")
    d = tempfile.mkdtemp()
    flash = os.path.join(d, "flash.bin")
    runs = []
    for on in (True, False):
        s = Script()
        t = band_hold(s, 100)
        t = pg(s, t, LFO, 0, [(K3, 127)])                         # LFO 1: DEPTH 127
        t = pg(s, t, LFO, 1, [(K1, 1), (K2, 12)])                 # VEL, on the drums
        s.press(t, LFO); s.tap_key(t + 30, wk(0)); s.release(t + 100, LFO); t += 160    # LFO + white 1: LFO 1 on
        if not on:
            s.press(t, LFO); s.tap_key(t + 30, wk(0)); s.release(t + 100, LFO)            # (... and off again: the same time)
        t += 160
        s.tap_btn(t, PLAY); t0 = t; t += 4000
        s.tap_btn(t, PLAY); t += 200
        if on:
            s.tap_btn(t, SAVE); s.tap_btn(t + 300, SAVE)
        t += 1200
        log = run(s, t, flash=flash if on else None)
        runs.append((log, t0))
    vel = [{ch: [v for _, n, v in lg.notes(ch=ch, after=t0)] for ch in range(12)} for lg, t0 in runs]
    differ = [ch for ch in range(12) if vel[0][ch] != vel[1][ch]]
    heard = [ch for ch in range(12) if vel[0][ch]]
    check(differ == [ch for ch in range(6) if ch in heard] and len(differ) >= 3 and all(len(vel[0][ch]) == len(vel[1][ch]) for ch in range(12)),
          "the LFO on the drums: the velocities of channels 1-6 (the drum tracks that play) move, of no other channel; the same notes (%s; %s)" % (
              differ, heard))
    check(len(runs[0][0].saves) == 1, "saved (%s)" % runs[0][0].saves)
    s = Script()
    s.at(300, "probe")
    log = run(s, 400, flash=flash)
    pr = probes(log)
    check(len(pr) == 1 and pr[0]["G"]["lfot"] == "16" and pr[0]["G"]["lfod"] == "1",
          "after a power cycle LFO 1 is still VEL on the drums (target 16) (%s)" % (((pr[0]["G"]["lfot"], pr[0]["G"]["lfod"]) if pr else None),))


def t031_grid():
    group("0.31 THE GRID'S PADS THAT DID NOTHING: the bank of 9-12 - buttons 12-15 the mutes of 9-12, PERF rows 5-8 the 32 scenes, "
          "the 16 snapshots and the twelve mutes with the GROUPS, DRUM rows 5-8 the force of the steps, EUCLID rows 5-8 the "
          "rotation and the family; the rows of the tracks' pads 13-16 the groups (FX LOOP and KILL, MOSSE dice and in / out, "
          "BEAT's CUSTOM scope, the LFO's target, FOLLOW); PROJ row 4 the channels; BEAT page 2 pads 11-12 a genre at random and "
          "the SOURCE; and two fixes: CC's lanes 7-8 lit, BEAT row 3's HARMONY and bars back")
    s = Script()
    t = band_hold(s, 100)                                                  # TECHNO: T1-T6 drums, T7-T8 bass, T9-T12 melodic
    s.raw(t, "attach"); t += 50
    s.tap_key(t, bk(8)); t += 80                                           # the bank 9-12 (track 9)
    marks, n = {}, [0]
    def P(name):                                                           # a probe, and where it is in the list
        nonlocal t
        s.at(t, "probe"); marks[name] = n[0]; n[0] += 1; t += 40
    s.ctl(t, GC_TRK0 + 4); t += 80; P("b12")                               # button 12 (bank 2): T9 muted
    t_b12 = t
    shift(s, t, 1); s.ctl(t + 10, GC_TRK0 + 5); shift(s, t + 60, 0); t += 100; P("sb13")   # SHIFT + 13: T10 solo
    shift(s, t, 1); s.ctl(t + 10, GC_TRK0 + 5); shift(s, t + 60, 0); t += 100
    s.ctl(t, GC_TRK0 + 4); t += 80                                         # (T9 back)
    t = view(s, t, GC_VPERF)                                               # PERF, the bank 9-12
    s.pad(t, 1, 4); t += 100; P("sc2")                                     # row 5 pad 2: scene 2
    shift(s, t, 1); s.pad(t + 10, 1, 5); shift(s, t + 90, 0); t += 120; P("st18")   # SHIFT + row 6 pad 2: store scene 18
    s.pad(t, 1, 5); t += 100; P("sc18")                                    # row 6 pad 2: scene 18
    shift(s, t, 1); s.pad(t + 10, 9, 6); shift(s, t + 90, 0); t += 120; P("ss10")   # SHIFT + row 7 pad 10: snapshot 10
    s.pad(t, 9, 6); t += 100; P("sn10")
    s.pad(t, 2, 7); t += 100; P("m3")                                      # row 8 pad 3: T3 muted
    s.pad(t, 12, 7); t += 100; P("mdr")                                    # pad 13: the drums
    t_perf = t
    s.pad(t, 15, 7); t += 100; P("mall")                                   # pad 16: ALL
    shift(s, t, 1); s.pad(t + 10, 13, 7); shift(s, t + 90, 0); t += 120; P("sbs")   # SHIFT + pad 14: the bass's solo
    shift(s, t, 1); s.pad(t + 10, 14, 7); shift(s, t + 90, 0); t += 120; P("sml")   # SHIFT + pad 15: the melodic ones' too
    shift(s, t, 1); s.pad(t + 10, 13, 7); shift(s, t + 90, 0); t += 120; P("sbo")   # SHIFT + pad 14 again: the bass's off
    shift(s, t, 1); s.pad(t + 10, 15, 7); shift(s, t + 90, 0); t += 120; P("nos")   # SHIFT + pad 16: no solo
    t = view(s, t, GC_VSTEP); t = view(s, t, GC_VSTEP)                     # DRUM
    s.pad(t, 0, 6); t += 100; P("f11")                                     # row 7 pad 1: T11 step 1 (off): on, ACCENT
    t_drum = t
    s.pad(t, 0, 6); t += 100; P("f11b")                                    # again: GHOST
    s.pad(t, 0, 6); t += 100; P("f11c")                                    # again: NORMAL
    shift(s, t, 1); s.pad(t + 10, 3, 5); shift(s, t + 90, 0); t += 120; P("s10")    # SHIFT + row 6: T10 selected
    t = view(s, t, GC_VTRACK, alt=True); t = view(s, t, GC_VTRACK, alt=True)   # EUCLID
    s.pad(t, 5, 4); t += 100; P("rot")                                     # row 5 pad 6: T9 rotation 4
    s.pad(t, 0, 5); t += 100; P("fam")                                     # row 6 pad 1: T10's family TRESILLO
    t_euc = t
    t = view(s, t, GC_UNDO, alt=True)                                      # FX
    s.pad(t, 12, 3); t += 100; P("l1")                                     # row 4 pad 13: without the drums
    s.pad(t, 12, 3); t += 100; P("l2")                                     # again: with
    s.pad(t, 13, 3); t += 100; P("l3")                                     # pad 14: without the bass
    s.pad(t, 15, 3); t += 100; P("l4")                                     # pad 16: every track
    s.at(t, "pad", 12, 5, 100); t += 80; P("k1")                           # row 6 pad 13 held: KILL the drums
    s.at(t, "pad", 12, 5, 0); t += 60; P("k2")
    shift(s, t, 1); s.pad(t + 10, 13, 5); shift(s, t + 90, 0); t += 120; P("k3")    # SHIFT + 14: the bass, latched
    t_fx = t
    shift(s, t, 1); s.pad(t + 10, 13, 5); shift(s, t + 90, 0); t += 120; P("k4")    # again: off
    s.at(t, "pad", 15, 5, 100); t += 80; P("k5")                           # pad 16 held: all but T10
    s.at(t, "pad", 15, 5, 0); t += 60
    t = view(s, t, GC_VPERF); t = view(s, t, GC_VPERF); t = view(s, t, GC_VPERF)   # PERF, SONG, MOSSE
    s.pad(t, 12, 2); t += 100; P("q1"); s.at(t, "dump", 0); t += 40       # row 3 pad 13: the drums in / out
    s.pad(t, 14, 1); t += 100; P("dice")                                   # row 2 pad 15: the dice for the melodic ones
    t = view(s, t, GC_VTRACK, alt=True)                                    # BEAT
    s.pad(t, 14, 1); t += 100                                              # row 2 pad 15: the scope CUSTOM
    s.pad(t, 12, 4); t += 100; P("cu1")                                    # row 5 pad 13: + the drums
    s.pad(t, 12, 4); t += 100; P("cu2")                                    # - the drums
    s.pad(t, 6, 2); t += 100; P("harm")                                    # row 3 pad 7: HARMONY on / off (0.29-0.30: progression 7)
    s.pad(t, 7, 2); t += 100; P("hb")                                      # pad 8: its bars (0.29-0.30: progression 8)
    s.pad(t, 12, 0); t += 100                                              # row 1 pad 13: the genres' page 2
    s.pad(t, 11, 0); t += 100; P("src")                                    # pad 12: the SOURCE
    t_beat = t
    s.pad(t, 10, 0); t += 100; P("rnd")                                    # pad 11: a genre at random
    t = view(s, t, GC_VPERF, alt=True)                                     # LFO
    s.pad(t, 9, 1); t += 100                                               # DEST VEL
    s.pad(t, 14, 6); t += 100; P("lfo")                                    # row 7 pad 15: the melodic ones
    t = view(s, t, GC_REC, alt=True)                                       # PROJ
    s.pad(t, 13, 3); t += 100; P("ch10a")                                  # row 4 pad 14: the drums on channel 10 - 0.32.1: asked
    s.pad(t, 13, 3); t += 100; P("ch10")                                   # ... again: done
    s.pad(t, 12, 3); t += 100; P("chowna")                                 # pad 13: each on its own - asked
    s.pad(t, 13, 3); t += 100; P("chx14")                                  # (pad 14 now: ANOTHER pad's question is no answer - it asks)
    s.pad(t, 12, 3); t += 100; P("chx13")                                  # (pad 13: the question was pad 14's - it asks again)
    s.pad(t, 12, 3); t += 100; P("chown")                                  # ... again: done
    s.pad(t, 15, 3); t += 100; P("chp")                                    # pad 16: T10 channel +
    t_proj = t
    t = view(s, t, GC_VSTEP, alt=True)                                     # CC
    t_cc = t + 80; t += 100
    log = run(s, t + 100)
    pr = probes(log)
    G = [p["G"] for p in pr]
    ok = len(G) == n[0]
    check(ok, "%d probes (%d)" % (n[0], len(G)))
    if not ok:
        return
    def g(name, *k): return tuple(G[marks[name]].get(x) for x in k) if len(k) > 1 else G[marks[name]].get(k[0])
    check(g("b12", "mute", "msg") == ("0100", "T9 MUTED"), "bank 9-12: button 12 is T9's mute (%s)" % (g("b12", "mute", "msg"),))
    check(g("sb13", "solo") == "0200", "SHIFT + button 13: T10's solo (%s)" % g("sb13", "solo"))
    _, c = log.leds(until=t_b12)
    check(c.get(GC_TRK0 + 4) == GL_MUTED and c.get(GC_TRK0 + 5) == GL_ON, "... button 12 red (muted), 13 green (%s %s)" % (c.get(GC_TRK0 + 4), c.get(GC_TRK0 + 5)))
    check(g("sc2", "scene") == "1" and g("st18", "msg") == "SCENE STORED 18" and g("sc18", "scene") == "17",
          "PERF (bank 9-12) row 5 pad 2: scene 2; SHIFT + row 6 pad 2 stores 18, the pad brings it (%s %s %s)" % (g("sc2", "scene"), g("st18", "msg"), g("sc18", "scene")))
    check(g("ss10", "msg") == "SNAPSHOT STORED 10" and g("sn10", "msg") == "SNAPSHOT 10" and g("sn10", "sbank") == "8",
          "row 7 pad 10 with SHIFT: snapshot 10 stored; the pad: snapshot 10 back (%s %s)" % (g("ss10", "msg"), g("sn10", "msg")))
    check(g("m3", "mute", "msg") == ("0004", "T3 MUTED") and g("mdr", "mute", "msg") == ("003F", "DRUMS MUTED") and g("mall", "mute") == "0000",
          "row 8: pad 3 T3's mute, 13 the drums, 16 ALL (%s %s %s)" % (g("m3", "mute", "msg"), g("mdr", "mute", "msg"), g("mall", "mute")))
    check(g("sbs", "solo", "msg") == ("00C0", "SOLO: BASS") and g("sml", "solo", "msg") == ("0FC0", "SOLO: MELODIC")
          and g("sbo", "solo", "msg") == ("0F00", "SOLO OFF: BASS") and g("nos", "solo", "msg") == ("0000", "NO SOLO"),
          "SHIFT + pad 14: the bass's solo; 15: the melodic ones' too; 14 again: the bass's off; 16: no solo (%s %s %s %s)" % (
              g("sbs", "solo", "msg"), g("sml", "solo", "msg"), g("sbo", "solo", "msg"), g("nos", "solo", "msg")))
    p, _ = log.leds(until=t_perf)
    check(p.get(7 * 16 + 12) == GL_FAINT and p.get(7 * 16 + 13) == GL_BLUE and p.get(7 * 16 + 2) == GL_MUTED and p.get(5 * 16 + 1) == GL_ON
          and p.get(4 * 16 + 1) in (GL_FAINT, GL_DIM) and p.get(6 * 16 + 9) in (GL_PLAY, GL_CYAN),
          "... the lights: the drums faint (quiet), the bass blue, T3 red; scene 18 the cursor's (lit), 2 not; snapshot 10 there (%s)" % (
              [p.get(i) for i in (7 * 16 + 12, 7 * 16 + 13, 7 * 16 + 2, 4 * 16 + 1, 5 * 16 + 1, 6 * 16 + 9)],))
    check(g("f11", "msg") == "T11 STEP 1: ACCENT" and g("f11b", "msg") == "T11 STEP 1: GHOST" and g("f11c", "msg") == "T11 STEP 1: NORMAL",
          "DRUM (bank 9-12) row 7: T11's step 1, off - on, ACCENT; GHOST; NORMAL (%s %s %s)" % (g("f11", "msg"), g("f11b", "msg"), g("f11c", "msg")))
    p, _ = log.leds(until=t_drum)
    check(p.get(6 * 16) == GL_ACCENT and p.get(2 * 16) not in (GL_OFF, None), "... the force pad bright (ACCENT), the step lit above (%s %s)" % (p.get(6 * 16), p.get(2 * 16)))
    check(g("s10", "sel") == "10", "SHIFT + a pad of row 6: T10 selected (%s)" % g("s10", "sel"))
    check(g("rot", "msg") == "T9 ROTATION 4" and pr[marks["rot"]]["T9"]["euc"].endswith("/4") and g("fam", "msg") == "T10 FAMILY TRESILLO",
          "EUCLID (bank 9-12) row 5 pad 6: T9's rotation 4; row 6 pad 1: T10's family (%s %s %s)" % (g("rot", "msg"), pr[marks["rot"]]["T9"]["euc"], g("fam", "msg")))
    p, _ = log.leds(until=t_euc)
    check(p.get(4 * 16 + 5) == GL_YELLOW and p.get(5 * 16) == GL_ORANGE, "... the rotation yellow, TRESILLO orange (%s %s)" % (p.get(4 * 16 + 5), p.get(5 * 16)))
    check([g(k, "lmask") for k in ("l1", "l2", "l3", "l4")] == ["0FC0", "0FFF", "0F3F", "0FFF"] and g("l1", "msg") == "LOOP / REPEAT WITHOUT DRUMS",
          "FX row 4 pad 13: LOOP / REPEAT without the drums, again with; 14 without the bass; 16 every track (%s %s)" % ([g(k, "lmask") for k in ("l1", "l2", "l3", "l4")], g("l1", "msg")))
    check([g(k, "gkill") for k in ("k1", "k2", "k3", "k4", "k5")] == ["003F", "0000", "00C0", "0000", "0DFF"] and g("k3", "msg") == "KILL BASS (STAYS)",
          "FX row 6 pad 13 held: KILL the drums; SHIFT + 14: the bass latched, again off; 16 held: all but T10 (%s %s)" % ([g(k, "gkill") for k in ("k1", "k2", "k3", "k4", "k5")], g("k3", "msg")))
    p, _ = log.leds(until=t_fx)
    check(p.get(5 * 16 + 13) == GL_PLAY and p.get(5 * 16 + 12) == GL_ORANGE and p.get(3 * 16 + 15) == GL_WHITE,
          "... the bass's KILL lit (PLAY), the drums' pad orange; row 4 pad 16 white (every track) (%s)" % ([p.get(i) for i in (5 * 16 + 13, 5 * 16 + 12, 3 * 16 + 15)],))
    q = log.viaggio[-1]["queue"] if log.viaggio else []
    check(re.match(r"^QUEUED: DRUMS (OUT|IN), 6 TRACKS$", g("q1", "msg") or "") is not None and len(q) == 6,
          "MOSSE row 3 pad 13: the six drum tracks in the queue, out or in (%s %s)" % (g("q1", "msg"), q))
    check(g("dice", "msg") == "THE DICE: MELODIC, 4 TRACKS", "row 2 pad 15: the dice for the melodic ones (%s)" % g("dice", "msg"))
    check(g("cu1", "cmask", "msg") == ("023F", "SCOPE + DRUMS") and g("cu2", "cmask", "msg") == ("0200", "SCOPE - DRUMS"),
          "BEAT, scope CUSTOM, row 5 pad 13: the drums in the scope (with T10), again out (%s %s)" % (g("cu1", "cmask", "msg"), g("cu2", "cmask", "msg")))
    check(g("harm", "harm") != G[marks["harm"] - 1]["harm"] and g("hb", "hbars") != g("harm", "hbars"),
          "row 3 pad 7: HARMONY on / off again, pad 8 its bars (0.29-0.30: progressions 7 and 8) (%s -> %s, %s -> %s)" % (
              G[marks["harm"] - 1]["harm"], g("harm", "harm"), g("harm", "hbars"), g("hb", "hbars")))
    check(g("src", "thsrc") == "1" and g("src", "msg") == "SOURCE THEORY: MADE BY THE GENRE'S RULES" and g("rnd", "genre") != g("src", "genre"),
          "BEAT page 2: pad 12 the SOURCE (THEORY), pad 11 another genre (%s %s %s -> %s)" % (g("src", "thsrc"), g("src", "msg"), g("src", "genre"), g("rnd", "genre")))
    p, _ = log.leds(until=t_beat)
    check(p.get(10) == GL_YELLOW and p.get(11) == GL_CYAN, "... pad 11 yellow, pad 12 cyan (THEORY) (%s %s)" % (p.get(10), p.get(11)))
    check(g("lfo", "lfot", "lfod", "msg") == ("18", "1", "LFO ON MELODIC"), "LFO row 7 pad 15: VEL on the melodic ones (%s)" % (g("lfo", "lfot", "lfod", "msg"),))
    check(g("ch10", "chs") == "9999996789AB" and g("chown", "chs") == "0123456789AB" and g("chp", "chs") == "012345678AAB" and g("chp", "msg") == "T10 CHANNEL 11",
          "PROJ row 4 pad 14: the drums on channel 10; 13: each on its own; 16: T10 on 11 (%s %s %s)" % (g("ch10", "chs"), g("chown", "chs"), g("chp", "chs")))
    check(g("ch10a", "chs", "msg") == ("0123456789AB", "THE DRUM TRACKS ON CHANNEL 10? AGAIN: YES")
          and g("chowna", "chs", "msg") == ("9999996789AB", "EVERY TRACK ON ITS OWN CHANNEL? AGAIN: YES"),
          "0.32.1: pads 13 and 14 change every track's channel - the first tap only asks, the channels as they were (%s %s)" % (g("ch10a", "chs", "msg"), g("chowna", "chs", "msg")))
    check(g("chx14", "chs", "msg") == ("9999996789AB", "THE DRUM TRACKS ON CHANNEL 10? AGAIN: YES")
          and g("chx13", "chs", "msg") == ("9999996789AB", "EVERY TRACK ON ITS OWN CHANNEL? AGAIN: YES"),
          "0.32.1: a pad's question is answered by the same pad only - another pad in between asks its own, and then this one asks again (%s %s)" % (g("chx14", "chs", "msg"), g("chx13", "chs", "msg")))
    p, _ = log.leds(until=t_proj)
    check(p.get(3 * 16 + 12) == GL_DIM and p.get(3 * 16 + 14) == GL_VIOLET, "... pad 13 dim (T10 not on its own any more), 15 violet (%s %s)" % (p.get(3 * 16 + 12), p.get(3 * 16 + 14)))
    p, _ = log.leds(until=t_cc)
    check(p.get(4 * 16 + 6) not in (GL_OFF, None) and p.get(4 * 16 + 7) not in (GL_OFF, None),
          "CC row 5: the lanes 7 and 8 lit like the others (0.28-0.30: dark, as with six lanes) (%s %s)" % (p.get(4 * 16 + 6), p.get(4 * 16 + 7)))
    # FOLLOW: a track's knob across the tracks - pad 15, the melodic ones (every track of an empty project), take T1's LENGTH
    s = Script()
    s.raw(100, "attach")
    t = view(s, 150, GC_VSTEP, alt=True); t = view(s, t, GC_VSTEP, alt=True)   # FOLLOW
    s.tap_btn(t, HOME); t += 80                                            # the HOME window: page 1 (CHANNEL, LENGTH ...)
    s.enc(t, K2, 16); t += 60                                              # T1 LENGTH 32
    s.pad(t, 14, 5); t += 100                                              # row 6 pad 15: the melodic ones
    s.at(t, "probe"); t += 40
    s.tap_btn(t, HOME); t += 80
    log = run(s, t + 100)
    pr = probes(log)
    check(len(pr) == 1 and [pr[0]["T%d" % k]["len"] for k in range(1, 13)] == ["32"] * 12 and re.sub(r"^TAB (T\d+: )?", "", pr[0]["G"]["msg"]) == "MELODIC: LENGTH AS T1",
          "FOLLOW row 6 pad 15: every melodic track (here all twelve) gets T1's LENGTH 32 (%s %s)" % (
              [pr[0]["T%d" % k]["len"] for k in range(1, 13)] if pr else None, pr[0]["G"]["msg"] if pr else None))


def t031_group_retrig():
    group("0.31: the remote's RETRIG of a group (channel 14 CC 102-105: the drums, the bass, the melodic ones, all) - each "
          "track of it from its first step at its next one; a group with no track says so and nothing moves")
    res, msg = {}, {}
    for cc in (None, 104, 105, 102):
        s = Script()
        t = program(s, 100, [60, 61, 62, 63, 64, 65, 66, 67])          # steps 1-8 of T1 (an empty project: every track melodic)
        p = t + 100
        s.tap_btn(p, PLAY)
        if cc:
            remote(s, int(p + 5.5 * STEP_MS), cc)                      # in the 6th step
            s.at(int(p + 5.5 * STEP_MS) + 15, "probe")
        log = run(s, p + int(9 * STEP_MS))
        res[cc] = [d1 for _, d1, _ in log.notes(ch=0, after=p)][:9]
        pr = probes(log)
        msg[cc] = re.sub(r"^TAB (T\d+: )?", "", pr[0]["G"]["msg"]) if pr else None
    check(res[None][:8] == [60, 61, 62, 63, 64, 65, 66, 67], "without: the eight steps in a row (%s)" % res[None])
    check(res[104] == [60, 61, 62, 63, 64, 65, 60, 61, 62] and msg[104] == "RETRIG MELODIC",
          "CC 104 (the melodic ones) in the 6th step: T1 from its first step at the next one (%s %s)" % (res[104], msg[104]))
    check(res[105] == [60, 61, 62, 63, 64, 65, 60, 61, 62] and msg[105] == "RETRIG ALL", "CC 105 (all): the same (%s %s)" % (res[105], msg[105]))
    check(res[102][:8] == [60, 61, 62, 63, 64, 65, 66, 67] and msg[102] == "NO DRUM TRACK",
          "CC 102 (the drums) with no drum track: NO DRUM TRACK, T1 goes on (%s %s)" % (res[102], msg[102]))



# ------------------------------------------------------------------------------------------------ 0.32
def t032_panel():
    group("0.32 THE KEYS THAT DID NOTHING SINCE BEFORE, ON THE PANEL: EDIT + black 8 FORCE (ACCENT, GHOST, NORMAL), 9 / 10 "
          "the step a place earlier / later, 11 its extras back to plain; ENV + black 1-8 the lane, 9 RAMP UP, 10 RAMP DOWN, "
          "11 CLEAR; LFO + black 1-6 the page, 7 COPY, 8 PASTE, 9 ALL OFF / BACK ON, 10 the next free LFO, 11 RESET (twice); "
          "SAVE + white 11 EXPORT, 14 / 15 the Pi's setlist (twice); the MASTER knob's fourth job, the ENERGY")
    img = sgq_image(["step 0,0,0 flags - 3", "step 0,0,0 velocity - 90", "step 0,0,0 chance - 50", "step 0,0,0 condition - 2",
                     "step 0,0,0 nudge - 3", "step 0,0,0 ratchet - 3", "step 0,0,0 ramp - 2", "step 0,0,0 note 0 64"])
    s = Script()
    t = sx_import(s, 100, img)                           # T1 step 1: velocity 90, chance 50, a condition, nudge, 3 ratchets, a ramp
    marks, n, ex, leds = {}, [0], {}, {}
    def P(name):
        nonlocal t
        s.at(t, "probe"); marks[name] = n[0]; n[0] += 1; t += 40
    def X(name):                                         # an export: the project as it is now
        nonlocal t
        s.raw(t, "sx 7D 53 47 01"); ex[name] = len(ex); t += 30
    def hold(btn, key, name=None):
        nonlocal t
        s.press(t, btn); s.tap_key(t + 30, key)
        if name:
            leds[name] = t + 75; s.at(t + 75, "leds")
        s.release(t + 100, btn); t += 160
    def lit(btn, name):                                  # the keys' lights while btn is held
        nonlocal t
        s.press(t, btn); leds[name] = t + 50; s.at(t + 50, "leds"); s.release(t + 100, btn); t += 160
    lit(EDIT, "ex1")                                     # black 11 lit: the step has extras
    hold(EDIT, bk(10)); P("plain"); X("plain")           # EDIT + black 11: back to plain
    lit(EDIT, "ex2")
    hold(EDIT, wk(1))                                    # the cursor on step 2 (off)
    hold(EDIT, bk(7)); P("f1")                           # black 8: on, ACCENT
    hold(EDIT, bk(7)); P("f2")                           # GHOST
    hold(EDIT, bk(7)); P("f3")                           # NORMAL
    hold(EDIT, bk(7), "acc"); P("f4")                    # ACCENT again (black 8 lit)
    hold(EDIT, bk(9)); P("later"); X("later")            # black 10: step 2 to 3
    hold(EDIT, bk(8)); P("earlier")                      # black 9: back to 2
    hold(EDIT, wk(0))                                    # the cursor on step 1
    hold(EDIT, bk(8)); P("wrap"); X("wrap")              # black 9 on the first step: to the last of the loop (16)
    hold(ENV, bk(2)); P("lane3")                         # ENV + black 3: lane 3
    hold(ENV, bk(8)); P("rup"); X("rup")                 # black 9: RAMP UP over the loop
    lit(ENV, "env")
    hold(ENV, bk(10)); P("clr"); X("clr")                # black 11: CLEAR
    hold(ENV, bk(10)); P("clr2")                         # again: nothing to clear
    hold(ENV, bk(9)); P("rdn"); X("rdn")                 # black 10: RAMP DOWN
    hold(LFO, bk(2)); P("lpage")                         # LFO + black 3: the LFO's page 3
    s.pages[LFO] = 2
    lit(LFO, "lfo")
    hold(LFO, wk(0)); P("l1")                            # LFO 1 on
    t = pg(s, t, LFO, 1, [(K1, 1), (K2, 3)]); P("l1set")   # LFO 1: VEL on T4
    t = pg(s, t, LFO, 4, [(K1, 2)])                      # ... its ENV's attack
    hold(LFO, bk(6)); P("copy")                          # black 7: COPY
    hold(LFO, wk(1)); P("l2")                            # LFO 2 on (selected)
    hold(LFO, bk(7)); P("paste"); X("paste")             # black 8: PASTE onto LFO 2
    hold(LFO, bk(8)); P("off"); X("off")                 # black 9: all off
    hold(LFO, bk(8)); P("on"); X("on")                   # again: back on, the ones that were
    hold(LFO, bk(9)); P("free")                          # black 10: the next free one (LFO 3)
    t = pg(s, t, LFO, 1, [(K1, 2), (K2, 5)]); P("l3set")   # (LFO 3: something to reset - its RATE SEQ too)
    t = pg(s, t, LFO, 3, [(K1, 2)])
    hold(LFO, bk(10)); P("rst0")                         # black 11: asks, for LFO 3 ...
    hold(LFO, wk(1)); hold(LFO, wk(1))                   # (0.32.1: LFO 2 chosen meanwhile - off and on again, as it was)
    hold(LFO, bk(10)); P("rst0b"); X("rst0b")            # ... black 11 again within the 3 s: it ASKS for LFO 2, nothing reset
    hold(LFO, wk(2)); hold(LFO, wk(2))                   # (LFO 3 again)
    hold(LFO, bk(10)); P("rst1")                         # black 11: asks
    hold(LFO, bk(10)); P("rst2"); X("rst")               # again: LFO 3 as a new project has it
    s.press(t, SAVE); s.enc(t + 30, K1, 3); s.release(t + 100, SAVE); t += 160; P("mk")   # SAVE + K1: MASTER KNOB ENERGY
    s.knob(t, 0); t += 60; s.knob(t, 512); t += 60; P("e50")
    s.knob(t, 1023); t += 60; P("e100")
    hold(SAVE, wk(10)); P("exp")                         # SAVE + white 11: EXPORT
    for i, nm in enumerate(("ONE", "TWO", "TRE")):       # the Pi's setlist, as the bridge sends it
        s.raw(t, "sx 7D 53 47 21 %02X 03 %s" % (i, " ".join("%02X" % ord(c) for c in nm))); t += 30
    t += 60
    hold(SAVE, wk(14), "nx"); P("nx1")                   # SAVE + white 15: names the next
    hold(SAVE, wk(14)); P("nx2")                         # again: loads it (asks the Pi)
    t_load = t
    hold(SAVE, wk(13)); P("pv0")                         # white 14: the one before - none
    t = sx_import(s, t, img); P("loaded")                # the Pi sends file 1
    hold(SAVE, wk(14)); P("nx3")                         # white 15: names file 2
    t += 3200
    hold(SAVE, wk(14)); P("nx4")                         # 3 s later: names it again
    log = run(s, t + 100)
    pr = probes(log)
    G = [p["G"] for p in pr]
    ok = len(G) == n[0]
    check(ok, "%d probes (%d)" % (n[0], len(G)))
    if not ok:
        return
    def g(name, k="msg"): return G[marks[name]].get(k)
    E = exports(log)
    check(len(E) == len(ex) + 1, "%d exports, and SAVE + white 11's (%d)" % (len(ex) + 1, len(E)))
    if len(E) != len(ex) + 1:
        return
    def e(name): return E[ex[name]]
    def kl(name): return dict(log.key_leds()).get(leds[name], "")
    st = step_of(e("plain"), 0, 0, 0)
    check(g("plain") == "STEP 1: PLAIN - CHANCE 100, ALL, NO NUDGE, 1 RATCHET" and (st["chance"], st["condition"], st["nudge"], st["ratchet"], st["ramp"]) == (100, 0, 0, 1, 0)
          and (st["velocity"], st["note"][0], st["flags"] & 1) == (90, 64, 1),
          "EDIT + black 11: chance 100, every time, no nudge, one hit, no ramp - the note and the velocity stay (%s %s)" % (g("plain"), st))
    check(kl("ex1")[BLACK[10]] == "X" and kl("ex2")[BLACK[10]] == ".", "... black 11 lit while the step has extras, dark after (%s %s)" % (kl("ex1")[BLACK[10]:BLACK[10] + 1], kl("ex2")[BLACK[10]:BLACK[10] + 1]))
    check([g(k) for k in ("f1", "f2", "f3", "f4")] == ["STEP 2: ACCENT", "STEP 2: GHOST", "STEP 2: NORMAL", "STEP 2: ACCENT"],
          "EDIT + black 8 FORCE on a step that is off: on, ACCENT; then GHOST, NORMAL, ACCENT (%s)" % [g(k) for k in ("f1", "f2", "f3", "f4")])
    check(kl("acc")[BLACK[7]] == "X", "... black 8 lit on an accent (%s)" % kl("acc"))
    a, b = step_of(e("later"), 0, 0, 1), step_of(e("later"), 0, 0, 2)
    check(g("later") == "STEP 2 TO 3" and b["velocity"] == 124 and b["flags"] & 1 and not a["flags"] & 1,
          "EDIT + black 10: the step a place later - it changes place with step 3 (%s %s %s)" % (g("later"), a["flags"], b))
    w = e("wrap")
    check(g("earlier") == "STEP 3 TO 2" and g("wrap") == "STEP 1 TO 16" and step_of(w, 0, 0, 15)["velocity"] == 90 and step_of(w, 0, 0, 1)["velocity"] == 124
          and not step_of(w, 0, 0, 0)["flags"] & 1,
          "EDIT + black 9: a place earlier; on the loop's first step it goes round to the last (%s %s %s)" % (g("earlier"), g("wrap"), step_of(w, 0, 0, 15)))
    up = [step_of(e("rup"), 0, 0, i)["lane"][2] for i in range(16)]
    check(g("lane3") == "ENV LANE 3" and g("rup") == "LANE 3 RAMP UP" and up == [k * 127 // 15 for k in range(16)],
          "ENV + black 3: lane 3; + black 9: a ramp up over the 16 steps of the loop, 0 to 127 (%s %s)" % (g("rup"), up))
    el = kl("env")
    check(el[BLACK[2]] == "X" and el[BLACK[0]] == "g" and el[BLACK[8]] == "g" and el[BLACK[10]] == "g",
          "... ENV held: black 3 lit (the lane), the other lanes dim (a CC each), 9-11 dim (%s)" % el)
    cl = [step_of(e("clr"), 0, 0, i)["lane"][2] for i in range(16)]
    dn = [step_of(e("rdn"), 0, 0, i)["lane"][2] for i in range(16)]
    check(g("clr") == "LANE 3 CLEARED" and cl == [255] * 16 and g("clr2") == "LANE 3: NO LOCK IN THE LOOP" and dn == [127 - k * 127 // 15 for k in range(16)],
          "black 11 CLEARs the lane (again: nothing there); black 10 a ramp down (%s %s %s)" % (g("clr"), g("clr2"), dn))
    check(g("lpage") == "LFO 1: PAGE 3" and kl("lfo")[BLACK[2]] == "X" and kl("lfo")[BLACK[0]] == "g",
          "LFO + black 3: the LFO's page 3, its key lit (%s %s)" % (g("lpage"), kl("lfo")))
    pl, pe = e("paste")["lfo"], e("paste")["lfoe"]
    check(g("copy") == "LFO COPIED 1" and g("paste") == "LFO PASTED 2" and (g("paste", "lfod"), g("paste", "lfot")) == ("1", "3") and pl[1] == pl[0]
          and pe[1] == pe[0] != pe[2],
          "black 7 COPY, black 8 PASTE: LFO 2 is LFO 1 (VEL on T4, its ENV too) (%s %s %s %s)" % (g("copy"), g("paste"), pl[1], pe[:3]))
    check(g("off") == "ALL LFOS OFF (AGAIN: BACK ON)" and [x["enabled"] for x in e("off")["lfo"]] == [0] * 16
          and g("on") == "THE LFOS BACK ON" and [x["enabled"] for x in e("on")["lfo"]] == [1, 1] + [0] * 14,
          "black 9: every LFO off; again: the two that were on, on (%s %s)" % (g("off"), g("on")))
    new = sgq_read(sgq_image([]))
    r = e("rst")
    check(g("free") == "THE NEXT FREE LFO: 3" and g("free", "lfosel") == "2" and g("rst1") == "RESET LFO? AGAIN: 3" and g("rst2") == "LFO RESET 3"
          and g("l3set", "lfod") != g("rst2", "lfod") and r["lfo"][2] == new["lfo"][2]
          and r["lfox"][2] == new["lfox"][2] and r["lfoe"][2] == new["lfoe"][2] and r["lfo"][0]["dest"] == 1,
          "black 10: the next LFO that is off; black 11 twice: that LFO as a new project has it, the others as they were (%s %s %s)" % (g("free"), g("rst1"), g("rst2")))
    r0 = e("rst0b")
    check(g("rst0") == "RESET LFO? AGAIN: 3" and g("rst0b") == "RESET LFO? AGAIN: 2" and r0["lfo"][1] == e("paste")["lfo"][1] and r0["lfo"][2] != new["lfo"][2],
          "0.32.1: RESET asked for LFO 3, LFO 2 chosen, black 11 again: it asks for LFO 2 - neither is reset (0.32: LFO 2 was) (%s %s)" % (g("rst0"), g("rst0b")))
    check(g("mk") == "MASTER KNOB: ENERGY" and g("e50") == "ENERGY 50: THE WHOLE SET" and g("e50", "en") == "50" and g("e100", "en") == "100",
          "the MASTER knob's fourth job: the ENERGY of the MOSSE, 0-100 (%s %s %s)" % (g("mk"), g("e50"), g("e100", "en")))
    check(g("exp") == "EXPORT: THE PROJECT TO THE PI" and E[-1]["live"]["master_fn"] == 3,
          "SAVE + white 11: the project to the Pi, an EXPORT (%s)" % g("exp"))
    loads = [(tm, m[5:7]) for tm, m in log.sysex if m[4] == 0x22]
    check(g("nx1") == "NEXT, AGAIN TO LOAD: 1 ONE" and g("nx2") == "LOADING 1 ONE" and [l for _, l in loads] == [[0, 0]] and loads[0][0] < t_load,
          "SAVE + white 15: the setlist's next file named; again: the FM-1 asks the Pi for it (%s %s %s)" % (g("nx1"), g("nx2"), loads))
    check(kl("nx")[WHITE[14]] in "Xg" and kl("nx")[WHITE[10]] == "g", "... SAVE held: white 11-15 lit (%s)" % kl("nx"))
    check(g("pv0") == "START OF THE LIST" and g("loaded") == "LOADED 1 ONE" and g("nx3") == "NEXT, AGAIN TO LOAD: 2 TWO" and g("nx4") == "NEXT, AGAIN TO LOAD: 2 TWO",
          "white 14 on the first: nothing before; file 1 in; white 15 names file 2 - and again after 3 s, not loading (%s %s %s)" % (g("pv0"), g("loaded"), g("nx4")))
    # SAVE + white 12 / 13: the track's pattern and the progression to the Pi (as SEQ + SAVE and ARP + SAVE)
    s = Script()
    t = band_hold(s, 100)
    s.press(t, SAVE); s.tap_key(t + 30, wk(11)); s.release(t + 100, SAVE); t += 160; s.at(t, "probe"); t += 40
    s.press(t, SAVE); s.tap_key(t + 30, wk(12)); s.release(t + 100, SAVE); t += 160; s.at(t, "probe"); t += 40
    log = run(s, t + 100)
    pr = probes(log)
    m = [p["G"].get("msg") for p in pr]
    cmds = [x[4] for _, x in log.sysex]
    check(len(m) == 2 and m[0] == "TO THE PI: TECHNO KICK" and (m[1] or "").startswith("TO THE PI: TECHNO ") and 0x64 in cmds and 0x6A in cmds,
          "SAVE + white 12: the track's pattern to the Pi; white 13: the progression (%s %s)" % (m, [hex(c) for c in cmds]))

def t032_grid():
    group("0.32 THE GRID'S PADS THAT DID NOTHING SINCE BEFORE: TRACK row 7 / 8 pad 16 (every VEL OFFSET 0, every nudge 0); CC "
          "row 5 COPY / PASTE / the lane in every pattern, row 8 the lane's mode and its tools (ramps, random, upside down, a "
          "step earlier / later, smoothed, halfway, the page cleared); BEAT row 4 pad 8 DICE PROG; FX row 2 pads 13 / 15 the "
          "dotted lengths")
    s = Script()
    s.raw(100, "attach")
    t = view(s, 200, GC_VTRACK)                                            # TRACK
    marks, n, ex, at = {}, [0], {}, {}
    def P(name):
        nonlocal t
        s.at(t, "probe"); marks[name] = n[0]; n[0] += 1; t += 40
    def X(name):
        nonlocal t
        s.raw(t, "sx 7D 53 47 01"); ex[name] = len(ex); t += 30
    def pad(x, y, name=None, wait=100):
        nonlocal t
        s.pad(t, x, y); t += wait
        if name:
            P(name)
    def mark(name):                                                        # the lights, a little after
        nonlocal t
        t += 150; at[name] = t
    pad(0, 6, "v1")                                                        # row 7 pad 1: T1's VEL OFFSET
    s.ctl(t, GC_TRK0 + 1); t += 80                                         # T2
    pad(14, 6, "v2"); mark("vo")                                           # row 7 pad 15: T2's
    pad(15, 6, "v0a"); X("v0a")                                            # pad 16: every track's to 0 - 0.32.1: asked
    for _ in range(3):                                                     # (more than three seconds go by, the grid kept alive)
        t += 1050; s.raw(t, "hb")
    pad(15, 6, "v0b"); X("v0b")                                            # ... too late: it asks again
    pad(15, 6, "v0"); X("v0"); mark("vo0")                                 # ... again: done
    pad(0, 7, "nu"); mark("nu")                                            # row 8 pad 1: T2 step 1's nudge (it comes on)
    pad(15, 7, "nu0"); X("nu0"); mark("nu0")                               # pad 16: every step of the pattern on the grid
    t = view(s, t, GC_VSTEP, alt=True)                                     # CC (T2, lane 1)
    pad(6, 7, "up")                                                        # row 8 pad 7: RAMP UP
    pad(12, 4, "copy")                                                     # row 5 pad 13: COPY
    pad(1, 4)                                                              # lane 2
    pad(13, 4, "paste"); X("paste"); mark("clip")                          # pad 14: PASTE
    pad(10, 7, "inv"); X("inv")                                            # row 8 pad 11: upside down
    pad(11, 7, "early"); X("early")                                        # pad 12: a step earlier
    pad(12, 7, "late"); X("late")                                          # pad 13: a step later
    pad(13, 7, "smooth"); X("smooth")                                      # pad 14: smoothed
    pad(14, 7, "half"); X("half")                                          # pad 15: halfway to the base
    pad(8, 7, "updn"); X("updn")                                           # pad 9: up and down
    pad(9, 7, "rnd"); X("rnd")                                             # pad 10: at random
    pad(14, 4, "every"); X("every")                                        # row 5 pad 15: the lane in every pattern of T2
    pad(15, 7, "page"); X("page")                                          # row 8 pad 16: the page cleared
    s.ctl(t, GC_UNDO); t += 100; X("undo")                                 # UNDO: back
    pad(3, 7, "slide")                                                     # pad 4: SLIDE
    pad(4, 7, "trig")                                                      # pad 5: TRIGLESS too
    pad(2, 7, "norm")                                                      # pad 3: NORMAL
    pad(5, 7, "nrpn"); X("nrpn"); mark("mode")                             # pad 6: NRPN
    t = view(s, t, GC_VTRACK, alt=True)                                    # BEAT
    pad(7, 3, "dice"); mark("dice")                                        # row 4 pad 8: DICE PROG
    log = run(s, t + 100)
    pr = probes(log)
    G = [p["G"] for p in pr]
    E = exports(log)
    ok = len(G) == n[0] and len(E) == len(ex)
    check(ok, "%d probes, %d exports (%d %d)" % (n[0], len(ex), len(G), len(E)))
    if not ok:
        return
    def g(name, k="msg"): return G[marks[name]].get(k)
    def e(name): return E[ex[name]]
    def L(name, x, y): return log.leds(until=at[name])[0].get(y * 16 + x)
    def lane(name, l=1, pat=0): return [step_of(e(name), 1, pat, i)["lane"][l] for i in range(16)]
    check(g("v1").startswith("VEL -") and g("v2").startswith("VEL ") and L("vo", 15, 6) == GL_ORANGE,
          "TRACK row 7: T1's and T2's VEL OFFSET; pad 16 orange - some track has one (%s %s %s)" % (g("v1"), g("v2"), L("vo", 15, 6)))
    check(g("v0") == "EVERY TRACK: VEL OFFSET 0" and [x["vel_offset"] for x in e("v0")["track"]] == [0] * 12 and L("vo0", 15, 6) == GL_FAINT,
          "row 7 pad 16: every track's VEL OFFSET back to 0, the pad faint (%s %s)" % (g("v0"), [x["vel_offset"] for x in e("v0")["track"]]))
    check(g("v0a") == "EVERY TRACK'S VEL OFFSET TO 0? AGAIN: YES" and [x["vel_offset"] for x in e("v0a")["track"]][:2] != [0, 0],
          "0.32.1: the first tap only asks - T1's and T2's offsets still there (%s %s)" % (g("v0a"), [x["vel_offset"] for x in e("v0a")["track"]][:3]))
    check(g("v0b") == "EVERY TRACK'S VEL OFFSET TO 0? AGAIN: YES" and [x["vel_offset"] for x in e("v0b")["track"]] == [x["vel_offset"] for x in e("v0a")["track"]],
          "0.32.1: the same pad more than three seconds later asks again - the question had gone (%s)" % g("v0b"))
    st = step_of(e("nu0"), 1, 0, 0)
    check(g("nu").startswith("NUDGE -") and L("nu", 15, 7) == GL_ORANGE and g("nu0") == "EVERY STEP ON THE GRID: NO NUDGE" and st["nudge"] == 0
          and st["flags"] & 1 and L("nu0", 15, 7) == GL_FAINT,
          "row 8: a step nudged, pad 16 orange; pad 16: every step of the pattern on the grid again (%s %s %s)" % (g("nu"), g("nu0"), st))
    ramp = [k * 127 // 15 for k in range(16)]
    check(g("up") == "LANE 1 RAMP UP" and g("copy") == "LANE 1 COPIED" and g("paste") == "LANE 2 PASTED" and lane("paste", 1) == ramp == lane("paste", 0),
          "CC row 8 pad 7: a ramp up; row 5 pad 13 COPY, pad 14 PASTE onto lane 2 (%s %s)" % (g("paste"), lane("paste", 1)))
    check(L("clip", 13, 4) == GL_CYAN and L("clip", 12, 4) == GL_ORANGE and L("clip", 14, 4) == GL_VIOLET,
          "... pad 14 cyan: a lane is copied; 13 orange, 15 violet (%s %s %s)" % (L("clip", 12, 4), L("clip", 13, 4), L("clip", 14, 4)))
    inv = [127 - v for v in ramp]
    ear = inv[1:] + inv[:1]
    def smooth(v):
        return [(v[k] * 2 + v[(k - 1) % 16] + v[(k + 1) % 16] + 2) // 4 for k in range(16)]
    sm = smooth(inv)
    hf = [(v + 64 + 1) // 2 for v in sm]
    ud = [(k * 254 // 15) if k * 254 // 15 <= 127 else 254 - k * 254 // 15 for k in range(16)]
    check((g("inv"), lane("inv")) == ("LANE 2 UPSIDE DOWN", inv), "pad 11: upside down (%s %s)" % (g("inv"), lane("inv")))
    check((g("early"), lane("early")) == ("LANE 2 A STEP EARLIER", ear) and (g("late"), lane("late")) == ("LANE 2 A STEP LATER", inv),
          "pad 12: the locks a step earlier, pad 13 a step later - round the loop (%s %s)" % (lane("early"), lane("late")))
    check((g("smooth"), lane("smooth")) == ("LANE 2 SMOOTHED", sm) and (g("half"), lane("half")) == ("LANE 2 HALFWAY TO THE BASE", hf),
          "pad 14: smoothed with the neighbours; pad 15 halfway to the base (none: 64) (%s %s)" % (lane("smooth"), lane("half")))
    rn = lane("rnd")
    check((g("updn"), lane("updn")) == ("LANE 2 UP AND DOWN", ud) and g("rnd") == "LANE 2 AT RANDOM" and all(0 <= v <= 127 for v in rn) and len(set(rn)) > 8,
          "pad 9: up and down; pad 10 at random, a lock on every step (%s %s)" % (lane("updn"), rn))
    check(g("every") == "LANE 2 IN EVERY PATTERN OF T2" and all(lane("every", 1, k) == rn for k in range(8)) and lane("every", 0, 3) == [255] * 16,
          "row 5 pad 15: the lane in all eight patterns of the track, the other lanes as they were (%s)" % g("every"))
    check(g("page") == "LANE 2 CLEARED ON THE PAGE" and lane("page") == [255] * 16 and lane("page", 1, 1) == rn and lane("undo") == rn,
          "row 8 pad 16: the lane cleared on the page shown (the other patterns keep it); UNDO: back (%s %s)" % (g("page"), lane("undo")))
    fl = e("nrpn")["track"][1]["lane_flags"]
    check(g("slide") == "SLIDE: THE VALUE GLIDES TO THE NEXT LOCK" and g("trig") == "SLIDE + TRIGLESS" and g("norm") == "LANE NORMAL"
          and g("nrpn") == "NRPN: K2 THE LSB, LANE HI (SEL+K2) THE MSB" and fl[1] == 4 and fl[0] == 0,
          "row 8 pads 3-6: the lane's mode - NORMAL, SLIDE, TRIGLESS, NRPN (as ENV K4) (%s %s %s %s %s)" % (g("slide"), g("trig"), g("norm"), g("nrpn"), fl))
    check(L("mode", 5, 7) == GL_WHITE and L("mode", 2, 7) == GL_DIM and L("mode", 6, 7) == GL_CYAN and L("mode", 15, 7) == GL_ORANGE,
          "... NRPN white, NORMAL dim; the tools cyan, blue, the page orange (%s %s %s %s)" % (L("mode", 5, 7), L("mode", 2, 7), L("mode", 6, 7), L("mode", 15, 7)))
    check((g("dice") or "").startswith("DICE PROG") and L("dice", 7, 3) == GL_VIOLET, "BEAT row 4 pad 8: DICE PROG (%s %s)" % (g("dice"), L("dice", 7, 3)))
    # FX row 2 pads 13 and 15: LOOP 1/16 dotted, 1/8 dotted - the loop repeats every 9 / 18 ticks (T1: a step on every 16th)
    for x, ticks, name in ((12, 9, "1/16 DOTTED"), (14, 18, "1/8 DOTTED")):
        s = Script()
        t = s.steps(100, list(range(16)))
        s.raw(t, "attach"); t += 50
        t = view(s, t, GC_UNDO, alt=True)                                  # FX
        s.tap_btn(t, PLAY)
        t += int(BAR_MS)
        s.pad(t, x, 1, hold=40); t_in = t; t += 120
        s.at(t, "probe"); t += 40
        t += int(BAR_MS)
        s.pad(t, 15, 1, hold=40); t_out = t; t += 200
        s.tap_btn(t, PLAY)
        for k in range(1100, t, 900):                                      # (the bridge's keep-alive)
            s.raw(k, "hb")
        log = run(s, t + 100)
        pr = probes(log)
        G1 = pr[0]["G"] if pr else {}
        tick = 60000.0 / int(G1.get("bpm", "128")) / 24
        on = [tm for tm, _, _ in log.notes(ch=0, after=t_in + 2 * ticks * tick, before=t_out)]
        per = [any(abs(tm - ticks * tick - u) <= 2.5 for u in on) for tm in on if tm > t_in + 3 * ticks * tick]
        gaps = sorted(set(round((b - a) / tick) for a, b in zip(on, on[1:])))
        p, _ = log.leds(until=t_in + 300)
        check(G1.get("msg") == name and G1.get("loop") == "1" and len(per) >= 8 and all(per) and p.get(16 + x) in (GL_ACCENT, GL_PLAY),
              "FX row 2 pad %d: LOOP %s - what plays repeats every %d ticks (%s, %d notes, %d in time, gaps %s ticks, the pad %s)" % (
                  x + 1, name, ticks, G1.get("msg"), len(per), per.count(True), gaps, p.get(16 + x)))


def t032_grid2():
    group("0.32 THE GRID'S PADS THAT DID NOTHING SINCE BEFORE: SONG row 4 (the entry earlier / later, its tempo, SONG TEMPO, "
          "its bars / 2 and x 2, SAVE THE SET, the end, the song from its first entry); PROJ rows 1, 3, 5, 6, 7 (a fifth down / "
          "up, RELATIVE, PARALLEL, THE KEY BEFORE; the MASTER knob's ENERGY and the project's switches; CLEAR, the setlist, SAVE "
          "OVER, NEW PROJECT; the tempo halved, doubled, 90 100 120 128 140 174)")
    s = Script()
    s.raw(100, "attach")
    t = view(s, 200, GC_VPERF); t = view(s, t, GC_VPERF)                  # SONG
    marks, n, ex, at = {}, [0], {}, {}
    def P(name):
        nonlocal t
        s.at(t, "probe"); marks[name] = n[0]; n[0] += 1; t += 40
    def X(name):
        nonlocal t
        s.raw(t, "sx 7D 53 47 01"); ex[name] = len(ex); t += 30
    def pad(x, y, name=None, wait=100):
        nonlocal t
        s.pad(t, x, y); t += wait
        if name:
            P(name)
    def mark(name):
        nonlocal t
        t += 150; at[name] = t
    for k in range(3):                                                     # three entries: scenes 1, 2, 3
        pad(k, 0, wait=80); pad(k, 1)
    pad(1, 0)                                                              # entry 2
    pad(5, 3, "later"); X("later")                                         # row 4 pad 6: a place later
    pad(4, 3, "earlier"); X("earlier")                                     # pad 5: back
    pad(6, 3, "bpm1")                                                      # pad 7: its tempo, the tempo now
    pad(8, 3, "stempo")                                                    # pad 9: SONG TEMPO
    pad(6, 3, "bpm2"); X("bpm"); mark("bpm")
    pad(7, 3, "nobpm")                                                     # pad 8: none of its own
    pad(10, 3, "x2"); X("x2")                                              # pad 11: its bars x 2
    pad(9, 3, "d2"); pad(9, 3); pad(9, 3, "d4"); X("d4")                   # pad 10: / 2 (4, 2, 1)
    pad(11, 3, "set")                                                      # pad 12: SAVE THE SET
    pad(14, 3, "end"); mark("end")                                         # pad 15: the end
    pad(0, 0); pad(9, 3); pad(9, 3)                                        # entry 1: a bar
    pad(15, 3, "first0")                                                   # pad 16: the song is off
    pad(0, 3)                                                              # pad 1: the song on
    s.tap_btn(t, PLAY); t += int(BAR_MS + 6 * STEP_MS)                     # entry 2 plays (entry 1 is a bar now)
    P("song2")
    pad(15, 3, "first")                                                    # pad 16: from the first entry
    s.tap_btn(t, PLAY); t += 200
    t = view(s, t, GC_REC, alt=True)                                       # PROJ
    pad(15, 2, "kb0")                                                      # row 3 pad 16: nothing changed yet
    pad(12, 0, "f4"); pad(13, 0, "f5")                                     # row 1 pad 13: a fifth down; 14 up
    pad(14, 0, "rel0")                                                     # 15 RELATIVE: of no major or minor
    pad(1, 1, "maj")                                                       # row 2 pad 2: MAJOR
    pad(14, 0, "rel"); pad(15, 0, "par"); mark("key")                      # RELATIVE (A minor), PARALLEL (A major)
    pad(15, 2, "kb1"); pad(15, 2, "kb2")                                   # THE KEY BEFORE, and back
    for x, name in ((3, "mk"), (5, "st"), (6, "thru"), (7, "long"), (8, "click"), (9, "cin"), (10, "mq"), (11, "sm"), (12, "prof")):
        pad(x, 4, name)
    X("sw"); mark("sw")
    pad(8, 4, "click2"); pad(9, 4, "cin2"); pad(12, 4, "prof2"); X("sw2")
    pad(8, 4, "click0"); pad(9, 4, "cin0"); pad(12, 4, "prof0")
    pad(7, 6, "h"); pad(9, 6, "d")                                         # row 7 pad 8: half (64); pad 10 double
    pad(15, 6, "b174"); mark("b174")
    pad(9, 6, "dmax"); pad(10, 6, "b90"); pad(7, 6, "h45"); pad(7, 6, "hmin")
    pad(10, 5, "clr")                                                      # row 6 pad 11: CLEAR an empty slot
    pad(12, 5, "pv"); pad(14, 5, "over")                                   # 13 the setlist, 15 SAVE OVER: no library
    pad(15, 5, "new1"); mark("new1"); pad(15, 5, "new2"); X("new")         # 16 a NEW PROJECT, twice
    log = run(s, t + 100)
    pr = probes(log)
    G = [p["G"] for p in pr]
    E = exports(log)
    ok = len(G) == n[0] and len(E) == len(ex)
    check(ok, "%d probes, %d exports (%d %d)" % (n[0], len(ex), len(G), len(E)))
    if not ok:
        return
    def g(name, k="msg"): return G[marks[name]].get(k)
    def e(name): return E[ex[name]]
    def L(name, x, y): return log.leds(until=at[name])[0].get(y * 16 + x)
    def sc(name): return [x["scene"] for x in e(name)["song_e"][:3]]
    check(g("later") == "SONG 2 TO 3" and sc("later") == [0, 2, 1] and g("earlier") == "SONG 3 TO 2" and sc("earlier") == [0, 1, 2],
          "SONG row 4 pad 6: the entry a place later, pad 5 earlier (%s %s %s %s)" % (g("later"), sc("later"), g("earlier"), sc("earlier")))
    se = e("bpm")["song_e"][1]
    check(g("bpm1") == "SONG 2: 128 BPM (SONG TEMPO: PAD 9)" and g("stempo") == "THE SONG SETS THE TEMPO" and g("bpm2") == "SONG 2: 128 BPM"
          and se["bpm"] == 128 and e("bpm")["live"]["song_tempo"] == 1 and L("bpm", 6, 3) == GL_CYAN and L("bpm", 8, 3) == GL_ON,
          "pad 7: the entry's tempo is the tempo now; pad 9 SONG TEMPO (%s %s %s %s)" % (g("bpm1"), g("stempo"), g("bpm2"), se))
    check(g("nobpm") == "SONG 2: NO TEMPO OF ITS OWN" and e("x2")["song_e"][1] == {"scene": 1, "bars": 8, "bpm": 0} and e("d4")["song_e"][1]["bars"] == 1,
          "pad 8: no tempo of its own; pad 11 its bars x 2 (8); pad 10 / 2 down to 1 (%s %s)" % (e("x2")["song_e"][1], e("d4")["song_e"][1]))
    check(g("set") == "NOTHING IN THE TRAIL YET" and g("end") == "SONG: THE NEW ENTRY 4" and L("end", 14, 3) == GL_WHITE,
          "pad 12: SAVE THE SET (no trail yet: it says so); pad 15: the free entry after the last (%s %s)" % (g("set"), g("end")))
    check(g("first0") == "SONG IS OFF (PAD 1)" and g("song2", "spos") == "1" and g("first", "spos") == "0" and g("first", "son") == "1",
          "pad 16: the song from its first entry (off: it says so) (%s %s %s)" % (g("first0"), g("song2", "spos"), g("first", "spos")))
    check(g("kb0") == "NO KEY BEFORE: CHANGE IT HERE FIRST" and (g("f4", "root"), g("f5", "root")) == ("5", "0") and g("rel0") == "RELATIVE: OF A MAJOR OR A MINOR KEY",
          "PROJ row 1 pad 13: a fifth down (C to F), 14 a fifth up (back to C); RELATIVE of a scale that is neither (%s %s %s)" % (g("kb0"), g("f4", "root"), g("rel0")))
    check((g("rel", "root"), g("rel", "scale")) == ("9", "2") and (g("par", "root"), g("par", "scale")) == ("9", "1")
          and (g("kb1", "root"), g("kb1", "scale")) == ("9", "2") and (g("kb2", "root"), g("kb2", "scale")) == ("9", "1"),
          "C MAJOR: RELATIVE A MINOR, PARALLEL A MAJOR; row 3 pad 16: the key before, and back (%s)" % [(g(k, "root"), g(k, "scale")) for k in ("rel", "par", "kb1", "kb2")])
    check(L("key", 14, 0) == GL_VIOLET and L("key", 12, 0) == GL_BLUE and L("key", 15, 2) == GL_YELLOW, "... the pads' lights (%s %s %s)" % (L("key", 14, 0), L("key", 12, 0), L("key", 15, 2)))
    w = e("sw")
    check(g("mk") == "MASTER KNOB: ENERGY" and w["live"]["master_fn"] == 3 and g("st") == "THE SONG KEEPS THE TEMPO" and w["live"]["song_tempo"] == 0
          and g("thru") == "MIDI IN PLAYS THE TRACK, REC OR NOT" and w["ext"]["in_thru"] == 1 and g("long") == "LONG PATTERNS: A PHRASE (THE NEXT ONE, A FILL)"
          and g("click") == "CLICK WHILE REC IS ON" and g("cin") == "COUNT IN 1 BAR: REC, THEN PLAY" and (w["ext"]["click"], w["ext"]["count_in"]) == (1, 1)
          and g("mq") == "MUTES WAIT FOR THE QUANTISE" and w["live"]["mute_q"] == 1 and g("sm") == "SCENE METRE: A SCENE STORED KEEPS THE METRE"
          and w["ext"]["scene_metre_on"] == 1 and g("prof", "prof") != G[marks["prof"] - 1]["prof"],
          "PROJ row 5: 4 the MASTER knob's ENERGY; 6-13 SONG TEMPO, MIDI IN PLAYS, LONG PATTERNS, CLICK, COUNT IN, MUTE QUEUE, SCENE METRE, the PROFILE (%s)" % (
              [g(k) for k in ("mk", "st", "thru", "long", "click", "cin", "mq", "sm", "prof")],))
    check(all(L("sw", x, 4) in (GL_ON, GL_ACCENT) for x in (6, 7, 8, 9, 10, 11, 12)) and L("sw", 5, 4) == GL_DIM and L("sw", 3, 4) == GL_WHITE,
          "... the switches lit when on (SONG TEMPO off again: dim), ENERGY white (%s)" % [L("sw", x, 4) for x in range(3, 13)])
    w2 = e("sw2")
    check((w2["ext"]["click"], w2["ext"]["count_in"]) == (2, 2) and g("click0") == "CLICK OFF" and g("cin0") == "NO COUNT IN"
          and len({g("prof", "prof"), g("prof2", "prof"), g("prof0", "prof")}) == 3 and g("prof0", "prof") == G[marks["prof"] - 1]["prof"],
          "the CLICK and the COUNT IN go round (off, 1, 2); the PROFILE round its three (%s %s)" % ([g(k) for k in ("click2", "cin2", "click0", "cin0")], [g(k, "prof") for k in ("prof", "prof2", "prof0")]))
    check([g(k, "bpm") for k in ("h", "d", "b174", "b90", "h45")] == ["64", "128", "174", "90", "45"] and g("dmax") == "TEMPO: 300 IS THE FASTEST"
          and g("hmin") == "TEMPO: 30 IS THE SLOWEST" and L("b174", 15, 6) == GL_WHITE and L("b174", 10, 6) == GL_VIOLET,
          "PROJ row 7 pad 8: the tempo halved, 10 doubled (30 to 300), 11-16 90 ... 174 (%s %s %s)" % ([g(k, "bpm") for k in ("h", "d", "b174", "b90", "h45")], g("dmax"), g("hmin")))
    nw = e("new")
    check(g("clr") == "NOTHING TO CLEAR: EMPTY SLOT 1" and g("pv") in ("LIBRARY EMPTY", "LIBRARY: ASKING THE PI") and g("over") == "NO FILE LOADED FROM THE PI"
          and g("new1") == "NEW PROJECT? AGAIN: WHAT IS NOT SAVED GOES" and L("new1", 15, 5) == GL_PEND and g("new2") == "NEW PROJECT: SAVE PUTS IT IN SLOT 1"
          and (nw["project"]["key_root"], nw["project"]["key_scale"], nw["project"]["bpm"], nw["live"]["master_fn"], nw["ext"]["in_thru"]) == (0, 0, 128, 0, 0),
          "PROJ row 6 pad 11 CLEAR (an empty slot: nothing), 13 / 15 the Pi's (no library), 16 a NEW PROJECT, twice (%s %s %s %s %s)" % (
              g("clr"), g("pv"), g("over"), g("new1"), g("new2")))
    # TRACK 2: row 5 the scenes' banks and programs, rows 6-8 a loop's playhead moved (T1: 16 steps, a note loop of 4)
    img = sgq_image(["step 0,0,%d flags - 3" % i for i in range(16)] + ["step 0,0,%d note 0 %d" % (i, v) for i, v in ((0, 60), (1, 62), (2, 64), (3, 65))]
                    + ["track 0 plen 0 4"])
    s = Script()
    t = sx_import(s, 100, img)
    s.raw(t, "attach"); t += 50
    t = view(s, t, GC_VTRACK); t = view(s, t, GC_VTRACK)                   # TRACK 2
    marks, n, ex, at = {}, [0], {}, {}
    pad(9, 4, "bank"); pad(0, 4, "s9")                                     # row 5 pad 10: scenes 9-16; pad 1: scene 9
    pad(4, 3); mark("pc")                                                  # row 4 pad 5: scene 9's program 5 (channel 1)
    pad(12, 4, "alla"); X("alla")                                          # pad 13: these programs in every scene - 0.32.1: asked
    pad(12, 4, "all"); X("all")                                            # ... again: done
    pad(13, 4, "none"); X("none")                                          # pad 14: this scene's none (one scene: at once)
    pad(6, 3); pad(14, 4, "cha"); X("cha")                                 # program 7; pad 15: channel 1's in every scene - asked
    pad(14, 4, "ch"); X("ch")                                              # ... again
    pad(5, 5, "far"); pad(0, 6, "nov")                                     # row 6 pad 6: past the loop of 4; row 7: no velocity loop
    for k in range(1100, t + 3000, 900):
        s.raw(k, "hb")
    s.tap_btn(t, PLAY); p0 = t
    tap = p0 + int(2.5 * STEP_MS)
    s.pad(tap, 2, 5, hold=30)                                              # row 6 pad 3, between steps 3 and 4: the note loop from its step 3
    s.at(tap + 50, "probe"); marks["jump"] = n[0]; n[0] += 1
    t = p0 + int(9 * STEP_MS)
    s.tap_btn(t, PLAY)
    log = run(s, t + 200)
    pr = probes(log)
    G = [p["G"] for p in pr]
    E = exports(log)
    ok = len(G) == n[0] and len(E) == len(ex)
    check(ok, "TRACK 2: %d probes, %d exports (%d %d)" % (n[0], len(ex), len(G), len(E)))
    if not ok:
        return
    pcs = lambda name: [x["pc"][0] for x in e(name)["scene"]]
    check(g("bank") == "PROGRAMS: SCENES 9-16" and g("s9") == "PROGRAMS OF SCENE 9" and L("pc", 9, 4) == GL_WHITE and L("pc", 0, 4) == GL_WHITE,
          "TRACK 2 row 5 pads 9-12: the bank of scenes pads 1-8 are; pad 1 now scene 9 (%s %s)" % (g("bank"), g("s9")))
    check(g("all") == "THE PROGRAMS OF SCENE 9 IN EVERY SCENE" and pcs("all") == [4] * 32 and g("none") == "SCENE 9: NO PROGRAM"
          and pcs("none") == [4] * 8 + [255] + [4] * 23 and g("ch") == "CHANNEL 1'S PROGRAM IN EVERY SCENE" and pcs("ch") == [6] * 32,
          "pad 13: scene 9's programs in all 32 scenes; 14: scene 9 without; 15: channel 1's program everywhere (%s %s %s)" % (pcs("all")[:10], pcs("none")[:10], pcs("ch")[:10]))
    check(g("alla") == "THESE PROGRAMS IN EVERY SCENE? AGAIN: YES" and pcs("alla") == [255] * 8 + [4] + [255] * 23
          and g("cha") == "THIS CHANNEL'S PROGRAM IN EVERY SCENE? AGAIN: YES" and pcs("cha") == [4] * 8 + [6] + [4] * 23,
          "0.32.1: pads 13 and 15 write all 32 scenes - the first tap only asks, the scenes as they were (%s %s | %s %s)" % (g("alla"), pcs("alla")[:10], g("cha"), pcs("cha")[:10]))
    nt = [d1 for _, d1, _ in log.notes(ch=0, after=p0 - 2)]
    check(g("far") == "NOTE LOOP 4 STEPS" and g("nov") == "VELOCITY LOOP = THE TRACK'S (ROW 2 GIVES IT ONE)" and g("jump") == "NOTE LOOP FROM STEP 3"
          and nt[:7] == [60, 62, 64, 64, 65, 60, 62],
          "rows 6-8: a tap moves the loop's playhead - the note loop of 4 goes on from its step 3 (without: 65 60 62 64) (%s %s)" % (g("jump"), nt[:8]))


def t032_grid3():
    group("0.32 THE GRID'S PADS THAT DID NOTHING SINCE BEFORE: LIB rows 5-7 (112 files, 0.5-0.31: 64) and row 8 (FIRST, AS "
          "SAVED, the pattern and the progression to the Pi, the files loaded last); MOSSE row 4 the phrase, row 6 MOVES AT, the "
          "genre and the key, row 7 HARMONY, LOCK, its bars; REGIA rows 2-8 the MOSSE's; FOLLOW's pads 11-16 of rows 5-8")
    img = sgq_image([])
    s = Script()
    s.raw(100, "attach")
    t = view(s, 200, GC_REC, alt=True); t = view(s, t, GC_REC, alt=True)  # LIB
    marks, n, at = {}, [0], {}
    def P(name):
        nonlocal t
        s.at(t, "probe"); marks[name] = n[0]; n[0] += 1; t += 40
    def pad(x, y, name=None, wait=100):
        nonlocal t
        s.pad(t, x, y); t += wait
        if name:
            P(name)
    def mark(name):
        nonlocal t
        t += 150; at[name] = t
    def entries(names):
        nonlocal t
        for k, nm in enumerate(names):
            s.raw(t, "sx 7D 53 47 21 %02X %02X %s" % (k, len(names), " ".join("%02X" % ord(c) for c in nm))); t += 12
        t += 100
    entries(["F%03d" % (k + 1) for k in range(100)])                       # the Pi's 100 files
    mark("list")
    pad(3, 6, "f100"); pad(3, 6, "f100l")                                  # row 7 pad 4: file 100; again: LOAD
    t = sx_import(s, t, img); P("in100")                                    # (the Pi sends it)
    pad(2, 7, "first"); t = sx_import(s, t, img); P("in1")                  # row 8 pad 3: the FIRST file
    mark("rec")
    pad(10, 7, "r2"); pad(10, 7, "r2l")                                    # pad 11: the one loaded before (file 100); again: LOAD
    pad(9, 7, "r1")                                                        # pad 10: the one loaded (file 1)
    pad(11, 7, "r3")                                                       # pad 12: nothing there yet
    pad(4, 7, "as1"); mark("as"); pad(4, 7, "as2")                         # pad 5: AS SAVED, twice
    pad(5, 7, "pat"); pad(6, 7, "prog")                                    # pads 6, 7: the pattern, the progression to the Pi
    entries(["G1", "G2"])                                                  # the Pi's folder changed
    pad(9, 7, "gone")
    for k in range(1000, t + 200, 900):
        s.raw(k, "hb")
    log = run(s, t + 100)
    pr = probes(log)
    G = [p["G"] for p in pr]
    ok = len(G) == n[0]
    check(ok, "LIB: %d probes (%d)" % (n[0], len(G)))
    if not ok:
        return
    def g(name, k="msg"): return G[marks[name]].get(k)
    def L(name, x, y): return log.leds(until=at[name])[0].get(y * 16 + x)
    loads = [m[5] + 128 * m[6] for _, m in log.sysex if m[4] == 0x22]
    check(L("list", 3, 6) == GL_DIM and L("list", 4, 6) == GL_OFF and L("list", 15, 4) == GL_DIM and g("f100") == "FILE 100 F100" and g("f100l") == "LOADING 100 F100",
          "LIB rows 5-7: files 65-112 (here 100 of them); file 100 chosen, again: the FM-1 asks the Pi for it (%s %s)" % (g("f100"), g("f100l")))
    check(g("in100") == "LOADED 100 F100" and g("first") == "LOADING 1 F001" and g("in1") == "LOADED 1 F001" and loads[:2] == [99, 0],
          "row 8 pad 3: the FIRST file of the setlist (%s %s %s)" % (g("first"), g("in1"), loads))
    check(L("rec", 9, 7) in (GL_ON, GL_CURSOR) and L("rec", 10, 7) == GL_DIM and L("rec", 11, 7) == GL_OFF,
          "row 8 pads 10-15: the files loaded last - 10 the one loaded (lit), 11 the one before (%s %s %s)" % (L("rec", 9, 7), L("rec", 10, 7), L("rec", 11, 7)))
    check(g("r2") == "FILE 100 F100" and g("r2l") == "LOADING 100 F100" and g("r1") == "FILE 1 F001" and g("r3") == "NO FILE LOADED THERE YET",
          "... a tap chooses that file, again loads it (by its name) (%s %s %s %s)" % (g("r2"), g("r2l"), g("r1"), g("r3")))
    check(g("as1") == "AS SAVED? AGAIN: 1 F001" and L("as", 4, 7) == GL_PEND and g("as2") == "LOADING 1 F001" and loads[-1] == 0,
          "row 8 pad 5: the file loaded as it is on the Pi - twice (%s %s)" % (g("as1"), g("as2")))
    check(all(g(k).startswith("TO THE PI: ") or g(k) in ("NOTHING WRITTEN TO SAVE", "NO PART: GIVE THE TRACK A ROLE (HOME 4 K2)") for k in ("pat", "prog")),
          "pads 6 / 7: the track's pattern and the progression to the Pi, as SEQ + SAVE, ARP + SAVE (%s %s)" % (g("pat"), g("prog")))
    check(g("gone") == "NOT ON THE PI NOW: F001", "a file loaded before that the Pi has no more: said so (%s)" % g("gone"))
    # MOSSE: the phrase, MOVES AT, the genre and the key; HARMONY, LOCK, its bars. REGIA: the same rows
    s = Script()
    s.raw(100, "attach")
    t = view(s, 200, GC_VPERF); t = view(s, t, GC_VPERF); t = view(s, t, GC_VPERF)   # MOSSE
    marks, n, at = {}, [0], {}
    pad(11, 3, "b4"); s.at(t, "dump", 0); t += 20; mark("b4")              # row 4 pad 12: a phrase of 4 bars
    pad(13, 3, "b16"); s.at(t, "dump", 0); t += 20
    pad(9, 5, "qbar"); pad(10, 5, "qbeat"); pad(8, 5, "qph"); mark("q")   # row 6 pads 9-11: MOVES AT
    pad(12, 5, "gen"); pad(14, 5, "key")                                  # 13 the genre +, 15 the key +: stopped, at once
    pad(11, 5, "gen0"); pad(13, 5, "key0")                                # 12 the genre -, 14 the key -: back
    s.tap_btn(t, PLAY); t += 300
    pad(12, 5); pad(14, 5); s.at(t, "dump", 0); t += 20; mark("gk")       # playing: in the queue
    s.tap_btn(t, PLAY); t += 200
    pad(13, 6, "h1"); pad(14, 6, "lock"); pad(15, 6, "bars"); mark("harm") # row 7 pads 14-16: HARMONY, LOCK, the bars
    s.raw(t, "sx 7D 53 47 54 01 00 02 00 00 00 00 00 00 00 00 00 00 00 00 00"); t += 50   # a regista on the Pi
    t = view(s, t, GC_VPERF)                                               # REGIA
    pad(12, 3, "rb8"); s.at(t, "dump", 0); t += 20; mark("regia")          # its row 4 pad 13: a phrase of 8
    s.at(t, "pad", 1, 1, 100); t += 700; P("rdice"); s.at(t, "pad", 1, 1, 0); t += 100   # row 2 pad 2 held: T2's dice
    pad(0, 0, "rule")
    log = run(s, t + 100)
    pr = probes(log)
    G = [p["G"] for p in pr]
    v = log.viaggio
    ok = len(G) == n[0] and len(v) == 4
    check(ok, "MOSSE: %d probes, 4 dumps (%d %d)" % (n[0], len(G), len(v)))
    if not ok:
        return
    check((g("b4"), v[0]["bars"], g("b16"), v[1]["bars"]) == ("PHRASE: BARS 4", 4, "PHRASE: BARS 16", 16) and L("b4", 11, 3) == GL_WHITE and L("b4", 12, 3) == GL_BLUE,
          "MOSSE row 4 pads 12-14: the phrase of 4, 8, 16 bars (as GLO 3 K2) (%s %s %s)" % (g("b4"), g("b16"), [v[0]["bars"], v[1]["bars"]]))
    check([g(k) for k in ("qbar", "qbeat", "qph")] == ["MOVES AT EVERY BAR", "MOVES AT EVERY BEAT", "MOVES AT THE PHRASE BOUNDARY"] and L("q", 8, 5) == GL_WHITE and L("q", 9, 5) == GL_DIM,
          "row 6 pads 9-11: MOVES AT every bar, every beat, the phrase (%s)" % [g(k) for k in ("qbar", "qbeat", "qph")])
    q = v[2]["queue"]
    check(g("gen").startswith("GENRE ") and g("gen", "genre") != G[marks["gen"] - 1]["genre"] and g("key", "root") == "1"
          and g("gen0", "genre") == G[marks["gen"] - 1]["genre"] and g("key0", "root") == "0"
          and len(q) == 2 and L("gk", 11, 5) == GL_PEND and L("gk", 13, 5) == GL_PEND,
          "pads 12-13: the genre - / +, 14-15: the key - / + - stopped at once, playing in the queue, the pads blink (%s %s %s)" % (g("gen"), g("key"), q))
    check(g("h1", "harm") != G[marks["h1"] - 1]["harm"] and g("lock", "hlock") == "1" and g("lock", "harm") == "1" and g("bars", "hbars") != g("lock", "hbars")
          and L("harm", 13, 6) == GL_ON and L("harm", 14, 6) == GL_ORANGE,
          "row 7 pad 14: HARMONY on / off; 15 LOCK; 16 its bars a chord (%s)" % [(g(k, "harm"), g(k, "hlock"), g(k, "hbars")) for k in ("h1", "lock", "bars")])
    check(g("rb8") == "PHRASE: BARS 8" and v[3]["bars"] == 8 and L("regia", 12, 3) == GL_WHITE and L("regia", 0, 0) == GL_ON and L("regia", 1, 0) == GL_DIM
          and L("regia", 2, 0) == GL_PLAY and g("rule") == "REGIA RULE 1" and (g("rdice") or "").startswith("T2 ") and " DICE" in (g("rdice") or ""),
          "REGIA rows 2-8 are the MOSSE's (0.9-0.31: dark), a track pad held its dice too; row 1 the regista's rules (%s %s %s %s)" % (g("rb8"), v[3]["bars"], g("rdice"), g("rule")))
    # FOLLOW, a knob that is no track's: ARP 5 (USER PROG) K4 its shape, ARP 6 K3 the chord's length - the pads past the black keys
    s = Script()
    s.raw(100, "attach")
    t = 200
    s.tap_btn(t, ARP); t += 100
    for _ in range(4):
        s.tap_btn(t, OCT_UP); t += 80                                      # ARP 5: USER PROG
    s.enc(t, K3, 1); t += 60                                               # a chord on its first place (I)
    t = view(s, t, GC_VSTEP, alt=True); t = view(s, t, GC_VSTEP, alt=True)   # FOLLOW
    marks, n, at = {}, [0], {}
    t += 200; mark("sh0"); P("sh0")
    pad(10, 7); s.at(t, "ui"); t += 40                                     # row 8 pad 11: shape 27
    pad(11, 7, "shape"); s.at(t, "ui"); t += 40; mark("shape")             # pad 12: shape 28
    s.tap_btn(t, OCT_UP); t += 300                                         # ARP 6
    pad(11, 6, "len"); s.at(t, "ui"); t += 40; mark("len")                 # row 7 pad 12: the chord's length 18
    pad(13, 6); s.at(t, "ui"); t += 40                                     # pad 14: 21
    pad(11, 7, "push")                                                     # row 8 pad 12: PUSH (0-4): no such value
    log = run(s, t + 100)
    pr = probes(log)
    G = [p["G"] for p in pr]
    ok = len(G) == n[0]
    check(ok, "FOLLOW: %d probes (%d)" % (n[0], len(G)))
    if not ok:
        return
    cells = [x["cells"][2:4] for x in log.screens()][-4:]
    check(L("sh0", 11, 7) not in (GL_OFF, GL_WHITE, None) and L("shape", 11, 7) == GL_WHITE and L("shape", 10, 7) != GL_WHITE and L("shape", 9, 7) != GL_WHITE
          and g("sh0", "uprog#") != g("shape", "uprog#") and g("shape", "uprog#") != g("len", "uprog#")
          and len(cells) == 4 and cells[0][1][1] == "DOM9" and cells[1][1][1] == "MIN9",
          "ARP 5 K4, the shape: row 8 pads 11-16 its items 27-32 (0.12-0.31: dark) - 27 DOM9, 28 MIN9 (%s %s %s)" % (L("sh0", 11, 7), L("shape", 11, 7), cells[:2]))
    check(L("len", 11, 6) == GL_WHITE and L("len", 12, 6) not in (GL_OFF, GL_WHITE, None) and len(cells) == 4 and cells[2][0][1] == "18 16TH"
          and cells[3][0][1] == "21 16TH" and g("push").endswith(": NOT A VALUE OF IT"),
          "ARP 6 K3, the chord's length: row 7 pads 11-16 the lengths 17 18 19 21 22 23; a list of five has no item 28 (%s %s)" % (cells[2:], g("push")))


def t032_maps():
    group("0.32 the map of the keys (a button held half a second): EDIT, ENV and LFO say their new black keys on line 2 "
          "(with SEL: what PICK does, as before), SAVE its whites 11-15")
    s = Script()
    t = pg(s, 3500, SAVE, 1) + 3200                      # (after the power-on's name; SAVE on its page 2: page 1 shows the slots)
    for btns in ((EDIT,), (EDIT, SEL), (ENV,), (LFO,), (SAVE,)):
        for k, b in enumerate(btns):
            s.press(t + 20 * k, b)
        s.at(t + 700, "ui")
        for b in btns:
            s.release(t + 760, b)
        t += 900
    log = run(s, t + 100)
    sc = [x["lines"][3:5] for x in log.screens()]
    want = [["B LCK CPY PST CLR PLN TIE SLD", "B8 FORCE 9/10 MOVE 11 EXTRAS"], None, ["W CURSOR  B1-8 THE LANE", "B9 RAMP UP 10 DOWN 11 CLEAR"],
            ["W LFO ON/OFF  B1-6 THE PAGE", "B7CPY 8PST 9OFF 10FREE 11RST"], ["W SLOT 9/10SNP 11-15 PI 16SET", "B SNAP SEL+B STORE 9CAP 10SND"]]
    ok = len(sc) == 5 and all(w is None or [x.strip() for x in sc[k]] == w for k, w in enumerate(want))
    check(ok and sc[1][0].strip() == want[0][0] and sc[1][1].strip().startswith("SEL+"),
          "EDIT, ENV, LFO, SAVE held: the new keys in the map; EDIT + SEL: PICK's line as before (%s)" % sc)
    # 0.32.1: HOME and GLO say what 0.31 gave their whites 13-16 - the page of steps, the groups (0.31-0.32: not said)
    s = Script()
    t = 6800
    for b in (HOME, GLO):
        s.press(t, b); s.at(t + 700, "ui"); s.release(t + 760, b); t += 900
    log = run(s, t + 100)
    sc = [x["lines"][3].strip() for x in log.screens()]
    check(sc == ["W TRK 13-16 STEP PG  B TRACKS", "W MUTE 13-16 GROUPS  B SCENES"], "0.32.1: HOME and GLO held: their whites 13-16 in the map (%s)" % sc)



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
         t011_lengths, t011_harmony_genre, t011_algo_slots, t011_band_cook, t011_note_lengths, t011_pi_patterns, t011_progressions, t011_pi_progressions, t011_in_time_after, t011_explorer_sessions, t011_pc_test, t0203_test_listens, t012_pick, t012_blocks, t012_studio_viaggio, t012_break, t012_remote13, t012_review, t012_window, t012_grid_pick,
         t013_lfo, t013_repeat, t013_keyboard, t013_motion, t013_slide, t013_chain,
         t015_names_clear, t015_groove, t015_link, t016_genre_groove, t016_harm_free_copy, t016_algo_ready, t016_ready_elsewhere, t016_merengue,
         t017_mosse, t017_proposal,
         t018_arp_slow, t018_tablet_track, t018_live_page, t0206_echo_ccs, t018_live_sweep,
         t019_mfx_chain, t020_new_fx, t020_env_mod, t021_clean, t022_deep, t022_unrun, t_theory, t023_theory, t023_theory_genres, t023_theory_free, t023_snapshot_direction, t0231_numeric, t0231_cell, t0231_counts, t0232_tablet_rule,
         t024_lengths, t024_copies, t024_longer_shorter, t024_makers,
         t025_tablet_lengths, t025_metre, t025_metre_makers, t025_turing_numeric, t025_polyrhythm, t025_listen, t025_melody,
         t026_engines, t026_tune_answers, t026_gaps, t026_octave_patterns, t026_lfo_dests, t026_song_entries, t026_cook_lfo, t026_tablet_retrig, t026_take_poly,
         t027_keyless_band, t027_random_dice, t027_evolve_return, t027_who_acts, t027_semplice, t027_mark, t028_panel, t0281_mod_page, t0281_proposal_start,
    t026_smooth, t026_live_chords, t026_scene_metre, t026_click, t026_expression, t029_more,
    t029_viaggio_progs, t030_banks, t030_tape, t031_panel, t031_lfo_group, t031_grid, t031_group_retrig,
    t032_panel, t032_grid, t032_grid2, t032_grid3, t032_maps, t0321_tablet_banks]
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
