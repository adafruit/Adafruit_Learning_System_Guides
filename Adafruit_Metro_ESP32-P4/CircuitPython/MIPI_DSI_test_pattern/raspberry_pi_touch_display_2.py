# SPDX-FileCopyrightText: Copyright (c) 2022 Raspberry Pi Ltd.
#
# SPDX-License-Identifier: GPL-2.0-only
# Raspberry Pi Touch Display 2 (7-inch), ILI9881C initialization.
# Register sequence from the Raspberry Pi Linux panel-ilitek-ili9881c driver:
# Copyright (C) 2017-2018 Bootlin; 2021 Henson Li and Penk Chen;
# 2022 Mark Williams. MCU protocol: Copyright (C) 2022 Raspberry Pi Ltd.
# https://github.com/raspberrypi/linux/blob/rpi-6.12.y/drivers/gpu/drm/panel/panel-ilitek-ili9881c.c
# Adapted for CircuitPython on Metro ESP32-P4.

import time
import framebufferio
import mipidsi

_INIT_SEQUENCE = bytes.fromhex(
    "ff 03 98 81 03 01 01 00 02 01 00 03 01 73 04 01 00 05 01 00 06 01 0a 07"
    "01 00 08 01 00 09 01 61 0a 01 00 0b 01 00 0c 01 01 0d 01 00 0e 01 00 0f"
    "01 61 10 01 61 11 01 00 12 01 00 13 01 00 14 01 00 15 01 00 16 01 00 17"
    "01 00 18 01 00 19 01 00 1a 01 00 1b 01 00 1c 01 00 1d 01 00 1e 01 40 1f"
    "01 80 20 01 06 21 01 01 22 01 00 23 01 00 24 01 00 25 01 00 26 01 00 27"
    "01 00 28 01 33 29 01 03 2a 01 00 2b 01 00 2c 01 00 2d 01 00 2e 01 00 2f"
    "01 00 30 01 00 31 01 00 32 01 00 33 01 00 34 01 04 35 01 00 36 01 00 37"
    "01 00 38 01 3c 39 01 00 3a 01 00 3b 01 00 3c 01 00 3d 01 00 3e 01 00 3f"
    "01 00 40 01 00 41 01 00 42 01 00 43 01 00 44 01 00 50 01 10 51 01 32 52"
    "01 54 53 01 76 54 01 98 55 01 ba 56 01 10 57 01 32 58 01 54 59 01 76 5a"
    "01 98 5b 01 ba 5c 01 dc 5d 01 fe 5e 01 00 5f 01 0e 60 01 0f 61 01 0c 62"
    "01 0d 63 01 06 64 01 07 65 01 02 66 01 02 67 01 02 68 01 02 69 01 01 6a"
    "01 00 6b 01 02 6c 01 15 6d 01 14 6e 01 02 6f 01 02 70 01 02 71 01 02 72"
    "01 02 73 01 02 74 01 02 75 01 0e 76 01 0f 77 01 0c 78 01 0d 79 01 06 7a"
    "01 07 7b 01 02 7c 01 02 7d 01 02 7e 01 02 7f 01 01 80 01 00 81 01 02 82"
    "01 14 83 01 15 84 01 02 85 01 02 86 01 02 87 01 02 88 01 02 89 01 02 8a"
    "01 02 ff 03 98 81 04 6c 01 15 6e 01 2a 6f 01 33 3b 01 98 3a 01 94 8d 01"
    "14 87 01 ba 26 01 76 b2 01 d1 b5 01 06 38 01 01 39 01 00 ff 03 98 81 01"
    "22 01 0a 31 01 00 53 01 7d 55 01 8f 40 01 33 50 01 96 51 01 96 60 01 23"
    "a0 01 08 a1 01 1d a2 01 2a a3 01 10 a4 01 15 a5 01 28 a6 01 1c a7 01 1d"
    "a8 01 7e a9 01 1d aa 01 29 ab 01 6b ac 01 1a ad 01 18 ae 01 4b af 01 20"
    "b0 01 27 b1 01 50 b2 01 64 b3 01 39 c0 01 08 c1 01 1d c2 01 2a c3 01 10"
    "c4 01 15 c5 01 28 c6 01 1c c7 01 1d c8 01 7e c9 01 1d ca 01 29 cb 01 6b"
    "cc 01 1a cd 01 18 ce 01 4b cf 01 20 d0 01 27 d1 01 50 d2 01 64 d3 01 39"
    "ff 03 98 81 00 35 01 00 11 80 78 29 00"
)


def make_display(i2c):
    """Initialize the 7-inch Touch Display 2 at 1280 x 720 landscape."""
    while not i2c.try_lock():
        pass
    try:
        # The display MCU requires a STOP and delay before register reads.
        i2c.writeto(0x45, bytes((1,)))
        time.sleep(0.005)
        identity = bytearray(1)
        i2c.readfrom_into(0x45, identity)
        if identity[0] & 15 not in (1, 4):
            raise RuntimeError("Connect the 7-inch Raspberry Pi Touch Display 2")
        print("Display controller ID:", hex(identity[0]))
        i2c.writeto(0x45, bytes((3, 0)))
        i2c.writeto(0x45, bytes((2, 0)))
        time.sleep(0.02)
        bus = mipidsi.Bus(frequency=1_000_000_000, num_lanes=2)
        i2c.writeto(0x45, bytes((2, 3)))
        time.sleep(0.02)
        framebuffer = mipidsi.Display(
            bus, _INIT_SEQUENCE,
            width=720, height=1280, color_depth=24,
            hsync_pulse_width=33, hsync_back_porch=50, hsync_front_porch=239,
            vsync_pulse_width=2, vsync_back_porch=30, vsync_front_porch=20,
            pixel_clock_frequency=83_330_000, native_frames_per_second=60,
        )
        display = framebufferio.FramebufferDisplay(framebuffer, rotation=90)
        i2c.writeto(0x45, bytes((3, 0x88)))
        return display
    finally:
        i2c.unlock()
