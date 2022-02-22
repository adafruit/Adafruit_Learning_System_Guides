# SPDX-FileCopyrightText: 2021 Brent Rubell for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
'temperature_alarm.py'.

=================================================
sounds an alarm when the temperature crosses a threshold
requires:
- simpleio
"""

import time
import analogio
import board
from simpleio import map_range, tone

tmp_36 = analogio.AnalogIn(board.A0)

freeze_temp = 0
boil_temp = 100

while True:
    temp = map_range(tmp_36.value, 0, 65535, 0, 5)
    # temp to degrees C
    temp = (temp - 0.5) * 100
    print(temp)

    if temp < freeze_temp:
        tone(board.D8, 349, 4)
    if temp > boil_temp:
        tone(board.D8, 523, 4)
    time.sleep(0.5)
