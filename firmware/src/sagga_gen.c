/* SPDX-License-Identifier: GPL-3.0-only */
/*
 * SAGGA GEN - the generators. Included by dinghy.c after the editing helpers.
 *
 *   the pattern tools     on the selected track, or on several (the SCOPE: this track, its bank, all, the drums,
 *                         the melodic ones, the ones you chose); COOK and RANDOM change, besides the rhythm, the notes (in
 *                         the key), the CC lanes and the LFOs aimed at the track, as the TARGETS say
 *   the LIVE LAYER (0.8)  per track, while it plays, never written unless you WRITE it: EUCLID (pulses, rotation),
 *                         TURING, CELL, ACCENT, DENSITY. What the steps show is what you hear.
 *   the HARMONY (0.8)     a progression of the genre plays along; the FOLLOW tracks move to its chords
 *   BEAT, PROG, KIT       the library; PROG writes the tonic chord on the genre's chord rhythm and starts the HARMONY
 *   the dice              a new take of the sequence, the CC sound, the LFOs, the groove, or all of it, heard at once:
 *                         OCT+ keeps it, OCT- puts back what was there; 0.8: the last 16 rolls stay, ALG goes through them
 *   EVOLVE                every few bars the patterns change by themselves around what they were (the seed), by the
 *                         rules of voice leading (0.8); FREEZE keeps what you hear, REVERT goes back to the seed
 *   TEMP                  changes made while it is held go away when it is let go (the grid's FX view)
 *   SONG                  scenes in a row, each for some bars
 *   tap tempo
 */

enum { TOOL_CLEAR = 0, TOOL_REV, TOOL_SHL, TOOL_SHR, TOOL_RAND, TOOL_EUC, TOOL_WRITE, TOOL_UNDO,
       TOOL_COOK, TOOL_BEAT, TOOL_PROG, TOOL_COPY, TOOL_PASTE, TOOL_DOUBLE, TOOL_INVERT, TOOL_HUMAN, TOOL_COUNT };
static const char *const TOOL_NAME[TOOL_COUNT] = {"CLEAR", "REVERSE", "SHIFT LEFT", "SHIFT RIGHT", "RANDOM", "EUCLID LIVE",
                                                  "WRITE LIVE", "UNDO", "COOK", "BEAT", "PROG", "COPY", "PASTE", "DOUBLE",
                                                  "INVERT", "HUMANIZE"};
static const char *const SCOPE_NAME[SQ_SCOPES] = {"THIS TRACK", "BANK", "ALL", "DRUMS", "MELODIC", "CUSTOM"};
#define GEN_TARGET_SETS 6u
static const uint8_t TARGET_SET[GEN_TARGET_SETS] = {SQ_GT_RHYTHM, SQ_GT_RHYTHM | SQ_GT_NOTES, SQ_GT_RHYTHM | SQ_GT_CC,
                                                    SQ_GT_RHYTHM | SQ_GT_NOTES | SQ_GT_CC, SQ_GT_RHYTHM | SQ_GT_CC | SQ_GT_LFO,
                                                    SQ_GT_RHYTHM | SQ_GT_NOTES | SQ_GT_CC | SQ_GT_LFO};
static const char *const TARGET_NAME[GEN_TARGET_SETS] = {"RHYTHM", "+NOTES", "+CC", "+NOTES+CC", "+CC+LFO", "ALL"};
static const uint8_t EVO_BARS[SQ_EVO_EVERY] = {1u, 2u, 4u, 8u, 16u};
enum { DICE_SEQ = 1, DICE_CC, DICE_LFO, DICE_GROOVE, DICE_ALL, DICE_RANDOM };   /* 0.27: RANDOM is a roll of the dice too */
static const char *const DICE_NAME[7] = {"", "DICE SEQ", "DICE CC", "DICE LFO", "DICE GROOVE", "DICE ALL", "RANDOM"};
static const char *const ALGO_NAME[SQ_ALGOS] = {"OFF", "TURING", "CELL", "ACCENT", "DENSITY"};

/* the settings live in the project (sq_gen_t): these names are the ones the panel and the grid use */
#define tool_density (project.gen.density)
#define tool_heat    (project.gen.heat)
#define beat_genre   (project.gen.genre)
#define beat_func    (project.gen.func)
#define beat_var     (project.gen.var)

static uint8_t gen_target_index(void)
{
    uint32_t i;
    for (i = 0; i < GEN_TARGET_SETS; i++) if (TARGET_SET[i] == project.gen.targets) return (uint8_t)i;
    return 0u;
}

static uint8_t track_drum(uint32_t t) { return (project.track[t].flags & SQ_TF_DRUM) ? 1u : 0u; }
#define TRACK_MODES 5u
static uint8_t track_mode(uint32_t t) { return (project.track[t].flags & SQ_TF_BREAK) ? 4u : (project.track[t].flags & SQ_TF_TAPE) ? 3u : track_drum(t) ? 2u : track_in_key(t) ? 1u : 0u; }   /* FREE, KEY, DRUM, TAPE, BREAK (0.12) */
static void track_realign(uint32_t t);               /* (dinghy.c) */
static void track_cfg_back(uint32_t t, const sq_track_cfg_t *was, uint8_t pat);
static uint8_t track_break(uint32_t t);              /* (sagga_break.c, 0.12) */
static void brk_say(const char *what, uint32_t t);
static uint8_t brk_slices(uint32_t t);
static uint8_t brk_cook_chop(uint32_t t, uint8_t random);   /* ... the chop COOK goes to: the genre's next (random: one of them) */
static void brk_cook_say(uint32_t t);
static void brk_dice_track(uint32_t t);
static void set_track_mode(uint32_t t, uint8_t m)
{
    uint8_t was_tape, f;
    if (t >= SQ_TRACKS) return;
    was_tape = (uint8_t)((project.track[t].flags & SQ_TF_TAPE) != 0u);
    f = (uint8_t)(project.track[t].flags & ~(SQ_TF_SCALE | SQ_TF_DRUM | SQ_TF_TAPE | SQ_TF_BREAK));
    if (m == 1u) f |= SQ_TF_SCALE;
    else if (m == 2u) f = (uint8_t)((f | SQ_TF_DRUM) & ~SQ_TF_FOLLOW);   /* (a drum never follows the harmony) */
    else if (m == 3u) { f = (uint8_t)((f | SQ_TF_TAPE) & ~SQ_TF_FOLLOW); track_all_off(t); }   /* 0.11 TAPE: the steps rest */
    else if (m == 4u) f = (uint8_t)((f | SQ_TF_BREAK) & ~SQ_TF_FOLLOW);   /* 0.12 BREAK: slices, never the key */
    project.track[t].flags = f;
    if (was_tape && m != 3u && playing) track_realign(t);   /* 0.11: off the tape, the steps where the bar says (the explorer) */
    ui_dirty = grid_dirty = 1u;
}
static const char *track_mode_name(uint32_t t) { static const char *const N[TRACK_MODES] = {"FREE", "IN KEY", "DRUM", "TAPE", "BREAK"}; return N[track_mode(t)]; }

static uint16_t bank_mask(void) { return (uint16_t)((0xFFu << (selected_track & 8u)) & SQ_TRACK_BITS); }   /* (0.28: 1-8 or 9-12) */
static uint16_t gen_custom_mask(void) { return project.gen.custom ? project.gen.custom : (uint16_t)(1u << selected_track); }
static uint16_t scope_mask_of(uint8_t scope)
{
    uint32_t t;
    uint16_t m = 0u;
    switch (scope) {
    case SQ_SCOPE_BANK: return bank_mask();
    case SQ_SCOPE_ALL:  return (uint16_t)SQ_TRACK_BITS;
    case SQ_SCOPE_DRUM: for (t = 0; t < SQ_TRACKS; t++) if (track_drum(t)) m |= (uint16_t)(1u << t); break;
    case SQ_SCOPE_MELO: for (t = 0; t < SQ_TRACKS; t++) if (!track_drum(t)) m |= (uint16_t)(1u << t); break;
    case SQ_SCOPE_CUSTOM: return gen_custom_mask();
    default: break;
    }
    return m ? m : (uint16_t)(1u << selected_track);   /* (no drum track, say: the selected one) */
}
static uint16_t gen_mask(void) { return scope_mask_of(project.gen.scope); }
static void gen_custom_toggle(uint8_t t)
{
    uint16_t m = gen_custom_mask();
    if (t >= SQ_TRACKS) return;
    m ^= (uint16_t)(1u << t);
    if (!m) m = (uint16_t)(1u << t);
    project.gen.custom = m;
    project.gen.scope = SQ_SCOPE_CUSTOM;
    status_num((m & (1u << t)) ? "SCOPE + TRACK " : "SCOPE - TRACK ", (uint32_t)t + 1u);
    ui_dirty = grid_dirty = 1u;
}
static uint32_t popcount16(uint16_t m) { uint32_t n = 0; while (m) { n += m & 1u; m >>= 1; } return n; }

/* the CC lanes the generators may touch: those with a CC number and a base value (the synth's "home" for that CC, so
 * a generated lock is put back after its step). None: lane 1 (CC 74, the filter) with the base 64. Lanes without a
 * base, like expression or volume, are never moved by chance. */
static uint8_t gen_lanes(uint32_t t)
{
    sq_track_cfg_t *c = &project.track[t];
    uint8_t m = 0u, l;
    for (l = 0; l < SQ_LANES; l++) if (c->lane_cc[l] != SQ_LANE_NONE && c->lane_base[l] != SQ_LANE_NONE) m |= (uint8_t)(1u << l);
    if (!m && c->lane_cc[0] != SQ_LANE_NONE) { c->lane_base[0] = 64u; m = 1u; }
    return m;
}
/* the key the generators write in: the project's when it has one, else the pen note's minor (pentatonic for melodies) */
static uint8_t gen_root(uint32_t t) { return project.key_scale != SQ_SC_CHROMATIC ? project.key_root : (uint8_t)(PEN(t) % 12u); }
static uint8_t gen_scale(void) { return project.key_scale; }
/* a melodic part's root note: the key's root in the octave of the pen note */
static uint8_t gen_root_note(uint32_t t)
{
    uint8_t note = PEN(t);
    if (project.key_scale != SQ_SC_CHROMATIC) {
        note = (uint8_t)((note / 12u) * 12u + project.key_root);
        if (note > 127u) note = (uint8_t)(note - 12u);
    }
    return note;
}
/* 0.27: the note a NEW track starts from (a drum part's General MIDI note, the register of a melodic part). With no key
 * (the scale CHROMA, as a new project is) a melodic part is rooted on its track's note: that note goes to the project's
 * root (HOME 3 K2: C at first), the nearest one, in the part's register, so all the parts of a band are in one key.
 * Until 0.26 the arpeggio started from G4 and played a fifth above the rest. */
static uint8_t start_note(uint8_t func, uint8_t note)
{
    int32_t n;
    if (sq_func_kind(func) == SQ_KIND_DRUM || project.key_scale != SQ_SC_CHROMATIC) return note;
    n = (int32_t)(note / 12u) * 12 + (int32_t)(project.key_root % 12u);
    if (n - (int32_t)note > 6) n -= 12;
    else if ((int32_t)note - n > 6) n += 12;
    return sq_part_root(func, (uint8_t)clamp_i32(n, 0, 127));   /* (in the part's register, where the makers put its root) */
}
static uint32_t grand(uint32_t n) { return n ? sq_rng_next(&sq_rng_state) % n : 0u; }
/* 0.10: the role of a track for the library and COOK: the one the player set (HOME 4 K2), else what its notes say */
static uint8_t gen_role(uint32_t t)
{
    if (project.track[t].role) return project.track[t].role;
    return sq_func_role(sq_beat_role(track_drum(t), PEN(t)));       /* (0.11: a chord register is a CHORD) */
}
static uint8_t genre_feel(void) { return project.gen.genre_mode != SQ_GM_FREE; }   /* 0.10: the generators mind the genre */
/* 0.23 THEORY: the style the engines make a part of `genre` in now (every genre has one; SOURCE FREE, or GENRE FREE: the
 * style of no genre); 255: the patterns come from the library - the SOURCE says so (SEQ 8 K1) */
static uint8_t th_style_now(uint8_t genre)
{
    if (project.th.src != SQ_SRC_THEORY && project.th.src != SQ_SRC_FREE) return 255u;
    if (project.th.src == SQ_SRC_FREE || project.gen.genre_mode == SQ_GM_FREE) return SQ_TH_FREE;
    return sq_th_style(genre);
}
static uint16_t genre_reload_pend;                     /* 0.10 GENRE LIVE: tracks to reload from the library at the bar */
/* 0.24: THE LENGTH IS THE TRACK'S. A pattern is MADE (the library, the engines, the Pi) for the track it goes to:
 * in 64 steps for a track of 64, in 32 for one of 32 .. 63, in 16 for a shorter one (made_len). What the track has more
 * than that is the pattern again (its copies), what it has less is kept after the loop (made_fit: sq_row_made). Nobody
 * who brings a pattern changes the track's length any more (but the bembe', twelve steps: beat_cfg_apply).
 * lib_phrase: a library pattern of one bar in a longer track comes as a PHRASE (SAVE 2 K4, or a DICE: dice_phrase) */
static uint8_t dice_phrase;
/* 0.25 THE METRE: the library and the engines think in bars of sixteen steps, in four quarters. In another metre they
 * still do - a part is made in one, two or four SIXTEENS (made_len: as many as the track has bars of the metre, the
 * same 64 / 32 / 16 in 4/4) and then RE-BARRED (made_rebar: sq_rebar - every beat of the metre's bar takes a beat of
 * the sixteen: the first its first, the last its last, the backbeat between). A pattern that is not made of sixteens
 * (the bembe', a pattern of the Pi's) is as it is. */
static uint8_t made_len(uint32_t t)
{
    uint8_t bars = (uint8_t)(project.track[t].length / bar_st());
    return (uint8_t)(bars >= 4u ? 64u : bars >= 2u ? 32u : 16u);
}
static uint8_t lib_phrase(void) { return (uint8_t)(dice_phrase || project.gen.lib_len == SQ_LL_PHRASE); }
static uint8_t made_rebar(sq_step_t *row, uint8_t n)     /* a row of n steps made in sixteens: in the metre's bars -> its steps then */
{
    if (metre_44() || !n || (n & 15u)) return n;
    sq_rebar(row, (uint8_t)(n / 16u), bar_st(), bar_bt());
    return sq_rebar_len(n, bar_st(), bar_bt());
}
static void made_fit_x(uint32_t t, uint8_t pat, uint8_t n, uint8_t rebar)
{
    uint8_t made = made_len(t);
    if (t >= SQ_TRACKS || pat >= SQ_PATTERNS || !n) return;
    if (n > made && rebar != 2u) n = made;
    if (rebar == 1u) n = made_rebar(project.step[t][pat], n);
    sq_row_made(project.step[t][pat], n, project.track[t].length);
    gh_st[t].pat = 255u;                                  /* (what the copies were made from is not known any more) */
}
/* (0.26: a pattern the engines of 0.26 made is in the metre's bars already - th_make: so many bars of it - and stays so) */
static uint8_t made_in_bar(uint32_t t, uint8_t pat)
{
    return (uint8_t)(t < SQ_TRACKS && pat < SQ_PATTERNS && (project.th.pat[t][pat].style & 31u) && (project.th.pat[t][pat].style & SQ_THP_V26));
}
static void made_fit(uint32_t t, uint8_t pat, uint8_t n) { made_fit_x(t, pat, n, made_in_bar(t, pat) ? 2u : 1u); }
static void made_fit_asis(uint32_t t, uint8_t pat, uint8_t n) { made_fit_x(t, pat, n, 0u); }   /* (the Pi's: as it was written) */

/* ---- the settings (the panel and the grid share them) */
static void gen_scope_set(uint8_t scope)
{
    char *p = msg_buf;
    project.gen.scope = scope < SQ_SCOPES ? scope : (uint8_t)SQ_SCOPE_THIS;
    p = put_s(p, "SCOPE "); p = put_s(p, SCOPE_NAME[project.gen.scope]);
    if (project.gen.scope != SQ_SCOPE_THIS) { p = put_s(p, " ("); p = put_u(p, popcount16(gen_mask())); p = put_s(p, ")"); }
    finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}
static void gen_targets_set(uint8_t i)
{
    char *p = msg_buf;
    if (i >= GEN_TARGET_SETS) i = 0u;
    project.gen.targets = TARGET_SET[i];
    p = put_s(p, "COOK/RANDOM/EVOLVE: "); p = put_s(p, TARGET_NAME[i]); finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}
static void tool_bar_tick(void);
static void beat_func_fit(void);
/* 0.11: the HARMONY has a genre of its own. It follows the machine's when something is DONE in that genre - a pattern
 * loaded (BEAT, KIT, BAND, PROG), GENRE LIVE reloading the tracks, VIAGGIO changing the set's genre - never while the
 * knobs only browse the library; and never while HARM LOCK is on (the player changes it by hand: SEQ 4, SEL + K2). */
static void harm_follow_genre(uint8_t g)
{
    if (g >= SQ_GENRES || project.gen.harm_lock || project.gen.harm_free || g == project.gen.harm_genre) return;   /* (0.16 FREE: nobody's) */
    project.gen.harm_genre = g;
    ui_dirty = grid_dirty = 1u;
}
/* 0.10: the one genre of the machine changed: the library's, VIAGGIO's; GENRE LIVE reloads the tracks that came from
 * the library (at the next bar line, at once when stopped). 0.11 `act`: the change is an act (VIAGGIO, a phrase coming
 * back) and the harmony follows it; the knobs pass 0: they browse, and the harmony follows only in GENRE LIVE, where a
 * change of genre reloads the tracks. */
static void gen_genre_changed(uint8_t g, uint8_t act)
{
    uint32_t t;
    if (g >= SQ_GENRES) return;
    if (g != beat_genre) beat_var = 0u;
    beat_genre = g;
    beat_func_fit();                                      /* 0.11: the part chosen, in the new genre */
    project.viaggio.set_genre = g;
    if (project.gen.genre_mode == SQ_GM_LIVE) {
        for (t = 0; t < SQ_TRACKS; t++) if (project.track[t].src_func != 255u) genre_reload_pend |= (uint16_t)(1u << t);
        act = 1u;
    }
    if (act) harm_follow_genre(g);
    if (genre_reload_pend && !playing) tool_bar_tick();   /* stopped: at once */
    ui_dirty = grid_dirty = 1u;
}
static void gen_genre_set(uint8_t g)
{
    char *p = msg_buf;
    uint16_t lo, hi;
    if (g >= SQ_GENRES) return;
    gen_genre_changed(g, 0u);
    sq_genre_bpm(g, &lo, &hi);
    p = put_s(p, "GENRE "); p = put_s(p, sq_genre_name(g)); p = put_s(p, " "); p = put_u(p, lo); p = put_s(p, "-"); p = put_u(p, hi);
    if (project.gen.genre_mode == SQ_GM_LIVE && genre_reload_pend) p = put_s(p, playing ? " (LIVE: AT THE BAR)" : " (LIVE)");
    finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}
static void genre_mode_note(void)
{
    if (project.th.src == SQ_SRC_FREE)                  /* 0.23: the engines are free of the genre whatever its mode */
        status_msg(project.gen.genre_mode == SQ_GM_FREE ? "GENRE FREE (THE SOURCE TOO: PARTS OF NO GENRE)" :
                   project.gen.genre_mode == SQ_GM_LIVE ? "GENRE LIVE (SOURCE FREE: ITS PARTS STAY)" : "GENRE ON (SOURCE FREE: PARTS OF NO GENRE)");
    else if (project.th.src == SQ_SRC_THEORY)           /* ... what the mode means to them */
        status_msg(project.gen.genre_mode == SQ_GM_FREE ? "GENRE FREE: THEORY MAKES PARTS OF NO GENRE" :
                   project.gen.genre_mode == SQ_GM_LIVE ? "GENRE LIVE: A CHANGE MAKES THE PARTS AGAIN" : "GENRE ON: THEORY MAKES THE GENRE'S PARTS");
    else
    status_msg(project.gen.genre_mode == SQ_GM_FREE ? "GENRE FREE: THE GENERATORS IGNORE IT" :
               project.gen.genre_mode == SQ_GM_LIVE ? "GENRE LIVE: A CHANGE RELOADS THE LIBRARY TRACKS" : "GENRE ON: ITS FEEL IN COOK, DICE, EVOLVE");
}
static void gen_func_set(uint8_t f)
{
    char *p = msg_buf;
    if (f >= SQ_FUNCS) return;
    if (f != beat_func) beat_var = 0u;
    beat_func = f;
    p = put_s(p, "BEAT "); p = put_s(p, sq_func_name(f));
    if (f != SQ_FUNC_PROG && th_style_now(beat_genre) != 255u) p = put_s(p, " (THEORY)");   /* 0.23: made, any number of them */
    else if (f != SQ_FUNC_PROG && f != SQ_FUNC_KIT) { p = put_s(p, " ("); p = put_u(p, sq_beat_variants(beat_genre, f)); p = put_s(p, ")"); }
    finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}
/* 0.11: what the instrument knob (SEQ + SELECT) goes through: the genre's parts (its band first), PROG, KIT */
static uint8_t beat_list(uint8_t *out)
{
    uint8_t n = th_style_now(beat_genre) == SQ_TH_FREE ? sq_th_band(SQ_TH_FREE, out) : sq_genre_parts(beat_genre, out);   /* (0.23: no genre: FREE's band) */
    out[n++] = SQ_FUNC_PROG;
    out[n++] = SQ_FUNC_KIT;
    return n;
}
static uint8_t beat_list_pos(void)
{
    uint8_t l[SQ_PARTS_MAX + 2u], n = beat_list(l), i;
    for (i = 0; i < n; i++) if (l[i] == beat_func) return i;
    return 0u;
}
static void beat_func_turn(int32_t d)
{
    uint8_t l[SQ_PARTS_MAX + 2u], n = beat_list(l);
    gen_func_set(l[clamp_i32((int32_t)beat_list_pos() + d, 0, (int32_t)n - 1)]);
}
/* the genre changed: the part chosen stays if the genre has it, else its family's */
static void beat_func_fit(void)
{
    uint8_t f = beat_func == SQ_FUNC_PROG || beat_func == SQ_FUNC_KIT ? beat_func : sq_genre_part_for(beat_genre, beat_func);
    if (f == 255u) { uint8_t l[SQ_PARTS_MAX + 2u]; beat_list(l); f = l[0]; }
    if (f != beat_func) { beat_func = f; beat_var = 0u; }
}

/* ---- undo: up to 16 pattern rows, one level (UNDO again = redo) */
/* 0.10: undo is a ring of U_ROWS pattern rows. Every edit (undo_begin, then undo_add for each row it touches) is a
 * transaction; UNDO swaps the newest one back (and again the one before, ...); REDO walks forward. A new edit after an
 * UNDO drops what could be redone. When the ring is full the oldest edit is forgotten. */
static void undo_refresh(void)
{
    uint32_t i;
    undo_valid = 0u;
    for (i = 0; i < U_ROWS; i++) if (undo_txn[i] && undo_txn[i] <= u_top) { undo_valid = 1u; break; }
}

static void undo_begin(void)
{
    uint32_t i;
    for (i = 0; i < U_ROWS; i++) if (undo_txn[i] > u_top) undo_txn[i] = 0u;   /* no more redo */
    if (++u_seq == 0u) u_seq = 1u;
    u_cur = u_seq;
}

static const sq_thpat_t *undo_th_src;                 /* 0.23: the record that goes with a row that is not the project's (a dice's snapshot) */
static void undo_add_row(uint8_t t, uint8_t pat, const sq_step_t *row, uint8_t len, uint8_t start)
{
    uint32_t i, slot = U_ROWS;
    uint16_t oldest = 0u;
    if (!u_cur) undo_begin();
    for (i = 0; i < U_ROWS; i++) if (undo_txn[i] == u_cur && undo_track[i] == t && undo_pat[i] == pat) return;
    for (i = 0; i < U_ROWS; i++) if (!undo_txn[i]) { slot = i; break; }
    if (slot == U_ROWS) {                                /* full: the oldest edit goes, whole */
        for (i = 0; i < U_ROWS; i++) if (undo_txn[i] && (!oldest || (uint16_t)(oldest - undo_txn[i]) < 0x8000u)) oldest = undo_txn[i];
        if (!oldest || oldest == u_cur) return;
        for (i = 0; i < U_ROWS; i++) if (undo_txn[i] == oldest) { undo_txn[i] = 0u; if (slot == U_ROWS) slot = i; }
    }
    memcpy(undo_row[slot], row, sizeof undo_row[0]);
    undo_th[slot] = undo_th_src ? *undo_th_src : project.th.pat[t][pat < SQ_PATTERNS ? pat : 0u];   /* 0.23 */
    undo_track[slot] = t;
    undo_pat[slot] = pat;
    undo_len[slot] = len;
    undo_start[slot] = start;
    undo_txn[slot] = u_cur;
    u_top = u_cur;
    undo_refresh();
}

static void undo_add(uint8_t t, uint8_t pat)
{
    undo_add_row(t, pat, project.step[t][pat], project.track[t].length, project.track[t].start);
}

