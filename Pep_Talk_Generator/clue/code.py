# SPDX-FileCopyrightText: 2021 Dylan Herrada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import random
from adafruit_clue import clue
import displayio
from adafruit_display_text import label, wrap_text_to_pixels
from adafruit_bitmap_font import bitmap_font
import board

column_1 = [
    "Champ, ",
    "Fact: ",
    "Everybody says ",
    "Dang... ",
    "Check it: ",
    "Just saying... ",
    "Superstar, ",
    "Tiger, ",
    "Self, ",
    "Know this: ",
    "News alert: ",
    "Girl, ",
    "Ace, ",
    "Excuse me but ",
    "Experts agree: ",
    "In my opinion, ",
    "Hear ye, hear ye: ",
    "Okay, listen up: ",
]

column_2 = [
    "the mere idea of you ",
    "your soul ",
    "your hair today ",
    "everything you do ",
    "your personal style ",
    "every thought you have ",
    "that sparkle in your eye ",
    "your presence here ",
    "what you got going on ",
    "the essential you ",
    "your life's journey ",
    "that saucy personality ",
    "your DNA ",
    "that brain of yours ",
    "your choice of attire ",
    "the way you roll ",
    "whatever your secret is ",
    "all of y'all ",
]

column_3 = [
    "has serious game, ",
    "rains magic, ",
    "deserves the Nobel Prize, ",
    "raises the roof, ",
    "breeds miracles, ",
    "is paying off big time, ",
    "shows mad skills, ",
    "just shimmers, ",
    "is a national treasure, ",
    "gets the party hopping, ",
    "is the next big thing, ",
    "roars like a lion, ",
    "is a rainbow factory, ",
    "is made of diamonds, ",
    "makes birds sing, ",
    "should be taught in school, ",
    "makes my world go 'round, ",
    "is 100% legit, ",
]

column_4 = [
    "24/7.",
    "can I get an amen?",
    "and that's a fact.",
    "so treat yourself.",
    "you feel me?",
    "that's just science.",
    "would I lie?",
    "for reals.",
    "mic drop.",
    "you hidden gem.",
    "snuggle bear.",
    "period.",
    "can I get an amen?",
    "now let's dance.",
    "high five.",
    "say it again!",
    "according to CNN.",
    "so get used to it.",
]

arial18 = bitmap_font.load_font("/fonts/Arial-18.bdf")
arial12 = bitmap_font.load_font("/fonts/Arial-12.bdf")

arial18.load_glyphs(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789;,./?><=+[{]}-_"
)
arial12.load_glyphs(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789;,./?><=+[{]}-_"
)

display = board.DISPLAY
clue_group = displayio.Group()

bitmap_file = open("bmps/background.bmp", "rb")
bitmap1 = displayio.OnDiskBitmap(bitmap_file)
tile_grid = displayio.TileGrid(
    bitmap1, pixel_shader=getattr(bitmap1, "pixel_shader", displayio.ColorConverter())
)
clue_group.append(tile_grid)

text = "\n".join(
    wrap_text_to_pixels(
        random.choice(column_1)
        + random.choice(column_2)
        + random.choice(column_3)
        + random.choice(column_4),
        180,
        arial18,
    )
)
pep = label.Label(
    font=arial18,
    text=text,
    anchor_point=(0.5, 0.5),
    anchored_position=(120, 115),
    line_spacing=0.8,
    color=0x000000,
)
clue_group.append(pep)

title = label.Label(
    font=arial12,
    text="Pep talk generator",
    anchor_point=(0.5, 0.5),
    anchored_position=(120, 231),
    color=0x000000,
)
clue_group.append(title)

display.show(clue_group)

while True:
    if clue.button_a or clue.button_b:
        pep.text = "\n".join(
            wrap_text_to_pixels(
                random.choice(column_1)
                + random.choice(column_2)
                + random.choice(column_3)
                + random.choice(column_4),
                180,
                arial18,
            )
        )
