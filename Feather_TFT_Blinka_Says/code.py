# SPDX-FileCopyrightText: 2024 Tim Cocks
#
# SPDX-License-Identifier: MIT
"""
Blinka Says - A game inspired by Simon. Test your memory by
following along to the pattern that Blinka puts forth.

This project uses asyncio for cooperative multitasking
through tasks. There is one task for the players actions
and another for Blinka's actions.

The player action reads input from the buttons being
pressed by the player and reacts to them as appropriate.

The Blinka action blinks the randomized sequence that
the player must then try to follow and replicate.
"""
import random
import time

import asyncio
import board
from digitalio import DigitalInOut, Direction
from displayio import Group
import keypad
import terminalio

from adafruit_display_text.bitmap_label import Label
import foamyguy_nvm_helper as nvm_helper

# State Machine variables
STATE_WAITING_TO_START = 0
STATE_PLAYER_TURN = 1
STATE_BLINKA_TURN = 2

# list of color shortcut letters
COLORS = ("Y", "G", "R", "B")

# keypad initialization to read the button pins
buttons = keypad.Keys(
    (board.D5, board.D6, board.D9, board.D10), value_when_pressed=False, pull=True)

# Init LED output pins
leds = {
    "Y": DigitalInOut(board.A0),
    "G": DigitalInOut(board.A1),
    "R": DigitalInOut(board.A3),
    "B": DigitalInOut(board.A2)
}

for color in COLORS:
    leds[color].direction = Direction.OUTPUT

# a global variable to hold the eventual high-score
highscore = None

try:
    # read data from NVM storage
    read_data = nvm_helper.read_data()
    # if we found data check if it's a high-score value
    if isinstance(read_data, list) and read_data[0] == "bls_hs":
        # it is a high-score so populate the label with its value
        highscore = read_data[1]
except EOFError:
    # no high-score data
    pass

# display setup
display = board.DISPLAY
main_group = Group()

# Label to show the "High" score label
highscore_lbl = Label(terminalio.FONT, text="High ", scale=2)
highscore_lbl.anchor_point = (1.0, 0.0)
highscore_lbl.anchored_position = (display.width - 4, 4)
main_group.append(highscore_lbl)

# Label to show the "Current" score label
curscore_lbl = Label(terminalio.FONT, text="Current", scale=2)
curscore_lbl.anchor_point = (0.0, 0.0)
curscore_lbl.anchored_position = (4, 4)
main_group.append(curscore_lbl)

# Label to show the current score numerical value
curscore_val = Label(terminalio.FONT, text="0", scale=4)
curscore_val.anchor_point = (0.0, 0.0)
curscore_val.anchored_position = (4,
                                  curscore_lbl.bounding_box[1] +
                                  (curscore_lbl.bounding_box[3] * curscore_lbl.scale)
                                  + 10)
main_group.append(curscore_val)

# Label to show the high score numerical value
highscore_val = Label(terminalio.FONT, text="" if highscore is None else str(highscore), scale=4)
highscore_val.anchor_point = (1.0, 0.0)
highscore_val.anchored_position = (display.width - 4,
                                   highscore_lbl.bounding_box[1] +
                                   highscore_lbl.bounding_box[3] * curscore_lbl.scale
                                   + 10)
main_group.append(highscore_val)

