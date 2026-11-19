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
    check(j['version'] == 1 and len(j['track']) == 12 and len(j['scene']) == 16 and len(j['lfo']) == 16 and len(j['song_e']) == 64,
          'read: the groups with their sizes (0.28: twelve tracks)')
    check(j['schema']['step']['dims'] == [12, 8, 64] and ['note', 1, 0, 6] in j['schema']['step']['fields'] and ['lane', 1, 0, 8] in j['schema']['step']['fields']
          and ['lane_cc', 1, 0, 8] in j['schema']['track']['fields'], 'the schema: the steps 12 x 8 x 64, note[6], lane[8]; a track\'s lane_cc[8] (%s)' % j['schema']['step'])
    on = [s for s in j['steps'] if s[3]['flags'] & 1]
    check(len(on) >= 9 and j['step_default']['note'] == [60, 255, 255, 255, 255, 255] and j['step_default']['lane'] == [255] * 8,
          'the steps that are not a new project\'s, sparse (%d on)' % len(on))
    check(len(j['names']['condition']) == 16 and j['names']['role'][1] == 'KICK' and len(j['names']['scale']) == 16, 'the core\'s names')
    out = os.path.join(d, 'same.sgq')
    r = apply(HW, [], out)
    j2 = read(out)
    check(r.returncode == 0 and {k: v for k, v in j2.items()} == j, 'an empty patch: the same project back')
    out2 = os.path.join(d, 'same2.sgq')
    apply(out, [], out2)
    check(open(out, 'rb').read() == open(out2, 'rb').read(), '... and once written, byte for byte the same again')
    r = apply(HW, ['project - bpm - 141', 'track 4 length - 32', 'track 4 division - 6', 'step 4,0,3 flags - 3', 'step 4,0,3 note 0 64',
                   'step 4,0,3 velocity - 90', 'step 4,1,63 lane 5 77', 'scene 2 pattern 11 7', 'song - len - 3', 'song_e 2 bars - 8',
                   'lfo 5 enabled - 1', 'lfox 5 trig - 2', 'chain 1 chain_on - 1', 'chain 1 chain_n - 3', 'live - mac 3 -20', 'ext - kb_mode - 2',
                   'key 3 shift - -5', '# a comment', ''], out)
    j3 = read(out)
    st = {(t, p, s): x for t, p, s, x in j3['steps']}
    check(r.returncode == 0 and j3['project']['bpm'] == 141 and j3['track'][4]['length'] == 32 and j3['track'][4]['division'] == 6,
          'a patch: project and track fields (%s)' % r.stderr)
    check(st.get((4, 0, 3), {}).get('note', [0])[0] == 64 and st[(4, 0, 3)]['velocity'] == 90 and st[(4, 0, 3)]['flags'] == 3 and st[(4, 1, 63)]['lane'][5] == 77,
          'a patch: steps, by track, pattern, step')
    check(j3['scene'][2]['pattern'][11] == 7 and j3['song']['len'] == 3 and j3['song_e'][2]['bars'] == 8 and j3['lfo'][5]['enabled'] == 1 and j3['lfox'][5]['trig'] == 2
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
    # 0.23: what the THEORY engines know of a pattern they made - the SOURCE, the next seed, a record a pattern (track
    # * 8 + pattern) - comes through a read, a patch that touches something else, and goes when the patch says so; a
    # style there is not is put right (the record is nobody's)
    r = apply(out, ['th - src - 1', 'th - seed - 41', 'thp 19 style - %d' % (11 | 0x40), 'thp 19 seed - 7', 'thp 19 func - 1', 'thp 19 var - 3', 'thp 19 vary - 40',
                    'thp 19 energy - 60', 'thp 95 style - 26', 'thp 95 seed - 998', 'thp 5 style - 31', 'thp 5 seed - 9'], out2)
    j7 = read(out2)
    check(r.returncode == 0 and j7.get('th') == {'src': 1, 'seed': 41} and len(j7.get('thp', [])) == 96
          and j7['thp'][19] == {'seed': 7, 'style': 11 | 0x40, 'func': 1, 'var': 3, 'vary': 40, 'energy': 60, 'metre': 0} and j7['thp'][95]['style'] == 26 and j7['thp'][95]['seed'] == 998,
          '0.23 THEORY: the SOURCE, the next seed, the record of a pattern (track 3 pattern 4: REGGAETON, 64 steps, seed 8, variation 3) (%s %s)' % (j7.get('th'), r.stderr))
    check(j7['thp'][5] == {'seed': 0, 'style': 0, 'func': 0, 'var': 0, 'vary': 0, 'energy': 0, 'metre': 0}, '... a style there is not: the record is put right - nobody\'s (%s)' % j7['thp'][5])
    out3 = os.path.join(d, 'th2.sgq')
    r = apply(out2, ['step 2,3,0 flags - 3', 'thp 95 style - 0'], out3)
    j8 = read(out3)
    check(r.returncode == 0 and j8['thp'][19] == j7['thp'][19] and j8['th'] == j7['th'] and j8['thp'][95]['style'] == 0 and j8['thp'][95]['seed'] == 0,
          '... a patch of a step keeps the pattern\'s record; the record goes when the patch says so (%s)' % j8['thp'][95])
    out4 = os.path.join(d, 'th3.sgq')                     # the SOURCE on FREE (2: the engines, the rules of no genre); one there is not
    r = apply(out2, ['th - src - 2'], out4)
    j10 = read(out4)
    check(r.returncode == 0 and j10['th'] == {'src': 2, 'seed': 41} and j10['thp'][19] == j7['thp'][19], '... the SOURCE on FREE comes through, the records with it (%s %s)' % (j10.get('th'), r.stderr))
    r = apply(out2, ['th - src - 3'], out4)
    check(r.returncode == 0 and read(out4)['th'] == {'src': 0, 'seed': 41}, '... a SOURCE there is not is put right: LIBRARY (%s %s)' % (read(out4).get('th'), r.stderr))
    j9 = read(HW)
    check(j9.get('th') == {'src': 0, 'seed': 0} and not any(m['style'] for m in j9['thp']), 'a project of before 0.23: SOURCE LIBRARY, no pattern is the engines\'')
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
    for bad, why in ((['nogroup - bpm - 1'], 'a group'), (['project - nofield - 1'], 'a field'), (['track 12 length - 4'], 'an index (0.28: twelve tracks)'),
                     (['step 0,0 flags - 1'], 'a step needs three'), (['track 0 length 0 4'], 'an element of a scalar'),
                     (['track 0 lane_cc 8 4'], 'an element past the array (0.28: eight lanes)'), (['project - bpm - 70000'], 'a value past u16'),
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
    # 0.23.2: a Pi without the internet has no clock to trust: a version kept "now" can bear an earlier time than one
    # kept before. The names are the order: the new one takes the second after the newest there
    vdir = os.path.join(d, E.VERSIONS, 'hw')
    was = open(os.path.join(d, 'hw.sgq'), 'rb').read()
    open(os.path.join(vdir, '20991231-235959.sgq'), 'wb').write(b'di domani')
    ed.save('hw.sgq', [['project', '-', 'bpm', '-', 141]])
    v = ed.versions('hw.sgq')
    check(v[0] == '21000101-000000' and v[1] == '20991231-235959' and open(os.path.join(vdir, v[0] + '.sgq'), 'rb').read() == was,
          'the clock behind the newest version: the new one is named a second after it, and is first in the list (%s)' % v[:3])
    ed.save('hw.sgq', [['project', '-', 'bpm', '-', 142]])
    ed.save('hw.sgq', [['project', '-', 'bpm', '-', 143]])
    v = ed.versions('hw.sgq')
    check(v[:3] == ['21000101-000002', '21000101-000001', '21000101-000000'] and ed.restore('hw.sgq', v[0])['project']['bpm'] == 142,
          '... and the next ones after it, in order: the first of the list is the last one replaced (%s)' % v[:3])
    os.unlink(os.path.join(vdir, '20991231-235959.sgq'))
    for n in os.listdir(vdir):
        if n.startswith('2100'):
            os.unlink(os.path.join(vdir, n))
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
    check(js('FOLLOW') == c('static const char *const FMN[SQ_FMS]') and js('FOLLOW')[-2:] == ['MELODY', 'SMOOTH'], 'FOLLOW\'s ways as the panel\'s: MELODY, and SMOOTH the last (%s)' % js('FOLLOW'))   # 0.25, 0.26


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
    for bad, why in ((['tape 5 add - 1'], 'add needs the event'), (['tape 12 clear - 0'], 'a track past 12 (0.28)'), (['tape 5,0,0,60 add - 100'], 'a length 0'),
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
    r = ed.preview(11, [48, 52, 55, 59, 62, 65, 69], 90, 300)
    req = json.load(open(os.path.join(ctl, 'bridge-preview.json')))
    check(r['ok'] and req['t'] == 11 and req['notes'] == [48, 52, 55, 59, 62, 65], '0.28: track 12, a chord of six notes (a seventh is not sent) (%s)' % req)
    for bad in ((12, [60]), (16, [60]), (0, []), (0, [128]), ('x', [60])):
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


def t023_page():
    group('0.23 the page and the THEORY engines: a pattern they made says so with its seed; emptied here, they forget it; one copied on its track keeps what they know; the others stay')
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
    name = os.path.join(pr, 'motori.sgq')
    # track 3 (index 2): pattern 1 made from seed 8, variation 3; track 6: pattern 1 from seed 21; the SOURCE on THEORY
    r = apply(HW, ['th - src - 1', 'th - seed - 41', 'thp 16 style - 11', 'thp 16 seed - 7', 'thp 16 func - 1', 'thp 16 var - 3', 'thp 16 vary - 40', 'thp 16 energy - 50',
                   'thp 40 style - 1', 'thp 40 seed - 20', 'thp 40 energy - 50', 'step 2,0,3 flags - 3', 'step 2,0,3 note 0 38', 'step 5,0,0 flags - 3'], name)
    check(r.returncode == 0, 'a project with two patterns of the engines (%s)' % r.stderr)
    # ... and one with the SOURCE on FREE: track 1's pattern made by the rules of no genre (style 26), from seed 4
    r = apply(HW, ['th - src - 2', 'th - seed - 6', 'thp 0 style - 26', 'thp 0 seed - 3', 'thp 0 energy - 50', 'step 0,0,0 flags - 3'], os.path.join(pr, 'libero.sgq'))
    check(r.returncode == 0, 'a project with the SOURCE on FREE (%s)' % r.stderr)
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
            pg.goto('http://127.0.0.1:%d/edit/motori.sgq' % port)
            pg.wait_for_timeout(800)
            pg.evaluate("V.pat=0;V.t=2;V.tab='tracce';render()")
            labels = [x.text_content() for x in pg.query_selector_all('.tr .lb')]
            head = pg.text_content('#main .row small') or ''
            check(len(labels) == 12 and '\u25c68' in labels[2] and '\u25c621' in labels[5] and not any('\u25c6' in x for i, x in enumerate(labels) if i not in (2, 5)),
                  'the tracks whose pattern the engines made say so, with the seed as the FM-1 shows it (%s)' % [labels[2], labels[5]])
            check('sorgente THEORY (prossimo seme 42)' in head, 'the SOURCE and the next seed (%s)' % head)
            title = pg.get_attribute('.tr .lb.cur', 'title') or ''
            check('seme 8' in title and 'variazione 3' in title and 'ENERGIA' in title, 'the label says what it means (%s)' % title)
            pg.evaluate("V.tab='traccia';render()")
            pg.select_option('#cpt', '2'); pg.select_option('#cpp', '4')            # copy T3 P1 onto T3 P5: its record goes with it
            pg.click('button:has-text("Copia in")')
            pg.wait_for_timeout(100)
            check(pg.evaluate('thOf(2,4) && thOf(2,4).seed') == 7 and pg.evaluate('thOf(2,4).var') == 3, 'a copy onto another pattern of the track keeps what the engines know (%s)' % pg.evaluate('JSON.stringify(P.thp[20])'))
            pg.select_option('#cpt', '9'); pg.select_option('#cpp', '0')            # ... onto another track: a pattern of nobody's
            pg.click('button:has-text("Copia in")')
            pg.wait_for_timeout(100)
            check(pg.evaluate('thOf(9,0)') is None and pg.evaluate('getStep(9,0,3).flags') & 1 == 1, '... onto another track: the steps, not the record')
            pg.click('button:has-text("Svuota il pattern")')
            pg.wait_for_timeout(100)
            check(pg.evaluate('thOf(2,0)') is None and pg.evaluate('thOf(5,0).seed') == 20, 'a pattern emptied here: the engines forget it; the other stays (%s)' % pg.evaluate('JSON.stringify(P.thp[16])'))
            pg.keyboard.press('Control+z')
            check(pg.evaluate('thOf(2,0) && thOf(2,0).seed') == 7 and pg.evaluate('getStep(2,0,3).flags') & 1 == 1, 'Ctrl+Z: the pattern and what the engines knew of it')
            pg.click('button:has-text("Svuota il pattern")')
            pg.wait_for_timeout(100)
            pg.click('#bsave')
            pg.wait_for_timeout(700)
            j = read(name)
            check(j['thp'][16]['style'] == 0 and j['thp'][16]['seed'] == 0 and j['thp'][20] == {'seed': 7, 'style': 11, 'func': 1, 'var': 3, 'vary': 40, 'energy': 50, 'metre': 0}
                  and j['thp'][40]['seed'] == 20 and j['thp'][72]['style'] == 0 and j['th'] == {'src': 1, 'seed': 41},
                  'saved: the emptied pattern is nobody\'s, the copy and the other pattern are the engines\', the SOURCE stays (%s)' % [j['thp'][k] for k in (16, 20, 40)])
            pg.goto('http://127.0.0.1:%d/edit/libero.sgq' % port)                    # the SOURCE on FREE
            pg.wait_for_timeout(800)
            pg.evaluate("V.pat=0;V.t=0;V.tab='tracce';render()")
            head = pg.text_content('#main .row small') or ''
            labels = [x.text_content() for x in pg.query_selector_all('.tr .lb')]
            title = pg.get_attribute('.tr .lb.cur', 'title') or ''
            check('sorgente FREE' in head and 'nessun genere' in head and 'prossimo seme 7' in head, 'the SOURCE on FREE: the page says the engines make by no genre (%s)' % head)
            check('\u25c64' in labels[0] and 'FREE' in title and 'seme 4' in title, '... and a pattern made so says it (%s, %s)' % (labels[0], title))
            check(not errs, 'no script errors (%s)' % errs[:2])
            b.close()
    finally:
        srv.shutdown()


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
    check(B.preview_frame(dict(t=16, notes=[60])) is None and B.preview_frame(dict(t=12, notes=[60])) is None and B.preview_frame(dict(t=0, notes=[])) is None
          and B.preview_frame(dict(t=0, notes=[200])) is None and B.preview_frame('x') is None and B.preview_frame(dict(t=0, notes=[1, 2, 3, 4, 5, 6, 7]))[9] == 6
          and B.preview_frame(dict(t=11, notes=[60]))[5] == 11, 'a preview that is not one: no frame (0.28: track 13 neither); 6 notes at most (0.28)')


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


def t0232_tape_link():
    group('0.23.2 the old piano roll\'s link opens the Tape tab; what its Save got wrong the editor gets right: a TAPE track on another channel, transposed, with a loop of its own')
    d = tempfile.mkdtemp()
    fw, pr = os.path.join(d, 'fw'), os.path.join(d, 'pr')
    os.makedirs(fw)
    os.makedirs(pr)
    name = os.path.join(pr, 'tapes.sgq')
    # hwtest's T4 is a TAPE of one bar with two notes: on MIDI channel 10 here, an octave up; T10 is a step track
    r = apply(HW, ['track 3 channel - 9', 'track 3 transpose - 12', 'step 9,0,0 note 0 55', 'step 9,0,0 flags - 3'], name)
    check(r.returncode == 0, 'the project is made (%s)' % r.stderr.strip())
    j0 = read(name)
    t10 = dict(j0['track'][9])
    # the converter alone: a note more on T4, nothing else moves (the old Save: T10 became a TAPE of eight notes, T4 stayed as it was)
    out = os.path.join(d, 'conv.sgq')
    r = apply(name, ['tape 3 clear - 0', 'tape 3,96,117,48 add - 110', 'tape 3,960,119,50 add - 90', 'tape 3,480,96,52 add - 100'], out)
    j = read(out)
    check(r.returncode == 0 and [e for e in j['tape'] if e[0] == 3] == [[3, 96, 117, 48, 110], [3, 480, 96, 52, 100], [3, 960, 119, 50, 90]],
          'the converter: T4\'s notes as written, not transposed again (%s)' % [e for e in j['tape'] if e[0] == 3])
    check(j['track'][3]['channel'] == 9 and j['track'][3]['transpose'] == 12 and j['track'][3]['tape_bars'] == 1 and j['tape_len'][3] == 1536,
          'T4 keeps its channel, its transpose and its one bar (%s %s %s)' % (j['track'][3]['channel'], j['track'][3]['transpose'], j['track'][3]['tape_bars']))
    check(j['track'][9] == t10 and j['tape_cnt'][9] == 0 and [x for x in j['steps'] if x[0] == 9] == [x for x in j0['steps'] if x[0] == 9],
          'T10 (the track of that channel\'s number) is not touched: a step track still, its step there')
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print('  (the page: skipped, no playwright)')
        return
    import sagga_fw as FW
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
            pg.add_init_script("localStorage.clear()")
            pg.goto('http://127.0.0.1:%d/' % port)
            pg.wait_for_timeout(500)
            check('/roll/' not in pg.content() and '/edit/tapes.sgq' in pg.content(), 'the library: the editor\'s link, no piano roll')
            pg.goto('http://127.0.0.1:%d/roll/tapes.sgq' % port)                   # an old bookmark
            pg.wait_for_timeout(900)
            check(pg.url.endswith('/edit/tapes.sgq') and pg.evaluate('V.tab') == 'tape' and pg.evaluate('V.tt') == 3,
                  'the old link lands in the editor, on the Tape tab, on the TAPE track (%s, %s, T%s)' % (pg.url.rsplit('/', 2)[-2:], pg.evaluate('V.tab'), pg.evaluate('V.tt') + 1))
            check(pg.evaluate('evs(3)') == [[96, 117, 48, 110], [960, 119, 50, 90]] and pg.evaluate('tapeLen(3)') == 1536,
                  'its two notes once, as they are kept (not four copies an octave up), the loop one bar (%s)' % pg.evaluate('evs(3)'))
            pg.evaluate("V.snap=true;V.listen=false;render()")
            Z = pg.evaluate('V.rz')
            box = pg.query_selector('#roll').bounding_box()
            hi = pg.evaluate('V.rhi')
            pg.mouse.click(box['x'] + Z * 5 + 3, box['y'] + (hi - 52) * 10 + 4)             # an E3 on the 6th 16th
            check(pg.evaluate('evs(3)') == [[96, 117, 48, 110], [480, 96, 52, 100], [960, 119, 50, 90]], 'a note added on the roll (%s)' % pg.evaluate('evs(3)'))
            pg.click('#bsave')
            pg.wait_for_timeout(1200)
            check((pg.text_content('#status') or '').startswith('salvato') and not errs, 'saved, no script errors (%s, %s)' % (pg.text_content('#status'), errs))
            pg.goto('http://127.0.0.1:%d/edit/tapes.sgq' % port)                   # the plain link: where the view was left, no jump
            pg.wait_for_timeout(700)
            pg.evaluate("V.tab='tracce';keepView();render()")
            pg.goto('http://127.0.0.1:%d/edit/tapes.sgq' % port)
            pg.wait_for_timeout(700)
            check(pg.evaluate('V.tab') == 'tracce', 'the editor\'s own link opens where you left it, not the Tape tab')
            b.close()
    finally:
        srv.shutdown()
    j = read(name)
    check([e for e in j['tape'] if e[0] == 3] == [[3, 96, 117, 48, 110], [3, 480, 96, 52, 100], [3, 960, 119, 50, 90]] and j['track'][3]['channel'] == 9
          and j['track'][3]['transpose'] == 12 and j['track'][3]['tape_bars'] == 1, 'in the file: T4 with the note more, on its channel, its transpose, its bar (%s)' % [e for e in j['tape'] if e[0] == 3])
    check(j['track'][9] == t10 and j['tape_cnt'][9] == 0, 'in the file: T10 as it was')


def t024_copies():
    group('0.24 the copies: a track made longer has its patterns go round, as on the FM-1; a step of the pattern changed: its copies follow; a copy changed: they are steps; shorter: the mark')
    d = tempfile.mkdtemp()
    a, b, c2, e = [os.path.join(d, n) for n in ('a.sgq', 'b.sgq', 'c.sgq', 'e.sgq')]
    lines = []
    for st in (0, 4, 10):
        lines += ['step 0,0,%d flags - 3' % st, 'step 0,0,%d note 0 %d' % (st, 60 + st)]
    lines += ['step 0,1,2 flags - 3']                                       # pattern 2 of the same track
    r = apply('new', lines, a)
    check(r.returncode == 0 and not any(x['flags'] & 64 for _, _, _, x in read(a)['steps']), 'three steps in a track of 16: no copies (%s)' % r.stderr)

    def steps(path):
        return {(t, p, st): x for t, p, st, x in read(path)['steps']}
    def copies(path, t, p):
        return sorted(st for (tt, pp, st), x in steps(path).items() if tt == t and pp == p and x['flags'] & 64)

    r = apply(a, ['track 0 length - 32'], b)
    st = steps(b)
    check(r.returncode == 0 and copies(b, 0, 0) == list(range(16, 32)) and st[(0, 0, 20)]['flags'] == 3 | 64 and st[(0, 0, 20)]['note'][0] == 64 and st[(0, 0, 17)]['flags'] == 64,
          'LENGTH 32 in a patch: steps 17 .. 32 are the pattern\'s copies - the notes and the rests (%s)' % copies(b, 0, 0)[:4])
    check(copies(b, 0, 1) == list(range(16, 32)) and st[(0, 1, 18)]['flags'] == 3 | 64, '... in the track\'s other pattern too')
    apply(b, [], e)
    check(open(b, 'rb').read() == open(e, 'rb').read(), 'an empty patch: the same image, byte for byte (the copies are in it)')
    r = apply(b, ['step 0,0,4 note 0 72', 'step 0,0,10 flags - 2'], c2)   # step 5: another note; step 11: off
    st = steps(c2)
    check(r.returncode == 0 and st[(0, 0, 20)]['note'][0] == 72 and st[(0, 0, 20)]['flags'] == 3 | 64 and st[(0, 0, 26)]['flags'] == 2 | 64 and copies(c2, 0, 0) == list(range(16, 32)),
          'steps of the pattern changed: their copies follow (step 21 plays %s, step 27 is %s)' % (st[(0, 0, 20)]['note'][0], st[(0, 0, 26)]['flags']))
    r = apply(c2, ['step 0,0,20 velocity - 33'], e)                         # step 21, a copy: changed
    st = steps(e)
    check(r.returncode == 0 and copies(e, 0, 0) == [] and st[(0, 0, 20)]['velocity'] == 33 and st[(0, 0, 20)]['flags'] == 3 and st[(0, 0, 16)]['flags'] == 3
          and copies(e, 0, 1) == list(range(16, 32)),
          'a copy changed: the copies of that pattern are steps (the other pattern keeps its own) (%s)' % copies(e, 0, 0))
    r = apply(b, ['track 0 length - 12'], c2)
    st = steps(c2)
    check(r.returncode == 0 and copies(c2, 0, 0) == [16] and st[(0, 0, 16)]['flags'] == 64 and st[(0, 0, 10)]['flags'] == 3 and (0, 0, 20) not in st,
          'LENGTH 12: the pattern keeps its 16 steps, the mark after them, no copies (%s)' % copies(c2, 0, 0))
    r = apply(c2, ['track 0 length - 24'], e)
    st = steps(e)
    check(copies(e, 0, 0) == list(range(16, 24)) and st[(0, 0, 20)]['note'][0] == 64 and (0, 0, 12) not in st, '... 24 after it: the pattern whole, and its first half again (%s)' % copies(e, 0, 0))
    r = apply(a, ['step 0,0,63 flags - 3', 'track 0 length - 40'], c2)       # the 64th step written, then longer: nothing copied
    check(r.returncode == 0 and copies(c2, 0, 0) == [] and (0, 0, 20) not in steps(c2), 'a step written at the end, then LENGTH 40: no copies, silence up to it')
    r = apply(b, ['track 0 start - 4'], c2)                                  # the loop's start moved: nothing mirrors it
    check(r.returncode == 0 and copies(c2, 0, 0) == [] and steps(c2)[(0, 0, 20)]['flags'] == 3, 'the loop\'s start moved: the copies are steps')

    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print('  (the page: skipped, no playwright)')
        return
    import sagga_fw as FW
    fw, pr = os.path.join(d, 'fw'), os.path.join(d, 'pr')
    os.makedirs(fw)
    os.makedirs(pr)
    name = os.path.join(pr, 'copie.sgq')
    shutil.copy(b, name)
    state = FW.State(fw, pr, writer=FW.BootWriter(fw, mounts=lambda: [('/', ['rw'])]))
    state.editor.control = os.path.join(d, 'run')
    srv = FW.ThreadingHTTPServer(('127.0.0.1', 0), FW.make_handler(state))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            pg = br.new_page(viewport={'width': 1300, 'height': 900})
            errs = []
            pg.on('pageerror', lambda x: errs.append(str(x)))
            pg.on('dialog', lambda dg: dg.accept())
            pg.goto('http://127.0.0.1:%d/edit/copie.sgq' % port)
            pg.wait_for_timeout(800)
            pg.evaluate("V.pat=0;V.t=0;V.s=20;V.toggle=true;V.listen=false;V.tab='tracce';render()")
            gh = pg.evaluate("[...document.querySelectorAll('.tr')][0].querySelectorAll('.c.on.ghost').length")
            on = pg.evaluate("[...document.querySelectorAll('.tr')][0].querySelectorAll('.c.on').length")
            note = pg.text_content('#main p.dim') or ''
            check(gh == 3 and on == 6, 'the page: the three copies that play have their own colour (%s of %s lit)' % (gh, on))
            check('copia' in note and 'dello step 5' in note and 'di 16 step' in note, 'a copy selected: the page says of which step it is one (%s)' % note[:80])
            check('verde-azzurro: una copia' in (pg.text_content('#main') or ''), 'the legend names the colour')
            pg.evaluate("set('step','0,0,4','note',0,70);commit();render()")       # step 5 of the pattern: another note
            pg.click('#bsave')
            pg.wait_for_timeout(700)
            check(pg.evaluate('getStep(0,0,20).note[0]') == 70 and pg.evaluate('getStep(0,0,20).flags') == 3 | 64, 'a step of the pattern changed and saved: the page comes back with its copy changed too')
            pg.click('.c[data-ts="0,20"]')                                           # the copy turned off
            pg.wait_for_timeout(100)
            pg.click('#bsave')
            pg.wait_for_timeout(700)
            gh = pg.evaluate("[...document.querySelectorAll('.tr')][0].querySelectorAll('.c.ghost').length")
            check(gh == 0 and pg.evaluate('getStep(0,0,16).flags') == 3 and pg.evaluate('getStep(0,0,20).flags') == 2 and copies(name, 0, 0) == [],
                  'a copy turned off and saved: the copies are steps, on the page and in the file (%s)' % gh)
            pg.evaluate("V.s=4;clip=clone(getStep(0,1,18));pasteStep()")             # a copy of pattern 2 pasted onto step 5 of pattern 1: a step
            check(pg.evaluate('getStep(0,0,4).flags') == 3, 'a copy pasted somewhere is a step there (flags %s)' % pg.evaluate('getStep(0,0,4).flags'))
            pg.evaluate("set('track',0,'length','-',48);commit();render()")
            pg.click('#bsave')
            pg.wait_for_timeout(700)
            check(pg.evaluate('P.track[0].length') == 48 and copies(name, 0, 0) == list(range(32, 48)) and copies(name, 0, 1) == list(range(16, 48)),
                  'LENGTH 48 in the editor, saved: the pattern of 32 goes round (16 copies), the other one of 16 twice more (%s)' % len(copies(name, 0, 1)))
            # 0.25: the copies BEFORE Save - LENGTH 56 typed: the picture is already what Save will make
            row0 = "[...[...document.querySelectorAll('.tr')][0].querySelectorAll('.c')].map(c => c.className.replace(' sel', '')).join('|')"
            pg.evaluate("V.s=50;set('track',0,'length','-',56);commit();render()")
            before = pg.evaluate(row0)
            gh = pg.evaluate("[...document.querySelectorAll('.tr')][0].querySelectorAll('.c.ghost').length")
            note = pg.text_content('#main p.dim') or ''
            check(gh == 24 and pg.evaluate('getStep(0,0,50).flags & 64') == 0 and copies(name, 0, 0) == list(range(32, 48)),
                  'LENGTH 56 typed, not saved: the 8 new steps show as copies already, 24 in all (%s) - a picture: the project has the 16 it had' % gh)
            check('Al Salva questo step sarà una' in note and 'dello step 19' in note, 'one of them selected: the page says what Save will make of it (%s)' % note[:70])
            pg.click('#bsave')
            pg.wait_for_timeout(700)
            check(pg.evaluate(row0) == before and copies(name, 0, 0) == list(range(32, 56)) and pg.evaluate('getStep(0,0,50).flags & 64') == 64,
                  'saved: the page is as it was a moment before, and the copies are in the file (%s)' % len(copies(name, 0, 0)))
            pg.evaluate("set('track',0,'length','-',40);commit();render()")          # shorter, not saved: no copy shown after the loop
            gh = pg.evaluate("[...document.querySelectorAll('.tr')][0].querySelectorAll('.c.ghost').length")
            out = pg.evaluate("[...document.querySelectorAll('.tr')][0].querySelectorAll('.c.out').length")
            check(gh == 8 and out == 24, 'LENGTH 40 typed: 8 copies in the loop, the rest out of it (%s, %s)' % (gh, out))
            pg.evaluate("undoOne()")
            check(not errs, 'no script errors (%s)' % errs[:2])
            br.close()
    finally:
        srv.shutdown()


def t025_preview():
    group("0.25 the editor shows the copies BEFORE Save: its picture (rowFit, in the page) is the core's sq_row_fit, step by step, on 4000 rows")
    import random
    import shutil
    page = open(os.path.join(ROOT, 'tools', 'hub', 'editor.html'), encoding='utf-8').read()
    a, b = page.find('//<fit>'), page.find('//</fit>')
    check(0 < a < b and 'function rowFit(row, start, oldLen, newLen, def)' in page[a:b], 'the page has its rowFit between the marks')
    check('const st = shownStep(t, V.pat, s)' in page and 'pvCache = null;' in page and 'function previewRow(t, p)' in page,
          'the overview draws shownStep (the pattern as Save will make it), worked out again at every render')
    check("if (tch.some(s => origStep(t, p, s).flags & GHOST)) rowKeep(row);" in page and "if (c.start !== o.start) rowKeep(row);" in page
          and "rowFit(row, c.start, moved ? o.length : c.length, c.length, P.step_default);" in page,
          "previewRow follows the converter's copies_after: a copy written or a start moved keeps them, then the fit from the saved length")
    node = shutil.which('node')
    if not node:
        print("  (node non c'e': il confronto fra rowFit e sq_row_fit e' saltato)")
        return
    # the cases: rows as the FM-1 and the editor leave them, and rows of anything
    rnd = random.Random(25)
    cases = []
    for n in range(4000):
        start = rnd.choice([0, 0, 0, 0, 1, 3, 8])
        old = rnd.randint(start + 1, 64)
        new = rnd.randint(1, 64) if rnd.random() < 0.9 else old
        row = [[0, 0] for _ in range(64)]                          # (flags, k: 0 = nothing of its own)
        kind = n % 5
        if kind < 3:                                               # a pattern, its copies, a mark, things written after
            own = rnd.randint(start + 1, 64)
            for i in range(start, own):
                if rnd.random() < 0.45:
                    row[i] = [1 | (2 if rnd.random() < 0.5 else 0), rnd.randint(1, 60)]
            if own < old:
                for i in range(own, old):
                    s = row[start + (i - start) % (own - start)]
                    row[i] = [s[0] | 64, s[1]]
                if kind == 1 and old - own > 1:                    # one of them is not a copy any more
                    row[rnd.randint(own, old - 1)][0] &= ~64
            elif own > old and own < 64 and kind == 2:
                row[own] = [64, 0]                                 # the mark of the pattern's end after the loop
            if rnd.random() < 0.3:
                for _ in range(rnd.randint(1, 3)):
                    i = rnd.randint(min(63, max(own, old)), 63)
                    row[i] = [1, rnd.randint(1, 60)]               # written after it
        else:                                                      # anything
            for i in range(64):
                f = rnd.choice([0, 0, 0, 1, 1, 3, 64, 65, 67])
                row[i] = [f, rnd.randint(1, 60) if (f & 1) or rnd.random() < 0.1 else 0]
        cases.append((start, old, new, row))
    text = "\n".join("%d %d %d %s" % (s, o, nw, " ".join("%d:%d" % (f, k) for f, k in row)) for s, o, nw, row in cases) + "\n"
    with tempfile.TemporaryDirectory() as d:
        csrc = os.path.join(d, 'fit.c')
        with open(csrc, 'w') as f:
            f.write(r"""
#include <stdio.h>
#include "sagga_seq_core.h"
int main(void)
{
    unsigned st, ol, nw;
    while (scanf("%u %u %u", &st, &ol, &nw) == 3) {
        sq_step_t row[SQ_STEPS], d;
        unsigned i, f, k;
        sq_step_default(&d);
        for (i = 0; i < SQ_STEPS; i++) {
            if (scanf("%u:%u", &f, &k) != 2) return 1;
            sq_step_default(&row[i]);
            row[i].flags = (uint8_t)f;
            if (k) row[i].chance = (uint8_t)k;                     /* (something of its own: 1..60, never the default 100) */
        }
        sq_row_fit(row, (uint8_t)st, (uint8_t)ol, (uint8_t)nw);
        for (i = 0; i < SQ_STEPS; i++) printf("%u:%u%c", row[i].flags, row[i].chance == d.chance ? 0u : row[i].chance, i + 1 < SQ_STEPS ? ' ' : '\n');
    }
    return 0;
}
""")
        exe = os.path.join(d, 'fit')
        subprocess.run(['cc', '-std=c11', '-O2', '-I' + os.path.join(ROOT, 'firmware', 'src'), csrc,
                        os.path.join(ROOT, 'firmware', 'src', 'sagga_seq_core.c'), os.path.join(ROOT, 'firmware', 'src', 'sagga_beats.c'), '-o', exe], check=True)
        want = subprocess.run([exe], input=text, capture_output=True, text=True, check=True).stdout
        js = os.path.join(d, 'fit.js')
        with open(js, 'w') as f:
            f.write("const ON = 1, GHOST = 64;\n" + page[a:b] + r"""
const def = {flags: 0, chance: 100};
const lines = require('fs').readFileSync(0, 'utf8').trim().split('\n');
const out = [];
for (const ln of lines) {
  const w = ln.split(' ');
  const row = w.slice(3).map(x => { const [f, k] = x.split(':').map(Number); return {flags: f, chance: k || 100}; });
  rowFit(row, +w[0], +w[1], +w[2], def);
  out.push(row.map(s => s.flags + ':' + (s.chance === 100 ? 0 : s.chance)).join(' '));
}
console.log(out.join('\n'));
""")
        got = subprocess.run([node, js], input=text, capture_output=True, text=True)
    check(got.returncode == 0, 'the page\'s rowFit runs (%s)' % got.stderr.strip()[-200:])
    gl, wl = got.stdout.strip().split('\n'), want.strip().split('\n')
    bad = [i for i in range(min(len(gl), len(wl))) if gl[i] != wl[i]]
    check(len(gl) == len(wl) == len(cases) and not bad,
          "4000 rows fitted by the page and by the core: the same steps, the same copies (%d differ%s)" % (
              len(bad), "; the first: start %d, %d -> %d" % cases[bad[0]][:3] if bad else ""))
    changed = sum(1 for i, c in enumerate(cases) if wl[i] != " ".join("%d:%d" % (f, k) for f, k in c[3]))
    check(changed > 1500, "... and the fit did change most of them (%d of %d: the comparison is not of rows left alone)" % (changed, len(cases)))


def t025_metre():
    group("0.25 THE METRE in the files and on the page: the bar and its beats in a patch, put right; the page's own reading of them is the core's; the bar typed on the page moves the tracks on it")
    import shutil
    d = tempfile.mkdtemp()
    a, b, c2 = [os.path.join(d, n) for n in ('a.sgq', 'b.sgq', 'c.sgq')]
    j0 = read(os.path.join(d, 'new.sgq')) if tool('new', os.path.join(d, 'new.sgq')).returncode == 0 else {}
    ways = j0.get('names', {}).get('metre', {})
    check(j0.get('metre') == {'bar_steps': 0, 'bar_beats': [0, 0, 0, 0]} and j0.get('metre_now') == {'steps': 16, 'beats': 0x1111, 'sig': '4/4', 'split': '4x2', 'id': 0},
          'a new project: 4/4, written as nothing at all (%s %s)' % (j0.get('metre'), j0.get('metre_now')))
    check(sorted(map(int, ways)) == list(range(3, 33)) and sum(len(v) for v in ways.values()) == 217
          and ways.get('14') == [[0x111, '7/8', '2+2+3'], [0x411, '7/8', '2+3+2'], [0x441, '7/8', '3+2+2']] and ways.get('12') == [[0x111, '3/4', '2+2+2'], [0x41, '6/8', '3+3']],
          'the names: every way every bar of 3 to 32 steps divides, 217 in all (14: %s)' % ways.get('14'))
    check(['metre', 1, 0, 1] in j0['schema']['thp']['fields'] and j0['schema']['metre']['fields'] == [['bar_steps', 1, 0, 1], ['bar_beats', 1, 0, 4]],
          'the schema: the metre, and the metre a pattern of the engines was made in')
    r = apply('new', ['metre - bar_steps - 14', 'track 2 flags - 32'], a)
    j = read(a)
    check(r.returncode == 0 and j['metre_now']['sig'] == '7/8' and j['metre_now']['split'] == '2+2+3' and j['metre']['bar_steps'] == 14 and j['metre']['bar_beats'] == [0x11, 1, 0, 0]
          and j['metre_now']['id'] not in (0, 255),
          'bar_steps 14 in a patch: 7/8 in its usual way, the beats written out (%s %s)' % (j['metre'], j['metre_now']))
    check(j['track'][0]['length'] == 16 and j['tape_len'][2] == 4 * 14 * 96, 'a patch of the bar alone moves no track; a tape\'s loop is bars of the metre (%s, %s ticks)' % (j['track'][0]['length'], j['tape_len'][2]))
    r = apply(a, ['metre - bar_beats 0 17', 'metre - bar_beats 1 4'], b)
    j = read(b)
    check(r.returncode == 0 and j['metre_now']['split'] == '2+3+2' and j['metre_now']['beats'] == 0x411, 'the beats in a patch: 2+3+2 (%s)' % j['metre_now'])
    for lines, want, why in ((['metre - bar_steps - 99'], ('4/4', '4x2', 0, [0, 0, 0, 0]), 'a bar there is not: 4/4'),
                             (['metre - bar_steps - 14', 'metre - bar_beats 0 255', 'metre - bar_beats 1 63'], ('7/8', '7x1', 14, None), 'every step a beat: put right'),
                             (['metre - bar_steps - 16'], ('8/8', '2+3+3', 16, [0x11, 4, 0, 0]), 'the bar alone, 16: the beats it had are beats of it - 8/8 as 2+3+3'),
                             (['metre - bar_steps - 16', 'metre - bar_beats 0 0', 'metre - bar_beats 1 0'], ('4/4', '4x2', 0, [0, 0, 0, 0]), '16 and its usual beats: 4/4, nothing at all'),
                             (['metre - bar_steps - 12', 'metre - bar_beats 0 65', 'metre - bar_beats 1 0'], ('6/8', '3+3', 12, [0x41, 0, 0, 0]), '12 as 3+3: 6/8')):
        r = apply(b, lines, c2)
        j = read(c2) if r.returncode == 0 else {}
        mn, m = j.get('metre_now', {}), j.get('metre', {})
        ok = r.returncode == 0 and mn.get('sig') == want[0] and m.get('bar_steps') == want[2] and (want[3] is None or m.get('bar_beats') == want[3]) and (want[1] == '7x1' or mn.get('split') == want[1])
        if want[1] == '7x1':                                    # (no beat of one step is left: the mask is one sq_metre_fix made)
            bt = mn.get('beats', 0)
            ok = ok and bt & 1 and not any((bt >> s) & 1 and (bt >> (s + 1)) & 1 for s in range(13)) and not (bt >> 13) & 1 and mn.get('id') == 255
        check(ok, '%s (%s %s)' % (why, m, mn))
    # a tape event past sixteen bars: of the metre the project ends up with, wherever the patch says it
    lim = 16 * 14 * 96
    for lines, code, why in ((['tape 5,%d,96,60 add - 9' % (lim - 96)], 0, 'in the last 16th of the 16 bars of 7/8: taken'),
                             (['tape 5,%d,96,60 add - 9' % lim], 4, 'past them: refused (in 4/4 it would fit)'),
                             (['tape 5,%d,96,60 add - 9' % lim, 'metre - bar_steps - 16'], 0, 'the metre made 4/4 on a later line: taken'),
                             (['tape 5,30000,96,60 add - 9', 'metre - bar_steps - 20'], 0, 'tick 30000 in a patch that makes the bar 20: taken (4/4: refused)')):
        r = apply(a, ['track 5 flags - 32', 'track 5 tape_bars - 16'] + lines, c2)
        check(r.returncode == code and (code == 0 or 'line 3' in r.stderr), '%s (%s %s)' % (why, r.returncode, r.stderr.strip()))

    # the page's own reading of the metre (barSteps, barBeats, beatAt, metreFollow: between the marks) is the core's
    page = open(os.path.join(ROOT, 'tools', 'hub', 'editor.html'), encoding='utf-8').read()
    pa, pb = page.find('//<metre>'), page.find('//</metre>')
    check(0 < pa < pb and 'function metreFollow(len, start, oldBar, newBar)' in page[pa:pb] and 'function beatAt(s)' in page[pa:pb], 'the page has its metre between the marks')
    node = shutil.which('node')
    if not node:
        print("  (node non c'e': il confronto con il core e' saltato)")
    else:
        csrc, exe, js = os.path.join(d, 'm.c'), os.path.join(d, 'm'), os.path.join(d, 'm.js')
        with open(csrc, 'w') as f:
            f.write(r"""
#include <stdio.h>
#include "sagga_seq_core.h"
int main(void)
{
    unsigned n, k, s, len, st, o, w;
    for (n = SQ_BAR_MIN; n <= SQ_BAR_MAX; n++)
        for (k = 0; k < sq_metre_options((uint8_t)n); k++) {
            uint32_t m = sq_metre_option((uint8_t)n, (uint8_t)k);
            printf("B %u %u ", n, k);
            for (s = 0; s < 64; s++) putchar(sq_metre_beat((uint8_t)n, m, s) ? '1' : '0');
            putchar('\n');
        }
    for (len = 1; len <= 64; len++) for (st = 0; st < len; st += (st < 4 ? 1 : 7)) for (o = SQ_BAR_MIN; o <= SQ_BAR_MAX; o++) {
        printf("F %u %u %u", len, st, o);
        for (w = SQ_BAR_MIN; w <= SQ_BAR_MAX; w++) printf(" %u", sq_metre_follow((uint8_t)len, (uint8_t)st, (uint8_t)o, (uint8_t)w));
        putchar('\n');
    }
    return 0;
}
""")
        subprocess.run(['cc', '-std=c11', '-O2', '-I' + os.path.join(ROOT, 'firmware', 'src'), csrc,
                        os.path.join(ROOT, 'firmware', 'src', 'sagga_seq_core.c'), os.path.join(ROOT, 'firmware', 'src', 'sagga_beats.c'), '-o', exe], check=True)
        want = subprocess.run([exe], capture_output=True, text=True, check=True).stdout
        with open(js, 'w') as f:
            f.write("let P = null;\nconst N = {metre: " + json.dumps(ways) + "};\n" + page[pa:pb] + r"""
const out = [];
for (let n = 3; n <= 32; n++) N.metre[n].forEach((w, k) => {
  P = {metre: {bar_steps: n === 16 && k === 0 ? 0 : n, bar_beats: n === 16 && k === 0 ? [0, 0, 0, 0] : [0, 1, 2, 3].map(i => Math.floor(w[0] / 2 ** (8 * i)) % 256)}};
  let s = 'B ' + n + ' ' + k + ' ';
  for (let i = 0; i < 64; i++) s += beatAt(i) ? '1' : '0';
  if (barSteps() !== n || barWayNow() !== k) s += ' WRONG';
  out.push(s);
});
for (let len = 1; len <= 64; len++) for (let st = 0; st < len; st += (st < 4 ? 1 : 7)) for (let o = 3; o <= 32; o++) {
  let s = 'F ' + len + ' ' + st + ' ' + o;
  for (let w = 3; w <= 32; w++) s += ' ' + metreFollow(len, st, o, w);
  out.push(s);
}
console.log(out.join('\n'));
""")
        got = subprocess.run([node, js], capture_output=True, text=True)
        gl, wl = got.stdout.strip().split('\n'), want.strip().split('\n')
        bad = [i for i in range(min(len(gl), len(wl))) if gl[i] != wl[i]]
        check(got.returncode == 0 and len(gl) == len(wl) and len(wl) > 10000 and not bad,
              "the beats of the 217 ways and %d lengths that follow a new bar: the page says what the core says (%d differ%s) %s" % (
                  len(wl) - 217, len(bad), ": " + gl[bad[0]][:60] + " / " + wl[bad[0]][:60] if bad else "", got.stderr.strip()[-200:]))

    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print('  (the page: skipped, no playwright)')
        return
    import sagga_fw as FW
    fw, pr = os.path.join(d, 'fw'), os.path.join(d, 'pr')
    os.makedirs(fw)
    os.makedirs(pr)
    name = os.path.join(pr, 'metro.sgq')
    lines = ['track 1 length - 32', 'track 2 length - 19', 'track 3 flags - 32']
    for st in (0, 4, 8, 12):
        lines += ['step 0,0,%d flags - 3' % st, 'step 0,0,%d note 0 60' % st]
    apply('new', lines, name)
    state = FW.State(fw, pr, writer=FW.BootWriter(fw, mounts=lambda: [('/', ['rw'])]))
    state.editor.control = os.path.join(d, 'run')
    srv = FW.ThreadingHTTPServer(('127.0.0.1', 0), FW.make_handler(state))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            pg = br.new_page(viewport={'width': 1300, 'height': 900})
            errs = []
            pg.on('pageerror', lambda x: errs.append(str(x)))
            pg.on('dialog', lambda dg: dg.accept())
            pg.goto('http://127.0.0.1:%d/edit/metro.sgq' % port)
            pg.wait_for_timeout(800)
            pg.evaluate("V.pat=0;V.t=0;V.s=0;V.listen=false;V.tab='tracce';render()")
            marks = "[...document.querySelectorAll('.tr')][0].querySelectorAll('.c.bar').length + '/' + [...document.querySelectorAll('.tr')][0].querySelectorAll('.c.barl').length"
            check(pg.evaluate(marks) == '16/4' and 'metro' not in (pg.text_content('#main .row small') or ''), '4/4: a mark every four steps, a wider one every sixteen (%s)' % pg.evaluate(marks))
            pg.evaluate("V.tab='progetto';render()")
            box = pg.locator('input[data-g="metre"][data-f="bar"]')
            check(box.count() == 1 and box.input_value() == '16' and pg.locator('select[data-g="metre"][data-f="ways"] option').count() == 4,
                  'the Progetto tab: the bar (16) and its four ways')
            box.fill('14'); box.dispatch_event('change')
            pg.wait_for_timeout(150)
            waysel = pg.locator('select[data-g="metre"][data-f="ways"]')
            check(pg.evaluate('barSteps()') == 14 and waysel.locator('option').count() == 3 and '7/8 = 2+2+3' in (waysel.locator('option:checked').text_content() or ''),
                  'the bar typed, 14: 7/8, three ways, the usual one chosen (%s)' % (waysel.locator('option:checked').text_content() or ''))
            lens = pg.evaluate('[0, 1, 2, 3].map(t => P.track[t].length)')
            check(lens == [14, 28, 19, 16], 'the tracks on the bar follow (16 -> 14, 32 -> 28), the one of 19 stays, a TAPE track is not counted in steps (%s)' % lens)
            pg.evaluate("V.tab='tracce';render()")
            check(pg.evaluate(marks) == '14/4' and 'metro 7/8 (2+2+3)' in (pg.text_content('#main .row small') or ''),
                  'the tracks: the marks are the beats of 7/8 and its bar lines; the metre is named (%s)' % pg.evaluate(marks))
            first = pg.evaluate("[...[...document.querySelectorAll('.tr')][0].querySelectorAll('.c')].slice(0, 14).map(c => /barl/.test(c.className) ? 'L' : / bar/.test(c.className) ? 'b' : '.').join('')")
            check(first == '...b...b.....L', '... 2+2+3: a mark after steps 4 and 8, the bar line after 14 (%s)' % first)
            pg.click('#bsave')
            pg.wait_for_timeout(700)
            j = read(name)
            check(j['metre_now']['sig'] == '7/8' and [j['track'][t]['length'] for t in range(4)] == [14, 28, 19, 16] and j['tape_len'][3] == 4 * 14 * 96,
                  'saved: the file is in 7/8, the tracks as the page showed them (%s %s)' % (j['metre_now'], [j['track'][t]['length'] for t in range(4)]))
            pg.evaluate("V.tab='progetto';render()")
            pg.locator('select[data-g="metre"][data-f="ways"]').select_option('2')
            pg.wait_for_timeout(150)
            pg.click('#bsave')
            pg.wait_for_timeout(700)
            j = read(name)
            check(j['metre_now']['split'] == '3+2+2' and pg.evaluate('metreText()') == '7/8 (3+2+2)', 'the third way chosen and saved: 3+2+2 (%s)' % j['metre_now'])
            box = pg.locator('input[data-g="metre"][data-f="bar"]')
            box.fill('16'); box.dispatch_event('change')
            pg.wait_for_timeout(150)
            pg.click('#bsave')
            pg.wait_for_timeout(700)
            j = read(name)
            st = {(t, pp, s): x for t, pp, s, x in j['steps']}
            check(j['metre'] == {'bar_steps': 0, 'bar_beats': [0, 0, 0, 0]} and [j['track'][t]['length'] for t in range(4)] == [16, 32, 19, 16]
                  and all(st[(0, 0, s)]['flags'] == 3 for s in (0, 4, 8, 12)) and not any(x['flags'] & 64 for x in st.values()),
                  'the bar 16 again, saved: 4/4, the tracks and the pattern as they were (%s)' % [j['track'][t]['length'] for t in range(4)])
            check(not errs, 'no script errors (%s)' % errs[:2])
            br.close()
    finally:
        srv.shutdown()


def t025_melody():
    group("0.25 FOLLOW MELODY in the files: the fourth way of FOLLOW is a way; one there is not is put right")
    d = tempfile.mkdtemp()
    a, b = os.path.join(d, 'a.sgq'), os.path.join(d, 'b.sgq')
    r = apply('new', ['track 0 follow_mode - 3', 'track 1 follow_mode - 2'], a)
    j = read(a) if r.returncode == 0 else {}
    check(r.returncode == 0 and [t['follow_mode'] for t in j['track'][:3]] == [3, 2, 0], 'MELODY (3) on track 1, LEGATO on 2 (%s)' % [t['follow_mode'] for t in j.get('track', [])[:3]])
    r = apply(a, ['track 0 follow_mode - 4'], b)
    j = read(b) if r.returncode == 0 else {}
    check(r.returncode == 0 and [t['follow_mode'] for t in j['track'][:3]] == [4, 2, 0], '0.26: SMOOTH (4) on track 1 (%s)' % [t['follow_mode'] for t in j.get('track', [])[:3]])
    r = apply(a, ['track 0 follow_mode - 5'], b)
    j = read(b) if r.returncode == 0 else {}
    check(r.returncode == 0 and [t['follow_mode'] for t in j['track'][:3]] == [0, 2, 0], 'a way there is not: HOLD (%s)' % [t['follow_mode'] for t in j.get('track', [])[:3]])


def t026_files():
    group("0.26 in the files: THE CLICK and the scenes' metres (ext), the chords of the keyboard (kb_mode 3, 4), a pattern made in its bar with notes in its answers (thp: style's bit 7, vary's bit 7) - written, read back, put right")
    d = tempfile.mkdtemp()
    a, b = os.path.join(d, 'a.sgq'), os.path.join(d, 'b.sgq')
    r = apply('new', ['ext - click - 2', 'ext - count_in - 2', 'ext - click_out - 10', 'ext - click_note - 76', 'ext - click_level - 9', 'ext - scene_metre_on - 1',
                      'ext - scene_metre 3 10', 'ext - kb_mode - 4', 'metre - bar_steps - 14',
                      'thp 19 style - %d' % (11 | 0x40 | 0x80), 'thp 19 seed - 7', 'thp 19 func - 4', 'thp 19 vary - %d' % (40 | 0x80), 'thp 19 metre - 9',
                      'thp 20 style - 11', 'thp 20 seed - 7', 'thp 20 vary - %d' % (40 | 0x80), 'step 2,3,0 flags - 3', 'step 2,4,0 flags - 3'], a)
    j = read(a) if r.returncode == 0 else {}
    e = j.get('ext', {})
    check(r.returncode == 0 and [e.get(k) for k in ('click', 'count_in', 'click_out', 'click_note', 'click_level', 'scene_metre_on', 'kb_mode')] == [2, 2, 10, 76, 9, 1, 4]
          and e.get('scene_metre', [])[3] == 10 and len(e.get('scene_metre', [])) == 16, 'the click, the count, the scenes\' metres, CHORDS <C3 come back (%s %s)' % (e, r.stderr))
    check(j.get('thp', [{}] * 20)[19] == {'seed': 7, 'style': 11 | 0x40 | 0x80, 'func': 4, 'var': 0, 'vary': 40 | 0x80, 'energy': 0, 'metre': 9},
          'a pattern made in its bar, its answers with notes: kept as it is (%s)' % j.get('thp', [{}] * 20)[19])
    check(j.get('thp', [{}] * 21)[20]['vary'] == 100 and j['thp'][20]['style'] == 11, 'the notes\' bit on a pattern of 0.25 is no bit: a variation too large, put right (%s)' % j.get('thp', [{}] * 21)[20])
    r = apply(a, ['ext - click - 9', 'ext - count_in - 7', 'ext - click_out - 40', 'ext - click_level - 30', 'ext - click_note - 200', 'ext - scene_metre 3 250', 'ext - kb_mode - 9',
                  'thp 19 metre - 250', 'thp 19 vary - %d' % (120 | 0x80)], b)
    j2 = read(b) if r.returncode == 0 else {}
    e = j2.get('ext', {})
    check(r.returncode == 0 and e.get('click', 9) <= 2 and e.get('count_in', 9) <= 2 and e.get('click_out', 99) <= 16 and e.get('click_level', 99) <= 10 and e.get('click_note', 200) <= 127
          and e.get('scene_metre', [0] * 4)[3] == 0 and e.get('kb_mode') == 0, 'values there are not are put right as the FM-1 does (%s)' % e)
    check(j2.get('thp', [{}] * 20)[19].get('style') == 0, 'a pattern made in the bar of a metre there is not: nobody\'s (%s)' % j2.get('thp', [{}] * 20)[19])
    # a project of 0.25 (an image without the new fields at its end): read with the click off, the scenes leaving the metre alone
    img = open(a, 'rb').read()
    j3 = read(a)
    check(len(img) > 1000 and j3['ext']['click'] == 2, 'the image is written whole (%d B)' % len(img))


def t027_files():
    group("0.27 in the files: EVOLVE's RETURN (ext evo_ret: the RETURN + 1; 0, a project of before: DRIFT's switch says) - written, kept by an edit, put right")
    d = tempfile.mkdtemp()
    a, b, c = os.path.join(d, 'a.sgq'), os.path.join(d, 'b.sgq'), os.path.join(d, 'c.sgq')
    j = read(HW)
    check(j.get('ext', {}).get('evo_ret') == 0, 'a project of before has none: EVOLVE as it was (%s)' % j.get('ext', {}).get('evo_ret'))
    r = apply('new', ['ext - evo_ret - 41'], a)
    j = read(a) if r.returncode == 0 else {}
    check(r.returncode == 0 and j.get('ext', {}).get('evo_ret') == 41, 'RETURN 40 %% written and read back (%s %s)' % (j.get('ext', {}).get('evo_ret'), r.stderr))
    r = apply(a, ['project - bpm - 99'], b)
    j = read(b) if r.returncode == 0 else {}
    check(r.returncode == 0 and j.get('ext', {}).get('evo_ret') == 41 and j.get('project', {}).get('bpm') == 99, 'an edit of something else keeps it (%s)' % j.get('ext', {}))
    r = apply(a, ['ext - evo_ret - 150'], c)
    j = read(c) if r.returncode == 0 else {}
    check(r.returncode == 0 and j.get('ext', {}).get('evo_ret') == 0, 'a RETURN there is not is put right as the FM-1 does: none (%s)' % j.get('ext', {}).get('evo_ret'))


def t028_files_page():
    group("0.28 in the files and on the page: twelve tracks, a step's six notes, eight lanes - written, read back, put right; the page shows them and saves them")
    d = tempfile.mkdtemp()
    a, b = os.path.join(d, 'a.sgq'), os.path.join(d, 'b.sgq')
    lines = (['step 11,2,5 flags - 3'] + ['step 11,2,5 note %d %d' % (k, 50 + 3 * k) for k in range(6)] +
             ['step 11,2,5 lane 6 33', 'step 11,2,5 lane 7 99', 'track 11 lane_cc 6 20', 'track 11 lane_cc 7 21', 'track 11 lane_base 7 64', 'track 11 lane_flags 6 1',
              'scene 4 pattern 11 2', 'scene 4 mute_mask - %d' % 0xFFFF, 'lfo 2 enabled - 1', 'lfo 2 dest - 1', 'lfo 2 target - 11', 'lfox 2 trig - 12',
              'mod 0 src - 5', 'mod 0 src_i - 11', 'mod 0 dst - 3', 'mod 0 dst_i - 11', 'mod 0 amt - 50',
              'lfo 3 dest - 1', 'lfo 3 target - 12', 'lfox 3 trig - 13', 'mod 1 src - 5', 'mod 1 src_i - 12', 'mod 1 dst - 4', 'mod 1 dst_i - 15', 'mod 1 amt - 50',
              'lfo 4 dest - 0', 'lfo 4 target - 15'])
    r = apply('new', lines, a)
    j = read(a) if r.returncode == 0 else {}
    st = {(t, p, s): x for t, p, s, x in j.get('steps', [])}
    x = st.get((11, 2, 5), {})
    check(r.returncode == 0 and x.get('note') == [50, 53, 56, 59, 62, 65] and x.get('lane', [0] * 8)[6:] == [33, 99], 'a step of track 12: six notes, lanes 7 and 8 (%s %s)' % (x, r.stderr))
    tr = j.get('track', [{}] * 12)[11]
    check(tr.get('lane_cc', [0] * 8)[6:] == [20, 21] and tr.get('lane_base', [0] * 8)[7] == 64 and tr.get('lane_flags', [0] * 8)[6] == 1,
          'track 12: the settings of lanes 7 and 8 (%s)' % tr.get('lane_cc'))
    check(all(t.get('lane_cc', [0] * 8)[6:] == [73, 72] for t in j.get('track', [])[:11]), 'a new project: lanes 7 and 8 on CC 73 (attack) and 72 (release)')
    check(j['scene'][4]['pattern'][11] == 2 and j['scene'][4]['mute_mask'] == 0x0FFF, 'a scene: track 12\'s pattern; no mute for tracks 13-16 (%04x)' % j['scene'][4]['mute_mask'])
    check(j['lfo'][2]['target'] == 11 and j['lfox'][2]['trig'] == 12 and j['mod'][0]['src_i'] == 11 and j['mod'][0]['dst_i'] == 11,
          'an LFO on track 12, TRIG by track 12, a MOD from and to track 12 (%s %s)' % (j['lfo'][2], j['mod'][0]))
    check(j['lfo'][3]['target'] == 0 and j['lfox'][3]['trig'] == 0 and j['mod'][1]['src_i'] == 0 and j['mod'][1]['dst_i'] == 0 and j['lfo'][4]['target'] == 15,
          'a track past 12 is put right as the FM-1 does; an LFO on CC still has its sixteen channels (%s %s %s)' % (j['lfo'][3], j['mod'][1], j['lfo'][4]))
    r = apply(a, ['project - bpm - 99'], b)
    j2 = read(b) if r.returncode == 0 else {}
    st2 = {(t, p, s): x for t, p, s, x in j2.get('steps', [])}
    check(r.returncode == 0 and st2.get((11, 2, 5)) == x and j2['track'][11] == j['track'][11], 'an edit of something else keeps them (%s)' % r.stderr)
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print('  (skipped: no playwright)')
        return
    import sagga_fw as FW
    fw, pr = os.path.join(d, 'fw'), os.path.join(d, 'pr')
    os.makedirs(fw)
    os.makedirs(pr)
    shutil.copy(a, os.path.join(pr, 'dodici.sgq'))
    state = FW.State(fw, pr, writer=FW.BootWriter(fw, mounts=lambda: [('/', ['rw'])]))
    state.editor.control = os.path.join(d, 'run')
    srv = FW.ThreadingHTTPServer(('127.0.0.1', 0), FW.make_handler(state))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            pg = br.new_page(viewport={'width': 1300, 'height': 900})
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('dialog', lambda dg: dg.accept())
            pg.goto('http://127.0.0.1:%d/' % port)       # a view kept from sixteen tracks: track 16, its tape, lane 8 of a page that had six
            pg.evaluate("localStorage.setItem('sagga-ed-view', JSON.stringify({tab: 'tape', t: 15, tt: 14, lane: 9, pat: 2, s: 5}))")
            pg.goto('http://127.0.0.1:%d/edit/dodici.sgq' % port)
            pg.wait_for_timeout(800)
            check(pg.evaluate('[NT, NPOLY, NLANES]') == [12, 6, 8] and pg.evaluate('[V.t, V.tt, V.lane]') == [11, 11, 7] and not errs,
                  'the page takes the sizes from the file; a view of track 16 opens on track 12 (%s %s %s)' % (pg.evaluate('[NT, NPOLY, NLANES]'), pg.evaluate('[V.t, V.tt, V.lane]'), errs))
            pg.evaluate("V.tab='tracce';V.pat=2;V.t=11;V.s=5;render()")
            rows = pg.query_selector_all('.tr .lb')
            notes6 = pg.evaluate("[...document.querySelectorAll('select[data-g=\"step\"][data-f=\"note\"]')].map(s => +s.value)")
            lanes8 = pg.query_selector_all('select[data-g="step"][data-f="lane"]')
            check(len(rows) == 12 and notes6 == [50, 53, 56, 59, 62, 65] and len(lanes8) == 8, 'twelve tracks; the step shows its six notes and eight lanes (%d %s %d)' % (len(rows), notes6, len(lanes8)))
            pg.select_option('select[data-g="step"][data-i="11,2,5"][data-f="note"][data-e="5"]', '67')
            pg.select_option('select[data-g="step"][data-i="11,2,5"][data-f="lane"][data-e="7"]', '100')
            pg.evaluate("V.tab='lane';V.lane=7;V.erase=false;render()")
            opts = pg.evaluate("[...document.querySelectorAll('#main .row select')].map(s => s.options.length)")
            check(opts[0] == 12 and opts[2] == 8, 'the Lane tab: twelve tracks, eight lanes (%s)' % opts)
            pg.evaluate("V.tab='lfo';render()")
            tg = pg.evaluate("[2, 4].map(i => document.querySelector('select[data-g=\"lfo\"][data-i=\"' + i + '\"][data-f=\"target\"]').options.length)")
            trg = pg.evaluate("document.querySelector('select[data-g=\"lfox\"][data-i=\"2\"][data-f=\"trig\"]').options.length")
            check(tg == [12, 16] and trg == 13, 'an LFO: a track of twelve, a channel of sixteen; TRIG: the clock and twelve tracks (%s %s)' % (tg, trg))
            for tb in ('tracce', 'traccia', 'lane', 'tape', 'scene', 'song', 'catene', 'lfo', 'progetto'):
                pg.evaluate("V.tab='%s';render()" % tb)
            check(not errs, 'every tab renders (%s)' % errs)
            pg.click('#bsave')
            pg.wait_for_timeout(1200)
            check((pg.text_content('#status') or '').startswith('salvato'), 'Save (%s)' % pg.text_content('#status'))
            br.close()
    finally:
        srv.shutdown()
    j3 = read(os.path.join(pr, 'dodici.sgq'))
    st3 = {(t, p, s): x for t, p, s, x in j3['steps']}
    x3 = st3.get((11, 2, 5), {})
    check(x3.get('note', [0] * 6)[5] == 67 and x3.get('lane', [0] * 8)[7] == 100, 'in the file: the sixth note and lane 8 changed on the page (%s)' % x3)


def main():
    build()
    for t in (t_converter, t_editor_backend, t_page_lists, t_fm1_in_out, t_page, t015_converter, t015_backend, t015_bridge, t015_page, t023_page, t0232_tape_link, t024_copies, t025_preview,
              t025_metre, t025_melody, t026_files, t027_files, t028_files_page):
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
