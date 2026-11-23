#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA HUB 0.20.3: l'esploratore del banco - l'FM-1, il Pi e il grid insieme, sul Pi.

    sudo python3 sagga_banco.py [--piano banco_piano.json | fm1_piano.json] [--sessioni N] [--out CARTELLA] [--solo-matrice]
                                [--non-staccare] [--rimetti]

L'esploratore sull'FM-1 (tools/hwtest) fa le sue sessioni dal PC: il PC preme i tasti dell'FM-1 e fa anche da tablet e
da grid. Questo le fa dal Pi, con le strade vere:
  * le pagine SAGGA (Remote, Mutes, Motori, Break, Mod, Live) premute dentro RaspiMIDIHub, con la sua API: il comando
    esce dalla pagina e arriva all'FM-1 dalla matrice, come quando tocchi il tablet;
  * il grid con il bridge vero (sagga_grid_bridge.py, quello installato) e due Launchpad finti: i pad entrano nel bridge,
    il bridge parla con l'FM-1, le luci che l'FM-1 rimanda arrivano al bridge (il servizio del bridge resta fermo
    durante la prova e riparte alla fine);
  * i tasti del pannello e le sonde (tutto lo stato dell'FM-1) con il test dell'FM-1 (SEL sull'FM-1 dice si').
L'FM-1 (SAGGA SEQ 0.20.3 o piu' recente) ascolta le sue porte durante il test e dice al Pi ogni messaggio che ha
sentito, dove: il simulatore poi rifa' la sessione con quei messaggi negli stessi punti.
Prima di tutto controlla la matrice (le celle che servono e quelle che non devono esserci), i servizi, le versioni.
Poi stacca dalla matrice le celle fra l'FM-1 e i synth (o altro che non sia una pagina SAGGA): durante la prova l'FM-1
suona a caso e i synth tacciono; le celle tornano alla fine (anche dopo un'interruzione: la volta dopo, o --rimetti).
Dopo ogni sessione: i valori che l'FM-1 rimanda sono arrivati alle pagine? Il bridge ha tradotto ogni pad giusto?
Alla fine il progetto che l'FM-1 aveva in memoria torna dov'era. Tutto in raccolta-banco-<data>.json (il confronto
con il simulatore: python3 tests/sagga_explore.py --banco raccolta-banco-<data>.json) e RAPPORTO-BANCO-<data>.md.

Con --piano fm1_piano.json fa l'FM-1 completo: le sessioni dell'esploratore dal PC (ogni situazione, 60 gesti, il
tablet e il grid come eventi del test), dal Pi, senza PC. Una mano sull'FM-1 ferma tutto. Serve python3-mido e python3-rtmidi (install_hub.sh li installa)."""
import argparse
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                                   # sagga_testport, sagga_hw_test, sagga_hw_explore (from tools/hwtest)
sys.path.insert(0, os.path.dirname(HERE))                  # /opt/sagga: fm1_install, sagga_grid_bridge
for d in (os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"), os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools", "hwtest")):
    if os.path.isdir(d):                                   # (in the repository)
        sys.path.insert(0, d)
import sagga_testport as T          # noqa: E402
import sagga_hw_test as HT          # noqa: E402
import sagga_hw_explore as X        # noqa: E402
import sagga_grid_bridge as B       # noqa: E402
import sagga_celle as K             # noqa: E402  (0.20.9: the FM-1's cells, RaspiMIDIHub's API, the USB)

PAGES = ("sagga_remote", "sagga_mutes", "sagga_motori", "sagga_break", "sagga_mod", "sagga_live")
PAGE_NAMES = K.PAGE_NAMES
HubAPI = K.HubAPI
is_fm1 = K.is_fm1
GRID_ST = (0x9F, 0x8F, 0xBE)       # what the FM-1 sends the grid (the bridge's lights)
SNAP_MS = 250                      # the grid's lights are read this long after a probe (the FM-1 sends them over a few ms)
CELLS_FILE = "/boot/firmware/sagga/banco/celle-staccate.json"   # the cells taken away, until they are back (a power cut too)


# ------------------------------------------------------------------------------------------------ RaspiMIDIHub's pages
def page_bindings(data):
    """an instance's data (GET /api/plugins/instances/<id>) -> {cell: (channel, cc, kind, on, off)}: the schema's cells
    with the user's own bindings over them (as the hub's ControllerBase does)"""
    out = {}
    params = data.get("params") or {}

    def walk(x):
        if isinstance(x, dict):
            if x.get("type") == "layoutgrid":
                over = params.get(x.get("bindings_param") or "cell_bindings") or {}
                for c in x.get("cells") or []:
                    p = c.get("param") or {}
                    name = p.get("name")
                    if name is None or c.get("cc") is None:
                        continue
                    kind = p.get("type", "")
                    if kind == "button":
                        kind = "trigger" if p.get("trigger") else "button"
                    ch, cc, on, off = c.get("channel"), c.get("cc"), 127, 0
                    ov = over.get(name) if isinstance(over, dict) else None
                    if isinstance(ov, dict):
                        ch = ov["channel"] if isinstance(ov.get("channel"), int) else ch
                        cc = ov["cc"] if isinstance(ov.get("cc"), int) else cc
                        on = ov["on"] if isinstance(ov.get("on"), int) else on
                        off = ov["off"] if isinstance(ov.get("off"), int) else off
                    out[name] = (ch, cc, kind, on, off)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(data.get("params_schema") or [])
    return out


