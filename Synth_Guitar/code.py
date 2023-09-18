# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import digitalio
import audiobusio
import board
import neopixel
import adafruit_lis3dh
import synthio
import keypad
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
import ulab.numpy as np
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.neopixel import NeoPixel as SS_NeoPixel
from adafruit_seesaw.digitalio import DigitalIO
from adafruit_seesaw.rotaryio import IncrementalEncoder
import audiomixer
import busio
import simpleio

i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)

int1 = digitalio.DigitalInOut(board.ACCELEROMETER_INTERRUPT)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, int1=int1)
lis3dh.range = adafruit_lis3dh.RANGE_2_G

ss_enc0 = Seesaw(i2c, addr=0x36)
ss_enc0.pin_mode(24, ss_enc0.INPUT_PULLUP)
button0 = DigitalIO(ss_enc0, 24)
button0_state = False
enc0 = IncrementalEncoder(ss_enc0)
ss_enc0.set_GPIO_interrupts(1 << 24, True)
ss_enc0.enable_encoder_interrupt(encoder=0)

ss_enc1 = Seesaw(i2c, addr=0x37)
ss_enc1.pin_mode(24, ss_enc1.INPUT_PULLUP)
button1 = DigitalIO(ss_enc1, 24)
button1_state = False
enc1 = IncrementalEncoder(ss_enc1)
ss_enc1.set_GPIO_interrupts(1 << 24, True)
ss_enc1.enable_encoder_interrupt(encoder=0)

ss_enc2 = Seesaw(i2c, addr=0x38)
ss_enc2.pin_mode(24, ss_enc2.INPUT_PULLUP)
button2 = DigitalIO(ss_enc2, 24)
button2_state = False
enc2 = IncrementalEncoder(ss_enc2)
ss_enc2.set_GPIO_interrupts(1 << 24, True)
ss_enc2.enable_encoder_interrupt(encoder=0)

neokey0 = Seesaw(i2c, addr=0x30)
neokey1 = Seesaw(i2c, addr=0x31)

keys = []
for k in range(4, 8):
    key0 = DigitalIO(neokey0, k)
    key0.direction = digitalio.Direction.INPUT
    key0.pull = digitalio.Pull.UP
    keys.append(key0)
for k in range(4, 8):
    key1 = DigitalIO(neokey1, k)
    key1.direction = digitalio.Direction.INPUT
    key1.pull = digitalio.Pull.UP
    keys.append(key1)

NUM_PIXELS = 8
NEOPIXEL_PIN = board.EXTERNAL_NEOPIXELS

pixels = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, auto_write=True)

pixels.brightness = 0.1

enable = digitalio.DigitalInOut(board.EXTERNAL_POWER)
enable.direction = digitalio.Direction.OUTPUT
enable.value = True
strum_switch = digitalio.DigitalInOut(board.D12)
strum_switch.direction = digitalio.Direction.INPUT
strum_switch.pull = digitalio.Pull.UP

int_keys = keypad.Keys((board.D5, board.D6, board.D9, board.EXTERNAL_BUTTON),
                        value_when_pressed=False, pull=True, interval = 0.001)

key_pix0 = SS_NeoPixel(neokey0, 3, 4, auto_write = True)
key_pix0.brightness = 1
key_pix1 = SS_NeoPixel(neokey1, 3, 4, auto_write = True)
key_pix1.brightness = 1

key_pixels = [key_pix0[0], key_pix0[1], key_pix0[2], key_pix0[3],
              key_pix1[0], key_pix1[1], key_pix1[2], key_pix1[3]]

# i2s audio
audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)

key_states = [False, False, False, False, False, False, False, False]
key_colors = [0xFF0000, 0xFF5500, 0xFFFF00, 0x00FF00, 0x00FFFF, 0x0000FF, 0x5500FF, 0xFF00FF]
for c in range(4):
    key_pix0[c] = key_colors[c]
    key_pix1[c] = key_colors[c + 4]

