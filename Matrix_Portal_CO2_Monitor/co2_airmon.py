import time
import board
import displayio
import adafruit_imageload
from adafruit_matrixportal.matrix import Matrix
import adafruit_scd30

# --| User Config |----
CO2_CUTOFFS = (1000, 2000, 5000)
UPDATE_RATE = 1
# ---------------------

# the sensor
scd30 = adafruit_scd30.SCD30(board.I2C())

# optional if known (pick one)
# scd30.ambient_pressure = 1013.25
# scd30.altitude = 0

# the display
matrix = Matrix(width=64, height=32, bit_depth=6)
display = matrix.display
display.rotation = 90  # matrixportal up
# display.rotation = 270 # matrixportal down

# current condition smiley face
smileys_bmp, smileys_pal = adafruit_imageload.load("/bmps/smileys.bmp")
smiley = displayio.TileGrid(
    smileys_bmp,
    pixel_shader=smileys_pal,
    x=0,
    y=0,
    width=1,
    height=1,
    tile_width=32,
    tile_height=32,
)

# current condition label
tags_bmp, tags_pal = adafruit_imageload.load("/bmps/tags.bmp")
label = displayio.TileGrid(
    tags_bmp,
    pixel_shader=tags_pal,
    x=0,
    y=32,
    width=1,
    height=1,
    tile_width=32,
    tile_height=16,
)

# current CO2 value
digits_bmp, digits_pal = adafruit_imageload.load("/bmps/digits.bmp")
co2_value = displayio.TileGrid(
    digits_bmp,
    pixel_shader=digits_pal,
    x=0,
    y=51,
    width=4,
    height=1,
    tile_width=8,
    tile_height=10,
)

# put em all together
splash = displayio.Group()
splash.append(smiley)
splash.append(label)
splash.append(co2_value)

# and show em
display.show(splash)


def update_display(value):

    value = abs(round(value))

    # smiley and label
    if value < CO2_CUTOFFS[0]:
        smiley[0] = label[0] = 0
    elif value < CO2_CUTOFFS[1]:
        smiley[0] = label[0] = 1
    elif value < CO2_CUTOFFS[2]:
        smiley[0] = label[0] = 2
    else:
        smiley[0] = label[0] = 3

    # CO2 value
    # clear it
    for i in range(4):
        co2_value[i] = 10
    # update it
    i = 3
    while value:
        co2_value[i] = value % 10
        value = int(value / 10)
        i -= 1


while True:
    # protect against NaNs and Nones
    try:
        update_display(scd30.CO2)
    except:
        pass
    time.sleep(UPDATE_RATE)
