"""
CircuitPython Capacitive Two Touch Pad Example - Print to the serial console when a pad is touched.

Update TOUCH_PAD_PIN_ONE to the first touch pad pin name for the board you're using.
Update TOUCH_PAD_PIN_TWO to the pin name for the second touch pad.

For example:
If you are using the BLM Badge, update TOUCH_PAD_PIN_ONE to CAP1, and TOUCH_PAD_PIN_TWO to CAP2.
If using a CPX, update TOUCH_PAD_PIN to A1, and TOUCH_PAD_PIN_TWO to A2.
"""
import time
import board
import touchio

touch_one = touchio.TouchIn(board.TOUCH_PAD_PIN_ONE)
touch_two = touchio.TouchIn(board.TOUCH_PAD_PIN_TWO)

while True:
    if touch_one.value:
        print("Pad one touched!")
    if touch_two.value:
        print("Pad two touched!")
    time.sleep(0.1)
