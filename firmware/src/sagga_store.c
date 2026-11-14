/* SPDX-License-Identifier: GPL-3.0-only */
/*
 * SAGGA STORE - the eight project slots in the flash. Included by dinghy.c after handle_buttons().
 *
 * The eight slots live in nine 32 KB areas of the flash at SQ_SLOT_BASE (the data area of the Felucca family, which
 * this firmware does not otherwise use). An area holds a header page (written last, so a save cut by a power loss is
 * simply not there) and, from SQ_SLOT_HEAD, the sparse image of sq_serialize(). The header says which slot it is and
 * a sequence number: the newest copy of a slot is the slot, an older one is free space.
 *
 * Erasing 4 KB of the flash keeps the interrupts off for ~45 ms, which the clock would hear. So:
 *   - the free areas are erased in the background while the transport is stopped, one sector per pass;
 *   - a save goes into an area that is already erased: it only programs pages (1-3 ms a pass), and the copy it
 *     replaces stays until the new one is complete and checked;
 *   - a save made while playing, with no erased area left, keeps its snapshot and is written at STOP.
 * The slot saved last is the one loaded at power-on.
 *
 *   SAVE + PRESETS     choose the slot (the screen shows the eight; 0.15: and the name of the project in each)
 *   SAVE, SAVE         the first press asks, the second (within 3 s) saves
 *   HOME + SAVE, again load the chosen slot
 *   SAVE + REC, again  0.15: clear the chosen slot (stopped): it is EMPTY after, the project you have is not touched
 * 0.15: the header page carries the project's name too (after the five words), so that choosing a slot can show it
 * without reading the image; a 0.14 header has none there (FF: no name).
 */

#define SQ_SLOTS      8u
#define SQ_AREAS      9u                            /* one more than the slots: a save never overwrites the copy it replaces */
#define SQ_SLOT_SIZE  0x8000u
#define SQ_SLOT_HEAD  0x100u
#define SQ_SLOT_MAGIC 0x4C534753u                   /* "SGSL" */
#define SQ_IMG_MAX    (SQ_SLOT_SIZE - SQ_SLOT_HEAD)
#define SQ_ASK_MS     3000u
#define SQ_STEP_PLAY  512u                          /* bytes programmed / checked per pass while playing */
#define SQ_STEP_IDLE  4096u                         /* ... and while stopped */

#if SQ_SLOT_BASE + SQ_AREAS * SQ_SLOT_SIZE > SQ_SLOT_END
#error "the slot areas do not fit"
#endif

#ifdef DINGHY_HOST
#define SQ_STORE_LOG(...) printf(__VA_ARGS__)
#else
#define SQ_STORE_LOG(...) ((void)0)
#endif

static uint8_t store_img[SQ_SLOT_SIZE] __attribute__((section(".pool")));   /* the image being saved, loaded or exchanged */
static uint8_t store_chk[256];

typedef struct { uint8_t ok, area; uint32_t seq, len, crc; char name[SQ_NAME_LEN + 1u]; } slot_info_t;
#define SQ_HEAD_NAME 20u                            /* 0.15: where the name is in the header page (after h[0..4]) */
static slot_info_t slot_info[SQ_SLOTS];
static uint8_t slot_cur;                            /* the slot SAVE and LOAD use */
static uint32_t store_seq;                          /* the highest sequence number on the flash */
static uint16_t area_live;                          /* bit per area: it holds the newest copy of a slot */
static uint16_t area_blank;                         /* bit per area: known to be erased all through */
static uint8_t maint_area = 255u, maint_sector;    /* the background eraser */

enum { ST_IDLE = 0, ST_WAIT, ST_ERASE, ST_PROGRAM, ST_CHECK, ST_FINISH };
static uint8_t save_state, save_slot, save_area;
static char save_name[SQ_NAME_LEN];                 /* 0.15: the name the header gets (the project's at SAVE) */
static uint32_t save_len, save_pos, save_sector, save_sectors, save_crc;

static uint8_t imp_on;                              /* a SysEx import is filling store_img (see the dump, below) */
static uint32_t imp_next, imp_count, imp_got, imp_until;

/* RELOAD (sagga_live.c) reads the project as it was saved: from the slot it was loaded from or saved to, or, after an
 * import (a file of the library), from store_img while nothing else has used it since */
#define RL_IMPORT 0x80u
static uint8_t rl_src = 255u;
static uint8_t rl_state;                            /* 0 idle, 1 reading the slot, 2 putting the tracks back */
static uint32_t rl_len;
static void rl_img_used(void) { if (rl_src == RL_IMPORT) rl_src = 255u; }     /* store_img is about to hold something else */
static void reload_step(void);

static uint8_t save_down, save_turned;              /* the SAVE button is held / the slot was turned while it was */
static uint8_t ask_kind;                            /* 0 nothing asked, 1 save, 2 load, 3 clear (0.15) */
static uint8_t ask_slot;
static uint32_t ask_until;

static uint32_t area_off(uint32_t a) { return SQ_SLOT_BASE + a * SQ_SLOT_SIZE; }

static int store_erase(uint32_t off)
{
    uint32_t took = 0u;
#ifdef DINGHY_HOST
    if (playing) printf("%6u ms  ERASE WHILE PLAYING\n", fm1_ms);   /* (the tests look for this: it must never happen) */
#endif
    return fl_erase4k(off, &took);
}

