# SPDX-FileCopyrightText: 2019 John Edgar Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Demonstration of a Bluefruit BLE Central/client. Connects to the first BLE UART peripheral it finds.
Sends Bluefruit ColorPackets, read from three potentiometers, to the peripheral.
"""

import time

import board
from analogio import AnalogIn

#from adafruit_bluefruit_connect.packet import Packet
# Only the packet classes that are imported will be known to Packet.
from adafruit_bluefruit_connect.color_packet import ColorPacket

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

def scale(value):
    """Scale an value from 0-65535 (AnalogIn range) to 0-255 (RGB range)"""
    return int(value / 65535 * 255)

ble = BLERadio()

a4 = AnalogIn(board.A4)
a5 = AnalogIn(board.A5)
a6 = AnalogIn(board.A6)

uart_connection = None

# See if any existing connections are providing UARTService.
if ble.connected:
    for connection in ble.connections:
        if UARTService in connection:
            uart_connection = connection
        break

while True:
    if not uart_connection:
        for adv in ble.start_scan(ProvideServicesAdvertisement, timeout=5):
            if UARTService in adv.services:
                uart_connection = ble.connect(adv)
                break
        # Stop scanning whether or not we are connected.
        ble.stop_scan()

    while uart_connection and uart_connection.connected:
        r = scale(a4.value)
        g = scale(a5.value)
        b = scale(a6.value)

        color = (r, g, b)
        print(color)
        color_packet = ColorPacket(color)
        try:
            uart_connection[UARTService].write(color_packet.to_bytes())
        except OSError:
            pass
        time.sleep(0.3)
