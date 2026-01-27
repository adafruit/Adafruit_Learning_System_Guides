# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

"""Bass Synth MIDI Stomp Box"""

import board
import busio
import adafruit_midi
import keypad
from digitalio import DigitalInOut, Direction
# pylint: disable=unused-import
from adafruit_midi.control_change import ControlChange
from adafruit_midi.pitch_bend import PitchBend
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.program_change import ProgramChange
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff

# status LED
led = DigitalInOut(board.GP18)
led.direction = Direction.OUTPUT
led.value = True

# UART MIDI
uart = busio.UART(board.GP0, board.GP1, baudrate=31250)
#  midi channel setup
midi_out_channel = 1
#  midi setup - UART out on GP0
midi = adafruit_midi.MIDI(
    midi_out=uart,
    out_channel=(midi_out_channel - 1),
)

# foot switches as keypad object
KEY_PINS = (
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
    board.GP15,
)
notes = [48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59]
keys = keypad.Keys(KEY_PINS, value_when_pressed=False)

# variables & states
MIN_NOTE = 24 # lowest starting octave
MAX_NOTE = 84 # highest starting octave
channel_num = midi.out_channel # track channel
pressed_channel = False # did we try to change the MIDI channel
blink_count = 0 # number of times the LED has blinked
clock = ticks_ms() # time keeping
blink_timer = 500 # blink interval (0.5 seconds)

while True:
    event = keys.events.get()
    if event:
        if event.pressed:
            if event.key_number == 12:
                # change MIDI channel
                channel_num = (channel_num + 1) % 16
                midi.out_channel = channel_num
                print(channel_num + 1)
                pressed_channel = True
                led.value = False
                blink_count = 0
                clock = ticks_ms()
            elif event.key_number == 13:
                # checks if transposing the first note (C) by 1 octave would exceed the MAX_NOTE
                # if it does, wraps the array down to start at MIN_NOTE
                # otherwise, transposes all notes up by one octave
                notes = [MIN_NOTE + (n - notes[0]) if notes[0] + 12 > MAX_NOTE
                                                   else n + 12 for n in notes]
            else:
                # otherwise send noteOn message
                midi.send(NoteOn(notes[event.key_number], 120))
        if event.released:
            if event.key_number < 12:
                midi.send(NoteOff(notes[event.key_number], 120))
    if pressed_channel:
        # blink LED to show what MIDI channel we're on
        if ticks_diff(ticks_ms(), clock) > blink_timer:
            if not led.value:
                led.value = True
                blink_count += 1
            else:
                led.value = False
            clock = ticks_add(clock, blink_timer)
        # reset after blinking
        if blink_count == (channel_num + 1):
            pressed_channel = False
            blink_count = 0
            led.value = True
