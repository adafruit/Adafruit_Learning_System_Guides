import time
import board
from adafruit_pyportal import PyPortal

# Get wifi details and more from a settings.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi settings are kept in settings.py, please add them there!")
    raise

# Set up where we'll be fetching data from
DATA_SOURCE = "https://api.wordnik.com/v4/word.json/vermiculate/topExample?useCanonical=false&api_key="+secrets['wordnik_token']
CAPTION = 'Example'
EXAMPLE_LOCATION = ['text']
PUBLISH_DATE = ['publishDate']
URLCAP = ['wordnik.com/word-of-the-day']

cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = PyPortal(url=DATA_SOURCE,
                    json_path=(EXAMPLE_LOCATION),  #PART_OF_SPEECH, PUBLISH_DATE
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/wordoftheday_background.bmp",
                    text_font=cwd+"/fonts/Arial-ItalicMT-17.bdf",
                    text_position=((45, 120)  # Example location
                                   ),
                    text_color=(0xFFFFFF # quote text color -> pink
                                ), # author text color
                    text_wrap=(30 # characters to wrap for text
                               ), # no wrap for author
                    text_maxlen=(100), # max text size for word, def, type, and date (10 for date)
                    caption_text=CAPTION,
                    caption_font=cwd+"/fonts/Arial-ItalicMT-17.bdf",
                    caption_position=(45, 40),
                    caption_color=0x808080
                   # curlcap_text=CAPTION,
                   # urlcap_font=cwd+"/fonts/Arial-ItalicMT-17.bdf",
                   # urlcap=(50, 220),
                   # urlcap=0x808080
                    )
# speed up projects with lots of text by preloading the font!
pyportal.preload_font()

while True:
    try:
        value = pyportal.fetch()
        print("Response is", value)
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)
    time.sleep(120)