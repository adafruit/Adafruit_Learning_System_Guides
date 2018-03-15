import time
import board
import touchio

touch_A0 = touchio.TouchIn(board.A0)  # Will not work on Circuit Playground Express! Comment it out!
# touch_A1 = touchio.TouchIn(board.A1)  # Uncomment for using with CPX.

while True:
    # if touch_A1.value:  # Uncomment for using with CPX.
    if touch_A0.value:  # Will not work on CPX! Comment this out!
        print("Touched!")
    time.sleep(0.05)
