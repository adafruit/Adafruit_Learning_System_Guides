# SPDX-FileCopyrightText: 2023 Robert Dale Smith for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

import usb_hid

# This is only one example of a gamepad descriptor, and may not suit your needs.
GAMEPAD_REPORT_DESCRIPTOR = bytes((
    0x05, 0x01,        # USAGE_PAGE (Generic Desktop)
	0x09, 0x05,        # USAGE (Gamepad)
	0xa1, 0x01,        # COLLECTION (Application)
	0x15, 0x00,        #   LOGICAL_MINIMUM (0)
	0x25, 0x01,        #   LOGICAL_MAXIMUM (1)
	0x35, 0x00,        #   PHYSICAL_MINIMUM (0)
	0x45, 0x01,        #   PHYSICAL_MAXIMUM (1)
	0x75, 0x01,        #   REPORT_SIZE (1)
	0x95, 0x0e,        #   REPORT_COUNT (14)
	0x05, 0x09,        #   USAGE_PAGE (Button)
	0x19, 0x01,        #   USAGE_MINIMUM (Button 1)
	0x29, 0x0e,        #   USAGE_MAXIMUM (Button 14)
	0x81, 0x02,        #   INPUT (Data,Var,Abs)
	0x95, 0x02,        #   REPORT_COUNT (3)
	0x81, 0x01,        #   INPUT (Cnst,Ary,Abs)
	0x05, 0x01,        #   USAGE_PAGE (Generic Desktop)
	0x25, 0x07,        #   LOGICAL_MAXIMUM (7)
	0x46, 0x3b, 0x01,  #   PHYSICAL_MAXIMUM (315)
	0x75, 0x04,        #   REPORT_SIZE (4)
	0x95, 0x01,        #   REPORT_COUNT (1)
	0x65, 0x14,        #   UNIT (Eng Rot:Angular Pos)
	0x09, 0x39,        #   USAGE (Hat switch)
	0x81, 0x42,        #   INPUT (Data,Var,Abs,Null)
	0x65, 0x00,        #   UNIT (None)
	0x95, 0x01,        #   REPORT_COUNT (1)
	0x81, 0x01,        #   INPUT (Cnst,Ary,Abs)
	0x26, 0xff, 0x00,  #   LOGICAL_MAXIMUM (255)
	0x46, 0xff, 0x00,  #   PHYSICAL_MAXIMUM (255)
	0x09, 0x30,        #   USAGE (X)
	0x09, 0x31,        #   USAGE (Y)
	0x09, 0x32,        #   USAGE (Z)
	0x09, 0x35,        #   USAGE (Rz)
	0x75, 0x08,        #   REPORT_SIZE (8)
	0x95, 0x04,        #   REPORT_COUNT (6)
	0x81, 0x02,        #   INPUT (Data,Var,Abs)
	0x06, 0x00, 0xff,  #   USAGE_PAGE (Vendor Specific)
	0x09, 0x20,        #   Unknown
	0x09, 0x21,        #   Unknown
	0x09, 0x22,        #   Unknown
	0x09, 0x23,        #   Unknown
	0x09, 0x24,        #   Unknown
	0x09, 0x25,        #   Unknown
	0x09, 0x26,        #   Unknown
	0x09, 0x27,        #   Unknown
	0x09, 0x28,        #   Unknown
	0x09, 0x29,        #   Unknown
	0x09, 0x2a,        #   Unknown
	0x09, 0x2b,        #   Unknown
	0x95, 0x0c,        #   REPORT_COUNT (12)
	0x81, 0x02,        #   INPUT (Data,Var,Abs)
	0x0a, 0x21, 0x26,  #   Unknown
	0x95, 0x08,        #   REPORT_COUNT (8)
	0xb1, 0x02,        #   FEATURE (Data,Var,Abs)
	0xc0               # END_COLLECTION
))

gamepad = usb_hid.Device(
    report_descriptor=GAMEPAD_REPORT_DESCRIPTOR,
    usage_page=0x01,           # Generic Desktop Control
    usage=0x05,                # Gamepad
    report_ids=(0,),           # Descriptor uses report ID 0.
    in_report_lengths=(19,),    # This gamepad sends 6 bytes in its report.
    out_report_lengths=(0,),   # It does not receive any reports.
)

usb_hid.enable((gamepad,))
