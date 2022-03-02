# SPDX-FileCopyrightText: 2021 Erin St Blaine for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Clock & sky colorbox for Adafruit MagTag: displays current time while
NeoPixels provide theme lighting for the time of day. Requires WiFi
internet access -- configure credentials in secrets.py. An Adafruit IO
user name and API key are also needed there, plus timezone and
geographic coords.
"""

# pylint: disable=import-error
import time
import json
import board
import neopixel
from adafruit_magtag.magtag import MagTag
import adafruit_fancyled.adafruit_fancyled as fancy

# UTC offset queries require some info from the secrets table...
try:
    from secrets import secrets
except ImportError:
    print('Please set up secrets.py with network credentials.')


# CONFIGURABLE SETTINGS ----------------------------------------------------

USE_AMPM_TIME = True # Set to False to use 24-hour time (e.g. 18:00)
NUM_LEDS = 22        # Length of NeoPixel strip
BRIGHTNESS = 0.9     # NeoPixel brightness: 0.0 (off) to 1.0 (max)
SPIN_TIME = 10 * 60  # Seconds for NeoPixels to complete one revolution
# Default spin time is 10 minutes. It should be very slow...imperceptible
# really...as there will be pauses when network activity is occurring.

DAY_PALETTE = [               # Daylight colors
    fancy.CRGB(0.5, 0, 1.0),  # Purplish blue
    fancy.CRGB(0, 0.5, 1.0),  # Blue
    fancy.CRGB(0, 0.5, 1.0),  # Blue
    0x1B90FF,                 # Cyan
    fancy.CRGB(0, 0.8, 0.2),  # Green
    fancy.CRGB(0, 0.8, 0.2),  # Green
    0xFFEA0A,                 # Yellow
    0xFFEA0A,                 # Yellow
    0xFFEA0A,                 # Yellow
    0xFFEA0A,                 # Yellow
    0x30FEF2,                 # Sky blue
    0x0C69FC,                 # Sky blue
    0x1A82FF,
    fancy.CRGB(0, 0.8, 0.8),  # Green
    fancy.CRGB(0, 0.8, 0.2),  # Green
    fancy.CRGB(0, 0.8, 0.2),  # Green
    fancy.CRGB(0.5, 0, 1.0),] # Purplish blue

NIGHT_PALETTE = [ # Starlight colors
    fancy.CRGB(0, 0, 1.0),
    fancy.CRGB(0, 0.2, 1.0),
    fancy.CRGB(0, 0.1, 1.0),
    fancy.CRGB(0, 0, 1.0),
    0x000000,
    0x000000,
    0x000000,
    fancy.CRGB(1.0, 1.0, 0.8),
    0x000000,
    fancy.CRGB(0.3, 0.3, 0.3),
    fancy.CRGB(0.2, 0.2, 0.2),
    fancy.CRGB(0.3, 0.3, 0.3),
    0x000000,
    0x000000,
    0x000000,
    0x000000]

HORIZON_PALETTE = [            # Dawn & dusk colors
    fancy.CHSV(0.8),           # Purple
    fancy.CHSV(1.0),           # Red
    fancy.CHSV(1.0),           # Red
    fancy.CRGB(1.0, 0.5, 0.0), # Orange
    fancy.CRGB(1.0, 0.5, 0.0), # Orange
    fancy.CRGB(1.0, 0.8, 0.0), # Yellow
    0xFFFFFF,                  # White
    fancy.CRGB(1.0, 0.8, 0.0), # Yellow
    fancy.CRGB(1.0, 0.5, 0.0)] # Orange


# SOME UTILITY FUNCTIONS ---------------------------------------------------

def hh_mm(time_struct, twelve_hour=True):
    """ Given a time.struct_time, return a string as H:MM or HH:MM, either
        12- or 24-hour style depending on twelve_hour flag.
    """
    postfix = ""
    if twelve_hour:
        if time_struct.tm_hour > 12:
            hour_string = str(time_struct.tm_hour - 12) # 13-23 -> 1-11 (pm)
            postfix = "pm"
        elif time_struct.tm_hour > 0:
            hour_string = str(time_struct.tm_hour) # 1-12
            postfix = "am"
        else:
            hour_string = '12' # 0 -> 12 (am)
            postfix = "pm"
    else:
        hour_string = '{hh:02d}'.format(hh=time_struct.tm_hour)
    return hour_string + ':{mm:02d}'.format(mm=time_struct.tm_min) + postfix

def parse_time(timestring):
    """ Given a string of the format YYYY-MM-DDTHH:MM:SS.SS-HH:MM (and
        optionally a DST flag), convert to and return a numeric value for
        elapsed seconds since midnight (date, UTC offset and/or decimal
        fractions of second are ignored).
    """
    date_time = timestring.split('T') # Separate into date and time
    hour_minute_second = date_time[1].split('+')[0].split('-')[0].split(':')
    return (int(hour_minute_second[0]) * 3600 +
            int(hour_minute_second[1]) * 60 +
            int(hour_minute_second[2].split('.')[0]))

def blend(palette1, palette2, weight2, offset):
    """ Given two FancyLED color palettes and a weighting (0.0 to 1.0) of
        the second palette, plus a positional offset (where 0.0 is the start
        of each palette), fill the NeoPixel strip with an interpolated blend
        of the two palettes.
    """
    weight2 = min(1.0, max(0.0, weight2)) # Constrain input to 0.0-1.0
    weight1 = 1.0 - weight2               # palette1 weight (inverse of #2)
    for i in range(NUM_LEDS):
        position = offset + i / NUM_LEDS
        color1 = fancy.palette_lookup(palette1, position)
        color2 = fancy.palette_lookup(palette2, position)
        # Blend the two colors based on weight1&2, run through gamma func:
        color = fancy.CRGB(
            color1[0] * weight1 + color2[0] * weight2,
            color1[1] * weight1 + color2[1] * weight2,
            color1[2] * weight1 + color2[2] * weight2)
        color = fancy.gamma_adjust(color, brightness=BRIGHTNESS)
        PIXELS[i] = color.pack()
    PIXELS.show()


# ONE-TIME INITIALIZATION --------------------------------------------------

MAGTAG = MagTag()

MAGTAG.graphics.set_background("/background.bmp")

MAGTAG.add_text(
    text_font="Lato-Regular-74.pcf",
    text_position=(MAGTAG.graphics.display.width // 2, 30),
    text_anchor_point=(0.5, 0),
    is_data=False,
)

# Declare NeoPixel object on pin D10 with NUM_LEDS pixels, no auto-write.
# Set brightness to max as we'll be using FancyLED's brightness control.
PIXELS = neopixel.NeoPixel(board.D10, NUM_LEDS, brightness=0.1,
                           auto_write=False)
PIXELS.show() # Off at start

LAST_SYNC = time.monotonic() - 5000 # Force initial clock sync
LAST_MINUTE = -1                    # Force initial display update
LAST_DAY = -1                       # Force initial sun query
SUNRISE = 6 * 60 * 60               # Sunrise @ 6am by default
SUNSET = 18 * 60 * 60               # Sunset @ 6pm by default
UTC_OFFSET = '+00:00'               # Gets updated along with time
SUN_FLAG = False                    # Triggered at midnight

# MAIN LOOP ----------------------------------------------------------------

while True:
    if (time.monotonic() - LAST_SYNC) > 3600: # Sync time once an hour
        MAGTAG.network.get_local_time()
        LAST_SYNC = time.monotonic()
        # Sun API requires a valid UTC offset. Adafruit IO's time API
        # offers this, but get_local_time() above (using AIO) doesn't
        # store it anywhere. I’ll put in a feature request for the
        # PortalBase library, but in the meantime this just makes a
        # second request to the time API asking for that one value.
        # Since time is synced only once per hour, the extra request
        # isn't particularly burdensome.
        try:
            RESPONSE = MAGTAG.network.requests.get(
                'https://io.adafruit.com/api/v2/%s/integrations/time/'
                'strftime?x-aio-key=%s&tz=%s' % (secrets.get('aio_username'),
                                                 secrets.get('aio_key'),
                                                 secrets.get('timezone')) +
                '&fmt=%25z')
            if RESPONSE.status_code == 200:
                # Arrives as sHHMM, convert to sHH:MM
                print(RESPONSE.text)
                UTC_OFFSET = RESPONSE.text[:3] + ':' + RESPONSE.text[-2:]
        except: # pylint: disable=bare-except
            # If query fails, prior value is kept until next query.
            # Only changes 2X a year anyway -- worst case, if these
            # events even align, is rise/set is off by an hour.
            pass

    NOW = time.localtime() # Current time (as time_struct)

    # If minute has changed, refresh display
    if LAST_MINUTE != NOW.tm_min:
        MAGTAG.set_text(hh_mm(NOW, USE_AMPM_TIME), index=0)
        LAST_MINUTE = NOW.tm_min

    # If day has changed (local midnight), set flag for later sun query
    # (it's not done at midnight, see below).
    if LAST_DAY != NOW.tm_mday:
        SUN_FLAG = True
        LAST_DAY = NOW.tm_mday

    # If the sun flag is set, and if the time is 3:05 am or thereabouts,
    # query the sun API for new rise and set times for today. It's done
    # this way (rather than at midnight) to allow for DST time jumps
    # (which occur at 2am) and slight clock drift (corrected hourly),
    # but still before dawn.
    if SUN_FLAG and (NOW.tm_hour * 60 + NOW.tm_min > 185):
        try:
            URL = ('https://api.met.no/weatherapi/sunrise/2.0/.json?'
                   'lat=%s&lon=%s&date=%s-%s-%s&offset=%s' %
                   (secrets.get('latitude'), secrets.get('longitude'),
                    str(NOW.tm_year), '{0:0>2}'.format(NOW.tm_mon),
                    '{0:0>2}'.format(NOW.tm_mday), UTC_OFFSET))
            print('Fetching sun data via', URL)
            FULL_DATA = json.loads(MAGTAG.network.fetch_data(URL))
            SUN_DATA = FULL_DATA['location']['time'][0]
            SUNRISE = parse_time(SUN_DATA['sunrise']['time'])
            SUNSET = parse_time(SUN_DATA['sunset']['time'])
        except: # pylint: disable=bare-except
            # If any part of the sun API query fails (whether network or
            # bad inputs), just repeat the old sun rise/set times and we'll
            # try again tomorrow. These only shift by seconds or minutes
            # daily, and the LEDs are just for mood, not like we're
            # launching a Mars rocket, errors here are not catastrophic.
            # Very worst case is a query error on a DST time change day,
            # in which case rise/set lights will be off by about an hour
            # until next successful query.
            pass
        SUN_FLAG = False # Pass or fail, don't query again until tomorrow

    # Convert NOW into elapsed seconds since midnight
    NOW = time.mktime(NOW) - time.mktime((NOW.tm_year, NOW.tm_mon,
                                          NOW.tm_mday, 0, 0, 0,
                                          NOW.tm_wday, NOW.tm_yday,
                                          NOW.tm_isdst))
    # Compare current time (in seconds since midnight) against sun rise/set
    # times and do color fades within +/- 30 minutes of each.
    if SUNRISE < NOW < SUNSET:                  # Day (ish)
        if NOW - SUNRISE < (30 * 60):           # Between sunrise & daylight
            PALETTE1, PALETTE2 = HORIZON_PALETTE, DAY_PALETTE
            INTERP = (NOW - SUNRISE) / (30 * 60)
        elif SUNSET - NOW < (30 * 60):          # Between daylight & sunset
            PALETTE1, PALETTE2 = HORIZON_PALETTE, DAY_PALETTE
            INTERP = (SUNSET - NOW) / (30 * 60)
        else:                                   # Full daylight
            PALETTE1 = PALETTE2 = DAY_PALETTE   # Day sky
            INTERP = 0.0                        # No fade
    else:                                       # Night (ish)
        if 0 < SUNRISE - NOW < (30 * 60):       # Between night & sunrise
            PALETTE1, PALETTE2 = HORIZON_PALETTE, NIGHT_PALETTE
            INTERP = (SUNRISE - NOW) / (30 * 60)
        elif 0 < NOW - SUNSET < (30 * 60):      # Between sunset & night
            PALETTE1, PALETTE2 = HORIZON_PALETTE, NIGHT_PALETTE
            INTERP = (NOW - SUNSET) / (30 * 60)
        else:                                   # Full night
            PALETTE1 = PALETTE2 = NIGHT_PALETTE # Night sky
            INTERP = 0.0                        # No fade

    # Update NeoPixels based on time of day
    blend(PALETTE1, PALETTE2, INTERP, time.monotonic() / SPIN_TIME)
