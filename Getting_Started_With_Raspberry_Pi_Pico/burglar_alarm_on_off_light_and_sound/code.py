"""
A burglar alarm example for Pico. Slow flashing LED indicates alarm is ready. Quick flashing LED
and beeping buzzer indicate alarm has been triggered.

REQUIRED HARDWARE:
* PIR sensor on pin GP28.
* LED on pin GP13.
* Piezo buzzer on pin GP14.
"""
import time
import board
import digitalio
import pwmio

pir = digitalio.DigitalInOut(board.GP28)
pir.direction = digitalio.Direction.INPUT
led = digitalio.DigitalInOut(board.GP13)
led.direction = digitalio.Direction.OUTPUT
buzzer = pwmio.PWMOut(board.GP14, frequency=660, duty_cycle=0, variable_frequency=True)

motion_detected = False
while True:
    if pir.value and not motion_detected:
        print("ALARM! Motion detected!")
        motion_detected = True

    if pir.value:
        led.value = True
        buzzer.duty_cycle = 2 ** 15
        time.sleep(0.1)
        led.value = False
        buzzer.duty_cycle = 0
        time.sleep(0.1)

    else:
        motion_detected = False
        led.value = True
        time.sleep(0.5)
        led.value = False
        time.sleep(0.5)
