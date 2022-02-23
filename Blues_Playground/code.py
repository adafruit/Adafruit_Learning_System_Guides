# SPDX-FileCopyrightText: 2018 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Blues Playground Instrument
# 2018-06-19 v03

import time
from adafruit_circuitplayground.express import cpx

# lists
drums = [  # startup and drum sound files
    "chime.wav",
    "kick.wav",
    "snare.wav",
    "hat.wav",
    "cymbal.wav",
    "tamb.wav",
    "cowbell.wav",
    "vibra_slap.wav"
]

chords = ["cp_A.wav", "cp_D.wav", "cp_E.wav"]

chord_changes = [  # chord_file, beats to play, beats played
    [0, 4, 0],
    [1, 4, 0],
    [0, 2, 0], [1, 2, 0],
    [0, 4, 0],
    [1, 4, 0],
    [1, 4, 0],
    [0, 2, 0], [1, 2, 0],
    [0, 4, 0],
    [2, 4, 0],
    [1, 4, 0],
    [0, 2, 0], [1, 2, 0],
    [0, 2, 0], [2, 2, 0]
]

cpx.pixels.fill((0, 0, 0))  # clear all pixels
cpx.play_file(drums[0])  # play startup

# select instrument mode with slide switch
if cpx.switch:
    instrument = "Chords"  # remember mode for later
    for i in range(9, -1, -1):  # fill chord range background with blue
        cpx.pixels[i] = (0, 0, 1)
        time.sleep(0.05)
else:
    instrument = "Drums"  # remember mode for later
    for i in range(9, 2, -1):  # fill voice range background with white
        cpx.pixels[i] = (1, 1, 1)
        time.sleep(0.05)

    voice = 1  # first drum voice
    cpx.pixels[10 - voice] = (0, 5, 0)  # green for first voice
    cpx.play_file(drums[voice])  # play first drum voice

    # choose drum voice with button A, lock-in selection with button B
    while not cpx.button_b:
        if cpx.button_a:  # loop through voices
            cpx.pixels[10 - voice] = (1, 1, 1)  # replace background color
            voice = voice + 1
            if voice > 7:
                voice = 1
            cpx.pixels[10 - voice] = (0, 5, 0)  # green for voice selection
            cpx.play_file(drums[voice])  # play current voice
        time.sleep(0.3)
    for i in range(3, 10):
        if i != (10 - voice):
            cpx.pixels[i] = (0, 0, 0)
            time.sleep(.1)
time.sleep(0.3)

# let's play the blues!
c_idx = 0  # start with the first chord change
while True:
    cpx.detect_taps = 1
    if cpx.tapped:  # wait for single tap
        if instrument == "Drums":
            cpx.play_file(drums[voice])  # play the selected drum sound

        if instrument == "Chords":  # play chords in sequence
            cpx.pixels[9 - (c_idx % 16)] = (3, 3, 0)  # yellow foreground
            cpx.play_file(chords[chord_changes[c_idx][0]])
            chord_changes[c_idx][2] = chord_changes[c_idx][2] + 1
            cpx.pixels[9 - (c_idx % 16)] = (0, 0, 1)  # replace background
            if chord_changes[c_idx][2] >= chord_changes[c_idx][1]:
                chord_changes[c_idx][2] = 0
                c_idx = c_idx + 1
                if c_idx > 15:
                    c_idx = 0