SAMPLE_RATE = 22050
SAMPLE_SIZE = 512
VOLUME = 32000

square = np.concatenate((np.ones(SAMPLE_SIZE//2, dtype=np.int16)*VOLUME,np.ones(SAMPLE_SIZE//2,
                         dtype=np.int16)*-VOLUME))
sine = np.array(np.sin(np.linspace(0, 2*np.pi, SAMPLE_SIZE, endpoint=False)) * VOLUME,
                       dtype=np.int16)

amp_env = synthio.Envelope(attack_time=0.01,
                                sustain_level=0.5,
                                release_time=0.1)

lfo_tremo = synthio.LFO(waveform=sine, rate=5)

synth = synthio.Synthesizer(sample_rate=SAMPLE_RATE)

synth_notes = []

octave = 12
mult = 2
octave_range = 6
tones = [36, 40, 43, 47, 50, 53, 57, 60]
diatonic = 0
t = [0, 0, 0, 0, 0, 0, 0, 0]
current_freq = []
for s in range(8):
    t[s] = tones[s] + (octave * mult)
    print(t[s])
    note = synthio.Note(frequency=synthio.midi_to_hz(t[s]),
                        envelope=amp_env, waveform=square,
                        amplitude = lfo_tremo)
    synth_notes.append(note)
    current_freq.append(synth_notes[s].frequency)

lfo_frequency = 2000
lfo_resonance = 1.5
lpf = synth.low_pass_filter(lfo_frequency, lfo_resonance)
hpf = synth.high_pass_filter(lfo_frequency, lfo_resonance)

synth_volume = 0.3
last_pos0 = synth_volume
last_pos1 = 0
last_pos2 = 0

mixer = audiomixer.Mixer(voice_count=1, sample_rate=SAMPLE_RATE, channel_count=1,
                         bits_per_sample=16, samples_signed=True, buffer_size=2048)
audio.play(mixer)
mixer.voice[0].play(synth)
mixer.voice[0].level = synth_volume

int_number = 0
def normalize(val, min_v, max_v):
    return max(min(max_v, val), min_v)

key_pressed = 0
strum = False
last_strum = strum
tremolo = True
pressed_notes = []
last_y = 0
accel_time = 0.1
accel_clock = ticks_ms()
accel_time = int(accel_time * 1000)

