# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import os
import random
import board
from digitalio import DigitalInOut, Direction
import neopixel
import audiocore
import audiobusio
import keypad
import adafruit_lis3dh

from rainbowio import colorwheel
hue = 0
# enable external power pin
# provides power to the external components
external_power = DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = Direction.OUTPUT
external_power.value = True

# external neopixels
num_pixels = 24
pixels = neopixel.NeoPixel(board.EXTERNAL_NEOPIXELS, num_pixels, brightness=0.4, auto_write=True)

# external button
switch = keypad.Keys((board.EXTERNAL_BUTTON,), value_when_pressed=False, pull=True)

wavs = []
wav_names = []
for filename in os.listdir('/wavs'):
    if filename.lower().endswith('.wav') and not filename.startswith('.'):
        wavs.append("/wavs/"+filename)
        wav_names.append(filename.replace('.wav', ''))

audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)

num_wavs = len(wavs)
wav_index = 0

def open_audio(num):
    n = wavs[num]
    f = open(n, "rb")
    w = audiocore.WaveFile(f)
    wn = wav_names[num]
    return w, wn
wave, wave_name = open_audio(wav_index)

colors = [
    {'label': "BLUE", 'color': 0x0000FF},
    {'label': "RED", 'color': 0xFF0000},
    {'label': "GREEN", 'color': 0x00FF00},
    {'label': "YELLOW", 'color': 0xFFFF00},
    {'label': "AQUA", 'color': 0x00FFFF},
    {'label': "PURPLE", 'color': 0xFF00FF},
    {'label': "PINK", 'color': 0xFF0055},
    {'label': "ORANGE", 'color': 0xFF5500},
    {'label': "WHITE", 'color': 0x555555},
    ]

i2c = board.I2C()
int1 = DigitalInOut(board.ACCELEROMETER_INTERRUPT)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, int1=int1)
lis3dh.range = adafruit_lis3dh.RANGE_2_G

while True:
    event = switch.events.get()
    if event:
        if event.pressed:
            wave, wave_name = open_audio(random.randint(0, 8))
            audio.play(wave)
            for color in colors:
                if color['label'] in wave_name:
                    pixels.fill(color['color'])
                else:
                    pass
            time.sleep(.7)
            pixels.fill((0, 0, 0))
            print('pressed')
        if event.released:
            pass
    if lis3dh.shake(shake_threshold=12):
        for v in wav_names:
            name = wav_names.index(v)
            if "SHAKE" in v:
                wave, wave_name = open_audio(name)
                audio.play(wave)
                for i in range(num_pixels):
                    pixels[i] = colorwheel(hue)
                    hue = (hue + 30) % 256
                    print(hue)
                time.sleep(.7)
                pixels.fill((0, 0, 0))
                print('shake')
