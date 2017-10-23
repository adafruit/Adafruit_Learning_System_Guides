from digitalio import DigitalInOut, Direction, Pull
import board
import time

button = DigitalInOut(board.D1)
button.direction = Direction.INPUT
button.pull = Pull.UP

led = DigitalInOut(board.D2)
led.direction = Direction.OUTPUT

while True:
    # When the button is True (pressed), the LED should be True (on).
    led.value = button.value
    # Wait a little bit to reduce flicker.
    time.sleep(0.01)
