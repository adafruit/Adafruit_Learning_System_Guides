# SPDX-FileCopyrightText: 2019 John Edgar Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Turtle Gizmo Parabolic Jack
#==| Turtle Gizmo Setup start |========================================
import board
import busio
import displayio
import fourwire
from adafruit_st7789 import ST7789
from adafruit_turtle import Color, turtle
displayio.release_displays()
spi = busio.SPI(board.SCL, MOSI=board.SDA)
display_bus = fourwire.FourWire(spi, command=board.TX, chip_select=board.RX)
display = ST7789(display_bus, width=240, height=240, rowstart=80,
                 backlight_pin=board.A3, rotation=180)
turtle = turtle(display)
#==| Turtle Gizmo Setup end |=========================================

print("Draw parabolas using straight line segments!")

def vert(x, y, size):
    turtle.goto(x, y)
    turtle.dot(size)

turtle.penup()
turtle.pencolor(Color.GREEN)

vert(0, 0, 7)
vert(0, 100, 7)
vert(100, 0, 7)
vert(0, -100, 7)
vert(-100, 0, 7)

x_quad=[10, 10, -10, -10]
y_quad=[10, -10, -10, 10]

for q in range(4):
    for i in range(0,11):
        x_from = 0
        y_from = (10-i) * y_quad[q]
        x_to = i * x_quad[q]
        y_to = 0
        turtle.penup()
        turtle.goto(x_from,y_from)
        turtle.pendown()
        turtle.goto(x_to,y_to)

turtle.home()


while True:
    pass
