#!/usr/bin/env python3
"""SAGGA M8 LINK 0.5, the Brick side of the vendor link (used only when the kernel has no f_midi).

The M8's raw MIDI (/dev/snd/midiC<card>D0, the card named M8 in /proc/asound/cards) <-> two bulk endpoints of a
FunctionFS function: bytes as they are, both ways. After ChatGPT's 0.3 (descriptors, the KNULLI g1 gadget); 0.4 finds
the M8 by name (its card number changes with what else is plugged in), waits for it and opens it again when it is
replugged, and never lets one direction wait on the other.
"""
import argparse
import errno
import os
import re
import select
import signal
import struct
import sys
import threading
import time

FUNCTIONFS_DESCRIPTORS_MAGIC = 1
FUNCTIONFS_STRINGS_MAGIC = 2
USB_DT_INTERFACE, USB_DT_ENDPOINT = 4, 5
USB_CLASS_VENDOR_SPEC = 0xFF
USB_ENDPOINT_XFER_BULK = 2
USB_DIR_IN = 0x80

stop_evt = threading.Event()
midi_lock = threading.Lock()
midi_fd = [None]                       # the M8's raw MIDI, or None while it is not there


def log(*a):
    print(time.strftime('%F %T'), *a, file=sys.stderr, flush=True)


def descriptors_blob():
    intf = struct.pack('<BBBBBBBBB', 9, USB_DT_INTERFACE, 0, 0, 2, USB_CLASS_VENDOR_SPEC, 0, 0, 1)

    def ep(addr, maxp):
        return struct.pack('<BBBBHB', 7, USB_DT_ENDPOINT, addr, USB_ENDPOINT_XFER_BULK, maxp, 0)
    fs = intf + ep(0x01, 64) + ep(USB_DIR_IN | 0x01, 64)
    hs = intf + ep(0x01, 512) + ep(USB_DIR_IN | 0x01, 512)
    return struct.pack('<IIII', FUNCTIONFS_DESCRIPTORS_MAGIC, 16 + len(fs) + len(hs), 3, 3) + fs + hs


def strings_blob(label='SAGGA M8 LINK'):
    payload = struct.pack('<H', 0x0409) + label.encode() + b'\x00'
    return struct.pack('<IIII', FUNCTIONFS_STRINGS_MAGIC, 16 + len(payload), 1, 1) + payload


def m8_rawmidi(cards='/proc/asound/cards'):
    """/dev/snd/midiC<n>D0 of the card whose id is M8, or None"""
    try:
        with open(cards) as f:
            for line in f:
                m = re.match(r'\s*(\d+)\s+\[M8\s*\]', line)
                if m:
                    return '/dev/snd/midiC%sD0' % m.group(1)
    except OSError:
        pass
    return None


def write_all(fd, data):
    view = memoryview(data)
    while view:
        view = view[os.write(fd, view):]


def open_retry(path, flags):
    while not stop_evt.is_set():
        try:
            return os.open(path, flags)
        except OSError as e:
            if e.errno not in (errno.ENOENT, errno.ENXIO, errno.EBUSY, errno.ENODEV):
                raise
            time.sleep(0.05)
    raise SystemExit(0)


def drop_midi(fd):
    with midi_lock:
        if midi_fd[0] == fd:
            midi_fd[0] = None
            try:
                os.close(fd)
            except OSError:
                pass
            log('M8 gone')


def m8_keeper():
    """opens the M8 when it is there (again after a replug)"""
    while not stop_evt.is_set():
        if midi_fd[0] is None:
            path = m8_rawmidi()
            if path:
                try:
                    fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
                    with midi_lock:
                        midi_fd[0] = fd
                    log('M8 open:', path)
                except OSError as e:
                    log('M8 not ready:', e)
        time.sleep(0.5)


def ep0_events(ep0):
    """FunctionFS wants its events read (BIND, ENABLE, DISABLE, SUSPEND ...); a vendor link needs no answer"""
    while not stop_evt.is_set():
        try:
            r, _, _ = select.select([ep0], [], [], 0.5)
            if r:
                os.read(ep0, 12 * 16)
        except OSError as e:
            if e.errno not in (errno.EINTR, errno.EAGAIN, errno.ESHUTDOWN, errno.ENODEV):
                log('ep0:', e)
            time.sleep(0.05)


def usb_to_m8(ep_out):
    """the Pi's bytes to the M8 (a read waits until the Pi sends; nothing else waits on it)"""
    while not stop_evt.is_set():
        try:
            data = os.read(ep_out, 1024)
        except OSError as e:
            if e.errno not in (errno.EINTR, errno.EAGAIN, errno.ESHUTDOWN, errno.ENODEV, errno.EPIPE):
                log('USB->M8:', e)
            time.sleep(0.02)
            continue
        fd = midi_fd[0]
        if data and fd is not None:
            try:
                write_all(fd, data)
            except BlockingIOError:
                pass                                    # (the M8 is not reading: this message is lost)
            except OSError:
                drop_midi(fd)


def m8_to_usb(ep_in):
    """the M8's bytes to the Pi"""
    while not stop_evt.is_set():
        fd = midi_fd[0]
        if fd is None:
            time.sleep(0.1)
            continue
        try:
            r, _, _ = select.select([fd], [], [], 0.25)
            if not r:
                continue
            data = os.read(fd, 1024)
        except OSError as e:
            if e.errno in (errno.EAGAIN, errno.EINTR):
                continue
            drop_midi(fd)
            continue
        if not data:
            drop_midi(fd)
            continue
        try:
            write_all(ep_in, data)                      # (waits while the Pi is not reading)
        except OSError as e:
            if e.errno not in (errno.EINTR, errno.EAGAIN, errno.ESHUTDOWN, errno.ENODEV, errno.EPIPE):
                log('M8->USB:', e)
            time.sleep(0.02)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--ffs', default='/dev/ffs-sagga')
    ap.add_argument('--name', default='A', help='this Brick\'s name (A, B): the interface string the Pi shows')
    a = ap.parse_args()
    for s in (signal.SIGTERM, signal.SIGINT):
        signal.signal(s, lambda *_: stop_evt.set())
    ep0 = open_retry(os.path.join(a.ffs, 'ep0'), os.O_RDWR)
    write_all(ep0, descriptors_blob())
    write_all(ep0, strings_blob('SAGGA M8 LINK ' + a.name))
    log('FunctionFS descriptors written')
    ep_out = open_retry(os.path.join(a.ffs, 'ep1'), os.O_RDONLY)
    ep_in = open_retry(os.path.join(a.ffs, 'ep2'), os.O_WRONLY)
    log('link ready')
    for fn, arg in ((ep0_events, ep0), (m8_keeper, None), (usb_to_m8, ep_out), (m8_to_usb, ep_in)):
        threading.Thread(target=fn, args=(() if arg is None else (arg,)), daemon=True).start()
    while not stop_evt.wait(1.0):
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
