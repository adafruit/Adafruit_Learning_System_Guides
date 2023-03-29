# SPDX-FileCopyrightText: 2023 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# Documentation:
#   https://docs.circuitpython.org/en/latest/shared-bindings/gifio/
# Updated 3/29/2023
import board
import gifio
import displayio
import time

display = board.DISPLAY
splash = displayio.Group()
display.root_group = splash

try:
    odg = gifio.OnDiskGif('/sample.gif')
except OSError:  # pylint: disable=broad-except
    raise Exception("sample.gif was not found\n")
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

# Play the GIF file forever
while True:
    time.sleep(max(0, next_delay - call_delay))
    next_delay = odg.next_frame()
