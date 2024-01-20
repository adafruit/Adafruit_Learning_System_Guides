# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

from random import randint
import ulab.numpy as np
import board
import audiobusio
import audiomixer
import synthio
import simpleio
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
from adafruit_ht16k33 import segments
from adafruit_ht16k33.matrix import Matrix8x8x2
from adafruit_seesaw import seesaw, rotaryio, digitalio

SAMPLE_RATE = 44100
SAMPLE_SIZE = 256
VOLUME = 5000

# waveforms, envelopes and synth setup

square = np.concatenate((np.ones(SAMPLE_SIZE//2, dtype=np.int16)*VOLUME,np.ones(SAMPLE_SIZE//2,
                         dtype=np.int16)*-VOLUME))
sine = np.array(np.sin(np.linspace(0, 4*np.pi, SAMPLE_SIZE, endpoint=False)) * VOLUME,
                       dtype=np.int16)
saw = np.linspace(VOLUME, -VOLUME, num=SAMPLE_SIZE, dtype=np.int16)
noise = np.array([randint(-VOLUME, VOLUME) for i in range(SAMPLE_SIZE)], dtype=np.int16)

lfo = synthio.LFO(rate = .5, waveform = sine)

amp_env0 = synthio.Envelope(attack_time=0.1, decay_time = 0.1, release_time=0.1,
                           attack_level=1, sustain_level=0.05)
amp_env1 = synthio.Envelope(attack_time=0.05, decay_time = 0.1, release_time=0.1,
                           attack_level=1, sustain_level=0.05)

# synth plays the notes
synth = synthio.Synthesizer(sample_rate=SAMPLE_RATE)

# these are the notes
synth0 =  synthio.Note(frequency = 0.0, envelope=amp_env0, waveform=square, ring_frequency = 0,
                       ring_bend = lfo, ring_waveform = sine)
synth1 =  synthio.Note(frequency = 0.0, envelope=amp_env1, waveform=sine, ring_frequency = 0,
                       ring_bend = lfo, ring_waveform = sine)
synth2 =  synthio.Note(frequency = 0.0, envelope=amp_env0, waveform=square, ring_frequency = 0,
                       ring_bend = lfo, ring_waveform = sine)
synth3 =  synthio.Note(frequency = 0.0, envelope=amp_env1, waveform=sine, ring_frequency = 0,
                       ring_bend = lfo, ring_waveform = sine)

synths = [synth0, synth1, synth2, synth3]
wave_names = ["SQUR", "SINE", "SAW ", "NOIZ"]
waveforms = [square, sine, saw, noise]
synth0_wave = 0
synth1_wave = 1
synth2_wave = 0
synth3_wave = 1

# i2s amp setup
audio = audiobusio.I2SOut(bit_clock=board.D10, word_select=board.D11, data=board.D9)
mixer = audiomixer.Mixer(voice_count=4, sample_rate=SAMPLE_RATE, channel_count=1,
                         bits_per_sample=16, samples_signed=True, buffer_size=2048 )
audio.play(mixer)
vol_val = 2
mixer.voice[0].play(synth)
mixer.voice[0].level = 0.3

# these are the triads, all major
c_tones = [130.81, 164.81, 196.00]
g_tones = [196.00, 246.94, 293.66]
d_tones = [146.83, 185.00, 220.00]
a_tones = [220.00, 277.18, 329.63]
e_tones = [164.81, 207.65, 246.94]
b_tones = [246.94, 311.13, 369.99]
fsharp_tones = [185.00, 233.08, 277.18]
csharp_tones = [138.59, 174.61, 207.65]
aflat_tones = [207.65, 261.63, 311.13]
eflat_tones = [155.56, 196.00, 233.08]
bflat_tones = [233.08, 293.66, 349.23]
f_tones = [174.61, 220.00, 261.63]

# names for the alphanumeric displays
chord_names = ["Cmaj", "Gmaj", "Dmaj", "Amaj", "Emaj", "Bmaj",
               "F#ma", "C#ma", "Abma", "Ebma", "Bbma", "Fmaj"]
chords = [c_tones, g_tones, d_tones, a_tones, e_tones, b_tones, fsharp_tones, csharp_tones,
          aflat_tones, eflat_tones, bflat_tones, f_tones]

