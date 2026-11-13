#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The hardware test's reference, made with the simulator (the same firmware on this computer, tests/host.c):

  hwtest.sgq            a small project: track 1 four on the floor (note 60), track 2 a four-note line,
                        track 3 one step with EXPO RAMP (8 hits a bar), track 4 a TAPE of one bar with two
                        notes played in (0.10), 128 BPM, master clock
  hwtest_expected.json  what the firmware sends when that project plays from the REMOTE (CC 20 on channel 14):
                        the notes of the first two bars per channel, the clock, the mute and tempo behaviour

    python3 tools/hwtest/make_assets.py          (from the repository root; writes next to this file)

sagga_hw_test.py plays the same project on the real FM-1 and compares."""
import json
import os
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import sagga_sim_tests as S                                                   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REMOTE = 0xBD                                                                 # CC on channel 14
BARS = 4


def remote(s, t, cc, v=127):
    s.raw(t, "midi 0x%X %d %d" % (REMOTE, cc, v))
    s.raw(t + 30, "midi 0x%X %d 0" % (REMOTE, cc))
    return t + 60


def build_project(s, t=100):
    """the gestures that make the project; returns the time after"""
    t = s.steps(t, (0, 4, 8, 12))                                            # track 1: steps 1 5 9 13, note 60
    s.tap_key(t, S.bk(1)); t += 200                                          # track 2
    t = S.program(s, t, [60, 62, 64, 67])                                    # steps 1-4: C D E G
    s.tap_key(t, S.bk(2)); t += 200                                          # track 3
    t = s.steps(t, (0,))
    t = S.seq_page_turn(s, t, 4, [(S.K4, 1)])                                # SEQ 5/6: SHAPE OFF -> RAMP (8 hits, +4, 1 BAR)
    s.tap_key(t, S.bk(3)); t += 200                                          # track 4: a TAPE of one bar with two notes played in
    t = S.kp(s, t, [(S.K4, 3)])                                              # 0.10 HOME 4/8 K1: FREE -> IN KEY -> DRUM -> TAPE (the page is left on 3)
    t = S.home_page(s, t, 6, [(S.K3, -3)], cur=2)                            # HOME 7/8 K3: TAPE BARS 1
    s.tap_btn(t, S.REC); t += 100                                            # REC (quantised: the starts land on the 1/16)
    tp = t
    s.tap_btn(tp, S.PLAY)
    beat = 4 * S.STEP_MS
    s.raw(tp + int(0.25 * beat) + 7, "midi 0x90 48 110"); s.raw(tp + int(0.25 * beat) + 150, "midi 0x80 48 0")
    s.raw(tp + int(2.5 * beat) + 5, "midi 0x90 50 90"); s.raw(tp + int(2.5 * beat) + 150, "midi 0x80 50 0")
    t = tp + int(1.2 * 16 * S.STEP_MS)
    s.tap_btn(t, S.PLAY); t += 200                                           # STOP
    s.tap_btn(t, S.REC); t += 100                                            # REC off
    s.tap_key(t, S.bk(0)); t += 200                                          # back on track 1
    return t


def image_from_sysex(frames):
    """the export's frames (lists of bytes, F0..F7) -> the image, checked"""
    chunks, end = {}, None
    for f in frames:
        if f[:5] != [0xF0, 0x7D, 0x53, 0x47, 0x02] and f[:5] != [0xF0, 0x7D, 0x53, 0x47, 0x03]:
            continue
        body = f[5:-1]
        if f[4] == 0x02:
            idx = body[0] | body[1] << 7
            cnt = body[2] | body[3] << 7
            data, sm = body[4:-1], body[-1]
            assert sum(data) & 0x7F == sm, "chunk %d: bad sum" % idx
            chunks[idx] = (cnt, bytes(unpack7(data)))
        else:
            ln = body[0] | body[1] << 7 | body[2] << 14
            crc = body[3] | body[4] << 7 | body[5] << 14 | body[6] << 21 | body[7] << 28
            end = (ln, crc & 0xFFFFFFFF)
    assert end, "no END frame"
    cnt = chunks[0][0]
    img = b"".join(chunks[i][1] for i in range(cnt))[:end[0]]
    assert len(img) == end[0] and zlib.crc32(img) == end[1], "image length / CRC"
    assert img[:4] in (b"SGQB", b"SGQA")
    return img


def unpack7(s):
    out, acc, nb = [], 0, 0
    for b in s:
        acc |= (b & 0x7F) << nb
        nb += 7
        if nb >= 8:
            out.append(acc & 0xFF)
            acc >>= 8
            nb -= 8
    return out


