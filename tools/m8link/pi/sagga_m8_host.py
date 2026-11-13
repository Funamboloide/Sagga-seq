#!/usr/bin/env python3
"""SAGGA M8 LINK 0.5, the Raspberry Pi side of the vendor link (only for Bricks that run in "ffs" mode).

The Brick's vendor USB device (1209:7a01) <-> a virtual MIDI card of the kernel (snd-virmidi). RaspiMIDIHub shows only
real (kernel) MIDI devices and its own plugins, so the virtual ports ChatGPT's 0.3 opened with rtmidi never reached
its matrix; a snd-virmidi card is a kernel device: it is in the matrix like any synth ("Virtual Raw MIDI ...").
Bytes as they are, both ways, each direction in its own thread: a clock or a note going to the M8 never waits for
a read of the other direction (0.3 polled both in one loop, up to 20 ms late: a jittery clock).
0.5: more than one Brick. Each says its name in its USB serial number (SAGGAM8-A, SAGGAM8-B: `sagga_m8 name B` on the
Brick) and gets its own virtual card (SAGGAM8A, SAGGAM8B); a Brick of 0.4 (SAGGAM8-001) counts as A.

    sudo modprobe snd-virmidi enable=1,1 midi_devs=1,1 id=SAGGAM8A,SAGGAM8B        (the service does it)
    sudo python3 sagga_m8_host.py [--list]
needs python3-usb (pyusb).
"""
import argparse
import errno
import os
import re
import select
import signal
import sys
import threading
import time

stop_evt = threading.Event()


def log(*a):
    print(time.strftime('%F %T'), *a, file=sys.stderr, flush=True)


def virmidi_rawmidi(card_id='SAGGAM8A', cards='/proc/asound/cards'):
    """/dev/snd/midiC<n>D0 of the virtual card with this id, or None (0.5: no "first virtual card" fallback: with two
    Bricks it would give both the same card)"""
    try:
        with open(cards) as f:
            for line in f:
                m = re.match(r'\s*(\d+)\s+\[(\S+)\s*\]:', line)
                if m and m.group(2) == card_id:
                    return '/dev/snd/midiC%sD0' % m.group(1)
    except OSError:
        pass
    return None


def brick_name(serial):
    """the Brick's name from its USB serial number: SAGGAM8-B -> B; 0.4's SAGGAM8-001 (or none) -> A"""
    m = re.match(r'^SAGGAM8-([A-Z0-9]{1,4})$', serial or '')
    if not m or m.group(1) == '001':
        return 'A'
    return m.group(1)


def card_for(serial):
    return 'SAGGAM8' + brick_name(serial)


def running(done):
    return not stop_evt.is_set() and not (done is not None and done.is_set())


def usb_to_midi(ep_in, fd, usb_core, done=None):
    while running(done):
        try:
            data = bytes(ep_in.read(512, timeout=200))
        except usb_core.USBTimeoutError:
            continue
        if data:
            try:
                os.write(fd, data)
            except BlockingIOError:
                pass


def midi_to_usb(ep_out, fd, usb_core, done=None):
    while running(done):
        r, _, _ = select.select([fd], [], [], 0.25)
        if not r:
            continue
        try:
            data = os.read(fd, 512)
        except OSError as e:
            if e.errno in (errno.EAGAIN, errno.EINTR):
                continue
            raise
        if data:
            ep_out.write(data, timeout=1000)


def run_link(dev, fd, usb_core, usb_util, name='A'):
    """one connection: until the Brick goes away (an exception) or we are stopped"""
    dev.set_configuration()
    intf = dev.get_active_configuration()[(0, 0)]
    try:
        if dev.is_kernel_driver_active(intf.bInterfaceNumber):
            dev.detach_kernel_driver(intf.bInterfaceNumber)
    except (NotImplementedError, usb_core.USBError):
        pass
    usb_util.claim_interface(dev, intf.bInterfaceNumber)
    ep_in = next(e for e in intf if usb_util.endpoint_direction(e.bEndpointAddress) == usb_util.ENDPOINT_IN)
    ep_out = next(e for e in intf if usb_util.endpoint_direction(e.bEndpointAddress) == usb_util.ENDPOINT_OUT)
    log('Brick %s connected' % name)
    errors = []

    def guard(fn, *args):
        try:
            fn(*args)
        except Exception as e:                    # (the cable pulled: both threads end, the outer loop waits again)
            errors.append(e)
    done = threading.Event()                      # (both pumps stop with the link: a replugged Brick gets new ones,
    threads = [threading.Thread(target=guard, args=(usb_to_midi, ep_in, fd, usb_core, done), daemon=True),
               threading.Thread(target=guard, args=(midi_to_usb, ep_out, fd, usb_core, done), daemon=True)]
    for t in threads:                             #  and no old pump is left reading the card)
        t.start()
    while not stop_evt.is_set() and not errors:
        time.sleep(0.2)
    done.set()
    for t in threads:
        t.join(1.5)
    if errors:
        raise errors[0]


