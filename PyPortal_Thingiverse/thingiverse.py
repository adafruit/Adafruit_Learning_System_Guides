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
NUM_THINGS=25  # how many things to select from (we randomize between em)
DATA_SOURCE = "https://api.thingiverse.com/users/adafruit/things?per_page="+str(NUM_THINGS)
DATA_SOURCE += "&access_token=" + secrets['thingiverse_token']
IMAGE_LOCATION = [0, "thumbnail"]
TITLE_LOCATION = [0, "name"]
URL_LOCATION = [0, "public_url"]

# determine the current working directory needed so we know where to find files
cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = adafruit_pyportal.PyPortal(url=DATA_SOURCE,
                                      json_path=(TITLE_LOCATION, URL_LOCATION, IMAGE_LOCATION),
                                      status_neopixel=board.NEOPIXEL,
                                      default_bg=cwd+"/thingiverse_background.bmp",
                                      text_font=cwd+"/fonts/Arial-12.bdf",
                                      text_position=((5, 10), (5, 230)),
                                      text_color=(0x00FF00, 0x00FF00),
                                      text_transform=(None, None))
pyportal.preload_font()

while True:
    response = None
    try:
        response = pyportal.fetch()
        print("Response is", response)
        pyportal.set_background(None)
        image_url = response[2].replace('_thumb_medium.', '_display_large.')
        pyportal.wget(pyportal.image_converter_url(image_url,320, 240,color_depth=16),
                      "/cache.bmp",
                      chunk_size=512)
        pyportal.set_background("/cache.bmp")

    except (IndexError, RuntimeError, ValueError) as e:
        print("Some error occured, retrying! -", e)

    # next thingy should be random!
    thingy = random.randint(0, NUM_THINGS - 1)
    URL_LOCATION[0] = TITLE_LOCATION[0] = IMAGE_LOCATION[0] = thingy

    time.sleep(60 * 3)  # cycle every 3 minutes
