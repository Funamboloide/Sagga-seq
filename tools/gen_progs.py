#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA SEQ 0.11: writes the stock progressions the Pi starts with (tools/hub/progressions/<GENRE>.txt, read by
tools/hub/sagga_progs.py): for each genre the moods it lives in, the progressions of each mood, coloured the genre's way
(dub techno's minor sevenths and ninths, house's sevenths, amapiano's major sevenths, trance's added ninths, hard
techno's fifths ...). The moods are given here, not guessed: a progression is written under the mood it is known for.

    python3 tools/gen_progs.py            (writes the files)
    python3 tools/gen_progs.py --check    (exit 1 if a file would change)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'hub'))
import sagga_progs as P  # noqa: E402

# the progressions of each mood, above the key's root (the chords' own colours where the mood is in them)
POOL = {
    'SAD':        ['i iv bVI v', 'i bVI iv v', 'i v bVI iv', 'i iv v i', 'i bVI bIII v', 'i iv bVI bVII', 'i bVI iv i',
                   'iv i v i'],
    'MELANCHOLY': ['i IV i IV', 'i bIII bVII IV', 'vi IV I V', 'i iv bVII bIII', 'ii iii vi vi', 'i bVII IV i',
                   'i bIII IV iv', 'vi iii IV I'],
    'SATISFYING': ['ii7 V7 Imaj7', 'IV V I', 'I IV V I', 'ii V I vi', 'IV V iii vi', 'iv V7 i', 'bVI bVII i',
                   'I vi ii V'],
    'ENERGETIC':  ['i:8 bVII:8 bVI:8 bVII:8', 'I:8 V:8 vi:8 IV:8', 'i:4 i:4 bVII:4 bVI:4', 'i:8 bVII:8',
                   'I:8 bVII:8 IV:16', 'i:8 iv:8 bVI:8 bVII:8', 'vi:8 IV:8 I:8 V:8'],
    'EUPHORIC':   ['I V vi IV', 'vi IV I V', 'IV I V vi', 'I iii IV V', 'I V IV V', 'IV V vi I', 'I IV vi V',
                   'bVI bVII I I'],
    'EPIC':       ['i bVI bVII i', 'i bVI bIII bVII', 'bVI bVII i i', 'i bVII bVI bVII', 'i bVI bVII V', 'iv bVI bVII i',
                   'i bIII bVII bVI', 'bVI bIII bVII i'],
    'DREAMY':     ['Imaj7 IVmaj7', 'Imaj9 vi9', 'IVmaj7 iii7 ii7 Imaj7', 'i9 bVImaj7', 'Imaj7 bVIImaj7', 'ii9 Imaj9',
                   'bIIImaj7 bVImaj7 i9', 'IVmaj9 Imaj9'],
    'DARK':       ['i', 'i bII', 'i bII i bVII', 'i5 bII5', 'i bvi', 'i iv', 'i bII bVII i', 'i7 bII'],
    'TENSE':      ['i #ivo', 'i bV', 'i iio', 'i bII #ivo bII', 'io7', 'i+ i', 'i viio7', 'i bII7'],
    'SUSPENDED':  ['Isus2 IVsus2', 'Isus4 I', 'Isus2 bVIsus2', 'I9sus4 bVII9sus4', 'Isus2 Vsus4', 'I7sus4 bVII7sus4',
                   'Isus4 IVsus2', 'Isus2'],
}

# the genres: the moods they live in, the colour of their triads
GENRES = {
    'TECHNO':       (['DARK', 'TENSE', 'SUSPENDED', 'SAD', 'EPIC'], 'stab'),
    'HARDTECHNO':   (['DARK', 'TENSE', 'EPIC', 'ENERGETIC'], 'power'),
    'DUBTECHNO':    (['DREAMY', 'SUSPENDED', 'MELANCHOLY', 'DARK'], 'dub'),
    'HOUSE':        (['SATISFYING', 'EUPHORIC', 'DREAMY', 'MELANCHOLY'], 'house'),
    'UKGARAGE':     (['MELANCHOLY', 'DREAMY', 'SATISFYING', 'SAD', 'ENERGETIC'], 'garage'),   # (0.29: + the bassline's)
    'UKFUNKY':      (['SATISFYING', 'MELANCHOLY', 'ENERGETIC', 'DREAMY'], 'house'),
    'DUBSTEP':      (['DARK', 'TENSE', 'SAD', 'EPIC'], 'plain'),
    'JUNGLE':       (['MELANCHOLY', 'DREAMY', 'SAD', 'DARK'], 'dub'),
    'REGGAETON':    (['SAD', 'EUPHORIC', 'MELANCHOLY', 'SATISFYING', 'DREAMY'], 'plain'),   # (0.29: + the amapiano's)
    'BATIDA':       (['ENERGETIC', 'DARK', 'SAD'], 'plain'),
    'GQOM':         (['DARK', 'TENSE', 'SUSPENDED', 'MELANCHOLY'], 'plain'),   # (0.29: + the afro house's)
    'EXPERIMENTAL': (['TENSE', 'DARK', 'SUSPENDED', 'DREAMY'], 'plain'),
    'ELECTRO':      (['DARK', 'TENSE', 'SAD', 'ENERGETIC'], 'plain'),
    'DNB':          (['MELANCHOLY', 'DREAMY', 'SAD', 'EPIC'], 'dub'),
    'BALANI':       (['EUPHORIC', 'SATISFYING', 'ENERGETIC'], 'plain'),        # 0.29: the balafon's few, bright chords
    'FOOTWORK':     (['MELANCHOLY', 'DREAMY', 'ENERGETIC', 'TENSE'], 'jazz'),
    'TRANCE':       (['EPIC', 'EUPHORIC', 'SAD', 'SUSPENDED'], 'trance'),
    'UKDRILL':      (['DARK', 'SAD', 'TENSE'], 'plain'),
    'HARDCORE':     (['EUPHORIC', 'EPIC', 'ENERGETIC'], 'plain'),
    'PHONK':        (['DARK', 'TENSE', 'SAD'], 'plain'),
    'BAILEFUNK':    (['ENERGETIC', 'DARK', 'SATISFYING'], 'plain'),
    'MERENGUE':     (['EUPHORIC', 'SATISFYING', 'ENERGETIC', 'MELANCHOLY'], 'plain'),
}

