#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""USB-MIDI event packets (4 bytes: cable / CIN, then up to three MIDI bytes) <-> MIDI byte streams, and the SLIP
frames the SAGGA HUB uses to carry those packets over a UART (between the Pi and the RP2040 of the PC port).
Pure functions and small stateful classes; the C side (tools/hub/rp2040/slip_midi.h) does the same job."""

# bytes of MIDI in a packet, by its Code Index Number; 0 and 1 are reserved (never sent)
CIN_LEN = {0x2: 2, 0x3: 3, 0x4: 3, 0x5: 1, 0x6: 2, 0x7: 3, 0x8: 3, 0x9: 3, 0xA: 3, 0xB: 3, 0xC: 2, 0xD: 2, 0xE: 3, 0xF: 1}

SLIP_END, SLIP_ESC, SLIP_ESC_END, SLIP_ESC_ESC = 0xC0, 0xDB, 0xDC, 0xDD


def unpack(pkt):
    """a 4-byte packet -> (cable, midi bytes), or None if it is not a valid packet"""
    if len(pkt) != 4:
        return None
    cin = pkt[0] & 0x0F
    n = CIN_LEN.get(cin)
    if n is None:
        return None
    return pkt[0] >> 4, bytes(pkt[1:1 + n])


class Packetizer:
    """MIDI bytes of one cable in, 4-byte packets out. Running status is expanded; realtime bytes pass at once, even
    inside a SysEx; a SysEx goes out three bytes at a time as it arrives (CIN 4), its end as 5 / 6 / 7."""
    def __init__(self, cable=0):
        self.cable = cable & 0x0F
        self.status = 0            # running status of the channel message in progress
        self.need = 0              # data bytes the message still needs
        self.data = []
        self.sysex = None          # bytes of the SysEx in progress (without the F0 already sent), or None

    def pkt(self, cin, *b):
        out = [(self.cable << 4) | cin] + list(b)
        while len(out) < 4:
            out.append(0)
        return bytes(out)

    def feed(self, data):
        out = []
        for b in data:
            if b >= 0xF8:                                  # realtime: alone, right now
                out.append(self.pkt(0xF, b))
                continue
            if self.sysex is not None:
                if b == 0xF7:
                    s = self.sysex + [b]
                    out.append(self.pkt({1: 0x5, 2: 0x6, 3: 0x7}[len(s)], *s))
                    self.sysex = None
                elif b & 0x80:                             # a status cuts the SysEx short: end it, then go on
                    s = self.sysex + [0xF7]
                    out.append(self.pkt({1: 0x5, 2: 0x6, 3: 0x7}[len(s)], *s))
                    self.sysex = None
                    out += self.feed(bytes([b]))
                else:
                    self.sysex.append(b)
                    if len(self.sysex) == 3:
                        out.append(self.pkt(0x4, *self.sysex))
                        self.sysex = []
                continue
            if b == 0xF0:
                self.sysex = [0xF0]
                self.status = 0
                continue
            if b & 0x80:                                   # a status byte
                if b >= 0xF0:                              # system common
                    self.status = 0
                    if b in (0xF1, 0xF3):
                        self.status, self.need, self.data = b, 1, [b]
                    elif b == 0xF2:
                        self.status, self.need, self.data = b, 2, [b]
                    else:                                  # F4 F5 F6 (F7 alone: a stray end, dropped as F7 is only in a SysEx)
                        if b != 0xF7:
                            out.append(self.pkt(0x5, b))
                    continue
                self.status = b
                self.need = 2 if (b & 0xF0) not in (0xC0, 0xD0) else 1
                self.data = [b]
                continue
            if not self.status:                            # a data byte with nothing before it: dropped
                continue
            if self.need == 0:                             # running status: a new message with the old status
                self.data = [self.status]
                self.need = 2 if (self.status & 0xF0) not in (0xC0, 0xD0) else 1
                if self.status >= 0xF0:
                    self.need = 1 if self.status in (0xF1, 0xF3) else 2
            self.data.append(b)
            self.need -= 1
            if self.need == 0:
                st = self.data[0]
                cin = {0xF1: 0x2, 0xF3: 0x2, 0xF2: 0x3}.get(st, st >> 4)
                out.append(self.pkt(cin, *self.data))
                if st >= 0xF0:
                    self.status = 0
        return out


def slip_encode(frame):
    out = bytearray([SLIP_END])
    for b in frame:
        if b == SLIP_END:
            out += bytes([SLIP_ESC, SLIP_ESC_END])
        elif b == SLIP_ESC:
            out += bytes([SLIP_ESC, SLIP_ESC_ESC])
        else:
            out.append(b)
    out.append(SLIP_END)
    return bytes(out)


class SlipDecoder:
    """bytes in, complete frames out (a frame = one 4-byte packet; others are dropped)"""
    def __init__(self):
        self.buf = bytearray()
        self.esc = False

    def feed(self, data):
        frames = []
        for b in data:
            if b == SLIP_END:
                if len(self.buf) == 4:
                    frames.append(bytes(self.buf))
                self.buf = bytearray()
                self.esc = False
            elif self.esc:
                self.esc = False
                self.buf.append(SLIP_END if b == SLIP_ESC_END else SLIP_ESC if b == SLIP_ESC_ESC else b)
            elif b == SLIP_ESC:
                self.esc = True
            else:
                self.buf.append(b)
                if len(self.buf) > 4:                      # garbage: wait for the next END
                    self.buf = bytearray(b'\xff' * 5)
        return frames
