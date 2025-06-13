# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
USB Typewriter Feather-side Script
Converts incoming keystrokes to solenoid clicks
"""

import time
import struct
import usb_cdc
import board
from adafruit_mcp230xx.mcp23017 import MCP23017

# Typewriter configuration
KEYSTROKE_BELL_INTERVAL = 25  # Ring bell every 25 keystrokes
SOLENOID_STRIKE_TIME = 0.03   # Duration in seconds for solenoid activation
ENTER_KEY_CODE = 0x28         # HID code for Enter key
ESCAPE_KEY_CODE = 0x29        # HID code for Escape key
BACKSPACE_KEY_CODE = 0x2A     # HID code for Backspace key
TAB_KEY_CODE = 0x2B           # HID code for Tab key

# Key name mapping for debug output
key_names = {
    0x04: "A", 0x05: "B", 0x06: "C", 0x07: "D",
    0x08: "E", 0x09: "F", 0x0A: "G", 0x0B: "H",
    0x0C: "I", 0x0D: "J", 0x0E: "K", 0x0F: "L",
    0x10: "M", 0x11: "N", 0x12: "O", 0x13: "P",
    0x14: "Q", 0x15: "R", 0x16: "S", 0x17: "T",
    0x18: "U", 0x19: "V", 0x1A: "W", 0x1B: "X",
    0x1C: "Y", 0x1D: "Z",
    0x1E: "1", 0x1F: "2", 0x20: "3", 0x21: "4",
    0x22: "5", 0x23: "6", 0x24: "7", 0x25: "8",
    0x26: "9", 0x27: "0",
    0x28: "ENTER", 0x29: "ESC", 0x2A: "BACKSPACE",
    0x2B: "TAB", 0x2C: "SPACE", 0x2D: "MINUS",
    0x2E: "EQUAL", 0x2F: "LBRACKET", 0x30: "RBRACKET",
    0x31: "BACKSLASH", 0x33: "SEMICOLON", 0x34: "QUOTE",
    0x35: "GRAVE", 0x36: "COMMA", 0x37: "PERIOD",
    0x38: "SLASH", 0x39: "CAPS_LOCK",
    0x4F: "RIGHT", 0x50: "LEFT", 0x51: "DOWN", 0x52: "UP",
}

# Add F1-F12 keys
for i in range(12):
    key_names[0x3A + i] = f"F{i + 1}"

# Set up I2C and MCP23017
i2c = board.STEMMA_I2C()
mcp = MCP23017(i2c)

# Configure solenoid pins
noid_1 = mcp.get_pin(0)  # Bell solenoid
noid_2 = mcp.get_pin(1)  # Key strike solenoid
noid_1.switch_to_output(value=False)
noid_2.switch_to_output(value=False)

# Typewriter state tracking
keystroke_count = 0
current_keys = set()  # Track currently pressed keys

# Check if USB CDC data is available
if usb_cdc.data is None:
    print("ERROR: USB CDC data not enabled!")
    print("Please create a boot.py file with:")
    print("  import usb_cdc")
    print("  usb_cdc.enable(console=True, data=True)")
    print("\nThen reset the board.")
    while True:
        time.sleep(1)

serial = usb_cdc.data

def strike_key_solenoid():
    """Activate the key strike solenoid briefly"""
    noid_2.value = True
    time.sleep(SOLENOID_STRIKE_TIME)
    noid_2.value = False

def ring_bell_solenoid():
    """Activate the bell solenoid briefly"""
    noid_1.value = True
    time.sleep(SOLENOID_STRIKE_TIME)
    noid_1.value = False

def process_key_event(mod, code, p): # pylint: disable=too-many-branches
    """Process a key event from the computer"""
    global keystroke_count # pylint: disable=global-statement

    # Debug output
    key_name = key_names.get(code, f"0x{code:02X}")
    action = "pressed" if p else "released"

    # Handle modifier display
    if mod > 0:
        mod_str = []
        if mod & 0x01:
            mod_str.append("L_CTRL")
        if mod & 0x02:
            mod_str.append("L_SHIFT")
        if mod & 0x04:
            mod_str.append("L_ALT")
        if mod & 0x08:
            mod_str.append("L_GUI")
        if mod & 0x10:
            mod_str.append("R_CTRL")
        if mod & 0x20:
            mod_str.append("R_SHIFT")
        if mod & 0x40:
            mod_str.append("R_ALT")
        if mod & 0x80:
            mod_str.append("R_GUI")
        print(f"[{'+'.join(mod_str)}] {key_name} {action}")
    else:
        print(f"{key_name} {action}")

    # Only process key presses (not releases) for solenoid activation
    if p and code > 0:  # key_code 0 means modifier-only update
        # Check if this is a new key press
        if code not in current_keys:
            current_keys.add(code)

            # Increment keystroke counter
            keystroke_count += 1

            # Strike the key solenoid
            strike_key_solenoid()

            # Check for special keys
            if code == ENTER_KEY_CODE:
                ring_bell_solenoid()
                keystroke_count = 0  # Reset counter for new line
            elif code == ESCAPE_KEY_CODE:
                ring_bell_solenoid()
                keystroke_count = 0  # Reset counter
            elif code == TAB_KEY_CODE:
                ring_bell_solenoid()
                keystroke_count = 0  # Reset counter
            elif code == BACKSPACE_KEY_CODE:
                keystroke_count = 0  # Reset counter but no bell
            elif keystroke_count % KEYSTROKE_BELL_INTERVAL == 0:
                print(f"\n*** DING! ({keystroke_count} keystrokes) ***\n")
                ring_bell_solenoid()

            print(f"Total keystrokes: {keystroke_count}")

    elif not p and code > 0:
        # Remove key from pressed set when released
        current_keys.discard(code)

print("USB Typewriter Receiver starting...")
print(f"Bell will ring every {KEYSTROKE_BELL_INTERVAL} keystrokes or on special keys")
print("Waiting for key events from computer...")
print("-" * 40)

# Buffer for incoming data
buffer = bytearray(4)
buffer_pos = 0

while True:
    # Check for incoming serial data
    if serial.in_waiting > 0:
        # Read available bytes
        data = serial.read(serial.in_waiting)

        for byte in data:
            # Look for start marker
            if buffer_pos == 0:
                if byte == 0xAA:
                    buffer[0] = byte
                    buffer_pos = 1
            else:
                # Fill buffer
                buffer[buffer_pos] = byte
                buffer_pos += 1

                # Process complete message
                if buffer_pos >= 4:
                    # Unpack the message
                    _, modifier, key_code, pressed = struct.unpack('BBBB', buffer)

                    # Process the key event
                    process_key_event(modifier, key_code, pressed)

                    # Reset buffer
                    buffer_pos = 0

    # Small delay to prevent busy-waiting
    time.sleep(0.001)
