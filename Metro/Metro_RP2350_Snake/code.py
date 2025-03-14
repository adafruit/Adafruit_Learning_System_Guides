# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
import sys
import time
from micropython import const
import board
import picodvi
import framebufferio
import supervisor
import displayio
import terminalio
from adafruit_display_text.text_box import TextBox
from snake_helpers import World, Snake, GameOverException, SpeedAdjuster

# state machine constant
STATE_TITLE = const(0)
STATE_PLAYING = const(1)
STATE_PAUSED = const(2)
STATE_GAME_OVER = const(3)

# begin in the title state
CURRENT_STATE = STATE_TITLE

# movement key bindings, change to different letters if you want.
KEY_UP = "w"
KEY_LEFT = "a"
KEY_DOWN = "s"
KEY_RIGHT = "d"
KEY_PAUSE = "t"

# how many segments the snake will start with
INITIAL_SNAKE_LEN = 3

# variable for the players score
score = 0

# initialize display
displayio.release_displays()
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

# In future release the default HSTX display
# will get initialized by default by circuitpython
# display = supervisor.runtime.display

# load title splash screen bitmap
title_bmp = displayio.OnDiskBitmap("snake_splash.bmp")
# create a tilegrid for the title splash screen
title_tg = displayio.TileGrid(bitmap=title_bmp, pixel_shader=title_bmp.pixel_shader)

instructions_txt = TextBox(
    terminalio.FONT,
    text=f"Move: {KEY_UP}{KEY_LEFT}{KEY_DOWN}{KEY_RIGHT} Pause: {KEY_PAUSE}".upper(),
    width=title_bmp.width,
    height=16,
    align=TextBox.ALIGN_CENTER,
)
instructions_txt.anchor_point = (0, 0)
instructions_txt.anchored_position = (0, title_bmp.height + 1)

# create a group for the title splash screen and put it in the center of the display
title_group = displayio.Group()
title_group.append(title_tg)
title_group.append(instructions_txt)
title_group.x = display.width // 2 - title_bmp.width // 2
title_group.y = display.height // 2 - title_bmp.height // 2

# initialize SpeedAdjuster to control how fast the snake is moving
speed_adjuster = SpeedAdjuster(12)

# initialize the world with enough room unused at the top for the score bar
world = World(height=28, width=40)
# move the world down to make room for the score bar
world.y = 16

# initialize a Snake instance and grow it to the appropriate size
snake = Snake(starting_location=[10, 10])
for i in range(INITIAL_SNAKE_LEN - 1):
    snake.grow()

# add one of each type of apple to the world
world.add_apple(snake=snake, apple_sprite_index=World.APPLE_RED_SPRITE_INDEX)
world.add_apple(snake=snake, apple_sprite_index=World.APPLE_GREEN_SPRITE_INDEX)

# create a group to hold everything for the game
game_group = displayio.Group()

# add the world to the game group
game_group.append(world)

# create TextBox to hold the score in a bar at the top of the display
score_txt = TextBox(
    terminalio.FONT, text=f"Score: {score}", color=0xFFFFFF, width=320, height=16
)
score_txt.anchor_point = (0, 0)
score_txt.anchored_position = (0, 2)

# add the score text to the game group
game_group.append(score_txt)

# create a TextBox to hold the game over message
game_over_label = TextBox(
    terminalio.FONT,
    text="",
    color=0xFFFFFF,
    background_color=0x000000,
    width=display.width // 2,
    height=80,
    align=TextBox.ALIGN_CENTER,
)
# move it to the center of the display
game_over_label.anchor_point = (0, 0)
game_over_label.anchored_position = (
    display.width // 2 - game_over_label.width // 2,
    40,
)

# make it hidden, we'll show it when the game is over.
game_over_label.hidden = True

# add it to the game group
game_group.append(game_over_label)

# set the title group to show on the display
display.root_group = title_group

# draw the snake in it's starting location
world.draw_snake(snake)

# timpstamp of the game step render
prev_step_time = time.monotonic()

# variable to hold string read from the keyboard to get button presses
cur_btn_val = None

