# SPDX-FileCopyrightText: 2021 john park for Adafruit Industries
# SPDX-License-Identifier: MIT
# NeoController: NeoSlider(x4) + NeoKey MIDI input device

import board
import busio
from adafruit_simplemath import map_range
import usb_midi
import adafruit_midi
from adafruit_midi.control_change import ControlChange
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw import neopixel
from adafruit_seesaw.analoginput import AnalogInput
from adafruit_neokey.neokey1x4 import NeoKey1x4

i2c = busio.I2C(board.SCL, board.SDA)  # for QT Py RP2040, use SCL1/SDA1

# --- NeoSlider object setup
addresses = (0x30, 0x31, 0x32, 0x33)  # cut jumpers to proper addreses (none, A0, A1, A0+A1)
neosliders = []  # list to hold neoslider objects
for address in addresses:  # create each neoslider w proper address
    temp_neosliders = Seesaw(i2c, address)
    neosliders.append(temp_neosliders)  # append to the list

# --- NeoSlider analog read setup
analogin_pin = 18  # slider is on this analog pin
analog_pins = (0, 1)
analog_inputs = []
for n in range(len(neosliders)):
    temp_analog_in = AnalogInput(neosliders[n], analogin_pin)
    analog_inputs.append(temp_analog_in)

# --- Slider NeoPixels Setup
PIX_PIN = 14
PIX_NUM = 4
pixels = []
for p in range(len(neosliders)):
    temp_pix = neopixel.NeoPixel(neosliders[p], PIX_PIN, PIX_NUM)
    pixels.append(temp_pix)
    pixels[p].brightness = 1.0
    pixels[p].fill((20, 20, 0))
    pixels[p].show()

# --- NeoKey 1x4 Setup --- #
neokey = NeoKey1x4(i2c, addr=0x38)
amber = 0x300800
blue = 0x002040
red = 0x900000
neokey.pixels.fill(amber)

keys = [  # neokey (adjust if multiple sets), key number, keypress color, MIDI note
    (neokey, 0, blue, 40),
    (neokey, 1, red, 42),
    (neokey, 2, blue, 43),
    (neokey, 3, red, 46),
]

#  states for key presses
key_states = [False, False, False, False]


# --- MIDI setup
midi = adafruit_midi.MIDI(
                        midi_in=usb_midi.ports[0],
                        in_channel=(0),
                        midi_out=usb_midi.ports[1],
                        out_channel=0
)
cc_numbers = [48, 49, 50, 51]  # pick the CC number for each slider to send over

last_sliders = [0] * len(neosliders)  # list to hold state variables

while True:
    # check NeoKeys
    for k in range(len(keys)):
        neokey, key_number, color, midi_note = keys[k]
        if neokey[key_number] and not key_states[key_number]:
            midi.send(NoteOn(midi_note, 127))
            key_states[key_number] = True
            neokey.pixels[key_number] = color
        if not neokey[key_number] and key_states[key_number]:
            midi.send(NoteOff(midi_note, 0))
            neokey.pixels[key_number] = amber
            key_states[key_number] = False

    # check sliders
    for i in range(len(neosliders)):
        slider = analog_inputs[i].value
        if abs(slider - last_sliders[i]) > 1:
            cc_val = int(map_range(slider, 0, 1023, 0, 127))
            midi.send(ControlChange(cc_numbers[i], cc_val))
            color_val = int(map_range(slider, 0, 1023, 5, 255))
            pixels[i].fill((color_val, color_val, 0))
            last_sliders[i] = slider
