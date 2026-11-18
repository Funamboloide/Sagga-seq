#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Tests of tools/sagga_grid_bridge.py with fake ports (no MIDI hardware, no mido needed):
the translation both ways, batching, blink, keep-alive, left/right, and that the LED roles match the firmware.

    python3 tests/sagga_bridge_tests.py        (from the repository root)
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import sagga_grid_bridge as B   # noqa: E402

N = [0]
FAILS = []


def check(cond, what):
    N[0] += 1
    if not cond:
        FAILS.append(what)
        print("  FAIL:", what)


class Rig:
    def __init__(self, model="mk3", swap=False):
        self.lp = {0: [], 1: []}
        self.fm = []
        self.b = B.Bridge(lambda i, m: self.lp[i].append(list(m)), lambda m: self.fm.append(list(m)), model=model, swap=swap)

    def specs(self, idx):
        """every LED spec of every SysEx sent to Launchpad idx (MK3 format): [(type, led, data...)]; a spec that
        is not 1 (flash, 2 data), 2 (pulse, 1 data) or 3 (RGB, 3 data) fails the test"""
        size = {1: 4, 2: 3, 3: 5}
        out = []
        for m in self.lp[idx]:
            if m[:7] == B.MK3.HEADER + [0x03]:
                assert m[-1] == 0xF7
                body = m[7:-1]
                i = 0
                while i < len(body):
                    out.append(tuple(body[i:i + size[body[i]]]))
                    i += size[body[i]]
        return out

    def leds(self, idx):
        """led index -> the last static rgb sent to Launchpad idx (MK3 format)"""
        return {s[1]: tuple(s[2:5]) for s in self.specs(idx) if s[0] == 3}


def t_roles_match_firmware():
    src = open(os.path.join(ROOT, "firmware/src/sagga_grid.c")).read()
    m = re.search(r"enum \{ GL_OFF = 0,(.*?)\};", src, re.S)
    body = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)                 # (0.12: a comment inside the enum)
    names = ["OFF"] + [x.strip()[3:] for x in body.replace("\n", " ").split(",") if x.strip()]
    check(names == B.ROLE_NAMES, "LED roles in the bridge are the GL_* of the firmware (%s)" % names)
    check(len(B.RGB) == 19 and all(len(c) == 3 and max(c) <= 127 for c in B.RGB), "19 colours, 0..127 (0.12: TAIL, TIE; 0.24: GHOST)")
    check(len(set(B.RGB)) == len(B.RGB), "no two roles of one colour (the red-green Launchpad finds a role by its colour)")
    check(all(n in B.MINI_RG for n in B.ROLE_NAMES), "the red-green Launchpad has every role")
    m = re.search(r"enum \{ GC_PLAY = 0, (.*?)GC_TRK0 = 8, GC_PAT0 = 16, GC_SCN0 = 24", src, re.S)
    check(len([x for x in m.group(1).split(",") if x.strip()]) == 7, "buttons 0-7 are the transport / view / shift ones")


def t_start_stop():
    r = Rig()
    r.b.start(0.0)
    check(r.fm == [[0xBF, 118, 127]], "start attaches (CC 118 = 127 on channel 16)")
    check(all(r.lp[i][0] == B.MK3.HEADER + [0x0E, 0x01, 0xF7] for i in (0, 1)), "both Launchpads go to programmer mode first")
    check(all(r.lp[i][:3] == B.MK3().init() and len(r.lp[i]) == 4 for i in (0, 1)),
          "then midigrid's reset (flash and pulse layers) and one blanking message, nothing else")
    leds = set(B.MK3().all_leds())
    check(len(leds) == 80 and 11 in leds and 88 in leds and 91 in leds and 98 in leds and 89 in leds and 19 in leds,
          "the 80 LEDs: 64 pads, 8 top, 8 side")
    for i in (0, 1):
        sp = r.specs(i)
        check({s[1] for s in sp if s[0] == 1} == leds and all(s[2:] == (0, 0) for s in sp if s[0] == 1),
              "flash layer of every LED cleared (%d)" % i)
        check({s[1] for s in sp if s[0] == 2} == leds and all(s[2:] == (0,) for s in sp if s[0] == 2),
              "pulse layer of every LED cleared (%d)" % i)
        check(r.leds(i) == {led: (0, 0, 0) for led in leds}, "and every LED dark (%d)" % i)
        check(all(len(m) <= 7 + 81 * 5 + 1 for m in r.lp[i]), "no message with more than 81 LED specs")
    r.b.fm1_in([0x9F, 0, 0]); r.b.tick(0.01)
    check(len(r.lp[0]) == 4 and len(r.lp[1]) == 4, "an LED that is off stays unsent after the blanking")
    r.b.tick(0.5)
    check(r.fm == [[0xBF, 118, 127]], "no keep-alive too early")
    r.b.tick(1.01)
    check(r.fm[-1] == [0xBF, 118, 64], "keep-alive after a second")
    r.b.tick(1.5); r.b.tick(2.02)
    check(r.fm[-1] == [0xBF, 118, 64] and len(r.fm) == 3, "and every second")
    r.b.stop()
    check(r.fm[-1] == [0xBF, 118, 0], "stop detaches")
    check(r.lp[0][-1] == B.MK3.HEADER + [0x0E, 0x00, 0xF7], "and puts the Launchpads back to live mode")
    check(all(v == (0, 0, 0) for v in r.leds(0).values()) and len(r.leds(0)) == 64 + 16, "and blanks their LEDs")


def t_pads_in():
    r = Rig()
    for lp, note, vel, want in ((0, 81, 100, [0x9F, 0, 100]), (1, 88, 90, [0x9F, 15, 90]), (0, 11, 64, [0x9F, 112, 64]),
                                (1, 18, 1, [0x9F, 127, 1]), (0, 44, 70, [0x9F, 3 + 4 * 16, 70]), (1, 55, 70, [0x9F, 8 + 4 + 3 * 16, 70])):
        r.fm.clear(); r.b.lp_in(lp, [0x90, note, vel])
        check(r.fm == [want], "LP%d note %d -> %s (%s)" % (lp, note, want, r.fm))
    r.fm.clear(); r.b.lp_in(0, [0x80, 81, 0]); r.b.lp_in(0, [0x90, 81, 0])
    check(r.fm == [[0x9F, 0, 0], [0x9F, 0, 0]], "release = velocity 0, whichever way the Launchpad says it")
    r.fm.clear()
    for junk in ([0x90, 19, 5], [0x90, 89, 5], [0x90, 90, 5], [0x90, 9, 5], [0xA0, 81, 5], [0xD0, 5], [0xF8]):
        r.b.lp_in(0, junk)
    check(r.fm == [], "side-column notes, out-of-range notes, pressure and clock are ignored")


def t_buttons_in():
    r = Rig()
    for lp, cc, val, want in ((0, 91, 127, [0xBE, 0, 127]), (0, 98, 0, [0xBE, 7, 0]), (1, 91, 127, [0xBE, 8, 127]),
                              (1, 98, 127, [0xBE, 15, 127]), (0, 89, 127, [0xBE, 16, 127]), (0, 19, 127, [0xBE, 23, 127]),
                              (1, 89, 127, [0xBE, 24, 127]), (1, 19, 127, [0xBE, 31, 127]), (0, 79, 40, [0xBE, 17, 0])):
        r.fm.clear(); r.b.lp_in(lp, [0xB0, cc, val])
        check(r.fm == [want], "LP%d CC %d -> %s (%s)" % (lp, cc, want, r.fm))
    r.fm.clear(); r.b.lp_in(0, [0xB0, 99, 127]); r.b.lp_in(0, [0xB0, 7, 127])
    check(r.fm == [], "the logo and unknown CCs are ignored")


def t_leds_out():
    r = Rig()
    on, blue = B.ROLE_NAMES.index("ON"), B.ROLE_NAMES.index("BLUE")
    for fm, lp, led in (([0x9F, 0, on], 0, 81), ([0x9F, 15, on], 1, 88), ([0x9F, 112, on], 0, 11), ([0x9F, 127, on], 1, 18),
                        ([0x9F, 8, on], 1, 81), ([0x9F, 7 + 16, on], 0, 78),
                        ([0xBE, 0, blue], 0, 91), ([0xBE, 7, blue], 0, 98), ([0xBE, 8, blue], 1, 91), ([0xBE, 15, blue], 1, 98),
                        ([0xBE, 16, blue], 0, 89), ([0xBE, 23, blue], 0, 19), ([0xBE, 24, blue], 1, 89), ([0xBE, 31, blue], 1, 19)):
        r2 = Rig()
        r2.b.fm1_in(fm); r2.b.tick(0.0)
        got = r2.leds(lp)
        want = B.RGB[fm[2]]
        check(got == {led: want}, "FM-1 %s -> Launchpad %d LED %d (%s)" % (fm, lp, led, got))
        check(not r2.lp[1 - lp], "and nothing on the other Launchpad")
    r.b.fm1_in([0x9F, 0, on]); r.b.tick(0.0); n = len(r.lp[0])
    r.b.fm1_in([0x9F, 0, on]); r.b.tick(0.01)
    check(len(r.lp[0]) == n, "an unchanged LED is not sent again")
    r.b.fm1_in([0x9F, 0, 0]); r.b.tick(0.02)
    check(r.leds(0)[81] == (0, 0, 0), "role 0 switches the LED off")
    r.b.fm1_in([0x9F, 0, 99]); r.b.tick(0.03)
    check(r.leds(0)[81] == B.RGB[2], "a role the bridge does not know (a newer firmware's) is DIM, not dark (0.23.2: what 0.12 meant) (%s)" % (r.leds(0)[81],))
    for junk in ([0x91, 0, 3], [0x9F, 8 * 16, 3], [0xBE, 32, 3], [0xBF, 118, 127], [0xF8]):
        r.b.fm1_in(junk)
    r.b.tick(0.04)


def t_batching():
    r = Rig()
    for y in range(8):
        for x in range(8):
            r.b.fm1_in([0x9F, y * 16 + x, 4])
    for j in range(8):
        r.b.fm1_in([0xBE, j, 3]); r.b.fm1_in([0xBE, 16 + j, 3])
    r.b.tick(0.0)
    check(len(r.leds(0)) == 80 and not r.lp[1], "80 LEDs of one Launchpad")
    check(len(r.lp[0]) == 1 and len(r.lp[0][0]) == 7 + 80 * 5 + 1, "...in one SysEx message")
    r.b.fm1_in([0x9F, 0, 2]); r.b.tick(0.1)
    # with 81 distinct changes the message is split
    r2 = Rig()
    items = [(i, (i % 100, 1, 2)) for i in range(11, 11 + 85)]
    msgs = r2.b.lp.leds(items)
    check(len(msgs) == 2 and all(m[0] == 0xF0 and m[-1] == 0xF7 for m in msgs) and all(b < 0x80 for m in msgs for b in m[1:-1]),
          "long LED lists are split, every byte is 7-bit")
    check(all(b < 0x80 for m in r.lp[0] for b in m[1:-1]), "all SysEx bytes are 7-bit")


def t_pump():
    """0.22: one turn of the loop takes what is waiting: a frame of the FM-1's lights (eight messages in one USB packet)
    is one SysEx for the Launchpad, not eight; a pad is handled at once; a flood ends at the limit (the ticks run)"""
    import queue
    import time
    r = Rig()
    q = queue.Queue()
    for i in range(8):
        q.put(("fm1", 0, "", [0x9F, i, 4]))
    n = B.pump(q, lambda it: r.b.fm1_in(it[3]), lambda: bool(r.b.dirty), idle=0.01)
    r.b.tick(0.0)
    check(n == 8 and len(r.lp[0]) == 1 and len(r.leds(0)) == 8, "eight lights waiting: one turn, one SysEx with the eight (%d handled, %d messages)" % (n, len(r.lp[0])))
    got = []
    q.put(("lp", 0, "x", [0x90, 11, 100]))
    check(B.pump(q, got.append, lambda: False, idle=0.01) == 1 and got[0][0] == "lp", "a pad pressed: handled in the turn it comes")
    t0 = time.monotonic()
    check(B.pump(q, got.append, lambda: False, idle=0.02) == 0 and time.monotonic() - t0 < 0.5, "nothing waiting: the turn ends by itself")
    for i in range(200):
        q.put(("fm1", 0, "", [0x9F, i % 64, 1 + i % 5]))
    check(B.pump(q, lambda it: r.b.fm1_in(it[3]), lambda: bool(r.b.dirty), idle=0.01) == 64 and q.qsize() == 136, "a flood: 64 a turn, the rest at the next")
    check(B.IDLE_S >= 0.01, "the idle turn is not a busy loop (%s s)" % B.IDLE_S)


def t_blink():
    r = Rig()
    r.b.start(0.0)
    pend = B.ROLE_PEND
    r.b.fm1_in([0x9F, 5, pend]); r.b.tick(0.01)
    led = 81 + 5
    check(r.leds(0)[led] == B.RGB[pend], "PEND starts lit")
    r.b.tick(0.3)
    check(r.leds(0)[led] == (0, 0, 0), "PEND blinks off after a quarter second")
    r.b.tick(0.6)
    check(r.leds(0)[led] == B.RGB[pend], "and on again")
    r.b.fm1_in([0x9F, 5, 3]); r.b.tick(0.61); r.b.tick(0.9); r.b.tick(1.2)
    check(r.leds(0)[led] == B.RGB[3], "a pad that stops being PEND stops blinking")


def t_swap_and_guard():
    r = Rig(swap=True)
    r.b.lp_in(0, [0x90, 81, 100]); r.b.lp_in(1, [0x90, 81, 100])
    check(r.fm == [[0x9F, 8, 100], [0x9F, 0, 100]], "--swap exchanges the halves on the way in (%s)" % r.fm)
    r.fm.clear(); r.b.lp_in(0, [0xB0, 91, 127])
    check(r.fm == [[0xBE, 8, 127]], "and for the buttons")
    r.b.fm1_in([0x9F, 0, 3]); r.b.tick(0)
    check(list(r.leds(1)) == [81] and not r.lp[0], "and on the way out")
    r = Rig()
    r.b.lp_in(0, [0x90, 81, 100], port="A", now=1.000)
    r.b.lp_in(0, [0x90, 81, 100], port="B", now=1.001)
    check(len(r.fm) == 1, "the same press on a Launchpad's second MIDI port is dropped")
    r.b.lp_in(0, [0x90, 81, 100], port="A", now=1.5)
    check(len(r.fm) == 2, "a real second press is not")


