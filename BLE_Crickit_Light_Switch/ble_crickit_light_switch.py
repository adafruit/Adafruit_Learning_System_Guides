# BLE Crickit Light Switch
# Use with the Adafruit BlueFruit LE Connect app
# Works with CircuitPython 4.0.0-beta.1 and later
# running on an nRF52840 Feather board and Crickit FeatherWing
# micro servo, 3D printed switch actuator

import time

import board
import digitalio

from adafruit_crickit import crickit
from adafruit_ble.uart import UARTServer

from adafruit_bluefruit_connect.packet import Packet
# Only the packet classes that are imported will be known to Packet.
from adafruit_bluefruit_connect.button_packet import ButtonPacket

# Prep the status LEDs on the Feather
blue_led = digitalio.DigitalInOut(board.BLUE_LED)
red_led = digitalio.DigitalInOut(board.RED_LED)
blue_led.direction = digitalio.Direction.OUTPUT
red_led.direction = digitalio.Direction.OUTPUT

uart_server = UARTServer()

UP_ANGLE = 180
NEUTRAL_ANGLE = 120
DOWN_ANGLE = 80

crickit.servo_1.angle = NEUTRAL_ANGLE

while True:
    blue_led.value = False
    uart_server.start_advertising()

    while not uart_server.connected:
        # Wait for a connection.
        pass

    blue_led.value = True
    while uart_server.connected:
        crickit.servo_1.angle = NEUTRAL_ANGLE
        if uart_server.in_waiting:
            # Packet is arriving.
            red_led.value = False
            packet = Packet.from_stream(uart_server)

            if isinstance(packet, ButtonPacket) and packet.pressed:
                red_led.value = True
                if packet.button == ButtonPacket.UP:
                    # The Up button was pressed.
                    crickit.servo_1.angle = UP_ANGLE
                elif packet.button == ButtonPacket.DOWN:
                    # The Down button was pressed.
                    crickit.servo_1.angle = DOWN_ANGLE

                # Wait a bit before returning to neutral position.
                time.sleep(0.25)
