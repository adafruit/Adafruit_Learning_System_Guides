# SPDX-FileCopyrightText: 2020 Noe Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import neopixel
import adafruit_dotstar

LED = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1) #Setup Internal Dotar
LED.brightness = 0.8 #DotStar brightness

NUMPIX = 7        # Number of NeoPixels
PIXPIN = board.D2  # Pin where NeoPixels are connected
PIXELS = neopixel.NeoPixel(PIXPIN, NUMPIX) # NeoPixel object setup

RED = 7 #Number of pixels to be red
BLUE = 0 #First pixel

while True:  # Loop forever...
    #Make the internal dotstar light up.
    LED[0] = (100, 0, 255)

    #Select these pixels starting with the second pixel.
    for i in range(1, RED):
        # Make the pixels red
        PIXELS[i] = (100, 0, 0)

    #Make the first neopixel this color
    PIXELS[BLUE] = (0, 0, 100)
