#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA SEQ: the rules of the THEORY engines for the genres that have none written by hand, COUNTED from the
firmware's own library. The way of GESMI (Eigenfeldt, Pasquier: a corpus transcribed by hand, the onsets counted on
every 16th), with the thinning of Mutable Instruments Grids (the hits that matter stay as the part empties).

  python3 tools/theory/gen_rules.py            write firmware/src/sagga_theory_data.h and docs/TEORIA-GENERI.md (the same
                                               rules, to read: in Italian, a table a genre)
  python3 tools/theory/gen_rules.py --check    exit 1 when those files are not what the library gives
  python3 tools/theory/gen_rules.py --stats    what was counted, a line a family

WHAT IS COUNTED, a genre and a part at a time
  the families   the variations of a part that are the same pattern with other details (a hat in 8ths, a hat off the
                 beat): variations are put together while they differ by 3 16ths a bar or less. A seed picks one, by
                 how many variations it has. The four biggest are kept.
  two bars       a variation of two or four bars says what bar 1 does and what bar 2 answers: a family has a rule for
                 the odd bars and, when the even ones differ, one for them.
  always         the 16ths nearly every variation of the family plays. Of four or more, a part of them is there at
                 every energy and the rest comes in at energy 25. The part that stays: what a thinned variation of the
                 library keeps (the two kicks of a breakdown); else another family of the part that is this one with
                 less (the off-beat bass under the rolling one); else every other hit of a regular pattern; else the
                 half that matters most - the accents, then the 16ths the part plays in all its families, then the
                 strong places of the bar.
  the weights    how often the family plays each other 16th: the energy brings them in (half of them at energy 50).
  the levels     an accent, a hit, a soft hit, a ghost: what the family writes there most often. The rolls too.
  the notes      a line: how often each tone of the chord, the root on the one, the octave after a root, the held
                 notes. Chords: triads, sevenths, power chords. A motif: its ladder, its shapes, how far it goes.
  the chords     the six progressions of the genre: how many chords, how long, where the roots go, the colours.
"""
import collections
import os
import statistics
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "firmware", "src", "sagga_theory_data.h")
DOC = os.path.join(ROOT, "docs", "TEORIA-GENERI.md")
HAND = (0, 3, 6, 13)             # TECHNO HOUSE DUBSTEP DRUM+BASS: their rules are written by hand (sagga_theory.c; 0.29: 22 genres)
ON = "Xxog234"
ROLLS = "234"
T_SAME = 3.0                     # variations this near (16ths a bar) are one family
MAX_FAM = 4
MID_E = 25                       # (th_rhythm_rule: the second half of what is always there comes in here)
D_LO, D_HI = 40, 255
W_SCALE = 26.0                   # a weight for a frequency: half of the hits are there at energy 50
METRIC = [1.0, 0.2, 0.4, 0.2, 0.7, 0.2, 0.4, 0.2, 0.9, 0.2, 0.4, 0.2, 0.7, 0.2, 0.4, 0.2]

F_KICK, F_SNARE, F_HAT, F_PERC, F_BASS, F_CHORD, F_ARP = range(7)
FUNC = {"KICK": 0, "SNARE": 1, "HAT": 2, "PERC": 3, "BASS": 4, "CHORD": 5, "ARP": 6, "CLAP": 9, "OPEN HAT": 10, "RIDE": 11,
        "SHAKER": 12, "CONGA": 13, "TOM": 14, "RIM": 15, "CRASH": 16, "COWBELL": 17, "RUMBLE": 18, "SUB": 19, "LOG DRUM": 20,
        "STAB": 21, "PAD": 22, "PIANO": 23, "LEAD": 24, "VOX": 25}
FILL = {"KICK": "TH_F_PICK", "SNARE": "TH_F_ROLL", "CLAP": "TH_F_ROLL", "HAT": "TH_F_HAT", "PERC": "TH_F_BUSY",
        "CONGA": "TH_F_BUSY", "TOM": "TH_F_BUSY"}


def libdump():
    """the firmware's library as lines of text (tools/theory/libdump.c, built here)"""
    build = os.path.join(ROOT, "build")
    os.makedirs(build, exist_ok=True)
    exe = os.path.join(build, "sagga_libdump")
    src = [os.path.join(ROOT, "tools", "theory", "libdump.c"), os.path.join(ROOT, "firmware", "src", "sagga_seq_core.c"),
           os.path.join(ROOT, "firmware", "src", "sagga_beats.c")]
    if not os.path.exists(exe) or any(os.path.getmtime(s) > os.path.getmtime(exe) for s in src):
        fd, tmp = tempfile.mkstemp(dir=build, prefix="libdump.")
        os.close(fd)
        subprocess.check_call(["cc", "-std=c11", "-O2", "-I" + os.path.join(ROOT, "firmware", "src")] + src + ["-o", tmp])
        os.replace(tmp, exe)
    return subprocess.check_output([exe]).decode("ascii").splitlines()