# Label to show the "Game Over" message.
game_over_lbl = Label(terminalio.FONT, text="Game Over", scale=3)
game_over_lbl.anchor_point = (0.5, 1.0)
game_over_lbl.anchored_position = (display.width // 2, display.height - 4)
game_over_lbl.hidden = True
main_group.append(game_over_lbl)

# set the main_group to show on the display
display.root_group = main_group


class GameState:
    """
    Class that stores all the information about the game state.
    Used for keeping track of everything and sharing it between
    the asyncio tasks.
    """
    def __init__(self, difficulty: int, led_off_time: int, led_on_time: int):
        # how many blinks per sequence
        self.difficulty = difficulty

        # how long the LED should spend off during a blink
        self.led_off_time = led_off_time

        # how long the LED should spend on during a blink
        self.led_on_time = led_on_time

        # the player's current score
        self.score = 0

        # the current state for the state machine that controls how the game behaves.
        self.current_state = STATE_WAITING_TO_START

        # list to hold the sequence of colors that have been chosen
        self.sequence = []

        # the current index within the sequence
        self.index = 0

        # a timestamp that will be used to ignore button presses for a short period of time
        # to avoid accidental double presses.
        self.btn_cooldown_time = -1


async def player_action(game_state: GameState):
    """
    Read the buttons to determine if the player has pressed any of them, and react
    appropriately if so.

    :param game_state: The GameState object that holds the current state of the game.
    :return: None
    """
    # pylint: disable=too-many-branches, too-many-statements

    # access the global highscore variable
    global highscore  # pylint: disable=global-statement

    # loop forever inside of this task
    while True:
        # get any events that have occurred from the keypad object
        key_event = buttons.events.get()

        # if we're Waiting To Start
        if game_state.current_state == STATE_WAITING_TO_START:

            # if the buttons aren't locked out for cool down
            if game_state.btn_cooldown_time < time.monotonic():

                # if there is a released event on any key
                if key_event and key_event.released:

                    # hide the game over label
                    game_over_lbl.hidden = True

                    # show the starting score
                    curscore_val.text = str(game_state.score)
                    print("Starting game!")
                    # ready set go blinks
                    for _, led_obj in leds.items():
                        led_obj.value = True
                    await asyncio.sleep(250 / 1000)
                    for _, led_obj in leds.items():
                        led_obj.value = False
                    await asyncio.sleep(250 / 1000)
                    for _, led_obj in leds.items():
                        led_obj.value = True
                    await asyncio.sleep(250 / 1000)
                    for _, led_obj in leds.items():
                        led_obj.value = False
                    await asyncio.sleep(250 / 1000)
                    for _, led_obj in leds.items():
                        led_obj.value = True
                    await asyncio.sleep(250 / 1000)
                    for _, led_obj in leds.items():
                        led_obj.value = False

                    # change the state to Blinka's Turn
                    game_state.current_state = STATE_BLINKA_TURN

        # if it's Blinka's Turn
        elif game_state.current_state == STATE_BLINKA_TURN:
            # ignore buttons on Blinka's turn
            pass

        # if it's the Player's Turn
        elif game_state.current_state == STATE_PLAYER_TURN:

            # if a button has been pressed
            if key_event and key_event.pressed:
                # light up the corresponding LED in the button
                leds[COLORS[key_event.key_number]].value = True

            # if a button has been released
            if key_event and key_event.released:
                # turn off the corresponding LED in the button
                leds[COLORS[key_event.key_number]].value = False
                #print(key_event)
                #print(game_state.sequence)

                # if the color of the button pressed matches the current color in the sequence
                if COLORS[key_event.key_number] == game_state.sequence[0]:

                    # remove the current color from the sequence
                    game_state.sequence.pop(0)

                    # increment the score value
                    game_state.score += 1

                    # update the score label
                    curscore_val.text = str(game_state.score)

                    # if there are no colors left in the sequence
                    # i.e. the level is complete
                    if len(game_state.sequence) == 0:

                        # give a bonus point for finishing the level
                        game_state.score += 1

                        # increase the difficulty for next level
                        game_state.difficulty += 1

                        # update the score label
                        curscore_val.text = str(game_state.score)

                        # change the state to Blinka's Turn
                        game_state.current_state = STATE_BLINKA_TURN
                        print(f"difficulty after lvl: {game_state.difficulty}")

                # The pressed button color does not match the current color in the sequence
                # i.e. player pressed the wrong button
                else:
                    print("player lost!")
                    # show the game over label
                    game_over_lbl.hidden = False

                    # if the player's current score is higher than the highscore
                    if highscore is None or game_state.score > highscore:

                        # save new high score value to NVM storage
                        nvm_helper.save_data(("bls_hs", game_state.score), test_run=False)

                        # update global highscore variable to the players score
                        highscore = game_state.score

                        # update the high score label
                        highscore_val.text = str(game_state.score)

                    # change to Waiting to Start
                    game_state.current_state = STATE_WAITING_TO_START

                    # reset the current score to zero
                    game_state.score = 0

                    # reset the difficulty to 1
                    game_state.difficulty = 1

                    # enable the button cooldown timer to ignore any button presses
                    # in the near future to avoid double presses
                    game_state.btn_cooldown_time = time.monotonic() + 1.5

                    # reset the sequence to an empty list
                    game_state.sequence = []

        # sleep, allowing other asyncio tasks to take action
        await asyncio.sleep(0)


async def blinka_action(game_state: GameState):
    """
    Choose colors randomly to add to the sequence. Blink the LEDs in accordance
    with the sequence.

    :param game_state: The GameState object that holds the current state of the game.
    :return: None
    """

    # loop forever inside of this task
    while True:
        # if it's Blinka's Turn
        if game_state.current_state == STATE_BLINKA_TURN:
            print(f"difficulty start of blinka turn: {game_state.difficulty}")

            # if the sequence is empty
            if len(game_state.sequence) == 0:

                # loop for the current difficulty
                for _ in range(game_state.difficulty):
                    # append a random color to the sequence
                    game_state.sequence.append(random.choice(COLORS))
                print(game_state.sequence)

                # wait for LED_OFF amount of time
                await asyncio.sleep(game_state.led_off_time / 1000)

            # turn on the LED for the current color in the sequence
            leds[game_state.sequence[game_state.index]].value = True

            # wait for LED_ON amount of time
            await asyncio.sleep(game_state.led_on_time / 1000)

            # turn off the LED for the current color in the sequence
            leds[game_state.sequence[game_state.index]].value = False

            # wait for LED_OFF amount of time
            await asyncio.sleep(game_state.led_off_time / 1000)

            # increment the index
            game_state.index += 1

            # if the last index in the sequence has been passed
            if game_state.index >= len(game_state.sequence):

                # reset the index to zero
                game_state.index = 0

                # change to the Players Turn
                game_state.current_state = STATE_PLAYER_TURN
                print("players turn!")

        # sleep, allowing other asyncio tasks to take action
        await asyncio.sleep(0)


async def main():
    """
    Main asyncio task that will initialize the Game State and
    start the other tasks running.

    :return: None
    """

    # initialize the Game State
    game_state = GameState(1, 500, 500)

    # initialze player task
    player_task = asyncio.create_task(player_action(game_state))

    # initialize blinka task
    blinka_task = asyncio.create_task(blinka_action(game_state))

    # start the tasks running
    await asyncio.gather(player_task, blinka_task)

# run the main task
asyncio.run(main())
