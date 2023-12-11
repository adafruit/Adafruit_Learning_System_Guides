# SPDX-FileCopyrightText: 2020 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
This version runs on Feather RP2040 with a 3.5" FeatherWing
"""

import time
import displayio
import terminalio
from adafruit_display_text import bitmap_label
from adafruit_displayio_layout.layouts.grid_layout import GridLayout
from adafruit_displayio_layout.widgets.icon_widget import IconWidget
from adafruit_featherwing import tft_featherwing_35
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.consumer_control import ConsumerControl
from touch_deck_layers import (
    touch_deck_config,
    KEY,
    STRING,
    MEDIA,
    KEY_PRESS,
    KEY_RELEASE,
    CHANGE_LAYER,
)

# seems to help the touchscreen not get stuck with chip not found
time.sleep(3)

# display and touchscreen initialization
displayio.release_displays()
tft_featherwing = tft_featherwing_35.TFTFeatherWing35()
display = tft_featherwing.display
touchscreen = tft_featherwing.touchscreen

# HID setup
kbd = Keyboard(usb_hid.devices)
cc = ConsumerControl(usb_hid.devices)
kbd_layout = KeyboardLayoutUS(kbd)

# variables to enforce timout between icon presses
COOLDOWN_TIME = 0.5
LAST_PRESS_TIME = -1

# 'mock' icon indexes for the layer buttons
# used for debouncing
PREV_LAYER_INDEX = -1
NEXT_LAYER_INDEX = -2
HOME_LAYER_INDEX = -3

# start on first layer
current_layer = 0

# Make the main_group to hold everything
main_group = displayio.Group()
display.root_group = main_group

# loading screen
loading_group = displayio.Group()

# black background, screen size minus side buttons
loading_background = displayio.Bitmap(
    (display.width - 40) // 20, display.height // 20, 1
)
loading_palette = displayio.Palette(1)
loading_palette[0] = 0x0

# scaled group to match screen size minus side buttons
loading_background_scale_group = displayio.Group(scale=20)
loading_background_tilegrid = displayio.TileGrid(
    loading_background, pixel_shader=loading_palette
)
loading_background_scale_group.append(loading_background_tilegrid)

# loading screen label
loading_label = bitmap_label.Label(terminalio.FONT, text="Loading...", scale=3)
loading_label.anchor_point = (0.5, 0.5)
loading_label.anchored_position = (display.width // 2, display.height // 2)

# append background and label to the group
loading_group.append(loading_background_scale_group)
loading_group.append(loading_label)

# GridLayout to hold the icons
# size and location can be adjusted to fit
# different sized screens.
layout = GridLayout(
    x=20,
    y=20,
    width=420,
    height=290,
    grid_size=(4, 3),
    cell_padding=6,
)

# list that holds the IconWidget objects for each icon.
_icons = []

# list that holds indexes of currently pressed icons and layer buttons
# used for debouncing
_pressed_icons = []

# layer label at the top of the screen
layer_label = bitmap_label.Label(terminalio.FONT)
layer_label.anchor_point = (0.5, 0.0)
layer_label.anchored_position = (display.width // 2, 4)
main_group.append(layer_label)

# right side layer buttons
next_layer_btn = IconWidget("", "touch_deck_icons/layer_next.bmp", on_disk=True)
next_layer_btn.x = display.width - 40
next_layer_btn.y = display.height - 100
next_layer_btn.resize = (40, 100)
main_group.append(next_layer_btn)

prev_layer_btn = IconWidget("", "touch_deck_icons/layer_prev.bmp", on_disk=True)
prev_layer_btn.x = display.width - 40
prev_layer_btn.y = 110
prev_layer_btn.resize = (40, 100)
main_group.append(prev_layer_btn)

home_layer_btn = IconWidget("", "touch_deck_icons/layer_home.bmp", on_disk=True)
home_layer_btn.x = display.width - 40
home_layer_btn.y = 0
home_layer_btn.resize = (40, 100)
main_group.append(home_layer_btn)


# helper method to laod icons for an index by its index in the
# list of layers
def load_layer(layer_index):
    # show the loading screen
    main_group.append(loading_group)
    time.sleep(0.05)

    # resets icon lists to empty
    global _icons
    _icons = []
    layout._cell_content_list = []

    # remove previous layer icons from the layout
    while len(layout) > 0:
        layout.pop()

    # set the layer labed at the top of the screen
    layer_label.text = touch_deck_config["layers"][layer_index]["name"]

    # loop over each shortcut and it's index
    for i, shortcut in enumerate(touch_deck_config["layers"][layer_index]["shortcuts"]):
        # create an icon for the current shortcut
        _new_icon = IconWidget(shortcut["label"], shortcut["icon"], on_disk=True)

        # add it to the list of icons
        _icons.append(_new_icon)

        # add it to the grid layout
        # calculate it's position from the index
        layout.add_content(_new_icon, grid_position=(i % 4, i // 4), cell_size=(1, 1))

    # hide the loading screen
    time.sleep(0.05)
    main_group.pop()


# append the grid layout to the main_group
# so it gets shown on the display
main_group.append(layout)

# load the first layer to start
load_layer(current_layer)

#  main loop
while True:
    if touchscreen.touched:
        # loop over all data in touchscreen buffer
        while not touchscreen.buffer_empty:
            touches = touchscreen.touches
            # loop over all points touched
            for point in touches:
                if point:
                    # current time, used for timeout between icon presses
                    _now = time.monotonic()

                    # if the timeout has passed
                    if _now - LAST_PRESS_TIME > COOLDOWN_TIME:
                        # print(point)

                        # map the observed minimum and maximum touch values
                        # to the screen size
                        y = point["y"] - 250
                        x = 4096 - point["x"] - 250
                        y = y * display.width // (3820 - 250)
                        x = x * display.height // (3820 - 250)

                        # touch data is 90 degrees rotated
                        # flip x, and y here to account for that
                        p = (y, x)
                        # print(p)

                        # Next layer button pressed
                        if (
                            next_layer_btn.contains(p)
                            and NEXT_LAYER_INDEX not in _pressed_icons
                        ):

                            # increment layer
                            current_layer += 1
                            # wrap back to beginning from end
                            if current_layer >= len(touch_deck_config["layers"]):
                                current_layer = 0
                            # load the new layer
                            load_layer(current_layer)

                            # save current time to check for timeout
                            LAST_PRESS_TIME = _now

                            # append this index to pressed icons for debouncing
                            _pressed_icons.append(NEXT_LAYER_INDEX)

                        # home layer button pressed
                        if (
                            home_layer_btn.contains(p)
                            and HOME_LAYER_INDEX not in _pressed_icons
                        ):
                            # 0 index is home layer
                            current_layer = 0
                            # load the home layer
                            load_layer(current_layer)

                            # save current time to check for timeout
                            LAST_PRESS_TIME = _now

                            # append this index to pressed icons for debouncing
                            _pressed_icons.append(HOME_LAYER_INDEX)

                        # Previous layer button pressed
                        if (
                            prev_layer_btn.contains(p)
                            and PREV_LAYER_INDEX not in _pressed_icons
                        ):

                            # decrement layer
                            current_layer -= 1
                            # wrap back to end from beginning
                            if current_layer < 0:
                                current_layer = len(touch_deck_config["layers"]) - 1

                            # load the new layer
                            load_layer(current_layer)

                            # save current time to check for timeout
                            LAST_PRESS_TIME = _now

                            # append this index to pressed icons for debouncing
                            _pressed_icons.append(PREV_LAYER_INDEX)

                        # loop over current layer icons and their indexes
                        for index, icon_shortcut in enumerate(_icons):
                            # if this icon was pressed
                            if icon_shortcut.contains(p):
                                # debounce logic, check that it wasn't already pressed
                                if index not in _pressed_icons:
                                    # print("pressed {}".format(index))

                                    # get actions for this icon from config object
                                    _cur_actions = touch_deck_config["layers"][
                                        current_layer
                                    ]["shortcuts"][index]["actions"]

                                    # tuple means it's a single action
                                    if isinstance(_cur_actions, tuple):
                                        # put it in a list by itself
                                        _cur_actions = [_cur_actions]

                                    # loop over the actions
                                    for _action in _cur_actions:
                                        # HID keyboard keys
                                        if _action[0] == KEY:
                                            kbd.press(*_action[1])
                                            kbd.release(*_action[1])

                                        # String to write from layout
                                        elif _action[0] == STRING:
                                            kbd_layout.write(_action[1])

                                        # Consumer control code
                                        elif _action[0] == MEDIA:
                                            cc.send(_action[1])

                                        # Key press
                                        elif _action[0] == KEY_PRESS:
                                            kbd.press(*_action[1])

                                        # Key release
                                        elif _action[0] == KEY_RELEASE:
                                            kbd.release(*_action[1])

                                        # Change Layer
                                        elif _action[0] == CHANGE_LAYER:
                                            if isinstance(
                                                _action[1], int
                                            ) and 0 <= _action[1] < len(
                                                touch_deck_config["layers"]
                                            ):

                                                current_layer = _action[1]
                                                load_layer(_action[1])

                                        # if there are multiple actions
                                        if len(_cur_actions) > 1:
                                            # small sleep to make sure
                                            # OS can respond to previous action
                                            time.sleep(0.2)

                                    # save current time to check for timeout
                                    LAST_PRESS_TIME = _now
                                    # append this index to pressed icons for debouncing
                                    _pressed_icons.append(index)
    else:  # screen not touched

        # empty the pressed icons list
        _pressed_icons.clear()
