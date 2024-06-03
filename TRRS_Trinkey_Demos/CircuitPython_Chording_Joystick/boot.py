# SPDX-FileCopyrightText: 2024 Bill Binko
# SPDX-License-Identifier: MIT

import usb_midi
import usb_hid

print("In boot.py")

# storage.disable_usb_device()

# usb_cdc.enable(console=True, data=True)

usb_midi.disable()
xac_descriptor=bytes(
            # This descriptor mimics the simple joystick from PDP that the XBox likes
            (
                0x05,
                0x01,  #  Usage Page (Desktop),
                0x09,
                0x05,  #  Usage (Gamepad),
                0xA1,
                0x01,  #  Collection (Application),
            )
            + ((0x85, 0x04) ) #report id
            + (
                0x15,
                0x00,  #      Logical Minimum (0),
                0x25,
                0x01,  #      Logical Maximum (1),
                0x35,
                0x00,  #      Physical Minimum (0),
                0x45,
                0x01,  #      Physical Maximum (1),
                0x75,
                0x01,  #      Report Size (1),
                0x95,
                0x08,  #      Report Count (8),
                0x05,
                0x09,  #      Usage Page (Button),
                0x19,
                0x01,  #      Usage Minimum (01h),
                0x29,
                0x08,  #      Usage Maximum (08h),
                0x81,
                0x02,  #      Input (Variable),
                0x05,
                0x01,  #      Usage Page (Desktop),
                0x26,
                0xFF,
                0x00,  #      Logical Maximum (255),
                0x46,
                0xFF,
                0x00,  #      Physical Maximum (255),
                0x09,
                0x30,  #      Usage (X),
                0x09,
                0x31,  #      Usage (Y),
                0x75,
                0x08,  #      Report Size (8),
                0x95,
                0x02,  #      Report Count (2),
                0x81,
                0x02,  #      Input (Variable),
                0xC0,  #  End Collection
            ))
# pylint: disable=missing-kwoa
my_gamepad = usb_hid.Device(
    report_descriptor=xac_descriptor,
    usage_page=1,
    usage=5,
    report_ids=(4,),
    in_report_lengths=(3,),
    out_report_lengths=(0,),)
print("Enabling XAC Gamepad")
usb_hid.enable((my_gamepad,))
