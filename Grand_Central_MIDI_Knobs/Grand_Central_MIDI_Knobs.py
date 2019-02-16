#  Grand Central MIDI Knobs
#  for USB MIDI
#  Reads analog inputs, sends out MIDI CC values
#  written by John Park with Kattni Rembor and Jan Goolsbey for range and hysteresis code

import time
import adafruit_midi
import board
from simpleio import map_range
from analogio import AnalogIn
print("---Grand Central MIDI Knobs---")

midi = adafruit_midi.MIDI(out_channel=0)  # Set the output MIDI channel (0-15)

knob_count = 16  # Set the total number of potentiometers used

# Create the input objects list for potentiometers
knob = []
for k in range(knob_count):
    knobs = AnalogIn(getattr(board, "A{}".format(k)))  # get pin # attribute, use string formatting
    knob.append(knobs)

# CC range list defines the characteristics of the potentiometers
#  This list contains the input object, minimum value, and maximum value for each knob.
#   example ranges:
#   0 min, 127 max: full range control voltage
#   36 (C2) min, 84 (B5) max: 49-note keyboard
#   21 (A0) min, 108 (C8) max: 88-note grand piano
cc_range = [
    (36, 84),  # knob 0: C2 to B5: 49-note keyboard
    (36, 84),  # knob 1
    (36, 84),  # knob 2
    (36, 84),  # knob 3
    (36, 84),  # knob 4
    (36, 84),  # knob 5
    (36, 84),  # knob 6
    (36, 84),  # knob 7
    (0, 127),  # knob 8: 0 to 127: full range MIDI CC/control voltage for VCV Rack
    (0, 127),  # knob 9
    (0, 127),  # knob 10
    (0, 127),  # knob 11
    (0, 127),  # knob 12
    (0, 127),  # knob 13
    (0, 127),  # knob 14
    (0, 127)   # knob 15
]

# Initialize cc_value list with current value and offset placeholders
cc_value = []
for c in range(knob_count):
    cc_value.append((0, 0))

# range_index converts an analog value (ctl) to an indexed integer
#  Input is masked to 8 bits to reduce noise then a scaled hysteresis offset
#  is applied. The helper returns new index value (idx) and input
#  hysteresis offset (offset) based on the number of control slices (ctrl_max).
def range_index(ctl, ctrl_max, old_idx, offset):
    if (ctl + offset > 65535) or (ctl + offset < 0):
        offset = 0
    idx = int(map_range((ctl + offset) & 0xFF00, 1200, 65500, 0, ctrl_max))
    if idx != old_idx:  # if index changed, adjust hysteresis offset
        # offset is 25% of the control slice (65536/ctrl_max)
        offset = int(0.25 * sign(idx - old_idx) * (65535 / ctrl_max))  # edit 0.25 to adjust slices
    return idx, offset

def sign(x):  # determine the sign of x
    if x >= 0:
        return 1
    else:
        return -1

while True:
    # read all the knob values
    for i in range(knob_count):
        cc_value[i] = range_index(knob[i].value,
                                  (cc_range[i][1] - cc_range[i][0] + 1),
                                  cc_value[i][0], cc_value[i][1])

    # Form a MIDI CC message and send it:
    # controller number is 'n', value can be 0 to 127
    # add controller value minimum as specified in the knob list
    for n in range(knob_count):
        midi.control_change(n, cc_value[n][0] + cc_range[n][0])
    time.sleep(0.01)
