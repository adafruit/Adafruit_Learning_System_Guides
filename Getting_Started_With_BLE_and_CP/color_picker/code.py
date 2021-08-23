import board
import neopixel

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.color_packet import ColorPacket

ble = BLERadio()
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)

while True:
    ble.start_advertising(advertisement)
    while not ble.connected:
        pass

    # Now we're connected

    while ble.connected:
        if uart.in_waiting:
            packet = Packet.from_stream(uart)
            if isinstance(packet, ColorPacket):
                # Change the NeoPixel color.
                pixel.fill(packet.color)

    # If we got here, we lost the connection. Go up to the top and start
    # advertising again and waiting for a connection.
