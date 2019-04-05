import time

import board
import neopixel

try:
    import urandom as random
except ImportError:
    import random

numpix = 3  # Number of NeoPixels
pixpin = board.D1  # Pin where NeoPixels are connected
strip = neopixel.NeoPixel(pixpin, numpix, brightness=.1, auto_write=True)
colors = [
    [30, 144, 255],  # Dodger Blue
    [232, 100, 255],  # Purple
    [204, 0, 204],  # Pink
    [200, 200, 20],  # Yellow
    [30, 200, 200],  # Blue
]


def flash_random(wait, howmany):
    for _ in range(howmany):

        c = random.randint(0, len(colors) - 1)  # Choose random color index
        j = random.randint(0, numpix - 1)  # Choose random pixel
        strip[j] = colors[c]  # Set pixel to color

        for i in range(1, 5):
            strip.brightness = i / 5.0  # Ramp up brightness
            time.sleep(wait)

        for i in range(5, 0, -1):
            strip.brightness = i / 5.0  # Ramp down brightness
            strip[j] = [0, 0, 0]  # Set pixel to 'off'
            time.sleep(wait)


while True:
    # first number is 'wait' delay, shorter num == shorter twinkle
    flash_random(.01, 1)
    # second number is how many neopixels to simultaneously light up
    flash_random(.01, 3)
    flash_random(.01, 2)
