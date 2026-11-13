/* SPDX-License-Identifier: GPL-3.0-only */
/* SAGGA HUB PC port: USB-MIDI event packets (4 bytes) carried over a UART as SLIP frames. Header only, no
 * dependencies: the RP2040 firmware (sagga_pc.c) and the host test (test_slip_midi.c) both use it; the Pi side is
 * tools/hub/usbmidi_pkt.py, the same rules. */
#ifndef SLIP_MIDI_H
#define SLIP_MIDI_H
#include <stdint.h>
#include <stddef.h>

#define SLIP_END 0xC0u
#define SLIP_ESC 0xDBu
#define SLIP_ESC_END 0xDCu
#define SLIP_ESC_ESC 0xDDu

/* MIDI bytes in a packet by its Code Index Number; 0 = not a valid packet (CIN 0 and 1 are reserved) */
static inline uint8_t usbmidi_cin_len(uint8_t cin)
{
    static const uint8_t L[16] = {0, 0, 2, 3, 3, 1, 2, 3, 3, 3, 3, 3, 2, 2, 3, 1};
    return L[cin & 15u];
}

/* a 4-byte packet -> SLIP bytes into out (at most 10); returns how many */
static inline size_t slip_encode_pkt(const uint8_t pkt[4], uint8_t *out)
{
    size_t n = 0, i;
    out[n++] = SLIP_END;
    for (i = 0; i < 4; i++) {
        uint8_t b = pkt[i];
        if (b == SLIP_END) { out[n++] = SLIP_ESC; out[n++] = SLIP_ESC_END; }
        else if (b == SLIP_ESC) { out[n++] = SLIP_ESC; out[n++] = SLIP_ESC_ESC; }
        else out[n++] = b;
    }
    out[n++] = SLIP_END;
    return n;
}

typedef struct { uint8_t buf[5]; uint8_t n; uint8_t esc; } slip_dec_t;

/* one byte in; 1 when a 4-byte packet with a valid CIN is complete in pkt */
static inline int slip_decode_byte(slip_dec_t *d, uint8_t b, uint8_t pkt[4])
{
    if (b == SLIP_END) {
        int ok = d->n == 4 && usbmidi_cin_len(d->buf[0] & 15u) != 0;
        if (ok) { pkt[0] = d->buf[0]; pkt[1] = d->buf[1]; pkt[2] = d->buf[2]; pkt[3] = d->buf[3]; }
        d->n = 0; d->esc = 0;
        return ok;
    }
    if (d->esc) {
        d->esc = 0;
        b = b == SLIP_ESC_END ? SLIP_END : b == SLIP_ESC_ESC ? SLIP_ESC : b;
    } else if (b == SLIP_ESC) {
        d->esc = 1;
        return 0;
    }
    if (d->n < 5) d->buf[d->n] = b;
    if (d->n < 5) d->n++;                                  /* (5 = too long: dropped at the END) */
    return 0;
}

#endif
