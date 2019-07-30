"""
PyPortal Calculator Demo
"""
import time
from collections import namedtuple
import board
import displayio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.rect import Rect
from adafruit_button import Button
from calculator import Calculator
import adafruit_touchscreen
Coords = namedtuple("Point", "x y")

ts = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,
                                      board.TOUCH_YD, board.TOUCH_YU,
                                      calibration=((5200, 59000), (5800, 57000)),
                                      size=(320, 240))

# Settings
BUTTON_WIDTH = 60
BUTTON_HEIGHT = 30
BUTTON_MARGIN = 8
MAX_DIGITS = 29
BLACK = 0x0
ORANGE = 0xFF8800
WHITE = 0xFFFFFF
GRAY = 0x888888
LABEL_OFFSET = 290

# Make the display context
calc_group = displayio.Group(max_size=25)
board.DISPLAY.show(calc_group)

# Make a background color fill
color_bitmap = displayio.Bitmap(320, 240, 1)
color_palette = displayio.Palette(1)
color_palette[0] = GRAY
bg_sprite = displayio.TileGrid(color_bitmap,
                               pixel_shader=color_palette,
                               x=0, y=0)
calc_group.append(bg_sprite)

# Load the font
font = bitmap_font.load_font("/fonts/Arial-12.bdf")
buttons = []

# Some button functions
def button_grid(row, col):
    return Coords(BUTTON_MARGIN * (row + 1) + BUTTON_WIDTH * row + 20,
                  BUTTON_MARGIN * (col + 1) + BUTTON_HEIGHT * col + 40)

def add_button(row, col, label, width=1, color=WHITE, text_color=BLACK):
    pos = button_grid(row, col)
    new_button = Button(x=pos.x, y=pos.y,
                        width=BUTTON_WIDTH * width + BUTTON_MARGIN * (width - 1),
                        height=BUTTON_HEIGHT, label=label, label_font=font,
                        label_color=text_color, fill_color=color, style=Button.ROUNDRECT)
    buttons.append(new_button)
    return new_button

def find_button(label):
    result = None
    for _, btn in enumerate(buttons):
        if btn.label == label:
            result = btn
    return result

border = Rect(20, 8, 280, 35, fill=WHITE, outline=BLACK, stroke=2)
calc_display = Label(font, text="0", color=BLACK, max_glyphs=MAX_DIGITS)
calc_display.y = 25

clear_button = add_button(0, 0, "AC")
add_button(1, 0, "+/-")
add_button(2, 0, "%")
add_button(3, 0, "/", 1, ORANGE, WHITE)
add_button(0, 1, "7")
add_button(1, 1, "8")
add_button(2, 1, "9")
add_button(3, 1, "x", 1, ORANGE, WHITE)
add_button(0, 2, "4")
add_button(1, 2, "5")
add_button(2, 2, "6")
add_button(3, 2, "-", 1, ORANGE, WHITE)
add_button(0, 3, "1")
add_button(1, 3, "2")
add_button(2, 3, "3")
add_button(3, 3, "+", 1, ORANGE, WHITE)
add_button(0, 4, "0", 2)
add_button(2, 4, ".")
add_button(3, 4, "=", 1, ORANGE, WHITE)

# Add the display and buttons to the main calc group
calc_group.append(border)
calc_group.append(calc_display)
for b in buttons:
    calc_group.append(b.group)

calculator = Calculator(calc_display, clear_button, LABEL_OFFSET)

button = ""
while True:
    point = ts.touch_point
    if point is not None:
        # Button Down Events
        for _, b in enumerate(buttons):
            if b.contains(point) and button == "":
                b.selected = True
                button = b.label
    elif button != "":
        # Button Up Events
        last_op = calculator.get_current_operator()
        op_button = find_button(last_op)
        # Deselect the last operation when certain buttons are pressed
        if op_button is not None:
            if button in ('=', 'AC', 'CE'):
                op_button.selected = False
            elif button in ('+', '-', 'x', '/') and button != last_op:
                op_button.selected = False
        calculator.add_input(button)
        b = find_button(button)
        if b is not None:
            if button not in ('+', '-', 'x', '/') or button != calculator.get_current_operator():
                b.selected = False
        button = ""
    time.sleep(0.05)
