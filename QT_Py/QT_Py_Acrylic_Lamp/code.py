# SPDX-FileCopyrightText: 2021 Ruiz Bros for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
This example displays three chase animations in sequence.
"""
import board
import neopixel
from adafruit_led_animation.animation.chase import Chase
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation.color import (
    RED,
    GREEN,
    BLUE
)

# Update to match the pin connected to your NeoPixels
pixel_pin = board.D0
# Update to match the number of NeoPixels you have connected
pixel_num = 8

pixels = neopixel.NeoPixel(pixel_pin, pixel_num, brightness=0.8, auto_write=False)

RedChase = Chase(pixels, speed=0.4, color=RED, size=1, spacing=8, reverse=True)
GreenChase = Chase(pixels, speed=0.4, color=GREEN, size=1, spacing=8, reverse=True)
BlueChase = Chase(pixels, speed=0.4, color=BLUE, size=1, spacing=8, reverse=True)

animations = AnimationSequence(
    RedChase,
    GreenChase,
    BlueChase,
    advance_interval=4,
    auto_clear=True,
)

while True:
    animations.animate()
