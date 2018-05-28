# CircuitPython demo - NeoPixel

import time

import board
import neopixel

pixpin = board.D1
numpix = 10

strip = neopixel.NeoPixel(pixpin, numpix, brightness=0.3, auto_write=False)


def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if (pos < 0) or (pos > 255):
        return (0, 0, 0)
    if pos < 85:
        return (int(pos * 3), int(255 - (pos * 3)), 0)
    elif pos < 170:
        pos -= 85
        return (int(255 - pos * 3), 0, int(pos * 3))
    else:
        pos -= 170
        return (0, int(pos * 3), int(255 - pos * 3))


def rainbow_cycle(wait):
    for j in range(255):
        for i in range(len(strip)):
            idx = int((i * 256 / len(strip)) + j)
            strip[i] = wheel(idx & 255)
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
