"""
This example will access the adafruit.io API, grab a number like active users
and io plus subscribers... and display it on a screen
If you can find something that spits out JSON data, we can display it!
"""
import time
import board
from adafruit_pyportal import PyPortal

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Set up where we'll be fetching data from
DATA_SOURCE = "https://io.adafruit.com/api/v2/stats?x-aio-key="+secrets['aio_key']
DATA_LOCATION1 = ["io_plus", "io_plus_subscriptions"]
DATA_LOCATION2 = ["users", "users_active_30_days"]

cwd = ("/"+__file__).rsplit('/', 1)[0]
print(cwd)
pyportal = PyPortal(url=DATA_SOURCE,
                    json_path=(DATA_LOCATION1, DATA_LOCATION2),
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/adafruitio_background.bmp",
                    text_font=cwd+"/fonts/Collegiate-24.bdf",
                    text_position=((165, 170), (165, 200)),
                    text_color=(0x00FF00, 0x0000FF))

while True:
    try:
        value = pyportal.fetch()
        print("Response is", value)
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)

    time.sleep(60)
