# CircusPython!
# For use with the Adafruit BlueFruit LE Connect app.
# Works with CircuitPython 4.0.0-beta.1 and later running on an nRF52840 board.

import random
import time

from adafruit_crickit import crickit
from adafruit_ble.uart import UARTServer

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

uart_server = UARTServer()

# Increase this to slow down movement of the servo arm.
DELAY = 0.0

# Angle for Blinka before jumping through the ring.
UP_ANGLE = 50

# Go to this angle when jumping through the ring. Adjust
# slightly as necessary so you don't bump into the ring.
DOWN_ANGLE = 2

advertising_now = False
crickit.servo_1.angle = UP_ANGLE
angle = UP_ANGLE

while True:
    sparkle()
    if not uart_server.connected:
        if not advertising_now:
            uart_server.start_advertising()
            advertising_now = True
        continue

    # Connected, so no longer advertising.
    advertising_now = False

    if uart_server.in_waiting:
        packet = Packet.from_stream(uart_server)
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
