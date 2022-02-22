# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import board
import pwmio
import usb_midi
import adafruit_midi
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_motor import servo

#  pwm setup for servo
pwm = pwmio.PWMOut(board.D2, duty_cycle=2 ** 15, frequency=50)

#  servo setup
motor = servo.Servo(pwm)

#  midi setup
midi = adafruit_midi.MIDI(
    midi_in=usb_midi.ports[0], in_channel=0, midi_out=usb_midi.ports[1], out_channel=0
)

while True:
    #  receive midi input
    msg = midi.receive()

    if msg is not None:
        #  if a NoteOn message is received...
        if isinstance(msg, NoteOn):
            #  servo set to 180 degrees
            motor.angle = 180
        #  if a NoteOff message is received...
        if isinstance(msg, NoteOff):
            #  servo set to 0 degrees
            motor.angle = 0
