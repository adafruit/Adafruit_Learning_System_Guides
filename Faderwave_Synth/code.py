# SPDX-FileCopyrightText: Copyright (c) 2023 john park for Adafruit Industries
#
# SPDX-License-Identifier: MIT
''' Faderwave Synthesizer
    use 16 faders to create the single cycle waveform
    rotary encoder adjusts other synth parameters
    audio output: line level over 3.5mm TRS
    optional CV output via DAC '''

import board
import busio
import ulab.numpy as np
import rotaryio
from digitalio import DigitalInOut, Pull
import displayio
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect
import terminalio
import synthio
import audiomixer
from adafruit_debouncer import Debouncer
import adafruit_ads7830.ads7830 as ADC
from adafruit_ads7830.analog_in import AnalogIn
import adafruit_displayio_ssd1306
import adafruit_ad569x
import usb_midi
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff

displayio.release_displays()

DEBUG = False  # turn on print debugging messages
ITSY_TYPE = 0  # Pick your ItsyBitsy: 0=M4, 1=RP2040

# neopixel setup for RP2040 only
if ITSY_TYPE == 1:
    import neopixel
    pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.3)
    pixel.fill(0x004444)

i2c = busio.I2C(board.SCL, board.SDA, frequency=1_000_000)

midi = adafruit_midi.MIDI(midi_in=usb_midi.ports[0], in_channel=0)

NUM_FADERS = 16
num_oscs = 1       # how many oscillators for each note to start
detune = 0.000  # how much to detune the oscillators
volume = 0.6  # mixer volume
lpf_freq = 12000  # user Low Pass Filter frequency setting
lpf_basef = 500     # filter lowest frequency
lpf_resonance = 0.1  # filter q

faders_pos = [0] * NUM_FADERS
last_faders_pos = [0] * NUM_FADERS

# Initialize ADS7830
adc_a = ADC.ADS7830(i2c, address=0x48)  # default address 0x48
adc_b = ADC.ADS7830(i2c, address=0x49)  # A0 jumper 0x49, A1 0x4A

faders = []  # list for fader objects on first ADC
for fdr in range(8):  # add first group to list
    faders.append(AnalogIn(adc_a, fdr))
for fdr in range(8):  # add second group
    faders.append(AnalogIn(adc_b, fdr))

# Initialize AD5693R for CV out
dac = adafruit_ad569x.Adafruit_AD569x(i2c)
dac.gain = True
dac.value = faders[0].value  # set dac out to the slider level

# Rotary encoder setup
ENC_A = board.D9
ENC_B = board.D10
ENC_SW = board.D7

button_in = DigitalInOut(ENC_SW)  # defaults to input
button_in.pull = Pull.UP  # turn on internal pull-up resistor
button = Debouncer(button_in)

encoder = rotaryio.IncrementalEncoder(ENC_A, ENC_B)
encoder_pos = encoder.position
last_encoder_pos = encoder.position

# display setup
OLED_RST = board.D13
OLED_DC = board.D12
OLED_CS = board.D11

spi = board.SPI()
display_bus = displayio.FourWire(spi, command=OLED_DC, chip_select=OLED_CS,
                                 reset=OLED_RST, baudrate=30_000_000)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=64)

# Create display group
group = displayio.Group()

# Set the font for the text label
font = terminalio.FONT

# Create text label
title = label.Label(font, x=2, y=4, text=("FADERWAVE SYNTHESIZER"), color=0xffffff)
group.append(title)

column_x = (8, 60, 100)
row_y = (22, 34, 46, 58)

midi_lbl_rect = Rect(column_x[2]-3, row_y[0]-5, 28, 10, fill=0xffffff)
group.append(midi_lbl_rect)
midi_lbl = label.Label(font, x=column_x[2], y=row_y[0], text="MIDI", color=0x000000)
group.append(midi_lbl)
midi_rect = Rect(column_x[2]-3, row_y[1]-5, 28, 10, fill=0xffffff)
group.append(midi_rect)
midi_counter_lbl = label.Label(font, x=column_x[2]+8, y=row_y[1], text='-', color=0x000000)
group.append(midi_counter_lbl)