# ------------------------------------------------------------------------------------------------------ the matrix
def audit(api, version_file=None, services=None):
    """the matrix, the pages, the services -> (findings [(level, text)], facts {})"""
    found, facts = [], {}
    try:
        system = api.get("/api/system") or {}
        devices = api.get("/api/devices") or []
        conns = api.get("/api/connections") or []
        insts = api.get("/api/plugins/instances") or []
    except Exception as e:
        return [("ERRORE", "RaspiMIDIHub non risponde sulla sua API (%s): la matrice non si controlla" % e)], facts
    facts["raspimidihub"] = system.get("version")
    if version_file and os.path.isfile(version_file):
        with open(version_file) as f:
            facts["hub"] = f.read().strip()
    if system.get("default_routing") == "all":
        found.append(("DA GUARDARE", "Settings > MIDI > Default routing e' 'Connect all': ogni dispositivo nuovo si collega a "
                                     "tutto. Mettilo su nessuna connessione"))
    by_client = {d.get("client_id"): d for d in devices if d.get("online") and d.get("client_id") is not None}
    fm1 = [d for d in by_client.values() if is_fm1(d.get("name")) or is_fm1(d.get("default_name"))]
    if not fm1:
        found.append(("ERRORE", "nella matrice non c'e' l'FM-1 (Felucca): e' collegato al Pi e acceso?"))
        return found, facts
    fm = fm1[0]
    facts["fm1"] = fm.get("name")
    outs = [p for p in fm.get("ports", []) if p.get("is_output")]
    two = len(outs) >= 2
    facts["porte_fm1"] = 2 if two else 1
    remote_port = outs[1]["port_id"] if two else (outs[0]["port_id"] if outs else 0)
    port1 = outs[0]["port_id"] if outs else 0
    fmc = fm["client_id"]
    if not two:
        found.append(("DA GUARDARE", "l'FM-1 ha una porta USB: con il Pi conviene USB PORTS 2 (SAVE tenuto, OCT+ fino a SAVE 3 SYSTEM, "
                                     "K1 su 2, poi SEL + K1 due volte), cosi' il grid e le pagine stanno sulla porta 2 e i synth sulla 1"))
    pages = {}
    for row in insts:
        if row.get("type") in PAGE_NAMES:
            pages.setdefault(row["type"], row)
    facts["pagine"] = sorted(pages)
    page_client = {}
    for d in by_client.values():
        if d.get("plugin_type") in PAGE_NAMES:
            page_client[d["client_id"]] = d["plugin_type"]
    missing = [PAGE_NAMES[p] for p in PAGES if p not in pages]
    if missing:
        found.append(("VISTO", "pagine non aggiunte nel hub: %s (i loro comandi vanno all'FM-1 diretti, senza passare dal hub)" % ", ".join(missing)))
    edges = {}
    for c in conns:
        if c.get("offline"):
            continue
        edges[(c.get("src_client"), c.get("src_port"), c.get("dst_client"), c.get("dst_port"))] = c
    name_of = lambda cl: (by_client.get(cl) or {}).get("name", "client %s" % cl)
    for cl, typ in page_client.items():
        nm = PAGE_NAMES[typ]
        if typ == "sagga_bsp":
            continue
        if not any(k[0] == cl and k[2] == fmc and k[3] == remote_port for k in edges):
            found.append(("ERRORE", "manca la cella %s -> FM-1 porta %d: i comandi di quella pagina non arrivano all'FM-1"
                                    % (nm, 2 if two else 1)))
        if not any(k[0] == fmc and k[1] == remote_port and k[2] == cl for k in edges):
            found.append(("DA GUARDARE", "manca la cella FM-1 porta %d -> %s: i valori dell'FM-1 non tornano su quella pagina"
                                         % (2 if two else 1, nm)))
    for k, c in edges.items():
        src, dst = by_client.get(k[0]) or {}, by_client.get(k[2]) or {}
        if "launchpad" in (src.get("name", "") + src.get("default_name", "")).lower() or \
                "launchpad" in (dst.get("name", "") + dst.get("default_name", "")).lower():
            found.append(("ERRORE", "il Launchpad ha una cella (%s -> %s): toglila, i Launchpad parlano solo con il bridge" % (
                name_of(k[0]), name_of(k[2]))))
        if two and k[0] == fmc and k[1] == remote_port and k[2] not in page_client and k[2] != fmc:
            found.append(("ERRORE", "la porta 2 dell'FM-1 va a %s: la porta 2 e' del grid e delle pagine, ai synth va la 1" % name_of(k[2])))
        if k[2] == fmc and k[0] not in page_client:
            found.append(("DA GUARDARE", "%s manda MIDI all'FM-1 (porta %d): durante la prova puo' cambiare le cose che l'FM-1 fa"
                                         % (name_of(k[0]), 1 if k[3] == port1 else 2)))
    facts["celle"] = len(edges)
    for svc, (st, want) in (services or {}).items():
        if st != want:
            found.append(("DA GUARDARE", "il servizio %s e' %s" % (svc, st)))
    return found, facts


def services_state(run=None):
    run = run or (lambda cmd: subprocess.run(cmd, capture_output=True, text=True, timeout=10))
    out = {}
    for svc in ("raspimidihub", "sagga-grid-bridge", "sagga-fw"):
        try:
            r = run(["systemctl", "is-active", svc])
            out[svc] = ((r.stdout or "").strip() or "?", "active")
        except Exception as e:
            out[svc] = ("? (%s)" % e, "active")
    return out


# ---------------------------------------------------------------------------------------- the grid's bridge, stopped and back
BRIDGE = "sagga-grid-bridge"
SYSTEM_S = 20                      # how long a systemctl / journalctl may take (the service's TimeoutStopSec is shorter: 15)


def service_is(system, svc=BRIDGE):
    """systemd's word for the service now - active, inactive, failed, deactivating ...; "?" when it cannot be asked"""
    try:
        return ((system(["systemctl", "is-active", svc]).stdout or "").strip() or "?")
    except Exception:
        return "?"


def bridge_stop(system, say, wait=time.sleep):
    """0.32.2: the grid's bridge stopped for the prova -> True when it is not running any more. `systemctl stop` waits
    for the bridge to end by itself, and one that does not end makes it wait: on the Pi, 0.32.1, the bridge locked up
    as it closed the FM-1's port (sagga_grid_bridge.py, the way out), systemctl was still waiting after this program's
    20 s, and the prova ended there with a Python error, the bridge stopped for good and the grid dark until the Pi
    was started again. Now: a stop that does not come back, or a bridge still there after it, is ended by the kernel
    (systemctl kill -s KILL: nothing can refuse that), and the prova goes on"""
    try:
        system(["systemctl", "stop", BRIDGE])
    except Exception as e:
        say("il bridge del grid non si ferma da solo (%s): lo chiudo io" % type(e).__name__)
    st = "?"
    for k in range(12):
        st = service_is(system)
        if st in ("inactive", "failed"):
            return True
        if st != "?" and k in (0, 6):                    # (still active, or deactivating: systemd is waiting for it)
            try:
                system(["systemctl", "kill", "-s", "KILL", BRIDGE])
            except Exception:
                pass
        wait(0.5)
    return st == "?"                                     # (systemctl cannot be asked: as before 0.32.2, the prova goes on)


def bridge_start(system, say):
    """... and started again; never an error of this program's (it runs in the last lines of a prova, after everything)"""
    try:
        system(["systemctl", "start", BRIDGE])
        say("il bridge del grid riparte")
        return True
    except Exception as e:
        say("il bridge del grid NON riparte (%s: %s): premi Controlla la matrice, che lo fa ripartire" % (type(e).__name__, e))
        return False


def bridge_revive(system, wait=time.sleep):
    """0.32.2: a bridge that should be running and is not - failed (it did not end when it was stopped and systemd
    killed it: systemd does not start such a one again by itself), or stopped while its service is enabled (a prova that
    was cut before its last lines) - is started again. No prova is running when this is asked (the page starts one at a
    time), so nobody stopped it on purpose. Until 0.32.1 the page only said "il servizio sagga-grid-bridge e' failed",
    and the grid stayed dark until the Pi was started again. -> what to say, or None (it runs, or it is not wanted)"""
    st = service_is(system)
    if st not in ("failed", "inactive"):
        return None
    if st == "inactive":
        try:
            if (system(["systemctl", "is-enabled", BRIDGE]).stdout or "").strip() != "enabled":
                return None
        except Exception:
            return None
    try:
        system(["systemctl", "start", BRIDGE])
    except Exception as e:
        return "Il bridge del grid era fermo (%s) e non riparte (%s: %s): riavvia il Pi." % (st, type(e).__name__, e)
    wait(3.0)
    now = service_is(system)
    if now == "active":
        return "Il bridge del grid era fermo (%s): l'ho fatto ripartire, il grid torna." % st
    return "Il bridge del grid era fermo (%s) e non riparte (ora e' %s): riavvia il Pi." % (st, now)


# ---------------------------------------------------------------------------------------- the synths, away and back
def keep_file(path, data):
    """the cells' file where a power cut does not take it: /boot/firmware is read-only, sagga_fw's BootWriter opens it"""
    try:
        import sagga_fw
        w = sagga_fw.BootWriter(os.path.dirname(path))
        if data is None:
            if os.path.exists(path):
                w.remove(path)
        else:
            w.write(path, data)
        return
    except ImportError:
        pass
    if data is None:
        if os.path.exists(path):
            os.unlink(path)
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)


def fm1_cells(api):
    """the matrix's cells between the FM-1 and anything that is not a SAGGA page -> ([cell], the FM-1's device) where a
    cell says both ends by their stable ids too (the FM-1's ALSA number may change at each reboot)"""
    devices = api.get("/api/devices") or []
    conns = api.get("/api/connections") or []
    by = {d.get("client_id"): d for d in devices if d.get("online") and d.get("client_id") is not None}
    fm = [d for d in by.values() if is_fm1(d.get("name")) or is_fm1(d.get("default_name"))]
    if not fm:
        return [], None
    fmc = fm[0]["client_id"]
    pages = {cid for cid, d in by.items() if d.get("plugin_type") in PAGE_NAMES}
    out = []
    for c in conns:
        if c.get("offline") or c.get("src_client") is None:
            continue
        src, dst = c["src_client"], c["dst_client"]
        if (src == fmc and dst not in pages and dst != fmc) or (dst == fmc and src not in pages and src != fmc):
            other = by.get(dst if src == fmc else src) or {}
            out.append({"id": c.get("id") or "%d:%d-%d:%d" % (src, c["src_port"], dst, c["dst_port"]),
                        "fm1_src": src == fmc, "fm1_port": c["src_port"] if src == fmc else c["dst_port"],
                        "other_port": c["dst_port"] if src == fmc else c["src_port"],
                        "other": other.get("stable_id"), "other_name": other.get("name", "?"),
                        "filtro": bool(c.get("filtered"))})
    return out, fm[0]


