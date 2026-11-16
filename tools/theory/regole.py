#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA SEQ, the THEORY engines: the rules written by hand, written out (in Italian, for docs/TEORIA.md).

The rules are the tables of firmware/src/sagga_theory.c; `sagga_theory --rules` prints them, a line each, and this writes
the ones of the four genres with rules written by hand, and of FREE, as the sheet shows them (the other 21 genres: their
rules are counted from the library, and tools/theory/gen_rules.py writes them out in docs/TEORIA-GENERI.md). The sheet
holds one block a style between two marks:

    <!-- regole TECHNO -->
    ...
    <!-- /regole -->

    python3 tools/theory/regole.py STYLE            the block of a style, to read
    python3 tools/theory/regole.py --write FILE     put the blocks into the sheet
    python3 tools/theory/regole.py --check FILE     ... or say whether they are the engine's (the tests do)
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STYLES = ["TECHNO", "HOUSE", "DNB", "DUBSTEP", "FREE"]
NAME = {"DNB": "DRUM+BASS"}                      # (a mark is a word; the FM-1's name of the genre has a sign in it)
FILL = {1: "levare del kick sull'ultimo sedicesimo (da energia 25; da 75 anche il penultimo)",
        2: "un ghost, un colpo e un accento che rulla sugli ultimi tre sedicesimi",
        3: "l'ultimo rullante un ottavo in ritardo, oppure due colpi rapidi dopo di lui",
        4: "due sedicesimi, o una rullata in tre, prima dell'uno (da energia 25)",
        5: "gli ultimi due sedicesimi pieni (da energia 30; da 60 l'ultimo rulla)",
        6: "la seconda metà si riempie"}
LEV = {1: "g", 2: "o", 3: "x", 4: "X"}
TONES = ["fondamentale", "quinta", "ottava", "terza", "settima", "quarta", "seconda", "sesta"]
SHAPES = ["scende", "sale", "arco", "due note alternate"]
KINDS = ["triade", "settima", "sus4", "quinta vuota"]
NCH = ["uno", "due", "tre", "quattro"]
MOVES = ["un grado sopra", "una terza sopra", "una quarta sopra", "una quinta sopra", "una terza sotto", "un grado sotto"]
DEG = ["I", "II", "III", "IV", "V", "VI", "VII"]
COLS = ["triade", "settima", "nona", "sus4", "sus2", "sesta"]
SCALES = ["minore", "dorica", "frigia", "maggiore", "misolidia", "minore armonica"]
PUSH = ["sulla battuta", "un sedicesimo prima", "un ottavo prima"]


def tool():
    out = os.path.join(ROOT, "build", "sagga_theory")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    src = [os.path.join(ROOT, p) for p in ("tools/theory/sagga_theory.c", "firmware/src/sagga_seq_core.c", "firmware/src/sagga_beats.c")]
    tmp = "%s.%d" % (out, os.getpid())
    subprocess.run(["cc", "-std=c11", "-O2", "-I" + os.path.join(ROOT, "firmware/src")] + src + ["-o", tmp], check=True)
    os.replace(tmp, out)
    return out


def pc(v):
    """a chance 0..255 against a number 0..255, as a percentage"""
    return "sempre" if int(v) >= 255 else "%d %%" % round(int(v) * 100 / 256)


def sixteenths(n):
    return "1 sedicesimo" if int(n) == 1 else "%s sedicesimi" % n


def weights(names, w):
    """the names of what has a weight, with its share"""
    w = [int(x) for x in w.split(",")]
    tot = sum(w)
    return ", ".join("%s %d %%" % (n, round(x * 100 / tot)) for n, x in zip(names, w) if x)


