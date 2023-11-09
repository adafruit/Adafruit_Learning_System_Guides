# SPDX-FileCopyrightText: 2022 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

#
# Dual Knob Sketcher
#

import time
import board
import displayio
import digitalio
import analogio
import adafruit_ili9341
from simpleio import map_range

#--| User Config |---------------------------------------------------
SKETCH_SCALE      = 3
DRAW_COLOR        = 0xFFFFFF
BACKGROUND_COLOR  = 0x000000
PEN_UP_COLOR      = 0xFF0000
PEN_DOWN_COLOR    = 0x00FF00
KNOB_READS        = 10
KNOB_DELAY        = 0.001
REVERSE_X         = True
REVERSE_Y         = True
#--| User Config |---------------------------------------------------

# Feather M4 + 2.4" TFT FeatherWing setup
DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240
SKETCH_WIDTH = DISPLAY_WIDTH // SKETCH_SCALE
SKETCH_HEIGHT = DISPLAY_HEIGHT // SKETCH_SCALE
PEN_SWITCH = board.D12
CLEAR_BUTTON = board.D11
X_KNOB = board.A0
Y_KNOB = board.A1

# set up knobs
x_knob = analogio.AnalogIn(X_KNOB)
y_knob = analogio.AnalogIn(Y_KNOB)

# set up button
clear_button = digitalio.DigitalInOut(CLEAR_BUTTON)
clear_button.switch_to_input(pull=digitalio.Pull.UP)

# set up pen up/down switch
pen_switch = digitalio.DigitalInOut(PEN_SWITCH)
pen_switch.switch_to_input(pull=digitalio.Pull.UP)

# set up display
displayio.release_displays()

spi = board.SPI()
tft_cs = board.D9
tft_dc = board.D10
tft_rst = board.D6
display_bus = displayio.FourWire(
    spi, command=tft_dc, chip_select=tft_cs, reset=tft_rst
)
display = adafruit_ili9341.ILI9341(display_bus, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)

# add base UI element
splash = displayio.Group(scale=SKETCH_SCALE)
display.root_group = splash

# add sketch
sketch_bitmap = displayio.Bitmap(SKETCH_WIDTH, SKETCH_HEIGHT, 2)
sketch_palette = displayio.Palette(2)
sketch_palette[0] = BACKGROUND_COLOR
sketch_palette[1] = DRAW_COLOR
sketch = displayio.TileGrid(sketch_bitmap, pixel_shader=sketch_palette, x=0, y=0)
splash.append(sketch)

# add pen cursor
pen_bitmap = displayio.Bitmap(3, 3, 2)
pen_palette = displayio.Palette(2)
pen_palette[0] = BACKGROUND_COLOR
pen_palette[1] = PEN_DOWN_COLOR
CURSOR = (
    1, 1, 1,
    1, 0, 1,
    1, 1, 1,
)
for i, value in enumerate(CURSOR):
    pen_bitmap[i] = value
pen = displayio.TileGrid(pen_bitmap, pixel_shader=pen_palette)
splash.append(pen)

# helper to average analog knob readings
def read_knobs(reads, delay):
    avg_x = avg_y = 0
    for _ in range(reads):
        avg_x += x_knob.value
        avg_y += y_knob.value
        time.sleep(delay)
    avg_x /= reads
    avg_y /= reads
    xx = int(map_range(avg_x, 0, 65535, 0, SKETCH_WIDTH - 1))
    yy = int(map_range(avg_y, 0, 65535, 0, SKETCH_HEIGHT - 1))
    if REVERSE_X:
        xx = SKETCH_WIDTH - xx - 1
    if REVERSE_Y:
        yy = SKETCH_HEIGHT - yy - 1
    return xx, yy

#-------
# MAIN
#-------
while True:
    while clear_button.value:
        x, y = read_knobs(KNOB_READS, KNOB_DELAY)
        pen.x = x - 1
        pen.y = y - 1
        if pen_switch.value:
            # PEN DOWN
            pen_palette[1] = PEN_DOWN_COLOR
            sketch_bitmap[x, y] = 1
        else:
            # PEN UP
            pen_palette[1] = PEN_UP_COLOR
    sketch_bitmap.fill(0)
