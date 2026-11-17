/* SPDX-License-Identifier: GPL-3.0-only */
#ifndef SAGGA_BEATS_H
#define SAGGA_BEATS_H

#include "sagga_seq_core.h"

/* The BEAT library: ready-made patterns by genre and by function, and chord progressions in the key. A pattern is a
 * string with one character per 16th: '.' rest, 'x' hit, 'X' accent, 'o' soft, 'g' ghost, '2' '3' '4' a hit that
 * repeats 2-4 times, 0.11 '-' the note before held through this step; 16, 32 or 64 steps (one, two or four bars).
 * Pitched functions carry a second string with one
 * character per step: a semitone above the root (hex digit, 0-f), or for CHORD the kind of chord (m minor, M major,
 * n minor 7th, N major 7th, 7 dominant, s sus4, 5 power chord). The data is tools/gen_beats.py's (sagga_beats_data.h;
 * the same script writes VIAGGIO's set genres, sagga_setgenre_data.h, one per genre in this order). */
#define SQ_GENRES 25u                                           /* 0.16: 25 with the merengue */
#define SQ_FUNCS  26u        /* KICK SNARE HAT PERC BASS CHORD ARP from the patterns, PROG the tonic chord, KIT the drums of
                              * the band; 0.11: the parts of the bands (CLAP .. VOX) */
#define SQ_BEAT_VARS 12u     /* 0.11: the variations of a part in flash, at most (a main part 12, the others 6); the Pi has more */
#define SQ_PROGS 6u          /* progressions per genre */
#define SQ_BAND_MAX 11u      /* 0.11: the parts of a genre's band, at most */
#define SQ_PARTS_MAX 14u     /* 0.11: the parts a genre has (its band and the parts kept to browse), at most */

/* the genres, in the order of the library (and of the grid's BEAT view: two pages of 12) */
enum { SQ_GENRE_TECHNO = 0, SQ_GENRE_HARDTECHNO, SQ_GENRE_DUBTECHNO, SQ_GENRE_HOUSE, SQ_GENRE_UKG, SQ_GENRE_UKFUNKY,
       SQ_GENRE_GRIME, SQ_GENRE_DUBSTEP, SQ_GENRE_JUNGLE, SQ_GENRE_BASSLINE, SQ_GENRE_REGGAETON, SQ_GENRE_BATIDA,
       SQ_GENRE_GQOM, SQ_GENRE_EXPERIMENTAL, SQ_GENRE_ELECTRO, SQ_GENRE_DNB, SQ_GENRE_AFROHOUSE, SQ_GENRE_AMAPIANO,
       SQ_GENRE_FOOTWORK, SQ_GENRE_TRANCE, SQ_GENRE_UKDRILL, SQ_GENRE_HARDCORE, SQ_GENRE_PHONK, SQ_GENRE_BAILEFUNK,
       SQ_GENRE_MERENGUE };                                       /* 0.16 */
enum { SQ_FUNC_KICK = 0, SQ_FUNC_SNARE, SQ_FUNC_HAT, SQ_FUNC_PERC, SQ_FUNC_BASS, SQ_FUNC_CHORD, SQ_FUNC_ARP, SQ_FUNC_PROG,
       SQ_FUNC_KIT,
       /* 0.11: the parts of the bands, in the order of the roles SQ_ROLE_CLAP .. SQ_ROLE_VOX */
       SQ_FUNC_CLAP, SQ_FUNC_OHAT, SQ_FUNC_RIDE, SQ_FUNC_SHAKER, SQ_FUNC_CONGA, SQ_FUNC_TOM, SQ_FUNC_RIM, SQ_FUNC_CRASH,
       SQ_FUNC_COWBELL, SQ_FUNC_RUMBLE, SQ_FUNC_SUB, SQ_FUNC_LOGDRUM, SQ_FUNC_STAB, SQ_FUNC_PAD, SQ_FUNC_PIANO, SQ_FUNC_LEAD,
       SQ_FUNC_VOX };
