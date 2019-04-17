import time
import board
from digitalio import DigitalInOut, Direction

pad_pin = board.D23

pad = DigitalInOut(pad_pin)
pad.direction = Direction.INPUT

already_pressed = False

while True:

    if pad.value and not already_pressed:
        print("pressed")

    already_pressed = pad.value
    time.sleep(0.1)
