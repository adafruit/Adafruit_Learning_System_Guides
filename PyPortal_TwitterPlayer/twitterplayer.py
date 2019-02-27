import time
import os
import random
import board
from adafruit_pyportal import PyPortal

# Set up where we'll be fetching data from
TWITTER_USER = "DuneQuoteBot"
TWITTER_TO_XML = "https://twitrss.me/twitter_user_to_rss/?user="
XML_TO_JSON = "http://www.unmung.com/mf2?url=http://www.unmung.com/feed?feed="
NUM_TWEETS=20  # how many tweets we get within a query to randomize from
DATA_SOURCE = XML_TO_JSON+TWITTER_TO_XML+TWITTER_USER
TEXT_LOCATION = ["items", 0, "children", 0, "properties", "name", 0]

# the current working directory (where this file is)
cwd = ("/"+__file__).rsplit('/', 1)[0]

# Find all image files on the storage
imagefiles = [file for file in os.listdir(cwd+"/backgrounds/")
              if (file.endswith(".bmp") and not file.startswith("._"))]
for i, filename in enumerate(imagefiles):
    imagefiles[i] = cwd+"/backgrounds/"+filename
print("Image files found: ", imagefiles)

pyportal = PyPortal(url=DATA_SOURCE,
                    json_path=TEXT_LOCATION,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=imagefiles[0],
                    text_font=cwd+"/fonts/Arial-Italic-12.bdf",
                    text_position=(25, 20),
                    text_color=0xFFFFFF,
                    text_wrap=35, # character to wrap around
                    text_maxlen=280, # cut off characters
                   )
pyportal.preload_font()

while True:
    response = None
    try:
        pyportal.set_background(random.choice(imagefiles))
        response = pyportal.fetch()
        print("Response is", response)
    except (IndexError, RuntimeError, ValueError) as e:
        print("Some error occured, retrying! -", e)

    # next tweet should be random!
    tweet_idx = random.randint(0, NUM_TWEETS)
    TEXT_LOCATION[3] = tweet_idx
    time.sleep(60)
