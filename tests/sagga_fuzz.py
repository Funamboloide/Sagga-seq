#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Random-input test of SAGGA SEQ in the host simulator: buttons, keys, encoders, the tempo knob, MIDI in and a
Launchpad bridge that attaches, taps pads, goes quiet and comes back, all at random for a minute of FM-1 time.
After every run the MIDI the firmware sent is checked:

  * no crash, and no memory error: run_sagga_tests.sh builds it with ASan + UBSan when the compiler has them
    (SAGGA_SIM_CFLAGS="-fsanitize=address,undefined -g"; 0.21: seed 85 found a line of the screen past its buffer)
  * every data byte is 7-bit; notes and CCs only on channels 1-14; grid traffic only on 9F / BE, roles 0..15
  * no hung notes after a final panic: every note-on has its note-off
  * 0.22: the FM-1's real output ring in every run (its size, the USB's pace, the room the senders that wait see): no
    message may be dropped; half of the runs start with a BAND in play
  * 0.21: half of the seeds play the hub's pages too (channels 12 and 13, the pads, any SysEx of the app; a quarter on
    USB PORTS 2), one in eight starts from a project image with bytes changed at random
  * odd seeds run with the screen's SPI time charged to the clock (the script verb "lcdcost"): no clock recovery and
    no pass of the main loop over 20 ms, whatever was pressed (a pass that erases the flash, ~45 ms, is counted
    apart: the store erases only while stopped, and never while playing)

    python3 tests/sagga_fuzz.py [SEEDS]
