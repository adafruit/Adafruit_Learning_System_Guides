"""
This example will access shields.io API, grab the SVG graphic and then use
regular expression search to locate the number of online discord users, then
display it on a screen.
If you can find something that spits out text, we can display it!
"""
import time
import board
from adafruit_pyportal import PyPortal

# Set up where we'll be fetching data from
DATA_SOURCE = "https://img.shields.io/discord/327254708534116352.svg"
# a regular expression for finding the data within the SVG xml text!
DATA_LOCATION = [r">([0-9]+ online)<"]

cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = PyPortal(url=DATA_SOURCE, regexp_path=DATA_LOCATION,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/discord_background.bmp",
                    text_font=cwd+"/fonts/Collegiate-50.bdf",
                    text_position=(70, 216), text_color=0x000000)

while True:
    try:
        value = pyportal.fetch()
        print("Response is", value)
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)
    time.sleep(60)
