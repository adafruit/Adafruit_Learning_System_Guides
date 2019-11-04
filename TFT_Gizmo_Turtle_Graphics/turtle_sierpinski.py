# Turtle Gizmo Sierpinski Triangle
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

def getMid(p1, p2):
    return ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2) #find midpoint

def triangle(points, depth):

    turtle.penup()
    turtle.goto(points[0][0], points[0][1])
    turtle.pendown()
    turtle.goto(points[1][0], points[1][1])
    turtle.goto(points[2][0], points[2][1])
    turtle.goto(points[0][0], points[0][1])

    if depth > 0:
        triangle([points[0],
                  getMid(points[0], points[1]),
                  getMid(points[0], points[2])],
                 depth-1)
        triangle([points[1],
                  getMid(points[0], points[1]),
                  getMid(points[1], points[2])],
                 depth-1)
        triangle([points[2],
                  getMid(points[2], points[1]),
                  getMid(points[0], points[2])],
                 depth-1)

big = min(display.width/2, display.height/2)
little = big / 1.4
seed_points = [[-big, -little], [0, big], [big, -little]] #size of triangle
triangle(seed_points, 4)

while True:
    pass
