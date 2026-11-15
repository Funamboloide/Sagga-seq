#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The RaspiMIDIHub plugins of SAGGA SEQ (tools/raspimidihub): loaded by the hub's own plugin host, driven through the
hub's own test harness. Needs a checkout of RaspiMIDIHub (github.com/wamdam/raspimidihub):

    RMH=/path/to/raspimidihub python3 tests/sagga_plugin_tests.py      (skipped without RMH)
"""
import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RMH = os.environ.get("RMH")
N, FAILS = [0], []


def check(cond, what):
    N[0] += 1
    if not cond:
        FAILS.append(what)
        print("  FAIL:", what)


# the FM-1's remote map (docs/SAGGA-SEQ.md): what a plugin may send. Channel 14 (SAGGA REMOTE), channel 13 (VIAGGIO's
# CC 1-32, and 0.12's CC 33 and up: firmware/src/sagga_remote2.c)
CH14_CCS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11} | set(range(12, 20)) | set(range(20, 48)) | set(range(48, 64)) | set(range(64, 80)) | \
           set(range(80, 85)) | {85, 86, 87, 88, 89} | set(range(90, 106)) | set(range(106, 114)) | set(range(114, 120))
CH13_CCS = set(range(1, 33)) | set(range(33, 49)) | set(range(49, 65)) | set(range(65, 76)) | set(range(76, 92)) | set(range(92, 98)) | \
           set(range(101, 107)) | set(range(107, 119))
CH12_CCS = set(range(1, 33)) | set(range(40, 56))                      # 0.18: the LIVE page (sagga_tablet.c)
PLUGINS = ("sagga_remote", "sagga_mutes", "sagga_motori", "sagga_break", "sagga_mod", "sagga_live")


def stub_hub():
    """a stand-in for the hub's plugin API, enough to load the plugins and press their cells (no RMH checkout)"""
    import types
    from dataclasses import dataclass, field

    @dataclass
    class Param:
        name: str
        label: str = ""

    @dataclass
    class Button(Param):
        default: bool = False
        color: str = "green"
        trigger: bool = False
        mini: bool = False

    @dataclass
    class Knob(Param):
        min: int = 0
        max: int = 127
        default: int = 0
        labels: list = field(default_factory=list)

    @dataclass
    class Fader(Param):
        min: int = 0
        max: int = 127
        default: int = 0
        vertical: bool = False

    @dataclass
    class Radio(Param):
        options: list = field(default_factory=list)
        default: str = ""
        config_only: bool = False

    @dataclass
    class LayoutCell:
        param: object
        col: int = 1
        row: int = 1
        span_cols: int = 1
        span_rows: int = 1
        channel: int = None
        cc: int = None

    @dataclass
    class LayoutGrid(Param):
        cols: int = 8
        rows: int = 4
        cells: list = field(default_factory=list)
        labels_param: str = None
        bindings_param: str = None

    class ControllerBase:
        BG_OPTIONS = ["Default", "Navy", "Forest", "Wine", "Plum", "Teal", "Sienna", "Slate"]

        def __init__(self):
            self.ccs = []
            self._values = {}
            self._cells = {c.param.name: c for p in self.params if isinstance(p, LayoutGrid) for c in p.cells}

        def send_cc(self, ch, cc, v): self.ccs.append((ch, cc, v))
        def send_note_on(self, ch, note, vel): self.ccs.append(("on", ch, note, vel))
        def send_note_off(self, ch, note): self.ccs.append(("off", ch, note))
        def set_param(self, name, value, persist=True): self._values[name] = value
        def get_param(self, name): return self._values.get(name, getattr(self._cells[name].param, "default", False))

        def _effective_binding(self, name):
            c = self._cells.get(name)
            if c is None or c.cc is None:
                return None
            return {"channel": c.channel, "cc": c.cc, "on": 127, "off": 0}

        def on_param_change(self, name, value):     # the hub: the cell's value as a CC byte
            b = self._effective_binding(name)
            if b is None:
                return
            self._values[name] = value
            p = self._cells[name].param
            if isinstance(p, Button):
                self.send_cc(b["channel"], b["cc"], b["on"] if value else b["off"])
            else:
                self.send_cc(b["channel"], b["cc"], max(0, min(127, int(value))))

    @dataclass
    class Display(Param):
        display_name: str = ""

        def to_dict(self):
            return {"type": "display", "name": self.name, "display_name": self.display_name}

    class PluginBase:                                  # 0.20: a plain plugin (SAGGA BeatStep)
        params = []

        def __init__(self):
            self.ccs, self.displays = [], {}
            self._param_values = {p.name: p.default for p in self.params if hasattr(p, "default")}

        def get_param(self, name): return self._param_values.get(name)
        def set_param(self, name, value, persist=True): self._param_values[name] = value
        def set_display(self, name, value): self.displays[name] = value
        def send_cc(self, ch, cc, v): self.ccs.append((ch, cc, v))

    api = types.ModuleType("raspimidihub.plugin_api")
    for k in ("Button", "Knob", "Fader", "Radio", "LayoutCell", "LayoutGrid", "Param", "Display", "PluginBase"):
        setattr(api, k, locals()[k])
    base = types.ModuleType("raspimidihub.controller_base")
    base.ControllerBase = ControllerBase
    pkg = types.ModuleType("raspimidihub")
    pkg.plugin_api, pkg.controller_base = api, base
    sys.modules["raspimidihub"], sys.modules["raspimidihub.plugin_api"], sys.modules["raspimidihub.controller_base"] = pkg, api, base


