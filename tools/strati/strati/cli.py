# SPDX-License-Identifier: GPL-3.0-only
"""strati: from samples and stems to synth patches.

    python3 -m strati convert FOLDER [--out OUT] [--budget SECONDS] [--targets surge,norns,relitto]
    python3 -m strati send FILE.syx [--port NAME] [--slot 0-3]        (to the FM-1, over USB-MIDI)
    python3 -m strati pad FILE [--start S] [--length S] [--name NAME] [--out OUT]

FOLDER holds the sounds (wav, mp3, flac, aiff, ogg), in any sub-folders. A sub-folder may say what is in it:
    one-shot/   (or oneshot/, hits/, drums/)   every file is one sound
    stems/      (or loops/)                   every file is cut into its sounds, the different ones become patches
    anything else: a file under 3 s is one sound, a longer one a stem
OUT (default FOLDER/patches) gets, per sound:
    recipes/<name>.json        what the analysis heard (the layers): every target is made from it
    preview/<name>-recipe.wav  the recipe played back (how much of the sound the layers hold)
    relitto/<name>.syx         the Relitto sound (a USER table + its parameters: python3 -m strati send it)
    relitto/<name>.txt         the same as knob values, page by page
    preview/<name>-relitto.wav that sound played by Relitto's own engine (the real one, in host mode)
    surge/<name>.fxp           the Surge XT patch (Zynthian)
    preview/<name>-surge.wav   this tool's model of that patch (the real check: the patch in Surge)
    norns/<name>.strati        a sound for the strati script on Norns (norns/strati in this folder)
    preview/<name>-norns.wav   that sound as the script's engine plays it (the same model, in Python)
and report.json / report.txt: every sound, its layers, and how close each step got (dB, lower is closer)."""
import argparse
import json
import os
import sys
import time

import numpy as np

from . import analysis, audio, norns, render, surge
from . import relitto as rl
from .refine import refine

AUDIO = (".wav", ".mp3", ".flac", ".aif", ".aiff", ".ogg", ".m4a")
ONE_SHOT_DIRS = {"one-shot", "oneshot", "one_shot", "hits", "drums", "one-shots"}
STEM_DIRS = {"stems", "stem", "loops"}


def find_sounds(folder):
    """(path, kind) for every audio file; kind 'one' / 'stem' / 'auto' from the folder names"""
    out = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if d not in ("patches",) and not d.startswith("."))
        parts = {p.lower() for p in os.path.relpath(root, folder).split(os.sep)}
        kind = "one" if parts & ONE_SHOT_DIRS else "stem" if parts & STEM_DIRS else "auto"
        for f in sorted(files):
            if f.lower().endswith(AUDIO) and not f.startswith("."):
                out.append((os.path.join(root, f), kind))
    return out


def safe_name(s):
    keep = "".join(c if c.isalnum() or c in "-_" else "-" for c in s)
    return keep.strip("-")[:40] or "sound"


SURGE_KNOBS = [
    (("scenes", "A", "amp_eg", "attack"), 1.0, -8.0, 5.0),
    (("scenes", "A", "amp_eg", "decay"), 1.0, -8.0, 5.0),
    (("scenes", "A", "amp_eg", "sustain"), 0.2, 0.0, 1.0),
    (("scenes", "A", "morph_eg", "decay"), 1.0, -8.0, 5.0),
    (("scenes", "B", "level"), 0.15, 0.0, 1.0),         # (the noise's level: only when there is a noise layer)
    (("scenes", "B", "amp_eg", "attack"), 1.0, -8.0, 5.0),
    (("scenes", "B", "amp_eg", "decay"), 1.0, -8.0, 5.0),
    (("scenes", "B", "amp_eg", "sustain"), 0.2, 0.0, 1.0),
    (("scenes", "B", "cutoff"), 6.0, -60.0, 70.0),
    (("scenes", "B", "envmod"), 6.0, -96.0, 96.0),
    (("scenes", "B", "filter_eg", "decay"), 1.0, -8.0, 5.0),
    (("scenes", "B", "color"), 0.25, -1.0, 1.0),
]


TARGETS = ("surge", "norns", "relitto")


def relitto_exe(targets, log=print):
    """the host build of Relitto when it is wanted and its source is there (else the target is skipped, said once)"""
    if "relitto" not in targets:
        return None
    try:
        exe = rl.host_binary()
    except RuntimeError as e:
        log(str(e))
        return None
    if not exe:
        log("relitto: no source found (STRATI_RELITTO=/path/to/relitto): skipped")
    return exe


def relitto_out(rec, src, exe, out, name, budget, entry, log):
    """the Relitto sound: refined against the original by the real engine, the SysEx, the sheet, the preview"""
    pl = rl.plan(rec)
    best, score, start = rl.refine(pl, exe, src, budget=budget, gate=pl["gate"])
    rl.write_syx(best, os.path.join(out, "relitto", name + ".syx"))
    with open(os.path.join(out, "relitto", name + ".txt"), "w") as f:
        f.write(rl.sheet(best))
    y, _ = rl.render(best, exe, gate=pl["gate"], dur=len(src) / audio.SR + 0.5)
    audio.save(os.path.join(out, "preview", name + "-relitto.wav"), y)
    entry.update(relitto_db_start=round(start, 2), relitto_db=round(score, 2), relitto_b=best["b_source"], relitto_notes=best["notes"])
    return best


