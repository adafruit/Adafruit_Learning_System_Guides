# Chirp Owl written by Becky Stern and T Main for Adafruit Industries
# Tutorial: http://learn.adafruit.com/chirping-plush-owl-toy/

# Includes animal sounds by Mike Barela
# http://learn.adafruit.com/adafruit-trinket-modded-stuffed-animal/animal-sounds
# based in part on Debounce
#  created 21 November 2006
#  by David A. Mellis
#  modified 30 Aug 2011
#  by Limor Fried
#  modified 28 Dec 2012
#  by Mike Walters
#  CircuitPython Port 2018
#  by Mikey Sklar
#  This example code is in the public domain.
#  http://www.arduino.cc/en/Tutorial/Debounce

import time
import board
import digitalio 

# setup for vibration sensor
motion = digitalio.DigitalInOut(board.D0)
motion.direction = digitalio.Direction.INPUT
motion.pull = digitalio.Pull.UP

# setup for speaker output
speaker = digitalio.DigitalInOut(board.D2)
speaker.direction = digitalio.Direction.OUTPUT

def chirp():
    for i in range(200,180,-1):
        play_tone(i,9)

def play_tone(tone_value, duration):
    microseconds = 10 ** 6              # duration divider, convert to microseconds

    for i in range(0, duration):
        i += tone_value * 2
        speaker.value = True
        time.sleep(tone_value / microseconds)
        speaker.value = False
        time.sleep(tone_value / microseconds)

# loop forever...
while True:

    if not motion.value:
        # bird chirp noise
        # comment out chirp and uncomment a different line below for other sounds
        chirp()                         
        # meow()
        # meow2()
        # ruff()
        # arf()
        time.sleep(.5)                  # leave some time to complete rotation
