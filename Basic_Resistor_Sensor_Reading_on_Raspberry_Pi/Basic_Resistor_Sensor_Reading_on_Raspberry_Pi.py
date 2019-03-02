# Example for RC timing reading for Raspberry Pi
# using CircuitPython Libraries

import time
import board
from digitalio import DigitalInOut, Direction

def RCtime (RCpin):
    reading = 0

    # setup pin as output and direction low value
    rc = DigitalInOut(RCpin)
    rc.direction = Direction.OUTPUT
    rc.value = False

    time.sleep(0.1)

    # setup pin as input and wait for low value
    rc = DigitalInOut(RCpin)
    rc.direction = Direction.INPUT

    # This takes about 1 millisecond per loop cycle
    while rc.value is False:
        reading += 1
    return reading

while True:
    result = RCtime(board.D18)     # Read RC timing using pin #18
    print(result)
