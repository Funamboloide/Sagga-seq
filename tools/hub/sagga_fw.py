#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA HUB: the firmware library, a small web page on the Pi (port 8090).

It keeps the FM-1 packages (.fwsc) in a folder, shows which firmware the connected FM-1 runs, installs the one you
pick (fm1_install.py over USB-MIDI, through the hub), takes new packages by upload, and lists the projects the grid
bridge exported (.sgq) for download. 0.13: BREAK, a drum loop (WAV) cut into slices for a sampler (sagga_slicer.py),
back as a zip. 0.20.1: a package away (Elimina), and the Pi updates itself from a sagga-hub-X.zip uploaded here
(checked, unpacked in /run, install_hub.sh run in a unit of its own: it restarts this page). 0.20.3: the ESPLORATORE
DEL BANCO (sagga_banco.py, in a unit of its own too): the matrix checked, the FM-1, the pages and the grid tested
together; its log here, its files to download. Standard library only.

    sudo python3 sagga_fw.py [--dir /boot/firmware/sagga/firmware] [--projects /boot/firmware/sagga] [--port 8090]
"""
import argparse
import email.parser
import email.policy
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import contextlib
import tempfile
import threading
import time
import urllib.parse
import zipfile
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
try:
    import sagga_celle                                                           # noqa: E402  (0.20.9: the FM-1's cells kept)
except ImportError:                                                              # (never the page down for it)
    sagga_celle = None
EDITOR = os.path.join(HERE, 'editor.html')                                       # 0.14: its page
UPDATE_DIR = os.environ.get('SAGGA_UPDATE_DIR', '/run/sagga-update')              # 0.20.1: the Pi's update (tmpfs: gone at reboot)
SYSTEMD_RUN = shutil.which('systemd-run')                                        # 0.20.1: the installer outside this service
HUB_TOP_RE = re.compile(r'^sagga-hub-([0-9][0-9A-Za-z.\-]*)$')
HUB_NEEDS = ('install_hub.sh', 'hub/sagga_fw.py', 'hub/sagga-fw.service', 'fm1_install.py', 'sagga_grid_bridge.py')
GUARD = 'X-Sagga-Hub'          # 0.20.1: the page's own requests carry it (a form of another site cannot: no CSRF)
BANCO = os.path.join(HERE, 'sagga_banco.py')                                    # 0.20.3: the banco's explorer
BANCO_DIR = os.environ.get('SAGGA_BANCO_DIR', '/run/sagga-banco')               # ... its log and files (tmpfs)
BANCO_FILE_RE = re.compile(r'^(raccolta-banco-[0-9-]+\.json|RAPPORTO-BANCO-[0-9-]+\.md|banco-[0-9-]+\.log|banco\.out)$')


def hub_version():
    """0.20.1: the version install_hub.sh wrote next to this file ('' before 0.20.1)"""
    try:
        with open(os.path.join(HERE, 'VERSION')) as f:
            return f.read().strip()[:32]
    except OSError:
        return ''


def pc_enabled():
    """0.20.1: is the PC port's service on here (install_hub.sh without --no-pc)? An update keeps what is there"""
    try:
        return subprocess.run(['systemctl', 'is-enabled', '--quiet', 'sagga-pc-link'], timeout=5).returncode == 0
    except Exception:
        return False


class UpdateError(Exception):
    def __init__(self, msg, code=400):
        Exception.__init__(self, msg)
        self.code = code


