/* SPDX-License-Identifier: GPL-3.0-only */
/* A fake FM-1 on a computer: the app (firmware/src/dinghy.c) runs unchanged on it. platform.c includes
 * this file instead of the hardware when DINGHY_HOST is set. A script presses keys over time; out come
 * the screen (PPM, at the times SHOT asks) and the sound (WAV, as the FM-1 sends it over USB).
 *
 *   mkdir -p build/host
 *   cc -O2 -Wall -DDINGHY_HOST -Ifirmware/src -Ifirmware/gen -o build/host/dinghy firmware/src/dinghy.c
 *   build/host/dinghy build/host/dinghy        (-> build/host/dinghy.wav, build/host/dinghy-<ms>.ppm)
 *   build/host/dinghy OUT script.txt [FPS]    (your own script; with FPS: OUT-NNNNN.ppm, a frame every 1/FPS s:
 *                                             a film of your firmware, e.g. ffmpeg -r 30 -i OUT-%05d.ppm ...)
 *
 * Change SCRIPT below to try your own app. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

#ifndef APP_NAME
#define APP_NAME "DINGHY"
#endif
#ifndef APP_VER
#define APP_VER "0.0"
#endif
#define FS 44100u
#define HALF_FRAMES 256u

static volatile uint32_t fm1_ms;
static struct { uint32_t notes, buttons; } fm1_in;
static uint32_t host_edges;
static uint32_t fm1_input_edges(uint32_t *released) { uint32_t b = host_edges; host_edges = 0; *released = 0; return b; }
static uint32_t fm1_input_note_edges(void) { return 0; }   /* (the script sets fm1_in.notes) */
static int32_t host_enc[8];                                  /* the script turns encoders: "T enc ID DELTA" */
static int32_t fm1_enc_take(uint32_t e) { int32_t v = host_enc[e & 7u]; host_enc[e & 7u] = 0; return v; }
static volatile uint32_t fm1_knob = 512;                     /* the MASTER knob, 0..1023: "T knob VALUE" */
static volatile int32_t sq_batt_raw = 600;                   /* the battery divider, smoothed (ADC ch3): "T batt VALUE" */
static uint32_t host_usb_power = 1u;                         /* a USB host powers the FM-1: "T usbpower 0|1" */
static uint32_t host_tx_room = 64u;                          /* free slots of the USB MIDI output ring: "T txroom N" */
/* 0.22: the ring itself, as the FM-1 has it ("T ring": on, USB_MIDI_OUT_RING events; "T ring N": N; 0 = off as before): what the app sends waits in it,
 * the 2 kHz USB poll takes 16 events an IN packet (32 a millisecond when the host reads), the throttled senders see
 * its room (midi_tx_room: 64 less what waits, as on the FM-1), and what does not fit is DROPPED and said - the FM-1
 * only counts it (usb.tx_drop, DROPPED on the USB page). Without this no test could see a note lost in a burst */
static uint32_t host_ring_cap, host_ring_used, host_ring_max, host_ring_drops;
static uint32_t midi_tx_room(void)
{
    if (!host_ring_cap) return host_tx_room;
    return host_ring_used >= 64u ? 0u : 64u - host_ring_used;
}
static uint8_t host_led[41];                                 /* 0.12: the key LEDs as the firmware set them: 0 off, 1 glow, 2 lit ("T leds") */
static void fm1_led_key(uint32_t id, int on) { if (id < 41u) { if (on) host_led[id] = 2u; else if (host_led[id] == 2u) host_led[id] = 0u; } }
static void fm1_led_key_dim(uint32_t id, int on) { if (id < 41u) { if (on) { if (host_led[id] != 2u) host_led[id] = 1u; } else if (host_led[id] == 1u) host_led[id] = 0u; } }
static void host_leds_print(void)
{
    uint32_t k;
    printf("%6u ms  LEDS ", fm1_ms);
    for (k = 14; k < 41u; k++) putchar(host_led[k] == 2u ? 'X' : host_led[k] == 1u ? 'g' : '.');
    putchar(' ');                                              /* 0.12: then the 14 buttons (platform.c's order: OCT- OCT+ FX SEL ...) */
    for (k = 0; k < 14u; k++) putchar(host_led[k] == 2u ? 'X' : host_led[k] == 1u ? 'g' : '.');
    putchar('\n');
}

