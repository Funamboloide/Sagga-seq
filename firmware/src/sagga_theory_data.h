/* SPDX-License-Identifier: GPL-3.0-only
 * SAGGA SEQ: the rules of the THEORY engines counted from the library, for the genres that have none written by
 * hand. MADE by tools/theory/gen_rules.py (which says what is counted): do not edit, run it again. The suite
 * checks that this file is what the library gives. 610 rhythm rules, 25 lines, 21 motifs, 24 chord parts, 21 genres. */
#ifndef SAGGA_THEORY_DATA_H
#define SAGGA_THEORY_DATA_H

#define TH_DATA_MID_E 25u    /* the energy the second half of what a family always plays comes in at */

/* a bit a genre: its arpeggios are the triad and the octave (no seventh in them) */
#define TH_DATA_ARP4 0x000A7300u

#define TH_DATA_RULES \
    /* HARDTECHNO KICK 1/2, variations 0,1,2,3,4,5,6: always X...X...X...X...  from energy 25 ....+.......+...  weights .........44..4f4 */ \
    {1, 0, 58, 0, 0x0101, 0, TW(0,0,0,0,0,0,0,0,0,4,4,0,0,4,15,4), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1010, 0x0000, TL(0x9929, 0x0101), 0}, \
    /* HARDTECHNO KICK 2/2, variations 7,8,9,10,11: always X..xX...X..xX..x  from energy 25 ...+.......+...+  weights .55....a..5..... */ \
    {1, 0, 42, 0, 0x1111, 0, TW(0,5,5,0,0,0,0,10,0,0,5,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x8808, 0x0000, TL(0x0101, 0x0129), 0}, \
    /* HARDTECHNO KICK 2/2, variations 7,8,9,10,11 (even bars): always X..xX...X..xX...  from energy 25 ...+.......+....  weights .55....a......af */ \
    {255, 0, 42, 0, 0x1111, 0, TW(0,5,5,0,0,0,0,10,0,0,0,0,0,0,10,15), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0808, 0x4000, TL(0x0101, 0x0129), 127}, \
    /* HARDTECHNO RUMBLE 1/4, variations 3,4,5,6,7,8: always .xxx.xxx.xxx.xxx  from energy 25 ..+...+...+...+.  weights ....4...4....... */ \
    {1, 18, 50, 0, 0xAAAA, 0, TW(0,0,0,0,4,0,0,0,4,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_AVOID | TH_K_LV, 0x4444, 0x0000, TL(0x0002, 0x0200), 0}, \
    /* HARDTECHNO RUMBLE 2/4, variations 0,1,2: always ..xx..xx..xx..xx  from energy 25 ...+...+...+...+  weights .1...1...1...1.. */ \
    {1, 18, 25, 0, 0x4444, 0, TW(0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_AVOID | TH_K_LV, 0x8888, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* HARDTECHNO RUMBLE 3/4, variations 9,10: always .x.x.x.x.x.x.x.x  from energy 25 .+...+...+...+..  weights ..1...d...1...1. */ \
    {1, 18, 17, 0, 0x8888, 0, TW(0,0,1,0,0,0,13,0,0,0,1,0,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_AVOID | TH_K_LV, 0x2222, 0x0000, TL(0x0000, 0x2000), 0}, \
    /* HARDTECHNO RUMBLE 4/4, variations 11: always ..x...x...x...x.  from energy 25 ..+.......+.....  weights .1.1.1.1.1.1.1.1 */ \
    {1, 18, 8, 0, 0x4040, 0, TW(0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_AVOID | TH_K_LV, 0x0404, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* HARDTECHNO CLAP 1/2, variations 0,1,2,3,4,5,6,7,8,9,10: always ....X.......X..x  from energy 25 ................  weights ..3....a36...33. */ \
    {1, 9, 92, 0, 0x9010, 0, TW(0,0,3,0,0,0,0,10,3,6,0,0,0,3,3,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x8000, TL(0x3D0C, 0x0130), 111}, \
    /* HARDTECHNO CLAP 2/2, variations 11: always ........X.......  from energy 25 ................  weights ................ */ \
    {1, 9, 8, 0, 0x0100, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0001, 0x0000), 0}, \
    /* HARDTECHNO HAT 1/4, variations 5,6,7,8,9,10: always ..xx..xx..xx..xx  from energy 25 ...+...+...+...+  weights 1...1...14..94.. */ \
    {1, 2, 50, 0, 0x4444, 0, TW(1,0,0,0,1,0,0,0,1,4,0,0,9,4,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x8888, 0x0000, TL(0x0A0E, 0x0202), 0}, \
    /* HARDTECHNO HAT 1/4, variations 5,6,7,8,9,10 (even bars): always ..xx..xx..xxxxxx  from energy 25 ...+...+...+++.+  weights 1...1d..1....... */ \
    {255, 2, 50, 0, 0x4444, 0, TW(1,0,0,0,1,13,0,0,1,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0xB888, 0x0000, TL(0x0002, 0x0E02), 0}, \
    /* HARDTECHNO HAT 2/4, variations 1,2,3,4: always x.x.x.x.x.x.x.x.  from energy 25 +...+...+...+...  weights ...1.1.6.1.1.6.6 */ \
    {1, 2, 33, 0, 0x4444, 0, TW(0,0,0,1,0,1,0,6,0,1,0,1,0,6,0,6), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1111, 0x4000, TL(0xCC88, 0xCC80), 111}, \
    /* HARDTECHNO HAT 3/4, variations 0: always ..X...X...X...X.  from energy 25 ......+.......+.  weights 1..111.11..111.1 */ \
    {1, 2, 8, 0, 0x0404, 0, TW(1,0,0,1,1,1,0,1,1,0,0,1,1,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4040, 0x0000, TL(0x9A92, 0x9E92), 0}, \
    /* HARDTECHNO HAT 4/4, variations 11: always xxxxxxxxxxxxxxxx  from energy 25 .+.+.+.+.+.+.+.+  weights ................ */ \
    {1, 2, 8, 0, 0x5555, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0xAAAA, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* HARDTECHNO HAT 4/4, variations 11 (even bars): always xxxxxxxxxxxxxxxx  from energy 25 ++..++..++......  weights ................ */ \
    {255, 2, 8, 0, 0xFCCC, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0333, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* HARDTECHNO OPEN HAT, variations 0,1,2,3,4,5: always ..x...x...x...x.  from energy 25 ..+.......+.....  weights .5.........5...5 */ \
    {1, 10, 0, 0, 0x4040, 0, TW(0,5,0,0,0,0,0,0,0,0,0,5,0,0,0,5), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0404, 0x4000, TL(0x00C0, 0x000C), 89}, \
    /* HARDTECHNO RIDE 1/3, variations 0,1: always x.x.x.x.x.x.x.x.  from energy 25 +...+...+...+...  weights ...1.1.1.1.1...1 */ \
    {1, 11, 33, 0, 0x4444, 0, TW(0,0,0,1,0,1,0,1,0,1,0,1,0,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1111, 0x0000, TL(0x808C, 0x8C80), 0}, \
    /* HARDTECHNO RIDE 2/3, variations 2,3: always x.oxx.oxx.oxx.ox  from energy 25 ...+...+...+...+  weights .....1...d...... */ \
    {1, 11, 33, 0, 0x5555, 0, TW(0,0,0,0,0,1,0,0,0,13,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x8888, 0x8000, TL(0x202C, 0x2C20), 96}, \
    /* HARDTECHNO RIDE 3/3, variations 4,5: always ..x...x...x...x.  from energy 25 ..+.......+.....  weights 1..11d.111.11..1 */ \
    {1, 11, 33, 0, 0x4040, 0, TW(1,0,0,1,1,13,0,1,1,1,0,1,1,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0404, 0x4000, TL(0x828E, 0x8E82), 96}, \
    /* HARDTECHNO PERC 1/4, variations 0,1,2,3,4: always ..x...x...x...x.  from energy 25 ..+.......+.....  weights 1a.1.5.5.1.511.5 */ \
    {1, 3, 42, 0, 0x4040, 0, TW(1,10,0,1,0,5,0,5,0,1,0,5,1,1,0,5), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0404, 0x0000, TL(0x8AC8, 0x8C8E), 0}, \
    /* HARDTECHNO PERC 2/4, variations 5,6,7,8: always ...x...x...x..xx  from energy 25 .......+...+....  weights 111..11..61.16.. */ \
    {1, 3, 33, 0, 0xC008, 0, TW(1,1,1,0,0,1,1,0,0,6,1,0,1,6,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0880, 0x8000, TL(0x0228, 0x282E), 85}, \
    /* HARDTECHNO PERC 3/4, variations 10,11: always x..x..x..x..x..x  from energy 25 +........+..+...  weights .11..d.1..11..1. */ \
    {1, 3, 17, 0, 0x8048, 0, TW(0,1,1,0,0,13,0,1,0,0,1,1,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x1201, 0x8000, TL(0x20A0, 0x882C), 96}, \
    /* HARDTECHNO PERC 4/4, variations 9: always .x.x.x.x.x.x.x.x  from energy 25 .+...+...+...+..  weights ..1...1...1...1. */ \
    {1, 3, 8, 0, 0x8888, 0, TW(0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x2222, 0x0000, TL(0x2020, 0x2020), 0}, \
    /* HARDTECHNO STAB 1/4, variations 0,4: always ........x.......  from energy 25 ................  weights d.d1.11...111.d. */ \
    {1, 21, 33, 0, 0x0100, 0, TW(13,0,13,1,0,1,1,0,0,0,1,1,1,0,13,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* HARDTECHNO STAB 2/4, variations 1,2: always x.....x.....x...  from energy 25 ................  weights ..1d....1.1...1. */ \
    {1, 21, 33, 0, 0x1041, 0, TW(0,0,1,13,0,0,0,0,1,0,1,0,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0080), 0}, \
    /* HARDTECHNO STAB 3/4, variations 3: always ...x.......x....  from energy 25 ................  weights 1.....1.1....... */ \
    {1, 21, 17, 0, 0x0808, 0, TW(1,0,0,0,0,0,1,0,1,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* HARDTECHNO STAB 4/4, variations 5: always ..x..x....x.....  from energy 25 ................  weights 1.......1...1... */ \
    {1, 21, 17, 0, 0x0424, 0, TW(1,0,0,0,0,0,0,0,1,0,0,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* HARDTECHNO LEAD 1/4, variations 1,2: always X.xx.xx.x.xx.xx.  from energy 25 ..++.+....++.++.  weights .1..1..1.1..1..d */ \
    {1, 24, 33, 0, 0x0141, 0, TW(0,1,0,0,1,0,0,1,0,1,0,0,1,0,0,13), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x6C2C, 0x0000, TL(0x8000, 0x0001), 0}, \
    /* HARDTECHNO LEAD 2/4, variations 4,5: always x.....x.x.......  from energy 25 ................  weights .11dd1.1.1111111 */ \
    {1, 24, 33, 0, 0x0141, 0, TW(0,1,1,13,13,1,0,1,0,1,1,1,1,1,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* HARDTECHNO LEAD 3/4, variations 0: always xxxxxxxxxxxxxxxx  from energy 25 .+..+..+.+..+..+  weights ................ */ \
    {1, 24, 17, 0, 0x6D6D, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x9292, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* HARDTECHNO LEAD 4/4, variations 3: always x.xx.x.xx.x.x.x.  from energy 25 .....+.+....+.+.  weights ....1.1....1.1.1 */ \
    {1, 24, 17, 0, 0x050D, 0, TW(0,0,0,0,1,0,1,0,0,0,0,1,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x50A0, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* DUB TECHNO KICK 1/2, variations 0,1,2,3,4,5,6,7,8,9: always X...X...X...X...  from energy 25 ....+.......+...  weights ...3.3.5.3.f...5 */ \
    {2, 0, 83, 0, 0x0101, 0, TW(0,0,0,3,0,3,0,5,0,3,0,15,0,0,0,5), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x1010, 0x0000, TL(0x0101, 0x4901), 0}, \
    /* DUB TECHNO KICK 1/2, variations 0,1,2,3,4,5,6,7,8,9 (even bars): always X.......X...X..x  from energy 25 ............+..+  weights ..3.a5.3........ */ \
    {255, 0, 83, 0, 0x0101, 0, TW(0,0,3,0,10,5,0,3,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x9000, 0x8000, TL(0x0101, 0x8101), 103}, \
    /* DUB TECHNO KICK 2/2, variations 10,11: always X.......X.......  from energy 25 ................  weights ..d............. */ \
    {2, 0, 17, 0, 0x0101, 0, TW(0,0,13,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0001, 0x0021), 0}, \
    /* DUB TECHNO RIM 1/4, variations 0,1,2,3,4,5: always ............x...  from energy 25 ................  weights ....9.9..9.....4 */ \
    {2, 15, 50, 0, 0x1000, 0, TW(0,0,0,0,9,0,9,0,0,9,0,0,0,0,0,4), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x1000, TL(0xC00C, 0x0000), 85}, \
    /* DUB TECHNO RIM 2/4, variations 6,7,8: always .............x..  from energy 25 ................  weights .......9...f.... */ \
    {2, 15, 25, 0, 0x2000, 0, TW(0,0,0,0,0,0,0,9,0,0,0,15,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x2000, TL(0x00C0, 0xC000), 106}, \
    /* DUB TECHNO RIM 3/4, variations 10,11: always ...x..........x.  from energy 25 ................  weights ......dd...d.... */ \
    {2, 15, 17, 0, 0x4008, 0, TW(0,0,0,0,0,0,13,13,0,0,0,13,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* DUB TECHNO RIM 4/4, variations 9: always ..x..x....x..x..  from energy 25 ..+..+....+.....  weights ................ */ \
    {2, 15, 8, 0, 0x2000, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0424, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* DUB TECHNO HAT 1/4, variations 4,5,6,7,8: always ..x..ox...x..ox.  from energy 25 .....+.......+..  weights .5.5...f...5...1 */ \
    {2, 2, 42, 0, 0x4444, 0, TW(0,5,0,5,0,0,0,15,0,0,0,5,0,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x2020, 0x4000, TL(0xC8C0, 0xC88C), 89}, \
    /* DUB TECHNO HAT 2/4, variations 0,1,2,3: always ..x...x...x...x.  from energy 25 ..+.......+.....  weights .6.1.1.1...6.6.d */ \
    {2, 2, 33, 0, 0x4040, 0, TW(0,6,0,1,0,1,0,1,0,0,0,6,0,6,0,13), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x0404, 0x0000, TL(0xC8C0, 0xC88C), 0}, \
    /* DUB TECHNO HAT 3/4, variations 9,10: always ..xo..Xo..xo..xx  from energy 25 ...+...+...+...+  weights .....1.......1.. */ \
    {2, 2, 17, 0, 0x4444, 0, TW(0,0,0,0,0,1,0,0,0,0,0,0,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x8888, 0x8000, TL(0x0880, 0x9880), 96}, \
    /* DUB TECHNO HAT 4/4, variations 11: always x.x.x.x.x.x.x.x.  from energy 25 +...+...+...+...  weights ...1.1.1...1.1.1 */ \
    {2, 2, 8, 0, 0x4444, 0, TW(0,0,0,1,0,1,0,1,0,0,0,1,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x1111, 0x0000, TL(0xC880, 0xC880), 0}, \
    /* DUB TECHNO SHAKER 1/2, variations 0,1,2,3,4: always xoxo.oxoxoxo.oxo  from energy 25 ++.+.+.+++.+.+.+  weights ....a.......a... */ \
    {2, 12, 83, 0, 0x4444, 0, TW(0,0,0,0,10,0,0,0,0,0,0,0,10,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0xABAB, 0x0000, TL(0x8888, 0x8888), 0}, \
    /* DUB TECHNO SHAKER 2/2, variations 5: always ..o...o...o...o.  from energy 25 ..+.......+.....  weights 11.111.111.111.1 */ \
    {2, 12, 17, 0, 0x4040, 0, TW(1,1,0,1,1,1,0,1,1,1,0,1,1,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0404, 0x0000, TL(0xAAAA, 0xAAAA), 0}, \
    /* DUB TECHNO PERC 1/4, variations 2,3: always ...o...o...o...o  from energy 25 .......+.......+  weights .11..11..d1..11. */ \
    {2, 3, 33, 0, 0x0808, 0, TW(0,1,1,0,0,1,1,0,0,13,1,0,0,1,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x8080, 0x0000, TL(0xACAC, 0xACAC), 0}, \
    /* DUB TECHNO PERC 1/4, variations 2,3 (even bars): always ...o...o.o.o...o  from energy 25 .......+.......+  weights .11..11...1..1d. */ \
    {255, 3, 33, 0, 0x0A08, 0, TW(0,1,1,0,0,1,1,0,0,0,1,0,0,1,13,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x8080, 0x0000, TL(0x8CA8, 0xACAC), 0}, \
    /* DUB TECHNO PERC 2/4, variations 4,5: always ......x.......x.  from energy 25 ................  weights .111.1.1.11d.1.1 */ \
    {2, 3, 33, 0, 0x4040, 0, TW(0,1,1,1,0,1,0,1,0,1,1,13,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x4000, TL(0x8CEC, 0x8CAC), 96}, \
    /* DUB TECHNO PERC 3/4, variations 0: always ..o.......o.....  from energy 25 ................  weights ...1..11.1.1..11 */ \
    {2, 3, 17, 0, 0x0404, 0, TW(0,0,0,1,0,0,1,1,0,1,0,1,0,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0xA0AC, 0xA0A0), 0}, \
    /* DUB TECHNO PERC 4/4, variations 1: always .g...g...g...g..  from energy 25 .....+.......+..  weights ...1..11...1..11 */ \
    {2, 3, 17, 0, 0x0202, 0, TW(0,0,0,1,0,0,1,1,0,0,0,1,0,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2020, 0x0000, TL(0xAC8C, 0xAC8C), 0}, \
    /* DUB TECHNO BASS 1/3, variations 2,3,4,5,6,7: always x..x....x..x....  from energy 25 ...+.......+....  weights ..1...1...1.441. */ \
    {2, 4, 50, 0, 0x0101, 0, TW(0,0,1,0,0,0,1,0,0,0,1,0,4,4,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0808, 0x0000, TL(0x0A00, 0x0000), 0}, \
    /* DUB TECHNO BASS 2/3, variations 8,9,10,11: always ..x...x...x...x.  from energy 25 ..+.......+.....  weights 16.1....1..1.... */ \
    {2, 4, 33, 0, 0x4040, 0, TW(1,6,0,1,0,0,0,0,1,0,0,1,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0404, 0x0000, TL(0x0000, 0x0008), 0}, \
    /* DUB TECHNO BASS 3/3, variations 0,1: always X.....x.x.......  from energy 25 ................  weights ..11.....d11..1. */ \
    {2, 4, 17, 0, 0x0141, 0, TW(0,0,1,1,0,0,0,0,0,13,1,1,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0008, 0x0001), 0}, \
    /* DUB TECHNO CHORD 1/2, variations 0,1,2,3,4,5,6: always ...x.......x....  from energy 25 ................  weights .44..1...41..1.. */ \
    {2, 5, 58, 0, 0x0808, 0, TW(0,4,4,0,0,1,0,0,0,4,1,0,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0008, 0x0028), 0}, \
    /* DUB TECHNO CHORD 2/2, variations 7,8,9,10,11: always ..x..x....x..x..  from energy 25 .....+.......+..  weights ...1..5....5.... */ \
    {2, 5, 42, 0, 0x0404, 0, TW(0,0,0,1,0,0,5,0,0,0,0,5,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2020, 0x0000, TL(0x0080, 0x2000), 0}, \
    /* DUB TECHNO PAD, variations 0,1,2,3,4,5: always x...............  from energy 25 ................  weights ......4.4....... */ \
    {2, 22, 0, 0, 0x0001, 0, TW(0,0,0,0,0,0,4,0,4,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* DUB TECHNO ARP 1/2, variations 2,3,4,5: always ..x...x...x...x.  from energy 25 ..+.......+.....  weights 1..616.11..61... */ \
    {2, 6, 67, 0, 0x4040, 0, TW(1,0,0,6,1,6,0,1,1,0,0,6,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0404, 0x0000, TL(0x0080, 0x8880), 0}, \
    /* DUB TECHNO ARP 2/2, variations 0,1: always x...x...x...x...  from energy 25 ....+.......+...  weights ..11.11d..11..1. */ \
    {2, 6, 33, 0, 0x0101, 0, TW(0,0,1,1,0,1,1,13,0,0,1,1,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1010, 0x0000, TL(0x0080, 0x8880), 0}, \
    /* UK GARAGE KICK, variations 0,1,2,3,4,5,6,7,8,9,10,11: always X.........X.....  from energy 25 ................  weights ...1.4.2....91.1 */ \
    {4, 0, 0, 0, 0x0401, 0, TW(0,0,0,1,0,4,0,2,0,0,0,0,9,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_PICK, TH_K_LV | TH_K_TWO, 0x0000, 0x0000, TL(0x8810, 0x0001), 0}, \
    /* UK GARAGE KICK, variations 0,1,2,3,4,5,6,7,8,9,10,11 (even bars): always X.........X.....  from energy 25 ................  weights ...6..2e11.....2 */ \
    {255, 0, 0, 0, 0x0401, 0, TW(0,0,0,6,0,0,2,14,1,1,0,0,0,0,0,2), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_PICK, TH_K_LV, 0x0000, 0x0000, TL(0x8014, 0x2001), 0}, \
    /* UK GARAGE SNARE 1/3, variations 0,1,2,3,10,11: always ....X.......X..g  from energy 25 ................  weights ...6...6.6...... */ \
    {4, 1, 50, 0, 0x9010, 0, TW(0,0,0,6,0,0,0,6,0,6,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0xC10C, 0xC180), 0}, \
    /* UK GARAGE SNARE 2/3, variations 6,7,8,9: always ....X......gX.g.  from energy 25 ...........+..+.  weights .6........6....6 */ \
    {4, 1, 33, 0, 0x1010, 0, TW(0,6,0,0,0,0,0,0,0,0,6,0,0,0,0,6), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4800, 0x0000, TL(0xB1F0, 0x0108), 0}, \
    /* UK GARAGE SNARE 3/3, variations 4,5: always ....X...g...X...  from energy 25 ................  weights .........d...d.. */ \
    {4, 1, 17, 0, 0x1110, 0, TW(0,0,0,0,0,0,0,0,0,13,0,0,0,13,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0D0F, 0x0100), 0}, \
    /* UK GARAGE HAT 1/4, variations 0,1,2,3: always ..x...x...x...x.  from energy 25 ..+.......+.....  weights .6.111.611.611.1 */ \
    {4, 2, 33, 0, 0x4040, 0, TW(0,6,0,1,1,1,0,6,1,1,0,6,1,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0404, 0x4000, TL(0x8ACA, 0xCA8C), 111}, \
    /* UK GARAGE HAT 2/4, variations 4,5,6,7: always ..x.x.xx..x.x.xx  from energy 25 ....+..+....+..+  weights .6.1.1..16.6.1.. */ \
    {4, 2, 33, 0, 0x4444, 0, TW(0,6,0,1,0,1,0,0,1,6,0,6,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x9090, 0x8000, TL(0x088E, 0x088C), 96}, \
    /* UK GARAGE HAT 3/4, variations 9,10,11: always .xxx.xxx.xxx.xxx  from energy 25 .+.+.+.+.+.+.+.+  weights ....1...9...1... */ \
    {4, 2, 25, 0, 0x4444, 0, TW(0,0,0,0,1,0,0,0,9,0,0,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0xAAAA, 0x0000, TL(0x0202, 0x0200), 0}, \
    /* UK GARAGE HAT 3/4, variations 9,10,11 (even bars): always ..xx.xxx.xxx.xxx  from energy 25 ...+.+.+.+.+.+.+  weights .f..1...9...9... */ \
    {255, 2, 25, 0, 0x4444, 0, TW(0,15,0,0,1,0,0,0,9,0,0,0,9,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0xAAA8, 0x8000, TL(0x0200, 0x0200), 127}, \
    /* UK GARAGE HAT 4/4, variations 8: always x.x.x.x.x.x.x.x.  from energy 25 +...+...+...+...  weights .1.1.1.1.1.1.1.1 */ \
    {4, 2, 8, 0, 0x4444, 0, TW(0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1111, 0x0000, TL(0x8888, 0x8888), 0}, \
    /* UK GARAGE OPEN HAT, variations 0,1,2,3,4,5: always ..X...x...X...x.  from energy 25 ..+.......+.....  weights .............6.6 */ \
    {4, 10, 0, 0, 0x4040, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,6,0,6), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0404, 0x0000, TL(0x0C10, 0x0010), 0}, \
    /* UK GARAGE SHAKER 1/2, variations 0,1,2: always xoxo.oxoxoxo.oxo  from energy 25 ++.+.+.+++.+.+.+  weights ....f.......f... */ \
    {4, 12, 50, 0, 0x4444, 0, TW(0,0,0,0,15,0,0,0,0,0,0,0,15,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0xABAB, 0x0000, TL(0x8888, 0x8888), 0}, \
    /* UK GARAGE SHAKER 2/2, variations 3,4,5: always ..o...o...o...o.  from energy 25 ..+.......+.....  weights 11.111.111.911.f */ \
    {4, 12, 50, 0, 0x4040, 0, TW(1,1,0,1,1,1,0,1,1,1,0,9,1,1,0,15), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0404, 0x0000, TL(0xEAEA, 0xAAAA), 0}, \
    /* UK GARAGE PERC 1/4, variations 0,1,2,3,4,5: always ...x..x....X....  from energy 25 ................  weights .11.....441..444 */ \
    {4, 3, 50, 0, 0x0848, 0, TW(0,1,1,0,0,0,0,0,4,4,1,0,0,4,4,4), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0000, 0x0000, TL(0xA86A, 0x002C), 0}, \
    /* UK GARAGE PERC 2/4, variations 6,7,8,9: always ......x..x....x.  from energy 25 ................  weights .611....1.16.1.6 */ \
    {4, 3, 33, 0, 0x4240, 0, TW(0,6,1,1,0,0,0,0,1,0,1,6,0,1,0,6), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0000, 0x4000, TL(0xC8A2, 0x00AC), 96}, \
    /* UK GARAGE PERC 3/4, variations 10: always ..x.....x.x.....  from energy 25 ................  weights ...1..1..1.1..11 */ \
    {4, 3, 8, 0, 0x0504, 0, TW(0,0,0,1,0,0,1,0,0,1,0,1,0,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0000, 0x0000, TL(0xE008, 0x2080), 0}, \
    /* UK GARAGE PERC 4/4, variations 11: always xgxgxgxgxgxgxgxg  from energy 25 +.+.+.+.+.+.+.+.  weights ................ */ \
    {4, 3, 8, 0, 0xAAAA, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x5555, 0x0000, TL(0xCCCC, 0xCCCC), 0}, \
    /* UK GARAGE BASS 1/2, variations 2,3,4,5,6,7,8,9,10,11: always x..x..x...x.x...  from energy 25 ...+........+...  weights .4.....4.4...4.. */ \
    {4, 4, 83, 0, 0x0441, 0, TW(0,4,0,0,0,0,0,4,0,4,0,0,0,4,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1008, 0x0000, TL(0x0808, 0x8008), 0}, \
    /* UK GARAGE BASS 2/2, variations 0,1: always x..x......x..x..  from energy 25 ...+.........+..  weights ......1.....1... */ \
    {4, 4, 17, 0, 0x0401, 0, TW(0,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2008, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* UK GARAGE CHORD 1/2, variations 0,1,2,3,4,5: always ..x....x..X.....  from energy 25 ................  weights 1..41.........1. */ \
    {4, 5, 50, 0, 0x0484, 0, TW(1,0,0,4,1,0,0,0,0,0,0,0,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0010, 0x0081), 0}, \
    /* UK GARAGE CHORD 2/2, variations 6,7,8,9,10,11: always X...x.....x...x.  from energy 25 ....+.........+.  weights ..1....1........ */ \
    {4, 5, 50, 0, 0x0401, 0, TW(0,0,1,0,0,0,0,1,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4010, 0x0000, TL(0x0000, 0x0001), 0}, \
    /* UK GARAGE VOX 1/2, variations 0,1,2,3: always ........x.x.....  from energy 25 ................  weights d.1d1.......116. */ \
    {4, 25, 67, 0, 0x0500, 0, TW(13,0,1,13,1,0,0,0,0,0,0,0,1,1,6,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x2800, 0x0001), 0}, \
    /* UK GARAGE VOX 2/2, variations 4,5: always ..x.x.......x...  from energy 25 ................  weights 1..1....1.1..d1. */ \
    {4, 25, 33, 0, 0x1014, 0, TW(1,0,0,1,0,0,0,0,1,0,1,0,0,13,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x2800, 0x0001), 0}, \
    /* UK GARAGE ARP 1/2, variations 0,1,2,3,4: always x.x.x.x.x.x.x.x.  from energy 25 ..+...+...+...+.  weights .1.1...1.5...1.1 */ \
    {4, 6, 83, 0, 0x1111, 0, TW(0,1,0,1,0,0,0,1,0,5,0,0,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4444, 0x0000, TL(0x0008, 0x0000), 0}, \
    /* UK GARAGE ARP 2/2, variations 5: always xx.xx.xx.xx.xx.x  from energy 25 .+.+...+.....+.+  weights ..1.....1.....1. */ \
    {4, 6, 17, 0, 0x1651, 0, TW(0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0xA08A, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* UK FUNKY KICK 1/3, variations 0,1,2,3,4,5,6: always X..x..X...X..x..  from energy 25 ...+.........+..  weights .4...4........4. */ \
    {5, 0, 58, 0, 0x0441, 0, TW(0,4,0,0,0,4,0,0,0,0,0,0,0,0,4,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2008, 0x0000, TL(0x2010, 0x1809), 0}, \
    /* UK FUNKY KICK 2/3, variations 7,8,9: always X..x...xX..x...x  from energy 25 .......+...+...+  weights .....9.......... */ \
    {5, 0, 25, 0, 0x0109, 0, TW(0,0,0,0,0,9,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x8880, 0x0000, TL(0x0001, 0x0801), 0}, \
    /* UK FUNKY KICK 2/3, variations 7,8,9 (even bars): always X..x..X...x..x..  from energy 25 ...+.........+..  weights .......f......9. */ \
    {255, 0, 25, 0, 0x0441, 0, TW(0,0,0,0,0,0,0,15,0,0,0,0,0,0,9,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x2008, 0x0000, TL(0x0000, 0x1001), 0}, \
    /* UK FUNKY KICK 3/3, variations 10,11: always X...X....x..X...  from energy 25 .........+..+...  weights .......d........ */ \
    {5, 0, 17, 0, 0x0011, 0, TW(0,0,0,0,0,0,0,13,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1200, 0x0000, TL(0x0100, 0x0101), 0}, \
    /* UK FUNKY SNARE 1/3, variations 0,1,2,3,4,5: always ....X..x.x..X...  from energy 25 .......+.+......  weights ...5.5.....a..5. */ \
    {5, 1, 50, 0, 0x1010, 0, TW(0,0,0,5,0,5,0,0,0,0,0,10,0,0,5,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0280, 0x0000, TL(0x21C0, 0x0DC0), 0}, \
    /* UK FUNKY SNARE 2/3, variations 8,9,10,11: always ......x.......x.  from energy 25 ................  weights .6......d......6 */ \
    {5, 1, 33, 0, 0x4040, 0, TW(0,6,0,0,0,0,0,0,13,0,0,0,0,0,0,6), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x4000, TL(0xC003, 0x000C), 96}, \
    /* UK FUNKY SNARE 3/3, variations 6,7: always ...X..x.....x...  from energy 25 ................  weights ..d............. */ \
    {5, 1, 17, 0, 0x1048, 0, TW(0,0,13,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0060), 0}, \
    /* UK FUNKY HAT 1/4, variations 8,9,10,11: always ..x...X...x...x.  from energy 25 ..+.......+.....  weights 11.111..16.611.6 */ \
    {5, 2, 33, 0, 0x4040, 0, TW(1,1,0,1,1,1,0,0,1,6,0,6,1,1,0,6), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x0404, 0x0000, TL(0x8A8A, 0x1A8A), 0}, \
    /* UK FUNKY HAT 2/4, variations 0,1,2: always x.x.x.x.x.x.x.x.  from energy 25 +...+...+...+...  weights .1.9.9...1.1.1.. */ \
    {5, 2, 25, 0, 0x4444, 0, TW(0,1,0,9,0,9,0,0,0,1,0,1,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x1111, 0x4000, TL(0x0888, 0x08C8), 85}, \
    /* UK FUNKY HAT 3/4, variations 5,6,7: always x.xx.xx.x.xx.xx.  from energy 25 +..+.+..+..+.+..  weights .f..1..9.1..1... */ \
    {5, 2, 25, 0, 0x4444, 0, TW(0,15,0,0,1,0,0,9,0,1,0,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x2929, 0x0000, TL(0x0208, 0xC208), 0}, \
    /* UK FUNKY HAT 4/4, variations 3,4: always xxx.xxx.xxx.xxx.  from energy 25 .+...+...+...+..  weights ...d.......1.... */ \
    {5, 2, 17, 0, 0x5555, 0, TW(0,0,0,13,0,0,0,0,0,0,0,1,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x2222, 0x4000, TL(0x0080, 0x00C0), 96}, \
    /* UK FUNKY RIM 1/3, variations 0,1,2: always ...x..........x.  from energy 25 ................  weights ......f9...f.... */ \
    {5, 15, 50, 0, 0x4008, 0, TW(0,0,0,0,0,0,15,9,0,0,0,15,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x4000, TL(0x0000, 0x0000), 85}, \
    /* UK FUNKY RIM 2/3, variations 3,4: always ......x.....x...  from energy 25 ................  weights ...........d.... */ \
    {5, 15, 33, 0, 0x1040, 0, TW(0,0,0,0,0,0,0,0,0,0,0,13,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x1000, TL(0x00C0, 0x0000), 96}, \
    /* UK FUNKY RIM 3/3, variations 5: always ..x..x....x..x..  from energy 25 .....+.......+..  weights ................ */ \
    {5, 15, 17, 0, 0x0404, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2020, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* UK FUNKY CONGA 1/4, variations 4,5,6,7,8: always ...x..x....x.xx.  from energy 25 ...........+.+..  weights 151.15.5151.1..1 */ \
    {5, 13, 42, 0, 0x4048, 0, TW(1,5,1,0,1,5,0,5,1,5,1,0,1,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x2800, 0x4000, TL(0x822E, 0xCE2E), 115}, \
    /* UK FUNKY CONGA 2/4, variations 9,10,11: always ..o.x..x..o...x.  from energy 25 ....+..+........  weights 1..1..1.1..1f1.9 */ \
    {5, 13, 25, 0, 0x4404, 0, TW(1,0,0,1,0,0,1,0,1,0,0,1,15,1,0,9), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0090, 0x4000, TL(0xC8A2, 0x20A2), 85}, \
    /* UK FUNKY CONGA 3/4, variations 0,1: always x..x..x...x.x..x  from energy 25 ..........+.+..+  weights ..1.1..1d..1.11. */ \
    {5, 13, 17, 0, 0x0049, 0, TW(0,0,1,0,1,0,0,1,13,0,0,1,0,1,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x9400, 0x0000, TL(0x2882, 0x8220), 0}, \
    /* UK FUNKY CONGA 4/4, variations 2,3: always x.xx..x.x.xx..x.  from energy 25 ..+.....+.++....  weights ....1..1....11.1 */ \
    {5, 13, 17, 0, 0x4049, 0, TW(0,0,0,0,1,0,0,1,0,0,0,0,1,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0D04, 0x0000, TL(0x8A00, 0x8200), 0}, \
    /* UK FUNKY PERC 1/4, variations 0,1,2,3: always x..x..X...x.x...  from energy 25 +..+............  weights .16.11.611...116 */ \
    {5, 3, 33, 0, 0x1440, 0, TW(0,1,6,0,1,1,0,6,1,1,0,0,0,1,1,6), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0009, 0x0000, TL(0xA80A, 0xDA28), 0}, \
    /* UK FUNKY PERC 2/4, variations 4,5,6: always x.x..x.x..x.x...  from energy 25 ..+..+.+........  weights .1.11.1.1....1.f */ \
    {5, 3, 25, 0, 0x1401, 0, TW(0,1,0,1,1,0,1,0,1,0,0,0,0,1,0,15), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x00A4, 0x0000, TL(0x0802, 0x2288), 0}, \
    /* UK FUNKY PERC 2/4, variations 4,5,6 (even bars): always x.x..x.x..x.x..x  from energy 25 .....+.+.......+  weights .1.19.1.1..9.f.. */ \
    {255, 3, 25, 0, 0x1405, 0, TW(0,1,0,1,9,0,1,0,1,0,0,9,0,15,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x80A0, 0x0000, TL(0x00C2, 0x2288), 0}, \
    /* UK FUNKY PERC 3/4, variations 7,8,9: always ..x.x...x.x..x..  from energy 25 ........+....+..  weights 19.9.111....1..1 */ \
    {5, 3, 25, 0, 0x0414, 0, TW(1,9,0,9,0,1,1,1,0,0,0,0,1,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2100, 0x2000, TL(0x8200, 0xA8CE), 106}, \
    /* UK FUNKY PERC 4/4, variations 10,11: always .x..X.x..x..x.x.  from energy 25 .+.......+....+.  weights 1.11.1.11.d..1.1 */ \
    {5, 3, 17, 0, 0x1050, 0, TW(1,0,1,1,0,1,0,1,1,0,13,0,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4202, 0x0000, TL(0x8822, 0x89A2), 0}, \
    /* UK FUNKY TOM 1/3, variations 1,2,3,4: always ..............xx  from energy 25 ................  weights 1.....d...16d1.. */ \
    {5, 14, 67, 0, 0xC000, 0, TW(1,0,0,0,0,0,13,0,0,0,1,6,13,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0000, 0x8000, TL(0x08E0, 0x0002), 85}, \
    /* UK FUNKY TOM 1/3, variations 1,2,3,4 (even bars): always ..............xx  from energy 25 ................  weights 6.....d...16d1.. */ \
    {255, 14, 67, 0, 0xC000, 0, TW(6,0,0,0,0,0,13,0,0,0,1,6,13,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x08E0, 0x0000), 0}, \
    /* UK FUNKY TOM 2/3, variations 0: always ..........x..x..  from energy 25 ................  weights 1.....1.....1.11 */ \
    {5, 14, 17, 0, 0x2400, 0, TW(1,0,0,0,0,0,1,0,0,0,0,0,1,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0xA200, 0x2002), 0}, \
    /* UK FUNKY TOM 3/3, variations 5: always x.....x.....x...  from energy 25 ................  weights ..............11 */ \
    {5, 14, 17, 0, 0x1041, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0xA000, 0x0000), 0}, \
    /* UK FUNKY BASS 1/3, variations 0,1,2,3,4: always x..x..x...x..x..  from energy 25 ...+.........+..  weights ..1..1..1.....1. */ \
    {5, 4, 42, 0, 0x0441, 0, TW(0,0,1,0,0,1,0,0,1,0,0,0,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2008, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* UK FUNKY BASS 2/3, variations 8,9,10,11: always x.....x.x.....x.  from energy 25 ........+.....+.  weights ..1661...61..1.. */ \
    {5, 4, 33, 0, 0x0041, 0, TW(0,0,1,6,6,1,0,0,0,6,1,0,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4100, 0x0000, TL(0x0008, 0x0280), 0}, \
    /* UK FUNKY BASS 3/3, variations 5,6,7: always ..x..x....x..x..  from energy 25 ..+..+..........  weights 19.9..1.1.....1. */ \
    {5, 4, 25, 0, 0x2400, 0, TW(1,9,0,9,0,0,1,0,1,0,0,0,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0024, 0x0000, TL(0x0000, 0x0088), 0}, \
    /* UK FUNKY CHORD 1/2, variations 0,1,2,3,4,5,6,7,8,9: always ..x..x....x.....  from energy 25 ................  weights 33.1....1..36... */ \
    {5, 5, 83, 0, 0x0424, 0, TW(3,3,0,1,0,0,0,0,1,0,0,3,6,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0280, 0x000A), 0}, \
    /* UK FUNKY CHORD 2/2, variations 10,11: always x..x....x..x....  from energy 25 ...+.......+....  weights ..1..1....1..... */ \
    {5, 5, 17, 0, 0x0101, 0, TW(0,0,1,0,0,1,0,0,0,0,1,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0808, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* UK FUNKY LEAD 1/4, variations 3,4,5: always x.....x.x.......  from energy 25 ................  weights ..1f91.1..11111. */ \
    {5, 24, 50, 0, 0x0141, 0, TW(0,0,1,15,9,1,0,1,0,0,1,1,1,1,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* UK FUNKY LEAD 2/4, variations 0: always x.xx.xx.x.xx.xx.  from energy 25 ..++.+....++.++.  weights ....1.......1... */ \
    {5, 24, 17, 0, 0x0141, 0, TW(0,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x6C2C, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* UK FUNKY LEAD 3/4, variations 1: always x.xx.x.xx.x.x.x.  from energy 25 .....+.+....+.+.  weights ....1.1......... */ \
    {5, 24, 17, 0, 0x050D, 0, TW(0,0,0,0,1,0,1,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x50A0, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* UK FUNKY LEAD 4/4, variations 2: always x.x.x.x.x.x.x.x.  from energy 25 ..+.+.....+.+.+.  weights ...1.1.......... */ \
    {5, 24, 17, 0, 0x0141, 0, TW(0,0,0,1,0,1,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x5414, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* GRIME KICK, variations 0,1,2,3,4,5,6,7,8,9,10,11: always X.........x.....  from energy 25 ................  weights ...4..b.b..2.4.2 */ \
    {6, 0, 0, 0, 0x0401, 0, TW(0,0,0,4,0,0,11,0,11,0,0,2,0,4,0,2), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0000, 0x0000, TL(0x8081, 0x0001), 0}, \
    /* GRIME KICK, variations 0,1,2,3,4,5,6,7,8,9,10,11 (even bars): always X.........x.....  from energy 25 ................  weights ...4..b....4.d92 */ \
    {255, 0, 0, 0, 0x0401, 0, TW(0,0,0,4,0,0,11,0,0,0,0,4,0,13,9,2), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0xA000, 0x0001), 0}, \
    /* GRIME SNARE 1/2, variations 0,1,2,3,4,5,6,7,8,9: always ........X.......  from energy 25 ................  weights ......3a..3d.338 */ \
    {6, 1, 83, 0, 0x0100, 0, TW(0,0,0,0,0,0,3,10,0,0,3,13,0,3,3,8), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x8000, TL(0x3831, 0xF000), 85}, \
    /* GRIME SNARE 2/2, variations 10,11: always ....X.......X...  from energy 25 ................  weights ..........d..d.. */ \
    {6, 1, 17, 0, 0x1010, 0, TW(0,0,0,0,0,0,0,0,0,0,13,0,0,13,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0D30, 0x0100), 0}, \
    /* GRIME HAT 1/3, variations 0,1,2,3,4,5: always x.x.x.x.x.x.x.x.  from energy 25 ..+...+...+...+.  weights .4.9.9.......d.. */ \
    {6, 2, 50, 0, 0x1111, 0, TW(0,4,0,9,0,9,0,0,0,0,0,0,0,13,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x4444, 0x4000, TL(0x0000, 0x008C), 96}, \
    /* GRIME HAT 2/3, variations 8,9,10,11: always ..x...x...X...x.  from energy 25 ......+.......+.  weights 1..611..16.611.. */ \
    {6, 2, 33, 0, 0x0404, 0, TW(1,0,0,6,1,1,0,0,1,6,0,6,1,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x4040, 0x0000, TL(0x0A9A, 0x0A82), 0}, \
    /* GRIME HAT 3/3, variations 6,7: always X...x...x...x...  from energy 25 ....+.......+...  weights ..11..1...1..1d. */ \
    {6, 2, 17, 0, 0x0101, 0, TW(0,0,1,1,0,0,1,0,0,0,1,0,0,1,13,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x1010, 0x0000, TL(0x2820, 0x20A1), 0}, \
    /* GRIME PERC 1/4, variations 3,4,5: always .......x.......x  from energy 25 ................  weights 1..1..1.1..9.99. */ \
    {6, 3, 50, 0, 0x8080, 0, TW(1,0,0,1,0,0,1,0,1,0,0,9,0,9,9,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0000, 0x0000, TL(0x0CC2, 0x2082), 0}, \
    /* GRIME PERC 1/4, variations 3,4,5 (even bars): always .......x.....x.x  from energy 25 ................  weights 1..9..1.1..1..1. */ \
    {255, 3, 50, 0, 0xA080, 0, TW(1,0,0,9,0,0,1,0,1,0,0,1,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x2082, 0x2002), 0}, \
    /* GRIME PERC 2/4, variations 0: always ......x.......x.  from energy 25 ................  weights ...1...1...1.1.1 */ \
    {6, 3, 17, 0, 0x4040, 0, TW(0,0,0,1,0,0,0,1,0,0,0,1,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x8880, 0x8080), 0}, \
    /* GRIME PERC 3/4, variations 1: always ...x.......x....  from energy 25 ................  weights ......11.....111 */ \
    {6, 3, 17, 0, 0x0808, 0, TW(0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0xA800, 0xA000), 0}, \
    /* GRIME PERC 4/4, variations 2: always x..x..x.x..x..x.  from energy 25 +.....+.+.....+.  weights .......1.....1.1 */ \
    {6, 3, 17, 0, 0x0808, 0, TW(0,0,0,0,0,0,0,1,0,0,0,0,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4141, 0x0000, TL(0x8800, 0x8000), 0}, \
    /* GRIME BASS 1/2, variations 0,1,2,3,4,5: always x.....x...x.....  from energy 25 ................  weights .5......15.1.5.. */ \
    {6, 4, 50, 0, 0x0441, 0, TW(0,5,0,0,0,0,0,0,1,5,0,1,0,5,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0809, 0x0008), 0}, \
    /* GRIME BASS 2/2, variations 6,7,8,9,10,11: always X.......X..x....  from energy 25 ................  weights ......1...1....4 */ \
    {6, 4, 50, 0, 0x0901, 0, TW(0,0,0,0,0,0,1,0,0,0,1,0,0,0,0,4), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x8001, 0x0001), 0}, \
    /* GRIME SUB, variations 0,1,2,3,4,5: always x...............  from energy 25 ................  weights ......4.9.f..... */ \
    {6, 19, 0, 0, 0x0001, 0, TW(0,0,0,0,0,0,4,0,9,0,15,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_WITH | TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* GRIME STAB 1/3, variations 0,1,2,3,4,5,6,7: always x.....x.....x...  from energy 25 ................  weights .414.1.1..14.47. */ \
    {6, 21, 67, 0, 0x1041, 0, TW(0,4,1,4,0,1,0,1,0,0,1,4,0,4,7,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x2890, 0x8008), 0}, \
    /* GRIME STAB 2/3, variations 8,9: always ...x.......X....  from energy 25 ................  weights 1.d...1.....1... */ \
    {6, 21, 17, 0, 0x0808, 0, TW(1,0,13,0,0,0,1,0,0,0,0,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0040, 0x0020), 0}, \
    /* GRIME STAB 3/3, variations 10,11: always ..x..x....X.....  from energy 25 ................  weights 1..1..1d...11... */ \
    {6, 21, 17, 0, 0x0424, 0, TW(1,0,0,1,0,0,1,13,0,0,0,1,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0050, 0x8000), 0}, \
    /* GRIME LEAD 1/4, variations 6,7,8,9,10,11: always x..x..x.x.......  from energy 25 ...+....+.......  weights .11.41.4..1.1414 */ \
    {6, 24, 50, 0, 0x0041, 0, TW(0,1,1,0,4,1,0,4,0,0,1,0,1,4,1,4), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0108, 0x0000, TL(0x8800, 0x8000), 0}, \
    /* GRIME LEAD 2/4, variations 1,2,3,4: always x.xx.x.xx.x.x.x.  from energy 25 .....+.+..+...+.  weights .6..1.6......6.1 */ \
    {6, 24, 33, 0, 0x110D, 0, TW(0,6,0,0,1,0,6,0,0,0,0,0,0,6,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x44A0, 0x0000, TL(0x0800, 0x2008), 0}, \
    /* GRIME LEAD 3/4, variations 0: always x.x.x.x.x.x.x.x.  from energy 25 ..+...+...+...+.  weights ...1.1.1.....1.. */ \
    {6, 24, 8, 0, 0x1111, 0, TW(0,0,0,1,0,1,0,1,0,0,0,0,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4444, 0x0000, TL(0x0800, 0x0000), 0}, \
    /* GRIME LEAD 4/4, variations 5: always xxxxxxxxxxxxxxxx  from energy 25 .+..+.+..+.+.+.+  weights ................ */ \
    {6, 24, 8, 0, 0x55AD, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0xAA52, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* JUNGLE KICK, variations 0,1,2,3,4,5,6,7,8,9,10,11: always X.........x.....  from energy 25 ................  weights .2b.....12..2..1 */ \
    {8, 0, 0, 0, 0x0401, 0, TW(0,2,11,0,0,0,0,0,1,2,0,0,2,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_PICK, TH_K_LV | TH_K_TWO, 0x0000, 0x0000, TL(0x8000, 0x0001), 0}, \
    /* JUNGLE KICK, variations 0,1,2,3,4,5,6,7,8,9,10,11 (even bars): always X.........X.....  from energy 25 ................  weights ..81..3....2f4.. */ \
    {255, 0, 0, 0, 0x0401, 0, TW(0,0,8,1,0,0,3,0,0,0,0,2,15,4,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_PICK, TH_K_LV, 0x0000, 0x0000, TL(0x0050, 0x0001), 0}, \
    /* JUNGLE SNARE 1/2, variations 0,6,7,8,9,10,11: always ....X.......X..x  from energy 25 ................  weights .....5.......... */ \
    {8, 1, 58, 0, 0x9010, 0, TW(0,0,0,0,0,5,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0000, 0x0000, TL(0x0100, 0x0D00), 0}, \
    /* JUNGLE SNARE 1/2, variations 0,6,7,8,9,10,11 (even bars): always ....X..x.g..X.g.  from energy 25 .......+......+.  weights .a.5.55........5 */ \
    {255, 1, 58, 0, 0x1210, 0, TW(0,10,0,5,0,5,5,0,0,0,0,0,0,0,0,5), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x4080, 0x0000, TL(0xF10C, 0x09C0), 0}, \
    /* JUNGLE SNARE 2/2, variations 1,2,3,4,5: always ....X..g.g..X...  from energy 25 .......+.+......  weights .5............5a */ \
    {8, 1, 42, 0, 0x1010, 0, TW(0,5,0,0,0,0,0,0,0,0,0,0,0,0,5,10), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0280, 0x0000, TL(0xC10C, 0xC10C), 0}, \
    /* JUNGLE SNARE 2/2, variations 1,2,3,4,5 (even bars): always g...X..g.g..X...  from energy 25 +......+........  weights ......5........a */ \
    {255, 1, 42, 0, 0x1210, 0, TW(0,0,0,0,0,0,5,0,0,0,0,0,0,0,0,10), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0081, 0x0000, TL(0x010C, 0xC103), 0}, \
    /* JUNGLE HAT 1/3, variations 3,4,5,6,7,8,9,10: always ..x...x...x...x.  from energy 25 ......+.......+.  weights 11.311.111.116.3 */ \
    {8, 2, 67, 0, 0x0404, 0, TW(1,1,0,3,1,1,0,1,1,1,0,1,1,6,0,3), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x4040, 0x0000, TL(0x828A, 0x8A0A), 0}, \
    /* JUNGLE HAT 1/3, variations 3,4,5,6,7,8,9,10 (even bars): always ..x...x...x.xxxx  from energy 25 ............++.+  weights 11.113.313.3.... */ \
    {255, 2, 67, 0, 0x4444, 0, TW(1,1,0,1,1,3,0,3,1,3,0,3,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0xB000, 0x8000, TL(0x0002, 0xCA8A), 100}, \
    /* JUNGLE HAT 2/3, variations 0,1,2: always x.x.x.x.x.x.x.x.  from energy 25 +...+...+...+...  weights .9.9.......9.1.1 */ \
    {8, 2, 25, 0, 0x4444, 0, TW(0,9,0,9,0,0,0,0,0,0,0,9,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1111, 0x4000, TL(0x8800, 0x000C), 85}, \
    /* JUNGLE HAT 3/3, variations 11: always xxxxxxxxxxxxxxxx  from energy 25 .+.+.+.+.+.+.+.+  weights ................ */ \
    {8, 2, 8, 0, 0x5555, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0xAAAA, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* JUNGLE RIDE 1/3, variations 0,1: always x.x.x.x.x.x.x.x.  from energy 25 +...+...+...+...  weights ...1.1.1...1...1 */ \
    {8, 11, 33, 0, 0x4444, 0, TW(0,0,0,1,0,1,0,1,0,0,0,1,0,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1111, 0x0000, TL(0x8080, 0x8C80), 0}, \
    /* JUNGLE RIDE 2/3, variations 2,3: always x.oxx.oxx.oxx.ox  from energy 25 ...+...+...+...+  weights .....d.......... */ \
    {8, 11, 33, 0, 0x5555, 0, TW(0,0,0,0,0,13,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x8888, 0x8000, TL(0x2020, 0x2C20), 96}, \
    /* JUNGLE RIDE 3/3, variations 4,5: always ..x...x...x...x.  from energy 25 ..+.......+.....  weights 1..11d.11..11..1 */ \
    {8, 11, 33, 0, 0x4040, 0, TW(1,0,0,1,1,13,0,1,1,0,0,1,1,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0404, 0x4000, TL(0x8282, 0x8E82), 96}, \
    /* JUNGLE PERC 1/4, variations 0,1,2,3: always ..x...x...x...x.  from energy 25 ..+.......+.....  weights 11.16..1.1.61d.1 */ \
    {8, 3, 33, 0, 0x4040, 0, TW(1,1,0,1,6,0,0,1,0,1,0,6,1,13,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0404, 0x0000, TL(0xCECC, 0xC28E), 0}, \
    /* JUNGLE PERC 2/4, variations 4,5,6,7: always .g..g..g.g..g..g  from energy 25 .+.....+.......+  weights 1.11..1.6.61.61. */ \
    {8, 3, 33, 0, 0x1210, 0, TW(1,0,1,1,0,0,1,0,6,0,6,1,0,6,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x8082, 0x0000, TL(0xEFAF, 0xE3AE), 0}, \
    /* JUNGLE PERC 3/4, variations 9,10,11: always x..x..x..x..x..x  from energy 25 +........+.....+  weights .91.1..9..1..11. */ \
    {8, 3, 25, 0, 0x1048, 0, TW(0,9,1,0,1,0,0,9,0,0,1,0,0,1,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x8201, 0x8000, TL(0x2C20, 0xC328), 85}, \
    /* JUNGLE PERC 4/4, variations 8: always ...x.......x....  from energy 25 ................  weights 111.1.11.11.1111 */ \
    {8, 3, 8, 0, 0x0808, 0, TW(1,1,1,0,1,0,1,1,0,1,1,0,1,1,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0000, 0x0000, TL(0xEE2C, 0xE32E), 0}, \
    /* JUNGLE SUB, variations 0,1,2,3,4,5,6,7,8,9,10,11: always x...............  from energy 25 ................  weights ......f.2.b..... */ \
    {8, 19, 0, 0, 0x0001, 0, TW(0,0,0,0,0,0,15,0,2,0,11,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_WITH | TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x8000, 0x0000), 0}, \
    /* JUNGLE BASS 1/2, variations 0,1,2,3,4,5,6,7,8: always x.......x.......  from energy 25 ................  weights ..3e..1...c36... */ \
    {8, 4, 75, 0, 0x0101, 0, TW(0,0,3,14,0,0,1,0,0,0,12,3,6,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x8280, 0x1020), 0}, \
    /* JUNGLE BASS 2/2, variations 9,10,11: always x.....X...x.....  from energy 25 ................  weights ...1....1....... */ \
    {8, 4, 25, 0, 0x0441, 0, TW(0,0,0,1,0,0,0,0,1,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x8000, 0x1000), 0}, \
    /* JUNGLE PAD, variations 0,1,2,3,4,5,6,7,8,9,10,11: always x...............  from energy 25 ................  weights ......2.d..2.... */ \
    {8, 22, 0, 0, 0x0001, 0, TW(0,0,0,0,0,0,2,0,13,0,0,2,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0080, 0x0000), 0}, \
    /* JUNGLE VOX 1/3, variations 1,2,3: always x.......x.x.....  from energy 25 ................  weights ..111..9...91.1. */ \
    {8, 25, 50, 0, 0x0501, 0, TW(0,0,1,1,1,0,0,9,0,0,0,9,1,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x2080, 0x8000), 0}, \
    /* JUNGLE VOX 2/3, variations 4,5: always ..x.x.......x...  from energy 25 ................  weights 1..1...11.11..d. */ \
    {8, 25, 33, 0, 0x1014, 0, TW(1,0,0,1,0,0,0,1,1,0,1,1,0,0,13,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x2080, 0x8000), 0}, \
    /* JUNGLE VOX 3/3, variations 0: always ...x......x.....  from energy 25 ................  weights 1.1.1...1...1... */ \
    {8, 25, 17, 0, 0x0408, 0, TW(1,0,1,0,1,0,0,0,1,0,0,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* JUNGLE ARP 1/2, variations 0,1,2: always x.x.x.x.x.x.x.x.  from energy 25 ..+...+...+...+.  weights .1.1.1.1.1.1.1.9 */ \
    {8, 6, 50, 0, 0x1111, 0, TW(0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,9), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4444, 0x0000, TL(0x8000, 0x0000), 0}, \
    /* JUNGLE ARP 2/2, variations 3,4,5: always xxxxxxxxxxxxxxxx  from energy 25 .+.+.+.+.+.+.+.+  weights ................ */ \
    {8, 6, 50, 0, 0x5555, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0xAAAA, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* BASSLINE KICK 1/2, variations 3,4,5,6,7,8,9,10: always X...X..x..X.X...  from energy 25 .......+..+.....  weights ...3.3.....3.... */ \
    {9, 0, 67, 0, 0x1011, 0, TW(0,0,0,3,0,3,0,0,0,0,0,3,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0480, 0x0000, TL(0x0110, 0x0901), 0}, \
    /* BASSLINE KICK 1/2, variations 3,4,5,6,7,8,9,10 (even bars): always X...X...X..xX.x.  from energy 25 ...........+..+.  weights .3...3.3.....3.. */ \
    {255, 0, 67, 0, 0x1111, 0, TW(0,3,0,0,0,3,0,3,0,0,0,0,0,3,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x4800, 0x4000, TL(0x0901, 0x8101), 111}, \
    /* BASSLINE KICK 2/2, variations 0,1,2,11: always X...X...X...X...  from energy 25 +.......+.......  weights ......66.......d */ \
    {9, 0, 33, 0, 0x1010, 0, TW(0,0,0,0,0,0,6,6,0,0,0,0,0,0,0,13), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0101, 0x0000, TL(0x4101, 0x2101), 0}, \
    /* BASSLINE SNARE 1/2, variations 0,1,6,7,8,9,10,11: always ....X.......X...  from energy 25 ................  weights ...........d.6ad */ \
    {9, 1, 67, 0, 0x1010, 0, TW(0,0,0,0,0,0,0,0,0,0,0,13,0,6,10,13), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0xFD00, 0x0100), 0}, \
    /* BASSLINE SNARE 2/2, variations 2,3,4,5: always ....X..g..g.X...  from energy 25 .......+..+.....  weights ........6..6.... */ \
    {9, 1, 33, 0, 0x1010, 0, TW(0,0,0,0,0,0,0,0,6,0,0,6,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0480, 0x0000, TL(0x01F3, 0xC100), 0}, \
    /* BASSLINE HAT 1/4, variations 7,8,9,10,11: always .xx..xx..xx..xx.  from energy 25 .+...+...+...+..  weights 1...1..11...1..1 */ \
    {9, 2, 42, 0, 0x4444, 0, TW(1,0,0,0,1,0,0,1,1,0,0,0,1,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x2222, 0x0000, TL(0x8202, 0x8202), 0}, \
    /* BASSLINE HAT 1/4, variations 7,8,9,10,11 (even bars): always .xx..xx..xx.xxxx  from energy 25 .+...+...+..++.+  weights 1...1..a1..f.... */ \
    {255, 2, 42, 0, 0x4444, 0, TW(1,0,0,0,1,0,0,10,1,0,0,15,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0xB222, 0x0000, TL(0x0082, 0x8202), 0}, \
    /* BASSLINE HAT 2/4, variations 1,2,3,4: always ..x.x.xx..x.x.xx  from energy 25 ....+..+....+..+  weights 16.6.1..11.6.1.. */ \
    {9, 2, 33, 0, 0x4444, 0, TW(1,6,0,6,0,1,0,0,1,1,0,6,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x9090, 0x8000, TL(0x08CA, 0x08CA), 96}, \
    /* BASSLINE HAT 3/4, variations 5,6: always x.x.x.x.x.x.x.x.  from energy 25 +...+...+...+...  weights .1...1.d.1.1.1.1 */ \
    {9, 2, 17, 0, 0x4444, 0, TW(0,1,0,0,0,1,0,13,0,1,0,1,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1111, 0x4000, TL(0x8888, 0xC808), 96}, \
    /* BASSLINE HAT 4/4, variations 0: always ..x...x...x...x.  from energy 25 ..+.......+.....  weights .1..11.1.1.111.1 */ \
    {9, 2, 8, 0, 0x4040, 0, TW(0,1,0,0,1,1,0,1,0,1,0,1,1,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0404, 0x0000, TL(0x8A88, 0x8A08), 0}, \
    /* BASSLINE OPEN HAT, variations 0,1,2,3,4,5: always ......x.......x.  from energy 25 ................  weights ..d......4d..4.4 */ \
    {9, 10, 0, 0, 0x4040, 0, TW(0,0,13,0,0,0,0,0,0,4,13,0,0,4,0,4), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0C08, 0x0000), 0}, \
    /* BASSLINE PERC 1/3, variations 0,1,2,3: always ......x.......x.  from energy 25 ................  weights 16161...1.1616.. */ \
    {9, 3, 67, 0, 0x4040, 0, TW(1,6,1,6,1,0,0,0,1,0,1,6,1,6,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0000, 0x4000, TL(0x0E22, 0x022E), 96}, \
    /* BASSLINE PERC 2/3, variations 4: always ..x.....x.x.....  from energy 25 ................  weights ......1.......1. */ \
    {9, 3, 17, 0, 0x0504, 0, TW(0,0,0,0,0,0,1,0,0,0,0,0,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0000, 0x0000, TL(0x2000, 0x2000), 0}, \
    /* BASSLINE PERC 3/3, variations 5: always x.g.x.g.x.g.x.g.  from energy 25 +...+.+.....+.+.  weights ................ */ \
    {9, 3, 17, 0, 0x0504, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x5051, 0x0000, TL(0x3030, 0x3030), 0}, \
    /* BASSLINE BASS 1/3, variations 6,7,8,9,10,11: always x..x..x...x..x..  from energy 25 ...+.........+..  weights .44.1...11..1.14 */ \
    {9, 4, 50, 0, 0x0441, 0, TW(0,4,4,0,1,0,0,0,1,1,0,0,1,0,1,4), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2008, 0x0000, TL(0x8000, 0x0028), 0}, \
    /* BASSLINE BASS 2/3, variations 0,1,2,3: always x.x.x.x.x.X.x.x.  from energy 25 +...+...+...+...  weights .1.1.....1...1.. */ \
    {9, 4, 33, 0, 0x4444, 0, TW(0,1,0,1,0,0,0,0,0,1,0,0,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1111, 0x0000, TL(0x0010, 0x0000), 0}, \
    /* BASSLINE BASS 3/3, variations 4,5: always xx..x.x.xx..x.x.  from energy 25 .+.......+..+.+.  weights ..11......1..1.. */ \
    {9, 4, 17, 0, 0x0151, 0, TW(0,0,1,1,0,0,0,0,0,0,1,0,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x5202, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* BASSLINE SUB 1/2, variations 0,1,2,3,4: always x...x...x...x...  from energy 25 ....+.......+...  weights ......1...1..... */ \
    {9, 19, 83, 0, 0x0101, 0, TW(0,0,0,0,0,0,1,0,0,0,1,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_WITH | TH_K_APART | TH_K_LV, 0x1010, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* BASSLINE SUB 2/2, variations 5: always x.....x...x.....  from energy 25 ................  weights ....1...1...1... */ \
    {9, 19, 17, 0, 0x0441, 0, TW(0,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_WITH | TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* BASSLINE STAB 1/4, variations 4,5,6,7: always x.....x.....x...  from energy 25 ................  weights ..16.1....61..1. */ \
    {9, 21, 33, 0, 0x1041, 0, TW(0,0,1,6,0,1,0,0,0,0,6,1,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* BASSLINE STAB 2/4, variations 8,9,10,11: always ...X.......x....  from energy 25 ................  weights 1.1.661...1.1.1. */ \
    {9, 21, 33, 0, 0x0808, 0, TW(1,0,1,0,6,6,1,0,0,0,1,0,1,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0A40), 0}, \
    /* BASSLINE STAB 3/4, variations 0,1,2: always ..x...x...x...x.  from energy 25 ..+.......+.....  weights 1..1.......19... */ \
    {9, 21, 25, 0, 0x4040, 0, TW(1,0,0,1,0,0,0,0,0,0,0,1,9,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0404, 0x0000, TL(0x0200, 0x0040), 0}, \
    /* BASSLINE STAB 4/4, variations 3: always ..x..x....x.....  from energy 25 ................  weights 1..1..1....11.1. */ \
    {9, 21, 8, 0, 0x0424, 0, TW(1,0,0,1,0,0,1,0,0,0,0,1,1,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0040), 0}, \
    /* BASSLINE VOX 1/3, variations 0,1,2: always ...x......x.....  from energy 25 ................  weights 1.1.19..1...9... */ \
    {9, 25, 50, 0, 0x0408, 0, TW(1,0,1,0,1,9,0,0,1,0,0,0,9,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0800), 0}, \
    /* BASSLINE VOX 2/3, variations 3,4: always ....x.......x...  from energy 25 ................  weights 1.d1.1..1.1..... */ \
    {9, 25, 33, 0, 0x1010, 0, TW(1,0,13,1,0,1,0,0,1,0,1,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0800), 0}, \
    /* BASSLINE VOX 3/3, variations 5: always x.......x.x.....  from energy 25 ................  weights ...11.......1... */ \
    {9, 25, 17, 0, 0x0501, 0, TW(0,0,0,1,1,0,0,0,0,0,0,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* BASSLINE ARP 1/2, variations 2,3,4,5: always x.x.x.x.x.x.x.x.  from energy 25 +...+...+...+...  weights .1.6.1.6.1.1.1.1 */ \
    {9, 6, 67, 0, 0x4444, 0, TW(0,1,0,6,0,1,0,6,0,1,0,1,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1111, 0x0000, TL(0x0000, 0x8080), 0}, \
    /* BASSLINE ARP 2/2, variations 0,1: always xxxxxxxxxxxxxxxx  from energy 25 .+.+.+.+.+.+.+.+  weights ................ */ \
    {9, 6, 33, 0, 0x5555, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0xAAAA, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* REGGAETON KICK 1/3, variations 3,4,5,6,7,8,9: always X..xX...X..xX...  from energy 25 ...+.......+....  weights ..4..44........4 */ \
    {10, 0, 58, 0, 0x1111, 0, TW(0,0,4,0,0,4,4,0,0,0,0,0,0,0,0,4), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0808, 0x0000, TL(0x8101, 0x2921), 0}, \
    /* REGGAETON KICK 1/3, variations 3,4,5,6,7,8,9 (even bars): always X...X..xX...X.x.  from energy 25 .......+......+.  weights ..44......44.... */ \
    {255, 0, 58, 0, 0x1111, 0, TW(0,0,4,4,0,0,0,0,0,0,4,4,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x4080, 0x4000, TL(0x01A1, 0x0121), 100}, \
    /* REGGAETON KICK 2/3, variations 0,1,2: always X...X...X...X...  from energy 25 ....+.......+...  weights ...9...........f */ \
    {10, 0, 25, 0, 0x0101, 0, TW(0,0,0,9,0,0,0,0,0,0,0,0,0,0,0,15), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1010, 0x0000, TL(0x0101, 0x0181), 0}, \
    /* REGGAETON KICK 3/3, variations 10,11: always X.......X.......  from energy 25 ................  weights ..........d..... */ \
    {10, 0, 17, 0, 0x0101, 0, TW(0,0,0,0,0,0,0,0,0,0,13,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0021, 0x0001), 0}, \
    /* REGGAETON SNARE, variations 0,1,2,3,4,5,6,7,8,9,10,11: always ...X..x....X..x.  from energy 25 ......+.......+.  weights .22..2.6.....2.2 */ \
    {10, 1, 0, 0, 0x0808, 0, TW(0,2,2,0,0,2,0,6,0,0,0,0,0,2,0,2), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x4040, 0x0000, TL(0xCC40, 0x8070), 0}, \
    /* REGGAETON SNARE, variations 0,1,2,3,4,5,6,7,8,9,10,11 (even bars): always ...X..x....X..x.  from energy 25 ......+.......+.  weights .....4.2.2...f.f */ \
    {255, 1, 0, 0, 0x0808, 0, TW(0,0,0,0,0,4,0,2,0,2,0,0,0,15,0,15), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x4040, 0x0000, TL(0x004C, 0xC040), 0}, \
    /* REGGAETON HAT 1/4, variations 3,4,5,6,7,8: always x.xx.xx.x.xx.xx.  from energy 25 +..+.+..+..+.+..  weights .9..1..4.9..1..9 */ \
    {10, 2, 50, 0, 0x4444, 0, TW(0,9,0,0,1,0,0,4,0,9,0,0,1,0,0,9), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x2929, 0x0000, TL(0x8208, 0x820C), 0}, \
    /* REGGAETON HAT 2/4, variations 0,1,2: always x.x.x.x.x.x.x.x.  from energy 25 +...+...+...+...  weights .1.1.1...f.1.9.1 */ \
    {10, 2, 25, 0, 0x4444, 0, TW(0,1,0,1,0,1,0,0,0,15,0,1,0,9,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x1111, 0x4000, TL(0x8C8C, 0x088C), 85}, \
    /* REGGAETON HAT 3/4, variations 10,11: always ..X...x...x...x.  from energy 25 ......+.......+.  weights 11.111..1d.111.1 */ \
    {10, 2, 17, 0, 0x0404, 0, TW(1,1,0,1,1,1,0,0,1,13,0,1,1,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x4040, 0x0000, TL(0x8A8A, 0x0A9E), 0}, \
    /* REGGAETON HAT 4/4, variations 9: always xxxxxxxxxxxxxxxx  from energy 25 .+..+..+.+..+..+  weights ................ */ \
    {10, 2, 8, 0, 0x6D6D, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x9292, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* REGGAETON RIM 1/3, variations 0,1,2,3: always ...x..x....x..x.  from energy 25 ...+.......+....  weights .......66....... */ \
    {10, 15, 67, 0, 0x4040, 0, TW(0,0,0,0,0,0,0,6,6,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0808, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* REGGAETON RIM 2/3, variations 4: always ......x.....x...  from energy 25 ................  weights ................ */ \
    {10, 15, 17, 0, 0x1040, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* REGGAETON RIM 3/3, variations 5: always ..x..x....x..x..  from energy 25 .....+.......+..  weights ................ */ \
    {10, 15, 17, 0, 0x0404, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2020, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* REGGAETON CONGA 1/4, variations 0,1,2,3: always x..x..x.x..x..x.  from energy 25 ...+....+..+....  weights ..d.11.6..d.16.1 */ \
    {10, 13, 36, 0, 0x4041, 0, TW(0,0,13,0,1,1,0,6,0,0,13,0,1,6,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0908, 0x4000, TL(0x8E20, 0xC820), 96}, \
    /* REGGAETON CONGA 2/4, variations 4,5,6: always ...X..x....x.xx.  from energy 25 ...........+.+..  weights 191.19.11.1.1... */ \
    {10, 13, 27, 0, 0x4048, 0, TW(1,9,1,0,1,9,0,1,1,0,1,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x2800, 0x0000, TL(0x0222, 0x886A), 0}, \
    /* REGGAETON CONGA 3/4, variations 8,9,10: always ..o.X..x....x.x.  from energy 25 .......+....+...  weights 1..1.91.1.f1.1.. */ \
    {10, 13, 27, 0, 0x4014, 0, TW(1,0,0,1,0,9,1,0,1,0,15,1,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x1080, 0x0000, TL(0x08A2, 0x29A2), 0}, \
    /* REGGAETON CONGA 4/4, variations 7: always x..x..x.o.x.x..o  from energy 25 ..........+.+..+  weights ..1.11.1...1.11. */ \
    {10, 13, 9, 0, 0x0149, 0, TW(0,0,1,0,1,1,0,1,0,0,0,1,0,1,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x9400, 0x0000, TL(0xA882, 0x8820), 0}, \
    /* REGGAETON PERC 1/3, variations 0,1,2: always ......x.......x.  from energy 25 ................  weights 1..911.1..191..9 */ \
    {10, 3, 50, 0, 0x4040, 0, TW(1,0,0,9,1,1,0,1,0,0,1,9,1,0,0,9), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x4000, TL(0xC220, 0x8E02), 85}, \
    /* REGGAETON PERC 2/3, variations 4,5: always ....x..x....x..x  from energy 25 .......+.......+  weights 1..1..1...11..1. */ \
    {10, 3, 33, 0, 0x1010, 0, TW(1,0,0,1,0,0,1,0,0,0,1,1,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x8080, 0x0000, TL(0x20A0, 0x2082), 0}, \
    /* REGGAETON PERC 2/3, variations 4,5 (even bars): always ....x..x..x.x..x  from energy 25 .......+..+.....  weights 1..1.d1....1..d. */ \
    {255, 3, 33, 0, 0x9010, 0, TW(1,0,0,1,0,13,1,0,0,0,0,1,0,0,13,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0480, 0x0000, TL(0x0080, 0x2C82), 0}, \
    /* REGGAETON PERC 3/3, variations 3: always x..x..x...x.x...  from energy 25 ...+......+.....  weights ....1..1......11 */ \
    {10, 3, 17, 0, 0x1041, 0, TW(0,0,0,0,1,0,0,1,0,0,0,0,0,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0408, 0x0000, TL(0xA000, 0x8200), 0}, \
    /* REGGAETON BASS 1/2, variations 0,1,2,3,4,5,6,7: always x..x....x..x....  from energy 25 ...+.......+....  weights .....1f...3..3d. */ \
    {10, 4, 67, 0, 0x0101, 0, TW(0,0,0,0,0,1,15,0,0,0,3,0,0,3,13,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0808, 0x0000, TL(0x0820, 0x0800), 0}, \
    /* REGGAETON BASS 2/2, variations 8,9,10,11: always x.....x.x.....x.  from energy 25 ......+.......+.  weights ...1.6.....1.... */ \
    {10, 4, 33, 0, 0x0101, 0, TW(0,0,0,1,0,6,0,0,0,0,0,1,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4040, 0x0000, TL(0x0000, 0x0800), 0}, \
    /* REGGAETON CHORD 1/2, variations 0,1,2,3,4,5: always x..x..x.x..x..x.  from energy 25 ...+..+....+..+.  weights .........44..... */ \
    {10, 5, 50, 0, 0x0101, 0, TW(0,0,0,0,0,0,0,0,0,4,4,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4848, 0x0000, TL(0x0028, 0x0000), 0}, \
    /* REGGAETON CHORD 2/2, variations 6,7,8,9,10,11: always x.......x.......  from energy 25 ................  weights ...1.44....1..1. */ \
    {10, 5, 50, 0, 0x0101, 0, TW(0,0,0,1,0,4,4,0,0,0,0,1,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x2800), 0}, \
    /* REGGAETON LEAD 1/3, variations 0,1,2,3: always x..x..x.x.......  from energy 25 ...+..+.........  weights ..1.61.1..161.6. */ \
    {10, 24, 67, 0, 0x0101, 0, TW(0,0,1,0,6,1,0,1,0,0,1,6,1,0,6,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0048, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* REGGAETON LEAD 2/3, variations 4: always x.x.x.x.x.x.x.x.  from energy 25 ..+...+...+...+.  weights ...1............ */ \
    {10, 24, 17, 0, 0x1111, 0, TW(0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4444, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* REGGAETON LEAD 3/3, variations 5: always x.xx.x.xx.x.x.x.  from energy 25 ..+..+.+..+.....  weights ....1.1......... */ \
    {10, 24, 17, 0, 0x5109, 0, TW(0,0,0,0,1,0,1,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x04A4, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* BATIDA KICK 1/3, variations 1,2,3,4,5,6,7,8,9: always X.....X.X..x....  from energy 25 ......+....+....  weights ...6.....3...f93 */ \
    {11, 0, 75, 0, 0x0101, 0, TW(0,0,0,6,0,0,0,0,0,3,0,0,0,15,9,3), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0840, 0x0000, TL(0x8001, 0x1041), 0}, \
    /* BATIDA KICK 1/3, variations 1,2,3,4,5,6,7,8,9 (even bars): always X..x..X.X..x..x.  from energy 25 ...+.......+..+.  weights .....6....3..f.c */ \
    {255, 0, 75, 0, 0x0141, 0, TW(0,0,0,0,0,6,0,0,0,0,3,0,0,15,0,12), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x4808, 0x0000, TL(0x8021, 0x1001), 0}, \
    /* BATIDA KICK 2/3, variations 10,11: always X...X..x..X.X...  from energy 25 .......+..+.....  weights .............d.. */ \
    {11, 0, 17, 0, 0x1011, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,13,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0480, 0x0000, TL(0x0910, 0x0101), 0}, \
    /* BATIDA KICK 3/3, variations 0: always X..x..X...X..x..  from energy 25 ...+.........+..  weights ................ */ \
    {11, 0, 8, 0, 0x0441, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2008, 0x0000, TL(0x0010, 0x1001), 0}, \
    /* BATIDA SNARE 1/3, variations 0,1,3,4,5,6,7,8,9,10: always ....X.......X.x.  from energy 25 ................  weights .......a.d...6.3 */ \
    {11, 1, 83, 0, 0x5010, 0, TW(0,0,0,0,0,0,0,10,0,13,0,0,0,6,0,3), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0xCD0C, 0xC100), 0}, \
    /* BATIDA SNARE 2/3, variations 2: always ....Xg......Xg..  from energy 25 .....+.......+..  weights ................ */ \
    {11, 1, 8, 0, 0x1010, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2020, 0x0000, TL(0x0D00, 0x0D00), 0}, \
    /* BATIDA SNARE 3/3, variations 11: always ...x....X..x....  from energy 25 ................  weights ................ */ \
    {11, 1, 8, 0, 0x0908, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0001, 0x0000), 0}, \
    /* BATIDA HAT 1/4, variations 0,1,2,3,4,5: always x.xx.xx.x.xx.xx.  from energy 25 ...+.++......++.  weights .4..1..9.9..4... */ \
    {11, 2, 50, 0, 0x0D05, 0, TW(0,4,0,0,1,0,0,9,0,9,0,0,4,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x6068, 0x0000, TL(0x0208, 0xC208), 0}, \
    /* BATIDA HAT 2/4, variations 9,10,11: always ..x.x...x.x...x.  from energy 25 ....+.........+.  weights 1..1.111.9.119.. */ \
    {11, 2, 25, 0, 0x0504, 0, TW(1,0,0,1,0,1,1,1,0,9,0,1,1,9,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x4010, 0x4000, TL(0x0A8C, 0xE882), 85}, \
    /* BATIDA HAT 3/4, variations 7,8: always x.x.x.x.x.x.x.x.  from energy 25 +.....+.....+...  weights ...1.d.d.1.1.1.. */ \
    {11, 2, 17, 0, 0x4514, 0, TW(0,0,0,1,0,13,0,13,0,1,0,1,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x1041, 0x0000, TL(0x088C, 0xCC80), 0}, \
    /* BATIDA HAT 4/4, variations 6: always xxxxxxxxxxxxxxxx  from energy 25 .+..+..+.+..+..+  weights ................ */ \
    {11, 2, 8, 0, 0x6D6D, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x9292, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* BATIDA SHAKER 1/2, variations 0,1,2,3,4: always xoxoooxoxoxo.oxo  from energy 25 ++.+++.+++.+.+.+  weights ............f... */ \
    {11, 12, 83, 0, 0x4444, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,15,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0xABBB, 0x0000, TL(0x8A88, 0x8A88), 0}, \
    /* BATIDA SHAKER 2/2, variations 5: always ..o...o...o...o.  from energy 25 ..+.......+.....  weights 11.111.111.111.1 */ \
    {11, 12, 17, 0, 0x4040, 0, TW(1,1,0,1,1,1,0,1,1,1,0,1,1,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0404, 0x0000, TL(0xAAAA, 0xAAAA), 0}, \
    /* BATIDA CONGA 1/4, variations 3,4,5: always x.xx..x.x.xx..x.  from energy 25 ..++....+..+....  weights ....1..1....19.. */ \
    {11, 13, 30, 0, 0x4441, 0, TW(0,0,0,0,1,0,0,1,0,0,0,0,1,9,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x090C, 0x4000, TL(0x0E00, 0x8200), 85}, \
    /* BATIDA CONGA 2/4, variations 9,10,11: always ....x..x..o.x.x.  from energy 25 ....+.......+...  weights 1.f1..1.1..1.9.. */ \
    {11, 13, 30, 0, 0x4480, 0, TW(1,0,15,1,0,0,1,0,1,0,0,1,0,9,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x1010, 0x4000, TL(0x0CA2, 0x20A2), 85}, \
    /* BATIDA CONGA 3/4, variations 0,1: always x..x..x...x..x..  from energy 25 ...+.........+..  weights ..1.1..11..11.1d */ \
    {11, 13, 20, 0, 0x0441, 0, TW(0,0,1,0,1,0,0,1,1,0,0,1,1,0,1,13), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x2008, 0x2000, TL(0xE282, 0x8220), 96}, \
    /* BATIDA CONGA 4/4, variations 6,7: always ...x..x....x.xx.  from energy 25 ...........+.+..  weights 1.1.1..11d1.1... */ \
    {11, 13, 20, 0, 0x4048, 0, TW(1,0,1,0,1,0,0,1,1,13,1,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x2800, 0x4000, TL(0x022E, 0x8222), 96}, \
    /* BATIDA PERC 1/4, variations 6,7,8,9,10,11: always .x..x..x..x..x.x  from energy 25 .+........+....+  weights 1.41.11.1f.41.4. */ \
    {11, 3, 50, 0, 0x2090, 0, TW(1,0,4,1,0,1,1,0,1,15,0,4,1,0,4,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x8402, 0x0000, TL(0x020A, 0x2882), 0}, \
    /* BATIDA PERC 1/4, variations 6,7,8,9,10,11 (even bars): always .x..x..x.x.x.x.x  from energy 25 .+.........+...+  weights 1.11.11.1...1.9. */ \
    {255, 3, 50, 0, 0x2290, 0, TW(1,0,1,1,0,1,1,0,1,0,0,0,1,0,9,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x8802, 0x0000, TL(0x0202, 0x28A2), 0}, \
    /* BATIDA PERC 2/4, variations 0,1: always x..x..x..x..x.x.  from energy 25 ...+..+.....+...  weights .11.11.1..11.d.1 */ \
    {11, 3, 17, 0, 0x4201, 0, TW(0,1,1,0,1,1,0,1,0,0,1,1,0,13,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1048, 0x4000, TL(0x8CA0, 0x8A28), 96}, \
    /* BATIDA PERC 3/4, variations 2,3: always x.x..x.x.X..x.x.  from energy 25 ..+..+......+...  weights .1..1.....1d.1.1 */ \
    {11, 3, 17, 0, 0x4281, 0, TW(0,1,0,0,1,0,0,0,0,0,1,13,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1024, 0x0000, TL(0x88A4, 0x0208), 0}, \
    /* BATIDA PERC 4/4, variations 4,5: always ..x..x..x..X..x.  from energy 25 ..+..+..........  weights 11..1..1.11.11.d */ \
    {11, 3, 17, 0, 0x4900, 0, TW(1,1,0,0,1,0,0,1,0,1,1,0,1,1,0,13), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0024, 0x0000, TL(0x8A68, 0x820A), 0}, \
    /* BATIDA TOM 1/3, variations 0,1,2,3: always ......x.......x.  from energy 25 ................  weights 1........61.61.d */ \
    {11, 14, 67, 0, 0x4040, 0, TW(1,0,0,0,0,0,0,0,0,6,1,0,6,1,0,13), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0000, 0x0000, TL(0x0820, 0x0002), 0}, \
    /* BATIDA TOM 1/3, variations 0,1,2,3 (even bars): always ......x.......xx  from energy 25 ................  weights 6........61.61.. */ \
    {255, 14, 67, 0, 0xC040, 0, TW(6,0,0,0,0,0,0,0,0,6,1,0,6,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0820, 0x0000), 0}, \
    /* BATIDA TOM 2/3, variations 4: always x.....x.....x...  from energy 25 ................  weights ..............11 */ \
    {11, 14, 17, 0, 0x1041, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0xA000, 0x0000), 0}, \
    /* BATIDA TOM 3/3, variations 5: always ..........x..x..  from energy 25 ................  weights 1.....1.....1.11 */ \
    {11, 14, 17, 0, 0x2400, 0, TW(1,0,0,0,0,0,1,0,0,0,0,0,1,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0xA200, 0x2002), 0}, \
    /* BATIDA BASS 1/3, variations 3,4,5,6,7: always x.x...x.x.x...x.  from energy 25 ..+.....+.+.....  weights ...1.......1.5.5 */ \
    {11, 4, 42, 0, 0x4041, 0, TW(0,0,0,1,0,0,0,0,0,0,0,1,0,5,0,5), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0504, 0x0000, TL(0x8800, 0x0000), 0}, \
    /* BATIDA BASS 2/3, variations 8,9,10,11: always X..x..x.x..x..x.  from energy 25 ...+.......+..+.  weights .66..6....1..1.. */ \
    {11, 4, 33, 0, 0x0141, 0, TW(0,6,6,0,0,6,0,0,0,0,1,0,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4808, 0x0000, TL(0x0000, 0x0829), 0}, \
    /* BATIDA BASS 3/3, variations 0,1,2: always x..x..x...x..x..  from energy 25 ...+.........+..  weights ..1.....1..1..1. */ \
    {11, 4, 25, 0, 0x0441, 0, TW(0,0,1,0,0,0,0,0,1,0,0,1,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2008, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* BATIDA CHORD 1/2, variations 3,4,5,6,7,8,9,10,11: always ..x..x..x..x..x.  from energy 25 .....+.....+....  weights 1..1..1...3....3 */ \
    {11, 5, 75, 0, 0x4104, 0, TW(1,0,0,1,0,0,1,0,0,0,3,0,0,0,0,3), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0820, 0x0000, TL(0x8020, 0x0000), 0}, \
    /* BATIDA CHORD 2/2, variations 0,1,2: always x..x..x.........  from energy 25 ................  weights ..1..1..1..1..1. */ \
    {11, 5, 25, 0, 0x0049, 0, TW(0,0,1,0,0,1,0,0,1,0,0,1,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* BATIDA LEAD 1/4, variations 3,4,5: always x.....x.x.......  from energy 25 ................  weights ..1f91.1..11111. */ \
    {11, 24, 50, 0, 0x0141, 0, TW(0,0,1,15,9,1,0,1,0,0,1,1,1,1,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* BATIDA LEAD 2/4, variations 0: always x.xx.xx.x.xx.xx.  from energy 25 ..++.+....++.++.  weights ....1.......1... */ \
    {11, 24, 17, 0, 0x0141, 0, TW(0,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x6C2C, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* BATIDA LEAD 3/4, variations 1: always x.xx.x.xx.x.x.x.  from energy 25 .....+.+....+.+.  weights ....1.1......... */ \
    {11, 24, 17, 0, 0x050D, 0, TW(0,0,0,0,1,0,1,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x50A0, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* BATIDA LEAD 4/4, variations 2: always x.x.x.x.x.x.x.x.  from energy 25 ..+.+.....+.+.+.  weights ...1.1.......... */ \
    {11, 24, 17, 0, 0x0141, 0, TW(0,0,0,1,0,1,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x5414, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* GQOM KICK 1/3, variations 0,1,2,3,4: always X.....X.....x...  from energy 25 ................  weights ...a....a.5..... */ \
    {12, 0, 42, 0, 0x1041, 0, TW(0,0,0,10,0,0,0,0,10,0,5,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0022, 0x1041), 0}, \
    /* GQOM KICK 2/3, variations 5,6,7,8: always X.....X...X..X..  from energy 25 ..........+..+..  weights ...6.......d.... */ \
    {12, 0, 33, 0, 0x0041, 0, TW(0,0,0,6,0,0,0,0,0,0,0,13,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x2400, 0x0000, TL(0x0490, 0x1081), 0}, \
    /* GQOM KICK 2/3, variations 5,6,7,8 (even bars): always X.....X.....X.X.  from energy 25 ..............+.  weights ..666........... */ \
    {255, 0, 33, 0, 0x1041, 0, TW(0,0,6,6,6,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x4000, 0x0000, TL(0x1100, 0x1001), 0}, \
    /* GQOM KICK 3/3, variations 9,10,11: always X.....X..x......  from energy 25 ................  weights ..........99.... */ \
    {12, 0, 25, 0, 0x0241, 0, TW(0,0,0,0,0,0,0,0,0,0,9,9,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x00A0, 0x1001), 0}, \
    /* GQOM SNARE 1/3, variations 4,5,6,7,8: always ........x.......  from energy 25 ................  weights .....5...55..5.. */ \
    {12, 1, 42, 0, 0x0100, 0, TW(0,0,0,0,0,5,0,0,0,5,5,0,0,5,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0828, 0x0800), 0}, \
    /* GQOM SNARE 2/3, variations 0,1,2,3: always ....X..X....x...  from energy 25 ................  weights .9.......9...... */ \
    {12, 1, 33, 0, 0x1090, 0, TW(0,9,0,0,0,0,0,0,0,9,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x1000, TL(0x000C, 0x410C), 106}, \
    /* GQOM SNARE 3/3, variations 9,10,11: always ......x.......x.  from energy 25 ................  weights .....9.......9.. */ \
    {12, 1, 25, 0, 0x4040, 0, TW(0,0,0,0,0,9,0,0,0,0,0,0,0,9,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x4000, TL(0x0C00, 0x0C00), 106}, \
    /* GQOM HAT 1/4, variations 0,1,2,3: always ..x...x...x...x.  from energy 25 ..+.......+.....  weights 1..161.116.116.. */ \
    {12, 2, 33, 0, 0x4040, 0, TW(1,0,0,1,6,1,0,1,1,6,0,1,1,6,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x0404, 0x0000, TL(0x0A8E, 0xCA82), 0}, \
    /* GQOM HAT 2/4, variations 4,5,6: always ..x..x....x..x..  from energy 25 .....+.......+..  weights 1..11.991..1..1. */ \
    {12, 2, 25, 0, 0x0404, 0, TW(1,0,0,1,1,0,9,9,1,0,0,1,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x2020, 0x2000, TL(0x2082, 0xE282), 85}, \
    /* GQOM HAT 3/4, variations 7,8,9: always x.xx.x..x.xx.x..  from energy 25 +..+....+..+....  weights .9..1.1..9....1. */ \
    {12, 2, 25, 0, 0x2424, 0, TW(0,9,0,0,1,0,1,0,0,9,0,0,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x0909, 0x2000, TL(0x200C, 0x220C), 106}, \
    /* GQOM HAT 4/4, variations 10,11: always x...x...x...x...  from energy 25 ....+.......+...  weights ..11.11d..11.11. */ \
    {12, 2, 17, 0, 0x0101, 0, TW(0,0,1,1,0,1,1,13,0,0,1,1,0,1,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x1010, 0x1000, TL(0x28A0, 0xE8A0), 96}, \
    /* GQOM PERC 1/4, variations 5,6,7,8,9: always ...xx.....x.x...  from energy 25 ....+.....+.....  weights 115..115.1...155 */ \
    {12, 3, 42, 0, 0x1008, 0, TW(1,1,5,0,0,1,1,5,0,1,0,0,0,1,5,5), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0410, 0x0000, TL(0xE008, 0x282A), 0}, \
    /* GQOM PERC 1/4, variations 5,6,7,8,9 (even bars): always ...xx.....x.x.xx  from energy 25 ....+.........++  weights 11...55..1...5.. */ \
    {255, 3, 42, 0, 0x1408, 0, TW(1,1,0,0,0,5,5,0,0,1,0,0,0,5,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0xC010, 0x0000, TL(0x0008, 0x200A), 0}, \
    /* GQOM PERC 2/4, variations 0,1,2: always ...x..x.....x...  from energy 25 ................  weights .9..11...91..111 */ \
    {12, 3, 25, 0, 0x1048, 0, TW(0,9,0,0,1,1,0,0,0,9,1,0,0,1,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x1000, TL(0xA82C, 0x0A0C), 106}, \
    /* GQOM PERC 3/4, variations 3,4: always x..x..x...x.x...  from energy 25 +.........+.....  weights .1..1d...1...111 */ \
    {12, 3, 17, 0, 0x1048, 0, TW(0,1,0,0,1,13,0,0,0,1,0,0,0,1,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0401, 0x1000, TL(0xA808, 0x0E08), 96}, \
    /* GQOM PERC 4/4, variations 10,11: always .x...x...x...X..  from energy 25 .+.......+......  weights ..d11.1...1.1.11 */ \
    {12, 3, 17, 0, 0x2020, 0, TW(0,0,13,1,1,0,1,0,0,0,1,0,1,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0202, 0x0000, TL(0xA620, 0x22A0), 0}, \
    /* GQOM TOM 1/4, variations 1,2,3,4: always ..x..x....x..x..  from energy 25 ..+..+..........  weights 1..1..19.9.11.11 */ \
    {12, 14, 40, 0, 0x2400, 0, TW(1,0,0,1,0,0,1,9,0,9,0,1,1,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0024, 0x2000, TL(0xA28C, 0xE082), 106}, \
    /* GQOM TOM 2/4, variations 7,8,9: always ......x.......x.  from energy 25 ................  weights 1.19.1....1.11.. */ \
    {12, 14, 30, 0, 0x4040, 0, TW(1,0,1,9,0,1,0,0,0,0,1,0,1,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0000, 0x0000, TL(0x0A20, 0x08E2), 0}, \
    /* GQOM TOM 2/4, variations 7,8,9 (even bars): always x.....x.......xx  from energy 25 ..............++  weights ..9..1....1919.. */ \
    {255, 14, 30, 0, 0x0041, 0, TW(0,0,9,0,0,1,0,0,0,0,1,9,1,9,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0xC000, 0x0000, TL(0x02E0, 0x0800), 0}, \
    /* GQOM TOM 3/4, variations 5,6: always x.....x.....x...  from energy 25 ................  weights ..11.1....1..11. */ \
    {12, 14, 20, 0, 0x1041, 0, TW(0,0,1,1,0,1,0,0,0,0,1,0,0,1,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0000, 0x0000, TL(0x2820, 0x08A0), 0}, \
    /* GQOM TOM 3/4, variations 5,6 (even bars): always x...........x...  from energy 25 ................  weights ..1.d1d...d..111 */ \
    {255, 14, 20, 0, 0x1001, 0, TW(0,0,1,0,13,1,13,0,0,0,13,0,0,1,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0xA800, 0x0820), 0}, \
    /* GQOM TOM 4/4, variations 0: always x..x..x...x..x..  from energy 25 ...+.........+..  weights ..1..1......1.11 */ \
    {12, 14, 10, 0, 0x0441, 0, TW(0,0,1,0,0,1,0,0,0,0,0,0,1,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2008, 0x0000, TL(0xA200, 0x0820), 0}, \
    /* GQOM BASS, variations 0,1,2,3,4,5,6,7,8,9,10,11: always x.....x.....x...  from energy 25 ................  weights ...a.3.3.......3 */ \
    {12, 4, 0, 0, 0x1041, 0, TW(0,0,0,10,0,3,0,3,0,0,0,0,0,0,0,3), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x8000, 0x8800), 0}, \
    /* GQOM PAD, variations 0,1,2,3,4,5: always x...............  from energy 25 ................  weights ......9.4....... */ \
    {12, 22, 0, 0, 0x0001, 0, TW(0,0,0,0,0,0,9,0,4,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* GQOM VOX 1/3, variations 0,1,2: always ................  from energy 25 ................  weights 1.1f1.9.11f.1... */ \
    {12, 25, 50, 0, 0x0000, 0, TW(1,0,1,15,1,0,9,0,1,1,15,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0008, 0x0001), 0}, \
    /* GQOM VOX 2/3, variations 3,4: always X.......x.x.....  from energy 25 ................  weights ..111.1..d..1... */ \
    {12, 25, 33, 0, 0x0501, 0, TW(0,0,1,1,1,0,1,0,0,13,0,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0008, 0x0001), 0}, \
    /* GQOM VOX 3/3, variations 5: always ..x.x.......x...  from energy 25 ................  weights 1..1....1.1..... */ \
    {12, 25, 17, 0, 0x1014, 0, TW(1,0,0,1,0,0,0,0,1,0,1,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0001), 0}, \
    /* GQOM ARP 1/2, variations 0,1,2: always x..x..x..x..x..x  from energy 25 ...+.....+.....+  weights ..9..9.......1.. */ \
    {12, 6, 50, 0, 0x1041, 0, TW(0,0,9,0,0,9,0,0,0,0,0,0,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x8208, 0x0000, TL(0x0000, 0x0820), 0}, \
    /* GQOM ARP 2/2, variations 3,4,5: always x.....x.....x...  from energy 25 ................  weights ..11.1...1...d.1 */ \
    {12, 6, 50, 0, 0x1041, 0, TW(0,0,1,1,0,1,0,0,0,1,0,0,0,13,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0820), 0}, \
    /* EXPERIMENT KICK 1/4, variations 1,2,3,4,5,6,7,8,9: always X..x..X..X.x....  from energy 25 ...+.......+....  weights .............3.3 */ \
    {13, 0, 75, 0, 0x0241, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,3,0,3), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0808, 0x0000, TL(0x0004, 0x1001), 0}, \
    /* EXPERIMENT KICK 1/4, variations 1,2,3,4,5,6,7,8,9 (even bars): always x..x..X.....x...  from energy 25 ...+........+...  weights .........3.....3 */ \
    {255, 0, 75, 0, 0x0041, 0, TW(0,0,0,0,0,0,0,0,0,3,0,0,0,0,0,3), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x1008, 0x1000, TL(0x0000, 0x1000), 184}, \
    /* EXPERIMENT KICK 2/4, variations 0: always X..x.x...x.x..x.  from energy 25 .....+...+....+.  weights ................ */ \
    {13, 0, 8, 0, 0x0809, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4220, 0x0000, TL(0x0000, 0x0001), 0}, \
    /* EXPERIMENT KICK 3/4, variations 10: always X.......x..x.x..  from energy 25 ........+....+..  weights ................ */ \
    {13, 0, 8, 0, 0x0801, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2100, 0x0000, TL(0x0000, 0x0001), 0}, \
    /* EXPERIMENT KICK 4/4, variations 11: always X....x....x....x  from energy 25 .....+.........+  weights ................ */ \
    {13, 0, 8, 0, 0x0401, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x8020, 0x0000, TL(0x0000, 0x0001), 0}, \
    /* EXPERIMENT SNARE 1/4, variations 0,1,2,3,4: always ......x.....x..x  from energy 25 ................  weights .5.....5...5..f. */ \
    {13, 1, 42, 0, 0x9040, 0, TW(0,5,0,0,0,0,0,5,0,0,0,5,0,0,15,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x30C0, 0xC008), 0}, \
    /* EXPERIMENT SNARE 2/4, variations 7,8,9: always ..g..g..X..g..g.  from energy 25 ..+........+....  weights ......99........ */ \
    {13, 1, 25, 0, 0x4120, 0, TW(0,0,0,0,0,0,9,9,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0804, 0x0000, TL(0x30C1, 0xAC30), 0}, \
    /* EXPERIMENT SNARE 3/4, variations 5,6: always .....x....X.....  from energy 25 ................  weights d............... */ \
    {13, 1, 17, 0, 0x0420, 0, TW(13,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0010, 0x0002), 0}, \
    /* EXPERIMENT SNARE 4/4, variations 10,11: always ...x.....x....x.  from energy 25 ................  weights ......d......... */ \
    {13, 1, 17, 0, 0x4208, 0, TW(0,0,0,0,0,0,13,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x4000, TL(0x0000, 0x3000), 160}, \
    /* EXPERIMENT HAT 1/4, variations 2,3,4,5: always xxx.xx.x..xxx.x.  from energy 25 .++..+.....+..+.  weights ...1..1.16...6.6 */ \
    {13, 2, 33, 0, 0x1491, 0, TW(0,0,0,1,0,0,1,0,1,6,0,0,0,6,0,6), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x4826, 0x4000, TL(0xCC0E, 0x2080), 175}, \
    /* EXPERIMENT HAT 2/4, variations 8,9,10,11: always x..x..x...x.x...  from energy 25 ...+..+.........  weights .d6.11.611.6.11. */ \
    {13, 2, 33, 0, 0x1401, 0, TW(0,13,6,0,1,1,0,6,1,1,0,6,0,1,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x0048, 0x1041, TL(0x28CA, 0xCA2C), 127}, \
    /* EXPERIMENT HAT 3/4, variations 0,1: always x.xx.x.xxX.x.xx.  from energy 25 ...+.+..+....++.  weights .1..1.1...1.d... */ \
    {13, 2, 17, 0, 0x0A85, 0, TW(0,1,0,0,1,0,1,0,0,0,1,0,13,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x6128, 0x0000, TL(0x0224, 0x2208), 0}, \
    /* EXPERIMENT HAT 4/4, variations 6,7: always x...x..x.x...x..  from energy 25 .........+...+..  weights .111.11...1d1.1. */ \
    {13, 2, 17, 0, 0x0091, 0, TW(0,1,1,1,0,1,1,0,0,0,1,13,1,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x2200, 0x2000, TL(0x22E0, 0x28A8), 160}, \
    /* EXPERIMENT PERC 1/4, variations 0,1,2,3: always x....x....x....x  from energy 25 .....+....+.....  weights .1111.1116.61d1. */ \
    {13, 3, 33, 0, 0x8001, 0, TW(0,1,1,1,1,0,1,1,1,6,0,6,1,13,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0420, 0x8000, TL(0x2ECE, 0xA2A8), 160}, \
    /* EXPERIMENT PERC 2/4, variations 7,8,9,10: always x..x..x..x..x..x  from energy 25 ...+..+..+......  weights ..1..6..1.16.1.. */ \
    {13, 3, 33, 0, 0x9001, 0, TW(0,0,1,0,0,6,0,0,1,0,1,6,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0248, 0x0000, TL(0x0CE2, 0x0C20), 0}, \
    /* EXPERIMENT PERC 2/4, variations 7,8,9,10 (even bars): always .x..x..x..x.x.xx  from energy 25 .+.....+......+.  weights 1.16.6..16.6.1.. */ \
    {255, 3, 33, 0, 0x9410, 0, TW(1,0,1,6,0,6,0,0,1,6,0,6,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x4082, 0x8000, TL(0x0C02, 0x0822), 127}, \
    /* EXPERIMENT PERC 3/4, variations 4,5,6: always ..x.....x...x..x  from energy 25 ............+..+  weights 1..1.11..191.9.. */ \
    {13, 3, 25, 0, 0x0104, 0, TW(1,0,0,1,0,1,1,0,0,1,9,1,0,9,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x9000, 0x0000, TL(0x08E8, 0x2882), 0}, \
    /* EXPERIMENT PERC 3/4, variations 4,5,6 (even bars): always ..x.....x...x..x  from energy 25 ............+..+  weights 11..11.1..91.91. */ \
    {255, 3, 25, 0, 0x0104, 0, TW(1,1,0,0,1,1,0,1,0,0,9,1,0,9,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x9000, 0x0000, TL(0x28A0, 0x8A0A), 0}, \
    /* EXPERIMENT PERC 4/4, variations 11: always .x.x...x..xx....  from energy 25 .......+...+....  weights 1.1.111.11..1111 */ \
    {13, 3, 8, 0, 0x040A, 0, TW(1,0,1,0,1,1,1,0,1,1,0,0,1,1,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0880, 0x0000, TL(0xAE0A, 0x2A22), 0}, \
    /* EXPERIMENT TOM 1/4, variations 1,2: always ............x.xx  from energy 25 ................  weights 1....11..d11.1.. */ \
    {13, 14, 33, 0, 0xD000, 0, TW(1,0,0,0,0,1,1,0,0,13,1,1,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x8000, TL(0x08AC, 0x2C02), 160}, \
    /* EXPERIMENT TOM 2/4, variations 3,4: always ......x.......x.  from energy 25 ................  weights 1....d...11.11.1 */ \
    {13, 14, 33, 0, 0x4040, 0, TW(1,0,0,0,0,13,0,0,0,1,1,0,1,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0000, 0x0000, TL(0x8A2C, 0x0C02), 0}, \
    /* EXPERIMENT TOM 2/4, variations 3,4 (even bars): always x.....x.......xx  from energy 25 ......+........+  weights .........11d11.. */ \
    {255, 14, 33, 0, 0x4001, 0, TW(0,0,0,0,0,0,0,0,0,1,1,13,1,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x8040, 0x0000, TL(0x0A2C, 0x0000), 0}, \
    /* EXPERIMENT TOM 3/4, variations 0: always ..........x..x..  from energy 25 ................  weights 1.....1.....1.11 */ \
    {13, 14, 17, 0, 0x2400, 0, TW(1,0,0,0,0,0,1,0,0,0,0,0,1,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0xA200, 0x2002), 0}, \
    /* EXPERIMENT TOM 4/4, variations 5: always x.....x.....x...  from energy 25 ................  weights ..............11 */ \
    {13, 14, 17, 0, 0x1041, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0xA000, 0x0000), 0}, \
    /* EXPERIMENT BASS 1/3, variations 3,4,5,6,7: always xx..x...x.x..x..  from energy 25 .+........+..+..  weights ..5...15...11... */ \
    {13, 4, 42, 0, 0x0111, 0, TW(0,0,5,0,0,0,1,5,0,0,0,1,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2402, 0x0000, TL(0x0000, 0x8020), 0}, \
    /* EXPERIMENT BASS 2/3, variations 8,9,10,11: always x.....x....x....  from energy 25 ................  weights .1..16.11.1.11.. */ \
    {13, 4, 33, 0, 0x0841, 0, TW(0,1,0,0,1,6,0,1,1,0,1,0,1,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0800), 0}, \
    /* EXPERIMENT BASS 3/3, variations 0,1,2: always x...x..x..x.x...  from energy 25 .......+....+...  weights .1....1.1..1.199 */ \
    {13, 4, 25, 0, 0x0411, 0, TW(0,1,0,0,0,0,1,0,1,0,0,1,0,1,9,9), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1080, 0x0000, TL(0xA000, 0x0000), 0}, \
    /* EXPERIMENT PAD 1/2, variations 4,5,6,7,8,9,10,11: always x...............  from energy 25 ................  weights ....1.3.6.61..1. */ \
    {13, 22, 67, 0, 0x0001, 0, TW(0,0,0,0,1,0,3,0,6,0,6,1,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0xA000, 0x0200), 0}, \
    /* EXPERIMENT PAD 2/2, variations 0,1,2,3: always x.....X....x....  from energy 25 ................  weights ....6...1.....6. */ \
    {13, 22, 33, 0, 0x0841, 0, TW(0,0,0,0,6,0,0,0,1,0,0,0,0,0,6,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0xA000, 0x1200), 0}, \
    /* EXPERIMENT ARP 1/2, variations 0,1,2,3,4,5: always xxxxxxxxxxxxxxxx  from energy 25 .+.+..+.+..+.+.+  weights ................ */ \
    {13, 6, 50, 0, 0x56B5, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0xA94A, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* EXPERIMENT ARP 2/2, variations 6,7,8,9,10,11: always x.x.xx.x.xx.x.x.  from energy 25 .....+.+..+...+.  weights .1.4..1.1..1.1.1 */ \
    {13, 6, 50, 0, 0x1215, 0, TW(0,1,0,4,0,0,1,0,1,0,0,1,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x44A0, 0x0000, TL(0x0000, 0x0080), 0}, \
    /* ELECTRO KICK 1/2, variations 0,1,2,3,4,5,6,7: always X.....x...X.....  from energy 25 ................  weights ...6...3.....f33 */ \
    {14, 0, 67, 0, 0x0441, 0, TW(0,0,0,6,0,0,0,3,0,0,0,0,0,15,3,3), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0000, 0x2000, TL(0xA010, 0x8001), 115}, \
    /* ELECTRO KICK 1/2, variations 0,1,2,3,4,5,6,7 (even bars): always X.....X.........  from energy 25 ................  weights ...6.3..f.6...f. */ \
    {255, 0, 67, 0, 0x0041, 0, TW(0,0,0,6,0,3,0,0,15,0,6,0,0,0,15,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0011, 0x1801), 0}, \
    /* ELECTRO KICK 2/2, variations 8,9,10,11: always X.....X.x.....x.  from energy 25 ........+.....+.  weights ..........666... */ \
    {14, 0, 33, 0, 0x0041, 0, TW(0,0,0,0,0,0,0,0,0,0,6,6,6,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4100, 0x0000, TL(0x02A0, 0x1001), 0}, \
    /* ELECTRO SNARE 1/3, variations 0,1,5,6,7,8,9,10: always ....X.......X...  from energy 25 ................  weights .....6.33....33d */ \
    {14, 1, 67, 0, 0x1010, 0, TW(0,0,0,0,0,6,0,3,3,0,0,0,0,3,3,13), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x3D02, 0x0900), 0}, \
    /* ELECTRO SNARE 2/3, variations 2,3,4: always ....X.......X.g.  from energy 25 ................  weights ......f....f...9 */ \
    {14, 1, 25, 0, 0x5010, 0, TW(0,0,0,0,0,0,15,0,0,0,0,15,0,0,0,9), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0xF180, 0x3100), 0}, \
    /* ELECTRO SNARE 3/3, variations 11: always ....X..g....Xgg.  from energy 25 .......+.....+..  weights ................ */ \
    {14, 1, 8, 0, 0x5010, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2080, 0x0000, TL(0x3D00, 0xC100), 0}, \
    /* ELECTRO CLAP, variations 0,1,2,3,4,5: always ....X.......X...  from energy 25 ................  weights .......9......44 */ \
    {14, 9, 0, 0, 0x1010, 0, TW(0,0,0,0,0,0,0,9,0,0,0,0,0,0,4,4), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x1100, 0x0100), 0}, \
    /* ELECTRO HAT 1/4, variations 0,1,2,3: always x.x.x.x.x.x.x.x.  from energy 25 +...+...+...+...  weights .1.1.6.6.1.6...1 */ \
    {14, 2, 33, 0, 0x4444, 0, TW(0,1,0,1,0,6,0,6,0,1,0,6,0,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x1111, 0x4000, TL(0x80C8, 0xC88C), 96}, \
    /* ELECTRO HAT 2/4, variations 4,5,6,7: always x.xxx.xxX.xxx.xx  from energy 25 ...+...+...+...+  weights .d...1...6...... */ \
    {14, 2, 33, 0, 0x5555, 0, TW(0,13,0,0,0,1,0,0,0,6,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x8888, 0x0000, TL(0x0009, 0x080C), 0}, \
    /* ELECTRO HAT 3/4, variations 9,10,11: always ..x...x...X...x.  from energy 25 ......+.......+.  weights 19.11..91..11..1 */ \
    {14, 2, 25, 0, 0x0404, 0, TW(1,9,0,1,1,0,0,9,1,0,0,1,1,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x4040, 0x0000, TL(0x8292, 0xC28A), 0}, \
    /* ELECTRO HAT 4/4, variations 8: always xxxxxxxxxxxxxxxx  from energy 25 .+...+...+...+..  weights ................ */ \
    {14, 2, 8, 0, 0xDDDD, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x2222, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* ELECTRO OPEN HAT, variations 0,1,2,3,4,5: always ......x.......x.  from energy 25 ................  weights ..d..4...4d....4 */ \
    {14, 10, 0, 0, 0x4040, 0, TW(0,0,13,0,0,4,0,0,0,4,13,0,0,0,0,4), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x4000, TL(0x000C, 0x0C00), 85}, \
    /* ELECTRO COWBELL 1/4, variations 0,1: always ..x...x...x...x.  from energy 25 ......+.......+.  weights 1..111.11...d1.1 */ \
    {14, 17, 40, 0, 0x0404, 0, TW(1,0,0,1,1,1,0,1,1,0,0,0,13,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4040, 0x0000, TL(0x8802, 0x8A82), 0}, \
    /* ELECTRO COWBELL 2/4, variations 2: always ..x.x..x..x...x.  from energy 25 ....+..+........  weights 1.....1.....11.. */ \
    {14, 17, 20, 0, 0x4404, 0, TW(1,0,0,0,0,0,1,0,0,0,0,0,1,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0090, 0x0000, TL(0x0A00, 0x2002), 0}, \
    /* ELECTRO COWBELL 3/4, variations 3: always ..x.x...x...x.x.  from energy 25 ........+...+...  weights 1.....11..1..1.. */ \
    {14, 17, 20, 0, 0x4014, 0, TW(1,0,0,0,0,0,1,1,0,0,1,0,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1100, 0x0000, TL(0x0820, 0xA002), 0}, \
    /* ELECTRO COWBELL 4/4, variations 4: always x..x..x...x..x..  from energy 25 ...+.........+..  weights ..1.1..1....1.1. */ \
    {14, 17, 20, 0, 0x0441, 0, TW(0,0,1,0,1,0,0,1,0,0,0,0,1,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2008, 0x0000, TL(0x2200, 0x8220), 0}, \
    /* ELECTRO BASS 1/3, variations 0,1,2,3,4,5,6: always X.....x...x.....  from energy 25 ................  weights .4.1.4..1..1.44. */ \
    {14, 4, 58, 0, 0x0441, 0, TW(0,4,0,1,0,4,0,0,1,0,0,1,0,4,4,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x2800, 0x0809), 0}, \
    /* ELECTRO BASS 2/3, variations 8,9,10,11: always x..x..x.x..x....  from energy 25 ...+.......+....  weights ..........1...1. */ \
    {14, 4, 33, 0, 0x0141, 0, TW(0,0,0,0,0,0,0,0,0,0,1,0,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0808, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* ELECTRO BASS 3/3, variations 7: always x.x...x.x.x...x.  from energy 25 ..+.....+.....+.  weights ...1.......1.... */ \
    {14, 4, 8, 0, 0x0441, 0, TW(0,0,0,1,0,0,0,0,0,0,0,1,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4104, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* ELECTRO STAB 1/3, variations 0,1,2,3: always x...........x...  from energy 25 ................  weights ..11d1d...6..... */ \
    {14, 21, 67, 0, 0x1001, 0, TW(0,0,1,1,13,1,13,0,0,0,6,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0020, 0x0000), 0}, \
    /* ELECTRO STAB 2/3, variations 4: always ...x.......x....  from energy 25 ................  weights 1.....1......... */ \
    {14, 21, 17, 0, 0x0808, 0, TW(1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* ELECTRO STAB 3/3, variations 5: always ..x..x....x.....  from energy 25 ................  weights 1...........1... */ \
    {14, 21, 17, 0, 0x0424, 0, TW(1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* ELECTRO ARP 1/2, variations 0,1,2,3,4,5,6,7,8,9: always x.x.x.x.x.x.x.x.  from energy 25 ..+...+...+...+.  weights .1.1.1.1.1.3.1.1 */ \
    {14, 6, 83, 0, 0x1111, 0, TW(0,1,0,1,0,1,0,1,0,1,0,3,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4444, 0x0000, TL(0x0080, 0x0000), 0}, \
    /* ELECTRO ARP 2/2, variations 10,11: always xxXxxxxxxxxxxxxx  from energy 25 .+.+.+.+.+.+.+.+  weights ................ */ \
    {14, 6, 17, 0, 0x5555, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0xAAAA, 0x0000, TL(0x0000, 0x0010), 0}, \
    /* ELECTRO PERC 1/4, variations 1,2: always .x...x......x...  from energy 25 ................  weights 1.11..1d1d1...1. */ \
    {14, 3, 33, 0, 0x1022, 0, TW(1,0,1,1,0,0,1,13,1,13,1,0,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0000, 0x0000, TL(0x2022, 0xE0A2), 0}, \
    /* ELECTRO PERC 1/4, variations 1,2 (even bars): always .x...x...x..x.x.  from energy 25 .+.......+......  weights 1.11..1.1.1..... */ \
    {255, 3, 33, 0, 0x5020, 0, TW(1,0,1,1,0,0,1,0,1,0,1,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0202, 0x0000, TL(0x0022, 0x20A2), 0}, \
    /* ELECTRO PERC 2/4, variations 3,4: always ......x.......x.  from energy 25 ................  weights 1111.d.1111.1... */ \
    {14, 3, 33, 0, 0x4040, 0, TW(1,1,1,1,0,13,0,1,1,1,1,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x4000, TL(0x022A, 0xCCAA), 96}, \
    /* ELECTRO PERC 3/4, variations 0: always ..x.....x...x...  from energy 25 ................  weights .1...11..1....1. */ \
    {14, 3, 17, 0, 0x1104, 0, TW(0,1,0,0,0,1,1,0,0,1,0,0,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x2008, 0x2808), 0}, \
    /* ELECTRO PERC 4/4, variations 5: always x..x..x...x.....  from energy 25 ...+......+.....  weights .1...1...1..1.1. */ \
    {14, 3, 17, 0, 0x0041, 0, TW(0,1,0,0,0,1,0,0,0,1,0,0,1,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0408, 0x0000, TL(0x2208, 0x0808), 0}, \
    /* AFRO HOUSE KICK, variations 0,1,2,3,4,5,6,7,8,9,10,11: always X...X...X...X...  from energy 25 +.......+.......  weights .......4.42d...2 */ \
    {16, 0, 0, 0, 0x1010, 0, TW(0,0,0,0,0,0,0,4,0,4,2,13,0,0,0,2), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0101, 0x0000, TL(0x0129, 0x0101), 0}, \
    /* AFRO HOUSE KICK, variations 0,1,2,3,4,5,6,7,8,9,10,11 (even bars): always X...X...X...X...  from energy 25 +.......+.......  weights ......2f.42..2d4 */ \
    {255, 0, 0, 0, 0x1010, 0, TW(0,0,0,0,0,0,2,15,0,4,2,0,0,2,13,4), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0101, 0x4000, TL(0x0129, 0x0101), 96}, \
    /* AFRO HOUSE CLAP 1/2, variations 0,1,2,3,4,5,6,7,8,9,10: always ....X.......X...  from energy 25 ................  weights .......5.572..57 */ \
    {16, 9, 92, 0, 0x1010, 0, TW(0,0,0,0,0,0,0,5,0,5,7,2,0,0,5,7), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x8000, TL(0x11FC, 0x0100), 106}, \
    /* AFRO HOUSE CLAP 2/2, variations 11: always ...........x....  from energy 25 ................  weights ................ */ \
    {16, 9, 8, 0, 0x0800, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AFRO HOUSE HAT 1/3, variations 0,1,2,3,4,5,6: always ..x...x...x...x.  from energy 25 ..+.......+.....  weights 14.b14.111.f14.1 */ \
    {16, 2, 58, 0, 0x4040, 0, TW(1,4,0,11,1,4,0,1,1,1,0,15,1,4,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x0404, 0x4000, TL(0x8E02, 0x8E0E), 100}, \
    /* AFRO HOUSE HAT 2/3, variations 7,8,9: always x.xxx.xxx.xxx.xx  from energy 25 +..++..++..++..+  weights .1...1...9...9.. */ \
    {16, 2, 25, 0, 0x4444, 0, TW(0,1,0,0,0,1,0,0,0,9,0,0,0,9,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x9999, 0x8000, TL(0x0C0C, 0x0808), 106}, \
    /* AFRO HOUSE HAT 3/3, variations 10,11: always xxxxxxxxxXxxxxxx  from energy 25 .+...+...+...+..  weights ................ */ \
    {16, 2, 17, 0, 0xDDDD, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x2222, 0x0000, TL(0x0004, 0x0000), 0}, \
    /* AFRO HOUSE SHAKER 1/2, variations 0,1,2,3,4,5,6,7,8: always xo.oxoxoxo.oxoxo  from energy 25 ....++.+.+.+.+.+  weights ..f.......f..... */ \
    {16, 12, 75, 0, 0x514B, 0, TW(0,0,15,0,0,0,0,0,0,0,15,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0xAAB0, 0x0000, TL(0x88A8, 0x88A8), 0}, \
    /* AFRO HOUSE SHAKER 2/2, variations 9,10,11: always ..o...o...o...o.  from energy 25 ..+.......+.....  weights 11.111.111.111.1 */ \
    {16, 12, 25, 0, 0x4040, 0, TW(1,1,0,1,1,1,0,1,1,1,0,1,1,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0404, 0x0000, TL(0xAAAA, 0xAAAA), 0}, \
    /* AFRO HOUSE CONGA 1/4, variations 0,1,2,3,4: always x..x..x...x.x..x  from energy 25 ...+........+..+  weights .f5.1..15..5.11. */ \
    {16, 13, 42, 0, 0x0441, 0, TW(0,15,5,0,1,0,0,1,5,0,0,5,0,1,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x9008, 0x0000, TL(0x2802, 0x820C), 0}, \
    /* AFRO HOUSE CONGA 1/4, variations 0,1,2,3,4 (even bars): always x..x..x.o.x.x.oo  from energy 25 ...+........+.++  weights ..5.1..1...1.1.. */ \
    {255, 13, 42, 0, 0x0541, 0, TW(0,0,5,0,1,0,0,1,0,0,0,1,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0xD008, 0x0000, TL(0xA882, 0x8200), 0}, \
    /* AFRO HOUSE CONGA 2/4, variations 5,6,7: always x.ox..x.x.ox..x.  from energy 25 ..++.......+..+.  weights .1...9.9....11.1 */ \
    {16, 13, 25, 0, 0x0541, 0, TW(0,1,0,0,0,9,0,9,0,0,0,0,1,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x480C, 0x4000, TL(0x8A20, 0xCC2C), 106}, \
    /* AFRO HOUSE CONGA 3/4, variations 8,9: always ...x..x....x.xx.  from energy 25 ...........+.+..  weights 111....d1.1.1..1 */ \
    {16, 13, 17, 0, 0x4048, 0, TW(1,1,1,0,0,0,0,13,1,0,1,0,1,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2800, 0x4000, TL(0x8222, 0xC02E), 96}, \
    /* AFRO HOUSE CONGA 4/4, variations 10,11: always ..o.x..x..o.x.x.  from energy 25 ..+.+..+........  weights 11.1..1.1..1.d.1 */ \
    {16, 13, 17, 0, 0x5400, 0, TW(1,1,0,1,0,0,1,0,1,0,0,1,0,13,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0094, 0x4000, TL(0x8CA2, 0x20AE), 96}, \
    /* AFRO HOUSE PERC 1/4, variations 2,3,4,5,6: always x.x..x..x.x..x..  from energy 25 .....+..+....+..  weights .1.a1.15.1..1.11 */ \
    {16, 3, 42, 0, 0x0405, 0, TW(0,1,0,10,1,0,1,5,0,1,0,0,1,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x2120, 0x0000, TL(0xA208, 0xE2C0), 0}, \
    /* AFRO HOUSE PERC 1/4, variations 2,3,4,5,6 (even bars): always x.x..x..x.x.xx.x  from energy 25 .....+..+....+.+  weights .1.11.15.a....5. */ \
    {255, 3, 42, 0, 0x1405, 0, TW(0,1,0,1,1,0,1,5,0,10,0,0,0,0,5,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0xA120, 0x0000, TL(0x0000, 0x2280), 0}, \
    /* AFRO HOUSE PERC 2/4, variations 7,8,9: always ..x.x..x..x.x..x  from energy 25 ....+..+.......+  weights 1..1.11.19.9.11. */ \
    {16, 3, 25, 0, 0x1404, 0, TW(1,0,0,1,0,1,1,0,1,9,0,9,0,1,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x8090, 0x8000, TL(0x288E, 0x2882), 85}, \
    /* AFRO HOUSE PERC 3/4, variations 0,1: always x..x..x...x..x..  from energy 25 ...+..+.........  weights ..1.11.d11..1.11 */ \
    {16, 3, 17, 0, 0x2401, 0, TW(0,0,1,0,1,1,0,13,1,1,0,0,1,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0048, 0x2000, TL(0xA20A, 0xCA20), 96}, \
    /* AFRO HOUSE PERC 4/4, variations 10,11: always .X..x.x..x..x.x.  from energy 25 ......+..+....+.  weights 1.11.1.11.d..1.1 */ \
    {16, 3, 17, 0, 0x1012, 0, TW(1,0,1,1,0,1,0,1,1,0,13,0,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4240, 0x0000, TL(0x8822, 0x88A6), 0}, \
    /* AFRO HOUSE RIM 1/4, variations 0,1: always ...x..........x.  from energy 25 ................  weights ......dd...d.... */ \
    {16, 15, 33, 0, 0x4008, 0, TW(0,0,0,0,0,0,13,13,0,0,0,13,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AFRO HOUSE RIM 2/4, variations 3,4: always ......x.....x...  from energy 25 ................  weights ...............d */ \
    {16, 15, 33, 0, 0x1040, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,13), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x1000, TL(0xC000, 0x0000), 96}, \
    /* AFRO HOUSE RIM 3/4, variations 2: always ...x..x....x...x  from energy 25 ...........+...+  weights ................ */ \
    {16, 15, 17, 0, 0x0048, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x8800, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AFRO HOUSE RIM 4/4, variations 5: always ..x..x....x..x..  from energy 25 .....+.......+..  weights ................ */ \
    {16, 15, 17, 0, 0x0404, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2020, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AFRO HOUSE TOM 1/3, variations 0,1,2,3: always ..............x.  from energy 25 ................  weights 1.....d...1.d1.6 */ \
    {16, 14, 67, 0, 0x4000, 0, TW(1,0,0,0,0,0,13,0,0,0,1,0,13,1,0,6), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0000, 0x0000, TL(0x0820, 0x0002), 0}, \
    /* AFRO HOUSE TOM 1/3, variations 0,1,2,3 (even bars): always ..............x.  from energy 25 ................  weights 6.....d...1.d1.d */ \
    {255, 14, 67, 0, 0x4000, 0, TW(6,0,0,0,0,0,13,0,0,0,1,0,13,1,0,13), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0820, 0x0000), 0}, \
    /* AFRO HOUSE TOM 2/3, variations 4: always x.....x.....x...  from energy 25 ................  weights ..............11 */ \
    {16, 14, 17, 0, 0x1041, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0xA000, 0x0000), 0}, \
    /* AFRO HOUSE TOM 3/3, variations 5: always ..........x..x..  from energy 25 ................  weights 1.....1.....1.11 */ \
    {16, 14, 17, 0, 0x2400, 0, TW(1,0,0,0,0,0,1,0,0,0,0,0,1,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0xA200, 0x2002), 0}, \
    /* AFRO HOUSE BASS 1/2, variations 1,2,3,4,5,6,7,8,9,10,11: always ......x...x..x..  from energy 25 ................  weights e2e1.....2....22 */ \
    {16, 4, 92, 0, 0x2440, 0, TW(14,2,14,1,0,0,0,0,0,2,0,0,0,0,2,2), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0xA008, 0x0008), 0}, \
    /* AFRO HOUSE BASS 2/2, variations 0: always x..x......x.....  from energy 25 ................  weights ..1...1......1.. */ \
    {16, 4, 8, 0, 0x0409, 0, TW(0,0,1,0,0,0,1,0,0,0,0,0,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AFRO HOUSE CHORD 1/2, variations 0,1,2,3,4,5,6: always ..x.....x.....x.  from energy 25 ................  weights 1.....1...1..... */ \
    {16, 5, 58, 0, 0x4104, 0, TW(1,0,0,0,0,0,1,0,0,0,1,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AFRO HOUSE CHORD 2/2, variations 7,8,9,10,11: always x.....x...x.....  from energy 25 ................  weights ..1.....1.....1. */ \
    {16, 5, 42, 0, 0x0441, 0, TW(0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AFRO HOUSE VOX 1/4, variations 1,2,3: always ...x......x.....  from energy 25 ................  weights 1.1.1.1.1...1.9. */ \
    {16, 25, 50, 0, 0x0408, 0, TW(1,0,1,0,1,0,1,0,1,0,0,0,1,0,9,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x2000, 0x0000), 0}, \
    /* AFRO HOUSE VOX 2/4, variations 0: always ......x.........  from energy 25 ................  weights ...1......1..... */ \
    {16, 25, 17, 0, 0x0040, 0, TW(0,0,0,1,0,0,0,0,0,0,1,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AFRO HOUSE VOX 3/4, variations 4: always x.......x.x.....  from energy 25 ................  weights ...1............ */ \
    {16, 25, 17, 0, 0x0501, 0, TW(0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AFRO HOUSE VOX 4/4, variations 5: always ..x.x.......x...  from energy 25 ................  weights ...1......1..... */ \
    {16, 25, 17, 0, 0x1014, 0, TW(0,0,0,1,0,0,0,0,0,0,1,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AFRO HOUSE ARP 1/2, variations 2,3,4,5: always x.xx.x.xx.xx.x.x  from energy 25 ..+..+.+..++....  weights ......6..6..6... */ \
    {16, 6, 67, 0, 0xA109, 0, TW(0,0,0,0,0,0,6,0,0,6,0,0,6,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0CA4, 0x0000, TL(0x0208, 0x2000), 0}, \
    /* AFRO HOUSE ARP 2/2, variations 0,1: always x..x..x..x..x..x  from energy 25 ......+..+..+...  weights ..1..1.11.11.d.. */ \
    {16, 6, 33, 0, 0x8009, 0, TW(0,0,1,0,0,1,0,1,1,0,1,1,0,13,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1240, 0x0000, TL(0x0800, 0x0000), 0}, \
    /* AMAPIANO KICK 1/2, variations 4,5,6,7,8,9,10,11: always X..x....X..x....  from energy 25 ...+.......+....  weights .........4...... */ \
    {17, 0, 67, 0, 0x0101, 0, TW(0,0,0,0,0,0,0,0,0,4,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0808, 0x0000, TL(0x0009, 0x0001), 0}, \
    /* AMAPIANO KICK 1/2, variations 4,5,6,7,8,9,10,11 (even bars): always X.......X..x..x.  from energy 25 ...........+..+.  weights ..4....4.....4.b */ \
    {255, 0, 67, 0, 0x0101, 0, TW(0,0,4,0,0,0,0,4,0,0,0,0,0,4,0,11), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x4800, 0xC000, TL(0x8001, 0x8021), 85}, \
    /* AMAPIANO KICK 2/2, variations 0,1,2,3: always X...X...X......x  from energy 25 ....+..........+  weights ............d6.. */ \
    {17, 0, 33, 0, 0x0101, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,13,6,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x8010, 0x0000, TL(0x0901, 0x0101), 0}, \
    /* AMAPIANO CLAP 1/3, variations 0,1,2,3,4,5,6: always ....X.......X...  from energy 25 ................  weights .......7.4....77 */ \
    {17, 9, 58, 0, 0x1010, 0, TW(0,0,0,0,0,0,0,7,0,4,0,0,0,0,7,7), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x8000, TL(0x110C, 0x0100), 96}, \
    /* AMAPIANO CLAP 2/3, variations 7,8,9,10: always ......x.......x.  from energy 25 ................  weights .......6...6...6 */ \
    {17, 9, 33, 0, 0x4040, 0, TW(0,0,0,0,0,0,0,6,0,0,0,6,0,0,0,6), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x4000, TL(0xC0C0, 0xC000), 111}, \
    /* AMAPIANO CLAP 3/3, variations 11: always ...x...x...x..x.  from energy 25 ...+.......+....  weights ................ */ \
    {17, 9, 8, 0, 0x4080, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0808, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AMAPIANO SHAKER 1/2, variations 0,1,2,3,4,5,6,7,8,9,10: always xoxoxoxoxoxoxoxo  from energy 25 ++.+++.+++.+++.+  weights ................ */ \
    {17, 12, 92, 0, 0x4444, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0xBBBB, 0x0000, TL(0x8888, 0x8888), 0}, \
    /* AMAPIANO SHAKER 1/2, variations 0,1,2,3,4,5,6,7,8,9,10 (even bars): always xoxo.oxoxoxoxoxo  from energy 25 ++.+.+.+++.+++.+  weights ....e........... */ \
    {255, 12, 92, 0, 0x4444, 0, TW(0,0,0,0,14,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0xBBAB, 0x0000, TL(0x8888, 0x8888), 0}, \
    /* AMAPIANO SHAKER 2/2, variations 11: always ..o...o...o...o.  from energy 25 ......+.......+.  weights 11.111.111.111.1 */ \
    {17, 12, 8, 0, 0x0404, 0, TW(1,1,0,1,1,1,0,1,1,1,0,1,1,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4040, 0x0000, TL(0xAAAA, 0xAAAA), 0}, \
    /* AMAPIANO HAT 1/3, variations 0,1,2,3,4: always oxxooxxooxxooxxx  from energy 25 .+.+.+.+.+.+.+.+  weights ................ */ \
    {17, 2, 42, 0, 0x5555, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0xAAAA, 0x0000, TL(0x0282, 0x8282), 0}, \
    /* AMAPIANO HAT 2/3, variations 8,9,10,11: always ..x...x...x...x.  from energy 25 ..+.......+.....  weights 11.111.111.116.6 */ \
    {17, 2, 33, 0, 0x4040, 0, TW(1,1,0,1,1,1,0,1,1,1,0,1,1,6,0,6), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x0404, 0x0000, TL(0x028A, 0x8A8A), 0}, \
    /* AMAPIANO HAT 3/3, variations 5,6,7: always x.x.x.x.x.x.x.x.  from energy 25 +...+...+...+...  weights .9.f.1.1.1.1.1.1 */ \
    {17, 2, 25, 0, 0x4444, 0, TW(0,9,0,15,0,1,0,1,0,1,0,1,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x1111, 0x4000, TL(0x8888, 0x88CC), 85}, \
    /* AMAPIANO RIM 1/3, variations 0,1,2: always ...x..x.......x.  from energy 25 ................  weights ..........d..... */ \
    {17, 15, 50, 0, 0x4048, 0, TW(0,0,0,0,0,0,0,0,0,0,13,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AMAPIANO RIM 2/3, variations 3,4: always ......x.........  from energy 25 ................  weights .........d..d.d. */ \
    {17, 15, 33, 0, 0x0040, 0, TW(0,0,0,0,0,0,0,0,0,13,0,0,13,0,13,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AMAPIANO RIM 3/3, variations 5: always ..x..x....x..x..  from energy 25 .....+.......+..  weights ................ */ \
    {17, 15, 17, 0, 0x0404, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2020, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AMAPIANO PERC 1/4, variations 2,3,4: always ...x...x...x..xx  from energy 25 ...........+...+  weights 111..11.1.1..1.. */ \
    {17, 3, 50, 0, 0x4088, 0, TW(1,1,1,0,0,1,1,0,1,0,1,0,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x8800, 0x0000, TL(0x0822, 0x282A), 0}, \
    /* AMAPIANO PERC 1/4, variations 2,3,4 (even bars): always ...x...x..x.x.x.  from energy 25 .......+....+...  weights 199..11.19.1.1.f */ \
    {255, 3, 50, 0, 0x4408, 0, TW(1,9,9,0,0,1,1,0,1,9,0,1,0,1,0,15), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x1080, 0x0000, TL(0x088E, 0x280E), 0}, \
    /* AMAPIANO PERC 2/4, variations 0: always ..x..x....x..x..  from energy 25 .....+.......+..  weights .1.1...1...11.11 */ \
    {17, 3, 17, 0, 0x0404, 0, TW(0,1,0,1,0,0,0,1,0,0,0,1,1,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2020, 0x0000, TL(0xA280, 0x8088), 0}, \
    /* AMAPIANO PERC 3/4, variations 1: always .x...x.x..x...x.  from energy 25 .+...+..........  weights ..11.......11..1 */ \
    {17, 3, 17, 0, 0x4480, 0, TW(0,0,1,1,0,0,0,0,0,0,0,1,1,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0022, 0x0000, TL(0x8280, 0x00A0), 0}, \
    /* AMAPIANO PERC 4/4, variations 5: always x..x..x.x..x....  from energy 25 ......+....+....  weights .11..1.1..1.1.11 */ \
    {17, 3, 17, 0, 0x0109, 0, TW(0,1,1,0,0,1,0,1,0,0,1,0,1,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0840, 0x0000, TL(0xA220, 0x8828), 0}, \
    /* AMAPIANO LOG DRUM 1/4, variations 0,1,2,3: always x.....x...x..x..  from energy 25 ......+......+..  weights ..16.1.116..1.1. */ \
    {17, 20, 40, 0, 0x0401, 0, TW(0,0,1,6,0,1,0,1,1,6,0,0,1,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2040, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AMAPIANO LOG DRUM 2/4, variations 5,6: always ...x..x...x.x...  from energy 25 ...+........+...  weights 1.1.....1....11. */ \
    {17, 20, 20, 0, 0x0440, 0, TW(1,0,1,0,0,0,0,0,1,0,0,0,0,1,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1008, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AMAPIANO LOG DRUM 3/4, variations 7,8: always x..x....x.x...x.  from energy 25 ...+..........+.  weights ..1...1.....11.. */ \
    {17, 20, 20, 0, 0x0501, 0, TW(0,0,1,0,0,0,1,0,0,0,0,0,1,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4008, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AMAPIANO LOG DRUM 4/4, variations 10,11: always ..x..x.x..x..x..  from energy 25 .....+.+........  weights 1..1..1.1...1.1. */ \
    {17, 20, 20, 0, 0x2404, 0, TW(1,0,0,1,0,0,1,0,1,0,0,0,1,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x00A0, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AMAPIANO BASS 1/3, variations 2,3,4: always x.......x.......  from energy 25 ................  weights ..19.11...9.119. */ \
    {17, 4, 50, 0, 0x0101, 0, TW(0,0,1,9,0,1,1,0,0,0,9,0,1,1,9,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AMAPIANO BASS 2/3, variations 0,1: always ...x..x...x.x...  from energy 25 ...+..+.........  weights 1.......1.....1. */ \
    {17, 4, 33, 0, 0x1400, 0, TW(1,0,0,0,0,0,0,0,1,0,0,0,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0048, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AMAPIANO BASS 3/3, variations 5: always ..x..x.x..x..x..  from energy 25 .......+.....+..  weights 1............... */ \
    {17, 4, 17, 0, 0x0424, 0, TW(1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x2080, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AMAPIANO PIANO 1/4, variations 3,4,5,6,7: always ..x...x...x...x.  from energy 25 ..+.......+.....  weights 1..1.1.115.1.1.1 */ \
    {17, 23, 42, 0, 0x4040, 0, TW(1,0,0,1,0,1,0,1,1,5,0,1,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0404, 0x0000, TL(0x0008, 0x0000), 0}, \
    /* AMAPIANO PIANO 2/4, variations 0,1,2: always x..x..X...x..x..  from energy 25 ...+.........+..  weights ..1..d........1. */ \
    {17, 23, 25, 0, 0x0441, 0, TW(0,0,1,0,0,13,0,0,0,0,0,0,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2008, 0x0000, TL(0x0000, 0x1800), 0}, \
    /* AMAPIANO PIANO 3/4, variations 8,9: always ..X..x.x..x..x.x  from energy 25 .......+.....+.+  weights 1..1d.1.......1. */ \
    {17, 23, 17, 0, 0x0424, 0, TW(1,0,0,1,13,0,1,0,0,0,0,0,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0xA080, 0x0000, TL(0x0000, 0x0210), 0}, \
    /* AMAPIANO PIANO 4/4, variations 10,11: always x..x..x.x..x..x.  from energy 25 ...+....+..+....  weights ..1..d....1..1.. */ \
    {17, 23, 17, 0, 0x4041, 0, TW(0,0,1,0,0,13,0,0,0,0,1,0,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0908, 0x0000, TL(0x0000, 0x0800), 0}, \
    /* AMAPIANO PAD, variations 0,1,2,3,4,5: always x...............  from energy 25 ................  weights ......4.9....... */ \
    {17, 22, 0, 0, 0x0001, 0, TW(0,0,0,0,0,0,4,0,9,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0001, 0x0000), 0}, \
    /* AMAPIANO VOX 1/3, variations 3,4,5: always ..x.x.......x...  from energy 25 ................  weights 1..1....1.11.99. */ \
    {17, 25, 50, 0, 0x1014, 0, TW(1,0,0,1,0,0,0,0,1,0,1,1,0,9,9,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x2880, 0x0000), 0}, \
    /* AMAPIANO VOX 2/3, variations 0,1: always ...x......x.....  from energy 25 ................  weights 1.1.1...1..d111. */ \
    {17, 25, 33, 0, 0x0408, 0, TW(1,0,1,0,1,0,0,0,1,0,0,13,1,1,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x2880, 0x0000), 0}, \
    /* AMAPIANO VOX 3/3, variations 2: always x.......x.x.....  from energy 25 ................  weights ..111.......1... */ \
    {17, 25, 17, 0, 0x0501, 0, TW(0,0,1,1,1,0,0,0,0,0,0,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* AMAPIANO ARP 1/2, variations 1,2,3,4,5: always ..x.x...x.x...x.  from energy 25 ..+...........+.  weights 1..1..1..5..15.5 */ \
    {17, 6, 83, 0, 0x0510, 0, TW(1,0,0,1,0,0,1,0,0,5,0,0,1,5,0,5), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4004, 0x0000, TL(0x8808, 0x0000), 0}, \
    /* AMAPIANO ARP 2/2, variations 0: always x..x..x..x..x...  from energy 25 ...+..+.........  weights ..1.1...1.1...1. */ \
    {17, 6, 17, 0, 0x1201, 0, TW(0,0,1,0,1,0,0,0,1,0,1,0,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0048, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* FOOTWORK KICK 1/2, variations 0,1,2,3,4,5,6,7,8: always X..X......X..X..  from energy 25 ...+.........+..  weights ..3...6........6 */ \
    {18, 0, 75, 0, 0x0401, 0, TW(0,0,3,0,0,0,6,0,0,0,0,0,0,0,0,6), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x2008, 0x0000, TL(0x0410, 0x1051), 0}, \
    /* FOOTWORK KICK 1/2, variations 0,1,2,3,4,5,6,7,8 (even bars): always X..X..X...X.X...  from energy 25 ...+..+.........  weights .......3.3.3.6f. */ \
    {255, 0, 75, 0, 0x1401, 0, TW(0,0,0,0,0,0,0,3,0,3,0,3,0,6,15,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0048, 0x0000, TL(0x1510, 0x5041), 0}, \
    /* FOOTWORK KICK 2/2, variations 9,10,11: always X.....X..x..X...  from energy 25 ......+..+......  weights ...f...........f */ \
    {18, 0, 25, 0, 0x1001, 0, TW(0,0,0,15,0,0,0,0,0,0,0,0,0,0,0,15), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0240, 0x0000, TL(0x0100, 0x1041), 0}, \
    /* FOOTWORK SNARE 1/2, variations 5,6,7,8,9,10,11: always ....x.......X..x  from energy 25 ................  weights ..4..4..44.4.... */ \
    {18, 1, 58, 0, 0x9010, 0, TW(0,0,4,0,0,4,0,0,4,4,0,4,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x8000, TL(0x01CF, 0x0820), 96}, \
    /* FOOTWORK SNARE 2/2, variations 0,1,2,3,4: always ........X.......  from energy 25 ................  weights ....5......a.5f5 */ \
    {18, 1, 42, 0, 0x0100, 0, TW(0,0,0,0,5,0,0,0,0,0,0,10,0,5,15,5), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x4000, TL(0xCCC1, 0x0300), 85}, \
    /* FOOTWORK CLAP 1/2, variations 0,1,2,3,4: always ....X.......X...  from energy 25 ................  weights .......5......55 */ \
    {18, 9, 83, 0, 0x1010, 0, TW(0,0,0,0,0,0,0,5,0,0,0,0,0,0,5,5), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x1100, 0x0100), 0}, \
    /* FOOTWORK CLAP 2/2, variations 5: always ...x..x....x..x.  from energy 25 ...+.......+....  weights ................ */ \
    {18, 9, 17, 0, 0x4040, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0808, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* FOOTWORK HAT 1/4, variations 4,5,6,7: always ..x...x...x..gx.  from energy 25 .............++.  weights 11.11..616..1..1 */ \
    {18, 2, 33, 0, 0x0444, 0, TW(1,1,0,1,1,0,0,6,1,6,0,0,1,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x6000, 0x0000, TL(0x8E0E, 0xC28A), 0}, \
    /* FOOTWORK HAT 2/4, variations 8,9,10,11: always x..x..x..x..x..x  from energy 25 ...+.....+.....+  weights .61.1..d1.1..61. */ \
    {18, 2, 33, 0, 0x1041, 0, TW(0,6,1,0,1,0,0,13,1,0,1,0,0,6,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x8208, 0x8000, TL(0x2C22, 0xC22C), 96}, \
    /* FOOTWORK HAT 3/4, variations 0,1,2: always x.x.x.x.x.x.x.x.  from energy 25 +...+...+...+...  weights ...9...1.1.9.1.1 */ \
    {18, 2, 25, 0, 0x4444, 0, TW(0,0,0,9,0,0,0,1,0,1,0,9,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x1111, 0x4000, TL(0x8C88, 0xC080), 85}, \
    /* FOOTWORK HAT 4/4, variations 3: always xxx.xxx.xxx.xxx.  from energy 25 .+...+...+...+..  weights ...1...1.......1 */ \
    {18, 2, 8, 0, 0x5555, 0, TW(0,0,0,1,0,0,0,1,0,0,0,0,0,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x2222, 0x0000, TL(0x8000, 0xC080), 0}, \
    /* FOOTWORK PERC 1/4, variations 0,1,2,3: always x..x..x..x..x..x  from energy 25 ...+.....+..+...  weights .61.1..11.16.61. */ \
    {18, 3, 33, 0, 0x8041, 0, TW(0,6,1,0,1,0,0,1,1,0,1,6,0,6,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1208, 0x0000, TL(0x28A2, 0x822C), 0}, \
    /* FOOTWORK PERC 2/4, variations 4,5,6: always x.x...x.x.x...x.  from energy 25 ..+.....+.....+.  weights .1.11..1.1.919.1 */ \
    {18, 3, 25, 0, 0x0441, 0, TW(0,1,0,1,1,0,0,1,0,1,0,9,1,9,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x4104, 0x0000, TL(0x8EC8, 0x8288), 0}, \
    /* FOOTWORK PERC 2/4, variations 4,5,6 (even bars): always x.x...x.x.x.xx.x  from energy 25 ..+.....+....+.+  weights .9.11..1.1....9. */ \
    {255, 3, 25, 0, 0x1441, 0, TW(0,9,0,1,1,0,0,1,0,1,0,0,0,0,9,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0xA104, 0x0000, TL(0x0008, 0x8280), 0}, \
    /* FOOTWORK PERC 3/4, variations 9,10,11: always .x..x..x..x..x..  from energy 25 .+..+...........  weights 1.11.91.11.91.11 */ \
    {18, 3, 25, 0, 0x2480, 0, TW(1,0,1,1,0,9,1,0,1,1,0,9,1,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0012, 0x2000, TL(0xA28A, 0x2CA2), 85}, \
    /* FOOTWORK PERC 4/4, variations 7,8: always ..x....x..x....x  from energy 25 ..+....+........  weights 11.11.1.11.11d1. */ \
    {18, 3, 17, 0, 0x8400, 0, TW(1,1,0,1,1,0,1,0,1,1,0,1,1,13,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0084, 0x8000, TL(0x2E8A, 0x228A), 96}, \
    /* FOOTWORK TOM 1/4, variations 1,2: always ..............x.  from energy 25 ................  weights 1.11.1d.1111d1.d */ \
    {18, 14, 33, 0, 0x4000, 0, TW(1,0,1,1,0,1,13,0,1,1,1,1,13,1,0,13), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0000, 0x0000, TL(0x08AA, 0x08A2), 0}, \
    /* FOOTWORK TOM 1/4, variations 1,2 (even bars): always ..............xx  from energy 25 ................  weights d.11.1d.1111d1.. */ \
    {255, 14, 33, 0, 0xC000, 0, TW(13,0,1,1,0,1,13,0,1,1,1,1,13,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x08AA, 0x08A0), 0}, \
    /* FOOTWORK TOM 2/4, variations 3,5: always x.....x.....x...  from energy 25 ................  weights ..1d.1..1d11.11d */ \
    {18, 14, 33, 0, 0x1041, 0, TW(0,0,1,13,0,1,0,0,1,13,1,1,0,1,1,13), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x28A2, 0x0820), 0}, \
    /* FOOTWORK TOM 3/4, variations 0: always ..x..x..x..x..x.  from energy 25 .....+.....+....  weights 1.....1.....1..1 */ \
    {18, 14, 17, 0, 0x4104, 0, TW(1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0820, 0x0000, TL(0x8200, 0x2002), 0}, \
    /* FOOTWORK TOM 4/4, variations 4: always ..........x..x..  from energy 25 ................  weights 1.....1.....1.11 */ \
    {18, 14, 17, 0, 0x2400, 0, TW(1,0,0,0,0,0,1,0,0,0,0,0,1,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0xA200, 0x2002), 0}, \
    /* FOOTWORK SUB 1/3, variations 7,8,9,10,11: always x.....x..x..x...  from energy 25 ......+..+..+...  weights ...1......1..5.. */ \
    {18, 19, 42, 0, 0x0001, 0, TW(0,0,0,1,0,0,0,0,0,0,1,0,0,5,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_WITH | TH_K_LV, 0x1240, 0x0000, TL(0x0800, 0x0000), 0}, \
    /* FOOTWORK SUB 2/3, variations 0,1,2,3: always x..x......x..x..  from energy 25 ...+......+..+..  weights ......6..1..1... */ \
    {18, 19, 33, 0, 0x0001, 0, TW(0,0,0,0,0,0,6,0,0,1,0,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_WITH | TH_K_LV, 0x2408, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* FOOTWORK SUB 3/3, variations 4,5,6: always x...............  from energy 25 ................  weights ...1..9.919.11.. */ \
    {18, 19, 25, 0, 0x0001, 0, TW(0,0,0,1,0,0,9,0,9,1,9,0,1,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_WITH | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* FOOTWORK CHORD 1/2, variations 0,1,2,3,4,5,6,7: always x.........x.....  from energy 25 ................  weights .1.3..1......33. */ \
    {18, 5, 67, 0, 0x0401, 0, TW(0,1,0,3,0,0,1,0,0,0,0,0,0,3,3,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x2800, 0x1088), 0}, \
    /* FOOTWORK CHORD 2/2, variations 8,9,10,11: always x..X..X.........  from energy 25 ................  weights .6........1..... */ \
    {18, 5, 33, 0, 0x0049, 0, TW(0,6,0,0,0,0,0,0,0,0,1,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x1048), 0}, \
    /* FOOTWORK VOX 1/3, variations 0,1,2,3: always x..x..x..x..x..x  from energy 25 .........+..+..+  weights ..1.1...1.1..... */ \
    {18, 25, 33, 0, 0x0049, 0, TW(0,0,1,0,1,0,0,0,1,0,1,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x9200, 0x0000, TL(0x0010, 0x0010), 0}, \
    /* FOOTWORK VOX 2/3, variations 4,5,6,7: always ...x......X.....  from energy 25 ................  weights 6.1.1.1.d6..1..1 */ \
    {18, 25, 33, 0, 0x0408, 0, TW(6,0,1,0,1,0,1,0,13,6,0,0,1,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0018, 0x0010), 0}, \
    /* FOOTWORK VOX 3/3, variations 8,9,10,11: always ..X.x.......x...  from energy 25 ................  weights 1..1..1.111...66 */ \
    {18, 25, 33, 0, 0x1014, 0, TW(1,0,0,1,0,0,1,0,1,1,1,0,0,0,6,6), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0xA010, 0x0010), 0}, \
    /* TRANCE KICK, variations 0,1,2,3,4,5,6,7,8,9,10,11: always X...X...X...X...  from energy 25 ....+.......+...  weights ..2..2...2.f..26 */ \
    {19, 0, 0, 0, 0x0101, 0, TW(0,0,2,0,0,2,0,0,0,2,0,15,0,0,2,6), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x1010, 0x0000, TL(0x4149, 0x0101), 0}, \
    /* TRANCE KICK, variations 0,1,2,3,4,5,6,7,8,9,10,11 (even bars): always X...X...X...X..x  from energy 25 ....+..........+  weights ...2.....4....f. */ \
    {255, 0, 0, 0, 0x1101, 0, TW(0,0,0,2,0,0,0,0,0,4,0,0,0,0,15,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x8010, 0x8000, TL(0x0101, 0x0101), 96}, \
    /* TRANCE CLAP 1/2, variations 0,1,2,3,4,5,6,7: always ....X.......X..x  from energy 25 ................  weights .5.....5.....55. */ \
    {19, 9, 67, 0, 0x9010, 0, TW(0,5,0,0,0,0,0,5,0,0,0,0,0,5,5,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x8000, TL(0x0D00, 0xC10C), 102}, \
    /* TRANCE CLAP 2/2, variations 8,9,10,11: always ............x...  from energy 25 ................  weights .........666.... */ \
    {19, 9, 33, 0, 0x1000, 0, TW(0,0,0,0,0,0,0,0,0,6,6,6,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x00A8, 0x0000), 0}, \
    /* TRANCE HAT 1/4, variations 6,7,8,9,10: always x.x.x.x.x.x.x.x.  from energy 25 +...+...+...+...  weights .5.5...5.1.5.1.1 */ \
    {19, 2, 42, 0, 0x4444, 0, TW(0,5,0,5,0,0,0,5,0,1,0,5,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x1111, 0x4000, TL(0x8888, 0xC0CC), 102}, \
    /* TRANCE HAT 2/4, variations 2,3,4,5: always ..xx..xx..xx..xx  from energy 25 ...+...+...+...+  weights 16..1...16..16.. */ \
    {19, 2, 33, 0, 0x4444, 0, TW(1,6,0,0,1,0,0,0,1,6,0,0,1,6,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x8888, 0x8000, TL(0x0E0A, 0x020E), 96}, \
    /* TRANCE HAT 3/4, variations 0,1: always ..x...x...X...x.  from energy 25 ......+.......+.  weights 11.11..11..11d.1 */ \
    {19, 2, 17, 0, 0x0404, 0, TW(1,1,0,1,1,0,0,1,1,0,0,1,1,13,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0x4040, 0x0000, TL(0x8A92, 0x828E), 0}, \
    /* TRANCE HAT 4/4, variations 11: always oxXxoxXxoxXxoxXx  from energy 25 .+.+.+.+.+.+.+.+  weights ................ */ \
    {19, 2, 8, 0, 0x5555, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_HAT, TH_K_LV, 0xAAAA, 0x0000, TL(0x1212, 0x1212), 0}, \
    /* TRANCE OPEN HAT 1/2, variations 0,1,2,3,4,5,6,7,8,9: always ..x...x...x...x.  from energy 25 ..+.......+.....  weights ...5.3.3.3.1.3.5 */ \
    {19, 10, 83, 0, 0x4040, 0, TW(0,0,0,5,0,3,0,3,0,3,0,1,0,3,0,5), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0404, 0x0000, TL(0x08C8, 0x8C80), 0}, \
    /* TRANCE OPEN HAT 2/2, variations 10,11: always ......x.......x.  from energy 25 ................  weights ..1.......1d.... */ \
    {19, 10, 17, 0, 0x4040, 0, TW(0,0,1,0,0,0,0,0,0,0,1,13,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x4000, TL(0x00E0, 0x0020), 96}, \
    /* TRANCE RIDE 1/3, variations 3,4,5: always x.oxx.oxx.oxx.ox  from energy 25 ...+...+...+...+  weights .9...9.......... */ \
    {19, 11, 50, 0, 0x5555, 0, TW(0,9,0,0,0,9,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x8888, 0x8000, TL(0x2020, 0x282C), 85}, \
    /* TRANCE RIDE 2/3, variations 1,2: always x.x.x.x.x.x.x.x.  from energy 25 +...+...+...+...  weights .1.1.1.1...1...1 */ \
    {19, 11, 33, 0, 0x4444, 0, TW(0,1,0,1,0,1,0,1,0,0,0,1,0,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1111, 0x0000, TL(0x8080, 0x888C), 0}, \
    /* TRANCE RIDE 3/3, variations 0: always ..x...x...x...x.  from energy 25 ..+.......+.....  weights 1..11..11..11..1 */ \
    {19, 11, 17, 0, 0x4040, 0, TW(1,0,0,1,1,0,0,1,1,0,0,1,1,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0404, 0x0000, TL(0x8282, 0x8282), 0}, \
    /* TRANCE PERC 1/3, variations 0,1,2: always ................  from energy 25 ................  weights 1..1..f11.f1.1f1 */ \
    {19, 3, 50, 0, 0x0000, 0, TW(1,0,0,1,0,0,15,1,1,0,15,1,0,1,15,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x9882, 0xC082), 0}, \
    /* TRANCE PERC 2/3, variations 3,4: always x.......x.......  from energy 25 ................  weights ...1..1d..11..1. */ \
    {19, 3, 33, 0, 0x0101, 0, TW(0,0,0,1,0,0,1,13,0,0,1,1,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0000, 0x0000, TL(0x00A0, 0xE080), 0}, \
    /* TRANCE PERC 2/3, variations 3,4 (even bars): always x.............xx  from energy 25 ................  weights ...1..1...11.d.. */ \
    {255, 3, 33, 0, 0xC001, 0, TW(0,0,0,1,0,0,1,0,0,0,1,1,0,13,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x00A0, 0x2080), 0}, \
    /* TRANCE PERC 3/3, variations 5: always ...x.......x....  from energy 25 ................  weights 1.....1.1.1...11 */ \
    {19, 3, 17, 0, 0x0808, 0, TW(1,0,0,0,0,0,1,0,1,0,1,0,0,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x8022, 0x2002), 0}, \
    /* TRANCE BASS 1/3, variations 4,5,6,7,8: always .xx..xx..xx..xx.  from energy 25 .+...+...+...+..  weights ...1...1...1...1 */ \
    {19, 4, 42, 0, 0x4444, 0, TW(0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2222, 0x0000, TL(0x0000, 0x4000), 0}, \
    /* TRANCE BASS 2/3, variations 0,1,2,3: always .xxx.xxX.xxx.xxx  from energy 25 ...+...+...+...+  weights ................ */ \
    {19, 4, 33, 0, 0x6666, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x8888, 0x0000, TL(0x0000, 0x4000), 0}, \
    /* TRANCE BASS 3/3, variations 9,10,11: always ..x...x...x...X.  from energy 25 ..+.......+.....  weights .1.1.1.1.1.1.1.1 */ \
    {19, 4, 25, 0, 0x4040, 0, TW(0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0404, 0x0000, TL(0x1000, 0x4000), 0}, \
    /* TRANCE PAD, variations 0,1,2,3,4,5,6,7,8,9,10,11: always x...............  from energy 25 ................  weights ......4.d.2..... */ \
    {19, 22, 0, 0, 0x0001, 0, TW(0,0,0,0,0,0,4,0,13,0,2,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0020, 0x0000), 0}, \
    /* TRANCE ARP 1/2, variations 4,5,6,7,8,9,10,11: always x.xxx.xxx.xxx.Xx  from energy 25 ..+...++..++...+  weights .1...1...1...3.. */ \
    {19, 6, 67, 0, 0x5119, 0, TW(0,1,0,0,0,1,0,0,0,1,0,0,0,3,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x8CC4, 0x0000, TL(0x1800, 0x0000), 0}, \
    /* TRANCE ARP 2/2, variations 0,1,2,3: always xxxxxxxxxxxxxxxx  from energy 25 .+...+...+...+..  weights ................ */ \
    {19, 6, 33, 0, 0xDDDD, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2222, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* TRANCE LEAD 1/4, variations 2,3,4,5: always x.xx.x.xx.x.x.x.  from energy 25 ..++.+.+..+...+.  weights ......6....1.6.6 */ \
    {19, 24, 33, 0, 0x1101, 0, TW(0,0,0,0,0,0,6,0,0,0,0,1,0,6,0,6), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x44AC, 0x0000, TL(0x8800, 0x2000), 0}, \
    /* TRANCE LEAD 2/4, variations 6,7,8,9: always x..x..x.x.......  from energy 25 ...+..+.........  weights ..1.61.1..161161 */ \
    {19, 24, 33, 0, 0x0101, 0, TW(0,0,1,0,6,1,0,1,0,0,1,6,1,1,6,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0048, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* TRANCE LEAD 3/4, variations 0,1: always x.xx.xx.x.xx.x.x  from energy 25 ..+..+....++.+.+  weights .......1....1.d. */ \
    {19, 24, 17, 0, 0x0149, 0, TW(0,0,0,0,0,0,0,1,0,0,0,0,1,0,13,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0xAC24, 0x0000, TL(0x2000, 0x0000), 0}, \
    /* TRANCE LEAD 4/4, variations 10,11: always x.......x...x...  from energy 25 ................  weights ..11.111..11.111 */ \
    {19, 24, 17, 0, 0x1101, 0, TW(0,0,1,1,0,1,1,1,0,0,1,1,0,1,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* UK DRILL KICK, variations 0,1,2,3,4,5,6,7,8,9,10,11: always X......x..x.....  from energy 25 ................  weights ..6..1...1...1.. */ \
    {20, 0, 0, 0, 0x0481, 0, TW(0,0,6,0,0,1,0,0,0,1,0,0,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_PICK, TH_K_LV | TH_K_TWO, 0x0000, 0x0000, TL(0x0000, 0x0001), 0}, \
    /* UK DRILL KICK, variations 0,1,2,3,4,5,6,7,8,9,10,11 (even bars): always X.........x.....  from energy 25 ................  weights ..1.1..c.3...3.5 */ \
    {255, 0, 0, 0, 0x0401, 0, TW(0,0,1,0,1,0,0,12,0,3,0,0,0,3,0,5), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_PICK, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0001), 0}, \
    /* UK DRILL SNARE, variations 0,1,2,3,4,5,6,7,8,9,10,11: always ........X.....X.  from energy 25 ................  weights .....26...69...4 */ \
    {20, 1, 0, 0, 0x4100, 0, TW(0,0,0,0,0,2,6,0,0,0,6,9,0,0,0,4), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0000, 0x0000, TL(0x90B1, 0x2000), 0}, \
    /* UK DRILL SNARE, variations 0,1,2,3,4,5,6,7,8,9,10,11 (even bars): always ........X.....X.  from energy 25 ................  weights ......f4..26.2.6 */ \
    {255, 1, 0, 0, 0x4100, 0, TW(0,0,0,0,0,0,15,4,0,0,2,6,0,2,0,6), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0000, 0x4000, TL(0x9081, 0xB000), 96}, \
    /* UK DRILL HAT, variations 0,1,2,3,4,5,6,7,8,9,10,11: always x.x.x.x.x.x.x.x.  from energy 25 +...+...+...+...  weights ...2.2...6...4.. */ \
    {20, 2, 0, 0, 0x4444, 0, TW(0,0,0,2,0,2,0,0,0,6,0,0,0,4,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x1111, 0x5000, TL(0x0808, 0x0880), 160}, \
    /* UK DRILL HAT, variations 0,1,2,3,4,5,6,7,8,9,10,11 (even bars): always x.x.x.x.x.x.x.x.  from energy 25 +...+...+...+...  weights ...2.4.2.2...6.b */ \
    {255, 2, 0, 0, 0x4444, 0, TW(0,0,0,2,0,4,0,2,0,2,0,0,0,6,0,11), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x1111, 0xC010, TL(0x0000, 0x0880), 176}, \
    /* UK DRILL PERC 1/4, variations 1,2: always ..x.....x.....x.  from energy 25 ................  weights ...1..11...d.1.. */ \
    {20, 3, 33, 0, 0x4104, 0, TW(0,0,0,1,0,0,1,1,0,0,0,13,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0000, 0x4000, TL(0x00C0, 0xA080), 160}, \
    /* UK DRILL PERC 2/4, variations 4,5: always .......x.....X..  from energy 25 ................  weights ..11..1.1..d..1. */ \
    {20, 3, 33, 0, 0x2080, 0, TW(0,0,1,1,0,0,1,0,1,0,0,13,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0000, 0x0000, TL(0x2482, 0x20A0), 0}, \
    /* UK DRILL PERC 3/4, variations 0: always ......x.......x.  from energy 25 ................  weights ..1....11..1.1.. */ \
    {20, 3, 17, 0, 0x4040, 0, TW(0,0,1,0,0,0,0,1,1,0,0,1,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0000, 0x0000, TL(0x0082, 0x8020), 0}, \
    /* UK DRILL PERC 4/4, variations 3: always ...x.......x....  from energy 25 ................  weights ..1....11....11. */ \
    {20, 3, 17, 0, 0x0808, 0, TW(0,0,1,0,0,0,0,1,1,0,0,0,0,1,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0000, 0x0000, TL(0x2002, 0x8020), 0}, \
    /* UK DRILL RIM 1/4, variations 1,2,3: always ......x.........  from energy 25 ................  weights ...9........9.f. */ \
    {20, 15, 50, 0, 0x0040, 0, TW(0,0,0,9,0,0,0,0,0,0,0,0,9,0,15,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* UK DRILL RIM 2/4, variations 0: always ...x......x.....  from energy 25 ................  weights ................ */ \
    {20, 15, 17, 0, 0x0408, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* UK DRILL RIM 3/4, variations 4: always ...x...x...x..x.  from energy 25 .......+...+....  weights ................ */ \
    {20, 15, 17, 0, 0x4008, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0880, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* UK DRILL RIM 4/4, variations 5: always ..x..x....x..x..  from energy 25 .....+.......+..  weights ................ */ \
    {20, 15, 17, 0, 0x0404, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2020, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* UK DRILL SUB, variations 0,1,2,3,4,5,6,7,8,9,10,11: always X...............  from energy 25 ................  weights ......2d2.f..... */ \
    {20, 19, 0, 0, 0x0001, 0, TW(0,0,0,0,0,0,2,13,2,0,15,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_WITH | TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0001), 0}, \
    /* UK DRILL PAD, variations 0,1,2,3,4,5,6,7,8,9,10,11: always x...............  from energy 25 ................  weights ......2.b.....9. */ \
    {20, 22, 0, 0, 0x0001, 0, TW(0,0,0,0,0,0,2,0,11,0,0,0,0,0,9,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x1000, 0x0000), 0}, \
    /* UK DRILL LEAD 1/4, variations 2,3,4: always x..x..x.x..x..x.  from energy 25 ...........+..+.  weights ..1.11.1..1.1... */ \
    {20, 24, 50, 0, 0x0149, 0, TW(0,0,1,0,1,1,0,1,0,0,1,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4800, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* UK DRILL LEAD 2/4, variations 0: always x.x.x.x.x.x.x.x.  from energy 25 ..+.......+.+.+.  weights ...1.......1.... */ \
    {20, 24, 17, 0, 0x0151, 0, TW(0,0,0,1,0,0,0,0,0,0,0,1,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x5404, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* UK DRILL LEAD 3/4, variations 1: always x.xx.x.xx.x.x.x.  from energy 25 ..+..+.+..+.....  weights ....1.1....1.... */ \
    {20, 24, 17, 0, 0x5109, 0, TW(0,0,0,0,1,0,1,0,0,0,0,1,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x04A4, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* UK DRILL LEAD 4/4, variations 5: always x...x.x.x.......  from energy 25 ....+.+.........  weights ..11......111.1. */ \
    {20, 24, 17, 0, 0x0101, 0, TW(0,0,1,1,0,0,0,0,0,0,1,1,1,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0050, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* UK DRILL VOX 1/3, variations 0,1,2,3: always ...x......x.....  from energy 25 ................  weights 1.1.1..61...d... */ \
    {20, 25, 67, 0, 0x0408, 0, TW(1,0,1,0,1,0,0,6,1,0,0,0,13,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x8000), 0}, \
    /* UK DRILL VOX 2/3, variations 4: always x.......x.x.....  from energy 25 ................  weights ...1........1... */ \
    {20, 25, 17, 0, 0x0501, 0, TW(0,0,0,1,0,0,0,0,0,0,0,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* UK DRILL VOX 3/3, variations 5: always ..x.x.......x...  from energy 25 ................  weights ...1......1..... */ \
    {20, 25, 17, 0, 0x1014, 0, TW(0,0,0,1,0,0,0,0,0,0,1,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* HARDCORE KICK 1/2, variations 0,1,2,3,4,5,6,7,8,9,10: always X...X...X...X...  from energy 25 ....+.......+...  weights .7...1...7.....1 */ \
    {21, 0, 92, 0, 0x0101, 0, TW(0,7,0,0,0,1,0,0,0,7,0,0,0,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_PICK, TH_K_LV | TH_K_TWO, 0x1010, 0x0000, TL(0x0105, 0x0905), 0}, \
    /* HARDCORE KICK 1/2, variations 0,1,2,3,4,5,6,7,8,9,10 (even bars): always X...X...X...X...  from energy 25 +.......+.......  weights .964.272..9..2f2 */ \
    {255, 0, 92, 0, 0x1010, 0, TW(0,9,6,4,0,2,7,2,0,0,9,0,0,2,15,2), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_PICK, TH_K_LV, 0x0101, 0x4000, TL(0x0101, 0x0985), 88}, \
    /* HARDCORE KICK 2/2, variations 11: always X.x.X.x.X.x.X.x.  from energy 25 ..+...+...+...+.  weights ................ */ \
    {21, 0, 8, 0, 0x1111, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_PICK, TH_K_LV, 0x4444, 0x0000, TL(0x0101, 0x0101), 0}, \
    /* HARDCORE CLAP, variations 0,1,2,3,4,5,6,7,8,9,10,11: always ....X.......X...  from energy 25 ................  weights ...2.2.d.2...42f */ \
    {21, 9, 0, 0, 0x1010, 0, TW(0,0,0,2,0,2,0,13,0,2,0,0,0,4,2,15), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0000, 0x8000, TL(0x190C, 0x0DC0), 109}, \
    /* HARDCORE CLAP, variations 0,1,2,3,4,5,6,7,8,9,10,11 (even bars): always ....X.......X...  from energy 25 ................  weights ...2.2.d.2...64f */ \
    {255, 9, 0, 0, 0x1010, 0, TW(0,0,0,2,0,2,0,13,0,2,0,0,0,6,4,15), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0000, 0xA000, TL(0x190C, 0x0DC0), 104}, \
    /* HARDCORE HAT 1/2, variations 0,1,2,3,4,5,6,7,8,9: always ..x...x...x...x.  from energy 25 ..+.......+.....  weights 15.335.31..513.. */ \
    {21, 2, 83, 0, 0x4040, 0, TW(1,5,0,3,3,5,0,3,1,0,0,5,1,3,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0404, 0x0000, TL(0x0E82, 0xC802), 0}, \
    /* HARDCORE HAT 1/2, variations 0,1,2,3,4,5,6,7,8,9 (even bars): always ..x...x...x...x.  from energy 25 ..+.......+.....  weights 1...1..31..1ff.f */ \
    {255, 2, 83, 0, 0x4040, 0, TW(1,0,0,0,1,0,0,3,1,0,0,1,15,15,0,15), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0404, 0x0000, TL(0x0082, 0xC202), 0}, \
    /* HARDCORE HAT 2/2, variations 10,11: always x.x.x.x.x.X.x.x.  from energy 25 +...+...+...+...  weights ...........d.1.1 */ \
    {21, 2, 17, 0, 0x4444, 0, TW(0,0,0,0,0,0,0,0,0,0,0,13,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1111, 0x0000, TL(0x8890, 0x0000), 0}, \
    /* HARDCORE OPEN HAT, variations 0,1,2,3,4,5: always ......x.......x.  from energy 25 ................  weights ..d4......d....9 */ \
    {21, 10, 0, 0, 0x4040, 0, TW(0,0,13,4,0,0,0,0,0,0,13,0,0,0,0,9), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x4000, TL(0x0000, 0x00C0), 85}, \
    /* HARDCORE PERC 1/4, variations 1,2: always ..x.x...x.x...x.  from energy 25 ..........+...+.  weights 11.1..11.1..1d.1 */ \
    {21, 3, 33, 0, 0x0114, 0, TW(1,1,0,1,0,0,1,1,0,1,0,0,1,13,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x4400, 0x4000, TL(0x8E08, 0xA08E), 96}, \
    /* HARDCORE PERC 2/4, variations 4,5: always x..x..x..x..x..x  from energy 25 ...+..+..+......  weights .d1.1..11.1..11. */ \
    {21, 3, 33, 0, 0x9001, 0, TW(0,13,1,0,1,0,0,1,1,0,1,0,0,1,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0248, 0x8000, TL(0x2C22, 0x822C), 96}, \
    /* HARDCORE PERC 3/4, variations 0: always x.......x.......  from energy 25 ................  weights ..111.1..11.1.11 */ \
    {21, 3, 17, 0, 0x0101, 0, TW(0,0,1,1,1,0,1,0,0,1,1,0,1,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0000, 0x0000, TL(0xA228, 0x22A0), 0}, \
    /* HARDCORE PERC 4/4, variations 3: always ....x..x....x..x  from energy 25 .......+.......+  weights 1.11..1.111...1. */ \
    {21, 3, 17, 0, 0x1010, 0, TW(1,0,1,1,0,0,1,0,1,1,1,0,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x8080, 0x0000, TL(0x202A, 0x20A2), 0}, \
    /* HARDCORE STAB 1/4, variations 0,1,2,3: always x.....x.....x...  from energy 25 ................  weights .611.1..1.61.11. */ \
    {21, 21, 33, 0, 0x1041, 0, TW(0,6,1,1,0,1,0,0,1,0,6,1,0,1,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0820, 0x0048), 0}, \
    /* HARDCORE STAB 2/4, variations 6,7,8,9: always ...X.......x....  from energy 25 ................  weights 161.611.1.1.161. */ \
    {21, 21, 33, 0, 0x0808, 0, TW(1,6,1,0,6,1,1,0,1,0,1,0,1,6,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0800, 0x0248), 0}, \
    /* HARDCORE STAB 3/4, variations 4,5: always X.......x.....x.  from energy 25 ................  weights ...1..1...11d... */ \
    {21, 21, 17, 0, 0x4101, 0, TW(0,0,0,1,0,0,1,0,0,0,1,1,13,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0200, 0x0041), 0}, \
    /* HARDCORE STAB 4/4, variations 10,11: always ..x..x....x.....  from energy 25 ................  weights 1..1..1....11d.. */ \
    {21, 21, 17, 0, 0x0424, 0, TW(1,0,0,1,0,0,1,0,0,0,0,1,1,13,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0800, 0x0040), 0}, \
    /* HARDCORE LEAD 1/4, variations 7,8,9,10,11: always x..x..x.x.......  from energy 25 ...+..+.........  weights ..1.55.1.1111511 */ \
    {21, 24, 42, 0, 0x0101, 0, TW(0,0,1,0,5,5,0,1,0,1,1,1,1,5,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0048, 0x0000, TL(0x0800, 0x0800), 0}, \
    /* HARDCORE LEAD 2/4, variations 3,4,5,6: always x.x.x.x.x.x.x.x.  from energy 25 ..+...+...+...+.  weights ...1.1.1.6.1.6.6 */ \
    {21, 24, 33, 0, 0x1111, 0, TW(0,0,0,1,0,1,0,1,0,6,0,1,0,6,0,6), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4444, 0x0000, TL(0x8808, 0x0000), 0}, \
    /* HARDCORE LEAD 3/4, variations 0,1: always x.xxxxxxxxxxxxxx  from energy 25 ....+.+..+.+.+.+  weights .d.............. */ \
    {21, 24, 17, 0, 0x55AD, 0, TW(0,13,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0xAA50, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* HARDCORE LEAD 4/4, variations 2: always x.xx.x.xx.x.x.x.  from energy 25 ...+.+.+......+.  weights ....1.1..1...1.1 */ \
    {21, 24, 8, 0, 0x1505, 0, TW(0,0,0,0,1,0,1,0,0,1,0,0,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x40A8, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* HARDCORE PAD, variations 0,1,2,3,4,5: always x...............  from energy 25 ................  weights ......9.4....... */ \
    {21, 22, 0, 0, 0x0001, 0, TW(0,0,0,0,0,0,9,0,4,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* HARDCORE BASS 1/2, variations 0,1,2,3,4: always x...x...x...x...  from energy 25 ....+.......+...  weights ..1...15..1...15 */ \
    {21, 4, 83, 0, 0x0101, 0, TW(0,0,1,0,0,0,1,5,0,0,1,0,0,0,1,5), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1010, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* HARDCORE BASS 2/2, variations 5: always x.x.x.x.x.x.x.x.  from energy 25 ..+...+...+...+.  weights ................ */ \
    {21, 4, 17, 0, 0x1111, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4444, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* PHONK KICK, variations 0,1,2,3,4,5,6,7,8,9,10,11: always X.........X.X...  from energy 25 ................  weights ..11.....1.2...4 */ \
    {22, 0, 0, 0, 0x1401, 0, TW(0,0,1,1,0,0,0,0,0,1,0,2,0,0,0,4), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_PICK, TH_K_LV | TH_K_TWO, 0x0000, 0x0000, TL(0x0114, 0x0081), 0}, \
    /* PHONK KICK, variations 0,1,2,3,4,5,6,7,8,9,10,11 (even bars): always X.........X.....  from energy 25 ................  weights ..1..1f4.1.52... */ \
    {255, 0, 0, 0, 0x0401, 0, TW(0,0,1,0,0,1,15,4,0,1,0,5,2,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_PICK, TH_K_LV, 0x0000, 0x0000, TL(0x0150, 0x0001), 0}, \
    /* PHONK SNARE, variations 0,1,2,3,4,5,6,7,8,9,10,11: always ........X.......  from energy 25 ................  weights .2.2.....b44..4. */ \
    {22, 1, 0, 0, 0x0100, 0, TW(0,2,0,2,0,0,0,0,0,11,4,4,0,0,4,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0000, 0x0000, TL(0x00FD, 0x0008), 0}, \
    /* PHONK SNARE, variations 0,1,2,3,4,5,6,7,8,9,10,11 (even bars): always ........X.....x.  from energy 25 ................  weights .2.222...4.222.f */ \
    {255, 1, 0, 0, 0x4100, 0, TW(0,2,0,2,2,2,0,0,0,4,0,2,2,2,0,15), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0000, 0xC000, TL(0x0009, 0x000C), 124}, \
    /* PHONK HAT 1/3, variations 0,1,2,3,4,6,7,8,9,10: always x.x.x.x.x.x.x.x.  from energy 25 ..+...+...+...+.  weights .5.1.1.5.1.3.1.3 */ \
    {22, 2, 83, 0, 0x1111, 0, TW(0,5,0,1,0,1,0,5,0,1,0,3,0,1,0,3), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x4444, 0x0400, TL(0xC888, 0xC88C), 160}, \
    /* PHONK HAT 1/3, variations 0,1,2,3,4,6,7,8,9,10 (even bars): always x.x.x.x.x.x.x.x.  from energy 25 ..+...+...+...+.  weights .5.1.1.8.1.5.3.f */ \
    {255, 2, 83, 0, 0x1111, 0, TW(0,5,0,1,0,1,0,8,0,1,0,5,0,3,0,15), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x4444, 0xD100, TL(0x0008, 0xC880), 167}, \
    /* PHONK HAT 2/3, variations 5: always x.xgx.x.xgx.x.x.  from energy 25 ...+..+..++...+.  weights .1.....1...1...1 */ \
    {22, 2, 8, 0, 0x1115, 0, TW(0,1,0,0,0,0,0,1,0,0,0,1,0,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4648, 0x0000, TL(0x808C, 0xC0CC), 0}, \
    /* PHONK HAT 3/3, variations 11: always xxxxxxxxxxxxxxxx  from energy 25 .+...+.+...+.+.+  weights ................ */ \
    {22, 2, 8, 0, 0x575D, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0xA8A2, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* PHONK COWBELL 1/4, variations 1,2: always x..x..x...x.....  from energy 25 ...+......+.....  weights ..1.11..1..1dd1. */ \
    {22, 17, 40, 0, 0x0041, 0, TW(0,0,1,0,1,1,0,0,1,0,0,1,13,13,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0408, 0x0000, TL(0x2082, 0x0A20), 0}, \
    /* PHONK COWBELL 2/4, variations 0: always x..x..x.x..x..x.  from energy 25 ...+.......+..+.  weights ..1.......1.11.. */ \
    {22, 17, 20, 0, 0x0141, 0, TW(0,0,1,0,0,0,0,0,0,0,1,0,1,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4808, 0x0000, TL(0x0A20, 0x0020), 0}, \
    /* PHONK COWBELL 3/4, variations 3: always ..x...x...x...x.  from energy 25 ......+.......+.  weights 1..1....1...11.. */ \
    {22, 17, 20, 0, 0x0404, 0, TW(1,0,0,1,0,0,0,0,1,0,0,0,1,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4040, 0x0000, TL(0x0A02, 0x0082), 0}, \
    /* PHONK COWBELL 4/4, variations 4: always ..x.x...x...x.x.  from energy 25 ....+.......+...  weights 1..1..1...1..1.. */ \
    {22, 17, 20, 0, 0x4104, 0, TW(1,0,0,1,0,0,1,0,0,0,1,0,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1010, 0x0000, TL(0x0820, 0x2082), 0}, \
    /* PHONK PERC 1/3, variations 0,1,2,3: always ......x.......x.  from energy 25 ................  weights 1.61.6.61.61.1.. */ \
    {22, 3, 67, 0, 0x4040, 0, TW(1,0,6,1,0,6,0,6,1,0,6,1,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0000, 0x0000, TL(0x0882, 0x8882), 0}, \
    /* PHONK PERC 2/3, variations 4: always ..x.....x..x....  from energy 25 ................  weights ......1...1...1. */ \
    {22, 3, 17, 0, 0x0904, 0, TW(0,0,0,0,0,0,1,0,0,0,1,0,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0000, 0x0000, TL(0x2020, 0x2000), 0}, \
    /* PHONK PERC 3/3, variations 5: always x..x..x...x..x..  from energy 25 ...+.........+..  weights ..1...........1. */ \
    {22, 3, 17, 0, 0x0441, 0, TW(0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x2008, 0x0000, TL(0x2000, 0x0020), 0}, \
    /* PHONK SUB 1/2, variations 0,1,2,3,4,5,11: always X.....x...X.....  from energy 25 ................  weights .4......1..441.. */ \
    {22, 19, 58, 0, 0x0441, 0, TW(0,4,0,0,0,0,0,0,1,0,0,4,4,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_WITH | TH_K_LV, 0x0000, 0x0000, TL(0x0190, 0x0009), 0}, \
    /* PHONK SUB 2/2, variations 6,7,8,9,10: always x.......x.......  from energy 25 ................  weights ......1..5a.1a.. */ \
    {22, 19, 42, 0, 0x0101, 0, TW(0,0,0,0,0,0,1,0,0,5,10,0,1,10,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_WITH | TH_K_LV, 0x0000, 0x0000, TL(0x0118, 0x0000), 0}, \
    /* PHONK LEAD 1/3, variations 4,5,6,7,8,9,10,11: always x.....x.x.......  from energy 25 ................  weights ..1f61.1..1a1.a. */ \
    {22, 24, 67, 0, 0x0141, 0, TW(0,0,1,15,6,1,0,1,0,0,1,10,1,0,10,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* PHONK LEAD 2/3, variations 1,2,3: always x.xx.x.xx.x.x.x.  from energy 25 ..+..+.+..+.....  weights ....1.9....9.... */ \
    {22, 24, 25, 0, 0x5109, 0, TW(0,0,0,0,1,0,9,0,0,0,0,9,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x04A4, 0x0000, TL(0x0080, 0x2000), 0}, \
    /* PHONK LEAD 3/3, variations 0: always x.x.x.x.x.x.x.x.  from energy 25 ..+.+.....+.+.+.  weights ...1.1.1...1.... */ \
    {22, 24, 8, 0, 0x0141, 0, TW(0,0,0,1,0,1,0,1,0,0,0,1,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x5414, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* PHONK PAD, variations 0,1,2,3,4,5: always x...............  from energy 25 ................  weights ......4.9....... */ \
    {22, 22, 0, 0, 0x0001, 0, TW(0,0,0,0,0,0,4,0,9,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* PHONK VOX 1/2, variations 0,1,2,3: always ....x.......x...  from energy 25 ................  weights 6.61....161..... */ \
    {22, 25, 67, 0, 0x1010, 0, TW(6,0,6,1,0,0,0,0,1,6,1,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0008, 0x0000), 0}, \
    /* PHONK VOX 2/2, variations 4,5: always ..........x.....  from energy 25 ................  weights d.1d1...d1..1... */ \
    {22, 25, 33, 0, 0x0400, 0, TW(13,0,1,13,1,0,0,0,13,1,0,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0008, 0x0000), 0}, \
    /* BAILE FUNK KICK 1/3, variations 2,3,4,5,6,7,8,9,10: always X..X..X.X..X..X.  from energy 25 ...+.......+..+.  weights ....1.....3.3..4 */ \
    {23, 0, 75, 0, 0x0141, 0, TW(0,0,0,0,1,0,0,0,0,0,3,0,3,0,0,4), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_PICK, TH_K_LV | TH_K_TWO, 0x4808, 0x0000, TL(0x9141, 0x1141), 0}, \
    /* BAILE FUNK KICK 1/3, variations 2,3,4,5,6,7,8,9,10 (even bars): always X..X..X...X.....  from energy 25 ...+......+.....  weights .6..13.1f..39f.. */ \
    {255, 0, 75, 0, 0x0041, 0, TW(0,6,0,0,1,3,0,1,15,0,0,3,9,15,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_PICK, TH_K_LV, 0x0408, 0x0000, TL(0x0591, 0x5149), 0}, \
    /* BAILE FUNK KICK 2/3, variations 0,1: always X..X..X.X..X..X.  from energy 25 ...+.......+..+.  weights ...............d */ \
    {23, 0, 17, 0, 0x0141, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,13), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_PICK, TH_K_LV, 0x4808, 0x0000, TL(0x9041, 0x1041), 0}, \
    /* BAILE FUNK KICK 3/3, variations 11: always X..X..X...X..X..  from energy 25 ..........+..+..  weights ................ */ \
    {23, 0, 8, 0, 0x0049, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_PICK, TH_K_LV, 0x2400, 0x0000, TL(0x0410, 0x1041), 0}, \
    /* BAILE FUNK SNARE 1/2, variations 0,1,2,3,4,5,6,7,8,9,10: always ....X.......X...  from energy 25 ................  weights .2.2.2.2.....229 */ \
    {23, 1, 92, 0, 0x1010, 0, TW(0,2,0,2,0,2,0,2,0,0,0,0,0,2,2,9), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0000, 0x8000, TL(0x2D00, 0x0DCC), 96}, \
    /* BAILE FUNK SNARE 1/2, variations 0,1,2,3,4,5,6,7,8,9,10 (even bars): always ....X.......X..x  from energy 25 ................  weights .222..52.2...2e. */ \
    {255, 1, 92, 0, 0x9010, 0, TW(0,2,2,2,0,0,5,2,0,2,0,0,0,2,14,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0100, 0xA1CC), 0}, \
    /* BAILE FUNK SNARE 2/2, variations 11: always ..x.X.....x.X...  from energy 25 ..+.......+.....  weights ................ */ \
    {23, 1, 8, 0, 0x1010, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0404, 0x0000, TL(0x0100, 0x0100), 0}, \
    /* BAILE FUNK HAT 1/4, variations 1,2,3,4,5: always ..x...x...x...x.  from energy 25 ......+.......+.  weights 15.111.11..115.5 */ \
    {23, 2, 42, 0, 0x0404, 0, TW(1,5,0,1,1,1,0,1,1,0,0,1,1,5,0,5), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4040, 0x4000, TL(0x8E82, 0x8A8E), 89}, \
    /* BAILE FUNK HAT 2/4, variations 6,7,8,9,10: always x.xx.xx.x.xx.xx.  from energy 25 +..+.+..+..+.+..  weights .f..1..a....1..1 */ \
    {23, 2, 42, 0, 0x4444, 0, TW(0,15,0,0,1,0,0,10,0,0,0,0,1,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x2929, 0x0000, TL(0x8200, 0x0208), 0}, \
    /* BAILE FUNK HAT 2/4, variations 6,7,8,9,10 (even bars): always x.xx.xx.x.xxxxxx  from energy 25 +..+.+..+..+++.+  weights .5..1........... */ \
    {255, 2, 42, 0, 0x4444, 0, TW(0,5,0,0,1,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0xB929, 0x0000, TL(0x0000, 0x0200), 0}, \
    /* BAILE FUNK HAT 3/4, variations 0: always x.x.x.x.x.x.x.x.  from energy 25 +...+...+...+...  weights .1.1.1.1...1.1.1 */ \
    {23, 2, 8, 0, 0x4444, 0, TW(0,1,0,1,0,1,0,1,0,0,0,1,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1111, 0x0000, TL(0x8880, 0x8888), 0}, \
    /* BAILE FUNK HAT 4/4, variations 11: always xxxxxxxxxxxxxxxx  from energy 25 .+..+..+.+..+..+  weights ................ */ \
    {23, 2, 8, 0, 0x6D6D, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x9292, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* BAILE FUNK HAT 4/4, variations 11 (even bars): always xxxxxxxxxxxxxxxx  from energy 25 .+..+..+.+......  weights ................ */ \
    {255, 2, 8, 0, 0xFD6D, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0292, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* BAILE FUNK PERC 1/3, variations 0,1,2,3,4,5,6: always ..x..x.x..x..x.x  from energy 25 ..+..+.........+  weights ...1..4..1.14.4. */ \
    {23, 3, 58, 0, 0x2480, 0, TW(0,0,0,1,0,0,4,0,0,1,0,1,4,0,4,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x8024, 0x0000, TL(0x20C8, 0x2080), 0}, \
    /* BAILE FUNK PERC 1/3, variations 0,1,2,3,4,5,6 (even bars): always ..x..x.x..x..xxx  from energy 25 .....+........++  weights .4.4..7..1.1f... */ \
    {255, 3, 58, 0, 0x2484, 0, TW(0,4,0,4,0,0,7,0,0,1,0,1,15,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0xC020, 0x0000, TL(0x00C8, 0x2000), 0}, \
    /* BAILE FUNK PERC 2/3, variations 7,8,9,10: always ...x...x.x.g.x..  from energy 25 .........+.+....  weights ..1..61...1.1.16 */ \
    {23, 3, 33, 0, 0x2088, 0, TW(0,0,1,0,0,6,1,0,0,0,1,0,1,0,1,6), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0A00, 0x0000, TL(0xE2E0, 0x2C20), 0}, \
    /* BAILE FUNK PERC 3/3, variations 11: always x.....x.x.....x.  from energy 25 ......+.+.......  weights ..11.1.1.11111.1 */ \
    {23, 3, 8, 0, 0x4001, 0, TW(0,0,1,1,0,1,0,1,0,1,1,1,1,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0140, 0x0000, TL(0x8AE8, 0x88A0), 0}, \
    /* BAILE FUNK CONGA 1/4, variations 0: always x..x..x...x..x..  from energy 25 ...+.........+..  weights ..1....11..11.11 */ \
    {23, 13, 25, 0, 0x0441, 0, TW(0,0,1,0,0,0,0,1,1,0,0,1,1,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x2008, 0x0000, TL(0xA282, 0x8020), 0}, \
    /* BAILE FUNK CONGA 2/4, variations 1: always x..x..x.o.x.x..o  from energy 25 ...+........+..+  weights ..1....1...1.11. */ \
    {23, 13, 25, 0, 0x0541, 0, TW(0,0,1,0,0,0,0,1,0,0,0,1,0,1,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x9008, 0x0000, TL(0xA882, 0x8020), 0}, \
    /* BAILE FUNK CONGA 3/4, variations 2: always x.ox..x.x.ox..x.  from energy 25 ..++.......+..+.  weights .......1....11.1 */ \
    {23, 13, 25, 0, 0x0541, 0, TW(0,0,0,0,0,0,0,1,0,0,0,0,1,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x480C, 0x0000, TL(0x8A20, 0x8020), 0}, \
    /* BAILE FUNK CONGA 4/4, variations 3: always ...x..x....x.xx.  from energy 25 ...........+.+..  weights 1.1....11.1.1..1 */ \
    {23, 13, 25, 0, 0x4048, 0, TW(1,0,1,0,0,0,0,1,1,0,1,0,1,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x2800, 0x0000, TL(0x8222, 0x8022), 0}, \
    /* BAILE FUNK TOM 1/4, variations 0,1: always ..........x..x..  from energy 25 ................  weights d..d..d.11.11.11 */ \
    {23, 14, 40, 0, 0x2400, 0, TW(13,0,0,13,0,0,13,0,1,1,0,1,1,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0000, 0x0000, TL(0xA28A, 0x0000), 0}, \
    /* BAILE FUNK TOM 2/4, variations 2: always x.....x.....x...  from energy 25 ................  weights ...1......1..11. */ \
    {23, 14, 20, 0, 0x1041, 0, TW(0,0,0,1,0,0,0,0,0,0,1,0,0,1,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0000, 0x0000, TL(0x2820, 0x0080), 0}, \
    /* BAILE FUNK TOM 3/4, variations 3: always ......x..x....x.  from energy 25 ................  weights 1..1......1.11.. */ \
    {23, 14, 20, 0, 0x4240, 0, TW(1,0,0,1,0,0,0,0,0,0,1,0,1,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0000, 0x0000, TL(0x0A20, 0x0082), 0}, \
    /* BAILE FUNK TOM 4/4, variations 4: always x..x..x.x..x..x.  from energy 25 ...+....+..+....  weights ..........1.11.. */ \
    {23, 14, 20, 0, 0x4041, 0, TW(0,0,0,0,0,0,0,0,0,0,1,0,1,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0908, 0x0000, TL(0x0A20, 0x0000), 0}, \
    /* BAILE FUNK SUB 1/3, variations 0,1,2,3,4,5,6: always x.....x.x.....x.  from energy 25 ......+.+.....+.  weights .447......1b.4.. */ \
    {23, 19, 58, 0, 0x0001, 0, TW(0,4,4,7,0,0,0,0,0,0,1,11,0,4,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_WITH | TH_K_LV, 0x4140, 0x0000, TL(0x0800, 0x0028), 0}, \
    /* BAILE FUNK SUB 2/3, variations 9,10,11: always x..x..x...x..x..  from energy 25 ...+.........+..  weights ........1..1..1. */ \
    {23, 19, 25, 0, 0x0441, 0, TW(0,0,0,0,0,0,0,0,1,0,0,1,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_WITH | TH_K_LV, 0x2008, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* BAILE FUNK SUB 3/3, variations 7,8: always x...............  from energy 25 ................  weights ...1..1.d.11.11. */ \
    {23, 19, 17, 0, 0x0001, 0, TW(0,0,0,1,0,0,1,0,13,0,1,1,0,1,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_WITH | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* BAILE FUNK VOX 1/4, variations 7,8,9,10,11: always ..x.x.......x...  from energy 25 ................  weights 1..1..1.1.11..1. */ \
    {23, 25, 42, 0, 0x1014, 0, TW(1,0,0,1,0,0,1,0,1,0,1,1,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* BAILE FUNK VOX 2/4, variations 4,5,6: always ...x......x.....  from energy 25 ................  weights 1.1.19..1...1... */ \
    {23, 25, 25, 0, 0x0408, 0, TW(1,0,1,0,1,9,0,0,1,0,0,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0800), 0}, \
    /* BAILE FUNK VOX 3/4, variations 0,1: always x..x..x.X..x..x.  from energy 25 ......+....+..+.  weights ..1.1.....1.1... */ \
    {23, 25, 17, 0, 0x0109, 0, TW(0,0,1,0,1,0,0,0,0,0,1,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4840, 0x0000, TL(0x0001, 0x0000), 0}, \
    /* BAILE FUNK VOX 4/4, variations 2,3: always X.......x.x.....  from energy 25 ................  weights ..111.......1... */ \
    {23, 25, 17, 0, 0x0501, 0, TW(0,0,1,1,1,0,0,0,0,0,0,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0001), 0}, \
    /* BAILE FUNK STAB 1/4, variations 0,1: always x.......x.......  from energy 25 ................  weights ..1d.11...1d1... */ \
    {23, 21, 33, 0, 0x0101, 0, TW(0,0,1,13,0,1,1,0,0,0,1,13,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0008), 0}, \
    /* BAILE FUNK STAB 2/4, variations 2,3: always ...X.......x....  from energy 25 ................  weights 1d...11.1....... */ \
    {23, 21, 33, 0, 0x0808, 0, TW(1,13,0,0,0,1,1,0,1,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0048), 0}, \
    /* BAILE FUNK STAB 3/4, variations 4: always x.....x.....x...  from energy 25 ................  weights ...1....1....... */ \
    {23, 21, 17, 0, 0x1041, 0, TW(0,0,0,1,0,0,0,0,1,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* BAILE FUNK STAB 4/4, variations 5: always ..x..x....x.....  from energy 25 ................  weights 1.......1....... */ \
    {23, 21, 17, 0, 0x0424, 0, TW(1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_APART | TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* MERENGUE KICK 1/2, variations 0,1,2,3,4,5,6,7,8,9,10: always X...X...X...X...  from energy 25 ....+.......+...  weights ......2...5...5. */ \
    {24, 0, 92, 0, 0x0101, 0, TW(0,0,0,0,0,0,2,0,0,0,5,0,0,0,5,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x1010, 0x0000, TL(0x0121, 0x0101), 0}, \
    /* MERENGUE KICK 1/2, variations 0,1,2,3,4,5,6,7,8,9,10 (even bars): always X...X...X...X...  from energy 25 ....+.......+...  weights ...5.....2e2.2f2 */ \
    {255, 0, 92, 0, 0x0101, 0, TW(0,0,0,5,0,0,0,0,0,2,14,2,0,2,15,2), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x1010, 0x4000, TL(0x8901, 0x0101), 91}, \
    /* MERENGUE KICK 2/2, variations 11: always X.......X.......  from energy 25 ................  weights ................ */ \
    {24, 0, 8, 0, 0x0101, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0001, 0x0001), 0}, \
    /* MERENGUE SNARE, variations 0,1,2,3,4,5,6,7,8,9,10,11: always ......x.......x.  from energy 25 ................  weights ....4....42226.2 */ \
    {24, 1, 0, 0, 0x4040, 0, TW(0,0,0,0,4,0,0,0,0,4,2,2,2,6,0,2), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x0000, 0x0000, TL(0x0CCC, 0x0000), 0}, \
    /* MERENGUE SNARE, variations 0,1,2,3,4,5,6,7,8,9,10,11 (even bars): always ......x.......x.  from energy 25 ................  weights .2.42.....2.f4.f */ \
    {255, 1, 0, 0, 0x4040, 0, TW(0,2,0,4,2,0,0,0,0,0,2,0,15,4,0,15), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x0000, 0x8000, TL(0x0000, 0x008C), 127}, \
    /* MERENGUE HAT 1/2, variations 0,1,2,3,4,5,6,7,8: always X.xxX.xxX.xxX.xx  from energy 25 ...+...+...+...+  weights .3...3...6...c.. */ \
    {24, 2, 75, 0, 0x5555, 0, TW(0,3,0,0,0,3,0,0,0,6,0,0,0,12,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x8888, 0x0000, TL(0x0101, 0x090D), 0}, \
    /* MERENGUE HAT 2/2, variations 9,10,11: always x.x.x.x.x.x.x.x.  from energy 25 +...+...+...+...  weights ...1.9.1.9.1.1.1 */ \
    {24, 2, 25, 0, 0x4444, 0, TW(0,0,0,1,0,9,0,1,0,9,0,1,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1111, 0x0000, TL(0x8888, 0x8880), 0}, \
    /* MERENGUE PERC 1/3, variations 0,1,2,3,4,5: always x..x.xx.x..x.xx.  from energy 25 ...+.+.....+.+..  weights .11.1..4.41.1..4 */ \
    {24, 3, 50, 0, 0x4141, 0, TW(0,1,1,0,1,0,0,4,0,4,1,0,1,0,0,4), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV | TH_K_TWO, 0x2828, 0x0000, TL(0xC22C, 0xC22C), 0}, \
    /* MERENGUE PERC 1/3, variations 0,1,2,3,4,5 (even bars): always x..x.xx.x....xx.  from energy 25 ...+.+.......+..  weights .11.1..4.4ddf..f */ \
    {255, 3, 50, 0, 0x4141, 0, TW(0,1,1,0,1,0,0,4,0,4,13,13,15,0,0,15), 40, 255, 0, TH_O, TH_NOCLS, 0, 35, TH_F_NONE, TH_K_LV, 0x2028, 0xA000, TL(0x0000, 0xC22C), 115}, \
    /* MERENGUE PERC 2/3, variations 6,7,8: always x.xx..x.x.xx..x.  from energy 25 ..++......++....  weights .9..19.1....11.1 */ \
    {24, 3, 25, 0, 0x4141, 0, TW(0,9,0,0,1,9,0,1,0,0,0,0,1,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0C0C, 0x4000, TL(0x8A00, 0x8E0C), 106}, \
    /* MERENGUE PERC 3/3, variations 9,10,11: always ....x..x....x.xx  from energy 25 .......+.......+  weights 1991.11.1.11.1.. */ \
    {24, 3, 25, 0, 0x5010, 0, TW(1,9,9,1,0,1,1,0,1,0,1,1,0,1,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x8080, 0x8000, TL(0x08A2, 0x28AE), 85}, \
    /* MERENGUE CONGA 1/4, variations 9,10,11: always ..o.x..x..o.x.x.  from energy 25 ..+.+..+........  weights 1..1.11.1..9.9.. */ \
    {24, 13, 33, 0, 0x5400, 0, TW(1,0,0,1,0,1,1,0,1,0,0,9,0,9,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0094, 0x4000, TL(0x0CA2, 0x28A2), 85}, \
    /* MERENGUE CONGA 2/4, variations 1,2: always x..x.xx.x..x.xx.  from energy 25 +....+..+.......  weights .d1.1..1..1.1... */ \
    {24, 13, 22, 0, 0x6848, 0, TW(0,13,1,0,1,0,0,1,0,0,1,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x0121, 0x4000, TL(0x0220, 0x822C), 96}, \
    /* MERENGUE CONGA 3/4, variations 3,4: always ...x..x....x.xx.  from energy 25 ...........+.+..  weights 1.1.11.d1.1.1... */ \
    {24, 13, 22, 0, 0x4048, 0, TW(1,0,1,0,1,1,0,13,1,0,1,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x2800, 0x4000, TL(0x0222, 0xCA22), 96}, \
    /* MERENGUE CONGA 4/4, variations 5,6: always ..x..xx...x..xx.  from energy 25 ..+..+.......+..  weights 1..11..11d.11... */ \
    {24, 13, 22, 0, 0x4440, 0, TW(1,0,0,1,1,0,0,1,1,13,0,1,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_BUSY, TH_K_LV, 0x2024, 0x4000, TL(0x028E, 0x8282), 96}, \
    /* MERENGUE BASS 1/2, variations 0,1,2,3,4,5,6: always x.....x.x.....x.  from energy 25 ......+.......+.  weights ...717.....71..7 */ \
    {24, 4, 58, 0, 0x0101, 0, TW(0,0,0,7,1,7,0,0,0,0,0,7,1,0,0,7), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4040, 0x0000, TL(0x8000, 0x0800), 0}, \
    /* MERENGUE BASS 2/2, variations 7,8,9,10,11: always x...x...x...x...  from energy 25 ....+.......+...  weights ...1.115...1..11 */ \
    {24, 4, 42, 0, 0x0101, 0, TW(0,0,0,1,0,1,1,5,0,0,0,1,0,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x1010, 0x0000, TL(0x8000, 0x8800), 0}, \
    /* MERENGUE PIANO 1/4, variations 1,2,3,4,5: always x..x..x.x..x..x.  from energy 25 ........+..+..+.  weights ..5..1.1..5..5.1 */ \
    {24, 23, 42, 0, 0x0049, 0, TW(0,0,5,0,0,1,0,1,0,0,5,0,0,5,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4900, 0x0000, TL(0x0820, 0x0020), 0}, \
    /* MERENGUE PIANO 2/4, variations 6,7,8: always x..x..x...x..x..  from energy 25 ...+.........+..  weights ..1..1.91..1..11 */ \
    {24, 23, 25, 0, 0x0441, 0, TW(0,0,1,0,0,1,0,9,1,0,0,1,0,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2008, 0x0000, TL(0x0000, 0x8000), 0}, \
    /* MERENGUE PIANO 3/4, variations 9,10,11: always ..x..x.x..x..x.x  from energy 25 .....+.+.......+  weights 1..1..1.1..1..1. */ \
    {24, 23, 25, 0, 0x2404, 0, TW(1,0,0,1,0,0,1,0,1,0,0,1,0,0,1,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x80A0, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* MERENGUE PIANO 4/4, variations 0: always ..x...x...x...x.  from energy 25 ..+.......+.....  weights 1..1.1.11..1.1.1 */ \
    {24, 23, 8, 0, 0x4040, 0, TW(1,0,0,1,0,1,0,1,1,0,0,1,0,1,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0404, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* MERENGUE LEAD 1/4, variations 1,2,3,4,5: always x.x.x.xxx.x.x.xx  from energy 25 ..+.+..+..+.+.++  weights .5.5.1...1.5.5.. */ \
    {24, 24, 42, 0, 0x0141, 0, TW(0,5,0,5,0,1,0,0,0,1,0,5,0,5,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0xD494, 0x0000, TL(0x0880, 0x0088), 0}, \
    /* MERENGUE LEAD 2/4, variations 6,7,8: always x.xx.x.xx.x.x.x.  from energy 25 ...+...+..+...+.  weights ....1.1..9.9...1 */ \
    {24, 24, 25, 0, 0x1125, 0, TW(0,0,0,0,1,0,1,0,0,9,0,9,0,0,0,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x4488, 0x0000, TL(0x0088, 0x0000), 0}, \
    /* MERENGUE LEAD 3/4, variations 9,10,11: always x.....x.x.......  from energy 25 ................  weights ..1f91.9..111.11 */ \
    {24, 24, 25, 0, 0x0141, 0, TW(0,0,1,15,9,1,0,9,0,0,1,1,1,0,1,1), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0080, 0x8000), 0}, \
    /* MERENGUE LEAD 4/4, variations 0: always xxxxxxxxxxxxxxxx  from energy 25 .+.+.+...+.+.+..  weights ................ */ \
    {24, 24, 8, 0, 0xD5D5, 0, TW(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x2A2A, 0x0000, TL(0x0000, 0x0000), 0}, \
    /* MERENGUE VOX 1/3, variations 0,1,2: always ....x.......x...  from energy 25 ................  weights 9.91....911..... */ \
    {24, 25, 50, 0, 0x1010, 0, TW(9,0,9,1,0,0,0,0,9,1,1,0,0,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0008, 0x0040), 0}, \
    /* MERENGUE VOX 2/3, variations 4,5: always ...X......x.....  from energy 25 ................  weights 1.1.1...1d..1... */ \
    {24, 25, 33, 0, 0x0408, 0, TW(1,0,1,0,1,0,0,0,1,13,0,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0008, 0x0040), 0}, \
    /* MERENGUE VOX 3/3, variations 3: always x.......x.x.....  from energy 25 ................  weights ...11.......1... */ \
    {24, 25, 17, 0, 0x0501, 0, TW(0,0,0,1,1,0,0,0,0,0,0,0,1,0,0,0), 40, 255, 0, TH_O, TH_NOCLS, 0, 25, TH_F_NONE, TH_K_LV, 0x0000, 0x0000, TL(0x0000, 0x0040), 0}, \


#define TH_DATA_LINES \
    {1, 18, {98, 0, 0, 0, 0, 1, 1, 0}, 217, 153, 20, 3, 115, 64, 42, 1, 0, 0}, /* HARDTECHNO RUMBLE */ \
    {2, 4, {76, 0, 0, 20, 4, 0, 0, 0}, 247, 125, 10, 3, 146, 64, 33, 2, 0, 0}, /* DUB TECHNO BASS */ \
    {4, 4, {1, 0, 0, 44, 6, 50, 0, 0}, 250, 236, 51, 3, 188, 64, 30, 2, 0, 0}, /* UK GARAGE BASS */ \
    {5, 4, {4, 9, 3, 37, 0, 47, 0, 0}, 225, 197, 13, 3, 168, 64, 51, 0, 0, 0}, /* UK FUNKY BASS */ \
    {6, 4, {1, 0, 0, 20, 0, 20, 59, 0}, 213, 236, 138, 3, 66, 64, 55, 2, 0, 0}, /* GRIME BASS */ \
    {6, 19, {45, 9, 0, 23, 0, 0, 23, 0}, 214, 217, 34, 3, 51, 64, 255, 0, 0, 0}, /* GRIME SUB */ \
    {8, 19, {10, 0, 0, 40, 20, 30, 0, 0}, 195, 204, 51, 3, 76, 64, 255, 0, 0, 0}, /* JUNGLE SUB */ \
    {8, 4, {25, 0, 0, 48, 0, 27, 0, 0}, 231, 165, 96, 3, 90, 64, 45, 1, 0, 0}, /* JUNGLE BASS */ \
    {9, 4, {21, 11, 10, 12, 0, 47, 0, 0}, 177, 222, 179, 3, 27, 64, 24, 0, 0, 0}, /* BASSLINE BASS */ \
    {9, 19, {38, 4, 3, 56, 0, 0, 0, 0}, 214, 242, 51, 3, 76, 64, 255, 0, 0, 0}, /* BASSLINE SUB */ \
    {10, 4, {30, 7, 0, 12, 8, 43, 0, 0}, 250, 117, 25, 3, 209, 64, 45, 0, 0, 0}, /* REGGAETON BASS */ \
    {11, 4, {20, 15, 0, 31, 2, 31, 0, 0}, 250, 125, 86, 3, 98, 64, 26, 0, 0, 0}, /* BATIDA BASS */ \
    {12, 4, {37, 4, 0, 23, 0, 0, 35, 0}, 250, 157, 15, 3, 131, 64, 64, 2, 0, 0}, /* GQOM BASS */ \
    {13, 4, {5, 2, 0, 19, 19, 29, 25, 0}, 231, 34, 13, 3, 35, 64, 29, 0, 0, 0}, /* EXPERIMENT BASS */ \
    {14, 4, {20, 10, 34, 9, 4, 22, 0, 0}, 231, 197, 68, 3, 71, 64, 26, 2, 0, 0}, /* ELECTRO BASS */ \
    {16, 4, {1, 0, 0, 50, 0, 50, 0, 0}, 246, 178, 26, 3, 166, 64, 27, 0, 0, 0}, /* AFRO HOUSE BASS */ \
    {17, 20, {19, 23, 0, 24, 0, 33, 0, 0}, 222, 153, 89, 3, 58, 42, 42, 1, 0, 0}, /* AMAPIANO LOG DRUM */ \
    {17, 4, {14, 15, 0, 35, 0, 35, 0, 0}, 240, 124, 119, 3, 38, 64, 58, 5, 0, 0}, /* AMAPIANO BASS */ \
    {18, 19, {18, 22, 0, 20, 0, 40, 0, 0}, 250, 76, 59, 3, 95, 64, 77, 2, 0, 0}, /* FOOTWORK SUB */ \
    {19, 4, {82, 6, 0, 0, 3, 10, 0, 0}, 217, 178, 51, 3, 76, 64, 29, 1, 0, 0}, /* TRANCE BASS */ \
    {20, 19, {9, 1, 0, 28, 0, 7, 35, 21}, 195, 204, 51, 3, 76, 64, 106, 0, 0, 0}, /* UK DRILL SUB */ \
    {21, 4, {7, 0, 0, 0, 0, 31, 62, 0}, 214, 247, 13, 3, 147, 64, 36, 2, 0, 0}, /* HARDCORE BASS */ \
    {22, 19, {47, 10, 1, 12, 12, 0, 18, 0}, 231, 172, 34, 3, 68, 64, 96, 0, 0, 0}, /* PHONK SUB */ \
    {23, 19, {45, 11, 0, 16, 20, 8, 0, 0}, 231, 112, 11, 3, 176, 64, 41, 0, 0, 0}, /* BAILE FUNK SUB */ \
    {24, 4, {41, 49, 0, 0, 10, 0, 0, 0}, 231, 249, 102, 3, 131, 64, 31, 2, 0, 0}, /* MERENGUE BASS */ \


#define TH_DATA_LEADS \
    {1, 24, 166, {17, 17, 50, 17}, 3, 5, 7, 50, 80, 221, 209, 128, 69, 1, 0, {6, 3, 1}, 12}, /* HARDTECHNO LEAD */ \
    {4, 25, 230, {50, 17, 17, 17}, 2, 3, 41, 50, 71, 176, 230, 60, 0, 0, 0, {4, 6, 3}, 12}, /* UK GARAGE VOX */ \
    {5, 24, 230, {17, 33, 50, 5}, 3, 5, 3, 50, 52, 207, 192, 128, 70, 1, 0, {6, 6, 5}, 12}, /* UK FUNKY LEAD */ \
    {6, 24, 235, {8, 33, 58, 5}, 3, 5, 14, 50, 65, 208, 193, 146, 97, 1, 0, {6, 3, 3}, 12}, /* GRIME LEAD */ \
    {8, 25, 230, {50, 17, 17, 17}, 2, 2, 38, 50, 19, 140, 230, 60, 0, 0, 0, {4, 6, 5}, 12}, /* JUNGLE VOX */ \
    {9, 25, 230, {33, 5, 5, 67}, 2, 3, 51, 50, 47, 159, 227, 60, 0, 0, 0, {3, 6, 3}, 12}, /* BASSLINE VOX */ \
    {10, 24, 230, {17, 67, 17, 5}, 3, 5, 3, 50, 26, 207, 204, 128, 77, 1, 0, {6, 4, 5}, 12}, /* REGGAETON LEAD */ \
    {11, 24, 166, {17, 33, 50, 5}, 3, 5, 3, 50, 16, 207, 171, 96, 70, 1, 0, {6, 5, 2}, 12}, /* BATIDA LEAD */ \
    {12, 25, 230, {40, 5, 20, 40}, 2, 3, 9, 50, 74, 147, 204, 64, 0, 0, 0, {5, 6, 2}, 12}, /* GQOM VOX */ \
    {16, 25, 230, {40, 5, 5, 60}, 2, 3, 36, 50, 56, 153, 208, 64, 0, 0, 0, {4, 6, 1}, 12}, /* AFRO HOUSE VOX */ \
    {17, 25, 230, {67, 5, 5, 33}, 2, 3, 41, 50, 20, 117, 173, 60, 0, 0, 0, {4, 6, 1}, 12}, /* AMAPIANO VOX */ \
    {18, 25, 235, {33, 5, 33, 33}, 2, 5, 35, 50, 47, 202, 245, 60, 0, 0, 0, {5, 6, 3}, 12}, /* FOOTWORK VOX */ \
    {19, 24, 235, {25, 17, 58, 5}, 3, 5, 15, 50, 14, 206, 166, 109, 98, 0, 0, {6, 6, 5}, 12}, /* TRANCE LEAD */ \
    {20, 24, 134, {17, 17, 67, 5}, 3, 5, 3, 50, 17, 221, 153, 96, 58, 2, 0, {6, 4, 6}, 10}, /* UK DRILL LEAD */ \
    {20, 25, 230, {80, 5, 5, 20}, 2, 2, 30, 50, 25, 178, 187, 64, 0, 0, 0, {3, 6, 3}, 12}, /* UK DRILL VOX */ \
    {21, 24, 131, {8, 42, 50, 5}, 3, 5, 13, 50, 80, 182, 175, 60, 88, 1, 0, {6, 3, 2}, 13}, /* HARDCORE LEAD */ \
    {22, 24, 168, {25, 17, 58, 5}, 3, 5, 9, 50, 40, 221, 171, 128, 78, 1, 0, {6, 3, 3}, 12}, /* PHONK LEAD */ \
    {22, 25, 230, {50, 5, 5, 50}, 2, 3, 32, 50, 74, 204, 211, 96, 0, 0, 0, {6, 4, 1}, 12}, /* PHONK VOX */ \
    {23, 25, 235, {17, 8, 17, 58}, 2, 3, 37, 50, 61, 173, 242, 73, 0, 0, 0, {6, 5, 2}, 12}, /* BAILE FUNK VOX */ \
    {24, 24, 131, {8, 17, 75, 5}, 4, 5, 21, 50, 13, 216, 151, 109, 59, 1, 0, {6, 6, 3}, 12}, /* MERENGUE LEAD */ \
    {24, 25, 166, {50, 17, 5, 33}, 3, 3, 27, 50, 43, 204, 193, 64, 0, 0, 0, {6, 6, 2}, 12}, /* MERENGUE VOX */ \


#define TH_DATA_CHORDS \
    {1, 21, {65, 18, 0, 18}, 247, 0, 0, 0}, /* HARDTECHNO STAB */ \
    {2, 5, {15, 85, 0, 0}, 216, 51, 1, 0}, /* DUB TECHNO CHORD */ \
    {2, 22, {10, 90, 0, 0}, 195, 255, 0, 0}, /* DUB TECHNO PAD */ \
    {4, 5, {5, 95, 0, 0}, 229, 62, 2, 0}, /* UK GARAGE CHORD */ \
    {5, 5, {12, 88, 0, 0}, 188, 45, 1, 0}, /* UK FUNKY CHORD */ \
    {6, 21, {34, 20, 0, 46}, 235, 0, 0, 0}, /* GRIME STAB */ \
    {8, 22, {27, 73, 0, 0}, 119, 174, 0, 0}, /* JUNGLE PAD */ \
    {9, 21, {74, 26, 0, 0}, 208, 0, 0, 0}, /* BASSLINE STAB */ \
    {10, 5, {90, 10, 0, 0}, 222, 26, 1, 0}, /* REGGAETON CHORD */ \
    {11, 5, {91, 9, 0, 0}, 220, 59, 1, 0}, /* BATIDA CHORD */ \
    {12, 22, {40, 60, 0, 0}, 195, 178, 0, 0}, /* GQOM PAD */ \
    {13, 22, {50, 37, 0, 13}, 148, 100, 7, 0}, /* EXPERIMENT PAD */ \
    {14, 21, {71, 29, 0, 0}, 208, 0, 0, 0}, /* ELECTRO STAB */ \
    {16, 5, {23, 77, 0, 0}, 180, 68, 2, 0}, /* AFRO HOUSE CHORD */ \
    {17, 23, {0, 100, 0, 0}, 253, 65, 1, 0}, /* AMAPIANO PIANO */ \
    {17, 22, {18, 82, 0, 0}, 168, 255, 0, 0}, /* AMAPIANO PAD */ \
    {18, 5, {44, 56, 0, 0}, 216, 90, 2, 0}, /* FOOTWORK CHORD */ \
    {19, 22, {70, 30, 0, 0}, 208, 133, 8, 0}, /* TRANCE PAD */ \
    {20, 22, {50, 50, 0, 0}, 157, 149, 7, 0}, /* UK DRILL PAD */ \
    {21, 21, {54, 21, 0, 26}, 208, 0, 0, 0}, /* HARDCORE STAB */ \
    {21, 22, {20, 80, 0, 0}, 195, 255, 0, 0}, /* HARDCORE PAD */ \
    {22, 22, {30, 70, 0, 0}, 153, 178, 0, 0}, /* PHONK PAD */ \
    {23, 21, {76, 24, 0, 0}, 208, 0, 0, 0}, /* BAILE FUNK STAB */ \
    {24, 23, {27, 73, 0, 0}, 216, 56, 1, 0}, /* MERENGUE PIANO */ \


#define TH_DATA_PROGS \
    [1] = {{18, 60, 4, 18}, {18, 60, 18, 4}, {29, 4, 4, 4, 17, 42}, 95, {0, 10, 10, 10, 10, 10, 42}, {83, 2, 2, 2, 9, 2}, 75, {0, 0, 0, 0, 0, 0}, {100, 0, 0}}, /* HARDTECHNO */ \
    [2] = {{18, 60, 4, 18}, {18, 60, 18, 4}, {17, 4, 17, 17, 17, 29}, 82, {0, 10, 10, 10, 10, 10, 42}, {9, 49, 22, 9, 2, 9}, 25, {0, 0, 0, 0, 0, 0}, {100, 0, 0}}, /* DUB TECHNO */ \
    [4] = {{4, 32, 4, 60}, {74, 18, 4, 4}, {17, 9, 38, 17, 9, 9}, 70, {0, 7, 7, 7, 32, 7, 32}, {6, 47, 38, 6, 1, 1}, 12, {0, 0, 0, 0, 0, 0}, {45, 40, 15}}, /* UK GARAGE */ \
    [5] = {{18, 60, 4, 18}, {32, 46, 18, 4}, {26, 3, 26, 15, 15, 15}, 70, {0, 14, 14, 14, 14, 14, 14}, {2, 76, 16, 2, 2, 2}, 62, {0, 0, 0, 0, 0, 0}, {45, 15, 40}}, /* UK FUNKY */ \
    [6] = {{18, 46, 4, 32}, {32, 46, 18, 4}, {34, 13, 13, 3, 23, 13}, 95, {0, 10, 10, 10, 42, 10, 10}, {85, 2, 2, 8, 2, 2}, 75, {0, 0, 0, 0, 0, 0}, {100, 0, 0}}, /* GRIME */ \
    [8] = {{18, 46, 4, 32}, {32, 46, 18, 4}, {23, 3, 34, 3, 13, 23}, 70, {0, 10, 10, 10, 10, 10, 42}, {8, 55, 32, 2, 2, 2}, 38, {0, 0, 0, 0, 0, 0}, {100, 0, 0}}, /* JUNGLE */ \
    [9] = {{4, 32, 4, 60}, {60, 32, 4, 4}, {29, 2, 16, 22, 16, 16}, 82, {0, 6, 6, 25, 6, 6, 45}, {84, 11, 1, 1, 1, 1}, 88, {0, 0, 0, 0, 0, 0}, {45, 40, 15}}, /* BASSLINE */ \
    [10] = {{4, 4, 4, 88}, {88, 4, 4, 4}, {34, 2, 28, 18, 18, 2}, 82, {0, 6, 25, 25, 6, 6, 25}, {94, 1, 1, 1, 1, 1}, 88, {0, 0, 0, 0, 0, 0}, {100, 0, 0}}, /* REGGAETON */ \
    [11] = {{4, 4, 4, 88}, {88, 4, 4, 4}, {23, 2, 18, 18, 23, 18}, 70, {0, 4, 4, 32, 32, 4, 18}, {94, 1, 1, 1, 1, 1}, 88, {0, 0, 0, 0, 0, 0}, {100, 0, 0}}, /* BATIDA */ \
    [12] = {{18, 74, 4, 4}, {4, 74, 18, 4}, {22, 5, 22, 5, 22, 22}, 95, {0, 14, 14, 14, 14, 14, 14}, {80, 2, 2, 10, 2, 2}, 75, {0, 0, 0, 0, 0, 0}, {100, 0, 0}}, /* GQOM */ \
    [13] = {{4, 46, 4, 46}, {46, 46, 4, 4}, {10, 41, 2, 18, 2, 26}, 82, {0, 25, 6, 6, 25, 6, 25}, {7, 27, 22, 17, 17, 12}, 25, {0, 0, 0, 0, 0, 0}, {100, 0, 0}}, /* EXPERIMENT */ \
    [14] = {{18, 60, 4, 18}, {18, 60, 18, 4}, {4, 17, 29, 4, 17, 29}, 95, {0, 10, 10, 10, 42, 10, 10}, {70, 16, 2, 9, 2, 2}, 75, {0, 0, 0, 0, 0, 0}, {100, 0, 0}}, /* ELECTRO */ \
    [16] = {{18, 60, 4, 18}, {18, 60, 18, 4}, {3, 15, 26, 15, 15, 26}, 82, {0, 10, 10, 10, 42, 10, 10}, {2, 49, 36, 9, 2, 2}, 38, {0, 0, 0, 0, 0, 0}, {45, 15, 40}}, /* AFRO HOUSE */ \
    [17] = {{18, 18, 4, 60}, {60, 18, 18, 4}, {17, 2, 31, 17, 31, 2}, 57, {0, 6, 6, 6, 45, 25, 6}, {6, 45, 45, 1, 1, 1}, 38, {0, 0, 0, 0, 0, 0}, {45, 40, 15}}, /* AMAPIANO */ \
    [18] = {{18, 60, 4, 18}, {18, 60, 18, 4}, {42, 4, 17, 4, 29, 4}, 82, {0, 14, 14, 14, 14, 14, 14}, {2, 63, 22, 9, 2, 2}, 38, {0, 0, 0, 0, 0, 0}, {100, 0, 0}}, /* FOOTWORK */ \
    [19] = {{4, 4, 4, 88}, {60, 32, 4, 4}, {24, 7, 7, 24, 19, 19}, 70, {0, 4, 4, 4, 32, 4, 46}, {90, 1, 1, 5, 1, 1}, 75, {0, 0, 0, 0, 0, 0}, {100, 0, 0}}, /* TRANCE */ \
    [20] = {{18, 32, 4, 46}, {46, 32, 18, 4}, {28, 3, 11, 19, 28, 11}, 82, {0, 10, 10, 10, 10, 10, 42}, {92, 2, 2, 2, 2, 2}, 88, {0, 0, 0, 0, 0, 0}, {100, 0, 0}}, /* UK DRILL */ \
    [21] = {{18, 46, 4, 32}, {32, 46, 18, 4}, {34, 3, 3, 3, 13, 44}, 95, {0, 7, 7, 7, 7, 7, 56}, {85, 2, 2, 2, 8, 2}, 75, {0, 0, 0, 0, 0, 0}, {100, 0, 0}}, /* HARDCORE */ \
    [22] = {{18, 60, 4, 18}, {18, 60, 18, 4}, {17, 4, 17, 17, 17, 29}, 95, {0, 10, 10, 10, 10, 42, 10}, {83, 9, 2, 2, 2, 2}, 75, {0, 0, 0, 0, 0, 0}, {100, 0, 0}}, /* PHONK */ \
    [23] = {{18, 32, 4, 46}, {46, 32, 18, 4}, {45, 3, 19, 3, 11, 19}, 82, {0, 10, 10, 10, 10, 10, 42}, {92, 2, 2, 2, 2, 2}, 88, {0, 0, 0, 0, 0, 0}, {100, 0, 0}}, /* BAILE FUNK */ \
    [24] = {{4, 18, 4, 74}, {88, 4, 4, 4}, {19, 2, 47, 19, 13, 2}, 82, {0, 7, 7, 7, 56, 7, 7}, {68, 26, 1, 1, 1, 1}, 12, {0, 0, 0, 0, 0, 0}, {100, 0, 0}}, /* MERENGUE */ \


#endif
