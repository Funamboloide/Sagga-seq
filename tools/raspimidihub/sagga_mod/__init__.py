# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA MOD - a RaspiMIDIHub controller for SAGGA SEQ 0.12: the LFOs, the CC lanes of the tablet's track, the THROWS
and VIAGGIO's knobs.

One LFO at a time (channel 13, CC 92: which), its ON / OFF (97), SHAPE (93), RATE (94), DEPTH (95), DEST (96). The eight
lanes of the tablet's track (0.18: the track TRACK picks on SAGGA Live or Motori; before: the FM-1's selected one):
their base value, sent to the synth as you move them - lanes 1-6 on channel 13 CC 101-106, lanes 7 and 8 (0.28.1) on
channel 12 CC 62 / 63. The THROWS (108-111):
INTENSITY, GATE, SWING, FILTER thrown and springing back to 0 over a bar on their own. VIAGGIO: ENERGY (114), GENRE
(115), KEY (116), the HARMONY's progression (117) and state (118). The sixteen LFO switches L1-L16 (rows 10-13): each
is a note on channel 13 (100 + the LFO, note on = on, note off = off), all sixteen at hand at once; their CC 0 binding
is a placeholder the FM-1 ignores (the hub wants a CC on every cell).

Wire this plugin's OUT to the FM-1 (USB PORTS 2: its port 2); SAVE K2 on the FM-1 = REMOTE 13 + 14. 0.18: the FM-1's port 2
to this plugin's IN, and the knobs and switches follow the FM-1 (the tablet's LFO, its track's lanes, VIAGGIO).
"""

from raspimidihub.controller_base import ControllerBase
from raspimidihub.plugin_api import Button, Fader, Knob, LayoutCell, LayoutGrid, Radio

CH12, CH13 = 11, 12                       # MIDI channels 12 and 13 (0-based)

LFO_LABELS = ["LFO %d" % (i + 1) for i in range(16)]
SHAPE_LABELS = ["SINE", "TRI", "RAMP+", "RAMP-", "SQUARE", "S&H", "SMOOTH", "DECAY", "ENV"]   # 0.28.1: + ENV (the FM-1's since 0.20)
RATE_LABELS = ["16 BAR", "8 BAR", "4 BAR", "3 BAR", "2 BAR", "1.5 BAR", "1 BAR", "3/4 BAR",
               "1/2 BAR", "3/8 BAR", "1/4 BAR", "3/16", "1/8 BAR", "3/32", "1/16", "1/32",
               "1/4T", "1/8T", "1/16T", "1/32T"]                     # 0.13: the triplets (the FM-1's LFO RATE after 1/32)
DEST_LABELS = ["CC", "VEL", "GATE", "CHANCE", "TIMING", "SWING", "MOD ONLY"]          # 0.28.1: + MOD ONLY (the panel's since 0.20)
# 0.29: 22 (GRIME into DUBSTEP, BASSLINE into UK GARAGE, AMAPIANO into REGGAETON, AFRO HOUSE out, BALANI in)
GENRE_LABELS = ["TECHNO", "HARDTECHNO", "DUB TECHNO", "HOUSE", "UK GARAGE", "UK FUNKY", "DUBSTEP", "JUNGLE",
                "REGGAETON", "BATIDA", "GQOM", "EXPERIMENT", "ELECTRO", "DRUM+BASS", "BALANI",
                "FOOTWORK", "TRANCE", "UK DRILL", "HARDCORE", "PHONK", "BAILE FUNK",
                "MERENGUE"]
KEY_LABELS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# 0.29: the genre's eight (until 0.28: six), then the player's four and the Pi's - the FM-1's harm_prog 0..12
PROG_LABELS = ["PROG %d" % (i + 1) for i in range(8)] + ["USER 1", "USER 2", "USER 3", "USER 4", "DICE/PI"]
HARM_LABELS = ["OFF", "ON", "LOCK"]


def hold(name, label, cc, col, row, color="yellow"):
    return LayoutCell(Button(name, label, color=color), col=col, row=row, channel=CH13, cc=cc)


def knob(name, label, cc, col, row, lo, hi, default, labels=None):
    return LayoutCell(Knob(name, label, min=lo, max=hi, default=default, labels=labels or []), col=col, row=row, channel=CH13, cc=cc)


def fader(name, label, cc, col, row, default=64, ch=CH13):
    return LayoutCell(Fader(name, label, min=0, max=127, default=default), col=col, row=row, channel=ch, cc=cc)


# the lanes' base values: 1-6 on channel 13 CC 101-106; 0.28.1, lanes 7 and 8 on channel 12 CC 62 / 63 (channel 13 has
# one CC free, 119, and CC 98-100 do not come back to a MIDI 2.0 page)
LANES = [(CH13, 101 + i) for i in range(6)] + [(CH12, 62), (CH12, 63)]


CELLS = [
    knob("lfo", "LFO", 92, 1, 1, 0, 15, 0, LFO_LABELS),
    hold("lfo_on", "LFO ON", 97, 2, 1, "green"),
    knob("shape", "SHAPE", 93, 3, 1, 0, len(SHAPE_LABELS) - 1, 0, SHAPE_LABELS),
    knob("rate", "RATE", 94, 4, 1, 0, len(RATE_LABELS) - 1, 6, RATE_LABELS),
    knob("depth", "DEPTH", 95, 1, 2, 0, 127, 64),
    knob("dest", "DEST", 96, 2, 2, 0, len(DEST_LABELS) - 1, 0, DEST_LABELS),

    *[fader("lane%d" % i, "LANE %d" % (i + 1), LANES[i][1], 1 + (i % 2) * 2, 3 + i // 2, 64, LANES[i][0]) for i in range(8)],

    fader("th_int", "THROW INT", 108, 1, 7),
    fader("th_gate", "THROW GATE", 109, 3, 7),
    fader("th_swing", "THROW SWING", 110, 1, 8),
    fader("th_filt", "THROW FILTER", 111, 3, 8),

    knob("energy", "ENERGY", 114, 1, 9, 0, 127, 64),
    knob("genre", "GENRE", 115, 2, 9, 0, len(GENRE_LABELS) - 1, 0, GENRE_LABELS),
    knob("key", "KEY", 116, 3, 9, 0, 11, 0, KEY_LABELS),
    knob("prog", "PROGRESSION", 117, 4, 9, 0, len(PROG_LABELS) - 1, 0, PROG_LABELS),
    knob("harm", "HARMONY", 118, 4, 2, 0, 2, 0, HARM_LABELS),

    *[LayoutCell(Button("lfo_sw%d" % i, "L%d" % (i + 1), color="green"), col=1 + i % 4, row=10 + i // 4, channel=CH13, cc=0) for i in range(16)],
]
for c in CELLS:
    if isinstance(c.param, Fader):
        c.span_cols = 2

LFO_SW_NOTE = 100                         # L1-L16: notes 100-115 on channel 13 (on = note on, off = note off)


class SaggaMod(ControllerBase):
    """SAGGA SEQ's modulation: an LFO, the tablet's track's lanes, the THROWS, VIAGGIO's knobs."""

    NAME = "SAGGA Mod"
    DESCRIPTION = "SAGGA SEQ (M-VAVE FM-1): the LFOs, the track's CC lanes, the THROWS that spring back, VIAGGIO's energy, genre, key, harmony"
    AUTHOR = "SAGGA SEQ"
    VERSION = "0.29"
    HELP = """\