while True:
    # current timestamp
    now = time.monotonic()

    # check if there is any keyboard input
    available = supervisor.runtime.serial_bytes_available

    # if there is some keyboard input
    if available:
        # read it into cur_btn_val
        cur_btn_val = sys.stdin.read(available)

        # change to lower-case before comparison
        # so that it's case-insensitive.
        cur_btn_val = cur_btn_val.lower()

    else:  # no keyboard input
        # set to None to clear out previous value
        cur_btn_val = None

    # if the current state is title screen
    if CURRENT_STATE == STATE_TITLE:
        # if any button was pressed
        if cur_btn_val is not None:
            # set the visible group on the display to the game group
            display.root_group = game_group
            # update the current state to playing
            CURRENT_STATE = STATE_PLAYING

    # if game is being played
    elif CURRENT_STATE == STATE_PLAYING:
        # if up button was pressed
        if cur_btn_val == KEY_UP:
            # if the snake is not already moving up or down
            if snake.direction not in (snake.DIRECTION_DOWN, snake.DIRECTION_UP):
                # change the direction to up
                snake.direction = snake.DIRECTION_UP
        # if down button was pressed
        if cur_btn_val == KEY_DOWN:
            # if the snake is not already moving up or down
            if snake.direction not in (snake.DIRECTION_DOWN, snake.DIRECTION_UP):
                # change the direction to down
                snake.direction = snake.DIRECTION_DOWN
        # if right button was pressed
        if cur_btn_val == KEY_RIGHT:
            # if the snake is not already moving left or right
            if snake.direction not in (snake.DIRECTION_LEFT, snake.DIRECTION_RIGHT):
                # change the direction to right
                snake.direction = snake.DIRECTION_RIGHT
        # if left button was pressed
        if cur_btn_val == KEY_LEFT:
            # if the snake is not already moving left or right
            if snake.direction not in (snake.DIRECTION_LEFT, snake.DIRECTION_RIGHT):
                # change direction to left
                snake.direction = snake.DIRECTION_LEFT
        # if the pause button was pressed
        if cur_btn_val == KEY_PAUSE:
            # change the state to paused
            CURRENT_STATE = STATE_PAUSED

        # if it's time to render a step of the game
        if now >= prev_step_time + speed_adjuster.delay:
            try:
                # move the snake in the direction it's going
                result = world.move_snake(snake)

                # if a red apple was eaten
                if result == World.APPLE_RED_SPRITE_INDEX:
                    # decrease the speed to slow down movement
                    speed_adjuster.decrease_speed()
                    # award score based on current speed and snake size
                    score += ((20 - speed_adjuster.speed) // 3) + snake.size
                    # update the score text in the top bar
                    score_txt.text = f"Score: {score}"

                # if a green apple was eaten
                elif result == World.APPLE_GREEN_SPRITE_INDEX:
                    # increase the speed to speed up movement
                    speed_adjuster.increase_speed()
                    # award score based on current speed and snake
                    # size plus bonus points for green apple
                    score += ((20 - speed_adjuster.speed) // 3) + 3 + snake.size
                    # update the score text in the top bar
                    score_txt.text = f"Score: {score}"

            # if the game is over due to snake running into the edge or itself
            except GameOverException as e:
                # update the game over message with the score
                output_str = (
                    f"Game Over\nScore: {score}\nPress P to play again\nPress Q to quit"
                )
                # set the message into the game over label
                game_over_label.text = output_str
                # make the game over label visible
                game_over_label.hidden = False
                # update the state to game over
                CURRENT_STATE = STATE_GAME_OVER

            # store the timestamp to compare with next iteration
            prev_step_time = now

    # if the game is paused
    elif CURRENT_STATE == STATE_PAUSED:
        # if the pause button was pressed
        if cur_btn_val == KEY_PAUSE:
            # change the state to playing so the game resumes
            CURRENT_STATE = STATE_PLAYING

    # if the current state is game over
    elif CURRENT_STATE == STATE_GAME_OVER:
        # if the p button is pressed for play again
        if cur_btn_val == "p":
            # set next code file to this one
            supervisor.set_next_code_file(__file__)
            # reload
            supervisor.reload()
        # if the q button is pressed for exit
        if cur_btn_val == "q":
            # break out of main while True loop.
            break
