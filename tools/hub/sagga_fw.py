#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA HUB: the firmware library, a small web page on the Pi (port 8090).

It keeps the FM-1 packages (.fwsc) in a folder, shows which firmware the connected FM-1 runs, installs the one you
pick (fm1_install.py over USB-MIDI, through the hub), takes new packages by upload, and lists the projects the grid
bridge exported (.sgq) for download. 0.13: BREAK, a drum loop (WAV) cut into slices for a sampler (sagga_slicer.py),
back as a zip. Standard library only.

    sudo python3 sagga_fw.py [--dir /boot/firmware/sagga/firmware] [--projects /boot/firmware/sagga] [--port 8090]
"""
import argparse
import email.parser
import email.policy
import json
import os
import re
import subprocess
import sys
import contextlib
import tempfile
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
INSTALLER = os.environ.get('FM1_INSTALL', os.path.join(HERE, 'fm1_install.py'))
SGQMID = os.environ.get('SAGGA_SGQMID', os.path.join(HERE, 'sagga_sgqmid'))    # 0.11: .sgq <-> .mid (tools/sgqmid, built on the Pi)
ROLL = os.path.join(HERE, 'roll.html')                                           # 0.11: the piano roll page
sys.path.insert(0, HERE)
import sagga_patterns                                                            # noqa: E402  (0.11: the Pi's patterns)
import sagga_progs                                                               # noqa: E402  (0.11: the Pi's progressions)
import sagga_slicer                                                              # noqa: E402  (0.13: a break into slices)
import sagga_editor                                                              # noqa: E402  (0.14: the projects' web editor)
EDITOR = os.path.join(HERE, 'editor.html')                                       # 0.14: its page


def sgqmid(cmd, src, dst, extra=None):
    """run the converter; returns (ok, its message)"""
    if not os.path.isfile(SGQMID):
        return False, 'convertitore non installato (sagga_sgqmid)'
    try:
        r = subprocess.run([SGQMID, cmd, src, dst] + ([extra] if extra else []), capture_output=True, text=True, timeout=30)
    except Exception as e:
        return False, str(e)
    return r.returncode == 0, (r.stderr or r.stdout).strip()
IDENT_RE = re.compile(r'^(FM-1_\S+)\s+\[(\w+)\]\s+port:\s*(.*)$', re.M)


def read_mounts(path='/proc/mounts'):
    try:
        with open(path) as f:
            return [(ln.split()[1], ln.split()[3].split(',')) for ln in f if len(ln.split()) > 3]
    except OSError:
        return []


class BootWriter:
    """writes in a folder that may sit on a partition mounted read-only (RaspiMIDIHub's /boot/firmware): remounted
    read-write for the write only, under RaspiMIDIHub's own lock, like the grid bridge does"""
    LOCK = '/run/raspimidihub/boot-rw.lock'

    def __init__(self, folder, run=None, mounts=None, lock=LOCK):
        self.folder, self.lock = folder, lock
        self.run = run or (lambda cmd: subprocess.run(cmd, check=True, capture_output=True, timeout=10))
        self.mounts = mounts or read_mounts

    def _mount_of(self, path):
        path = os.path.abspath(path)
        best, ro = '/', False
        for mp, opts in self.mounts():
            if (path == mp or path.startswith(mp.rstrip('/') + '/')) and len(mp) >= len(best):
                best, ro = mp, 'ro' in opts
        return best, ro

    @contextlib.contextmanager
    def writable(self):
        mp, ro = self._mount_of(self.folder)
        if not ro:
            os.makedirs(self.folder, exist_ok=True)
            yield
            return
        if mp == '/':
            raise OSError('%s is on the read-only root file system' % self.folder)
        fd = None
        if self.lock and os.path.isdir(os.path.dirname(self.lock)):
            try:
                import fcntl
                fd = os.open(self.lock, os.O_CREAT | os.O_WRONLY, 0o600)
                fcntl.flock(fd, fcntl.LOCK_EX)
            except (OSError, ImportError):
                fd = None
        try:
            self.run(['mount', '-o', 'remount,rw', mp])
            try:
                os.makedirs(self.folder, exist_ok=True)
                yield
                try:
                    self.run(['sync'])
                except Exception:
                    pass
            finally:
                try:
                    self.run(['mount', '-o', 'remount,ro', mp])
                except Exception:
                    pass
        finally:
            if fd is not None:
                os.close(fd)

    def write(self, path, data):
        with self.writable():
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)   # (0.14: the editor's versions folder)
            tmp = path + '.part'
            with open(tmp, 'wb') as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        return path

    def remove(self, path):
        """0.14: a file away (an old version of the editor's)"""
        with self.writable():
            os.unlink(path)


