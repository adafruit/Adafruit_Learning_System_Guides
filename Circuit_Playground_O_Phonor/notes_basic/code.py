# SPDX-FileCopyrightText: 2019 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import array
import board
import audiobusio

#---| User Configuration |---------------------------
SAMPLERATE = 16000
SAMPLES = 1024
THRESHOLD = 100
MIN_DELTAS = 5
DELAY = 0.2

#        octave = 1    2    3    4    5     6     7     8
NOTES = { "C" : (33,  65, 131, 262, 523, 1047, 2093, 4186),
          "D" : (37,  73, 147, 294, 587, 1175, 2349, 4699),
          "E" : (41,  82, 165, 330, 659, 1319, 2637, 5274),
          "F" : (44,  87, 175, 349, 698, 1397, 2794, 5588),
          "G" : (49,  98, 196, 392, 785, 1568, 3136, 6272),
          "A" : (55, 110, 220, 440, 880, 1760, 3520, 7040),
          "B" : (62, 123, 247, 494, 988, 1976, 3951, 7902)}
#----------------------------------------------------

# Create a buffer to record into
samples = array.array('H', [0] * SAMPLES)

# Setup the mic input
mic = audiobusio.PDMIn(board.MICROPHONE_CLOCK,
                       board.MICROPHONE_DATA,
                       sample_rate=SAMPLERATE,
                       bit_depth=16)

while True:
    # Get raw mic data
    mic.record(samples, SAMPLES)

    # Compute DC offset (mean) and threshold level
    mean = int(sum(samples) / len(samples) + 0.5)
    threshold = mean + THRESHOLD

    # Compute deltas between mean crossing points
    # (this bit by Dan Halbert)
    deltas = []
    last_xing_point = None
    crossed_threshold = False
    for i in range(SAMPLES-1):
        sample = samples[i]
        if sample > threshold:
            crossed_threshold = True
        if crossed_threshold and sample < mean:
            if last_xing_point:
                deltas.append(i - last_xing_point)
            last_xing_point = i
            crossed_threshold = False

    # Try again if not enough deltas
    if len(deltas) < MIN_DELTAS:
        continue

    # Average the deltas
    mean = sum(deltas) / len(deltas)

    # Compute frequency
    freq = SAMPLERATE / mean

    print("crossings: {}  mean: {}  freq: {} ".format(len(deltas), mean, freq))

    # Find corresponding note
    for note in NOTES:
        for octave, note_freq in enumerate(NOTES[note]):
            if note_freq * 0.97 <= freq <= note_freq * 1.03:
                print("-"*10)
                print("NOTE = {}{}".format(note, octave + 1))
                print("-"*10)

    time.sleep(DELAY)
