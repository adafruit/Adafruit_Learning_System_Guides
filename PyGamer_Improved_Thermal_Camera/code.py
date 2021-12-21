# SPDX-FileCopyrightText: 2021 Jan Goolsbey for Adafruit Industries
# SPDX-License-Identifier: MIT

# Thermal_Cam_v70_PyBadge_code.py
# 2021-12-21 v7.0  # CircuitPython v7.x compatible

import time
import board
import busio
import gc
import ulab
import displayio
import neopixel
from analogio import AnalogIn
from digitalio import DigitalInOut
from simpleio import map_range, tone
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.rect import Rect
import adafruit_amg88xx
from gamepadshift import GamePadShift
from index_to_rgb.iron_spectrum import index_to_rgb
from thermal_cam_converters import celsius_to_fahrenheit, fahrenheit_to_celsius
from thermal_cam_config import ALARM_F, MIN_RANGE_F, MAX_RANGE_F, SELFIE

# Instantiate display, joystick, speaker, and neopixels
display = board.DISPLAY
# Load the text font from the fonts folder
font_0 = bitmap_font.load_font("/fonts/OpenSans-9.bdf")

if hasattr(board, "JOYSTICK_X"):
    has_joystick = True  # PyGamer with joystick
    joystick_x = AnalogIn(board.JOYSTICK_X)
    joystick_y = AnalogIn(board.JOYSTICK_Y)
else:
    has_joystick = False  # PyBadge with buttons

speaker_enable = DigitalInOut(board.SPEAKER_ENABLE)
speaker_enable.switch_to_output(value=True)

pixels = neopixel.NeoPixel(board.NEOPIXEL, 5, pixel_order=neopixel.GRB)
pixels.brightness = 0.25  # Set NeoPixel brightness
pixels.fill(0x000000)  # Clear all NeoPixels

# Define and instantiate front panel buttons
BUTTON_LEFT = 0b10000000
BUTTON_UP = 0b01000000
BUTTON_DOWN = 0b00100000
BUTTON_RIGHT = 0b00010000
BUTTON_SELECT = 0b00001000
BUTTON_START = 0b00000100
BUTTON_A = 0b00000010
BUTTON_B = 0b00000001

panel = GamePadShift(
    DigitalInOut(board.BUTTON_CLOCK),
    DigitalInOut(board.BUTTON_OUT),
    DigitalInOut(board.BUTTON_LATCH),
)

# Establish I2C interface for the AMG8833 Thermal Camera
i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
amg8833 = adafruit_amg88xx.AMG88XX(i2c)

# Display splash graphics
splash = displayio.Group(scale=display.width // 160)
bitmap = displayio.OnDiskBitmap("/thermal_cam_splash.bmp")
splash.append(displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader))
board.DISPLAY.show(splash)
time.sleep(0.1)  # Allow the splash to display

# Set up ulab arrays
n = 8  # Thermal sensor grid axis size; AMG8833 sensor is 8x8
sensor_data = ulab.numpy.array(range(n * n)).reshape((n, n))  # Color index narray
grid_data = ulab.numpy.zeros(((2 * n) - 1, (2 * n) - 1))  # 15x15 color index narray
histogram = ulab.numpy.zeros((2 * n) - 1)  # Histogram accumulation narray

# Convert default alarm and min/max range values from config file
ALARM_C = fahrenheit_to_celsius(ALARM_F)
MIN_RANGE_C = fahrenheit_to_celsius(MIN_RANGE_F)
MAX_RANGE_C = fahrenheit_to_celsius(MAX_RANGE_F)

# The board's integral display size
WIDTH = display.width
HEIGHT = display.height

GRID_AXIS = (2 * n) - 1  # Number of cells along the grid x or y axis
GRID_SIZE = HEIGHT  # Maximum number of pixels for a square grid
GRID_X_OFFSET = WIDTH - GRID_SIZE  # Right-align grid with display boundary
CELL_SIZE = GRID_SIZE // GRID_AXIS  # Size of a grid cell in pixels

PALETTE_SIZE = 100  # Number of colors in spectral palette (must be > 0)

