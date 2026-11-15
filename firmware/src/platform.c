/* SPDX-License-Identifier: GPL-3.0-only */
/* Dinghy's platform: everything an FM-1 firmware needs before it can be fun, taken unchanged from
 * SLOOP / Felucca / sloopDX and wired up here. You should not need to touch this file.
 *
 *   boot + boot guard   a firmware that crashes at boot falls back to the USB rescue, then to the ROM
 *   USB rescue          OCT- held at power-on: no audio, only the updater (the web installer still works)
 *   updater             the M-UPGRADE SysEx path: the web installer / the hub can always reach the FM-1
 *   USB-MIDI            in and out (midi_get, midi_send)
 *   USB audio           (off in SAGGA SEQ 0.4.1: the app is silent, so the FM-1 is a MIDI-only USB device)
 *   keys, knobs, LEDs   fm1_in.notes / buttons, fm1_input_edges, fm1_enc_take, fm1_led_key (hal/fm1_input.h)
 *   screen              240 x 240, lcd_fill, draw_text_box with FONT_S (16 px) / FONT_L (32 px) (gfx.c)
 *   settings            one 4 KiB flash sector with a CRC (settings_load / settings_save)
 *   crash screen        the PC of a fault, then a reboot
 *
 * The app (dinghy.c) includes this file first and supplies:
 *   static void app_audio(int32_t *out, uint32_t n)   audio ISR: n stereo frames, L R L R, Q15 (+-32767), out is zero
 *   static void app_main(void)                        never returns; calls platform_poll() often (every few ms)
 */
/* the panel by name: buttons (fm1_in.buttons, fm1_input_edges, fm1_led_key: bit / id), the encoders
 * (fm1_enc_take); the 27 note keys are fm1_in.notes bit 0 (F3) .. 26 (G5), LED id 14 + key */
enum { BTN_OCT_DOWN = 0, BTN_OCT_UP = 1, BTN_FX = 2, BTN_SEL = 3, BTN_ENV = 4, BTN_LFO = 5, BTN_EDIT = 6,
       BTN_GLO = 7, BTN_HOME = 8, BTN_SAVE = 9, BTN_ARP = 10, BTN_SEQ = 11, BTN_PLAY = 12, BTN_REC = 13 };
enum { ENC_SELECT = 0, ENC_ALGORITHM = 1, ENC_KNOB1 = 2, ENC_KNOB2 = 3, ENC_KNOB3 = 4, ENC_KNOB4 = 5, ENC_PRESETS = 6 };
#define KEY_LED(k) (14u + (k))

/* SAGGA SEQ: the project slots (sagga_store.c) live in nine 32 KB areas of the flash's data area (FL_DATA_LO..HI),
 * which this app does not otherwise use */
#define SQ_SLOT_BASE 0x00097000u
#define SQ_SLOT_END  0x000DF000u

#include <stdint.h>
/* SAGGA SEQ: what the USB link is doing, for the diagnostics page (HOME + SEL held): usb_stats(), and
 * usb_reconnect() (the host sees the cable pulled and plugged in again, without touching it) */
typedef struct {
    uint8_t up, config, suspended;
    uint32_t queued, wait_ms, wait_max_ms, dropped, resets, suspends, stalls, retries, rx_held, rx_bad;
} sq_usb_stats_t;
static uint32_t sq_midi_out_n;                  /* messages handed to midi_send since power-on */
/* SAGGA SEQ 0.11, the PC test (sagga_test.c): while it runs the slots and the settings are never written (fl_app_lock),
 * the MASTER knob is the PC's (tst_knob_on: fm1_knob = tst_knob_v), and what the test is lives across a reboot in
 * tst_noinit (RAM the start-up code does not clear; lost at a power-off). */
static uint8_t fl_app_lock, tst_knob_on;
static uint32_t tst_knob_v = 512u;
typedef struct { uint32_t magic, check, boots, fault_vec, fault_pc; } tst_noinit_t;
#define TST_MAGIC 0x54535431u                   /* "TST1"; check = its complement (RAM after a power-on is noise) */
static void platform_test_reboot(void);