class State:
    """what the page shows: the folders, the FM-1 seen last, the install running (one at a time)"""
    def __init__(self, fw_dir, proj_dir, writer=None, pat_writer=None):
        self.fw_dir, self.proj_dir = fw_dir, proj_dir
        self.writer = writer or BootWriter(fw_dir)
        pat_dir = os.path.join(proj_dir, 'patterns')                     # 0.11: the patterns the grid bridge serves
        self.patterns = sagga_patterns.Patterns(pat_dir, writer=(pat_writer or BootWriter(pat_dir)).write)
        prog_dir = os.path.join(proj_dir, 'progressions')                # 0.11: the progressions the grid bridge serves
        self.progs = sagga_progs.Progressions(prog_dir, writer=(pat_writer or BootWriter(prog_dir)).write)
        self.editor = sagga_editor.Editor(proj_dir, self.writer)       # 0.14: the projects' web editor
        self.lock = threading.Lock()
        self.proc = None                                    # the install running
        self.log = []                                       # its lines (and the last probe's)
        self.job = None                                     # the package being installed
        self.result = None                                  # 'ok' / 'failed N' of the last install
        self.device = None                                  # (identity, mode, port) of the FM-1 seen last
        self.device_at = 0

    def packages(self):
        out = []
        try:
            for n in sorted(os.listdir(self.fw_dir)):
                if n.lower().endswith('.fwsc'):
                    p = os.path.join(self.fw_dir, n)
                    out.append(dict(name=n, size=os.path.getsize(p), mtime=int(os.path.getmtime(p))))
        except OSError:
            pass
        return out

    def projects(self):
        out = []
        try:
            for n in sorted(os.listdir(self.proj_dir)):
                if n.lower().endswith('.sgq'):
                    p = os.path.join(self.proj_dir, n)
                    out.append(dict(name=n, size=os.path.getsize(p), mtime=int(os.path.getmtime(p))))
        except OSError:
            pass
        return out

    def busy(self):
        return self.proc is not None and self.proc.poll() is None

    def probe(self):
        """fm1_install.py --info: the FM-1's identity (cached 5 s; never while an install runs)"""
        with self.lock:
            if self.busy() or time.time() - self.device_at < 5:
                return self.device
            try:
                r = subprocess.run([sys.executable, INSTALLER, '--info'], capture_output=True, text=True, timeout=20)
                m = IDENT_RE.search(r.stdout or '')
                self.device = (m.group(1), m.group(2), m.group(3).strip()) if m else None
            except Exception:
                self.device = None
            self.device_at = time.time()
            return self.device

    def install(self, name):
        path = os.path.join(self.fw_dir, os.path.basename(name))
        if not os.path.isfile(path) or not name.lower().endswith('.fwsc'):
            return 'no such package'
        with self.lock:
            if self.busy():
                return 'an install is running'
            self.log = ['install %s' % name]
            self.job, self.result = name, None
            self.proc = subprocess.Popen([sys.executable, '-u', INSTALLER, '--yes', path], stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT, text=True)
            threading.Thread(target=self._reader, args=(self.proc,), daemon=True).start()
        return None

    def _reader(self, proc):
        for line in proc.stdout:
            line = line.replace('\r', '\n').rstrip('\n')
            for part in line.split('\n'):
                if part.strip():
                    self.log.append(part[-200:])
            del self.log[:-400]
        rc = proc.wait()
        self.result = 'ok' if rc == 0 else 'failed %d' % rc
        self.log.append('done: %s' % self.result)
        self.device_at = 0

    def snapshot(self):
        return dict(packages=self.packages(), projects=self.projects(), busy=self.busy(), job=self.job,
                    result=self.result, log=self.log[-60:], device=self.probe())


