# CircuitPlaygroundExpress_LightSensor
# reads the on-board light sensor and graphs the brightness with NeoPixels

import time

import board
import neopixel
from analogio import AnalogIn
from simpleio import map_range

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, auto_write=0, brightness=.05)
pixels.fill((0, 0, 0))
pixels.show()

analogin = AnalogIn(board.LIGHT)

while True:
    # light value remapped to pixel position
    peak = map_range(analogin.value, 2000, 62000, 0, 9)
    print(analogin.value)
    print(int(peak))

    for i in range(0, 9, 1):
        if i <= peak:
            pixels[i] = (0, 255, 0)
        else:
            pixels[i] = (0, 0, 0)
    pixels.show()

    time.sleep(0.01)
