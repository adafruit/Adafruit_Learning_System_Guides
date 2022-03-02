# SPDX-FileCopyrightText: 2019 Erin St Blaine for Adafruit Industries
#
# SPDX-License-Identifier: MIT

""" Simple FancyLED example for NeoPixel strip
"""

import board
import neopixel
import adafruit_fancyled.adafruit_fancyled as fancy

num_leds = 17

# Declare a Water Colors palette
palette = [fancy.CRGB(0, 214, 214), # blues and cyans
           fancy.CRGB(0, 92, 160),
           fancy.CRGB(0, 123, 255),
           fancy.CRGB(0, 68, 214)]

# Declare a Fire Colors palette
#palette = [fancy.CRGB(0, 0, 0),       # Black
#             fancy.CHSV(1.0),           # Red
#              fancy.CRGB(1.0, 1.0, 0.0), # Yellow
#              0xFFFFFF]                  # White

# Declare a NeoPixel object on pin D6 with num_leds pixels, no auto-write.
# Set brightness to max because we'll be using FancyLED's brightness control.
pixels = neopixel.NeoPixel(board.D1, num_leds, brightness=1.0,
                           auto_write=False)

offset = 0  # Positional offset into color palette to get it to 'spin'

while True:
    for i in range(num_leds):
        # Load each pixel's color from the palette using an offset, run it
        # through the gamma function, pack RGB value and assign to pixel.
        color = fancy.palette_lookup(palette, offset + i / num_leds)
        color = fancy.gamma_adjust(color, brightness=0.25)
        pixels[i] = color.pack()
    pixels.show()

    offset += 0.02  # Bigger number = faster spin
