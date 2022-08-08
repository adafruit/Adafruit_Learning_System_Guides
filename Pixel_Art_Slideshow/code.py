# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Slideshow Example using the Matrix Portal and 64 x 32 LED matrix display
Written by Melissa LeBlanc-Williams for Adafruit Industries
Images smaller than 64 pixel width will be aligned alternating left or right
Press Up button to pause/resume Slideshow
Press Down button to advance
"""
import time
import board
from digitalio import DigitalInOut, Pull
from adafruit_matrixportal.matrix import Matrix
from adafruit_slideshow import SlideShow, PlayBackDirection, HorizontalAlignment
from adafruit_debouncer import Debouncer

IMAGE_DURATION = 3
IMAGE_FOLDER = "/bmps"

# --- Display setup ---
matrix = Matrix(bit_depth=6)
display = matrix.display

pin_down = DigitalInOut(board.BUTTON_DOWN)
pin_down.switch_to_input(pull=Pull.UP)
button_down = Debouncer(pin_down)
pin_up = DigitalInOut(board.BUTTON_UP)
pin_up.switch_to_input(pull=Pull.UP)
button_up = Debouncer(pin_up)

align_right = True
auto_advance = True

slideshow = SlideShow(
    display,
    None,
    folder=IMAGE_FOLDER,
    order=0,
    auto_advance=False,
    fade_effect=False,
    dwell=IMAGE_DURATION,
    h_align=HorizontalAlignment.RIGHT,
)
last_advance = time.monotonic()


def advance():
    # pylint: disable=global-statement
    global align_right, last_advance
    align_right = not align_right
    if align_right:
        slideshow.h_align = HorizontalAlignment.RIGHT
    else:
        slideshow.h_align = HorizontalAlignment.LEFT
    last_advance = time.monotonic()
    slideshow.advance()


while True:
    if auto_advance and time.monotonic() > last_advance + IMAGE_DURATION:
        advance()
    button_down.update()
    button_up.update()
    if button_up.fell:
        auto_advance = not auto_advance
    if button_down.fell:
        slideshow.direction = PlayBackDirection.FORWARD
        advance()
