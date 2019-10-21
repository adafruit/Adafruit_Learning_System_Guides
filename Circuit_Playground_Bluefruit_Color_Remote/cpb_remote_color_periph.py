"""
Used along with cpb_remote_color_client.py. Receives Bluefruit LE ColorPackets from a central,
and updates NeoPixels to show the history of the received packets.
"""

import board
import neopixel

from adafruit_ble.uart_server import UARTServer
from adafruit_bluefruit_connect.packet import Packet
# Only the packet classes that are imported will be known to Packet.
from adafruit_bluefruit_connect.color_packet import ColorPacket

uart_server = UARTServer()

NUM_PIXELS = 10
np = neopixel.NeoPixel(board.NEOPIXEL, NUM_PIXELS, brightness=0.1)
next_pixel = 0

def mod(i):
    """Wrap i to modulus NUM_PIXELS."""
    return i % NUM_PIXELS

while True:
    # Advertise when not connected.
    uart_server.start_advertising()
    while not uart_server.connected:
        pass

    while uart_server.connected:
        packet = Packet.from_stream(uart_server)
        if isinstance(packet, ColorPacket):
            print(packet.color)
            np[next_pixel] = packet.color
            np[mod(next_pixel + 1)] = (0, 0, 0)
        next_pixel = (next_pixel + 1) % NUM_PIXELS