/* the screen: 240 x 240 RGB565, as the ST7789 gets it (gfx.c sends the bytes swapped) */
static uint16_t fb[240 * 240];
static void lcd_sync(void) {}
/* 0.22: a build for gcov (-DSAGGA_GCOV --coverage): a branch of a `fork` leaves through _exit, which writes no
 * counters; without this the explorer's gestures, which all run in branches, counted for nothing */
#ifdef SAGGA_GCOV
extern void __gcov_dump(void);
#define HOST_COV_DUMP() __gcov_dump()
#else
#define HOST_COV_DUMP() ((void)0)
#endif
/* "T lcdcost": from then on the screen costs what the SPI costs on the FM-1 (12 MHz, 16 bits a pixel, plus
 * ~60 us a transfer for the window commands): the time is added to the clock at the next platform_poll, as a
 * blocking redraw does on the real thing. Off by default, so the other tests keep their 1 ms per poll. */
static uint32_t host_lcd_cost, host_lcd_us, host_lcd_worst_us, host_max_dt, host_max_dt_erase, host_erase_pass;
/* 0.22: as the FM-1 does it: the pixels go out by themselves (DMA) while the loop goes on, and only the next access to
 * the panel waits for them (lcd_sync). host_lcd_until: the simulated microsecond the transfer in flight ends;
 * lcd_idle(): nothing in flight (the app starts a piece of the screen only then, so it never waits). A piece drawn
 * while another is in flight (the app until 0.21) costs the loop the rest of that one, as on the FM-1 */
static uint64_t host_lcd_until;
static uint64_t host_now_us(void) { return (uint64_t)fm1_ms * 1000u + host_lcd_us; }
static int lcd_idle(void) { return !host_lcd_cost || host_now_us() >= host_lcd_until; }
static void host_lcd_charge(uint32_t px)
{
    uint32_t us;
    uint64_t now;
    if (!host_lcd_cost) return;
    us = px * 4u / 3u;
    now = host_now_us();
    if (now < host_lcd_until) host_lcd_us += (uint32_t)(host_lcd_until - now);   /* (lcd_sync: the loop waits) */
    host_lcd_us += 60u;                                                          /* the window's commands, byte by byte */
    host_lcd_until = host_now_us() + us;
    if (us + 60u > host_lcd_worst_us) host_lcd_worst_us = us + 60u;
}
static void lcd_fill(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint16_t c)
{
    uint32_t i, j;
    host_lcd_charge(w * h);
    for (j = y; j < y + h && j < 240u; j++)
        for (i = x; i < x + w && i < 240u; i++)
            fb[j * 240u + i] = c;
}
static void lcd_blit(uint32_t x, uint32_t y, uint32_t w, uint32_t h, const uint16_t *px)
{
    uint32_t i, j;
    host_lcd_charge(w * h);
    for (j = 0; j < h; j++)
        for (i = 0; i < w; i++)
            if (x + i < 240u && y + j < 240u) {
                uint16_t c = px[j * w + i];
                fb[(y + j) * 240u + x + i] = (uint16_t)(c >> 8 | c << 8);
            }
}
#define CV_MAX (240u * 64u)
#include "gfx.c"

static uint8_t host_store[256 + 4];
static void host_store_path(char *out, size_t n)           /* the settings live beside the flash file (HOST_FLASH + ".cfg") */
{
    const char *path = getenv("HOST_FLASH");
    out[0] = 0;
    if (path && strlen(path) + 5 < n) { strcpy(out, path); strcat(out, ".cfg"); }
}
static int settings_load(void *p, uint32_t n)
{
    char path[512];
    FILE *f;
    const char *hs = getenv("HOST_SETTINGS");            /* 0.11: "PORTS,PROFILE", the FM-1's own (the PC test's replay) */
    if (hs) {
        unsigned ports = 1, prof = 0;
        if (sscanf(hs, "%u,%u", &ports, &prof) == 2 && n >= 3u) {
            memset(p, 0, n);
            ((uint8_t *)p)[0] = 2u; ((uint8_t *)p)[1] = (uint8_t)ports; ((uint8_t *)p)[2] = (uint8_t)prof;
            return 0;
        }
    }
    host_store_path(path, sizeof path);
    if (path[0] && (f = fopen(path, "rb"))) { size_t got = fread(host_store, 1, sizeof host_store, f); (void)got; fclose(f); }
    if (host_store[0] != 1 || n > 256u) return -1;
    memcpy(p, host_store + 4, n);
    return 0;
}
static int settings_save(const void *p, uint32_t n)
{
    char path[512];
    FILE *f;
    if (fl_app_lock) { printf("%6u ms  FLASH LOCKED: settings not saved\n", fm1_ms); return -1; }   /* (0.11: the PC test) */
    host_store[0] = 1;
    memcpy(host_store + 4, p, n);
    host_store_path(path, sizeof path);
    if (path[0] && (f = fopen(path, "wb"))) { fwrite(host_store, 1, sizeof host_store, f); fclose(f); }
    printf("%6u ms  settings saved (%u B)\n", fm1_ms, n);
    return 0;
}

