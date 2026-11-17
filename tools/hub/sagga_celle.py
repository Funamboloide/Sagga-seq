# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA HUB 0.20.9 (0.21: le pagine nuove): il custode delle celle dell'FM-1.

RaspiMIDIHub 6 perde le celle di un dispositivo che non c'e': il suo salvataggio automatico (ogni 15-30 secondi, quando
qualcosa e' cambiato - e le pagine SAGGA cambiano sempre, seguono l'FM-1) scrive solo le celle dei dispositivi presenti.
Se in quel momento l'FM-1 si sta riavviando, o e' spento, le sue celle spariscono anche dalla memoria di RaspiMIDIHub, e
quando l'FM-1 torna non le rimette. Il custode le ricorda per lui:
  * finche' l'FM-1 c'e', ricorda le sue celle (le pagine, i synth, i filtri e le mappature di ognuna), in
    /boot/firmware/sagga/celle-fm1.json (anche dopo un riavvio del Pi);
  * quando l'FM-1 se ne va e torna (spento, riavviato, aggiornato: lo dicono il suo numero USB e la sua scheda audio
    nel kernel, che cambiano a ogni volta), o quando se ne va e torna l'altro capo di una cella, aspetta che
    RaspiMIDIHub abbia fatto il suo (5 secondi), poi rimette quelle che mancano, come erano;
  * una cella che sparisce mentre tutti e due i capi ci sono l'hai tolta tu: la dimentica. Toglile con l'FM-1 acceso;
  * una pagina SAGGA nuova (0.21: aggiunta in RaspiMIDIHub; o tutte, la prima volta, senza ricordo) riceve da sola le
    sue celle: la pagina verso la porta 2 dell'FM-1, la porta 2 verso la pagina (SAGGA BeatStep: solo l'OUT). Una volta
    per pagina, e solo con USB PORTS 2: tolte a mano, restano tolte;
  * i Launchpad non hanno celle (parlano solo con il bridge): mai rimesse.
Il custode gira dentro sagga_fw (la pagina del hub); durante l'esploratore del banco aspetta (il banco stacca e rimette
le sue celle da se')."""
import json
import os
import time
import urllib.request

PAGE_NAMES = {"sagga_remote": "SAGGA Remote", "sagga_mutes": "SAGGA Mutes", "sagga_motori": "SAGGA Motori",
              "sagga_break": "SAGGA Break", "sagga_mod": "SAGGA Mod", "sagga_live": "SAGGA Live", "sagga_bsp": "SAGGA BeatStep"}
MEMORY_FILE = "/boot/firmware/sagga/celle-fm1.json"
SYSFS_USB = "/sys/bus/usb/devices"


