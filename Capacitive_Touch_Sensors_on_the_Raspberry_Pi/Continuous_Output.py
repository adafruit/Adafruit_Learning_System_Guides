import time
import board
from digitalio import DigitalInOut, Direction

pad_pin = board.D23

pad = DigitalInOut(pad_pin)
pad.direction = Direction.INPUT

while True:

    if pad.value:
        print("pressed")

    time.sleep(0.1)