/* the flash: 1 MB, 0xFF when erased. Programming only clears bits, so a write over a byte that was not erased fails, as
 * on a NOR; an erase costs the 45 ms the real one keeps the interrupts off, a page 0.7 ms. HOST_FLASH=file keeps it
 * between runs (loaded at start, written at the end): a power cycle. Only the project slots can be touched. */
static uint8_t flash_ok = 1;
static uint8_t host_flash[0x100000];
static uint32_t host_erases, host_programs;
static int host_flash_in(uint32_t off, uint32_t n)
{
    if (fl_app_lock) { printf("%6u ms  FLASH LOCKED: %06X not written\n", fm1_ms, off); return 0; }   /* (0.11: the PC test) */
    return off >= SQ_SLOT_BASE && off <= SQ_SLOT_END && n <= SQ_SLOT_END - off;
}
static int st_read(uint32_t off, void *dst, uint32_t n)
{
    if (off > sizeof host_flash || n > sizeof host_flash - off) return -1;
    memcpy(dst, host_flash + off, n);
    return 0;
}
static int fl_erase4k(uint32_t off, uint32_t *took_us)
{
    if (!host_flash_in(off, 0x1000u) || (off & 0xFFFu)) return -1;
    memset(host_flash + off, 0xFF, 0x1000u);
    *took_us = 45000u;
    host_lcd_us += 45000u;
    host_erases++;
    host_erase_pass = 1u;                       /* (the pass that erased is counted apart: the store erases only when stopped) */
    return 0;
}
static int fl_write(uint32_t off, const uint8_t *src, uint32_t n)
{
    uint32_t i;
    if (!host_flash_in(off, n)) return -1;
    for (i = 0; i < n; i++) {
        if ((uint8_t)(host_flash[off + i] & src[i]) != src[i]) return -5;      /* not erased */
        host_flash[off + i] = (uint8_t)(host_flash[off + i] & src[i]);
    }
    host_lcd_us += 700u * ((n + 255u) / 256u);
    host_programs++;
    return 0;
}
static void host_flash_save(void)
{
    const char *path = getenv("HOST_FLASH");
    FILE *f;
    if (!path || !(f = fopen(path, "wb"))) return;
    fwrite(host_flash, 1, sizeof host_flash, f);
    fclose(f);
}
static void host_flash_load(void)
{
    const char *path = getenv("HOST_FLASH");
    FILE *f;
    memset(host_flash, 0xFF, sizeof host_flash);
    if (path && (f = fopen(path, "rb"))) {
        size_t n = fread(host_flash, 1, sizeof host_flash, f);
        (void)n;
        fclose(f);
    }
}

static uint8_t mq[64][4];                  /* status, data 1, data 2, the cable (0.8: 1 = USB port 2) */
static uint32_t mq_w, mq_r;
static uint8_t host_rx_cable, host_usb_ports = 1u;
static int midi_get(uint8_t *st, uint8_t *d1, uint8_t *d2)
{
    if (mq_r == mq_w) return 0;
    *st = mq[mq_r % 64u][0]; *d1 = mq[mq_r % 64u][1]; *d2 = mq[mq_r % 64u][2]; host_rx_cable = mq[mq_r % 64u][3];
    mq_r++;
    return 1;
}
static uint8_t midi_cable(void) { return host_rx_cable; }
static void midi_send_c(uint32_t cable, uint32_t st, uint32_t d1, uint32_t d2)
{
    sq_midi_out_n++;
    if (cable >= host_usb_ports) cable = 0u;
    if (host_ring_cap) {
        if (host_ring_used >= host_ring_cap) {
            host_ring_drops++;
            printf("%6u ms  MIDI DROP %02X %u %u%s\n", fm1_ms, st, d1, d2, cable ? " port 2" : "");
            return;
        }
        if (++host_ring_used > host_ring_max) host_ring_max = host_ring_used;
    }
    printf("%6u ms  MIDI out %02X %u %u%s\n", fm1_ms, st, d1, d2, cable ? " port 2" : "");
}
static void midi_send(uint32_t st, uint32_t d1, uint32_t d2) { midi_send_c(0u, st, d1, d2); }

