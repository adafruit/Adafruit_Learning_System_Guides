# SPDX-FileCopyrightText: 2023 John Park for Adafruit
#
# SPDX-License-Identifier: MIT
# Cyber Cat MIDI Keyboard conversion for Meowsic Cat Piano

#  Functions:
#    --28 keys
#    --left five toe buttons: patches
#    --right five toe buttons: picking CC number for ice cream cone control
#    --volume arrows: octave up/down
#    --tempo arrows: pitchbend up/down
#    --on switch: reset
#    --nose button: midi panic
#    --record button: ice cream cone CC enable/disable (led indicator)
#    --play button: start stop arp or sequence in soft synth via cc 16 0/127
#    --treble clef button: hold notes (use nose to turn off all notes)
#    --face button: momentary CC 0/127 on CC number 17

import keypad
import board
import busio
import supervisor
import digitalio
from adafruit_simplemath import map_range
from adafruit_msa3xx import MSA311
import usb_midi
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
from adafruit_midi.control_change import ControlChange
from adafruit_midi.program_change import ProgramChange
from adafruit_midi.pitch_bend import PitchBend

supervisor.runtime.autoreload = True  # set False to prevent unwanted restarts due to OS weirdness

ledpin = digitalio.DigitalInOut(board.A3)
ledpin.direction = digitalio.Direction.OUTPUT
ledpin.value = True

i2c = board.STEMMA_I2C()
msa = MSA311(i2c)

key_matrix = keypad.KeyMatrix(
    column_pins=(board.D2, board.D3, board.D4, board.D5, board.D6, board.D7, board.D8, board.D9),
    row_pins=(board.D10, board.MOSI, board.MISO, board.CLK, board.A0, board.A1)
)

midi_uart = busio.UART(board.TX, None, baudrate=31250)

midi_usb_channel = 1
midi_usb = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=midi_usb_channel-1)
midi_serial_channel = 1
midi_serial = adafruit_midi.MIDI(midi_out=midi_uart, out_channel=midi_serial_channel-1)

octave = 4
note_offset = 9  # first note on keyboard is an A, first key in keypad matrix is 0

def send_note_on(note, octv):
    note = ((note+note_offset)+(12*octv))
    midi_usb.send(NoteOn(note, 120))
    midi_serial.send(NoteOn(note, 120))

def send_note_off(note, octv):
    note = ((note+note_offset)+(12*octv))
    midi_usb.send(NoteOff(note, 0))
    midi_serial.send(NoteOff(note, 0))

def send_cc(number, val):
    midi_usb.send(ControlChange(number, val))
    midi_serial.send(ControlChange(number, val))

def send_pc(bank, folder, patch):
    send_cc(0, bank)
    send_cc(32, folder)
    midi_usb.send(ProgramChange(patch))
    midi_serial.send(ProgramChange(patch))

def send_bend(bend_start, bend_val, rate, dir):
    b = bend_start
    if dir is 0:
        while b > bend_val + rate:
            print(b)
            b = b - rate
            midi_usb.send(PitchBend(b))
            midi_serial.send(PitchBend(b))
    if dir is 1:
        while b < bend_val - rate:
            print(b)
            b = b + rate
            midi_usb.send(PitchBend(b))
            midi_serial.send(PitchBend(b))

def send_midi_panic():
    for x in range(128):
        midi_usb.send(NoteOff(x, 0))
        midi_serial.send(NoteOff(x, 0))

# key ranges
piano_keys = range(0, 28)  # 'range()' excludes last value, so add one
patch_toes = list(range(28, 33))
cc_toes = list(range(35, 40))
clef_button = 33
nose_button = 47
face_button = 34
record_button = 44
play_button = 45
vol_down_button = 43
vol_up_button = 42
tempo_down_button = 41
tempo_up_button = 40

# patch assigments
patch_list = (
                (0, 0, 0),  # bank 0, folder 0, patch 0
                (1, 0, 0),
                (1, 0, 1),
                (2, 0, 0),
                (3, 0, 0),
)

pb_max = 16383  # bend up value
pb_default = 8192  # bend center value
pb_min = 0  # bend down value
pb_change_rate = 100  # interval for pitch bend, lower number is slower
pb_return_rate = 100  # interval for pitch bend release

# accelerometer filtering variables
slop = 0.2  # threshold for accelerometer send
filter_percent = 0.5  # ranges from 0.0 to 1.0
accel_data_y = msa.acceleration[1]
last_accel_data_y = msa.acceleration[1]

# midi cc variables
cc_enable = True
cc_numbers = (1, 43, 44, 14, 15)  # mod wheel, filter cutoff, resonance, user, user
cc_current = 0
cc_play = 16
cc_face_number = 17

started = False  # state of arp/seq play
note_hold = False

print("Cyber Cat MIDI Keyboard")


while True:
    if cc_enable:
        new_data_y = msa.acceleration[1]
        accel_data_y = ((new_data_y * filter_percent) + (1-filter_percent) * accel_data_y)  # smooth
        if abs(accel_data_y - last_accel_data_y) > slop:
            modulation = int(map_range(accel_data_y, 9, -9, 0, 127))
            send_cc(cc_numbers[cc_current], modulation)
            last_accel_data_y = accel_data_y

    event = key_matrix.events.get()
    if event:
        if event.pressed:
            key = event.key_number

            # Note keys
            if key in piano_keys:
                send_note_on(key, octave)

            # Volume buttons
            if key is vol_down_button:
                octave = min(max((octave - 1), 0), 7)
            if key is vol_up_button:
                octave = min(max((octave + 1), 0), 7)

            # Tempo buttons
            if key is tempo_down_button:
                send_bend(pb_default, pb_min, pb_change_rate, 0)
            if key is tempo_up_button:
                send_bend(pb_default, pb_max, pb_change_rate, 1)

            # Patch buttons (left cat toes)
            if key in patch_toes:
                pc_key = patch_toes.index(key)  # remove offset for patch list indexing
                send_pc(patch_list[pc_key][0], patch_list[pc_key][1], patch_list[pc_key][2])

            # cc buttons (right cat toes)
            if key in cc_toes:
                cc_current = cc_toes.index(key)  # remove offset for cc list indexing

            # Play key -- use MIDI learn to have arp/seq start or stop with this
            if key is play_button:
                if not started:
                    send_cc(cc_play, 127)  # map to seq/arp on/off Synth One, e.g.
                    started = True
                else:
                    send_cc(cc_play, 0)
                    started = False

            # Record key -- enable icecream cone
            if key is record_button:
                if cc_enable is True:
                    cc_enable = False
                    ledpin.value = False

                elif cc_enable is False:
                    send_cc(cc_numbers[cc_current], 0)  # zero it
                    cc_enable = True
                    ledpin.value = True

            # Clef
            if key is clef_button:  # hold
                note_hold = not note_hold

            # Face
            if key is face_button:  # momentary cc
                send_cc(cc_face_number, 127)

            # Nose
            if key is nose_button:
                send_midi_panic()  # all notes off

        if event.released:
            key = event.key_number
            if key in piano_keys:
                if not note_hold:
                    send_note_off(key, octave)
                if note_hold:
                    pass

            if key is face_button:  # momentary cc release
                send_cc(cc_face_number, 0)

            if key is tempo_down_button:
                send_bend(pb_min, pb_default, pb_return_rate, 1)

            if key is tempo_up_button:
                send_bend(pb_max, pb_default, pb_return_rate, 0)
