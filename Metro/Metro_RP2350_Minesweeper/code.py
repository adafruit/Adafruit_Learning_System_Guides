# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
An implementation of minesweeper. The logic game where the player
correctly identifies the locations of mines on a grid by clicking on squares
and revealing the number of mines in adjacent squares.

The player can also flag squares they suspect contain mines. The game ends when
the player successfully reveals all squares without mines or clicks on a mine.
"""
import array
from displayio import Group, OnDiskBitmap, TileGrid, Bitmap, Palette
from adafruit_display_text.bitmap_label import Label
from adafruit_display_text.text_box import TextBox
from eventbutton import EventButton
import supervisor
import terminalio
from adafruit_usb_host_mouse import find_and_init_boot_mouse
from gamelogic import GameLogic, BLANK, INFO_BAR_HEIGHT, DIFFICULTIES
from menu import Menu, SubMenu

# pylint: disable=ungrouped-imports
if hasattr(supervisor.runtime, "display") and supervisor.runtime.display is not None:
    # use the built-in HSTX display for Metro RP2350
    display = supervisor.runtime.display
else:
    # pylint: disable=ungrouped-imports
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
    supervisor.runtime.display = display

game_logic = GameLogic(display) # pylint: disable=no-value-for-parameter

# Load the spritesheet
sprite_sheet = OnDiskBitmap("bitmaps/game_sprites.bmp")

# Main group will hold all the visual layers
main_group = Group()
display.root_group = main_group

# Add Background to the Main Group
background = Bitmap(display.width, display.height, 1)
bg_color = Palette(1)
bg_color[0] = 0xaaaaaa
main_group.append(TileGrid(
    background,
    pixel_shader=bg_color
))

# Add Game group, which holds the game board, to the main group
game_group = Group()
main_group.append(game_group)

# Add a group for the UI Elements
ui_group = Group()
main_group.append(ui_group)

MENU_ITEM_HEIGHT = INFO_BAR_HEIGHT

def create_game_board():
    # Remove the old game board
    if len(game_group) > 0:
        game_group.pop()

    x = display.width // 2 - (game_logic.grid_width * 16) // 2
    y = ((display.height - INFO_BAR_HEIGHT) // 2 -
         (game_logic.grid_height * 16) // 2 + INFO_BAR_HEIGHT)

    # Create a new game board
    game_board = TileGrid(
        sprite_sheet,
        pixel_shader=sprite_sheet.pixel_shader,
        width=game_logic.grid_width,
        height=game_logic.grid_height,
        tile_height=16,
        tile_width=16,
        x=x,
        y=y,
        default_tile=BLANK,
    )

    game_group.append(game_board)
    return game_board

def update_ui():
    # Update the UI elements with the current game state
    mines_left_label.text = f"Mines: {game_logic.mines_left}"
    elapsed_time_label.text = f"Time: {game_logic.elapsed_time}"


# variable for the mouse USB device instance
mouse = find_and_init_boot_mouse(cursor_image="bitmaps/mouse_cursor.bmp")
if mouse is None:
    raise RuntimeError("No mouse found. Please connect a USB mouse.")

mouse.sensitivity = 4  # Slow the mouse down a bit
mouse_tg = mouse.tilegrid
mouse_tg.x = display.width // 2
mouse_tg.y = display.height // 2

# add mouse graphic to main_group
main_group.append(mouse_tg)

buf = array.array("b", [0] * 4)
waiting_for_release = False
chord_selected = False
left_button = right_button = False
mouse_coords = (display.width // 2, display.height // 2)

# Create the UI Elements (Ideally fit into 320x16 area)
# Label for the Mines Left (Left of Center)
mines_left_label = Label(
    terminalio.FONT,
    color=0x000000,
    x=5,
    y=0,
)
mines_left_label.anchor_point = (0, 0)
mines_left_label.anchored_position = (5, 2)
ui_group.append(mines_left_label)
# Label for the Elapsed Time (Right of Center)
elapsed_time_label = Label(
    terminalio.FONT,
    color=0x000000,
    x=display.width - 50,
    y=0,
)
elapsed_time_label.anchor_point = (1, 0)
elapsed_time_label.anchored_position = (display.width - 5, 2)
ui_group.append(elapsed_time_label)

# Menu button to change difficulty
difficulty_menu = SubMenu(
    "Difficulty",
    70,
    80,
    display.width // 2 - 70,
    0
)

reset_menu = SubMenu(
    "Reset",
    50,
    40,
    display.width // 2 + 15,
    0
)

message_dialog = Group()
message_dialog.hidden = True

def reset():
    # Reset the game logic
    game_logic.reset()

    # Create a new game board and assign it into the game logic
    game_logic.game_board = create_game_board()

    message_dialog.hidden = True

def set_difficulty(diff):
    game_logic.difficulty = diff
    reset()
    difficulty_menu.select_item(DIFFICULTIES[diff]['label'].lower().replace(" ", "_"))

def hide_group(group):
    group.hidden = True

for i, difficulty in enumerate(DIFFICULTIES):
    # Create a button for each difficulty
    selected = i == game_logic.difficulty
    difficulty_menu.add_item((set_difficulty, i), difficulty['label'], selected)

reset_menu.add_item(reset, "OK")

menu = Menu()
menu.append(difficulty_menu)
menu.append(reset_menu)
ui_group.append(menu)

reset()

message_label = TextBox(
    terminalio.FONT,
    text="",
    color=0x333333,
    background_color=0xEEEEEE,
    width=display.width // 4,
    height=50,
    align=TextBox.ALIGN_CENTER,
    padding_top=5,
)
message_label.anchor_point = (0, 0)
message_label.anchored_position = (
    display.width // 2 - message_label.width // 2,
    display.height // 2 - message_label.height // 2,
)
message_dialog.append(message_label)
message_button = EventButton(
    (hide_group, message_dialog),
    label="OK",
    width=40,
    height=16,
    x=display.width // 2 - 20,
    y=display.height // 2 - message_label.height // 2 + 20,
    style=EventButton.RECT,
)
message_dialog.append(message_button)
ui_group.append(message_dialog)

# Popup message for game over/win

menus = (reset_menu, difficulty_menu)

# main loop
while True:
    update_ui()
    # update cursor position, and check for clicks
    mouse.update()
    buttons = mouse.pressed_btns

    # Extract button states
    if buttons is None or buttons == ():
        left_button = 0
        right_button = 0
    else:
        left_button = 1 if 'left' in buttons else 0
        right_button = 1 if 'right' in buttons else 0

    mouse_coords = (mouse_tg.x, mouse_tg.y)

    if waiting_for_release and not left_button and not right_button:
        # If both buttons are released, we can process the next click
        waiting_for_release = False

    if not message_dialog.hidden:
        if message_button.handle_mouse(mouse_coords, left_button, waiting_for_release):
            waiting_for_release = True
        continue

    if menu.handle_mouse(mouse_coords, left_button, waiting_for_release):
        waiting_for_release = True
    else:
        # process gameboard click if no menu
        ms_board = game_logic.game_board

        if left_button and right_button and not chord_selected:
            chord_coords = ((mouse_tg.x - ms_board.x) // 16, (mouse_tg.y - ms_board.y) // 16)
            chord_selected = game_logic.square_chord_highlight(chord_coords)
            if chord_selected:
                waiting_for_release = True

        if (ms_board.x <= mouse_tg.x <= ms_board.x + game_logic.grid_width * 16 and
            ms_board.y <= mouse_tg.y <= ms_board.y + game_logic.grid_height * 16 and
            not waiting_for_release):

            coords = ((mouse_tg.x - ms_board.x) // 16, (mouse_tg.y - ms_board.y) // 16)
            if chord_selected:
                chord_selected = False
                game_logic.square_chord_highlight(chord_coords, False)
                game_logic.square_chorded(chord_coords)
            elif right_button:
                game_logic.square_flagged(coords)
            elif left_button:
                if not game_logic.square_clicked(coords):
                    message_label.text = "Game Over"
                    message_dialog.hidden = False
            if left_button or right_button:
                waiting_for_release = True
        status = game_logic.check_for_win()
        if status:
            message_label.text = "You win!"
            message_dialog.hidden = False
            # Display message
        if status is None:
            continue
