#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA SEQ 0.23, the THEORY engines: what they make, to listen to without an FM-1.

For a style (a genre of the FM-1, or FREE) and a seed the simulator - the firmware itself, the engines where BAND loads
the library - makes a band into eight scenes; the project comes out as the Pi's editor takes it (a .sgq the FM-1 loads),
and every scene is played and written into one MIDI file (General MIDI: the drums on channel 10, a sound for each
melodic part), with a marker at each scene.

    python3 tools/theory/render.py OUT_DIR [--styles TECHNO,REGGAETON,"UK GARAGE",FREE | all] [--seeds 1,2,3]
                                           [--pick HOUSE=5,6,10 ...] [--pack FILE.zip]

A project goes into OUT_DIR/<style>/; OUT_DIR/catalogo.txt lists them, and what the first sixteen seeds of each style
would be. --pack: with LEGGIMI.md and the sheets of the rules (docs/TEORIA.md, docs/TEORIA-GENERI.md), into a zip.
On an FM-1 with 0.23 the ENERGY is the machine's own: scenes 1, 4 and 5 (one band at three energies) play alike there,
at the energy of the moment - the three energies are for the MIDI file.

The scenes of a project:
    1  the seed's band, energy 60                 5  the same, energy 95
    2  a small variation of it (25 %)             6  another band, with USER 2
    3  a large variation of it (60 %)             7  a third one, with USER 3
    4  the same band, energy 25                   8  a fourth, energy 90, with USER 4
