# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
An implementation of a match3 jewel swap game. The idea is to move one character at a time
to line up at least 3 characters.
"""
import time
from displayio import Group, OnDiskBitmap, TileGrid, Bitmap, Palette
from adafruit_display_text.bitmap_label import Label
from adafruit_display_text.text_box import TextBox
from eventbutton import EventButton
import supervisor
import terminalio
from adafruit_usb_host_mouse import find_and_init_boot_mouse
from gamelogic import GameLogic, SELECTOR_SPRITE, EMPTY_SPRITE, GAMEBOARD_POSITION

GAMEBOARD_SIZE = (8, 7)
HINT_TIMEOUT = 10  # seconds before hint is shown
GAME_PIECES = 7  # Number of different game pieces (set between 3 and 8)

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

def get_color_index(color, shader=None):
    for index, palette_color in enumerate(shader):
        if palette_color == color:
            return index
    return None

# Load the spritesheet
sprite_sheet = OnDiskBitmap("/bitmaps/game_sprites.bmp")
sprite_sheet.pixel_shader.make_transparent(
    get_color_index(0x00ff00, sprite_sheet.pixel_shader)
)

# Main group will hold all the visual layers
main_group = Group()
display.root_group = main_group

# Add Background to the Main Group
background = Bitmap(display.width, display.height, 1)
bg_color = Palette(1)
bg_color[0] = 0x333333
main_group.append(TileGrid(
    background,
    pixel_shader=bg_color
))

# Add Game grid, which holds the game board, to the main group
game_grid = TileGrid(
    sprite_sheet,
    pixel_shader=sprite_sheet.pixel_shader,
    width=GAMEBOARD_SIZE[0],
    height=GAMEBOARD_SIZE[1],
    tile_width=32,
    tile_height=32,
    x=GAMEBOARD_POSITION[0],
    y=GAMEBOARD_POSITION[1],
    default_tile=EMPTY_SPRITE,
)
main_group.append(game_grid)

# Add a special selection groupd to highlight the selected piece and allow animation
selected_piece_group = Group()
selected_piece = TileGrid(
    sprite_sheet,
    pixel_shader=sprite_sheet.pixel_shader,
    width=1,
    height=1,
    tile_width=32,
    tile_height=32,
    x=0,
    y=0,
    default_tile=EMPTY_SPRITE,
)
selected_piece_group.append(selected_piece)
selector = TileGrid(
    sprite_sheet,
    pixel_shader=sprite_sheet.pixel_shader,
    width=1,
    height=1,
    tile_width=32,
    tile_height=32,
    x=0,
    y=0,
    default_tile=SELECTOR_SPRITE,
)
selected_piece_group.append(selector)
selected_piece_group.hidden = True
main_group.append(selected_piece_group)

# Add a group for the swap piece to help with animation
swap_piece = TileGrid(
    sprite_sheet,
    pixel_shader=sprite_sheet.pixel_shader,
    width=1,
    height=1,
    tile_width=32,
    tile_height=32,
    x=0,
    y=0,
    default_tile=EMPTY_SPRITE,
)
swap_piece.hidden = True
main_group.append(swap_piece)

# Add foreground
foreground_bmp = OnDiskBitmap("/bitmaps/foreground.bmp")
foreground_bmp.pixel_shader.make_transparent(0)
foreground_tg = TileGrid(foreground_bmp, pixel_shader=foreground_bmp.pixel_shader)
foreground_tg.x = 0
foreground_tg.y = 0
main_group.append(foreground_tg)

# Add a group for the UI Elements
ui_group = Group()
main_group.append(ui_group)

# Create the mouse graphics and add to the main group
time.sleep(1)  # Allow time for USB host to initialize
mouse = find_and_init_boot_mouse("/bitmaps/mouse_cursor.bmp")
if mouse is None:
    raise RuntimeError("No mouse found connected to USB Host")
main_group.append(mouse.tilegrid)

# Create the game logic object
# pylint: disable=no-value-for-parameter, too-many-function-args
game_logic = GameLogic(
    display,
    mouse,
    game_grid,
    swap_piece,
    selected_piece_group,
    GAME_PIECES,
    HINT_TIMEOUT
)

def update_ui():
    # Update the UI elements with the current game state
    score_label.text = f"Score:\n{game_logic.score}"

waiting_for_release = False
game_over_shown = False

# Create the UI Elements
# Label for the Score
score_label = Label(
    terminalio.FONT,
    color=0xffff00,
    x=5,
    y=10,
)
ui_group.append(score_label)

message_dialog = Group()
message_dialog.hidden = True

def reset():
    global game_over_shown  # pylint: disable=global-statement
    # Reset the game logic
    game_logic.reset()
    message_dialog.hidden = True
    game_over_shown = False

def hide_group(group):
    group.hidden = True

reset()

reset_button = EventButton(
    reset,
    label="Reset",
    width=40,
    height=16,
    x=5,
    y=50,
    style=EventButton.RECT,
)
ui_group.append(reset_button)

message_label = TextBox(
    terminalio.FONT,
    text="",
    color=0x333333,
    background_color=0xEEEEEE,
    width=display.width // 3,
    height=90,
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
    y=display.height // 2 - message_label.height // 2 + 60,
    style=EventButton.RECT,
)
message_dialog.append(message_button)
ui_group.append(message_dialog)

# main loop
while True:
    update_ui()
    # update mouse
    game_logic.update_mouse()

    if not message_dialog.hidden:
        if message_button.handle_mouse(
            (mouse.x, mouse.y),
            game_logic.pressed_btns and "left" in game_logic.pressed_btns,
            waiting_for_release
        ):
            game_logic.waiting_for_release = True
        continue

    if reset_button.handle_mouse(
        (mouse.x, mouse.y),
        game_logic.pressed_btns is not None and "left" in game_logic.pressed_btns,
        game_logic.waiting_for_release
    ):
        game_logic.waiting_for_release = True

    # process gameboard click if no menu
    game_logic.update()
    game_over = game_logic.check_for_game_over()
    if game_over and not game_over_shown:
        message_label.text = ("No more moves available. your final score is:\n"
                              + str(game_logic.score))
        message_dialog.hidden = False
        game_over_shown = True
