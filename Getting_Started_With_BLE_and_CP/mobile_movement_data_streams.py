from adafruit_ble.uart import UARTServer
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.accelerometer_packet import AccelerometerPacket
from adafruit_bluefruit_connect.magnetometer_packet import MagnetometerPacket
from adafruit_bluefruit_connect.gyro_packet import GyroPacket
from adafruit_bluefruit_connect.quaternion_packet import QuaternionPacket


uart_server = UARTServer()

while True:
    uart_server.start_advertising()
    while not uart_server.connected:
        pass

    # Now we're connected

    while uart_server.connected:
        if uart_server.in_waiting:
            packet = Packet.from_stream(uart_server)
            if isinstance(packet, AccelerometerPacket):
                print("Acceleration:", packet.x, packet.y, packet.z)
            if isinstance(packet, MagnetometerPacket):
                print("Magnetometer:", packet.x, packet.y, packet.z)
            if isinstance(packet, GyroPacket):
                print("Gyro:", packet.x, packet.y, packet.z)
            if isinstance(packet, QuaternionPacket):
                print("Quaternion:", packet.x, packet.y, packet.z)

    # If we got here, we lost the connection. Go up to the top and start
    # advertising again and waiting for a connection.
