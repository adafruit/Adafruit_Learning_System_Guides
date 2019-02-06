# BLE Crickit Light Switch
# Use with the Adafruit BlueFruit LE Connect app
# Works with CircuitPython 4.0.0-beta.1 and later
# running on an nRF52840 Feather board and Crickit FeatherWing
# micro servo, 3D printed switch actuator

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

advertising_now = False
angle = NEUTRAL_ANGLE
crickit.servo_1.angle = NEUTRAL_ANGLE

while True:
    crickit.servo_1.angle = NEUTRAL_ANGLE
    if not uart_server.connected:
        if not advertising_now:
            uart_server.start_advertising()
            advertising_now = True
            blue_led.value = False
        continue

    # Connected, so no longer advertising.
    advertising_now = False
    blue_led.value = True

    if uart_server.in_waiting:
        red_led.value = False
        packet = Packet.from_stream(uart_server)

        if isinstance(packet, ButtonPacket):
            if packet.pressed:
                red_led.value = True
                if packet.button == '5' and angle != UP_ANGLE:
                    # The Up button was pressed.
                    for a in range(angle, UP_ANGLE+1, 1):
                        crickit.servo_1.angle = a
                    angle = UP_ANGLE

                elif packet.button == '6' and angle != DOWN_ANGLE:
                    # The Down button was pressed.
                    for a in range(angle, DOWN_ANGLE-1, -1):
                        crickit.servo_1.angle = a
                    angle = DOWN_ANGLE
