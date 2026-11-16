# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA EDITOR (0.14): what the hub's web editor does with a project of the library (sagga_fw.py serves the page,
editor.html; this does the work). 0.15: the project's name, the TAPE tracks' events, where the FM-1 is (pos) and the
notes it plays for the page (preview), both through the grid bridge.

  read(name)               the project as the editor sees it: sagga_sgqjson read (the firmware's own core: the same
                           format and limits as the FM-1)
  save(name, changes, rev) the changes over the file as it is (rev: its mtime as the page read it - someone else saved
                           meanwhile: refused), through the firmware's sanitize; the file as it was goes to the versions
  new(name)                a new project in the library
  versions(name) / restore(name, version)
  receive(name) / send(name)   the FM-1's project into the library / a project of the library into the FM-1 (stopped):
                           through the grid bridge when it runs (it holds the FM-1's port: the hub asks it with a file in
                           CONTROL_DIR, sagga_grid_bridge.py's Control), else with sagga_grid_bridge.py --export / --import
  pos()                    0.15: where the FM-1 is (the bridge writes CONTROL_DIR/pos.json while a page asks: pos-want)
  preview(track, notes, vel, gate_ms, tape)   0.15: the FM-1 plays these notes on that track (the bridge sends them)

A change is [group, index, field, elem, value]: index "-" or an int or "t,p,s" (a step), elem "-" or an int (an array
field), value an int - one line of sagga_sgqjson's patch. 0.15, a TAPE track's events: ["tape", "T", "clear", "-", 0]
then ["tape", "T,ON,DUR,NOTE", "add", "-", VEL] for each (the track's events written again whole).
"""
import unicodedata
import json
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SGQJSON = os.environ.get('SAGGA_SGQJSON', os.path.join(HERE, 'sagga_sgqjson'))
BRIDGE = os.environ.get('SAGGA_BRIDGE', '/opt/sagga/sagga_grid_bridge.py')
CONTROL_DIR = os.environ.get('SAGGA_CONTROL', '/run/sagga')
VERSIONS = 'versioni'                       # the folder of the old versions, inside the library (the bridge lists only .sgq files)
KEEP_VERSIONS = 20
NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9 ._+-]{0,39}\.sgq$')
GROUPS = ('project', 'key', 'track', 'step', 'scene', 'lfo', 'lfox', 'chain', 'song', 'song_e', 'live', 'ext', 'mfxc', 'mfxd', 'lfoe', 'mod', 'th', 'thp', 'tape')   # 0.19 mfxc: the MIDI FX chain; 0.20 mfxd lfoe mod; 0.23 th thp: the THEORY engines
NAME_LEN = 16                               # 0.15: a project's name (sq_ext_t.name)
NAME_OK = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_.+#&!\'()/:')
POS_FRESH = 3.0                             # 0.15: a position older than this: the FM-1 is not playing for us (s)


class EditorError(Exception):
    """what went wrong, said for the page (and an HTTP code)"""
    def __init__(self, text, code=400):
        super().__init__(text)
        self.code = code


def clean_name(name):
    name = os.path.basename((name or '').strip())
    if name and not name.lower().endswith('.sgq'):
        name += '.sgq'
    if not NAME_RE.match(name):
        raise EditorError('nome non valido (lettere, numeri, spazi . _ + -, fino a 40 caratteri)')
    return name


def _tool(args, timeout=30):
    if not os.path.isfile(SGQJSON):
        raise EditorError('convertitore non installato (sagga_sgqjson): rilancia install_hub.sh', 500)
    try:
        r = subprocess.run([SGQJSON] + args, capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        raise EditorError('sagga_sgqjson: %s' % e, 500)
    if r.returncode:
        raise EditorError((r.stderr or r.stdout).strip() or 'sagga_sgqjson: errore %d' % r.returncode, 400 if r.returncode in (2, 4) else 500)
    return r.stdout


def patch_lines(changes):
    """the changes as sagga_sgqjson's patch; a malformed one raises EditorError (nothing is written)"""
    out = []
    if not isinstance(changes, list) or len(changes) > 200000:
        raise EditorError('modifiche non valide')
    for k, c in enumerate(changes):
        if not isinstance(c, (list, tuple)) or len(c) != 5:
            raise EditorError('modifica %d: servono 5 valori' % (k + 1))
        g, idx, f, el, v = c
        if g == 'tape':                                  # 0.15: tape T clear - 0 / tape T,ON,DUR,NOTE add - VEL
            idx = str(idx)
            ok = (f == 'clear' and re.match(r'^\d{1,2}$', idx)) or (f == 'add' and re.match(r'^\d{1,2},\d{1,5},\d{1,5},\d{1,3}$', idx))
            if not ok or str(el) != '-' or isinstance(v, bool) or not isinstance(v, int):
                raise EditorError('modifica %d: tape %r %r' % (k + 1, idx, f))
            out.append('tape %s %s - %d' % (idx, f, v))
            continue
        if g not in GROUPS or not isinstance(f, str) or not re.match(r'^[a-z_0-9]{1,24}$', f):
            raise EditorError('modifica %d: %r %r' % (k + 1, g, f))
        idx = str(idx)
        if not re.match(r'^(-|\d{1,3}(,\d{1,3}){0,2})$', idx):
            raise EditorError('modifica %d: indice %r' % (k + 1, idx))
        el = str(el)
        if not re.match(r'^(-|\d{1,3})$', el):
            raise EditorError('modifica %d: elemento %r' % (k + 1, el))
        if isinstance(v, bool) or not isinstance(v, int):
            raise EditorError('modifica %d: valore %r' % (k + 1, v))
        out.append('%s %s %s %s %d' % (g, idx, f, el, v))
    return '\n'.join(out) + '\n'


def project_name(text):
    """0.15: a name as the FM-1 shows it (as sq_name_sanitize: upper case, its characters, 16 at most), from a file
    name or what was typed: accents dropped (è -> E), other characters _"""
    base = os.path.basename(text or '')
    if base.lower().endswith('.sgq'):
        base = base[:-4]
    t = unicodedata.normalize('NFKD', base).encode('ascii', 'ignore').decode('ascii').upper()
    t = ''.join(c if c in NAME_OK else '_' for c in t)
    return t.strip()[:NAME_LEN].rstrip()


def name_changes(text):
    """the ext name as changes (the 16 characters, 0 after the last)"""
    t = project_name(text)
    return [['ext', '-', 'name', str(i), ord(t[i]) if i < len(t) else 0] for i in range(NAME_LEN)]


def _vkey(n):
    """a version's order: its time, then its -2, -3 ..."""
    m = re.match(r'^(\d{8}-\d{6})(?:-(\d+))?\.sgq$', n)
    return (m.group(1), int(m.group(2) or 1)) if m else (n, 0)


class Editor:
    def __init__(self, folder, writer, bridge=BRIDGE, control=CONTROL_DIR, run=subprocess.run):
        self.folder, self.writer, self.bridge, self.control, self.run = folder, writer, bridge, control, run

    def path(self, name):
        return os.path.join(self.folder, clean_name(name))

    def _exists(self, name):
        p = self.path(name)
        if not os.path.isfile(p):
            raise EditorError('il progetto %s non c\'è' % name, 404)
        return p

    def read(self, name):
        p = self._exists(name)
        d = json.loads(_tool(['read', p]))
        d['name'] = os.path.basename(p)
        d['rev'] = int(os.path.getmtime(p) * 1000)
        return d

    def _keep_version(self, p):
        """the file as it is now into versioni/<name>/<time>.sgq (the newest KEEP_VERSIONS)"""
        vdir = os.path.join(self.folder, VERSIONS, os.path.basename(p)[:-4])
        with open(p, 'rb') as f:
            data = f.read()
        stamp = time.strftime('%Y%m%d-%H%M%S')        # (when it was replaced; two in one second: -2, -3 ...)
        name, k = stamp, 1
        while os.path.exists(os.path.join(vdir, name + '.sgq')):
            k += 1
            name = '%s-%d' % (stamp, k)
        self.writer.write(os.path.join(vdir, name + '.sgq'), data)
        old = sorted((n for n in os.listdir(vdir) if n.endswith('.sgq')), key=_vkey)
        for n in old[:-KEEP_VERSIONS]:
            self.writer.remove(os.path.join(vdir, n))

    def save(self, name, changes, rev=None):
        p = self._exists(name)
        if rev is not None and int(rev) != int(os.path.getmtime(p) * 1000):
            raise EditorError('il progetto è cambiato da quando l\'hai aperto (salvato dall\'FM-1 o da un\'altra pagina): ricaricalo', 409)
        patch = patch_lines(changes)
        with tempfile.TemporaryDirectory() as td:
            pf, out = os.path.join(td, 'patch.txt'), os.path.join(td, 'out.sgq')
            with open(pf, 'w') as f:
                f.write(patch)
            _tool(['apply', p, pf, out])
            with open(out, 'rb') as f:
                data = f.read()
        self._keep_version(p)
        self.writer.write(p, data)
        return self.read(name)

    def new(self, name):
        p = self.path(name)
        if os.path.exists(p):
            raise EditorError('c\'è già un progetto %s' % os.path.basename(p), 409)
        with tempfile.TemporaryDirectory() as td:
            out, pf = os.path.join(td, 'new.sgq'), os.path.join(td, 'name.txt')
            with open(pf, 'w') as f:                                  # 0.15: named after its file
                f.write(patch_lines(name_changes(os.path.basename(p))))
            _tool(['apply', 'new', pf, out])
            with open(out, 'rb') as f:
                self.writer.write(p, f.read())
        return self.read(name)

    def versions(self, name):
        vdir = os.path.join(self.folder, VERSIONS, clean_name(name)[:-4])
        try:
            return sorted((n[:-4] for n in os.listdir(vdir) if n.endswith('.sgq')), key=lambda n: _vkey(n + '.sgq'), reverse=True)
        except OSError:
            return []

    def restore(self, name, version):
        p = self._exists(name)
        if not re.match(r'^\d{8}-\d{6}(-\d{1,3})?$', version or ''):
            raise EditorError('versione non valida')
        src = os.path.join(self.folder, VERSIONS, os.path.basename(p)[:-4], version + '.sgq')
        if not os.path.isfile(src):
            raise EditorError('la versione %s non c\'è' % version, 404)
        with open(src, 'rb') as f:
            data = f.read()
        _tool(['read', src])                                   # (still a project)
        self._keep_version(p)
        self.writer.write(p, data)
        return self.read(name)

    # ---- 0.15: where the FM-1 is, what it plays for the page
    def pos(self):
        """the newest position the bridge wrote (and a wish for more: pos-want, which the bridge sees and asks the FM-1
        for positions while it is fresh)"""
        out = dict(bridge=self.bridge_alive(), fresh=False)
        try:
            with open(os.path.join(self.control, 'pos-want'), 'w') as f:
                f.write('%.0f\n' % time.time())
        except OSError:
            return out
        try:
            p = os.path.join(self.control, 'pos.json')
            age = time.time() - os.path.getmtime(p)
            with open(p) as f:
                d = json.load(f)
        except (OSError, ValueError):
            return out
        if isinstance(d, dict):
            out.update(d)
            out['age'] = round(age, 2)
            out['fresh'] = age < POS_FRESH or not d.get('playing')
        return out

    def preview(self, track, notes, vel=100, gate_ms=250, tape=False):
        """the FM-1 plays these notes on that track, as the track plays a step (its key, CHORD ...); tape: as a TAPE note"""
        try:
            track = int(track)
            notes = [int(n) for n in notes][:4]
            vel, gate_ms = int(vel), int(gate_ms)
        except (TypeError, ValueError):
            raise EditorError('ascolto: valori non validi')
        if not 0 <= track < 16 or not notes or any(not 0 <= n < 128 for n in notes):
            raise EditorError('ascolto: valori non validi')
        if not self.bridge_alive():
            raise EditorError('per ascoltare serve il bridge acceso, con l\'FM-1 collegato', 409)
        req = dict(t=track, notes=notes, vel=max(1, min(127, vel)), gate=max(1, min(100, round(gate_ms / 10))), tape=1 if tape else 0)
        p = os.path.join(self.control, 'bridge-preview.json')
        with open(p + '.part', 'w') as f:
            json.dump(req, f)
        os.replace(p + '.part', p)
        return dict(ok=True)

    # ---- the FM-1
    def bridge_alive(self):
        try:
            return time.time() - os.path.getmtime(os.path.join(self.control, 'bridge-alive')) < 3.0
        except OSError:
            return False

    def _ask_bridge(self, op, path, timeout=20.0):
        rid = '%d-%d' % (os.getpid(), int(time.time() * 1000))
        req = os.path.join(self.control, 'bridge-req.json')
        ans = os.path.join(self.control, 'bridge-ans-%s.json' % rid)
        with open(req + '.part', 'w') as f:
            json.dump(dict(id=rid, op=op, file=os.path.basename(path)), f)
        os.replace(req + '.part', req)
        end = time.time() + timeout
        while time.time() < end:
            if os.path.isfile(ans):
                with open(ans) as f:
                    a = json.load(f)
                try:
                    os.unlink(ans)
                except OSError:
                    pass
                if not a.get('ok'):
                    raise EditorError('FM-1: %s' % a.get('msg', 'non ha risposto'), 502)
                return a.get('msg', '')
            time.sleep(0.1)
        try:
            os.unlink(req)
        except OSError:
            pass
        raise EditorError('il bridge non ha risposto (l\'FM-1 è collegato e fermo?)', 504)

    def _one_shot(self, args, timeout=30):
        try:
            r = self.run([sys.executable, self.bridge] + args, capture_output=True, text=True, timeout=timeout)
        except Exception as e:
            raise EditorError('sagga_grid_bridge.py: %s' % e, 500)
        if r.returncode:
            raise EditorError('FM-1: %s' % ((r.stderr or r.stdout).strip() or 'errore %d' % r.returncode), 502)
        return (r.stdout or '').strip()

    def receive(self, name):
        """the FM-1's project (as it is now) into the library as `name` (over it, its old self into the versions). It
        comes into a file of its own first: only a project that reads back takes the name"""
        p = self.path(name)
        tmp = os.path.join(self.folder, '_dall-fm1-%d.sgq' % os.getpid())
        try:
            if self.bridge_alive():
                self._ask_bridge('export', tmp)
            else:
                self._one_shot(['--export', '--out', tmp])
            if not os.path.isfile(tmp):
                raise EditorError('l\'FM-1 non ha mandato il progetto', 502)
            try:
                _tool(['read', tmp])
            except EditorError as e:
                raise EditorError('quello che è arrivato dall\'FM-1 non è un progetto: %s' % e, 502)
            with open(tmp, 'rb') as f:
                data = f.read()
        finally:
            if os.path.exists(tmp):
                try:
                    self.writer.remove(tmp)
                except OSError:
                    pass
        if os.path.isfile(p):
            self._keep_version(p)
        self.writer.write(p, data)
        return self.read(name)

    def send(self, name):
        """a project of the library into the FM-1 (it replaces the project there; SAVE on the FM-1 keeps it)"""
        p = self._exists(name)
        if self.bridge_alive():
            return self._ask_bridge('import', p) or 'caricato sull\'FM-1'
        return self._one_shot(['--import', p]) or 'caricato sull\'FM-1'
