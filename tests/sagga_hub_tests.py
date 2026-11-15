#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA HUB tests: the USB-MIDI packetizer and SLIP (both ways, against the C header too), the PC link over a
pseudo-terminal with fake cards, the firmware library web page with a fake installer. No Pi, no hardware.

    python3 tests/sagga_hub_tests.py            (from the repository root)
"""
import json
import os
import pty
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HUB = os.path.join(ROOT, 'tools', 'hub')                   # in the repository (tests/ next to tools/)
if not os.path.isdir(HUB):
    HUB = os.path.join(HERE, 'hub')                        # in the unpacked zip
RP2040 = os.path.join(HUB, 'rp2040')
if not os.path.isdir(RP2040):
    RP2040 = os.path.join(HERE, 'rp2040')
sys.path.insert(0, HUB)
import usbmidi_pkt as U                                    # noqa: E402
import sagga_pc_host as PC                                 # noqa: E402
import sagga_fw as FW                                      # noqa: E402

FAILS = []
CHECKS = [0]


def check(cond, what):
    CHECKS[0] += 1
    if not cond:
        FAILS.append(what)
        print('  FAIL:', what)


def t_packets():
    print('packets: MIDI bytes <-> USB-MIDI packets, running status, SysEx, realtime inside a SysEx')
    p = U.Packetizer(1)
    out = p.feed(bytes([0x90, 60, 100, 0x80, 60, 0]))
    check(out == [bytes([0x19, 0x90, 60, 100]), bytes([0x18, 0x80, 60, 0])], 'note on / off on cable 1 (%s)' % out)
    out = p.feed(bytes([0x90, 60, 100, 64, 90, 67, 0]))             # running status
    check([U.unpack(x)[1] for x in out] == [bytes([0x90, 60, 100]), bytes([0x90, 64, 90]), bytes([0x90, 67, 0])], 'running status expands')
    out = p.feed(bytes([0xC0, 5, 0xD0, 7, 0xE0, 0, 64]))
    check([x[0] & 15 for x in out] == [0xC, 0xD, 0xE] and U.unpack(out[0])[1] == bytes([0xC0, 5]), 'two-byte and three-byte channel messages')
    out = p.feed(bytes([0xF0, 1, 2, 3, 4, 5, 0xF7]))                 # 7 bytes: 4, 4, 5
    check([x[0] & 15 for x in out] == [0x4, 0x4, 0x5] and out[-1][1] == 0xF7, 'SysEx of 7 bytes: two CIN 4 and a CIN 5 (%s)' % out)
    out = p.feed(bytes([0xF0, 1, 0xF7]))
    check([x[0] & 15 for x in out] == [0x7], 'SysEx of 3 bytes: one CIN 7')
    out = p.feed(bytes([0xF0, 1, 2, 0xF7]))
    check([x[0] & 15 for x in out] == [0x4, 0x5], 'SysEx of 4 bytes: CIN 4 then 5')
    out = p.feed(bytes([0xF0, 1, 2, 3, 0xF7]))
    check([x[0] & 15 for x in out] == [0x4, 0x6], 'SysEx of 5 bytes: CIN 4 then 6')
    out = p.feed(bytes([0xF0, 1, 0xF8, 2, 0xF7]))
    check([x[0] & 15 for x in out] == [0xF, 0x4, 0x5] and out[0][1] == 0xF8 and out[1][1:4] == bytes([0xF0, 1, 2]) and out[2][1] == 0xF7,
          'a clock inside a SysEx goes out at once, the SysEx stays whole (%s)' % out)
    out = p.feed(bytes([0xF8, 0xFA, 0xFC]))
    check([x[1] for x in out] == [0xF8, 0xFA, 0xFC] and all(x[0] == 0x1F for x in out), 'realtime: CIN F')
    out = p.feed(bytes([0xF1, 3, 0xF2, 1, 2, 0xF6]))
    check([x[0] & 15 for x in out] == [0x2, 0x3, 0x5], 'system common: F1 (2), F2 (3), F6 (1)')
    out = p.feed(bytes([0xF0, 1, 2, 0x90, 60, 1]))                   # a status cuts the SysEx short
    check([x[0] & 15 for x in out] == [0x4, 0x5, 0x9] and out[1][1] == 0xF7, 'a SysEx cut by a note: ended with an F7, then the note (%s)' % out)
    check(U.unpack(bytes([0x19, 0x90, 60, 100])) == (1, bytes([0x90, 60, 100])) and U.unpack(bytes([0x10, 1, 2, 3])) is None, 'unpack, and CIN 0 is not a packet')
    # SLIP
    f = U.slip_encode(bytes([0x04, 0xF0, 0xC0, 0xDB]))
    check(f == bytes([0xC0, 0x04, 0xF0, 0xDB, 0xDC, 0xDB, 0xDD, 0xC0]), 'SLIP escapes END and ESC (%s)' % f.hex())
    d = U.SlipDecoder()
    got = d.feed(f[:3]) + d.feed(f[3:]) + d.feed(bytes([1, 2, 3, 4, 5, 6, 0xC0])) + d.feed(U.slip_encode(bytes([0x19, 0x90, 1, 2])))
    check(got == [bytes([0x04, 0xF0, 0xC0, 0xDB]), bytes([0x19, 0x90, 1, 2])], 'SLIP decodes across reads, drops a long frame (%s)' % got)


def t_c_header():
    print('the C header slip_midi.h agrees with the Python (host test, and bytes compared)')
    src = os.path.join(RP2040, 'test_slip_midi.c')
    exe = os.path.join(tempfile.gettempdir(), 'sagga_slip_test_%d' % os.getpid())
    r = subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', src, '-o', exe], capture_output=True, text=True)
    check(r.returncode == 0, 'test_slip_midi.c compiles (%s)' % r.stderr[-300:])
    if r.returncode == 0:
        r = subprocess.run([exe], capture_output=True, text=True)
        check(r.returncode == 0 and 'ok' in r.stdout, 'the C test passes (%s)' % r.stdout.strip())
        os.remove(exe)
    # the same frame from both sides
    c = r'''#include <stdio.h>
#include "slip_midi.h"
int main(void){uint8_t o[10];const uint8_t p[4]={0x04,0xF0,0xC0,0xDB};size_t n=slip_encode_pkt(p,o);for(size_t i=0;i<n;i++)printf("%02x",o[i]);printf("\n");return 0;}'''
    cs = os.path.join(tempfile.gettempdir(), 'sagga_slip_cmp_%d.c' % os.getpid())
    open(cs, 'w').write(c)
    r = subprocess.run(['cc', '-std=c11', '-I', RP2040, cs, '-o', exe], capture_output=True, text=True)
    if r.returncode == 0:
        out = subprocess.run([exe], capture_output=True, text=True).stdout.strip()
        check(out == U.slip_encode(bytes([0x04, 0xF0, 0xC0, 0xDB])).hex(), 'C and Python encode the same bytes (%s)' % out)
        os.remove(exe)
    os.remove(cs)


def t_pc_link():
    print('the PC link: packets from the "RP2040" reach the right card, bytes from a card go out as frames')
    import tty
    m, s = pty.openpty()                                   # the UART: we are the RP2040 on m, the link on s
    tty.setraw(s)                                          # (bytes as they are: no line discipline, no EOT)
    tty.setraw(m)
    r1, w1 = os.pipe()                                     # card 1: the link writes w1 (we read r1); it reads c1r
    c1r, c1w = os.pipe()
    r2, w2 = os.pipe()
    c2r, c2w = os.pipe()
    # a "card" fd must be read and written on the same fd: give the link a socketpair instead
    import socket
    a1, b1 = socket.socketpair()
    a2, b2 = socket.socketpair()
    for x in (a1, b1, a2, b2):
        x.setblocking(False)
    os.set_blocking(s, False)
    link = PC.Link(s, [b1.fileno(), b2.fileno()])
    done = threading.Event()
    th = threading.Thread(target=link.pump, args=(done,), daemon=True)
    th.start()
    # RP2040 -> Pi: a note on cable 0, a CC on cable 1, a SysEx on cable 0
    frames = U.slip_encode(bytes([0x09, 0x90, 60, 100])) + U.slip_encode(bytes([0x1B, 0xB0, 7, 99]))
    frames += b''.join(U.slip_encode(p) for p in U.Packetizer(0).feed(bytes([0xF0, 1, 2, 3, 4, 0xF7])))
    os.write(m, frames)
    time.sleep(0.4)
    got1 = b''
    got2 = b''
    try:
        got1 = a1.recv(100)
    except BlockingIOError:
        pass
    try:
        got2 = a2.recv(100)
    except BlockingIOError:
        pass
    check(got1 == bytes([0x90, 60, 100, 0xF0, 1, 2, 3, 4, 0xF7]), 'cable 0 -> card 1: the note and the whole SysEx (%s)' % got1.hex())
    check(got2 == bytes([0xB0, 7, 99]), 'cable 1 -> card 2: the CC (%s)' % got2.hex())
    # Pi -> RP2040: bytes written to card 2 come out as frames with cable 1
    a2.send(bytes([0x90, 64, 1, 0xF8]))
    time.sleep(0.4)
    out = os.read(m, 200)
    d = U.SlipDecoder()
    pk = d.feed(out)
    check(pk == [bytes([0x19, 0x90, 64, 1]), bytes([0x1F, 0xF8, 0, 0])], 'card 2 -> cable 1: a note and a clock as packets (%s)' % [x.hex() for x in pk])
    check(link.rx_pkts == 4 and link.bad == 0, 'counters: 4 packets in, none bad (%d, %d)' % (link.rx_pkts, link.bad))
    done.set()
    th.join(1)
    for x in (a1, b1, a2, b2):
        x.close()
    for fd in (m, s, r1, w1, c1r, c1w, r2, w2, c2r, c2w):
        os.close(fd)
    # the card finder
    with tempfile.NamedTemporaryFile('w', suffix='.cards', delete=False) as f:
        f.write(' 0 [vc4hdmi        ]: vc4-hdmi - vc4-hdmi\n 1 [SAGGAM8A       ]: VirMIDI - VirMIDI\n'
                ' 2 [SAGGAPC1       ]: VirMIDI - VirMIDI\n 3 [SAGGAPC2       ]: VirMIDI - VirMIDI\n')
        cards = f.name
    check(PC.virmidi_rawmidi('SAGGAPC2', cards) == '/dev/snd/midiC3D0' and PC.virmidi_rawmidi('SAGGAPC9', cards) is None, 'the virtual cards are found by id')
    os.remove(cards)


def t_fw_page():
    print('the firmware library: list, probe, install through a fake installer, upload, projects')
    d = tempfile.mkdtemp()
    fw, pr = os.path.join(d, 'fw'), os.path.join(d, 'projects')
    os.makedirs(fw)
    os.makedirs(pr)
    open(os.path.join(fw, 'sagga-seq-0.9.fwsc'), 'wb').write(b'x' * 1000)
    open(os.path.join(fw, 'relitto-0.1.fwsc'), 'wb').write(b'y' * 500)
    open(os.path.join(fw, 'notes.txt'), 'w').write('no')
    open(os.path.join(pr, 'sagga-001.sgq'), 'wb').write(b'SGQA' + b'\0' * 20)
    fake = os.path.join(d, 'fake_install.py')
    open(fake, 'w').write('''import sys, time
if "--info" in sys.argv:
    print("FM-1_992  [running]  port: Felucca MIDI 1"); sys.exit(0)
print("package: SAGGA SEQ 0.10 (%s)" % sys.argv[-1]); sys.stdout.flush()
for i in range(3):
    print("\\rwriting %d%%" % (i * 40), end=""); sys.stdout.flush(); time.sleep(0.05)
print("\\ndone: FM-1_992")
sys.exit(0 if "sagga" in sys.argv[-1] else 4)
''')
    FW.INSTALLER = fake
    state = FW.State(fw, pr, writer=FW.BootWriter(fw, mounts=lambda: [('/', ['rw'])]))
    srv = FW.ThreadingHTTPServer(('127.0.0.1', 0), FW.make_handler(state))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = 'http://127.0.0.1:%d' % port

    def get(path):
        return urllib.request.urlopen(base + path, timeout=5)
    s = json.loads(get('/api/state').read())
    check([p['name'] for p in s['packages']] == ['relitto-0.1.fwsc', 'sagga-seq-0.9.fwsc'] and s['projects'][0]['name'] == 'sagga-001.sgq',
          'the lists: only .fwsc and .sgq files (%s)' % [p['name'] for p in s['packages']])
    check(s['device'] == ['FM-1_992', 'running', 'Felucca MIDI 1'] and not s['busy'], 'the FM-1 probed through the installer (%s)' % (s['device'],))
    check(b'SAGGA HUB' in get('/').read(), 'the page')
    req = urllib.request.Request(base + '/api/install?file=sagga-seq-0.9.fwsc', method='POST')
    check(json.loads(urllib.request.urlopen(req, timeout=5).read())['error'] is None, 'install accepted')
    req = urllib.request.Request(base + '/api/install?file=relitto-0.1.fwsc', method='POST')
    try:
        urllib.request.urlopen(req, timeout=5)
        check(False, 'a second install while one runs is refused')
    except urllib.error.HTTPError as e:
        check(e.code == 400 and json.loads(e.read())['error'] == 'an install is running', 'a second install while one runs is refused')
    time.sleep(0.6)
    s = json.loads(get('/api/state').read())
    check(s['result'] == 'ok' and s['job'] == 'sagga-seq-0.9.fwsc' and any('writing 80%' in ln for ln in s['log']) and s['log'][-1] == 'done: ok',
          'the install ran, its progress lines in the log (%s)' % s['log'][-3:])
    req = urllib.request.Request(base + '/api/install?file=relitto-0.1.fwsc', method='POST')
    urllib.request.urlopen(req, timeout=5)
    time.sleep(0.6)
    s = json.loads(get('/api/state').read())
    check(s['result'] == 'failed 4', 'a failing install says so (%s)' % s['result'])
    req = urllib.request.Request(base + '/api/install?file=../etc/passwd', method='POST')
    try:
        urllib.request.urlopen(req, timeout=5)
        check(False, 'a path outside the folder is refused')
    except urllib.error.HTTPError as e:
        check(e.code == 400, 'a path outside the folder is refused')
    body = (b'--B\r\nContent-Disposition: form-data; name="f"; filename="new-0.2.fwsc"\r\nContent-Type: application/octet-stream\r\n\r\n'
            b'\x00\xc0\xff' + b'z' * 300 + b'\r\n--B--\r\n')
    req = urllib.request.Request(base + '/api/upload', data=body, method='POST', headers={'Content-Type': 'multipart/form-data; boundary=B'})

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    try:
        urllib.request.build_opener(NoRedirect).open(req, timeout=5)
    except urllib.error.HTTPError as e:
        check(e.code == 303, 'upload answers with a redirect to the page')
    check(os.path.isfile(os.path.join(fw, 'new-0.2.fwsc')) and os.path.getsize(os.path.join(fw, 'new-0.2.fwsc')) == 303, 'the uploaded package is in the folder, whole')
    check(get('/projects/sagga-001.sgq').read().startswith(b'SGQA'), 'a project downloads')
    try:
        get('/projects/../fw/notes.txt')
        check(False, 'no path escape on downloads')
    except urllib.error.HTTPError as e:
        check(e.code == 404, 'no path escape on downloads')
    # 0.11: the converter: a project downloads as .mid, a .mid uploads as a project of TAPE tracks, a .sgq uploads as it is
    tool = os.path.join(ROOT, 'build', 'sagga_sgqmid')
    srcdir = os.path.join(ROOT, 'tools', 'sgqmid')                               # the repository ...
    inc = os.path.join(ROOT, 'firmware', 'src')
    hwp = os.path.join(ROOT, 'tools', 'hwtest', 'hwtest.sgq')
    if not os.path.isdir(srcdir):                                                 # ... or the unpacked zip
        srcdir = inc = os.path.join(HERE, 'sgqmid')
        tool = os.path.join(d, 'sagga_sgqmid')
        hwp = os.path.join(HERE, 'hub', 'hwtest.sgq')
    if not os.path.isfile(tool):
        subprocess.run(['cc', '-std=c11', '-O2', '-I' + inc, os.path.join(srcdir, 'sagga_sgqmid.c'),
                        os.path.join(inc, 'sagga_seq_core.c'), os.path.join(inc, 'sagga_beats.c'), '-o', tool], check=True)
    FW.SGQMID = tool
    if not os.path.isfile(hwp):
        print('  (no hwtest.sgq here: the converter checks are skipped)')
        srv.shutdown()
        return
    hw = open(hwp, 'rb').read()
    open(os.path.join(pr, 'hw.sgq'), 'wb').write(hw)
    mid = get('/projects/hw.mid').read()
    check(mid[:4] == b'MThd' and len(mid) > 100, 'a project downloads as a MIDI file (%d bytes)' % len(mid))
    body = (b'--B\r\nContent-Disposition: form-data; name="f"; filename="song.mid"\r\nContent-Type: audio/midi\r\n\r\n' + mid + b'\r\n--B--\r\n')
    req = urllib.request.Request(base + '/api/upload', data=body, method='POST', headers={'Content-Type': 'multipart/form-data; boundary=B'})
    try:
        urllib.request.build_opener(NoRedirect).open(req, timeout=10)
    except urllib.error.HTTPError as e:
        check(e.code == 303, 'a .mid upload answers with the redirect')
    back = os.path.join(pr, 'song.sgq')
    check(os.path.isfile(back) and open(back, 'rb').read()[:4] == b'SGQB', 'the MIDI file became song.sgq in the projects folder')
    body = (b'--B\r\nContent-Disposition: form-data; name="f"; filename="mine.sgq"\r\nContent-Type: application/octet-stream\r\n\r\n' + hw + b'\r\n--B--\r\n')
    req = urllib.request.Request(base + '/api/upload', data=body, method='POST', headers={'Content-Type': 'multipart/form-data; boundary=B'})
    try:
        urllib.request.build_opener(NoRedirect).open(req, timeout=10)
    except urllib.error.HTTPError as e:
        check(e.code == 303, 'a .sgq upload answers with the redirect')
    check(open(os.path.join(pr, 'mine.sgq'), 'rb').read() == hw, 'the .sgq is in the projects folder, whole')
    FW.ROLL = os.path.join(ROOT, 'tools', 'hub', 'roll.html') if os.path.isdir(os.path.join(ROOT, 'tools', 'hub')) else os.path.join(HERE, 'hub', 'roll.html')
    page = get('/roll/song.sgq').read()
    check(b'SAGGA PIANO ROLL' in page and b'parseSMF' in page, 'the piano roll page serves for a project')
    try:
        get('/roll/nothing.sgq'); check(False, 'no roll for a project that is not there')
    except urllib.error.HTTPError as e:
        check(e.code == 404, 'no roll for a project that is not there')
    # a save: the MIDI of track 3 only (one note) over hw.sgq -> track 3 becomes a TAPE of one note, tracks 1-2 stay steps
    import struct as _st
    def var(v):
        b = [v & 0x7F]; v >>= 7
        while v: b.append((v & 0x7F) | 0x80); v >>= 7
        return bytes(reversed(b))
    t3 = b'\x00\xff\x03\x0bT3 ch3 TAPE' + var(0) + bytes([0x92, 72, 100]) + var(300) + bytes([0x82, 72, 0]) + b'\x00\xff\x2f\x00'
    tempo = b'\x00\xff\x51\x03' + (468750).to_bytes(3, 'big') + b'\x00\xff\x2f\x00'
    smf = b'MThd' + _st.pack('>IHHH', 6, 1, 2, 384) + b'MTrk' + _st.pack('>I', len(tempo)) + tempo + b'MTrk' + _st.pack('>I', len(t3)) + t3
    req = urllib.request.Request(base + '/api/roll?file=hw.sgq', data=smf, method='POST', headers={'Content-Type': 'audio/midi'})
    r = urllib.request.urlopen(req, timeout=10)
    check(r.status == 200 and b'1 notes on 1 tapes' in r.read(), 'the roll saves over the project')
    check(os.path.isfile(os.path.join(pr, 'hw.sgq.bak')) and open(os.path.join(pr, 'hw.sgq.bak'), 'rb').read() == hw, 'the project as it was is kept in .bak')
    r = subprocess.run([tool, 'sgq2mid', os.path.join(pr, 'hw.sgq'), os.path.join(d, 'after.mid')], capture_output=True, text=True)
    check('4 tracks' in r.stderr, 'the saved project still has its four tracks with notes (%s)' % r.stderr.strip())
    body = (b'--B\r\nContent-Disposition: form-data; name="f"; filename="x.mid"\r\nContent-Type: audio/midi\r\n\r\nnot a midi file\r\n--B--\r\n')
    req = urllib.request.Request(base + '/api/upload', data=body, method='POST', headers={'Content-Type': 'multipart/form-data; boundary=B'})
    try:
        urllib.request.build_opener(NoRedirect).open(req, timeout=10)
        check(False, 'a file that is not MIDI is refused')
    except urllib.error.HTTPError as e:
        check(e.code == 400 and b'non si converte' in e.read(), 'a file that is not MIDI is refused with the reason')
    # the BootWriter on a read-only partition: remount rw, write, remount ro, under the lock
    calls = []
    bw = FW.BootWriter(os.path.join(d, 'boot', 'sagga', 'firmware'), run=lambda cmd: calls.append(cmd),
                       mounts=lambda: [('/', ['rw']), (os.path.join(d, 'boot'), ['ro', 'noatime'])], lock=None)
    os.makedirs(os.path.join(d, 'boot'))
    bw.write(os.path.join(d, 'boot', 'sagga', 'firmware', 'a.fwsc'), b'abc')
    check(calls[0] == ['mount', '-o', 'remount,rw', os.path.join(d, 'boot')] and calls[-1] == ['mount', '-o', 'remount,ro', os.path.join(d, 'boot')]
          and open(os.path.join(d, 'boot', 'sagga', 'firmware', 'a.fwsc'), 'rb').read() == b'abc', 'a read-only boot partition is opened for the write and closed again (%s)' % calls)
    srv.shutdown()


def t_patterns():
    print('0.11: the patterns of the genres: the stock files, a new one kept, the page lists and deletes')
    import sagga_patterns as P
    d = tempfile.mkdtemp()
    stock, mine = os.path.join(d, 'stock'), os.path.join(d, 'projects', 'patterns')
    os.makedirs(stock)
    open(os.path.join(stock, 'TECHNO.txt'), 'w').write('# a comment\nKICK\tX...X...X..xX...\t-\nKICK\tX.x.X...X...X...\t-\n'
                                                       'BASS\t..x-..x.\t..0...7.\nBASS\t..x?\t..0.\nNOPE\tx...\t-\n')
    lib = P.Patterns(mine, stock=stock)
    check(lib.of('TECHNO', 'KICK') == [('X...X...X..xX...', None), ('X.x.X...X...X...', None)] and lib.of('TECHNO', 'BASS') == [('..x-..x.', '..0...7.')],
          'the stock file read: two kicks, one bass (a bad line and an unknown part left out) (%s)' % lib.of('TECHNO', 'BASS'))
    check(lib.summary()['TECHNO'] == {'KICK': 2, 'BASS': 1} and lib.summary()['HOUSE'] == {}, 'the counts (%s)' % lib.summary()['TECHNO'])
    k = lib.add('TECHNO', 'KICK', 'X...X.x.X...X...', None)
    check(k == 2 and os.path.isfile(os.path.join(mine, 'TECHNO.txt')) and len(lib.of('TECHNO', 'KICK')) == 3 and len(lib.of('TECHNO', 'BASS')) == 1,
          'a new kick kept: the genre\'s file starts from the stock one (%d)' % k)
    check(open(os.path.join(stock, 'TECHNO.txt')).read().count('KICK') == 2, 'the stock file is not touched')
    for bad in (('KICK', 'X..y', None), ('BASS', 'x...', None), ('BASS', 'x...', 'z...'), ('PROG', 'x...', None), ('KICK', '....', None), ('KICK', '-x..', None)):
        try:
            lib.add('TECHNO', *bad); check(False, 'refused: %s' % (bad,))
        except ValueError:
            check(True, '')
    check(lib.delete('TECHNO', 'KICK', 0) and lib.of('TECHNO', 'KICK')[0][0] == 'X.x.X...X...X...' and not lib.delete('TECHNO', 'KICK', 9), 'a pattern deleted, by its number')
    # the page
    fw, pr = os.path.join(d, 'fw'), os.path.join(d, 'projects')
    os.makedirs(fw)
    P.STOCK = stock
    state = FW.State(fw, pr, writer=FW.BootWriter(fw, mounts=lambda: [('/', ['rw'])]), pat_writer=FW.BootWriter(mine, mounts=lambda: [('/', ['rw'])]))
    state.patterns.stock = stock
    srv = FW.ThreadingHTTPServer(('127.0.0.1', 0), FW.make_handler(state))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = 'http://127.0.0.1:%d' % srv.server_address[1]
    j = json.loads(urllib.request.urlopen(base + '/api/patterns?genre=techno', timeout=5).read())
    check(j['genre'] == 'TECHNO' and len(j['genres']) == 25 and [p['part'] for p in j['parts']] == ['KICK', 'BASS'] and len(j['parts'][0]['list']) == 2,
          'GET /api/patterns: the genre part by part (%s)' % [(p['part'], len(p['list'])) for p in j['parts']])
    req = urllib.request.Request(base + '/api/patterns/delete?genre=TECHNO&part=BASS&i=0', method='POST')
    check(json.loads(urllib.request.urlopen(req, timeout=5).read())['ok'] and not lib.of('TECHNO', 'BASS'), 'POST delete: the bass is gone')
    check(b'PATTERN SUL PI' in urllib.request.urlopen(base + '/', timeout=5).read(), 'the page has the patterns')
    srv.shutdown()


def t_progressions():
    print('0.11: the progressions of the genres: the words, the stock files, one kept, by likeness; the page lists, adds and deletes')
    import sagga_progs as Q
    d = tempfile.mkdtemp()
    stock, mine = os.path.join(d, 'stock'), os.path.join(d, 'projects', 'progressions')
    os.makedirs(stock)
    open(os.path.join(stock, 'HOUSE.txt'), 'w').write('# house\nSATISFYING\tii7 V7 Imaj7\nDREAMY\tImaj7 IVmaj7\tthe deep one\n'
                                                      'EPIC\ti bVI bVII i\n-\tI IV\nCALM\tI\nDREAMY\tImaj7 Xmaj7\n')
    lib = Q.Progressions(mine, stock=stock)
    check([(m, Q.name(r)) for m, r, _ in lib.of('HOUSE')] == [('SATISFYING', 'ii7 V7 Imaj7'), ('DREAMY', 'Imaj7 IVmaj7'), ('EPIC', 'i bVI bVII i'), ('ANY', 'I IV')],
          'the stock file read (an unknown mood, a chord that is none: left out) (%s)' % [Q.name(r) for _, r, _ in lib.of('HOUSE')])
    check(lib.of('HOUSE', 'DREAMY')[0][2] == 'the deep one' and lib.summary()['HOUSE'] == {'SATISFYING': 1, 'DREAMY': 1, 'EPIC': 1, 'ANY': 1}, 'its name, the counts')
    ref = [(s, sh) for s, sh, _, _ in Q.parse('Imaj7 IV')]
    check([Q.name(r) for _, r, _ in lib.ordered('HOUSE', 'ANY', ref)][:2] == ['Imaj7 IVmaj7', 'I IV'], 'by likeness to Imaj7 IV (%s)' % [Q.name(r) for _, r, _ in lib.ordered('HOUSE', 'ANY', ref)])
    check(Q.distance(ref, Q.parse('Imaj7 IV')) == 0 and Q.distance([(0, 10), (8, 9)], Q.parse('bVI i')) < Q.distance([(0, 10), (8, 9)], Q.parse('ii V')),
          'the same: 0; turned round: nearer than another')
    k = lib.add('HOUSE', 'DREAMY', Q.parse('IVmaj9:8 Imaj9:8^1'))
    check(k == 1 and os.path.isfile(os.path.join(mine, 'HOUSE.txt')) and 'DREAMY\tIVmaj9:8 Imaj9:8^1' in open(os.path.join(mine, 'HOUSE.txt')).read(),
          'a new one kept: the 2nd DREAMY, the file started from the stock one (%d)' % k)
    for bad in (('HOUSE', 'CALM', [(0, 9, 0, 0)]), ('NOPE', 'ANY', [(0, 9, 0, 0)]), ('HOUSE', 'ANY', []), ('HOUSE', 'ANY', [(12, 9, 0, 0)]), ('HOUSE', 'ANY', [(0, 99, 0, 0)])):
        try:
            lib.add(*bad); check(False, 'refused: %s' % (bad,))
        except ValueError:
            check(True, '')
    for bad in ('', 'X', 'i:99', 'Iwhat', 'i ' * 9):
        try:
            Q.parse(bad); check(False, 'not a progression: %r' % bad)
        except ValueError:
            check(True, '')
    # the page
    fw, pr = os.path.join(d, 'fw'), os.path.join(d, 'projects')
    os.makedirs(fw)
    state = FW.State(fw, pr, writer=FW.BootWriter(fw, mounts=lambda: [('/', ['rw'])]), pat_writer=FW.BootWriter(mine, mounts=lambda: [('/', ['rw'])]))
    state.progs.stock = stock
    srv = FW.ThreadingHTTPServer(('127.0.0.1', 0), FW.make_handler(state))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = 'http://127.0.0.1:%d' % srv.server_address[1]
    j = json.loads(urllib.request.urlopen(base + '/api/progressions?genre=house', timeout=5).read())
    check(j['genre'] == 'HOUSE' and len(j['genres']) == 25 and j['moods'][0] == 'ANY' and len(j['list']) == 5 and j['list'][4]['chords'] == 'IVmaj9:8 Imaj9:8^1',
          'GET /api/progressions: the genre\'s, with their moods (%s)' % [x['chords'] for x in j['list']])
    req = urllib.request.Request(base + '/api/progressions/add?genre=HOUSE&mood=EPIC&chords=' + urllib.parse.quote('i bVI bIII bVII'), method='POST')
    check(json.loads(urllib.request.urlopen(req, timeout=5).read())['i'] == 1 and len(lib.of('HOUSE', 'EPIC')) == 2, 'POST add: written on the page, the 2nd EPIC')
    req = urllib.request.Request(base + '/api/progressions/add?genre=HOUSE&mood=EPIC&chords=nope', method='POST')
    try:
        urllib.request.urlopen(req, timeout=5); check(False, 'a bad one refused')
    except urllib.error.HTTPError as e:
        check(e.code == 400, 'POST add: not a progression: 400')
    req = urllib.request.Request(base + '/api/progressions/delete?genre=HOUSE&i=0', method='POST')
    check(json.loads(urllib.request.urlopen(req, timeout=5).read())['ok'] and not lib.of('HOUSE', 'SATISFYING'), 'POST delete: the first is gone')
    check(b'PROGRESSIONI SUL PI' in urllib.request.urlopen(base + '/', timeout=5).read(), 'the page has the progressions')
    srv.shutdown()


def hub_zip(top='sagga-hub-9.9', script=None, page=None, drop=(), extra=None, link=None):
    """0.20.1: a sagga-hub zip as make_release.sh makes it (only the files the update looks at)"""
    import io, zipfile
    files = {'install_hub.sh': script or '#!/bin/sh\necho "fake install $*"\necho "sagga_sgqmid built"\n',
             'hub/sagga_fw.py': page or 'ROUTES = (\'/api/update\',)\n', 'hub/sagga-fw.service': '[Unit]\n',
             'fm1_install.py': '', 'sagga_grid_bridge.py': ''}
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w') as z:
        for k, v in files.items():
            if k not in drop:
                z.writestr(top + '/' + k, v)
        for k, v in (extra or {}).items():
            z.writestr(k, v)
        if link:
            zi = zipfile.ZipInfo(top + '/' + link)
            zi.external_attr = 0o120777 << 16
            z.writestr(zi, '/etc/passwd')
    return b.getvalue()


def t_update_delete():
    print('0.20.1: a package away; the Pi updates itself from a sagga-hub zip (checked, a unit of its own, the log after)')
    d = tempfile.mkdtemp()
    fw, pr, up = os.path.join(d, 'fw'), os.path.join(d, 'projects'), os.path.join(d, 'run', 'sagga-update')
    os.makedirs(fw)
    os.makedirs(pr)
    open(os.path.join(fw, 'sagga-0.19.fwsc'), 'wb').write(b'x' * 100)
    open(os.path.join(fw, 'sagga-0.20.fwsc'), 'wb').write(b'y' * 100)
    open(os.path.join(fw, 'notes.txt'), 'w').write('no')
    fake = os.path.join(d, 'fake_install.py')
    open(fake, 'w').write('import sys, time\nif "--info" in sys.argv:\n    print("FM-1_970  [running]  port: Felucca MIDI 1"); sys.exit(0)\n'
                          'time.sleep(0.8)\nprint("done")\n')
    FW.INSTALLER = fake
    FW.SYSTEMD_RUN = None
    FW.pc_enabled = lambda: False
    state = FW.State(fw, pr, writer=FW.BootWriter(fw, mounts=lambda: [('/', ['rw'])]), upd_dir=up)
    srv = FW.ThreadingHTTPServer(('127.0.0.1', 0), FW.make_handler(state))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = 'http://127.0.0.1:%d' % srv.server_address[1]

    def post(path, data=None, guard=True, ctype=None):
        h = {FW.GUARD: '1'} if guard else {}
        if ctype:
            h['Content-Type'] = ctype
        req = urllib.request.Request(base + path, data=data, method='POST', headers=h)
        try:
            r = urllib.request.urlopen(req, timeout=10)
            return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def upload(zb, name='sagga-hub-9.9.zip', guard=True):
        body = (b'--B\r\nContent-Disposition: form-data; name="f"; filename="' + name.encode() + b'"\r\n'
                b'Content-Type: application/zip\r\n\r\n' + zb + b'\r\n--B--\r\n')
        return post('/api/update', body, guard, 'multipart/form-data; boundary=B')

    def wait_done(t=8.0):
        end = time.time() + t
        while time.time() < end:
            st = state.update_status()
            if st and not st['running']:
                return st
            time.sleep(0.05)
        return state.update_status()

    def state_json():
        return json.loads(urllib.request.urlopen(base + '/api/state', timeout=5).read())

    page = urllib.request.urlopen(base + '/', timeout=5).read()
    check(b'AGGIORNA IL PI' in page and b'pkdel(' in page and b"'X-Sagga-Hub':'1'" in page and b'data-n=' in page,
          'the page: the update section, Elimina, the guard header, names in data- (a quote in a name breaks nothing)')
    check(state_json()['update'] is None, 'no update yet: nothing to show')
    # the delete
    code, _ = post('/api/package/delete?file=sagga-0.19.fwsc', guard=False)
    check(code == 403 and os.path.isfile(os.path.join(fw, 'sagga-0.19.fwsc')), 'a delete without the page header is refused (%d)' % code)
    code, _ = post('/api/package/delete?file=sagga-0.19.fwsc')
    check(code == 200 and not os.path.exists(os.path.join(fw, 'sagga-0.19.fwsc')), 'Elimina: the package is gone (%d)' % code)
    check([p['name'] for p in state_json()['packages']] == ['sagga-0.20.fwsc'], 'the list has one package left')
    for bad in ('sagga-0.19.fwsc', 'notes.txt', '../fw/sagga-0.20.fwsc/../../projects', '../../etc/passwd'):
        code, _ = post('/api/package/delete?file=' + urllib.parse.quote(bad))
        check(code == 404, 'a delete of %s: 404 (%d)' % (bad, code))
    check(os.path.isfile(os.path.join(fw, 'notes.txt')) and os.path.isfile(os.path.join(fw, 'sagga-0.20.fwsc')), 'nothing else went away')
    req = urllib.request.Request(base + '/api/install?file=sagga-0.20.fwsc', method='POST')
    urllib.request.urlopen(req, timeout=5)
    code, body = post('/api/package/delete?file=sagga-0.20.fwsc')
    check(code == 409 and os.path.isfile(os.path.join(fw, 'sagga-0.20.fwsc')), 'the package being installed is not deleted (%d %s)' % (code, body))
    code, body = upload(hub_zip())
    check(code == 409 and b'FM-1' in body, 'no update while the FM-1 installs: the restart would kill the install (%d %s)' % (code, body))
    time.sleep(1.2)
    # the zips that are refused, and why
    import zipfile
    for zb, why, what in ((b'PK not a zip at all', 'non è uno zip', 'not a zip'),
                          (hub_zip(top='sagga-seq-0.20'), 'sagga-hub-X', 'the source zip, not the hub'),
                          (hub_zip(extra={'other/x': 'y'}), 'una cartella sola', 'two folders'),
                          (hub_zip(extra={'sagga-hub-9.9/../../evil': 'y'}), 'fuori dalla cartella', 'a path out of the folder'),
                          (hub_zip(extra={'/etc/cron.d/x': 'y'}), 'fuori dalla cartella', 'an absolute path'),
                          (hub_zip(link='hub/patterns'), 'symlink', 'a link'),
                          (hub_zip(drop=('install_hub.sh',)), 'manca install_hub.sh', 'no installer'),
                          (hub_zip(drop=('hub/sagga_fw.py',)), 'manca hub/sagga_fw.py', 'no page'),
                          (hub_zip(script='echo hi\n'), "non è lo script", 'an installer that is not ours'),
                          (hub_zip(page='def broken(:\n'), 'non è Python valido', 'a page that does not compile'),
                          (hub_zip(page='print(1)\n'), 'non sa aggiornarsi', 'an older hub (0.20): its page has no update')):
        code, body = upload(zb)
        check(code == 400 and why.encode() in body, 'refused, %s: %d %s' % (what, code, body.decode('utf-8', 'replace')))
    rel = os.path.join(ROOT, 'build', 'release020', 'sagga-hub-0.20.zip')
    if os.path.isfile(rel):
        code, body = upload(open(rel, 'rb').read(), name='sagga-hub-0.20.zip')
        check(code == 400 and 'non sa aggiornarsi' in body.decode('utf-8', 'replace'), 'the real 0.20 hub zip is refused: no going back to a page without the update')
    check(not os.path.exists(os.path.join(up, 'update.log')), 'a refused zip starts nothing')
    code, _ = upload(hub_zip(), guard=False)
    check(code == 403, 'an update without the page header is refused (%d)' % code)
    # the update
    code, body = upload(hub_zip(script='#!/bin/sh\necho "fake install $*"\necho "pwd $(pwd)"\nsleep 0.4\necho "sagga_sgqmid built"\n'))
    check(code == 200 and json.loads(body)['version'] == '9.9', 'the update starts (%d %s)' % (code, body))
    st = state_json()['update']
    check(st and st['running'] and st['version'] == '9.9' and st['log'][0].startswith('update 9.9 from sagga-hub-9.9.zip'),
          'the page sees it running (%s)' % st)
    code, body = upload(hub_zip())
    check(code == 409, 'a second update while one runs: 409 (%d)' % code)
    req = urllib.request.Request(base + '/api/install?file=sagga-0.20.fwsc', method='POST')
    try:
        urllib.request.urlopen(req, timeout=5)
        check(False, 'no FM-1 install while the Pi updates')
    except urllib.error.HTTPError as e:
        check(e.code == 400 and json.loads(e.read())['error'] == 'the Pi is updating', 'no FM-1 install while the Pi updates')
    st = wait_done()
    check(st and st['rc'] == 0 and 'fake install --no-pc' in st['log'] and 'sagga_sgqmid built' in st['log'] and st['log'][-1] == 'exit 0',
          'the installer ran with --no-pc, its lines in the log, exit 0 (%s)' % (st and st['log']))
    check(any(ln.startswith('pwd ') and ln.endswith('/sagga-hub-9.9') for ln in st['log']), 'from the zip\'s folder, as install_hub.sh wants')
    check(not [n for n in os.listdir(up) if n.startswith('stage-')], 'the unpacked zip is cleaned up after')
    # a new page process (what install_hub.sh's restart makes) reads the same files
    st2 = FW.State(fw, pr, writer=state.writer, upd_dir=up).update_status()
    check(st2['rc'] == 0 and st2['version'] == '9.9', 'after the restart the page still knows how the update went')
    code, body = upload(hub_zip(top='sagga-hub-9.10', script='#!/bin/sh\necho "no gcc"\nexit 3\n'), name='sagga-hub-9.10.zip')
    st = wait_done()
    check(code == 200 and st['rc'] == 3 and st['version'] == '9.10' and 'no gcc' in st['log'], 'a failing installer: exit 3, on the page (%s)' % st)
    # with systemd: systemd-run, a unit of its own (sagga-fw's restart does not kill it), the PC port kept if it is on
    rec = os.path.join(d, 'sdrun.txt')
    sd = os.path.join(d, 'systemd-run')
    open(sd, 'w').write('#!/bin/sh\necho "$@" > %s\nwhile [ "$1" != "--quiet" ]; do shift; done; shift\n"$@" &\n' % rec)
    os.chmod(sd, 0o755)
    FW.SYSTEMD_RUN = sd
    FW.pc_enabled = lambda: True
    code, body = upload(hub_zip())
    st = wait_done()
    args = open(rec).read().split() if os.path.isfile(rec) else []
    check(code == 200 and args[:2] == ['--unit', args[1]] and args[1].startswith('sagga-update-') and '--collect' in args,
          'systemd-run starts it as a transient unit (%s)' % args[:4])
    check(st['rc'] == 0 and 'fake install' in ' '.join(st['log']) and '--no-pc' not in [w for ln in st['log'][1:] for w in ln.split()],
          'with the PC port on, the installer runs without --no-pc (%s)' % st['log'])
    FW.SYSTEMD_RUN = None
    # the real hub zip passes the check (make_release.sh, the files it really ships)
    mk = os.path.join(ROOT, 'tools', 'make_release.sh')
    if os.path.isfile(mk) and shutil_which('zip') and shutil_which('cc'):
        out = os.path.join(d, 'rel')
        r = subprocess.run(['sh', mk, '0.0.1', out], capture_output=True, text=True, cwd=ROOT)
        zp = os.path.join(out, 'sagga-hub-0.0.1.zip')
        if r.returncode == 0 and os.path.isfile(zp):
            z, top, ver = FW.check_hub_zip(open(zp, 'rb').read())
            check(top == 'sagga-hub-0.0.1' and ver == '0.0.1', 'the zip make_release.sh makes is one the page takes (%s %s)' % (top, ver))
        else:
            check(False, 'make_release.sh runs (%s)' % r.stderr[-300:])
    else:
        print('  (no make_release.sh / zip / cc here: the real zip is not checked)')
    sh = open(os.path.join(HUB, 'install_hub.sh')).read()
    check('/opt/sagga/hub/VERSION' in sh and 'sagga-hub-*' in sh, 'install_hub.sh writes the version the page shows')
    # 0.20.2: RaspiMIDIHub's restart puts the root back read-only and may drop its WiFi: last, after everything
    lines = sh.splitlines()
    rmh = [i for i, ln in enumerate(lines) if 'systemctl restart raspimidihub' in ln and not ln.lstrip().startswith('#')]
    last_write = max(i for i, ln in enumerate(lines) if 'remount,ro /' in ln or '/etc/systemd/system' in ln or 'systemctl enable' in ln)
    check(len(rmh) == 1 and rmh[0] > last_write, 'install_hub.sh restarts RaspiMIDIHub once, after its last write (%s > %s)' % (rmh, last_write))
    check('rwroot\ninstall -m 644 "$HERE/hub/sagga-virmidi.service"' in sh and 'rwroot\nsystemctl daemon-reload' in sh,
          'install_hub.sh makes the root writable again before the services')
    check('systemd-run --unit="$UNIT"' in sh and 'SAGGA_INSTALL_EXIT=' in sh and 'exit "${RC:-1}"' in sh,
          'install_hub.sh runs in a unit of its own and gives back its exit code (a dropped SSH does not stop it)')
    check('SAGGA_DETACHED=1 sh ./install_hub.sh' in open(os.path.join(HUB, 'sagga_fw.py')).read(),
          'the page runs it already detached (no unit inside the unit)')
    FW.HERE = d
    open(os.path.join(d, 'VERSION'), 'w').write('0.20.1\n')
    check(state_json()['version'] == '0.20.1', 'the page shows the hub version')
    # the delete on the read-only boot partition: remount rw, unlink, remount ro
    calls = []
    boot = os.path.join(d, 'boot')
    os.makedirs(os.path.join(boot, 'sagga', 'firmware'))
    open(os.path.join(boot, 'sagga', 'firmware', 'old.fwsc'), 'wb').write(b'o')
    bw = FW.BootWriter(os.path.join(boot, 'sagga', 'firmware'), run=lambda cmd: calls.append(cmd),
                       mounts=lambda: [('/', ['rw']), (boot, ['ro'])], lock=None)
    st3 = FW.State(os.path.join(boot, 'sagga', 'firmware'), pr, writer=bw, upd_dir=up)
    check(st3.delete_package('old.fwsc') is None and not os.path.exists(os.path.join(boot, 'sagga', 'firmware', 'old.fwsc'))
          and calls[0] == ['mount', '-o', 'remount,rw', boot] and calls[-1] == ['mount', '-o', 'remount,ro', boot],
          'Elimina on the read-only boot partition: opened, the file away, closed (%s)' % calls)
    srv.shutdown()


def shutil_which(x):
    import shutil
    return shutil.which(x)


def main():
    for t in (t_packets, t_c_header, t_pc_link, t_fw_page, t_patterns, t_progressions, t_update_delete):
        try:
            t()
        except Exception as e:
            import traceback
            traceback.print_exc()
            FAILS.append('%s raised %r' % (t.__name__, e))
    print('sagga hub: %d checks, %d failures' % (CHECKS[0], len(FAILS)))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
