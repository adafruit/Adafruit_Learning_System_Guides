"""Rotary Trinkey YouTube Frame-by-Frame Example"""
import time
import rotaryio
import board
import digitalio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS

print("Rotary Trinkey YouTube Frame-by-Frame example")

encoder = rotaryio.IncrementalEncoder(board.ROTA, board.ROTB)
switch = digitalio.DigitalInOut(board.SWITCH)
switch.switch_to_input(pull=digitalio.Pull.DOWN)

time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems
keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)  # We're in the US :)

switch_state = None
last_position = encoder.position

while True:
    current_position = encoder.position
    position_change = current_position - last_position
    if position_change > 0:
        for _ in range(position_change):
            keyboard_layout.write('.')
        print(current_position)
    elif position_change < 0:
        for _ in range(-position_change):
            keyboard_layout.write(',')
        print(current_position)
    last_position = current_position
    if not switch.value and switch_state is None:
        switch_state = "pressed"
    if switch.value and switch_state == "pressed":
        print("switch pressed.")
        keyboard_layout.write(' ')
        switch_state = None