MAJ, MIN = 4, 5                                   # SQ_CH_* the colours are made of
POWER, MAJ7, DOM7, MIN7, ADD9, MADD9, DOM9, MIN9, MAJ9, SUS9, MSHELL = 2, 14, 12, 13, 19, 20, 21, 22, 23, 24, 30


def seventh(semi, small, mt):
    """the seventh the key gives a chord (mt: a minor key - aeolian, dorian's IV, the harmonic V)"""
    if small:
        return MIN7
    if mt:
        return MAJ7 if semi in (1, 3, 8) else DOM7       # bII bIII bVI: major sevenths; IV V bVII: dominant
    return MAJ7 if semi in (0, 5, 8) else DOM7           # I IV bVI; V bVII II III: dominant


def ninth(semi, small, mt):
    """a ninth where the key has it, else the seventh"""
    if small:
        return MIN9 if semi in ((0, 5) if mt else (0, 2, 5, 9)) else MIN7
    if mt:
        return MAJ9 if semi in (3, 8) else DOM9 if semi in (5, 10) else seventh(semi, small, mt)
    return MAJ9 if semi in (0, 5) else DOM9 if semi in (7, 10) else seventh(semi, small, mt)


def add9(semi, small, mt):
    if small:
        return MADD9 if semi in ((0, 5) if mt else (2, 9)) else None
    return ADD9 if (semi in (3, 8, 10) if mt else semi in (0, 5, 7)) else None


COLOURS = {                                       # a genre's triads: (place, root, minor?, minor key?) -> a shape or None
    'stab':   lambda i, semi, small, mt: MSHELL if small and i % 2 == 0 else None,   # the minor stab, every other
    'power':  lambda i, semi, small, mt: POWER,                                        # fifths
    'dub':    lambda i, semi, small, mt: seventh(semi, small, mt) if i % 2 == 0 else ninth(semi, small, mt),
    'house':  lambda i, semi, small, mt: ninth(semi, small, mt) if small and semi == 2 else seventh(semi, small, mt),
    'garage': lambda i, semi, small, mt: ninth(semi, small, mt) if small else SUS9 if semi == 7 else seventh(semi, small, mt),
    'jazz':   lambda i, semi, small, mt: ninth(semi, small, mt) if i % 2 == 0 else seventh(semi, small, mt),
    'trance': lambda i, semi, small, mt: add9(semi, small, mt) if (i % 2 == 0) == small else None,
    'plain':  lambda i, semi, small, mt: None,
}


def colour(rows, how):
    f = COLOURS[how]
    kinds = [P.KIND.get(sh - P.SHAPE_CH, 0) for _, sh, _, _ in rows]
    tonic = [k for (semi, _, _, _), k in zip(rows, kinds) if semi == 0 and k in (0, 1)]
    mt = tonic[0] == 1 if tonic else kinds.count(1) * 2 >= len(kinds)
    out = []
    for i, (semi, shape, dur, push) in enumerate(rows):
        k = shape - P.SHAPE_CH
        if k in (MAJ, MIN):
            new = f(i, semi, k == MIN, mt)
            if new:
                shape = P.SHAPE_CH + new
        out.append((semi, shape, dur, push))
    return out


def lines_of(genre):
    moods, how = GENRES[genre]
    out = ['# SAGGA SEQ 0.11 progressions, %s (tools/gen_progs.py): MOOD, the chords above the key\'s root, a name.' % genre,
           '# I bII II bIII III IV #IV V bVI VI bVII VII, small for minor; then the shape (7 maj7 9 sus2 o ...);',
           '# :N its own length in 16ths, ^N 16ths early. Add your own; SEQ + SAVE on SEQ 4 / SEQ 8 adds the FM-1\'s.']
    seen = set()
    for mood in moods:
        for text in POOL[mood]:
            rows = colour(P.parse(text), how)
            key = (mood, tuple(rows))
            if key in seen:
                continue
            seen.add(key)
            out.append('%s\t%s' % (mood, P.name(rows)))
    return out


def main(argv):
    check = '--check' in argv
    folder = os.path.join(HERE, 'hub', 'progressions')
    os.makedirs(folder, exist_ok=True)
    changed = []
    for g in P.GENRES:
        data = '\n'.join(lines_of(g)) + '\n'
        path = os.path.join(folder, '%s.txt' % g)
        old = open(path, encoding='utf-8').read() if os.path.isfile(path) else None
        if old != data:
            changed.append(g)
            if not check:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(data)
    if check:
        if changed:
            print('gen_progs: would change %s' % ', '.join(changed))
            return 1
        return 0
    total = sum(len(lines_of(g)) - 3 for g in P.GENRES)
    print('gen_progs: %d progressions in %d genres%s' % (total, len(P.GENRES), (' (%s changed)' % len(changed)) if changed else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
