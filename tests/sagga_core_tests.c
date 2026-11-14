/* SPDX-License-Identifier: GPL-3.0-only */
/* Unit tests of the SAGGA SEQ core (firmware/src/sagga_seq_core.c): pure logic, no hardware.
 *   sh tests/run_sagga_tests.sh */
#include <stdio.h>
#include <string.h>
#include "sagga_seq_core.h"
#include "sagga_beats.h"
#include "sagga_setgenre_data.h"     /* 0.10: VIAGGIO's set genres as generated (the core has its own copy of the table) */

static int failures, checks;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #c); } } while (0)

static void test_layout(void)
{
    CHECK(sizeof(sq_step_t) == 18u);
    CHECK(sizeof(sq_track_cfg_t) == 96u && SQ_TRACK_CFG_A == 80u && sizeof(sq_algo_t) == 4u);   /* 0.11: 16 more bytes, the algorithm slots */
    CHECK(sizeof(sq_scene_t) == 16u + 2u + 16u + 96u + 1u);
    CHECK(sizeof(sq_live_t) == 20u);
    CHECK(sizeof(sq_lfo_t) == 10u);
    CHECK(sizeof(sq_gen_t) == 32u && SQ_GEN_A == 24u && sizeof(sq_song_t) == 2u + 4u * SQ_SONG_LEN);   /* 0.11: the harmony's rhythm and mood */
    CHECK(sizeof(sq_snap_t) == SQ_SNAP_HEAD + 16u * 96u + 16u * 10u + 48u * 3u && SQ_SNAP_HEAD == 40u);
    {   /* the project: its parts end to end, no padding (images compare whole) */
        uint32_t want = 4u + 8u + 16u * 4u + 16u + 5u * 52u + 16u * 96u + 16u * 131u + 16u * 10u + 32u + 258u + 20u + 8u * (uint32_t)sizeof(sq_snap_t) + 28u + 1004u + 32u + 2u + 2u + 1536u * 6u + 16u * 8u * 64u * 18u + 2u;
        CHECK(sizeof(sq_viaggio_t) == 28u && sizeof(sq_phrase_t) == 26u && sizeof(sq_move_t) == 3u && sizeof(sq_expo_t) == 12u);
        CHECK(sizeof(sq_tape_ev_t) == 6u && sizeof(sq_tape_cfg_t) == 4u && sizeof(sq_key_t) == 4u && sizeof(sq_uprog_t) == 52u && SQ_UPROG_A == 18u);
        CHECK(sizeof(sq_project_t) == want);
    }
    CHECK(SQ_CHORD_COUNT <= 16u);                        /* the mode is 4 bits */
    CHECK(SQ_ARP_OUT == 36u && SQ_POLY_OUT == 6u);
}

static void test_tape(void)
{
    static sq_project_t pa, pb;
    static uint8_t img[20000];
    uint16_t f, n;
    uint32_t len, k;
    sq_project_init(&pa);
    CHECK(pa.tape_n == 0u && pa.track[3].tape.bars == 4u && pa.track[3].tape.quant == 0u);
    len = sq_tape_len(&pa.track[3].tape);
    CHECK(len == 4u * 1536u && SQ_TAPE_PPQ == 384u);
    /* add out of order on two tracks: kept per track, sorted */
    CHECK(sq_tape_add(&pa, 3u, 1000u, 50u, 60u, 100u) == 0);
    CHECK(sq_tape_add(&pa, 3u, 10u, 400u, 62u, 90u) == 0);
    CHECK(sq_tape_add(&pa, 1u, 5000u, 10u, 36u, 127u) == 0);
    CHECK(sq_tape_add(&pa, 3u, 1000u, 20u, 64u, 80u) == 0);                 /* the same start: after the one there */
    CHECK(pa.tape_n == 4u && pa.tape_cnt[1] == 1u && pa.tape_cnt[3] == 3u);
    sq_tape_range(&pa, 1u, &f, &n); CHECK(f == 0u && n == 1u && pa.tape_ev[0].note == 36u);
    sq_tape_range(&pa, 3u, &f, &n); CHECK(f == 1u && n == 3u && pa.tape_ev[1].on == 10u && pa.tape_ev[2].note == 60u && pa.tape_ev[3].note == 64u);
    sq_tape_range(&pa, 0u, &f, &n); CHECK(f == 0u && n == 0u);
    sq_tape_range(&pa, 15u, &f, &n); CHECK(f == 4u && n == 0u);
    /* quantise: 1000 is 40 ticks past 960: at 50 % it plays at 980, at 100 % at 960; the end of the loop wraps */
    CHECK(sq_tape_quantised(1000u, 0u, len) == 1000u && sq_tape_quantised(1000u, 50u, len) == 980u && sq_tape_quantised(1000u, 100u, len) == 960u);
    CHECK(sq_tape_quantised((uint16_t)(len - 10u), 100u, len) == 0u);
    /* shift by +100: 10 -> 110, 1000 -> 1100; by -200 wraps the first one to the end */
    sq_tape_shift(&pa, 3u, 100);
    CHECK(pa.tape_ev[1].on == 110u && pa.tape_ev[2].on == 1100u && pa.tape_ev[0].on == 5000u);
    sq_tape_shift(&pa, 3u, -200);
    sq_tape_range(&pa, 3u, &f, &n);
    CHECK(n == 3u && pa.tape_ev[f].on == 900u && pa.tape_ev[f + 2u].on == len - 90u && pa.tape_ev[f + 2u].note == 62u);
    /* the image: the chunk carries the tapes; back identical */
    pa.track[3].tape.quant = 60u; pa.track[2].tape.bars = 2u;
    k = sq_serialize(&pa, img, sizeof img);
    CHECK(k > 0u);
    memset(&pb, 0x33, sizeof pb);
    CHECK(sq_deserialize(&pb, img, k) == 0 && pb.tape_n == 4u && pb.tape_cnt[3] == 3u && pb.track[3].tape.quant == 60u && pb.track[2].tape.bars == 2u
          && !memcmp(pb.tape_ev, pa.tape_ev, 4u * sizeof(sq_tape_ev_t)) && !memcmp(&pa, &pb, sizeof pa));
    /* erase a window; clear */
    CHECK(sq_tape_erase(&pa, 3u, 800u, 1200u) == 2u && pa.tape_n == 2u && pa.tape_cnt[3] == 1u);
    CHECK(sq_tape_clear(&pa, 1u) == 1u && pa.tape_n == 1u && pa.tape_cnt[1] == 0u && pa.tape_ev[0].note == 62u);
    /* sanitise: a bad event is dropped, counts that do not add up are cut, bars out of range reset */
    pa.tape_ev[0].vel = 0u; pa.tape_cnt[3] = 9u; pa.track[5].tape.bars = 40u; pa.track[6].tape.quant = 200u;
    sq_project_sanitize(&pa);
    CHECK(pa.tape_n == 0u && pa.tape_cnt[3] == 0u && pa.track[5].tape.bars == 4u && pa.track[6].tape.quant == 100u);
    /* 0.10: the energy on the EXPO hits: 0 halves, 50 leaves, 100 doubles, within 2..64; a PLAIN step keeps its flag */
    CHECK(sq_expo_energy_hits(8u, 0u) == 4u && sq_expo_energy_hits(8u, 50u) == 8u && sq_expo_energy_hits(8u, 100u) == 16u && sq_expo_energy_hits(8u, 75u) == 12u);
    CHECK(sq_expo_energy_hits(2u, 0u) == 2u && sq_expo_energy_hits(64u, 100u) == 64u && sq_expo_energy_hits(3u, 0u) == 2u);
    {
        sq_step_t st; sq_step_default(&st); st.flags = SQ_STEP_ON | SQ_STEP_XOFF | 0x80u;
        sq_project_init(&pa); pa.step[0][0][3] = st; sq_project_sanitize(&pa);
        CHECK(pa.step[0][0][3].flags == (SQ_STEP_ON | SQ_STEP_XOFF));
    }
    /* the TAPE and CHAIN flags of a track survive the sanitiser (0.11 forgot TAPE once) */
    sq_project_init(&pa);
    pa.track[2].flags = SQ_TF_TAPE | SQ_TF_CHAIN; pa.track[3].flags = 0x80u | SQ_TF_DRUM; pa.track[4].flags = SQ_TF_BREAK | SQ_TF_DRUM | SQ_TF_SCALE;
    sq_project_sanitize(&pa);
    CHECK(pa.track[2].flags == (SQ_TF_TAPE | SQ_TF_CHAIN) && pa.track[3].flags == SQ_TF_DRUM && pa.track[4].flags == SQ_TF_BREAK);   /* (0.12: a BREAK is neither a drum nor in key) */
    /* full: 1536 events, the next is refused */
    sq_project_init(&pa);
    for (k = 0; k < SQ_TAPE_MAX; k++) CHECK(sq_tape_add(&pa, (uint8_t)(k & 15u), (uint16_t)(k * 3u % 6144u), 10u, 60u, 100u) == 0);
    CHECK(sq_tape_add(&pa, 0u, 1u, 1u, 60u, 100u) == -1 && pa.tape_n == SQ_TAPE_MAX);
    k = sq_serialize(&pa, img, sizeof img);
    CHECK(k > 9216u && sq_deserialize(&pb, img, k) == 0 && pb.tape_n == SQ_TAPE_MAX && !memcmp(&pa, &pb, sizeof pa));
}

static void test_expo(void)
{
    sq_expo_t x;
    uint32_t t[SQ_X_HITS_MAX], k, rng = 7u;
    sq_expo_default(&x);
    CHECK(x.shape == SQ_XS_OFF && x.hits == 8u && x.curve == 4 && x.span == SQ_XSPAN_BAR && x.gate == 60u);
    CHECK(sq_expo_span_ticks(SQ_XSPAN_STEP) == 0u && sq_expo_span_ticks(SQ_XSPAN_BEAT) == 24u && sq_expo_span_ticks(SQ_XSPAN_BAR) == 96u
          && sq_expo_span_ticks(SQ_XSPAN_4BARS) == 384u && sq_expo_span_ticks(99u) == 0u);
    /* even: curve 0 = the grid */
    x.shape = SQ_XS_RAMP; x.curve = 0; x.hits = 4u;
    sq_expo_times(&x, 1000u, t, 0);
    CHECK(t[0] == 0u && t[1] == 250u && t[2] == 500u && t[3] == 750u);
    /* RAMP +8: 16 x between the first gap and the last; the hits stay inside the span and in order */
    x.curve = 8; x.hits = 9u;
    sq_expo_times(&x, 100000u, t, 0);
    for (k = 1; k < 9u; k++) CHECK(t[k] > t[k - 1u] && t[k] < 100000u);
    CHECK(t[0] == 0u && (t[1] - t[0]) / (100000u - t[8]) >= 15u && (t[1] - t[0]) / (100000u - t[8]) <= 16u);
    /* the same backwards */
    x.curve = -8;
    sq_expo_times(&x, 100000u, t, 0);
    CHECK((100000u - t[8]) / (t[1] - t[0]) >= 15u && (100000u - t[8]) / (t[1] - t[0]) <= 16u);
    /* BOUNCE: symmetrical gaps */
    x.shape = SQ_XS_BOUNCE; x.curve = 6; x.hits = 8u;
    sq_expo_times(&x, 80000u, t, 0);
    for (k = 0; k < 8u; k++) {
        uint32_t g = (k + 1u < 8u ? t[k + 1u] : 80000u) - t[k], m = (7u - k + 1u < 8u ? t[7u - k + 1u] : 80000u) - t[7u - k];
        CHECK(g + 2u >= m && m + 2u >= g);
    }
    CHECK(t[4] - t[3] < t[1] - t[0]);
    /* jitter keeps the order, and never moves hit 0 */
    x.shape = SQ_XS_RAMP; x.curve = 3; x.hits = 16u; x.jitter = 50u;
    sq_expo_times(&x, 500000u, t, &rng);
    CHECK(t[0] == 0u);
    for (k = 1; k < 16u; k++) CHECK(t[k] > t[k - 1u] && t[k] < 500000u);
    /* the velocity curves */
    x.hits = 5u;
    x.vel = SQ_XV_FLAT; CHECK(sq_expo_vel(&x, 100u, 0u) == 100u && sq_expo_vel(&x, 100u, 4u) == 100u);
    x.vel = SQ_XV_FALL; CHECK(sq_expo_vel(&x, 100u, 0u) == 100u && sq_expo_vel(&x, 100u, 4u) == 40u && sq_expo_vel(&x, 100u, 2u) == 70u);
    x.vel = SQ_XV_RISE; CHECK(sq_expo_vel(&x, 100u, 0u) == 40u && sq_expo_vel(&x, 100u, 4u) == 100u);
    x.vel = SQ_XV_BOUNCE; CHECK(sq_expo_vel(&x, 100u, 2u) == 100u && sq_expo_vel(&x, 100u, 0u) == 40u && sq_expo_vel(&x, 1u, 0u) == 1u);
    x.vel = SQ_XV_FALL; CHECK(sq_expo_vel(&x, 127u, 9u) == sq_expo_vel(&x, 127u, 4u));   /* (past the last hit: the last) */
    x.vel = SQ_XV_GRACE; CHECK(sq_expo_vel(&x, 100u, 0u) == 75u && sq_expo_vel(&x, 100u, 1u) == 100u && sq_expo_vel(&x, 100u, 4u) == 100u);
}

static void test_divisions(void)
{
    uint8_t prev = 255u, d;
    for (d = 0; d < SQ_DIV_COUNT; d++) {
        CHECK(sq_div_ticks(d) < prev);          /* longest first */
        prev = sq_div_ticks(d);
    }
    CHECK(sq_div_ticks(SQ_DIV_1_16) == 6u);
    CHECK(sq_div_ticks(SQ_DIV_1_4) == 24u);
    CHECK(sq_div_ticks(SQ_DIV_1_8D) == 18u);
    CHECK(sq_div_ticks(SQ_DIV_1_8T) == 8u);
    CHECK(sq_div_ticks(SQ_DIV_1_1) == 96u);
    CHECK(sq_div_ticks(200u) == 6u);            /* out of range falls back to 1/16 */
}

static void test_init(void)
{
    static sq_project_t p;
    uint32_t t;
    memset(&p, 0xAA, sizeof p);
    sq_project_init(&p);
    CHECK(p.bpm == 128u && p.clock_mode == SQ_CLOCK_MASTER);
    CHECK(p.track[3].channel == 3u && p.track[3].length == 16u && p.track[3].division == SQ_DIV_1_16);
    for (t = 0; t < SQ_TRACKS; t++) CHECK(p.track[t].channel < SQ_MIDI_CH);
    CHECK(p.track[14].channel == 0u && p.track[15].channel == 1u);      /* 16 tracks on 14 channels: they share */
    CHECK(p.track[0].chord_mode == SQ_CHORD_BLOCK && p.track[0].swing == SQ_SWING_MIN);
    CHECK(p.track[5].lane_cc[0] == 74u && p.track[5].lane_base[0] == SQ_LANE_NONE);
    CHECK(p.step[15][7][63].nudge == 0 && p.step[15][7][63].note[0] == 60u && p.step[15][7][63].flags == 0u);
    CHECK(p.step[0][0][0].note[1] == SQ_NOTE_NONE && p.step[0][0][0].ratchet == 1u);
    CHECK(p.step[3][2][1].lane[0] == SQ_LANE_NONE && p.step[3][2][1].lane[3] == SQ_LANE_NONE);
    CHECK(p.lfo[15].enabled == 0u && p.lfo[0].rate == 6u);
    CHECK(p.scene[7].pattern[15] == 0u && p.scene[7].mute_mask == 0u);
}

static void test_offset(void)
{
    /* 125000 us = a 1/16 at 120 BPM */
    CHECK(sq_step_offset(125000u, 0u, 50u, 0) == 0);
    CHECK(sq_step_offset(125000u, 1u, 50u, 0) == 0);                  /* straight */
    CHECK(sq_step_offset(125000u, 0u, 66u, 0) == 0);                  /* even steps never swing */
    CHECK(sq_step_offset(125000u, 1u, 66u, 0) == 40000);              /* 66% -> 32% of a step late */
    CHECK(sq_step_offset(125000u, 1u, 75u, 0) == 62500);              /* 75% -> half a step late */
    CHECK(sq_step_offset(125000u, 0u, 50u, 20) == 25000);             /* nudge +20% */
    CHECK(sq_step_offset(125000u, 0u, 50u, -20) == -25000);           /* nudge -20%: early */
    CHECK(sq_step_offset(125000u, 0u, 50u, -50) == -62500);           /* half a step early at most */
    CHECK(sq_step_offset(125000u, 0u, 50u, -128) == -62500);          /* out of range is clamped */
    CHECK(sq_step_offset(125000u, 1u, 75u, 50) == 124999);            /* never leaves its step */
    CHECK(sq_step_offset(125000u, 1u, 250u, 127) == 124999);
    CHECK(sq_step_offset(125000u, 1u, 66u, -50) == 40000 - 62500);    /* swing and anticipation add up */
    CHECK(sq_step_offset(125000u, 1u, 75u, -50) == 0);
    CHECK(sq_step_offset(0u, 1u, 75u, 50) == 0);
    /* the slowest case must not overflow: 30 BPM, 1/1 */
    CHECK(sq_step_offset(96u * 83333u, 1u, 75u, 50) == (int32_t)(96u * 83333u) - 1);
    CHECK(sq_step_offset(96u * 83333u, 0u, 50u, -50) == -(int32_t)(96u * 83333u / 2u));
    CHECK(sq_step_offset(96u * 100000u, 1u, 75u, 50) == (int32_t)(96u * 100000u) - 1);   /* an external clock at 25 BPM */
}

static void test_long_gate(void)
{
    CHECK(sq_gate_sanitize(0u) == 1u);
    CHECK(sq_gate_sanitize(100u) == 100u);
    CHECK(sq_gate_sanitize(101u) == 101u);
    CHECK(sq_gate_sanitize(200u) == SQ_GATE_LONG_MAX);
    CHECK(sq_gate_us(50u, 100000u, 100000u) == 50000u);
    CHECK(sq_gate_us(101u, 100000u, 100000u) == 150000u);
    CHECK(sq_gate_us(102u, 100000u, 100000u) == 200000u);
    CHECK(sq_gate_us(164u, 100000u, 100000u) == 6400000u);
}

static void test_ramp(void)
{
    uint8_t i;
    CHECK(sq_ramp_velocity(100u, 0, 0u, 4u) == 100u && sq_ramp_velocity(100u, 0, 3u, 4u) == 100u);
    CHECK(sq_ramp_velocity(100u, 50, 0u, 1u) == 100u);                /* one hit: no ramp */
    CHECK(sq_ramp_velocity(100u, 100, 0u, 5u) == 1u);                 /* builds up from nothing... */
    CHECK(sq_ramp_velocity(100u, 100, 4u, 5u) == 100u);               /* ...to the step velocity */
    CHECK(sq_ramp_velocity(100u, -100, 0u, 5u) == 100u);              /* fades out */
    CHECK(sq_ramp_velocity(100u, -100, 4u, 5u) == 1u);
    CHECK(sq_ramp_velocity(100u, -50, 4u, 5u) == 50u);
    CHECK(sq_ramp_velocity(100u, 50, 0u, 5u) == 50u);
    CHECK(sq_ramp_velocity(127u, 100, 9u, 5u) == 127u);               /* index past the end is the last */
    for (i = 0; i < 8u; i++) CHECK(sq_ramp_velocity(90u, 60, i, 8u) >= 1u && sq_ramp_velocity(90u, 60, i, 8u) <= 127u);
    for (i = 1; i < 8u; i++) CHECK(sq_ramp_velocity(90u, 60, i, 8u) >= sq_ramp_velocity(90u, 60, (uint8_t)(i - 1u), 8u));
}

static void notes(sq_step_t *s, uint8_t a, uint8_t b, uint8_t c, uint8_t d)
{
    sq_step_default(s);
    s->note[0] = a; s->note[1] = b; s->note[2] = c; s->note[3] = d;
}

static void test_arp(void)
{
    sq_step_t s;
    uint8_t out[SQ_ARP_OUT], n;

    notes(&s, 67u, 60u, 64u, SQ_NOTE_NONE);                           /* played out of order: C E G */
    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_UP, 1u), out);
    CHECK(n == 3u && out[0] == 60u && out[1] == 64u && out[2] == 67u);

    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_DOWN, 1u), out);
    CHECK(n == 3u && out[0] == 67u && out[1] == 64u && out[2] == 60u);

    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_UPDN, 1u), out); /* C E G E */
    CHECK(n == 4u && out[0] == 60u && out[1] == 64u && out[2] == 67u && out[3] == 64u);

    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_UP, 2u), out);   /* two octaves */
    CHECK(n == 6u && out[3] == 72u && out[4] == 76u && out[5] == 79u);

    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_UP, 3u), out);
    CHECK(n == 9u && out[8] == 91u);

    notes(&s, 60u, SQ_NOTE_NONE, SQ_NOTE_NONE, SQ_NOTE_NONE);         /* one note */
    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_UPDN, 1u), out);
    CHECK(n == 1u && out[0] == 60u);
    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_UPDN, 2u), out); /* 60 72 */
    CHECK(n == 2u && out[0] == 60u && out[1] == 72u);

    notes(&s, 120u, 124u, 127u, SQ_NOTE_NONE);                        /* notes above 127 are dropped, not wrapped */
    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_UP, 2u), out);
    CHECK(n == 3u);

    notes(&s, SQ_NOTE_NONE, SQ_NOTE_NONE, SQ_NOTE_NONE, SQ_NOTE_NONE);
    CHECK(sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_UP, 1u), out) == 0u);

    notes(&s, 40u, 44u, 47u, 52u);                                    /* the longest: 4 notes, 3 octaves, up-down */
    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_UPDN, 3u), out);
    CHECK(n == 2u * 12u - 2u);
    CHECK(SQ_CHORD_MODE(SQ_CHORD_PACK(SQ_CHORD_ARP_RND, 3u)) == SQ_CHORD_ARP_RND);
    CHECK(SQ_CHORD_OCTS(SQ_CHORD_PACK(SQ_CHORD_ARP_RND, 3u)) == 3u);
}

static void test_euclid(void)
{
    uint8_t bits[SQ_STEPS];
    uint32_t len, pulses, rot, i, count;

    /* every (pulses, len): exactly `pulses` hits, first step hits, hits as even as they can be */
    for (len = 1; len <= 64u; len++)
        for (pulses = 0; pulses <= len; pulses++) {
            uint32_t first = 999u, last = 0u, mingap = 999u, maxgap = 0u;
            sq_euclid((uint8_t)pulses, (uint8_t)len, 0u, bits);
            count = 0;
            for (i = 0; i < len; i++) {
                if (!bits[i]) continue;
                if (count) { uint32_t g = i - last; if (g < mingap) mingap = g; if (g > maxgap) maxgap = g; }
                else first = i;
                last = i;
                count++;
            }
            CHECK(count == pulses);
            if (pulses) CHECK(first == 0u);
            if (pulses > 1u) {
                uint32_t wrap = len - last + first;            /* the gap that closes the circle */
                if (wrap < mingap) mingap = wrap;
                if (wrap > maxgap) maxgap = wrap;
                CHECK(maxgap - mingap <= 1u);
            }
        }

    sq_euclid(3u, 8u, 0u, bits);                                  /* x..x..x. */
    CHECK(bits[0] && !bits[1] && !bits[2] && bits[3] && !bits[4] && !bits[5] && bits[6] && !bits[7]);

    /* rotation moves every hit by the same amount, the count does not change */
    sq_euclid(5u, 16u, 0u, bits);
    {
        uint8_t rb[SQ_STEPS];
        for (rot = 0; rot < 16u; rot++) {
            sq_euclid(5u, 16u, (uint8_t)rot, rb);
            for (i = 0; i < 16u; i++) CHECK(rb[(i + rot) % 16u] == bits[i]);
        }
    }
    sq_euclid(4u, 16u, 0u, bits);                                 /* four on the floor */
    CHECK(bits[0] && bits[4] && bits[8] && bits[12]);
}

static void test_tools(void)
{
    static sq_step_t row[SQ_STEPS];
    uint32_t rng = 1234u, i, n;

    sq_row_clear(row);
    for (i = 0; i < SQ_STEPS; i++) CHECK(!(row[i].flags & SQ_STEP_ON));

    row[0].flags = SQ_STEP_ON; row[0].note[0] = 10u;
    row[1].flags = SQ_STEP_ON; row[1].note[0] = 11u;
    row[2].note[0] = 12u;
    row[3].note[0] = 13u;
    row[4].note[0] = 99u;                                         /* beyond length 4: untouched */

    sq_row_reverse(row, 4u);
    CHECK(row[0].note[0] == 13u && row[1].note[0] == 12u && row[2].note[0] == 11u && row[3].note[0] == 10u);
    CHECK(row[2].flags & SQ_STEP_ON && row[3].flags & SQ_STEP_ON && row[4].note[0] == 99u);
    sq_row_reverse(row, 4u);
    CHECK(row[0].note[0] == 10u && row[3].note[0] == 13u);

    sq_row_shift(row, 4u, 1);                                     /* right: 13 10 11 12 */
    CHECK(row[0].note[0] == 13u && row[1].note[0] == 10u && row[2].note[0] == 11u && row[3].note[0] == 12u);
    sq_row_shift(row, 4u, -1);                                    /* left again */
    CHECK(row[0].note[0] == 10u && row[1].note[0] == 11u && row[2].note[0] == 12u && row[3].note[0] == 13u);
    CHECK(row[4].note[0] == 99u);
    sq_row_shift(row, 1u, 1);                                     /* length 1: nothing to do */
    CHECK(row[0].note[0] == 10u);

    sq_row_clear(row);
    sq_row_euclid(row, 16u, 4u, 0u);
    n = 0;
    for (i = 0; i < 16u; i++) n += (row[i].flags & SQ_STEP_ON) ? 1u : 0u;
    CHECK(n == 4u && (row[0].flags & SQ_STEP_ON) && (row[4].flags & SQ_STEP_ON));
    for (i = 16u; i < SQ_STEPS; i++) CHECK(!(row[i].flags & SQ_STEP_ON));
    sq_row_euclid(row, 16u, 0u, 0u);                              /* 0 pulses clears the length */
    for (i = 0; i < 16u; i++) CHECK(!(row[i].flags & SQ_STEP_ON));

    sq_row_random(row, 64u, 0u, &rng);
    for (i = 0; i < 64u; i++) CHECK(!(row[i].flags & SQ_STEP_ON));
    sq_row_random(row, 64u, 100u, &rng);
    for (i = 0; i < 64u; i++) CHECK(row[i].flags & SQ_STEP_ON);
    sq_row_random(row, 64u, 50u, &rng);
    n = 0;
    for (i = 0; i < 64u; i++) n += (row[i].flags & SQ_STEP_ON) ? 1u : 0u;
    CHECK(n > 16u && n < 48u);                                    /* about half, never all or none */
}

static void test_advance(void)
{
    sq_track_cfg_t c;
    sq_track_rt_t rt;
    uint32_t rng = 7u, seen[64] = {0}, i;
    uint8_t wraps = 0u;

    memset(&c, 0, sizeof c); memset(&rt, 0, sizeof rt);
    c.length = 4u; c.direction = SQ_DIR_FWD; rt.ping_dir = 1;
    for (i = 0; i < 8u; i++) wraps = (uint8_t)(wraps + sq_advance_step(&c, &rt, &rng));
    CHECK(wraps == 2u && rt.step == 0u && rt.loop_count == 2u);

    c.direction = SQ_DIR_PINGPONG; rt.step = 0u; rt.ping_dir = 1;
    {
        uint8_t want[] = {1, 2, 3, 2, 1, 0, 1};
        for (i = 0; i < sizeof want; i++) { sq_advance_step(&c, &rt, &rng); CHECK(rt.step == want[i]); }
    }

    c.direction = SQ_DIR_RANDOM; c.length = 16u;
    for (i = 0; i < 4000u; i++) { sq_advance_step(&c, &rt, &rng); CHECK(rt.step < 16u); seen[rt.step]++; }
    for (i = 0; i < 16u; i++) CHECK(seen[i] > 100u);              /* every step gets visited */
}


static void test_advance_loop(void)
{
    sq_track_cfg_t c;
    sq_track_rt_t rt;
    uint32_t rng = 99u, i, seen[64] = {0};
    memset(&c, 0, sizeof c); memset(&rt, 0, sizeof rt);
    c.length = 12u; c.start = 8u; c.direction = SQ_DIR_FWD; rt.ping_dir = 1; rt.step = 8u;     /* the loop is steps 9-12 */
    {
        uint8_t want[] = {9, 10, 11, 8, 9, 10, 11, 8};
        for (i = 0; i < sizeof want; i++) { uint8_t w = sq_advance_step(&c, &rt, &rng); CHECK(rt.step == want[i]); CHECK(w == (want[i] == 8u)); }
    }
    CHECK(rt.loop_count == 2u);
    rt.step = 3u; CHECK(sq_advance_step(&c, &rt, &rng) == 1u);     /* outside the loop (it was shortened): a wrap onto the first step (0.10: not past it) */
    CHECK(rt.step == 8u);
    rt.step = 40u; sq_advance_step(&c, &rt, &rng);
    CHECK(rt.step == 8u);

    c.direction = SQ_DIR_REV; rt.step = 8u; rt.loop_count = 0u;
    {
        uint8_t want[] = {11, 10, 9, 8, 11};
        for (i = 0; i < sizeof want; i++) { sq_advance_step(&c, &rt, &rng); CHECK(rt.step == want[i]); }
    }
    CHECK(rt.loop_count == 2u);

    c.direction = SQ_DIR_PINGPONG; rt.step = 8u; rt.ping_dir = 1;
    {
        uint8_t want[] = {9, 10, 11, 10, 9, 8, 9, 10};
        for (i = 0; i < sizeof want; i++) { sq_advance_step(&c, &rt, &rng); CHECK(rt.step == want[i]); }
    }
    c.start = 11u;                                                 /* a loop of one step */
    for (i = 0; i < 6u; i++) { sq_advance_step(&c, &rt, &rng); CHECK(rt.step == 11u); }

    c.start = 5u; c.length = 13u; c.direction = SQ_DIR_RANDOM;
    for (i = 0; i < 4000u; i++) { sq_advance_step(&c, &rt, &rng); CHECK(rt.step >= 5u && rt.step < 13u); seen[rt.step]++; }
    for (i = 5u; i < 13u; i++) CHECK(seen[i] > 200u);

    c.start = 70u; c.length = 4u;                                 /* nonsense: treated as a loop from 0 */
    rt.step = 0u; c.direction = SQ_DIR_FWD;
    sq_advance_step(&c, &rt, &rng);
    CHECK(rt.step == 1u);
}

