# SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import time
import random
import board
import audioio
import audiocore
from adafruit_crickit import crickit

# Sparky automaton

# Find all Wave files on the storage
wavefiles = [file for file in os.listdir("/")
             if (file.endswith(".wav") and not file.startswith("._"))]
print("Audio files found: ", wavefiles)

# mouth servo
mouth_servo = crickit.servo_1
# TowerPro servos like 500/2500 pulsewidths
mouth_servo.set_pulse_width_range(min_pulse=500, max_pulse=2500)

# Servo angles
MOUTH_START = 100
MOUTH_END = 90

# Starting servo location
mouth_servo.angle = MOUTH_START

# Audio playback object and helper to play a full file
a = audioio.AudioOut(board.A0)

# Play a wave file and move the mouth while its playing!
def play_file(wavfile):
    print("Playing", wavfile)
    with open(wavfile, "rb") as f:
        wav = audiocore.WaveFile(f)
        a.play(wav)
        while a.playing:  # turn servos, motors, etc. during playback
            mouth_servo.angle = MOUTH_END
            time.sleep(0.15)
            mouth_servo.angle = MOUTH_START
            time.sleep(0.15)

while True:
    # Play a random quip
    play_file(random.choice(wavefiles))
    # then hang out for a few seconds
    time.sleep(3)
