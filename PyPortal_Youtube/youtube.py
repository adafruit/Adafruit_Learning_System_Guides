"""
This example will access the youtube API, grab a number like number of views
or subscribers... and display it on a screen
If you can find something that spits out JSON data, we can display it!

Requires a youtube API key!
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
CHANNEL_ID = "UCpOlOeQjj7EsVnDh3zuCgsA" # this isn't a secret but you have to look it up
#CHANNEL_ID = "UC6p-tjZN8s9GBSbiN4K-bwg"
CAPTION = "www.youtube.com/adafruit"
#CAPTION = "www.youtube.com/c/JohnParkMakes"

# pylint: disable=line-too-long
DATA_SOURCE = "https://www.googleapis.com/youtube/v3/channels/?part=statistics&id="+CHANNEL_ID+"&key="+secrets['youtube_token']
DATA_LOCATION1 = ["items", 0, "statistics", "viewCount"]
DATA_LOCATION2 = ["items", 0, "statistics", "subscriberCount"]
# pylint: enable=line-too-long

# the current working directory (where this file is)
cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = PyPortal(url=DATA_SOURCE,
                    json_path=(DATA_LOCATION1, DATA_LOCATION2),
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/youtube_background.bmp",
                    text_font=cwd+"/fonts/Collegiate-50.bdf",
                    text_position=((100, 129), (155, 180)),
                    text_color=(0xFFFFFF, 0xFFFFFF),
                    caption_text=CAPTION,
                    caption_font=cwd+"/fonts/Collegiate-24.bdf",
                    caption_position=(40, 220),
                    caption_color=0xFFFFFF)

# track the last value so we can play a sound when it updates
last_subs = 0

while True:
    try:
        views, subs = pyportal.fetch()
        subs = int(subs)
        views = int(views)
        print("Subscribers:", subs)
        print("Views:", views)
        if last_subs < subs:  # ooh it went up!
            print("New subscriber!")
            pyportal.play_file(cwd+"/coin.wav")
        last_subs = subs
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)

    time.sleep(60)
