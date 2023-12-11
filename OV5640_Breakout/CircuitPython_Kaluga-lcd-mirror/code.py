# SPDX-FileCopyrightText: Copyright (c) 2021 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

"""
This demo is designed for the Kaluga development kit version 1.3 with the
ILI9341 display. It requires CircuitPython 8.

To fix the MemoryError when creating a Camera object, Place the line
```toml
CIRCUITPY_RESERVED_PSRAM=1048576
```
in the file **CIRCUITPY/settings.toml** and restart.
"""

import struct

import board
import busio
import keypad
import displayio
import espcamera
import espidf

print("Initializing display")
displayio.release_displays()
spi = busio.SPI(MOSI=board.LCD_MOSI, clock=board.LCD_CLK)
display_bus = displayio.FourWire(
    spi,
    command=board.LCD_D_C,
    chip_select=board.LCD_CS,
    reset=board.LCD_RST,
    baudrate=80_000_000,
)
_INIT_SEQUENCE = (
    b"\x01\x80\x80"  # Software reset then delay 0x80 (128ms)
    b"\xEF\x03\x03\x80\x02"
    b"\xCF\x03\x00\xC1\x30"
    b"\xED\x04\x64\x03\x12\x81"
    b"\xE8\x03\x85\x00\x78"
    b"\xCB\x05\x39\x2C\x00\x34\x02"
    b"\xF7\x01\x20"
    b"\xEA\x02\x00\x00"
    b"\xc0\x01\x23"  # Power control VRH[5:0]
    b"\xc1\x01\x10"  # Power control SAP[2:0];BT[3:0]
    b"\xc5\x02\x3e\x28"  # VCM control
    b"\xc7\x01\x86"  # VCM control2
    b"\x36\x01\x40"  # Memory Access Control
    b"\x37\x01\x00"  # Vertical scroll zero
    b"\x3a\x01\x55"  # COLMOD: Pixel Format Set
    b"\xb1\x02\x00\x18"  # Frame Rate Control (In Normal Mode/Full Colors)
    b"\xb6\x03\x08\x82\x27"  # Display Function Control
    b"\xF2\x01\x00"  # 3Gamma Function Disable
    b"\x26\x01\x01"  # Gamma curve selected
    b"\xe0\x0f\x0F\x31\x2B\x0C\x0E\x08\x4E\xF1\x37\x07\x10\x03\x0E\x09\x00"  # Set Gamma
    b"\xe1\x0f\x00\x0E\x14\x03\x11\x07\x31\xC1\x48\x08\x0F\x0C\x31\x36\x0F"  # Set Gamma
    b"\x11\x80\x78"  # Exit Sleep then delay 0x78 (120ms)
    b"\x29\x80\x78"  # Display on then delay 0x78 (120ms)
)

display = displayio.Display(display_bus, _INIT_SEQUENCE, width=320, height=240)

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
    pixel_format=espcamera.PixelFormat.RGB565,
    frame_size=espcamera.FrameSize.QVGA,
    i2c=board.I2C(),
    external_clock_frequency=20_000_000,
    framebuffer_count=2)
print(cam.width, cam.height)
display.auto_refresh = False

k = keypad.Keys([board.IO0], value_when_pressed=False)

ow = (display.width - cam.width) // 2
oh = (display.height - cam.height) // 2
display_bus.send(42, struct.pack(">hh", ow, cam.width + ow - 1))
display_bus.send(43, struct.pack(">hh", oh, cam.height + ow - 1))

while True:
    if (e := k.events.get()) is not None and e.pressed:
        cam.colorbar = not cam.colorbar

    frame = cam.take(1)
    display_bus.send(44, frame)
