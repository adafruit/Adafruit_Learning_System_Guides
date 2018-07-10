import time
import array
import math
import audioio
import board
import digitalio

button = digitalio.DigitalInOut(board.A1)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

length = 8000 // 440
tone_volume = 0.1  # Increase this to increase the volume of the tone.
sine_wave = array.array("H", [0] * length)
for i in range(length):
    sine_wave[i] = int((1 + math.sin(math.pi * 2 * i / 18)) * tone_volume * (2 ** 15))

audio = audioio.AudioOut(board.A0)
sine_wave = audioio.RawSample(sine_wave)
while True:
    if not button.value:
        audio.play(sine_wave, loop=True)
        time.sleep(1)
        audio.stop()
