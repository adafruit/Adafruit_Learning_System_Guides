"""
Dashblock API Adafruit Learn Guide Count demo
Isaac Wellish
"""

import board
import time
from adafruit_pyportal import PyPortal

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi settings are kept in settings.py, please add them there!")
    raise

# Set up where we'll be fetching data from
DATA_SOURCE = "https://api.dashblock.io/model/v1?api_key=39c755c0-c84e-11e9-8ee0-7bf8836bd560&url=https%3A%2F%2Flearn.adafruit.com%2F&model_id=3rOMRrfFn"
GUIDE_COUNT = ['entities', 0, 'guide count']
CAPTION = 'learn.adafruit.com'

# determine the current working directory
# needed so we know where to find files
cwd = ("/"+__file__).rsplit('/', 1)[0]

# Initialize the pyportal object and let us know what data to fetch and where
# to display it
pyportal = PyPortal(url=DATA_SOURCE,
                    json_path = (GUIDE_COUNT),
                    status_neopixel=board.NEOPIXEL,
                    #default_bg=cwd+"/wordoftheday_background.bmp",
                    text_font=cwd+"/fonts/Arial-ItalicMT-17.bdf",
                    text_position=((50, 100)), # definition location
                    text_color=(0x8080FF),
                    text_wrap=(0),
                    text_maxlen=(180), # max text size for word, part of speech and def
                    caption_text=CAPTION,
                    caption_font=cwd+"/fonts/Arial-ItalicMT-17.bdf",
                    caption_position=(50, 220),
                    caption_color=0xFFFFFF)

print("loading...") # print to repl while waiting for font to load
pyportal.preload_font() # speed things up by preloading font

while True:
    try:
        # pylint: disable=protected-access
        value = pyportal.fetch()
        print("Response is", value)
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)

    time.sleep(3600) #update every hour
