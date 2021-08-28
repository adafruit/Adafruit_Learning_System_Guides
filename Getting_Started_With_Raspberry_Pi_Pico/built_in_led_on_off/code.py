"""Example for Pico. Turns the built-in LED on and off with no delay."""
import board
import digitalio

led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

while True:
    led.value = True
    led.value = False
