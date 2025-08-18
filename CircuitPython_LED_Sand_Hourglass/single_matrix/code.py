# SPDX-FileCopyrightText: 2020 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import adafruit_lsm6ds.lsm6ds33
from adafruit_ht16k33 import matrix
import matrixsand

DELAY = 0.00 # add some delay if you want

# setup i2c
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller

# check for LSM6DS33 or LSM6DS3TR-C (Adafruit Feather Sense)
try:
    from adafruit_lsm6ds.lsm6ds33 import LSM6DS33 as LSM6DS
    lsm6ds = LSM6DS(i2c)
except RuntimeError:
    from adafruit_lsm6ds.lsm6ds3 import LSM6DS3 as LSM6DS
    lsm6ds = LSM6DS(i2c)

# the matrix
matrix = matrix.Matrix8x8(i2c, 0x70)

# the sand
sand = matrixsand.MatrixSand(8, 8)

# simple helper
def update_matrix():
    for x in range(8):
        for y in range(8):
            matrix[x,y] = sand[x,y]

# add some initial sand
for sx in range(4):
    for sy in range(4):
        sand[sx, sy] = 1
update_matrix()

# loop forever
while True:
    # read accelo
    ax, ay, az = accelo.acceleration

    # rotate coord sys
    xx = ay
    yy = ax
    zz = az

    # iterate the sand
    updated = sand.iterate((xx, yy, zz))

    # update matrix if needed
    if updated:
        update_matrix()

    # sleep
    time.sleep(DELAY)
