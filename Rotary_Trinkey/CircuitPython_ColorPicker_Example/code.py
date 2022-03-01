# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Rotary Trinkey NeoPixel color picker example"""
import rotaryio
import digitalio
import board
from rainbowio import colorwheel
import neopixel

print("Rotary Trinkey color picker example")

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.5)
encoder = rotaryio.IncrementalEncoder(board.ROTA, board.ROTB)
switch = digitalio.DigitalInOut(board.SWITCH)
switch.switch_to_input(pull=digitalio.Pull.DOWN)

last_position = -1
color = 0  # start at red
while True:
    position = encoder.position
    if last_position is None or position != last_position:
        print(position)
        if not switch.value:
            # change the color
            if position > last_position:  # increase
                color += 1
            else:
                color -= 1
            color = (color + 256) % 256  # wrap around to 0-256
            pixel.fill(colorwheel(color))
        else:
            # change the brightness
            if position > last_position:  # increase
                pixel.brightness = min(1.0, pixel.brightness + 0.1)
            else:
                pixel.brightness = max(0, pixel.brightness - 0.1)
    last_position = position
