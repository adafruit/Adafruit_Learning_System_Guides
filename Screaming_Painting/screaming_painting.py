import time
import math
import array
import audiobusio
import audioio
import audiocore
import board
from adafruit_crickit import crickit

# Number of samples to read at once.
NUM_SAMPLES = 160

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

head_servo = crickit.servo_1
head_servo.set_pulse_width_range(min_pulse=500, max_pulse=2500)
head_servo.angle = 90  # center the head.

# Set audio out on speaker.
a = audioio.AudioOut(board.A0)

# Start playing the file (in the background).
def play_file(wavfile):
    print("Playing scream!")
    with open(wavfile, "rb") as f:
        wav = audiocore.WaveFile(f)
        a.play(wav)
        while a.playing:
            head_servo.angle = 60
            time.sleep(.01)
            head_servo.angle = 120
            time.sleep(.01)


while True:
    mic.record(samples, len(samples))
    magnitude = normalized_rms(samples)
    print(((magnitude),))  # formatting is for the Mu plotter.

    if magnitude < 1000:  # it's quiet, do nothing.
        pass
    else:
        print("LOUD")
        head_servo.angle = 60
        time.sleep(.05)
        head_servo.angle = 120
        time.sleep(.05)
        head_servo.angle = 90
        time.sleep(.02)
        play_file("scream_low.wav")
        head_servo.angle = 90
        time.sleep(2)
