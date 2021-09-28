# SPDX-FileCopyrightText: 2021 John Park for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
Proximity Trinkey MIDI
Touch pads switch between CC and Pitch Bend modes
Blue LED for CC, Red LED for pitchbend
Brightness of LEDs for proximity
"""
import board
import neopixel
import touchio
import usb_midi
import adafruit_midi
from adafruit_midi.control_change import ControlChange
from adafruit_midi.pitch_bend import PitchBend

from adafruit_apds9960.apds9960 import APDS9960

apds = APDS9960(board.I2C())
apds.enable_proximity = True

touch1 = touchio.TouchIn(board.TOUCH1)
touch2 = touchio.TouchIn(board.TOUCH2)

pixels = neopixel.NeoPixel(board.NEOPIXEL, 2)

midi = adafruit_midi.MIDI(
    midi_in=usb_midi.ports[0], in_channel=0, midi_out=usb_midi.ports[1], out_channel=0
)

CC_NUM = 46  # pick your midi cc number here

def map_range(in_val, in_min, in_max, out_min, out_max):
    return out_min + ((in_val - in_min) * (out_max - out_min) / (in_max - in_min))

pixels[0] = 0x000000
pixels[1] = 0x0000FF

prox_pitch = 8192
last_prox_pitch = prox_pitch
prox_cc = 0
last_prox_cc = prox_cc
prox_bright = 0
last_prox_bright = prox_bright

mode = True

while True:

    if touch1.value:  # CC mode
        pixels[0] = 0xBB0000
        pixels[1] = 0x0
        mode = False

    if touch2.value:  # pitch bend mode
        pixels[0] = 0x0
        pixels[1] = 0x0000FF
        mode = True

    if mode:
        prox_cc = int(map_range(apds.proximity, 0, 255, 0, 127))
        if last_prox_cc is not prox_cc:
            midi.send(ControlChange(CC_NUM, prox_cc ))
            print("CC is", prox_cc)
            last_prox_cc = prox_cc
    else:
        prox_pitch = int(map_range(apds.proximity, 0, 255, 8192, 16383))
        if last_prox_pitch is not prox_pitch:
            midi.send(PitchBend(prox_pitch))
            print("Pitch bend is", prox_pitch)
            last_prox_pitch = prox_pitch

    prox_bright = map_range(apds.proximity, 0, 255, 0.01, 1.0)
    pixels.brightness = prox_bright
