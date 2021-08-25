from time import sleep
from adafruit_ble.uart_server import UARTServer
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.button_packet import ButtonPacket
from adafruit_bluefruit_connect.color_packet import ColorPacket
from board import A0, D13
from analogio import AnalogIn
from digitalio import DigitalInOut, Direction

led = AnalogIn(A0)  # Initialize blue LED light detector

solenoid = DigitalInOut(D13)  # Initialize solenoid
solenoid.direction = Direction.OUTPUT
solenoid.value = False

uart_server = UARTServer()

while True:
    uart_server.start_advertising()  # Advertise when not connected.

    while not uart_server.connected:  # Wait for connection
        pass

    while uart_server.connected:  # Connected
        if uart_server.in_waiting:  # Check BLE commands
            packet = Packet.from_stream(uart_server)
            if isinstance(packet, ButtonPacket):
                if packet.button == '1' and packet.pressed:
                    solenoid.value = True  # Activate solenoid for 1 second
                    sleep(1)
                    solenoid.value = False

        led_intensity = led.value  # Check blue LED detector intensity
        led_on = led_intensity > 1000
        # Color: red = off, green = on
        color_packet = ColorPacket((255 * int(not led_on), 255 * led_on, 0))
        try:
            uart_server.write(color_packet.to_bytes())  # Transmit state color
        except OSError:
            pass

        sleep(.2)