/* the headers of the nine areas: which slot each holds, the newest copy of each slot */
static void store_scan(void)
{
    uint32_t a, s, h[5];
    for (s = 0; s < SQ_SLOTS; s++) { slot_info[s].ok = 0u; slot_info[s].name[0] = 0; }
    for (a = 0; a < SQ_AREAS; a++) {
        if (!flash_ok || st_read(area_off(a), h, sizeof h)) continue;
        if (h[0] != SQ_SLOT_MAGIC || h[2] == 0u || h[2] > SQ_IMG_MAX || h[4] >= SQ_SLOTS) {
            if (h[0] != 0xFFFFFFFFu) area_blank &= (uint16_t)~(1u << a);
            continue;
        }
        area_blank &= (uint16_t)~(1u << a);
        if (h[1] > store_seq) store_seq = h[1];
        s = h[4];
        if (slot_info[s].ok && slot_info[s].seq >= h[1]) continue;
        slot_info[s].ok = 1u;
        slot_info[s].area = (uint8_t)a;
        slot_info[s].seq = h[1];
        slot_info[s].len = h[2];
        slot_info[s].crc = h[3];
        if (st_read(area_off(a) + SQ_HEAD_NAME, slot_info[s].name, SQ_NAME_LEN)) slot_info[s].name[0] = 0;   /* 0.15 */
        sq_name_sanitize(slot_info[s].name, SQ_NAME_LEN);
        slot_info[s].name[SQ_NAME_LEN] = 0;
    }
    area_live = 0u;
    for (s = 0; s < SQ_SLOTS; s++) if (slot_info[s].ok) area_live |= (uint16_t)(1u << slot_info[s].area);
}

/* the image of a slot into store_img; 0 = ok and the CRC matches */
static int slot_read(uint32_t s)
{
    uint32_t len = slot_info[s].len, i;
    if (!slot_info[s].ok || tst_booted) return -1;     /* (0.11: the PC test reads no slot) */
    rl_img_used();
    for (i = 0; i < len; i += 256u) {
        uint32_t k = len - i < 256u ? len - i : 256u;
        if (st_read(area_off(slot_info[s].area) + SQ_SLOT_HEAD + i, store_img + i, k)) return -2;
    }
    return sq_crc32(store_img, len) == slot_info[s].crc ? 0 : -3;
}

/* the project from a slot; on a failure the project is not touched */
static int slot_load(uint32_t s)
{
    int rc = slot_read(s);
    if (rc) return rc;
    if (sq_image_ok(store_img, slot_info[s].len)) return -4;
    return sq_deserialize(&project, store_img, slot_info[s].len) ? -4 : 0;
}

/* 0.8: every project has an id of its own (the Pi keeps the synths' patches of its snapshots under it): made once */
static void project_id_check(void)
{
    if (project.id) return;
    project.id = sq_hash3(fm1_ms, sq_micros(), sq_rng_next(&sq_rng_state)) | 1u;
}

/* power-on: the slot saved last, else the next newest, else a blank project */
static void store_boot(void)
{
    uint32_t best, tried = 0u, attempt;
    sq_project_init(&project);
    store_scan();
    for (attempt = 0; attempt < SQ_SLOTS; attempt++) {
        uint32_t i, hi = 0u;
        best = SQ_SLOTS;
        for (i = 0; i < SQ_SLOTS; i++)
            if (slot_info[i].ok && !(tried & (1u << i)) && (best == SQ_SLOTS || slot_info[i].seq > hi)) { best = i; hi = slot_info[i].seq; }
        if (best == SQ_SLOTS) break;
        tried |= 1u << best;
        if (slot_load(best) == 0) { slot_cur = (uint8_t)best; rl_src = (uint8_t)best; project_id_check(); return; }
        sq_project_init(&project);
        slot_info[best].ok = 0u;                    /* it does not read back: not offered as a project (its area is kept) */
    }
    project_id_check();
}

/* ---- the background eraser: while stopped, one sector of a free area per pass */

static int sector_blank(uint32_t off)
{
    uint32_t i, j;
    for (i = 0; i < 0x1000u; i += sizeof store_chk) {
        if (st_read(off + i, store_chk, sizeof store_chk)) return 0;
        for (j = 0; j < sizeof store_chk; j++) if (store_chk[j] != 0xFFu) return 0;
    }
    return 1;
}

static void store_maint(void)
{
    uint32_t a, busy = area_live | area_blank;
    if (playing || !flash_ok || tst_booted) return;   /* (0.11: the PC test never erases) */
    if (maint_area >= SQ_AREAS || (busy & (1u << maint_area))) {
        for (a = 0; a < SQ_AREAS; a++) if (!(busy & (1u << a))) break;
        if (a == SQ_AREAS) { maint_area = 255u; return; }
        maint_area = (uint8_t)a;
        maint_sector = 0u;
    }
    {
        uint32_t off = area_off(maint_area) + (uint32_t)maint_sector * 0x1000u;
        if (!sector_blank(off) && store_erase(off)) { maint_area = 255u; return; }   /* (a failing sector: tried again later) */
    }
    if (++maint_sector >= SQ_SLOT_SIZE / 0x1000u) {
        area_blank |= (uint16_t)(1u << maint_area);
        maint_area = 255u;
    }
}

/* ---- saving: (erase,) program, check, header */

static void save_fail(const char *why)
{
    save_state = ST_IDLE;
    area_blank &= (uint16_t)~(1u << save_area);
    status_msg(why);
    store_scan();
    ui_dirty = 1u;
}

