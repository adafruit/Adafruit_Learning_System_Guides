# SPDX-FileCopyrightText: 2020 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Check for connection between pin and GND on hard boot (power-on or reset).
If NO connection: storage is remounted as read/write so the light painter
code can run (it requires temporary files), but code.py can't be edited.
If connected: storage is left in read-only mode. Light painter code can't
run but files are editable.
"""

# pylint: disable=import-error
import board
import digitalio
import storage

PIN = board.D0

IO = digitalio.DigitalInOut(PIN)
IO.direction = digitalio.Direction.INPUT
IO.pull = digitalio.Pull.UP

if IO.value:                             # No connection
    storage.remount('/', readonly=False) # Remount storage as read/write for painter
