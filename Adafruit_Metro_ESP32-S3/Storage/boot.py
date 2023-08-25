# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Essentials Storage CP Filesystem boot.py file
"""
import board
import digitalio
import storage

pin = digitalio.DigitalInOut(board.A0)
pin.switch_to_input(pull=digitalio.Pull.UP)

# If the pin is connected to ground, the filesystem is writable by CircuitPython
storage.remount("/", readonly=pin.value)