# ------------------------------------------------------------------------------------------------ RaspiMIDIHub's API
class HubAPI:
    """RaspiMIDIHub's own web API (the one its pages use), on this Pi"""
    def __init__(self, base="http://127.0.0.1", timeout=4.0):
        self.base, self.timeout = base.rstrip("/"), timeout

    def _req(self, method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"} if data else {})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            raw = r.read()
        return json.loads(raw.decode() or "null") if raw else None

    def get(self, path):
        return self._req("GET", path)

    def patch(self, path, body):
        return self._req("PATCH", path, body)

    def post(self, path, body):
        return self._req("POST", path, body)

    def delete(self, path):
        return self._req("DELETE", path)


def is_fm1(name):
    n = (name or "").lower()
    return "felucca" in n or "fm-1" in n


def is_launchpad(d):
    return "launchpad" in ((d or {}).get("name", "") + (d or {}).get("default_name", "")).lower()


def online_by_client(devices):
    return {d.get("client_id"): d for d in devices or [] if d.get("online") and d.get("client_id") is not None}


def fm1_of(by):
    fm = [d for d in by.values() if is_fm1(d.get("name")) or is_fm1(d.get("default_name"))]
    return fm[0] if fm else None


def remote_port(fm):
    """the FM-1's port of the pages and the grid: the second with USB PORTS 2, else the only one"""
    outs = [p for p in (fm or {}).get("ports", []) if p.get("is_output")]
    return outs[1]["port_id"] if len(outs) >= 2 else (outs[0]["port_id"] if outs else 0)


# ------------------------------------------------------------------------------------------------- USB, from sysfs
USBDEVFS_RESET = 0x5514            # _IO('U', 20): a port reset of the device, as the usbreset tool


def usb_devnum(usb_path, sysfs=SYSFS_USB):
    """the device's number on its bus: a new one at every enumeration (unplugged, rebooted, updated) - None if unknown"""
    if not usb_path:
        return None
    try:
        with open(os.path.join(sysfs, usb_path, "devnum")) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def usb_instance(usb_path, sysfs=SYSFS_USB):
    """which appearance of the device this is: its number on the bus (a new one at every enumeration) and its sound
    cards' sysfs nodes (new ones whenever the kernel made the card again: a port reset, the driver bound again - the
    device keeps its number then, but its ALSA client and every cell of it went and came back) - None if nothing is read"""
    if not usb_path:
        return None
    num = usb_devnum(usb_path, sysfs)
    cards = []
    try:
        for itf in sorted(os.listdir(sysfs)):
            if not itf.startswith(usb_path + ":"):
                continue
            snd = os.path.join(sysfs, itf, "sound")
            try:
                for c in sorted(os.listdir(snd)):
                    if c.startswith("card"):
                        cards.append((c, os.stat(os.path.join(snd, c)).st_ino))
            except OSError:
                continue
    except OSError:
        pass
    if num is None and not cards:
        return None
    return (num, tuple(cards))


def alsa_midi_counts(usb_path, sysfs=SYSFS_USB, proc="/proc/asound"):
    """0.23.1: what the Pi's USB MIDI driver has received from the device, port by port - "Rx bytes" of
    /proc/asound/cardN/midi0: every MIDI byte the driver took out of the USB packets, counted before ALSA's sequencer
    and before any program - and the bytes it had no room for (overruns); then the events ALSA's sequencer could not
    keep for the programs that listen (the "Alloc failures" of the input pools, all clients together).
    -> {"rx": [port 1, port 2 ...], "over": [...], "pool": n or None}, or None when it cannot be read"""
    inst = usb_instance(usb_path, sysfs)
    if not inst:
        return None
    for card, _ in inst[1]:
        try:
            with open(os.path.join(proc, card, "midi0")) as f:
                text = f.read()
        except OSError:
            continue
        rx, over, cur = {}, {}, None
        for ln in text.splitlines():
            w = ln.split()
            if len(w) == 2 and w[0] in ("Input", "Output") and w[1].isdigit():
                cur = int(w[1]) if w[0] == "Input" else None
            elif cur is not None and ":" in ln:
                k, v = [x.strip() for x in ln.split(":", 1)]
                if k == "Rx bytes" and v.isdigit():
                    rx[cur] = int(v)
                elif k == "Overruns" and v.isdigit():
                    over[cur] = int(v)
        if not rx:
            continue
        n = max(rx) + 1
        pool = None
        try:
            with open(os.path.join(proc, "seq", "clients")) as f:
                inp = False
                for ln in f.read().splitlines():
                    t = ln.strip()
                    if t.endswith("pool :") or t.endswith("pool:"):
                        inp = t.lower().startswith("input")
                    elif t.startswith("Client ") or t.startswith("Port "):
                        inp = False
                    elif inp and t.startswith("Alloc failures") and t.split(":")[-1].strip().isdigit():
                        pool = (pool or 0) + int(t.split(":")[-1].strip())
        except OSError:
            pool = None
        return {"rx": [rx.get(i, 0) for i in range(n)], "over": [over.get(i, 0) for i in range(n)], "pool": pool}
    return None


def fm1_usb_path(sysfs=SYSFS_USB):
    """the FM-1's USB path ("1-1.2"), by its product name, or None"""
    try:
        names = sorted(os.listdir(sysfs))
    except OSError:
        return None
    for n in names:
        if ":" in n:
            continue
        try:
            with open(os.path.join(sysfs, n, "product")) as f:
                if is_fm1(f.read()):
                    return n
        except OSError:
            continue
    return None


def usb_reset(usb_path, sysfs=SYSFS_USB, devfs="/dev/bus/usb", ioctl=None):
    """a port reset of the device: the host addresses and configures it again, also when the device restarted without
    the host seeing it go (it then waits at address 0, and only a reset finds it) -> True if the kernel was asked"""
    if not usb_path:
        return False
    try:
        with open(os.path.join(sysfs, usb_path, "busnum")) as f:
            bus = int(f.read().strip())
        num = usb_devnum(usb_path, sysfs)
        if num is None:
            return False
        fd = os.open(os.path.join(devfs, "%03d" % bus, "%03d" % num), os.O_WRONLY)
    except (OSError, ValueError):
        return False
    try:
        if ioctl is None:
            import fcntl
            ioctl = fcntl.ioctl
        ioctl(fd, USBDEVFS_RESET, 0)
    except OSError:
        pass                                          # (a reset that fails: the kernel takes the device off and looks again)
    finally:
        os.close(fd)
    return True


def usb_reenumerate(usb_path, sysfs=SYSFS_USB, wait=time.sleep, devfs="/dev/bus/usb"):
    """the host finds the device again: a port reset; where that cannot be asked (no device node), the configuration
    taken away and given back (authorized 0, then 1) -> "reset", "authorized" or None"""
    if not usb_path:
        return None
    if usb_reset(usb_path, sysfs, devfs):
        return "reset"
    p = os.path.join(sysfs, usb_path, "authorized")
    try:
        with open(p, "w") as f:
            f.write("0")
        wait(0.5)
        with open(p, "w") as f:
            f.write("1")
        return "authorized"
    except OSError:
        return None


# ------------------------------------------------------------------------------------------------------ the cells
def cell_key(c):
    return (c["fm1_src"], c["fm1_port"], c["other"] or c["other_name"], c["other_port"])


def describe(conns, by, fm, pages_only=False, others_only=False):
    """the live cells between the FM-1 and anything else -> [cell]: which way, the FM-1's port, the other end (its stable
    id, name, plugin type, port), its filter and mappings (as RaspiMIDIHub gives them)"""
    fmc = fm["client_id"]
    out = []
    for c in conns or []:
        if c.get("offline") or c.get("src_client") is None:
            continue
        src, dst = c["src_client"], c["dst_client"]
        if src == dst or fmc not in (src, dst):
            continue
        other = by.get(dst if src == fmc else src) or {}
        page = other.get("plugin_type") in PAGE_NAMES
        if (pages_only and not page) or (others_only and page) or is_launchpad(other):
            continue
        cell = {"fm1_src": src == fmc, "fm1_port": c["src_port"] if src == fmc else c["dst_port"],
                "other_port": c["dst_port"] if src == fmc else c["src_port"],
                "other": other.get("stable_id"), "other_name": other.get("name", "?"), "other_type": other.get("plugin_type"),
                "id": c.get("id") or "%d:%d-%d:%d" % (src, c["src_port"], dst, c["dst_port"])}
        if c.get("filter"):
            cell["filter"] = c["filter"]
        if c.get("mappings"):
            cell["mappings"] = c["mappings"]
        out.append(cell)
    return out


def needed_page_cells(by, fm):
    """the cells the SAGGA pages need: each page to the FM-1's remote port, that port to each page (SAGGA BeatStep:
    only its OUT to the FM-1 - its IN is the BeatStep Pro's, and what the FM-1 sends back would be taken for a pad)"""
    rp = remote_port(fm)
    out = []
    for d in by.values():
        typ = d.get("plugin_type")
        if typ not in PAGE_NAMES:
            continue
        for fm1_src in ((False,) if typ == "sagga_bsp" else (False, True)):
            out.append({"fm1_src": fm1_src, "fm1_port": rp, "other_port": 0, "other": d.get("stable_id"),
                        "other_name": d.get("name", PAGE_NAMES[typ]), "other_type": typ})
    return out


def find_other(by, cell):
    oc = next((cid for cid, d in by.items() if cell.get("other") and d.get("stable_id") == cell["other"]), None)
    if oc is None:
        oc = next((cid for cid, d in by.items() if d.get("name") == cell.get("other_name")), None)
    return oc


def make(api, by, fm, cell):
    """the cell into the matrix, with its filter and mappings -> None, or what went wrong"""
    oc = find_other(by, cell)
    if oc is None:
        return "%s non c'e'" % cell.get("other_name")
    fmc = fm["client_id"]
    edge = (fmc, cell["fm1_port"], oc, cell["other_port"]) if cell["fm1_src"] else (oc, cell["other_port"], fmc, cell["fm1_port"])
    cid = "%d:%d-%d:%d" % edge
    try:
        api.post("/api/connections", {"src_client": edge[0], "src_port": edge[1], "dst_client": edge[2], "dst_port": edge[3]})
    except Exception as e:
        return "la cella non si fa (%s)" % e
    flt = cell.get("filter")
    try:
        if isinstance(flt, dict) and "channel_mask" in flt:
            api.patch("/api/connections/%s" % cid, {"channel_mask": flt["channel_mask"], "msg_types": flt.get("msg_types", [])})
        for m in cell.get("mappings") or []:
            api.post("/api/mappings/%s" % cid, m)
    except Exception as e:
        return "la cella c'e', il suo filtro no (%s)" % e
    return None


def arrow(c):
    return "FM-1 %d -> %s" % (c["fm1_port"] + 1, c.get("other_name")) if c["fm1_src"] else "%s -> FM-1 %d" % (c.get("other_name"), c["fm1_port"] + 1)


# ------------------------------------------------------------------------------------------------------ the keeper
class Keeper:
    """remembers the FM-1's cells while it is there; puts back the ones RaspiMIDIHub lost while an end was away"""
    GRACE = 5.0                       # s after an end comes back: RaspiMIDIHub restores its cells by itself first
    RETRY = 15.0                      # s between two tries at a cell that would not come back

    def __init__(self, api, path=MEMORY_FILE, write=None, say=None, sysfs=SYSFS_USB, clock=time.monotonic):
        self.api, self.path, self.sysfs, self.clock = api, path, sysfs, clock
        self.write = write or self._write_plain
        self.say = say or (lambda s: None)
        self.mem = {}                 # key -> {"cell": cell, "broken": an end went away since it was last seen, "tried": t}
        self.ends = {}                # an end (stable id or name) -> ((client, its USB appearance, a USB device), since)
        self.events = []              # [(time, text)] the last things done, for the page
        self.pages = set()            # the SAGGA pages that have had their cells (0.21: a new one gets them by itself,
                                      # once: no memory yet = every page is new, 0.20.9's "first time")
        self.fm_end = None            # the FM-1's stable id, the last time it was here
        self._saved = None
        try:
            with open(path) as f:
                data = json.load(f) or {}
            for c in data.get("celle") or []:
                self.mem[cell_key(c)] = {"cell": c, "broken": True, "tried": None}   # (what happened while nobody watched?)
            # (a memory of 0.20.9 has no pages: the ones here at the first look had their cells then, or lost them by hand)
            self.pages = set(data["pagine"]) if isinstance(data.get("pagine"), list) else None
            self._saved = self._dump()
        except (OSError, ValueError, KeyError, TypeError):
            pass

    @staticmethod
    def _write_plain(path, data):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    def _dump(self):
        cells = [dict((k, v) for k, v in m["cell"].items() if k != "id") for _, m in sorted(self.mem.items(), key=lambda x: repr(x[0]))]
        data = {"celle": cells}
        if self.pages is not None:
            data["pagine"] = sorted(self.pages)
        return json.dumps(data, indent=1, sort_keys=True).encode()

    def _event(self, text):
        self.events = (self.events + [(time.strftime("%Y-%m-%d %H:%M:%S"), text)])[-12:]
        self.say(text)

    def _end_of(self, d):
        return d.get("stable_id") or d.get("name")

    def all_broken(self):
        """nothing is known for sure (RaspiMIDIHub did not answer, the banco held the FM-1): every end as new"""
        for m in self.mem.values():
            m["broken"] = True
        self.ends = {}

    def poll(self):
        """one look at the matrix -> the cells put back now"""
        now = self.clock()
        try:
            by = online_by_client(self.api.get("/api/devices"))
            conns = self.api.get("/api/connections") or []
        except Exception:
            self.all_broken()
            return []
        fm = fm1_of(by)
        if fm is not None:
            self.fm_end = self._end_of(fm)
        # which ends are here, since when: one that went away (or came back as another device number) breaks its cells
        here = {}
        for cid, d in by.items():
            e = self._end_of(d)
            if e:
                here[e] = (cid, usb_instance(d.get("usb_path"), self.sysfs), bool(d.get("usb_path")))
        for e in list(self.ends):
            if e not in here or self.ends[e][0] != here[e]:
                self._break(e)
                del self.ends[e]
        for e, ident in here.items():
            if e not in self.ends:
                self.ends[e] = (ident, now)
                self._break(e)
        if fm is None:
            return []
        settled = lambda e: e in self.ends and now - self.ends[e][1] >= self.GRACE
        # sure that an end did not go away between two looks: its USB appearance is read (a plugin never goes)
        sure = lambda e: e in self.ends and (self.ends[e][0][1] is not None or not self.ends[e][0][2])
        if not settled(self.fm_end):
            return []
        current = {cell_key(c): c for c in describe(conns, by, fm)}
        # 0.21: a SAGGA page that is new here (added in RaspiMIDIHub's interface, or all of them the first time) gets
        # its cells with the FM-1's remote port, once: taken away by hand afterwards, they stay away. Only with USB
        # PORTS 2: with one port the pages' port is the synths' too, and the cells would stay there when it becomes two
        two = len([p for p in fm.get("ports", []) if p.get("is_output")]) >= 2
        needed = needed_page_cells(by, fm) if two else []
        if two and self.pages is None:
            self.pages = {c.get("other") or c.get("other_name") for c in needed}
        fresh = set()
        for c in needed:
            e = c.get("other") or c.get("other_name")
            if e in self.pages or not settled(e):
                continue
            fresh.add(e)
            k = cell_key(c)
            if k not in current and k not in self.mem:
                self.mem[k] = {"cell": c, "broken": True, "tried": None, "new": True}
        if fresh:
            self.pages |= fresh
        done, failed, linked = [], [], []
        for k, m in list(self.mem.items()):
            c = m["cell"]
            if k in current:
                m["cell"], m["broken"], m["tried"] = current[k], False, None
                m.pop("new", None)
                continue
            other = c.get("other") or c.get("other_name")
            if not settled(other):
                m["broken"] = True                    # (its other end is away: it waits for it)
                continue
            if not m["broken"] and sure(self.fm_end) and sure(other):
                del self.mem[k]                       # (both ends here all along: taken away by hand)
                continue
            if m["tried"] is not None and now - m["tried"] < self.RETRY:
                continue
            m["tried"] = now
            err = make(self.api, by, fm, c)
            if err:
                failed.append((c, err))
            else:
                (linked if m.pop("new", None) else done).append(c)
                m["broken"], m["tried"] = False, None
        for k, c in current.items():
            if k not in self.mem:
                self.mem[k] = {"cell": c, "broken": False, "tried": None}
        if done:
            self._event("RaspiMIDIHub aveva perso %d celle dell'FM-1: rimesse (%s)" % (len(done), ", ".join(arrow(c) for c in done[:4]) +
                                                                                       (" ..." if len(done) > 4 else "")))
        if linked:
            names = sorted({c.get("other_name") or "?" for c in linked})
            self._event("%s: %s all'FM-1 (%d celle)" % (", ".join(names[:4]) + (" ..." if len(names) > 4 else ""),
                                                      "pagina nuova, collegata" if len(names) == 1 else "pagine nuove, collegate", len(linked)))
        for c, err in failed[:2]:
            self._event("la cella %s non torna: %s" % (arrow(c), err))
        dump = self._dump()
        if dump != self._saved:
            try:
                self.write(self.path, dump)
                self._saved = dump
            except Exception as e:
                self.say("il ricordo delle celle non si scrive (%s)" % e)
        return done + linked

    def _break(self, end):
        for m in self.mem.values():
            c = m["cell"]
            if end == self.fm_end or end in (c.get("other"), c.get("other_name")):
                m["broken"] = True


def run_forever(keeper, paused, period=3.0, sleep=time.sleep):
    """the keeper's thread: one look every few seconds; while paused() (the banco holds the FM-1) every end counts as
    new when it ends"""
    was = False
    while True:
        try:
            if paused():
                if not was:
                    keeper.all_broken()
                was = True
            else:
                if was:
                    keeper.all_broken()
                was = False
                keeper.poll()
        except Exception as e:                        # (never the page's service down for this)
            keeper.say("custode delle celle: %s" % e)
        sleep(period)
