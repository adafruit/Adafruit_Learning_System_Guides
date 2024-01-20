# SPDX-FileCopyrightText: 2023 John Park and @todbot / Tod Kurt
#
# SPDX-License-Identifier: MIT

import board
import digitalio
import audiomixer
import synthio

# for PWM audio with an RC filter
# import audiopwmio
# audio = audiopwmio.PWMAudioOut(board.GP10)

# for I2S audio with external I2S DAC board
import audiobusio

# I2S on Audio BFF or Amp BFF on QT Py:
# audio = audiobusio.I2SOut(bit_clock=board.A3, word_select=board.A2, data=board.A1)

# I2S audio on PropMaker Feather RP2040
power = digitalio.DigitalInOut(board.EXTERNAL_POWER)
power.switch_to_output(value=True)
audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)

mixer = audiomixer.Mixer(channel_count=1, sample_rate=44100, buffer_size=4096)
synth = synthio.Synthesizer(channel_count=1, sample_rate=44100)

audio.play(mixer)
mixer.voice[0].play(synth)
mixer.voice[0].level = 0.1

lfo = synthio.LFO(rate=0.6, scale=0.05)  # 1 Hz lfo at 0.25%
midi_note = 52
note = synthio.Note(synthio.midi_to_hz(midi_note), bend=lfo)
synth.press(note)


while True:
    pass
