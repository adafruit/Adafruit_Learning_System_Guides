"""
PyPortal UV Index display

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2019 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

import time
import json
import board
import displayio
from adafruit_pyportal import PyPortal
from adafruit_display_shapes.rect import Rect
from adafruit_display_text.Label import Label
from adafruit_bitmap_font import bitmap_font

try:
    from secrets import secrets
except ImportError:
    print("""WiFi settings are kept in secrets.py, please add them there!
the secrets dictionary must contain 'ssid' and 'password' at a minimum""")
    raise

MAX_BAR_HEIGHT = 160
MARGIN = 10
SPACE_BETWEEN_BARS = 1

COLORS = [0x00FF00, 0x83C602, 0xa2CF02,
          0xF7DE03, 0xF6B502, 0xF78802,
          0xF65201, 0xEA2709,
          0xDA0115, 0xFC019E, 0xB548FF,
          0x988FFE, 0x7EA7FE, 0x66BFFD, 0x4BD9FF]

cwd = ("/"+__file__).rsplit('/', 1)[0]

CAPTION_FONT_FILE = cwd+'/fonts/Helvetica-Bold-16.bdf'
TEXT_FONT_FILE = cwd+'/fonts/Helvetica-Bold-16.bdf'
HOUR_FONT_FILE = cwd+'/fonts/Arial-Bold-12.bdf'

def halt_and_catch_fire(message, *args):
    """Log a critical error and stall the system."""
    print(message % args)
    while True:
        pass

#pylint:disable=line-too-long
url = 'https://enviro.epa.gov/enviro/efservice/getEnvirofactsUVHOURLY/ZIP/{0}/JSON'.format(secrets['zip'])
#pylint:enable=line-too-long

def extract_hour(date_time):
    split_date_time = date_time.split()
    hour = split_date_time[1]
    suffix = split_date_time[2]
    if hour[0] == '0':
        hour = hour[1]
    return '\n'.join([hour, suffix])

def extract_date(date_time):
    return ' '.join(date_time.split('/')[0:2])

# Initialize the pyportal object and let us know what data to fetch and where
# to display it
pyportal = PyPortal(url=url,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=0xFFFFFF,
                    text_font=TEXT_FONT_FILE,
                    text_position=(20, 60),
                    text_color=0xFFFFFF,
                    text_wrap=35,
                    caption_font=CAPTION_FONT_FILE)

canvas = displayio.Group(max_size=36)
pyportal.splash.append(canvas)
hour_font = bitmap_font.load_font(HOUR_FONT_FILE)

while True:
    raw_data = json.loads(pyportal.fetch())
    data = [{'hour': extract_hour(d['DATE_TIME']), 'value': int(d['UV_VALUE'])}
            for d in raw_data
            if d['UV_VALUE'] > 0]
    the_day = raw_data[0]['DATE_TIME']
    pyportal.set_caption('UV Index for {0}'.format(extract_date(the_day)),
                         (80, 20),
                         0x000000)
    number_of_readings = len(data)
    whitespace = (number_of_readings - 1) * SPACE_BETWEEN_BARS + 2 * MARGIN
    bar_width = (320 - whitespace) // number_of_readings
    max_reading = max([d['value'] for d in data])

    while len(canvas) > 0:
        canvas.pop()

    for i, reading in enumerate(data):
        bar_height = (MAX_BAR_HEIGHT * reading['value']) // max_reading
        x = int(MARGIN + i * (bar_width + SPACE_BETWEEN_BARS))
        canvas.append(Rect(x, 200 - bar_height,
                           bar_width, bar_height,
                           fill=COLORS[reading['value']]))
        canvas.append(Label(hour_font,
                            x=x+3, y=220,
                            text=reading['hour'],
                            color=0x000000,
                            line_spacing=0.6))
        canvas.append(Label(hour_font,
                            x=x+(bar_width//2)-4, y=208-bar_height,
                            text=str(reading['value']),
                            color=0x000000))

    time.sleep(3600)                  #refresh hourly
