# Trinket IO demo - analog inputs

from analogio import AnalogIn
import board
import time


analog0in = AnalogIn(board.D0)
analog1in = AnalogIn(board.D1)
analog2in = AnalogIn(board.D2)
analog3in = AnalogIn(board.D3)
analog4in = AnalogIn(board.D4)

def getVoltage(pin):
    return (pin.value * 3.3) / 65536

while True:
    print("A0: %0.2f \t A1: %0.2f \t A2: %0.2f \t A3: %0.2f \t A4: %0.2f" %
          (getVoltage(analog0in),
           getVoltage(analog1in),
           getVoltage(analog2in),
           getVoltage(analog3in),
           getVoltage(analog4in) ))
    time.sleep(0.1)
