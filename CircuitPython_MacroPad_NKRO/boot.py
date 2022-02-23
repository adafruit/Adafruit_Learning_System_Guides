# SPDX-FileCopyrightText: 2021 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import usb_hid

REPORT_ID = 0x4
REPORT_BYTES = 16
bitmap_keyboard_descriptor = bytes((
        0x05, 0x01,                     # Usage Page (Generic Desktop),
        0x09, 0x06,                     # Usage (Keyboard),
        0xA1, 0x01,                     # Collection (Application),
        0x85, REPORT_ID,                #   Report ID
        # bitmap of modifiers
        0x75, 0x01,                     #   Report Size (1),
        0x95, 0x08,                     #   Report Count (8),
        0x05, 0x07,                     #   Usage Page (Key Codes),
        0x19, 0xE0,                     #   Usage Minimum (224),
        0x29, 0xE7,                     #   Usage Maximum (231),
        0x15, 0x00,                     #   Logical Minimum (0),
        0x25, 0x01,                     #   Logical Maximum (1),
        0x81, 0x02,                     #   Input (Data, Variable, Absolute), ;Modifier byte
        # LED output report
        0x95, 0x05,                     #   Report Count (5),
        0x75, 0x01,                     #   Report Size (1),
        0x05, 0x08,                     #   Usage Page (LEDs),
        0x19, 0x01,                     #   Usage Minimum (1),
        0x29, 0x05,                     #   Usage Maximum (5),
        0x91, 0x02,                     #   Output (Data, Variable, Absolute),
        0x95, 0x01,                     #   Report Count (1),
        0x75, 0x03,                     #   Report Size (3),
        0x91, 0x03,                     #   Output (Constant),
        # bitmap of keys
        0x95, (REPORT_BYTES-1)*8,       #   Report Count (),
        0x75, 0x01,                     #   Report Size (1),
        0x15, 0x00,                     #   Logical Minimum (0),
        0x25, 0x01,                     #   Logical Maximum(1),
        0x05, 0x07,                     #   Usage Page (Key Codes),
        0x19, 0x00,                     #   Usage Minimum (0),
        0x29, (REPORT_BYTES-1)*8-1,     #   Usage Maximum (),
        0x81, 0x02,                     #   Input (Data, Variable, Absolute),
        0xc0                            # End Collection
))

bitmap_keyboard = usb_hid.Device(
    report_descriptor=bitmap_keyboard_descriptor,
    usage_page=0x1,
    usage=0x6,
    report_ids=(REPORT_ID,),
    in_report_lengths=(REPORT_BYTES,),
    out_report_lengths=(1,),
)

usb_hid.enable(
    (
        bitmap_keyboard,
        usb_hid.Device.MOUSE,
        usb_hid.Device.CONSUMER_CONTROL,
    )
)
print("enabled HID with custom keyboard device")
