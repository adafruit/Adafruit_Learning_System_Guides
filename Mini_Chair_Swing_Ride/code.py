# Isaac Wellish
# Code adapted from Mike Barela's Hello World of Robotics and
# Make it Move with Crickit guides at learn.adafruit.com
# Power must be plugged into right side of motor 1 on CRICKIT
#  to turn counter clock wise

import time
import audioio
import board
import neopixel
from digitalio import DigitalInOut, Pull, Direction
from adafruit_crickit import crickit

# Set audio out on speaker
speaker = audioio.AudioOut(board.A0)

# Two onboard CPX buttons for input (low level saves memory)
button_a = DigitalInOut(board.BUTTON_A)
button_a.direction = Direction.INPUT
button_a.pull = Pull.DOWN

button_b = DigitalInOut(board.BUTTON_B)
button_b.direction = Direction.INPUT
button_b.pull = Pull.DOWN

# Create one motor on seesaw motor port #1
motor = crickit.dc_motor_1

# NeoPixels on the Circuit Playground Express Light Blue
pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=0.7)
# Fill them with our favorite color "#0099FF light blue" -> 0x0099FF
# (see http://www.color-hex.com/ for more colors and find your fav!)

# set pixels to blue on start up
pixels.fill(0x0099FF)

motorInc = 0

# Start playing the file (in the background)
def play_file(wavfile):
    audio_file = open(wavfile, "rb")
    wav = audioio.WaveFile(audio_file)
    speaker.play(wav,loop = True)

while True:
    if button_a.value:
        pixels.fill(0xFC4044)
        play_file("circus_chair.wav")       # play WAV file
        motor.throttle = -0.20
        time.sleep(0.2)
        motor.throttle = -0.11 + motorInc  # increase speed
        motorInc -= 0.01

    if button_b.value:
        speaker.stop()
        pixels.fill(0x0099FF)  # magenta
        i = motor.throttle
        while i < -0.05:
            i += 0.005
            motor.throttle = i    # slow down!
            time.sleep(0.1)
        motor.throttle = 0 # stop
        motorInc = 0
