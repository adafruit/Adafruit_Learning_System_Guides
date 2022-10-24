# SPDX-FileCopyrightText: 2022 Noe Ruiz for Adafruit Industries
# SPDX-License-Identifier: MIT
# Werewolf and Moon Neon Sign
import board
import neopixel
from adafruit_led_animation.animation.blink import Blink
from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.animation.pulse import Pulse
from adafruit_led_animation.group import AnimationGroup
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation import color

moon_leds = neopixel.NeoPixel(board.SDA, 60, brightness=0.8,
    auto_write=False, pixel_order=neopixel.RGB)
wolf_leds = neopixel.NeoPixel(board.SCL, 57, brightness=0.8,
    auto_write=False, pixel_order=neopixel.RGB)

animations = AnimationSequence(
    Blink(wolf_leds, speed=0.07, color=color.BLUE),
    Pulse(wolf_leds, speed=0.01, color=color.PURPLE, period=3),
    AnimationGroup(
        Pulse(wolf_leds, speed=0.01, color=color.PURPLE, period=3),
        Comet(moon_leds, speed=0.01, color=color.AMBER, tail_length=60, reverse=True),
        sync=True,
    ),
    AnimationGroup(
        Pulse(wolf_leds, speed=0.01, color=color.PURPLE, period=3),
        Pulse(moon_leds, speed=0.01, color=color.AMBER, period=3),
        sync=True,
    ),
    AnimationGroup(
        Pulse(wolf_leds, speed=0.01, color=color.PURPLE, period=3),
        Pulse(moon_leds, speed=0.01, color=color.AMBER, period=3),
        sync=True,
    ),
    advance_interval=2.0,
    auto_clear=True,
    auto_reset=True,
)

while True:
    animations.animate()
