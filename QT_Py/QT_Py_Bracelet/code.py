# SPDX-FileCopyrightText: 2020 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Demo code to generate an alternating color-gradient effect in
# the QT Py LED cuff bracelet LEDs.
import time
import board
from rainbowio import colorwheel
import neopixel

# Total number of LEDs on both strips
NUM_PIXELS = 14

pixels = neopixel.NeoPixel(board.MOSI, NUM_PIXELS, pixel_order=neopixel.GRB, auto_write=False, brightness = 0.4
)

    
# Scales a tuple by a fraction of 255
def scale(tup, frac):
    return tuple((x*frac)//255 for x in tup)

# Sawtooth function with amplitude and period of 255
def sawtooth(x):
    return int(2*(127.5 - abs((x % 255) - 127.5)))

# Hue value at the opposite side of the color colorwheel
def oppositeHue(x):
    return ((x + 128) % 256)

hueIndex = 0         # determines hue value (0->255)
brightnessIndex = 0  # input to the sawtooth function for determining brightness (0->255)
brightnessSpeed = 3  # bigger value = faster shifts in brightness

while True:
    bright = sawtooth(brightnessIndex)
    
    # get RGB color from colorwheel function and scale it by the brightness
    mainColor = scale(colorwheel(hueIndex),bright)
    oppColor = scale(colorwheel(oppositeHue(hueIndex)), 255 - bright)

    # hue and brightness alternate along each strip
    for i in range(NUM_PIXELS//2):
        pixels[i*2] = mainColor
        pixels[i*2 + 1] = oppColor
    pixels.show()
    
    # increment hue and brightness
    hueIndex = (hueIndex + 1) % 255        
    brightnessIndex = (brightnessIndex + brightnessSpeed) % 255
