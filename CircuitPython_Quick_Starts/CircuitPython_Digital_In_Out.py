# CircuitPython IO demo #1 - General Purpose I/O

from digitalio import DigitalInOut, Direction, Pull
import board
import time

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

switch = DigitalInOut(board.D2) # For Gemma M0, Trinket M0, Metro M0 Express, ItsyBitsy M0 Express
# switch = DigitalInOut(board.D5)  # For Feather M0 Express
# switch = DigitalInOut(board.D7)  # For Circuit Playground Express
switch.direction = Direction.INPUT
switch.pull = Pull.DOWN  # For Gemma M0, Trinket M0, Metro M0 Exp, ItsyBitsy M0 Exp, Feather M0 Exp
# switch.pull = Pull.UP  # For Circuit Playground Express


while True:
    if switch.value:
        led.value = False
    else:
        led.value = True

    time.sleep(0.01)  # debounce delay
