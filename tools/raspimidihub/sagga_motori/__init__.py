# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA MOTORI - a RaspiMIDIHub controller for SAGGA SEQ 0.12: the tracks as engines, one row each (0.28: twelve).

A row a track: MUTE (channel 14, CC 48 + t), PATTERN 1-8 (channel 13, CC 33 + t: at the QUANTISE moment), LENGTH 1-64
(channel 13, CC 49 + t: at the bar line while it plays), RETRIG (channel 14, CC 90 + t: from its first step), KILL
(channel 14, CC 64 + t: silent while on). Under the rows: the tablet's track (channel 13, CC 112; 0.18: a track of the
pages' own, the FM-1 keeps its selected one) and its MODE (CC 113: FREE, IN KEY, DRUM, TAPE, BREAK), the dice of its
pattern (CC 69), UNDO (channel 14, CC 36).

Wire this plugin's OUT to the FM-1 (with USB PORTS 2: to its port 2) and set SAVE K2 on the FM-1 to REMOTE 13 + 14.
"""

from raspimidihub.controller_base import ControllerBase
from raspimidihub.plugin_api import Button, Knob, LayoutCell, LayoutGrid, Radio

CH13 = 12                                 # MIDI channel 13 (0-based): VIAGGIO and the 0.12 commands
CH14 = 13                                 # MIDI channel 14: SAGGA REMOTE

PATTERN_LABELS = ["P%d" % (i + 1) for i in range(8)]
MODE_LABELS = ["FREE", "IN KEY", "DRUM", "TAPE", "BREAK"]
TRACKS = 12                               # 0.28: the FM-1's tracks (until 0.27: sixteen)
TRACK_LABELS = ["T%d" % (i + 1) for i in range(TRACKS)]


def tap(name, label, ch, cc, col, row, color="green"):
    return LayoutCell(Button(name, label, color=color, trigger=True), col=col, row=row, channel=ch, cc=cc)


def hold(name, label, ch, cc, col, row, color="red"):
    return LayoutCell(Button(name, label, color=color), col=col, row=row, channel=ch, cc=cc)


def knob(name, label, ch, cc, col, row, lo, hi, default, labels=None):
    return LayoutCell(Knob(name, label, min=lo, max=hi, default=default, labels=labels or []), col=col, row=row, channel=ch, cc=cc)


CELLS = []
for t in range(TRACKS):
    r = t + 1
    CELLS += [
        tap("m%d" % t, "MUTE %d" % (t + 1), CH14, 48 + t, 1, r),
        knob("p%d" % t, "PATTERN %d" % (t + 1), CH13, 33 + t, 2, r, 0, 7, 0, PATTERN_LABELS),
        knob("l%d" % t, "LENGTH %d" % (t + 1), CH13, 49 + t, 3, r, 1, 64, 16),
        tap("r%d" % t, "RETRIG %d" % (t + 1), CH14, 90 + t, 4, r, "blue"),
        hold("k%d" % t, "KILL %d" % (t + 1), CH14, 64 + t, 5, r),
    ]
CELLS += [
    knob("sel", "TRACK", CH13, 112, 1, TRACKS + 1, 0, TRACKS - 1, 0, TRACK_LABELS),
    knob("mode", "MODE", CH13, 113, 2, TRACKS + 1, 0, 4, 0, MODE_LABELS),
    tap("dice", "DICE", CH13, 69, 3, TRACKS + 1, "yellow"),
    tap("undo", "UNDO", CH14, 36, 4, TRACKS + 1, "yellow"),
    tap("keep", "KEEP DICE", CH14, 85, 5, TRACKS + 1),
]


class SaggaMotori(ControllerBase):
    """SAGGA SEQ's twelve tracks: mute, pattern, length, retrig, kill; the tablet's track and its mode."""

    NAME = "SAGGA Motori"
    DESCRIPTION = "SAGGA SEQ (M-VAVE FM-1): the 12 tracks - mute, pattern, length, retrig, kill - and the tablet's track and its mode"
    AUTHOR = "SAGGA SEQ"
    VERSION = "0.28"
    HELP = """\
A row a track. MUTE (at the QUANTISE moment when MUTE QUEUE is on), PATTERN 1-8 (it changes at the QUANTISE moment:
AUTO = the end of the track's loop), LENGTH 1-64 (while it plays: at the bar line), RETRIG (the track from its first
step on its next step), KILL (silent while on). TRACK picks the tablet's track (the one SAGGA Live, Mod and Break work
on; the FM-1 keeps its own and its screen says TAB T5), MODE its mode (FREE, IN KEY, DRUM, TAPE, BREAK); DICE rolls its
pattern (KEEP DICE keeps it, UNDO puts it back).
Channel 13: CC 33-44 patterns, 49-60 lengths, 69 dice, 112 track, 113 mode. Channel 14: CC 48-59 mutes, 64-75 kills,
90-101 retrig, 36 UNDO, 85 KEEP (0.28: twelve tracks). The FM-1 needs SAVE K2 = REMOTE 13 + 14; wire OUT to the FM-1 (USB PORTS 2: port 2)."""

    params = [
        Radio("bg", "Background", ControllerBase.BG_OPTIONS, default="Forest", config_only=True),
        LayoutGrid("controller", "", cols=5, rows=TRACKS + 1, labels_param="cell_labels", bindings_param="cell_bindings", cells=CELLS),
    ]

    cc_outputs = sorted({c.cc for c in CELLS})
    outputs = ["CC on ch 13 and 14: the tracks of SAGGA SEQ 0.12"]

    TRIGGERS = frozenset(c.param.name for c in CELLS if isinstance(c.param, Button) and c.param.trigger)

    def on_cc(self, channel, cc, value):
        """0.20.6: the FM-1 sends this cell's value back on channel 12 CC 35 (its own CC 38 is, in MIDI 2.0, part of an
        RPN / NRPN: RaspiMIDIHub 6's pages never get it from the FM-1 as a CC): taken as the cell's"""
        if channel == 11 and cc == 35:
            b = self._effective_binding('p5')
            if b is not None:
                channel, cc = b["channel"], b["cc"]
        super().on_cc(channel, cc, value)

    def on_param_change(self, name, value):
        super().on_param_change(name, value)
        if name in self.TRIGGERS and value:          # a press: 127, then 0 (the FM-1 acts on the press)
            b = self._effective_binding(name)
            if b is not None:
                self.send_cc(b["channel"], b["cc"], b.get("off", 0))
            self.set_param(name, False, persist=False)

    def panic(self):
        """the hub's PANIC: the KILLs let go; the knobs stay (a reset would change the FM-1's patterns and lengths)"""
        for cell in CELLS:
            name = cell.param.name
            if isinstance(cell.param, Button) and name not in self.TRIGGERS and self.get_param(name):
                b = self._effective_binding(name)
                if b is not None:
                    self.send_cc(b["channel"], b["cc"], b.get("off", 0))
                self.set_param(name, False, persist=False)