#ifdef DINGHY_HOST
#include "../../tests/host.c"                  /* on a computer: a fake FM-1 (tests/host.c) */
#else
#include <stdint.h>
#include "fm1_time.h"
#include "fm1_sys.h"
#include "fm1_irq.h"
#include "fm1_guard.h"
#include "fm1_input.h"
#include "fm1_timer.h"
#include "fm1_lcd_hw.h"
#include "fm1_audio.h"
#include "fm1_adc.h"
#include "bootguard.h"

#ifndef APP_NAME
#define APP_NAME "DINGHY"
#endif
#ifndef FELUCCA_ID
#define FELUCCA_ID "FM-1_950"                   /* package identity: 95N = SAGGA SEQ 0.N (tools/build.py) */
#endif
#ifndef APP_VER
#define APP_VER "0.0"
#endif

bootguard_t bootguard __attribute__((section(".noinit")));
tst_noinit_t tst_noinit __attribute__((section(".noinit")));   /* 0.11: the PC test across its reboots */
static volatile uint32_t fm1_ms;                /* milliseconds since power-on (TIMER5) */

#define RING_PUBLISH() __asm__ volatile("" ::: "memory")
#include "libc.c"
#include "lcd.c"
#define CV_MAX (240u * 64u)                     /* the biggest text box drawn at once */
#include "gfx.c"

#define FS 44100u                               /* the sample rate */
#define HALF_FRAMES 256u                        /* I2S half buffer: 5.8 ms (as sloopDX: the USB audio band is set for it) */
#define HALF_WORDS (HALF_FRAMES * 2u)
#define FELUCCA_OTA 1
#define FELUCCA_CDC 0
#define FELUCCA_UAC 0                           /* SAGGA SEQ is silent: no USB audio input, MIDI only (0.4.1) */
#define FELUCCA_UART 1                          /* MIDI IN on the TRS jack (0.4.2; SLOOP's midi_uart.c) */
#include "usb.c"
#if FELUCCA_UART
#include "midi_uart.c"
#endif

/* ---- flash: read anywhere; erase / program only the update's staging area and the settings sector */
#define SETTINGS_AT 0x000FC000u                 /* one 4 KiB sector of Felucca's globals area */
#define FL_RANGE_OK(off, n) (FL_IN(off, n, FL_OTA_LO, FL_OTA_HI) || \
                             (!fl_app_lock && (FL_IN(off, n, SETTINGS_AT, SETTINGS_AT + 0x1000u) || FL_IN(off, n, SQ_SLOT_BASE, SQ_SLOT_END))))
#include "fm1_flash.h"
static uint8_t flash_ok;
static volatile int32_t sq_batt_raw;           /* the battery divider, smoothed (0: not read yet); the screen's battery */
static int st_read(uint32_t off, void *dst, uint32_t n)
{
    uint8_t *d = dst;
    while (n) {
        uint32_t k = n > 256u ? 256u : n, f = irq_save();
        int rc = FL_FAR(fl_read_ram)(off, d, k);
        irq_restore(f);
        if (rc)
            return rc;
        off += k;
        d += k;
        n -= k;
    }
    return 0;
}

static uint8_t recovery_active;
#define OTA_IDENTITY (recovery_active ? "FM-1_000" : FELUCCA_ID)
#include "ota.c"
/* SAGGA SEQ: SysEx frames whose first byte is 7D (non-commercial id) go to the app (sagga_store.c, the project
 * dump); the app answers with complete F0..F7 messages. The update protocol's frames start with 00: untouched. */
static void app_sysex(const uint8_t *p, uint32_t n);
static int sysex_send(const uint8_t *p, uint32_t n)   /* SAGGA SEQ 0.8: the app's SysEx on the control port (2 with two) */
{
    int rc;
    sx_tx_force = usb_midi_ports > 1u ? 1u : 0u;
    rc = ota_wire_send(p, n);
    sx_tx_force = 0xFFu;
    return rc;
}
/* 0.9: the same without waiting: -1 if the SysEx ring has no room for the whole frame now (the sequencer must never
 * wait for the host while it plays; the regista's messages are sent again at the next bar) */
