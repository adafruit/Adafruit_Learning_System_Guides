# SPDX-FileCopyrightText: 2019 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Gemma M0 Onchip Temperature Sensor
# Project by Kathy Ceceri
# CircuitPython by Anne Barela
# Adafruit Industries, 2019

import time
import board
import microcontroller
import neopixel
import adafruit_dotstar

ROOM_TEMP = 65.0  # Set this to the temp to change from blue to red (F)

# Set up NeoPixel strand
pixels = neopixel.NeoPixel(board.D1,  # NeoPixels on pin D1
                           4,         # Number of Pixels
                           brightness=0.2)   # Change from 0.0 to 1.0

# For the Gemma M0 onboard DotStar LED
dotstar = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)

def deg_f(deg_c):  # Convert celsius to Fahrenheit
    return(deg_c * 9 / 5) + 32.0

while True:
    temp = deg_f(microcontroller.cpu.temperature)
    if temp > ROOM_TEMP:
        pixels.fill((255, 0, 0))   # (255,0,0) is red
        dotstar.fill((255, 0, 0))  # Set to red
    else:
        pixels.fill((0, 0, 255))   # (0,0,255) is blue
        dotstar.fill((0, 0, 255))  # Set to blue

    time.sleep(1.0)  # Wait 1 second
