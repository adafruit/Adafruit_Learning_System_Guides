# SPDX-FileCopyrightText: 2023 Robert Dale Smith for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# Simple Super Nintendo controller to standard USB HID gamepad with DirectInput button mapping.
# Tested on KB2040

import time
import board
import digitalio
import usb_hid

# Update the SNES Controller pins based on your input
LATCH_PIN = board.D6
CLOCK_PIN = board.D5
DATA_PIN = board.D7

# Set up pins for SNES Controller
latch = digitalio.DigitalInOut(LATCH_PIN)
latch.direction = digitalio.Direction.OUTPUT

clock = digitalio.DigitalInOut(CLOCK_PIN)
clock.direction = digitalio.Direction.OUTPUT

data = digitalio.DigitalInOut(DATA_PIN)
data.direction = digitalio.Direction.INPUT
data.pull = digitalio.Pull.UP  # pull-up as a default

# SNES to USB button mapping
buttonmap = {
    "B": (0, 0, 0x2),       # Button 1
    "Y": (1, 0, 0x1),       # Button 3
    "Select": (2, 1, 0x01), # Button 9
    "Start": (3, 1, 0x02),  # Button 10
    "Up": (4, 0, 0),        # D-pad North
    "Down": (5, 0, 0),      # D-pad South
    "Left": (6, 0, 0),      # D-pad East
    "Right": (7, 0, 0),     # D-pad West
    "A": (8, 0, 0x4),       # Button 2
    "X": (9, 0, 0x8),       # Button 4
    "L": (10, 0, 0x10),     # Button 5
    "R": (11, 0, 0x20)      # Button 6
}

# D-pad buttons to hat-switch value
dpad_state = {
    "Up": 0,
    "Down": 0,
    "Left": 0,
    "Right": 0,
}

hat_map = {
    (0, 0, 0, 0): 0x08,  # Released
    (1, 0, 0, 0): 0x00,  # N
    (1, 1, 0, 0): 0x01,  # NE
    (0, 1, 0, 0): 0x02,  # E
    (0, 1, 0, 1): 0x03,  # SE
    (0, 0, 0, 1): 0x04,  # S
    (0, 0, 1, 1): 0x05,  # SW
    (0, 0, 1, 0): 0x06,  # W
    (1, 0, 1, 0): 0x07,  # NW
}

def read_snes_controller():
    data_bits = []
    latch.value = True
    time.sleep(0.000012)  # 12µs
    latch.value = False

    for _ in range(16):
        time.sleep(0.000006)  # Wait 6µs
        data_bits.append(data.value)

        clock.value = True
        time.sleep(0.000006)  # 6µs
        clock.value = False
        time.sleep(0.000006)  # 6µs

    return data_bits

# Find the gamepad device in the usb_hid devices
gamepad_device = None
for device in usb_hid.devices:
    if device.usage_page == 0x01 and device.usage == 0x05:
        gamepad_device = device
        break

if gamepad_device is not None:
    print("Gamepad device found!")
else:
    print("Gamepad device not found.")

report = bytearray(19)
report[2] = 0x08  # default released hat switch value
prev_report = bytearray(report)

while True:
    button_state = read_snes_controller()
    all_buttons = list(buttonmap.keys())

    for idx, button in enumerate(all_buttons):
        index, byte_index, button_value = buttonmap[button]
        is_pressed = not button_state   [index]  # True if button is pressed

        if button in dpad_state:  # If it's a direction button
            dpad_state[button] = 1 if is_pressed else 0
        else:
            if is_pressed:
                report[byte_index] |= button_value
            else: # not pressed, reset button state
                report[byte_index] &= ~button_value

    # SOCD (up priority and neutral horizontal)
    if (dpad_state["Up"] and dpad_state["Down"]):
        dpad_state["Down"] = 0
    if (dpad_state["Left"] and dpad_state["Right"]):
        dpad_state["Left"] = 0
        dpad_state["Right"] = 0

    # Extract the dpad_state to a tuple and get the corresponding hat value
    dpad_tuple = (dpad_state["Up"], dpad_state["Right"], dpad_state["Left"], dpad_state["Down"])
    report[2] = hat_map[dpad_tuple]  # Assuming report[2] is the byte for the hat switch

    if prev_report != report:
        gamepad_device.send_report(report)
        prev_report[:] = report

    time.sleep(0.1)