static void test_arp_modes(void)
{
    sq_step_t s;
    uint8_t out[SQ_ARP_OUT], n, i;
    notes(&s, 67u, 60u, 64u, SQ_NOTE_NONE);                           /* entered G C E: sorted C E G */

    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_DNUP, 1u), out);  /* G E C E */
    CHECK(n == 4u && out[0] == 67u && out[1] == 64u && out[2] == 60u && out[3] == 64u);
    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_UPDN2, 1u), out); /* C E G G E C */
    CHECK(n == 6u && out[0] == 60u && out[2] == 67u && out[3] == 67u && out[5] == 60u);
    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_CONV, 1u), out);  /* C G E */
    CHECK(n == 3u && out[0] == 60u && out[1] == 67u && out[2] == 64u);
    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_DIV, 1u), out);   /* E G C */
    CHECK(n == 3u && out[0] == 64u && out[1] == 67u && out[2] == 60u);
    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_PLAYED, 1u), out);/* G C E */
    CHECK(n == 3u && out[0] == 67u && out[1] == 60u && out[2] == 64u);
    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_THUMB, 1u), out); /* C E C G */
    CHECK(n == 4u && out[0] == 60u && out[1] == 64u && out[2] == 60u && out[3] == 67u);
    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_PINKY, 1u), out); /* C G E G */
    CHECK(n == 4u && out[0] == 60u && out[1] == 67u && out[2] == 64u && out[3] == 67u);
    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_RND, 1u), out);   /* the caller picks: all notes, ascending */
    CHECK(n == 3u && out[0] == 60u && out[2] == 67u);
    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_WALK, 1u), out);
    CHECK(n == 3u && out[0] == 60u && out[2] == 67u);

    notes(&s, 60u, 60u, 64u, SQ_NOTE_NONE);                           /* a note entered twice plays once */
    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_UP, 1u), out);
    CHECK(n == 2u);
    notes(&s, 60u, SQ_NOTE_NONE, SQ_NOTE_NONE, SQ_NOTE_NONE);         /* one note: every mode plays it */
    for (i = 1; i < SQ_CHORD_COUNT; i++) {
        n = sq_arp_build(&s, SQ_CHORD_PACK(i, 1u), out);
        CHECK(n == 1u && out[0] == 60u);
    }
    notes(&s, 60u, 64u, SQ_NOTE_NONE, SQ_NOTE_NONE);                  /* two notes */
    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_THUMB, 1u), out); CHECK(n == 2u && out[0] == 60u && out[1] == 64u);
    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_DNUP, 1u), out);  CHECK(n == 2u && out[0] == 64u && out[1] == 60u);
    n = sq_arp_build(&s, SQ_CHORD_PACK(SQ_CHORD_ARP_DIV, 1u), out);   CHECK(n == 2u && out[0] == 60u && out[1] == 64u);

    /* the longest of every mode (4 notes x 3 octaves) fits the buffer, and every note it returns is a note of the chord */
    notes(&s, 40u, 44u, 47u, 52u);
    for (i = 1; i < SQ_CHORD_COUNT; i++) {
        uint8_t k, guard[SQ_ARP_OUT + 8u];
        memset(guard, 0x5A, sizeof guard);
        n = sq_arp_build(&s, SQ_CHORD_PACK(i, 3u), guard);
        CHECK(n >= 12u && n <= SQ_ARP_OUT);
        for (k = SQ_ARP_OUT; k < sizeof guard; k++) CHECK(guard[k] == 0x5Au);
        for (k = 0; k < n; k++) CHECK(guard[k] >= 40u && guard[k] <= 88u);
    }
}

static void test_rec_target(void)
{
    uint8_t st; int8_t nu;
    sq_rec_target(4u, 0u, 16u, SQ_DIR_FWD, 10u, 0u, &st, &nu);   CHECK(st == 4u && nu == 10);       /* a little late */
    sq_rec_target(4u, 0u, 16u, SQ_DIR_FWD, 49u, 0u, &st, &nu);   CHECK(st == 4u && nu == 49);
    sq_rec_target(4u, 0u, 16u, SQ_DIR_FWD, 50u, 0u, &st, &nu);   CHECK(st == 5u && nu == -50);      /* a little early for the next */
    sq_rec_target(4u, 0u, 16u, SQ_DIR_FWD, 95u, 0u, &st, &nu);   CHECK(st == 5u && nu == -5);
    sq_rec_target(15u, 0u, 16u, SQ_DIR_FWD, 90u, 0u, &st, &nu);  CHECK(st == 0u && nu == -10);      /* the loop wraps */
    sq_rec_target(11u, 8u, 12u, SQ_DIR_FWD, 90u, 0u, &st, &nu);  CHECK(st == 8u && nu == -10);      /* ...to its own start */
    sq_rec_target(4u, 0u, 16u, SQ_DIR_FWD, 95u, 1u, &st, &nu);   CHECK(st == 5u && nu == 0);        /* quantised: nearest step */
    sq_rec_target(4u, 0u, 16u, SQ_DIR_FWD, 20u, 1u, &st, &nu);   CHECK(st == 4u && nu == 0);
    sq_rec_target(4u, 0u, 16u, SQ_DIR_REV, 90u, 0u, &st, &nu);   CHECK(st == 3u && nu == -10);
    sq_rec_target(0u, 0u, 16u, SQ_DIR_REV, 90u, 0u, &st, &nu);   CHECK(st == 15u && nu == -10);
    sq_rec_target(8u, 8u, 12u, SQ_DIR_REV, 90u, 0u, &st, &nu);   CHECK(st == 11u && nu == -10);
    sq_rec_target(4u, 0u, 16u, SQ_DIR_PINGPONG, 90u, 0u, &st, &nu); CHECK(st == 4u && nu == 50);   /* cannot know the next step */
    sq_rec_target(4u, 0u, 16u, SQ_DIR_RANDOM, 99u, 0u, &st, &nu);   CHECK(st == 4u && nu == 50);
    sq_rec_target(200u, 0u, 16u, SQ_DIR_FWD, 200u, 0u, &st, &nu);   CHECK(st < 16u && nu >= -50 && nu <= 50);
    sq_rec_target(0u, 0u, 0u, SQ_DIR_FWD, 60u, 0u, &st, &nu);       CHECK(st == 0u);
}

static void test_names(void)
{
    char b[8];
    sq_note_name(60u, b);  CHECK(!strcmp(b, "C4"));
    sq_note_name(61u, b);  CHECK(!strcmp(b, "C#4"));
    sq_note_name(69u, b);  CHECK(!strcmp(b, "A4"));
    sq_note_name(0u, b);   CHECK(!strcmp(b, "C-1"));
    sq_note_name(1u, b);   CHECK(!strcmp(b, "C#-1"));
    sq_note_name(11u, b);  CHECK(!strcmp(b, "B-1"));
    sq_note_name(12u, b);  CHECK(!strcmp(b, "C0"));
    sq_note_name(36u, b);  CHECK(!strcmp(b, "C2"));
    sq_note_name(127u, b); CHECK(!strcmp(b, "G9"));
    sq_note_name(255u, b); CHECK(!strcmp(b, "---"));
    sq_note_name(128u, b); CHECK(!strcmp(b, "---"));
}

static void test_lfo(void)
{
    sq_lfo_t l;
    uint32_t tick, seen_hi = 0, seen_lo = 0;
    uint8_t shape;
    int16_t prev;
    sq_lfo_default(&l);
    CHECK(sq_lfo_ticks(6u) == 96u && sq_lfo_ticks(0u) == 1536u && sq_lfo_ticks(15u) == 3u && sq_lfo_ticks(99u) == 96u);
    for (tick = 1; tick < SQ_LFO_RATES; tick++) if (tick != SQ_LFO_RATES_STRAIGHT) CHECK(sq_lfo_ticks((uint8_t)tick) < sq_lfo_ticks((uint8_t)(tick - 1u)));   /* (0.13: then the triplets) */
    CHECK(sq_lfo_ticks(16u) == 16u && sq_lfo_ticks(17u) == 8u && sq_lfo_ticks(18u) == 4u && sq_lfo_ticks(19u) == 2u);

    /* sine over one bar: starts at 0, peaks a quarter in, 0 at half, trough at three quarters */
    l.shape = SQ_LFO_SINE; l.rate = 6u; l.depth = 127u; l.center = 64u;
    CHECK(sq_lfo_wave(&l, 0u, 0u, 0u) == 0);
    CHECK(sq_lfo_wave(&l, 0u, 24u, 0u) >= 126);
    CHECK(sq_lfo_wave(&l, 0u, 48u, 0u) == 0);
    CHECK(sq_lfo_wave(&l, 0u, 72u, 0u) <= -126);
    CHECK(sq_lfo_wave(&l, 0u, 96u, 0u) == 0);                        /* the cycle repeats */
    CHECK(sq_lfo_wave(&l, 0u, 96u * 7u + 24u, 0u) >= 126);
    CHECK(sq_lfo_cc(&l, 0u, 24u, 0u) == 127u);                       /* 64 + 126 clamps */
    CHECK(sq_lfo_cc(&l, 0u, 72u, 0u) <= 1u);
    CHECK(sq_lfo_cc(&l, 0u, 0u, 0u) == 64u);
    l.depth = 0u;
    CHECK(sq_lfo_cc(&l, 0u, 24u, 0u) == 64u && sq_lfo_offset(&l, 0u, 24u, 0u) == 0);
    l.depth = 64u; l.center = 100u;
    CHECK(sq_lfo_cc(&l, 0u, 24u, 0u) >= 160u - 100u - 1u + 100u - 60u);     /* ~ 100 + 63 -> 127 */
    l.center = 30u;
    CHECK(sq_lfo_cc(&l, 0u, 72u, 0u) == 0u);                                  /* 30 - 63 clamps at 0 */
    CHECK(sq_lfo_offset(&l, 0u, 24u, 0u) >= 31 && sq_lfo_offset(&l, 0u, 24u, 0u) <= 32);
    l.depth = 127u; l.center = 64u;

    /* the fraction of a tick moves the wave smoothly between two ticks */
    l.shape = SQ_LFO_RAMP_UP; l.rate = 8u;                          /* a half note = 48 ticks */
    CHECK(sq_lfo_wave(&l, 0u, 0u, 0u) == -128);
    CHECK(sq_lfo_wave(&l, 0u, 24u, 0u) == 0);
    CHECK(sq_lfo_wave(&l, 0u, 47u, 65535u) >= 126);
    prev = sq_lfo_wave(&l, 0u, 10u, 0u);
    CHECK(sq_lfo_wave(&l, 0u, 10u, 32768u) > prev && sq_lfo_wave(&l, 0u, 10u, 32768u) < sq_lfo_wave(&l, 0u, 11u, 0u));
    l.shape = SQ_LFO_RAMP_DN;
    CHECK(sq_lfo_wave(&l, 0u, 0u, 0u) == 127 && sq_lfo_wave(&l, 0u, 24u, 0u) == -1);
    l.shape = SQ_LFO_SQUARE;
    CHECK(sq_lfo_wave(&l, 0u, 23u, 65535u) == 127 && sq_lfo_wave(&l, 0u, 24u, 0u) == -128);
    l.shape = SQ_LFO_TRI;
    CHECK(sq_lfo_wave(&l, 0u, 0u, 0u) == -128 && sq_lfo_wave(&l, 0u, 24u, 0u) >= 126 && sq_lfo_wave(&l, 0u, 47u, 65535u) <= -126);
    l.flags = SQ_LF_INVERT;
    CHECK(sq_lfo_wave(&l, 0u, 0u, 0u) == 127);                       /* upside down */
    l.flags = 0u;

    /* phase: a quarter turn of offset moves the peak */
    l.shape = SQ_LFO_SINE; l.rate = 6u; l.phase = 32u;               /* 32/128 of a turn */
    CHECK(sq_lfo_wave(&l, 0u, 0u, 0u) >= 126);
    l.phase = 0u;

    /* every shape stays inside -128..127 and moves, at every rate */
    for (shape = 0; shape < SQ_LFO_SHAPES; shape++) {
        uint32_t r;
        for (r = 0; r < SQ_LFO_RATES; r++) {
            int32_t lo = 999, hi = -999;
            l.shape = shape; l.rate = (uint8_t)r;
            for (tick = 0; tick < 4000u; tick += 1u) {
                int16_t v = sq_lfo_wave(&l, 3u, tick, (uint16_t)(tick * 977u));
                if (v < lo) lo = v;
                if (v > hi) hi = v;
                CHECK(v >= -128 && v <= 127);
            }
            CHECK(hi - lo > 100);
        }
    }

    /* sample and hold: constant inside a cycle, changing from one cycle to the next, different per LFO index */
    l.shape = SQ_LFO_SH; l.rate = 10u;                               /* a quarter: 24 ticks */
    CHECK(sq_lfo_wave(&l, 0u, 0u, 0u) == sq_lfo_wave(&l, 0u, 23u, 65535u));
    for (tick = 0; tick < 200u; tick += 24u) {
        if (sq_lfo_wave(&l, 0u, tick, 0u) > 0) seen_hi++; else seen_lo++;
        CHECK(sq_lfo_wave(&l, 0u, tick, 0u) == sq_lfo_wave(&l, 0u, tick + 12u, 0u));
    }
    CHECK(seen_hi > 1u && seen_lo > 1u);
    {
        uint32_t differ = 0;
        for (tick = 0; tick < 480u; tick += 24u) if (sq_lfo_wave(&l, 0u, tick, 0u) != sq_lfo_wave(&l, 5u, tick, 0u)) differ++;
        CHECK(differ > 10u);
    }
    /* smooth random: no jump at the cycle boundary */
    l.shape = SQ_LFO_SMOOTH;
    for (tick = 24u; tick < 480u; tick += 24u) {
        int32_t d = (int32_t)sq_lfo_wave(&l, 2u, tick, 0u) - (int32_t)sq_lfo_wave(&l, 2u, tick - 1u, 65535u);
        CHECK(d >= -6 && d <= 6);
    }
    /* decay: starts high, ends low, falling */
    l.shape = SQ_LFO_DECAY; l.rate = 6u;
    CHECK(sq_lfo_wave(&l, 0u, 0u, 0u) >= 126 && sq_lfo_wave(&l, 0u, 95u, 65535u) <= -126);
    CHECK(sq_lfo_wave(&l, 0u, 20u, 0u) > sq_lfo_wave(&l, 0u, 40u, 0u) && sq_lfo_wave(&l, 0u, 40u, 0u) > sq_lfo_wave(&l, 0u, 80u, 0u));
}

static int steps_equal(const sq_step_t *a, const sq_step_t *b) { return !memcmp(a, b, sizeof *a); }

static void test_cook_and_tools(void)
{
    static sq_step_t row[SQ_STEPS], keep[SQ_STEPS];
    uint32_t rng = 4242u, i, n, changed, k;
    uint8_t len;

    sq_row_clear(row);
    for (i = 0; i < 16u; i += 4u) { row[i].flags = SQ_STEP_ON | SQ_STEP_SET; row[i].note[0] = (uint8_t)(36u + i); }
    memcpy(keep, row, sizeof row);

    sq_row_cook(row, 16u, 0u, &rng);                              /* no heat, no change */
    CHECK(!memcmp(row, keep, sizeof row));

    changed = 0;
    for (k = 0; k < 40u; k++) {
        memcpy(row, keep, sizeof row);
        sq_row_cook(row, 16u, 100u, &rng);
        if (memcmp(row, keep, sizeof row)) changed++;
        CHECK(row[0].flags & SQ_STEP_ON);                         /* the first step is never taken away */
        for (i = 16u; i < SQ_STEPS; i++) CHECK(steps_equal(&row[i], &keep[i]));   /* outside the length: untouched */
        for (i = 0; i < 16u; i++) {
            CHECK(row[i].velocity >= 1u && row[i].velocity <= 127u);
            CHECK(row[i].ratchet >= 1u && row[i].ratchet <= SQ_RATCHET_MAX);
            CHECK(row[i].condition < SQ_COND_COUNT && row[i].condition != SQ_COND_FILL && row[i].condition != SQ_COND_NOT_FILL);
            CHECK(row[i].length >= 1u && row[i].length <= 100u);
            CHECK(row[i].chance <= 100u);
        }
    }
    CHECK(changed == 40u);

    /* more heat, more change (on average) */
    {
        uint32_t diff_lo = 0, diff_hi = 0;
        for (k = 0; k < 200u; k++) {
            memcpy(row, keep, sizeof row); sq_row_cook(row, 16u, 15u, &rng);
            for (i = 0; i < 16u; i++) diff_lo += !steps_equal(&row[i], &keep[i]);
            memcpy(row, keep, sizeof row); sq_row_cook(row, 16u, 90u, &rng);
            for (i = 0; i < 16u; i++) diff_hi += !steps_equal(&row[i], &keep[i]);
        }
        CHECK(diff_hi > diff_lo * 2u);
        CHECK(diff_lo > 0u);
    }
    /* a new hit plays the pattern's own note */
    {
        uint32_t newhits = 0, wrong = 0;
        for (k = 0; k < 100u; k++) {
            memcpy(row, keep, sizeof row); sq_row_cook(row, 16u, 80u, &rng);
            for (i = 0; i < 16u; i += 1u)
                if ((row[i].flags & SQ_STEP_ON) && !(keep[i].flags & SQ_STEP_ON)) { newhits++; if (row[i].note[0] < 36u || row[i].note[0] > 48u) wrong++; }
        }
        CHECK(newhits > 50u && wrong == 0u);
    }
    /* an empty pattern: cooking does not crash and does not invent notes out of nothing but defaults */
    sq_row_clear(row);
    for (k = 0; k < 20u; k++) sq_row_cook(row, 16u, 100u, &rng);
    for (i = 0; i < 16u; i++) CHECK(row[i].note[0] == 60u || (row[i].flags & SQ_STEP_ON) == 0u);

    /* invert */
    sq_row_clear(row);
    row[1].flags = SQ_STEP_ON; row[3].flags = SQ_STEP_ON;
    sq_row_invert(row, 4u);
    CHECK((row[0].flags & SQ_STEP_ON) && !(row[1].flags & SQ_STEP_ON) && (row[2].flags & SQ_STEP_ON) && !(row[3].flags & SQ_STEP_ON));
    CHECK(!(row[4].flags & SQ_STEP_ON));

    /* humanise */
    sq_row_clear(row);
    row[0].flags = SQ_STEP_ON; row[1].flags = SQ_STEP_ON; row[2].velocity = 33u;
    for (k = 0; k < 100u; k++) sq_row_humanize(row, 8u, &rng);
    CHECK(row[2].velocity == 33u && row[2].nudge == 0);          /* rests are not touched */
    CHECK(row[0].velocity >= 1u && row[0].velocity <= 127u && row[0].nudge >= -50 && row[0].nudge <= 50);
    CHECK(row[0].velocity != 100u || row[1].velocity != 100u);

    /* double */
    sq_row_clear(row);
    row[0].flags = SQ_STEP_ON; row[0].note[0] = 10u; row[3].flags = SQ_STEP_ON; row[3].note[0] = 13u;
    len = sq_row_double(row, 4u, 64u);
    CHECK(len == 8u && row[4].note[0] == 10u && (row[4].flags & SQ_STEP_ON) && (row[7].flags & SQ_STEP_ON) && row[7].note[0] == 13u);
    len = sq_row_double(row, 8u, 64u); CHECK(len == 16u && row[12].note[0] == 10u);
    len = sq_row_double(row, 40u, 64u); CHECK(len == 64u && steps_equal(&row[40], &row[0]));
    len = sq_row_double(row, 64u, 64u); CHECK(len == 64u);
    len = sq_row_double(row, 0u, 64u); CHECK(len == 2u);
    {   /* a loop that starts at step 33 has 32 steps of room: nothing is written past the pattern (0.3 did) */
        static sq_step_t two[2][SQ_STEPS];
        sq_row_clear(two[0]); sq_row_clear(two[1]);
        two[0][40].flags = SQ_STEP_ON; two[1][0].note[0] = 99u;
        len = sq_row_double(two[0] + 32, 32u, 32u);
        CHECK(len == 32u && two[1][0].note[0] == 99u);
        len = sq_row_double(two[0] + 32, 20u, 32u);
        CHECK(len == 32u && (two[0][60].flags & SQ_STEP_ON) && two[1][0].note[0] == 99u);
    }

    /* tools on the loop only: hand them row + start */
    sq_row_clear(row);
    for (i = 0; i < 16u; i++) { row[i].note[0] = (uint8_t)i; row[i].flags = (i & 1u) ? SQ_STEP_ON : 0u; }
    sq_row_reverse(row + 4, 4u);                                  /* steps 5-8 */
    CHECK(row[3].note[0] == 3u && row[4].note[0] == 7u && row[7].note[0] == 4u && row[8].note[0] == 8u);
    n = 0;
    sq_row_euclid(row + 8, 8u, 2u, 0u);
    for (i = 0; i < 8u; i++) n += (row[i].flags & SQ_STEP_ON) ? 1u : 0u;
    CHECK(n == 4u);                                               /* steps before the loop are untouched */
}

static void test_sanitize(void)
{
    static sq_project_t p;
    uint32_t t;
    sq_project_init(&p);
    memset(&p, 0xFF, sizeof p);
    sq_project_sanitize(&p);
    CHECK(p.bpm == 128u && p.clock_mode == SQ_CLOCK_MASTER);
    for (t = 0; t < SQ_TRACKS; t++) {
        const sq_track_cfg_t *c = &p.track[t];
        CHECK(c->channel < SQ_MIDI_CH && c->length >= 1u && c->length <= 64u && c->start < c->length);
        CHECK(c->division < SQ_DIV_COUNT && c->direction < SQ_DIR_COUNT && c->transpose >= -48 && c->transpose <= 48);
        CHECK(c->initial_pattern < SQ_PATTERNS && SQ_CHORD_MODE(c->chord_mode) < SQ_CHORD_COUNT && SQ_CHORD_OCTS(c->chord_mode) <= 3u);
        CHECK(c->swing >= SQ_SWING_MIN && c->swing <= SQ_SWING_MAX && c->vel_offset >= -63 && c->vel_offset <= 63);
        CHECK(c->hum_time <= 50u && c->hum_vel <= 50u);
        CHECK(c->lane_cc[0] == SQ_LANE_NONE && c->lane_base[3] == SQ_LANE_NONE);
    }
    CHECK(p.scene[3].pattern[9] == 0u);
    CHECK(p.lfo[4].shape == SQ_LFO_SINE && p.lfo[4].dest == SQ_LD_CC && p.lfo[4].target < SQ_MIDI_CH && p.lfo[4].depth <= 127u && p.lfo[4].enabled == 1u);
    CHECK(p.step[9][5][33].velocity == 127u && p.step[9][5][33].ratchet == SQ_RATCHET_MAX && p.step[9][5][33].chance == 100u);
    CHECK(p.step[9][5][33].note[2] == SQ_NOTE_NONE && p.step[9][5][33].lane[1] == SQ_LANE_NONE);
    CHECK(p.step[9][5][33].nudge == -1 && p.step[9][5][33].ramp == -1);   /* 0xFF as a signed byte is in range */
    CHECK(p.step[9][5][33].flags == (SQ_STEP_ON | SQ_STEP_SET | SQ_STEP_LOCK | SQ_STEP_XOFF | SQ_STEP_TIE | SQ_STEP_SLIDE));   /* (0.10: PLAIN is a flag too; 0.13 SLIDE) */
    p.step[1][1][1].nudge = 100; p.step[1][1][1].ramp = -120; p.step[1][1][1].condition = 99;
    sq_project_sanitize(&p);
    CHECK(p.step[1][1][1].nudge == 50 && p.step[1][1][1].ramp == -100 && p.step[1][1][1].condition == SQ_COND_ALWAYS);
}


static void test_scales(void)
{
    static sq_project_t p;
    uint32_t sc, root, n, k;
    char buf[8];
    CHECK(SQ_SCALES == 16u);
    CHECK(sq_scale_mask(SQ_SC_CHROMATIC) == 0xFFFu && sq_scale_mask(SQ_SC_MAJOR) == 0xAB5u && sq_scale_mask(SQ_SC_PENT_MINOR) == 0x4A9u);
    CHECK(sq_scale_mask(200u) == 0xFFFu);
    for (sc = 0; sc < SQ_SCALES; sc++) {
        uint16_t m = sq_scale_mask((uint8_t)sc);
        CHECK(m & 1u);                                               /* the root is always in */
        CHECK(strlen(sq_scale_name((uint8_t)sc)) <= 7u && strlen(sq_scale_long_name((uint8_t)sc)) > 0u);
        for (root = 0; root < 12u; root++)
            for (n = 0; n < 128u; n++) {
                uint8_t o = sq_scale_snap((uint8_t)n, (uint8_t)root, (uint8_t)sc);
                int32_t d = (int32_t)o - (int32_t)n, ad = d < 0 ? -d : d;
                CHECK((m >> ((o + 120u - root) % 12u)) & 1u);        /* the result belongs to the key */
                CHECK(ad <= 2 || n < 4u || n > 123u);                /* no gap of these scales is wider than four (but at the ends of the range) */
                CHECK(sq_scale_snap(o, (uint8_t)root, (uint8_t)sc) == o);   /* and snapping again changes nothing */
                if (ad) {                                            /* nothing in the key is nearer; a tie goes down */
                    for (k = 1; k < (uint32_t)ad; k++) {
                        int32_t a = (int32_t)n - (int32_t)k, b = (int32_t)n + (int32_t)k;
                        CHECK(a < 0 || !((m >> ((uint32_t)(a + 120 - (int32_t)root) % 12u)) & 1u));
                        CHECK(b > 127 || !((m >> ((uint32_t)(b + 120 - (int32_t)root) % 12u)) & 1u));
                    }
                    if (d > 0) { int32_t a = (int32_t)n - ad; CHECK(a < 0 || !((m >> ((uint32_t)(a + 120 - (int32_t)root) % 12u)) & 1u)); }
                }
            }
    }
    CHECK(sq_scale_snap(61u, 0u, SQ_SC_MAJOR) == 60u);               /* C#4 in C major: C and D are as near, C wins */
    CHECK(sq_scale_snap(63u, 0u, SQ_SC_MAJOR) == 62u);
    CHECK(sq_scale_snap(60u, 2u, SQ_SC_MAJOR) == 59u);               /* C4 in D major: B3 (a tie, down) */
    CHECK(sq_scale_snap(64u, 0u, SQ_SC_DORIAN) == 63u);              /* E4 in C dorian: Eb */
    CHECK(sq_scale_snap(64u, 9u, SQ_SC_MINOR) == 64u);               /* E is the fifth of A minor */
    CHECK(sq_scale_snap(66u, 0u, SQ_SC_PENT_MAJOR) == 64u || sq_scale_snap(66u, 0u, SQ_SC_PENT_MAJOR) == 67u);
    CHECK(sq_scale_snap(66u, 0u, SQ_SC_PENT_MAJOR) == 67u);          /* F#4 -> E4 (2 away) or G4 (1 away): G */
    CHECK(sq_scale_snap(200u, 0u, SQ_SC_MAJOR) == 200u);             /* not a note: left alone */
    CHECK(sq_scale_snap(61u, 5u, SQ_SC_CHROMATIC) == 61u);           /* chromatic: off */
    CHECK(sq_scale_snap(0u, 1u, SQ_SC_PENT_MINOR) <= 2u && sq_scale_snap(127u, 3u, SQ_SC_PENT_MAJOR) >= 125u);
    CHECK(sq_scale_apply(60, 0u, SQ_SC_MAJOR, 1) == 60u && sq_scale_apply(60, 0u, SQ_SC_MAJOR, 2) == 62u);
    CHECK(sq_scale_apply(127, 0u, SQ_SC_MAJOR, 24) == 127u && sq_scale_apply(-5, 0u, SQ_SC_MAJOR, 0) == 0u);
    CHECK(sq_scale_apply(60, 0u, SQ_SC_CHROMATIC, 7) == 67u);        /* with no scale the shift is a plain transposition */
    CHECK(!strcmp(sq_root_name(0u), "C") && !strcmp(sq_root_name(1u), "C#") && !strcmp(sq_root_name(11u), "B") && !strcmp(sq_root_name(14u), "D"));
    (void)buf;

    sq_project_init(&p);
    CHECK(p.key_root == 0u && p.key_scale == SQ_SC_CHROMATIC && p.key_shift == 0 && p.track[3].flags == 0u);
    p.track[0].flags = SQ_TF_SCALE;
    p.key_scale = SQ_SC_MAJOR; p.key_shift = 1;
    p.step[0][2][4].note[0] = 60u; p.step[0][2][4].note[1] = 61u; p.step[0][2][4].note[2] = SQ_NOTE_NONE;
    p.step[0][0][0].note[0] = 61u; p.step[0][0][0].note[1] = 62u;                    /* 62, 63 once shifted: 62, 62 */
    p.step[1][2][4].note[0] = 61u;                                                  /* a track that does not follow the key */
    n = sq_project_bake_scale(&p);
    CHECK(p.step[0][2][4].note[0] == 60u && p.step[0][2][4].note[1] == 62u);         /* 61 -> 60, 62 -> 62 */
    CHECK(p.step[0][0][0].note[0] == 62u && p.step[0][0][0].note[1] == SQ_NOTE_NONE);/* two notes became one */
    CHECK(p.step[1][2][4].note[0] == 61u);
    CHECK(p.key_shift == 0 && n > 0u);
    CHECK(sq_project_bake_scale(&p) == 0u);                                         /* baked: nothing left to change */
}

static sq_project_t proj_a, proj_b;
static uint8_t image[140000];

