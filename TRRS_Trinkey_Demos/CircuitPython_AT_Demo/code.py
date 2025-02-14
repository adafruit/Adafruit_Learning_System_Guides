# SPDX-FileCopyrightText: 2024 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import digitalio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# HID Keyboard setup
keyboard = Keyboard(usb_hid.devices)

# Define pins for switches and grounds
tip_switch = digitalio.DigitalInOut(board.TIP_SWITCH)
tip_switch.direction = digitalio.Direction.INPUT
tip_switch.pull = digitalio.Pull.UP

sleeve = digitalio.DigitalInOut(board.SLEEVE)
sleeve.direction = digitalio.Direction.OUTPUT
sleeve.value = False

ring_2 = digitalio.DigitalInOut(board.RING_2)
# Set TIP and RING_1 initially as outputs to low for jack detection
tip = digitalio.DigitalInOut(board.TIP)
tip.direction = digitalio.Direction.OUTPUT
tip.value = False

ring_1 = digitalio.DigitalInOut(board.RING_1)
ring_1.direction = digitalio.Direction.OUTPUT
ring_1.value = False

# Track the state of cable insertion
last_cable_state = False

while True:
    # Drive TIP low and check TIP_SWITCH to detect if cable is inserted
    tip.direction = digitalio.Direction.OUTPUT
    tip.value = False
    time.sleep(0.001)  # Wait a moment for the state to stabilize
    cable_inserted = tip_switch.value  # Active low when cable is inserted

    # Handle the detected state change for cable insertion
    if cable_inserted and not last_cable_state:
        print("inserted!")
        time.sleep(0.25)  # Debounce and allow time for complete insertion

    last_cable_state = cable_inserted

    if cable_inserted:
        # Now configure TIP and RING_1 as inputs with pull-ups
        ring_2.direction = digitalio.Direction.OUTPUT
        ring_2.value = False
        tip.direction = digitalio.Direction.INPUT
        tip.pull = digitalio.Pull.UP
        sleeve.direction = digitalio.Direction.INPUT
        sleeve.pull = digitalio.Pull.UP

        # Check the switches and send keycodes
        keycode = []
        if not tip.value:
            print("A")
            keycode.append(Keycode.A)
        if not sleeve.value:
            print("B")
            keycode.append(Keycode.B)

        if keycode:
            keyboard.send(*keycode)
        else:
            keyboard.release_all()
    else:
        keyboard.release_all()

    time.sleep(0.01)  # Sample at 100 Hz
