# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import sys
import serial
import keyboard

port = '/dev/ttyUSB0'  # Replace with your actual serial port

# Define a mapping for special characters when shift is pressed
SHIFTED_KEYS = {
    '1': '!', '2': '@', '3': '#', '4': '$', '5': '%',
    '6': '^', '7': '&', '8': '*', '9': '(', '0': ')',
    '`': '~', '-': '_', '=': '+', '[': '{', ']': '}',
    '\\': '|', ';': ':', "'": '"', ',': '<', '.': '>',
    '/': '?'
}

def send_key(serial_port, key):
    """
    Send a key press to the CH9328 via UART.

    Parameters:
    serial_port (serial.Serial): The serial port connection.
    key (str): The key to send.
    """
    serial_port.write(key.encode('ascii'))
    serial_port.flush()

def send_empty_report(serial_port):
    """
    Send an empty HID report to reset the state of the device.

    Parameters:
    serial_port (serial.Serial): The serial port connection.
    """
    try:
        empty_report = bytearray([0] * 8)
        serial_port.write(empty_report)
        serial_port.flush()
    except serial.SerialException as e:
        print(f"Failed to send empty report: {e}")

def main():
    # Configure the serial connection
    baudrate = 9600  # Default baud rate for CH9328 in Mode 1
    timeout = 1

    with serial.Serial(port, baudrate, timeout=timeout) as ser:

        print("Listening for keyboard inputs. Press 'ESC' to exit.")

        def on_key_event(event):
            if event.event_type == 'down':
                key = event.name
                if len(key) == 1:  # Only process single character keys
                    if keyboard.is_pressed('shift'):  # Check if shift is pressed
                        key = SHIFTED_KEYS.get(key, key.upper())
                    send_key(ser, key)
                elif key == 'space':
                    send_key(ser, ' ')
                elif key == 'enter':
                    send_key(ser, '\n')
            send_empty_report(ser)

        # Hook the keyboard event
        keyboard.hook(on_key_event)

        # Wait for ESC to exit
        keyboard.wait('esc')

if __name__ == "__main__":
    main()
    sys.exit()
