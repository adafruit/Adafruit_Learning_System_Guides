# CircuitPython Demo - USB/Serial echo

import digitalio
import board
import busio

led = digitalio.DigitalInOut(board.D13)
led.direction = digitalio.Direction.OUTPUT

uart = busio.UART(board.TX, board.RX, baudrate=9600)

while True:
    data = uart.read(32)  # read up to 32 bytes
    # print(data)  # this is a bytearray type

    if data is not None:
        led.value = True

        data_string = ''.join([chr(b) for b in data])  # convert bytearray to string
        print(data_string, end="")

        led.value = False