/* the USB numbers of the diagnostics page: a healthy link, the output ring as "txroom" sets it */
static uint32_t host_usb_reconnects;
static void usb_stats(sq_usb_stats_t *s)
{
    memset(s, 0, sizeof *s);
    s->up = 1; s->config = host_usb_power ? 1u : 0u;
    s->queued = host_ring_cap ? host_ring_used : 64u - (host_tx_room > 64u ? 64u : host_tx_room);
    s->dropped = host_ring_drops;
    s->resets = 1u + host_usb_reconnects;
}
static void usb_reconnect(void) { host_usb_reconnects++; printf("%6u ms  USB reconnect\n", fm1_ms); }
static void usb_set_ports(uint8_t n) { host_usb_ports = n; printf("%6u ms  USB ports %u\n", fm1_ms, n); }
#define USB_DIAG_N 13u
static void usb_diag(uint32_t d[USB_DIAG_N])         /* (0.20.9: the simulator's USB: enumerated once, at its start) */
{
    memset(d, 0, USB_DIAG_N * sizeof d[0]);
    d[0] = 1u; d[1] = 1u;
}

static void app_audio(int32_t *out, uint32_t n);
static void app_main(void);

/* SysEx: "T sx 7D 53 47 01" hands the app a frame (the bytes between F0 and F7), as platform.c does on the FM-1;
 * what the app sends is printed ("SYSEX out F0 ... F7"); "T sxdead 1" makes the sends fail (nobody reads) */
static void app_sysex(const uint8_t *p, uint32_t n);
static void app_host_dump(int t);          /* dinghy.c: a track's pattern, for the tests ("T dump TRACK") */
static void app_host_probe(void);          /* dinghy.c: the whole machine as key=value, for the explorer ("T probe") */
static void app_host_ui(void);             /* dinghy.c: the screen's text (0.12: "T ui"), lines and cells */
static void app_host_theory(int packed, int seed);   /* dinghy.c: 0.23 a band made by the THEORY engines */
static void app_host_scene(int s, int prog);         /* ... and a scene recalled (prog 0..3: with that progression of the player's) */
static void app_host_energy(int e);                  /* ... the machine's energy, at once */
static uint8_t host_sx[1u << 20];
static uint32_t host_sx_n, host_sx_dead;
static int sysex_send(const uint8_t *p, uint32_t n)
{
    uint32_t i;
    if (host_sx_dead) return -1;
    printf("%6u ms  SYSEX out", fm1_ms);
    for (i = 0; i < n; i++) printf(" %02X", p[i]);
    printf("%s\n", host_usb_ports > 1u ? " port 2" : "");
    return 0;
}
static int sysex_try_send(const uint8_t *p, uint32_t n) { return host_sx_dead ? -1 : sysex_send(p, n); }   /* (0.9: never waits) */

/* the script: at t ms, keys down (bit k = key k, 0 = F3), a button edge, a MIDI message. A script file (the second
 * argument) replaces it, a line each: "T keys MASK" (hex or decimal), "T btn ID", "T midi ST D1 D2", "T end" */
typedef struct { uint32_t t, keys; int btn; uint8_t st, d1, d2; int kind, a, b; uint8_t cab; } host_ev_t;   /* cab: 1 USB port 2, 255 the control port (the grid: port 2 with two) */
/* kind: 1 press, 2 release, 3 enc, 4 knob, 5 txroom, 6 shot, 7 lcdcost, 8 sx, 9 sxdead, 10 dump, 11 batt, 12 usbpower,
 * 13 fork, 14 branch, 15 endbranch, 16 join, 17 probe (the explorer: tests/sagga_explore.py)
 *
 * The explorer's branches: "T fork", then any number of "T branch NAME" ... "T2 endbranch" (events of a branch at times
 * from T on), then "join". At the fork the simulator copies itself (fork(2)) once a branch: each copy plays its branch
 * from the same moment, the same machine, and ends at its endbranch; the original waits for it, then the next. After the
 * join the original goes on as if no branch had happened. "T probe" prints the machine (app_host_probe). */
