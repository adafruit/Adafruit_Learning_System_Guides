# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
from analogio import AnalogIn

analog_in = AnalogIn(board.A0)

while True:
    print(f"Soil Moisture: {analog_in.value}")
    time.sleep(5)
