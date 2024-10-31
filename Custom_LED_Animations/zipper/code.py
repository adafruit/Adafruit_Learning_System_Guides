# SPDX-FileCopyrightText: 2024 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import board
import neopixel

from zipper import ZipperAnimation

from adafruit_led_animation.color import PINK, JADE

# Update to match the pin connected to your NeoPixels
pixel_pin = board.D10
# Update to match the number of NeoPixels you have connected
pixel_num = 32

# initialize the neopixels. Change out for dotstars if needed.
pixels = neopixel.NeoPixel(pixel_pin, pixel_num, brightness=0.02, auto_write=False)

# initialize the animation
zipper = ZipperAnimation(pixels, speed=0.1, color=PINK, alternate_color=JADE)

while True:
    # call animation to show the next animation frame
    zipper.animate()
