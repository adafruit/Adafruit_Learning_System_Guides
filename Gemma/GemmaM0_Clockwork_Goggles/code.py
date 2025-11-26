# SPDX-FileCopyrightText: 2017 John Edgar Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# CircuitPython Gemma Gear goggles
# uses two 16 NeoPixel rings (RGBW)
# connected to Gemma M0 powered by LiPo battery

import time

import board
import neopixel

pixpinLeft = board.D1  # Data In attached to Gemma pin D1
pixpinRight = board.D0  # Data In attached to Gemma pin D0
numpix = 16

# uncomment the lines below for RGB NeoPixels
stripLeft = neopixel.NeoPixel(pixpinLeft, numpix, bpp=3, brightness=.18,
                              auto_write=False)
stripRight = neopixel.NeoPixel(pixpinRight, numpix, bpp=3, brightness=.18,
                               auto_write=False)


# Use these lines for RGBW NeoPixels
# stripLeft = neopixel.NeoPixel(pixpinLeft, numpix, bpp=4, brightness=.18,
#    auto_write=False)
# stripRight = neopixel.NeoPixel(pixpinRight, numpix, bpp=4, brightness=.18,
#    auto_write=False)


def cog(pos):
    # Input a value 0 to 255 to get a color value.
    # Note: switch the commented lines below if using RGB vs. RGBW NeoPixles
    if (pos < 8) or (pos > 250):
        # return (120, 0, 0, 0) #first color, red: for RGBW NeoPixels
        return (120, 0, 0)  # first color, red: for RGB NeoPixels
    if pos < 85:
        return (int(pos * 3), int(255 - (pos * 3)), 0)
        # return (125, 35, 0, 0) #second color, brass: for RGBW NeoPixels
        # return (125, 35, 0)  # second color, brass: for RGB NeoPixels
    elif pos < 170:
        pos -= 85
        # return (int(255 - pos*3), 0, int(pos*3), 0)#: for RGBW NeoPixels
        return (int(255 - pos * 3), 0, int(pos * 3))  # : for RGB NeoPixels
    else:
        pos -= 170
        # return (0, int(pos*3), int(255 - pos*3), 0)#: for RGBW NeoPixels
        return (0, int(pos * 3), int(255 - pos * 3))  # : for RGB NeoPixels


def brass_cycle(wait, patternL, patternR):
    # patterns do different things, try:
    # 1 blink
    # 24 chase w pause
    # 64 chase
    # 96 parial chase
    # 128 half turn
    # 230 quarter turn w blink
    # 256 quarter turn
    for j in range(255):
        for i in range(len(stripLeft)):
            idxL = int((i * patternL / len(stripLeft)) + j)
            stripLeft[i] = cog(idxL & 64)  # sets the second (brass) color
            idxR = int((i * patternR / len(stripRight)) + j)
            stripRight[i] = cog(idxR & 64)  # sets the second (brass) color
        stripLeft.show()
        stripRight.show()
        time.sleep(wait)


while True:
    brass_cycle(0.01, 256, 24)  # brass color cycle with 1ms delay per step
    # patternL, patternR
