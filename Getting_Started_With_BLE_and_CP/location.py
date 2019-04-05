from adafruit_ble.uart import UARTServer
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.location_packet import LocationPacket


uart_server = UARTServer()

while True:
    uart_server.start_advertising()
    while not uart_server.connected:
        pass

    # Now we're connected

    while uart_server.connected:
        if uart_server.in_waiting:
            packet = Packet.from_stream(uart_server)
            if isinstance(packet, LocationPacket):
                print("Latitude:", packet.latitude)
                print("Longitude", packet.longitude)
                print("Altitude:", packet.altitude)

    # If we got here, we lost the connection. Go up to the top and start
    # advertising again and waiting for a connection..