# i2c setup
i2c = board.I2C()
# the encoders
seesaw0 = seesaw.Seesaw(i2c, addr=0x49)
seesaw1 = seesaw.Seesaw(i2c, addr=0x4A)
seesaw2 = seesaw.Seesaw(i2c, addr=0x4B)
seesaw3 = seesaw.Seesaw(i2c, addr=0x4C)
menu_seesaw = seesaw.Seesaw(i2c, addr=0x4D)
# the alphanumeric displays
display0 = segments.Seg14x4(i2c, address=0x70)
display1 = segments.Seg14x4(i2c, address=0x71)
display2 = segments.Seg14x4(i2c, address=0x72)
display3 = segments.Seg14x4(i2c, address=0x73)
menu_display = segments.Seg14x4(i2c, address=0x74)
# the matrix
matrix0 = Matrix8x8x2(i2c, address=0x75)

seesaws = [seesaw0, seesaw1, seesaw2, seesaw3, menu_seesaw]
buttons0 = []
buttons1 = []
buttons2 = []
buttons3 = []
menu_buttons = []
button0_states = []
button1_states = []
button2_states = []
button3_states = []
menu_states = []
button0_names = ["Select", "Up", "Left", "Down", "Right"]

# setup the buttons on all of the encoders
for i in range(1, 6):
    seesaw0.pin_mode(i, seesaw0.INPUT_PULLUP)
    seesaw1.pin_mode(i, seesaw1.INPUT_PULLUP)
    seesaw2.pin_mode(i, seesaw2.INPUT_PULLUP)
    seesaw3.pin_mode(i, seesaw3.INPUT_PULLUP)
    menu_seesaw.pin_mode(i, menu_seesaw.INPUT_PULLUP)
    buttons0.append(digitalio.DigitalIO(seesaw0, i))
    buttons1.append(digitalio.DigitalIO(seesaw1, i))
    buttons2.append(digitalio.DigitalIO(seesaw2, i))
    buttons3.append(digitalio.DigitalIO(seesaw3, i))
    menu_buttons.append(digitalio.DigitalIO(menu_seesaw, i))
    button0_states.append(False)
    button1_states.append(False)
    button2_states.append(False)
    button3_states.append(False)
    menu_states.append(False)

# make all of the encoders
encoder0 = rotaryio.IncrementalEncoder(seesaw0)
last_position0 = 0
encoder1 = rotaryio.IncrementalEncoder(seesaw1)
last_position1 = 0
encoder2 = rotaryio.IncrementalEncoder(seesaw2)
last_position2 = 0
encoder3 = rotaryio.IncrementalEncoder(seesaw3)
last_position3 = 0
menu_enc = rotaryio.IncrementalEncoder(menu_seesaw)
last_menuPosition = 0

# Python Implementation of Björklund's Algorithm by Brian House
# MIT License 2011
# https://github.com/brianhouse/bjorklund

