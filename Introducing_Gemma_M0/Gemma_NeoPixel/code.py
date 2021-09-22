# CircuitPython demo - NeoPixel

import time
from rainbowio import colorwheel
import board
import neopixel

pixpin = board.D1
numpix = 10

strip = neopixel.NeoPixel(pixpin, numpix, brightness=0.3, auto_write=False)


def rainbow_cycle(wait):
    for j in range(255):
        for i in range(len(strip)):
            idx = int((i * 256 / len(strip)) + j)
            strip[i] = colorwheel(idx & 255)
        strip.write()
        time.sleep(wait)


while True:
    strip.fill((255, 0, 0))
    strip.write()
    time.sleep(1)

    strip.fill((0, 255, 0))
    strip.write()
    time.sleep(1)

    strip.fill((0, 0, 255))
    strip.write()
    time.sleep(1)

    rainbow_cycle(0.001)  # rainbowcycle with 1ms delay per step
