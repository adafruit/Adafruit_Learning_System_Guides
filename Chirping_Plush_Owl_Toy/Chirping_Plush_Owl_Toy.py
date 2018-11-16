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

# emphasis ow "me"
def meow():
    play_tone(5100,50)           # "m" (short)
    play_tone(394,180)           # "eee" (long)
    for i in range(990,1022,2): # vary "ooo" down
        play_tone(i,8)
    play_tone(5100,40)           # "w" (short)

# cat meow (emphasis on "ow")
def meow2():
    play_tone(5100,55)          # "m" (short)
    play_tone(394,170)          # "eee" (long)
    time.sleep(0.03)            # wait a tiny bit
    for i in range(990,1022,2): # vary "ooo" down
        play_tone(i,8)
    play_tone(5100,40)          # "w" (short)

# dog ruff
def ruff():
    for i in range(890,910,2):  # "rrr"  (vary down)
        play_tone(i,3)
    play_tone(1664,150)         # "uuu" (hard to do)
    play_tone(12200,70)         # "ff"  (long, hard to do)

# dog arf
def arf():
    play_tone(890,25)             # "a"    (short)
    for i in range(890,910,2):    # "rrr"  (vary down)
        play_tone(i,5)
    play_tone(4545,80)            # intermediate
    play_tone(12200,70)           # "ff"   (shorter, hard to do)

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

    # reverse logic for motion pins
    if not motion.value:
        # bird chirp noise
        # comment out chirp and uncomment a different sound below
        # for more animal noises
        chirp()
        # meow()
        # meow2()
        # ruff()
        # arf()
        time.sleep(.5)                  # leave some time to complete rotation
