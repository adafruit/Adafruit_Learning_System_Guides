import time
from random import randint
import board
from adafruit_pyportal import PyPortal

# There's a few different places we look for data in the photo of the day
IMAGE_LOCATION = ["primaryImage"]
TITLE_LOCATION = ["title"]

# the current working directory (where this file is)
cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = PyPortal(json_path=(IMAGE_LOCATION, TITLE_LOCATION),
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/pocket_museum_background.bmp",
                    text_font=cwd+"/fonts/Arial-12.bdf",
                    text_position=((320, 240), (5, 220)), # need better way of hiding link text
                    text_color=(0xFFFFFF, 0xFFFFFF),
                    text_maxlen=(1, 50), # need better way of hiding link text
                    image_resize=(320, 240),
                    image_position=(0, 0),
                    debug = True)

print("loading...") # print to repl while waiting for font to load
pyportal.preload_font() # speed things up by preloading font

while True:

    print("Searching for new work!")
    #random work is selected
    RANDOM_ART = str(randint(1, 470000))

    # error handling
    try:
        try:
            # set image json path to change pictures when screen touched
            # pylint: disable=protected-access
            pyportal._url=\
            ("https://collectionapi.metmuseum.org/public/collection/v1/objects/"+RANDOM_ART)
            pyportal._image_json_path = (IMAGE_LOCATION)
            value = pyportal.fetch()
            # print("The image is here: ", value[0])
            # if primary image does not exist, try another work
            if value[0] == '':
                print("No image found")
                continue
        # if Key error (conent-length) occurs, try another work
        except KeyError:
            print('Key Error')
            continue
        print("Response is", value)
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)
        continue

    stamp = time.monotonic()
    # wait 5 minutes before getting again
    while (time.monotonic() - stamp) < (5*60):
        # or, if they touch the screen, fetch immediately!
        if pyportal.touchscreen.touch_point:
            break
