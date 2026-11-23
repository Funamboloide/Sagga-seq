#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""0.32.1: every table of the firmware that is declared with a size has that many elements.

C fills what an initializer leaves out with zeros and says nothing: a table of names declared `NAMES[COUNT]` that
keeps its old rows when COUNT grows has null pointers at its end, and nothing fails until something reads them. 0.29
added four chord shapes and the table of the chords' names kept its 32: from 0.29 to 0.32 a USER progression's chord
of one of the four made the FM-1 read its name from address 0.

In a COPY of firmware/src each `name[SIZE] = {...};` becomes `name[] = {...};` followed by a _Static_assert that its
length is SIZE; the copy is then compiled as the simulator and the core are (the syntax only). The compiler says
which tables are short. A table with designators (`[K] = ...`) is listed, not counted: its places are named.

    python3 tests/sagga_tables.py          the check, and the check of the check (a table made short on purpose)
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECL = re.compile(r"\b([A-Za-z_]\w*)[ \t]*\[([^\]\n;{}=]+)\]((?:[ \t]*\[[^\]\n;{}=]*\])*)[ \t]*=[ \t\n]*\{")


def code_map(src):
    """True for the characters that are code: not in a comment, a string or a character literal"""
    code = [True] * len(src)
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
        elif src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j < 0 else j
        elif c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            j += 1
        else:
            i += 1
            continue
        for k in range(i, min(j, n)):
            code[k] = False
        i = j
    return code


def depth_map(src, code):
    """how many braces are open at each character (0: the file's own level, not inside a function)"""
    out, d = [0] * len(src), 0
    for i, ch in enumerate(src):
        if code[i] and ch == "}":
            d -= 1
        out[i] = d
        if code[i] and ch == "{":
            d += 1
    return out


def designated(src, code, a, b):
    """the initializer src[a:b] names its places (`[K] = ...` at its top level)"""
    depth, first = 0, True
    for i in range(a, b):
        if not code[i]:
            continue
        ch = src[i]
        if ch in "{(":
            depth += 1
        elif ch in "})":
            depth -= 1
        elif depth == 0:
            if ch == ",":
                first = True
            elif not ch.isspace():
                if first and ch == "[":
                    return True
                first = False
    return False


def unsize(src, names):
    """a table's earlier declaration with its size (`static const T NAME[SIZE][..];`, an extern in a header) would give
    the array its size whatever the initializer holds: for the tables counted, it loses its first size too"""
    code = code_map(src)
    depth = depth_map(src, code)
    out, pos = [], 0
    for m in re.finditer(r"\b([A-Za-z_]\w*)[ \t]*\[[^\]\n;{}=]+\]((?:[ \t]*\[[^\]\n;{}=]*\])*)[ \t]*;", src):
        if m.group(1) not in names or not code[m.start()] or m.start() < pos or depth[m.start()]:
            continue                                       # (the file's own tables: a function's b[4] is not NAME's)
        head = src[src.rfind("\n", 0, m.start()) + 1:m.start()]
        if not re.match(r"\s*(static|extern|const)\b[\w\s\*]*$", head):
            continue                                       # (an expression, not a declaration)
        out.append(src[pos:m.start()])
        out.append("%s[]%s;" % (m.group(1), m.group(2)))
        pos = m.end()
    out.append(src[pos:])
    return "".join(out)


def rewrite(src, name_of_file, names):
    """-> (the source with every sized table counted by a _Static_assert, how many, the designated ones); names: the
    file's own tables counted (not a function's) are added to it"""
    code = code_map(src)
    level = depth_map(src, code)
    out, pos, n, named = [], 0, 0, []
    for m in DECL.finditer(src):
        if m.start() < pos or not code[m.start()] or not code[m.end() - 1]:
            continue
        head = src[src.rfind("\n", 0, m.start()) + 1:m.start()]
        if "#define" in head or "typedef" in head or "extern" in head or "sizeof" in head:
            continue
        size = m.group(2).strip()
        if re.fullmatch(r"\d+u?", size) and int(size.rstrip("u")) <= 1:
            continue
        i, depth = m.end(), 1                              # the initializer's closing brace
        while depth and i < len(src):
            if code[i]:
                depth += src[i] == "{"
                depth -= src[i] == "}"
            i += 1
        j = i
        while j < len(src) and src[j].isspace():
            j += 1
        if j >= len(src) or src[j] != ";":
            continue                                       # (not a declaration's initializer)
        if src[m.end():i - 1].strip() in ("0", "0u"):
            continue                                       # (`= {0}`: zeros asked for, not a table)
        if designated(src, code, m.end(), i - 1):
            named.append("%s: %s[%s]" % (name_of_file, m.group(1), size))
            continue
        name = m.group(1)
        if not level[m.start()]:
            names.add(name)
        out.append(src[pos:m.start()])
        out.append("%s[]%s = {" % (name, m.group(3)))
        out.append(src[m.end():j + 1])
        out.append(' _Static_assert(sizeof %s / sizeof %s[0] == (%s), "SHORT TABLE %s: %s has not its %s elements");'
                   % (name, name, size, name_of_file, name, size.replace('"', "'")))
        pos = j + 1
        n += 1
    out.append(src[pos:])
    return "".join(out), n, named