static const host_ev_t SCRIPT0[] = {
    {200, 1u << 7, -1, 0, 0, 0},                                /* C4 */
    {700, 1u << 7 | 1u << 11 | 1u << 14, -1, 0, 0, 0},          /* + E4 G4: a chord */
    {1500, 0, -1, 0, 0, 0},
    {1700, 0, -1, 0x90, 81, 120},                               /* MIDI in: A5 */
    {2300, 0, -1, 0x80, 81, 0},
    {2500, 0, BTN_OCT_UP, 0, 0, 0},
    {2700, 1u << 2 | 1u << 9, -1, 0, 0, 0},                     /* G4 + D5, an octave up */
    {3400, 0, -1, 0, 0, 0},
};
static const host_ev_t *script = SCRIPT0;
static uint32_t script_n = sizeof SCRIPT0 / sizeof SCRIPT0[0], end_ms = 6500, frame_fps;
static uint32_t host_child;                 /* this copy plays one branch of a fork (the explorer) */
static uint32_t host_nowav;                 /* HOST_NOWAV set: no sound rendered nor written, no screens unless asked */
static const uint32_t SHOT[] = {1000, 3000};

static void read_script(const char *path)
{
    static host_ev_t ev[65536];
    static char line[8192];
    char what[16];
    FILE *f = fopen(path, "r");
    uint32_t n = 0;
    if (!f) { perror(path); exit(1); }
    while (fgets(line, sizeof line, f) && n < 65536u) {
        host_ev_t e = {0, 0, -1, 0, 0, 0};
        unsigned a = 0, b = 0, c = 0;
        if (line[0] == '#' || sscanf(line, "%u %15s", &e.t, what) != 2) continue;
        if (!strcmp(what, "end")) { end_ms = e.t; continue; }
        if (!strcmp(what, "keys")) { sscanf(line, "%*u %*s %i", (int *)&e.keys); }
        else if (!strcmp(what, "btn")) { sscanf(line, "%*u %*s %d", &e.btn); }
        else if (!strcmp(what, "midi")) {                                                               /* "midi ST D1 D2 [PORT 1|2]" */
            unsigned port = 1;
            sscanf(line, "%*u %*s %i %u %u %u", (int *)&a, &b, &c, &port);
            e.st = (uint8_t)a; e.d1 = (uint8_t)b; e.d2 = (uint8_t)c; e.cab = port == 2u ? 1u : 0u;
        }
        else if (!strcmp(what, "press") || !strcmp(what, "release")) {      /* a button held down / let go */
            int id = 0; sscanf(line, "%*u %*s %d", &id); e.kind = what[0] == 'p' ? 1 : 2; e.a = id;
        }
        else if (!strcmp(what, "enc")) { int id = 0, d = 0; sscanf(line, "%*u %*s %d %d", &id, &d); e.kind = 3; e.a = id; e.b = d; }
        else if (!strcmp(what, "knob")) { int v = 512; sscanf(line, "%*u %*s %d", &v); e.kind = 4; e.a = v; }
        else if (!strcmp(what, "batt")) { int v = 600; sscanf(line, "%*u %*s %d", &v); e.kind = 11; e.a = v; }
        else if (!strcmp(what, "usbpower")) { int v = 1; sscanf(line, "%*u %*s %d", &v); e.kind = 12; e.a = v; }
        /* the SAGGA grid (docs/SAGGA-GRID.md): pad X Y VEL (VEL 0 = let go), ctl ID VEL, attach, detach */
        else if (!strcmp(what, "pad")) { sscanf(line, "%*u %*s %u %u %u", &a, &b, &c); if (sscanf(line, "%*u %*s %*u %*u %u", &c) != 1) c = 100u; e.st = 0x9F; e.d1 = (uint8_t)(b * 16u + a); e.d2 = (uint8_t)c; e.cab = 255u; }
        else if (!strcmp(what, "ctl")) { c = 127u; sscanf(line, "%*u %*s %u %u", &a, &c); e.st = 0xBE; e.d1 = (uint8_t)a; e.d2 = (uint8_t)c; e.cab = 255u; }
        else if (!strcmp(what, "hb")) { e.st = 0xBF; e.d1 = 118; e.d2 = 64; e.cab = 255u; }                           /* the bridge's keep-alive */
        else if (!strcmp(what, "txroom")) { int v = 64; sscanf(line, "%*u %*s %d", &v); e.kind = 5; e.a = v; }
        else if (!strcmp(what, "ring")) { int v = (int)USB_MIDI_OUT_RING; sscanf(line, "%*u %*s %d", &v); e.kind = 20; e.a = v; }   /* 0.22: the output ring: the FM-1's, or N events */
        else if (!strcmp(what, "lcdcost")) { e.kind = 7; }                                               /* charge the screen's SPI time */
        else if (!strcmp(what, "shot")) { e.kind = 6; }                                                  /* the screen, now */
        else if (!strcmp(what, "sx")) {                                                                  /* a SysEx frame for the app */
            char *q = strstr(line, "sx") + 2;
            unsigned v; int used;
            e.kind = 8; e.a = (int)host_sx_n; e.b = 0;
            while (sscanf(q, " %x%n", &v, &used) == 1 && host_sx_n < sizeof host_sx) { host_sx[host_sx_n++] = (uint8_t)v; e.b++; q += used; }
        }
        else if (!strcmp(what, "dump")) { int v = 0; sscanf(line, "%*u %*s %d", &v); e.kind = 10; e.a = v; }
        else if (!strcmp(what, "probe")) { e.kind = 17; }
        else if (!strcmp(what, "theory")) {          /* 0.23: STYLE SEED VAR VARY ENERGY PAT (STYLE: a genre 0..24, 25 FREE) */
            int st = 0, seed = 0, var = 0, vary = 0, en = 60, pat = 0;
            sscanf(line, "%*u %*s %d %d %d %d %d %d", &st, &seed, &var, &vary, &en, &pat);
            e.kind = 21; e.a = (st & 31) | (pat & 15) << 5 | (en & 127) << 9 | (vary & 127) << 16 | (var & 127) << 24; e.b = seed;
        }
        else if (!strcmp(what, "energy")) { int v = 50; sscanf(line, "%*u %*s %d", &v); e.kind = 23; e.a = v; }
        else if (!strcmp(what, "scene")) {           /* N [K]: scene N; K: with the player's progression K (0..3) */
            int v = 0, k = -1;
            sscanf(line, "%*u %*s %d %d", &v, &k);
            e.kind = 22; e.a = v; e.b = k;
        }
        else if (!strcmp(what, "ui")) { e.kind = 18; }                                                   /* the screen's text */
        else if (!strcmp(what, "leds")) { e.kind = 19; }                                                 /* the key LEDs: X lit, g glow */
        else if (!strcmp(what, "fork")) { e.kind = 13; }
        else if (!strcmp(what, "endbranch")) { e.kind = 15; }
        else if (!strcmp(what, "join")) { e.kind = 16; }
        else if (!strcmp(what, "branch")) {                                                              /* "T branch NAME" */
            char *q = strstr(line, "branch") + 6;
            size_t L;
            while (*q == ' ') q++;
            L = strcspn(q, "\r\n");
            e.kind = 14; e.a = (int)host_sx_n; e.b = (int)L;
            if (host_sx_n + L < sizeof host_sx) { memcpy(host_sx + host_sx_n, q, L); host_sx_n += (uint32_t)L; } else e.b = 0;
        }
        else if (!strcmp(what, "sxdead")) { int v = 1; sscanf(line, "%*u %*s %d", &v); e.kind = 9; e.a = v; }
        else if (!strcmp(what, "attach")) { e.st = 0xBF; e.d1 = 118; e.d2 = 127; e.cab = 255u; }
        else if (!strcmp(what, "detach")) { e.st = 0xBF; e.d1 = 118; e.d2 = 0; e.cab = 255u; }
        else continue;
        ev[n++] = e;
    }
    fclose(f);
    script = ev;
    script_n = n;
}

