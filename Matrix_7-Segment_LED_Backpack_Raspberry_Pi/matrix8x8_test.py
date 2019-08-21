# Import all board pins.
import time
import board
import busio
from adafruit_ht16k33 import matrix

# Create the I2C interface.
i2c = busio.I2C(board.SCL, board.SDA)

# creates a 8x8 matrix:
matrix = matrix.Matrix8x8(i2c)

# edges of an 8x8 matrix
col_max = 8
row_max = 8

# Clear the matrix.
matrix.fill(0)
col = 0
row = 0

while True:

    # illuminate a column one LED at a time
    while col < col_max:
        matrix[row, col] = 1
        col += 1
        time.sleep(.2)

    # next row when previous column is full
    if row < row_max:
        row += 1
        col = 0

    # clear matrix, start over
    else:
        row = col = 0
        matrix.fill(0)
