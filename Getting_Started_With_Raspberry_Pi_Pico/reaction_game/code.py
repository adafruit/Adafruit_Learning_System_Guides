"""
Reaction game example for Pico. LED turns on for between 5 and 10 seconds. Once it turns off, try
to press the button as quickly as possible to measure reaction timm.

REQUIRED HARDWARE:
* LED on pin GP13.
* Button switch on pin GP14.
"""
import time
import random
import board
import digitalio

led = digitalio.DigitalInOut(board.GP13)
led.direction = digitalio.Direction.OUTPUT
button = digitalio.DigitalInOut(board.GP14)
button.switch_to_input(pull=digitalio.Pull.DOWN)

led.value = True
time.sleep(random.randint(5, 10))
led.value = False
timer_start = time.monotonic()
while True:
    if button.value:
        reaction_time = (time.monotonic() - timer_start) * 1000  # Convert to ms
        print("Your reaction time was", reaction_time, "milliseconds!")
        break
