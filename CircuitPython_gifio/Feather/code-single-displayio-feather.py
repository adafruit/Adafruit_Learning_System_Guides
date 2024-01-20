# SPDX-FileCopyrightText: 2023 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# Play a single animated GIF file (display_bus "fast" method)
#
# Documentation:
#   https://docs.circuitpython.org/en/latest/shared-bindings/gifio/
# Updated 4/5/2023

import time
import gc
import board
import gifio
import digitalio
import displayio

display = board.DISPLAY
splash = displayio.Group()
display.root_group = splash

# Set BOOT button on ESP32-S2 Feather TFT to stop GIF
button = digitalio.DigitalInOut(board.BUTTON)
button.switch_to_input(pull=digitalio.Pull.UP)

# Open GIF file sample.gif
odg = gifio.OnDiskGif('/sample.gif')

start = time.monotonic()
next_delay = odg.next_frame()  # Load the first frame
end = time.monotonic()
overhead = end - start

face = displayio.TileGrid(
    odg.bitmap,
    pixel_shader=displayio.ColorConverter(
        input_colorspace=displayio.Colorspace.RGB565_SWAPPED
    ),
)
splash.append(face)
board.DISPLAY.refresh()

# Display repeatedly & directly.
while True:
    # Sleep for the frame delay specified by the GIF,
    # minus the overhead measured to advance between frames.
    time.sleep(max(0, next_delay - overhead))
    # If the BOOT button is pressed, stop the GIF
    if button.value is False:
        print("Button Press, Stop\n")
        break
    next_delay = odg.next_frame()
# End While - cleanup memory
odg.deinit()
odg = None
gc.collect()
