# SPDX-FileCopyrightText: 2021 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import json
import terminalio
import digitalio
import random
from adafruit_magtag.magtag import MagTag

# Set up the magtag
print("Magtag Basic Flashcards")
magtag = MagTag()

# Import cards
cards = {}
with open("deck.json") as fp:
    cards = json.load(fp)

# Create a text area
magtag.add_text(
    text_font="yasashi20.pcf",
    text_position=(
        magtag.graphics.display.width // 2,
        magtag.graphics.display.height // 2,
    ),
    line_spacing=0.85,
    text_anchor_point=(0.5, 0.5),
)

# Set up buttons
cur_btn = False
prev_btn = False

while True:
    # Shuffle the deck
    cards = sorted(cards, key=lambda _: random.random())
    for card in cards:

        # Show the first side and wait for the D button
        text = ''.join(magtag.wrap_nicely(card[0], 20))
        magtag.set_text(text)
        while True:
            cur_btn = magtag.peripherals.button_d_pressed
            if cur_btn and not prev_btn:
                print("Show Result")
                time.sleep(0.1)
                break
            prev_btn = cur_btn

        # Show the second side and wait for the D button
        text = '\n'.join(magtag.wrap_nicely(card[1], 11))
        text += '\n'
        text += '\n'.join(magtag.wrap_nicely(card[2], 20))
        print(text)
        magtag.set_text(text)
        while True:
            cur_btn = magtag.peripherals.button_d_pressed
            if cur_btn and not prev_btn:
                print("Next Card")
                time.sleep(0.1)
                break
            prev_btn = cur_btn
