# SPDX-FileCopyrightText: 2023 John Park and @todbot / Tod Kurt
#
# SPDX-License-Identifier: MIT

import board
import digitalio
import audiomixer
import synthio
import usb_midi
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff

# note for ESP32-S2 boards, due to not enough available endpoints,
# to enable USB MIDI, create a "boot.py" with following in it, then power cycle board:
#  import usb_hid
#  import usb_midi
#  usb_hid.disable()
#  usb_midi.enable()
#  print("enabled USB MIDI, disabled USB HID")


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

mixer = audiomixer.Mixer(channel_count=1, sample_rate=22050, buffer_size=2048)

midi = adafruit_midi.MIDI(midi_in=usb_midi.ports[0], in_channel=0)

amp_env_med = synthio.Envelope(
                                attack_time=0.05,
                                sustain_level=0.8,
                                release_time=0.2
)

synth = synthio.Synthesizer(channel_count=1, sample_rate=22050, envelope=amp_env_med)

note1 = synthio.Note(frequency=330, filter=None)

audio.play(mixer)
mixer.voice[0].play(synth)
mixer.voice[0].level = 0.2

while True:
    msg = midi.receive()
    if isinstance(msg, NoteOn) and msg.velocity != 0:
        print("noteOn: ", msg.note, "vel:", msg.velocity)
        note1.frequency = synthio.midi_to_hz(msg.note)
        synth.press(note1)
    elif isinstance(msg, NoteOff) or isinstance(msg, NoteOn) and msg.velocity == 0:
        print("noteOff:", msg.note, "vel:", msg.velocity)
        note1.frequency = synthio.midi_to_hz(msg.note)
        synth.release(note1)
