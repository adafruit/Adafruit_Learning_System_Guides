import analogio
import board
import time
 
light = analogio.AnalogIn(board.LIGHT)
 
while True:
    print((light.value,))
    time.sleep(0.1)
