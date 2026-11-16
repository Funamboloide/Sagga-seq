#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA EDITOR (0.14): the converter built from the firmware's core (tools/sgqmid/sagga_sgqjson.c), the hub's editor
(tools/hub/sagga_editor.py: saves, versions, the FM-1 in and out through the grid bridge's Control or its one-shot
commands), the bridge's side of it, the page's lists against the panel's, and the page in a headless browser (playwright:
skipped without it). 0.15: the name, the GROOVE, the TAPE events, the positions and the previews (hub, bridge, page).

    python3 tests/sagga_editor_tests.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'hub'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tests'))
TOOL = os.path.join(ROOT, 'build', 'sagga_sgqjson')
MID = os.path.join(ROOT, 'build', 'sagga_sgqmid')
HW = os.path.join(ROOT, 'tools', 'hwtest', 'hwtest.sgq')
FAILS, CHECKS = [], [0]


def check(c, what):
    CHECKS[0] += 1
    if not c:
        FAILS.append(what)
        print('  FAIL:', what)


def group(name):
    print(name)


def build():
    src = [os.path.join(ROOT, 'firmware', 'src', f) for f in ('sagga_seq_core.c', 'sagga_beats.c')]
    os.makedirs(os.path.dirname(TOOL), exist_ok=True)
    subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-I' + os.path.join(ROOT, 'firmware', 'src'),
                    os.path.join(ROOT, 'tools', 'sgqmid', 'sagga_sgqjson.c')] + src + ['-o', TOOL], check=True)
    subprocess.run(['cc', '-std=c11', '-O2', '-I' + os.path.join(ROOT, 'firmware', 'src'),
                    os.path.join(ROOT, 'tools', 'sgqmid', 'sagga_sgqmid.c')] + src + ['-o', MID], check=True)
    os.environ['SAGGA_SGQJSON'] = TOOL


def tool(*args):
    return subprocess.run([TOOL] + list(args), capture_output=True, text=True)


