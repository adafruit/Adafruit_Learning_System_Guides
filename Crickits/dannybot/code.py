# SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import random
import audioio
import audiocore
from digitalio import DigitalInOut, Pull, Direction
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import servo
from busio import I2C
import board

wavefiles = ["01.wav", "02.wav", "03.wav", "04.wav", "05.wav", "06.wav",
             "07.wav", "08.wav", "09.wav", "10.wav", "11.wav", "12.wav",
             "13.wav", "14.wav"]

# Create seesaw object
i2c = I2C(board.SCL, board.SDA)
seesaw = Seesaw(i2c)

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

buttona = DigitalInOut(board.BUTTON_A)
buttona.direction = Direction.INPUT
buttona.pull = Pull.DOWN

buttonb = DigitalInOut(board.BUTTON_B)
buttonb.direction = Direction.INPUT
buttonb.pull = Pull.DOWN

SWITCH = 2     # A switch on signal #0
# Add a pullup on the switch
seesaw.pin_mode(SWITCH, seesaw.INPUT_PULLUP)

# Servo angles
MOUTH_START = 95
MOUTH_END = 90

# 17 is labeled SERVO 1 on CRICKIT
pwm = PWMOut(seesaw, 17)
# must be 50 cannot change
pwm.frequency = 50
# microservo usually is 400/2500 (tower pro sgr2r)
my_servo = servo.Servo(pwm, min_pulse=400, max_pulse=2500)
# Starting servo locations
my_servo.angle = MOUTH_START

# Audio playback object and helper to play a full file
a = audioio.AudioOut(board.A0)
def play_file(wavfile):
    print("Playing", wavfile)
    with open(wavfile, "rb") as f:
        wav = audiocore.WaveFile(f)
        a.play(wav)
        while a.playing:
            my_servo.angle = MOUTH_END
            time.sleep(.15)
            my_servo.angle = MOUTH_START
            time.sleep(.15)

while True:
    if seesaw.digital_read(SWITCH) and not buttona.value and not buttonb.value:
        continue

    play_file(random.choice(wavefiles))

    # wait for buttons to be released
    while buttona.value or buttonb.value or not seesaw.digital_read(SWITCH):
        pass
