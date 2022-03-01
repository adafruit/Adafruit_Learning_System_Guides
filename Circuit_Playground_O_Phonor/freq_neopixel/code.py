# SPDX-FileCopyrightText: 2019 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import array
import board
import audiobusio
import simpleio
import neopixel

#---| User Configuration |---------------------------
SAMPLERATE = 16000
SAMPLES = 1024
THRESHOLD = 100
MIN_DELTAS = 5
DELAY = 0.2

FREQ_LOW = 520
FREQ_HIGH = 990
COLORS = (
    (0xFF, 0x00, 0x00) , # pixel 0
    (0xFF, 0x71, 0x00) , # pixel 1
    (0xFF, 0xE2, 0x00) , # pixel 2
    (0xAA, 0xFF, 0x00) , # pixel 3
    (0x38, 0xFF, 0x00) , # pixel 4
    (0x00, 0xFF, 0x38) , # pixel 5
    (0x00, 0xFF, 0xA9) , # pixel 6
    (0x00, 0xE2, 0xFF) , # pixel 7
    (0x00, 0x71, 0xFF) , # pixel 8
    (0x00, 0x00, 0xFF) , # pixel 9
)
#----------------------------------------------------

# Create a buffer to record into
samples = array.array('H', [0] * SAMPLES)

# Setup the mic input
mic = audiobusio.PDMIn(board.MICROPHONE_CLOCK,
                       board.MICROPHONE_DATA,
                       sample_rate=SAMPLERATE,
                       bit_depth=16)

# Setup NeoPixels
pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, auto_write=False)

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

    # Show on NeoPixels
    pixels.fill(0)
    pixel = round(simpleio.map_range(freq, FREQ_LOW, FREQ_HIGH, 0, 9))
    pixels[pixel] = COLORS[pixel]
    pixels.show()

    time.sleep(DELAY)