def check_hub_zip(data, limit=64 * 1024 * 1024):
    """0.20.1: a sagga-hub zip as make_release.sh makes it -> (ZipFile, top folder, version), or UpdateError saying
    what is wrong: one folder sagga-hub-X, no path out of it, no links, the files install_hub.sh needs, a page that
    is Python (a broken one would take this page, and with it the next update, away) and still has the update (an
    older hub would leave the Pi updatable by SSH only)"""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        infos = z.infolist()
    except (zipfile.BadZipFile, ValueError, OSError):
        raise UpdateError('non è uno zip')
    if not infos or len(infos) > 4000:
        raise UpdateError('uno zip vuoto o con troppi file')
    tops, names, total = set(), set(), 0
    for i in infos:
        n = i.filename
        if n.startswith('/') or '\\' in n or ':' in n or any(part == '..' for part in n.split('/')):
            raise UpdateError('un percorso fuori dalla cartella: %s' % n)
        if (i.external_attr >> 16) & 0o170000 == 0o120000:
            raise UpdateError('un collegamento (symlink): %s' % n)
        if i.flag_bits & 0x1:
            raise UpdateError('uno zip con la password')
        tops.add(n.split('/')[0])
        names.add(n)
        total += i.file_size
    if len(tops) != 1:
        raise UpdateError('lo zip deve avere una cartella sola, sagga-hub-X (ne ha %d)' % len(tops))
    top = tops.pop()
    m = HUB_TOP_RE.match(top)
    if not m:
        raise UpdateError('la cartella si chiama %s: serve sagga-hub-X (lo zip del Pi, non il sorgente)' % top)
    if total > limit:
        raise UpdateError('troppo grande, aperto: %d MB' % (total >> 20))
    for need in HUB_NEEDS:
        if top + '/' + need not in names:
            raise UpdateError('manca %s' % need)
    try:
        if not z.read(top + '/install_hub.sh').startswith(b'#!/bin/sh'):
            raise UpdateError('install_hub.sh non è lo script del hub')
        page = z.read(top + '/hub/sagga_fw.py')
        compile(page, 'sagga_fw.py', 'exec')
        if b"'/api/update'" not in page:
            raise UpdateError('la pagina di questo zip non sa aggiornarsi (prima della 0.20.1): dopo, il Pi si '
                              'aggiornerebbe solo da SSH. Se lo vuoi davvero, installalo da SSH')
    except SyntaxError as e:
        raise UpdateError('hub/sagga_fw.py non è Python valido (riga %s)' % e.lineno)
    except (zipfile.BadZipFile, RuntimeError, OSError, ValueError) as e:
        raise UpdateError('lo zip è rovinato: %s' % e)
    return z, top, m.group(1)


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
    def __init__(self, fw_dir, proj_dir, writer=None, pat_writer=None, upd_dir=None, banco_dir=None):
        self.fw_dir, self.proj_dir = fw_dir, proj_dir
        self.upd_dir = upd_dir or UPDATE_DIR                # 0.20.1: the Pi's update (its log survives this page's restart)
        self.banco_dir = banco_dir or BANCO_DIR             # 0.20.3: the banco's explorer
        self.writer = writer or BootWriter(fw_dir)
        self.keeper = None                                  # 0.20.9: the keeper of the FM-1's cells (main starts it)
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
        """an install running, or the banco's explorer (0.20.3: it holds the FM-1 the whole time)"""
        return (self.proc is not None and self.proc.poll() is None) or self.banco_running()

    # ---- 0.20.3 the ESPLORATORE DEL BANCO: sagga_banco.py in a unit of its own (it survives this page's restarts);
    # its state from its files: banco.json (pid, rc), banco-<ts>.log
    def _bfile(self, name):
        return os.path.join(self.banco_dir, name)

    def banco_cells(self):
        return os.path.join(self.proj_dir, 'banco', 'celle-staccate.json')

    def _banco_meta(self):
        try:
            with open(self._bfile('banco.json')) as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def banco_running(self):
        m = self._banco_meta()
        if not m or m.get('rc') is not None:
            return False
        pid = m.get('pid')
        if not pid:
            return time.time() - m.get('started', 0) < 20         # (started, not yet written its own pid)
        try:
            os.kill(int(pid), 0)
            return True
        except (OSError, ValueError):
            return False

    def banco_files(self):
        out = []
        for folder, where in ((self.banco_dir, 'run'), (os.path.join(self.proj_dir, 'banco'), 'sd')):
            try:
                for n in sorted(os.listdir(folder), reverse=True):
                    if BANCO_FILE_RE.match(n) and not any(x['name'] == n for x in out):
                        out.append(dict(name=n, size=os.path.getsize(os.path.join(folder, n)), where=where))
            except OSError:
                pass
        return out[:12]

    def banco_file(self, name):
        """the path of a file of the banco's (the newest copy), or None"""
        name = os.path.basename(name or '')
        if not BANCO_FILE_RE.match(name):
            return None
        for folder in (self.banco_dir, os.path.join(self.proj_dir, 'banco')):
            p = os.path.join(folder, name)
            if os.path.isfile(p):
                return p
        return None

    def banco_status(self):
        m = self._banco_meta()
        running = self.banco_running()
        log = []
        if m:
            p = self._bfile('banco-%s.log' % m.get('quando', '')) if m.get('quando') else None
            if not p or not os.path.isfile(p):
                p = self._bfile('banco.out')
            try:
                with open(p, encoding='utf-8', errors='replace') as f:
                    log = [ln[-220:] for ln in f.read().splitlines()[-80:]]
            except OSError:
                pass
            if not running and m.get('rc') is not None and not m.get('copiati'):
                self._banco_keep(m)
        return dict(running=running, modo=(m or {}).get('modo'), piano=(m or {}).get('piano'), rc=None if running or not m else m.get('rc'),
                    quando=(m or {}).get('quando'), log=log, files=self.banco_files(),
                    celle=os.path.isfile(self.banco_cells()) and not running,
                    ask=running and bool(log) and log[-1].startswith('>>>'))

    def _banco_keep(self, m):
        """the run's files also on the SD card (/run goes at a reboot): the newest three runs kept"""
        try:
            m['copiati'] = True
            with open(self._bfile('banco.json'), 'w') as f:
                json.dump(m, f)
            q = m.get('quando', '')
            keep = os.path.join(self.proj_dir, 'banco')
            for n in ('raccolta-banco-%s.json' % q, 'RAPPORTO-BANCO-%s.md' % q, 'banco-%s.log' % q):
                src = self._bfile(n)
                if os.path.isfile(src):
                    with open(src, 'rb') as f:
                        self.writer.write(os.path.join(keep, n), f.read())
            runs = sorted({re.sub(r'^.*?([0-9]{8}-[0-9]{6}).*$', r'\1', n) for n in os.listdir(keep) if BANCO_FILE_RE.match(n)})
            for old in runs[:-3]:
                for n in os.listdir(keep):
                    if old in n and BANCO_FILE_RE.match(n):
                        self.writer.remove(os.path.join(keep, n))
        except Exception:
            pass

    def start_banco(self, modo, stacca=True, sessioni=0, piano='banco'):
        """0.20.3: the banco's explorer: 'matrice' (only the matrix), 'prova' (everything), 'rimetti' (the cells a prova
        took away, back) -> None, or (message, HTTP code). piano: 'banco' (the pages, the grid, the panel along the real
        roads) or 'fm1' (the whole FM-1: the PC explorer's sessions, every situation, from the Pi)"""
        if modo not in ('matrice', 'prova', 'rimetti') or piano not in ('banco', 'fm1'):
            return 'modo sconosciuto', 400
        if not os.path.isfile(BANCO):
            return "l'esploratore del banco non e' installato (aggiorna il Pi)", 404
        plan = os.path.join(os.path.dirname(BANCO), '%s_piano.json' % piano)
        if modo == 'prova' and not os.path.isfile(plan):
            return "il piano %s non c'e' (aggiorna il Pi)" % os.path.basename(plan), 404
        with self.lock:
            if self.banco_running():
                return "l'esploratore del banco sta gia' andando", 409
            if self.proc is not None and self.proc.poll() is None:
                return "l'FM-1 si sta installando: aspetta che finisca", 409
            if (self.update_status() or {}).get('running'):
                return 'il Pi si sta aggiornando', 409
            os.makedirs(self.banco_dir, exist_ok=True)
            cmd = [sys.executable, '-u', BANCO, '--out', self.banco_dir, '--celle', self.banco_cells()]
            if modo == 'matrice':
                cmd.append('--solo-matrice')
            elif modo == 'rimetti':
                cmd.append('--rimetti')
            else:
                cmd += ['--piano', plan]
                if not stacca:
                    cmd.append('--non-staccare')
                if sessioni:
                    cmd += ['--sessioni', str(int(sessioni))]
            with open(self._bfile('banco.json'), 'w') as f:
                json.dump(dict(pid=None, started=time.time(), rc=None, modo=modo, piano=piano), f)
            out = self._bfile('banco.out')
            script = '%s >>%s 2>&1' % (' '.join(shlex.quote(x) for x in cmd), shlex.quote(out))
            with open(out, 'w') as f:
                f.write('%s\n' % ' '.join(cmd))
            started = False
            if SYSTEMD_RUN:
                try:
                    r = subprocess.run([SYSTEMD_RUN, '--unit', 'sagga-banco-%d' % int(time.time()), '--collect', '--quiet',
                                        '/bin/sh', '-c', script], capture_output=True, text=True, timeout=20)
                    started = r.returncode == 0
                except Exception:
                    started = False
            if not started:
                subprocess.Popen(['/bin/sh', '-c', script], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True)
        return None

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
            if self.banco_running():
                return "l'esploratore del banco sta usando l'FM-1"
            if self.busy():
                return 'an install is running'
            if (self.update_status() or {}).get('running'):
                return 'the Pi is updating'                  # 0.20.1: the update restarts this page, and the install with it
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

    def delete_package(self, name):
        """0.20.1: a package of the library away -> None, or (message, HTTP code)"""
        name = os.path.basename(name or '')
        path = os.path.join(self.fw_dir, name)
        if not name.lower().endswith('.fwsc') or not os.path.isfile(path):
            return 'no such package', 404
        with self.lock:
            if self.busy() and self.job == name:
                return 'si sta installando: aspetta che finisca', 409
            try:
                self.writer.remove(path)
            except OSError as e:
                return 'non riesco a cancellarlo: %s' % e, 500
        return None

    def _upd(self, name):
        return os.path.join(self.upd_dir, name)

    def update_status(self):
        """0.20.1: the last update of the Pi (from its files: this process may be the one the update started), or None"""
        try:
            with open(self._upd('update.log'), encoding='utf-8', errors='replace') as f:
                lines = f.read().splitlines()
        except OSError:
            return None
        try:
            with open(self._upd('update.json')) as f:
                meta = json.load(f)
        except (OSError, ValueError):
            meta = {}
        rc = None
        for ln in reversed(lines[-6:]):
            m = re.match(r'^exit (\d+)$', ln.strip())
            if m:
                rc = int(m.group(1))
                break
        started = meta.get('started', 0)
        return dict(version=meta.get('version', ''), name=meta.get('name', ''), started=started, rc=rc,
                    running=rc is None and time.time() - started < 900, log=[ln[-200:] for ln in lines[-80:]])

    def start_update(self, filename, data, pc=None):
        """0.20.1: a sagga-hub zip -> checked, unpacked, install_hub.sh started in a unit of its own (it restarts this
        service, which would kill a child of ours); returns the version, or raises UpdateError"""
        with self.lock:
            if self.banco_running():
                raise UpdateError("l'esploratore del banco sta andando: aggiorna il Pi quando ha finito", 409)
            if self.busy():
                raise UpdateError("l'FM-1 si sta installando: aggiorna il Pi quando ha finito", 409)
            if (self.update_status() or {}).get('running'):
                raise UpdateError('un aggiornamento è già in corso', 409)
            z, top, ver = check_hub_zip(data)
            os.makedirs(self.upd_dir, exist_ok=True)
            for n in os.listdir(self.upd_dir):                # the stages of the updates before
                if n.startswith('stage-'):
                    shutil.rmtree(self._upd(n), ignore_errors=True)
            stage = tempfile.mkdtemp(prefix='stage-', dir=self.upd_dir)
            try:
                z.extractall(stage)
            except (zipfile.BadZipFile, OSError, RuntimeError) as e:
                shutil.rmtree(stage, ignore_errors=True)
                raise UpdateError('non riesco ad aprirlo: %s' % e, 500)
            pc = pc_enabled() if pc is None else pc
            log = self._upd('update.log')
            with open(log, 'w') as f:
                f.write('update %s from %s (%s)\n' % (ver, os.path.basename(filename or '?'),
                                                       'with the PC port' if pc else '--no-pc: no PC port on this Pi'))
            with open(self._upd('update.json'), 'w') as f:
                json.dump(dict(version=ver, name=os.path.basename(filename or ''), started=time.time()), f)
            script = '{ cd %s && SAGGA_DETACHED=1 sh ./install_hub.sh%s; echo "exit $?"; cd /; rm -rf %s; } >>%s 2>&1' % (
                shlex.quote(os.path.join(stage, top)), '' if pc else ' --no-pc', shlex.quote(stage), shlex.quote(log))
            started = False
            if SYSTEMD_RUN:
                try:
                    r = subprocess.run([SYSTEMD_RUN, '--unit', 'sagga-update-%d' % int(time.time()), '--collect', '--quiet',
                                        '/bin/sh', '-c', script], capture_output=True, text=True, timeout=20)
                    started = r.returncode == 0
                    if not started:
                        with open(log, 'a') as f:
                            f.write('systemd-run: %s\n' % (r.stderr or r.stdout).strip()[-300:])
                except Exception as e:
                    with open(log, 'a') as f:
                        f.write('systemd-run: %s\n' % e)
            if not started:                                     # no systemd here: a session of its own
                subprocess.Popen(['/bin/sh', '-c', script], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True)
        return ver

    def keeper_status(self):
        """0.20.9: what the keeper of the FM-1's cells did lately, how many it remembers (None: not running)"""
        k = self.keeper
        if k is None:
            return None
        return dict(events=[list(e) for e in k.events[-6:]], cells=len(k.mem), waiting=self.banco_running())

    def snapshot(self):
        return dict(packages=self.packages(), projects=self.projects(), busy=self.busy(), job=self.job,
                    result=self.result, log=self.log[-60:], device=self.probe(), version=hub_version(),
                    update=self.update_status(), banco=self.banco_status(), celle=self.keeper_status())


