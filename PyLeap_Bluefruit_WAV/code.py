# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Circuit Playground Bluefruit WAV Playback

Press each button on the Circuit Playground Bluefruit to play a different WAV.
"""
from adafruit_circuitplayground import cp

while True:
    if cp.button_a:
        cp.play_file("dip.wav")
    if cp.button_b:
        cp.play_file("rise.wav")
