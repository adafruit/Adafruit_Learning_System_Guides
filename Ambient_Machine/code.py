# SPDX-FileCopyrightText: 2023 John Park
#
# SPDX-License-Identifier: MIT
# Ambient Machine inspired by Yuri Suzuki https://www.yurisuzuki.com/projects/the-ambient-machine
import os
import board
import busio
import audiocore
import audiobusio
import audiomixer
from digitalio import Pull
from adafruit_debouncer import Debouncer
from adafruit_mcp230xx.mcp23017 import MCP23017

i2c = busio.I2C(board.SCL, board.SDA)
mcp_a = MCP23017(i2c, address=0x20)  # default address
mcp_b = MCP23017(i2c, address=0x21)  # MCP23017 w/ address 0 jumper set

switches = []  # set up all the switch pins on two MCP23017 boards as debouncer switches
for p in (8,9,10,11,12,4,3,2,1,0):
    pin = mcp_a.get_pin(p)
    pin.switch_to_input(pull=Pull.UP)
    switches.append(Debouncer(pin))
for p in (8,9,10,11,12,4,3,2,1,0):
    pin = mcp_b.get_pin(p)
    pin.switch_to_input(pull=Pull.UP)
    switches.append(Debouncer(pin))

switch_states = [False] * 20  # list of switch states

wav_files = []

for filename in os.listdir('/samples/'):  # on board flash
    if filename.lower().endswith('.wav') and not filename.startswith('.'):
        wav_files.append("/samples/"+filename)
        print(filename)

wav_files.sort()  # put in alphabetical/numberical order

# Metro M7 pins for the I2S amp:
lck_pin, bck_pin, dat_pin = board.D9, board.D10, board.D12

audio = audiobusio.I2SOut(bit_clock=bck_pin, word_select=lck_pin, data=dat_pin)
mixer = audiomixer.Mixer(voice_count=len(wav_files), sample_rate=22050, channel_count=1,
                         bits_per_sample=16, samples_signed=True, buffer_size=8192)
audio.play(mixer)

for i in range(10):  # start playing all wavs on loop w levels down
    wave = audiocore.WaveFile(open(wav_files[i], "rb"))
    mixer.voice[i].play(wave, loop=True)
    mixer.voice[i].level = 0.0


while True:
    for i in range(len(switches)):
        switches[i].update()
        if i < 5:  # first row plays five samples
            if switches[i].fell:
                if switch_states[i+5] is True:  # check volume switch
                    mixer.voice[i].level = 0.4  # if up
                else:
                    mixer.voice[i].level = 0.2  # if down
                switch_states[i] = not switch_states[i]
            if switches[i].rose:
                mixer.voice[i].level = 0.0
                switch_states[i] = not switch_states[i]

        elif 4 < i < 10:  # second row adjusts volume of first row
            if switches[i].fell:
                if switch_states[i-5] is True:  # raise  volume if it is on
                    mixer.voice[i-5].level = 0.4
                switch_states[i] = not switch_states[i]
            if switches[i].rose:
                if switch_states[i-5] is True:  # lower volume if it is on
                    mixer.voice[i-5].level = 0.2
                switch_states[i] = not switch_states[i]

        elif 9 < i < 15:  # third row plays five different samples
            if switches[i].fell:
                if switch_states[i+5] is True:
                    mixer.voice[i-5].level = 0.4
                else:
                    mixer.voice[i-5].level = 0.2
                switch_states[i] = not switch_states[i]
            if switches[i].rose:
                mixer.voice[i-5].level = 0.0
                switch_states[i] = not switch_states[i]

        elif 14 < i < 20:  # fourth row adjust volumes of third row
            if switches[i].fell:
                if switch_states[i-5] is True:
                    mixer.voice[i-10].level = 0.4
                switch_states[i] = not switch_states[i]
            if switches[i].rose:
                if switch_states[i-5] is True:
                    mixer.voice[i-10].level = 0.2
                switch_states[i] = not switch_states[i]
