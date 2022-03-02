# SPDX-FileCopyrightText: 2018 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

#  Designed specifically to work with the MLX90614 sensors in the
#  adafruit shop
#  ----> https://www.adafruit.com/product/1747
#  ----> https://www.adafruit.com/product/1748
#
#  These sensors use I2C to communicate, 2 pins are required to
#  interface Adafruit invests time and resources providing this open
#  source code,
#  please support Adafruit and open-source hardware by purchasing
#  products from Adafruit!

import time
import board
import busio as io
import neopixel
import adafruit_mlx90614

# the mlx90614 must be run at 100k [normal speed]
# i2c default mode is is 400k [full speed]
# the mlx90614 will not appear at the default 400k speed
i2c = io.I2C(board.SCL, board.SDA, frequency=100000)
mlx = adafruit_mlx90614.MLX90614(i2c)

# neopixel setup
num_leds = 24           # how many LEDs
led_pin = board.D1      # which pin the neopixel ring is connected to
strip = neopixel.NeoPixel(led_pin, num_leds, brightness=1)

# change these to adjust the range of temperatures you want to measure
# (these are in Farenheit)
cold_temp = 60
hot_temp = 80

def remapRange(value, leftMin, leftMax, rightMin, rightMax):
    # this remaps a value from original (left) range to new (right) range
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin

    # Convert the left range into a 0-1 range (int)
    valueScaled = int(value - leftMin) / int(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return int(rightMin + (valueScaled * rightSpan))

# Fill the dots one after the other with a color
def colorWipe(color):
    for j in range(len(strip)):
        strip[j] = (color)

while True:
    # get object temperature in celsius
    temp = mlx.object_temperature

    # convert object temperature to fahrenheit
    temp = (temp * 9/5) + 32

    if temp < cold_temp:
        temp = cold_temp

    if temp > hot_temp:
        temp = hot_temp

    # map temperature to red/blue color
    # hotter temp -> more red
    red = remapRange(temp, cold_temp, hot_temp, 0, 255)
    # hotter temp -> less blue
    blue = remapRange(temp, cold_temp, hot_temp, 255, 0)

    colorWipe((red, 0, blue))

    # can adjust this for faster/slower updates
    time.sleep(.05)
