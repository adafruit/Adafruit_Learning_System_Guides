# Turtle Gizmo Christmas Tree
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

# Fractal Christmas Tree:
# https://codegolf.stackexchange.com/questions/15860/make-a-scalable-christmas-tree
#  by Keith Randall
n = 42  # input value for scaling the tree. note: ornaments don't scale
turtle.goto(0, -20)

#star
turtle.left(90)
turtle.forward(3*n)
turtle.pencolor(Color.YELLOW)
turtle.left(126)
turtle.pendown()
for _ in range(5):
    turtle.forward(n/5)
    turtle.right(144)
    turtle.forward(n/5)
    turtle.left(72)
turtle.right(126)

#tree
turtle.pencolor(Color.GREEN)
turtle.back(n*4.8)

def tree(d,s):
    if d <= 0:
        return
    turtle.forward(s)
    tree(d-1, s*.8)
    turtle.right(120)
    tree(d-3, s*.5)
    turtle.right(120)
    tree(d-3, s*.5)
    turtle.right(120)
    turtle.back(s)
turtle.pendown()
turtle.pencolor(Color.GREEN)
tree(15, n)
turtle.back(n/2)

#ornaments
def ornament(x, y):
    turtle.penup()
    turtle.goto(x, y)
    turtle.pencolor(Color.RED)
    turtle.pendown()
    turtle.dot(7)
    turtle.penup()

orn_pnts=[  (5, 60), (-7, 40), (10, 20), (-15, 0), (25, -20),
            (-27, -30), (7, -33), (40, -60), (-9, -63),
            (-50, -88), (62, -97) ]

for j in range(len(orn_pnts)):
    ornament(orn_pnts[j][0], orn_pnts[j][1])


turtle.penup()
turtle.goto(0, -120)

while True:
    pass
