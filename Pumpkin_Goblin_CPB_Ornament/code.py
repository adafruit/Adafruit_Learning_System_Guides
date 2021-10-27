# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
This example shows different ways to use AnimationGroup: syncing four animations across two separate
pixel objects such as the built-in NeoPixels on a Circuit Playground Bluefruit and a 16x NeoPixel Ring.

This example is written for Circuit Playground Bluefruit and a 16-pixel NeoPixel ring connected to
pad A1. It does not work on Circuit Playground Express.
"""
import board
import neopixel
from adafruit_circuitplayground import cp

from adafruit_led_animation.animation.blink import Blink
from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.animation.chase import Chase
from adafruit_led_animation.animation.pulse import Pulse
from adafruit_led_animation.animation.sparkle import Sparkle

from adafruit_led_animation.group import AnimationGroup
from adafruit_led_animation.sequence import AnimationSequence

import adafruit_led_animation.color as color

strip_pixels = neopixel.NeoPixel(board.A1, 16, brightness=0.5, auto_write=False)
cp.pixels.brightness = 0.5

animations = AnimationSequence(
    # Synchronized to 0.5 seconds. Ignores the second animation setting of 3 seconds.
    AnimationGroup(
        Sparkle(cp.pixels, 0.1, color.GREEN, num_sparkles=1),
        Sparkle(strip_pixels, 0.1, color.GREEN, num_sparkles=1),
    ),
    AnimationGroup(
        Blink(cp.pixels, 0.25, color.RED),
        Blink(strip_pixels, 0.25, color.RED),
        sync=True,
    ),
    # Different speeds
    AnimationGroup(
        Comet(cp.pixels, 0.05, color.GREEN, tail_length=5),
        Comet(strip_pixels, 0.05, color.GREEN, tail_length=5),
    ),
    AnimationGroup(
        Pulse(cp.pixels, 0.05, color.RED, period=3),
        Pulse(strip_pixels, 0.05, color.RED, period=3),
    ),
    advance_interval=4.0,
    auto_clear=True,
    auto_reset=True,
)

while True:
    animations.animate()
