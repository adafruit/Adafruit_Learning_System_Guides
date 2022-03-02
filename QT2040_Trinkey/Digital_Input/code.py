# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""CircuitPython Digital Input Example for QT2040 Trinkey"""
import board
import digitalio
import neopixel

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)

button = digitalio.DigitalInOut(board.BUTTON)
button.switch_to_input(pull=digitalio.Pull.UP)

while True:
    if not button.value:
        pixel.fill((255, 0, 0))
    else:
        pixel.fill((0, 0, 0))
