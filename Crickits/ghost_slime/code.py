# SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from digitalio import DigitalInOut, Direction, Pull
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.analoginput import AnalogInput
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import motor
from busio import I2C
import neopixel
import audioio
import audiocore
import board

# Create seesaw object
i2c = I2C(board.SCL, board.SDA)
seesaw = Seesaw(i2c)

# built in CPX button A
button = DigitalInOut(board.BUTTON_A)
button.direction = Direction.INPUT
button.pull = Pull.DOWN

# NeoPixels
pixels = neopixel.NeoPixel(board.A1, 10, brightness=0)
pixels.fill((0,0,250))

# Analog reading from Signal #1 (ss. #2)
foot_pedal = AnalogInput(seesaw, 2)

# Create one motor on seesaw PWM pins 22 & 23
motor_a = motor.DCMotor(PWMOut(seesaw, 22), PWMOut(seesaw, 23))
motor_a.throttle = 0

def map_range(x, in_min, in_max, out_min, out_max):
    # Maps a number from one range to another.
    mapped = (x-in_min) * (out_max - out_min) / (in_max-in_min) + out_min
    if out_min <= out_max:
        return max(min(mapped, out_max), out_min)
    return min(max(mapped, out_max), out_min)

# Get the audio file ready
wavfile = "unchained.wav"
f = open(wavfile, "rb")
wav = audiocore.WaveFile(f)
a = audioio.AudioOut(board.A0)

time_to_play = 0  # when to start playing
played = False  # have we played audio already? only play once!
while True:
    # Foot pedal ranges from about 700 (unpressed) to 50 (pressed)
    # make that change the speed of the motor from 0 (stopped) to 0.5 (half)
    press = foot_pedal.value
    speed = map_range(press, 700, 50, 0, 0.5)
    print("%d -> %0.3f" % (press, speed))
    motor_a.throttle = speed

    if not time_to_play and speed > 0.1:
        print("Start audio in 3 seconds")
        time_to_play = time.monotonic() + 3
    elif time_to_play and time.monotonic() > time_to_play and not played:
        print("Playing audio")
        a.play(wav)
        played = True

    # turn on/off blue LEDs
    if button.value:
        if pixels.brightness < 0.1:
            pixels.brightness = 1
        else:
            pixels.brightness = 0
        time.sleep(0.5)

    # loop delay
    time.sleep(0.1)
