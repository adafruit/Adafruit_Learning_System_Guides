# CircuitPython Demo - Cap Touch Multiple Pins
# Example only works with Gemma, Feather M0 Express, Metro M0 Express, ItsyBitsy M0 Express!

import time
import board
import touchio

touch_A0 = touchio.TouchIn(board.A0)  # Will not work on Circuit Playground Express!
touch_A1 = touchio.TouchIn(board.A1)  # Will not work on Trinket M0!

while True:
    if touch_A0.value:  # Will not work on Circuit Playground Express!
        print("Touched A0!")
    if touch_A1.value:  # Will not work on Trinket M0!
        print("Touched A1!")
    time.sleep(0.05)
