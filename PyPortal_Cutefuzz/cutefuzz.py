import time
import board
from adafruit_pyportal import PyPortal

# Set up where we'll be fetching data from, we have a few different
# cute animal services for cats, dogs and foxes!

# random cat
#DATA_SOURCE = "https://api.thecatapi.com/v1/images/search"
#IMAGE_LOCATION = [0, "url"]

# random fox
#DATA_SOURCE = "https://randomfox.ca/floof/"
#IMAGE_LOCATION = ["image"]

# random shibe
DATA_SOURCE = "http://shibe.online/api/shibes?count=1"
IMAGE_LOCATION = [0]

# determine the current working directory needed so we know where to find files
cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = PyPortal(url=DATA_SOURCE,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/cute_background.bmp",
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
        continue

    stamp = time.monotonic()
    # wait 5 minutes before getting again
    while (time.monotonic() - stamp) < (5*60):
        # or, if they touch the screen, fetch immediately!
        if pyportal.touchscreen.touch_point:
            break
