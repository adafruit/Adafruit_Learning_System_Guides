import random

import board
import neopixel
from rainbowio import colorwheel
from ulab import numpy as np

# Customize your neopixel configuration here...
pixel_pin = board.D5
num_pixels = 96
pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.1,
                           auto_write=False, pixel_order=neopixel.RGB)

ddt = np.array([1.,-2.,1.])
def step(u, um, f, n, dx, dt, c):
    dt2 = dt*dt
    C2 = (c*dt/dx)**2
    deriv = np.convolve(u, ddt)[1:-1] * C2
    up = -um + u * 2 + deriv + f * dt2
    up[0] = 0
    up[n-1] = 0

    return up

def main():
    # This precomputes the color palette for maximum speed
    # You could change it to compute the color palette of your choice
    w = [colorwheel(i) for i in range(256)]

    # This sets up the initial wave as a smooth gradient
    u = np.zeros(num_pixels)
    um = np.zeros(num_pixels)
    f = np.zeros(num_pixels)

    slope = np.linspace(0, 256, num=num_pixels)
    th = 1

    # the first time is always random (is that a contradiction?)
    r = 0

    while True:

        # Some of the time, add a random new wave to the mix
        # increase .15 to add waves more often
        # decrease it to add waves less often
        if r < .01:
            ii = random.randrange(1, num_pixels-1)
            # increase 2 to make bigger waves
            f[ii] = (random.random() - .5) * 2

        # Here's where to change dx, dt, and c
        # try .2, .02, 2 for relaxed
        # try 1., .7, .2 for very busy / almost random
        u, um = step(u, um, f, num_pixels, .1, .02, 1), u

        v = u * 200000 + slope + th
        for i, vi in enumerate(v):
            # Scale up by an empirical value, rotate by th, and look up the color
            pixels[i] = w[round(vi) % 256]

        # Take away a portion of the energy of the waves so they don't get out
        # of control
        u = u * .99

        # incrementing th causes the colorwheel to slowly cycle even if nothing else is happening
        th = (th + .25) % 256
        pixels.show()

        # Clear out the old random value, if any
        f[ii] = 0

        # and get a new random value
        r = random.random()

main()
