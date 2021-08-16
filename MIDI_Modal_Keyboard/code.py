# SPDX-FileCopyrightText: 2021 John Park for Adafruit Industries
# SPDX-License-Identifier: MIT

# Pico RP2040 Mechanical MIDI Modal Keyboard
# 7x3 mech keyboard
# Each key sends MIDI NoteOn / NoteOff message over USB
# Can be any scale/mode
# Key combo sends MIDI panic (see bottom section of code)

import time
import board
from digitalio import DigitalInOut, Direction, Pull
import usb_midi
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
from adafruit_debouncer import Debouncer

print("---Pico MIDI Modal Mech Keyboard---")

MIDI_CHANNEL = 1  # pick your MIDI channel here

midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=MIDI_CHANNEL-1)

def send_midi_panic():
    print("All MIDI notes off")
    for x in range(128):
        midi.send(NoteOff(x, 0))

led = DigitalInOut(board.LED)
led.direction = Direction.OUTPUT
led.value = True

num_keys = 21

# list of pins to use (skipping GP15 on Pico because it's funky)
pins = (
    board.GP0,
    board.GP1,
    board.GP2,
    board.GP3,
    board.GP4,
    board.GP5,
    board.GP6,
    board.GP7,
    board.GP8,
    board.GP9,
    board.GP10,
    board.GP11,
    board.GP12,
    board.GP13,
    board.GP14,
    board.GP16,
    board.GP17,
    board.GP18,
    board.GP19,
    board.GP20,
    board.GP21,
)


keys = []
for pin in pins:
    tmp_pin = DigitalInOut(pin)
    tmp_pin.pull = Pull.UP
    keys.append(Debouncer(tmp_pin))

root_notes = (48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59)  # used during config
note_numbers = (48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
                60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71,
                72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83)
note_names = ("C2", "C#2", "D2", "D#2", "E2", "F2", "F#2", "G2", "G#2", "A2", "A#2", "B2",
              "C3", "C#3", "D3", "D#3", "E3", "F3", "F#3", "G3", "G#3", "A3", "A#3", "B3",
              "C4", "C#4", "D4", "D#4", "E4", "F4", "F#4", "G4", "G#4", "A4", "A#4", "B4",)
scale_root = root_notes[0]  # default if nothing is picked
root_picked = False  # state of root selection
mode_picked = False  # state of mode selection
mode_choice = 0


#  ----- User selection of the root note ----- #
print("Pick the root using top twelve keys, then press bottom right key to enter:")
print(". . . . . . .")
print(". . . . . o o")
print("o o o o o o .")

while not root_picked:
    for i in range(12):
        keys[i].update()
        if keys[i].fell:
            scale_root = root_notes[i]
            midi.send(NoteOn(root_notes[i], 120))
            print("Root is", note_names[i])
        if keys[i].rose:
            midi.send(NoteOff(root_notes[i], 0))
    keys[20].update()

    if keys[20].rose:
        root_picked = True
        print("Root picked.\n")

#  lists of mode intervals relative to root
major = ( 0, 2, 4, 5, 7, 9, 11 )
minor = ( 0, 2, 3, 5, 7, 8, 10 )
dorian = ( 0, 2, 3, 5, 7, 9, 10 )
phrygian = ( 0, 1, 3, 5, 7, 8, 10 )
lydian = (0 , 2, 4, 6, 7, 9, 11 )
mixolydian = ( 0, 2, 4, 5, 7, 9, 10)
locrian = ( 0, 1, 3, 5, 6, 8, 10)

modes = []
modes.append(major)
modes.append(minor)
modes.append(dorian)
modes.append(phrygian)
modes.append(lydian)
modes.append(mixolydian)
modes.append(locrian)

mode_names = ("Major/Ionian",
              "Minor/Aeolian",
              "Dorian",
              "Phrygian",
              "Lydian",
              "Mixolydian",
              "Locrian")

intervals = list(mixolydian)  # intervals for Mixolydian by default

print("Pick the mode with top seven keys, then press bottom right key to enter:")
print(". . . . . . .")
print("o o o o o o o")
print("o o o o o o .")

while not mode_picked:
    for i in range(7):
        keys[i].update()
        if keys[i].fell:
            mode_choice = i
            print(mode_names[mode_choice], "mode")
            for j in range(7):
                intervals[j] = modes[i][j]
            # play the scale
            for k in range(7):
                midi.send(NoteOn(scale_root+intervals[k], 120))
                note_index = note_numbers.index(scale_root+intervals[k])
                print(note_names[note_index])
                time.sleep(0.15)
                midi.send(NoteOff(scale_root+intervals[k], 0))
                time.sleep(0.15)
            midi.send(NoteOn(scale_root+12, 120))
            note_index = note_numbers.index(scale_root+12)
            print(note_names[note_index], "\n")
            time.sleep(0.15)
            midi.send(NoteOff(scale_root+12, 0))
            time.sleep(0.15)

    keys[20].update()
    if keys[20].rose:
        print(mode_names[mode_choice], "mode picked.\n")
        mode_picked = True

scale = []  # create the base scale
for i in range(7):
    scale.append(scale_root + intervals[i])

midi_notes = []  # build the list with three octaves
for k in range(7):
    midi_notes.append(scale[k]+24)
for l in range(7):
    midi_notes.append(scale[l]+12)
for m in range(7):
    midi_notes.append(scale[m])

led.value = False
print("Ready, set, play!")


while True:

    for i in range(num_keys):
        keys[i].update()
        if keys[i].fell:
            try:
                midi.send(NoteOn(midi_notes[i], 120))
                note_index = note_numbers.index(midi_notes[i])
                print("MIDI NoteOn:", note_names[note_index])
            except ValueError:  # deals w six key limit
                pass

        if keys[i].rose:
            try:
                midi.send(NoteOff(midi_notes[i], 0))
                note_index = note_numbers.index(midi_notes[i])
                print("MIDI NoteOff:", note_names[note_index])
            except ValueError:
                pass

    #  Key combo for MIDI panic
    # . o o o o o .
    # o o o . o o o
    # . o o o o o .

    if (not keys[0].value and
            not keys[6].value
            and not keys[10].value
            and not keys[14].value
            and not keys[20].value):
        send_midi_panic()
        time.sleep(1)
