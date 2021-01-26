"""
Simple motion sensor example for Pico. Prints to serial console when PIR sensor is triggered.

REQUIRED HARDWARE:
* PIR sensor on pin GP28.
"""
import board
import digitalio

pir = digitalio.DigitalInOut(board.GP28)
pir.direction = digitalio.Direction.INPUT

while True:
    if pir.value:
        print("ALARM! Motion detected!")
        while pir.value:
            pass
