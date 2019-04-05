import time

import analogio
import board

light = analogio.AnalogIn(board.LIGHT)

while True:
    print((light.value,))
    time.sleep(0.1)
