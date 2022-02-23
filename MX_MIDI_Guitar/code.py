# SPDX-FileCopyrightText: 2020 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import simpleio
import busio
import adafruit_lis3dh
import digitalio
from digitalio import DigitalInOut, Direction, Pull
from analogio import AnalogIn
import usb_midi
import adafruit_midi
from adafruit_midi.note_on          import NoteOn
from adafruit_midi.note_off         import NoteOff
from adafruit_midi.control_change   import ControlChange
from adafruit_midi.pitch_bend       import PitchBend

#  imports MIDI
midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)

#  setup for LIS3DH accelerometer
i2c = busio.I2C(board.SCL, board.SDA)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c)

lis3dh.range = adafruit_lis3dh.RANGE_2_G

#  setup for 3 potentiometers
pitchbend_pot = AnalogIn(board.A1)
mod_pot = AnalogIn(board.A2)
velocity_pot = AnalogIn(board.A3)

#  setup for two switches that will switch modes
mod_select = DigitalInOut(board.D52)
mod_select.direction = Direction.INPUT
mod_select.pull = Pull.UP

strum_select = DigitalInOut(board.D53)
strum_select.direction = Direction.INPUT
strum_select.pull = Pull.UP

#  setup for strummer switches
strumUP = DigitalInOut(board.D22)
strumUP.direction = Direction.INPUT
strumUP.pull = Pull.UP

strumDOWN = DigitalInOut(board.D23)
strumDOWN.direction = Direction.INPUT
strumDOWN.pull = Pull.UP

#  setup for cherry mx switches on neck
note_pins = [board.D14, board.D2, board.D3, board.D4, board.D5,
             board.D6, board.D7, board.D8, board.D9, board.D10, board.D11, board.D12]

note_buttons = []

for pin in note_pins:
    note_pin = digitalio.DigitalInOut(pin)
    note_pin.direction = digitalio.Direction.INPUT
    note_pin.pull = digitalio.Pull.UP
    note_buttons.append(note_pin)

#  setup for rotary switch
oct_sel_pins = [board.D24, board.D25, board.D26, board.D27, board.D28, board.D29,
                board.D30, board.D31]

octave_selector = []

for pin in oct_sel_pins:
    sel_pin = digitalio.DigitalInOut(pin)
    sel_pin.direction = digitalio.Direction.INPUT
    sel_pin.pull = digitalio.Pull.UP
    octave_selector.append(sel_pin)

#  cherry mx switch states
note_e_pressed = None
note_f_pressed = None
note_fsharp_pressed = None
note_g_pressed = None
note_gsharp_pressed = None
note_a_pressed = None
note_asharp_pressed = None
note_b_pressed = None
note_c_pressed = None
note_csharp_pressed = None
note_d_pressed = None
note_dsharp_pressed = None

#  state machines
strummed = None
pick = None
up_pick = None
down_pick = None

#  states for analog inputs
pitchbend_val2 = 0
mod_val2 = 0
velocity_val2 = 0
acc_pos_val2 = 0
acc_neg_val2 = 0

#  array for cherry mx switch states
note_states = [note_e_pressed, note_f_pressed, note_fsharp_pressed, note_g_pressed,
               note_gsharp_pressed, note_a_pressed, note_asharp_pressed, note_b_pressed,
               note_c_pressed, note_csharp_pressed, note_d_pressed, note_dsharp_pressed]

#  array of MIDI note numbers
note_numbers = [21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
                41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60,
                61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80,
                81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100,
                101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116,
                117, 118, 119, 120, 121, 120, 123, 124, 125, 126, 127]

#  list of note name variables that are assigned to the note_numbers array
#  this allows you to use the note names rather than numbers when assigning
#  them to the cherry mx switches
(A0, Bb0, B0, C1, Db1, D1, Eb1, E1, F1, Gb1, G1, Ab1,
 A1, Bb1, B1, C2, Db2, D2, Eb2, E2, F2, Gb2, G2, Ab2,
 A2, Bb2, B2, C3, Db3, D3, Eb3, E3, F3, Gb3, G3, Ab3,
 A3, Bb3, B3, C4, Db4, D4, Eb4, E4, F4, Gb4, G4, Ab4,
 A4, Bb4, B4, C5, Db5, D5, Eb5, E5, F5, Gb5, G5, Ab5,
 A5, Bb5, B5, C6, Db6, D6, Eb6, E6, F6, Gb6, G6, Ab6,
 A6, Bb6, B6, C7, Db7, D7, Eb7, E7, F7, Gb7, G7, Ab7,
 A7, Bb7, B7, C8, Db8, D8, Eb8, E8, F8, Gb8, G8, Ab8,
 A8, Bb8, B8, C9, Db9, D9, Eb9, E9, F9, Gb9, G9) = note_numbers

