"""
Seasonal produce finder for Adafruit MagTag w/CircuitPython 6.1 or later.
Lists in-season fruits and vegetables for a user's location and season.
"Smart cursive" BDF font by Thomas A. Fine, helvB12.bdf from Xorg fonts.
"""

# pylint: disable=import-error, no-name-in-module
import gc
import time
from secrets import secrets
import alarm
import displayio
from rtc import RTC
from adafruit_magtag.magtag import Graphics
from adafruit_magtag.magtag import Network
from adafruit_magtag.magtag import Peripherals
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.label import Label
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
# contained there, value above will be used. If time zone is not there, IP
# geolocation is used (http://worldtimeapi.org/api/timezone for list).
# pylint: disable=bare-except
try:
    LOCATION = secrets['location'] # e.g. 'NY'
except:
    pass # Original LOCATION value above is intact
try:
    TIME_ZONE = secrets['timezone'] # e.g. 'America/New_York'
except:
    TIME_ZONE = None # Use IP geolocation


# SOME UTILITY FUNCTIONS ---------------------------------------------------

def parse_time(timestring, is_dst=-1):
    """ Given a string of the format YYYY-MM-DDTHH:MM:SS.SS-HH:MM (and
        optionally a DST flag), convert to and return an equivalent
        time.struct_time (strptime() isn't available here). Calling function
        can use time.mktime() on result if epoch seconds is needed instead.
        Time string is assumed local time; UTC offset is ignored. If seconds
        value includes a decimal fraction it's ignored.
    """
    date_time = timestring.split('T')        # Separate into date and time
    year_month_day = date_time[0].split('-') # Separate time into Y/M/D
    hour_minute_second = date_time[1].split('+')[0].split('-')[0].split(':')
    return time.struct_time(int(year_month_day[0]),
                            int(year_month_day[1]),
                            int(year_month_day[2]),
                            int(hour_minute_second[0]),
                            int(hour_minute_second[1]),
                            int(hour_minute_second[2].split('.')[0]),
                            -1, -1, is_dst)

def update_time(timezone=None):
    """ Update system date/time from WorldTimeAPI public server;
        no account required. Pass in time zone string
        (http://worldtimeapi.org/api/timezone for list)
        or None to use IP geolocation. Returns current local time as a
        time.struct_time and UTC offset as string. This may throw an
        exception on fetch_data() - it is NOT CAUGHT HERE, should be
        handled in the calling code because different behaviors may be
        needed in different situations (e.g. reschedule for later).
    """
    if timezone: # Use timezone api
        time_url = 'http://worldtimeapi.org/api/timezone/' + timezone
    else: # Use IP geolocation
        time_url = 'http://worldtimeapi.org/api/ip'

    time_data = NETWORK.fetch_data(time_url,
                                   json_path=[['datetime'], ['dst'],
                                              ['utc_offset']])
    time_struct = parse_time(time_data[0], time_data[1])
    RTC().datetime = time_struct
    return time_struct, time_data[2]

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

PERIPHERALS = Peripherals()
PERIPHERALS.neopixel_disable = True
NETWORK = Network(status_neopixel=None)
GRAPHICS = Graphics(auto_refresh=False)
DISPLAY = GRAPHICS.display
DISPLAY.rotation = 0
PRODUCE = Produce(JSON_URL, LOCATION)


# GRAPHICS INITIALIZATION --------------------------------------------------

TIME_FONT = bitmap_font.load_font('/fonts/helvB12.bdf')
LIST_FONT = bitmap_font.load_font('/fonts/cursive-smart.bdf')
LINE_SPACING = 15 # Matches what's in background bitmap

GROUP = displayio.Group(max_size=4)

# Load background image, make it the bottom-most element in GROUP
FILE = open('bitmaps/produce.bmp', 'rb')
BITMAP = displayio.OnDiskBitmap(FILE)
TILEGRID = displayio.TileGrid(
    BITMAP, pixel_shader=displayio.ColorConverter())
GROUP.append(TILEGRID)

# Produce list is inserted at this position into GROUP later

# Add 14-pixel-tall black bar at bottom of display. It's a distinct layer
# (not just background) to appear on top of produce list if it runs long.
PALETTE = displayio.Palette(1)
PALETTE[0] = 0
BITMAP = displayio.Bitmap(1, DISPLAY.width, 1)
TILEGRID = displayio.TileGrid(BITMAP, pixel_shader=PALETTE,
                              width=DISPLAY.width, height=14)
