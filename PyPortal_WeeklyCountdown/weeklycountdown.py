"""
This example will figure out the current local time using the internet, and
then draw out a countdown clock until an event occurs!
Once the event is happening, a new graphic is shown
"""
import time
import board
from adafruit_pyportal import PyPortal
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.label import Label

# The time of the thing!
EVENT_WEEKDAY = 2       # monday = 0 .. sunday = 6
EVENT_HOUR = 20         # in 24-hour time
EVENT_MINUTE = 00
EVENT_DURATION = 3600   # in seconds!
# Instead of messing around with timezones, just put in
# the *location* of the event, and we'll automatically set the PyPortal's
# time to that location. Then compute the math from there
# for a list of valid locations, see http://worldtimeapi.org/api/timezone
EVENT_LOCATION = "America/New_York"  # set to None if its for your local time

# the current working directory (where this file is)
cwd = ("/"+__file__).rsplit('/', 1)[0]
event_background = cwd+"/countdown_event.bmp"
countdown_background = cwd+"/countdown_background.bmp"

# Initialize the pyportal object and let us know what data to fetch and where
# to display it
pyportal = PyPortal(status_neopixel=board.NEOPIXEL,
                    default_bg=countdown_background)

big_font = bitmap_font.load_font(cwd+"/fonts/Helvetica-Bold-36.bdf")
big_font.load_glyphs(b'0123456789') # pre-load glyphs for fast printing

days_position = (25, 212)
hours_position = (110, 212)
minutes_position = (220, 212)
text_color = 0x000000

text_areas = []
for pos in (days_position, hours_position, minutes_position):
    textarea = Label(big_font, text='  ')
    textarea.x = pos[0]
    textarea.y = pos[1]
    textarea.color = text_color
    pyportal.splash.append(textarea)
    text_areas.append(textarea)
refresh_time = None

while True:
    # only query the online time once per hour (and on first run)
    if (not refresh_time) or (time.monotonic() - refresh_time) > 3600:
        try:
            print("Getting time from internet!")
            pyportal.get_local_time(location=EVENT_LOCATION)
            refresh_time = time.monotonic()
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
            continue

    the_time = time.localtime()
    print("Time at location", EVENT_LOCATION, ":", the_time)

    # The easiest way to tell when
    mins_remaining = EVENT_MINUTE - the_time[4]
    if mins_remaining < 0:
        mins_remaining += 60
    # add minutes to go forward
    the_time = time.localtime(time.mktime(the_time) + mins_remaining * 60)
    #print("minute fastforward:", the_time)

    hours_remaining = EVENT_HOUR - the_time[3]
    if hours_remaining < 0:
        hours_remaining += 24
    # add hours to go forward
    the_time = time.localtime(time.mktime(the_time) + hours_remaining * 60 * 60)
    #print("hour fastforward:", the_time)

    days_remaining = EVENT_WEEKDAY - the_time[6]
    if days_remaining < 0:
        days_remaining += 7

    total_sec_remaining = days_remaining * 24 * 60 * 60
    total_sec_remaining += hours_remaining * 60 * 60
    total_sec_remaining += mins_remaining * 60

    print("Remaining: %d days, %d hours, %d minutes (%d total seconds)" %
          (days_remaining, hours_remaining, mins_remaining, total_sec_remaining))

    week_of_seconds = 604800
    if (week_of_seconds - total_sec_remaining) < EVENT_DURATION:
        print("ITS HAPPENING!")
        pyportal.set_background(event_background)
    else:
        pyportal.set_background(countdown_background)
        text_areas[0].text = '{:>1}'.format(days_remaining)  # set days textarea
        text_areas[1].text = '{:>2}'.format(hours_remaining) # set hours textarea
        text_areas[2].text = '{:>2}'.format(mins_remaining)  # set minutes textarea

    # update every 30 seconds
    time.sleep(30)