static int save_begin(uint8_t s)
{
    uint32_t len, a, free_a = SQ_AREAS;
    if (tst_booted) { status_msg(TST_SLOTS_OFF); return -1; }
    if (save_state != ST_IDLE) { status_msg("SAVING, WAIT"); return -1; }
    if (imp_on) { status_msg("IMPORT IN PROGRESS"); return -1; }
    if (!flash_ok) { status_msg("NO FLASH"); return -2; }
    rl_img_used();
    project_prepare_save();
    len = sq_serialize(&project, store_img, SQ_IMG_MAX);
    if (!len) { status_msg("TOO BIG FOR A SLOT"); return -3; }
    save_len = len;
    save_slot = s;
    save_pos = 0u;
    save_sector = 0u;
    save_sectors = (SQ_SLOT_HEAD + len + 0xFFFu) / 0x1000u;
    save_crc = sq_crc32(store_img, len);
    memcpy(save_name, project.ext.name, SQ_NAME_LEN);  /* 0.15: the header carries it */
    for (a = 0; a < SQ_AREAS; a++) {                /* an erased area; else any area that holds no slot */
        if (area_live & (1u << a)) continue;
        if (area_blank & (1u << a)) { free_a = a; break; }
        if (free_a == SQ_AREAS) free_a = a;
    }
    save_area = (uint8_t)free_a;                    /* (nine areas, eight slots: there is always one) */
    if (maint_area == save_area) maint_area = 255u;
    if (area_blank & (1u << save_area)) {
        save_state = ST_PROGRAM;
        status_num("SAVING SLOT ", (uint32_t)s + 1u);
    } else if (playing) {
        save_state = ST_WAIT;
        status_num("SAVED AT STOP: SLOT ", (uint32_t)s + 1u);
    } else {
        save_state = ST_ERASE;
        status_num("SAVING SLOT ", (uint32_t)s + 1u);
    }
    area_blank &= (uint16_t)~(1u << save_area);     /* from here it is being written */
    ui_dirty = 1u;
    return 0;
}

static void store_service(void)
{
    uint32_t k, step = playing ? SQ_STEP_PLAY : SQ_STEP_IDLE;
    switch (save_state) {
    case ST_IDLE:
        if (imp_on && time_due(fm1_ms, imp_until)) { imp_on = 0u; status_msg("IMPORT CUT OFF"); }
        reload_step();
        store_maint();
        return;
    case ST_WAIT:                                   /* the snapshot waits for the transport to stop */
        if (!playing) save_state = ST_ERASE;
        return;
    case ST_ERASE:
        if (playing) return;                        /* (an erase is never done while playing) */
        if (store_erase(area_off(save_area) + save_sector * 0x1000u)) { save_fail("SAVE FAILED (ERASE)"); return; }
        if (++save_sector >= save_sectors) save_state = ST_PROGRAM;
        ui_dirty = 1u;
        return;
    case ST_PROGRAM:
        k = save_len - save_pos < step ? save_len - save_pos : step;
        if (fl_write(area_off(save_area) + SQ_SLOT_HEAD + save_pos, store_img + save_pos, k)) { save_fail("SAVE FAILED (WRITE)"); return; }
        save_pos += k;
        if (save_pos >= save_len) { save_state = ST_CHECK; save_pos = 0u; }
        return;
    case ST_CHECK: {                                /* read it back: the check is on what is in the flash */
        uint32_t end = save_pos + step < save_len ? save_pos + step : save_len;
        while (save_pos < end) {
            k = end - save_pos < sizeof store_chk ? end - save_pos : sizeof store_chk;
            if (st_read(area_off(save_area) + SQ_SLOT_HEAD + save_pos, store_chk, k) || bdiff_(store_chk, store_img + save_pos, k)) {
                save_fail("SAVE FAILED (CHECK)");
                return;
            }
            save_pos += k;
        }
        if (save_pos >= save_len) save_state = ST_FINISH;
        return;
    }
    default: {                                      /* the header: from now on the new copy is the slot */
        uint32_t h[5u + SQ_NAME_LEN / 4u], r[5u + SQ_NAME_LEN / 4u];
        h[0] = SQ_SLOT_MAGIC; h[1] = store_seq + 1u; h[2] = save_len; h[3] = save_crc; h[4] = save_slot;
        memcpy(&h[5], save_name, SQ_NAME_LEN);       /* 0.15: the name (a 0.14 firmware reads the five words only) */
        if (fl_write(area_off(save_area), (const uint8_t *)h, sizeof h) || st_read(area_off(save_area), r, sizeof r) ||
            bdiff_((const uint8_t *)r, (const uint8_t *)h, sizeof h)) { save_fail("SAVE FAILED (HEADER)"); return; }
        save_state = ST_IDLE;
        store_scan();                               /* (the copy it replaces is free now: erased when stopped) */
        slot_cur = save_slot;
        rl_src = save_slot;                         /* RELOAD brings this back */
        {
            char *p = msg_buf;
            p = put_s(p, "SAVED "); p = put_u(p, (uint32_t)save_slot + 1u); p = put_s(p, " ("); p = put_u(p, (save_len + 512u) / 1024u);
            p = put_s(p, " KB)"); finish(p);
            status_msg(msg_buf);
        }
        SQ_STORE_LOG("%6u ms  slot %u saved (%u B) area %u\n", fm1_ms, (unsigned)save_slot + 1u, (unsigned)save_len, (unsigned)save_area);
        ui_dirty = grid_dirty = 1u;
        return;
    }
    }
}

/* ---- the buttons */

static void slot_turn(int32_t d)
{
    slot_cur = change_u8(slot_cur, d, 0u, SQ_SLOTS - 1u);
    save_turned = 1u;
    ask_kind = 0u;
    ui_dirty = 1u;
}
static void save_turn(int32_t d) { slot_turn(d); }
static void slot_pick(uint8_t s) { slot_cur = s < SQ_SLOTS ? s : (uint8_t)(SQ_SLOTS - 1u); ask_kind = 0u; ui_dirty = grid_dirty = 1u; }

static void ask_for(uint8_t kind)
{
    char *p = msg_buf;
    ask_kind = kind;
    ask_slot = slot_cur;
    ask_until = fm1_ms + SQ_ASK_MS;
    p = put_s(p, kind == 1u ? "SAVE SLOT " : kind == 3u ? "CLEAR SLOT " : "LOAD SLOT ");
    p = put_u(p, (uint32_t)slot_cur + 1u);
    if (kind != 1u && slot_info[slot_cur].ok && slot_info[slot_cur].name[0]) { p = put_s(p, " "); p = put_s(p, slot_info[slot_cur].name); }   /* 0.15 */
    p = put_s(p, kind == 1u ? ": SAVE AGAIN" : kind == 3u ? ": SAVE+REC AGAIN" : !slot_info[slot_cur].ok ? " EMPTY: AGAIN = NEW PROJECT" : ": HOME+SAVE AGAIN");   /* (0.14) */
    finish(p);
    status_msg(msg_buf);
}

