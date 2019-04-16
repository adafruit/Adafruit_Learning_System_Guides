import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

#set the GPIO input pins
pad0 = 22
pad1 = 27
pad2 = 17
pad3 = 24
pad4 = 23

GPIO.setup(pad0, GPIO.IN)
GPIO.setup(pad1, GPIO.IN)
GPIO.setup(pad2, GPIO.IN)
GPIO.setup(pad3, GPIO.IN)
GPIO.setup(pad4, GPIO.IN)

pad0alreadyPressed = False
pad1alreadyPressed = False
pad2alreadyPressed = False
pad3alreadyPressed = False
pad4alreadyPressed = False


while True:
    pad0pressed = not GPIO.input(pad0)
    pad1pressed = not GPIO.input(pad1)
    pad2pressed = not GPIO.input(pad2)
    pad3pressed = not GPIO.input(pad3)
    pad4pressed = not GPIO.input(pad4)
    
    if pad0pressed and not pad0alreadyPressed:
        print "Pad 0 pressed"
    pad0alreadyPressed = pad0pressed

    if pad1pressed and not pad1alreadyPressed:
        print "Pad 1 pressed"
    pad1alreadyPressed = pad1pressed

    if pad2pressed and not pad2alreadyPressed:
        print "Pad 2 pressed"
    pad2alreadyPressed = pad2pressed

    if pad3pressed and not pad3alreadyPressed:
        print "Pad 3 pressed"
    pad3alreadyPressed = pad3pressed

    if pad4pressed and not pad4alreadyPressed:
        print "Pad 4 pressed"
    pad4alreadyPressed = pad4pressed

    time.sleep(0.1)
