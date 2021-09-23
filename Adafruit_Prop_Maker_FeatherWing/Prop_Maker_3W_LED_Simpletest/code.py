"""Simple rainbow swirl example for 3W LED"""
import pwmio
import board
from rainbowio import colorwheel
import digitalio

enable = digitalio.DigitalInOut(board.D10)
enable.direction = digitalio.Direction.OUTPUT
enable.value = True

red = pwmio.PWMOut(board.D11, duty_cycle=0, frequency=20000)
green = pwmio.PWMOut(board.D12, duty_cycle=0, frequency=20000)
blue = pwmio.PWMOut(board.D13, duty_cycle=0, frequency=20000)

while True:
    for i in range(255):
        r, g, b = colorwheel(i)
        red.duty_cycle = int(r * 65536 / 256)
        green.duty_cycle = int(g * 65536 / 256)
        blue.duty_cycle = int(b * 65536 / 256)
