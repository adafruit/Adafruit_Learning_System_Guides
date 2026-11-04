# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""The flasher's hardware for the UI, the FM-1 on the USB host port, and
running an install.

The display, touch, SD card, USB host and WiFi come from fm1ui.metro_p4
(Metro ESP32-P4 with the 2.8" TFT Touch Shield). v1's Feather code is at
the tag v1-feather-final.

An install runs in place, from the confirm screen, on a transport opened for
it. (The Feather reloaded first, to install on an unfragmented heap, DEVNOTES
§6.7; the Metro's 16 MB doesn't need that.)
"""
# Disabled for the Learn Guides lint check: modules are imported where they're needed, to keep RAM
# free and start-up quick; methods kept on their class: the screen interface, or overridden; some
# drawing and protocol functions are long by nature.
# pylint: disable=import-outside-toplevel,no-self-use,too-many-locals,too-many-statements
import json
import time

import microcontroller
import usb.core

import fm1usb
from fm1ui import catalog as C
# The board's hardware, re-exported for code.py (D.display_setup() and so on).
from fm1ui.metro_p4 import (  # pylint: disable=unused-import  # noqa: F401
    display_setup, splash, display_redo, host_setup, mount_sd, Touch, Network)

# fm1proto and fm1update (the installer) are imported only by run(). The
# list screen's FM-1 probe below needs just the identity query.

ANSWER_WAIT_S = 15  # for the FM-1 to answer when an install starts


def firmware_root(sd):
    for root in (("/sd/firmware",) if sd else ()) + ("/firmware",):
        try:
            open(root + "/index.txt").close()
            return root
        except OSError:
            pass
    return None


# fm1proto.frame(CMD_IDENTITY): the identity query, which never changes
IDENTITY_QUERY = bytes.fromhex("f0003245000000407ff7")
CMD_IDENTITY = 17


def _unpack(sysex):
    """(command, data) from a valid FM-1 reply, else None: fm1proto.parse,
    kept here so probing doesn't load the installer."""
    n = len(sysex)
    if n < 10 or n > 608 or sysex[0] != 0xF0 or sysex[n - 1] != 0xF7:
        return None
    raw = bytearray()
    bits = value = 0
    for i in range(1, n - 1):
        if sysex[i] > 127:
            return None
        value |= sysex[i] << bits
        bits += 7
        if bits >= 8:
            raw.append(value & 0xFF)
            value >>= 8
            bits -= 8
    if bits >= 7 or value or len(raw) < 7 or raw[0] or raw[1] != 0x59:
        return None
    if raw[3] | (raw[4] << 8) | (raw[5] << 16) != len(raw) - 7 or sum(raw[6:]) & 0xFF != 0xFF:
        return None
    return raw[2], bytes(raw[6:-1])


def query_identity(transport, ms=750):
    """The FM-1's identity string, or None if it doesn't answer in time."""
    while transport.recv(0) is not None:
        pass
    transport.send(IDENTITY_QUERY)
    end = time.monotonic() + ms / 1000
    while time.monotonic() < end and not transport.lost:
        msg = transport.recv(250)
        p = _unpack(msg) if msg else None
        if p and p[0] == CMD_IDENTITY:
            data = p[1]
            s = bytes(data).split(b"\0", 1)[0].decode()
            if len(data) == 27 and s and all(0x20 <= ord(c) <= 0x7E for c in s):
                return s
    return None


def find_fm1(seconds, idle=None):
    """(transport, identity, queries) for an FM-1 that answers an identity
    query within `seconds`; transport and identity are None if none does.
    idle() runs between tries.

    After a reload the first query or two on the FM-1 get no reply, then it
    answers at once, but only on the same transport: reopening each try
    (endpoints closed and opened again) never got an answer in 15 s
    (logs/ui-install1.log). So one transport is kept for the whole wait, and
    the caller keeps using it."""
    t0 = time.monotonic()
    t = None
    tries = 0
    while time.monotonic() - t0 < seconds:
        try:
            if t is None or t.lost:
                if t is not None:
                    t.close()
                found = fm1usb.finder(None, 64, 0)()
                for other in found[1:]:
                    other.close()
                t = found[0] if found else None
            if t is not None:
                tries += 1
                ident = query_identity(t)
                if ident:
                    return t, ident, tries
        except (usb.core.USBError, OSError, ValueError) as e:
            print("find_fm1:", repr(e))
            if t is not None:
                t.close()
            t = None
        if idle:
            idle()
        time.sleep(0.25)
    if t is not None:
        t.close()
    return None, None, tries


def _usb_devices():
    return tuple((d.idVendor, d.idProduct) for d in usb.core.find(find_all=True))


class Probe:
    """The FM-1 the user connected with Connect FM-1. Nothing is sent to the
    FM-1 until connect(); present() only lists the USB devices, to notice
    an unplug. The answering transport is kept until then, so the FM-1
    stays ready to answer (see find_fm1)."""

    CONNECT_S = 6  # after a reload V15 answered on the 3rd query, 2.2 s in

    def __init__(self):
        self.t = None
        self.devices = None

    def close(self):
        if self.t is not None:
            self.t.close()
            self.t = None

    def connect(self):
        """The FM-1's identity, or None if none answered."""
        self.close()
        t0 = time.monotonic()
        t, ident, tries = find_fm1(self.CONNECT_S)
        print("connect: %s after %.1f s, %d queries" % (ident, time.monotonic() - t0, tries))
        if ident:
            self.t = t
            try:
                self.devices = _usb_devices()
            except (usb.core.USBError, OSError):
                self.devices = None
        return ident

    def present(self):
        """Is the connected FM-1 still attached? Sends nothing to it."""
        if self.t is None:
            return False
        try:
            devices = _usb_devices()
        except (usb.core.USBError, OSError):
            return True  # can't tell; keep it
        if self.t.lost or (self.devices is not None and devices != self.devices):
            self.close()
            return False
        return True


class DeviceState(C.State):
    """C.State that falls back to NVM when the file can't be written
    (CIRCUITPY is read-only to code while it's mounted on a computer)."""

    NVM_STATE = b"FM1S"

    def __init__(self, path):
        super().__init__(path)
        if not self.favorites and not self.installed:
            data = _nvm_read(self.NVM_STATE, 512)
            if data:
                try:
                    d = json.loads(data)
                    self.favorites = set(d.get("favorites", ()))
                    self.installed = d.get("installed")
                    self.view = d.get("view", "grid")
                    self.sort = d.get("sort", "az")
                    self.scroll = d.get("scroll", True)
                except ValueError:
                    pass

    def save(self):
        if super().save():
            return True
        data = json.dumps(
            {
                "favorites": sorted(self.favorites),
                "installed": self.installed,
                "view": self.view,
                "sort": self.sort,
                "scroll": self.scroll,
            }
        )
        return _nvm_write(self.NVM_STATE, 512, data.encode())


def _nvm_read(tag, at):
    nvm = microcontroller.nvm
    if nvm is None or bytes(nvm[at:at + 4]) != tag:
        return None
    n = nvm[at + 4] | (nvm[at + 5] << 8)
    return bytes(nvm[at + 6:at + 6 + n]).decode()


def _nvm_write(tag, at, data):
    nvm = microcontroller.nvm
    if nvm is None or at + 6 + len(data) > len(nvm):
        return False
    nvm[at:at + 6 + len(data)] = tag + bytes((len(data) & 0xFF, len(data) >> 8)) + data
    return True


class Installer:
    def start(self, app, entry):
        """Install now. Connect FM-1's transport is closed and a new one
        opened (endpoints cleared, fm1usb): handed over as it was, minutes
        after Connect, the FM-1 lost the first two queries on it, and once
        the install's next query too (4 November 2026, from Aisling)."""
        if app.probe is not None:
            app.probe.close()
        run(app, entry)


def wait_for_fm1(screen, seconds=ANSWER_WAIT_S):
    """The transport of an FM-1 that answers an identity query, or None.
    The installer is handed that same transport (see find_fm1)."""
    t0 = time.monotonic()
    waiting = []

    def idle():
        if not waiting:
            screen.wait("connect", "Waiting for the FM-1 to connect...")
            waiting.append(True)
        screen.tick(time.monotonic())

    t, ident, tries = find_fm1(seconds, idle)
    if ident:
        print("install: %s answered after %.1f s, query %d" % (ident, time.monotonic() - t0, tries))
        if waiting:
            screen.found()
    else:
        print("install: no FM-1 answered in %d s (%d queries)" % (seconds, tries))
    return t


def run(app, entry):
    """Install `entry` with a progress screen. Returns True on success.
    Stages, waits and errors also go to the serial console."""
    import fm1proto as P
    import fm1update as U
    from fm1ui import screens as S

    class UIClock(U.Clock):
        """Lets the progress screen tick (elapsed time, hints) while the
        installer waits for the FM-1."""

        def __init__(self, screen):
            self.screen = screen

        def sleep_ms(self, ms):
            self.screen.tick(time.monotonic())
            super().sleep_ms(ms)

    screen = S.ProgressScreen(app, entry)
    app.push(screen)
    folder = app.root + "/" + entry.slug
    t0 = time.monotonic()
    last = [None]

    def status(name, pct):
        if name != last[0]:  # one line per stage, not per percent
            last[0] = name
            print("install: %.1f s %s" % (time.monotonic() - t0, name))
        screen.phase(name, pct)

    import gc
    gc.collect()
    print("install:", entry.slug, "free RAM", gc.mem_free())
    # Closed in the finally: with no reload after an install, nothing else
    # would close the package file or a transport an error left open.
    held = [None]
    pkg_file = up = None
    try:
        status("Checking package", 0)
        with open(folder + "/meta.json") as f:
            meta = json.load(f)
        pkg_file = open(folder + "/" + meta["file"], "rb")
        pkg, meta = P.prepare(meta, pkg_file, checked=True)

        def trace(event, *values):
            if event == "wait":
                screen.wait(values[0])
            elif event == "found":
                screen.found()
            if event != "read":
                print("install: %.1f s trace" % (time.monotonic() - t0), event, *values)

        status("Connecting", 0)
        held[0] = wait_for_fm1(screen)
        fresh = fm1usb.finder(None, 64, 0)

        def finder():
            # The first search gets the transport that already answered; any
            # later one (after the FM-1 restarts) finds new devices.
            t, held[0] = held[0], None
            return [t] if t is not None and not t.lost else fresh()

        up = U.Updater(finder, pkg, meta, status=status, clock=UIClock(screen))
        up.trace = trace
        print("install: connect", up.connect(force=True))
        up.install(force=True)
        app.state.record_install(entry.slug, meta["product"])
        print("install: done in %.1f s" % (time.monotonic() - t0))
        screen.finish(True, "The FM-1 restarted with %s." % entry.name)
        return True
    except Exception as e:  # pylint: disable=broad-except  # FM1Error, USBError, OSError
        print("install: failed after %.1f s:" % (time.monotonic() - t0), repr(e))
        screen.finish(False, str(e) or repr(e))
        return False
    finally:
        if up is not None:
            up.disconnect()
        if held[0] is not None:
            held[0].close()
        if pkg_file is not None:
            pkg_file.close()
