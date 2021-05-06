"""
CircuitPython Capacitive Two Touch Pin Example - Print to the serial console when a pin is touched.

Update TOUCH_PIN_ONE to the first touch-capable pin name for the board you're using.
Update TOUCH_PIN_TWO to the pin name for the second touch-capable pin.

For example:
If you are using A0 and A1 on a Feather RP2040, update TOUCH_PIN_ONE to A0 and TOUCH_PIN_TWO to A2.
"""
import time
import board
import touchio

touch_one = touchio.TouchIn(board.TOUCH_PIN_ONE)
touch_two = touchio.TouchIn(board.TOUCH_PIN_TWO)

while True:
    if touch_one.value:
        print("Pin one touched!")
    if touch_two.value:
        print("Pin two touched!")
    time.sleep(0.1)
