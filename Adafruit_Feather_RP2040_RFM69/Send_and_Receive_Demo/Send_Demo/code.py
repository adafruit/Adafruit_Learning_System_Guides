# SPDX-FileCopyrightText: 2023 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
CircuitPython Feather RP2040 RFM69 Packet Send Demo

This demo sends a "button" packet when the Boot button is pressed.

This example is meant to be paired with the Packet Receive Demo code running
on a second Feather RP2040 RFM69 board.
"""

import board
import digitalio
import keypad
import adafruit_rfm69

# Set up button using keypad module.
button = keypad.Keys((board.BUTTON,), value_when_pressed=False)

# Define radio frequency in MHz. Must match your
# module. Can be a value like 915.0, 433.0, etc.
RADIO_FREQ_MHZ = 915.0

# Define Chip Select and Reset pins for the radio module.
CS = digitalio.DigitalInOut(board.RFM_CS)
RESET = digitalio.DigitalInOut(board.RFM_RST)

# Initialise RFM69 radio
rfm69 = adafruit_rfm69.RFM69(board.SPI(), CS, RESET, RADIO_FREQ_MHZ)

while True:
    button_press = button.events.get()
    if button_press:
        if button_press.pressed:
            rfm69.send(bytes("button", "UTF-8"))