static uint16_t th_made;                                /* 0.25 THE PARTS LISTEN: tracks whose pattern an act made, or put back (th_answer) */
static void undo_clear(void)
{
    memset(undo_txn, 0, sizeof undo_txn);
    u_top = 0u; u_cur = 0u; undo_valid = 0u;
}

static void undo_apply(uint16_t txn)                     /* swap the rows of one edit with the project */
{
    uint32_t k, i;
    for (k = 0; k < U_ROWS; k++) {
        sq_step_t *row;
        sq_track_cfg_t *c;
        uint8_t l, s0;
        sq_step_t tmp;
        sq_track_cfg_t was;
        if (undo_txn[k] != txn) continue;
        row = project.step[undo_track[k]][undo_pat[k]];
        c = &project.track[undo_track[k]];
        was = *c;
        l = c->length; s0 = c->start;
        for (i = 0; i < SQ_STEPS; i++) { tmp = row[i]; row[i] = undo_row[k][i]; undo_row[k][i] = tmp; }
        if (undo_pat[k] < SQ_PATTERNS) {                  /* 0.23: and what the engines knew of it */
            sq_thpat_t m = project.th.pat[undo_track[k]][undo_pat[k]];
            project.th.pat[undo_track[k]][undo_pat[k]] = undo_th[k];
            undo_th[k] = m;
        }
        c->length = undo_len[k]; c->start = undo_start[k];
        undo_len[k] = l; undo_start[k] = s0;
        th_made |= (uint16_t)(1u << undo_track[k]);       /* (0.25: the parts that answer this track answer what is back) */
        track_cfg_back(undo_track[k], &was, undo_pat[k]);   /* 0.11: in time (the explorer) */
    }
}

static uint32_t undo_levels(void)                        /* edits UNDO can still take */
{
    uint32_t i, n = 0u;
    uint16_t seen[U_ROWS];
    for (i = 0; i < U_ROWS; i++) {
        uint32_t j;
        if (!undo_txn[i] || undo_txn[i] > u_top) continue;
        for (j = 0; j < n; j++) if (seen[j] == undo_txn[i]) break;
        if (j == n) seen[n++] = undo_txn[i];
    }
    return n;
}

static void undo_swap(void)                              /* UNDO: the newest edit back */
{
    uint32_t i;
    uint16_t below = 0u;
    char *p;
    if (!undo_valid) { status_msg("NOTHING TO UNDO"); return; }
    undo_apply(u_top);
    for (i = 0; i < U_ROWS; i++)
        if (undo_txn[i] && undo_txn[i] < u_top && undo_txn[i] > below) below = undo_txn[i];
    u_top = below;
    u_cur = 0u;                                          /* the next edit starts its own transaction */
    undo_refresh();
    p = msg_buf; p = put_s(p, "UNDO"); if (undo_valid) { p = put_s(p, "  "); p = put_u(p, undo_levels()); p = put_s(p, " MORE"); } else p = put_s(p, "  (REDO: SEL+UNDO)");
    finish(p); status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}

static void undo_redo(void)                              /* REDO: the edit undone last, forward again */
{
    uint32_t i;
    uint16_t next = 0u;
    for (i = 0; i < U_ROWS; i++)
        if (undo_txn[i] > u_top && (!next || undo_txn[i] < next)) next = undo_txn[i];
    if (!next) { status_msg("NOTHING TO REDO"); return; }
    undo_apply(next);
    u_top = next;
    u_cur = 0u;
    undo_refresh();
    status_msg("REDO");
    ui_dirty = grid_dirty = 1u;
}

static void activate_row(uint32_t t, sq_step_t *row)
{
    uint32_t i;
    for (i = 0; i < SQ_STEPS; i++) if (row[i].flags & SQ_STEP_ON) step_activate(t, &row[i]);
    vg_state_sync(t);                                          /* 0.12: a row rewritten while the journey runs: its state follows */
}

/* ---- LFOs aimed at a track: those that move one of its parameters, and the CC ones on its channel */
static uint8_t lfo_aims(const sq_lfo_t *l, uint32_t t)
{
    return l->dest == SQ_LD_CC ? (uint8_t)(l->target == track_ch(t)) : (uint8_t)(l->target == t);
}

static void lfo_cook(uint32_t t, uint8_t heat)
{
    uint32_t i;
    for (i = 0; i < SQ_LFOS; i++) {
        sq_lfo_t *l = &project.lfo[i];
        if (!l->enabled || !lfo_aims(l, t)) continue;
        if (grand(100u) < heat / 2u && l->rate < SQ_LFO_RATES_STRAIGHT) l->rate = (uint8_t)clamp_i32((int32_t)l->rate + (grand(2u) ? 1 : -1), 2, SQ_LFO_RATES_STRAIGHT - 1);   /* (0.13: the triplets stay as they are) */
        if (grand(100u) < heat / 2u) l->depth = (uint8_t)clamp_i32((int32_t)l->depth + (int32_t)grand(2u * heat / 2u + 1u) - (int32_t)(heat / 2u), 8, 127);
        if (grand(100u) < heat / 3u) l->phase = (uint8_t)grand(128u);
        if (grand(100u) < heat / 6u) l->shape = (uint8_t)grand(SQ_LFO_SHAPES);
        lfo_last_valid[i] = 0u;
    }
}

/* a new LFO for the track: the one aimed at it, else a free one; mostly at its first CC lane (the filter), sometimes at
 * velocity, gate or timing */
static void lfo_dice(uint32_t t, uint8_t heat)
{
    uint32_t i, pick = SQ_LFOS, r;
    sq_lfo_t *l;
    for (i = 0; i < SQ_LFOS && pick == SQ_LFOS; i++) if (lfo_aims(&project.lfo[i], t) && project.lfo[i].enabled) pick = i;
    for (i = 0; i < SQ_LFOS && pick == SQ_LFOS; i++) if (!project.lfo[i].enabled) pick = i;
    if (pick == SQ_LFOS) return;                         /* all sixteen busy elsewhere */
    l = &project.lfo[pick];
    r = grand(100u);
    l->enabled = 1u;
    if (r < 65u) {
        l->dest = SQ_LD_CC;
        l->target = track_ch(t);
        l->param = project.track[t].lane_cc[0] != SQ_LANE_NONE ? project.track[t].lane_cc[0] : 74u;
    } else {
        l->dest = r < 80u ? SQ_LD_VEL : r < 92u ? SQ_LD_GATE : SQ_LD_TIMING;
        l->target = (uint8_t)t;
    }
    l->shape = (uint8_t)grand(SQ_LFO_SHAPES);
    l->rate = (uint8_t)(4u + grand(9u));
    l->depth = (uint8_t)clamp_i32(16 + (int32_t)heat * 9 / 10, 8, 127);
    l->center = 64u;
    l->phase = (uint8_t)grand(128u);
    l->flags = grand(2u) ? SQ_LF_RETRIG : 0u;
    lfo_last_valid[pick] = 0u;
}

/* ================================================================ 0.8 the LIVE LAYER (per track)
 * EUCLID LIVE: the track plays euc_pulses hits spread over its loop, turned by euc_rot, instead of its written on / off
 * (the notes, velocities ... of the steps stay; a step never written plays the track's own note).
 * Then the ALGORITHM: TURING (a looping or drifting register: the rhythm, or the notes as steps of the key), CELL (an
 * automaton, a new generation every 1 / 2 / 4 bars or loop), ACCENT (velocity), DENSITY (fewer or more hits).
 * The state lives here; turning the algorithm's knobs keeps it (0.7 started it again at every touch), choosing another
 * algorithm makes it new. WRITE LIVE (SEQ + white 7) puts what you hear into the pattern and switches the layer off. */
static uint8_t live_span(uint32_t t)
{
    const sq_track_cfg_t *c = &project.track[t];
    return (uint8_t)(c->length > c->start ? (uint32_t)(c->length - c->start) : 1u);
}

static uint64_t row_bits(uint32_t t, uint8_t n)     /* the written hits from the loop's start, n of them (wrapping) */
{
    const sq_track_cfg_t *c = &project.track[t];
    const sq_step_t *row = project.step[t][tr[t].pattern];
    uint8_t span = live_span(t);
    uint64_t b = 0u;
    uint32_t i;
    for (i = 0; i < n && i < 64u; i++)
        if (row[c->start + i % span].flags & SQ_STEP_ON) b |= (uint64_t)1u << i;
    return b;
}

static uint8_t cell_cells(const sq_algo_t *s) { return s->b < 4u ? 4u : s->b > 64u ? 64u : s->b; }   /* a CELL's width */

/* 0.25: a TURING's steps: its LENGTH, 2 .. 16 - or, past 16 (TRACK), the track's loop: the whole written rhythm is its
 * first loop, and the register is made longer or shorter WITH the track (LONGER, SHORTER, a length at the bar, the
 * metre): longer, the loop it has goes round again in the new steps; shorter, it keeps its first ones */
static uint8_t tm_steps(uint32_t t, const sq_algo_t *s)
{
    uint8_t n = s->b >= SQ_TM_LEN_TRACK ? live_span(t) : s->b;
    return (uint8_t)(n < 2u ? 2u : n > 64u ? 64u : n);
}
/* 0.11: the state of slot k is made when the slot's algorithm changes (algo_seen), from the written pattern */
static void live_sync_slot(uint32_t t, uint8_t k)
{
    const sq_track_cfg_t *c = &project.track[t];
    const sq_algo_t *s = SQ_ALGO_AT((sq_track_cfg_t *)c, k);
    if (algo_seen[t][k] == s->algo) {
        if (s->algo == SQ_ALGO_TURING) {             /* 0.25: its length is another */
            uint8_t len = tm_steps(t, s), track = (uint8_t)(s->b >= SQ_TM_LEN_TRACK ? 0x80u : 0u);
            if ((tm_len[t][k] & 0x7Fu) != len || (tm_len[t][k] & 0x80u) != track) {
                if (track || (tm_len[t][k] & 0x80u)) tm_reg[t][k] = sq_turing_resize(tm_reg[t][k], (uint8_t)(tm_len[t][k] & 0x7Fu), len);
                tm_len[t][k] = (uint8_t)(len | track);   /* (a length of 2 .. 16 turned by hand: the register as it is, as ever) */
            }
        }
        return;
    }
    algo_seen[t][k] = s->algo;
    ca_bars[t][k] = 0u;
    if (s->algo == SQ_ALGO_TURING) {                 /* the written rhythm is its first loop */
        uint8_t len = tm_steps(t, s);
        tm_len[t][k] = (uint8_t)(len | (s->b >= SQ_TM_LEN_TRACK ? 0x80u : 0u));
        tm_reg[t][k] = row_bits(t, len);
        if (!tm_reg[t][k]) {
            tm_reg[t][k] = sq_hash3(t + 16u * k, s->b, project.id);
            if (len > 32u) tm_reg[t][k] |= (uint64_t)sq_hash3(t + 16u * k + 1u, s->b, project.id) << 32;
            if (len < 64u) tm_reg[t][k] &= ((uint64_t)1u << len) - 1u;
        }
        if (!tm_reg[t][k]) tm_reg[t][k] = 1u;
    } else if (s->algo == SQ_ALGO_CELL) {
        uint8_t cells = cell_cells(s);
        ca_row[t][k] = row_bits(t, cells);
        if (!ca_row[t][k]) ca_row[t][k] = (uint64_t)1u << (cells / 2u);
    }
}
/* 0.23.1: a CELL's next row; when every cell died, the rhythm written on the track again (0.8-0.23: a single cell in
 * the middle, and the written rhythm never came back) */
static void cell_advance(uint32_t t, uint8_t k, const sq_algo_t *s)
{
    uint8_t cells = cell_cells(s);
    ca_row[t][k] = sq_cell_step(ca_row[t][k], cells, s->a, row_bits(t, cells));
}
static void live_sync(uint32_t t)
{
    uint8_t k;
    for (k = 0; k < SQ_ALGO_SLOTS; k++) live_sync_slot(t, k);
}

/* the step `step` of the track, written on or not: does it play now (*ghost: a hit DENSITY added)? The slots run in
 * order: a rhythm algorithm replaces the hit, DENSITY thins or fills what came before it. */
static uint8_t live_hit(uint32_t t, uint8_t step, uint8_t written, uint8_t *ghost)
{
    const sq_track_cfg_t *c = &project.track[t];
    uint8_t on = written, rel, k, g;
    *ghost = 0u;
    if (step < c->start || step >= c->length) return written;
    rel = (uint8_t)(step - c->start);
    if (c->flags & SQ_TF_EUC) on = sq_rhythm_hit(c->euc_fam, c->euc_pulses, live_span(t), c->euc_rot, rel);
    live_sync(t);
    for (k = 0; k < SQ_ALGO_SLOTS; k++) {
        const sq_algo_t *s = SQ_ALGO_AT((sq_track_cfg_t *)c, k);
        switch (s->algo) {
        case SQ_ALGO_TURING:
            if (s->c != SQ_TM_NOTES) { on = (uint8_t)(tm_reg[t][k] & 1u); *ghost = 0u; }
            break;
        case SQ_ALGO_CELL: {
            uint8_t cells = cell_cells(s);
            on = (uint8_t)((ca_row[t][k] >> (rel % cells)) & 1u); *ghost = 0u;
            break;
        }
        case SQ_ALGO_DENSITY:
            g = 0u;
            on = sq_density_hit(on, s->a, rel, sq_hash3(t + (k ? 16u * (k + 1u) : 0u), step, tr[t].loop_count), &g);
            if (g) *ghost = 1u;
            break;
        default: break;
        }
    }
    g = 0u;                                          /* (vg_density_hit leaves it when it has nothing to say) */
    on = vg_density_hit(t, on, rel, sq_hash3(t + 16u, step, tr[t].loop_count), &g);   /* 0.9: the energy */
    if (g) *ghost = 1u;
    return on;
}

static int32_t live_vel(uint32_t t, uint8_t step)  /* the ACCENTs, added up */
{
    const sq_track_cfg_t *c = &project.track[t];
    int32_t v = 0;
    uint8_t k;
    if (step < c->start) return 0;
    for (k = 0; k < SQ_ALGO_SLOTS; k++) {
        const sq_algo_t *s = SQ_ALGO_AT((sq_track_cfg_t *)c, k);
        if (s->algo == SQ_ALGO_ACCENT) v += sq_accent(s->a, s->b, s->c, (uint32_t)(step - c->start), sq_rng_next(&sq_rng_state));
    }
    return v;
}

static int32_t live_note_deg(uint32_t t)           /* the TURINGs on the notes: steps of the scale up, added */
{
    const sq_track_cfg_t *c = &project.track[t];
    int32_t d = 0;
    uint8_t k;
    for (k = 0; k < SQ_ALGO_SLOTS; k++) {
        const sq_algo_t *s = SQ_ALGO_AT((sq_track_cfg_t *)c, k);
        if (s->algo != SQ_ALGO_TURING || s->c == SQ_TM_RHYTHM) continue;
        live_sync_slot(t, k);
        d += (int32_t)((tm_reg[t][k] >> 1) & 7u);
    }
    return d;
}

static void live_step_done(uint32_t t)             /* after each step of the track: the registers move */
{
    const sq_track_cfg_t *c = &project.track[t];
    uint8_t k;
    for (k = 0; k < SQ_ALGO_SLOTS; k++) {
        const sq_algo_t *s = SQ_ALGO_AT((sq_track_cfg_t *)c, k);
        if (s->algo != SQ_ALGO_TURING) continue;
        live_sync_slot(t, k);
        tm_reg[t][k] = sq_turing_step64(tm_reg[t][k], tm_steps(t, s), s->a, sq_rng_next(&sq_rng_state));
    }
}

static void live_loop_done(uint32_t t)             /* the loop came round: the CELLs that move with the loop */
{
    const sq_track_cfg_t *c = &project.track[t];
    uint8_t k;
    for (k = 0; k < SQ_ALGO_SLOTS; k++) {
        const sq_algo_t *s = SQ_ALGO_AT((sq_track_cfg_t *)c, k);
        if (s->algo != SQ_ALGO_CELL || s->c != 3u) continue;
        live_sync_slot(t, k);
        cell_advance(t, k, s);
    }
}

static void live_bar(void)                         /* every bar: the CELLs that move with the bars */
{
    static const uint8_t EVERY[3] = {1u, 2u, 4u};
    uint32_t t;
    uint8_t k;
    for (t = 0; t < SQ_TRACKS; t++) {
        const sq_track_cfg_t *c = &project.track[t];
        for (k = 0; k < SQ_ALGO_SLOTS; k++) {
            const sq_algo_t *s = SQ_ALGO_AT((sq_track_cfg_t *)c, k);
            if (s->algo != SQ_ALGO_CELL || s->c > 2u) continue;
            live_sync_slot(t, k);
            if (++ca_bars[t][k] < EVERY[s->c]) continue;
            ca_bars[t][k] = 0u;
            cell_advance(t, k, s);
            if (t == selected_track) grid_dirty = 1u;
        }
    }
}

/* what the step will sound like: for the LEDs, the screen, the grid (TURING: as the register stands, if it does not
 * mutate before; DENSITY: in this loop) */
static uint8_t live_preview(uint32_t t, uint8_t step)
{
    const sq_track_cfg_t *c = &project.track[t];
    const sq_step_t *s0 = &project.step[t][tr[t].pattern][step];
    uint8_t on = (s0->flags & SQ_STEP_ON) ? 1u : 0u, rel, span, ghost, k;
    if (step < c->start || step >= c->length) return on;
    rel = (uint8_t)(step - c->start);
    span = live_span(t);
    if (c->flags & SQ_TF_EUC) on = sq_rhythm_hit(c->euc_fam, c->euc_pulses, span, c->euc_rot, rel);
    live_sync(t);
    for (k = 0; k < SQ_ALGO_SLOTS; k++) {
        const sq_algo_t *s = SQ_ALGO_AT((sq_track_cfg_t *)c, k);
        switch (s->algo) {
        case SQ_ALGO_TURING:
            if (s->c != SQ_TM_NOTES) {
                uint8_t next = (uint8_t)(tr[t].step >= c->start && tr[t].step < c->length ? (uint32_t)(tr[t].step - c->start) : 0u);
                uint8_t len = tm_steps(t, s), q = (uint8_t)((rel + span - next) % span);
                on = (uint8_t)((tm_reg[t][k] >> (q % len)) & 1u);
            }
            break;
        case SQ_ALGO_CELL: {
            uint8_t cells = cell_cells(s);
            on = (uint8_t)((ca_row[t][k] >> (rel % cells)) & 1u);
            break;
        }
        case SQ_ALGO_DENSITY:
            on = sq_density_hit(on, s->a, rel, sq_hash3(t + (k ? 16u * (k + 1u) : 0u), step, tr[t].loop_count), &ghost);
            break;
        default: break;
        }
    }
    return on;
}

/* 0.11: a melodic track whose RHYTHM an algorithm makes (TURING on the rhythm, CELL, DENSITY, EUCLID LIVE): its
 * notes are not all one step long. A note lasts to the next hit the layer makes, by the track's role: a PAD or a SUB
 * holds to it, a BASS on the beat (at most a beat), a CHORD or a PIANO when the gap is long, a LEAD a little; a STAB,
 * an ARP stay as written. Returns the steps (0 or 1: as written). A step written longer than one step is the player's. */
static uint8_t live_hold(uint32_t t, uint8_t step)
{
    const sq_track_cfg_t *c = &project.track[t];
    uint8_t role = gen_role(t), fam = sq_role_family(role), k, rhythm = (uint8_t)((c->flags & SQ_TF_EUC) != 0u), gap = 1u, span, rel, i;
    if (!sq_role_melodic(role) || track_drum(t) || step < c->start || step >= c->length) return 0u;
    if (project.step[t][tr[t].pattern][step].length > 100u) return 0u;
    for (k = 0; k < SQ_ALGO_SLOTS && !rhythm; k++) {
        const sq_algo_t *a = SQ_ALGO_AT((sq_track_cfg_t *)c, k);
        if (a->algo == SQ_ALGO_CELL || a->algo == SQ_ALGO_DENSITY || (a->algo == SQ_ALGO_TURING && a->c != SQ_TM_NOTES)) rhythm = 1u;
    }
    if (!rhythm) return 0u;
    span = live_span(t);
    rel = (uint8_t)(step - c->start);
    for (i = 1u; i < span && i <= 8u; i++) {
        if (live_preview(t, (uint8_t)(c->start + (rel + i) % span))) break;
        gap++;
    }
    switch (role) {
    case SQ_ROLE_PAD: case SQ_ROLE_SUB: return gap;
    case SQ_ROLE_STAB: case SQ_ROLE_ARP: return 0u;
    case SQ_ROLE_LEAD: case SQ_ROLE_VOX: return (uint8_t)(gap >= 3u ? (gap > 4u ? 4u : gap) : 0u);
    default: break;
    }
    if (fam == SQ_ROLE_BASS) return (uint8_t)((sq_g16(rel) & 3u) == 0u ? (gap > 4u ? 4u : gap) : 0u);   /* (on the beat - 0.25: the metre's) */
    if (fam == SQ_ROLE_CHORD) return (uint8_t)(gap >= 3u ? gap - 1u : 0u);
    return 0u;
}

static uint8_t live_algos(uint32_t t)             /* 0.11: how many slots run an algorithm */
{
    const sq_track_cfg_t *c = &project.track[t];
    uint8_t k, n = 0u;
    for (k = 0; k < SQ_ALGO_SLOTS; k++) if (SQ_ALGO_AT((sq_track_cfg_t *)c, k)->algo != SQ_ALGO_OFF) n++;
    return n;
}
static uint8_t live_active(uint32_t t)
{
    const sq_track_cfg_t *c = &project.track[t];
    return (uint8_t)((c->flags & SQ_TF_EUC) || live_algos(t));
}

/* 0.23.1: what the track's EUCLID knobs say, after "<what> T<n>: ": "5/16", or in NUMERIC the rhythm K1 picked and its
 * shape, "7 = 3-3-4-2-4" (the steps from each hit to the next); the rotation after it when `rot` */
static char *euclid_what(char *p, uint32_t t, uint8_t rot)
{
    const sq_track_cfg_t *c = &project.track[t];
    if (c->euc_fam == SQ_RF_NUMERIC) {
        p = put_u(p, (uint32_t)sq_numeric_index(c->euc_pulses) + 1u); p = put_s(p, " = ");
        p = sq_numeric_gaps_n(c->euc_pulses, sq_numeric_unit(live_span(t)), p);   /* (0.25: as it is in the bar, or in a loop shorter than one) */
    } else { p = put_u(p, c->euc_pulses); p = put_s(p, "/"); p = put_u(p, live_span(t)); }
    if (rot && c->euc_rot) { p = put_s(p, " ROT "); p = put_u(p, c->euc_rot); }
    return p;
}
static void euclid_status(uint32_t t)
{
    const sq_track_cfg_t *c = &project.track[t];
    uint8_t num = (uint8_t)(c->euc_fam == SQ_RF_NUMERIC);
    char *p = msg_buf;
    p = put_s(p, num ? "NUMERIC" : "EUCLID"); p = put_s(p, (c->flags & SQ_TF_EUC) ? " LIVE T" : " OFF T"); p = put_u(p, t + 1u);
    p = put_s(p, ": "); p = euclid_what(p, t, 1u);
    finish(p);
    status_msg(msg_buf);
}

/* a knob of EUCLID turned: heard at once if EUCLID LIVE is on; 0.16: off, the knobs set it up (READY) and SEQ + white 6
 * starts it with them (0.8-0.15 switched it on at the first touch, with what the knobs had before) */
static void euclid_touch(uint8_t t)
{
    const sq_track_cfg_t *c = &project.track[t];
    if (c->flags & SQ_TF_EUC) euclid_status(t);
    else {
        uint8_t num = (uint8_t)(c->euc_fam == SQ_RF_NUMERIC);   /* (NUMERIC: the shape takes the room of the rotation, which the cell shows) */
        char *p = msg_buf;
        p = put_s(p, num ? "NUMERIC READY T" : "EUCLID READY T"); p = put_u(p, t + 1u); p = put_s(p, ": "); p = euclid_what(p, t, (uint8_t)!num);
        p = put_s(p, num ? " SEQ + WHITE 6" : " SEQ + WHITE 6 STARTS IT"); finish(p);
        status_msg(msg_buf);
    }
    ui_dirty = grid_dirty = 1u;
}

/* SEQ + white 6: EUCLID LIVE on / off on the scope (any of them off: all on) */
static void euclid_toggle(void)
{
    uint16_t mask = gen_mask(), any_off = 0u;
    uint32_t t;
    for (t = 0; t < SQ_TRACKS; t++) if ((mask & (1u << t)) && !(project.track[t].flags & SQ_TF_EUC)) any_off = 1u;
    for (t = 0; t < SQ_TRACKS; t++) {
        if (!(mask & (1u << t))) continue;
        if (any_off) project.track[t].flags |= SQ_TF_EUC; else project.track[t].flags &= (uint8_t)~SQ_TF_EUC;
    }
    if (mask == (uint16_t)(1u << selected_track)) euclid_status(selected_track);
    else { char *p = msg_buf; p = put_s(p, any_off ? "EUCLID LIVE ON " : "EUCLID LIVE OFF "); p = put_u(p, popcount16(mask)); p = put_s(p, " TRACKS"); finish(p); status_msg(msg_buf); }
    ui_dirty = grid_dirty = 1u;
}

