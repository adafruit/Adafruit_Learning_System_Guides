import ssl
import board
import neopixel
import adafruit_requests
import socketpool
import wifi
from adafruit_io.adafruit_io import IO_HTTP
from adafruit_pixel_framebuf import PixelFramebuffer
# adafruit_circuitpython_adafruitio usage with native wifi networking

# Neopixel matrix configuration
PIXEL_PIN = board.IO6
PIXEL_WIDTH = 12
PIXEL_HEIGHT = 12

# secrets.py has SSID/password and adafruit.io
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise
AIO_USERNAME = secrets["aio_username"]
AIO_KEY = secrets["aio_key"]

# LED matrix creation
PIXELS = neopixel.NeoPixel(
    PIXEL_PIN, PIXEL_WIDTH * PIXEL_HEIGHT, brightness=0.5, auto_write=False,
)

PIXEL_FRAMEBUF = PixelFramebuffer(
    PIXELS,
    PIXEL_WIDTH,
    PIXEL_HEIGHT,
    alternating=True,
    rotation=1,
    reverse_x=True
    )

# Adafruit.io feeds setup
QUOTE_FEED = "sign-quotes.signtext"
COLOR_FEED = "sign-quotes.signcolor"
CURRENT_TEXT = "Merry Christmas!"
CURRENT_COLOR = 0xFFFFFF

# Helper function to get updated data from Adafruit.io
def update_data():
    global CURRENT_TEXT, CURRENT_COLOR
    print("Updating data from Adafruit IO")
    try:
        quote_feed = IO.get_feed(QUOTE_FEED)
        quotes_data = IO.receive_data(quote_feed["key"])
        CURRENT_TEXT = quotes_data["value"]
        color_feed = IO.get_feed(COLOR_FEED)
        color_data = IO.receive_data(color_feed["key"])
        CURRENT_COLOR = int(color_data["value"][1:], 16)
    # pylint: disable=broad-except
    except Exception as error:
        print(error)


# Connect to WiFi
print("Connecting to %s" % secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s!" % secrets["ssid"])

# Setup Adafruit IO connection
POOL = socketpool.SocketPool(wifi.radio)
REQUESTS = adafruit_requests.Session(POOL, ssl.create_default_context())
# Initialize an Adafruit IO HTTP API object
IO = IO_HTTP(AIO_USERNAME, AIO_KEY, REQUESTS)


while True:
    update_data()
    print("Displaying", CURRENT_TEXT, "in", hex(CURRENT_COLOR))

    for i in range(12 * len(CURRENT_TEXT) + PIXEL_WIDTH):
        PIXEL_FRAMEBUF.fill(0x000000)
        PIXEL_FRAMEBUF.pixel(0, 0, 0x000000)
        PIXEL_FRAMEBUF.text(CURRENT_TEXT, PIXEL_WIDTH - i, 3, CURRENT_COLOR)
        PIXEL_FRAMEBUF.display()
