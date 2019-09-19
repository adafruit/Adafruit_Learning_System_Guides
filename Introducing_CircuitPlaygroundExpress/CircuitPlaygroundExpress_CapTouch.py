# Circuit Playground Capacitive Touch

import time
import board
import touchio

touch_A1 = touchio.TouchIn(board.A1)
touch_A2 = touchio.TouchIn(board.A2)
touch_A3 = touchio.TouchIn(board.A3)
touch_A4 = touchio.TouchIn(board.A4)
touch_A5 = touchio.TouchIn(board.A5)
touch_A6 = touchio.TouchIn(board.A6)
touch_TX = touchio.TouchIn(board.TX)

while True:
    if touch_A1.value:
        print("A1 touched!")
    if touch_A2.value:
        print("A2 touched!")
    if touch_A3.value:
        print("A3 touched!")
    if touch_A4.value:
        print("A4 touched!")
    if touch_A5.value:
        print("A5 touched!")
    if touch_A6.value:
        print("A6 touched!")
    if touch_TX.value:
        print("TX touched!")

    time.sleep(0.01)
