import time

import board
import neopixel

numpix = 64  # Number of NeoPixels
pixpin = board.D1  # Pin where NeoPixels are connected
strip = neopixel.NeoPixel(pixpin, numpix, brightness=0.15)
color = [5, 250, 200]  # RGB color - cyan

sine = [  # These are the pixels in order of animation - 70 pixels in total:
    4, 3, 2, 1, 0, 15, 14, 13, 12, 20, 21, 22, 23, 24, 25, 26, 27, 28,
    36, 35, 34, 33, 32, 47, 46, 45, 44, 52, 53, 54, 55, 56, 57, 58, 59, 60,
    61, 62, 63, 48, 49, 50, 51, 52, 44, 43, 42, 41, 40, 39, 38, 37, 36, 28,
    29, 30, 31, 16, 17, 18, 19, 20, 12, 11, 10, 9, 8, 7, 6, 5]

while True:  # Loop forever...
    for i in range(len(sine)):
        # Erase 'tail':
        strip[sine[i]] = [0, 0, 0]
        # Draw 'head,' 10 pixels ahead:
        strip[sine[(i + 10) % len(sine)]] = color
        strip.write()  # Refresh LED states
        time.sleep(0.04)  # 40 millisecond delay