static void fill_demo(sq_project_t *p)
{
    uint32_t t, pat, i, rng = 77u;
    sq_project_init(p);
    p->bpm = 141u; p->clock_mode = SQ_CLOCK_SLAVE;
    p->track[2].channel = 9u; p->track[2].length = 24u; p->track[2].start = 5u; p->track[2].division = SQ_DIV_1_8T;
    p->track[2].direction = SQ_DIR_PINGPONG; p->track[2].transpose = -7; p->track[2].chord_mode = SQ_CHORD_PACK(SQ_CHORD_ARP_THUMB, 2u);
    p->track[2].swing = 62u; p->track[2].vel_offset = -12; p->track[2].hum_time = 7u; p->track[2].hum_vel = 9u;
    p->track[2].lane_cc[1] = 91u; p->track[2].lane_base[1] = 20u;
    p->track[15].channel = 13u;
    p->key_root = 7u; p->key_scale = SQ_SC_DORIAN; p->key_shift = -5; p->track[2].flags = SQ_TF_SCALE;
    p->scene[3].mute_mask = 0xA5C3u; p->scene[3].pattern[15] = 6u;
    p->lfo[5].enabled = 1u; p->lfo[5].shape = SQ_LFO_SMOOTH; p->lfo[5].rate = 3u; p->lfo[5].param = 74u; p->lfo[5].flags = SQ_LF_RETRIG;
    p->lfo[15].dest = SQ_LD_TIMING; p->lfo[15].target = 12u;
    p->track[4].flags = SQ_TF_DRUM;
    p->gen.genre = 12u; p->gen.scope = SQ_SCOPE_DRUM; p->gen.targets = SQ_GT_RHYTHM | SQ_GT_CC; p->gen.heat = 77u;
    p->gen.evo_every = 3u; p->gen.evo_drift = 1u; p->gen.harm_on = 1u; p->gen.harm_prog = 4u; p->gen.harm_bars = 2u;
    p->gen.custom = 0x0F0Fu;
    p->id = 0x1234ABCDu;
    p->track[5].mfx = SQ_MFX_ECHO; p->track[5].mfx_amt = 3; p->track[5].mfx_time = 2u; p->track[5].mfx_fb = 45u;
    sq_mfx_from_track(&p->track[5], &p->ext.mfxc[5]);   /* 0.19: the track's effect is its chain's first */
    p->track[5].flags = SQ_TF_SCALE | SQ_TF_FOLLOW | SQ_TF_EUC; p->track[5].euc_pulses = 5u; p->track[5].euc_rot = 3u;
    p->track[5].algo = SQ_ALGO_CELL; p->track[5].algo_a = 110u; p->track[5].algo_b = 24u; p->track[5].algo_c = 2u; p->track[5].pen = 48u;
    p->live.snap_tempo = 1u;
    p->snap[1].used = 1u; p->snap[1].bpm = 99u; p->snap[1].pattern[3] = 5u; p->snap[1].mute = 0x00F0u; p->snap[1].mac[3] = -20;
    for (t = 0; t < SQ_TRACKS; t++) p->snap[1].track[t] = p->track[t];
    p->snap[1].track[7].swing = 66u; p->snap[1].track[9].channel = 11u;
    memcpy(p->snap[1].lfo, p->lfo, sizeof p->lfo);
    p->snap[1].ccn = 3u; p->snap[1].cc[0].ch = 2u; p->snap[1].cc[0].cc = 74u; p->snap[1].cc[0].val = 33u;
    p->snap[1].cc[1].ch = 2u; p->snap[1].cc[1].cc = 71u; p->snap[1].cc[1].val = 100u; p->snap[1].cc[2].ch = 9u; p->snap[1].cc[2].cc = 1u; p->snap[1].cc[2].val = 7u;
    p->snap[6].used = 1u; p->snap[6].bpm = 140u;
    for (t = 0; t < SQ_TRACKS; t++) p->snap[6].track[t] = p->track[t];
    memcpy(p->snap[6].lfo, p->lfo, sizeof p->lfo);
    p->snap[6].lfo[2].enabled = 1u;
    p->song.len = 3u; p->song.loop = 0u; p->song.e[0].scene = 2u; p->song.e[0].bars = 8u; p->song.e[2].scene = 7u; p->song.e[2].bars = 64u;
    for (t = 0; t < SQ_TRACKS; t += 3u)
        for (pat = 0; pat < 3u; pat++)
            for (i = 0; i < 40u; i += 3u) {
                sq_step_t *s = &p->step[t][pat][i];
                s->flags = SQ_STEP_ON | SQ_STEP_SET;
                s->note[0] = (uint8_t)(30u + sq_rng_next(&rng) % 60u); s->note[1] = (uint8_t)(30u + sq_rng_next(&rng) % 60u);
                s->velocity = (uint8_t)(1u + sq_rng_next(&rng) % 127u); s->ratchet = (uint8_t)(1u + sq_rng_next(&rng) % 8u);
                s->nudge = (int8_t)((int32_t)(sq_rng_next(&rng) % 101u) - 50); s->ramp = (int8_t)((int32_t)(sq_rng_next(&rng) % 201u) - 100);
                s->lane[i % 4u] = (uint8_t)(sq_rng_next(&rng) % 128u); s->condition = (uint8_t)(sq_rng_next(&rng) % SQ_COND_COUNT);
            }
    sq_project_sanitize(p);                                   /* (0.10: the canonical form: the key slot that plays holds the key) */
}

static void test_serialize(void)
{
    uint32_t n, n2, i;
    fill_demo(&proj_a);
    n = sq_serialize(&proj_a, image, sizeof image);
    CHECK(n > 0u && n < 32768u);                                  /* a rich project still fits an 32 KiB slot */
    memset(&proj_b, 0x77, sizeof proj_b);
    CHECK(sq_deserialize(&proj_b, image, n) == 0);
    CHECK(!memcmp(&proj_a, &proj_b, sizeof proj_a));              /* a perfect round trip */
    n2 = sq_serialize(&proj_b, image + 70000, sizeof image - 70000);
    CHECK(n2 == n && !memcmp(image, image + 70000, n));          /* and the image is stable */

    /* an empty project is tiny */
    sq_project_init(&proj_a);
    n2 = sq_serialize(&proj_a, image, sizeof image);
    CHECK(n2 > 0u && n2 < 5000u);                                 /* (0.10: 16 keys, 6 lanes, 80-byte tracks, 4.1 KB; 0.11: 96-byte tracks, 4.6 KB) */
    CHECK(sq_deserialize(&proj_b, image, n2) == 0 && !memcmp(&proj_a, &proj_b, sizeof proj_a));

    /* too small a buffer: refused, never written past */
    fill_demo(&proj_a);
    n = sq_serialize(&proj_a, image, sizeof image);
    {
        static uint8_t small[1024 + 16];
        memset(small, 0xA5, sizeof small);
        CHECK(n > 1024u && sq_serialize(&proj_a, small, 1024u) == 0u);
        for (i = 1024u; i < sizeof small; i++) CHECK(small[i] == 0xA5u);
    }
    CHECK(sq_serialize(&proj_a, image, n) == n);                  /* exactly enough */
    CHECK(sq_serialize(&proj_a, image, n - 1u) == 0u);

    /* damaged images: refused or, if accepted, in range */
    sq_serialize(&proj_a, image, sizeof image);
    CHECK(sq_deserialize(&proj_b, image, 3u) != 0);
    CHECK(sq_deserialize(&proj_b, image, 0u) != 0);
    CHECK(sq_deserialize(&proj_b, image, n - 1u) != 0);          /* truncated */
    CHECK(sq_image_ok(image, n) == 0 && sq_image_ok(image, n - 1u) != 0 && sq_image_ok(image, 3u) != 0);
    for (i = 0; i < n; i += 97u) {
        uint8_t keep = image[i];
        image[i] = (uint8_t)~image[i];
        CHECK((sq_image_ok(image, n) == 0) == (sq_deserialize(&proj_b, image, n) == 0));   /* the check agrees with the reader */
        if (sq_deserialize(&proj_b, image, n) == 0) {
            uint32_t t;
            for (t = 0; t < SQ_TRACKS; t++) CHECK(proj_b.track[t].length >= 1u && proj_b.track[t].length <= 64u && proj_b.track[t].start < proj_b.track[t].length);
            CHECK(proj_b.bpm >= 30u && proj_b.bpm <= 300u);
        }
        image[i] = keep;
    }
    {   /* random garbage with a good magic */
        uint32_t rng = 5u, k;
        for (k = 0; k < 300u; k++) {
            uint32_t len = 8u + sq_rng_next(&rng) % 4000u, j;
            for (j = 0; j < len; j++) image[j] = (uint8_t)sq_rng_next(&rng);
            image[0] = 'S'; image[1] = 'G'; image[2] = 'Q'; image[3] = (uint8_t)((k % 5u) ? '8' : '7');
            CHECK((sq_image_ok(image, len) == 0) == (sq_deserialize(&proj_b, image, len) == 0));
            if (sq_deserialize(&proj_b, image, len) == 0) {
                uint32_t t;
                CHECK(proj_b.bpm >= 30u && proj_b.bpm <= 300u);
                for (t = 0; t < SQ_TRACKS; t++) CHECK(proj_b.track[t].channel < SQ_CHANNELS);
                for (t = 0; t < SQ_SNAPS; t++) CHECK(proj_b.snap[t].ccn <= SQ_SNAP_CC);
            }
        }
    }
    CHECK(sq_crc32((const uint8_t *)"123456789", 9u) == 0xCBF43926u);

    {   /* how many hits a slot holds now: 16 tracks x 8 patterns of 16 steps, every step a hit with its own note */
        uint32_t t, pat;
        sq_project_init(&proj_a);
        for (t = 0; t < SQ_TRACKS; t++) for (pat = 0; pat < SQ_PATTERNS; pat++) for (i = 0; i < 16u; i++) {
            sq_step_t *s = &proj_a.step[t][pat][i];
            s->flags = SQ_STEP_ON | SQ_STEP_SET; s->note[0] = (uint8_t)(36u + i); s->velocity = (uint8_t)(60u + i);
        }
        n = sq_serialize(&proj_a, image, sizeof image);
        CHECK(n > 0u && n < 32512u);                                         /* 2048 hits: they fit (0.3 needed ~34 KB) */
    }
    {   /* a drum never follows the key; settings out of range come back in */
        sq_project_init(&proj_a);
        proj_a.track[1].flags = SQ_TF_DRUM | SQ_TF_SCALE | 0x80u;
        proj_a.gen.scope = 9u; proj_a.gen.targets = 0xF0u; proj_a.gen.heat = 0u; proj_a.gen.evo_every = 7u;
        proj_a.song.len = 70u; proj_a.song.e[3].bars = 0u; proj_a.song.e[4].scene = 19u;
        sq_project_sanitize(&proj_a);
        CHECK(proj_a.track[1].flags == SQ_TF_DRUM);
        CHECK(proj_a.gen.scope == SQ_SCOPE_THIS && proj_a.gen.targets == SQ_GT_RHYTHM && proj_a.gen.heat == 1u && proj_a.gen.evo_every == 2u);
        CHECK(proj_a.song.len == 0u && proj_a.song.e[3].bars == 1u && proj_a.song.e[4].scene == 0u);
    }
}

static int in_key(uint8_t n, uint8_t root, uint8_t scale) { return (sq_scale_mask(scale) >> ((n + 120u - root) % 12u)) & 1u; }

static void test_generators(void)
{
    static sq_step_t row[SQ_STEPS], keep[SQ_STEPS];
    uint32_t rng = 99u, i, k, moved = 0, chords_ok = 1, lanes = 0;
    uint8_t base[SQ_LANES] = {40u, SQ_LANE_NONE, 100u, SQ_LANE_NONE};

    /* scale steps and the n-th note */
    CHECK(sq_scale_degree(60, 0u, SQ_SC_MAJOR, 1) == 62u && sq_scale_degree(60, 0u, SQ_SC_MAJOR, 2) == 64u);
    CHECK(sq_scale_degree(60, 0u, SQ_SC_MAJOR, -1) == 59u && sq_scale_degree(64, 0u, SQ_SC_MAJOR, -2) == 60u);
    CHECK(sq_scale_degree(61, 0u, SQ_SC_MAJOR, 0) == 60u);                     /* snapped first (a tie goes down) */
    CHECK(sq_scale_degree(60, 0u, SQ_SC_CHROMATIC, 3) == 63u);                 /* no key: semitones */
    CHECK(sq_scale_degree(126, 0u, SQ_SC_MAJOR, 5) <= 127u && sq_scale_degree(1, 0u, SQ_SC_MAJOR, -5) <= 127u);
    CHECK(sq_scale_nth(60u, 0u, SQ_SC_MINOR, 0) == 60u && sq_scale_nth(60u, 0u, SQ_SC_MINOR, 2) == 63u);
    CHECK(sq_scale_nth(60u, 0u, SQ_SC_MINOR, 7) == 72u && sq_scale_nth(60u, 0u, SQ_SC_MINOR, -1) == 58u);
    CHECK(sq_scale_nth(62u, 9u, SQ_SC_MINOR, 0) == 57u);                       /* A: the root at or under D4 is A3 */
    CHECK(sq_scale_nth(60u, 0u, SQ_SC_PENT_MINOR, 5) == 72u);

    /* notes move in the key, chords together; nothing outside the length, rests untouched */
    for (k = 0; k < 200u; k++) {
        sq_row_clear(row);
        for (i = 0; i < 16u; i += 2u) { row[i].flags = SQ_STEP_ON | SQ_STEP_SET; row[i].note[0] = 57u; row[i].note[1] = 60u; row[i].note[2] = 64u; }
        row[1].note[0] = 61u;                                                  /* (a rest) */
        memcpy(keep, row, sizeof row);
        sq_row_cook_notes(row, 16u, 90u, 9u, SQ_SC_MINOR, &rng);
        for (i = 0; i < 16u; i += 2u) {
            uint32_t n;
            if (row[i].note[0] != 57u) moved++;
            for (n = 0; n < 3u; n++) if (row[i].note[n] != SQ_NOTE_NONE && !in_key(row[i].note[n], 9u, SQ_SC_MINOR)) chords_ok = 0;
        }
        CHECK(row[1].note[0] == 61u);
        for (i = 16u; i < SQ_STEPS; i++) CHECK(!memcmp(&row[i], &keep[i], sizeof row[i]));
    }
    CHECK(moved > 200u && chords_ok);
    sq_row_clear(row); row[0].flags = SQ_STEP_ON | SQ_STEP_SET; row[0].note[0] = 60u; memcpy(keep, row, sizeof row);
    sq_row_cook_notes(row, 16u, 0u, 0u, SQ_SC_MAJOR, &rng);
    CHECK(!memcmp(row, keep, sizeof row));                                    /* no heat, no change */

    /* CC lanes: only the lanes asked, in range, around the base */
    for (k = 0; k < 100u; k++) {
        sq_row_clear(row);
        for (i = 0; i < 16u; i++) row[i].flags = SQ_STEP_ON | SQ_STEP_SET;
        sq_row_cook_lanes(row, 16u, 80u, 0x05u, base, &rng);
        for (i = 0; i < 16u; i++) {
            CHECK(row[i].lane[1] == SQ_LANE_NONE && row[i].lane[3] == SQ_LANE_NONE);
            CHECK(row[i].lane[0] == SQ_LANE_NONE || row[i].lane[0] <= 127u);
            if (row[i].lane[0] != SQ_LANE_NONE) { lanes++; CHECK(row[i].lane[0] <= 40u + 52u); }
            if (row[i].lane[2] != SQ_LANE_NONE) CHECK(row[i].lane[2] >= 100u - 52u);
        }
    }
    CHECK(lanes > 100u);
    sq_row_clear(row); for (i = 0; i < 16u; i++) row[i].flags = SQ_STEP_ON;
    sq_row_random_lanes(row, 16u, 100u, 0x02u, &rng);
    for (i = 0; i < 16u; i++) CHECK(row[i].lane[1] <= 127u && row[i].lane[0] == SQ_LANE_NONE);
    sq_row_random_lanes(row, 16u, 0u, 0x02u, &rng);
    for (i = 0; i < 16u; i++) CHECK(row[i].lane[1] == SQ_LANE_NONE);

    /* random notes: in the key, near the pen note, one note a step */
    sq_row_clear(row); for (i = 0; i < 32u; i++) row[i].flags = SQ_STEP_ON;
    sq_row_random_notes(row, 32u, 48u, 2u, SQ_SC_DORIAN, &rng);
    for (i = 0; i < 32u; i++) CHECK(in_key(row[i].note[0], 2u, SQ_SC_DORIAN) && row[i].note[0] >= 41u && row[i].note[0] <= 55u && row[i].note[1] == SQ_NOTE_NONE && (row[i].flags & SQ_STEP_SET));
    sq_row_random_notes(row, 32u, 48u, 0u, SQ_SC_CHROMATIC, &rng);         /* no key: the minor pentatonic */
    for (i = 0; i < 32u; i++) CHECK(in_key(row[i].note[0], 0u, SQ_SC_PENT_MINOR));

    /* 0.8 progressions: each genre its own, chords as steps of the key and colours */
    {
        uint8_t gg, p, j, out[SQ_POLY], m;
        char nm[64];
        for (gg = 0; gg < SQ_GENRES; gg++)
            for (p = 0; p < SQ_PROGS; p++) {
                const sq_prog_t *pg = sq_prog_get(gg, p);
                CHECK(pg->n >= 1u && pg->n <= 8u && (pg->bars == 1u || pg->bars == 2u || pg->bars == 4u || pg->bars == 8u));
                for (j = 0; j < pg->n; j++) CHECK(pg->deg[j] >= 0 && pg->deg[j] < 7 && pg->col[j] < SQ_HCS);
                sq_prog_name(gg, p, SQ_SC_MINOR, nm, sizeof nm);
                CHECK(nm[0] && strlen(nm) < sizeof nm);
            }
        sq_prog_name(SQ_GENRE_TECHNO, 3u, SQ_SC_MINOR, nm, sizeof nm);    /* i VII VI VII in a minor key */
        CHECK(!strcmp(nm, "i-VII-VI-VII"));
        sq_prog_name(SQ_GENRE_TECHNO, 3u, SQ_SC_MAJOR, nm, sizeof nm);    /* the same steps in a major key */
        CHECK(!strcmp(nm, "I-viio-vi-viio"));
        sq_prog_name(SQ_GENRE_DUBTECHNO, 1u, SQ_SC_MINOR, nm, sizeof nm);
        CHECK(!strcmp(nm, "i7-iv9"));
        {
            int8_t d; uint8_t col;
            CHECK(sq_prog_at(SQ_GENRE_TECHNO, 3u, 0u, 0u, &d, &col) == 0u && d == 0);
            CHECK(sq_prog_at(SQ_GENRE_TECHNO, 3u, 1u, 0u, &d, &col) == 1u && d == 6);
            CHECK(sq_prog_at(SQ_GENRE_TECHNO, 3u, 5u, 0u, &d, &col) == 1u);            /* bar 6: round again */
            CHECK(sq_prog_at(SQ_GENRE_TECHNO, 3u, 5u, 2u, &d, &col) == 2u && d == 5);  /* two bars a chord */
            CHECK(sq_prog_at(SQ_GENRE_TECHNO, 1u, 3u, 0u, &d, &col) == 1u && d == 5);  /* "1 6" two bars each */
        }
        m = sq_tonic_chord(0u, SQ_SC_MINOR, 60u, 3u, out);                /* C minor around C4: G C Eb */
        CHECK(m == 3u && out[0] == 55u && out[1] == 60u && out[2] == 63u);
        m = sq_tonic_chord(9u, SQ_SC_MAJOR, 60u, 4u, out);                /* A major, 4 notes: the 7th too */
        CHECK(m == 4u);
        for (j = 0; j < m; j++) CHECK(in_key(out[j], 9u, SQ_SC_MAJOR));
        CHECK(sq_beat_chords(row, SQ_GENRE_HOUSE, 0u, 0u, SQ_SC_MINOR, 60u) == 16u);
        for (i = 0; i < 16u; i++) if (row[i].flags & SQ_STEP_ON) {
            for (j = 0; j < SQ_POLY && row[i].note[j] != SQ_NOTE_NONE; j++) CHECK(in_key(row[i].note[j], 0u, SQ_SC_MINOR));
            CHECK(j == 4u);                                                    /* house: 7th chords */
        }
    }
    /* roles */
    CHECK(sq_beat_role(1u, 36u) == SQ_FUNC_KICK && sq_beat_role(1u, 39u) == SQ_FUNC_SNARE && sq_beat_role(1u, 46u) == SQ_FUNC_HAT && sq_beat_role(1u, 56u) == SQ_FUNC_PERC);
    CHECK(sq_beat_role(0u, 36u) == SQ_FUNC_BASS && sq_beat_role(0u, 55u) == SQ_FUNC_PROG && sq_beat_role(0u, 60u) == SQ_FUNC_ARP);
}


/* 0.11: which variation of a part has this pattern (255: none) */
static uint8_t var_of(uint8_t g, uint8_t f, const char *text)
{
    uint8_t v, nv = sq_beat_variants(g, f);
    for (v = 0; v < nv; v++) if (!strcmp(sq_beat_text(g, f, v, 0), text)) return v;
    return 255u;
}

