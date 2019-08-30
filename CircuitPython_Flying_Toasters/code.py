"""
Continuously scroll randomly generated Mario style toasters.
Designed fr an ItsyBitsy M4 Express and a 1.3" 240x240 TFT

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
CELL_1 = EMPTY + 1
CELL_2 = CELL_1 + 1
CELL_3 = CELL_2 + 1
CELL_4 = CELL_3 + 1
TOAST = CELL_4 + 1

NUMBER_OF_SPRITES = TOAST + 1

# Animation support

FIRST_CELL = CELL_1
LAST_CELL = CELL_4

NUMBER_OF_CELLS = (LAST_CELL - FIRST_CELL) + 1

# A boolean array corresponding to the sprites, True if it's part of the animation sequence.
ANIMATED = [_sprite >= FIRST_CELL and _sprite <= LAST_CELL for _sprite in range(NUMBER_OF_SPRITES)]


# The chance (out of 10) that a new toaster, or toast will enter
CHANCE_OF_NEW_TOASTER = 5
CHANCE_OF_NEW_TOAST = 2

# How many sprites to styart with
INITIAL_NUMBER_OF_SPRITES= 5

# Global variables
display = None
tilegrid = None

seed(int(time.monotonic()))

def make_display():
    """Set up the display support.
    Return the Display object.
    """
    spi = board.SPI()
    while not spi.try_lock():
        pass
    spi.configure(baudrate=24000000) # Configure SPI for 24MHz
    spi.unlock()
    tft_cs = board.D10
    tft_dc = board.D7

    displayio.release_displays()
    display_bus = displayio.FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=board.D9)

    return ST7789(display_bus, width=240, height=240, rowstart=80, auto_refresh=True)

def make_tilegrid():
    """Construct and return the tilegrid."""
    group = displayio.Group(max_size=10)

    sprite_sheet, palette = adafruit_imageload.load("/spritesheet.bmp",
                                                    bitmap=displayio.Bitmap,
                                                    palette=displayio.Palette)
    grid = displayio.TileGrid(sprite_sheet, pixel_shader=palette,
                              width=9, height=9,
                              tile_height=32, tile_width=32,
                              x=0, y=-32,
                              default_tile=EMPTY)
    group.append(grid)
    display.show(group)
    return grid

def random_cell():
    return randint(FIRST_CELL, LAST_CELL)

def evaluate_position(row, col):
    """Return whether how long of aa toaster is placable at the given location.
    :param row: the tile row (0-9)
    :param col: the tile column (0-9)
    """
    return tilegrid[col, row] == EMPTY

def seed_toasters(number_of_toasters):
    """Create the initial toasters so it doesn't start empty"""
    for _ in range(number_of_toasters):
        while True:
            row = randint(0, 8)
            col = randint(0, 8)
            if evaluate_position(row, col):
                break
        tilegrid[col, row] = random_cell()

def next_sprite(sprite):
    if ANIMATED[sprite]:
        return (((sprite - FIRST_CELL) + 1) % NUMBER_OF_CELLS) + FIRST_CELL
    return sprite

def advance_animation():
    """Cycle through animation cells each time."""
    for tile_number in range(81):
        tilegrid[tile_number] = next_sprite(tilegrid[tile_number])

def slide_tiles():
    """Move the tilegrid one pixel to the bottom-left."""
    tilegrid.x -= 1
    tilegrid.y += 1

def shift_tiles():
    """Move tiles one spot to the left, and reset the tilegrid's position"""
    for row in range(8, 0, -1):
        for col in range(8):
            tilegrid[col, row] = tilegrid[col + 1, row - 1]
        tilegrid[8, row] = EMPTY
    for col in range(9):
        tilegrid[col, 0] = EMPTY
    tilegrid.x = 0
    tilegrid.y = -32

def get_entry_row():
    while True:
        row = randint(0, 8)
        if tilegrid[8, row] == EMPTY and tilegrid[7, row] == EMPTY:
            return row

def get_entry_column():
    while True:
        col = randint(0, 8)
        if tilegrid[col, 0] == EMPTY and tilegrid[col, 1] == EMPTY:
            return col

def add_toaster_or_toast():
    """Maybe add a new toaster or toast on the right and/or top at a randon open location"""
    if randint(1, 10) <= CHANCE_OF_NEW_TOAST:
        tile = TOAST
    elif randint(1, 10) <= CHANCE_OF_NEW_TOASTER:
        tile = random_cell()
    else:
        tile = EMPTY
    tilegrid[8, get_entry_row()] = tile

    if randint(1, 10) <= CHANCE_OF_NEW_TOAST:
        tile = TOAST
    elif randint(1, 8) <= CHANCE_OF_NEW_TOASTER:
        tile = random_cell()
    else:
        tile = EMPTY
    tilegrid[get_entry_column(), 0] = tile

display = make_display()
tilegrid = make_tilegrid()
seed_toasters(INITIAL_NUMBER_OF_SPRITES)
display.refresh()

while True:
    for _ in range(32):
        display.refresh(target_frames_per_second=80)
        advance_animation()
        slide_tiles()
    shift_tiles()
    add_toaster_or_toast()
    display.refresh(target_frames_per_second=120)
