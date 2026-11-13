#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA GRID bridge: two Launchpad Minis <-> the FM-1 running SAGGA SEQ.

The FM-1 has a single USB MIDI cable, so the two Launchpads cannot plug into it. They plug into the Raspberry Pi
(next to RaspiMIDIHub); this script turns them into one 16 x 8 pad grid (left Launchpad = columns 1-8, right =
9-16) and talks the SAGGA GRID protocol with the FM-1 (docs/SAGGA-GRID.md):

    to the FM-1    channel 16 Note On/Off   note = y * 16 + x   pad down / up            (y = 0 is the top row)
                   channel 15 CC id 0..31   127 / 0             the 16 top + 16 side buttons
                   channel 16 CC 118        127 attach, 64 keep-alive, 0 detach
    from the FM-1  channel 16 Note On       note = y * 16 + x   velocity = LED role 0..15
                   channel 15 CC id 0..31   value = LED role

The FM-1 only says which role a pad has; the colours are in ROLE_RGB below: change them here, no reflash.

This is the idea of the midigrid mod for norns (github.com/jaggednz/midigrid, GPL-3.0): a virtual grid made of
two 8 x 8 quads, the first Launchpad the left one, the second the right one. What it learned about the
Launchpad Mini MK3 is used here: programmer mode, the flash and pulse layers cleared at start, only SysEx sent
to the Launchpad, the MIDI port of the second USB interface, up to 80 LEDs in one message.

    python3 sagga_grid_bridge.py --list
    python3 sagga_grid_bridge.py --identify                  # left half green, right half red: check which is which
    python3 sagga_grid_bridge.py [--swap] [--frame]          # run ('--fm1 REGEX' if the FM-1's port is named otherwise)

--frame: the left Launchpad turned a quarter anticlockwise (its round buttons down the left side and along the top,
its USB cable out at the top left), as midigrid does with a rotated quad: the round buttons frame the grid, 16 on top
and 8 on each side, and no cable sits between the two Launchpads.

Projects (SysEx, docs/SAGGA-SEQ.md): while the bridge runs, a project the FM-1 exports (EXPORT pad in the PROJ view)
is saved as a .sgq file in --dump-dir (default /boot/firmware/sagga: RaspiMIDIHub keeps the root file system
read-only, the boot partition is where it keeps what must survive; it is also the partition a Windows PC sees when
the SD card is put in it). RaspiMIDIHub mounts that partition read-only too: the bridge opens it for writing only while
it writes a file, as RaspiMIDIHub itself does (0.5; 0.4 could not save there). The files of that folder are the
LIBRARY the FM-1 shows on the grid's LIB view (0.5): load one, the next one (a setlist, in the order of the names),
save a project as a new file or over one. With the FM-1 stopped, from the Pi (or any computer with the FM-1 on USB):

    python3 sagga_grid_bridge.py --export [SLOT]             # the current project (or saved slot 1-8) to a file
    python3 sagga_grid_bridge.py --import FILE.sgq           # a file back into the FM-1 (it replaces the project)