static sq_algo_t *algo_slot(uint32_t t) { return SQ_ALGO_AT(&project.track[t], algo_cur[t] < SQ_ALGO_SLOTS ? algo_cur[t] : 0u); }

/* 0.16: an algorithm is set up before it plays. K1 (SEQ 2, the grid's pads) makes one READY on the slot: K2-K4 set its
 * values, SEQ + white 6 starts it with them; SEQ + white 6 again stops it (its values stay, READY for the next start).
 * While one plays, K1 on another makes that one READY: the one playing goes on until SEQ + white 6 swaps them; K1 back on
 * the one playing and K2-K4 change it as it plays. K1 on OFF while one plays: SEQ + white 6 stops it. The values of
 * each algorithm of each slot are kept while the FM-1 is on (the project saves the one playing).
 * (0.11-0.15: K1 started an algorithm at once, with its default values.) */
#define ALGO_PEND_STOP 0x80u                            /* algo_pend: OFF chosen while one plays */
static uint8_t algo_k(uint32_t t) { return algo_cur[t] < SQ_ALGO_SLOTS ? algo_cur[t] : 0u; }
static uint8_t algo_pend_of(uint32_t t) { return algo_pend[t][algo_k(t)]; }
/* the algorithm the panel shows on the slot: the READY one, else the one playing */
static uint8_t algo_shown(uint32_t t)
{
    uint8_t p = algo_pend_of(t), a = algo_slot(t)->algo;
    if (p == ALGO_PEND_STOP) return SQ_ALGO_OFF;
    if (p && p < SQ_ALGOS) return p;
    return a < SQ_ALGOS ? a : SQ_ALGO_OFF;
}
/* the values kept for algorithm `a` of the slot shown (its defaults the first time) */
static sq_algo_t *algo_ready(uint32_t t, uint8_t a)
{
    sq_algo_t *m;
    if (a >= SQ_ALGOS) a = SQ_ALGO_OFF;
    m = &algo_mem[t][algo_k(t)][a];
    if (m->algo != a || a == SQ_ALGO_OFF) sq_algo_slot_default(m, a);
    return m;
}
/* what K2-K4 and the grid's rows change: the READY algorithm, or the one playing */
static sq_algo_t *algo_edit(uint32_t t)
{
    uint8_t p = algo_pend_of(t);
    if (p == ALGO_PEND_STOP) return algo_ready(t, SQ_ALGO_OFF);
    if (p && p < SQ_ALGOS) return algo_ready(t, p);
    return algo_slot(t);
}
static void algo_status(uint32_t t)
{
    const sq_algo_t *s = algo_slot(t);
    uint8_t pd = algo_pend_of(t), run = s->algo < SQ_ALGOS ? s->algo : 0u;
    char *p = msg_buf;
    p = put_s(p, "T"); p = put_u(p, t + 1u); p = put_s(p, " ALGO "); p = put_u(p, (uint32_t)algo_k(t) + 1u); p = put_s(p, ": ");
    if (pd == ALGO_PEND_STOP) { p = put_s(p, "SEQ + WHITE 6 STOPS "); p = put_s(p, ALGO_NAME[run]); }
    else if (pd && pd < SQ_ALGOS) {
        p = put_s(p, ALGO_NAME[pd]); p = put_s(p, " READY");
        if (run) { p = put_s(p, " ("); p = put_s(p, ALGO_NAME[run]); p = put_s(p, " PLAYS)"); }
        p = put_s(p, ": SEQ + WHITE 6");
    } else {
        p = put_s(p, ALGO_NAME[run]);
        if (live_algos(t) > 1u) { p = put_s(p, " ("); p = put_u(p, live_algos(t)); p = put_s(p, " RUN)"); }
    }
    finish(p);
    status_msg(msg_buf);
}

/* 0.11: the slot the knobs and the grid work on (SEL + K1 on SEQ 2, the grid's pad) */
static void algo_slot_select(uint8_t t, uint8_t k)
{
    algo_cur[t] = k < SQ_ALGO_SLOTS ? k : 0u;
    algo_status(t);
    ui_dirty = grid_dirty = 1u;
}

/* K1 on SEQ 2, a pad of the grid: algorithm `a` READY on the slot shown (the one playing: its knobs again) */
static void algo_choose(uint8_t t, uint8_t a)
{
    uint8_t run = algo_slot(t)->algo;
    if (a >= SQ_ALGOS) a = SQ_ALGO_OFF;
    if (a == run) algo_pend[t][algo_k(t)] = 0u;
    else algo_pend[t][algo_k(t)] = a == SQ_ALGO_OFF ? (uint8_t)ALGO_PEND_STOP : a;
    algo_status(t);
    ui_dirty = grid_dirty = 1u;
}

/* SEQ + white 6 on SEQ 2: the READY algorithm starts with its values (in place of the one playing); none READY: the one
 * playing stops, READY again as it was */
static void algo_go(uint8_t t)
{
    uint8_t k = algo_k(t), pd = algo_pend[t][k];
    sq_algo_t *s = algo_slot(t);
    char *p = msg_buf;
    p = put_s(p, "T"); p = put_u(p, (uint32_t)t + 1u); p = put_s(p, " ALGO "); p = put_u(p, (uint32_t)k + 1u); p = put_s(p, ": ");
    if (pd && pd < SQ_ALGOS) {
        if (s->algo != SQ_ALGO_OFF && s->algo < SQ_ALGOS) *algo_ready(t, s->algo) = *s;   /* (the one it replaces keeps its values) */
        *s = *algo_ready(t, pd);
        p = put_s(p, ALGO_NAME[pd]); p = put_s(p, " STARTS");
        if (live_algos(t) > 1u) { p = put_s(p, " ("); p = put_u(p, live_algos(t)); p = put_s(p, " RUN)"); }
    } else if (s->algo != SQ_ALGO_OFF && s->algo < SQ_ALGOS) {
        uint8_t was = s->algo;
        *algo_ready(t, was) = *s;
        sq_algo_slot_default(s, SQ_ALGO_OFF);
        pd = was;
        p = put_s(p, ALGO_NAME[was]); p = put_s(p, " STOPS (READY AGAIN)");
    } else {
        algo_pend[t][k] = 0u;
        status_msg("NOTHING READY: K1 CHOOSES, K2-K4 SET, SEQ + WHITE 6 STARTS");
        ui_dirty = grid_dirty = 1u;
        return;
    }
    algo_pend[t][k] = (pd && pd < SQ_ALGOS && s->algo == SQ_ALGO_OFF) ? pd : 0u;
    algo_seen[t][k] = 255u;                              /* its state is made new, from the written pattern */
    ca_bars[t][k] = 0u;
    finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}

/* the grid's pads 1-5 of the ALGO row: a tap makes it READY, a tap on the READY one starts it, on the one playing stops it */
static void algo_pad(uint8_t t, uint8_t a)
{
    uint8_t pd = algo_pend_of(t);
    if (a == algo_shown(t) && (pd || algo_slot(t)->algo != SQ_ALGO_OFF)) algo_go(t);
    else algo_choose(t, a);
}

/* 0.23.1: the rule or the width of the CELL shown changed: the screen says what it makes of this track's rhythm from
 * here on - from the row that plays if it is the one playing, from the written rhythm if it is READY:
 * "T1 CELL RULE 90: A LOOP OF 8 ROWS", "... SLIDES 1 STEP LATER EVERY ROW", "... AFTER 3 ROWS IT STAYS" */
static void cell_hint(uint8_t t)
{
    const sq_algo_t *s = algo_edit(t);
    uint8_t cells = cell_cells(s), k = algo_k(t);
    uint64_t home = row_bits(t, cells), row = home;
    sq_cell_story_t st;
    char *p = msg_buf;
    if (s->algo != SQ_ALGO_CELL) return;
    if (s == algo_slot(t)) { live_sync_slot(t, k); row = ca_row[t][k]; }
    p = put_s(p, "T"); p = put_u(p, (uint32_t)t + 1u); p = put_s(p, " CELL RULE "); p = put_u(p, s->a); p = put_s(p, ": ");
    if (!sq_cell_story(row, cells, s->a, home, &st)) p = put_s(p, "KEEPS CHANGING FOR A LONG TIME");
    else {
        if (st.lead) { p = put_s(p, "AFTER "); p = put_u(p, st.lead); p = put_s(p, st.lead == 1u ? " ROW " : " ROWS "); }
        if (st.period == 1u) p = put_s(p, st.full ? "EVERY STEP PLAYS" : st.lead ? "IT STAYS" : "THE RHYTHM STAYS AS IT IS");
        else if (st.slide) {
            uint32_t n = (uint32_t)(st.slide < 0 ? -st.slide : st.slide);
            p = put_s(p, "SLIDES "); p = put_u(p, n); p = put_s(p, n == 1u ? " STEP " : " STEPS "); p = put_s(p, st.slide < 0 ? "EARLIER" : "LATER");
            if (!st.lead) p = put_s(p, " EVERY ROW");
        } else { p = put_s(p, "A LOOP OF "); p = put_u(p, st.period); if (!st.lead) p = put_s(p, " ROWS"); }
    }
    finish(p);
    status_msg(msg_buf);
}

/* SEQ page 2, K2-K4: the algorithm's A, B, C (each its range; the state stays); 0.16: of the READY one if there is one */
static void algo_turn(uint8_t t, int32_t d2, int32_t d3, int32_t d4, int32_t f2, int32_t f3, int32_t f4)
{
    sq_algo_t *s = algo_edit(t);
    switch (s->algo) {
    case SQ_ALGO_TURING:
        if (d2) s->a = (uint8_t)kstep(s->a, d2, f2, 0, 100);
        if (d3) s->b = (uint8_t)clamp_i32((int32_t)s->b + d3, 2, (int32_t)SQ_TM_LEN_TRACK);   /* (0.25: past 16: TRACK) */
        if (d4) s->c = change_u8(s->c, d4, 0u, SQ_TM_MODES - 1u);
        break;
    case SQ_ALGO_CELL:
        if (d2) s->a = (uint8_t)kstep(s->a, d2, f2, 0, 255);
        if (d3) s->b = (uint8_t)kstep(s->b, d3, f3, 4, 64);
        if (d4) { s->c = change_u8(s->c, d4, 0u, 3u); if (s == algo_slot(t)) ca_bars[t][algo_k(t)] = 0u; }
        if (d2 || d3) cell_hint(t);                      /* 0.23.1: what this rule makes of the rhythm */
        break;
    case SQ_ALGO_ACCENT:
        if (d2) s->a = change_u8(s->a, d2, 0u, 4u);
        if (d3) s->b = (uint8_t)kstep(s->b, d3, f3, 0, 63);
        if (d4) s->c = change_u8(s->c, d4, 0u, 15u);
        break;
    case SQ_ALGO_DENSITY:
        if (d2) {                                         /* 0.27: and the screen says who it works on */
            char *p = msg_buf;
            s->a = (uint8_t)kstep(s->a, d2, 5 * f2, 0, 200);
            p = put_s(p, "T"); p = put_u(p, (uint32_t)t + 1u); p = put_s(p, " DENSITY "); p = put_u(p, s->a); p = put_s(p, "%: THIS TRACK ONLY"); finish(p);
            status_msg(msg_buf);
        }
        if (d3) s->b = (uint8_t)kstep(s->b, d3, 5 * f3, 10, 100);
        break;
    default:
        if (d2 || d3 || d4) status_msg(algo_pend_of(t) == ALGO_PEND_STOP ? "OFF CHOSEN: SEQ + WHITE 6 STOPS IT (K1: ANOTHER)"
                                                                     : "ALGORITHM OFF: K1 CHOOSES ONE (SEL + K1: THE SLOT)");
        break;
    }
    (void)f4;
    ui_dirty = grid_dirty = 1u;
}

/* WRITE LIVE: what the scope's tracks play now goes into their patterns; the live layer goes off (UNDO takes it back) */
static void live_write(void)
{
    uint16_t mask = gen_mask();
    uint32_t t, i, n = 0u;
    undo_begin();
    for (t = 0; t < SQ_TRACKS; t++) {
        sq_track_cfg_t *c = &project.track[t];
        sq_step_t *row = project.step[t][tr[t].pattern];
        uint8_t heard[SQ_STEPS];
        if (!(mask & (1u << t)) || !live_active(t)) continue;
        for (i = c->start; i < c->length; i++) heard[i] = live_preview(t, (uint8_t)i);
        undo_add((uint8_t)t, tr[t].pattern);
        for (i = c->start; i < c->length; i++) {
            if (heard[i]) step_activate(t, &row[i]); else row[i].flags &= (uint8_t)~SQ_STEP_ON;
        }
        c->flags &= (uint8_t)~SQ_TF_EUC;
        {   uint8_t k;                                   /* (ACCENT changes no hit: it stays) */
            for (k = 0; k < SQ_ALGO_SLOTS; k++) {
                sq_algo_t *a = SQ_ALGO_AT(c, k);
                if (a->algo != SQ_ALGO_ACCENT) sq_algo_slot_default(a, SQ_ALGO_OFF);
                algo_seen[t][k] = 255u;
            }
        }
        n++;
    }
    if (!n) status_msg("NO LIVE LAYER TO WRITE");
    else { char *p = msg_buf; p = put_s(p, "LIVE WRITTEN TO "); p = put_u(p, n); p = put_s(p, n == 1u ? " TRACK" : " TRACKS"); finish(p); status_msg(msg_buf); }
    ui_dirty = grid_dirty = 1u;
}

/* ================================================================ 0.8 the HARMONY
 * A progression of the genre (sagga_beats.c) plays along with the transport: chord k after the bars it lasts. The
 * tracks with FOLLOW (HOME page 2, K4; SEQ page 4, K4) move to the chord that plays (dinghy.c: step_notes): written on
 * the tonic, they sound on I, VI, III, VII ... with the colours of the progression. Stopped: the tonic. */
/* 0.10: the progression: one of the genre's (0..5) or one the player wrote (6..9, project.uprog).
 * 0.11: the genre is the harmony's own (project.gen.harm_genre), not the one the knobs browse. */
/* 0.11: the progression as it plays: a row of chords with their 16ths (sq_hprog_t), made from the library's or the
 * player's by the HARMONY's rhythm (SEL + K4 on SEQ 4; GENRE: the genre's own) */
static uint8_t harm_rhythm_now(void)
{
    uint8_t r = project.gen.harm_rhythm;
    return r == SQ_HR_GENRE ? sq_genre_hrhythm(project.gen.harm_genre) : r;
}
static const sq_uprog_t *harm_uprog(uint8_t prog)
{
    return prog >= SQ_PROGS ? &project.uprog[(prog - SQ_PROGS) % SQ_UPROG_SLOTS] : 0;
}
static void harm_hprog_of(uint8_t prog, sq_hprog_t *h)
{
    const sq_gen_t *g = &project.gen;
    if (prog >= SQ_PROGS) sq_hprog_user(h, harm_uprog(prog), g->harm_bars, harm_rhythm_now());
    else {
        const sq_prog_t *pg = sq_prog_get(g->harm_genre, prog);
        sq_hprog_lib(h, pg->deg, pg->col, pg->n, g->harm_bars ? g->harm_bars : pg->bars, harm_rhythm_now());
    }
}
/* (16ths: a chord may change on any of them. 0.25: the 16ths of a 4/4 bar the metre's steps stand for - a chord that
 * lasts a bar lasts a bar of the metre, one that changes at the half changes on a beat near it: sq_metre_virt16) */
static uint32_t harm_pos(void)
{
    if (!playing) return 0u;
    return bar_no() * 16u + sq_metre_virt16(bar_st(), bar_bt(), (uint8_t)(bar_into() / 6u));
}
/* the chord playing now; 0 if the HARMONY is off */
static uint8_t harm_chord(sq_hchord_t *c, uint8_t *idx)
{
    sq_hprog_t h;
    uint8_t k;
    if (kb_chord_on && SQ_KB_IS_CHORD(project.ext.kb_mode)) {   /* 0.26 LIVE CHORDS: the keyboard's, whatever the progression (the HARMONY off too) */
        *c = kb_chord;
        if (idx) *idx = 0u;
        return 1u;
    }
    if (!project.gen.harm_on) return 0u;
    harm_hprog_of(project.gen.harm_prog, &h);
    k = sq_hprog_at(&h, harm_pos(), c);
    if (idx) *idx = k;
    if (vg_color7()) {                                               /* 0.9: high energy colours the triads */
        if (c->semi == 255u && c->col == SQ_HC_TRIAD) c->col = SQ_HC_7;
        else if (c->semi <= 11u && c->shape == SQ_HC_TRIAD) c->shape = SQ_HC_7;
        else if (c->shape == SQ_HSHAPE_CH + SQ_CH_MAJ) c->shape = SQ_HSHAPE_CH + SQ_CH_7;
        else if (c->shape == SQ_HSHAPE_CH + SQ_CH_MIN) c->shape = SQ_HSHAPE_CH + SQ_CH_MIN7;
    }
    return 1u;
}
static void harm_name_of(uint8_t prog, char *out, uint32_t cap)
{
    if (prog >= SQ_PROGS) sq_uprog_name(harm_uprog(prog), project.key_scale, out, cap);
    else sq_prog_name(project.gen.harm_genre, prog, project.key_scale, out, cap);
}
static void harm_name(char *out, uint32_t cap) { harm_name_of(project.gen.harm_prog, out, cap); }
/* (0.10's view of a chord, for VIAGGIO and the Pi's STATO: the step of the key nearest its root) */
static uint8_t harm_now(int8_t *deg, uint8_t *col)
{
    sq_hchord_t c;
    if (!harm_chord(&c, 0)) return 0u;
    if (c.semi == 255u) { *deg = c.deg; *col = c.col; return 1u; }
    {
        uint8_t want = c.semi, best = 0u, bd = 12u, d;
        for (d = 0; d < 7u; d++) {
            sq_hchord_t x = {(int8_t)d, SQ_HC_TRIAD, 255u, 0u};
            uint8_t sm = sq_hchord_semi(project.key_scale, &x), dist = (uint8_t)(sm > want ? sm - want : want - sm);
            if (dist > 6u) dist = (uint8_t)(12u - dist);
            if (dist < bd) { bd = dist; best = d; }
        }
        *deg = (int8_t)best;
        *col = c.shape <= SQ_HSHAPE_CH ? c.shape : SQ_HC_TRIAD;
    }
    return 1u;
}

static uint8_t harm_index(void)                    /* which chord of the progression plays now */
{
    sq_hchord_t c;
    uint8_t k = 0u;
    if (!harm_chord(&c, &k)) {
        sq_hprog_t h;
        harm_hprog_of(project.gen.harm_prog, &h);
        k = sq_hprog_at(&h, harm_pos(), &c);
    }
    return k;
}
/* the mood of a progression: the one the player gave it, else the machine's guess */
static uint8_t harm_mood_of(uint8_t prog)
{
    sq_hprog_t h;
    const sq_uprog_t *u = harm_uprog(prog);
    if (u && u->mood) return u->mood;
    if (u && !u->n) return SQ_MOOD_ANY;
    harm_hprog_of(prog, &h);
    return sq_hprog_mood(&h, project.key_scale);
}

/* the progression after a head: FREE, the genre (USER, DICE/PI), the chords, as much of them as the line holds */
static void harm_say(const char *head, const char *tail)
{
    const sq_gen_t *g = &project.gen;
    char *p = msg_buf, *end;
    uint32_t tl = 0u;
    while (tail && tail[tl]) tl++;
    p = put_s(p, head);
    if (g->harm_free && g->harm_prog < SQ_PROGS) p = put_s(p, "FREE ");              /* 0.16 */
    if (g->harm_prog == SQ_PROG_PI) p = put_s(p, "DICE/PI ");
    else if (g->harm_prog >= SQ_PROGS) p = put_s(p, "USER ");
    else { p = put_s(p, sq_genre_name(project.gen.harm_genre)); p = put_s(p, " "); }
    end = msg_buf + sizeof msg_buf - 1u - tl;           /* (0.16: FREE made a long one run past the 64 bytes) */
    if (p < end) { harm_name(p, (uint32_t)(end - p) + 1u); while (*p) p++; }
    if (tail) p = put_s(p, tail);
    finish(p);
    status_msg(msg_buf);
}
static void harm_status(void)
{
    const sq_gen_t *g = &project.gen;
    if (!g->harm_on) { status_msg("HARMONY OFF"); return; }
    harm_say(g->harm_lock ? "HARMONY LOCK " : "HARMONY ", 0);
}

static void piprog_leave(void);                    /* sagga_pipat.c: 0.11 no longer browsing the Pi's progressions */
/* 0.11 SEQ 4 K1: OFF / ON / LOCK. LOCK: the harmony plays and changes only by hand (not with a pattern loaded from
 * another genre, not with VIAGGIO's genre); the player still turns K2 / K3 and SEL + K2 (its genre) as ever. */
static uint8_t any_follow(void);
static void harm_state_set(uint8_t st)
{
    project.gen.harm_on = st ? 1u : 0u;
    project.gen.harm_lock = st == 2u ? 1u : 0u;
    harm_status();
    if (st == 2u) status_msg("HARMONY LOCK: CHANGES ONLY BY YOUR HAND");
    else if (st == 1u && !any_follow()) status_msg("HARMONY ON: NO TRACK FOLLOWS (HOME 2 K4)");
    ui_dirty = grid_dirty = 1u;
}
static uint8_t harm_state(void) { return project.gen.harm_on ? (project.gen.harm_lock ? 2u : 1u) : 0u; }
/* SEQ 4, SEL + K2: the harmony's genre, by hand (the progression keeps its number: the same slot of another genre) */
static void harm_genre_set(uint8_t g)
{
    if (g >= SQ_GENRES) return;
    if (g != project.gen.harm_genre) piprog_leave();
    project.gen.harm_genre = g;
    if (project.gen.harm_prog >= SQ_PROGS) status_msg("HARMONY: A USER PROGRESSION PLAYS (K2 FOR THE GENRE'S)");
    else harm_status();
    ui_dirty = grid_dirty = 1u;
}

/* 0.16 ARP 4 K2: FREE, then the 22 genres (0.29; 25 before). FREE keeps the progression playing (its genre stays harm_genre, for what
 * reads it) and from then on no pattern loaded moves it; K2 on ARP 3 goes through every genre's eight (0.29) */
static uint8_t harm_genre_pos(void) { return project.gen.harm_free ? 0u : (uint8_t)(project.gen.harm_genre + 1u); }
static void harm_genre_turn(int32_t d)
{
    uint8_t pos = change_u8(harm_genre_pos(), d, 0u, SQ_GENRES);
    if (!pos) {
        if (!project.gen.harm_free) {
            char *p = msg_buf;
            project.gen.harm_free = 1u;
            p = put_s(p, "HARMONY FREE: NO GENRE MOVES IT, ARP 3 K2 ALL "); p = put_u(p, (uint32_t)SQ_GENRES * SQ_PROGS); finish(p);
            status_msg(msg_buf);
            ui_dirty = grid_dirty = 1u;
        }
        return;
    }
    project.gen.harm_free = 0u;
    harm_genre_set((uint8_t)(pos - 1u));
}

static uint8_t any_follow(void)
{
    uint32_t t;
    for (t = 0; t < SQ_TRACKS; t++) if (project.track[t].flags & SQ_TF_FOLLOW) return 1u;
    return 0u;
}

static void harm_toggle(void)
{
    project.gen.harm_on ^= 1u;
    harm_status();
    if (project.gen.harm_on && !any_follow()) status_msg("HARMONY ON: NO TRACK FOLLOWS (HOME 2 K4)");
    ui_dirty = grid_dirty = 1u;
}

/* a progression of the genre, or one of the player's (6..9), 0.11 the DICE/PI one (10). 0.16: with the HARMONY off it is
 * READY, ARP 3 K1 starts it (0.11-0.15 choosing one switched the HARMONY on: live, before you had the one you wanted) */
typedef char sq_lib_progs_fit[SQ_LIB_PROGS == SQ_PROGS ? 1 : -1];   /* (0.29: eight a genre, in the library and in harm_prog) */
static void harm_prog_set(uint8_t i)
{
    project.gen.harm_prog = i < SQ_PROGS_ALL ? i : 0u;
    if (project.gen.harm_on) harm_status();
    else harm_say("READY ", ": K1 ON");
    ui_dirty = grid_dirty = 1u;
}
/* 0.11 SEQ 4 K2: the next progression, of the MOOD chosen (SEL + K3) when there is one: the genre's eight (0.29; six
 * until then), the player's four, the DICE/PI one when it holds a progression; past them the Pi's (sagga_pipat.c) */
static uint8_t piprog_enter(void);
static void piprog_turn(int32_t d);
static uint8_t piprog_browsing(void);
/* 0.16: the mood of progression p of genre g (as harm_mood_of, for a genre that is not the harmony's) */
static uint8_t harm_lib_mood(uint8_t g, uint8_t p)
{
    sq_hprog_t h;
    const sq_prog_t *pg = sq_prog_get(g, p);
    uint8_t r = project.gen.harm_rhythm == SQ_HR_GENRE ? sq_genre_hrhythm(g) : project.gen.harm_rhythm;
    sq_hprog_lib(&h, pg->deg, pg->col, pg->n, project.gen.harm_bars ? project.gen.harm_bars : pg->bars, r);
    return sq_hprog_mood(&h, project.key_scale);
}
/* 0.16 FREE: K2 goes through every genre's progressions (TECHNO 1 .. MERENGUE 8: 0.29, 22 genres of eight), then the
 * player's, DICE/PI, the Pi's; the MOOD chooses among all of them */