class Var:
    def __init__(self, v, hits, notes):
        self.v, self.hits, self.notes = v, hits, notes
        n = len(hits) // 16
        b = [hits[i * 16:(i + 1) * 16] for i in range(n)]
        if n == 1:
            self.bars = ([b[0]], [b[0]])
        elif n == 2:
            self.bars = ([b[0]], [b[1]])
        else:                    # four bars: the last six 16ths are the fill of the pattern - bar 2's stand in
            self.bars = ([b[0], b[2]], [b[1], b[3][:10] + b[1][10:]])
        self.vec = [sum(1.0 for x in bs if x[s] in ON) / len(bs) for bs in self.bars for s in range(16)]


def parse(lines):
    genres, scales = collections.OrderedDict(), {}
    for l in lines:
        f = l.split("\t")
        if f[0] == "S":
            scales[int(f[1])] = (int(f[3]), int(f[4]), f[2])
        elif f[0] == "G":
            genres[int(f[1])] = dict(name=f[2], scales=[int(x) for x in f[5].split(",")], hrhythm=int(f[6]), half=int(f[8]),
                                     parts=collections.OrderedDict(), progs=[])
        elif f[0] == "V":
            p = genres[int(f[1])]["parts"].setdefault(int(f[2]), dict(name=f[3], kind=int(f[4]), family=int(f[5]), vars=[]))
            p["vars"].append(Var(int(f[6]), f[7], f[8]))
        elif f[0] == "P":
            genres[int(f[1])]["progs"].append((int(f[2]), int(f[3]), [int(x) for x in f[4].split(",")], [int(x) for x in f[5].split(",")]))
    return genres, scales


def cluster(vs):
    """the families: average linkage, while two groups differ by T_SAME 16ths a bar or less; the biggest are kept"""
    cl = [[i] for i in range(len(vs))]

    def d(a, b):
        return sum(abs(x - y) for x, y in zip(vs[a].vec, vs[b].vec)) / 2.0

    def dist(A, B):
        return sum(d(a, b) for a in A for b in B) / (len(A) * len(B))

    while len(cl) > 1:
        best = min((dist(cl[i], cl[j]), i, j) for i in range(len(cl)) for j in range(i + 1, len(cl)))
        if best[0] > T_SAME:
            break
        cl[best[1]] = sorted(cl[best[1]] + cl[best[2]])
        del cl[best[2]]
    cl.sort(key=lambda c: (-len(c), c[0]))
    return cl[:MAX_FAM], cl[MAX_FAM:]


def count(members, which):
    """how often the members play each 16th of their odd (0) or even (1) bars, and what they write there"""
    f, ch = [0.0] * 16, [collections.Counter() for _ in range(16)]
    for m in members:
        bars = m.bars[which]
        for b in bars:
            for s, c in enumerate(b):
                if c in ON:
                    f[s] += 1.0 / len(bars)
                    ch[s][c] += 1.0 / len(bars)
    return [x / len(members) for x in f], ch


def level_of(ch, soften=False):
    """0 a hit, 1 an accent, 2 a soft hit, 3 a ghost: what is written most often (a roll: a hit; a tie: the louder)"""
    c = collections.Counter()
    for k, v in ch.items():
        c["x" if k in ROLLS else k] += v
    if not c:
        return 0
    top = max("Xxog", key=lambda k: (c[k], -"Xxog".index(k)))
    if soften:                   # (a hit borrowed from the part's other families: one step softer)
        top = {"X": "x", "x": "o", "o": "o", "g": "g"}[top]
    return {"x": 0, "X": 1, "o": 2, "g": 3}[top]


def rate(c, n, prior, k=2.0):
    return (c + prior * k) / (n + k)


def u8(x):
    return max(0, min(255, int(round(x))))


def family_core(members):
    """what a family always plays in its odd and in its even bars, the variations it is counted on, and its thinned ones"""
    f_all, _ = count(members, 0)
    maj = {s for s in range(16) if f_all[s] >= 0.6}
    sparse = []
    if len(members) >= 3 and len(maj) >= 3:                       # a thinned variation: most of the family's hits are missing
        for m in members:
            on = {s for s in range(16) if m.bars[0][0][s] in ON}
            if len(on & maj) <= 0.67 * len(maj) and len(on - maj) <= 1:
                sparse.append(m)
    full = [m for m in members if m not in sparse]
    if len(full) < 2:
        full, sparse = members, []
    n = len(full)
    thr = 0.99 if n <= 3 else 0.75 if n <= 5 else 0.8
    cores, hints = [], []
    for which in (0, 1):
        f, _ = count(full, which)
        cores.append({s for s in range(16) if f[s] >= thr})
        hint = set()
        for m in sparse:
            for b in m.bars[which]:
                hint |= {s for s in range(16) if b[s] in ON}
        hints.append(hint)
    return cores, hints, full, sparse


