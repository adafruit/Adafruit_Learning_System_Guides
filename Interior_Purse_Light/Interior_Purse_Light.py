import time

import board
from digitalio import DigitalInOut, Direction, Pull

button = DigitalInOut(board.D1)
button.direction = Direction.INPUT
button.pull = Pull.UP

led = DigitalInOut(board.D2)
led.direction = Direction.OUTPUT

while True:
    if button.value:
        led.value = True  # check if the pushbutton is pressed.
    else:
        led.value = False  # turn LED off

    time.sleep(0.01)  # debounce delay