LFO picks one of the sixteen (the one the FM-1 shows under LFO); LFO ON, SHAPE (ENV: the envelope), RATE, DEPTH, DEST
(MOD ONLY: a source for the MOD MATRIX, it sends nothing) set it.
LANE 1-8: the base value of the CC lanes of the tablet's track (the one TRACK picks on SAGGA Live or Motori; the
FM-1's screen says TAB T5), sent to the synth as you move it (what the lane's steps add rides on it). THROW INT / GATE / SWING / FILTER: the four macros as throws (64 = 0): move one and let it go, it
glides back to 0 within a bar on its own. ENERGY, GENRE, KEY: VIAGGIO's (queued at the phrase boundary while it
plays, at once when stopped); PROGRESSION and HARMONY (OFF, ON, LOCK): the harmony. L1-L16: the sixteen LFOs on / off,
all at hand (a switch is a note on channel 13: 100 + the LFO).
Channel 13: CC 92-97 the LFO, 101-106 lanes 1-6, 108-111 the throws, 114-118 VIAGGIO and the harmony, notes 100-115 the
switches; channel 12: CC 62 / 63 lanes 7 and 8 (0.28.1: the FM-1 0.28.1 or later). The FM-1: SAVE K2 = REMOTE 13 + 14;
wire OUT to it (USB PORTS 2: port 2)."""

    params = [
        Radio("bg", "Background", ControllerBase.BG_OPTIONS, default="Teal", config_only=True),
        LayoutGrid("controller", "", cols=4, rows=13, labels_param="cell_labels", bindings_param="cell_bindings", cells=CELLS),
    ]

    cc_outputs = sorted({c.cc for c in CELLS} - {0})
    outputs = ["CC and notes on ch 13 (lanes 7 and 8: CC on ch 12): the LFOs, lanes, throws and VIAGGIO of SAGGA SEQ"]

    THROWS = ("th_int", "th_gate", "th_swing", "th_filt")

    def on_cc(self, channel, cc, value):
        """0.20.6: the FM-1 sends this cell's value back on channel 12 CC 36 (its own CC 101 is, in MIDI 2.0, part of an
        RPN / NRPN: RaspiMIDIHub 6's pages never get it from the FM-1 as a CC): taken as the cell's"""
        if channel == 11 and cc == 36:
            b = self._effective_binding('lane0')
            if b is not None:
                channel, cc = b["channel"], b["cc"]
        super().on_cc(channel, cc, value)

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

    def on_note_on(self, channel, note, velocity):
        """0.18: the FM-1 says which LFOs are on (notes 100-115 on channel 13, its port 2): the switches follow"""
        if channel == CH13 and LFO_SW_NOTE <= note < LFO_SW_NOTE + 16 and velocity > 0:
            self.set_param("lfo_sw%d" % (note - LFO_SW_NOTE), True, persist=False)
            return
        super().on_note_on(channel, note, velocity)

    def on_note_off(self, channel, note):
        if channel == CH13 and LFO_SW_NOTE <= note < LFO_SW_NOTE + 16:
            self.set_param("lfo_sw%d" % (note - LFO_SW_NOTE), False, persist=False)
            return
        super().on_note_off(channel, note)

    def panic(self):
        """the hub's PANIC: nothing here (0.20.9: LFO ON is the FM-1's state, as SAGGA Live's switches: a reset would
        switch the tablet's LFO off; the FM-1's own PANIC stops its notes)"""
        return