def t_mk2():
    r = Rig(model="mk2")
    r.b.start(0.0)
    check(all(r.lp[i][0] == [0x90, 81, 0] for i in (0, 1)), "MK2: no set-up message (midigrid sends none), straight to blanking LEDs")
    check(all(len(r.lp[i]) == 80 and all(len(m) == 3 and m[2] == 0 for m in r.lp[i]) for i in (0, 1)),
          "MK2: 80 blank LEDs, one 3-byte message each, nothing flashing")
    check(sum(1 for m in r.lp[0] if m[0] == 0xB0) == 8 and {m[1] for m in r.lp[0] if m[0] == 0xB0} == set(range(104, 112)),
          "MK2: the top row lights by CC 104..111")
    r.fm.clear()
    r.b.lp_in(0, [0xB0, 104, 127]); r.b.lp_in(1, [0x90, 89, 127]); r.b.lp_in(0, [0x90, 81, 50])
    check(r.fm == [[0xBE, 0, 127], [0xBE, 24, 127], [0x9F, 0, 50]], "MK2: top CC 104.., side notes, pads (%s)" % r.fm)
    r.lp[0].clear()
    r.b.fm1_in([0x9F, 0, B.ROLE_NAMES.index("PLAY")]); r.b.fm1_in([0xBE, 3, B.ROLE_NAMES.index("ON")])
    r.b.tick(0.01)
    check(r.lp[0] == [[0x90, 81, 5], [0xB0, 107, 22]], "MK2: PLAY is palette 5 (red), a button LED goes by CC (%s)" % r.lp[0])
    check(B.MK2.nearest((0, 0, 0)) == 0 and B.MK2.nearest(B.ROLE_RGB["FAINT"]) != 0, "MK2: only black is black")
    check(all(B.MK2.nearest(c) in B.MK2_PALETTE for c in B.RGB) and B.MK2.nearest(B.ROLE_RGB["BLUE"]) in (45, 46),
          "MK2: every role has a palette colour, blue is blue")
    r.b.stop()
    check(r.lp[0][-80:][0][2] == 0, "MK2: stop blanks")


def t_mini():
    """the first Launchpad Mini (red / green LEDs, the X-Y layout)"""
    r = Rig(model="mini")
    r.b.start(0.0)
    check(all(r.lp[i][:2] == [[0xB0, 0, 0], [0xB0, 0, 1]] for i in (0, 1)), "Mini: reset, then the X-Y layout")
    check(all(len(r.lp[i]) == 82 and all(m[2] == 12 for m in r.lp[i][2:]) for i in (0, 1)), "Mini: 80 LEDs blanked (velocity 12 = off)")
    r.fm.clear()
    r.b.lp_in(0, [0x90, 0, 127]); r.b.lp_in(0, [0x90, 8, 127]); r.b.lp_in(1, [0xB0, 104, 127]); r.b.lp_in(1, [0x90, 7 * 16 + 7, 0])
    r.b.lp_in(0, [0x80, 0x18, 0])
    check(r.fm == [[0x9F, 0, 127], [0xBE, 16, 127], [0xBE, 8, 127], [0x9F, 127, 0], [0xBE, 17, 0]],
          "Mini: pads, the side column (note y*16+8), the top row (CC 104..111) (%s)" % r.fm)
    r.lp[0].clear(); r.lp[1].clear()
    r.b.fm1_in([0x9F, 0, B.ROLE_NAMES.index("PLAY")]); r.b.fm1_in([0xBE, 3, B.ROLE_NAMES.index("ON")])
    r.b.fm1_in([0xBE, 24, B.ROLE_NAMES.index("ON")]); r.b.tick(0.01)
    check(r.lp == {0: [[0x90, 0, 15], [0xB0, 107, 60]], 1: [[0x90, 8, 60]]}, "Mini: PLAY is red, ON green, by velocity 16*g + r + 12 (%s)" % r.lp)
    check(all(0 <= B.Mini.velocity(c) - 12 < 64 for c in B.RGB), "Mini: every role has a red / green colour")
    r.b.stop()
    check(r.lp[0][-1] == [0xB0, 0, 0], "Mini: stop resets it")


def t_heal():
    r = Rig()
    r.b.start(0.0)
    r.b.fm1_in([0x9F, 0, 3]); r.b.fm1_in([0xBE, 8, 6]); r.b.tick(0.01)
    n = [len(r.lp[0]), len(r.lp[1])]
    r.b.tick(1.99)
    check([len(r.lp[0]), len(r.lp[1])] == n, "no repaint before two seconds")
    r.b.tick(2.01)
    check(len(r.lp[0]) == n[0] + 1 and len(r.lp[1]) == n[1] + 1, "after two seconds every LED that has a role is sent again")
    check(r.leds(0)[81] == B.RGB[3] and r.leds(1)[91] == B.RGB[6], "with its colour")
    r.b.tick(2.5)
    check(len(r.lp[0]) == n[0] + 1, "and then it is quiet again")
    r.b.tick(4.02)
    check(len(r.lp[0]) == n[0] + 2, "until the next round")
    r = Rig()
    r.b.heal_s = 0
    r.b.start(0.0); r.b.fm1_in([0x9F, 0, 3]); r.b.tick(0.01); n = len(r.lp[0])
    r.b.tick(10.0); r.b.tick(20.0)
    check(len(r.lp[0]) == n, "heal_s = 0 switches it off")


def t_ports():
    names = ["Midi Through:Midi Through Port-0 14:0", "Launchpad Mini MK3:Launchpad Mini MK3 LPMiniMK3 MIDI In 32:1",
             "Launchpad Mini MK3:Launchpad Mini MK3 LPMiniMK3 DAW In 32:0",
             "Launchpad Mini MK3:Launchpad Mini MK3 LPMiniMK3 MIDI In 28:1", "Launchpad Mini MK3:Launchpad Mini MK3 LPMiniMK3 DAW In 28:0",
             "M-VAVE FM-1:M-VAVE FM-1 MIDI 1 36:0"]
    g = B.split_ports(names, "Launchpad Mini", "DAW|DIN")
    check(len(g) == 2 and "28:1" in g[0][0] and "32:1" in g[1][0], "two Launchpads, ALSA client order, DAW ports left alone (%s)" % g)
    check(B.split_ports(names, "FM-1", None) == [[names[5]]], "the FM-1 by name")
    felucca = names + ["Felucca 2:Felucca 2 MIDI 1 40:0"]
    check(B.split_ports(felucca, B.FM1_PATTERN, None) == [[names[5]], [felucca[6]]] or B.split_ports(felucca, B.FM1_PATTERN, None) == [[felucca[6]], [names[5]]],
          "the default FM-1 pattern finds both the 'FM-1' and the 'Felucca 2' name")
    check(B.split_ports(names, B.FM1_PATTERN, None) == [[names[5]]] and not B.split_ports(names[:5], B.FM1_PATTERN, None),
          "and nothing that is a Launchpad")
    check(B.plan_ports(names, names) == [(names[3], names[3]), (names[1], names[1])], "plan: one port per Launchpad, the MIDI one")
    # ALSA names without 'DAW' in them: the two ports of one client are told apart by number, the second one wins
    bare = ["Launchpad Mini MK3:Launchpad Mini MK3 MIDI 1 20:0", "Launchpad Mini MK3:Launchpad Mini MK3 MIDI 2 20:1",
            "Launchpad Mini MK3:Launchpad Mini MK3 MIDI 1 24:0", "Launchpad Mini MK3:Launchpad Mini MK3 MIDI 2 24:1"]
    p = B.plan_ports(bare, bare)
    check(p == [(bare[1], bare[1]), (bare[3], bare[3])], "plan: the second USB MIDI interface when the names do not say (%s)" % p)
    check(B.plan_ports(bare, bare, left="20:", right="24:") == p, "plan: --left / --right by pattern")
    check(B.pick_port(["x 5:0", "x 5:2", "x 5:1"]) == "x 5:2" and B.pick_port(["name only"]) == "name only", "pick_port")
    for bad, why in ((dict(), "none present"), (dict(left="20:"), "only --left")):
        try:
            B.plan_ports([names[0]] if not bad else bare, [names[0]] if not bad else bare, **bad)
            check(False, "plan must refuse: " + why)
        except SystemExit as e:
            check(bool(str(e)), "plan refuses (%s): %s" % (why, e))
    try:
        B.plan_ports(bare[:2], bare[:2])
        check(False, "one Launchpad is not enough")
    except SystemExit as e:
        check("found 1" in str(e), "plan refuses a single Launchpad: %s" % e)
    try:
        B.plan_ports(bare, bare, left="20:", right="99:")
        check(False, "a pattern that matches nothing")
    except SystemExit as e:
        check("99:" in str(e), "plan names the pattern that matched nothing")


def t_portwatch():
    state = {20: "Launchpad Mini MK3", 24: "Launchpad Mini MK3", 36: "M-VAVE FM-1", 14: "Midi Through"}
    ports = ["Launchpad Mini MK3:Launchpad Mini MK3 MIDI 2 20:1", "Launchpad Mini MK3:Launchpad Mini MK3 MIDI 2 24:1", "M-VAVE FM-1:M-VAVE FM-1 MIDI 1 36:0"]
    w = B.PortWatch(ports, read=lambda: state)
    check(sorted(w.want) == [20, 24, 36], "it watches the three clients that are in use, not the others (%s)" % w.want)
    check(w.check(0.0) is None and w.check(0.5) is None and w.check(5.0) is None, "all there: quiet")
    del state[24]
    check(w.check(5.5) is None, "it looks once a second, not more often")
    msg = w.check(6.1)
    check(msg and "24" in msg and "gone" in msg, "a client that left is reported (%s)" % msg)
    state[24] = "Launchpad Mini MK3"
    check(w.check(7.2) is None, "and when it is back under the same number it is fine again")
    state[24] = "Something else"
    msg = w.check(8.3)
    check(msg and "24" in msg and "Something else" in msg, "a number taken by another device is reported (%s)" % msg)
    check(B.PortWatch(ports, read=lambda: None).check(100.0) is None, "without /proc (not Linux) it does nothing")
    check(B.PortWatch(["no numbers in this name"], read=lambda: state).check(100.0) is None, "and with names it cannot read")
    import tempfile
    sample = 'Client info\n  cur  clients : 4\n\nClient   0 : "System" [Kernel]\n  Port   0 : "Timer" (Rwe-)\nClient  20 : "Launchpad Mini MK3" [Kernel]\n  Port   0 : "Launchpad Mini MK3 MIDI 1" (RWe-)\n  Port   1 : "Launchpad Mini MK3 MIDI 2" (RWe-)\nClient 130 : "RtMidi Input Client" [User]\n'
    with tempfile.NamedTemporaryFile("w", suffix=".txt") as f:
        f.write(sample); f.flush()
        check(B.alsa_clients(f.name) == {0: "System", 20: "Launchpad Mini MK3", 130: "RtMidi Input Client"}, "/proc/asound/seq/clients is read (%s)" % B.alsa_clients(f.name))
    check(B.alsa_clients("/nonexistent/clients") is None, "a missing file is None")
    check(B.client_number("x MIDI 2 24:1") == 24 and B.client_number("no numbers") is None, "client_number")


def t_main():
    """main() wired to a fake mido: which ports it opens and uses, a clean stop, and the exit on a port error"""
    import contextlib
    import io
    import types
    import time as real_time

    lp = ["Launchpad Mini MK3:Launchpad Mini MK3 LPMiniMK3 DAW In 20:0", "Launchpad Mini MK3:Launchpad Mini MK3 LPMiniMK3 MIDI In 20:1",
          "Launchpad Mini MK3:Launchpad Mini MK3 LPMiniMK3 DAW In 24:0", "Launchpad Mini MK3:Launchpad Mini MK3 LPMiniMK3 MIDI In 24:1"]
    fm = "Felucca 2:Felucca 2 MIDI 1 36:0"                     # what Felucca-based firmware calls itself
    names = lp + [fm]

    class Msg:
        def __init__(self, b): self.b = list(b)
        def bytes(self): return self.b
        @classmethod
        def from_bytes(cls, b): return cls(b)

    def run(fail_fm1_at, args=(), clients=None):
        log, closed = [], []

        class Port:
            def __init__(self, name): self.name = name
            def send(self, m):
                log.append((self.name, m.bytes()))
                n = sum(1 for p, _ in log if p == fm)
                if self.name == fm and n == fail_fm1_at:
                    raise (KeyboardInterrupt() if fail_fm1_at == 3 else OSError("port gone"))
            def close(self): closed.append(self.name)

        first = {lp[1]: [[0x90, 81, 100]], fm: [[0x9F, 0, 3]]}      # waiting in the queue when the loop starts

        def open_input(name, callback=None, virtual=False):
            for b in first.get(name, []):
                callback(Msg(b))
            return Port(name)

        fake = types.SimpleNamespace(get_input_names=lambda: list(names), get_output_names=lambda: list(names),
                                     open_input=open_input, open_output=lambda name, virtual=False: Port(name), Message=Msg)
        clock = [0.0]

        def monotonic():
            clock[0] += 0.3
            return clock[0]
        sys.modules["mido"] = fake
        real, real_clients = real_time.monotonic, B.alsa_clients
        real_time.monotonic = monotonic
        B.alsa_clients = (lambda *a, **k: clients(clock[0])) if clients else (lambda *a, **k: None)   # not the /proc of the machine the test runs on (clients: by the fake time)
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = B.main(list(args))
        finally:
            real_time.monotonic = real
            B.alsa_clients = real_clients
            del sys.modules["mido"]
        return rc, log, closed, out.getvalue(), err.getvalue()

    rc, log, closed, out, err = run(3)
    check(rc == 0, "Ctrl-C ends the bridge cleanly, FM-1 found by its Felucca name with the default pattern (%s)" % rc)
    check(log[0][0] == lp[1] and log[0][1] == B.MK3.HEADER + [0x0E, 0x01, 0xF7], "the first thing the left Launchpad gets is programmer mode")
    check(not any(p in (lp[0], lp[2]) for p, _ in log), "nothing is ever sent to a Launchpad's DAW port")
    check({p for p, _ in log} == {lp[1], lp[3], fm}, "only the three ports in use are written to")
    fm1 = [m for p, m in log if p == fm]
    check(fm1 == [[0xBF, 118, 127], [0x9F, 0, 100], [0xBF, 118, 64], [0xBF, 118, 0]],
          "FM-1 gets attach, the pad press from the queue, a keep-alive, and at the end detach (%s)" % fm1)
    history = []                                     # (led, rgb) in the order the left Launchpad was told
    for p, m in log:
        if p == lp[1] and m[:7] == B.MK3.HEADER + [0x03]:
            body, i = m[7:-1], 0
            while i < len(body):
                size = {1: 4, 2: 3, 3: 5}[body[i]]
                if body[i] == 3:
                    history.append((body[i + 1], tuple(body[i + 2:i + 5])))
                i += size
    check((81, B.RGB[3]) in history, "the FM-1's LED (pad 1 = ON) showed up on the left Launchpad")
    check([rgb for led, rgb in history if led == 81][-1] == (0, 0, 0), "and it was blanked again at the end")
    check(sorted(closed) == sorted([lp[1], lp[3], fm, lp[1], lp[3], fm]), "all six ports closed (%s)" % len(closed))
    check("left Launchpad" in out and "bridge running" in out, "it says which ports it chose")

    rc, log, closed, out, err = run(1)
    check(rc == 1 and "bridge stopped: OSError" in err, "a port error ends it with exit code 1, for the service to restart it (%s, %r)" % (rc, err))
    check(len(closed) == 6, "and closes the ports")

    # 0.15: no Launchpads: the bridge runs for the FM-1's side (the library, the editor's link); two plugged in: it ends,
    # for the service to start it again with them
    real_plan, calls = B.plan_ports, [0]

    def plan(*a, **k):
        calls[0] += 1
        if calls[0] < 3:
            raise SystemExit("found 0 Launchpad(s), need 2")
        return real_plan(*a, **k)
    B.plan_ports = plan
    try:
        rc, log, closed, out, err = run(99)
    finally:
        B.plan_ports = real_plan
    check(rc == 1 and "no grid" in err and "two Launchpads are here now" in err and calls[0] == 3, "no grid: it runs; the Launchpads come: it ends for a restart (%s %r)" % (rc, err))
    check(not [p for p, _ in log if p in lp] and [m for p, m in log if p == fm][:1] == [[0xBF, 118, 127]] and closed == [fm, fm],
          "meanwhile only the FM-1's port is used (%s)" % sorted({p for p, _ in log}))

    try:
        run(0, args=("--fm1", "NoSuchDevice"))
        check(False, "an --fm1 pattern that matches nothing")
    except SystemExit as e:
        check("NoSuchDevice" in str(e), "--fm1 that matches nothing is refused, naming the pattern")
    # a Launchpad is unplugged while the bridge runs: ALSA gives no error, the bridge must notice and end
    def clients(t):
        c = {20: "Launchpad Mini MK3", 24: "Launchpad Mini MK3", 36: "M-VAVE FM-1", 14: "Midi Through"}
        if t > 1.5:
            del c[24]
        return c
    rc, log, closed, out, err = run(0, clients=clients)
    check(rc == 1 and "ALSA client 24" in err and "is gone" in err, "an unplugged Launchpad ends the bridge with exit code 1 (%s, %r)" % (rc, err))
    check(len(closed) == 6, "and it closes the ports")

    try:                                         # (0.15: one Launchpad is no grid: the bridge runs without it, Ctrl-C at the 3rd FM-1 message)
        names.remove(lp[3]); names.remove(lp[2])
        rc, log, closed, out, err = run(3)
        check(rc == 0 and "no grid (found 1" in err and not [p for p, _ in log if p in lp], "one Launchpad is not a grid: it runs without (%s %r)" % (rc, err))
    finally:
        names[:] = lp + [fm]