/* 0.15: SAVE + REC, twice: the chosen slot cleared. Every area whose header names that slot loses its header page (an
 * older copy would otherwise become the slot); the rest of the area the background eraser does. Stopped only: an erase
 * keeps the interrupts off for ~45 ms. The project in the FM-1 is not touched (SAVE puts it back, in any slot). */
static void store_tap_clear(void)
{
    uint32_t a, h[5], bad = 0u;
    uint8_t s = slot_cur;
    char *p = msg_buf;
    if (tst_booted) { status_msg(TST_SLOTS_OFF); return; }
    if (save_state != ST_IDLE) { status_msg(save_state == ST_WAIT ? "A SAVE WAITS FOR STOP" : "SAVING, WAIT"); ask_kind = 0u; return; }
    if (imp_on) { status_msg("IMPORT IN PROGRESS"); return; }
    if (!slot_info[s].ok) { ask_kind = 0u; status_num("NOTHING TO CLEAR: EMPTY SLOT ", (uint32_t)s + 1u); return; }
    if (playing) { ask_kind = 0u; status_msg("CLEAR A SLOT: STOP FIRST"); return; }
    if (!(ask_kind == 3u && ask_slot == s && !time_due(fm1_ms, ask_until))) { ask_for(3u); return; }
    ask_kind = 0u;
    for (a = 0; a < SQ_AREAS; a++) {
        if (st_read(area_off(a), h, sizeof h) || h[0] != SQ_SLOT_MAGIC || h[4] != s) continue;
        area_blank &= (uint16_t)~(1u << a);
        if (maint_area == a) maint_area = 255u;
        if (store_erase(area_off(a))) bad = 1u;
    }
    store_scan();
    if (rl_src == s) rl_src = 255u;                 /* (RELOAD has nothing to go back to there) */
    if (bad || slot_info[s].ok) { status_msg("CLEAR FAILED"); ui_dirty = grid_dirty = 1u; return; }
    p = put_s(p, "SLOT "); p = put_u(p, (uint32_t)s + 1u); p = put_s(p, " CLEARED: THE PROJECT YOU HAVE STAYS");
    finish(p);
    status_msg(msg_buf);
    SQ_STORE_LOG("%6u ms  slot %u cleared\n", fm1_ms, (unsigned)s + 1u);
    ui_dirty = grid_dirty = 1u;
}

static void store_tap_save(void)
{
    if (tst_booted) { status_msg(TST_SLOTS_OFF); return; }   /* 0.11: the PC test: no slot is touched */
    if (save_state != ST_IDLE) { status_msg(save_state == ST_WAIT ? "A SAVE WAITS FOR STOP" : "SAVING, WAIT"); return; }
    if (ask_kind == 1u && ask_slot == slot_cur && !time_due(fm1_ms, ask_until)) {
        ask_kind = 0u;
        save_begin(slot_cur);
    } else ask_for(1u);
}

/* a project has just replaced the old one (LOAD, a SysEx import): start from its beginning */
static void store_loaded(void)
{
    loop_on = 0u;
    gen_reset();                                   /* no dice, EVOLVE, TEMP or song carries over */
    project_runtime_reset(1u);
    brk_roll_clear(); take_clear(); rep_clear();   /* 0.12: nothing of the old project's live play remembered */
    mute_mask = (uint16_t)(project.live.mute_lo | ((uint16_t)project.live.mute_hi << 8));   /* 0.9: as saved */
    solo_mask = 0u; pending_mute = 0u;
    selected_track = 0u; cursor_step = 0u; page = 0u;
    learn_kind = 0u;                               /* (a LEARN armed before the load would write into the new project) */
    memset(lfo_last_valid, 0, sizeof lfo_last_valid);
    rl_state = 0u;
    morph_pos = 0u; morph_dirty = 0u;
    mac_vel = mac_gate = mac_swing = mac_filt = 0; filt_dirty = 0u;      /* 0.5.1: the macros start at 0 */
    snap_cur = snap_pend = 255u; snap_capture = 0u; snap_tx_on = 0u;     /* 0.8: no snapshot plays yet */
    echo_global = 0u;
    audible_prev = 0xFFFFu;
    project_id_check();
    ktrans_pend = SQ_KT_NONE;
    knob_live = 0u; knob_ref = fm1_knob;
    scene_cursor = project.live.scene_cursor < SQ_SCENES ? project.live.scene_cursor : 0u;   /* 0.9: as saved */
    memset(pc_last, 255, sizeof pc_last);
    scene_send_pc(scene_cursor);                   /* 0.5: the synths get the programs of the scene */
    if (project.viaggio.on) vg_reset();            /* 0.9: the states of the tracks from the mutes just restored */
    ui_dirty = grid_dirty = 1u;
}

static void store_tap_load(void)
{
    if (tst_booted) { status_msg(TST_SLOTS_OFF); return; }
    if (imp_on) { status_msg("IMPORT IN PROGRESS"); return; }
    if (save_state != ST_IDLE) {                    /* store_img holds the image being saved: that goes first */
        if (playing) transport_stop();
        status_msg("SAVING FIRST: LOAD AGAIN");
        ask_kind = 0u;
        return;
    }
    if (ask_kind == 2u && ask_slot == slot_cur && !time_due(fm1_ms, ask_until)) {
        ask_kind = 0u;
        if (!slot_info[slot_cur].ok) {             /* 0.14: an empty slot loaded = a new project, all at its defaults */
            if (playing) transport_stop();
            panic_all();
            sq_project_init(&project);
            project.id = 0u;                       /* (a new identity: project_id_check in store_loaded) */
            store_loaded();
            rl_src = 255u;                         /* (nothing saved yet to RELOAD) */
            status_num("NEW PROJECT: SAVE PUTS IT IN SLOT ", (uint32_t)slot_cur + 1u);
            return;
        }
        if (playing) transport_stop();
        panic_all();
        if (slot_load(slot_cur)) { status_msg("LOAD FAILED"); return; }
        store_loaded();
        rl_src = slot_cur;
        {   /* 0.15: with its name */
            char *q = msg_buf;
            q = put_s(q, "LOADED SLOT "); q = put_u(q, (uint32_t)slot_cur + 1u);
            if (project.ext.name[0]) { char nm[SQ_NAME_LEN + 1u]; memcpy(nm, project.ext.name, SQ_NAME_LEN); nm[SQ_NAME_LEN] = 0; q = put_s(q, ": "); q = put_s(q, nm); }
            finish(q);
            status_msg(msg_buf);
        }
    } else ask_for(2u);                             /* (0.14: an empty slot too: the second time, a new project) */
}

