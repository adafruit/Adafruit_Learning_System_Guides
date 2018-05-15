# CircuitPlaygroundExpress_CapTouch

import time

import board
import touchio

touch1 = touchio.TouchIn(board.A1)
touch2 = touchio.TouchIn(board.A2)
touch3 = touchio.TouchIn(board.A3)
touch4 = touchio.TouchIn(board.A4)
touch5 = touchio.TouchIn(board.A5)
touch6 = touchio.TouchIn(board.A6)
touch7 = touchio.TouchIn(board.A7)

while True:
    if touch1.value:
        print("A1 touched!")
    if touch2.value:
        print("A2 touched!")
    if touch3.value:
        print("A3 touched!")
    if touch4.value:
        print("A4 touched!")
    if touch5.value:
        print("A5 touched!")
    if touch6.value:
        print("A6 touched!")
    if touch7.value:
        print("A7 touched!")

    time.sleep(0.01)
