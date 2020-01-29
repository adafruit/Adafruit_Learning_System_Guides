# Thermal_Cam_v31.py
# 2020-01-28 v3.1
# (c) 2020 Jan Goolsbey for Adafruit Industries

print("Thermal_Cam_v31.py")

import time
import board
import displayio
from simpleio import map_range
from collections import namedtuple
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.rect import Rect
import adafruit_amg88xx
from adafruit_pybadger import PyBadger
from thermal_cam_converters import celsius_to_fahrenheit, fahrenheit_to_celsius

# Establish panel instance and check for joystick
panel = PyBadger(pixels_brightness=0.1)  # Set NeoPixel brightness
panel.pixels.fill(0)                     # Clear all NeoPixels
if hasattr(board, "JOYSTICK_X"):
    panel.has_joystick = True     # PyGamer
else: panel.has_joystick = False  # Must be PyBadge

# Establish I2C interface for the AMG8833 Thermal Camera
i2c = board.I2C()
amg8833 = adafruit_amg88xx.AMG88XX(i2c)

# Load the text font from the fonts folder
font = bitmap_font.load_font("/fonts/OpenSans-9.bdf")

# Display spash graphics and play startup tones
with open("/thermal_cam_splash.bmp", "rb") as bitmap_file:
    bitmap = displayio.OnDiskBitmap(bitmap_file)
    splash = displayio.Group()
    splash.append(displayio.TileGrid(bitmap,
                  pixel_shader=displayio.ColorConverter()))
    board.DISPLAY.show(splash)
    time.sleep(0.1)  # Allow the splash to display
panel.play_tone(440, 0.1)  # A4
panel.play_tone(880, 0.1)  # A5

# The image sensor's design-limited temperature range
MIN_SENSOR_C = 0
MAX_SENSOR_C = 80
MIN_SENSOR_F = celsius_to_fahrenheit(MIN_SENSOR_C)
MAX_SENSOR_F = celsius_to_fahrenheit(MAX_SENSOR_C)

# Load default alarm and min/max range values list from config file
from thermal_cam_config import *

# Convert default alarm and min/max range values from config file
ALARM_C     = fahrenheit_to_celsius(ALARM_F)
MIN_RANGE_C = fahrenheit_to_celsius(MIN_RANGE_F)
MAX_RANGE_C = fahrenheit_to_celsius(MAX_RANGE_F)

# The board's integral display size
WIDTH  = board.DISPLAY.width   # 160 for PyGamer and PyBadge
HEIGHT = board.DISPLAY.height  # 128 for PyGamer and PyBadge

ELEMENT_SIZE = WIDTH // 10  # Size of element_grid blocks in pixels

# Default colors
BLACK   = 0x000000
RED     = 0xFF0000
ORANGE  = 0xFF8811
YELLOW  = 0xFFFF00
GREEN   = 0x00FF00
CYAN    = 0x00FFFF
BLUE    = 0x0000FF
VIOLET  = 0x9900FF
WHITE   = 0xFFFFFF
GRAY    = 0x444455

# Block colors for the thermal image grid
element_color = [GRAY, BLUE, GREEN, YELLOW, ORANGE, RED, VIOLET, WHITE]
# Text colors for on-screen parameters
param_list = [("ALARM", WHITE), ("RANGE", RED), ("RANGE", CYAN)]

### Helpers ###
Coords = namedtuple("Point", "x y")  # Used by element_grid()

def element_grid(col, row):  # Determine display coordinates for column, row
    return Coords(int(ELEMENT_SIZE * col + 30), int(ELEMENT_SIZE * row + 1))

def flash_status(text="", duration=0.05):  # Flash status message once
    status_label.color = WHITE
    status_label.text  = text
    time.sleep(duration)
    status_label.color = BLACK
    time.sleep(duration)
    return

