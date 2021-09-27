"""
CircuitPython Capacitive Touch Pad Example - Print to the serial console when one pad is touched.
"""
import time
import board
import touchio

touch = touchio.TouchIn(board.TOUCH1)

while True:
    if touch.value:
        print("Pad touched!")
    time.sleep(0.1)