needs mido and python-rtmidi (apt install python3-mido python3-rtmidi, or pip install mido python-rtmidi).
Launchpad Mini MK3 is what this was written for. --model mini drives the red / green Launchpad Mini (MK1, MK2)
and the first Launchpad. --model mk2 follows midigrid's driver for the Launchpad MK2
(note LEDs, palette colours) and is untested.
"""
import argparse
import json
import contextlib
import os
import queue
import re
import subprocess
import sys
import time
import zlib

# ----------------------------------------------------------------------------------------------- roles
# the order is the GL_* enum in firmware/src/sagga_grid.c (tests/sagga_bridge_tests.py checks it)
ROLE_NAMES = ["OFF", "FAINT", "DIM", "ON", "ACCENT", "PLAY", "CURSOR", "BLUE",
              "MUTED", "PEND", "FILL", "WHITE", "CYAN", "VIOLET", "ORANGE", "YELLOW",
              "TAIL", "TIE"]                  # 0.12: a step a long note covers (a dark green), a step tied to the next
ROLE_PEND = ROLE_NAMES.index("PEND")          # blinks

# Launchpad RGB, 0..127 per channel
ROLE_RGB = {
    "OFF": (0, 0, 0),
    "FAINT": (5, 5, 8),
    "DIM": (14, 14, 18),
    "ON": (0, 70, 28),
    "ACCENT": (10, 127, 50),
    "PLAY": (127, 6, 6),
    "CURSOR": (127, 80, 0),
    "BLUE": (8, 30, 110),
    "MUTED": (40, 0, 0),
    "PEND": (127, 90, 0),
    "FILL": (100, 0, 90),
    "WHITE": (100, 100, 110),
    "CYAN": (0, 90, 100),
    "VIOLET": (60, 16, 110),
    "ORANGE": (80, 26, 0),
    "YELLOW": (100, 100, 0),
    "TAIL": (0, 28, 12),
    "TIE": (40, 110, 60),
}
RGB = [ROLE_RGB[n] for n in ROLE_NAMES]

CH_PAD = 0x0F                     # MIDI channel 16 (pads, attach)
CH_CTL = 0x0E                     # MIDI channel 15 (buttons)
CC_ATTACH = 118
HEARTBEAT_S = 1.0
BLINK_S = 0.25
HEAL_S = 2.0                      # every LED is sent again now and then (a lost message cannot stay wrong for long)
FLUSH_MAX = 80                    # LEDs per SysEx message (the Launchpad takes 81; midigrid sends 80 as well)


# ----------------------------------------------------------------------------------------------- drivers
class Launchpad:
    """What the models share: an 8 x 8 pad field (notes 11..88, bottom left = 11), 8 buttons above, 8 on the right."""

    @staticmethod
    def pad_led(col, y): return 11 + 10 * (7 - y) + col         # y = 0 is the top row
    @staticmethod
    def side_led(j): return 89 - 10 * j                         # j = 0 is the top one

    def all_leds(self):
        return ([self.pad_led(c, y) for y in range(8) for c in range(8)]
                + [self.top_led(j) for j in range(8)] + [self.side_led(j) for j in range(8)])


class MK3(Launchpad):
    """Launchpad Mini [MK3], programmer mode: pads are notes 11..88, top row CC 91..98, side CC 89,79..19.
    SysEx header with device id 0Dh, RGB LED = command 03h, spec type 3 (led, r, g, b, each 0..127)."""
    name = "mk3"
    HEADER = [0xF0, 0x00, 0x20, 0x29, 0x02, 0x0D]

    @staticmethod
    def top_led(j): return 91 + j

    def init(self):
        """programmer mode, then (as midigrid does) the flash and pulse layers cleared: an LED that was left
        flashing or pulsing by something else would otherwise keep doing so under our static colours"""
        leds = self.all_leds()
        flash = [b for led in leds for b in (0x01, led, 0, 0)]
        pulse = [b for led in leds for b in (0x02, led, 0)]
        return [self.HEADER + [0x0E, 0x01, 0xF7],
                self.HEADER + [0x03] + flash + [0xF7],
                self.HEADER + [0x03] + pulse + [0xF7]]

    def exit(self): return [self.HEADER + [0x0E, 0x00, 0xF7]]       # back to live mode

    def decode(self, msg):
        """-> ('pad', col, y, velocity) | ('top', j, value) | ('side', j, value) | None"""
        if len(msg) != 3:
            return None
        st, d1, d2 = msg[0] & 0xF0, msg[1], msg[2]
        if st in (0x90, 0x80):
            r, c = divmod(d1, 10)
            if 1 <= r <= 8 and 1 <= c <= 8:
                return ("pad", c - 1, 8 - r, d2 if st == 0x90 else 0)
        elif st == 0xB0:
            if 91 <= d1 <= 98:
                return ("top", d1 - 91, d2)
            r, c = divmod(d1, 10)
            if c == 9 and 1 <= r <= 8:
                return ("side", 8 - r, d2)
        return None

    def leds(self, items):
        """items: [(led index, (r, g, b) 0..127)] -> SysEx messages"""
        out = []
        for i in range(0, len(items), FLUSH_MAX):
            body = []
            for led, (r, g, b) in items[i:i + FLUSH_MAX]:
                body += [0x03, led, r, g, b]
            out.append(self.HEADER + [0x03] + body + [0xF7])
        return out


# Launchpad MK2 / Pro / MK3 palette entries (index: approximate RGB, 0..127), from Novation's colour chart as
# I remember it: only used by the MK2 driver, which picks the nearest one
MK2_PALETTE = {
    0: (0, 0, 0), 1: (14, 14, 14), 2: (62, 62, 62), 3: (127, 127, 127),
    5: (127, 0, 0), 6: (44, 0, 0), 9: (127, 42, 0), 10: (44, 14, 0), 13: (127, 127, 0), 14: (44, 44, 0),
    21: (0, 127, 0), 22: (0, 44, 0), 37: (0, 84, 127), 38: (0, 32, 41), 45: (0, 0, 127), 46: (0, 0, 44),
    49: (42, 0, 127), 53: (127, 0, 127), 54: (44, 0, 44), 57: (127, 0, 42),
}


class MK2(Launchpad):
    """Launchpad [MK2] in its Session layout, driven the way midigrid drives 'launchpad mk2': no set-up message,
    pads are notes 11..88, an LED takes a Note On whose velocity is a palette index. The top row (CC 104..111,
    LED by Control Change) and the side buttons (notes 89,79..19) are my reading of the manual, not midigrid's.
    UNTESTED, and not for the first-generation Mini (that one has its own 0..127 red / green codes)."""
    name = "mk2"

    @staticmethod
    def top_led(j): return 104 + j

    def init(self): return []
    def exit(self): return []

    def decode(self, msg):
        if len(msg) != 3:
            return None
        st, d1, d2 = msg[0] & 0xF0, msg[1], msg[2]
        if st in (0x90, 0x80):
            r, c = divmod(d1, 10)
            v = d2 if st == 0x90 else 0
            if 1 <= r <= 8 and 1 <= c <= 8:
                return ("pad", c - 1, 8 - r, v)
            if c == 9 and 1 <= r <= 8:
                return ("side", 8 - r, v)
        elif st == 0xB0 and 104 <= d1 <= 111:
            return ("top", d1 - 104, d2)
        return None

    @staticmethod
    def nearest(rgb):
        """the palette index whose colour is closest; never black for a colour that is not black"""
        best, best_d = 0, None
        for idx, (r, g, b) in MK2_PALETTE.items():
            if idx == 0 and tuple(rgb) != (0, 0, 0):
                continue
            d = (r - rgb[0]) ** 2 + (g - rgb[1]) ** 2 + (b - rgb[2]) ** 2
            if best_d is None or d < best_d:
                best, best_d = idx, d
        return best

    def leds(self, items):
        return [[0xB0, led, self.nearest(rgb)] if led >= 104 else [0x90, led, self.nearest(rgb)] for led, rgb in items]


# first-generation Launchpad / Launchpad Mini (MK1 and the "MK2" Mini): red + green LEDs, 2 bits each
MINI_RG = {"OFF": (0, 0), "FAINT": (0, 1), "DIM": (1, 1), "ON": (0, 3), "ACCENT": (2, 3), "PLAY": (3, 0),
           "CURSOR": (3, 2), "BLUE": (0, 2), "MUTED": (1, 0), "PEND": (3, 3), "FILL": (3, 1), "WHITE": (3, 3),
           "CYAN": (1, 3), "VIOLET": (2, 1), "ORANGE": (2, 2), "YELLOW": (3, 3), "TAIL": (0, 1), "TIE": (1, 3)}


class Mini(Launchpad):
    """Launchpad Mini (MK1 / MK2, red-green) and the first Launchpad, in their X-Y layout (Programmer's Reference):
    pad = Note y*16+x, the right column Note y*16+8, the top row CC 104..111; an LED takes velocity
    16*green + red + 12 (both 0..3). Reset: CC 0 value 0."""
    name = "mini"

    @staticmethod
    def pad_led(col, y): return y * 16 + col
    @staticmethod
    def side_led(j): return j * 16 + 8
    @staticmethod
    def top_led(j): return 200 + j                 # (an id of ours; on the wire CC 104 + j)

    def init(self): return [[0xB0, 0, 0], [0xB0, 0, 1]]
    def exit(self): return [[0xB0, 0, 0]]

    def decode(self, msg):
        if len(msg) != 3:
            return None
        st, d1, d2 = msg[0] & 0xF0, msg[1], msg[2]
        if st in (0x90, 0x80) and d1 < 128:
            y, x = d1 >> 4, d1 & 15
            v = d2 if st == 0x90 else 0
            if y < 8 and x < 8:
                return ("pad", x, y, v)
            if y < 8 and x == 8:
                return ("side", y, v)
        elif st == 0xB0 and 104 <= d1 <= 111:
            return ("top", d1 - 104, d2)
        return None

    @staticmethod
    def velocity(rgb):
        r, g = MINI_RG.get(RGB_NAME.get(tuple(rgb), "OFF"), (0, 0))
        return 16 * g + r + 12

    def leds(self, items):
        return [[0xB0, 104 + led - 200, self.velocity(rgb)] if led >= 200 else [0x90, led, self.velocity(rgb)]
                for led, rgb in items]


RGB_NAME = {tuple(v): k for k, v in ROLE_RGB.items()}
DRIVERS = {"mk3": MK3, "mk2": MK2, "mini": Mini}
DEFAULT_PATTERN = {"mk3": "Launchpad Mini", "mk2": "Launchpad", "mini": "Launchpad"}
FM1_PATTERN = "FM-1|Felucca"      # the USB name of the FM-1; the Felucca-based firmware (and so SAGGA SEQ) calls itself "Felucca 2"


# ----------------------------------------------------------------------------------------------- the bridge
class Bridge:
    """The translation, with no I/O: it is given send functions and is fed messages (lists of ints) and time.
    send_lp(idx, msg): idx 0 = left Launchpad, 1 = right.  send_fm1(msg)."""

    def __init__(self, send_lp, send_fm1, model="mk3", swap=False, heal_s=HEAL_S, turned=(False, False)):
        self.lp = DRIVERS[model]()
        self.send_lp, self.send_fm1 = send_lp, send_fm1
        self.swap = swap
        self.turned = tuple(bool(t) for t in turned)    # (left, right): turned a quarter anticlockwise (--frame)
        self.heal_s = heal_s
        self.role = {}                 # (idx, led index) -> role wanted
        self.shown = {}                # (idx, led index) -> rgb on the Launchpad
        self.dirty = set()
        self.phase = True              # blink
        self.next_beat = 0.0
        self.next_blink = 0.0
        self.next_heal = 0.0
        self.last_in = {}              # for the double-port guard

    # -- ends
    def _side(self, idx): return idx ^ 1 if self.swap else idx

    # -- where things are. A Launchpad, as it is built: pads (c, r), c and r 0..7 from the top left; the round
    # buttons above at (j, -1), those on the right at (8, j). Turned a quarter anticlockwise (--frame) a point
    # (c, r) is at (r, 7 - c): the top row of round buttons runs down the left side (its first one at the bottom),
    # the right column runs along the top (its first one on the left), and the USB socket, on the right edge near
    # the top, ends up on the top edge at the left, out of the way of the other Launchpad.
    def _to_grid(self, half, c, r):
        return (r, 7 - c) if self.turned[half] else (c, r)

    def _from_grid(self, half, x, y):
        return (7 - y, x) if self.turned[half] else (x, y)

    def _led(self, c, r):
        """the LED of a point of the Launchpad as it is built"""
        if r < 0:
            return self.lp.top_led(c)
        if c > 7:
            return self.lp.side_led(r)
        return self.lp.pad_led(c, r)

    def _button(self, half, ident):
        """button 0..31 of the grid -> (c, r) on that half's Launchpad: 0-15 the row on top (8 each), 16-23 / 24-31 the
        column of each half (on the right of an upright Launchpad, on the left of a turned one), each from the top"""
        if ident < 16:
            x, y = ident & 7, -1
        else:
            x, y = (-1 if self.turned[half] else 8), ident & 7
        return self._from_grid(half, x, y)

    def _blank(self, idx):
        leds = self.lp.all_leds()
        for m in self.lp.leds([(led, (0, 0, 0)) for led in leds]):
            self.send_lp(idx, m)
        for led in leds:
            self.shown[(idx, led)] = (0, 0, 0)

    def start(self, now=0.0):
        for idx in (0, 1):
            for m in self.lp.init():
                self.send_lp(idx, m)
            self._blank(idx)
        self.send_fm1([0xB0 | CH_PAD, CC_ATTACH, 127])
        self.next_beat = now + HEARTBEAT_S
        self.next_blink = now + BLINK_S
        self.next_heal = now + self.heal_s

    def stop(self):
        self.send_fm1([0xB0 | CH_PAD, CC_ATTACH, 0])
        for idx in (0, 1):
            self._blank(idx)
            for m in self.lp.exit():
                self.send_lp(idx, m)

    # -- Launchpad -> FM-1
    def lp_in(self, idx, msg, port=None, now=0.0):
        """a message from Launchpad idx (0 left, 1 right); returns what it was, or None"""
        ev = self.lp.decode(list(msg))
        if ev is None:
            return None
        key = (idx, tuple(msg))
        last = self.last_in.get(key)
        if last and port is not None and last[0] != port and now - last[1] < 0.004:
            return None                 # the same press from a second MIDI port of the same Launchpad
        self.last_in[key] = (port, now)
        side = self._side(idx)
        if ev[0] == "pad":
            _, col, y, vel = ev
            x, y = self._to_grid(side, col, y)
            self.send_fm1([0x90 | CH_PAD, y * 16 + x + 8 * side, vel & 0x7F])
        else:
            kind, j, val = ev
            x, y = self._to_grid(side, *((j, -1) if kind == "top" else (8, j)))
            ident = (x if y < 0 else 16 + y) + 8 * side
            self.send_fm1([0xB0 | CH_CTL, ident, 127 if val >= 64 else 0])
        return ev

    # -- FM-1 -> Launchpads
    def fm1_in(self, msg):
        msg = list(msg)
        if len(msg) != 3:
            return
        st, d1, d2 = msg[0] & 0xF0, msg[1], msg[2]
        ch = msg[0] & 0x0F
        if ch == CH_PAD and st in (0x90, 0x80) and d1 < 128:
            x, y = d1 & 15, d1 >> 4
            if y < 8:
                half = x >> 3
                self._set(half, self._led(*self._from_grid(half, x & 7, y)), d2 if st == 0x90 else 0)
        elif ch == CH_CTL and st == 0xB0 and d1 < 32:      # 0-7 / 8-15 top row, 16-23 / 24-31 side column: left / right
            half = (d1 >> 3) & 1
            self._set(half, self._led(*self._button(half, d1)), d2)

    def _set(self, fm_half, led, role):
        idx = self._side(fm_half)
        role = role if role < len(RGB) else 0
        if self.role.get((idx, led)) != role:
            self.role[(idx, led)] = role
            self.dirty.add((idx, led))

    def tick(self, now):
        """flush LED changes, blink, heal, keep-alive; call every few ms"""
        if now >= self.next_beat:
            self.next_beat = now + HEARTBEAT_S
            self.send_fm1([0xB0 | CH_PAD, CC_ATTACH, 64])
        if now >= self.next_blink:
            self.next_blink = now + BLINK_S
            self.phase = not self.phase
            for k, role in self.role.items():
                if role == ROLE_PEND:
                    self.dirty.add(k)
        if self.heal_s and now >= self.next_heal:
            self.next_heal = now + self.heal_s
            self.shown.clear()                       # forget what the Launchpads show: every LED is sent again
            self.dirty.update(self.role)
        if not self.dirty:
            return
        todo = {0: [], 1: []}
        for idx, led in sorted(self.dirty):
            role = self.role[(idx, led)]
            rgb = (RGB[role] if role < len(RGB) else RGB[2]) if (role != ROLE_PEND or self.phase) else (0, 0, 0)   # (a role this bridge does not know: DIM)
            if self.shown.get((idx, led)) != rgb:
                self.shown[(idx, led)] = rgb
                todo[idx].append((led, rgb))
        self.dirty.clear()
        for idx in (0, 1):
            for m in self.lp.leds(todo[idx]):
                self.send_lp(idx, m)

    def identify(self):
        """left half ON (green), right half PLAY (red; the first Launchpad Mini has no blue): which is the left one?
        The top left pad of each half is amber, and so are the first round button of each half's top row and the top
        one of each side column: if one of them is somewhere else, the layout (--frame, --swap) is not the one on the
        table"""
        for y in range(8):
            for x in range(16):
                self.fm1_in([0x90 | CH_PAD, y * 16 + x, 6 if y == 0 and x in (0, 8) else 3 if x < 8 else 5])
        for ident in (0, 8, 16, 24):
            self.fm1_in([0xB0 | CH_CTL, ident, 6])


# ----------------------------------------------------------------------------------------------- projects (SysEx)
# F0 7D 53 47 CMD ... F7, every byte 7-bit (firmware/src/sagga_store.c has the same description)
SX_HEAD = [0xF0, 0x7D, 0x53, 0x47]
SX_EXPORT, SX_DATA, SX_END, SX_STATUS = 0x01, 0x02, 0x03, 0x10
SX_CHUNK = 256
SX_MAX = 0x8000 - 0x100                     # the biggest image a slot takes
SX_LAST = 0x3FFF                            # the index a status for the END frame carries
SX_TEXT = {0: "ok", 1: "the FM-1 is busy: stop it (and let a save finish) first", 2: "a chunk arrived damaged",
           3: "a chunk came out of order", 4: "the image does not check out", 5: "it is not a SAGGA SEQ project",
           6: "that slot is empty", 7: "nobody listens"}
PROJECT_MAGIC = b"SGQB"                     # SAGGA SEQ 0.11 project image
PROJECT_MAGICS = (PROJECT_MAGIC, b"SGQA")   # ... and 0.10's, which 0.11 reads; nothing older (0.10 started the format over: SGQ3..SGQ9 are refused)
SX_LIB_LIST, SX_LIB_ENTRY, SX_LIB_LOAD, SX_LIB_SAVE, SX_LIB_ANSWER = 0x20, 0x21, 0x22, 0x23, 0x24
LIB_MAX = 64                                # the files the FM-1 shows
LIB_NAME = 16                               # ... and the characters of a name
LIB_NEW = 0x3FFF                            # SX_LIB_SAVE: a new file


def pack7(data):
    """8-to-7, LSB first (as the FM-1's update protocol packs)"""
    out, acc, nb = [], 0, 0
    for b in data:
        acc |= b << nb
        nb += 8
        while nb >= 7:
            out.append(acc & 0x7F)
            acc >>= 7
            nb -= 7
    if nb:
        out.append(acc & 0x7F)
    return out


def unpack7(data):
    out, acc, nb = [], 0, 0
    for b in data:
        acc |= (b & 0x7F) << nb
        nb += 7
        if nb >= 8:
            out.append(acc & 0xFF)
            acc >>= 8
            nb -= 8
    return bytes(out)


def put7(v, n): return [(v >> (7 * i)) & 0x7F for i in range(n)]
def get7(b): return sum((x & 0x7F) << (7 * i) for i, x in enumerate(b))


def sx_cmd(msg):
    """the command of one of our SysEx messages, else None"""
    msg = list(msg)
    return msg[4] if len(msg) >= 6 and msg[:4] == SX_HEAD and msg[-1] == 0xF7 else None


def export_request(slot=None):
    """slot None: the project as it is now; 0-7: a saved slot"""
    return SX_HEAD + [SX_EXPORT] + ([slot] if slot is not None else []) + [0xF7]


def dump_frames(image):
    """the SysEx messages that carry an image: the chunks, then the end"""
    image = bytes(image)
    cnt = (len(image) + SX_CHUNK - 1) // SX_CHUNK
    out = []
    for i in range(cnt):
        data = pack7(image[i * SX_CHUNK:(i + 1) * SX_CHUNK])
        out.append(SX_HEAD + [SX_DATA] + put7(i, 2) + put7(cnt, 2) + data + [sum(data) & 0x7F, 0xF7])
    out.append(SX_HEAD + [SX_END] + put7(len(image), 3) + put7(zlib.crc32(image), 5) + [0xF7])
    return out


def check_image(image):
    """None if this looks like a project the FM-1 takes, else why not"""
    if len(image) < 8 or bytes(image[:4]) not in PROJECT_MAGICS:
        return "not a SAGGA SEQ project (no SGQB or SGQA at the start; 0.11 reads 0.10's projects, nothing older)"
    if len(image) > SX_MAX:
        return "too big (%d bytes, a slot takes %d)" % (len(image), SX_MAX)
    return None


class DumpReceiver:
    """Puts an export together. feed() every SysEx message from the FM-1: None while it is not complete (or not
    ours), ('image', bytes) when it is, ('error', text) when it went wrong or the FM-1 said no."""

    def __init__(self):
        self.chunks, self.count = {}, None

    def feed(self, msg):
        msg = list(msg)
        cmd = sx_cmd(msg)
        if cmd == SX_DATA and len(msg) >= 11:
            body = msg[5:-1]
            idx, cnt, data, s = get7(body[0:2]), get7(body[2:4]), body[4:-1], body[-1]
            if sum(data) & 0x7F != s:
                self.__init__()
                return ("error", "chunk %d arrived damaged" % idx)
            if idx == 0:
                self.chunks, self.count = {}, cnt
            if self.count != cnt:
                self.__init__()
                return ("error", "chunk %d does not belong to this export" % idx)
            self.chunks[idx] = unpack7(data)
        elif cmd == SX_END and len(msg) >= 14:
            body = msg[5:-1]
            length, crc = get7(body[0:3]), get7(body[3:8])
            have = self.count is not None and all(i in self.chunks for i in range(self.count))
            image = b"".join(self.chunks[i] for i in range(self.count))[:length] if have else b""
            self.__init__()
            if not have or len(image) != length:
                return ("error", "chunks are missing")
            if zlib.crc32(image) != crc:
                return ("error", "the export does not check out (CRC)")
            return ("image", image)
        elif cmd == SX_STATUS and len(msg) >= 9 and msg[5] != 0 and msg[5] in (1, 6):
            return ("error", "the FM-1 says: " + SX_TEXT.get(msg[5], "code %d" % msg[5]))
        return None


class DumpSender:
    """An import: chunk by chunk, each answered by the FM-1 (it has room for one SysEx frame), a damaged or
    unanswered one sent again (up to `tries` times), then the end. feed() the FM-1's messages, tick() the time;
    state is 'sending', then 'done' or 'failed' (error says why)."""

    def __init__(self, image, send, timeout=1.5, tries=3):
        self.frames, self.send = dump_frames(image), send
        self.timeout, self.tries = timeout, tries
        self.i, self.again, self.deadline = 0, 0, 0.0
        self.state, self.error = "idle", None

    def start(self, now):
        self.state = "sending"
        self._send(now)

    def _send(self, now):
        self.send(self.frames[self.i])
        self.deadline = now + self.timeout

    def _retry(self, now, why):
        if self.again < self.tries:
            self.again += 1
            self._send(now)
        else:
            self.state, self.error = "failed", why

    def feed(self, msg, now):
        msg = list(msg)
        if self.state != "sending" or sx_cmd(msg) != SX_STATUS or len(msg) < 9:
            return
        code, idx = msg[5], get7(msg[6:8])
        last = self.i == len(self.frames) - 1
        if idx != (SX_LAST if last else self.i):
            return                                   # (an answer to an earlier try)
        if code == 0:
            if last:
                self.state = "done"
            else:
                self.i, self.again = self.i + 1, 0
                self._send(now)
        elif code == 2:
            self._retry(now, SX_TEXT[2])
        else:
            self.state, self.error = "failed", "the FM-1 says: " + SX_TEXT.get(code, "code %d" % code)

    def tick(self, now):
        if self.state == "sending" and now >= self.deadline:
            self._retry(now, "the FM-1 does not answer (is it SAGGA SEQ 0.3 or later, and on?)")

    def progress(self): return "%d/%d" % (min(self.i + 1, len(self.frames)), len(self.frames))


def default_dump_dir():
    """where exports go: the boot partition (RaspiMIDIHub's Pi: mounted read-only, BootWriter opens it for a write),
    else ~/sagga-projects"""
    for d in ("/boot/firmware", "/boot"):
        if os.path.ismount(d):
            return os.path.join(d, "sagga")
    return os.path.expanduser("~/sagga-projects")


def read_mounts(path="/proc/mounts"):
    """[(mount point, options)] of the mounted file systems, or [] where there is no such file"""
    try:
        with open(path) as f:
            out = []
            for line in f:
                parts = line.split()
                if len(parts) >= 4:
                    out.append((parts[1].replace("\\040", " "), parts[3].split(",")))
            return out
    except OSError:
        return []


class BootWriter:
    """Writes files in a folder that may be on a partition mounted read-only (RaspiMIDIHub's /boot/firmware). Such a
    partition is remounted read-write for the write only, then read-only again, as RaspiMIDIHub does for its own
    config: under the same lock (/run/raspimidihub/boot-rw.lock), so that its window and ours never overlap. Needs
    root for that (the service runs as root; on the command line: sudo)."""

    LOCK = "/run/raspimidihub/boot-rw.lock"

    def __init__(self, folder, run=None, mounts=None, lock=LOCK):
        self.folder = folder
        self.run = run or (lambda cmd: subprocess.run(cmd, check=True, capture_output=True, timeout=10))
        self.mounts = mounts or read_mounts
        self.lock = lock

    def _mount_of(self, path):
        """(mount point, read-only?) of the file system path is on"""
        path = os.path.abspath(path)
        best, ro = "/", False
        for mp, opts in self.mounts():
            if (path == mp or path.startswith(mp.rstrip("/") + "/")) and len(mp) >= len(best):
                best, ro = mp, "ro" in opts
        return best, ro

    @contextlib.contextmanager
    def _locked(self):
        fd = None
        if self.lock and os.path.isdir(os.path.dirname(self.lock)):
            try:
                import fcntl
                fd = os.open(self.lock, os.O_CREAT | os.O_WRONLY, 0o600)
                fcntl.flock(fd, fcntl.LOCK_EX)
            except (OSError, ImportError):
                fd = None
        try:
            yield
        finally:
            if fd is not None:
                os.close(fd)                     # (releases the lock)

    @contextlib.contextmanager
    def writable(self):
        """the folder exists and can be written while inside"""
        mp, ro = self._mount_of(self.folder)
        if not ro:
            os.makedirs(self.folder, exist_ok=True)
            yield
            return
        if mp == "/":
            raise OSError("%s is on the read-only root file system" % self.folder)
        with self._locked():
            self.run(["mount", "-o", "remount,rw", mp])
            try:
                os.makedirs(self.folder, exist_ok=True)
                yield
                try:
                    self.run(["sync"])
                except Exception:
                    pass
            finally:
                try:
                    self.run(["mount", "-o", "remount,ro", mp])
                except Exception:
                    pass

    def write(self, path, data):
        """writes path (in the folder) in one go: a power cut leaves the old file or the new one, never half"""
        with self.writable():
            tmp = path + ".part"
            with open(tmp, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        return path


def new_name(folder):
    """sagga-001.sgq, sagga-002.sgq ...: the first number after the highest one there (never over an older file)"""
    hi = 0
    try:
        for n in os.listdir(folder):
            m = re.match(r"sagga-(\d+)\.sgq$", n, re.I)
            if m:
                hi = max(hi, int(m.group(1)))
    except OSError:
        pass
    return os.path.join(folder, "sagga-%03d.sgq" % (hi + 1))


def save_image(image, folder, when=None, writer=None):
    """writes the image as a new file (sagga-NNN.sgq) in folder; returns the path"""
    writer = writer or BootWriter(folder)
    with writer.writable():
        path = new_name(folder)
    return writer.write(path, image)


def natural_key(name):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def library_files(folder):
    """the .sgq files of the folder, in the order of their names (2-x before 10-x), at most LIB_MAX"""
    try:
        names = [n for n in os.listdir(folder) if n.lower().endswith(".sgq") and os.path.isfile(os.path.join(folder, n))]
    except OSError:
        return []
    return sorted(names, key=natural_key)[:LIB_MAX]


def lib_label(name):
    """what the FM-1 shows of a file name: without .sgq, 7-bit ASCII, at most LIB_NAME characters"""
    base = name[:-4] if name.lower().endswith(".sgq") else name
    return "".join(c if 32 <= ord(c) < 127 else "?" for c in base)[:LIB_NAME]


class Library:
    """The FM-1's side of the files (docs/SAGGA-GRID.md, the LIB view): the list, a file sent to the FM-1 (an import),
    an export written as a new file or over one. fm1_sysex() every SysEx message from the FM-1, tick() the time.
    send_fm1(msg) sends to the FM-1; log(text) says what happened."""

    def __init__(self, folder, send_fm1, writer=None, log=print):
        self.folder, self.send, self.log = folder, send_fm1, log
        self.writer = writer or BootWriter(folder)
        self.receiver = DumpReceiver()
        self.sender = None
        self.target = None                       # where the next export goes: a file name, or None (a new file)
        self.files = []
        self.saved_n, self.saved_path, self.export_error = 0, None, None   # 0.14: what Control (the hub's editor) waits for
        self.sent_n, self.sent_error = 0, None

    def answer(self, code, idx=0):
        self.send(SX_HEAD + [SX_LIB_ANSWER, code] + put7(idx, 2) + [0xF7])

    def entry(self, idx):
        if idx == 0:
            self.files = library_files(self.folder)
        n = len(self.files)
        if not n:
            self.send(SX_HEAD + [SX_LIB_ENTRY, 0, 0, 0xF7])
        elif idx < n:
            self.send(SX_HEAD + [SX_LIB_ENTRY, idx, n] + [ord(c) for c in lib_label(self.files[idx])] + [0xF7])

    def load(self, idx, now):
        files = self.files or library_files(self.folder)
        if idx >= len(files):
            return self.answer(2, idx)
        self.load_path(os.path.join(self.folder, files[idx]), now, idx)

    def load_path(self, path, now, idx=0):
        """a file of the library to the FM-1 (0.14: also asked by the hub's editor, by name)"""
        try:
            with open(path, "rb") as f:
                image = f.read()
        except OSError as e:
            self.log("library: cannot read %s: %s" % (path, e))
            return self.answer(3, idx)
        why = check_image(image)
        if why:
            self.log("library: %s: %s" % (path, why))
            self.sent_n, self.sent_error = self.sent_n + 1, why
            return self.answer(3, idx)
        self.sender = DumpSender(image, self.send)
        self.sender.start(now)
        self.sending = os.path.basename(path)
        self.log("library: %s -> the FM-1" % self.sending)

    def save(self, image):
        try:
            if self.target:
                path = self.writer.write(os.path.join(self.folder, self.target), image)
            else:
                path = save_image(image, self.folder, writer=self.writer)
        except (OSError, subprocess.SubprocessError) as e:
            self.log("could not save the FM-1's project in %s: %s" % (self.folder, e))
            self.target = None
            self.export_error = str(e)
            return self.answer(1)
        self.target = None
        self.saved_n, self.saved_path = self.saved_n + 1, path
        self.log("project from the FM-1 saved: %s" % path)
        self.answer(0)

    def fm1_sysex(self, msg, now=0.0):
        msg = list(msg)
        cmd = sx_cmd(msg)
        if cmd is None:
            return
        body = msg[5:-1]
        if cmd == SX_LIB_LIST:
            self.entry(get7(body[0:2]) if len(body) >= 2 else 0)
        elif cmd == SX_LIB_LOAD and len(body) >= 2:
            self.load(get7(body[0:2]), now)
        elif cmd == SX_LIB_SAVE and len(body) >= 2:
            idx = get7(body[0:2])
            files = self.files or library_files(self.folder)
            self.target = files[idx] if idx != LIB_NEW and idx < len(files) else None
        elif cmd == SX_STATUS and self.sender is not None and self.sender.state == "sending":
            self.sender.feed(msg, now)
            self._sender_done()
        else:
            got = self.receiver.feed(msg)
            if got and got[0] == "image":
                self.save(got[1])
            elif got:
                self.export_error = got[1]
                self.log("export: %s" % got[1])

    def _sender_done(self):
        if self.sender is not None and self.sender.state in ("done", "failed"):
            if self.sender.state == "failed":
                self.log("library: %s did not go to the FM-1: %s" % (self.sending, self.sender.error))
            self.sent_n, self.sent_error = self.sent_n + 1, (self.sender.error if self.sender.state == "failed" else None)
            self.sender = None

    def tick(self, now):
        if self.sender is not None:
            self.sender.tick(now)
            self._sender_done()


CONTROL_DIR = os.environ.get("SAGGA_CONTROL", "/run/sagga")


class Control:
    """0.14: the hub's web editor (tools/hub/sagga_editor.py) asks the running bridge - it holds the FM-1's port - for
    the FM-1's project into a file of the library (export) or a file of the library into the FM-1 (import). It writes
    CONTROL_DIR/bridge-req.json ({"id", "op", "file"}); the bridge answers in bridge-ans-<id>.json ({"id", "ok", "msg"})
    and touches bridge-alive every second (the hub uses the bridge only while that is fresh)."""
    TIMEOUT = 12.0

    def __init__(self, lib, folder=CONTROL_DIR, log=print):
        self.lib, self.folder, self.log = lib, folder, log
        self.job = None                          # (id, op, deadline, the count it waits past)
        self.alive_at = self.poll_at = -1e9
        try:
            os.makedirs(self.folder, exist_ok=True)
        except OSError as e:
            self.log("control: %s: %s (the hub's editor will use --export / --import)" % (self.folder, e))

    def _answer(self, rid, ok, msg):
        try:
            p = os.path.join(self.folder, "bridge-ans-%s.json" % re.sub(r"[^0-9A-Za-z-]", "", str(rid))[:40])
            with open(p + ".part", "w") as f:
                f.write(json.dumps(dict(id=rid, ok=ok, msg=msg)))
            os.replace(p + ".part", p)
        except OSError as e:
            self.log("control: cannot answer: %s" % e)

    def _start(self, req, now):
        rid, op, name = req.get("id", "0"), req.get("op"), os.path.basename(str(req.get("file", "")))
        if not name.lower().endswith(".sgq"):
            return self._answer(rid, False, "not a .sgq file")
        if self.lib.sender is not None:
            return self._answer(rid, False, "a project is already going to the FM-1")
        if op == "export":
            self.lib.target, self.lib.export_error = name, None
            self.job = (rid, op, now + self.TIMEOUT, self.lib.saved_n)
            self.lib.send(export_request(None))
            self.log("control: the FM-1's project -> %s" % name)
        elif op == "import":
            path = os.path.join(self.lib.folder, name)
            if not os.path.isfile(path):
                return self._answer(rid, False, "%s is not in the library" % name)
            n0 = self.lib.sent_n
            self.lib.load_path(path, now)
            self.job = (rid, op, now + self.TIMEOUT, n0)
        else:
            self._answer(rid, False, "op %r" % op)

    def tick(self, now):
        if now - self.alive_at >= 1.0:
            self.alive_at = now
            try:
                p = os.path.join(self.folder, "bridge-alive")
                with open(p, "w") as f:
                    f.write("%.0f\n" % time.time())
            except OSError:
                pass
        if self.job:
            rid, op, deadline, n0 = self.job
            if op == "export":
                if self.lib.saved_n > n0:
                    self.job = None
                    return self._answer(rid, True, "saved %s" % os.path.basename(self.lib.saved_path or ""))
                if self.lib.export_error:
                    self.job, self.lib.target = None, None
                    return self._answer(rid, False, self.lib.export_error)
            elif self.lib.sent_n > n0:
                self.job = None
                return self._answer(rid, self.lib.sent_error is None, self.lib.sent_error or "it is the FM-1's project now")
            if now > deadline:
                self.job = None
                if op == "export":
                    self.lib.target = None
                return self._answer(rid, False, "no answer from the FM-1 (is it stopped?)")
            return
        if now - self.poll_at < 0.2:
            return
        self.poll_at = now
        req = os.path.join(self.folder, "bridge-req.json")
        try:
            with open(req) as f:
                data = json.loads(f.read())
            os.unlink(req)
        except (OSError, ValueError):
            return
        if isinstance(data, dict):
            self._start(data, now)


# ----------------------------------------------------------------------------------------------- 0.11 the patterns
SX_PAT_ASK, SX_PAT_COUNT, SX_PAT_GET, SX_PAT, SX_PAT_PUT, SX_PAT_SAVED = 0x60, 0x61, 0x62, 0x63, 0x64, 0x65


def _patterns_module():
    """tools/hub/sagga_patterns.py (installed in /opt/sagga/hub next to the hub)"""
    here = os.path.dirname(os.path.abspath(__file__))
    for d in (os.path.join(here, "hub"), here):
        if os.path.isfile(os.path.join(d, "sagga_patterns.py")) and d not in sys.path:
            sys.path.insert(0, d)
    import sagga_patterns
    return sagga_patterns


class PatternLib:
    """0.11: the FM-1 asks for the Pi's patterns of a genre's part (firmware/src/sagga_pipat.c): how many, one of them,
    and sends one to keep (SEQ + SAVE). The files: <folder>/<GENRE>.txt (sagga_patterns.py). fm1_sysex() returns True
    if the message was one of these."""

    def __init__(self, folder, send_fm1, writer=None, log=print, stock=None):
        P = _patterns_module()
        self.P = P
        self.send, self.log = send_fm1, log
        self.lib = P.Patterns(folder, stock=stock if stock is not None else P.STOCK, writer=writer.write if writer else None)

    def _names(self, body):
        g, f = body[0], body[1]
        if g >= len(self.P.GENRES) or f >= len(self.P.PARTS):
            return None, None
        return self.P.GENRES[g], self.P.PARTS[f]

    def fm1_sysex(self, msg, now=0.0):
        msg = list(msg)
        cmd = sx_cmd(msg)
        if cmd not in (SX_PAT_ASK, SX_PAT_GET, SX_PAT_PUT):
            return False
        body = msg[5:-1]
        if len(body) < 2:
            return True
        genre, part = self._names(body)
        if genre is None:
            return True
        if cmd == SX_PAT_ASK:
            n = len(self.lib.of(genre, part))
            self.send(SX_HEAD + [SX_PAT_COUNT, body[0], body[1]] + put7(min(n, 0x3FFF), 2) + [0xF7])
        elif cmd == SX_PAT_GET and len(body) >= 4:
            k = get7(body[2:4])
            pats = self.lib.of(genre, part)
            if k < len(pats):
                text, notes = pats[k]
                has = 1 if notes else 0
                out = [ord(c) & 0x7F for c in text] + ([ord(c) & 0x7F for c in notes] if has else [])
                self.send(SX_HEAD + [SX_PAT, body[0], body[1]] + put7(k, 2) + [len(text), has] + out + [0xF7])
                self.log("patterns: %s %s #%d -> the FM-1" % (genre, part, k + 1))
            else:
                self.send(SX_HEAD + [SX_PAT, body[0], body[1]] + put7(k, 2) + [0, 0, 0xF7])
        elif cmd == SX_PAT_PUT and len(body) >= 4:
            n, has = body[2], body[3]
            text = "".join(chr(b) for b in body[4:4 + n])
            notes = "".join(chr(b) for b in body[4 + n:4 + 2 * n]) if has else None
            code, k = 2, 0
            if len(text) == n and (not has or (notes and len(notes) == n)):
                try:
                    k = self.lib.add(genre, part, text, notes)
                    code = 0
                    self.log("patterns: %s %s kept as #%d of the Pi's" % (genre, part, k + 1))
                except ValueError as e:
                    self.log("patterns: %s %s not kept: %s" % (genre, part, e))
                except (OSError, subprocess.SubprocessError) as e:
                    code = 1
                    self.log("could not write the pattern: %s" % e)
            self.send(SX_HEAD + [SX_PAT_SAVED, body[0], body[1], code] + put7(k, 2) + [0xF7])
        return True


# ----------------------------------------------------------------------------------------------- 0.11 the progressions
SX_PROG_ASK, SX_PROG_COUNT, SX_PROG_GET, SX_PROG, SX_PROG_PUT, SX_PROG_SAVED = 0x66, 0x67, 0x68, 0x69, 0x6A, 0x6B


def _progs_module():
    """tools/hub/sagga_progs.py (installed in /opt/sagga/hub next to the hub)"""
    _patterns_module()                                             # (the same folder on the path)
    import sagga_progs
    return sagga_progs


class ProgLib:
    """0.11: the FM-1 asks for the Pi's chord progressions of a genre and a mood (firmware/src/sagga_pipat.c): how many,
    the I-th in order of likeness to the chords it sends, and sends one to keep (SEQ + SAVE on SEQ 4 / SEQ 8). The files:
    <folder>/<GENRE>.txt (sagga_progs.py). fm1_sysex() returns True if the message was one of these."""

    def __init__(self, folder, send_fm1, writer=None, log=print, stock=None):
        P = _progs_module()
        self.P = P
        self.send, self.log = send_fm1, log
        self.lib = P.Progressions(folder, stock=stock if stock is not None else P.STOCK, writer=writer.write if writer else None)

    def fm1_sysex(self, msg, now=0.0):
        msg = list(msg)
        cmd = sx_cmd(msg)
        if cmd not in (SX_PROG_ASK, SX_PROG_GET, SX_PROG_PUT):
            return False
        body = msg[5:-1]
        if len(body) < 2 or body[0] >= len(self.P.GENRES) or body[1] >= len(self.P.MOODS):
            return True
        genre, mood = self.P.GENRES[body[0]], self.P.MOODS[body[1]]
        if cmd == SX_PROG_ASK:
            n = len(self.lib.of(genre, mood))
            self.send(SX_HEAD + [SX_PROG_COUNT, body[0], body[1]] + put7(min(n, 0x3FFF), 2) + [0xF7])
        elif cmd == SX_PROG_GET and len(body) >= 5:
            k, rn = get7(body[2:4]), body[4]
            ref = [(body[5 + 2 * i], body[6 + 2 * i]) for i in range(rn) if 6 + 2 * i < len(body)]
            got = self.lib.ordered(genre, mood, ref)
            if k < len(got):
                m, rows, _ = got[k]
                out = [v & 0x7F for r in rows for v in r]
                self.send(SX_HEAD + [SX_PROG, body[0], body[1]] + put7(k, 2) + [len(rows), self.P.MOODS.index(m)] + out + [0xF7])
                self.log("progressions: %s %s #%d -> the FM-1: %s" % (genre, mood, k + 1, self.P.name(rows)))
            else:
                self.send(SX_HEAD + [SX_PROG, body[0], body[1]] + put7(k, 2) + [0, 0, 0xF7])
        elif cmd == SX_PROG_PUT and len(body) >= 3:
            n = body[2]
            rows = [tuple(body[3 + 4 * i:7 + 4 * i]) for i in range(n)]
            code, k = 2, 0
            if all(len(r) == 4 for r in rows):
                try:
                    k = self.lib.add(genre, mood, rows)
                    code = 0
                    self.log("progressions: %s %s kept as #%d: %s" % (genre, mood, k + 1, self.P.name(rows)))
                except ValueError as e:
                    self.log("progressions: %s %s not kept: %s" % (genre, mood, e))
                except (OSError, subprocess.SubprocessError) as e:
                    code = 1
                    self.log("could not write the progression: %s" % e)
            self.send(SX_HEAD + [SX_PROG_SAVED, body[0], body[1], code] + put7(k, 2) + [0xF7])
        return True


# ----------------------------------------------------------------------------------------------- snapshot patches
SX_SNAP_PLAY, SX_SNAP_KEEP, SX_SNAP_ANSWER = 0x40, 0x41, 0x42


def load_patch_config(path):
    """patches.json: {"synths": [{"name": "MicroFreak", "port": "MicroFreak", "request": "F0 .. F7", "wait": 3}, ...],
    "send_while_playing": true}. port: a regex of the synth's MIDI port; request: the SysEx that asks the synth for its
    patch (its manual says which; none: the bridge listens, send the patch from the synth by hand); wait: seconds to
    listen (default 3 with a request, 10 without). Returns (synths, send_while_playing); a missing file: ([], True)."""
    import json
    try:
        with open(path) as f:
            cfg = json.load(f)
    except FileNotFoundError:
        return [], True
    synths = []
    for e in cfg.get("synths", []):
        if not e.get("name") or not e.get("port"):
            continue
        req = e.get("request")
        if isinstance(req, str):
            req = [int(x, 16) for x in req.split()]
        if req and (req[0] != 0xF0 or req[-1] != 0xF7 or any(b > 0x7F for b in req[1:-1])):
            raise ValueError("%s: the request is not a SysEx message (F0 .. F7)" % e["name"])
        synths.append(dict(name=re.sub(r"[^A-Za-z0-9_.-]+", "_", e["name"]), port=e["port"], request=req or None,
                           wait=float(e.get("wait", 3.0 if req else 10.0))))
    return synths, bool(cfg.get("send_while_playing", True))


def split_sysex(data):
    """the F0 .. F7 messages in a .syx file's bytes"""
    out, cur = [], None
    for b in data:
        if b == 0xF0:
            cur = [b]
        elif cur is not None:
            cur.append(b)
            if b == 0xF7:
                out.append(cur)
                cur = None
    return out


class PatchKeeper:
    """0.8 SNAPSHOT PATCHES. The FM-1 says KEEP (SysEx 41: snapshot n, the project's id): the bridge asks each synth of
    patches.json for its patch (or listens while you send it from the synth) and keeps what comes in
    <dump dir>/patches/<project id>/s<n>/<synth>.syx, then answers (42: 0 kept, count; 1 nothing came). The FM-1 says
    PLAY (40, when a snapshot comes back or its sound is SENT): the bridge sends the patches it keeps for that
    snapshot to their synths and answers (42: 2, count). open_port(regex, name) -> (send, close) or None; the
    synths' SysEx comes in through synth_in(name, bytes)."""

    def __init__(self, folder, synths, send_fm1, open_port, writer=None, log=print, send_while_playing=True):
        self.folder, self.synths, self.send, self.open_port, self.log = folder, synths, send_fm1, open_port, log
        self.writer = writer                              # writer(folder) -> a BootWriter (tests: one that needs no root)
        self.send_while_playing = send_while_playing
        self.job = None                                   # a KEEP that listens: dict(n, pid, until, got, ports)

    def snap_dir(self, pid, n):
        return os.path.join(self.folder, "patches", "%08x" % pid, "s%d" % (n + 1))

    def answer(self, code, count):
        self.send(SX_HEAD + [SX_SNAP_ANSWER, code, min(count, 127), 0xF7])

    def fm1_sysex(self, msg, now):
        """a SysEx from the FM-1: True if it was the keeper's"""
        cmd = sx_cmd(msg)
        body = msg[5:-1]
        if cmd not in (SX_SNAP_PLAY, SX_SNAP_KEEP) or len(body) < 7:
            return False
        n, pid, playing = body[0], get7(body[1:6]), body[6]
        if cmd == SX_SNAP_KEEP:
            self.keep(n, pid, now)
        else:
            self.play(n, pid, playing)
        return True

    def keep(self, n, pid, now):
        if self.job:
            self.finish()
        if not self.synths:
            self.log("snapshot %d: no synths in patches.json, no patches to keep" % (n + 1))
            self.answer(1, 0)
            return
        ports, wait = {}, 0.0
        for sy in self.synths:
            p = self.open_port(sy["port"], sy["name"])
            if p is None:
                self.log("snapshot %d: %s is not connected" % (n + 1, sy["name"]))
                continue
            ports[sy["name"]] = p
            wait = max(wait, sy["wait"])
        self.job = dict(n=n, pid=pid, until=now + wait, got={k: [] for k in ports}, ports=ports)
        for sy in self.synths:                            # (the job first: an answer may come at once)
            if sy["name"] in ports and sy["request"]:
                ports[sy["name"]][0](sy["request"])
        if not ports:
            self.finish()
        else:
            self.log("snapshot %d: listening to %s for %.0f s" % (n + 1, ", ".join(ports), wait))

    def synth_in(self, name, msg):
        if self.job and name in self.job["got"] and msg and msg[0] == 0xF0:
            self.job["got"][name].append(list(msg))

    def tick(self, now):
        if self.job and now >= self.job["until"]:
            self.finish()

    def finish(self):
        job, self.job = self.job, None
        for send_close in job["ports"].values():
            try:
                send_close[1]()
            except Exception:
                pass
        kept = {k: v for k, v in job["got"].items() if v}
        if not kept:
            self.answer(1, 0)
            self.log("snapshot %d: no synth sent a patch" % (job["n"] + 1))
            return
        d = self.snap_dir(job["pid"], job["n"])
        w = self.writer(d) if self.writer else BootWriter(d)
        try:
            with w.writable():
                for old in os.listdir(d):
                    if old.endswith(".syx"):
                        os.remove(os.path.join(d, old))
                for name, msgs in kept.items():
                    path = os.path.join(d, name + ".syx")
                    with open(path + ".part", "wb") as f:
                        f.write(bytes(b for m in msgs for b in m))
                        f.flush()
                        os.fsync(f.fileno())
                    os.replace(path + ".part", path)
        except Exception as e:
            self.log("snapshot %d: the patches could not be written: %s" % (job["n"] + 1, e))
            self.answer(1, 0)
            return
        self.answer(0, len(kept))
        self.log("snapshot %d: kept the patches of %s" % (job["n"] + 1, ", ".join(sorted(kept))))

    def play(self, n, pid, playing):
        d = self.snap_dir(pid, n)
        try:
            files = sorted(f for f in os.listdir(d) if f.endswith(".syx"))
        except OSError:
            return                                        # (nothing kept for this snapshot: no answer, no noise)
        if playing and not self.send_while_playing:
            return
        sent = 0
        for f in files:
            name = f[:-4]
            sy = next((x for x in self.synths if x["name"] == name), None)
            p = self.open_port(sy["port"] if sy else re.escape(name), name)
            if p is None:
                self.log("snapshot %d: %s is not connected, its patch stays" % (n + 1, name))
                continue
            try:
                with open(os.path.join(d, f), "rb") as fh:
                    for m in split_sysex(fh.read()):
                        p[0](m)
                sent += 1
            finally:
                p[1]()
        if sent:
            self.answer(2, sent)
            self.log("snapshot %d: patches sent to %d synth(s)" % (n + 1, sent))


# ----------------------------------------------------------------------------------------------- ports
def port_number(name):
    """the ALSA port number at the end of a port name ('... 28:1'), or 0"""
    m = re.search(r"\b\d+:(\d+)\s*$", name)
    return int(m.group(1)) if m else 0


def split_ports(names, pattern, exclude):
    """the ports whose name matches pattern, grouped by ALSA client number (or by name), in client order"""
    rx, ex = re.compile(pattern, re.I), re.compile(exclude, re.I) if exclude else None
    groups = {}
    for n in names:
        if not rx.search(n) or (ex and ex.search(n)):
            continue
        m = re.search(r"\b(\d+):(\d+)\s*$", n)
        key = (int(m.group(1)), 0) if m else (0, n)
        groups.setdefault(key, []).append(n)
    return [groups[k] for k in sorted(groups)]


def pick_port(group):
    """One port of a Launchpad. A Mini MK3 has two USB MIDI interfaces: the first is the DAW one, the second
    (the higher ALSA port number) takes programmer mode and the LED messages: midigrid uses that one only."""
    return sorted(group, key=port_number)[-1]


def fm1_port(group, which="auto"):
    """0.8: the FM-1's port for the bridge. With USB PORTS 2 the FM-1 has two ports (one ALSA client, ports 0 and 1):
    port 2 is the grid's (and the remote's, and the SysEx's), port 1 the synths'. auto: port 2 when there are two."""
    ports = sorted(group, key=port_number)
    if which == "1" or len(ports) < 2:
        return ports[0]
    return ports[1]


def client_number(name):
    """the ALSA client number in a port name ('... 28:1' -> 28), or None"""
    m = re.search(r"\b(\d+):\d+\s*$", name)
    return int(m.group(1)) if m else None


def alsa_clients(path="/proc/asound/seq/clients"):
    """{client number: name} of the ALSA sequencer clients, or None where there is no such file. It is read from /proc
    on purpose: asking mido for the port names would create an ALSA client each time, and RaspiMIDIHub rescans its
    devices whenever a client appears or leaves."""
    try:
        with open(path) as f:
            return {int(m.group(1)): m.group(2) for m in re.finditer(r'^Client\s+(\d+)\s*:\s*"(.*?)"', f.read(), re.M)}
    except OSError:
        return None


SX_STATO, SX_FRASE, SX_RISPOSTA, SX_TOCCATA, SX_REGIA_LED, SX_REGIA_KEY = 0x50, 0x51, 0x52, 0x53, 0x54, 0x55
RISPOSTA_TEXT = {0: "written", 1: "busy: a phrase is waiting", 2: "the track is locked", 3: "the frame is broken"}
STATO_FIELDS = ("bar", "scene", "snap", "root", "scale", "deg", "col", "harm", "phrase_bar", "phrase_bars", "energy",
                "set_genre", "queue", "playing")


def frase_frame(track, bars, steps):
    """SysEx 51: a phrase onto track (0-15), bars 1-4 of 16 steps; steps = [(step, note, vel, len%), ...] with
    len 1..100 the gate, 0 = two steps long. None if it cannot be said in a frame."""
    if not 0 <= track < 16 or not 1 <= bars <= 4 or len(steps) > 64:
        return None
    body = [track, bars, len(steps)]
    for st, note, vel, ln in steps:
        if not (0 <= st < 16 * bars and 0 <= note <= 127 and 0 <= vel <= 127 and 0 <= ln <= 100):
            return None
        body += [st, note, vel, ln]
    return SX_HEAD + [SX_FRASE] + body + [0xF7]


def regia_led_frame(leds):
    """SysEx 54: the 16 LEDs of the REGIA view (0 off, 1 on, 2 passing)"""
    leds = [min(max(int(v), 0), 2) for v in list(leds)[:16]]
    return SX_HEAD + [SX_REGIA_LED] + leds + [0xF7]


def parse_stato(msg):
    """SysEx 50 -> dict, None if it is not one"""
    if sx_cmd(msg) != SX_STATO:
        return None
    body = list(msg)[5:-1]
    if len(body) < 15:
        return None
    vals = [get7(body[0:2])] + body[2:15]
    d = dict(zip(STATO_FIELDS, vals))
    d["deg"] -= 64
    if d["snap"] == 127:
        d["snap"] = None
    return d


class Regista:
    """0.9 the REGISTA: the Pi talks to the FM-1 as a second musician (docs/SAGGA-SEQ.md). The FM-1 sends STATO (50)
    at every bar line and at a change of scene, snapshot or chord, RISPOSTA (52) to a FRASE, TOCCATA (53) when a hand
    changes a track, REGIA TASTO (55) when a rule is tapped on the grid; the bridge sends FRASE (51, a phrase onto a
    track at the next bar) and REGIA LED (54, the rules' LEDs). The FM-1 only talks once it has heard a FRASE or a
    REGIA LED. on_* hooks are for a regista running on the Pi (a script that imports the bridge)."""

    def __init__(self, send_fm1, log=print, verbose=False):
        self.send, self.log, self.verbose = send_fm1, log, verbose
        self.stato = None                                 # the last STATO, as parse_stato gives it
        self.on_stato = self.on_risposta = self.on_toccata = self.on_key = None
        self.pending = {}                                 # track -> steps of a FRASE sent, until RISPOSTA
        self.leds = [0] * 16

    def start(self):
        """say hello: the LEDs off, so that the FM-1 starts sending STATO"""
        self.led(self.leds)

    def frase(self, track, bars, steps):
        f = frase_frame(track, bars, steps)
        if f is None:
            raise ValueError("a phrase that does not fit a frame (track %r, %r bars, %d steps)" % (track, bars, len(steps)))
        self.pending[track] = steps
        self.send(f)

    def led(self, leds):
        self.leds = [min(max(int(v), 0), 2) for v in list(leds)[:16]] + [0] * (16 - min(len(leds), 16))
        self.send(regia_led_frame(self.leds))

    def fm1_sysex(self, msg, now=None):
        """a SysEx from the FM-1: True if it was the regista's"""
        cmd = sx_cmd(msg)
        if cmd not in (SX_STATO, SX_RISPOSTA, SX_TOCCATA, SX_REGIA_KEY):
            return False
        body = list(msg)[5:-1]
        if cmd == SX_STATO:
            st = parse_stato(msg)
            if st is None:
                return True
            self.stato = st
            if self.verbose:
                self.log("STATO: bar %d scene %d snap %s key %d/%d deg %+d col %d harm %d phrase %d/%d energy %d genre %d queue %d %s"
                         % (st["bar"], st["scene"] + 1, "-" if st["snap"] is None else st["snap"] + 1, st["root"], st["scale"],
                            st["deg"], st["col"], st["harm"], st["phrase_bar"] + 1, st["phrase_bars"], st["energy"],
                            st["set_genre"], st["queue"], "playing" if st["playing"] else "stopped"))
            if self.on_stato:
                self.on_stato(st)
        elif cmd == SX_RISPOSTA and len(body) >= 2:
            t, code = body[0], body[1]
            self.pending.pop(t, None)
            self.log("regista: track %d: %s" % (t + 1, RISPOSTA_TEXT.get(code, "code %d" % code)))
            if self.on_risposta:
                self.on_risposta(t, code)
        elif cmd == SX_TOCCATA and len(body) >= 1:
            if self.verbose:
                self.log("regista: track %d touched by hand" % (body[0] + 1))
            if self.on_toccata:
                self.on_toccata(body[0])
        elif cmd == SX_REGIA_KEY and len(body) >= 1:
            self.log("regista: rule %d tapped" % (body[0] + 1))
            if self.on_key:
                self.on_key(body[0])
        return True


class PortWatch:
    """Notices that a Launchpad or the FM-1 has gone. ALSA drops the connections of a client that leaves, and a
    program that goes on writing to a port nobody listens to gets no error: without this the bridge would sit
    there mute after a cable was pulled. Ends in a restart (the service) that finds the new ports."""

    def __init__(self, port_names, read=None, every=1.0):
        self.read = read or (lambda: alsa_clients())
        self.every = every
        self.next = 0.0
        self.want = {}
        now = self.read()
        if now is not None:
            for n in port_names:
                c = client_number(n)
                if c is not None and c in now:
                    self.want[c] = now[c]

    def check(self, now):
        """None while all is well, else a sentence about the client that has gone"""
        if not self.want or now < self.next:
            return None
        self.next = now + self.every
        cur = self.read()
        if cur is None:
            return None
        for c, name in sorted(self.want.items()):
            if cur.get(c) != name:
                return "ALSA client %d (%s) %s" % (c, name, "is gone" if c not in cur else "is now %r" % cur[c])
        return None


def plan_ports(ins, outs, left=None, right=None, exclude="DAW|DIN", pattern="Launchpad Mini"):
    """-> [(input port, output port)] for the left and the right Launchpad; SystemExit with advice if that fails"""
    if left or right:
        if not (left and right):
            raise SystemExit("give both --left and --right")
        pairs = []
        for p in (left, right):
            g_in, g_out = split_ports(ins, p, exclude), split_ports(outs, p, exclude)
            if not g_in or not g_out:
                raise SystemExit("no Launchpad port matches %r; try --list" % p)
            pairs.append((pick_port(g_in[0]), pick_port(g_out[0])))
        return pairs
    g_in, g_out = split_ports(ins, pattern, exclude), split_ports(outs, pattern, exclude)
    if len(g_in) < 2 or len(g_out) < 2:
        raise SystemExit("found %d Launchpad(s), need 2: plug both in, or name them with --left / --right (see --list)"
                         % min(len(g_in), len(g_out)))
    return [(pick_port(g_in[i]), pick_port(g_out[i])) for i in (0, 1)]


def one_shot(a, mido, ins, outs):
    """--export / --import: only the FM-1's ports, no Launchpads (the bridge may be running too: ALSA shares ports)"""
    names_in, names_out = split_ports(ins, a.fm1, None), split_ports(outs, a.fm1, None)
    if not names_in or not names_out:
        sys.exit("no port matches --fm1 %r; try --list" % a.fm1)
    q = queue.Queue()
    inp = mido.open_input(fm1_port(names_in[0], a.port), callback=lambda m: q.put(m.bytes()))
    out = mido.open_output(fm1_port(names_out[0], a.port))

    def send(msg):
        out.send(mido.Message.from_bytes(msg))

    def next_sysex(timeout):
        try:
            raw = q.get(timeout=timeout)
        except queue.Empty:
            return None
        return raw if raw and raw[0] == 0xF0 else None

    try:
        if a.import_file:
            with open(a.import_file, "rb") as f:
                image = f.read()
            why = check_image(image)
            if why:
                print("%s: %s" % (a.import_file, why), file=sys.stderr)
                return 2
            snd = DumpSender(image, send)
            snd.start(time.monotonic())
            while snd.state == "sending":
                raw = next_sysex(0.02)
                now = time.monotonic()
                if raw:
                    snd.feed(raw, now)
                snd.tick(now)
            if snd.state != "done":
                print("import failed: %s" % snd.error, file=sys.stderr)
                return 1
            print("imported %s (%d bytes): it is the FM-1's project now; SAVE on the FM-1 keeps it" % (a.import_file, len(image)))
            return 0
        rcv = DumpReceiver()
        send(export_request(None if a.export == 0 else a.export - 1))
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            raw = next_sysex(0.05)
            got = rcv.feed(raw) if raw else None
            if got and got[0] == "image":
                if a.out:
                    path = BootWriter(os.path.dirname(os.path.abspath(a.out))).write(os.path.abspath(a.out), got[1])
                else:
                    path = save_image(got[1], a.dump_dir or default_dump_dir())
                print("saved %s (%d bytes)" % (path, len(got[1])))
                return 0
            if got:
                print("export failed: %s" % got[1], file=sys.stderr)
                return 1
        print("no answer from the FM-1 (is it SAGGA SEQ 0.3 or later?)", file=sys.stderr)
        return 1
    finally:
        inp.close()
        out.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--list", action="store_true", help="show the MIDI ports and exit")
    ap.add_argument("--model", choices=sorted(DRIVERS), default="mk3")
    ap.add_argument("--fm1", default=FM1_PATTERN, help="regex of the FM-1's port name (default: %s; a Felucca-based build"
                    " shows up as 'Felucca 2')" % FM1_PATTERN)
    ap.add_argument("--port", choices=("auto", "1", "2"), default="auto", help="the FM-1's port to use: with USB PORTS 2 "
                    "(the FM-1's USB page) port 2 carries the grid; auto takes port 2 when the FM-1 has two (default)")
    ap.add_argument("--patches", help="the synths whose patches the snapshots keep (default: patches.json in --dump-dir)")
    ap.add_argument("--left", help="regex of the LEFT Launchpad's port (default: the first two 'Launchpad Mini' devices)")
    ap.add_argument("--right", help="regex of the RIGHT Launchpad's port")
    ap.add_argument("--exclude", default="DAW|DIN", help="ports to leave alone (default: DAW|DIN, the Mini MK3's DAW interface)")
    ap.add_argument("--swap", action="store_true", help="exchange left and right")
    ap.add_argument("--frame", action="store_true", help="the LEFT Launchpad is turned a quarter anticlockwise, as in "
                    "midigrid with a rotated quad: the round buttons frame the grid (16 on top, 8 on each side) and its "
                    "cable leaves at the top, out of the way")
    ap.add_argument("--identify", action="store_true", help="light the left half green and the right half red, no FM-1")
    ap.add_argument("--dump-dir", help="where exported projects are saved (default: /boot/firmware/sagga if writable, "
                    "else ~/sagga-projects)")
    ap.add_argument("--export", nargs="?", const=0, type=int, metavar="SLOT",
                    help="ask the FM-1 (stopped) for its project, or for saved slot 1-8, save it as a file and exit")
    ap.add_argument("--out", help="with --export: the file to write (default: a new one in --dump-dir)")
    ap.add_argument("--import", dest="import_file", metavar="FILE",
                    help="send a .sgq project to the FM-1 (stopped): it replaces the project there (SAVE keeps it); then exit")
    ap.add_argument("--regista", action="store_true", help="0.9: print the FM-1's STATO frames (bar, scene, key, chord, "
                    "phrase, energy) and the tracks touched by hand; the REGIA LEDs start off")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    if a.export is not None and not 0 <= a.export <= 8:
        ap.error("--export takes a slot 1-8 (or nothing: the current project)")

    try:
        import mido
    except ImportError:
        sys.exit("needs mido and python-rtmidi:  apt install python3-mido python3-rtmidi   (or: pip install mido python-rtmidi)")

    ins, outs = mido.get_input_names(), mido.get_output_names()
    if a.list:
        print("inputs:");  [print("  ", n) for n in ins]
        print("outputs:"); [print("  ", n) for n in outs]
        return 0

    if a.export is not None or a.import_file:
        return one_shot(a, mido, ins, outs)

    pairs = plan_ports(ins, outs, a.left, a.right, a.exclude, DEFAULT_PATTERN[a.model])
    q = queue.Queue()
    opened = []
    lp_out = []
    for idx, (pin, pout) in enumerate(pairs):
        print("%s Launchpad: in %r, out %r" % (("left", "right")[idx], pin, pout))
        opened.append(mido.open_input(pin, callback=(lambda m, i=idx, nm=pin: q.put(("lp", i, nm, m.bytes())))))
        lp_out.append(mido.open_output(pout))

    fm1_out = None
    watched = [p for pair in pairs for p in pair]
    if a.identify:
        fm1_out = None
    else:
        names_in, names_out = split_ports(ins, a.fm1, None), split_ports(outs, a.fm1, None)
        if not names_in or not names_out:
            sys.exit("no port matches --fm1 %r; try --list" % a.fm1)
        fin, fout = fm1_port(names_in[0], a.port), fm1_port(names_out[0], a.port)
        print("FM-1: in %r, out %r%s" % (fin, fout, " (USB PORTS 2: port 2)" if len(names_in[0]) > 1 and a.port != "1" else ""))
        opened.append(mido.open_input(fin, callback=lambda m: q.put(("fm1", 0, "", m.bytes()))))
        fm1_out = mido.open_output(fout)
        watched += [fin, fout]
    watch = PortWatch(watched)

    def send_lp(idx, msg):
        lp_out[idx].send(mido.Message.from_bytes(msg))

    def send_fm1(msg):
        if fm1_out is not None:
            fm1_out.send(mido.Message.from_bytes(msg))
        if a.verbose:
            print("-> FM-1", msg)

    br = Bridge(send_lp, send_fm1, model=a.model, swap=a.swap, turned=(a.frame, False))
    dump_dir = a.dump_dir or default_dump_dir()
    lib = Library(dump_dir, send_fm1, log=lambda text: print(text, file=sys.stderr if "could not" in text or "cannot" in text else sys.stdout))
    print("library: %s (%d files)" % (dump_dir, len(library_files(dump_dir))))
    control = Control(lib, log=lambda text: print(text, file=sys.stderr if "cannot" in text else sys.stdout))   # 0.14: the hub's editor
    try:
        synths, send_playing = load_patch_config(a.patches or os.path.join(dump_dir, "patches.json"))
    except (ValueError, OSError) as e:
        print("patches.json: %s (snapshot patches off)" % e, file=sys.stderr)
        synths, send_playing = [], True

    def open_synth(pattern, name):
        """(send, close) of a synth's port, its SysEx coming into the queue; None if it is not there"""
        try:
            ins_now, outs_now = mido.get_input_names(), mido.get_output_names()
            o = [n for n in outs_now if re.search(pattern, n, re.I) and not re.search(a.fm1, n, re.I)]
            i = [n for n in ins_now if re.search(pattern, n, re.I) and not re.search(a.fm1, n, re.I)]
            if not o:
                return None
            po = mido.open_output(o[0])
            pi = mido.open_input(i[0], callback=lambda m, nm=name: q.put(("syn", 0, nm, m.bytes()))) if i else None
        except Exception:
            return None

        def close():
            for p in (po, pi):
                if p is not None:
                    p.close()
        return (lambda msg: po.send(mido.Message.from_bytes(msg))), close
    keeper = PatchKeeper(dump_dir, synths, send_fm1, open_synth, send_while_playing=send_playing,
                         log=lambda text: print(text, file=sys.stderr if "could not" in text else sys.stdout))
    if synths:
        print("snapshot patches: %s" % ", ".join(sy["name"] for sy in synths))
    regista = Regista(send_fm1, verbose=a.regista)                 # 0.9: STATO / RISPOSTA / TOCCATA / REGIA TASTO in
    try:                                                           # 0.11: the patterns of the genres
        patterns = PatternLib(os.path.join(dump_dir, "patterns"), send_fm1, writer=BootWriter(os.path.join(dump_dir, "patterns")),
                              log=lambda text: print(text, file=sys.stderr if "could not" in text else sys.stdout))
    except ImportError:
        patterns = None
        print("patterns: sagga_patterns.py not found (the Pi's patterns off)", file=sys.stderr)
    try:                                                           # 0.11: the progressions of the genres
        progs = ProgLib(os.path.join(dump_dir, "progressions"), send_fm1, writer=BootWriter(os.path.join(dump_dir, "progressions")),
                        log=lambda text: print(text, file=sys.stderr if "could not" in text else sys.stdout))
    except ImportError:
        progs = None
        print("progressions: sagga_progs.py not found (the Pi's progressions off)", file=sys.stderr)

    rc = 0
    try:
        br.start(time.monotonic())
        if a.identify:
            br.identify()
        print("bridge running (Ctrl-C to stop)")
        while True:
            try:
                kind, idx, port, raw = q.get(timeout=0.005)
            except queue.Empty:
                kind = None
            now = time.monotonic()
            if kind == "lp":
                ev = br.lp_in(idx, raw, port, now)
                if a.identify and ev and ev[0] == "pad" and ev[3]:
                    print("pad pressed on the %s Launchpad (columns %s)" % (("left", "right")[idx ^ a.swap], ("1-8", "9-16")[idx ^ a.swap]))
            elif kind == "fm1" and raw and raw[0] == 0xF0:          # SysEx: the library, a project the FM-1 exports
                if not keeper.fm1_sysex(raw, now) and not regista.fm1_sysex(raw, now) and not (patterns and patterns.fm1_sysex(raw, now)) \
                        and not (progs and progs.fm1_sysex(raw, now)):
                    lib.fm1_sysex(raw, now)                                  # (a snapshot's patches, the regista, 0.11 the patterns, the progressions)
            elif kind == "syn":
                keeper.synth_in(port, raw)
            elif kind == "fm1" and not a.identify:
                br.fm1_in(raw)
            br.tick(now)
            lib.tick(now)
            control.tick(now)
            keeper.tick(now)
            gone = watch.check(now)
            if gone:
                raise RuntimeError(gone)
    except KeyboardInterrupt:
        pass
    except Exception as e:                       # a Launchpad or the FM-1 went away: stop, so that a service restarts us
        print("bridge stopped: %s: %s" % (type(e).__name__, e), file=sys.stderr)
        rc = 1
    finally:
        try:
            br.stop()
        except Exception:
            pass
        for p in opened + lp_out + ([fm1_out] if fm1_out is not None else []):
            try:
                p.close()
            except Exception:
                pass
    return rc


if __name__ == "__main__":
    sys.exit(main())