static void pipat_save(void);                     /* sagga_pipat.c */
static void pipat_in(uint8_t cmd, const uint8_t *p, uint32_t n);
static void piprog_save(void);
static void piprog_in(uint8_t cmd, const uint8_t *p, uint32_t n);
static void save_pressed(void)
{
    if (in_held() & (1u << BTN_SEQ)) { pipat_save(); return; }               /* 0.11: SEQ + SAVE = the track's pattern to the Pi */
    if (in_held() & (1u << BTN_ARP)) { piprog_save(); return; }              /* 0.12: ARP + SAVE = the progression to the Pi (ARP 3-6) */
    if (in_held() & (1u << BTN_HOME)) { store_tap_load(); return; }
    if (in_held() & (1u << BTN_SEL)) { reload_request(); return; }          /* 0.5: SEL + SAVE = RELOAD */
    save_down = 1u;
    save_turned = 0u;
    save_knob = 0u;
    ui_dirty = 1u;
}

static void save_released(uint32_t held)
{
    (void)held;
    if (!save_down) return;
    save_down = 0u;
    if (save_knob) { save_knob = 0u; ui_dirty = 1u; return; }      /* SAVE + K1 / K2 set something: no save asked */
    store_tap_save();
    ui_dirty = 1u;
}

/* once per pass: an ask that was not answered goes; returns 1 if the screen has to change */
static uint8_t save_tick(void)
{
    if (ask_kind && time_due(fm1_ms, ask_until)) { ask_kind = 0u; return 1u; }
    return 0u;
}

/* ---- the SysEx dump: a project out to the Raspberry Pi (or any computer) and back in (docs/SAGGA-SEQ.md).
 * Every frame is F0 7D 53 47 CMD ... F7 (7D: the non-commercial manufacturer id, then "SG"), every byte 7-bit:
 *   01 [SLOT]                        export: the current project, or slot 0-7 as saved     (to the FM-1)
 *   02 IDX IDX CNT CNT DATA... SUM   a chunk: 256 bytes of the image (the last may be shorter), packed 8-to-7
 *                                    LSB first; IDX / CNT 14-bit; SUM = the sum of the DATA bytes & 7F   (both ways)
 *   03 LEN*3 CRC*5                   the end: the image's length (21 bits) and CRC-32 (7 bits a byte, LSB first)
 *   10 CODE IDX IDX                  the FM-1's answer to an import chunk / end, or to an export it cannot do
 * An export goes out at once (only while stopped: the main loop waits for the USB). An import is chunk by chunk,
 * each answered (the FM-1 has room for one frame), and only while stopped: at the end, if the CRC matches, it
 * replaces the project as LOAD does. SAVE keeps it. */
enum { SX_EXPORT = 0x01, SX_DATA = 0x02, SX_END = 0x03, SX_STATUS = 0x10 };
/* 0.8 SNAPSHOTS and the Pi (the bridge keeps the synths' patches, docs/SAGGA-SEQ.md):
 *   40 N ID*5 PLAY     snapshot N of project ID plays now: send the synths their patches for it        (to the Pi)
 *   41 N ID*5 PLAY     keep the synths' patches for snapshot N of project ID (ask them / listen)        (to the Pi)
 *   42 CODE COUNT      the Pi's answer: 0 patches kept (COUNT synths), 1 none came, 2 sent (COUNT)     (from the Pi)
 * ID: the project's id, 7 bits a byte, LSB first; PLAY: 1 if the transport runs (the Pi may wait for STOP to send) */
enum { SX_SNAP_PLAY = 0x40, SX_SNAP_KEEP = 0x41, SX_SNAP_ANSWER = 0x42 };
enum { SXS_OK = 0, SXS_BUSY, SXS_BADCHUNK, SXS_ORDER, SXS_BADIMAGE, SXS_BADPROJECT, SXS_EMPTY, SXS_NOHOST };
#define SX_CHUNK 256u
#define SX_IMPORT_MS 3000u                          /* an import that stops talking is dropped after this */

static uint8_t sx_out[9u + (SX_CHUNK * 8u + 6u) / 7u + 2u];

/* the library (below) */
enum { SX_LIB_LIST = 0x20, SX_LIB_ENTRY = 0x21, SX_LIB_LOAD = 0x22, SX_LIB_SAVE = 0x23, SX_LIB_ANSWER = 0x24 };
#define LIB_MAX  64u
#define LIB_NAME 17u
#define LIB_NONE 255u
static char lib_name[LIB_MAX][LIB_NAME] __attribute__((section(".pool")));
static uint8_t lib_n, lib_have, lib_sel, lib_cur = LIB_NONE, lib_wait = LIB_NONE, lib_loading = LIB_NONE, lib_ask_over;
static uint32_t lib_ask_until;
static void lib_toast(const char *what, uint8_t i);

