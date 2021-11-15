# SPDX-FileCopyrightText: 2021 Ruiz Brothers for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import neopixel
from adafruit_led_animation.animation.pulse import Pulse
from adafruit_led_animation.animation.rainbow import Rainbow
from adafruit_led_animation.animation.rainbowsparkle import RainbowSparkle
from adafruit_led_animation.animation.rainbowcomet import RainbowComet
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation.color import PURPLE

# Update this to match the number of NeoPixel LEDs connected to your board.
num_pixels = 124

pixels = neopixel.NeoPixel(board.GP1, num_pixels, auto_write=True)
pixels.brightness = 0.2

rainbow = Rainbow(pixels, speed=0.01, period=1)
rainbow_sparkle = RainbowSparkle(pixels, speed=0.05, num_sparkles=15)
rainbow_comet = RainbowComet(pixels, speed=.01, tail_length=20, bounce=True)
pulse = Pulse(pixels, speed=.05, color=PURPLE, period=3)

animations = AnimationSequence(
    pulse,
    rainbow_sparkle,
    rainbow_comet,
    rainbow,
    advance_interval=5,
    auto_clear=True,
    random_order=False
)

while True:
    animations.animate()
