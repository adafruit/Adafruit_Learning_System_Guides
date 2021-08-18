import time
import os
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

print("press a button!")

while True:
    if not button1.value:
        os.system('echo "Use the force Luke!" | festival --tts')

    if not button2.value:
        os.system('echo "Some rescue!" | festival --tts')

    if not button3.value:
        os.system('echo "I find your lack of faith disturbing." | festival --tts')

    time.sleep(0.1)
