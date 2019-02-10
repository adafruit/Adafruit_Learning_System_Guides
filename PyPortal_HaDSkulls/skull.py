"""
This example will access the Hackaday.io API, grab a number like hackaday skulls,
and display it on a screen
If you can find something that spits out JSON data, we can display it!
Note that you need a hackaday API key to access the API!
"""
import time
import board
from adafruit_pyportal import PyPortal

# Get wifi details and more from a settings.py file
try:
    from settings import settings
except ImportError:
    print("WiFi settings are kept in settings.py, please add them there!")
    raise

# Some data sources and JSON locations to try out
CAPTION="hackaday.io/project/163309-circuitpython-hackaday"
DATA_SOURCE = "https://api.hackaday.io/v1/projects/163309?api_key="+settings['hackaday_token']
DATA_LOCATION = ["skulls"]

cwd = __file__.rsplit('/', 1)[0] # the current working directory (where this file is)
pyportal = PyPortal(url=DATA_SOURCE, json_path=DATA_LOCATION,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/had_background.bmp",
                    text_font=cwd+"/fonts/Checkbook-50.bdf",
                    text_position=(200, 80),
                    text_color=0xFFFFFF,
                    caption_text=CAPTION,
                    caption_font=cwd+"/fonts/Arial.bdf",
                    caption_position=(10, 220),
                    caption_color=0xFFFFFF)

# track the last value so we can play a sound when it updates
last_value = 0

while True:
    try:
        value = pyportal.fetch()
        print("Response is", value)
        if last_value < value:  # ooh it went up!
            print("New skull!")
            pyportal.play_file(cwd+"/coin.wav")
        last_value = value
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)
    time.sleep(60)
