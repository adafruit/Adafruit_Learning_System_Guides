# SPDX-FileCopyrightText: 2020 Erin St Blaine for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Crystal Gem Light Strand Project By Erin St Blaine for Adafruit Industries
https://learn.adafruit.com/no-solder-papercraft-crystal-light-strand

Circuit Playground Bluetooth with LED strand attached runs 4 different variable animation modes.

Code by Rose Hooper using Adafruit's LED Animation Library:
 https://learn.adafruit.com/circuitpython-led-animations/overview
"""
# pylint: disable=attribute-defined-outside-init

#Import libraries
import board
import neopixel
from rainbowio import colorwheel
from adafruit_circuitplayground import cp
from adafruit_led_animation.animation.solid import Solid
from adafruit_led_animation.animation import Animation
from adafruit_led_animation.animation.rainbow import Rainbow
from adafruit_led_animation.animation.sparkle import Sparkle
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation.color import WHITE

speeds = (0.25, 0.125, 0.1, 0.08, 0.05, 0.02, 0.01)  # Customize speed levels here
# periods = (7, 6, 5, 4, 3, 2, 1)

class RainbowFade(Animation):

    _color_index = 0
    def __init__(self, pixel_object, speed, name):
        super().__init__(pixel_object, speed=speed, color=WHITE, name=name)

    def draw(self):
        self.color = colorwheel(self._color_index)
        self._color_index = (self._color_index + 1) % 256
        self.fill(self.color)


current_speed = 4

# Set your number of pixels here
pixel_num = 20

pixel_pin = board.A1
pixels = neopixel.NeoPixel(pixel_pin, pixel_num, brightness=1, auto_write=False)

# Animation Setup

rainbow = Rainbow(pixels, speed=speeds[current_speed], period=2, name="rainbow", step=3)
sparkle = Sparkle(pixels, speed=speeds[current_speed], color=WHITE, name="sparkle")
rainbowfade = RainbowFade(pixels, speed=speeds[current_speed], name="rainbowfade")
solid = Solid(pixels, color=colorwheel(0), name="solid")

# Animation Sequence Playlist -- rearrange to change the order of animations

animations = AnimationSequence(
    rainbow,
    rainbowfade,
    solid,
    sparkle,
    auto_clear=True,
    auto_reset=True,
)

solid.speed = 0.01
solid_color = 0

while True:
    if cp.switch:  # if slide switch is in the "on" position, run animations
        animations.animate()  #play animation sequence
        if cp.button_a:
            animations.next()
            while cp.button_a:
                continue

        if cp.button_b:
            if animations.current_animation.name == "solid":
                solid_color = (solid_color + 8) % 256
                animations.current_animation.color = colorwheel(solid_color)
            else:
                current_speed += 1
                if current_speed >= len(speeds):
                    current_speed = 0
                rainbow.speed = speeds[current_speed]
                sparkle.speed = speeds[current_speed]
                rainbowfade.speed = speeds[current_speed]
                print(speeds[current_speed])
            while cp.button_b:
                continue
    else:  # If slide switch is in the "off" position, set pixels to black
        pixels.fill(0)
        pixels.show()
