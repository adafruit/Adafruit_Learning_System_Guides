# SPDX-FileCopyrightText: 2021 Noe Ruiz for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
NeoPixel Menorah using QT Py RP2040.
"""
import board
import neopixel
from adafruit_led_animation.animation.pulse import Pulse
from adafruit_led_animation.animation.solid import Solid
from adafruit_led_animation.animation.sparkle import Sparkle
from adafruit_led_animation.animation.chase import Chase
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation.color import AMBER

# Update to match the pin connected to your NeoPixels
pixel_pin = board.D0
# Update to match the number of NeoPixels you have connected
pixel_num = 9

pixels = neopixel.NeoPixel(pixel_pin, pixel_num, brightness=1, auto_write=False)

solid = Solid(pixels, color=AMBER)
pulse = Pulse(pixels, speed=0.05, color=AMBER, period=5)
sparkle = Sparkle(pixels, speed=0.15, color=AMBER, num_sparkles=10)
chase = Chase(pixels, speed=0.1, color=AMBER, size=1, spacing=8)

from adafruit_led_animation.animation.solid import Solid

animations = AnimationSequence(
    chase,
    pulse,
    sparkle,
    solid,
    advance_interval=5,
    auto_clear=True,
)

while True:
    animations.animate()

