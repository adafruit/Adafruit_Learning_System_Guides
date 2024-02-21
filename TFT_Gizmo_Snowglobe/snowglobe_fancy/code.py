# SPDX-FileCopyrightText: 2019 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

from random import randrange
import board
import busio
import displayio
from adafruit_gizmo import tft_gizmo
import adafruit_imageload
import adafruit_lis3dh

#---| User Config |---------------
BACKGROUND = "/blinka_dark.bmp"    # specify color or background BMP file

NUM_FLAKES = 50                    # total number of snowflakes
FLAKE_SHEET = "/flakes_sheet.bmp"  # flake sprite sheet
FLAKE_WIDTH = 4                    # sprite width
FLAKE_HEIGHT = 4                   # sprite height
FLAKE_TRAN_COLOR = 0x000000        # transparency color

SNOW_COLOR = 0xFFFFFF              # snow color

SHAKE_THRESHOLD = 27               # shake sensitivity, lower=more sensitive
#---| User Config |---------------

# Accelerometer setup
accelo_i2c = busio.I2C(board.ACCELEROMETER_SCL, board.ACCELEROMETER_SDA)
accelo = adafruit_lis3dh.LIS3DH_I2C(accelo_i2c, address=0x19)

# Create the TFT Gizmo display
display = tft_gizmo.TFT_Gizmo()

# Load background image
try:
    bg_bitmap, bg_palette = adafruit_imageload.load(BACKGROUND,
                                                    bitmap=displayio.Bitmap,
                                                    palette=displayio.Palette)
# Or just use solid color
except (OSError, TypeError, AttributeError):
    BACKGROUND = BACKGROUND if isinstance(BACKGROUND, int) else 0x000000
    bg_bitmap = displayio.Bitmap(display.width, display.height, 1)
    bg_palette = displayio.Palette(1)
    bg_palette[0] = BACKGROUND
background = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette)


# Snowflake setup
flake_bitmap, flake_palette = adafruit_imageload.load(FLAKE_SHEET,
                                                      bitmap=displayio.Bitmap,
                                                      palette=displayio.Palette)
if FLAKE_TRAN_COLOR is not None:
    for i, color in enumerate(flake_palette):
        if color == FLAKE_TRAN_COLOR:
            flake_palette.make_transparent(i)
            break
NUM_SPRITES = flake_bitmap.width // FLAKE_WIDTH * flake_bitmap.height // FLAKE_HEIGHT
flake_pos = [0.0] * NUM_FLAKES
flakes = displayio.Group()
for _ in range(NUM_FLAKES):
    flakes.append(displayio.TileGrid(flake_bitmap, pixel_shader=flake_palette,
                                     width = 1,
                                     height = 1,
                                     tile_width = FLAKE_WIDTH,
                                     tile_height = FLAKE_HEIGHT,
                                     x = randrange(0, display.width),
                                     default_tile=randrange(0, NUM_SPRITES)))

# Snowfield setup
snow_depth = [display.height] * display.width
snow_palette = displayio.Palette(2)
snow_palette[0] = 0xADAF00   # transparent color
snow_palette[1] = SNOW_COLOR # snow color
snow_palette.make_transparent(0)
snow_bitmap = displayio.Bitmap(display.width, display.height, len(snow_palette))
snow = displayio.TileGrid(snow_bitmap, pixel_shader=snow_palette)

# Add everything to display
splash = displayio.Group()
splash.append(background)
splash.append(flakes)
splash.append(snow)
display.root_group = splash

def clear_the_snow():
    #pylint: disable=global-statement, redefined-outer-name
    global flakes, flake_pos, snow_depth
    display.auto_refresh = False
    for flake in flakes:
        # set to a random sprite
        flake[0] = randrange(0, NUM_SPRITES)
        # set to a random x location
        flake.x = randrange(0, display.width)
    # set random y locations, off screen to start
    flake_pos = [-1.0*randrange(0, display.height) for _ in range(NUM_FLAKES)]
    # reset snow level
    snow_depth = [display.height] * display.width
    # and snow bitmap
    for i in range(display.width*display.height):
        snow_bitmap[i] = 0
    display.auto_refresh = True

def add_snow(index, amount, steepness=2):
    location = []
    # local steepness check
    for x in range(index - amount, index + amount):
        add = False
        if x == 0:
            # check depth to right
            if snow_depth[x+1] - snow_depth[x] < steepness:
                add = True
        elif x == display.width - 1:
            # check depth to left
            if snow_depth[x-1] - snow_depth[x] < steepness:
                add = True
        elif 0 < x < display.width - 1:
            # check depth to left AND right
            if snow_depth[x-1] - snow_depth[x] < steepness and \
               snow_depth[x+1] - snow_depth[x] < steepness:
                add = True
        if add:
            location.append(x)
    # add where snow is not too steep
    for x in location:
        new_level = snow_depth[x] - 1
        if new_level >= 0:
            snow_depth[x] = new_level
            snow_bitmap[x, new_level] = 1

while True:
    clear_the_snow()
    # loop until globe is full of snow
    while snow_depth.count(0) < display.width:
        # check for shake
        if accelo.shake(SHAKE_THRESHOLD, 5, 0):
            break
        # update snowflakes
        for i, flake in enumerate(flakes):
            # speed based on sprite index
            flake_pos[i] += 1 - flake[0] / NUM_SPRITES
            # check if snowflake has hit the ground
            if flake_pos[i] >= snow_depth[flake.x]:
                # add snow where it fell
                add_snow(flake.x, FLAKE_WIDTH)
                # reset flake to top
                flake_pos[i] = 0
                # at a new x location
                flake.x = randrange(0, display.width)
            flake.y = int(flake_pos[i])
        display.refresh()
