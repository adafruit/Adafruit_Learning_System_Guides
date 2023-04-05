# SPDX-FileCopyrightText: 2023 John Park for Adafruit
#
# SPDX-License-Identifier: MIT
# Hexboard seven key modal note/chord pad for MIDI instruments
# Runs on QT Py RP2040
# (other QT Pys should work, but the BOOT button is handy for initiating configuration)

import time
import board
from digitalio import DigitalInOut, Pull
import keypad
import neopixel
import rainbowio
import usb_midi
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff

button = DigitalInOut(board.BUTTON)
button.pull = Pull.UP

num_switches = 7
leds = neopixel.NeoPixel(board.A0, num_switches, brightness=0.7)
leds.fill(rainbowio.colorwheel(5))
leds.show()

# root_picked = False
note = 0
root = 0  # defaults to a C

#  lists of modal intervals (relative to root). Customize these if you want other scales/keys
major = (0, 2, 4, 5, 7, 9, 11)
minor = (0, 2, 3, 5, 7, 8, 10)
dorian = (0, 2, 3, 5, 7, 9, 10)
phrygian = (0, 1, 3, 5, 7, 8, 10)
lydian = (0, 2, 4, 6, 7, 9, 11)
mixolydian = (0, 2, 4, 5, 7, 9, 10)
locrian = (0, 1, 3, 5, 6, 8, 10)

modes = []
modes.append(major)
modes.append(minor)
modes.append(dorian)
modes.append(phrygian)
modes.append(lydian)
modes.append(mixolydian)
modes.append(locrian)

octv = 4
mode = 0  # default to major scale
play_chords = True  # default to play chords
pre_notes = modes[mode]  # initial mapping
keymap = (4, 3, 5, 0, 2, 6, 1)  # physical to logical key mapping

#  Key chart  | logical  |Interval chart example
#    6   1    |  6   7   |   9  11
#   5  0  2   | 3  4  5  |  4   5   7
#    4   3    |  0   1   |    0   2

# MIDI Setup
midi_usb_channel = 1  # change this to your desired MIDI out channel, 1-16
midi_usb = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=midi_usb_channel-1)

# Keyswitch setup
keyswitch_pins = (board.A3, board.A2, board.SDA, board.SCL, board.TX, board.RX, board.A1)
keyswitches = keypad.Keys(keyswitch_pins, value_when_pressed=False, pull=True)

def pick_mode():
    print("Choose mode...")
    mode_picked = False
    # pylint: disable=global-statement
    global mode
    while not mode_picked:
        # pylint: disable=redefined-outer-name
        keyswitch = keyswitches.events.get()  # check for key events
        if keyswitch:
            if keyswitch.pressed:
                mode = keymap.index(keyswitch.key_number)  # bottom left key is 0/major
                print("Mode is:", mode)
            if keyswitch.released:
                mode_picked = True
                leds.fill(rainbowio.colorwheel(8))
                leds.show()
                pick_octave()

def pick_octave():
    print("Choose octave...")
    octave_picked = False
    # pylint: disable=global-statement
    global octv
    while not octave_picked:
        if button.value is False:  # pressed
            launch_config()
            time.sleep(0.1)
        # pylint: disable=redefined-outer-name
        keyswitch = keyswitches.events.get()  # check for key events
        if keyswitch:
            if keyswitch.pressed:
                octv = keymap.index(keyswitch.key_number)  # get remapped position, lower left is 0
                print("Octave is:", octv)
            if keyswitch.released:
                octave_picked = True
                leds.fill(rainbowio.colorwheel(16))
                pick_root()

