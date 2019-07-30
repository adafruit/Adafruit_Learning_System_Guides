import time
import board
from adafruit_pyportal import PyPortal

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

PROJECT_NAME = "3c92f0"

# Set up where we'll be fetching data from
DATA_SOURCE = "https://api.hackster.io/v2/projects/"+PROJECT_NAME+"?"
DATA_SOURCE += "client_id="+secrets['hackster_clientid']
DATA_SOURCE += "&client_secret="+secrets['hackster_secret']
VIEWS_LOCATION = ['stats', 'views']
LIKES_LOCATION = ['stats', 'respects']
CAPTION = "http://www.hackster.com/project/"+PROJECT_NAME

# the current working directory (where this file is)
cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = PyPortal(url=DATA_SOURCE, json_path=(LIKES_LOCATION, VIEWS_LOCATION),
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/hackster_background.bmp",
                    text_font=cwd+"/fonts/Arial-Bold-24.bdf",
                    text_position=((80, 75), (80, 145)),
                    text_color=(0x0000FF, 0x000000),
                    caption_text=CAPTION,
                    caption_font=cwd+"/fonts/Arial-12.bdf",
                    caption_position=(20, 200),
                    caption_color=0x000000)

# track the last value so we can play a sound when it updates
last_likes = 0

while True:
    try:
        likes, views = pyportal.fetch()
        print("Views", views, "Likes", likes)
        if last_likes < likes:  # ooh it went up!
            print("New respect!")
            pyportal.play_file(cwd+"/coin.wav")
        last_likes = likes
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)

    time.sleep(60)
