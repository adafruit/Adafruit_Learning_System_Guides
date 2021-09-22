import time
import board
from rainbowio import colorwheel
import neopixel

pixpin = board.D1
numpix = 60

strip = neopixel.NeoPixel(pixpin, numpix, brightness=1, auto_write=True)


# Fill the dots one after the other with a color
def colorWipe(color, wait):
    for j in range(len(strip)):
        strip[j] = (color)
        time.sleep(wait)


def rainbow_cycle(wait):
    for j in range(255):
        for i in range(len(strip)):
            idx = int((i * 256 / len(strip)) + j)
            strip[i] = colorwheel(idx & 255)
        time.sleep(wait)


def rainbow(wait):
    for j in range(255):
        for i in range(len(strip)):
            idx = int(i + j)
            strip[i] = colorwheel(idx & 255)
        time.sleep(wait)


while True:
    colorWipe((255, 0, 0), .05)  # red and delay
    colorWipe((0, 255, 0), .05)  # green and delay
    colorWipe((0, 0, 255), .05)  # blue and delay

    rainbow(0.02)
    rainbow_cycle(0.02)
