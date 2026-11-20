/* SPDX-License-Identifier: GPL-3.0-only */
#ifndef SAGGA_IMG27_H
#define SAGGA_IMG27_H
/*
 * 0.28: the saved project's layout as 0.27 wrote it, kept as it was. 0.28 has twelve tracks, chords of six notes and
 * eight CC lanes; its image is still SGQB in this layout - sixteen tracks (the last four empty), steps of four notes and
 * six lanes - so that a 0.27 firmware, and the Pi's tools of 0.27, open a project of 0.28. What 0.27 has no room for
 * (the notes 5 and 6, the lanes 7 and 8 and their settings) is in a chunk of its own, SQ_CHUNK_X28, which 0.27 skips.
 * An image of 0.27 or before read by 0.28: what is on its tracks 13-16 goes to tracks of the twelve that are empty.
 * Included by sagga_seq_core.c only (the image is the core's).
 */
#include "sagga_seq_core.h"

#define SQ27_TRACKS 16u
#define SQ27_POLY   4u
#define SQ27_LANES  6u
#define SQ27_TRACK_HEAD 12u      /* the bytes of a track's settings before its lanes (channel .. hum_vel) */
#define SQ27_TRACK_TAIL 60u      /* ... after its lanes (flags .. brk_cfg) */
/* 0.30: what the image's own layout holds of the scenes, the snapshots, the song and the tapes (0.9 - 0.29's sizes); the
 * scenes 17-32, the snapshots 9-16, the song's entries past 64 and the tapes' events past 1536 are in chunk 6 */
#define SQ27_SCENES   16u
#define SQ27_SNAPS    8u
#define SQ27_SONG_LEN 64u
#define SQ27_TAPE_MAX 1536u

/* a step: 18 bytes (0.28: 22, the notes 5-6 and the lanes 7-8 in the chunk) */
typedef struct __attribute__((packed)) {
    uint8_t note[SQ27_POLY];
    uint8_t velocity, length, chance, ratchet, condition, flags;
    uint8_t lane[SQ27_LANES];
    int8_t nudge, ramp;
} sq27_step_t;

/* a track's settings: 96 bytes - the twelve before the lanes, six lanes, the sixty after */
typedef struct __attribute__((packed)) {
    uint8_t head[SQ27_TRACK_HEAD];
    uint8_t lane_cc[SQ27_LANES], lane_base[SQ27_LANES], lane_flags[SQ27_LANES], lane_hi[SQ27_LANES];
    uint8_t tail[SQ27_TRACK_TAIL];
} sq27_track_t;

typedef struct __attribute__((packed)) {
    uint8_t pattern[SQ27_TRACKS];
    uint16_t mute_mask;
    uint8_t pc[SQ_CHANNELS];
    uint8_t lane[SQ27_TRACKS][SQ27_LANES];
    uint8_t key_slot;
} sq27_scene_t;                  /* 131 bytes */

typedef struct __attribute__((packed)) {
    uint8_t used, ccn;
    uint16_t bpm;
    uint8_t key_root, key_scale;
    int8_t key_shift, ktrans;
    uint8_t pattern[SQ27_TRACKS];
    uint16_t mute, solo;
    int8_t mac[4];
    uint8_t harm_on, genre, harm_prog, harm_bars;
    uint8_t morph_b, key_cur, harm_genre;
    uint8_t reserved[1];
} sq27_snap_head_t;              /* 40 bytes */

typedef struct __attribute__((packed)) {
    uint8_t on, phrase_bars, energy, set_genre;
    uint8_t state[SQ27_TRACKS];
    uint8_t phrase_count, quant;
    uint8_t reserved[6];
} sq27_viaggio_t;                /* 28 bytes */

/* 0.20 - 0.28's five new effects and the order of nine (0.29 has two more: sq_mfxd_t, and chunk 5 keeps it whole) */
typedef struct __attribute__((packed)) {
    uint8_t on;
    uint8_t order[9];
    int8_t amt[5];
    uint8_t time[5];
    uint8_t fb[5];
} sq27_mfxd_t;                   /* 25 bytes */

typedef struct __attribute__((packed)) {
    sq_lfox_t lfo[SQ_LFOS];
    sq_trackx_t track[SQ27_TRACKS];
    uint8_t motion_bars, kb_mode, kb_ch, in_thru;
    int8_t motion[4][SQ_MOTION_CELLS];
    uint8_t click, count_in, click_out, click_note, click_level, scene_metre_on, evo_ret;
    uint8_t reserved[1];
    char name[SQ_NAME_LEN];
    sq_mfxc_t mfxc[SQ27_TRACKS];
    sq27_mfxd_t mfxd[SQ27_TRACKS];
    sq_lfoe_t lfoe[SQ_LFOS];
    sq_mod_t mod[SQ_MODS];
    uint8_t scene_metre[SQ27_SCENES];
} sq27_ext_t;                    /* 1524 bytes */

typedef struct __attribute__((packed)) {
    uint8_t len, loop;
    sq_song_entry_t e[SQ27_SONG_LEN];
} sq27_song_t;                   /* 258 bytes */

#define SQ27_EXT_014 780u        /* the bytes of the chunk a 0.13 / 0.14 image holds */
#define SQ27_EXT_018 796u        /* ... a 0.15 - 0.18 image */
#define SQ27_EXT_019 1004u       /* ... a 0.19 image */
#define SQ27_EXT_025 1508u       /* ... a 0.20 - 0.25 image */

