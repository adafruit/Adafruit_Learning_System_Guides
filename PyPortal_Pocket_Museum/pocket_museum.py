import random
import time
import board
import math
from adafruit_pyportal import PyPortal

RANDOM_ART = str(math.floor(random.uniform(0, 470000)))
print(RANDOM_ART)
# Set up where we'll be fetching data from
DATA_SOURCE = "https://collectionapi.metmuseum.org/public/collection/v1/objects/"+RANDOM_ART
# There's a few different places we look for data in the photo of the day
IMAGE_LOCATION = ["primaryImage"]
TITLE_LOCATION = ["title"]
ARTIST_LOCATION = ["artistDisplayName"]

# the current working directory (where this file is)
cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = PyPortal(url=DATA_SOURCE,
                    json_path=(TITLE_LOCATION, ARTIST_LOCATION),
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/cute_background.bmp",
                    text_font=cwd+"/fonts/Arial-12.bdf",
                    text_position=((5, 220), (5, 200)),
                    text_color=(0xFFFFFF, 0xFFFFFF),
                    text_maxlen=(50, 50), # cut off characters
                    image_json_path=IMAGE_LOCATION,
                    image_resize=(320, 240),
                    image_position=(0, 0))

while True:
    response = None
    try:
        response = pyportal.fetch()
        print("Response is", response)
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)

    time.sleep(60)  # 60 seconds till next check