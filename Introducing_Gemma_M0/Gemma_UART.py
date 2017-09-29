# Gemma IO demo - USB/Serial echo

from digitalio import *
from board import *
import busio
import time

led = DigitalInOut(D13)
led.direction = Direction.OUTPUT

uart = busio.UART(D0, D2, baudrate=9600)

while True:
    data = uart.read(32)  # read up to 32 bytes
    #print(data)          # this is a bytearray type

    if data != None:
        led.value = True

	datastr = ''.join([chr(b) for b in data]) # convert bytearray to string
	print(datastr, end="")

        led.value = False
