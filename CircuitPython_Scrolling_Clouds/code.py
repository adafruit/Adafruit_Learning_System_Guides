"""
This test will initialize the display using displayio and draw a solid green
background, a smaller purple rectangle, and some yellow text.
"""

#pylint:disable=redefined-outer-name
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

    return ST7789(display_bus, width=240, height=240, rowstart=80)

def make_tilegrid():
    """Construct and return the tilegrid."""
    group = displayio.Group(max_size=10)

    sprite_sheet, palette = adafruit_imageload.load("/tilesheet.bmp",
                                                    bitmap=displayio.Bitmap,
                                                    palette=displayio.Palette)
    grid = displayio.TileGrid(sprite_sheet, pixel_shader=palette,
                              width=16, height=10,
                              tile_height=24, tile_width=16,
                              default_tile=EMPTY)
    group.append(grid)
    display.show(group)
    return grid

def evaluate_position(row, col):
    """Return how long of a cloud is placable at the given location.
    :param row: the tile row (0-9)
    :param col: the tile column (0-14)
    """
    if tilegrid[col, row] != EMPTY or tilegrid[col + 1, row] != EMPTY:
        return 0
    end_col = col + 1
    while end_col < 16 and tilegrid[end_col, row] == EMPTY:
        end_col += 1
    return min([4, end_col - col])

def seed_clouds(number_of_clouds):
    """Create the initial clouds so it doesn't start empty"""
    for _ in range(number_of_clouds):
        while True:
            row = randint(0, 9)
            col = randint(0,14)
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
    for _ in range(16):
        tilegrid.x -= 1
        display.refresh_soon()
        display.wait_for_frame()

def shift_tiles():
    """Move tiles one spot to the left, and reset the tilegrid's position"""
    for row in range(10):
        for col in range(15):
            tilegrid[col, row] = tilegrid[col + 1, row]
        tilegrid[15, row] = EMPTY
    tilegrid.x = 0

def extend_clouds():
    """Extend any clouds on the right edge, either finishing them with a right
    end or continuing them with a middle piece
    """
    for row in range(10):
        if tilegrid[14, row] == LEFT or tilegrid[14, row] == MIDDLE:
            if randint(1, 10) > CHANCE_OF_EXTENDING_A_CLOUD:
                tilegrid[15, row] = MIDDLE
            else:
                tilegrid[15, row] = RIGHT

def add_cloud():
    """Maybe add a new cloud on the right at a randon open row"""
    if randint(1, 10) > CHANCE_OF_NEW_CLOUD:
        while True:
            row = randint(0, 9)
            if tilegrid[14, row] == EMPTY and tilegrid[15, row] == EMPTY:
                break
        tilegrid[15, row] = LEFT

display = make_display()
tilegrid = make_tilegrid()
seed_clouds(5)

while True:
    slide_tiles()
    shift_tiles()
    extend_clouds()
    add_cloud()