def convert(folder, out=None, budget=30.0, targets=TARGETS, log=print):
    out = out or os.path.join(folder, "patches")
    exe = relitto_exe(targets, log)
    targets = tuple(t for t in targets if t != "relitto" or exe)
    for d in ("recipes", "preview") + tuple(targets):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    report = []
    for path, kind in find_sounds(folder):
        t0 = time.time()
        base = safe_name(os.path.splitext(os.path.basename(path))[0])
        try:
            x = audio.load(path)
        except Exception as e:                          # (a file ffmpeg cannot read: said, and the next one)
            report.append(dict(file=path, error=str(e)))
            log("%s: cannot read (%s)" % (path, e))
            continue
        if kind == "one" or (kind == "auto" and len(x) < 3.0 * audio.SR):
            on = analysis.onsets(x)
            s = on[0] if on else 0
            try:
                rec = analysis.analyse_sound(x[s:], base)
                rec["source"] = [int(s), len(x)]
                recipes = [rec]
            except ValueError:
                recipes = []
        else:
            recipes = analysis.analyse_file(x, base)
        for i, rec in enumerate(recipes):
            name = rec["name"]
            s, e = rec["source"]
            src = x[s:e][:int(6.0 * audio.SR)]
            with open(os.path.join(out, "recipes", name + ".json"), "w") as f:
                json.dump(rec, f)
            ref = render.render(rec)
            audio.save(os.path.join(out, "preview", name + "-recipe.wav"), ref)
            entry = dict(file=path, name=name, pitched=rec["pitched"], modal=rec.get("modal", False),
                         note=rec["midi"] and round(rec["midi"], 2), f0=round(rec["f0"], 2), duration=round(rec["duration"], 3),
                         mix=rec["mix"], recipe_db=round(render.distance(src, ref), 2))
            if "surge" in targets:
                p = surge.plan(rec)
                f0 = rec["f0"] if rec["f0"] > 0 else 261.63
                sim = lambda q: surge.simulate(q, f0, rec["duration"])
                p2, score, start = refine(p, src, sim, SURGE_KNOBS, budget=budget)
                xml, wts, trail = surge.build_xml_and_tables(p2)
                surge.write_fxp(os.path.join(out, "surge", name + ".fxp"), p2["name"], xml, wts, trail)
                audio.save(os.path.join(out, "preview", name + "-surge.wav"), sim(p2))
                entry.update(surge_db_start=round(start, 2), surge_db=round(score, 2), surge_layers=sorted(p2["scenes"]),
                             surge_tonal=p2["scenes"].get("A", {}).get("kind"))
            if "norns" in targets:
                red = norns.reduce(rec)
                norns.write(red, os.path.join(out, "norns", name + ".strati"))
                y = norns.simulate(red)
                audio.save(os.path.join(out, "preview", name + "-norns.wav"), y)
                entry["norns_db"] = round(render.distance(src, y), 2)
            if "relitto" in targets:
                relitto_out(rec, src, exe, out, name, budget, entry, log)
            entry["seconds"] = round(time.time() - t0, 1)
            report.append(entry)
            log("%-28s %-10s recipe %.1f dB  surge %s dB  norns %s dB  relitto %s dB  (%.0f s)" % (
                name, ("note %.1f" % rec["midi"]) if rec["midi"] else "no pitch", entry["recipe_db"],
                entry.get("surge_db", "-"), entry.get("norns_db", "-"), entry.get("relitto_db", "-"), entry["seconds"]))
    with open(os.path.join(out, "report.json"), "w") as f:
        json.dump(report, f, indent=1)
    with open(os.path.join(out, "report.txt"), "w") as f:
        f.write("strati: %d sounds\n(dB: how far from the original; ~3 close, over ~10 another sound)\n\n" % len(report))
        for e in report:
            if "error" in e:
                f.write("%s: %s\n" % (e["file"], e["error"]))
                continue
            f.write("%-28s %-10s mix t%.2f n%.2f  recipe %5.1f dB  surge %s dB (from %s)  norns %s dB  relitto %s dB (from %s)\n" % (
                e["name"], ("note %.1f" % e["note"]) if e["note"] else "no pitch", e["mix"]["tonal"], e["mix"]["noise"],
                e["recipe_db"], e.get("surge_db", "-"), e.get("surge_db_start", "-"), e.get("norns_db", "-"),
                e.get("relitto_db", "-"), e.get("relitto_db_start", "-")))
    return report


