# CircusPython!
# For use with the Adafruit BlueFruit LE Connect app.
# Works with CircuitPython 5.0.0-beta.0 and later running on an nRF52840 board.

import random
import time

from adafruit_crickit import crickit
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

from adafruit_bluefruit_connect.packet import Packet
# Only the packet classes that are imported will be known to Packet.
from adafruit_bluefruit_connect.color_packet import ColorPacket
from adafruit_bluefruit_connect.button_packet import ButtonPacket

# Initialize the NeoPixel ring to a fire color, not too bright.
crickit.init_neopixel(24, brightness=0.1)
color = (25, 12, 0)

# Creates a sparkly "fire"-like effect.
def sparkle():
    crickit.neopixel[random.randrange(24)] = (0, 0, 0)
    crickit.neopixel[random.randrange(24)] = color
    crickit.neopixel[random.randrange(24)] = color
    crickit.neopixel[random.randrange(24)] = color

ble = BLERadio()
uart_service = UARTService()
advertisement = ProvideServicesAdvertisement(uart_service)

# Increase this to slow down movement of the servo arm.
DELAY = 0.0

# Angle for Blinka before jumping through the ring.
UP_ANGLE = 50

# Go to this angle when jumping through the ring. Adjust
# slightly as necessary so you don't bump into the ring.
DOWN_ANGLE = 2

crickit.servo_1.angle = UP_ANGLE
angle = UP_ANGLE

while True:
    ble.start_advertising(advertisement)
    while not ble.connected:
        sparkle()
    while ble.connected:
        sparkle()
        if uart_service.in_waiting:
            packet = Packet.from_stream(uart_service)
            if isinstance(packet, ColorPacket):
                # Change the fire color.
                color = packet.color
            elif isinstance(packet, ButtonPacket):
                if packet.pressed:
                    if packet.button == '5' and angle != UP_ANGLE:
                        # The Up button was pressed.
                        for a in range(angle, UP_ANGLE+1, 1):
                            crickit.servo_1.angle = a
                            # Sparkle while moving.
                            sparkle()
                            time.sleep(DELAY)
                        angle = UP_ANGLE
                    elif packet.button == '6' and angle != DOWN_ANGLE:
                        # The Down button was pressed.
                        for a in range(angle, DOWN_ANGLE-1, -1):
                            crickit.servo_1.angle = a
                            # Sparkle while moving.
                            sparkle()
                            time.sleep(DELAY)
                        angle = DOWN_ANGLE
