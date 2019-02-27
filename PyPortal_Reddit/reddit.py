"""
This example will access the reddit API, grab a number like subreddit followers
and display it on a screen
If you can find something that spits out JSON data, we can display it!
"""
import time
import board
from adafruit_pyportal import PyPortal

SUBREDDIT = "circuitpython"

# Set up where we'll be fetching data from
DATA_SOURCE = "https://www.reddit.com/r/"+SUBREDDIT+"/about.json"
DATA_LOCATION = ["data", "subscribers"]
CAPTION="reddit.com/r/"+SUBREDDIT

# the current working directory (where this file is)
cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = PyPortal(url=DATA_SOURCE, json_path=DATA_LOCATION,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/reddit_background.bmp",
                    text_font=cwd+"/fonts/Collegiate-50.bdf",
                    text_position=(210, 80),
                    text_color=0xFFFFFF,
                    caption_text=CAPTION,
                    caption_font=cwd+"/fonts/Collegiate-24.bdf",
                    caption_position=(40, 200),
                    caption_color=0xFFFFFF)

# track the last value so we can play a sound when it updates
last_value = 0

while True:
    try:
        value = pyportal.fetch()
        print("Response is", value)
        if last_value < value:  # ooh it went up!
            print("New subscriber!")
            pyportal.play_file(cwd+"/coin.wav")
        last_value = value
    except (ValueError, RuntimeError) as e:
        print("Some error occured, retrying! -", e)

    time.sleep(60)