cell_key = K.cell_key


def detach(api, saved, say, path):
    """every cell between the FM-1 and the synths away (the ones a reboot of the FM-1 brought back too); saved: the
    list kept so far (the ones taken away are added, the file rewritten)"""
    try:
        cells, _ = fm1_cells(api)
    except Exception as e:
        say("  (la matrice non risponde: %s; le celle restano)" % e)
        return saved
    known = {cell_key(c) for c in saved}
    new = 0
    for c in cells:
        try:
            api.delete("/api/connections/%s" % c["id"])
        except Exception as e:
            say("  (la cella FM-1 %s %s non si stacca: %s)" % ("->" if c["fm1_src"] else "<-", c["other_name"], e))
            continue
        if cell_key(c) not in known:
            saved.append(c)
            known.add(cell_key(c))
            new += 1
    if new:
        keep_file(path, json.dumps({"celle": saved, "quando": time.strftime("%Y-%m-%d %H:%M")}, indent=1).encode())
    return saved


def reattach(api, saved, say):
    """the cells back -> the ones that would not come back"""
    try:
        devices = api.get("/api/devices") or []
        conns = api.get("/api/connections") or []
    except Exception as e:
        say("  la matrice non risponde (%s): le celle restano da rimettere" % e)
        return list(saved)
    by = {d.get("client_id"): d for d in devices if d.get("online") and d.get("client_id") is not None}
    fm = [d for d in by.values() if is_fm1(d.get("name")) or is_fm1(d.get("default_name"))]
    if not fm:
        say("  l'FM-1 non e' nella matrice: le celle restano da rimettere (collegalo e premi Rimetti le celle)")
        return list(saved)
    fmc = fm[0]["client_id"]
    have = {(c.get("src_client"), c.get("src_port"), c.get("dst_client"), c.get("dst_port")) for c in conns if not c.get("offline")}
    left = []
    for c in saved:
        oc = next((cid for cid, d in by.items() if c["other"] and d.get("stable_id") == c["other"]), None)
        if oc is None:
            oc = next((cid for cid, d in by.items() if d.get("name") == c["other_name"]), None)
        if oc is None:
            say("  %s non c'e' adesso: la sua cella resta da rimettere" % c["other_name"])
            left.append(c)
            continue
        edge = (fmc, c["fm1_port"], oc, c["other_port"]) if c["fm1_src"] else (oc, c["other_port"], fmc, c["fm1_port"])
        if edge not in have:
            try:
                api.post("/api/connections", {"src_client": edge[0], "src_port": edge[1], "dst_client": edge[2], "dst_port": edge[3]})
            except Exception as e:
                say("  la cella FM-1 %s %s non torna: %s" % ("->" if c["fm1_src"] else "<-", c["other_name"], e))
                left.append(c)
                continue
        if c.get("filtro"):
            say("  la cella FM-1 %s %s aveva un filtro: guarda nella matrice che ci sia ancora" % ("->" if c["fm1_src"] else "<-", c["other_name"]))
    return left


def load_cells(path):
    try:
        with open(path) as f:
            return (json.load(f) or {}).get("celle") or []
    except (OSError, ValueError):
        return []


def put_back(api, path, say):
    """the cells of the file back; the file away when all are -> how many are left"""
    saved = load_cells(path)
    if not saved:
        return 0
    say("Le celle staccate per la prova tornano nella matrice (%d)" % len(saved))
    left = reattach(api, saved, say)
    if left:
        keep_file(path, json.dumps({"celle": left, "quando": time.strftime("%Y-%m-%d %H:%M")}, indent=1).encode())
    else:
        keep_file(path, None)
        say("  tutte a posto")
    return len(left)


# ------------------------------------------------------------------------------------------------- the real paths
class Pages:
    """presses the SAGGA pages inside RaspiMIDIHub (PATCH params, as the tablet does), in a thread of its own: the
    HTTP call takes some ms, the session goes on. What each press sent is noted with its time"""
    def __init__(self, api, clock, direct):
        self.api, self.clock, self.direct = api, clock, direct
        self.q = queue.Queue()
        self.done = []                    # [t_ms, "pagina"/"diretto", [st, d1, d2], plugin, cell, value, ms of the call]
        self.inst, self.lock = {}, threading.Lock()
        self.own = {}                     # (page, cell) -> (its binding, the user's) where the user bound it otherwise
        self.errors = []
        self._run = True
        self.th = threading.Thread(target=self._work, daemon=True)
        self.th.start()

    def find(self):
        """the instances of the pages, by type, and the cells the user bound otherwise (cell_bindings): what those send"""
        try:
            for row in self.api.get("/api/plugins/instances") or []:
                if row.get("type") in PAGE_NAMES and row.get("status", "running") == "running":
                    self.inst.setdefault(row["type"], row["id"])
            for typ, iid in self.inst.items():
                data = self.api.get("/api/plugins/instances/%s" % iid) or {}
                mine = page_bindings(data)
                plain = page_bindings(dict(data, params=dict(data.get("params") or {}, cell_bindings={})))
                for cell, b in mine.items():
                    if plain.get(cell) != b:
                        self.own[(typ, cell)] = (plain.get(cell), b)
        except Exception as e:
            self.errors.append("le pagine del hub: %s" % e)
        return dict(self.inst)

    def proprie(self):
        return ["%s %s: canale %d CC %d (on %d, off %d) invece di canale %d CC %d" % (
            PAGE_NAMES.get(t, t), c, b[0] + 1, b[1], b[3], b[4], a[0] + 1 if a else 0, a[1] if a else 0)
            for (t, c), (a, b) in sorted(self.own.items()) if a]

    def press(self, plugin, cell, value, msgs):
        own = self.own.get((plugin, cell))
        if own and own[0]:                               # (the user's binding: what the page really sends)
            (ch0, cc0, _, on0, off0), (ch, cc, _, on, off) = own
            out = []
            for m in msgs:
                if (m[0] & 0xF0) == 0xB0 and (m[0] & 15) == ch0 and m[1] == cc0:
                    v = on if m[2] == on0 else (off if m[2] == off0 else m[2])
                    out.append((0xB0 | ch, cc, v))
                else:
                    out.append(tuple(m))
            msgs = out
        self.q.put((plugin, cell, value, msgs))

    def _work(self):
        while self._run:
            try:
                plugin, cell, value, msgs = self.q.get(timeout=0.2)
            except queue.Empty:
                continue
            iid = self.inst.get(plugin)
            if iid is None:                                  # no such page in the hub: straight to the FM-1
                t = self.clock()
                for m in msgs:
                    self.direct(m)
                with self.lock:
                    for m in msgs:
                        self.done.append([round(t, 1), "diretto", list(m), plugin, cell, value, 0])
                continue
            t0 = self.clock()
            ok = True
            try:
                self.api.patch("/api/plugins/instances/%s" % iid, {"params": {cell: value}})
            except Exception as e:
                ok = False
                self.errors.append("%s %s=%s: %s" % (PAGE_NAMES.get(plugin, plugin), cell, value, e))
            t1 = self.clock()
            if ok:
                with self.lock:
                    for m in msgs:                           # (the page sends while the call is being answered)
                        self.done.append([round((t0 + t1) / 2, 1), "pagina", list(m), plugin, cell, value, round(t1 - t0, 1)])

    def idle(self, timeout=3.0):
        end = time.perf_counter() + timeout
        while not self.q.empty() and time.perf_counter() < end:
            time.sleep(0.01)
        time.sleep(0.05)

    def take(self):
        with self.lock:
            d, self.done = self.done, []
        return d

    def stop(self):
        self._run = False


