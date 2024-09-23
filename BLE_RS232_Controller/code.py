# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import busio
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.button_packet import ButtonPacket
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService
import neopixel

# baud rate for your device
baud = 38400
# commands for your device
commands = ["AVI=1", "AVI=2", "AVI=3", "AVI=4"]
# Initialize UART for the RS232
uart = busio.UART(board.TX, board.RX, baudrate=baud)
# onboard neopixel
pixels = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.5, auto_write=True)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
#  BLE setup
ble = BLERadio()
ble_uart = UARTService()
advertisement = ProvideServicesAdvertisement(ble_uart)
advertising = False
print("advertising..")
while True:
    if not ble.connected and not advertising:
        #  not connected in the app yet
        pixels.fill(RED)
        ble.start_advertising(advertisement)
        advertising = True

    while ble.connected:
        pixels.fill(BLUE)
        # after connected via app
        advertising = False
        if ble_uart.in_waiting:
            #  waiting for input from app
            packet = Packet.from_stream(ble_uart)
            if isinstance(packet, ButtonPacket):
                #  if buttons in the app are pressed
                if packet.pressed:
                    if packet.button == ButtonPacket.BUTTON_1:
                        uart.write((commands[0] + "\r\n").encode('ascii'))
                    if packet.button == ButtonPacket.BUTTON_2:
                        uart.write((commands[1] + "\r\n").encode('ascii'))
                    if packet.button == ButtonPacket.BUTTON_3:
                        uart.write((commands[2] + "\r\n").encode('ascii'))
                    if packet.button == ButtonPacket.BUTTON_4:
                        uart.write((commands[3] + "\r\n").encode('ascii'))
        # empty buffer to collect the incoming data
        response_buffer = bytearray()
        # check for data
        time.sleep(1)
        while uart.in_waiting:
            data = uart.read(uart.in_waiting)
            if data:
                response_buffer.extend(data)
        # decode and print
        if response_buffer:
            print(response_buffer.decode('ascii'), end='')
            print()