"""
import os
import random
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sagga_sim_tests as S   # noqa: E402

PANEL = [S.OCT_DOWN, S.OCT_UP, S.FX, S.SEL, S.ENV, S.LFO, S.EDIT, S.GLO, S.HOME, S.SAVE, S.ARP, S.SEQ, S.PLAY]
NO_HOLD = {S.PLAY, S.SAVE, S.GLO}            # tapped, not held


def make_script(seed, length_ms=60000):
    rnd = random.Random(seed)
    s = S.Script()
    if seed % 2:
        s.raw(2, "lcdcost")
    t = 100
    held, rec, keys = set(), 0, 0
    # 0.21: half of the seeds with the hub's pages too (REMOTE 13 + 14: channels 12 and 13 speak, the pads of channel 13,
    # every SysEx of the app), and half of those on USB PORTS 2 (the hub on port 2: what goes back to its pages)
    tablet, two = seed % 4 >= 2, seed % 8 >= 6
    if tablet:
        t = S.remote13_on(s, t)
        if two:
            t = S.usb2(s, t)
    port = " 2" if two else ""
    # 0.22: the FM-1's real output ring in every run (64 events and the USB's pace: tests/host.c "ring"): the grid's
    # lights, the lanes and the values for the hub wait for room as they do on the FM-1, and a message that does not
    # fit is DROPPED and said (check_log: none may be). And half of the runs (by sixteens of seeds) start with a BAND
    # in play: ten tracks of notes under the random hands, not an empty project
    s.raw(1, "ring %d" % RING if RING else "ring")
    if (seed // 8) % 2 == 0:
        s.press(t, S.SEQ); s.tap_key(t + 30, S.bk(6), hold=700); s.release(t + 800, S.SEQ); t += 900
        s.tap_btn(t, S.PLAY); t += 100
    # 0.21: one seed in eight starts from a project with bytes changed at random, sent in as the Pi sends one (no
    # checksum in the image itself: what the FM-1 takes it must play and show, on every page, whatever it says)
    if seed % 8 == 4:
        img = bytearray(S.sgq_image([]))
        k = rnd.random()
        if k < 0.4:
            for _ in range(rnd.choice([1, 2, 4, 8, 16])):
                img[rnd.randrange(4, len(img))] = rnd.choice([0, 1, 127, 128, 200, 254, 255, rnd.randrange(256)])
        elif k < 0.8:
            for _ in range(rnd.choice([40, 100, 300, 1000])):
                img[rnd.randrange(4, len(img))] = rnd.choice([255, 255, 128, rnd.randrange(256)])
        else:
            a, v = rnd.randrange(4, len(img) - 8), rnd.choice([0, 255, 128, None])
            for j in range(a, min(len(img), a + rnd.choice([8, 64, 300, 2000]))):
                img[j] = rnd.randrange(256) if v is None else v
        t = S.sx_import(s, t, bytes(img)) + 300
    while t < length_ms:
        t += rnd.choice([5, 10, 20, 40, 80, 150, 400])
        r = rnd.random()
        if r < 0.05 and S.SEQ not in held and keys == 0:          # SEQ + a key: tools, dice, EVOLVE (0.4)
            s.press(t, S.SEQ)
            s.tap_key(t + 10, 1 << rnd.randrange(27), hold=20)
            if rnd.random() < 0.3:
                s.tap_btn(t + 40, rnd.choice([S.OCT_UP, S.OCT_DOWN]), hold=10)
            s.release(t + 60, S.SEQ)
            t += 70
        elif r < 0.20:                                            # panel button
            b = rnd.choice(PANEL)
            if b in NO_HOLD:
                s.tap_btn(t, b)
            elif b in held:
                s.release(t, b); held.discard(b)
            else:
                s.press(t, b); held.add(b)
        elif r < 0.27:                                            # REC toggles only with no key down, so no live note is left on
            if keys == 0:
                s.tap_btn(t, S.REC); rec ^= 1
        elif r < 0.40:                                            # keys
            keys = 0
            for _ in range(rnd.choice([0, 0, 1, 1, 2, 3])):
                keys |= 1 << rnd.randrange(27)
            s.keys(t, keys)
        elif r < 0.62:                                            # encoders
            s.enc(t, rnd.randrange(7), rnd.choice([-7, -3, -1, 1, 1, 2, 5, 9]))
        elif r < 0.65:
            s.knob(t, rnd.choice([0, 100, 512, 700, 1023, rnd.randrange(1024)]))
        elif r < 0.70:                                            # MIDI in: realtime, notes, 0.5: remote, CCs, SPP, battery
            k = rnd.random()
            if tablet and k < 0.45:                               # 0.21: a page of the hub: any CC of channels 12, 13, 14
                s.raw(t, "midi 0x%X %d %d%s" % (rnd.choice([0xBB, 0xBB, 0xBC, 0xBC, 0xBD]), rnd.randrange(128),
                                                rnd.choice([0, 1, 5, 64, 127, rnd.randrange(128)]), port))
            elif tablet and k < 0.52:                             # ... a pad of channel 13, an LFO switch
                n = rnd.choice(list(range(36, 52)) + list(range(100, 116)))
                s.raw(t, "midi 0x9C %d %d%s" % (n, rnd.choice([0, 100]), port))
            elif k < 0.25:
                s.raw(t, "midi 0xBD %d %d" % (rnd.choice([1, 2, 4, 5, 6, 7, 8, 9, 10, 11] + list(range(20, 106))), rnd.choice([0, 0, 64, 127, rnd.randrange(128)])))
            elif k < 0.32:
                s.raw(t, "midi 0x%X %d %d" % (0xB0 | rnd.randrange(13), rnd.randrange(128), rnd.randrange(128)))
            elif k < 0.36:
                spp = rnd.randrange(16384)
                s.raw(t, "midi 0xF2 %d %d" % (spp & 127, spp >> 7))
            elif k < 0.40:
                s.raw(t, rnd.choice(["batt %d" % rnd.randrange(450, 650), "usbpower 0", "usbpower 1"]))
            elif k < 0.70:
                s.raw(t, "midi %s 0 0" % rnd.choice(["0xF8", "0xF8", "0xFA", "0xFB", "0xFC"]))
            else:
                n = rnd.randrange(128)
                s.raw(t, "midi 0x90 %d %d" % (n, rnd.randrange(0, 128)))
                s.raw(t + rnd.choice([30, 200, 1500]), "midi %s %d 0" % (rnd.choice(["0x80", "0x90"]), n))
        elif r < 0.73:
            s.raw(t, rnd.choice(["attach", "hb", "hb", "detach"]))
        elif r < 0.83:                                            # grid pad
            x, y = rnd.randrange(16), rnd.randrange(8)
            s.at(t, "pad", x, y, rnd.randrange(1, 128))
            s.at(t + rnd.choice([20, 60, 500]), "pad", x, y, 0)
        elif r < 0.93:                                            # grid button
            i = rnd.randrange(32)
            s.at(t, "ctl", i, 127)
            s.at(t + rnd.choice([20, 60, 500]), "ctl", i, 0)
        elif r < 0.955:
            s.raw(t, "txroom %d" % rnd.choice([0, 20, 28, 29, 40, 64]))
        elif r < 0.96:                                            # SysEx for the app: requests, chunks, ends, junk
            k = rnd.random()
            if tablet and k < 0.5:                                # 0.21: any message of the app (the PC test apart: it
                sub = rnd.choice([x for x in range(128) if not 0x70 <= x <= 0x74])   # reboots, and has its own tests)
                body = [0x7D, 0x53, 0x47, sub] + [rnd.randrange(128) for _ in range(rnd.choice([0, 1, 2, 4, 9, 30, 120]))]
            elif k < 0.2:
                body = [0x7D, 0x53, 0x47, 0x01] + ([rnd.randrange(128)] if rnd.random() < 0.5 else [])
            elif k < 0.7:
                n = rnd.choice([0, 1, 5, 40, 293, 300, 330])
                body = [0x7D, 0x53, 0x47, 0x02, rnd.choice([0, 0, 1, 2, 127]), rnd.choice([0, 1]), rnd.choice([1, 2, 3, 127]), rnd.choice([0, 1])]
                body += [rnd.randrange(128) for _ in range(n)]
                body.append(sum(body[8:]) & 0x7F if rnd.random() < 0.8 else rnd.randrange(128))
            elif k < 0.75:
                body = [0x7D, 0x53, 0x47, 0x03] + [rnd.randrange(128) for _ in range(rnd.choice([0, 3, 8, 12]))]
            elif k < 0.85:                                        # 0.5: the library's list and answers
                body = [0x7D, 0x53, 0x47, rnd.choice([0x21, 0x21, 0x24])] + [rnd.randrange(128) for _ in range(rnd.choice([0, 1, 2, 3, 9, 30]))]
            else:
                body = [rnd.choice([0x7D, 0x00, 0x7E])] + [rnd.randrange(128) for _ in range(rnd.randrange(12))]
            s.raw(t, "sx " + " ".join("%02X" % b for b in body))
        else:                                                     # a pad held for a long press
            x, y = rnd.randrange(16), rnd.randrange(4)
            s.at(t, "pad", x, y, 100)
            s.at(t + 600, "pad", x, y, 0)
    # the end: let go of everything, then panic
    t += 1000
    s.keys(t, 0)
    for b in sorted(held):
        s.release(t + 10, b)
    s.raw(t + 20, "txroom 64")
    for i in range(32):
        s.at(t + 30, "ctl", i, 0)
    for cc in [23, 24, 25, 26, 27, 37] + list(range(64, 80)):     # the remote's held buttons let go
        s.raw(t + 35, "midi 0xBD %d 0%s" % (cc, port))
    if tablet:                                                    # ... the pages' too: the ROLLs, the pads, the notes
        for cc in [65, 71] + list(range(76, 92)):
            s.raw(t + 36, "midi 0xBC %d 0%s" % (cc, port))
        for n in range(36, 52):
            s.raw(t + 37, "midi 0x8C %d 0%s" % (n, port))
    for x in range(16):
        for y in range(8):
            s.at(t + 40, "pad", x, y, 0)
    if rec:
        s.tap_btn(t + 100, S.REC)
    s.press(t + 200, S.FX); s.press(t + 220, S.HOME)              # HOME + FX: panic
    s.release(t + 300, S.HOME); s.release(t + 310, S.FX)
    return s, t + 1500, t + 230          # (the sequencer may still be playing after the panic: only what came before is checked for hung notes)


def check_log(log, seed, panic_t=1 << 30):
    bad = []
    on = {}
    drops = re.findall(r"(\d+) ms  MIDI DROP (\w\w \d+ \d+)", log.text)   # 0.22: the output ring was full: a message lost
    if drops:
        bad.append("seed %d: %d messages DROPPED, the output ring was full (the first at %s ms: %s)" % (seed, len(drops), drops[0][0], drops[0][1]))
    def ports_at(t):                                              # 0.8: USB PORTS 2 from the moment the log says so
        n = 1
        for t2, k in log.usb_ports:
            if t2 < t:                                             # (the panic before a reconnect: still the old ports)
                n = k
        return n
    for (t, st, d1, d2), port in zip(log.msgs, log.port):
        if d1 > 127 or d2 > 127:
            bad.append("%d: data byte over 127 in %02X %d %d" % (t, st, d1, d2))
        kind, ch = st & 0xF0, st & 15
        two = ports_at(t) > 1
        if two and port == 2 and ch == 12 and kind in (0x80, 0x90) and 100 <= d1 <= 115:
            continue                                               # 0.18: the LFO switches as the hub's pages show them: a state
        if two and port == 1:
            top = 15                                               # two ports: port 1 has 16 channels of tracks
        elif st == 0x9F:
            top = 13
            if d2 > 18:                                            # 0.12: 16 TAIL, 17 TIE; 0.24: 18 GHOST (a copy that plays)
                bad.append("%d: pad LED role %d" % (t, d2))
            if two:
                continue
        elif st == 0xBE:
            top = 13
            if d1 > 31 or d2 > 15:
                bad.append("%d: button LED %d role %d" % (t, d1, d2))
            if two:
                continue
        else:
            top = 13
            if kind in (0x80, 0x90, 0xB0) and ch > 13:
                bad.append("%d: %02X %d %d on a grid channel%s" % (t, st, d1, d2, " (port 2)" if port == 2 else ""))
        if kind == 0x90 and d2 and ch <= top and not (st == 0x9F and not two):   # every note-on is matched with the next
            on.setdefault((ch, d1), []).append(t)                   # note-off of its key, wherever it comes in the log
        elif (kind == 0x80 or (kind == 0x90 and not d2)) and ch <= top and not (st == 0x9F and not two):
            if on.get((ch, d1)):
                on[(ch, d1)].pop(0)
    if "ERASE WHILE PLAYING" in log.text:
        bad.append("the flash was erased while playing")
    if "clock recovery" in log.text:
        bad.append("the clock needed %d recoveries" % log.text.count("clock recovery"))
    m = re.search(r"longest pass of the main loop (\d+) ms", log.text)
    if m and int(m.group(1)) > 20:
        bad.append("a pass of the main loop took %s ms" % m.group(1))
    hung = sorted(k for k, v in on.items() if any(t <= panic_t for t in v))   # (after the panic the sequencer may still play)
    if hung:
        bad.append("hung notes (channel, note): %s" % hung[:8])
    return bad


RING = int(os.environ.get("SAGGA_FUZZ_RING", "0"))                 # the output ring's size: 0 = the FM-1's (platform.c USB_MIDI_OUT_RING; until 0.21: 64)

# seeds that found something, run whatever the count asked. 85 (0.21, with ASan): the screen's line of what is going on
# (DICE? EVOLVE LOOP MACRO MORPH ECHO ALL STEP LOOP ... together) written past the 64 bytes it had on the stack
# 182 (0.22, with the output ring as the FM-1 has it): 68 Control Changes in one pass (three keys at once, each a move
# that sends every track's CC) into a ring of 64: four were dropped. The ring is 256 now
FOUND = [85, 182]


def main():
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    S.build()
    fails = 0
    try:
        for seed in list(range(seeds)) + [x for x in FOUND if x >= seeds]:
            s, end, panic_t = make_script(seed)
            try:
                log = S.run(s, end)
            except subprocess.CalledProcessError as e:
                print("seed %d: the simulator died (%s)\n%s" % (seed, e.returncode, (e.stderr or "")[-1500:]))
                fails += 1
                continue
            bad = check_log(log, seed, panic_t)
            if bad:
                fails += 1
                print("seed %d: %s" % (seed, "; ".join(bad[:4])))
    finally:
        if os.path.exists(S.BIN):
            os.remove(S.BIN)
    print("sagga fuzz: %d runs, %d failures%s" % (seeds + len([x for x in FOUND if x >= seeds]), fails,
                                               " (ASan + UBSan)" if "sanitize" in os.environ.get("SAGGA_SIM_CFLAGS", "") else ""))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
