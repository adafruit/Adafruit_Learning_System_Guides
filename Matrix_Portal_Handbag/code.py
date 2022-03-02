# SPDX-FileCopyrightText: 2020 Melissa LeBlanc-Williams for Adafruit Industries
# SPDX-FileCopyrightText: 2020 Erin St Blaine for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Slideshow Example using the Matrix Portal and 64 x 32 LED matrix display
Written by Melissa LeBlanc-Williams and Erin St Blaine for Adafruit Industries
Images smaller than 64 pixel width will be aligned alternating left or right
Press Up button to pause/resume Slideshow
Press Down button to cycle between slideshow folders
"""
import time
import board
import adafruit_lis3dh
import displayio
import busio
from digitalio import DigitalInOut, Pull
from adafruit_matrixportal.matrix import Matrix
from adafruit_slideshow import SlideShow, HorizontalAlignment
from adafruit_debouncer import Debouncer

'''
Display will go to sleep after SLEEP_DURATION seconds have elapsed with no accelerometer movement
Each slide will play for IMAGE_DURATION - customizable for each folder
Add folders to the list to add more slideshows.
'''

SLEEP_DURATION = 60
IMAGE_DURATION = (1, 0.5, 10)
IMAGE_FOLDER = (
    "/bmps",
    "/bmps2",
    "/bmps3",
)
# pylint: disable=invalid-name
# --- Display setup ---
matrix = Matrix(bit_depth=6)
display = matrix.display
ACCEL = adafruit_lis3dh.LIS3DH_I2C(busio.I2C(board.SCL, board.SDA),
                                   address=0x19)
_ = ACCEL.acceleration # Dummy reading to blow out any startup residue

pin_down = DigitalInOut(board.BUTTON_DOWN)
pin_down.switch_to_input(pull=Pull.UP)
button_down = Debouncer(pin_down)
pin_up = DigitalInOut(board.BUTTON_UP)
pin_up.switch_to_input(pull=Pull.UP)
button_up = Debouncer(pin_up)

ALIGN_RIGHT = True
auto_advance = True

i = 0
NUM_FOLDERS = 2 #first folder is numbered 0

slideshow = SlideShow(
    display,
    None,
    folder=IMAGE_FOLDER[i],
    order=0,
    auto_advance=False,
    fade_effect=False,
    dwell=IMAGE_DURATION[i],
    h_align=HorizontalAlignment.RIGHT,
)

LAST_ADVANCE = time.monotonic()
last_movement = time.monotonic()
MODE = 1

def advance():
    ''' go to the next slide '''
    # pylint: disable=global-statement
    global ALIGN_RIGHT, LAST_ADVANCE
    ALIGN_RIGHT = not ALIGN_RIGHT
    if ALIGN_RIGHT:
        slideshow.h_align = HorizontalAlignment.RIGHT
    else:
        slideshow.h_align = HorizontalAlignment.LEFT
    LAST_ADVANCE = time.monotonic()
    slideshow.advance()

empty_group = displayio.Group()

while True:
    if ACCEL.shake(shake_threshold=10):
        print("Moving!")
        if MODE == 0:
            slideshow = SlideShow(
                display,
                None,
                folder=IMAGE_FOLDER[i],
                order=0,
                auto_advance=False,
                fade_effect=False,
                dwell=IMAGE_DURATION[i],
                h_align=HorizontalAlignment.RIGHT,
            )
        last_movement = time.monotonic()
        MODE = 1
    elif time.monotonic() > last_movement + SLEEP_DURATION:
        MODE = 0
        display.show(empty_group)
    if MODE == 1:
        if auto_advance and time.monotonic() > LAST_ADVANCE + IMAGE_DURATION[i]:
            advance()
        button_down.update()
        button_up.update()
        if button_up.fell:
            auto_advance = not auto_advance
        if button_down.fell:
            i = i + 1
            if i > NUM_FOLDERS:
                i = 0
            slideshow = SlideShow(
                display,
                None,
                folder=IMAGE_FOLDER[i],
                order=0,
                auto_advance=False,
                fade_effect=False,
                dwell=IMAGE_DURATION[i],
                h_align=HorizontalAlignment.RIGHT,
            )
