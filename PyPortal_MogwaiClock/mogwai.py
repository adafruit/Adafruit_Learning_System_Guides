"""
This example will figure out the current local time using the internet, and
then draw out a count-up clock since an event occurred!
Once the event is happening, a new graphic is shown
"""
import time
import board
from adafruit_pyportal import PyPortal
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.Label import Label

# Set to True for '12 hour + AM/PM' time, set to false for 24 hour time
AM_PM = True

# When to stop feeding                      Hr, Min, Sec
gremlin_time = time.struct_time((2019, 1, 1, 00, 00, 00, -1, -1, 0))
mogwai_time = time.struct_time((2019, 1, 1, 8, 00, 00, -1, -1, 0))
print(gremlin_time, mogwai_time)

# If you want to set the time for experimentation
#                                     yr, mon, day, h, min, sec
#import rtc
#rtc.RTC().datetime = time.struct_time((2019, 1, 1, 23, 59, 00, 0, 0, -1))

# determine the current working directory
# needed so we know where to find files
cwd = ("/"+__file__).rsplit('/', 1)[0]
# Initialize the pyportal object and let us know what data to fetch and where
# to display it
mogwai_image = cwd+"/mogwai_background.bmp"
mogwai_sound = cwd+"/mogwai_alarm.wav"
gremlin_image = cwd+"/gremlin_background.bmp"
gremlin_sound = cwd+"/gremlin_alarm.wav"
pyportal = PyPortal(status_neopixel=board.NEOPIXEL,
                    default_bg="pyportal_startup.bmp")

big_font = bitmap_font.load_font(cwd+"/fonts/DSEG14ModernMiniBI-44.bdf")
big_font.load_glyphs(b'0123456789:AP') # pre-load glyphs for fast printing

time_textarea = Label(big_font, max_glyphs=15)
time_textarea.x = 0
time_textarea.y = 130
time_textarea.color = 0xFF0000
pyportal.splash.append(time_textarea)

# To help us know if we've changed the times, print them out!
gremlin_hour, gremlin_min = gremlin_time[3:5]
print("Gremlin time: %02d:%02d" % (gremlin_hour, gremlin_min))
mogwai_hour, mogwai_min = mogwai_time[3:5]
print("Mogwai time: %02d:%02d" % (mogwai_hour, mogwai_min))
gremlin_since_midnite = gremlin_hour*60+gremlin_min
mogwai_since_midnite = mogwai_hour*60+mogwai_min

# this is how we track whether to flip images
is_gremlin_time = None
last_gremlin_time = is_gremlin_time

refresh_time = time.monotonic()

while True:
    # only query the online time once per hour (and on first run)
    if (not refresh_time) or (time.monotonic() - refresh_time) > 3600:
        try:
            print("Getting time from internet!")
            pyportal.get_local_time()
            refresh_time = time.monotonic()
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
            continue

    now = time.localtime()
    hour, minute = now[3:5]
    print("Current time: %02d:%02d" % (hour, minute))
    time_since_midnite = hour*60 + minute

    # display the time in a nice big font
    format_str = "%d:%02d"
    if AM_PM:
        if hour >= 12:
            hour -= 12
            format_str = format_str+"   P"
        else:
            format_str = format_str+"   A"
        if hour == 0:
            hour = 12
    if hour < 10:
        format_str = "    "+format_str
    time_str = format_str % (hour, minute)
    time_textarea.text = time_str

    if gremlin_since_midnite < mogwai_since_midnite:
        #print("Gremlin time before mogwai time")
        if gremlin_since_midnite <= time_since_midnite < mogwai_since_midnite:
            is_gremlin_time = True
        else:
            is_gremlin_time = False
    else:
        #print("Mogwai time before gremlin time")
        if mogwai_since_midnite <= time_since_midnite < gremlin_since_midnite:
            is_gremlin_time = False
        else:
            is_gremlin_time = True

    if is_gremlin_time != last_gremlin_time:
        if is_gremlin_time:
            print("GREMLIN TIME!")
            pyportal.set_background(gremlin_image)
            pyportal.play_file(gremlin_sound)
        else:
            print("MOGWAI TIME!")
            pyportal.set_background(mogwai_image)
            pyportal.play_file(mogwai_sound)

    last_gremlin_time = is_gremlin_time


    # update every 10 seconds
    #time.sleep(10)
