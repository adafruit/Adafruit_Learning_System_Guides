# Gemma IO demo - USB/Serial echo

import busio
from board import D0, D2, D13
from digitalio import DigitalInOut, Direction

led = DigitalInOut(D13)
led.direction = Direction.OUTPUT

uart = busio.UART(D0, D2, baudrate=9600)

while True:
    data = uart.read(32)  # read up to 32 bytes
    # print(data)          # this is a bytearray type

    if data is not None:
        led.value = True

        # convert bytearray to string
        datastr = ''.join([chr(b) for b in data])
        print(datastr, end="")

        led.value = False
