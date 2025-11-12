# SPDX-FileCopyrightText: 2018 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import random
import time
import board
import audioio
import audiocore
from adafruit_crickit import crickit

# Hal button-and-voice example

# Button connected to Signal pin #1 & ground:
BUTTON = crickit.SIGNAL1
crickit.seesaw.pin_mode(BUTTON, crickit.seesaw.INPUT_PULLUP)

# LED connected to 5V & Drive pin #1:
LED = crickit.drive_1
LED.duty_cycle = 65535

# Find all Wave files in CIRCUITPY storage:
WAVEFILES = [file for file in os.listdir("/")
             if (file.endswith(".wav") and not file.startswith("._"))]
print("Audio files found:", WAVEFILES)

# Audio playback object:
AUDIO = audioio.AudioOut(board.A0)

# Function to play a wave file in its entirety:
def play_file(wavfile):
    print("Playing", wavfile)
    with open(wavfile, "rb") as f:
        wav = audiocore.WaveFile(f)
        AUDIO.play(wav)
        while AUDIO.playing:
            LED.duty_cycle = random.randint(5000, 30000)
            time.sleep(0.1)
    LED.duty_cycle = 65535

while True:
    if not crickit.seesaw.digital_read(BUTTON):
        # Play a random wave file
        play_file(random.choice(WAVEFILES))
        # Then wait for button to be released
        while not crickit.seesaw.digital_read(BUTTON):
            continue