static void harm_free_turn(int32_t d)
{
    const int32_t lib = (int32_t)SQ_GENRES * SQ_PROGS, total = lib + (int32_t)(SQ_PROGS_ALL - SQ_PROGS);
    uint8_t mood = project.gen.harm_mood;
    int32_t cur = project.gen.harm_prog < SQ_PROGS ? (int32_t)project.gen.harm_genre * SQ_PROGS + project.gen.harm_prog
                                                   : lib + (int32_t)(project.gen.harm_prog - SQ_PROGS);
    int32_t start = cur, step = d > 0 ? 1 : -1, left = d > 0 ? d : -d;
    piprog_leave();
    while (left-- > 0) {
        int32_t next = cur;
        uint8_t found = 0u;
        for (;;) {
            next += step;
            if (next < 0 || next >= total) break;
            if (next < lib) { if (mood && harm_lib_mood((uint8_t)(next / SQ_PROGS), (uint8_t)(next % SQ_PROGS)) != mood) continue; }
            else {
                uint8_t pr = (uint8_t)(SQ_PROGS + (next - lib));
                if (pr == SQ_PROG_PI && !project.uprog[SQ_UPROGS].n) continue;
                if (mood && harm_mood_of(pr) != mood) continue;
            }
            found = 1u; break;
        }
        if (!found) {
            if (d > 0 && cur >= lib) {                             /* on into the Pi's, from the last of the FM-1's */
                if (cur != start) harm_prog_set((uint8_t)(SQ_PROGS + (cur - lib)));
                if (piprog_enter()) return;
            }
            if (mood && cur == start) {
                char *p = msg_buf;
                p = put_s(p, "NO MORE "); p = put_s(p, sq_mood_name(mood)); p = put_s(p, " (SEQ+BLACK 1 HELD: DICE PROG)"); finish(p);
                status_msg(msg_buf);
                return;
            }
            break;
        }
        cur = next;
    }
    if (cur < lib) { project.gen.harm_genre = (uint8_t)(cur / SQ_PROGS); harm_prog_set((uint8_t)(cur % SQ_PROGS)); }
    else harm_prog_set((uint8_t)(SQ_PROGS + (cur - lib)));
}
static void harm_prog_turn(int32_t d)
{
    uint8_t mood = project.gen.harm_mood, cur = project.gen.harm_prog, start = cur, k, step = d > 0 ? 1u : (uint8_t)(SQ_PROGS_ALL - 1u);
    int32_t left = d > 0 ? d : -d;
    if (piprog_browsing()) { piprog_turn(d); return; }
    if (project.gen.harm_free) { harm_free_turn(d); return; }     /* 0.16 */
    piprog_leave();
    while (left-- > 0) {
        uint8_t next = cur, found = 0u;
        for (k = 0; k < SQ_PROGS_ALL; k++) {
            next = (uint8_t)((next + step) % SQ_PROGS_ALL);
            if ((d > 0 && next <= cur) || (d < 0 && next >= cur)) break;   /* (no wrapping round: the ends stay) */
            if (next == SQ_PROG_PI && !project.uprog[SQ_UPROGS].n) continue;
            if (mood && harm_mood_of(next) != mood) continue;
            found = 1u; break;
        }
        if (!found) {
            if (d > 0) {                                               /* on into the Pi's, from the last of the FM-1's */
                if (cur != project.gen.harm_prog) harm_prog_set(cur);
                if (piprog_enter()) return;
            }
            if (mood && cur == start) {
                char *p = msg_buf;
                p = put_s(p, "NO MORE "); p = put_s(p, sq_mood_name(mood)); p = put_s(p, " (SEQ+SEL+BLACK 1: DICE PROG)"); finish(p);
                status_msg(msg_buf);
                return;
            }
            break;
        }
        cur = next;
    }
    harm_prog_set(cur);
}
/* 0.11 SEQ 4, SEL + K3: the MOOD the progressions are chosen by (ANY: all); SEL + K4: the HARMONY's RHYTHM */
static void harm_mood_set(uint8_t m)
{
    char *p = msg_buf;
    project.gen.harm_mood = m < SQ_MOODS ? m : 0u;
    piprog_leave();
    p = put_s(p, "MOOD "); p = put_s(p, sq_mood_name(project.gen.harm_mood));
    if (project.gen.harm_mood && harm_mood_of(project.gen.harm_prog) != project.gen.harm_mood) p = put_s(p, " (K2: ITS PROGRESSIONS)");
    finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}
static void harm_rhythm_set(uint8_t r)
{
    char *p = msg_buf;
    project.gen.harm_rhythm = r < SQ_HRS ? r : 0u;
    p = put_s(p, "CHORDS CHANGE: "); p = put_s(p, sq_hrhythm_name(project.gen.harm_rhythm));
    if (project.gen.harm_rhythm == SQ_HR_GENRE) { p = put_s(p, " ("); p = put_s(p, sq_hrhythm_name(sq_genre_hrhythm(project.gen.harm_genre))); p = put_s(p, ")"); }
    finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}
/* 0.11 SEQ + SEL + black 1: DICE PROG - a new progression of the MOOD (any) into the DICE/PI slot, which plays.
 * 0.23 THEORY: a progression by the rules of the harmony's genre's style (HARMONY FREE, GENRE FREE: of no genre) */
static void th_prog_dice(uint8_t style);
static void harm_dice(void)
{
    sq_uprog_t *u = &project.uprog[SQ_UPROGS];
    uint8_t minor = (uint8_t)(((sq_scale_mask(project.key_scale) >> 3) & 1u) && !((sq_scale_mask(project.key_scale) >> 4) & 1u));
    uint8_t style = th_style_now(project.gen.harm_genre < SQ_GENRES ? project.gen.harm_genre : beat_genre);
    char *p = msg_buf;
    if (style != 255u && project.gen.harm_free) style = SQ_TH_FREE;   /* (the engines are on, the harmony is nobody's: so is its progression) */
    if (style != 255u) {
        th_prog_dice(style);
        p = put_s(p, "DICE PROG "); p = put_s(p, sq_th_name(style)); p = put_s(p, ": ");
        sq_uprog_name(u, project.key_scale, p, 40u);
        while (*p) p++;
        finish(p);
        status_msg(msg_buf);
        ui_dirty = grid_dirty = 1u;
        return;
    }
    if (project.key_scale == SQ_SC_CHROMATIC) minor = 1u;
    piprog_leave();
    sq_uprog_dice(u, project.gen.harm_mood, minor, harm_rhythm_now(), &sq_rng_state);
    project.gen.harm_prog = SQ_PROG_PI;
    project.gen.harm_on = 1u;
    p = put_s(p, "DICE PROG "); p = put_s(p, sq_mood_name(u->mood)); p = put_s(p, ": ");
    sq_uprog_name(u, project.key_scale, p, 40u);
    while (*p) p++;
    finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}
/* 0.11 SEQ 4, SEL + K1: how a FOLLOW track's held note meets a change of chord; 0.25 MELODY: a tune - it stays where it is
 * written and its strong notes (on a beat, long, held through a change) go to the chord playing; 0.26 SMOOTH: a chord's
 * notes go to the nearest notes of the chord playing (held ones as LEGATO: those the two chords share go on) */
static void follow_mode_set(uint8_t t, uint8_t m)
{
    static const char *const N[SQ_FMS] = {"HELD NOTES KEEP THEIR CHORD", "HELD NOTES STRUCK AGAIN ON THE NEW CHORD", "HELD NOTES SLIDE TO THE NEW CHORD",
                                          "A TUNE: ITS STRONG NOTES ON THE CHORD", "CHORDS MOVE LITTLE: THE NEAREST NOTES"};
    project.track[t].follow_mode = m < SQ_FMS ? m : 0u;
    status_msg(N[project.track[t].follow_mode]);
    ui_dirty = grid_dirty = 1u;
}

static void harm_bars_turn(int32_t d)
{
    static const uint8_t B[5] = {0u, 1u, 2u, 4u, 8u};
    uint8_t i = 0u;
    while (i < 4u && B[i] != project.gen.harm_bars) i++;
    i = change_u8(i, d, 0u, 4u);
    project.gen.harm_bars = B[i];
    if (!B[i]) status_msg("HARMONY: THE PROGRESSION'S OWN BARS");
    else if (B[i] == 1u) status_msg("HARMONY: A CHORD EVERY BAR");
    else { char *p = msg_buf; p = put_s(p, "HARMONY: A CHORD EVERY "); p = put_u(p, B[i]); p = put_s(p, " BARS"); finish(p); status_msg(msg_buf); }
    ui_dirty = grid_dirty = 1u;
}

static void follow_set(uint8_t t, uint8_t on)
{
    sq_track_cfg_t *c = &project.track[t];
    if (track_drum(t)) { status_msg("A DRUM TRACK DOES NOT FOLLOW"); return; }
    if (on) c->flags |= SQ_TF_FOLLOW; else c->flags &= (uint8_t)~SQ_TF_FOLLOW;
    status_msg(on ? (project.gen.harm_on ? "FOLLOWS THE HARMONY" : "FOLLOWS (HARMONY IS OFF)") : "PLAYS AS WRITTEN");
    ui_dirty = grid_dirty = 1u;
}

/* ---- BEAT and PROG onto one track */
static void beat_onto(uint8_t t, uint8_t func, uint8_t var);

/* 0.25 THE MELODY KNOWS THE CHORD: the FOLLOW way a made part asks for. A tune (a LEAD, a VOX) follows as a MELODY: it
 * stays where it is written and its strong notes go to the chord playing. Any other part moves with the chords as ever:
 * a track that was a tune's goes back to HOLD, the ways the player chose for held notes (RETRIG, LEGATO) stay. */
static uint8_t follow_way_for(const sq_track_cfg_t *c, uint8_t func)
{
    if (sq_func_tune(func)) return SQ_FM_MELODY;      /* (0.29: the balafon too) */
    /* 0.26 THE CHORDS MOVE LITTLE: the chords a hand holds (a PAD, a PIANO) follow SMOOTH - each note to the nearest note
     * of the chord playing; a riff's chords (a STAB, the CHORD part) go on moving whole, as riffs do */
    if (func == SQ_FUNC_PAD || func == SQ_FUNC_PIANO)
        return (uint8_t)(c->follow_mode == SQ_FM_RETRIG || c->follow_mode == SQ_FM_LEGATO ? c->follow_mode : SQ_FM_SMOOTH);
    return (uint8_t)(c->follow_mode == SQ_FM_MELODY || c->follow_mode == SQ_FM_SMOOTH ? SQ_FM_HOLD : c->follow_mode);
}

/* PROG: the tonic chord on the genre's chord rhythm; the track follows the HARMONY, which starts if it was off */
typedef struct { uint8_t length, swing, flags, pen, groove, groove_amt, fmode; } beat_cfg_t;   /* (0.16: the part's GROOVE too; 0.25: its FOLLOW way) */
static uint8_t prog_onto_x(uint8_t t, uint8_t pat, uint8_t genre, uint8_t var, uint8_t apply, beat_cfg_t *cfg)
{
    sq_track_cfg_t *c = &project.track[t];
    uint8_t center = PEN(t) >= 48u && PEN(t) <= 72u ? PEN(t) : 60u, n;
    n = sq_beat_chords(project.step[t][pat < SQ_PATTERNS ? pat : tr[t].pattern], genre, var, gen_root(t), gen_scale(), center);
    if (!n) return 0u;
    project.th.pat[t][pat < SQ_PATTERNS ? pat : tr[t].pattern].style = 0u;   /* 0.23: the library's chords */
    made_fit(t, pat < SQ_PATTERNS ? pat : tr[t].pattern, n);          /* 0.24: the track keeps its length */
    if (cfg) {
        cfg->length = 0u; cfg->swing = c->swing; cfg->flags = (uint8_t)((c->flags & ~SQ_TF_DRUM) | SQ_TF_SCALE | SQ_TF_FOLLOW); cfg->pen = c->pen;
        cfg->groove = project.ext.track[t].groove; cfg->groove_amt = project.ext.track[t].groove_amt;
        cfg->fmode = follow_way_for(c, SQ_FUNC_PROG);
    }
    if (apply) {
        uint8_t st = c->start;
        c->start = 0u;
        if (st) track_fit(t, c->length, st, pat < SQ_PATTERNS ? pat : tr[t].pattern);   /* (the loop begins elsewhere: the other patterns) */
        c->flags = (uint8_t)((c->flags & ~SQ_TF_DRUM) | SQ_TF_SCALE | SQ_TF_FOLLOW);
        c->follow_mode = follow_way_for(c, SQ_FUNC_PROG);             /* 0.25: chords are no tune */
        c->src_func = SQ_FUNC_PROG; c->src_var = var;                 /* 0.10: GENRE LIVE loads it again from the new genre */
        c->src_genre = genre;                                         /* 0.11: COOK walks to the next one of this genre */
        if (!c->role) c->role = SQ_ROLE_CHORD;
        harm_follow_genre(genre);                                     /* 0.11: a chord part of this genre: its progressions */
        track_loaded(t);                                              /* 0.11: in time with the clock, whatever length it had */
    }
    if (!project.gen.harm_on) project.gen.harm_on = 1u;
    return n;
}
static void prog_onto(uint8_t t, uint8_t var) { prog_onto_x(t, tr[t].pattern, beat_genre, var, 1u, 0); }

/* the track's settings a loaded pattern asks for (0.9: a proposal keeps them until it enters: vg_prop_cfg) */
static void beat_cfg_for(const sq_track_cfg_t *c, uint8_t genre, uint8_t func, uint8_t n, uint8_t note, beat_cfg_t *o)
{
    uint8_t melodic = sq_func_kind(func) != SQ_KIND_DRUM;
    (void)n;
    o->length = 0u;                                                        /* 0.24: the track's own (12: the bembe' asks for its twelve) */
    sq_genre_groove(genre, func, &o->swing, &o->groove, &o->groove_amt);   /* the genre's feel (UK garage swings; 0.16: the
                                                                            * part's GROOVE, and the swing that goes with it) */
    if (melodic) {
        o->flags = (uint8_t)((c->flags & ~SQ_TF_DRUM) | SQ_TF_SCALE);
        if (project.gen.harm_on) o->flags |= SQ_TF_FOLLOW;   /* with the chords (0.11: every melodic part: a PAD, a STAB too) */
    } else o->flags = (uint8_t)((c->flags & ~(SQ_TF_SCALE | SQ_TF_FOLLOW)) | SQ_TF_DRUM);
    o->pen = melodic ? c->pen : note;
    o->fmode = melodic ? follow_way_for(c, func) : c->follow_mode;         /* 0.25: a tune knows the chord (a drum: nothing to follow) */
}
static void beat_cfg_apply(uint8_t t, uint8_t pat, const beat_cfg_t *o)
{
    sq_track_cfg_t *c = &project.track[t];
    uint8_t st = c->start, old = c->length;
    c->start = 0u;
    if (o->length && o->length != c->length) {         /* a pattern that is not made of bars: the track is as long as it is */
        if (pat < SQ_PATTERNS) sq_row_made(project.step[t][pat], o->length, o->length);
        c->length = o->length;
    }
    if (st || old != c->length) track_fit(t, old, st, pat);   /* (the track's other patterns: another loop for them too) */
    c->swing = o->swing;
    c->flags = o->flags;
    c->follow_mode = o->fmode < SQ_FMS ? o->fmode : (uint8_t)SQ_FM_HOLD;   /* 0.25 */
    PEN(t) = o->pen;
    project.ext.track[t].groove = o->groove;           /* 0.16 */
    project.ext.track[t].groove_amt = o->groove_amt;
}

/* ---- 0.23 THEORY: the engines (sagga_theory.c) where the library was. With the SOURCE on THEORY (SEQ 8 K1) a part
 * is not loaded: it is MADE, from the rules of the genre's style (GENRE FREE: of no genre) and a seed. What it was made
 * from is kept with the pattern (project.th.pat), so it can be made again: at another energy (th_service: the machine's
 * ENERGY fills and empties it), walked to its next variation (COOK), from another seed (SEQ 8 K3). Every genre of the
 * FM-1 has its style: four with rules written by hand, the others with rules counted from the library itself. */
static uint8_t vg_energy_now(void);                   /* sagga_viaggio.c: the energy applied now */
static sq_step_t th_row_a[SQ_STEPS] __attribute__((section(".pool")));   /* the rows the engines work in */
static sq_step_t th_row_b[SQ_STEPS] __attribute__((section(".pool")));
static uint8_t th_kick_lev[SQ_STEPS];
static uint8_t th_kept[SQ_TRACKS];                      /* 0.25: patterns of the engines the player changed, found when the metre did (a bit a pattern): they stay */

/* the kick that plays with pattern `pat` of track t: the first other track whose role is KICK and that plays in 16ths,
 * its pattern as levels a 16th (the one the engines made for the same pattern number, else the one it plays now).
 * 0: none, or the part is a kick itself: the engines then use the kick of the part's own seed. */
static const uint8_t *th_kick(uint8_t t, uint8_t pat, uint8_t func, uint8_t direct)
{
    uint32_t k, i;
    if (sq_func_family(func) == SQ_FUNC_KICK) return 0;
    for (k = 0; k < SQ_TRACKS; k++) {
        const sq_track_cfg_t *c = &project.track[k];
        const sq_step_t *row;
        uint8_t len, any = 0u;
        if (k == t || c->role != SQ_ROLE_KICK || c->division != SQ_DIV_1_16 || c->length <= c->start || track_tape(k) || track_break(k)) continue;
        row = project.step[k][pat < SQ_PATTERNS && project.th.pat[k][pat].style ? pat : tr[k].pattern];
        len = (uint8_t)(c->length - c->start);
        memset(th_kick_lev, 0, sizeof th_kick_lev);
        for (i = 0; i < SQ_STEPS; i++) {                 /* (0.25: step i of what the kick plays is a 16th of the engines' sixteens: sq_g16;
                                                          *  0.26, a part made in the bar: step i is step i) */
            const sq_step_t *st = &row[c->start + i % len];
            uint8_t v = (st->flags & SQ_STEP_ON) ? (uint8_t)(st->velocity ? st->velocity : 1u) : 0u;
            uint8_t lv = (uint8_t)(!v ? 0u : v >= 112u ? 4u : v >= 88u ? 3u : v >= 60u ? 2u : 1u);
            uint32_t at = direct ? i : (i / bar_st()) * 16u + sq_g16(i % bar_st());
            if (at < SQ_STEPS && lv > th_kick_lev[at]) th_kick_lev[at] = lv;
            if (v) any = 1u;
        }
        return any ? th_kick_lev : 0;
    }
    return 0;
}
/* 0.25 THE PARTS LISTEN. The part `func` on track t ANSWERS (sq_th_t.mate) the first other track whose role is of the
 * family it answers (sq_th_mate_family: a lead the chords, the percussion the snare, a bass the lead) and that plays
 * in 16ths. A pattern of the engines' is heard as it is at HALF the energy, made from what the engines keep of it:
 * what a part answers must not move as the energy rises, nor depend on which of the two was made first. One written by
 * hand, or the library's: its steps, as the kick's. 0: nobody to answer. */
static uint8_t th_mate_lev[SQ_STEPS];
static int32_t th_mate_track(uint8_t t, uint8_t func)    /* the track the part `func` on track t answers; -1: nobody */
{
    uint8_t fam = sq_th_mate_family(func);
    uint32_t k;
    if (fam == 255u) return -1;
    for (k = 0; k < SQ_TRACKS; k++) {
        const sq_track_cfg_t *c = &project.track[k];
        if (k == t || !c->role || (uint8_t)(sq_role_family(c->role) - 1u) != fam || c->division != SQ_DIV_1_16 || c->length <= c->start || track_tape(k) || track_break(k)) continue;
        return (int32_t)k;
    }
    return -1;
}
/* 0.26: `direct` - the part that answers is made in the bar (the engines of 0.26): the levels are a step each as the
 * track plays them, and the other part's NOTES come too (th_mate_nt: sq_th_t.mate_nt). The other part AS IT IS when it
 * is the engines', of 0.26 and in the bar there is now: made from what they keep of it at half the energy, with the
 * part IT answers heard the same way (the bass hears the tune that hears the chords: no further, nobody answers a
 * bass) - so what the bass takes from the tune is what the tune plays. Else as its steps are: of a track of chords
 * every step is a chord (with a seventh when one of its notes is one), of another its first note above the root. */
static uint8_t th_mate_nt[SQ_STEPS];
static uint8_t th_mate2_lev[SQ_STEPS], th_mate2_nt[SQ_STEPS];   /* (the part the heard part answers) */
static uint8_t th_mate_notes;                           /* th_mate_nt says something (the last th_mate) */
static uint8_t th_rec_len(const sq_thpat_t *m);
static void th_rec_bar(const sq_thpat_t *m, sq_th_t *h);
static uint8_t th_rec_here(const sq_thpat_t *m);
static uint8_t th_hear(uint32_t k, uint8_t pat, uint8_t direct, uint8_t deep, uint8_t *lev, uint8_t *nt)
{
    const sq_track_cfg_t *c = &project.track[k];
    uint8_t pi = pat < SQ_PATTERNS && project.th.pat[k][pat].style ? pat : tr[k].pattern;
    const sq_thpat_t *m = &project.th.pat[k][pi];
    const sq_step_t *row = project.step[k][pi];
    uint8_t len = (uint8_t)(c->length - c->start), any = 0u;
    uint8_t chords = (uint8_t)(c->role && (uint8_t)(sq_role_family(c->role) - 1u) == SQ_FUNC_CHORD);
    uint32_t i;
    if (m->style && (!direct || th_rec_here(m))) {
        sq_th_t h;
        memset(&h, 0, sizeof h);
        h.style = SQ_THP_STYLE(m); h.energy = 50u; h.vary = SQ_THP_VARY(m); h.scale = gen_scale(); h.seed = m->seed; h.var = m->var;
        if (!direct) sq_th_levels(&h, m->func, SQ_THP_LEN(m), lev);       /* (0.25: its rhythm, and alone) */
        else {
            int32_t k2 = deep ? -1 : th_mate_track((uint8_t)k, m->func);
            th_rec_bar(m, &h);                           /* (in its bar, as it was made) */
            if (k2 >= 0 && th_hear((uint32_t)k2, pat, 1u, 1u, th_mate2_lev, th_mate2_nt)) {
                h.mate = th_mate2_lev;
                if (SQ_THP_NOTES(m)) h.mate_nt = th_mate2_nt;             /* (its own answers have notes when it was made so) */
            }
            sq_th_heard(&h, m->func, th_rec_len(m), lev, nt);
        }
        for (i = 0; i < SQ_STEPS; i++) if (lev[i]) any = 1u;
        return any;
    }
    memset(lev, 0, SQ_STEPS);
    if (direct) memset(nt, 255, SQ_STEPS);
    for (i = 0; i < SQ_STEPS; i++) {                     /* (in the engines' sixteens, whatever the metre: sq_g16; 0.26, direct: a step each) */
        const sq_step_t *st = &row[c->start + i % len];
        uint8_t v = (st->flags & SQ_STEP_ON) ? (uint8_t)(st->velocity ? st->velocity : 1u) : 0u;
        uint8_t lv = (uint8_t)(!v ? 0u : v >= 112u ? 4u : v >= 88u ? 3u : v >= 60u ? 2u : 1u);
        uint32_t at = direct ? i : (i / bar_st()) * 16u + sq_g16(i % bar_st());
        if (at < SQ_STEPS && lv > lev[at]) lev[at] = lv;
        if (v && direct && st->note[0] <= 127u) {
            uint8_t cnt = 0u, sev = 0u, j;
            for (j = 0; j < SQ_POLY; j++)
                if (st->note[j] <= 127u) {
                    uint32_t iv = ((uint32_t)st->note[j] + 120u - st->note[0]) % 12u;
                    cnt++;
                    if (iv == 10u || iv == 11u) sev = 1u;
                }
            nt[i] = (uint8_t)(chords || cnt >= 2u ? (sev ? 18u : 16u) : ((uint32_t)st->note[0] + 120u - gen_root_note(k)) % 12u);
        }
        if (v) any = 1u;
    }
    return any;
}
static const uint8_t *th_mate(uint8_t t, uint8_t pat, uint8_t func, uint8_t direct)
{
    int32_t mk = th_mate_track(t, func);
    th_mate_notes = 0u;
    if (mk < 0 || !th_hear((uint32_t)mk, pat, direct, 0u, th_mate_lev, th_mate_nt)) return 0;
    th_mate_notes = direct;
    return th_mate_lev;
}
/* 0.26 THE ANSWER HAS NOTES, when it plays. A tune the engines of 0.26 made answers the chords with their notes: on the
 * 16ths right after a chord (three of them, the chords silent) it plays a note of the chord - written as a note of the
 * HOME chord, its root, its third or its fifth. When the progression has moved it must be a note of the chord that
 * PLAYS: so such a note is one FOLLOW MELODY takes to the chord (a strong note: the nearest note of the chord; on the
 * home chord it is where it is written). Read from the rows as they are when it plays - the tune's step, the steps of
 * the track it answers. Only in a pattern whose answers have notes (SQ_THPV_NOTES: made new by 0.26): one written by
 * hand, one of 0.25 play as they did. */
