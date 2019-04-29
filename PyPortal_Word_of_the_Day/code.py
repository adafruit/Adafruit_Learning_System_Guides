"""
This example uses the Wordnik API to display Wordnik's Word of the Day.
Each day a new word, its part of speech, and definition
will appear automatically on the display. Tap the screen to start
as well as to switch between the word's definition and an example sentence.
"""

import board
from adafruit_pyportal import PyPortal

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi settings are kept in settings.py, please add them there!")
    raise

# Set up where we'll be fetching data from
DATA_SOURCE = "https://api.wordnik.com/v4/words.json/wordOfTheDay?api_key="+secrets['wordnik_token']
PART_OF_SPEECH = ['definitions', 0, 'partOfSpeech']
DEF_LOCATION = ['definitions', 0, 'text']
EXAMPLE_LOCATION = ['examples', 0, 'text']
CAPTION = 'wordnik.com/word-of-the-day'
DEFINITION_EXAMPLE_ARR = [DEF_LOCATION, EXAMPLE_LOCATION]
#defintion and example array variable initialized at 0
definition_example = 0

# determine the current working directory
# needed so we know where to find files
cwd = ("/"+__file__).rsplit('/', 1)[0]

# Initialize the pyportal object and let us know what data to fetch and where
# to display it
pyportal = PyPortal(url=DATA_SOURCE,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/wordoftheday_background.bmp",
                    text_font=cwd+"/fonts/Arial-ItalicMT-17.bdf",
                    text_position=((50, 30),  # word location
                                   (50, 50), # part of speech location
                                   (50, 135)), # definition location
                    text_color=(0x8080FF,
                                0xFF00FF,
                                0xFFFFFF),
                    text_wrap=(0, # characters to wrap for text
                               0,
                               28),
                    text_maxlen=(180, 30, 115), # max text size for word, part of speech and def
                    caption_text=CAPTION,
                    caption_font=cwd+"/fonts/Arial-ItalicMT-17.bdf",
                    caption_position=(50, 220),
                    caption_color=0x808080)

print("loading...") # print to repl while waiting for font to load
pyportal.preload_font() # speed things up by preloading font
pyportal.set_text("\nWord of the Day") # show title

while True:
    if pyportal.touchscreen.touch_point:
        try:
            #set the JSON path here to be able to change between definition and example
            # pylint: disable=protected-access
            pyportal._json_path=(['word'],
                                 PART_OF_SPEECH,
                                 DEFINITION_EXAMPLE_ARR[definition_example])
            value = pyportal.fetch()
            print("Response is", value)
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
        #Change between definition and example
        if definition_example == 0:
            definition_example = 1
        elif definition_example == 1:
            definition_example = 0
