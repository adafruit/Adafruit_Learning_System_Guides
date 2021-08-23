# Gemma IO demo - captouch

import time

import board
import touchio

touch0 = touchio.TouchIn(board.A0)
touch1 = touchio.TouchIn(board.A1)
touch2 = touchio.TouchIn(board.A2)

while True:
    if touch0.value:
        print("A0 touched!")
    if touch1.value:
        print("A1 touched!")
    if touch2.value:
        print("A2 touched!")
    time.sleep(0.01)