# Create menu selector
menu_sel = 0
menu_sel_txt = label.Label(font, text=(">"), color=0xffffff)
menu_sel_txt.x = column_x[0]-10
menu_sel_txt.y = row_y[menu_sel]
group.append(menu_sel_txt)

# Create detune text
det_txt_a = label.Label(font, text=("Detune "), color=0xffffff)
det_txt_a.x = column_x[0]
det_txt_a.y = row_y[0]
group.append(det_txt_a)

det_txt_b = label.Label(font, text=(str(detune)), color=0xffffff)
det_txt_b.x = column_x[1]
det_txt_b.y = row_y[0]
group.append(det_txt_b)

# Create number of oscs text
num_oscs_txt_a = label.Label(font, text=("Num Oscs "), color=0xffffff)
num_oscs_txt_a.x = column_x[0]
num_oscs_txt_a.y = row_y[1]
group.append(num_oscs_txt_a)

num_oscs_txt_b = label.Label(font, text=(str(num_oscs)), color=0xffffff)
num_oscs_txt_b.x = column_x[1]
num_oscs_txt_b.y = row_y[1]
group.append(num_oscs_txt_b)

# Create volume text
vol_txt_a = label.Label(font, text=("Volume "), color=0xffffff)
vol_txt_a.x = column_x[0]
vol_txt_a.y = row_y[2]
group.append(vol_txt_a)

vol_txt_b = label.Label(font, text=(str(volume)), color=0xffffff)
vol_txt_b.x = column_x[1]
vol_txt_b.y = row_y[2]
group.append(vol_txt_b)

# Create lpf frequency text
lpf_txt_a = label.Label(font, text=("LPF "), color=0xffffff)
lpf_txt_a.x = column_x[0]
lpf_txt_a.y = row_y[3]
group.append(lpf_txt_a)

lpf_txt_b = label.Label(font, text=(str(lpf_freq)), color=0xffffff)
lpf_txt_b.x = column_x[1]
lpf_txt_b.y = row_y[3]
group.append(lpf_txt_b)

# Show the display group
display.root_group = group

# Synthio setup
if ITSY_TYPE == 0:
    import audioio
    audio = audioio.AudioOut(left_channel=board.A0, right_channel=board.A1)  # M4 built-in DAC
if ITSY_TYPE == 1:
    import audiopwmio
    audio = audiopwmio.PWMAudioOut(board.A1)
# if using I2S amp:
# audio = audiobusio.I2SOut(bit_clock=board.MOSI, word_select=board.MISO, data=board.SCK)

mixer = audiomixer.Mixer(channel_count=2, sample_rate=44100, buffer_size=4096)
synth = synthio.Synthesizer(channel_count=2, sample_rate=44100)
audio.play(mixer)
mixer.voice[0].play(synth)
mixer.voice[0].level = 0.75

wave_user = np.array([0]*NUM_FADERS, dtype=np.int16)
amp_env = synthio.Envelope(attack_time=0.3, attack_level=1, sustain_level=0.65, release_time=0.3)

def faders_to_wave():
    for j in range(NUM_FADERS):
        wave_user[j] = int(map_range(faders_pos[j], 0, 127, -32768, 32767))

notes_pressed = {}  # which notes being pressed. key=midi note, val=note object

def note_on(n):
    voices = []   # holds our currently sounding voices ('Notes' in synthio speak)
    fo = synthio.midi_to_hz(n)
    lpf = synth.low_pass_filter(lpf_freq, lpf_resonance)

    for k in range(num_oscs):
        f = fo * (1 + k*detune)
        voices.append(synthio.Note(frequency=f, filter=lpf, envelope=amp_env, waveform=wave_user))
    synth.press(voices)
    note_off(n)  # help to prevent double note_on for same note which can get stuck
    notes_pressed[n] = voices

