# CircuitPlaygroundExpress_AnalogIn
# reads the on-board light sensor's analog voltage level
# and prints the results to REPL

from digitalio import DigitalInOut, Direction
from analogio import AnalogIn
import board
import time

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

analogin = AnalogIn(board.LIGHT)


def getVoltage(pin):  # helper 
    return (pin.value * 3.3) / 65536

while True:
    print("Analog Voltage: %f" % getVoltage(analogin))
    time.sleep(0.1)