static int sysex_try_send(const uint8_t *p, uint32_t n)
{
    uint32_t used = so_w - so_r, need = (n + 2u) / 3u + 1u;
    if (!*(volatile uint8_t *)&usb.config || used + need > SXQ) return -1;
    return sysex_send(p, n);
}
static void recovery_poll(void);
static uint32_t ota_now_ms(void) { return fm1_ms; }
static void ota_idle(void)
{
    fm1_wdt_feed();
    if (recovery_active) recovery_poll();
}
static int ota_in_area(uint32_t off, uint32_t n) { return FL_IN(off, n, OTA_AREA, OTA_AREA + OTA_AREA_LEN); }
static int ota_erase(uint32_t off)
{
    uint32_t took;
    if (!ota_in_area(off, 0x1000u) || (off & 0xFFFu))
        return -8;
    return fl_erase4k(off, &took);
}
static int ota_prog(uint32_t off, const void *p, uint32_t n)
{
    if (!ota_in_area(off, n))
        return -8;
    return fl_write(off, p, n);
}
static int ota_fread(uint32_t off, void *p, uint32_t n) { return st_read(off, p, n); }
static void ota_show(uint32_t step, int32_t code)
{
    static const char *const STEP[] = {"", "PACKAGE", "CHECK HEAD", "LOADER", "CONFIRM", "RESTART"};
    if (recovery_active) return;
    lcd_fill(0, 0, 240, 240, C_BLACK);
    draw_text_box(0, 92, 240, &FONT_S, "UPDATE", C_WHITE, 1);
    if (step < 9u)
        draw_text_box(0, 124, 240, &FONT_S, STEP[step < 6u ? step : 0], C_WHITE, 1);
    else
        draw_text_box(0, 124, 240, &FONT_S, code == 1 ? "DRY RUN OK" : "FAILED", C_WHITE, 1);
}
static void ota_commit(const uint8_t *parm)
{
    bootguard_clear(&bootguard);
    usb_detach();
    fm1_delay_ms(30);
    fm1_enter_update(parm);
}
#include "recovery.c"

/* ---- settings: [magic][length][crc32] then the bytes; settings_save erases the sector (~50 ms with
 * the interrupts off: the sound drops out), so save when nothing plays, not on every knob step */
#define SETTINGS_MAGIC 0x59474E44u              /* "DNGY" */
static uint32_t crc32(const uint8_t *p, uint32_t n)
{
    uint32_t c = 0xFFFFFFFFu, k;
    while (n--) {
        c ^= *p++;
        for (k = 0; k < 8u; k++)
            c = c & 1u ? (c >> 1) ^ 0xEDB88320u : c >> 1;
    }
    return ~c;
}
static int settings_load(void *p, uint32_t n)   /* 0: loaded; else p is untouched */
{
    static uint8_t buf[256];
    uint32_t h[3];
    if (!flash_ok || n > sizeof buf || st_read(SETTINGS_AT, h, sizeof h) || h[0] != SETTINGS_MAGIC || h[1] != n)
        return -1;
    if (st_read(SETTINGS_AT + sizeof h, buf, n) || crc32(buf, n) != h[2])
        return -1;
    memcpy(p, buf, n);
    return 0;
}
static int settings_save(const void *p, uint32_t n)   /* p in RAM, n <= 256 */
{
    uint32_t h[3] = {SETTINGS_MAGIC, n, 0}, took;
    int rc;
    if (!flash_ok || n > 256u)
        return -1;
    h[2] = crc32(p, n);
    if ((rc = fl_erase4k(SETTINGS_AT, &took)) != 0)
        return rc;
    if ((rc = fl_write(SETTINGS_AT + sizeof h, p, n)) != 0)
        return rc;
    return fl_write(SETTINGS_AT, (const uint8_t *)h, sizeof h);   /* the header last: a cut save stays invalid */
}

/* ---- MIDI over USB: 4-byte USB-MIDI packets. SAGGA SEQ 0.8: cable 0 (port 1), and cable 1 (port 2) when the
 * USB page asks for two ports; midi_cable() is the cable of the message midi_get gave last (15: the TRS jack) */
