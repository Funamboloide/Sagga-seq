#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA SEQ 0.11: the chord progressions the Pi keeps for the FM-1 (the grid bridge serves them, the SAGGA HUB page
lists them).

One text file a genre in <the projects folder>/progressions (TECHNO.txt ...): a line a progression,
MOOD <tab> chords [<tab> a name]; '#' starts a comment. The chords are written above the key's root, whatever the key:
I bII II bIII III IV #IV V bVI VI bVII VII, small for a minor chord (i, bvii, iv7 ...), then the shape (maj7, 9, sus2,
o for diminished ... see SHAPES), then, if it has its own, the length in 16ths (:8) and how many 16ths early it comes in
(^1). "i bVI bVII i", "ii7:8 V7:8 Imaj7", "Isus2 IVsus2^1". The mood is one of MOODS (ANY: none given).

The first time a genre is changed, its file is started from the stock one (tools/hub/progressions, written by
tools/gen_progs.py). The FM-1 asks for the progressions of a genre and a mood in order of likeness to the one it plays:
ordered() is that order. Standard library only.
"""
import os
import re

try:
    from sagga_patterns import GENRES, RETIRED
except ImportError:                                   # (alone: the same lists, the FM-1's order; 0.29: 22 genres)
    GENRES = ['TECHNO', 'HARDTECHNO', 'DUBTECHNO', 'HOUSE', 'UKGARAGE', 'UKFUNKY', 'DUBSTEP', 'JUNGLE',
              'REGGAETON', 'BATIDA', 'GQOM', 'EXPERIMENTAL', 'ELECTRO', 'DNB', 'BALANI', 'FOOTWORK', 'TRANCE',
              'UKDRILL', 'HARDCORE', 'PHONK', 'BAILEFUNK', 'MERENGUE']
    RETIRED = {'AMAPIANO': 'REGGAETON', 'BASSLINE': 'UKGARAGE', 'GRIME': 'DUBSTEP', 'AFROHOUSE': 'GQOM'}
RETIRED_MARK = '# 0.29: the progressions you kept in %s (a genre that left the library) are here, after these'

# sagga_seq_core.h SQ_MOOD_*
MOODS = ['ANY', 'SAD', 'MELANCHOLY', 'SATISFYING', 'ENERGETIC', 'EUPHORIC', 'EPIC', 'DREAMY', 'DARK', 'TENSE', 'SUSPENDED']
# the chord shapes SQ_CH_* 1..31: (small: a minor or diminished chord, its suffix); the FM-1 sends SQ_HSHAPE_CH + it
SHAPE_CH = 5
SHAPES = {1: (False, '8'), 2: (False, '5'), 3: (False, '5/8'), 4: (False, ''), 5: (True, ''), 6: (True, 'o'),
          7: (False, '+'), 8: (False, 'sus2'), 9: (False, 'sus4'), 10: (False, '6'), 11: (True, '6'), 12: (False, '7'),
          13: (True, '7'), 14: (False, 'maj7'), 15: (True, 'mM7'), 16: (True, 'o7'), 17: (True, 'm7b5'),
          18: (False, '7sus4'), 19: (False, 'add9'), 20: (True, 'add9'), 21: (False, '9'), 22: (True, '9'),
          23: (False, 'maj9'), 24: (False, '9sus4'), 25: (False, '6/9'), 26: (True, '6/9'), 27: (True, '11'),
          28: (False, '13'), 29: (False, '7sh'), 30: (True, 'sh'), 31: (False, '1358')}
_BY_NAME = {(small, suf): k for k, (small, suf) in SHAPES.items()}
_ALIAS = {(True, 'ø'): 17, (True, 'ø7'): 17, (False, 'M7'): 14, (False, 'Δ'): 14, (False, 'Δ7'): 14, (True, 'm7'): 13,
          (True, 'm'): 5, (False, 'dim'): 6, (True, 'dim'): 6, (False, 'aug'): 7, (True, 'min7'): 13}
# the kind of each shape (for likeness): 0 major 1 minor 2 diminished 3 augmented 4 no third (sus, power)
KIND = {1: 4, 2: 4, 3: 4, 4: 0, 5: 1, 6: 2, 7: 3, 8: 4, 9: 4, 10: 0, 11: 1, 12: 0, 13: 1, 14: 0, 15: 1, 16: 2, 17: 2,
        18: 4, 19: 0, 20: 1, 21: 0, 22: 1, 23: 0, 24: 4, 25: 0, 26: 1, 27: 1, 28: 0, 29: 0, 30: 1, 31: 0}
ROMAN = ['I', 'bII', 'II', 'bIII', 'III', 'IV', '#IV', 'V', 'bVI', 'VI', 'bVII', 'VII']
_NUM = {'I': 0, 'II': 2, 'III': 4, 'IV': 5, 'V': 7, 'VI': 9, 'VII': 11}
_TOKEN = re.compile(r'^([b#]?)(VII|VI|IV|V|III|II|I|vii|vi|iv|v|iii|ii|i)([^:^]*)(?::(\d+))?(?:\^(\d))?$')
MAX_CHORDS = 8
STOCK = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'progressions')


def chord(token):
    """'bVImaj7:8^1' -> (semi, shape, dur, push) (shape: SQ_HSHAPE_CH + SQ_CH_*); ValueError if it is not one"""
    m = _TOKEN.match(token.strip())
    if not m:
        raise ValueError('not a chord: %r' % token)
    acc, num, suf, dur, push = m.groups()
    semi = (_NUM[num.upper()] + (-1 if acc == 'b' else 1 if acc == '#' else 0)) % 12
    small = num.islower()
    k = _BY_NAME.get((small, suf)) or _ALIAS.get((small, suf)) or _BY_NAME.get((not small, suf))
    if not k:
        raise ValueError('not a chord shape: %r' % token)
    dur = int(dur) if dur else 0
    push = int(push) if push else 0
    if not 0 <= dur <= 64 or not 0 <= push <= 4:
        raise ValueError('a length 1..64 16ths, a push 0..4: %r' % token)
    return semi, SHAPE_CH + k, dur, push


def chord_name(semi, shape, dur=0, push=0):
    """(10, 19, 8, 0) -> 'bVIIadd9:8'"""
    small, suf = SHAPES.get(shape - SHAPE_CH, (False, '?'))
    r = ROMAN[semi % 12]
    if small:
        r = r.lower()
    return r + suf + (':%d' % dur if dur else '') + ('^%d' % push if push else '')


def parse(text):
    """'i bVI bVII i' -> [(semi, shape, dur, push)]; ValueError if not a progression"""
    rows = [chord(t) for t in text.replace(',', ' ').replace('-', ' ').split()]
    if not 1 <= len(rows) <= MAX_CHORDS:
        raise ValueError('a progression: 1 to %d chords' % MAX_CHORDS)
    return rows


def name(rows):
    return ' '.join(chord_name(*r) for r in rows)


def valid(rows):
    """None if rows (from the FM-1) are a progression, else why not"""
    if not 1 <= len(rows) <= MAX_CHORDS:
        return 'a progression: 1 to %d chords' % MAX_CHORDS
    for semi, shape, dur, push in rows:
        if not 0 <= semi <= 11 or shape - SHAPE_CH not in SHAPES or not 0 <= dur <= 64 or not 0 <= push <= 4:
            return 'not a chord: %r' % ((semi, shape, dur, push),)
    return None


def distance(ref, rows):
    """how unlike two progressions are (0: the same): chord by chord, the roots (a fifth apart: nearer), the kinds; the
    one turned to start where it is most alike (a little dearer), and the chords one has more"""
    if not ref:
        return 0.0
    a = [(s % 12, KIND.get(sh - SHAPE_CH, 0)) for s, sh in ref]
    best = None
    for rot in range(len(rows)):
        b = [(r[0] % 12, KIND.get(r[1] - SHAPE_CH, 0)) for r in rows[rot:] + rows[:rot]]
        cost = 0.3 * (rot > 0)
        for i in range(max(len(a), len(b))):
            if i >= len(a) or i >= len(b):
                cost += 2.0
                continue
            (ra, ka), (rb, kb) = a[i], b[i]
            if ra != rb:
                cost += 1.0 if (ra - rb) % 12 in (5, 7) else 1.5
            if ka != kb:
                cost += 0.5
        best = cost if best is None else min(best, cost)
    return best


class Progressions:
    """the files of one folder; writer(path, data) writes a file (the BootWriter's write: the folder may be on a
    partition kept read-only)"""

    def __init__(self, folder, stock=STOCK, writer=None):
        self.folder, self.stock = folder, stock
        self.writer = writer

    def _file(self, genre):
        mine = os.path.join(self.folder, '%s.txt' % genre)
        if os.path.isfile(mine):
            return mine
        theirs = os.path.join(self.stock, '%s.txt' % genre) if self.stock else None
        return theirs if theirs and os.path.isfile(theirs) else None

    def lines(self, genre):
        path = self._file(genre)
        if not path:
            return []
        try:
            with open(path, encoding='utf-8') as f:
                return f.read().splitlines()
        except OSError:
            return []

    def entries(self, genre):
        """[(line number, mood, rows, name)] of a genre, in the file's order (lines that are not one: left out)"""
        out = []
        for i, ln in enumerate(self.lines(genre)):
            s = ln.strip()
            if not s or s.startswith('#'):
                continue
            f = s.split('\t')
            if len(f) < 2:
                f = s.split(None, 1)
                if len(f) < 2:
                    continue
            mood = f[0].strip().upper()
            if mood == '-':
                mood = 'ANY'
            if mood not in MOODS:
                continue
            try:
                rows = parse(f[1])
            except ValueError:
                continue
            out.append((i, mood, rows, f[2].strip() if len(f) > 2 else ''))
        return out

    def of(self, genre, mood='ANY'):
        """the progressions of a genre with that mood (ANY: all), in the file's order: [(mood, rows, name)]"""
        return [(m, r, n) for _, m, r, n in self.entries(genre) if mood == 'ANY' or m == mood]

    def ordered(self, genre, mood='ANY', ref=None):
        """of(), the most like ref [(semi, shape)] first (equal: the file's order)"""
        got = self.of(genre, mood)
        if not ref:
            return got
        return [e for _, e in sorted(enumerate(got), key=lambda ie: (distance(ref, ie[1][1]), ie[0]))]

    def summary(self):
        """{genre: {mood: count}}"""
        out = {}
        for g in GENRES:
            c = {}
            for _, m, _, _ in self.entries(g):
                c[m] = c.get(m, 0) + 1
            out[g] = c
        return out

    def _write(self, genre, lines):
        path = os.path.join(self.folder, '%s.txt' % genre)
        data = ('\n'.join(lines) + '\n').encode('utf-8')
        if self.writer:
            self.writer(path, data)
        else:
            os.makedirs(self.folder, exist_ok=True)
            tmp = path + '.part'
            with open(tmp, 'wb') as f:
                f.write(data)
            os.replace(tmp, path)

    def add(self, genre, mood, rows, label=''):
        """keeps a new progression at the end of the genre's file; returns its number among those of its mood"""
        if genre not in GENRES:
            raise ValueError('no such genre')
        if mood not in MOODS:
            raise ValueError('no such mood')
        why = valid(rows)
        if why:
            raise ValueError(why)
        lines = self.lines(genre) or ['# SAGGA SEQ 0.11 progressions, %s: MOOD, the chords above the key\'s root, a name.' % genre]
        lines.append('%s\t%s%s' % (mood, name(rows), '\t' + label if label else ''))
        self._write(genre, lines)
        return len(self.of(genre, mood)) - 1

    def retire(self):
        """0.29: the progressions you kept yourself in a genre that left the library go to the end of the genre it went
        into (the old file is left as it was). Once: the genre's file says so. -> how many moved"""
        moved = 0
        for old, new in RETIRED.items():
            if not os.path.isfile(os.path.join(self.folder, '%s.txt' % old)):
                continue
            mark = RETIRED_MARK % old
            lines = self.lines(new)
            if any(ln.startswith(mark) for ln in lines):
                continue
            stock = set()
            path = os.path.join(self.stock, 'retired', '%s.txt' % old) if self.stock else None
            if path and os.path.isfile(path):
                stock = {(m, tuple(r)) for _, m, r, _ in Progressions(os.path.join(self.stock, 'retired'), stock=None).entries(old)}
            yours = [(m, r, nm) for _, m, r, nm in Progressions(self.folder, stock=None).entries(old) if (m, tuple(r)) not in stock]
            if not yours:
                continue
            lines = lines or ['# SAGGA SEQ 0.11 progressions, %s: MOOD, the chords above the key\'s root, a name.' % new]
            lines.append(mark)
            for mood, rows, label in yours:
                if valid(rows):
                    continue
                lines.append('%s\t%s%s' % (mood, name(rows), '\t' + label if label else ''))
                moved += 1
            self._write(new, lines)
        return moved

    def delete(self, genre, k):
        """takes progression k (of all the genre's, in the file's order) away; True if there was one"""
        ents = self.entries(genre)
        if genre not in GENRES or not 0 <= k < len(ents):
            return False
        drop = ents[k][0]
        self._write(genre, [ln for i, ln in enumerate(self.lines(genre)) if i != drop])
        return True