# Default colors for temperature value sidebar
BLACK = 0x000000
RED = 0xFF0000
YELLOW = 0xFFFF00
CYAN = 0x00FFFF
BLUE = 0x0000FF
WHITE = 0xFFFFFF

# Text colors for setup helper's on-screen parameters
param_colors = [("ALARM", WHITE), ("RANGE", RED), ("RANGE", CYAN)]

# ### Helpers ###
def play_tone(freq=440, duration=0.01):
    tone(board.A0, freq, duration)
    return


def flash_status(text="", duration=0.05):  # Flash status message once
    status_label.color = WHITE
    status_label.text = text
    time.sleep(duration)
    status_label.color = BLACK
    time.sleep(duration)
    status_label.text = ""
    return


def spectrum():  # Load a test spectrum into the grid_data array
    for row in range(0, GRID_AXIS):
        for col in range(0, GRID_AXIS):
            grid_data[row][col] = ((row * GRID_AXIS) + col) * 1 / 235
    return


def update_image_frame(selfie=False):  # Get camera data and update display
    for row in range(0, GRID_AXIS):
        for col in range(0, GRID_AXIS):
            if selfie:
                color_index = grid_data[GRID_AXIS - 1 - row][col]
            else:
                color_index = grid_data[GRID_AXIS - 1 - row][GRID_AXIS - 1 - col]
            color = index_to_rgb(round(color_index * PALETTE_SIZE, 0) / PALETTE_SIZE)
            if color != image_group[((row * GRID_AXIS) + col)].fill:
                image_group[((row * GRID_AXIS) + col)].fill = color
    return


def update_histo_frame():  # Calculate and display histogram
    min_histo.text = str(MIN_RANGE_F)  # Display histogram legend
    max_histo.text = str(MAX_RANGE_F)

    histogram = ulab.numpy.zeros(GRID_AXIS)  # Clear histogram accumulation array
    for row in range(0, GRID_AXIS):  # Collect camera data and calculate histo
        for col in range(0, GRID_AXIS):
            histo_index = int(map_range(grid_data[col, row], 0, 1, 0, GRID_AXIS - 1))
            histogram[histo_index] = histogram[histo_index] + 1

    histo_scale = ulab.numpy.max(histogram) / (GRID_AXIS - 1)
    if histo_scale <= 0:
        histo_scale = 1

    for col in range(0, GRID_AXIS):  # Display histogram
        for row in range(0, GRID_AXIS):
            if histogram[col] / histo_scale > GRID_AXIS - 1 - row:
                image_group[((row * GRID_AXIS) + col)].fill = index_to_rgb(
                    round((col / GRID_AXIS), 3)
                )
            else:
                image_group[((row * GRID_AXIS) + col)].fill = BLACK
    return


def ulab_bilinear_interpolation():  # 2x bilinear interpolation
    # Upscale sensor data array; by @v923z and @David.Glaude
    grid_data[1::2, ::2] = sensor_data[:-1, :]
    grid_data[1::2, ::2] += sensor_data[1:, :]
    grid_data[1::2, ::2] /= 2
    grid_data[::, 1::2] = grid_data[::, :-1:2]
    grid_data[::, 1::2] += grid_data[::, 2::2]
    grid_data[::, 1::2] /= 2
    return


