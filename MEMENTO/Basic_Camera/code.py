# SPDX-FileCopyrightText: Copyright (c) 2023 john park for Adafruit Industries
#
# SPDX-License-Identifier: MIT
""" 
simple point-and-shoot camera example. No bells! Zero whistles!

Requires libraries from the Adafruit CircuitPython Library Bundle.
Download the bundle from circuitpython.org/libraries and copy the
following files/folders to your CIRCUITPY/lib folder:
* adafruit_display_text
* adafruit_register
* adafruit_aw9523.mpy
* adafruit_debouncer.mpy
* adafruit_lis3dh.mpy
* adafruit_ticks.mpy
* neopixel.mpy

Once the libraries are copied, save this file as code.py to your CIRCUITPY
drive to run it.
"""

import time
import adafruit_pycamera # pylint: disable=import-error

pycam = adafruit_pycamera.PyCamera()
pycam.mode = 0  # only mode 0 (JPEG) will work in this example

# User settings - try changing these:
pycam.resolution = 8    # 0-12 preset resolutions:
#                      0: 240x240, 1: 320x240, 2: 640x480, 3: 800x600, 4: 1024x768,
#                      5: 1280x720, 6: 1280x1024, 7: 1600x1200, 8: 1920x1080, 9: 2048x1536,
#                      10: 2560x1440, 11: 2560x1600, 12: 2560x1920
pycam.led_level = 1  # 0-4 preset brightness levels
pycam.led_color = 0  # 0-7  preset colors: 0: white, 1: green, 2: yellow, 3: red,
#                                          4: pink, 5: blue, 6: teal, 7: rainbow
pycam.effect = 0  # 0-7 preset FX: 0: normal, 1: invert, 2: b&w, 3: red,
#                                  4: green, 5: blue, 6: sepia, 7: solarize

print("Simple camera ready.")
pycam.tone(800, 0.1)
pycam.tone(1200, 0.05)

while True:
    pycam.blit(pycam.continuous_capture())
    pycam.keys_debounce()

    if pycam.shutter.short_count:
        print("Shutter released")
        pycam.tone(1200, 0.05)
        pycam.tone(1600, 0.05)
        try:
            pycam.display_message("snap", color=0x00DD00)
            pycam.capture_jpeg()
            pycam.live_preview_mode()
        except TypeError as exception:
            pycam.display_message("Failed", color=0xFF0000)
            time.sleep(0.5)
            pycam.live_preview_mode()
        except RuntimeError as exception:
            pycam.display_message("Error\nNo SD Card", color=0xFF0000)
            time.sleep(0.5)

    if pycam.card_detect.fell:
        print("SD card removed")
        pycam.unmount_sd_card()
        pycam.display.refresh()

    if pycam.card_detect.rose:
        print("SD card inserted")
        pycam.display_message("Mounting\nSD Card", color=0xFFFFFF)
        for _ in range(3):
            try:
                print("Mounting card")
                pycam.mount_sd_card()
                print("Success!")
                break
            except OSError as exception:
                print("Retrying!", exception)
                time.sleep(0.5)
        else:
            pycam.display_message("SD Card\nFailed!", color=0xFF0000)
            time.sleep(0.5)
        pycam.display.refresh()
