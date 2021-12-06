# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: Unlicense
"""CircuitPython Digital Input example - Blinking a built-in NeoPixel LED using a button switch.

Update BUTTON_PIN to the pin to which you have connected the button (in the case of an external
button), or to the pin connected to the built-in button (in the case of boards with built-in
buttons).

For example:
If you connected a button switch to D1, change BUTTON_PIN to D1.
If using a QT Py RP2040, to use button A, change BUTTON_PIN to BUTTON.
"""
import board
import digitalio
import neopixel

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)

button = digitalio.DigitalInOut(board.BUTTON_PIN)
button.switch_to_input(pull=digitalio.Pull.UP)

while True:
    if not button.value:
        pixel.fill((255, 0, 0))
    else:
        pixel.fill((0, 0, 0))
