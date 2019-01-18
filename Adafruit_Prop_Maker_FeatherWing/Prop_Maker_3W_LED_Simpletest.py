"""Simple rainbow swirl example for 3W LED"""
import pulseio
import board
import digitalio

enable = digitalio.DigitalInOut(board.D10)
enable.direction = digitalio.Direction.OUTPUT
enable.value = True

red = pulseio.PWMOut(board.D11, duty_cycle=0, frequency=20000)
green = pulseio.PWMOut(board.D12, duty_cycle=0, frequency=20000)
blue = pulseio.PWMOut(board.D13, duty_cycle=0, frequency=20000)


def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


while True:
    for i in range(255):
        r, g, b = wheel(i)
        red.duty_cycle = int(r * 65536 / 256)
        green.duty_cycle = int(g * 65536 / 256)
        blue.duty_cycle = int(b * 65536 / 256)
