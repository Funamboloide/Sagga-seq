#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""strati tests: the analysis on sounds made here (their notes, layers and envelopes are known), the recipe played
back, the Surge XT patch written and read back, the trial and error, the folder conversion. Needs numpy, scipy,
ffmpeg (for loading files). No Surge: the patch is checked as a file (the sound is checked on the Pi).

    python3 tests/strati_tests.py            (from the repository root)
"""
import os
import re
import struct
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'strati'))
from strati import analysis, audio, cli, dexed, norns, perf, render, surge
from strati import pad as padmod     # noqa: E402
from strati import relitto as rl, send as rlsend    # noqa: E402
from strati.refine import refine                          # noqa: E402

SR = audio.SR
OK = [0]
FAIL = []


def check(cond, what):
    if cond:
        OK[0] += 1
    else:
        FAIL.append(what)
        print('FAIL', what)


T = np.arange(int(SR * 1.5)) / SR
RNG = np.random.default_rng(7)


def pluck(f=220.0):
    x = sum(np.sin(2 * np.pi * f * k * T) / k * np.exp(-T * (3 + k)) for k in range(1, 30))
    return x * np.minimum(1, T / 0.003)


def snare():
    from scipy.signal import lfilter
    tone = np.sin(2 * np.pi * 185 * T) * np.exp(-T * 25) + 0.5 * np.sin(2 * np.pi * 330 * T) * np.exp(-T * 30)
    n = lfilter([1, -0.5], [1], RNG.standard_normal(len(T))) * np.exp(-T * 14) * 0.5
    return (tone + n) * np.minimum(1, T / 0.001)


def pad(f=146.83):
    env = np.minimum(1, T / 0.35)
    return sum(np.sin(2 * np.pi * f * k * T) / k ** 1.5 for k in range(1, 20)) * env


def t_analysis():
    r = analysis.analyse_sound(pluck(), 'pluck')
    check(r['pitched'] and abs(r['midi'] - 57.0) < 0.05, 'pluck: note A3 (%s)' % r['midi'])
    check(abs(r['ratios'][0] - 1.0) < 0.003 and abs(r['ratios'][2] - 3.0) < 0.01, 'pluck: harmonic ratios %s' % r['ratios'][:3])
    check(r['mix']['tonal'] > 0.95 and r['mix']['noise'] < 0.15, 'pluck: tonal %s' % r['mix'])
    check(r['adsr_tonal']['attack'] < 0.015 and r['adsr_tonal']['sustain'] < 0.05, 'pluck: fast attack, no sustain %s' % r['adsr_tonal'])
    r = analysis.analyse_sound(snare(), 'snare')
    check(not r['pitched'] and r['modal'], 'snare: modes, no pitch')
    check(abs(r['f0'] - 185.0) < 3.0, 'snare: lowest mode 185 Hz (%s)' % r['f0'])
    check(r['mix']['noise'] > 0.3 and r['mix']['tonal'] > 0.3, 'snare: both layers %s' % r['mix'])
    r = analysis.analyse_sound(pad(), 'pad')
    check(r['pitched'] and abs(r['midi'] - 50.0) < 0.05, 'pad: note D3')
    check(0.2 < r['adsr_tonal']['attack'] < 0.5 and r['adsr_tonal']['sustain'] > 0.8, 'pad: slow attack, sustain %s' % r['adsr_tonal'])
    n = RNG.standard_normal(SR)
    r = analysis.analyse_sound(n, 'noise')
    check(not r['pitched'] and r['mix']['tonal'] < 0.05, 'white noise: noise only')
    try:
        analysis.analyse_sound(np.zeros(SR), 'z')
        check(False, 'silence refused')
    except ValueError:
        check(True, '')


def t_stem():
    gap = np.zeros(int(0.25 * SR))
    hit = pluck()[:int(0.4 * SR)]
    sn = snare()[:int(0.4 * SR)]
    x = np.concatenate([hit, gap, sn, gap, hit, gap, sn, gap, pluck(330.0)[:int(0.4 * SR)], gap])
    on = analysis.onsets(x)
    check(len(on) == 5, 'stem: 5 onsets (%d)' % len(on))
    recs = analysis.analyse_file(x, 'stem')
    check(len(recs) == 3, 'stem: 3 different sounds (%d)' % len(recs))
    check(all('source' in r and r['source'][1] > r['source'][0] for r in recs), 'stem: every recipe knows its place')
    notes = sorted(round(r['midi']) for r in recs if r['pitched'])
    check(notes == [57, 64], 'stem: the two plucks A3 E4 %s' % notes)


def t_render():
    for name, x in (('pluck', pluck()), ('snare', snare()), ('pad', pad())):
        r = analysis.analyse_sound(x, name)
        y = render.render(r)
        d = render.distance(x, y)
        check(d < 4.0, '%s: the recipe sounds like it (%.2f dB)' % (name, d))
        check(render.distance(x, RNG.standard_normal(len(x))) > 12.0, '%s: noise does not' % name)
    # the noise layer's loudness: white noise in, the same rms out (within 2 dB)
    n = RNG.standard_normal(SR) * 0.1
    r = analysis.analyse_sound(n, 'n')
    y = render.render(r)
    nn = n / np.abs(n).max()
    g = 20 * np.log10(np.sqrt(np.mean(y[:SR] ** 2)) / np.sqrt(np.mean(nn ** 2)))
    check(abs(g) < 2.0, 'noise rendered at its level (%.1f dB)' % g)
    # another note: the harmonics follow
    r = analysis.analyse_sound(pluck(), 'p')
    y = render.render(r, f0=440.0)
    rr = analysis.analyse_sound(y, 'p2')
    check(abs(rr['midi'] - 69.0) < 0.1, 'recipe played an octave up (%s)' % rr['midi'])
    check(render.distance(pluck(), pluck()) < 1e-6, 'distance to itself 0')


def t_surge():
    with tempfile.TemporaryDirectory() as d:
        for name, x in (('pluck', pluck()), ('snare', snare()), ('pad', pad())):
            r = analysis.analyse_sound(x, name)
            path = os.path.join(d, name + '.fxp')
            p = surge.write_patch(r, path)
            raw = open(path, 'rb').read()
            check(raw[:4] == b'CcnK' and raw[8:12] == b'FPCh', '%s: an fxp' % name)
            check(struct.unpack('>I', raw[16:20])[0] == 0x63786533, '%s: for Surge XT' % name)
            nm, xml, wts, _ = surge.read_fxp(path)
            check(nm.startswith(name), '%s: its name' % name)
            check('category="STRATI"' in xml, '%s: category' % name)
            both = 'A' in p['scenes'] and 'B' in p['scenes']
            check(int(surge.get_param(xml, 'scenemode')) == (2 if both else 0), '%s: dual scene when two layers' % name)
            if p['scenes'].get('A', {}).get('kind') == 'wavetable':
                check(wts[0] is not None and wts[0][0] == surge.WT_SAMPLES and wts[0][1] == surge.WT_FRAMES, '%s: its wavetable' % name)
                check(int(surge.get_param(xml, 'a_osc1_type')) == surge.OT_WAVETABLE, '%s: osc 1 a wavetable' % name)
                check('source="16"' in xml, '%s: the morph on the filter EG' % name)
            for i, w in enumerate(wts):
                sc, o = 'ab'[i // 3], i % 3 + 1
                if int(surge.get_param(xml, '%s_osc%d_type' % (sc, o))) != surge.OT_WAVETABLE:
                    check(w is None, '%s: no table on a non-wavetable osc' % name)
            a = float(surge.get_param(xml, 'a_env2_attack'))
            check(-8.0 <= a <= 5.0, '%s: attack in range' % name)
        r = analysis.analyse_sound(pluck(), 'pluck')
        p = surge.plan(r)
        check(p['scenes']['A']['kind'] == 'wavetable' and 'B' not in p['scenes'], 'pluck: one wavetable, no noise layer')
        check(p['root_note'] == 57, 'pluck: root note A3')
        r = analysis.analyse_sound(snare(), 'snare')
        p = surge.plan(r)
        check(p['scenes']['A']['kind'] == 'modes' and 'B' in p['scenes'], 'snare: sine modes + a noise layer')


def t_refine():
    r = analysis.analyse_sound(snare(), 'snare')
    p = surge.plan(r)
    bad = dict(p, scenes=dict(p['scenes']))
    import copy
    bad = copy.deepcopy(p)
    bad['scenes']['B']['amp_eg']['decay'] = 3.0                # (a noise that rings 8 s: wrong)
    sim = lambda q: surge.simulate(q, r['f0'], r['duration'])
    best, score, start = refine(bad, snare(), sim, cli.SURGE_KNOBS, budget=20.0)
    check(score < start - 1.0, 'refine: better (%.2f -> %.2f)' % (start, score))
    check(best['scenes']['B']['amp_eg']['decay'] < 1.0, 'refine: the decay comes back (%.2f)' % best['scenes']['B']['amp_eg']['decay'])


def t_norns():
    with tempfile.TemporaryDirectory() as d:
        for name, x, lim in (('pluck', pluck(), 4.0), ('snare', snare(), 5.0), ('pad', pad(), 4.0)):
            r = analysis.analyse_sound(x, name)
            red = norns.reduce(r)
            check(len(red['seg']) == norns.N_POINTS - 1 and all(v > 0 for v in red['seg']), '%s: 11 times' % name)
            check(abs(sum(red['seg']) - r['times'][-1]) < 1e-6, '%s: to the end' % name)
            check(red['sines'].shape == (24, 12) and red['gains'].shape == (24, 12), '%s: 24 x 12' % name)
            check(np.all(red['sines'] >= 0) and np.all(red['gains'] >= 0), '%s: no negative level' % name)
            y = norns.simulate(red)
            dd = render.distance(x, y)
            check(dd < lim, '%s: the Norns voice sounds like it (%.2f dB)' % (name, dd))
            path = os.path.join(d, name + '.strati')
            norns.write(red, path)
            back = norns.read(path)
            check(np.allclose(back['sines'], red['sines'], rtol=1e-5, atol=1e-9) and np.allclose(back['gains'], red['gains'], rtol=1e-5, atol=1e-9), '%s: file read back' % name)
            lines = open(path).read().split('\n')
            check(lines[0] == 'strati 1' and [len(l.split()) for l in lines[2:8]] == [2, 11, 24, 288, 25, 288], '%s: the lines the engine reads' % name)
            check(abs(back['root'] - (r['midi'] or 60.0)) < 1e-4, '%s: root' % name)
        # the noise at its level (white noise in: the same rms out, within 2 dB)
        n = RNG.standard_normal(SR) * 0.1
        red = norns.reduce(analysis.analyse_sound(n, 'n'))
        y = norns.simulate(red)
        nn = n / np.abs(n).max()
        g = 20 * np.log10(np.sqrt(np.mean(y[:SR // 2] ** 2)) / np.sqrt(np.mean(nn[:SR // 2] ** 2)))
        check(abs(g) < 2.0, 'norns: noise at its level (%.1f dB)' % g)
        # the sines follow the note, the noise stays
        r = analysis.analyse_sound(pluck(), 'p')
        y = norns.simulate(norns.reduce(r), note=r['midi'] + 12)
        check(abs(analysis.analyse_sound(y, 'q')['midi'] - 69.0) < 0.1, 'norns: an octave up')
    # the engine and the script agree with the file
    eng = open(os.path.join(ROOT, 'tools', 'strati', 'norns', 'strati', 'lib', 'Engine_Strati.sc')).read()
    check('nSines = %d, nBands = %d, nPts = %d' % (norns.N_SINES, len(norns.BAND_CENTRES), norns.N_POINTS) in eng, 'engine: sizes as the file')
    check('lines[0] != "strati 1"' in eng, 'engine: checks the version')
    for c in ('(', '[', '{'):
        pair = {'(': ')', '[': ']', '{': '}'}[c]
        check(eng.count(c) == eng.count(pair), 'engine: %s%s balanced' % (c, pair))
    lua = open(os.path.join(ROOT, 'tools', 'strati', 'norns', 'strati', 'strati.lua')).read()
    check('engine.name = "Strati"' in lua, 'script: its engine')
    for cmd in ('load', 'select', 'noteOn', 'noteOff', 'allOff', 'amp', 'follow', 'poly', 'pan'):
        check(('\\%s,' % cmd) in eng and ('engine.%s(' % cmd) in lua, 'engine and script: %s' % cmd)


def pad_song():
    """a made-up pad: three chords of two detuned saws per note, over a noise bed that closes (quieter) and
    reopens, at -20 cents (a record not at 440)"""
    from scipy.signal import lfilter
    dur = 12.0
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    plan = [(0.0, 4.0, (57, 60, 64)), (4.0, 8.0, (55, 59, 62, 65)), (8.0, 12.0, (53, 57, 60))]
    for a, b, notes in plan:
        sel = (t >= a) & (t < b)
        g = np.clip((t - a) / 0.3, 0, 1) * np.clip((b - t) / 0.2, 0, 1) * sel
        for m in notes:
            for d in (-10, 10):
                f = 440 * 2 ** ((m - 69 - 0.2) / 12 + d / 1200)
                x += g * sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 12)) * 0.05
    ctrl = np.where(t < 9.0, 1 - t / 9.0 * 0.8, 1.0)
    nz = lfilter([1, -0.3], [1], RNG.standard_normal(n)) * 0.04 * ctrl
    return x + nz, plan, ctrl


def t_pad():
    x, plan, ctrl = pad_song()
    p = padmod.analyse_pad(x)
    check(abs(p['cents'] + 20) < 4, 'pad: tuning -20 cents (%.1f)' % p['cents'])
    ch = padmod.chords(p)
    got = [set(n) for a, b, n in ch if b - a > 2.0]
    want = [set(n) for a, b, n in plan]
    hits = sum(1 for w in want if any(len(w & g) >= len(w) - 1 and len(g - w) <= 1 for g in got))
    check(hits == 3, 'pad: the 3 chords (%s)' % [sorted(g) for g in got])
    prof = p['voices']['pad']['profile']
    check(0.3 < prof[1] < 0.75 and prof[2] < prof[1], 'pad: a saw-like profile %s' % np.round(prof[:4], 2))
    c = padmod.noise_control(p)
    v = np.interp([1.0, 8.5, 10.5], c['times'], c['value'])
    check(v[0] > v[1] + 0.3 and v[2] > v[1] + 0.3, 'pad: the noise closes and reopens %s' % np.round(v, 2))
    rec = padmod.voice_recipe(p, name='test pad')
    check(rec['held'] and rec['control'] == 'noise' and rec['unison_cents'] > 0, 'pad: a held recipe with its control')
    # Norns: the control line, 24 sines as 12 detuned pairs
    red = norns.reduce(rec)
    check(red.get('control') and len(red['control']) == 3, 'pad norns: noise control')
    check(abs(red['ratios'][1] / red['ratios'][0] - 2 ** (20 / 1200)) < 1e-6, 'pad norns: detuned pairs')
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, 'p.strati')
        norns.write(red, path)
        back = norns.read(path)
        check(back.get('control') == red['control'], 'pad norns: control read back')
        y_open = norns.simulate(red, gate=1.0, ctrl=1.0, parts=True)[1]
        y_shut = norns.simulate(red, gate=1.0, ctrl=0.0, parts=True)[1]
        g = 20 * np.log10(np.sqrt(np.mean(y_shut ** 2)) / np.sqrt(np.mean(y_open ** 2)))
        check(g < -12, 'pad norns: wheel down, noise down (%.1f dB)' % g)
        # Surge: unison, the wheel on the noise's level and cutoff
        sp = surge.plan(rec)
        xml, wts, tr = surge.build_xml_and_tables(sp)
        fx = os.path.join(d, 'p.fxp')
        surge.write_fxp(fx, sp['name'], xml, wts, tr)
        _, xml2, _, _ = surge.read_fxp(fx)
        check(int(surge.get_param(xml2, 'a_osc1_param6')) == 2 and abs(surge.get_param(xml2, 'a_osc1_param5') - 0.1) < 1e-6, 'pad surge: 2 voices, 10 cents')
        check(xml2.count('modrouting source="6"') == 2, 'pad surge: the mod wheel twice (level, cutoff)')
        check(int(surge.get_param(xml2, 'scenemode')) == 2, 'pad surge: dual')
        # Dexed: the bank, read back
        dv = dexed.make_voice(rec, 'test pad')
        check(dv['fit_db'] < 5.0, 'pad dexed: the profile fitted (%.1f dB)' % dv['fit_db'])
        sx = os.path.join(d, 'p.syx')
        dexed.write_bank([dv], sx)
        check(os.path.getsize(sx) == 4104, 'dexed: a 32-voice bank')
        b = dexed.read_bank(sx)
        check(b[0]['name'].strip() == 'TEST PAD' and b[0]['algorithm'] == 4, 'dexed: name, algorithm 5')
        check([o['ol'] for o in b[0]['ops']] == [o['ol'] for o in dv['ops']], 'dexed: levels read back')
        check([o['coarse'] for o in b[0]['ops']] == [o['coarse'] for o in dv['ops']], 'dexed: ratios read back')
        check(b[1]['name'] == 'INIT VOICE', 'dexed: the rest INIT')
    for m, idx in ((1, 0.0), (1, 1.0), (2, 1.5)):
        h = dexed.fm_harmonics(m, idx, 8)
        if idx == 0:
            check(abs(h[0] - 1) < 1e-9 and h[1:].max() < 1e-9, 'fm: no index, a sine')
        else:
            from scipy.special import jv
            # (the fundamental: J0 at 1, plus what folds over from -1: J-2 for m = 1, J-1 for m = 2, sign turned)
            want1 = abs(jv(0, idx) - jv(-2, idx)) if m == 1 else abs(jv(0, idx) - jv(-1, idx))
            check(abs(h[0] - want1) < 1e-9, 'fm: m=%d I=%.1f fundamental' % (m, idx))
    check(abs(dexed.rate_time(50) - 1.486) < 0.01, 'dexed: rate 50 -> 1.5 s')
    # the performance through a patch, at the original's loudness
    pf = padmod.performance(p)
    check(len(pf['notes']) >= 8, 'pad: the notes (%d)' % len(pf['notes']))
    y = perf.match_level(perf.play(pf, perf.norns_voice(red, p['cents'])), x)
    dd = render.distance(perf.highpass(x), perf.highpass(y)[:len(x)])
    check(dd < 8.0, 'pad: Norns plays it close (%.1f dB)' % dd)


def kick():
    t = T
    ph = 2 * np.pi * np.cumsum(50 * 2 ** (24 * np.exp(-t / 0.05) / 12)) / SR
    return np.sin(ph) * np.exp(-t / 0.25) * np.minimum(1, t / 0.002)


def t_pitch_env():
    r = analysis.analyse_sound(kick(), 'kick')
    pe = r['pitch_env']
    check(pe is not None and 18 < pe['semitones'] < 36 and 0.03 < pe['decay'] < 0.08, 'kick: the pitch falls ~24 st in ~50 ms (%s)' % pe)
    check(abs(r['f0'] - 50) < 2, 'kick: the note is where it lands (%.1f)' % r['f0'])
    check(r['mix']['noise'] < 0.2, 'kick: the sweep is not noise (%.2f)' % r['mix']['noise'])
    d = render.distance(kick(), render.render(r))
    check(d < 4.0, 'kick: the recipe sweeps too (%.2f dB)' % d)
    check(analysis.analyse_sound(pluck(), 'p')['pitch_env'] is None, 'pluck: no pitch envelope')


def t_relitto():
    rd = rl.find_relitto()
    # the parameters as the firmware has them (when its source is there)
    if rd:
        eng = open(os.path.join(rd, 'firmware', 'src', 'engine.c')).read()
        enum = eng[eng.index('enum {\n    P_A_TAB'):eng.index('    NP\n};')]
        order = [w.strip() for line in enum.split('\n')[1:] for w in line.split('/*')[0].split(',') if w.strip().startswith('P_')]
        check([n for n, m, d, c in rl.PARAMS] == [o[2:] for o in order], 'relitto: the parameters in the engine\'s order')
        src = open(os.path.join(rd, 'firmware', 'src', 'relitto.c')).read()
        for n, m, d, c in rl.PARAMS:
            got = re.search(r'\[P_%s\] = \{"[^"]*", ([^,]+), (\d+), (\d+), K_\w+\}' % n, src)
            check(got is not None and int(got.group(2)) == d and int(got.group(3)) == c, 'relitto: %s default %d CC %d' % (n, d, c))
        wt = open(os.path.join(rd, 'firmware', 'gen', 'relitto_wt.h')).read()
        check('#define WT_SIZE %du' % rl.WT_SIZE in wt and '#define WT_N %du' % rl.WT_N in wt, 'relitto: the table format')
    # the table: a saw's frames bake to a saw at level 0
    h = np.arange(1, rl.NH + 1)
    saw = np.repeat((2 / (np.pi * h))[None, :], 16, axis=0)
    data, rms = rl.bake(rl.spec_frames_from_amps(saw, list(range(1, rl.NH + 1)), phases=np.zeros(rl.NH)))
    check(data.shape == (rl.WT_SIZE,) and data.dtype == np.int16 and np.abs(data).max() <= 32000, 'bake: int16, in range')
    f0 = data[:512].astype(float)
    sp = np.abs(np.fft.rfft(f0)) / 256
    check(abs(sp[2] / sp[1] - 0.5) < 0.05 and abs(sp[3] / sp[1] - 1 / 3) < 0.05, 'bake: the saw\'s harmonics (%.2f %.2f)' % (sp[2] / sp[1], sp[3] / sp[1]))
    check(np.argmax(np.abs(np.fft.rfft(data[rl.FRAMES * 512:rl.FRAMES * 512 + 256]))[1:]) == 0, 'bake: level 1 is the same wave')
    check(len(rms) == 16 and 0.3 < rms[0] < 0.9, 'bake: the frames\' rms')
    q, hs = rl.pick_q([1.0, 3.6, 13.0], [1, 0.5, 0.3])
    check(q == 5 and hs == [5, 18, 65], 'pick_q: f0/5 puts the gong\'s modes on harmonics (%d %s)' % (q, hs))
    check(rl.pick_q([1.0, 2.0, 3.01], [1, 1, 1])[0] == 1, 'pick_q: harmonics stay on q 1')
    # units
    check(rl.time_param(0.0005) == 0 and rl.time_param(12.0) == 127 and abs(rl.param_time(rl.time_param(0.3)) - 0.3) < 0.03, 'relitto: envelope times')
    check(rl.cutoff_param(440.0) == round((69 - 16) * 256 / 228) and rl.noise_colour_param(150) == 0 and rl.noise_colour_param(20000) == 127, 'relitto: cutoff, colour')
    pos = rl.position_curve(dict(rl.defaults(), A_POS=1, E2_POS=127, E2A=0, E2D=rl.time_param(1.0), E2S=0), np.array([0.001, 0.5, 1.0]))
    check(pos[0] > 14.5 and 0.3 < pos[1] < 1.5 and pos[2] < 0.3, 'relitto: ENV 2 sweeps the frames 15 -> 0, -60 dB at the decay time (%s)' % np.round(pos, 2))
    # the plans
    rp = rl.plan(analysis.analyse_sound(pluck(), 'pluck'))
    check(rp['b_source'] == 'none' and rp['mode'] == 'decay' and rp['table'] is not None and rp['params']['A_TAB'] == rl.TAB_USER, 'pluck: a USER table on OSC A')
    check(rp['params']['E1S'] < 10 and rp['params']['E2_POS'] == 127 and rp['params']['E2_PITCH'] == 64, 'pluck: no sustain, the sweep on, no pitch env')
    rs = rl.plan(analysis.analyse_sound(snare(), 'snare'))
    check(rs['b_source'] == 'noise' and rs['params']['B_TAB'] == rl.TAB_NOISE and rs['params']['B_LVL'] > 20, 'snare: NOISE on OSC B')
    check(rs['root'] < -1000, 'snare: the table on a fraction of the pitch (root %d)' % rs['root'])
    rk = rl.plan(analysis.analyse_sound(kick(), 'kick'))
    check(rk['params']['E2_PITCH'] > 80, 'kick: ENV 2 to the pitch (%d)' % rk['params']['E2_PITCH'])
    rpad = rl.plan(analysis.analyse_sound(pad(), 'pad'))
    check(rpad['params']['E1S'] > 100 and rpad['params']['E1A'] > 20, 'pad: sustain, a slow attack')
    # the SysEx
    msgs = rl.sysex_messages(rp, slot=2)
    check(len(msgs) == 2 + (rl.WT_SIZE * 2 + rl.U_CHUNK - 1) // rl.U_CHUNK, 'syx: BEGIN, %d DATA, END (%d)' % ((rl.WT_SIZE * 2 + 223) // 224, len(msgs)))
    check(all(m[0] == 0xF0 and m[-1] == 0xF7 and max(m[1:-1]) < 0x80 for m in msgs), 'syx: 7-bit payloads')
    b = msgs[0]
    check(b[4] == 1 and b[5] == 2 and b[6:18] == b'PLUCK       ' and b[18] == rl.NP, 'syx: BEGIN slot, name, np')
    vals = b[19:19 + rl.NP]
    check(vals[0] == rl.TAB_USER + 2, 'syx: A_TAB points at the slot')
    root = vals and (b[19 + rl.NP] | b[20 + rl.NP] << 7 | b[21 + rl.NP] << 14) - 32768
    ln = b[22 + rl.NP] | b[23 + rl.NP] << 7 | b[24 + rl.NP] << 14
    check(root == rp['root'] and ln == rl.WT_SIZE * 2, 'syx: root %d, length %d' % (root, ln))
    raw = b''.join(rlsend.split_messages(b''.join(msgs))[i][7:-1] for i in range(1, len(msgs) - 1))
    import zlib
    # (unpack the 7-bit chunks back: the firmware's sx_unpack7)
    def unpack7(d):
        out, acc, nb = bytearray(), 0, 0
        for c in d:
            acc |= (c & 0x7F) << nb; nb += 7
            if nb >= 8: out.append(acc & 0xFF); acc >>= 8; nb -= 8
        return bytes(out)
    table = b''.join(unpack7(rlsend.split_messages(b''.join(msgs))[i][7:-1])[:224] for i in range(1, len(msgs) - 1))
    check(table == np.asarray(rp['table'], dtype='<i2').tobytes(), 'syx: the table survives the 7-bit packing')
    crc = sum(b[25 + rl.NP + i] << (7 * i) for i in range(5))
    check(crc == zlib.crc32(table) & 0xFFFFFFFF, 'syx: the CRC')
    check(msgs[-1] == bytes([0xF0, 0x7D, 0x52, 0x4C, 0x03, 0xF7]), 'syx: END')
    nz = rl.plan(analysis.analyse_sound(RNG.standard_normal(SR // 2) * 0.3, 'hat'))
    check(nz['table'] is None and nz['params']['A_TAB'] == rl.TAB_NOISE, 'noise only: NOISE on OSC A, no table')
    check(len(rl.sysex_messages(nz)) == 1 and rl.sysex_messages(nz)[0][4] == 0x20, 'noise only: a PARAMS message')
    m2 = rlsend.with_slot(msgs[0], 0)
    check(m2[5] == 0 and m2[19] == rl.TAB_USER, 'send: --slot moves the slot and the table reference')
    check('TABLE USER 1' in rl.sheet(rp) and 'NOISE' in rl.sheet(rs), 'sheet: the tables by name')
    # the real engine
    exe = rl.host_binary() if rd else None
    if not exe:
        print('  (relitto host: skipped, no source)')
        return
    y, log = rl.render(rp, exe, gate=rp['gate'], dur=1.6)
    acks = [l for l in log.split('\n') if 'SYSEX out' in l]
    check(len(acks) == len(msgs) and all(' 40 00 ' in l for l in acks), 'host: every message answered OK (%d)' % len(acks))
    d = render.distance(pluck(), y[:len(T)])
    check(d < 7.0, 'host: the pluck as planned (%.2f dB)' % d)
    best, score, start = rl.refine(rp, exe, pluck(), budget=8.0, gate=rp['gate'])
    check(score < start and score < 3.5, 'host: refined (%.2f -> %.2f dB)' % (start, score))
    # the sound is kept: a QUERY after the load names it
    q = bytes([0xF0, 0x7D, 0x52, 0x4C, 0x10, 0xF7])
    _, log = rl.run_host(exe, "0 syx SYX\n300 end\n", msgs + [q])
    info = [l for l in log.split('\n') if 'SYSEX out F0 7D 52 4C 11' in l]
    check(len(info) == 1 and bytes(int(h, 16) for h in info[0].split('F0 7D 52 4C 11 ')[1].split()[8 + 13 * 2:8 + 13 * 3]) == b'\x01' + b'PLUCK'.ljust(12), 'host: INFO names slot 3 (%s)' % (info[0][-80:] if info else '-'))
    ys, _ = rl.render(rs, exe, gate=rs['gate'], dur=1.0)
    check(np.abs(ys).max() > 0.01 and render.distance(snare(), ys[:len(T)]) < 8.0, 'host: the snare (NOISE + modes)')
    yk, _ = rl.render(rk, exe, gate=rk['gate'], dur=1.0)
    rr = analysis.analyse_sound(yk[:len(T)], 'rk')
    check(rr['pitch_env'] is not None and rr['pitch_env']['semitones'] > 10, 'host: the kick sweeps (%s)' % rr['pitch_env'])


def t_cli():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, 'one-shot'))
        os.makedirs(os.path.join(d, 'stems'))
        audio.save(os.path.join(d, 'one-shot', 'my pluck!.wav'), pluck() * 0.5)
        audio.save(os.path.join(d, 'one-shot', 'snare.wav'), snare() * 0.5)
        gap = np.zeros(int(0.25 * SR))
        audio.save(os.path.join(d, 'stems', 'loop.wav'), np.concatenate([pluck()[:int(.4 * SR)], gap, snare()[:int(.4 * SR)], gap] * 3) * 0.5)
        open(os.path.join(d, 'notes.txt'), 'w').write('not a sound')
        open(os.path.join(d, 'broken.wav'), 'wb').write(b'RIFF nothing')
        found = cli.find_sounds(d)
        check(len(found) == 4, 'cli: 4 audio files (%d)' % len(found))
        kinds = {os.path.basename(p): k for p, k in found}
        check(kinds['snare.wav'] == 'one' and kinds['loop.wav'] == 'stem' and kinds['broken.wav'] == 'auto', 'cli: kinds from folders')
        rep = cli.convert(d, budget=3.0, log=lambda *a: None)
        errs = [e for e in rep if 'error' in e]
        good = [e for e in rep if 'error' not in e]
        check(len(errs) == 1, 'cli: the broken file reported')
        check(len(good) == 4, 'cli: 2 one-shots + 2 from the loop (%d)' % len(good))
        out = os.path.join(d, 'patches')
        rel = [('relitto', '.syx'), ('relitto', '.txt'), ('preview', '-relitto.wav')] if rl.find_relitto() else []
        for e in good:
            for sub, ext in [('recipes', '.json'), ('surge', '.fxp'), ('norns', '.strati'), ('preview', '-recipe.wav'),
                             ('preview', '-surge.wav'), ('preview', '-norns.wav')] + rel:
                check(os.path.isfile(os.path.join(out, sub, e['name'] + ext)), 'cli: %s%s' % (e['name'], ext))
            if rel:
                check(e['relitto_db'] <= e['relitto_db_start'], 'cli: relitto never worse')
            check(e['surge_db'] <= e['surge_db_start'], 'cli: refine never worse')
        check(any(e['name'] == 'my-pluck' for e in good), 'cli: safe names')
        check(os.path.isfile(os.path.join(out, 'report.txt')), 'cli: report')
        again = cli.find_sounds(d)
        check(len(again) == 4, 'cli: its own output is not input')


for t in (t_analysis, t_stem, t_render, t_surge, t_refine, t_norns, t_pad, t_pitch_env, t_relitto, t_cli):
    t()
print('strati: %d checks, %d failed' % (OK[0] + len(FAIL), len(FAIL)))
sys.exit(1 if FAIL else 0)