def rhythm(f, several):
    (_, _, part, pick, fixA, fixx, never, w, d_lo, d_hi, soft, soft_lev, cls, cls_e0, cls_lev, link, hole, cyc_n, cyc_p, bar2, fill, kick, apart) = f[:23]
    apart = str(int(apart) & 1)                   # (the other bits: a rule counted from the library, of two bars - not these)
    out = []
    cls = [int(x) for x in cls.split(",")]
    lev = [int(x) for x in cls_lev.split(",")]
    always = "".join("X" if a == "X" else "x" if b == "x" else "." for a, b in zip(fixA, fixx))
    if several:
        out.append("  una famiglia (%s %% dei semi)" % pick)
    if always.strip("."):
        out.append("    sempre   %s" % always)
    if never.strip(".") or kick == "1":
        out.append("    mai      %s%s" % (never if never.strip(".") else "", ("   e mai" if never.strip(".") else "") + " dove suona il kick" if kick == "1" else ""))
    if w.strip("."):
        ws = [int(c, 16) for c in w.replace(".", "0")]
        line = "    pesi     %s   densità %d-%d %%" % (w, round(int(d_lo) * 100 / 255), round(int(d_hi) * 100 / 255))
        if int(soft) >= max(ws):
            line += "   tutti '%s'" % LEV[int(soft_lev)]
        elif any(0 < x <= int(soft) for x in ws):
            line += "   fino a peso %s: '%s'" % (soft, LEV[int(soft_lev)])
        out.append(line)
    if any(cls):
        names = ["tempi", "e", "&", "a"]
        out.append("    classi   %s%s%s" % ("   ".join("%s %s '%s'" % (n, pc(c), LEV[l]) for n, c, l in zip(names, cls, lev) if c),
                                        "   (insieme)" if link == "1" else "",
                                        "   a energia 0 il %d %% di queste" % round(int(cls_e0) * 100 / 255) if any(0 < c < 255 for c in cls) else ""))
        if int(hole):
            out.append("             un colpo della classe manca: %s" % pc(hole))
    if int(cyc_n):
        out.append("    ciclo    un colpo ogni %s sedicesimi, oltre le stanghette (%d %% dei semi); sotto energia 40 uno ogni %d" % (
            cyc_n, round(int(cyc_p) * 17 * 100 / 256), 2 * int(cyc_n)))
    extra = []
    if kick == "2":
        extra.append("più probabile dove suona il kick (+5)")
    if apart == "1":
        extra.append("mai due colpi su sedicesimi vicini")
    extra.append("battute 2 e 4: %s %% delle scelte rifatte" % bar2)
    out.append("    " + "   ".join(extra))
    if int(fill):
        out.append("    chiusura %s" % FILL[int(fill)])
    return out


def line(f):
    (_, _, part, tone, first, strong, octpair, pair, same, turn, hold, hold_max, gap, roll) = f
    out = ["    note     %s" % weights(TONES, tone),
           "             sull'uno la fondamentale %s%s" % (pc(first), "   sui tempi fondamentale, quinta o ottava %s" % pc(strong) if int(strong) else "")]
    off = []
    if int(octpair) and int(pair):
        off.append("l'ottava della fondamentale del tempo %s (entro %s sedicesimi)" % (pc(octpair), pair))
    if int(same):
        off.append("la nota del tempo %s" % pc(same))
    if off:
        out.append("             fuori dai tempi: " + ", ".join(off))
    tail = []
    if int(turn):
        tail.append("nell'ultimo ottavo una nota che riporta a casa %s" % pc(turn))
    if int(hold):
        tail.append("tenute %s%s%s" % (pc(hold), " (al massimo %s)" % sixteenths(hold_max) if int(hold_max) else "", ", fino a %s di pausa prima della nota dopo" % sixteenths(gap) if int(gap) else ""))
    if int(roll):
        tail.append("rullate (2, 3 o 4 in un sedicesimo) %s" % pc(roll))
    if tail:
        out.append("             " + "   ".join(tail))
    return out


