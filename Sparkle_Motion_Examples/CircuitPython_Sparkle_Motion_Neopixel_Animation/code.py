# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Example illustrating two different LED Animations running on
Neopixels connected to 2 of the main outputs of the Sparkle Motion
"""
import board
import neopixel

from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.animation.rainbow import Rainbow
from adafruit_led_animation.color import GREEN

strip1_pixel_pin = board.D21
strip2_pixel_pin = board.D22

pixel_count = 8

strip1_pixels = neopixel.NeoPixel(
    strip1_pixel_pin, pixel_count, brightness=0.1, auto_write=False
)
strip2_pixels = neopixel.NeoPixel(
    strip2_pixel_pin, pixel_count, brightness=0.1, auto_write=False
)

comet = Comet(strip1_pixels, speed=0.05, color=GREEN, tail_length=3, bounce=True)
rainbow = Rainbow(strip2_pixels, speed=0.05, period=3)

while True:
    comet.animate()
    rainbow.animate()
