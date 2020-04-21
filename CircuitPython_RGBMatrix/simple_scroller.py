# This example implements a simple two line scroller using
# Adafruit_CircuitPython_Display_Text. Each line has its own color
# and it is possible to modify the example to use other fonts and non-standard
# characters.

import array

from _pixelbuf import wheel
import adafruit_display_text.label
import board
import displayio
import framebufferio
import rgbmatrix
import terminalio
displayio.release_displays()

matrix = rgbmatrix.RGBMatrix(
    width=64, height=32, bit_depth=1,
    rgb_pins=[board.D6, board.D5, board.D9, board.D11, board.D10, board.D12],
    addr_pins=[board.A5, board.A4, board.A3, board.A2],
    clock_pin=board.D13, latch_pin=board.D0, output_enable_pin=board.D1)
display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)

line1 = adafruit_display_text.label.Label(
    terminalio.FONT,
    color=0xff0000,
    text="This scroller is brought to you by CircuitPython RGBMatrix")
line1.x = display.width
line1.y = 8

line2 = adafruit_display_text.label.Label(
    terminalio.FONT,
    color=0x0080ff,
    text="Hello to all CircuitPython contributors worldwide <3")
line2.x = display.width
line2.y = 24

g = displayio.Group(max_size=2)
g.append(line1)
g.append(line2)
display.show(g)

# Scoot one label a pixel to the left; send it back to the far right
# if it's gone all the way off screen
def scroll(line):
    line.x = line.x - 1
    line_width = line.bounding_box[2]
    if line.x < -line_width:
        line.x = display.width

# You can add more effects in this loop. For instance, maybe you want to set the
# color of each label to a different value
while True:
    scroll(line1)
    scroll(line2)
    display.refresh(minimum_frames_per_second=0)
