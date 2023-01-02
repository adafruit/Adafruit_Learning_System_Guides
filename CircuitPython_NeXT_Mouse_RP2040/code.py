# SPDX-FileCopyrightText: 2023 Jeff Epler for Adafruit Industries
# SPDX-License-Identifier: MIT
import board
import digitalio
import rotaryio
from adafruit_hid.mouse import Mouse
from usb_hid import devices

SCALE = 4

class RelativeEncoder:
    def __init__(self, pin_a, pin_b, divisor=1):
        self._encoder = rotaryio.IncrementalEncoder(pin_a, pin_b, divisor)
        self._old = self._encoder.position

    @property
    def delta(self):
        old = self._old
        new = self._old = self._encoder.position
        return new - old

xpos = RelativeEncoder(board.A0, board.A1)
ypos = RelativeEncoder(board.A2, board.A3)
lmb = digitalio.DigitalInOut(board.SCL)
lmb.pull = digitalio.Pull.UP
rmb = digitalio.DigitalInOut(board.SDA)
rmb.pull = digitalio.Pull.UP

mouse = Mouse(devices)

while True:
    dx = xpos.delta * SCALE
    dy = ypos.delta * SCALE
    l = not lmb.value
    r = not rmb.value
    mouse.report[0] = (
        mouse.MIDDLE_BUTTON if (l and r) else
        mouse.LEFT_BUTTON if l else
        mouse.RIGHT_BUTTON if r else
        0)

    if dx or dy:
        mouse.move(dx, dy)
    else:
        mouse._send_no_move() # pylint: disable=protected-access
