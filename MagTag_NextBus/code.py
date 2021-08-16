"""
NEXTBUS SCHEDULER for Adafruit MagTag: Shows arrival predictions for
up to four lines/stops. Requires WiFi internet access.

Written by Phil 'PaintYourDragon' Burgess for Adafruit Industries.
MIT license, all text above must be included in any redistribution.
"""

# pylint: disable=import-error
import gc
import time
from secrets import secrets
import displayio
from rtc import RTC
from adafruit_magtag.magtag import Graphics
from adafruit_magtag.magtag import Network
from adafruit_magtag.magtag import Peripherals
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.label import Label
from nextbus import NextBus


# CONFIGURABLE SETTINGS ----------------------------------------------------

# List of bus lines/stops to predict. Use nextbus_routefinder.py
# (desktop Python) to look up lines/stops for your location, copy & paste
# results here. The 4th element on each line can then be edited for
# brevity if desired (screen space is tight!).
STOPS = [
    ('lametro', '79', '11086', 'Downtown'),
    ('lametro', '79', '2549', 'Arcadia'),
    ('lametro', '260', '11086', 'Altadena'),
    ('lametro', '260', '2549', 'Artesia')
]

# How often to query the NextBus server, in seconds.
# Balance accuracy vs. limiting bandwidth & battery power.
QUERY_INTERVAL = 4 * 60

# Maximum number of predictions to display (NextBus allows up to 5, I think,
# but there's only so much screen and we probably don't care that far ahead).
MAX_PREDICTIONS = 3

# Don't display any times below this threshold, in seconds.
# This is to discourage unsafe bus-chasing behavior! 5 minute default.
MINIMUM_TIME = 5 * 60

# How often to sync clock with time server, in seconds. Clock is only used
# for 'Last checked' display, this does NOT affect predictions, so it's
# not a big problem if this drifts a bit due to infrequent synchronizations.
# 6 hour default.
CLOCK_SYNC_INTERVAL = 6 * 60 * 60
# Load time zone string from secrets.py, else IP geolocation is used
# (http://worldtimeapi.org/api/timezone for list). Again, this is only
# used for the 'Last checked' display, not predictions, so it's not
# especially disruptive if missing.
# pylint: disable=bare-except
try:
    TIME_ZONE = secrets['timezone'] # e.g. 'America/New_York'
except:
    TIME_ZONE = None # Use IP geolocation


# SOME UTILITY FUNCTIONS ---------------------------------------------------

def fillrect(xpos, ypos, width, height, color):
    """ Generate a solid rectangle that's (usually) more RAM-efficient
        than allocating a full bitmap of the requested size.
        Returns a TileGrid that can be appended to a Group.
    """
    palette = displayio.Palette(1)
    palette[0] = color
    # Allocate a bitmap, rectangle's width by 1 pixel tall
    bitmap = displayio.Bitmap(width, 1, 1)
    # Allocate and return a TileGrid, 1 cell wide by rectangle's height
    # cells tall. Each cell value is 0 by default, which points to our
    # full-width rectangle.
    # A more thoughtful implementation would optimize for wide vs tall
    # vs full-rect bitmaps, whichever is most RAM-efficient for the
    # situation, which would require some behind-the-scenes detailed
    # knowledge of Bitmap and TileGrid memory requirements. But for now...
    return displayio.TileGrid(bitmap, pixel_shader=palette, x=xpos, y=ypos,
                              width=1, height=height)

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
        12- or 24-hour style depending on twelve_hour flag. This is ONLY
        for 'clock time,' NOT for countdown time.
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
NETWORK = Network(status_neopixel=None)
GRAPHICS = Graphics(auto_refresh=False)
DISPLAY = GRAPHICS.display

FONT_SMALL = bitmap_font.load_font('/fonts/Impact-16.pcf')
FONT_MEDIUM = bitmap_font.load_font('/fonts/Impact-24.pcf')
FONT_LARGE = bitmap_font.load_font('/fonts/Impact-30.pcf')

# displayio group holds all the labels for the stops and predictions...
GROUP = displayio.Group()
GROUP.append(fillrect(0, 0, DISPLAY.width, DISPLAY.height, 0xFFFFFF))
# Clear the screen ASAP before populating rest of group (erase any old
# prediction data)...
DISPLAY.show(GROUP)
DISPLAY.refresh()
time.sleep(5) # Don't allow another refresh() too soon

