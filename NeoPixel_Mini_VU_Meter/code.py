# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import array
import math
import board
import audiobusio
import simpleio
import neopixel

#  neopixel setup
pixel_pin = board.A0

pixel_num = 16

pixels = neopixel.NeoPixel(pixel_pin, pixel_num, brightness=0.1, auto_write=False)

#  function to average mic levels
def mean(values):
    return sum(values) / len(values)

#  function to return mic level
def normalized_rms(values):
    minbuf = int(mean(values))
    samples_sum = sum(
        float(sample - minbuf) * (sample - minbuf)
        for sample in values
    )

    return math.sqrt(samples_sum / len(values))

#  mic setup
mic = audiobusio.PDMIn(board.TX,
                       board.A1, sample_rate=16000, bit_depth=16)
samples = array.array('H', [0] * 160)

#  variable to hold previous mic level
last_input = 0

#  neopixel colors
GREEN = (0, 127, 0)
RED = (127, 0, 0)
YELLOW = (127, 127, 0)
OFF = (0, 0, 0)

#  array of colors for VU meter
colors = [GREEN, GREEN, GREEN, GREEN, GREEN, GREEN, GREEN, GREEN,
          GREEN, YELLOW, YELLOW, YELLOW, YELLOW, YELLOW, RED, RED]

#  begin with pixels off
pixels.fill(OFF)
pixels.show()

while True:
    #  take in audio
    mic.record(samples, len(samples))
    #  magnitude holds the value of the mic level
    magnitude = normalized_rms(samples)
    #  uncomment to see the levels in the REPL
    #  print((magnitude,))

    #  mapping the volume range (125-500) to the 16 neopixels
    #  volume range is optimized for music. you may want to adjust the range
    #  based on the type of audio that you're trying to show
    mapped_value = simpleio.map_range(magnitude, 125, 500, 0, 16)
    #  converting the mapped range to an integer
    input_val = int(mapped_value)

    #  if the mic input has changed from the last input value...
    if last_input != input_val:
        for i in range(input_val):
            #  if the level is lower...
            if last_input > input_val:
                for z in range(last_input):
                    #  turn those pixels off
                    pixels[z] = (OFF)
            #  turn on pixels using the colors array
            pixels[i] = (colors[i])
            pixels.show()
            #  update last_input
            last_input = input_val

    time.sleep(0.01)
