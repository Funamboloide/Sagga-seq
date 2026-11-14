# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA SEQ 0.11: the bands of the genres and the variations of their parts. Used by tools/gen_beats.py.

Every genre has a BAND: the parts BAND (SEQ + SEL + black 7) puts on the tracks, 8 to 11 of them, in that order, and
EXTRAS: parts of the 0.10 library that are not in the band but stay to be browsed and loaded (TECHNO keeps its ARP).
A part marked * is a main part: 12 variations in the FM-1's flash; the others get 6. The Pi keeps more (VAR 13 on).

The variations come from SEEDS: the 0.10 library's own patterns (written by hand, by genre) where the part was there
(a TECHNO CLAP is 0.10's TECHNO SNARE, a STAB its CHORD), and for the new parts the patterns below, written for each
genre where the genre has its own (an amapiano log drum, a gqom tom, a phonk cowbell ...) and else the part's common
ones. From the seeds, small musical changes (a ghost on a 16th, a hit moved a step, an accent, a roll into the bar, a
held note, another note of the chord ...) make the candidates. The variations are then ORDERED by likeness: the first
is the genre's most typical (the first seed), each next the closest to the one before, the density rising, the odd
ones last - so that COOK, which walks a track towards the next variation, takes small steps.

Pattern text: one character per 16th: '.' rest, 'x' hit, 'X' accent, 'o' soft, 'g' ghost, '2'-'4' a hit repeated,
'-' the note before goes on through this step (a held note). Notes (melodic parts): one character per step: a
semitone above the root (hex 0-f) for single notes, the kind of chord for chord parts (m M n N 7 s 5), '.' where
nothing starts.

Sources for the new parts' common patterns: the genres' usual programming (four-on-the-floor kicks, off-beat open
hats, an 8th-note ride with every second hit quieter (Attack Magazine, "Dark techno rumble"), a 16th shaker with
alternating velocity and missing hits, an amapiano log drum phrase of two bars - a root near the start, a gap, one or
two syncopated notes later, the second bar's last note earlier (beatstorapon.com, "How to make an amapiano beat"),
afro house congas in call and answer, swing 80-85 (Attack Magazine, "Deep afro house")).
"""
import random
import zlib

# the parts, in SQ_FUNC_* order: 0..6 as 0.10, 7 PROG and 8 KIT (no patterns of their own), then 0.11's
PARTS = ['KICK', 'SNARE', 'HAT', 'PERC', 'BASS', 'CHORD', 'ARP', 'PROG', 'KIT',
         'CLAP', 'OHAT', 'RIDE', 'SHAKER', 'CONGA', 'TOM', 'RIM', 'CRASH', 'COWBELL',
         'RUMBLE', 'SUB', 'LOGDRUM', 'STAB', 'PAD', 'PIANO', 'LEAD', 'VOX']
SHOWN = dict(OHAT='OPEN HAT', LOGDRUM='LOG DRUM')
DRUM = {'KICK', 'SNARE', 'HAT', 'PERC', 'CLAP', 'OHAT', 'RIDE', 'SHAKER', 'CONGA', 'TOM', 'RIM', 'CRASH', 'COWBELL'}
MONO = {'BASS', 'ARP', 'RUMBLE', 'SUB', 'LOGDRUM', 'LEAD', 'VOX'}
CHORDS = {'CHORD', 'STAB', 'PAD', 'PIANO'}
FAMILY = dict(KICK='KICK', SNARE='SNARE', HAT='HAT', PERC='PERC', BASS='BASS', CHORD='CHORD', ARP='ARP',
              CLAP='SNARE', OHAT='HAT', RIDE='HAT', SHAKER='HAT', CONGA='PERC', TOM='PERC', RIM='SNARE', CRASH='PERC',
              COWBELL='PERC', RUMBLE='BASS', SUB='BASS', LOGDRUM='BASS', STAB='CHORD', PAD='CHORD', PIANO='CHORD',
              LEAD='ARP', VOX='ARP')
# the note a drum part plays (General MIDI) unless the genre's KIT says (KICK SNARE HAT PERC), the register of the others
NOTE = dict(CLAP=39, OHAT=46, RIDE=51, SHAKER=70, CONGA=63, TOM=45, RIM=37, CRASH=49, COWBELL=56,
            BASS=36, RUMBLE=36, SUB=36, LOGDRUM=43, CHORD=55, STAB=60, PAD=60, PIANO=60, ARP=67, LEAD=72, VOX=72)

# BAND: the parts in order ('*': a main part, 12 variations); MAP: where a part's seeds come from in the 0.10 library;
# EXTRA: 0.10 parts kept to browse
BANDS = {
    'TECHNO':       ('KICK* CLAP* HAT* OHAT RIDE PERC* RUMBLE* BASS* STAB PAD', dict(CLAP='SNARE', STAB='CHORD'), 'ARP'),
    'HARDTECHNO':   ('KICK* RUMBLE* CLAP* HAT* OHAT RIDE PERC* STAB LEAD', dict(RUMBLE='BASS', CLAP='SNARE', STAB='CHORD', LEAD='ARP'), ''),
    'DUBTECHNO':    ('KICK* RIM* HAT* SHAKER PERC BASS* CHORD* PAD', dict(RIM='SNARE'), 'ARP'),
    'HOUSE':        ('KICK* CLAP* HAT* OHAT* SHAKER PERC BASS* PIANO* PAD VOX', dict(CLAP='SNARE', PIANO='CHORD'), 'ARP'),
    'UKGARAGE':     ('KICK* SNARE* HAT* OHAT SHAKER PERC* BASS* CHORD* VOX', {}, 'ARP'),
    'UKFUNKY':      ('KICK* SNARE* HAT* RIM CONGA* PERC* TOM BASS* CHORD* LEAD', dict(LEAD='ARP'), ''),
    'GRIME':        ('KICK* SNARE* HAT* PERC CRASH BASS* SUB STAB* LEAD*', dict(STAB='CHORD', LEAD='ARP'), ''),
    'DUBSTEP':      ('KICK* SNARE* HAT* PERC* CRASH SUB* BASS* PAD LEAD', dict(PAD='CHORD', LEAD='ARP'), ''),
    'JUNGLE':       ('KICK* SNARE* HAT* RIDE PERC* CRASH SUB* BASS* PAD* VOX', dict(PAD='CHORD'), 'ARP'),
    'BASSLINE':     ('KICK* SNARE* HAT* OHAT PERC BASS* SUB STAB* VOX', dict(STAB='CHORD'), 'ARP'),
    'REGGAETON':    ('KICK* SNARE* HAT* RIM CONGA* PERC BASS* CHORD* LEAD', dict(LEAD='ARP'), ''),
    'BATIDA':       ('KICK* SNARE* HAT* SHAKER CONGA* PERC* TOM BASS* CHORD* LEAD', dict(LEAD='ARP'), ''),
    'GQOM':         ('KICK* SNARE* HAT* PERC* TOM* BASS* PAD VOX', dict(PAD='CHORD'), 'ARP'),
    'EXPERIMENTAL': ('KICK* SNARE* HAT* PERC* CRASH TOM BASS* PAD* ARP*', dict(PAD='CHORD'), ''),
    'ELECTRO':      ('KICK* SNARE* CLAP HAT* OHAT COWBELL BASS* STAB ARP*', dict(STAB='CHORD'), 'PERC'),
    'DNB':          ('KICK* SNARE* HAT* RIDE SHAKER PERC* SUB* BASS* PAD* LEAD', dict(PAD='CHORD', LEAD='ARP'), ''),
    'AFROHOUSE':    ('KICK* CLAP* HAT* SHAKER* CONGA* PERC* RIM TOM BASS* CHORD* VOX', dict(CLAP='SNARE'), 'ARP'),
    'AMAPIANO':     ('KICK* CLAP* SHAKER* HAT* RIM PERC LOGDRUM* BASS PIANO* PAD VOX', dict(CLAP='SNARE', LOGDRUM='BASS', PIANO='CHORD'), 'ARP'),
    'FOOTWORK':     ('KICK* SNARE* CLAP HAT* PERC* TOM SUB* CHORD* VOX*', dict(SUB='BASS', VOX='ARP'), ''),
    'TRANCE':       ('KICK* CLAP* HAT* OHAT* RIDE CRASH PERC BASS* PAD* ARP* LEAD*', dict(CLAP='SNARE', PAD='CHORD'), ''),
    'UKDRILL':      ('KICK* SNARE* HAT* PERC RIM SUB* PAD* LEAD VOX', dict(SUB='BASS', PAD='CHORD', LEAD='ARP'), ''),
    'HARDCORE':     ('KICK* CLAP* HAT* OHAT CRASH PERC STAB* LEAD* PAD', dict(CLAP='SNARE', STAB='CHORD', LEAD='ARP'), 'BASS'),
    'PHONK':        ('KICK* SNARE* HAT* COWBELL PERC SUB* LEAD* PAD VOX', dict(SUB='BASS', LEAD='ARP', PAD='CHORD'), ''),
    'BAILEFUNK':    ('KICK* SNARE* HAT* PERC* CONGA TOM SUB* VOX* STAB', dict(SUB='BASS', VOX='ARP', STAB='CHORD'), ''),
    # 0.16: the HAT is the guira, the PERC the tambora, the SNARE its rim; the piano's montuno, the sax / accordion riff
    'MERENGUE':     ('KICK* SNARE* HAT* PERC* CONGA* BASS* PIANO* LEAD* VOX', dict(PIANO='CHORD', LEAD='ARP'), ''),
}

# the new parts' common patterns (a drum: text; a melodic part: (text, notes))
COMMON = {
    'CLAP':    ["....X.......X...", "....X.......X..x", "....X..x....X...", "....X.......X.X."],
    'OHAT':    ["..x...x...x...x.", "..X...x...X...x.", "..x...x...x...xx", "......x.......x."],
    'RIDE':    ["x.o.x.o.x.o.x.o.", "..x...x...x...x.", "x.x.x.x.x.x.x.x.", "x.oxx.oxx.oxx.ox"],
    'SHAKER':  ["xoxoxoxoxoxoxoxo", "..o...o...o...o.", "xoxo.oxoxoxo.oxo", "oxoxoxoxoxoxoxox"],
    'CONGA':   ["x..x..x.o.x.x..o", "..o.x..x..o.x.x.", "x.ox..x.x.ox..x.", "...x..x....x.xx."],
    'TOM':     ["..........x..x..", "x.....x.....x...", "............x.xx", "......x.......x.x.....x.......xx"],
    'RIM':     ["...x..x.......x.", "..x..x....x..x..", "......x.....x...", "...x...x...x..x."],
    'CRASH':   ["x...............", "x...............................", "x...............................................................", "x.......x......."],
    'COWBELL': ["..x...x...x...x.", "x..x..x...x..x..", "..x.x...x...x.x.", "x.x..x.x..x..x.x"],
    'RUMBLE':  [(".xxx.xxx.xxx.xxx", ".000.000.000.000"), ("..xx..xx..xx..xx", "..00..00..00..00"),
                (".x.x.x.x.x.x.x.x", ".0.0.0.0.0.0.0.0"), (".oxo.oxo.oxo.oxo", ".000.000.000.000")],
    'SUB':     [("x-------x-------", "0.......0......."), ("x-----x---x-----", "0.....0...3....."),
                ("x---------------", "0..............."), ("x--.....x-..x---", "0.......0..5....")],
    'LOGDRUM': [("x.....x...x.....x.....x..x......", "0.....0...7.....0.....5..3......"), ("x..x......x..x..", "0..0......7..5.."),
                ("..x...x.x.....x.", "..0...0.c.....7."), ("x-..x.....x.x...", "0...0.....7.5...")],
    'BASS':    [("x--.x--.x--.x--.", "0...0...0...0..."), ("x.....x.x.....x.", "0.....0.7.....5."), ("x-..x...x-..x.x.", "0...0...3...5.7.")],
    'STAB':    [("...x.......x....", "...m.......m...."), ("x.....x.....x...", "m.....m.....m..."), ("..x..x....x.....", "..n..n....n.....")],
    'PAD':     [("x---------------", "n..............."), ("x-------x-------", "n.......n......."),
                ("x---------------x---------------", "n...............N..............."), ("x-----x---------", "n.....s.........")],
    'PIANO':   [("x..x..x...x..x..", "n..n..n...n..n.."), ("..x..x.x..x..x.x", "..n..n.n..n..n.n"), ("x-.x-.x.x-.x-.x.", "n..n..n.n..n..n.")],
    'ARP':     [("x.x.x.x.x.x.x.x.", "0.3.7.c.7.3.0.5.")],
    'LEAD':    [("x-.x-.x.x---....", "0..3..7.5......."), ("x.xx.x.xx.x.x.x.", "0.37.5.c7.5.3.0."), ("x---x-x-x-------", "7...5.3.0.......")],
    'VOX':     [("...x......x.....", "...0......7....."), ("..x.x.......x...", "..c.a.......7..."), ("x.......x.x.....", "7.......5.3.....")],
}
# a genre's own patterns for a new part (before the common ones)
OWN = {
    ('TECHNO', 'PAD'): [("x---------------x---------------", "n...............n...............")],
    ('HOUSE', 'OHAT'): ["..x...x...x...x.", "..x...x...x..xx."],
    ('HOUSE', 'SHAKER'): ["xoxoxoxoxoxoxoxo", "oxoxoxoxoxoxoxox"],
    ('HOUSE', 'VOX'): [("......x.......x.", "......0.......7."), ("..x.......x.x...", "..7.......5.3...")],
    ('DUBTECHNO', 'PAD'): [("x---------------x---------------", "n...............n..............."), ("x-------........", "n...............")],
    ('UKFUNKY', 'CONGA'): ["x..x..x...x.x..x", "..x.x..x..x...x.", "x.xx..x.x.xx..x."],
    ('UKFUNKY', 'TOM'): ["..........x..x..", "......x.......xx"],
    ('GRIME', 'SUB'): [("x---------x-----", "0.........0....."), ("x-------x-x-----", "0.......0.1.....")],
    ('DUBSTEP', 'SUB'): [("x-------x-------", "0.......0......."), ("x---------------", "0..............."), ("x-------x---x---", "0.......0...3...")],
    ('JUNGLE', 'SUB'): [("x-------..x-----", "0.........0....."), ("x-----x---------", "0.....5.........")],
    ('BASSLINE', 'SUB'): [("x---x---x---x---", "0...0...0...0...")],
    ('REGGAETON', 'RIM'): ["...x..x....x..x.", "...x..x.x..x..x."],
    ('REGGAETON', 'CONGA'): ["x..x..x.x..x..x.", "..x..x.x..x..x.x"],
    ('BATIDA', 'CONGA'): ["x..x..x...x..x..", "x.xx..x.x.xx..x.", "..x..x....x..x.."],
    ('BATIDA', 'TOM'): ["......x.......x.", "......x..x....xx"],
    ('GQOM', 'TOM'): ["x..x..x...x..x..", "x..x..x.x..x..x.", "..x..x....x..x..", "x.....x.....x...x...x.....x.x..."],
    ('GQOM', 'VOX'): [("......x.........", "......0........."), ("...x......x.....", "...7......5.....")],
    ('ELECTRO', 'COWBELL'): ["..x...x...x.x.x.", "x..x..x...x..x..", "..x.x..x..x...x."],
    ('ELECTRO', 'CLAP'): ["....x.......x...", "....x..x....x..."],
    ('DNB', 'SUB'): [("x---------x-----", "0.........0....."), ("x-------..x---x-", "0.........7...5.")],
    ('DNB', 'RIDE'): ["..x...x...x...x.", "x.x.x.x.x.x.x.x."],
    ('AFROHOUSE', 'SHAKER'): ["xoxoxoxoxoxoxoxo", "xo.oxoxoxo.oxoxo", "..o...o...o...o."],
    ('AFROHOUSE', 'CONGA'): ["x..x..x.o.x.x..o", "..o.x..x..o.x.x.", "x.ox..x.x.ox..x.", "x..x..x...x.x..xx..x..x.o.x.x.oo"],
    ('AFROHOUSE', 'RIM'): ["...x..x.......x.", "...x..x....x...x"],
    ('AFROHOUSE', 'TOM'): ["............x.x.", "......x.......x.", "..........x..x.."],
    ('AFROHOUSE', 'VOX'): [("......x.........", "......0........."), ("...x......x.....", "...7......5.....")],
    ('AMAPIANO', 'SHAKER'): ["xoxoxoxoxoxoxoxo", "xoxo.oxoxoxo.oxo", "xoxoxoxoxoxoxoxoxoxo.oxoxoxoxo.o"],
    ('AMAPIANO', 'RIM'): ["...x......x.....", "...x..x...x...x.", "......x..x....x."],
    ('AMAPIANO', 'LOGDRUM'): [("x.....x...x.....x.....x..x......", "0.....0...7.....0.....5..3......"),
                              ("x..x......x..x..", "0..0......7..5.."), ("x-....x...x-.x..", "0.....0...7..5..")],
    ('AMAPIANO', 'BASS'): [("x-------x-------", "0.......0......."), ("x-----..x-----..", "0.......5.......")],
    ('AMAPIANO', 'PAD'): [("x---------------x---------------", "n...............N...............")],
    ('FOOTWORK', 'TOM'): ["..x..x..x..x..x.", "x..x..x..x..x..x"],
    ('FOOTWORK', 'CLAP'): ["....x.......x...", "...x..x....x..x."],
    ('TRANCE', 'OHAT'): ["..x...x...x...x.", "..X...X...X...X.", "..x...x...x...xx"],
    ('TRANCE', 'LEAD'): [("x.xx.xx.x.xx.x.x", "0.37.a7.c.a7.5.3"), ("x--x--x-x--x--x-", "c..a..7.5..7..a."), ("x-------x---x---", "7.......5...3...")],
    ('TRANCE', 'RIDE'): ["..x...x...x...x.", "x.x.x.x.x.x.x.x."],
    ('UKDRILL', 'RIM'): ["...x......x.....", "......x.......x."],
    ('UKDRILL', 'VOX'): [("..........x.....", "..........0....."), ("...x......x.x...", "...7......5.3...")],
    ('HARDCORE', 'PAD'): [("x---------------", "m...............")],
    ('PHONK', 'COWBELL'): ["x..x..x.x..x..x.", "x..x..x...x.x...", "..x..x....x..x.."],
    ('PHONK', 'VOX'): [("x...........x...", "0...........7..."), ("....x.......x...", "....0.......0...")],
    ('BAILEFUNK', 'CONGA'): ["x..x..x...x..x..", "..x..x.x..x..x.x"],
    ('BAILEFUNK', 'TOM'): ["x..x..x...x..x..", "x..x..x.x..x..x.", "......x..x....x."],
    ('MERENGUE', 'CONGA'): ["x.ox..x.x.ox..x.", "..x..xx...x..xx.", "x..x.xx.x..x.xx."],
    ('MERENGUE', 'VOX'): [("x...x.......x...", "0...4.......7..."), ("....x...x...x...", "....7...4...0...")],
}

KINDS = dict(m=0, M=1, n=2, N=3, s=5)                 # (7 and 5 stay as written)
STRENGTH = {'.': 0.0, '-': 0.0, 'g': 0.3, 'o': 0.5, 'x': 1.0, 'X': 1.25, '2': 1.35, '3': 1.4, '4': 1.45}


def kind(part):
    return 'drum' if part in DRUM else 'mono' if part in MONO else 'chord'


def split(e):
    return (e, None) if isinstance(e, str) else e


def tile(s, n):
    return (s * (n // len(s) + 1))[:n]


def holds(r):
    """1 where a note sounds on (a hit or its '-'), per step"""
    out, on = [], 0
    for c in r:
        on = 1 if c not in '.-' else (on if c == '-' else 0)
        out.append(on)
    return out


def dist(a, b):
    """how unalike two patterns are, in hits per bar (a rest against an accent counts 1.25)"""
    ra, na = split(a)
    rb, nb = split(b)
    n = 64
    ra, rb = tile(ra, n), tile(rb, n)
    na = tile(na, n) if na else None
    nb = tile(nb, n) if nb else None
    ha, hb = holds(ra), holds(rb)
    d = 0.0
    for i in range(n):
        d += abs(STRENGTH[ra[i]] - STRENGTH[rb[i]])
        if na and nb and ra[i] not in '.-' and rb[i] not in '.-' and na[i] != nb[i]:
            d += 0.4
        d += 0.25 * abs(ha[i] - hb[i])
    return d * 16.0 / n


def density(e):
    r, _ = split(e)
    return sum(1 for c in r if c not in '.-') * 16.0 / len(r)


def ok(part, e):
    r, nt = split(e)
    if len(r) not in (16, 32, 64) or (nt is not None and len(nt) != len(r)):
        return False
    if all(c in '.-' for c in r) or r[0] == '-':
        return False
    if part == 'KICK' and r[0] not in 'Xx':
        return False
    dens = density(e)
    caps = dict(KICK=9, CRASH=2, PAD=4, SUB=6, TOM=8, COWBELL=10, CLAP=6, SNARE=8, RIM=7, STAB=6, VOX=6)
    if dens > caps.get(part, 16):
        return False
    if part not in ('CRASH', 'PAD', 'SUB', 'VOX', 'TOM') and dens < 1.0:
        return False
    if nt is not None:
        for c, k in zip(r, nt):
            if c in '.-' and k not in '.-':
                return False
            if c not in '.-' and k in '.-':
                return False
    return True


# ---- the small changes
def _weak_rests(r, part):
    """rests a hit may go to, weighted: 16ths most, "and"s, beats least (none for a kick's one)"""
    out = []
    for i, c in enumerate(r):
        if c != '.':
            continue
        w = 3 if i % 2 else (2 if i % 4 == 2 else 0.5)
        if part == 'KICK' and i % 16 == 0:
            continue
        out.append((i, w))
    return out


def _pick(rng, items):
    tot = sum(w for _, w in items)
    if tot <= 0:
        return None
    x = rng.random() * tot
    for i, w in items:
        x -= w
        if x <= 0:
            return i
    return items[-1][0]


def _note_for(part, nt, rng, near):
    if part in CHORDS:
        return rng.choice('mmnnNs') if near is None else near
    tones = '0037a75c'
    return rng.choice(tones) if near is None else (near if rng.random() < 0.6 else rng.choice(tones))


def mutate(part, e, rng, triplets):
    r, nt = split(e)
    r, nt = list(r), (list(nt) if nt else None)
    hits = [i for i, c in enumerate(r) if c not in '.-']
    op = rng.choice(['add', 'add', 'add', 'remove', 'shift', 'shift', 'shift', 'accent', 'ratchet', 'fill'] +
                    (['note', 'note', 'hold', 'hold', 'unhold', 'octave'] if nt else ['ghost', 'double']))
    if op == 'add':
        i = _pick(rng, _weak_rests(r, part))
        if i is None:
            return None
        r[i] = rng.choice('xo' if part in ('KICK', 'BASS', 'SUB') else 'xog' if part in ('SNARE', 'CLAP', 'RIM') else 'xxo')
        if nt:
            prev = next((nt[j] for j in range(i, -1, -1) if nt[j] not in '.-'), None)
            nt[i] = _note_for(part, nt, rng, prev)
    elif op == 'remove':
        cand = [(i, 3 if i % 2 else 2 if i % 4 == 2 else 0.4) for i in hits if not (part == 'KICK' and i % 16 == 0) and i != 0]
        i = _pick(rng, cand)
        if i is None:
            return None
        r[i] = '.'
        if nt:
            nt[i] = '.'
        j = i + 1
        while j < len(r) and r[j] == '-':
            r[j] = '.'
            j += 1
    elif op == 'shift':
        cand = [i for i in hits if i != 0 and not (part == 'KICK' and i % 4 == 0)]
        if not cand:
            return None
        i = rng.choice(cand)
        j = i + rng.choice((-1, 1))
        if not 0 < j < len(r) or r[j] != '.':
            return None
        r[j], r[i] = r[i], '.'
        if nt:
            nt[j], nt[i] = nt[i], '.'
        k = i + 1                                      # (a held note does not move with it: it ends)
        while k < len(r) and r[k] == '-':
            r[k] = '.'
            k += 1
    elif op == 'accent':
        if not hits:
            return None
        i = rng.choice(hits)
        r[i] = {'x': 'X', 'X': 'x', 'o': 'x', 'g': 'o'}.get(r[i], r[i])
    elif op == 'ratchet':
        bar = rng.randrange(len(r) // 16) * 16
        last = [i for i in hits if bar + 12 <= i < bar + 16]
        if not last or part in ('PAD', 'SUB', 'CRASH'):
            return None
        r[last[-1]] = '3' if triplets else '2'
    elif op == 'fill':
        if part in ('PAD', 'SUB', 'CRASH', 'KICK'):
            return None
        bar = (len(r) // 16 - 1) * 16
        i = bar + rng.choice((13, 14, 15))
        if r[i] != '.':
            return None
        r[i] = 'x'
        if nt:
            prev = next((nt[j] for j in range(i, -1, -1) if nt[j] not in '.-'), None)
            nt[i] = _note_for(part, nt, rng, prev)
    elif op == 'ghost':
        i = _pick(rng, [(i, w) for i, w in _weak_rests(r, part) if i % 2])
        if i is None or part in ('KICK', 'CRASH'):
            return None
        r[i] = 'g'
    elif op == 'double':
        if part not in ('HAT', 'SHAKER', 'RIDE', 'OHAT'):
            return None
        r = [c if c != '.' or i % 2 == 0 else 'o' for i, c in enumerate(r)]
    elif op == 'note':
        if not hits:
            return None
        i = rng.choice(hits)
        nt[i] = _note_for(part, nt, rng, None)
    elif op == 'hold':
        cand = [i for i in hits if i + 1 < len(r) and r[i + 1] == '.']
        if not cand or part in ('ARP', 'STAB', 'VOX'):
            return None
        i = rng.choice(cand)
        j = i + 1
        stop = rng.choice((2, 3, 4, 8))
        while j < len(r) and r[j] == '.' and j - i < stop:
            r[j] = '-'
            j += 1
    elif op == 'unhold':
        cand = [i for i, c in enumerate(r) if c == '-']
        if not cand:
            return None
        i = rng.choice(cand)
        while i < len(r) and r[i] == '-':
            r[i] = '.'
            i += 1
    elif op == 'octave':
        if part in CHORDS or not hits:
            return None
        i = rng.choice(hits)
        nt[i] = {'0': 'c', 'c': '0', '7': '0', '3': 'f', '5': '0'}.get(nt[i], '0')
    out = ''.join(r)
    return (out, ''.join(nt)) if nt else out


def variations(genre, part, seeds, count, extra, triplets):
    """count variations (the first the first seed), ordered by likeness; then `extra` more for the Pi"""
    rng = random.Random(zlib.crc32(('%s/%s' % (genre, part)).encode()))
    seeds = [s for s in seeds if ok(part, s)]
    want = count + extra
    pool, seen = [], set()
    for s in seeds:
        if s not in seen:
            seen.add(s)
            pool.append(s)
    front = list(pool)
    for _ in range(4):                                  # four generations of small changes
        nxt = []
        for e in front:
            for _ in range(10):
                m = mutate(part, e, rng, triplets)
                if m is not None and m not in seen and ok(part, m):
                    seen.add(m)
                    nxt.append(m)
        pool += nxt
        front = nxt
        if len(pool) > 8 * want:
            break
    s0 = pool[0]
    seeds = [e for e in pool if e in set(seeds)]           # (once each, in their order)
    near = {e: min(dist(e, s) for s in seeds) for e in pool}
    ranked = sorted(pool, key=lambda e: (near[e], e))

    def take(into, n, avoid, gap):
        for e in ranked:
            if len(into) >= n:
                return
            if e in into or e in avoid or any(dist(e, c) < gap for c in into + avoid):
                continue
            into.append(e)

    flash = seeds[:count]                                   # the patterns written by hand all go in the FM-1
    for gap in (0.9, 0.45, 0.0):                            # then the nearest that differ by a hit or more
        take(flash, count, [], gap)
    pi = []
    for gap in (0.9, 0.45, 0.0):
        take(pi, extra, flash, gap)

    def bar1(e):
        r, n = split(e)
        return (r[:16], n[:16] if n else None)

    def chain(start, items):
        """each next the closest; one whose first bar is the bar before's comes later (at the library's 16 steps, the
        length a pattern is loaded at unless SAVE 2 K4 says more, the two would sound the same)"""
        order, left = [], list(items)
        prev = start
        while left:
            best = min(left, key=lambda c: (dist(prev, c) + 0.6 * dist(c, s0) + 0.5 * max(0.0, density(prev) - density(c))
                                            + (2.5 if bar1(c) == bar1(prev) else 0.0), c))
            order.append(best)
            left.remove(best)
            prev = best
        return order
    flash = [s0] + chain(s0, [e for e in flash if e != s0])
    return flash, chain(flash[-1], pi)


def parse_band(spec):
    out = []
    for tok in spec.split():
        out.append((tok.rstrip('*'), tok.endswith('*')))
    return out
