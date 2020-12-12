"""
Google Sheets to MagTag example: Naughty or Nice?
Gets JSON spreadsheet from Google, displays names from one column or other.
"Smart cursive" font by Thomas A. Fine, helvB12 from Xorg fonts.
"""

# pylint: disable=import-error, line-too-long
import time
import rtc
from adafruit_display_shapes.rect import Rect
from adafruit_magtag.magtag import MagTag


# CONFIGURABLE SETTINGS and ONE-TIME INITIALIZATION ------------------------

JSON_URL = 'https://spreadsheets.google.com/feeds/cells/1Tk943egFNDV7TmXGL_VspYyWKELeJO8gguAmNSgLDbk/1/public/full?alt=json'
NICE = True        # Use 'True' for nice list, 'False' for naughty
TWELVE_HOUR = True # If set, show 12-hour vs 24-hour (e.g. 3:00 vs 15:00)
DD_MM = False      # If set, show DD/MM instead of MM/DD dates

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

MAGTAG.graphics.set_background('bitmaps/nice.bmp' if NICE else
                               'bitmaps/naughty.bmp')

# Add empty name list here in the drawing stack, names are added later
MAGTAG.add_text(
    text_font='/fonts/cursive-smart.pcf',
    text_position=(8, 40),
    line_spacing=1.0,
    text_anchor_point=(0, 0), # Top left
    is_data=False,            # Text will be set manually
)

# Add 14-pixel-tall black bar at bottom of display. It's a distinct layer
# (not just background) to appear on top of name list if it runs long.
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
    text_anchor_point=(0.5, 1), # Center bottom
    is_data=False,              # Text will be set manually
)


# MAIN LOOP ----------------------------------------------------------------

# FYI: Not really a "loop" -- deep sleep makes the whole system restart on
# wake, this only needs to run once.

try:
    MAGTAG.network.connect() # Do this last, as WiFi uses power

    print('Updating time')
    MAGTAG.get_local_time()
    NOW = rtc.RTC().datetime
    print(NOW)

    print('Updating names')
    RESPONSE = MAGTAG.network.fetch(JSON_URL)
    if RESPONSE.status_code == 200:
        JSON_DATA = RESPONSE.json()
        print('OK')

    # Set the "Updated" date and time label
    if DD_MM:
        DATE = '%d/%d' % (NOW.tm_mday, NOW.tm_mon)
    else:
        DATE = '%d/%d' % (NOW.tm_mon, NOW.tm_mday)
    MAGTAG.set_text('Updated %s %s' % (DATE, hh_mm(NOW, TWELVE_HOUR)), 1,
                    auto_refresh=False)

    ENTRIES = JSON_DATA['feed']['entry'] # List of cell data

    # Scan cells in row #1 to find the column number for naughty vs nice.
    # This allows the order of columns in the spreadsheet to be changed,
    # though they still must have a "Naughty" or "Nice" heading at top.
    for entry in ENTRIES:
        cell = entry['gs$cell']
        if int(cell['row']) is 1:     # Only look at top row
            head = cell['$t'].lower() # Case-insensitive compare
            if ((NICE and head == 'nice') or (not NICE and head == 'naughty')):
                NAME_COLUMN = int(cell['col'])

    # Now that we know which column number contains the names we want,
    # a second pass is made through all the cells. Items where row > 1
    # and column is equal to NAME_COLUMN are joined in a string.
    NAME_LIST = '' # Clear name list
    for entry in ENTRIES:
        cell = entry['gs$cell']
        if int(cell['row']) > 1 and int(cell['col']) is NAME_COLUMN:
            NAME_LIST += cell['$t'] + '\n' # Name + newline character

    MAGTAG.set_text(NAME_LIST) # Update list on the display

    time.sleep(2) # Allow refresh to finish before deep sleep
    print('Zzzz time')
    MAGTAG.exit_and_deep_sleep(24 * 60 * 60) # 24 hour deep sleep

except RuntimeError as error:
    # If there's an error above, no harm, just try again in ~15 minutes.
    # Usually it's a common network issue or time server hiccup.
    print('Retrying in 15 min - ', error)
    MAGTAG.exit_and_deep_sleep(15 * 60) # 15 minute deep sleep