def note_off(n):
    note = notes_pressed.get(n, None)
    if note:
        synth.release(note)

# simple range mapper, like Arduino map()
def map_range(s, a1, a2, b1, b2):
    return b1 + ((s - a1) * (b2 - b1) / (a2 - a1))

notes_on = 0

print("Welcome to Faderwave")


while True:
    #  get midi messages
    msg = midi.receive()
    if isinstance(msg, NoteOn) and msg.velocity != 0:
        note_on(msg.note)
        notes_on = notes_on + 1
        if DEBUG:
            print("MIDI notes on:     ", msg.note, "      Polyphony:", " "*notes_on, notes_on)
        midi_counter_lbl.text = str(msg.note)
    elif isinstance(msg, NoteOff) or (isinstance(msg, NoteOn) and msg.velocity == 0):
        note_off(msg.note)
        notes_on = notes_on - 1
        if DEBUG:
            print("MIDI notes off:", msg.note, "          Polyphony:", " "*notes_on, notes_on)
        midi_counter_lbl.text = "-"

    # check faders
    for i in range(len(faders)):
        faders_pos[i] = faders[i].value//512
        if faders_pos[i] is not last_faders_pos[i]:
            faders_to_wave()
            last_faders_pos[i] = faders_pos[i]
            if DEBUG:
                print("fader", [i], faders_pos[i])

            # send out a DAC value based on fader 0
            # if i == 1:
            #     dac.value = faders[1].value

    # check encoder button
    button.update()
    if button.fell:
        menu_sel = (menu_sel+1) % 4
        menu_sel_txt.y = row_y[menu_sel]

    # check encoder
    encoder_pos = encoder.position
    if encoder_pos > last_encoder_pos:
        delta = encoder_pos - last_encoder_pos
        if menu_sel == 0:
            detune = detune + (delta * 0.001)
            detune = min(max(detune, -0.030), 0.030)
            formatted_detune = str("{:.3f}".format(detune))
            det_txt_b.text = formatted_detune

        elif menu_sel == 1:
            num_oscs = num_oscs + delta
            num_oscs = min(max(num_oscs, 1), 5)
            formatted_num_oscs = str(num_oscs)
            num_oscs_txt_b.text = formatted_num_oscs

        elif menu_sel == 2:
            volume = volume + (delta * 0.01)
            volume = min(max(volume, 0.00), 1.00)
            mixer.voice[0].level = volume
            formatted_volume = str("{:.2f}".format(volume))
            vol_txt_b.text = formatted_volume

        elif menu_sel == 3:
            lpf_freq = lpf_freq + (delta * 1000)
            lpf_freq = min(max(lpf_freq, 1000), 20_000)
            formatted_lpf = str(lpf_freq)
            lpf_txt_b.text = formatted_lpf

        last_encoder_pos = encoder.position

    if encoder_pos < last_encoder_pos:
        delta = last_encoder_pos - encoder_pos
        if menu_sel == 0:
            detune = detune - (delta * 0.001)
            detune = min(max(detune, -0.030), 0.030)
            formatted_detune = str("{:.3f}".format(detune))
            det_txt_b.text = formatted_detune

        elif menu_sel == 1:
            num_oscs = num_oscs - delta
            num_oscs = min(max(num_oscs, 1), 8)
            formatted_num_oscs = str(num_oscs)
            num_oscs_txt_b.text = formatted_num_oscs

        elif menu_sel == 2:
            volume = volume - (delta * 0.01)
            volume = min(max(volume, 0.00), 1.00)
            mixer.voice[0].level = volume
            formatted_volume = str("{:.2f}".format(volume))
            vol_txt_b.text = formatted_volume

        elif menu_sel == 3:
            lpf_freq = lpf_freq - (delta * 1000)
            lpf_freq = min(max(lpf_freq, 1000), 20_000)
            formatted_lpf = str(lpf_freq)
            lpf_txt_b.text = formatted_lpf

        last_encoder_pos = encoder.position