static uint8_t tune_answers(uint32_t t, const sq_step_t *s, uint8_t idx)
{
    const sq_track_cfg_t *c = &project.track[t], *mc;
    const sq_thpat_t *m = &project.th.pat[t][tr[t].pattern < SQ_PATTERNS ? tr[t].pattern : 0u];
    const sq_step_t *mrow, *ms;
    uint8_t root, hs, pc, hit = 0u;
    int32_t k, ri, base;
    uint32_t p, d, mlen;
    if (c->follow_mode != SQ_FM_MELODY || !(m->style & 31u) || !SQ_THP_NOTES(m) || s->note[0] > 127u || idx < c->start ||
        sq_th_mate_family(m->func) != SQ_FUNC_CHORD) return 0u;
    k = th_mate_track((uint8_t)t, m->func);
    if (k < 0) return 0u;
    mc = &project.track[k];
    mrow = project.step[k][tr[k].pattern < SQ_PATTERNS ? tr[k].pattern : 0u];
    mlen = (uint32_t)mc->length - mc->start;
    p = (uint32_t)idx - c->start;
    ms = &mrow[mc->start + p % mlen];
    if ((ms->flags & SQ_STEP_ON) && ms->velocity >= 60u) return 0u;         /* (the chords play here: it is not an answer) */
    for (d = 1u; d <= 3u && d <= p && !hit; d++) {
        ms = &mrow[mc->start + (p - d) % mlen];
        hit = (uint8_t)((ms->flags & SQ_STEP_ON) && ms->velocity >= 60u);
    }
    if (!hit) return 0u;
    root = key_root_of(t); hs = sq_harm_scale(key_scale_of(t));
    ri = sq_scale_index(60u, root, hs); base = ri - ((ri % 7) + 7) % 7;       /* (the home chord: sq_harm_tones) */
    pc = (uint8_t)(key_note(t, (int32_t)s->note[0]) % 12u);
    return (uint8_t)(pc == sq_scale_at(base, root, hs) % 12u || pc == sq_scale_at(base + 2, root, hs) % 12u || pc == sq_scale_at(base + 4, root, hs) % 12u);
}
static uint8_t th_note(uint8_t t, uint8_t func) { return sq_func_kind(func) != SQ_KIND_DRUM ? gen_root_note(t) : PEN(t); }
/* 0.26: `gen` 1 - the part is made IN the bar `steps` / `beats` (0: in sixteens, as 0.25; whoever asked re-bars it);
 * `notes` (only with gen) - its answers have notes */
/* 0.26: a part made in the bar hears the part it answers a step each, as that one IS - so that one must be in the bar
 * there is first. The engines' pattern it will hear, still in another metre (the service has not come to it yet), is
 * made again in this one now - and the part THAT one answers before it (the bass, the tune, the chords: no further). */
static void th_remetre(uint8_t t, uint8_t pat);
static uint8_t th_ready_depth;
static void th_mate_ready(uint8_t t, uint8_t pat, uint8_t func)
{
    int32_t k = th_mate_track(t, func);
    const sq_thpat_t *m;
    uint8_t pi;
    if (k < 0 || th_ready_depth >= 2u) return;
    pi = pat < SQ_PATTERNS && project.th.pat[k][pat].style ? pat : tr[k].pattern;
    m = &project.th.pat[k][pi];
    if (!m->style || m->metre == metre_id_now() || (th_kept[k] & (1u << pi)) || track_tape((uint32_t)k) || track_break((uint32_t)k)) return;
    th_ready_depth++;
    th_remetre((uint8_t)k, pi);
    th_ready_depth--;
}
static void th_set_x(sq_th_t *h, uint8_t style, uint16_t seed, uint8_t var, uint8_t vary, uint8_t energy, uint8_t t, uint8_t pat, uint8_t func,
                     uint8_t gen, uint8_t notes, uint8_t steps, uint32_t beats)
{
    if (gen) th_mate_ready(t, pat, func);
    memset(h, 0, sizeof *h);
    h->style = style; h->energy = energy > 100u ? 100u : energy; h->vary = vary > 100u ? 100u : vary;
    h->scale = gen_scale();
    h->seed = seed; h->var = var;
    h->gen = gen ? 1u : 0u;
    if (gen) { h->bar_steps = steps; h->bar_beats = beats; }
    h->kick = th_kick(t, pat, func, h->gen);
    h->mate = th_mate(t, pat, func, h->gen);             /* 0.25 */
    h->mate_nt = h->gen && notes && h->mate && th_mate_notes ? th_mate_nt : 0;   /* 0.26 */
}
/* THE ENGINES A PATTERN IS MADE BY (0.26). One made NEW - BEAT, a band, the dice, a seed chosen - is made by the engines
 * of now: in the bar there is, its answers with notes (th_set, th_make). One made AGAIN from what the engines keep of it
 * - the energy, a variation, another genre's style, the answer to a part that changed, UNDO - is made the way it was
 * (th_set_as, th_again: SQ_THP_V26, SQ_THPV_NOTES say how), so a project of 0.25 plays what it played. The METRE
 * changing is between the two: the pattern is made again IN THE NEW BAR - rhythms born in seven, in five - and its
 * answers stay as they were (th_remetre); back in 4/4 it is the pattern it was, to the note.
 * In 4/4 a pattern made in the bar and one made in sixteens are the same thing: without notes in its answers it is kept,
 * and made, as 0.25 did. A bar divided from outside has no number a pattern could keep: as 0.25 too. */
static uint8_t th_gen_now(uint8_t gen, uint8_t notes) { return (uint8_t)(gen && metre_id_now() != 255u && (notes || !metre_44())); }
/* for a pattern made NOW (a preview of one) */
static void th_set(sq_th_t *h, uint8_t style, uint16_t seed, uint8_t var, uint8_t vary, uint8_t energy, uint8_t t, uint8_t pat, uint8_t func)
{
    th_set_x(h, style, seed, var, vary, energy, t, pat, func, th_gen_now(1u, 1u), 1u, bar_st(), bar_bt());
}
/* the bar a pattern of the engines was made in when it was made in one; the steps it was made of (its bars of that
 * metre); whether it can be made again as it is in the bar there is now, a step each */
static void th_rec_bar(const sq_thpat_t *m, sq_th_t *h)
{
    uint8_t st = 16u;
    uint32_t bt = SQ_BEATS_44;
    h->gen = (uint8_t)((m->style & SQ_THP_V26) && sq_metre_of(m->metre, &st, &bt));
    h->bar_steps = h->gen ? st : 0u; h->bar_beats = h->gen ? bt : 0u;
}
static uint8_t th_rec_len(const sq_thpat_t *m)
{
    sq_th_t h;
    memset(&h, 0, sizeof h);
    th_rec_bar(m, &h);
    return h.gen ? sq_th_steps(&h, (uint8_t)(SQ_THP_LEN(m) / 16u)) : SQ_THP_LEN(m);
}
static uint8_t th_rec_here(const sq_thpat_t *m)
{
    if (m->style & SQ_THP_V26) return (uint8_t)(m->metre == metre_id_now());
    return (uint8_t)(metre_44() && m->metre == 0u);
}
/* for a pattern the engines keep, AS IT WAS MADE (in which bar, its answers with or without notes) - with another
 * variation, another energy if asked: what makes it again without changing what it is */
static void th_set_as(sq_th_t *h, const sq_thpat_t *m, uint8_t var, uint8_t vary, uint8_t energy, uint8_t t, uint8_t pat)
{
    sq_th_t b;
    memset(&b, 0, sizeof b);
    th_rec_bar(m, &b);
    th_set_x(h, SQ_THP_STYLE(m), m->seed, var, vary, energy, t, pat, m->func, b.gen, SQ_THP_NOTES(m), b.bar_steps, b.bar_beats);
}
/* ... its steps, into `row`, as it was made (in its bars; a pattern of 0.25: in sixteens, re-barred for the bar there is) */
static uint8_t th_load_as(sq_step_t *row, const sq_th_t *h, const sq_thpat_t *m, uint8_t t)
{
    if (h->gen) return sq_th_load(row, h, m->func, th_rec_len(m), th_note(t, m->func));
    return made_rebar(row, sq_th_load(row, h, m->func, SQ_THP_LEN(m), th_note(t, m->func)));
}
/* a pattern written whole by something else (a tool, the library, the Pi): it is not the engines' any more */
static void th_forget(uint8_t t, uint8_t pat) { if (t < SQ_TRACKS && pat < SQ_PATTERNS) project.th.pat[t][pat].style = 0u; }
/* the part `func` made into pattern `pat` of track t; what it was made from is kept with the pattern. Returns its steps
 * (th_make_x: `gen` in the bar, `notes` its answers have notes - where the bar allows: th_gen_now) */
static uint8_t th_make_x(uint8_t t, uint8_t pat, uint8_t style, uint8_t func, uint16_t seed, uint8_t var, uint8_t vary, uint8_t energy, uint8_t len,
                         uint8_t gen, uint8_t notes)
{
    sq_th_t h;
    sq_thpat_t *m = &project.th.pat[t][pat];
    uint8_t n;
    gen = th_gen_now(gen, notes);
    notes = (uint8_t)(gen && notes);
    th_set_x(&h, style, seed, var, vary, energy, t, pat, func, gen, notes, bar_st(), bar_bt());
    if (h.gen) len = sq_th_steps(&h, (uint8_t)(len / 16u));          /* 0.26: so many BARS OF THE METRE (16, 32, 64 in 4/4, as ever) */
    n = sq_th_load(project.step[t][pat], &h, func, len, th_note(t, func));
    if (!n) return 0u;
    m->seed = seed; m->func = func; m->var = var; m->energy = h.energy;
    m->vary = (uint8_t)(h.vary | (notes ? SQ_THPV_NOTES : 0u));
    m->style = h.gen ? (uint8_t)(SQ_THP_PACK(style, (uint8_t)(16u * (n / bar_st()))) | SQ_THP_V26) : SQ_THP_PACK(style, n);
    m->metre = metre_id_now();                           /* 0.25: the metre it is made in (0.26: its bars are that metre's; a pattern of 0.25: made_fit re-bars it) */
    th_kept[t] &= (uint8_t)~(1u << pat);
    return n;
}
static uint8_t th_make(uint8_t t, uint8_t pat, uint8_t style, uint8_t func, uint16_t seed, uint8_t var, uint8_t vary, uint8_t energy, uint8_t len)
{
    return th_make_x(t, pat, style, func, seed, var, vary, energy, len, 1u, 1u);
}
/* ... made again by the engines it was made by (what the pattern keeps says which), in another style if asked */
static uint8_t th_make_as(uint8_t t, uint8_t pat, uint8_t style, uint8_t func)
{
    const sq_thpat_t *m = &project.th.pat[t][pat];
    return th_make_x(t, pat, style, func, m->seed, m->var, SQ_THP_VARY(m), vg_energy_now(), made_len(t),
                     (uint8_t)((m->style & SQ_THP_V26) ? 1u : 0u), SQ_THP_NOTES(m));
}
/* the pattern the engines made, made again as it is kept (after its variation was changed by hand, for the part it
 * answers that changed) */
static uint8_t th_again(uint8_t t, uint8_t pat)
{
    sq_thpat_t *m = &project.th.pat[t][pat];
    uint8_t n;
    if (!m->style) return 0u;
    n = th_make_as(t, pat, SQ_THP_STYLE(m), m->func);    /* 0.24: for the track as it is now; 0.26: by the engines it was made by */
    made_fit(t, pat, n);
    return n;
}
/* THE ENERGY: a pattern of the engines that plays, and was made at another energy than the machine has now, is made
 * again at this one - only the steps that are not the same at the two energies are written (sq_th_remake), so the
 * pattern fills and empties without anything else in it moving, and what was changed by hand elsewhere stays. One
 * track a pass of the main loop; the kicks first, since a rumble and a sub mind where the kick is. */
static uint8_t th_serv_t, th_serv_phase, th_serv_e = 255u, th_serv_m;
/* 0.25 THE METRE: a pattern of the engines that plays was made in another metre: it is made again in this one, from
 * what it was made from - the same band in the new bar, and the same pattern again when the old bar comes back. Unless
 * the player changed it by hand since: then it is not what the engines would make, and it stays as it is (th_kept; it
 * follows the energy again when its own metre is back). A part that minds the kick that plays (a rumble, a sub) is
 * made again whatever: the kick under it is another now. */
static void th_remetre(uint8_t t, uint8_t pat)
{
    sq_thpat_t *m = &project.th.pat[t][pat];
    sq_step_t *row = project.step[t][pat];
    sq_th_t h;
    uint8_t os = 16u, n, same = 1u, style = SQ_THP_STYLE(m), func = m->func, var = m->var, vary = SQ_THP_VARY(m), notes = SQ_THP_NOTES(m);
    uint16_t seed = m->seed;
    uint32_t ob = SQ_BEATS_44, i;
    th_set_as(&h, m, var, vary, m->energy, t, pat);                        /* (0.26: as it was made - by which engines, in which bar) */
    if (!sq_th_minds_kick(&h, func) && !h.mate && sq_metre_of(m->metre, &os, &ob)) {   /* (nor one that answers another part: that one is another now) */
        if (h.gen) n = sq_th_load(th_row_a, &h, func, th_rec_len(m), th_note(t, func));
        else {
            n = sq_th_load(th_row_a, &h, func, SQ_THP_LEN(m), th_note(t, func));
            sq_rebar(th_row_a, (uint8_t)(n / 16u), os, ob);
            n = sq_rebar_len(n, os, ob);
        }
        for (i = 0; i < n && same; i++) same = (uint8_t)!memcmp(&row[i], &th_row_a[i], sizeof(sq_step_t));
        if (!n) same = 0u;
    }
    if (!same) { th_kept[t] |= (uint8_t)(1u << pat); return; }
    n = th_make_x(t, pat, style, func, seed, var, vary, vg_energy_now(), made_len(t), 1u, notes);   /* 0.26: IN the new bar; its answers as they were */
    if (!n) { th_kept[t] |= (uint8_t)(1u << pat); return; }
    made_fit(t, pat, n);
    activate_row(t, row);
    ui_dirty = grid_dirty = 1u;
}
/* 0.25 THE PARTS LISTEN: an act made the pattern of some tracks (BEAT, a BAND, the dice, a seed turned), or put it
 * back (UNDO): the engines' patterns that ANSWER one of those tracks are made again, from what the engines keep of them
 * - the same part of the same seed, answering what is there now. So nothing depends on the order the parts came in
 * (the bass of a band is made before its lead), and UNDO brings back the answer with the call. */
static void th_answer(void)
{
    uint16_t made = th_made;
    uint32_t u;
    th_made = 0u;
    for (u = 0; u < SQ_TRACKS; u++) {
        uint8_t pat = tr[u].pattern;
        const sq_thpat_t *m = &project.th.pat[u][pat];
        int32_t k;
        if (!m->style || track_tape(u) || track_break(u)) continue;
        k = th_mate_track((uint8_t)u, m->func);
        if (k < 0 || !(made & (1u << k))) continue;
        if (th_again((uint8_t)u, pat)) { activate_row(u, project.step[u][pat]); ui_dirty = grid_dirty = 1u; }
    }
}
static void th_service(void)
{
    uint8_t e = vg_energy_now(), mt = metre_id_now(), t, phase, pat, kick;
    sq_thpat_t *m;
    sq_th_t from, to;
    sq_step_t *row;
    if (th_made) th_answer();
    if (mt != th_serv_m) memset(th_kept, 0, sizeof th_kept);                      /* another metre: every pattern is looked at again */
    if (e != th_serv_e || mt != th_serv_m) { th_serv_e = e; th_serv_m = mt; th_serv_t = 0u; th_serv_phase = 0u; }   /* a new energy, a new metre: from the kicks again */
    t = th_serv_t; phase = th_serv_phase;
    if (++th_serv_t >= SQ_TRACKS) { th_serv_t = 0u; th_serv_phase ^= 1u; }       /* (a round of the kicks, a round of the others) */
    pat = tr[t].pattern;
    m = &project.th.pat[t][pat];
    if (!m->style || (m->energy == e && m->metre == mt) || track_tape(t) || track_break(t)) return;
    kick = (uint8_t)(sq_func_family(m->func) == SQ_FUNC_KICK);
    if ((phase == 0u) != (kick != 0u)) return;
    if (m->metre != mt) {                                 /* 0.25: made in another metre */
        if (!(th_kept[t] & (1u << pat))) th_remetre(t, pat);
        return;
    }
    row = project.step[t][pat];
    th_set_as(&from, m, m->var, SQ_THP_VARY(m), m->energy, t, pat);       /* (0.26: as it was made) */
    to = from; to.energy = e;
    if (from.gen ? sq_th_remake(row, &from, &to, m->func, th_rec_len(m), th_note(t, m->func), th_row_a, th_row_b)
                 : sq_th_remake_bar(row, &from, &to, m->func, SQ_THP_LEN(m), th_note(t, m->func), th_row_a, th_row_b, bar_st(), bar_bt())) {
        activate_row(t, row);
        ui_dirty = grid_dirty = 1u;
    }
    m->energy = e;
}
/* SEQ 8: K1 the SOURCE, K2 the SEED of the next band, the next part; K3 the seed of the pattern the selected track
 * plays, K4 its variation: turned, the pattern is made again at once (the first turn is an edit UNDO takes back; one
 * after two seconds, or on another pattern, an edit of its own) */
static uint8_t th_knob_t = 255u, th_knob_pat;
static uint32_t th_knob_ms;
static void th_knobs(uint32_t t, int32_t d1, int32_t d2, int32_t d3, int32_t d4, int32_t f2, int32_t f3)
{
    char *p = msg_buf;
    uint8_t pat = tr[t].pattern, again = 0u;
    sq_thpat_t *m = &project.th.pat[t][pat];
    if (d1) {
        project.th.src = change_u8(project.th.src, d1, 0u, SQ_SRCS - 1u);
        status_msg(project.th.src == SQ_SRC_FREE ? "SOURCE FREE: MADE BY THE RULES OF NO GENRE" :
                   project.th.src == SQ_SRC_THEORY ? "SOURCE THEORY: MADE BY THE GENRE'S RULES" : "SOURCE LIBRARY: THE PATTERNS ARE LOADED");
    }
    if (d2) {
        project.th.seed = (uint16_t)kstep(project.th.seed, d2, f2, 0, (int32_t)SQ_TH_SEEDS - 1);
        status_num("NEXT SEED ", (uint32_t)project.th.seed + 1u);
    }
    if (!d3 && !d4) return;
    if (!m->style || track_tape(t) || track_break(t)) {
        status_msg(project.th.src != SQ_SRC_LIBRARY ? "NOT A PATTERN OF THE ENGINES: BEAT MAKES ONE" : "SOURCE LIBRARY: K1 FOR THEORY");
        return;
    }
    if (th_knob_t != t || th_knob_pat != pat || time_due(fm1_ms, th_knob_ms)) { undo_begin(); undo_add((uint8_t)t, pat); }
    th_knob_t = (uint8_t)t; th_knob_pat = pat; th_knob_ms = fm1_ms + 2000u;
    if (d3) {                                            /* another seed: a new pattern, made by the engines of now */
        uint8_t n = th_make((uint8_t)t, pat, SQ_THP_STYLE(m), m->func, (uint16_t)kstep(m->seed, d3, f3, 0, (int32_t)SQ_TH_SEEDS - 1), 0u, 0u,
                            vg_energy_now(), made_len(t));
        made_fit(t, pat, n);
        again = n;
    }
    if (d4) {                                            /* another variation of it: by the engines it was made by */
        m->var = (uint8_t)clamp_i32((int32_t)m->var + d4, 0, 99);
        m->vary = (uint8_t)((m->vary & SQ_THPV_NOTES) | (m->var ? tool_heat : 0u));
        again = th_again((uint8_t)t, pat);
    }
    if (again) {
        activate_row(t, project.step[t][pat]);
        if (tr[t].step >= project.track[t].length) tr[t].step = 0u;
        th_made |= (uint16_t)(1u << t);                  /* (0.25: another seed, another variation: the parts that answer it too) */
    }
    p = put_s(p, sq_func_name(m->func)); p = put_s(p, " SEED "); p = put_u(p, (uint32_t)m->seed + 1u);
    if (m->var) { p = put_s(p, " VAR "); p = put_u(p, m->var); p = put_s(p, " ("); p = put_u(p, SQ_THP_VARY(m)); p = put_s(p, " %)"); }
    finish(p);
    status_msg(msg_buf);
}
/* a progression by the rules of a style, from a seed of the dice, into the DICE / PI slot, which plays */
static void th_prog_dice(uint8_t style)
{
    sq_th_t h;
    piprog_leave();
    th_set(&h, style, (uint16_t)grand(SQ_TH_SEEDS), 0u, 0u, vg_energy_now(), 0u, 0u, SQ_FUNC_KICK);
    sq_th_prog(&project.uprog[SQ_UPROGS], &h);
    project.gen.harm_prog = SQ_PROG_PI;
    project.gen.harm_on = 1u;
}
/* GENRE LIVE: a pattern of the engines made again in the new genre's style, from the same seed (the new genre's part
 * for it: a CLAP where it has no SNARE). The SOURCE on FREE: the engines are free of the genre, the pattern stays as it
 * is. 0: not the engines' (the library reloads it) */
static void beat_cfg_for(const sq_track_cfg_t *c, uint8_t genre, uint8_t func, uint8_t n, uint8_t note, beat_cfg_t *o);
static void beat_cfg_apply(uint8_t t, uint8_t pat, const beat_cfg_t *o);
static uint8_t th_restyle(uint8_t t, uint8_t pat, uint8_t genre)
{
    sq_thpat_t *m = &project.th.pat[t][pat];
    sq_track_cfg_t *c = &project.track[t];
    uint8_t style = th_style_now(genre), fn, n;
    beat_cfg_t o;
    if (!m->style || style == 255u) return 0u;
    if (project.th.src == SQ_SRC_FREE) return 1u;       /* the SOURCE is free of the genre: a change of genre leaves the engines' patterns as they are */
    fn = style == SQ_TH_FREE ? m->func : sq_genre_part_for(genre, m->func);
    if (fn == 255u || fn >= SQ_FUNCS) fn = m->func;
    n = th_make_as(t, pat, style, fn);                   /* (0.26: by the engines it was made by) */
    if (!n) return 0u;
    made_fit(t, pat, n);
    beat_cfg_for(c, genre, fn, n, th_note(t, fn), &o);
    if (style == SQ_TH_FREE) { o.swing = SQ_SWING_MIN; o.groove = SQ_GROOVE_OFF; o.groove_amt = 0u; }   /* (no genre: no feel of one) */
    beat_cfg_apply(t, pat, &o);
    c->src_func = fn; c->src_genre = genre;
    harm_follow_genre(genre);
    track_loaded(t);
    return 1u;
}

/* a pattern of the library onto pattern `pat` of track t; `cfg` (may be 0): what the track should become, applied now
 * when `apply` (BEAT), kept for later when not (0.9: a proposal). Returns the steps, 0 if there is no such pattern.
 * 0.23: `style` is where it comes from - 255 the library, else the engines make it in that style (th_style_now) */
static uint8_t beat_onto_s(uint8_t t, uint8_t pat, uint8_t genre, uint8_t func, uint8_t var, uint8_t apply, beat_cfg_t *cfg, uint8_t style)
{
    sq_track_cfg_t *c = &project.track[t];
    uint8_t pi = pat < SQ_PATTERNS ? pat : tr[t].pattern;
    sq_step_t *row = project.step[t][pi];
    uint8_t nv, n, melodic = sq_func_kind(func) != SQ_KIND_DRUM, note = melodic ? gen_root_note(t) : PEN(t);
    beat_cfg_t o;
    if (func == SQ_FUNC_PROG || func == SQ_FUNC_KIT || func >= SQ_FUNCS) return 0u;
    nv = sq_beat_variants(genre, func);
    if (style != 255u) {                                 /* 0.23 THEORY: made, from the seed `var` after the one SEQ 8 K2 shows */
        n = th_make(t, pi, style, func, (uint16_t)(((uint32_t)project.th.seed + var) % SQ_TH_SEEDS), 0u, 0u, vg_energy_now(), made_len(t));
        if (!nv) nv = 1u;                                /* (any part: the engines make them all) */
    } else {
        if (!nv) return 0u;
        n = sq_beat_load_for(row, genre, func, (uint8_t)(var % nv), note, made_len(t), lib_phrase());   /* 0.24: for the track's length (0.25: its bars) */
        if (n) project.th.pat[t][pi].style = 0u;        /* (the library's: not the engines' any more) */
    }
    if (!n) return 0u;
    made_fit(t, pi, n);                                  /* 0.24: the track keeps its length: the pattern again in what it has more */
    beat_cfg_for(c, genre, func, n, note, &o);
    if (style == SQ_TH_FREE) { o.swing = SQ_SWING_MIN; o.groove = SQ_GROOVE_OFF; o.groove_amt = 0u; }   /* (no genre: no feel of one) */
    if (apply) {
        beat_cfg_apply(t, pi, &o);
        th_made |= (uint16_t)(1u << t);                               /* 0.25: the parts that answer this one answer it again */
        c->src_func = func; c->src_var = (uint8_t)(var % nv);        /* 0.10: GENRE LIVE knows where it came from */
        c->src_genre = genre;                                         /* 0.11: and COOK which genre's next variation */
        if (!c->role) c->role = sq_func_role(func);                   /* the library gives the track its role */
        harm_follow_genre(genre);                                     /* 0.11: something of this genre plays: its progressions */
        track_loaded(t);                                              /* 0.11: the new loop in time with the clock */
    }
    if (cfg) *cfg = o;
    return n;
}
static uint8_t beat_onto_x(uint8_t t, uint8_t pat, uint8_t genre, uint8_t func, uint8_t var, uint8_t apply, beat_cfg_t *cfg)
{
    return beat_onto_s(t, pat, genre, func, var, apply, cfg, th_style_now(genre));   /* (the SOURCE says: SEQ 8 K1) */
}