enum { SQ_KIND_DRUM = 0, SQ_KIND_MONO, SQ_KIND_CHORD };   /* 0.11: what a part's notes are */
uint8_t sq_func_kind(uint8_t func);        /* a drum (one note), a line (a note above the root), chords */
uint8_t sq_func_family(uint8_t func);      /* the 0.10 function it belongs to: SQ_FUNC_KICK .. SQ_FUNC_ARP */
uint8_t sq_func_role(uint8_t func);        /* the track's role for it (SQ_ROLE_*); PROG: CHORD, KIT: KICK */
uint8_t sq_role_func(uint8_t role);        /* the part of a role (255: NONE) */
/* 0.11: the parts a genre has: its BAND first (sq_genre_band of them, in the band's order), then the 0.10 parts it
 * keeps to browse; PROG and KIT are not in the list. Returns how many (at most SQ_PARTS_MAX). */
uint8_t sq_genre_parts(uint8_t genre, uint8_t *funcs);
uint8_t sq_genre_band(uint8_t genre);
uint8_t sq_genre_has(uint8_t genre, uint8_t func);          /* 1 if the genre has the part (PROG, KIT: always) */
/* the part of the genre that stands for `func` when the genre has no such part: the same, else the first of its
 * family (a SNARE for a CLAP, a PAD for a CHORD ...), else 255 */
uint8_t sq_genre_part_for(uint8_t genre, uint8_t func);
/* the note a drum part plays in the genre (General MIDI; the KIT's), the register of a melodic part */
uint8_t sq_part_note(uint8_t genre, uint8_t func);
uint8_t sq_part_main(uint8_t genre, uint8_t func);          /* 1: a main part (12 variations) */
uint8_t sq_part_root(uint8_t func, uint8_t note);           /* the root a part's pattern is loaded on, from the track's note */
char sq_chord_kind_of(const uint8_t *notes);                /* the library's letter for a step's chord (m M n N 7 s 5) */

const char *sq_genre_name(uint8_t genre);
const char *sq_func_name(uint8_t func);
/* how many variations a (genre, function) has; KIT as many as the kick, PROG one per progression */
uint8_t sq_beat_variants(uint8_t genre, uint8_t func);
/* The pattern as written, or 0 if there is none (and the chord / offset string in *notes, may be 0). PROG and KIT:
 * the CHORD / KICK pattern. */
const char *sq_beat_text(uint8_t genre, uint8_t func, uint8_t var, const char **notes);
/* Writes the pattern into row[0..n-1] (the steps are replaced) and returns n (16, 32 or 64: the pattern's own length),
 * 0 if there is no such pattern. `note` is the track's own note: what a drum plays, or the root of BASS / CHORD / ARP
 * (moved into a sensible range). */
uint8_t sq_beat_load(sq_step_t *row, uint8_t genre, uint8_t func, uint8_t var, uint8_t note);
/* 0.10: the same, `len` steps long (16, 32 or 64; 0 = the pattern's own length; anything else 16). A pattern as long
 * as `len` goes in as written, a longer one its first bars; a shorter one is tiled from the library: the bars before
 * the last repeat the variant's own (a two-bar variant gives two), the last bar is the NEXT variant's (wrapping round),
 * which for BASS / CHORD / ARP brings its notes as a turnaround, and for the drums gets the genre's fill: its final two
 * 16ths roll (a ratchet of 2, or 3 where the genre rolls in triplets) or gain a hit. Deterministic. */
uint8_t sq_beat_load_len(sq_step_t *row, uint8_t genre, uint8_t func, uint8_t var, uint8_t note, uint8_t len);
/* 0.9: the same from a pattern's text (at most SQ_STEPS characters; `notes` 0 for a drum): the AFRO / LATIN family */
/* 0.24: the variation as the pattern of a track `len` steps long (1..64): the track's length is the player's, the
 * pattern is made for it. A track of 64 gets 64 steps, one of 32..63 gets 32, a shorter one 16: the variation as it is
 * written when it is written that long (many are, over two or four bars: the answers, the fills), or its first bars
 * when it is longer; one written shorter is given as it is (`phrase` 0: the track repeats it - COPY) or in the long
 * form of 0.10 (`phrase` 1: the bars after the first are the next variation's, the genre's fill in the last). Returns
 * the steps of the pattern, 16, 32 or 64 (0: none); what the track has more is the pattern again (sq_row_made) */