static void test_beats(void)
{
    static sq_step_t row[SQ_STEPS];
    uint32_t g, f, v, i;
    CHECK(SQ_GENRES == 25u && SQ_FUNCS == 26u && SQ_GENRE_HARDCORE == 21 && SQ_GENRE_BAILEFUNK == 23 && SQ_GENRE_MERENGUE == 24 && SQ_BEAT_VARS == 12u);
    CHECK(!strcmp(sq_genre_name(SQ_GENRE_TECHNO), "TECHNO") && !strcmp(sq_genre_name(SQ_GENRE_GQOM), "GQOM"));
    CHECK(!strcmp(sq_genre_name(SQ_GENRE_UKG), "UK GARAGE") && !strcmp(sq_genre_name(SQ_GENRE_REGGAETON), "REGGAETON"));
    {   /* 0.10: the 24 genres by name (breakbeat, trap, minimal and lo-fi left; UK drill, hardcore, phonk, baile funk came);
         * 0.16: the merengue, the 25th */
        static const char *const NAMES[SQ_GENRES] = {"TECHNO", "HARDTECHNO", "DUB TECHNO", "HOUSE", "UK GARAGE", "UK FUNKY",
            "GRIME", "DUBSTEP", "JUNGLE", "BASSLINE", "REGGAETON", "BATIDA", "GQOM", "EXPERIMENT", "ELECTRO", "DRUM+BASS",
            "AFRO HOUSE", "AMAPIANO", "FOOTWORK", "TRANCE", "UK DRILL", "HARDCORE", "PHONK", "BAILE FUNK", "MERENGUE"};
        for (g = 0; g < SQ_GENRES; g++) CHECK(!strcmp(sq_genre_name((uint8_t)g), NAMES[g]) && strlen(NAMES[g]) <= 10u);
        CHECK(!strcmp(sq_genre_name(SQ_GENRE_UKDRILL), "UK DRILL") && !strcmp(sq_genre_name(SQ_GENRE_DNB), "DRUM+BASS"));
    }
    CHECK(!strcmp(sq_func_name(SQ_FUNC_KICK), "KICK") && !strcmp(sq_func_name(SQ_FUNC_PROG), "PROG") && !strcmp(sq_func_name(SQ_FUNC_KIT), "KIT"));
    {   /* 0.16: the merengue: four on the floor, the guira's "cha chi-ki", major keys, I - V7, its band */
        const char *notes = 0;
        uint16_t lo, hi;
        char nm[40];
        uint8_t parts[SQ_PARTS_MAX], n = sq_genre_parts(SQ_GENRE_MERENGUE, parts);
        sq_genre_bpm(SQ_GENRE_MERENGUE, &lo, &hi);
        sq_prog_name(SQ_GENRE_MERENGUE, 0u, SQ_SC_MAJOR, nm, sizeof nm);
        CHECK(!strcmp(sq_beat_text(SQ_GENRE_MERENGUE, SQ_FUNC_KICK, 0u, &notes), "X...X...X...X..."));
        CHECK(!strcmp(sq_beat_text(SQ_GENRE_MERENGUE, SQ_FUNC_HAT, 0u, &notes), "x.xxx.xxx.xxx.xx"));
        CHECK(lo == 128u && hi == 156u && sq_genre_scale(SQ_GENRE_MERENGUE, 0u) == SQ_SC_MAJOR && sq_genre_swing(SQ_GENRE_MERENGUE) == 50u);
        CHECK(!strcmp(nm, "I-V7") && sq_genre_band(SQ_GENRE_MERENGUE) == 9u && n >= 9u && parts[3] == SQ_FUNC_PERC && parts[4] == SQ_FUNC_CONGA);
        CHECK(sq_brk_genre_chops(SQ_GENRE_MERENGUE) == 4u && sq_beat_variants(SQ_GENRE_MERENGUE, SQ_FUNC_KICK) == 12u);
    }
    {   /* 0.16: the genres' GROOVE, as the doc says */
        uint8_t sw, gv, ga;
        sq_genre_groove(SQ_GENRE_UKG, SQ_FUNC_HAT, &sw, &gv, &ga);
        CHECK(sw == 50u && gv == SQ_GROOVE_GARAGE && ga == 100u);                 /* the drums straight under GARAGE */
        sq_genre_groove(SQ_GENRE_UKG, SQ_FUNC_BASS, &sw, &gv, &ga);
        CHECK(sw == 63u && gv == SQ_GROOVE_OFF && ga == 0u);                      /* the bass: the swing that meets it */
        sq_genre_groove(SQ_GENRE_HOUSE, SQ_FUNC_KICK, &sw, &gv, &ga);
        CHECK(sw == 54u && gv == SQ_GROOVE_OFF);                                  /* the kick: the anchor */
        sq_genre_groove(SQ_GENRE_HOUSE, SQ_FUNC_SHAKER, &sw, &gv, &ga);
        CHECK(sw == 54u && gv == SQ_GROOVE_HOUSE && ga == 100u);
        sq_genre_groove(SQ_GENRE_AMAPIANO, SQ_FUNC_RIM, &sw, &gv, &ga);
        CHECK(sw == 58u && gv == SQ_GROOVE_AFRO && ga == 80u);                    /* a rim carries the groove (the percussion's) */
        sq_genre_groove(SQ_GENRE_AMAPIANO, SQ_FUNC_LOGDRUM, &sw, &gv, &ga);
        CHECK(sw == 58u && gv == SQ_GROOVE_OFF);
        sq_genre_groove(SQ_GENRE_BAILEFUNK, SQ_FUNC_PERC, &sw, &gv, &ga);
        CHECK(sw == 50u && gv == SQ_GROOVE_SAMBA && ga == 100u);
        sq_genre_groove(SQ_GENRE_UKDRILL, SQ_FUNC_HAT, &sw, &gv, &ga);
        CHECK(sw == 54u && gv == SQ_GROOVE_TRAP && ga == 100u);
        sq_genre_groove(SQ_GENRE_TRANCE, SQ_FUNC_HAT, &sw, &gv, &ga);
        CHECK(gv == SQ_GROOVE_OFF);
        sq_genre_groove(SQ_GENRE_DUBSTEP, SQ_FUNC_SNARE, &sw, &gv, &ga);
        CHECK(sw == 52u && gv == SQ_GROOVE_OFF);                                  /* the half-time snare on the grid */
    }
    CHECK(!strcmp(sq_genre_name(200u), "TECHNO") && !strcmp(sq_func_name(200u), "KICK"));       /* out of range: no crash */
    for (g = 0; g < SQ_GENRES; g++) {
        uint16_t lo, hi;
        CHECK(sq_genre_swing((uint8_t)g) >= 50u && sq_genre_swing((uint8_t)g) <= 66u);
        {   /* 0.16: every part's feel: a swing in range, a template, an amount; OFF has no amount */
            uint8_t f, sw, gv, ga;
            for (f = 0; f < SQ_FUNCS; f++) {
                sq_genre_groove((uint8_t)g, f, &sw, &gv, &ga);
                CHECK(sw >= SQ_SWING_MIN && sw <= 66u && gv < SQ_GROOVES && ga <= 100u && (gv ? ga >= 20u : ga == 0u));
            }
            sq_genre_groove((uint8_t)g, 200u, &sw, &gv, &ga);
            CHECK(sw == sq_genre_swing((uint8_t)g) && gv == SQ_GROOVE_OFF && ga == 0u);
        }
        sq_genre_bpm((uint8_t)g, &lo, &hi); CHECK(lo >= 30u && lo <= hi && hi <= 300u);
        CHECK(sq_genre_scale((uint8_t)g, 0u) > 0u && sq_genre_scale((uint8_t)g, 2u) < SQ_SCALES);
        CHECK(sq_genre_chord_size((uint8_t)g) == 3u || sq_genre_chord_size((uint8_t)g) == 4u);
        {   /* 0.11: the genre's parts: a band of 8 to 11 (its first part the KICK), the parts kept after it */
            uint8_t parts[SQ_PARTS_MAX], np = sq_genre_parts((uint8_t)g, parts), nb = sq_genre_band((uint8_t)g), k2, mains = 0u;
            CHECK(nb >= 8u && nb <= SQ_BAND_MAX && np >= nb && np <= SQ_PARTS_MAX && parts[0] == SQ_FUNC_KICK);
            for (k2 = 0; k2 < np; k2++) {
                uint8_t j2, nvk = sq_beat_variants((uint8_t)g, parts[k2]);
                CHECK(parts[k2] < SQ_FUNCS && parts[k2] != SQ_FUNC_PROG && parts[k2] != SQ_FUNC_KIT && sq_genre_has((uint8_t)g, parts[k2]));
                for (j2 = 0; j2 < k2; j2++) CHECK(parts[j2] != parts[k2]);                  /* each part once */
                CHECK(nvk == (sq_part_main((uint8_t)g, parts[k2]) ? 12u : 6u));             /* a main part 12, the others 6 */
                if (sq_part_main((uint8_t)g, parts[k2])) mains++;
                CHECK(sq_role_func(sq_func_role(parts[k2])) == parts[k2] && sq_genre_part_for((uint8_t)g, parts[k2]) == parts[k2]);
                if (sq_func_kind(parts[k2]) == SQ_KIND_DRUM && k2 < nb)
                    for (j2 = 0; j2 < k2; j2++) if (sq_func_kind(parts[j2]) == SQ_KIND_DRUM) CHECK(sq_part_note((uint8_t)g, parts[j2]) != sq_part_note((uint8_t)g, parts[k2]));   /* two drums, two notes */
            }
            CHECK(mains >= 5u);
            CHECK(sq_beat_variants((uint8_t)g, SQ_FUNC_KIT) == sq_beat_variants((uint8_t)g, SQ_FUNC_KICK) && sq_beat_variants((uint8_t)g, SQ_FUNC_PROG) >= 6u);
        }
        for (f = 0; f < SQ_FUNCS; f++) {
            uint8_t nv = sq_beat_variants((uint8_t)g, (uint8_t)f);
            if (f == SQ_FUNC_KIT || f == SQ_FUNC_PROG) {
                uint8_t part, fn, note;
                CHECK(sq_beat_load(row, (uint8_t)g, (uint8_t)f, 0u, 36u) == 0u);              /* made elsewhere */
                for (part = 0; part < 4u; part++) {
                    sq_beat_kit_part((uint8_t)g, part, &fn, &note);
                    CHECK(fn == part && note >= 35u && note <= 81u);
                }
                continue;
            }
            CHECK((nv != 0u) == sq_genre_has((uint8_t)g, (uint8_t)f));
            for (v = 0; v < SQ_BEAT_VARS + 1u; v++) {
                const char *nt, *r = sq_beat_text((uint8_t)g, (uint8_t)f, (uint8_t)v, &nt);
                uint32_t hits = 0, n;
                uint8_t len, kind = sq_func_kind((uint8_t)f);
                CHECK((r != 0) == (v < nv));
                if (!r) { CHECK(sq_beat_load(row, (uint8_t)g, (uint8_t)f, (uint8_t)v, 60u) == 0u); continue; }
                for (n = 0; r[n]; n++) if (r[n] != '.' && r[n] != '-') hits++;
                CHECK((n == 16u || n == 32u || n == 64u) && hits >= 1u && hits <= n && r[0] != '-');
                if (f == SQ_FUNC_KICK) CHECK(r[0] == 'X' || r[0] == 'x');
                if (kind != SQ_KIND_DRUM) { CHECK(nt != 0); { uint32_t k = 0; while (nt[k]) k++; CHECK(k == n); } }
                else CHECK(nt == 0);
                {   uint32_t k;                                                      /* no two variations of a part alike */
                    for (k = 0; k < v; k++) {
                        const char *nt2, *r2 = sq_beat_text((uint8_t)g, (uint8_t)f, (uint8_t)k, &nt2);
                        CHECK(strcmp(r, r2) || (nt && nt2 && strcmp(nt, nt2)));
                    }
                }
                memset(row, 0xEE, sizeof row);
                for (i = 0; i < n; i++) sq_step_default(&row[i]);
                len = sq_beat_load(row, (uint8_t)g, (uint8_t)f, (uint8_t)v, 38u);
                CHECK(len == n);
                {   uint32_t on = 0;
                    for (i = 0; i < n; i++) {
                        const sq_step_t *s = &row[i];
                        uint32_t span = 1u;
                        CHECK(((s->flags & SQ_STEP_ON) != 0) == (r[i] != '.' && r[i] != '-'));
                        CHECK(s->velocity >= 1u && s->velocity <= 127u && s->ratchet >= 1u && s->ratchet <= 4u && s->length >= 10u && s->length <= SQ_GATE_LONG_MAX);
                        if (s->flags & SQ_STEP_ON) {
                            uint32_t k; on++;
                            while (i + span < n && r[i + span] == '-') span++;            /* 0.11: a held note lasts its steps */
                            CHECK(span == 1u || s->ratchet > 1u ? s->length <= 101u || span > 1u : sq_gate_span(s->length) == span);
                            if (span > 1u && s->ratchet <= 1u) CHECK(sq_gate_span(s->length) == span);
                            CHECK(s->flags & SQ_STEP_SET);
                            CHECK(s->note[0] <= 127u);
                            for (k = 1; k < SQ_POLY; k++) CHECK(s->note[k] == SQ_NOTE_NONE || s->note[k] <= 127u);
                            if (kind == SQ_KIND_DRUM) CHECK(s->note[0] == 38u && s->note[1] == SQ_NOTE_NONE);
                            else if (sq_func_family((uint8_t)f) == SQ_FUNC_BASS) CHECK(s->note[0] >= 24u && s->note[0] < 48u + 16u);
                            else CHECK(s->note[0] >= 48u && s->note[0] < 84u + 16u);
                            if (kind == SQ_KIND_CHORD) CHECK(s->note[1] != SQ_NOTE_NONE && s->note[2] != SQ_NOTE_NONE);
                        }
                    }
                    CHECK(on == hits);
                }
                if (n < SQ_STEPS) CHECK(row[n].note[0] == 0xEEu);                 /* nothing written past the pattern */
            }
        }
        /* 0.10: every genre has a two-bar kick and a two-bar hat or perc of its own */
        {   uint32_t long_kick = 0, long_hp = 0;
            for (v = 0; v < SQ_BEAT_VARS; v++) {
                const char *r = sq_beat_text((uint8_t)g, SQ_FUNC_KICK, (uint8_t)v, 0);
                if (r && strlen(r) >= 32u) long_kick++;
                r = sq_beat_text((uint8_t)g, SQ_FUNC_HAT, (uint8_t)v, 0); if (r && strlen(r) >= 32u) long_hp++;
                r = sq_beat_text((uint8_t)g, SQ_FUNC_PERC, (uint8_t)v, 0); if (r && strlen(r) >= 32u) long_hp++;
            }
            CHECK(long_kick >= 1u && long_hp >= 1u);
        }
    }
    /* 0.10: four-bar kicks where the genre lives on four-bar phrases */
    {   static const uint8_t FOUR[7] = {SQ_GENRE_TECHNO, SQ_GENRE_HOUSE, SQ_GENRE_UKG, SQ_GENRE_JUNGLE, SQ_GENRE_DNB, SQ_GENRE_UKDRILL, SQ_GENRE_HARDCORE};
        for (i = 0; i < 7u; i++) {
            uint32_t n64 = 0;
            for (v = 0; v < SQ_BEAT_VARS; v++) { const char *r = sq_beat_text(FOUR[i], SQ_FUNC_KICK, (uint8_t)v, 0); if (r && strlen(r) == 64u) n64++; }
            CHECK(n64 >= 1u);
        }
    }
    /* 0.11: the variations are in order of likeness, so the 0.10 patterns are found by their text (each kept in flash) */
    CHECK(var_of(SQ_GENRE_HARDTECHNO, SQ_FUNC_CLAP, "....x...x...x..2") < 12u);     /* (0.10's HARDTECHNO SNARE) */
    sq_beat_load(row, SQ_GENRE_HARDTECHNO, SQ_FUNC_CLAP, var_of(SQ_GENRE_HARDTECHNO, SQ_FUNC_CLAP, "....x...x...x..2"), 39u);
    CHECK(row[15].ratchet == 2u && row[4].ratchet == 1u);
    sq_beat_load(row, SQ_GENRE_TECHNO, SQ_FUNC_HAT, var_of(SQ_GENRE_TECHNO, SQ_FUNC_HAT, "oxXxoxXxoxXxoxXx"), 42u);
    CHECK(row[0].velocity == 75u && row[2].velocity == 124u && row[1].velocity == 100u);
    sq_beat_load(row, SQ_GENRE_HOUSE, SQ_FUNC_BASS, 0u, 60u);                     /* the default note 60, a bass: C2 */
    CHECK(row[2].note[0] == 36u && row[14].note[0] == 43u);
    CHECK(sq_beat_load(row, 99u, 0u, 0u, 60u) == 0u && sq_beat_load(row, 0u, 99u, 0u, 60u) == 0u && sq_beat_load(row, 0u, 0u, 12u, 60u) == 0u);
    CHECK(sq_beat_variants(99u, 0u) == 0u && sq_beat_variants(0u, 99u) == 0u);
    CHECK(sq_beat_load(row, SQ_GENRE_DUBSTEP, SQ_FUNC_KICK, var_of(SQ_GENRE_DUBSTEP, SQ_FUNC_KICK, "X.......x.......X.........x.x..."), 36u) == 32u);   /* two bars */
    CHECK(sq_beat_load(row, SQ_GENRE_GQOM, SQ_FUNC_KICK, 0u, 36u) == 16u && (row[6].flags & SQ_STEP_ON) && !(row[4].flags & SQ_STEP_ON));   /* broken: 1, 7, 13 */
    /* the first variation of every 0.10 part is 0.10's first: the most typical stays where it was */
    CHECK(!strcmp(sq_beat_text(SQ_GENRE_TECHNO, SQ_FUNC_KICK, 0u, 0), "X...X...X...X...") && !strcmp(sq_beat_text(SQ_GENRE_TECHNO, SQ_FUNC_CLAP, 0u, 0), "....X.......X..."));
    CHECK(!strcmp(sq_beat_text(SQ_GENRE_HOUSE, SQ_FUNC_PIANO, 0u, 0), "..x...x...x...x.") && sq_genre_has(SQ_GENRE_HOUSE, SQ_FUNC_ARP) && !sq_genre_has(SQ_GENRE_HOUSE, SQ_FUNC_SNARE));
    CHECK(sq_genre_part_for(SQ_GENRE_HOUSE, SQ_FUNC_SNARE) == SQ_FUNC_CLAP && sq_genre_part_for(SQ_GENRE_TECHNO, SQ_FUNC_CHORD) == SQ_FUNC_STAB);
    CHECK(sq_genre_part_for(SQ_GENRE_AMAPIANO, SQ_FUNC_LOGDRUM) == SQ_FUNC_LOGDRUM && sq_genre_part_for(SQ_GENRE_TECHNO, SQ_FUNC_LOGDRUM) == SQ_FUNC_BASS);
    CHECK(sq_genre_band(SQ_GENRE_TECHNO) == 10u && sq_genre_band(SQ_GENRE_AFROHOUSE) == 11u && sq_genre_band(SQ_GENRE_TRANCE) == 11u && sq_genre_band(SQ_GENRE_GQOM) == 8u);
    {   uint8_t parts[SQ_PARTS_MAX], n = sq_genre_parts(SQ_GENRE_TECHNO, parts);
        static const uint8_t WANT[11] = {SQ_FUNC_KICK, SQ_FUNC_CLAP, SQ_FUNC_HAT, SQ_FUNC_OHAT, SQ_FUNC_RIDE, SQ_FUNC_PERC, SQ_FUNC_RUMBLE, SQ_FUNC_BASS, SQ_FUNC_STAB, SQ_FUNC_PAD, SQ_FUNC_ARP};
        CHECK(n == 11u && !memcmp(parts, WANT, 11u));                             /* the band of 10, the ARP kept */
        CHECK(sq_part_note(SQ_GENRE_TECHNO, SQ_FUNC_OHAT) == 46u && sq_part_note(SQ_GENRE_TECHNO, SQ_FUNC_PERC) != 46u && sq_part_note(SQ_GENRE_TECHNO, SQ_FUNC_RIDE) == 51u);
        CHECK(sq_func_role(SQ_FUNC_RUMBLE) == SQ_ROLE_RUMBLE && sq_role_family(SQ_ROLE_RUMBLE) == SQ_ROLE_BASS && sq_func_family(SQ_FUNC_RUMBLE) == SQ_FUNC_BASS);
        CHECK(sq_role_func(SQ_ROLE_NONE) == 255u && sq_func_role(SQ_FUNC_PROG) == SQ_ROLE_CHORD && sq_func_kind(SQ_FUNC_PAD) == SQ_KIND_CHORD && sq_func_kind(SQ_FUNC_RIDE) == SQ_KIND_DRUM);
        CHECK(!strcmp(sq_role_name(SQ_ROLE_OHAT), "OPEN HAT") && !strcmp(sq_func_name(SQ_FUNC_LOGDRUM), "LOG DRUM") && !strcmp(sq_role_name(SQ_ROLE_VOX), "VOX"));
    }
    {   /* 0.11 held notes: a PAD "x---..." holds; the PROG rhythm of a genre whose first chord part holds, holds too */
        const char *nt, *r = sq_beat_text(SQ_GENRE_TECHNO, SQ_FUNC_PAD, 0u, &nt);
        uint32_t k = 1u;
        CHECK(r && r[0] == 'x' && r[1] == '-');
        while (r[k] == '-') k++;
        CHECK(sq_beat_load(row, SQ_GENRE_TECHNO, SQ_FUNC_PAD, 0u, 60u) == strlen(r) && sq_gate_span(row[0].length) == k && row[0].note[2] != SQ_NOTE_NONE);
        CHECK(sq_gate_steps(1u) == 100u && sq_gate_steps(2u) == 102u && sq_gate_steps(64u) == 164u && sq_gate_span(164u) == 64u && sq_gate_span(101u) == 1u && sq_gate_span(55u) == 1u);
        CHECK(sq_beat_load_text(row, "x---x-..", "0...7...", SQ_FUNC_SUB, 36u) == 8u && sq_gate_span(row[0].length) == 4u && sq_gate_span(row[4].length) == 2u && row[4].note[0] == 43u);
        CHECK(sq_beat_load_text(row, "x?..", "0...", SQ_FUNC_SUB, 36u) == 0u && sq_beat_load_text(row, "x...", "z...", SQ_FUNC_SUB, 36u) == 0u);   /* (what the Pi sends is checked) */
        CHECK(sq_beat_load_text(row, "x...", 0, SQ_FUNC_PROG, 36u) == 0u && sq_beat_load_text(row, "x...", 0, SQ_FUNC_RIM, 37u) == 4u);
    }

    /* 0.10 sq_beat_load_len: a 64-step load of TECHNO KICK #1 ("X...X...X...X...") is four bars; the first three are the
     * pattern, the fourth is the next variant with the fill: its last 16th rolls */
    {   static sq_step_t one[SQ_STEPS];
        uint32_t same = 0, diff = 0;
        uint8_t v2;
        CHECK(sq_beat_load(one, SQ_GENRE_TECHNO, SQ_FUNC_KICK, 0u, 36u) == 16u);
        memset(row, 0xEE, sizeof row);
        CHECK(sq_beat_load_len(row, SQ_GENRE_TECHNO, SQ_FUNC_KICK, 0u, 36u, 64u) == 64u);
        for (i = 0; i < 48u; i++) CHECK(!memcmp(&row[i], &one[i % 16u], sizeof one[0]));
        for (i = 48u; i < 64u; i++) { if (memcmp(&row[i], &one[i % 16u], sizeof one[0])) diff++; else same++; }
        CHECK(diff >= 1u && same >= 8u);                                           /* the fourth bar differs, but is kin */
        CHECK((row[63].flags & SQ_STEP_ON) && row[63].note[0] == 36u && (row[63].ratchet >= 2u || ((row[62].flags & SQ_STEP_ON) && row[62].ratchet >= 2u) || !(row[62].flags & SQ_STEP_ON)));   /* the fill: a pick-up into the one, a roll where it hit */
        /* 32 steps: one bar of the variant, then the next variant with the fill */
        CHECK(sq_beat_load_len(row, SQ_GENRE_TECHNO, SQ_FUNC_KICK, 0u, 36u, 32u) == 32u);
        for (i = 0; i < 16u; i++) CHECK(!memcmp(&row[i], &one[i], sizeof one[0]));
        CHECK((row[31].flags & SQ_STEP_ON) && (row[31].ratchet >= 2u || (row[30].flags & SQ_STEP_ON) ? row[30].ratchet >= 2u || row[31].ratchet >= 2u : 1));
        /* the last variant wraps round to the first; len 0 is the pattern's own length; an odd len is 16 */
        v2 = (uint8_t)(sq_beat_variants(SQ_GENRE_GQOM, SQ_FUNC_KICK) - 1u);
        CHECK(sq_beat_load_len(row, SQ_GENRE_GQOM, SQ_FUNC_KICK, v2, 36u, 0u) == strlen(sq_beat_text(SQ_GENRE_GQOM, SQ_FUNC_KICK, v2, 0)));
        CHECK(sq_beat_load_len(row, SQ_GENRE_GQOM, SQ_FUNC_KICK, 0u, 36u, 24u) == 16u && (row[6].flags & SQ_STEP_ON));
        v2 = (uint8_t)(sq_beat_variants(SQ_GENRE_GQOM, SQ_FUNC_SNARE) - 1u);
        if (strlen(sq_beat_text(SQ_GENRE_GQOM, SQ_FUNC_SNARE, v2, 0)) == 16u) {
            CHECK(sq_beat_load_len(row, SQ_GENRE_GQOM, SQ_FUNC_SNARE, v2, 38u, 32u) == 32u);
            CHECK(sq_beat_load(one, SQ_GENRE_GQOM, SQ_FUNC_SNARE, 0u, 38u) == 16u);
            for (i = 16u; i < 30u; i++) CHECK(!memcmp(&row[i], &one[i - 16u], sizeof one[0]));   /* bar 2 = variant 1 ... */
            CHECK((row[30].flags & SQ_STEP_ON) && row[30].ratchet == 2u && (row[31].flags & SQ_STEP_ON) && row[31].ratchet == 2u);   /* ... with a snare roll */
        }
        /* a longer pattern than asked: its first bars (DUBSTEP's two-bar kick), nothing written past them */
        v2 = var_of(SQ_GENRE_DUBSTEP, SQ_FUNC_KICK, "X.......x.......X.........x.x...");
        memset(row, 0xEE, sizeof row);
        CHECK(sq_beat_load_len(row, SQ_GENRE_DUBSTEP, SQ_FUNC_KICK, v2, 36u, 16u) == 16u && (row[8].flags & SQ_STEP_ON) && row[16].note[0] == 0xEEu);
        /* a two-bar variant tiled to four: bars A B A, then the next variant's */
        CHECK(sq_beat_load_len(row, SQ_GENRE_DUBSTEP, SQ_FUNC_KICK, v2, 36u, 64u) == 64u);
        CHECK(sq_beat_load(one, SQ_GENRE_DUBSTEP, SQ_FUNC_KICK, v2, 36u) == 32u);
        for (i = 0; i < 32u; i++) CHECK(!memcmp(&row[i], &one[i], sizeof one[0]));
        for (i = 32u; i < 48u; i++) CHECK(!memcmp(&row[i], &one[i - 32u], sizeof one[0]));
        /* the pitched parts: the last bar is the next variant's notes (a turnaround), no fill */
        CHECK(sq_beat_load_len(row, SQ_GENRE_HOUSE, SQ_FUNC_BASS, 0u, 60u, 32u) == 32u);
        if (strlen(sq_beat_text(SQ_GENRE_HOUSE, SQ_FUNC_BASS, 1u, 0)) == 16u) {
            CHECK(sq_beat_load(one, SQ_GENRE_HOUSE, SQ_FUNC_BASS, 1u, 60u) == 16u);
            for (i = 16u; i < 32u; i++) CHECK(!memcmp(&row[i], &one[i - 16u], sizeof one[0]));
        }
        CHECK(row[2].note[0] == 36u && row[16].note[0] >= 24u && row[16].note[0] < 64u);
        CHECK(sq_beat_load_len(row, SQ_GENRE_TECHNO, SQ_FUNC_STAB, 0u, 60u, 64u) == 64u && (row[48 + 3].flags & SQ_STEP_ON) == 0u ? 1 : row[48 + 3].note[2] != SQ_NOTE_NONE);
        CHECK(sq_beat_load_len(row, SQ_GENRE_TECHNO, SQ_FUNC_PROG, 0u, 60u, 32u) == 0u && sq_beat_load_len(row, 99u, 0u, 0u, 36u, 32u) == 0u);
        CHECK(sq_beat_load_len(row, SQ_GENRE_TECHNO, SQ_FUNC_KICK, 12u, 36u, 32u) == 0u && sq_beat_load_len(row, SQ_GENRE_TECHNO, SQ_FUNC_SNARE, 0u, 36u, 32u) == 0u);   /* (TECHNO has a CLAP, no SNARE) */
        /* UK drill rolls in triplets: its fill is a 3 */
        CHECK(sq_beat_load_len(row, SQ_GENRE_UKDRILL, SQ_FUNC_HAT, 0u, 42u, 32u) == 32u && row[31].ratchet == 3u && row[30].ratchet == 3u);
    }
    /* 0.10: UK drill and hardcore load for every part and variant, and sound like themselves */
    {   static const uint8_t NEW[2] = {SQ_GENRE_UKDRILL, SQ_GENRE_HARDCORE};
        uint16_t lo, hi;
        for (i = 0; i < 2u; i++) {
            uint8_t parts[SQ_PARTS_MAX], np = sq_genre_parts(NEW[i], parts), k;
            for (k = 0; k < np; k++) {
                uint8_t nv = sq_beat_variants(NEW[i], parts[k]);
                for (v = 0; v < nv; v++) {
                    uint8_t n = sq_beat_load(row, NEW[i], parts[k], (uint8_t)v, 60u);
                    CHECK(n == 16u || n == 32u || n == 64u);
                    CHECK(sq_beat_load_len(row, NEW[i], parts[k], (uint8_t)v, 60u, 64u) == 64u);
                }
            }
            CHECK(sq_beat_chords(row, NEW[i], 0u, 0u, SQ_SC_MINOR, 60u) >= 16u);
            for (v = 0; v < SQ_PROGS; v++) CHECK(sq_prog_get(NEW[i], (uint8_t)v)->n >= 1u);
        }
        sq_genre_bpm(SQ_GENRE_UKDRILL, &lo, &hi); CHECK(lo == 140u && hi == 145u);
        sq_genre_bpm(SQ_GENRE_HARDCORE, &lo, &hi); CHECK(lo == 160u && hi == 200u);
        CHECK(sq_beat_load(row, SQ_GENRE_UKDRILL, SQ_FUNC_SNARE, 0u, 38u) == 16u && (row[8].flags & SQ_STEP_ON) && (row[14].flags & SQ_STEP_ON) && !(row[4].flags & SQ_STEP_ON) && !(row[12].flags & SQ_STEP_ON));
        v = var_of(SQ_GENRE_UKDRILL, SQ_FUNC_SUB, "X......x..x....x");
        CHECK(v < 12u && sq_beat_load(row, SQ_GENRE_UKDRILL, SQ_FUNC_SUB, (uint8_t)v, 60u) == 16u && row[0].note[0] == 36u && row[7].note[0] == 44u && row[15].note[0] == 37u);   /* the 808 slides to the flat 6th and the flat 2nd */
        CHECK(sq_beat_load(row, SQ_GENRE_HARDCORE, SQ_FUNC_KICK, 0u, 36u) == 16u && (row[0].flags & SQ_STEP_ON) && (row[4].flags & SQ_STEP_ON) && (row[8].flags & SQ_STEP_ON) && (row[12].flags & SQ_STEP_ON));
        CHECK(sq_beat_load(row, SQ_GENRE_HARDCORE, SQ_FUNC_STAB, 0u, 60u) == 16u && row[0].note[1] == row[0].note[0] + 7u && row[0].note[2] == row[0].note[0] + 12u);   /* a power chord */
    }
    /* 0.10: VIAGGIO's set genres, generated with the library: one per genre, in its order (the header itself; the core
     * includes it as its SET_GENRE) */
    {   CHECK(sizeof SET_GENRE / sizeof SET_GENRE[0] == SQ_GENRES);
        for (g = 0; g < SQ_GENRES; g++) {
            const sq_set_genre_t *s = &SET_GENRE[g];
            CHECK(s->genre == g && s->genre2 < SQ_GENRES && s->genre2 != g && !strcmp(s->name, sq_genre_name((uint8_t)g)) && strlen(s->name) <= 10u);
            CHECK(s->swing == sq_genre_swing((uint8_t)g) && s->swing >= 50u && s->swing <= 75u && s->half_time <= 1u && s->afro <= 1u);
            for (i = 0; i < SQ_ROLES; i++) CHECK(s->ladder[i] <= 100u);
            CHECK(s->ladder[0] <= 15u);                                            /* the kick comes first */
        }
        CHECK(SET_GENRE[SQ_GENRE_DUBSTEP].half_time && SET_GENRE[SQ_GENRE_UKDRILL].half_time && !SET_GENRE[SQ_GENRE_JUNGLE].half_time && !SET_GENRE[SQ_GENRE_DNB].half_time);
        CHECK(SET_GENRE[SQ_GENRE_REGGAETON].afro && SET_GENRE[SQ_GENRE_GQOM].afro && SET_GENRE[SQ_GENRE_AMAPIANO].afro && !SET_GENRE[SQ_GENRE_TECHNO].afro);
        CHECK(SET_GENRE[SQ_GENRE_JUNGLE].ladder[1] <= 10u && SET_GENRE[SQ_GENRE_DUBTECHNO].ladder[5] <= 30u);   /* the break's snare early; the dub chord early */
    }
}

/* 0.8: the SGQ8 round trip (snapshots too) and the RELOAD reader. Older images are rejected. */
static void test_serialize_v8(void)
{
    uint32_t n, k, n_nosnap;
    static sq_track_cfg_t cfg;
    static sq_step_t row[SQ_STEPS];
    fill_demo(&proj_a);
    proj_a.track[2].voicing = SQ_VOICE_OPEN;
    proj_a.track[2].strum = -23;
    proj_a.step[2][1][3].flags |= SQ_STEP_LOCK;
    n = sq_serialize(&proj_a, image, sizeof image);
    CHECK(n > 0u && n < 32768u);
    memset(&proj_b, 0xEE, sizeof proj_b);
    CHECK(sq_deserialize(&proj_b, image, n) == 0);
    CHECK(!memcmp(&proj_a, &proj_b, sizeof proj_a));
    CHECK(proj_b.id == 0x1234ABCDu && proj_b.gen.custom == 0x0F0Fu && proj_b.gen.harm_prog == 4u && proj_b.live.snap_tempo == 1u);
    CHECK(proj_b.track[5].mfx == SQ_MFX_ECHO && proj_b.track[5].algo == SQ_ALGO_CELL && proj_b.track[5].algo_a == 110u && proj_b.track[5].pen == 48u);
    CHECK((proj_b.track[5].flags & (SQ_TF_FOLLOW | SQ_TF_EUC)) == (SQ_TF_FOLLOW | SQ_TF_EUC) && proj_b.track[5].euc_pulses == 5u);
    CHECK(proj_b.snap[1].used && proj_b.snap[1].ccn == 3u && proj_b.snap[1].cc[1].val == 100u && proj_b.snap[1].track[7].swing == 66u);
    CHECK(proj_b.snap[6].used && proj_b.snap[6].lfo[2].enabled && !proj_b.snap[0].used);
    CHECK(proj_b.step[2][1][3].flags & SQ_STEP_LOCK);
    {   /* a snapshot whose tracks are the project's costs little: only what differs is written */
        sq_project_t *q = &proj_b;
        memcpy(q, &proj_a, sizeof *q);
        q->snap[1].used = 0u; q->snap[6].used = 0u;
        sq_project_sanitize(q);
        n_nosnap = sq_serialize(q, image + 100000, sizeof image - 100000);
        /* snapshot 2: its head, 2 tracks that differ (7, 9) and track 2 (changed after it was taken), 3 CC values;
         * snapshot 7: its head, track 2, its own LFOs */
        CHECK(n_nosnap > 0u && n - n_nosnap == 2u * (SQ_SNAP_HEAD + 2u + 1u) + 3u * 96u + 9u + 96u + 160u);
    }

    n = sq_serialize(&proj_a, image, sizeof image);
    for (k = 0; k < 24u; k++) {
        uint8_t tt = (uint8_t)((k * 7u) % SQ_TRACKS), pp = (uint8_t)((k * 3u) % SQ_PATTERNS);
        memset(&cfg, 0xEE, sizeof cfg); memset(row, 0xEE, sizeof row);
        CHECK(sq_image_track(image, n, tt, pp, &cfg, row) == 0);
        CHECK(!memcmp(&cfg, &proj_a.track[tt], sizeof cfg));
        CHECK(!memcmp(row, proj_a.step[tt][pp], sizeof row));
    }
    CHECK(sq_image_track(image, n - 1u, 0u, 0u, &cfg, row) != 0);
    CHECK(sq_image_track(image, n, 16u, 0u, &cfg, row) != 0);

    /* older magics are not accepted (0.10 made the format over: SGQ3 .. SGQ9 are refused); 0.11 writes SGQB and reads SGQA */
    for (k = 3u; k <= 9u; k++) { uint8_t keep = image[3]; image[3] = (uint8_t)('0' + k); CHECK(sq_image_ok(image, n) != 0); image[3] = keep; }
    CHECK(SQ_SAVE_MAGIC7 == 0x37514753u && SQ_SAVE_MAGIC9 == 0x39514753u && SQ_SAVE_MAGICA == 0x41514753u && SQ_SAVE_MAGIC == 0x42514753u && image[3] == 'B');
    { uint8_t keep = image[3]; image[3] = 'C'; CHECK(sq_image_ok(image, n) != 0); image[3] = keep; }
    {   /* a 0.10 image (SGQA): 80-byte tracks under the old magic (made here from the SGQB image: 16 bytes taken off
         * every track, in the project and in the snapshots); read whole: the algorithm slots 2..4 off, the harmony's
         * genre (reserved then) the genre, everything else as it was */
        static uint8_t img_a[400000];
        uint32_t a = 0u, b = 0u, head = 4u + 4u + 2u + 1u + 3u + 1u + (uint32_t)sizeof proj_a.key + (uint32_t)sizeof proj_a.device;
        uint8_t smask, t2;
        memcpy(img_a, image, head); a = b = head;
        img_a[3] = 'A';
        for (k = 0; k < SQ_UPROG_SLOTS; k++) { if (k < SQ_UPROGS) { memcpy(img_a + a, image + b, SQ_UPROG_A); a += SQ_UPROG_A; } b += (uint32_t)sizeof(sq_uprog_t); }   /* (0.10: four of 18 bytes) */
        for (k = 0; k < SQ_TRACKS; k++) { memcpy(img_a + a, image + b, SQ_TRACK_CFG_A); a += SQ_TRACK_CFG_A; b += (uint32_t)sizeof(sq_track_cfg_t); }
        k = (uint32_t)sizeof proj_a.scene + (uint32_t)sizeof proj_a.lfo;
        memcpy(img_a + a, image + b, k); a += k; b += k;
        memcpy(img_a + a, image + b, SQ_GEN_A); a += SQ_GEN_A; b += (uint32_t)sizeof proj_a.gen;   /* (0.10: 24 bytes of settings) */
        k = (uint32_t)sizeof proj_a.song + (uint32_t)sizeof proj_a.live + (uint32_t)sizeof proj_a.viaggio + (uint32_t)sizeof proj_a.tape_cnt + 1u;
        memcpy(img_a + a, image + b, k); a += k; b += k;
        smask = image[b - 1u];
        for (k = 0; k < SQ_SNAPS; k++) {
            uint8_t tm[2], lf;
            uint32_t ccn, hb = b;
            if (!(smask & (1u << k))) continue;
            memcpy(img_a + a, image + b, SQ_SNAP_HEAD + 2u); tm[0] = image[b + SQ_SNAP_HEAD]; tm[1] = image[b + SQ_SNAP_HEAD + 1u]; a += SQ_SNAP_HEAD + 2u; b += SQ_SNAP_HEAD + 2u;
            for (t2 = 0; t2 < SQ_TRACKS; t2++) if (tm[t2 >> 3] & (1u << (t2 & 7u))) { memcpy(img_a + a, image + b, SQ_TRACK_CFG_A); a += SQ_TRACK_CFG_A; b += (uint32_t)sizeof(sq_track_cfg_t); }
            lf = image[b]; img_a[a++] = image[b++];
            if (lf) { memcpy(img_a + a, image + b, sizeof proj_a.lfo); a += (uint32_t)sizeof proj_a.lfo; b += (uint32_t)sizeof proj_a.lfo; }
            ccn = (uint32_t)image[hb + 1u] * 3u;                                             /* head[1]: the CC values */
            memcpy(img_a + a, image + b, ccn); a += ccn; b += ccn;
        }
        memcpy(img_a + a, image + b, n - b); a += n - b;
        CHECK(sq_image_ok(img_a, a) == 0);
        memset(&proj_b, 0x55, sizeof proj_b);
        CHECK(sq_deserialize(&proj_b, img_a, a) == 0);
        CHECK(proj_b.gen.harm_genre == proj_b.gen.genre && proj_b.gen.harm_lock == 0u);
        for (k = 0; k < SQ_SNAPS; k++) if (proj_b.snap[k].used) CHECK(proj_b.snap[k].harm_genre == proj_b.snap[k].genre);
        for (k = 0; k < SQ_TRACKS; k++) {
            CHECK(!memcmp(&proj_b.track[k], &proj_a.track[k], SQ_TRACK_CFG_A));              /* the 80 bytes as they were */
            CHECK(proj_b.track[k].algo2[0].algo == SQ_ALGO_OFF && proj_b.track[k].algo2[2].algo == SQ_ALGO_OFF && proj_b.track[k].follow_mode == SQ_FM_HOLD);
        }
        for (k = 0; k < SQ_UPROGS; k++) CHECK(!memcmp(&proj_b.uprog[k], &proj_a.uprog[k], SQ_UPROG_A) && proj_b.uprog[k].semi[0] == 255u && proj_b.uprog[k].dur[3] == 0u);
        CHECK(proj_b.uprog[SQ_UPROGS].n == 0u && proj_b.gen.harm_rhythm == SQ_HR_BARS && proj_b.gen.harm_mood == SQ_MOOD_ANY && !memcmp(&proj_b.gen, &proj_a.gen, 12u));
        CHECK(!memcmp(proj_b.step, proj_a.step, sizeof proj_a.step) && proj_b.tape_n == proj_a.tape_n);
        CHECK(sq_image_track(img_a, a, 7u, 0u, &cfg, row) == 0 && !memcmp(&cfg, &proj_a.track[7], SQ_TRACK_CFG_A) && cfg.algo2[1].algo == SQ_ALGO_OFF);   /* RELOAD from a 0.10 image */
        CHECK(sq_image_ok(img_a, a - 1u) != 0);
    }
    {   /* a snapshot that says it holds more CC values than it can: refused */
        uint32_t off = 4u + 4u + 2u + 1u + 3u + 1u + (uint32_t)sizeof proj_a.key + (uint32_t)sizeof proj_a.device + (uint32_t)sizeof proj_a.uprog
                     + (uint32_t)sizeof proj_a.track + (uint32_t)sizeof proj_a.scene + (uint32_t)sizeof proj_a.lfo + (uint32_t)sizeof proj_a.gen
                     + (uint32_t)sizeof proj_a.song + (uint32_t)sizeof proj_a.live + (uint32_t)sizeof proj_a.viaggio + (uint32_t)sizeof proj_a.tape_cnt + 1u;   /* snapshot 1's head */
        uint8_t keep = image[off + 1u];
        CHECK(image[off] == 1u && image[off + 1u] == 3u);
        image[off + 1u] = 200u;
        CHECK(sq_image_ok(image, n) != 0);
        image[off + 1u] = keep;
        CHECK(sq_image_ok(image, n) == 0);
    }
}

