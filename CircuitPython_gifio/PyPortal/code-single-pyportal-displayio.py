# SPDX-FileCopyrightText: 2023 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# gifio demo for the Adafruit PyPortal - single file
#
# Documentation:
#   https://docs.circuitpython.org/en/latest/shared-bindings/gifio/
# Updated 4/5/2023
#
import time
import gc
import board
import gifio
import displayio
import adafruit_touchscreen

display = board.DISPLAY
splash = displayio.Group()
display.root_group = splash

# Pyportal has a touchscreen, a touch stops the display
WIDTH = board.DISPLAY.width
HEIGHT = board.DISPLAY.height
ts = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,
                                      board.TOUCH_YD, board.TOUCH_YU,
                                      calibration=((5200, 59000), (5800, 57000)),
                                      size=(WIDTH, HEIGHT))

odg = gifio.OnDiskGif('/sample.gif')

start = time.monotonic()
next_delay = odg.next_frame()  # Load the first frame
end = time.monotonic()
call_delay = end - start

# Depending on your display the next line may need Colorspace.RGB565
#   instead of Colorspace.RGB565_SWAPPED
face = displayio.TileGrid(odg.bitmap,
                          pixel_shader=displayio.ColorConverter
                          (input_colorspace=displayio.Colorspace.RGB565_SWAPPED))
splash.append(face)
board.DISPLAY.refresh()

# Play the GIF file until screen is touched
while True:
    time.sleep(max(0, next_delay - call_delay))
    next_delay = odg.next_frame()
    if ts.touch_point is not None:
        break
# End while
# Clean up memory
odg.deinit()
odg = None
gc.collect()
