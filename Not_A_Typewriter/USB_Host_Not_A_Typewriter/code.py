# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import array
import time
import board
from adafruit_mcp230xx.mcp23017 import MCP23017

import usb
import adafruit_usb_host_descriptors
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# Typewriter configuration
KEYSTROKE_BELL_INTERVAL = 25  # Ring bell every 25 keystrokes
SOLENOID_STRIKE_TIME = 0.03   # Duration in seconds for solenoid activation (reduced)
SOLENOID_DELAY = 0.01         # Small delay between solenoid operations (reduced)
ENTER_KEY_CODE = 0x28         # HID code for Enter key
ESCAPE_KEY_CODE = 0x29        # HID code for Escape key
BACKSPACE_KEY_CODE = 0x2A     # HID code for Backspace key
TAB_KEY_CODE = 0x2B           # HID code for Tab key
bell_keys = {ENTER_KEY_CODE, ESCAPE_KEY_CODE, TAB_KEY_CODE}

# Set up USB HID keyboard
hid_keyboard = Keyboard(usb_hid.devices)

# HID to Keycode mapping dictionary
hid_to_keycode = {
    0x04: Keycode.A,
    0x05: Keycode.B,
    0x06: Keycode.C,
    0x07: Keycode.D,
    0x08: Keycode.E,
    0x09: Keycode.F,
    0x0A: Keycode.G,
    0x0B: Keycode.H,
    0x0C: Keycode.I,
    0x0D: Keycode.J,
    0x0E: Keycode.K,
    0x0F: Keycode.L,
    0x10: Keycode.M,
    0x11: Keycode.N,
    0x12: Keycode.O,
    0x13: Keycode.P,
    0x14: Keycode.Q,
    0x15: Keycode.R,
    0x16: Keycode.S,
    0x17: Keycode.T,
    0x18: Keycode.U,
    0x19: Keycode.V,
    0x1A: Keycode.W,
    0x1B: Keycode.X,
    0x1C: Keycode.Y,
    0x1D: Keycode.Z,
    0x1E: Keycode.ONE,
    0x1F: Keycode.TWO,
    0x20: Keycode.THREE,
    0x21: Keycode.FOUR,
    0x22: Keycode.FIVE,
    0x23: Keycode.SIX,
    0x24: Keycode.SEVEN,
    0x25: Keycode.EIGHT,
    0x26: Keycode.NINE,
    0x27: Keycode.ZERO,
    0x28: Keycode.ENTER,
    0x29: Keycode.ESCAPE,
    0x2A: Keycode.BACKSPACE,
    0x2B: Keycode.TAB,
    0x2C: Keycode.SPACE,
    0x2D: Keycode.MINUS,
    0x2E: Keycode.EQUALS,
    0x2F: Keycode.LEFT_BRACKET,
    0x30: Keycode.RIGHT_BRACKET,
    0x31: Keycode.BACKSLASH,
    0x33: Keycode.SEMICOLON,
    0x34: Keycode.QUOTE,
    0x35: Keycode.GRAVE_ACCENT,
    0x36: Keycode.COMMA,
    0x37: Keycode.PERIOD,
    0x38: Keycode.FORWARD_SLASH,
    0x39: Keycode.CAPS_LOCK,
    0x3A: Keycode.F1,
    0x3B: Keycode.F2,
    0x3C: Keycode.F3,
    0x3D: Keycode.F4,
    0x3E: Keycode.F5,
    0x3F: Keycode.F6,
    0x40: Keycode.F7,
    0x41: Keycode.F8,
    0x42: Keycode.F9,
    0x43: Keycode.F10,
    0x44: Keycode.F11,
    0x45: Keycode.F12,
    0x4F: Keycode.RIGHT_ARROW,
    0x50: Keycode.LEFT_ARROW,
    0x51: Keycode.DOWN_ARROW,
    0x52: Keycode.UP_ARROW,
}

# Modifier mapping
modifier_to_keycode = {
    0x01: Keycode.LEFT_CONTROL,
    0x02: Keycode.LEFT_SHIFT,
    0x04: Keycode.LEFT_ALT,
    0x08: Keycode.LEFT_GUI,
    0x10: Keycode.RIGHT_CONTROL,
    0x20: Keycode.RIGHT_SHIFT,
    0x40: Keycode.RIGHT_ALT,
    0x80: Keycode.RIGHT_GUI,
}

#interface index, and endpoint addresses for USB Device instance
kbd_interface_index = None
kbd_endpoint_address = None
keyboard = None

i2c = board.STEMMA_I2C()

mcp = MCP23017(i2c)

noid_2 = mcp.get_pin(0)  # Key strike solenoid
noid_1 = mcp.get_pin(1)  # Bell solenoid
noid_1.switch_to_output(value=False)
noid_2.switch_to_output(value=False)

# Typewriter state tracking
keystroke_count = 0
previous_keys = set()  # Track previously pressed keys to detect new presses
previous_modifiers = 0  # Track modifier state