static uint32_t sx_pack7(const uint8_t *in, uint32_t n, uint8_t *out)
{
    uint32_t acc = 0u, nb = 0u, o = 0u;
    while (n--) {
        acc |= (uint32_t)*in++ << nb;
        nb += 8u;
        while (nb >= 7u) { out[o++] = (uint8_t)(acc & 0x7Fu); acc >>= 7; nb -= 7u; }
    }
    if (nb) out[o++] = (uint8_t)(acc & 0x7Fu);
    return o;
}

static uint32_t sx_unpack7(const uint8_t *in, uint32_t n, uint8_t *out, uint32_t max)
{
    uint32_t acc = 0u, nb = 0u, o = 0u;
    while (n--) {
        acc |= (uint32_t)(*in++ & 0x7Fu) << nb;
        nb += 7u;
        if (nb >= 8u) { if (o < max) out[o] = (uint8_t)acc; o++; acc >>= 8; nb -= 8u; }
    }
    return o;
}

static uint8_t *sx_head(uint8_t cmd)
{
    sx_out[0] = 0xF0u; sx_out[1] = 0x7Du; sx_out[2] = 0x53u; sx_out[3] = 0x47u; sx_out[4] = cmd;
    return sx_out + 5;
}

static void sx_status(uint8_t code, uint32_t idx)
{
    uint8_t *p = sx_head(SX_STATUS);
    *p++ = code; *p++ = (uint8_t)(idx & 127u); *p++ = (uint8_t)((idx >> 7) & 127u); *p++ = 0xF7u;
    sysex_send(sx_out, (uint32_t)(p - sx_out));
}

static void sx_put7(uint8_t **p, uint32_t v, uint32_t n) { while (n--) { *(*p)++ = (uint8_t)(v & 127u); v >>= 7; } }
static uint32_t sx_get7(const uint8_t *p, uint32_t n) { uint32_t v = 0u, i; for (i = n; i--;) v = v << 7 | (p[i] & 127u); return v; }

/* the project (slot < 0) or a saved slot out as SysEx; 0 = sent */
static int sx_export(int32_t slot)
{
    uint32_t len, crc, cnt, idx;
    uint8_t *p;
    if (playing || save_state != ST_IDLE || imp_on) { sx_status(SXS_BUSY, 0u); status_msg("EXPORT: STOP FIRST"); return -1; }
    if (slot >= 0 && slot < (int32_t)SQ_SLOTS) {
        if (!slot_info[slot].ok) { sx_status(SXS_EMPTY, 0u); status_msg("SLOT EMPTY"); return -2; }
        if (slot_read((uint32_t)slot)) { sx_status(SXS_BADIMAGE, 0u); status_msg("SLOT DOES NOT READ BACK"); return -3; }
        len = slot_info[slot].len;
    } else { rl_img_used(); project_prepare_save(); len = sq_serialize(&project, store_img, SQ_IMG_MAX); }
    if (!len) { sx_status(SXS_BADPROJECT, 0u); status_msg("TOO BIG FOR A SLOT"); return -4; }
    crc = sq_crc32(store_img, len);
    cnt = (len + SX_CHUNK - 1u) / SX_CHUNK;
    for (idx = 0; idx < cnt; idx++) {
        uint32_t k = len - idx * SX_CHUNK < SX_CHUNK ? len - idx * SX_CHUNK : SX_CHUNK, n, i, sum = 0u;
        p = sx_head(SX_DATA);
        sx_put7(&p, idx, 2u);
        sx_put7(&p, cnt, 2u);
        n = sx_pack7(store_img + idx * SX_CHUNK, k, p);
        for (i = 0; i < n; i++) sum += p[i];
        p += n;
        *p++ = (uint8_t)(sum & 127u);
        *p++ = 0xF7u;
        if (sysex_send(sx_out, (uint32_t)(p - sx_out))) { status_msg("EXPORT: NOBODY LISTENS"); return -5; }
    }
    p = sx_head(SX_END);
    sx_put7(&p, len, 3u);
    sx_put7(&p, crc, 5u);
    *p++ = 0xF7u;
    if (sysex_send(sx_out, (uint32_t)(p - sx_out))) { status_msg("EXPORT: NOBODY LISTENS"); return -5; }
    {
        char *q = msg_buf;
        q = put_s(q, "EXPORTED "); q = put_u(q, (len + 512u) / 1024u); q = put_s(q, " KB"); finish(q);
        status_msg(msg_buf);
    }
    SQ_STORE_LOG("%6u ms  exported %u B\n", fm1_ms, (unsigned)len);
    return 0;
}

static void sx_import_chunk(const uint8_t *p, uint32_t n)       /* p: after the command byte */
{
    uint32_t idx, cnt, i, sum = 0u, k;
    if (n < 6u) return;
    idx = sx_get7(p, 2u);
    cnt = sx_get7(p + 2, 2u);
    if (save_state != ST_IDLE || playing) { imp_on = 0u; sx_status(SXS_BUSY, idx); return; }   /* (it would replace the project: not mid-show) */
    for (i = 4; i + 1u < n; i++) sum += p[i];
    if ((sum & 127u) != p[n - 1u]) { sx_status(SXS_BADCHUNK, idx); return; }   /* (the sender sends it again) */
    if (imp_on && idx != 0u && idx + 1u == imp_next && cnt == imp_count) { sx_status(SXS_OK, idx); return; }   /* our answer was lost: again */
    if (idx == 0u) { imp_on = 1u; imp_next = 0u; imp_count = cnt; imp_got = 0u; rl_img_used(); }
    if (!imp_on || idx != imp_next || cnt != imp_count || cnt == 0u || cnt * SX_CHUNK > SQ_IMG_MAX + SX_CHUNK - 1u) {
        sx_status(SXS_ORDER, idx);
        return;
    }
    k = sx_unpack7(p + 4, n - 5u, store_img + idx * SX_CHUNK, SQ_IMG_MAX - idx * SX_CHUNK < SX_CHUNK ? SQ_IMG_MAX - idx * SX_CHUNK : SX_CHUNK);
    if (k == 0u || k > SX_CHUNK || (idx + 1u < cnt && k != SX_CHUNK) || idx * SX_CHUNK + k > SQ_IMG_MAX) { imp_on = 0u; sx_status(SXS_BADCHUNK, idx); return; }
    imp_got = idx * SX_CHUNK + k;
    imp_next++;
    imp_until = fm1_ms + SX_IMPORT_MS;
    if (idx == 0u) status_msg("IMPORTING");
    sx_status(SXS_OK, idx);
}

