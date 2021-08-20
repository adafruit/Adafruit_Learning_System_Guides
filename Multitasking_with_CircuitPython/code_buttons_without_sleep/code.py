"""
This example script shows how to read button state with
debouncing that does not rely on time.sleep().
"""

import board
from digitalio import DigitalInOut, Direction, Pull

btn = DigitalInOut(board.SWITCH)
btn.direction = Direction.INPUT
btn.pull = Pull.UP

prev_state = btn.value

while True:
    cur_state = btn.value
    if cur_state != prev_state:
        if not cur_state:
            print("BTN is down")
        else:
            print("BTN is up")

    prev_state = cur_state
