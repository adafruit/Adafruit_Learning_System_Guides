# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
An implementation of the card game memory. Players take turns flipping
over two cards trying to find pairs. After the turn any non-pairs are
flipped face down so the players must try to remember where they are.

Players trade off using the USB mouse to play their turns.
"""
import array
import random
import time
import atexit
from displayio import Group, OnDiskBitmap, TileGrid
from adafruit_display_text.bitmap_label import Label
from adafruit_display_text.text_box import TextBox
from adafruit_displayio_layout.layouts.grid_layout import GridLayout
from adafruit_ticks import ticks_ms
import supervisor
import terminalio
import usb.core
from adafruit_fruitjam.peripherals import request_display_config
import adafruit_usb_host_descriptors
from adafruit_pathlib import Path


def random_selection(lst, count):
    """
    Select items randomly from a list of items.

    returns a list of length count containing the selected items.
    """
    if len(lst) <= count:
        raise ValueError("Count must be less than or equal to length of list")
    iter_copy = list(lst)
    selection = set()
    while len(selection) < count:
        selection.add(iter_copy.pop(random.randrange(len(iter_copy))))
    return list(selection)


def update_score_text():
    """
    Update the score text on the display for each player
    """
    for _ in range(2):
        out_str = f"p{_+1} score: {player_scores[_]}"
        score_lbls[_].text = out_str


# state machine constants

# title state, shows title screen waits for click
STATE_TITLE = 0

# playing state alternates players flipping cards to play the game
STATE_PLAYING = 1

# shows the game over message and waits for a button to be clicked
STATE_GAMEOVER = 2

# initial state is title screen
CUR_STATE = STATE_TITLE

request_display_config(320,240)
display = supervisor.runtime.display

# main group will hold all the visual elements
main_group = Group()

# make main group visible on the display
display.root_group = main_group

# list of Label instances for player scores
score_lbls = []

# list of colors, one representing each player
colors = [0xFF00FF, 0x00FF00]

# randomly choose the first player
current_turn_index = random.randrange(0, 2)

# list that holds up to 2 cards that have been flipped over
# on the current turn
cards_flipped_this_turn = []

# list that holds the scores of each player
player_scores = [0, 0]

# size of the grid of cards to layout
grid_size = (6, 4)

# create a grid layout to help place cards neatly
# into a grid on the display
card_grid = GridLayout(x=10, y=10, width=260, height=200, grid_size=grid_size)

# these indexes within the spritesheet contain the
# card front sprites, there are 8 different cards total.
CARD_FRONT_SPRITE_INDEXES = {1, 2, 3, 4, 5, 6, 7, 9}

# pool of cards to deal them onto the board from
# starts with 2 copies of each of 8 different cards
pool = list(CARD_FRONT_SPRITE_INDEXES) + list(CARD_FRONT_SPRITE_INDEXES)

# select 4 cards at random that will be duplicated
duplicates = random_selection(CARD_FRONT_SPRITE_INDEXES, 4)

# add 2 copies each of the 4 selected duplicate cards
# this brings the pool to 24 cards total
pool += duplicates + duplicates

# list that represents the order the cards are randomly
# dealt out into. The board is a two-dimensional grid,
# but this list is one dimension where
# index in the list = y * width + x in the grid.
card_locations = []

# load the spritesheet for the cards
sprites = OnDiskBitmap("memory_game_sprites.bmp")

# list to hold TileGrid instances for each card
card_tgs = []

# loop over 4 rows
for y in range(4):
    # loop over 6 columns
    for x in range(6):
        # i = y * 6 + x

        # create a TileGrid
        new_tg = TileGrid(
            bitmap=sprites,
            default_tile=10,
            tile_height=32,
            tile_width=32,
            height=1,
            width=1,
            pixel_shader=sprites.pixel_shader,
        )

        # add it to the list of card tilegrids
        card_tgs.append(new_tg)

        # add it to the grid layout at the current x,y position
        card_grid.add_content(new_tg, grid_position=(x, y), cell_size=(1, 1))

        # choose a random index of a card in the pool
        random_choice = random.randrange(0, len(pool) - 1) if len(pool) > 1 else 0

        # remove the chosen card from the pool, and add it
        # to the card locations list at the current location
        card_locations.append(pool.pop(random_choice))

# center the card grid layout horizontally
card_grid.x = display.width // 2 - card_grid.width // 2

# move the card grid layout towards the bottom of the screen
card_grid.y = display.height - card_grid.height

# add the card grid to the main group
main_group.append(card_grid)

# create a group to hold the game over elements
game_over_group = Group()

# create a TextBox to hold the game over message
game_over_label = TextBox(
    terminalio.FONT,
    text="",
    color=0xFFFFFF,
    background_color=0x222222,
    width=display.width // 2,
    height=80,
    align=TextBox.ALIGN_CENTER,
)
# move it to the center top of the display
game_over_label.anchor_point = (0, 0)
game_over_label.anchored_position = (
    display.width // 2 - game_over_label.width // 2,
    40,
)

# make it hidden, it will show it when the game is over.
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
play_again_btn.x = display.width // 2 - play_again_btn_bmp.width // 2 - 30

# inside the bounds of the game over label, so it looks like a dialog visually
play_again_btn.y = 80

# create TileGrid for the exit button
exit_btn = TileGrid(bitmap=exit_btn_bmp, pixel_shader=exit_btn_bmp.pixel_shader)

# transparent pixels in the corners for the rounded corner effect
exit_btn_bmp.pixel_shader.make_transparent(0)

# centered within the display, offset to the right
exit_btn.x = display.width // 2 - exit_btn_bmp.width // 2 + 30

# inside the bounds of the game over label, so it looks like a dialog visually
exit_btn.y = 80

# add the play again and exit buttons to the game over group
game_over_group.append(play_again_btn)
game_over_group.append(exit_btn)

# add the game over group to the main group
main_group.append(game_over_group)

# create score label for each player
for i in range(2):
    # create a new label to hold score
    score_lbl = Label(terminalio.FONT, text="", color=colors[i], scale=1)
    if i == 0:
        # if it's player 1 put it in the top left
        score_lbl.anchor_point = (0, 0)
        score_lbl.anchored_position = (4, 1)
    else:
        # if it's player 2 put it tin the top right
        score_lbl.anchor_point = (1.0, 0)
        score_lbl.anchored_position = (display.width - 4, 1)

    # add the label to list of score labels
    score_lbls.append(score_lbl)

    # add the label to the main group
    main_group.append(score_lbl)

# initialize the text in the score labels to show 0
update_score_text()

# create a label to indicate which player's turn it is
current_player_lbl = Label(
    terminalio.FONT, text="Current Player", color=colors[current_turn_index], scale=1
)

# place it centered horizontally at the top of the screen
current_player_lbl.anchor_point = (0.5, 0)
current_player_lbl.anchored_position = (display.width // 2, 1)

# add the score label to the main group
main_group.append(current_player_lbl)

# load the title screen bitmap
title_screen_bmp = OnDiskBitmap("memory_title.bmp")

# create a TileGrid for the title screen
title_screen_tg = TileGrid(
    bitmap=title_screen_bmp, pixel_shader=title_screen_bmp.pixel_shader
)

# add it to the main group
main_group.append(title_screen_tg)

# load the mouse bitmap
mouse_bmp = OnDiskBitmap("mouse_cursor.bmp")

# make the background pink pixels transparent
mouse_bmp.pixel_shader.make_transparent(0)

# create a TileGrid for the mouse
mouse_tg = TileGrid(mouse_bmp, pixel_shader=mouse_bmp.pixel_shader)

# place it in the center of the display
mouse_tg.x = display.width // 2
mouse_tg.y = display.height // 2

# add the mouse to the main group
main_group.append(mouse_tg)

# variable for the mouse USB device instance
mouse = None

# wait a second for USB devices to be ready
time.sleep(1)

mouse_interface_index, mouse_endpoint_address = None, None
mouse = None

# scan for connected USB devices
for device in usb.core.find(find_all=True):
    # print information about the found devices
    print(f"{device.idVendor:04x}:{device.idProduct:04x}")
    print(device.manufacturer, device.product)
    print(device.serial_number)

    config_descriptor = adafruit_usb_host_descriptors.get_configuration_descriptor(
        device, 0
    )

    _possible_interface_index, _possible_endpoint_address = adafruit_usb_host_descriptors.find_boot_mouse_endpoint(
        device)
    if _possible_interface_index is not None and _possible_endpoint_address is not None:
        mouse = device
        mouse_interface_index = _possible_interface_index
        mouse_endpoint_address = _possible_endpoint_address
        print(f"mouse interface: {mouse_interface_index} endpoint_address: {hex(mouse_endpoint_address)}")

mouse_was_attached = None
if mouse is not None:
    # detach the kernel driver if needed
    if mouse.is_kernel_driver_active(0):
        mouse_was_attached = True
        mouse.detach_kernel_driver(0)
    else:
        mouse_was_attached = False

    # set configuration on the mouse so we can use it
    mouse.set_configuration()

def atexit_callback():
    """
    re-attach USB devices to kernel if needed.
    :return:
    """
    print("inside atexit callback")
    if mouse_was_attached and not mouse.is_kernel_driver_active(0):
        mouse.attach_kernel_driver(0)

atexit.register(atexit_callback)

# Buffer to hold data read from the mouse
# Boot mice have 4 byte reports
buf = array.array("b", [0] * 4)

# timestamp in the future to wait until before
# awarding points for a pair, or flipping cards
# back over and changing turns
WAIT_UNTIL = 0

# bool indicating whether the code is waiting to reset flipped
# cards and change turns or award points and remove
# cards. Will be True if the code is waiting to take action,
# False otherwise.
waiting_to_reset = False

# main loop
while True:
    # timestamp of the current time
    now = ticks_ms()

    # attempt mouse read
    try:
        # try to read data from the mouse, small timeout so the code will move on
        # quickly if there is no data
        data_len = mouse.read(mouse_endpoint_address, buf, timeout=20)

        # if there was data, then update the mouse cursor on the display
        # using min and max to keep it within the bounds of the display
        mouse_tg.x = max(0, min(display.width - 1, mouse_tg.x + buf[1] // 2))
        mouse_tg.y = max(0, min(display.height - 1, mouse_tg.y + buf[2] // 2))

    # timeout error is raised if no data was read within the allotted timeout
    except usb.core.USBTimeoutError:
        # no problem, just go on
        pass

    # if the current state is title screen
    if CUR_STATE == STATE_TITLE:
        # if the left mouse button was clicked
        if buf[0] & (1 << 0) != 0:
            # change the current state to playing
            CUR_STATE = STATE_PLAYING
            # hide the title screen
            title_screen_tg.hidden = True
            # change the mouse cursor color to match the current player
            mouse_bmp.pixel_shader[2] = colors[current_turn_index]

    # if the current state is playing
    elif CUR_STATE == STATE_PLAYING:

        # if the code is  waiting to reset, and it's time to take action
        if waiting_to_reset and now >= WAIT_UNTIL:
            # this means that there are already 2 cards flipped face up.
            # The code needs to either award points, or flip the cards
            # back over and change to the next players turn.

            # change variable to indicate the code is no longer waiting to take action
            waiting_to_reset = False

            # if both cards were the same i.e. they found a match
            if (
                card_tgs[cards_flipped_this_turn[0]][0]
                == card_tgs[cards_flipped_this_turn[1]][0]
            ):

                # set the cards tile index to show a blank spot instead of a card
                card_tgs[cards_flipped_this_turn[0]][0] = 8
                card_tgs[cards_flipped_this_turn[1]][0] = 8

                # award a point to the player
                player_scores[current_turn_index] += 1

                # refresh the score texts to show the new score
                update_score_text()

                # if the total of both players scores is equal to half the amount
                # of cards then the code knows the game is over because each pair is worth 1
                # point
                if (
                    player_scores[0] + player_scores[1]
                    >= (grid_size[0] * grid_size[1]) // 2
                ):

                    # if the player's scores are equal
                    if player_scores[0] == player_scores[1]:
                        # set the game over message to tie game
                        game_over_label.text = "Game Over\nTie Game"

                    else:  # player scores are not equal

                        # if player 2 score is larger than player 1
                        if player_scores[0] < player_scores[1]:
                            # set the game over message to indicate player 2 victory
                            game_over_label.text = "Game Over\nPlayer 2 Wins"
                            game_over_label.color = colors[1]

                        else:  # player 1 score is larger than player 2
                            # set the game over message to indicate player 1 victory
                            game_over_label.text = "Game Over\nPlayer 1 Wins"
                            game_over_label.color = colors[0]

                    # set the game over group to visible
                    game_over_group.hidden = False

                    # change the state to gameover
                    CUR_STATE = STATE_GAMEOVER

            else:  # the two cards were different i.e. they did not find a match
                # set both cards tile index to the card back sprite to flip it back over
                card_tgs[cards_flipped_this_turn[0]][0] = 10
                card_tgs[cards_flipped_this_turn[1]][0] = 10

                # go to the next players turn
                current_turn_index = (current_turn_index + 1) % 2

                # update the color of the current player indicator
                current_player_lbl.color = colors[current_turn_index]

                # update the color of the mouse cursor
                mouse_bmp.pixel_shader[2] = colors[current_turn_index]

            # empty out the cards flipped this turn list
            cards_flipped_this_turn = []

        # ignore any clicks while the code is waiting to take reset cards
        if now >= WAIT_UNTIL:
            # left btn pressed
            if buf[0] & (1 << 0) != 0:

                # loop over all cards
                for card_index, card in enumerate(card_tgs):
                    # coordinates of the mouse taking into account
                    # the offset from the card_grid position
                    coords = (mouse_tg.x - card_grid.x, mouse_tg.y - card_grid.y, 0)

                    # if this is a face down card, and the mouse coordinates
                    # are within its bounding box
                    if card[0] == 10 and card.contains(coords):
                        # flip the card face up by setting its tile index
                        # to the appropriate value from the card_locations list
                        card[0] = card_locations[card_tgs.index(card)]

                        # add this card index to the cards flipped this turn list
                        cards_flipped_this_turn.append(card_index)

                        # if 2 cards have been flipped this turn
                        if len(cards_flipped_this_turn) == 2:
                            # set the wait until time to a little bit in the future
                            WAIT_UNTIL = ticks_ms() + 1500
                            # set the waiting to reset flag to True
                            waiting_to_reset = True

    # if the current state is gameover
    elif CUR_STATE == STATE_GAMEOVER:
        # left btn pressed
        if buf[0] & (1 << 0) != 0:
            # get the coordinates of the mouse cursor point
            coords = (mouse_tg.x, mouse_tg.y, 0)

            # if the mouse point is within the play again
            # button bounding box
            if play_again_btn.contains(coords):
                # set next code file to this one
                supervisor.set_next_code_file(__file__, working_directory=Path(__file__).parent.absolute())
                # reload
                supervisor.reload()

            # if the mouse point is within the exit
            # button bounding box
            if exit_btn.contains(coords):
                # restart back to code.py
                supervisor.reload()
