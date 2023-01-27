# SPDX-FileCopyrightText: 2023 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import audiocore
import board
import audiobusio
import audiomixer
from digitalio import DigitalInOut, Pull
from adafruit_debouncer import Button

button_pins = (
                board.D2, board.D3, board.D4, board.D5,
                board.D6, board.D7, board.D8, board.D9,
                board.D10, board.MOSI, board.MISO, board.SCK,
)
buttons = []   # will hold list of Debouncer button objects
for pin in button_pins:   # set up each pin
    tmp_pin = DigitalInOut(pin)  # defaults to input
    tmp_pin.pull = Pull.UP      # turn on internal pull-down resistor
    buttons.append(Button(tmp_pin, value_when_pressed=False))

# get the filenames in aplha order from files in the 'wavs' directory
sounds = []
for filename in sorted(os.listdir("/wavs")):
    filename = filename.lower()
    if filename.endswith(".wav") and not filename.startswith("."):
        sounds.append(filename)

audio = audiobusio.I2SOut(bit_clock=board.A1, word_select=board.A2, data=board.A3)
mixer = audiomixer.Mixer(voice_count=1, sample_rate=11025, channel_count=1,
                         bits_per_sample=16, samples_signed=True)

audio.play(mixer)
mixer.voice[0].level = 0.5

def play_sound(sound_number):
    wave_file = open(("wavs/" + sounds[sound_number]), "rb")
    wave = audiocore.WaveFile(wave_file)
    mixer.voice[0].play(wave, loop=False)


while True:
    for i in range(len(buttons)):
        buttons[i].update()
        if buttons[i].pressed:
            play_sound(i)
