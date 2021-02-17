"""
Read the potentiometer value. Prints the value to the serial console every two seconds.

REQUIRED HARDWARE:
* potentiometer on pin GP26.
"""
import time
import board
import analogio

potentiometer = analogio.AnalogIn(board.GP26)

while True:
    print(potentiometer.value)
    time.sleep(2)