def lp_message(fm_msg):
    """the FM-1 message a grid press must become -> (Launchpad 0/1, the MK3 Launchpad's message), as the bridge
    (upright, not swapped) reads them back"""
    st, d1, d2 = fm_msg
    if st in (0x9F, 0x8F):
        x, y = d1 & 15, d1 >> 4
        side = x >> 3
        led = B.MK3.pad_led(x & 7, y)
        return side, [0x90 if st == 0x9F and d2 else 0x80, led, d2 if st == 0x9F else 0]
    if st == 0xBE:
        ident = d1
        side = (ident >> 3) & 1
        j = ident & 7
        led = B.MK3.top_led(j) if ident < 16 else B.MK3.side_led(j)
        return side, [0xB0, led, 127 if d2 >= 64 else 0]
    return None, None


class Grid:
    """the bridge as installed, with two Launchpads of ours: what it sends to the FM-1 (with the time) is kept"""
    def __init__(self, send_fm1, clock):
        self.clock, self._send = clock, send_fm1
        self.sent = []                    # [t_ms, [st, d1, d2]]
        self.lp_out = {0: 0, 1: 0}
        self.started = False
        self.wrong = []                   # a press the bridge did not turn into the FM-1 message the plan says
        self.fed = 0                      # the FM-1's messages for the lights the bridge has had
        self.b = B.Bridge(self._lp, self._fm, model="mk3")

    def _lp(self, idx, msg):
        self.lp_out[idx] += 1

    def _fm(self, msg):
        self.sent.append([round(self.clock(), 1), list(msg)])
        self._send(bytes(msg))

    def start(self):
        self.b.start(time.perf_counter())
        self.started = True

    def press(self, fm_msg):
        side, lp = lp_message(fm_msg)
        if lp is None:
            return
        n = len(self.sent)
        self.b.lp_in(side, lp, now=time.perf_counter())
        got = [m for _, m in self.sent[n:]]
        want = [0x9F if fm_msg[0] in (0x9F, 0x8F) else fm_msg[0], fm_msg[1], fm_msg[2] if fm_msg[0] == 0x9F else 0]
        if fm_msg[0] == 0xBE:
            want = [0xBE, fm_msg[1], 127 if fm_msg[2] >= 64 else 0]
        if got != [want]:
            self.wrong.append({"piano": list(fm_msg), "launchpad": [side] + lp, "bridge": got})

    def from_fm1(self, msg):
        if len(msg) == 3 and msg[0] in GRID_ST:
            self.b.fm1_in(list(msg))
            self.fed += 1

    def tick(self):
        if self.started:
            self.b.tick(time.perf_counter())

    def roles(self):
        return sorted([idx, led, r] for (idx, led), r in self.b.role.items() if r)

    def stop(self):
        if self.started:
            self.b.stop()


# ------------------------------------------------------------------------------------------------------ a session
# 0.20.6: four cells the FM-1 sends back on channel 12 CC 33-36 (their own CC is part of an RPN / NRPN in MIDI 2.0)
ECHO_BACK = {("sagga_live", "swing"): (11, 33), ("sagga_remote", "quant"): (11, 34), ("sagga_motori", "p5"): (11, 35),
             ("sagga_mod", "lane0"): (11, 36)}


def values_back(api, insts, feedback, when=None, pressed=None):
    """the values the FM-1 sent back (CC on its remote port; the LFO switches as notes) -> did each page's cell take
    it? ([(page, cell, the FM-1's value, the page's value)] for the ones that did not, how many were looked at, and
    0.32.1 the same rows for the cells the Pi pressed AFTER the FM-1's last word on them).
    0.32.1 when: {the feedback's key: the ms the FM-1 said it last}; pressed: {(page type, cell): the ms the Pi pressed
    it last}. A cell is compared only when the FM-1 spoke last: a value the Pi pressed afterwards is on the page, and
    whether the FM-1 took it is not something a value from before can say - the banco of 0.32 called two such cells
    wrong (a grid pad had switched the REMOTE off: the FM-1 hears no page then, and says nothing back; a SEED on a
    pattern that has none: the FM-1 has nothing to show there)"""
    wrong, checked, later = [], 0, []
    for typ, iid in insts.items():
        try:
            data = api.get("/api/plugins/instances/%s" % iid) or {}
        except Exception:
            continue
        params = data.get("params") or {}
        for cell, (ch, cc, kind, on, off) in page_bindings(data).items():
            key = ("cc", ch, cc)
            v = feedback.get(key)
            if typ == "sagga_mod" and cell.startswith("lfo_sw"):
                key = ("note", 12, 100 + int(cell[6:]))
                v = feedback.get(key)
                if v is None:
                    continue
                want, have = bool(v), bool(params.get(cell))
            else:
                if (typ, cell) in ECHO_BACK:
                    e = feedback.get(("cc",) + ECHO_BACK[(typ, cell)])
                    if e is not None:
                        v, key = e, ("cc",) + ECHO_BACK[(typ, cell)]
                if v is None:
                    continue
                if kind in ("button", "trigger"):
                    if kind == "trigger":
                        continue                     # (a trigger lets go by itself)
                    want, have = abs(v - on) < abs(v - off), bool(params.get(cell))
                else:
                    want, have = v, params.get(cell)
            row = [PAGE_NAMES.get(typ, typ), cell, want, have]
            t_fm1, t_pi = (when or {}).get(key), (pressed or {}).get((typ, cell))
            if t_fm1 is not None and t_pi is not None and t_pi > t_fm1:
                if want != have:
                    later.append(row)                # (the Pi had the last word: nothing to compare it with)
                continue
            checked += 1
            if want != have:
                wrong.append(row)
    return wrong, checked, later


def pressed_last(done):
    """0.32.1: {(page type, cell): the ms of the last press} from what the Pi did on the pages (Pages.take's rows)"""
    out = {}
    for r in done or []:
        if len(r) >= 5 and r[1] == "pagina":            # (r[0]: the middle of the hub's call, r[6]: how long it took -
            t = r[0] + (r[6] if len(r) > 6 else 0) / 2.0  #  its end: what the FM-1 said while it ran is not "after")
            out[(r[3], r[4])] = max(out.get((r[3], r[4]), 0), t)
    return out


def take_tagged(hub):
    """what came in from every port of the FM-1, in order: (t, data, from the remote's port?) - the remote's port is the
    one the test answers on (port 2 with two, else the only one)"""
    out = []
    for p in hub.ports:
        for t, d in p.take():
            out.append((t, d, p is hub.ctl))
    out.sort(key=lambda x: x[0])
    return out


