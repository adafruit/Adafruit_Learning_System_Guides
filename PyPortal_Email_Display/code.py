"""
PyPortal Adafruit IO Feed Display

Displays an Adafruit IO Feed on a PyPortal.
"""
import time
import board
from adafruit_pyportal import PyPortal

# Get Adafruit IO details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("Adafruit IO secrets are kept in secrets.py, please add them there!")
    raise

# Adafruit IO Account
IO_USER = secrets['aio_username']
IO_KEY = secrets['aio_key']
# Adafruit IO Feed
IO_FEED = 'zapemail'

DATA_SOURCE = "https://io.adafruit.com/api/v2/{0}/feeds/{1}?X-AIO-Key={2}".format(IO_USER,
                                                                                  IO_FEED, IO_KEY)
FEED_VALUE_LOCATION = ['last_value']

cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = PyPortal(url=DATA_SOURCE,
                    json_path=FEED_VALUE_LOCATION,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/pyportal_email.bmp",
                    text_font=cwd+"/fonts/Helvetica-Oblique-17.bdf",
                    text_position=(30, 65),
                    text_color=0xFFFFFF,
                    text_wrap=35, # wrap feed after 35 chars
                    text_maxlen=160)

# speed up projects with lots of text by preloading the font!
pyportal.preload_font()

while True:
    try:
        print('Fetching Adafruit IO Feed Value..')
        value = pyportal.fetch()
        print("Response is", value)
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)
    time.sleep(10)
