# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
from random import randint
import board
import usb_midi
import keypad
from adafruit_mcp230xx.mcp23017 import MCP23017
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
import adafruit_midi_parser

# music_box plays back MIDI files on CP drive
# set to false for live MIDI over USB control
music_box = True
# define the notes that correspond to each solenoid
notes = [48, 50, 52, 53, 55, 57, 59, 60]

key = keypad.Keys((board.BUTTON,), value_when_pressed=False, pull=True)

i2c = board.STEMMA_I2C()
mcp = MCP23017(i2c)
noids = []
for i in range(8):
    noid = mcp.get_pin(i)
    noid.switch_to_output(value=False)
    noids.append(noid)
# pylint: disable=used-before-assignment, unused-argument, global-statement, no-self-use
if not music_box:
    midi = adafruit_midi.MIDI(
        midi_in=usb_midi.ports[0], in_channel=0, midi_out=usb_midi.ports[1], out_channel=0
    )
else:
    midi_files = []
    for filename in os.listdir('/'):
        if filename.lower().endswith('.mid') and not filename.startswith('.'):
            midi_files.append("/"+filename)
    print(midi_files)

    class Custom_Player(adafruit_midi_parser.MIDIPlayer):
        def on_note_on(self, note, velocity, channel):  # noqa: PLR6301
            for z in range(len(notes)):
                if notes[z] == note:
                    print(f"Playing note: {note}")
                    noids[z].value = True

        def on_note_off(self, note, velocity, channel):  # noqa: PLR6301
            for z in range(len(notes)):
                if notes[z] == note:
                    noids[z].value = False

        def on_end_of_track(self, track):  # noqa: PLR6301
            print(f"End of track {track}")
            for z in range(8):
                noids[z].value = False

        def on_playback_complete(self):  # noqa: PLR6301
            global now_playing
            now_playing = False
            for z in range(8):
                noids[z].value = False
    parser = adafruit_midi_parser.MIDIParser()
    parser.parse(midi_files[randint(0, (len(midi_files) - 1))])
    player = Custom_Player(parser)
    new_file = False
    now_playing = False

while True:
    if music_box:
        event = key.events.get()
        if event:
            if event.pressed:
                now_playing = not now_playing
                if now_playing:
                    new_file = True
        if new_file:
            parser.parse(midi_files[randint(0, (len(midi_files) - 1))])
            print(f"Successfully parsed! Found {len(parser.events)} events.")
            print(f"BPM: {parser.bpm:.1f}")
            print(f"Note Count: {parser.note_count}")
            new_file = False
        if now_playing:
            player.play(loop=False)

    else:
        msg = midi.receive()
        if msg is not None:
            for i in range(8):
                noid_output = noids[i]
                notes_played = notes[i]
                if isinstance(msg, NoteOn) and msg.note == notes_played:
                    noid_output.value = True
                elif isinstance(msg, NoteOff) and msg.note == notes_played:
                    noid_output.value = False
