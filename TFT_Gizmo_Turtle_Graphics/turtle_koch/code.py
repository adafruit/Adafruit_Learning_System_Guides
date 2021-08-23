# Turtle Gizmo Koch Snowflake
#==| Turtle Gizmo Setup start |========================================
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

def f(side_length, depth, generation):
    if depth == 0:
        side = turtle.forward(side_length)
    else:
        side = lambda: f(side_length / 3, depth - 1, generation + 1)
        side()
        turtle.left(60)
        side()
        turtle.right(120)
        side()
        turtle.left(60)
        side()

turtle.penup()
turtle.goto(-99, 56)
turtle.pendown()

num_generations = 3
top_side = lambda: f(218, num_generations, 0)

top_side()
turtle.right(120)
top_side()
turtle.right(120)
top_side()

while True:
    pass
