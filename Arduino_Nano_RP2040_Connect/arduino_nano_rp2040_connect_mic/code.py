# SPDX-FileCopyrightText: 2021 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

'''Adapted from the example code DM_Mic_Sound_Level_Plot.py
https://github.com/adafruit/Adafruit_Learning_System_Guides/
blob/master/PDM_Microphone/PDM_Mic_Sound_Level_Plot.py '''

import time
import array
import math
import board
import audiobusio
import pwmio
import simpleio

# LED setup
led = pwmio.PWMOut(board.A1, frequency=5000, duty_cycle=0)

# Remove DC bias before computing RMS.
def mean(values):
    return sum(values) / len(values)

def normalized_rms(values):
    minbuf = int(mean(values))
    samples_sum = sum(
        float(sample - minbuf) * (sample - minbuf)
        for sample in values
    )

    return math.sqrt(samples_sum / len(values))

mic = audiobusio.PDMIn(board.MICROPHONE_CLOCK,
                       board.MICROPHONE_DATA, sample_rate=16000, bit_depth=16)
samples = array.array('H', [0] * 160)

while True:

    mic.record(samples, len(samples))
    magnitude = normalized_rms(samples)
    print((magnitude,))

	#  mapping mic's level to LED PWM range
    mapped_value = simpleio.map_range(magnitude, 75 , 300, 0, 65535)

	#  sending mapped value to LED for PWM
    led.duty_cycle = int(mapped_value)
	#  optional logging for mapped_value
    #  print((mapped_value,))
    time.sleep(0.01)