PAGE = r'''<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SAGGA HUB</title><style>
body{font:16px/1.4 system-ui,sans-serif;margin:0;background:#111;color:#eee}header{background:#222;padding:12px 16px;font-weight:700;letter-spacing:.08em}
main{padding:12px 16px;max-width:720px;margin:auto}h2{font-size:14px;letter-spacing:.1em;color:#9cf;margin:20px 0 8px}
.row{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid #333}
button{background:#2a6;color:#fff;border:0;border-radius:6px;padding:8px 14px;font-size:15px}button[disabled]{background:#444}
.dev{background:#1a2a3a;border-radius:8px;padding:10px 12px}.mono{font-family:ui-monospace,monospace;font-size:13px}
pre{background:#000;color:#9f9;padding:10px;border-radius:8px;max-height:260px;overflow:auto;font-size:12px}small{color:#999}
input[type=file]{color:#ccc}a{color:#9cf}</style></head><body>
<header>SAGGA HUB</header><main>
<h2>FM-1</h2><div class="dev" id="dev">...</div>
<h2>FIRMWARE</h2><div id="pk"></div>
<form id="up" method="post" action="/api/upload" enctype="multipart/form-data" class="row"><input type="file" name="f" accept=".fwsc" required><button>Carica</button></form>
<h2>INSTALLAZIONE</h2><pre id="log"></pre>
<h2>PROGETTI</h2><div id="pr"></div>
<div class="row" style="flex-wrap:wrap"><input id="np" placeholder="nome del progetto" size="18"><button onclick="newp()">Nuovo</button><button class="sec" onclick="recv()">Ricevi dall'FM-1</button><small id="npm"></small></div>
<small>Nuovo: un progetto vuoto nella libreria, che si apre nell'editor. Ricevi: il progetto che l'FM-1 ha adesso (fermo), con quel nome. Dall'editor: <b>Manda all'FM-1</b>.</small>
<form method="post" action="/api/upload" enctype="multipart/form-data" class="row"><span><small>un .sgq (torna nella libreria) o un .mid (diventa un progetto di tracce TAPE)</small></span><input type="file" name="f" accept=".sgq,.mid,.midi" required><button>Carica</button></form>
<h2>BREAK IN SLICE</h2>
<form method="post" action="/api/slice" enctype="multipart/form-data" class="row" style="flex-wrap:wrap"><input type="file" name="f" accept=".wav" required>
<label><small>slice</small> <select name="slices"><option>8</option><option selected>16</option><option>32</option></select></label>
<label><small>BPM</small> <input name="bpm" size="5" placeholder="auto"></label><label><small>battute</small> <input name="bars" size="3" placeholder="auto"></label>
<label><small>prima nota</small> <input name="pen" size="3" value="36"></label><button>Taglia</button></form>
<small>Un loop di batteria in WAV: trovo inizio, battute e tempo, taglio sulla griglia spostando ogni taglio sul colpo vicino. Torna uno zip: le slice (01.wav ...), il loop con i cue, un .sfz per sfizz / Zynthian (dalla prima nota in su, una alla volta) e LEGGIMI.txt con cosa impostare sull'FM-1 (traccia BREAK, la PEN = la prima nota, SEQ 7 SLICES).</small>
<h2>PATTERN SUL PI</h2><div class="row"><select id="pg" onchange="pats()"></select><small id="pn"></small></div><div id="pl"></div>
<small>Sull'FM-1: SEQ + ALG oltre l'ultima variazione arriva a queste, BEAT le carica; SEQ + SAVE ci aggiunge il pattern della traccia.</small>
<h2>PROGRESSIONI SUL PI</h2><div class="row"><select id="qg" onchange="progs()"></select><select id="qm" onchange="progs()"></select><small id="qn"></small></div><div id="ql"></div>
<div class="row"><select id="am"></select><input id="ac" placeholder="i bVI bVII i  (ii7:8 V7:8 Imaj7^1 ...)" style="flex:1"><button onclick="padd()">Aggiungi</button></div>
<small>Accordi sopra la tonica: I bII II bIII III IV #IV V bVI VI bVII VII, minuscolo = minore; poi la forma (7 maj7 9 sus2 o ...), :N la durata in sedicesimi, ^N quanti sedicesimi in anticipo. Sull'FM-1: SEQ 4 K2 oltre le progressioni del genere arriva a queste (le pi&ugrave; simili prima, del MOOD scelto); SEQ + SAVE su SEQ 4 / SEQ 8 ci aggiunge la progressione.</small>
</main><script>
const h=s=>s.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function tick(){const s=await (await fetch('/api/state')).json();
document.getElementById('dev').innerHTML=s.device?`<b>${h(s.device[0])}</b> <small>[${h(s.device[1])}] ${h(s.device[2])}</small>`:'<small>nessun FM-1 risponde (cavo? un altro programma lo usa?)</small>';
document.getElementById('pk').innerHTML=s.packages.map(p=>`<div class="row"><span class="mono">${h(p.name)} <small>${(p.size/1024).toFixed(0)} KB</small></span><button ${s.busy?'disabled':''} onclick="inst('${h(p.name)}')">Installa</button></div>`).join('')||'<small>nessun pacchetto: carica un .fwsc</small>';
document.getElementById('log').textContent=(s.job?`[${s.job}] `:'')+s.log.join('\n');
function npost(u){const n=document.getElementById('np').value.trim(),m=document.getElementById('npm');if(!n){m.textContent='scrivi un nome';return null;}m.textContent='...';return fetch(u+'?file='+encodeURIComponent(n),{method:'POST'}).then(async r=>{if(!r.ok){m.textContent=await r.text();return null;}const d=await r.json();location.href='/edit/'+encodeURIComponent(d.name);});}
function newp(){npost('/api/project/new');}
function recv(){npost('/api/fm1/receive');}
document.getElementById('pr').innerHTML=s.projects.map(p=>`<div class="row"><a class="mono" href="/projects/${encodeURIComponent(p.name)}">${h(p.name)}</a><span><a href="/projects/${encodeURIComponent(p.name.replace(/\.sgq$/i,''))}.mid"><small>.mid</small></a> <a href="/edit/${encodeURIComponent(p.name)}"><small><b>editor</b></small></a> <a href="/roll/${encodeURIComponent(p.name)}"><small>piano roll</small></a> <small>${new Date(p.mtime*1000).toLocaleString()}</small></span></div>`).join('')||'<small>nessun progetto esportato</small>';}
async function inst(n){if(!confirm('Installare '+n+' sull\'FM-1? Non spegnere durante la scrittura.'))return;await fetch('/api/install?file='+encodeURIComponent(n),{method:'POST'});tick();}
async function pats(){const sel=document.getElementById('pg');const g=sel.value||'TECHNO';const s=await (await fetch('/api/patterns?genre='+g)).json();
if(!sel.options.length){sel.innerHTML=s.genres.map(x=>`<option${x==g?' selected':''}>${x}</option>`).join('');}
document.getElementById('pn').textContent=s.parts.reduce((a,p)=>a+p.list.length,0)+' pattern';
document.getElementById('pl').innerHTML=s.parts.map(p=>`<h2>${h(p.part)} <small>${p.list.length}</small></h2>`+p.list.map((x,i)=>`<div class="row"><span class="mono">${h(x.text)}${x.notes?'<br><small>'+h(x.notes)+'</small>':''}</span><button onclick="del('${g}','${p.part}',${i})">Elimina</button></div>`).join('')).join('');}
async function del(g,p,i){if(!confirm('Eliminare il pattern '+(i+1)+' di '+p+' ('+g+')?'))return;await fetch('/api/patterns/delete?genre='+g+'&part='+p+'&i='+i,{method:'POST'});pats();}
async function progs(){const sel=document.getElementById('qg'),ms=document.getElementById('qm');const g=sel.value||'TECHNO',m=ms.value||'ANY';
const s=await (await fetch('/api/progressions?genre='+g)).json();
if(!sel.options.length){sel.innerHTML=s.genres.map(x=>`<option${x==g?' selected':''}>${x}</option>`).join('');ms.innerHTML=s.moods.map(x=>`<option>${x}</option>`).join('');document.getElementById('am').innerHTML=s.moods.map(x=>`<option>${x}</option>`).join('');}
const l=s.list.map((x,i)=>[x,i]).filter(([x])=>m=='ANY'||x.mood==m);
document.getElementById('qn').textContent=l.length+' progressioni';
document.getElementById('ql').innerHTML=l.map(([x,i])=>`<div class="row"><span class="mono"><small>${h(x.mood)}</small> ${h(x.chords)}${x.name?' <small>'+h(x.name)+'</small>':''}</span><button onclick="pdel('${g}',${i})">Elimina</button></div>`).join('');}
async function pdel(g,i){if(!confirm('Eliminare la progressione '+(i+1)+' di '+g+'?'))return;await fetch('/api/progressions/delete?genre='+g+'&i='+i,{method:'POST'});progs();}
async function padd(){const g=document.getElementById('qg').value||'TECHNO',m=document.getElementById('am').value||'ANY',c=document.getElementById('ac').value;
const r=await fetch('/api/progressions/add?genre='+g+'&mood='+m+'&chords='+encodeURIComponent(c),{method:'POST'});if(!r.ok){alert(await r.text());return;}document.getElementById('ac').value='';progs();}
tick();setInterval(tick,2000);pats();progs();</script></body></html>'''


