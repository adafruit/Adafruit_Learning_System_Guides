# SPDX-FileCopyrightText: 2022 Noe Ruiz for Adafruit Industries
# SPDX-License-Identifier: MIT
# Grim Reaper and Moon Neon Sign
import board
import neopixel
from adafruit_led_animation.animation.chase import Chase
from adafruit_led_animation.animation.pulse import Pulse
from adafruit_led_animation.group import AnimationGroup
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation import color

knife_leds = neopixel.NeoPixel(board.SDA, 48, brightness=0.8, auto_write=False, pixel_order=neopixel.RGB)
repear_leds = neopixel.NeoPixel(board.SCL, 60, brightness=0.8, auto_write=False, pixel_order=neopixel.RGB)

animations = AnimationSequence(

    AnimationGroup(
        Chase(knife_leds, speed=0.02, color=color.PURPLE, spacing=12, size=40),
        Pulse(repear_leds, speed=0.01, color=color.GREEN, period=3),
        sync=True,
    ),
    advance_interval=8.0,
    auto_clear=True,
    auto_reset=True,
)

while True:
    animations.animate()
