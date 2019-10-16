# Circuit Playground digitalio example

import time
import board
import digitalio

led = digitalio.DigitalInOut(board.D13)
led.switch_to_output()

button = digitalio.DigitalInOut(board.BUTTON_A)
button.switch_to_input(pull=digitalio.Pull.DOWN)

while True:
    if button.value:  # button is pushed
        led.value = True
    else:
        led.value = False

    time.sleep(0.01)