while True:

    interrupt_event = int_keys.events.get()
    strum = strum_switch.value
    if last_strum != strum:
        synth.release_all()
        last_strum = strum
    if interrupt_event:
        int_number = interrupt_event.key_number
        if int_number == 0 and interrupt_event.pressed:
            pos0 = -enc0.position
            if pos0 != last_pos0:
                if pos0 > last_pos0:
                    synth_volume = synth_volume + 0.1
                else:
                    synth_volume = synth_volume - 0.1
                synth_volume = normalize(synth_volume, 0.0, 1.0)
                print(synth_volume)
                mixer.voice[0].level = synth_volume
                last_pos0 = pos0
            if not button0.value and not button0_state:
                button0_state = True
                if mixer.voice[0].level > 0:
                    mixer.voice[0].level = 0
                else:
                    mixer.voice[0].level = synth_volume
            if button0.value and button0_state:
                button0_state = False
        elif int_number == 1 and interrupt_event.pressed:
            pos1 = -enc1.position
            if pos1 != last_pos1:
                if pos1 > last_pos1:
                    lfo_tremo.rate = lfo_tremo.rate + 0.5
                else:
                    lfo_tremo.rate = lfo_tremo.rate - 0.5
                lfo_tremo.rate = normalize(lfo_tremo.rate, 1.0, 20.0)
                print(lfo_tremo.rate)
                last_pos1 = pos1
            if tremolo:
                if not button1.value and not button1_state:
                    button1_state = True
                    tremolo = False
                    for i in range(8):
                        synth_notes[i].amplitude = 1.0
                if button1.value and button1_state:
                    button1_state = False
            else:
                if not button1.value and not button1_state:
                    button1_state = True
                    tremolo = True
                    for i in range(8):
                        lfo_tremo.rate = 5.0
                        synth_notes[i].amplitude = lfo_tremo
                if button1.value and button1_state:
                    button1_state = False
        elif int_number == 2 and interrupt_event.pressed:
            pos2 = -enc2.position
            if pos2 != last_pos2:
                if pos2 > last_pos2:
                    mult = (mult + 1) % octave_range
                    print(mult)
                    for o in range(8):
                        t[o] = tones[o] + (octave * mult)
                        print(t[o])
                        synth_notes[o].frequency = synthio.midi_to_hz(t[o])
                        current_freq[o] = synth_notes[o].frequency
                else:
                    mult = (mult - 1) % octave_range
                    print(mult)
                    for o in range(8):
                        t[o] = tones[o] + (octave * mult)
                        print(t[o])
                        synth_notes[o].frequency = synthio.midi_to_hz(t[o])
                        current_freq[o] = synth_notes[o].frequency
                last_pos2 = pos2
            if not button2.value and not button2_state:
                button2_state = True
                diatonic = (diatonic + 1) % 2
                print(diatonic)
                if diatonic == 0:
                    new_tones = [36, 40, 43, 47, 50, 53, 57, 60]
                    for r in range(8):
                        tones[r] = new_tones[r]
                        print(tones[r])
                else:
                    new_tones = [36, 38, 40, 41, 43, 45, 47, 48]
                    for r in range(8):
                        tones[r] = new_tones[r]
                        print(tones[r])
                for x in range(8):
                    t[x] = tones[x] + (octave * mult)
                    print(t[x])
                    synth_notes[x].frequency = synthio.midi_to_hz(t[x])
                    current_freq[x] = synth_notes[x].frequency
            if button2.value and button2_state:
                button2_state = False
        elif int_number == 3 and interrupt_event.pressed:
            if strum:
                for i in range(0, 8):
                    if not keys[i].value:
                        pixels.fill(key_colors[i])
                        pixels.show()
                        synth.press(synth_notes[i])
        elif int_number == 3 and interrupt_event.released:
            if strum:
                synth.release_all()
        ss_enc0.get_GPIO_interrupt_flag()
        ss_enc1.get_GPIO_interrupt_flag()
        ss_enc2.get_GPIO_interrupt_flag()
    if ticks_diff(ticks_ms(), accel_clock) >= accel_time:
        x, y, z = [
            value / adafruit_lis3dh.STANDARD_GRAVITY for value in lis3dh.acceleration
            ]
        if last_y != y:
            if abs(last_y - y) > 0.01:
                # print(f"x = {x:.3f} G, y = {y:.3f} G, z = {z:.3f} G")
                if y < -0.500:
                    mapped_freq = simpleio.map_range(y, -0.300, -1, 2000, 10000)
                    mapped_resonance = simpleio.map_range(y, -0.300, -1, 1.5, 8)
                    hpf = synth.high_pass_filter(mapped_freq, mapped_resonance)
                    for i in range(0, 8):
                        synth_notes[i].filter = hpf
                elif y > 0.200:
                    mapped_freq = simpleio.map_range(y, 0.200, 1, 2000, 100)
                    mapped_resonance = simpleio.map_range(y, 0.200, 1, 2, 0.5)
                    lpf = synth.low_pass_filter(mapped_freq, mapped_resonance)
                    for i in range(0, 8):
                        synth_notes[i].filter = lpf
                else:
                    for i in range(0, 8):
                        synth_notes[i].filter = None
            last_y = y
        accel_clock = ticks_add(accel_clock, accel_time)
    if not strum:
        for i in range(0, 8):
            if not keys[i].value and not key_states[i]:
                pixels.fill(key_colors[i])
                pixels.show()
                synth.press(synth_notes[i])
                key_states[i] = True
            if keys[i].value and key_states[i]:
                key_pixels[i] = key_colors[i]
                synth.release(synth_notes[i])
                key_states[i] = False
