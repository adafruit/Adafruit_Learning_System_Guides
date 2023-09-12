# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
This test will initialize the display using displayio and display
a bitmap image. The image advances when the touch screen is touched.

Pinouts are for the 2.8" TFT Shield
"""
import os
import board
import displayio
import adafruit_ili9341
import adafruit_tsc2007

# Release any resources currently in use for the displays
displayio.release_displays()

# Use Hardware SPI
spi = board.SPI()

# Use Software SPI if you have a shield with pins 11-13 jumpered
# import busio
# spi = busio.SPI(board.D11, board.D13)

tft_cs = board.D10
tft_dc = board.D9

display_width = 320
display_height = 240

display_bus = displayio.FourWire(spi, command=tft_dc, chip_select=tft_cs)
display = adafruit_ili9341.ILI9341(display_bus, width=display_width, height=display_height)

i2c = board.I2C()

irq_dio = None
tsc = adafruit_tsc2007.TSC2007(i2c, irq=irq_dio)

groups = []
images = []
for filename in os.listdir('/'):
    if filename.lower().endswith('.bmp') and not filename.startswith('.'):
        images.append("/"+filename)
print(images)

for i in range(len(images)):
    splash = displayio.Group()
    bitmap = displayio.OnDiskBitmap(images[i])
    tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
    splash.append(tile_grid)
    groups.append(splash)

index = 0
touch_state = False

display.show(groups[index])
while True:
    if tsc.touched and not touch_state:
        point = tsc.touch
        touch_state = True
        if point["pressure"] < 200:  # ignore touches with no 'pressure' as false
            continue
        print("Touchpoint: (%d, %d, %d)" % (point["x"], point["y"], point["pressure"]))
        # left side of the screen
        if point["y"] < 2000:
            index = (index - 1) % len(images)
            display.show(groups[index])
        # right side of the screen
        else:
            index = (index + 1) % len(images)
            display.show(groups[index])
    if not tsc.touched and touch_state:
        touch_state = False