static void sx_import_end(const uint8_t *p, uint32_t n)
{
    uint32_t len, crc;
    if (n < 8u) return;
    len = sx_get7(p, 3u);
    crc = sx_get7(p + 3, 5u);
    if (playing) { imp_on = 0u; sx_status(SXS_BUSY, 0x3FFFu); status_msg("IMPORT: STOP FIRST"); return; }
    if (!imp_on || imp_next != imp_count || len != imp_got || sq_crc32(store_img, len) != crc) {
        imp_on = 0u;
        sx_status(SXS_BADIMAGE, 0x3FFFu);
        status_msg("IMPORT FAILED (DATA)");
        return;
    }
    imp_on = 0u;
    if (sq_image_ok(store_img, len)) {                  /* checked before: the project you have stays if it is not one */
        sx_status(SXS_BADPROJECT, 0x3FFFu);
        status_msg("IMPORT FAILED (NOT A PROJECT)");
        return;
    }
    panic_all();
    sq_deserialize(&project, store_img, len);
    store_loaded();                                     /* (an id of its own if it had none) */
    rl_src = RL_IMPORT;                                 /* RELOAD: from this image, while store_img keeps it */
    rl_len = len;
    if (lib_loading < LIB_MAX) {                        /* a file of the library: it stays on the Pi */
        lib_cur = lib_loading;
        lib_loading = LIB_NONE;
        if (!project.ext.name[0] && lib_cur < lib_n) {  /* 0.15: a project with no name takes the file's (without .SGQ) */
            uint32_t k;
            for (k = 0; k < SQ_NAME_LEN && lib_name[lib_cur][k]; k++) project.ext.name[k] = lib_name[lib_cur][k];
            if (k >= 4u && project.ext.name[k - 4u] == '.') k -= 4u;
            for (; k < SQ_NAME_LEN; k++) project.ext.name[k] = 0;
            sq_name_sanitize(project.ext.name, SQ_NAME_LEN);
        }
        lib_toast("LOADED ", lib_cur);
    } else status_msg("IMPORTED: SAVE TO KEEP IT");
    SQ_STORE_LOG("%6u ms  imported %u B\n", fm1_ms, (unsigned)len);
    sx_status(SXS_OK, 0x3FFFu);
}

/* ---- 0.5: the LIBRARY - the .sgq files the bridge keeps on the Raspberry Pi (docs/SAGGA-GRID.md), as a list on the
 * grid's LIB view: load one (while stopped; asked while playing, it loads at STOP), the next one of the list (a setlist:
 * the files in the order of their names), save the project as a new file or over the one chosen.
 *   20 IDX IDX               file IDX of the list, please (one at a time: the FM-1 has room for one frame)   (to the Pi)
 *   21 IDX CNT NAME...       file IDX of the list: IDX 0..CNT-1 (CNT 0: no file), up to 16 characters   (from the Pi)
 *   22 IDX IDX               load file IDX: the Pi sends it as an import (02 ... 03)      (to the Pi)
 *   23 IDX IDX               the export that follows goes over file IDX (16383: a new file)   (to the Pi)
 *   24 CODE IDX IDX          the Pi's answer: 0 saved, 1 could not save, 2 no such file, 3 could not read it (from the Pi) */

static void lib_send(uint8_t cmd, int32_t idx)
{
    uint8_t *q = sx_head(cmd);
    if (idx >= 0) { *q++ = (uint8_t)(idx & 127); *q++ = (uint8_t)((idx >> 7) & 127); }
    *q++ = 0xF7u;
    sysex_send(sx_out, (uint32_t)(q - sx_out));
}

static void lib_ask_list(void)
{
    lib_send(SX_LIB_LIST, 0);
    if (!lib_have) status_msg("LIBRARY: ASKING THE PI");
}

static void lib_toast(const char *what, uint8_t i)
{
    char *p = msg_buf;
    p = put_s(p, what);
    if (i < lib_n) { p = put_u(p, (uint32_t)i + 1u); p = put_s(p, " "); p = put_s(p, lib_name[i]); }
    finish(p);
    status_msg(msg_buf);
}

static void lib_entry_in(const uint8_t *p, uint32_t n)      /* p: after the command byte */
{
    uint32_t idx, cnt, k;
    if (n < 2u) return;
    idx = p[0]; cnt = p[1];
    if (cnt > LIB_MAX) cnt = LIB_MAX;
    lib_have = 1u;
    if (!cnt) { lib_n = 0u; lib_sel = 0u; lib_cur = LIB_NONE; status_msg("LIBRARY: NO FILES ON THE PI"); grid_dirty = 1u; return; }
    if (idx >= cnt) return;
    lib_n = (uint8_t)cnt;
    if (lib_sel >= lib_n) lib_sel = 0u;
    if (lib_cur != LIB_NONE && lib_cur >= lib_n) lib_cur = LIB_NONE;
    for (k = 0; k + 2u < n && k < LIB_NAME - 1u; k++) {
        uint8_t c = p[2u + k] & 0x7Fu;
        lib_name[idx][k] = (char)(c < 32u ? '?' : c);
    }
    lib_name[idx][k] = 0;
    if (idx + 1u < cnt) lib_send(SX_LIB_LIST, (int32_t)idx + 1);           /* the next one */
    else { char *q = msg_buf; q = put_s(q, "LIBRARY: "); q = put_u(q, cnt); q = put_s(q, " FILES"); finish(q); status_msg(msg_buf); }
    grid_dirty = 1u;
}

