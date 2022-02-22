# SPDX-FileCopyrightText: 2021 Brent Rubell for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
'squeeze.py'.

=================================================
force sensitive resistor (fsr) with circuitpython
"""

import analogio
import board
import pwmio

FORCE_SENS_RESISTOR = analogio.AnalogIn(board.A2)
LED = pwmio.PWMOut(board.D10)

while True:
    LED.duty_cycle = FORCE_SENS_RESISTOR.value
