"""
Circuit Playground Express Compass

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

import time
import math
import sys
import board
import busio
import adafruit_lsm303
import neopixel
import digitalio

BLACK = 0x000000
RED = 0xFF0000
GREEN = 0x00FF00
BLUE = 0x0000FF

i2c = busio.I2C(board.SCL, board.SDA)
compass = adafruit_lsm303.LSM303(i2c)
compass.mag_rate = adafruit_lsm303.MAGRATE_30
#compass.mag_gain = adafruit_lsm303.MAGGAIN_8_1

calibrate_button = digitalio.DigitalInOut(board.BUTTON_A)
calibrate_button.direction = digitalio.Direction.INPUT
calibrate_button.pull = digitalio.Pull.UP


#-------------------------------------------------------------------------------
# Replace these two lines with the results of calibration
#-------------------------------------------------------------------------------
raw_mins = [1000.0, 1000.0]
raw_maxes = [-1000.0, -1000.0]
#-------------------------------------------------------------------------------


mins = [0.0, 0.0]
maxes = [0.0, 0.0]
corrections = [0.0, 0.0]

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=.2, auto_write=False)

led_patterns =  [[4, 5], [5], [6], [7], [8], [9], [9, 0], [0], [1], [2], [3], [4]]


def fill(colour):
    pixels.fill(colour)
    pixels.show()


def warm_up():
    fill(BLUE)
    for _ in range(100):
        _, _, _ = compass.magnetic
        time.sleep(0.010)


def calibrate(do_the_readings):
    values = [0.0, 0.0]
    start_time = time.monotonic()

    fill(GREEN)

    # Update the high and low extremes
    if do_the_readings:
        while time.monotonic() - start_time < 10.0:
            values[0], values[1], _ = compass.magnetic
            values[1] *= -1                           # accel is upside down, so y is reversed
            if values[0] != 0.0 and values[1] != 0.0: # ignore the random 0 values
                for i in range(2):
                    if values[i] < raw_mins[i]:
                        raw_mins[i] = values[i]
                    if values[i] > raw_maxes[i]:
                        raw_maxes[i] = values[i]
#            time.sleep(0.005)

    # Recompute the correction and the correct mins/maxes
    for i in range(2):
        corrections[i] = (raw_maxes[i] + raw_mins[i]) / 2
        mins[i] = raw_mins[i] - corrections[i]
        maxes[i] = raw_maxes[i] - corrections[i]

    fill(BLACK)


def normalize(value, in_min, in_max):
    mapped = (value - in_min) * 200 / (in_max - in_min) + -100
    return max(min(mapped, 100), -100)



# Setup

warm_up()

if not calibrate_button.value or (raw_mins[0] == 1000.0 and raw_mins[1] == 1000.0):
    print("Compass calibration")
    raw_mins[0] = 1000.0
    raw_mins[1] = 1000.0
    raw_maxes[0] = -1000.0
    raw_maxes[1] = -1000.0
    calibrate(True)


    print("Calibration results")
    print("Update the corresponding lines near the top of the code\n")
    print("raw_mins = [{0}, {1}]".format(raw_mins[0], raw_mins[1]))
    print("raw_maxes = [{0}, {1}]".format(raw_maxes[0], raw_maxes[1]))
    sys.exit()
else:
    calibrate(False)


while True:
    if not calibrate_button.value:
        calibrate(True)

    x, y, _ = compass.magnetic
    y = y * -1

    if x != 0.0 and y != 0.0:
        normalized_x = normalize(x - corrections[0], mins[0], maxes[0])
        normalized_y = normalize(y - corrections[1], mins[1], maxes[1])

        compass_heading = int(math.atan2(normalized_y, normalized_x) * 180.0 / math.pi)
        # compass_heading is between -180 and +180 since atan2 returns -pi to +pi
        # this translates it to be between 0 and 360
        compass_heading += 180

        direction_index = ((compass_heading + 15) % 360) // 30

        pixels.fill(BLACK)
        for l in led_patterns[direction_index]:
            pixels[l] = RED
        pixels.show()
        time.sleep(0.050)
