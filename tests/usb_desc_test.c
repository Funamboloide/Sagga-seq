/* SPDX-License-Identifier: GPL-3.0-only
 * SAGGA SEQ 0.8: the USB descriptors with one and with two MIDI ports (firmware/src/usb.c), checked on a computer:
 *   cc -Ifirmware/src -Ifirmware/hal tests/usb_desc_test.c -o build/usb_desc_test && build/usb_desc_test
 * One port: the bytes of CFG_DESC untouched. Two: a valid USB-MIDI 1.0 configuration with jacks 1-8, the MS header's
 * and the configuration's lengths right, both endpoints naming two embedded jacks, bcdDevice + 0.40. */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#define RING_PUBLISH() __asm__ volatile("" ::: "memory")
#define FELUCCA_OTA 1
static uint32_t ota_now_ms(void) { return 0; }
static void ota_idle(void) {}
#include "usb.c"

static int fails, checks;
static void check(int c, const char *what) { checks++; if (!c) { fails++; printf("  FAIL: %s\n", what); } }

static void parse(const uint8_t *d, uint16_t l, int ports)
{
    uint32_t i = 0, in_ms = 0, ms_at = 0, ms_len = 0, ms_sum = 0, jacks = 0, eps = 0, ok_chain = 1;
    uint8_t seen[16] = {0};
    check(d[0] == 9 && d[1] == 2 && (d[2] | d[3] << 8) == l, "configuration: wTotalLength = the bytes");
    while (i < l) {
        uint32_t bl = d[i], ty = d[i + 1];
        if (!bl || i + bl > l) { ok_chain = 0; break; }
        if (ty == 4) in_ms = d[i + 5] == 1 && d[i + 6] == 3;
        else if (ty == 2 || ty == 0x0B) in_ms = 0;
        if (in_ms) {
            if (ty == 0x24 && d[i + 2] == 1) { ms_at = i; ms_len = d[i + 5] | d[i + 6] << 8; }
            if (ty == 0x24 || ty == 5 || ty == 0x25) ms_sum += bl;
            if (ty == 0x24 && (d[i + 2] == 2 || d[i + 2] == 3)) { jacks++; if (d[i + 4] < 16) seen[d[i + 4]] = 1; }
            if (ty == 0x24 && d[i + 2] == 3) check(d[i + 6] < 16 && seen[d[i + 6]], "an OUT jack's source is a jack described before");
            if (ty == 0x25) {
                uint32_t k;
                eps++;
                check(d[i + 3] == (uint32_t)ports && bl == 4u + (uint32_t)ports, "a CS endpoint names one embedded jack a port");
                for (k = 0; k < d[i + 3]; k++) check(d[i + 4 + k] < 16 && seen[d[i + 4 + k]], "the endpoint's jacks exist");
            }
        }
        i += bl;
    }
    check(ok_chain && i == l, "the descriptors chain to the end");
    check(ms_at && ms_len == ms_sum, "MS header wTotalLength = its descriptors and the endpoints'");
    check(jacks == 4u * (uint32_t)ports, "four jacks a port");
    check(eps == 2, "two CS endpoints");
}

int main(void)
{
    const uint8_t *d;
    uint16_t l;
    uint8_t dev1[18];
    get_desc(0x100, &d, &l); memcpy(dev1, d, 18);
    get_desc(0x200, &d, &l);
    check(d == CFG_DESC && l == sizeof CFG_DESC, "one port: CFG_DESC itself");
    parse(d, l, 1);
    usb_ports_set(2);
    get_desc(0x200, &d, &l);
    check(l == sizeof CFG_DESC + MIDI2_EXTRA, "two ports: 32 bytes more");
    parse(d, l, 2);
    get_desc(0x100, &d, &l);
    check(l == 18 && d[12] == (uint8_t)(dev1[12] + 0x40) && !memcmp(d, dev1, 12) && !memcmp(d + 13, dev1 + 13, 5), "two ports: bcdDevice + 0.40, the rest the same");
    usb_ports_set(1);
    get_desc(0x200, &d, &l);
    check(d == CFG_DESC, "back to one port: CFG_DESC again");
    get_desc(0x100, &d, &l);
    check(!memcmp(d, dev1, 18), "and the device descriptor as before");
    printf("usb descriptors: %d checks, %d failures\n", checks, fails);
    return fails != 0;
}
