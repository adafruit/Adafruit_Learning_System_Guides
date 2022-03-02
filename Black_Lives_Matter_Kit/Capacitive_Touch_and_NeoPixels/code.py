# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import touchio
import digitalio
import neopixel
from rainbowio import colorwheel

pixels = neopixel.NeoPixel(board.NEOPIXEL, 6, auto_write=False)
red_led = digitalio.DigitalInOut(board.D13)
red_led.direction = digitalio.Direction.OUTPUT
cap1 = touchio.TouchIn(board.CAP1)
cap2 = touchio.TouchIn(board.CAP2)
cap3 = touchio.TouchIn(board.CAP3)
cap4 = touchio.TouchIn(board.CAP4)

pixels.fill((255, 0, 0))
pixels.show()
mode = 0
touched_4 = False
color_value = 1
while True:
    if cap1.value and mode == 0:
        # Touch pad 1 to increase the brightness.
        pixels.brightness += 0.05
        pixels.show()
        time.sleep(0.15)
    if cap2.value and mode == 0:
        # Touch pad 2 to decrease the brightness.
        pixels.brightness -= 0.05
        pixels.show()
        time.sleep(0.15)
    if cap3.value and mode == 0:
        # Touch pad 3 to cycle through a rainbow of colors on the NeoPixels.
        color_value = (color_value + 1) % 255
        pixels.fill(colorwheel(color_value))
        pixels.show()
    if cap4.value and not touched_4:
        # Touch pad 4 to "disable" the other pads.
        mode += 1
        if mode > 1:
            mode = 0
        touched_4 = True
        time.sleep(0.05)
    if not cap4.value and touched_4:
        # This prevents pad 4 from spamming mode changes.
        touched_4 = False
        time.sleep(0.05)
    if mode == 0:
        # The little red LED is off when pads 1-3 are "enabled".
        red_led.value = False
    if mode == 1:
        # The little red LED is on when pads 1-3 are "disabled".
        red_led.value = True
