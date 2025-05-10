# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Match3 game inspired by the Set card game. Two players compete
to find sets of cards that share matching or mis-matching traits.
"""
import array
import atexit
import io
import os
import time

import board
import busio
import digitalio
import supervisor
import terminalio
import usb
from tilepalettemapper import TilePaletteMapper
from displayio import TileGrid, Group, Palette, OnDiskBitmap, Bitmap
from adafruit_display_text.text_box import TextBox
import adafruit_usb_host_descriptors
from adafruit_debouncer import Debouncer
import adafruit_sdcard
import msgpack
import storage
from match3_game_helpers import (
    Match3Game,
    STATE_GAMEOVER,
    STATE_PLAYING_SETCALLED,
    GameOverException,
)

original_autoreload_val = supervisor.runtime.autoreload
supervisor.runtime.autoreload = False

AUTOSAVE_FILENAME = "match3_game_autosave.dat"

main_group = Group()
display = supervisor.runtime.display

# set up scale factor of 2 for larger display resolution
scale_factor = 1
if display.width > 360:
    scale_factor = 2
    main_group.scale = scale_factor

save_to = None
game_state = None
try:
    # check for autosave file on CPSAVES drive
    if AUTOSAVE_FILENAME in os.listdir("/saves/"):
        savegame_buffer = io.BytesIO()
        with open(f"/saves/{AUTOSAVE_FILENAME}", "rb") as f:
            savegame_buffer.write(f.read())
        savegame_buffer.seek(0)
        game_state = msgpack.unpack(savegame_buffer)
        print(game_state)

    # if we made it to here then /saves/ exist so use it for
    # save data
    save_to = f"/saves/{AUTOSAVE_FILENAME}"
except OSError as e:
    # no /saves/ dir likely means no CPSAVES
    pass

sd_pins_in_use = False

if game_state is None:
    # try to use sdcard for saves
    # The SD_CS pin is the chip select line.
    SD_CS = board.SD_CS

    # Connect to the card and mount the filesystem.
    try:
        cs = digitalio.DigitalInOut(SD_CS)
    except ValueError:
        sd_pins_in_use = True

    print(f"sd pins in use: {sd_pins_in_use}")
    try:
        if not sd_pins_in_use:
            sdcard = adafruit_sdcard.SDCard(
                busio.SPI(board.SD_SCK, board.SD_MOSI, board.SD_MISO), cs
            )
            vfs = storage.VfsFat(sdcard)
            storage.mount(vfs, "/sd")

        if "set_game_autosave.dat" in os.listdir("/sd/"):
            savegame_buffer = io.BytesIO()
            with open("/sd/set_game_autosave.dat", "rb") as f:
                savegame_buffer.write(f.read())
            savegame_buffer.seek(0)
            game_state = msgpack.unpack(savegame_buffer)
            print(game_state)

        if "placeholder.txt" not in os.listdir("/sd/"):
            # if we made it to here then /sd/ exists and has a card
            # so use it for save data
            save_to = "/sd/set_game_autosave.dat"
    except OSError:
        # no SDcard
        pass

# background color
bg_bmp = Bitmap(
    display.width // scale_factor // 10, display.height // scale_factor // 10, 1
)
bg_palette = Palette(1)
bg_palette[0] = 0x888888
bg_tg = TileGrid(bg_bmp, pixel_shader=bg_palette)
bg_group = Group(scale=10)
bg_group.append(bg_tg)
main_group.append(bg_group)

# create Game helper object
match3_game = Match3Game(
    game_state=game_state,
    display_size=(display.width // scale_factor, display.height // scale_factor),
    save_location=save_to,
)
main_group.append(match3_game)

# create a group to hold the game over elements
game_over_group = Group()

# create a TextBox to hold the game over message
game_over_label = TextBox(
    terminalio.FONT,
    text="",
    color=0xFFFFFF,
    background_color=0x111111,
    width=display.width // scale_factor // 2,
    height=110,
    align=TextBox.ALIGN_CENTER,
)
# move it to the center top of the display
game_over_label.anchor_point = (0, 0)
game_over_label.anchored_position = (
    display.width // scale_factor // 2 - (game_over_label.width) // 2,
    40,
)

# make it hidden, we'll show it when the game is over.
game_over_group.hidden = True

# add the game over lable to the game over group
game_over_group.append(game_over_label)

# load the play again, and exit button bitmaps
play_again_btn_bmp = OnDiskBitmap("btn_play_again.bmp")
exit_btn_bmp = OnDiskBitmap("btn_exit.bmp")

# create TileGrid for the play again button
play_again_btn = TileGrid(
    bitmap=play_again_btn_bmp, pixel_shader=play_again_btn_bmp.pixel_shader
)

# transparent pixels in the corners for the rounded corner effect
play_again_btn_bmp.pixel_shader.make_transparent(0)

# centered within the display, offset to the left
play_again_btn.x = (
    display.width // scale_factor // 2 - (play_again_btn_bmp.width) // 2 - 30
)

# inside the bounds of the game over label, so it looks like a dialog visually
play_again_btn.y = 100

# create TileGrid for the exit button
exit_btn = TileGrid(bitmap=exit_btn_bmp, pixel_shader=exit_btn_bmp.pixel_shader)

# transparent pixels in the corners for the rounded corner effect
exit_btn_bmp.pixel_shader.make_transparent(0)

# centered within the display, offset to the right
exit_btn.x = display.width // scale_factor // 2 - (exit_btn_bmp.width) // 2 + 30

# inside the bounds of the game over label, so it looks like a dialog visually
exit_btn.y = 100

# add the play again and exit buttons to the game over group
game_over_group.append(play_again_btn)
game_over_group.append(exit_btn)
main_group.append(game_over_group)

# wait a second for USB devices to be ready
time.sleep(1)

# load the mouse bitmap
mouse_bmp = OnDiskBitmap("mouse_cursor.bmp")

# make the background pink pixels transparent
mouse_bmp.pixel_shader.make_transparent(0)

# list for mouse tilegrids
mouse_tgs = []
# list for palette mappers, one for each mouse
palette_mappers = []
# list for mouse colors
colors = [0x2244FF, 0xFFFF00]

# remap palette will have the 3 colors from mouse bitmap
# and the two colors from the mouse colors list
remap_palette = Palette(3 + len(colors))
# index 0 is transparent
remap_palette.make_transparent(0)

# copy the 3 colors from the mouse bitmap palette
for i in range(3):
    remap_palette[i] = mouse_bmp.pixel_shader[i]

# copy the 2 colors from the mouse colors list
for i in range(2):
    remap_palette[i + 3] = colors[i]

# create tile palette mappers
for i in range(2):
    palette_mapper = TilePaletteMapper(remap_palette, 3)
    # remap index 2 to each of the colors in mouse colors list
    palette_mapper[0] = [0, 1, i + 3]
    palette_mappers.append(palette_mapper)

    # create tilegrid for each mouse
    mouse_tg = TileGrid(mouse_bmp, pixel_shader=palette_mapper)
    mouse_tg.x = display.width // scale_factor // 2 - (i * 12)
    mouse_tg.y = display.height // scale_factor // 2
    mouse_tgs.append(mouse_tg)

# USB info lists
mouse_interface_indexes = []
mouse_endpoint_addresses = []
kernel_driver_active_flags = []
# USB device object instance list
mice = []
# buffers list for mouse packet data
mouse_bufs = []
# debouncers list for debouncing mouse left clicks
mouse_debouncers = []

# scan for connected USB devices
for device in usb.core.find(find_all=True):
    # check if current device is has a boot mouse endpoint
    mouse_interface_index, mouse_endpoint_address = (
        adafruit_usb_host_descriptors.find_boot_mouse_endpoint(device)
    )
    if mouse_interface_index is not None and mouse_endpoint_address is not None:
        # if it does have a boot mouse endpoint then add information to the
        # usb info lists
        mouse_interface_indexes.append(mouse_interface_index)
        mouse_endpoint_addresses.append(mouse_endpoint_address)

        # add the mouse device instance to list
        mice.append(device)
        print(
            f"mouse interface: {mouse_interface_index} "
            + f"endpoint_address: {hex(mouse_endpoint_address)}"
        )

        # detach kernel driver if needed
        kernel_driver_active_flags.append(device.is_kernel_driver_active(0))
        if device.is_kernel_driver_active(0):
            device.detach_kernel_driver(0)

        # set the mouse configuration so it can be used
        device.set_configuration()


def is_mouse1_left_clicked():
    """
    Check if mouse 1 left click is pressed
    :return: True if mouse 1 left click is pressed
    """
    return is_left_mouse_clicked(mouse_bufs[0])


def is_mouse2_left_clicked():
    """
    Check if mouse 2 left click is pressed
    :return: True if mouse 2 left click is pressed
    """
    return is_left_mouse_clicked(mouse_bufs[1])


def is_left_mouse_clicked(buf):
    """
    Check if a mouse is pressed given its packet buffer
    filled with read data
    :param buf: the buffer containing the packet data
    :return: True if mouse left click is  pressed
    """
    val = buf[0] & (1 << 0) != 0
    return val


def is_right_mouse_clicked(buf):
    """
    check if a mouse right click is pressed given its packet buffer
    :param buf: the buffer containing the packet data
    :return: True if mouse right click is pressed
    """
    val = buf[0] & (1 << 1) != 0
    return val


# print(f"addresses: {mouse_endpoint_addresses}")
# print(f"indexes: {mouse_interface_indexes}")

for mouse_tg in mouse_tgs:
    # add the mouse to the main group
    main_group.append(mouse_tg)

    # Buffer to hold data read from the mouse
    # Boot mice have 4 byte reports
    mouse_bufs.append(array.array("b", [0] * 8))

# create debouncer objects for left click functions
mouse_debouncers.append(Debouncer(is_mouse1_left_clicked))
mouse_debouncers.append(Debouncer(is_mouse2_left_clicked))

# set main_group as root_group, so it is visible on the display
display.root_group = main_group

# variable to hold winning player
winner = None


def get_mouse_deltas(buffer, read_count):
    """
    Given a mouse packet buffer and a read count of number of bytes read,
    return the delta x and y values of the mouse.
    :param buffer: the buffer containing the packet data
    :param read_count: the number of bytes read from the mouse
    :return: tuple containing x and y delta values
    """
    if read_count == 4:
        delta_x = buffer[1]
        delta_y = buffer[2]
    elif read_count == 8:
        delta_x = buffer[2]
        delta_y = buffer[4]
    else:
        raise ValueError(f"Unsupported mouse packet size: {read_count}, must be 4 or 8")
    return delta_x, delta_y


def atexit_callback():
    """
    re-attach USB devices to kernel if needed, and set
    autoreload back to the original state.
    :return:
    """
    for _i, _mouse in enumerate(mice):
        if kernel_driver_active_flags[_i]:
            if not _mouse.is_kernel_driver_active(0):
                _mouse.attach_kernel_driver(0)
    supervisor.runtime.autoreload = original_autoreload_val


atexit.register(atexit_callback)

# main loop
while True:

    # if set has been called
    if match3_game.cur_state == STATE_PLAYING_SETCALLED:
        # update the progress bar ticking down
        match3_game.update_active_turn_progress()

    # loop over the mice objects
    for i, mouse in enumerate(mice):
        mouse_tg = mouse_tgs[i]
        # attempt mouse read
        try:
            # read data from the mouse, small timeout so we move on
            # quickly if there is no data
            data_len = mouse.read(
                mouse_endpoint_addresses[i], mouse_bufs[i], timeout=10
            )
            mouse_deltas = get_mouse_deltas(mouse_bufs[i], data_len)
            # if we got data, then update the mouse cursor on the display
            # using min and max to keep it within the bounds of the display
            mouse_tg.x = max(
                0,
                min(
                    display.width // scale_factor - 1, mouse_tg.x + mouse_deltas[0] // 2
                ),
            )
            mouse_tg.y = max(
                0,
                min(
                    display.height // scale_factor - 1,
                    mouse_tg.y + mouse_deltas[1] // 2,
                ),
            )

        # timeout error is raised if no data was read within the allotted timeout
        except usb.core.USBTimeoutError:
            pass

        # update the mouse debouncers
        mouse_debouncers[i].update()

        try:
            # if the current mouse is right-clicking
            if is_right_mouse_clicked(mouse_bufs[i]):
                # let the game object handle the right-click
                match3_game.handle_right_click(i)

            # if the current mouse left-clicked
            if mouse_debouncers[i].rose:
                # get the current mouse coordinates
                coords = (mouse_tg.x, mouse_tg.y, 0)

                # if the current state is GAMEOVER
                if match3_game.cur_state != STATE_GAMEOVER:
                    # let the game object handle the click event
                    match3_game.handle_left_click(i, coords)
                else:
                    # if the mouse point is within the play again
                    # button bounding box
                    if play_again_btn.contains(coords):
                        # set next code file to this one
                        supervisor.set_next_code_file(__file__)
                        # reload
                        supervisor.reload()

                    # if the mouse point is within the exit
                    # button bounding box
                    if exit_btn.contains(coords):
                        supervisor.reload()

        # if the game is over
        except GameOverException:
            # check for a winner
            winner = None
            if match3_game.scores[0] > match3_game.scores[1]:
                winner = 0
            elif match3_game.scores[0] < match3_game.scores[1]:
                winner = 1

            # if there was a winner
            if winner is not None:
                # show a message with the winning player
                message = f"\nGame Over\nPlayer{winner + 1} Wins!"
                game_over_label.color = colors[winner]
                game_over_label.text = message

            else:  # there wasn't a winner
                # show a tie game message
                message = "\nGame Over\nTie Game Everyone Wins!"

            # make the gameover group visible
            game_over_group.hidden = False

            # delete the autosave file.
            os.remove(save_to)
