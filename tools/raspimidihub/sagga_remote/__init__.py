# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA REMOTE - a RaspiMIDIHub controller for SAGGA SEQ 0.8 on the M-VAVE FM-1.

A page of buttons, knobs and a fader in RaspiMIDIHub's web interface (the phone, full screen) that sends the
commands of SAGGA SEQ as Control Changes on MIDI channel 14 (docs/SAGGA-SEQ.md, "SAGGA REMOTE"). In the hub's
matrix: connect this plugin's OUT to the FM-1 (nothing else needs it). With USB PORTS 2 (the FM-1's USB page): to its
port 2 ("Felucca MIDI 2"), where the FM-1 listens for the remote then.

0.8: the SNAPSHOTS (1-8 recall at the QUANTISE moment, STORE 1-8), CC CAPTURE, SEND, PATCHES (the Pi keeps the
synths' patches), HARMONY on / off, the global ECHO, WRITE LIVE.

0.5.1: LOOP (a tap: it stays) and REPEAT (on while the button is on, it lands in time when you switch it off) share
their CC, as on the FM-1, where a tap is a LOOP and a hold is a REPEAT; EXIT, RESTART, STOP at the bar; the four
macros (INTENSITY, GATE, SWING, FILTER: 64 = 0) and TRANSPOSE (12 = 0).

Copy this folder next to the hub's own plugins (README in tools/raspimidihub) and restart the hub.
"""

from raspimidihub.controller_base import ControllerBase
from raspimidihub.plugin_api import Button, Fader, Knob, LayoutCell, LayoutGrid, Radio

CH = 13                                   # MIDI channel 14 (0-based), where the FM-1 listens for the remote

QUANT_LABELS = ["AUTO", "NOW", "BEAT", "BAR", "2 BAR", "4 BAR", "8 BAR"]
SCENE_LABELS = ["SC1", "SC2", "SC3", "SC4", "SC5", "SC6", "SC7", "SC8"]
TRANS_LABELS = ["%+d" % (i - 12) if i != 12 else "0" for i in range(25)]
LOOPS = [("4", "1/4", 24), ("8", "1/8", 25), ("16", "1/16", 26), ("32", "1/32", 27)]


def tap(name, label, cc, col, row, color="green"):
    """a button that acts when it is pressed (the FM-1 gets 127 then 0)"""
    return LayoutCell(Button(name, label, color=color, trigger=True), col=col, row=row, channel=CH, cc=cc)


def hold(name, label, cc, col, row, color="yellow"):
    """a button that is on until it is pressed again (FILL, REPEAT, TEMP: on = held)"""
    return LayoutCell(Button(name, label, color=color), col=col, row=row, channel=CH, cc=cc)


def knob(name, label, cc, col, row, lo=0, hi=127, default=64, labels=None):
    return LayoutCell(Knob(name, label, min=lo, max=hi, default=default, labels=labels or []), col=col, row=row, channel=CH, cc=cc)


CELLS = [
    tap("play", "PLAY/STOP", 20, 1, 1),
    tap("cont", "CONTINUE", 21, 2, 1),
    tap("stopbar", "STOP @BAR", 87, 3, 1, "red"),
    tap("restart", "RESTART", 88, 4, 1, "yellow"),

    hold("fill", "FILL", 23, 1, 2, "blue"),
    tap("reload", "RELOAD", 22, 2, 2, "yellow"),
    hold("temp", "TEMP", 37, 3, 2, "red"),
    tap("panic", "PANIC", 38, 4, 2, "red"),

    *[tap("loop" + n, "LOOP " + lab, cc, i + 1, 3) for i, (n, lab, cc) in enumerate(LOOPS)],
    *[hold("rep" + n, "REP " + lab, cc, i + 1, 4) for i, (n, lab, cc) in enumerate(LOOPS)],

    tap("exit", "EXIT LOOP", 89, 1, 5, "yellow"),
    tap("undo", "UNDO", 36, 2, 5, "yellow"),
    tap("dice_keep", "KEEP DICE", 85, 3, 5),
    tap("muteq", "MUTE QUEUE", 39, 4, 5, "yellow"),

    tap("scdn", "SCENE -", 28, 1, 6, "blue"),
    tap("scup", "SCENE +", 29, 2, 6, "blue"),
    tap("evolve", "EVOLVE", 33, 3, 6),
    tap("freeze", "FREEZE", 34, 4, 6),

    *[tap("sc%d" % i, "SCENE %d" % (i + 1), 40 + i, (i % 4) + 1, 7 + i // 4, "blue") for i in range(8)],

    LayoutCell(Fader("morph", "MORPH", min=0, max=127, default=0), col=1, row=9, span_cols=3, channel=CH, cc=1),
    knob("morph_to", "MORPH TO", 2, 4, 9, 0, 7, 1, SCENE_LABELS),

    knob("intensity", "INTENSITY", 7, 1, 10),
    knob("gate", "GATE", 8, 2, 10),
    knob("swing", "SWING", 9, 3, 10),
    knob("filter", "FILTER", 10, 4, 10),

    knob("transpose", "TRANSPOSE", 11, 1, 11, 0, 24, 12, TRANS_LABELS),
    knob("quant", "QUANTISE", 6, 2, 11, 0, 6, 0, QUANT_LABELS),
    knob("evo_amt", "EVOLVE AMT", 4, 3, 11, default=32),
    knob("heat", "HEAT", 5, 4, 11, default=50),

    tap("bpm_dn", "TEMPO -1", 30, 1, 12),
    tap("bpm_up", "TEMPO +1", 31, 2, 12),
    tap("taptempo", "TAP", 32, 3, 12),
    tap("revert", "REVERT", 35, 4, 12),

    *[tap("snap%d" % i, "SNAP %d" % (i + 1), 106 + i, (i % 4) + 1, 13 + i // 4, "green") for i in range(8)],
    *[tap("store%d" % i, "STORE %d" % (i + 1), 12 + i, (i % 4) + 1, 15 + i // 4, "red") for i in range(8)],
    tap("capture", "CC CAPTURE", 114, 1, 17, "yellow"),
    tap("snd", "SEND SOUND", 115, 2, 17, "yellow"),
    tap("patches", "PATCHES", 116, 3, 17, "yellow"),
    tap("harmony", "HARMONY", 117, 4, 17, "blue"),
    tap("echo", "ECHO", 118, 1, 18, "blue"),
    tap("write", "WRITE LIVE", 119, 2, 18, "red"),
    LayoutCell(Button("take", "TAKE", color="red", trigger=True), col=3, row=18, channel=12, cc=107),   # 0.12: on channel 13
]


class SaggaRemote(ControllerBase):
    """SAGGA SEQ's live commands on channel 14."""

    NAME = "SAGGA Remote"
    DESCRIPTION = "SAGGA SEQ (M-VAVE FM-1): transport, LOOP / REPEAT, scenes, snapshots, MORPH, macros, TRANSPOSE on ch 14"
    AUTHOR = "SAGGA SEQ"
    VERSION = "0.12"
    HELP = """\
The live commands of SAGGA SEQ 0.8 on the M-VAVE FM-1, as Control Changes on MIDI channel 14. Wire this plugin's
OUT to the FM-1 in the matrix (with USB PORTS 2: to its port 2, "Felucca MIDI 2").

PLAY/STOP, CONTINUE, STOP @BAR (the end of the bar; again: no), RESTART (every track from step 1 at the QUANTISE
moment). FILL and TEMP are on until you press them again (on = held); RELOAD, PANIC.
LOOP 1/4 .. 1/32: a loop that stays (the same LOOP again, or EXIT LOOP: off). REP 1/4 .. 1/32: the same CC held: a
REPEAT while the button is on; switch it off and the music lands where it would have been.
UNDO (a dice waiting: back), KEEP DICE, MUTE QUEUE. SCENE - / + and 1-8 (QUANTISE decides when), EVOLVE, FREEZE,
REVERT. MORPH glides the CC values from the scene playing to MORPH TO.
The macros act on every track (64 = 0): INTENSITY (velocity), GATE, SWING, FILTER (the CC lane 1 of every track).
TRANSPOSE moves the key (the tracks in key), 0 in the middle, at the QUANTISE moment. QUANTISE, EVOLVE AMT, HEAT.
TEMPO -1 / +1, TAP.
SNAP 1-8: a snapshot comes back (at the QUANTISE moment); STORE 1-8 keeps what plays now in it. CC CAPTURE: the CCs
your synths send go into the snapshot playing (again: off). SEND SOUND: its CC values out again. PATCHES: the Pi keeps
the synths' patches for it (patches.json on the Pi). HARMONY on / off, ECHO (every track), WRITE LIVE (what the live
EUCLID and algorithms play goes into the patterns). TAKE (0.12, channel 13): what was played on the keys or the pads
in the last loop of the selected track goes into its pattern.

The tracks' mutes, kills and RETRIG are in the SAGGA Mutes plugin; 0.12 adds SAGGA Motori (the tracks as engines),
SAGGA Break (the slices of a drum break) and SAGGA Mod (LFOs, lanes, throws, VIAGGIO)."""

    params = [
        Radio("bg", "Background", ControllerBase.BG_OPTIONS, default="Slate", config_only=True),
        LayoutGrid("controller", "", cols=4, rows=18, labels_param="cell_labels", bindings_param="cell_bindings", cells=CELLS),
    ]

    cc_outputs = sorted({c.cc for c in CELLS})
    outputs = ["CC on ch 14 (TAKE on ch 13): the commands of SAGGA SEQ 0.12"]

    TRIGGERS = frozenset(c.param.name for c in CELLS if isinstance(c.param, Button) and c.param.trigger)

    def on_cc(self, channel, cc, value):
        """0.20.6: the FM-1 sends this cell's value back on channel 12 CC 34 (its own CC 6 is, in MIDI 2.0, part of an
        RPN / NRPN: RaspiMIDIHub 6's pages never get it from the FM-1 as a CC): taken as the cell's"""
        if channel == 11 and cc == 34:
            b = self._effective_binding('quant')
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
        """the hub's PANIC: what is held is let go (FILL, REPEAT, TEMP, KILL); the knobs stay where they are (a reset
        would change the FM-1's settings: QUANTISE, MORPH ...)"""
        for cell in CELLS:
            name = cell.param.name
            if isinstance(cell.param, Button) and name not in self.TRIGGERS and self.get_param(name):
                b = self._effective_binding(name)
                if b is not None:
                    self.send_cc(b["channel"], b["cc"], b.get("off", 0))
                self.set_param(name, False, persist=False)
