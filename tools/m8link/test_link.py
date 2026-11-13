"""SAGGA M8 LINK 0.5: both daemons' byte pumps with fake endpoints (no USB, no M8): python3 tests/test_link.py"""
import importlib.util, os, queue, socket, sys, threading, time
base = os.path.dirname(os.path.abspath(__file__))
def load(n, p):
    s = importlib.util.spec_from_file_location(n, os.path.join(base, p)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
fails = []
def check(c, what):
    print(('ok   ' if c else 'FAIL ') + what)
    if not c: fails.append(what)

def recv_until(sock_or_fd, n, timeout=2.0):
    got, end = b'', time.time() + timeout
    while len(got) < n and time.time() < end:
        try:
            got += os.read(sock_or_fd, 1024)
        except BlockingIOError:
            time.sleep(0.01)
    return got

# ---- the Brick: Pi bytes -> M8, M8 bytes -> Pi, the M8 replugged
b = load('ffs', 'brick/sagga_m8_ffs.py')
ep_out_r, ep_out_w = os.pipe()           # what the Pi sends (bulk OUT)
ep_in_r, ep_in_w = os.pipe()             # what goes to the Pi (bulk IN)
m8_side, link_side = socket.socketpair()  # the M8's raw MIDI, read and write
m8_side.setblocking(False)
b.midi_fd[0] = link_side.fileno()
for fn, arg in ((b.usb_to_m8, ep_out_r), (b.m8_to_usb, ep_in_w)):
    threading.Thread(target=fn, args=(arg,), daemon=True).start()
os.write(ep_out_w, bytes([0xF8, 0x90, 60, 100]))
got = b''
end = time.time() + 2
while len(got) < 4 and time.time() < end:
    try: got += m8_side.recv(64)
    except BlockingIOError: time.sleep(0.01)
check(got == bytes([0xF8, 0x90, 60, 100]), 'Brick: clock and a note from the Pi reach the M8 (%s)' % got.hex())
m8_side.send(bytes([0x90, 64, 90, 0x80, 64, 0]))
check(recv_until(ep_in_r, 6) == bytes([0x90, 64, 90, 0x80, 64, 0]), 'Brick: the M8 notes reach the Pi')
m8_side.close()                           # the M8 unplugged: the link lets it go and keeps the Pi side alive
time.sleep(0.5)
check(b.midi_fd[0] is None, 'Brick: an unplugged M8 is let go (the keeper opens it again when it is back)')
os.write(ep_out_w, bytes([0xF8]))         # bytes for a missing M8 are dropped, nothing blocks
time.sleep(0.2)
m8b, linkb = socket.socketpair(); m8b.setblocking(False)
b.midi_fd[0] = linkb.fileno()             # (what m8_keeper does when the card is back)
m8b.send(bytes([0xB0, 1, 2]))
check(recv_until(ep_in_r, 3) == bytes([0xB0, 1, 2]), 'Brick: after the replug the M8 is heard again')

# ---- the Pi: the Brick's bulk endpoints <-> the virtual MIDI card
h = load('host', 'pi/sagga_m8_host.py')
class Timeout(Exception): pass
class FakeCore: USBTimeoutError = Timeout
class EpIn:
    def __init__(self): self.q = queue.Queue()
    def read(self, n, timeout):
        try: return self.q.get(timeout=timeout / 1000)
        except queue.Empty: raise Timeout()
class EpOut:
    def __init__(self): self.sent = []; self.t = []
    def write(self, data, timeout): self.sent.append(bytes(data)); self.t.append(time.time())
card_side, daemon_side = socket.socketpair()
card_side.setblocking(False)
ep_in, ep_out = EpIn(), EpOut()
threading.Thread(target=h.usb_to_midi, args=(ep_in, daemon_side.fileno(), FakeCore), daemon=True).start()
threading.Thread(target=h.midi_to_usb, args=(ep_out, daemon_side.fileno(), FakeCore), daemon=True).start()
ep_in.q.put(bytes([0x90, 48, 100]))
got, end = b'', time.time() + 2
while len(got) < 3 and time.time() < end:
    try: got += card_side.recv(64)
    except BlockingIOError: time.sleep(0.01)
check(got == bytes([0x90, 48, 100]), 'Pi: the M8 note appears on the virtual card (RaspiMIDIHub sees it)')
lat = []
for i in range(24):                        # a bar of clock from the hub, 20 ms apart, while nothing comes from the M8
    t0 = time.time(); card_side.send(bytes([0xF8]))
    end = time.time() + 1
    while len(ep_out.sent) <= i and time.time() < end: time.sleep(0.0005)
    lat.append(ep_out.t[i] - t0 if len(ep_out.t) > i else 1.0)
    time.sleep(0.02)
check(max(lat) < 0.01, 'Pi: a clock to the M8 leaves within 10 ms, never waiting for a read (worst %.1f ms)' % (max(lat) * 1000))

# ---- 0.5: two Bricks, each on its own virtual card
import tempfile, subprocess
check(h.brick_name('SAGGAM8-B') == 'B' and h.brick_name('SAGGAM8-001') == 'A' and h.brick_name(None) == 'A'
      and h.brick_name('other') == 'A', 'Pi: the Brick name comes from its serial (0.4 counts as A)')
cards = tempfile.NamedTemporaryFile('w', delete=False, suffix='cards')
cards.write(' 0 [Headphones     ]: bcm2835_headpho - bcm2835 Headphones\n'
            ' 3 [SAGGAM8A       ]: VirMIDI - Virtual MIDI Card 1\n'
            '                      Virtual MIDI Card 1\n'
            ' 4 [SAGGAM8B       ]: VirMIDI - Virtual MIDI Card 2\n')
cards.close()
check(h.virmidi_rawmidi('SAGGAM8A', cards.name) == '/dev/snd/midiC3D0' and
      h.virmidi_rawmidi('SAGGAM8B', cards.name) == '/dev/snd/midiC4D0' and
      h.virmidi_rawmidi('SAGGAM8C', cards.name) is None, 'Pi: each name finds its own card, an unknown one none')

class FakeUtil:
    def __init__(self, serials): self.serials = serials
    def get_string(self, dev, idx): return self.serials[dev.address]
    def dispose_resources(self, dev): pass
class Dev:
    def __init__(self, address): self.bus, self.address, self.iSerialNumber = 1, address, 3
opened = []
util = FakeUtil({5: 'SAGGAM8-A', 6: 'SAGGAM8-B', 7: 'SAGGAM8-A', 8: 'SAGGAM8-C'})
links = h.Links(FakeCore, util, cards=cards.name, opener=lambda path: opened.append(path) or len(opened) + 100)
logged = []
h.log = lambda *a: logged.append(' '.join(str(x) for x in a))
running = links.poll([Dev(5), Dev(6), Dev(7), Dev(8)], start=False)
check(running == {'A': 'SAGGAM8A', 'B': 'SAGGAM8B'}, 'Pi: two Bricks, two links (%s)' % running)
check(sorted(opened) == ['/dev/snd/midiC3D0', '/dev/snd/midiC4D0'], 'Pi: each card opened once')
check(any('both called A' in m for m in logged), 'Pi: a second Brick with the same name is refused with a hint')
check(any('no virtual card SAGGAM8C' in m for m in logged), 'Pi: a Brick without its card says which card is missing')
n = len(logged)
links.poll([Dev(5), Dev(6), Dev(7), Dev(8)], start=False)
check(len(logged) == n, 'Pi: the warnings are not repeated every second')

# the pumps of a link that ended stop (a replugged Brick must not find an old pump still reading its card)
done = threading.Event()
c2, d2 = socket.socketpair(); c2.setblocking(False)
ep_out2 = EpOut()
t = threading.Thread(target=h.midi_to_usb, args=(ep_out2, d2.fileno(), FakeCore, done), daemon=True); t.start()
done.set(); t.join(1.0)
check(not t.is_alive(), 'Pi: the pumps of a finished link stop')

# the Brick: sagga_m8 name B writes the name, keeps MODE, and the service reads it
tmp = tempfile.mkdtemp()
conf = os.path.join(tmp, 'sagga_m8.conf')
open(conf, 'w').write('MODE=ffs\n')
script = open(os.path.join(base, 'brick', 'sagga_m8')).read().replace('/userdata/system/sagga_m8.conf', conf)
sp = os.path.join(tmp, 'sagga_m8'); open(sp, 'w').write(script)
out = subprocess.run(['sh', sp, 'name', 'b'], capture_output=True, text=True).stdout
text = open(conf).read()
check('NAME=B' in text and 'MODE=ffs' in text and 'SAGGA M8 B' in out, 'Brick: "name b" writes NAME=B and keeps MODE')
bad = subprocess.run(['sh', sp, 'name', 'b-1'], capture_output=True, text=True)
check(bad.returncode == 2 and 'NAME=B' in open(conf).read(), 'Brick: a bad name is refused')
st = subprocess.run(['sh', sp, 'status'], capture_output=True, text=True).stdout
check('name: SAGGA M8 B' in st, 'Brick: the status shows the name')

# 0.6 the watchdog: KNULLI unbinds the port (going back to EmulationStation after m8c): bound again; a port bound to
# something else is left alone; the gadget taken apart: the link starts again
import time
g = os.path.join(tmp, 'g1'); run = os.path.join(tmp, 'run')
os.makedirs(os.path.join(g, 'configs', 'b.1')); os.makedirs(os.path.join(g, 'functions', 'ffs.sagga')); os.makedirs(run)
os.symlink(os.path.join(g, 'functions', 'ffs.sagga'), os.path.join(g, 'configs', 'b.1', 'ffs.sagga'))
open(os.path.join(g, 'UDC'), 'w').write('')
daemon = subprocess.Popen(['sleep', '30'])
open(os.path.join(run, 'ffs.pid'), 'w').write(str(daemon.pid))
env = dict(os.environ, SAGGA_G=g, SAGGA_RUN=run, SAGGA_LOG=os.path.join(tmp, 'link.log'), SAGGA_UDC='5100000.udc-controller',
           SAGGA_DOG_S='0.2')
dogscript = script.rsplit('SELF=', 1)[0] + 'SELF=%s\nwatchdog ffs.sagga\n' % os.path.join(tmp, 'restart_called.sh')
open(os.path.join(tmp, 'restart_called.sh'), 'w').write('#!/bin/sh\necho "$@" > %s\n' % os.path.join(tmp, 'restarted'))
os.chmod(os.path.join(tmp, 'restart_called.sh'), 0o755)
dp = os.path.join(tmp, 'dog.sh'); open(dp, 'w').write(dogscript)
dog = subprocess.Popen(['sh', dp], env=env)
time.sleep(0.6)
check(open(os.path.join(g, 'UDC')).read().strip() == '5100000.udc-controller', 'Brick: the watchdog binds an unbound port again')
open(os.path.join(g, 'UDC'), 'w').write('')
time.sleep(0.6)
check(open(os.path.join(g, 'UDC')).read().strip() == '5100000.udc-controller', '... every time it is unbound')
open(os.path.join(g, 'UDC'), 'w').write('other.udc\n')
time.sleep(0.6)
check(open(os.path.join(g, 'UDC')).read().strip() == 'other.udc', '... a port bound to something else is left alone')
check('bound again' in open(os.path.join(tmp, 'link.log')).read(), '... and the log says so')
os.unlink(os.path.join(g, 'configs', 'b.1', 'ffs.sagga'))
time.sleep(2.0)
check(dog.poll() is not None and open(os.path.join(tmp, 'restarted')).read().strip() == 'restart',
      'Brick: the gadget taken apart: the watchdog starts the link again and ends')
daemon.kill(); dog.kill() if dog.poll() is None else None
print('m8 link: %d failures' % len(fails))
sys.exit(1 if fails else 0)
