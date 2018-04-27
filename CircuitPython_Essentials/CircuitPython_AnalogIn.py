# CircuitPython AnalogIn Demo

import time
from analogio import AnalogIn
import board

analog_in = AnalogIn(board.A1)


def get_voltage(pin):
    return (pin.value * 3.3) / 65536


while True:
    print((get_voltage(analog_in),))
    time.sleep(0.1)