def pad_convert(path, out=None, name=None, start=None, length=None, log=print, budget=30.0):
    """a pad (a held, chordal part with a noise bed) out of a recording: the patches (Norns, Surge XT, a Dexed bank
    for MicroDexed-touch and Zynthian), the original performance (notes and the noise control) and previews of it
    played by each patch (in its model), at the original's loudness"""
    from . import dexed, pad, perf
    x = audio.load(path)
    if start is not None or length is not None:
        a = int((start or 0.0) * audio.SR)
        x = x[a:a + int(length * audio.SR)] if length else x[a:]
    base = safe_name(name or os.path.splitext(os.path.basename(path))[0])
    out = out or os.path.join(os.path.dirname(os.path.abspath(path)), "patches")
    exe = relitto_exe(("relitto",), log)
    for d in ("norns", "surge", "dexed", "preview", "recipes") + (("relitto",) if exe else ()):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    p = pad.analyse_pad(x)
    rec = pad.voice_recipe(p, name=base)
    pf = pad.performance(p)
    with open(os.path.join(out, "recipes", base + ".json"), "w") as f:
        json.dump(rec, f)
    with open(os.path.join(out, "recipes", base + "-performance.json"), "w") as f:
        json.dump(pf, f)
    red = norns.reduce(rec)
    norns.write(red, os.path.join(out, "norns", base + ".strati"))
    sp = surge.plan(rec)
    xml, wts, trail = surge.build_xml_and_tables(sp)
    surge.write_fxp(os.path.join(out, "surge", base + ".fxp"), sp["name"], xml, wts, trail)
    dv = dexed.make_voice(rec, base)
    dexed.write_bank([dv], os.path.join(out, "dexed", base + ".syx"))
    rep = dict(file=path, name=base, tuning_cents=round(p["cents"], 1), root=round(rec["midi"], 2),
               chords=[(round(a, 2), round(b, 2), n) for a, b, n in pad.chords(p)], dexed_fit_db=round(dv["fit_db"], 2))
    hx = perf.highpass(x)
    for k, v in (("norns", perf.norns_voice(red, p["cents"])), ("surge", perf.surge_voice(sp, p["cents"])),
                 ("dexed", perf.dexed_voice(dv, p["cents"]))):
        y = perf.match_level(perf.play(pf, v), x)
        y = y / max(np.abs(y).max() / 0.89, 1.0)
        audio.save(os.path.join(out, "preview", "%s-%s.wav" % (base, k)), y)
        rep["%s_db" % k] = round(render.distance(hx, perf.highpass(y)[:len(x)]), 2)
        log("%-24s %-6s %.1f dB" % (base, k, rep["%s_db" % k]))
    if exe:                                         # Relitto: the sound, then the performance by the real engine (8 voices)
        pl = rl.plan(rec)
        rl.write_syx(pl, os.path.join(out, "relitto", base + ".syx"))
        with open(os.path.join(out, "relitto", base + ".txt"), "w") as f:
            f.write(rl.sheet(pl))
        y = perf.match_level(rl.play_performance(pl, exe, pf), x)
        y = y / max(np.abs(y).max() / 0.89, 1.0)
        audio.save(os.path.join(out, "preview", "%s-relitto.wav" % base), y)
        rep["relitto_db"] = round(render.distance(hx, perf.highpass(y)[:len(x)]), 2)
        log("%-24s %-6s %.1f dB" % (base, "relitto", rep["relitto_db"]))
    with open(os.path.join(out, base + "-pad-report.json"), "w") as f:
        json.dump(rep, f, indent=1)
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(prog="strati", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert", help="a folder of sounds -> recipes, previews, patches")
    c.add_argument("folder")
    c.add_argument("--out")
    c.add_argument("--budget", type=float, default=30.0, help="seconds of trial and error per sound and target")
    c.add_argument("--targets", default=",".join(TARGETS), help="any of: " + ", ".join(TARGETS))
    sd = sub.add_parser("send", help="a Relitto .syx to the FM-1 over USB-MIDI (needs mido and python-rtmidi)")
    sd.add_argument("file")
    sd.add_argument("--port", help="part of the FM-1's MIDI port name (default: Felucca / FM-1)")
    sd.add_argument("--slot", type=int, default=None, help="USER slot 0-3 (default: as in the file)")
    q = sub.add_parser("pad", help="a pad out of a recording -> patches, its performance, previews")
    q.add_argument("file")
    q.add_argument("--out")
    q.add_argument("--name")
    q.add_argument("--start", type=float, help="from this second")
    q.add_argument("--length", type=float, help="this many seconds")
    q.add_argument("--budget", type=float, default=30.0)
    a = ap.parse_args(argv)
    if a.cmd == "pad":
        pad_convert(a.file, a.out, a.name, a.start, a.length, budget=a.budget)
        return 0
    if a.cmd == "send":
        from .send import send_file
        return send_file(a.file, a.port, a.slot)
    if a.cmd == "convert":
        targets = tuple(t for t in a.targets.split(",") if t)
        bad = [t for t in targets if t not in TARGETS]
        if bad:
            ap.error("unknown target: %s" % ", ".join(bad))
        convert(a.folder, a.out, a.budget, targets)
    return 0


if __name__ == "__main__":
    sys.exit(main())
