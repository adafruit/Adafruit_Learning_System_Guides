import time
import board
from digitalio import DigitalInOut, Direction

# LED setup for onboard LED
led = DigitalInOut(board.LED)
led.direction = Direction.OUTPUT

while True:

    led.value = True
    print("led on")
    time.sleep(1)

    led.value = False
    print("led off")
    time.sleep(1)
