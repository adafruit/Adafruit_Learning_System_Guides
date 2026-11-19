# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Touch input for the Raspberry Pi Touch Display 2 (GT911 controller, polled).

The default board I2C bus is released and reopened at 400 kHz for faster touch
reads. Pass the display's rotation so taps come back in screen coordinates.
"""

import time

import adafruit_gt911
import board
import busio

TAP_LOCKOUT_MS = 150  # ignore a new touch this soon after a tap (bounce)


def _ms():
    return time.monotonic_ns() // 1000000


class Touch:
    def __init__(self, rotation):
        board.I2C().deinit()
        self.i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        self.gt = adafruit_gt911.GT911(self.i2c, rotation=rotation)
        self.down = False
        self.last_tap = -10000
        self.x = self.y = 0

    def tapped(self):
        """True once per new touch, with the position in self.x and self.y."""
        touches = self.gt.touch
        down = len(touches) > 0
        tap = down and not self.down
        self.down = down
        if tap:
            now = _ms()
            if now - self.last_tap < TAP_LOCKOUT_MS:
                return False
            self.last_tap = now
            self.x = touches[0]["x"]
            self.y = touches[0]["y"]
        return tap
