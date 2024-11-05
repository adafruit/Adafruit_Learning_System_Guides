# SPDX-FileCopyrightText: 2024 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Uses NeoPixel Featherwing connected to D10 and
Dotstar Featherwing connected to D13, and D11.
Update pins as needed for your connections.
"""
import board
import neopixel
import adafruit_dotstar as dotstar
from conways import ConwaysLifeAnimation
from snake import SnakeAnimation

# Update to match the pin connected to your NeoPixels
pixel_pin = board.D10
# Update to match the number of NeoPixels you have connected
pixel_num = 32

# initialize the neopixels featherwing
pixels = neopixel.NeoPixel(pixel_pin, pixel_num, brightness=0.02, auto_write=False)

# initialize the dotstar featherwing
dots = dotstar.DotStar(board.D13, board.D11, 72, brightness=0.02)

# initial live cells for conways
initial_cells = [
    (2, 1),
    (3, 1),
    (4, 1),
    (5, 1),
    (6, 1),
]

# initialize the animations
conways = ConwaysLifeAnimation(dots, 0.1, 0xff00ff, 12, 6, initial_cells)

snake = SnakeAnimation(pixels, speed=0.1, color=0xff00ff, width=8, height=4)

while True:
    # call animate to show the next animation frames
    conways.animate()
    snake.animate()
