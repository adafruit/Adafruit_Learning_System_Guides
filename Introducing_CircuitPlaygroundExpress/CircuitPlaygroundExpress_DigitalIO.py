# CircuitPlaygroundExpress_DigitalIO

from digitalio import DigitalInOut, Direction, Pull
import board
import time

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

button = DigitalInOut(board.BUTTON_A)
button.direction = Direction.INPUT
button.pull = Pull.DOWN

while True:
    if button.value == True:  # button is pushed
        led.value = True
    else:
        led.value = False

    time.sleep(0.01)
