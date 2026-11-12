# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""The Metro ESP32-P4's hardware for fm1ui.device (docs/PLAN-v2.md, Phase 1).

fm1ui.device imports these:

- display: the 2.8" TFT Touch Shield's ILI9341, 320x240, on board.SPI()
  through the ICSP header (CS D10, DC D9), no jumpers;
- touch: found on I2C at start-up. The capacitive shield (1947) has an
  FT6206 at 0x38, reporting portrait; the resistive one (1651) a TSC2007 at
  0x48, read as 12-bit raw values and mapped with RES_CAL;
- SD card: the Metro's own slot, 4-bit SDIO, on pins of its own (so the
  card never shares a bus with the display, unlike the Feather, DEVNOTES 6.18);
- USB host: the P4's USB-A port (needs CircuitPython main at 92da735b06
  or later, for the 512-byte enumeration buffer and the TinyUSB DWC2 abort
  fix, patches/README.md).
"""
# Disabled for the Learn Guides lint check: the board's hardware objects are module-level, made
# once; modules are imported where they're needed, to keep RAM free and start-up quick; methods
# kept on their class: the screen interface, or overridden; fm1ui's modules share a few internal
# helpers.
# pylint: disable=global-statement,import-outside-toplevel,no-self-use,protected-access
# pylint: disable=cyclic-import  # the cycles go through imports inside functions
import time

import board
import displayio
import fourwire
import supervisor

from fm1ui import app as A

W, H = 320, 240
# The FT6206 reports the panel's portrait frame: x = 319 - raw y, y = raw x,
# as (ax, bx, ay, by) for x = ax * raw_y + bx, y = ay * raw_x + by. Measured
# with tools/device/metro_spike_display.py (the dot followed the finger).
TOUCH_CAL = (-1, 319, 1, 0)
# The TSC2007 on the resistive shield: (swap, ax, bx, ay, by) for
# x = ax * u + bx, y = ay * v + by, where (u, v) is the raw (x, y), or the raw
# (y, x) when swap is True. Measure it with tools/device/metro_spike_resistive.py.
RES_CAL = (True, -0.0877, 333.2, 0.0656, -12.8)  # a first guess, not measured yet
RES_PRESSURE = 100  # raw Z1 below this is no touch (adafruit_tsc2007's own threshold)
FT6206_ADDR, TSC2007_ADDR = 0x38, 0x48

_host = None  # (power pin, usb_host.Port): kept alive for usb.core

SPLASH = "/splash.bmp"  # art/splash_text_320.png (tools/deploy.py --board metro-p4)
SPLASH_HOLD = 2.0  # seconds the splash stays up after display_redo()
_splash_bmp = None


def _started():
    return supervisor.runtime.run_reason == supervisor.RunReason.STARTUP


def display_setup():
    import adafruit_ili9341
    displayio.release_displays()
    spi = board.SPI()
    # 80 MHz: clean on the shield, and scrolling pages need it (29 fps, not
    # 22 at 40 MHz; tools/device/metro_spike_scroll.py).
    bus = fourwire.FourWire(spi, command=board.D9, chip_select=board.D10, baudrate=80_000_000)
    return adafruit_ili9341.ILI9341(bus, width=W, height=H, auto_refresh=False), spi


def _show_splash(display):
    g = displayio.Group()
    g.append(displayio.TileGrid(_splash_bmp, pixel_shader=_splash_bmp.pixel_shader))
    display.root_group = g
    display.refresh()


def splash(display):
    """After a start (not a reload), show the splash until the first screen."""
    global _splash_bmp
    if not _started():
        return
    try:
        _splash_bmp = displayio.OnDiskBitmap(SPLASH)
    except OSError:
        return
    _show_splash(display)


def display_redo(display):
    """Hold the splash SPLASH_HOLD s, just before the first screen. (The
    Feather's panel needed its setup sent again here, DEVNOTES 6.20; the
    shield hasn't.)"""
    global _splash_bmp
    if not _started() or _splash_bmp is None:
        return
    prev = display.root_group
    _show_splash(display)
    time.sleep(SPLASH_HOLD)
    display.root_group = prev
    _splash_bmp = None


def host_setup(_spi):
    """5 V on the USB-A port and the host on it."""
    global _host
    if _host is None:
        import digitalio
        import usb_host
        power = digitalio.DigitalInOut(board.USB_HOST_POWER)
        power.switch_to_output(value=True)
        _host = (power, usb_host.Port(board.USB_HOST_DP, board.USB_HOST_DM))


def mount_sd(_spi):
    """Mount the Metro's microSD at /sd. False if there is no card."""
    import storage
    try:
        storage.getmount("/sd")
        return True  # mounted before a soft reload
    except OSError:
        pass
    try:
        import sdioio
        sd = sdioio.SDCard(clock=board.SD_CLK, command=board.SD_CMD,
                           data=[board.SD_DATA0, board.SD_DATA1, board.SD_DATA2, board.SD_DATA3],
                           frequency=40_000_000)
        storage.mount(storage.VfsFat(sd), "/sd")
        return True
    except (OSError, ValueError, RuntimeError):
        return False


class Network:
    """WiFi for Update firmwares (fm1ui.update) and Settings > WiFi
    (fm1ui.settings): the networks saved there, kept in NVM so they stay with
    the flasher when the card changes, and the one in settings.toml, which
    CircuitPython itself joins at start (its web workflow)."""

    NVM_WIFI = b"FM1W"
    NVM_AT = 4096  # fm1ui.device keeps 0 (a queued install) and 512 (the list state)
    JOIN_S = 15

    def __init__(self):
        from fm1ui import device as D
        from fm1ui import networks
        self.http = None
        self.saved = networks.Saved(lambda: D._nvm_read(self.NVM_WIFI, self.NVM_AT),
                                    lambda s: D._nvm_write(self.NVM_WIFI, self.NVM_AT, s.encode()))

    @staticmethod
    def toml():
        """settings.toml's (ssid, password), or None."""
        import os
        ssid = os.getenv("CIRCUITPY_WIFI_SSID")
        return (ssid, os.getenv("CIRCUITPY_WIFI_PASSWORD") or "") if ssid else None

    def status(self):
        """(the network joined, its IP address), or (None, None)."""
        import wifi
        if not wifi.radio.connected:
            return None, None
        info = wifi.radio.ap_info
        return (info.ssid if info else "?"), str(wifi.radio.ipv4_address)

    def scan(self):
        """Networks in range as (ssid, rssi, open), one per name, strongest first."""
        import wifi
        from fm1ui import networks
        found = []
        try:
            for n in wifi.radio.start_scanning_networks():
                found.append((n.ssid, n.rssi, wifi.AuthMode.OPEN in n.authmode))
        finally:
            wifi.radio.stop_scanning_networks()
        return networks.strongest(found)

    def join(self, ssid, password):
        """Join one network. None when joined, else what went wrong; then
        it goes back to the network it was on, if it knows that password."""
        import wifi
        before, _ = self.status()
        try:
            wifi.radio.connect(ssid, password, timeout=self.JOIN_S)
            return None
        except (ConnectionError, OSError) as e:
            err = str(e) or repr(e)
        from fm1ui import networks
        for s, p in networks.candidates(self.saved, self.toml()):
            if before and s == before and s != ssid:
                try:
                    wifi.radio.connect(s, p, timeout=self.JOIN_S)
                except (ConnectionError, OSError):
                    pass
        return err

    def connect(self):
        """Be on a network: stay on the one joined, else the first saved one
        in range (most recently used first), then settings.toml's. None when
        connected, else what to tell the user."""
        import wifi
        from fm1ui import networks
        if not wifi.radio.connected:
            tries = networks.candidates(self.saved, self.toml())
            if not tries:
                return ("No WiFi set up. Add a network in Settings (the gear), "
                        "or in settings.toml on CIRCUITPY.")
            try:
                seen = [n[0] for n in self.scan()]
                tries = [c for c in tries if c[0] in seen]
                if not tries:
                    return "None of the saved WiFi networks is in range."
            except (OSError, RuntimeError):
                pass  # can't scan: try them all
            err = None
            for ssid, password in tries:
                err = self.join(ssid, password)
                if err is None:
                    self.saved.used(ssid)
                    break
            else:
                return "Couldn't join WiFi %s (%s)." % (tries[-1][0], err)
        if self.http is None:
            import adafruit_connection_manager as cm
            import adafruit_requests
            pool = cm.get_radio_socketpool(wifi.radio)
            self.http = adafruit_requests.Session(pool, cm.get_radio_ssl_context(wifi.radio))
        return None

    def _get(self, url):
        r = self.http.get(url, headers={"User-Agent": "FM-1_Flasher"}, timeout=30)
        if r.status_code != 200:
            r.close()
            raise OSError("HTTP %d for %s" % (r.status_code, url.rsplit("/", 1)[-1]))
        return r

    def get(self, url):
        r = self._get(url)
        try:
            return r.content
        finally:
            r.close()

    def get_json(self, url):
        r = self._get(url)
        try:
            return r.json()
        finally:
            r.close()

    def stream(self, url, chunk=8192):
        r = self._get(url)
        try:
            for data in r.iter_content(chunk_size=chunk):
                yield data
        finally:
            r.close()


def find_touch(i2c):
    """Which touch chip the shield has: "ft6206", "tsc2007" or None."""
    while not i2c.try_lock():
        pass
    try:
        found = i2c.scan()
    finally:
        i2c.unlock()
    if FT6206_ADDR in found:
        return "ft6206"
    if TSC2007_ADDR in found:
        return "tsc2007"
    return None


class Resistive:
    """The TSC2007's raw readings made steady enough for Gestures.

    A resistive panel's readings jitter and its pressure flickers, most at
    the start and end of a touch. Each sample is the median of three reads;
    a touch starts after two pressed samples in a row and ends after two
    released ones, so a flicker in the middle of a drag doesn't split it into
    two taps."""

    READS = 3
    HOLD = 2  # samples in a row that start or end a touch

    def __init__(self, i2c, cal=RES_CAL, pressure=RES_PRESSURE):
        import adafruit_tsc2007
        self.tsc = adafruit_tsc2007.TSC2007(i2c, address=TSC2007_ADDR)
        self.cal = cal
        self.pressure = pressure
        self.point = None  # the touch being reported, in raw units
        self.run = 0  # samples in a row that disagree with self.point

    def read(self):
        """The median raw (x, y) of a few reads, or None when not pressed."""
        xs, ys = [], []
        for _ in range(self.READS):
            p = self.tsc.touch
            if p["pressure"] < self.pressure:
                return None
            xs.append(p["x"])
            ys.append(p["y"])
        xs.sort()
        ys.sort()
        return xs[len(xs) // 2], ys[len(ys) // 2]

    def sample(self):
        """The current touch in raw units, or None."""
        p = self.read()
        if (p is None) == (self.point is None):
            self.run = 0
            if p is not None:
                self.point = p
            return self.point
        self.run += 1
        if self.run >= self.HOLD:
            self.run = 0
            self.point = p
        return self.point

    def map(self, x, y):
        swap, ax, bx, ay, by = self.cal
        u, v = (y, x) if swap else (x, y)
        return (min(W - 1, max(0, int(ax * u + bx))),
                min(H - 1, max(0, int(ay * v + by))))


class Touch:
    """The shield's touch polled into taps and swipes, in display
    coordinates: the FT6206 (capacitive shield) or the TSC2007 (resistive
    shield), whichever answers on I2C. With neither, there are no touches."""

    def __init__(self, cal=TOUCH_CAL, debug=False):
        i2c = board.I2C()
        self.kind = find_touch(i2c)
        self.ft = self.res = None
        if self.kind == "ft6206":
            import adafruit_focaltouch
            self.ft = adafruit_focaltouch.Adafruit_FocalTouch(i2c)
        elif self.kind == "tsc2007":
            self.res = Resistive(i2c)
        print("touch:", self.kind or "none found (no FT6206 at 0x38, no TSC2007 at 0x48)")
        self.cal = cal
        self.debug = debug
        self.first = None
        self.gestures = A.Gestures()

    def map(self, x, y):
        if self.res:
            return self.res.map(x, y)
        ax, bx, ay, by = self.cal
        return (min(W - 1, max(0, int(ax * y + bx))),
                min(H - 1, max(0, int(ay * x + by))))

    def raw(self):
        try:
            if self.res:
                return self.res.sample()
            if self.ft:
                pts = self.ft.touches
                if pts:
                    return pts[0]["x"], pts[0]["y"]
        except OSError:  # an I2C hiccup reads as no touch
            pass
        return None

    def event(self):
        p = self.raw()
        if self.debug and p and self.first is None:
            self.first = p
        self.gestures.sample(self.map(*p) if p else None)
        ev = self.gestures.event()
        if self.debug and p is None and self.first is not None:
            print("touch raw", self.first, "mapped", self.map(*self.first), "->", ev)
            self.first = None
        return ev