def update_image_frame():  # Get camera data and display
    minimum = MAX_SENSOR_C  # Set minimum to sensor's maximum C value
    maximum = MIN_SENSOR_C  # Set maximum to sensor's minimum C value

    min_histo.text   = ""  # Clear histogram legend
    max_histo.text   = ""
    range_histo.text = ""

    sum_bucket = 0  # Clear bucket for building average value

    for row in range(0, 8):  # Parse camera data list and update display
        for col in range(0, 8):
            value = map_range(image[7 - row][7 - col],
                              MIN_SENSOR_C, MAX_SENSOR_C,
                              MIN_SENSOR_C, MAX_SENSOR_C)
            color_index = int(map_range(value, MIN_RANGE_C, MAX_RANGE_C, 0, 7))
            image_group[((row * 8) + col) + 1].fill = element_color[color_index]
            sum_bucket = sum_bucket + value  # Calculate sum for average
            minimum = min(value, minimum)
            maximum = max(value, maximum)
    return minimum, maximum, sum_bucket

def update_histo_frame():
    minimum = MAX_SENSOR_C  # Set minimum to sensor's maximum C value
    maximum = MIN_SENSOR_C  # Set maximum to sensor's minimum C value

    min_histo.text   = str(MIN_RANGE_F)  # Display histogram legend
    max_histo.text   = str(MAX_RANGE_F)
    range_histo.text = "-RANGE-"

    sum_bucket = 0  # Clear bucket for building average value

    histo_bucket = [0, 0, 0, 0, 0, 0, 0, 0]  # Clear histogram bucket
    for row in range(7, -1, -1):  # Collect camera data and calculate spectrum
        for col in range(0, 8):
            value = map_range(image[col][row],
                              MIN_SENSOR_C, MAX_SENSOR_C,
                              MIN_SENSOR_C, MAX_SENSOR_C)
            histo_index = int(map_range(value, MIN_RANGE_C, MAX_RANGE_C, 0, 7))
            histo_bucket[histo_index] = histo_bucket[histo_index] + 1
            sum_bucket = sum_bucket + value  # Calculate sum for average
            minimum = min(value, minimum)
            maximum = max(value, maximum)

    for col in range(0, 8):  # Display histogram
        for row in range(0, 8):
            if histo_bucket[col] / 8 > 7 - row:
                image_group[((row * 8) + col) + 1].fill = element_color[col]
            else:
                image_group[((row * 8) + col) + 1].fill = BLACK
    return minimum, maximum, sum_bucket

def setup_mode():  # Set alarm threshold and minimum/maximum range values
    status_label.color = WHITE
    status_label.text  = "-SET-"

    ave_label.color = BLACK  # Turn off average label and value display
    ave_value.color = BLACK

    max_value.text = str(MAX_RANGE_F)  # Display maximum range value
    min_value.text = str(MIN_RANGE_F)  # Display minimum range value

    time.sleep(0.8)  # Show SET status text before setting parameters
    status_label.text  = ""  # Clear status text

    param_index = 0  # Reset index of parameter to set

    # Select parameter to set
    while not panel.button.start:
        while (not panel.button.a) and (not panel.button.start):
            left, right, up, down = move_buttons(joystick=panel.has_joystick)
            if up:
                param_index = param_index - 1
            if down:
                param_index = param_index + 1
            param_index = max(0, min(2, param_index))
            status_label.text = param_list[param_index][0]
            image_group[param_index + 66].color = BLACK
            status_label.color = BLACK
            time.sleep(0.2)
            image_group[param_index + 66].color = param_list[param_index][1]
            status_label.color = WHITE
            time.sleep(0.2)

        if panel.button.a:  # Button A pressed
            panel.play_tone(1319, 0.030)  # E6
        while panel.button.a:  # wait for button release
            pass

        # Adjust parameter value
        param_value = int(image_group[param_index + 70].text)
        while (not panel.button.a) and (not panel.button.start):
            left, right, up, down = move_buttons(joystick=panel.has_joystick)
            if up:
                param_value = param_value + 1
            if down:
                param_value = param_value - 1
            param_value = max(MIN_SENSOR_F, min(MAX_SENSOR_F, param_value))
            image_group[param_index + 70].text = str(param_value)
            image_group[param_index + 70].color = BLACK
            status_label.color = BLACK
            time.sleep(0.05)
            image_group[param_index + 70].color = param_list[param_index][1]
            status_label.color = WHITE
            time.sleep(0.2)

        if panel.button.a:  # Button A pressed
            panel.play_tone(1319, 0.030)  # E6
        while panel.button.a:  # wait for button release
            pass

    # Exit setup process
    if panel.button.start:  # Start button pressed
        panel.play_tone(784, 0.030)  # G5
    while panel.button.start:  # wait for button release
        pass

    status_label.text = "RESUME"
    time.sleep(0.5)
    status_label.text = ""

    # Display average label and value
    ave_label.color = YELLOW
    ave_value.color = YELLOW
    return int(alarm_value.text), int(max_value.text), int(min_value.text)

