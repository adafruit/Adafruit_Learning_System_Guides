# SPDX-FileCopyrightText: 2022 Jan Goolsbey for Adafruit Industries
# SPDX-License-Identifier: MIT
#
# clue_scale_code.py
# 2022-07-29 v1.2.0
#
# Clue Scale - Single Channel Version
# Adafruit NAU7802 Stemma breakout example

# import clue_scale_calibrator  # Uncomment to run calibrator method

import time
import board
from simpleio import map_range
from adafruit_clue import clue
from adafruit_display_shapes.circle import Circle
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
import displayio
from cedargrove_nau7802 import NAU7802

clue.pixel.brightness = 0.2  # Set NeoPixel brightness
clue.pixel[0] = clue.YELLOW  # Set status indicator to yellow (initializing)

# Set Scale Defaults
MAX_GR = 100  # Maximum (full-scale) display range in grams
DEFAULT_GAIN = 128  # Default gain for internal PGA
SAMPLE_AVG = 100  # Number of sample values to average
SCALE_NAME_1 = "COFFEE"  # 6 characters maximum
SCALE_NAME_2 = "SCALE"  # 6 characters maximum

"""Enter the calibration ratio for the individual load cell in-use. The ratio is
composed of the reference weight in grams divided by the raw reading. For
example, a raw reading of 215300 for a 100 gram weight results in a calibration
ratio of 100 / 215300. Use the clue_scale_single_calibrate method to obtain the
raw value.
FYI: A US dime coin weighs 2.268 grams or 0.079 ounces."""
CALIB_RATIO = 100 / 215300  # load cell serial#4540-02

# Instantiate the Sensor and Display
nau7802 = NAU7802(board.I2C(), address=0x2A, active_channels=1)

display = board.DISPLAY
scale_group = displayio.Group()

FONT_0 = bitmap_font.load_font("/fonts/Helvetica-Bold-24.bdf")
FONT_1 = bitmap_font.load_font("/fonts/OpenSans-16.bdf")
FONT_2 = bitmap_font.load_font("/fonts/OpenSans-9.bdf")

# Display the Background Bitmap Image
bkg = displayio.OnDiskBitmap("/clue_scale_bkg.bmp")
_background = displayio.TileGrid(bkg, pixel_shader=bkg.pixel_shader, x=0, y=0)
scale_group.append(_background)

# Define and Display the Text Labels and Graphic Elements
# Place the project name on either side of the graduated scale
scale_name_1 = Label(FONT_1, text=SCALE_NAME_1, color=clue.CYAN)
scale_name_1.anchor_point = (0.5, 0.5)
scale_name_1.anchored_position = (40, 96)
scale_group.append(scale_name_1)

scale_name_2 = Label(FONT_1, text=SCALE_NAME_2, color=clue.CYAN)
scale_name_2.anchor_point = (0.5, 0.5)
scale_name_2.anchored_position = (199, 96)
scale_group.append(scale_name_2)

# Define the zeroing button graphic
zero_button_circle = Circle(14, 152, 14, fill=None, outline=clue.RED, stroke=2)
scale_group.append(zero_button_circle)

zero_button_label = Label(FONT_1, text="Z", color=clue.RED)
zero_button_label.x = 8
zero_button_label.y = 150
scale_group.append(zero_button_label)

# Place tickmark labels next to the graduated scale
for i in range(-1, 6):
    tick_value = Label(FONT_2, text=str((MAX_GR) // 5 * i), color=clue.CYAN)
    if i == -1:
        tick_value.anchor_point = (1.0, 1.1)
    elif i == 5:
        tick_value.anchor_point = (1.0, 0.0)
    else:
        tick_value.anchor_point = (1.0, 0.5)
    tick_value.anchored_position = (99, 201 - (i * 40))
    scale_group.append(tick_value)

# Place the grams and ounces labels and values near the bottom of the display
grams_label = Label(FONT_0, text="grams", color=clue.BLUE)
grams_label.anchor_point = (1.0, 0)
grams_label.anchored_position = (80, 216)
scale_group.append(grams_label)

ounces_label = Label(FONT_0, text="ounces", color=clue.BLUE)
ounces_label.anchor_point = (1.0, 0)
ounces_label.anchored_position = (230, 216)
scale_group.append(ounces_label)

grams_value = Label(FONT_0, text="0.0", color=clue.WHITE)
grams_value.anchor_point = (1.0, 0.5)
grams_value.anchored_position = (80, 200)
scale_group.append(grams_value)

ounces_value = Label(FONT_0, text="0.00", color=clue.WHITE)
ounces_value.anchor_point = (1.0, 0.5)
ounces_value.anchored_position = (230, 200)
scale_group.append(ounces_value)

# Define the moveable indicator bubble
indicator_group = displayio.Group()
bubble = Circle(120, 200, 10, fill=clue.YELLOW, outline=clue.YELLOW, stroke=3)
indicator_group.append(bubble)

scale_group.append(indicator_group)
display.show(scale_group)


# Helpers
def zero_channel():
    """Prepare internal amplifier settings and zero the current channel. Use
    after power-up, a new channel is selected, or to adjust for measurement
    drift. Can be used to zero the scale with a tare weight.
    The nau7802.calibrate function used here does not calibrate the load cell,
    but sets the NAU7802 internals to prepare for measuring input signals."""
    nau7802.calibrate("INTERNAL")
    nau7802.calibrate("OFFSET")


def read(samples=100):
    """Read and average consecutive raw samples; return averaged value."""
    sample_sum = 0
    sample_count = samples
    while sample_count > 0:
        if nau7802.available:
            sample_sum = sample_sum + nau7802.read()
            sample_count -= 1
    return int(sample_sum / samples)


# Activate the Sensor
# Enable the internal analog circuitry, set gain, and zero
nau7802.enable(True)
nau7802.gain = DEFAULT_GAIN
zero_channel()

# Play "welcome" tones
clue.play_tone(1660, 0.15)
clue.play_tone(1440, 0.15)

# The Primary Code Loop
# Read sensor, move bubble, and display values
while True:
    clue.pixel[0] = clue.GREEN  # Set status indicator to green (ready)

    # Read the raw scale value and scale for grams and ounces
    value = read(SAMPLE_AVG)
    mass_grams = round(value * CALIB_RATIO, 1)
    mass_ounces = round(mass_grams * 0.03527, 2)
    grams_value.text = f"{mass_grams:5.1f}"
    ounces_value.text = f"{mass_ounces:5.2f}"
    print(f" {mass_grams:5.1f} grams   {mass_ounces:5.2f} ounces")

    # Reposition the indicator bubble based on grams value
    min_gr = (MAX_GR // 5) * -1  # Minimum display value
    bubble.y = int(map_range(mass_grams, min_gr, MAX_GR, 240, 0)) - 10
    if mass_grams > MAX_GR or mass_grams < min_gr:
        bubble.fill = clue.RED
    else:
        bubble.fill = None

    # Check to see if the zeroing button is pressed
    if clue.button_a:
        # Zero the sensor
        clue.pixel[0] = clue.RED  # Set status indicator to red (stopped)
        bubble.fill = clue.RED  # Set bubble center to red (stopped)
        clue.play_tone(1660, 0.3)  # Play "button pressed" tone

        zero_channel()

        while clue.button_a:
            # Wait until the button is released
            time.sleep(0.1)

        clue.play_tone(1440, 0.5)  # Play "reset completed" tone
        bubble.fill = None  # Set bubble center to transparent (ready)
