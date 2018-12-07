import os
from time import sleep

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.IN)
GPIO.setup(24, GPIO.IN)
GPIO.setup(25, GPIO.IN)

while True:
    if not GPIO.input(23):
        os.system('omxplayer temple-bell.mp3 &')

    if not GPIO.input(24):
        os.system('omxplayer temple-bell-bigger.mp3 &')

    if not GPIO.input(25):
        os.system('omxplayer temple-bell-huge.mp3 &')

    sleep(0.25)