def read(path):
    r = tool('read', path)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def apply(base, lines, out):
    d = tempfile.mkdtemp()
    p = os.path.join(d, 'patch.txt')
    with open(p, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    return tool('apply', base, p, out)


def t_converter():
    group('the converter (the firmware\'s core): read, a patch, sanitize, errors')
    d = tempfile.mkdtemp()
    j = read(HW)
    check(j['version'] == 1 and len(j['track']) == 16 and len(j['scene']) == 16 and len(j['lfo']) == 16 and len(j['song_e']) == 64,
          'read: the groups with their sizes')
    check(j['schema']['step']['dims'] == [16, 8, 64] and ['note', 1, 0, 4] in j['schema']['step']['fields'], 'the schema: the steps 16 x 8 x 64, note[4] (%s)' % j['schema']['step'])
    on = [s for s in j['steps'] if s[3]['flags'] & 1]
    check(len(on) >= 9 and j['step_default']['note'] == [60, 255, 255, 255], 'the steps that are not a new project\'s, sparse (%d on)' % len(on))
    check(len(j['names']['condition']) == 16 and j['names']['role'][1] == 'KICK' and len(j['names']['scale']) == 16, 'the core\'s names')
    out = os.path.join(d, 'same.sgq')
    r = apply(HW, [], out)
    j2 = read(out)
    check(r.returncode == 0 and {k: v for k, v in j2.items()} == j, 'an empty patch: the same project back')
    out2 = os.path.join(d, 'same2.sgq')
    apply(out, [], out2)
    check(open(out, 'rb').read() == open(out2, 'rb').read(), '... and once written, byte for byte the same again')
    r = apply(HW, ['project - bpm - 141', 'track 4 length - 32', 'track 4 division - 6', 'step 4,0,3 flags - 3', 'step 4,0,3 note 0 64',
                   'step 4,0,3 velocity - 90', 'step 4,1,63 lane 5 77', 'scene 2 pattern 15 7', 'song - len - 3', 'song_e 2 bars - 8',
                   'lfo 5 enabled - 1', 'lfox 5 trig - 2', 'chain 1 chain_on - 1', 'chain 1 chain_n - 3', 'live - mac 3 -20', 'ext - kb_mode - 2',
                   'key 3 shift - -5', '# a comment', ''], out)
    j3 = read(out)
    st = {(t, p, s): x for t, p, s, x in j3['steps']}
    check(r.returncode == 0 and j3['project']['bpm'] == 141 and j3['track'][4]['length'] == 32 and j3['track'][4]['division'] == 6,
          'a patch: project and track fields (%s)' % r.stderr)
    check(st.get((4, 0, 3), {}).get('note', [0])[0] == 64 and st[(4, 0, 3)]['velocity'] == 90 and st[(4, 0, 3)]['flags'] == 3 and st[(4, 1, 63)]['lane'][5] == 77,
          'a patch: steps, by track, pattern, step')
    check(j3['scene'][2]['pattern'][15] == 7 and j3['song']['len'] == 3 and j3['song_e'][2]['bars'] == 8 and j3['lfo'][5]['enabled'] == 1 and j3['lfox'][5]['trig'] == 2
          and j3['chain'][1]['chain_on'] == 1 and j3['chain'][1]['chain_n'] == 3 and j3['live']['mac'][3] == -20 and j3['ext']['kb_mode'] == 2 and j3['key'][3]['shift'] == -5,
          'a patch: scenes, song, LFOs, chains, macros, LIVE IN, keys, signed values')
    # 0.19: the MIDI FX chain of a track: HARM + ECHO with their values; the track's one effect is its first (HARM)
    r = apply(out, ['mfxc 3 on - 10', 'mfxc 3 amt 0 -3', 'mfxc 3 amt 2 4', 'mfxc 3 time 2 3', 'mfxc 3 fb 2 40', 'track 3 mfx - 4'], out2)
    j5 = read(out2)
    m3 = j5.get('mfxc', [{}] * 16)[3]
    check(r.returncode == 0 and m3.get('on') == 10 and m3.get('amt') == [-3, 1, 4, 3] and m3.get('time', [0] * 4)[2] == 3 and m3.get('fb', [0] * 4)[2] == 40
          and j5['track'][3]['mfx'] == 1 and j5['track'][3]['mfx_amt'] == -3,
          '0.19 the MIDI FX chain: mfxc on, amt / time / fb per effect; the track shows its first, whatever the patch said (%s %s)' % (m3, r.stderr))
    # 0.20: the new MIDI FX (CHANCE 40 % and GLITCH on), the order (GLITCH first), an envelope, a MOD slot; a broken
    # order (an effect twice) goes back to the default
    r = apply(out, ['mfxd 2 on - 17', 'mfxd 2 amt 0 40', 'mfxd 2 order 0 9', 'mfxd 2 order 7 7', 'mfxd 2 time 4 2',
                    'mfxd 5 order 0 3', 'lfoe 4 a - 3', 'lfoe 4 s - 70', 'mod 1 src - 6', 'mod 1 src_i - 21', 'mod 1 dst - 8', 'mod 1 dst_i - 2',
                    'mod 1 amt - -60', 'lfo 4 shape - 8', 'lfo 4 dest - 6'], out2)
    j6 = read(out2)
    m2, m5 = j6.get('mfxd', [{}] * 16)[2], j6.get('mfxd', [{}] * 16)[5]
    md, le = j6.get('mod', [{}] * 8)[1], j6.get('lfoe', [{}] * 16)[4]
    check(r.returncode == 0 and m2.get('on') == 17 and m2.get('amt', [0])[0] == 40 and m2.get('order') == [9, 5, 4, 6, 2, 1, 8, 7, 3]
          and m2.get('time', [0] * 5)[4] == 2 and m5.get('order') == [7, 5, 4, 6, 2, 1, 8, 9, 3],
          '0.20 mfxd: on, values, the order (a broken one back to the default) (%s %s %s)' % (m2, m5, r.stderr))
    check(md == {'src': 6, 'src_i': 21, 'dst': 8, 'dst_i': 2, 'amt': -60} and le.get('a') == 3 and le.get('s') == 70
          and j6['lfo'][4]['shape'] == 8 and j6['lfo'][4]['dest'] == 6,
          '0.20 the MOD MATRIX, an LFO\'s envelope, the ENV shape and MOD ONLY (%s %s %s)' % (md, le, j6['lfo'][4]))
    # what the FM-1 would play: the converter's step is a note for the firmware's own sgq2mid
    mid = os.path.join(d, 'x.mid')
    subprocess.run([MID, 'sgq2mid', out, mid], check=True, capture_output=True)
    import sagga_sgqmid_tests as G
    _, _, _, trs = G.read_smf(mid)
    t5 = [G.notes(e) for n, e in trs if n.startswith('T5 ')]
    check(t5 and any(n[2] == 64 and n[3] == 90 for n in t5[0]), 'the firmware\'s core plays the step written (T5: %s)' % (t5[0][:2] if t5 else trs))
    # sanitize: what the panel could never set is put right, not refused
    r = apply(HW, ['project - bpm - 900', 'track 0 length - 0', 'chain 0 chain_n - 9', 'step 0,0,0 ratchet - 40', 'ext - motion_bars - 3'], out)
    j4 = read(out)
    check(r.returncode == 0 and 30 <= j4['project']['bpm'] <= 300 and j4['track'][0]['length'] >= 1 and 1 <= j4['chain'][0]['chain_n'] <= 8
          and j4['ext']['motion_bars'] in (0, 1, 2, 4), 'out of range: the firmware\'s sanitize puts it right (bpm %d)' % j4['project']['bpm'])
    st0 = {(t, p, s): x for t, p, s, x in j4['steps']}
    check(st0.get((0, 0, 0), j4['step_default'])['ratchet'] <= 8, 'ratchet 40 -> at most 8')
    # errors: nothing written
    for bad, why in ((['nogroup - bpm - 1'], 'a group'), (['project - nofield - 1'], 'a field'), (['track 16 length - 4'], 'an index'),
                     (['step 0,0 flags - 1'], 'a step needs three'), (['track 0 length 0 4'], 'an element of a scalar'),
                     (['track 0 lane_cc 6 4'], 'an element past the array'), (['project - bpm - 70000'], 'a value past u16'),
                     (['live - mac 0 200'], 'a value past s8'), (['project - bpm'], 'four words'), (['project - bpm - x'], 'not a number')):
        o2 = os.path.join(d, 'bad.sgq')
        r = apply(HW, ['project - bpm - 99'] + bad, o2)
        check(r.returncode == 4 and not os.path.exists(o2) and 'line 2' in r.stderr, 'refused: %s (%s)' % (why, r.stderr.strip()))
    r = tool('new', os.path.join(d, 'n.sgq'))
    jn = read(os.path.join(d, 'n.sgq'))
    check(r.returncode == 0 and jn['steps'] == [] and jn['project']['bpm'] == 128 and jn['song']['len'] == 0, 'new: a blank project')
    r = apply('new', ['project - bpm - 100'], os.path.join(d, 'n2.sgq'))
    check(r.returncode == 0 and read(os.path.join(d, 'n2.sgq'))['project']['bpm'] == 100, 'apply over "new"')
    check(tool('read', os.path.join(ROOT, 'README.md')).returncode == 2, 'not a project: 2')


class DirWriter:
    """the hub's writer without a read-only partition"""
    def write(self, path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(data)
        return path

    def remove(self, path):
        os.unlink(path)


def t_editor_backend():
    group('the editor on the Pi: save over the file as it is, refuse a stale one, versions, new, names')
    import sagga_editor as E
    d = tempfile.mkdtemp()
    shutil.copy(HW, os.path.join(d, 'hw.sgq'))
    ed = E.Editor(d, DirWriter(), control=os.path.join(d, 'run'))
    j = ed.read('hw.sgq')
    j2 = ed.save('hw.sgq', [['project', '-', 'bpm', '-', 133], ['step', '2,0,5', 'flags', '-', 3], ['track', 2, 'swing', '-', 60]], j['rev'])
    st = {(t, p, s): x for t, p, s, x in j2['steps']}
    check(j2['project']['bpm'] == 133 and st[(2, 0, 5)]['flags'] == 3 and j2['track'][2]['swing'] == 60 and j2['rev'] != j['rev'], 'save: the changes in, a new rev')
    check(ed.versions('hw') and len(ed.versions('hw.sgq')) == 1, 'the file as it was is kept as a version (%s)' % ed.versions('hw'))
    try:
        ed.save('hw.sgq', [['project', '-', 'bpm', '-', 99]], j['rev'])
        check(False, 'a stale rev is refused')
    except E.EditorError as e:
        check(e.code == 409 and ed.read('hw.sgq')['project']['bpm'] == 133, 'saved meanwhile by someone else: 409, nothing written')
    for bad in ([['nope', '-', 'bpm', '-', 1]], [['project', '-', 'bpm', '-', '1']], [['project', 'x;rm', 'bpm', '-', 1]], [['project', '-', 'bpm', '-']],
                [['project', '-', 'Bpm Bpm', '-', 1]], [['step', '0,0,0', 'note', '-9', 1]], 'x'):
        try:
            ed.save('hw.sgq', bad)
            check(False, 'refused: %r' % (bad,))
        except E.EditorError as e:
            check(e.code == 400, 'a malformed change is refused before the converter (%r)' % (bad,))
    try:
        ed.save('hw.sgq', [['track', 99, 'length', '-', 4]])
        check(False, 'index 99')
    except E.EditorError as e:
        check(e.code == 400 and 'index' in str(e), 'the converter\'s refusal comes back (%s)' % e)
    time.sleep(1.1)
    ed.save('hw.sgq', [['project', '-', 'bpm', '-', 150]])
    v = ed.versions('hw.sgq')
    j3 = ed.restore('hw.sgq', v[-1])
    check(len(v) == 2 and j3['project']['bpm'] == 128, 'restore: the oldest version back (%s, bpm %d)' % (v, j3['project']['bpm']))
    check(len(ed.versions('hw.sgq')) == 3, 'and the one it replaced is a version too')
    n = ed.new('Nuovo pezzo')
    check(n['name'] == 'Nuovo pezzo.sgq' and n['steps'] == [] and os.path.isfile(os.path.join(d, 'Nuovo pezzo.sgq')), 'new: a blank project with that name')
    ed.new('../fuori')
    check(os.path.isfile(os.path.join(d, 'fuori.sgq')) and not os.path.exists(os.path.join(os.path.dirname(d), 'fuori.sgq')), 'a path in the name: only its last part, inside the library')
    for bad in ('', '.hidden', 'x' * 50, 'a*b', 'a;b'):
        try:
            ed.new(bad)
            check(False, 'name %r' % bad)
        except E.EditorError:
            check(True, '')
    try:
        ed.new('Nuovo pezzo')
        check(False, 'twice')
    except E.EditorError as e:
        check(e.code == 409, 'a name already there: 409')
    import sagga_grid_bridge as B
    check(len(B.library_files(d)) == 3, 'the versions do not show in the FM-1\'s library (%s)' % B.library_files(d))


def t_page_lists():
    group('the page\'s lists are the panel\'s (firmware/src)')
    page = open(os.path.join(ROOT, 'tools', 'hub', 'editor.html'), encoding='utf-8').read()
    src = open(os.path.join(ROOT, 'firmware', 'src', 'dinghy.c')).read() + open(os.path.join(ROOT, 'firmware', 'src', 'sagga_ui.c')).read()

    def js(name):
        m = re.search(r"const %s = \[([^\]]*)\]" % name, page)
        return re.findall(r"'([^']*)'", m.group(1)) if m else None

    def c(anchor, after=0):
        i = src.index(anchor, after)
        return re.findall(r'"([^"]*)"', src[i:src.index('};', i)])
    for name, anchor in (('DIV', 'static const char *div_name'), ('DIR', 'static const char *dir_name'), ('ARPM', 'static const char *chord_name'),
                         ('SHAPES', 'static const char *lfo_shape_name'), ('RATES', 'static const char *lfo_rate_name'),
                         ('DESTS', 'static const char *lfo_dest_name'), ('QUANT', 'QUANT_NAME[SQ_QUANTS] =')):
        check(js(name) == c(anchor), '%s as the panel\'s (%s / %s)' % (name, js(name), c(anchor)))
    check(js('MFX') == c('static const char *const MFX_NAME[SQ_MFXS]'), 'MFX as the panel\'s')
    check(js('VOICE') == c('static const char *const VN[SQ_VOICES]'), 'VOICE as the panel\'s')


class FakeBridge:
    """the grid bridge's loop with its Library and Control, and an FM-1 that answers exports and takes imports"""
    def __init__(self, lib_dir, ctl_dir, image):
        import sagga_grid_bridge as B
        import sagga_bridge_tests as BT
        self.B, self.fm, self.image, self.stop = B, BT.FakeFM1(), image, False
        self.inbox = []
        self.lib = B.Library(lib_dir, self.send, writer=DirWriter(), log=lambda t: None)
        self.ctl = B.Control(self.lib, folder=ctl_dir, log=lambda t: None)

    def send(self, msg):
        msg = list(msg)
        if self.B.sx_cmd(msg) == self.B.SX_EXPORT:
            self.inbox += self.B.dump_frames(self.image)
        else:
            self.fm.rx(msg)
            self.inbox += self.fm.replies
            self.fm.replies = []

    def run(self):
        t0 = time.monotonic()
        while not self.stop:
            now = time.monotonic() - t0
            while self.inbox:
                self.lib.fm1_sysex(self.inbox.pop(0), now)
            self.lib.tick(now)
            self.ctl.tick(now)
            time.sleep(0.005)


def t_fm1_in_out():
    group('the FM-1 in and out: through the running bridge (Control), else its one-shot commands')
    import sagga_editor as E
    d = tempfile.mkdtemp()
    lib, ctl = os.path.join(d, 'lib'), os.path.join(d, 'run')
    os.makedirs(lib)
    shutil.copy(HW, os.path.join(lib, 'hw.sgq'))
    ed = E.Editor(lib, DirWriter(), control=ctl)
    check(not ed.bridge_alive(), 'no bridge: not alive')
    fm_image = open(HW, 'rb').read()
    j = ed.read('hw.sgq')
    ed.save('hw.sgq', [['project', '-', 'bpm', '-', 97]], j['rev'])
    fb = FakeBridge(lib, ctl, fm_image)
    th = threading.Thread(target=fb.run, daemon=True)
    th.start()
    time.sleep(0.3)
    try:
        check(ed.bridge_alive(), 'the bridge says it is alive')
        msg = ed.send('hw.sgq')
        check(fb.fm.project is not None and fb.fm.project == open(os.path.join(lib, 'hw.sgq'), 'rb').read() and 'FM-1' in msg,
              'send: the file goes to the FM-1 whole, through the bridge (%s)' % msg)
        j2 = ed.receive('dal-fm1.sgq')
        check(j2['name'] == 'dal-fm1.sgq' and open(os.path.join(lib, 'dal-fm1.sgq'), 'rb').read() == fm_image, 'receive: the FM-1\'s project into the library as that name')
        check(sorted(x for x in os.listdir(lib) if x.endswith('.sgq')) == ['dal-fm1.sgq', 'hw.sgq'], 'and only that file: the bridge did not save another (%s)' % os.listdir(lib))
        j3 = ed.receive('hw.sgq')
        check(j3['project']['bpm'] == 128 and len(ed.versions('hw.sgq')) == 2, 'receive over a file: it is replaced, the old one kept as a version')
        fb.fm.playing = True
        try:
            ed.send('hw.sgq')
            check(False, 'busy')
        except E.EditorError as e:
            check(e.code == 502 and 'busy' in str(e), 'a playing FM-1: the page hears why (%s)' % e)
        fb.fm.playing = False
        fb.image = b'XXXX' + bytes(30)
        try:
            ed.receive('rotto.sgq')
            check(False, 'not a project')
        except E.EditorError as e:
            check(e.code == 502 and not os.path.exists(os.path.join(lib, 'rotto.sgq')) and not [x for x in os.listdir(lib) if x.startswith('_dall')],
                  'an export that is not a project: refused, nothing left (%s)' % e)
    finally:
        fb.stop = True
        th.join(1)
    time.sleep(3.2)
    check(not ed.bridge_alive(), 'the bridge gone: not alive after 3 s')
    calls = []

    def run(cmd, **kw):
        calls.append(cmd[2:])
        if '--export' in cmd:
            shutil.copy(HW, cmd[-1])
        return type('R', (), {'returncode': 0, 'stdout': 'ok', 'stderr': ''})()
    ed2 = E.Editor(lib, DirWriter(), control=ctl, run=run, bridge='/opt/sagga/sagga_grid_bridge.py')
    ed2.send('hw.sgq')
    ed2.receive('uno.sgq')
    check(calls[0] == ['--import', os.path.join(lib, 'hw.sgq')] and calls[1][:2] == ['--export', '--out'] and os.path.dirname(calls[1][2]) == lib
          and open(os.path.join(lib, 'uno.sgq'), 'rb').read() == open(HW, 'rb').read() and not [x for x in os.listdir(lib) if x.startswith('_dall')],
          'no bridge: sagga_grid_bridge.py --import / --export --out (%s)' % calls)


def t_page():
    group('the page in a browser: a step on, its velocity, a lane drawn, the song, a chain, saved; undo; no script errors')
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print('  (skipped: no playwright)')
        return
    import sagga_fw as FW
    d = tempfile.mkdtemp()
    fw, pr = os.path.join(d, 'fw'), os.path.join(d, 'pr')
    os.makedirs(fw)
    os.makedirs(pr)
    shutil.copy(HW, os.path.join(pr, 'hw.sgq'))
    state = FW.State(fw, pr, writer=FW.BootWriter(fw, mounts=lambda: [('/', ['rw'])]))
    state.editor.control = os.path.join(d, 'run')
    srv = FW.ThreadingHTTPServer(('127.0.0.1', 0), FW.make_handler(state))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={'width': 1300, 'height': 900})
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('dialog', lambda dg: dg.accept())
            home = pg.goto('http://127.0.0.1:%d/' % port)
            pg.wait_for_timeout(500)
            check('/edit/hw.sgq' in pg.content(), 'the library links each project to the editor')
            pg.goto('http://127.0.0.1:%d/edit/hw.sgq' % port)
            pg.wait_for_timeout(800)
            check((pg.text_content('#status') or '').startswith('aperto'), 'it opens (%s)' % pg.text_content('#status'))
            pg.evaluate("V.toggle=true;V.pat=0;V.tab='tracce';render()")
            pg.click('.c[data-ts="4,6"]')
            pg.wait_for_timeout(100)
            check(pg.evaluate('getStep(4,0,6).flags') & 3 == 3 and pg.evaluate('getStep(4,0,6).note[0]') == pg.evaluate('P.track[4].pen'), 'a tap turns a step on with the track\'s PEN note')
            pg.fill('input[data-g="step"][data-f="velocity"]', '77')
            pg.press('input[data-g="step"][data-f="velocity"]', 'Tab')
            pg.select_option('select[data-g="step"][data-f="condition"]', '1')
            check(pg.evaluate('getStep(4,0,6).velocity') == 77 and pg.evaluate('getStep(4,0,6).condition') == 1 and pg.evaluate('changes.size') == 3, 'the step panel: velocity, condition (%d changes)' % pg.evaluate('changes.size'))
            pg.click('.c[data-ts="4,7"]')
            pg.keyboard.press('Control+z')
            check(pg.evaluate('getStep(4,0,7).flags') & 1 == 0, 'Ctrl+Z takes the last tap back')
            pg.evaluate("V.tab='lane';V.t=4;V.lane=1;V.erase=false;render()")
            bars = pg.query_selector_all('#lane .b')
            box = bars[2].bounding_box()
            pg.mouse.move(box['x'] + 5, box['y'] + box['height'] * 0.25)
            pg.mouse.down()
            box5 = bars[5].bounding_box()
            pg.mouse.move(box5['x'] + 5, box5['y'] + box5['height'] * 0.25, steps=6)
            pg.mouse.up()
            lv = pg.evaluate('[2,3,4,5].map(s=>getStep(4,0,s).lane[1])')
            check(all(90 <= v <= 100 for v in lv), 'a drag over the lane draws the locks (%s)' % lv)
            pg.evaluate("V.tab='song';render()")
            pg.click('text=+ voce')
            pg.click('text=+ voce')
            pg.evaluate("V.tab='catene';render()")
            pg.select_option('select[data-g="chain"][data-i="3"][data-f="mode"]', '2')
            pg.evaluate("V.tab='lfo';render()")
            pg.select_option('select[data-g="lfox"][data-i="0"][data-f="trig"]', '1')
            pg.select_option('select[data-g="lfo"][data-i="0"][data-f="rate"]', '18')
            pg.evaluate("V.tab='progetto';render()")
            pg.fill('input[data-g="project"][data-f="bpm"]', '174')
            pg.press('input[data-g="project"][data-f="bpm"]', 'Tab')
            pg.select_option('select[data-g="key"][data-f="cur"]', '2')
            pg.select_option('select[data-g="key"][data-i="2"][data-f="scale"]', '2')
            n = pg.evaluate('changes.size')
            pg.click('#bsave')
            pg.wait_for_timeout(1200)
            stt = pg.text_content('#status') or ''
            check(stt.startswith('salvato: hw.sgq (%d modifiche' % n) and pg.evaluate('changes.size') == 0, 'Save: %s' % stt)
            check(not errs, 'no script errors (%s)' % errs)
            # every tab renders
            for tb in ('tracce', 'traccia', 'lane', 'scene', 'song', 'catene', 'lfo', 'progetto'):
                pg.evaluate("V.tab='%s';render()" % tb)
            check(not errs, 'every tab renders (%s)' % errs)
            b.close()
    finally:
        srv.shutdown()
    j = read(os.path.join(pr, 'hw.sgq'))
    st = {(t, p, s): x for t, p, s, x in j['steps']}
    s6 = st.get((4, 0, 6), {})
    check(s6.get('flags', 0) & 1 and s6.get('velocity') == 77 and s6.get('condition') == 1, 'in the file: the step on, velocity 77, condition 1:2 (%s)' % s6)
    check(all(90 <= st.get((4, 0, s), j['step_default'])['lane'][1] <= 100 for s in (2, 3, 4, 5)), 'in the file: the lane\'s locks')
    check(j['song']['len'] == 2 and j['chain'][3]['chain_on'] == 1 and j['lfox'][0]['trig'] == 1 and j['lfo'][0]['rate'] == 18 and j['project']['bpm'] == 174,
          'in the file: the song, the chain list, TRIG, a triplet rate, the tempo')
    check(j['project']['key_cur'] == 2 and j['key'][2]['scale'] == 2 and j['project']['key_scale'] == 2, 'in the file: the key slot that plays, and the project\'s key with it')


# ------------------------------------------------------------------------------------------------ 0.15
def t015_converter():
    group('0.15 the converter: the name, the GROOVE, the TAPE events and their loop')
    d = tempfile.mkdtemp()
    out = os.path.join(d, 'a.sgq')
    name = [ord(c) for c in 'Notte è'] + [0] * 9
    lines = ['ext - name %d %d' % (i, v) for i, v in enumerate(name[:16])]
    lines += ['chain 2 groove - 3', 'chain 2 groove_amt - 60', 'chain 3 groove - 40', 'chain 4 groove_amt - 140',
              'track 5 flags - 32', 'track 5 tape_bars - 2', 'track 5 tape_quant - 30',
              'tape 5 clear - 0', 'tape 5,768,96,64 add - 90', 'tape 5,0,192,60 add - 100', 'tape 5,5000,10,62 add - 80', 'tape 6,10,20,30 add - 40']
    r = apply('new', lines, out)
    j = read(out)
    nm = ''.join(chr(c) for c in j['ext']['name'] if c)
    check(r.returncode == 0 and nm == 'NOTTE _', 'the name: upper case, a character the FM-1 cannot draw becomes _ (%r %s)' % (nm, r.stderr))
    check(j['chain'][2]['groove'] == 3 and j['chain'][2]['groove_amt'] == 60 and j['chain'][3]['groove'] == 0 and j['chain'][4]['groove_amt'] == 100,
          'the GROOVE: template and amount; out of range put right (%s)' % [j['chain'][k] for k in (2, 3, 4)])
    check(j['names']['groove'][:4] == ['OFF', 'HOUSE', 'GARAGE', 'DILLA'] and len(j['names']['groove']) == 10, 'the core\'s GROOVE names (%s)' % j['names']['groove'])
    check(j['track'][5]['tape_bars'] == 2 and j['track'][5]['tape_quant'] == 30 and j['tape_len'][5] == 2 * 1536, 'the tape\'s loop: bars, quantise, its length in ticks')
    check(j['tape'] == [[5, 0, 192, 60, 100], [5, 768, 96, 64, 90], [6, 10, 20, 30, 40]] and j['tape_cnt'][5] == 2 and j['tape_n'] == 3,
          'the events: sorted, one past the 2-bar loop dropped (%s)' % j['tape'])
    out2 = os.path.join(d, 'b.sgq')
    r = apply(out, ['tape 5 clear - 0', 'tape 5,96,48,67 add - 70'], out2)
    j2 = read(out2)
    check(r.returncode == 0 and j2['tape'] == [[5, 96, 48, 67, 70], [6, 10, 20, 30, 40]], 'a track\'s events written again: the others as they were (%s)' % j2['tape'])
    # the image is the FM-1's: sgq2mid plays the tape note where it was written
    mid = os.path.join(d, 'b.mid')
    subprocess.run([MID, 'sgq2mid', out2, mid], check=True, capture_output=True)
    import sagga_sgqmid_tests as G
    _, _, _, trs = G.read_smf(mid)
    t6 = [G.notes(e) for n, e in trs if n.startswith('T6 ')]
    check(t6 and any(n[2] == 67 and n[3] == 70 for n in t6[0]), 'the firmware\'s core plays the tape note written (T6: %s)' % (t6[0][:2] if t6 else [n for n, _ in trs]))
    for bad, why in ((['tape 5 add - 1'], 'add needs the event'), (['tape 16 clear - 0'], 'a track past 16'), (['tape 5,0,0,60 add - 100'], 'a length 0'),
                     (['tape 5,0,96,128 add - 100'], 'a note past 127'), (['tape 5,0,96,60 add - 0'], 'velocity 0'),
                     (['tape 5,30000,96,60 add - 9'], 'past 16 bars'), (['tape 5 wipe - 0'], 'not clear / add'), (['tape 5,0,96 add - 9'], 'three numbers')):
        o3 = os.path.join(d, 'bad.sgq')
        r = apply(out, ['project - bpm - 99'] + bad, o3)
        check(r.returncode == 4 and not os.path.exists(o3) and 'line 2' in r.stderr, 'refused: %s (%s)' % (why, r.stderr.strip()))
    # full: 1536 events in all
    lines = ['tape 0,%d,10,60 add - 100' % (i % 6000) for i in range(1537)]
    r = apply('new', ['track 0 tape_bars - 16'] + lines, os.path.join(d, 'full.sgq'))
    check(r.returncode == 4 and 'full' in r.stderr, 'more than the tape holds: refused (%s)' % r.stderr.strip())


def t015_backend():
    group('0.15 the editor on the Pi: a new project named after its file; the tape lines; positions and previews through the bridge\'s files')
    import sagga_editor as E
    d = tempfile.mkdtemp()
    ctl = os.path.join(d, 'run')
    os.makedirs(ctl)
    ed = E.Editor(d, DirWriter(), control=ctl)
    n = ed.new('Notte in citta')
    nm = ''.join(chr(c) for c in n['ext']['name'] if c)
    check(nm == 'NOTTE IN CITTA', 'Nuovo: the project takes its file\'s name (%r)' % nm)
    check(E.project_name('a-very-long-name-for-a-song.sgq') == 'A-VERY-LONG-NAME' and E.project_name('  x*y  ') == 'X_Y' and E.project_name('ÀÉÎ.sgq') == 'AEI',
          'the name as the FM-1 shows it: 16, upper case, accents dropped, others _ (%s)' % E.project_name('a-very-long-name-for-a-song.sgq'))
    j = ed.save('Notte in citta.sgq', [['track', 2, 'flags', '-', 32], ['tape', '2', 'clear', '-', 0], ['tape', '2,0,96,60', 'add', '-', 100],
                                       ['tape', '2,384,96,62', 'add', '-', 90], ['chain', 1, 'groove', '-', 5]], n['rev'])
    check(j['tape'] == [[2, 0, 96, 60, 100], [2, 384, 96, 62, 90]] and j['chain'][1]['groove'] == 5, 'save: the tape events and a GROOVE (%s)' % j['tape'])
    for bad in ([['tape', '2;rm', 'clear', '-', 0]], [['tape', '2', 'add', '-', 1]], [['tape', '2,0,96,60', 'add', '1', 100]],
                [['tape', '2,0,96,60', 'move', '-', 100]], [['tape', '2,0,96,60', 'add', '-', '100']], [['tape', '123456,0,1,1', 'add', '-', 1]]):
        try:
            ed.save('Notte in citta.sgq', bad)
            check(False, 'refused %r' % bad)
        except E.EditorError as e:
            check(e.code == 400, 'a malformed tape change is refused (%r)' % (bad,))
    # positions: the page's wish (pos-want), the bridge's file (pos.json)
    p0 = ed.pos()
    check(p0['bridge'] is False and p0['fresh'] is False and os.path.isfile(os.path.join(ctl, 'pos-want')), 'no bridge, no position; the wish is written (%s)' % p0)
    with open(os.path.join(ctl, 'pos.json'), 'w') as f:
        json.dump(dict(playing=1, scene=2, song=-1, clock=480, bpm=124, steps=list(range(16)), pats=[0] * 16), f)
    with open(os.path.join(ctl, 'bridge-alive'), 'w') as f:
        f.write('1\n')
    p1 = ed.pos()
    check(p1['bridge'] and p1['fresh'] and p1['bpm'] == 124 and p1['steps'][3] == 3 and p1['age'] < 1, 'a fresh position comes back as it is (%s)' % p1)
    old = time.time() - 10
    os.utime(os.path.join(ctl, 'pos.json'), (old, old))
    check(not ed.pos()['fresh'], 'a position 10 s old while "playing": not fresh (the FM-1 stopped talking)')
    r = ed.preview(3, [60, 64, 67], 90, 300)
    req = json.load(open(os.path.join(ctl, 'bridge-preview.json')))
    check(r['ok'] and req == dict(t=3, notes=[60, 64, 67], vel=90, gate=30, tape=0), 'a preview: a file for the bridge (%s)' % req)
    for bad in ((16, [60]), (0, []), (0, [128]), ('x', [60])):
        try:
            ed.preview(*bad)
            check(False, 'preview %r' % (bad,))
        except E.EditorError as e:
            check(e.code == 400, 'a bad preview is refused (%r)' % (bad,))
    os.unlink(os.path.join(ctl, 'bridge-alive'))
    try:
        ed.preview(0, [60])
        check(False, 'no bridge')
    except E.EditorError as e:
        check(e.code == 409 and 'bridge' in str(e), 'no bridge: the page is told (%s)' % e)


def t015_bridge():
    group('0.15 the bridge: asks the FM-1 for positions while the page wants them, writes them, sends the previews')
    import sagga_grid_bridge as B
    d = tempfile.mkdtemp()
    sent = []
    lib = type('L', (), {'send': lambda self, m: sent.append(list(m)), 'sender': None})()
    ctl = B.Control(lib, folder=d, log=lambda t: None)
    ctl.tick(0.0)
    check(not [m for m in sent if m[4:5] == [0x30]], 'nobody watching: no positions asked')
    with open(os.path.join(d, 'pos-want'), 'w') as f:
        f.write('1\n')
    ctl.tick(1.0); ctl.tick(1.2); ctl.tick(3.5)
    subs = [m for m in sent if m[:5] == [0xF0, 0x7D, 0x53, 0x47, 0x30]]
    check(subs == [[0xF0, 0x7D, 0x53, 0x47, 0x30, 1, 0xF7]] * 2, 'a page watching: 30 01, again every 2 s (%s)' % subs)
    pos = [0xF0, 0x7D, 0x53, 0x47, 0x31, 1, 3, 127] + B.put7(1000, 3) + B.put7(132, 2)
    for t in range(16):
        pos += [t * 2, t % 8]
    pos.append(0xF7)
    check(ctl.fm1_sysex(pos, 4.0) and not ctl.fm1_sysex([0xF0, 0x7D, 0x53, 0x47, 0x21, 0, 0, 0xF7], 4.0), 'a position is the Control\'s, a library frame is not')
    j = json.load(open(os.path.join(d, 'pos.json')))
    check(j['playing'] == 1 and j['scene'] == 3 and j['song'] == -1 and j['clock'] == 1000 and j['bpm'] == 132 and j['steps'][5] == 10 and j['pats'][9] == 1,
          'pos.json: what the frame says (%s)' % {k: j[k] for k in ('playing', 'scene', 'song', 'clock', 'bpm')})
    old = time.time() - 30
    os.utime(os.path.join(d, 'pos-want'), (old, old))
    del sent[:]
    ctl.tick(5.0)
    check(sent == [[0xF0, 0x7D, 0x53, 0x47, 0x30, 0, 0xF7]], 'the page gone: 30 00 once (%s)' % sent)
    ctl.tick(6.0)
    check(len(sent) == 1, '... and nothing more')
    with open(os.path.join(d, 'bridge-preview.json'), 'w') as f:
        json.dump(dict(t=4, notes=[60, 67], vel=80, gate=25, tape=1), f)
    ctl.tick(6.1)
    check(sent[-1] == [0xF0, 0x7D, 0x53, 0x47, 0x32, 4, 80, 25, 1, 2, 60, 67, 0xF7] and not os.path.exists(os.path.join(d, 'bridge-preview.json')),
          'a preview file: the PREVIEW frame, the file gone (%s)' % sent[-1:])
    check(B.preview_frame(dict(t=16, notes=[60])) is None and B.preview_frame(dict(t=0, notes=[])) is None and B.preview_frame(dict(t=0, notes=[200])) is None
          and B.preview_frame('x') is None and B.preview_frame(dict(t=0, notes=[1, 2, 3, 4, 5, 6]))[9] == 4, 'a preview that is not one: no frame; 4 notes at most')


def t015_page():
    group('0.15 the page: the name, the GROOVE, a TAPE track (mode, notes added, moved, taken away), saved; it follows the FM-1, it plays what is touched')
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print('  (skipped: no playwright)')
        return
    import sagga_fw as FW
    d = tempfile.mkdtemp()
    fw, pr, ctl = os.path.join(d, 'fw'), os.path.join(d, 'pr'), os.path.join(d, 'run')
    for x in (fw, pr, ctl):
        os.makedirs(x)
    shutil.copy(HW, os.path.join(pr, 'hw.sgq'))
    state = FW.State(fw, pr, writer=FW.BootWriter(fw, mounts=lambda: [('/', ['rw'])]))
    state.editor.control = ctl
    srv = FW.ThreadingHTTPServer(('127.0.0.1', 0), FW.make_handler(state))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def alive():
        with open(os.path.join(ctl, 'bridge-alive'), 'w') as f:
            f.write('1\n')
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={'width': 1300, 'height': 900})
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('dialog', lambda dg: dg.accept())
            pg.add_init_script("localStorage.clear()")
            pg.goto('http://127.0.0.1:%d/edit/hw.sgq' % port)
            pg.wait_for_timeout(800)
            # the name
            pg.evaluate("V.tab='progetto';render()")
            pg.fill('#pnm', 'Il mio pezzo è qui!')
            pg.press('#pnm', 'Tab')
            check(pg.evaluate('projName()') == 'IL MIO PEZZO E Q' and 'IL MIO PEZZO E Q' in (pg.text_content('#pname') or ''), 'the name: as the FM-1 shows it (%r)' % pg.evaluate('projName()'))
            # GROOVE on a step track, TAPE on another
            pg.evaluate("V.tab='traccia';V.t=1;render()")
            pg.select_option('select[data-g="chain"][data-i="1"][data-f="groove"]', '3')
            check(pg.evaluate("get('chain','1','groove_amt','-')") == 100, 'a GROOVE chosen at 0 %: all of it (as HOME 7 K3)')
            pg.fill('input[data-g="chain"][data-i="1"][data-f="groove_amt"]', '70')
            pg.press('input[data-g="chain"][data-i="1"][data-f="groove_amt"]', 'Tab')
            pg.evaluate("V.t=5;render()")
            pg.select_option('select[data-g="track"][data-i="5"][data-f="mode"]', '3')
            check(pg.evaluate("P.track[5].flags & 0x63") == 0x20, 'the mode TAPE: the TAPE bit (%#x)' % pg.evaluate("P.track[5].flags"))
            check(pg.query_selector('select[data-g="track"][data-i="5"][data-f="tape_bars"]') is not None and pg.query_selector('select[data-g="chain"][data-i="5"][data-f="groove"]') is None,
                  'a TAPE track: its loop instead of the GROOVE')
            pg.select_option('select[data-g="track"][data-i="5"][data-f="tape_bars"]', '2')
            pg.evaluate("V.tab='tape';V.tt=5;V.snap=true;V.zoom=14;V.listen=false;render()")
            Z = pg.evaluate('V.rz')
            check(Z >= 14 and Z * 32 <= 1300, 'a 2-bar loop fills the width (%s px a 16th)' % Z)
            box = pg.query_selector('#roll').bounding_box()
            hi = pg.evaluate('V.rhi')
            pg.mouse.click(box['x'] + Z * 4 + 3, box['y'] + (hi - 60) * 10 + 4)             # a C4 on the 5th 16th
            check(pg.evaluate('evs(5)') == [[384, 96, 60, 100]], 'a tap on the roll: a note on the grid (%s)' % pg.evaluate('evs(5)'))
            nb = pg.query_selector('.rn[data-i="0"]').bounding_box()
            pg.mouse.move(nb['x'] + 4, nb['y'] + 4)
            pg.mouse.down()
            pg.mouse.move(nb['x'] + 4 + Z * 2, nb['y'] + 4 - 20, steps=5)
            pg.mouse.up()
            check(pg.evaluate('evs(5)') == [[576, 96, 62, 100]], 'dragged: two 16ths later, two notes up (%s)' % pg.evaluate('evs(5)'))
            nb = pg.query_selector('.rn[data-i="0"]').bounding_box()
            pg.mouse.move(nb['x'] + nb['width'] - 2, nb['y'] + 4)
            pg.mouse.down()
            pg.mouse.move(nb['x'] + nb['width'] - 2 + Z * 3, nb['y'] + 4, steps=5)
            pg.mouse.up()
            check(pg.evaluate('evs(5)[0][1]') == 384, 'its right edge dragged: longer (%s)' % pg.evaluate('evs(5)'))
            pg.mouse.click(box['x'] + 3, box['y'] + (hi - 64) * 10 + 4)
            check(len(pg.evaluate('evs(5)')) == 2 and pg.evaluate('V.tsel') == 0, 'another note, chosen')
            pg.keyboard.press('Delete')
            check(pg.evaluate('evs(5)') == [[576, 384, 62, 100]], 'Delete takes the chosen note away (%s)' % pg.evaluate('evs(5)'))
            pg.keyboard.press('Control+z')
            check(len(pg.evaluate('evs(5)')) == 2, 'Ctrl+Z brings it back')
            pg.keyboard.press('Control+z')
            pg.evaluate("V.tsel=0;render()")
            pg.fill('input[onchange^="tapeEdit(3"]', '77')
            pg.press('input[onchange^="tapeEdit(3"]', 'Tab')
            check(pg.evaluate('evs(5)') == [[576, 384, 62, 77]], 'the chosen note\'s velocity typed (%s)' % pg.evaluate('evs(5)'))
            pg.click('#bsave')
            pg.wait_for_timeout(1200)
            stt = pg.text_content('#status') or ''
            check(stt.startswith('salvato') and pg.evaluate('changes.size') == 0 and pg.evaluate('evs(5)') == [[576, 384, 62, 77]], 'saved and read back (%s)' % stt)
            # it follows the FM-1: the bridge's position paints the step that plays
            alive()
            with open(os.path.join(ctl, 'pos.json'), 'w') as f:
                json.dump(dict(playing=1, scene=0, song=-1, clock=6 * 9, bpm=124, steps=[6] * 16, pats=[0] * 4 + [1] + [0] * 11), f)
            pg.evaluate("V.tab='tracce';V.pat=0;render()")
            pg.check('#follow')
            pg.wait_for_timeout(500)
            check(pg.evaluate("document.querySelector('.c[data-ts=\"2,6\"]').classList.contains('ph')") and not pg.query_selector('.c.ph[data-ts="4,6"]'),
                  'the step that plays is marked, where the track plays the pattern shown')
            check((pg.text_content('#pp4') or '') == '▶P2' and (pg.text_content('#pos') or '').startswith('▶ 124 BPM'), 'a track on another pattern says which; the tempo (%s / %s)' % (pg.text_content('#pp4'), pg.text_content('#pos')))
            check(os.path.isfile(os.path.join(ctl, 'pos-want')), 'the page asks for positions (pos-want)')
            pg.evaluate("V.tab='tape';V.tt=5;render()")
            pg.wait_for_timeout(400)
            left = pg.evaluate("parseFloat($('rph').style.left)")
            check(pg.evaluate("$('rph').style.display") == 'block' and abs(left - 9 * Z) < 0.5, 'the TAPE roll: the line where the loop is (%s px)' % left)
            pg.uncheck('#follow')
            pg.wait_for_timeout(300)
            check(pg.evaluate("$('rph').style.display") == 'none', 'not following: no line')
            # it plays what is touched
            alive()
            pg.evaluate("V.tab='tracce';V.toggle=true;V.listen=true;V.pat=0;render()")
            pg.click('.c[data-ts="2,9"]')
            pg.wait_for_timeout(400)
            req = json.load(open(os.path.join(ctl, 'bridge-preview.json')))
            check(req['t'] == 2 and req['notes'] == [pg.evaluate('P.track[2].pen')] and req['tape'] == 0, 'a step turned on: the FM-1 is asked to play it (%s)' % req)
            os.unlink(os.path.join(ctl, 'bridge-preview.json'))
            pg.evaluate("V.tab='tape';V.tt=5;V.tsel=0;render()")
            pg.click('text=♪ ascolta')
            pg.wait_for_timeout(400)
            req = json.load(open(os.path.join(ctl, 'bridge-preview.json')))
            check(req == dict(t=5, notes=[62], vel=77, gate=25, tape=1), 'a TAPE note: played as the tape plays it (%s)' % req)
            for tb in ('tracce', 'traccia', 'lane', 'tape', 'scene', 'song', 'catene', 'lfo', 'progetto'):
                pg.evaluate("V.tab='%s';render()" % tb)
            check(not errs, 'no script errors (%s)' % errs)
            b.close()
    finally:
        srv.shutdown()
    j = read(os.path.join(pr, 'hw.sgq'))
    nm = ''.join(chr(c) for c in j['ext']['name'] if c)
    check(nm == 'IL MIO PEZZO E Q' and j['chain'][1]['groove'] == 3 and j['chain'][1]['groove_amt'] == 70, 'in the file: the name, the GROOVE (%r)' % nm)
    check(j['track'][5]['flags'] & 0x20 and j['track'][5]['tape_bars'] == 2 and [e for e in j['tape'] if e[0] == 5] == [[5, 576, 384, 62, 77]],
          'in the file: T6 a TAPE track of 2 bars with its note (%s)' % [e for e in j['tape'] if e[0] == 5])


def main():
    build()
    for t in (t_converter, t_editor_backend, t_page_lists, t_fm1_in_out, t_page, t015_converter, t015_backend, t015_bridge, t015_page):
        try:
            t()
        except Exception as e:
            import traceback
            traceback.print_exc()
            FAILS.append('%s raised %r' % (t.__name__, e))
    print('sagga editor: %d checks, %d failures' % (CHECKS[0], len(FAILS)))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
