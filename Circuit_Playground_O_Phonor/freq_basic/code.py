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

    time.sleep(DELAY)
