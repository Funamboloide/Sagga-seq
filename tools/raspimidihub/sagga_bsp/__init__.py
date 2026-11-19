# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA BEATSTEP - a RaspiMIDIHub plugin for SAGGA SEQ 0.20: an Arturia BeatStep Pro (in its CONTROL mode) as real
knobs and pads for the FM-1, through the Pi.

The 16 encoders are the knobs of SAGGA Live (channel 12, firmware/src/sagga_tablet.c) on the tablet's track: TRACK,
PATTERN, LENGTH, OCTAVE, SWING, GROOVE, ARP, CHORD (the first row), MIDI FX, FX AMOUNT, ALGO, A, B, C, PULSES,
ROTATION (the second). The pads 1-12 are the twelve MUTES (SAGGA REMOTE, channel 14 CC 48-59; 0.28: the FM-1 has
twelve tracks, pads 13-16 send nothing), or (PADS = ACTIONS) PLAY, FILL, FX GO, ALGO GO, COOK, BEAT, DICE, UNDO,
PROPOSAL, QUEUE, KEEP, BACK, RETRIG, MUTE, EUCLID, ECHO ALL.

Whatever the BeatStep Pro sends (its MIDI Control Center sets it), LEARN finds it: press LEARN, turn the 16 encoders
one after the other (top row left to right, then the bottom row), then tap the 16 pads in the same order. The hub
keeps what it learned.

