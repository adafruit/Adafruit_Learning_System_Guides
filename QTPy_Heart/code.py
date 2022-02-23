# SPDX-FileCopyrightText: 2021 Noe Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import neopixel
from adafruit_led_animation.animation.pulse import Pulse
from adafruit_led_animation.color import RED

# Update to match the pin connected to your NeoPixels
pixel_pin = board.D1
# Update to match the number of NeoPixels you have connected
pixel_num = 6

pixels = neopixel.NeoPixel(pixel_pin, pixel_num, brightness=0.5, auto_write=False)

pulse = Pulse(pixels, speed=0.01, color=RED, period=1)

while True:
    pulse.animate()
