import time
import board
import adafruit_pyportal

# We can cycle through the latest featured products
#PRODUCTS_TYPE = "featured"
#or we can view the latest new products
PRODUCTS_TYPE = "new"

# Set up where we'll be fetching data from
DATA_SOURCE = "https://www.adafruit.com/api/products?format=micro&"+PRODUCTS_TYPE+"=1&random=1"
# What data we'll be viewing
IMAGE_LOCATION = [0, "image"]
NAME_LOCATION = [0, "name"]
URL_LOCATION = [0, "url"]

# determine the current working directory needed so we know where to find files
cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = adafruit_pyportal.PyPortal(url=DATA_SOURCE,
                                      json_path=(NAME_LOCATION, URL_LOCATION),
                                      status_neopixel=board.NEOPIXEL,
                                      default_bg=cwd+"/new_background.bmp",
                                      text_font=cwd+"/fonts/Arial-Bold-12.bdf",
                                      text_position=((5, 35), (5, 225)),
                                      text_color=(0xFFFFFF, 0xFFFFFF),
                                      text_wrap=(35, 35), # characters to wrap
                                      image_json_path=IMAGE_LOCATION,
                                      image_resize=(320, 240),
                                      image_position=(0, 0))
pyportal.preload_font()

while True:
    response = None
    try:
        response = pyportal.fetch()
        print("Response is", response)
    except (IndexError, RuntimeError, ValueError) as e:
        print("Some error occured, retrying! -", e)

    time.sleep(60)
