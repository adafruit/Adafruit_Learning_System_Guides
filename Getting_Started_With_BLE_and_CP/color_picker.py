import board
import neopixel
from adafruit_ble.uart import UARTServer
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.color_packet import ColorPacket

uart_server = UARTServer()

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)

while True:
    uart_server.start_advertising()
    while not uart_server.connected:
        pass

    # Now we're connected

    while uart_server.connected:
        if uart_server.in_waiting:
            packet = Packet.from_stream(uart_server)
            if isinstance(packet, ColorPacket):
                # Change the NeoPixel color.
                pixel.fill(packet.color)

    # If we got here, we lost the connection. Go up to the top and start
    # advertising again and waiting for a connection.