TILEGRID.y = DISPLAY.height - 14
GROUP.append(TILEGRID)

# Center white text label over black bar to show last update time
# (Initially a placeholder, string is not assigned to label until later)
UPDATED = Label(TIME_FONT, max_glyphs=19, color=0xFFFFFF)
UPDATED.anchor_point = (0.5, 1)
UPDATED.anchored_position = (DISPLAY.width // 2, DISPLAY.height - 1)
GROUP.append(UPDATED)

DISPLAY.show(GROUP)

NETWORK.connect() # Sneak this in last, as WiFi uses power


# MAIN LOOP ----------------------------------------------------------------

# Just FYI, the "main loop" doesn't really loop when using deep sleep...
# it runs once and the whole system restarts on wake. It's written this
# way so time.sleep() can be used during testing rather than deep sleep.

# pylint: disable=protected-access
while True:
    try:
        print('Updating time')
        TIME_STRUCT, _ = update_time(TIME_ZONE)
        LAST_UPDATE = time.mktime(TIME_STRUCT)

        print('Updating produce')
        PRODUCE.fetch(NETWORK)
        if DEEP_SLEEP:
            NETWORK._wifi.enabled = False # WiFi off ASAP!

        # Set the "Updated" date and time label
        if DD_MM:
            DATE = '%d/%d' % (TIME_STRUCT.tm_mday, TIME_STRUCT.tm_mon)
        else:
            DATE = '%d/%d' % (TIME_STRUCT.tm_mon, TIME_STRUCT.tm_mday)
        UPDATED.text = ('Updated %s %s' %
                        (DATE, hh_mm(TIME_STRUCT, TWELVE_HOUR)))

        # Look up the matching produce data (returned as list of strings)
        PRODUCE_LIST = PRODUCE.in_season(TIME_STRUCT.tm_mon)
        NUM_ITEMS = len(PRODUCE_LIST)
        print(PRODUCE_LIST)

        # Generate group of produce labels...
        PRODUCE_GROUP = displayio.Group(max_size=NUM_ITEMS)

        # Baseline alignment is complicated and would require math & stuff.
        # This makes assumptions based on font chosen and veggie names.
        INITIAL_Y = 2
        for index, item in enumerate(PRODUCE_LIST):
            label = Label(LIST_FONT, text=item, color=0)
            label.anchor_point = (0, 0)
            label.anchored_position = (3, INITIAL_Y + index * LINE_SPACING)
            PRODUCE_GROUP.append(label)

        # PRODUCE_GROUP is inserted after the background, but before the
        # "Updated" rectangle, so latter appears "on top" if list runs long.
        GROUP.insert(1, PRODUCE_GROUP)

        DISPLAY.refresh()
        time.sleep(5) # Allow refresh to finish before deep sleep

        NOW = time.localtime() # Time, right now, after screen update
        # For next update time, start with 'now' time, but change hour to
        # DAILY_UPDATE_HOUR, minutes and seconds to 0. For updates after the
        # first, this will be in the past, but that's OK, we'll adjust...
        EVENT_TIME = time.struct_time(NOW[0], NOW[1], NOW[2],
                                      DAILY_UPDATE_HOUR, 0, 0,
                                      -1, -1, NOW[8])
        SLEEP_SECONDS = time.mktime(EVENT_TIME) - time.mktime(NOW)
        if SLEEP_SECONDS <= 0:            # Compensate for EVENT_TIME in past
            SLEEP_SECONDS += 24 * 60 * 60 # by pushing 24 hours ahead
    except:
        # If there's an error above, no harm, just try again in ~15 minutes.
        # Usually it's a common network issue or time server hiccup.
        SLEEP_SECONDS = 15 * 60

    if DEEP_SLEEP:
        # This basically powers down the board and code restarts next time
        alarm.exit_and_deep_sleep_until_alarms(
            alarm.time.TimeAlarm(monotonic_time=
                                 time.monotonic() + SLEEP_SECONDS))
    else:
        GROUP.remove(PRODUCE_GROUP) # Regenerated/inserted on next pass
        gc.collect()
        time.sleep(SLEEP_SECONDS)
