"""
This example will access the open-notify people in space API, the number of
astronauts and their names... and display it on a screen!
if you can find something that spits out JSON data, we can display it
"""
import time
import board
from adafruit_pyportal import PyPortal
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.label import Label

# Set up where we'll be fetching data from
DATA_SOURCE = "http://api.open-notify.org/astros.json"
DATA_LOCATION = [["number"], ["people"]]

# determine the current working directory
# needed so we know where to find files
cwd = ("/"+__file__).rsplit('/', 1)[0]
# Initialize the pyportal object and let us know what data to fetch and where
# to display it
pyportal = PyPortal(url=DATA_SOURCE,
                    json_path=DATA_LOCATION,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/astronauts_background.bmp",
                    text_font=cwd+"/fonts/Helvetica-Bold-100.bdf",
                    text_position=((225, 50), None),
                    text_color=(0xFFFFFF, None))

names_font =  bitmap_font.load_font(cwd+"/fonts/Helvetica-Bold-16.bdf")
# pre-load glyphs for fast printing
names_font.load_glyphs(b'abcdefghjiklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ- ()')
names_position = (10, 135)
names_color = 0xFF00FF

while True:
    try:
        value = pyportal.fetch()
        print("Response is", value)
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)

    stamp = time.monotonic()
    while (time.monotonic() - stamp) < 5 *60:  # wait 5 minutes before getting again
        if pyportal.touchscreen.touch_point:
            names = ""
            for astro in value[1]:
                names += "%s (%s)\n" % (astro['name'], astro['craft'])
            names = names[:-1] # remove final '\n'
            names_textarea = Label(names_font, text=names)
            names_textarea.x = names_position[0]
            names_textarea.y = names_position[1]
            names_textarea.color = names_color
            pyportal.splash.append(names_textarea)
            time.sleep(30)  # wait 30 seconds to read it
            pyportal.splash.pop()
