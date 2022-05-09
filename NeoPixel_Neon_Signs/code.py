# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT

import board
import neopixel

from adafruit_led_animation.animation.rainbow import Rainbow
from adafruit_led_animation.animation.rainbowchase import RainbowChase
from adafruit_led_animation.animation.rainbowcomet import RainbowComet
from adafruit_led_animation.sequence import AnimationSequence

# Update to match the pin connected to your NeoPixels
pixel_pin = board.A0
# Update to match the number of NeoPixels you have connected
pixel_num = 96

pixels = neopixel.NeoPixel(pixel_pin, pixel_num, brightness=0.8, auto_write=False)

rainbow = Rainbow(pixels, speed=0.1, period=5)
rainbow_chase = RainbowChase(pixels, speed=0.03, size=24, spacing=4)
rainbow_comet = RainbowComet(pixels, speed=0.01, tail_length=50, bounce=True)

animations = AnimationSequence(
    rainbow,
    rainbow_comet,
    rainbow_chase,
    advance_interval=5,
    auto_clear=True,
)

while True:
    animations.animate()
