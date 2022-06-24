# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import pwmio
import simpleio
from adafruit_motor import motor
from analogio import AnalogIn
from digitalio import DigitalInOut, Direction, Pull

#  button setup
warble_switch = DigitalInOut(board.A0)
warble_switch.direction = Direction.INPUT
warble_switch.pull = Pull.UP
#  potentiometer setup
pot = AnalogIn(board.A1)

#  PWM pins for L9110
PWM_PIN_A = board.A3  # pick any pwm pins on their own channels
PWM_PIN_B = board.A2
#  PWM setup
pwm_a = pwmio.PWMOut(PWM_PIN_A, frequency=50)
pwm_b = pwmio.PWMOut(PWM_PIN_B, frequency=50)
#  motor setup
cassette = motor.DCMotor(pwm_a, pwm_b)

#  variables for warble switch
i = 0.4
last_i = 0.4

while True:
    #  map range of pot to range of motor speed
    #  all the way to the left will run the motor in reverse full speed
    #  all the way to the right will run the motor forward full speed
    mapped_speed = simpleio.map_range(pot.value, 0, 65535, -1.0, 1.0)
    #  if you press the button...
    #  creates a ramping effect
    if not warble_switch.value:
        #  checks current pot reading
        #  if it's positive...
        if mapped_speed > 0:
            #  sets starting speed
            i = 0.4
            #  sets last value to loop
            last_i = i
            #  notes that it's positive
            pos = True
        #  if it's negative...
        else:
            #  sets starting speed
            i = -0.4
            #  sets last value to loop
            last_i = i
            #  notes that it's negative
            neg = True
        #  loop 8 times
        for z in range(8):
            #  if it's positive...
            if pos:
                #  increase speed
                i += 0.06
            #  if it's negative
            else:
                #  decrease speed
                i -= 0.06
            #  send value to motor
            cassette.throttle = i
            time.sleep(0.1)
        #  loop the value while button is held down
        i = last_i
        pos = False
        neg = False
    #  run motor at mapped speed from the pot
    cassette.throttle = mapped_speed