def serial_of(dev, usb_util):
    try:
        return usb_util.get_string(dev, dev.iSerialNumber) if dev.iSerialNumber else None
    except Exception:
        return None


class Links:
    """one thread per Brick plugged in; each Brick's bytes go to the virtual card of its name"""
    def __init__(self, usb_core, usb_util, cards='/proc/asound/cards', opener=None):
        self.usb_core, self.usb_util, self.cards = usb_core, usb_util, cards
        self.opener = opener or (lambda path: os.open(path, os.O_RDWR | os.O_NONBLOCK))
        self.fds = {}                                   # card id -> fd (opened once, kept)
        self.active = {}                                # (bus, address) -> (name, thread)
        self.warned = set()

    def warn_once(self, key, *msg):
        if key not in self.warned:
            self.warned.add(key)
            log(*msg)

    def fd_for(self, card):
        if card not in self.fds:
            path = virmidi_rawmidi(card, self.cards)
            if not path:
                return None
            self.fds[card] = self.opener(path)
            log('virtual MIDI card %s: %s' % (card, path))
        return self.fds[card]

    def worker(self, dev, fd, name):
        try:
            run_link(dev, fd, self.usb_core, self.usb_util, name)
        except Exception as e:
            log('Brick %s: link ended:' % name, e)
        finally:
            try:
                self.usb_util.dispose_resources(dev)
            except Exception:
                pass

    def poll(self, devs, start=True):
        """devs: the Bricks on USB now; starts a link for each new one. Returns {name: card} of the ones running"""
        for key, (name, t) in list(self.active.items()):
            if not t.is_alive():
                del self.active[key]
        busy = {name for name, _ in self.active.values()}
        for dev in devs:
            key = (getattr(dev, 'bus', None), getattr(dev, 'address', None))
            if key in self.active:
                continue
            serial = serial_of(dev, self.usb_util)
            name, card = brick_name(serial), card_for(serial)
            if name in busy:
                self.warn_once(('dup', name), 'two Bricks are both called %s: on one of them run "sagga_m8 name B" '
                                              'and restart its link' % name)
                continue
            fd = self.fd_for(card)
            if fd is None:
                self.warn_once(('card', card), 'Brick %s: no virtual card %s; the service loads them '
                                               '(modprobe snd-virmidi enable=1,1 midi_devs=1,1 id=SAGGAM8A,SAGGAM8B)'
                               % (name, card))
                continue
            t = threading.Thread(target=self.worker, args=(dev, fd, name), daemon=True)
            self.active[key] = (name, t)
            busy.add(name)
            if start:
                t.start()
        return {name: card_for_name(name) for name, _ in self.active.values()}


def card_for_name(name):
    return 'SAGGAM8' + name


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--vid', type=lambda x: int(x, 0), default=0x1209)
    ap.add_argument('--pid', type=lambda x: int(x, 0), default=0x7A01)
    ap.add_argument('--list', action='store_true', help='show the Bricks on USB and their cards, then exit')
    a = ap.parse_args(argv)
    try:
        import usb.core as usb_core
        import usb.util as usb_util
    except ImportError:
        sys.exit('needs pyusb: sudo apt install python3-usb')
    if a.list:
        devs = list(usb_core.find(find_all=True, idVendor=a.vid, idProduct=a.pid))
        print('%d Brick(s) on USB' % len(devs))
        for dev in devs:
            serial = serial_of(dev, usb_util)
            card = card_for(serial)
            print('  bus %s address %s  serial %s  ->  SAGGA M8 %s  card %s (%s)' % (
                dev.bus, dev.address, serial, brick_name(serial), card, virmidi_rawmidi(card) or 'missing'))
        return 0
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop_evt.set())
    links = Links(usb_core, usb_util)
    log('waiting for Bricks (%04x:%04x)' % (a.vid, a.pid))
    while not stop_evt.is_set():
        try:
            devs = list(usb_core.find(find_all=True, idVendor=a.vid, idProduct=a.pid))
        except Exception as e:
            log('USB scan:', e)
            devs = []
        links.poll(devs)
        stop_evt.wait(1.0)
    for fd in links.fds.values():
        os.close(fd)
    return 0


if __name__ == '__main__':
    sys.exit(main())
