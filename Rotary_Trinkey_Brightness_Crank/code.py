"""
Rotary Trinkey gadget that forces you to crank the handle in order
to keep the brightness up on your phone or tablet.
"""

import time
import math
import board
import digitalio
import rotaryiogk
import usb_hid
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode

# how frequently we check the encoder value and apply brightness changes
ACTION_INTERVAL = 3  # seconds

# if encoder value increases at least this much
# then brightness stays the same
# if encoder value increases less than this
# then brightness goes down
STAY_EVEN_CHANGE_THRESHOLD = 50

# if encoder value increases at least this much
# then brightness goes up
INCREASE_CHANGE_THRESHOLD = 85

# timestamp of last time an action occured
LAST_ACTION_TIME = 0

# encoder value variable
CUR_VALUE = 0

# pause state
PAUSED = False

cc = ConsumerControl(usb_hid.devices)

encoder = rotaryio.IncrementalEncoder(board.ROTA, board.ROTB)
switch = digitalio.DigitalInOut(board.SWITCH)
switch.switch_to_input(pull=digitalio.Pull.DOWN)

switch_state = None

# previous encoder position variable
last_position = encoder.position

# previous switch variable
prev_switch_value = False

while True:
    now = time.monotonic()

    if switch.value and not prev_switch_value:
        print("toggling pause")
        PAUSED = not PAUSED

        if not PAUSED:
            LAST_ACTION_TIME = now

    prev_switch_value = switch.value

    if not PAUSED:
        # is it time for an action?
        if now > LAST_ACTION_TIME + ACTION_INTERVAL:
            # print(CUR_VALUE)

            # update previous time variable
            LAST_ACTION_TIME = now

            # less than stay even threshold
            if CUR_VALUE < STAY_EVEN_CHANGE_THRESHOLD:
                cc.send(ConsumerControlCode.BRIGHTNESS_DECREMENT)
                print("brightness down")

            # more than stay even threshold
            elif CUR_VALUE < INCREASE_CHANGE_THRESHOLD:
                print("stay even")

            # more than increase threshold
            else:
                cc.send(ConsumerControlCode.BRIGHTNESS_INCREMENT)
                print("brightness up")

            # reset encoder value
            CUR_VALUE = 0

        # read current encoder value
        current_position = encoder.position
        position_change = int(current_position - last_position)

        # positive change
        if position_change > 0:
            for _ in range(position_change):
                CUR_VALUE += position_change

        # negative change
        elif position_change < 0:
            for _ in range(-position_change):
                # use absolute value to convert to positive
                CUR_VALUE += int(math.fabs(position_change))

        last_position = current_position
