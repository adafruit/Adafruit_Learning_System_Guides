# CircuitPython AnalogIn Demo

from analogio import AnalogIn
import board
import time

analog1in = AnalogIn(board.A1)  # For Gemma M0, Metro M0 Exp, Feather M0 Exp, ItsyBitsy M0 Exp, CPX
# analog1in = AnalogIn(board.D1)  # For Trinket M0


def get_voltage(pin):
    return (pin.value * 3.3) / 65536


while True:
    print("A1: %f" % (get_voltage(analog1in)))
    time.sleep(0.1)
