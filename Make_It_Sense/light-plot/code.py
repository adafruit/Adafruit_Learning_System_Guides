# SPDX-FileCopyrightText: 2018 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import analogio
import board

# Create the light sensor object to read from
light = analogio.AnalogIn(board.LIGHT)

# Do readings, be sure to pause between readings
while True:
    print((light.value, ))
    time.sleep(0.1)
