# SPDX-FileCopyrightText: 2021 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

"""Jack-o'-Lantern flame example Adafruit Circuit Playground Express"""
import time
import math
import random
import board
import adafruit_ws2801
from digitalio import DigitalInOut, Direction, Pull

#  button setup
button = DigitalInOut(board.A2)
button.direction = Direction.INPUT
button.pull = Pull.UP

# pixel setup
pixel_num = 9
pixel_offset = 2
pixels = adafruit_ws2801.WS2801(board.SDA1, board.SCL1, pixel_num+pixel_offset, brightness=1, auto_write=False)

pixel_prev = [128] * len(pixels)

lit_candles = None
night = 1

def split(first, second, offset):
    """
    Subdivide a brightness range, introducing a random offset in middle,
    then call recursively with smaller offsets along the way.
    @param1 first:  Initial brightness value.
    @param1 second: Ending brightness value.
    @param1 offset: Midpoint offset range is +/- this amount max.
    """
    if offset != 0:
        mid = ((first + second + 1) / 2 + random.randint(-offset, offset))
        offset = int(offset / 2)
        split(first, mid, offset)
        split(mid, second, offset)
    else:
        level = math.pow(first / 255.0, 2.7) * 255.0 + 0.5
        return level

while True:
    if not button.value:
        while not button.value:
            time.sleep(0.01) # debounce
        night += 1 # next night
        if night == 9: # wrap around
            night = 1
        lit_candles = None # reset the lights
    if not lit_candles:
        print("Current night: ", night)
        lit_candles = [True] * night + [False] * (8-night)
        lit_candles.insert(4, True) # shamash always on
        print(lit_candles)

    # animate candles
    for p in range(len(pixels)-pixel_offset):
        if not lit_candles[p]:
            pixels[p+pixel_offset] = 0
            continue
        if p == 4:
            level = random.randint(128, 255)
        else:
            level = random.randint(64, 191)

        color = split(pixel_prev[p], level, 32)
        pixels[p+pixel_offset] = ((int(level), int(level / 8), int(level / 48)))
        pixel_prev[p] = level
    pixels.show()
