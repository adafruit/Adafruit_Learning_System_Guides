# SPDX-FileCopyrightText: 2023 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
CircuitPython Feather RP2040 RFM95 Packet Receive Demo

This demo waits for a "button" packet. When the first packet is received, the NeoPixel LED
lights up red. The next packet changes it to green. The next packet changes it to blue.
Subsequent button packets cycle through the same colors in the same order.

This example is meant to be paired with the Packet Send Demo code running
on a second Feather RP2040 RFM95 board.
"""

import board
import digitalio
import neopixel
import adafruit_rfm9x

# Set up NeoPixel.
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixel.brightness = 0.5

# Define the possible NeoPixel colors. You can add as many colors to this list as you like!
# Simply follow the format shown below. Make sure you include the comma after the color tuple!
color_values = [
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
]

# Define radio frequency in MHz. Must match your
# module. Can be a value like 915.0, 433.0, etc.
RADIO_FREQ_MHZ = 915.0

# Define Chip Select and Reset pins for the radio module.
CS = digitalio.DigitalInOut(board.RFM_CS)
RESET = digitalio.DigitalInOut(board.RFM_RST)

# Initialise RFM95 radio
rfm95 = adafruit_rfm9x.RFM9x(board.SPI(), CS, RESET, RADIO_FREQ_MHZ)

color_index = 0
# Wait to receive packets.
print("Waiting for packets...")
while True:
    # Look for a new packet - wait up to 5 seconds:
    packet = rfm95.receive(timeout=5.0)
    # If no packet was received during the timeout then None is returned.
    if packet is not None:
        print("Received a packet!")
        # If the received packet is b'button'...
        if packet == b'button':
            # ...cycle the NeoPixel LED color through the color_values list.
            pixel.fill(color_values[color_index])
            color_index = (color_index + 1) % len(color_values)
