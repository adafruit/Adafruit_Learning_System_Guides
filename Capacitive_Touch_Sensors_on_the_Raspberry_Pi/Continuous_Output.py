import time
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)

padPin = 23
GPIO.setup(padPin, GPIO.IN)


while True:
    padPressed =  GPIO.input(padPin)

    if padPressed:
        print "pressed"
    
    time.sleep(0.1)

