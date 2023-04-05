# SPDX-FileCopyrightText: 2023 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# Play Multiple GIF files on a PyPortal
# Requires CircuitPython 8.1.0-beta.1 or later
# Updated 4/4/2023

import time
import gc
import os
import struct
import board
import gifio
import adafruit_touchscreen

# Get a dictionary of GIF filenames at the passed base directory
def get_files(base):
    files = os.listdir(base)
    file_names = []
    for _, filetext in enumerate(files):
        if not filetext.startswith("."):
            if filetext not in ('boot_out.txt', 'System Volume Information'):
                if filetext.endswith(".gif"):
                    file_names.append(filetext)
    return file_names

display = board.DISPLAY

# Take over display to drive directly
display.auto_refresh = False
display_bus = display.bus

# Pyportal has a touchscreen, a touch advances to next GIF file
WIDTH = board.DISPLAY.width
HEIGHT = board.DISPLAY.height
ts = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,
                                      board.TOUCH_YD, board.TOUCH_YU,
                                      calibration=((5200, 59000), (5800, 57000)),
                                      size=(WIDTH, HEIGHT))
files = get_files("/")
for i in range(len(files)):

    odg = gifio.OnDiskGif(files[i])
    # Skip Feather GIFs if put on PyPortal
    if odg.width != WIDTH:
        print("File "+files[i]+" not right width, skipping\n")
        continue

    start = time.monotonic()
    next_delay = odg.next_frame()  # Load the first frame
    end = time.monotonic()
    call_delay = end - start

    # Display GIF file frames until screen touched (for PyPortal)
    while True:
        sleeptime = max(0, next_delay - call_delay)
        time.sleep(sleeptime)
        if ts.touch_point is not None:
            break
        next_delay = odg.next_frame()
        display_bus.send(42, struct.pack(">hh", 0, odg.bitmap.width - 1))
        display_bus.send(43, struct.pack(">hh", 0, odg.bitmap.height - 1))
        display_bus.send(44, odg.bitmap)
    # End while
    # Clean up memory
    odg.deinit()
    odg = None
    gc.collect()
# End for
