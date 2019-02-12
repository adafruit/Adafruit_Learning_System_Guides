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
DOWN_ANGLE = 60
crickit.servo_1.angle = NEUTRAL_ANGLE

angle = NEUTRAL_ANGLE  # use to track state

print("BLE Light Switch")
print("Use Adafruit Bluefruit app to connect")
while True:
    blue_led.value = False
    uart_server.start_advertising()

    while not uart_server.connected:
        # Wait for a connection.
        pass
    blue_led.value = True  # turn on blue LED when connected
    while uart_server.connected:
        if uart_server.in_waiting:
            # Packet is arriving.
            red_led.value = False  # turn off red LED
            packet = Packet.from_stream(uart_server)
            if isinstance(packet, ButtonPacket) and packet.pressed:
                red_led.value = True  # blink to show a packet has been received
                if packet.button == ButtonPacket.UP and angle != UP_ANGLE:  # UP button pressed
                    angle = NEUTRAL_ANGLE - 45  # set anticipation angle, opposite of goal angle
                    for a in range(angle, UP_ANGLE+1, 1):  # anticipation angle, ramp to goal angle
                        crickit.servo_1.angle = a
                    time.sleep(0.1)  # wait a moment
                    crickit.servo_1.angle = NEUTRAL_ANGLE  # then return to neutral angle
                    angle = UP_ANGLE  # set state to prevent redundant hits
                elif packet.button == ButtonPacket.DOWN and angle != DOWN_ANGLE:  # DOWN button
                    angle = NEUTRAL_ANGLE + 45
                    for a in range(angle, DOWN_ANGLE-1, -1):
                        crickit.servo_1.angle = a
                    time.sleep(0.1)  # wait a moment
                    crickit.servo_1.angle = NEUTRAL_ANGLE  # then return to neutral angle
                    angle = DOWN_ANGLE  # set state to prevent redundant hits