PAGE = r'''<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SAGGA HUB</title><style>
body{font:16px/1.4 system-ui,sans-serif;margin:0;background:#111;color:#eee}header{background:#222;padding:12px 16px;font-weight:700;letter-spacing:.08em}
main{padding:12px 16px;max-width:720px;margin:auto}h2{font-size:14px;letter-spacing:.1em;color:#9cf;margin:20px 0 8px}
.row{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid #333}
button{background:#2a6;color:#fff;border:0;border-radius:6px;padding:8px 14px;font-size:15px}button[disabled]{background:#444}
.dev{background:#1a2a3a;border-radius:8px;padding:10px 12px}.mono{font-family:ui-monospace,monospace;font-size:13px;overflow-wrap:anywhere;min-width:0}
pre{background:#000;color:#9f9;padding:10px;border-radius:8px;max-height:260px;overflow:auto;font-size:12px}small{color:#999}
input[type=file]{color:#ccc}a{color:#9cf}button.del{background:#833}header small{color:#9cf;font-weight:400;margin-left:6px}</style></head><body>
<header>SAGGA HUB<small id="ver"></small></header><main>
<h2>FM-1</h2><div class="dev" id="dev">...</div>
<h2>FIRMWARE</h2><div id="pk"></div>
<form id="up" method="post" action="/api/upload" enctype="multipart/form-data" class="row"><input type="file" name="f" accept=".fwsc" required><button>Carica</button></form>
<h2>INSTALLAZIONE</h2><pre id="log"></pre>
<h2>AGGIORNA IL PI</h2><div id="ust"></div>
<div class="row" style="flex-wrap:wrap"><input type="file" id="hz" accept=".zip"><button id="ub" onclick="upd()">Aggiorna il Pi</button><small id="um"></small></div>
<small>Uno zip <b>sagga-hub-X.zip</b>, di quelli che prepara Claude: il Pi lo controlla, lo installa da solo (install_hub.sh, come da SSH) e riavvia le sue pagine; questa sparisce per qualche secondo e torna con la versione nuova in alto. Lo pu&ograve; fare chi &egrave; sulla rete del Pi: la password del WiFi &egrave; la chiave.</small>
<pre id="ulog" style="display:none"></pre>
<h2>ESPLORATORE DEL BANCO</h2><div id="bst"></div>
<div class="row"><button id="bm" onclick="banco('matrice')">Controlla la matrice</button><button id="bp" onclick="banco('prova')">Avvia la prova</button>
<select id="bk"><option value="banco">il banco: pagine, grid, pannello</option><option value="fm1">l'FM-1 completo: ogni situazione</option></select>
<select id="bn"><option value="0">tutte le sessioni</option><option value="4">4 sessioni (5 minuti)</option></select>
<label><input type="checkbox" id="bs" checked> <small>stacca i synth</small></label><button id="br" class="del" style="display:none" onclick="banco('rimetti')">Rimetti le celle</button></div>
<div class="dev" id="bsel" style="display:none"><b>Sull'FM-1: premi SEL per dire s&igrave;</b> <small>(20 secondi; un altro tasto = no)</small></div>
<pre id="blog" style="display:none"></pre><div id="bf"></div>
<small><b>Il banco</b> (20 minuti circa): l'FM-1 (SAGGA SEQ 0.20.3), il Pi e il grid insieme, per le strade vere: le sei pagine SAGGA premute dentro RaspiMIDIHub, il bridge del grid con due Launchpad finti, il pannello dell'FM-1 con il suo test. Prima controlla la matrice; durante la prova le celle fra l'FM-1 e i synth sono staccate (i synth tacciono) e tornano alla fine; l'FM-1 si riavvia a ogni sessione, non toccarlo. Alla fine il tuo progetto torna in memoria (sull'FM-1: IMPORTED, SAVE per tenerlo). <b>L'FM-1 completo</b> (mezz'ora circa): l'esploratore dal PC, fatto dal Pi: ogni situazione, 60 gesti a sessione sul pannello, il tablet e il grid come eventi del test. Mandami la <b>raccolta-banco</b>: la confronto con il simulatore.</small>
<h2>LE CELLE DELL'FM-1</h2><div id="kc"></div>
<small>RaspiMIDIHub perde le celle dell'FM-1 se fa il suo salvataggio automatico mentre l'FM-1 &egrave; spento o si riavvia. Il Pi le ricorda e, quando l'FM-1 torna, rimette quelle che mancano (con i loro filtri). Una cella che togli con l'FM-1 acceso resta tolta; con l'FM-1 spento torna. Una pagina SAGGA aggiunta in RaspiMIDIHub viene collegata alla porta 2 dell'FM-1 da sola, una volta (con USB PORTS 2).</small>
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
async function tick(){let s;try{s=await (await fetch('/api/state')).json();}catch(e){document.getElementById('dev').innerHTML='<small>il Pi non risponde (le sue pagine si stanno riavviando?)</small>';return;}
document.getElementById('ver').textContent=s.version||'';
const u=s.update,upd_on=!!(u&&u.running);document.getElementById('ub').disabled=upd_on||s.busy;
document.getElementById('ust').innerHTML=!u?'<small>nessun aggiornamento da quando il Pi &egrave; acceso</small>':u.running?`<b>aggiornamento ${h(u.version)} in corso</b> <small>(la pagina sparisce qualche secondo e torna)</small>`:u.rc===0?`<b>aggiornato a ${h(u.version)}</b>`:u.rc===null?`<b>aggiornamento ${h(u.version)} interrotto</b> <small>(il Pi si &egrave; spento? rifallo)</small>`:`<b>aggiornamento ${h(u.version)} non riuscito</b> <small>(exit ${u.rc}: il log qui sotto)</small>`;
const ul=document.getElementById('ulog');ul.style.display=u?'':'none';ul.textContent=u?u.log.join('\n'):'';
const b=s.banco||{},bon=!!b.running;['bm','bp'].forEach(i=>document.getElementById(i).disabled=bon||s.busy||upd_on);
document.getElementById('ub').disabled=upd_on||s.busy;document.getElementById('br').style.display=b.celle?'':'none';
document.getElementById('bst').innerHTML=bon?`<b>${b.modo=='matrice'?'controllo della matrice':b.modo=='rimetti'?'rimetto le celle':b.piano=='fm1'?'FM-1 completo':'prova del banco'} in corso</b> <small>(non toccare l'FM-1)</small>`:b.rc===0?`<b>finito</b> <small>${h(b.quando||'')}</small>`:b.rc!=null?`<b>finito con qualcosa da guardare</b> <small>(exit ${b.rc}: il log qui sotto)</small>`:b.celle?'<b>celle staccate da una prova interrotta</b> <small>(Rimetti le celle)</small>':'<small>mai fatto da quando il Pi &egrave; acceso</small>';
document.getElementById('bsel').style.display=b.ask?'':'none';
const kc=s.celle;document.getElementById('kc').innerHTML=!kc?'<small>il custode non gira</small>':(kc.waiting?'<small>aspetta: la prova del banco tiene l\'FM-1</small><br>':'')+(kc.events.length?kc.events.map(e=>`<div class="row"><span>${h(e[1])}</span><small>${h(e[0])}</small></div>`).join(''):`<small>${kc.cells} celle ricordate, nessuna persa da quando il Pi &egrave; acceso</small>`);
const bl=document.getElementById('blog');bl.style.display=b.log&&b.log.length?'':'none';const atEnd=bl.scrollTop+bl.clientHeight>=bl.scrollHeight-20;bl.textContent=(b.log||[]).join('\n');if(atEnd)bl.scrollTop=bl.scrollHeight;
document.getElementById('bf').innerHTML=(b.files||[]).map(f=>`<div class="row"><a class="mono" href="/banco/${encodeURIComponent(f.name)}">${h(f.name)}</a><small>${(f.size/1024).toFixed(0)} KB${f.where=='sd'?' (sulla SD)':''}</small></div>`).join('');
document.getElementById('dev').innerHTML=s.device?`<b>${h(s.device[0])}</b> <small>[${h(s.device[1])}] ${h(s.device[2])}</small>`:'<small>nessun FM-1 risponde (cavo? un altro programma lo usa?)</small>';
document.getElementById('pk').innerHTML=s.packages.map(p=>`<div class="row"><span class="mono">${h(p.name)} <small>${(p.size/1024).toFixed(0)} KB</small></span><span><button ${s.busy||upd_on?'disabled':''} data-n="${h(p.name)}" onclick="inst(this.dataset.n)">Installa</button> <button class="del" ${s.busy&&s.job==p.name?'disabled':''} data-n="${h(p.name)}" onclick="pkdel(this.dataset.n)">Elimina</button></span></div>`).join('')||'<small>nessun pacchetto: carica un .fwsc</small>';
document.getElementById('log').textContent=(s.job?`[${s.job}] `:'')+s.log.join('\n');
function npost(u){const n=document.getElementById('np').value.trim(),m=document.getElementById('npm');if(!n){m.textContent='scrivi un nome';return null;}m.textContent='...';return fetch(u+'?file='+encodeURIComponent(n),{method:'POST'}).then(async r=>{if(!r.ok){m.textContent=await r.text();return null;}const d=await r.json();location.href='/edit/'+encodeURIComponent(d.name);});}
function newp(){npost('/api/project/new');}
function recv(){npost('/api/fm1/receive');}
document.getElementById('pr').innerHTML=s.projects.map(p=>`<div class="row"><a class="mono" href="/projects/${encodeURIComponent(p.name)}">${h(p.name)}</a><span><a href="/projects/${encodeURIComponent(p.name.replace(/\.sgq$/i,''))}.mid"><small>.mid</small></a> <a href="/edit/${encodeURIComponent(p.name)}"><small><b>editor</b></small></a> <a href="/roll/${encodeURIComponent(p.name)}"><small>piano roll</small></a> <small>${new Date(p.mtime*1000).toLocaleString()}</small></span></div>`).join('')||'<small>nessun progetto esportato</small>';}
async function inst(n){if(!confirm('Installare '+n+' sull\'FM-1? Non spegnere durante la scrittura.'))return;const r=await fetch('/api/install?file='+encodeURIComponent(n),{method:'POST'});if(!r.ok){const d=await r.json().catch(()=>({}));alert(d.error||'non parte');}tick();}
async function pkdel(n){if(!confirm('Cancellare '+n+' dalla libreria del Pi? (Il firmware che l\'FM-1 ha adesso non cambia.)'))return;const r=await fetch('/api/package/delete?file='+encodeURIComponent(n),{method:'POST',headers:{'X-Sagga-Hub':'1'}});if(!r.ok)alert(await r.text());tick();}
async function upd(){const f=document.getElementById('hz').files[0],m=document.getElementById('um');if(!f){m.textContent='scegli lo zip sagga-hub-...';return;}
if(!confirm('Aggiornare il Pi con '+f.name+'? Le sue pagine si riavviano: qualche secondo.'))return;
m.textContent='carico...';const fd=new FormData();fd.append('f',f,f.name);
try{const r=await fetch('/api/update',{method:'POST',body:fd,headers:{'X-Sagga-Hub':'1'}});m.textContent=r.ok?'':await r.text();if(r.ok)document.getElementById('hz').value='';}catch(e){m.textContent='non arriva al Pi: '+e;}tick();}
async function banco(m){const st=document.getElementById('bs').checked,n=document.getElementById('bn').value,k=document.getElementById('bk').value;
const q=m=='prova'?'Avviare '+(k=='fm1'?'l\'FM-1 completo':'la prova del banco')+'? Dura '+(n=='4'?'5':k=='fm1'?'30':'20')+' minuti circa: l\'FM-1 si riavvia a ogni sessione, non toccarlo. Il tuo progetto torna in memoria alla fine.'+(st?' I synth tacciono (le loro celle tornano alla fine).':' I synth restano collegati: suoneranno.'):m=='rimetti'?'Rimettere nella matrice le celle staccate?':null;
if(q&&!confirm(q))return;
const r=await fetch('/api/banco?modo='+m+'&stacca='+(st?1:0)+'&sessioni='+n+'&piano='+k,{method:'POST',headers:{'X-Sagga-Hub':'1'}});if(!r.ok)alert(await r.text());tick();}
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
            if u.path == '/api/pos':                              # 0.15: where the FM-1 is (the editor follows it)
                return self.send(200, json.dumps(state.editor.pos()), 'application/json')
            if u.path.startswith('/banco/'):                     # 0.20.3: a file of the banco's explorer
                p = state.banco_file(urllib.parse.unquote(u.path[len('/banco/'):]))
                if p:
                    with open(p, 'rb') as f:
                        ctype = 'application/json' if p.endswith('.json') else 'text/plain; charset=utf-8'
                        return self.send(200, f.read(), ctype, {'Content-Disposition': 'attachment; filename="%s"' % os.path.basename(p)})
                return self.send(404, 'no such file', 'text/plain')
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
            if u.path in ('/api/update', '/api/package/delete', '/api/banco') and self.headers.get(GUARD) != '1':
                return self.send(403, 'solo dalla pagina del hub', 'text/plain; charset=utf-8')
            if u.path == '/api/banco':                            # 0.20.3: the banco's explorer starts
                q = urllib.parse.parse_qs(u.query)
                try:
                    n = max(0, min(200, int(q.get('sessioni', ['0'])[0] or 0)))
                except ValueError:
                    n = 0
                err = state.start_banco(q.get('modo', [''])[0], stacca=q.get('stacca', ['1'])[0] != '0', sessioni=n,
                                        piano=q.get('piano', ['banco'])[0])
                if err:
                    return self.send(err[1], err[0], 'text/plain; charset=utf-8')
                return self.send(200, json.dumps(dict(ok=True)), 'application/json')
            if u.path.startswith('/api/fm1/') and state.banco_running():   # (it holds the FM-1)
                return self.send(409, "l'esploratore del banco sta usando l'FM-1: aspetta che finisca", 'text/plain; charset=utf-8')
            if u.path == '/api/package/delete':                   # 0.20.1: a package of the library away
                q = urllib.parse.parse_qs(u.query)
                err = state.delete_package(q.get('file', [''])[0])
                if err:
                    return self.send(err[1], err[0], 'text/plain; charset=utf-8')
                return self.send(200, json.dumps(dict(ok=True)), 'application/json')
            if u.path == '/api/update':                           # 0.20.1: the Pi updates itself from a sagga-hub zip
                n = int(self.headers.get('Content-Length', '0') or 0)
                if n <= 0 or n > 32 * 1024 * 1024:
                    return self.send(400, 'upload vuoto o troppo grande', 'text/plain; charset=utf-8')
                name, data = multipart_file(self.headers.get('Content-Type', ''), self.rfile.read(n))
                if not name or not data:
                    return self.send(400, 'serve lo zip sagga-hub-X.zip', 'text/plain; charset=utf-8')
                try:
                    ver = state.start_update(name, data)
                except UpdateError as e:
                    return self.send(e.code, str(e), 'text/plain; charset=utf-8')
                except OSError as e:
                    return self.send(500, 'non riesco: %s' % e, 'text/plain; charset=utf-8')
                return self.send(200, json.dumps(dict(ok=True, version=ver)), 'application/json')
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
                    elif u.path == '/api/fm1/preview':           # 0.15: the FM-1 plays what the page touched
                        try:
                            req = json.loads(body.decode('utf-8') or '{}')
                        except ValueError:
                            return self.send(400, 'JSON non valido', 'text/plain; charset=utf-8')
                        out = ed.preview(req.get('t'), req.get('notes') or [], req.get('vel', 100), req.get('gate', 250), req.get('tape'))
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
    ap.add_argument('--hub', default='http://127.0.0.1', help="RaspiMIDIHub's API (the keeper of the FM-1's cells)")
    ap.add_argument('--senza-custode', action='store_true', help="the FM-1's cells are not kept")
    a = ap.parse_args(argv)
    state = State(a.dir, a.projects)
    if not a.senza_custode and sagga_celle is not None:    # 0.20.9: the FM-1's cells RaspiMIDIHub loses, put back
        state.keeper = sagga_celle.Keeper(sagga_celle.HubAPI(a.hub), path=os.path.join(a.projects, 'celle-fm1.json'),
                                          write=state.writer.write, say=lambda t: print('celle:', t, file=sys.stderr, flush=True))
        threading.Thread(target=sagga_celle.run_forever, args=(state.keeper, state.banco_running), daemon=True).start()
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
