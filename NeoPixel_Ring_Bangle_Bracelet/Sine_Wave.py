import time

import board
import neopixel

numpix = 64  # Number of NeoPixels
pixpin = board.D1  # Pin where NeoPixels are connected
strip = neopixel.NeoPixel(pixpin, numpix, brightness=0.15)
color = [75, 250, 100]  # RGB color - teal

sine = [  # These are the pixels in order of animation - 36 pixels in total:
    4, 3, 2, 1, 0, 15, 14, 13, 12, 20, 21, 22, 23, 24, 25, 26, 27, 28,
    36, 35, 34, 33, 32, 47, 46, 45, 44, 52, 53, 54, 55, 56, 57, 58, 59, 60]

while True:  # Loop forever...
    for i in range(len(sine)):
        # Set 'head' pixel to color:
        strip[sine[i]] = color
        # Erase 'tail,' 8 pixels back:
        strip[sine[(i + len(sine) - 8) % len(sine)]] = [0, 0, 0]
        strip.write()  # Refresh LED states
        time.sleep(0.016)  # 16 millisecond delay
