# SPDX-FileCopyrightText: 2022 Noe Ruiz for Adafruit Industries
# SPDX-License-Identifier: MIT
# Ghost with Glasses Neon Sign
import board
import neopixel
from adafruit_led_animation.animation.blink import Blink
from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.animation.chase import Chase
from adafruit_led_animation.animation.pulse import Pulse
from adafruit_led_animation.group import AnimationGroup
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation import color

ghost_pixels = neopixel.NeoPixel(board.SDA, 90, brightness=0.5, auto_write=False, pixel_order=neopixel.RGB)
glasses_pixels = neopixel.NeoPixel(board.SCL, 33, brightness=0.5, auto_write=False, pixel_order=neopixel.RGB)

animations = AnimationSequence(
    # Synchronized animations
    AnimationGroup(
        Chase(ghost_pixels,speed=0.02, color=color.CYAN, size=40, spacing=5),
        Blink(glasses_pixels, speed=.4, color=color.PURPLE),
        sync=False,
    ),

    # Sequential animations
    Pulse(glasses_pixels, speed=0.01, color=color.WHITE, period=2),

    # Synchronized
    AnimationGroup(
        Pulse(glasses_pixels, speed=0.01, color=color.PURPLE, period=1),
        Comet(ghost_pixels, speed=0.01, color=color.CYAN, tail_length=50, bounce=False),
        sync=True,
    ),

    advance_interval=4.0,
    auto_clear=True,
    auto_reset=True,
)

while True:
    animations.animate()
