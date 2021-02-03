"""
'neopixel_builtin.py'.

=================================================
playing with the metro express builtin NeoPixel
"""

import time
import board
import neopixel

# we only have one neopixel on our metro express
NEO = neopixel.NeoPixel(board.NEOPIXEL, 1)
NEO.brightness = 0.5

# primary colors
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

COLORS = [RED, GREEN, BLUE]

for i in COLORS:
    NEO[0] = i
    NEO.show()
    time.sleep(0.3)

# shows all colors by trying all combinations of RGB levels
for red_level in range(0, 256, 100):
    for green_level in range(0, 256, 100):
        for blue_level in range(0, 256, 100):
            print("red: ", red_level, "green: ", green_level, "blue: ", blue_level)
            NEO[0] = (red_level, green_level, blue_level)
            NEO.show()
            # wait 0.2 seconds to give us time to see the colors
            time.sleep(1)
NEO[0] = (0, 0, 0)
NEO.show()
