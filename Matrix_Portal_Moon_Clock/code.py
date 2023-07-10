# SPDX-FileCopyrightText: 2020 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
MOON PHASE CLOCK for Adafruit Matrix Portal: displays current time, lunar
phase and time of next moonrise or moonset. Requires WiFi internet access
and Adafruit IO user account (basic account is free, just needs registration).

Written by Phil 'PaintYourDragon' Burgess for Adafruit Industries.
MIT license, all text above must be included in any redistribution.

BDF fonts from the X.Org project. Startup 'splash' images should not be
included in derivative projects, thanks. Tall splash images licensed from
123RF.com, wide splash images used with permission of artist Lew Lashmit
(viergacht@gmail.com). Rawr!
"""

# pylint: disable=import-error
import gc
import time
import math
import board
import busio
import displayio
from rtc import RTC
from adafruit_matrixportal.network import Network
from adafruit_matrixportal.matrix import Matrix
from adafruit_bitmap_font import bitmap_font
import adafruit_display_text.label
import adafruit_lis3dh

try:
    from secrets import secrets
except ImportError:
    print('WiFi secrets are kept in secrets.py, please add them there!')
    raise

# CONFIGURABLE SETTINGS ----------------------------------------------------

TWELVE_HOUR = True # If set, use 12-hour time vs 24-hour (e.g. 3:00 vs 15:00)
COUNTDOWN = False  # If set, show time to (vs time of) next rise/set event
MONTH_DAY = True   # If set, use MM/DD vs DD/MM (e.g. 31/12 vs 12/31)
BITPLANES = 6      # Ideally 6, but can set lower if RAM is tight

# Moon API requres valid User-Agent header. Only maintainer should edit this.
HEADERS = { "User-Agent" : "AdafruitMoonClock/1.1 support@adafruit.com" }

# SOME UTILITY FUNCTIONS AND CLASSES ---------------------------------------

# Notes to Future Self on timekeeping: times are expressed in so many
# formats throughout this code, a variable naming system is used: local
# times (i.e. in clock's present geographic time zone) will have _local
# in their variable name, while UTC times (aka Greenwich or Zulu time)
# will have _utc. Types are also explicitly stated: strings (e.g.
# "2023-07-20T08:37-07:00") will have _string in the variable name,
# struct_time objects will have _struct, and integer "UNIX time" epoch
# seconds will have _seconds. Conversions (offset is signed, e.g. -700):
# Convert UTC to local time: add UTC offset;      local = utc   + offset
# Convert local to UTC time: subtract UTC offset; utc   = local - offset

def update_system_time():
    """ Update system clock date/time from Adafruit IO. Credentials and time
        zone are in secrets.py. See http://worldtimeapi.org/api/timezone for
        list of time zones. If missing, will attempt using IP geolocation.
        Returns present local (not UTC) time as a struct_time and UTC offset
        as string "sHH:MM". This may throw an exception on get_local_time(),
        it is NOT CAUGHT HERE, should be handled in the calling code because
        different behaviors may be needed for some situations (e.g.
        reschedule later).
    """
    local_time_string = NETWORK.get_local_time() # Sets RTC() time, but also
    elements = local_time_string.split(" ")      # returns server response
    utc_offset = int(elements[-2]) # Format shHMM, e.g. -700 = -7 hr, 0 min
    # Pad UTC format shHMM to sHH:MM as needed for moon API 3.0
    utc_offset_string = "{:+03d}:{:02d}".format(utc_offset // 100,     # Hours
                                                abs(utc_offset) % 100) # Mins
    return RTC().datetime, utc_offset_string


def hh_mm(time_struct):
    """ Used for clock display elements, not for delta-time calculations.
        Given a struct_time, return a string as H:MM or HH:MM, either 12-
        or 24-hour style depending on global TWELVE_HOUR setting. This is
        ONLY for 'clock time,' NOT for countdown time, which is handled
        separately in the one spot where it's needed.
    """
    if TWELVE_HOUR:
        if time_struct.tm_hour > 12:
            hour_string = str(time_struct.tm_hour - 12) # 13-23 -> 1-11 (pm)
        elif time_struct.tm_hour > 0:
            hour_string = str(time_struct.tm_hour) # 1-12
        else:
            hour_string = '12' # 0 -> 12 (am)
    else:
        hour_string = '{0:0>2}'.format(time_struct.tm_hour)
    return hour_string + ':' + '{0:0>2}'.format(time_struct.tm_min)


def parse_time_to_utc_seconds(time_local_string):
    """ Given a string of YYYY-MM-DDTHH:MMsHH:MM or YYYY-MM-DDTHH:MM:SSZ
        return equivalent UTC epoch seconds.
    """
    # This could be UTC or local time, don't know yet, so no tag in var name
    date_time = time_local_string.split('T') # Separate into date and time
    date_str = date_time[0].split('-') # Separate date into Y/M/D
    time_str = date_time[1]
    # Moon API always puts 00 seconds for interval, while rise/set times
    # include no seconds value. Thus, only first two values are referenced:
    hour = int(time_str[0:2])        # HH:MM as encoded in string,
    minute = int(time_str[3:5])      # still could be UTC or local...
    if time_str[-1] != 'Z':          # If not "Zulu time" (UTC), is local, so:
        hour -= int(time_str[-6:-3]) # convert local to UTC
        minute -= int(time_str[-2:])
    return time.mktime(time.struct_time((int(date_str[0]),
                                         int(date_str[1]),
                                         int(date_str[2]),
                                         hour,
                                         minute,
                                         0, -1, -1, False)))


# pylint: disable=too-few-public-methods
class MoonData():
    """ Class holding lunar data for a given 24-hour period. App uses two
        of these -- one for the current day, and one for the following day,
        then some interpolations and such can be made. Elements include:
        age               : Moon phase 'age' at start of period, expressed
                            from 0.0 (new moon) through 0.5 (full moon) to
                            1.0 (next new moon).
        start_utc_seconds : Epoch time at start of period, UTC
        end_utc_seconds   : Epoch time at end of period, "
        rise_utc_seconds  : Epoch time of moon rise within this 24-hour period
        set_utc_seconds   : Epoch time of moon set within this 24-hour period
    """
    def __init__(self, datetime_local_struct, days_ahead, utc_offset_string):
        """ Initialize MoonData elements (see above) given a struct_time,
            days to skip ahead (typically 0 or 1), and a UTC offset (as a
            string) and a query to the MET Norway Sunrise API (also provides
            lunar data), documented at:
            https://docs.api.met.no/doc/sunrise/celestial.html
        """
        if days_ahead > 0:
            # Can't change attributes in struct_time, need to create a new
            # one which will roll the date ahead as needed. Convert to local
            # epoch seconds and back for the offset to work. :/
            datetime_local_struct = time.localtime(
                time.mktime(time.struct_time((
                    datetime_local_struct.tm_year,
                    datetime_local_struct.tm_mon,
                    datetime_local_struct.tm_mday + days_ahead,
                    datetime_local_struct.tm_hour,
                    datetime_local_struct.tm_min,
                    datetime_local_struct.tm_sec,
                    -1, -1, -1))))
        # URL does not contain local or UTC time, only date. strftime() is
        # not available in CircuitPython, manual conversion to time string
        # is needed. Response is moon data for a 24-hour period, based on
        # longitude and requested date. Some values within are UTC time,
        # others are local. Anything we parse out of this will be converted
        # to UTC epoch seconds, period.
        url = ('https://api.met.no/weatherapi/sunrise/3.0/moon?lat=' +
               str(LATITUDE) + '&lon=' + str(LONGITUDE) +
               '&date=' + str(datetime_local_struct.tm_year) + '-' +
               '{0:0>2}'.format(datetime_local_struct.tm_mon) + '-' +
               '{0:0>2}'.format(datetime_local_struct.tm_mday) +
               '&offset=' + utc_offset_string)
        print('Fetching moon data via', url)
        # pylint: disable=bare-except
        for _ in range(5): # Retries
            try:
                moon_data = NETWORK.fetch_data(url,
                                               json_path=[],
                                               headers = HEADERS)
                properties = moon_data['properties']
                # 0 = new moon, 90 = Q1, 180 = full moon, 270 = LQ
                self.age = float(properties['moonphase']) / 360
                interval = moon_data['when']['interval']
                self.start_utc_seconds = parse_time_to_utc_seconds(interval[0])
                self.end_utc_seconds = parse_time_to_utc_seconds(interval[1])
                # Thx user sandorcourane for the properties fixes!
                if properties['moonrise']['time'] is not None:
                    self.rise_utc_seconds = parse_time_to_utc_seconds(
                        properties['moonrise']['time'])
                else:
                    self.rise_utc_seconds = None
                if properties['moonset']['time'] is not None:
                    self.set_utc_seconds = parse_time_to_utc_seconds(
                        properties['moonset']['time'])
                else:
                    self.set_utc_seconds = None
                return # Success!
            except:
                # Moon server error (maybe), try again after 15 seconds.
                # (Might be a memory error, that should be handled different)
                time.sleep(15)


# ONE-TIME INITIALIZATION --------------------------------------------------

MATRIX = Matrix(bit_depth=BITPLANES)
DISPLAY = MATRIX.display
ACCEL = adafruit_lis3dh.LIS3DH_I2C(busio.I2C(board.SCL, board.SDA),
                                   address=0x19)
_ = ACCEL.acceleration # Dummy reading to blow out any startup residue
time.sleep(0.1)
DISPLAY.rotation = (int(((math.atan2(-ACCEL.acceleration.y,
                                     -ACCEL.acceleration.x) + math.pi) /
                         (math.pi * 2) + 0.875) * 4) % 4) * 90

LARGE_FONT = bitmap_font.load_font('/fonts/helvB12.bdf')
SMALL_FONT = bitmap_font.load_font('/fonts/helvR10.bdf')
SYMBOL_FONT = bitmap_font.load_font('/fonts/6x10.bdf')
LARGE_FONT.load_glyphs('0123456789:')
SMALL_FONT.load_glyphs('0123456789:/.%')
SYMBOL_FONT.load_glyphs('\u21A5\u21A7')

# Display group is set up once, then we just shuffle items around later.
# Order of creation here determines their stacking order.
GROUP = displayio.Group()

# Element 0 is a stand-in item, later replaced with the moon phase bitmap
# pylint: disable=bare-except
try:
    FILENAME = 'moon/splash-' + str(DISPLAY.rotation) + '.bmp'

    # CircuitPython 6 & 7 compatible
    BITMAP = displayio.OnDiskBitmap(open(FILENAME, 'rb'))
    TILE_GRID = displayio.TileGrid(
        BITMAP,
        pixel_shader=getattr(BITMAP, 'pixel_shader', displayio.ColorConverter())
    )

    # # CircuitPython 7+ compatible
    # BITMAP = displayio.OnDiskBitmap(FILENAME)
    # TILE_GRID = displayio.TileGrid(BITMAP, pixel_shader=BITMAP.pixel_shader)

    GROUP.append(TILE_GRID)
except:
    GROUP.append(adafruit_display_text.label.Label(SMALL_FONT, color=0xFF0000,
                                                   text='AWOO'))
    GROUP[0].x = (DISPLAY.width - GROUP[0].bounding_box[2] + 1) // 2
    GROUP[0].y = DISPLAY.height // 2 - 1

# Elements 1-4 are an outline around the moon percentage -- text labels
# offset by 1 pixel up/down/left/right. Initial position is off the matrix,
# updated on first refresh. Initial text value must be long enough for
# longest anticipated string later.
for i in range(4):
    GROUP.append(adafruit_display_text.label.Label(SMALL_FONT, color=0,
                                                   text='99.9%', y=-99))
# Element 5 is the moon percentage (on top of the outline labels)
GROUP.append(adafruit_display_text.label.Label(SMALL_FONT, color=0xFFFF00,
                                               text='99.9%', y=-99))
# Element 6 is the current time
GROUP.append(adafruit_display_text.label.Label(LARGE_FONT, color=0x808080,
                                               text='12:00', y=-99))
# Element 7 is the current date
GROUP.append(adafruit_display_text.label.Label(SMALL_FONT, color=0x808080,
                                               text='12/31', y=-99))
# Element 8 is a symbol indicating next rise or set
GROUP.append(adafruit_display_text.label.Label(SYMBOL_FONT, color=0x00FF00,
                                               text='x', y=-99))
# Element 9 is the time of (or time to) next rise/set event
GROUP.append(adafruit_display_text.label.Label(SMALL_FONT, color=0x00FF00,
                                               text='12:00', y=-99))
DISPLAY.show(GROUP)

NETWORK = Network(status_neopixel=board.NEOPIXEL, debug=False)
NETWORK.connect()

# LATITUDE, LONGITUDE, TIMEZONE are set up once, constant over app lifetime

# Fetch latitude/longitude from secrets.py. If not present, use
# IP geolocation. This only needs to be done once, at startup!
try:
    LATITUDE = secrets['latitude']
    LONGITUDE = secrets['longitude']
    print('Using stored geolocation: ', LATITUDE, LONGITUDE)
except KeyError:
    LATITUDE, LONGITUDE = (
        NETWORK.fetch_data('http://www.geoplugin.net/json.gp',
                           json_path=[['geoplugin_latitude'],
                                      ['geoplugin_longitude']]))
    print('Using IP geolocation: ', LATITUDE, LONGITUDE)

# Set initial clock time, also fetch initial UTC offset while
# here (NOT stored in secrets.py as it may change with DST).
# pylint: disable=bare-except
try:
    DATETIME_LOCAL_STRUCT, UTC_OFFSET_STRING = update_system_time()
except:
    DATETIME_LOCAL_STRUCT, UTC_OFFSET_STRING = time.localtime(), '+00:00'
LAST_SYNC_LOCAL_SECONDS = time.mktime(DATETIME_LOCAL_STRUCT)

# Poll server for moon data for current 24-hour period and +24 ahead
PERIOD = []
for DAY in range(2): # Today, tomorrow
    PERIOD.append(MoonData(DATETIME_LOCAL_STRUCT, DAY, UTC_OFFSET_STRING))
# PERIOD[0] is a current 24-hour time period we're in. PERIOD[1] is the
# 24 hours following that. Start/end time thresholds vary by longitude.
# Any values within the object are expressed in UTC seconds. Data is
# shifted down and new data fetched as days expire. Thought we might need a
# PERIOD[2] for certain circumstances but it appears not, that's changed
# easily enough if needed.


# MAIN LOOP ----------------------------------------------------------------

while True:
    gc.collect()
    NOW_LOCAL_SECONDS = time.time() # Current local epoch time in seconds

    # Sync with time server every ~3 hours
    if NOW_LOCAL_SECONDS - LAST_SYNC_LOCAL_SECONDS > 3 * 60 * 60:
        try:
            DATETIME_LOCAL_STRUCT, UTC_OFFSET_STRING = update_system_time()
            LAST_SYNC_LOCAL_SECONDS = time.mktime(DATETIME_LOCAL_STRUCT)
            continue # Time may have changed; refresh NOW_LOCAL_SECONDS value
        except:
            # update_system_time() can throw an exception if time server doesn't
            # respond. That's OK, keep running with our current time, and
            # push sync time ahead to retry in 30 minutes (don't overwhelm
            # the server with repeated queries).
            LAST_SYNC_LOCAL_SECONDS += 30 * 60 # 30 minutes -> seconds

    # NOW_LOCAL_SECONDS and DATETIME_LOCAL_STRUCT are local time, while all
    # moon properties are UTC. Convert 'now' to UTC seconds...
    # UTC_OFFSET_STRING is a string, like +HH:MM. Convert to integer seconds:
    hhmm = UTC_OFFSET_STRING.split(':')
    utc_offset_seconds = ((int(hhmm[0]) * 60 + int(hhmm[1])) * 60)
    NOW_UTC_SECONDS = NOW_LOCAL_SECONDS - utc_offset_seconds

    # If PERIOD has expired, move data down and fetch new +24-hour data
    if NOW_UTC_SECONDS >= PERIOD[0].end_utc_seconds:
        PERIOD[0] = PERIOD[1]
        PERIOD[1] = MoonData(time.localtime(), 1, UTC_OFFSET_STRING)

    # Determine weighting of tomorrow's phase vs today's, using current time
    RATIO = ((NOW_UTC_SECONDS - PERIOD[0].start_utc_seconds) /
             (PERIOD[1].start_utc_seconds - PERIOD[0].start_utc_seconds))
    # Determine moon phase 'age'
    # 0.0  = new moon
    # 0.25 = first quarter
    # 0.5  = full moon
    # 0.75 = last quarter
    # 1.0  = new moon
    if PERIOD[0].age < PERIOD[1].age:
        AGE = (PERIOD[0].age +
               (PERIOD[1].age - PERIOD[0].age) * RATIO) % 1.0
    else: # Handle age wraparound (1.0 -> 0.0)
        # If tomorrow's age is less than today's, it indicates a new moon
        # crossover. Add 1 to tomorrow's age when computing age delta.
        AGE = (PERIOD[0].age +
               (PERIOD[1].age + 1 - PERIOD[0].age) * RATIO) % 1.0

    # AGE can be used for direct lookup to moon bitmap (0 to 99) -- these
    # images are pre-rendered for a linear timescale (solar terminator moves
    # nonlinearly across sphere).
    FRAME = int(AGE * 100) % 100 # Bitmap 0 to 99

    # Then use some trig to get percentage lit
    if AGE <= 0.5: # New -> first quarter -> full
        PERCENT = (1 - math.cos(AGE * 2 * math.pi)) * 50
    else:          # Full -> last quarter -> new
        PERCENT = (1 + math.cos((AGE - 0.5) * 2 * math.pi)) * 50

    # Find next rise/set event, complicated by the fact that some 24-hour
    # periods might not have one or the other (but usually do) due to the
    # Moon rising ~50 mins later each day. This uses a brute force approach,
    # working through the time periods to locate rise/set events that
    # A) exist in that 24-hour period (are not None), B) are still in
    # the future, and C) are closer than the last guess. What's left at the
    # end is the next rise or set time, and a flag whether the moon's
    # currently risen or not.
    NEXT_EVENT_UTC_SECONDS = NOW_UTC_SECONDS + 300000 # Way future
    for DAY in PERIOD:
        if (DAY.rise_utc_seconds and
            NOW_UTC_SECONDS < DAY.rise_utc_seconds < NEXT_EVENT_UTC_SECONDS):
            NEXT_EVENT_UTC_SECONDS = DAY.rise_utc_seconds
            RISEN = False  # Current moon state; next event is inverse
        if (DAY.set_utc_seconds and
            NOW_UTC_SECONDS < DAY.set_utc_seconds < NEXT_EVENT_UTC_SECONDS):
            NEXT_EVENT_UTC_SECONDS = DAY.set_utc_seconds
            RISEN = True

    if DISPLAY.rotation in (0, 180): # Horizontal 'landscape' orientation
        CENTER_X = 48      # Text along right
        MOON_Y = 0         # Moon at left
        TIME_Y = 6         # Time at top right
        EVENT_Y = 26       # Rise/set at bottom right
    else:                  # Vertical 'portrait' orientation
        CENTER_X = 16      # Text down center
        if RISEN:
            MOON_Y = 0     # Moon at top
            EVENT_Y = 38   # Rise/set in middle
            TIME_Y = 49    # Time/date at bottom
        else:
            TIME_Y = 6     # Time/date at top
            EVENT_Y = 26   # Rise/set in middle
            MOON_Y = 32    # Moon at bottom

    print()

    # Update moon image (GROUP[0])
    FILENAME = 'moon/moon' + '{0:0>2}'.format(FRAME) + '.bmp'

    # CircuitPython 6 & 7 compatible
    # BITMAP = displayio.OnDiskBitmap(open(FILENAME, 'rb'))
    # TILE_GRID = displayio.TileGrid(
    #     BITMAP,
    #     pixel_shader=getattr(BITMAP, 'pixel_shader',
    #                          displayio.ColorConverter())
    # )

    # CircuitPython 7+ compatible
    BITMAP = displayio.OnDiskBitmap(FILENAME)
    TILE_GRID = displayio.TileGrid(BITMAP, pixel_shader=BITMAP.pixel_shader)

    TILE_GRID.x = 0
    TILE_GRID.y = MOON_Y
    GROUP[0] = TILE_GRID

    # Update percent value (5 labels: GROUP[1-4] for outline, [5] for text)
    if PERCENT >= 99.95:
        STRING = '100%'
    else:
        STRING = '{:.1f}'.format(PERCENT + 0.05) + '%'
    print(NOW_UTC_SECONDS, STRING, 'full')
    # Set element 5 first, use its size and position for setting others
    GROUP[5].text = STRING
    GROUP[5].x = 16 - GROUP[5].bounding_box[2] // 2
    GROUP[5].y = MOON_Y + 16
    for _ in range(1, 5):
        GROUP[_].text = GROUP[5].text
    GROUP[1].x, GROUP[1].y = GROUP[5].x, GROUP[5].y - 1 # Up 1 pixel
    GROUP[2].x, GROUP[2].y = GROUP[5].x - 1, GROUP[5].y # Left
    GROUP[3].x, GROUP[3].y = GROUP[5].x + 1, GROUP[5].y # Right
    GROUP[4].x, GROUP[4].y = GROUP[5].x, GROUP[5].y + 1 # Down

    # Update next-event time (GROUP[8] and [9])
    NEXT_EVENT_LOCAL_STRUCT = time.localtime(NEXT_EVENT_UTC_SECONDS +
                                             utc_offset_seconds) # Need later
    if COUNTDOWN: # Show NEXT_EVENT_UTC_SECONDS as countdown to event
        MINUTES = (NEXT_EVENT_UTC_SECONDS - NOW_UTC_SECONDS) // 60
        STRING = str(MINUTES // 60) + ':' + '{0:0>2}'.format(MINUTES % 60)
    else: # Show NEXT_EVENT_UTC_SECONDS in clock time
        STRING = hh_mm(NEXT_EVENT_LOCAL_STRUCT)
    GROUP[9].text = STRING
    XPOS = CENTER_X - (GROUP[9].bounding_box[2] + 6) // 2
    GROUP[8].x = XPOS
    if RISEN:                    # Next event is SET
        GROUP[8].text = '\u21A7' # Downwards arrow from bar
        GROUP[8].y = EVENT_Y - 2
        print('Sets:', STRING)
    else:                        # Next event is RISE
        GROUP[8].text = '\u21A5' # Upwards arrow from bar
        GROUP[8].y = EVENT_Y - 1
        print('Rises:', STRING)
    GROUP[9].x = XPOS + 6
    GROUP[9].y = EVENT_Y
    # Show event time in green if a.m., amber if p.m.
    GROUP[8].color = GROUP[9].color = (0x00FF00 if
                                       NEXT_EVENT_LOCAL_STRUCT.tm_hour < 12
                                       else 0xC04000)

    # Update time (GROUP[6]) and date (GROUP[7])
    NOW_LOCAL_STRUCT = time.localtime()
    STRING = hh_mm(NOW_LOCAL_STRUCT)
    GROUP[6].text = STRING
    GROUP[6].x = CENTER_X - GROUP[6].bounding_box[2] // 2
    GROUP[6].y = TIME_Y
    if MONTH_DAY:
        STRING = (str(NOW_LOCAL_STRUCT.tm_mon) + '/' +
                  str(NOW_LOCAL_STRUCT.tm_mday))
    else:
        STRING = (str(NOW_LOCAL_STRUCT.tm_mday) + '/' +
                  str(NOW_LOCAL_STRUCT.tm_mon))
    GROUP[7].text = STRING
    GROUP[7].x = CENTER_X - GROUP[7].bounding_box[2] // 2
    GROUP[7].y = TIME_Y + 10

    DISPLAY.refresh() # Force full repaint (splash screen sometimes sticks)
    time.sleep(5)
