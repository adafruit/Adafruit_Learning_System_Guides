# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Essentials Storage CP Filesystem boot.py file

REMOVE THIS LINE AND ALL TEXT BELOW BEFORE SUBMITTING TO GITHUB.
This file is specific to boards like ESP32-S2 where the boot button is used for bootloader and
safe mode, and therefore the button must be pressed at the right time to get into readonly mode.

There are two things to be updated in this file to match your board:
* Update OBJECT_PIN to match the pin name to which the button or pin is attached.
* Update UP_OR_DOWN to match the Pull necessary for the chosen pin.

For example:
If using the boot button on a QT Py ESP32-S2, OBJECT_PIN to BUTTON.

For example:
If using the boot button on a QT Py ESP32-S2, update UP_OR_DOWN to UP.
"""
import time
import board
import digitalio
import storage
import neopixel

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)

button = digitalio.DigitalInOut(board.OBJECT_PIN)
button.switch_to_input(pull=digitalio.Pull.UP_OR_DOWN)

# Turn the NeoPixel white for one second to indicate when to press the boot button.
pixel.fill((255, 255, 255))
time.sleep(1)

# If the button is connected to ground, the filesystem is writable by CircuitPython
storage.remount("/", readonly=button.value)
