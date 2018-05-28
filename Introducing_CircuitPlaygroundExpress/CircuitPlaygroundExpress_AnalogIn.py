# CircuitPlaygroundExpress_AnalogIn
# reads the analog voltage level from a 10k potentiometer
# connected to GND, 3.3V, and pin A1
# and prints the results to the REPL

import time

import board
from analogio import AnalogIn

analogin = AnalogIn(board.A1)


def getVoltage(pin):  # helper
    return (pin.value * 3.3) / 65536


while True:
    print("Analog Voltage: %f" % getVoltage(analogin))
    time.sleep(0.1)
