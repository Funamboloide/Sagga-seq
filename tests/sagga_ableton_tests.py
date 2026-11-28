#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA DA ABLETON (0.32.3): the MIDI clips of Ableton made a project of steps (tools/hub/sagga_ableton.py) - the MIDI
files read (both formats, any resolution, running status, a note-off as a note-on at 0), the parts found from the files'
names, the steps (the nudge that keeps the swing, ratchets, chords, ties, the copies of a short pattern, CHAIN, TAPE),
the channels of the rig, the scenes; then THE FIRMWARE ITSELF plays the project in the simulator and what comes out is
compared with the clips that went in, note by note; last, the hub's page (DA ABLETON, the channels).

    python3 tests/sagga_ableton_tests.py
"""
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'hub'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
TOOL = os.path.join(ROOT, 'build', 'sagga_sgqjson')
SIM = os.path.join(tempfile.gettempdir(), 'sagga_sim_ableton_%d' % os.getpid())
FAILS, CHECKS = [], [0]


def check(c, what):
    CHECKS[0] += 1
    if not c:
        FAILS.append(what)
        print('  FAIL:', what)


def group(name):
    print(name)


def build():
    src = [os.path.join(ROOT, 'firmware', 'src', f) for f in ('sagga_seq_core.c', 'sagga_beats.c')]
    os.makedirs(os.path.dirname(TOOL), exist_ok=True)
    subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-I' + os.path.join(ROOT, 'firmware', 'src'),
                    os.path.join(ROOT, 'tools', 'sgqmid', 'sagga_sgqjson.c')] + src + ['-o', TOOL], check=True)
    os.environ['SAGGA_SGQJSON'] = TOOL
    subprocess.run(['cc', '-O2', '-w', '-DDINGHY_HOST', '-DAPP_VER="test"', '-I' + ROOT + '/firmware/src', '-I' + ROOT + '/firmware/gen',
                    '-o', SIM, ROOT + '/firmware/src/dinghy.c'], check=True, cwd=ROOT)


# ------------------------------------------------------------------------------------------------ clips, as Ableton writes them
def vlq(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append(0x80 | (n & 0x7F))
        n >>= 7
    return bytes(reversed(out))


def mtrk(events, end, running=False):
    events = sorted(events, key=lambda e: (e[0], (e[1][0] & 0xF0) == 0x90 and e[1][2] > 0))
    b, t, last = b'', 0, None
    for tick, ev in events:
        b += vlq(tick - t)
        if running and ev[0] < 0xF0 and ev[0] == last:
            b += ev[1:]
        else:
            b += ev
        last = ev[0] if ev[0] < 0xF0 else None
        t = tick
    b += vlq(max(0, end - t)) + b'\xff\x2f\x00'
    return b'MTrk' + struct.pack('>I', len(b)) + b


def smf(notes, bars, ppq=96, bpm=124.0, name='clip', fmt=1, sig=(4, 4), running=False, off0=False, extra=(), tempo=True):
    """notes [(beat, beats long, note, vel)] -> the bytes of a .mid (type 1: a tempo track and a track of notes)"""
    end = int(round(bars * 4 * ppq))
    meta = [(0, b'\xff\x58\x04' + bytes([sig[0], {2: 1, 4: 2, 8: 3}[sig[1]], 24, 8]))]
    if tempo:
        meta.append((0, b'\xff\x51\x03' + int(round(60e6 / bpm)).to_bytes(3, 'big')))
    evs = [(0, b'\xff\x03' + vlq(len(name)) + name.encode())] + list(extra)
    for on, ln, n, v in notes:
        a, b = int(round(on * ppq)), int(round((on + ln) * ppq))
        evs.append((a, bytes([0x90, n, v])))
        evs.append((b, bytes([0x90, n, 0]) if off0 else bytes([0x80, n, 64])))
    if fmt == 0:
        return b'MThd' + struct.pack('>IHHH', 6, 0, 1, ppq) + mtrk(meta + evs, end, running)
    return b'MThd' + struct.pack('>IHHH', 6, 1, 2, ppq) + mtrk(meta, end) + mtrk(evs, end, running)


def clips():
    """the clips of a palette, as files: [(name, bytes)]"""
    out = []
    out.append(('A-kick-1.mid', smf([(b, 0.25, 36, 120) for b in range(4)], 1)))
    out.append(('A-kick-2.mid', smf([(b, 0.25, 36, 120) for b in range(4)] + [(4, .25, 36, 120), (5.5, .25, 36, 100), (6.25, .25, 36, 90)], 2)))
    bass = []
    for k in range(8):                                          # 8ths swung: the second of each pair a third of a 16th late
        bass.append((k * 0.5 + (0.25 / 3 if k % 2 else 0), 0.55 if k % 3 == 0 else 0.3, [29, 29, 41, 29, 32, 29, 39, 36][k], 100 + k))
    bass += [(4.0, 0.3, 29, 110), (4.25, 0.3, 31, 100)]          # the first holds into the next 16th: a TIE
    out.append(('A-basso-1.mid', smf(bass, 2, running=True)))
    out.append(('A-hat-1.mid', smf([(b * 0.5, 0.1, 42, 80) for b in range(7)] + [(3.75, 0.1, 42, 70), (3.875, 0.1, 42, 75)], 1)))
    pad = []
    for k, ch in enumerate([[41, 56, 60, 63, 67], [37, 53, 56, 60, 65], [34, 49, 53, 56, 60], [36, 52, 58, 61, 67]]):
        pad += [(k * 8, 8, n, 90) for n in ch]
    out.append(('A-pad-1.mid', smf(pad, 8)))
    out.append(('A-lead-1.mid', smf([(k * 1.5, 0.75, 60 + (k * 5) % 12, 100) for k in range(32)], 12)))
    kit = [(b, .25, 36, 120) for b in (0, 2.5)] + [(b, .25, 38, 110) for b in (1, 3)] + [(b * .5, .1, 42, 70) for b in range(8)] + [(3.75, .25, 45, 90)]
    out.append(('B-drums-3.mid', smf(kit, 1)))
    out.append(('qualcosa-1.mid', smf([(0, 1, 60, 100)], 1)))
    out.append(('A-accordi-1.mid', smf([(0, 2, n, 90) for n in (48, 52, 55, 59, 62, 65, 69)] + [(2, 2, n, 90) for n in (50, 53, 57, 60)], 1,
                                       ppq=480, fmt=0, off0=True)))
    return out


def read_project(data):
    with tempfile.NamedTemporaryFile(suffix='.sgq', delete=False) as f:
        f.write(data)
        p = f.name
    try:
        r = subprocess.run([TOOL, 'read', p], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        os.unlink(p)


def steps_of(d):
    return {(t, p, s): st for t, p, s, st in d['steps']}


# ------------------------------------------------------------------------------------------------ the tests
def t_midi(A):
    group('the MIDI files')
    m = A.read_midi(smf([(0, 1, 60, 100), (1.5, 0.25, 64, 90)], 2, ppq=96, bpm=127.5, name='Lead 1'))
    check(m['ppq'] == 96 and abs(60e6 / m['tempo'] - 127.5) < 0.01 and m['sig'] == (4, 4) and m['end'] == 768, 'type 1: ppq, tempo, metre, end (%s)' % {k: m[k] for k in ('ppq', 'tempo', 'sig', 'end')})
    check(m['notes'] == [(0, 96, 60, 100), (144, 168, 64, 90)] and m['names'] == ['Lead 1'], 'its notes and its name (%s %s)' % (m['notes'], m['names']))
    m0 = A.read_midi(smf([(0, 1, 60, 100), (1, 1, 62, 80), (1, 1, 65, 81)], 1, ppq=480, fmt=0, running=True, off0=True))
    check(m0['notes'] == [(0, 480, 60, 100), (480, 960, 62, 80), (480, 960, 65, 81)], 'type 0, 480 ppq, running status, note-offs as note-ons at 0 (%s)' % m0['notes'])
    sysex = (0, b'\xf0' + vlq(3) + b'\x7e\x7f\xf7')
    cc = (24, b'\xb0\x4a\x40')
    mx = A.read_midi(smf([(0, 1, 60, 100)], 1, extra=[sysex, cc]))
    check(mx['notes'] == [(0, 96, 60, 100)] and mx['other'] == 1, 'a SysEx skipped, a CC counted (%s)' % mx['other'])
    junk = smf([(0, 1, 60, 100)], 1)
    junk = junk[:14] + b'XFIL' + struct.pack('>I', 4) + b'abcd' + junk[14:]
    check(A.read_midi(junk)['notes'] == [(0, 96, 60, 100)], 'a chunk of another kind before the tracks: skipped')
    held = A.read_midi(b'MThd' + struct.pack('>IHHH', 6, 0, 1, 96) + mtrk([(0, b'\x90\x3c\x64')], 384))
    check(held['notes'] == [(0, 384, 60, 100)], 'a note never let go ends with its track (%s)' % held['notes'])
    liar = bytearray(smf([(0, 1, 60, 100)], 1, fmt=0))
    liar[18:22] = struct.pack('>I', struct.unpack('>I', bytes(liar[18:22]))[0] + 40)   # a track that says it is longer than the file
    for bad, why in ((b'RIFF0000', 'not MIDI'), (b'MThd' + struct.pack('>IHHH', 6, 0, 1, 0xE728), 'SMPTE'),
                     (smf([(0, 1, 60, 100)], 1)[:30], 'cut short'), (bytes(liar), 'a track longer than the file')):
        try:
            A.read_midi(bad)
            check(False, 'refused: %s' % why)
        except A.AbletonError:
            check(True, '')


def t_names(A):
    group('the parts from the names')
    parts = A.rig()
    for name, tracks, want in (('A-kick-1.mid', [], ('kick', 1)), ('Basso 2.mid', [], ('basso', 2)), ('A-basso2-1.mid', [], ('basso2', 1)),
                               ('p3-hat.mid', [], ('hat', None)), ('B-drums-3.mid', [], ('kit', 3)), ('A-snare-4.mid', [], ('rullante', 4)),
                               ('clip 1.mid', ['Lead synth'], ('lead', 1)), ('qualcosa-9.mid', [], (None, None)),
                               ('INTRO lunga 1.mid', [], ('sample', 1)), ('PAD-archi.MID', [], ('pad', None))):
        got = A.classify(name, tracks, parts)
        check(got == want, '%s -> %s (%s)' % (name, want, got))
    check([A.gate_code(d) for d in (0.25, 1.0, 1.1, 1.3, 1.5, 2.2, 70)] == [25, 100, 100, 101, 101, 102, 164], 'the gates (%s)' % [A.gate_code(d) for d in (0.25, 1.0, 1.1, 1.3, 1.5, 2.2, 70)])


def t_build(A):
    group('the project')
    data, rep = A.build(clips(), 'palette-a')
    d = read_project(data)
    S = steps_of(d)
    tr = d['track']
    check(''.join(chr(c) for c in d['ext']['name'] if c) == 'PALETTE-A' and d['project']['bpm'] == 124 and rep['bpm'] == 124, 'the name and the tempo of the clips')
    check([tr[t]['channel'] for t in range(12)] == list(range(12)), 'every track on its channel, 1-12 (%s)' % [tr[t]['channel'] for t in range(12)])
    check([tr[t]['flags'] for t in range(12)] == [2, 0, 0, 2, 2, 2, 2, 32, 0, 16, 0, 0], 'DRUM on the drums, TAPE on the long lead, CHAIN on the 8-bar pad (%s)' % [tr[t]['flags'] for t in range(12)])
    check([tr[t]['role'] for t in range(12)] == [1, 5, 18, 2, 3, 4, 10, 23, 6, 21, 7, 0], 'the roles: the groups DRUMS, BASS, MELODIC as on the FM-1')
    check([tr[t]['length'] for t in (0, 1, 3, 4, 9)] == [32, 32, 16, 16, 64], 'the lengths: the longest clip of each part (%s)' % [tr[t]['length'] for t in (0, 1, 3, 4, 9)])
    check(tr[0]['pen'] == 36 and tr[3]['pen'] == 38 and tr[5]['pen'] == 45, 'a drum track\'s PEN: its drum (%s)' % [tr[t]['pen'] for t in (0, 3, 5)])
    k = [s for s in range(32) if S.get((0, 0, s), {}).get('flags', 0) & 1]
    check(k == [0, 4, 8, 12, 16, 20, 24, 28] and all(S[(0, 0, s)]['flags'] & 64 for s in (16, 20, 24, 28)) and not S[(0, 0, 0)]['flags'] & 64,
          'a 1-bar clip in a 2-bar track: its COPIES (flag 64), as the FM-1 makes them (%s)' % k)
    check(all(S.get((0, 0, s), {}).get('flags') == 64 for s in (17, 18, 19)), '... the rests copied too (a pattern of 16 going round)')
    k2 = [(s, S[(0, 1, s)]['velocity']) for s in range(32) if S.get((0, 1, s), {}).get('flags', 0) & 1]
    check(k2 == [(0, 120), (4, 120), (8, 120), (12, 120), (16, 120), (22, 100), (25, 90)], 'the 2-bar kick as written (%s)' % k2)
    b = [(s, S[(1, 0, s)]['note'][0], S[(1, 0, s)]['nudge'], S[(1, 0, s)]['length'], S[(1, 0, s)]['flags']) for s in range(32) if (1, 0, s) in S]
    check([x[2] for x in b[:8]] == [0, 33, 0, 33, 0, 33, 0, 33], 'the swing: every second 8th a third of a 16th late, in the NUDGE (%s)' % [x[2] for x in b[:8]])
    check(b[0][3] == 102 and b[1][3] == 100, 'the gates: 2.2 steps -> 2 steps (102), 1.2 -> a step (%s %s)' % (b[0][3], b[1][3]))
    check((16, 29, 0, 100, 19) in b and (17, 31, 0, 100, 3) in b, 'the note that holds into the next 16th: a TIE (%s)' % b[-2:])
    h = S[(4, 0, 15)]
    check(h['ratchet'] == 2 and h['velocity'] == 75 and h['note'][0] == 42, 'two hats in a 16th: a RATCHET of 2 (%s)' % h)
    c = S[(8, 0, 0)]
    check(c['note'] == [48, 52, 55, 59, 62, 65] and c['length'] == 108, 'seven notes at once: the six lowest, 8 steps (%s)' % c)
    pads = [(p, s) for p in (0, 1) for s in range(64) if S.get((9, p, s), {}).get('flags', 0) & 1]
    check(pads == [(0, 0), (0, 32), (1, 0), (1, 32)] and S[(9, 1, 32)]['note'][:5] == [36, 52, 58, 61, 67], 'an 8-bar clip: patterns 1+2, CHAIN (%s)' % pads)
    check(d['tape_cnt'][7] == 32 and d['tape_len'][7] == 12 * 1536 and d['tape'][0] == [7, 0, 288, 60, 100], 'a 12-bar lead alone: a TAPE track of 12 bars, every note (%s %s)' % (d['tape_cnt'][7], d['tape'][:1]))
    kit = [(t, [s for s in range(16) if S.get((t, 2, s), {}).get('flags', 0) & 1]) for t in (0, 3, 4, 5)]
    check(kit == [(0, [0, 10]), (3, [4, 12]), (4, [0, 2, 4, 6, 8, 10, 12, 14]), (5, [15])], 'the whole kit split: kick, snare, hats, tom on their tracks, pattern 3 (%s)' % kit)
    sc = [d['scene'][s]['pattern'][:6] for s in range(3)]
    check(sc == [[0, 0, 0, 2, 0, 2], [1, 0, 0, 2, 0, 2], [2, 0, 0, 2, 2, 2]] and rep['scenes'] == 3, 'scene N: the N-th clip of every part, else its last (%s)' % sc)
    check(d['scene'][0]['pattern'][9] == 0 and tr[3]['initial_pattern'] == 2, 'the CHAIN plays from 1; a part with only pattern 3 starts there')
    f = {x['file']: x for x in rep['files']}
    check('non so che parte' in ' '.join(f['qualcosa-1.mid']['warnings']) and not f['qualcosa-1.mid']['patterns'], 'a file with no part in its name: said, left out')
    check(any('più di 6 note' in w for w in f['A-accordi-1.mid']['warnings']), 'the seventh note: said')
    check(f['B-drums-3.mid']['part'].startswith('kit: kick, rullante, hat, perc'), 'the kit: where it went (%s)' % f['B-drums-3.mid']['part'])
    check('A-lead-1.mid' in A.report_text(rep) or 'TAPE' in A.report_text(rep), 'the report as text')

    group('the channels, the tempo, the limits')
    data, rep = A.build(clips()[:3], 'x', {'canali': {'basso': 3, 'kick': 16, 'hat': 99}}, bpm=140)
    d = read_project(data)
    check(d['track'][1]['channel'] == 2 and d['track'][0]['channel'] == 15 and d['track'][4]['channel'] == 4 and d['project']['bpm'] == 140,
          'the channels saved on the page (a wrong one ignored), the BPM given (%s %s %s)' % (d['track'][1]['channel'], d['track'][0]['channel'], d['track'][4]['channel']))
    _, rep = A.build([('A-kick-1.mid', smf([(0, 1, 36, 100)], 1, tempo=False))], 'x')
    check(rep['bpm'] is None and any('128' in w for w in rep['warnings']), 'no tempo in the clips: said, 128')
    _, rep3 = A.build([('A-kick-%d.mid' % k, smf([(0, .25, 36, 100)], 1, bpm=b)) for k, b in ((1, 120), (2, 126), (3, 126))], 'x')
    check(rep3['bpm'] == 126, 'the tempo most of the clips have (%s)' % rep3['bpm'])
    d = read_project(A.build([('A-basso-1.mid', smf([(0, 0.8, 29, 100), (0.75, 0.25, 31, 100)], 1))], 'x')[0])
    st = steps_of(d)[(1, 0, 0)]
    check(not st['flags'] & 16 and st['length'] == 103, 'a note that holds into one three 16ths later: no TIE, its own length (%s %s)' % (st['flags'], st['length']))
    _, rep = A.build([('A-kick-1.mid', smf([(0, .25, 36, 100)], 1, bpm=120)), ('B-kick-1.mid', smf([(0, .25, 36, 100)], 1, bpm=126))], 'x')
    f = {x['file']: x for x in rep['files']}
    check(f['B-kick-1.mid']['patterns'] == ['2'] and any('già preso' in w for w in f['B-kick-1.mid']['warnings']) and any('tempi diversi' in w for w in rep['warnings']),
          'two clips for pattern 1: the second in 2, said; two tempos: said')
    many = [('A-hat-%d.mid' % (k % 9), smf([(k * 0.25, .1, 42, 80)], 1)) for k in range(9)]
    _, rep = A.build(many, 'x')
    check(sum(1 for x in rep['files'] if x['patterns']) == 8 and any('non c\'è più posto' in ' '.join(x['warnings']) for x in rep['files']),
          'nine clips of a part: eight patterns, the ninth said and left out')
    d = read_project(A.build([('A-arp-1.mid', smf([(0, .25, 60, 100), (11.9, .05, 67, 90)], 3))], 'x')[0])
    check(d['track'][10]['length'] == 48 and d['steps'][-1][2] == 47 and d['steps'][-1][3]['nudge'] == 50, 'a 3-bar clip: a track of 48; a note just before the end stays at its end, as late as a step goes (%s %s)' % (d['steps'][-1][:3], d['steps'][-1][3]['nudge']))
    data, rep = A.build([('A-arp-1.mid', smf([(0, .25, 60, 100)], 3)), ('A-arp-2.mid', smf([(0, .25, 62, 100)], 4))], 'x')
    check(read_project(data)['track'][10]['length'] == 64 and any('ripete la prima' in w for x in rep['files'] for w in x['warnings']), '3 bars and 4 in one track: 64, said')
    _, rep = A.build([('A-pad-1.mid', smf([(0, 1, 60, 100)], 1, sig=(3, 4))), ('A-lead-1.mid', smf([(0, 1, 60, 100)], 1, extra=[(0, b'\xb0\x01\x10')])), ('A-arp-1.mid', smf([], 1))], 'x')
    w = ' '.join(w for x in rep['files'] for w in x['warnings'])
    check('3/4' in w and '1 controllo (CC' in w and 'nessuna nota' in w, 'a metre of 3/4, a CC, an empty clip: said (%s)' % w)
    for files, why in (([], 'no files'), ([('qualcosa.mid', smf([(0, 1, 60, 100)], 1))], 'no part'), ([('A-kick-1.mid', b'nope')], 'not MIDI')):
        try:
            A.build(files, 'x')
            check(False, 'nothing to make: refused (%s)' % why)
        except A.AbletonError:
            check(True, '')
    cfg = A.config_from_page([{'key': 'basso', 'canale': 3}, {'key': 'kick', 'canale': 1}])
    check(cfg == {'canali': {'basso': 3, 'kick': 1}}, 'the page\'s table -> the config')
    for bad in ([{'key': 'nope', 'canale': 1}], [{'key': 'basso', 'canale': 17}], [{'key': 'basso', 'canale': True}], 'x'):
        try:
            A.config_from_page(bad)
            check(False, 'a wrong channel table refused (%r)' % (bad,))
        except A.AbletonError:
            check(True, '')


def t_nota(A):
    """0.32.6: the M8's note (N, the note the M8 calls C-4): the drums that go to an M8 arrive on it"""
    group('0.32.6 the M8\'s note: the drums for the M8s on N')

    def ons(S, t, p):
        return sorted({st['note'][0] for (tt, pp, s), st in S.items() if tt == t and pp == p and st['flags'] & 1})
    data, rep = A.build(clips(), 'palette-a', {'nota_m8': 48})
    d = read_project(data)
    S = steps_of(d)
    tr = d['track']
    check([tr[t]['pen'] for t in (0, 3, 4, 5)] == [48] * 4, 'the PEN of every drum track for the M8s: N (%s)' % [tr[t]['pen'] for t in (0, 3, 4, 5)])
    check(ons(S, 0, 0) == [48] and ons(S, 0, 1) == [48] and ons(S, 4, 0) == [48], 'the kick (36) and the hats (42) on 48 (%s %s)' % (ons(S, 0, 0), ons(S, 4, 0)))
    check([ons(S, t, 2) for t in (0, 3, 4, 5)] == [[48]] * 4, 'the kit split by its notes first, then each part on 48 (%s)' % [ons(S, t, 2) for t in (0, 3, 4, 5)])
    check(ons(S, 1, 0) == [29, 31, 32, 36, 39, 41] and tr[1]['pen'] == 36, 'the bass keeps its notes (%s)' % ons(S, 1, 0))
    k = [x for x in rep['tracks'] if x['part'] == 'kick'][0]
    check(rep['nota_m8'] == 48 and 'la 36 del clip diventa la 48' in k.get('m8', '') and "nota M8 (N): 48 (C3 sull'FM-1)" in A.report_text(rep),
          'the report says it, with the FM-1\'s name of N (%s)' % k.get('m8'))
    check(not any('casella' in w for w in rep['warnings']), 'with N: no word about the box')
    perc = [(b * .5, .1, 63, 90) for b in range(6)] + [(3.5, .1, 64, 90), (3.75, .1, 70, 90)]
    d, rep = A.build([('A-perc-1.mid', smf(perc, 1))], 'x', {'nota_m8': 48})
    d = read_project(d)
    check(ons(steps_of(d), 5, 0) == [48, 49, 55] and d['track'][5]['pen'] == 48 and 'si spostano con lei (-15)' in rep['tracks'][0]['m8'],
          'PERC: the most used (63) on 48, 64 and 70 with it (%s %s)' % (ons(steps_of(d), 5, 0), rep['tracks'][0].get('m8')))
    d, rep = A.build([('A-perc-1.mid', smf([(0, .1, 36, 90), (1, .1, 36, 90), (2, .1, 100, 90)], 1))], 'x', {'nota_m8': 120})
    check(ons(steps_of(read_project(d)), 5, 0) == [120, 124] and 'fuori da 0-127' in rep['tracks'][0]['m8'],
          'past 127: an octave in, said (%s)' % rep['tracks'][0].get('m8'))
    d, rep = A.build([('A-perc-1.mid', smf(perc, 1))], 'x', {'nota_m8': 48, 'canali': {'perc': 12}})
    t = rep['tracks'][0]
    check(ons(steps_of(read_project(d)), 5, 0) == [63, 64, 70] and t['machine'] == 'Zynthian' and 'non va a un M8' in t['m8']
          and 'slice' not in t.get('note', ''), 'a drum part on channel 12 (the Zynthian): the clip\'s notes, said (%s / %s)' % (t.get('m8'), t.get('note')))
    _, rep = A.build(clips()[:1], 'x')
    check(any('casella' in w for w in rep['warnings']) and rep['nota_m8'] is None, 'no N and drums for an M8: the report says where N goes')
    _, rep = A.build([('A-basso-1.mid', smf([(0, 1, 36, 90)], 1))], 'x')
    check(not any('casella' in w for w in rep['warnings']), 'no drums: nothing said')
    check([p.machine for p in A.rig({'canali': {'perc': 12, 'lead': 2, 'pad': 13}})][5:10] == ['Zynthian', 'M8 2', 'M8 1', 'MicroDexed', 'M8 2'],
          'the machine of each part is its channel\'s')
    check(A.config_from_page({'canali': [{'key': 'basso', 'canale': 3}], 'nota_m8': 48}) == {'canali': {'basso': 3}, 'nota_m8': 48}, 'the page: the channels and N')
    check(A.config_from_page([{'key': 'basso', 'canale': 3}], {'nota_m8': 50}) == {'canali': {'basso': 3}, 'nota_m8': 50}, 'a page of 0.32.3 (the channels only): N stays')
    check(A.config_from_page({'canali': [], 'nota_m8': None}, {'nota_m8': 50}) == {'canali': {}}, 'N emptied: the clip\'s notes again')
    for bad in (128, -1, True, 'x', 4.5):
        try:
            A.config_from_page({'canali': [], 'nota_m8': bad})
            check(False, 'N %r refused' % (bad,))
        except A.AbletonError:
            check(True, '')
    check(A.m8_note({'nota_m8': 200}) is None and A.m8_note({'nota_m8': True}) is None and A.m8_note({'nota_m8': 0}) == 0, 'a wrong N in the file: none')
    check([A.note_name(n) for n in (0, 36, 48, 60, 61, 127)] == ['C-1', 'C2', 'C3', 'C4', 'C#4', 'G9'], 'the notes as the FM-1 names them (60 C4)')
    with tempfile.TemporaryDirectory() as dd:
        src, out = os.path.join(dd, 'A-kick-1.mid'), os.path.join(dd, 'k.sgq')
        with open(src, 'wb') as f:
            f.write(smf([(b, .25, 36, 120) for b in range(4)], 1))
        rc = A.main([src, '-o', out, '--nota-m8', '50'])
        check(rc == 0 and ons(steps_of(read_project(open(out, 'rb').read())), 0, 0) == [50], 'the command line: --nota-m8 50')
        check(A.main([src, '-o', out, '--nota-m8', '200']) == 2, '--nota-m8 200: refused')


