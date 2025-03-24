# SPDX-FileCopyrightText: 2020 Dave Astels for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Dice roller for CLUE

Set the number of dice with button A (1-2-3-4-5-6)
and the type with button B (d4-d6-d8-d10-d12-d20-d100).
Roll by shaking.
Pressing either button returns to the dice selection mode.
"""

import time
from random import randint
import board
from adafruit_clue import clue
from adafruit_debouncer import Debouncer
import displayio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label


# input constraints
MAX_NUMBER_OF_DICE = 6
SIDES = [4, 6, 8, 10, 12, 20, 100]

# modes: selecting/result
SELECTING = 0
ROLL_RESULT = 1

# 0-relative, gets adjusted to 1-relative before display/use
number_of_dice = 0
side_selection = 0

button_a = Debouncer(lambda: clue.button_a)
button_b = Debouncer(lambda: clue.button_b)

# Set up display

select_font = bitmap_font.load_font('/Helvetica-Bold-36.bdf')
select_font.load_glyphs(b'0123456789XDd')
select_color = 0xDB4379

roll_font = bitmap_font.load_font('/Anton-Regular-104.bdf')
roll_font.load_glyphs(b'0123456789X')
roll_color = 0xFFFFFF

select_label = label.Label(select_font, x=0, y=25, text='XdXXX', color=select_color)
roll_label = label.Label(roll_font, x=0, y=150, text='XXX', color=roll_color)

group = displayio.Group()
group.append(select_label)
group.append(roll_label)

board.DISPLAY.root_group = group

# Helper functions

def roll(count, sides):
    select_label.text = ''
    for i in range(15):
        roll_value = sum([randint(1, sides) for _ in range(count + 1)])
        roll_label.text = str(roll_value)
        roll_label.x = 120 - (roll_label.bounding_box[2] // 2)
        duration = (i * 0.05) / 2
        clue.play_tone(2000, duration)
        time.sleep(duration)


def update_display(count, sides):
    select_label.text = '{0}d{1}'.format(count + 1, SIDES[sides])
    select_label.x = 120 - (select_label.bounding_box[2] // 2)
    roll_label.text = ''


mode = SELECTING
update_display(number_of_dice, side_selection)

while True:
    button_a.update()
    button_b.update()

    if mode == SELECTING:
        if button_a.rose:
            number_of_dice = ((number_of_dice + 1) % MAX_NUMBER_OF_DICE)
            update_display(number_of_dice, side_selection)
        elif button_b.rose:
            side_selection = (side_selection + 1) % len(SIDES)
            update_display(number_of_dice, side_selection)
        elif clue.shake(shake_threshold=25):
            mode = ROLL_RESULT
            if SIDES[side_selection] == 100:   # only roll one percentile
                number_of_dice = 0
                update_display(number_of_dice, side_selection)
            roll(number_of_dice, SIDES[side_selection])
    else:
        if button_a.rose or button_b.rose:   # back to dice selection
            mode = SELECTING
            update_display(number_of_dice, side_selection)
        elif clue.shake(shake_threshold=25):   # reroll
            roll(number_of_dice, SIDES[side_selection])
