# SPDX-FileCopyrightText: 2023 John Park and @todbot / Tod Kurt
#
# SPDX-License-Identifier: MIT

import time
import board
import digitalio
import audiomixer
import synthio
import ulab.numpy as np

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

amp_env_slow = synthio.Envelope(
                                attack_time=0.15,
                                sustain_level=1.0,
                                release_time=0.8
)
synth = synthio.Synthesizer(channel_count=1, sample_rate=44100, envelope=amp_env_slow)

audio.play(mixer)
mixer.voice[0].play(synth)
mixer.voice[0].level = 0.6

# create sine, tri, saw & square single-cycle waveforms to act as oscillators
SAMPLE_SIZE = 512
SAMPLE_VOLUME = 32000  # 0-32767
half_period = SAMPLE_SIZE // 2
wave_sine = np.array(np.sin(np.linspace(0, 2*np.pi, SAMPLE_SIZE, endpoint=False)) * SAMPLE_VOLUME,
                     dtype=np.int16)
wave_saw = np.linspace(SAMPLE_VOLUME, -SAMPLE_VOLUME, num=SAMPLE_SIZE, dtype=np.int16)
wave_tri = np.concatenate((np.linspace(-SAMPLE_VOLUME, SAMPLE_VOLUME, num=half_period,
                            dtype=np.int16),
                                np.linspace(SAMPLE_VOLUME, -SAMPLE_VOLUME, num=half_period,
                                dtype=np.int16)))
wave_square = np.concatenate((np.full(half_period, SAMPLE_VOLUME, dtype=np.int16),
                              np.full(half_period, -SAMPLE_VOLUME, dtype=np.int16)))

midi_note = 65


while True:
    # create notes using those waveforms
    note1 = synthio.Note(synthio.midi_to_hz(midi_note), waveform=wave_sine, amplitude=1)
    synth.press(note1)
    time.sleep(0.75)
    synth.release(note1)
    time.sleep(.75)

    note1 = synthio.Note(synthio.midi_to_hz(midi_note), waveform=wave_tri, amplitude=0.7)
    synth.press(note1)
    time.sleep(0.75)
    synth.release(note1)
    time.sleep(.75)

    note1 = synthio.Note(synthio.midi_to_hz(midi_note), waveform=wave_saw, amplitude=0.25)
    synth.press(note1)
    time.sleep(0.75)
    synth.release(note1)
    time.sleep(.75)

    note1 = synthio.Note(synthio.midi_to_hz(midi_note), waveform=wave_square, amplitude=0.2)
    synth.press(note1)
    time.sleep(0.75)
    synth.release(note1)
    time.sleep(.75)
