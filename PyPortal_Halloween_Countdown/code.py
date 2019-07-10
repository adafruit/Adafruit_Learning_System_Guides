"""
Halloween countdown for PyPortal.

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2019 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

import time
import board
import busio
import binascii
import json
from adafruit_pyportal import PyPortal
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.label import Label
from digitalio import DigitalInOut
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_esp32spi.adafruit_esp32spi_requests as requests
import adafruit_logging as logging

logger = logging.getLogger('main')
logger.setLevel(logging.DEBUG)
try:
    from secrets import secrets
except ImportError:
    logger.critical("""WiFi settings are kept in secrets.py, please add them there!
the secrets dictionary must contain 'ssid' and 'password' at a minimum""")
    raise

def halt_and_catch_fire(message, *args):
    """Log a critical error and stall the system."""
    logger.critical(message, *args)
    while True:
        pass

def connect_esp():
    """Connect the ESP to the network."""
    pyportal.neo_status((0, 0, 100))
    while not esp.is_connected:
        # secrets dictionary must contain 'ssid' and 'password' at a minimum
        logger.debug("Connecting to AP %s", secrets['ssid'])
        if secrets['ssid'] == 'CHANGE ME' or secrets['ssid'] == 'CHANGE ME':
            change_me = "\n"+"*"*45
            change_me += "\nPlease update the 'secrets.py' file on your\n"
            change_me += "CIRCUITPY drive to include your local WiFi\n"
            change_me += "access point SSID name in 'ssid' and SSID\n"
            change_me += "password in 'password'. Then save to reload!\n"
            change_me += "*"*45
            raise OSError(change_me)
        pyportal.neo_status((100, 0, 0)) # red = not connected
        try:
            esp.connect(secrets)
        except RuntimeError as error:
            logger.error("Could not connect to internet: %s", error)
            logger.error("Retrying in 3 seconds...")
            time.sleep(3)

#pylint:disable=redefined-outer-name
def get_bearer_token():
    """Get the bearer authentication token from twitter."""
    logger.debug('Getting bearer token')
    raw_key = secrets['twitter_api_key'] + ':' + secrets['twitter_secret_key']
    encoded_key = binascii.b2a_base64(bytes(raw_key, 'utf8'))
    string_key = bytes.decode(encoded_key).strip()
    headers= {'Authorization': 'Basic ' + string_key,
              'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'}
    response = requests.post('https://api.twitter.com/oauth2/token',
                             headers=headers,
                             data='grant_type=client_credentials')
    response_dict = json.loads(response.content)
    if response_dict['token_type'] != 'bearer':
        halt_and_catch_fire('Wrong token type from twitter: %s', response_dict['token_type'])
    return response_dict['access_token']
#pylint:enable=redefined-outer-name

#setup esp interface
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_gpio0 = DigitalInOut(board.ESP_GPIO0)
esp32_reset = DigitalInOut(board.ESP_RESET)
esp32_cs = DigitalInOut(board.ESP_CS)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready,
                                       esp32_reset, esp32_gpio0)

# determine the current working directory
# needed so we know where to find files
cwd = ("/"+__file__).rsplit('/', 1)[0]

backgrounds = ['countdown_background.bmp']
background_index = 0
event_background = cwd+"/countdown_event.bmp"

# Initialize the pyportal object and let us know what data to fetch and where
# to display it
pyportal = PyPortal(status_neopixel=board.NEOPIXEL,
                    default_bg=cwd + backgrounds[0],
                    external_spi=spi,
                    esp=esp,
                    caption_text='Days Remaining',
                    caption_font=cwd+'/fonts/Helvetica-Bold-36.bdf',
                    caption_position=(13, 160))

# Create the count label
big_font = bitmap_font.load_font(cwd+"/fonts/Helvetica-Bold-36.bdf")
big_font.load_glyphs(b'0123456789') # pre-load glyphs for fast printing
text_color = 0xFFFFFF
countdown_text = Label(big_font, max_glyphs=3)
countdown_text.x = 120
countdown_text.y = 100
countdown_text.color = text_color
pyportal.splash.append(countdown_text)

refresh_time = None

connect_esp()
bearer_token = get_bearer_token()

headers = {'Authorization': 'Bearer ' + bearer_token}

while True:
    # only query the online time once per hour (and on first run)
    if (not refresh_time) or (time.monotonic() - refresh_time) > 3600:
        try:
            logger.debug("Getting tweet from internet!")
            refresh_time = time.monotonic()
        except RuntimeError as e:
            logger.error("Some error occured, retrying! -", e)
            continue

        #fetch the tweetstream from HalloweenCounts
        response = requests.get('https://api.twitter.com/1.1/statuses/user_timeline.json?count=1&screen_name=halloweencounts',
                                headers=headers)
        if response.status_code != 200:
            logger.error('Tweet fetch status: %d', response.status_code)
        else:
            timeline = json.loads(response.content)
            latest_tweet = timeline[0]
            tweet_text = latest_tweet['text']
            days_remaining = int(tweet_text.split(' Days Until')[0].split(' ')[-1])
            logger.debug('Days remaining: %d', days_remaining)
            #if it's halloween, set the bground and stop
            if days_remaining == 0:
                pyportal.set_background(event_background)
                while True:
                    pass
            else:
                background_index = (background_index + 1) % len(backgrounds)
                pyportal.set_background(backgrounds[background_index])
                countdown_text.text = '{:>3}'.format(days_remaining)

    # check every minute
    time.sleep(60)
