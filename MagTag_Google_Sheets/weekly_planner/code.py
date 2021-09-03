"""
Google Sheets to MagTag example: Weekly Planner.
Gets JSON spreadsheet from Google, displays task list from today's column.
This example does NOT deep sleep, a USB power connection is recommended.
Fonts from Xorg project.
"""

# pylint: disable=import-error, line-too-long
import time
import rtc
from adafruit_display_shapes.rect import Rect
from adafruit_magtag.magtag import MagTag


# CONFIGURABLE SETTINGS and ONE-TIME INITIALIZATION ------------------------

JSON_URL = 'https://spreadsheets.google.com/feeds/cells/1vk6jE1-6CMV-hjDgBk-PuFLgG64YemyDoREhGrA6uGI/1/public/full?alt=json'
TWELVE_HOUR = True # If set, show 12-hour vs 24-hour (e.g. 3:00 vs 15:00)
DD_MM = False      # If set, show DD/MM instead of MM/DD dates
DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
        'Saturday']

MAGTAG = MagTag(rotation=0) # Portrait (vertical) display
MAGTAG.network.connect()


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

# First text label (index 0) is day of week -- empty for now, is set later
MAGTAG.add_text(
    text_font='/fonts/helvB24.pcf',
    text_position=(MAGTAG.graphics.display.width // 2, 4),
    line_spacing=1.0,
    text_anchor_point=(0.5, 0), # Center top
    is_data=False,              # Text will be set manually
)

# Second (index 1) is task list -- again, empty on start, is set later
MAGTAG.add_text(
    text_font='/fonts/ncenR14.pcf',
    text_position=(3, 36),
    line_spacing=1.0,
    text_anchor_point=(0, 0), # Top left
    is_data=False,            # Text will be set manually
)

# Add 14-pixel-tall black bar at bottom of display. It's a distinct layer
# (not just background) to appear on top of task list if it runs long.
MAGTAG.graphics.splash.append(Rect(0, MAGTAG.graphics.display.height - 14,
                                   MAGTAG.graphics.display.width,
                                   MAGTAG.graphics.display.height, fill=0x0))

# Center white text (index 2) over black bar to show last update time
MAGTAG.add_text(
    text_font='/fonts/helvB12.pcf',
    text_position=(MAGTAG.graphics.display.width // 2,
                   MAGTAG.graphics.display.height - 1),
    text_color=0xFFFFFF,
    text_anchor_point=(0.5, 1), # Center bottom
    is_data=False,              # Text will be set manually
)


# MAIN LOOP ----------------------------------------------------------------

PRIOR_LIST = '' # Initialize these to nonsense values
PRIOR_DAY = -1  # so the list or day change always triggers on first pass

while True:
    try:
        print('Updating time')
        MAGTAG.get_local_time()
        NOW = rtc.RTC().datetime

        print('Updating tasks')
        RESPONSE = MAGTAG.network.fetch(JSON_URL)
        if RESPONSE.status_code == 200:
            JSON_DATA = RESPONSE.json()
            print('OK')

        ENTRIES = JSON_DATA['feed']['entry'] # List of cell data

        # tm_wday uses 0-6 for Mon-Sun, we want 1-7 for Sun-Sat
        COLUMN = (NOW.tm_wday + 1) % 7 + 1

        TASK_LIST = '' # Clear task list string
        for entry in ENTRIES:
            cell = entry['gs$cell']
            if int(cell['row']) > 1 and int(cell['col']) is COLUMN:
                TASK_LIST += cell['$t'] + '\n' # Task + newline character

        # Refreshing the display is jarring, so only do it if the task list
        # or day has changed. This requires preserving state between passes,
        # and is why this code doesn't deep sleep (which is like a reset).
        if TASK_LIST != PRIOR_LIST or PRIOR_DAY != NOW.tm_wday:

            # Set the day-of-week label at top
            MAGTAG.set_text(DAYS[COLUMN - 1], auto_refresh=False)

            # Set the "Updated" date and time label
            if DD_MM:
                DATE = '%d/%d' % (NOW.tm_mday, NOW.tm_mon)
            else:
                DATE = '%d/%d' % (NOW.tm_mon, NOW.tm_mday)
            MAGTAG.set_text('Updated %s %s' % (DATE, hh_mm(NOW, TWELVE_HOUR)),
                            2, auto_refresh=False)

            MAGTAG.set_text(TASK_LIST, 1) # Update list, refresh display
            PRIOR_LIST = TASK_LIST        # Save list state for next pass
            PRIOR_DAY = NOW.tm_wday       # Save day-of-week for next pass

    except RuntimeError as error:
        # If there's an error above, no harm, just try again in ~15 minutes.
        # Usually it's a common network issue or time server hiccup.
        print('Retrying in 15 min - ', error)

    time.sleep(15 * 60) # Whether OK or error, wait 15 mins for next pass
