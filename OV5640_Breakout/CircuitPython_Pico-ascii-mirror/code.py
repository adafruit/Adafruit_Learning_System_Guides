# SPDX-FileCopyrightText: Copyright (c) 2023 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
This demo is designed for the Raspberry Pi Pico.

It shows the camera image as ASCII art on the USB REPL.
"""


import sys
import time
import busio
import board
import digitalio
import adafruit_ov5640

print("construct bus")
bus = busio.I2C(board.GP9, board.GP8)
print("construct camera")
reset = digitalio.DigitalInOut(board.GP10)
cam = adafruit_ov5640.OV5640(
    bus,
    data_pins=(
        board.GP12,
        board.GP13,
        board.GP14,
        board.GP15,
        board.GP16,
        board.GP17,
        board.GP18,
        board.GP19,
    ),
    clock=board.GP11,
    vsync=board.GP7,
    href=board.GP21,
    mclk=board.GP20,
    shutdown=None,
    reset=reset,
    size=adafruit_ov5640.OV5640_SIZE_QQVGA,
)
print("print chip id")
print(cam.chip_id)


cam.colorspace = adafruit_ov5640.OV5640_COLOR_YUV
cam.flip_y = True
cam.flip_x = True
cam.test_pattern = False

buf = bytearray(cam.capture_buffer_size)
chars = b" .':-+=*%$#"
remap = [chars[i * (len(chars) - 1) // 255] for i in range(256)]

width = cam.width
row = bytearray(width)

print("capturing")
cam.capture(buf)
print("capture complete")

sys.stdout.write("\033[2J")
while True:
    cam.capture(buf)
    for j in range(0, cam.height, 2):
        sys.stdout.write(f"\033[{j//2}H")
        for i in range(cam.width):
            row[i] = remap[buf[2 * (width * j + i)]]
        sys.stdout.write(row)
        sys.stdout.write("\033[K")
    sys.stdout.write("\033[J")
    time.sleep(0.1)
