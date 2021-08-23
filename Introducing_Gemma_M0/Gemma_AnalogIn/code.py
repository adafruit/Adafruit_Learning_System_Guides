# Gemma IO demo - analog inputs

import time

import board
from analogio import AnalogIn
from digitalio import DigitalInOut, Direction

led = DigitalInOut(board.L)
led.direction = Direction.OUTPUT

analog0in = AnalogIn(board.A0)
analog1in = AnalogIn(board.A1)
analog2in = AnalogIn(board.A2)


def getVoltage(pin):
    return (pin.value * 3.3) / 65536


while True:
    print("A0: %f \t\t A1: %f \t\t A2: %f" %
          (getVoltage(analog0in),
           getVoltage(analog1in),
           getVoltage(analog2in)))

    time.sleep(0.1)
