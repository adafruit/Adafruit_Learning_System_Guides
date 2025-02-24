# SPDX-FileCopyrightText: 2020 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Bright Wearables Purse Slideshow with FancyLED
# Anne Barela for Adafruit Industries, February 2020
# MIT License

import board
import adafruit_dotstar as dotstar
from adafruit_clue import clue
from adafruit_slideshow import SlideShow, PlayBackDirection
import adafruit_fancyled.adafruit_fancyled as fancy

# Set the LED ring speed and brightness
LED_SPEED = 0.2   # pick a number from 0 (no motion) to 1.0 (fastest!)
BRIGHTNESS = 0.2  # pick a number from 0 (dark) to 1.0 (bright!)

# colors available are RED, YELLOW, ORANGE, GREEN, TEAL
# CYAN, BLUE, PURPLE, MAGENTA, WHITE, BLACK, GOLD, PINK
# AQUA, JADE, AMBER, VIOLET, SKY - pick any color set!
# 3 to 5 colors looks best...
palette = [clue.PINK, clue.GOLD, clue.JADE]

# For the Bright Wearables DotStar LED Ring
num_leds = 12
pixels = dotstar.DotStar(board.P13, board.P15, num_leds, auto_write=False)
offset = 0

# Create the BMP displayer
slideshow = SlideShow(clue.display, None, folder="/",
                      auto_advance=False)

# turn palette to fancytype
for i, color in enumerate(palette):
    palette[i] = fancy.CRGB(*[x / 255 for x in color])

while True:
    if clue.button_b:
        slideshow.direction = PlayBackDirection.FORWARD
        slideshow.advance()
    if clue.button_a:
        slideshow.direction = PlayBackDirection.BACKWARD
        slideshow.advance()

    # spin the LEDs
    for i in range(num_leds):
        # Load each pixel's color from the palette using an offset, run it
        # through the gamma function, pack RGB value and assign to pixel.
        color = fancy.palette_lookup(palette, offset + i / num_leds)
        color = fancy.gamma_adjust(color, brightness=BRIGHTNESS)
        pixels[i] = color.pack()
    pixels.show()
    offset += LED_SPEED / 10
