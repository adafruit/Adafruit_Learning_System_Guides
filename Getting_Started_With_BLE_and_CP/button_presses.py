from adafruit_ble.uart import UARTServer
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.button_packet import ButtonPacket

uart_server = UARTServer()

while True:
    uart_server.start_advertising()
    while not uart_server.connected:
        pass

    # Now we're connected

    while uart_server.connected:
        if uart_server.in_waiting:
            packet = Packet.from_stream(uart_server)
            if isinstance(packet, ButtonPacket):
                if packet.pressed:
                    if packet.button == ButtonPacket.BUTTON_1:
                        # The 1 button was pressed.
                        print("1 button pressed!")
                    elif packet.button == ButtonPacket.UP:
                        # The UP button was pressed.
                        print("UP button pressed!")

    # If we got here, we lost the connection. Go up to the top and start
    # advertising again and waiting for a connection.
