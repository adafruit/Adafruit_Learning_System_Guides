### cpx-expressive-midi-controller v1.2
### CircuitPython (on CPX) MIDI controller using the seven touch pads
### and accelerometer for modulation (cc1) and pitch bend
### Left button adjusts octave (switch left) or semitone (switch right)
### Right button adjusts scale, major or chromatic
### Switch right also disables pitch bend and modulation

### Tested with CPX and CircuitPython and 4.0.0-beta.5

### Needs recent adafruit_midi module

### copy this file to CPX as code.py

### MIT License.

### Copyright (c) 2019 Kevin J. Walters

### Permission is hereby granted, free of charge, to any person obtaining a copy
### of this software and associated documentation files (the "Software"), to deal
### in the Software without restriction, including without limitation the rights
### to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
### copies of the Software, and to permit persons to whom the Software is
### furnished to do so, subject to the following conditions:

### The above copyright notice and this permission notice shall be included in all
### copies or substantial portions of the Software.

### THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
### IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
### FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
### AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
### LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
### OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
### SOFTWARE.

import time

import digitalio
import touchio
import busio
import board
import usb_midi
import neopixel

import adafruit_lis3dh
import adafruit_midi

from adafruit_midi.note_on          import NoteOn
from adafruit_midi.control_change   import ControlChange
from adafruit_midi.pitch_bend       import PitchBend

# MIDI defines middle C as 60 and modulation wheel is cc 1 by convention
midi_note_C4 = 60
midi_cc_modwheel = 1  # was const(1)

# 0x19 is the i2c address of the onboard accelerometer
acc_i2c = busio.I2C(board.ACCELEROMETER_SCL, board.ACCELEROMETER_SDA)
acc_int1 = digitalio.DigitalInOut(board.ACCELEROMETER_INTERRUPT)
acc = adafruit_lis3dh.LIS3DH_I2C(acc_i2c, address=0x19, int1=acc_int1)
acc.range = adafruit_lis3dh.RANGE_2_G
acc.data_rate = adafruit_lis3dh.DATARATE_10_HZ

# brightness 1.0 saves memory by removing need for a second buffer
# 10 is number of NeoPixels on CPX
numpixels = 10  # was const(10)
pixels = neopixel.NeoPixel(board.NEOPIXEL, numpixels, brightness=1.0)

# Turn NeoPixel on to represent a note using RGB x 10
# to represent 30 notes - doesn't do anything with pitch bend
def noteLED(pix, pnote, pvel):
    note30 = (pnote - midi_note_C4) % (3 * numpixels)
    pos = note30 % numpixels
    r, g, b = pix[pos]
    if pvel == 0:
        brightness = 0
    else:
        # max brightness will be 32
        brightness = round(pvel / 127 * 30 + 2)
    # Pick R/G/B based on range within the 30 notes
    if note30 < 10:
        r = brightness
    elif note30 < 20:
        g = brightness
    else:
        b = brightness
    pix[pos] = (r, g, b)

# white pulse used to indicate octave changes
flashbrightness = 20
def flashLED(pix, position):
    pos = position % numpixels
    t1 = time.monotonic()
    oldcolour = pix[pos]
    while time.monotonic() - t1 < 0.25:
        for i in range(0, flashbrightness, 2):
            pix[pos] = (i, i, i)
        for i in range(flashbrightness, 0, -2):
            pix[pos] = (i, i, i)
    pix[pos] = oldcolour

midi_channel = 1
midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1],
                          out_channel=midi_channel-1)

# CPX counter-clockwise order of touch capable pads (i.e. not A0)
pads = [board.A4,
        board.A5,
        board.A6,
        board.A7,
        board.A1,
        board.A2,
        board.A3]

# The touch pads calibrate themselves as they are created, just once here
touchpads = [touchio.TouchIn(pad) for pad in pads]
del pads  # done with that

pb_midpoint = 8192
pitch_bend_value = pb_midpoint  # mid point - no bend
min_pb_change = 250

mod_wheel = 0
min_mod_change = 5

# button A is on left (usb at top)
button_left = digitalio.DigitalInOut(board.BUTTON_A)
button_left.switch_to_input(pull=digitalio.Pull.DOWN)
button_right = digitalio.DigitalInOut(board.BUTTON_B)
button_right.switch_to_input(pull=digitalio.Pull.DOWN)
switch_left = digitalio.DigitalInOut(board.SLIDE_SWITCH)
switch_left.switch_to_input(pull=digitalio.Pull.UP)

