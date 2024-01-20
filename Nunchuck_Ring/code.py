# SPDX-FileCopyrightText: 2021 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import adafruit_nunchuk
import neopixel
import simpleio

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
nc = adafruit_nunchuk.Nunchuk(i2c)
#  create neopixel object
NEOPIN = board.D6
NEOLENGTH = 60
NEOORDER = neopixel.GRBW  # set to GRB for 'regular' RGB NeoPixels
pixels = neopixel.NeoPixel(
    NEOPIN, NEOLENGTH, brightness=0.1, auto_write=False, pixel_order=NEOORDER
)

RED = (220, 0, 0)
PURPLE = (80, 0, 160)
PINK = (100, 0, 80)
GREEN = (0, 180, 0)
CYAN = (0, 80, 100)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)

COLORS = [RED, PURPLE, PINK, GREEN, CYAN, BLUE]
pix = 0  # selected pixel
color_pick = 0  # current color index
pixels.fill(BLACK)
pixels.show()

while True:
    x, y = nc.joystick  # get joystick values
    ax, ay, az = nc.acceleration  # get accelerometer values

    tilt_x = simpleio.map_range(ax, 300.0, 800.0, 0.0, 1.0)  # remap tilt to brightness
    # remap y to current pixel
    pix = int(
        simpleio.map_range(y, 0, 255, 0, NEOLENGTH - 1)
    )

    if nc.button_C:  # hold C button to use tilt for brightness
        pixels.brightness = tilt_x

    if nc.button_Z:
        color_pick = (color_pick + 1) % 4  # cycle through colors
        time.sleep(0.02)  # debounce

    pixels.fill(BLACK)  # turn off pixels
    for i in range(0, pix + 1):  # light up all pixels up to the current one
        pixels[i] = COLORS[color_pick]

    pixels.show()
