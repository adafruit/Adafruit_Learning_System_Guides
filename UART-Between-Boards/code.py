# SPDX-FileCopyrightText: Copyright (c) 2021 Dylan Herrada for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
Code for communicating between two CircuitPython boards using UART.
Increments built-in neopixel values of the other board starting from blue, then green and red.
"""
import time
import board
import busio
import neopixel

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=1.0, auto_write=True)

uart = busio.UART(board.TX, board.RX, baudrate=9600)


array = [0x55, 0, 0, 0, 0xAA]
print(array)
barray = bytearray(array)
print(barray)

uart.write(barray)
while True:
    data = uart.read(32)  # read up to 32 bytes
    if data is not None:
        msg = []
        print(data)
        if data[0] == 85 and data[-1] == 170:
            for byte in data[1:-1]:
                if len(msg) == 3:
                    break
                print(byte)
                msg.append(byte)

        print(msg)
        print(type(msg))

        pixel.fill(msg)

        time.sleep(0.1)

        if msg[2] < 255:
            data = [msg[0], msg[1], msg[2] + 5]
            data.insert(0, 0x55)
            data.append(0xAA)
        elif msg[1] < 255:
            data = [msg[0], msg[1] + 5, msg[2]]
            data.insert(0, 0x55)
            data.append(0xAA)
        elif msg[0] < 255:
            data = [msg[0] + 5, msg[1], msg[2]]
            data.insert(0, 0x55)
            data.append(0xAA)
        print(data)
        uart.write(bytearray(data))
