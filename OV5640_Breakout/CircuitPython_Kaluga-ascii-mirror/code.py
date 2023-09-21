# SPDX-FileCopyrightText: Copyright (c) 2021 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

"""
This demo is designed for the Kaluga development kit version 1.3.

To fix the MemoryError when creating a Camera object, Place the line
```toml
CIRCUITPY_RESERVED_PSRAM=1048576
```
in the file **CIRCUITPY/settings.toml** and restart.
"""

import sys

import board
import keypad
import displayio
import espcamera
import espidf

# The demo runs very slowly if the LCD display is enabled!
# It's intended to be viewed on the REPL on a host computer
displayio.release_displays()

if espidf.get_reserved_psram() < 1047586:
    print("""Place the following line in CIRCUITPY/settings.toml, then hard-reset the board:
CIRCUITPY_RESERVED_PSRAM=1048576
""")
    raise SystemExit

print("Initializing camera")
cam = espcamera.Camera(
    data_pins=board.CAMERA_DATA,
    external_clock_pin=board.CAMERA_XCLK,
    pixel_clock_pin=board.CAMERA_PCLK,
    vsync_pin=board.CAMERA_VSYNC,
    href_pin=board.CAMERA_HREF,
    pixel_format=espcamera.PixelFormat.GRAYSCALE,
    frame_size=espcamera.FrameSize.QQVGA,
    i2c=board.I2C(),
    external_clock_frequency=20_000_000,
    framebuffer_count=2)
print("initialized")

k = keypad.Keys([board.IO0], value_when_pressed=False)

chars = b" .:-=+*#%@"
remap = [chars[i * (len(chars) - 1) // 255] for i in range(256)]
width = cam.width
row = bytearray(width//2)

sys.stdout.write("\033[2J")

while True:
    if (e := k.events.get()) is not None and e.pressed:
        cam.colorbar = not cam.colorbar

    frame = cam.take(1)

    for j in range(0, cam.height, 5):
        sys.stdout.write(f"\033[{j//5}H")
        for i in range(cam.width // 2):
            row[i] =  remap[frame[width * j + 2 * i]]
        sys.stdout.write(row)
        sys.stdout.write("\033[K")
    sys.stdout.write("\033[J")
