import time
import board
import digitalio

step = digitalio.DigitalInOut(board.D6)
direct = digitalio.DigitalInOut(board.D5)

step.direction = digitalio.Direction.OUTPUT
direct.direction = digitalio.Direction.OUTPUT

direct.value = True

while True:
    step.value = True
    time.sleep(0.001)
    step.value = False
    time.sleep(0.10025)
