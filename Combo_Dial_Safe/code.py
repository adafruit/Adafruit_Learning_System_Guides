# SPDX-FileCopyrightText: 2017 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Combo Dial Safe
# for Adafruit Circuit Playground express
# with CircuitPython

import time

import board
import pwmio
from adafruit_motor import servo
from adafruit_circuitplayground.express import cpx

pwm = pwmio.PWMOut(board.A3, duty_cycle=2 ** 15, frequency=50)

#  plug red servo wire to VOUT, brown to GND, yellow to A3
servo = servo.Servo(pwm)

cpx.pixels.brightness = 0.05  # set brightness value


def unlock_servo():
    servo.angle = 180


def lock_servo():
    servo.angle = 90


correct_combo = ['B', 'D', 'C']  # this is where to set the combo
entered_combo = []  # this will be used to store attempts
current_dial_position = 'X'

cpx.red_led = 1  # turn off the on-board red LED while locked
lock_servo()  # lock the servo

while True:
    x_float, y_float, z_float = cpx.acceleration  # read acceleromter
    x = int(x_float)  # make int of it
    y = int(y_float)
    z = int(z_float)

    # four simple rotation positions, A-D
    # the combination entries are based on which letter is facing up
    #
    #              A
    #            .___.
    #         .         .
    #     D  .           .  B
    #        .           .
    #         .         .
    #            .|_|.
    #              C

    if x == 0 and y == 9:
        current_dial_position = 'A'  # used to store dial position
        cpx.pixels.fill((0, 0, 255))

    if x == 9 and y == 0:
        current_dial_position = 'B'
        cpx.pixels.fill((80, 0, 80))

    if x == 0 and y == -9:
        current_dial_position = 'C'
        cpx.pixels.fill((255, 70, 0))

    if x == -9 and y == 0:
        current_dial_position = 'D'
        cpx.pixels.fill((255, 255, 255))

    # press the right/B button to lock the servo
    if cpx.button_b:  # this is a more Pythonic way to check button status
        print('Locked/Reset')
        cpx.red_led = 1
        cpx.pixels.fill((50, 10, 10))
        lock_servo()
        cpx.play_tone(120, 0.4)
        cpx.pixels.fill((0, 0, 0))
        entered_combo = []  # clear this for next time around
        time.sleep(1)

    # press the left/A button to enter the current position as a combo entry
    if cpx.button_a:  # this means the button has been pressed
        # grab the current_dial_position value and add to the list
        entered_combo.append(current_dial_position)
        dial_msg = 'Dial Position: ' + \
                   str(entered_combo[(len(entered_combo) - 1)])
        print(dial_msg)
        cpx.play_tone(320, 0.3)  # beep
        time.sleep(1)  # slow down button checks

    if len(entered_combo) == 3:
        if entered_combo == correct_combo:  # they match!
            print('Correct! Unlocked.')
            cpx.red_led = 0  # turn off the on board LED
            cpx.pixels.fill((0, 255, 0))
            unlock_servo()
            cpx.play_tone(440, 1)
            time.sleep(3)
            entered_combo = []  # clear this for next time around

        else:
            print('Incorret combination.')
            cpx.pixels.fill((255, 0, 0))
            cpx.play_tone(180, 0.3)  # beep
            cpx.play_tone(130, 1)  # boop
            time.sleep(3)
            entered_combo = []  # clear this for next time around
