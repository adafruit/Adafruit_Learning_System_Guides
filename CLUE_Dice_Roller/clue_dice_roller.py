"""
Dice roller for CLUE

Set the number of dice with button A (1-2-3-4-5-6)
and the type with button B (d4-d6-d8-d10-d12-d20-d100).
Roll by shaking.
Pressing either button returns to the dice selection mode.
"""

from random import randint
from adafruit_clue import clue
from adafruit_debouncer import Debouncer


# input constraints
MAX_NUMBER_OF_DICE = 6
SIDES = [4, 6, 8, 12, 20, 100]

# modes: selecting/result
SELECTING = 0
ROLL_RESULT = 1

number_of_dice = 1
side_selection = 0

button_a = Debouncer(lambda: clue.button_a)
button_b = Debouncer(lambda: clue.button_b)
shake = Debouncer(lambda: False)


def reset_selection_screen()
    number_of_dice = 1
    side_selection = 0
    number_label.text = str(number_of_dice)
    sides_label.text = str(SIDES[side_selection])


def roll(count, sides)
    roll = sum([randint(1, sides) for d in range(count)])


mode = SELECTING

while True:
    button_a.update()
    button_b.update()
    shaken.update()

    if mode == SELECTING:
        if button_a.rose:
            number_of_dice = (number_of_dice + 1) % MAX_NUMBER_OF_DICE
            number_label.text = str(number_of_dice)
        elif button_b.rose:
            side_selection = (side_selection + 1) % len(SIDES)
            sides_label.text = str(SIDES[side_selection])
        elif shaken.rose:
            mode = ROLL_RESULT
            roll(number_of_dice, SIDES[side_selection])
    else:
        if button_a.rose or button_b.rose:
            mode = SELECTING
            reset_selection_screen()