/* 0.8: the theory and the live layer's pure parts */
static void test_v08(void)
{
    uint8_t notes[SQ_POLY_OUT], n, i;
    uint32_t rng = 3u, k;
    /* scale index: C minor, octave by octave */
    CHECK(sq_scale_index(60u, 0u, SQ_SC_MINOR) == 35 && sq_scale_index(62u, 0u, SQ_SC_MINOR) == 36 && sq_scale_index(63u, 0u, SQ_SC_MINOR) == 37);
    CHECK(sq_scale_index(61u, 0u, SQ_SC_MINOR) == 35);                  /* outside the scale: the one under */
    CHECK(sq_scale_at(35, 0u, SQ_SC_MINOR) == 60u && sq_scale_at(42, 0u, SQ_SC_MINOR) == 72u && sq_scale_at(37, 0u, SQ_SC_MINOR) == 63u);
    for (k = 0; k < 128u; k++) {
        uint8_t v = sq_scale_snap((uint8_t)k, 5u, SQ_SC_DORIAN);
        CHECK(sq_scale_at(sq_scale_index(v, 5u, SQ_SC_DORIAN), 5u, SQ_SC_DORIAN) == v);
    }
    /* harmony scale */
    CHECK(sq_harm_scale(SQ_SC_DORIAN) == SQ_SC_DORIAN && sq_harm_scale(SQ_SC_PENT_MINOR) == SQ_SC_MINOR && sq_harm_scale(SQ_SC_CHROMATIC) == SQ_SC_MINOR);
    CHECK(sq_harm_scale(SQ_SC_PENT_MAJOR) == SQ_SC_MAJOR && sq_harm_scale(SQ_SC_BLUES) == SQ_SC_MINOR);
    {   /* chord names */
        char b[12];
        sq_harm_chord_name(SQ_SC_MINOR, 0, SQ_HC_7, b); CHECK(!strcmp(b, "i7"));
        sq_harm_chord_name(SQ_SC_MINOR, 1, SQ_HC_TRIAD, b); CHECK(!strcmp(b, "iio"));
        sq_harm_chord_name(SQ_SC_MINOR, 5, SQ_HC_9, b); CHECK(!strcmp(b, "VI9"));
        sq_harm_chord_name(SQ_SC_MAJOR, 4, SQ_HC_SUS4, b); CHECK(!strcmp(b, "Vsus4"));
        sq_harm_chord_name(SQ_SC_MAJOR, 6, SQ_HC_TRIAD, b); CHECK(!strcmp(b, "viio"));
        sq_harm_chord_name(SQ_SC_HARM_MINOR, 2, SQ_HC_TRIAD, b); CHECK(!strcmp(b, "III+"));
    }
    /* the tonic triad of C minor moved: to VI (down a third: Ab C Eb), to iv (F Ab C), sus4, the 7th added */
    notes[0] = 60u; notes[1] = 63u; notes[2] = 67u; notes[3] = SQ_NOTE_NONE;
    n = sq_harm_apply(notes, 3u, 0u, SQ_SC_MINOR, 5, SQ_HC_TRIAD, 1u);
    CHECK(n == 3u && notes[0] == 56u && notes[1] == 60u && notes[2] == 63u);
    notes[0] = 60u; notes[1] = 63u; notes[2] = 67u;
    n = sq_harm_apply(notes, 3u, 0u, SQ_SC_MINOR, 3, SQ_HC_TRIAD, 1u);
    CHECK(n == 3u && notes[0] == 65u && notes[1] == 68u && notes[2] == 72u);
    notes[0] = 60u; notes[1] = 63u; notes[2] = 67u;
    n = sq_harm_apply(notes, 3u, 0u, SQ_SC_MINOR, 0, SQ_HC_SUS4, 1u);  /* C F G */
    CHECK(n == 3u && notes[0] == 60u && notes[1] == 65u && notes[2] == 67u);
    notes[0] = 60u; notes[1] = 63u; notes[2] = 67u;
    n = sq_harm_apply(notes, 3u, 0u, SQ_SC_MINOR, 0, SQ_HC_7, 1u);     /* C Eb G Bb */
    CHECK(n == 4u && notes[3] == 70u);
    notes[0] = 60u; notes[1] = 63u; notes[2] = 67u;
    n = sq_harm_apply(notes, 3u, 0u, SQ_SC_MINOR, 5, SQ_HC_9, 1u);     /* VI9: Ab C Eb + Bb on top */
    CHECK(n == 4u && notes[0] == 56u && notes[3] == 70u);
    notes[0] = 60u; notes[1] = 63u; notes[2] = 67u; notes[3] = 72u;     /* four notes: the 7th goes on top (0.10: six voices) */
    n = sq_harm_apply(notes, 4u, 0u, SQ_SC_MINOR, 0, SQ_HC_7, 1u);
    CHECK(n == 5u && notes[4] == 82u && notes[0] == 60u);
    notes[0] = 60u; notes[1] = 63u; notes[2] = 67u; notes[3] = 70u; notes[4] = 74u; notes[5] = 77u;   /* six: full, the 9th replaces a note */
    n = sq_harm_apply(notes, 6u, 0u, SQ_SC_MINOR, 0, SQ_HC_9, 1u);
    CHECK(n == 6u && notes[0] == 60u);
    for (i = 0; i < n; i++) CHECK(notes[i] != SQ_NOTE_NONE);
    notes[0] = 36u;                                                     /* a bass note: only moved, never coloured */
    n = sq_harm_apply(notes, 1u, 0u, SQ_SC_MINOR, 5, SQ_HC_7, 0u);
    CHECK(n == 1u && notes[0] == 32u);                                  /* C2 -> Ab1 (down) */
    notes[0] = 36u;
    n = sq_harm_apply(notes, 1u, 0u, SQ_SC_MINOR, 0, SQ_HC_TRIAD, 0u);
    CHECK(n == 1u && notes[0] == 36u);                                  /* the tonic: as written */
    for (k = 0; k < 2000u; k++) {                                       /* never out of range, never doubled */
        uint8_t m, j, cnt = (uint8_t)(1u + sq_rng_next(&rng) % 4u), sc = (uint8_t)(sq_rng_next(&rng) % SQ_SCALES);
        for (j = 0; j < cnt; j++) notes[j] = (uint8_t)(sq_rng_next(&rng) % 128u);
        m = sq_harm_apply(notes, cnt, (uint8_t)(sq_rng_next(&rng) % 12u), sc, (int8_t)(sq_rng_next(&rng) % 7u), (uint8_t)(sq_rng_next(&rng) % SQ_HCS), cnt >= 2u);
        CHECK(m >= 1u && m <= SQ_POLY_OUT);
        for (j = 0; j < m; j++) { uint8_t q; CHECK(notes[j] <= 127u); for (q = 0; q < j; q++) CHECK(notes[q] != notes[j]); }
    }
    /* voicing: duplicates go */
    {
        uint8_t in[4] = {60u, 60u, 64u, SQ_NOTE_NONE}, out[4];
        CHECK(sq_voice_notes(in, 4u, SQ_VOICE_CLOSE, out) == 2u && out[0] == 60u && out[1] == 64u);
        in[0] = 60u; in[1] = 72u; in[2] = 64u; in[3] = 67u;
        CHECK(sq_voice_notes(in, 4u, SQ_VOICE_INV1, out) == 3u);       /* (60 up an octave meets 72) */
    }
    /* TURING: mutation 0 loops exactly, 100 inverts the bit every time */
    {
        uint32_t r = 0x2Du, r0 = r, j;
        for (j = 0; j < 8u; j++) r = sq_turing_step(r, 8u, 0u, j * 37u);
        CHECK(r == r0);
        r = 0x0Fu;
        for (j = 0; j < 8u; j++) r = sq_turing_step(r, 8u, 100u, 0u);
        CHECK(r == 0xF0u);
        CHECK(sq_turing_step(0xFFFFFFFFu, 4u, 0u, 0u) == 0x0Fu);        /* only its length counts */
    }
    /* CELL: rule 90 from one cell spreads symmetrically; never all empty */
    {
        uint64_t row = (uint64_t)1u << 8, r2;
        r2 = sq_cell_next(row, 16u, 90u);
        CHECK(r2 == (((uint64_t)1u << 7) | ((uint64_t)1u << 9)));
        CHECK(sq_cell_next(0u, 16u, 0u) != 0u && sq_cell_next(0xFFFFu, 16u, 0u) == ((uint64_t)1u << 8));
        CHECK((sq_cell_next(~(uint64_t)0, 64u, 255u)) == ~(uint64_t)0);
    }
    /* ACCENT */
    CHECK(sq_accent(0u, 30u, 0u, 0u, 0u) == 30 && sq_accent(0u, 30u, 0u, 1u, 0u) == -10 && sq_accent(0u, 30u, 1u, 3u, 0u) == 30);
    CHECK(sq_accent(1u, 40u, 0u, 2u, 0u) == 40 && sq_accent(2u, 40u, 0u, 3u, 0u) == 40 && sq_accent(3u, 40u, 0u, 3u, 0u) == 40);
    /* DENSITY: 100 = as written; 0 = nothing; 200 = every rest gets a ghost; the beat survives longest */
    {
        uint8_t gh, j, drop_beat = 0u, drop_off = 0u;
        for (j = 0; j < 16u; j++) {
            CHECK(sq_density_hit(1u, 100u, j, j * 31u, &gh) == 1u && !gh);
            CHECK(sq_density_hit(0u, 100u, j, j * 31u, &gh) == 0u);
            CHECK(sq_density_hit(1u, 0u, j, j * 31u, &gh) == 0u);
            if ((j & 3u) && (j & 3u) != 2u) CHECK(sq_density_hit(0u, 200u, j, j * 31u, &gh) == 1u && gh);
        }
        for (k = 0; k < 400u; k++) {
            if (!sq_density_hit(1u, 40u, 0u, k * 7919u, &gh)) drop_beat++;
            if (!sq_density_hit(1u, 40u, 1u, k * 7919u, &gh)) drop_off++;
        }
        CHECK(drop_beat < drop_off);
    }
    /* EUCLID one step at a time = the whole pattern */
    {
        uint8_t bits[SQ_STEPS], p, len, r, j;
        for (len = 1u; len <= 20u; len++) for (p = 1u; p <= len; p++) for (r = 0; r < 3u; r++) {
            sq_euclid(p, len, r, bits);
            for (j = 0; j < len; j++) CHECK(sq_euclid_hit(p, len, r, j) == bits[j]);
        }
    }
    /* EVOLVE with the theory: notes stay in the key; strong beats on the tonic chord; a bass keeps root / fifth */
    {
        static sq_step_t row[SQ_STEPS];
        uint32_t j, rr = 11u;
        for (k = 0; k < 30u; k++) {
            sq_row_clear(row);
            for (j = 0; j < 16u; j++) { row[j].flags = SQ_STEP_ON | SQ_STEP_SET; row[j].note[0] = (uint8_t)(62u + (j % 5u) * 2u); }
            sq_row_evolve_notes(row, 16u, 100u, 2u, SQ_SC_DORIAN, 0u, 66u, &rr);
            for (j = 0; j < 16u; j++) {
                uint8_t v = row[j].note[0];
                int32_t rel = ((int32_t)v - 2 + 120) % 12;
                CHECK(in_key(v, 2u, SQ_SC_DORIAN) && v >= 48u && v <= 84u);
                if ((j & 3u) == 0u) CHECK(rel == 0 || rel == 3 || rel == 7);   /* D dorian: D F A */
                if (j) { int32_t leap = (int32_t)v - (int32_t)row[j - 1u].note[0]; CHECK(leap <= 7 && leap >= -7); }
            }
            sq_row_clear(row);
            for (j = 0; j < 16u; j++) { row[j].flags = SQ_STEP_ON | SQ_STEP_SET; row[j].note[0] = 38u; }
            sq_row_evolve_notes(row, 16u, 100u, 2u, SQ_SC_DORIAN, 1u, 38u, &rr);
            for (j = 0; j < 16u; j += 4u) { int32_t rel = ((int32_t)row[j].note[0] - 2 + 120) % 12; CHECK(rel == 0 || rel == 7); }
        }
        sq_row_clear(row);                                               /* a locked step does not move */
        for (j = 0; j < 8u; j++) { row[j].flags = SQ_STEP_ON | SQ_STEP_SET | (j == 3u ? SQ_STEP_LOCK : 0u); row[j].note[0] = 61u; }
        sq_row_evolve_notes(row, 8u, 100u, 0u, SQ_SC_MAJOR, 0u, 60u, &rr);
        CHECK(row[3].note[0] == 61u);
    }
    /* algorithm defaults and ranges */
    {
        sq_track_cfg_t c;
        sq_track_default(&c, 3u);
        CHECK(c.algo == SQ_ALGO_OFF && c.pen == 60u && c.mfx == SQ_MFX_OFF && c.euc_pulses == 4u && !(c.flags & SQ_TF_EUC));
        sq_algo_default(&c, SQ_ALGO_TURING); CHECK(c.algo_a == 10u && c.algo_b == 8u && c.algo_c == SQ_TM_RHYTHM);
        sq_algo_default(&c, SQ_ALGO_DENSITY); CHECK(c.algo_a == 100u);
        c.algo = SQ_ALGO_TURING; c.algo_a = 250u; c.algo_b = 40u; c.algo_c = 9u;
        c.mfx = SQ_MFX_OCTAVE; c.mfx_amt = 8; c.mfx_time = 30u; c.mfx_fb = 0u; c.euc_pulses = 0u; c.euc_rot = 99u; c.pen = 200u;
        c.channel = 15u; c.flags = SQ_TF_DRUM | SQ_TF_FOLLOW | SQ_TF_EUC;
        sq_track_sanitize(&c);
        CHECK(c.algo_a == 100u && c.algo_b == 16u && c.algo_c == SQ_TM_RHYTHM);
        CHECK(c.mfx_amt == 2 && c.mfx_time == 6u && c.mfx_fb == 10u && c.euc_pulses == 1u && c.euc_rot == 0u && c.pen == 60u);
        CHECK(c.channel == 15u && c.flags == (SQ_TF_DRUM | SQ_TF_EUC));   /* a drum does not follow; 16 channels kept */
        c.mfx = SQ_MFX_ECHO; c.mfx_amt = -3; sq_track_sanitize(&c); CHECK(c.mfx_amt == 0);
    }
    CHECK(sq_echo_ticks(6u) == 18u && sq_echo_ticks(0u) == 3u && sq_echo_ticks(99u) == 18u);
    CHECK(sq_hash3(1u, 2u, 3u) == sq_hash3(1u, 2u, 3u) && sq_hash3(1u, 2u, 3u) != sq_hash3(1u, 2u, 4u));
}

/* 0.5: lengths per parameter */
static void test_planes(void)
{
    sq_track_cfg_t c;
    sq_track_rt_t rt;
    static sq_step_t row[SQ_STEPS];
    sq_step_t out;
    uint32_t rng = 9u, i, k;
    sq_track_default(&c, 0u);
    memset(&rt, 0, sizeof rt);
    for (i = 0; i < SQ_STEPS; i++) { sq_step_default(&row[i]); row[i].note[0] = (uint8_t)(30u + i); row[i].velocity = (uint8_t)(10u + i); row[i].length = (uint8_t)(1u + i); }
    CHECK(sq_plane_len(&c, SQ_PL_NOTE) == 0u && sq_plane_step(&c, &rt, SQ_PL_NOTE, 7u) == 7u);
    sq_plane_compose(&c, &rt, row, 7u, &out);
    CHECK(!memcmp(&out, &row[7], sizeof out));                           /* nothing of its own: the step as it is */

    c.length = 16u; c.start = 0u; c.plen[SQ_PL_NOTE] = 5u; c.plen[SQ_PL_VEL] = 3u;
    rt.step = 0u; rt.ppos[0] = rt.ppos[1] = rt.ppos[2] = 0u;
    for (i = 0; i < 240u; i++) {                                         /* 16 x 5 x 3: after 240 steps all are back */
        uint8_t s = rt.step;
        sq_plane_compose(&c, &rt, row, s, &out);
        CHECK(out.note[0] == 30u + (i % 5u) && out.velocity == 10u + (i % 3u) && out.length == row[s].length);
        CHECK(out.flags == row[s].flags && out.chance == row[s].chance);
        sq_advance_step(&c, &rt, &rng);
    }
    CHECK(rt.step == 0u && rt.ppos[0] == 0u && rt.ppos[1] == 0u);
    /* SPP: the same place as moving there step by step */
    for (k = 0; k < 4u; k++) {
        sq_track_rt_t a, b;
        uint32_t steps = 37u + k * 101u;
        c.start = (uint8_t)(k * 3u); c.length = (uint8_t)(c.start + 13u); c.plen[SQ_PL_GATE] = (uint8_t)(k + 2u);
        memset(&a, 0, sizeof a); a.step = c.start;
        for (i = 0; i < steps; i++) sq_advance_step(&c, &a, &rng);
        memset(&b, 0, sizeof b);
        sq_plane_seek(&c, &b, steps);
        CHECK(!memcmp(a.ppos, b.ppos, sizeof a.ppos));
        CHECK(sq_plane_step(&c, &a, SQ_PL_GATE, a.step) == c.start + steps % (k + 2u));
    }
    /* a loop of its own never goes past step 64 */
    c.start = 60u; c.length = 64u; c.plen[SQ_PL_NOTE] = 64u;
    CHECK(sq_plane_len(&c, SQ_PL_NOTE) == 4u);
    memset(&rt, 0, sizeof rt); rt.step = 60u;
    for (i = 0; i < 50u; i++) { CHECK(sq_plane_step(&c, &rt, SQ_PL_NOTE, rt.step) >= 60u && sq_plane_step(&c, &rt, SQ_PL_NOTE, rt.step) < 64u); sq_advance_step(&c, &rt, &rng); }
    rt.ppos[0] = 200u;                                                   /* (the loop got shorter meanwhile) */
    CHECK(sq_plane_step(&c, &rt, SQ_PL_NOTE, 61u) < 64u);
}


static void test_v07_music_tools(void)
{
    sq_step_t st;
    uint8_t out[4], n;
    sq_step_default(&st);
    st.note[0] = 60u; st.note[1] = 64u; st.note[2] = 67u; st.note[3] = 71u;
    n = sq_chord_voice(&st, SQ_VOICE_CLOSE, out);
    CHECK(n == 4u && out[0] == 60u && out[1] == 64u && out[2] == 67u && out[3] == 71u);
    n = sq_chord_voice(&st, SQ_VOICE_INV1, out);
    CHECK(n == 4u && out[0] == 64u && out[1] == 67u && out[2] == 71u && out[3] == 72u);
    n = sq_chord_voice(&st, SQ_VOICE_DROP2, out);
    CHECK(n == 4u && out[0] == 55u && out[1] == 60u && out[2] == 64u && out[3] == 71u);
    n = sq_chord_voice(&st, SQ_VOICE_OPEN, out);
    CHECK(n == 4u && out[0] == 60u && out[1] == 67u && out[2] == 76u && out[3] == 83u);
    CHECK(sq_mfx_velocity(64u, 0) == 64u);
    CHECK(sq_mfx_velocity(64u, 8) == 127u);
    CHECK(sq_mfx_velocity(64u, -8) == 1u);
}