def run_session(hub, sess, pages, grid, say, clock_box, conti=None):
    """one session: the panel and the probes through the FM-1's test, the pages through the hub, the grid through the
    bridge -> its record (the Windows runner's, plus reali, luci, ponte). conti (0.23.1, an FM-1 that counts what it
    sends): {"alsa": a function that reads the Pi's driver counts, or None} - the session's account goes in conti"""
    events = [tuple(e) for e in sess["eventi"]]
    reali = sorted((list(r) for r in sess.get("reali", [])), key=lambda r: r[1])
    probes_at = [i for i, e in enumerate(events) if e[1] == T.PROBE]
    two = len(hub.ports) > 1                             # (the FM-1 with USB PORTS 2: hub.ctl is its port 2)
    rec = {"go_ms": None, "presi": {}, "sonde": {}, "midi": [], "done": None, "abort": None, "errore": None,
           "rimandati": 0, "di_nuovo": 0, "luci": {}, "feedback": {}}
    hub.take()
    mark = X.counts_begin(hub, conti.get("alsa")) if conti is not None else None
    hub.send(T.go(listen=True))                         # (0.20.3: the FM-1 hears its ports too, and says where)
    go = hub.wait("go", 2.0)
    if go is None:
        rec["errore"] = "l'FM-1 non ha risposto a GO"
        return rec
    rec["go_ms"] = go
    t_go = time.perf_counter()
    clock_box[0] = t_go
    pacer, free, pending = T.Pacer(events), T.QUEUE, None
    pr = T.Probes()
    heard = T.Heard()
    asked = {}
    t_done, last_rx = None, time.perf_counter()
    nreal = 0
    snaps = [(events[i][0] + SNAP_MS, i) for i in probes_at]
    feedback, feedback_t = {}, {}
    while True:
        now = time.perf_counter()
        rel = (now - t_go) * 1000.0
        # the real paths, when due
        while nreal < len(reali) and reali[nreal][1] <= rel:
            r = reali[nreal]
            nreal += 1
            if r[0] == "pagina":
                pages.press(r[2], r[3], r[4], [tuple(m) for m in r[5]])
            elif r[0] == "grid":
                grid.press(tuple(r[2]))
            elif r[0] == "grid_start":
                grid.start()
            elif r[0] == "diretto":
                pages.direct(bytes(r[2]))
                with pages.lock:
                    pages.done.append([round(rel, 1), "diretto", list(r[2]), "", "", 0, 0])
        grid.tick()
        while snaps and snaps[0][0] <= rel:
            t_s, i = snaps.pop(0)
            rec["luci"][str(i)] = {"t": round(rel, 1), "n": grid.fed, "ruoli": grid.roles()}
        for t, d, remote in take_tagged(hub):
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
                elif k == "heard":
                    heard.add(*v)
                continue
            # (0.20.4: the grid's lights and the values for the pages only from the remote's port - port 2 with two: on
            #  port 1 channel 16 is a track and CC 64 the STOP's sustain off for the synths)
            if remote and len(d) == 3 and d[0] in GRID_ST:
                grid.from_fm1(d)
            if remote and len(d) == 3 and (d[0] & 0xF0) == 0xB0 and (d[0] & 15) in (11, 12, 13):
                feedback["cc %d %d" % (d[0] & 15, d[1])] = d[2]
                feedback_t["cc %d %d" % (d[0] & 15, d[1])] = round((t - t_go) * 1000.0, 1)   # (0.32.1: and when)
            elif remote and len(d) == 3 and (d[0] & 0xF0) in (0x80, 0x90) and (d[0] & 15) == 12 and 100 <= d[1] < 116:
                feedback["note %d %d" % (12, d[1])] = d[2] if (d[0] & 0xF0) == 0x90 else 0
                feedback_t["note %d %d" % (12, d[1])] = round((t - t_go) * 1000.0, 1)
            if (d[0] & 0xF0) in X.MIDI_KEEP or d[0] in (0xF8, 0xFA, 0xFB, 0xFC):
                rec["midi"].append([round((t - t_go) * 1000.0, 1)] + list(d[:3]) + [0] * (3 - len(d[:3])) + [2 if remote and two else 1])
        if rec["abort"] is not None:
            break
        try:
            if pending is None and rec["done"] is None:
                f = pacer.next_frame(rel, free)
                if f:
                    hub.send(f[0])
                    pending = (f[0], f[1], f[2], now, 0)
            elif pending is not None and now - pending[3] > 1.0:
                if pending[4] >= 5:
                    rec["errore"] = "l'FM-1 non accetta piu' gli eventi (all'evento %d)" % pending[1]
                    break
                hub.send(pending[0])
                pending = pending[:3] + (now, pending[4] + 1)
                rec["rimandati"] += 1
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
                    s0 = missing[0]
                    while s0 <= missing[-1]:
                        hub.send(T.taken(s0, 120))
                        s0 += 120
                whole = all(i in pr.done for i in probes_at if i < n)
                if (whole and not missing and not snaps) or now - t_done > 4.0:
                    break
        except Exception as e:
            rec["errore"] = "l'FM-1 e' sparito dall'USB (%s)" % e
            break
        if now - last_rx > 6.0 and rel > 2000:
            rec["errore"] = "l'FM-1 non manda niente da 6 s (all'evento %d di %d)" % (len(rec["presi"]), len(events))
            break
        time.sleep(0.002)
    rec.pop("_taken_asked", None)
    pages.idle()
    if mark and not rec["errore"] and rec["abort"] is None:
        rec["conti"] = X.counts_end(hub, mark, conti.get("alsa"))
    rec["sonde"] = {str(k): v for k, v in pr.done.items()}
    rec["sentiti"] = heard.rows()
    rec["reali_fatti"] = pages.take() + [[t, "grid", m] for t, m in grid.sent]
    rec["reali_fatti"].sort(key=lambda r: r[0])
    rec["ponte"] = grid.wrong
    rec["feedback"] = feedback
    rec["feedback_t"] = feedback_t
    return rec


def fb_keys(feedback):
    out = {}
    for k, v in feedback.items():
        kind, ch, n = k.split()
        out[(kind, int(ch), int(n))] = v
    return out


def fm1_now(api):
    """the matrix now -> (the online devices by client, the cells, the FM-1's device or None)"""
    by = K.online_by_client(api.get("/api/devices"))
    return by, api.get("/api/connections") or [], K.fm1_of(by)


def keep_cells(api, keep, say, timeout=8.0, wait=time.sleep):
    """0.20.9: after a reboot of the FM-1, the cells it had (the pages', and the synths' when they are not taken away)
    are back: RaspiMIDIHub's own restore first; the ones it lost (its autosave while the FM-1 was away) put back by the
    Pi, as they were -> {"mancavano": n, "rimesse": n, "non_tornano": [text]}"""
    end = time.perf_counter() + 20.0                    # (RaspiMIDIHub sees the FM-1 again: up to 20 s)
    by, conns, fm, missing = {}, [], None, list(keep)
    while keep:
        try:
            by, conns, fm = fm1_now(api)
        except Exception:
            by, conns, fm = {}, [], None
        if fm is not None:
            end = min(end, time.perf_counter() + timeout)  # (then its own restore: `timeout` s)
            have = {K.cell_key(c) for c in K.describe(conns, by, fm)}
            missing = [c for c in keep if K.cell_key(c) not in have]
            if not missing:
                break
        if time.perf_counter() >= end:
            break
        wait(0.5)
    out = {"mancavano": len(missing) if keep else 0, "rimesse": 0, "non_tornano": []}
    if not keep or not missing:
        return out
    if fm is None:
        out["non_tornano"] = ["l'FM-1 non e' nella matrice"]
        say("  (l'FM-1 non e' nella matrice di RaspiMIDIHub: le sue %d celle restano da rimettere)" % len(missing))
        return out
    done = []
    for c in missing:
        err = K.make(api, by, fm, c)
        if err:
            out["non_tornano"].append("%s: %s" % (K.arrow(c), err))
        else:
            done.append(c)
    out["rimesse"] = len(done)
    if done:
        say("  (RaspiMIDIHub aveva perso %d celle dell'FM-1 nel riavvio: rimesse dal Pi)" % len(done))
    for t in out["non_tornano"][:3]:
        say("  (la cella %s)" % t)
    return out


def kernel_lines(system, since, limit=30):
    """0.20.9: what the kernel said about the USB since `since` (time.time()): the FM-1 going and coming back, an
    error - for the log (when the FM-1 takes long to answer after a reboot, this says whether the Pi saw it go)"""
    try:
        r = system(["journalctl", "-k", "--no-pager", "-o", "short-monotonic", "-S", "@%d" % max(0, int(since) - 1)])
        text = r.stdout or ""
    except Exception:
        return []
    return [ln.strip() for ln in text.splitlines() if re.search(r"usb|snd|felucca|fm-1|midi", ln, re.I)][-limit:]


