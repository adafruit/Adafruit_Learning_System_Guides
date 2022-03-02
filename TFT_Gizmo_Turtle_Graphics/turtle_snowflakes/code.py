# SPDX-FileCopyrightText: 2019 John Edgar Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Turtle Gizmo Snowflakes
#==| Turtle Gizmo Setup start |========================================
import time
from random import randint
import board
import busio
import displayio
from adafruit_st7789 import ST7789
from adafruit_turtle import turtle
displayio.release_displays()
spi = busio.SPI(board.SCL, MOSI=board.SDA)
display_bus = displayio.FourWire(spi, command=board.TX, chip_select=board.RX)
display = ST7789(display_bus, width=240, height=240, rowstart=80,
                 backlight_pin=board.A3, rotation=180)
turtle = turtle(display)
#==| Turtle Gizmo Setup end |=========================================

def draw_arm():
    turtle.pendown()
    for angle, length in arm_data:
        turtle.forward(length)
        turtle.left(angle)
        turtle.forward(length)
        turtle.backward(length)
        turtle.right(2*angle)
        turtle.forward(length)
        turtle.backward(length)
        turtle.left(angle)
    turtle.penup()

def draw_flake(arms):
    turtle.penup()
    turtle.home()
    turtle.clear()
    angle = 0
    delta_angle = 360 // arms
    for _ in range(arms):
        turtle.home()
        turtle.setheading(angle)
        draw_arm()
        angle += delta_angle
    turtle.penup()
    turtle.home()

while True:
    arm_data = [(randint(30, 80), randint(10, 40)) for _ in range(5)]
    draw_flake(randint(5, 8)) #adjust number of arms here
    time.sleep(5)