def setup_mode():  # Set alarm threshold and minimum/maximum range values
    status_label.color = WHITE
    status_label.text = "-SET-"

    ave_label.color = BLACK  # Turn off average label and value display
    ave_value.color = BLACK

    max_value.text = str(MAX_RANGE_F)  # Display maximum range value
    min_value.text = str(MIN_RANGE_F)  # Display minimum range value

    time.sleep(0.8)  # Show SET status text before setting parameters
    status_label.text = ""  # Clear status text

    param_index = 0  # Reset index of parameter to set

    # Select parameter to set

    buttons = panel.get_pressed()
    while not buttons & BUTTON_START:
        buttons = panel.get_pressed()
        while (not buttons & BUTTON_A) and (not buttons & BUTTON_START):
            up, down = move_buttons(joystick=has_joystick)
            if up:
                param_index = param_index - 1
            if down:
                param_index = param_index + 1
            param_index = max(0, min(2, param_index))
            status_label.text = param_colors[param_index][0]
            image_group[param_index + 226].color = BLACK
            status_label.color = BLACK
            time.sleep(0.25)
            image_group[param_index + 226].color = param_colors[param_index][1]
            status_label.color = WHITE
            time.sleep(0.25)
            buttons = panel.get_pressed()

        buttons = panel.get_pressed()
        if buttons & BUTTON_A:  # Hold (button A) pressed
            play_tone(1319, 0.030)  # E6
        while buttons & BUTTON_A:  # Wait for button release
            buttons = panel.get_pressed()
            time.sleep(0.1)

        # Adjust parameter value
        param_value = int(image_group[param_index + 230].text)
        buttons = panel.get_pressed()
        while (not buttons & BUTTON_A) and (not buttons & BUTTON_START):
            up, down = move_buttons(joystick=has_joystick)
            if up:
                param_value = param_value + 1
            if down:
                param_value = param_value - 1
            param_value = max(32, min(157, param_value))
            image_group[param_index + 230].text = str(param_value)
            image_group[param_index + 230].color = BLACK
            status_label.color = BLACK
            time.sleep(0.05)
            image_group[param_index + 230].color = param_colors[param_index][1]
            status_label.color = WHITE
            time.sleep(0.2)
            buttons = panel.get_pressed()

        buttons = panel.get_pressed()
        if buttons & BUTTON_A:  # Button A pressed
            play_tone(1319, 0.030)  # E6
        while buttons & BUTTON_A:  # Wait for button release
            buttons = panel.get_pressed()
            time.sleep(0.1)

    # Exit setup process
    buttons = panel.get_pressed()
    if buttons & BUTTON_START:  # Start button pressed
        play_tone(784, 0.030)  # G5
    while buttons & BUTTON_START:  # Wait for button release
        buttons = panel.get_pressed()
        time.sleep(0.1)

    status_label.text = "RESUME"
    time.sleep(0.5)
    status_label.text = ""

    # Display average label and value
    ave_label.color = YELLOW
    ave_value.color = YELLOW
    return int(alarm_value.text), int(max_value.text), int(min_value.text)


def move_buttons(joystick=False):  # Read position buttons and joystick
    move_u = move_d = False
    if joystick:  # For PyGamer: interpret joystick as buttons
        if joystick_y.value < 20000:
            move_u = True
        elif joystick_y.value > 44000:
            move_d = True
    else:  # For PyBadge read the buttons
        buttons = panel.get_pressed()
        if buttons & BUTTON_UP:
            move_u = True
        if buttons & BUTTON_DOWN:
            move_d = True
    return move_u, move_d


play_tone(440, 0.1)  # A4
play_tone(880, 0.1)  # A5

# ### Define the display group ###
t0 = time.monotonic()  # Time marker: Define Display Elements
image_group = displayio.Group(scale=1)

# Define the foundational thermal image grid cells; image_group[0:224]
#   image_group[#] = image_group[ (row * GRID_AXIS) + column ]
for row in range(0, GRID_AXIS):
    for col in range(0, GRID_AXIS):
        cell_x = (col * CELL_SIZE) + GRID_X_OFFSET
        cell_y = row * CELL_SIZE
        cell = Rect(
            x=cell_x,
            y=cell_y,
            width=CELL_SIZE,
            height=CELL_SIZE,
            fill=None,
            outline=None,
            stroke=0,
        )
        image_group.append(cell)

