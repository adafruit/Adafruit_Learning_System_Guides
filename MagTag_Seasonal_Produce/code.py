"""
Seasonal produce finder for Adafruit MagTag w/CircuitPython 6.1 or later.
Lists in-season fruits and vegetables for a user's location and season.
"Smart cursive" BDF font by Thomas A. Fine, helvB12 from Xorg fonts.
"""

# pylint: disable=import-error, line-too-long
import time
from secrets import secrets
import rtc
from adafruit_display_shapes.rect import Rect
from adafruit_magtag.magtag import MagTag
from produce import Produce


# CONFIGURABLE SETTINGS and ONE-TIME INITIALIZATION ------------------------

TWELVE_HOUR = True # If set, show 12-hour vs 24-hour (e.g. 3:00 vs 15:00)
DD_MM = False      # If set, show DD/MM instead of MM/DD dates
# Location of produce data (file:// or http:// or https://):
JSON_URL = 'https://raw.githubusercontent.com/adafruit/Adafruit_Learning_System_Guides/master/MagTag_Seasonal_Produce/produce.json'

# Location is configured in secrets.py. If location is not contained there,
# default value below will be used.
LOCATION = secrets.get('location', 'NY') # default to 'NY'

PRODUCE = Produce(JSON_URL, LOCATION)
MAGTAG = MagTag(rotation=0) # Portrait (vertical) display


# SOME UTILITY FUNCTIONS ---------------------------------------------------

def hh_mm(time_struct, twelve_hour=True):
    """ Given a time.struct_time, return a string as H:MM or HH:MM, either
        12- or 24-hour style depending on twelve_hour flag.
    """
    if twelve_hour:
        if time_struct.tm_hour > 12:
            hour_string = str(time_struct.tm_hour - 12) # 13-23 -> 1-11 (pm)
        elif time_struct.tm_hour > 0:
            hour_string = str(time_struct.tm_hour) # 1-12
        else:
            hour_string = '12' # 0 -> 12 (am)
    else:
        hour_string = '{hh:02d}'.format(hh=time_struct.tm_hour)
    return hour_string + ':{mm:02d}'.format(mm=time_struct.tm_min)


# GRAPHICS INITIALIZATION --------------------------------------------------

MAGTAG.graphics.set_background('bitmaps/produce.bmp')

# Produce list is inserted at this position
MAGTAG.add_text(
    text_font='/fonts/cursive-smart.pcf',
    text_position=(3, 2),
    line_spacing=1.0,
    text_anchor_point=(0, 0),  # top left
    is_data=False, # we'll set this text manually
)

# Add 14-pixel-tall black bar at bottom of display. It's a distinct layer
# (not just background) to appear on top of produce list if it runs long.
MAGTAG.graphics.splash.append(Rect(0, MAGTAG.graphics.display.height - 14,
                                   MAGTAG.graphics.display.width,
                                   MAGTAG.graphics.display.height, fill=0x0))

# Center white text label over black bar to show last update time
# (Initially a placeholder, string is not assigned to label until later)
MAGTAG.add_text(
    text_font='/fonts/helvB12.pcf',
    text_position=(MAGTAG.graphics.display.width // 2,
                   MAGTAG.graphics.display.height - 1),
    text_color=0xFFFFFF,
    text_anchor_point=(0.5, 1),
    is_data=False, # we'll set this text manually later
)


# MAIN LOOP ----------------------------------------------------------------

# FYI: Not really a "loop" -- deep sleep makes the whole system restart on
# wake, this only needs to run once.

try:
    MAGTAG.network.connect() # Sneak this in last, as WiFi uses power
    print('Updating time')
    MAGTAG.get_local_time()
    NOW = rtc.RTC().datetime
    print(NOW)

    print('Updating produce')
    PRODUCE.fetch(MAGTAG)

    # Set the "Updated" date and time label
    if DD_MM:
        DATE = '%d/%d' % (NOW.tm_mday, NOW.tm_mon)
    else:
        DATE = '%d/%d' % (NOW.tm_mon, NOW.tm_mday)
    MAGTAG.set_text('Updated %s %s' % (DATE, hh_mm(NOW, TWELVE_HOUR)), 1,
                    auto_refresh=False)

    # Look up the matching produce data (returned as list of strings)
    PRODUCE_LIST = PRODUCE.in_season(NOW.tm_mon)
    NUM_ITEMS = len(PRODUCE_LIST)
    print('Produce list: ', PRODUCE_LIST)
    # List one item per line since some may be long
    VEGGIE_LIST = ''
    for item in PRODUCE_LIST:
        VEGGIE_LIST += '\n'.join(MAGTAG.wrap_nicely(item, 15)) + '\n'
    MAGTAG.set_text(VEGGIE_LIST) # Update list on the display

    time.sleep(2) # Allow refresh to finish before deep sleep
    print('Zzzz time')
    MAGTAG.exit_and_deep_sleep(24 * 60 * 60) # 24 hour snooze

except RuntimeError as error:
    # If there's an error above, no harm, just try again in ~15 minutes.
    # Usually it's a common network issue or time server hiccup.
    print('Retrying in 15 min - ', error)
    MAGTAG.exit_and_deep_sleep(15 * 60) # 15 minute snooze
