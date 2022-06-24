# SPDX-FileCopyrightText: 2020 Richard Albritton for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import microcontroller
import displayio
import busio
from analogio import AnalogIn
import neopixel
import adafruit_adt7410
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.label import Label
from adafruit_button import Button
import adafruit_touchscreen
from adafruit_pyportal import PyPortal

# ------------- Constants ------------- #
# Sound Effects
soundDemo = "/sounds/sound.wav"
soundBeep = "/sounds/beep.wav"
soundTab = "/sounds/tab.wav"

# Hex Colors
WHITE = 0xFFFFFF
RED = 0xFF0000
YELLOW = 0xFFFF00
GREEN = 0x00FF00
BLUE = 0x0000FF
PURPLE = 0xFF00FF
BLACK = 0x000000

# Default Label styling
TABS_X = 0
TABS_Y = 15

# Default button styling:
BUTTON_HEIGHT = 40
BUTTON_WIDTH = 80

# Default State
view_live = 1
icon = 1
icon_name = "Ruby"
button_mode = 1
switch_state = 0

# ------------- Functions ------------- #
# Backlight function
# Value between 0 and 1 where 0 is OFF, 0.5 is 50% and 1 is 100% brightness.
def set_backlight(val):
    val = max(0, min(1.0, val))
    board.DISPLAY.auto_brightness = False
    board.DISPLAY.brightness = val


# Helper for cycling through a number set of 1 to x.
def numberUP(num, max_val):
    num += 1
    if num <= max_val:
        return num
    else:
        return 1


# Set visibility of layer
def layerVisibility(state, layer, target):
    try:
        if state == "show":
            time.sleep(0.1)
            layer.append(target)
        elif state == "hide":
            layer.remove(target)
    except ValueError:
        pass


# This will handle switching Images and Icons
def set_image(group, filename):
    """Set the image file for a given goup for display.
    This is most useful for Icons or image slideshows.
        :param group: The chosen group
        :param filename: The filename of the chosen image
    """
    print("Set image to ", filename)
    if group:
        group.pop()

    if not filename:
        return  # we're done, no icon desired

    # CircuitPython 6 & 7 compatible
    image_file = open(filename, "rb")
    image = displayio.OnDiskBitmap(image_file)
    image_sprite = displayio.TileGrid(
        image, pixel_shader=getattr(image, "pixel_shader", displayio.ColorConverter())
    )

    # # CircuitPython 7+ compatible
    # image = displayio.OnDiskBitmap(filename)
    # image_sprite = displayio.TileGrid(image, pixel_shader=image.pixel_shader)

    group.append(image_sprite)


# return a reformatted string with word wrapping using PyPortal.wrap_nicely
def text_box(target, top, string, max_chars):
    text = pyportal.wrap_nicely(string, max_chars)
    new_text = ""
    test = ""

    for w in text:
        new_text += "\n" + w
        test += "M\n"

    text_height = Label(font, text="M", color=0x03AD31)
    text_height.text = test  # Odd things happen without this
    glyph_box = text_height.bounding_box
    target.text = ""  # Odd things happen without this
    target.y = int(glyph_box[3] / 2) + top
    target.text = new_text


def get_Temperature(source):
    if source:  # Only if we have the temperature sensor
        celsius = source.temperature
    else:  # No temperature sensor
        celsius = microcontroller.cpu.temperature
    return (celsius * 1.8) + 32


# ------------- Inputs and Outputs Setup ------------- #
light_sensor = AnalogIn(board.LIGHT)
try:
    # attempt to init. the temperature sensor
    i2c_bus = busio.I2C(board.SCL, board.SDA)
    adt = adafruit_adt7410.ADT7410(i2c_bus, address=0x48)
    adt.high_resolution = True
except ValueError:
    # Did not find ADT7410. Probably running on Titano or Pynt
    adt = None

# ------------- Screen Setup ------------- #
pyportal = PyPortal()
pyportal.set_background("/images/loading.bmp")  # Display an image until the loop starts
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=1)

# Touchscreen setup  [ Rotate 270 ]
display = board.DISPLAY
display.rotation = 270

