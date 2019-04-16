import time
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)

padPin = 23
GPIO.setup(padPin, GPIO.IN)


alreadyPressed = False

while True:
    padPressed =  GPIO.input(padPin)

    if padPressed and not alreadyPressed:
        print "pressed"
    
    alreadyPressed = padPressed
    time.sleep(0.1)