def move_buttons(joystick=False):  # Read position buttons and joystick
    move_r = move_l = False
    move_u = move_d = False
    if joystick:  # For PyGamer: interpret joystick as buttons
        if   panel.joystick[0] > 44000:
            move_r = True
        elif panel.joystick[0] < 20000:
            move_l = True
        if   panel.joystick[1] < 20000:
            move_u = True
        elif panel.joystick[1] > 44000:
            move_d = True
    else:  # For PyBadge read the buttons
        if panel.button.right:
            move_r = True
        if panel.button.left:
            move_l = True
        if panel.button.up:
            move_u = True
        if panel.button.down:
            move_d = True
    return move_r, move_l, move_u, move_d

### Define the display group ###
image_group = displayio.Group(max_size=77)

# Create a background color fill layer; image_group[0]
color_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 1)
color_palette = displayio.Palette(1)
color_palette[0] = BLACK
background = displayio.TileGrid(color_bitmap, pixel_shader=color_palette,
                                x=0, y=0)
image_group.append(background)

# Define the foundational thermal image element layers; image_group[1:64]
#   image_group[#]=(row * 8) + column
for row in range(0, 8):
    for col in range(0, 8):
        pos = element_grid(col, row)
        element = Rect(x=pos.x, y=pos.y,
                       width=ELEMENT_SIZE, height=ELEMENT_SIZE,
                       fill=None, outline=None, stroke=0)
        image_group.append(element)

# Define labels and values using element grid coordinates
status_label = Label(font, text="", color=BLACK, max_glyphs=6)
pos = element_grid(2.5, 4)
status_label.x = pos.x
status_label.y = pos.y
image_group.append(status_label)  # image_group[65]

alarm_label = Label(font, text="alm", color=WHITE, max_glyphs=3)
pos = element_grid(-1.8, 1.5)
alarm_label.x = pos.x
alarm_label.y = pos.y
image_group.append(alarm_label)  # image_group[66]

max_label = Label(font, text="max", color=RED, max_glyphs=3)
pos = element_grid(-1.8, 3.5)
max_label.x = pos.x
max_label.y = pos.y
image_group.append(max_label)  # image_group[67]

min_label = Label(font, text="min", color=CYAN, max_glyphs=3)
pos = element_grid(-1.8, 7.5)
min_label.x = pos.x
min_label.y = pos.y
image_group.append(min_label)  # image_group[68]

ave_label = Label(font, text="ave", color=YELLOW, max_glyphs=3)
pos = element_grid(-1.8, 5.5)
ave_label.x = pos.x
ave_label.y = pos.y
image_group.append(ave_label)  # image_group[69]

alarm_value = Label(font, text=str(ALARM_F), color=WHITE, max_glyphs=5)
pos = element_grid(-1.8, 0.5)
alarm_value.x = pos.x
alarm_value.y = pos.y
image_group.append(alarm_value)  # image_group[70]

max_value = Label(font, text=str(MAX_RANGE_F), color=RED, max_glyphs=5)
pos = element_grid(-1.8, 2.5)
max_value.x = pos.x
max_value.y = pos.y
image_group.append(max_value)  # image_group[71]

min_value = Label(font, text=str(MIN_RANGE_F), color=CYAN, max_glyphs=5)
pos = element_grid(-1.8, 6.5)
min_value.x = pos.x
min_value.y = pos.y
image_group.append(min_value)  # image_group[72]

ave_value = Label(font, text="---", color=YELLOW, max_glyphs=5)
pos = element_grid(-1.8, 4.5)
ave_value.x = pos.x
ave_value.y = pos.y
image_group.append(ave_value)  # image_group[73]

min_histo = Label(font, text="", color=CYAN, max_glyphs=3)
pos = element_grid(0.5, 7.5)
min_histo.x = pos.x
min_histo.y = pos.y
image_group.append(min_histo)  # image_group[74]

