# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA MUTES - a RaspiMIDIHub controller for SAGGA SEQ 0.8: the tracks' mutes, kills and RETRIG, on MIDI channel 14
(0.28: twelve tracks; 0.31: and the groups).

MUTE 1-12 switch a track's mute (with MUTE QUEUE on, at the next quantised moment); KILL 1-12 silence a track while
they are on; RETRIG 1-12 send a track back to its first step on the next step. 0.31: under each of the three, the four
GROUPS - the drums, the bass, the melodic ones, all of them (the CCs of tracks 13-16 until 0.27): MUTE a group (it goes
quiet if any of it plays, else it comes back; ALL ON: every track audible), KILL a group while on (the fourth: all but
the tablet's track), RETRIG a group. Wire this plugin's OUT to the FM-1 in RaspiMIDIHub's matrix.
"""

from raspimidihub.controller_base import ControllerBase
from raspimidihub.plugin_api import Button, LayoutCell, LayoutGrid, Radio

CH = 13                                   # MIDI channel 14 (0-based)
TRACKS = 12                               # 0.28: the FM-1's tracks (until 0.27: sixteen)
GROUPS = ("DRUMS", "BASS", "MELODIC", "ALL")   # 0.31: on the CCs of tracks 13-16 - 60-63, 76-79, 102-105

CELLS = [
    *[LayoutCell(Button("m%d" % i, "MUTE %d" % (i + 1), color="green", trigger=True),
                 col=(i % 4) + 1, row=1 + i // 4, channel=CH, cc=48 + i) for i in range(TRACKS)],
    *[LayoutCell(Button("mg%d" % g, "ALL ON" if g == 3 else "MUTE " + GROUPS[g], color="yellow", trigger=True),
                 col=g + 1, row=4, channel=CH, cc=48 + TRACKS + g) for g in range(4)],
    *[LayoutCell(Button("k%d" % i, "KILL %d" % (i + 1), color="red"),
                 col=(i % 4) + 1, row=5 + i // 4, channel=CH, cc=64 + i) for i in range(TRACKS)],
    *[LayoutCell(Button("kg%d" % g, "KILL ALL BUT T" if g == 3 else "KILL " + GROUPS[g], color="red"),
                 col=g + 1, row=8, channel=CH, cc=64 + TRACKS + g) for g in range(4)],
    *[LayoutCell(Button("r%d" % i, "RETRIG %d" % (i + 1), color="blue", trigger=True),
                 col=(i % 4) + 1, row=9 + i // 4, channel=CH, cc=90 + i) for i in range(TRACKS)],
    *[LayoutCell(Button("rg%d" % g, "RETRIG " + GROUPS[g], color="blue", trigger=True),
                 col=g + 1, row=12, channel=CH, cc=90 + TRACKS + g) for g in range(4)],
]


class SaggaMutes(ControllerBase):
    """SAGGA SEQ's 12 mutes, kills and RETRIG on channel 14."""

    NAME = "SAGGA Mutes"
    DESCRIPTION = "SAGGA SEQ (M-VAVE FM-1): mute, kill, retrigger the 12 tracks, on ch 14"
    AUTHOR = "SAGGA SEQ"
    VERSION = "0.31"
    HELP = """\
MUTE 1-12: a track's mute on / off (it waits for the QUANTISE if MUTE QUEUE is on in SAGGA SEQ). KILL 1-12: the track
is silent while the button is on, its notes stop at once. RETRIG 1-12: the track starts again from its first step on
its next step (the others go on). Under each, the GROUPS (0.31): DRUMS (the DRUM tracks), BASS (a BASS, SUB, RUMBLE or
LOG DRUM role), MELODIC (the others), ALL - MUTE a group (quiet if any of it plays, else back; ALL ON: every track
audible), KILL a group (ALL BUT T: every track but the tablet's, the one TRACK picks on SAGGA Live or Motori), RETRIG
a group. CC 48-63, 64-79 and 90-105 on MIDI channel 14; wire OUT to the FM-1."""

    params = [
        Radio("bg", "Background", ControllerBase.BG_OPTIONS, default="Wine", config_only=True),
        LayoutGrid("controller", "", cols=4, rows=12, labels_param="cell_labels", bindings_param="cell_bindings", cells=CELLS),
    ]

    cc_outputs = list(range(48, 64)) + list(range(64, 80)) + list(range(90, 106))
    outputs = ["CC 48-63, 64-79, 90-105 on ch 14: mutes, kills, RETRIG of SAGGA SEQ's tracks and groups"]

    TRIGGERS = frozenset(["m%d" % i for i in range(TRACKS)] + ["r%d" % i for i in range(TRACKS)] +
                         ["mg%d" % g for g in range(4)] + ["rg%d" % g for g in range(4)])

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
