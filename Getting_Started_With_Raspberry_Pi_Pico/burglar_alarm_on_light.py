"""
A burglar alarm example for Pico. Quick flashing LED indicates alarm has been triggered.

REQUIRED HARDWARE:
* PIR sensor on pin GP28.
* LED on pin GP13.
"""
import time
import board
import digitalio

pir = digitalio.DigitalInOut(board.GP28)
pir.direction = digitalio.Direction.INPUT
led = digitalio.DigitalInOut(board.GP13)
led.direction = digitalio.Direction.OUTPUT

motion_detected = False
while True:
    if pir.value and not motion_detected:
        print("ALARM! Motion detected!")
        motion_detected = True

    if pir.value:
        led.value = True
        time.sleep(0.1)
        led.value = False
        time.sleep(0.1)

    motion_detected = pir.value
