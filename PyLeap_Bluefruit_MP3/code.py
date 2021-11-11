# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Circuit Playground Bluefruit MP3 Playback

Press each button on the Circuit Playground Bluefruit to play a different MP3.
"""
from adafruit_circuitplayground import cp

while True:
    if cp.button_a:
        cp.play_mp3("happy.mp3")
    if cp.button_b:
        cp.play_mp3("beats.mp3")
