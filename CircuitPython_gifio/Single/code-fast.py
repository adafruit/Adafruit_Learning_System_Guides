# SPDX-FileCopyrightText: 2023 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# Play a single animated GIF file (display_bus method)
#
# Documentation:
#   https://docs.circuitpython.org/en/latest/shared-bindings/gifio/
# Updated 3/29/2023

import time
import struct
import board
import gifio

display = board.DISPLAY
# Take over display to drive directly
display.auto_refresh = False
display_bus = display.bus

try:
    odg = gifio.OnDiskGif('/sample.gif')
except OSError:  # pylint: disable=broad-except, raise-missing-from
    raise Exception("sample.gif was not found\n")
start = time.monotonic()
next_delay = odg.next_frame()  # Load the first frame
end = time.monotonic()
overhead = end - start

# Display repeatedly & directly.
while True:
    # Sleep for the frame delay specified by the GIF,
    # minus the overhead measured to advance between frames.
    time.sleep(max(0, next_delay - overhead))
    next_delay = odg.next_frame()

    display_bus.send(42, struct.pack(">hh", 0, odg.bitmap.width - 1))
    display_bus.send(43, struct.pack(">hh", 0, odg.bitmap.height - 1))
    display_bus.send(44, odg.bitmap)
