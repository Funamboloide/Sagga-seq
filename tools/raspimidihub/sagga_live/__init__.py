# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA LIVE - a RaspiMIDIHub controller for SAGGA SEQ 0.18 - 0.20: the tablet's own track, while the FM-1 works on another.

The tablet has a track of its own on the FM-1 (TRACK, channel 13 CC 112, the same as SAGGA Motori's and Mod's): what
this page sends acts there, and the FM-1's screen says so ("TAB T5: ..."); the FM-1's track, page and cursor stay as
they are. Channel 12 (firmware/src/sagga_tablet.c): MUTE, SOLO, PATTERN, LENGTH, OCTAVE, RETRIG; SWING, GROOVE and its
amount, FOLLOW; the ARP (mode, octaves, rate, run) and the CHORD; the MIDI FX (one of the four - 0.20: of the nine -, its
amount, GO: 0.19, it joins the track's chain or leaves it); an ALGORITHM
(READY, A B C, GO); EUCLID (pulses, rotation, on / off); COOK, BEAT, a PROPOSAL and QUEUE (it enters at the
QUANTISE), DICE, KEEP / BACK, UNDO; the sixteen MUTES.

The FM-1 sends its values back (USB PORTS 2: on its port 2): turn a knob on the FM-1 and the knob here moves too.
Wire this plugin's OUT to the FM-1's port 2 and the FM-1's port 2 to this plugin's IN; SAVE K2 on the FM-1 = REMOTE 13 + 14.
"""

from raspimidihub.controller_base import ControllerBase
from raspimidihub.plugin_api import Button, Knob, LayoutCell, LayoutGrid, Radio

CH12 = 11                                 # MIDI channel 12 (0-based): the LIVE page
CH13 = 12                                 # channel 13: the tablet's track (CC 112) and its mode (113)
CH14 = 13                                 # channel 14: SAGGA REMOTE (KEEP / BACK of a dice)

TRACK_LABELS = ["T%d" % (i + 1) for i in range(16)]
MODE_LABELS = ["FREE", "IN KEY", "DRUM", "TAPE", "BREAK"]
PATTERN_LABELS = ["P%d" % (i + 1) for i in range(8)]
OCT_LABELS = ["-3", "-2", "-1", "0", "+1", "+2", "+3"]
GROOVE_LABELS = ["OFF", "HOUSE", "GARAGE", "DILLA", "AFRO", "SAMBA", "LAID BACK", "PUSH", "HUMAN", "TRAP"]
ARP_LABELS = ["BLOCK", "UP", "DOWN", "UP-DN", "DN-UP", "UP&DN", "CONV", "DIV", "RND", "WALK", "PLAYED", "THUMB", "PINKY"]
ARP_OCT_LABELS = ["", "X1", "X2", "X3"]
RATE_LABELS = ["1/4", "1/2", "ROLL", "1", "2", "3", "4"]       # the FM-1's knob order: a note every 4 / 2 steps .. 4 a step
RUN_LABELS = ["OFF", "RETRIG", "HOLD", "HOLD+RT"]
CHORD_LABELS = ["OFF", "OCTAVE", "POWER", "5-8", "MAJOR", "MINOR", "DIM", "AUG", "SUS2", "SUS4",
                "MAJ6", "MIN6", "DOM7", "MIN7", "MAJ7", "MINMAJ7", "DIM7", "M7B5", "7SUS4", "ADD9", "MINADD9", "DOM9", "MIN9", "MAJ9",
                "9SUS4", "6/9", "MIN6/9", "MIN11", "DOM13", "SHELL7", "MINSHELL", "1-3-5-8"]
MFX_LABELS = ["OFF", "HARM", "OCTAVE", "ECHO", "VEL CURVE", "CHANCE", "RANDOM", "NOTE FILTER", "GATE", "GLITCH"]   # 0.20: nine
MFX_AMT_LABELS = ["%+d" % (i - 12) if i != 12 else "0" for i in range(25)]
ALGO_LABELS = ["OFF", "TURING", "CELL", "ACCENT", "DENSITY"]


def tap(name, label, cc, col, row, color="green", ch=CH12):
    return LayoutCell(Button(name, label, color=color, trigger=True), col=col, row=row, channel=ch, cc=cc)


def switch(name, label, cc, col, row, color="red"):
    return LayoutCell(Button(name, label, color=color), col=col, row=row, channel=CH12, cc=cc)


def knob(name, label, cc, col, row, lo, hi, default, labels=None, ch=CH12):
    return LayoutCell(Knob(name, label, min=lo, max=hi, default=default, labels=labels or []), col=col, row=row, channel=ch, cc=cc)


CELLS = [
    knob("track", "TRACK", 112, 1, 1, 0, 15, 0, TRACK_LABELS, ch=CH13),
    knob("mode", "MODE", 113, 2, 1, 0, 4, 0, MODE_LABELS, ch=CH13),
    switch("mute", "MUTE", 1, 3, 1),
    switch("solo", "SOLO", 2, 4, 1, "yellow"),

    knob("pattern", "PATTERN", 3, 1, 2, 0, 7, 0, PATTERN_LABELS),
    knob("length", "LENGTH", 4, 2, 2, 1, 64, 16),
    knob("octave", "OCTAVE", 5, 3, 2, 0, 6, 3, OCT_LABELS),
    tap("retrig", "RETRIG", 30, 4, 2, "blue"),

    knob("swing", "SWING", 6, 1, 3, 50, 75, 50),
    knob("groove", "GROOVE", 7, 2, 3, 0, 9, 0, GROOVE_LABELS),
    knob("groove_amt", "GROOVE AMT", 8, 3, 3, 0, 100, 100),
    switch("follow", "FOLLOW", 25, 4, 3, "blue"),

    knob("arp", "ARP", 20, 1, 4, 0, 12, 0, ARP_LABELS),
    knob("arp_oct", "OCTAVES", 21, 2, 4, 1, 3, 1, ARP_OCT_LABELS),
    knob("arp_rate", "RATE", 22, 3, 4, 0, 6, 3, RATE_LABELS),
    knob("arp_run", "RUN", 23, 4, 4, 0, 3, 0, RUN_LABELS),

    knob("chord", "CHORD", 24, 1, 5, 0, 31, 0, CHORD_LABELS),
    knob("mfx", "MIDI FX", 9, 2, 5, 0, 9, 0, MFX_LABELS),
    knob("mfx_amt", "FX AMOUNT", 10, 3, 5, 0, 24, 12, MFX_AMT_LABELS),
    tap("mfx_go", "FX GO", 11, 4, 5, "yellow"),

    knob("algo", "ALGO", 12, 1, 6, 0, 4, 0, ALGO_LABELS),
    knob("algo_a", "A", 13, 2, 6, 0, 127, 64),
    knob("algo_b", "B", 14, 3, 6, 0, 127, 64),
    knob("algo_c", "C", 15, 4, 6, 0, 127, 0),

    tap("algo_go", "ALGO GO", 16, 1, 7, "yellow"),
    knob("euc_pulses", "PULSES", 17, 2, 7, 1, 64, 4),
    knob("euc_rot", "ROTATION", 18, 3, 7, 0, 63, 0),
    switch("euclid", "EUCLID", 19, 4, 7, "green"),

    tap("cook", "COOK", 26, 1, 8),
    tap("beat", "BEAT", 27, 2, 8),
    tap("proposal", "PROPOSAL", 28, 3, 8, "yellow"),
    tap("queue", "QUEUE", 29, 4, 8, "yellow"),

    tap("dice", "DICE", 31, 1, 9, "blue"),
    tap("keep", "KEEP", 85, 2, 9, "green", ch=CH14),
    tap("back", "BACK", 86, 3, 9, "red", ch=CH14),
    tap("undo", "UNDO", 32, 4, 9, "red"),

    *[switch("m%d" % t, "MUTE %d" % (t + 1), 40 + t, 1 + t % 4, 10 + t // 4) for t in range(16)],
]


class SaggaLive(ControllerBase):
    """SAGGA SEQ's tablet track: everything of one track at hand while the FM-1 works on another."""

    NAME = "SAGGA Live"
    DESCRIPTION = "SAGGA SEQ (M-VAVE FM-1): a track of the tablet's own - pattern, length, ARP, chord, MIDI FX, algorithm, euclid, cook, beat - and the 16 mutes"
    AUTHOR = "SAGGA SEQ"
    VERSION = "0.20"
    HELP = """\
TRACK picks the tablet's own track on the FM-1 (the FM-1 keeps its own: one hand there, one here); MODE is its mode.
MUTE, SOLO, PATTERN (at the QUANTISE), LENGTH (at the bar), OCTAVE, RETRIG; SWING, GROOVE, GROOVE AMT, FOLLOW (the
harmony); ARP, OCTAVES, RATE (1/4 and 1/2: a note every 4 / 2 steps), RUN; CHORD (one note becomes a chord); MIDI FX
(one of the nine with FM-1 0.20: HARM, OCTAVE, ECHO, VEL CURVE, CHANCE, RANDOM, NOTE FILTER, GATE, GLITCH), FX AMOUNT (the
four of 0.19: -12..+12; the new five: their whole range, the FM-1's screen says the value), FX GO (the effect shown
joins the track's chain - again: it leaves; on OFF: they all stop); ALGO (READY), A B C, ALGO GO; EUCLID's PULSES and ROTATION, EUCLID
on / off. COOK, BEAT, DICE (KEEP / BACK), UNDO on this track only; PROPOSAL writes a variation on a free pattern, QUEUE
sends it in. MUTE 1-16: every track.
The FM-1 sends its values back: wire OUT to the FM-1's port 2 and the FM-1's port 2 to IN (USB PORTS 2); SAVE K2 on
the FM-1 = REMOTE 13 + 14. Channel 12: CC 1-32, 40-55; channel 13: 112, 113; channel 14: 85, 86."""

    params = [
        Radio("bg", "Background", ControllerBase.BG_OPTIONS, default="Wine", config_only=True),
        LayoutGrid("controller", "", cols=4, rows=13, labels_param="cell_labels", bindings_param="cell_bindings", cells=CELLS),
    ]

    cc_outputs = sorted({c.cc for c in CELLS})
    outputs = ["CC on ch 12, 13 and 14: the tablet's track of SAGGA SEQ 0.18"]

    TRIGGERS = frozenset(c.param.name for c in CELLS if isinstance(c.param, Button) and c.param.trigger)

    def on_cc(self, channel, cc, value):
        """0.20.6: the FM-1 sends this cell's value back on channel 12 CC 33 (its own CC 6 is, in MIDI 2.0, part of an
        RPN / NRPN: RaspiMIDIHub 6's pages never get it from the FM-1 as a CC): taken as the cell's"""
        if channel == 11 and cc == 33:
            b = self._effective_binding('swing')
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
        """the hub's PANIC: nothing here (the switches are the FM-1's mutes, solo, EUCLID: a reset would change them;
        the FM-1's own PANIC stops its notes)"""
        return