# Populate list of NextBus objects from STOPS[] and generate initial text
# labels (these get positioned in a second pass later)...
STOP_LIST = []
MAX_SIZE = (0, 0) # Pixel dimensions of largest route number
for stop in STOPS:
    STOP_LIST.append(NextBus(NETWORK, stop[0], stop[1], stop[2], None,
                             MAX_PREDICTIONS, MINIMUM_TIME))
    TEXT = Label(FONT_LARGE, text=stop[1], color=0)
    # Keep track of the largest route label for positioning things later
    MAX_SIZE = (max(TEXT.width, MAX_SIZE[0]), max(TEXT.height, MAX_SIZE[1]))
    TEXT.anchor_point = (1.0, 1.0) # Bottom-right align route
    GROUP.append(TEXT)
    # Because text anchoring works from bounding rectangles rather than
    # the font baseline, we use a kludge here of upper-casing the route
    # description to eliminate descenders that would throw off alignment.
    TEXT = Label(FONT_SMALL, text=stop[3].upper(), color=0)
    TEXT.anchor_point = (0.0, 1.0) # Bottom-left align description
    GROUP.append(TEXT)
    INITIAL = 'No predictions'
    TEXT = Label(FONT_MEDIUM, text=INITIAL, color=0)
    TEXT.anchor_point = (1.0, 1.0) # Bottom-right align predictions
    GROUP.append(TEXT)

# "Last checked" time at bottom of screen
TEXT = Label(FONT_SMALL, text='Last checked 00:00', color=0)
TEXT.anchor_point = (0.5, 1.0) # Bottom-center align last-checked time
TEXT.anchored_position = (DISPLAY.width // 2, DISPLAY.height - 1)
GROUP.append(TEXT)

# Second pass through STOPS to position the corresponding text elements...
SPACING = min(MAX_SIZE[1] + 4,
              (DISPLAY.height - TEXT.height - 4 - MAX_SIZE[1]) / 3)
# TEXT.width/height doesn't seem to be working correctly with bitmap fonts
# right now, so for now this does a brute-force override thing. Once that's
# resolved, these two lines can be removed:
MAX_SIZE = (48, 24)
SPACING = 28
for stop_index, stop in enumerate(STOPS):
    baseline = MAX_SIZE[1] + SPACING * stop_index
    GROUP[1 + stop_index * 3].anchored_position = (MAX_SIZE[0], baseline)
    GROUP[2 + stop_index * 3].anchored_position = (MAX_SIZE[0] + 4, baseline)
    # Third element (predictions) is NOT positioned here...see main loop

DISPLAY.show(GROUP)

NETWORK.connect()

# Force initial server queries for time and predictions
LAST_SYNC_TIME = -CLOCK_SYNC_INTERVAL
LAST_QUERY_TIME = -QUERY_INTERVAL


# MAIN LOOP ----------------------------------------------------------------

while True:

    # Periodically sync clock with time server
    if time.monotonic() - LAST_SYNC_TIME >= CLOCK_SYNC_INTERVAL:
        try:
            update_time(TIME_ZONE)
            LAST_SYNC_TIME = time.monotonic()
        except:
            # Time sync error isn't fatal, retry in 30 mins
            LAST_SYNC_TIME += 30 * 60

    # Periodically poll all the stops, rather than staggering the queries
    # like the Raspberry Pi version does, since the screen is updated much
    # less frequently.
    if time.monotonic() - LAST_QUERY_TIME >= QUERY_INTERVAL:
        LAST_QUERY_TIME = time.monotonic()
        for stop in STOP_LIST:
            stop.fetch()
        TEXT.text = 'Last checked ' + hh_mm(time.localtime())

    # Update displayed predictions on every pass though...
    for stop_index, stop in enumerate(STOP_LIST):
        times = stop.predict()
        group_index = 3 + stop_index * 3 # GROUP element for prediction text
        baseline = MAX_SIZE[1] + SPACING * stop_index
        if times:
            label = ''
            for time_index, time_seconds in enumerate(times):
                if time_index:
                    label += ', '
                time_minutes = int(time_seconds // 60)
                if time_minutes > 60:
                    # 'HHhMM' format is used rather than 'HH:MM' because
                    # latter might be confused with 'clock time' rather
                    # than countdown.
                    label += '{hh}h{mm:02d}'.format(hh=time_minutes // 60,
                                                    mm=time_minutes % 60)
                else:
                    label += str(time_minutes)
            GROUP[group_index].text = label
        else:
            GROUP[group_index].text = 'No predictions'

        # Because text anchoring currently uses bounding rect (not baseline),
        # the prediction text is scooted down by 2 pixels to compensate for
        # any commas (if present). Not ideal, assumes certain things about
        # font used here. Text without commas is NOT scooted down, to
        # maintain baseline across entire row.
        offset = 2 if ',' in GROUP[group_index].text else 0
        GROUP[group_index].anchored_position = (DISPLAY.width - 1,
                                                baseline + offset)

    DISPLAY.refresh()
    gc.collect()
    time.sleep(60) # Update predictions about once a minute
