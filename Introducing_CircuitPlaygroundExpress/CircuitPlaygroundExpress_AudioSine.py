import time
import array
import math
import audioio
import board
import digitalio

FREQUENCY = 440  # 440 Hz middle 'A'
SAMPLERATE = 8000  # 8000 samples/second, recommended!

# Generate one period of sine wav.
length = SAMPLERATE // FREQUENCY
sine_wave = array.array("H", [0] * length)
for i in range(length):
    sine_wave[i] = int(math.sin(math.pi * 2 * i / 18) * (2 ** 15) + 2 ** 15)

# enable the speaker
speaker_enable = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
speaker_enable.direction = digitalio.Direction.OUTPUT
speaker_enable.value = True

audio = audioio.AudioOut(board.A0)
sine_wave_sample = audioio.RawSample(sine_wave)

audio.play(sine_wave_sample, loop=True)  # keep playing the sample over and over
time.sleep(1)  # until...
audio.stop()  # we tell the board to stop
