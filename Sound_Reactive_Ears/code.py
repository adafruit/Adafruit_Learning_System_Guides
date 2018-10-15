"""
Circuit Playground Express sounds activated ears.

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

import time
import math
import array
import board
import audiobusio
import pulseio
from adafruit_motor import servo
from adafruit_circuitplayground.express import cpx

# Exponential scaling factor.
# Should probably be in range -10 .. 10 to be reasonable.
CURVE = 2
SCALE_EXPONENT = math.pow(10, CURVE * -0.1)

# Number of samples to read at once.
NUM_SAMPLES = 90

# the trigger threshhold
THRESHOLD = 6
left_pwm = pulseio.PWMOut(board.A1, frequency=50)
right_pwm = pulseio.PWMOut(board.A2, frequency=50)

left_ear = servo.Servo(left_pwm)
right_ear = servo.Servo(right_pwm)

cpx.pixels.fill((0, 0, 0))
left_ear.angle = 0
right_ear.angle = 0

# Restrict value to be between floor and ceiling.

def constrain(value, floor, ceiling):
    return max(floor, min(value, ceiling))


def log_scale(input_value, input_min, input_max, output_min, output_max):
    normalized_input_value = (input_value - input_min) / \
                             (input_max - input_min)
    return output_min + \
        math.pow(normalized_input_value, SCALE_EXPONENT) \
        * (output_max - output_min)


# Remove DC bias before computing RMS.

def normalized_rms(values):
    minbuf = int(mean(values))
    samples_sum = sum(
        float(sample - minbuf) * (sample - minbuf)
        for sample in values
    )

    return math.sqrt(samples_sum / len(values))


def mean(values):
    return sum(values) / len(values)


mic = audiobusio.PDMIn(board.MICROPHONE_CLOCK, board.MICROPHONE_DATA,
                       sample_rate=16000, bit_depth=16)


# Record an initial sample to calibrate. Assume it's quiet when we start.
samples = array.array('H', [0] * NUM_SAMPLES)
mic.record(samples, len(samples))
# Set lowest level to expect, plus a little.
input_floor = normalized_rms(samples) + 10

# Corresponds to sensitivity: lower means ears perk up at lower volumes
# Adjust this as you see fit.
input_ceiling = input_floor + 750

ears_up = False

while True:
    samples_read = mic.record(samples, len(samples))
    if samples_read < NUM_SAMPLES:
        print("MISSING SAMPLES, only: {0}".format(samples_read))
    magnitude = normalized_rms(samples)
    # You might want to print this to see the values.
    # print(magnitude)

    # Compute scaled logarithmic reading in the range 0 to 10
    c = log_scale(constrain(magnitude, input_floor, input_ceiling),
                  input_floor, input_ceiling, 0, 10)


    if c >= THRESHOLD and not ears_up:
        ears_up = True
        left_ear.angle = 90
        right_ear.angle = 90
        time.sleep(1.0)
    elif c < THRESHOLD and ears_up:
        ears_up = False
        left_ear.angle = 0
        right_ear.angle = 0
        time.sleep(1.0)
    else:
        time.sleep(0.1)
