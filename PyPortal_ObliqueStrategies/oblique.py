"""
This code will display a random strategy from strategies.py when the
PyPortal screen is pressed. See the original Oblique Strategies
by Brian Eno & Peter Schmidt here: https://www.enoshop.co.uk/product/oblique-strategies
"""
import random
import board
from strategies import strategies
from adafruit_pyportal import PyPortal

cwd = ("/"+__file__).rsplit('/', 1)[0] # the current working directory (where this file is)

# create pyportal object w no data source (we'll feed it text later)
pyportal = PyPortal(url = None,
                    json_path = None,
                    status_neopixel = board.NEOPIXEL,
                    default_bg = None,
                    text_font = cwd+"fonts/Arial-ItalicMT-17.bdf",
                    text_position = (30, 120),
                    text_color = 0xFFFFFF,
                   )

pyportal.set_text("loading ...") # display while user waits
pyportal.preload_font() # speed things up by preloading font
pyportal.set_text("OBLIQUE STRATEGIES\nBrian Eno / Peter Schmidt") # show title

while True:
    if pyportal.touchscreen.touch_point:
        # get random string from array and wrap w line breaks
        strat = pyportal.wrap_nicely(random.choice(strategies), 35)
        outstring = '\n'.join(strat)
        # display new text
        pyportal.set_text(outstring, 0)
        # don't repeat until a new touch begins
        while pyportal.touchscreen.touch_point:
            continue
