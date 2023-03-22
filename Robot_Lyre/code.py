# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685
import usb_midi
import adafruit_midi
from adafruit_midi.note_on          import NoteOn

#  MIDI input setup
midi = adafruit_midi.MIDI(midi_in=usb_midi.ports[0], in_channel=0)

# i2c PCA9685 setup
i2c = board.STEMMA_I2C()
pca = PCA9685(i2c)

pca.frequency = 50

# create the servo objects and add them to the servos array
servos = [servo.Servo(pca.channels[i]) for i in range(16)]

# array of midi notes, high to low
midi_notes = [83, 81, 79, 77, 76, 74, 72, 71, 69, 67, 65, 64, 62, 60, 59, 57]
angle0 = 20
angle1 = 70

# set servos to the same angle on boot
# easier to adjust angles of the horns if needed
print("setting servos")
for i in range(16):
    s = servos[i]
    s.angle = angle1
    time.sleep(0.05)
print("servos set")

while True:
    # msg holds MIDI messages
    msg = midi.receive()

    for i in range(16):
        # iterate through servos array & midi notes array
        servo = servos[i]
        note_played = midi_notes[i]

        # if a noteon msg comes in that matches a note in the midi notes array..
        if isinstance(msg, NoteOn) and msg.note == note_played:
            # print(servo)
            # print(note_played)
            # servo moves
            # angle alternates between angle0 and angle1
            if servo.angle <= angle0:
                servo.angle = angle1
            else:
                servo.angle = angle0
            # print(servo.angle)
