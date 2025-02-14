# SPDX-FileCopyrightText: 2022 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Multiple Button Digital Input Example - Handling multiple buttons with simple logic.
"""
import time
import board
import digitalio

# LED setup
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

# Button setup
button0 = digitalio.DigitalInOut(board.D0)
button0.switch_to_input(pull=digitalio.Pull.UP)

button1 = digitalio.DigitalInOut(board.D1)
button1.switch_to_input(pull=digitalio.Pull.DOWN)

button2 = digitalio.DigitalInOut(board.D2)
button2.switch_to_input(pull=digitalio.Pull.DOWN)

while True:
    # Check Button D0
    if not button0.value:  # button0 is active (Pull.UP, active LOW)
        print("Button D0 pressed")
        led.value = True
    # Check Button D1
    elif button1.value:  # button1 is active (Pull.DOWN, active HIGH)
        print("Button D1 pressed")
        led.value = True
    # Check Button D2
    elif button2.value:  # button2 is active (Pull.DOWN, active HIGH)
        print("Button D2 pressed")
        led.value = True
    else:
        led.value = False  # No buttons are pressed, turn off the LED

    # Small delay to debounce buttons and reduce serial output spam
    time.sleep(0.1)
