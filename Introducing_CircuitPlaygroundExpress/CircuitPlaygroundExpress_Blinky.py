# CircuitPlaygroundExpress_Blinky

import digitalio
import board
import time

led = digitalio.DigitalInOut(board.D13) #define the variable 'led'
led.direction = digitalio.Direction.OUTPUT #set the pin as output

while True: #code below this point loops over and over
    led.value = True #turn on the LED
    time.sleep(0.5) #pause
    led.value = False #turn off the LED
    time.sleep(0.5) #pause
