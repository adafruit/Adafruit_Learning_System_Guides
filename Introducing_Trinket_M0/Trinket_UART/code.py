# Trinket IO demo - USB/Serial echo

import board
import busio
from digitalio import DigitalInOut, Direction

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

# You can also use board.TX and board.RX for prettier code!
uart = busio.UART(board.D4, board.D3, baudrate=9600)

while True:
    data = uart.read(32)  # read up to 32 bytes
    # print(data)          # this is a bytearray type

    if data is not None:
        led.value = True

        # convert bytearray to string
        datastr = ''.join([chr(b) for b in data])
        print(datastr, end="")

        led.value = False
