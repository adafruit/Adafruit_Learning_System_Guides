# SPDX-FileCopyrightText: 2018 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

from digitalio import DigitalInOut, Pull, Direction
import board
import neopixel

# NeoPixel setup and blank out
pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=1)
pixels.fill((0, 0, 0))

# button setup: A, B, and slide switch
button_a = DigitalInOut(board.BUTTON_A)
button_a.direction = Direction.INPUT
button_a.pull = Pull.DOWN

button_b = DigitalInOut(board.BUTTON_B)
button_b.direction = Direction.INPUT
button_b.pull = Pull.DOWN

switch = DigitalInOut(board.SLIDE_SWITCH)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

# main program - light NeoPixels depending on switches
while True:
    if button_a.value:
        pixels[0] = (0, 30, 0)
    else:
        pixels[0] = (0, 0, 0)

    if button_b.value:
        pixels[9] = (0, 30, 0)
    else:
        pixels[9] = (0, 0, 0)

    if switch.value:
        pixels[4] = (0, 0, 30)
        pixels[5] = (0, 0, 0)
    else:
        pixels[4] = (0, 0, 0)
        pixels[5] = (0, 0, 30)
