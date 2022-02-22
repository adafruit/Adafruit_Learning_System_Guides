# SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
#import math
import array
from digitalio import DigitalInOut, Direction, Pull
import analogio
import supervisor
import audioio
import audiocore
import board
from rainbowio import colorwheel
import neopixel

# NeoPixels
pixel_pin = board.A1
num_pixels = 30
pixels = neopixel.NeoPixel(pixel_pin, num_pixels,
                           brightness=1, auto_write=False)
pixels.fill((0, 0, 0))
pixels.show()

ring = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=1)
ring.fill((255, 0, 0))

# Light sensor
light = analogio.AnalogIn(board.LIGHT)

BRIGHT = 40000
DARK = 10000
ACTIVITY_THRESHOLD = 20000

# button
button_a = DigitalInOut(board.BUTTON_A)
button_a.direction = Direction.INPUT
button_a.pull = Pull.DOWN

# audio output
cpx_audio = audioio.AudioOut(board.A0)
def play_file(wavfile):
    with open(wavfile, "rb") as f:
        wav = audiocore.WaveFile(f)
        cpx_audio.play(wav)
        while cpx_audio.playing:
            pass
# Generate one period of wave.
length = 8000 // 440
wave_array = array.array("H", [0] * length)
for i in range(length):
    # Sine wave
    # wave_array[i] = int(math.sin(math.pi * 2 * i / 18) * (2 ** 15) + 2 ** 15)
    # Triangle wave
    # wave_array[i] = int( i/length * (2 ** 16))
    # Saw wave
    if i < length/2:
        wave_array[i] = int(i*2/length * (2 ** 16 - 1))
    else:
        wave_array[i] = int((2**16 - 1) - i*2/length * (2 ** 16))
    print((wave_array[i],))

def map_range(x, in_min, in_max, out_min, out_max):
    # Maps a number from one range to another.
    mapped = (x-in_min) * (out_max - out_min) / (in_max-in_min) + out_min
    if out_min <= out_max:
        return max(min(mapped, out_max), out_min)
    return min(max(mapped, out_max), out_min)


time.sleep(2)

play_file("01_approach.wav")

while not button_a.value:
    pass  # wait for it to be pressed

if button_a.value:  # A pressed
    while button_a.value:  # wait for release
        pass

time.sleep(1)

play_file("02_last_day.wav")

time.sleep(1)

timeout = time.monotonic()

while True:
    print((light.value,))

    # determine height of pixels
    pixel_height = map_range(light.value, DARK, BRIGHT, 0, num_pixels)
    pixels.fill((0, 0, 0))
    for p in range(pixel_height):
        pixels[p] = colorwheel(int(p / num_pixels * 255))
        pixels.show()

    # determine squeek
    freq = int(map_range(light.value, DARK, BRIGHT, 440, 8800))
    sine_wave = audiocore.RawSample(wave_array, channel_count=1, sample_rate=freq)
    cpx_audio.stop()
    cpx_audio.play(sine_wave, loop=True)

    # check no activity
    if light.value > ACTIVITY_THRESHOLD:
        timeout = time.monotonic()  # reset our timeout

    # 4 seconds no activity
    if time.monotonic() - timeout > 4:
        break

pixels.fill((255, 0, 0))
pixels.show()
play_file("03_no_sanctuary.wav")

time.sleep(1)

# restart
supervisor.reload()
