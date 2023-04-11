# SPDX-FileCopyrightText: 2023 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# Play Multiple GIF files on an ESP32-S2 Feather TFT
# Requires CircuitPython 8.1.0-beta.1 or later
# Updated 4/4/2023

import time
import gc
import os
import struct
import board
import gifio
import digitalio

# Get a dictionary of GIF filenames at the passed base directory
def get_files(base):
    allfiles = os.listdir(base)
    file_names = []
    for _, filetext in enumerate(allfiles):
        if not filetext.startswith("."):
            if filetext not in ('boot_out.txt', 'System Volume Information'):
                if filetext.endswith(".gif"):
                    file_names.append(filetext)
    return file_names

# Set BOOT button on ESP32-S2 Feather TFT to advance to next GIF
button = digitalio.DigitalInOut(board.BUTTON)
button.switch_to_input(pull=digitalio.Pull.UP)

display = board.DISPLAY
display.auto_refresh = False

COL_OFFSET = 40  # The Feather TFT needs to have the display
ROW_OFFSET = 53  # offset by these values for direct writes

files = get_files("/")
for i in range(len(files)):

    odg = gifio.OnDiskGif(files[i])
    # Skip PyPortal GIFs if put on ESP32-S2 Feather TFT
    if odg.width != board.DISPLAY.width:
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
        # If the BOOT button is pressed, advance to next GIF file
        if button.value is False:
            print("Button Press, Advance\n")
            break
        next_delay = odg.next_frame()
        display.bus.send(42, struct.pack(">hh", COL_OFFSET,
                         odg.bitmap.width - 1 + COL_OFFSET))
        display.bus.send(43, struct.pack(">hh", ROW_OFFSET,
                         odg.bitmap.height - 1 + ROW_OFFSET))
        display.bus.send(44, odg.bitmap)
    # End while
    # Clean up memory
    odg.deinit()
    odg = None
    gc.collect()
# End for
