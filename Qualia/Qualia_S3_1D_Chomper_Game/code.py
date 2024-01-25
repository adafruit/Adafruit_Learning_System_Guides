# SPDX-FileCopyrightText: 2024 Tim Cocks
#
# SPDX-License-Identifier: MIT
"""
1D Chomper

Circuitpython based 1 dimensional pacman style game inspired by Paku Paku.
"""
import time
import board
from adafruit_qualia import Qualia
from adafruit_qualia.graphics import Displays
from entity import Entity
from chomper_1d_lib import ChomperGame
from digitalio import DigitalInOut, Direction, Pull


# initialize the physical button on A0
btn = DigitalInOut(board.A0)
btn.direction = Direction.INPUT
btn.pull = Pull.DOWN
btn_prev_val = btn.value

# Create the Qualia object for the 240x960 display PID 5799
qualia = Qualia(Displays.BAR240X960)

# OR create the Qualia object for the 320x960 display PID 5805
# qualia = Qualia(Displays.BAR320X960)

display = qualia.display

# Landscape orientation, mounted with ribbon cable coming off the left side of display.
display.rotation = 270

# Create the Game object, passing in the display size
game_obj = ChomperGame((display.width, display.height))

# set the Group scaling to 3x
game_obj.scale = 3

# down a little bit from top of display
game_obj.y = 10

# start the player moving to the right
game_obj.player_entity.direction = Entity.DIRECTION_RIGHT

# set game_obj as the root_group to show it on the Display.
display.root_group = game_obj

# main loop
while True:

    game_obj.game_tick()

    btn_cur_value = btn.value

    # if the button was pressed
    if btn_cur_value and not btn_prev_val:

        # If the game is currently playing
        if not game_obj.game_over:
            # change the Player to the opposite direction
            if game_obj.player_entity.direction == Entity.DIRECTION_LEFT:
                game_obj.player_entity.direction = Entity.DIRECTION_RIGHT
            else:
                game_obj.player_entity.direction = Entity.DIRECTION_LEFT

        # If the game is over
        else:
            # Restart to play again
            game_obj.restart()

    # update button variable for debouncing
    btn_prev_val = btn_cur_value