max_histo = Label(font, text="", color=RED, max_glyphs=3)
pos = element_grid(6.5, 7.5)
max_histo.x = pos.x
max_histo.y = pos.y
image_group.append(max_histo)  # image_group[75]

range_histo = Label(font, text="", color=BLUE, max_glyphs=7)
pos = element_grid(2.5, 7.5)
range_histo.x = pos.x
range_histo.y = pos.y
image_group.append(range_histo)  # image_group[76]

###--- PRIMARY PROCESS SETUP ---###
display_image = True   # Image display mode; False for histogram
display_hold  = False  # Active display mode; True to hold display
display_focus = False  # Standard display range; True to focus display range

# Activate display and play welcome tone
board.DISPLAY.show(image_group)
panel.play_tone(880, 0.1)  # A5; ready to start looking

###--- PRIMARY PROCESS LOOP ---###
while True:
    if display_hold:  # Flash hold status text label
        flash_status("-HOLD-")
    else:
        image = amg8833.pixels  # Get camera data list if not in hold mode
        status_label.text = ""  # Clear hold mode status text label

    if display_image:  # Image display mode and gather min, max, and sum stats
        v_min, v_max, v_sum = update_image_frame()
    else:  # Histogram display mode and gather min, max, and sum stats
        v_min, v_max, v_sum = update_histo_frame()

    # Display alarm setting and maxumum, minimum, and average stats
    alarm_value.text = str(ALARM_F)
    max_value.text   = str(celsius_to_fahrenheit(v_max))
    min_value.text   = str(celsius_to_fahrenheit(v_min))
    ave_value.text   = str(celsius_to_fahrenheit(v_sum // 64))

    # Flash first NeoPixel and play alarm notes if alarm threshold is exceeded
    # Second alarm note frequency is proportional to value above threshold
    if v_max >= ALARM_C:
        panel.pixels.fill(RED)
        panel.play_tone(880, 0.015)  # A5
        panel.play_tone(880 + (10 * (v_max - ALARM_C)), 0.015)  # A5
        panel.pixels.fill(BLACK)

    # See if a panel button is pressed
    if panel.button.a:  # Toggle display hold (shutter = button A)
        panel.play_tone(1319, 0.030)  # E6
        while panel.button.a:
            pass   # wait for button release
        if display_hold == False:
            display_hold = True
        else:
            display_hold = False

    if panel.button.b:  # Toggle image/histogram mode (display mode = button B)
        panel.play_tone(659, 0.030)  # E5
        while panel.button.b:  pass  # wait for button release
        if display_image:
            display_image = False
        else:
            display_image = True

    if panel.button.select:  # toggle focus mode (focus mode = select button)
        panel.play_tone(698, 0.030)  # F5
        if display_focus:
            display_focus = False  # restore previous (original) range values
            MIN_RANGE_F = temp_min_range_f
            MAX_RANGE_F = temp_max_range_f
            # update range min and max values in Celsius
            MIN_RANGE_C = fahrenheit_to_celsius(MIN_RANGE_F)
            MAX_RANGE_C = fahrenheit_to_celsius(MAX_RANGE_F)
            flash_status("ORIG", 0.2)
        else:
            display_focus = True  # set range values to image min/max
            temp_min_range_f = MIN_RANGE_F
            temp_max_range_f = MAX_RANGE_F
            MIN_RANGE_F = celsius_to_fahrenheit(v_min)
            MAX_RANGE_F = celsius_to_fahrenheit(v_max)
            MIN_RANGE_C = v_min  # update range temp in Celsius
            MAX_RANGE_C = v_max  # update range temp in Celsius
            flash_status("FOCUS", 0.2)
        while panel.button.select:
            pass  # wait for button release

    if panel.button.start:  # activate setup mode (setup mode = start button)
        panel.play_tone(784, 0.030)  # G5
        while panel.button.start:
            pass  # wait for button release

        # Update alarm and range values
        ALARM_F, MAX_RANGE_F, MIN_RANGE_F = setup_mode()
        ALARM_C = fahrenheit_to_celsius(ALARM_F)
        MIN_RANGE_C = fahrenheit_to_celsius(MIN_RANGE_F)
        MAX_RANGE_C = fahrenheit_to_celsius(MAX_RANGE_F)

    pass  # bottom of primary loop