def bridge_lines(system, limit=25, since=None):
    """0.23.2: the grid bridge's own last lines (its journal; since `since`, time.time(), when given): the ports it
    took, whether it waits for the FM-1 or runs without the Launchpads, why it ended. In the log because the bridge's
    ways of 0.23.2 (it waits without looking at the ports, it watches its own connections) have run on no real Pi:
    the file one sends after a run is their only witness"""
    cmd = ["journalctl", "-u", "sagga-grid-bridge", "--no-pager", "-o", "short-monotonic"]
    cmd += ["-S", "@%d" % max(0, int(since) - 1)] if since is not None else ["-n", str(limit)]
    try:
        r = system(cmd)
        text = r.stdout or ""
    except Exception:
        return []
    return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("-- ")][-limit:]


def ask_diag(hub, hello):
    """0.20.9: the FM-1's counters since its boot (the HELLOs it heard, the host's enumeration) - None before 0.20.9"""
    if hub is None or not hello or X.vkey(hello.get("version")) < (0, 20, 9):
        return None
    try:
        hub.take()
        hub.send(T.diag())
        return hub.wait("diag", 1.5)
    except Exception:
        return None


FIRST_WAIT, MORE_WAIT = 12.0, 30.0   # s: the FM-1 after a reboot; then again after the USB found again


def reconnect(backend, say, system, since, sysfs=K.SYSFS_USB, wait=time.sleep):
    """0.20.9: the FM-1 after a BOOT or a CLOSE -> (hub, hello, what happened). 12 s without an answer: the Pi has the
    host find it again at the USB (as unplugged and plugged back: the 0.20.8 banco stopped at its 4th reboot, the FM-1
    there and deaf for 40 s), then 30 s more. The kernel's USB lines and the FM-1's counters go in the log"""
    t0 = time.perf_counter()
    hub, hello = X.connect(backend, None, say, timeout=FIRST_WAIT, quiet=True)
    info = {}
    if hub is None:
        path = K.fm1_usb_path(sysfs)
        info["kernel_prima"] = kernel_lines(system, since)   # (what the kernel had seen before the Pi stepped in)
        how = X.timed(lambda: K.usb_reenumerate(path, sysfs, wait=wait), 25.0, "finding the FM-1 again at the USB") if path else None
        if how:
            say("  (l'FM-1 non risponde da %.0f s dopo il riavvio: il Pi lo fa ritrovare all'USB, come staccato e riattaccato)" % FIRST_WAIT)
            info["usb_di_nuovo"] = [path, how]
            wait(2.0)
        hub, hello = X.connect(backend, None, say, timeout=MORE_WAIT, quiet=True)
    info["s"] = round(time.perf_counter() - t0, 1)
    info["kernel"] = kernel_lines(system, since)
    d = ask_diag(hub, hello)
    if d:
        info["diag"] = d
    for ln in info["kernel"]:
        X.note("kernel: " + ln)
    if d:
        X.note("DIAG: %s" % d)
    if hub is not None and (info["s"] > 9 or "usb_di_nuovo" in info):
        say("  (l'FM-1 ha risposto dopo %.0f s%s)" % (info["s"], "; dal suo avvio: %d HELLO sentiti, %d risposte non partite, il Pi "
                                                     "l'ha configurato %d volte (l'ultima a %d ms), il suo giro fermo al piu' %d ms"
                                                     % (d["hellos"], d["unsent"], d["configs"], d["cfg_ms"], d["gap_max"]) if d else ""))
    return hub, hello, info


def wait_for_hub(api, timeout=20.0, need_pages=True):
    """after the FM-1's reboot: RaspiMIDIHub sees it again and its cells are back (it restores them by itself)"""
    end = time.perf_counter() + timeout
    while time.perf_counter() < end:
        try:
            devs = api.get("/api/devices") or []
            fm = [d for d in devs if d.get("online") and (is_fm1(d.get("name")) or is_fm1(d.get("default_name")))]
            if fm:
                if not need_pages:
                    return True
                fmc = fm[0]["client_id"]
                conns = api.get("/api/connections") or []
                pc = {d["client_id"] for d in devs if d.get("online") and d.get("plugin_type") in PAGES}
                if not pc or any(c.get("dst_client") == fmc and c.get("src_client") in pc for c in conns):
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