#interface index, and endpoint addresses for USB Device instance
kbd_interface_index = None
kbd_endpoint_address = None
keyboard = None

# scan for connected USB devices
for device in usb.core.find(find_all=True):
    # check for boot keyboard endpoints on this device
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

def strike_key_solenoid():
    """Activate the key strike solenoid briefly"""
    noid_1.value = True
    time.sleep(SOLENOID_STRIKE_TIME)
    noid_1.value = False

def ring_bell_solenoid():
    """Activate the bell solenoid briefly"""
    noid_2.value = True
    time.sleep(SOLENOID_STRIKE_TIME)
    noid_2.value = False

def get_pressed_keys(report_data):
    """Extract currently pressed keys from HID report"""
    pressed_keys = set()

    # Check bytes 2-7 for key codes (up to 6 simultaneous keys)
    for i in range(2, 8):
        k = report_data[i]
        # Skip if no key (0) or error rollover (1)
        if k > 1:
            pressed_keys.add(k)

    return pressed_keys

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
        for b, name in modifier_dict.items():
            if modifiers & b:
                print(name, end=" ")

        print()

    # Bytes 2-7 contain up to 6 key codes (byte 1 is reserved)
    keys_pressed = False

    for i in range(2, 8):
        k = report_data[i]

        # Skip if no key or error rollover
        if k in {0, 1}:
            continue

        if not keys_pressed:
            print("Keys:", end=" ")
            keys_pressed = True

        # Print key name based on dictionary lookup
        if k in key_dict:
            print(key_dict[k], end=" ")
        else:
            # For keys not in the dictionary, print the HID code
            print(f"0x{k:02X}", end=" ")

    if keys_pressed:
        print()
    elif modifiers == 0:
        print("No keys pressed")


print("USB Typewriter starting...")
print(f"Bell will ring every {KEYSTROKE_BELL_INTERVAL} keystrokes or when Enter is pressed")

while True:
    # try to read data from the keyboard
    try:
        count = keyboard.read(kbd_endpoint_address, buf, timeout=10)

    # if there is no data it will raise USBTimeoutError
    except usb.core.USBTimeoutError:
        # Nothing to do if there is no data for this keyboard
        continue

    # Get currently pressed keys and modifiers
    current_keys = get_pressed_keys(buf)
    current_modifiers = buf[0]

    # Find newly pressed keys (not in previous scan)
    new_keys = current_keys - previous_keys

    # Find released keys for HID pass-through
    released_keys = previous_keys - current_keys

    # Handle modifier changes
    if current_modifiers != previous_modifiers:
        # Build list of modifier keycodes to press/release
        for bit, keycode in modifier_to_keycode.items():
            if current_modifiers & bit and not previous_modifiers & bit:
                # Modifier newly pressed
                hid_keyboard.press(keycode)
            elif not (current_modifiers & bit) and (previous_modifiers & bit):
                # Modifier released
                hid_keyboard.release(keycode)

    # Release any keys that were let go
    for key in released_keys:
        if key in hid_to_keycode:
            hid_keyboard.release(hid_to_keycode[key])

    # Process each newly pressed key
    for key in new_keys:
        # Increment keystroke counter
        keystroke_count += 1
        # Strike the key solenoid for typewriter effect
        strike_key_solenoid()
        # Pass through the key press via USB HID
        if key in hid_to_keycode:
            hid_keyboard.press(hid_to_keycode[key])

        # Check if special keys were pressed
        if key == ENTER_KEY_CODE:
            ring_bell_solenoid()
            keystroke_count = 0  # Reset counter for new line
        elif key == ESCAPE_KEY_CODE:
            ring_bell_solenoid()
            keystroke_count = 0  # Reset counter
        elif key == TAB_KEY_CODE:
            ring_bell_solenoid()
            keystroke_count = 0  # Reset counter
        elif key == BACKSPACE_KEY_CODE:
            keystroke_count = 0  # Reset counter but no bell
        elif keystroke_count % KEYSTROKE_BELL_INTERVAL == 0:
            print(f"\n*** DING! ({keystroke_count} keystrokes) ***\n")
            ring_bell_solenoid()
    # Special handling for bell keys that are still held
    # check if they were released and re-pressed
    # This handles rapid double-taps where the key might not fully release

    for key in bell_keys:
        if key in current_keys and key in previous_keys and key not in new_keys:
            # Key is being held, check if it was briefly released by looking at the raw state
            # For held keys, we'll check if this is a repeat event
            if len(current_keys) != len(previous_keys) or current_keys != previous_keys:
                # Something changed, might be a repeat
                continue

    # Update previous keys and modifiers for next scan
    previous_keys = current_keys
    previous_modifiers = current_modifiers

    # Still print the keyboard report for debugging
    if new_keys:  # Only print if there are new key presses
        print_keyboard_report(buf)
        print(f"Total keystrokes: {keystroke_count}")
