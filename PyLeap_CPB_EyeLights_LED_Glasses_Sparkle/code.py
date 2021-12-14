# SPDX-FileCopyrightText: 2021 Rose Hooper
# SPDX-License-Identifier: MIT

import board
from adafruit_led_animation.animation.sparkle import Sparkle
from adafruit_led_animation.color import PURPLE
from adafruit_led_animation.sequence import AnimationSequence

from adafruit_is31fl3741.adafruit_ledglasses import MUST_BUFFER, LED_Glasses
from adafruit_is31fl3741.led_glasses_animation import LED_Glasses_Animation

glasses = LED_Glasses(board.I2C(), allocate=MUST_BUFFER)
glasses.set_led_scaling(255)
glasses.global_current = 0xFE
glasses.enable = True

pixels = LED_Glasses_Animation(glasses)


anim2 = Sparkle(pixels, 0.05, PURPLE)

group = AnimationSequence(
    anim2, advance_interval=5, auto_reset=True, auto_clear=True
)
while True:
    group.animate()
