import time
import board
import touchio

touch_A0 = touchio.TouchIn(board.A0)  # Will not work on Circuit Playground Express!

while True:
    if touch_A0.value:
        print("Touched A0!")
    time.sleep(0.05)
