# SPDX-FileCopyrightText: 2023 Jeff Epler for Adafruit Industries
# SPDX-License-Identifier: MIT
import board
from adafruit_led_animation.animation.chase import Chase
from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.animation.rainbow import Rainbow
from adafruit_led_animation.color import (JADE, RED, WHITE)
from adafruit_led_animation.group import AnimationGroup
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_neopxl8 import NeoPxl8
from adafruit_pixelmap import PixelMap

strand_length = 30
pixel_brightness = 0.8
num_strands = 8

num_pixels = num_strands * strand_length
pixels = NeoPxl8(board.NEOPIXEL0, num_pixels, auto_write=False, brightness=pixel_brightness)

def strand(n):
    return PixelMap(
        pixels,
        tuple(range(n * strand_length, (n + 1) * strand_length)),
        individual_pixels=True,
    )

pixel_strip_A = strand(0)
pixel_strip_B = strand(1)
pixel_strip_C = strand(2)
pixel_strip_D = strand(3)
pixel_strip_E = strand(4)
pixel_strip_F = strand(5)
pixel_strip_G = strand(6)
pixel_strip_H = strand(7)

animations = AnimationSequence(
    AnimationGroup(
        Rainbow(pixel_strip_A, speed=0.01, period=7),
        Rainbow(pixel_strip_B, speed=0.01, period=7),
        Rainbow(pixel_strip_C, speed=0.01, period=7),
        Rainbow(pixel_strip_D, speed=0.01, period=7),
        Rainbow(pixel_strip_E, speed=0.01, period=7),
        Rainbow(pixel_strip_F, speed=0.01, period=7),
        Rainbow(pixel_strip_G, speed=0.01, period=7),
        Rainbow(pixel_strip_H, speed=0.01, period=7),
    ),
    AnimationGroup(
        Chase(pixel_strip_A, speed=0.05, color=WHITE, spacing=5, size=8),
        Chase(pixel_strip_B, speed=0.05, color=RED, spacing=4, size=4),
        Chase(pixel_strip_C, speed=0.05, color=RED, spacing=4, size=8),
        Chase(pixel_strip_D, speed=0.05, color=JADE, spacing=5, size=5),
        Chase(pixel_strip_E, speed=0.05, color=WHITE, spacing=5, size=5),
        Chase(pixel_strip_F, speed=0.05, color=RED, spacing=4, size=5),
        Chase(pixel_strip_G, speed=0.05, color=JADE, spacing=3, size=4),
        Chase(pixel_strip_H, speed=0.05, color=RED, spacing=4, size=8),
        sync=False,
    ),
    AnimationGroup(
        Comet(pixel_strip_A, 0.01, color=WHITE, tail_length=12, bounce=True),
        Comet(pixel_strip_B, 0.01, color=RED, tail_length=12, reverse=True),
        Comet(pixel_strip_C, 0.01, color=RED, tail_length=12, bounce=True),
        Comet(pixel_strip_D, 0.01, color=JADE, tail_length=12, reverse=True),
        Comet(pixel_strip_E, 0.01, color=WHITE, tail_length=12, bounce=True),
        Comet(pixel_strip_F, 0.01, color=RED, tail_length=12, reverse=True),
        Comet(pixel_strip_G, 0.01, color=JADE, tail_length=12, bounce=True),
        Comet(pixel_strip_H, 0.01, color=RED, tail_length=12, reverse=True),
        sync=True,
    ),
    advance_interval=9,
    auto_clear=True,
)

while True:
    animations.animate()
