# SPDX-FileCopyrightText: Copyright (c) 2023 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

"""
This demo is designed for the Kaluga development kit version 1.3 with the
ILI9341 display. It requires CircuitPython 8.

This demo needs reserved psram properly configured in settings.toml:
CIRCUITPY_RESERVED_PSRAM=1048576

This example also requires an SD card breakout wired as follows:
 * IO18: SD Clock Input
 * IO17: SD Serial Output (MISO)
 * IO14: SD Serial Input (MOSI)
 * IO12: SD Chip Select

Insert a CircuitPython-compatible SD card before powering on the Kaluga.
Press the "BOOT" button to take a photo in BMP format.
"""

import os
import ssl
import struct

import board
import busio
import displayio
import espcamera
import espidf
import keypad
import sdcardio
import socketpool
import storage

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

print("Initializing SD card")
sd_spi = busio.SPI(clock=board.IO18, MOSI=board.IO14, MISO=board.IO17)
sd_cs = board.IO12
sdcard = sdcardio.SDCard(sd_spi, sd_cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

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
    framebuffer_count=1)
print("initialized")
display.auto_refresh = False

def exists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False


_image_counter = 0


def open_next_image(extension="jpg"):
    global _image_counter  # pylint: disable=global-statement
    while True:
        filename = f"/sd/img{_image_counter:04d}.{extension}"
        _image_counter += 1
        if exists(filename):
            continue
        print("#", filename)
        return open(filename, "wb")  # pylint: disable=consider-using-with

ow = (display.width - cam.width) // 2
oh = (display.height - cam.height) // 2

k = keypad.Keys([board.IO0], value_when_pressed=False)

while True:
    frame = cam.take(1)
    display_bus.send(42, struct.pack(">hh", ow, cam.width + ow - 1))
    display_bus.send(43, struct.pack(">hh", oh, cam.height + ow - 1))
    display_bus.send(44, frame)
    if (e := k.events.get()) is not None and e.pressed:
        cam.reconfigure(
            pixel_format=espcamera.PixelFormat.JPEG,
            frame_size=espcamera.FrameSize.SVGA,
        )
        frame = cam.take(1)
        if isinstance(frame, memoryview):
            jpeg = frame
            print(f"Captured {len(jpeg)} bytes of jpeg data")

            with open_next_image() as f:
                f.write(jpeg)
        cam.reconfigure(
            pixel_format=espcamera.PixelFormat.RGB565,
            frame_size=espcamera.FrameSize.QVGA,
        )