/* load file i of the list (stopped; while playing it waits for STOP) */
static void lib_load(uint8_t i)
{
    if (i >= lib_n) return;
    lib_sel = i;
    if (save_state != ST_IDLE || imp_on) { status_msg("SAVING, WAIT"); return; }
    if (playing) { lib_wait = i; lib_toast("LOADS AT STOP: ", i); grid_dirty = 1u; return; }
    lib_wait = LIB_NONE;
    lib_loading = i;
    lib_send(SX_LIB_LOAD, i);
    lib_toast("LOADING ", i);
    grid_dirty = 1u;
}

static void lib_transport_stopped(void)
{
    if (lib_wait < LIB_MAX) { uint8_t i = lib_wait; lib_wait = LIB_NONE; lib_load(i); }
}

static void lib_next(int32_t d)                     /* the setlist: the file after (before) the one loaded */
{
    int32_t i = (int32_t)(lib_cur != LIB_NONE ? lib_cur : lib_sel) + d;
    if (!lib_n) { status_msg("LIBRARY EMPTY"); return; }
    if (lib_cur == LIB_NONE && d > 0) i = lib_sel;
    if (i < 0 || i >= (int32_t)lib_n) { status_msg(d > 0 ? "END OF THE LIST" : "START OF THE LIST"); return; }
    lib_load((uint8_t)i);
}

static void lib_save(int32_t over)                  /* over: a file of the list (asks twice), -1: a new file */
{
    if (playing) { status_msg("SAVE: STOP FIRST"); return; }
    if (over >= 0) {
        if (over >= (int32_t)lib_n) return;
        if (!(lib_ask_over && !time_due(fm1_ms, lib_ask_until))) {
            lib_ask_over = 1u; lib_ask_until = fm1_ms + SQ_ASK_MS;
            lib_toast("SAVE OVER? AGAIN: ", (uint8_t)over);
            grid_dirty = 1u;
            return;
        }
    }
    lib_ask_over = 0u;
    lib_send(SX_LIB_SAVE, over >= 0 ? over : 0x3FFF);
    sx_export(-1);
    grid_dirty = 1u;
}

static void lib_answer_in(const uint8_t *p, uint32_t n)
{
    uint32_t idx;
    if (n < 3u) return;
    idx = sx_get7(p + 1, 2u);
    switch (p[0]) {
    case 0u:  status_msg("SAVED ON THE PI"); lib_send(SX_LIB_LIST, 0); break;      /* (the list again: a new name) */
    case 1u:  status_msg("THE PI COULD NOT SAVE"); break;
    case 2u:  status_msg("NO SUCH FILE ON THE PI"); lib_loading = LIB_NONE; break;
    default:  status_msg("THE PI COULD NOT READ IT"); lib_loading = LIB_NONE; break;
    }
    (void)idx;
    grid_dirty = 1u;
}

static void snap_pi(uint8_t cmd, uint8_t n)
{
    uint8_t *q = sx_head(cmd);
    *q++ = (uint8_t)(n & 127u);
    sx_put7(&q, project.id, 5u);
    *q++ = playing ? 1u : 0u;
    *q++ = 0xF7u;
    sysex_send(sx_out, (uint32_t)(q - sx_out));
}

static void snap_answer_in(const uint8_t *p, uint32_t n)
{
    char *q = msg_buf;
    if (n < 2u) return;
    switch (p[0]) {
    case 0u:  q = put_s(q, "PI KEPT THE PATCHES OF "); q = put_u(q, p[1]); q = put_s(q, p[1] == 1u ? " SYNTH" : " SYNTHS"); break;
    case 1u:  q = put_s(q, "PI: NO SYNTH SENT A PATCH"); break;
    default:  q = put_s(q, "PI SENT THE PATCHES TO "); q = put_u(q, p[1]); q = put_s(q, p[1] == 1u ? " SYNTH" : " SYNTHS"); break;
    }
    finish(q);
    status_msg(msg_buf);
}

static void link_sysex_in(uint8_t cmd, const uint8_t *p, uint32_t n);   /* sagga_link.c: 0.15 */
/* a SysEx frame for the app (between F0 and F7, first byte 7D): platform.c / tests/host.c call this */
static void app_sysex(const uint8_t *p, uint32_t n)
{
    if (n < 4u || p[0] != 0x7Du || p[1] != 0x53u || p[2] != 0x47u) return;
    switch (p[3]) {
    case SX_EXPORT: sx_export(n > 4u && p[4] < SQ_SLOTS ? (int32_t)p[4] : -1); break;
    case SX_DATA:   sx_import_chunk(p + 4, n - 4u); break;
    case SX_END:    sx_import_end(p + 4, n - 4u); break;
    case SX_LIB_ENTRY:  lib_entry_in(p + 4, n - 4u); break;
    case SX_LIB_ANSWER: lib_answer_in(p + 4, n - 4u); break;
    case SX_SNAP_ANSWER: snap_answer_in(p + 4, n - 4u); break;
    case 0x51u: case 0x54u: regia_sysex_in(p[3], p + 4, n - 4u); break;   /* 0.9 FRASE, REGIA LED (sagga_viaggio.c) */
    case 0x61u: case 0x63u: case 0x65u: pipat_in(p[3], p + 4, n - 4u); break;   /* 0.11 the Pi's patterns (sagga_pipat.c) */
    case 0x67u: case 0x69u: case 0x6Bu: piprog_in(p[3], p + 4, n - 4u); break;  /* 0.11 the Pi's progressions */
    case 0x70u: tst_sysex_in(p + 4, n - 4u); break;                             /* 0.11 the PC test (sagga_test.c) */
    case 0x30u: case 0x32u: link_sysex_in(p[3], p + 4, n - 4u); break;          /* 0.15 the Pi's editor (sagga_link.c) */
    default: break;
    }
}
