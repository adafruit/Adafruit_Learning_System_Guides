"""
CircuitPython DotStar rainbow example - multiple DotStars.

This example is meant for boards that have multiple built-in DotStar LEDs.

** Update NUMBER_OF_PIXELS to the match the number of built-in DotStars on the board. It is found
in THREE places in the code.

For example:
If you are using a FunHouse, change NUMBER_OF_PIXELS to 5.

** Update PIXELBUF_VERSION to _pixelbuf if available for the board (this is the most common case!)
or to adafruit_pypixelbuf where necessary (typically non-Express SAMD21 M0 boards).

For example:
If you are using a FunHouse, change PIXELBUF_VERSION to _pixelbuf.
If you are using a Trinket M0, change PIXELBUF_VERSION to adafruit_pypixelbuf.

** DO NOT INCLUDE THE pylint: disable LINE IN THE GUIDE CODE. It is present only to deal with the
NUMBER_OF_PIXELS variable being undefined, and the dots setup line being too long with the variable
in it in this pseudo-code. As you will be updating the variable in the guide, you will not need
the pylint: disable.
"""
# pylint: disable=undefined-variable, line-too-long

import time
import board
import adafruit_dotstar
from PIXELBUF_VERSION import colorwheel

dots = adafruit_dotstar.DotStar(board.DOTSTAR_CLOCK, board.DOTSTAR_DATA, NUMBER_OF_PIXELS, auto_write=False)
dots.brightness = 0.3


def rainbow(delay):
    for color_value in range(255):
        for led in range(NUMBER_OF_PIXELS):
            pixel_index = (led * 256 // NUMBER_OF_PIXELS) + color_value
            dots[led] = colorwheel(pixel_index & 255)
        dots.show()
        time.sleep(delay)


while True:
    rainbow(0.01)
