import time

import board
import neopixel

numpix = 5  # Number of NeoPixels
pixpin = board.D1  # Pin where NeoPixels are connected
hue = 0  # Starting color
strip = neopixel.NeoPixel(pixpin, numpix, brightness=0.4)


def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if (pos < 0) or (pos > 255):
        return [0, 0, 0]
    elif pos < 85:
        return [int(pos * 3), int(255 - (pos * 3)), 0]
    elif pos < 170:
        pos -= 85
        return [int(255 - pos * 3), 0, int(pos * 3)]
    else:
        pos -= 170
        return [0, int(pos * 3), int(255 - pos * 3)]


while True:  # Loop forever...
    for i in range(numpix):
        strip[i] = wheel((hue + i * 8) & 255)
    strip.write()
    time.sleep(0.02)  # 20 ms = ~50 fps
    hue = (hue + 1) & 255  # Increment hue and 'wrap around' at 255
