# SPDX-FileCopyrightText: 2022 Kattni Rembor for Adafruit Industries
# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Digital Input Example - Blinking an LED using the built-in button.
"""
import board
import digitalio

led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

button = digitalio.DigitalInOut(board.BUTTON1)
button.switch_to_input(pull=digitalio.Pull.UP)

while True:
    if not button.value:
        led.value = False
    else:
        led.value = True
