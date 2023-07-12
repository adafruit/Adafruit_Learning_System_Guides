# SPDX-FileCopyrightText: 2023 John Park & Tod Kurt
#
# SPDX-License-Identifier: MIT
# Tyrell Synth Distopia
# based on:
# 19 Jun 2023 - @todbot / Tod Kurt
# - A swirling ominous wub that evolves over time
# - Made for QTPy RP2040 but will work on any synthio-capable board
# - wallow in the sound
#
# Circuit:
# - QT Py RP2040
# - QTPy TX/RX pins for audio out, going through RC filter (1k + 100nF) to TRS jack
#  Touch io for eight pins, pairs that -/+ tempo, transpose pitch, filter rate, volume
#   use >1MΩ resistors to pull down to ground
#
# Code:
#  - Five detuned oscillators are randomly detuned very second or so
#  - A low-pass filter is slowly modulated over the filters
#  - The filter modulation rate also changes randomly every second (also reflected on neopixel)
#  - Every x seconds a new note is randomly chosen from the allowed note list

import time
import random
import board
import audiopwmio
import audiomixer
import synthio
import ulab.numpy as np
import neopixel
import rainbowio
import touchio
from adafruit_debouncer import Debouncer

touch_pins = (board.A0, board.A1, board.A2, board.A3, board.SDA, board.SCL, board.MISO, board.MOSI)
touchpads = []
for pin in touch_pins:
    tmp_pin = touchio.TouchIn(pin)
    touchpads.append(Debouncer(tmp_pin))

notes = (37, 38, 35, 49)  # MIDI C#, D, B
note_duration = 10   # how long each note plays for
num_voices = 6       # how many voices for each note
lpf_basef = 300      # low pass filter lowest frequency
lpf_resonance = 1.7  # filter q

led = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.1)

# PWM pin pair on QTPY RP2040
audio = audiopwmio.PWMAudioOut(left_channel=board.TX, right_channel=board.RX)

mixer = audiomixer.Mixer(channel_count=2, sample_rate=28000, buffer_size=2048)
synth = synthio.Synthesizer(channel_count=2, sample_rate=28000)
audio.play(mixer)
mixer.voice[0].play(synth)
mixer_vol = 0.5
mixer.voice[0].level = mixer_vol

# oscillator waveform, a 512 sample downward saw wave going from +/-30k
wave_saw = np.linspace(30000, -30000, num=512, dtype=np.int16)  # max is +/-32k gives us headroom
amp_env = synthio.Envelope(attack_level=1, sustain_level=1)

# set up the voices (aka "Notes" in synthio-speak) w/ initial values
voices = []
for i in range(num_voices):
    voices.append(synthio.Note(frequency=0, envelope=amp_env, waveform=wave_saw))

lfo_panning = synthio.LFO(rate=0.1, scale=0.75)

# set all the voices to the "same" frequency (with random detuning)
# zeroth voice is sub-oscillator, one-octave down
def set_notes(n):
    for voice in voices:
        f = synthio.midi_to_hz(n + random.uniform(0, 0.4))
        voice.frequency = f
        voice.panning = lfo_panning
    voices[0].frequency = voices[0].frequency/2  # bass note one octave down

# the LFO that modulates the filter cutoff
lfo_filtermod = synthio.LFO(rate=0.05, scale=2000, offset=2000)
# we can't attach this directly to a filter input, so stash it in the blocks runner
synth.blocks.append(lfo_filtermod)

note = notes[0]
last_note_time = time.monotonic()
last_filtermod_time = time.monotonic()

# start the voices playing
set_notes(note)
synth.press(voices)

# user input variables
note_offset = (0, 1, 3, 4, 5, 7)
note_offset_index = 0

lfo_subdivision = 8

print("'Prepare to wallow.' \n- Major Jack Dongle")


while True:
    for t in range(len(touchpads)):
        touchpads[t].update()
        if touchpads[t].rose:
            if t == 0:
                note_offset_index = (note_offset_index + 1) % (len(note_offset))
                set_notes(note + note_offset[note_offset_index])
            elif t == 1:
                note_offset_index = (note_offset_index - 1) % (len(note_offset))
                set_notes(note + note_offset[note_offset_index])

            elif t == 2:
                note_duration = note_duration + 1
            elif t == 3:
                note_duration = abs(max((note_duration - 1), 1))

            elif t == 4:
                lfo_subdivision = 20
            elif t == 5:
                lfo_subdivision = 0.2

            elif t == 6:  # volume
                mixer_vol = max(mixer_vol - 0.05, 0.0)
                mixer.voice[0].level = mixer_vol

            elif t == 7:  # volume
                mixer_vol = min(mixer_vol + 0.05, 1.0)
                mixer.voice[0].level = mixer_vol

    # continuosly update filter, no global filter, so update each voice's filter
    for v in voices:
        v.filter = synth.low_pass_filter(lpf_basef + lfo_filtermod.value, lpf_resonance)

    led.fill(rainbowio.colorwheel(lfo_filtermod.value/20))  # show filtermod moving

    if time.monotonic() - last_filtermod_time > 1:
        last_filtermod_time = time.monotonic()
        # randomly modulate the filter frequency ('rate' in synthio) to make more dynamic
        lfo_filtermod.rate = 0.01 + random.random() / lfo_subdivision

    if time.monotonic() - last_note_time > note_duration:
        last_note_time = time.monotonic()
        # pick new note, but not one we're currently playing
        note = random.choice([n for n in notes if n != note])
        set_notes(note+note_offset[note_offset_index])
        print("note", note, ["%3.2f" % v.frequency for v in voices])
