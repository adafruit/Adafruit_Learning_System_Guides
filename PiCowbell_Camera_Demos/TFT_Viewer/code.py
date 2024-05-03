# SPDX-FileCopyrightText: Copyright (c) 2023 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
This demo is designed for the Raspberry Pi Pico, Camera PiCowbell,
and ST7789 240x240 SPI TFT display

It shows the camera image on the LCD
"""

import time
import busio
import board
import digitalio
import adafruit_ov5640
import adafruit_st7789
import displayio

displayio.release_displays()
spi = busio.SPI(clock=board.GP18, MOSI=board.GP19)
display_bus = displayio.FourWire(spi, command=board.GP21, chip_select=board.GP17, reset=None)
display = adafruit_st7789.ST7789(display_bus, width=240, height=240, rowstart=80, rotation=0)

print("construct bus")
i2c = busio.I2C(board.GP5, board.GP4)
print("construct camera")
reset = digitalio.DigitalInOut(board.GP14)
cam = adafruit_ov5640.OV5640(
    i2c,
    data_pins=(
        board.GP6,
        board.GP7,
        board.GP8,
        board.GP9,
        board.GP10,
        board.GP11,
        board.GP12,
        board.GP13,
    ),
    clock=board.GP3,
    vsync=board.GP0,
    href=board.GP2,
    mclk=None,
    shutdown=None,
    reset=reset,
    size=adafruit_ov5640.OV5640_SIZE_240X240,
)
print("print chip id")
print(cam.chip_id)


cam.colorspace = adafruit_ov5640.OV5640_COLOR_RGB
cam.flip_y = False
cam.flip_x = False
cam.test_pattern = False

width = display.width
height = display.height

#cam.test_pattern = OV7670_TEST_PATTERN_COLOR_BAR_FADE
bitmap = displayio.Bitmap(cam.width, cam.height, 65535)
print(width, height, cam.width, cam.height)
if bitmap is None:
    raise SystemExit("Could not allocate a bitmap")

g = displayio.Group(scale=1, x=(width-cam.width)//2, y=(height-cam.height)//2)
tg = displayio.TileGrid(bitmap,
    pixel_shader=displayio.ColorConverter(input_colorspace=displayio.Colorspace.RGB565_SWAPPED)
)
g.append(tg)
display.root_group = g

t0 = time.monotonic_ns()
display.auto_refresh = False
while True:
    cam.capture(bitmap)
    bitmap.dirty()
    display.refresh(minimum_frames_per_second=0)
    t1 = time.monotonic_ns()
    print("fps", 1e9 / (t1 - t0))
    t0 = t1
