#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA SEQ 0.11: the patterns the Pi keeps for the FM-1 (the grid bridge serves them, the SAGGA HUB page lists them).

One text file a genre in <the projects folder>/patterns (TECHNO.txt ...): a line a pattern, PART <tab> pattern <tab>
notes ('-' for a drum); '#' starts a comment. The first time a genre is changed, its file is started from the stock
one (tools/hub/patterns, written by tools/gen_beats.py: the variations that come after the FM-1's). A part's patterns
are numbered in the order of the file, from 0: the FM-1 shows pattern k as the variation after its own (k + 13 of a
main part). Standard library only.
"""
import os

# the genres in the FM-1's order (sagga_beats.h SQ_GENRE_*), as the files are named (0.29: 22)
GENRES = ['TECHNO', 'HARDTECHNO', 'DUBTECHNO', 'HOUSE', 'UKGARAGE', 'UKFUNKY', 'DUBSTEP', 'JUNGLE',
          'REGGAETON', 'BATIDA', 'GQOM', 'EXPERIMENTAL', 'ELECTRO', 'DNB', 'BALANI', 'FOOTWORK', 'TRANCE',
          'UKDRILL', 'HARDCORE', 'PHONK', 'BAILEFUNK', 'MERENGUE']
# 0.29: the genres that left the library and the one each went into; RETIRED_STOCK: their files as 0.28 gave them (a
# line of a file of yours that is not there is one you kept yourself)
RETIRED = {'AMAPIANO': 'REGGAETON', 'BASSLINE': 'UKGARAGE', 'GRIME': 'DUBSTEP', 'AFROHOUSE': 'GQOM'}
# the parts in SQ_FUNC_* order (PROG and KIT have no patterns of their own)
PARTS = ['KICK', 'SNARE', 'HAT', 'PERC', 'BASS', 'CHORD', 'ARP', 'PROG', 'KIT',
         'CLAP', 'OHAT', 'RIDE', 'SHAKER', 'CONGA', 'TOM', 'RIM', 'CRASH', 'COWBELL',
         'RUMBLE', 'SUB', 'LOGDRUM', 'STAB', 'PAD', 'PIANO', 'LEAD', 'VOX']
DRUM = {'KICK', 'SNARE', 'HAT', 'PERC', 'CLAP', 'OHAT', 'RIDE', 'SHAKER', 'CONGA', 'TOM', 'RIM', 'CRASH', 'COWBELL'}
CHORDS = {'CHORD', 'STAB', 'PAD', 'PIANO'}
HITS = set('xXog234')
# a part's family (tools/beat_parts.py FAMILY): a part the genre has not is taken as its family's part
FAMILY = dict(KICK='KICK', SNARE='SNARE', HAT='HAT', PERC='PERC', BASS='BASS', CHORD='CHORD', ARP='ARP',
              CLAP='SNARE', OHAT='HAT', RIDE='HAT', SHAKER='HAT', CONGA='PERC', TOM='PERC', RIM='SNARE', CRASH='PERC',
              COWBELL='PERC', RUMBLE='BASS', SUB='BASS', LOGDRUM='BASS', STAB='CHORD', PAD='CHORD', PIANO='CHORD',
              LEAD='ARP', VOX='ARP')
MAX_STEPS = 64
STOCK = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'patterns')
RETIRED_MARK = '# 0.29: the patterns you kept in %s (a genre that left the library) are here, after these'


def kind(part):
    return 'drum' if part in DRUM else 'chord' if part in CHORDS else 'mono'


def valid(part, text, notes):
    """None if (text, notes) is a pattern of the part, else why not"""
    if part not in PARTS or part in ('PROG', 'KIT'):
        return 'no such part'
    if not text or len(text) > MAX_STEPS or any(c not in '.-' and c not in HITS for c in text):
        return 'the pattern: 1 to 64 of . x X o g 2 3 4 -'
    if text[0] == '-' or all(c in '.-' for c in text):
        return 'nothing plays'
    if kind(part) == 'drum':
        return None if notes in (None, '', '-') else 'a drum has no notes'
    if not notes or len(notes) != len(text):
        return 'the notes: one a step'
    ok = '0123456789abcdef' if kind(part) == 'mono' else 'mMnN7s5'
    for c, k in zip(text, notes):
        if c in HITS and k not in ok:
            return 'a note that is not one: %r' % k
        if c not in HITS and k not in '.-':
            return 'a note where nothing plays'
    return None


class Patterns:
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
        """[(line number, part, text, notes)] of a genre, in the file's order"""
        out = []
        for i, ln in enumerate(self.lines(genre)):
            s = ln.strip()
            if not s or s.startswith('#'):
                continue
            f = s.split('\t') if '\t' in s else s.split()
            if len(f) < 2:
                continue
            part, text = f[0].upper(), f[1]
            notes = f[2] if len(f) > 2 and f[2] != '-' else None
            if valid(part, text, notes) is None:
                out.append((i, part, text, notes))
        return out

    def of(self, genre, part):
        return [(t, n) for _, p, t, n in self.entries(genre) if p == part]

    def summary(self):
        """{genre: {part: count}}"""
        out = {}
        for g in GENRES:
            c = {}
            for _, p, _, _ in self.entries(g):
                c[p] = c.get(p, 0) + 1
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

    def add(self, genre, part, text, notes):
        """keeps a new pattern at the end of the genre's file; returns its number among the part's"""
        if genre not in GENRES:
            raise ValueError('no such genre')
        why = valid(part, text, notes)
        if why:
            raise ValueError(why)
        lines = self.lines(genre) or ['# SAGGA SEQ 0.11 pattern library, %s: PART, the pattern, its notes (- for a drum).' % genre]
        lines.append('%s\t%s\t%s' % (part, text, notes if kind(part) != 'drum' else '-'))
        self._write(genre, lines)
        return len(self.of(genre, part)) - 1

    def retire(self):
        """0.29: the patterns you kept yourself in a genre that left the library (SEQ + SAVE, or the page) go to the end of
        the genre it went into, each under its part (one that genre has not: the part of the same family it has; none:
        it stays in the old file, which is left as it was). Once: the genre's file says so. -> how many moved"""
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
                stock = {(p, t, n) for _, p, t, n in Patterns(os.path.join(self.stock, 'retired'), stock=None).entries(old)}
            yours = [(p, t, n) for _, p, t, n in Patterns(self.folder, stock=None).entries(old) if (p, t, n) not in stock]
            if not yours:
                continue
            have = {p for _, p, _, _ in self.entries(new)}
            lines = lines or ['# SAGGA SEQ 0.11 pattern library, %s: PART, the pattern, its notes (- for a drum).' % new]
            lines.append(mark)
            for part, text, notes in yours:
                to = part if part in have else next((q for q in PARTS if q in have and FAMILY.get(q) == FAMILY.get(part)), None)
                if to is None or valid(to, text, notes):
                    continue
                lines.append('%s\t%s\t%s' % (to, text, notes if kind(to) != 'drum' else '-'))
                moved += 1
            self._write(new, lines)
        return moved

    def delete(self, genre, part, k):
        """takes pattern k of a part away; True if there was one"""
        ents = [e for e in self.entries(genre) if e[1] == part]
        if genre not in GENRES or not 0 <= k < len(ents):
            return False
        drop = ents[k][0]
        lines = [ln for i, ln in enumerate(self.lines(genre)) if i != drop]
        self._write(genre, lines)
        return True