static uint8_t midi_rx_cable;
static int midi_get(uint8_t *st, uint8_t *d1, uint8_t *d2)   /* 1: a message (status, data 1, data 2) */
{
    uint32_t pk;
    if (mi_r == mi_w)
        return 0;
    pk = midi_in_q[mi_r % MQ];
    mi_r++;
    midi_rx_cable = (uint8_t)((pk >> 4) & 15u);
    *st = (uint8_t)(pk >> 8);
    *d1 = (uint8_t)(pk >> 16);
    *d2 = (uint8_t)(pk >> 24);
    return 1;
}
static uint8_t midi_cable(void) { return midi_rx_cable; }
static void midi_send_c(uint32_t cable, uint32_t st, uint32_t d1, uint32_t d2)   /* from the main loop only */
{
    /* the USB-MIDI code index: a channel message's own high nibble; system common by its length (Song Position
     * Pointer F2 has two data bytes: CIN 3; F1 / F3 one: CIN 2); the realtime bytes (F8 FA FB FC) CIN F, no data */
    uint32_t cin = st < 0xF0u ? st >> 4 : st == 0xF2u ? 3u : (st == 0xF1u || st == 0xF3u) ? 2u : 0xFu;
    sq_midi_out_n++;
    if (cin == 0xFu) d1 = d2 = 0u;
    else if (cin == 2u) d2 = 0u;
    if (cable >= usb_midi_ports) cable = 0u;
    midi_out_event(cin | (cable & 15u) << 4 | st << 8 | (d1 & 0x7Fu) << 16 | (d2 & 0x7Fu) << 24);
}
static void midi_send(uint32_t st, uint32_t d1, uint32_t d2) { midi_send_c(0u, st, d1, d2); }
static uint32_t midi_tx_room(void)                             /* free slots in the USB MIDI output ring */
{
    uint32_t used = mo_w - mo_r;
    return used >= MQ ? 0u : MQ - used;
}

/* ---- the timer: 10 kHz key scan, milliseconds, USB at 2 kHz. It outranks the audio ISR; nested in a
 * render it only scans, counts and feeds the USB audio stream (as sloopDX main.c) */
static volatile uint8_t in_audio;
void fm1_timer5_irq(void)
{
    static uint32_t sub, owed, last, acc;
    uint32_t t0 = fm1_ticks(), usb_due = sub % 5u == 0u;
    fm1_timer5_ack();
    fm1_input_tick();
    acc += t0 - last;
    last = t0;
    while (acc >= 1000u * FM1_TICKS_PER_US) {
        acc -= 1000u * FM1_TICKS_PER_US;
        fm1_ms++;
    }
    if (usb_due)
        owed = 1;
    if (++sub == 10u)
        sub = 0;
    if (in_audio) {
#if FELUCCA_UAC
        if (usb_due)
            uac_service();
#endif
        return;
    }
    if (owed) {
        usb_poll();
#if FELUCCA_UART
        uart_midi_poll();                       /* the TRS MIDI input, into the same ring as USB */
#endif
    }
    owed = 0;
}
extern void isr_timer5(void);

/* ---- the sound: ALNK0 I2S, two halves; the app renders, the MASTER knob scales, Q15 -> 24 bit (-6 dBFS ceiling) */
static int32_t abuf[2u * HALF_WORDS] __attribute__((aligned(4)));
static volatile int32_t master_q12 = 2048;
static volatile uint32_t fm1_knob = 512;       /* the MASTER knob, 0..1023, smoothed (SAGGA SEQ: the tempo) */
static void app_audio(int32_t *out, uint32_t n);
static void app_main(void);
static void app_usb_early(void);                /* the app's USB choices (dinghy.c: the settings), before usb_start */

void fm1_alnk0_irq(void)                       /* via isr_alnk0 (hal/fm1_isr.S) */
{
    uint8_t p;
    in_audio = 1;
    p = fm1_audio_pending();
    fm1_audio_ack_aux(p);
    if (p & FM1_AUDIO_HALF) {
        int32_t *o = &abuf[fm1_audio_free_half() * HALF_WORDS];
        uint32_t i, b;
        for (i = 0; i < HALF_WORDS; i++)
            o[i] = 0;
#if FELUCCA_UAC
        uac_render_start();
#endif
        app_audio(o, HALF_FRAMES);
        for (i = 0; i < HALF_WORDS; i++) {
            int32_t v = (o[i] * master_q12) >> 12;
            o[i] = v > 32767 ? 32767 : v < -32767 ? -32767 : v;
        }
#if FELUCCA_UAC
        for (b = 0; b < HALF_FRAMES; b += 32u)
            uac_tap(o + 2u * b, 32u);           /* the computer records what the speaker plays */
#else
        (void)b;
#endif
        for (i = 0; i < HALF_WORDS; i++)
            o[i] <<= 7;
        fm1_audio_ack_half();
    }
    in_audio = 0;
}
extern void isr_alnk0(void);

