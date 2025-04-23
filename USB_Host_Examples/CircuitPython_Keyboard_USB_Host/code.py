# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import array

import usb
import adafruit_usb_host_descriptors

# lists for mouse interface indexes, endpoint addresses, and USB Device instances
# each of these will end up with length 2 once we find both mice
kbd_interface_index = None
kbd_endpoint_address = None
keyboard = None

# scan for connected USB devices
for device in usb.core.find(find_all=True):
    # check for boot mouse endpoints on this device
    kbd_interface_index, kbd_endpoint_address = (
        adafruit_usb_host_descriptors.find_boot_keyboard_endpoint(device)
    )
    # if a boot keyboard interface index and endpoint address were found
    if kbd_interface_index is not None and kbd_interface_index is not None:
        keyboard = device

        # detach device from kernel if needed
        if keyboard.is_kernel_driver_active(0):
            keyboard.detach_kernel_driver(0)

        # set the configuration so it can be used
        keyboard.set_configuration()

if keyboard is None:
    raise RuntimeError("No boot keyboard endpoint found")

buf = array.array("b", [0] * 8)


def print_keyboard_report(report_data):
    # Dictionary for modifier keys (first byte)
    modifier_dict = {
        0x01: "LEFT_CTRL",
        0x02: "LEFT_SHIFT",
        0x04: "LEFT_ALT",
        0x08: "LEFT_GUI",
        0x10: "RIGHT_CTRL",
        0x20: "RIGHT_SHIFT",
        0x40: "RIGHT_ALT",
        0x80: "RIGHT_GUI",
    }

    # Dictionary for key codes (main keys)
    key_dict = {
        0x04: "A",
        0x05: "B",
        0x06: "C",
        0x07: "D",
        0x08: "E",
        0x09: "F",
        0x0A: "G",
        0x0B: "H",
        0x0C: "I",
        0x0D: "J",
        0x0E: "K",
        0x0F: "L",
        0x10: "M",
        0x11: "N",
        0x12: "O",
        0x13: "P",
        0x14: "Q",
        0x15: "R",
        0x16: "S",
        0x17: "T",
        0x18: "U",
        0x19: "V",
        0x1A: "W",
        0x1B: "X",
        0x1C: "Y",
        0x1D: "Z",
        0x1E: "1",
        0x1F: "2",
        0x20: "3",
        0x21: "4",
        0x22: "5",
        0x23: "6",
        0x24: "7",
        0x25: "8",
        0x26: "9",
        0x27: "0",
        0x28: "ENTER",
        0x29: "ESC",
        0x2A: "BACKSPACE",
        0x2B: "TAB",
        0x2C: "SPACE",
        0x2D: "MINUS",
        0x2E: "EQUAL",
        0x2F: "LBRACKET",
        0x30: "RBRACKET",
        0x31: "BACKSLASH",
        0x33: "SEMICOLON",
        0x34: "QUOTE",
        0x35: "GRAVE",
        0x36: "COMMA",
        0x37: "PERIOD",
        0x38: "SLASH",
        0x39: "CAPS_LOCK",
        0x4F: "RIGHT_ARROW",
        0x50: "LEFT_ARROW",
        0x51: "DOWN_ARROW",
        0x52: "UP_ARROW",
    }

    # Add F1-F12 keys to the dictionary
    for i in range(12):
        key_dict[0x3A + i] = f"F{i + 1}"

    # First byte contains modifier keys
    modifiers = report_data[0]

    # Print modifier keys if pressed
    if modifiers > 0:
        print("Modifiers:", end=" ")

        # Check each bit for modifiers and print if pressed
        for bit, name in modifier_dict.items():
            if modifiers & bit:
                print(name, end=" ")

        print()

    # Bytes 2-7 contain up to 6 key codes (byte 1 is reserved)
    keys_pressed = False

    for i in range(2, 8):
        key = report_data[i]

        # Skip if no key or error rollover
        if key in {0, 1}:
            continue

        if not keys_pressed:
            print("Keys:", end=" ")
            keys_pressed = True

        # Print key name based on dictionary lookup
        if key in key_dict:
            print(key_dict[key], end=" ")
        else:
            # For keys not in the dictionary, print the HID code
            print(f"0x{key:02X}", end=" ")

    if keys_pressed:
        print()
    elif modifiers == 0:
        print("No keys pressed")


while True:
    # try to read data from the keyboard
    try:
        count = keyboard.read(kbd_endpoint_address, buf, timeout=10)

    # if there is no data it will raise USBTimeoutError
    except usb.core.USBTimeoutError:
        # Nothing to do if there is no data for this mouse
        continue

    print_keyboard_report(buf)
