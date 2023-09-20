# SPDX-FileCopyrightText: 2023 @todbot / Tod Kurt w mods by John Park
#
# SPDX-License-Identifier: MIT

# wavetable_midisynth_code_i2s.py -- simple wavetable synth that responds to MIDI
# 26 Jul 2023 - @todbot / Tod Kurt
# Demonstrate using wavetables to make a MIDI synth
# Needs WAV files from waveeditonline.com
# - BRAIDS01.WAV - http://waveeditonline.com/index-17.html

import time
import busio
import board
import audiomixer
import synthio
import digitalio
import audiobusio
import ulab.numpy as np
import adafruit_wave

import usb_midi
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
from adafruit_midi.control_change import ControlChange

auto_play = False  # set to true to have it play its own little song
auto_play_notes = [36, 38, 40, 41, 43, 45, 46, 48, 50, 52]
auto_play_speed = 0.9  # time in seconds between notes

midi_channel = 1

wavetable_fname = "wav/BRAIDS01.WAV"  # from http://waveeditonline.com/index-17.html
wavetable_sample_size = 256  # number of samples per wave in wavetable (256 is standard)
sample_rate = 44100
wave_lfo_min = 0  # which wavetable number to start from  10
wave_lfo_max = 6  # which wavetable number to go up to  25

# for PWM audio with an RC filter
# Pins used on QTPY RP2040:
# - board.MOSI - Audio PWM output (needs RC filter output)
# import audiopwmio
# audio = audiopwmio.PWMAudioOut(board.GP10)

# for I2S audio with external I2S DAC board
# import audiobusio

# I2S on Audio BFF or Amp BFF on QT Py:
# audio = audiobusio.I2SOut(bit_clock=board.A3, word_select=board.A2, data=board.A1)

# I2S audio on PropMaker Feather RP2040
power = digitalio.DigitalInOut(board.EXTERNAL_POWER)
power.switch_to_output(value=True)
audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)

mixer = audiomixer.Mixer(buffer_size=4096, voice_count=1, sample_rate=sample_rate, channel_count=1,
                         bits_per_sample=16, samples_signed=True)
audio.play(mixer)  # attach mixer to audio playback
synth = synthio.Synthesizer(sample_rate=sample_rate)
mixer.voice[0].play(synth)  # attach synth to mixer
mixer.voice[0].level = 1

uart = busio.UART(tx=board.TX, rx=board.RX, baudrate=31250, timeout=0.001)
midi_uart = adafruit_midi.MIDI(midi_in=uart, in_channel=midi_channel-1)
midi_usb = adafruit_midi.MIDI(midi_in=usb_midi.ports[0], in_channel=midi_channel-1)

# mix between values a and b, works with numpy arrays too,  t ranges 0-1
def lerp(a, b, t):
    return (1-t)*a + t*b

class Wavetable:
    """ A 'waveform' for synthio.Note that uses a wavetable w/ a scannable wave position."""
    def __init__(self, filepath, wave_len=256):
        self.w = adafruit_wave.open(filepath)
        self.wave_len = wave_len  # how many samples in each wave
        if self.w.getsampwidth() != 2 or self.w.getnchannels() != 1:
            raise ValueError("unsupported WAV format")
        self.waveform = np.zeros(wave_len, dtype=np.int16)  # empty buffer we'll copy into
        self.num_waves = self.w.getnframes() // self.wave_len
        self.set_wave_pos(0)

    def set_wave_pos(self, pos):
        """Pick where in wavetable to be, morphing between waves"""
        pos = min(max(pos, 0), self.num_waves-1)  # constrain
        samp_pos = int(pos) * self.wave_len  # get sample position
        self.w.setpos(samp_pos)
        waveA = np.frombuffer(self.w.readframes(self.wave_len), dtype=np.int16)
        self.w.setpos(samp_pos + self.wave_len)  # one wave up
        waveB = np.frombuffer(self.w.readframes(self.wave_len), dtype=np.int16)
        pos_frac = pos - int(pos)  # fractional position between wave A & B
        self.waveform[:] = lerp(waveA, waveB, pos_frac)  # mix waveforms A & B


wavetable1 = Wavetable(wavetable_fname, wave_len=wavetable_sample_size)

amp_env = synthio.Envelope(attack_level=0.2, sustain_level=0.2, attack_time=0.05, release_time=0.3,
                            decay_time=.5)
wave_lfo = synthio.LFO(rate=0.2, waveform=np.array((0, 32767), dtype=np.int16))
lpf = synth.low_pass_filter(4000, 1)  # cut some of the annoying harmonics

synth.blocks.append(wave_lfo)  # attach wavelfo to global lfo runner since cannot attach to note

notes_pressed = {}  # keys = midi note num, value = synthio.Note,

def note_on(notenum):
    # release old note at this notenum if present
    if oldnote := notes_pressed.pop(notenum, None):
        synth.release(oldnote)

    if not auto_play:
        wave_lfo.retrigger()

    f = synthio.midi_to_hz(notenum)

    vibrato_lfo = synthio.LFO(rate=1, scale=0.01)
    note = synthio.Note(frequency=f, waveform=wavetable1.waveform,
                         envelope=amp_env, filter=lpf, bend=vibrato_lfo)
    synth.press(note)
    notes_pressed[notenum] = note

def note_off(notenum):
    if note := notes_pressed.pop(notenum, None):
        synth.release(note)

def set_wave_lfo_minmax(wmin, wmax):
    scale = (wmax - wmin)
    wave_lfo.scale = scale
    wave_lfo.offset = wmin

last_synth_update_time = 0
def update_synth():
    # pylint: disable=global-statement
    global last_synth_update_time
    # only update 100 times a sec to lighten the load
    if time.monotonic() - last_synth_update_time > 0.01:
        # last_update_time = time.monotonic()
        wavetable1.set_wave_pos( wave_lfo.value )

last_auto_play_time = 0
auto_play_pos = -1
def update_auto_play():
    # pylint: disable=global-statement
    global last_auto_play_time, auto_play_pos
    if auto_play and time.monotonic() - last_auto_play_time > auto_play_speed:
        last_auto_play_time = time.monotonic()
        note_off( auto_play_notes[ auto_play_pos ] )
        auto_play_pos = (auto_play_pos + 3) % len(auto_play_notes)
        note_on( auto_play_notes[ auto_play_pos ] )


set_wave_lfo_minmax(wave_lfo_min, wave_lfo_max)

def map_range(s, a1, a2, b1, b2):
    return  b1 + ((s - a1) * (b2 - b1) / (a2 - a1))


print("wavetable midisynth i2s. auto_play:",auto_play)

while True:
    update_synth()
    update_auto_play()

    msg = midi_uart.receive() or midi_usb.receive()

    if isinstance(msg, NoteOn) and msg.velocity != 0:
        note_on(msg.note)

    elif isinstance(msg,NoteOff) or isinstance(msg,NoteOn) and msg.velocity==0:
        note_off(msg.note)

    elif isinstance(msg,ControlChange):
        if msg.control == 21:  # mod wheel
            scan_low = map_range(msg.value, 0,127, 0, 64)
            set_wave_lfo_minmax(scan_low, scan_low)
