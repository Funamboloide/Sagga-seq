#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA DA ABLETON (0.32.3): the MIDI clips exported from Ableton Live (right click on a clip, Export MIDI Clip: one
.mid a clip) -> a SAGGA project of STEPS, in the library, for the set's rig: a track for each part, a pattern for each
clip, every track on the channel of the machine that plays that part.

The file's name says the part and the pattern: palette-part-number, A-basso-2.mid = the BASS, pattern 2 (the words
are below, Italian and English; no number: the next pattern free). A clip of the whole kit (drums, batteria, beat ...)
is split by its notes (the General MIDI drums: 35-36 the kick, 37-40 the snare, 42 44 46 the hats, the cymbals TOP,
the rest PERC). Each note goes on the 16th nearest to it, and how far it was stays in the step's NUDGE (+-50 % of a
step): the swing and the push of the clip are kept. Notes of the same pitch twice in a 16th are a RATCHET; up to six
notes at once are a chord; a note that holds into the next one is a TIE. A clip of 1, 2 or 4 bars is a pattern
(shorter ones go round again in the track, as on the FM-1: they are COPIES); 5 to 8 bars take a pair of patterns
(CHAIN: 1+2, 3+4 ...); the only clip of a part longer than 8 bars (up to 16) becomes a TAPE track. The tempo is the
clips'. Scene N plays the N-th clip of every part.

The project is written by sagga_sgqjson, the converter built from the firmware's own core: what the FM-1 loads.

    python3 sagga_ableton.py [-o OUT.sgq] [--nome NAME] [--bpm N] [--canali ableton.json] FILE.mid ...

