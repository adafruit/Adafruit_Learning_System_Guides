"""
Button example for Pico. Prints message to serial console when button is pressed.

REQUIRED HARDWARE:
* Button switch on pin GP13.
"""
import time
import board
import digitalio

button = digitalio.DigitalInOut(board.GP13)
button.switch_to_input(pull=digitalio.Pull.DOWN)

while True:
    if button.value:
        print("You pressed the button!")
        time.sleep(0.5)