def load_plugin(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", "raspimidihub", name, "__init__.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    cls = [v for v in vars(m).values() if isinstance(v, type) and v.__name__.startswith("Sagga")][0]
    return m, cls


def structural():
    """every plugin, with the stub: its cells fit its grid, every CC is one the FM-1 answers on that channel, a trigger
    presses and lets go, a held button stays, PANIC lets the held ones go, the 0.12 pages' names and channels"""
    stub_hub()
    for name in PLUGINS:
        m, cls = load_plugin(name)
        grid = [p for p in cls.params if p.__class__.__name__ == "LayoutGrid"][0]
        cells = grid.cells
        names = [c.param.name for c in cells]
        check(len(names) == len(set(names)), "%s: every cell its own name" % name)
        pos = [(c.col + dx, c.row + dy) for c in cells for dx in range(c.span_cols) for dy in range(c.span_rows)]
        check(len(pos) == len(set(pos)) and all(1 <= x <= grid.cols and 1 <= y <= grid.rows for x, y in pos), "%s: the cells fit the grid, none on another" % name)
        bad = [(c.param.name, c.channel, c.cc) for c in cells if not ((c.channel == 13 and c.cc in CH14_CCS) or (c.channel == 12 and c.cc in CH13_CCS)
                                                                        or (c.channel == 11 and c.cc in CH12_CCS and name == "sagga_live")
                                                                        or (c.channel == 12 and c.cc == 0 and c.param.name.startswith("lfo_sw")))]   # (the LFO switches send notes)
        check(not bad, "%s: every cell a CC the FM-1 answers on channel 13 or 14 (%s)" % (name, bad[:4]))
        check(cls.VERSION in ("0.8", "0.12", "0.13", "0.18", "0.20") and cls.NAME.startswith("SAGGA ") and len(cls.HELP) > 100, "%s: name, version, help" % name)
        p = cls()
        trig = [c for c in cells if c.param.__class__.__name__ == "Button" and c.param.trigger]
        if trig:
            c = trig[0]
            p.on_param_change(c.param.name, True)
            check(p.ccs == [(c.channel, c.cc, 127), (c.channel, c.cc, 0)] and p.get_param(c.param.name) is False, "%s: a trigger presses and lets go (%s)" % (name, p.ccs))
        held = [c for c in cells if c.param.__class__.__name__ == "Button" and not c.param.trigger]
        if held and name == "sagga_live":                  # 0.18: its switches are the FM-1's states: PANIC leaves them
            c = held[0]
            p.ccs = []
            p.on_param_change(c.param.name, True)
            p.panic()
            check(p.ccs == [(c.channel, c.cc, 127)], "%s: PANIC leaves the switches (%s)" % (name, p.ccs))
        elif held:
            c = held[0]
            p.ccs = []
            p.on_param_change(c.param.name, True)
            p.panic()
            check(p.ccs == [(c.channel, c.cc, 127), (c.channel, c.cc, 0)] and p.get_param(c.param.name) is False, "%s: a held button stays until PANIC lets it go (%s)" % (name, p.ccs))
    # 0.12: the pages speak on channel 13 (0-based 12) where the firmware's new commands are
    for name, ccs in (("sagga_motori", {33, 48, 49, 64, 112, 113, 69}), ("sagga_break", set(range(76, 92)) | {65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 107}),
                      ("sagga_mod", {92, 93, 94, 95, 96, 97, 101, 106, 108, 111, 114, 115, 116, 117, 118})):
        m, cls = load_plugin(name)
        got = {c.cc for p in cls.params if p.__class__.__name__ == "LayoutGrid" for c in p.cells if c.channel == 12}
        check(ccs <= got, "%s: the channel 13 commands it needs (%s missing)" % (name, sorted(ccs - got)))
    m, cls = load_plugin("sagga_break")
    p = cls()
    p.on_param_change("s4", True)
    check(p.ccs == [(12, 80, 127), (12, 80, 0)], "SAGGA Break: pad 5 = CC 80 on channel 13, pressed then let go (%s)" % p.ccs)
    m, cls = load_plugin("sagga_mod")
    p = cls()
    p.on_param_change("th_int", 100)
    check(p.ccs == [(12, 108, 100)] and p.get_param("th_int") == 64, "SAGGA Mod: a throw sends its value and the fader goes back to the middle (%s)" % p.ccs)
    p.ccs = []
    p.on_param_change("lfo_sw0", True); p.on_param_change("lfo_sw15", True); p.on_param_change("lfo_sw0", False)
    check(p.ccs == [("on", 12, 100, 127), ("on", 12, 115, 127), ("off", 12, 100)], "SAGGA Mod: L1 and L16 on, L1 off = notes 100 / 115 on channel 13 (%s)" % p.ccs)
    sw = [c for p2 in cls.params if p2.__class__.__name__ == "LayoutGrid" for c in p2.cells if c.param.name.startswith("lfo_sw")]
    check(len(sw) == 16 and all(c.row >= 9 for c in sw), "SAGGA Mod: sixteen switches on rows 9-12")
    src = open(os.path.join(ROOT, "firmware", "src", "dinghy.c")).read()
    i = src.index("static const char *lfo_rate_name")
    fw = re.findall(r'"([^"]+)"', src[i:src.index("};", i)])
    check(m.RATE_LABELS == fw and len(fw) == 20, "SAGGA Mod: RATE has the FM-1's twenty rates, the triplets last (%s)" % m.RATE_LABELS[-4:])
    rk = [c for p2 in cls.params if p2.__class__.__name__ == "LayoutGrid" for c in p2.cells if c.param.name == "rate"]
    check(rk and rk[0].param.max == 19, "SAGGA Mod: the RATE knob goes to 19 (%s)" % (rk[0].param.max if rk else rk))
    m, cls = load_plugin("sagga_motori")
    p = cls()
    p.on_param_change("p3", 5)
    p.on_param_change("l0", 32)
    p.on_param_change("m1", True)
    check(p.ccs == [(12, 36, 5), (12, 49, 32), (13, 49, 127), (13, 49, 0)], "SAGGA Motori: track 4 pattern 6 (ch 13 CC 36), track 1 length 32, MUTE 2 on ch 14 (%s)" % p.ccs)
    m, cls = load_plugin("sagga_live")
    p = cls()
    p.on_param_change("track", 4); p.on_param_change("pattern", 2); p.on_param_change("m3", True); p.on_param_change("cook", True)
    p.on_param_change("arp_rate", 0); p.on_param_change("keep", True)
    check(p.ccs == [(12, 112, 4), (11, 3, 2), (11, 43, 127), (11, 26, 127), (11, 26, 0), (11, 22, 0), (13, 85, 127), (13, 85, 0)],
          "SAGGA Live: TRACK 5 (ch 13), PATTERN 3, MUTE 4, COOK, RATE 1/4 on ch 12, KEEP on ch 14 (%s)" % p.ccs)
    cells = [c for p2 in cls.params if p2.__class__.__name__ == "LayoutGrid" for c in p2.cells]
    keys = [(c.channel, c.cc) for c in cells]
    check(len(keys) == len(set(keys)), "SAGGA Live: every cell its own channel and CC (the FM-1's values come back to one)")
    fwsrc = open(os.path.join(ROOT, "firmware", "src", "sagga_tablet.c")).read()
    fb = set((int(a.replace("TB_CH", "11")), int(b)) for a, b in re.findall(r"\{(TB_CH|\d+), (\d+), (?:0|FBF_SCALED)\}", fwsrc))
    knobs = {(c.channel, c.cc) for c in cells if c.param.__class__.__name__ == "Knob" or (c.param.__class__.__name__ == "Button" and not c.param.trigger)}
    check(knobs - fb <= {(11, cc) for cc in range(40, 56)}, "SAGGA Live: every knob and switch gets the FM-1's value back (%s missing)" % sorted(knobs - fb - {(11, cc) for cc in range(40, 56)}))
    d = {c.param.name: c.param for c in cells}
    src = open(os.path.join(ROOT, "firmware", "src", "dinghy.c")).read()
    i = src.index("static const char *chord_name")
    check(m.ARP_LABELS == re.findall(r'"([^"]+)"', src[i:src.index("};", i)]), "SAGGA Live: ARP names as the FM-1's")
    core = open(os.path.join(ROOT, "firmware", "src", "sagga_seq_core.c")).read()
    i = core.index("const char *sq_chord_shape_name")
    check(m.CHORD_LABELS == re.findall(r'"([^"]+)"', core[i:core.index("};", i)]) and d["chord"].max == 31, "SAGGA Live: the 32 CHORD shapes as the FM-1's")
    i = core.index("GROOVE_NAME[SQ_GROOVES]")
    check(m.GROOVE_LABELS == re.findall(r'"([^"]+)"', core[i:core.index("};", i)]), "SAGGA Live: GROOVE names as the FM-1's")
    check(m.RATE_LABELS == ["1/4", "1/2", "ROLL", "1", "2", "3", "4"] and d["arp_rate"].max == 6, "SAGGA Live: RATE in the FM-1's knob order")
    m, cls = load_plugin("sagga_mod")
    g = [c for p2 in cls.params if p2.__class__.__name__ == "LayoutGrid" for c in p2.cells if c.param.name == "genre"][0]
    check(g.param.max == 24 and m.GENRE_LABELS[24] == "MERENGUE", "SAGGA Mod: GENRE reaches MERENGUE (25 genres)")
    for k in [k for k in list(sys.modules) if k.startswith("raspimidihub")]:
        del sys.modules[k]


def bsp_learn(p):
    """LEARN: the 16 encoders (CC 10-25 on channel 1, each sent twice: the second is not a new one), then the 16 pads
    (notes 36-51 on channel 10)"""
    p.on_param_change("learn", True)
    for i in range(16):
        p.on_cc(0, 10 + i, 60); p.on_cc(0, 10 + i, 61)
    for i in range(16):
        p.on_note_on(9, 36 + i, 100); p.on_note_off(9, 36 + i)


def bsp_tests():
    """0.20 SAGGA BeatStep: its encoders are SAGGA Live's knobs, its actions commands the FM-1 answers; LEARN, then the
    encoders (ABSOLUTE, RELATIVE) and the pads (MUTE 1-16, ACTIONS)"""
    stub_hub()
    m, cls = load_plugin("sagga_bsp")
    ml, lcls = load_plugin("sagga_live")
    knobs = {c.param.label: (c.channel, c.cc, c.param.min, c.param.max) for p2 in lcls.params if p2.__class__.__name__ == "LayoutGrid"
             for c in p2.cells if c.param.__class__.__name__ == "Knob"}
    check(len(m.ENCODERS) == 16 and all(knobs.get(lab) == (ch, cc, lo, hi) for lab, ch, cc, lo, hi in m.ENCODERS),
          "SAGGA BeatStep: the 16 encoders are SAGGA Live's knobs (%s)" % [e for e in m.ENCODERS if knobs.get(e[0]) != e[1:]])
    bad = [a for a in m.ACTIONS if not ((a[1] == 11 and a[2] in CH12_CCS) or (a[1] == 13 and a[2] in CH14_CCS) or (a[1] == 12 and a[2] in CH13_CCS))]
    check(len(m.ACTIONS) == 16 and not bad, "SAGGA BeatStep: every action a command the FM-1 answers (%s)" % bad)
    check(cls.VERSION == "0.20" and cls.NAME == "SAGGA BeatStep" and len(cls.HELP) > 100, "SAGGA BeatStep: name, version, help")
    p = cls()
    p.on_start()
    bsp_learn(p)
    mp = p.get_param("bsp_map")
    check(mp["enc"][0] == [0, 10] and mp["enc"][15] == [0, 25] and mp["pad"][0] == ["n", 9, 36] and mp["pad"][15] == ["n", 9, 51] and p.displays.get("learned") == 32,
          "SAGGA BeatStep: LEARN finds the 16 encoders, then the 16 pads (%s %s)" % (mp, p.displays))
    p.ccs = []
    p.on_cc(0, 10, 127); p.on_cc(0, 11, 0); p.on_cc(0, 11, 1); p.on_cc(0, 18, 64)
    p.on_note_on(9, 40, 100); p.on_note_off(9, 40)
    check(p.ccs == [(12, 112, 15), (11, 3, 0), (11, 9, 5), (13, 52, 127), (13, 52, 0)],
          "SAGGA BeatStep: TRACK 16, PATTERN 1 (once), MIDI FX halfway, pad 5 = MUTE 5 (%s)" % p.ccs)
    p.set_param("pads", "ACTIONS"); p.set_param("encoders", "RELATIVE")
    p.ccs = []
    p.on_note_on(9, 37, 100); p.on_note_off(9, 37)                     # FILL held
    p.on_note_on(9, 49, 100); p.on_note_on(9, 49, 100)                 # MUTE (the tablet's track) on, off
    p.on_note_on(9, 38, 100)                                           # FX GO
    p.on_cc(0, 12, 66); p.on_cc(0, 12, 63)                             # LENGTH: from 32, +2, -1
    check(p.ccs == [(13, 23, 127), (13, 23, 0), (11, 1, 127), (11, 1, 0), (11, 11, 127), (11, 11, 0), (11, 4, 34), (11, 4, 33)],
          "SAGGA BeatStep: ACTIONS FILL held, MUTE twice, FX GO; RELATIVE LENGTH +2 -1 (%s)" % p.ccs)
    for k in [k for k in list(sys.modules) if k.startswith("raspimidihub")]:
        del sys.modules[k]


def main():
    structural()
    bsp_tests()
    if not RMH or not os.path.isdir(os.path.join(RMH, "src", "raspimidihub")):
        print("sagga plugins: %d checks, %d failures (the hub's own host: skipped, RMH= a RaspiMIDIHub checkout)" % (N[0], len(FAILS)))
        return 1 if FAILS else 0
    sys.path.insert(0, os.path.join(RMH, "src"))
    sys.path.insert(0, os.path.join(RMH, "tests"))
    from raspimidihub.plugin_host.host import PluginHost
    import helpers

    d = tempfile.mkdtemp()
    for name in PLUGINS + ("sagga_bsp",):
        shutil.copytree(os.path.join(ROOT, "tools", "raspimidihub", name), os.path.join(d, name))
    host = PluginHost(plugins_dir=d)
    types = host.discover_plugins()
    check(set(types) == set(PLUGINS) | {"sagga_bsp"} and all(types[n]["kind"] == "controller" for n in PLUGINS) and types["sagga_bsp"]["kind"] != "controller",
          "the hub's plugin host finds the six controllers and SAGGA BeatStep (%s)" % types)
    p, h = helpers.make_plugin(host._plugin_types["sagga_bsp"])     # 0.20: LEARN and the pads in the hub's own host
    p.on_start()
    bsp_learn(p)
    h.clear()
    p.on_cc(0, 13, 127)
    p.on_note_on(9, 36, 100)
    check(h.ccs == [(11, 5, 6), (13, 48, 127), (13, 48, 0)] and "bsp_map" in p._param_values and "bsp_map" not in p.tidy_param_values(),
          "SAGGA BeatStep in the hub: OCTAVE +3, pad 1 = MUTE 1; the hub keeps what LEARN found (%s)" % h.ccs)
    remote_cls, mutes_cls = host._plugin_types["sagga_remote"], host._plugin_types["sagga_mutes"]

    p, h = helpers.make_plugin(remote_cls)
    p.on_param_change("play", True)
    check(h.ccs == [(13, 20, 127), (13, 20, 0)] and p.get_param("play") is False, "PLAY: CC 20 on channel 14, pressed then let go (%s)" % h.ccs)
    h.clear()
    p.on_param_change("fill", True)
    p.on_param_change("fill", False)
    check(h.ccs == [(13, 23, 127), (13, 23, 0)], "FILL: on until pressed again (%s)" % h.ccs)
    h.clear()
    p.on_param_change("morph", 64)
    p.on_param_change("quant", 3)
    p.on_param_change("morph_to", 5)
    p.on_param_change("sc2", True)
    check(h.ccs == [(13, 1, 64), (13, 6, 3), (13, 2, 5), (13, 42, 127), (13, 42, 0)], "MORPH 64, QUANTISE BAR, MORPH TO 6, SCENE 3 (%s)" % h.ccs)
    h.clear()
    p.on_param_change("rep16", True)
    p._param_values["rep16"] = True
    p._param_values["morph"] = 64
    p.panic()
    check(h.ccs == [(13, 26, 127), (13, 26, 0)], "the hub's PANIC lets REPEAT go and leaves MORPH alone (%s)" % h.ccs)
    cells = remote_cls.params[1].cells
    ccs = sorted(c.cc for c in cells if c.channel == 13)        # (TAKE: CC 107 on channel 13, beside SNAP 2's on 14)
    pairs = {24, 25, 26, 27}                                    # LOOP (tap) and REP (held) share their CC
    check(all(ccs.count(c) == (2 if c in pairs else 1) for c in set(ccs)) and set(ccs) <= {1, 2, 4, 5, 6, 7, 8, 9, 10, 11} | set(range(20, 48)) | {85, 87, 88, 89} | set(range(12, 20)) | set(range(106, 120)) | {107},
          "every cell its own CC of the FM-1's map, LOOP and REP the same (%s)" % ccs)
    grid = remote_cls.params[1]
    pos = [(c.col + dx, c.row) for c in cells for dx in range(c.span_cols)]
    check(len(pos) == len(set(pos)) and all(1 <= x <= grid.cols and 1 <= y <= grid.rows for x, y in pos), "the cells fit the grid, none on another")
    h.clear()
    p.on_param_change("loop8", True)                           # LOOP 1/8: a tap (127, 0 at once)
    p.on_param_change("rep16", True)                           # REP 1/16: held until switched off
    p.on_param_change("rep16", False)
    p.on_param_change("exit", True)
    check(h.ccs == [(13, 25, 127), (13, 25, 0), (13, 26, 127), (13, 26, 0), (13, 89, 127), (13, 89, 0)], "LOOP 1/8 tapped, REP 1/16 held, EXIT (%s)" % h.ccs)
    h.clear()
    p.on_param_change("intensity", 84)
    p.on_param_change("transpose", 14)
    p.on_param_change("stopbar", True)
    p.on_param_change("restart", True)
    check(h.ccs == [(13, 7, 84), (13, 11, 14), (13, 87, 127), (13, 87, 0), (13, 88, 127), (13, 88, 0)], "INTENSITY, TRANSPOSE +2, STOP @BAR, RESTART (%s)" % h.ccs)
    d = {c.param.name: c.param for c in cells}
    check(d["transpose"].default == 12 and d["transpose"].labels[12] == "0" and d["transpose"].labels[0] == "-12" and all(d[k].default == 64 for k in ("intensity", "gate", "swing", "filter")),
          "the macros start at 64 and TRANSPOSE at 12: 0 on the FM-1")

    p, h = helpers.make_plugin(mutes_cls)
    p.on_param_change("m4", True)
    p.on_param_change("k15", True)
    check(h.ccs == [(13, 52, 127), (13, 52, 0), (13, 79, 127)], "MUTE 5: CC 52 pressed; KILL 16: CC 79 held (%s)" % h.ccs)
    h.clear()
    p.on_param_change("r2", True)
    check(h.ccs == [(13, 92, 127), (13, 92, 0)] and p.get_param("r2") is False, "RETRIG 3: CC 92 pressed (%s)" % h.ccs)
    # 0.18: what the FM-1 sends back moves the cells and sends nothing
    live_cls, mod_cls = host._plugin_types["sagga_live"], host._plugin_types["sagga_mod"]
    p, h = helpers.make_plugin(live_cls)
    p.on_cc(11, 20, 2)
    p.on_cc(11, 1, 127)
    p.on_cc(12, 112, 6)
    check(p.get_param("arp") == 2 and p.get_param("mute") is True and p.get_param("track") == 6 and not h.ccs,
          "SAGGA Live: the FM-1's ARP DOWN, MUTE, TRACK 7 move the cells, nothing goes out (%s %s %s %s)" % (p.get_param("arp"), p.get_param("mute"), p.get_param("track"), h.ccs))
    p, h = helpers.make_plugin(mod_cls)
    p.on_note_on(12, 104, 127)
    p.on_cc(12, 94, 10)
    check(p.get_param("lfo_sw4") is True and p.get_param("rate") == 10 and not h.ccs, "SAGGA Mod: the FM-1's LFO 5 on and its RATE come back (%s)" % h.ccs)
    p.on_note_off(12, 104)
    check(p.get_param("lfo_sw4") is False and not h.ccs, "SAGGA Mod: LFO 5 off comes back")
    print("sagga plugins: %d checks, %d failures" % (N[0], len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
