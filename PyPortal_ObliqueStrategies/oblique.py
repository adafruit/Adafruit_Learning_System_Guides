"""
This code will display a random strategy from strategies.py when the
PyPortal screen is pressed. See the original Oblique Strategies 
by Brian Eno & Peter Schmidt here: https://www.enoshop.co.uk/product/oblique-strategies
"""
import time
import board
import os
import random
from strategies import strategies
from adafruit_pyportal import PyPortal

cwd = os.getcwd() # the current working directory (where this file is)
wrap = 35 # text wrap value
firstload = True

# create pyportal object w no data source (we'll feed it text later)
pyportal = PyPortal(url = None,
                    json_path = None,
                    status_neopixel = board.NEOPIXEL,
                    default_bg = None,
                    text_font = cwd+"fonts/Arial-ItalicMT-17.bdf",
                    text_position = (30, 100),
                    text_color = 0xFFFFFF,
                    text_wrap = wrap,
                    text_maxlen = 180, # max text size for quote & author
                   )
                   
pyportal.set_text("loading ...") # display while user waits

pyportal.preload_font() # speed things up by preloading font

while True:
    # show title on first load
    if firstload:
        pyportal.set_text("OBLIQUE STRATEGIES\nBrian Eno / Peter Schmidt")
        firstload = False
    touch = pyportal.touchscreen.touch_point
    if touch:
        print(touch)
        # get random string from array and wrap
        index = random.randint(0, len(strategies)-1)
        strat = pyportal.wrap_nicely(strategies[index], wrap)
        # convert wrap array into line breaks
        outstring = ""
        for s in strat:
            outstring += s + "\n"
        # load new text
        pyportal.set_text(outstring, 0)
        time.sleep(0.5)