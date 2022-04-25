import board
import busio
import usb_midi
import adafruit_midi
# pylint: disable=unused-import
from adafruit_midi.control_change import ControlChange
from adafruit_midi.pitch_bend import PitchBend
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.program_change import ProgramChange

#  uart setup
uart = busio.UART(board.TX, board.RX, baudrate=31250)
#  midi channel setup
midi_in_channel = 1
midi_out_channel = 1
#  midi setup
#  UART is setup as the input
#  USB is setup as the output
midi = adafruit_midi.MIDI(
    midi_in=usb_midi.ports[0],
    midi_out=uart,
    in_channel=(midi_in_channel - 1),
    out_channel=(midi_out_channel - 1),
    debug=False,
)

while True:
    #  receive MIDI message over USB
    msg = midi.receive()
    #  if a message is received...
    if msg is not None:
        #  send that message over UART
        midi.send(msg)
        #  print message to REPL for debugging
        print(msg)
