# SPDX-FileCopyrightText: 2018 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
CircuitPython PWM Audio Out WAV example
Play a WAV file once.

Remove this line and all of the following docstring content before submitting to the Learn repo.

Update the audio out pin to match the wiring chosen for the microcontroller.
Update the following pin name to a viable pin:
* AUDIO_OUTPUT_PIN
"""
import board
from audiocore import WaveFile
from audiopwmio import PWMAudioOut as AudioOut

audio = AudioOut(board.AUDIO_OUTPUT_PIN)

with open("StreetChicken.wav", "rb") as wave_file:
    wave = WaveFile(wave_file)
    print("Playing wav file!")
    audio.play(wave)
    while audio.playing:
        pass

print("Done!")
