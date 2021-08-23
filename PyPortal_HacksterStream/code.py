import time
import random
import board
import adafruit_pyportal

# Get wifi details and more from a settings.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Set up where we'll be fetching data from
DATA_SOURCE = "https://api.hackster.io/v2/projects?"
DATA_SOURCE += "client_id="+secrets['hackster_clientid']
DATA_SOURCE += "&client_secret="+secrets['hackster_secret']
IMAGE_LOCATION = ['records', 0, "cover_image_url"]
TITLE_LOCATION = ['records',0, "name"]
HID_LOCATION = ['records', 0, "hid"]
NUM_PROJECTS = 24

# determine the current working directory needed so we know where to find files
cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = adafruit_pyportal.PyPortal(url=DATA_SOURCE,
                                      json_path=(TITLE_LOCATION, HID_LOCATION),
                                      image_json_path=IMAGE_LOCATION,
                                      image_position=(0, 0),
                                      image_resize=(320, 240),
                                      status_neopixel=board.NEOPIXEL,
                                      default_bg=cwd+"/hackster_background.bmp",
                                      text_font=cwd+"/fonts/Arial-Bold-12.bdf",
                                      text_position=((5, 5), (5, 200)),
                                      text_color=(0xFF0000, 0xFF0000),
                                      text_wrap=(40, 40))
pyportal.preload_font()

while True:
    response = None
    try:
        response = pyportal.fetch()
        print("Response is", response)
        pyportal.set_text("http://hackster.com/project/"+response[1], 1)
    except (IndexError, RuntimeError, ValueError) as e:
        print("Some error occured, retrying! -", e)

    # next thingy should be random!
    thingy = random.randint(0, NUM_PROJECTS-1)
    HID_LOCATION[1] = TITLE_LOCATION[1] = IMAGE_LOCATION[1] = thingy

    time.sleep(60 * 3)  # cycle every 3 minutes
