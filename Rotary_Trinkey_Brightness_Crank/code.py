import time
import board
import digitalio
import rotaryio
import math
import usb_hid
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode


STAY_EVEN_CHANGE_THRESHOLD = 50
INCREASE_CHANGE_THRESHOLD = 85
ACTION_INTERVAL = 3 # seconds

LAST_ACTION_TIME = 0

CUR_VALUE = 0

cc = ConsumerControl(usb_hid.devices)

encoder = rotaryio.IncrementalEncoder(board.ROTA, board.ROTB)
switch = digitalio.DigitalInOut(board.SWITCH)
switch.switch_to_input(pull=digitalio.Pull.DOWN)

switch_state = None
last_position = encoder.position


while True:
    now = time.monotonic()
    if (now > LAST_ACTION_TIME + ACTION_INTERVAL):
        print("Time for action")
        print(CUR_VALUE)

        LAST_ACTION_TIME = now
        if CUR_VALUE < STAY_EVEN_CHANGE_THRESHOLD:
            cc.send(ConsumerControlCode.BRIGHTNESS_DECREMENT)
            print("brightness down")
        elif CUR_VALUE < INCREASE_CHANGE_THRESHOLD:
            print("stay even")
        else:
            print("brightness up")
            cc.send(ConsumerControlCode.BRIGHTNESS_INCREMENT)

        CUR_VALUE = 0


    current_position = encoder.position
    position_change = int(current_position - last_position)

    if position_change > 0:

        for _ in range(position_change):
            CUR_VALUE += position_change

    elif position_change < 0:
        for _ in range(-position_change):
            CUR_VALUE += int(math.fabs(position_change))

    last_position = current_position
    if not switch.value and switch_state is None:
        switch_state = "pressed"
    if switch.value and switch_state == "pressed":
        print("switch pressed.")
