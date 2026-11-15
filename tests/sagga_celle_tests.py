#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA HUB 0.20.9: the keeper of the FM-1's cells (tools/hub/sagga_celle.py) against a fake RaspiMIDIHub that loses
the cells of a device that is away (as RaspiMIDIHub 6's autosave does), and a fake sysfs (the USB device numbers): the
cells come back after a reboot of the FM-1, after a synth comes back, with their filters and mappings; one taken away by
hand stays away; the first time the pages' cells come from the rule; a Launchpad's never; RaspiMIDIHub away = nothing
lost; the memory on the SD and back after a restart."""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "hub"))
import sagga_celle as C                # noqa: E402

CHECKS, FAILS = [0], []


def check(cond, what):
    CHECKS[0] += 1
    if not cond:
        FAILS.append(what)
        print("  FAIL:", what)


def group(name):
    print(name)


FM1, SYNTH, LP, REMOTE, LIVE = 24, 28, 32, 130, 135


class FakeHub:
    """RaspiMIDIHub's devices and cells; lose(dev) = what its autosave does while a device is away"""
    def __init__(self, sysfs):
        self.sysfs = sysfs
        self.on = {"fm1": True, "synth": True, "lp": True}
        self.synth_client = SYNTH
        self.conns = {}                    # (src, sp, dst, dp) -> {"filter":..., "mappings": [...]}
        for c in [(REMOTE, 0, FM1, 1), (FM1, 1, REMOTE, 0), (LIVE, 0, FM1, 1), (FM1, 1, LIVE, 0), (FM1, 0, LP, 0)]:
            self.conns[c] = {}
        self.conns[(FM1, 0, SYNTH, 0)] = {"filter": {"channel_mask": 3, "msg_types": ["note_on"]},
                                         "mappings": [{"type": "cc_to_cc", "src_cc": 1, "dst_cc": 74}]}
        self.conns[(SYNTH, 0, FM1, 0)] = {}
        self.posts, self.patches, self.maps = [], [], []
        self.down = False
        self.devnum = {"1-1.2": 5, "1-1.3": 7, "1-1.4": 9}
        self.write_sysfs()

    def write_sysfs(self):
        for p, n in self.devnum.items():
            os.makedirs(os.path.join(self.sysfs, p), exist_ok=True)
            with open(os.path.join(self.sysfs, p, "devnum"), "w") as f:
                f.write("%d\n" % n)

    def reboot_fm1(self, lose=True):
        """the FM-1 away and back between two looks: a new device number, and (lose) RaspiMIDIHub's autosave fell in
        the second it was away"""
        self.devnum["1-1.2"] += 1
        self.write_sysfs()
        if lose:
            self.conns = {c: v for c, v in self.conns.items() if FM1 not in (c[0], c[2])}

    def devices(self):
        ports = [{"port_id": 0, "is_output": True, "is_input": True}, {"port_id": 1, "is_output": True, "is_input": True}]
        out = []
        if self.on["fm1"]:
            out.append({"client_id": FM1, "name": "Felucca", "online": True, "ports": ports, "stable_id": "usb-0001:0002-FM1",
                        "usb_path": "1-1.2"})
        if self.on["synth"]:
            out.append({"client_id": self.synth_client, "name": "MicroFreak", "online": True, "ports": ports[:1],
                        "stable_id": "usb-1c75:0601-MF", "usb_path": "1-1.3"})
        if self.on["lp"]:
            out.append({"client_id": LP, "name": "Launchpad Mini MK3", "online": True, "ports": ports, "stable_id": "usb-lp",
                        "usb_path": "1-1.4"})
        out.append({"client_id": REMOTE, "name": "SAGGA Remote 1", "online": True, "ports": ports[:1], "plugin_type": "sagga_remote",
                    "stable_id": "plugin-r1"})
        out.append({"client_id": LIVE, "name": "SAGGA Live 1", "online": True, "ports": ports[:1], "plugin_type": "sagga_live",
                    "stable_id": "plugin-l1"})
        out.append({"client_id": None, "name": "Old synth", "online": False, "stable_id": "usb-old"})
        return out

    def get(self, path):
        if self.down:
            raise IOError("connection refused")
        if path == "/api/devices":
            return self.devices()
        if path == "/api/connections":
            here = {d["client_id"] for d in self.devices() if d.get("online")}
            out = []
            for c, v in sorted(self.conns.items()):
                if c[0] in here and c[2] in here:
                    e = {"id": "%d:%d-%d:%d" % c, "src_client": c[0], "src_port": c[1], "dst_client": c[2], "dst_port": c[3],
                         "filtered": bool(v)}
                    e.update(v)
                    out.append(e)
            out.append({"id": "offline:usb-old:0|plugin-r1:0", "src_stable_id": "usb-old", "offline": True})
            return out
        raise IOError("404 %s" % path)

    def post(self, path, body):
        if path.startswith("/api/mappings/"):
            c = tuple(int(x) for x in path.rsplit("/", 1)[1].replace("-", ":").split(":"))
            self.maps.append((c, body))
            self.conns[c].setdefault("mappings", []).append(body)
            return {"status": "added"}
        c = (body["src_client"], body["src_port"], body["dst_client"], body["dst_port"])
        if c in self.conns:
            raise IOError("400 already connected")
        self.posts.append(c)
        self.conns[c] = {}
        return {"status": "created"}

    def patch(self, path, body):
        c = tuple(int(x) for x in path.rsplit("/", 1)[1].replace("-", ":").split(":"))
        self.patches.append((c, body))
        self.conns[c]["filter"] = dict(body)
        return {"status": "updated"}


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def keeper(hub, d, clock, path=None):
    written = []

    def write(p, data):
        written.append(p)
        with open(p, "wb") as f:
            f.write(data)
    k = C.Keeper(hub, path=path or os.path.join(d, "celle-fm1.json"), write=write, sysfs=os.path.join(d, "sys"), clock=clock)
    return k, written


def settle(k, clock, n=3, step=3.0):
    out = []
    for _ in range(n):
        out += k.poll()
        clock.t += step
    return out


def t_reboot():
    group("0.20.9: the keeper - the FM-1 rebooted, RaspiMIDIHub lost its cells: back, filters and mappings too")
    with tempfile.TemporaryDirectory() as d:
        hub, clock = FakeHub(os.path.join(d, "sys")), Clock()
        k, written = keeper(hub, d, clock)
        before = dict(hub.conns)
        got = settle(k, clock)
        check(not got and not hub.posts, "the first looks: everything there, nothing done (%s)" % hub.posts)
        mem = json.load(open(os.path.join(d, "celle-fm1.json")))["celle"]
        check(len(mem) == 6 and not [c for c in mem if "Launchpad" in c["other_name"]],
              "remembered: the 4 cells of the pages, the 2 of the synth, not the Launchpad's (%d)" % len(mem))
        hub.reboot_fm1()
        clock.t += 1.0
        got = k.poll()
        check(not got and not hub.posts, "just back: RaspiMIDIHub's turn first (%s)" % hub.posts)
        got = settle(k, clock, n=3)
        want = {c for c in before if LP not in (c[0], c[2])}
        check(set(hub.posts) == want and len(got) == 6, "after the grace: the 6 cells back (%s)" % sorted(hub.posts))
        f = hub.conns.get((FM1, 0, SYNTH, 0), {})
        check(f.get("filter") == {"channel_mask": 3, "msg_types": ["note_on"]} and f.get("mappings") == [{"type": "cc_to_cc", "src_cc": 1, "dst_cc": 74}],
              "the synth's cell with its filter and its mapping (%s)" % f)
        check((FM1, 0, LP, 0) not in hub.conns, "the Launchpad's cell not put back")
        check(k.events and "6 celle" in k.events[-1][1], "said for the page (%s)" % k.events[-1:])
        n = len(hub.posts)
        settle(k, clock, n=4)
        check(len(hub.posts) == n, "then nothing more (%d)" % (len(hub.posts) - n))
        # a reboot RaspiMIDIHub got right: nothing to do
        hub.reboot_fm1(lose=False)
        settle(k, clock, n=4)
        check(len(hub.posts) == n, "a reboot without losses: nothing done (%d)" % (len(hub.posts) - n))


def t_by_hand():
    group("0.20.9: the keeper - a cell taken away by hand stays away; the FM-1 away waits; RaspiMIDIHub away loses nothing")
    with tempfile.TemporaryDirectory() as d:
        hub, clock = FakeHub(os.path.join(d, "sys")), Clock()
        k, _ = keeper(hub, d, clock)
        settle(k, clock)
        del hub.conns[(FM1, 1, LIVE, 0)]
        settle(k, clock, n=4)
        check(not hub.posts and (FM1, 1, LIVE, 0) not in hub.conns, "taken away with both ends here: not put back (%s)" % hub.posts)
        check(len(json.load(open(os.path.join(d, "celle-fm1.json")))["celle"]) == 5, "and forgotten in the memory")
        # the FM-1 off for a while, RaspiMIDIHub forgets its cells, then it is on again
        hub.on["fm1"] = False
        hub.conns = {c: v for c, v in hub.conns.items() if FM1 not in (c[0], c[2])}
        settle(k, clock, n=5)
        check(not hub.posts, "the FM-1 away: nothing to do")
        hub.on["fm1"] = True
        hub.devnum["1-1.2"] += 1
        hub.write_sysfs()
        settle(k, clock, n=4)
        check(len(hub.posts) == 5 and (FM1, 1, LIVE, 0) not in hub.posts, "on again: the 5 remembered back, not the one taken away (%s)" % sorted(hub.posts))
        # RaspiMIDIHub restarting: its API away, then back with the FM-1's cells lost
        hub.posts.clear()
        hub.down = True
        settle(k, clock, n=2)
        hub.down = False
        del hub.conns[(REMOTE, 0, FM1, 1)]
        settle(k, clock, n=4)
        check(hub.posts == [(REMOTE, 0, FM1, 1)], "RaspiMIDIHub back after a restart: the lost cell back, not forgotten (%s)" % hub.posts)


def t_synth_back():
    group("0.20.9: the keeper - a synth unplugged and back as another ALSA client: its cell back")
    with tempfile.TemporaryDirectory() as d:
        hub, clock = FakeHub(os.path.join(d, "sys")), Clock()
        k, _ = keeper(hub, d, clock)
        settle(k, clock)
        hub.on["synth"] = False
        hub.conns = {c: v for c, v in hub.conns.items() if SYNTH not in (c[0], c[2])}
        settle(k, clock, n=2)
        hub.on["synth"] = True
        hub.synth_client = 40
        hub.devnum["1-1.3"] += 1
        hub.write_sysfs()
        settle(k, clock, n=4)
        check(set(hub.posts) == {(FM1, 0, 40, 0), (40, 0, FM1, 0)}, "the synth's two cells, on its new client (%s)" % hub.posts)
        check(hub.patches and hub.patches[0][0] == (FM1, 0, 40, 0), "its filter too (%s)" % hub.patches)


def t_first_time():
    group("0.20.9: the keeper - the first time: the cells the pages need, from the rule; then the memory after a restart")
    with tempfile.TemporaryDirectory() as d:
        hub, clock = FakeHub(os.path.join(d, "sys")), Clock()
        for c in [(REMOTE, 0, FM1, 1), (FM1, 1, REMOTE, 0), (FM1, 1, LIVE, 0)]:
            del hub.conns[c]                         # (the matrix after the 0.20.8 banco: the pages' cells lost)
        k, _ = keeper(hub, d, clock)
        settle(k, clock, n=4)
        check(set(hub.posts) == {(REMOTE, 0, FM1, 1), (FM1, 1, REMOTE, 0), (FM1, 1, LIVE, 0)},
              "no memory yet: the missing cells of the pages from the rule (%s)" % sorted(hub.posts))
        # a new keeper (the Pi restarted) with the memory on the SD: what is missing comes back
        hub.posts.clear()
        del hub.conns[(SYNTH, 0, FM1, 0)]
        clock2 = Clock()
        k2, _ = keeper(hub, d, clock2)
        settle(k2, clock2, n=4)
        check(hub.posts == [(SYNTH, 0, FM1, 0)], "after a restart: the memory read, the missing cell back (%s)" % hub.posts)
        # the memory there and a page's cell taken away by hand: the rule does not bring it back
        hub.posts.clear()
        del hub.conns[(FM1, 1, LIVE, 0)]
        settle(k2, clock2, n=4)
        check(not hub.posts, "with a memory the rule is not used again (%s)" % hub.posts)


def t_no_sysfs():
    group("0.20.9: the keeper - no device number (sysfs not readable): a missing cell is put back, never forgotten")
    with tempfile.TemporaryDirectory() as d:
        hub, clock = FakeHub(os.path.join(d, "sys")), Clock()
        k, _ = keeper(hub, d, clock)
        k.sysfs = os.path.join(d, "nothing")
        settle(k, clock)
        del hub.conns[(FM1, 1, REMOTE, 0)]           # (a reboot between two looks that nobody saw)
        settle(k, clock, n=3)
        check(hub.posts == [(FM1, 1, REMOTE, 0)], "not sure it was a hand: put back (%s)" % hub.posts)


def t_same_number():
    group("0.20.9: the keeper - the FM-1's sound card made again with the same device number (a port reset): its cells back")
    with tempfile.TemporaryDirectory() as d:
        hub, clock = FakeHub(os.path.join(d, "sys")), Clock()
        snd = os.path.join(d, "sys", "1-1.2:1.0", "sound")
        os.makedirs(os.path.join(snd, "card9"))
        k, _ = keeper(hub, d, clock)
        settle(k, clock)
        os.makedirs(os.path.join(snd, "new"))
        os.rmdir(os.path.join(snd, "card9"))
        os.rename(os.path.join(snd, "new"), os.path.join(snd, "card9"))
        hub.conns = {c: v for c, v in hub.conns.items() if FM1 not in (c[0], c[2])}
        settle(k, clock, n=4)
        check(len(hub.posts) == 6, "the device number as before, the card another: the 6 cells back, not forgotten (%s)" % sorted(hub.posts))


def t_usb():
    group("0.20.9: the USB helpers - the FM-1 by its product name, the device number, a new enumeration asked")
    with tempfile.TemporaryDirectory() as d:
        for n, prod in (("1-1.2", "Felucca\n"), ("1-1.3", "MicroFreak\n"), ("1-1.2:1.0", "Felucca\n")):
            os.makedirs(os.path.join(d, n))
            with open(os.path.join(d, n, "product"), "w") as f:
                f.write(prod)
        with open(os.path.join(d, "1-1.2", "devnum"), "w") as f:
            f.write("12\n")
        with open(os.path.join(d, "1-1.2", "authorized"), "w") as f:
            f.write("1\n")
        check(C.fm1_usb_path(d) == "1-1.2", "the FM-1's USB path (%s)" % C.fm1_usb_path(d))
        check(C.usb_devnum("1-1.2", d) == 12 and C.usb_devnum("9-9", d) is None and C.usb_devnum("", d) is None, "its device number")
        waits = []
        nodev = os.path.join(d, "no-dev")
        how = C.usb_reenumerate("1-1.2", d, wait=waits.append, devfs=nodev)
        check(how == "authorized" and waits == [0.5] and open(os.path.join(d, "1-1.2", "authorized")).read() == "1",
              "no device node: the configuration away and back (0, a pause, 1) (%s)" % how)
        check(not C.usb_reenumerate("9-9", d, wait=waits.append, devfs=nodev) and not C.usb_reenumerate(None, d), "no device: no")
        # the port reset: the node /dev/bus/usb/<bus>/<devnum>, the ioctl of usbreset
        with open(os.path.join(d, "1-1.2", "busnum"), "w") as f:
            f.write("1\n")
        os.makedirs(os.path.join(d, "dev", "001"))
        open(os.path.join(d, "dev", "001", "012"), "w").close()
        calls = []
        ok = C.usb_reset("1-1.2", d, devfs=os.path.join(d, "dev"), ioctl=lambda fd, req, arg: calls.append((req, arg)))
        check(ok and calls == [(0x5514, 0)], "a port reset: USBDEVFS_RESET on bus 1 device 12 (%s)" % calls)

        def failing(fd, req, arg):
            raise OSError(19, "No such device")
        check(C.usb_reset("1-1.2", d, devfs=os.path.join(d, "dev"), ioctl=failing), "a reset the device did not survive: asked all the same")
        check(not C.usb_reset("1-1.2", d, devfs=nodev) and not C.usb_reset("", d), "no node: not asked")
        # which appearance of the device: its number, its sound card's node
        os.makedirs(os.path.join(d, "1-1.2:1.0", "sound", "card9"))
        a = C.usb_instance("1-1.2", d)
        os.makedirs(os.path.join(d, "1-1.2:1.0", "sound", "card9b"))        # (a new node while the old one is there: another inode)
        os.rmdir(os.path.join(d, "1-1.2:1.0", "sound", "card9"))
        os.rename(os.path.join(d, "1-1.2:1.0", "sound", "card9b"), os.path.join(d, "1-1.2:1.0", "sound", "card9"))
        b = C.usb_instance("1-1.2", d)
        check(a and b and a[0] == b[0] == 12 and a != b and C.usb_instance("9-9", d) is None and C.usb_instance("", d) is None,
              "the same device number, the card made again: another appearance (%s %s)" % (a, b))


def t_thread():
    group("0.20.9: the keeper's thread - paused while the banco runs, every end new after it")
    calls = []

    class K:
        def poll(self):
            calls.append("poll")

        def all_broken(self):
            calls.append("broken")

        def say(self, s):
            calls.append(s)
    seq = iter([False, True, True, False, False])

    class Stop(Exception):
        pass

    def sleep(_):
        if len(calls) > 20:
            raise Stop()
    paused = lambda: next(seq)
    try:
        C.run_forever(K(), paused, sleep=sleep)
    except (Stop, StopIteration):
        pass
    check(calls[:5] == ["poll", "broken", "broken", "poll", "poll"], "poll, paused (all broken once), then broken again and poll (%s)" % calls[:6])


def main():
    for t in (t_reboot, t_by_hand, t_synth_back, t_first_time, t_no_sysfs, t_same_number, t_usb, t_thread):
        t()
    print("sagga celle: %d checks, %d failures" % (CHECKS[0], len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