def t_quiet_wait():
    """0.23.2: the bridge makes no ALSA client while it waits - RaspiMIDIHub takes its whole matrix down and up again at
    every client that comes or goes. It waits for the FM-1 and for the Launchpads on /proc; and it watches its own
    connections (a device the kernel made again in less than a second)."""
    raw = {0: "System", 14: "Midi Through", 20: "Launchpad Mini MK3", 36: "Felucca 2", 128: "RaspiMIDIHub", 129: "RtMidiIn Client",
           130: "RtMidiOut Client", 131: "RtMidi Input Client", 132: "RtMidi Output Client"}
    check(B.device_clients(lambda: dict(raw)) == {0: "System", 14: "Midi Through", 20: "Launchpad Mini MK3", 36: "Felucca 2", 128: "RaspiMIDIHub"}
          and B.device_clients(lambda: None) is None, "the devices: ALSA's clients without RtMidi's own (the bridge's ports, a look at the names)")
    # wait_ports: a look only when the devices changed
    state = {"clients": {14: "Midi Through"}, "names": ["Midi Through:Midi Through Port-0 14:0"]}
    looks, sleeps, turns = [], [], [0]

    def read():
        turns[0] += 1
        if turns[0] == 4:                                       # an RtMidi client (another program's look): not a device
            c = dict(state["clients"]); c[129] = "RtMidiIn Client"
            return B.device_clients(lambda: c)
        if turns[0] == 6:                                       # a synth is plugged in: a device, not the FM-1
            state["clients"][40] = "MicroFreak"
            state["names"].append("MicroFreak:MicroFreak MIDI 1 40:0")
        if turns[0] == 11:                                      # the FM-1 comes
            state["clients"][36] = "Felucca 2"
            state["names"].append("Felucca 2:Felucca 2 MIDI 1 36:0")
        return B.device_clients(lambda: dict(state["clients"]))

    def look():
        looks.append(turns[0])
        return list(state["names"]), list(state["names"])
    have = lambda i, o: bool(B.split_ports(i, B.FM1_PATTERN, None) and B.split_ports(o, B.FM1_PATTERN, None))
    got = B.wait_ports(have, look, {14: "Midi Through"}, read=read, sleep=sleeps.append, every=1.0, settle=0.5)
    check(len(looks) == 2 and have(got[0], got[1]) and got[2] == {14: "Midi Through", 40: "MicroFreak", 36: "Felucca 2"},
          "waiting for the FM-1: the ports are looked at twice in all - when the synth came, when the FM-1 came - never in between (%s looks, at reads %s)" % (len(looks), looks))
    check(sleeps.count(0.5) == 2 and sleeps.count(1.0) >= 8, "a read of /proc every second, half a second for a device to settle before a look (%s)" % sleeps[:6])
    got = B.wait_ports(lambda i, o: True, lambda: (["x"], ["y"]), None, read=lambda: None, sleep=lambda s: None, every=0, settle=0)
    check(got[:2] == (["x"], ["y"]), "no /proc: a look every turn, as before")
    # ALSA's connections as /proc shows them
    import tempfile
    sample = ('Client info\n  cur  clients : 6\n  peak clients : 9\n  max  clients : 192\n\n'
              'Client   0 : "System" [Kernel Legacy]\n  Port   0 : "Timer" (Rwe-) [In/Out]\n  Port   1 : "Announce" (R-e-) [In/Out]\n    Connecting To: 128:1\n'
              'Client  20 : "Launchpad Mini" [Kernel Legacy]\n  Port   0 : "Launchpad Mini MIDI 1" (RWeX) [In/Out]\n    Connecting To: 129:0[r:0]\n    Connected From: 130:0\n'
              'Client  36 : "Felucca 2" [Kernel Legacy]\n  Port   0 : "Felucca 2 MIDI 1" (RWeX) [In/Out]\n    Connecting To: 128:0, 140:0\n'
              '  Port   1 : "Felucca 2 MIDI 2" (RWeX) [In/Out]\n    Connecting To: 131:0[r:1], 128:0[ex]\n    Connected From: 132:0, 128:3\n'
              'Client 128 : "RaspiMIDIHub" [User Legacy]\n  Port   0 : "monitor" (-We-) [In]\n    Connected From: 36:0, 36:1\n  Input pool :\n    Pool size          : 2000\n'
              'Client 131 : "RtMidiIn Client" [User Legacy]\n  Port   0 : "RtMidi input" (-We-) [In]\n    Connected From: 36:1\n')
    with tempfile.NamedTemporaryFile("w", suffix=".txt") as f:
        f.write(sample); f.flush()
        to, frm = B.alsa_links(f.name)
    check(to.get((36, 1)) == {(131, 0), (128, 0)} and frm.get((36, 1)) == {(132, 0), (128, 3)} and to.get((20, 0)) == {(129, 0)} and frm.get((20, 0)) == {(130, 0)}
          and to.get((36, 0)) == {(128, 0), (140, 0)} and (36, 0) not in frm and to.get((0, 1)) == {(128, 1)},
          "/proc/asound/seq/clients: who each port sends to and hears, the [r:0] and [ex] marks left out (%s)" % sorted(to.items()))
    check(B.alsa_links("/nonexistent/clients") is None, "a missing file is None")
    # PortWatch: the bridge's own connections
    clients = {20: "Launchpad Mini", 36: "Felucca 2", 128: "RaspiMIDIHub", 129: "RtMidiIn Client", 130: "RtMidiOut Client", 131: "RtMidiIn Client", 132: "RtMidiOut Client"}
    links = [dict((k, set(v)) for k, v in to.items()), dict((k, set(v)) for k, v in frm.items())]
    ports = ["Launchpad Mini:Launchpad Mini MIDI 1 20:0", "Felucca 2:Felucca 2 MIDI 2 36:1"]
    w = B.PortWatch(ports, read=lambda: clients, links=lambda: tuple(links), mine={129, 130, 131, 132})
    check(sorted(w.armed) == [(0, 20, 0), (0, 36, 1), (1, 20, 0), (1, 36, 1)], "the four connections of the bridge's own are watched (%s)" % sorted(w.armed))
    check(w.check(0.0) is None and w.check(1.1) is None, "all there: quiet")
    links[0][(128, 9)] = {(20, 0)}                              # RaspiMIDIHub rebuilding its matrix: not the bridge's business
    links[0][(36, 0)] = set()
    check(w.check(2.2) is None, "RaspiMIDIHub's own connections come and go: nothing said")
    links[0][(36, 1)] = {(128, 0)}                              # the FM-1 made again by the kernel: same number, same name, the bridge's connections gone
    links[1][(36, 1)] = {(128, 3)}
    msg = w.check(3.3)
    check(msg and "36:1" in msg and "Felucca 2" in msg and "made again" in msg, "the FM-1 made again in less than a second (same client, same name): the bridge's connection is gone, said (%s)" % msg)
    links[0][(36, 1)], links[1][(36, 1)] = {(131, 0), (128, 0)}, {(132, 0)}
    links[1][(20, 0)] = set()
    msg = w.check(4.4)
    check(msg and "to ALSA port 20:0" in msg, "a Launchpad's light road gone: said (%s)" % msg)
    w = B.PortWatch(ports, read=lambda: clients, links=lambda: tuple(links), mine=set())
    check(not w.armed and w.check(9.0) is None, "the bridge's clients not known (no /proc at the start, a mido that makes none): only the devices are watched")
    w = B.PortWatch(ports, read=lambda: clients, links=lambda: None, mine={131})
    check(not w.armed and w.check(9.0) is None, "connections that cannot be read: only the devices are watched")
    w = B.PortWatch(ports, read=lambda: clients, links=lambda: ({}, {}), mine={131, 132})
    check(not w.armed, "connections /proc does not show at the start are never asked for later (no restart for a file read wrong)")
    # main(): no FM-1 at the start - it waits (it ended, and the service started it again every two seconds); no Launchpads -
    # the ports are looked at again only when a device comes
    import contextlib
    import io
    import types
    import time as real_time
    lp = ["Launchpad Mini MK3:Launchpad Mini MK3 LPMiniMK3 MIDI In 20:1", "Launchpad Mini MK3:Launchpad Mini MK3 LPMiniMK3 MIDI In 24:1"]
    fm = "Felucca 2:Felucca 2 MIDI 1 36:0"

    class Msg:
        def __init__(self, b): self.b = list(b)
        def bytes(self): return self.b
        @classmethod
        def from_bytes(cls, b): return cls(b)

    def run_main(world, stop_at):
        """world(reads of /proc so far, fake time) -> (ALSA clients, port names); Ctrl-C at the FM-1's stop_at-th message"""
        log, looks, reads, clock = [], [0], [0], [0.0]

        class Port:
            def __init__(self, name): self.name = name
            def send(self, m):
                log.append((self.name, m.bytes()))
                if self.name == fm and sum(1 for q, _ in log if q == fm) == stop_at:
                    raise KeyboardInterrupt()
            def close(self): pass

        def names():
            looks[0] += 1
            return list(world(reads[0], clock[0])[1])

        def clients(*a, **k):
            reads[0] += 1
            return dict(world(reads[0], clock[0])[0])

        def monotonic():
            clock[0] += 0.3
            return clock[0]
        fake = types.SimpleNamespace(get_input_names=names, get_output_names=lambda: list(world(reads[0], clock[0])[1]),
                                     open_input=lambda name, callback=None, virtual=False: Port(name),
                                     open_output=lambda name, virtual=False: Port(name), Message=Msg)
        sys.modules["mido"] = fake
        keep = (real_time.monotonic, B.alsa_clients, B.WAIT_EVERY_S, B.WAIT_SETTLE_S)
        real_time.monotonic, B.alsa_clients, B.WAIT_EVERY_S, B.WAIT_SETTLE_S = monotonic, clients, 0.0, 0.0
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = B.main([])
        finally:
            real_time.monotonic, B.alsa_clients, B.WAIT_EVERY_S, B.WAIT_SETTLE_S = keep
            del sys.modules["mido"]
        return rc, log, looks[0], reads[0], err.getvalue()

    base = {14: "Midi Through", 20: "Launchpad Mini MK3", 24: "Launchpad Mini MK3"}

    def fm1_later(n, t):
        if n < 40:
            return base, lp
        return {**base, 36: "Felucca 2"}, lp + [fm]
    rc, log, looks, reads, err = run_main(fm1_later, 3)
    check(rc == 0 and "the bridge waits for it" in err and looks == 2 and reads >= 40,
          "no FM-1: the bridge waits on /proc (%d reads) and looks at the ports twice in all - at the start, when the FM-1 came (%d looks; rc %s)" % (reads, looks, rc))
    check([m for q, m in log if q == fm][:1] == [[0xBF, 118, 127]] and {q for q, _ in log} == set(lp + [fm]), "then it runs with the grid: the FM-1 gets its attach (%s)" % sorted({q for q, _ in log}))

    # 0.25: the FM-1 while a firmware is being installed is another USB device, "Felucca Update" (its update loader), on
    # the client number the FM-1 had. It is NOT the FM-1: the bridge waits (0.24 attached to it: an attach and a
    # keep-alive a second on the port the firmware goes through - seen in a log of a real install)
    upd = "Felucca Update:Felucca Update MIDI 1 36:0"

    def updating(n, t):
        if n < 40:
            return {**base, 36: "Felucca Update"}, lp + [upd]
        return {**base, 36: "Felucca 2"}, lp + [fm]
    rc, log, looks, reads, err = run_main(updating, 3)
    check(rc == 0 and "the bridge waits for it" in err and not [m for q, m in log if q == upd],
          "the FM-1 in update mode is not the FM-1: nothing is sent to it, the bridge waits (%s; %d messages to it)" % (
              err.strip().splitlines()[0][:40] if err.strip() else "", len([m for q, m in log if q == upd])))
    check([m for q, m in log if q == fm][:1] == [[0xBF, 118, 127]] and reads >= 40,
          "... and when the FM-1 is back with its firmware it gets its attach (%d reads)" % reads)
    check(B.fm1_ports([upd, fm], B.FM1_PATTERN) == [[fm]] and not B.fm1_ports([upd], B.FM1_PATTERN) and B.split_ports([upd], B.FM1_PATTERN, None),
          "fm1_ports: the loader's port is left out (the bare pattern still matches it: a synth's port it is not either)")

    def no_grid(n, t):
        return {14: "Midi Through", 36: "Felucca 2"}, [fm]
    rc, log, looks, reads, err = run_main(no_grid, 12)          # (attach + eleven keep-alives: more than eleven fake seconds)
    check(rc == 0 and "no grid" in err and looks == 1 and reads > 4,
          "no Launchpads, nothing changing: the ports are looked at once, at the start - not every 3 s (%d looks in %d reads of /proc)" % (looks, reads))

    def grid_later(n, t):
        if t < 8.0:
            return {14: "Midi Through", 36: "Felucca 2"}, [fm]
        if t < 16.0:                                            # a synth first: a look, no grid yet
            return {14: "Midi Through", 36: "Felucca 2", 40: "MicroFreak"}, [fm, "MicroFreak:MicroFreak MIDI 1 40:0"]
        return {14: "Midi Through", 36: "Felucca 2", 40: "MicroFreak", 20: "Launchpad Mini MK3", 24: "Launchpad Mini MK3"}, [fm, "MicroFreak:MicroFreak MIDI 1 40:0"] + lp
    rc, log, looks, reads, err = run_main(grid_later, 99)
    check(rc == 1 and "two Launchpads are here now" in err and looks == 3,
          "a synth comes: one look; the Launchpads come: one look, and the bridge ends for a restart with them (%d looks; %r)" % (looks, err[-90:]))
    # stopped by the service (systemctl stop: the banco does it, a shutdown): the Launchpads dark, the FM-1 told - as Ctrl-C
    import signal
    import threading

    def all_there(n, t):
        return {**base, 36: "Felucca 2"}, lp + [fm]
    before = signal.getsignal(signal.SIGTERM)

    def stopper():                                              # (once main() has its own handler, a moment in its loop)
        t0 = real_time.time()
        while signal.getsignal(signal.SIGTERM) is before and real_time.time() - t0 < 20.0:
            real_time.sleep(0.01)
        real_time.sleep(0.3)
        os.kill(os.getpid(), signal.SIGTERM)
    threading.Thread(target=stopper, daemon=True).start()
    try:
        rc, log, looks, reads, err = run_main(all_there, 10 ** 9)
    finally:
        signal.signal(signal.SIGTERM, before)
    last = {q: [m for qq, m in log if qq == q][-1] for q in lp + [fm]}
    check(rc == 0 and last[fm] == [0xBF, 118, 0] and all(last[q] == B.MK3.HEADER + [0x0E, 0x00, 0xF7] for q in lp) and "bridge stopped" not in err,
          "SIGTERM: the bridge ends as with Ctrl-C - the FM-1 gets the detach, the Launchpads are blanked and back in live mode (rc %s, %s)" % (rc, last[fm]))
    blank = [m for q, m in log if q == lp[0] and m[:7] == B.MK3.HEADER + [0x03]][-1]
    check(len(blank) > 100 and all(v == 0 for i in range(7, len(blank) - 1, 5) for v in blank[i + 2:i + 5]), "... every light of a Launchpad off before it goes (%d bytes)" % len(blank))


