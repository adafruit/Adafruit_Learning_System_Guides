# SPDX-FileCopyrightText: 2019 Dave Astels for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Continuously scroll randomly generated Mario style clouds.
Designed for an ItsyBitsy M4 Express and a 1.3" 240x240 TFT

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2019 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

import time
from random import seed, randint
import board
import displayio
from adafruit_st7789 import ST7789
import adafruit_imageload


# Sprite cell values
EMPTY = 0
LEFT = 1
MIDDLE = 2
RIGHT = 3

# These constants determine what happens when tiles are shifted.
# if randint(1, 10) > the value, the thing happens

# The chance a new cloud will enter
CHANCE_OF_NEW_CLOUD = 4

# The chance an existing cloud gets extended
CHANCE_OF_EXTENDING_A_CLOUD = 5

seed(int(time.monotonic()))


def make_display():
    """Set up the display support.
    Return the Display object.
    """
    spi = board.SPI()
    while not spi.try_lock():
        pass
    spi.configure(baudrate=24000000)  # Configure SPI for 24MHz
    spi.unlock()

    displayio.release_displays()
    display_bus = displayio.FourWire(spi, command=board.D7, chip_select=board.D10, reset=board.D9)

    return ST7789(display_bus, width=240, height=240, rowstart=80, auto_refresh=True)


def make_tilegrid():
    """Construct and return the tilegrid."""
    group = displayio.Group()

    sprite_sheet, palette = adafruit_imageload.load("/tilesheet-2x.bmp",
                                                    bitmap=displayio.Bitmap,
                                                    palette=displayio.Palette)
    grid = displayio.TileGrid(sprite_sheet, pixel_shader=palette,
                              width=9, height=5,
                              tile_height=48, tile_width=32,
                              default_tile=EMPTY)
    group.append(grid)
    display.root_group = group
    return grid


def evaluate_position(row, col):
    """Return how long of a cloud is placeable at the given location.
    :param row: the tile row (0-4)
    :param col: the tile column (0-8)
    """
    if tilegrid[col, row] != EMPTY or tilegrid[col + 1, row] != EMPTY:
        return 0
    end_col = col + 1
    while end_col < 9 and tilegrid[end_col, row] == EMPTY:
        end_col += 1
    return min([4, end_col - col])


def seed_clouds(number_of_clouds):
    """Create the initial clouds so it doesn't start empty"""
    for _ in range(number_of_clouds):
        while True:
            row = randint(0, 4)
            col = randint(0, 7)
            cloud_length = evaluate_position(row, col)
            if cloud_length > 0:
                break
        l = randint(1, cloud_length)
        tilegrid[col, row] = LEFT
        for _ in range(l - 2):
            col += 1
            tilegrid[col, row] = MIDDLE
        tilegrid[col + 1, row] = RIGHT


def slide_tiles():
    """Move the tilegrid to the left, one pixel at a time, a full time width"""
    for _ in range(32):
        tilegrid.x -= 1
        display.refresh(target_frames_per_second=60)


def shift_tiles():
    """Move tiles one spot to the left, and reset the tilegrid's position"""
    for row in range(5):
        for col in range(8):
            tilegrid[col, row] = tilegrid[col + 1, row]
        tilegrid[8, row] = EMPTY
    tilegrid.x = 0


def extend_clouds():
    """Extend any clouds on the right edge, either finishing them with a right
    end or continuing them with a middle piece
    """
    for row in range(5):
        if tilegrid[7, row] == LEFT or tilegrid[7, row] == MIDDLE:
            if randint(1, 10) > CHANCE_OF_EXTENDING_A_CLOUD:
                tilegrid[8, row] = MIDDLE
            else:
                tilegrid[8, row] = RIGHT


def add_cloud():
    """Maybe add a new cloud on the right at a random open row"""
    if randint(1, 10) > CHANCE_OF_NEW_CLOUD:
        count = 0
        while True:
            count += 1
            if count == 50:
                return
            row = randint(0, 4)
            if tilegrid[7, row] == EMPTY and tilegrid[8, row] == EMPTY:
                break
        tilegrid[8, row] = LEFT


display = make_display()
tilegrid = make_tilegrid()
seed_clouds(5)

while True:
    slide_tiles()
    shift_tiles()
    extend_clouds()
    add_cloud()