def check(work, spoil=None):
    """the firmware's sources copied to `work`, counted and compiled. spoil = (file, text, its replacement): a change
    made to the copy first. -> (tables counted, the short ones, the designated ones, the compiler's other errors)"""
    for d in ("firmware", "tests"):
        if os.path.exists(os.path.join(work, d)):
            shutil.rmtree(os.path.join(work, d))
    shutil.copytree(os.path.join(ROOT, "firmware"), os.path.join(work, "firmware"))
    os.makedirs(os.path.join(work, "tests"))
    for f in os.listdir(os.path.join(ROOT, "tests")):     # (the simulator's host: platform.c includes ../../tests/host.c)
        if f.endswith((".c", ".h")):
            shutil.copy(os.path.join(ROOT, "tests", f), os.path.join(work, "tests", f))
    dst = os.path.join(work, "firmware", "src")
    total, named, names, texts = 0, [], set(), {}
    for f in sorted(os.listdir(dst)):
        if not f.endswith((".c", ".h")):
            continue
        with open(os.path.join(dst, f), encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        if spoil and spoil[0] == f:
            assert src.count(spoil[1]) == 1, (f, spoil[1])
            src = src.replace(spoil[1], spoil[2])
        texts[f], n, nm = rewrite(src, f, names)
        total += n
        named += nm
    for f, src in texts.items():
        with open(os.path.join(dst, f), "w", encoding="utf-8") as fh:
            fh.write(unsize(src, names))
    gen = os.path.join(work, "firmware", "gen")
    builds = [["cc", "-std=gnu11", "-w", "-fsyntax-only", "-DDINGHY_HOST", '-DAPP_VER="test"', "-I" + dst, "-I" + gen, os.path.join(dst, "dinghy.c")]]
    builds += [["cc", "-std=c11", "-w", "-fsyntax-only", "-I" + dst, os.path.join(dst, f)] for f in ("sagga_seq_core.c", "sagga_beats.c", "sagga_theory.c")]
    short, other = set(), []
    for cmd in builds:
        r = subprocess.run(cmd, capture_output=True, text=True)
        for line in r.stderr.splitlines():
            if "error" not in line:
                continue
            m = re.search(r"SHORT TABLE ([^\"']+?) has not its (.+?) elements", line)
            if m:
                short.add("%s [%s]" % (m.group(1), m.group(2)))
            else:
                other.append(line[:240])
    return total, sorted(short), named, other


def main():
    bad = 0
    with tempfile.TemporaryDirectory() as work:
        total, short, named, other = check(work)
        for s in short:
            print("FAIL  a table shorter than its size (the rest is zeros): %s" % s)
        for o in other[:6]:
            print("FAIL  the counted copy does not compile: %s" % o)
        bad += len(short) + len(other)
        if total < 200:
            print("FAIL  only %d tables found: the firmware has more than two hundred" % total)
            bad += 1
        # the check of the check: a name taken from a table of names, a row from a table of rows - each must be found
        probes = 0
        for f, old, new, want in (
                ("sagga_seq_core.c", '"MALI", "DEMBOW", "BROKEN"};', '"MALI", "DEMBOW"};', "sagga_seq_core.c: GROOVE_NAME [SQ_GROOVES]"),
                ("dinghy.c", '"GLIT", "ROLL", "ACC"};', '"GLIT", "ROLL"};', "dinghy.c: MFX_SHORT [SQ_MFXS]"),
                ("sagga_seq_core.c", "    {0, 5, 10, 15, -1, -1},      /* QUARTAL: in fourths, no third */\n", "", "sagga_seq_core.c: CHORD_SEMI [SQ_CH_COUNT]")):
            _, short2, _, other2 = check(work, (f, old, new))
            probes += 1
            if short2 != [want] or other2:
                print("FAIL  a table made short on purpose is not found: %s (%s %s)" % (want, short2, other2[:2]))
                bad += 1
    print("sagga tables: %d tables counted by the compiler (%d with named places: not counted), %d made short on purpose and found, %d failures"
          % (total, len(named), probes, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
