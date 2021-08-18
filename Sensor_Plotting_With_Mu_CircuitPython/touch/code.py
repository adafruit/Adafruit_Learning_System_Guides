import time

import board
import touchio

touch_A1 = touchio.TouchIn(board.A1)
touch_A2 = touchio.TouchIn(board.A2)
touch_A5 = touchio.TouchIn(board.A5)
touch_A6 = touchio.TouchIn(board.A6)

while True:
    value_A1 = touch_A1.raw_value
    value_A2 = touch_A2.raw_value
    value_A5 = touch_A5.raw_value
    value_A6 = touch_A6.raw_value
    print((value_A1, value_A2, value_A5, value_A6))
    time.sleep(0.1)