# ---------------------------------------------------------------------------------------------------------- the run
def report_md(path, audit_f, facts, rows, out_json):
    lines = ["# L'esploratore del banco" + ("" if facts.get("piano", "banco") == "banco" else ": l'FM-1 completo"), "", "%s. FM-1: %s. Hub: %s, RaspiMIDIHub %s." % (
        time.strftime("%Y-%m-%d %H:%M"), facts.get("fm1_version", "?"), facts.get("hub", "?"), facts.get("raspimidihub", "?")), ""]
    lines += ["## La matrice", ""]
    if audit_f:
        lines += ["* **%s**: %s" % x for x in audit_f]
    else:
        lines.append("Tutto a posto: le pagine vanno all'FM-1 e tornano, i Launchpad non hanno celle, la porta 2 non va ai synth.")
    if facts.get("bridge_ripartito"):                   # 0.32.2
        lines += ["", facts["bridge_ripartito"]]
    lines += ["", "## Le sessioni", ""]
    if rows:
        lines += ["| sessione | sonde | per le pagine | per il grid | diretti | subito |", "| --- | --- | --- | --- | --- | --- |"]
        lines += ["| %s | %s | %s | %s | %s | %s |" % r for r in rows]
        lines += ["", "Il confronto completo con il simulatore (lo fa Claude, o in WSL): "
                  "`python3 tests/sagga_explore.py --banco %s`" % os.path.basename(out_json)]
    else:
        lines.append("Nessuna sessione fatta.")
    if facts.get("celle_rimesse"):
        lines += ["", "RaspiMIDIHub ha perso %d celle dell'FM-1 nei riavvii (il suo salvataggio automatico mentre l'FM-1 non "
                  "c'era): il Pi le ha rimesse." % facts["celle_rimesse"]]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def main(argv=None, backend=None, api=None, system=None, wait=time.sleep, sysfs=K.SYSFS_USB, control=None):
    ap = argparse.ArgumentParser(description="SAGGA HUB: l'esploratore del banco")
    ap.add_argument("--piano", default=os.path.join(HERE, "banco_piano.json"), help="il piano: banco_piano.json (il banco), "
                    "fm1_piano.json (l'FM-1 completo: ogni situazione, come l'esploratore dal PC)")
    ap.add_argument("--sessioni", type=int, default=0, help="solo le prime N sessioni")
    ap.add_argument("--out", default="/run/sagga-banco")
    ap.add_argument("--solo-matrice", action="store_true", help="solo il controllo della matrice (nessun test sull'FM-1)")
    ap.add_argument("--hub", default="http://127.0.0.1", help="l'indirizzo di RaspiMIDIHub")
    ap.add_argument("--non-staccare", action="store_true", help="lascia le celle fra l'FM-1 e i synth (i synth suonano "
                    "durante la prova, e quello che mandano all'FM-1 entra nella prova)")
    ap.add_argument("--rimetti", action="store_true", help="solo: rimette le celle staccate da una prova interrotta")
    ap.add_argument("--celle", default=CELLS_FILE, help=argparse.SUPPRESS)
    ap.add_argument("--progetti", default=None, help="la libreria dei progetti del hub (il progetto di prima della prova ci "
                    "va, se l'FM-1 non torna per riprenderlo; di solito la cartella sopra quella delle celle)")
    a = ap.parse_args(argv)
    a.progetti = a.progetti or os.path.dirname(os.path.dirname(os.path.abspath(a.celle)))
    api = api or HubAPI(a.hub)
    system = system or (lambda cmd: subprocess.run(cmd, capture_output=True, text=True, timeout=SYSTEM_S))
    os.makedirs(a.out, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    status = os.path.join(a.out, "banco.json")
    T.save(status, {"pid": os.getpid(), "started": time.time(), "rc": None, "quando": ts,
                    "modo": "rimetti" if a.rimetti else "matrice" if a.solo_matrice else "prova",
                    "piano": "fm1" if os.path.basename(a.piano).startswith("fm1") else "banco"})
    rep = HT.Report(os.path.join(a.out, "banco-%s.log" % ts))
    say = rep.say
    X.NOTE[0] = rep.f

    def finish(rc):
        rep.close()
        try:
            st = T.load(status)
        except (OSError, ValueError):
            st = {}
        st["rc"] = rc
        T.save(status, st)
        return rc
    left = put_back(api, a.celle, say)                  # (a prova that ended without putting them back)
    if a.rimetti:
        if not left and not load_cells(a.celle):
            say("Nessuna cella da rimettere.")
        return finish(1 if left else 0)
    revived = bridge_revive(system, wait)               # 0.32.2: a bridge that should be running and is not: started
    audit_f, facts = audit(api, version_file=os.path.join(HERE, "VERSION"), services=services_state(system))
    say("LA MATRICE")
    for lv, txt in audit_f:
        say("  %s: %s" % (lv, txt))
    if not audit_f:
        say("  tutto a posto")
    if revived:
        say(revived)
        facts["bridge_ripartito"] = revived
    bl = bridge_lines(system)                           # 0.23.2
    if bl:
        say("IL BRIDGE DEL GRID (le sue ultime righe)")
        for ln in bl:
            say("  " + ln)
    out_json = os.path.join(a.out, "raccolta-banco-%s.json" % ts)
    out_md = os.path.join(a.out, "RAPPORTO-BANCO-%s.md" % ts)
    if a.solo_matrice:
        report_md(out_md, audit_f, facts, [], out_json)
        say("Rapporto: %s" % out_md)
        return finish(1 if any(lv == "ERRORE" for lv, _ in audit_f) else 0)
    plan = T.load(a.piano)
    facts["piano"] = "banco" if plan.get("banco") else "fm1"            # (the whole FM-1's plan: no real roads, the PC's)
    sessions = plan["sessioni"][:a.sessioni] if a.sessioni else plan["sessioni"]
    minutes = (sum(s["eventi"][-1][0] for s in sessions) / 1000.0 + 10 * len(sessions)) / 60.0
    say("")
    say("LE SESSIONI: %d, circa %.0f minuti (%s)" % (len(sessions), minutes + 1, "il banco: pagine, grid e pannello" if plan.get("banco")
                                                     else "l'FM-1 completo: ogni situazione, il pannello, il tablet e il grid come eventi del test"))
    backend = backend or X.default_backend()
    bridge_was = (services_state(system).get("sagga-grid-bridge") or ("?",))[0] == "active"
    bridge_stopped = False                              # (only after the yes: stopped, the bridge lets the grid go and the
    hub, hello = X.connect(backend, None, say)          #  FM-1's GRID LOST would cover its question on the screen)
    rc = 0
    out = {"versione": 1, "firmware": plan.get("firmware"), "seme": plan.get("seme"), "audit": audit_f, "fatti": facts,
           "quando": ts, "sessioni": []}
    backup, rebooted, rows = None, False, []
    cells, keep = [], []
    clock_box = [time.perf_counter()]
    clock = lambda: (time.perf_counter() - clock_box[0]) * 1000.0
    try:
        if hub is None:
            say("Nessun FM-1 risponde al test: e' acceso, collegato al Pi, con SAGGA SEQ %s o piu' recente?" % plan.get("firmware", "0.20.3"))
            rc = 3
            return rc
        facts["fm1_version"] = hello["version"]
        say("FM-1: SAGGA SEQ %s, porta del test: %s" % (hello["version"], hub.ctl.label))
        if X.vkey(hello["version"]) < X.vkey(plan.get("firmware", "0")):
            say("Il piano vuole SAGGA SEQ %s sull'FM-1, che ha la %s: aggiorna l'FM-1." % (plan.get("firmware"), hello["version"]))
            rc = 3
            return rc
        if not hello["booted"]:
            if hello["playing"]:
                say("L'FM-1 sta suonando: fermalo (PLAY) e rilancia.")
                rc = 1
                return rc
            B.export_elsewhere_mark(control)             # 0.32.2: the bridge hears this image too: it is not its library's,
            img, st = HT.export(hub.ctl)                 # and its SAVED ON THE PI would cover the question that follows
            if img:
                backup = os.path.join(a.out, "backup-%s.sgq" % ts)
                with open(backup, "wb") as f:
                    f.write(img)
                say("Il progetto in memoria e' salvato (%s)" % os.path.basename(backup))
            else:
                say("Il progetto in memoria non si salva (EXPORT: %s): mi fermo, il tuo progetto resta dov'e'." % st)
                rc = 1
                return rc
            ans = None
            for k_ask in range(3):                       # (asked again when nobody answered: two more times)
                hub.take()
                hub.send(T.open_())
                say(">>> Sull'FM-1: premi SEL per dire si' (lo schermo dice PC TEST? SEL = YES; 20 secondi). Un altro tasto = no.%s"
                    % (" (di nuovo)" if k_ask else ""))
                ans = hub.wait("open", 2.0)
                if ans == 1:
                    ans = hub.wait("open", 25.0)
                if ans != 4:                             # (4: nobody pressed anything)
                    break
                say("  nessun tasto premuto in 20 secondi")
            if ans != 2:
                say("L'FM-1 dice: %s. Niente prova." % T.OPEN_STATES.get(ans, "nessuna risposta"))
                rc = 1
                return rc
            say("Si'. Si comincia: non toccare l'FM-1 fino alla fine.")
        if bridge_was:
            bridge_stopped = True                        # (0.32.2: said first - whatever the stop does, it is started again at the end)
            if not bridge_stop(system, say, wait):
                say("Il bridge del grid non si ferma (%s): niente prova. Riavvia il Pi e riprova." % service_is(system))
                rc = 1
                return rc
            say("il bridge del grid e' fermo per la prova: i Launchpad si spengono e l'FM-1 dice GRID LOST, e' giusto (riparte alla fine)")
        try:                                            # 0.20.9: the FM-1's cells now, to have them back after each reboot
            by0, conns0, fm0 = fm1_now(api)
            keep = K.describe(conns0, by0, fm0) if fm0 else []
        except Exception:
            keep = []
        if not a.non_staccare:
            cells = detach(api, cells, say, a.celle)
            say("Le celle fra l'FM-1 e i synth sono staccate per la prova (%d): tornano alla fine" % len(cells) if cells else
                "Nessuna cella fra l'FM-1 e i synth da staccare")
            away = {cell_key(c) for c in cells}
            keep = [c for c in keep if cell_key(c) not in away]
        for k, sess in enumerate(sessions):
            rebooted = True
            t_boot = time.time()
            hub.send_and_go(T.boot(), "BOOT")
            wait(2.0)
            hub, hello, reboot_info = reconnect(backend, say, system, t_boot, sysfs=sysfs, wait=wait)
            if hub is None or not hello["booted"]:
                say("Dopo il riavvio l'FM-1 non torna nel test: fermo qui.")
                for ln in reboot_info.get("kernel", [])[-8:]:
                    say("  kernel: " + ln)
                rc = 1
                break
            kept = keep_cells(api, keep, say, wait=wait)    # (RaspiMIDIHub's own restore, else the Pi's)
            facts["celle_rimesse"] = facts.get("celle_rimesse", 0) + kept["rimesse"]
            if not a.non_staccare:                      # (RaspiMIDIHub may bring the FM-1's cells back with it)
                cells = detach(api, cells, lambda x: None, a.celle)
            pages = Pages(api, clock, lambda m, h=hub: h.ctl.send(bytes(m)))
            insts = pages.find()
            grid = Grid(lambda m, h=hub: h.ctl.send(m), clock)
            t0, t_wall = time.perf_counter(), time.time()
            conti = None
            if X.vkey(hello.get("version")) >= (0, 23, 1):   # (0.23.1: the FM-1 counts what it sends)
                conti = {"alsa": lambda: K.alsa_midi_counts(K.fm1_usb_path(sysfs), sysfs)}
            rec = run_session(hub, sess, pages, grid, say, clock_box, conti)
            rec["kernel"] = kernel_lines(system, t_wall, 12)  # (0.23.1: what the kernel said of the USB during the session)
            pages.stop()
            if not a.non_staccare:                      # (RaspiMIDIHub's own rescan may have put some back meanwhile)
                try:
                    back = len(fm1_cells(api)[0])
                except Exception:
                    back = 0
                if back:
                    say("  (RaspiMIDIHub ha rimesso %d celle dei synth durante la sessione: tolte di nuovo)" % back)
                    cells = detach(api, cells, lambda x: None, a.celle)
                rec["celle_tornate"] = back
            rec["hello_prima"] = hello
            rec["riavvio"] = reboot_info                # (0.20.9: how long, the kernel's lines, the FM-1's counters)
            rec["celle_fm1"] = kept
            wrong, checked, later = values_back(api, insts, fb_keys(rec["feedback"]), fb_keys(rec.get("feedback_t") or {}),
                                                pressed_last(rec.get("reali_fatti")))
            rec["valori"] = {"sbagliati": wrong, "controllati": checked, "dopo": later}
            rec["pagine"] = sorted(insts)
            rec["errori_pagine"] = pages.errors[:20]
            rec["proprie"] = pages.proprie()
            if rec.get("errore") or rec.get("abort") is not None:
                hub.close()
                hub, h2 = X.connect(backend, None, say, timeout=30.0, quiet=True)
                rec["hello_dopo"] = h2
                hello = h2 or hello
            s2 = dict(sess)
            s2["fm1"] = rec
            out["sessioni"].append(s2)
            T.save(out_json, out)
            music = [m[:4] for m in rec["midi"] if not (len(m) > 4 and m[4] == 2) and not (m[1] in GRID_ST or m[1] == 0xBF or
                     ((m[1] & 0xEF) == 0x8B and 100 <= m[2] < 116))]
            probs, got, want, lag = X.quick(sess, dict(rec, midi=music))   # (not the grid's lights, nor the LFO switches)
            if kept["non_tornano"]:
                probs.append("CELLE: %d celle dell'FM-1 non tornate dopo il riavvio" % len(kept["non_tornano"]))
            if wrong:
                probs.append("VALORI: %d celle delle pagine non seguono l'FM-1 (%s)" % (len(wrong), ", ".join("%s %s" % (w[0], w[1]) for w in wrong[:3])))
            if grid.wrong:
                probs.append("PONTE: %d pad tradotti male dal bridge" % len(grid.wrong))
            if pages.errors:
                probs.append("PAGINE: %s" % pages.errors[0])
            verdict = X.counts_verdict(rec.get("conti"))    # (0.23.1: what the FM-1 sent against what the Pi heard)
            if X.counts_missing(rec.get("conti")):
                probs.append("CONTI: " + verdict[0])
            for ln in verdict:
                X.note("conti %s: %s" % (sess["nome"], ln))
            if rec.get("kernel"):
                for ln in rec["kernel"]:
                    X.note("kernel %s: %s" % (sess["nome"], ln))
            via = {}
            for r in rec["reali_fatti"]:
                via[r[1]] = via.get(r[1], 0) + 1
            rows.append((sess["nome"], "%d/%d" % (got, want), via.get("pagina", 0), via.get("grid", 0), via.get("diretto", 0),
                         "; ".join(probs) if probs else "ok"))
            say("%s  %-34s %2d/%2d sonde, pagine %3d, grid %3d, %4.0f s  %s" % (
                sess["nome"], sess["situazione"][:34], got, want, via.get("pagina", 0), via.get("grid", 0),
                time.perf_counter() - t0, "; ".join(probs) if probs else "ok"))
            if rec.get("abort") is not None:
                say("Fermato da una mano sull'FM-1: la prova finisce qui.")
                break
            if hub is None:
                rc = 1
                break
    except KeyboardInterrupt:
        say("Interrotto.")
    except Exception:                                   # (0.20.4: said in the log the page shows, not lost on stderr)
        import traceback
        say("ERRORE del programma, la prova si ferma qui:")
        for line in traceback.format_exc().rstrip().splitlines():
            say("  " + line)
        rc = 2
    finally:
        if hub is not None and hello and hello.get("booted"):
            t_boot = time.time()
            hub.send_and_go(T.close(), "CLOSE")
            wait(2.0)
            hub, hello, _ = reconnect(backend, say, system, t_boot, sysfs=sysfs, wait=wait)
        home = False                                    # (the project back in the FM-1's memory)
        if hub is not None and hello and hello.get("booted"):
            say("L'FM-1 e' ancora nel test: spegnilo e riaccendilo (ricarica l'ultimo slot salvato).")
        elif hub is not None and rebooted and backup:
            with open(backup, "rb") as f:
                st = HT.import_image(hub.ctl, f.read())
            home = st == "OK"
            say("Il tuo progetto e' tornato in memoria (%s): sull'FM-1 IMPORTED: SAVE TO KEEP IT." % st)
        if rebooted and backup and not home:            # 0.20.9: the FM-1 lost: the project before the prova kept where
            name = "prima-del-banco-%s.sgq" % ts         # the page shows it (PROGETTI: the editor sends it to the FM-1)
            try:
                with open(backup, "rb") as f:
                    keep_file(os.path.join(a.progetti, name), f.read())
                say("Il progetto che l'FM-1 aveva in memoria prima della prova e' nella libreria del hub: %s (PROGETTI: "
                    "editor, Manda all'FM-1). Spento e riacceso, l'FM-1 ha l'ultimo progetto salvato con SAVE." % name)
            except Exception as e:
                say("Il progetto di prima della prova resta in %s (%s)" % (backup, e))
        if hub is not None:
            hub.close()
        if rebooted and keep:                           # 0.20.9: its cells whole again, after the last reboot too
            kept = keep_cells(api, keep, say, timeout=10.0, wait=wait)
            facts["celle_rimesse"] = facts.get("celle_rimesse", 0) + kept["rimesse"]
        if cells:
            if rebooted:
                wait_for_hub(api, need_pages=False)
            left = put_back(api, a.celle, say)
            if left:
                rc = rc or 1
                say("%d celle non sono tornate: Rimetti le celle (pagina del hub) quando i dispositivi ci sono" % left)
        try:                                            # (0.32.2: the word left for a bridge that did not hear the image)
            os.unlink(os.path.join(B.CONTROL_DIR if control is None else control, B.ELSEWHERE))
        except OSError:
            pass
        t_bridge = time.time()
        if bridge_stopped:
            bridge_start(system, say)
        T.save(out_json, out)
        report_md(out_md, audit_f, facts, rows, out_json)
        say("")
        say("Raccolta: %s (%d sessioni). Rapporto: %s" % (out_json, len(out["sessioni"]), out_md))
        if bridge_stopped:                              # 0.23.2: what the bridge says of its start (its ports, the FM-1's
            try:                                        # answer, the Launchpads) - last, after everything is saved
                wait(6.0)
                bl = bridge_lines(system, since=t_bridge)
                if bl:
                    say("IL BRIDGE DEL GRID (ripartito)")
                    for ln in bl:
                        say("  " + ln)
                st = service_is(system)                 # 0.32.2
                if st not in ("active", "?"):
                    say("ATTENZIONE: il bridge del grid non e' ripartito (%s): premi Controlla la matrice, che lo fa ripartire" % st)
            except Exception:
                pass
        finish(rc)
    return rc


if __name__ == "__main__":
    rc = main()
    sys.stdout.flush()
    os._exit(rc)
