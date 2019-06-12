"""
This example will access the lastFM API, grab a number like subreddit followers
and display it on a screen
If you can find something that spits out JSON data, we can display it!
"""
import time
import board
from adafruit_pyportal import PyPortal

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Set up where we'll be fetching data from
DATA_SOURCE = "http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&limit=1&format=json"
CAPTION = "www.last.fm/user"
# If we have an access token, we can query more often
if 'lfm_username' in secrets:
    DATA_SOURCE += "&user="+secrets['lfm_username']
    CAPTION += "/"+secrets['lfm_username']
if 'lfm_key' in secrets:
    DATA_SOURCE += "&api_key="+secrets['lfm_key']
print(DATA_SOURCE)

# Total number of plays
DATA_LOCATION = ["recenttracks", "@attr", "totalPages"]

# the current working directory (where this file is)
cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = PyPortal(url=DATA_SOURCE, json_path=DATA_LOCATION,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/lastfm_background.bmp",
                    text_font=cwd+"/fonts/Collegiate-50.bdf",
                    text_position=(150, 160),
                    text_color=0xFFFFFF,
                    caption_text=CAPTION,
                    caption_font=cwd+"/fonts/Collegiate-24.bdf",
                    caption_position=(40, 220),
                    caption_color=0xFFFFFF,
                    debug=True)

# track the last value so we can play a sound when it updates
last_value = 0

while True:
    try:
        value = pyportal.fetch()
        print("Response is", value)
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)

    time.sleep(60)
