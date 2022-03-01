# SPDX-FileCopyrightText: 2020 Noe Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import neopixel
from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.animation.pulse import Pulse
from adafruit_led_animation.animation.blink import Blink
from adafruit_led_animation.animation.rainbow import Rainbow
from adafruit_led_animation.animation.colorcycle import ColorCycle
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation import helper
from adafruit_led_animation.color import PURPLE, AQUA, RED, JADE, ORANGE, YELLOW, BLUE

#Setup NeoPixels
pixel_pin = board.D6
pixel_num = 16
pixels = neopixel.NeoPixel(pixel_pin, pixel_num, brightness=.9, auto_write=False)

#Setup NeoPixel Grid
pixel_wing_vertical = helper.PixelMap.vertical_lines(
    pixels, 8, 2, helper.horizontal_strip_gridmap(8, alternating=True)
)
pixel_wing_horizontal = helper.PixelMap.horizontal_lines(
    pixels, 8, 2, helper.horizontal_strip_gridmap(8, alternating=True)
)

#Setup LED Animations
rainbow = Rainbow(pixels, speed=.001, period=2)
pulse = Pulse(pixels, speed=0.1, color=RED, period=3)
blink = Blink(pixels, speed=0.5, color=RED)
colorcycle = ColorCycle(pixels, speed=0.4, colors=[RED, ORANGE, YELLOW, JADE, BLUE, AQUA, PURPLE])
comet_v = Comet(pixel_wing_vertical, speed=0.05, color=PURPLE, tail_length=6, bounce=True)

#Setup the LED Sequences
animations = AnimationSequence(
    rainbow,
    pulse,
    comet_v,
    blink,
    colorcycle,
    advance_interval=5.95,
)

#Run ze animations!
while True:
    animations.animate()
