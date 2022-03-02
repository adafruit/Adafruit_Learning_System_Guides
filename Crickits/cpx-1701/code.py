# SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from busio import I2C
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import motor
import neopixel
import audioio
import audiocore
import board

print("The voyages of the CPX-1701!")

# Create seesaw object
i2c = I2C(board.SCL, board.SDA)
seesaw = Seesaw(i2c)

# Create one motor on seesaw PWM pins 22 & 23
motor_a = motor.DCMotor(PWMOut(seesaw, 22), PWMOut(seesaw, 23))

# audio output
cpx_audio = audioio.AudioOut(board.A0)

# neopixels!
pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=1)
pixels.fill((0, 0, 0))

# give me a second before starting
time.sleep(1)

motor_a.throttle = 0  # warp drive off

f = open("01space.wav", "rb")
wav = audiocore.WaveFile(f)
cpx_audio.play(wav)

t = time.monotonic()  # take a timestamp

# slowly power up the dilithium crystals
for i in range(50):
    pixels.fill((0, 0, i))
    time.sleep(0.05)

# 6 seconds after audio started...
while time.monotonic() - t < 6:
    pass

motor_a.throttle = 1  # full warp drive on!

# wait for music to end
while cpx_audio.playing:
    pass
f.close()

# play the warp drive and theme music!
f = open("02warp.wav", "rb")
wav = audiocore.WaveFile(f)
cpx_audio.play(wav)

time.sleep(1)

# blast off!
pixels.fill((255, 0, 0))

# pulse the warp core
while True:
    for i in range(255, 0, -5):
        pixels.fill((i, 0, 0))
    for i in range(0, 255, 5):
        pixels.fill((i, 0, 0))

# wait for music to end
while cpx_audio.playing:
    pass
f.close()