def t_synth_ports():
    """0.23.2: the snapshot patches' synth ports are opened once and kept - a port opened or closed at every snapshot
    was an ALSA client that came and went in the music (RaspiMIDIHub takes its matrix down and up again at each)."""
    import contextlib
    import io
    import json
    import tempfile
    import types
    import time as real_time
    check(B.links_touch(({(36, 1): {(131, 0)}}, {}), {131}) and B.links_touch(({}, {(131, 0): {(36, 1)}}), {131})
          and not B.links_touch(({(36, 1): {(128, 0)}}, {(128, 3): {(36, 1)}}), {131}) and not B.links_touch(({}, {}), {131}),
          "a client is in ALSA's connections when it is at either end of one")

    class World:
        """a fake ALSA: the synth ports there, the clients (a port opened makes one), the connections of those"""
        def __init__(self, proc=True):
            self.names, self.proc = ["MicroFreak:MicroFreak MIDI 1 40:0", "Felucca 2:Felucca 2 MIDI 2 36:1"], proc
            self.looks, self.opened, self.closed, self.sent, self.cb, self.next, self.live = 0, [], [], [], {}, 140, {}

        def look(self):
            self.looks += 1
            return list(self.names), list(self.names)

        def _port(self, name):
            if name not in self.names:
                raise IOError("no such port")
            cid, self.next = self.next, self.next + 1
            self.opened.append(name)
            self.live[cid] = name
            return cid

        def open_out(self, name):
            cid = self._port(name)
            return (lambda m: self.sent.append((cid, list(m)))), (lambda: (self.closed.append(cid), self.live.pop(cid, None)))

        def open_in(self, name, on_bytes):
            cid = self._port(name)
            self.cb[cid] = on_bytes
            return lambda: (self.closed.append(cid), self.live.pop(cid, None))

        def clients(self):
            if not self.proc:
                return None
            out = {40: "MicroFreak", 36: "Felucca 2"}
            out.update({c: "RtMidiOut Client" for c in self.live})
            return out

        def links(self):
            return ({(c, 0): {(40, 0)} for c in self.live}, {}) if self.proc else None
    got = []
    w = World()
    sp = B.SynthPorts(w.look, w.open_out, w.open_in, B.FM1_PATTERN, lambda nm, raw: got.append((nm, raw)), clients=w.clients, links=w.links)
    a = sp.open("MicroFreak", "MF")
    check(a is not None and w.looks == 1 and w.opened == [w.names[0]] * 2, "a synth's port opened: one look, its output and its input (%s)" % w.opened)
    a[0]([0xF0, 1, 0xF7]); a[1]()
    b = sp.open("MicroFreak", "MF"); b[0]([0xF0, 2, 0xF7]); b[1]()
    c = sp.open("MicroFreak", "MF"); c[0]([0xF0, 3, 0xF7]); c[1]()
    check(w.looks == 1 and len(w.opened) == 2 and not w.closed and [m for _, m in w.sent] == [[0xF0, 1, 0xF7], [0xF0, 2, 0xF7], [0xF0, 3, 0xF7]],
          "asked for again and again (a snapshot, another): no look, nothing opened, nothing closed - the same port carries them (%d looks, %d opened, %d closed)"
          % (w.looks, len(w.opened), len(w.closed)))
    cid_in = [k for k in w.cb][0]
    w.cb[cid_in]([0xF0, 0x41, 0xF7]); w.cb[cid_in]([0xF8]); w.cb[cid_in]([0x90, 60, 100]); w.cb[cid_in]([])
    check(got == [("MF", [0xF0, 0x41, 0xF7])], "the kept input hands on the synth's SysEx only - not its clock or its notes (%s)" % got)
    check(sp.open("Nothing here", "Absent") is None and "Absent" not in sp.kept and w.looks == 2, "a synth that is not there: None, nothing kept")
    check(sp.open("Felucca", "FM") is None, "the FM-1's own port is never a synth's")
    # the synth unplugged and back under the same number: ALSA no longer shows the kept port's connections
    old = dict(w.live)
    w.live.clear()                                              # (the kernel dropped them; the port objects are still held)
    looks0 = w.looks
    d2 = sp.open("MicroFreak", "MF")
    check(d2 is not None and w.looks == looks0 + 1 and len(w.opened) == 4 and sorted(w.closed) == sorted(old),
          "a kept port whose connections are gone: closed, and opened again when it is asked for (%d opened, closed %s)" % (len(w.opened), w.closed))
    d2[0]([0xF0, 9, 0xF7])
    check(w.sent[-1][1] == [0xF0, 9, 0xF7] and w.sent[-1][0] not in old, "... and the patch goes out of the new one")
    # open_all / drop: what main() does at its start and when a device comes or goes
    sp.drop()
    check(not sp.kept and not w.live, "drop: every kept port closed")
    two = [dict(name="MF", port="MicroFreak"), dict(name="TD3", port="TD-3")]
    looks0 = w.looks
    here = sp.open_all(two)
    check(here == ["MF"] and list(sp.kept) == ["MF"] and w.looks == looks0 + 1, "open_all: the synths that are there, one look for all of them (%s)" % here)
    opened0, closed0 = len(w.opened), len(w.closed)
    w.names.append("TD-3:TD-3 MIDI 1 44:0")                     # another synth plugged in: a device came
    here = sp.open_all(two)
    check(here == ["MF", "TD3"] and w.looks == looks0 + 2 and len(w.opened) == opened0 + 2 and len(w.closed) == closed0,
          "a device came: the synth not open yet is opened; the port that was good is not touched (%s, %d opened, %d closed)" % (here, len(w.opened) - opened0, len(w.closed) - closed0))
    here = sp.open_all(two)
    check(here == ["MF", "TD3"] and w.looks == looks0 + 2 and len(w.opened) == opened0 + 2, "a device came and every synth's port is open: no look, nothing opened")
    td = [c for c, nm in w.live.items() if nm.startswith("TD-3")]
    for c in td:
        del w.live[c]                                           # the TD-3 unplugged: its connections gone
    w.names.pop()
    here = sp.open_all(two)
    check(here == ["MF"] and sorted(w.closed[closed0:]) == sorted(td) and w.looks == looks0 + 3,
          "a synth went: its kept port is closed, it is looked for (not there); the other stays (%s)" % here)
    # an input that cannot be opened: the output opened before it is closed, nothing kept
    w2 = World()
    def bad_in(name, on_bytes):
        raise IOError("busy")
    sp2 = B.SynthPorts(w2.look, w2.open_out, bad_in, B.FM1_PATTERN, lambda nm, raw: None, clients=w2.clients, links=w2.links)
    check(sp2.open("MicroFreak", "MF") is None and not sp2.kept and not w2.live and len(w2.closed) == 1, "a port that fails to open: None, what was opened is closed")
    # not a Pi (no /proc to watch a kept port with): opened and closed each time, as before
    w3 = World(proc=False)
    sp3 = B.SynthPorts(w3.look, w3.open_out, w3.open_in, B.FM1_PATTERN, lambda nm, raw: None, clients=w3.clients, links=w3.links)
    for k in range(2):
        e = sp3.open("MicroFreak", "MF"); e[0]([0xF0, k, 0xF7]); e[1]()
    check(w3.looks == 2 and len(w3.opened) == 4 and len(w3.closed) == 4 and not sp3.kept and sp3.open_all([dict(name="MF", port="MicroFreak")]) == [],
          "no /proc: nothing kept - a look, the ports opened and closed, every time (%d looks, %d closed)" % (w3.looks, len(w3.closed)))
    # the PatchKeeper on kept ports: KEEP listens and its finish closes nothing; PLAY after PLAY, not a look
    d = tempfile.mkdtemp()
    w4 = World()
    to_fm1 = []
    wr = lambda folder: B.BootWriter(folder, run=lambda cmd: None, mounts=lambda: [("/", ["rw"])])
    synths = [dict(name="MF", port="MicroFreak", request=[0xF0, 0x7E, 0xF7], wait=3.0)]
    holder = {}
    sp4 = B.SynthPorts(w4.look, w4.open_out, w4.open_in, B.FM1_PATTERN, lambda nm, raw: holder["k"].synth_in(nm, raw), clients=w4.clients, links=w4.links)
    k = holder["k"] = B.PatchKeeper(d, synths, to_fm1.append, sp4.open, writer=wr, log=lambda x: None)
    sp4.open_all(synths)
    looks0, opened0 = w4.looks, len(w4.opened)
    pid = 0x00ABCDEF
    k.fm1_sysex(B.SX_HEAD + [0x41, 0] + B.put7(pid, 5) + [1, 0xF7], 10.0)
    check([m for _, m in w4.sent] == [[0xF0, 0x7E, 0xF7]], "KEEP: the request goes out of the kept port")
    w4.cb[[c for c in w4.cb][0]]([0xF0, 0x00, 0x20, 0x6B, 0x55, 0xF7])   # the synth answers
    k.tick(14.0)
    check(to_fm1 == [B.SX_HEAD + [0x42, 0, 1, 0xF7]] and not w4.closed, "its answer is kept; the KEEP's end closes no port (%s, closed %s)" % (to_fm1, w4.closed))
    for n in range(3):
        k.fm1_sysex(B.SX_HEAD + [0x40, 0] + B.put7(pid, 5) + [1, 0xF7], 20.0 + n)
    check([m for _, m in w4.sent][1:] == [[0xF0, 0x00, 0x20, 0x6B, 0x55, 0xF7]] * 3 and w4.looks == looks0 and len(w4.opened) == opened0 and not w4.closed,
          "the snapshot back three times while playing: the patch sent three times, no look, no port opened or closed (%d looks, %d opened)" % (w4.looks - looks0, len(w4.opened) - opened0))
    # main(): with a patches.json the synth's port is opened at the start, and again when a device comes - no look in between
    fm = "Felucca 2:Felucca 2 MIDI 1 36:0"
    mf = "MicroFreak:MicroFreak MIDI 1 40:0"
    cfg = os.path.join(d, "patches.json")
    json.dump({"synths": [{"name": "MF", "port": "MicroFreak"}]}, open(cfg, "w"))
    sdir = os.path.join(d, "patches", "%08x" % pid, "s1")
    os.makedirs(sdir, exist_ok=True)
    open(os.path.join(sdir, "MF.syx"), "wb").write(bytes([0xF0, 0x00, 0x20, 0x6B, 0x66, 0xF7]))

    class Msg:
        def __init__(self, b): self.b = list(b)
        def bytes(self): return self.b
        @classmethod
        def from_bytes(cls, b): return cls(b)

    def run_main(world, stop_at, plays):
        """world(fake time) -> (ALSA devices, port names); a PLAY of snapshot 1 from the FM-1 after each of its
        `plays`-th messages; Ctrl-C at the FM-1's stop_at-th message"""
        log, looks, opened, clock, cbs = [], [0], [], [0.0], {}

        class Port:
            def __init__(self, name, callback=None):
                self.name = name
                opened.append(name)
                if callback is not None:
                    cbs[name] = callback
            def send(self, m):
                log.append((self.name, m.bytes(), looks[0]))
                if self.name == fm:
                    n = sum(1 for q, _, _ in log if q == fm)
                    if n in plays:
                        cbs[fm](Msg(B.SX_HEAD + [0x40, 0] + B.put7(pid, 5) + [1, 0xF7]))
                    if n == stop_at:
                        raise KeyboardInterrupt()
            def close(self): pass

        def names():
            looks[0] += 1
            return list(world(clock[0])[1])

        def monotonic():
            clock[0] += 0.3
            return clock[0]
        fake = types.SimpleNamespace(get_input_names=names, get_output_names=lambda: list(world(clock[0])[1]),
                                     open_input=lambda name, callback=None, virtual=False: Port(name, callback),
                                     open_output=lambda name, virtual=False: Port(name), Message=Msg)
        sys.modules["mido"] = fake
        keep = (real_time.monotonic, B.alsa_clients, B.alsa_links)
        real_time.monotonic, B.alsa_clients, B.alsa_links = monotonic, (lambda *a, **k: dict(world(clock[0])[0])), (lambda *a, **k: None)
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = B.main(["--dump-dir", d, "--patches", cfg])
        finally:
            real_time.monotonic, B.alsa_clients, B.alsa_links = keep
            del sys.modules["mido"]
        return rc, log, looks[0], opened, out.getvalue(), err.getvalue()

    rc, log, looks, opened, out, err = run_main(lambda t: ({14: "Midi Through", 36: "Felucca 2", 40: "MicroFreak"}, [fm, mf]), 14, {3, 6, 9})
    patches = [(m, lk) for q, m, lk in log if q == mf]
    check(rc == 0 and "snapshot patches: MF (ports open: MF)" in out and [m for m, _ in patches] == [[0xF0, 0x00, 0x20, 0x6B, 0x66, 0xF7]] * 3,
          "main() with a patches.json: the synth's port opened at the start, the snapshot's patch sent at each of three PLAYs (%s; %r)" % (len(patches), err[-120:]))
    check(looks == 2 and opened.count(mf) == 2 and all(lk == 2 for _, lk in patches),
          "... two looks at the ports in all (the bridge's start, the synth's port), none at a PLAY; the synth's port opened once (%d looks, %s)" % (looks, opened))

    def synth_later(t):
        if t < 9.0:
            return {14: "Midi Through", 36: "Felucca 2"}, [fm]
        return {14: "Midi Through", 36: "Felucca 2", 40: "MicroFreak"}, [fm, mf]
    rc, log, looks, opened, out, err = run_main(synth_later, 30, {25, 27})
    patches = [(m, lk) for q, m, lk in log if q == mf]
    check(rc == 0 and "snapshot patches: MF (ports open: none)" in out and "snapshot patches: ports open: MF" in out and len(patches) == 2,
          "a synth plugged in later: its port is opened when it comes (said), and the patches go (%d; %r)" % (len(patches), out[-160:]))
    check(len({lk for _, lk in patches}) == 1 and opened.count(mf) == 2,
          "... opened then, once - not at the snapshots (%s looks at the two PLAYs, %s)" % ([lk for _, lk in patches], opened))


