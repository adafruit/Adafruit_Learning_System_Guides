import time
from random import choice
import displayio
import adafruit_imageload
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from adafruit_gizmo import tft_gizmo
from adafruit_circuitplayground import cp

#---| User Config |--------------------------------------------------
HEART_MESSAGES = (
    ("I LUV", "YOU"),
    ("SAY", "YES"),
    ("HUG", "ME"),
    ("BE", "MINE"),
    ("TEXT","ME"),
    ("OMG","LOL"),
    ("PEACE",""),
)
HEART_COLORS = (
    0xEAFF50, # yellow
    0xFFAD50, # orange
    0x9D50FF, # purple
    0x13B0FE, # blue
    0xABFF96, # green
    0xFF96FF, # pink
)
MESSAGE_COLORS = (
    0xFF0000, # red
)
#---| User Config |--------------------------------------------------

# Create the TFT Gizmo display
display = tft_gizmo.TFT_Gizmo()

# Load the candy heart BMP
bitmap, palette = adafruit_imageload.load("/heart_bw.bmp",
                                          bitmap=displayio.Bitmap,
                                          palette=displayio.Palette)

heart = displayio.TileGrid(bitmap, pixel_shader=palette)

# Set up message text
font = bitmap_font.load_font("/Multicolore_36.bdf")
line1 = label.Label(font, text="?"*9)
line2 = label.Label(font, text="?"*5)
line1.anchor_point = (0.5, 0)    # middle top
line2.anchor_point = (0.5, 1.0)  # middle bottom

# Set up group and add to display
group = displayio.Group()
group.append(heart)
group.append(line1)
group.append(line2)
display.show(group)

while True:
    # turn off auto refresh while we change some things
    display.auto_refresh = False
    # pick a random message
    line1.text, line2.text = choice(HEART_MESSAGES)
    # update location for new text bounds
    line1.anchored_position = (120, 85)
    line2.anchored_position = (120, 175)
    # pick a random text color
    line1.color = line2.color = choice(MESSAGE_COLORS)
    # pick a ranomd heart color
    palette[1] = choice(HEART_COLORS)
    # OK, now turn auto refresh back on to display
    display.auto_refresh = True
    # wait for button press
    while not cp.button_a and not cp.button_b:
        pass
    # just a little debounce
    time.sleep(0.25)
