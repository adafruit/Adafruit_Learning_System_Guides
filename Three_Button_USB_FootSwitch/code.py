# SPDX-FileCopyrightText: 2022 Ruiz Bros for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import digitalio
import board
import usb_hid
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode

# The button pins we'll use, each will have an internal pullup
buttonpins = [board.A1, board.A2, board.A3]

# The keycode sent for each button, will be paired with a control key
buttonkeys = [
    ConsumerControlCode.PLAY_PAUSE, # Center Foot Pad
    ConsumerControlCode.VOLUME_DECREMENT, #Left Foot Pad
    ConsumerControlCode.VOLUME_INCREMENT, # Right Foot Pad
]

# the keyboard object!
cc = ConsumerControl(usb_hid.devices)
# our array of button objects
buttons = []

# make all pin objects, make them inputs w/pullups
for pin in buttonpins:
    button = digitalio.DigitalInOut(pin)
    button.direction = digitalio.Direction.INPUT
    button.pull = digitalio.Pull.UP
    buttons.append(button)

print("Waiting for button presses")

while True:
    # check each button
    for button in buttons:
        if not button.value:  # pressed?
            i = buttons.index(button)

            print("Button #%d Pressed" % i)

            while not button.value:
                pass  # wait for it to be released!
            # type the keycode!
            k = buttonkeys[i]  # get the corresp. keycode
            cc.send(k)
    time.sleep(0.01)
