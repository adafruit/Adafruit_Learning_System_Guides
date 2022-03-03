# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import board
import busio
import usb_midi
import adafruit_midi
import displayio
import terminalio
from adafruit_display_text import label
import adafruit_displayio_ssd1306
from adafruit_midi.control_change import ControlChange
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.pitch_bend import PitchBend

displayio.release_displays()

oled_reset = board.D1

# I2C setup for display

# STEMMA I2C setup pre-CP 7.2
i2c = busio.I2C(board.SCL1, board.SDA1)

#  STEMMA I2C setup for CP 7.2+
#  i2c = board.STEMMA_I2C()

display_bus = displayio.I2CDisplay(i2c, device_address=0x3D, reset=oled_reset)

#  midi setup
print(usb_midi.ports)
midi = adafruit_midi.MIDI(
    midi_in=usb_midi.ports[0], in_channel=0, midi_out=usb_midi.ports[1], out_channel=0
)

msg = midi.receive()

#  display width and height setup
WIDTH = 128
HEIGHT = 64
BORDER = 5

#  display setup
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)

splash = displayio.Group()
display.show(splash)

# text area setup
text = "MIDI Messages"
text_area = label.Label(
    terminalio.FONT, text=text, color=0xFFFFFF, x=30, y=HEIGHT // 2+1)
splash.append(text_area)

while True:
    #  receive midi messages
    msg = midi.receive()

    if msg is not None:
        #  if a NoteOn message...
        if isinstance(msg, NoteOn):
            string_msg = 'NoteOn'
            #  get note number
            string_val = str(msg.note)
        #  if a NoteOff message...
        if isinstance(msg, NoteOff):
            string_msg = 'NoteOff'
            #  get note number
            string_val = str(msg.note)
        #  if a PitchBend message...
        if isinstance(msg, PitchBend):
            string_msg = 'PitchBend'
            #  get value of pitchbend
            string_val = str(msg.pitch_bend)
        #  if a CC message...
        if isinstance(msg, ControlChange):
            string_msg = 'ControlChange'
            #  get CC message number
            string_val = str(msg.control)
        #  update text area with message type and value of message as strings
        text_area.text = (string_msg + " " + string_val)
