import time
import array
import math
from busio import I2C
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import motor
import audiobusio
import board

print("Sound sensor motor!")

# Create seesaw object
i2c = I2C(board.SCL, board.SDA)
seesaw = Seesaw(i2c)

# Create one motor on seesaw PWM pins 22 & 23
motor_a = motor.DCMotor(PWMOut(seesaw, 22), PWMOut(seesaw, 23))
motor_a.throttle = 0 # motor is stopped


##################### helpers

# Maps a number from one range to another.
def map_range(x, in_min, in_max, out_min, out_max):
    mapped = (x-in_min) * (out_max - out_min) / (in_max-in_min) + out_min
    if out_min <= out_max:
        return max(min(mapped, out_max), out_min)
    return min(max(mapped, out_max), out_min)

# Returns the average
def mean(values):
    return sum(values) / len(values)

# Audio root-mean-square
def normalized_rms(values):
    minbuf = int(mean(values))
    return math.sqrt(sum(float(sample-minbuf)*(sample-minbuf) for sample in values) / len(values))


# Our microphone
mic = audiobusio.PDMIn(board.MICROPHONE_CLOCK, board.MICROPHONE_DATA,
                       sample_rate=16000, bit_depth = 16)
samples = array.array('H', [0] * 200)
mic.record(samples, len(samples))

while True:
    mic.record(samples, len(samples))
    magnitude = normalized_rms(samples)
    print(((magnitude),))
    motor_a.throttle = map_range(magnitude, 90, 200, 0, 1.0)
    time.sleep(0.1)
