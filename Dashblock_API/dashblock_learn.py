"""
Dashblock API Adafruit Learn Guide Count demo
Use Dashblock to create a custom API for learn.adafruit.com,
then display the number of learn guides on the site
"""

import time
import board
from adafruit_pyportal import PyPortal

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi settings are kept in settings.py, please add them there!")
    raise

# Set up where we'll be fetching data from
DATA_SOURCE = "https://api.dashblock.io/model/v1?api_key=" + secrets['dashblock_key']
GUIDE_COUNT = ['entities', 0, 'guide count']
CAPTION = 'total tutorials:'

# determine the current working directory
# needed so we know where to find files
cwd = ("/"+__file__).rsplit('/', 1)[0]

# Initialize the pyportal object and let us know what data to fetch and where
# to display it
pyportal = PyPortal(url=DATA_SOURCE,
                    json_path = (GUIDE_COUNT),
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/adabot_cover.bmp",
                    text_font=cwd+"/fonts/Collegiate-50.bdf",
                    text_position=((40, 100)),
                    text_color=(0x8080FF),
                    text_maxlen=(4), # max text length, only want first 4 chars for number of guides
                    caption_text=CAPTION,
                    caption_font=cwd+"/fonts/Collegiate-24.bdf",
                    caption_position=(40, 60),
                    caption_color=0xFFFFFF)

# track the last value so we can play a sound when it updates
last_value = 0

while True:
    try:
        value = pyportal.fetch()
        print("Response is", value)
        int_value = int(value[:4]) # save only first 4 chars and cast to int
        if last_value < int_value:  # ooh it went up!
            print("New guide!")
            pyportal.play_file(cwd+"/coin.wav")  # make a noise!
        last_value = int_value
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)
    except ValueError as e:
        print("Value error occured, retrying! -", e)
        continue

    time.sleep(600) #update every 10 mins