uint8_t sq_beat_load_for(sq_step_t *row, uint8_t genre, uint8_t func, uint8_t var, uint8_t note, uint8_t len, uint8_t phrase);
uint8_t sq_len_made(uint8_t len);        /* 64, 32 or 16: the steps a pattern is made in for a track of len steps */
uint8_t sq_beat_load_text(sq_step_t *row, const char *text, const char *notes, uint8_t func, uint8_t note);
/* the four parts of a KIT (0 kick, 1 snare, 2 hat, 3 perc): their function and the note they play */
void sq_beat_kit_part(uint8_t genre, uint8_t part, uint8_t *func, uint8_t *note);

/* the genre's feel: swing (50 = straight), tempo range, the scales it likes (for DICE ALL), chords of 3 or 4 notes */
uint8_t sq_genre_swing(uint8_t genre);
/* 0.16: the feel a part of the genre comes with: its swing (the genre's, or its own where a GROOVE template carries the
 * shuffle instead), its GROOVE template and how much of it. The hats, shakers and percussion carry the groove; the kick
 * stays the anchor; the bass and the chords keep the genre's swing (out of range: the genre's swing, no groove). */
void sq_genre_groove(uint8_t genre, uint8_t func, uint8_t *swing, uint8_t *groove, uint8_t *amt);
void sq_genre_bpm(uint8_t genre, uint16_t *lo, uint16_t *hi);
uint8_t sq_genre_scale(uint8_t genre, uint8_t i);          /* i = 0..2 */
uint8_t sq_genre_chord_size(uint8_t genre);
uint8_t sq_genre_hrhythm(uint8_t genre);                   /* 0.11: when its chords change (SQ_HR_*: house pushes them) */
void sq_genre_evolve(uint8_t genre, uint8_t *rhy, uint8_t *note);   /* EVOLVE: % of the amount for rhythm / notes */

/* ---- 0.8 progressions: each genre has SQ_PROGS of its own. A chord is a step of the key (0 = the tonic) and a colour
 * (SQ_HC_*: 7, 9, sus4, sus2, 6); `bars` is how long each chord lasts unless the HARMONY says otherwise. */
typedef struct { uint8_t n, bars; int8_t deg[8]; uint8_t col[8]; } sq_prog_t;
const sq_prog_t *sq_prog_get(uint8_t genre, uint8_t i);
/* "i7-VI9-III-VII" in the key's scale (the names show minor / major chords as the key makes them) */
void sq_prog_name(uint8_t genre, uint8_t i, uint8_t scale, char *out, uint32_t cap);
/* the chord playing after `bar` bars of the transport: chord index, its step and colour; bars_override 0 = the
 * progression's own length per chord */
uint8_t sq_prog_at(uint8_t genre, uint8_t i, uint32_t bar, uint8_t bars_override, int8_t *deg, uint8_t *col);
/* the tonic chord of the key: `size` notes (3 or 4), close around `center`; returns how many */
uint8_t sq_tonic_chord(uint8_t root, uint8_t scale, uint8_t center, uint8_t size, uint8_t *out);
/* PROG: the tonic chord on the rhythm of the genre's first chord part, variation `var` (16, 32 or 64 steps; 0.11: its
 * held notes held); the HARMONY moves it */
uint8_t sq_beat_chords(sq_step_t *row, uint8_t genre, uint8_t var, uint8_t root, uint8_t scale, uint8_t center);
/* the part a track gets when BEAT goes onto several: a drum by its General MIDI note (35-36 kick, 37-40 snare / clap,
 * 42 44 46 hats, else perc), any other by its register (under C3 bass, C3-B3 chords, from C4 arp). Only the seven
 * 0.10 functions (and PROG): what a note says of a part is no more than its family. */
uint8_t sq_beat_role(uint8_t drum, uint8_t note);

#endif
