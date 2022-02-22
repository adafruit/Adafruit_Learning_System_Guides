# SPDX-FileCopyrightText: 2021 Brent Rubell for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
'mib_potentiometer_THRESHOLD.py'.

=================================================
turns on a LED when the potentiometer is above a half-turn
"""
import analogio
import board
import digitalio

LED = digitalio.DigitalInOut(board.D13)
LED.switch_to_output()
POT = analogio.AnalogIn(board.A0)

THRESHOLD = 512

while True:
    if POT.value > THRESHOLD:
        LED.value = True
    else:
        LED.value = False