def t_end_to_end():
    """Launchpad presses -> bridge -> the real firmware (host simulator) -> its LED messages -> bridge -> Launchpad LEDs"""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import sagga_sim_tests as S
    r = Rig()
    presses = [(300, 0, [0x90, 81, 100]), (360, 0, [0x90, 81, 0]),          # left Launchpad, top-left pad: step 1
               (500, 1, [0x90, 88, 90]), (560, 1, [0x80, 88, 0]),           # right Launchpad, top-right pad: step 16
               (1000, 0, [0xB0, 91, 127]), (1040, 0, [0xB0, 91, 0])]        # top button 1: PLAY
    script = S.Script()
    r.b.start(0.0)
    for m in r.fm:
        script.raw(100, "attach")
    for t, lp, msg in presses:
        r.fm.clear()
        r.b.lp_in(lp, msg)
        for st, d1, d2 in r.fm:
            if st == 0x9F:
                script.at(t, "pad", d1 & 15, d1 >> 4, d2)
            elif st == 0xBE:
                script.at(t, "ctl", d1, d2)
    S.build()
    try:
        log = S.run(script, 1700)
    finally:
        os.remove(S.BIN)
    r2 = Rig()
    for t, st, d1, d2 in log.msgs:
        if st in (0x9F, 0xBE):
            r2.b.fm1_in([st, d1, d2])
    r2.b.tick(0.0)
    names = {v: k for k, v in enumerate(B.ROLE_NAMES)}
    check(r2.leds(0)[81] == B.RGB[names["ON"]], "step 1 is green on the left Launchpad (%s)" % (r2.leds(0).get(81),))
    check(r2.leds(1)[88] == B.RGB[names["CURSOR"]], "step 16, the cursor, is amber on the right Launchpad (%s)" % (r2.leds(1).get(88),))
    check(r2.leds(0)[91] == B.RGB[names["ON"]], "the PLAY button lights up after the press that started the transport")
    check(len(log.clock()) > 20, "the press on the Launchpad did start the transport")
    check(len(r2.leds(0)) >= 80 and len(r2.leds(1)) >= 80, "both Launchpads got a full repaint")


# ----------------------------------------------------------------------------------------------- project dumps
class FakeFM1:
    """the FM-1's side of an import, as firmware/src/sagga_store.c does it (to test the sender without hardware)"""

    def __init__(self, playing=False, lose=(), damage=()):
        self.img, self.on, self.next, self.count, self.got = bytearray(0x8000), False, 0, 0, 0
        self.playing, self.lose, self.damage, self.replies, self.project = playing, set(lose), set(damage), [], None

    def status(self, code, idx):
        self.replies.append(B.SX_HEAD + [B.SX_STATUS, code] + B.put7(idx, 2) + [0xF7])

    def rx(self, msg):
        cmd, body = B.sx_cmd(msg), msg[5:-1]
        if cmd == B.SX_DATA:
            idx, cnt = B.get7(body[0:2]), B.get7(body[2:4])
            if idx in self.damage:
                self.damage.discard(idx)
                return self.status(2, idx)
            if idx == 0 and self.playing:
                return self.status(1, idx)
            if self.on and idx and idx + 1 == self.next and cnt == self.count:
                return self.status(0, idx)
            if idx == 0:
                self.on, self.next, self.count = True, 0, cnt
            if not self.on or idx != self.next:
                return self.status(3, idx)
            data = B.unpack7(body[4:-1])
            self.img[idx * 256:idx * 256 + len(data)] = data
            self.got, self.next = idx * 256 + len(data), self.next + 1
            if idx in self.lose:
                self.lose.discard(idx)
                return                                   # the answer is lost on the way
            self.status(0, idx)
        elif cmd == B.SX_END:
            ln, crc = B.get7(body[0:3]), B.get7(body[3:8])
            ok = self.on and self.next == self.count and ln == self.got and B.zlib.crc32(bytes(self.img[:ln])) == crc
            self.on = False
            if ok:
                self.project = bytes(self.img[:ln])
            self.status(0 if ok else 4, B.SX_LAST)


def t_dump_codec():
    import random
    rnd = random.Random(7)
    for n in list(range(0, 20)) + [255, 256, 257, 1000]:
        data = bytes(rnd.randrange(256) for _ in range(n))
        packed = B.pack7(data)
        if not (all(b < 128 for b in packed) and B.unpack7(packed)[:n] == data and len(B.unpack7(packed)) == n):
            check(False, "pack7 / unpack7 round trip of %d bytes" % n)
            return
    check(True, "pack7 / unpack7: 7-bit, and back to the same bytes, any length")
    check(len(B.pack7(bytes(256))) == 293, "256 bytes pack into 293 (a frame of 304 fits the FM-1's 640)")
    check(B.get7(B.put7(0xCBF43926, 5)) == 0xCBF43926 and B.put7(300, 2) == [44, 2], "7-bit numbers, LSB first")
    image = B.PROJECT_MAGIC + bytes(rnd.randrange(256) for _ in range(1500))
    frames = B.dump_frames(image)
    check(len(frames) == 7 and all(f[0] == 0xF0 and f[-1] == 0xF7 and all(b < 128 for b in f[1:-1]) for f in frames),
          "an image of 1504 bytes: 6 chunks and the end, all SysEx-safe")
    check(max(len(f) for f in frames) == 304, "no frame over 304 bytes (%d)" % max(len(f) for f in frames))
    check(B.export_request() == [0xF0, 0x7D, 0x53, 0x47, 0x01, 0xF7] and B.export_request(2)[5] == 2, "the export request")


def t_dump_receiver():
    image = B.PROJECT_MAGIC + bytes(range(256)) * 5
    r = B.DumpReceiver()
    got = [r.feed(f) for f in B.dump_frames(image)]
    check(got[:-1] == [None] * (len(got) - 1) and got[-1] == ("image", image), "the receiver puts an export back together")
    frames = B.dump_frames(image)
    bad = list(frames[2]); bad[20] ^= 1
    r = B.DumpReceiver()
    got = [r.feed(f) for f in frames[:2] + [bad]]
    check(got[-1][0] == "error" and "damaged" in got[-1][1], "a damaged chunk is reported (%s)" % (got[-1],))
    r = B.DumpReceiver()
    got = [r.feed(f) for f in frames[:2] + frames[3:]]
    check(got[-1] == ("error", "chunks are missing"), "a missing chunk is reported")
    r = B.DumpReceiver()
    got = [r.feed(f) for f in frames[:-1]] + [r.feed(frames[-1][:9] + [frames[-1][9] ^ 1] + frames[-1][10:])]
    check(got[-1][0] == "error" and "CRC" in got[-1][1], "a wrong CRC is reported")
    r = B.DumpReceiver()
    check(r.feed(B.SX_HEAD + [B.SX_STATUS, 1, 0, 0, 0xF7])[0] == "error", "the FM-1's 'busy' answer to an export is reported")
    check(r.feed([0xF0, 0x00, 0x20, 0x29, 0x02, 0x0D, 0x0E, 0x01, 0xF7]) is None and r.feed([0xF8]) is None, "other SysEx and bytes are none of its business")


def t_dump_sender():
    def run(fm, image, timeout=1.0):
        t = [0.0]
        snd = B.DumpSender(image, fm.rx, timeout=timeout)
        snd.start(t[0])
        for _ in range(500):
            t[0] += 0.05
            while fm.replies:
                snd.feed(fm.replies.pop(0), t[0])
            snd.tick(t[0])
            if snd.state != "sending":
                break
        return snd
    image = B.PROJECT_MAGIC + bytes(range(256)) * 9
    fm = FakeFM1()
    snd = run(fm, image)
    check(snd.state == "done" and fm.project == image, "an import arrives whole (%s %s)" % (snd.state, snd.error))
    fm = FakeFM1(lose=[3])
    snd = run(fm, image)
    check(snd.state == "done" and fm.project == image, "an answer lost on the way: the chunk goes again and is taken (%s)" % snd.error)
    fm = FakeFM1(damage=[0, 5])
    snd = run(fm, image)
    check(snd.state == "done" and fm.project == image, "damaged chunks are sent again (%s)" % snd.error)
    fm = FakeFM1(playing=True)
    snd = run(fm, image)
    check(snd.state == "failed" and "busy" in snd.error and fm.project is None, "a playing FM-1 says busy: nothing is changed (%s)" % snd.error)
    snd = run(type("Dead", (), {"rx": lambda self, m: None, "replies": []})(), image)
    check(snd.state == "failed" and "does not answer" in snd.error, "no answer: it gives up after the retries")


def t_dump_files():
    import tempfile
    d = tempfile.mkdtemp()
    a = B.save_image(B.PROJECT_MAGIC + b"abc", d, when=1700000000)
    b = B.save_image(B.PROJECT_MAGIC + b"def", d, when=1700000000)
    check(os.path.basename(a) == "sagga-001.sgq" and os.path.basename(b) == "sagga-002.sgq", "a new file each time, numbered, never over another (%s, %s)" % (os.path.basename(a), os.path.basename(b)))
    open(os.path.join(d, "sagga-041.sgq"), "wb").write(b"x")
    check(os.path.basename(B.save_image(B.PROJECT_MAGIC, d)) == "sagga-042.sgq", "the number after the highest one")
    check(open(a, "rb").read() == B.PROJECT_MAGIC + b"abc" and not [f for f in os.listdir(d) if f.endswith(".part")], "written whole, nothing half-written left")
    check(B.check_image(B.PROJECT_MAGIC + bytes(100)) is None and B.check_image(b"SGQ5" + bytes(100))
          and B.check_image(b"RIFF" + bytes(100)) and B.check_image(B.PROJECT_MAGIC + bytes(40000)), "check_image: SGQA only, not a project, too big")


def t_bootwriter():
    """RaspiMIDIHub's boot partition is read-only: it is opened for a write, closed again, under the hub's lock"""
    import tempfile
    d = tempfile.mkdtemp()
    folder = os.path.join(d, "boot", "sagga")
    os.makedirs(os.path.join(d, "boot"))
    cmds = []
    w = B.BootWriter(folder, run=lambda c: cmds.append(c), mounts=lambda: [("/", ["ro"]), (os.path.join(d, "boot"), ["ro", "noatime"])],
                     lock=os.path.join(d, "run", "boot-rw.lock"))
    path = w.write(os.path.join(folder, "a.sgq"), B.PROJECT_MAGIC + b"x")
    mp = os.path.join(d, "boot")
    check(cmds == [["mount", "-o", "remount,rw", mp], ["sync"], ["mount", "-o", "remount,ro", mp]], "read-only: remount rw, write, sync, remount ro (%s)" % cmds)
    check(open(path, "rb").read() == B.PROJECT_MAGIC + b"x", "the file is there")
    cmds.clear()
    w = B.BootWriter(folder, run=lambda c: cmds.append(c), mounts=lambda: [("/", ["rw"])])
    w.write(os.path.join(folder, "b.sgq"), b"SGQ5y")
    check(cmds == [] and os.path.exists(os.path.join(folder, "b.sgq")), "a writable folder: no remount")
    w = B.BootWriter(folder, run=lambda c: cmds.append(c), mounts=lambda: [("/", ["ro"])])
    try:
        w.write(os.path.join(folder, "c.sgq"), b"x"); ok = False
    except OSError:
        ok = True
    check(ok and cmds == [], "the read-only root: refused, nothing remounted")

    def fail(c):
        cmds.append(c)
        if "remount,rw" in c[2]:
            raise B.subprocess.CalledProcessError(32, c)
    cmds.clear()
    w = B.BootWriter(folder, run=fail, mounts=lambda: [("/", ["ro"]), (mp, ["ro"])], lock=None)
    try:
        w.write(os.path.join(folder, "d.sgq"), b"x"); ok = False
    except B.subprocess.CalledProcessError:
        ok = True
    check(ok and not os.path.exists(os.path.join(folder, "d.sgq")) and cmds == [["mount", "-o", "remount,rw", mp]],
          "the remount fails (not root): nothing written, it stays read-only (%s)" % cmds)
    check(B.default_dump_dir() in ("/boot/firmware/sagga", "/boot/sagga", os.path.expanduser("~/sagga-projects")), "the default folder")