def motif(f):
    (_, _, part, penta, shape, span_lo, span_hi, rep, jit, leap, chord, off, cad, hold, hold_max, gap, cw, hi) = f
    return ["    motivo   scala: pentatonica %s, altrimenti tutte e sette le note; fino a %s semitoni sopra la fondamentale" % (pc(penta), hi),
            "             poggia su: %s" % weights(["la fondamentale", "la quinta", "la terza"], cw),
            "             profilo: %s   ampiezza %s-%s gradini" % (weights(SHAPES, shape), span_lo, span_hi),
            "             ripete la nota del suo tempo %s   un gradino fuori posto %s   un salto di due %s" % (pc(rep), pc(jit), pc(leap)),
            "             nota dell'accordo: sull'uno sempre, sui tempi %s, fuori dai tempi %s" % (pc(chord), pc(off)),
            "             la battuta 2 chiude aperta (sulla quinta) e l'ultima a casa %s   tenute %s" % (pc(cad), pc(hold))]


def chords(f):
    (_, _, part, kind, same, hold, hold_max, gap) = f
    return ["    accordi  %s   lo stesso tipo per tutto il pattern %s   tenuti %s%s" % (
        weights(KINDS, kind), pc(same), pc(hold), " (al massimo %s)" % sixteenths(hold_max) if int(hold_max) else "")]


def prog(f):
    (_, _, n_w, bars_w, move_w, first, last_w, col_w, col_same, scale_w, push_w) = f
    return ["LA PROGRESSIONE",
            "    scala          %s" % weights(SCALES, scale_w),
            "    accordi        %s" % weights(NCH, n_w),
            "    durata         %s" % weights(["1 battuta", "2 battute", "4 battute", "8 battute"], bars_w),
            "    parte da casa  %s %%" % first,
            "    la fondamentale si muove di  %s" % weights(MOVES, move_w),
            "    l'ultimo di tre o quattro    %s" % weights(DEG[1:], last_w.split(",", 1)[1]),
            "    colori         %s   lo stesso per tutti %s %%" % (weights(COLS, col_w), col_same),
            "    entra          %s" % weights(PUSH, push_w)]


def block(style, rows):
    """the rules of a style as the sheet shows them"""
    mine = [r for r in rows if r[1] == NAME.get(style, style)]
    out = []
    order = []
    for r in mine:
        if r[0] != "P" and r[2] not in order:
            order.append(r[2])
    for part in order:
        out.append(part)
        rh = [r for r in mine if r[0] == "R" and r[2] == part]
        for r in rh:
            out += rhythm(r, len(rh) > 1)
        for r in mine:
            if r[2] != part:
                continue
            if r[0] == "L":
                out += line(r)
            elif r[0] == "M":
                out += motif(r)
            elif r[0] == "C":
                out += chords(r)
        out.append("")
    for r in mine:
        if r[0] == "P":
            out += prog(r)
    return "\n".join(out).rstrip() + "\n"


def load():
    out = subprocess.run([tool(), "--rules"], capture_output=True, text=True, check=True).stdout
    return [l.split("\t") for l in out.splitlines()]


MARK = re.compile(r"(<!-- regole (\w+) -->\n```text\n)(.*?)(```\n<!-- /regole -->)", re.S)


def main(argv):
    rows = load()
    if len(argv) == 2 and argv[0] in ("--write", "--check"):
        text = open(argv[1], encoding="utf-8").read()
        new = MARK.sub(lambda m: m.group(1) + block(m.group(2), rows) + m.group(4), text)
        found = [m.group(2) for m in MARK.finditer(text)]
        if sorted(found) != sorted(STYLES):
            print("regole: %s holds the blocks of %s, not of every style" % (argv[1], ", ".join(found) or "no style"))
            return 1
        if argv[0] == "--check":
            if new != text:
                print("regole: %s is not what the engine's rules are: run python3 tools/theory/regole.py --write %s" % (argv[1], argv[1]))
                return 1
            print("regole: the sheet's rules are the engine's (%d rules)" % len(rows))
            return 0
        open(argv[1], "w", encoding="utf-8").write(new)
        print("regole: %s written" % argv[1])
        return 0
    for style in (argv or STYLES):
        print("=== %s\n%s" % (style, block(style, rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