Wiring in the hub's matrix: the BeatStep Pro to this plugin's IN; this plugin's OUT to the FM-1's port 2 ("Felucca
MIDI 2", with USB PORTS 2) or its only port; SAVE K2 on the FM-1 = REMOTE 13 + 14. The BeatStep Pro's CV / gate
outputs are a separate thing: the FM-1's port 1 to the BeatStep Pro (channels 1, 2 and 10) and it plays them.
"""

from dataclasses import dataclass

from raspimidihub.plugin_api import Button, Display, PluginBase, Radio

CH12, CH13, CH14 = 11, 12, 13          # MIDI channels 12, 13, 14 (0-based)
# the encoders: (label, channel, CC, lowest, highest) - SAGGA Live's knobs (tools/raspimidihub/sagga_live: the test
# checks they are the same)
ENCODERS = [
    ("TRACK", CH13, 112, 0, 11), ("PATTERN", CH12, 3, 0, 7), ("LENGTH", CH12, 4, 1, 64), ("OCTAVE", CH12, 5, 0, 6),
    ("SWING", CH12, 6, 50, 75), ("GROOVE", CH12, 7, 0, 9), ("ARP", CH12, 20, 0, 12), ("CHORD", CH12, 24, 0, 31),
    ("MIDI FX", CH12, 9, 0, 9), ("FX AMOUNT", CH12, 10, 0, 24), ("ALGO", CH12, 12, 0, 4), ("A", CH12, 13, 0, 127),
    ("B", CH12, 14, 0, 127), ("C", CH12, 15, 0, 127), ("PULSES", CH12, 17, 1, 64), ("ROTATION", CH12, 18, 0, 63),
]
# the pads as ACTIONS: (label, channel, CC, kind) - "tap": 127 then 0 (the FM-1 acts on the press); "hold": 127 while
# the pad is down; "switch": a state, each tap turns it over
ACTIONS = [
    ("PLAY", CH14, 20, "tap"), ("FILL", CH14, 23, "hold"), ("FX GO", CH12, 11, "tap"), ("ALGO GO", CH12, 16, "tap"),
    ("COOK", CH12, 26, "tap"), ("BEAT", CH12, 27, "tap"), ("DICE", CH12, 31, "tap"), ("UNDO", CH12, 32, "tap"),
    ("PROPOSAL", CH12, 28, "tap"), ("QUEUE", CH12, 29, "tap"), ("KEEP", CH14, 85, "tap"), ("BACK", CH14, 86, "tap"),
    ("RETRIG", CH12, 30, "tap"), ("MUTE", CH12, 1, "switch"), ("EUCLID", CH12, 19, "switch"), ("ECHO ALL", CH14, 118, "tap"),
]
MUTE_CC = 48                            # SAGGA REMOTE: mute track 1-12 = CC 48-59 on channel 14 (a press turns it over)
TRACKS = 12                             # 0.28: the FM-1's tracks (until 0.27: sixteen)
PAD_MODES = ["MUTE 1-12", "ACTIONS"]
ENC_MODES = ["ABSOLUTE", "RELATIVE"]
N = 16


@dataclass
class LearnMeter(Display):
    """the LEARN meter (how many of the 32 controls are known); map_param: the hub keeps what LEARN found there"""
    map_param: str = "bsp_map"

    def to_dict(self):
        d = super().to_dict()
        d["type"] = "display"
        return d


class SaggaBeatstep(PluginBase):
    """An Arturia BeatStep Pro as SAGGA SEQ's knobs and pads."""

    NAME = "SAGGA BeatStep"
    DESCRIPTION = "SAGGA SEQ (M-VAVE FM-1): a BeatStep Pro's 16 encoders and 16 pads as SAGGA Live's knobs, the mutes or the actions"
    AUTHOR = "SAGGA SEQ"
    VERSION = "0.28"
    HELP = """\
An Arturia BeatStep Pro in CONTROL mode as SAGGA SEQ's knobs: wire the BeatStep Pro to IN, OUT to the FM-1 (its port 2
with USB PORTS 2); SAVE K2 on the FM-1 = REMOTE 13 + 14.
LEARN: press it, turn the 16 encoders one after the other (top row left to right, then the bottom row), then tap the
16 pads in the same order. The meter counts them (32: done); the hub keeps the result.
ENCODERS (on the tablet's track, as SAGGA Live): TRACK, PATTERN, LENGTH, OCTAVE, SWING, GROOVE, ARP, CHORD / MIDI FX,
FX AMOUNT, ALGO, A, B, C, PULSES, ROTATION. ABSOLUTE: the encoder's value is the knob's place; RELATIVE: for encoders
set to send steps (65 and up: right, 63 and down: left).
PADS: MUTE 1-12 (pads 1-12 a track each; 13-16 nothing), or ACTIONS: PLAY, FILL (held), FX GO, ALGO GO, COOK, BEAT,
DICE, UNDO, PROPOSAL, QUEUE, KEEP, BACK, RETRIG, MUTE (the tablet's track), EUCLID, ECHO ALL."""

    params = [
        Radio("pads", "Pads", PAD_MODES, default="MUTE 1-12"),
        Radio("encoders", "Encoders", ENC_MODES, default="ABSOLUTE"),
        Button("learn", "LEARN", color="yellow", trigger=True),
        LearnMeter("learned", "Learned", display_name="learned"),
    ]
    display_outputs = [{"name": "learned", "type": "meter", "label": "LEARN", "min": 0, "max": 2 * N}]
    inputs = ["the BeatStep Pro (CONTROL mode): encoders and pads"]
    outputs = ["CC on ch 12, 13 and 14: SAGGA SEQ's tablet track, mutes, actions"]

    # ---- the map LEARN found: {"enc": [[ch, cc] or None] x 16, "pad": [["n" or "c", ch, num] or None] x 16}
    def _map(self):
        m = self.get_param("bsp_map")
        if not isinstance(m, dict) or len(m.get("enc") or []) != N or len(m.get("pad") or []) != N:
            m = {"enc": [None] * N, "pad": [None] * N}
        return m

    def on_start(self):
        if not isinstance(self.get_param("bsp_map"), dict):
            self.set_param("bsp_map", self._map(), persist=False)
        self._learning = -1                       # -1: not learning; 0..15 an encoder; 16..31 a pad
        self._pos = [None] * N                    # each encoder's value as last sent (RELATIVE: where it is)
        self._sent = [None] * N
        self._sw = [False] * N                    # ACTIONS: the switches' state (MUTE, EUCLID)
        self._show()

    def _st(self):                                # (a plugin made without on_start: the tests' stand-in)
        if not hasattr(self, "_learning"):
            self._learning, self._pos, self._sent, self._sw = -1, [None] * N, [None] * N, [False] * N

    def _show(self):
        m = self._map()
        n = sum(1 for x in m["enc"] if x) + sum(1 for x in m["pad"] if x)
        self.set_display("learned", n if self._learning < 0 else self._learning)

    def on_param_change(self, name, value):
        self._st()
        if name == "learn" and value:
            self._learning = 0
            self.set_param("bsp_map", {"enc": [None] * N, "pad": [None] * N}, persist=False)
            self.set_param("learn", False, persist=False)
            self._show()

    # ---- what comes in
    def _known(self, m, kind, ch, num):
        return any(e and kind == "c" and e[0] == ch and e[1] == num for e in m["enc"]) or \
            any(p and p[0] == kind and p[1] == ch and p[2] == num for p in m["pad"])

    def _learn(self, kind, ch, num):
        m = self._map()
        if self._known(m, kind, ch, num):
            return
        if self._learning < N:
            if kind != "c":
                return                            # (an encoder is a CC)
            m["enc"][self._learning] = [ch, num]
        else:
            m["pad"][self._learning - N] = [kind, ch, num]
        self._learning += 1
        if self._learning >= 2 * N:
            self._learning = -1
        self.set_param("bsp_map", m, persist=self._learning < 0)
        self._show()

    def on_cc(self, channel, cc, value):
        self._st()
        if self._learning >= 0:
            if value > 0 or self._learning < N:
                self._learn("c", channel, cc)
            return
        m = self._map()
        for i, e in enumerate(m["enc"]):
            if e and e[0] == channel and e[1] == cc:
                self._encoder(i, value)
                return
        for i, p in enumerate(m["pad"]):
            if p and p[0] == "c" and p[1] == channel and p[2] == cc:
                self._pad(i, value > 0)
                return

    def on_note_on(self, channel, note, velocity):
        self._st()
        if velocity <= 0:
            self.on_note_off(channel, note)
            return
        if self._learning >= 0:
            self._learn("n", channel, note)
            return
        for i, p in enumerate(self._map()["pad"]):
            if p and p[0] == "n" and p[1] == channel and p[2] == note:
                self._pad(i, True)
                return

    def on_note_off(self, channel, note):
        self._st()
        if self._learning >= 0:
            return
        for i, p in enumerate(self._map()["pad"]):
            if p and p[0] == "n" and p[1] == channel and p[2] == note:
                self._pad(i, False)
                return

    # ---- what goes out
    def _encoder(self, i, value):
        _, ch, cc, lo, hi = ENCODERS[i]
        if self.get_param("encoders") == "RELATIVE":    # 64 + n: n steps right, 64 - n: n steps left
            step = value - 64
            cur = self._pos[i] if self._pos[i] is not None else (lo + hi) // 2
            out = max(lo, min(hi, cur + step))
        else:
            out = lo + (max(0, min(127, value)) * (hi - lo) + 63) // 127
        self._pos[i] = out
        if out != self._sent[i]:
            self._sent[i] = out
            self.send_cc(ch, cc, out)

    def _pad(self, i, down):
        if self.get_param("pads") != "ACTIONS":
            if down and i < TRACKS:               # a mute: the press turns it over
                self.send_cc(CH14, MUTE_CC + i, 127)
                self.send_cc(CH14, MUTE_CC + i, 0)
            return
        _, ch, cc, kind = ACTIONS[i]
        if kind == "switch":
            if down:
                self._sw[i] = not self._sw[i]
                self.send_cc(ch, cc, 127 if self._sw[i] else 0)
        elif kind == "hold":
            self.send_cc(ch, cc, 127 if down else 0)
        elif down:
            self.send_cc(ch, cc, 127)
            self.send_cc(ch, cc, 0)

    def panic(self):
        """the hub's PANIC: a held FILL is let go; nothing else (the switches are the FM-1's states)"""
        if self.get_param("pads") == "ACTIONS":
            for i, (_, ch, cc, kind) in enumerate(ACTIONS):
                if kind == "hold":
                    self.send_cc(ch, cc, 0)
