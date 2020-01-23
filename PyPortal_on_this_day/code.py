import random
import board
import time
from adafruit_pyportal import PyPortal

cwd = ("/"+__file__).rsplit('/', 1)[0] # the current working directory (where this file is)

DAY = ["Day of the year"]
PERSON = ["Person"]
NOTABLE = ["Notable for"]
YEAR = ["Year"]
ACCOMPLISH = ["Accomplishment"]
WEB = ["Web Reference"]

DATA = cwd+"/local.txt"

# create pyportal object w no data source (we'll feed it text later)
pyportal = PyPortal(url = DATA,
                    json_path = (DAY, PERSON, NOTABLE, YEAR, ACCOMPLISH, WEB),
                    status_neopixel = board.NEOPIXEL,
                    default_bg = none,
                    text_font = cwd+"fonts/Arial-ItalicMT-17.bdf",
                    text_position=((10, 70), (10, 100), (10, 130),(60, 160), (105, 190), (10, 220)),
                    text_color=(0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF),
                    text_maxlen=(50, 50, 50, 50, 50, 50), # cut off characters
                   )

while True:
    response = None
    try:
        response = pyportal.fetch()
        print("Response is", response)
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)

    time.sleep(60)