USER 1 is the seed's progression (the HARMONY plays it), USER 2-4 three more of the style: a scene does not hold the
progression, so on the FM-1 scenes 6-8 play on USER 1 until USER 2-4 is chosen by hand. A scene plays 8 bars, 16 when
the round of its chords is longer than 8. In the MIDI file the drums are General MIDI's (each part its instrument,
whatever note the track has on the FM-1).
"""
import argparse
import os
import shutil
import struct
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import sagga_sim_tests as S          # noqa: E402
import sagga_grid_bridge as B        # noqa: E402

STYLES = []                          # the names of the 26 styles, in the engines' order (styles(): asked of the tool)
SEEDS = 999                          # the seeds of the FM-1
SCENES = [  # (what it is, seed offset, variation, vary %, energy, the player's progression 0..3)
    ("il seme, energia 60", 0, 0, 0, 60, 0),
    ("variazione piccola (25 %)", 0, 1, 25, 60, 0),
    ("variazione grande (60 %)", 0, 2, 60, 60, 0),
    ("la stessa band, energia 25", 0, 0, 0, 25, 0),
    ("la stessa band, energia 95", 0, 0, 0, 95, 0),
    ("un'altra band, un'altra progressione dello stile (USER 2)", 100, 0, 0, 60, 1),
    ("una terza band (USER 3)", 200, 0, 0, 60, 2),
    ("una quarta, energia 90 (USER 4)", 300, 0, 0, 90, 3),
]
# General MIDI's percussion (channel 10) for each drum part
GM_DRUM = {"KICK": 36, "SNARE": 38, "CLAP": 39, "HAT": 42, "OPEN HAT": 46, "RIDE": 51, "SHAKER": 70, "PERC": 76, "CONGA": 63,
           "TOM": 45, "RIM": 37, "CRASH": 49, "COWBELL": 56}
DRUMS = {"KICK", "SNARE", "HAT", "PERC", "CLAP", "OPEN HAT", "RIDE", "SHAKER", "CONGA", "TOM", "RIM", "CRASH", "COWBELL"}
# General MIDI programs (0-based) for the melodic parts
PROGRAM = {"BASS": 38, "RUMBLE": 39, "SUB": 39, "LOG DRUM": 12, "CHORD": 4, "STAB": 62, "PAD": 89, "PIANO": 1,
           "ARP": 81, "LEAD": 80, "VOX": 54}


def theory_tool():
    out = os.path.join(ROOT, "build", "sagga_theory")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    src = [os.path.join(ROOT, p) for p in ("tools/theory/sagga_theory.c", "firmware/src/sagga_seq_core.c", "firmware/src/sagga_beats.c")]
    tmp = "%s.%d" % (out, os.getpid())                         # (made aside and moved in: another tool may be running it)
    subprocess.run(["cc", "-std=c11", "-O2", "-I" + os.path.join(ROOT, "firmware/src")] + src + ["-o", tmp], check=True)
    os.replace(tmp, out)
    return out


def styles(tool):
    """the names of the styles, by their number (a genre of the FM-1, 25: FREE)"""
    if not STYLES:
        for k in range(26):
            head = subprocess.run([tool, str(k), "0", "0", "0", "60", "16"], capture_output=True, text=True, check=True).stdout.splitlines()[0]
            STYLES.append(head[2:].split(" seed ")[0])
    return STYLES


def slug(style):
    return "".join(c if c.isalnum() else "-" for c in style.lower()).strip("-")


def band_text(tool, style, seed, var, vary, energy, length=64):
    """the header line and [(part, hits, notes)] as the engines write them"""
    out = subprocess.run([tool, str(styles(tool).index(style)), str(seed % SEEDS), str(var), str(vary), str(energy), str(length)], capture_output=True,
                         text=True, check=True).stdout.splitlines()
    return out[0], [tuple(l.split("\t")) for l in out[1:]]


def chords(tool, style, seed, k):
    """the player's progression k of a project (0: the seed's own; 1-3: three more of the style): (names, bars a chord, push, bars of a round)"""
    head, _ = band_text(tool, style, seed, k, 100 if k else 0, 60, 16)
    names = head.split("chords ")[1].split(",")[0]
    bars = int(head.split(" bars a chord")[0].rsplit(" ", 1)[1])
    push = int(head.rsplit("push ", 1)[1])
    return names, bars, push, bars * (names.count("-") + 1)


def vlq(n):
    b = [n & 0x7F]
    n >>= 7
    while n:
        b.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(b))


def smf(tracks, ppq=480):
    """tracks: [[(tick, bytes)]] -> a format 1 file"""
    out = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks), ppq)
    for ev in tracks:
        data, last = b"", 0
        for tick, msg in sorted(ev, key=lambda e: (e[0], e[1][0] & 0xF0 == 0x90 and e[1][0] != 0xFF)):   # (offs before ons at a tick)
            data += vlq(max(0, tick - last)) + msg
            last = max(last, tick)
        data += b"\x00\xFF\x2F\x00"
        out += b"MTrk" + struct.pack(">I", len(data)) + data
    return out


def meta(kind, text):
    t = text.encode("ascii", "replace")
    return bytes([0xFF, kind]) + vlq(len(t)) + t


def render(tool, style, seed, out_dir):
    st = styles(tool).index(style)
    head, parts = band_text(tool, style, seed, 0, 0, 60)
    bpm = int(head.split(" BPM")[0].rsplit(" ", 1)[1])
    bar_ms = 4 * 60000.0 / bpm
    progs = [chords(tool, style, seed, k) for k in range(4)]
    nbars = [16 if progs[sc[5]][3] > 8 else 8 for sc in SCENES]  # a scene: 8 bars, 16 when the round of its chords is longer
    s = S.Script()
    t = 100
    for i, (_, off, var, vary, energy, _prog) in enumerate(SCENES):
        s.raw(t, "theory %d %d %d %d %d %d" % (st, (seed + off) % SEEDS, var, vary, energy, i))
        t += 50
    s.raw(t + 100, "sx 7D 53 47 01")                           # the export, as the Pi's editor asks for it
    t += 6000
    segs = []
    for i in range(len(SCENES)):
        s.raw(t, "scene %d %d" % (i, SCENES[i][5]))
        s.raw(t + 20, "energy %d" % SCENES[i][4])               # (the machine's energy: the engines' patterns follow it)
        s.tap_btn(t + 100, S.PLAY)
        segs.append(t + 100)
        t = t + 100 + int(round(nbars[i] * bar_ms)) - 6
        s.tap_btn(t, S.PLAY)
        t += 800
    log = S.run(s, t + 500)
    # the project
    rx, image = B.DumpReceiver(), None
    for _, msg in log.sysex:
        r = rx.feed(msg)
        if r and r[0] == "image":
            image = r[1]
        elif r and r[0] == "error":
            raise SystemExit("export: " + r[1])
    if image is None:
        raise SystemExit("no project came out of the simulator (%d SysEx messages)" % len(log.sysex))
    why = B.check_image(image)
    if why:
        raise SystemExit("the project is not one the FM-1 takes: " + why)
    name = "teoria-%s-seme%d" % (slug(style), seed)
    out_dir = os.path.join(out_dir, slug(style))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, name + ".sgq"), "wb") as f:
        f.write(image)
    # the music: the band's parts are on the first tracks, a channel each, in the band's order
    ppq = 480
    names = [p[0] for p in parts]
    drum = [n in DRUMS for n in names]
    mel = [i for i in range(len(names)) if not drum[i]]
    gm = {}
    free = [c for c in range(16) if c != 9]
    for k, i in enumerate(mel):
        gm[i] = free[k % len(free)]
    tracks = [[(0, bytes([0xFF, 0x51, 0x03]) + struct.pack(">I", int(60000000 / bpm))[1:]), (0, bytes([0xFF, 0x58, 0x04, 4, 2, 24, 8])),
               (0, meta(3, "SAGGA SEQ teoria: %s seme %d" % (style, seed)))]]
    for i, n in enumerate(names):
        tr = [(0, meta(3, n))]
        if not drum[i]:
            tr.append((0, bytes([0xC0 | gm[i], PROGRAM.get(n, 81)])))
        tracks.append(tr)
    notes = 0
    base = 0
    for k, t0 in enumerate(segs):
        seg_ticks = nbars[k] * 4 * ppq
        if k:
            base += nbars[k - 1] * 4 * ppq
        tracks[0].append((base, meta(6, "scena %d: %s" % (k + 1, SCENES[k][0]))))
        end = t0 + nbars[k] * bar_ms
        on = {}
        for (tm, stt, d1, d2), port in zip(log.msgs, log.port):
            ch, hi = stt & 15, stt & 0xF0
            if port != 1 or tm < t0 - 2 or tm > end + 400 or ch >= len(names) or hi not in (0x80, 0x90):
                continue
            tick = base + int(round((tm - t0) * ppq * bpm / 60000.0))
            out_ch = 9 if drum[ch] else gm[ch]
            if drum[ch]:
                d1 = GM_DRUM.get(names[ch], d1)
            if hi == 0x90 and d2:
                if tm > end - 3:
                    continue
                if (ch, d1) in on:                              # (the same note again: the first one ends here)
                    tracks[1 + ch].append((tick, bytes([0x80 | out_ch, d1, 0])))
                tracks[1 + ch].append((min(tick, base + seg_ticks - 1), bytes([0x90 | out_ch, d1, d2])))
                on[(ch, d1)] = out_ch
                notes += 1
            elif (ch, d1) in on:
                tracks[1 + ch].append((min(max(tick, base), base + seg_ticks), bytes([0x80 | out_ch, d1, 0])))
                del on[(ch, d1)]
        for (ch, d1), out_ch in on.items():                     # (what the STOP ended)
            tracks[1 + ch].append((base + seg_ticks, bytes([0x80 | out_ch, d1, 0])))
    with open(os.path.join(out_dir, name + ".mid"), "wb") as f:
        f.write(smf(tracks, ppq))
    # what was made, as text
    key = head.split("key ")[1].split(",")[0]
    lines = ["%s, seme %d: %d BPM, tonalita' %s" % (style, seed, bpm, key), ""]
    for k in range(4):
        lines.append("USER %d   %-28s %d battut%s per accordo%s%s" % (k + 1, progs[k][0], progs[k][1], "a" if progs[k][1] == 1 else "e",
                     ", in anticipo di un %s" % ("sedicesimo" if progs[k][2] == 1 else "ottavo") if progs[k][2] else "",
                     "   (del seme)" if not k else ""))
    lines.append("")
    for k, (what, off, var, vary, energy, prog) in enumerate(SCENES):
        h, p = band_text(tool, style, seed + off, var, vary, energy)
        lines.append("scena %d: %s - %d battute, accordi %s" % (k + 1, what, nbars[k], progs[prog][0]))
        for part, r, nt in p:
            lines.append("  %-9s %s" % (part, " ".join(r[i:i + 16] for i in range(0, len(r), 16))))
            if nt != "-":
                lines.append("  %-9s %s" % ("", " ".join(nt[i:i + 16] for i in range(0, len(nt), 16))))
        lines.append("")
    with open(os.path.join(out_dir, name + ".txt"), "w") as f:
        f.write("\n".join(lines))
    return name, len(image), notes, head


def catalogue(tool, made, out_dir):
    """the projects that were made, and what the seeds in a row would be"""
    lines = ["I PROGETTI", ""]
    for style, seed in made:
        head, _ = band_text(tool, style, seed, 0, 0, 60, 16)
        key = head.split("key ")[1].split(",")[0]
        lines.append("%-26s tonalita' %-12s %s" % ("teoria-%s-seme%d" % (slug(style), seed), key,
                                                 "   ".join("USER %d %s" % (k + 1, chords(tool, style, seed, k)[0]) for k in range(4))))
    for style in sorted({st for st, _ in made}, key=styles(tool).index):
        lines += ["", "%s: i primi sedici semi" % style, ""]
        for seed in range(1, 17):
            head, _ = band_text(tool, style, seed, 0, 0, 60, 16)
            names, bars, push, _ = chords(tool, style, seed, 0)
            lines.append("  seme %-3d %-12s %-30s %d battut%s per accordo%s" % (seed, head.split("key ")[1].split(",")[0], names, bars, "a" if bars == 1 else "e",
                         ", in anticipo di un %s" % ("sedicesimo" if push == 1 else "ottavo") if push else ""))
    with open(os.path.join(out_dir, "catalogo.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")


def pack(out_dir, path):
    """the folder, with the two sheets, as a zip (the same bytes from the same files: sorted, one date)"""
    shutil.copy(os.path.join(ROOT, "tools", "theory", "LEGGIMI.md"), os.path.join(out_dir, "LEGGIMI.md"))
    shutil.copy(os.path.join(ROOT, "docs", "TEORIA.md"), os.path.join(out_dir, "TEORIA.md"))
    shutil.copy(os.path.join(ROOT, "docs", "TEORIA-GENERI.md"), os.path.join(out_dir, "TEORIA-GENERI.md"))
    names = []
    for base, _, files in os.walk(out_dir):
        names += [os.path.relpath(os.path.join(base, f), out_dir) for f in files]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n in sorted(names):
            info = zipfile.ZipInfo("sagga-teoria/" + n.replace(os.sep, "/"), (2026, 11, 16, 12, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(os.path.join(out_dir, n), "rb") as f:
                z.writestr(info, f.read())
    return len(names)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--styles", default="TECHNO,HOUSE,DRUM+BASS,DUBSTEP,FREE", help="names as the FM-1 shows them, or: all")
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--pick", nargs="*", default=[], help="STYLE=seed,seed,...: the seeds of one style")
    ap.add_argument("--pack", help="a zip of the folder, with LEGGIMI.md and docs/TEORIA.md")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    made = []
    pick = dict(x.split("=") for x in a.pick)
    tool = theory_tool()
    S.build()
    try:
        for style in (styles(tool) if a.styles == "all" else a.styles.split(",")):
            if style not in styles(tool):
                raise SystemExit("no such style: %s (%s)" % (style, ", ".join(styles(tool))))
            for seed in [int(x) for x in pick.get(style, a.seeds).split(",")]:
                name, size, notes, head = render(tool, style, seed, a.out)
                made.append((style, seed))
                print("%s: project %d bytes, %d notes in %d scenes | %s" % (name, size, notes, len(SCENES), head.lstrip("# ")))
        catalogue(tool, made, a.out)
        if a.pack:
            print("%s: %d files" % (a.pack, pack(a.out, a.pack)))
    finally:
        try:
            os.remove(S.BIN)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
