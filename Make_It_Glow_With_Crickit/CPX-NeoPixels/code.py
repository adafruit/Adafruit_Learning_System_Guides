# SPDX-FileCopyrightText: 2018 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Use the 10 NeoPixels on Circuit Playground Express via the
#   Adafruit neopixel library
import time
import neopixel
import board

# Set up the 10 Circuit Playground Express NeoPixels half bright
CPX_pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=0.5)

# slowly power up via blue color
for i in range(50):
    CPX_pixels.fill((0, 0, i))
    time.sleep(0.05)

# blast off!
CPX_pixels.fill((255, 0, 0))

while True:
    # pulse effect
    for i in range(255, 0, -5):
        CPX_pixels.fill((i, 0, 0))
    for i in range(0, 255, 5):
        CPX_pixels.fill((i, 0, 0))
