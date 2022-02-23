# SPDX-FileCopyrightText: 2018 Phillip Torrone for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import analogio
import board

light = analogio.AnalogIn(board.LIGHT)

while True:
    print((light.value,))
    time.sleep(0.1)
