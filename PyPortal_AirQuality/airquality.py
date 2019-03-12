"""
This example will access the twitter follow button API, grab a number like
the number of followers... and display it on a screen!
if you can find something that spits out JSON data, we can display it
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

# Change this to your zip code, not all locations have AQI data. Check
# https://airnow.gov/ to see if there's data available!
LOCATION = "90210"

# Set up where we'll be fetching data from
DATA_SOURCE = "http://www.airnowapi.org/aq/forecast/zipCode/?format=application/json"
# You'll need to get a token from airnow.gov, looks like '4d36e978-e325-11cec1-08002be10318'
DATA_SOURCE += "&zipCode="+LOCATION+"&API_KEY="+secrets['airnow_token']
DATA_LOCATION = [1, "AQI"]

# the current working directory (where this file is)
cwd = ("/"+__file__).rsplit('/', 1)[0]
# Initialize the pyportal object and let us know what data to fetch and where
# to display it
pyportal = PyPortal(url=DATA_SOURCE,
                    json_path=DATA_LOCATION,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=0x000000,
                    text_font=cwd+"/fonts/Helvetica-Bold-100.bdf",
                    text_position=(90, 100),
                    text_color=0x000000,
                    caption_text="Air Quality Index for "+LOCATION,
                    caption_font=cwd+"/fonts/HelveticaNeue-24.bdf",
                    caption_position=(15, 220),
                    caption_color=0x000000,)

while True:
    try:
        value = pyportal.fetch()
        print("Response is", value)
        if 0 <= value <= 50:
            pyportal.set_background(0x66bb6a)  # good
        if 51 <= value <= 100:
            pyportal.set_background(0xffeb3b)  # moderate
        if 101 <= value <= 150:
            pyportal.set_background(0xf39c12)  # sensitive
        if 151 <= value <= 200:
            pyportal.set_background(0xff5722)  # unhealthy
        if 201 <= value <= 300:
            pyportal.set_background(0x8e24aa)  # very unhealthy
        if 301 <= value <= 500:
            pyportal.set_background(0xb71c1c ) # hazardous

    except RuntimeError as e:
        print("Some error occured, retrying! -", e)

    time.sleep(10*60)  # wait 10 minutes before getting again
