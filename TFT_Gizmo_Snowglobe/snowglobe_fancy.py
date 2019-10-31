from random import randrange
import board
import busio
import displayio
from adafruit_st7789 import ST7789
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

# Display setup
WIDTH = 240
HEIGHT = 240
displayio.release_displays()

spi = busio.SPI(board.SCL, MOSI=board.SDA)
tft_cs = board.RX
tft_dc = board.TX
tft_backlight = board.A3

display_bus = displayio.FourWire(spi, command=tft_dc, chip_select=tft_cs)

display = ST7789(display_bus, width=WIDTH, height=HEIGHT, rowstart=80,
                 backlight_pin=tft_backlight, rotation=180)

# Load background image
try:
    bg_bitmap, bg_palette = adafruit_imageload.load(BACKGROUND,
                                                    bitmap=displayio.Bitmap,
                                                    palette=displayio.Palette)
# Or just use solid color
except (OSError, TypeError):
    bg_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 1)
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
flakes = displayio.Group(max_size=NUM_FLAKES)
for _ in range(NUM_FLAKES):
    flakes.append(displayio.TileGrid(flake_bitmap, pixel_shader=flake_palette,
                                     width = 1,
                                     height = 1,
                                     tile_width = FLAKE_WIDTH,
                                     tile_height = FLAKE_HEIGHT,
                                     x = randrange(0, WIDTH),
                                     default_tile=randrange(0, NUM_SPRITES)))

# Snowfield setup
snow_depth = [HEIGHT] * WIDTH
snow_palette = displayio.Palette(2)
snow_palette[0] = 0xADAF00   # transparent color
snow_palette[1] = SNOW_COLOR # snow color
snow_palette.make_transparent(0)
snow_bitmap = displayio.Bitmap(WIDTH, HEIGHT, len(snow_palette))
snow = displayio.TileGrid(snow_bitmap, pixel_shader=snow_palette)

# Add everything to display
splash = displayio.Group()
splash.append(background)
splash.append(flakes)
splash.append(snow)
display.show(splash)

def clear_the_snow():
    #pylint: disable=global-statement, redefined-outer-name
    global flakes, flake_pos, snow_depth
    display.auto_refresh = False
    for flake in flakes:
        # set to a random sprite
        flake[0] = randrange(0, NUM_SPRITES)
        # set to a random x location
        flake.x = randrange(0, WIDTH)
    # set random y locations, off screen to start
    flake_pos = [-1.0*randrange(0, HEIGHT) for _ in range(NUM_FLAKES)]
    # reset snow level
    snow_depth = [HEIGHT] * WIDTH
    # and snow bitmap
    for i in range(WIDTH*HEIGHT):
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
        elif x == WIDTH - 1:
            # check depth to left
            if snow_depth[x-1] - snow_depth[x] < steepness:
                add = True
        elif 0 < x < WIDTH - 1:
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
    while snow_depth.count(0) < WIDTH:
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
                flake.x = randrange(0, WIDTH)
            flake.y = int(flake_pos[i])
        display.refresh()
