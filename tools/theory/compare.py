#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA SEQ: what the THEORY engines make against the library of the FM-1, a genre and a part at a time.

  python3 tools/theory/compare.py [SEEDS] [GENRE ...]      (SEEDS: 100; no GENRE: all 25)

For every part of a genre's band, made at energy 50 on two bars from SEEDS seeds:
  hits     the hits a bar the library writes, and the ones the engines make
  r        how alike the two are in WHERE the hits fall (1.00: the same 16ths as often)
  near     how many 16ths a made bar is from the nearest bar the library writes, on average
  same     the made bars that are a bar of the library, hit for hit
  bars     how many different bars the engines made
A line ends with "<<" when it is far from the library (r under 0.75, a third more or fewer hits, or 3 16ths from
the nearest written bar): something to listen to, not an error - the engines are not the library.
"""
import collections
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_rules  # noqa: E402

ROOT = gen_rules.ROOT
ON = gen_rules.ON


def tool():
    exe = os.path.join(ROOT, "build", "sagga_theory")
    src = [os.path.join(ROOT, "tools", "theory", "sagga_theory.c"), os.path.join(ROOT, "firmware", "src", "sagga_seq_core.c"),
           os.path.join(ROOT, "firmware", "src", "sagga_beats.c")]
    dep = src + [os.path.join(ROOT, "firmware", "src", f) for f in ("sagga_theory.c", "sagga_theory_data.h", "sagga_theory.h")]
    if not os.path.exists(exe) or any(os.path.getmtime(s) > os.path.getmtime(exe) for s in dep):
        tmp = exe + ".%d" % os.getpid()
        subprocess.check_call(["cc", "-std=c11", "-O2", "-I" + os.path.join(ROOT, "firmware", "src")] + src + ["-o", tmp])
        os.replace(tmp, exe)
    return exe


def onoff(bar):
    return "".join("x" if c in ON else "." for c in bar)


def main():
    args = sys.argv[1:]
    seeds = int(args.pop(0)) if args and args[0].isdigit() else 100
    genres, _ = gen_rules.parse(gen_rules.libdump())
    exe = tool()
    far = total = 0
    for gi, g in genres.items():
        if args and g["name"] not in args and str(gi) not in args:
            continue
        made = collections.OrderedDict()
        for seed in range(1, seeds + 1):
            out = subprocess.run([exe, str(gi), str(seed), "0", "0", "50", "32"], capture_output=True, text=True, check=True).stdout
            for l in out.splitlines():
                if not l.startswith("#"):
                    p, r, _n = l.split("\t")
                    made.setdefault(p, []).append(r)
        print("=== %s (%d seeds, energy 50, two bars)" % (g["name"], seeds))
        for func, part in g["parts"].items():
            if part["name"] not in made or part["name"] == "CRASH":
                continue
            lbars = [onoff(v.hits[i:i + 16]) for v in part["vars"] for i in range(0, len(v.hits), 16)]
            mbars = [onoff(r[i:i + 16]) for r in made[part["name"]] for i in range(0, len(r), 16)]
            lh = sum(b.count("x") for b in lbars) / len(lbars)
            mh = sum(b.count("x") for b in mbars) / len(mbars)
            lp = [sum(1 for b in lbars if b[s] == "x") / len(lbars) for s in range(16)]
            mp = [sum(1 for b in mbars if b[s] == "x") / len(mbars) for s in range(16)]
            ml, mm = sum(lp) / 16, sum(mp) / 16
            cov = sum((a - ml) * (b - mm) for a, b in zip(lp, mp))
            va, vb = sum((a - ml) ** 2 for a in lp), sum((b - mm) ** 2 for b in mp)
            r = cov / (va * vb) ** 0.5 if va and vb else 1.0 if va == vb else 0.0
            ds = [min(sum(1 for x, y in zip(b, l) if x != y) for l in set(lbars)) for b in mbars]
            near = sum(ds) / len(ds)
            flag = r < 0.75 or mh > lh * 1.34 + 0.3 or mh < lh / 1.34 - 0.3 or near >= 3.0
            far += flag
            total += 1
            print("%-9s hits %4.1f / %4.1f   r %.2f   near %.1f   same %3d%%   bars %3d%s" % (
                part["name"], lh, mh, r, near, round(100.0 * sum(1 for d in ds if d == 0) / len(ds)), len(set(mbars)), "   <<" if flag else ""))
    print("%d parts, %d far from the library" % (total, far))
    return 0


if __name__ == "__main__":
    sys.exit(main())
