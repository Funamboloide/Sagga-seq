# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA MUTES - a RaspiMIDIHub controller for SAGGA SEQ 0.8: the tracks' mutes, kills and RETRIG, on MIDI channel 14
(0.28: twelve tracks).

MUTE 1-12 switch a track's mute (with MUTE QUEUE on, at the next quantised moment); KILL 1-12 silence a track while
they are on; RETRIG 1-12 send a track back to its first step on the next step. Wire this plugin's OUT to the FM-1 in
RaspiMIDIHub's matrix.
"""

from raspimidihub.controller_base import ControllerBase
from raspimidihub.plugin_api import Button, LayoutCell, LayoutGrid, Radio

CH = 13                                   # MIDI channel 14 (0-based)
TRACKS = 12                               # 0.28: the FM-1's tracks (until 0.27: sixteen; CC 60-63, 76-79, 102-105 stay unsent)

CELLS = [
    *[LayoutCell(Button("m%d" % i, "MUTE %d" % (i + 1), color="green", trigger=True),
                 col=(i % 4) + 1, row=1 + i // 4, channel=CH, cc=48 + i) for i in range(TRACKS)],
    *[LayoutCell(Button("k%d" % i, "KILL %d" % (i + 1), color="red"),
                 col=(i % 4) + 1, row=4 + i // 4, channel=CH, cc=64 + i) for i in range(TRACKS)],
    *[LayoutCell(Button("r%d" % i, "RETRIG %d" % (i + 1), color="blue", trigger=True),
                 col=(i % 4) + 1, row=7 + i // 4, channel=CH, cc=90 + i) for i in range(TRACKS)],
]


class SaggaMutes(ControllerBase):
    """SAGGA SEQ's 12 mutes, kills and RETRIG on channel 14."""

    NAME = "SAGGA Mutes"
    DESCRIPTION = "SAGGA SEQ (M-VAVE FM-1): mute, kill, retrigger the 12 tracks, on ch 14"
    AUTHOR = "SAGGA SEQ"
    VERSION = "0.28"
    HELP = """\
MUTE 1-12: a track's mute on / off (it waits for the QUANTISE if MUTE QUEUE is on in SAGGA SEQ). KILL 1-12: the track
is silent while the button is on, its notes stop at once. RETRIG 1-12: the track starts again from its first step on
its next step (the others go on). CC 48-59, 64-75 and 90-101 on MIDI channel 14; wire OUT to the FM-1."""

    params = [
        Radio("bg", "Background", ControllerBase.BG_OPTIONS, default="Wine", config_only=True),
        LayoutGrid("controller", "", cols=4, rows=9, labels_param="cell_labels", bindings_param="cell_bindings", cells=CELLS),
    ]

    cc_outputs = list(range(48, 48 + TRACKS)) + list(range(64, 64 + TRACKS)) + list(range(90, 90 + TRACKS))
    outputs = ["CC 48-59, 64-75, 90-101 on ch 14: mutes, kills, RETRIG of SAGGA SEQ"]

    TRIGGERS = frozenset(["m%d" % i for i in range(TRACKS)] + ["r%d" % i for i in range(TRACKS)])

    def on_param_change(self, name, value):
        super().on_param_change(name, value)
        if name in self.TRIGGERS and value:
            b = self._effective_binding(name)
            if b is not None:
                self.send_cc(b["channel"], b["cc"], b.get("off", 0))
            self.set_param(name, False, persist=False)

    def panic(self):
        """the hub's PANIC: the KILLs that are held are let go"""
        for cell in CELLS:
            name = cell.param.name
            if isinstance(cell.param, Button) and name not in self.TRIGGERS and self.get_param(name):
                b = self._effective_binding(name)
                if b is not None:
                    self.send_cc(b["channel"], b["cc"], b.get("off", 0))
                self.set_param(name, False, persist=False)
