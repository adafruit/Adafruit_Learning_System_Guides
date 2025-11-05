# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import math
import board
from digitalio import DigitalInOut, Direction, Pull
import pwmio
from adafruit_lsm6ds.lsm6ds33 import LSM6DS33
from adafruit_lsm6ds.lsm6ds3trc import LSM6DS3TRC
from adafruit_lsm6ds import AccelRange, AccelHPF, Rate
from adafruit_display_text import label
import displayio
import terminalio

button_a = DigitalInOut(board.BUTTON_A)
button_a.direction = Direction.INPUT
button_a.pull = Pull.UP

splash = displayio.Group()

# bad egg
BAD_EGG_FILENAME = "broken_egg.bmp"

begg_bmp = displayio.OnDiskBitmap(BAD_EGG_FILENAME)
begg_sprite = displayio.TileGrid(begg_bmp, pixel_shader=begg_bmp.pixel_shader)

# good egg
GOOD_EGG_FILENAME = "good_egg.bmp"

gegg_bmp = displayio.OnDiskBitmap(GOOD_EGG_FILENAME)
gegg_sprite = displayio.TileGrid(gegg_bmp, pixel_shader=gegg_bmp.pixel_shader)

# draw the bad egg!
splash.append(begg_sprite)
# draw the good egg on top
splash.append(gegg_sprite)

# Draw a label
text_group = displayio.Group(scale=2, x=10, y=220)
text = "Current & Max Acceleration"
text_area = label.Label(terminalio.FONT, text=text, color=0x0000FF)
text_group.append(text_area) # Subgroup for text scaling
splash.append(text_group)

# display everything so far
board.DISPLAY.root_group = splash

# connect to the accelerometer
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
# connect to the accelerometer
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
try:
    sensor = LSM6DS33(i2c)      # older CLUEs
except RuntimeError:
    sensor = LSM6DS3TRC(i2c)    # newer CLUEs (Jan 2025)
# highest range for impacts!
sensor.accelerometer_range = AccelRange.RANGE_16G
# we'll read at about 1KHz
sensor.accelerometer_rate = Rate.RATE_1_66K_HZ
# Instead of raw accelerometer data, we'll read the *change* in acceleration (shock)
sensor.high_pass_filter = AccelHPF.SLOPE
sensor.high_pass_filter_enabled = True

# and make a lil buzzer
buzzer = pwmio.PWMOut(board.SPEAKER, variable_frequency=True)
buzzer.frequency = 1000

max_slope = 0
egg_ok = True
while True:
    # This isn't the acceleration but the SLOPE (change!) in acceleration
    x, y, z = sensor.acceleration
    # take the vector length by squaring, adding, taking root
    slope_g = math.sqrt(x*x + y*y + z*z) / 9.8  # take vector, convert to g
    # we'll track the max delta g

    if max_slope < slope_g:
        max_slope = slope_g
        print(slope_g)
        text_area.text = "Max Slope %0.1fg" % max_slope
        if max_slope >= 9 and egg_ok:
            gegg_sprite.x = 300
            time.sleep(0.1)
            egg_ok = False
            buzzer.duty_cycle = 2**15
            time.sleep(2)
            buzzer.duty_cycle = 0
            continue

    if button_a.value is False and egg_ok is False:
        print("Reset")
        time.sleep(0.1)  # debounce
        max_slope = 0
        gegg_sprite.x = 0
        egg_ok = True
