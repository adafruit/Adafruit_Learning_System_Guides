# SPDX-FileCopyrightText: 2021 Brent Rubell for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
'photo_sensor.py'.

=================================================
uses LIGHT to control a LED
"""
import analogio
import board
import pwmio
from simpleio import map_range

LED = pwmio.PWMOut(board.D9)
LIGHT = analogio.AnalogIn(board.A0)


while True:
    LIGHT_VAL = map_range(LIGHT.value, 20000, 32766, 0, 32766)
    LED.duty_cycle = int(LIGHT_VAL)