static const char *host_out = "build/host/dinghy";
static int16_t *wav;
static uint32_t wav_n, wav_cap;

static void write_ppm_as(const char *name)
{
    FILE *f;
    uint32_t i;
    if (!(f = fopen(name, "wb"))) { perror(name); exit(1); }
    fprintf(f, "P6 240 240 255\n");
    for (i = 0; i < 240u * 240u; i++) {
        uint16_t c = fb[i];
        fputc((c >> 11) * 255 / 31, f);
        fputc((c >> 5 & 63) * 255 / 63, f);
        fputc((c & 31) * 255 / 31, f);
    }
    fclose(f);
}
static void write_ppm(uint32_t t)
{
    char name[512];
    snprintf(name, sizeof name, "%s-%u.ppm", host_out, t);
    write_ppm_as(name);
    printf("%6u ms  screen -> %s\n", t, name);
}

static void write_wav(void)
{
    char name[512];
    FILE *f;
    uint32_t bytes = wav_n * 4u, v[] = {16, 0x00020001u, FS, FS * 4u, 0x00100004u};
    snprintf(name, sizeof name, "%s.wav", host_out);
    if (!(f = fopen(name, "wb"))) { perror(name); exit(1); }
    fwrite("RIFF", 1, 4, f); bytes += 36; fwrite(&bytes, 4, 1, f); bytes -= 36;
    fwrite("WAVEfmt ", 1, 8, f); fwrite(v, 4, 5, f);
    fwrite("data", 1, 4, f); fwrite(&bytes, 4, 1, f);
    fwrite(wav, 4, wav_n, f);
    fclose(f);
    printf("sound  -> %s (%u frames)\n", name, wav_n);
}

