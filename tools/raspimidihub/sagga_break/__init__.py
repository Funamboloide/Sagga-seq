# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA BREAK - a RaspiMIDIHub controller for SAGGA SEQ 0.12: a drum break cut into slices, played and re-ordered live.

Sixteen pads (channel 13, CC 76-91: a press plays slice 1-16 of the tablet's track, a BREAK, on its sampler; on any other
track they are the track's notes from C1), and the break's moves on that track (0.18: the track TRACK picks on SAGGA
Live, Motori or Mod; the FM-1 keeps its selected one): ROLL (held: the slice that
played again on every step) and ROLL/2 (twice a step), HALF, DOUBLE, BACKWARDS, DICE (the backbone kept: kick on the
one and three, snare on the two and four, the rest re-ordered), RESET (slices 1..16 in a row), TAKE (what the pads
played in the last loop goes into the pattern). The knobs: CHOP (the library of re-orders, written over the loop:
STRAIGHT, END ROLL, RUSH, REPEAT, DOUBLE, HALF, BACKWARDS, GHOST, LOW, HIGH, SHUFFLE, THINK, APACHE, SNARES,
TRIPLE, BUILD), ROLLS (how many steps the dice rolls), SWAP (how much the dice re-orders), SLICES (8, 16, 32).

Wire this plugin's OUT to the FM-1 (USB PORTS 2: its port 2); SAVE K2 on the FM-1 = REMOTE 13 + 14. The track must be a
BREAK (HOME 4 K1, or SAGGA Motori's MODE): its PEN note is slice 1 on the sampler.
"""

from raspimidihub.controller_base import ControllerBase
from raspimidihub.plugin_api import Button, Knob, LayoutCell, LayoutGrid, Radio

CH13 = 12                                 # MIDI channel 13 (0-based)

CHOP_LABELS = ["STRAIGHT", "END ROLL", "RUSH", "REPEAT", "DOUBLE", "HALF", "BACKWARDS", "GHOST", "LOW", "HIGH",
               "SHUFFLE", "THINK", "APACHE", "SNARES", "TRIPLE", "BUILD"]          # one a white key of the FM-1 (ARP + white 1-16)
SLICE_LABELS = ["8", "16", "32"]


def tap(name, label, cc, col, row, color="green"):
    return LayoutCell(Button(name, label, color=color, trigger=True), col=col, row=row, channel=CH13, cc=cc)


def hold(name, label, cc, col, row, color="yellow"):
    return LayoutCell(Button(name, label, color=color), col=col, row=row, channel=CH13, cc=cc)


def knob(name, label, cc, col, row, lo, hi, default, labels=None):
    return LayoutCell(Knob(name, label, min=lo, max=hi, default=default, labels=labels or []), col=col, row=row, channel=CH13, cc=cc)


CELLS = [
    # the pads: four rows of four, slice 1 bottom left as on a sampler (row 4 = slices 1-4)
    *[tap("s%d" % i, "SLICE %d" % (i + 1), 76 + i, (i % 4) + 1, 4 - i // 4, "blue" if i % 4 == 0 else "green") for i in range(16)],
    hold("roll", "ROLL", 65, 1, 5, "red"),
    hold("roll2", "ROLL/2", 71, 2, 5, "red"),
    tap("half", "HALF", 66, 3, 5, "yellow"),
    tap("double", "DOUBLE", 67, 4, 5, "yellow"),
    tap("back", "BACKWARDS", 68, 1, 6, "yellow"),
    tap("dice", "DICE", 69, 2, 6),
    tap("reset", "RESET", 70, 3, 6),
    tap("take", "TAKE", 107, 4, 6, "red"),
    knob("chop", "CHOP", 72, 1, 7, 0, 15, 0, CHOP_LABELS),
    knob("rolls", "ROLLS", 74, 2, 7, 0, 7, 2),
    knob("swap", "SWAP", 73, 3, 7, 0, 7, 3),
    knob("slices", "SLICES", 75, 4, 7, 0, 2, 1, SLICE_LABELS),
]


class SaggaBreak(ControllerBase):
    """SAGGA SEQ's BREAK tracks: the slices as pads, the live moves, the chops."""

    NAME = "SAGGA Break"
    DESCRIPTION = "SAGGA SEQ (M-VAVE FM-1): 16 slice pads, ROLL / HALF / DOUBLE / BACKWARDS / DICE / RESET, the chops - jungle breaks live"
    AUTHOR = "SAGGA SEQ"
    VERSION = "0.12"
    HELP = """\
The tablet's track (TRACK on SAGGA Live, Motori or Mod picks it; the FM-1's screen says TAB T5) in BREAK mode plays a
drum break cut into slices on consecutive notes of your sampler
(slice 1 = the track's PEN note). SLICE 1-16: a pad plays that slice now (with REC on the FM-1 it is written; TAKE writes
what you played in the last loop). ROLL and ROLL/2: while held, the slice that played last comes again on every step
(or twice a step). HALF, DOUBLE, BACKWARDS: the pattern's slices transformed; DICE: re-ordered, the kick and snare kept
on the beats; RESET: 1..16 in a row. CHOP writes a re-order from the library over the loop (UNDO on the FM-1 takes it
back); ROLLS and SWAP set the dice; SLICES says how many the break has (8, 16, 32): the three show the tablet's
track's (SAGGA SEQ 0.21 sends them back; CHOP is a move, it shows the last one you wrote).
Channel 13: CC 76-91 pads, 65 ROLL, 71 ROLL/2, 66-70 the moves, 107 TAKE, 72-75 the knobs. The FM-1: SAVE K2 = REMOTE
13 + 14; wire OUT to it (USB PORTS 2: port 2)."""

    params = [
        Radio("bg", "Background", ControllerBase.BG_OPTIONS, default="Wine", config_only=True),
        LayoutGrid("controller", "", cols=4, rows=7, labels_param="cell_labels", bindings_param="cell_bindings", cells=CELLS),
    ]

    cc_outputs = sorted({c.cc for c in CELLS})
    outputs = ["CC on ch 13: the slices and the moves of a SAGGA SEQ 0.12 BREAK track"]

    TRIGGERS = frozenset(c.param.name for c in CELLS if isinstance(c.param, Button) and c.param.trigger)

    def on_param_change(self, name, value):
        super().on_param_change(name, value)
        if name in self.TRIGGERS and value:          # a pad: 127 (the slice sounds), then 0 (its note-off)
            b = self._effective_binding(name)
            if b is not None:
                self.send_cc(b["channel"], b["cc"], b.get("off", 0))
            self.set_param(name, False, persist=False)

    def panic(self):
        """the hub's PANIC: the ROLLs let go; the knobs stay"""
        for cell in CELLS:
            name = cell.param.name
            if isinstance(cell.param, Button) and name not in self.TRIGGERS and self.get_param(name):
                b = self._effective_binding(name)
                if b is not None:
                    self.send_cc(b["channel"], b["cc"], b.get("off", 0))
                self.set_param(name, False, persist=False)
