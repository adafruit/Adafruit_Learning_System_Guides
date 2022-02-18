# SPDX-FileCopyrightText: 2017 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import board
import neopixel

pixpin = board.D1
numpix = 7
wait = .5  # 1/2 second color fade duration

# defaults to RGB|GRB Neopixels
strip = neopixel.NeoPixel(pixpin, numpix, brightness=1, auto_write=False)


# uncomment the following 3 line for RGBW Neopixels
# strip = neopixel.NeoPixel(
# pixpin, numpix, bpp=4, brightness=.3, auto_write=True
# )

# Linear interpolation of y value given min/max x, min/max y, and x position.


def lerp(x, x0, x1, y0, y1):
    # Clamp x within x0 and x1 bounds.
    if x > x1:
        x = x1

    if x < x0:
        x = x0

    # Calculate linear interpolation of y value.
    return y0 + (y1 - y0) * ((x - x0) / (x1 - x0))


# Set all pixels to the specified color.


def fill_pixels(r, g, b):
    for i in range(0, numpix):
        strip[i] = (r, g, b)
        strip.write()


# Get the color of a pixel within a smooth gradient of two colors.
# Starting R,G,B color
# Ending R,G,B color
# Position along gradient, should be a value 0 to 1.0


def color_gradient(start_r, start_g, start_b, end_r, end_g, end_b, pos):
    # Interpolate R,G,B values and return them as a color.
    red = lerp(pos, 0.0, 1.0, start_r, end_r)
    green = lerp(pos, 0.0, 1.0, start_g, end_g)
    blue = lerp(pos, 0.0, 1.0, start_b, end_b)

    return (red, green, blue)


# Starting R,G,B color
# Ending R,G,B color
# Total duration of animation, in milliseconds


def animate_gradient_fill(start_r, start_g, start_b, end_r, end_g, end_b,
                          duration_ms):
    start = time.monotonic()

    # Display start color.
    fill_pixels(start_r, start_g, start_b)

    # Main animation loop.
    delta = time.monotonic() - start

    while delta < duration_ms:
        # Calculate how far along we are in the duration as a position 0...1.0
        pos = delta / duration_ms
        # Get the gradient color and fill all the pixels with it.
        color = color_gradient(start_r, start_g, start_b,
                               end_r, end_g, end_b, pos)
        fill_pixels(int(color[0]), int(color[1]), int(color[2]))
        # Update delta and repeat.
        delta = time.monotonic() - start

    # Display end color.
    fill_pixels(end_r, end_g, end_b)


while True:
    # Run It:

    # Nice fade from dim red to full red for 1/2 of a second:
    animate_gradient_fill(10, 0, 0, 255, 0, 0, wait)

    # Then fade from full red to dim red for 1/2 a second.
    animate_gradient_fill(255, 0, 0, 10, 0, 0, wait)

    # time.sleep(1) # Use this delay if using multiple color fades