def pick_root():# user selects key in which to play
    print("Choose root note...")
    root_picked = False
    # pylint: disable=global-statement
    global root
    while not root_picked:
        if button.value is False:  # pressed
            launch_config()
            time.sleep(0.1)
        # pylint: disable=redefined-outer-name
        keyswitch = keyswitches.events.get()  # check for key events
        if keyswitch:
            if keyswitch.pressed:
                root = keymap.index(keyswitch.key_number)  # get remapped position, lower left is 0
                print("ksw:", keyswitch.key_number, "keymap index:", root)
                note = pre_notes[root]
                print("note:", note)
                midi_usb.send(NoteOn(note + (12*octv), 120))
                root_notes.clear()
                # pylint: disable=redefined-outer-name
                for mode_interval in range(num_switches):
                    root_notes.append(modes[mode][mode_interval] + note)
                print("root note intervals:", root_notes)
            if keyswitch.released:
                note = pre_notes[root]
                midi_usb.send(NoteOff(note + (12*octv), 0))
                root_picked = True
                leds.fill(0x0)
                leds[3] = rainbowio.colorwheel(12)
                leds[4] = rainbowio.colorwheel(5)
                leds.show()
                pick_chords()

def pick_chords():
    print("Choose chords vs. single notes...")
    chords_picked = False
    # pylint: disable=global-statement
    global play_chords
    while not chords_picked:
        if button.value is False:  # pressed
            launch_config()
            time.sleep(0.1)
        # pylint: disable=redefined-outer-name
        keyswitch = keyswitches.events.get()  # check for key events
        if keyswitch:
            if keyswitch.pressed:
                if keyswitch.key_number == 4:
                    play_chords = True
                    print("Chords are on")
                    chords_picked = True
                    playback_led_colors()
                if keyswitch.key_number == 3:
                    play_chords = False
                    print("Chords are off")
                    chords_picked = True
                    playback_led_colors()

# create the interval list based on root key and mode that's been picked in variable
root_notes = []
for mode_interval in range(num_switches):
    root_notes.append(modes[mode][mode_interval] + note)
print("---Hexpad---")
print("\nRoot note intervals:", root_notes)

key_colors = (18, 10, 18, 26, 26, 18, 10)

def playback_led_colors():
    for i in range(num_switches):
        leds[i]=(rainbowio.colorwheel(key_colors[i]))
        leds.show()
        time.sleep(0.1)

playback_led_colors()

# MIDI Note Message Functions
def send_note_on(note_num):
    if play_chords is True:
        note_num = root_notes[note_num] + (12*octv)
        midi_usb.send(NoteOn(note_num, 120))
        midi_usb.send(NoteOn(note_num + modes[mode][2], 80))
        midi_usb.send(NoteOn(note_num + modes[mode][4], 60))
        midi_usb.send(NoteOn(note_num+12, 80))
    else:
        note_num = root_notes[note_num] + (12*octv)
        midi_usb.send(NoteOn(note_num, 120))


def send_note_off(note_num):
    if play_chords is True:
        note_num = root_notes[note_num] + (12*octv)
        midi_usb.send(NoteOff(note_num, 0))
        midi_usb.send(NoteOff(note_num + modes[mode][2], 0))
        midi_usb.send(NoteOff(note_num + modes[mode][4], 0))
        midi_usb.send(NoteOff(note_num+12, 0))
    else:
        note_num = root_notes[note_num] + (12*octv)
        midi_usb.send(NoteOff(note, 0))

def send_midi_panic():
    for x in range(128):
        midi_usb.send(NoteOff(x, 0))

def launch_config():
    print("-launching config-")
    send_midi_panic()
    leds.fill(rainbowio.colorwheel(5))
    leds.show()
    pick_mode()

send_midi_panic()  # turn off any stuck notes at startup


while True:
    keyswitch = keyswitches.events.get()  # check for key events
    if keyswitch:
        keyswitch_number=keyswitch.key_number
        if keyswitch.pressed:
            note_picked = keymap.index(keyswitch.key_number)
            send_note_on(note_picked)
            leds[keyswitch_number]=(rainbowio.colorwheel(10))

            leds.show()
        if keyswitch.released:
            note_picked = keymap.index(keyswitch.key_number)
            send_note_off(note_picked)
            leds[keyswitch_number]=(rainbowio.colorwheel(key_colors[keyswitch_number]))
            leds.show()

    if button.value is False:  # pressed
        launch_config()
        time.sleep(0.1)
