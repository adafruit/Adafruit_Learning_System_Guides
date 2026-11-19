# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-or-later
# pylint: disable=import-outside-toplevel
"""Touch input for the resistive 2.8" TFT shield (TSC2007 at I2C 0x48, polled).

Readings are raw 12-bit values, so the screen needs calibrating: fit() makes an
affine map from three crosshair taps, which works for any display rotation. The
map is saved in microcontroller.nvm at CAL_OFFSET, after chess_settings' bytes.

tapped() is True once per new touch, with the screen position in x and y.
"""

import struct
import time

import board
import busio

ADDRESS = 0x48
Z_MIN = 100  # pressure (Z1) above this counts as pressed
SPREAD_MAX = 60  # max spread of one reading's samples, in raw units
RELEASE_MS = 40  # a touch ends after this long with no pressure
TAP_LOCKOUT_MS = 150  # ignore a new touch this soon after a tap (bounce)

CAL_OFFSET = 8
CAL_MAGIC = b"TK\x01"
CAL_FORMAT = "<6f"
CAL_SIZE = 3 + struct.calcsize(CAL_FORMAT)

# TSC2007 command byte: function << 4 | power << 2 | resolution << 1 (0 = 12 bit)
_X = 0xC0 | 1 << 2  # measure X, keep the ADC on
_Y = 0xD0 | 1 << 2
_Z1 = 0xE0 | 1 << 2
_Z1_OFF = 0xE0  # measure Z1, then power down


def _ms():
    return time.monotonic_ns() // 1000000


def fit(raw, screen):
    """Fits three raw (rx, ry) points to three screen (sx, sy) points.

    Returns (a, b, c, d, e, f) where sx = a*rx + b*ry + c and sy = d*rx + e*ry + f,
    or None if the points are too close to a line."""
    (x1, y1), (x2, y2), (x3, y3) = raw
    det = x1 * (y2 - y3) - y1 * (x2 - x3) + (x2 * y3 - x3 * y2)
    if abs(det) < 1e3:
        return None

    def solve(v1, v2, v3):
        a = (v1 * (y2 - y3) - y1 * (v2 - v3) + (v2 * y3 - v3 * y2)) / det
        b = (x1 * (v2 - v3) - v1 * (x2 - x3) + (x2 * v3 - x3 * v2)) / det
        c = (
            x1 * (y2 * v3 - y3 * v2)
            - y1 * (x2 * v3 - x3 * v2)
            + v1 * (x2 * y3 - x3 * y2)
        ) / det
        return a, b, c

    return solve(*[p[0] for p in screen]) + solve(*[p[1] for p in screen])


class Touch:
    needs_calibration = True

    def __init__(self, width=320, height=240, i2c=None, nvm=None):
        if i2c is None:
            try:
                board.I2C().deinit()
            except (RuntimeError, ValueError):
                pass
            i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        self.i2c = i2c
        self.width, self.height = width, height
        self._cmd = bytearray(1)
        self._buf = bytearray(2)
        self._read(_Z1_OFF)  # raises OSError if nothing answers at 0x48
        if nvm is None:
            try:
                import microcontroller

                nvm = microcontroller.nvm
            except (ImportError, AttributeError):
                nvm = None
        self._nvm = nvm
        self.cal = self.load_calibration()
        self.down = False
        self.up_since = None
        self.last_tap = -10000
        self.x = self.y = 0
        self.raw_x = self.raw_y = 0

    # ------------------------------------------------------------ chip

    def _read(self, cmd):
        self._cmd[0] = cmd
        i2c = self.i2c
        while not i2c.try_lock():
            pass
        try:
            i2c.writeto_then_readfrom(ADDRESS, self._cmd, self._buf)
        finally:
            i2c.unlock()
        b = self._buf
        return (b[0] << 4) | (b[1] >> 4)

    def pressed(self):
        return self._read(_Z1_OFF) > Z_MIN

    def raw(self):
        """(raw_x, raw_y), the median of three samples each. None if the touch
        lifted during the reading or the samples disagree."""
        if self._read(_Z1) <= Z_MIN:
            self._read(_Z1_OFF)
            return None
        r = self._read
        xs = sorted((r(_X), r(_X), r(_X)))
        ys = sorted((r(_Y), r(_Y), r(_Y)))
        if self._read(_Z1_OFF) <= Z_MIN:
            return None
        if xs[2] - xs[0] > SPREAD_MAX or ys[2] - ys[0] > SPREAD_MAX:
            return None
        return xs[1], ys[1]

    # ------------------------------------------------------------ calibration

    def load_calibration(self):
        nvm = self._nvm
        if nvm is None:
            return None
        raw = bytes(nvm[CAL_OFFSET : CAL_OFFSET + CAL_SIZE])
        if raw[:3] != CAL_MAGIC:
            return None
        cal = struct.unpack(CAL_FORMAT, raw[3:])
        if any(v != v for v in cal):  # NaN  # pylint: disable=comparison-with-itself
            return None
        return cal

    def save_calibration(self, cal):
        self.cal = cal
        if self._nvm is not None:
            self._nvm[CAL_OFFSET : CAL_OFFSET + CAL_SIZE] = CAL_MAGIC + struct.pack(
                CAL_FORMAT, *cal
            )

    def to_screen(self, rx, ry, cal=None):
        a, b, c, d, e, f = cal or self.cal
        x = int(a * rx + b * ry + c + 0.5)
        y = int(d * rx + e * ry + f + 0.5)
        return (min(self.width - 1, max(0, x)), min(self.height - 1, max(0, y)))

    # ------------------------------------------------------------ taps

    def tapped(self):
        """True once per new touch, with the screen position in self.x and self.y."""
        now = _ms()
        if not self.pressed():
            if self.down:
                if self.up_since is None:
                    self.up_since = now
                elif now - self.up_since >= RELEASE_MS:
                    self.down = False
            return False
        self.up_since = None
        if self.down:
            return False
        p = self.raw()
        if p is None:  # light or moving touch: try again next poll
            return False
        self.down = True
        if now - self.last_tap < TAP_LOCKOUT_MS:
            return False
        self.last_tap = now
        self.raw_x, self.raw_y = p
        if self.cal is None:
            self.x, self.y = 0, 0
        else:
            self.x, self.y = self.to_screen(p[0], p[1])
        return True

    def wait_release(self, timeout_ms=3000):
        end = _ms() + timeout_ms
        quiet = None
        while _ms() < end:
            if self.pressed():
                quiet = None
            elif quiet is None:
                quiet = _ms()
            elif _ms() - quiet >= RELEASE_MS * 2:
                break
            time.sleep(0.01)
        self.down = False
        self.up_since = None

    def average_press(self, max_samples=24):
        """Waits for a press and returns its average raw position (for calibration)."""
        while True:
            p = self.raw()
            if p is not None:
                break
            time.sleep(0.01)
        time.sleep(0.05)  # let it settle
        sx = sy = n = 0
        misses = 0
        while n < max_samples and misses < 5:
            p = self.raw()
            if p is None:
                misses += 1
            else:
                sx += p[0]
                sy += p[1]
                n += 1
            time.sleep(0.01)
        if n == 0:
            return None
        return sx / n, sy / n