def t_library():
    """the files, the list for the FM-1, a file to the FM-1, an export over a file or as a new one"""
    import tempfile
    d = tempfile.mkdtemp()
    for n, data in (("10-house.sgq", B.PROJECT_MAGIC + bytes(300)), ("2-techno.sgq", b"SGQ4" + bytes(600)), ("notes.txt", b"x"),
                    ("a very long name for a project.sgq", b"SGQ5" + bytes(20)), ("bad.sgq", b"MThd" + bytes(9))):
        open(os.path.join(d, n), "wb").write(data)
    check(B.library_files(d) == ["2-techno.sgq", "10-house.sgq", "a very long name for a project.sgq", "bad.sgq"], "the files in the order of their names (%s)" % B.library_files(d))
    sent, logs = [], []
    w = B.BootWriter(d, run=lambda c: None, mounts=lambda: [("/", ["rw"])])
    lib = B.Library(d, sent.append, writer=w, log=logs.append)
    lib.fm1_sysex(B.SX_HEAD + [B.SX_LIB_LIST, 0, 0, 0xF7])
    lib.fm1_sysex(B.SX_HEAD + [B.SX_LIB_LIST, 2, 0, 0xF7])
    check(sent[0] == B.SX_HEAD + [B.SX_LIB_ENTRY, 0, 4] + list(b"2-techno") + [0xF7], "entry 0 of 4: 2-techno (%s)" % sent[:1])
    check(sent[1][5:7] == [2, 4] and bytes(sent[1][7:-1]) == b"a very long name", "a name: 16 characters (%r)" % bytes(sent[1][7:-1]))
    sent.clear()
    fm = FakeFM1()
    lib.fm1_sysex(B.SX_HEAD + [B.SX_LIB_LOAD, 1, 0, 0xF7], 0.0)
    for i in range(40):
        msgs, sent[:] = list(sent), []
        for m in msgs:
            fm.rx(m)
        replies, fm.replies = fm.replies, []
        for r in replies:
            lib.fm1_sysex(r, 0.01 * i)
        if fm.project:
            break
    check(fm.project == B.PROJECT_MAGIC + bytes(300) and lib.sender is None, "LOAD 1: 10-house goes to the FM-1 as an import")
    sent.clear()
    lib.fm1_sysex(B.SX_HEAD + [B.SX_LIB_LOAD, 3, 0, 0xF7])
    lib.fm1_sysex(B.SX_HEAD + [B.SX_LIB_LOAD, 9, 0, 0xF7])
    check(sent == [B.SX_HEAD + [B.SX_LIB_ANSWER, 3, 3, 0, 0xF7], B.SX_HEAD + [B.SX_LIB_ANSWER, 2, 9, 0, 0xF7]], "not a project: 3; no such file: 2 (%s)" % sent)
    sent.clear()
    lib.fm1_sysex(B.SX_HEAD + [B.SX_LIB_SAVE, 0, 0, 0xF7])                      # over 2-techno
    for m in B.dump_frames(B.PROJECT_MAGIC + b"new"):
        lib.fm1_sysex(m)
    check(open(os.path.join(d, "2-techno.sgq"), "rb").read() == B.PROJECT_MAGIC + b"new" and sent == [B.SX_HEAD + [B.SX_LIB_ANSWER, 0, 0, 0, 0xF7]], "SAVE OVER file 1: written, answered 0")
    sent.clear()
    for m in B.dump_frames(B.PROJECT_MAGIC + b"plain"):                                          # an export with no 23 before: a new file
        lib.fm1_sysex(m)
    check(open(os.path.join(d, "sagga-001.sgq"), "rb").read() == B.PROJECT_MAGIC + b"plain" and sent[-1][5] == 0, "a plain EXPORT: a new file")
    lib.fm1_sysex(B.SX_HEAD + [B.SX_LIB_SAVE] + B.put7(B.LIB_NEW, 2) + [0xF7])
    for m in B.dump_frames(B.PROJECT_MAGIC + b"new2"):
        lib.fm1_sysex(m)
    check(open(os.path.join(d, "sagga-002.sgq"), "rb").read() == B.PROJECT_MAGIC + b"new2", "SAVE NEW: the next number")
    sent.clear()

    def bad(c):
        raise OSError("read-only")
    lib.writer = B.BootWriter(d, run=bad, mounts=lambda: [("/", ["rw"]), (d, ["ro"])], lock=None)
    for m in B.dump_frames(B.PROJECT_MAGIC + b"x"):
        lib.fm1_sysex(m)
    check(sent and sent[-1][5] == 1 and any("could not" in x for x in logs), "the write fails: answered 1, said so")
    e = tempfile.mkdtemp()
    sent.clear()
    B.Library(e, sent.append, log=logs.append).fm1_sysex(B.SX_HEAD + [B.SX_LIB_LIST, 0, 0, 0xF7])
    check(sent == [B.SX_HEAD + [B.SX_LIB_ENTRY, 0, 0, 0xF7]], "no files: 21 00 00")


def t_dump_cli():
    """--export and --import with a fake mido whose FM-1 port is the Python model"""
    import contextlib
    import io
    import tempfile
    import types
    fm_name = "Felucca 2:Felucca 2 MIDI 1 36:0"
    image = B.PROJECT_MAGIC + bytes(range(256)) * 4 + b"end"

    def run(args, model):
        cb = []

        class Msg:
            def __init__(self, b): self.b = list(b)
            def bytes(self): return self.b
            @classmethod
            def from_bytes(cls, b): return cls(b)

        class In:
            def __init__(self, name, callback): cb.append(callback)
            def close(self): pass

        class Out:
            def __init__(self, name): pass
            def send(self, m):
                for r in model(m.bytes()):
                    cb[0](Msg(r))
            def close(self): pass

        fake = types.SimpleNamespace(get_input_names=lambda: [fm_name], get_output_names=lambda: [fm_name],
                                     open_input=lambda name, callback=None: In(name, callback), open_output=Out, Message=Msg)
        sys.modules["mido"] = fake
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = B.main(list(args))
        finally:
            del sys.modules["mido"]
        return rc, out.getvalue(), err.getvalue()

    d = tempfile.mkdtemp()
    asked = []

    def exporter(m):
        asked.append(m)
        return B.dump_frames(image) if B.sx_cmd(m) == B.SX_EXPORT else []
    rc, out, err = run(["--export", "--dump-dir", d], exporter)
    files = os.listdir(d)
    check(rc == 0 and len(files) == 1 and open(os.path.join(d, files[0]), "rb").read() == image, "--export saves the project in --dump-dir (%s %r)" % (rc, err))
    check(asked == [B.export_request()], "and asked for the current project")
    rc, out, err = run(["--export", "3", "--out", os.path.join(d, "x.sgq")], exporter)
    check(rc == 0 and asked[-1] == B.export_request(2) and open(os.path.join(d, "x.sgq"), "rb").read() == image, "--export 3 asks for slot 3, --out names the file")
    rc, out, err = run(["--export", "9"], exporter) if False else (None, None, None)
    path = os.path.join(d, "in.sgq")
    open(path, "wb").write(image)
    fm = FakeFM1()

    def importer(m):
        fm.rx(m)
        r, fm.replies = fm.replies, []
        return r
    rc, out, err = run(["--import", path], importer)
    check(rc == 0 and fm.project == image and "imported" in out, "--import sends a file and the FM-1 takes it (%s %r)" % (rc, err))
    fm = FakeFM1(playing=True)
    rc, out, err = run(["--import", path], importer)
    check(rc == 1 and "busy" in err, "--import to a playing FM-1: refused, said so (%r)" % err)
    open(path, "wb").write(b"MThd" + bytes(50))
    rc, out, err = run(["--import", path], importer)
    check(rc == 2 and "not a SAGGA" in err, "--import of something else: refused before sending")


def t_dump_firmware():
    """export from the real firmware (host simulator), import the file into another run of it: the same project"""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import sagga_sim_tests as S
    S.build()
    try:
        s = S.Script()
        s.steps(100, [0, 6, 11])                                         # steps 1, 7, 12
        s.enc(400, S.K2, -20)                                            # (velocity of the cursor step: 80)
        s.at(600, "sx", "7D 53 47 01")
        log = S.run(s, 1500)
        r = B.DumpReceiver()
        got = [g for g in (r.feed(m) for _, m in log.sysex) if g]
        check(got and got[0][0] == "image" and got[0][1][:4] == B.PROJECT_MAGIC, "the firmware's export is taken by the bridge (%s)" % (got[:1] and got[0][0],))
        image = got[0][1] if got and got[0][0] == "image" else b""
        # import into a fresh FM-1, then play it
        s = S.Script()
        t = 100
        for f in B.dump_frames(image):
            s.at(t, "sx", " ".join("%02X" % b for b in f[1:-1]))
            t += 15
        s.tap_btn(t + 100, S.PLAY)
        log = S.run(s, t + 100 + int(16 * S.STEP_MS))
        st = [m for _, m in log.sysex if B.sx_cmd(m) == B.SX_STATUS]
        check(st and all(m[5] == 0 for m in st) and B.get7(st[-1][6:8]) == B.SX_LAST, "every chunk answered OK, and the end (%d answers)" % len(st))
        n = log.notes(ch=0, after=t + 100)
        gaps = [round((b[0] - a[0]) / S.STEP_MS) for a, b in zip(n, n[1:])]
        check(gaps == [6, 5] and n[2][2] == 80, "the imported project plays steps 1, 7, 12, the last at velocity 80 (%s %s)" % (gaps, n[-1:]))
        # while playing: export and import are refused, the show goes on
        s = S.Script()
        s.steps(100, [0, 4, 8, 12])
        s.tap_btn(400, S.PLAY)
        s.at(600, "sx", "7D 53 47 01")
        s.at(700, "sx", " ".join("%02X" % b for b in B.dump_frames(image)[0][1:-1]))
        log = S.run(s, 2500)
        st = [m for _, m in log.sysex]
        check(len(st) == 2 and all(B.sx_cmd(m) == B.SX_STATUS and m[5] == 1 for m in st), "while playing: export and import answer 'busy' (%s)" % st)
        n = log.notes(ch=0, after=400)
        gaps = [round((b[0] - a[0]) / S.STEP_MS) for a, b in zip(n, n[1:])]
        check(len(n) >= 4 and set(gaps) == {4}, "and the sequencer plays on, in time (%s)" % gaps)
        # nobody listens: the export gives up
        s = S.Script()
        s.at(100, "sxdead", 1); s.at(200, "sx", "7D 53 47 01"); s.at(400, "sxdead", 0); s.tap_btn(500, S.PLAY)
        log = S.run(s, 900)
        check(not log.sysex and len(log.clock()) > 5, "an export nobody reads gives up, and the FM-1 goes on")
        # a slot: save slot 1, then export slot 1 (01 00)
        import tempfile
        fd, flash = tempfile.mkstemp(); os.close(fd); os.remove(flash)
        s = S.Script()
        s.steps(100, [0, 4])
        s.tap_btn(300, S.SAVE); s.tap_btn(500, S.SAVE)
        s.at(1500, "sx", "7D 53 47 01 00")
        s.at(1600, "sx", "7D 53 47 01 05")                                # slot 6: empty
        log = S.run(s, 2000, flash)
        r = B.DumpReceiver()
        got = [g for g in (r.feed(m) for _, m in log.sysex) if g]
        check(len(got) == 2 and got[0][0] == "image" and got[1][0] == "error" and "empty" in got[1][1], "export of slot 1, and of an empty slot (%s)" % [g[0] for g in got])
        os.remove(flash)
    finally:
        os.remove(S.BIN)


def converse(S, base, end, bridge_of, rounds=32):
    """the host simulator and a bridge model, talking: the firmware runs the script; each SysEx it sends is given to a
    (0.11: a round a frame, and a project is 18 chunks now: 32 rounds)
    fresh model in order, whose answers are put into the script 5 ms later; again, until nothing new is answered"""
    sched = []
    for _ in range(rounds):
        s = S.Script()
        s.lines = list(base.lines)
        for t, m in sched:
            s.at(t, "sx", " ".join("%02X" % b for b in m[1:-1]))
        log = S.run(s, end)
        out = []
        send_t = [0]
        model = bridge_of(lambda m: out.append((send_t[0], list(m))))
        for t, m in log.sysex:
            send_t[0] = t + 5
            model(m, t / 1000.0)
        new, last = [], {}
        for t, m in out:                              # (frames one after another: 15 ms apart)
            t = max(t, last.get("t", 0) + 15)
            last["t"] = t
            new.append((t, m))
        if new == sched:
            return log
        sched = new
    return log


def t_library_firmware():
    """the real firmware's LIB view and the bridge's Library: the list, a file loaded and played, SAVE OVER"""
    import tempfile
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import sagga_sim_tests as S
    S.build()
    try:
        # a project to put on the Pi: steps 1, 5, 9, 13 at velocity 70 (exported by the firmware)
        s = S.Script()
        s.steps(100, [0, 4, 8, 12])
        s.enc(400, S.K2, -30)                            # (the cursor is on step 13: it plays at 70)
        s.at(600, "sx", "7D 53 47 01")
        log = S.run(s, 1500)
        r = B.DumpReceiver()
        image = [g for g in (r.feed(m) for _, m in log.sysex) if g][0][1]
        d = tempfile.mkdtemp()
        open(os.path.join(d, "01-empty.sgq"), "wb").write(image[:4] + image[4:])   # (the same project twice, a name each)
        open(os.path.join(d, "02-four.sgq"), "wb").write(image)
        w = B.BootWriter(d, run=lambda c: None, mounts=lambda: [("/", ["rw"])])

        def bridge_of(send):
            lib = B.Library(d, send, writer=w, log=lambda x: None)
            return lambda m, now: (lib.fm1_sysex(m, now), lib.tick(now))
        base = S.Script()
        base.raw(100, "attach")
        for k in range(1000, 9000, 900):
            base.raw(k, "hb")
        t = S.view(base, 200, S.GC_REC, alt=True)
        t = S.view(base, t, S.GC_REC, alt=True)          # LIB
        base.pad(1200, 1, 0); base.pad(1400, 1, 0)       # file 2: choose, load
        base.tap_btn(4000, S.PLAY)
        base.tap_btn(4000 + int(16 * S.STEP_MS), S.PLAY)
        log = converse(S, base, 7000, bridge_of)
        n = log.notes(ch=0, after=4000, before=4000 + int(16 * S.STEP_MS))
        check([v for _, _, v in n] == [100, 100, 100, 70], "LIB: file 2 is loaded from the Pi and plays, its last step at 70 (%s)" % n)
        pads, _ = log.leds()
        check(pads.get(0) is not None and pads.get(1) in (S.GL_CURSOR, S.GL_ON) and pads.get(2) == S.GL_OFF, "two files on the pads (%s)" % [pads.get(i) for i in range(3)])
        # SAVE OVER file 1 (pad 9 of row 8, twice) after a change: file 1 gets the new project
        base2 = S.Script()
        base2.lines = list(base.lines)
        base2.lines = [l for l in base2.lines if "4000" not in l[2] and str(4000 + int(16 * S.STEP_MS)) not in l[2]]
        base2.pad(2500, 0, 0); base2.pad(2700, 0, 0)     # (choose file 1: the second tap would load it ...)
        base2.pad(2600, 8, 7)                            # ... so SAVE OVER after the first: asks
        base2.pad(2650, 8, 7)                            # again: saves over 01-empty
        log = converse(S, base2, 6000, bridge_of)
        check(open(os.path.join(d, "01-empty.sgq"), "rb").read()[:4] == B.PROJECT_MAGIC and
              any(B.sx_cmd(m) == B.SX_LIB_SAVE for _, m in log.sysex), "SAVE OVER: the FM-1 says where, then exports; the file is written")
    finally:
        os.remove(S.BIN)


