# SPDX-FileCopyrightText: 2019 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Import all pins
import time
import board
import busio
from adafruit_ht16k33 import matrix

# Create the I2C interface
i2c = busio.I2C(board.SCL, board.SDA)

# Create the LED bargraph class.
bicolor = matrix.Matrix8x8x2(i2c)

# color mapping shortcut
OFF = 0
GREEN = 1
RED = 2
YELLOW = 3

# Set individual segments of the bicolor matrix
# Illuminate the first three pixels
bicolor[0,0] = GREEN
bicolor[0,1] = RED
bicolor[0,2] = YELLOW

time.sleep(2)

# Edges of an 8x8 matrix
col_max = 8
row_max = 8

# Turn all pixels off
bicolor.fill(OFF)
col = 0
row = 0

# Illuminate each pixel with each color
while row < row_max:

    # Turn them on in a loop
    while col < col_max:
        bicolor[row, col] = RED
        time.sleep(.25)
        bicolor[row, col] = GREEN
        time.sleep(.25)
        bicolor[row, col] = YELLOW
        time.sleep(.25)
        col += 1

    # next row when previous column is full
    if row < row_max:
        row += 1
        col = 0

    # clear matrix, start over
    else:
        row = col = 0
        bicolor.fill(OFF)

time.sleep(1)

# Fill the entrire display, with each color
bicolor.fill(GREEN)
time.sleep(1)
bicolor.fill(RED)
time.sleep(1)
bicolor.fill(YELLOW)
time.sleep(1)
bicolor.fill(OFF)
