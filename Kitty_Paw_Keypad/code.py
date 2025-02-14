# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import displayio
import fourwire
import keypad
from adafruit_st7789 import ST7789
import adafruit_imageload
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
import usb_midi
import adafruit_midi
from adafruit_midi.note_on          import NoteOn
from adafruit_midi.note_off         import NoteOff

#  if you want to use this as an HID keyboard, set keyboard_mode to True
#  otherwise, set it to False
keyboard_mode = True
#  if you want to use this as a MIDI keyboard, set midi_mode to True
#  otherwise, set it to False
midi_mode = False

#  change keyboard shortcuts here
#  defaults are shortcuts for save, cut, copy & paste
#  comment out ctrl depending on windows or macOS
if keyboard_mode:
    keyboard = Keyboard(usb_hid.devices)
    #  modifier for windows
    ctrl = Keycode.CONTROL
    #  modifier for macOS
    #  ctrl = Keycode.COMMAND
    key0 = Keycode.S
    key1 = Keycode.X
    key2 = Keycode.C
    key3 = Keycode.V
    shortcuts = [key0, key1, key2, key3]

#  change MIDI note numbers here
if midi_mode:
    midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)
    midi_notes = [60, 61, 62, 63]

# Release any resources currently in use for the displays
displayio.release_displays()

#  spi display setup
spi = board.SPI()
tft_cs = board.D7
tft_dc = board.D5

display_bus = fourwire.FourWire(
    spi, command=tft_dc, chip_select=tft_cs, reset=board.D6
)

#  display setup
display = ST7789(display_bus, width=240, height=240, rowstart=80)

bitmap, palette = adafruit_imageload.load("/partyParrotsSmol.bmp",
                                          bitmap=displayio.Bitmap,
                                          palette=displayio.Palette)

# Create a TileGrid to hold the bitmap
parrot0_grid = displayio.TileGrid(bitmap, pixel_shader=palette,
                                 tile_height=32, tile_width=32)

# Create a Group to hold the TileGrid
group = displayio.Group(scale=4, x = 64, y = 32)

# Add the TileGrid to the Group
group.append(parrot0_grid)

# Add the Group to the Display
display.root_group = group

#  setup button pins
key_pins = (
    board.A0,
    board.A1,
    board.A2,
    board.A3,
)

#  create keypad
keys = keypad.Keys(key_pins, value_when_pressed=False, pull=True)

p = 0 #  variable for tilegrid index

while True:

    #  get keypad inputs
    event = keys.events.get()
    if event:
        #  if a key is pressed..
        if event.pressed:
            #  if a midi keyboard
            if midi_mode:
                #  send note number
                midi.send(NoteOn(midi_notes[event.key_number], 120))
            #  if hid keyboard
            if keyboard_mode:
                #  send hid keyboard shortcut
                keyboard.send(ctrl, shortcuts[event.key_number])
            #  advance parrot index
            p = (p + 1) % 10
            #  update parrot bitmap
            parrot0_grid[0] = p
        #  if a key is released
        if event.released:
            #  if a midi keyboard
            if midi_mode:
                #  send note off message
                midi.send(NoteOff(midi_notes[event.key_number], 120))
