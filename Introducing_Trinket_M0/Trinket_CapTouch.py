# Trinket IO demo - captouch

import touchio
import board
import time

touch0 = touchio.TouchIn(board.D1)
touch1 = touchio.TouchIn(board.D3)
touch2 = touchio.TouchIn(board.D4)

while True:
    if touch0.value:
        print("D1 touched!")
    if touch1.value:
        print("D3 touched!")
    if touch2.value:
        print("D4 touched!")
    time.sleep(0.01)
