# SPDX-FileCopyrightText: 2023 John Park and @todbot / Tod Kurt
#
# SPDX-License-Identifier: MIT

import board
import busio
import digitalio
import audiomixer
import synthio
import usb_midi
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
from adafruit_midi.control_change import ControlChange

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

midi_channel = 1
uart = busio.UART(tx=board.TX, rx=board.RX, baudrate=31250, timeout=0.001)
midi_usb = adafruit_midi.MIDI(midi_in=usb_midi.ports[0], in_channel=0)
midi_uart = adafruit_midi.MIDI(midi_in=uart, in_channel=midi_channel-1)

amp_env_med = synthio.Envelope(
                                attack_time=0.05,
                                sustain_level=0.8,
                                release_time=0.2
)

synth = synthio.Synthesizer(channel_count=1, sample_rate=22050, envelope=amp_env_med)
# set up filters
filter_freq = 4000
filter_res = 0.5
filter_freq_lo = 100   # filter lowest freq
filter_freq_hi = 4500  # filter highest freq
filter_res_lo = 0.5    # filter q lowest value
filter_res_hi = 2.0    # filter q highest value
lpf = synth.low_pass_filter(filter_freq, filter_res)
note1 = synthio.Note(frequency=330, filter=lpf)

audio.play(mixer)
mixer.voice[0].play(synth)
mixer.voice[0].level = 0.2

def map_range(s, a1, a2, b1, b2):
    return b1 + ((s - a1) * (b2 - b1) / (a2 - a1))


while True:
    note1.filter = synth.low_pass_filter(filter_freq, filter_res)

    msg = midi_uart.receive() or midi_usb.receive()

    if isinstance(msg, NoteOn) and msg.velocity != 0:
        print("noteOn: ", msg.note, "vel:", msg.velocity)
        note1.frequency = synthio.midi_to_hz(msg.note)
        synth.press(note1)

    elif isinstance(msg, NoteOff) or isinstance(msg, NoteOn) and msg.velocity == 0:
        print("noteOff:", msg.note, "vel:", msg.velocity)
        note1.frequency = synthio.midi_to_hz(msg.note)
        synth.release(note1)

    elif isinstance(msg, ControlChange):
        print("CC", msg.control, "=", msg.value)
        if msg.control == 21:  # filter cutoff
            filter_freq = map_range(msg.value, 0, 127, filter_freq_lo, filter_freq_hi)
        elif msg.control == 22:  # filter Q
            filter_res = map_range(msg.value, 0, 127, filter_res_lo, filter_res_hi)
        elif msg.control == 7:  # volume
            mixer.voice[0].level = map_range(msg.value, 0, 127, 0.0, 1.0)
