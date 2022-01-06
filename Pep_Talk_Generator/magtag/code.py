# SPDX-FileCopyrightText: 2021 Eva Herrada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import random
from adafruit_magtag.magtag import MagTag

magtag = MagTag(default_bg="/bmps/background.bmp")

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


magtag.add_text(
    text_font="/fonts/Arial-16.bdf",
    text_position=((magtag.graphics.display.width // 2), 49),
    text_anchor_point=(0.5, 0.5),
    text_wrap=22,
    line_spacing=0.7,
)

magtag.set_text(
    random.choice(column_1)
    + random.choice(column_2)
    + random.choice(column_3)
    + random.choice(column_4),
    0,
    False,
)

magtag.add_text(
    text_font="/fonts/Arial-12.bdf",
    text_position=((magtag.graphics.display.width // 2), 116),
    text_anchor_point=(0.5, 0.5),
    line_spacing=0.7,
    is_data=False,
)

magtag.set_text("Pep talk generator", 1)

magtag.exit_and_deep_sleep(60)
