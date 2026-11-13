/* host test of slip_midi.h: cc -std=c11 -Wall -Wextra -Werror test_slip_midi.c -o t && ./t */
#include <stdio.h>
#include <string.h>
#include "slip_midi.h"
static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL %d: %s\n", __LINE__, #c); fails++; } } while (0)
int main(void)
{
    uint8_t out[16], pkt[4], i;
    slip_dec_t d = {{0}, 0, 0};
    const uint8_t p1[4] = {0x19, 0x90, 0x3C, 0x64};                  /* cable 1, note on */
    const uint8_t p2[4] = {0x04, 0xF0, SLIP_END, SLIP_ESC};          /* sysex bytes that need escaping */
    size_t n = slip_encode_pkt(p1, out);
    CHECK(n == 6 && out[0] == SLIP_END && out[5] == SLIP_END && out[1] == 0x19);
    int got = 0;
    for (i = 0; i < n; i++) got += slip_decode_byte(&d, out[i], pkt);
    CHECK(got == 1 && !memcmp(pkt, p1, 4));
    n = slip_encode_pkt(p2, out);
    CHECK(n == 8);
    got = 0;
    for (i = 0; i < n; i++) got += slip_decode_byte(&d, out[i], pkt);
    CHECK(got == 1 && !memcmp(pkt, p2, 4));
    /* garbage, then a good packet: only the good one comes out */
    const uint8_t junk[] = {0x12, 0x34, 0x56, SLIP_END, 0x01, 0x02, 0x03, 0x04, SLIP_END, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, SLIP_END};
    got = 0;
    for (i = 0; i < sizeof junk; i++) got += slip_decode_byte(&d, junk[i], pkt);
    CHECK(got == 0);                                                 /* CIN 0 is reserved; 5 bytes is too long */
    n = slip_encode_pkt(p1, out);
    got = 0;
    for (i = 0; i < n; i++) got += slip_decode_byte(&d, out[i], pkt);
    CHECK(got == 1);
    CHECK(usbmidi_cin_len(0xF) == 1 && usbmidi_cin_len(0xC) == 2 && usbmidi_cin_len(0x9) == 3 && usbmidi_cin_len(1) == 0);
    printf("slip_midi: %s\n", fails ? "FAILURES" : "ok");
    return fails ? 1 : 0;
}