/* 0.9: VIAGGIO's pure parts; 0.10: the SGQA image */
static void test_v09(void)
{
    sq_queue_t q;
    sq_trail_t tr;
    static sq_phrase_t ring[SQ_TRAIL];
    sq_phrase_t ph;
    sq_energy_fx_t fx;
    sq_track_cfg_t cfg;
    static sq_step_t row[SQ_STEPS];
    uint32_t n, k, i;
    uint8_t sel[16], bars[16];

    /* the queue: push, replace, cancel, full */
    sq_queue_clear(&q);
    CHECK(sq_queue_push(&q, SQ_MV_IN, 3u, 255u) == 0 && q.n == 1u);
    CHECK(sq_queue_push(&q, SQ_MV_IN, 3u, 2u) == 0 && q.n == 1u && q.m[0].b == 2u);     /* the same track: replaced */
    CHECK(sq_queue_push(&q, SQ_MV_OUT, 3u, 0u) == 0 && q.n == 0u);                     /* OUT cancels the IN */
    CHECK(sq_queue_push(&q, SQ_MV_FILL, 0u, 0u) == 0 && sq_queue_push(&q, SQ_MV_FILL, 0u, 0u) == 0 && q.n == 1u);
    CHECK(sq_queue_push(&q, SQ_MV_HALF, 0u, 0u) == 0 && sq_queue_push(&q, SQ_MV_DOUBLE, 0u, 0u) == 0 && q.n == 1u);
    CHECK(sq_queue_push(&q, SQ_MV_IN, 1u, 0u) == 0 && sq_queue_push(&q, SQ_MV_IN, 2u, 0u) == 0 && q.n == 3u);
    CHECK(sq_queue_find(&q, SQ_MV_IN, 2u) == 2 && sq_queue_find(&q, SQ_MV_IN, 9u) < 0 && sq_queue_find(&q, SQ_MV_FILL, 7u) == 0);
    sq_queue_remove(&q, 0u);
    CHECK(q.n == 2u && q.m[0].kind == SQ_MV_IN && q.m[0].a == 1u);
    sq_queue_drop_last(&q);
    CHECK(q.n == 1u);
    for (k = 0; k < SQ_MOVES + 4u; k++) sq_queue_push(&q, SQ_MV_IN, (uint8_t)(k + 3u), 0u);
    CHECK(q.n == SQ_MOVES && sq_queue_push(&q, SQ_MV_RISER, 0u, 0u) == -1);
    CHECK(sq_queue_push(&q, 0u, 0u, 0u) == -1 && sq_queue_push(&q, SQ_MOVE_KINDS, 0u, 0u) == -1);
    sq_queue_clear(&q);
    CHECK(q.n == 0u && sq_move_has_track(SQ_MV_SWAP) && !sq_move_has_track(SQ_MV_DROP));
    for (k = 0; k < SQ_MOVE_KINDS; k++) CHECK(strlen(sq_move_name((uint8_t)k)) <= 9u);
    CHECK(!strcmp(sq_move_name(SQ_MV_BREAK), "BREAK") && !strcmp(sq_move_name(200u), "-"));

    /* the trail: a ring of 128 */
    sq_trail_init(&tr);
    CHECK(sq_trail_get(&tr, ring, 0u) == 0);
    memset(&ph, 0, sizeof ph);
    for (k = 0; k < 130u; k++) { ph.energy = (uint8_t)k; ph.pattern[0] = (uint8_t)(k / 10u); sq_trail_push(&tr, ring, &ph); }
    CHECK(tr.n == SQ_TRAIL && sq_trail_get(&tr, ring, 0u)->energy == 129u && sq_trail_get(&tr, ring, 127u)->energy == 2u);
    CHECK(sq_trail_get(&tr, ring, 128u) == 0);
    sq_trail_drop(&tr, 3u);
    CHECK(tr.n == 125u && sq_trail_get(&tr, ring, 0u)->energy == 126u);
    sq_trail_drop(&tr, 200u);
    CHECK(tr.n == 0u && sq_trail_get(&tr, ring, 0u) == 0);
    /* SALVA VIAGGIO: runs of equal phrases, the longest kept */
    memset(&ph, 0, sizeof ph);
    for (k = 0; k < 20u; k++) { ph.pattern[1] = (uint8_t)(k < 8u ? 0u : k < 9u ? 1u : k < 15u ? 2u : 3u); sq_trail_push(&tr, ring, &ph); }
    n = sq_trail_scenes(&tr, ring, 16u, 16u, sel, bars);
    CHECK(n == 4u && sel[0] == 0u && bars[0] == 64u && sel[1] == 8u && bars[1] == 16u && sel[2] == 9u && bars[2] == 64u && sel[3] == 15u);
    n = sq_trail_scenes(&tr, ring, 4u, 3u, sel, bars);          /* room for three: the one-phrase run goes */
    CHECK(n == 3u && sel[0] == 0u && bars[0] == 32u && sel[1] == 9u && bars[1] == 24u && sel[2] == 15u && bars[2] == 20u);
    CHECK(sq_trail_scenes(&tr, ring, 16u, 0u, sel, bars) == 0u);

    /* the energy */
    sq_energy_map(50u, &fx);
    CHECK(fx.vel == 0 && fx.filt == 0 && fx.gate == 0 && fx.density == 100u && fx.lfo_pct == 100u && !fx.color7);   /* 0.17: 50 neutral */
    sq_energy_map(0u, &fx);
    CHECK(fx.vel == -20 && fx.filt == -40 && fx.density == 60u && fx.lfo_pct == 50u);
    sq_energy_map(100u, &fx);
    CHECK(fx.vel == 20 && fx.filt == 40 && fx.gate == 10 && fx.density == 130u && fx.lfo_pct == 100u && fx.color7);
    sq_energy_map(200u, &fx);
    CHECK(fx.vel == 20 && fx.density == 130u);
    CHECK(sq_energy_glide(20u, 100u, 0u, 16u) == 25u && sq_energy_glide(20u, 100u, 15u, 16u) == 100u);
    CHECK(sq_energy_glide(100u, 0u, 7u, 8u) == 0u && sq_energy_glide(40u, 40u, 3u, 16u) == 40u && sq_energy_glide(10u, 90u, 9u, 0u) == 90u);
    CHECK(sq_energy_riser(40u, 0u, 16u) == 40u && sq_energy_riser(40u, 11u, 16u) == 40u && sq_energy_riser(40u, 12u, 16u) == 55u && sq_energy_riser(40u, 15u, 16u) == 100u);
    CHECK(sq_energy_riser(40u, 3u, 4u) == 100u && sq_energy_riser(120u, 0u, 16u) == 100u);

    /* the genres of the set and the roles */
    for (k = 0; k < SQ_SET_GENRES; k++) {
        const sq_set_genre_t *g = sq_set_genre((uint8_t)k);
        CHECK(strlen(g->name) <= 10u && g->genre < SQ_GENRES && g->genre2 < SQ_GENRES && g->swing >= 50u && g->swing <= 75u);
        for (i = 0; i < SQ_ROLES; i++) CHECK(g->ladder[i] <= 100u && sq_role_energy((uint8_t)k, (uint8_t)i) == g->ladder[i]);
        CHECK(g->ladder[0] <= 15u);                              /* the kick comes first */
    }
    CHECK(sq_set_genre(99u) == sq_set_genre(0u) && sq_role_energy(2u, 9u) == sq_role_energy(2u, 0u));
    CHECK(sq_role_for_track(1u, 1u, 36u, 1u, 0u, 0u) == 0u && sq_role_for_track(1u, 1u, 38u, 1u, 0u, 0u) == 1u);
    CHECK(sq_role_for_track(1u, 1u, 42u, 1u, 0u, 0u) == 2u && sq_role_for_track(1u, 1u, 50u, 1u, 0u, 0u) == 3u);
    CHECK(sq_role_for_track(1u, 0u, 40u, 1u, 0u, 0u) == 4u && sq_role_for_track(1u, 0u, 55u, 1u, 0u, 0u) == 5u && sq_role_for_track(1u, 0u, 72u, 1u, 0u, 0u) == 6u);
    /* an empty track: the roles by the ladder, skipping the ones taken; dub techno (2): kick, hat, chord, bass, perc, snare, arp */
    CHECK(sq_role_for_track(2u, 0u, 60u, 0u, 0u, 0u) == 0u && sq_role_for_track(2u, 0u, 60u, 0u, 1u, 0u) == 2u);
    CHECK(sq_role_for_track(2u, 0u, 60u, 0u, 0u, 1u) == 2u && sq_role_for_track(2u, 0u, 60u, 0u, 2u, 0u) == 5u);
    CHECK(sq_role_for_track(1u, 0u, 60u, 0u, 0u, 0x7Fu) < SQ_ROLES);
    {   /* the same empty track asked twice gets the same role; eight tracks cover every role */
        uint8_t taken = 0u, r;
        for (k = 0; k < 7u; k++) { r = sq_role_for_track(2u, 0u, 60u, 0u, (uint8_t)k, taken); CHECK(!(taken & (1u << r))); taken |= (uint8_t)(1u << r); }
        CHECK(taken == 0x7Fu);
    }

    /* AFRO / LATIN: patterns the library's loader can read */
    for (k = 0; k < SQ_AFRO_N; k++) {
        const sq_afro_t *a = sq_afro((uint8_t)k);
        CHECK(strlen(a->text) == a->steps && (a->steps == 16u || a->steps == 12u) && strlen(a->name) <= 9u);
        for (i = 0; i < a->steps; i++) CHECK(strchr(".xXog", a->text[i]) != 0);
        CHECK(a->text[0] != '.' || k == 2u);                     /* (2-3 starts on a rest) */
    }
    CHECK(sq_afro(99u) == sq_afro(0u));

    /* SGQA: everything in one image (no chunks known yet: an unknown one is skipped, a cut one refused); a 0.10 track
     * carries its EXPO, DELAY and TAPE settings */
    sq_project_init(&proj_a);
    proj_a.bpm = 133u; proj_a.key_root = 7u; proj_a.key_scale = SQ_SC_DORIAN;
    proj_a.scene[7].pattern[2] = 5u; proj_a.scene[3].mute_mask = 0x0F0Fu; proj_a.scene[12].pattern[0] = 3u; proj_a.scene[12].key_slot = 4u;
    proj_a.song.len = 40u; proj_a.song.e[39].scene = 15u; proj_a.song.e[39].bars = 2u; proj_a.song.e[39].bpm = 140u;
    proj_a.live.remote_mode = SQ_RM_13_14; proj_a.live.remote_ch = 13u; proj_a.live.quant = SQ_Q_BAR;
    proj_a.live.mac[0] = 12; proj_a.live.mac[3] = -20; proj_a.live.cc_lead_ms = 12u; proj_a.live.song_tempo = 1u;
    proj_a.viaggio.on = 1u; proj_a.viaggio.phrase_bars = 8u; proj_a.viaggio.energy = 77u; proj_a.viaggio.set_genre = 3u;
    proj_a.viaggio.state[4] = SQ_TS_IN; proj_a.viaggio.phrase_count = 9u; proj_a.viaggio.quant = SQ_VQ_BAR;
    proj_a.track[2].expo.shape = SQ_XS_BOUNCE; proj_a.track[2].expo.hits = 12u; proj_a.track[2].expo.curve = -5; proj_a.track[2].expo.span = SQ_XSPAN_BEAT;
    proj_a.track[2].expo.vel = SQ_XV_RISE; proj_a.track[2].expo.gate = 25u; proj_a.track[2].expo.jitter = 10u; proj_a.track[2].expo.notes = SQ_XN_ARP2;
    proj_a.track[5].delay_ms = -12; proj_a.track[15].delay_ms = 30;
    proj_a.track[6].role = SQ_ROLE_BASS; proj_a.track[6].chord = SQ_CH_MIN11; proj_a.track[6].chord_key = SQ_CK_STRICT; proj_a.track[6].octave = -2; proj_a.track[6].key_slot = 3u;
    proj_a.track[6].lane_flags[1] = SQ_LF_SLIDE | SQ_LF_TRIGLESS; proj_a.track[6].lane_flags[5] = SQ_LF_NRPN; proj_a.track[6].lane_hi[5] = 1u; proj_a.track[6].lane_cc[5] = 20u;
    proj_a.track[6].arp_rate = 2u; proj_a.track[6].arp_flags = SQ_AF_HOLD; proj_a.track[6].src_func = 4u; proj_a.track[6].src_var = 1u; proj_a.track[6].euc_fam = SQ_RF_TRESILLO;
    proj_a.key[3].root = 2u; proj_a.key[3].scale = SQ_SC_LYDIAN; proj_a.key[3].shift = -12; proj_a.key_cur = 0u;
    proj_a.device[4] = SQ_DEV_ELEKTRON;
    proj_a.uprog[1].n = 3u; proj_a.uprog[1].deg[0] = 0; proj_a.uprog[1].deg[1] = 5; proj_a.uprog[1].deg[2] = 3; proj_a.uprog[1].col[2] = SQ_HC_7; proj_a.uprog[1].bars = 2u;
    proj_a.gen.harm_prog = 7u; proj_a.gen.genre_mode = SQ_GM_LIVE; proj_a.gen.when = SQ_WHEN_4; proj_a.gen.every = SQ_EVERY_8; proj_a.gen.every_tool = 9u; proj_a.gen.lib_len = SQ_LL_32;
    proj_a.step[1][0][3].flags = SQ_STEP_ON | SQ_STEP_SET | SQ_STEP_TIE; proj_a.step[1][0][3].condition = SQ_COND_PRE; proj_a.step[1][0][3].lane[5] = 99u;
    sq_project_sanitize(&proj_a);
    proj_a.gen.harm_genre = 5u; proj_a.gen.harm_lock = 1u;                                   /* 0.11 */
    proj_a.snap[1].used = 1u; proj_a.snap[1].harm_genre = 9u; sq_project_sanitize(&proj_a);
    n = sq_serialize(&proj_a, image, sizeof image);
    CHECK(n > 0u && image[3] == 'B' && image[n - 1u] == 0u);
    memset(&proj_b, 0x55, sizeof proj_b);
    CHECK(sq_deserialize(&proj_b, image, n) == 0 && !memcmp(&proj_a, &proj_b, sizeof proj_a));
    CHECK(proj_b.bpm == 133u && proj_b.key_root == 7u && proj_b.key_scale == SQ_SC_DORIAN && proj_b.live.quant == SQ_Q_BAR);
    CHECK(proj_b.gen.harm_genre == 5u && proj_b.gen.harm_lock == 1u && proj_b.snap[1].harm_genre == 9u);   /* 0.11: SGQB keeps the harmony's own genre */
    CHECK(proj_b.scene[7].pattern[2] == 5u && proj_b.scene[3].mute_mask == 0x0F0Fu && proj_b.scene[12].key_slot == 4u && proj_b.scene[0].key_slot == SQ_KEY_FOLLOW);
    CHECK(proj_b.song.len == 40u && proj_b.song.e[39].scene == 15u && proj_b.song.e[39].bpm == 140u && proj_b.song.e[0].bpm == 0u);
    CHECK(proj_b.live.remote_mode == SQ_RM_13_14 && proj_b.live.mac[0] == 12 && proj_b.live.mac[3] == -20 && proj_b.live.cc_lead_ms == 12u && proj_b.live.song_tempo == 1u);
    CHECK(proj_b.viaggio.on == 1u && proj_b.viaggio.phrase_bars == 8u && proj_b.viaggio.energy == 77u && proj_b.viaggio.state[4] == SQ_TS_IN && proj_b.viaggio.quant == SQ_VQ_BAR);
    CHECK(proj_b.track[2].expo.shape == SQ_XS_BOUNCE && proj_b.track[2].expo.hits == 12u && proj_b.track[2].expo.curve == -5 && proj_b.track[2].expo.notes == SQ_XN_ARP2);
    CHECK(proj_b.track[5].delay_ms == -12 && proj_b.track[15].delay_ms == 30 && proj_b.track[6].role == SQ_ROLE_BASS && proj_b.track[6].chord == SQ_CH_MIN11 && proj_b.track[6].chord_key == SQ_CK_STRICT);
    CHECK(proj_b.track[6].octave == -2 && proj_b.track[6].key_slot == 3u && proj_b.track[6].lane_flags[1] == (SQ_LF_SLIDE | SQ_LF_TRIGLESS) && proj_b.track[6].lane_hi[5] == 1u);
    CHECK(proj_b.track[6].arp_rate == 2u && proj_b.track[6].arp_flags == SQ_AF_HOLD && proj_b.track[6].src_func == 4u && proj_b.track[6].euc_fam == SQ_RF_TRESILLO);
    CHECK(proj_b.key[3].scale == SQ_SC_LYDIAN && proj_b.key[3].shift == -12 && proj_b.key[0].root == 7u && proj_b.device[4] == SQ_DEV_ELEKTRON);
    CHECK(proj_b.uprog[1].n == 3u && proj_b.uprog[1].deg[1] == 5 && proj_b.uprog[1].col[2] == SQ_HC_7 && proj_b.gen.harm_prog == 7u && proj_b.gen.every_tool == 9u);
    CHECK((proj_b.step[1][0][3].flags & SQ_STEP_TIE) && proj_b.step[1][0][3].condition == SQ_COND_PRE && proj_b.step[1][0][3].lane[5] == 99u);
    CHECK(sq_image_track(image, n, 6u, 0u, &cfg, row) == 0 && cfg.role == SQ_ROLE_BASS && cfg.expo.shape == SQ_XS_OFF);   /* RELOAD reads a track */
    CHECK(sq_deserialize(&proj_b, image, n - 1u) != 0);        /* short by a byte: refused */
    {   /* an unknown chunk before the end is skipped; one cut short is refused */
        uint8_t img2[8000];
        uint32_t m = n - 1u;
        memcpy(img2, image, m);
        img2[m++] = 0x5Au; img2[m++] = 3u; img2[m++] = 0u; img2[m++] = 1u; img2[m++] = 2u; img2[m++] = 3u;   /* 'Z', 3 bytes */
        img2[m++] = 0u;
        CHECK(sq_deserialize(&proj_b, img2, m) == 0 && !memcmp(&proj_a, &proj_b, sizeof proj_a));
        CHECK(sq_deserialize(&proj_b, img2, m - 2u) != 0);     /* the chunk's bytes missing */
    }
    /* out of range in the image: sanitised (the delay, EXPO, the new fields) */
    proj_a.track[1].delay_ms = 100; proj_a.track[2].delay_ms = -100;
    proj_a.track[5].expo.shape = 9u; proj_a.track[5].expo.hits = 1u; proj_a.track[5].expo.curve = 50; proj_a.track[5].expo.span = 9u; proj_a.track[5].expo.gate = 0u; proj_a.track[5].expo.jitter = 99u; proj_a.track[5].expo.notes = 9u;
    proj_a.track[7].role = 40u; proj_a.track[7].chord = 40u; proj_a.track[7].chord_key = 9u; proj_a.track[7].octave = 9; proj_a.track[7].key_slot = 20u; proj_a.track[7].arp_rate = 9u; proj_a.track[7].lane_flags[0] = 0xFFu;
    proj_a.scene[2].key_slot = 30u; proj_a.song.e[2].bpm = 999u; proj_a.live.cc_lead_ms = 99u; proj_a.key[9].scale = 99u; proj_a.device[2] = 9u;
    proj_a.uprog[2].n = 9u; proj_a.uprog[3].deg[0] = 9; proj_a.gen.harm_prog = 11u; proj_a.gen.when = 9u; proj_a.gen.every = 9u; proj_a.gen.genre_mode = 9u;
    n = sq_serialize(&proj_a, image, sizeof image);
    CHECK(sq_deserialize(&proj_b, image, n) == 0 && proj_b.track[1].delay_ms == SQ_DELAY_MAX && proj_b.track[2].delay_ms == -SQ_DELAY_MAX);
    CHECK(proj_b.track[5].expo.shape == SQ_XS_OFF && proj_b.track[5].expo.hits == 2u && proj_b.track[5].expo.curve == 8
          && proj_b.track[5].expo.span == SQ_XSPAN_BAR && proj_b.track[5].expo.gate == 5u && proj_b.track[5].expo.jitter == 50u && proj_b.track[5].expo.notes == SQ_XN_CHORD);
    CHECK(proj_b.track[7].role == SQ_ROLE_NONE && proj_b.track[7].chord == SQ_CH_OFF && proj_b.track[7].octave == 3 && proj_b.track[7].key_slot == SQ_KEY_FOLLOW
          && proj_b.track[7].arp_rate == 0u && proj_b.track[7].lane_flags[0] == 7u && proj_b.track[7].chord_key == SQ_CK_DIATONIC);
    CHECK(proj_b.scene[2].key_slot == SQ_KEY_FOLLOW && proj_b.song.e[2].bpm == 0u && proj_b.live.cc_lead_ms == SQ_CC_LEAD_MAX && proj_b.key[9].scale == SQ_SC_CHROMATIC && proj_b.device[2] == SQ_DEV_GENERIC);
    CHECK(proj_b.uprog[2].n == 0u && proj_b.uprog[3].deg[0] == 0 && proj_b.gen.harm_prog == 0u && proj_b.gen.when == SQ_WHEN_NOW && proj_b.gen.every == SQ_EVERY_OFF && proj_b.gen.genre_mode == SQ_GM_ON);
    proj_a.track[1].delay_ms = proj_a.track[2].delay_ms = 0;
    sq_project_sanitize(&proj_a);
    n = sq_serialize(&proj_a, image, sizeof image);
    CHECK(proj_a.track[2].expo.shape == SQ_XS_BOUNCE && proj_a.track[2].expo.notes == SQ_XN_ARP2 && proj_a.track[2].expo.gate == 25u);
    /* 0.10: lanes and LFOs on BEND (128) / AFTERTOUCH (129) survive; 130 is no lane, an LFO's 200 becomes 129 */
    proj_a.track[3].lane_cc[0] = SQ_CC_BEND; proj_a.track[3].lane_cc[1] = SQ_CC_AT; proj_a.track[3].lane_cc[2] = 130u;
    proj_a.lfo[2].param = SQ_CC_AT; proj_a.lfo[3].param = 200u;
    n = sq_serialize(&proj_a, image, sizeof image);
    CHECK(sq_deserialize(&proj_b, image, n) == 0 && proj_b.track[3].lane_cc[0] == SQ_CC_BEND && proj_b.track[3].lane_cc[1] == SQ_CC_AT
          && proj_b.track[3].lane_cc[2] == SQ_LANE_NONE && proj_b.lfo[2].param == SQ_CC_AT && proj_b.lfo[3].param == SQ_CC_MAX);
    proj_a.track[3].lane_cc[0] = 74u; proj_a.track[3].lane_cc[1] = SQ_LANE_NONE; proj_a.track[3].lane_cc[2] = SQ_LANE_NONE;
    proj_a.lfo[2].param = 74u; proj_a.lfo[3].param = 74u;
    /* out of range in the image: sanitised */
    proj_a.viaggio.phrase_bars = 5u; proj_a.viaggio.energy = 250u; proj_a.viaggio.set_genre = 99u; proj_a.viaggio.state[0] = 7u; proj_a.viaggio.phrase_count = 200u; proj_a.viaggio.quant = 9u;
    n = sq_serialize(&proj_a, image, sizeof image);
    CHECK(sq_deserialize(&proj_b, image, n) == 0 && proj_b.viaggio.phrase_bars == 16u && proj_b.viaggio.energy == 100u && proj_b.viaggio.set_genre == 0u && proj_b.viaggio.state[0] == SQ_TS_EMPTY && proj_b.viaggio.phrase_count == 0u && proj_b.viaggio.quant == SQ_VQ_PHRASE);
    /* 0.17: a project saved with VIAGGIO off (0.9-0.16) comes back with the journey running and its energy neutral: it
     * plays as it did */
    proj_a.viaggio.on = 0u; proj_a.viaggio.energy = 80u; proj_a.viaggio.phrase_bars = 8u; proj_a.viaggio.set_genre = 0u; proj_a.viaggio.state[0] = SQ_TS_EMPTY;
    n = sq_serialize(&proj_a, image, sizeof image);
    CHECK(sq_deserialize(&proj_b, image, n) == 0 && proj_b.viaggio.on == 1u && proj_b.viaggio.energy == 50u && proj_b.viaggio.phrase_bars == 8u);
    proj_a.viaggio.on = 1u;
    sq_project_init(&proj_b);
    CHECK(proj_b.viaggio.on == 1u && proj_b.viaggio.energy == 50u);
    proj_a.live.remote_mode = 9u;
    sq_project_sanitize(&proj_a);
    CHECK(proj_a.live.remote_mode == SQ_RM_14);
}

/* 0.10: the pure parts that are new */
/* 0.11: a track made longer repeats its loop in the new steps (unless something was written there) */
static void test_v011_extend(void)
{
    static sq_step_t row[SQ_STEPS];
    uint32_t i;
    for (i = 0; i < SQ_STEPS; i++) sq_step_default(&row[i]);
    for (i = 0; i < 16u; i += 4u) { row[i].flags |= SQ_STEP_ON; row[i].note[0] = (uint8_t)(36u + i); }
    row[6].flags |= SQ_STEP_ON; row[6].velocity = 77u;
    /* 16 -> 64 in one go: four copies */
    CHECK(sq_row_extend(row, 0u, 16u, 16u, 64u) == 48u);
    for (i = 16u; i < 64u; i++) CHECK(!memcmp(&row[i], &row[i % 16u], sizeof row[0]));
    CHECK(row[38].velocity == 77u && (row[60].flags & SQ_STEP_ON) && !(row[61].flags & SQ_STEP_ON));
    /* a turn of the knob 16 -> 17 -> 18 ... each click fills from the loop of 16, not from the loop so far */
    for (i = 0; i < SQ_STEPS; i++) sq_step_default(&row[i]);
    row[0].flags |= SQ_STEP_ON; row[3].flags |= SQ_STEP_ON;
    for (i = 17u; i <= 24u; i++) CHECK(sq_row_extend(row, 0u, 16u, (uint8_t)(i - 1u), (uint8_t)i) == 1u);
    CHECK((row[16].flags & SQ_STEP_ON) && !(row[17].flags & SQ_STEP_ON) && (row[19].flags & SQ_STEP_ON) && !(row[20].flags & SQ_STEP_ON));
    /* shortened and lengthened again: what was written beyond the old length comes back, nothing is overwritten */
    for (i = 0; i < SQ_STEPS; i++) sq_step_default(&row[i]);
    row[0].flags |= SQ_STEP_ON; row[20].flags |= SQ_STEP_ON; row[20].note[0] = 99u;
    CHECK(sq_row_extend(row, 0u, 16u, 16u, 32u) == 0u && row[20].note[0] == 99u && !(row[16].flags & SQ_STEP_ON));
    /* a loop that starts late repeats its own span */
    for (i = 0; i < SQ_STEPS; i++) sq_step_default(&row[i]);
    row[4].flags |= SQ_STEP_ON; row[6].flags |= SQ_STEP_ON;
    CHECK(sq_row_extend(row, 4u, 8u, 8u, 16u) == 8u);
    CHECK((row[8].flags & SQ_STEP_ON) && !(row[9].flags & SQ_STEP_ON) && (row[10].flags & SQ_STEP_ON) && (row[12].flags & SQ_STEP_ON) && (row[14].flags & SQ_STEP_ON));
    /* no change: nothing longer, or past the end */
    CHECK(sq_row_extend(row, 0u, 16u, 16u, 16u) == 0u && sq_row_extend(row, 0u, 16u, 16u, 8u) == 0u);
    CHECK(sq_row_extend(row, 0u, 64u, 64u, 70u) == 0u);
    /* `from` under the period (the knob came back under it, then up): the period's own steps are left alone */
    for (i = 0; i < SQ_STEPS; i++) sq_step_default(&row[i]);
    row[0].flags |= SQ_STEP_ON; row[12].flags |= SQ_STEP_ON;
    CHECK(sq_row_extend(row, 0u, 16u, 12u, 20u) == 4u && (row[16].flags & SQ_STEP_ON) && !(row[17].flags & SQ_STEP_ON) && (row[12].flags & SQ_STEP_ON));
}

/* 0.11: COOK walks a row to the next variation, the weak places first; the generated melodic parts get their lengths */
static void test_v011_cook(void)
{
    static sq_step_t row[SQ_STEPS], target[SQ_STEPS];
    uint32_t rng = 7u, i, presses = 0u;
    uint8_t left, prev = 255u, beat_last = 1u;
    CHECK(sq_beat_load(row, SQ_GENRE_TECHNO, SQ_FUNC_HAT, 0u, 42u) == 16u);
    CHECK(sq_beat_load(target, SQ_GENRE_TECHNO, SQ_FUNC_HAT, 5u, 42u) > 0u);
    row[5].lane[2] = 77u;                                       /* a CC lock of the player's */
    row[9].flags |= SQ_STEP_LOCK;                               /* a locked step */
    for (presses = 0; presses < 40u; presses++) {
        uint8_t before[SQ_STEPS], k, changed_beat = 0u, changed_weak = 0u;
        for (k = 0; k < 16u; k++) before[k] = (uint8_t)(row[k].flags & SQ_STEP_ON);
        left = sq_row_approach(row, target, 16u, 1u, &rng);
        for (k = 0; k < 16u; k++) if (before[k] != (row[k].flags & SQ_STEP_ON)) { if (k % 4u == 0u) changed_beat = 1u; else changed_weak = 1u; }
        if (changed_beat && !changed_weak) { CHECK(beat_last); }
        if (prev != 255u) CHECK(left <= prev);
        prev = left;
        if (!left) break;
    }
    CHECK(left == 0u && presses < 17u);                         /* one step a press: at most 16 presses */
    for (i = 0; i < 16u; i++) if (i != 9u) CHECK((row[i].flags & SQ_STEP_ON) == (target[i].flags & SQ_STEP_ON) && (!(row[i].flags & SQ_STEP_ON) || row[i].velocity == target[i].velocity));
    CHECK(row[9].flags & SQ_STEP_LOCK);
    CHECK(row[5].lane[2] == 77u || !(target[5].flags & SQ_STEP_ON) ? 1 : 0);
    {   /* the order: a 16th changes before an "and", an "and" before a beat, the one last */
        static sq_step_t a[SQ_STEPS], b[SQ_STEPS];
        for (i = 0; i < 16u; i++) { sq_step_default(&a[i]); sq_step_default(&b[i]); b[i].flags = SQ_STEP_ON; b[i].note[0] = 60u; }
        CHECK(sq_row_approach(a, b, 16u, 8u, &rng) == 8u);
        for (i = 0; i < 16u; i++) CHECK(((a[i].flags & SQ_STEP_ON) != 0u) == (i % 2u == 1u));   /* the eight 16ths */
        CHECK(sq_row_approach(a, b, 16u, 4u, &rng) == 4u);
        for (i = 0; i < 16u; i += 4u) CHECK(!(a[i].flags & SQ_STEP_ON));
        CHECK(sq_row_approach(a, b, 16u, 3u, &rng) == 1u && !(a[0].flags & SQ_STEP_ON));       /* the one last */
        CHECK(sq_row_approach(a, b, 16u, 3u, &rng) == 0u && (a[0].flags & SQ_STEP_ON));
    }
    {   /* the lengths of a generated part: a PAD holds to the next chord, a STAB is short, a BASS long on the beat */
        static sq_step_t r[SQ_STEPS];
        uint32_t k, longb = 0u;
        for (i = 0; i < 16u; i++) sq_step_default(&r[i]);
        r[0].flags = r[8].flags = r[12].flags = SQ_STEP_ON;
        sq_row_phrase_gates(r, 16u, SQ_ROLE_PAD, 50u, &rng);
        CHECK(sq_gate_span(r[0].length) == 8u && sq_gate_span(r[8].length) == 4u && sq_gate_span(r[12].length) == 4u);
        sq_row_phrase_gates(r, 16u, SQ_ROLE_PAD, 50u, &rng);                                 /* again: kept */
        CHECK(sq_gate_span(r[0].length) == 8u);
        for (i = 0; i < 16u; i++) { sq_step_default(&r[i]); r[i].flags = (i % 4u == 0u) ? SQ_STEP_ON : 0u; }
        sq_row_phrase_gates(r, 16u, SQ_ROLE_STAB, 50u, &rng);
        for (i = 0; i < 16u; i += 4u) CHECK(r[i].length >= 20u && r[i].length < 50u);
        for (k = 0; k < 20u; k++) {
            for (i = 0; i < 16u; i++) { sq_step_default(&r[i]); r[i].flags = (i % 2u == 0u) ? SQ_STEP_ON : 0u; }
            sq_row_phrase_gates(r, 16u, SQ_ROLE_BASS, 80u, &rng);
            for (i = 0; i < 16u; i += 4u) if (sq_gate_span(r[i].length) >= 2u) longb++;
            for (i = 2u; i < 16u; i += 4u) CHECK(r[i].length <= 100u);                          /* between the beats: short */
        }
        CHECK(longb > 20u);
        sq_step_default(&r[0]); r[0].flags = SQ_STEP_ON | SQ_STEP_LOCK; r[0].length = 30u;
        sq_row_phrase_gates(r, 16u, SQ_ROLE_PAD, 50u, &rng);
        CHECK(r[0].length == 30u);                                                           /* a locked step is left */
        sq_row_phrase_gates(r, 16u, SQ_ROLE_KICK, 50u, &rng);                                /* a drum: nothing */
    }
}

/* 0.11: the HARMONY's rows of chords (lengths in 16ths, PUSH, the rhythms), any root and shape, the names, the moods */
static void test_v011_harmony(void)
{
    static const int8_t DEG[4] = {0, 6, 5, 6};                 /* i VII VI VII */
    static const uint8_t COL[4] = {0, 0, 0, 0};
    sq_hprog_t h;
    sq_hchord_t c;
    sq_uprog_t u;
    uint8_t notes[SQ_POLY_OUT], n, k, ext;
    uint32_t rng = 99u, i;
    char nm[16];
    /* BARS: a chord every bar (16 16ths), as 0.10 */
    sq_hprog_lib(&h, DEG, COL, 4u, 1u, SQ_HR_BARS);
    CHECK(h.n == 4u && sq_hprog_len(&h) == 64u && sq_hprog_at(&h, 0u, &c) == 0u && sq_hprog_at(&h, 15u, &c) == 0u && sq_hprog_at(&h, 16u, &c) == 1u && c.deg == 6);
    CHECK(sq_hprog_at(&h, 64u + 33u, &c) == 2u && c.semi == 255u);
    sq_hprog_lib(&h, DEG, COL, 4u, 2u, SQ_HR_BARS);
    CHECK(sq_hprog_len(&h) == 128u && sq_hprog_at(&h, 31u, &c) == 0u && sq_hprog_at(&h, 32u, &c) == 1u);
    /* PUSH: the chord a 16th early (the last 16th of a bar has the next bar's chord; the first comes before the round) */
    sq_hprog_lib(&h, DEG, COL, 4u, 1u, SQ_HR_PUSH16);
    CHECK(sq_hprog_at(&h, 14u, &c) == 0u && sq_hprog_at(&h, 15u, &c) == 1u && sq_hprog_at(&h, 63u, &c) == 0u && sq_hprog_at(&h, 62u, &c) == 3u);
    sq_hprog_lib(&h, DEG, COL, 4u, 1u, SQ_HR_PUSH8);
    CHECK(sq_hprog_at(&h, 13u, &c) == 0u && sq_hprog_at(&h, 14u, &c) == 1u);
    /* 3+3+2: 6, 6, 4 16ths, round the chords (a bar of three) */
    sq_hprog_lib(&h, DEG, COL, 4u, 1u, SQ_HR_332);
    CHECK(h.nc == 4u && h.n == 12u && h.dur[0] == 6u && h.dur[1] == 6u && h.dur[2] == 4u && h.dur[3] == 6u && sq_hprog_len(&h) == 64u);   /* 4 bars: the lengths and the chords come round together */
    CHECK(sq_hprog_at(&h, 5u, &c) == 0u && sq_hprog_at(&h, 6u, &c) == 1u && sq_hprog_at(&h, 12u, &c) == 2u && sq_hprog_at(&h, 16u, &c) == 3u);
    CHECK(sq_hprog_at(&h, 22u, &c) == 0u && sq_hprog_at(&h, 28u, &c) == 1u && sq_hprog_at(&h, 32u, &c) == 2u && sq_hprog_at(&h, 48u, &c) == 1u && c.deg == 6);
    {   uint32_t changes = 0u, p; uint8_t last = 255u;           /* every bar: the changes on 1, the 4th 8th... and the 7th */
        for (p = 0; p < 64u; p++) { uint8_t k2 = sq_hprog_at(&h, p, &c); if (k2 != last) { CHECK((p % 16u) == 0u || (p % 16u) == 6u || (p % 16u) == 12u); changes++; } last = k2; }
        CHECK(changes == 12u); }
    sq_hprog_lib(&h, DEG, COL, 3u, 1u, SQ_HR_332);
    CHECK(h.n == 3u && sq_hprog_len(&h) == 16u);
    sq_hprog_lib(&h, DEG, COL, 3u, 1u, SQ_HR_HALF);
    CHECK(h.n == 6u && h.nc == 3u && sq_hprog_len(&h) == 48u && sq_hprog_at(&h, 24u, &c) == 0u);
    for (k = 0; k < SQ_HRS; k++) CHECK(strlen(sq_hrhythm_name(k)) >= 3u);
    /* the player's: its own lengths and pushes win over the rhythm */
    sq_uprog_default(&u);
    u.n = 3u; u.semi[0] = 0u; u.shape[0] = SQ_HSHAPE_CH + SQ_CH_MIN7; u.semi[1] = 10u; u.shape[1] = SQ_HSHAPE_CH + SQ_CH_MAJ; u.semi[2] = 8u; u.shape[2] = SQ_HSHAPE_CH + SQ_CH_MAJ7;
    u.dur[0] = 12u; u.dur[1] = 4u; u.push[1] = 1u;
    sq_hprog_user(&h, &u, 0u, SQ_HR_BARS);
    CHECK(h.dur[0] == 12u && h.dur[1] == 4u && h.dur[2] == 16u && sq_hprog_len(&h) == 32u);
    CHECK(sq_hprog_at(&h, 10u, &c) == 0u && sq_hprog_at(&h, 11u, &c) == 1u && c.semi == 10u && sq_hprog_at(&h, 16u, &c) == 2u);
    /* the names: by the step as 0.10, a root and a shape: the flats, small for minor */
    sq_hprog_at(&h, 0u, &c); sq_hchord_name(SQ_SC_MINOR, &c, nm); CHECK(!strcmp(nm, "i7"));
    sq_hprog_at(&h, 12u, &c); sq_hchord_name(SQ_SC_MINOR, &c, nm); CHECK(!strcmp(nm, "bVII"));
    sq_hprog_at(&h, 16u, &c); sq_hchord_name(SQ_SC_MINOR, &c, nm); CHECK(!strcmp(nm, "bVImaj7"));
    {   sq_hchord_t x = {0, 0, 1u, SQ_HSHAPE_CH + SQ_CH_MAJ}; sq_hchord_name(SQ_SC_MINOR, &x, nm); CHECK(!strcmp(nm, "bII")); }
    {   sq_hchord_t x = {0, 0, 6u, SQ_HSHAPE_CH + SQ_CH_DIM}; sq_hchord_name(SQ_SC_MAJOR, &x, nm); CHECK(!strcmp(nm, "#ivo")); }
    {   sq_hchord_t x = {0, 0, 7u, SQ_HC_SUS4}; sq_hchord_name(SQ_SC_MAJOR, &x, nm); CHECK(!strcmp(nm, "Vsus4")); }   /* the key's own V, sus4 */
    {   sq_hchord_t x = {5, SQ_HC_7, 255u, 0}; sq_hchord_name(SQ_SC_MINOR, &x, nm); CHECK(!strcmp(nm, "VI7")); }
    sq_uprog_name(&u, SQ_SC_MINOR, nm, sizeof nm); CHECK(!strcmp(nm, "i7-bVII-bVImaj7"));
    /* the notes of a FOLLOW track: C minor, written on the tonic (C Eb G), to bVII (Bb D F), the nearest octave */
    {   sq_hchord_t x = {0, 0, 10u, SQ_HSHAPE_CH + SQ_CH_MAJ};
        notes[0] = 60u; notes[1] = 63u; notes[2] = 67u;
        n = sq_harm_apply_chord(notes, 3u, 0u, SQ_SC_MINOR, &x, 1u);
        CHECK(n == 3u && notes[0] == 58u && notes[1] == 62u && notes[2] == 65u);
        notes[0] = 48u; n = sq_harm_apply_chord(notes, 1u, 0u, SQ_SC_MINOR, &x, 0u);              /* a bass: the root */
        CHECK(n == 1u && notes[0] == 46u);
        x.semi = 1u; x.shape = SQ_HSHAPE_CH + SQ_CH_MAJ7;                                          /* bIImaj7: the 7th on top of a written chord */
        notes[0] = 60u; notes[1] = 63u; notes[2] = 67u;
        n = sq_harm_apply_chord(notes, 3u, 0u, SQ_SC_MINOR, &x, 1u);
        CHECK(n == 4u && notes[0] == 61u && notes[1] == 65u && notes[2] == 68u && notes[3] == 72u);
        x.semi = 5u; x.shape = SQ_HSHAPE_CH + SQ_CH_SUS4;                                          /* IVsus4: the third is the fourth */
        notes[0] = 60u; notes[1] = 63u; notes[2] = 67u;
        n = sq_harm_apply_chord(notes, 3u, 0u, SQ_SC_MINOR, &x, 1u);
        CHECK(n == 3u && notes[0] == 65u - 12u + 12u - 0u ? 1 : 0);
        CHECK(((notes[0] % 12u) == 5u) && ((notes[1] % 12u) == 10u) && ((notes[2] % 12u) == 0u));
        x.semi = 3u; x.shape = SQ_HC_7;                                                            /* the key's III with a 7th: as 0.10's step and colour */
        notes[0] = 60u; notes[1] = 63u; notes[2] = 67u;
        { uint8_t m[SQ_POLY_OUT] = {60u, 63u, 67u}; uint8_t k2 = sq_harm_apply(m, 3u, 0u, SQ_SC_MINOR, 2, SQ_HC_7, 1u);
          n = sq_harm_apply_chord(notes, 3u, 0u, SQ_SC_MINOR, &x, 1u); CHECK(n == k2 && !memcmp(notes, m, n)); }
    }
    /* qualities */
    {   sq_hchord_t x = {0, 0, 0u, SQ_HSHAPE_CH + SQ_CH_MIN9};
        CHECK(sq_hchord_quality(SQ_SC_MAJOR, &x, &ext) == 1u && (ext & 4u));
        x.shape = SQ_HSHAPE_CH + SQ_CH_SUS2; CHECK(sq_hchord_quality(SQ_SC_MAJOR, &x, &ext) == 4u);
        x.semi = 255u; x.deg = 6; x.col = 0; CHECK(sq_hchord_quality(SQ_SC_MAJOR, &x, &ext) == 2u);   /* vii in major: diminished */
        CHECK(sq_hchord_semi(SQ_SC_MAJOR, &x) == 11u && sq_hchord_semi(SQ_SC_MINOR, &x) == 10u);
    }
    /* explicit: a step of the key with a colour as a root and a shape (what goes to the Pi) */
    {   static const struct { uint8_t scale; int8_t deg; uint8_t col, semi, shape; } X[] = {
            {SQ_SC_MINOR, 0, SQ_HC_TRIAD, 0u, SQ_CH_MIN}, {SQ_SC_MINOR, 6, SQ_HC_TRIAD, 10u, SQ_CH_MAJ}, {SQ_SC_MINOR, 5, SQ_HC_7, 8u, SQ_CH_MAJ7},
            {SQ_SC_MAJOR, 4, SQ_HC_7, 7u, SQ_CH_7}, {SQ_SC_MAJOR, 1, SQ_HC_9, 2u, SQ_CH_MIN9}, {SQ_SC_MAJOR, 6, SQ_HC_TRIAD, 11u, SQ_CH_DIM},
            {SQ_SC_MAJOR, 6, SQ_HC_7, 11u, SQ_CH_M7B5}, {SQ_SC_MAJOR, 0, SQ_HC_SUS2, 0u, SQ_CH_SUS2}, {SQ_SC_MAJOR, 3, SQ_HC_6, 5u, SQ_CH_MAJ6},
            {SQ_SC_MAJOR, 0, SQ_HC_9, 0u, SQ_CH_MAJ9}, {SQ_SC_MINOR, 3, SQ_HC_SUS4, 5u, SQ_CH_SUS4} };
        for (i = 0; i < sizeof X / sizeof X[0]; i++) {
            sq_hchord_t x = {X[i].deg, X[i].col, 255u, 0u};
            uint8_t sm, sh;
            sq_hchord_explicit(X[i].scale, &x, &sm, &sh);
            CHECK(sm == X[i].semi && sh == SQ_HSHAPE_CH + X[i].shape);
            if (sm != X[i].semi || sh != SQ_HSHAPE_CH + X[i].shape) printf("  explicit %u: %u %u\n", (unsigned)i, (unsigned)sm, (unsigned)sh);
            x.semi = X[i].semi; x.shape = X[i].col;                   /* the same by its root, the key's chord there */
            sq_hchord_explicit(X[i].scale, &x, &sm, &sh);
            CHECK(sm == X[i].semi && sh == SQ_HSHAPE_CH + X[i].shape);
        }
        {   sq_hchord_t x = {0, 0, 1u, SQ_HC_7}; uint8_t sm, sh;        /* bII out of C minor with a 7: a dominant 7 */
            sq_hchord_explicit(SQ_SC_MINOR, &x, &sm, &sh); CHECK(sm == 1u && sh == SQ_HSHAPE_CH + SQ_CH_7);
            x.shape = SQ_HSHAPE_CH + SQ_CH_MIN11; sq_hchord_explicit(SQ_SC_MINOR, &x, &sm, &sh); CHECK(sh == SQ_HSHAPE_CH + SQ_CH_MIN11); }
    }
    /* the moods: what known progressions are */
    {   static const struct { uint8_t scale, n; uint8_t semi[4], shape[4]; uint8_t want; } M[] = {
            {SQ_SC_MAJOR, 4, {0, 7, 9, 5}, {SQ_CH_MAJ, SQ_CH_MAJ, SQ_CH_MIN, SQ_CH_MAJ}, SQ_MOOD_EUPHORIC},
            {SQ_SC_MINOR, 4, {0, 8, 10, 0}, {SQ_CH_MIN, SQ_CH_MAJ, SQ_CH_MAJ, SQ_CH_MIN}, SQ_MOOD_EPIC},
            {SQ_SC_MINOR, 2, {0, 1, 0, 0}, {SQ_CH_MIN, SQ_CH_MAJ, 0, 0}, SQ_MOOD_DARK},
            {SQ_SC_MAJOR, 2, {0, 5, 0, 0}, {SQ_CH_SUS2, SQ_CH_SUS2, 0, 0}, SQ_MOOD_SUSPENDED},
            {SQ_SC_MAJOR, 2, {0, 5, 0, 0}, {SQ_CH_MAJ7, SQ_CH_MAJ7, 0, 0}, SQ_MOOD_DREAMY},
            {SQ_SC_MINOR, 2, {0, 6, 0, 0}, {SQ_CH_MIN, SQ_CH_DIM, 0, 0}, SQ_MOOD_TENSE},
            {SQ_SC_MAJOR, 4, {2, 7, 0, 0}, {SQ_CH_MIN7, SQ_CH_7, SQ_CH_MAJ7, SQ_CH_MAJ7}, SQ_MOOD_SATISFYING},
            {SQ_SC_MINOR, 4, {0, 5, 8, 7}, {SQ_CH_MIN, SQ_CH_MIN, SQ_CH_MAJ, SQ_CH_MIN}, SQ_MOOD_SAD},
        };
        for (i = 0; i < sizeof M / sizeof M[0]; i++) {
            sq_uprog_default(&u);
            u.n = M[i].n;
            for (k = 0; k < u.n; k++) { u.semi[k] = M[i].semi[k]; u.shape[k] = (uint8_t)(SQ_HSHAPE_CH + M[i].shape[k]); }
            sq_hprog_user(&h, &u, 0u, SQ_HR_BARS);
            CHECK(sq_hprog_mood(&h, M[i].scale) == M[i].want);
            if (sq_hprog_mood(&h, M[i].scale) != M[i].want) printf("  mood %u: got %s want %s\n", (unsigned)i, sq_mood_name(sq_hprog_mood(&h, M[i].scale)), sq_mood_name(M[i].want));
        }
        for (k = 0; k < SQ_MOODS; k++) CHECK(strlen(sq_mood_name(k)) >= 3u && strlen(sq_mood_name(k)) <= 10u);
    }
    /* DICE PROG: a progression of the mood asked, 2 to 4 chords, roots and shapes in range; mostly that mood */
    {   uint32_t same = 0u, rolls = 0u, m;
        for (m = 1u; m < SQ_MOODS; m++) for (i = 0; i < 12u; i++) {
            sq_uprog_dice(&u, (uint8_t)m, 1u, SQ_HR_BARS, &rng);
            CHECK(u.mood == m && u.n >= 1u && u.n <= 5u);
            for (k = 0; k < u.n; k++) CHECK(u.semi[k] <= 11u && u.shape[k] > SQ_HSHAPE_CH && u.shape[k] < SQ_HSHAPES);
            sq_uprog_sanitize(&u);
            CHECK(u.mood == m);
            sq_hprog_user(&h, &u, 0u, SQ_HR_BARS);
            rolls++;
            if (sq_hprog_mood(&h, SQ_SC_MINOR) == m) same++;
        }
        CHECK(same * 2u >= rolls);                                /* what the machine guesses agrees, more often than not */
        sq_uprog_dice(&u, SQ_MOOD_ANY, 0u, SQ_HR_BARS, &rng);
        CHECK(u.mood >= SQ_MOOD_SAD && u.mood < SQ_MOODS);
    }
    /* sanitised: out of range back to what is safe */
    sq_uprog_default(&u); u.n = 2u; u.semi[0] = 40u; u.shape[1] = 200u; u.dur[0] = 99u; u.push[1] = 9u; u.mood = 77u;
    sq_uprog_sanitize(&u);
    CHECK(u.semi[0] == 255u && u.shape[1] == SQ_HC_TRIAD && u.dur[0] == 0u && u.push[1] == 0u && u.mood == SQ_MOOD_ANY);
    CHECK(sq_genre_hrhythm(SQ_GENRE_HOUSE) == SQ_HR_PUSH16 && sq_genre_hrhythm(SQ_GENRE_REGGAETON) == SQ_HR_332 && sq_genre_hrhythm(SQ_GENRE_TECHNO) == SQ_HR_BARS);
}

