# SPDX-FileCopyrightText: 2019 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import digitalio

relay = digitalio.DigitalInOut(board.A1)
relay.direction = digitalio.Direction.OUTPUT

while True:
    relay.value = True
    time.sleep(1)
    relay.value = False
    time.sleep(1)
