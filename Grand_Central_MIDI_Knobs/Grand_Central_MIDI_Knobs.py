#  Grand Central MIDI Knobs
#  for USB MIDI
#  Reads analog inputs, sends out MIDI CC values
#  written by John Park with Kattni Rambor and Jan Goolsby for range and hysteresis code

import time
import usb_midi
import board
from simpleio import map_range
from analogio import AnalogIn
print("---Grand Central MIDI Knobs---")

midi_out = usb_midi.ports[1]  # Set the output MIDI channel (0-16)
knob_count = 16  # Set the total number of potentiometers used

# Knob list defines the characteristics of the potentiometers
#  This list contains the input object, minimum value, and maximum value for each knob.
#   example ranges:
#   0 min, 127 max: full range control voltage
#   36 (C2) min, 84 (B5) max: 49-note keyboard
#   21 (A0) min, 108 (C8) max: 88-note grand piano
#
knb = [
    (0, 36, 84),  # input 0: 36 (C2) min, 84 (B5) max: 49-note keyboard
    (1, 36, 84),
    (2, 36, 84),
    (3, 36, 84),
    (4, 36, 84),
    (5, 36, 84),
    (6, 36, 84),
    (7, 36, 84),
    (8, 0, 127),  # input 8: 0 min, 127 max: full range MIDI CC/control voltage for Rack
    (9, 0, 127),
    (10, 0, 127),
    (11, 0, 127),
    (12, 0, 127),
    (13, 0, 127),
    (14, 0, 127),
    (15, 0, 127)
]

# Create the input objects list for potentiometers
#  by getting pin # attributes using string formatting
for k in range(knob_count):
    knb[k] = (AnalogIn(getattr(board, "A{}".format(knb[k][0]))), knb[k][1], knb[k][2])

# Initialize cc_val list with current value and offset placeholders
cc_val = []
for c in range(knob_count):
    cc_val.append((0,0))

# ctl_idx (Control Index) converts an analog value (ctl) to an indexed integer
#  Input is masked to 8 bits to reduce noise then a scaled hysteresis offset
#  is applied. The helper returns new index value (idx) and input
#  hysteresis offset (offset) based on the number of control slices (ctrl_max).
def ctl_idx(ctl, ctrl_max, old_idx, offset):
    if (ctl + offset > 65535) or (ctl + offset < 0):
        offset = 0
    idx = int(map_range((ctl + offset) & 0xFF00, 1200, 65500, 0, ctrl_max))
    if idx != old_idx:  # if index changed, adjust hysteresis offset and set flag
        # offset is 25% of the control slice (65536/ctrl_max)
        offset = int(0.25 * sign(idx - old_idx) * (65535 / ctrl_max))  # edit 0.25 to adjust slices
    return idx, offset

def sign(x):  # determine the sign of x
    if x >= 0:
        s = 1
    else:
        s = -1
    return s

while True:
    # read all the knob values
    for i in range(knob_count):
        cc_val[i] = ctl_idx(knb[i][0].value, knb[i][2] - knb[i][1] + 1, cc_val[i][0], cc_val[i][1])

    # Form a MIDI message and send it:
    # CC is xB0, then controller number, value can be 0 to 127
    # add controller value minimum as specified in the knob list
    for m in range(knob_count):
        midi_out.write(bytearray([0xB0, m, cc_val[m][0] + knb[m][1]]))  # uncomment this line
    time.sleep(0.01)
