# SPDX-FileCopyrightText: 2019 John Edgar Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# CircuitPython BLE Rover
# Use with the Adafruit BlueFruit LE Connect app
# Works with CircuitPython 4.0.0-beta.1 and later
# running on an nRF52840 Feather board and Crickit FeatherWing

import time

import board
import digitalio

from adafruit_crickit import crickit

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

from adafruit_bluefruit_connect.packet import Packet
# Only the packet classes that are imported will be known to Packet.
from adafruit_bluefruit_connect.button_packet import ButtonPacket
from adafruit_bluefruit_connect.color_packet import ColorPacket

# Prep the status LEDs on the Feather
blue_led = digitalio.DigitalInOut(board.BLUE_LED)
red_led = digitalio.DigitalInOut(board.RED_LED)
blue_led.direction = digitalio.Direction.OUTPUT
red_led.direction = digitalio.Direction.OUTPUT

ble = BLERadio()
uart_service = UARTService()
advertisement = ProvideServicesAdvertisement(uart_service)

# motor setup
motor_1 = crickit.dc_motor_1
motor_2 = crickit.dc_motor_2

FWD = -1.0
REV = 0.7

crickit.init_neopixel(24, brightness = 0.2)  # create Crickit neopixel object
RED = (200, 0, 0)
GREEN = (0, 200, 0)
BLUE = (0, 0, 200)
PURPLE = (120, 0, 160)
YELLOW = (100, 100, 0)
AQUA = (0, 100, 100)
color = PURPLE  # current NeoPixel color
prior_color = PURPLE  # to store state of previous color when changing them
crickit.neopixel.fill(color)

print("BLE Rover")
print("Use Adafruit Bluefruit app to connect")
while True:
    blue_led.value = False
    ble.start_advertising(advertisement)
    while not ble.connected:
        # Wait for a connection.
        pass
    blue_led.value = True  # turn on blue LED when connected
    while ble.connected:
        if uart_service.in_waiting:
            # Packet is arriving.
            red_led.value = False  # turn off red LED
            packet = Packet.from_stream(uart_service)
            if isinstance(packet, ColorPacket):
                # Change the color.
                color = packet.color
                crickit.neopixel.fill(color)

            # do this when buttons are pressed
            if isinstance(packet, ButtonPacket) and packet.pressed:
                red_led.value = True  # blink to show a packet has been received
                if packet.button == ButtonPacket.UP:  # UP button pressed
                    crickit.neopixel.fill(color)
                    motor_1.throttle = FWD
                    motor_2.throttle = FWD
                elif packet.button == ButtonPacket.DOWN:  # DOWN button
                    crickit.neopixel.fill(color)
                    motor_1.throttle = REV
                    motor_2.throttle = REV
                elif packet.button == ButtonPacket.RIGHT:
                    prior_color = color
                    color = YELLOW
                    crickit.neopixel.fill(color)
                    motor_1.throttle = FWD
                    motor_2.throttle = FWD * 0.5
                elif packet.button == ButtonPacket.LEFT:
                    prior_color = color
                    color = YELLOW
                    crickit.neopixel.fill(color)
                    motor_1.throttle = FWD * 0.5
                    motor_2.throttle = FWD
                elif packet.button == ButtonPacket.BUTTON_1:
                    crickit.neopixel.fill(RED)
                    motor_1.throttle = 0.0
                    motor_2.throttle = 0.0
                    time.sleep(0.5)
                    crickit.neopixel.fill(color)
                elif packet.button == ButtonPacket.BUTTON_2:
                    color = GREEN
                    crickit.neopixel.fill(color)
                elif packet.button == ButtonPacket.BUTTON_3:
                    color = BLUE
                    crickit.neopixel.fill(color)
                elif packet.button == ButtonPacket.BUTTON_4:
                    color = PURPLE
                    crickit.neopixel.fill(color)
            # do this when some buttons are released
            elif isinstance(packet, ButtonPacket) and not packet.pressed:
                if packet.button == ButtonPacket.RIGHT:
                    print("released right")
                    color = prior_color
                    crickit.neopixel.fill(color)
                    motor_1.throttle = FWD
                    motor_2.throttle = FWD
                if packet.button == ButtonPacket.LEFT:
                    print("released left")
                    color = prior_color
                    crickit.neopixel.fill(color)
                    motor_1.throttle = FWD
                    motor_2.throttle = FWD
