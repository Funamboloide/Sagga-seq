# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA SEQ 0.11: the PC test's SysEx (firmware/src/sagga_test.c), for the runner on Windows (sagga_hw_explore.py)
and for the explorer (tests/sagga_explore.py --hw), which plays the same sessions in the simulator.

Only the standard library: the runner brings its own MIDI (mido)."""
import json

HEAD = [0xF0, 0x7D, 0x53, 0x47]
SX_TST, SX_TST_ANS, SX_TST_PROBE, SX_TST_LOG, SX_TST_HEARD = 0x70, 0x71, 0x72, 0x73, 0x74
HELLO, OPEN, BOOT, GO, EV, CLOSE, DONE, ABORT = range(8)
PRESS, RELEASE, ENC, KNOB, KEYS, PROBE, END, MIDI = range(1, 9)   # (0.18 MIDI: a message that comes in, the tablet, the grid)
NOGC = 0x0FFFFFFF
QUEUE = 64                     # the FM-1's queue of events
PER_FRAME = 24                 # events in one SysEx (13 bytes each; the FM-1 takes frames up to 640 bytes)
OPEN_STATES = {1: "asking", 2: "yes", 3: "no", 4: "no answer", 5: "playing: stop first"}
KIND_NAMES = {PRESS: "press", RELEASE: "release", ENC: "enc", KNOB: "knob", KEYS: "keys", PROBE: "probe", END: "end", MIDI: "midi"}
PORT1, PORT2, PORT_REMOTE = 0, 1, 2   # a MIDI event's port: 1, 2, the remote's (port 2 with two, else the only one)


def midi_ev(st, d1, d2, port=PORT_REMOTE):
    """(a, b) of a MIDI event: the status's low 7 bits | the port << 7, d1 | d2 << 7"""
    return (st & 0x7F) | (port << 7), (d1 & 127) | (d2 & 127) << 7


def put7(v, n):
    out = []
    for _ in range(n):
        out.append(v & 127)
        v >>= 7
    return out


def get7(b):
    v = 0
    for x in reversed(b):
        v = v << 7 | (x & 127)
    return v


def frame(sub, payload=()):
    return bytes(HEAD + [SX_TST, sub] + list(payload) + [0xF7])


def hello(): return frame(HELLO)
def open_(): return frame(OPEN)
def boot(): return frame(BOOT)
def go(listen=False): return frame(GO, [1] if listen else [])   # 0.20.3 listen: the FM-1 hears its ports too (the banco)
def close(): return frame(CLOSE)
def again(idx): return frame(6, put7(idx, 2))                     # a probe again (the FM-1 keeps the last two)
def taken(idx, n): return frame(7, put7(idx, 2) + [min(n, 127)])  # where events idx.. were taken, again
def diag(): return frame(DIAG)                                     # 0.20.9: the FM-1's counters since its boot


DIAG = 8
DIAG_FIELDS = ("hellos", "frames", "unsent", "first_ms", "gap_max", "resets", "configs", "cfg_ms", "suspends", "retries",
               "rx_pkts", "held", "bad", "xport", "sx_missed", "tx_pkts", "tx_wait_max", "tx_drop", "ms")   # 4 bytes each


def ev_frame(idx, events):
    """events: (t, kind, a, b[, gc]) a list of up to PER_FRAME, the first of them event number idx"""
    body = put7(idx, 2) + [len(events)]
    for e in events:
        t, kind, a, b = e[:4]
        gc = e[4] if len(e) > 4 and e[4] is not None else NOGC
        body += put7(t, 4) + [kind] + put7(a, 2) + put7(b, 2) + put7(gc, 4)
    return frame(EV, body)


