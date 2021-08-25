# Basic example of using the Bi-color 24 segment bargraph display.
# This example and library is meant to work with Adafruit CircuitPython API.
# Author: Carter Nelson
# License: Public Domain

import time
import board
import busio

# Import the Bicolor24 driver from the HT16K33 module
from adafruit_ht16k33.bargraph import Bicolor24

# Create the I2C interface
i2c = busio.I2C(board.SCL, board.SDA)

# Create the LED bargraph class.
bc24 = Bicolor24(i2c)

# Set individual segments of bargraph
bc24[0] = bc24.LED_RED
bc24[1] = bc24.LED_GREEN
bc24[2] = bc24.LED_YELLOW

time.sleep(2)

# Turn them all off
bc24.fill(bc24.LED_OFF)

# Turn them on in a loop
for i in range(24):
    bc24[i] = bc24.LED_RED
    time.sleep(0.1)
    bc24[i] = bc24.LED_OFF

time.sleep(1)

# Fill the entrire bargraph
bc24.fill(bc24.LED_GREEN)
