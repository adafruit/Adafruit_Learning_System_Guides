# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
This example is made for a basic Microsoft optical mouse with
two buttons and a wheel that can be pressed.

It assumes there is a single mouse connected to USB Host,
and no other devices connected.

It illustrates multi-player turn based logic with a very
basic implementation of tic-tac-toe.
"""
import array
import random
from displayio import Group, OnDiskBitmap, TileGrid
from adafruit_display_text.bitmap_label import Label
from adafruit_displayio_layout.layouts.grid_layout import GridLayout
import supervisor
import terminalio
import usb.core

if hasattr(supervisor.runtime, "display") and supervisor.runtime.display is not None:
    # use the built-in HSTX display for Metro RP2350
    display = supervisor.runtime.display
else:
    from displayio import release_displays
    import picodvi
    import board
    import framebufferio

    # initialize display
    release_displays()

    fb = picodvi.Framebuffer(
        320,
        240,
        clk_dp=board.CKP,
        clk_dn=board.CKN,
        red_dp=board.D0P,
        red_dn=board.D0N,
        green_dp=board.D1P,
        green_dn=board.D1N,
        blue_dp=board.D2P,
        blue_dn=board.D2N,
        color_depth=16,
    )
    display = framebufferio.FramebufferDisplay(fb)

# group to hold visual elements
main_group = Group()

# make the group visible on the display
display.root_group = main_group

# load the mouse cursor bitmap
mouse_bmp = OnDiskBitmap("mouse_cursor.bmp")

# make the background pink pixels transparent
mouse_bmp.pixel_shader.make_transparent(0)

# create a TileGrid for the mouse, using its bitmap and pixel_shader
mouse_tg = TileGrid(mouse_bmp, pixel_shader=mouse_bmp.pixel_shader)

# move it to the center of the display
mouse_tg.x = display.width // 2
mouse_tg.y = display.height // 2

# text label to show the x, y coordinates on the screen
output_lbl = Label(terminalio.FONT, text="", color=0xFFFFFF, scale=1)

# move it to the right side of the screen
output_lbl.anchor_point = (0, 0)
output_lbl.anchored_position = (180, 40)

# add it to the main group
main_group.append(output_lbl)

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

# set up a 3x3 grid for the tic-tac-toe board
board_grid = GridLayout(x=40, y=40, width=128, height=128, grid_size=(3, 3))

# load the tic-tac-toe spritesheet
tictactoe_spritesheet = OnDiskBitmap("tictactoe_spritesheet.bmp")

# X is index 1 in the spritesheet, O is index 2 in the spritesheet
player_icon_indexes = [1, 2]

# current player variable.
# When this equlas 0 its X's turn,
# when it equals 1 it is O's turn.
current_player_index = random.randint(0, 1)  # randomize the initial player

# loop over rows
for y in range(3):
    # loop over columns
    for x in range(3):
        # create a TileGrid for this cell
        new_tg = TileGrid(
            bitmap=tictactoe_spritesheet,
            default_tile=0,
            tile_height=32,
            tile_width=32,
            height=1,
            width=1,
            pixel_shader=tictactoe_spritesheet.pixel_shader,
        )

        # add the new TileGrid to the board grid at the current position
        board_grid.add_content(new_tg, grid_position=(x, y), cell_size=(1, 1))

# add the board grid to the main group
main_group.append(board_grid)

# add the mouse tile grid to the main group
main_group.append(mouse_tg)


def check_for_winner():
    """
    check if a player has won

    :return: the player icon index of the winning player,
        None if no winner and game continues, -1 if game ended in a tie.
    """
    found_empty = False

    # check rows
    for row_idx in range(3):
        # if the 3 cells in this row match
        if (
            board_grid[0 + (row_idx * 3)][0] != 0
            and board_grid[0 + (row_idx * 3)][0]
            == board_grid[1 + (row_idx * 3)][0]
            == board_grid[2 + (row_idx * 3)][0]
        ):
            return board_grid[0 + (row_idx * 3)][0]

        # if any of the cells in this row are empty
        if 0 in (
            board_grid[0 + (row_idx * 3)][0],
            board_grid[1 + (row_idx * 3)][0],
            board_grid[2 + (row_idx * 3)][0],
        ):
            found_empty = True

    # check columns
    for col_idx in range(3):
        # if the 3 cells in this column match
        if (
            board_grid[0 + col_idx][0] != 0
            and board_grid[0 + col_idx][0]
            == board_grid[3 + col_idx][0]
            == board_grid[6 + col_idx][0]
        ):
            return board_grid[0 + col_idx][0]

        # if any of the cells in this column are empty
        if 0 in (
            board_grid[0 + col_idx][0],
            board_grid[3 + col_idx][0],
            board_grid[6 + col_idx][0],
        ):
            found_empty = True

    # check diagonals
    if (
        board_grid[0][0] != 0
        and board_grid[0][0] == board_grid[4][0] == board_grid[8][0]
    ):
        return board_grid[0][0]

    if (
        board_grid[2][0] != 0
        and board_grid[2][0] == board_grid[4][0] == board_grid[6][0]
    ):
        return board_grid[2][0]

    if found_empty:
        # return None if there is no winner and the game continues
        return None
    else:
        # return -1 if it's a tie game with no winner
        return -1


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

    # if left button clicked
    if buf[0] & (1 << 0) != 0:
        # get the mouse pointer coordinates accounting for the offset of
        # the board grid location
        coords = (mouse_tg.x - board_grid.x, mouse_tg.y - board_grid.y, 0)

        # loop over all cells in the board
        for cell_tg in board_grid:

            # if the current cell is blank, and contains the clicked coordinates
            if cell_tg[0] == 0 and cell_tg.contains(coords):
                # set the current cell tile index to the current player's icon
                cell_tg[0] = player_icon_indexes[current_player_index]

                # change to the next player
                current_player_index = (current_player_index + 1) % 2

                # print out which player's turn it is
                print(f"It is now {'X' if current_player_index == 0 else 'O'}'s turn")

                # check for a winner
                result = check_for_winner()

                # if Xs or Os have won
                if result == 1:
                    output_lbl.text = "X is the winner!"
                elif result == 2:
                    output_lbl.text = "O is the winner!"

                # if it was a tie game
                elif result == -1:
                    output_lbl.text = "Tie game, no winner."
