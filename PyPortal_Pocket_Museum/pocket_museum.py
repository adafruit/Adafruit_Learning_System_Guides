import random
import time
import board
import math
from random import randint
from adafruit_pyportal import PyPortal

# There's a few different places we look for data in the photo of the day
IMAGE_LOCATION = ["primaryImage"]
TITLE_LOCATION = ["title"]
ARTIST_LOCATION = ["artistDisplayName"]

# the current working directory (where this file is)
cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = PyPortal(json_path=(TITLE_LOCATION, ARTIST_LOCATION),
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/cute_background.bmp",
                    text_font=cwd+"/fonts/Arial-12.bdf",
                    text_position=((5, 220), (5, 200)),
                    text_color=(0xFFFFFF, 0xFFFFFF),
                    text_maxlen=(50, 50), # cut off characters
                    image_resize=(320, 240),
                    image_position=(0, 0),
                    debug = True)



print("loading...") # print to repl while waiting for font to load
pyportal.preload_font() # speed things up by preloading font
pyportal.set_text("\nWelcome to the Pocket Museum!") # show title


while True:

    # touch to display first / next art piece
    if pyportal.touchscreen.touch_point:

        #random work is selected
        RANDOM_ART = str(randint(1, 470000))

        try:

            try:
                # set image json path to change pictures when screen touched
                pyportal._url=("https://collectionapi.metmuseum.org/public/collection/v1/objects/"+RANDOM_ART)
                pyportal._image_json_path = (IMAGE_LOCATION)
                value = pyportal.fetch()
            except KeyError:
                continue
            print("Response is", value)
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)


