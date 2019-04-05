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
CAPTION = 'Word of the Day'
WORD_LOCATION = ['word']
PART_OF_SPEECH = ['definitions', 0,'partOfSpeech']
DEF_LOCATION = ['definitions', 0,'text']
PUBLISH_DATE = ['publishDate']

cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = PyPortal(url=DATA_SOURCE,
                    json_path=(WORD_LOCATION),  #PART_OF_SPEECH, PUBLISH_DATE
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/wordoftheday_background.bmp",
                    text_font=cwd+"/fonts/Arial-ItalicMT-50.bdf",
                    text_position=((40, 100)  # word location
                                   #(50, 50), # part of speech location
                                   #(50, 90), # #date location
                                   ),
                    text_color=(0xFF00FF # quote text color -> pink
                                #0xFFFFFF,
                                #0xFF00FF,
                                #0xFFFFFF
                                ), # author text color
                    text_wrap=(0 # characters to wrap for text
                             #  0,
                             #  0,
                              # 28
                               ), # no wrap for author
                    text_maxlen=(20), # max text size for word, def, type, and date (10 for date)
                    caption_text=CAPTION,
                    caption_font=cwd+"/fonts/Arial-ItalicMT-17.bdf",
                    caption_position=(100, 40),
                    caption_color=0x808080
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