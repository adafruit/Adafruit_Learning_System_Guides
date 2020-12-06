"""
Seasonal produce finder for Adafruit MagTag w/CircuitPython 6.1 or later.
Lists in-season fruits and vegetables for a user's location and season.
"Smart cursive" BDF font by Thomas A. Fine, helvB12.bdf from Xorg fonts.
"""

# pylint: disable=import-error, no-name-in-module
import time
from secrets import secrets
import rtc
from adafruit_display_shapes.rect import Rect
from adafruit_magtag.magtag import MagTag
from produce import Produce


# CONFIGURABLE SETTINGS ----------------------------------------------------

LOCATION = 'CA'       # 2-letter postal U.S. state code
TWELVE_HOUR = True    # If set, show 12-hour vs 24-hour (e.g. 3:00 vs 15:00)
DD_MM = False         # If set, show DD/MM instead of MM/DD dates
DAILY_UPDATE_HOUR = 0 # Update around midnight
DEEP_SLEEP = True     # True for max battery run time, False for testing
# Location of produce data (file:// or http:// or https://):
JSON_URL = 'https://raw.githubusercontent.com/adafruit/Adafruit_Learning_System_Guides/master/MagTag_Seasonal_Produce/produce.json'

# Location and time zone can be configured in secrets.py. If location is not
# contained there, value above will be used.
LOCATION = secrets.get('location', "NY") # default to 'NY'

magtag = MagTag(rotation=0)  # portrait!
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


# ONE-TIME INITIALIZATION --------------------------------------------------

PRODUCE = Produce(JSON_URL, LOCATION)

# GRAPHICS INITIALIZATION --------------------------------------------------
# Load background image, make it the bottom-most element
magtag.graphics.set_background("bitmaps/produce.bmp")

# Produce list is inserted at this position
magtag.add_text(
    text_font="/fonts/cursive-smart.bdf",
    text_position=(3, 2),
    line_spacing=1.0,
    text_anchor_point=(0, 0),  # top left
    is_data=False, # we'll set this text manually
)
#magtag.set_text("testing", auto_refresh=False)  # don't refresh

# Add 14-pixel-tall black bar at bottom of display. It's a distinct layer
# (not just background) to appear on top of produce list if it runs long.
rect = Rect(0, magtag.graphics.display.height - 14,
            magtag.graphics.display.width, magtag.graphics.display.height,
            fill=0x0)
magtag.graphics.splash.append(rect)

# Center white text label over black bar to show last update time
# (Initially a placeholder, string is not assigned to label until later)
magtag.add_text(
    text_font="/fonts/helvB12.bdf",
    text_position=(magtag.graphics.display.width // 2, magtag.graphics.display.height - 1),
    text_maxlen=19,
    text_color=0xFFFFFF,
    text_anchor_point=(0.5, 1),
    is_data=False, # we'll set this text manually
)
#magtag.set_text("date", 1, auto_refresh=False)

# MAIN LOOP ----------------------------------------------------------------

# Just FYI, the "main loop" doesn't really loop when using deep sleep...
# it runs once and the whole system restarts on wake. It's written this
# way so time.sleep() can be used during testing rather than deep sleep.

try:
    magtag.network.connect() # Sneak this in last, as WiFi uses power=
    print('Updating time')
    magtag.get_local_time()
    now = rtc.RTC().datetime
    print(now)

    print('Updating produce')
    PRODUCE.fetch(magtag)

    # Set the "Updated" date and time label
    if DD_MM:
        DATE = '%d/%d' % (now.tm_mday, now.tm_mon)
    else:
        DATE = '%d/%d' % (now.tm_mon, now.tm_mday)
    magtag.set_text('Updated %s %s' % (DATE, hh_mm(now, TWELVE_HOUR)), 1, auto_refresh=False)

    # Look up the matching produce data (returned as list of strings)
    PRODUCE_LIST = PRODUCE.in_season(now.tm_mon)
    NUM_ITEMS = len(PRODUCE_LIST)
    print("Produce list: ", PRODUCE_LIST)
    # Make the list nicely wrapped since some words may be long
    veggie_list = ""
    for item in PRODUCE_LIST:
        print(item)
        veggie_list += "\n".join(magtag.wrap_nicely(item, 15)) + "\n"
    magtag.set_text(veggie_list)  # this finally updates the display!

    time.sleep(2) # Allow refresh to finish before deep sleep
    print("Zzzz time")
    magtag.exit_and_deep_sleep(24 * 60 * 60)  # one day snooze

except RuntimeError as e:
    # If there's an error above, no harm, just try again in ~15 minutes.
    # Usually it's a common network issue or time server hiccup.
    print("Retrying - ", e)
    magtag.exit_and_deep_sleep(15 * 60) # 15 minute snooze
