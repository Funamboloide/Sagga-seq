#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""0.32.2: python-rtmidi's way of closing an input, in small - enough of it to lock up, and to show what does not.

The real thing (python-rtmidi 1.5.8 under mido 1.3.3, read in their sources):
  * every function of the driver is called with the Python interpreter held (the GIL: the Cython wrapper has no
    `nogil` anywhere), closePort() too;
  * closePort() tells the port's thread to end and waits for it (pthread_join);
  * the port's thread hands what comes in to a callback that is Python: it must get the interpreter first;
  * mido always gives the driver a callback (its own wrapper, when the program gave none), and its close() puts that
    wrapper back in (`callback = None`) just before it closes.
So a message that comes in the moments before a close leaves the thread waiting for the interpreter and the closing
waiting for the thread: for ever, with the interpreter held - no signal handler, no other Python thread runs again.

Here: a driver of forty lines of C with exactly that shape (a thread that polls a pipe and calls back; a close that
joins it), called through ctypes.PyDLL (the interpreter held during the call, as Cython does) with a ctypes callback
(which takes the interpreter, as Cython's `with gil` does); around it the part of python-rtmidi's MidiIn and of mido's
Input that a close goes through. No ALSA, no MIDI: this runs anywhere there is a C compiler.

    python3 tests/sagga_lockup.py SCENARIO     one scenario, in this process (it may never come back: that is the point)

tests/sagga_wayout_tests.py runs each scenario in a process of its own and says which ones came back.
"""
import ctypes
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

C_SOURCE = r"""
#include <pthread.h>
#include <poll.h>
#include <stdlib.h>
#include <unistd.h>

typedef void (*cb_t)(int);
typedef struct {
    pthread_t th, storm_th;
    int msg[2], trig[2];
    volatile int do_input, using_cb, storm_us;
    volatile cb_t cb;
    volatile long called, kept;
} rt_t;

static void *handler(void *arg)                      /* RtMidi's alsaMidiHandler: wait, read, hand over */
{
    rt_t *r = arg;
    while (r->do_input) {
        struct pollfd p[2] = {{r->msg[0], POLLIN, 0}, {r->trig[0], POLLIN, 0}};
        char c;
        if (poll(p, 2, -1) < 0) continue;
        if (p[1].revents & POLLIN) { if (read(r->trig[0], &c, 1) < 0) {} continue; }
        if (!(p[0].revents & POLLIN) || read(r->msg[0], &c, 1) != 1) continue;
        if (r->using_cb) { r->called++; r->cb((int)c); }      /* Python: this thread needs the interpreter */
        else r->kept++;                                       /* no callback: the message stays in the driver */
    }
    return 0;
}

static void *storm(void *arg)                        /* a device that sends without pause (no interpreter needed) */
{
    rt_t *r = arg;
    while (r->storm_us) { if (write(r->msg[1], "s", 1) < 0) {} usleep((useconds_t)r->storm_us); }
    return 0;
}

rt_t *rt_open(void)
{
    rt_t *r = calloc(1, sizeof *r);
    if (!r || pipe(r->msg) || pipe(r->trig)) return 0;
    r->do_input = 1;
    if (pthread_create(&r->th, 0, handler, r)) return 0;
    return r;
}
void rt_set_callback(rt_t *r, cb_t cb) { r->cb = cb; r->using_cb = 1; }
void rt_cancel_callback(rt_t *r) { r->using_cb = 0; }
void rt_close_port(rt_t *r)                          /* RtMidi's closePort: tell the thread, wait for it */
{
    if (!r->do_input) return;
    r->do_input = 0;
    if (write(r->trig[1], "x", 1) < 0) {}
    pthread_join(r->th, 0);
}
void rt_feed(rt_t *r, int n) { while (n-- > 0) if (write(r->msg[1], "m", 1) < 0) {} }
void rt_storm(rt_t *r, int us)
{
    if (us && !r->storm_us) { r->storm_us = us; pthread_create(&r->storm_th, 0, storm, r); }
    else if (!us && r->storm_us) { r->storm_us = 0; pthread_join(r->storm_th, 0); }
}
long rt_called(rt_t *r) { return r->called; }
long rt_kept(rt_t *r) { return r->kept; }
"""

CB = ctypes.CFUNCTYPE(None, ctypes.c_int)
_lib = [None]
_thunks = []                                           # (ctypes callbacks, alive as long as a thread may call them)


def lib():
    """the driver, compiled once (build/lockup_rt.so), opened with the interpreter held during every call"""
    if _lib[0] is None:
        folder = os.path.join(ROOT, "build")
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError:
            folder = tempfile.mkdtemp()
        so, src = os.path.join(folder, "lockup_rt.so"), os.path.join(folder, "lockup_rt.c")
        if not os.path.exists(so) or not os.path.exists(src) or open(src).read() != C_SOURCE:
            with open(src, "w") as f:
                f.write(C_SOURCE)
            part = "%s.%d.part" % (so, os.getpid())
            subprocess.run(["cc", "-shared", "-fPIC", "-O1", "-pthread", src, "-o", part], check=True)
            os.replace(part, so)
        L = ctypes.PyDLL(so)
        L.rt_open.restype = ctypes.c_void_p
        for name in ("rt_set_callback", "rt_cancel_callback", "rt_close_port", "rt_feed", "rt_storm"):
            getattr(L, name).restype = None
        L.rt_set_callback.argtypes = [ctypes.c_void_p, CB]
        L.rt_cancel_callback.argtypes = L.rt_close_port.argtypes = [ctypes.c_void_p]
        L.rt_feed.argtypes = L.rt_storm.argtypes = [ctypes.c_void_p, ctypes.c_int]
        L.rt_called.argtypes = L.rt_kept.argtypes = [ctypes.c_void_p]
        L.rt_called.restype = L.rt_kept.restype = ctypes.c_long
        _lib[0] = L
    return _lib[0]


class Rt:
    """python-rtmidi's MidiIn, as much of it as a close goes through (src/_rtmidi.pyx: set_callback, cancel_callback,
    close_port, delete)"""
    def __init__(self):
        self.h = lib().rt_open()
        self._callback = None
        self.said = []                                 # what was called, in order

    def set_callback(self, func, data=None):
        if self._callback:
            self.cancel_callback()
        self._callback = (func, data)
        thunk = CB(lambda v, func=func, data=data: func(([v], 0.0), data))
        _thunks.append(thunk)
        lib().rt_set_callback(self.h, thunk)
        self.said.append("set")

    def cancel_callback(self):
        if self._callback:
            lib().rt_cancel_callback(self.h)
            self._callback = None
            self.said.append("cancel")

    def close_port(self):
        self.cancel_callback()
        self.said.append("close")
        lib().rt_close_port(self.h)                    # (the interpreter held, and the wait for the thread)

    def delete(self):
        self.said.append("delete")

    def feed(self, n=1):
        lib().rt_feed(self.h, n)

    def storm(self, us):
        lib().rt_storm(self.h, us)

    @property
    def called(self):
        return lib().rt_called(self.h)

    @property
    def kept(self):
        return lib().rt_kept(self.h)


class Port:
    """mido's rtmidi Input, as much of it as a close goes through (mido/backends/rtmidi.py: the callback's setter,
    _callback_wrapper, _close; mido/ports.py: close)"""
    def __init__(self, callback=None):
        self.closed, self.got = False, []
        self._rt = Rt()
        self.callback = callback

    @property
    def callback(self):
        return self._callback

    @callback.setter
    def callback(self, func):
        self._rt.cancel_callback()
        self._callback = func
        self._rt.set_callback(self._callback_wrapper)  # (mido: always a callback in the driver - its own wrapper)

    def _callback_wrapper(self, msg_data, data):
        (self._callback or self.got.append)(msg_data[0])

    def close(self):
        if not self.closed:
            self.callback = None
            self._rt.close_port()
            self._rt.delete()
            self.closed = True


def in_flight(port):
    """a message the port's thread is handing to Python while this thread holds the interpreter: what a message that
    comes in the moments before a close is. (The interpreter changes hands only when this thread waits: the switch
    interval is made long, and this thread is kept busy while the port's thread reads the message.)"""
    sys.setswitchinterval(1000.0)
    port._rt.feed(1)
    t = time.perf_counter()
    while time.perf_counter() - t < 0.05:
        pass
    return port._rt.called                              # 1: the thread is in its call, waiting for the interpreter


def closer(which):
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    sys.path.insert(0, os.path.join(ROOT, "tools", "hwtest"))
    if which == "mido":
        return lambda port: port.close()
    if which == "bridge":
        import sagga_grid_bridge as B
        return lambda port: B.close_inputs([port])
    if which == "installer":
        import fm1_install as FI
        return FI.close_input
    if which == "hwtest":
        import sagga_hw_test as HT
        return HT.close_input
    raise SystemExit("closer %r" % which)


def scenario(name):
    """one scenario; prints `ok ...` and returns 0 when the closing came back"""
    kind, _, which = name.partition(":")
    close = closer(which)
    if kind == "flight":                               # a message on its way as the port is closed
        heard = []
        port = Port(heard.append)
        n = in_flight(port)
        close(port)
        print("ok flight %s: closed, %d call on its way, heard %d, port.closed %s, driver %s" % (
            which, n, len(heard), port.closed, " ".join(port._rt.said)))
        return 0 if n == 1 and port.closed else 1
    if kind == "storm":                                # a device that sends without pause, a port opened and closed
        rounds, heard = 60, []
        for k in range(rounds):
            port = Port(heard.append)
            port._rt.storm(100)
            time.sleep(0.004)
            close(port)
            port._rt.storm(0)
        print("ok storm %s: %d ports closed under a message every 100 us, %d heard" % (which, rounds, len(heard)))
        return 0 if heard else 1
    if kind == "quiet":                                # nothing comes: any closing comes back
        port = Port(lambda m: None)
        close(port)
        print("ok quiet %s: closed, driver %s" % (which, " ".join(port._rt.said)))
        return 0
    raise SystemExit("scenario %r" % name)


if __name__ == "__main__":
    sys.exit(scenario(sys.argv[1]))
