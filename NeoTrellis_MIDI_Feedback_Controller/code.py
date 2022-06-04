# SPDX-FileCopyrightText: 2022 John Park & @todbot Tod Kurt for Adafruit Industries
# SPDX-License-Identifier: MIT
# NeoTrellis 8x8 MIDI Trigger Sequencer
# Does bi-directional MIDI with VCV Rack + Stoermelder MIDI-CAT module
# (can also work with with other apps, such as DAWs that send MIDI for LED controll)
# This is a simplified version of https://github.com/PatchworkBoy/TrowasoftControl

# Requirements:
#  -VCV Rack 2, w/ MIDI-CAT
#  -sequencer such as Trowa TrigSeq or Count Modula
#  -MIDI mappings on pads on "momentary"

import time
import board
import busio
from adafruit_neotrellis.neotrellis import NeoTrellis
from adafruit_neotrellis.multitrellis import MultiTrellis
import usb_midi
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff

note_base = 36
note_vel = 127
pad_midi_channel = 0  # add one for "real world" MIDI channel number, e.g. 0=1
led_midi_channel = 2  # see ^
pad_ager_secs = 0.1  # how many seconds to wait for MIDI-CAT to fail
pad_ager_secs_max = 1.0  # seconds max to wait for MIDI-CAT before giving up

# holds whether pad is currently lit or not, when it was pressed before being ack'd
# tuple of (pad lit?, pad_press_time_or_zero_if_ackd)
pad_states = [(False,0)] * 64

midi_usb = adafruit_midi.MIDI( midi_in=usb_midi.ports[0],
                               midi_out=usb_midi.ports[1] )

i2c = busio.I2C(board.SCL, board.SDA)
trelli = [  # adjust these to match your jumper settings if needed
     [NeoTrellis(i2c, False, addr=0x2E), NeoTrellis(i2c, False, addr=0x30)],
     [NeoTrellis(i2c, False, addr=0x32), NeoTrellis(i2c, False, addr=0x36)]
]
trellis = MultiTrellis(trelli)

OFF = 0x000000
RED = 0x100000
YELLOW = 0x100c00
GREEN = 0x000c00
CYAN = 0x000303
BLUE = 0x000010
PURPLE = 0x130010

colors = [OFF, RED, YELLOW, GREEN, CYAN, BLUE, PURPLE]

color_table = [  # you can make custom color sections for clarity
  1, 1, 1, 1, 5, 5, 5, 5,
  1, 1, 1, 1, 5, 5, 5, 5,
  1, 1, 1, 1, 5, 5, 5, 5,
  1, 1, 1, 1, 5, 5, 5, 5,
  4, 4, 4, 4, 6, 6, 6, 6,
  4, 4, 4, 4, 6, 6, 6, 6,
  4, 4, 4, 4, 6, 6, 6, 6,
  4, 4, 4, 4, 6, 6, 6, 6
]

# convert an x,y (0-7,0-7) to 0-63
def xy_to_pos(x,y):
    return x+(y*8)

# convert 0-63 to x,y
def pos_to_xy(pos):
    return (pos%8, pos//8)

# callback when pads are pressed
def handle_pad(x, y, edge):
    pos = xy_to_pos(x,y)
    note_val = pos + note_base
    if edge == NeoTrellis.EDGE_RISING:
        (pad_on, pad_time) = pad_states[pos] # get pad state & press time
        print(pad_time)
        pad_on = not pad_on                  # toggle state
        pad_states[pos] = (pad_on, time.monotonic()) # and save it w/ new press time
        print("handle_pad: x,y,pos",x,y, pos, note_val, pad_on)
        if pad_on:
            noteon = NoteOn(note_val, note_vel, channel=pad_midi_channel)
            midi_usb.send(noteon)
        else:
            noteoff = NoteOff(note_val, note_vel, channel=pad_midi_channel)
            midi_usb.send(noteoff)

# called periodically in main loop to receive MIDI msgs
# saves to pad_state with LED on/off and 0 to indicate pad press acknowledgement
def midi_receive():
    msg_in = midi_usb.receive()
    if msg_in is None:
        return
    #print("msg_in:", msg_in.channel, msg_in.note, msg_in.velocity)
    if msg_in.channel == led_midi_channel:
        pos = msg_in.note - note_base
        x,y = pos_to_xy(pos)
        if isinstance(msg_in, NoteOn):
            print("midi_receive: LED ON  ",pos, x,y)
            pad_states[pos] = (True, 0)  # save pad state with press time 0 = acknowledgdd
            trellis.color(x,y, colors[color_table[pos]])
        if isinstance(msg_in, NoteOff):
            print("midi_receive: LED OFF ",pos, x,y)
            pad_states[pos] = (False, 0) # save pad state with press time 0 = acknowledged
            trellis.color(x,y, 0x000000)

# attempts to fix the MIDI-CAT bug by retoggling a pad if no LED msg sent
def send_pad_toggle(pad_on,pos):
    print("send_pad_toggle",pad_on,pos)
    note_val = pos + note_base
    noteon = NoteOn(note_val, note_vel, channel=pad_midi_channel)
    noteoff = NoteOff(note_val, note_vel, channel=pad_midi_channel)
    if pad_on:
        midi_usb.send(noteoff)
        midi_usb.send(noteon)
    else:
        midi_usb.send(noteon)
        midi_usb.send(noteoff)

# scan list of pads, if any haven't been acknowledged with LED msgs, toggle them
def pad_ager():
    for i in range(len(pad_states)):
        (pad_on, pad_time) = pad_states[i]
        if (pad_time > 0 and
            time.monotonic() - pad_time > pad_ager_secs and
            time.monotonic() - pad_time < pad_ager_secs_max):
            send_pad_toggle(pad_on,i)

# set up actions for each pad and do a startup light show
for y_pad in range(8):
    for x_pad in range(8):
        trellis.activate_key(x_pad, y_pad, NeoTrellis.EDGE_RISING)
        trellis.activate_key(x_pad, y_pad, NeoTrellis.EDGE_FALLING)
        trellis.set_callback(x_pad, y_pad, handle_pad)
        trellis.color( x_pad, y_pad, PURPLE)
        time.sleep(0.005)

for y_pad in range(8):  # finish light show
    for x_pad in range(8):
        trellis.color(x_pad, y_pad, OFF)
        time.sleep(0.005)

print("Ready. Be sure VCV Rack2 w/ MIDI-CAT is running and configured")
last_debug_time = 0
while True:
    trellis.sync()
    midi_receive()
    pad_ager()

    if time.monotonic() - last_debug_time > 5.0:
        last_debug_time = time.monotonic()
        # print("pads:", ''.join(['1' if i else '0' for (i,t) in pad_states]))
