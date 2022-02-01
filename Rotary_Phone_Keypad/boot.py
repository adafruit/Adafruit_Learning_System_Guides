# SPDX-FileCopyrightText: 2022 Tod Kurt & John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# boot.py to enable or disable usb_hid
import usb_hid
import board
import digitalio

# set a pull-up
# If not pressed, the key will be at +V (due to the pull-up)
button = digitalio.DigitalInOut(board.D2)
button.pull = digitalio.Pull.UP

# Disable devices only if button is not pressed
# Phone receiver is normally open when handset is in place
if button.value:
    print("USB HID disabled")
    usb_hid.disable()