The rig (the set of 29 December 2026): SAGGA sequences, M8 1 plays the kick and the basses, M8 2 the top drums and the
percussion, the MicroDexed Touch the synths (leads, chords, pads, arps), the Zynthian the long samples (intros,
interludes) besides the mix. The channels are 1-12, track = channel: the Pi's matrix sends them to the machines;
ableton.json (in the library) changes them: {"canali": {"basso": 3, ...}}.
"""
import argparse
import collections
import json
import math
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SGQJSON = os.environ.get('SAGGA_SGQJSON', os.path.join(HERE, 'sagga_sgqjson'))

TRACKS, PATTERNS, STEPS, POLY, BAR = 12, 8, 64, 6, 16       # the core's sizes; a bar = 16 steps of 1/16 (4/4)
DIV_1_16 = 9                                                 # SQ_DIV_1_16
TF_DRUM, TF_CHAIN, TF_TAPE = 0x02, 0x10, 0x20                # SQ_TF_*
ST_ON, ST_SET, ST_TIE, ST_GHOST = 0x01, 0x02, 0x10, 0x40     # SQ_STEP_*
NUDGE_MAX, RATCHET_MAX = 50, 8
TAPE_PPQ, TAPE_BARS_MAX = 384, 16
NAME_LEN = 16
MAX_FILES, MAX_BYTES = 96, 512 * 1024                        # what the page takes at once
CONFIG = 'ableton.json'                                      # in the library: the channels changed from the page

# the parts: key, name on the page, track (0-11), channel (0-15), machine, role (SQ_ROLE_*), a drum, the words of a
# file's name, the note a new step plays (the track's PEN). The groups follow (sagga_gen.c): DRUM tracks = DRUMS, a
# role of the BASS family = BASS, the rest MELODIC
Part = collections.namedtuple('Part', 'key name track channel machine role drum words pen')
PARTS = (
    Part('kick', 'CASSA', 0, 0, 'M8 1', 1, True, ('kick', 'kik', 'cassa', 'bd', 'bassdrum'), 36),
    Part('basso', 'BASSO', 1, 1, 'M8 1', 5, False, ('basso', 'bass', 'bassline', 'sub', '808', 'reese'), 36),
    Part('basso2', 'BASSO 2', 2, 2, 'M8 1', 18, False, ('basso2', 'bass2', 'sub2', 'acid'), 36),
    Part('rullante', 'RULLANTE', 3, 3, 'M8 2', 2, True, ('rullante', 'snare', 'sd', 'clap', 'rim'), 38),
    Part('hat', 'HAT', 4, 4, 'M8 2', 3, True, ('hat', 'hats', 'hh', 'hihat', 'charleston', 'ohat', 'chat', 'openhat'), 42),
    Part('perc', 'PERC', 5, 5, 'M8 2', 4, True, ('perc', 'percs', 'percussioni', 'percussion', 'shaker', 'tom', 'toms',
                                                 'conga', 'bongo', 'cowbell', 'tamb', 'tambourine', 'clave'), 39),
    Part('top', 'TOP', 6, 6, 'M8 2', 10, True, ('top', 'tops', 'ride', 'crash', 'cymbal', 'piatti', 'piatto'), 51),
    Part('lead', 'LEAD', 7, 7, 'MicroDexed', 23, False, ('lead', 'melodia', 'melody', 'hook', 'synth'), 60),
    Part('accordi', 'ACCORDI', 8, 8, 'MicroDexed', 6, False, ('accordi', 'accordo', 'chord', 'chords', 'stab', 'stabs',
                                                              'keys', 'piano', 'rhodes'), 60),
    Part('pad', 'PAD', 9, 9, 'MicroDexed', 21, False, ('pad', 'pads', 'atmo', 'atmosfera', 'drone', 'strings', 'archi'), 60),
    Part('arp', 'ARP', 10, 10, 'MicroDexed', 7, False, ('arp', 'arpeggio', 'seq', 'pluck', 'plucks'), 60),
    Part('sample', 'SAMPLE', 11, 11, 'Zynthian', 0, False, ('sample', 'samples', 'campione', 'intro', 'interludio',
                                                            'outro', 'vox', 'voce', 'fx', 'riser'), 60),
)
KIT_WORDS = ('drums', 'drum', 'batteria', 'beat', 'kit', 'groove', 'loop')   # a clip of the whole kit: split by note
GM_SPLIT = {35: 'kick', 36: 'kick', 37: 'rullante', 38: 'rullante', 39: 'rullante', 40: 'rullante', 42: 'hat',
            44: 'hat', 46: 'hat', 49: 'top', 51: 'top', 52: 'top', 53: 'top', 55: 'top', 57: 'top', 59: 'top'}
NUM_WORDS = re.compile(r'^\d{1,2}$')


class AbletonError(Exception):
    """what is wrong, said for the page"""


def project_name(text):
    """the name as the FM-1 shows it (upper case, its characters, 16 at most): the editor's own rule"""
    try:
        sys.path.insert(0, HERE)
        import sagga_editor
        return sagga_editor.project_name(text)
    except ImportError:                                     # (alone, out of the hub: the same rule, simpler)
        t = os.path.splitext(os.path.basename(text or ''))[0].upper()
        return ''.join(c if c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_.+' else '_' for c in t).strip()[:NAME_LEN].rstrip()


# ------------------------------------------------------------------------------------------------ the MIDI file
def _varlen(b, i):
    v = 0
    for _ in range(4):
        if i >= len(b):
            raise AbletonError('il file finisce a metà')
        c = b[i]
        i += 1
        v = (v << 7) | (c & 0x7F)
        if not c & 0x80:
            return v, i
    raise AbletonError('un numero troppo lungo nel file')


def read_midi(data):
    """a Standard MIDI File -> dict(ppq, tempo (us a quarter, the first, or None), sig (num, den) or None, end (the
    last event's tick), notes [(on, off, note, vel)] in ticks, names [the tracks' names], other (CC, bend ... seen))"""
    if len(data) < 14 or data[:4] != b'MThd':
        raise AbletonError('non è un file MIDI')
    hlen = int.from_bytes(data[4:8], 'big')
    fmt, ntrk, div = (int.from_bytes(data[8 + 2 * k:10 + 2 * k], 'big') for k in range(3))
    if fmt > 2:
        raise AbletonError('formato MIDI %d sconosciuto' % fmt)
    if div & 0x8000 or not div:
        raise AbletonError('il tempo SMPTE non è gestito: esporta il clip da Ableton')
    pos = 8 + hlen
    notes, names, tempo, sig, end, other = [], [], None, None, 0, 0
    for _ in range(ntrk):
        while pos + 8 <= len(data) and data[pos:pos + 4] != b'MTrk':       # (a chunk of another kind: skipped)
            pos += 8 + int.from_bytes(data[pos + 4:pos + 8], 'big')
        if pos + 8 > len(data):
            raise AbletonError('il file finisce a metà (%d tracce su %d)' % (_, ntrk))
        tlen = int.from_bytes(data[pos + 4:pos + 8], 'big')
        if pos + 8 + tlen > len(data):
            raise AbletonError('il file finisce a metà')
        trk = data[pos + 8:pos + 8 + tlen]
        pos += 8 + tlen
        t, i, status, held = 0, 0, 0, {}
        while i < len(trk):
            d, i = _varlen(trk, i)
            t += d
            if i >= len(trk):
                break
            b = trk[i]
            if b == 0xFF:
                if i + 1 >= len(trk):
                    raise AbletonError('il file finisce a metà')
                kind = trk[i + 1]
                n, i = _varlen(trk, i + 2)
                body = trk[i:i + n]
                i += n
                if kind == 0x2F:
                    break
                if kind == 0x51 and n == 3 and tempo is None:
                    tempo = int.from_bytes(body, 'big')
                elif kind == 0x58 and n >= 2 and sig is None:
                    sig = (body[0], 1 << body[1])
                elif kind in (0x03, 0x01) and body:
                    names.append(body.decode('utf-8', 'replace'))
                continue
            if b in (0xF0, 0xF7):
                n, i = _varlen(trk, i + 1)
                i += n
                continue
            if b & 0x80:
                status = b
                i += 1
            elif not status:
                raise AbletonError('un evento senza stato nel file')
            k, ch = status & 0xF0, status & 0x0F
            if k == 0xF0:
                raise AbletonError('un evento di sistema in mezzo alle note')
            n = 1 if k in (0xC0, 0xD0) else 2
            ev = trk[i:i + n]
            i += n
            if len(ev) < n:
                raise AbletonError('il file finisce a metà')
            if k == 0x90 and ev[1]:
                held.setdefault((ch, ev[0]), []).append((t, ev[1]))
            elif k == 0x80 or k == 0x90:
                q = held.get((ch, ev[0]))
                if q:
                    on, v = q.pop(0)
                    notes.append((on, t, ev[0], v))
            elif k in (0xA0, 0xB0, 0xD0, 0xE0):
                other += 1
        for (ch, nt), q in held.items():                 # (a note never let go ends with its track)
            for on, v in q:
                notes.append((on, max(t, on + 1), nt, v))
        end = max(end, t)
    notes.sort()
    return dict(ppq=div, tempo=tempo, sig=sig, end=end, notes=notes, names=names, other=other)


# ------------------------------------------------------------------------------------------------ the parts
def rig(config=None):
    """the parts with the channels of the config (a dict: {"canali": {part: 1-16}}) -> [Part]"""
    ch = (config or {}).get('canali') or {}
    out = []
    for p in PARTS:
        c = ch.get(p.key)
        if isinstance(c, int) and not isinstance(c, bool) and 1 <= c <= 16:
            p = p._replace(channel=c - 1)
        out.append(p)
    return out


def load_config(folder):
    try:
        with open(os.path.join(folder, CONFIG)) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def config_from_page(items):
    """the page's table [{"key": part, "canale": 1-16}] -> the config to save; AbletonError if a value is wrong"""
    keys = {p.key for p in PARTS}
    ch = {}
    if not isinstance(items, list):
        raise AbletonError('canali non validi')
    for it in items:
        if not isinstance(it, dict) or it.get('key') not in keys:
            raise AbletonError('parte sconosciuta: %r' % (it.get('key') if isinstance(it, dict) else it))
        c = it.get('canale')
        if isinstance(c, bool) or not isinstance(c, int) or not 1 <= c <= 16:
            raise AbletonError('%s: il canale va da 1 a 16' % it['key'])
        ch[it['key']] = c
    return {'canali': ch}


def _words(text):
    return [w for w in re.split(r'[^a-z0-9]+', (text or '').lower()) if w]


def classify(name, track_names, parts):
    """a file -> (the part's key, 'kit' or None, the pattern number 1-8 or None)"""
    by_word = {}
    for p in parts:
        for w in p.words:
            by_word.setdefault(w, p.key)
    base = os.path.splitext(os.path.basename(name))[0]
    for source in [base] + list(track_names):
        for w in _words(source):
            if w in by_word:
                part = by_word[w]
                break
            if w in KIT_WORDS:
                part = 'kit'
                break
        else:
            continue
        break
    else:
        part = None
    num = None
    for w in reversed(_words(base)):
        if NUM_WORDS.match(w) and 1 <= int(w) <= PATTERNS:
            num = int(w)
            break
    return part, num


# ------------------------------------------------------------------------------------------------ the steps
def _n(k, one, many):
    """'1 nota', '3 note': the count and its word"""
    return '%d %s' % (k, one if k == 1 else many)


def gate_code(d):
    """a note's length in steps -> the step's length (1-100 % of a step, 101 = 1.5 steps, 102-164 = 2-64 steps)"""
    if d <= 1.0 + 1e-6:
        return max(1, min(100, int(round(d * 100))))
    if d < 1.25:                                     # (the nearest of a step, a step and a half, two ...)
        return 100
    if d < 1.75:
        return 101
    return 100 + max(2, min(STEPS, int(round(d))))


def clip_steps(notes, own, drum, warn):
    """notes [(on, off, note, vel)] in steps (from the clip's start) -> {step: dict(notes, vel, len, nudge, rat, flags)}
    in 0 .. own-1"""
    cells = collections.defaultdict(list)
    for on, off, n, v in notes:
        s = min(int(math.floor(on + 0.5)), own - 1)     # (a note just before the loop's end stays at its end, late)
        cells[s].append((on - s, max(off - on, 0.01), n, v, on))
    onsets = sorted(set(round(e[4], 4) for c in cells.values() for e in c))
    out = {}
    many = tight = 0
    for s, evs in sorted(cells.items()):
        evs.sort(key=lambda e: (e[4], e[2]))
        count = collections.Counter(e[2] for e in evs)
        rat = max(count.values())
        pitches = sorted(count)
        if len(pitches) > POLY:
            many += 1
            if drum:                                   # the loudest drums stay
                loud = sorted(pitches, key=lambda n: -max(e[3] for e in evs if e[2] == n))[:POLY]
                pitches = sorted(loud)
            else:                                      # the lowest notes of a chord stay
                pitches = pitches[:POLY]
        if rat > 1 and len(set(count.values())) > 1:
            tight += 1
        first = evs[0]
        nudge = max(-NUDGE_MAX, min(NUDGE_MAX, int(round(first[0] * 100))))
        rat = min(rat, RATCHET_MAX)
        d = max(e[1] for e in evs)
        if rat > 1:                                    # the gate is a % of a slice of the step
            d = min(1.0, min(e[1] for e in evs if e[2] == first[2]) * rat)
        flags = ST_ON | ST_SET
        if not drum:
            # legato: a note that holds past the start of a note on the NEXT step is a TIE (on the FM-1 it holds into
            # that step, 15 ms over: a mono synth slides). Further away, its length says how long it lasts
            end = max(e[4] + e[1] for e in evs)
            nxt = [o for o in onsets if o > first[4] + 0.05]
            if nxt and end > nxt[0] + 0.02 and int(math.floor(nxt[0] + 0.5)) == s + 1:
                flags |= ST_TIE
        out[s] = dict(notes=pitches, vel=max(e[3] for e in evs), len=gate_code(d) if not flags & ST_TIE else 100,
                      nudge=nudge, rat=rat, flags=flags)
    if many:
        warn('%s con più di %d note insieme: tenute %s' % (_n(many, 'passo', 'passi'), POLY, 'le più forti' if drum else 'le più basse'))
    if tight:
        warn('%s con note ripetute e altre no: il ratchet le ripete tutte' % _n(tight, 'passo', 'passi'))
    return out


def _lcm_len(lengths):
    L = 1
    for n in lengths:
        L = L * n // math.gcd(L, n)
    return L


# ------------------------------------------------------------------------------------------------ the project
def build(files, name='ABLETON', config=None, bpm=None):
    """files [(file name, bytes)] -> (the .sgq's bytes, report). The report: name, bpm, tracks [...], files [...],
    warnings [...]; AbletonError when nothing can be made"""
    parts = rig(config)
    by_key = {p.key: p for p in parts}
    if not files:
        raise AbletonError('nessun file')
    if len(files) > MAX_FILES:
        raise AbletonError('troppi file (al massimo %d)' % MAX_FILES)
    report = dict(name=name, bpm=None, tracks=[], files=[], warnings=[])
    clips = collections.defaultdict(list)            # part -> [dict(num, file, notes (steps), bars, warn)]
    tempos = collections.Counter()
    for fname, data in sorted(files, key=lambda f: f[0].lower()):
        fr = dict(file=os.path.basename(fname), part=None, patterns=[], notes=0, bars=0, warnings=[])
        report['files'].append(fr)
        if len(data) > MAX_BYTES:
            fr['warnings'].append('troppo grande (al massimo %d kB): lasciato fuori' % (MAX_BYTES // 1024))
            continue
        try:
            m = read_midi(data)
        except AbletonError as e:
            fr['warnings'].append('%s: lasciato fuori' % e)
            continue
        part, num = classify(fname, m['names'], parts)
        if part is None:
            fr['warnings'].append('non so che parte è: rinominalo palette-parte-numero (le parti: %s)'
                                  % ', '.join(p.key for p in parts))
            continue
        if not m['notes']:
            fr['warnings'].append('nessuna nota: lasciato fuori')
            continue
        if m['tempo']:
            tempos[round(60e6 / m['tempo'], 2)] += 1
        if m['sig'] and m['sig'] != (4, 4):
            fr['warnings'].append('in %d/%d: letto come 4/4' % m['sig'])
        if m['other']:
            fr['warnings'].append('%s (CC, pitch bend) non importati' % _n(m['other'], 'controllo', 'controlli'))
        q = m['ppq'] / 4.0                                       # ticks a 16th
        last_on = max(n[0] for n in m['notes'])
        length = m['end'] if m['end'] > last_on else max(n[1] for n in m['notes'])
        bars = max(1, int(math.ceil(length / (q * BAR) - 0.05)))
        notes = [(on / q, off / q, n, v) for on, off, n, v in m['notes']]
        fr['notes'], fr['bars'] = len(notes), bars
        if part == 'kit':
            split = collections.defaultdict(list)
            for nt in notes:
                split[GM_SPLIT.get(nt[2], 'perc')].append(nt)
            fr['part'] = 'kit: ' + ', '.join(sorted(split, key=lambda k: by_key[k].track))
            for k, ns in split.items():
                clips[k].append(dict(num=num, file=fr, notes=ns, bars=bars))
        else:
            fr['part'] = part
            clips[part].append(dict(num=num, file=fr, notes=notes, bars=bars))
    if tempos:
        report['bpm'] = tempos.most_common(1)[0][0]
        if len(tempos) > 1:
            report['warnings'].append('i clip hanno tempi diversi (%s): uso %s'
                                      % (', '.join('%g' % t for t in sorted(tempos)), '%g' % report['bpm']))
    if bpm:
        report['bpm'] = bpm
    if not report['bpm']:
        report['warnings'].append('il tempo non è nei file: il progetto resta a 128 BPM, cambialo sull\'FM-1 o qui (BPM)')
    if not clips:
        raise AbletonError('nessun clip da importare: ' + '; '.join('%s: %s' % (f['file'], ' '.join(f['warnings']))
                                                                     for f in report['files']))

    base = ['project - bpm - %d' % max(20, min(300, int(round(report['bpm'] or 128))))]
    nm = project_name(name)
    for i in range(NAME_LEN):
        base.append('ext - name %d %d' % (i, ord(nm[i]) if i < len(nm) else 0))
    lines = []
    scenes = 0
    for p in parts:
        t = p.track
        cl = clips.get(p.key, [])
        flags = TF_DRUM if p.drum else 0
        tr = dict(channel=p.channel, division=DIV_1_16, role=p.role, pen=p.pen, swing=50, length=BAR)
        info = dict(track=t + 1, part=p.key, name=p.name, machine=p.machine, channel=p.channel + 1, mode='', patterns=[],
                    length=0)
        if cl:
            if p.drum:
                common = collections.Counter(n[2] for c in cl for n in c['notes']).most_common()
                tr['pen'] = common[0][0]
                if len(common) > 1 and p.key not in ('kick',):
                    others = ' '.join(str(n) for n, _ in common[:8])
                    info['note'] = 'note diverse sullo stesso canale (%s): sull\'M8 uno strumento a slice, o un clip per suono' % others
            # the patterns: the clip's number, else the next free; a number taken: the next free
            longest = max(c['bars'] for c in cl)
            mode = 'tape' if longest > 8 and len(cl) == 1 else 'chain' if longest > 4 else 'steps'
            slots = PATTERNS // 2 if mode == 'chain' else PATTERNS if mode == 'steps' else 1
            used = {}
            for c in sorted(cl, key=lambda c: (c['num'] is None, c['num'] or 0, c['file']['file'])):
                k = c['num'] - 1 if c['num'] and c['num'] <= slots else None
                if k is None or k in used:
                    free = [j for j in range(slots) if j not in used]
                    if not free:
                        c['file']['warnings'].append('%s: non c\'è più posto (%d pattern): lasciato fuori' % (p.key, slots))
                        continue
                    if c['num']:
                        c['file']['warnings'].append('%s: il pattern %d è già preso, va nel %d' % (p.key, c['num'], free[0] + 1))
                    k = free[0]
                used[k] = c
            if mode == 'tape':
                c = used[0]
                bars = min(c['bars'], TAPE_BARS_MAX)
                if c['bars'] > TAPE_BARS_MAX:
                    c['file']['warnings'].append('%d battute: una traccia TAPE ne tiene %d, il resto è fuori'
                                                 % (c['bars'], TAPE_BARS_MAX))
                flags |= TF_TAPE
                tr['tape_bars'] = bars
                lines.append('tape %d clear - 0' % t)
                k = TAPE_PPQ / 4.0
                lim = bars * BAR * k
                kept = 0
                for on, off, n, v in c['notes']:
                    a = int(round(on * k))
                    if a >= lim:
                        continue
                    dur = max(1, min(int(round((off - on) * k)), int(lim) - a))
                    lines.append('tape %d,%d,%d,%d add - %d' % (t, a, dur, n, v))
                    kept += 1
                if kept < len(c['notes']):
                    c['file']['warnings'].append('%s fuori dalle %d battute' % (_n(len(c['notes']) - kept, 'nota', 'note'), bars))
                c['file']['patterns'].append('TAPE %d battute' % bars)
                info.update(mode='TAPE', patterns=['%d battute' % bars], length=bars * BAR)
                scenes = max(scenes, 1)
            else:
                if mode == 'chain':
                    flags |= TF_CHAIN
                    tr['length'] = STEPS
                else:
                    lens = sorted({min(c['bars'], 4) * BAR for c in used.values()})
                    L = _lcm_len(lens)
                    tr['length'] = L if L <= STEPS else STEPS
                    if L > STEPS:
                        info['note'] = ('clip di %s battute nella stessa traccia: in 4 battute i più corti ricominciano'
                                        % '+'.join(str(n // BAR) for n in lens))
                info.update(mode='CHAIN' if mode == 'chain' else 'passi', length=tr['length'])
                for k, c in sorted(used.items()):
                    w = c['file']['warnings'].append
                    if mode == 'chain':
                        a = 2 * k
                        bars = min(c['bars'], 8)
                        if c['bars'] > 8:
                            w('%d battute: in una coppia di pattern ne stanno 8, il resto è fuori' % c['bars'])
                        elif 4 < bars < 8:
                            w('%d battute: suona in 8, le ultime %d in silenzio' % (bars, 8 - bars))
                        notes = [n for n in c['notes'] if n[0] < bars * BAR]
                        if bars <= 4:                    # a short clip in a CHAIN track: the same in both halves
                            st = clip_steps(notes, bars * BAR, p.drum, w)
                            for half in (a, a + 1):
                                lines += _pattern_lines(t, half, st, bars * BAR, STEPS)
                        else:
                            st = clip_steps(notes, bars * BAR, p.drum, w)
                            lines += _pattern_lines(t, a, {s: v for s, v in st.items() if s < STEPS}, STEPS, STEPS)
                            lines += _pattern_lines(t, a + 1, {s - STEPS: v for s, v in st.items() if s >= STEPS},
                                                    bars * BAR - STEPS, STEPS, copies=False)
                        c['file']['patterns'].append('%d+%d' % (a + 1, a + 2))
                        info['patterns'].append('%d+%d' % (a + 1, a + 2))
                    else:
                        bars = c['bars']
                        if bars > 4:
                            w('%d battute: un pattern ne tiene 4, il resto è fuori' % bars)
                            bars = 4
                        if bars == 3 and tr['length'] == STEPS:
                            w('3 battute in una traccia di 4: la quarta ripete la prima')
                        own = bars * BAR
                        notes = [n for n in c['notes'] if n[0] < own]
                        if len(notes) < len(c['notes']):
                            w('%s dopo la battuta %d: fuori' % (_n(len(c['notes']) - len(notes), 'nota', 'note'), bars))
                        st = clip_steps(notes, own, p.drum, w)
                        lines += _pattern_lines(t, k, st, own, tr['length'])
                        c['file']['patterns'].append(str(k + 1))
                        info['patterns'].append(str(k + 1))
                scenes = max(scenes, max(used) + 1)
                tr['initial_pattern'] = 2 * min(used) if mode == 'chain' else min(used)
                info['used'] = sorted(used)
                info['chain'] = mode == 'chain'
            report['tracks'].append(info)
        tr['flags'] = flags
        for k, v in tr.items():
            base.append('track %d %s - %d' % (t, k, v))
    # the scenes: scene N plays the N-th clip of every part (a part with fewer: its last)
    for s in range(scenes):
        for info in report['tracks']:
            if 'used' not in info:
                continue
            have = [k for k in info['used'] if k <= s] or [min(info['used'])]
            k = max(have)
            lines.append('scene %d pattern %d %d' % (s, info['track'] - 1, 2 * k if info['chain'] else k))
    report['scenes'] = scenes
    for info in report['tracks']:
        info.pop('used', None)
        info.pop('chain', None)
    return _apply(base, lines), report


def _pattern_lines(t, pat, steps, own, length, copies=True):
    """a pattern's own steps (0 .. own-1), and from own to the track's length the COPIES (flag 64 on each: the
    converter makes them again from the pattern, as the FM-1 does)"""
    out = []
    for s, d in sorted(steps.items()):
        if not 0 <= s < own:
            continue
        idx = '%d,%d,%d' % (t, pat, s)
        for k in range(POLY):
            out.append('step %s note %d %d' % (idx, k, d['notes'][k] if k < len(d['notes']) else 255))
        out.append('step %s velocity - %d' % (idx, max(1, min(127, d['vel']))))
        out.append('step %s length - %d' % (idx, d['len']))
        out.append('step %s ratchet - %d' % (idx, d['rat']))
        out.append('step %s nudge - %d' % (idx, d['nudge']))
        out.append('step %s flags - %d' % (idx, d['flags']))
    if copies and steps and own < length:
        for s in range(own, length):
            out.append('step %d,%d,%d flags - %d' % (t, pat, s, ST_GHOST))
    return out


def _tool(args):
    if not os.path.isfile(SGQJSON):
        raise AbletonError('convertitore non installato (sagga_sgqjson): rilancia install_hub.sh')
    r = subprocess.run([SGQJSON] + args, capture_output=True, text=True, timeout=60)
    if r.returncode:
        raise AbletonError('sagga_sgqjson: %s' % ((r.stderr or r.stdout).strip() or 'errore %d' % r.returncode))
    return r.stdout


def _apply(base, lines):
    """two passes, as the FM-1 would: the tracks first (their lengths on empty patterns: nothing to fit), then the
    steps and the scenes"""
    with tempfile.TemporaryDirectory() as td:
        p1, p2 = os.path.join(td, 'base.txt'), os.path.join(td, 'steps.txt')
        b, out = os.path.join(td, 'base.sgq'), os.path.join(td, 'out.sgq')
        with open(p1, 'w') as f:
            f.write('\n'.join(base) + '\n')
        with open(p2, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        _tool(['apply', 'new', p1, b])
        _tool(['apply', b, p2, out])
        with open(out, 'rb') as f:
            return f.read()


# ------------------------------------------------------------------------------------------------ the report
def report_text(rep):
    """the report, for a terminal"""
    L = ['%s: %d tracce, %d scene, %s BPM' % (rep['name'], len(rep['tracks']), rep.get('scenes', 0),
                                              '%g' % rep['bpm'] if rep['bpm'] else '128 (non nei file)')]
    for t in rep['tracks']:
        L.append('  traccia %2d %-9s %-11s canale %2d  %s %s' % (t['track'], t['name'], t['machine'], t['channel'], t['mode'],
                                                                ' '.join(t['patterns'])))
        if t.get('note'):
            L.append('      ' + t['note'])
    for f in rep['files']:
        if f['warnings'] or not f['patterns']:
            L.append('  %s: %s' % (f['file'], '; '.join(f['warnings']) or 'non importato'))
    for w in rep['warnings']:
        L.append('  ' + w)
    return '\n'.join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('files', nargs='+')
    ap.add_argument('-o', '--out')
    ap.add_argument('--nome', default=None)
    ap.add_argument('--bpm', type=float, default=None)
    ap.add_argument('--canali', default=None, help='ableton.json: {"canali": {"basso": 3, ...}}')
    a = ap.parse_args(argv)
    cfg = {}
    if a.canali:
        with open(a.canali) as f:
            cfg = json.load(f)
    name = a.nome or (os.path.splitext(os.path.basename(a.out))[0] if a.out else 'ABLETON')
    files = []
    for p in a.files:
        with open(p, 'rb') as f:
            files.append((os.path.basename(p), f.read()))
    try:
        data, rep = build(files, name, cfg, a.bpm)
    except AbletonError as e:
        print('errore: %s' % e, file=sys.stderr)
        return 2
    out = a.out or name + '.sgq'
    with open(out, 'wb') as f:
        f.write(data)
    print(report_text(rep))
    print('scritto %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