/* ---- SAGGA SEQ: the USB link's numbers, and a reconnect without pulling the cable */
static uint8_t usb_rc_pending;
static uint32_t usb_rc_at;
static void usb_stats(sq_usb_stats_t *s)
{
    s->up = usb.up; s->config = usb.config; s->suspended = usb.suspended;
    s->queued = mo_w - mo_r;
    s->wait_ms = usb.tx_wait / 2u;                  /* (polls at 2 kHz) */
    s->wait_max_ms = usb.tx_wait_max / 2u;
    s->dropped = usb.tx_drop;
    s->resets = usb.resets; s->suspends = usb.suspends; s->stalls = usb.frame_stalls; s->retries = usb.retries;
    s->rx_held = usb.rx_held; s->rx_bad = usb.rx_bad;
}
static void usb_set_ports(uint8_t n) { usb_ports_set(n); }   /* the next enumeration (usb.c) */
/* 0.20.9: the USB's own counters since the boot, for the test's DIAG (sagga_test.c says what each is) */
#define USB_DIAG_N 13u
static void usb_diag(uint32_t d[USB_DIAG_N])
{
    d[0] = usb.resets; d[1] = usb.configs; d[2] = usb.cfg_ms; d[3] = usb.suspends; d[4] = usb.retries;
    d[5] = usb.rx_pkts; d[6] = usb.rx_held; d[7] = usb.rx_bad; d[8] = usb.rx_xport; d[9] = usb.sx_missed;
    d[10] = usb.tx_pkts; d[11] = usb.tx_wait_max; d[12] = usb.tx_drop;
}
static void usb_reconnect(void)                     /* off now, on again in 0.4 s (platform_poll) */
{
    usb.detached = 1;                               /* (usb_retry leaves it alone meanwhile) */
    usb.up = 0;                                     /* the TIMER5 ISR stops touching the SIE first */
    fm1_usb_off();
    usb_rc_at = fm1_ms + 400u;
    usb_rc_pending = 1;
}

/* ---- the main loop's duties: watchdog, USB, the installer's update request, the MASTER knob */
static void platform_poll(void)
{
    static int32_t knob_avg = 512 * 16;
    int32_t a;
    fm1_wdt_feed();
    if (usb_rc_pending && (int32_t)(fm1_ms - usb_rc_at) >= 0) {
        usb_rc_pending = 0;
        usb.config = 0;
        usb.detached = 0;
        usb_start();                                /* the host enumerates the FM-1 again */
    }
    usb_retry(fm1_ms);
    if (sx_ready && sx_frame_len && sx_frame[0] == 0x7Du) {
        RING_PUBLISH();                         /* the frame only after the flag (as ota_frame_get) */
        app_sysex(sx_frame, sx_frame_len);
        ota_frame_done();
    }
    ota_service();
    if (usb.ota_req) {
        usb.ota_req = 0;
        if (flash_ok)
            ota_session();                      /* returns only if nothing was committed */
    }
    if (usb.uboot_req) {
        fm1_audio_stop();
        lcd_fill(0, 0, 240, 240, C_BLACK);
        draw_text_box(0, 110, 240, &FONT_S, "UBOOT (USB)", C_WHITE, 1);
        usb_detach();
        fm1_delay_ms(30);
        bootguard.pending = 0;
        fm1_enter_uboot();
    }
    if (fm1_ms >= 30000u && bootguard.pending)
        bootguard_clear(&bootguard);            /* 30 s up: this firmware boots */
    if ((a = fm1_adc_read(FM1_ADC_MASTER)) >= 0) {
        uint32_t k10;
        knob_avg += (a * 16 - knob_avg) / 8;
        k10 = (uint32_t)(knob_avg / 16);
        fm1_knob = tst_knob_on ? tst_knob_v : k10;     /* (0.11: the PC test turns it) */
        master_q12 = (int32_t)((k10 * k10) >> 8);
    }
    {   /* 0.5: the battery divider (ADC ch3, as Felucca reads it), five times a second, smoothed */
        static uint32_t batt_next;
        if ((int32_t)(fm1_ms - batt_next) >= 0) {
            batt_next = fm1_ms + 200u;
            if ((a = fm1_adc_read(FM1_ADC_BATT)) > 0) sq_batt_raw = sq_batt_raw ? sq_batt_raw + (a - sq_batt_raw) / 8 : a;
        }
    }
}

