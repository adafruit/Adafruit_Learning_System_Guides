# SPDX-FileCopyrightText: 2019 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import os
import board
import digitalio

button = digitalio.DigitalInOut(board.D18)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

while True:

    if not button.value:
        os.system("date '+%I:%M %P' | festival --tts")

    # slight pause to debounce
    time.sleep(0.2)
