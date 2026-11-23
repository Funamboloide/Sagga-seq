#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA SEQ 0.11: l'esploratore sull'FM-1 vero, da Windows.

    py -3.12 sagga_hw_explore.py [piano.json] [--sessioni N] [--port NOME] [--si] [--out CARTELLA]

Il piano lo fa l'esploratore in WSL (python3 tests/sagga_explore.py --hw-piano CARTELLA). Con l'FM-1 collegato via
USB, SAGGA SEQ 0.11 o 0.12 acceso e FERMO:
  1. chiede all'FM-1 il permesso: sullo schermo "PC TEST? SEL = YES"; premi SEL (un altro tasto = no);
  2. salva il progetto che l'FM-1 ha in memoria (EXPORT) in backup-<data>.sgq;
  3. per ogni sessione del piano: l'FM-1 si riavvia nel test (niente progetto, nessuno slot letto, niente scritto in
     flash), il PC preme i tasti ai tempi del piano, l'FM-1 dice dove ha preso ogni evento e manda le sonde (tutto lo
     stato), il PC tiene anche le note e il clock che escono;
  4. alla fine l'FM-1 si riavvia normale e il tuo progetto torna in memoria (IMPORT: "IMPORTED: SAVE TO KEEP IT").
Una mano su un tasto o una manopola dell'FM-1 ferma il test subito (e il PC rimette a posto). Tutto finisce in
raccolta-<data>.json: copialo in WSL e  python3 tests/sagga_explore.py --hw raccolta-<data>.json  confronta ogni
sessione con il simulatore. Il registro (hwexplore-<data>.log) dice cosa e' successo, sessione per sessione.