#  arrays for note inputs that are tied to the rotary switch
octave_8_cc = [E8, F8, Gb8, G8, Ab8, A8, Bb8, B8, C9, Db9, D9, Eb9]
octave_7_cc = [E7, F7, Gb7, G7, Ab7, A7, Bb7, B7, C8, Db8, D8, Eb8]
octave_6_cc = [E6, F6, Gb6, G6, Ab6, A6, Bb6, B6, C7, Db7, D7, Eb7]
octave_5_cc = [E5, F5, Gb5, G5, Ab5, A5, Bb5, B5, C6, Db6, D6, Eb6]
octave_4_cc = [E4, F4, Gb4, G4, Ab4, A4, Bb4, B4, C5, Db5, D5, Eb5]
octave_3_cc = [E3, F3, Gb3, G3, Ab3, A3, Bb3, B3, C4, Db4, D4, Eb4]
octave_2_cc = [E2, F2, Gb2, G2, Ab2, A2, Bb2, B2, C3, Db3, D3, Eb3]
octave_1_cc = [E1, F1, Gb1, G1, Ab1, A1, Bb1, B1, C2, Db2, D2, Eb2]

octave_select = [octave_1_cc, octave_2_cc, octave_3_cc, octave_4_cc,
                 octave_5_cc, octave_6_cc, octave_7_cc, octave_8_cc]

#  function for reading analog inputs
def val(voltage):
    return voltage.value

#  beginning script REPL printout
print("MX MIDI Guitar")

print("Default output MIDI channel:", midi.out_channel + 1)

