# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA MOD - a RaspiMIDIHub controller for SAGGA SEQ 0.12: the LFOs, the CC lanes of the selected track, the THROWS
and VIAGGIO's knobs.

One LFO at a time (channel 13, CC 92: which), its ON / OFF (97), SHAPE (93), RATE (94), DEPTH (95), DEST (96). The six
lanes of the selected track: their base value (101-106), sent to the synth as you move them. The THROWS (108-111):
INTENSITY, GATE, SWING, FILTER thrown and springing back to 0 over a bar on their own. VIAGGIO: ENERGY (114), GENRE
(115), KEY (116), the HARMONY's progression (117) and state (118). The sixteen LFO switches L1-L16 (rows 9-12): each
is a note on channel 13 (100 + the LFO, note on = on, note off = off), all sixteen at hand at once; their CC 0 binding
is a placeholder the FM-1 ignores (the hub wants a CC on every cell).

Wire this plugin's OUT to the FM-1 (USB PORTS 2: its port 2); SAVE K2 on the FM-1 = REMOTE 13 + 14.
"""

from raspimidihub.controller_base import ControllerBase
from raspimidihub.plugin_api import Button, Fader, Knob, LayoutCell, LayoutGrid, Radio

CH13 = 12                                 # MIDI channel 13 (0-based)

LFO_LABELS = ["LFO %d" % (i + 1) for i in range(16)]
SHAPE_LABELS = ["SINE", "TRI", "RAMP+", "RAMP-", "SQUARE", "S&H", "SMOOTH", "DECAY"]
RATE_LABELS = ["16 BAR", "8 BAR", "4 BAR", "3 BAR", "2 BAR", "1.5 BAR", "1 BAR", "3/4 BAR",
               "1/2 BAR", "3/8 BAR", "1/4 BAR", "3/16", "1/8 BAR", "3/32", "1/16", "1/32",
               "1/4T", "1/8T", "1/16T", "1/32T"]                     # 0.13: the triplets (the FM-1's LFO RATE after 1/32)
DEST_LABELS = ["CC", "VEL", "GATE", "CHANCE", "TIMING", "SWING"]
GENRE_LABELS = ["TECHNO", "HARDTECHNO", "DUB TECHNO", "HOUSE", "UK GARAGE", "UK FUNKY", "GRIME", "DUBSTEP", "JUNGLE",
                "BASSLINE", "REGGAETON", "BATIDA", "GQOM", "EXPERIMENT", "ELECTRO", "DRUM+BASS", "AFRO HOUSE", "AMAPIANO",
                "FOOTWORK", "TRANCE", "UK DRILL", "HARDCORE", "PHONK", "BAILE FUNK",
                "MERENGUE"]
KEY_LABELS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PROG_LABELS = ["PROG %d" % (i + 1) for i in range(6)] + ["USER 1", "USER 2", "USER 3", "USER 4", "DICE/PI"]
HARM_LABELS = ["OFF", "ON", "LOCK"]


def hold(name, label, cc, col, row, color="yellow"):
    return LayoutCell(Button(name, label, color=color), col=col, row=row, channel=CH13, cc=cc)


def knob(name, label, cc, col, row, lo, hi, default, labels=None):
    return LayoutCell(Knob(name, label, min=lo, max=hi, default=default, labels=labels or []), col=col, row=row, channel=CH13, cc=cc)


def fader(name, label, cc, col, row, default=64):
    return LayoutCell(Fader(name, label, min=0, max=127, default=default), col=col, row=row, channel=CH13, cc=cc)


CELLS = [
    knob("lfo", "LFO", 92, 1, 1, 0, 15, 0, LFO_LABELS),
    hold("lfo_on", "LFO ON", 97, 2, 1, "green"),
    knob("shape", "SHAPE", 93, 3, 1, 0, 7, 0, SHAPE_LABELS),
    knob("rate", "RATE", 94, 4, 1, 0, len(RATE_LABELS) - 1, 6, RATE_LABELS),
    knob("depth", "DEPTH", 95, 1, 2, 0, 127, 64),
    knob("dest", "DEST", 96, 2, 2, 0, 5, 0, DEST_LABELS),

    *[fader("lane%d" % i, "LANE %d" % (i + 1), 101 + i, 1 + (i % 2) * 2, 3 + i // 2, 64) for i in range(6)],

    fader("th_int", "THROW INT", 108, 1, 6),
    fader("th_gate", "THROW GATE", 109, 3, 6),
    fader("th_swing", "THROW SWING", 110, 1, 7),
    fader("th_filt", "THROW FILTER", 111, 3, 7),

    knob("energy", "ENERGY", 114, 1, 8, 0, 127, 64),
    knob("genre", "GENRE", 115, 2, 8, 0, 23, 0, GENRE_LABELS),
    knob("key", "KEY", 116, 3, 8, 0, 11, 0, KEY_LABELS),
    knob("prog", "PROGRESSION", 117, 4, 8, 0, 10, 0, PROG_LABELS),
    knob("harm", "HARMONY", 118, 4, 2, 0, 2, 0, HARM_LABELS),

    *[LayoutCell(Button("lfo_sw%d" % i, "L%d" % (i + 1), color="green"), col=1 + i % 4, row=9 + i // 4, channel=CH13, cc=0) for i in range(16)],
]
for c in CELLS:
    if isinstance(c.param, Fader):
        c.span_cols = 2

LFO_SW_NOTE = 100                         # L1-L16: notes 100-115 on channel 13 (on = note on, off = note off)


class SaggaMod(ControllerBase):
    """SAGGA SEQ's modulation: an LFO, the selected track's lanes, the THROWS, VIAGGIO's knobs."""

    NAME = "SAGGA Mod"
    DESCRIPTION = "SAGGA SEQ (M-VAVE FM-1): the LFOs, the track's CC lanes, the THROWS that spring back, VIAGGIO's energy, genre, key, harmony"
    AUTHOR = "SAGGA SEQ"
    VERSION = "0.13"
    HELP = """\
LFO picks one of the sixteen (the one the FM-1 shows under LFO); LFO ON, SHAPE, RATE, DEPTH, DEST set it.
LANE 1-6: the base value of the selected track's CC lanes, sent to the synth as you move it (what the lane's steps
add rides on it). THROW INT / GATE / SWING / FILTER: the four macros as throws (64 = 0): move one and let it go, it
glides back to 0 within a bar on its own. ENERGY, GENRE, KEY: VIAGGIO's (queued at the phrase boundary while it
plays, at once when stopped); PROGRESSION and HARMONY (OFF, ON, LOCK): the harmony. L1-L16: the sixteen LFOs on / off,
all at hand (a switch is a note on channel 13: 100 + the LFO).
Channel 13: CC 92-97 the LFO, 101-106 the lanes, 108-111 the throws, 114-118 VIAGGIO and the harmony, notes 100-115 the
switches. The FM-1: SAVE K2 = REMOTE 13 + 14; wire OUT to it (USB PORTS 2: port 2)."""

    params = [
        Radio("bg", "Background", ControllerBase.BG_OPTIONS, default="Teal", config_only=True),
        LayoutGrid("controller", "", cols=4, rows=12, labels_param="cell_labels", bindings_param="cell_bindings", cells=CELLS),
    ]

    cc_outputs = sorted({c.cc for c in CELLS} - {0})
    outputs = ["CC and notes on ch 13: the LFOs, lanes, throws and VIAGGIO of SAGGA SEQ 0.12"]

    THROWS = ("th_int", "th_gate", "th_swing", "th_filt")

    def on_param_change(self, name, value):
        if name.startswith("lfo_sw"):                      # an LFO switch: a note, not the cell's CC
            n = int(name[6:])
            if value:
                self.send_note_on(CH13, LFO_SW_NOTE + n, 127)
            else:
                self.send_note_off(CH13, LFO_SW_NOTE + n)
            return
        super().on_param_change(name, value)
        if name in self.THROWS and value != 64:          # a throw: the FM-1 glides it back; the fader follows, back to the middle
            self.set_param(name, 64, persist=False)

    def panic(self):
        """the hub's PANIC: the LFO switch is let go; the knobs stay (a reset would move the FM-1's settings)"""
        if self.get_param("lfo_on"):
            b = self._effective_binding("lfo_on")
            if b is not None:
                self.send_cc(b["channel"], b["cc"], b.get("off", 0))
            self.set_param("lfo_on", False, persist=False)