# Define labels and values
status_label = Label(font_0, text="", color=None)
status_label.anchor_point = (0.5, 0.5)
status_label.anchored_position = ((WIDTH // 2) + (GRID_X_OFFSET // 2), HEIGHT // 2)
image_group.append(status_label)  # image_group[225]

alarm_label = Label(font_0, text="alm", color=WHITE)
alarm_label.anchor_point = (0, 0)
alarm_label.anchored_position = (1, 16)
image_group.append(alarm_label)  # image_group[226]

max_label = Label(font_0, text="max", color=RED)
max_label.anchor_point = (0, 0)
max_label.anchored_position = (1, 46)
image_group.append(max_label)  # image_group[227]

min_label = Label(font_0, text="min", color=CYAN)
min_label.anchor_point = (0, 0)
min_label.anchored_position = (1, 106)
image_group.append(min_label)  # image_group[228]

ave_label = Label(font_0, text="ave", color=YELLOW)
ave_label.anchor_point = (0, 0)
ave_label.anchored_position = (1, 76)
image_group.append(ave_label)  # image_group[229]

alarm_value = Label(font_0, text=str(ALARM_F), color=WHITE)
alarm_value.anchor_point = (0, 0)
alarm_value.anchored_position = (1, 5)
image_group.append(alarm_value)  # image_group[230]

max_value = Label(font_0, text=str(MAX_RANGE_F), color=RED)
max_value.anchor_point = (0, 0)
max_value.anchored_position = (1, 35)
image_group.append(max_value)  # image_group[231]

min_value = Label(font_0, text=str(MIN_RANGE_F), color=CYAN)
min_value.anchor_point = (0, 0)
min_value.anchored_position = (1, 95)
image_group.append(min_value)  # image_group[232]

ave_value = Label(font_0, text="---", color=YELLOW)
ave_value.anchor_point = (0, 0)
ave_value.anchored_position = (1, 65)
image_group.append(ave_value)  # image_group[233]

min_histo = Label(font_0, text="", color=None)
min_histo.anchor_point = (0, 0.5)
min_histo.anchored_position = (GRID_X_OFFSET, 121)
image_group.append(min_histo)  # image_group[234]

max_histo = Label(font_0, text="", color=None)
max_histo.anchor_point = (1, 0.5)
max_histo.anchored_position = (WIDTH - 2, 121)
image_group.append(max_histo)  # image_group[235]

range_histo = Label(font_0, text="-RANGE-", color=None)
range_histo.anchor_point = (0.5, 0.5)
range_histo.anchored_position = ((WIDTH // 2) + (GRID_X_OFFSET // 2), 121)
image_group.append(range_histo)  # image_group[236]

# ###--- PRIMARY PROCESS SETUP ---###
t1 = time.monotonic()  # Time marker: Primary Process Setup
fm1 = gc.mem_free()  # Monitor free memory
display_image = True  # Image display mode; False for histogram
display_hold = False  # Active display mode; True to hold display
display_focus = False  # Standard display range; True to focus display range
orig_max_range_f = 0  # Establish temporary range variables
orig_min_range_f = 0

# Activate display and play welcome tone
display.show(image_group)
spectrum()
update_image_frame()
flash_status("IRON", 0.75)
play_tone(880, 0.010)  # A5

# ###--- PRIMARY PROCESS LOOP ---###
while True:
    t2 = time.monotonic()  # Time marker: Acquire Sensor Data
    if display_hold:
        flash_status("-HOLD-", 0.25)
    else:
        sensor = amg8833.pixels  # Get sensor_data data
    sensor_data = ulab.numpy.array(sensor)  # Copy to narray

    t3 = time.monotonic()  # Time marker: Constrain Sensor Values
    for row in range(0, 8):
        for col in range(0, 8):
            sensor_data[col, row] = min(max(sensor_data[col, row], 0), 80)

    # Update and display alarm setting and max, min, and ave stats
    t4 = time.monotonic()  # Time marker: Display Statistics
    v_max = ulab.numpy.max(sensor_data)
    v_min = ulab.numpy.min(sensor_data)
    v_ave = ulab.numpy.mean(sensor_data)

    alarm_value.text = str(ALARM_F)
    max_value.text = str(celsius_to_fahrenheit(v_max))
    min_value.text = str(celsius_to_fahrenheit(v_min))
    ave_value.text = str(celsius_to_fahrenheit(v_ave))

    # Normalize temperature to index values and interpolate
    t5 = time.monotonic()  # Time marker: Normalize and Interpolate
    sensor_data = (sensor_data - MIN_RANGE_C) / (MAX_RANGE_C - MIN_RANGE_C)
    grid_data[::2, ::2] = sensor_data  # Copy sensor data to the grid array
    ulab_bilinear_interpolation()  # Interpolate to produce 15x15 result

    # Display image or histogram
    t6 = time.monotonic()  # Time marker: Display Image
    if display_image:
        update_image_frame(selfie=SELFIE)
    else:
        update_histo_frame()

    # If alarm threshold is reached, flash NeoPixels and play alarm tone
    if v_max >= ALARM_C:
        pixels.fill(RED)
        play_tone(880, 0.015)  # A5
        pixels.fill(BLACK)

    # See if a panel button is pressed
    buttons = panel.get_pressed()
    if buttons & BUTTON_A:  # Toggle display hold (shutter)
        play_tone(1319, 0.030)  # E6
        display_hold = not display_hold

        while buttons & BUTTON_A:
            buttons = panel.get_pressed()
            time.sleep(0.1)

    if buttons & BUTTON_B:  # Toggle image/histogram mode (display image)
        play_tone(659, 0.030)  # E5
        display_image = not display_image
        while buttons & BUTTON_B:
            buttons = panel.get_pressed()
            time.sleep(0.1)

        if display_image:
            min_histo.color = None
            max_histo.color = None
            range_histo.color = None
        else:
            min_histo.color = CYAN
            max_histo.color = RED
            range_histo.color = BLUE

    if buttons & BUTTON_SELECT:  # Toggle focus mode (display focus)
        play_tone(698, 0.030)  # F5
        display_focus = not display_focus
        if display_focus:
            # Set range values to image min/max for focused image display
            orig_min_range_f = MIN_RANGE_F
            orig_max_range_f = MAX_RANGE_F
            MIN_RANGE_F = celsius_to_fahrenheit(v_min)
            MAX_RANGE_F = celsius_to_fahrenheit(v_max)
            # Update range min and max values in Celsius
            MIN_RANGE_C = v_min
            MAX_RANGE_C = v_max
            flash_status("FOCUS", 0.2)
        else:
            # Restore previous (original) range values for image display
            MIN_RANGE_F = orig_min_range_f
            MAX_RANGE_F = orig_max_range_f
            # Update range min and max values in Celsius
            MIN_RANGE_C = fahrenheit_to_celsius(MIN_RANGE_F)
            MAX_RANGE_C = fahrenheit_to_celsius(MAX_RANGE_F)
            flash_status("ORIG", 0.2)

        while buttons & BUTTON_SELECT:
            buttons = panel.get_pressed()
            time.sleep(0.1)

    if buttons & BUTTON_START:  # Activate setup mode
        play_tone(784, 0.030)  # G5
        while buttons & BUTTON_START:
            buttons = panel.get_pressed()
            time.sleep(0.1)

        # Invoke startup helper; update alarm and range values
        ALARM_F, MAX_RANGE_F, MIN_RANGE_F = setup_mode()
        ALARM_C = fahrenheit_to_celsius(ALARM_F)
        MIN_RANGE_C = fahrenheit_to_celsius(MIN_RANGE_F)
        MAX_RANGE_C = fahrenheit_to_celsius(MAX_RANGE_F)

    t7 = time.monotonic()  # Time marker: End of Primary Process
    gc.collect()
    fm7 = gc.mem_free()
    print("*** PyBadge/Gamer Performance Stats ***")
    print(f"    define displayio:      {(t1 - t0):6.3f} sec")
    print(f"    startup free memory: {fm1/1000:6.3} Kb")
    print("")
    print(
        f" 1) data acquisition: {(t4 - t2):6.3f}      rate:  {(1 / (t4 - t2)):5.1f} /sec"
    )
    print(f" 2) display stats:    {(t5 - t4):6.3f}")
    print(f" 3) interpolate:      {(t6 - t5):6.3f}")
    print(f" 4) display image:    {(t7 - t6):6.3f}")
    print(f"                     =======")
    print(
        f"total frame:          {(t7 - t2):6.3f} sec  rate:  {(1 / (t7 - t2)):5.1f} /sec"
    )
    print(f"                           free memory: {fm7/1000:6.3} Kb")
    print("")
