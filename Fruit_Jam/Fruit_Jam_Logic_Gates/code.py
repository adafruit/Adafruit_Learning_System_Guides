# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Fruit Jam Logic Gates Simulator
"""
import sys
import time

import board
from digitalio import DigitalInOut, Pull, Direction
from displayio import Group

import supervisor
from neopixel import NeoPixel
from adafruit_usb_host_mouse import find_and_init_boot_mouse
from adafruit_fruitjam.peripherals import request_display_config
from workspace import Workspace

# cooldown time to ignore double clicks
CLICK_COOLDOWN = 0.15
last_click_time = None

# set the display size to 320,240
request_display_config(320, 240)
display = supervisor.runtime.display

# setup the mouse
mouse = find_and_init_boot_mouse()
mouse.sensitivity = 1.5
if mouse is None:
    raise RuntimeError(
        "No mouse found connected to USB Host. A mouse is required for this app."
    )

# setup displayio Group for visuals
main_group = Group()
display.root_group = main_group

# setup physical hardware buttons
btn_1 = DigitalInOut(board.BUTTON1)
btn_1.direction = Direction.INPUT
btn_1.pull = Pull.UP
btn_2 = DigitalInOut(board.BUTTON2)
btn_2.direction = Direction.INPUT
btn_2.pull = Pull.UP
btn_3 = DigitalInOut(board.BUTTON3)
btn_3.direction = Direction.INPUT
btn_3.pull = Pull.UP

# setup neopixels
neopixels = NeoPixel(board.NEOPIXEL, 5, brightness=0.2, auto_write=True)

# setup Workspace object, giving it the neopixels, and hardware button objects
workspace = Workspace(neopixels, (btn_1, btn_2, btn_3))

# add workspace elements to the Group to be shown on display
main_group.append(workspace.group)
main_group.append(workspace.mouse_moving_tg)

# add the mouse to the Group to be shown on top of everything else
main_group.append(mouse.tilegrid)

# hardware button state variables
old_button_values = [True, True, True]
button_values_changed = False

while True:
    # update mouse, and get any mouse buttons that are pressed
    pressed_btns = mouse.update()

    # enforce click cooldown to ignore double clicks
    now = time.monotonic()
    if last_click_time is None or now > last_click_time + CLICK_COOLDOWN:
        # if any buttons are pressed
        if pressed_btns is not None and len(pressed_btns) > 0:
            last_click_time = now
            # let workspace handle the click event
            workspace.handle_mouse_click(mouse.x, mouse.y, pressed_btns)

    # if there is an entity on the mouse being moved
    if not workspace.mouse_moving_tg.hidden:
        # update its TileGrid's location to follow the mouse
        workspace.mouse_moving_tg.x = mouse.x - 12
        workspace.mouse_moving_tg.y = mouse.y - 24 - 12

    # check how many bytes are available from keyboard
    available = supervisor.runtime.serial_bytes_available

    # if there are some bytes available
    if available:
        # read data from the keyboard input
        c = sys.stdin.read(available)
        key_bytes = c.encode("utf-8")
        # let workspace handle the key press event
        workspace.handle_key_press(key_bytes, mouse.x, mouse.y)

    # get hardware button states
    btn_1_current = btn_1.value
    btn_2_current = btn_2.value
    btn_3_current = btn_3.value
    button_values_changed = False

    # check if any hardware button states have changed
    if btn_1_current != old_button_values[0]:
        button_values_changed = True
    if btn_2_current != old_button_values[1]:
        button_values_changed = True
    if btn_3_current != old_button_values[2]:
        button_values_changed = True

    # update the old button states to compare with next iteration
    old_button_values[0] = btn_1_current
    old_button_values[1] = btn_2_current
    old_button_values[2] = btn_3_current

    # if any button state changed, update workspace to run simulation
    if button_values_changed:
        workspace.update()
