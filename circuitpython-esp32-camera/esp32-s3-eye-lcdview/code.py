# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2021 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

"""
Use the built-in LCD as a viewfinder for the camera

This example requires:
 * ESP32-S3-EYE development kit from Espressif

To use:

Copy the project bundle to CIRCUITPY.
"""

import os
import struct
import time

import adafruit_ticks
import esp32_camera
import board
import displayio
from adafruit_st7789 import ST7789

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
    framebuffer_count=2,
    grab_mode=esp32_camera.GrabMode.WHEN_EMPTY)

cam.vflip = True

board.DISPLAY.auto_refresh = False
display_bus = board.DISPLAY.bus

display_bus.send(36, struct.pack(">hh", 0, 239))
display_bus.send(42, struct.pack(">hh", 0, 239))
display_bus.send(43, struct.pack(">hh", 0, 80+239))
t0 = adafruit_ticks.ticks_ms()
while True:
    frame = cam.take(1)
    if isinstance(frame, displayio.Bitmap):
        display_bus.send(44, frame)
        t1 = adafruit_ticks.ticks_ms()
        fps = 1000 / adafruit_ticks.ticks_diff(t1, t0)
        print(f"{fps:3.1f}fps")  # typically runs at about 25fps
        t0 = t1