def multipart_file(content_type, body):
    """the first file field of a multipart/form-data body -> (filename, bytes), or (None, None)"""
    head = ('Content-Type: %s\r\nMIME-Version: 1.0\r\n\r\n' % content_type).encode()
    msg = email.parser.BytesParser(policy=email.policy.default).parsebytes(head + body)
    if not msg.is_multipart():
        return None, None
    for part in msg.iter_parts():
        fn = part.get_filename()
        if fn:
            return fn, part.get_payload(decode=True)
    return None, None


def multipart_form(content_type, body):
    """0.13: the fields of a multipart/form-data body -> ({name: text}, (filename, bytes) of the first file or (None, None))"""
    head = ('Content-Type: %s\r\nMIME-Version: 1.0\r\n\r\n' % content_type).encode()
    msg = email.parser.BytesParser(policy=email.policy.default).parsebytes(head + body)
    fields, f = {}, (None, None)
    if not msg.is_multipart():
        return fields, f
    for part in msg.iter_parts():
        fn = part.get_filename()
        if fn:
            if f[0] is None:
                f = (fn, part.get_payload(decode=True))
        else:
            name = part.get_param('name', header='content-disposition')
            if name:
                fields[name] = (part.get_payload(decode=True) or b'').decode('utf-8', 'replace').strip()
    return fields, f


