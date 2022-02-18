# SPDX-FileCopyrightText: 2019 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import storage
from analogio import AnalogIn

def read_buttons():
    with AnalogIn(board.A3) as ain:
        reading = ain.value / 65535
        if reading > 0.75:
            return None
        if reading > 0.4:
            return 4
        if reading > 0.25:
            return 3
        if reading > 0.13:
            return 2
        return 1

readonly = True
# if a button is pressed while booting up, CircuitPython can write to the drive
button = read_buttons()
if button != None:
    readonly = False
if readonly:
    print("OS has write access to CircuitPython drive")
else:
    print("CircuitPython has write access to drive")
storage.remount("/", readonly)
