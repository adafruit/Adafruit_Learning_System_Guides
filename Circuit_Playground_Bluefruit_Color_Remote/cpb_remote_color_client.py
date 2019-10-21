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

from adafruit_ble.scanner import Scanner
from adafruit_ble.uart_client import UARTClient

def scale(value):
    """Scale an value from 0-65535 (AnalogIn range) to 0-255 (RGB range)"""
    return int(value / 65535 * 255)

scanner = Scanner()
uart_client = UARTClient()

a3 = AnalogIn(board.A4)
a4 = AnalogIn(board.A5)
a5 = AnalogIn(board.A6)

while True:
    uart_addresses = []
    # Keep trying to find a UART peripheral
    while not uart_addresses:
        uart_addresses = uart_client.scan(scanner)
    uart_client.connect(uart_addresses[0], 5)

    while uart_client.connected:
        r = scale(a3.value)
        g = scale(a4.value)
        b = scale(a5.value)

        color = (r, g, b)
        print(color)
        color_packet = ColorPacket(color)
        try:
            uart_client.write(color_packet.to_bytes())
        except OSError:
            pass
        time.sleep(0.3)