def slice_request(fields, name, data):
    """0.13: the BREAK form -> (zip bytes, its file name) or raises sagga_slicer.SliceError with what is wrong"""
    def num(key, kind, lo, hi):
        v = fields.get(key, '').replace(',', '.')
        if not v or v.lower() == 'auto':
            return None
        try:
            x = kind(v)
        except ValueError:
            raise sagga_slicer.SliceError('%s: "%s" non è un numero' % (key, v))
        if not lo <= x <= hi:
            raise sagga_slicer.SliceError('%s: %s fuori da %s..%s' % (key, v, lo, hi))
        return x
    n = num('slices', int, 8, 32) or 16
    pen = num('pen', int, 0, 127)
    zipb, info = sagga_slicer.slice_break(data, name, n, num('bpm', float, 40, 300), num('bars', int, 1, 64), 36 if pen is None else pen)
    return zipb, '%s-%d-slice-%dbpm.zip' % (info['name'], n, int(round(info['bpm'])))


def make_handler(state):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, code, body, ctype='text/html; charset=utf-8', extra=None):
            if isinstance(body, str):
                body = body.encode()
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            if u.path == '/':
                return self.send(200, PAGE)
            if u.path == '/api/state':
                return self.send(200, json.dumps(state.snapshot()), 'application/json')
            if u.path == '/api/patterns':                         # 0.11: the patterns of a genre, part by part
                q = urllib.parse.parse_qs(u.query)
                g = q.get('genre', ['TECHNO'])[0].upper()
                if g not in sagga_patterns.GENRES:
                    return self.send(404, 'no such genre', 'text/plain')
                parts = {}
                for _, p, t, n in state.patterns.entries(g):
                    parts.setdefault(p, []).append(dict(text=t, notes=n))
                order = [p for p in sagga_patterns.PARTS if p in parts]
                return self.send(200, json.dumps(dict(genre=g, genres=sagga_patterns.GENRES,
                                                      parts=[dict(part=p, list=parts[p]) for p in order])), 'application/json')
            if u.path == '/api/progressions':                     # 0.11: the progressions of a genre
                q = urllib.parse.parse_qs(u.query)
                g = q.get('genre', ['TECHNO'])[0].upper()
                if g not in sagga_progs.GENRES:
                    return self.send(404, 'no such genre', 'text/plain')
                rows = [dict(mood=m, chords=sagga_progs.name(r), name=n) for _, m, r, n in state.progs.entries(g)]
                return self.send(200, json.dumps(dict(genre=g, genres=sagga_progs.GENRES, moods=sagga_progs.MOODS, list=rows)), 'application/json')
            if u.path.startswith('/edit/') or u.path == '/edit':  # 0.14: the web editor (its project in the address)
                if os.path.isfile(EDITOR):
                    with open(EDITOR, 'rb') as f:
                        return self.send(200, f.read())
                return self.send(404, 'editor non installato', 'text/plain; charset=utf-8')
            if u.path in ('/api/project', '/api/project/versions'):    # 0.14: a project as the editor reads it; its versions
                q = urllib.parse.parse_qs(u.query)
                try:
                    if u.path.endswith('versions'):
                        return self.send(200, json.dumps(dict(versions=state.editor.versions(q.get('file', [''])[0]))), 'application/json')
                    return self.send(200, json.dumps(state.editor.read(q.get('file', [''])[0])), 'application/json')
                except sagga_editor.EditorError as e:
                    return self.send(e.code, str(e), 'text/plain; charset=utf-8')
            if u.path.startswith('/roll/'):                       # 0.11: the piano roll of a project of the library
                name = os.path.basename(urllib.parse.unquote(u.path[len('/roll/'):]))
                if name.lower().endswith('.sgq') and os.path.isfile(os.path.join(state.proj_dir, name)) and os.path.isfile(ROLL):
                    with open(ROLL, 'rb') as f:
                        return self.send(200, f.read())
                return self.send(404, 'no such project', 'text/plain')
            if u.path.startswith('/projects/'):
                name = os.path.basename(urllib.parse.unquote(u.path[len('/projects/'):]))
                p = os.path.join(state.proj_dir, name)
                if name.lower().endswith('.sgq') and os.path.isfile(p):
                    with open(p, 'rb') as f:
                        return self.send(200, f.read(), 'application/octet-stream',
                                         {'Content-Disposition': 'attachment; filename="%s"' % name})
                if name.lower().endswith('.mid'):                 # 0.11: the project as a MIDI file, made now
                    src = os.path.join(state.proj_dir, name[:-4] + '.sgq')
                    if os.path.isfile(src):
                        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tf:
                            dst = tf.name
                        ok, msg = sgqmid('sgq2mid', src, dst)
                        try:
                            data = open(dst, 'rb').read() if ok else b''
                        finally:
                            try: os.unlink(dst)
                            except OSError: pass
                        if ok:
                            return self.send(200, data, 'audio/midi', {'Content-Disposition': 'attachment; filename="%s"' % name})
                        return self.send(500, msg, 'text/plain; charset=utf-8')
            return self.send(404, 'not found', 'text/plain')

        def do_POST(self):
            u = urllib.parse.urlparse(self.path)
            if u.path == '/api/install':
                q = urllib.parse.parse_qs(u.query)
                err = state.install(q.get('file', [''])[0])
                return self.send(400 if err else 200, json.dumps(dict(error=err)), 'application/json')
            if u.path == '/api/patterns/delete':                  # 0.11: a pattern of the Pi's away
                q = urllib.parse.parse_qs(u.query)
                g, p = q.get('genre', [''])[0].upper(), q.get('part', [''])[0].upper()
                try:
                    k = int(q.get('i', ['-1'])[0])
                    ok = state.patterns.delete(g, p, k)
                except (ValueError, OSError) as e:
                    return self.send(500, 'non riesco: %s' % e, 'text/plain; charset=utf-8')
                return self.send(200 if ok else 404, json.dumps(dict(ok=ok)), 'application/json')
            if u.path == '/api/progressions/delete':              # 0.11: a progression of the Pi's away
                q = urllib.parse.parse_qs(u.query)
                g = q.get('genre', [''])[0].upper()
                try:
                    ok = state.progs.delete(g, int(q.get('i', ['-1'])[0]))
                except (ValueError, OSError) as e:
                    return self.send(500, 'non riesco: %s' % e, 'text/plain; charset=utf-8')
                return self.send(200 if ok else 404, json.dumps(dict(ok=ok)), 'application/json')
            if u.path == '/api/progressions/add':                 # 0.11: a progression written on the page
                q = urllib.parse.parse_qs(u.query)
                g, m = q.get('genre', [''])[0].upper(), q.get('mood', ['ANY'])[0].upper()
                try:
                    k = state.progs.add(g, m, sagga_progs.parse(q.get('chords', [''])[0]))
                except ValueError as e:
                    return self.send(400, 'non è una progressione: %s' % e, 'text/plain; charset=utf-8')
                except OSError as e:
                    return self.send(500, 'non riesco: %s' % e, 'text/plain; charset=utf-8')
                return self.send(200, json.dumps(dict(ok=True, i=k)), 'application/json')
            if u.path == '/api/roll':                              # 0.11: the piano roll saves: a MIDI body of the TAPE tracks over the project
                q = urllib.parse.parse_qs(u.query)
                name = os.path.basename(q.get('file', [''])[0])
                dst = os.path.join(state.proj_dir, name)
                n = int(self.headers.get('Content-Length', '0') or 0)
                if not name.lower().endswith('.sgq') or not os.path.isfile(dst):
                    return self.send(404, 'no such project', 'text/plain; charset=utf-8')
                if n <= 0 or n > 2 * 1024 * 1024:
                    return self.send(400, 'empty or too big', 'text/plain; charset=utf-8')
                data = self.rfile.read(n)
                with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tf:
                    tf.write(data); src = tf.name
                out = src[:-4] + '.sgq'
                ok, msg = sgqmid('mid2sgq', src, out, dst)
                try:
                    if ok:
                        with open(dst, 'rb') as f:
                            state.writer.write(dst + '.bak', f.read())        # the project as it was, once
                        state.writer.write(dst, open(out, 'rb').read())
                finally:
                    for p in (src, out):
                        try: os.unlink(p)
                        except OSError: pass
                return self.send(200 if ok else 400, msg.replace(out, name), 'text/plain; charset=utf-8')
            if u.path.startswith('/api/project') or u.path.startswith('/api/fm1/'):   # 0.14: the editor writes, the FM-1 in / out
                q = urllib.parse.parse_qs(u.query)
                name = q.get('file', [''])[0]
                n = int(self.headers.get('Content-Length', '0') or 0)
                if n > 16 * 1024 * 1024:
                    return self.send(400, 'troppo grande', 'text/plain; charset=utf-8')
                body = self.rfile.read(n) if n > 0 else b''
                ed = state.editor
                try:
                    if u.path == '/api/project':
                        try:
                            req = json.loads(body.decode('utf-8') or '{}')
                        except ValueError:
                            return self.send(400, 'JSON non valido', 'text/plain; charset=utf-8')
                        out = ed.save(name, req.get('changes', []), req.get('rev'))
                    elif u.path == '/api/project/new':
                        out = ed.new(name)
                    elif u.path == '/api/project/restore':
                        out = ed.restore(name, q.get('v', [''])[0])
                    elif u.path == '/api/fm1/receive':
                        out = ed.receive(name)
                    elif u.path == '/api/fm1/send':
                        out = dict(msg=ed.send(name))
                    else:
                        return self.send(404, 'not found', 'text/plain')
                except sagga_editor.EditorError as e:
                    return self.send(e.code, str(e), 'text/plain; charset=utf-8')
                except OSError as e:
                    return self.send(500, 'non riesco a scrivere: %s' % e, 'text/plain; charset=utf-8')
                return self.send(200, json.dumps(out), 'application/json')
            if u.path == '/api/slice':                             # 0.13: a break into slices, back as a zip
                n = int(self.headers.get('Content-Length', '0') or 0)
                if n <= 0 or n > 24 * 1024 * 1024:
                    return self.send(400, 'upload vuoto o troppo grande (un break: qualche battuta di WAV)', 'text/plain; charset=utf-8')
                fields, (name, data) = multipart_form(self.headers.get('Content-Type', ''), self.rfile.read(n))
                if not name or not data:
                    return self.send(400, 'serve un file .wav', 'text/plain; charset=utf-8')
                try:
                    zipb, zname = slice_request(fields, name, data)
                except sagga_slicer.SliceError as e:
                    return self.send(400, 'non riesco a tagliarlo: %s' % e, 'text/plain; charset=utf-8')
                return self.send(200, zipb, 'application/zip', {'Content-Disposition': 'attachment; filename="%s"' % zname})
            if u.path == '/api/upload':
                n = int(self.headers.get('Content-Length', '0') or 0)
                if n <= 0 or n > 4 * 1024 * 1024:
                    return self.send(400, 'upload vuoto o troppo grande', 'text/plain; charset=utf-8')
                name, data = multipart_file(self.headers.get('Content-Type', ''), self.rfile.read(n))
                low = (name or '').lower()
                if not name or not (low.endswith('.fwsc') or low.endswith('.sgq') or low.endswith('.mid') or low.endswith('.midi')):
                    return self.send(400, 'serve un file .fwsc, .sgq o .mid', 'text/plain; charset=utf-8')
                try:
                    if low.endswith('.fwsc'):
                        state.writer.write(os.path.join(state.fw_dir, os.path.basename(name)), data)
                    elif low.endswith('.sgq'):
                        state.writer.write(os.path.join(state.proj_dir, os.path.basename(name)), data)
                    else:                                           # 0.11: a MIDI file -> a project of TAPE tracks
                        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tf:
                            tf.write(data); src = tf.name
                        dst = src[:-4] + '.sgq'
                        ok, msg = sgqmid('mid2sgq', src, dst)
                        try:
                            if ok:
                                out = os.path.splitext(os.path.basename(name))[0] + '.sgq'
                                state.writer.write(os.path.join(state.proj_dir, out), open(dst, 'rb').read())
                        finally:
                            for p in (src, dst):
                                try: os.unlink(p)
                                except OSError: pass
                        if not ok:
                            return self.send(400, 'il file MIDI non si converte: %s' % msg, 'text/plain; charset=utf-8')
                except Exception as e:
                    return self.send(500, 'non riesco a scrivere: %s' % e, 'text/plain; charset=utf-8')
                self.send_response(303)
                self.send_header('Location', '/')
                self.end_headers()
                return None
            return self.send(404, 'not found', 'text/plain')
    return H


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--dir', default='/boot/firmware/sagga/firmware')
    ap.add_argument('--projects', default='/boot/firmware/sagga')
    ap.add_argument('--port', type=int, default=8090)
    ap.add_argument('--bind', default='0.0.0.0')
    a = ap.parse_args(argv)
    state = State(a.dir, a.projects)
    try:
        with state.writer.writable():
            pass                                            # (the folder exists from now on)
    except Exception as e:
        print('firmware folder %s: %s' % (a.dir, e), file=sys.stderr, flush=True)
    srv = ThreadingHTTPServer((a.bind, a.port), make_handler(state))
    print('SAGGA HUB firmware library on http://%s:%d  (%s)' % (a.bind, a.port, a.dir), file=sys.stderr, flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
