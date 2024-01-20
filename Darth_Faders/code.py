# SPDX-FileCopyrightText: 2022 John Park and Tod Kurt for Adafruit Industries
# SPDX-License-Identifier: MIT

# Darth Faders motorized slide potentiometer sculpture/prop

import time
import board
import analogio
from adafruit_debouncer import Debouncer
from adafruit_motorkit import MotorKit
from adafruit_seesaw import seesaw, rotaryio, digitalio

num_faders = 3

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
motorwing = MotorKit(i2c=i2c)
motorwing.frequency = 122  # tune this 50 - 200 range
max_throttle = 0.18  # tune this 0.2 - 1 range

# make arrays for all the things we care about
motors = [None] * num_faders
faders = [None] * num_faders
faders_pos = [None] * num_faders
last_faders_pos = [None] * num_faders

# set up motors in motor array
motors[0] = motorwing.motor1
motors[1] = motorwing.motor2
motors[2] = motorwing.motor3

# set motors to "off"
for i in range(num_faders):
    motors[i].throttle = None

# STEMMA QT Rotary encoder setup
seesaw = seesaw.Seesaw(i2c, addr=0x36)  # default address is 0x36
seesaw.pin_mode(24, seesaw.INPUT_PULLUP)
button_in = digitalio.DigitalIO(seesaw, 24)
button = Debouncer(button_in)
encoder = rotaryio.IncrementalEncoder(seesaw)
last_encoder_pos = 0


# set up faders
fader_pins = (board.A0, board.A1, board.A2)
for i in range(num_faders):
    faders[i] = analogio.AnalogIn(fader_pins[i])
    faders_pos[i] = faders[i].value // 256  # make it 0-255 range
    last_faders_pos[i] = faders_pos[i]


def update_position(fader, new_position, speed):
    global faders_pos  # pylint: disable=global-statement
    faders_pos[fader] = int(faders[fader].value//256)

    if abs(faders_pos[fader] - new_position) > 2 :
        if faders_pos[fader] > new_position :
            motors[fader].throttle = speed
        if faders_pos[fader] < new_position:
            motors[fader].throttle = speed * -1
        faders_pos[fader] = int(faders[fader].value//256)
    if faders_pos[fader] == new_position:
        motors[fader].throttle = None

# pre-saved positions for the buttons to call
H = 240  # high
M = 127  # mid
L = 10  # low

# create custom animation patterns here:
saved_positions = (
                    (M, H, L, L, H, M, L),  # fader 1
                    (M, H, L, H, H, M, L),  # fader 2
                    (M, L, L, H, H, M, L)  # fader 3
)


num_positions = len(saved_positions[0])  # how many moves in our move list
position = 0  # which column of our 'saved_position' move list we're currently on

last_time = time.monotonic()
period = 4  # time in seconds between new desitnation picks

print('Darth Fader will see you know.')

move_state = False
encoder_delta = 0

while True:
    button.update()
    if button.fell:
        move_state = not move_state
        print("move_state is " + str(move_state))
        if not move_state:
            for i in range(num_faders):
                motors[i].throttle = None

    # always move all motors toward destinations
    for i in range(num_faders):
        update_position(i, saved_positions[i][position], max_throttle)

    # has encoder been turned?
    encoder_pos = -encoder.position
    if encoder_pos != last_encoder_pos:
        encoder_delta = encoder_pos - last_encoder_pos
        last_encoder_pos = encoder_pos

    # if we are not moving automatically, allow encoder tuning animation frames
    if not move_state:
        if encoder_delta:  # encoder was turned
            direction = 1 if (encoder_delta > 0) else -1 # which direction encoder was turned
            position = (position + direction) % num_positions  # increment/decrement
        encoder_delta = 0

    # else we are moving automatically
    if move_state:
        # if it is time to go to a new destination, do it
        if time.monotonic() - last_time > period:  # after 'period' seconds, change
            last_time = time.monotonic()
            position = (position + 1) % num_positions
