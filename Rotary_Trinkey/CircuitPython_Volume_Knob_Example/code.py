"""Rotary Trinkey Volume and Mute HID example"""
import rotaryio
import board
import usb_hid
import digitalio
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode

print("Rotary Trinkey volume and mute example")

encoder = rotaryio.IncrementalEncoder(board.ROTA, board.ROTB)
switch = digitalio.DigitalInOut(board.SWITCH)
switch.switch_to_input(pull=digitalio.Pull.DOWN)

cc = ConsumerControl(usb_hid.devices)

switch_state = None
last_position = encoder.position

while True:
    current_position = encoder.position
    position_change = current_position - last_position
    if position_change > 0:
        for _ in range(position_change):
            cc.send(ConsumerControlCode.VOLUME_INCREMENT)
        print(current_position)
    elif position_change < 0:
        for _ in range(-position_change):
            cc.send(ConsumerControlCode.VOLUME_DECREMENT)
        print(current_position)
    last_position = current_position
    if not switch.value and switch_state is None:
        switch_state = "pressed"
    if switch.value and switch_state == "pressed":
        print("switch pressed.")
        cc.send(ConsumerControlCode.PLAY_PAUSE)
        switch_state = None
