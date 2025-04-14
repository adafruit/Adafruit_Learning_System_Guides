# SPDX-FileCopyrightText: 2024 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
This example demonstrates basic autosave and resume functionality. There are two buttons
that can be clicked to increment respective counters. The number of clicks is stored
in a game_state dictionary and saved to a data file on the SDCard. When the code first
launches it will read the data file and load the game_state from it.
"""
import array
from io import BytesIO
import os

import board
import busio
import digitalio
import displayio
import msgpack
import storage
import supervisor
import terminalio
import usb

import adafruit_sdcard
from adafruit_display_text.bitmap_label import Label
from adafruit_button import Button

# use the default built-in display
display = supervisor.runtime.display

# button configuration
BUTTON_WIDTH = 100
BUTTON_HEIGHT = 30
BUTTON_STYLE = Button.ROUNDRECT

# game state object will get loaded from SDCard
# or a new one initialized as a dictionary
game_state = None

save_to = None

# boolean variables for possible SDCard states
sd_pins_in_use = False

# The SD_CS pin is the chip select line.
SD_CS = board.SD_CS

# try to Connect to the sdcard card and mount the filesystem.
try:
    # initialze CS pin
    cs = digitalio.DigitalInOut(SD_CS)
except ValueError:
    # likely the SDCard was auto-initialized by the core
    sd_pins_in_use = True

try:
    # if sd CS pin was not in use
    if not sd_pins_in_use:
        # try to initialize and mount the SDCard
        sdcard = adafruit_sdcard.SDCard(
            busio.SPI(board.SD_SCK, board.SD_MOSI, board.SD_MISO), cs
        )
        vfs = storage.VfsFat(sdcard)
        storage.mount(vfs, "/sd")

    # check for the autosave data file
    if "autosave_demo.dat" in os.listdir("/sd/"):
        # if the file is found read data from it into a BytesIO buffer
        buffer = BytesIO()
        with open("/sd/autosave_demo.dat", "rb") as f:
            buffer.write(f.read())
        buffer.seek(0)

        # unpack the game_state object from the read data in the buffer
        game_state = msgpack.unpack(buffer)
        print(game_state)

    # if placeholder.txt file does not exist
    if "placeholder.txt" not in os.listdir("/sd/"):
        # if we made it to here then /sd/ exists and has a card
        # so use it for save data
        save_to = "/sd/autosave_demo.dat"
except OSError as e:
    # sdcard init or mounting failed
    raise OSError(
        "This demo requires an SDCard. Please power off the device " +
        "insert an SDCard and then plug it back in."
    ) from e

# if no saved game_state was loaded
if game_state is None:
    # create a new game state dictionary
    game_state = {"pink_count": 0, "blue_count": 0}

# Make the display context
main_group = displayio.Group()
display.root_group = main_group

# make buttons
blue_button = Button(
    x=30,
    y=40,
    width=BUTTON_WIDTH,
    height=BUTTON_HEIGHT,
    style=BUTTON_STYLE,
    fill_color=0x0000FF,
    outline_color=0xFFFFFF,
    label="BLUE",
    label_font=terminalio.FONT,
    label_color=0xFFFFFF,
)

pink_button = Button(
    x=30,
    y=80,
    width=BUTTON_WIDTH,
    height=BUTTON_HEIGHT,
    style=BUTTON_STYLE,
    fill_color=0xFF00FF,
    outline_color=0xFFFFFF,
    label="PINK",
    label_font=terminalio.FONT,
    label_color=0x000000,
)

# add them to a list for easy iteration
all_buttons = [blue_button, pink_button]

# Add buttons to the display context
main_group.append(blue_button)
main_group.append(pink_button)

# make labels for each button
blue_lbl = Label(
    terminalio.FONT, text=f"Blue: {game_state['blue_count']}", color=0x3F3FFF
)
blue_lbl.anchor_point = (0, 0)
blue_lbl.anchored_position = (4, 4)
pink_lbl = Label(
    terminalio.FONT, text=f"Pink: {game_state['pink_count']}", color=0xFF00FF
)
pink_lbl.anchor_point = (0, 0)
pink_lbl.anchored_position = (4, 4 + 14)
main_group.append(blue_lbl)
main_group.append(pink_lbl)

# load the mouse cursor bitmap
mouse_bmp = displayio.OnDiskBitmap("mouse_cursor.bmp")

# make the background pink pixels transparent
mouse_bmp.pixel_shader.make_transparent(0)

# create a TileGrid for the mouse, using its bitmap and pixel_shader
mouse_tg = displayio.TileGrid(mouse_bmp, pixel_shader=mouse_bmp.pixel_shader)

# move it to the center of the display
mouse_tg.x = display.width // 2
mouse_tg.y = display.height // 2

# add the mouse tilegrid to main_group
main_group.append(mouse_tg)

# scan for connected USB device and loop over any found
for device in usb.core.find(find_all=True):
    # print device info
    print(f"{device.idVendor:04x}:{device.idProduct:04x}")
    print(device.manufacturer, device.product)
    print(device.serial_number)
    # assume the device is the mouse
    mouse = device

# detach the kernel driver if needed
if mouse.is_kernel_driver_active(0):
    mouse.detach_kernel_driver(0)

# set configuration on the mouse so we can use it
mouse.set_configuration()

# buffer to hold mouse data
# Boot mice have 4 byte reports
buf = array.array("b", [0] * 4)


def save_game_state():
    """
    msgpack the game_state and save it to the autosave data file
    :return:
    """
    b = BytesIO()
    msgpack.pack(game_state, b)
    b.seek(0)
    with open(save_to, "wb") as savefile:
        savefile.write(b.read())


# main loop
while True:
    try:
        # attempt to read data from the mouse
        # 10ms timeout, so we don't block long if there
        # is no data
        count = mouse.read(0x81, buf, timeout=10)
    except usb.core.USBTimeoutError:
        # skip the rest of the loop if there is no data
        continue

    # update the mouse tilegrid x and y coordinates
    # based on the delta values read from the mouse
    mouse_tg.x = max(0, min(display.width - 1, mouse_tg.x + buf[1]))
    mouse_tg.y = max(0, min(display.height - 1, mouse_tg.y + buf[2]))

    # if left click is pressed
    if buf[0] & (1 << 0) != 0:
        # get the current cursor coordinates
        coords = (mouse_tg.x, mouse_tg.y, 0)

        # loop over the buttons
        for button in all_buttons:
            # if the current button contains the mouse coords
            if button.contains(coords):
                # if the button isn't already in the selected state
                if not button.selected:
                    # enter selected state
                    button.selected = True

                    # if it is the pink button
                    if button == pink_button:
                        # increment pink count
                        game_state["pink_count"] += 1
                        # update the label
                        pink_lbl.text = f"Pink: {game_state['pink_count']}"

                    # if it is the blue button
                    elif button == blue_button:
                        # increment blue count
                        game_state["blue_count"] += 1
                        # update the label
                        blue_lbl.text = f"Blue: {game_state['blue_count']}"

                    # save the new game state
                    save_game_state()

            # if the click is not on the current button
            else:
                # set this button as not selected
                button.selected = False

                # left click is not pressed
    else:
        # set all buttons as not selected
        for button in all_buttons:
            button.selected = False
