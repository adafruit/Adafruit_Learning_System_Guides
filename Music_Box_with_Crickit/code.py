# Music Box code in CircuitPython - Dano Wall and Mike Barela

import os
import random
from busio import I2C
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import servo
from analogio import AnalogIn
from simpleio import map_range
import neopixel
import audioio
import board

# Create seesaw object
i2c = I2C(board.SCL, board.SDA)
seesaw = Seesaw(i2c)

# Create one servo on seesaw servo 2
pwm = PWMOut(seesaw, 16)
pwm.frequency = 50
myservo = servo.Servo(pwm)
myservo.angle = 0

# Find all Wave files on the storage
wavefiles = [file for file in os.listdir("/")
             if (file.endswith(".wav") and not file.startswith("._"))]
if len(wavefiles) < 1:
    print("No wav files found in root directory")
else:
    print("Audio files found: ", wavefiles)

# audio output
cpx_audio = audioio.AudioOut(board.A0)

def play_file(filename):
    f = open(filename, "rb")
    wav = audioio.WaveFile(f)
    cpx_audio.play(wav)

# neopixels!
pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=1)
pixels.fill((0, 0, 0))

# light sensor
rawlight = AnalogIn(board.LIGHT)

def light():
    peak = map_range(rawlight.value, 2000, 62000, 0, 1023)  # map to 0 to 1023
    return int(peak)

def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        return 0, 0, 0
    if pos < 85:
        return int(255 - pos * 3), int(pos * 3), 0
    if pos < 170:
        pos -= 85
        return 0, int(255 - pos * 3), int(pos * 3)
    pos -= 170
    return int(pos * 3), 0, int(255 - (pos * 3))

def rainbow(value):
    for i in range(10):
        pixels[i] = wheel((value * i) & 255)

index = 0
sign = 1

while True:
    if light() < 130:
        # Turn things off if light level < value
        pixels.fill((0, 0, 0))
        # myservo.angle = 0.0
        cpx_audio.stop()
    else:
        # calculate servo rotation
        if index > 246:
            index = 0
            sign = sign * -1
        # Move servo one slot depending on current direction
        if sign == 1:
            myservo.angle = int(index / 2)
        else:
            myservo.angle = 123 - int(index / 2)
        # play wav file when index is a multiple of 40 (~6x per
        # servo rotation and the sound is not already playing
        if (index % 40) == 0 and not cpx_audio.playing:
            play_file(random.choice(wavefiles))
        rainbow(index)
        index += 1