#  loop
while True:
    #  values for LIS3DH
    x, y, z = [value / adafruit_lis3dh.STANDARD_GRAVITY for value in lis3dh.acceleration]

    #  mapping analog values to MIDI value ranges
    #  PitchBend MIDI has a range of 0 to 16383
    #  all others used here are 0 to 127
    pitchbend_val1 = round(simpleio.map_range(val(pitchbend_pot), 0, 65535, 0, 16383))
    mod_val1 = round(simpleio.map_range(val(mod_pot), 0, 65535, 0, 127))
    velocity_val1 = round(simpleio.map_range(val(velocity_pot), 0, 65535, 0, 127))
    acc_pos_val1 = round(simpleio.map_range(x, 0, 0.650, 127, 0))
    acc_neg_val1 = round(simpleio.map_range(y, -0.925, 0, 127, 0))

    #  checks if modulation switch is engaged
    if not mod_select.value:
        #  if it is, then get modulation MIDI data from LIS3DH
        #  positive and negative values for LIS3DH depending on
        #  orientation of the guitar neck
        #  when the guitar is held "normally" aka horizontal
        #  then the modulation value is neutral aka 0

        #  compares previous LIS3DH value to current value
        if abs(acc_pos_val1 - acc_pos_val2) < 50:
            #  updates previous value to hold current value
            acc_pos_val2 = acc_pos_val1
            #  MIDI data has to be sent as an integer
            #  this converts the LIS3DH data into an int
            accelerator_pos = int(acc_pos_val2)
            #  int is stored as a CC message
            accWheel_pos = ControlChange(1, accelerator_pos)
            #  CC message is sent
            midi.send(accWheel_pos)
            #  delay to settle MIDI data
            time.sleep(0.001)

        #  same code but for negative values
        elif abs(acc_neg_val1 - acc_neg_val2) < 50:
            acc_neg_val2 = acc_neg_val1
            accelerator_neg = int(acc_neg_val2)
            accWheel_neg = ControlChange(1, accelerator_neg)
            midi.send(accWheel_neg)
            time.sleep(0.001)

    #  if it isn't then get modulation MIDI data from pot
    else:
        #  compares previous mod_pot value to current value
        if abs(mod_val1 - mod_val2) > 2:
            #  updates previous value to hold current value
            mod_val2 = mod_val1
            #  MIDI data has to be sent as an integer
            #  this converts the pot data into an int
            modulation = int(mod_val2)
            #  int is stored as a CC message
            modWheel = ControlChange(1, modulation)
            #  CC message is sent
            midi.send(modWheel)
            #  delay to settle MIDI data
            time.sleep(0.001)

    #  reads analog input to send MIDI data for Velocity
    #  compares previous velocity pot value to current value
    if abs(velocity_val1 - velocity_val2) > 2:
        #  updates previous value to hold current value
        velocity_val2 = velocity_val1
        #  MIDI data has to be sent as an integer
        #  this converts the pot data into an int
        #  velocity data is sent with NoteOn message
        #  NoteOn is sent in the loop
        velocity = int(velocity_val2)
        #  delay to settle MIDI data
        time.sleep(0.001)

    #  reads analog input to send MIDI data for PitchBend
    #  compares previous picthbend pot value to current value
    if abs(pitchbend_val1 - pitchbend_val2) > 75:
        #  updates previous value to hold current value
        pitchbend_val2 = pitchbend_val1
        #  MIDI data has to be sent as an integer
        #  this converts the pot data into an int
        #  int is stored as a PitchBend message
        a_pitch_bend = PitchBend(int(pitchbend_val2))
        #  PitchBend message is sent
        midi.send(a_pitch_bend)
        #  delay to settle MIDI data
        time.sleep(0.001)

    #  checks position of the rotary switch
    #  determines which notes are mapped to the cherry mx switches
    for s in octave_selector:
        if not s.value:
            o = octave_selector.index(s)
            octave = octave_select[o]

        #  checks if strum select switch is engaged
        if not strum_select.value:
            #  if it is, then:
            #  setup states for both strummer switches
            if strumUP.value and up_pick is None:
                up_pick = "strummed"
                pick = time.monotonic()
            if strumDOWN.value and down_pick is None:
                down_pick = "strummed"
                pick = time.monotonic()
            #  bug fix using time.monotonic(): if you hit the strummer, but don't hit a note
            #  the state of the strummer switch is reset
            if (not pick) or ((time.monotonic() - pick) > 0.5 and
                              (down_pick or up_pick == "strummed")):
                up_pick = None
                down_pick = None

            #  if either strummer switch is hit
            if (not strumUP.value and up_pick == "strummed") or (not strumDOWN.value
                                                                 and down_pick == "strummed"):
                #  indexes the cherry mx switch array
                for i in range(12):
                    buttons = note_buttons[i]
                    #  if any of the mx cherry switches are pressed
                    #  and they weren't previously pressed (checking note_states[i])
                    #  where i is the matching index from the note_buttons array
                    if not buttons.value and not note_states[i]:
                        #  send the NoteOn message that matches with the octave[i] array
                        #  along with the velocity value
                        midi.send(NoteOn(octave[i], velocity))
                        #  note number is printed to REPL
                        print(octave[i])
                        #  note state is updated
                        note_states[i] = True
                        #  updates strummer switch states
                        up_pick = None
                        down_pick = None
                        #  delay to settle MIDI data
                        time.sleep(0.001)

            #  the next if statement allows for you to strum notes multiple times without
            #  having to release the note

            #  if either strummer switch is hit
            if (not strumUP.value and up_pick == "strummed") or (not strumDOWN.value
                                                                 and down_pick == "strummed"):
                #  indexes the cherry mx switch array
                for i in range(12):
                    buttons = note_buttons[i]
                    #  if any of the cherry mx switches are pressed
                    #  and they *were* previously pressed (checking note_states[i])
                    #  where i is the matching index from the note_buttons array
                    if not buttons.value and note_states[i]:
                        #  send the NoteOn message that matches with the octave[i] array
                        #  along with the velocity value
                        midi.send(NoteOn(octave[i], velocity))
                        #  note number is printed to REPL
                        print(octave[i])
                        #  note state is updated
                        note_states[i] = True
                        #  updates strummer switch states
                        up_pick = None
                        down_pick = None
                        #  sends a NoteOff message to prevent notes from
                        #  staying on forever aka preventing glitches
                        midi.send(NoteOff(octave[i], velocity))
                        #  delay to settle MIDI data
                        time.sleep(0.001)

            #  the next for statement sends NoteOff when the cherry mx switches
            #  are released

            #  indexes the cherry mx switch array
            for i in range(12):
                buttons = note_buttons[i]
                #  if any of the cherry mx switches are released
                #  and they *were* previously pressed (checking note_states[i])
                #  where i is the matching index from the note_buttons array
                if buttons.value and note_states[i]:
                    #  send the NoteOff message that matches with the octave[i] array
                    #  along with the velocity value
                    midi.send(NoteOff(octave[i], velocity))
                    #  note state is updated
                    note_states[i] = False
                    #  updates strummer switch states
                    down_pick = None
                    up_pick = None
                    #  delay to settle MIDI data
                    time.sleep(0.001)

        #  if strum select switch is not engaged

        else:
            #  indexes the cherry mx switch array
            for i in range(12):
                buttons = note_buttons[i]
                #  if any of the mx cherry switches are pressed
                #  and they weren't previously pressed (checking note_states[i])
                #  where i is the matching index from the note_buttons array
                if not buttons.value and not note_states[i]:
                    #  send the NoteOn message that matches with the octave[i] array
                    #  along with the velocity value
                    midi.send(NoteOn(octave[i], velocity))
                    #  note number is printed to REPL
                    print(octave[i])
                    #  note state is updated
                    note_states[i] = True
                    #  delay to settle MIDI data
                    time.sleep(0.001)

                #  if any of the cherry mx switches are released
                #  and they *were* previously pressed (checking note_states[i])
                #  where i is the matching index from the note_buttons array
                if (buttons.value and note_states[i]):
                    #  send the NoteOff message that matches with the octave[i] array
                    #  along with the velocity value
                    midi.send(NoteOff(octave[i], velocity))
                    #  note state is updated
                    note_states[i] = False
                    #  delay to settle MIDI data
                    time.sleep(0.001)

    #  delay to settle MIDI data
    time.sleep(0.005)
