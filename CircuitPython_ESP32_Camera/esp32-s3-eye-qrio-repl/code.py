# SPDX-FileCopyrightText: Copyright (c) 2021 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

"""
This demo is designed for the Kaluga development kit version 1.3 with the
ILI9341 display.
"""

import struct
import board
import esp32_camera
import qrio

print("Initializing camera")
cam = esp32_camera.Camera(
    data_pins=board.CAMERA_DATA,
    external_clock_pin=board.CAMERA_XCLK,
    pixel_clock_pin=board.CAMERA_PCLK,
    vsync_pin=board.CAMERA_VSYNC,
    href_pin=board.CAMERA_HREF,
    pixel_format=esp32_camera.PixelFormat.RGB565,
    frame_size=esp32_camera.FrameSize.R240X240,
    i2c=board.I2C(),
    external_clock_frequency=20_000_000,
    framebuffer_count=2)
cam.vflip = True
cam.hmirror = True

board.DISPLAY.auto_refresh = False
display_bus = board.DISPLAY.bus

print(cam.width, cam.height)
qrdecoder = qrio.QRDecoder(cam.width, cam.height)

print(qrdecoder.width, qrdecoder.height)
#raise SystemExit

ow = (board.DISPLAY.width - cam.width) // 2
oh = (board.DISPLAY.height - cam.height) // 2
display_bus.send(42, struct.pack(">hh", ow, cam.width + ow - 1))
display_bus.send(43, struct.pack(">hh", oh, cam.height + ow - 1))

while True:
    frame = cam.take(1)
    display_bus.send(44, frame)
    for row in qrdecoder.decode(memoryview(frame), qrio.PixelPolicy.RGB565_SWAPPED):
        payload = row.payload
        try:
            payload = payload.decode("utf-8")
        except UnicodeError:
            payload = str(payload)
        print(payload)
    print(end=".")
