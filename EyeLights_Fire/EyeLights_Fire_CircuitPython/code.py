# SPDX-FileCopyrightText: 2021 Phil Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
FIRE EFFECT for Adafruit EyeLights (LED Glasses + Driver).
A demoscene classic that produces a cool analog-esque look with
modest means, iteratively scrolling and blurring raster data.
"""

import random
from supervisor import reload
import board
from busio import I2C
import adafruit_is31fl3741
from adafruit_is31fl3741.adafruit_ledglasses import LED_Glasses


# HARDWARE SETUP ---------

# Manually declare I2C (not board.I2C() directly) to access 1 MHz speed...
i2c = I2C(board.SCL, board.SDA, frequency=1000000)

# Initialize the IS31 LED driver, buffered for smoother animation
glasses = LED_Glasses(i2c, allocate=adafruit_is31fl3741.MUST_BUFFER)
glasses.show()  # Clear any residue on startup
glasses.global_current = 20  # Just middlin' bright, please


# INITIALIZE TABLES ------

# The raster data is intentionally one row taller than the LED matrix.
# Each frame, random noise is put in the bottom (off matrix) row. There's
# also an extra column on either side, to avoid needing edge clipping when
# neighboring pixels (left, center, right) are averaged later.
data = [[0] * (glasses.width + 2) for _ in range(glasses.height + 1)]
# (2D array where elements are accessed as data[y][x], initialized to 0)

# Each element in the raster is a single value representing brightness.
# A pre-computed lookup table maps these to RGB colors. This one happens
# to have 32 elements, but as we're not on an actual paletted hardware
# framebuffer it could be any size really (with suitable changes throughout).
gamma = 2.6
colormap = []
for n in range(32):
    n *= 3 / 31  #  0.0 <= n <= 3.0 from start to end of map
    if n <= 1:  #   0.0 <= n <= 1.0 : black to red
        r = n  #    r,g,b are initially calculated 0 to 1 range
        g = b = 0
    elif n <= 2:  # 1.0 <= n <= 2.0 : red to yellow
        r = 1
        g = n - 1
        b = 0
    else:  #        2.0 <= n <= 3.0 : yellow to white
        r = g = 1
        b = n - 2
    r = int((r ** gamma) * 255)  #               Gamma correction linearizes
    g = int((g ** gamma) * 255)  #               perceived brightness, then
    b = int((b ** gamma) * 255)  #               scale to 0-255 for LEDs and
    colormap.append((r << 16) | (g << 8) | b)  # store as 'packed' RGB color


# UTILITY FUNCTIONS -----


def interp(ring, led1, led2, level1, level2):
    """Linearly interpolate a range of brightnesses between two LEDs of
    one eyeglass ring, mapping through the global color table. LED range
    is non-inclusive; the first and last LEDs (which overlap matrix pixels)
    are not set. led2 MUST be > led1. LED indices may be >= 24 to 'wrap
    around' the seam at the top of the ring."""
    span = led2 - led1 + 1  #  Number of LEDs
    delta = level2 - level1  # Difference in brightness
    for led in range(led1 + 1, led2):  # For each LED in-between,
        ratio = (led - led1) / span  #   interpolate brightness level
        ring[led % 24] = colormap[min(31, int(level1 + delta * ratio))]


# MAIN LOOP -------------

while True:
    # The try/except here is because VERY INFREQUENTLY the I2C bus will
    # encounter an error when accessing the LED driver, whether from bumping
    # around the wires or sometimes an I2C device just gets wedged. To more
    # robustly handle the latter, the code will restart if that happens.
    try:

        # At the start of each frame, fill the bottom (off matrix) row
        # with random noise. To make things less strobey, old data from the
        # prior frame still has about 1/3 'weight' here. There's no special
        # real-world significance to the 85, it's just an empirically-
        # derived fudge factor that happens to work well with the size of
        # the color map.
        for x in range(1, 19):
            data[5][x] = 0.33 * data[5][x] + 0.67 * random.random() * 85
        # If this were actual SRS BZNS 31337 D3M0SC3N3 code, great care
        # would be taken to avoid floating-point math. But with few pixels,
        # and so this code might be less obtuse, a casual approach is taken.

        # Each row (except last) is then processed, top-to-bottom. This
        # order is important because it's an iterative algorithm...the
        # output of each frame serves as input to the next, and the steps
        # below (looking at the pixels below each row) are what makes the
        # "flames" appear to move "up."
        for y in range(5):  #         Current row of pixels
            y1 = data[y + 1]  #       One row down
            for x in range(1, 19):  # Skip left, right columns in data
                # Each pixel is sort of the average of the three pixels
                # under it (below left, below center, below right), but not
                # exactly. The below center pixel has more 'weight' than the
                # others, and the result is scaled to intentionally land
                # short, making each row bit darker as they move up.
                data[y][x] = (y1[x] + ((y1[x - 1] + y1[x + 1]) * 0.33)) * 0.35
                glasses.pixel(x - 1, y, colormap[min(31, int(data[y][x]))])

        # That's all well and good for the matrix, but what about the extra
        # LEDs in the rings? Since these don't align to the pixel grid,
        # rather than trying to extend the raster data and filter it in
        # somehow, we'll fill those arcs with colors interpolated from the
        # endpoints where rings and matrix intersect. Maybe not perfect,
        # but looks okay enough!
        interp(glasses.left_ring, 7, 17, data[4][8], data[4][1])
        interp(glasses.left_ring, 21, 29, data[0][2], data[2][8])
        interp(glasses.right_ring, 7, 17, data[4][18], data[4][11])
        interp(glasses.right_ring, 19, 27, data[2][11], data[0][17])

        glasses.show()  # Buffered mode MUST use show() to refresh matrix

    except OSError:  # See "try" notes above regarding rare I2C errors.
        print("Restarting")
        reload()
