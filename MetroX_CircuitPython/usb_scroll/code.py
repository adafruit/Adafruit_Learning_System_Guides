# SPDX-FileCopyrightText: 2021 Brent Rubell for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
'usb_scroll.py'.

=================================================
control a NeoPixel using an (NEC) IR Remote
requires:
- adafruit_hid
- simpleio
"""
import time
import analogio
import board
import digitalio
from adafruit_hid import mouse
from simpleio import map_range

button = digitalio.DigitalInOut(board.D6)
pot = analogio.AnalogIn(board.A0)

m = mouse.Mouse()

while True:
    if not button.value:  # move while button is pressed
        m.move(0, 0, int(map_range(pot.value, 50, 65520, -5, 5)))
        time.sleep(0.08)
