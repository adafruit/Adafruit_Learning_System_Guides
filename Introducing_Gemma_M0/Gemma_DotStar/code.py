# CircuitPython demo - Dotstar

import time
from rainbowio import colorwheel
import adafruit_dotstar
import board

numpix = 64
strip = adafruit_dotstar.DotStar(board.D2, board.D0, numpix, brightness=0.2)


def rainbow_cycle(wait):
    for j in range(255):
        for i in range(len(strip)):
            idx = int((i * 256 / len(strip)) + j)
            strip[i] = colorwheel(idx & 255)
        strip.show()
        time.sleep(wait)


while True:
    strip.fill((255, 0, 0))
    strip.show()
    time.sleep(1)

    strip.fill((0, 255, 0))
    strip.show()
    time.sleep(1)

    strip.fill((0, 0, 255))
    strip.show()
    time.sleep(1)

    rainbow_cycle(0.001)  # high speed rainbow cycle w/1ms delay per sweep
