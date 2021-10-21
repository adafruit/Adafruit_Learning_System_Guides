# SPDX-FileCopyrightText: 2020 Collin Cunningham for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
"""ACTIVITY GENERATOR for Adafruit CLUE"""

import time
import random
from adafruit_clue import clue
from things import activities
from things import subjects

screen = clue.simple_text_display(text_scale=4, colors=(clue.WHITE,))

screen[1].text = "ACTIVITY"
screen[2].text = "GENERATOR"
screen.show()
time.sleep(1.5)

screen[0].text = "make a"
screen[2].text = "about"
screen[1].color = clue.RED
screen[3].color = clue.GREEN
screen[4].color = clue.BLUE

activity = "???"
subject_a = "???"
subject_b = "???"
two_subjects = True

def random_pick(items):
    index = random.randint(0, len(items)-1)
    return items[index]

while True:

    if clue.button_a:
        activity = random_pick(activities)
        subject_a = random_pick(subjects)
        subject_b = random_pick(subjects)
        time.sleep(0.25)
    if clue.button_b:
        two_subjects = not two_subjects
        time.sleep(0.5)

    screen[1].text = activity
    screen[3].text = subject_a

    if two_subjects:
        screen[4].text = subject_b
    else:
        screen[4].text = ""

    screen.show()