static void beat_onto(uint8_t t, uint8_t func, uint8_t var)
{
    if (func == SQ_FUNC_PROG) { prog_onto(t, var); return; }
    beat_onto_x(t, tr[t].pattern, beat_genre, func, var, 1u, 0);
}

/* 0.11 BAND (SEQ + SEL + black 7) and KIT (SEQ + black 7): the genre's band - KIT: its drums - on the tracks. Each part
 * goes to the track that has its role (HOME 4 K2: the player decides where a part plays), else to a free track: one
 * with no role, an empty one first, from the first track of the bank (KIT: from the selected track) round the 16, never
 * a TAPE track. The track's CHANNEL is never touched. Its NOTE is set only on a track that had no role and nothing
 * written (the part's General MIDI drum, or its register): the drums and the sounds the player chose stay theirs.
 * Every part plays variation `beat_var` of its own (or the last it has). */
static uint8_t row_written(uint32_t t)
{
    const sq_step_t *row = project.step[t][tr[t].pattern];
    uint32_t i;
    for (i = 0; i < SQ_STEPS; i++) if (row[i].flags & (SQ_STEP_ON | SQ_STEP_SET)) return 1u;
    return 0u;
}
static void band_load(uint8_t drums_only)
{
    char *p = msg_buf;
    uint8_t parts[SQ_PARTS_MAX], dest[SQ_BAND_MAX], nb = sq_genre_band(beat_genre), i, v = beat_var, done = 0u, skipped = 0u, pass, k;
    uint8_t first = drums_only ? selected_track : (uint8_t)(selected_track & 8u), style = th_style_now(beat_genre);
    uint16_t used = 0u, seed = project.th.seed;
    sq_genre_parts(beat_genre, parts);
    if (style != 255u) nb = sq_th_band(style, parts);    /* 0.23 THEORY: the style's band (GENRE FREE: a band of no genre), all of one seed */
    if (!nb) return;
    if (!project.gen.harm_on && !drums_only) project.gen.harm_on = 1u;   /* (before the loads: the melodic parts FOLLOW) */
    for (i = 0; i < nb; i++) {                                           /* the tracks that have the part's role */
        uint8_t role = sq_func_role(parts[i]);
        dest[i] = 255u;
        if (drums_only && sq_func_kind(parts[i]) != SQ_KIND_DRUM) continue;
        for (k = 0; k < SQ_TRACKS; k++) if (project.track[k].role == role && !(used & (1u << k)) && !track_tape(k)) { dest[i] = k; used |= (uint16_t)(1u << k); break; }
    }
    for (pass = 0; pass < 2u; pass++)                                    /* free tracks: the empty ones first */
        for (i = 0; i < nb; i++) {
            if (dest[i] != 255u || (drums_only && sq_func_kind(parts[i]) != SQ_KIND_DRUM)) continue;
            for (k = 0; k < SQ_TRACKS; k++) {
                uint8_t tt = (uint8_t)((first + k) % SQ_TRACKS);
                if (project.track[tt].role || (used & (1u << tt)) || track_tape(tt) || (!pass && row_written(tt))) continue;
                dest[i] = tt; used |= (uint16_t)(1u << tt); break;
            }
        }
    undo_begin();
    for (i = 0; i < nb; i++) {
        uint8_t tt = dest[i], fn = parts[i], nv = sq_beat_variants(beat_genre, fn);
        if (drums_only && sq_func_kind(fn) != SQ_KIND_DRUM) continue;
        if (style != 255u && !nv) nv = 1u;
        if (tt == 255u || !nv) { skipped++; continue; }
        undo_add(tt, tr[tt].pattern);
        if (!row_written(tt) && PEN(tt) == 60u) PEN(tt) = start_note(fn, sq_part_note(beat_genre, fn));   /* a new track (nothing written, its note the default): a starting note */
        beat_onto(tt, fn, (uint8_t)(style != 255u ? 0u : v < nv ? v : nv - 1u));
        activate_row(tt, project.step[tt][tr[tt].pattern]);
        done++;
    }

    p = put_s(p, style == SQ_TH_FREE ? "FREE" : sq_genre_name(beat_genre));
    if (style != 255u) { p = put_s(p, drums_only ? " KIT SEED " : " BAND SEED "); p = put_u(p, (uint32_t)seed + 1u); }
    else { p = put_s(p, drums_only ? " KIT #" : " BAND #"); p = put_u(p, (uint32_t)v + 1u); }
    p = put_s(p, ": "); p = put_u(p, done); p = put_s(p, " TRACKS");
    if (skipped) { p = put_s(p, ", "); p = put_u(p, skipped); p = put_s(p, " NO ROOM"); }
    finish(p);
    status_msg(msg_buf);
    if (style != 255u) project.th.seed = (uint16_t)((seed + 1u) % SQ_TH_SEEDS);   /* (pressed again: the next seed, another band) */
    else beat_var = (uint8_t)((v + 1u) % SQ_BEAT_VARS);
    ui_dirty = grid_dirty = 1u;
}
static void beat_kit(void) { band_load(1u); }
static uint8_t pipat_count(uint8_t g, uint8_t f);             /* sagga_pipat.c: 0.11 */
static void pipat_get(uint8_t t, uint8_t g, uint8_t f, uint16_t idx);
static void beat_band(void) { band_load(0u); }

/* ---- the tools */
static void dice_answer(uint8_t keep);
static uint8_t dice_pending;

/* 0.11 COOK on a track that came from the library walks it towards the NEXT variation of its part (they are in order
 * of likeness: small steps): HEAT says how many steps change a press, the weak places first, the one of the bar last.
 * When it is there, the track IS that variation, and the next press walks on to the one after (round to the first).
 * A track written by hand, a TAPE track, or SEQ + SEL + COOK (cook_random): the 0.10 COOK, at random. */
static uint8_t cook_random;                    /* the next COOK is the random one (SEL held; kept if it waits for the bar) */
static uint8_t cook_said;                      /* cook_towards wrote the message: tool_status keeps quiet */
typedef struct { uint8_t on, pat, base, next, vary; uint16_t seed; } th_walk_t;   /* 0.23: where a COOK of the engines is going */
static th_walk_t th_walk[SQ_TRACKS];
static uint8_t cook_towards(uint8_t t)
{
    static sq_step_t target[SQ_STEPS];
    sq_track_cfg_t *c = &project.track[t];
    sq_step_t *row = project.step[t][tr[t].pattern];
    uint8_t g = c->src_genre < SQ_GENRES ? c->src_genre : beat_genre, fn = c->src_func, nv, next, left, steps, len = c->length, n, i;
    char *p = msg_buf;
    sq_row_keep(row);                                    /* 0.24: the walk moves the steps of the loop, the copies as any other */
    {   /* 0.23 THEORY: a pattern of the engines walks to the next variation of its own seed; HEAT says how large the
         * variation is (and, as for the library, how many steps move a press). A variation that is the pattern as it
         * is - a part with little to vary, a small HEAT - is passed over: the next ones, then larger ones, until one
         * differs. The walk keeps its target until it is there. */
        sq_thpat_t *m = &project.th.pat[t][tr[t].pattern];
        if (m->style && !track_tape(t)) {
            sq_th_t h;
            th_walk_t *wk = &th_walk[t];
            uint8_t vy = tool_heat, tries, found = 0u;
            if (wk->on && wk->pat == tr[t].pattern && wk->base == m->var && wk->seed == m->seed) {   /* the walk goes on */
                next = wk->next; vy = wk->vary;
                th_set_as(&h, m, next, vy, m->energy, t, tr[t].pattern);       /* (0.26: the same engines, the same bar: only the variation moves) */
                n = th_load_as(target, &h, m, t);
                found = n ? 1u : 0u;
            }
            for (tries = 0; tries < 8u && !found; tries++) {
                uint32_t r = sq_rng_state;               /* (looking only: the dice's numbers stay where they are) */
                next = (uint8_t)(1u + ((uint32_t)m->var + tries % 3u) % 250u);
                vy = (uint8_t)(tries < 3u ? tool_heat : tries < 6u ? (tool_heat > 60u ? tool_heat : 60u) : 100u);
                th_set_as(&h, m, next, vy, m->energy, t, tr[t].pattern);
                n = th_load_as(target, &h, m, t);                         /* (0.25: in the metre's bars) */
                if (!n) break;
                for (i = n; i < len; i++) target[i] = target[i % n];
                if (sq_row_approach(row, target, len, 0u, &r)) found = 1u;
            }
            if (found) {
                for (i = n; i < len; i++) target[i] = target[i % n];
                steps = (uint8_t)(1u + ((uint32_t)tool_heat * len) / 800u);
                left = sq_row_approach(row, target, len, steps, &sq_rng_state);
                wk->on = left ? 1u : 0u; wk->pat = tr[t].pattern; wk->base = m->var; wk->next = next; wk->vary = vy; wk->seed = m->seed;
                if (!left) { m->var = next; m->vary = (uint8_t)((m->vary & SQ_THPV_NOTES) | h.vary); if (!h.gen) m->metre = metre_id_now(); sq_row_again(row, 0u, n, len); }   /* (there: the pattern and its copies again; 0.26: one made in its bar keeps its metre) */
                p = put_s(p, "COOK "); p = put_s(p, sq_func_name(m->func)); p = put_s(p, " VAR "); p = put_u(p, next);
                if (left) { p = put_s(p, ": "); p = put_u(p, left); p = put_s(p, " TO GO"); }
                else p = put_s(p, " REACHED");
            } else {
                p = put_s(p, "COOK "); p = put_s(p, sq_func_name(m->func)); p = put_s(p, ": NOTHING TO VARY IN IT");
            }
            finish(p);
            status_msg(msg_buf);
            cook_said = 1u;
            return 1u;
        }
    }
    if (fn >= SQ_FUNCS || fn == SQ_FUNC_KIT || track_tape(t)) return 0u;
    nv = sq_beat_variants(g, fn);
    if (nv < 2u) return 0u;
    next = (uint8_t)((c->src_var + 1u) % nv);
    if (fn == SQ_FUNC_PROG) {
        uint8_t center = PEN(t) >= 48u && PEN(t) <= 72u ? PEN(t) : 60u;
        n = sq_beat_chords(target, g, next, gen_root(t), gen_scale(), center);
    } else {
        uint8_t note = sq_func_kind(fn) != SQ_KIND_DRUM ? gen_root_note(t) : PEN(t);
        n = sq_beat_load_for(target, g, fn, next, note, made_len(t), 1u);   /* 0.24: for the track's length, as a phrase (as 0.11 did at 32 and 64) */
    }
    n = made_rebar(target, n);                                   /* (0.25: in the metre's bars) */
    if (!n) return 0u;
    for (i = n; i < len; i++) target[i] = target[i % n];         /* (a length of the player's: the variation repeats) */
    steps = (uint8_t)(1u + ((uint32_t)tool_heat * len) / 800u);
    left = sq_row_approach(row, target, len, steps, &sq_rng_state);
    if (!left) { c->src_var = next; sq_row_again(row, 0u, n, len); }   /* (there: the pattern and its copies again) */
    p = put_s(p, "COOK "); p = put_s(p, sq_func_name(fn)); p = put_s(p, " #"); p = put_u(p, (uint32_t)next + 1u);
    if (left) { p = put_s(p, ": "); p = put_u(p, left); p = put_s(p, " TO GO"); }
    else p = put_s(p, " REACHED");
    finish(p);
    status_msg(msg_buf);
    cook_said = 1u;
    return 1u;
}

/* 0.24: A GENERATOR ON A LOOP LONGER THAN A BAR MAKES A PHRASE - not the bar again, and not 64 steps of chance: the
 * bar it made (A, the first 16 steps of `part`) is answered. Two bars: A A'. Three: A A' B. Four: A A' A B. A' is the
 * ANSWER: the bar with its second half cooked (by the track's role, in the key: COOK's own rules, the beats the last
 * to go). B is the TURN of the phrase: all of the bar but its first beat cooked, harder. HEAT says how much both. A bar
 * the cook left as it was gets a pickup at its end (or loses the one it had): an answer is never the question again.
 * A loop that is not a number of bars ends on the beginning of the next one. The steps are the track's own. */
static uint32_t bar_hits(const sq_step_t *bar, uint8_t n)
{
    uint32_t m = 0u;
    uint8_t k;
    for (k = 0; k < n && k < 32u; k++) if (bar[k].flags & SQ_STEP_ON) m |= (uint32_t)1u << k;
    return m;
}
static void phrase_pickup(sq_step_t *bar, uint8_t n)
{
    uint8_t k, r;
    for (k = n; k-- > 0u;) {
        sq_step_t *s = &bar[k];
        if (!(sq_g16(k) & 3u) || (s->flags & SQ_STEP_LOCK)) continue;   /* (never a beat - 0.25: of the metre's -, never a locked step) */
        if (s->flags & SQ_STEP_ON) { s->flags &= (uint8_t)~SQ_STEP_ON; return; }
        for (r = k; r-- > 0u;) if (bar[r].flags & SQ_STEP_ON) break;      /* the hit before it: the pickup plays what it plays */
        if (r >= n) return;                                          /* (none: an empty bar has no answer) */
        *s = bar[r];
        s->flags = (uint8_t)((s->flags & ~(SQ_STEP_TIE | SQ_STEP_SLIDE | SQ_STEP_LOCK)) | SQ_STEP_ON);
        s->velocity = (uint8_t)(bar[r].velocity > 54u ? ((uint32_t)bar[r].velocity * 3u) / 4u : 40u);
        s->ratchet = 1u;
        if (s->length > 50u) s->length = 50u;
        return;
    }
}
static void gen_phrase(uint8_t t, sq_step_t *part, uint8_t len)
{
    uint8_t bs = bar_st(), bars = (uint8_t)((len + bs - 1u) / bs), b, drum = track_drum(t), role = gen_role(t);   /* (0.25: the metre's bars) */
    for (b = 1; b < bars; b++) {
        sq_step_t *bar = part + (uint32_t)bs * b;
        uint8_t n = (uint8_t)(len - bs * b > bs ? bs : len - bs * b), last = (uint8_t)(b + 1u == bars && bars >= 3u);
        uint8_t from = bar_beat_le((uint8_t)(last ? n / 4u : n / 2u)), heat = (uint8_t)(last ? 35u + tool_heat / 2u : 25u + tool_heat / 3u);
        uint8_t base;
        uint32_t was;
        memcpy(bar, part, (uint32_t)n * sizeof(sq_step_t));
        if (!(b & 1u) && !last) continue;                        /* (the third bar of four: A as it is) */
        if (from >= n) continue;
        was = bar_hits(bar, n);
        base = sq_grid_from(from);                               /* (the cook's row begins at the bar's step `from`) */
        if (genre_feel()) sq_row_cook_role(bar + from, (uint8_t)(n - from), heat, role, gen_root(t), gen_scale(), &sq_rng_state);
        else sq_row_cook(bar + from, (uint8_t)(n - from), heat, &sq_rng_state);
        if (!drum && (!genre_feel() || role == SQ_ROLE_NONE || role == SQ_ROLE_ARP))
            sq_row_cook_notes(bar + from, (uint8_t)(n - from), heat, gen_root(t), gen_scale(), &sq_rng_state);
        sq_grid_from(base);
        if (bar_hits(bar, n) == was) phrase_pickup(bar, n);
    }
}

static void tool_one(uint8_t tool, uint8_t t)
{
    sq_track_cfg_t *cfg = &project.track[t];
    sq_step_t *row = project.step[t][tr[t].pattern];
    uint8_t lo = cfg->start, len = (uint8_t)(cfg->length - cfg->start), tg = project.gen.targets, drum = track_drum(t);
    uint8_t own = sq_row_own(row, lo, cfg->length), bar = (uint8_t)(len > bar_st() ? bar_st() : len);   /* (0.25: the metre's bar) */
    sq_step_t *part = row + lo;
    uint32_t i;
    if (track_break(t) && (tool == TOOL_RAND || tool == TOOL_COOK)) {   /* 0.12: a break's dice, the chop after */
        if (tool == TOOL_RAND) sq_brk_dice(row, cfg->start, cfg->length, PEN(t), brk_slices(t), (uint8_t)SQ_BRK_SWAP(cfg->brk_cfg), (uint8_t)SQ_BRK_ROLL(cfg->brk_cfg), tool_heat, &sq_rng_state);
        else {                                                     /* COOK: the genre's chops, one after the other (held: one of them at random) */
            cfg->brk_chop = brk_cook_chop(t, cook_random);
            sq_brk_apply(row, cfg->start, cfg->length, cfg->brk_chop, PEN(t), brk_slices(t));
            if (t == selected_track) { brk_cook_say(t); cook_said = 1u; }   /* "END ROLL (JUNGLE 2/7)" */
        }
        activate_row(t, row);
        if (tr[t].step >= cfg->length || tr[t].step < cfg->start) tr[t].step = cfg->start;
        return;
    }
    /* 0.24: a tool works on the loop as it sounds, the copies steps as any other. After it, a loop that is still the
     * pattern and its rounds (turned, shifted, cleared: it is) has its copies again; one that is not is the player's */
    if (tool != TOOL_COOK || cook_random) sq_row_keep(row);          /* (COOK towards a variation: cook_towards) */
    switch (tool) {
    case TOOL_CLEAR: sq_row_clear(row); break;
    case TOOL_REV:   sq_row_reverse(part, len); break;
    case TOOL_SHL:   sq_row_shift(part, len, -1); break;
    case TOOL_SHR:   sq_row_shift(part, len, 1); break;
    case TOOL_RAND:                                                  /* 0.24: a bar of chance, then its phrase (gen_phrase) */
        sq_row_random(part, bar, tool_density, &sq_rng_state);
        if ((tg & SQ_GT_NOTES) && !drum) sq_row_random_notes(part, bar, PEN(t), gen_root(t), gen_scale(), &sq_rng_state);
        if (!drum) sq_row_phrase_gates(part, bar, gen_role(t), tool_heat, &sq_rng_state);   /* 0.11: the lengths, by the role */
        gen_phrase(t, part, len);
        if (tg & SQ_GT_CC) sq_row_random_lanes(part, len, tool_density, gen_lanes(t), &sq_rng_state);
        if (tg & SQ_GT_LFO) lfo_dice(t, tool_heat);
        break;
    case TOOL_EUC:   sq_row_rhythm(part, len, cfg->euc_fam, cfg->euc_pulses, cfg->euc_rot);   /* (the grid's WRITE EUCLID) */
        if (!drum) sq_row_phrase_gates(part, len, gen_role(t), tool_heat, &sq_rng_state);
        break;
    case TOOL_COOK:                                      /* 0.10: by the track's role when the genre is minded */
        if (!cook_random && cook_towards(t)) break;     /* 0.11: towards the next variation */
        if (genre_feel()) sq_row_cook_role(part, len, tool_heat, gen_role(t), gen_root(t), gen_scale(), &sq_rng_state);
        else sq_row_cook(part, len, tool_heat, &sq_rng_state);
        if ((tg & SQ_GT_NOTES) && !drum && (!genre_feel() || gen_role(t) == SQ_ROLE_NONE || gen_role(t) == SQ_ROLE_ARP))
            sq_row_cook_notes(part, len, tool_heat, gen_root(t), gen_scale(), &sq_rng_state);
        if (tg & SQ_GT_CC) sq_row_cook_lanes(part, len, tool_heat, gen_lanes(t), cfg->lane_base, &sq_rng_state);
        if (tg & SQ_GT_LFO) lfo_cook(t, tool_heat);
        break;
    case TOOL_INVERT: sq_row_invert(part, len); break;
    case TOOL_HUMAN:  sq_row_humanize(part, len, &sq_rng_state); break;
    case TOOL_WRITE:  for (i = 0; i < len; i++) part[i].flags |= SQ_STEP_ON; break;   /* (not reached: live_write) */
    default: break;
    }
    if (tool != TOOL_COOK && tool != TOOL_HUMAN && tool != TOOL_WRITE) th_forget(t, tr[t].pattern);   /* 0.23: cleared, turned, written at random: the player's */
    if (own && own < cfg->length && (tool != TOOL_COOK || cook_random)) sq_row_again(row, lo, own, cfg->length);
    gh_st[t].pat = 255u;
    activate_row(t, row);
    if (tr[t].step >= cfg->length || tr[t].step < cfg->start) tr[t].step = cfg->start;
}

static void tool_status(uint8_t tool, uint16_t mask)
{
    char *p = msg_buf;
    if (tool == TOOL_COOK && cook_said && mask == (uint16_t)(1u << selected_track)) return;   /* 0.11: COOK said where it goes */
    p = put_s(p, TOOL_NAME[tool]);
    if (mask != (uint16_t)(1u << selected_track)) { p = put_s(p, ": "); p = put_s(p, SCOPE_NAME[project.gen.scope]); p = put_s(p, " ("); p = put_u(p, popcount16(mask)); p = put_s(p, ")"); }
    finish(p);
    status_msg(msg_buf);
}

