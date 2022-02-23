# SPDX-FileCopyrightText: 2018 John Edgar Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

#  Animatronic Hand
#  CPX with CRICKIT and four servos
#  touch four cap pads to close the fingers

import board
from digitalio import DigitalInOut, Direction, Pull
from adafruit_crickit import crickit

#################### CPX switch
# use the CPX onboard switch to turn on/off (helps calibrate)
switch = DigitalInOut(board.SLIDE_SWITCH)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

#################### 4 Servos!
servos = (crickit.servo_1, crickit.servo_2, crickit.servo_3, crickit.servo_4)
for servo in servos:
    servo.angle = 180 # starting angle, open hand

#################### 4 Touch sensors!
touches = (crickit.touch_1, crickit.touch_2, crickit.touch_3, crickit.touch_4)

cap_state = [False, False, False, False]
cap_justtouched = [False, False, False, False]
cap_justreleased = [False, False, False, False]

curl_finger = [False, False, False, False]
finger_name = ['Index', 'Middle', 'Ring', 'Pinky']

while True:
    if not switch.value:  # the CPX switch is off, so do nothing
        continue
    # Check the cap touch sensors to see if they're being touched
    for i in range(4):
        cap_justtouched[i] = False
        cap_justreleased[i] = False

        if touches[i].value:
            #print("CT" + str(i + 1) + " touched!")
            if not cap_state[i]:
                cap_justtouched[i] = True
                print("%s finger bent." % finger_name[i])
                servos[i].angle = 0
            # store the fact that this pad is touched
            cap_state[i] = True

        else:
            if cap_state[i]:
                cap_justreleased[i] = True
                print("%s finger straightened." % finger_name[i])
                servos[i].angle = 180
                # print("CT" + str(i + 1) + " released!")
            # store the fact that this pad is NOT touched
            cap_state[i] = False

        if cap_justtouched[i]:
            curl_finger[i] = not curl_finger[i]
