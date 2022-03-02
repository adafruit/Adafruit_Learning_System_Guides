# SPDX-FileCopyrightText: 2018 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import audioio
import audiocore
from adafruit_crickit import crickit

# Minerva Owl Robot

wavefiles = ["01.wav", "02.wav", "03.wav", "04.wav",
             "05.wav", "06.wav", "07.wav", "08.wav"]

# Two servos
eye_servo = crickit.servo_1
wing_servo = crickit.servo_2
# TowerPro servos like 500/2500 pulsewidths
eye_servo.set_pulse_width_range(min_pulse=500, max_pulse=2500)
wing_servo.set_pulse_width_range(min_pulse=500, max_pulse=2500)

# Servo angles
EYES_START = 90
EYES_LEFT = 110
EYES_RIGHT = 70
WINGS_START = 90
WINGS_END = 160

# Starting servo locations
eye_servo.angle = EYES_START
wing_servo.angle = WINGS_START

# Audio playback object and helper to play a full file
a = audioio.AudioOut(board.A0)


def play_file(wavfile):
    print("Playing", wavfile)
    with open(wavfile, "rb") as f:
        wav = audiocore.WaveFile(f)
        a.play(wav)
        while a.playing:  # turn servos, motors, etc. during playback
            eye_servo.angle = EYES_LEFT
            time.sleep(.25)
            eye_servo.angle = EYES_START
            time.sleep(.25)
            wing_servo.angle = WINGS_END
            time.sleep(.2)
            wing_servo.angle = WINGS_START
            time.sleep(.2)
            eye_servo.angle = EYES_RIGHT
            time.sleep(.25)
            eye_servo.angle = EYES_START
            time.sleep(.25)


while True:
    for i in range(8):
        play_file(wavefiles[i])
        time.sleep(2.5)
