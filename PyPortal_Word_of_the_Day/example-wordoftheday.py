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
DATA_SOURCE = "https://api.wordnik.com/v4/words.json/wordOfTheDay?api_key="+secrets['wordnik_token']
WORD_LOCATION = ['word']
PART_OF_SPEECH = ['definitions', 0,'partOfSpeech']
DEF_LOCATION = ['definitions', 0,'text']
EXAMPLE_LOCATION = ['examples', 0, 'text']
PUBLISH_DATE = ['publishDate']
CAPTION = 'wordnik.com/word-of-the-day'
PRONUNCIATION = [0,'raw']

DEF_EX_ARR = [DEF_LOCATION, EXAMPLE_LOCATION]

DEF_EX_VAL = 1

cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = PyPortal(url=DATA_SOURCE,
                    json_path=(WORD_LOCATION, PART_OF_SPEECH, DEF_EX_ARR[DEF_EX_VAL]),
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/wordoftheday_background.bmp",
                    text_font=cwd+"/fonts/Arial-ItalicMT-17.bdf",
                    text_position=((50, 30),  # word location
                                   #(187, 25), #date location
                                   (50, 50), # part of speech location
                                   (50, 135), # definition location
                                   ),
                    text_color=(0x8080FF, # quote text color
                                #0xFFFFFF,
                                0xFF00FF,
                                0xFFFFFF
                                ), # author text color
                    text_wrap=(0, # characters to wrap for quote
                             #  0,
                               0,
                               28
                               ), # no wrap for author
                    text_maxlen=(180, 30, 115), # max text size for word, def, type, and date (10 for date)
                    caption_text=CAPTION,
                    caption_font=cwd+"/fonts/Arial-ItalicMT-17.bdf",
                    caption_position=(50, 220),
                    caption_color=0x808080
                    )

pyportal.set_text("\nloading ...") # display while user waits
pyportal.preload_font() # speed things up by preloading font
pyportal.set_text("\nWord of the Day") # show title


while True:
    try:
        value = pyportal.fetch()
        print("Response is", value)
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)
    time.sleep(120)



    """

    if (DEF_EX_VAL == 0):
        DEF_EX_VAL = 1
    elif (DEF_EX_VAL == 1):
        DEF_EX_VAL = 0

    """