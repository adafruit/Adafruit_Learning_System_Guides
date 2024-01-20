# SPDX-FileCopyrightText: 2021 Phil Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# modified from original
# 2024 Carter Nelson

"""
Modifed from original project code here:
https://learn.adafruit.com/adafruit-eyelights-led-glasses-and-driver/bmp-animation

This version only uses the matrix part of the glasses. The ring
LEDs are not used. BMP image files should be properly formatted
for the matrix (18x5 sprites) and placed in the /images folder.

Current animation can be changed by tilting head back. Brightness
can be changed by pressing the user button.
"""

import os
import time
import board
from busio import I2C
import digitalio
import adafruit_lis3dh
import adafruit_is31fl3741
from adafruit_is31fl3741.adafruit_ledglasses import LED_Glasses
from eyelights_anim import EyeLightsAnim

# --| User Config |------------------------------
ANIM_DELAY = 0.07
BRIGHT_LEVELS = (0, 10, 20, 40)
# --| User Config |------------------------------

# use all BMPs found in /images dir
ANIM_FILES = [
    "/images/" + f
    for f in os.listdir("/images")
    if f.endswith(".bmp") and not f.startswith("._")
]

# HARDWARE SETUP -----------------------

i2c = I2C(board.SCL, board.SDA, frequency=1000000)

lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c)

button = digitalio.DigitalInOut(board.SWITCH)
button.switch_to_input(digitalio.Pull.UP)

# Initialize the IS31 LED driver, buffered for smoother animation
glasses = LED_Glasses(i2c, allocate=adafruit_is31fl3741.MUST_BUFFER)
glasses.show()  # Clear any residue on startup
glasses.global_current = 20  # Just middlin' bright, please


# ANIMATION SETUP ----------------------

# Two indexed-color BMP filenames are specified: first is for the LED matrix
# portion, second is for the LED rings -- or pass None for one or the other
# if not animating that part. The two elements, matrix and rings, share a
# few LEDs in common...by default the rings appear "on top" of the matrix,
# or you can optionally pass a third argument of False to have the rings
# underneath. There's that one odd unaligned pixel between the two though,
# so this may only rarely be desirable.
anim = EyeLightsAnim(glasses, ANIM_FILES[0], None)

# MAIN LOOP ----------------------------

# This example just runs through a repeating cycle. If you need something
# else, like ping-pong animation, or frames based on a specific time, the
# anim.frame() function can optionally accept two arguments: an index for
# the matrix animation, and an index for the rings.

_, filtered_y, _ = lis3dh.acceleration
looking_up = filtered_y < -5
anim_index = 0
bright_index = 0

while True:
    # read accelo and check if looking up
    _, y, _ = lis3dh.acceleration
    filtered_y = filtered_y * 0.85 + y * 0.15
    if looking_up:
        if filtered_y > -3.5:
            looking_up = False
    else:
        if filtered_y < -5:
            looking_up = True
            anim_index = (anim_index + 1) % len(ANIM_FILES)
            print(ANIM_FILES[anim_index])
            anim.matrix_filename = ANIM_FILES[anim_index]

    # check for button press
    if not button.value:
        bright_index = (bright_index + 1) % len(BRIGHT_LEVELS)
        print(BRIGHT_LEVELS[bright_index])
        glasses.global_current = BRIGHT_LEVELS[bright_index]
        while not button.value:
            pass

    anim.frame()  #     Advance matrix and rings by 1 frame and wrap around
    glasses.show()  #   Update LED matrix
    time.sleep(ANIM_DELAY)  # Pause briefly
