# SPDX-FileCopyrightText: 2019 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Circuit Playground Bluefruit Rover
# Use with the Adafruit BlueFruit LE Connect app
# Works with CircuitPython 5.0.0-beta.0 and later
# running on an nRF52840 CPB board and Crickit

import time
import board
import digitalio
import neopixel
from adafruit_crickit import crickit

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

from adafruit_bluefruit_connect.packet import Packet
# Only the packet classes that are imported will be known to Packet.
from adafruit_bluefruit_connect.button_packet import ButtonPacket
from adafruit_bluefruit_connect.color_packet import ColorPacket

# Prep the status LED on the CPB
red_led = digitalio.DigitalInOut(board.D13)
red_led.direction = digitalio.Direction.OUTPUT

ble = BLERadio()
uart_service = UARTService()
advertisement = ProvideServicesAdvertisement(uart_service)

# motor setup
motor_1 = crickit.dc_motor_1
motor_2 = crickit.dc_motor_2

FWD = 0.25
REV = -0.25

neopixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=0.1)
RED = (200, 0, 0)
GREEN = (0, 200, 0)
BLUE = (0, 0, 200)
PURPLE = (120, 0, 160)
YELLOW = (100, 100, 0)
AQUA = (0, 100, 100)
BLACK = (0, 0, 0)
color = PURPLE  # current NeoPixel color
neopixels.fill(color)

print("BLE Turtle Rover")
print("Use Adafruit Bluefruit app to connect")
while True:
    neopixels[0] = BLACK
    neopixels.show()
    ble.start_advertising(advertisement)
    while not ble.connected:
        # Wait for a connection.
        pass
    # set a pixel blue when connected
    neopixels[0] = BLUE
    neopixels.show()
    while ble.connected:
        if uart_service.in_waiting:
            # Packet is arriving.
            red_led.value = False  # turn off red LED
            packet = Packet.from_stream(uart_service)
            if isinstance(packet, ColorPacket):
                # Change the color.
                color = packet.color
                neopixels.fill(color)

            # do this when buttons are pressed
            if isinstance(packet, ButtonPacket) and packet.pressed:
                red_led.value = True  # blink to show packet has been received
                if packet.button == ButtonPacket.UP:
                    neopixels.fill(color)
                    motor_1.throttle = FWD
                    motor_2.throttle = FWD
                elif packet.button == ButtonPacket.DOWN:
                    neopixels.fill(color)
                    motor_1.throttle = REV
                    motor_2.throttle = REV
                elif packet.button == ButtonPacket.RIGHT:
                    color = YELLOW
                    neopixels.fill(color)
                    motor_2.throttle = 0
                    motor_1.throttle = FWD
                elif packet.button == ButtonPacket.LEFT:
                    color = YELLOW
                    neopixels.fill(color)
                    motor_2.throttle = FWD
                    motor_1.throttle = 0
                elif packet.button == ButtonPacket.BUTTON_1:
                    neopixels.fill(RED)
                    motor_1.throttle = 0.0
                    motor_2.throttle = 0.0
                    time.sleep(0.5)
                    neopixels.fill(color)
                elif packet.button == ButtonPacket.BUTTON_2:
                    color = GREEN
                    neopixels.fill(color)
                elif packet.button == ButtonPacket.BUTTON_3:
                    color = BLUE
                    neopixels.fill(color)
                elif packet.button == ButtonPacket.BUTTON_4:
                    color = PURPLE
                    neopixels.fill(color)
            # do this when some buttons are released
            elif isinstance(packet, ButtonPacket) and not packet.pressed:
                if packet.button == ButtonPacket.UP:
                    neopixels.fill(RED)
                    motor_1.throttle = 0
                    motor_2.throttle = 0
                if packet.button == ButtonPacket.DOWN:
                    neopixels.fill(RED)
                    motor_1.throttle = 0
                    motor_2.throttle = 0
                if packet.button == ButtonPacket.RIGHT:
                    neopixels.fill(RED)
                    motor_1.throttle = 0
                    motor_2.throttle = 0
                if packet.button == ButtonPacket.LEFT:
                    neopixels.fill(RED)
                    motor_1.throttle = 0
                    motor_2.throttle = 0