if board.board_id == "pyportal_titano":
    screen_width = 320
    screen_height = 480
    set_backlight(
        1
    )  # 0.3 brightness does not cause the display to be visible on the Titano
else:
    screen_width = 240
    screen_height = 320
    set_backlight(0.3)

# We want three buttons across the top of the screen
TAB_BUTTON_Y = 0
TAB_BUTTON_HEIGHT = 40
TAB_BUTTON_WIDTH = int(screen_width / 3)

# We want two big buttons at the bottom of the screen
BIG_BUTTON_HEIGHT = int(screen_height / 3.2)
BIG_BUTTON_WIDTH = int(screen_width / 2)
BIG_BUTTON_Y = int(screen_height - BIG_BUTTON_HEIGHT)

# Initializes the display touch screen area
ts = adafruit_touchscreen.Touchscreen(
    board.TOUCH_YD,
    board.TOUCH_YU,
    board.TOUCH_XR,
    board.TOUCH_XL,
    calibration=((5200, 59000), (5800, 57000)),
    size=(screen_width, screen_height),
)

# ------------- Display Groups ------------- #
splash = displayio.Group()  # The Main Display Group
view1 = displayio.Group()  # Group for View 1 objects
view2 = displayio.Group()  # Group for View 2 objects
view3 = displayio.Group()  # Group for View 3 objects

# ------------- Setup for Images ------------- #
bg_group = displayio.Group()
splash.append(bg_group)
set_image(bg_group, "/images/BGimage.bmp")

icon_group = displayio.Group()
icon_group.x = 180
icon_group.y = 120
icon_group.scale = 1
view2.append(icon_group)

# ---------- Text Boxes ------------- #
# Set the font and preload letters
font = bitmap_font.load_font("/fonts/Helvetica-Bold-16.bdf")
font.load_glyphs(b"abcdefghjiklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890- ()")

# Text Label Objects
feed1_label = Label(font, text="Text Window 1", color=0xE39300)
feed1_label.x = TABS_X
feed1_label.y = TABS_Y
view1.append(feed1_label)

feed2_label = Label(font, text="Text Window 2", color=0xFFFFFF)
feed2_label.x = TABS_X
feed2_label.y = TABS_Y
view2.append(feed2_label)

sensors_label = Label(font, text="Data View", color=0x03AD31)
sensors_label.x = TABS_X
sensors_label.y = TABS_Y
view3.append(sensors_label)

sensor_data = Label(font, text="Data View", color=0x03AD31)
sensor_data.x = TABS_X + 16  # Indents the text layout
sensor_data.y = 150
view3.append(sensor_data)

# ---------- Display Buttons ------------- #
# This group will make it easy for us to read a button press later.
buttons = []

# Main User Interface Buttons
button_view1 = Button(
    x=0,  # Start at furthest left
    y=0,  # Start at top
    width=TAB_BUTTON_WIDTH,  # Calculated width
    height=TAB_BUTTON_HEIGHT,  # Static height
    label="View 1",
    label_font=font,
    label_color=0xFF7E00,
    fill_color=0x5C5B5C,
    outline_color=0x767676,
    selected_fill=0x1A1A1A,
    selected_outline=0x2E2E2E,
    selected_label=0x525252,
)
buttons.append(button_view1)  # adding this button to the buttons group

button_view2 = Button(
    x=TAB_BUTTON_WIDTH,  # Start after width of a button
    y=0,
    width=TAB_BUTTON_WIDTH,
    height=TAB_BUTTON_HEIGHT,
    label="View 2",
    label_font=font,
    label_color=0xFF7E00,
    fill_color=0x5C5B5C,
    outline_color=0x767676,
    selected_fill=0x1A1A1A,
    selected_outline=0x2E2E2E,
    selected_label=0x525252,
)
buttons.append(button_view2)  # adding this button to the buttons group