Serve Python 3.9+ con mido e python-rtmidi (run_hw_explore.ps1 li installa)."""
import argparse
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))
import sagga_testport as T     # noqa: E402
import sagga_hw_test as HT     # noqa: E402  (the ports, EXPORT and IMPORT of the hardware test)

MIDI_KEEP = {0x80, 0x90, 0xA0, 0xB0, 0xC0, 0xE0}
NOTE = [None]                  # the log file's own lines (every step, with the time): what the screen does not need


def note(s):
    f = NOTE[0]
    if f is not None:
        try:
            f.write("%s  %s\n" % (time.strftime("%H:%M:%S"), s))
            f.flush()
        except Exception:
            pass


def timed(fn, timeout, what):
    """fn() in a thread: its result, or None if it is still stuck after timeout s (a MIDI driver can hang on a device
    that has just gone; the thread is left behind, the program goes on)"""
    box = {}

    def run():
        try:
            box["r"] = fn()
        except Exception as e:
            box["e"] = e
    th = threading.Thread(target=run, daemon=True)
    th.start()
    th.join(timeout)
    if th.is_alive():
        note("%s: still stuck after %.0f s, left behind" % (what, timeout))
        return None
    if "e" in box:
        note("%s: %s: %s" % (what, type(box["e"]).__name__, box["e"]))
        return None
    return box.get("r")


# ------------------------------------------------------------------------------------------------ MIDI without callbacks
def free(x):
    """0.20.6: python-rtmidi's object away at once. On Linux each MidiIn / MidiOut is an ALSA sequencer client, and
    close_port() does not end it: left to the garbage collector they piled up at every reconnect, until ALSA had no
    client left to give (the first banco on the Pi stopped at its third session: 'error creating ALSA sequencer client
    object')"""
    try:
        x.delete()
    except Exception:
        pass


class RtLink:
    """python-rtmidi directly, and no callback in the driver: a thread of ours asks it for what came in. (mido hands
    the driver a Python callback; on Windows closing a port while a message arrives can then lock up for ever - the
    driver waits for the callback, the callback for Python. The first run on the user's PC stopped exactly there, as
    the FM-1 rebooted with its All Notes Off on the way.)"""
    def __init__(self, in_name, out_name):
        import rtmidi
        self.on_message, self._run = None, True
        self.inp = rtmidi.MidiIn(queue_size_limit=8192)
        self.inp.ignore_types(sysex=False, timing=False, active_sense=True)
        self.inp.open_port(self._index(self.inp.get_ports(), in_name))
        self.out = rtmidi.MidiOut()
        try:
            self.out.open_port(self._index(self.out.get_ports(), out_name))
        except Exception:
            self.inp.close_port()             # (a port left open is a port Windows will not give again)
            free(self.inp)
            free(self.out)
            raise
        self._th = threading.Thread(target=self._poll, daemon=True)
        self._th.start()

    @staticmethod
    def _index(names, name):
        if name not in names:
            raise IOError("%s is not there any more" % name)
        return names.index(name)

    def _poll(self):
        while self._run:
            try:
                m = self.inp.get_message()
            except Exception:
                m = None
            if m is None:
                time.sleep(0.001)
                continue
            cb = self.on_message
            if cb:
                cb(bytes(m[0]), time.perf_counter())

    def send(self, data):
        self.out.send_message(list(data))

    def close_input(self):
        self._run = False
        self._th.join(1.0)
        self.inp.close_port()
        free(self.inp)

    def close_output(self):
        self.out.close_port()
        free(self.out)

    def close(self):
        self.close_input()
        self.close_output()


class RtBackend:
    def _names(self, cls):
        import rtmidi  # noqa: F401
        x = cls()
        try:
            return list(dict.fromkeys(x.get_ports()))
        finally:
            free(x)

    def input_names(self):
        import rtmidi
        return self._names(rtmidi.MidiIn)

    def output_names(self):
        import rtmidi
        return self._names(rtmidi.MidiOut)

    def open(self, in_name, out_name):
        return RtLink(in_name, out_name)


def default_backend():
    try:
        import rtmidi  # noqa: F401
        return RtBackend()
    except Exception:
        return HT.MidoBackend()


GRAVE = []                     # ports whose closing hung: kept, so that nothing tries again; the program ends with
                               # os._exit


def close_output(link):
    if hasattr(link, "close_output"):
        return link.close_output()
    out = getattr(link, "out", None)
    if out is not None:
        out.close()


def close_input(link):
    if hasattr(link, "close_input"):
        return link.close_input()
    inp = getattr(link, "inp", None)
    if inp is not None:
        HT.close_input(inp)                    # (0.32.2: mido's `callback = None` puts its wrapper straight back in)


class Hub:
    """every FM-1 port open at once: what comes in from any of them, in order; SysEx out on the one that answered"""
    def __init__(self, ports):
        self.ports, self.ctl = ports, None

    def take(self):
        ev = []
        for p in self.ports:
            ev += p.take()
        ev.sort(key=lambda x: x[0])
        return ev

    def send(self, data, port=None):
        (port or self.ctl).send(data)

    def wait(self, what, timeout, keep=None):
        """the next answer of the test of that kind; the rest goes to keep (a list) if given"""
        end = time.perf_counter() + timeout
        while time.perf_counter() < end:
            for t, d in self.take():
                a = T.parse(d) if d[:1] == b"\xF0" else None
                if a and a[0] == what:
                    return a[1]
                if keep is not None:
                    keep.append((t, d))
            time.sleep(0.004)
        return None

    def send_and_go(self, frame, what):
        """a frame after which the FM-1 drops off the USB (BOOT, CLOSE: it reboots 80 ms after it): the inputs closed
        first, while it is still there (an input closed while its device goes can hang for ever: the first run on the
        user's PC); the frame; then the outputs (a port left open is one Windows does not give again: the second run)"""
        for p in self.ports:
            p.link.on_message = None
            if not timed(lambda link=p.link: close_input(link) or True, 3.0, "closing the input of %s" % p.label):
                GRAVE.append(p.link)
        ok = timed(lambda: self.ctl.send(frame) or True, 3.0, "sending %s" % what)
        note("%s sent on %s: %s" % (what, self.ctl.label, "ok" if ok else "NOT SENT"))
        for p in self.ports:
            if not timed(lambda link=p.link: close_output(link) or True, 3.0, "closing the output of %s" % p.label):
                GRAVE.append(p.link)
        note("%s: ports closed" % what)
        self.ports = []
        return bool(ok)

    def close(self):
        """every port closed, each in a thread of its own that may not hang the program"""
        for p in self.ports:
            p.link.on_message = None

            timed(lambda link=p.link: link.close() or True, 3.0, "closing %s" % p.label)
        self.ports = []


def connect(backend, want, say, timeout=0.0, quiet=False):
    """the FM-1's ports, and the one its answers come back on (with two USB ports: the second, MIDIIN2) -> (hub, hello)
    or (None, None). The test's SysEx goes out on that one too."""
    end = time.perf_counter() + timeout
    tries = 0
    while True:
        tries += 1
        ports = timed(lambda: HT.find_ports(backend, want, _Note() if quiet else _Say(say)), 10.0, "looking for the ports") or []
        note("try %d: ports %s" % (tries, [p.label for p in ports]))
        if ports:
            hub = Hub(ports)
            for p in ports:
                p.tally = T.Tally()                   # (0.23.1: every message counted as it comes in, for the session's account)
            other = 0                                 # (0.20.9: what came in that was no answer, for the log)
            for p in ports:
                other += len(hub.take())
                try:
                    p.send(T.hello())
                except Exception as e:
                    note("HELLO on %s: %s" % (p.label, e))
                    continue
                end_w = time.perf_counter() + 1.0
                got = None
                while time.perf_counter() < end_w and got is None:
                    for q in ports:
                        for t, d in q.take():
                            a = T.parse(d) if d[:1] == b"\xF0" else None
                            if a and a[0] == "hello":
                                got = (q, a[1])
                            else:
                                other += 1
                    time.sleep(0.005)
                if got:
                    hub.ctl = got[0]
                    note("HELLO sent on %s, answered on %s: %s" % (p.label, got[0].label, got[1]))
                    return hub, got[1]
            note("try %d: no answer to HELLO on %d ports (%d other messages came in)" % (tries, len(ports), other))
            hub.close()
        if time.perf_counter() >= end:
            return None, None
        time.sleep(0.7)


class _Note:
    def __init__(self): self.say = note


class _Say:
    def __init__(self, say): self.say = say


# ---- 0.23.1 the session's account: what the FM-1 says it sent against what the computer received and heard.
# The FM-1 counts what its program hands to the USB by port and kind (DIAG); the test asks before GO, while nothing plays,
# and after QUIET (the FM-1 stopped, every note off, the ports still): between the two both sides counted the same
# messages. Where the numbers part says where a message was lost: inside the FM-1 (its own account does not add up),
# between the FM-1 and the computer's USB driver (the driver's byte count, on a Pi), or in the computer (the driver
# has every byte, the program heard less).
def _tallies(hub):
    """what each of the FM-1's ports has heard so far: [port 1, port 2] (with one port: the only one, then nothing)"""
    zero = dict.fromkeys(T.OUT_KINDS, 0)
    ports = list(hub.ports)
    if len(ports) > 1 and hub.ctl is not None:        # (with two the test answers on port 2)
        ports = [p for p in ports if p is not hub.ctl][:1] + [hub.ctl]
    out = [p.tally.snapshot() if getattr(p, "tally", None) is not None else dict(zero) for p in ports[:2]]
    return out + [dict(zero)] * (2 - len(out))


def _still(hub, quiet_s=0.3, max_s=6.0, wait=time.sleep):
    """wait until neither port has heard anything for quiet_s (at most max_s) -> ([port 1 still?, port 2 still?], s)"""
    t0 = time.perf_counter()
    last, last_t = _tallies(hub), [t0, t0]
    while True:
        wait(0.05)
        now, cur = time.perf_counter(), _tallies(hub)
        for i in range(2):
            if cur[i] != last[i]:
                last[i], last_t[i] = cur[i], now
        still = [now - last_t[i] >= quiet_s for i in range(2)]
        if all(still) or now - t0 >= max_s:
            return still, round(now - t0, 2)


def _ask(hub, frame, what, timeout=1.0):
    try:
        hub.send(frame)
        return hub.wait(what, timeout)
    except Exception:
        return None


def counts_begin(hub, alsa=None, wait=time.sleep):
    """before GO -> the mark (the FM-1's counters, what the ports heard, the driver's counts), or None: an FM-1 before
    0.23.1, which does not count what it sends"""
    still, _ = _still(hub, 0.15, 1.5, wait)
    d = _ask(hub, T.diag(), "diag")
    if not d or "p1_ticks" not in d:
        return None
    return {"diag": d, "heard": _tallies(hub), "alsa": alsa() if alsa else None, "still": still}


def counts_end(hub, mark, alsa=None, wait=time.sleep):
    """after the session: QUIET, the ports still, DIAG again -> the session's account (None: no answer any more).
    "fermo": port by port, whether it stood still at both ends - only then its two counts are of the same messages"""
    if not mark:
        return None
    q = _ask(hub, T.quiet(), "quiet")
    still, took = _still(hub, 0.3, 6.0, wait)
    d = _ask(hub, T.diag(), "diag")
    if not d or "p1_ticks" not in d:
        return None
    wait(0.25)                                         # (the answer itself and any straggler: counted on both sides)
    heard, a1, d0 = _tallies(hub), (alsa() if alsa else None), mark["diag"]
    out = {"fermo": [bool(still[i] and mark["still"][i] and q == 1) for i in range(2)], "attesa": took, "quiet": q,
           "fm1": {"p%d" % (i + 1): {k: d["p%d_%s" % (i + 1, k)] - d0["p%d_%s" % (i + 1, k)] for k in T.OUT_KINDS} for i in range(2)},
           "pi": {"p%d" % (i + 1): {k: heard[i][k] - mark["heard"][i][k] for k in T.OUT_KINDS} for i in range(2)},
           "usb": dict({k: d[k] - d0[k] for k in ("tx_ev", "tx_drop", "tx_noconf", "tx_flush", "tx_pkts", "resets", "configs", "suspends")},
                       tx_ring=d["tx_ring"], tx_ring_prima=d0["tx_ring"], tx_wait_max=d["tx_wait_max"]),
           "alsa": None}
    a0 = mark.get("alsa")
    if a0 and a1 and len(a0.get("rx", [])) == len(a1.get("rx", [])):
        out["alsa"] = {"rx": [b - a for a, b in zip(a0["rx"], a1["rx"])], "over": [b - a for a, b in zip(a0.get("over", []), a1.get("over", []))],
                       "pool": (a1.get("pool") or 0) - (a0.get("pool") or 0) if a1.get("pool") is not None and a0.get("pool") is not None else None}
    return out


KIND_IT = {"ticks": "tick del clock", "on": "note", "off": "note-off", "cc": "CC", "other": "altri messaggi"}


def counts_missing(c):
    """how many messages the FM-1 says it sent and the program did not hear, on the ports that stood still"""
    if not c:
        return 0
    return sum(max(0, c["fm1"][p][k] - c["pi"][p][k]) for i, p in enumerate(("p1", "p2")) if c["fermo"][i] for k in T.OUT_KINDS[:5])


def counts_verdict(c):
    """the account read: [] when what the FM-1 sent is what the computer heard, else the lines that say what is missing
    and where it was lost (counts_missing: how many; lines of more heard than sent alone: nothing is missing)"""
    if not c:
        return []
    out, missing = [], 0
    for i, port in enumerate(("p1", "p2")):
        if not c["fermo"][i]:
            continue                                   # (that port never stood still: its two counts are not of the same messages)
        f, h = c["fm1"][port], c["pi"][port]
        diff = [(k, f[k] - h[k]) for k in T.OUT_KINDS[:5] if f[k] != h[k]]
        if not diff:
            continue
        lost = [(k, n) for k, n in diff if n > 0]
        more = [(k, -n) for k, n in diff if n < 0]
        missing += sum(n for _, n in lost)
        if lost:
            out.append("porta %s: l'FM-1 ha mandato %s che il programma non ha sentito" % (port[1], ", ".join("%d %s" % (n, KIND_IT[k]) for k, n in lost)))
        if more:
            out.append("porta %s: il programma ha sentito %s in piu' di quelli che l'FM-1 dice di aver mandato" % (port[1], ", ".join("%d %s" % (n, KIND_IT[k]) for k, n in more)))
    if not out or not missing:
        return out                                     # (nothing to say, or only more heard than sent: no place to look for)
    u = c["usb"]
    sent = sum(c["fm1"][p][k] for p in ("p1", "p2") for k in T.OUT_KINDS[:5])
    gone = u["tx_ev"] + u["tx_drop"] + u["tx_noconf"] + u["tx_flush"] + u["tx_ring"] - u.get("tx_ring_prima", 0)
    thrown = u["tx_drop"] + u["tx_noconf"] + u["tx_flush"]
    if thrown:
        out.append("dentro l'FM-1: %d messaggi scartati prima dell'USB (%d con l'anello pieno, %d senza configurazione, %d a un reset del bus)"
                   % (thrown, u["tx_drop"], u["tx_noconf"], u["tx_flush"]))
    if sent != gone:
        out.append("dentro l'FM-1 i conti non tornano: %d messaggi dati all'USB, %d messi nei pacchetti o scartati" % (sent, gone))
    if u["resets"] or u["configs"] or u["suspends"]:
        out.append("l'USB dell'FM-1 nella sessione: %d reset del bus, %d configurazioni, %d sospensioni" % (u["resets"], u["configs"], u["suspends"]))
    a = c.get("alsa")
    if a and len(a["rx"]) >= 1:
        short = [(i + 1, c["fm1"]["p%d" % (i + 1)]["bytes"] - a["rx"][i]) for i in range(min(2, len(a["rx"]))) if c["fermo"][i]]
        short = [(i, n) for i, n in short if n]
        if not short and not thrown and sent == gone:
            out.append("il driver USB del computer ha ricevuto tutti i byte che l'FM-1 ha mandato: persi DOPO, nel computer (ALSA o il programma)")
        elif short:
            out.append("al driver USB del computer mancano " + ", ".join("%d byte sulla porta %d" % (n, i) for i, n in short)
                       + (": persi fra l'FM-1 e il computer (l'FM-1 li aveva messi nei pacchetti USB)" if not thrown and sent == gone else ""))
        if any(a.get("over") or []):
            out.append("il driver del computer ha perso byte per conto suo (overrun: %s)" % a["over"])
        if a.get("pool"):
            out.append("ALSA ha scartato %d eventi (il suo serbatoio era pieno)" % a["pool"])
    elif not thrown and sent == gone:
        out.append("l'FM-1 li ha messi tutti nei pacchetti USB: persi dopo l'FM-1 (il cavo, o il computer)")
    return out


def run_session(hub, sess, say, counts=False):
    """one session of the plan on the FM-1 (already rebooted into the test) -> its record (counts: an FM-1 from 0.23.1,
    which counts what it sends: the session's account in "conti")"""
    events = [tuple(e) for e in sess["eventi"]]
    probes_at = [i for i, e in enumerate(events) if e[1] == T.PROBE]
    rec = {"go_ms": None, "presi": {}, "sonde": {}, "midi": [], "done": None, "abort": None, "errore": None,
           "rimandati": 0, "di_nuovo": 0}
    hub.take()
    mark = counts_begin(hub) if counts else None      # (0.23.1: what the FM-1 says it sent against what was heard)
    hub.send(T.go())
    go = hub.wait("go", 2.0)
    if go is None:
        rec["errore"] = "l'FM-1 non ha risposto a GO"
        return rec
    rec["go_ms"] = go
    t_go = time.perf_counter()
    pacer, free, pending = T.Pacer(events), T.QUEUE, None
    pr = T.Probes()
    asked = {}
    t_done, last_rx = None, time.perf_counter()
    shown = t_go
    while True:
        now = time.perf_counter()
        rel = (now - t_go) * 1000.0
        if now - shown > 10.0:
            shown = now
            print("      ... %d eventi su %d, %d sonde" % (len(rec["presi"]), len(events), len(pr.done)), flush=True)
        for t, d in hub.take():
            last_rx = t
            if d[0] == 0xF0:
                a = T.parse(d)
                if not a:
                    continue
                k, v = a
                if k == "ev" and pending is not None:
                    pacer.sent = pending[1] + pending[2] if v["ok"] else v["next"]
                    free, pending = v["free"], None
                elif k == "probe":
                    pr.add(*v)
                elif k == "log":
                    for idx, ms, gc in v:
                        rec["presi"][str(idx)] = [ms, gc]
                elif k == "done":
                    rec["done"], t_done = v, now
                elif k == "abort":
                    rec["abort"] = v
            elif (d[0] & 0xF0) in MIDI_KEEP or d[0] in (0xF8, 0xFA, 0xFB, 0xFC):
                rec["midi"].append([round((t - t_go) * 1000.0, 1)] + list(d[:3]) + [0] * (3 - len(d[:3])))
        if rec["abort"] is not None:
            break
        try:
            if pending is None and rec["done"] is None:
                f = pacer.next_frame(rel, free)
                if f:
                    hub.send(f[0])
                    pending = (f[0], f[1], f[2], now, 0)
            elif pending is not None and now - pending[3] > 1.0:   # no answer: once more (the FM-1 says where it is)
                if pending[4] >= 5:
                    rec["errore"] = "l'FM-1 non accetta piu' gli eventi (all'evento %d)" % pending[1]
                    break
                hub.send(pending[0])
                pending = pending[:3] + (now, pending[4] + 1)
                rec["rimandati"] += 1
            # a probe taken (it, or an event after it: they are taken in order) and not whole half a second later:
            # again, at once (the FM-1 keeps the last two)
            top = max((int(x) for x in rec["presi"]), default=-1)
            for i in probes_at:
                if i <= top and i not in pr.done and asked.get(i, (0, 0))[0] < 3:
                    n_ask, since = asked.get(i, (0, now))
                    if i not in asked:
                        asked[i] = (0, now)
                    elif now - since > 0.5:
                        hub.send(T.again(i))
                        asked[i] = (n_ask + 1, now)
                        rec["di_nuovo"] += 1
            if rec["done"] is not None:
                n = rec["done"]["applied"]
                missing = [i for i in range(n) if str(i) not in rec["presi"]]
                if missing and now - t_done > 0.3 and not rec.get("_taken_asked"):
                    rec["_taken_asked"] = 1
                    runs, a0 = [], missing[0]
                    for x, y in zip(missing, missing[1:] + [None]):
                        if y != x + 1:
                            runs.append((a0, x - a0 + 1))
                            a0 = y
                    for s0, c in runs:
                        while c > 0:
                            hub.send(T.taken(s0, min(c, 120)))
                            s0, c = s0 + 120, c - 120
                whole = all(i in pr.done for i in probes_at if i < n)
                if (whole and not missing) or now - t_done > 4.0:
                    break
        except Exception as e:                                       # (the FM-1 gone from the USB)
            rec["errore"] = "l'FM-1 e' sparito dall'USB (%s)" % e
            break
        if now - last_rx > 6.0 and rel > 2000:
            rec["errore"] = "l'FM-1 non manda niente da 6 s (all'evento %d di %d)" % (len(rec["presi"]), len(events))
            break
        time.sleep(0.003)
    rec.pop("_taken_asked", None)
    rec["sonde"] = {str(k): v for k, v in pr.done.items()}
    if mark and not rec["errore"] and rec["abort"] is None:
        rec["conti"] = counts_end(hub, mark)
    return rec


def quick(sess, rec):
    """what can be said at once, without the simulator"""
    out = []
    if rec.get("errore"):
        out.append("ERRORE: " + rec["errore"])
    if rec.get("abort") is not None:
        out.append("fermato da una mano")
    roles = dict(zip([i for i, e in enumerate(sess["eventi"]) if e[1] == T.PROBE], sess.get("sonde", [])))
    by_role = {roles.get(int(k)): T.probe_dict(v) for k, v in rec["sonde"].items()}
    pb, pf = by_role.get("battuta"), by_role.get("fermo")
    if pb and pb.get("G", {}).get("play") == "1":
        late = ["T%d" % t for t in range(1, 17) if pb.get("T%d" % t, {}).get("ok") == "0"]
        if late:
            out.append("FASE: fuori fase alla fine " + ",".join(late))
    if pf and pf.get("G", {}).get("play") == "0":
        on = {}
        for m in rec["midi"]:
            st, d1, d2 = m[1], m[2], m[3]
            if (st & 0xF0) == 0x90 and d2:
                on[(st & 15, d1)] = on.get((st & 15, d1), 0) + 1
            elif ((st & 0xF0) == 0x80 or ((st & 0xF0) == 0x90 and not d2)) and on.get((st & 15, d1), 0) > 0:
                on[(st & 15, d1)] -= 1
            elif (st & 0xF0) == 0xB0 and d1 in (120, 123):
                for k in [k for k in on if k[0] == (st & 15)]:
                    on[k] = 0
        hung = [k for k, v in on.items() if v > 0]
        if hung:
            out.append("NOTE APPESE: %d" % len(hung))
    lags = [int(p.get("H", {}).get("lag", 0)) for p in by_role.values() if p]
    n_probes = sum(1 for e in sess["eventi"] if e[1] == T.PROBE)
    return out, len(rec["sonde"]), n_probes, max(lags) if lags else 0


def vkey(v):
    """'0.18' -> (0, 18): versions compared as numbers (0.9 < 0.18)"""
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        return (0,)


def main(argv=None, backend=None, wait=time.sleep):
    ap = argparse.ArgumentParser(description="SAGGA SEQ: l'esploratore sull'FM-1 vero")
    ap.add_argument("piano", nargs="?", default=os.path.join(HERE, "piano.json"), help="il piano (piano.json)")
    ap.add_argument("--sessioni", type=int, default=0, help="solo le prime N sessioni del piano")
    ap.add_argument("--port", help="parte del nome della porta MIDI dell'FM-1")
    ap.add_argument("--si", action="store_true", help="non chiedere conferma")
    ap.add_argument("--out", default=HERE, help="dove scrivere raccolta, registro e backup")
    ap.add_argument("--senza-backup", action="store_true", help="anche se il progetto in memoria non si salva sul PC")
    a = ap.parse_args(argv)
    backend = backend or default_backend()
    ts = time.strftime("%Y%m%d-%H%M%S")
    rep = HT.Report(os.path.join(a.out, "hwexplore-%s.log" % ts))
    say = rep.say
    NOTE[0] = rep.f
    plan = T.load(a.piano)
    sessions = plan["sessioni"][:a.sessioni] if a.sessioni else plan["sessioni"]
    minutes = (sum(s["eventi"][-1][0] for s in sessions) / 1000.0 + 9 * len(sessions)) / 60.0
    say("SAGGA SEQ, l'esploratore sull'FM-1: %s, %d sessioni, circa %.0f minuti" % (os.path.basename(a.piano), len(sessions), minutes + 1))
    hub, hello = connect(backend, a.port, say)
    if hub is None:
        say("Nessun FM-1 risponde al test: e' acceso, collegato via USB, con SAGGA SEQ 0.11 o piu' recente (con il test dal PC)?")
        say("Chiudi Ableton e i programmi che tengono le porte MIDI. --port NOME per scegliere la porta.")
        rep.close()
        return 3
    say("FM-1: SAGGA SEQ %s, porta del test: %s" % (hello["version"], hub.ctl.label))
    want = str(plan.get("firmware", ""))
    midi_ev = any(e[1] == T.MIDI for sess in sessions for e in sess["eventi"])
    if midi_ev and want and vkey(hello["version"]) < vkey(want):              # (0.18: the tablet and the grid are MIDI events)
        say("Questo piano ha il tablet e il grid (eventi MIDI): serve SAGGA SEQ %s o piu' recente sull'FM-1, che ha la %s. "
            "Aggiorna l'FM-1, o fai un piano per la sua versione." % (want, hello["version"]))
        rep.close()
        return 3
    backup = None
    if hello["booted"]:
        olds = sorted(f for f in os.listdir(a.out) if f.startswith("backup-") and f.endswith(".sgq"))
        if olds:
            backup = os.path.join(a.out, olds[-1])
            say("L'FM-1 e' gia' nel test (una corsa di prima, interrotta): si continua da qui; alla fine torna in memoria "
                "il progetto salvato da quella corsa, %s." % olds[-1])
        else:
            say("L'FM-1 e' gia' nel test (una corsa di prima, interrotta): si continua da qui; alla fine l'FM-1 ricarica "
                "l'ultimo slot salvato.")
    else:
        if hello["playing"]:
            say("L'FM-1 sta suonando: fermalo (PLAY) e rilancia.")
            rep.close()
            return 1
        if not a.si:
            print("Per ogni sessione l'FM-1 si riavvia nel test; il progetto che ha in memoria viene salvato qui e torna alla fine.")
            print("Durante il test non toccare l'FM-1: una mano su un tasto lo ferma.")
            if input("Avanti? [s/N] ").strip().lower() not in ("s", "si", "y", "yes"):
                rep.close()
                return 1
        img, st = HT.export(hub.ctl)
        note("EXPORT on %s: %s" % (hub.ctl.label, st))
        for p in [x for x in hub.ports if x is not hub.ctl] if not img else []:
            img, st = HT.export(p)
            note("EXPORT on %s: %s" % (p.label, st))
            if img:
                break
        if img:
            backup = os.path.join(a.out, "backup-%s.sgq" % ts)
            with open(backup, "wb") as f:
                f.write(img)
            say("Il progetto in memoria e' in %s" % backup)
        elif not a.senza_backup:
            say("Il progetto in memoria non si salva sul PC (EXPORT: %s): mi fermo, il tuo progetto resta dov'e'." % st)
            say("(Con --senza-backup si va avanti lo stesso: alla fine l'FM-1 ricarica l'ultimo slot salvato.)")
            hub.close()
            rep.close()
            return 1
        else:
            say("EXPORT del progetto: %s; si va avanti (--senza-backup)" % st)
        hub.take()
        hub.send(T.open_())
        say(">>> Sull'FM-1: premi SEL per dire si' (20 secondi). Un altro tasto = no.")
        ans = hub.wait("open", 2.0)
        if ans == 1:
            ans = hub.wait("open", 25.0)
        if ans != 2:
            say("L'FM-1 dice: %s. Niente test." % T.OPEN_STATES.get(ans, "nessuna risposta"))
            hub.close()
            rep.close()
            return 1
        say("Si'. Si comincia.")
    out = dict(plan)
    out["sessioni"] = []
    out["fm1"] = {"version": hello["version"], "porta": hub.ctl.label}
    out["quando"] = ts
    path = os.path.join(a.out, "raccolta-%s.json" % ts)
    rc = 0
    rebooted = bool(hello["booted"])
    try:
        for k, sess in enumerate(sessions):
            print("%s  l'FM-1 si riavvia nel test..." % sess["nome"], flush=True)
            rebooted = True
            hub.send_and_go(T.boot(), "BOOT")
            note("%s: ports closed, waiting for the FM-1" % sess["nome"])
            wait(2.0)
            hub, hello = connect(backend, a.port, say, timeout=40.0, quiet=True)
            if hub is None or not hello["booted"]:
                say("Dopo il riavvio l'FM-1 non torna nel test (%s): fermo qui." % (
                    "non risponde" if hub is None else "non si e' riavviato: ha detto di no al BOOT"))
                rc = 1
                break
            print("%s  ci siamo: %s, circa %.0f s" % (sess["nome"], sess["situazione"], sess["eventi"][-1][0] / 1000.0 + 2), flush=True)
            t0 = time.perf_counter()
            rec = run_session(hub, sess, say, counts=vkey(hello.get("version")) >= (0, 23, 1))
            rec["hello_prima"] = hello
            if rec.get("errore") or rec.get("abort") is not None:      # it may be rebooting by itself: wait for it
                hub.close()
                hub, h2 = connect(backend, a.port, say, timeout=30.0, quiet=True)
                rec["hello_dopo"] = h2
                hello = h2 or hello
            s2 = dict(sess)
            s2["fm1"] = rec
            out["sessioni"].append(s2)
            T.save(path, out)
            probs, got, want, lag = quick(sess, rec)
            if counts_missing(rec.get("conti")):
                probs += ["CONTI: " + x for x in counts_verdict(rec.get("conti"))[:2]]
            say("%s  %-46s %3d gesti, %2d/%2d sonde, %4.0f s, ciclo max %3d ms  %s" % (
                sess["nome"], sess["situazione"][:46], len(sess["gesti"]), got, want, time.perf_counter() - t0, lag,
                "; ".join(probs) if probs else "ok"))
            if rec.get("abort") is not None:
                say("Fermato da una mano sull'FM-1: il test finisce qui.")
                break
            if hub is None:
                say("L'FM-1 non torna: fermo qui.")
                rc = 1
                break
    except KeyboardInterrupt:
        say("Interrotto dal PC.")
    finally:
        if hub is not None and hello and hello.get("booted"):
            print("L'FM-1 si riavvia normale...", flush=True)
            hub.send_and_go(T.close(), "CLOSE")
            wait(2.0)
            hub, hello = connect(backend, a.port, say, timeout=40.0, quiet=True)
        if hub is not None and hello and hello.get("booted"):
            say("L'FM-1 e' ancora nel test: spegnilo e riaccendilo (ricarica l'ultimo slot salvato).")
        elif hub is not None and rebooted and backup:
            with open(backup, "rb") as f:
                st = HT.import_image(hub.ctl, f.read())
            say("Il tuo progetto e' tornato in memoria (%s): sull'FM-1 IMPORTED: SAVE TO KEEP IT." % st)
        elif hub is None:
            say("L'FM-1 non risponde dopo la fine del test: spegnilo e riaccendilo (ricarica l'ultimo slot salvato)%s." % (
                "; il progetto che avevi in memoria e' in %s" % backup if backup else ""))
        if hub is not None:
            hub.close()
    say("")
    say("Raccolta: %s (%d sessioni)" % (path, len(out["sessioni"])))
    say("Copiala in WSL e:  python3 tests/sagga_explore.py --hw %s" % os.path.basename(path))
    rep.close()
    return rc


if __name__ == "__main__":
    rc = main()
    sys.stdout.flush()
    os._exit(rc)                # (no port closed at the exit: see GRAVE)
