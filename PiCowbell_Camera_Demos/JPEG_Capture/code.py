# SPDX-FileCopyrightText: Copyright (c) 2023 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
This demo is designed for the Raspberry Pi Pico and Camera PiCowbell

It take an image when the shutter button is pressed and saves it to
the microSD card.
"""

import os
import time
import busio
import board
import digitalio
import adafruit_ov5640
import keypad
import sdcardio
import storage

print("Initializing SD card")
sd_spi = busio.SPI(clock=board.GP18, MOSI=board.GP19, MISO=board.GP16)
sd_cs = board.GP17
sdcard = sdcardio.SDCard(sd_spi, sd_cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

print("construct bus")
i2c = busio.I2C(board.GP5, board.GP4)
print("construct camera")
reset = digitalio.DigitalInOut(board.GP14)
cam = adafruit_ov5640.OV5640(
    i2c,
    data_pins=(
        board.GP6,
        board.GP7,
        board.GP8,
        board.GP9,
        board.GP10,
        board.GP11,
        board.GP12,
        board.GP13,
    ),
    clock=board.GP3,
    vsync=board.GP0,
    href=board.GP2,
    mclk=None,
    shutdown=None,
    reset=reset,
    size=adafruit_ov5640.OV5640_SIZE_VGA,
)
print("print chip id")
print(cam.chip_id)

keys = keypad.Keys((board.GP22,), value_when_pressed=False, pull=True)

def exists(filename):
    try:
        os.stat(filename)
        return True
    except OSError as _:
        return False


_image_counter = 0


def open_next_image():
    global _image_counter  # pylint: disable=global-statement
    while True:
        filename = f"/sd/img{_image_counter:04d}.jpg"
        _image_counter += 1
        if exists(filename):
            continue
        print("# writing to", filename)
        return open(filename, "wb")

cam.colorspace = adafruit_ov5640.OV5640_COLOR_JPEG
cam.quality = 3
b = bytearray(cam.capture_buffer_size)
jpeg = cam.capture(b)

while True:
    shutter = keys.events.get()
    # event will be None if nothing has happened.
    if shutter:
        if shutter.pressed:
            time.sleep(0.01)
            jpeg = cam.capture(b)
            print(f"Captured {len(jpeg)} bytes of jpeg data")
            print(f" (had allocated {cam.capture_buffer_size} bytes")
            print(f"Resolution {cam.width}x{cam.height}")
            try:
                with open_next_image() as f:
                    f.write(jpeg)
                print("# Wrote image")
            except OSError as e:
                print(e)
