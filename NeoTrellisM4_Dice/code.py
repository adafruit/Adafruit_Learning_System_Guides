"""
Dice roller for the NeoTrellisM4

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

# pylint: disable=global-statement

import math
import time
import random
import board
import adafruit_trellism4
import adafruit_adxl34x
import busio

# Set up the trellis and accelerometer

trellis = adafruit_trellism4.TrellisM4Express()

i2c = busio.I2C(board.ACCELEROMETER_SCL, board.ACCELEROMETER_SDA)
accelerometer = adafruit_adxl34x.ADXL345(i2c)


# a 3-wide, 4-tall fonts for 0-9
# Each string is a row with a space being unlit, and anything else being lit.

number_patterns = [
    [" * ", "* *", "* *", "***"],         # 0
    [" * ", "** ", " * ", "***"],         # 1
    ["** ", "  *", " * ", "***"],         # 2
    ["** ", "  *", " **", "***"],         # 3
    ["* *", "* *", "***", "  *"],         # 4
    ["***", "*  ", " **", "***"],         # 5
    [" **", "*  ", "***", "***"],         # 6
    ["***", "  *", " * ", " * "],         # 7
    [" * ", "* *", "***", "***"],         # 8
    [" * " ,"* *", " **", "  *"]          # 9
]

sides_per_die = [4, 6, 8, 10, 12, 20]
die_colors = [
    (255, 0, 0),                          # d4
    (0, 255, 0),                          # d6
    (0, 0, 255),                          # d8
    (255, 255, 0),                        # d10
    (0, 255, 255),                        # d12
    (255, 0, 255)]                        # d20

def display_digit(number, offset, color, force_zero):
    """Display a digit.
    number     -- the number (0-9) to display
    offset     -- the left-most column of the displayed digit
    color      -- the RGB color to use to display the digit
    force_zero -- whether to leave a 0 blank (False) or display it
    """
    bits = number_patterns[number]
    for row in range(4):
        for col in range(3):
            if bits[row][col] == " " or (number == 0 and not force_zero):
                trellis.pixels[col + offset, row] = (0, 0, 0)
            else:
                trellis.pixels[col + offset, row] = color


def display_number(number, color):
    """Display a multi-digit number.
    If the number is > 99, the hundreds digit (1-4) is indicated on the far left column:
        100 is the top pixel, 400 is the bottom.
    number      -- the number to display
    color       -- the RGB color to use to display the digit
    force_zeros -- whether to leave a 0 in the tens place blank (False) or display it
    """
    if number >= 500 or number < 0:
        return False
    display_digit(number % 10, 5, color, True)
    display_digit((number // 10) % 10, 1, color, number >= 100)
    hundreds = number // 100
    for h in range(4):
        if h + 1 == hundreds:
            trellis.pixels[0, h] = (255, 255, 255)
        else:
            trellis.pixels[0, h] = (0, 0, 0)
    return True


def animate_to(number, color):
    """Perform an animation (displaying random numbers) before displaying the requested number.
    number -- the number to eventually display
    color  -- the color to use (indicates the type of dice used)
    """
    for _ in range(10):
        trellis.pixels.fill((0, 0, 0))
        display_number(random.randint(10, 99), color)
        time.sleep(0.1)
    trellis.pixels.fill((0, 0, 0))
    display_number(number, color)


def roll(number, sides):
    """Generate a random dice roll.
    Returns the total of the roll.
    number -- the number of dice to roll
    sides  -- the number of side on dice to roll (4, 6, 8, 10, 12, 20)
    """
    total = 0
    for _ in range(number):
        total += random.randint(1, sides + 1)
    return total


previous_reading = [None, None, None]
bound = 4.0

def shaken():
    """Detect when the Trellis is shaken.
    See http://www.profoundlogic.com/docs/display/PUI/Accelerometer+Test+for+Shaking
    TL;DR one or more axis experiences a significant (set by bound) change very quickly
    Returns whether a shake was detected.
    """
    global previous_reading
    result = False
    x, y, z = accelerometer.acceleration
    if previous_reading[0] is not None:
        result = (math.fabs(previous_reading[0] - x) > bound and
                  math.fabs(previous_reading[1] - y) > bound and
                  math.fabs(previous_reading[2] - z) > bound)
    previous_reading = (x, y, z)
    return result


selected_count = -1
selected_die = -1

while True:
    trellis.pixels.fill((0, 0, 0))
    previous_reading = accelerometer.acceleration
    while not shaken():
        # update selected count/die if a respective selection has been made
        pressed = trellis.pressed_keys    # Get the pressed buttons
        count_selector = [key for key in pressed if key[1] == 0]   # first row presses
        die_selector = [key for key in pressed if key[1] == 1]     # second row presses
        if len(count_selector) > 0:
            selected_count = count_selector[0][0] + 1
        if len(die_selector) > 0 and die_selector[0][0] < 6:   # only 6 types of dice
            selected_die = die_selector[0][0]

        # update the pixels to reflect the selections
        for i in range(8):
            if i < selected_count:        # Display a bar for the count
                trellis.pixels[i, 0] = (128, 64, 16)
            else:
                trellis.pixels[i, 0] = (0, 0, 0)
            if i == selected_die:         # Just the selected dice, in the appropriate color
                trellis.pixels[i, 1] = die_colors[selected_die]
            else:
                trellis.pixels[i, 1] = (0, 0, 0)

    # Only do the roll if both count and die have been selected
    if (selected_count > -1) and (selected_die > -1):
        animate_to(roll(selected_count, sides_per_die[selected_die]), die_colors[selected_die])
        timeout = time.monotonic() + 5.0
        while len(trellis.pressed_keys) == 0 and time.monotonic() < timeout:
            pass
