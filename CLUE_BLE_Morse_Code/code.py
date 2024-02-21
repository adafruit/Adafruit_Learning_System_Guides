# SPDX-FileCopyrightText: 2020 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import displayio
import terminalio
from adafruit_clue import clue
from adafruit_display_text import label
import adafruit_imageload
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

#--| User Config |---------------------------------------------------
MY_NAME = "CENTRAL"
FRIENDS_NAME = "PERIPHERAL"
#--| User Config |---------------------------------------------------

WAIT_FOR_DOUBLE = 0.05
DEBOUNCE = 0.25

# Define Morse Code dictionary
morse_code = {
    ".-"   : "A", "-..." : "B", "-.-." : "C", "-.."  : "D", "."    : "E",
    "..-." : "F", "--."  : "G", "...." : "H", ".."   : "I", ".---" : "J",
    "-.-"  : "K", ".-.." : "L", "--"   : "M", "-."   : "N", "---"  : "O",
    ".--." : "P", "--.-" : "Q", ".-."  : "R", "..."  : "S", "-"    : "T",
    "..-"  : "U", "...-" : "V", ".--"  : "W", "-..-" : "X", "-.--" : "Y",
    "--.." : "Z",
}

# BLE Radio Stuff
ble = BLERadio()
uart_service = UARTService()
advertisement = ProvideServicesAdvertisement(uart_service)
ble._adapter.name = MY_NAME #pylint: disable=protected-access

# Display Stuff
display = clue.display
disp_group = displayio.Group()
display.show(disp_group)

# Background BMP with the Morse Code cheat sheet
bmp, pal = adafruit_imageload.load("morse_bg.bmp",
                                   bitmap=displayio.Bitmap,
                                   palette=displayio.Palette)
disp_group.append(displayio.TileGrid(bmp, pixel_shader=pal))

# Incoming messages show up here
in_label = label.Label(terminalio.FONT, text='A'*18, scale=2,
                       color=0x000000)
in_label.anchor_point = (0.5, 0)
in_label.anchored_position = (65, 12)
disp_group.append(in_label)

# Outging messages show up here
out_label = label.Label(terminalio.FONT, text='B'*18, scale=2,
                        color=0x000000)
out_label.anchor_point = (0.5, 0)
out_label.anchored_position = (65, 190)
disp_group.append(out_label)

# Morse Code entry happens here
edit_label = label.Label(terminalio.FONT, text='....', scale=2,
                         color=0x000000)
edit_label.anchor_point = (0.5, 0)
edit_label.anchored_position = (105, 222)
disp_group.append(edit_label)

def scan_and_connect():
    '''
    Advertise self while scanning for friend. If friend is found, can
    connect by pressing A+B buttons. If friend connects first, then
    just stop.
    '''

# peripheral
    if MY_NAME == "PERIPHERAL":
        print("Advertising.")
        central = False
        ble.start_advertising(advertisement)

        while not ble.connected:
            if ble.connected:
                break

        # We're now connected, one way or the other
        print("Stopping advertising.")
        ble.stop_advertising()

        print("Peripheral - connecting to their UART service.")
        for connection in ble.connections:
            if UARTService not in connection:
                continue
            return connection[UARTService]

  # central
    else:
        print("Waiting.")
        friend = None
        while not ble.connected:
            if friend is None:
                print("Scanning.")
                in_label.text = out_label.text = "Scanning..."
                for adv in ble.start_scan():
                    if ble.connected:
                        # Friend connected with us, we're done
                        ble.stop_scan()
                        break
                    if adv.complete_name == FRIENDS_NAME:
                        # Found friend, can stop scanning
                        ble.stop_scan()
                        friend = adv
                        print("Found", friend.complete_name)
                        in_label.text = "Found {}".format(friend.complete_name)
                        out_label.text = "A+B to connect"
                        break
            else:
                if clue.button_a and clue.button_b:
                    # Connect to friend
                    print("Connecting to", friend.complete_name)
                    ble.connect(friend)
                    central = True
    

    # Return a UART object to use
    print("Central - using my UART service.")
    return uart_service

#--------------------------
# The main application loop
#--------------------------
while True:

    # Establish initial connection
    uart = scan_and_connect()

    print("Connected.")

    code = ''
    in_label.text = out_label.text = ' '*18
    edit_label.text = ' '*4
    done = False

    # Run the chat while connected
    while ble.connected:

        # Check for incoming message
        incoming_bytes = uart.in_waiting
        if incoming_bytes:
            bytes_in = uart.read(incoming_bytes)
            print("Received: ", bytes_in)
            in_label.text = in_label.text[incoming_bytes:] + bytes_in.decode()

        # DOT (or done)
        if clue.button_a:
            start = time.monotonic()
            while time.monotonic() - start < WAIT_FOR_DOUBLE:
                if clue.button_b:
                    done = True
            if not done and len(code) < 4:
                print('.', end='')
                code += '.'
                edit_label.text = "{:4s}".format(code)
                time.sleep(DEBOUNCE)

        # DASH (or done)
        if clue.button_b:
            start = time.monotonic()
            while time.monotonic() - start < WAIT_FOR_DOUBLE:
                if clue.button_a:
                    done = True
            if not done and len(code) < 4:
                print('-', end='')
                code += '-'
                edit_label.text = "{:4s}".format(code)
                time.sleep(DEBOUNCE)

        # Turn Morse Code into letter and send
        if done:
            letter = morse_code.get(code, ' ')
            print(' >', letter)
            out_label.text = out_label.text[1:] + letter
            uart.write(str.encode(letter))
            code = ''
            edit_label.text = ' '*4
            done = False
            time.sleep(DEBOUNCE)

    print("Disconnected.")
