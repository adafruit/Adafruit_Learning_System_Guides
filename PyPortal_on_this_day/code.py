import random
import board
import adafruit_pyportal

cwd = ("/"+__file__).rsplit('/', 1)[0] # the current working directory (where this file is)

DAY = ["Day of the year"]
PERSON = ["Person"]
NOTABLE = ["Notable for"]
YEAR = ["year"]
ACCOMPLISH = ["Accomplishment"]
WEB = ["Web Reference"]

DATA = Fake_Requests(cwd+"/jan1_hist_json.py")

# create pyportal object w no data source (we'll feed it text later)
pyportal = PyPortal(url = DATA,
                    json_path = (DAY, PERSON, NOTABLE, YEAR, ACCOMPLISH, WEB),
                    status_neopixel = board.NEOPIXEL,
                    default_bg = None,
                    text_font = cwd+"fonts/Arial-ItalicMT-17.bdf",
                    text_position=((5, 10), (5, 50), (5, 90),(5, 130), (5, 170), (5, 210)),
                    text_color=(0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF),
                    text_maxlen=(50, 50, 50, 50, 50, 50), # cut off characters
                   )

pyportal.set_text("loading ...") # display while user waits
pyportal.preload_font() # speed things up by preloading font
pyportal.set_text("What happened today in history?") # show title

while True:
    if pyportal.touchscreen.touch_point:
        while True:
            response = None
            try:
                response = pyportal.fetch()
                print("Response is", response)
            except RuntimeError as e:
                print("Some error occured, retrying! -", e)