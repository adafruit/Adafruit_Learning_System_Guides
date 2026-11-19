# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-or-later
# pylint: disable=import-outside-toplevel
"""Touch input for the capacitive 2.8" TFT shield (FT6206 at I2C 0x38, polled).

The FT6206 reports positions in the panel's fixed 240x320 portrait frame, so no
calibration is needed: map_for_rotation() gives a fixed affine map to screen
coordinates, in the same form as chess_touch_tsc's calibration.

Has the same interface as chess_touch_tsc.Touch, with needs_calibration False.
"""

import time

import adafruit_focaltouch

ADDRESS = 0x38
TAP_LOCKOUT_MS = 150  # ignore a new touch this soon after a tap (bounce)
RELEASE_MS = 40  # a touch ends after this long with no contact


def _ms():
    return time.monotonic_ns() // 1000000


# Raw-to-screen map measured at rotation 180:
#   screen x = SX * raw_y + OX,  screen y = OY - SY * raw_x
# The scales are below 1 because the raw range reaches a little past the display.
SX, OX = 0.959, 4.4
SY, OY = 0.887, 221.8


def map_for_rotation(rotation, width=320, height=240):
    """Affine map (a, b, c, d, e, f) for the display rotation, where
    screen x = a*rx + b*ry + c and y = d*rx + e*ry + f. Only the landscape
    rotations 0 and 180 are supported; others raise ValueError."""
    rotation %= 360
    if rotation == 180:
        return (0.0, SX, OX, -SY, 0.0, OY)
    if rotation == 0:
        return (0.0, -SX, width - 1 - OX, SY, 0.0, height - 1 - OY)
    raise ValueError("capacitive shield touch: rotation must be 0 or 180")


class Touch:
    needs_calibration = False

    def __init__(self, width=320, height=240, rotation=0, i2c=None):
        if i2c is None:
            import board
            import busio

            try:
                board.I2C().deinit()
            except (RuntimeError, ValueError):
                pass
            i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        self.i2c = i2c
        self.width, self.height = width, height
        # OSError if nothing answers, RuntimeError if it isn't a FocalTech chip
        self.ft = adafruit_focaltouch.Adafruit_FocalTouch(i2c, address=ADDRESS)
        self.cal = map_for_rotation(rotation, width, height)
        self.down = False
        self.up_since = None
        self.last_tap = -10000
        self.x = self.y = 0
        self.raw_x = self.raw_y = 0

    def raw(self):
        """(raw_x, raw_y) of the first touch point, or None if not touched."""
        n = self.ft.touched
        if n < 1 or n > 2:  # the FT6206 tracks up to two points; more is noise
            return None
        try:
            pts = self.ft.touches
        except (ValueError, OSError):
            return None
        if not pts:
            return None
        return pts[0]["x"], pts[0]["y"]

    def pressed(self):
        return 1 <= self.ft.touched <= 2

    def to_screen(self, rx, ry, cal=None):
        a, b, c, d, e, f = cal or self.cal
        x = int(a * rx + b * ry + c + 0.5)
        y = int(d * rx + e * ry + f + 0.5)
        return (min(self.width - 1, max(0, x)), min(self.height - 1, max(0, y)))

    def tapped(self):
        """True once per new touch, with the screen position in self.x and self.y."""
        now = _ms()
        p = self.raw()
        if p is None:
            if self.down:
                if self.up_since is None:
                    self.up_since = now
                elif now - self.up_since >= RELEASE_MS:
                    self.down = False
            return False
        self.up_since = None
        if self.down:
            return False
        self.down = True
        if now - self.last_tap < TAP_LOCKOUT_MS:
            return False
        self.last_tap = now
        self.raw_x, self.raw_y = p
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
