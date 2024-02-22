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

# --| User Config |---------------------------------------------------
# Set to either A or B. The other CLUE should be set to opposite mode.
BLE_MODE = "A"
# --| User Config |---------------------------------------------------

BLE_MODE = BLE_MODE.upper().strip()
if BLE_MODE not in ("A", "B"):
    raise ValueError("BLE_MODE must be set to either A or B.")

WAIT_FOR_DOUBLE = 0.05
DEBOUNCE = 0.25

# Define Morse Code dictionary
morse_code = {
    ".-": "A",
    "-...": "B",
    "-.-.": "C",
    "-..": "D",
    ".": "E",
    "..-.": "F",
    "--.": "G",
    "....": "H",
    "..": "I",
    ".---": "J",
    "-.-": "K",
    ".-..": "L",
    "--": "M",
    "-.": "N",
    "---": "O",
    ".--.": "P",
    "--.-": "Q",
    ".-.": "R",
    "...": "S",
    "-": "T",
    "..-": "U",
    "...-": "V",
    ".--": "W",
    "-..-": "X",
    "-.--": "Y",
    "--..": "Z",
}

# BLE Radio Stuff
if BLE_MODE == "A":
    MY_NAME = "CENTRAL"
    FRIENDS_NAME = "PERIPHERAL"
else:
    MY_NAME = "PERIPHERAL"
    FRIENDS_NAME = "CENTRAL"
ble = BLERadio()
uart_service = UARTService()
advertisement = ProvideServicesAdvertisement(uart_service)
ble._adapter.name = MY_NAME  # pylint: disable=protected-access

# Display Stuff
display = clue.display
disp_group = displayio.Group()
display.show(disp_group)

# Background BMP with the Morse Code cheat sheet
bmp, pal = adafruit_imageload.load(
    "morse_bg.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette
)
disp_group.append(displayio.TileGrid(bmp, pixel_shader=pal))

# Incoming messages show up here
in_label = label.Label(terminalio.FONT, text="A" * 18, scale=2, color=0x000000)
in_label.anchor_point = (1.0, 0)
in_label.anchored_position = (235, 4)
disp_group.append(in_label)

# Outging messages show up here
out_label = label.Label(terminalio.FONT, text="B" * 18, scale=2, color=0x000000)
out_label.anchor_point = (1.0, 0)
out_label.anchored_position = (235, 180)
disp_group.append(out_label)

# Morse Code entry happens here
edit_label = label.Label(terminalio.FONT, text="----", scale=2, color=0x000000)
edit_label.anchor_point = (0.5, 0)
edit_label.anchored_position = (115, 212)
disp_group.append(edit_label)


def scan_and_connect():
    """
    Handles initial connection between the two CLUES.

    The CLUE set to BLE_MODE="A" will act as Central.
    The CLUE set to BLE_MODE="B" will act as Peripheral.

    Return is a UART object that can be used for read/write.
    """

    print("Connecting...")
    in_label.text = out_label.text = "Connecting..."

    if MY_NAME == "CENTRAL":
        keep_scanning = True
        print("Scanning...")

        while keep_scanning:
            for adv in ble.start_scan():
                if adv.complete_name == FRIENDS_NAME:
                    ble.stop_scan()
                    ble.connect(adv)
                    keep_scanning = False

        print("Connected. Done scanning.")
        return uart_service

    else:
        print("Advertising...")
        ble.start_advertising(advertisement)

        while not ble.connected:
            if ble.connected:
                break

        print("Connected. Stop advertising.")
        ble.stop_advertising()

        print("Connecting to Central UART service.")
        for connection in ble.connections:
            if UARTService not in connection:
                continue
            return connection[UARTService]

    return None


# --------------------------
# The main application loop
# --------------------------
while True:
    # Establish initial connection
    uart = scan_and_connect()

    print("Connected.")

    code = ""
    in_label.text = out_label.text = " " * 18
    edit_label.text = " " * 4
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
                print(".", end="")
                code += "."
                edit_label.text = "{:4s}".format(code)
                time.sleep(DEBOUNCE)

        # DASH (or done)
        if clue.button_b:
            start = time.monotonic()
            while time.monotonic() - start < WAIT_FOR_DOUBLE:
                if clue.button_a:
                    done = True
            if not done and len(code) < 4:
                print("-", end="")
                code += "-"
                edit_label.text = "{:4s}".format(code)
                time.sleep(DEBOUNCE)

        # Turn Morse Code into letter and send
        if done:
            letter = morse_code.get(code, " ")
            print(" >", letter)
            out_label.text = out_label.text[1:] + letter
            uart.write(str.encode(letter))
            code = ""
            edit_label.text = " " * 4
            done = False
            time.sleep(DEBOUNCE)

    print("Disconnected.")
