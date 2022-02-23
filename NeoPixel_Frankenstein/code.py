# SPDX-FileCopyrightText: 2020 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import touchio
import neopixel
from adafruit_led_animation.animation.pulse import Pulse
from adafruit_led_animation.color import (
    RED,
    YELLOW,
    ORANGE,
    GREEN,
    TEAL,
    CYAN,
    BLUE,
    PURPLE,
    MAGENTA,
    GOLD,
    PINK,
    AQUA,
    JADE,
    AMBER
)

#  NeoPixel pin
pixel_pin = board.A3
#  number of NeoPixels
pixel_num = 68

#  NeoPixels setup
pixels = neopixel.NeoPixel(pixel_pin, pixel_num, brightness=0.5, auto_write=False)

#  animation setup
pulse = Pulse(pixels, speed=0.1, color=RED, period=5)

#  two cap touch pins
touch_left = board.A1
touch_right = board.A2

#  cap touch setup
bolt_left = touchio.TouchIn(touch_left)
bolt_right = touchio.TouchIn(touch_right)

#  NeoPixel colors for animation
colors = [RED, YELLOW, ORANGE, GREEN, TEAL, CYAN, BLUE,
          PURPLE, MAGENTA, GOLD, PINK, AQUA, JADE, AMBER]

#  variable for color array index
c = 0

#  debounce states for cap touch
bolt_left_state = False
bolt_right_state = False

while True:
    #  run animation
    pulse.animate()

    #  debounce for cap touch
    if not bolt_left.value and not bolt_left_state:
        bolt_left_state = True
    if not bolt_right.value and not bolt_right_state:
        bolt_right_state = True

    #  if the left bolt is touched...
    if bolt_left.value and bolt_left_state:
        print("Touched left bolt!")
        #  increase color array index by 1
        c += 1
        #  reset debounce state
        bolt_left_state = False
    #  if the right bolt is touched...
    if bolt_right.value and bolt_right_state:
        print("Touched right bolt!")
        #  decrease color array index by 1
        c -= 1
        #  reset debounce state
        bolt_right_state = False
    #  if the color array index is bigger than 13...
    if c > 13:
        #  reset it to 0
        c = 0
    #  if the color array index is smaller than 0...
    if c < 0:
        #  reset it to 13
        c = 13
    #  update animation color to current array index
    pulse.color = colors[c]
    time.sleep(0.01)