def t_fm1_port():
    """0.8: USB PORTS 2: the bridge takes the FM-1's port 2 (the second ALSA port of its client)"""
    one = ["Felucca:Felucca MIDI 1 24:0"]
    two = ["Felucca:Felucca MIDI 1 24:0", "Felucca:Felucca MIDI 2 24:1"]
    check(B.fm1_port(one) == one[0] and B.fm1_port(two) == two[1] and B.fm1_port(list(reversed(two))) == two[1],
          "auto: port 2 when there are two, else the only one")
    check(B.fm1_port(two, "1") == two[0] and B.fm1_port(one, "2") == one[0], "--port 1 / --port 2")


class FakeSynths:
    """synth ports for the PatchKeeper: what is sent to each, a patch each one answers a request with"""
    def __init__(self, present, answers):
        self.present, self.answers, self.sent, self.opened, self.keeper = present, answers, {}, [], None

    def open(self, pattern, name):
        hit = [n for n in self.present if re.search(pattern, n, re.I)]
        if not hit:
            return None
        self.opened.append(name)

        def send(m, nm=name):
            self.sent.setdefault(nm, []).append(list(m))
            if m[0] == 0xF0 and nm in self.answers and self.keeper and self.keeper.job:
                for a in self.answers[nm]:
                    self.keeper.synth_in(nm, a)
        return send, (lambda: None)


def t_patch_keeper():
    """0.8 snapshot patches: KEEP asks the synths, keeps their answers per project and snapshot; PLAY sends them back"""
    import json
    import tempfile
    d = tempfile.mkdtemp()
    cfg = os.path.join(d, "patches.json")
    json.dump({"synths": [{"name": "Micro Freak", "port": "MicroFreak", "request": "F0 00 20 6B 07 01 00 F7"},
                          {"name": "TD3", "port": "TD-3"},
                          {"name": "Absent", "port": "Nothing here", "request": "F0 7E 7F 06 01 F7"}]}, open(cfg, "w"))
    synths, playing = B.load_patch_config(cfg)
    check([x["name"] for x in synths] == ["Micro_Freak", "TD3", "Absent"] and synths[0]["request"][:2] == [0xF0, 0x00]
          and synths[1]["request"] is None and synths[1]["wait"] == 10.0 and playing, "patches.json read (%s)" % synths)
    bad = os.path.join(d, "bad.json")
    json.dump({"synths": [{"name": "X", "port": "X", "request": "90 3C 40"}]}, open(bad, "w"))
    try:
        B.load_patch_config(bad)
        check(False, "a request that is not SysEx is refused")
    except ValueError:
        check(True, "")
    check(B.load_patch_config(os.path.join(d, "none.json")) == ([], True), "no patches.json: no synths")
    patch = [[0xF0, 0x00, 0x20, 0x6B, 0x07, 0x01, 0x11, 0x22, 0xF7], [0xF0, 0x00, 0x20, 0x6B, 0x07, 0x02, 0x33, 0xF7]]
    fs = FakeSynths(["MicroFreak:MicroFreak MIDI 1 28:0", "TD-3:TD-3 MIDI 1 32:0"], {"Micro_Freak": patch})
    to_fm1 = []
    w = lambda folder: B.BootWriter(folder, run=lambda c: None, mounts=lambda: [("/", ["rw"])])
    k = B.PatchKeeper(d, synths, to_fm1.append, fs.open, writer=w, log=lambda x: None)
    fs.keeper = k
    pid = 0x12345678
    keep = B.SX_HEAD + [0x41, 2] + B.put7(pid, 5) + [1, 0xF7]
    check(k.fm1_sysex(keep, 10.0), "KEEP is the keeper's")
    check(fs.sent.get("Micro_Freak") == [synths[0]["request"]] and "TD3" not in fs.sent, "the request goes to the synth that has one")
    k.synth_in("TD3", [0xF0, 0x41, 0x10, 0xF7])                 # (sent by hand from the TD-3)
    k.synth_in("TD3", [0x90, 60, 100])                          # (not a SysEx: not kept)
    k.tick(12.0)
    check(k.job is not None and not to_fm1, "it listens as long as the slowest synth needs (10 s)")
    k.tick(20.5)
    sd = os.path.join(d, "patches", "12345678", "s3")
    check(to_fm1 == [B.SX_HEAD + [0x42, 0, 2, 0xF7]], "the answer: kept, 2 synths (%s)" % to_fm1)
    check(sorted(os.listdir(sd)) == ["Micro_Freak.syx", "TD3.syx"] and
          open(os.path.join(sd, "Micro_Freak.syx"), "rb").read() == bytes(patch[0] + patch[1]), "kept in patches/<id>/s3")
    fs.sent.clear(); del to_fm1[:]
    play = B.SX_HEAD + [0x40, 2] + B.put7(pid, 5) + [0, 0xF7]
    k.fm1_sysex(play, 30.0)
    check(fs.sent.get("Micro_Freak") == patch and fs.sent.get("TD3") == [[0xF0, 0x41, 0x10, 0xF7]], "PLAY: the patches go back (%s)" % fs.sent)
    check(to_fm1 == [B.SX_HEAD + [0x42, 2, 2, 0xF7]], "the answer: sent to 2")
    del to_fm1[:]
    k.fm1_sysex(B.SX_HEAD + [0x40, 5] + B.put7(pid, 5) + [0, 0xF7], 31.0)
    check(not to_fm1, "a snapshot with no patches: no answer")
    k.send_while_playing = False
    fs.sent.clear()
    k.fm1_sysex(B.SX_HEAD + [0x40, 2] + B.put7(pid, 5) + [1, 0xF7], 32.0)
    check(not fs.sent, "send_while_playing false: nothing while the FM-1 plays")
    k2 = B.PatchKeeper(d, [], to_fm1.append, fs.open, writer=w, log=lambda x: None)
    del to_fm1[:]
    k2.fm1_sysex(keep, 0.0)
    check(to_fm1 == [B.SX_HEAD + [0x42, 1, 0, 0xF7]], "no synths: the FM-1 hears that nothing was kept")


def t_patch_firmware():
    """the real firmware: SAVE + SEL + black 1 stores snapshot 1, SAVE + black 11 asks the Pi to keep the patches; the
    keeper answers, the FM-1 shows it; the snapshot recalled: the patches go out again"""
    import tempfile
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import sagga_sim_tests as S
    S.build()
    try:
        d = tempfile.mkdtemp()
        synths = [dict(name="Synth", port="Synth", request=[0xF0, 0x7E, 0x7F, 0x06, 0x01, 0xF7], wait=0.5)]
        fs = FakeSynths(["Synth:Synth MIDI 1 30:0"], {"Synth": [[0xF0, 0x43, 0x00, 0x01, 0x7F, 0xF7]]})
        w = lambda folder: B.BootWriter(folder, run=lambda c: None, mounts=lambda: [("/", ["rw"])])

        def bridge_of(send):
            k = B.PatchKeeper(d, synths, send, fs.open, writer=w, log=lambda x: None)
            fs.keeper = k

            def feed(m, now):
                k.fm1_sysex(m, now)
                k.tick(now + 1.0)                       # (the synth answered at once)
            return feed
        base = S.Script()
        base.press(100, S.SAVE); base.press(120, S.SEL); base.tap_key(140, S.bk(0)); base.release(200, S.SEL); base.release(220, S.SAVE)
        base.press(400, S.SAVE); base.tap_key(420, S.bk(10)); base.release(500, S.SAVE)
        base.at(900, "dump", 0)
        base.press(1500, S.SAVE); base.tap_key(1520, S.bk(0)); base.release(1600, S.SAVE)     # recall snapshot 1
        base.at(1900, "dump", 0)
        log = S.converse(S, base, 2200, bridge_of) if hasattr(S, "converse") else converse(S, base, 2200, bridge_of)
        msgs = [x["msg"] for x in log.states]
        check(msgs[:1] == ["PI KEPT THE PATCHES OF 1 SYNTH"], "the FM-1 shows the Pi's answer (%s)" % msgs)
        check(msgs[1:] == ["PI SENT THE PATCHES TO 1 SYNTH"], "recalled: the Pi sent the patch back (%s)" % msgs)
        check([0xF0, 0x43, 0x00, 0x01, 0x7F, 0xF7] in fs.sent.get("Synth", []), "the synth got its patch again")
    finally:
        os.remove(S.BIN)


def t_regista():
    """0.9 the regista's frames: STATO decoded, FRASE / REGIA LED built and checked, the answers logged and handed on"""
    sent, logged, got = [], [], []
    r = B.Regista(sent.append, log=logged.append, verbose=True)
    r.on_stato = lambda st: got.append(("stato", st["bar"]))
    r.on_risposta = lambda t, c: got.append(("risp", t, c))
    r.on_toccata = lambda t: got.append(("tocc", t))
    r.on_key = lambda k: got.append(("key", k))
    r.start()
    check(sent == [B.SX_HEAD + [0x54] + [0] * 16 + [0xF7]], "start: REGIA LED all off, so that the FM-1 starts talking")
    stato = B.SX_HEAD + [0x50] + B.put7(300, 2) + [2, 127, 9, 1, 64 + 4, 2, 1, 5, 16, 72, 3, 2, 1, 0xF7]
    check(r.fm1_sysex(stato) and r.stato == dict(bar=300, scene=2, snap=None, root=9, scale=1, deg=4, col=2, harm=1, phrase_bar=5,
                                                 phrase_bars=16, energy=72, set_genre=3, queue=2, playing=1), "STATO decoded (%s)" % r.stato)
    check(got == [("stato", 300)] and logged and logged[0].startswith("STATO: bar 300 scene 3 snap - key 9/1 deg +4"), "... logged and handed on (%s)" % logged)
    check(not r.fm1_sysex(B.SX_HEAD + [0x50, 1, 0xF7]) is False and r.stato["bar"] == 300, "a short STATO is swallowed, the last one stays")
    check(not r.fm1_sysex(B.SX_HEAD + [0x40, 1, 0xF7]) and not r.fm1_sysex([0x90, 60, 100]), "a snapshot frame or a note is not the regista's")
    del sent[:]
    r.frase(3, 2, [(0, 60, 100, 50), (8, 63, 90, 0), (31, 67, 80, 100)])
    check(sent == [B.SX_HEAD + [0x51, 3, 2, 3, 0, 60, 100, 50, 8, 63, 90, 0, 31, 67, 80, 100, 0xF7]] and r.pending == {3: [(0, 60, 100, 50), (8, 63, 90, 0), (31, 67, 80, 100)]},
          "FRASE: T BARS N then STEP NOTE VEL LEN per step (%s)" % sent)
    for bad in [(16, 1, []), (0, 0, []), (0, 5, []), (0, 1, [(16, 60, 100, 50)]), (0, 1, [(0, 128, 100, 50)]), (0, 1, [(0, 60, 100, 101)]),
                (0, 4, [(i, 60, 100, 50) for i in range(65)])]:
        try:
            r.frase(*bad)
            check(False, "a phrase that does not fit is refused (%r)" % (bad,))
        except ValueError:
            pass
    check(B.frase_frame(0, 4, [(63, 0, 0, 0)]) is not None, "step 63 of a 4-bar phrase, note 0, vel 0 (the FM-1 makes it 100), len 0 (long)")
    check(r.fm1_sysex(B.SX_HEAD + [0x52, 3, 0, 0xF7]) and got[-1] == ("risp", 3, 0) and r.pending == {} and logged[-1] == "regista: track 4: written",
          "RISPOSTA 0: written, the pending phrase is done")
    r.fm1_sysex(B.SX_HEAD + [0x52, 3, 2, 0xF7])
    check(logged[-1] == "regista: track 4: the track is locked", "RISPOSTA 2: locked")
    check(r.fm1_sysex(B.SX_HEAD + [0x53, 7, 0xF7]) and got[-1] == ("tocc", 7) and logged[-1] == "regista: track 8 touched by hand", "TOCCATA")
    check(r.fm1_sysex(B.SX_HEAD + [0x55, 11, 0xF7]) and got[-1] == ("key", 11) and logged[-1] == "regista: rule 12 tapped", "REGIA TASTO")
    del sent[:]
    r.led([1, 2, 3, -1] + [1] * 20)
    check(sent == [B.SX_HEAD + [0x54, 1, 2, 2, 0] + [1] * 12 + [0xF7]] and r.leds[:4] == [1, 2, 2, 0], "REGIA LED: 16 values clipped to 0-2")
    r.led([2])
    check(sent[-1] == B.SX_HEAD + [0x54, 2] + [0] * 15 + [0xF7], "a short list: the rest off")
    check(B.check_image(b"SGQB" + bytes(100)) is None and B.check_image(b"SGQA" + bytes(100)) is None and B.check_image(b"SGQ9" + bytes(100))
          and "SGQA" in B.check_image(b"SGQ8" + bytes(100)), "the bridge takes SGQB and SGQA images, not SGQ8 / SGQ9 (0.10 started over)")


