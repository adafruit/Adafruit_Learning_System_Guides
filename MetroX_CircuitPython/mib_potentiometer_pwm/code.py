# SPDX-FileCopyrightText: 2021 Brent Rubell for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
'mib_potentiometer_pwm.py'.

=================================================
fades a led using a potentiometer
"""

import analogio
import board
import pwmio

led = pwmio.PWMOut(board.D9)
pot = analogio.AnalogIn(board.A0)

while True:
    led.duty_cycle = pot.value