def main():
    S.build()
    # 1. the project, exported
    s = S.Script()
    t = build_project(s)
    s.raw(t, "sx 7D 53 47 01")
    log = S.run(s, t + 400)
    img = image_from_sysex([f for _, f in log.sysex])
    bpm = img[8] | img[9] << 8
    with open(os.path.join(HERE, "hwtest.sgq"), "wb") as f:
        f.write(img)
    print("hwtest.sgq: %d bytes, %d BPM, crc %08x" % (len(img), bpm, zlib.crc32(img)))

    # 2. it plays from the remote: four bars, then STOP; then MUTE track 1 and the tempo, in a second run
    bar = S.BAR_MS * 128.0 / bpm
    s = S.Script()
    t = build_project(s)
    t0 = t + 200
    remote(s, t0, 20)                                                        # PLAY
    t_stop = t0 + int(BARS * bar) + 40
    remote(s, t_stop, 20)                                                    # STOP
    log = S.run(s, t_stop + 400)
    starts = [tt for tt, st, _, _ in log.msgs if st == 0xFA and tt >= t0]   # (the project's own recording pass has one too)
    assert starts, "no MIDI Start"
    t_start = starts[0]
    clocks = [tt - t_start for tt in log.clock() if tt >= t_start]
    notes = {}
    for ch in range(4):
        notes[ch + 1] = [(round(tt - t_start), d1, d2) for tt, d1, d2 in log.notes(ch=ch, after=t_start) if tt - t_start < 2 * bar - 5]
    ons = len(log.notes(after=t_start))
    offs = len([1 for tt, _ in log.offs() if tt >= t_start])
    stops = [tt for tt, st, _, _ in log.msgs if st == 0xFC and tt >= t0]
    after_stop = len(log.notes(after=stops[0] + 1)) if stops else -1
    exp = {
        "bpm": bpm, "bar_ms": bar, "bars": BARS, "clocks_per_bar": 96,
        "clock_ms": round(60000.0 / bpm / 24, 3),
        "clock_count_4bars": len(clocks),
        "notes_2bars": notes,                                                  # channel -> [(ms from Start, note, vel)]
        "note_ons_4bars": ons, "note_offs_4bars": offs, "note_ons_after_stop": after_stop,
        "stop_sends_FC": bool(stops),
    }
    # 3. MUTE track 1 (CC 48) at bar 2, unmute at bar 4: when does channel 1 fall silent?
    s = S.Script()
    t = build_project(s)
    t0 = t + 200
    remote(s, t0, 20)
    remote(s, t0 + int(1.5 * bar), 48)
    remote(s, t0 + int(3.5 * bar), 48)
    remote(s, t0 + int(6 * bar) + 40, 20)
    log = S.run(s, t0 + int(6 * bar) + 400)
    t_start = [tt for tt, st, _, _ in log.msgs if st == 0xFA and tt >= t0][0]
    ch1 = [round(tt - t_start) for tt, _, _ in log.notes(ch=0, after=t_start) if tt - t_start < 6 * bar - 5]
    bars_with = sorted(set(int(x // bar) for x in ch1))
    exp["mute_test"] = {"mute_at_bar": 1.5, "unmute_at_bar": 3.5, "ch1_bars_with_notes": bars_with}
    # 4. tempo: CC 31 eight times, the clock speeds up; CC 30 eight times, back
    s = S.Script()
    t = build_project(s)
    t0 = t + 200
    remote(s, t0, 20)
    tt = t0 + int(bar)
    for _ in range(8):
        tt = remote(s, tt, 31)
    t_back = t0 + int(3 * bar)
    for _ in range(8):
        t_back = remote(s, t_back, 30)
    remote(s, t0 + int(5 * bar), 20)
    log = S.run(s, t0 + int(5 * bar) + 400)
    clk = log.clock()
    def rate(a, b):
        c = [x for x in clk if a <= x < b]
        return 60000.0 / 24 / ((c[-1] - c[0]) / (len(c) - 1)) if len(c) > 2 else 0
    exp["tempo_test"] = {"presses": 8, "bpm_before": round(rate(t0, t0 + bar)), "bpm_after_up": round(rate(t0 + 1.5 * bar, t0 + 2.8 * bar)),
                         "bpm_after_down": round(rate(t0 + 3.6 * bar, t0 + 4.8 * bar))}
    with open(os.path.join(HERE, "hwtest_expected.json"), "w") as f:
        json.dump(exp, f, indent=1)
    print(json.dumps({k: v for k, v in exp.items() if k != "notes_2bars"}, indent=1))
    for ch, ns in notes.items():
        print("ch %d: %d notes in 2 bars: %s" % (ch, len(ns), ns[:10]))


if __name__ == "__main__":
    main()
