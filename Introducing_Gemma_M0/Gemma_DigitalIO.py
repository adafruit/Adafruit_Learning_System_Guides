# Gemma IO demo #1 - General Purpose I/O

from digitalio import DigitalInOut, Direction, Pull
import board
import time

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

button = DigitalInOut(board.D1)
button.direction = Direction.INPUT
button.pull = Pull.UP

while True:
    # we could also just do "led.value = not button.value" !
    if button.value:
		led.value = False
    else:
		led.value = True

    time.sleep(0.01) # debounce delay
