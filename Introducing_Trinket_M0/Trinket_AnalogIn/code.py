# SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Trinket IO demo - analog inputs

import time

import board
from analogio import AnalogIn

analog0in = AnalogIn(board.D0)
analog1in = AnalogIn(board.D1)
analog2in = AnalogIn(board.D2)
analog3in = AnalogIn(board.D3)
analog4in = AnalogIn(board.D4)


def getVoltage(pin):
    return (pin.value * 3.3) / 65536


while True:
    print("D0: %0.2f \t D1: %0.2f \t D2: %0.2f \t D3: %0.2f \t D4: %0.2f" %
          (getVoltage(analog0in),
           getVoltage(analog1in),
           getVoltage(analog2in),
           getVoltage(analog3in),
           getVoltage(analog4in)))
    time.sleep(0.1)