static void test_v010(void)
{
    sq_track_cfg_t c;
    sq_track_rt_t rt;
    uint8_t out[8], bits[64], n, k, i;
    static sq_step_t row[SQ_STEPS], row2[SQ_STEPS];
    uint32_t rng = 123u, hits, j;

    /* the conditions: thirds, eighths, FIRST, PRE */
    CHECK(sq_condition_pass(SQ_COND_1_3, 0u, 0u, 0u) && !sq_condition_pass(SQ_COND_1_3, 1u, 0u, 0u) && sq_condition_pass(SQ_COND_1_3, 3u, 0u, 0u));
    CHECK(sq_condition_pass(SQ_COND_2_3, 1u, 0u, 0u) && sq_condition_pass(SQ_COND_3_3, 5u, 0u, 0u) && !sq_condition_pass(SQ_COND_3_3, 4u, 0u, 0u));
    CHECK(sq_condition_pass(SQ_COND_1_8, 8u, 0u, 0u) && !sq_condition_pass(SQ_COND_1_8, 4u, 0u, 0u));
    CHECK(sq_condition_pass(SQ_COND_FIRST, 0u, 0u, 0u) && !sq_condition_pass(SQ_COND_FIRST, 1u, 0u, 0u));
    CHECK(sq_condition_pass(SQ_COND_PRE, 0u, 0u, 1u) && !sq_condition_pass(SQ_COND_PRE, 0u, 0u, 0u) && sq_condition_pass(SQ_COND_NOT_PRE, 0u, 0u, 0u));
    CHECK(!strcmp(sq_cond_name(SQ_COND_PRE), "PRE") && !strcmp(sq_cond_name(SQ_COND_1_3), "1:3") && !strcmp(sq_cond_name(99u), "ALL"));
    CHECK(SQ_COND_COUNT == 16u);

    /* the closed form of the loop: where the counters would be */
    sq_track_default(&c, 0u);
    c.length = 16u; c.division = SQ_DIV_1_16;
    memset(&rt, 0, sizeof rt);
    sq_track_seek(&c, &rt, 0u, 6u);
    CHECK(rt.step == 0u && rt.div_accum == 5u && rt.loop_count == 0u);        /* the first tick plays step 1 */
    sq_track_seek(&c, &rt, 1u, 6u);
    CHECK(rt.step == 1u && rt.div_accum == 0u);                                /* one tick in: step 1 has begun, step 2 next */
    sq_track_seek(&c, &rt, 96u, 6u);
    CHECK(rt.step == 0u && rt.div_accum == 5u && rt.loop_count == 1u);        /* a bar: back on the first step, a loop counted */
    sq_track_seek(&c, &rt, 96u + 7u, 6u);
    CHECK(rt.step == 2u && rt.div_accum == 0u);
    {   /* the counters agree with the closed form at every tick of 3 bars (a 12-step loop, start 2, ping-pong, a note loop) */
        sq_track_rt_t a, b;
        uint32_t rng2 = 1u;
        c.length = 12u; c.start = 2u; c.direction = SQ_DIR_PINGPONG; c.plen[SQ_PL_NOTE] = 5u;
        memset(&a, 0, sizeof a);
        a.step = c.start; a.div_accum = 5u; a.ping_dir = 1;
        for (j = 0; j < 288u; j++) {
            a.div_accum++;
            if (a.div_accum >= 6u) { a.div_accum = (uint16_t)(a.div_accum - 6u); sq_advance_step(&c, &a, &rng2); }
            memset(&b, 0, sizeof b);
            sq_track_seek(&c, &b, j + 1u, 6u);
            CHECK(a.step == b.step && a.div_accum == b.div_accum && a.ppos[0] == b.ppos[0] && a.ping_dir == b.ping_dir);
        }
        c.direction = SQ_DIR_FWD; c.plen[SQ_PL_NOTE] = 0u;
        memset(&a, 0, sizeof a);
        a.step = c.start; a.div_accum = 5u;
        for (j = 0; j < 288u; j++) {
            a.div_accum++;
            if (a.div_accum >= 6u) { a.div_accum = (uint16_t)(a.div_accum - 6u); sq_advance_step(&c, &a, &rng2); }
            memset(&b, 0, sizeof b);
            sq_track_seek(&c, &b, j + 1u, 6u);
            CHECK(a.step == b.step && a.div_accum == b.div_accum && a.loop_count == b.loop_count);
        }
        c.direction = SQ_DIR_RANDOM;
        b.step = 7u; sq_track_seek(&c, &b, 50u, 6u);
        CHECK(b.step == 7u);                                                  /* RANDOM keeps its step */
        b.step = 0u; sq_track_seek(&c, &b, 50u, 6u);
        CHECK(b.step == 2u);                                                  /* ... inside the loop */
        c.direction = SQ_DIR_FWD; c.start = 0u; c.length = 16u;
    }

    /* the track's note: octave, transpose in steps of the scale when IN KEY, semitones when FREE */
    sq_track_default(&c, 0u);
    c.octave = 1; c.transpose = 2;
    CHECK(sq_track_note(&c, 60, 0u, SQ_SC_MAJOR, 0) == 74u);                 /* FREE: +12 +2 */
    c.flags = SQ_TF_SCALE;
    CHECK(sq_track_note(&c, 60, 0u, SQ_SC_MAJOR, 0) == 76u);                 /* IN KEY: +12, two steps of C major: E */
    c.transpose = -1;
    CHECK(sq_track_note(&c, 60, 0u, SQ_SC_MAJOR, 0) == 71u);                 /* one step down from C5: B4 */
    c.transpose = 0; c.octave = 0;
    CHECK(sq_track_note(&c, 61, 0u, SQ_SC_MAJOR, 0) == 60u && sq_track_note(&c, 61, 0u, SQ_SC_MAJOR, 2) == 62u);   /* the shift, then snapped (63 -> D) */

    /* the chord shapes: DIATONIC (steps of the scale), FREE (the exact intervals), STRICT (the intervals, out of key silent) */
    n = sq_chord_build(60u, SQ_CH_MAJ, SQ_CK_DIATONIC, 0u, SQ_SC_MAJOR, out);
    CHECK(n == 3u && out[0] == 60u && out[1] == 64u && out[2] == 67u);      /* C major */
    n = sq_chord_build(62u, SQ_CH_MAJ, SQ_CK_DIATONIC, 0u, SQ_SC_MAJOR, out);
    CHECK(n == 3u && out[0] == 62u && out[1] == 65u && out[2] == 69u);      /* D minor: the scale decides (MAJOR and MINOR alike) */
    n = sq_chord_build(62u, SQ_CH_MIN, SQ_CK_DIATONIC, 0u, SQ_SC_MAJOR, out);
    CHECK(n == 3u && out[1] == 65u && out[2] == 69u);
    n = sq_chord_build(60u, SQ_CH_7, SQ_CK_DIATONIC, 9u, SQ_SC_MINOR, out);
    CHECK(n == 4u && out[0] == 60u && out[1] == 64u && out[2] == 67u && out[3] == 71u);   /* in A minor C is major: Cmaj7 */
    n = sq_chord_build(60u, SQ_CH_POWER, SQ_CK_DIATONIC, 11u, SQ_SC_MAJOR, out);
    CHECK(n == 2u && out[1] == 67u);                                          /* POWER is always a fifth (B major's VII is diminished) */
    n = sq_chord_build(62u, SQ_CH_MAJ, SQ_CK_FREE, 0u, SQ_SC_MAJOR, out);
    CHECK(n == 3u && out[1] == 66u && out[2] == 69u);                         /* FREE: D major in C major (F# out of the key, kept) */
    n = sq_chord_build(62u, SQ_CH_MAJ, SQ_CK_STRICT, 0u, SQ_SC_MAJOR, out);
    CHECK(n == 2u && out[0] == 62u && out[1] == 69u);                         /* STRICT: the F# is silent, D and A play */
    n = sq_chord_build(62u, SQ_CH_MIN7, SQ_CK_STRICT, 0u, SQ_SC_MAJOR, out);
    CHECK(n == 4u && out[1] == 65u && out[2] == 69u && out[3] == 72u);      /* Dm7 is all in C major: nothing silent */
    n = sq_chord_build(60u, SQ_CH_MAJ, SQ_CK_FREE, 0u, SQ_SC_MAJOR, out);
    CHECK(n == 3u && out[1] == 64u && out[2] == 67u);
    n = sq_chord_build(60u, SQ_CH_SUS4, SQ_CK_FREE, 0u, SQ_SC_MAJOR, out);
    CHECK(n == 3u && out[1] == 65u && out[2] == 67u);
    n = sq_chord_build(61u, SQ_CH_MAJ, SQ_CK_DIATONIC, 0u, SQ_SC_MAJOR, out);
    CHECK(n == 3u && out[0] == 61u && out[1] == 65u && out[2] == 68u);      /* a note outside the scale keeps its distance */
    n = sq_chord_build(60u, SQ_CH_OFF, SQ_CK_DIATONIC, 0u, SQ_SC_MAJOR, out);
    CHECK(n == 1u && out[0] == 60u);
    n = sq_chord_build(126u, SQ_CH_9, SQ_CK_FREE, 0u, SQ_SC_MAJOR, out);
    CHECK(n >= 1u && out[0] == 126u);                                         /* at the top: what fits */
    /* the big ones: five and six notes */
    n = sq_chord_build(60u, SQ_CH_MIN9, SQ_CK_FREE, 0u, SQ_SC_MAJOR, out);
    CHECK(n == 5u && out[1] == 63u && out[2] == 67u && out[3] == 70u && out[4] == 74u);   /* Cm9 */
    n = sq_chord_build(60u, SQ_CH_9SUS4, SQ_CK_FREE, 0u, SQ_SC_MAJOR, out);
    CHECK(n == 5u && out[1] == 65u && out[2] == 67u && out[3] == 70u && out[4] == 74u);   /* C9sus4: the garage chord */
    n = sq_chord_build(60u, SQ_CH_MIN11, SQ_CK_FREE, 0u, SQ_SC_MAJOR, out);
    CHECK(n == 6u && out[5] == 77u);                                          /* Cm11: six notes */
    n = sq_chord_build(60u, SQ_CH_13, SQ_CK_FREE, 0u, SQ_SC_MAJOR, out);
    CHECK(n == 6u && out[5] == 81u);                                          /* C13 */
    n = sq_chord_build(62u, SQ_CH_MIN9, SQ_CK_DIATONIC, 0u, SQ_SC_MAJOR, out);
    CHECK(n == 5u && out[1] == 65u && out[2] == 69u && out[3] == 72u && out[4] == 76u);   /* Dm9 on the scale */
    n = sq_chord_build(60u, SQ_CH_13, SQ_CK_DIATONIC, 0u, SQ_SC_MAJOR, out);
    CHECK(n == 6u && out[3] == 70u + 1u && out[5] == 81u);                    /* Cmaj13 in C major: B, not Bb */
    n = sq_chord_build(60u, SQ_CH_MIN9, SQ_CK_FREE, 0u, SQ_SC_CHROMATIC, out);
    CHECK(n == 5u && out[1] == 63u);                                          /* no key: always the intervals */
    n = sq_chord_build(60u, SQ_CH_MIN9, SQ_CK_DIATONIC, 0u, SQ_SC_CHROMATIC, out);
    CHECK(n == 5u && out[1] == 63u);
    {   /* every shape: the written note first, ascending, no doubles, at most six */
        uint8_t sh, ck, i;
        for (sh = 0; sh < SQ_CH_COUNT; sh++) for (ck = 0; ck < SQ_CK_COUNT; ck++) {
            n = sq_chord_build(57u, sh, ck, 9u, SQ_SC_MINOR, out);
            CHECK(n >= 1u && n <= SQ_POLY_OUT && out[0] == 57u);
            for (i = 1; i < n; i++) CHECK(out[i] > out[i - 1u]);
            CHECK(strlen(sq_chord_shape_name(sh)) <= 8u);
        }
    }
    CHECK(!strcmp(sq_chord_shape_name(SQ_CH_SUS2), "SUS2") && !strcmp(sq_chord_shape_name(99u), "OFF") && !strcmp(sq_chord_shape_name(SQ_CH_9SUS4), "9SUS4"));
    CHECK(!strcmp(sq_chord_key_name(SQ_CK_STRICT), "STRICT") && !strcmp(sq_chord_key_name(9u), "DIATONIC"));
    CHECK(!strcmp(sq_role_name(SQ_ROLE_HAT), "HAT") && !strcmp(sq_role_name(99u), "NONE"));

    /* the rhythm families */
    sq_rhythm(SQ_RF_TRESILLO, 8u, 16u, 0u, bits);
    CHECK(bits[0] && bits[3] && bits[6] && bits[8] && bits[11] && bits[14] && !bits[1] && !bits[7]);   /* 3 3 2, twice */
    sq_rhythm(SQ_RF_TRESILLO, 2u, 16u, 0u, bits);
    CHECK(bits[0] && bits[3] && !bits[6] && !bits[8]);                        /* two pulses kept */
    sq_rhythm(SQ_RF_TRESILLO, 8u, 16u, 1u, bits);
    CHECK(bits[1] && bits[4] && !bits[0]);                                    /* turned */
    sq_rhythm(SQ_RF_TRESILLO, 3u, 8u, 0u, bits);
    CHECK(bits[0] && bits[3] && bits[6] && !bits[7]);
    sq_rhythm(SQ_RF_NUMERIC, 1u, 16u, 0u, bits);                              /* the first prime, 2 = 10b: every other step */
    for (hits = 0u, i = 0; i < 16u; i++) hits += bits[i];
    CHECK(hits == 8u && !bits[0] && bits[1]);
    sq_rhythm(SQ_RF_NUMERIC, 5u, 16u, 0u, bits);                              /* 11 = 1011b: 1 1 0 1 repeated */
    CHECK(bits[0] && bits[1] && !bits[2] && bits[3] && bits[4] && bits[5] && !bits[6]);
    for (k = 1; k <= 64u; k++) { sq_rhythm(SQ_RF_NUMERIC, k, 16u, 3u, bits); for (hits = 0u, i = 0; i < 16u; i++) hits += bits[i]; CHECK(hits >= 1u); }
    CHECK(sq_rhythm_hit(SQ_RF_TRESILLO, 8u, 16u, 0u, 3u) == 1u && sq_rhythm_hit(SQ_RF_TRESILLO, 8u, 16u, 0u, 4u) == 0u && sq_rhythm_hit(SQ_RF_EUCLID, 4u, 16u, 0u, 4u) == 1u);
    CHECK(!strcmp(sq_rhythm_name(SQ_RF_NUMERIC), "NUMERIC") && !strcmp(sq_rhythm_name(9u), "EUCLID"));
    for (i = 0; i < SQ_STEPS; i++) sq_step_default(&row[i]);
    sq_row_rhythm(row, 16u, SQ_RF_TRESILLO, 8u, 0u);
    CHECK((row[0].flags & SQ_STEP_ON) && (row[3].flags & SQ_STEP_ON) && !(row[1].flags & SQ_STEP_ON) && (row[0].flags & SQ_STEP_SET));

    /* COOK by role: the kick keeps its beats, the snare its backbeat, a bass its root on the beats; NONE is the old cook */
    for (i = 0; i < SQ_STEPS; i++) sq_step_default(&row[i]);
    for (i = 0; i < 16u; i += 4u) { row[i].flags = SQ_STEP_ON | SQ_STEP_SET; row[i].note[0] = 36u; }
    for (j = 0; j < 20u; j++) sq_row_cook_role(row, 16u, 100u, SQ_ROLE_KICK, 0u, SQ_SC_MINOR, &rng);
    CHECK((row[0].flags & SQ_STEP_ON) && (row[4].flags & SQ_STEP_ON) && (row[8].flags & SQ_STEP_ON) && (row[12].flags & SQ_STEP_ON));
    for (hits = 0u, i = 0; i < 16u; i++) hits += (row[i].flags & SQ_STEP_ON) ? 1u : 0u;
    CHECK(hits >= 4u && hits <= 12u);
    for (i = 0; i < SQ_STEPS; i++) sq_step_default(&row[i]);
    row[4].flags = row[12].flags = SQ_STEP_ON | SQ_STEP_SET;
    for (j = 0; j < 20u; j++) sq_row_cook_role(row, 16u, 100u, SQ_ROLE_SNARE, 0u, SQ_SC_MINOR, &rng);
    CHECK((row[4].flags & SQ_STEP_ON) && (row[12].flags & SQ_STEP_ON) && row[4].velocity >= 90u);
    for (i = 0; i < SQ_STEPS; i++) sq_step_default(&row[i]);
    for (i = 0; i < 16u; i += 2u) { row[i].flags = SQ_STEP_ON | SQ_STEP_SET; row[i].note[0] = (uint8_t)(36u + (i % 3u) * 2u); }
    for (j = 0; j < 30u; j++) sq_row_cook_role(row, 16u, 100u, SQ_ROLE_BASS, 0u, SQ_SC_MINOR, &rng);
    for (hits = 0u, i = 0; i < 16u; i += 4u) if ((row[i].flags & SQ_STEP_ON) && row[i].note[0] == 36u) hits++;
    CHECK(hits >= 2u);                                                        /* the root holds most of the beats */
    for (i = 0; i < 16u; i++) CHECK(row[i].note[0] >= 24u && row[i].note[0] <= 60u);
    for (i = 0; i < SQ_STEPS; i++) { sq_step_default(&row[i]); sq_step_default(&row2[i]); }
    row[0].flags = row[4].flags = SQ_STEP_ON | SQ_STEP_SET; row2[0].flags = row2[4].flags = SQ_STEP_ON | SQ_STEP_SET;
    row[2].flags = SQ_STEP_ON | SQ_STEP_SET | SQ_STEP_LOCK; row[2].velocity = 33u;
    for (j = 0; j < 10u; j++) sq_row_cook_role(row, 16u, 90u, SQ_ROLE_HAT, 0u, SQ_SC_MINOR, &rng);
    CHECK((row[2].flags & SQ_STEP_ON) && row[2].velocity == 33u && row[2].ratchet == 1u);   /* a LOCKed step is left alone */
    { uint32_t r1 = 5u, r2 = 5u; sq_row_cook_role(row2, 16u, 60u, SQ_ROLE_NONE, 0u, SQ_SC_MINOR, &r1); for (i = 0; i < SQ_STEPS; i++) sq_step_default(&row[i]); row[0].flags = row[4].flags = SQ_STEP_ON | SQ_STEP_SET; sq_row_cook(row, 16u, 60u, &r2); CHECK(!memcmp(row, row2, sizeof row)); }

    /* the player's progressions */
    {
        sq_uprog_t u;
        int8_t d; uint8_t col; char nm[40];
        sq_uprog_default(&u);
        CHECK(u.n == 0u && sq_uprog_at(&u, 5u, 0u, &d, &col) == 0u && d == 0 && col == SQ_HC_TRIAD);
        sq_uprog_name(&u, SQ_SC_MINOR, nm, sizeof nm);
        CHECK(!strcmp(nm, "--"));
        u.n = 3u; u.bars = 2u; u.deg[0] = 0; u.deg[1] = 5; u.col[1] = SQ_HC_7; u.deg[2] = 3;
        CHECK(sq_uprog_at(&u, 0u, 0u, &d, &col) == 0u && d == 0 && sq_uprog_at(&u, 2u, 0u, &d, &col) == 1u && d == 5 && col == SQ_HC_7);
        CHECK(sq_uprog_at(&u, 4u, 0u, &d, &col) == 2u && d == 3 && sq_uprog_at(&u, 6u, 0u, &d, &col) == 0u);
        CHECK(sq_uprog_at(&u, 1u, 1u, &d, &col) == 1u);                       /* a bar a chord when overridden */
        sq_uprog_name(&u, SQ_SC_MINOR, nm, sizeof nm);
        CHECK(!strcmp(nm, "i-VI7-iv"));
        u.n = 9u; u.deg[0] = 9; u.col[0] = 9u; u.bars = 0u;
        sq_uprog_sanitize(&u);
        CHECK(u.n == 0u && u.deg[0] == 0 && u.col[0] == SQ_HC_TRIAD && u.bars == 1u);
    }

    /* the synths' CC names */
    CHECK(!strcmp(sq_cc_name(SQ_DEV_GENERIC, 74u), "CUTOFF") && !strcmp(sq_cc_name(SQ_DEV_GENERIC, 1u), "MOD") && !strcmp(sq_cc_name(SQ_DEV_GENERIC, 3u), ""));
    CHECK(!strcmp(sq_cc_name(SQ_DEV_ELEKTRON, 74u), "FLT FREQ") && !strcmp(sq_cc_name(SQ_DEV_ELEKTRON, 95u), "LEVEL") && !strcmp(sq_cc_name(SQ_DEV_GENERIC, SQ_CC_BEND), "BEND"));
    CHECK(!strcmp(sq_device_name(SQ_DEV_ELEKTRON), "ELEKTRON") && !strcmp(sq_device_name(9u), "GENERIC"));
    for (k = 0; k < SQ_DEV_COUNT; k++) for (i = 0; i <= SQ_CC_MAX; i++) CHECK(strlen(sq_cc_name(k, i)) <= 8u);

    /* the set genres cover the library, one each, in its order */
    for (k = 0; k < SQ_SET_GENRES; k++) CHECK(sq_set_genre(k)->genre == k && sq_set_genre(k)->genre2 < SQ_SET_GENRES && strlen(sq_set_genre(k)->name) <= 10u);
}

