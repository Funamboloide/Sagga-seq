#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The piano roll page (tools/hub/roll.html) in a headless browser: it loads a project of TAPE tracks through the hub
page, a drag adds a note, Ctrl+Z takes it back, Save writes the project with the note. Needs playwright + chromium;
without them the test says so and passes.

    python3 tests/sagga_roll_tests.py
"""
import os
import subprocess
import sys
import tempfile
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'hub'))
sys.path.insert(0, os.path.join(ROOT, 'tests'))


def main():
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print('sagga roll: skipped (no playwright)')
        return 0
    import sagga_fw as FW
    import sagga_sgqmid_tests as G
    tool = os.path.join(ROOT, 'build', 'sagga_sgqmid')
    if not os.path.isfile(tool):
        subprocess.run(['cc', '-std=c11', '-O2', '-I' + os.path.join(ROOT, 'firmware', 'src'), os.path.join(ROOT, 'tools', 'sgqmid', 'sagga_sgqmid.c'),
                        os.path.join(ROOT, 'firmware', 'src', 'sagga_seq_core.c'), os.path.join(ROOT, 'firmware', 'src', 'sagga_beats.c'), '-o', tool], check=True)
    fails = []
    def check(c, what):
        if not c:
            fails.append(what); print('  FAIL:', what)
    d = tempfile.mkdtemp()
    fw, pr = os.path.join(d, 'fw'), os.path.join(d, 'projects'); os.makedirs(fw); os.makedirs(pr)
    subprocess.run([tool, 'sgq2mid', os.path.join(ROOT, 'tools', 'hwtest', 'hwtest.sgq'), d + '/hw.mid'], check=True, capture_output=True)
    subprocess.run([tool, 'mid2sgq', d + '/hw.mid', pr + '/tapes.sgq'], check=True, capture_output=True)
    FW.SGQMID = tool; FW.ROLL = os.path.join(ROOT, 'tools', 'hub', 'roll.html')
    state = FW.State(fw, pr, writer=FW.BootWriter(fw, mounts=lambda: [('/', ['rw'])]))
    srv = FW.ThreadingHTTPServer(('127.0.0.1', 0), FW.make_handler(state)); port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1200, 'height': 700})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('http://127.0.0.1:%d/roll/tapes.sgq' % port); pg.wait_for_timeout(800)
        check('4 tracce TAPE' in (pg.text_content('#status') or '') and '4 battute' in (pg.text_content('#status') or ''), 'the page loads the project (%s)' % pg.text_content('#status'))
        n0 = pg.evaluate('tracks[cur].notes.length')
        x = 40 + 1536 * 0.25 + 10; y = 18 + (108 - 60) * 12 + 6 - pg.evaluate('wrap.scrollTop')
        pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x + 60, y); pg.mouse.up(); pg.wait_for_timeout(100)
        n1 = pg.evaluate('tracks[cur].notes.length'); last = pg.evaluate('tracks[cur].notes[tracks[cur].notes.length-1]')
        check(n1 == n0 + 1 and last['on'] == 1536 and last['dur'] == 288 and 60 <= last['note'] <= 70, 'a drag adds a note on the grid, three 1/16 long (%s)' % last)
        pg.keyboard.press('Control+z')
        check(pg.evaluate('tracks[cur].notes.length') == n0, 'Ctrl+Z takes it back')
        pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x + 60, y); pg.mouse.up()
        pg.click('#save'); pg.wait_for_timeout(1500)
        check((pg.text_content('#status') or '').startswith('salvato: tapes.sgq'), 'Save writes the project (%s)' % pg.text_content('#status'))
        check(not errs, 'no script errors (%s)' % errs)
        b.close()
    srv.shutdown()
    r = subprocess.run([tool, 'sgq2mid', pr + '/tapes.sgq', d + '/after.mid'], capture_output=True, text=True)
    fmt, ppq, tempo, tr = G.read_smf(d + '/after.mid')
    counts = {n: len(G.notes(e)) for n, e in tr}
    check(counts.get('T1 ch1 TAPE') == 17 and counts.get('T2 ch2 TAPE') == 16 and counts.get('T3 ch3 TAPE') == 4 and counts.get('T4 ch4 TAPE') == 8, 'the saved project has the note more on track 1, the others as they were (%s)' % counts)
    check(os.path.isfile(pr + '/tapes.sgq.bak'), 'and a .bak of the one before')
    print('sagga roll: %d failures' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