static void tool_apply_x(uint8_t tool, uint8_t now);
static uint8_t tool_every_now;                         /* 0.27: the tool running is EVERY's repeat */
static void dice_roll(uint8_t kind);
static const uint8_t WHEN_BARS[SQ_WHENS] = {0u, 1u, 2u, 4u, 8u, 16u};
static const uint8_t EVERY_BARS[SQ_EVERYS] = {0u, 1u, 2u, 4u, 8u, 16u, 32u};
/* 0.10: the tools that change a pattern can wait for a bar line (WHEN) and come back every so many bars (EVERY) */
static uint8_t tool_schedulable(uint8_t tool)
{
    return (tool == TOOL_UNDO || tool == TOOL_COPY || tool == TOOL_WRITE || tool == TOOL_EUC) ? 0u : 1u;
}
static void every_arm(void)
{
    uint8_t e = project.gen.every < SQ_EVERYS ? project.gen.every : 0u;
    char *p = msg_buf;
    if (!e) { status_msg("EVERY OFF"); return; }
    every_next_bar = (bar_no() / EVERY_BARS[e] + 1u) * EVERY_BARS[e];
    p = put_s(p, "EVERY "); p = put_u(p, EVERY_BARS[e]); p = put_s(p, EVERY_BARS[e] == 1u ? " BAR: " : " BARS: ");
    p = put_s(p, project.gen.every_tool < TOOL_COUNT ? TOOL_NAME[project.gen.every_tool] : "THE NEXT TOOL YOU USE"); finish(p);
    status_msg(msg_buf);
}
static void tool_bar_tick(void)                         /* every bar line: the tool that waited, the one that repeats, GENRE LIVE */
{
    uint32_t bar = bar_no(), t;
    uint8_t e = project.gen.every < SQ_EVERYS ? project.gen.every : 0u;
    if (genre_reload_pend) {
        undo_begin();
        for (t = 0; t < SQ_TRACKS; t++) {
            sq_track_cfg_t *c = &project.track[t];
            if (!(genre_reload_pend & (1u << t)) || c->src_func == 255u || track_tape(t)) continue;
            undo_add((uint8_t)t, tr[t].pattern);
            if (th_restyle((uint8_t)t, tr[t].pattern, beat_genre)) { }   /* 0.23: the engines' own, in the new style, from its seed */
            else if (c->src_func == SQ_FUNC_PROG) prog_onto_x((uint8_t)t, tr[t].pattern, beat_genre, c->src_var, 1u, 0);
            else {                                        /* 0.11: the new genre's part for it (a CLAP where it has no SNARE ...) */
                uint8_t fn = sq_genre_part_for(beat_genre, c->src_func);
                /* (0.23: the SOURCE on FREE has nothing to say about a genre: a track of the library takes the new
                 *  genre's part from the library, as it always did) */
                if (fn != 255u) beat_onto_s((uint8_t)t, tr[t].pattern, beat_genre, fn, c->src_var, 1u, 0,
                                            project.th.src == SQ_SRC_FREE ? 255u : th_style_now(beat_genre));
            }
            activate_row(t, project.step[t][tr[t].pattern]);
            if (tr[t].step >= c->length) tr[t].step = 0u;
        }
        genre_reload_pend = 0u;
        ui_dirty = grid_dirty = 1u;
    }
    if (tool_due_tool < TOOL_COUNT && bar >= tool_due_bar) { uint8_t tl = tool_due_tool; tool_due_tool = 255u; tool_apply_x(tl, 1u); }
    if (e && project.gen.every_tool < TOOL_COUNT && bar >= every_next_bar) {
        every_next_bar = bar + EVERY_BARS[e];
        tool_every_now = 1u;                              /* (0.27: RANDOM repeated by EVERY is the tool, not a roll to answer) */
        tool_apply_x(project.gen.every_tool, 1u);
        tool_every_now = 0u;
    }
}
static void tool_apply(uint8_t tool)
{
    if (tool >= TOOL_COUNT) return;
    if (tool_schedulable(tool)) {
        project.gen.every_tool = tool;                    /* EVERY repeats the last tool used */
        if (project.gen.when && playing && !track_tape(selected_track)) {   /* WHEN: at the bar line asked */
            uint32_t bar = bar_no(), n = WHEN_BARS[project.gen.when < SQ_WHENS ? project.gen.when : SQ_WHEN_BAR];   /* (never 0 bars: n divides) */
            char *p = msg_buf;
            tool_due_tool = tool;
            tool_due_bar = (bar / n + 1u) * n;
            p = put_s(p, TOOL_NAME[tool]); p = put_s(p, " IN "); p = put_u(p, tool_due_bar - bar); p = put_s(p, tool_due_bar - bar == 1u ? " BAR" : " BARS"); finish(p);
            status_msg(msg_buf);
            ui_dirty = grid_dirty = 1u;
            return;
        }
    }
    tool_apply_x(tool, 0u);
}
static void tool_apply_x_(uint8_t tool, uint8_t now);
static void tool_apply_x(uint8_t tool, uint8_t now)
{
    cook_said = 0u;
    tool_apply_x_(tool, now);
    if (tool == TOOL_COOK) cook_random = 0u;               /* (SEQ + SEL + COOK: this one only) */
}
static void tool_apply_x_(uint8_t tool, uint8_t now)
{
    uint8_t t = selected_track, pat = tr[selected_track].pattern;
    sq_track_cfg_t *cfg = &project.track[t];
    uint8_t lo = cfg->start, len = (uint8_t)(cfg->length - cfg->start);
    sq_step_t *row = project.step[t][pat], *part = row + lo;
    uint16_t mask = gen_mask();
    uint32_t k;
    (void)now;
    if (tool >= TOOL_COUNT) return;
    if (track_tape(t) && tool != TOOL_UNDO) { tape_tool(t, tool); return; }   /* 0.11 */
    if (tool == TOOL_EUC) { euclid_toggle(); return; }                   /* 0.8: EUCLID LIVE on / off (the scope) */
    if (tool == TOOL_WRITE) { if (dice_pending) dice_answer(1u); live_write(); return; }   /* 0.8: WRITE what is heard */
    if (tool == TOOL_RAND && !tool_every_now) { dice_roll(DICE_RANDOM); return; }   /* 0.27: RANDOM is a roll: OCT+ keeps it, OCT- puts it back, ALG goes through the rolls */
    if (tool == TOOL_UNDO && dice_pending) { dice_answer(0u); return; }   /* 0.5.1: UNDO with a dice waiting: BACK */
    if (dice_pending) dice_answer(1u);                    /* a tool after a dice: the dice is kept */
    if (tool == TOOL_UNDO) { undo_swap(); return; }
    if (tool == TOOL_COPY) {
        memcpy(clip_row, part, (uint32_t)len * sizeof(sq_step_t));
        for (k = 0; k < len; k++) clip_row[k].flags &= (uint8_t)~SQ_STEP_GHOST;   /* 0.24: what is pasted is the player's */
        clip_len = len; clip_valid = 1u;
        status_num("COPIED STEPS ", len);
        return;
    }
    if (tool == TOOL_PASTE && !clip_valid) { status_msg("NOTHING COPIED"); return; }
    if (tool == TOOL_PASTE || tool == TOOL_DOUBLE) {      /* (these two: the selected track only) */
        undo_begin();
        undo_add(t, pat);
        th_forget(t, pat);                               /* 0.23 */
        if (tool == TOOL_PASTE) {
            uint8_t n = clip_len < (uint8_t)(SQ_STEPS - lo) ? clip_len : (uint8_t)(SQ_STEPS - lo);
            memcpy(part, clip_row, (uint32_t)n * sizeof(sq_step_t));
            if (n > len) set_length(t, (uint8_t)(lo + n));          /* (0.3 lengthened it but copied only `len` steps) */
        } else {
            uint8_t nl;
            sq_row_keep(row);                            /* 0.24: DOUBLE writes steps: the loop as it sounds, twice, the player's */
            nl = sq_row_double(part, len, (uint8_t)(SQ_STEPS - lo));
            set_length(t, (uint8_t)(lo + nl));
        }
        activate_row(t, row);
        status_msg(TOOL_NAME[tool]);
        ui_dirty = grid_dirty = 1u;
        return;
    }
    if (tool == TOOL_BEAT && mask == (uint16_t)(1u << t)) {   /* BEAT on one track: the function chosen */
        uint8_t nv = sq_beat_variants(beat_genre, beat_func), v;
        char *p = msg_buf;
        if (beat_func == SQ_FUNC_KIT) { beat_kit(); return; }
        if (beat_func != SQ_FUNC_PROG && th_style_now(beat_genre) != 255u) {   /* 0.23 THEORY: the part made from the seed; again: the next seed */
            uint16_t seed = project.th.seed;
            undo_begin();
            undo_add(t, pat);
            if (!row_written(t) && PEN(t) == 60u) PEN(t) = start_note(beat_func, sq_part_note(beat_genre, beat_func));
            if (!beat_onto_x(t, pat, beat_genre, beat_func, 0u, 1u, 0)) { status_msg("NO PATTERN"); return; }
            project.th.seed = (uint16_t)((seed + 1u) % SQ_TH_SEEDS);
            p = put_s(p, th_style_now(beat_genre) == SQ_TH_FREE ? "FREE" : sq_genre_name(beat_genre)); p = put_s(p, " "); p = put_s(p, sq_func_name(beat_func));
            p = put_s(p, " SEED "); p = put_u(p, (uint32_t)seed + 1u);
            finish(p);
            activate_row(t, row);
            if (tr[t].step >= project.track[t].length) tr[t].step = 0u;
            status_msg(msg_buf);
            ui_dirty = grid_dirty = 1u;
            return;
        }
        if (!nv) { status_msg("NO PATTERN"); return; }
        if (beat_var >= nv && beat_func != SQ_FUNC_PROG) {   /* 0.11: one of the Pi's: asked, loaded when it comes */
            uint8_t npi = pipat_count(beat_genre, beat_func);
            pipat_get(t, beat_genre, beat_func, (uint16_t)(beat_var - nv));
            beat_var = (uint8_t)(beat_var + 1u < nv + npi ? beat_var + 1u : 0u);
            return;
        }
        undo_begin();
        undo_add(t, pat);
        if (beat_func == SQ_FUNC_PROG) {
            v = (uint8_t)(beat_var % nv);
            prog_onto(t, v);
            p = put_s(p, "PROG: TONIC CHORD, RHYTHM #"); p = put_u(p, (uint32_t)v + 1u);
            beat_var = (uint8_t)((v + 1u) % nv);
        } else {
            v = (uint8_t)(beat_var % nv);
            beat_onto(t, beat_func, v);
            p = put_s(p, sq_genre_name(beat_genre)); p = put_s(p, " "); p = put_s(p, sq_func_name(beat_func));
            p = put_s(p, " #"); p = put_u(p, (uint32_t)v + 1u);
            beat_var = (uint8_t)((v + 1u) % nv);
        }
        finish(p);
        activate_row(t, row);
        if (tr[t].step >= project.track[t].length) tr[t].step = 0u;
        status_msg(msg_buf);
        ui_dirty = grid_dirty = 1u;
        return;
    }
    if (tool == TOOL_PROG) {                              /* PROG: the tonic chord on the melodic tracks; the HARMONY plays */
        uint8_t any = 0u, nv = sq_beat_variants(beat_genre, SQ_FUNC_PROG);
        undo_begin();
        for (k = 0; k < SQ_TRACKS; k++) {
            if (!(mask & (1u << k)) || (track_drum(k) && mask != (uint16_t)(1u << k))) continue;
            undo_add((uint8_t)k, tr[k].pattern);
            prog_onto((uint8_t)k, (uint8_t)(nv ? beat_var % nv : 0u));
            activate_row(k, project.step[k][tr[k].pattern]);
            if (tr[k].step >= project.track[k].length) tr[k].step = 0u;
            any = 1u;
        }
        if (!any) { status_msg("PROG: NO MELODIC TRACK"); return; }
        harm_status();
        ui_dirty = grid_dirty = 1u;
        return;
    }
    undo_begin();
    if (tool == TOOL_BEAT) {                              /* BEAT on several: each track the part that fits it */
        uint8_t v = beat_var;
        for (k = 0; k < SQ_TRACKS; k++) {
            uint8_t fn;
            if (!(mask & (1u << k))) continue;
            undo_add((uint8_t)k, tr[k].pattern);
            fn = project.track[k].role ? sq_role_func(project.track[k].role) : sq_beat_role(track_drum(k), PEN(k));
            if (fn != SQ_FUNC_PROG && th_style_now(beat_genre) != SQ_TH_FREE) fn = sq_genre_part_for(beat_genre, fn);   /* 0.11: the genre's part for it */
            if (fn == 255u) continue;
            beat_onto((uint8_t)k, fn, (uint8_t)(th_style_now(beat_genre) != 255u && fn != SQ_FUNC_PROG ? 0u : v));   /* (THEORY: one seed for all) */
            activate_row(k, project.step[k][tr[k].pattern]);
            if (tr[k].step >= project.track[k].length) tr[k].step = 0u;
        }
        if (th_style_now(beat_genre) != 255u) project.th.seed = (uint16_t)((project.th.seed + 1u) % SQ_TH_SEEDS);
        else beat_var = (uint8_t)((v + 1u) % SQ_BEAT_VARS);
    } else {
        for (k = 0; k < SQ_TRACKS; k++) {
            if (!(mask & (1u << k))) continue;
            undo_add((uint8_t)k, tr[k].pattern);
            tool_one(tool, (uint8_t)k);
        }
    }
    tool_status(tool, mask);
    ui_dirty = grid_dirty = 1u;
}

/* ---- the dice: what they touch is kept at the first roll; OCT+ keeps the roll, OCT- puts it back. 0.8: the rolls are
 * remembered (16, by their seed: a roll is the same every time it is made again from what was there), and while a dice
 * waits, ALG goes back and forth through them; a new roll after going back forgets the ones after. */
#define DICE_HIST 16u
static uint8_t dice_kind;
static uint16_t dsnap_mask;
static sq_step_t dsnap_row[SQ_TRACKS][SQ_STEPS];    /* (0.30: in the RAM - the pool has the 16 snapshots, 32 scenes, 32 undo rows) */
static sq_track_cfg_t dsnap_cfg[SQ_TRACKS];
static sq_thpat_t dsnap_th[SQ_TRACKS];             /* 0.23: what the engines knew of each row */
static uint8_t dsnap_pat[SQ_TRACKS], dsnap_key[3], dsnap_harm[5];
static sq_lfo_t dsnap_lfo[SQ_LFOS];
static uint32_t dhist_seed[DICE_HIST];
static uint16_t dhist_mask[DICE_HIST];
static uint8_t dhist_kind[DICE_HIST], dhist_n, dhist_pos;

static void dice_save(uint16_t mask)
{
    uint32_t t;
    if (!dice_pending) {
        memcpy(dsnap_lfo, project.lfo, sizeof dsnap_lfo);
        dsnap_key[0] = project.key_root; dsnap_key[1] = project.key_scale; dsnap_key[2] = (uint8_t)project.key_shift;
        dsnap_harm[0] = project.gen.harm_on; dsnap_harm[1] = beat_genre;
        dsnap_harm[2] = project.gen.harm_prog; dsnap_harm[3] = project.gen.harm_bars; dsnap_harm[4] = project.gen.harm_genre;
        dsnap_mask = 0u;
    }
    for (t = 0; t < SQ_TRACKS; t++) {
        if (!(mask & ~dsnap_mask & (1u << t))) continue;
        dsnap_pat[t] = tr[t].pattern;
        dsnap_th[t] = project.th.pat[t][tr[t].pattern];
        memcpy(dsnap_row[t], project.step[t][tr[t].pattern], sizeof dsnap_row[t]);
        dsnap_cfg[t] = project.track[t];
        dsnap_mask |= (uint16_t)(1u << t);
    }
}

static void dice_restore(void)
{
    uint32_t t, l;
    for (t = 0; t < SQ_TRACKS; t++) {
        sq_track_cfg_t *c = &project.track[t], was;
        if (!(dsnap_mask & (1u << t))) continue;
        was = *c;
        memcpy(project.step[t][dsnap_pat[t]], dsnap_row[t], sizeof dsnap_row[t]);
        project.th.pat[t][dsnap_pat[t]] = dsnap_th[t];
        *c = dsnap_cfg[t];
        track_cfg_back(t, &was, dsnap_pat[t]);            /* 0.11: the loop as it was, in time (the explorer) */
        for (l = 0; l < SQ_LANES; l++)                    /* the synth's sound back as it was */
            if (c->lane_cc[l] != SQ_LANE_NONE && c->lane_base[l] != SQ_LANE_NONE) send_cc(track_ch(t), c->lane_cc[l], lane_val(l, c->lane_base[l]));
    }
    memcpy(project.lfo, dsnap_lfo, sizeof dsnap_lfo);
    memset(lfo_last_valid, 0, sizeof lfo_last_valid);
    project.key_root = dsnap_key[0]; project.key_scale = dsnap_key[1]; project.key_shift = (int8_t)dsnap_key[2];
    key_sync_slot();
    project.gen.harm_on = dsnap_harm[0]; beat_genre = dsnap_harm[1];
    project.gen.harm_prog = dsnap_harm[2]; project.gen.harm_bars = dsnap_harm[3]; project.gen.harm_genre = dsnap_harm[4];
}

static void dice_restore_locked(uint16_t mask)
{
    uint32_t t, i;
    for (t = 0; t < SQ_TRACKS; t++) if (mask & (1u << t)) {
        sq_step_t *row = project.step[t][dsnap_pat[t]];
        for (i = 0; i < SQ_STEPS; i++) if (dsnap_row[t][i].flags & SQ_STEP_LOCK) row[i] = dsnap_row[t][i];
    }
}

static void dice_answer(uint8_t keep)
{
    uint32_t t;
    if (!dice_pending) return;
    if (keep) {                                           /* kept: UNDO can still take it back (the patterns) */
        undo_begin();
        for (t = 0; t < SQ_TRACKS; t++) {
            if (!(dsnap_mask & (1u << t))) continue;
            undo_th_src = &dsnap_th[t];
            undo_add_row((uint8_t)t, dsnap_pat[t], dsnap_row[t], dsnap_cfg[t].length, dsnap_cfg[t].start);
            undo_th_src = 0;
        }
        status_msg("DICE KEPT");
    } else {
        dice_restore();
        status_msg("DICE: BACK AS IT WAS");
    }
    dice_pending = 0u;
    dhist_n = dhist_pos = 0u;
    ui_dirty = grid_dirty = 1u;
}

static void dice_seq(uint16_t mask)
{
    uint32_t t;
    uint8_t melodic = 0u;
    for (t = 0; t < SQ_TRACKS; t++) if ((mask & (1u << t)) && !track_drum(t) && !track_break(t)) melodic = 1u;
    uint8_t style = th_style_now(beat_genre);
    if (melodic && !project.gen.harm_lock) {              /* one progression of the genre for the roll: chords, bass, arps (not under HARM LOCK) */
        project.gen.harm_on = 1u;
        if (style != 255u) th_prog_dice(style);           /* 0.23 THEORY: one by the style's rules */
        else project.gen.harm_prog = (uint8_t)grand(SQ_PROGS);
    }
    for (t = 0; t < SQ_TRACKS; t++) {
        uint8_t fn, nv, own;
        sq_track_cfg_t *c = &project.track[t];
        sq_step_t *row;
        if (!(mask & (1u << t))) continue;
        own = fn = project.track[t].role ? sq_role_func(project.track[t].role) : sq_beat_role(track_drum(t), PEN(t));
        if (fn != SQ_FUNC_PROG) fn = sq_genre_part_for(beat_genre, fn);   /* 0.11: the genre's part for the track */
        nv = fn < SQ_FUNCS ? sq_beat_variants(beat_genre, fn) : 0u;
        row = project.step[t][tr[t].pattern];
        if (track_break(t)) { brk_dice_track(t); continue; }   /* 0.12: the slices re-ordered, the backbone kept */
        if (style != 255u && own != SQ_FUNC_PROG && own < SQ_FUNCS && !track_tape(t)) {   /* 0.23 THEORY: the part from a seed of the dice */
            if (style == SQ_TH_FREE || fn >= SQ_FUNCS) fn = own;
            beat_onto((uint8_t)t, fn, (uint8_t)(1u + grand(250u)));
            activate_row(t, row);
            if (tr[t].step >= c->length) tr[t].step = 0u;
            continue;
        }
        if (genre_feel() && nv) {
            dice_phrase = 1u;                                 /* 0.24: on a long track the dice rolls a PHRASE (the next variation, a fill) */
            beat_onto((uint8_t)t, fn, (uint8_t)grand(nv));
            dice_phrase = 0u;
            sq_row_keep(row);                                 /* (and every bar of it gets a take of its own: the steps are the track's) */
            sq_row_cook_role(row + c->start, (uint8_t)(c->length - c->start), (uint8_t)(tool_heat / 4u + 1u), gen_role(t), gen_root(t), gen_scale(), &sq_rng_state);   /* a take of its own */
        } else {                                              /* GENRE FREE: a rhythm of the dice, no library */
            uint8_t span = (uint8_t)(c->length - c->start), bar = (uint8_t)(span > bar_st() ? bar_st() : span);   /* 0.24: a bar (0.25: the metre's), then its phrase */
            sq_row_keep(row);
            sq_row_random(row + c->start, bar, (uint8_t)(30u + grand(40u)), &sq_rng_state);
            if (!track_drum(t)) {
                sq_row_random_notes(row + c->start, bar, PEN(t), gen_root(t), gen_scale(), &sq_rng_state);
                sq_row_phrase_gates(row + c->start, bar, gen_role(t), tool_heat, &sq_rng_state);   /* 0.11: notes of their own length */
            }
            gen_phrase((uint8_t)t, row + c->start, span);
        }
        if ((project.gen.targets & SQ_GT_NOTES) && !track_drum(t) && fn != SQ_FUNC_PROG)
            sq_row_cook_notes(row + c->start, (uint8_t)(c->length - c->start), (uint8_t)(tool_heat / 3u + 1u), gen_root(t), gen_scale(), &sq_rng_state);
        activate_row(t, row);
        if (tr[t].step >= c->length) tr[t].step = 0u;
    }
}

static void dice_cc(uint16_t mask)
{
    uint32_t t, l;
    int32_t span = 16 + (int32_t)tool_heat * 6 / 10;
    for (t = 0; t < SQ_TRACKS; t++) {
        sq_track_cfg_t *c = &project.track[t];
        if (!(mask & (1u << t))) continue;
        uint8_t lanes = gen_lanes(t);
        for (l = 0; l < SQ_LANES; l++) {
            int32_t b;
            if (!(lanes & (1u << l))) continue;
            b = (int32_t)c->lane_base[l];
            b = clamp_i32(b + (int32_t)grand((uint32_t)(2 * span + 1)) - span, 0, 127);
            c->lane_base[l] = (uint8_t)b;
            send_cc(track_ch(t), c->lane_cc[l], lane_val(l, (uint8_t)b));   /* heard at once: the synth's sound moves */
        }
        if (project.gen.targets & SQ_GT_CC) {
            sq_step_t *row = project.step[t][tr[t].pattern];
            sq_row_cook_lanes(row + c->start, (uint8_t)(c->length - c->start), tool_heat, lanes, c->lane_base, &sq_rng_state);
        }
    }
}

static void dice_groove(uint16_t mask)
{
    static const uint8_t GATES[4] = {25u, 50u, 80u, 100u};
    uint32_t t, i;
    uint8_t heat = tool_heat;
    for (t = 0; t < SQ_TRACKS; t++) {
        sq_track_cfg_t *c = &project.track[t];
        sq_step_t *row = project.step[t][tr[t].pattern];
        uint8_t drum = track_drum(t);
        if (!(mask & (1u << t))) continue;
        {   /* 0.16: the part's swing and GROOVE (the track's part: where it came from, else its role), a little off */
            uint8_t fn = c->src_func < SQ_FUNCS ? c->src_func : c->role ? sq_role_func(c->role) : 255u, sw, gv, ga;
            sq_genre_groove(beat_genre, fn, &sw, &gv, &ga);
            c->swing = (uint8_t)clamp_i32((int32_t)sw + (int32_t)grand(10u) - 3, SQ_SWING_MIN, SQ_SWING_MAX);
            if (fn < SQ_FUNCS && !track_tape(t)) {
                project.ext.track[t].groove = gv;
                project.ext.track[t].groove_amt = gv ? (uint8_t)clamp_i32((int32_t)ga + (int32_t)grand(41u) - 20, 10, 100) : 0u;
            }
        }
        c->hum_time = (uint8_t)grand(1u + heat / 8u);
        c->hum_vel = (uint8_t)grand(1u + heat / 5u);
        for (i = c->start; i < c->length; i++) {
            sq_step_t *s = &row[i];
            uint8_t beat = (sq_g16(i - c->start) & 3u) == 0u;        /* (0.25: the metre's beats) */
            if (!(s->flags & SQ_STEP_ON)) continue;
            if (grand(100u) < heat / 4u) s->length = drum ? GATES[grand(2u)] : GATES[grand(4u)];
            if (beat && grand(100u) < heat / 8u) s->velocity = 124u;
            else if (!beat && grand(100u) < heat / 10u) s->velocity = 50u;
            if (!beat && grand(100u) < heat / 14u) s->ratchet = (uint8_t)(2u + grand(2u));
            if (!beat && grand(100u) < heat / 12u) s->chance = (uint8_t)(60u + grand(36u));
        }
    }
}

/* DICE ALL: the bank of the selected track becomes a piece of the genre: tracks 1-4 kick, snare, hat, perc, 5 bass,
 * 6 chords, 7 arp, 8 a second percussion; a key the genre likes; a progression of the genre; the parts, the groove (and
 * the CC and LFO dice if the targets have them). The MIDI channels are not touched. */
/* 0.28: DICE ALL makes a piece on eight tracks - 1-8, or 5-12 from the bank of 9-12 (four tracks) */
static uint32_t dice_all_base(void) { return (selected_track & 8u) ? SQ_TRACKS - 8u : 0u; }
static uint16_t dice_all_mask(void) { return (uint16_t)(0xFFu << dice_all_base()); }
static void dice_all(void)
{
    uint32_t b = dice_all_base(), k;
    uint16_t mask = dice_all_mask();
    for (k = 0; k < 4u; k++) {
        uint8_t fn, note;
        sq_beat_kit_part(beat_genre, (uint8_t)k, &fn, &note);
        PEN(b + k) = note;
        set_track_mode(b + k, 2u);
    }
    PEN(b + 7u) = PEN(b + 3u) != 37u ? 37u : 39u;
    set_track_mode(b + 7u, 2u);
    PEN(b + 4u) = 36u; PEN(b + 5u) = 55u; PEN(b + 6u) = 67u;
    for (k = 4; k < 7u; k++) set_track_mode(b + k, 1u);
    project.key_root = (uint8_t)grand(12u);
    project.key_scale = sq_genre_scale(beat_genre, (uint8_t)grand(3u));
    project.key_shift = 0;
    key_sync_slot();
    dice_seq(mask);
    dice_groove(mask);
    if (project.gen.targets & SQ_GT_CC) dice_cc(mask);
    if (project.gen.targets & SQ_GT_LFO) for (k = 4; k < 7u; k++) lfo_dice(b + k, tool_heat);
}

static void dice_apply(uint8_t kind, uint16_t mask)
{
    uint32_t t;
    switch (kind) {
    case DICE_SEQ:    dice_seq(mask); break;
    case DICE_CC:     dice_cc(mask); break;
    case DICE_LFO:    for (t = 0; t < SQ_TRACKS; t++) if (mask & (1u << t)) lfo_dice(t, tool_heat); break;
    case DICE_GROOVE: dice_groove(mask); break;
    case DICE_RANDOM: for (t = 0; t < SQ_TRACKS; t++) if (mask & (1u << t)) tool_one(TOOL_RAND, (uint8_t)t); break;   /* 0.27: the tool, as a roll */
    default:          dice_all(); break;
    }
    if (kind != DICE_LFO) dice_restore_locked(mask);
}

/* the rolls 0..pos made again from what was there before the first one */
static void dice_replay(uint8_t pos)
{
    uint32_t i, keep = sq_rng_state;
    dice_restore();
    for (i = 0; i <= pos && i < dhist_n; i++) {
        sq_rng_state = dhist_seed[i];
        dice_apply(dhist_kind[i], dhist_mask[i]);
    }
    sq_rng_state = keep ^ 0x9E3779B9u;
    dhist_pos = pos;
    dice_kind = dhist_kind[pos];
}