static void platform_poll(void)                 /* one call = one millisecond */
{
    static uint32_t step, shot, owed, frame;
    static int32_t blk[2u * HALF_FRAMES];
    uint32_t dt = 1u + host_lcd_us / 1000u;      /* 1 ms, plus the whole milliseconds the screen kept the loop busy */
    host_lcd_us %= 1000u;
    if (host_erase_pass) { if (dt > host_max_dt_erase) host_max_dt_erase = dt; }
    else if (dt > host_max_dt) host_max_dt = dt;
    host_erase_pass = 0u;
    fm1_ms += dt;
    host_ring_used -= host_ring_used < 32u * dt ? host_ring_used : 32u * dt;   /* (the USB poll, while the loop was busy) */
    while (step < script_n && script[step].t <= fm1_ms) {
        const host_ev_t *e = &script[step];
        if (e->kind == 13) {                    /* the explorer: a copy of the machine for each branch, one after the other */
            uint32_t j = step + 1u, join = step + 1u;
            while (join < script_n && script[join].kind != 16) join++;
            while (j < join) {
                uint32_t b = j, eb = j + 1u;
                pid_t pid;
                int st = 0;
                if (script[b].kind != 14) { j++; continue; }
                while (eb < join && script[eb].kind != 15 && script[eb].kind != 14) eb++;
                fflush(stdout);
                pid = fork();
                if (pid == 0) {
                    host_child = 1u;
                    printf("BRANCH %.*s\n", script[b].b, (const char *)host_sx + script[b].a);
                    script_n = eb;                              /* (this copy sees its branch only) */
                    end_ms = eb < join && script[eb].kind == 15 ? script[eb].t : fm1_ms + 1u;
                    step = b + 1u;
                    break;
                }
                if (pid > 0) {
                    waitpid(pid, &st, 0);
                    if (!WIFEXITED(st) || WEXITSTATUS(st)) printf("BRANCH-DIED %.*s %s %d\n", script[b].b, (const char *)host_sx + script[b].a,
                                                                  WIFSIGNALED(st) ? "signal" : "status", WIFSIGNALED(st) ? WTERMSIG(st) : WEXITSTATUS(st));
                    printf("BRANCH-END\n");
                } else printf("BRANCH-DIED fork failed\n");
                j = eb < join && script[eb].kind == 15 ? eb + 1u : eb;
            }
            if (host_child) continue;
            step = join < script_n ? join + 1u : join;          /* (the original: on after the join, as if nothing happened) */
            continue;
        }
        if (e->kind == 1) { fm1_in.buttons |= 1u << e->a; host_edges |= 1u << e->a; }
        else if (e->kind == 2) fm1_in.buttons &= ~(1u << e->a);
        else if (e->kind == 3) host_enc[e->a & 7] += e->b;
        else if (e->kind == 4) fm1_knob = (uint32_t)e->a;
        else if (e->kind == 5) host_tx_room = (uint32_t)e->a;
        else if (e->kind == 20) { host_ring_cap = (uint32_t)e->a; host_ring_used = 0u; }
        else if (e->kind == 6) write_ppm(fm1_ms);
        else if (e->kind == 7) host_lcd_cost = 1;
        else if (e->kind == 8) app_sysex(host_sx + e->a, (uint32_t)e->b);
        else if (e->kind == 10) app_host_dump(e->a);
        else if (e->kind == 17) app_host_probe();
        else if (e->kind == 21) app_host_theory(e->a, e->b);
        else if (e->kind == 22) app_host_scene(e->a, e->b);
        else if (e->kind == 23) app_host_energy(e->a);
        else if (e->kind == 18) app_host_ui();
        else if (e->kind == 19) host_leds_print();
        else if (e->kind >= 14 && e->kind <= 16) { }   /* (a branch's marks outside a fork: nothing) */
        else if (e->kind == 9) host_sx_dead = (uint32_t)e->a;
        else if (e->kind == 11) sq_batt_raw = e->a;
        else if (e->kind == 12) host_usb_power = (uint32_t)e->a;
        else if (e->st) {
            mq[mq_w % 64u][0] = e->st; mq[mq_w % 64u][1] = e->d1; mq[mq_w % 64u][2] = e->d2;
            mq[mq_w % 64u][3] = e->cab == 255u ? (host_usb_ports > 1u ? 1u : 0u) : e->cab;
            mq_w++;
        } else if (e->btn >= 0)
            host_edges |= 1u << e->btn;
        else
            fm1_in.notes = e->keys;
        step++;
    }
    if (host_child && fm1_ms >= end_ms) { fflush(stdout); HOST_COV_DUMP(); _exit(0); }   /* (a branch ends here: nothing written) */
    owed += FS * dt;                            /* the frames these milliseconds are worth, in blocks as the ISR renders */
    if (host_nowav) owed = 0u;                  /* (HOST_NOWAV: no sound kept, the explorer's speed) */
    while (owed >= 1000u * HALF_FRAMES) {
        uint32_t i;
        owed -= 1000u * HALF_FRAMES;
        memset(blk, 0, sizeof blk);
        app_audio(blk, HALF_FRAMES);
        if ((wav_n + HALF_FRAMES) > wav_cap) { wav_cap = 2u * wav_cap + 65536u; wav = realloc(wav, wav_cap * 4u); }   /* (grow by doubling) */
        for (i = 0; i < 2u * HALF_FRAMES; i++) {
            int32_t v = blk[i];                 /* (USB audio at the MASTER knob all the way up) */
            wav[2u * wav_n + i] = (int16_t)(v > 32767 ? 32767 : v < -32767 ? -32767 : v);
        }
        wav_n += HALF_FRAMES;
    }
    if (frame_fps) {                            /* a film: a frame every 1/fps s, as the screen is then */
        if ((uint64_t)frame * 1000u <= (uint64_t)fm1_ms * frame_fps) {
            char name[512];
            snprintf(name, sizeof name, "%s-%05u.ppm", host_out, frame++);
            write_ppm_as(name);
        }
    } else if (!host_nowav && shot < sizeof SHOT / sizeof SHOT[0] && fm1_ms == SHOT[shot])
        write_ppm(SHOT[shot++]);
    if (fm1_ms >= end_ms) {
        if (host_lcd_cost) printf("screen cost on: longest pass of the main loop %u ms, longest transfer %u us\n", host_max_dt, host_lcd_worst_us);
        if (host_erases) printf("flash: %u erases, %u writes, longest pass with an erase %u ms\n", host_erases, host_programs, host_max_dt_erase);
        if (host_ring_cap) printf("output ring of %u: the fullest %u, dropped %u\n", host_ring_cap, host_ring_max, host_ring_drops);
        if (!host_nowav) write_wav();
        host_flash_save();
        exit(0);
    }
}

