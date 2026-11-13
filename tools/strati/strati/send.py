# SPDX-License-Identifier: GPL-3.0-only
"""A Relitto .syx to the FM-1 over USB-MIDI, one message at a time, each one answered (the FM-1's STATUS:
7D 52 4C 40 code idx idx). Needs mido and python-rtmidi. On Windows close whatever holds the FM-1's port."""
import re
import sys
import time

HEAD = bytes([0x7D, 0x52, 0x4C])


def split_messages(data):
    out, i = [], 0
    while i < len(data):
        if data[i] != 0xF0:
            i += 1
            continue
        j = data.find(b"\xF7", i)
        if j < 0:
            break
        out.append(data[i:j + 1])
        i = j + 1
    return out


def with_slot(msg, slot):
    """the BEGIN message with another slot, and the table references in the parameters moved with it"""
    if len(msg) < 6 or msg[4] != 0x01:
        return msg
    b = bytearray(msg)
    old = b[5]
    b[5] = slot
    np_ = b[5 + 1 + 12]
    for i in (0, 4):                                    # A_TAB, B_TAB
        k = 5 + 1 + 12 + 1 + i
        if k < len(b) and 8 <= b[k] < 12 and b[k] - 8 == old:
            b[k] = 8 + slot
    return bytes(b)


def send_file(path, port=None, slot=None, log=print):
    try:
        import mido
    except ImportError:
        log("mido / python-rtmidi missing: pip install mido python-rtmidi")
        return 2
    with open(path, "rb") as f:
        msgs = split_messages(f.read())
    if not msgs:
        log("%s: no SysEx in it" % path)
        return 2
    if slot is not None:
        msgs = [with_slot(m, slot) for m in msgs]
    ins, outs = mido.get_input_names(), mido.get_output_names()
    want = (port or "").lower()
    pick = [n for n in ins if (want and want in n.lower()) or (not want and re.search(r"felucca|fm-1|relitto", n, re.I))]
    if not pick:
        log("no FM-1 port among %s (--port NAME)" % ins)
        return 3
    in_name = pick[-1]                                  # (with two ports, the control one is the second)
    out_name = next((o for o in outs if o == in_name), None) or next((o for o in outs if re.sub(r"MIDIIN(\d+)", r"MIDIOUT\1", in_name).split(" ")[0] in o), outs[0] if outs else None)
    log("FM-1: in %s, out %s" % (in_name, out_name))
    got = []
    with mido.open_input(in_name, callback=lambda m: got.append(m)) as mi, mido.open_output(out_name) as mo:
        try:
            mi._rt.ignore_types(sysex=False)
        except Exception:
            pass
        for k, m in enumerate(msgs):
            got.clear()
            mo.send(mido.Message("sysex", data=list(m[1:-1])))
            t0 = time.time()
            ok = None
            while time.time() - t0 < 3.0 and ok is None:
                for r in got:
                    d = bytes(r.data)
                    if d[:3] == HEAD and len(d) >= 7 and d[3] == 0x40:
                        ok = (d[4], d[5] | d[6] << 7)
                time.sleep(0.002)
            if ok is None:
                log("message %d of %d: no answer (is Relitto 0.2 or later running?)" % (k + 1, len(msgs)))
                return 4
            if ok[0]:
                log("message %d of %d: the FM-1 says %s" % (k + 1, len(msgs), {1: "bad frame", 2: "flash error", 3: "CRC", 4: "out of order"}.get(ok[0], ok[0])))
                return 5
            if k % 20 == 0 or k == len(msgs) - 1:
                log("  %d / %d" % (k + 1, len(msgs)))
    log("done: the sound is in the FM-1 (it plays it now; it is kept in its USER slot)")
    return 0


if __name__ == "__main__":
    sys.exit(send_file(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
