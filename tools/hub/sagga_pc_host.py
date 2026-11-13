#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SAGGA HUB: the PC port. The RP2040-Zero on the hub's USB-C "PC" socket is a USB-MIDI interface for the computer
(two ports, "SAGGA HUB 1" and "SAGGA HUB 2"); it talks to the Pi over a UART, SLIP frames of USB-MIDI packets
(tools/hub/usbmidi_pkt.py, tools/hub/rp2040). This program moves those packets to and from two virtual MIDI cards of
the kernel (snd-virmidi: SAGGAPC1, SAGGAPC2), which RaspiMIDIHub shows in its matrix like any synth. Route
"Felucca MIDI 1 <-> SAGGAPC1" there and the computer sees the FM-1 through the hub.

    sudo modprobe snd-virmidi enable=1,1,1,1 midi_devs=1,1,1,1 id=SAGGAM8A,SAGGAM8B,SAGGAPC1,SAGGAPC2
    sudo python3 sagga_pc_host.py [--port /dev/serial0] [--baud 1000000]
The service (sagga-pc-link.service) does both. Needs python3-serial.
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from usbmidi_pkt import Packetizer, SlipDecoder, slip_encode, unpack      # noqa: E402

CARDS = ('SAGGAPC1', 'SAGGAPC2')
stop_evt = threading.Event()


def log(*a):
    print(time.strftime('%F %T'), *a, file=sys.stderr, flush=True)


def virmidi_rawmidi(card_id, cards='/proc/asound/cards'):
    """/dev/snd/midiC<n>D0 of the virtual card with this id, or None"""
    try:
        with open(cards) as f:
            for line in f:
                m = re.match(r'\s*(\d+)\s+\[(\S+)\s*\]:', line)
                if m and m.group(2) == card_id:
                    return '/dev/snd/midiC%sD0' % m.group(1)
    except OSError:
        pass
    return None


class Link:
    """one UART (fd, non-blocking) <-> the cards' fds (by cable number)"""
    def __init__(self, uart_fd, card_fds, name='PC'):
        self.uart, self.cards, self.name = uart_fd, card_fds, name
        self.dec = SlipDecoder()
        self.pk = [Packetizer(c) for c in range(len(card_fds))]
        self.rx_pkts = self.tx_pkts = self.bad = 0
        self.lock = threading.Lock()

    def uart_bytes(self, data):
        """bytes from the RP2040: packets -> the cable's card"""
        for frame in self.dec.feed(data):
            u = unpack(frame)
            if not u:
                self.bad += 1
                continue
            cable, midi = u
            self.rx_pkts += 1
            if cable < len(self.cards) and self.cards[cable] is not None:
                try:
                    os.write(self.cards[cable], midi)
                except BlockingIOError:
                    pass

    def card_bytes(self, cable, data):
        """bytes from a card: packets -> the RP2040"""
        out = b''.join(slip_encode(p) for p in self.pk[cable].feed(data))
        if out:
            self.tx_pkts += 1
            with self.lock:
                try:
                    os.write(self.uart, out)
                except BlockingIOError:
                    pass                                    # (the UART is full: the computer side is not reading)

    def pump(self, done=None):
        fds = [self.uart] + [fd for fd in self.cards if fd is not None]
        while not stop_evt.is_set() and not (done is not None and done.is_set()):
            r, _, _ = select.select(fds, [], [], 0.25)
            for fd in r:
                try:
                    data = os.read(fd, 1024)
                except OSError as e:
                    if e.errno in (errno.EAGAIN, errno.EINTR):
                        continue
                    raise
                if not data:
                    if fd == self.uart:
                        raise OSError('UART closed')
                    continue
                if fd == self.uart:
                    self.uart_bytes(data)
                else:
                    self.card_bytes(self.cards.index(fd), data)


def open_uart(path, baud):
    import serial                                           # python3-serial
    s = serial.Serial(path, baud, timeout=0, write_timeout=0)
    fd = s.fileno()
    os.set_blocking(fd, False)
    return s, fd


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--port', default='/dev/serial0')
    ap.add_argument('--baud', type=int, default=1000000)
    ap.add_argument('--cards', default=','.join(CARDS))
    a = ap.parse_args(argv)
    for s in (signal.SIGTERM, signal.SIGINT):
        signal.signal(s, lambda *_: stop_evt.set())
    card_ids = a.cards.split(',')
    fds = []
    for cid in card_ids:
        path = virmidi_rawmidi(cid)
        if not path:
            log('no virtual card %s: the service loads them (modprobe snd-virmidi ... id=%s)' % (cid, a.cards))
            fds.append(None)
            continue
        fds.append(os.open(path, os.O_RDWR | os.O_NONBLOCK))
        log('virtual MIDI card %s: %s' % (cid, path))
    while not stop_evt.is_set():
        try:
            ser, ufd = open_uart(a.port, a.baud)
        except Exception as e:
            log('UART %s: %s (waiting)' % (a.port, e))
            time.sleep(2)
            continue
        log('PC port on %s at %d' % (a.port, a.baud))
        link = Link(ufd, fds)
        try:
            link.pump()
        except Exception as e:
            log('link ended:', e)
        finally:
            try:
                ser.close()
            except Exception:
                pass
        time.sleep(1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
