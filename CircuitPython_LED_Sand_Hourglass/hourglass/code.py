# SPDX-FileCopyrightText: 2020 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import adafruit_lsm6ds.lsm6ds33
from adafruit_ht16k33 import matrix
import matrixsand

DELAY = 0.05 # overall update rate

# setup i2c
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller

# the accelo
accelo = adafruit_lsm6ds.lsm6ds33.LSM6DS33(i2c)

# the matrices
m1 = matrix.Matrix8x8(i2c, 0x70)
m2 = matrix.Matrix8x8(i2c, 0x71)

# the sand
sand1 = matrixsand.MatrixSand(8, 8)
sand2 = matrixsand.MatrixSand(8, 8)

# simple helper
def update_matrix(m, s):
    for x in range(8):
        for y in range(8):
            m[x,y] = s[x,y]

# fill up some sand
for sx in range(8):
    for sy in range(8):
        sand1[sx, sy] = True
sand1[0,0] = sand1[0,1] = sand1[1,0] = False
sand1[0,2] = sand1[1,1] = sand1[2,0] = False

update_matrix(m1, sand1)
update_matrix(m2, sand2)

updated1 = updated2 = False

while True:
    # read accelo
    ax, ay, az = accelo.acceleration
    # rotate coords
    xx = -ax - ay
    yy = -ax + ay
    zz = az

    # move grain of sand from upper to lower?
    if yy > 0 and sand1[7,7] and not sand2[0,0] and not updated2:
        sand1[7,7] = False
        sand2[0,0] = True
        updated1 = updated2 = True
    # move grain of sand from lower to upper?
    elif yy <= 0 and sand2[0,0] and not sand1[7,7] and not updated1:
        sand2[0,0] = False
        sand1[7,7] = True
        updated1 = updated2 = True
    # nope, just a regular update
    else:
        updated1 = sand1.iterate((xx, yy, zz))
        updated2 = sand2.iterate((xx, yy, zz))

    # update matrices if needed
    if updated1:
        update_matrix(m1, sand1)
    if updated2:
        update_matrix(m2, sand2)

    time.sleep(DELAY)
