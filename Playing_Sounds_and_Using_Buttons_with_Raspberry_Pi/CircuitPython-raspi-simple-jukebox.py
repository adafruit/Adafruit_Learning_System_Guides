# This script requires a Raspberry Pi 2, 3 or Zero. Circuit Python must
# be installed and it is strongly recommended that you use the latest
# release of Raspbian.

import time
from os import listdir
import subprocess
import board
import digitalio

button1 = digitalio.DigitalInOut(board.D23)
button1.direction = digitalio.Direction.INPUT
button1.pull = digitalio.Pull.UP

button2 = digitalio.DigitalInOut(board.D24)
button2.direction = digitalio.Direction.INPUT
button2.pull = digitalio.Pull.UP

button3 = digitalio.DigitalInOut(board.D25)
button3.direction = digitalio.Direction.INPUT
button3.pull = digitalio.Pull.UP

mp3_files = [ f for f in listdir('.') if f[-4:] == '.mp3' ]

if not len(mp3_files) > 0:
    print("No mp3 files found!")

print('--- Available mp3 files ---')
print(mp3_files)
print('--- Press button #1 to select mp3, button #2 to play current. ---')

index = 0
while True:
    if not button1.value:
        index += 1
        if index >= len(mp3_files):
            index = 0
        print("--- " + mp3_files[index] + " ---")

    if not button2.value:
        subprocess.Popen(['omxplayer', mp3_files[index]])
        print('--- Playing ' + mp3_files[index] + ' ---')
        print('--- Press button #3 to clear playing mp3s. ---')
        time.sleep(0.25)

    if not button3.value:
        subprocess.call(['killall', 'omxplayer'])
        print('--- Cleared all existing mp3s. ---')

    time.sleep(0.25)