button_view3 = Button(
    x=TAB_BUTTON_WIDTH * 2,  # Start after width of 2 buttons
    y=0,
    width=TAB_BUTTON_WIDTH,
    height=TAB_BUTTON_HEIGHT,
    label="View 3",
    label_font=font,
    label_color=0xFF7E00,
    fill_color=0x5C5B5C,
    outline_color=0x767676,
    selected_fill=0x1A1A1A,
    selected_outline=0x2E2E2E,
    selected_label=0x525252,
)
buttons.append(button_view3)  # adding this button to the buttons group

button_switch = Button(
    x=0,  # Start at furthest left
    y=BIG_BUTTON_Y,
    width=BIG_BUTTON_WIDTH,
    height=BIG_BUTTON_HEIGHT,
    label="Light Switch",
    label_font=font,
    label_color=0xFF7E00,
    fill_color=0x5C5B5C,
    outline_color=0x767676,
    selected_fill=0x1A1A1A,
    selected_outline=0x2E2E2E,
    selected_label=0x525252,
)
buttons.append(button_switch)  # adding this button to the buttons group

button_2 = Button(
    x=BIG_BUTTON_WIDTH,  # Starts just after button 1 width
    y=BIG_BUTTON_Y,
    width=BIG_BUTTON_WIDTH,
    height=BIG_BUTTON_HEIGHT,
    label="Light Color",
    label_font=font,
    label_color=0xFF7E00,
    fill_color=0x5C5B5C,
    outline_color=0x767676,
    selected_fill=0x1A1A1A,
    selected_outline=0x2E2E2E,
    selected_label=0x525252,
)
buttons.append(button_2)  # adding this button to the buttons group

# Add all of the main buttons to the splash Group
for b in buttons:
    splash.append(b)

# Make a button to change the icon image on view2
button_icon = Button(
    x=150,
    y=60,
    width=BUTTON_WIDTH,
    height=BUTTON_HEIGHT,
    label="Icon",
    label_font=font,
    label_color=0xFFFFFF,
    fill_color=0x8900FF,
    outline_color=0xBC55FD,
    selected_fill=0x5A5A5A,
    selected_outline=0xFF6600,
    selected_label=0x525252,
    style=Button.ROUNDRECT,
)
buttons.append(button_icon)  # adding this button to the buttons group

# Add this button to view2 Group
view2.append(button_icon)

# Make a button to play a sound on view2
button_sound = Button(
    x=150,
    y=170,
    width=BUTTON_WIDTH,
    height=BUTTON_HEIGHT,
    label="Sound",
    label_font=font,
    label_color=0xFFFFFF,
    fill_color=0x8900FF,
    outline_color=0xBC55FD,
    selected_fill=0x5A5A5A,
    selected_outline=0xFF6600,
    selected_label=0x525252,
    style=Button.ROUNDRECT,
)
buttons.append(button_sound)  # adding this button to the buttons group

# Add this button to view2 Group
view3.append(button_sound)

# pylint: disable=global-statement
def switch_view(what_view):
    global view_live
    if what_view == 1:
        button_view1.selected = False
        button_view2.selected = True
        button_view3.selected = True
        layerVisibility("hide", splash, view2)
        layerVisibility("hide", splash, view3)
        layerVisibility("show", splash, view1)
    elif what_view == 2:
        # global icon
        button_view1.selected = True
        button_view2.selected = False
        button_view3.selected = True
        layerVisibility("hide", splash, view1)
        layerVisibility("hide", splash, view3)
        layerVisibility("show", splash, view2)
    else:
        button_view1.selected = True
        button_view2.selected = True
        button_view3.selected = False
        layerVisibility("hide", splash, view1)
        layerVisibility("hide", splash, view2)
        layerVisibility("show", splash, view3)

    # Set global button state
    view_live = what_view
    print("View {view_num:.0f} On".format(view_num=what_view))


# pylint: enable=global-statement

# Set veriables and startup states
button_view1.selected = False
button_view2.selected = True
button_view3.selected = True
button_switch.label = "OFF"
button_switch.selected = True

layerVisibility("show", splash, view1)
layerVisibility("hide", splash, view2)
layerVisibility("hide", splash, view3)