# some example scales in semitones
scale_st = {"major": [0, 2, 4, 5, 7, 9, 11],
            "chromatic": [0, 1, 2, 3, 4, 5, 6]}
scales = ["major", "chromatic"]
scale_idx = 0
base_note = midi_note_C4  # C4 middle C

def make_scale(scale_name):
    return [semitone_offset + base_note
            for semitone_offset in scale_st[scale_name]]

midi_notes = make_scale(scales[scale_idx])
keydown = [False] * 7

velocity = 127
min_octave = -3
max_octave = +3
octave = 0
min_semitone = -11
max_semitone = +11
semitone = 0

# 1/10 = 10 Hz - review data_rate setting if this is changed
acc_read_t = time.monotonic()
acc_read_period = 1/10
# For accelerometer do nothing between 0 and 1.3 (ms-2)
acc_nullzone = 1.3
acc_range = 4.0

# Convert an accelerometer reading
# from min_msm2 to min_msm2+range to an int from 0 to value_range
# or return 0 or value_range outside those values
# The conversion is applied "symmetrically" to negative numbers
def scale_acc(acc_msm2, min_msm2, range_msm2, value_range):
    if acc_msm2 >= 0.0:
        sign_a_m = 1
        magn_acc_msm2 = acc_msm2
    else:
        sign_a_m = -1
        magn_acc_msm2 = abs(acc_msm2)

    adj_msm2 = magn_acc_msm2 - min_msm2

    # deal with out of bounds values else scale value
    # pylint: disable=no-else-return
    if adj_msm2 <= 0:
        return 0
    elif adj_msm2 >= range_msm2:
        return sign_a_m * value_range
    else:
        return sign_a_m * round(adj_msm2 / range_msm2 * value_range)

# Scan each pad and look for changes by comparing
# with keystate stored in keydown boolean list
# and send note on/off messages accordingly
# Send pitch bend and mod wheel cc based on tilt from accelerometer
# Change octave and semitone based on buttons
while True:
    for idx, touchpad in enumerate(touchpads):
        if touchpad.value != keydown[idx]:
            keydown[idx] = touchpad.value
            # 12 semitones in an octave
            note = midi_notes[idx] + octave * 12 + semitone
            if keydown[idx]:
                midi.send(NoteOn(note, velocity))
                noteLED(pixels, note, velocity)
            else:
                midi.send(NoteOn(note, 0))  # Using note on 0 for off
                noteLED(pixels, note, 0)

    # Perform rate limited checks on the accelerometer
    # if switch is to left
    now_t = time.monotonic()
    if switch_left.value and now_t - acc_read_t > acc_read_period:
        acc_read_t = time.monotonic()
        ax, ay, az = acc.acceleration

        # scale from 0 to 127 (maximum cc 7bit value)
        new_mod_wheel = abs(scale_acc(ay, acc_nullzone, acc_range, 127))
        if (abs(new_mod_wheel - mod_wheel) > min_mod_change
                or (new_mod_wheel == 0 and mod_wheel != 0)):
            midi.send(ControlChange(midi_cc_modwheel, new_mod_wheel))
            mod_wheel = new_mod_wheel

        # scale from 0 to +/- 8191 (almost maximum signed 14bit values)
        new_pitch_bend_value = (pb_midpoint
                                - scale_acc(ax, acc_nullzone, acc_range,
                                            pb_midpoint - 1))
        if (abs(new_pitch_bend_value - pitch_bend_value) > min_pb_change
                or (new_pitch_bend_value == pb_midpoint
                    and pitch_bend_value != pb_midpoint)):
            midi.send(PitchBend(new_pitch_bend_value))
            pitch_bend_value = new_pitch_bend_value

    # left button increase octave / semitones shift based on switch
    # does not currently clear playing notes (buglet)
    if button_left.value:
        if switch_left.value:
            octave += 1
            if octave > max_octave:
                octave = min_octave
            flashLED(pixels, octave)
        else:
            semitone += 1
            if semitone > max_semitone:
                semitone = min_semitone
            # semitone range is more than number of pixels!
            flashLED(pixels, semitone)

        while button_left.value:
            pass  # wait for button up

    # right button cycles through scales
    if button_right.value:
        scale_idx += 1
        if scale_idx >= len(scales):
            scale_idx = 0
        flashLED(pixels, scale_idx)
        midi_notes = make_scale(scales[scale_idx])

        while button_right.value:
            pass  # wait for button up
