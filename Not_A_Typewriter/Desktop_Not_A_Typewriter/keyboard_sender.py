# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

#!/usr/bin/env python3
"""
USB Typewriter Computer-side Script
Captures keyboard input and sends it to the Feather via serial
"""

import struct
import time
import threading
import queue
import sys
import serial
import serial.tools.list_ports
from pynput import keyboard

class TypewriterSender:
    def __init__(self):
        self.serial_port = None
        self.key_queue = queue.Queue()
        self.running = True
        self.modifier_state = 0

        # Map pynput keys to HID keycodes
        self.key_to_hid = {
            # Letters
            'a': 0x04, 'b': 0x05, 'c': 0x06, 'd': 0x07,
            'e': 0x08, 'f': 0x09, 'g': 0x0A, 'h': 0x0B,
            'i': 0x0C, 'j': 0x0D, 'k': 0x0E, 'l': 0x0F,
            'm': 0x10, 'n': 0x11, 'o': 0x12, 'p': 0x13,
            'q': 0x14, 'r': 0x15, 's': 0x16, 't': 0x17,
            'u': 0x18, 'v': 0x19, 'w': 0x1A, 'x': 0x1B,
            'y': 0x1C, 'z': 0x1D,
            # Numbers
            '1': 0x1E, '2': 0x1F, '3': 0x20, '4': 0x21,
            '5': 0x22, '6': 0x23, '7': 0x24, '8': 0x25,
            '9': 0x26, '0': 0x27,
            # Special keys
            keyboard.Key.enter: 0x28,
            keyboard.Key.esc: 0x29,
            keyboard.Key.backspace: 0x2A,
            keyboard.Key.tab: 0x2B,
            keyboard.Key.space: 0x2C,
            '-': 0x2D, '=': 0x2E, '[': 0x2F, ']': 0x30,
            '\\': 0x31, ';': 0x33, "'": 0x34, '`': 0x35,
            ',': 0x36, '.': 0x37, '/': 0x38,
            keyboard.Key.caps_lock: 0x39,
            # Arrow keys
            keyboard.Key.right: 0x4F,
            keyboard.Key.left: 0x50,
            keyboard.Key.down: 0x51,
            keyboard.Key.up: 0x52,
        }

        # Add function keys
        for i in range(1, 13):
            self.key_to_hid[getattr(keyboard.Key, f'f{i}')] = 0x3A + i - 1

        # Modifier bits
        self.modifier_bits = {
            keyboard.Key.ctrl_l: 0x01,
            keyboard.Key.shift_l: 0x02,
            keyboard.Key.alt_l: 0x04,
            keyboard.Key.cmd_l: 0x08,  # Windows/Command key
            keyboard.Key.ctrl_r: 0x10,
            keyboard.Key.shift_r: 0x20,
            keyboard.Key.alt_r: 0x40,
            keyboard.Key.cmd_r: 0x80,
        }

    @staticmethod
    def find_feather_port():
        """Find the Feather's serial port"""
        ports = serial.tools.list_ports.comports()

        print("Available serial ports:")
        for i, port in enumerate(ports):
            print(f"{i}: {port.device} - {port.description}")
        feather_port = None

        if not feather_port:
            # Manual selection
            try:
                choice = int(input("\nSelect port number: "))
                if 0 <= choice < len(ports):
                    feather_port = ports[choice].device
                else:
                    print("Invalid selection")
                    return None
            except (ValueError, IndexError):
                print("Invalid input")
                return None

        return feather_port

    def connect(self):
        """Connect to the Feather via serial"""
        port = self.find_feather_port()
        if not port:
            return False

        try:
            self.serial_port = serial.Serial(port, 115200, timeout=0.1)
            time.sleep(2)  # Wait for connection to stabilize
            print(f"Connected to {port}")
            return True
        except Exception as e: # pylint: disable=broad-except
            print(f"Failed to connect: {e}")
            return False

    def send_key_event(self, hid_code, pressed):
        """Send a key event to the Feather"""
        if self.serial_port and self.serial_port.is_open:
            try:
                # Protocol: [0xAA][modifier_byte][key_code][pressed]
                # 0xAA is a start marker
                data = struct.pack('BBBB', 0xAA, self.modifier_state, hid_code, 1 if pressed else 0)
                self.serial_port.write(data)
                self.serial_port.flush()
            except Exception as e: # pylint: disable=broad-except
                print(f"Error sending data: {e}")

    def on_press(self, key):
        """Handle key press events"""
        # Check for modifier keys
        if key in self.modifier_bits:
            self.modifier_state |= self.modifier_bits[key]
            self.send_key_event(0, True)  # Send modifier update
            return

        # Get HID code for the key
        hid_code = None

        # Check if it's a special key
        if hasattr(key, 'value') and key in self.key_to_hid:
            hid_code = self.key_to_hid[key]
        # Check if it's a regular character
        elif hasattr(key, 'char') and key.char:
            hid_code = self.key_to_hid.get(key.char.lower())

        if hid_code:
            self.key_queue.put((hid_code, True))

    def on_release(self, key):
        """Handle key release events"""
        # Check for modifier keys
        if key in self.modifier_bits:
            self.modifier_state &= ~self.modifier_bits[key]
            self.send_key_event(0, False)  # Send modifier update
            return None

        # Get HID code for the key
        hid_code = None

        # Check if it's a special key
        if hasattr(key, 'value') and key in self.key_to_hid:
            hid_code = self.key_to_hid[key]
        # Check if it's a regular character
        elif hasattr(key, 'char') and key.char:
            hid_code = self.key_to_hid.get(key.char.lower())

        if hid_code:
            self.key_queue.put((hid_code, False))

        # Check for escape to quit
        if key == keyboard.Key.esc:
            print("\nESC pressed - exiting...")
            self.running = False
            return False

        return None

    def process_queue(self):
        """Process queued key events"""
        while self.running:
            try:
                hid_code, pressed = self.key_queue.get(timeout=0.1)
                self.send_key_event(hid_code, pressed)

                # Debug output
                action = "pressed" if pressed else "released"
                print(f"Key {action}: 0x{hid_code:02X}")

            except queue.Empty:
                continue

    def run(self):
        """Main run loop"""
        if not self.connect():
            print("Failed to connect to Feather")
            return

        print("\nNot A Typewriter")
        print("Press keys to send to typewriter")
        print("Press ESC to exit")
        print("-" * 30)

        # Start queue processor thread
        queue_thread = threading.Thread(target=self.process_queue)
        queue_thread.daemon = True
        queue_thread.start()

        # Start keyboard listener
        with keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release) as listener:
            listener.join()

        # Cleanup
        if self.serial_port:
            self.serial_port.close()
        print("Disconnected")

if __name__ == "__main__":
    try:
        sender = TypewriterSender()
        sender.run()
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(0)
