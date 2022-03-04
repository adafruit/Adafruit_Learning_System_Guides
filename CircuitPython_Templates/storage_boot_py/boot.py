# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Essentials Storage CP Filesystem boot.py file

REMOVE THIS LINE AND ALL TEXT BELOW BEFORE SUBMITTING TO GITHUB.
There are three things to be updated in this file to match your board:
* Update OBJECT_NAME to match the physical thing you are using, e.g. button or pin.
* Update OBJECT_PIN to match the pin name to which the button or pin is attached.
* Update UP_OR_DOWN to match the Pull necessary for the chosen pin.

For example:
If using the up button on a FunHouse, update OBJECT_NAME to button, and OBJECT_PIN to BUTTON_UP.
If using pin A0 on a Feather RP2040, update OBJECT_NAME to pin, and OBJECT_PIN to A0.

For example:
If using the up button on a FunHouse, update UP_OR_DOWN to DOWN.
IF using pin A0 on a Feather RP2040, update UP_OR_DOWN to UP.
"""
import board
import digitalio
import storage

OBJECT_NAME = digitalio.DigitalInOut(board.OBJECT_PIN)
OBJECT_NAME.switch_to_input(pull=digitalio.Pull.UP_OR_DOWN)

# If the OBJECT_NAME is connected to ground, the filesystem is writable by CircuitPython
storage.remount("/", readonly=OBJECT_NAME.value)