def t_regista_firmware():
    """the real firmware: silent until the Pi speaks; a FRASE while stopped is written at once (RISPOSTA 0), one while
    it plays waits for the bar line; STATO comes at every bar; a hand on a track sends TOCCATA; a rule tapped on the
    grid's REGIA view sends REGIA TASTO; a FRASE on the track LOOP records on is refused (2)"""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import sagga_sim_tests as S
    S.build()
    try:
        base = S.Script()
        base.at(100, "sx", "7D 53 47 51 00 01 03 00 3C 64 32 04 40 50 00 0F 43 46 64")     # FRASE: track 1, 1 bar, 3 steps (C4, E4 long, G4)
        base.at(300, "dump", 0)
        base.tap_btn(500, S.PLAY)
        base.at(600, "sx", "7D 53 47 51 01 01 01 02 2A 60 32")                                # FRASE track 2 while playing: at the bar line
        base.at(700, "dump", 1)
        base.at(2500, "dump", 1)                                                             # (a bar at 128 BPM = 1875 ms)
        base.tap_key(2600, S.wk(5))                                                          # a hand on track 1, step 6: TOCCATA
        base.at(2700, "sx", "7D 53 47 51 00 09 00")                                          # FRASE with 9 bars: broken (3)
        base.tap_btn(4200, S.PLAY)
        log = S.run(base, 4700)
        sx = [(t, m[4], m[5:-1]) for t, m in log.sysex]
        risp = [(t, b) for t, c, b in sx if c == 0x52]
        stato = [(t, b) for t, c, b in sx if c == 0x50]
        check(risp[:1] == [(100, [0, 0])], "FRASE while stopped: written at once (%s)" % risp[:3])
        check(log.dumps[0]["on"] == "x...x..........x" and log.dumps[0]["length"] == 16, "track 1 holds the phrase (%s)" % log.dumps[0])
        check(log.dumps[1]["on"] == "." * 16 or not log.dumps[1]["on"].startswith("..x"), "track 2 waits for the bar (%s)" % log.dumps[1]["on"])
        check(log.dumps[2]["on"].startswith("..x.") and len(risp) >= 2 and risp[1][1] == [1, 0] and 2300 <= risp[1][0] <= 2500,
              "... and gets it at the bar line, with RISPOSTA 0 (%s, %s)" % (log.dumps[2]["on"], risp))
        check(stato[:2] == [(100, [0, 0, 0, 127, 0, 0, 64, 0, 0, 0, 16, 50, 0, 0, 0]), (500, [0, 0, 0, 127, 0, 0, 64, 0, 0, 0, 16, 50, 0, 0, 1])],
              "STATO when the Pi first speaks and at PLAY: bar 0, scene 1, no snapshot, phrase 0/16, energy 50, TECHNO (0.10: the project's genre) (%s)" % stato[:2])
        bars = [(t, B.get7(b[0:2]), b[8]) for t, b in stato if t > 600]
        check(bars == [(2375, 1, 0)], "... then at every bar line: bar 1 (the phrase bar stays 0: the journey is off) (%s)" % bars)
        tocc = [(t, b) for t, c, b in sx if c == 0x53]
        check(tocc and tocc[0][1] == [0] and 2600 <= tocc[0][0] <= 2700, "TOCCATA: track 1 touched by hand (%s)" % tocc)
        check([b for t, b in risp if t >= 2700][:1] == [[0, 3]], "a FRASE of 9 bars: broken (3) (%s)" % risp)
        notes = log.notes(ch=0, after=500)
        check([n for _, n, _ in notes][:3] == [60, 64, 67], "the phrase plays: C4 E4 G4 (%s)" % [n for _, n, _ in notes][:6])
        # REGIA LED and REGIA TASTO on the grid
        g = S.Script()
        g.at(50, "attach")
        g.at(100, "sx", "7D 53 47 54 01 02 00 00 00 00 00 00 01 00 00 00 00 00 00 00")
        g.at(200, "ctl", S.GC_VPERF, 127); g.at(240, "ctl", S.GC_VPERF, 0)      # PERF
        g.at(300, "ctl", S.GC_VPERF, 127); g.at(340, "ctl", S.GC_VPERF, 0)      # SONG
        g.at(400, "ctl", S.GC_VPERF, 127); g.at(440, "ctl", S.GC_VPERF, 0)      # VIAGGIO
        g.at(500, "ctl", S.GC_VPERF, 127); g.at(540, "ctl", S.GC_VPERF, 0)      # REGIA (the regista has spoken)
        g.pad(700, 3, 0)                                                          # rule 4 tapped
        log = S.run(g, 1200)
        check(log.sysex and any(m[4] == 0x50 for _, m in log.sysex), "a REGIA LED wakes the regista: a STATO goes out (%s)" % [m[4] for _, m in log.sysex][:4])
        pads, _ = log.leds(until=690)
        check(pads.get(0) == S.GL_ON and pads.get(1) == S.GL_PLAY and pads.get(2) == S.GL_DIM and pads.get(8) == S.GL_ON,
              "the REGIA view shows the LEDs the Pi sent: on, passing, off (%s)" % [pads.get(i) for i in range(16)])
        keys = [m[5] for _, m in log.sysex if m[4] == 0x55]
        check(keys == [3], "rule 4 tapped on the grid: REGIA TASTO 3 (%s)" % keys)
        pads, _ = log.leds()
        check(pads.get(3) == S.GL_ON, "... and its LED lights at once, until the Pi says otherwise")
        g2 = S.Script()
        g2.at(50, "attach")
        g2.at(200, "ctl", S.GC_VPERF, 127); g2.at(240, "ctl", S.GC_VPERF, 0)
        g2.at(300, "ctl", S.GC_VPERF, 127); g2.at(340, "ctl", S.GC_VPERF, 0)
        g2.at(400, "ctl", S.GC_VPERF, 127); g2.at(440, "ctl", S.GC_VPERF, 0)
        g2.pad(700, 3, 0)
        log = S.run(g2, 1200)
        check(not log.sysex, "no regista on the Pi: no REGIA view in the cycle, and the FM-1 sends nothing (%s)" % [m[4] for _, m in log.sysex][:4])
    finally:
        os.remove(S.BIN)


def t_patterns():
    """0.11: the Pi's patterns over SysEx: how many, one of them, one to keep"""
    import tempfile
    d = tempfile.mkdtemp()
    stock = os.path.join(d, "stock")
    os.makedirs(stock)
    open(os.path.join(stock, "TECHNO.txt"), "w").write("KICK\tX...X...X..xX...\t-\nKICK\tX.x.X...\t-\nBASS\tx-..x.x.\t0...7.c.\n")
    out = []
    lib = B.PatternLib(os.path.join(d, "mine"), out.append, log=lambda x: None, stock=stock)
    H = B.SX_HEAD
    check(lib.fm1_sysex(H + [0x60, 0, 0, 0xF7]) and out[-1] == H + [0x61, 0, 0, 2, 0, 0xF7], "how many TECHNO KICKs: 2 (%s)" % out[-1:])
    check(lib.fm1_sysex(H + [0x60, 0, 9, 0xF7]) and out[-1] == H + [0x61, 0, 9, 0, 0, 0xF7], "no CLAP: 0")
    lib.fm1_sysex(H + [0x62, 0, 0, 1, 0, 0xF7])
    check(out[-1] == H + [0x63, 0, 0, 1, 0, 8, 0] + [ord(c) for c in "X.x.X..."] + [0xF7], "KICK 1: its text, no notes (%s)" % out[-1])
    lib.fm1_sysex(H + [0x62, 0, 4, 0, 0, 0xF7])
    check(out[-1] == H + [0x63, 0, 4, 0, 0, 8, 1] + [ord(c) for c in "x-..x.x."] + [ord(c) for c in "0...7.c."] + [0xF7], "BASS 0: text and notes")
    lib.fm1_sysex(H + [0x62, 0, 0, 7, 0, 0xF7])
    check(out[-1] == H + [0x63, 0, 0, 7, 0, 0, 0, 0xF7], "no such one: LEN 0")
    lib.fm1_sysex(H + [0x64, 0, 0, 16, 0] + [ord(c) for c in "X...X...X...X.x."] + [0xF7])
    check(out[-1] == H + [0x65, 0, 0, 0, 2, 0, 0xF7] and os.path.isfile(os.path.join(d, "mine", "TECHNO.txt")), "a kick kept as the Pi's 3rd (%s)" % out[-1])
    lib.fm1_sysex(H + [0x64, 0, 4, 4, 1] + [ord(c) for c in "x..."] + [ord(c) for c in "z..."] + [0xF7])
    check(out[-1][:8] == H + [0x65, 0, 4, 2], "a bass with a note that is not one: not kept (CODE 2)")
    check(not lib.fm1_sysex(H + [0x21, 0, 0, 0xF7]) and not lib.fm1_sysex(H + [0x40, 1, 0xF7]), "other frames are not the patterns'")
    check(lib.fm1_sysex(H + [0x60, 99, 0, 0xF7]) and out[-1][4] == 0x65, "a genre that does not exist: nothing answered")
    P = B._patterns_module()
    check(P.GENRES[0] == "TECHNO" and P.GENRES[23] == "BAILEFUNK" and P.GENRES[24] == "MERENGUE" and len(P.GENRES) == 25 and P.PARTS.index("VOX") == 25 and P.PARTS.index("CLAP") == 9, "the names in the FM-1's order")
    gen = os.path.join(ROOT, "tools", "hub", "patterns")
    check(sorted(os.listdir(gen)) == sorted("%s.txt" % g for g in P.GENRES) and P.Patterns(d, stock=gen).summary()["TECHNO"].get("KICK") == 12,
          "the stock library: a file a genre, 12 more kicks for TECHNO (%s)" % P.Patterns(d, stock=gen).summary()["TECHNO"].get("KICK"))


def t_progressions():
    """0.11: the Pi's chord progressions over SysEx: how many of a genre and mood, the I-th by likeness, one to keep"""
    import tempfile
    import re as _re
    d = tempfile.mkdtemp()
    stock = os.path.join(d, "stock")
    os.makedirs(stock)
    open(os.path.join(stock, "TECHNO.txt"), "w").write(
        "# a comment\nDARK\ti bII\nEPIC\ti bVI bVII i\tthe big one\nDARK\ti\nEPIC\tbVI bVII i i\nSAD\ti iv bVI v\nNOPE\ti\nDARK\tnot a chord\n")
    out = []
    lib = B.ProgLib(os.path.join(d, "mine"), out.append, log=lambda x: None, stock=stock)
    P = lib.P
    H = B.SX_HEAD
    EPIC, DARK, ANY = P.MOODS.index("EPIC"), P.MOODS.index("DARK"), 0
    check(lib.fm1_sysex(H + [0x66, 0, EPIC, 0xF7]) and out[-1] == H + [0x67, 0, EPIC, 2, 0, 0xF7], "how many TECHNO EPIC: 2 (%s)" % out[-1:])
    check(lib.fm1_sysex(H + [0x66, 0, ANY, 0xF7]) and out[-1] == H + [0x67, 0, ANY, 5, 0, 0xF7], "all of TECHNO: 5 (the lines that are none left out)")
    sh = lambda k: P.SHAPE_CH + k
    MIN, MAJ = 5, 4
    # ref: bVI bVII i (the order of likeness: 'bVI bVII i i' before 'i bVI bVII i')
    ref = [8, sh(MAJ), 10, sh(MAJ), 0, sh(MIN)]
    lib.fm1_sysex(H + [0x68, 0, EPIC, 0, 0, 3] + ref + [0xF7])
    check(out[-1] == H + [0x69, 0, EPIC, 0, 0, 4, EPIC] + [8, sh(MAJ), 0, 0, 10, sh(MAJ), 0, 0, 0, sh(MIN), 0, 0, 0, sh(MIN), 0, 0] + [0xF7],
          "the EPIC most like bVI bVII i first (%s)" % out[-1])
    lib.fm1_sysex(H + [0x68, 0, EPIC, 0, 0, 0, 0xF7])
    check(out[-1][9:11] == [4, EPIC] and out[-1][11:13] == [0, sh(MIN)], "no chords to be like: the file's order (%s)" % out[-1])
    lib.fm1_sysex(H + [0x68, 0, EPIC, 5, 0, 0, 0xF7])
    check(out[-1] == H + [0x69, 0, EPIC, 5, 0, 0, 0, 0xF7], "no such one: N 0")
    # keep one: ii7:8 V7:8 Imaj7 pushed, SATISFYING
    SAT = P.MOODS.index("SATISFYING")
    rows = [2, sh(13), 8, 0, 7, sh(12), 8, 0, 0, sh(14), 16, 1]
    lib.fm1_sysex(H + [0x6A, 0, SAT, 3] + rows + [0xF7])
    check(out[-1] == H + [0x6B, 0, SAT, 0, 0, 0, 0xF7] and os.path.isfile(os.path.join(d, "mine", "TECHNO.txt")), "kept as the first SATISFYING (%s)" % out[-1])
    text = open(os.path.join(d, "mine", "TECHNO.txt")).read()
    check("SATISFYING\tii7:8 V7:8 Imaj7:16^1" in text and "EPIC\ti bVI bVII i\tthe big one" in text, "written as words, the stock's lines kept (%s)" % text.splitlines()[-1])
    lib.fm1_sysex(H + [0x6A, 0, SAT, 1, 40, sh(MAJ), 0, 0, 0xF7])
    check(out[-1][:8] == H + [0x6B, 0, SAT, 2], "a root that is none: not kept (CODE 2)")
    check(not lib.fm1_sysex(H + [0x60, 0, 0, 0xF7]) and not lib.fm1_sysex(H + [0x21, 0, 0xF7]), "the patterns' frames are not the progressions'")
    # the words: every shape there and back; the FM-1's names
    for k in P.SHAPES:
        for semi in range(12):
            r = (semi, P.SHAPE_CH + k, 0, 0)
            if P.chord(P.chord_name(*r)) != r:
                check(False, "shape %d semi %d: %s" % (k, semi, P.chord_name(*r)))
    check(P.parse("bVImaj7:8^1 i9 Vsus4 #ivo viim7b5") == [(8, sh(14), 8, 1), (0, sh(22), 0, 0), (7, sh(9), 0, 0), (6, sh(6), 0, 0), (11, sh(17), 0, 0)], "the words")
    src = open(os.path.join(ROOT, "firmware", "src", "sagga_seq_core.c")).read()
    names = _re.search(r'sq_mood_name\(uint8_t m\)\s*\{\s*static const char \*const N\[SQ_MOODS\] = \{([^}]*)\}', src)
    check(names and [x.strip().strip('"') for x in names.group(1).replace("\n", " ").split(",") if x.strip()] == P.MOODS, "the moods in the FM-1's order")
    hdr = open(os.path.join(ROOT, "firmware", "src", "sagga_seq_core.h")).read()
    ch = _re.search(r"enum \{ SQ_CH_OFF = 0,([^}]*)SQ_CH_COUNT \}", hdr).group(1)
    check(len([x for x in ch.split(",") if x.strip()]) == len(P.SHAPES) and _re.search(r"#define SQ_HSHAPE_CH (\d+)u", hdr).group(1) == str(P.SHAPE_CH),
          "the shapes: as many as the FM-1's, from SQ_HSHAPE_CH + 1")
    pip = open(os.path.join(ROOT, "firmware", "src", "sagga_pipat.c")).read()
    check("SX_PROG_ASK = 0x66, SX_PROG_COUNT = 0x67, SX_PROG_GET = 0x68, SX_PROG = 0x69, SX_PROG_PUT = 0x6A, SX_PROG_SAVED = 0x6B" in pip
          and (B.SX_PROG_ASK, B.SX_PROG_SAVED) == (0x66, 0x6B), "the commands as the FM-1 has them")
    gen = os.path.join(ROOT, "tools", "hub", "progressions")
    summ = P.Progressions(d, stock=gen).summary()
    check(sorted(os.listdir(gen)) == sorted("%s.txt" % g for g in P.GENRES) and sum(summ["TECHNO"].values()) >= 30 and summ["TRANCE"].get("EPIC", 0) >= 6,
          "the stock: a file a genre, 30 or more for TECHNO, EPIC ones for TRANCE (%s)" % summ["TRANCE"])


TESTS = [t_roles_match_firmware, t_start_stop, t_pads_in, t_buttons_in, t_leds_out, t_batching, t_pump, t_blink,
         t_swap_and_guard, t_mk2, t_mini, t_heal, t_ports, t_portwatch, t_main, t_quiet_wait, t_synth_ports, t_end_to_end,
         t_dump_codec, t_dump_receiver, t_dump_sender, t_dump_files, t_dump_cli, t_dump_firmware, t_bootwriter, t_library,
         t_library_firmware, t_fm1_port, t_patch_keeper, t_patch_firmware, t_regista, t_regista_firmware, t_patterns, t_progressions]

if __name__ == "__main__":
    for t in TESTS:
        print(t.__name__)
        try:
            t()
        except Exception as e:
            import traceback
            traceback.print_exc()
            FAILS.append("%s raised %r" % (t.__name__, e))
    print("sagga bridge: %d checks, %d failures" % (N[0], len(FAILS)))
    sys.exit(1 if FAILS else 0)
