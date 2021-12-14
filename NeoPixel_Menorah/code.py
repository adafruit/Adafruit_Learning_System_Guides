# SPDX-FileCopyrightText: 2021 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import neopixel
from digitalio import DigitalInOut, Direction, Pull
from adafruit_led_animation.animation.rainbow import Rainbow
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation import helper
from adafruit_led_animation.color import AMBER

#  button setup
button = DigitalInOut(board.D1)
button.direction = Direction.INPUT
button.pull = Pull.UP

#  neopixel setup
pixel_pin = board.D0
pixel_num = 9

pixels = neopixel.NeoPixel(pixel_pin, pixel_num, brightness=0.3, auto_write=False)

#  variable for number of pixels in the pixelmap helper
num = 1

#  pixel map helper
#  allows you to light each candle up one by one
#  begins with one being lit (num)
candles = helper.PixelMap.horizontal_lines(
    pixels, num, 1, helper.horizontal_strip_gridmap(pixel_num, alternating=False)
)

#  rainbow animation
rainbow = Rainbow(candles, speed=0.1, period=5)

animations = AnimationSequence(rainbow)

#  turn on center candle
pixels[4] = AMBER
pixels.show()

while True:

    #  if only one candle is lit, don't rewrite center neopixel
    if num == 1:
        pass
    #  otherwise write data to center neopixel
    else:
        pixels[4] = AMBER
        pixels.show()
    #  animation the rainbow animation
    animations.animate()

    #  if you press the button...
    if not button.value:
        #  if all of the candles are not lit up yet...
        if num < 9:
            #  increase value of num by one
            num += 1
        #  skip the center candle so that it stays amber
        if num == 4:
            num = 5
        #  recreate the pixel helper to increase the size of the horizontal grid
        #  this is how the next neopixel is lit up in the sequence
        candles = helper.PixelMap.horizontal_lines(
            pixels, num, 1, helper.horizontal_strip_gridmap(pixel_num, alternating=False)
        )
        rainbow = Rainbow(candles, speed=0.1, period=5)
        animations = AnimationSequence(rainbow)
        #  quick delay so that everything flows well
        time.sleep(0.5)
