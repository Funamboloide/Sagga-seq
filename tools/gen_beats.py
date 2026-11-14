#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The BEAT library: authoring + validation; writes firmware/src/sagga_beats_data.h and, next to it, VIAGGIO's set
genres (firmware/src/sagga_setgenre_data.h).

    python3 tools/gen_beats.py firmware/src/sagga_beats_data.h [firmware/src/sagga_setgenre_data.h]

One character per 16th: '.' rest, 'x' hit, 'X' accent, 'o' soft, 'g' ghost, '2'-'4' a hit repeated (ratchet).
BASS / ARP: a second string, the semitone above the root of each hit (hex 0-f). CHORD: the kind of chord of each hit
(m minor, M major, n minor 7th, N major 7th, 7 dominant 7th, s sus4, 5 power chord). 16, 32 or 64 steps (one, two or
four bars; a four-bar pattern carries its fill in the fourth).
Genres for bass music, UK, techno, house, reggaeton, batida, gqom, experimental club music; 0.8: electro, drum & bass,
afro house, amapiano, footwork, trance; 0.10: UK drill, hardcore, phonk and baile funk (breakbeat, trap, minimal and
lo-fi left); 0.16: merengue.
"""
import os
import sys

D = {}
SC = dict(CHROMATIC=0, MAJOR=1, MINOR=2, DORIAN=3, PHRYGIAN=4, LYDIAN=5, MIXOLYDIAN=6, LOCRIAN=7, HARM_MINOR=8,
          MEL_MINOR=9, PENT_MAJOR=10, PENT_MINOR=11, BLUES=12, WHOLE=13, PHRYG_DOM=14, HIRAJOSHI=15)


def g(name, kick, snare, hat, perc, bass, chord, arp, kit, swing, bpm, scales, chord_size):
    D[name] = dict(KICK=kick, SNARE=snare, HAT=hat, PERC=perc, BASS=bass, CHORD=chord, ARP=arp, KIT=kit,
                   SWING=swing, BPM=bpm, SCALES=[SC[s] for s in scales], CS=chord_size)


# 0.8: the progressions of each genre (SQ_PROGS of them): "1:7 4:9" = the tonic's chord with its 7th, then the 4th step's
# with its 9th; colours 7 9 s4 (sus4) s2 (sus2) 6; the number after: bars a chord. The names the FM-1 shows come from the
# key (i / I, VI ...), so a progression fits a minor and a major key alike.
COLORS = {'': 0, '7': 1, '9': 2, 's4': 3, 's2': 4, '6': 5}
P = {}


def progs(name, *lst):
    P[name] = list(lst)


# EVOLVE: how much of the amount goes to the rhythm and to the notes, in % (rhythm-heavy styles move more)
EVO = dict(TECHNO=(70, 35), HARDTECHNO=(90, 30), DUBTECHNO=(45, 45), HOUSE=(65, 45), UKGARAGE=(90, 65), UKFUNKY=(85, 60),
           GRIME=(70, 60), DUBSTEP=(65, 60), JUNGLE=(100, 70), BASSLINE=(85, 70), REGGAETON=(70, 45), BATIDA=(100, 65),
           GQOM=(95, 40), EXPERIMENTAL=(100, 100), ELECTRO=(80, 50), DNB=(85, 60), AFROHOUSE=(70, 50), AMAPIANO=(75, 60),
           FOOTWORK=(95, 55), TRANCE=(55, 50), UKDRILL=(70, 50), HARDCORE=(90, 35), PHONK=(65, 50), BAILEFUNK=(85, 50),
           MERENGUE=(80, 50))

# 0.10 VIAGGIO's set genres, one per library genre: a neighbouring genre the dice may draw from, the ladder (the energy
# 0..100 at which a role enters: KICK SNARE HAT PERC BASS CHORD ARP), half-time (the snare on the 3), afro (the
# percussion from the AFRO / LATIN family first). The swing is the genre's own.
SETG = {}


def setg(name, genre2, ladder, half_time=0, afro=0):
    SETG[name] = dict(G2=genre2, LADDER=ladder, HALF=half_time, AFRO=afro)


# The longer patterns (0.10): a two-bar variation keeps the one-bar pattern it grew from as its first bar; a four-bar
# kick is three bars that breathe and a fourth with the fill.
g('TECHNO',
  ["X...X...X...X...", "X...X...X...X..x", "X...X...X..xX...X...X...X...X.x.",
   "X...X...X...X...X...X...X...X..xX...X...X...X...X..xX...X...X.x2"],
  ["....X.......X...", "....X.......X..g", "............X...", "....X..g....X.x."],
  ["..x...x...x...x.", "x.x.x.x.x.x.x.x.", "oxXxoxXxoxXxoxXx", "..x..xx...x..xx...x..xx...x.xxxx"],
  ["...x..x....x..x.", ".x..x..x.x..x..x", "x..x..x...x..x..", "......x.......x."],
  [("..x...x...x...x.", "..0...0...0...0."), ("xxx.xxx.xxx.xxx.", "000.000.000.000."), ("..xx..xx..xx..xx", "..0c..0c..07..05")],
  [("...x.......x....", "...m.......m...."), ("x.....x.....x...", "n.....n.....n...")],
  [("xxxxxxxxxxxxxxxx", "0370c7030370c703"), ("x.x.x.x.x.x.x.x.", "0.7.c.3.0.7.c.a.")],
  (36, 39, 42, 46), 50, (128, 135), ('MINOR', 'PHRYGIAN', 'DORIAN'), 3)
g('HARDTECHNO',
  ["X...X...X...X...", "X...X...X...X.x.", "X..xX...X..xX..x", "X..xX..xX..xX..xX..xX..xX..xX.2."],
  ["....X.......X...", "........X.......", "....X..x....X..x", "....x...x...x..2"],
  ["..X...X...X...X.", "x.x.x.x.x.x.x.x.", "xxxxxxxxxxxxxxxx", "..xx..xx..xx..xx..xx..xx..xxxxxx"],
  ["..x...x...x...x.", "x..x..x..x..x..x", ".x.x.x.x.x.x.x.x", "...x...x...x..xx"],
  [("..xx..xx..xx..xx", "..00..00..00..00"), (".xxx.xxx.xxx.xxx", ".000.000.000.000"), ("..x...x...x...x.", "..0...0...1...0.")],
  [("x.......x.......", "m.......m......."), ("..x.....x.....x.", "..5.....5.....5.")],
  [("xxxxxxxxxxxxxxxx", "0c0c0c0c0c0c0c0c"), ("x.xx.xx.x.xx.xx.", "0.17.c7.0.17.c7.")],
  (36, 39, 42, 37), 50, (145, 155), ('PHRYGIAN', 'MINOR', 'LOCRIAN'), 3)
g('DUBTECHNO',
  ["X...X...X...X...", "X...X...X...X..x", "X.......X.......", "X...X...X..xX...X.......X...X..x"],
  ["....x.......x...", "............x...", "....o.......x..g", "...........g.x.."],
  ["..x...x...x...x.", "..xo..xo..xo..xo", "x.x.x.x.x.x.x.x.", "..x..ox...x..ox."],
  ["..o.......o.....", "......x.......x.", ".g...g...g...g..", "...o...o...o...o...o...o.o.o...o"],
  [("x.....x.x.......", "0.....0.0......."), ("..x...x...x...x.", "..0...0...0...0."), ("x..x....x..x....", "0..0....3..0....")],
  [("...x.......x....", "...n.......n...."), ("..x..x....x..x..", "..n..n....n..n..")],
  [("x...x...x...x...", "0...3...7...a..."), ("..x...x...x...x.", "..7...c...a...7.")],
  (36, 37, 42, 51), 54, (118, 125), ('MINOR', 'DORIAN', 'PHRYGIAN'), 4)
g('HOUSE',
  ["X...X...X...X...", "X...X...X...X.x.", "X...X...X..xX...X...X...X...X..x",
   "X...X...X...X...X...X...X...X.x.X...X...X...X...X..xX...X..xX.x2"],
  ["....X.......X...", "....X.......X..g", "....X..g....X...", "....X.......X.x."],
  ["..x...x...x...x.", "x.x.x.x.x.x.x.x.", "..xo..xo..xo..xo", "xoxoxoxoxoxoxoxo"],
  ["..X...X...X...X.", "...x..x....x..x.", ".x..x..x.x..x...", "......x.......x.......x.....x.x."],
  [("..x...x...x...x.", "..0...0...0...7."), ("x..x..x.x..x..x.", "0..c..0.0..c..7."), ("..x.x...x...x.x.", "..0.c...0...3.5.")],
  [("..x...x...x...x.", "..n...n...n...n."), ("x..x..x...x..x..", "n..n..n...n..N..")],
  [("xxxxxxxxxxxxxxxx", "037a037a037a037a"), ("x.x.x.x.x.x.x.x.", "0.3.7.c.7.3.0.5.")],
  (36, 39, 42, 46), 54, (122, 126), ('DORIAN', 'MINOR', 'MAJOR'), 4)
g('UKGARAGE',
  ["X.........X.....", "X......x..X.....", "X.........x.x...X......x..X.....",
   "X.........X.....X......x..X.....X.........X.....X..x......X...xx"],
  ["....X.......X...", "....X.......X..g", "....X..g....X...", "....X......gX.g."],
  ["..x...x...x...x.", "x.x.x.x.x.x.x.x.", "..x.x.xx..x.x.xx", ".xxx.xxx.xxx.xxx.xxx.xxx.xxx.xx2"],
  ["...x..x....x....", "..x.....x.x.....", "xgxgxgxgxgxgxgxg", "......x..x....x."],
  [("x..x......x..x..", "0..c......0..7.."), ("x.....x...x.....", "0.....0...5....."), ("x..x..x...x.x...", "0..0..3...5.7...")],
  [("..x....x..x.....", "..n....n..n....."), ("x...x.....x...x.", "N...N.....n...n.")],
  [("x.x.x.x.x.x.x.x.", "0.3.7.a.7.3.0.3."), ("xx.xx.xx.xx.xx.x", "07.3c.07.3c.07.3")],
  (36, 38, 42, 70), 60, (130, 134), ('MINOR', 'DORIAN', 'MAJOR'), 4)
g('UKFUNKY',
  ["X..x..X...x..x..", "X..x..x...X..x..", "X...X..x.x..X...", "X..x...xX..x...xX..x..X...x..x.."],
  ["....X.......X...", "...x..x.....x...", "....X..x.x..X...", "......x.......x."],
  ["x.x.x.x.x.x.x.x.", "..x...x...x...x.", "xxx.xxx.xxx.xxx.", "x.xx.xx.x.xx.xx."],
  ["x..x..x...x.x...", ".x..x.x..x..x.x.", "..x.x...x.x..x..", "x.x..x.x..x.x..xx.x..x.x..x.xx.x"],
  [("x..x..x...x..x..", "0..0..7...5..3.."), ("x.....x.x.....x.", "0.....0.c.....7."), ("..x..x....x..x..", "..0..3....5..7..")],
  [("..x..x....x.....", "..n..n....n....."), ("x..x....x..x....", "n..n....N..N....")],
  [("x.xx.xx.x.xx.xx.", "0.37.a7.0.37.a7."), ("x.x.x.x.x.x.x.x.", "0.7.3.a.0.7.3.c.")],
  (36, 39, 42, 63), 56, (128, 132), ('MINOR', 'DORIAN', 'PHRYGIAN'), 4)
g('GRIME',
  ["X.........x.....", "X.....x...X.....", "X..x......x..x..", "X.......X.x.....X.........x..x.."],
  ["........X.......", "........X......g", "....X.......X...", "........X..x...."],
  ["x.x.x.x.x.x.x.x.", "x...x...x...x...", "x.x.xxx.x.x.xxx.", "..x...x...x...x."],
  ["......x.......x.", "...x.......x....", "x..x..x.x..x..x.", ".......x.......x.......x.....x.x"],
  [("x.....x...x.....", "0.....0...1....."), ("X.......X..x....", "0.......0..c...."), ("x..x..x.........", "0..3..5.........")],
  [("x..x..x.........", "m..m..m........."), ("x.....x.....x...", "5.....5.....5...")],
  [("x.x.x.x.x.x.x.x.", "0.3.0.7.0.3.0.a."), ("xxxxxxxxxxxxxxxx", "0c3c7c3c0c3c7c5c")],
  (36, 38, 42, 39), 50, (138, 142), ('MINOR', 'PHRYGIAN', 'HARM_MINOR'), 3)
g('DUBSTEP',
  ["X...............", "X.........x.....", "X.......x.......X.........x.x...", "X.....x.........X......x..x....."],
  ["........X.......", "........X......g", "........X...............X..g....", "........X.......g.......X......."],
  ["..x...x...x...x.", "x.x.x.x.x.x.x.x.", "x.xxx.x.x.xxx.x.", "....x.......x.......x.......x.xx"],
  ["......x.......x.", "...x.......x....", "x..x..x.x..x..x.", "..........x....."],
  [("x.......x.......", "0.......0......."), ("x..2....x...4...", "0..0....0...0..."), ("x.....x.x...x...", "0.....3.5...7...")],
  [("x...............", "m..............."), ("x.......x.......", "m.......n.......")],
  [("x..x..x..x..x..x", "0..3..7..c..7..3"), ("x.x.x.x.x.x.x.x.", "0.7.c.7.0.3.5.7.")],
  (36, 38, 42, 37), 52, (138, 142), ('MINOR', 'PHRYGIAN', 'HARM_MINOR'), 3)
g('JUNGLE',
  ["X.........x.....", "X.........X.x...", "X.x.......x.....X.........x.....",
   "X.........x.....X.........X.x...X.x.......x.....X.x.......X..x.x"],
  ["....X.......X...", "....X..g.g..X..g", "....X..g.g..X...g...X..g.g..X...", "....X.......X..x....X..x.g..X.g."],
  ["x.x.x.x.x.x.x.x.", "xxxxxxxxxxxxxxxx", "x.xxx.x.x.xxx.x.", "..x...x...x...x...x...x...x.xxxx"],
  ["..x...x...x...x.", "...x.......x....", ".g..g..g.g..g..g", "x..x..x..x..x..x"],
  [("x.......x.......", "0.......0......."), ("x.....x...x.....", "0.....0...3....."), ("x..x....x.x.....", "0..0....5.3.....")],
  [("x...............", "n..............."), ("x.......x.......", "m.......n.......")],
  [("x.x.x.x.x.x.x.x.", "0.3.7.c.7.3.0.3."), ("xxxxxxxxxxxxxxxx", "0307030703070307")],
  (36, 38, 42, 51), 50, (170, 175), ('MINOR', 'DORIAN', 'PHRYGIAN'), 3)
g('BASSLINE',
  ["X...X...X...X...", "X...X...X...X..x", "X......xX...X...", "X...X..x..X.X...X...X...X..xX.x."],
  ["....X.......X...", "....X.......X..g", "....X..g....X...", "....X......xX..."],
  ["..x...x...x...x.", "..x.x.xx..x.x.xx", "x.x.x.x.x.x.x.x.", ".xx..xx..xx..xx..xx..xx..xx.xxxx"],
  ["...x..x....x..x.", "x.g.x.g.x.g.x.g.", "......x.......x.", "..x.....x.x....."],
  [("x.x.x.x.x.x.x.x.", "0.c.0.c.0.c.0.c."), ("x..x..x...x..x..", "0..c..0...7..5.."), ("xx..x.x.xx..x.x.", "0c..0.7.0c..3.5.")],
  [("..x...x...x...x.", "..m...m...m...m."), ("x..x..x...x.....", "m..m..m...m.....")],
  [("xxxxxxxxxxxxxxxx", "0c0c3c3c5c5c7c7c"), ("x.x.x.x.x.x.x.x.", "0.3.7.c.0.3.7.a.")],
  (36, 39, 42, 46), 56, (135, 140), ('MINOR', 'DORIAN', 'PHRYGIAN'), 3)
g('REGGAETON',
  ["X...X...X...X...", "X.......X.......", "X...X...X...X..x", "X..xX...X..xX...X...X..xX...X.x."],
  ["...X..x....X..x.", "...X..X....X..X.", "...x..x....x..xg", "...X..x....X..x....X..x....X.xxx"],
  ["x.x.x.x.x.x.x.x.", "..x...x...x...x.", "xxxxxxxxxxxxxxxx", "x.xx.xx.x.xx.xx."],
  ["...x..x....x..x.", "......x.......x.", "x..x..x...x.x...", "....x..x....x..x....x..x..x.x..x"],
  [("x..x..x.x..x..x.", "0..0..0.0..0..0."), ("x..x....x..x....", "0..0....5..5...."), ("x.....x.x.....x.", "0.....3.5.....7.")],
  [("x..x..x.x..x..x.", "m..m..m.m..m..m."), ("x.......x.......", "m.......M.......")],
  [("x..x..x.x..x..x.", "0..3..7.0..3..a."), ("x.x.x.x.x.x.x.x.", "0.3.7.3.0.3.7.c.")],
  (36, 38, 42, 37), 50, (90, 100), ('MINOR', 'HARM_MINOR', 'PHRYG_DOM'), 3)
g('BATIDA',
  ["X..x..X...X..x..", "X...X..x..X.X...", "X..X..X.X..X..X.", "X.....X.X..x.x..X..x..X.X..x.xx."],
  ["....X.......X...", "....X..x....X...", "...x....X..x....", "....X.......X.x."],
  ["x.xx.xx.x.xx.xx.", "x.x.x.x.x.x.x.x.", "xxxxxxxxxxxxxxxx", "..x.x...x.x...x."],
  ["x..x..x..x..x.x.", "..x..x..x..x..x.", "x.x..x.x.x..x.x.", ".x..x..x..x..x.x.x..x..x.x.x.x.x"],
  [("x..x..x...x..x..", "0..0..7...5..3.."), ("x.x...x.x.x...x.", "0.0...7.5.3...0."), ("x..x..x.x..x..x.", "0..c..0.7..5..3.")],
  [("x..x..x.........", "M..M..m........."), ("..x..x..x..x..x.", "..m..m..m..m..m.")],
  [("x.xx.xx.x.xx.xx.", "0.47.c7.0.47.c7."), ("x.x.x.x.x.x.x.x.", "0.4.7.c.7.4.0.4.")],
  (36, 39, 42, 56), 52, (128, 138), ('MINOR', 'MAJOR', 'DORIAN'), 3)
g('GQOM',
  ["X.....X.....X...", "X..X..X.....X...", "X.....X..X......", "X.....X...X..X..X.....X.....X.X."],
  ["....X.......X...", "........X.......", "......X.......X.", "....X..X....X..."],
  ["..x...x...x...x.", "x...x...x...x...", "..x..x....x..x..", "x.xx.x..x.xx.x.."],
  ["...x..x.....x...", "x..x..x...x.x...", ".x...x...x...x..", "...xx.....x.x......xx.....x.x.xx"],
  [("x.....x.....x...", "0.....0.....0..."), ("x.....x..x......", "0.....0..1......"), ("x..x..x.....x...", "0..0..3.....1...")],
  [("x...............", "m..............."), ("x.....x.........", "m.....m.........")],
  [("x..x..x..x..x..x", "0..3..7..3..0..1"), ("x.....x.....x...", "0.....7.....c...")],
  (36, 39, 42, 47), 54, (120, 127), ('MINOR', 'PHRYGIAN', 'HARM_MINOR'), 3)
g('EXPERIMENTAL',
  ["X..x.x...x.x..x.", "X....x....x....x", "X..x..x..X.x....x..x..X.....x...", "X.......x..x.x.."],
  ["......x.....x..x", ".....x....x.....", "...x.....x....x.", "..g..g..X..g..g."],
  ["x.xx.x.xxx.x.xx.", "xxx.xx.x..xxx.x.", "x...x..x.x...x..", "3..x..2...x.4..."],
  ["x....x....x....x", "..x.....x...x..x", ".x.x...x..xx....", "x..x..x..x..x..x.x..x..x..x.x.x2"],
  [("x...x..x..x.x...", "0...1..6..3.b..."), ("x.....x....x....", "0.....6....1...."), ("xx..x...x.x..x..", "01..5...6.3..b..")],
  [("x.....x....x....", "s.....5....s...."), ("x.........x.....", "N.........m.....")],
  [("xxxxxxxxxxxxxxxx", "0618206182061820"), ("x.x.xx.x.xx.x.x.", "0.6.1b.5.3a.2.8.")],
  (36, 37, 42, 56), 50, (100, 160), ('WHOLE', 'HIRAJOSHI', 'LOCRIAN'), 3)
# 0.8: more genres (two pages of 12 on the grid's BEAT view)
g('ELECTRO',
  ["X.....X...X.....", "X.....X.X.....x.", "X..x..X...X.....", "X.....x...X..x..X.....X.X.....x."],
  ["....X.......X...", "....X.......X..x", "....X..x....X...", "....X.......X.g."],
  ["x.x.x.x.x.x.x.x.", "xxxxxxxxxxxxxxxx", "x.xxx.xxx.xxx.xx", "..x...x...x...x."],
  ["..x.....x...x...", "x..x..x...x.....", "......x.......x.", ".x...x...x..x....x...x...x..x.x."],
  [("x.....x...x.....", "0.....0...c....."), ("x..x..x.x..x....", "0..0..c.7..5...."), ("x.x...x.x.x...x.", "0.c...0.3.5...7.")],
  [("x.....x.........", "m.....m........."), ("x...x.......x...", "m...m.......n...")],
  [("x.x.x.x.x.x.x.x.", "0.3.7.c.7.3.0.3."), ("xxxxxxxxxxxxxxxx", "0c370c370c370c37")],
  (36, 40, 42, 56), 50, (125, 135), ('MINOR', 'PHRYGIAN', 'DORIAN'), 3)
g('DNB',
  ["X.........X.....", "X.........x.x...", "X.x.......X.....X.........x.x...",
   "X.........X.....X.........x.x...X.x.......X.....X......x..X...xx"],
  ["....X.......X...", "....X.......X..g", "....X..g....X...", "....X...g...X.g."],
  ["x.x.x.x.x.x.x.x.", "xxxxxxxxxxxxxxxx", "..x...x...x...x.", "x.xxx.xxx.xxx.xxx.xxx.xxx.xxxxxx"],
  ["..x.......x.....", "......x.......x.", "x..x..x...x..x..", ".g..g...g..g...."],
  [("x.......x.......", "0.......0......."), ("x.....x.......x.", "0.....0.......3."), ("x..x....x.x.....", "0..0....5.3.....")],
  [("x...............", "n..............."), ("x.......x.......", "n.......m.......")],
  [("x..x..x..x..x..x", "0..7..c..7..3..5"), ("x.x.x.x.x.x.x.x.", "0.3.7.a.c.a.7.3.")],
  (36, 38, 42, 51), 50, (170, 176), ('MINOR', 'DORIAN', 'PHRYGIAN'), 4)
g('AFROHOUSE',
  ["X...X...X...X...", "X...X...X...X..x", "X...X..xX...X...", "X...X...X..xX...X...X..xX...X.x."],
  ["....x.......x...", "....x..g....x...", "...........x....", "....x.....g.x..."],
  ["..x...x...x...x.", "x.xxx.xxx.xxx.xx", "..xx..x...xx..x.", "xxxxxxxxxxxxxxxx"],
  ["x..x..x...x..x..", "..x.x..x..x.x..x", ".x..x.x..x..x.x.", "x.x..x..x.x..x..x.x..x..x.x.xx.x"],
  [("x..x......x.....", "0..0......7....."), ("x.....x...x..x..", "0.....0...5..3.."), ("..x...x...x..x..", "..0...0...3..5..")],
  [("..x.....x.....x.", "..n.....n.....n."), ("x.....x...x.....", "n.....n...m.....")],
  [("x..x..x..x..x..x", "0..3..7..a..7..3"), ("x.xx.x.xx.xx.x.x", "0.37.a.c7.30.7.a")],
  (36, 39, 42, 63), 54, (118, 124), ('MINOR', 'DORIAN', 'PHRYGIAN'), 4)
g('AMAPIANO',
  ["X...X...X...X...", "X.......X.......", "X...X...X......x", "X..x....X..x....X.......X..x..x."],
  ["....x.......x...", "......x.......x.", "...x...x...x..x.", "....x..x....x.x."],
  ["xxxxxxxxxxxxxxxx", "x.x.x.x.x.x.x.x.", "oxxooxxooxxooxxo", "..x...x...x...x."],
  ["..x..x....x..x..", ".x...x.x..x...x.", "x..x..x.x..x....", "...x...x...x..xx...x...x..x.x.xx"],
  [("...x..x...x.x...", "...0..7...5.3..."), ("x..x....x.x...x.", "0..c....7.5...3."), ("..x..x.x..x..x..", "..0..0.7..3..5..")],
  [("x.....x...x.....", "n.....n...n....."), ("..x...x...x...x.", "..N...N...n...n.")],
  [("x..x..x..x..x...", "0..3..7..a..c..."), ("..x.x...x.x...x.", "..7.3...0.3...5.")],
  (36, 37, 70, 63), 58, (110, 116), ('DORIAN', 'MINOR', 'MAJOR'), 4)
g('FOOTWORK',
  ["X..X..X...X..X..", "X..x..X..x..X...", "X.....X..X..X..x", "X..X......X..X..X..X..X...X.X.X."],
  ["........X.......", "....X.......X...", "........X.....x.", "....x.......X..x"],
  ["x.x.x.x.x.x.x.x.", "..x...x...x...x.", "xxx.xxx.xxx.xxx.", "x..x..x..x..x..x"],
  ["x..x..x..x..x..x", ".x..x..x..x..x..", "..x....x..x....x", "x.x...x.x.x...x.x.x...x.x.x.xx.x"],
  [("x..x..x...x..x..", "0..0..0...3..5.."), ("x.....x..x..x...", "0.....0..7..5..."), ("x..x......x..x..", "0..c......5..3..")],
  [("x.........x.....", "n.........n....."), ("x..x..x.........", "m..m..m.........")],
  [("x..x..x..x..x..x", "0..3..7..c..7..3"), ("x.x..x.x..x.x..x", "0.3..7.a..c.a..7")],
  (36, 39, 42, 75), 50, (155, 165), ('MINOR', 'DORIAN', 'PENT_MINOR'), 4)
g('TRANCE',
  ["X...X...X...X...", "X...X...X...X..x", "X...X...X...X.x.", "X...X...X..xX...X...X...X...X.xx"],
  ["....X.......X...", "....X.......X..x", "............X...", "....X.......X.xx"],
  ["..x...x...x...x.", "x.x.x.x.x.x.x.x.", "..xx..xx..xx..xx", "oxXxoxXxoxXxoxXx"],
  ["..........x.....", "......x.......x.", "...x.......x....", "x.......x.......x.............xx"],
  [(".xxx.xxx.xxx.xxx", ".000.000.000.000"), ("..x...x...x...x.", "..0...0...0...0."), (".xx..xx..xx..xx.", ".0c..0c..07..05.")],
  [("x...............", "m..............."), ("x.......x.......", "m.......M.......")],
  [("xxxxxxxxxxxxxxxx", "037c037c037c037c"), ("x.xxx.xxx.xxx.xx", "0.37c.73c.7c3.7c")],
  (36, 39, 42, 46), 50, (136, 140), ('MINOR', 'HARM_MINOR', 'PHRYGIAN'), 3)
# 0.10: UK drill (half-time at 140: the snare on the 3 and on the "and" of 4, kicks off the beat, hats in triplet bursts,
# the 808 sliding to the flat 2nd and the flat 6th) and hardcore / gabber (the kick on every beat and doubled, hats off
# the beat, snare rolls, hoover stabs: power chords and minor)
g('UKDRILL',
  ["X.........x.....", "X......x..x.....", "X......x..x.....X.........x..x..",
   "X......x..x.....X.........x.....X......x..x.....X......x..x.x.xx"],
  ["........X.....X.", "......g.X.....X.", "........X..g..X.", "........X.....X.......g.X.....2."],
  ["x.x.x.x.x.x.x.x.", "x.x.x.x.x.x.3.x.", "x.x.3.x.x.x.x.3.", "x.x.x.x.x.x.3.x.x.x.3.x.x.x.x.33"],
  ["......x.......x.", "...x.......x....", ".......x.....x..", "..x.....x.....x."],
  [("X.........x.....", "0.........0....."), ("X......x..x.....", "0......0..1....."), ("X......x..x....x", "0......8..3....1")],
  [("x...............", "m..............."), ("x.......x.....x.", "m.......n.....m.")],
  [("x.x.x.x.x.x.x.x.", "0.3.7.8.7.3.0.1."), ("x..x..x.x..x..x.", "0..3..8.7..3..1.")],
  (36, 38, 42, 37), 54, (140, 145), ('MINOR', 'PHRYGIAN', 'HARM_MINOR'), 3)
g('HARDCORE',
  ["X...X...X...X...", "X.x.X.x.X.x.X.x.", "XX..X...XX..X...XX..X...X.x.X.x.",
   "X...X...X...X...X...X...X...X.x.X...X...X...X...X.x.X.x.X.x.X.22"],
  ["....X.......X...", "....X.......X..2", "....X..x....X..x", "....X.......X.......X.......2222"],
  ["..x...x...x...x.", "..X...X...X...X.", "x.x.x.x.x.x.x.x.", "..x...x...x...x...x...x...x.xxxx"],
  ["x.......x.......", "..x.x...x.x...x.", "....x..x....x..x", "x..x..x..x..x..x"],
  [("x...x...x...x...", "0...0...0...0..."), ("x.x.x.x.x.x.x.x.", "0.0.0.0.0.0.0.0."), ("x...x..xx...x..x", "0...0..10...0..1")],
  [("x.....x.....x...", "5.....5.....5..."), ("x.......x.....x.", "m.......5.....m.")],
  [("xxxxxxxxxxxxxxxx", "0c0c1d1d0c0c3f3f"), ("x.x.x.x.x.x.x.x.", "0.7.c.7.1.8.c.8.")],
  (36, 38, 42, 49), 50, (160, 200), ('PHRYGIAN', 'MINOR', 'HARM_MINOR'), 3)
# 0.10: phonk (Memphis to drift phonk): half-time, the 808 slides, trap hats that roll, the cowbell riff as the ARP
g('PHONK',
  ["X.........X.X...", "X.....x...X.....", "X.........X.X...X......x..X.....",
   "X.........X.X...X.....x...X.....X.........X.X...X.....x...X.X.xx"],
  ["........X.......", "........X.....x.", "...x....X.......", "........X...............X.....22"],
  ["x.x.x.x.x.x.x.x.", "x.x.x.3.x.x.x.3.", "x.x.x.x.x.3.x.x.x.x.x.x.3.x.3.33", "xxxxxxxxxxxxxxxx"],
  ["..x...x...x...x.", "x..x..x...x..x..", "......x.......x.", "..x.....x..x...."],
  [("X.........X.X...", "0.........0.0..."), ("X.....x...X.....", "0.....1...0....."), ("X.......x.X..x..", "0.......a.0..7..")],
  [("x...............", "m..............."), ("x.......x.......", "m.......n.......")],
  [("x.x.x.x.x.x.x.x.", "0.1.0.7.0.1.0.3."), ("x..x..x.x..x..x.", "0..3..1.0..7..1.")],
  (36, 38, 42, 56), 52, (130, 150), ('PHRYGIAN', 'MINOR', 'HARM_MINOR'), 3)
# 0.10: baile funk (funk carioca): the tamborzao kick in 3-3-2 cells, the clap on 2 and 4, the atabaque in between
g('BAILEFUNK',
  ["X..X..X.X..X..X.", "X..X..X...X..X..", "X..X..X.X..X..X.X..X..X.X.X.X...",
   "X..X..X.X..X..X.X..X..X...X..X..X..X..X.X..X..X.X..X..X.X.X.X.xx"],
  ["....X.......X...", "....X.......X..x", "..x.X.....x.X...", "....X.......X.......X.......X.xx"],
  ["x.x.x.x.x.x.x.x.", "..x...x...x...x.", "xxxxxxxxxxxxxxxx", "x.xx.xx.x.xx.xx.x.xx.xx.x.xxxxxx"],
  ["..x..x.x..x..x.x", "...x...x.x...x..", "x.....x.x.....x.", "..x..x.x..x..x.x..x..x.x..x.xxxx"],
  [("x..x..x.x..x..x.", "0..0..0.0..0..0."), ("x..x..x...x..x..", "0..0..3...0..5.."), ("x.....x.x.....x.", "0.....0.a.....7.")],
  [("x.......x.......", "m.......m......."), ("x..x....x..x....", "m..m....M..M....")],
  [("x.x.x.x.x.x.x.x.", "0.3.5.3.0.3.7.3."), ("x..x..x.x..x..x.", "0..0..3.5..3..0.")],
  (36, 39, 42, 63), 54, (125, 135), ('MINOR', 'PHRYGIAN', 'HARM_MINOR'), 3)

# 0.16: merengue (Dominican, in 2): the bass drum on every beat (the modern orquesta and merengue de calle), the guira
# as the HAT (an 8th and two 16ths a beat: "cha chi-ki"), the tambora as the PERC (the slap and its roll into the bar),
# its rim as the SNARE on the "and" of 2 and 4, the bass anticipating the beat, the piano's offbeat montuno, the
# accordion / sax riff as the ARP; major keys, I - V7
g('MERENGUE',
  ["X...X...X...X...", "X.......X.......", "X...X...X...X.x.", "X...X...X...X...X...X...X.x.X.x."],
  ["......x.......x.", "....x.x.....x.x.", "......x...x...x.", "......x.......x.......x.....x.x2"],
  ["x.xxx.xxx.xxx.xx", "X.xxX.xxX.xxX.xx", "x.x.x.x.x.x.x.x.", "X.xxX.xxX.xxX.xxX.xxX.xxX.xxxxxx"],
  ["x..x.xx.x..x.xx.", "x.xx..x.x.xx..x.", "....x..x....x.xx", "x..x.xx.x..x.xx.x..x.xx.x.x.x2x2"],
  [("x.....x.x.....x.", "0.....7.0.....7."), ("x...x...x...x...", "0...7...0...7..."), ("x..x..x.x..x..x.", "0..0..7.0..c..7.")],
  [("..x...x...x...x.", "..M...M...M...M."), ("x..x..x.x..x..x.", "M..M..M.M..M..M.")],
  [("xxxxxxxxxxxxxxxx", "047cc740047cc740"), ("x.x.x.xxx.x.x.xx", "0.4.7.97c.9.7.42")],
  (36, 37, 69, 66), 50, (128, 156), ('MAJOR', 'MIXOLYDIAN', 'MINOR'), 3)

progs('TECHNO', ("1", 4), ("1 6", 2), ("1 4", 2), ("1 7 6 7", 1), ("1:7 4:7", 2), ("1:s4 1", 2))
progs('HARDTECHNO', ("1", 4), ("1 2", 2), ("1 6", 2), ("1 7", 2), ("1 2 1 7", 1), ("1:s2 1", 2))
progs('DUBTECHNO', ("1:7", 4), ("1:7 4:9", 2), ("1:9 6:7", 2), ("1:7 7:6 6:7 7", 1), ("1:s4 1:7", 2), ("4:9 1:7", 2))
progs('HOUSE', ("1:7 4:9", 1), ("2:7 5:7 1:9 6:7", 1), ("1:9 6:9 4:7 5", 1), ("6 4 1 5", 1), ("1:7 7:6 6:7 5:s4", 1),
      ("4:9 5:7 3:7 6:7", 1))
progs('UKGARAGE', ("1:7 4:9", 1), ("1:9 6:7 3:7 7", 1), ("2:7 5:7 1:9 1:9", 1), ("6:7 5:7 1:9 1:9", 1), ("1:9 4:7", 2),
      ("1:7 3:7 4:9 5:s4", 1))
progs('UKFUNKY', ("1:7 4:7", 1), ("1:9 7:7", 2), ("1:7 6:7 7:7 1:7", 1), ("4:9 1:7", 2), ("1:7", 4), ("2:7 5:7", 2))
progs('GRIME', ("1", 4), ("1 2", 2), ("1 6 7 1", 1), ("1:s4 1", 2), ("1 4 6 5", 1), ("1 6", 2))
progs('DUBSTEP', ("1", 4), ("1 6", 2), ("1 2", 2), ("1 7 6 5", 1), ("1 4", 2), ("1:s2 1", 2))
progs('JUNGLE', ("1:9 4:7", 2), ("1:7 6:7", 2), ("1:9 7:7 6:7 7", 1), ("2:7 5:7 1:9 1:9", 1), ("1:7", 4), ("4:9 5:7", 2))
progs('BASSLINE', ("1 6 3 7", 1), ("1 4", 2), ("1 7 6 7", 1), ("6 7 1 1", 1), ("1:7 4:7", 2), ("1 5 6 4", 1))
progs('REGGAETON', ("1 6 3 7", 1), ("1 4 5 1", 1), ("6 7 1 1", 1), ("1 4 7 3", 1), ("1 6 7 1", 1), ("1 5 6 4", 1))
progs('BATIDA', ("1 4 5 4", 1), ("6 4 1 5", 1), ("1 5 6 4", 1), ("1 7 6 7", 1), ("2 5 1 1", 1), ("1 6 4 5", 1))
progs('GQOM', ("1", 4), ("1 2", 2), ("1 6", 2), ("1:s4 1", 2), ("1 7", 2), ("1 4", 2))
progs('EXPERIMENTAL', ("1:s2 3:6 7:9 2:7", 1), ("1:9 2:s4", 2), ("1 7:s2 6:9 5:s4", 1), ("4:9 1:6", 2), ("1:7 3:7 5:7 7:7", 1),
      ("1:s4 1:s2", 2))
progs('ELECTRO', ("1", 4), ("1 6", 2), ("1 7", 2), ("1 4 6 5", 1), ("1:7 4:7", 2), ("1:s4 1", 2))
progs('DNB', ("1:7 6:7", 2), ("1:9 4:7", 2), ("1:7", 4), ("6:7 7 1:9 1:9", 1), ("1:9 7:7 6:7 7:s4", 1), ("4:9 5:7", 2))
progs('AFROHOUSE', ("1:7 4:9", 2), ("1:9 6:7", 2), ("1:7", 4), ("1:9 4:9 6:7 5:s4", 1), ("1:7 7:7", 2), ("4:9 1:7", 2))
progs('AMAPIANO', ("1:9 4:9", 2), ("2:7 5:7 1:9 1:9", 1), ("1:7 6:7 4:9 5:7", 1), ("6:7 4:9 1:9 5", 1), ("1:9", 4),
      ("4:9 5:7 3:7 6:7", 1))
progs('FOOTWORK', ("1:7", 4), ("1:7 4:9", 2), ("1:9 6:7", 2), ("1:7 6:7 7:7 1:7", 1), ("4:9 5:7", 2), ("1:s4 1:7", 2))
progs('TRANCE', ("1 6 3 7", 1), ("6 4 1 5", 1), ("1 7 6 7", 2), ("1 4 6 5", 1), ("6 7 1 1", 1), ("1:s4 1 6 7", 2))
# drill: i-VI-III-VII and i-II (the flat 2nd of the phrygian); hardcore: the tonic, i-II, i-VI, i-VII-VI-VII
progs('UKDRILL', ("1 6 3 7", 1), ("1 2", 2), ("1", 4), ("1 6", 2), ("6 7 1 1", 1), ("1 4 2 1", 1))
progs('HARDCORE', ("1", 4), ("1 2", 2), ("1 6", 2), ("1 7 6 7", 1), ("1 2 1 7", 1), ("1:s2 1", 2))
progs('PHONK', ("1", 4), ("1 6", 2), ("1 2", 2), ("1 4", 2), ("1 7 6 6", 1), ("1:7 5", 2))
progs('BAILEFUNK', ("1 6", 2), ("1 4 5 1", 1), ("1 7 6 7", 1), ("1", 4), ("6 7 1 1", 1), ("1 2", 2))
# merengue: I - V7 (the merengue's own), I IV V7 I, I vi ii V7, I IV I V7, I ii V7 I, vi IV V7 I
progs('MERENGUE', ("1 5:7", 1), ("1 4 5:7 1", 1), ("1 6 2 5:7", 1), ("1 4 1 5:7", 1), ("1 2 5:7 1", 1), ("6 4 5:7 1", 1))

# the set genres: ladder = KICK SNARE HAT PERC BASS CHORD ARP (the kick within 15, the first in)
setg('TECHNO', 'HARDTECHNO', (0, 50, 20, 45, 35, 60, 75))
setg('HARDTECHNO', 'TECHNO', (5, 45, 20, 35, 15, 70, 55))
setg('DUBTECHNO', 'TECHNO', (10, 60, 25, 45, 35, 30, 70))              # the chord early: it is the dub
setg('HOUSE', 'AFROHOUSE', (0, 30, 15, 50, 25, 40, 70))
setg('UKGARAGE', 'UKFUNKY', (5, 20, 15, 45, 30, 50, 65))
setg('UKFUNKY', 'UKGARAGE', (5, 30, 20, 15, 35, 55, 70), afro=1)      # the percussion makes it funky
setg('GRIME', 'UKDRILL', (5, 15, 40, 55, 20, 35, 70), half_time=1)
setg('DUBSTEP', 'GRIME', (15, 20, 35, 50, 10, 60, 75), half_time=1)
setg('JUNGLE', 'DNB', (10, 5, 30, 45, 20, 65, 75))                     # the break first: snare early, no half-time
setg('BASSLINE', 'UKGARAGE', (0, 25, 20, 50, 10, 55, 70))              # the bass is the genre
setg('REGGAETON', 'BATIDA', (0, 10, 40, 25, 35, 55, 75), afro=1)       # the dembow: kick and snare at once
setg('BATIDA', 'GQOM', (0, 35, 30, 10, 40, 60, 70), afro=1)
setg('GQOM', 'BATIDA', (0, 45, 35, 15, 30, 65, 80), afro=1)
setg('EXPERIMENTAL', 'FOOTWORK', (10, 40, 50, 20, 35, 30, 60))
setg('ELECTRO', 'TECHNO', (0, 15, 25, 55, 20, 50, 40))                 # the arp early: the electro lead
setg('DNB', 'JUNGLE', (10, 5, 25, 50, 15, 60, 75))
setg('AFROHOUSE', 'HOUSE', (0, 50, 30, 10, 35, 45, 70), afro=1)
setg('AMAPIANO', 'AFROHOUSE', (15, 55, 35, 20, 30, 10, 70), afro=1)    # the piano opens, the log drum (bass) after
setg('FOOTWORK', 'JUNGLE', (0, 30, 35, 15, 25, 70, 55))
setg('TRANCE', 'TECHNO', (0, 45, 20, 60, 15, 50, 30))                  # the arp early: the trance lead
setg('UKDRILL', 'GRIME', (5, 15, 10, 50, 25, 45, 70), half_time=1)
setg('HARDCORE', 'HARDTECHNO', (0, 35, 15, 55, 20, 40, 70))
setg('PHONK', 'UKDRILL', (0, 20, 15, 45, 10, 55, 30), half_time=1)        # the cowbell riff (ARP) comes early
setg('BAILEFUNK', 'REGGAETON', (0, 25, 30, 10, 20, 60, 70), afro=1)
setg('MERENGUE', 'BATIDA', (0, 40, 5, 10, 25, 35, 55), afro=1)       # the kick, then the guira and the tambora

GENRES = ['TECHNO', 'HARDTECHNO', 'DUBTECHNO', 'HOUSE', 'UKGARAGE', 'UKFUNKY', 'GRIME', 'DUBSTEP', 'JUNGLE', 'BASSLINE',
          'REGGAETON', 'BATIDA', 'GQOM', 'EXPERIMENTAL', 'ELECTRO', 'DNB', 'AFROHOUSE', 'AMAPIANO', 'FOOTWORK', 'TRANCE',
          'UKDRILL', 'HARDCORE', 'PHONK', 'BAILEFUNK', 'MERENGUE']
SHOWN = ['TECHNO', 'HARDTECHNO', 'DUB TECHNO', 'HOUSE', 'UK GARAGE', 'UK FUNKY', 'GRIME', 'DUBSTEP', 'JUNGLE', 'BASSLINE',
         'REGGAETON', 'BATIDA', 'GQOM', 'EXPERIMENT', 'ELECTRO', 'DRUM+BASS', 'AFRO HOUSE', 'AMAPIANO', 'FOOTWORK', 'TRANCE',
         'UK DRILL', 'HARDCORE', 'PHONK', 'BAILE FUNK', 'MERENGUE']
# the SQ_GENRE_* names of sagga_beats.h, in this order (the enum is written by hand there: keep the two together)
ENUM = ['TECHNO', 'HARDTECHNO', 'DUBTECHNO', 'HOUSE', 'UKG', 'UKFUNKY', 'GRIME', 'DUBSTEP', 'JUNGLE', 'BASSLINE',
        'REGGAETON', 'BATIDA', 'GQOM', 'EXPERIMENTAL', 'ELECTRO', 'DNB', 'AFROHOUSE', 'AMAPIANO', 'FOOTWORK', 'TRANCE',
        'UKDRILL', 'HARDCORE', 'PHONK', 'BAILEFUNK', 'MERENGUE']
FUNCS = ['KICK', 'SNARE', 'HAT', 'PERC', 'BASS', 'CHORD', 'ARP']
DRUMS = FUNCS[:4]
WANT = dict(KICK=4, SNARE=4, HAT=4, PERC=4, BASS=3, CHORD=2, ARP=2)
# the four-bar kicks the library must have (the genres that live on four-bar phrases)
WANT64 = ['TECHNO', 'HOUSE', 'UKGARAGE', 'JUNGLE', 'DNB', 'UKDRILL', 'HARDCORE']
assert list(D) == GENRES, list(D)
assert len(GENRES) == len(SHOWN) == len(ENUM) == 25
ok = True
for gn in GENRES:
    for fn in FUNCS:
        v = D[gn][fn]
        if len(v) != WANT[fn]:
            print('count', gn, fn, len(v)); ok = False
        seen = set()
        for e in v:
            r, n = (e if fn in ('BASS', 'CHORD', 'ARP') else (e, None))
            if r in seen: print('dup', gn, fn, r); ok = False
            seen.add(r)
            if len(r) not in (16, 32, 64): print('len', gn, fn, r, len(r)); ok = False
            if any(c not in '.xXog234' for c in r): print('chr', gn, fn, r); ok = False
            if set(r) == {'.'}: print('empty', gn, fn); ok = False
            if fn == 'KICK' and r[0] not in 'Xx': print('kick not on one', gn, r); ok = False
            if n is not None:
                if len(n) != len(r): print('nlen', gn, fn, r, n); ok = False; continue
                for a, b in zip(r, n):
                    if a == '.' and b != '.': print('note at a rest', gn, fn, r, n); ok = False
                    if a != '.':
                        valid = 'mMnN7s5' if fn == 'CHORD' else '0123456789abcdef'
                        if b not in valid: print('bad note', gn, fn, r, n); ok = False
    # 0.10: every genre has a two-bar kick (or longer) and a two-bar hat or perc; some a four-bar kick
    if not any(len(r) >= 32 for r in D[gn]['KICK']): print('no two-bar kick', gn); ok = False
    if not any(len(r) >= 32 for r in D[gn]['HAT'] + D[gn]['PERC']): print('no two-bar hat / perc', gn); ok = False
    if gn in WANT64 and not any(len(r) == 64 for r in D[gn]['KICK']): print('no four-bar kick', gn); ok = False
    k = D[gn]['KIT']
    if len(k) != 4 or not all(27 <= x <= 87 for x in k): print('kit', gn, k); ok = False
    if not 50 <= D[gn]['SWING'] <= 66: print('swing', gn); ok = False
    lo, hi = D[gn]['BPM']
    if not 30 <= lo <= hi <= 300: print('bpm', gn); ok = False
    if D[gn]['CS'] not in (3, 4): print('chord size', gn); ok = False
    if len(P.get(gn, [])) != 6: print('progressions', gn, len(P.get(gn, []))); ok = False
    for text, bars in P.get(gn, []):
        toks = text.split()
        if not 1 <= len(toks) <= 8 or bars not in (1, 2, 4, 8): print('prog', gn, text, bars); ok = False
        for tk in toks:
            d, _, c = tk.partition(':')
            if d not in '1234567' or len(d) != 1 or c not in COLORS: print('prog chord', gn, text, tk); ok = False
    if gn not in EVO: print('evolve', gn); ok = False
    if len(SHOWN[GENRES.index(gn)]) > 10: print('name too long', gn); ok = False
    s = SETG.get(gn)
    if not s: print('set genre', gn); ok = False
    else:
        if s['G2'] not in GENRES or s['G2'] == gn: print('set genre2', gn, s['G2']); ok = False
        if len(s['LADDER']) != 7 or not all(0 <= x <= 100 for x in s['LADDER']): print('ladder', gn); ok = False
        elif s['LADDER'][0] > 15: print('ladder: the kick comes first', gn); ok = False
        if s['HALF'] not in (0, 1) or s['AFRO'] not in (0, 1): print('set genre flags', gn); ok = False
if set(P) != set(GENRES): print('progressions of genres that do not exist', set(P) - set(GENRES)); ok = False
if set(SETG) != set(GENRES): print('set genres that do not exist', set(SETG) - set(GENRES)); ok = False
if not ok:
    sys.exit(1)


def cstr(s): return '"' + s + '"'


def fill_ratchet(gn):
    """how the genre rolls a fill: in triplets if its drums already do ('3' somewhere), else doubled"""
    return 3 if any('3' in r for fn in DRUMS for r in D[gn][fn]) else 2




# ---- 0.11: the bands and the variations of their parts (tools/beat_parts.py)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import beat_parts as BP                                                        # noqa: E402

FUNC_ID = {n: i for i, n in enumerate(BP.PARTS)}
OLD = set(FUNCS)
PI_DIR = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hub', 'patterns')
NEWLIB = {}                                                                    # genre -> [(part, main, in_band, flash, pi, note)]
for gn in GENRES:
    spec, mp, extra = BP.BANDS[gn]
    band = BP.parse_band(spec)
    members = [(p, m, 1) for p, m in band] + [(p, False, 0) for p in extra.split()]
    names = [p for p, _, _ in members]
    if len(set(names)) != len(names): print('a part twice', gn, names); ok = False
    if not 8 <= len(band) <= 11: print('band size', gn, len(band)); ok = False
    if any(p not in FUNC_ID or p in ('PROG', 'KIT') for p in names): print('unknown part', gn, names); ok = False
    used, ents = set(), []
    for part, main, inb in members:
        src = mp.get(part, part if part in OLD else None)
        old = list(D[gn][src]) if src else []
        own = list(BP.OWN.get((gn, part), []))
        seeds = (old + own) if part in OLD else (own + old + list(BP.COMMON.get(part, [])))
        if not seeds: print('no seeds', gn, part); ok = False; continue
        flash, pi = BP.variations(gn, part, seeds, 12 if main else 6, 12 if main else 6, fill_ratchet(gn) == 3)
        if part in ('KICK', 'SNARE', 'HAT', 'PERC'): note = D[gn]['KIT'][('KICK', 'SNARE', 'HAT', 'PERC').index(part)]
        else: note = BP.NOTE.get(part, 60)
        if part in BP.DRUM:
            for alt in (note, 37, 75, 76, 67, 54, 63, 60):              # (two drums of a band never on the same note)
                if alt not in used: note = alt; break
            used.add(note)
        if part == 'KICK' and src and flash[0] != BP.split(D[gn]['KICK'][0])[0]: print('kick #1 moved', gn); ok = False
        ents.append((part, main, inb, flash, pi, note))
    NEWLIB[gn] = ents
for (gn, part) in BP.OWN:
    if gn not in GENRES or part not in [e[0] for e in NEWLIB.get(gn, [])]: print('OWN of a part not in the band', gn, part); ok = False
if not ok:
    sys.exit(1)


out = ['/* SPDX-License-Identifier: GPL-3.0-only */',
       '/* The BEAT library\'s data: generated by tools/gen_beats.py (edit that, and run it again). Included by sagga_beats.c. */',
       '',
       'static const char *const GENRE_NAME[SQ_GENRES] = {%s};' % ', '.join(cstr(n) for n in SHOWN),
       '',
       '/* 0.11: the parts of every genre (its BAND first, then the parts kept to browse) and their variations. A',
       ' * variation is two offsets into POOL (its pattern and its notes; 0: none - POOL starts with an empty string). */']
pool = ['']
pool_at = {'': 0}
pool_len = [1]


def put(sv):
    if sv is None: return 0
    if sv not in pool_at:
        pool_at[sv] = pool_len[0]
        pool.append(sv)
        pool_len[0] += len(sv) + 1
    return pool_at[sv]


voff, gparts, gfirst, gband = [], [], [], []
for gn in GENRES:
    gfirst.append(len(gparts))
    gband.append(sum(1 for e in NEWLIB[gn] if e[2]))
    for part, main, inb, flash, pi, note in NEWLIB[gn]:
        first = len(voff)
        for e in flash:
            r, n = BP.split(e)
            voff.append((put(r), put(n)))
        gparts.append((FUNC_ID[part], len(flash), note, main, first, gn, part))
gfirst.append(len(gparts))
out.append('#define SQ_LIB_POOL %d' % pool_len[0])
out.append('static const char POOL[SQ_LIB_POOL] =')
line = '    "'
for sv in pool:
    piece = sv + '\\000'   # (three octal digits: a pattern of notes starts with a digit)
    if len(line) + len(piece) > 116:
        out.append(line + '"'); line = '    "'
    line += piece
out.append(line + '";')
out.append('')
out.append('static const uint32_t VOFF[%d][2] = {' % len(voff))
for i in range(0, len(voff), 6):
    out.append('    ' + ' '.join('{%d, %d},' % v for v in voff[i:i + 6]))
out.append('};')
out.append('')
out.append('/* {part (SQ_FUNC_*), variations, note (a drum: its General MIDI note; a melodic part: its register), main, first VOFF} */')
out.append('static const lib_part_t GPART[%d] = {' % len(gparts))
for fid, nv, note, main, first, gn, part in gparts:
    out.append('    {%2d, %2d, %3d, %d, %4d},  /* %s %s */' % (fid, nv, note, 1 if main else 0, first, gn, part))
out.append('};')
out.append('static const uint16_t GPART_AT[SQ_GENRES + 1] = {%s};' % ', '.join(map(str, gfirst)))
out.append('static const uint8_t GBAND[SQ_GENRES] = {%s};' % ', '.join(map(str, gband)))
out.append('')
out.append('/* per genre: the notes of a KIT (kick, snare, hat, perc; General MIDI), swing, tempo, scales, chord size, EVOLVE, the')
out.append(' * ratchet of a fill (2, or 3 where the drums roll in triplets) */')
out.append('static const genre_t GENRE[SQ_GENRES] = {')
for gn in GENRES:
    d = D[gn]
    sc = (d['SCALES'] + d['SCALES'][:1] * 3)[:3]
    out.append('    {{%d, %d, %d, %d}, %d, %d, %d, {%d, %d, %d}, %d, %d, %d, %d},  /* %s */' %
               (*d['KIT'], d['SWING'], d['BPM'][0], d['BPM'][1], *sc, d['CS'], EVO[gn][0], EVO[gn][1], fill_ratchet(gn), gn))
out.append('};')
out.append('')
out.append('/* per genre: SQ_PROGS progressions {chords, bars a chord, steps of the key (0 = the tonic), colours (SQ_HC_*)} */')
out.append('static const sq_prog_t PROGS[SQ_GENRES][SQ_PROGS] = {')
for gn in GENRES:
    ents = []
    for text, bars in P[gn]:
        toks = [tk.partition(':') for tk in text.split()]
        deg = [int(d) - 1 for d, _, _ in toks] + [0] * (8 - len(toks))
        col = [COLORS[c] for _, _, c in toks] + [0] * (8 - len(toks))
        ents.append('{%d, %d, {%s}, {%s}}' % (len(toks), bars, ', '.join(map(str, deg)), ', '.join(map(str, col))))
    out.append('    { %s },  /* %s */' % (', '.join(ents), gn))
out.append('};')
open(sys.argv[1], 'w').write('\n'.join(out) + '\n')

# 0.10: VIAGGIO's set genres, one per library genre, in the library's order (SET_GENRE[i].genre == i)
sg = ['/* SPDX-License-Identifier: GPL-3.0-only */',
      '/* VIAGGIO\'s set genres: GENERATED by tools/gen_beats.py (edit that, and run it again). One entry per genre of the BEAT',
      ' * library, in its order, so SET_GENRE[i].genre == i == SQ_GENRE_*. The ladder: the energy 0..100 at which a role enters',
      ' * (KICK SNARE HAT PERC BASS CHORD ARP). Include after sagga_seq_core.h (sq_set_genre_t) and sagga_beats.h (SQ_GENRES). */',
      'static const sq_set_genre_t SET_GENRE[SQ_SET_GENRES] = {']
for i, gn in enumerate(GENRES):
    s = SETG[gn]
    g2 = GENRES.index(s['G2'])
    sg.append('    { %-13s %2du /* %-12s */, %2du /* %-12s */, {%s}, %du, %du, %du },' %
              (cstr(SHOWN[i]) + ',', i, ENUM[i], g2, ENUM[g2],
               ', '.join('%3du' % x for x in s['LADDER']), D[gn]['SWING'], s['HALF'], s['AFRO']))
sg.append('};')
sg_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(sys.argv[1]), 'sagga_setgenre_data.h')
open(sg_path, 'w').write('\n'.join(sg) + '\n')
# 0.11: the Pi's patterns: the variations after the FM-1's (VAR 13 on for a main part, 7 on for the others), one file
# a genre: PART <tab> pattern <tab> notes ('-' for a drum); the bridge serves them (tools/sagga_grid_bridge.py)
os.makedirs(PI_DIR, exist_ok=True)
npi = 0
for gn in GENRES:
    lines = ['# SAGGA SEQ 0.11 pattern library, %s: PART, the pattern, its notes (- for a drum). Written by tools/gen_beats.py;' % gn,
             '# the patterns you save from the FM-1 (SEQ + SAVE) are added at the end. One per line.']
    for part, main, inb, flash, pi, note in NEWLIB[gn]:
        for e in pi:
            r, n = BP.split(e)
            lines.append('%s\t%s\t%s' % (part, r, n or '-'))
            npi += 1
    open(os.path.join(PI_DIR, '%s.txt' % gn), 'w').write('\n'.join(lines) + '\n')
print('ok: %d genres, %d parts, %d variations in flash (%d bytes of patterns), %d on the Pi, %d set genres' % (
    len(GENRES), len(gparts), len(voff), pool_len[0], npi, len(GENRES)))
