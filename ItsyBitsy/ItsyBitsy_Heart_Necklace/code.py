# SPDX-FileCopyrightText: 2020 Noe Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
from rainbowio import colorwheel
import neopixel
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.button_packet import ButtonPacket
from adafruit_bluefruit_connect.color_packet import ColorPacket

# NeoPixel strip data pin
pixel_pin = board.D5

# The number of NeoPixels
num_pixels = 46

# Increase or decrease between 0 and 1 to increase or decrease the brightness of the LEDs
brightness = 0.1

# The order of the pixel colors - RGB or GRB. Some NeoPixels have red and green reversed!
ORDER = neopixel.GRB

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=brightness, auto_write=False,
                           pixel_order=ORDER)
# BLE Setup
ble = BLERadio()
uart_service = UARTService()
advertisement = ProvideServicesAdvertisement(uart_service)


#Rainbow Swirl Animation
def rainbow_swirl(wait):
    for j in range(255):
        for i in range(num_pixels):
            pixel_index = (i * 256 // num_pixels) + j
            pixels[i] = colorwheel(pixel_index & 255)
        pixels.show()
        time.sleep(wait)

#Rainbow Fill Animation
def rainbow_fill(wait):
    for j in range(255):
        for i in range(num_pixels):
            pixel_index = int(i + j)
            pixels[i] = colorwheel(pixel_index & 255)
        pixels.show()
        time.sleep(wait)

# List of colors
RED = (255, 0, 0)
ORANGE = (255, 50, 0)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
PURPLE = (100, 0, 255)
YELLOW = (255,230, 0)
BLUE = (0, 0, 255)

while True:
    while ble.connected:
        if uart_service.in_waiting:
            if uart_service.in_waiting:
                packet = Packet.from_stream(uart_service)
            if isinstance(packet, ColorPacket):
                # Set all the pixels to one color and stay there.
                pixels.fill(packet.color)
                pixels.show()
            elif isinstance(packet, ButtonPacket):
                if packet.pressed:
                    if packet.button == ButtonPacket.BUTTON_1:
                        pixels.fill(BLUE)
                        pixels.show()
                    elif packet.button == ButtonPacket.BUTTON_2:
                        pixels.fill(RED)
                        pixels.show()
                    elif packet.button == ButtonPacket.BUTTON_3:
                        rainbow_swirl(0.01)
                        pixels.show()
                    elif packet.button == ButtonPacket.BUTTON_4:
                        rainbow_fill(0.001)
                    elif packet.button == ButtonPacket.DOWN:
                        pixels.fill(BLACK)
                        pixels.show()
