from digitalio import DigitalInOut, Direction
import audioio
import board
import array
import time
import math

FREQUENCY = 440    # 440 Hz middle 'A'
SAMPLERATE = 8000  # 8000 samples/second, recommended!

# Generate one period of sine wav.
length = SAMPLERATE // FREQUENCY
sine_wave = array.array("H", [0] * length)
for i in range(length):
    sine_wave[i] = int(math.sin(math.pi * 2 * i / 18) * (2 ** 15) + 2 ** 15)

# enable the speaker
spkrenable = DigitalInOut(board.SPEAKER_ENABLE)
spkrenable.direction = Direction.OUTPUT
spkrenable.value = True

sample = audioio.AudioOut(board.SPEAKER, sine_wave)
sample.frequency = SAMPLERATE
sample.play(loop=True)  # keep playing the sample over and over
time.sleep(1)           # until...
sample.stop()           # we tell the board to stop
