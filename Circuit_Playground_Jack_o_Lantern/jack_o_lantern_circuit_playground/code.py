"""Jack-o'-Lantern flame example Adafruit Circuit Playground Express"""

import math
import board
import neopixel
try:
    import urandom as random  # for v1.0 API support
except ImportError:
    import random

NUMPIX = 10        # Number of NeoPixels
PIXPIN = board.D8  # Pin where NeoPixels are connected
STRIP = neopixel.NeoPixel(PIXPIN, NUMPIX, brightness=1.0)
PREV = 128

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
        STRIP.fill((int(level), int(level / 8), int(level / 48)))
        STRIP.write()

while True:  # Loop forever...
    LVL = random.randint(64, 191)
    split(PREV, LVL, 32)
    PREV = LVL
