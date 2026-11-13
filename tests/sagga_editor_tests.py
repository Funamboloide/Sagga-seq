#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA EDITOR (0.14): the converter built from the firmware's core (tools/sgqmid/sagga_sgqjson.c), the hub's editor
(tools/hub/sagga_editor.py: saves, versions, the FM-1 in and out through the grid bridge's Control or its one-shot
commands), the bridge's side of it, the page's lists against the panel's, and the page in a headless browser (playwright:
skipped without it).

    python3 tests/sagga_editor_tests.py
"""
import io
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
    check(js('MFX') == c('static const char *const MF[SQ_MFXS]'), 'MFX as the panel\'s')
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


def main():
    build()
    for t in (t_converter, t_editor_backend, t_page_lists, t_fm1_in_out, t_page):
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
