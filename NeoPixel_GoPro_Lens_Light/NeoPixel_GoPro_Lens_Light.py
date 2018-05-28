import time

import board
import neopixel
from analogio import AnalogIn

pot = AnalogIn(board.A1)  # what pin the pot is on
pixpin = board.D0  # what pin the LEDs are on
numpix = 16  # number of LEDs in ring!
BPP = 4  # required for RGBW ring

ring = neopixel.NeoPixel(pixpin, numpix, bpp=BPP, brightness=0.9)


def val(pin):
    # divides voltage (65535) to get a value between 0 and 255
    return pin.value / 257


while True:
    # Two lines for troubleshooting to see analog value in REPL
    # print("A0: %f" % (pot.value / 65535 * 3.3))
    # time.sleep(1)

    # change floating point value to an int
    ring.fill((0, 0, 0, int(val(pot))))
    time.sleep(0.01)
