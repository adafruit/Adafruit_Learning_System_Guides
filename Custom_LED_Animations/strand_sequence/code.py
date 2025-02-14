# SPDX-FileCopyrightText: 2024 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import board

import neopixel
from adafruit_led_animation.color import PINK, JADE
from adafruit_led_animation.sequence import AnimationSequence

from rainbowsweep import RainbowSweepAnimation
from sweep import SweepAnimation
from zipper import ZipperAnimation

# Update to match the pin connected to your NeoPixels
pixel_pin = board.A1
# Update to match the number of NeoPixels you have connected
pixel_num = 30

# initialize the neopixels. Change out for dotstars if needed.
pixels = neopixel.NeoPixel(pixel_pin, pixel_num, brightness=0.02, auto_write=False)

# initialize the animations
sweep = SweepAnimation(pixels, speed=0.05, color=PINK)

zipper = ZipperAnimation(pixels, speed=0.1, color=PINK, alternate_color=JADE)

rainbowsweep = RainbowSweepAnimation(pixels, speed=0.05, color=0x000000, sweep_speed=0.1,
                                     sweep_direction=RainbowSweepAnimation.DIRECTION_END_TO_START)

# sequence to play them all one after another
animations = AnimationSequence(
    sweep, zipper, rainbowsweep, advance_interval=6, auto_clear=True
)

while True:
    animations.animate()