/* 0.11 the PC test: HOST_TESTBOOT set = this run is the FM-1 after the test's reboot (what tst_noinit says on the real
 * one); its reboot ends the run */
static tst_noinit_t tst_noinit;
static void platform_test_reboot(void)
{
    printf("%6u ms  TEST REBOOT\n", fm1_ms);
    fflush(stdout);
    exit(0);
}

int main(int argc, char **argv)
{
    host_nowav = getenv("HOST_NOWAV") != 0;
    if (getenv("HOST_TESTBOOT")) { tst_noinit.magic = TST_MAGIC; tst_noinit.check = ~TST_MAGIC; tst_noinit.boots = (uint32_t)atoi(getenv("HOST_TESTBOOT")); }
    host_flash_load();
    if (argc > 1) host_out = argv[1];
    if (argc > 2) read_script(argv[2]);
    if (argc > 3) frame_fps = (uint32_t)atoi(argv[3]);
    app_main();
    return 0;
}

/* SAGGA SEQ host timing: the same time base as the FM-1 (hal/fm1_time.h). TIMER4 is a 24 MHz,
 * 32-bit counter, so fm1_ticks() wraps every 178.96 s and fm1_micros() = ticks / 24 wraps at
 * 2^32 / 24 us, NOT at 2^32 us. The old host stub (fm1_ms * 1000) wrapped at 2^32 and hid that. */
#define FM1_TICKS_PER_US 24u
static uint32_t fm1_ticks(void) { return (uint32_t)(fm1_ms * 24000u); }
static uint32_t fm1_micros(void) { return fm1_ticks() / FM1_TICKS_PER_US; }
