# SPDX-FileCopyrightText: 2019 John Edgar Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Turtle Gizmo Hilbert
#==| Turtle Gizmo Setup start |========================================
import board
import busio
import displayio
from adafruit_st7789 import ST7789
from adafruit_turtle import Color, turtle
displayio.release_displays()
spi = busio.SPI(board.SCL, MOSI=board.SDA)
display_bus = displayio.FourWire(spi, command=board.TX, chip_select=board.RX)
display = ST7789(display_bus, width=240, height=240, rowstart=80,
                 backlight_pin=board.A3, rotation=180)
turtle = turtle(display)
#==| Turtle Gizmo Setup end |=========================================

def hilbert2(step, rule, angle, depth, t):
    if depth > 0:
        a = lambda: hilbert2(step, "a", angle, depth - 1, t)
        b = lambda: hilbert2(step, "b", angle, depth - 1, t)
        left = lambda: t.left(angle)
        right = lambda: t.right(angle)
        forward = lambda: t.forward(step)
        if rule == "a":
            left()
            b()
            forward()
            right()
            a()
            forward()
            a()
            right()
            forward()
            b()
            left()
        if rule == "b":
            right()
            a()
            forward()
            left()
            b()
            forward()
            b()
            left()
            forward()
            a()
            right()

turtle.penup()

turtle.goto(-108, -108)
turtle.pendown()
turtle.pencolor(Color.PURPLE)
hilbert2(7, "a", 90, 5, turtle)

while True:
    pass
