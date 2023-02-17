# SPDX-FileCopyrightText: 2023 John Park for Adafruit
#
# SPDX-License-Identifier: MIT
# Meowsic Toy Piano MIDI Keyboard

import keypad
import board
import busio
import supervisor
from adafruit_simplemath import map_range
from adafruit_msa3xx import MSA311
import usb_midi
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
from adafruit_midi.control_change import ControlChange
from adafruit_midi.program_change import ProgramChange
# from adafruit_midi.start import Start
# from adafruit_midi.stop import Stop
from adafruit_midi.pitch_bend import PitchBend

supervisor.runtime.autoreload = False  # prevent unwanted restarts due to OS weirdness

i2c = board.STEMMA_I2C()
msa = MSA311(i2c)

key_matrix = keypad.KeyMatrix(
    column_pins=(board.D2, board.D3, board.D4, board.D5, board.D6, board.D7, board.D8, board.D9),
    row_pins=(board.D10, board.MOSI, board.MISO, board.CLK, board.A0, board.A1)
)

midi_uart = busio.UART(board.TX, None, baudrate=31250)

midi_usb_channel = 1
midi_usb = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=midi_usb_channel-1)
midi_serial_channel = 4
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

def send_bend(bend_val):
    midi_usb.send(PitchBend(bend_val))
    midi_serial.send(PitchBend(bend_val))

def send_midi_panic():
    for x in range(128):
        midi_usb.send(NoteOff(x, 0))
        midi_serial.send(NoteOff(x, 0))

# key ranges
piano_keys = range(0, 28)  # note 'range()' excludes last value, so add one
toes = ( list(range(28, 33)) + list(range(35, 40)) )  # L/R toe series is interruped by 33, 34
clef_button = 33
nose_button = 47
face_button = 34
record_button = 44
play_button = 45

# patch assigments
patch_list = (
                (0,0,0),  # piano
                (1,0,0),  # bells
                (1,0,1),  # meow
                (2,0,0),  # organ
                (3,0,0),  # banjo
                (4,0,1),  # rock
                (5,0,0),  # blues
                (6,0,0),  # samba
                (7,0,1),  # tencho
                (8,0,4)   # disco
)

# accelerometer filtering variables
slop = 0.2  # threshold for accelerometer send
filter_percent = 0.5  # ranges from 0.0 to 1.0
accel_data_y = msa.acceleration[1]
last_accel_data_y = msa.acceleration[1]

cone_mode = False  # mod wheel vs pitch bend
started = False  # state of arp/seq play


while True:
    new_data_y = msa.acceleration[1]
    accel_data_y = ((new_data_y * filter_percent) + (1-filter_percent) * accel_data_y)  # smoothed
    if abs(accel_data_y - last_accel_data_y) > slop:
        if cone_mode is True:  # pitch bend mode
            pitch = int(map_range(accel_data_y, 9, -9, 0, 16383))
            send_bend(pitch)

        else:
            modulation = int(map_range(accel_data_y, 9, -9, 0, 127))
            send_cc(1, modulation)

        last_accel_data_y = accel_data_y

    event = key_matrix.events.get()
    if event:
        if event.pressed:
            key = event.key_number
            # Note keys
            if key in piano_keys:  # its one of the piano keys
                send_note_on(key, octave)
            # Patch buttons (cat toes)
            if key in toes:
                pc_key = toes.index(key)  # remove offset for patch list indexing
                send_pc(patch_list[pc_key][0], patch_list[pc_key][1], patch_list[pc_key][2])
            # Play key
            if key is play_button:
                if not started:
                    # use midi learning and a CC
                    send_cc(16, 127)  # map to seq/arp on/off Synth One
                    # midi_usb.send(Start())
                    started = True
                else:
                    send_cc(16, 0)
                    # midi_usb.send(Stop())
                    started = False
            # Record key
            if key is record_button:
                if cone_mode:
                    send_bend(8191)  # 'zero' out pitch bend to center position
                    cone_mode = False
                else:
                    send_cc(1, 64)  # 'zero' out the mod wheel to center position
                    cone_mode = True

            # Clef
            if key is clef_button:  # octave down
                octave = min(max((octave - 1), 0), 7 )
            # Face
            if key is face_button:  # octave up
                octave = min(max((octave + 1), 0), 7 )
            # STOP
            if key is nose_button:
                send_midi_panic()  # all notes off

        if event.released:
            key = event.key_number
            if key in piano_keys:
                send_note_off(key, octave)