def parse(msg):
    """a SysEx from the FM-1 (bytes F0 .. F7) -> (what, data) or None when it is not the test's"""
    m = list(msg)
    if len(m) < 6 or m[:4] != HEAD or m[-1] != 0xF7:
        return None
    cmd, p = m[4], m[5:-1]
    if cmd == SX_TST_ANS and p:
        sub, q = p[0], p[1:]
        if sub == HELLO and len(q) >= 21:
            return "hello", {"state": q[0], "booted": q[1], "playing": q[2], "boots": get7(q[3:5]),
                             "fault_vec": get7(q[5:10]), "fault_pc": get7(q[10:15]), "ms": get7(q[15:19]),
                             "usb_ports": q[19], "profile": q[20], "version": bytes(q[21:]).decode("ascii", "replace")}
        if sub == OPEN and q:
            return "open", q[0]
        if sub == BOOT and q:
            return "boot", q[0]
        if sub == GO and len(q) >= 4:
            return "go", get7(q[:4])
        if sub == GO:
            return "go", None
        if sub == EV and len(q) >= 4:
            return "ev", {"ok": q[0], "next": get7(q[1:3]), "free": q[3]}
        if sub == CLOSE and q:
            return "close", q[0]
        if sub == DONE and len(q) >= 7:
            d = {"applied": get7(q[0:2]), "late": get7(q[2:4]), "lag": get7(q[4:6]), "lost": q[6]}
            if len(q) >= 10:                           # (0.20.3, listening: how many heard, how many lost)
                d["heard"], d["heard_lost"] = get7(q[7:9]), q[9]
            return "done", d
        if sub == ABORT:
            return "abort", q[0] if q else 0
        if sub == DIAG and len(q) >= 4 * len(DIAG_FIELDS):
            return "diag", {name: get7(q[4 * k:4 * k + 4]) for k, name in enumerate(DIAG_FIELDS)}
        return "?", p
    if cmd == SX_TST_PROBE and len(p) >= 4:
        return "probe", (get7(p[0:2]), p[2], p[3], bytes(p[4:]).decode("ascii", "replace"))
    if cmd == SX_TST_LOG and p:
        n, out = p[0], []
        for i in range(n):
            s = p[1 + 10 * i: 11 + 10 * i]
            if len(s) == 10:
                out.append((get7(s[0:2]), get7(s[2:6]), get7(s[6:10])))
        return "log", out
    if cmd == SX_TST_HEARD and len(p) >= 3:            # 0.20.3: (seq, [(ms, gc, st, d1, d2, cable)])
        seq, n, out = get7(p[0:2]), p[2], []
        for i in range(n):
            s = p[3 + 12 * i: 15 + 12 * i]
            if len(s) == 12:
                out.append((get7(s[0:4]), get7(s[4:8]), 0x80 | s[8], s[9], s[10], s[11]))
        return "heard", (seq, out)
    return None


class Heard:
    """0.20.3: the messages the FM-1 heard from its ports, by their number in the session (a frame lost on the way =
    a gap: said, and the replay is then not the FM-1's)"""
    def __init__(self):
        self.by_seq = {}

    def add(self, seq, entries):
        for k, e in enumerate(entries):
            self.by_seq[(seq + k) & 0x3FFF] = list(e)

    def rows(self):
        """[[ms, gc, st, d1, d2, cable]] in the order the FM-1 heard them"""
        return [self.by_seq[k] for k in sorted(self.by_seq)]

    def gaps(self, total=None):
        n = len(self.by_seq)
        if total is None:
            total = (max(self.by_seq) + 1) if self.by_seq else 0
        return max(0, min(total, 0x4000) - n)


class Probes:
    """the pieces of the probes -> the text of each, by the index of its event"""
    def __init__(self):
        self.parts, self.done = {}, {}

    def add(self, idx, k, last, text):
        d = self.parts.setdefault(idx, {})
        d[k] = text
        if last:
            d["last"] = k
        if "last" in d and all(i in d for i in range(d["last"] + 1)):
            self.done[idx] = "".join(d[i] for i in range(d["last"] + 1))


def probe_dict(text):
    """the text of a probe -> {"G": {...}, "T1": {...}, ..., "H": {...}}, as the explorer's parse_probe reads a line"""
    out = {}
    for line in text.splitlines():
        if not line.startswith("PROBE "):
            continue
        who, _, rest = line[6:].partition(" ")
        d = {}
        if " msg=" in " " + rest:
            head, _, msg = (" " + rest).partition(" msg=")
            d["msg"] = msg
            rest = head
        for kv in rest.split():
            k, _, v = kv.partition("=")
            d[k] = v
        out[who] = d
    return out


class Pacer:
    """which events go to the FM-1 now: those due within `ahead` ms, as many as its queue has room for (the runner and
    the simulator's stand-in send the same frames)"""
    def __init__(self, events, ahead=600):
        self.events, self.ahead, self.sent = events, ahead, 0

    def next_frame(self, now_rel, free):
        """-> (frame, first index, count) or None. free: the queue's room (the FM-1's last answer, or an estimate)"""
        room = min(PER_FRAME, free)
        if self.sent >= len(self.events) or room <= 0:
            return None
        batch = []
        for e in self.events[self.sent:]:
            if e[0] > now_rel + self.ahead or len(batch) >= room:
                break
            batch.append(e)
        if not batch:
            return None
        return ev_frame(self.sent, batch), self.sent, len(batch)

    def free_estimate(self, now_rel):
        """the room in the FM-1's queue if every event due 60 ms ago was taken (the simulator's stand-in: no answers)"""
        taken = sum(1 for e in self.events[:self.sent] if e[0] <= now_rel - 60)
        return QUEUE - (self.sent - taken)


def save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=1)


def load(path):
    with open(path) as f:
        return json.load(f)
