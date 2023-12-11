# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Essentials Storage CP Filesystem boot.py file
"""
import time
import board
import digitalio
import storage
import neopixel

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)

button = digitalio.DigitalInOut(board.BUTTON)
button.switch_to_input(pull=digitalio.Pull.UP)

# Turn the NeoPixel white for one second to indicate when to press the boot button.
pixel.fill((255, 255, 255))
time.sleep(1)

# If the button is connected to ground, the filesystem is writable by CircuitPython
storage.remount("/", readonly=button.value)