def family_rules(part, fam, other_cores, others, G, apart, drum):
    """the rule of a family for its odd bars and for its even bars: (always, from MID_E, weights, levels, rolls, ...)"""
    out = []
    cores, hints, full, sparse = fam
    for which in (0, 1):
        f, ch = count(full, which)
        fo, cho = count(others, which) if others else ([0.0] * 16, [collections.Counter() for _ in range(16)])
        core, hint = cores[which], hints[which]
        acc = [(ch[s]["X"] / sum(ch[s].values())) if ch[s] else 0.0 for s in range(16)]
        imp = [4.0 * acc[s] + 2.0 * G[s] for s in range(16)]
        skel = None
        subs = sorted((c[which] for c in other_cores if c[which] < core and 0.25 * len(core) <= len(c[which]) <= 0.75 * len(core)),
                      key=lambda c: (-len(c), sorted(c)))         # another family of the part that is this one, thinned
        if len(core) < 4:
            skel = set(core)
        elif hint & core and len(hint & core) <= 0.75 * len(core):
            skel = hint & core
        elif subs:
            skel = set(subs[0])
        else:
            for p in (1, 2, 4):                                   # a regular pattern thins to every other hit of it: the half
                for o in range(p):                                # that matters more (a tie: a hat keeps its off-beats)
                    if core == set(range(o, 16, p)):
                        a, b = set(range(o, 16, 2 * p)), set(range(o + p, 16, 2 * p))
                        ia, ib = sum(imp[s] for s in a), sum(imp[s] for s in b)
                        skel = a if ia > ib + 0.01 else b if ib > ia + 0.01 else (b if part["family"] == F_HAT else a)
        if skel is None:
            order = sorted(core, key=lambda s: (-(imp[s] + METRIC[s]), s))
            skel = set(order[:(len(core) + 1) // 2])
        w, lv, rollm, rr, rk = [0] * 16, [0] * 16, 0, [], collections.Counter()
        for s in range(16):
            if f[s] > 0.0:
                lv[s] = level_of(ch[s])
            if s in core:
                continue
            if f[s] > 0.0:
                w[s] = max(1, min(15, int(round(W_SCALE * f[s]))))
            elif part["family"] not in (F_KICK, F_SNARE) and fo[s] >= 0.25:  # a little of what the part does in its other families
                w[s] = 1
                lv[s] = level_of(cho[s], soften=drum)
        if drum:
            for s in range(16):
                tot = sum(ch[s].values())
                r = sum(v for k, v in ch[s].items() if k in ROLLS)
                if f[s] >= 0.25 and tot and r / tot >= 0.3:
                    rollm |= 1 << s
                    rr.append((r / tot, f[s]))
                    for k, v in ch[s].items():
                        if k in ROLLS:
                            rk[k] += v
        roll = 0
        if rollm:
            chance = sum(a * b for a, b in rr) / sum(b for _, b in rr)
            top = max(ROLLS, key=lambda k: (rk[k], -ROLLS.index(k)))
            roll = ((int(top) - 1) << 6) | (u8(chance * 255.0) >> 2)
        out.append(dict(core=core, skel=skel, w=w, lv=lv, rollm=rollm, roll=roll, f=f))
    if apart:                    # no hit beside one that is always there (th_rhythm_rule would take it away again at energy MID_E)
        for which in (0, 1):
            me, other = out[which], out[1 - which]
            for s in range(16):
                left = (s - 1) in me["core"] if s else 15 in other["core"]
                right = (s + 1) in me["core"] if s < 15 else 0 in other["core"]
                if left or right:
                    me["w"][s] = 0
    return out, len(sparse)


def part_rules(g, G_all, func, part, kick_common, stats, doc):
    """the rhythm rules of a part: a list of text lines for TH_DATA_RULES (and its rows of the sheet, into doc)"""
    vs = part["vars"]
    drum = part["kind"] == 0
    kept, dropped = cluster(vs)
    total = sum(len(c) for c in kept)
    Gf, _ = count(vs, 0)
    Ge, _ = count(vs, 1)
    G = [(a + b) / 2.0 for a, b in zip(Gf, Ge)]
    # what the part does with the kick of its genre, and whether two of its notes ever stand side by side
    kick = []
    on_n = adj = on_k = 0
    for v in vs:
        for i, c in enumerate(v.hits):
            if c in ON:
                on_n += 1
                on_k += (i % 16) in kick_common
                if i + 1 < len(v.hits) and v.hits[i + 1] in ON:
                    adj += 1
    per_bar = on_n / sum(len(v.hits) / 16.0 for v in vs)
    apart = (not drum) and adj == 0 and per_bar <= 4.0 and part["name"] not in ("ARP", "LEAD", "VOX")
    if part["name"] == "RUMBLE" and kick_common and on_k <= 0.08 * on_n:
        kick.append("TH_K_AVOID")
    elif part["name"] == "SUB" and kick_common and on_k * 16.0 >= 1.5 * on_n * len(kick_common):
        kick.append("TH_K_WITH")
    if apart:
        kick.append("TH_K_APART")
    kick.append("TH_K_LV")
    # the fill: the genre's part has one when its four-bar variations end fuller than their second bar, or when it has
    # nothing but one-bar variations to say (the family's own way into the one; not a snare or a clap: theirs is a
    # roll with an accent, and a one-bar variation that wants one has written it)
    fill = "TH_F_NONE"
    v64 = [v for v in vs if len(v.hits) == 64]
    all16 = all(len(v.hits) == 16 for v in vs)
    extra = (sum(sum(1 for c in v.hits[58:64] if c in ON) - sum(1 for c in v.hits[26:32] if c in ON) for v in v64) / len(v64)) if v64 else 0.0
    if part["name"] in FILL and ((v64 and extra >= 0.75) or (all16 and part["family"] != F_SNARE)):
        fill = FILL[part["name"]]
        if fill == "TH_F_ROLL" and g["half"]:
            fill = "TH_F_TRIP"
    lines = []
    fams = [family_core([vs[i] for i in c]) for c in kept]
    for k, c in enumerate(kept):
        others = [vs[i] for i in range(len(vs)) if i not in c]
        rules, n_sparse = family_rules(part, fams[k], [f[0] for j, f in enumerate(fams) if j != k], others, G, apart, drum)
        a, b = rules
        two = (a["core"] != b["core"] or a["skel"] != b["skel"] or a["rollm"] != b["rollm"] or a["roll"] != b["roll"]
               or sum(abs(x - y) for x, y in zip(a["w"], b["w"])) > 6 or any(a["lv"][s] != b["lv"][s] for s in a["core"]))
        if not two:              # (the two bars are one rule: what either does)
            for s in range(16):
                if b["w"][s] > a["w"][s]:
                    a["w"][s], a["lv"][s] = b["w"][s], b["lv"][s]
        pick = 0 if len(kept) == 1 else max(1, int(round(100.0 * len(c) / total)))
        cells = [[], [], []]
        for which in (0, 1) if two else (0,):
            r = rules[which]
            cells[0].append("".join(("Xxog"[[1, 0, 2, 3].index(r["lv"][s])] if s in r["skel"] else ".") for s in range(16)))
            cells[1].append("".join(("Xxog"[[1, 0, 2, 3].index(r["lv"][s])] if s in r["core"] else ".") for s in range(16)))
            cells[2].append("".join("%x" % x if x else "." for x in r["w"]))
        notes = []
        if fill != "TH_F_NONE":
            notes.append("chiusura")
        if rules[0]["rollm"] or rules[1]["rollm"]:
            notes.append("rullate")
        if "TH_K_AVOID" in kick:
            notes.append("mai sul kick")
        if "TH_K_WITH" in kick:
            notes.append("con il kick")
        doc.append("| %s | %s | %s | %s | %s | %s |" % (
            part["name"] if k == 0 else "", "la sola" if len(kept) == 1 else "%d di %d · %d %%" % (k + 1, len(kept), pick),
            "<br>".join("`%s`" % x for x in cells[0]), "<br>".join("`%s`" % x for x in cells[1]),
            "<br>".join("`%s`" % x for x in cells[2]), ", ".join(notes)))
        for which in (0, 1) if two else (0,):
            r = rules[which]
            fixx = sum(1 << s for s in r["skel"])
            mid = sum(1 << s for s in r["core"] - r["skel"])
            lvw = sum(r["lv"][s] << (2 * s) for s in range(16))
            flags = " | ".join(kick + (["TH_K_TWO"] if two and which == 0 else []))
            look = "".join(("Xxog"[[1, 0, 2, 3].index(r["lv"][s])] if s in r["core"] else ".") for s in range(16))
            later = "".join(("+" if s in r["core"] - r["skel"] else ".") for s in range(16))
            wtxt = "".join("%x" % x if x else "." for x in r["w"])
            lines.append("    /* %s %s%s, variations %s%s: always %s  from energy %d %s  weights %s */ \\" % (
                g["name"], part["name"], "" if len(kept) == 1 else " %d/%d" % (k + 1, len(kept)),
                ",".join(str(vs[i].v) for i in c), " (even bars)" if which else "", look, MID_E, later, wtxt))
            # (the levels: two halves - a whole 32-bit number can look like the address of a register of the FM-1, and the
            # build's check that no register is touched outside firmware/hal would stop on it)
            lines.append("    {%s, %d, %d, 0, 0x%04X, 0, TW(%s), %d, %d, 0, TH_O, TH_NOCLS, 0, %d, %s, %s, 0x%04X, 0x%04X, TL(0x%04X, 0x%04X), %d}, \\" % (
                "255" if which else str(g["index"]), func, pick, fixx, ",".join(str(x) for x in r["w"]), D_LO, D_HI, 35 if two else 25,
                fill, flags, mid, r["rollm"], lvw >> 16, lvw & 0xFFFF, r["roll"]))
        stats.append("%-10s %-8s family %d/%d (%2d%%) variations %-28s %s%s%s" % (
            g["name"], part["name"], k + 1, len(kept), pick or 100, ",".join(str(vs[i].v) for i in c),
            "two bars  " if two else "one bar   ", "sparse %d  " % n_sparse if n_sparse else "", fill if fill != "TH_F_NONE" else ""))
    if dropped:
        stats.append("%-10s %-8s not kept: variations %s" % (g["name"], part["name"], ",".join(str(vs[i].v) for c in dropped for i in c)))
    return lines


TONE = {0: 0, 7: 1, 12: 2, 3: 3, 4: 3, 15: 3, 10: 4, 11: 4, 5: 5, 6: 5, 1: 6, 2: 6, 13: 6, 14: 6, 8: 7, 9: 7}


def holds_of(vs):
    """how the notes of a part are held: (chance 0..255, the longest in steps - 0: to the next -, the rests kept before the next)"""
    had = held = 0
    lens, rooms, gaps = [], [], []
    for v in vs:
        h, n = v.hits, len(v.hits)
        for i, c in enumerate(h):
            if c not in ON:
                continue
            j = i + 1
            while j < n and h[j] == "-":
                j += 1
            nxt = j
            while nxt < n and h[nxt] == ".":
                nxt += 1
            if nxt - i - 1 < 1 or c in ROLLS:
                continue
            had += 1
            if j > i + 1:
                held += 1
                lens.append(j - i - 1)
                rooms.append(nxt - i - 1)
                if nxt < n:
                    gaps.append(nxt - j)
    if not held:
        return 0, 0, 0
    share = held / had
    chance = 255 if share >= 0.9 else u8(255.0 * share)
    if statistics.median(lens) >= 0.8 * statistics.median(rooms):          # held to the next note, less a rest or two
        return chance, 0, min(3, int(round(statistics.median(gaps)))) if gaps else 0
    return chance, max(1, min(15, int(round(statistics.median(lens))))), 0


def line_rule(g, func, part):
    tone = collections.Counter()
    first, strong, octp, same, rolls, turn = [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0]
    for v in part["vars"]:
        h, nt = v.hits, v.notes
        last = max((i for i, c in enumerate(h) if c in ON), default=-1)
        if len(h) >= 32 and last >= 0:
            turn[1] += 1
            turn[0] += last >= len(h) - 2 and TONE[int(nt[last], 16)] in (4, 1, 6, 5)
        for i, c in enumerate(h):
            if c not in ON:
                continue
            t = TONE[int(nt[i], 16)]
            tone[t] += 1
            s = i % 16
            rolls[1] += 1
            rolls[0] += c in ROLLS
            if s == 0:
                first[1] += 1
                first[0] += t == 0
            elif s % 4 == 0:
                strong[1] += 1
                strong[0] += t in (0, 1, 2)
            else:
                bi = i - s % 4
                if h[bi] in ON:
                    tb = TONE[int(nt[bi], 16)]
                    if tb in (0, 2):
                        octp[1] += 1
                        octp[0] += t == (2 if tb == 0 else 0)
                    same[1] += 1
                    same[0] += t == tb
    total = sum(tone.values())
    lib = [tone[k] / total for k in range(8)]
    p_first, p_strong = u8(255 * rate(first[0], first[1], 0.85)), u8(255 * rate(strong[0], strong[1], 0.7))
    p_oct, p_same = u8(255 * rate(octp[0], octp[1], 0.2)), u8(255 * rate(same[0], same[1], 0.3))
    # The weights of the tones are not the library's counts: the engine puts the root on the one, the root, the fifth or
    # the octave on a beat, the octave after a root, and repeats (th_line_tone). The weights that, through all that, give
    # back the library's counts: fitted, a step at a time.
    T = [max(x, 0.002) for x in lib]

    def made(T):
        f1, st, oc, sm = p_first / 256.0, p_strong / 256.0, p_oct / 256.0, p_same / 256.0
        tot = sum(T)
        Tn = [x / tot for x in T]
        t3 = sum(Tn[:3])
        B = [st * (Tn[k] / t3 if k < 3 else 0.0) + (1.0 - st) * Tn[k] for k in range(8)]
        D0 = [f1 * (1.0 if k == 0 else 0.0) + (1.0 - f1) * B[k] for k in range(8)]

        def off(base):
            o = [0.0] * 8
            for k in range(8):
                rest = base[k]
                if k in (0, 2):
                    o[2 - k] += rest * oc
                    rest *= 1.0 - oc
                o[k] += rest * sm
                for j in range(8):
                    o[j] += rest * (1.0 - sm) * Tn[j]
            return o

        o0, ob = off(D0), off(B)
        n = sum(where) or 1.0
        return [(where[0] * D0[k] + where[1] * o0[k] + where[2] * B[k] + where[3] * ob[k]) / n for k in range(8)]

    where = [0.0, 0.0, 0.0, 0.0]          # the notes on the one, after it, on the other beats, after them
    for v in part["vars"]:
        for i, c in enumerate(v.hits):
            if c in ON:
                s = i % 16
                where[(0 if s < 4 else 2) + (1 if s % 4 else 0)] += 1.0
    for _ in range(40):
        out = made(T)
        T = [max(0.0005, T[k] * (lib[k] / out[k] if out[k] > 0 else 1.0)) if lib[k] > 0 else 0.0 for k in range(8)]
    tot = sum(T)
    tw = [int(round(100.0 * x / tot)) for x in T]
    tw[0] = max(tw[0], 1)
    hold, hold_max, gap = holds_of(part["vars"])
    say = "%s: %s%s." % (part["name"], shares(TONE_IT, lib), "; note tenute" if hold >= 128 else "")
    return "    {%d, %d, {%s}, %d, %d, %d, 3, %d, %d, %d, %d, %d, %d}, /* %s %s */ \\" % (
        g["index"], func, ", ".join(str(x) for x in tw), p_first, p_strong, p_oct, p_same, u8(255 * rate(turn[0], turn[1], 0.25)),
        hold, hold_max, gap, u8(255.0 * rolls[0] / max(1, rolls[1])), g["name"], part["name"]), say


def chord_rule(g, func, part):
    kinds = collections.Counter()
    same = [0, 0]
    KIND = {"m": 0, "M": 0, "s": 0, "n": 1, "N": 1, "7": 1, "5": 3}
    for v in part["vars"]:
        first = None
        for i, c in enumerate(v.hits):
            if c not in ON:
                continue
            k = KIND[v.notes[i]]
            kinds[k] += 1
            if first is None:
                first = k
            else:
                same[1] += 1
                same[0] += k == first
    total = sum(kinds.values())
    kw = [int(round(100.0 * kinds[k] / total)) for k in range(4)]
    hold, hold_max, gap = holds_of(part["vars"])
    say = "%s: %s%s." % (part["name"], shares(["triadi", "accordi di settima", "sus4", "quinte vuote"], [x / 100.0 for x in kw]), "; tenuti" if hold >= 128 else "")
    return "    {%d, %d, {%s}, %d, %d, %d, %d}, /* %s %s */ \\" % (
        g["index"], func, ", ".join(str(x) for x in kw), u8(255 * rate(same[0], same[1], 0.8)), hold, hold_max, gap, g["name"], part["name"]), say


def lead_rule(g, func, part, major):
    penta_set = {0, 2, 4, 7, 9} if major else {0, 3, 5, 7, 10}
    chord_set = {0, 4, 7} if major else {0, 3, 7}
    penta, shapes, spans, rep, leap, chord, off, cad = [0, 0], collections.Counter(), [], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0]
    pitches, cw = [], [0, 0, 0]
    for v in part["vars"]:
        h, nt = v.hits, v.notes
        notes = [(i, int(nt[i], 16)) for i, c in enumerate(h) if c in ON]
        if not notes:
            continue
        inp = sum(1 for _, p in notes if p % 12 in penta_set)
        penta[1] += 1
        penta[0] += inp >= 0.9 * len(notes)
        cad[1] += 1
        cad[0] += notes[-1][1] % 12 == 0
        for a, b in zip(notes, notes[1:]):
            rep[1] += 1
            rep[0] += a[1] == b[1]
            leap[1] += 1
            leap[0] += abs(a[1] - b[1]) >= 7
        for i, p in notes:
            w = chord if i % 4 == 0 else off
            w[1] += 1
            w[0] += p % 12 in chord_set
            pitches.append(p)
            if p % 12 in chord_set:
                cw[0 if p % 12 == 0 else 1 if p % 12 == 7 else 2] += 1
        for b in range(len(h) // 16):
            bar = [(i, p) for i, p in notes if i // 16 == b]
            if len(bar) < 2:
                continue
            ps = [p for _, p in bar]
            spans.append((max(ps) - min(ps)) / (2.4 if inp >= 0.9 * len(notes) else 1.7))
            if len(set(ps)) <= 2:
                shapes[3] += 1
                continue
            mt, mp = sum(i for i, _ in bar) / len(bar), sum(ps) / len(bar)
            cov = sum((i - mt) * (p - mp) for i, p in bar)
            den = (sum((i - mt) ** 2 for i, _ in bar) * sum((p - mp) ** 2 for p in ps)) ** 0.5
            r = cov / den if den else 0.0
            shapes[0 if r <= -0.5 else 1 if r >= 0.5 else 2] += 1
    total = sum(shapes.values())
    sw = [max(5, int(round(100.0 * shapes[k] / total))) if total else 25 for k in range(4)]
    spans.sort()
    lo = max(1, min(4, int(round(spans[len(spans) // 4])))) if spans else 1
    hi = max(lo, min(5, int(round(spans[(3 * len(spans)) // 4])))) if spans else 3
    hold, hold_max, gap = holds_of(part["vars"])
    pitches.sort()
    top = max(10, min(15, pitches[min(len(pitches) - 1, (19 * len(pitches)) // 20)])) if pitches else 15
    cws = [int(round(6.0 * x / max(cw))) if max(cw) else 1 for x in cw]
    cws[0] = max(cws[0], 1)
    p_penta = max(40, min(235, u8(255 * rate(penta[0], penta[1], 0.6))))
    say = "%s: un motivo - %s; scala pentatonica %d volte su 100, altrimenti tutte e sette le note; fino a %d semitoni sopra la fondamentale; poggia su %s." % (
        part["name"], shares(["scende", "sale", "fa un arco", "alterna due note"], [x / float(sum(sw)) for x in sw]), round(p_penta * 100 / 256.0), top,
        shares(["fondamentale", "quinta", "terza"], [x / float(sum(cws)) for x in cws]))
    return "    {%d, %d, %d, {%s}, %d, %d, %d, 50, %d, %d, %d, %d, %d, %d, %d, {%s}, %d}, /* %s %s */ \\" % (
        g["index"], func, p_penta, ", ".join(str(x) for x in sw), lo, hi,
        min(200, u8(255 * rate(rep[0], rep[1], 0.2))), min(80, u8(255 * rate(leap[0], leap[1], 0.1))),
        u8(255 * rate(chord[0], chord[1], 0.8)), u8(255 * rate(off[0], off[1], 0.4)), max(60, u8(255 * rate(cad[0], cad[1], 0.5))),
        hold, hold_max, gap, ", ".join(str(x) for x in cws), top, g["name"], part["name"]), say


TONE_IT = ["fondamentale", "quinta", "ottava", "terza", "settima", "quarta", "seconda", "sesta"]


def shares(names, vals):
    """the names of what has a share of 3 % or more, the biggest first"""
    order = sorted(range(len(names)), key=lambda k: (-vals[k], k))
    return ", ".join("%s %d %%" % (names[k], round(100.0 * vals[k])) for k in order if vals[k] >= 0.03)


def prog_rule(g, scale_names):
    a = 0.3

    def weights(counter, keys):
        tot = sum(counter[k] for k in keys) + a * len(keys)
        return [int(round(100.0 * (counter[k] + a) / tot)) for k in keys]

    n_w, bars_w, move, last, col = (collections.Counter() for _ in range(5))
    first = same = 0
    for n, bars, degs, cols in g["progs"]:
        n_w[min(n, 4)] += 1
        bars_w[bars if bars in (1, 2, 4, 8) else 2] += 1
        first += degs[0] == 0
        same += len(set(cols)) == 1
        for x, y in zip(degs, degs[1:]):
            if (y - x) % 7:
                move[(y - x) % 7] += 1
        if n >= 3 and degs[-1] % 7:
            last[degs[-1] % 7] += 1
        for c in cols:
            col[c] += 1
    np_ = len(g["progs"])
    lw = weights(last, range(7))
    lw[0] = 0                    # (the last chord of three or four is never home: sq_th_prog)
    push = {2: (45, 40, 15), 3: (45, 15, 40)}.get(g["hrhythm"], (100, 0, 0))
    wn, wb, wm, wc = weights(n_w, (1, 2, 3, 4)), weights(bars_w, (1, 2, 4, 8)), weights(move, range(1, 7)), weights(col, range(6))
    say = ("**La progressione.** %s; ogni accordo dura %s; parte da casa %d volte su 100; la fondamentale si muove di %s; colori: %s%s. Le scale del genere: %s." % (
        shares(["un accordo", "due accordi", "tre accordi", "quattro accordi"], [x / 100.0 for x in wn]),
        shares(["1 battuta", "2 battute", "4 battute", "8 battute"], [x / 100.0 for x in wb]), int(round(100.0 * rate(first, np_, 0.8))),
        shares(["un grado sopra", "una terza sopra", "una quarta sopra", "una quinta sopra", "una terza sotto", "un grado sotto"], [x / 100.0 for x in wm]),
        shares(["triade", "settima", "nona", "sus4", "sus2", "sesta"], [x / 100.0 for x in wc]),
        {2: "; gli accordi entrano spesso un sedicesimo prima", 3: "; gli accordi entrano spesso un ottavo prima"}.get(g["hrhythm"], ""),
        ", ".join(scale_names)))
    return "    [%d] = {{%s}, {%s}, {%s}, %d, {%s}, {%s}, %d, {0, 0, 0, 0, 0, 0}, {%d, %d, %d}}, /* %s */ \\" % (
        g["index"], ", ".join(str(x) for x in weights(n_w, (1, 2, 3, 4))), ", ".join(str(x) for x in weights(bars_w, (1, 2, 4, 8))),
        ", ".join(str(x) for x in weights(move, range(1, 7))), int(round(100.0 * rate(first, np_, 0.8))), ", ".join(str(x) for x in lw),
        ", ".join(str(x) for x in weights(col, range(6))), int(round(100.0 * rate(same, np_, 0.5))), push[0], push[1], push[2], g["name"]), say


def generate(lines):
    genres, scales = parse(lines)
    rules, lns, leads, chords, progs, stats = [], [], [], [], [], []
    arp4 = 0
    doc = [DOC_HEAD]
    for gi, g in genres.items():
        g["index"] = gi
        if gi in HAND:
            continue
        major = bool(scales[scales[g["scales"][0]][1]][0] & (1 << 4))
        kick = g["parts"].get(FUNC["KICK"])
        kick_common = set()
        if kick:
            kf, _ = count(kick["vars"], 0)
            kick_common = {s for s in range(16) if kf[s] >= 0.6}
        doc += ["## %s" % g["name"], "", "| parte | famiglia | base | pieno | in più | |", "| --- | --- | --- | --- | --- | --- |"]
        says = []
        for func, part in g["parts"].items():
            if part["name"] == "CRASH":                           # (the engine has one way with a crash: th_crash)
                continue
            rules += part_rules(g, None, func, part, kick_common, stats, doc)
            if part["kind"] == 2:
                c, say = chord_rule(g, func, part)
                chords.append(c)
                says.append(say)
            elif part["name"] in ("LEAD", "VOX"):
                c, say = lead_rule(g, func, part, major)
                leads.append(c)
                says.append(say)
            elif part["name"] == "ARP":
                nts = [int(v.notes[i], 16) for v in part["vars"] for i, c in enumerate(v.hits) if c in ON]
                four = sum(1 for p in nts if p in (10, 11)) < 0.08 * len(nts)
                if four:
                    arp4 |= 1 << gi
                says.append("ARP: le note dell'accordo in fila%s." % (" (fondamentale, terza, quinta, ottava)" if four else ", con la settima"))
            elif part["kind"] == 1:
                c, say = line_rule(g, func, part)
                lns.append(c)
                says.append(say)
        c, say = prog_rule(g, [scales[x][2] for x in g["scales"]])
        progs.append(c)
        doc += ["", "**Le note.** " + " ".join(says), "", say, ""]
    n_rules = sum(1 for r in rules if r.startswith("    {"))
    out = ["/* SPDX-License-Identifier: GPL-3.0-only",
           " * SAGGA SEQ: the rules of the THEORY engines counted from the library, for the genres that have none written by",
           " * hand. MADE by tools/theory/gen_rules.py (which says what is counted): do not edit, run it again. The suite",
           " * checks that this file is what the library gives. %d rhythm rules, %d lines, %d motifs, %d chord parts, %d genres. */" % (
               n_rules, len(lns), len(leads), len(chords), len(progs)),
           "#ifndef SAGGA_THEORY_DATA_H", "#define SAGGA_THEORY_DATA_H", "",
           "#define TH_DATA_MID_E %du    /* the energy the second half of what a family always plays comes in at */" % MID_E, "",
           "/* a bit a genre: its arpeggios are the triad and the octave (no seventh in them) */",
           "#define TH_DATA_ARP4 0x%08Xu" % arp4, ""]
    for name, body in (("TH_DATA_RULES", rules), ("TH_DATA_LINES", lns), ("TH_DATA_LEADS", leads), ("TH_DATA_CHORDS", chords), ("TH_DATA_PROGS", progs)):
        out.append("#define %s \\" % name)
        out += body
        out += ["", ""]
    out += ["#endif", ""]
    return "\n".join(out), stats, "\n".join(doc)


DOC_HEAD = """# SAGGA SEQ 0.23 - i motori THEORY, genere per genere

Questo foglio lo scrive `tools/theory/gen_rules.py` **contando la libreria dell'FM-1**: non si corregge a mano (la
suite dei test controlla che sia quello che la libreria dà). Dice cosa suonano i motori nei 21 generi le cui regole
sono contate. TECHNO, HOUSE, DRUM+BASS e DUBSTEP hanno regole scritte a mano: sono in `TEORIA.md`, che spiega anche
cosa sono i motori e come si usano.

## Come si legge

Una riga è una **famiglia**: un modo di suonare quella parte in quel genere (un hat in ottavi, un hat in levare). Il
seme ne sceglie una; la percentuale dice quanto spesso.

* **base**: quello che la famiglia suona anche con l'energia a zero.
* **pieno**: quello che suona sempre da energia 25 in su.
* **in più**: i sedicesimi che l'energia aggiunge. Una cifra per sedicesimo, da `1` (raro) a `f` (quasi sempre): a
  energia 50 un sedicesimo segnato `d` c'è una volta su due, a 100 quasi sempre.
* Due righe nella stessa casella: la prima è la battuta, la seconda la sua **risposta** (le battute 2 e 4).
* L'ultima colonna: *chiusura* = l'ultima battuta del pattern si riempie verso l'uno; *rullate* = certi colpi
  diventano rullate; *mai sul kick*, *con il kick* = la parte guarda il kick che suona.

`X` accento, `x` colpo, `o` piano, `g` ghost, `.` niente. Sedici caratteri sono una battuta.

Le **note** sono quelle che la libreria usa in quella parte: i motori le scelgono nelle stesse proporzioni, ma mettono
la fondamentale sull'uno e l'ottava dopo una fondamentale come fa un bassista.
"""


def main():
    text, stats, doc = generate(libdump())
    if "--stats" in sys.argv:
        print("\n".join(stats))
        return 0
    if "--check" in sys.argv:
        bad = 0
        for path, want in ((OUT, text), (DOC, doc)):
            old = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
            if old != want:
                print("gen_rules: %s is not what the library gives: run tools/theory/gen_rules.py" % os.path.relpath(path, ROOT))
                bad = 1
        if not bad:
            print("gen_rules: the counted rules and their sheet are what the library gives (%d and %d bytes)" % (len(text), len(doc)))
        return bad
    for path, want in ((OUT, text), (DOC, doc)):
        with open(path, "w", encoding="utf-8") as f:
            f.write(want)
        print("gen_rules: wrote %s (%d bytes)" % (os.path.relpath(path, ROOT), len(want)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
