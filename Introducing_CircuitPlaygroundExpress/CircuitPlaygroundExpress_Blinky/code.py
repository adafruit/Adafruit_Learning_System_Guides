# CircuitPlaygroundExpress_Blinky

import time

import board
import digitalio

led = digitalio.DigitalInOut(board.D13)  # defines the variable 'led'
led.direction = digitalio.Direction.OUTPUT  # set the pin as output

while True:  # code below this point loops over and over
    led.value = True  # turn on the LED
    time.sleep(0.5)  # pause
    led.value = False  # turn off the LED
    time.sleep(0.5)  # pause