def t_firmware(A):
    """the project in the FM-1's own code: every note of the clips comes out, on its channel, when the clip says"""
    group('the firmware plays it (the simulator)')
    import sagga_grid_bridge as B
    files = clips()
    data, rep = A.build(files, 'palette-a')
    lines, t = [], 300
    for fr in B.dump_frames(data):
        lines.append('%d sx %s' % (t, ' '.join('%02X' % b for b in fr[1:-1])))
        t += 25
    t += 800
    lines += ['%d press 12' % t, '%d release 12' % (t + 30), '%d end' % (t + 17000)]
    with tempfile.TemporaryDirectory() as d:
        sp = os.path.join(d, 's.txt')
        with open(sp, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        out = subprocess.run([SIM, os.path.join(d, 'o'), sp], capture_output=True, text=True, check=True, cwd=ROOT, timeout=600).stdout
    rx = re.compile(r'^\s*(\d+) ms  MIDI out ([0-9A-F]{2}) (\d+) (\d+)$')
    msgs = [(int(m.group(1)), int(m.group(2), 16), int(m.group(3)), int(m.group(4))) for m in map(rx.match, out.splitlines()) if m]
    ons = [(t, st & 15, a) for t, st, a, b in msgs if st & 0xF0 == 0x90 and b]
    offs = [(t, st & 15, a) for t, st, a, b in msgs if st & 0xF0 == 0x80 or (st & 0xF0 == 0x90 and not b)]
    check(ons, 'notes came out')
    if not ons:
        return
    beat = 60000.0 / 124
    T0 = min(t for t, ch, n in ons if ch == 0)
    by = {n: b for n, b in files}

    def expect(fname, loop_bars, ch, only=None, until=32):
        m = A.read_midi(by[fname])
        ev = []
        for k in range(int(until // (loop_bars * 4)) + 1):
            for on, off, n, v in m['notes']:
                b = on / m['ppq'] + k * loop_bars * 4
                if b < until - 1e-6 and (only is None or n in only):
                    ev.append((T0 + b * beat, ch, n))
        return ev
    exp = (expect('A-kick-1.mid', 1, 0) + expect('A-basso-1.mid', 2, 1) + expect('B-drums-3.mid', 1, 3, {38}) + expect('A-hat-1.mid', 1, 4)
           + expect('B-drums-3.mid', 1, 5, {45}) + expect('A-lead-1.mid', 12, 7) + expect('A-accordi-1.mid', 1, 8, {48, 50, 52, 53, 55, 57, 59, 60, 62, 65})
           + expect('A-pad-1.mid', 8, 9))
    got = [x for x in ons if x[0] < T0 + 32 * beat - 1]
    used, errs, missing = [False] * len(got), [], []
    for t, ch, n in sorted(exp):
        best = None
        for i, (t2, ch2, n2) in enumerate(got):
            if not used[i] and ch2 == ch and n2 == n and abs(t2 - t) < 30 and (best is None or abs(t2 - t) < abs(got[best][0] - t)):
                best = i
        if best is None:
            missing.append((round(t - T0), ch + 1, n))
        else:
            used[best] = True
            errs.append(abs(got[best][0] - t))
    extra = [(round(t - T0), ch + 1, n) for (t, ch, n), u in zip(got, used) if not u]
    check(len(exp) == 290 and not missing and not extra, 'eight bars, eight parts: %d notes of the clips, every one out on its channel (missing %s, more %s)' % (len(exp), missing[:6], extra[:6]))
    check(errs and max(errs) <= 2.0, 'each when the clip says: %.1f ms at most (the swing, the roll, the chords, the TAPE, the CHAIN)' % (max(errs) if errs else -1))
    # the tie: the bass's note of beat 4 holds past the start of the next (legato), the others end before it
    b_on = sorted(t for t, ch, n in ons if ch == 1 and n == 29 and abs(t - (T0 + 4 * beat)) < 3)
    b_off = sorted(t for t, ch, n in offs if ch == 1 and n == 29 and T0 + 4 * beat < t < T0 + 4.6 * beat)
    nxt = [t for t, ch, n in ons if ch == 1 and n == 31 and abs(t - (T0 + 4.25 * beat)) < 3]
    check(b_on and b_off and nxt and b_off[0] > nxt[0], 'the TIE: the bass holds into the next note (legato: a mono synth slides) (%s %s %s)' % (b_on[:1], b_off[:1], nxt[:1]))


def t_page(A):
    group('the hub\'s page: DA ABLETON')
    import sagga_fw as FW
    with tempfile.TemporaryDirectory() as d:
        fw, pr = os.path.join(d, 'fw'), os.path.join(d, 'pr')
        os.makedirs(fw)
        os.makedirs(pr)
        state = FW.State(fw, pr, writer=FW.BootWriter(fw, mounts=lambda: [('/', ['rw'])]), pat_writer=FW.BootWriter(pr, mounts=lambda: [('/', ['rw'])]))
        srv = FW.ThreadingHTTPServer(('127.0.0.1', 0), FW.make_handler(state))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = 'http://127.0.0.1:%d' % srv.server_address[1]

        def req(path, body=None, headers=None):
            r = urllib.request.Request(base + path, data=body, headers=headers or {})
            try:
                with urllib.request.urlopen(r, timeout=30) as f:
                    return f.status, f.read().decode('utf-8', 'replace')
            except urllib.error.HTTPError as e:
                return e.code, e.read().decode('utf-8', 'replace')

        def multipart(fields, files):
            bnd = 'sagga7d1'
            body = b''
            for k, v in fields.items():
                body += ('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (bnd, k, v)).encode()
            for n, data in files:
                body += ('--%s\r\nContent-Disposition: form-data; name="f"; filename="%s"\r\nContent-Type: audio/midi\r\n\r\n' % (bnd, n)).encode() + data + b'\r\n'
            body += ('--%s--\r\n' % bnd).encode()
            return body, {'Content-Type': 'multipart/form-data; boundary=%s' % bnd}

        code, page = req('/')
        check(code == 200 and 'DA ABLETON' in page and 'action="/api/ableton"' in page and 'multiple' in page, 'the section on the page')
        code, js = req('/api/ableton/canali')
        parts = json.loads(js)['parti'] if code == 200 else []
        check([(p['track'], p['canale'], p['machine']) for p in parts][:3] == [(1, 1, 'M8 1'), (2, 2, 'M8 1'), (3, 3, 'M8 1')] and len(parts) == 12
              and parts[11]['machine'] == 'Zynthian', 'the parts, their machines and channels (%s)' % parts[:2])
        body = json.dumps([{'key': 'basso', 'canale': 5}]).encode()
        check(req('/api/ableton/canali', body, {'Content-Type': 'application/json'})[0] == 403, 'the channels: only from the hub\'s page (its header)')
        code, _ = req('/api/ableton/canali', body, {'Content-Type': 'application/json', 'X-Sagga-Hub': '1'})
        check(code == 200 and json.load(open(os.path.join(pr, 'ableton.json'))) == {'canali': {'basso': 5}}, 'the channels saved in the library')
        code, _ = req('/api/ableton/canali', json.dumps([{'key': 'basso', 'canale': 0}]).encode(), {'Content-Type': 'application/json', 'X-Sagga-Hub': '1'})
        check(code == 400, 'a channel 0: refused')
        # 0.32.6: the M8's note, with the channels
        hub = {'Content-Type': 'application/json', 'X-Sagga-Hub': '1'}
        js = json.loads(req('/api/ableton/canali')[1])
        check(js.get('nota_m8') is None and js.get('macchine', {}).get('12') == 'Zynthian' and js['macchine']['14'] == 'M8 2'
              and js['parti'][1]['machine'] == 'M8 2', 'no N yet; the machine of every channel; the bass on 5 is on M8 2 (%s)' % js['parti'][1]['machine'])
        code, _ = req('/api/ableton/canali', json.dumps({'canali': [{'key': 'basso', 'canale': 5}], 'nota_m8': 48}).encode(), hub)
        check(code == 200 and json.load(open(os.path.join(pr, 'ableton.json'))) == {'canali': {'basso': 5}, 'nota_m8': 48}
              and json.loads(req('/api/ableton/canali')[1])['nota_m8'] == 48, 'N saved with the channels')
        code, _ = req('/api/ableton/canali', json.dumps([{'key': 'basso', 'canale': 5}]).encode(), hub)
        check(code == 200 and json.load(open(os.path.join(pr, 'ableton.json'))).get('nota_m8') == 48, 'a page of 0.32.3 saves its channels: N stays')
        code, out = req('/api/ableton/canali', json.dumps({'canali': [], 'nota_m8': 300}).encode(), hub)
        check(code == 400 and '0 a 127' in out and json.load(open(os.path.join(pr, 'ableton.json'))).get('nota_m8') == 48, 'N 300: refused, nothing saved')
        body, h = multipart({'nome': 'con n', 'bpm': ''}, clips()[:1])
        code, out = req('/api/ableton', body, h)
        p = os.path.join(pr, 'con n.sgq')
        kick = sorted({st['note'][0] for t, pp, s, st in read_project(open(p, 'rb').read())['steps'] if t == 0 and st['flags'] & 1}) if os.path.isfile(p) else []
        check(code == 200 and 'Nota M8 (N): <b>48</b> (C3' in out and 'diventa la 48' in out and kick == [48],
              'a project made with N: the kick on 48, the report says so (%s)' % kick)
        code, _ = req('/api/ableton/canali', json.dumps({'canali': [{'key': 'basso', 'canale': 5}], 'nota_m8': None}).encode(), hub)
        check(code == 200 and json.load(open(os.path.join(pr, 'ableton.json'))) == {'canali': {'basso': 5}}, 'N emptied')
        body, h = multipart({'nome': 'palette a', 'bpm': ''}, clips()[:4])
        code, out = req('/api/ableton', body, h)
        p = os.path.join(pr, 'palette a.sgq')
        check(code == 200 and 'LE TRACCE' in out and '/edit/palette%20a.sgq' in out and os.path.isfile(p), 'four clips -> a project in the library, its report, the editor\'s link (%d)' % code)
        if os.path.isfile(p):
            dd = read_project(open(p, 'rb').read())
            check(dd['track'][1]['channel'] == 4, 'the bass on the channel saved: 5 (%d)' % (dd['track'][1]['channel'] + 1))
            have = sorted({(t, p) for t, p, s, st in dd['steps'] if st['flags'] & 1})
            check(have == [(0, 0), (0, 1), (1, 0), (4, 0)], 'every file of the upload in the project: kick 1 and 2, bass, hats (%s)' % have)
        code, out = req('/api/ableton', body, h)
        vdir = os.path.join(pr, 'versioni', 'palette a')
        check(code == 200 and os.path.isdir(vdir) and len(os.listdir(vdir)) == 1, 'the same name again: the one before kept among its versions')
        body, h = multipart({'nome': 'x', 'bpm': '500'}, clips()[:1])
        check(req('/api/ableton', body, h)[0] == 400, 'a BPM of 500: refused')
        body, h = multipart({'nome': 'x'}, [('a.txt', b'hello')])
        check(req('/api/ableton', body, h)[0] == 400, 'no .mid: refused')
        body, h = multipart({'nome': '../x'}, clips()[:1])
        check(req('/api/ableton', body, h)[0] == 200 and not os.path.exists(os.path.join(d, 'x.sgq')) and os.path.isfile(os.path.join(pr, 'x.sgq')),
              'a name with a path: only its last part, in the library')
        body, h = multipart({'nome': 'y'}, [('qualcosa.mid', smf([(0, 1, 60, 100)], 1))])
        code, out = req('/api/ableton', body, h)
        check(code == 400 and 'non so che parte' in out, 'nothing to make: said why (%d)' % code)
        t_browser(base, pr)
        srv.shutdown()


def t_browser(base, pr):
    """the section in a real browser (playwright; skipped without it): the table of the parts filled, a channel
    changed and saved from the page, the form there"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('  (skipped: no playwright)')
        return
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 390, 'height': 800})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(base + '/')
        pg.wait_for_function("document.querySelectorAll('#abl input').length == 12", timeout=10000)
        vals = pg.eval_on_selector_all('#abl input', 'els => els.map(e => [e.dataset.k, e.value])')
        check(vals[1] == ['basso', '5'] and vals[0] == ['kick', '1'], 'in the browser: the twelve parts, the channel saved before (%s)' % vals[:2])
        check(pg.input_value('#abln') == '' and 'note del clip' in pg.inner_text('#ablnn'), '0.32.6: the M8\'s note, empty (%r)' % pg.inner_text('#ablnn'))
        pg.fill('#abl input[data-k="pad"]', '13')
        check(pg.inner_text('[data-m="pad"]') == 'M8 2', '0.32.6: the pad on 13: the machine it goes to, as it is typed (%s)' % pg.inner_text('[data-m="pad"]'))
        pg.fill('#abln', '50')
        check("D3 sull'FM-1" in pg.inner_text('#ablnn'), '0.32.6: N 50 is D3 on the FM-1 (%s)' % pg.inner_text('#ablnn'))
        pg.click('text=Salva canali e nota')
        pg.wait_for_function("document.getElementById('ablm').textContent.length > 0", timeout=10000)
        saved = json.load(open(os.path.join(pr, 'ableton.json')))
        check(saved['canali'].get('pad') == 13 and saved['canali'].get('basso') == 5 and saved.get('nota_m8') == 50 and 'salvati' in pg.inner_text('#ablm'),
              'a channel and the M8\'s note changed and saved from the page (%s)' % saved)
        wide = pg.evaluate('document.documentElement.scrollWidth')
        check(wide <= 390 and not errs, 'on a phone: no sideways scroll, no script errors (%s %s)' % (wide, errs[:1]))
        b.close()


def t_install():
    group('installed with the hub')
    sh = open(os.path.join(ROOT, 'tools', 'hub', 'install_hub.sh')).read()
    rel = open(os.path.join(ROOT, 'tools', 'make_release.sh')).read()
    check('"$HERE/hub/sagga_ableton.py"' in sh and 'tools/hub/sagga_ableton.py' in rel, 'install_hub.sh installs it, make_release.sh packs it')


def main():
    build()
    t_install()
    import sagga_ableton as A
    try:
        t_midi(A)
        t_names(A)
        t_build(A)
        t_nota(A)
        t_firmware(A)
        t_page(A)
    finally:
        try:
            os.unlink(SIM)
        except OSError:
            pass
    print('%d checks, %d failed' % (CHECKS[0], len(FAILS)))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