typedef char sq27_sizes[(sizeof(sq27_step_t) == 18u && sizeof(sq27_track_t) == 96u && sizeof(sq27_scene_t) == 131u &&
                         sizeof(sq27_snap_head_t) == 40u && sizeof(sq27_viaggio_t) == 28u && sizeof(sq27_ext_t) == 1524u &&
                         __builtin_offsetof(sq27_ext_t, name) == SQ27_EXT_014 && __builtin_offsetof(sq27_ext_t, mfxc) == SQ27_EXT_018 &&
                         __builtin_offsetof(sq27_ext_t, mfxd) == SQ27_EXT_019 && __builtin_offsetof(sq27_ext_t, scene_metre) == SQ27_EXT_025 &&
                         __builtin_offsetof(sq27_ext_t, click) == SQ27_EXT_014 - 8u) ? 1 : -1];
/* 0.28's own layouts against these: the same fields, in the same order, only longer arrays */
typedef char sq27_track_split[(__builtin_offsetof(sq_track_cfg_t, lane_cc) == SQ27_TRACK_HEAD &&
                               __builtin_offsetof(sq_track_cfg_t, flags) == SQ27_TRACK_HEAD + 4u * SQ_LANES &&
                               sizeof(sq_track_cfg_t) == SQ27_TRACK_HEAD + 4u * SQ_LANES + SQ27_TRACK_TAIL) ? 1 : -1];
typedef char sq27_more[(SQ_TRACKS <= SQ27_TRACKS && SQ_POLY >= SQ27_POLY && SQ_LANES >= SQ27_LANES && SQ_SCENES >= SQ27_SCENES &&
                        SQ_SNAPS >= SQ27_SNAPS && SQ_SONG_LEN >= SQ27_SONG_LEN && SQ_TAPE_MAX >= SQ27_TAPE_MAX && sizeof(sq27_song_t) == 258u) ? 1 : -1];

/* the chunk of 0.28 (SQ_CHUNK_X28): a version byte, a byte of the parts that follow (SQ_X28_*), then each part:
 *   LANES  the settings of the lanes 7-8 of the twelve tracks: lane_cc, lane_base, lane_flags, lane_hi, two of each
 *   SCENE  n (2 bytes), n x (scene, track, value of lane 7, of lane 8): the scenes' values of those lanes, not NONE
 *   SNAP   n, n x (snapshot, track, 8 bytes): a snapshot's track whose lanes 7-8 settings are not the project's
 *   STEPS  n (2 bytes), n x (track, pattern, 8 bytes: a bit a step, then 4 bytes a step: notes 5 and 6, lanes 7 and 8):
 *          the steps whose extra bytes are not an empty step's */
#define SQ_CHUNK_X28 4u
/* 0.29: chunk 5, one byte (1): the genres are numbered as 0.29's - the image keeps 0.28's numbers (sq_genre_from28),
 * where 0.28's AFRO HOUSE is 0.29's BALANI (an image without the chunk: AFRO HOUSE went into GQOM). Written only when
 * the project has BALANI somewhere (every other genre reads back as it was). 0.28 skips the chunk and opens the project
 * with its own genres: BALANI as AFRO HOUSE */
#define SQ_CHUNK_X29 5u
/* 0.30: chunk 6, what 0.29 has no room for: a version byte (1), a byte of the parts that follow (SQ_X30_*), then each part:
 *   SCENES  2 bytes, a bit a scene 17-32 that is not an empty one, then those scenes in the layout above (131 bytes each)
 *   METRES  the metres of the scenes 17-32 (16 bytes: ext.scene_metre)
 *   SONG    the song's length (65..128), then its entries past the 64th (4 bytes each)
 *   SNAPS   a byte, a bit a snapshot 9-16 that is used, then each as the image's own snapshots (its head, the tracks that
 *           are not the project's, the LFOs if they are not, the CC values) - but with the genres, the progression, the
 *           roles and parts as 0.30 numbers them (no 0.28 numbers: nothing before 0.30 reads it)
 *   TAPES   the twelve tracks' counts of events (2 bytes each, all of them), 2 bytes n, the n events past the 1536th
 * Written before chunk 4, whose lanes 7-8 reach the snapshots 9-16 (and the scenes 17-32) by their numbers: 0.28 and 0.29
 * skip both what chunk 4 says of them and chunk 6 */
#define SQ_CHUNK_X30 6u
#define SQ_X30_VER    1u
#define SQ_X30_SCENES 0x01u
#define SQ_X30_METRES 0x02u
#define SQ_X30_SONG   0x04u
#define SQ_X30_SNAPS  0x08u
#define SQ_X30_TAPES  0x10u
#define SQ_X28_VER   1u
#define SQ_X28_LANES 0x01u
#define SQ_X28_SCENE 0x02u
#define SQ_X28_SNAP  0x04u
#define SQ_X28_STEPS 0x08u
#define SQ_X28_EXTRA (SQ_POLY - SQ27_POLY + SQ_LANES - SQ27_LANES)   /* 4: the bytes of a step the chunk keeps */
#define SQ_X28_LCFG  (4u * (SQ_LANES - SQ27_LANES))                    /* 8: the bytes of a track's lanes 7-8 settings */

#endif
