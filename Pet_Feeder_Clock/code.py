import ipaddress
import ssl
import wifi
import socketpool
import adafruit_requests
import secrets
import time
import terminalio
import displayio
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
from adafruit_magtag.magtag import MagTag

TEXT_URL = "http://wifitest.adafruit.com/testwifi/index.html"
JSON_QUOTES_URL = "https://www.adafruit.com/api/quotes.php"
JSON_STARS_URL = "https://api.github.com/repos/adafruit/circuitpython"

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Get our username, key and desired timezone
aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]
#location = secrets.get("timezone", None)
TIME_URL = "https://io.adafruit.com/api/v2/%s/integrations/time/strftime?x-aio-key=%s" % (aio_username, aio_key)
TIME_URL += "&fmt=%25Y-%25m-%25d+%25H%3A%25M%3A%25S.%25L+%25j+%25u+%25z+%25Z"

# in seconds, we can refresh about 100 times on a battery
PET_NAME = "Midi"
TIME_BETWEEN_REFRESHES = 24 * 60 * 60  # once a day delay

magtag = MagTag()

small_font = bitmap_font.load_font("/Lato-Bold-ltd-25.bdf")
time_font = bitmap_font.load_font("/Montserrat-Regular-78.bdf")
label_group = displayio.Group(max_size=3)

fed_label = label.Label(small_font, max_glyphs = 50,  color=0x000000)
fed_label.anchor_point = (0,0)
fed_label.anchored_position = (10, 5)
label_group.append(fed_label)

time_label = label.Label(time_font, text="TIME", max_glyphs = 10, color=0x000000)
time_label.anchor_point = (0,0)
time_label.anchored_position = (10, 50)
label_group.append(time_label)

#add group
magtag.splash.append(label_group)

#magtag.display.refresh()

magtag.get_local_time()
now = time.localtime()
print(now)

print("Connecting to %s"%secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s!"%secrets["ssid"])
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

while(True):

    if magtag.peripherals.button_a_pressed:
        print("button pressed")
        response = requests.get(TIME_URL)
        parts = response.text.split(" ") #['2020-12-09', '15:56:27.988', '344', '3', '-0500', 'EST']

        #format date
        date = parts[0].split("-")
        date_string = date[1] + "/" + date[2] + "/" + date[0][-2:]
        print(date_string)
        fed_label.text = PET_NAME + " was fed " + date_string +  " @"

        #format time
        time_string = parts[1][:5].lstrip("0")
        hour = int(time_string.split(":")[0])
        suffix = "a" if hour < 12 else "p"
        time_string += suffix
        print(time_string)
        time_label.text = time_string

        magtag.display.refresh()

        time.sleep(2)

    time.sleep(0.01)