static void dice_status(void)
{
    char *p = msg_buf;
    if (dice_kind == DICE_ALL) {
        uint16_t lo, hi;
        sq_genre_bpm(beat_genre, &lo, &hi);
        p = put_s(p, sq_genre_name(beat_genre)); p = put_s(p, " "); p = put_u(p, lo); p = put_s(p, "-"); p = put_u(p, hi); p = put_s(p, " BPM");
    } else p = put_s(p, DICE_NAME[dice_kind <= DICE_RANDOM ? dice_kind : 0u]);
    if (dhist_n > 1u) { p = put_s(p, " "); p = put_u(p, (uint32_t)dhist_pos + 1u); p = put_s(p, "/"); p = put_u(p, dhist_n); p = put_s(p, " ALG"); }
    p = put_s(p, ": OCT+ KEEP, OCT- BACK");
    finish(p);
    status_msg(msg_buf);
    msg_until = fm1_ms + 4000u;
}

static void dice_roll(uint8_t kind)
{
    uint16_t mask = kind == DICE_ALL ? dice_all_mask() : gen_mask();
    if (kind < DICE_SEQ || kind > DICE_RANDOM) return;
    if (!dice_pending) dhist_n = dhist_pos = 0u;
    dice_save(mask);                                  /* (the tracks not kept yet) */
    if (dhist_n && dhist_pos + 1u < dhist_n) dhist_n = (uint8_t)(dhist_pos + 1u);   /* a new roll forgets the ones after */
    if (dhist_n >= DICE_HIST) {                       /* full: the oldest roll becomes part of where they start from */
        uint32_t i, t;
        dice_replay(0u);
        for (t = 0; t < SQ_TRACKS; t++) {
            if (!(dsnap_mask & (1u << t))) continue;
            memcpy(dsnap_row[t], project.step[t][dsnap_pat[t]], sizeof dsnap_row[t]);
            dsnap_cfg[t] = project.track[t];
        }
        memcpy(dsnap_lfo, project.lfo, sizeof dsnap_lfo);
        dsnap_key[0] = project.key_root; dsnap_key[1] = project.key_scale; dsnap_key[2] = (uint8_t)project.key_shift;
        dsnap_harm[0] = project.gen.harm_on; dsnap_harm[1] = beat_genre;
        dsnap_harm[2] = project.gen.harm_prog; dsnap_harm[3] = project.gen.harm_bars;
        dhist_n--;
        for (i = 0; i < dhist_n; i++) { dhist_seed[i] = dhist_seed[i + 1u]; dhist_kind[i] = dhist_kind[i + 1u]; dhist_mask[i] = dhist_mask[i + 1u]; }
    }
    dhist_seed[dhist_n] = sq_rng_next(&sq_rng_state) ^ fm1_ms;
    dhist_kind[dhist_n] = kind;
    dhist_mask[dhist_n] = mask;
    dhist_n++;
    dice_pending = 1u;
    dice_replay((uint8_t)(dhist_n - 1u));
    dice_status();
    ui_dirty = grid_dirty = 1u;
}

static void dice_browse(int32_t d)                    /* while a dice waits: ALG goes to the roll before / after */
{
    int32_t p;
    if (!dice_pending || !dhist_n) return;
    p = clamp_i32((int32_t)dhist_pos + d, 0, (int32_t)dhist_n - 1);
    if (p != dhist_pos) dice_replay((uint8_t)p);
    dice_status();
    ui_dirty = grid_dirty = 1u;
}

/* ---- EVOLVE */
static uint8_t evo_run;                                 /* 0 off, 1 changing, 2 frozen */
static uint16_t evo_mask;
static uint8_t evo_pat[SQ_TRACKS], evo_bar;
static sq_step_t evo_seed[SQ_TRACKS][SQ_STEPS] __attribute__((section(".pool")));
static sq_lfo_t evo_seed_lfo[SQ_LFOS];

static void evo_take_seed(void)
{
    uint32_t t;
    for (t = 0; t < SQ_TRACKS; t++) if (evo_mask & (1u << t)) memcpy(evo_seed[t], project.step[t][evo_pat[t]], sizeof evo_seed[t]);
    memcpy(evo_seed_lfo, project.lfo, sizeof evo_seed_lfo);
}

/* 0.24: the track's length changed (track_fit): EVOLVE's seed is one of its patterns */
static void gen_track_fit(uint32_t t, uint8_t old_len, uint8_t old_start)
{
    if (!evo_run || !(evo_mask & (1u << t))) return;
    if (old_start != project.track[t].start) sq_row_keep(evo_seed[t]);
    sq_row_fit(evo_seed[t], project.track[t].start, old_len, project.track[t].length);
}

static void evo_status(void)
{
    char *p = msg_buf;
    uint8_t r = sq_evo_return(&project.ext, &project.gen);
    p = put_s(p, "EVOLVE "); p = put_u(p, project.gen.evo_amount); p = put_s(p, "% EVERY "); p = put_u(p, EVO_BARS[project.gen.evo_every]);
    if (!r) p = put_s(p, " DRIFT");                    /* (0.27: RETURN 0 is DRIFT; between: how much comes back) */
    else if (r < SQ_EVO_RETURN_MAX) { p = put_s(p, " RETURN "); p = put_u(p, r); p = put_s(p, "%"); }
    finish(p);
    status_msg(msg_buf);
}

static void evo_toggle(void)
{
    uint32_t t;
    if (evo_run) { evo_run = 0u; status_msg("EVOLVE OFF (WHAT YOU HEAR STAYS)"); ui_dirty = grid_dirty = 1u; return; }
    evo_mask = gen_mask();
    for (t = 0; t < SQ_TRACKS; t++) evo_pat[t] = tr[t].pattern;
    evo_take_seed();
    evo_run = 1u;
    evo_bar = 0u;
    evo_status();
    ui_dirty = grid_dirty = 1u;
}

static void evo_freeze(void)
{
    if (!evo_run) { status_msg("NOT EVOLVING"); return; }
    if (evo_run == 1u) { evo_take_seed(); evo_run = 2u; status_msg("FROZEN: THIS IS THE SEED NOW"); }
    else { evo_run = 1u; evo_bar = 0u; status_msg("EVOLVING AGAIN"); }
    ui_dirty = grid_dirty = 1u;
}

static void evo_revert(void)
{
    uint32_t t;
    if (!evo_run) { status_msg("NOT EVOLVING"); return; }
    for (t = 0; t < SQ_TRACKS; t++) if (evo_mask & (1u << t)) memcpy(project.step[t][evo_pat[t]], evo_seed[t], sizeof evo_seed[t]);
    memcpy(project.lfo, evo_seed_lfo, sizeof evo_seed_lfo);
    memset(lfo_last_valid, 0, sizeof lfo_last_valid);
    evo_run = 2u;
    status_msg("BACK TO THE SEED (FROZEN)");
    ui_dirty = grid_dirty = 1u;
}

/* 0.27: DRIFT is EVOLVE's RETURN at 0 (SEQ 3 SEL + K2). The key goes there, and back to the RETURN it had (100 at first) */
static uint8_t evo_ret_was = SQ_EVO_RETURN_MAX;
static uint8_t evo_drifts(void) { return sq_evo_return(&project.ext, &project.gen) == 0u; }
static void evo_drift_toggle(void)
{
    uint8_t r = sq_evo_return(&project.ext, &project.gen);
    if (r) { evo_ret_was = r; sq_evo_return_set(&project.ext, &project.gen, 0u); status_msg("DRIFT: EVOLVE WANDERS AWAY"); }
    else {
        char *p = msg_buf;
        r = evo_ret_was ? evo_ret_was : (uint8_t)SQ_EVO_RETURN_MAX;
        sq_evo_return_set(&project.ext, &project.gen, r);
        if (r >= SQ_EVO_RETURN_MAX) status_msg("NO DRIFT: EVOLVE STAYS NEAR THE SEED");
        else { p = put_s(p, "NO DRIFT: EVOLVE RETURN "); p = put_u(p, r); p = put_s(p, "%"); finish(p); status_msg(msg_buf); }
    }
    ui_dirty = grid_dirty = 1u;
}
static void evo_return_turn(int32_t d, int32_t f)          /* SEQ 3, SEL + K2 */
{
    char *p = msg_buf;
    uint8_t r = (uint8_t)kstep(sq_evo_return(&project.ext, &project.gen), d, 5 * f, 0, (int32_t)SQ_EVO_RETURN_MAX);
    sq_evo_return_set(&project.ext, &project.gen, r);
    if (r) evo_ret_was = r;
    p = put_s(p, "EVOLVE RETURN "); p = put_u(p, r); p = put_s(p, "%: ");
    p = put_s(p, r >= SQ_EVO_RETURN_MAX ? "FROM THE SEED EVERY TIME" : r ? "PART OF THE WAY BACK" : "DRIFT, NO WAY BACK");
    finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}

/* 0.8: how EVOLVE moves a genre (sq_genre_evolve: rhythm-heavy styles move the syncopation harder, dub and house keep
 * the harmony, EXPERIMENT lets go). The notes move by the rules of voice leading (sq_row_evolve_notes): on the beats
 * the tones of the tonic chord (the HARMONY then moves a FOLLOW track to the chord that plays), steps of the key between
 * them, leaps that come back; a bass keeps root and fifth on the beats. */
static uint8_t evo_center(const sq_step_t *row, uint8_t len, uint8_t fallback)
{
    uint32_t i, sum = 0u, n = 0u;
    for (i = 0; i < len; i++)
        if ((row[i].flags & SQ_STEP_ON) && row[i].note[0] != SQ_NOTE_NONE) { sum += row[i].note[0]; n++; }
    return n ? (uint8_t)(sum / n) : fallback;
}

static void evo_change(void)
{
    uint32_t t, i;
    uint8_t amt = project.gen.evo_amount, tg = project.gen.targets, rhy = 50u, note = 50u, ret = sq_evo_return(&project.ext, &project.gen);
    if (genre_feel()) sq_genre_evolve(beat_genre, &rhy, &note);   /* (0.10 GENRE FREE: half and half) */
    for (t = 0; t < SQ_TRACKS; t++) {
        sq_track_cfg_t *c = &project.track[t];
        sq_step_t *row = project.step[t][evo_pat[t]], *part = row + c->start;
        uint8_t len = (uint8_t)(c->length - c->start);
        uint8_t ramt = (uint8_t)(((uint32_t)amt * rhy + 50u) / 100u);
        uint8_t namt = (uint8_t)(((uint32_t)amt * note + 50u) / 100u);
        if (!(evo_mask & (1u << t))) continue;
        if (ret >= SQ_EVO_RETURN_MAX) memcpy(row, evo_seed[t], sizeof evo_seed[t]);    /* around the seed */
        else if (ret) for (i = 0; i < SQ_STEPS; i++) if (grand(100u) < ret) row[i] = evo_seed[t][i];   /* 0.27 RETURN: part of the way back */
        sq_row_keep(row);                               /* 0.24: EVOLVE moves every bar of the loop its own way: the copies are steps (the seed keeps its own) */
        if (genre_feel()) sq_row_cook_role(part, len, ramt, gen_role(t), gen_root(t), gen_scale(), &sq_rng_state);
        else sq_row_cook(part, len, ramt, &sq_rng_state);
        if ((tg & SQ_GT_NOTES) && !track_drum(t)) {
            uint8_t center = evo_center(evo_seed[t] + c->start, len, PEN(t));
            sq_row_evolve_notes(part, len, namt, gen_root(t), gen_scale(), (uint8_t)(center < 48u), center, &sq_rng_state);
        }
        if (tg & SQ_GT_CC) sq_row_cook_lanes(part, len, amt, gen_lanes(t), c->lane_base, &sq_rng_state);
        if (tg & SQ_GT_LFO) {
            if (ret)
                for (i = 0; i < SQ_LFOS; i++) if (lfo_aims(&evo_seed_lfo[i], t) && (ret >= SQ_EVO_RETURN_MAX || grand(100u) < ret)) project.lfo[i] = evo_seed_lfo[i];
            lfo_cook(t, amt);
        }
        for (i = 0; i < SQ_STEPS; i++) if (evo_seed[t][i].flags & SQ_STEP_LOCK) row[i] = evo_seed[t][i];
        activate_row(t, row);
    }
}

/* at every bar line (seq_clock_tick) */
static void gen_bar_tick(void)
{
    live_bar();
    if (evo_run != 1u) return;
    if (++evo_bar < EVO_BARS[project.gen.evo_every]) return;
    evo_bar = 0u;
    evo_change();
    ui_dirty = grid_dirty = 1u;
}

/* ---- TEMP: everything as it was when it was pressed, back when it is let go */
static uint8_t temp_on;
static sq_step_t temp_row[SQ_TRACKS][SQ_STEPS] __attribute__((section(".pool")));
static sq_track_cfg_t temp_cfg[SQ_TRACKS];
static uint8_t temp_pat[SQ_TRACKS], temp_key[3], temp_harm[5];
static sq_lfo_t temp_lfo[SQ_LFOS];
static uint16_t temp_mute, temp_solo, temp_bpm;
static int8_t temp_ktrans;

static void temp_begin(void)
{
    uint32_t t;
    if (temp_on) return;
    if (dice_pending) dice_answer(1u);
    for (t = 0; t < SQ_TRACKS; t++) {
        temp_pat[t] = tr[t].pattern;
        memcpy(temp_row[t], project.step[t][tr[t].pattern], sizeof temp_row[t]);
        temp_cfg[t] = project.track[t];
    }
    temp_harm[0] = project.gen.harm_on; temp_harm[1] = beat_genre;
    temp_harm[2] = project.gen.harm_prog; temp_harm[3] = project.gen.harm_bars; temp_harm[4] = project.gen.harm_genre;
    memcpy(temp_lfo, project.lfo, sizeof temp_lfo);
    temp_key[0] = project.key_root; temp_key[1] = project.key_scale; temp_key[2] = (uint8_t)project.key_shift;
    temp_mute = mute_mask; temp_solo = solo_mask; temp_bpm = project.bpm;
    temp_ktrans = project.live.ktrans;
    temp_on = 1u;
    status_msg("TEMP: CHANGES LAST WHILE HELD");
    ui_dirty = grid_dirty = 1u;
}

static void temp_end(void)
{
    uint32_t t;
    if (!temp_on) return;
    dice_pending = 0u;                                    /* (a dice rolled under TEMP goes with it) */
    for (t = 0; t < SQ_TRACKS; t++) {
        sq_track_cfg_t *c = &project.track[t];
        sq_track_cfg_t was = *c;
        memcpy(project.step[t][temp_pat[t]], temp_row[t], sizeof temp_row[t]);
        *c = temp_cfg[t];
        tr[t].pattern = temp_pat[t];
        tr[t].pending_pattern = SQ_NO_PENDING;
        track_cfg_back(t, &was, temp_pat[t]);             /* 0.11: in time (the explorer) */
    }
    memcpy(project.lfo, temp_lfo, sizeof temp_lfo);
    memset(lfo_last_valid, 0, sizeof lfo_last_valid);
    project.key_root = temp_key[0]; project.key_scale = temp_key[1]; project.key_shift = (int8_t)temp_key[2];
    key_sync_slot();
    mute_mask = temp_mute; solo_mask = temp_solo; project.bpm = temp_bpm;
    project.live.ktrans = temp_ktrans;
    project.gen.harm_on = temp_harm[0]; beat_genre = temp_harm[1];
    project.gen.harm_prog = temp_harm[2]; project.gen.harm_bars = temp_harm[3]; project.gen.harm_genre = temp_harm[4];
    ktrans_pend = SQ_KT_NONE;
    temp_on = 0u;
    status_msg("TEMP OFF: BACK AS IT WAS");
    ui_dirty = grid_dirty = 1u;
}

/* ---- SONG: the scenes of project.song one after the other */
static uint8_t song_on, song_pos, song_bar, song_wait;
static uint8_t song_skip_bar;          /* the next bar line is the one the song was put on (song_seek): not counted again */

static void song_play_entry(uint8_t pos)
{
    if (!project.song.len) return;
    if (pos >= project.song.len) pos = 0u;
    song_pos = pos;
    song_bar = 0u;
    song_skip_bar = 0u;
    apply_scene(project.song.e[pos].scene);
    pending_scene = SQ_NO_PENDING;
    if (project.live.song_tempo && project.song.e[pos].bpm >= 30u && project.song.e[pos].bpm <= 300u && project.clock_mode == SQ_CLOCK_MASTER) {
        project.bpm = project.song.e[pos].bpm;             /* 0.10: the entry's tempo (SAVE page 2 K2) */
        knob_live = 0u; knob_ref = fm1_knob;
    }
}

static void song_status(void)
{
    char *p = msg_buf;
    if (!song_on) { status_msg("SONG OFF"); return; }
    p = put_s(p, "SONG "); p = put_u(p, (uint32_t)song_pos + 1u); p = put_s(p, "/"); p = put_u(p, project.song.len);
    p = put_s(p, " SCENE "); p = put_u(p, (uint32_t)project.song.e[song_pos].scene + 1u); finish(p);
    status_msg(msg_buf);
}

static void song_toggle(void)
{
    if (!song_on && !project.song.len) { status_msg("SONG EMPTY"); return; }
    song_on ^= 1u;
    if (song_on) {
        if (playing) { song_wait = 1u; song_pos = 0u; status_msg("SONG FROM THE NEXT BAR"); }
        else { song_play_entry(0u); song_status(); }
    } else { song_wait = 0u; song_status(); }
    ui_dirty = grid_dirty = 1u;
}

/* a scene at the end of the song, for four bars; the same scene as the last one: four bars more */
static void song_append(uint8_t scene)
{
    char *p = msg_buf;
    sq_song_entry_t *e;
    if (scene >= SQ_SCENES) return;
    if (project.song.len && project.song.e[project.song.len - 1u].scene == scene) {
        e = &project.song.e[project.song.len - 1u];
        e->bars = (uint8_t)(e->bars + 4u > SQ_SONG_BARS_MAX ? SQ_SONG_BARS_MAX : e->bars + 4u);
    } else {
        if (project.song.len >= SQ_SONG_LEN) { status_msg("SONG FULL (128)"); return; }
        e = &project.song.e[project.song.len++];
        e->scene = scene;
        e->bars = 4u;
        e->bpm = project.bpm;                                 /* 0.10: the tempo of the moment goes with the entry */
    }
    p = put_s(p, "SONG "); p = put_u(p, project.song.len); p = put_s(p, ": SCENE "); p = put_u(p, (uint32_t)e->scene + 1u);
    p = put_s(p, " X "); p = put_u(p, e->bars); p = put_s(p, " BARS"); finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}

static void song_drop_last(void)
{
    if (!project.song.len) { status_msg("SONG EMPTY"); return; }
    project.song.len--;
    if (song_pos >= project.song.len) song_pos = 0u;
    if (!project.song.len) { song_on = 0u; song_wait = 0u; }
    status_num("SONG ENTRIES ", project.song.len);
    ui_dirty = grid_dirty = 1u;
}

static void song_insert(uint8_t pos)                    /* a copy of entry pos right after it */
{
    uint32_t i;
    if (pos >= project.song.len) { status_msg("NO ENTRY THERE"); return; }
    if (project.song.len >= SQ_SONG_LEN) { status_msg("SONG FULL (128)"); return; }
    for (i = project.song.len; i > pos + 1u; i--) project.song.e[i] = project.song.e[i - 1u];
    project.song.e[pos + 1u] = project.song.e[pos];
    project.song.len++;
    if (song_on && song_pos > pos) song_pos++;
    status_num("SONG ENTRIES ", project.song.len);
    ui_dirty = grid_dirty = 1u;
}

static void song_delete(uint8_t pos)
{
    uint32_t i;
    if (pos >= project.song.len) { status_msg("NO ENTRY THERE"); return; }
    for (i = pos; i + 1u < project.song.len; i++) project.song.e[i] = project.song.e[i + 1u];
    project.song.len--;
    if (song_pos > pos) song_pos--;
    if (song_pos >= project.song.len) { song_pos = 0u; song_bar = 0u; }
    if (!project.song.len) { song_on = 0u; song_wait = 0u; }
    status_num("SONG ENTRIES ", project.song.len);
    ui_dirty = grid_dirty = 1u;
}

static void song_loop_toggle(void)
{
    project.song.loop ^= 1u;
    status_msg(project.song.loop ? "SONG LOOPS" : "SONG STOPS ON THE LAST SCENE");
    ui_dirty = grid_dirty = 1u;
}

static void song_set_bars(uint8_t pos, uint8_t bars)
{
    char *p = msg_buf;
    if (pos >= project.song.len) return;
    project.song.e[pos].bars = bars < 1u ? 1u : bars > SQ_SONG_BARS_MAX ? (uint8_t)SQ_SONG_BARS_MAX : bars;
    p = put_s(p, "SONG "); p = put_u(p, (uint32_t)pos + 1u); p = put_s(p, ": "); p = put_u(p, project.song.e[pos].bars);
    p = put_s(p, " BARS"); finish(p);
    status_msg(msg_buf);
    ui_dirty = grid_dirty = 1u;
}

static void song_start_hook(void)                       /* PLAY: the song from its first scene */
{
    if (!song_on || !project.song.len) return;
    song_wait = 0u;
    song_play_entry(0u);
}

static void song_clear(void)
{
    project.song.len = 0u;
    song_on = 0u; song_wait = 0u;
    status_msg("SONG CLEARED");
    ui_dirty = grid_dirty = 1u;
}

/* 0.5: a Song Position Pointer (as a slave), or a jump to a bar: the song goes to the entry that plays there, and on
 * to the bar of it. A position past the end of a song that loops wraps round; one that does not loop stays on the
 * last entry. */
static void song_seek(uint32_t ticks)
{
    sq_song_pos_t o;
    uint8_t moved = 0u;
    /* (0.25: the metre's bars; 0.26: each entry the bars of the metre its scene brings - sq_song_locate walks them from
     *  the song's start, which is taken to be in the bar there is now when its first scene brings none) */
    if (!song_on || !project.song.len) return;
    if (!sq_song_locate(&project.song, project.ext.scene_metre_on ? project.ext.scene_metre : 0, bar_st(), bar_bt(), ticks, &o)) return;
    song_wait = 0u;
    song_pos = o.entry;
    if (o.steps != bar_st() || o.beats != bar_bt()) {  /* 0.26: the bar there, and the tracks that are bars long with it */
        bar_pend_steps = 0u;
        metre_put(o.steps, o.beats);
        metre_say(0u, "");
        moved = 1u;
    }
    apply_scene(project.song.e[o.entry].scene);
    pending_scene = SQ_NO_PENDING;
    song_bar = o.bar;
    song_skip_bar = o.on_line;
    bar_origin = o.line; bar_base = o.bars_before;     /* the bar lines are the entry's (the same lines as ever while no scene brings a metre) */
    if (o.metre_from || moved) seek_tracks(o.metre_from, ticks);   /* every track began again where the metre last changed (and is as long as its bars are now) */
    ui_dirty = grid_dirty = 1u;
}

/* at every bar line (seq_clock_tick), before a queued scene */
static void song_bar_tick(void)
{
    uint8_t next;
    if (song_skip_bar) { song_skip_bar = 0u; return; }
    if (!song_on || !project.song.len) return;
    if (song_wait) { song_wait = 0u; song_play_entry(0u); ui_dirty = grid_dirty = 1u; return; }
    if (++song_bar < project.song.e[song_pos].bars) return;
    next = (uint8_t)(song_pos + 1u);
    if (next >= project.song.len) {
        if (!project.song.loop) { song_bar = project.song.e[song_pos].bars; return; }   /* the last one goes on */
        next = 0u;
    }
    song_play_entry(next);
    ui_dirty = grid_dirty = 1u;
}

/* a project is loaded: what was going on is over */
static void gen_reset(void)
{
    dice_pending = 0u;
    dhist_n = dhist_pos = 0u;
    memset(algo_seen, 255, sizeof algo_seen);       /* the live layers start again from the patterns */
    memset(algo_pend, 0, sizeof algo_pend);         /* 0.16: nothing READY (the values kept stay: they are the player's) */
    mfx_sel_reset();                                /* 0.19: K1 shows each track's first MIDI FX, nothing READY */
    evo_run = 0u;
    temp_on = 0u;
    song_on = 0u; song_wait = 0u; song_pos = 0u; song_bar = 0u; song_skip_bar = 0u;
    kb_chord_on = 0u;                               /* 0.26: no chord of the keyboard's */
    undo_clear();
}

/* ---- tap tempo: the average of the last taps (the first tap, or one after a pause of 2 s, starts again; a tap
 * closer than 100 ms to the last is a bounce and is ignored) */
static uint32_t tap_last, tap_sum;
static uint8_t tap_n, tap_have;

static void tap_tempo(void)
{
    uint32_t d = (uint32_t)(fm1_ms - tap_last), bpm;
    if (project.clock_mode != SQ_CLOCK_MASTER) { status_msg("EXTERNAL CLOCK"); return; }
    if (tap_have && d < 100u) return;
    tap_last = fm1_ms;
    if (!tap_have || d > 2000u) { tap_have = 1u; tap_n = 0u; tap_sum = 0u; status_msg("TAP"); return; }
    if (tap_n >= 4u) { tap_sum = tap_sum * 3u / 4u; tap_n = 3u; }
    tap_sum += d;
    tap_n++;
    bpm = (60000u * tap_n + tap_sum / 2u) / tap_sum;
    project.bpm = (uint16_t)clamp_i32((int32_t)bpm, 30, 300);
    knob_live = 0u; knob_ref = fm1_knob;
    status_num("TAP ", project.bpm);
}
