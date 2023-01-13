# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Basic IoT Button with NeoPixel BFF Example"""
import time
import board
from digitalio import DigitalInOut, Direction, Pull
from rainbowio import colorwheel
import neopixel

# setup onboard NeoPixel
pixel_pin = board.A3
num_pixels = 1

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.3, auto_write=False)

# setup onboard button
switch = DigitalInOut(board.A2)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

# rainbow cycle function
def rainbow_cycle(wait):
    for j in range(255):
        for i in range(num_pixels):
            rc_index = (i * 256 // num_pixels) + j
            pixels[i] = colorwheel(rc_index & 255)
        pixels.show()
        time.sleep(wait)

while True:
    # run rainbow cycle animation
    rainbow_cycle(0)

    # if the button is not pressed..
    if switch.value:
        # neopixel brightness is zero and appears to be "off"
        pixels.brightness = 0
    # if the button is pressed..
    else:
        # neopixel brightness is 0.3 and rainbow animation is visible
        pixels.brightness = 0.3