# Update out Labels with display text.
text_box(
    feed1_label,
    TABS_Y,
    "The text on this screen is wrapped so that all of it fits nicely into a "
    "text box that is {} x {}.".format(
        feed1_label.bounding_box[2], feed1_label.bounding_box[3] * 2
    ),
    30,
)

text_box(feed2_label, TABS_Y, "Tap on the Icon button to meet a new friend.", 18)

text_box(
    sensors_label,
    TABS_Y,
    "This screen can display sensor readings and tap Sound to play a WAV file.",
    28,
)

board.DISPLAY.show(splash)


# ------------- Code Loop ------------- #
while True:
    touch = ts.touch_point
    light = light_sensor.value
    sensor_data.text = "Touch: {}\nLight: {}\nTemp: {:.0f}°F".format(
        touch, light, get_Temperature(adt)
    )

    # Will also cause screen to dim when hand is blocking sensor to touch screen
    #    # Adjust backlight
    #    if light < 1500:
    #        set_backlight(0.1)
    #    elif light < 3000:
    #        set_backlight(0.5)
    #    else:
    #        set_backlight(1)

    # ------------- Handle Button Press Detection  ------------- #
    if touch:  # Only do this if the screen is touched
        # loop with buttons using enumerate() to number each button group as i
        for i, b in enumerate(buttons):
            if b.contains(touch):  # Test each button to see if it was pressed
                print("button{} pressed".format(i))
                if i == 0 and view_live != 1:  # only if view1 is visible
                    pyportal.play_file(soundTab)
                    switch_view(1)
                    while ts.touch_point:
                        pass
                if i == 1 and view_live != 2:  # only if view2 is visible
                    pyportal.play_file(soundTab)
                    switch_view(2)
                    while ts.touch_point:
                        pass
                if i == 2 and view_live != 3:  # only if view3 is visible
                    pyportal.play_file(soundTab)
                    switch_view(3)
                    while ts.touch_point:
                        pass
                if i == 3:
                    pyportal.play_file(soundBeep)
                    # Toggle switch button type
                    if switch_state == 0:
                        switch_state = 1
                        b.label = "ON"
                        b.selected = False
                        pixel.fill(WHITE)
                        print("Switch ON")
                    else:
                        switch_state = 0
                        b.label = "OFF"
                        b.selected = True
                        pixel.fill(BLACK)
                        print("Switch OFF")
                    # for debounce
                    while ts.touch_point:
                        pass
                    print("Switch Pressed")
                if i == 4:
                    pyportal.play_file(soundBeep)
                    # Momentary button type
                    b.selected = True
                    print("Button Pressed")
                    button_mode = numberUP(button_mode, 5)
                    if button_mode == 1:
                        pixel.fill(RED)
                    elif button_mode == 2:
                        pixel.fill(YELLOW)
                    elif button_mode == 3:
                        pixel.fill(GREEN)
                    elif button_mode == 4:
                        pixel.fill(BLUE)
                    elif button_mode == 5:
                        pixel.fill(PURPLE)
                    switch_state = 1
                    button_switch.label = "ON"
                    button_switch.selected = False
                    # for debounce
                    while ts.touch_point:
                        pass
                    print("Button released")
                    b.selected = False
                if i == 5 and view_live == 2:  # only if view2 is visible
                    pyportal.play_file(soundBeep)
                    b.selected = True
                    while ts.touch_point:
                        pass
                    print("Icon Button Pressed")
                    icon = numberUP(icon, 3)
                    if icon == 1:
                        icon_name = "Ruby"
                    elif icon == 2:
                        icon_name = "Gus"
                    elif icon == 3:
                        icon_name = "Billie"
                    b.selected = False
                    text_box(
                        feed2_label,
                        TABS_Y,
                        "Every time you tap the Icon button the icon image will "
                        "change. Say hi to {}!".format(icon_name),
                        18,
                    )
                    set_image(icon_group, "/images/" + icon_name + ".bmp")
                if i == 6 and view_live == 3:  # only if view3 is visible
                    b.selected = True
                    while ts.touch_point:
                        pass
                    print("Sound Button Pressed")
                    pyportal.play_file(soundDemo)
                    b.selected = False
