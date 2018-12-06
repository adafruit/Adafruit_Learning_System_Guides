from os import listdir
import subprocess
from time import sleep

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.IN)
GPIO.setup(24, GPIO.IN)
GPIO.setup(25, GPIO.IN)

mp3_files = [ f for f in listdir('.') if f[-4:] == '.mp3' ]

if not len(mp3_files) > 0:
    print("No mp3 files found!")

print('--- Available mp3 files ---')
print(mp3_files)
print('--- Press button #1 to select mp3, button #2 to play current. ---')

index = 0
while True:
    if not GPIO.input(23):
        index += 1
        if index >= len(mp3_files):
            index = 0
        print("--- " + mp3_files[index] + " ---")

    if not GPIO.input(24):
        subprocess.Popen(['omxplayer', mp3_files[index]])
        print('--- Playing ' + mp3_files[index] + ' ---')
        print('--- Press button #3 to clear playing mp3s. ---')
        sleep(1)

    if not GPIO.input(25):
        subprocess.call(['killall', 'omxplayer'])
        print('--- Cleared all existing mp3s. ---')

    sleep(0.25)