/* 0.12 BREAK: the chops, the slices on consecutive notes, the dice's backbone, half / double / backwards */
static void test_v012_break(void)
{
    sq_step_t row[SQ_STEPS];
    uint32_t i, k, rng = 7u;
    for (i = 0; i < SQ_STEPS; i++) sq_step_default(&row[i]);
    /* the library */
    CHECK(SQ_BRK_CHOPS == 16u && !strcmp(sq_brk_chop(0)->name, "STRAIGHT") && sq_brk_chop(99)->name == sq_brk_chop(0)->name);   /* one a white key */
    CHECK(!strcmp(sq_brk_chop(10)->name, "SHUFFLE") && !strcmp(sq_brk_chop(15)->name, "BUILD") && !strcmp(sq_brk_chop(5)->name, "HALF"));
    for (k = 0; k < SQ_BRK_CHOPS; k++) {
        const sq_brk_chop_t *c = sq_brk_chop((uint8_t)k);
        CHECK(strlen(c->name) <= 9u && (c->gate == 100u || c->gate == 102u));
        for (i = 0; i < 16u; i++) CHECK(c->sl[i] <= 16u);
        CHECK(c->sl[0] == 1u || k == 6u || k == 9u);                            /* the one is the kick (not BACKWARDS, not HIGH) */
    }
    for (i = 0; i < 16u; i++) CHECK(sq_brk_chop(0)->sl[i] == i + 1u);
    /* the genres' chops: every genre has some, all of the library, none twice; JUNGLE walks STRAIGHT, THINK, APACHE ... */
    for (k = 0; k < 24u; k++) {
        uint8_t n = sq_brk_genre_chops((uint8_t)k), j;
        CHECK(n >= 3u && n <= 7u);
        for (i = 0; i < n; i++) {
            CHECK(sq_brk_genre_chop((uint8_t)k, (uint8_t)i) < SQ_BRK_CHOPS);
            for (j = 0; j < i; j++) CHECK(sq_brk_genre_chop((uint8_t)k, j) != sq_brk_genre_chop((uint8_t)k, (uint8_t)i));
        }
        CHECK(sq_brk_genre_chop((uint8_t)k, n) == sq_brk_genre_chop((uint8_t)k, 0u));   /* (past the end: the first) */
    }
    CHECK(sq_brk_genre_chops(8u) == 7u && sq_brk_genre_chop(8u, 0u) == 0u && sq_brk_genre_chop(8u, 1u) == 11u && sq_brk_genre_chop(8u, 2u) == 12u);
    CHECK(sq_brk_genre_chops(99u) == sq_brk_genre_chops(0u));
    /* STRAIGHT over a bar from pen 36: notes 36..51, one a step, accents on the beats */
    sq_brk_apply(row, 0u, 16u, 0u, 36u, 16u);
    for (i = 0; i < 16u; i++) {
        CHECK((row[i].flags & SQ_STEP_ON) && row[i].note[0] == 36u + i && row[i].note[1] == SQ_NOTE_NONE && row[i].length == 100u);
        CHECK(row[i].velocity == ((i & 3u) == 0u ? 115u : 95u) && row[i].ratchet == 1u);
        CHECK(sq_brk_slice_of(&row[i], 36u, 16u) == i + 1u);
    }
    CHECK(sq_brk_slice_of(&row[0], 40u, 16u) == 0u && sq_brk_slice_of(&row[15], 36u, 8u) == 0u);   /* outside the break: no slice */
    /* 8 slices: slice 9 wraps to the first note; END ROLL: the last two steps roll */
    sq_brk_step(row, 3u, 9u, 36u, 8u, 100u, 100u);
    CHECK(row[3].note[0] == 36u);
    sq_brk_apply(row, 0u, 16u, 1u, 36u, 16u);
    CHECK(row[14].ratchet == 2u && row[15].ratchet == 2u && row[13].ratchet == 1u && row[15].note[0] == 36u + 14u);
    /* HALF: every slice held two steps (1 . 2 . 3 .); DOUBLE: every other slice twice over; BACKWARDS: reversed */
    sq_brk_apply(row, 0u, 16u, 0u, 36u, 16u);
    sq_brk_half(row, 0u, 16u, 36u, 16u);
    for (i = 0; i < 16u; i++) {
        if (i & 1u) CHECK(!(row[i].flags & SQ_STEP_ON));
        else CHECK(sq_brk_slice_of(&row[i], 36u, 16u) == i / 2u + 1u && row[i].length == 102u);
    }
    CHECK(row[0].velocity == 115u && row[2].velocity == 95u && row[8].velocity == 115u);   /* (the velocities of the slices they came from) */
    sq_brk_apply(row, 0u, 16u, 0u, 36u, 16u);
    sq_brk_double(row, 0u, 16u, 36u, 16u);
    for (i = 0; i < 16u; i++) CHECK(sq_brk_slice_of(&row[i], 36u, 16u) == (2u * i) % 16u + 1u);
    sq_brk_apply(row, 0u, 16u, 0u, 36u, 16u);
    sq_brk_backwards(row, 0u, 16u);
    for (i = 0; i < 16u; i++) CHECK(sq_brk_slice_of(&row[i], 36u, 16u) == 16u - i);
    /* the dice: no swap, no roll: the backbone (1 5 1 5 on the beats), the rest as it was; a rest gets its own slice */
    sq_brk_apply(row, 0u, 16u, 6u, 36u, 16u);                                   /* BACKWARDS: 16 .. 1 */
    row[6].flags &= (uint8_t)~SQ_STEP_ON;
    sq_brk_dice(row, 0u, 16u, 36u, 16u, 0u, 0u, 50u, &rng);
    CHECK(sq_brk_slice_of(&row[0], 36u, 16u) == 1u && sq_brk_slice_of(&row[4], 36u, 16u) == 5u && sq_brk_slice_of(&row[8], 36u, 16u) == 1u && sq_brk_slice_of(&row[12], 36u, 16u) == 5u);
    CHECK(sq_brk_slice_of(&row[1], 36u, 16u) == 15u && sq_brk_slice_of(&row[6], 36u, 16u) == 7u && row[0].velocity == 115u);
    for (i = 0; i < 16u; i++) CHECK(row[i].ratchet == 1u);
    /* roll 2: the steps before the three and the one roll (16 and 8 of the bar) */
    sq_brk_dice(row, 0u, 16u, 36u, 16u, 0u, 2u, 50u, &rng);
    CHECK(row[15].ratchet >= 2u && row[7].ratchet >= 2u && row[11].ratchet == 1u);
    /* swap 7, heat 100: the backbone stays whatever the dice does; every step either a slice or a rest; 32 steps: two bars */
    for (k = 0; k < 20u; k++) {
        sq_brk_dice(row, 0u, 32u, 36u, 16u, 7u, 7u, 100u, &rng);
        for (i = 0; i < 32u; i++) {
            uint8_t sl = sq_brk_slice_of(&row[i], 36u, 16u);
            if ((i & 3u) == 0u) CHECK(sl == ((i & 15u) == 0u || (i & 15u) == 8u ? 1u : 5u));
            else CHECK(sl <= 16u && (sl || !(row[i].flags & SQ_STEP_ON)));
        }
    }
    /* the settings are packed with a bias: a 0.11 image's zero means the default; a lock keeps a step through a chop */
    CHECK(SQ_BRK_PACK(0u, 0u, 0u) == 1u && SQ_BRK_SL(SQ_BRK_PACK(0u, 0u, 0u)) == 0u && SQ_BRK_ROLL(SQ_BRK_PACK(2u, 5u, 7u)) == 5u && SQ_BRK_SWAP(SQ_BRK_PACK(2u, 5u, 7u)) == 7u && SQ_BRK_SL(SQ_BRK_PACK(2u, 5u, 7u)) == 2u);
    {
        static sq_project_t pz;
        sq_project_init(&pz);
        pz.track[0].brk_cfg = 0u; pz.track[1].brk_cfg = SQ_BRK_PACK(0u, 0u, 0u);
        sq_project_sanitize(&pz);
        CHECK(pz.track[0].brk_cfg == SQ_BRK_DEFAULT && pz.track[1].brk_cfg == SQ_BRK_PACK(0u, 0u, 0u));
    }
    for (i = 0; i < SQ_STEPS; i++) sq_step_default(&row[i]);
    sq_brk_apply(row, 0u, 16u, 0u, 36u, 16u);
    row[3].flags |= SQ_STEP_LOCK;
    sq_brk_apply(row, 0u, 16u, 6u, 36u, 16u);                                   /* BACKWARDS: 16 .. 1, but step 4 keeps slice 4 */
    CHECK(sq_brk_slice_of(&row[3], 36u, 16u) == 4u && sq_brk_slice_of(&row[0], 36u, 16u) == 16u);
    sq_brk_dice(row, 0u, 16u, 36u, 16u, 7u, 7u, 100u, &rng);
    CHECK(sq_brk_slice_of(&row[3], 36u, 16u) == 4u && row[3].ratchet == 1u);
    sq_brk_half(row, 0u, 16u, 36u, 16u); CHECK(sq_brk_slice_of(&row[3], 36u, 16u) == 4u);
    sq_brk_double(row, 0u, 16u, 36u, 16u); CHECK(sq_brk_slice_of(&row[3], 36u, 16u) == 4u);
    sq_brk_backwards(row, 0u, 16u); CHECK(sq_brk_slice_of(&row[3], 36u, 16u) == 4u);
    /* a loop that starts late: the chop counts its bar from the loop's first step */
    for (i = 0; i < SQ_STEPS; i++) sq_step_default(&row[i]);
    sq_brk_apply(row, 4u, 20u, 0u, 60u, 16u);
    CHECK(!(row[3].flags & SQ_STEP_ON) && sq_brk_slice_of(&row[4], 60u, 16u) == 1u && sq_brk_slice_of(&row[19], 60u, 16u) == 16u && !(row[20].flags & SQ_STEP_ON));
}

static void test_v013_ext(void)
{
    static sq_project_t a, b;
    static uint8_t img[0x8000];
    uint32_t n, n0, i;
    sq_lfo_t l;
    sq_lfox_t x;
    sq_trackx_t c;
    uint8_t pos, left, seen[8];
    /* the defaults: no RATE SEQ, no trigger, chains of one, no motion, the keyboard off */
    sq_project_init(&a);
    CHECK(a.ext.lfo[3].seq_n == 0u && a.ext.lfo[3].seq_rate[5] == SQ_RSEQ_OWN && a.ext.lfo[3].trig == 0u);
    CHECK(a.ext.track[2].chain_on == 0u && a.ext.track[2].chain_n == 1u && a.ext.track[2].chain_rep[7] == 1u);
    CHECK(a.ext.motion[3][63] == SQ_MOTION_NONE && a.ext.motion_bars == 0u && a.ext.kb_mode == SQ_KB_OFF && a.ext.in_thru == 0u);
    /* an image of defaults has no chunk: as 0.12 wrote it (the end mark right after the tapes) */
    n0 = sq_serialize(&a, img, sizeof img);
    CHECK(n0 > 0u && img[n0 - 1u] == 0u && img[n0 - 3u] == 0u && img[n0 - 2u] == 0u);   /* (no events: 2 zero bytes, then the end) */
    /* set them, save, load: all back */
    a.ext.lfo[1].seq_n = 4u; a.ext.lfo[1].seq_every = SQ_RE_BAR; a.ext.lfo[1].seq_rate[0] = 10u; a.ext.lfo[1].seq_rate[2] = 17u;
    a.ext.lfo[5].trig = 1u;
    a.ext.track[0].chain_on = 1u; a.ext.track[0].chain_n = 4u;
    a.ext.track[0].chain_pat[0] = 0u; a.ext.track[0].chain_pat[1] = 0u; a.ext.track[0].chain_pat[2] = 1u; a.ext.track[0].chain_pat[3] = 0u;
    a.ext.track[0].chain_rep[2] = 2u;
    a.ext.motion_bars = 2u; a.ext.motion[3][5] = -40; a.ext.motion[0][31] = 63;
    a.ext.kb_mode = SQ_KB_SPLIT; a.ext.kb_ch = 2u; a.ext.in_thru = 1u;
    a.step[0][0][3].flags |= SQ_STEP_ON | SQ_STEP_SLIDE;
    n = sq_serialize(&a, img, sizeof img);
    CHECK(n == n0 + 3u + (uint32_t)sizeof a.ext + 18u - 15u || n > n0 + (uint32_t)sizeof a.ext);   /* (the chunk: tag, length, its bytes; and the step) */
    CHECK(sq_image_ok(img, n) == 0);
    CHECK(sq_deserialize(&b, img, n) == 0);
    CHECK(!memcmp(&a.ext, &b.ext, sizeof a.ext));
    CHECK(b.step[0][0][3].flags & SQ_STEP_SLIDE);
    /* a chunk this firmware does not know (tag 2) and a longer chunk 1 (from a later one): skipped, read as far as known */
    {
        static uint8_t big[0x8000];
        uint32_t m = n - 1u, k;                       /* (n - 1: the end mark) */
        uint32_t at1 = m - 3u - (uint32_t)sizeof a.ext, xn = (uint32_t)sizeof a.ext;   /* our chunk 1 */
        memcpy(big, img, at1);
        big[at1] = 2u; big[at1 + 1u] = 5u; big[at1 + 2u] = 0u;        /* a chunk 2 of 5 bytes */
        for (k = 0; k < 5u; k++) big[at1 + 3u + k] = 0xAAu;
        big[at1 + 8u] = SQ_CHUNK_EXT; big[at1 + 9u] = (uint8_t)((xn + 4u) & 0xFFu); big[at1 + 10u] = (uint8_t)((xn + 4u) >> 8);
        memcpy(big + at1 + 11u, &a.ext, xn);
        for (k = 0; k < 4u; k++) big[at1 + 11u + xn + k] = 0x55u;
        big[at1 + 11u + xn + 4u] = 0u;
        CHECK(sq_deserialize(&b, big, at1 + 12u + xn + 4u) == 0 && !memcmp(&a.ext, &b.ext, sizeof a.ext));
        CHECK(sq_image_ok(big, at1 + 12u + xn + 4u) == 0);
        /* 0.15: a 0.14 image (chunk 1 of 780 bytes): no name, no groove; the rest as written */
        memcpy(big, img, at1);
        big[at1] = SQ_CHUNK_EXT; big[at1 + 1u] = (uint8_t)(SQ_EXT_014 & 0xFFu); big[at1 + 2u] = (uint8_t)(SQ_EXT_014 >> 8);
        {
            sq_ext_t x14 = a.ext;
            for (k = 0; k < SQ_TRACKS; k++) { x14.track[k].groove = 0u; x14.track[k].groove_amt = 0u; }
            memcpy(big + at1 + 3u, &x14, SQ_EXT_014);
            big[at1 + 3u + SQ_EXT_014] = 0u;
            memset(&b, 0x5A, sizeof b);
            CHECK(sq_deserialize(&b, big, at1 + 4u + SQ_EXT_014) == 0 && !memcmp(&x14, &b.ext, SQ_EXT_014) && b.ext.name[0] == 0 && b.ext.name[15] == 0);
        }
    }
    /* 0.15: the name and the groove go round */
    {
        static const char nm[16] = "my song #2";
        memcpy(a.ext.name, nm, 16u);
        a.ext.track[3].groove = SQ_GROOVE_DILLA; a.ext.track[3].groove_amt = 70u;
        sq_ext_sanitize(&a.ext);
        CHECK(!memcmp(a.ext.name, "MY SONG #2\0\0\0\0\0\0", 16u));
        n = sq_serialize(&a, img, sizeof img);
        CHECK(n > 0u && sq_deserialize(&b, img, n) == 0 && !memcmp(&a.ext, &b.ext, sizeof a.ext));
        CHECK(b.ext.track[3].groove == SQ_GROOVE_DILLA && b.ext.track[3].groove_amt == 70u);
        memset(a.ext.name, 0, 16u);
        a.ext.track[3].groove = 0u; a.ext.track[3].groove_amt = 0u;
    }
    {   /* the name's characters */
        char t1[16] = {' ', ' ', 'a', 'b', '\t', 'Z', '9', '@', ' ', ' ', 0, 'X', 'Y', 0, 0, 0};
        char t2[16], t3[16];
        uint32_t k;
        sq_name_sanitize(t1, 16u);
        CHECK(!memcmp(t1, "AB_Z9_\0\0\0\0\0\0\0\0\0\0", 16u));     /* (after the 0: nothing) */
        for (k = 0; k < 16u; k++) t2[k] = (char)0xFF;                   /* an erased flash */
        sq_name_sanitize(t2, 16u);
        CHECK(t2[0] == 0 && t2[15] == 0);
        memcpy(t3, "ABCDEFGHIJKLMNOP", 16u);                            /* all 16, no 0 */
        sq_name_sanitize(t3, 16u);
        CHECK(!memcmp(t3, "ABCDEFGHIJKLMNOP", 16u));
        memcpy(t3, "-_.+#&!'()/: x\xE8y", 16u);
        sq_name_sanitize(t3, 16u);
        CHECK(!memcmp(t3, "-_.+#&!'()/: X_Y", 16u));
    }
    {   /* GROOVE: the tables in the nudge's and the velocity's room, OFF and 0 % do nothing, the amount scales */
        uint32_t g, k;
        int ok = 1;
        for (g = 0; g < SQ_GROOVES; g++)
            for (k = 0; k < 16u; k++) {
                int32_t tt = sq_groove_time((uint8_t)g, 100u, k), vv = sq_groove_vel((uint8_t)g, 100u, k);
                if (tt < -40 || tt > 40 || vv < -30 || vv > 30) ok = 0;
                if (sq_groove_time((uint8_t)g, 0u, k) || sq_groove_vel((uint8_t)g, 0u, k)) ok = 0;
                if (sq_groove_time((uint8_t)g, 100u, k) != sq_groove_time((uint8_t)g, 100u, k + 16u)) ok = 0;
            }
        CHECK(ok);
        CHECK(sq_groove_time(SQ_GROOVE_OFF, 100u, 1u) == 0 && sq_groove_vel(SQ_GROOVE_OFF, 100u, 0u) == 0);
        CHECK(sq_groove_time(SQ_GROOVE_GARAGE, 100u, 1u) == 28 && sq_groove_time(SQ_GROOVE_GARAGE, 50u, 1u) == 14);
        CHECK(sq_groove_vel(SQ_GROOVE_TRAP, 100u, 1u) == -20 && sq_groove_vel(SQ_GROOVE_TRAP, 200u, 1u) == -20);
        CHECK(sq_groove_time(SQ_GROOVES, 100u, 1u) == 0 && !strcmp(sq_groove_name(SQ_GROOVE_LAIDBACK), "LAID BACK") && !strcmp(sq_groove_name(99u), "OFF"));
        a.ext.track[0].groove = 77u; a.ext.track[0].groove_amt = 180u;
        sq_ext_sanitize(&a.ext);
        CHECK(a.ext.track[0].groove == 0u && a.ext.track[0].groove_amt == 100u);
        a.ext.track[0].groove_amt = 0u;
    }
    /* sanitize: out-of-range values go to the defaults */
    b.ext.lfo[0].seq_n = 1u; b.ext.lfo[2].seq_n = 9u; b.ext.lfo[0].seq_every = 7u; b.ext.lfo[0].seq_rate[1] = 40u; b.ext.lfo[0].trig = 17u;
    b.ext.track[1].chain_n = 0u; b.ext.track[1].chain_pat[2] = 9u; b.ext.track[1].chain_rep[3] = 0u; b.ext.track[1].chain_on = 3u;
    b.ext.motion_bars = 3u; b.ext.kb_mode = 5u; b.ext.kb_ch = 20u; b.ext.motion[2][0] = 100; b.ext.motion[1][0] = -100;
    sq_ext_sanitize(&b.ext);
    CHECK(b.ext.lfo[0].seq_n == 0u && b.ext.lfo[2].seq_n == 0u && b.ext.lfo[0].seq_every == SQ_RE_BEAT && b.ext.lfo[0].seq_rate[1] == SQ_RSEQ_OWN && b.ext.lfo[0].trig == 0u);
    CHECK(b.ext.track[1].chain_n == 1u && b.ext.track[1].chain_pat[2] == 0u && b.ext.track[1].chain_rep[3] == 1u && b.ext.track[1].chain_on == 1u);
    CHECK(b.ext.motion_bars == 0u && b.ext.kb_mode == SQ_KB_OFF && b.ext.kb_ch == 0u && b.ext.motion[2][0] == 25 && b.ext.motion[1][0] == -90);
    /* RATE SEQ: a new rate each beat, the cycle from each beat */
    sq_lfo_default(&l); l.rate = 6u;
    for (i = 0; i < sizeof x; i++) ((uint8_t *)&x)[i] = 0u;
    CHECK(sq_lfo_rate_at(&l, &x, 1000u) == 6u && sq_lfo_seq_tick(&x, 1000u) == 1000u);   /* (off: the RATE, the clock) */
    x.seq_n = 3u; x.seq_every = SQ_RE_BEAT; x.seq_rate[0] = 10u; x.seq_rate[1] = 12u; x.seq_rate[2] = SQ_RSEQ_OWN;
    CHECK(sq_lfo_rate_at(&l, &x, 0u) == 10u && sq_lfo_rate_at(&l, &x, 23u) == 10u && sq_lfo_rate_at(&l, &x, 24u) == 12u);
    CHECK(sq_lfo_rate_at(&l, &x, 48u) == 6u && sq_lfo_rate_at(&l, &x, 72u) == 10u);
    CHECK(sq_lfo_seq_tick(&x, 50u) == 2u && sq_lfo_seq_tick(&x, 24u) == 0u);
    x.seq_every = SQ_RE_2BARS;
    CHECK(sq_rseq_ticks(SQ_RE_2BARS) == 192u && sq_lfo_rate_at(&l, &x, 191u) == 10u && sq_lfo_rate_at(&l, &x, 192u) == 12u && sq_lfo_seq_tick(&x, 200u) == 8u);
    /* CHAIN LIST: A A B(x2) A */
    c = a.ext.track[0];
    pos = 255u; left = 0u;
    seen[0] = sq_chain_next(&c, &pos, &left);
    CHECK(seen[0] == 0u && pos == 0u && left == 1u);   /* (from nowhere: the first entry) */
    {
        uint8_t q = 0u, lf = c.chain_rep[0], got[10];
        for (i = 0; i < 10u; i++) got[i] = sq_chain_next(&c, &q, &lf);
        /* after entry 0 (A): A, B, B, A, A, A, B, B, A, A */
        CHECK(got[0] == 0u && got[1] == 1u && got[2] == 1u && got[3] == 0u && got[4] == 0u && got[5] == 0u && got[6] == 1u && got[7] == 1u && got[8] == 0u);
    }
    CHECK(sq_chain_find(&c, 1u) == 2 && sq_chain_find(&c, 0u) == 0 && sq_chain_find(&c, 5u) == -1);
    /* the keyboard: semitones from the key's own root, -5..+6 */
    CHECK(sq_kb_transpose(60u, 0u) == 0 && sq_kb_transpose(65u, 0u) == 5 && sq_kb_transpose(67u, 0u) == -5 && sq_kb_transpose(66u, 0u) == 6);
    CHECK(sq_kb_transpose(41u, 5u) == 0 && sq_kb_transpose(43u, 5u) == 2 && sq_kb_transpose(40u, 5u) == -1 && sq_kb_transpose(36u, 5u) == -5);
}

/* 0.19: the MIDI FX chain - the four effects together, their values kept, the track's one effect its first; a 0.18
 * image's one effect becomes the chain */
static void test_v019_mfx_chain(void)
{
    static sq_project_t a, b;
    static uint8_t img[0x10000], old[0x10000];
    uint32_t n, t, k, at1;
    int8_t am; uint8_t tm, fb;
    sq_project_init(&a);
    for (t = 0; t < SQ_TRACKS; t++) {                  /* a new project: nothing plays, each effect its defaults */
        CHECK(a.ext.mfxc[t].on == 0u && a.track[t].mfx == SQ_MFX_OFF);
        for (k = 1u; k < SQ_MFXS; k++) {
            sq_mfx_defaults((uint8_t)k, &am, &tm, &fb);
            CHECK(a.ext.mfxc[t].amt[k - 1u] == am && a.ext.mfxc[t].time[k - 1u] == tm && a.ext.mfxc[t].fb[k - 1u] == fb);
        }
    }
    CHECK(SQ_MFX_ORDER[0] == SQ_MFX_VELOCITY && SQ_MFX_ORDER[1] == SQ_MFX_OCTAVE && SQ_MFX_ORDER[2] == SQ_MFX_HARM && SQ_MFX_ORDER[3] == SQ_MFX_ECHO);
    /* track 3: OCTAVE + HARM + ECHO with their own values; the track's mfx: the first of the list (HARM) */
    a.ext.mfxc[3].on = (uint8_t)((1u << SQ_MFX_OCTAVE) | (1u << SQ_MFX_HARM) | (1u << SQ_MFX_ECHO));
    a.ext.mfxc[3].amt[SQ_MFX_HARM - 1u] = -3; a.ext.mfxc[3].fb[SQ_MFX_HARM - 1u] = 50u;
    a.ext.mfxc[3].amt[SQ_MFX_OCTAVE - 1u] = 2; a.ext.mfxc[3].time[SQ_MFX_OCTAVE - 1u] = SQ_OCT_THIRD;
    a.ext.mfxc[3].amt[SQ_MFX_ECHO - 1u] = 4; a.ext.mfxc[3].time[SQ_MFX_ECHO - 1u] = 3u; a.ext.mfxc[3].fb[SQ_MFX_ECHO - 1u] = 40u;
    a.ext.mfxc[9].on = (uint8_t)(1u << SQ_MFX_VELOCITY); a.ext.mfxc[9].amt[SQ_MFX_VELOCITY - 1u] = -6;
    sq_project_sanitize(&a);
    CHECK(a.track[3].mfx == SQ_MFX_HARM && a.track[3].mfx_amt == -3 && a.track[3].mfx_fb == 50u);
    CHECK(a.track[9].mfx == SQ_MFX_VELOCITY && a.track[9].mfx_amt == -6);
    n = sq_serialize(&a, img, sizeof img);
    CHECK(n > 0u && sq_deserialize(&b, img, n) == 0 && !memcmp(&a, &b, sizeof a));
    CHECK(b.ext.mfxc[3].on == a.ext.mfxc[3].on && b.ext.mfxc[3].time[SQ_MFX_OCTAVE - 1u] == SQ_OCT_THIRD && b.ext.mfxc[3].fb[SQ_MFX_ECHO - 1u] == 40u);
    /* sanitize: each effect its range, no bit for OFF or beyond */
    b.ext.mfxc[0].on = 0xFFu;
    b.ext.mfxc[0].amt[SQ_MFX_OCTAVE - 1u] = 9; b.ext.mfxc[0].time[SQ_MFX_OCTAVE - 1u] = 7u;
    b.ext.mfxc[0].amt[SQ_MFX_ECHO - 1u] = -2; b.ext.mfxc[0].fb[SQ_MFX_ECHO - 1u] = 0u;
    b.ext.mfxc[0].amt[SQ_MFX_VELOCITY - 1u] = 100; b.ext.mfxc[0].amt[SQ_MFX_HARM - 1u] = -50;
    sq_project_sanitize(&b);
    CHECK(b.ext.mfxc[0].on == SQ_MFX_ALL && b.ext.mfxc[0].amt[SQ_MFX_OCTAVE - 1u] == 2 && b.ext.mfxc[0].time[SQ_MFX_OCTAVE - 1u] == SQ_OCT_ALT);
    CHECK(b.ext.mfxc[0].amt[SQ_MFX_ECHO - 1u] == 0 && b.ext.mfxc[0].fb[SQ_MFX_ECHO - 1u] == 10u && b.ext.mfxc[0].amt[SQ_MFX_VELOCITY - 1u] == 8 &&
          b.ext.mfxc[0].amt[SQ_MFX_HARM - 1u] == -12);
    CHECK(b.track[0].mfx == SQ_MFX_HARM && b.track[0].mfx_amt == -12);
    b.ext.mfxc[0].on = 0u; sq_project_sanitize(&b);
    CHECK(b.track[0].mfx == SQ_MFX_OFF && b.track[0].mfx_amt == 0);
    /* a 0.18 image: chunk 1 of 796 bytes (no chain); track 2 plays OCTAVE -1 on every 4th, track 7 ECHO: their chains */
    sq_project_init(&a);
    a.ext.kb_mode = SQ_KB_ALL;                          /* (so that chunk 1 is written) */
    a.track[2].mfx = SQ_MFX_OCTAVE; a.track[2].mfx_amt = -1; a.track[2].mfx_time = SQ_OCT_FOURTH; a.track[2].mfx_fb = 30u;
    a.track[7].mfx = SQ_MFX_ECHO; a.track[7].mfx_amt = 3; a.track[7].mfx_time = 1u; a.track[7].mfx_fb = 70u;
    n = sq_serialize(&a, img, sizeof img);             /* (no sanitize: the tracks as a 0.18 firmware had them) */
    CHECK(n > 0u);
    at1 = n - 1u - 3u - (uint32_t)sizeof a.ext;
    CHECK(img[at1] == SQ_CHUNK_EXT);
    memcpy(old, img, at1);
    old[at1] = SQ_CHUNK_EXT; old[at1 + 1u] = (uint8_t)(SQ_EXT_018 & 0xFFu); old[at1 + 2u] = (uint8_t)(SQ_EXT_018 >> 8);
    memcpy(old + at1 + 3u, &a.ext, SQ_EXT_018);
    old[at1 + 3u + SQ_EXT_018] = 0u;
    memset(&b, 0x5A, sizeof b);
    CHECK(sq_deserialize(&b, old, at1 + 4u + SQ_EXT_018) == 0 && b.ext.kb_mode == SQ_KB_ALL);
    CHECK(b.ext.mfxc[2].on == (1u << SQ_MFX_OCTAVE) && b.ext.mfxc[2].amt[SQ_MFX_OCTAVE - 1u] == -1 && b.ext.mfxc[2].time[SQ_MFX_OCTAVE - 1u] == SQ_OCT_FOURTH);
    CHECK(b.ext.mfxc[7].on == (1u << SQ_MFX_ECHO) && b.ext.mfxc[7].amt[SQ_MFX_ECHO - 1u] == 3 && b.ext.mfxc[7].time[SQ_MFX_ECHO - 1u] == 1u &&
          b.ext.mfxc[7].fb[SQ_MFX_ECHO - 1u] == 70u);
    CHECK(b.track[2].mfx == SQ_MFX_OCTAVE && b.track[7].mfx == SQ_MFX_ECHO && b.ext.mfxc[0].on == 0u);
    sq_mfx_defaults(SQ_MFX_HARM, &am, &tm, &fb);
    CHECK(b.ext.mfxc[2].amt[SQ_MFX_HARM - 1u] == am && b.ext.mfxc[2].fb[SQ_MFX_HARM - 1u] == fb);   /* (the others: their defaults) */
    /* an image with no chunk 1 at all (a 0.12 one, or the defaults): the same */
    a.ext.kb_mode = SQ_KB_OFF;
    n = sq_serialize(&a, img, sizeof img);
    CHECK(n > 0u && sq_deserialize(&b, img, n) == 0 && b.ext.mfxc[7].on == (1u << SQ_MFX_ECHO) && b.track[7].mfx_fb == 70u);
    /* the chain written back and read again: what a 0.18 firmware sees is the first effect, as before */
    n = sq_serialize(&b, img, sizeof img);
    CHECK(n > 0u && sq_deserialize(&a, img, n) == 0 && !memcmp(&a, &b, sizeof a));
}

int main(void)
{
    test_v012_break();
    test_v013_ext();
    test_v07_music_tools();
    test_layout();
    test_divisions();
    test_expo();
    test_tape();
    test_init();
    test_offset();
    test_long_gate();
    test_ramp();
    test_arp();
    test_arp_modes();
    test_euclid();
    test_tools();
    test_advance();
    test_advance_loop();
    test_rec_target();
    test_names();
    test_lfo();
    test_cook_and_tools();
    test_scales();
    test_sanitize();
    test_serialize();
    test_serialize_v8();
    test_v08();
    test_v09();
    test_v010();
    test_v011_extend();
    test_v011_cook();
    test_v011_harmony();
    test_planes();
    test_beats();
    test_generators();
    test_v019_mfx_chain();
    printf("sagga core: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
