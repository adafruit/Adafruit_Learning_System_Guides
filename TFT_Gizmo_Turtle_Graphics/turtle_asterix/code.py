# SPDX-FileCopyrightText: 2019 John Edgar Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

#Turtle Gizmo Asterix
#==| Turtle Gizmo Setup start |========================================
import board
import busio
import displayio
import fourwire
from adafruit_st7789 import ST7789
from adafruit_turtle import turtle
displayio.release_displays()
spi = busio.SPI(board.SCL, MOSI=board.SDA)
display_bus = fourwire.FourWire(spi, command=board.TX, chip_select=board.RX)
display = ST7789(display_bus, width=240, height=240, rowstart=80,
                 backlight_pin=board.A3, rotation=180)
turtle = turtle(display)
#==| Turtle Gizmo Setup end |=========================================

turtle.pendown()
for _ in range(20):
    turtle.forward(80)
    turtle.back(80) #try changing this to 70 for an iris effect
    turtle.left(18)

while True:
    pass