static void fm1_fault(const fm1_crash_t *c)
{
    char b[12];
    uint32_t i, t0, v[3] = {c->vec, c->pc, c->rets};
    fm1_audio_stop();
    if (tst_noinit.magic == TST_MAGIC && tst_noinit.check == ~TST_MAGIC) {   /* 0.11: the PC test is told after the reboot */
        tst_noinit.fault_vec = c->vec;
        tst_noinit.fault_pc = c->pc;
    }
    lcd_fill(0, 0, 240, 240, RGB(160, 0, 0));
    draw_text_box(0, 20, 240, &FONT_S, APP_NAME " CRASH", C_WHITE, 1);
    for (i = 0; i < 3u; i++) {
        uint32_t k;
        for (k = 0; k < 8u; k++) b[k] = "0123456789ABCDEF"[(v[i] >> (28u - 4u * k)) & 15u];
        b[8] = 0;
        draw_text_box(10, 60 + i * 20, 220, &FONT_S, b, C_WHITE, 0);
    }
    t0 = fm1_ticks();
    while ((uint32_t)(fm1_ticks() - t0) < 8000u * 1000u * FM1_TICKS_PER_US)
        fm1_wdt_feed();
    fm1_reboot();
}

/* 0.11 the PC test: off the USB, then a reboot that is not a failed boot (the guard counts only those) */
static void platform_test_reboot(void)
{
    fm1_audio_stop();
    usb_detach();
    fm1_delay_ms(30);
    bootguard_clear(&bootguard);
    fm1_reboot();
}

void fm1_cstart(void)
{
    extern uint32_t _data_start[], _data_end[], _data_load[], _bss_start[], _bss_end[];
    extern uint32_t _pool_start[], _pool_end[], _rt_start[], _rt_end[], _rt_load[];
    uint32_t *s, *d, p3, boot_mode;
    fm1_time_init();
    fm1_reset_reason();
    p3 = fm1_boot.p3_rst;
    fm1_wdt_arm(0x0D);
    if ((p3 & 1u) && !(p3 & (4u | 0x40u)))
        bootguard_clear(&bootguard);
    boot_mode = bootguard_begin(&bootguard);
    if (boot_mode == BOOT_ROM)
        fm1_enter_uboot();
    fm1_irq_init();
    for (d = _bss_start; d < _bss_end; d++) *d = 0;
    for (d = _pool_start; d < _pool_end; d++) *d = 0;
    for (s = _data_load, d = _data_start; d < _data_end; s++, d++) *d = *s;
    for (s = _rt_load, d = _rt_start; d < _rt_end; s++, d++) *d = *s;
    fm1_mailbox_clear();
    fm1_guard_enable(FM1_GUARD_STACK | FM1_GUARD_WRITE | FM1_GUARD_BUS | FM1_GUARD_PC);
    fm1_boot.p3_rst = (uint8_t)p3;
    if (boot_mode == BOOT_RECOVERY || recovery_key())
        recovery_main();                        /* OCT- at power-on: the USB rescue */
    flash_ok = FL_FAR(fl_jedec_ram)() == 0x856014u;
    ota_boot_cleanup();
    lcd_init();
    lcd_fill(0, 0, 240, 240, C_BLACK);
    fm1_input_init();
    fm1_adc_init();
    fm1_audio_init(abuf, HALF_WORDS, isr_alnk0, 3);   /* (abuf is zero: .bss) */
    app_usb_early();                            /* SAGGA SEQ 0.8: one or two MIDI ports, before the host looks */
    usb_start();
#if FELUCCA_UART
    uart_midi_init();                           /* (before TIMER5: PORTH read-modify-write) */
#endif
    fm1_timer5_start(isr_timer5, 4);
    fm1_guard_lock_top();
    fm1_irq_enable_all();
    app_main();
    for (;;)
        platform_poll();
}
#endif