def bjorklund(steps, pulses):
    steps = int(steps)
    pulses = int(pulses)
    if pulses > steps:
        raise ValueError
    pattern = []
    counts = []
    remainders = []
    divisor = steps - pulses
    remainders.append(pulses)
    level = 0
    while True:
        counts.append(divisor // remainders[level])
        remainders.append(divisor % remainders[level])
        divisor = remainders[level]
        level = level + 1
        if remainders[level] <= 1:
            break
    counts.append(divisor)

    def build(level):
        if level == -1:
            pattern.append(0)
        elif level == -2:
            pattern.append(1)
        else:
            for _ in range(0, counts[level]):
                build(level - 1)
            if remainders[level] != 0:
                build(level - 2)

    build(level)
    p = pattern.index(1)
    pattern = pattern[p:] + pattern[0:p]
    return pattern

# using ticks for time tracking
clock = ticks_ms()

# default BPM
bpm = 120

# beat divison
beat_div = [15, 30, 60, 120, 240]
beat_index = 2
beat_names = ["1/16", "1/8 ", "1/4 ", "1/2 ", "HOLE"]
delay = int((beat_div[beat_index] / bpm) * 1000)

# variables for euclidean
c0 = 0
c1 = 0
c2 = 0
c3 = 0
r0 = 0
r1 = 0
r2 = 0
r3 = 0
last_r0 = 0
last_r1 = 0
last_r2 = 0
last_r3 = 0

euclid0_steps = 8
euclid0_pulses = 4
euclid1_steps = 8
euclid1_pulses = 4
euclid2_steps = 8
euclid2_pulses = 4
euclid3_steps = 8
euclid3_pulses = 4

rhythm0 = bjorklund(euclid0_steps, euclid0_pulses)
rhythm1 = bjorklund(euclid1_steps, euclid1_pulses)
rhythm2 = bjorklund(euclid2_steps, euclid2_pulses)
rhythm3 = bjorklund(euclid3_steps, euclid3_pulses)

# read buttons to update Euclidean rhythms
# pylint: disable=too-many-branches
def read_buttons(button_array, button_states, euc, e_step, e_pulse, the_step):
    for b in range(5):
        if not button_array[b].value and button_states[b] is False:
            button_states[b] = True
            if button0_names[b] == "Select":
                e_step = 8
                e_pulse = 4
                if the_step >= e_step:
                    the_step = 0
            elif button0_names[b] == "Up":
                if e_step > 16:
                    e_step = 16
                else:
                    e_step += 1
            elif button0_names[b] == "Down":
                if e_step < 1:
                    e_step = 1
                else:
                    e_step -= 1
                if the_step >= e_step:
                    the_step = 0
            elif button0_names[b] == "Left":
                e_pulse -= 1
                e_pulse = max(e_pulse, 1)
            else:
                e_pulse += 1
            e_pulse = min(e_pulse, e_step)
            euc = bjorklund(e_step, e_pulse)
        if button_array[b].value and button_states[b] is True:
            button_states[b] = False
            if button0_names[b] in ("Select", "Up", "Down"):
                matrix0.fill(matrix0.LED_OFF)
                draw_steps(euclid0_steps, 0)
                draw_steps(euclid1_steps, 2)
                draw_steps(euclid2_steps, 4)
                draw_steps(euclid3_steps, 6)
    return euc, e_step, e_pulse, the_step

# play euclidean rhythms and update matrix
def play_euclidean(this_synth, n, the_rhythm, rhythm_count, last_count, c, matrix_slot):
    if last_count <= 7:
        matrix0[matrix_slot, last_count] = matrix0.LED_GREEN
    else:
        c -= 1
        matrix0[matrix_slot + 1, (last_count - last_count) + c] = matrix0.LED_GREEN
        c += 1

    if the_rhythm[rhythm_count] == 1:
        this_synth.frequency = n[randint(0, 2)]
        synth.press(this_synth)
        if rhythm_count <= 7:
            matrix0[matrix_slot, rhythm_count] = matrix0.LED_RED
        else:
            matrix0[matrix_slot + 1, (rhythm_count - rhythm_count) + c] = matrix0.LED_RED
            c += 1
    else:
        synth.release(this_synth)
        if rhythm_count > 7:
            c += 1
    last_count = rhythm_count

    rhythm_count += 1
    if rhythm_count >= len(the_rhythm):
        rhythm_count = 0
    if rhythm_count == 1:
        c = 0
    return rhythm_count, last_count, c

# initial matrix draw
def draw_steps(euc_steps, col):
    dif = 0
    for m in range(euc_steps):
        if m <= 7:
            matrix0[col, m] = matrix0.LED_GREEN
        else:
            matrix0[col + 1, (m - m) + dif] = matrix0.LED_GREEN
            dif += 1
draw_steps(euclid0_steps, 0)
draw_steps(euclid1_steps, 2)
draw_steps(euclid2_steps, 4)
draw_steps(euclid3_steps, 6)

# clocks for playing euclidean and reading menu encoder
enc_clock = ticks_ms()
menu_clock = ticks_ms()

# the modes menu
modes = ["PLAY", "EUC ", "BPM ", "BEAT", "ADSR", "WAVE", "RING", "LFO ", "VOL "]
mode_index = 0
mode = modes[mode_index]
menu_display.print(f"   {mode}")

# default chords
chord0_sel = 0
chord1_sel = 1
chord2_sel = 0
chord3_sel = 1

display0.print(chord_names[chord0_sel])
display1.print(chord_names[chord1_sel])
display2.print(chord_names[chord2_sel])
display3.print(chord_names[chord3_sel])

# arrays of individual buttons

select_buttons = [buttons0[0], buttons1[0], buttons2[0], buttons3[0]]
left_buttons = [buttons0[2], buttons1[2], buttons2[2], buttons3[2]]
right_buttons = [buttons0[4], buttons1[4], buttons2[4], buttons3[4]]
select_states = [button0_states[0], button1_states[0], button2_states[0], button3_states[0]]
left_states = [button0_states[2], button1_states[2], button2_states[2], button3_states[2]]
right_states = [button0_states[4], button1_states[4], button2_states[4], button3_states[4]]
select_index = 0
left_index = 0
right_index = 0

# adsr mode
adsr_names = ["A", "D", "S", "R"]

synth_adsr_indexes = [0, 0, 0, 0]

adsr_properties = [0, 1, 4, 2]

adsr0_values = [amp_env0.attack_time, amp_env0.decay_time,
                amp_env0.sustain_level, amp_env0.release_time]
adsr1_values = [amp_env1.attack_time, amp_env1.decay_time,
                amp_env1.sustain_level, amp_env1.release_time]
adsr2_values = [amp_env0.attack_time, amp_env0.decay_time,
                amp_env0.sustain_level, amp_env0.release_time]
adsr3_values = [amp_env1.attack_time, amp_env1.decay_time,
                amp_env1.sustain_level, amp_env1.release_time]

all_adsr_values = [adsr0_values, adsr1_values, adsr2_values, adsr3_values]

adsr0_val = int(simpleio.map_range(amp_env0.attack_time, 0.0, 1.0, 0, 19))

adsr1_val = int(simpleio.map_range(amp_env0.decay_time, 0.0, 1.0, 0, 19))

adsr2_val = int(simpleio.map_range(amp_env0.sustain_level, 0.0, 1.0, 0, 19))

adsr3_val = int(simpleio.map_range(amp_env0.release_time, 0.0, 1.0, 0, 19))

clock_stretch = False

ring0_val = 0
ring1_val = 0
ring2_val = 0
ring3_val = 0

lfo_val = 0

# used to play/pause
play_states = [True, True, True, True]

while True:
    # rotary encoder reading
    if ticks_diff(ticks_ms(), enc_clock) >= 100:
        position0 = encoder0.position
        position1 = encoder1.position
        position2 = encoder2.position
        position3 = encoder3.position
        menuPosition = menu_enc.position
        # menu changes mode
        if menuPosition != last_menuPosition:
            if menuPosition > last_menuPosition:
                mode_index = (mode_index + 1) % len(modes)
            else:
                mode_index = (mode_index - 1) % len(modes)
            if mode in ("EUC ", "ADSR"):
                clock_stretch = True
            if mode in ("PLAY", "BPM ", "BEAT", "WAVE") and clock_stretch:
                clock = ticks_ms()
                clock_stretch = False
            mode = modes[mode_index]
            menu_display.print(f"   {mode}")
            last_menuPosition = menuPosition
        # encoder functionality depends on mode
        # encoder 0 has most functionality
        if position0 != last_position0:
            if position0 > last_position0:
                if mode == "PLAY":
                    chord0_sel = (chord0_sel + 1) % len(chords)
                    display0.print(chord_names[chord0_sel])
                elif mode == "BEAT":
                    beat_index = (beat_index + 1) % 5
                    delay = int((beat_div[beat_index] / bpm) * 1000)
                    display0.print(f"   {beat_names[beat_index]}")
                elif mode == "BPM ":
                    bpm += 1
                    delay = int((beat_div[beat_index] / bpm) * 1000)
                    display0.print(f"   {bpm}")
                elif mode == "ADSR":
                    adsr0_val = (adsr0_val + 1) % 20
                    mapped_val = simpleio.map_range(adsr0_val, 0, 19, 0.0, 1.0)
                    all_adsr_values[0][synth_adsr_indexes[0]] = mapped_val
                    the_env = synthio.Envelope(attack_time=all_adsr_values[0][0],
                                               decay_time = all_adsr_values[0][1],
                                               release_time=all_adsr_values[0][3],
                                               attack_level=1, sustain_level=all_adsr_values[0][2])
                    synth0.envelope = the_env
                elif mode == "WAVE":
                    synth0_wave = (synth0_wave + 1) % len(wave_names)
                    synth0.waveform = waveforms[synth0_wave]
                elif mode == "RING":
                    ring0_val = (ring0_val + 1) % 25
                    mapped_val = simpleio.map_range(ring0_val, 0, 24, 0.0, 220.0)
                    synth0.ring_frequency = mapped_val
                elif mode == "LFO ":
                    lfo_val = (lfo_val + 1) % 10
                    mapped_val = simpleio.map_range(lfo_val, 0, 9, 0.0, 5.0)
                    lfo.rate = mapped_val
                elif mode == "VOL ":
                    vol_val = (vol_val + 1) % 10
                    mapped_val = simpleio.map_range(vol_val, 0, 9, 0.0, 1.0)
                    mixer.voice[0].level = mapped_val
            else:
                if mode == "PLAY":
                    chord0_sel = (chord0_sel - 1) % len(chords)
                    display0.print(chord_names[chord0_sel])
                elif mode == "BEAT":
                    beat_index = (beat_index - 1) % 5
                    delay = int((beat_div[beat_index] / bpm) * 1000)
                    display0.print(f"   {beat_names[beat_index]}")
                elif mode == "BPM ":
                    bpm -= 1
                    display0.print(f"   {bpm}")
                elif mode == "ADSR":
                    adsr0_val = (adsr0_val - 1) % 20
                    mapped_val = simpleio.map_range(adsr0_val, 0, 19, 0.0, 1.0)
                    all_adsr_values[0][synth_adsr_indexes[0]] = mapped_val
                    the_env = synthio.Envelope(attack_time=all_adsr_values[0][0],
                                               decay_time = all_adsr_values[0][1],
                                               release_time=all_adsr_values[0][3],
                                               attack_level=1, sustain_level=all_adsr_values[0][2])
                    synth0.envelope = the_env
                elif mode == "WAVE":
                    synth0_wave = (synth0_wave - 1) % len(wave_names)
                    synth0.waveform = waveforms[synth0_wave]
                elif mode == "RING":
                    ring0_val = (ring0_val - 1) % 25
                    mapped_val = simpleio.map_range(ring0_val, 0, 24, 0.0, 220.0)
                    synth0.ring_frequency = mapped_val
                elif mode == "LFO ":
                    lfo_val = (lfo_val - 1) % 10
                    mapped_val = simpleio.map_range(lfo_val, 0, 9, 0.0, 5.0)
                    lfo.rate = mapped_val
                elif mode == "VOL ":
                    vol_val = (vol_val - 1) % 10
                    mapped_val = simpleio.map_range(vol_val, 0, 9, 0.0, 1.0)
                    mixer.voice[0].level = mapped_val
            last_position0 = position0
        if position1 != last_position1:
            if position1 > last_position1:
                if mode == "PLAY":
                    chord1_sel = (chord1_sel + 1) % len(chords)
                    display1.print(chord_names[chord1_sel])
                elif mode == "ADSR":
                    adsr1_val = (adsr1_val + 1) % 20
                    mapped_val = simpleio.map_range(adsr1_val, 0, 19, 0.0, 1.0)
                    all_adsr_values[1][synth_adsr_indexes[1]] = mapped_val
                    the_env = synthio.Envelope(attack_time=all_adsr_values[1][0],
                                               decay_time = all_adsr_values[1][1],
                                               release_time=all_adsr_values[1][3],
                                               attack_level=1, sustain_level=all_adsr_values[1][2])
                    synth1.envelope = the_env
                elif mode == "WAVE":
                    synth1_wave = (synth1_wave + 1) % len(wave_names)
                    synth1.waveform = waveforms[synth1_wave]
                elif mode == "RING":
                    ring1_val = (ring1_val + 1) % 25
                    mapped_val = simpleio.map_range(ring1_val, 0, 24, 0.0, 220.0)
                    synth1.ring_frequency = mapped_val
            else:
                if mode == "PLAY":
                    chord1_sel = (chord1_sel - 1) % len(chords)
                    display1.print(chord_names[chord1_sel])
                elif mode == "ADSR":
                    adsr1_val = (adsr1_val - 1) % 20
                    mapped_val = simpleio.map_range(adsr1_val, 0, 19, 0.0, 1.0)
                    all_adsr_values[1][synth_adsr_indexes[1]] = mapped_val
                    the_env = synthio.Envelope(attack_time=all_adsr_values[1][0],
                                               decay_time = all_adsr_values[1][1],
                                               release_time=all_adsr_values[1][3],
                                               attack_level=1, sustain_level=all_adsr_values[1][2])
                    synth1.envelope = the_env
                elif mode == "WAVE":
                    synth1_wave = (synth1_wave - 1) % len(wave_names)
                    synth1.waveform = waveforms[synth1_wave]
                elif mode == "RING":
                    ring1_val = (ring1_val - 1) % 25
                    mapped_val = simpleio.map_range(ring1_val, 0, 24, 0.0, 220.0)
                    synth1.ring_frequency = mapped_val
            last_position1 = position1
        if position2 != last_position2:
            if position2 > last_position2:
                if mode == "PLAY":
                    chord2_sel = (chord2_sel + 1) % len(chords)
                elif mode == "ADSR":
                    adsr2_val = (adsr2_val + 1) % 20
                    mapped_val = simpleio.map_range(adsr2_val, 0, 19, 0.0, 1.0)
                    all_adsr_values[2][synth_adsr_indexes[2]] = mapped_val
                    the_env = synthio.Envelope(attack_time=all_adsr_values[2][0],
                                               decay_time = all_adsr_values[2][1],
                                               release_time=all_adsr_values[2][3],
                                               attack_level=1, sustain_level=all_adsr_values[2][2])
                    synth2.envelope = the_env
                elif mode == "WAVE":
                    synth2_wave = (synth2_wave + 1) % len(wave_names)
                    synth2.waveform = waveforms[synth2_wave]
                elif mode == "RING":
                    ring2_val = (ring2_val + 1) % 25
                    mapped_val = simpleio.map_range(ring2_val, 0, 24, 0.0, 220.0)
                    synth2.ring_frequency = mapped_val
            else:
                if mode == "PLAY":
                    chord2_sel = (chord2_sel - 1) % len(chords)
                    display2.print(chord_names[chord2_sel])
                elif mode == "ADSR":
                    adsr2_val = (adsr2_val - 1) % 20
                    mapped_val = simpleio.map_range(adsr2_val, 0, 19, 0.0, 1.0)
                    all_adsr_values[2][synth_adsr_indexes[2]] = mapped_val
                    the_env = synthio.Envelope(attack_time=all_adsr_values[2][0],
                                               decay_time = all_adsr_values[2][1],
                                               release_time=all_adsr_values[2][3],
                                               attack_level=1, sustain_level=all_adsr_values[2][2])
                    synth2.envelope = the_env
                elif mode == "WAVE":
                    synth2_wave = (synth2_wave - 1) % len(wave_names)
                    synth2.waveform = waveforms[synth2_wave]
                elif mode == "RING":
                    ring2_val = (ring2_val - 1) % 25
                    mapped_val = simpleio.map_range(ring2_val, 0, 24, 0.0, 220.0)
                    synth2.ring_frequency = mapped_val
            last_position2 = position2
        if position3 != last_position3:
            if position3 > last_position3:
                if mode == "PLAY":
                    chord3_sel = (chord3_sel + 1) % len(chords)
                    display3.print(chord_names[chord3_sel])
                elif mode == "ADSR":
                    adsr3_val = (adsr3_val + 1) % 20
                    mapped_val = simpleio.map_range(adsr3_val, 0, 19, 0.0, 1.0)
                    all_adsr_values[3][synth_adsr_indexes[3]] = mapped_val
                    the_env = synthio.Envelope(attack_time=all_adsr_values[3][0],
                                               decay_time = all_adsr_values[3][1],
                                               release_time=all_adsr_values[3][3],
                                               attack_level=1, sustain_level=all_adsr_values[3][2])
                    synth3.envelope = the_env
                elif mode == "WAVE":
                    synth3_wave = (synth3_wave + 1) % len(wave_names)
                    synth3.waveform = waveforms[synth3_wave]
                elif mode == "RING":
                    ring3_val = (ring3_val + 1) % 25
                    mapped_val = simpleio.map_range(ring3_val, 0, 24, 0.0, 220.0)
                    synth3.ring_frequency = mapped_val
            else:
                if mode == "PLAY":
                    chord3_sel = (chord3_sel - 1) % len(chords)
                    display3.print(chord_names[chord3_sel])
                elif mode == "ADSR":
                    adsr3_val = (adsr3_val - 1) % 20
                    mapped_val = simpleio.map_range(adsr3_val, 0, 19, 0.0, 1.0)
                    all_adsr_values[3][synth_adsr_indexes[3]] = mapped_val
                    the_env = synthio.Envelope(attack_time=all_adsr_values[3][0],
                                               decay_time = all_adsr_values[3][1],
                                               release_time=all_adsr_values[3][3],
                                               attack_level=1, sustain_level=all_adsr_values[3][2])
                    synth3.envelope = the_env
                elif mode == "WAVE":
                    synth3_wave = (synth3_wave - 1) % len(wave_names)
                    synth3.waveform = waveforms[synth3_wave]
                elif mode == "RING":
                    ring3_val = (ring3_val - 1) % 25
                    mapped_val = simpleio.map_range(ring3_val, 0, 24, 0.0, 220.0)
                    synth3.ring_frequency = mapped_val
            last_position3 = position3
        enc_clock = ticks_add(enc_clock, 100)

    # synth plays based on ticks timing
    if ticks_diff(ticks_ms(), clock) >= delay:
        if play_states[0] is True:
            r0, last_r0, c0 = play_euclidean(synth0, chords[chord0_sel],
                                             rhythm0, r0, last_r0, c0, 0)
        if play_states[1] is True:
            r1, last_r1, c1 = play_euclidean(synth1, chords[chord1_sel],
                                             rhythm1, r1, last_r1, c1, 2)
        if play_states[2] is True:
            r2, last_r2, c2 = play_euclidean(synth2, chords[chord2_sel],
                                             rhythm2, r2, last_r2, c2, 4)
        if play_states[3] is True:
            r3, last_r3, c3 = play_euclidean(synth3, chords[chord3_sel],
                                             rhythm3, r3, last_r3, c3, 6)
        clock = ticks_add(clock, delay)
    # in PLAY select button controls play/pause
    if mode == "PLAY":
        for i in range(4):
            if not select_buttons[i].value and select_states[i] is False:
                select_states[i] = True
                if play_states[i] is True:
                    synth.release(synths[i])
                    play_states[i] = False
                else:
                    play_states[i] = True
            if select_buttons[i].value and select_states[i] is True:
                select_states[i] = False
        display0.print(chord_names[chord0_sel])
        display1.print(chord_names[chord1_sel])
        display2.print(chord_names[chord2_sel])
        display3.print(chord_names[chord3_sel])
    # EUC menu select resets cycle count
    elif mode == "EUC ":
        if not menu_buttons[0].value and menu_states[0] is False:
            r0 = 0
            r1 = 0
            r2 = 0
            r3 = 0
            menu_states[0] = True
        if menu_buttons[0].value and menu_states[0] is True:
            menu_states[0] = False
        rhythm0, euclid0_steps, euclid0_pulses, r0 = read_buttons(buttons0, button0_states,
                                                                  rhythm0, euclid0_steps,
                                                                  euclid0_pulses, r0)
        rhythm1, euclid1_steps, euclid1_pulses, r1 = read_buttons(buttons1, button1_states,
                                                                  rhythm1, euclid1_steps,
                                                                  euclid1_pulses, r1)
        rhythm2, euclid2_steps, euclid2_pulses, r2 = read_buttons(buttons2, button2_states,
                                                                  rhythm2, euclid2_steps,
                                                                  euclid2_pulses, r2)
        rhythm3, euclid3_steps, euclid3_pulses, r3 = read_buttons(buttons3, button3_states,
                                                                  rhythm3, euclid3_steps,
                                                                  euclid3_pulses, r3)
        display0.print(f"   {euclid0_pulses}")
        display1.print(f"   {euclid1_pulses}")
        display2.print(f"   {euclid2_pulses}")
        display3.print(f"   {euclid3_pulses}")
    # BPM is adjusted
    elif mode == "BPM ":
        if not select_buttons[0].value and select_states[0] is False:
            bpm = 120
            select_states[0] = True
        if select_buttons[0].value and select_states[0] is True:
            select_states[0] = False
        display0.print(f"   {bpm}")
        display1.print("    ")
        display2.print("    ")
        display3.print("    ")
    # beat division is changed
    elif mode == "BEAT":
        if not select_buttons[0].value and select_states[0] is False:
            beat_names[beat_index] = 2
            select_states[0] = True
        if select_buttons[0].value and select_states[0] is True:
            select_states[0] = False
        display0.print(f"   {beat_names[beat_index]}")
        display1.print("    ")
        display2.print("    ")
        display3.print("    ")
    # adsr for each voice
    elif mode == "ADSR":
        for i in range(4):
            if not left_buttons[i].value and left_states[i] is False:
                synth_adsr_indexes[i] = (synth_adsr_indexes[i] - 1) % 4
                left_states[i] = True
                the_synth = synths[i]
            if left_buttons[i].value and left_states[i] is True:
                left_states[i] = False
            if not right_buttons[i].value and right_states[i] is False:
                synth_adsr_indexes[i] = (synth_adsr_indexes[i] + 1) % 4
                right_states[i] = True
            if right_buttons[i].value and right_states[i] is True:
                right_states[i] = False
            if not select_buttons[i].value and select_states[i] is False:
                the_synth = synths[i]
                all_adsr_values[i][0] = 0.1
                all_adsr_values[i][1] = 0.1
                all_adsr_values[i][3] = 0.1
                all_adsr_values[i][2] = 0.05
                the_env = synthio.Envelope(attack_time=all_adsr_values[i][0],
                                           decay_time = all_adsr_values[i][1],
                                           release_time=all_adsr_values[i][3],
                                           attack_level=1, sustain_level=all_adsr_values[i][2])
                the_synth.envelope = the_env
                select_states[i] = True
            if select_buttons[i].value and select_states[i] is True:
                select_states[i] = False
        # pylint: disable=line-too-long
        display0.print(f"{adsr_names[synth_adsr_indexes[0]]}{synth0.envelope[adsr_properties[synth_adsr_indexes[0]]]:.2f}")
        display1.print(f"{adsr_names[synth_adsr_indexes[1]]}{synth1.envelope[adsr_properties[synth_adsr_indexes[1]]]:.2f}")
        display2.print(f"{adsr_names[synth_adsr_indexes[2]]}{synth2.envelope[adsr_properties[synth_adsr_indexes[2]]]:.2f}")
        display3.print(f"{adsr_names[synth_adsr_indexes[3]]}{synth3.envelope[adsr_properties[synth_adsr_indexes[3]]]:.2f}")
    # change waveform
    elif mode == "WAVE":
        display0.print(f"    {wave_names[synth0_wave]}")
        display1.print(f"    {wave_names[synth1_wave]}")
        display2.print(f"    {wave_names[synth2_wave]}")
        display3.print(f"    {wave_names[synth3_wave]}")
    # adjust ring modulation
    elif mode == "RING":
        display0.print(f"    {synth0.ring_frequency:.1f}")
        display1.print(f"    {synth1.ring_frequency:.1f}")
        display2.print(f"    {synth2.ring_frequency:.1f}")
        display3.print(f"    {synth3.ring_frequency:.1f}")
    # adjust lfo rate used for ring modulation
    elif mode == "LFO ":
        display0.print("RATE")
        display1.print(f"    {lfo.rate:.1f}")
        display2.print("    ")
        display3.print("    ")
    # overall volume 0.0 - 1.0
    elif mode == "VOL ":
        display0.print(f"    {mixer.voice[0].level:.1f}")
        display1.print("    ")
        display2.print("    ")
        display3.print("    ")
