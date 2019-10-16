"""
This example uses a PyPortal and rgbw leds for a simple "wake up" light.
The strip starts to brighten 30 minutes before set wake up time.
This program assumes a neopixel strip is attached to D3 on the Adafruit PyPortal.
"""
import time
import board
import neopixel
from adafruit_pyportal import PyPortal
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.Label import Label

# type in time to get up  each day of the week
default_wake_up = "6:30A"
up_time_monday = default_wake_up
up_time_tuesday = default_wake_up
up_time_wednesday = default_wake_up
up_time_thursday = default_wake_up
up_time_friday = default_wake_up
up_time_saturday = "10:00A"
up_time_sunday = "10:00A"
wake_up_times = (up_time_monday,
                 up_time_tuesday,
                 up_time_wednesday,
                 up_time_thursday,
                 up_time_friday,
                 up_time_saturday,
                 up_time_sunday,
                 default_wake_up)
days_str = ("Mon.", "Tues.", "Wed.", "Thurs.", "Fri.", "Sat.", "Sun.")

# set neopixel min and max brightness
BRIGHTNESS = 0
MIN_BRIGHTNESS = 0
MAX_BRIGHTNESS = 0.85
# initialize neopixel strip
num_pixels = 30
ORDER = neopixel.RGBW
strip = neopixel.NeoPixel(board.D3, num_pixels, brightness=BRIGHTNESS,
                          pixel_order=ORDER)
strip.fill(0) # start it set to off
# color of strip
WHITE = (0, 0, 0, 255)
# number of minutes it takes for strip to fade from min to max
light_minutes = 30

# determine the current working directory
# needed so we know where to find files
cwd = ("/"+__file__).rsplit('/', 1)[0]

# initialize the pyportal object and let us know what data to fetch and where
# to display it
pyportal = PyPortal(status_neopixel=board.NEOPIXEL,
                    default_bg=0x000000)

# set backlight default to off
backlight_off = 0
backlight_on = 0.8
pyportal.set_backlight(backlight_off)

# assign fonts
big_font = bitmap_font.load_font(cwd+"/fonts/Nunito-Light-75.bdf")
big_font.load_glyphs(b'0123456789:AP') # pre-load glyphs for fast printing
print('loading fonts...')
info_font = bitmap_font.load_font(cwd+"/fonts/Nunito-Black-17.bdf")
info_font.load_glyphs(b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.:/ ')

time_color = 0xFFFFFF
time_position = (75,130)
time_textarea = Label(big_font, max_glyphs=15, color=time_color,
                      x=time_position[0], y=time_position[1])

wakeup_time_color = 0xFFFFFF
wakeup_time_position = (15,200)
wakeup_time_textarea = Label(info_font, max_glyphs=30, color=wakeup_time_color,
                             x=wakeup_time_position[0], y=wakeup_time_position[1])

light_on_time_color = 0xFFFFFF
light_on_time_position = (15,220)
light_on_time_textarea = Label(info_font, max_glyphs=30, color=light_on_time_color,
                               x=light_on_time_position[0], y=light_on_time_position[1])

pyportal.splash.append(time_textarea)
pyportal.splash.append(wakeup_time_textarea)
pyportal.splash.append(light_on_time_textarea)

while True:
    try:
        print("Getting time from internet!")
        pyportal.get_local_time()
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)
        continue
    break

# parse given time string into hour minute and AM_PM elements
def parseTime(time_before):
    hours_before, minutes_before = time_before.split(":")
    AM_PM_str = minutes_before[-1:]
    minutes_before = int(minutes_before[:-1])
    if (hours_before != '12') and AM_PM_str == 'P':
        hours_before = int(hours_before) + 12
    elif ((hours_before == '12') and (AM_PM_str == 'P')):
        hours_before = int(hours_before)
    elif ((hours_before == '12') and (AM_PM_str == 'A')):
        hours_before = 0
    else:
        hours_before = int(hours_before)
    parsed_time = [hours_before, minutes_before]
    return parsed_time

# get time objects for wake up times
val_times = []
parsed_times = []
for i in range(len(wake_up_times)):
    parsed_time_day = parseTime(wake_up_times[i])
    hours, minutes = parsed_time_day[0:2]
    now_day = time.localtime()
    time_obj_mk = time.mktime((now_day[0], now_day[1], now_day[2], hours,
                               minutes, now_day[5], i, now_day[7], now_day[8]))
    time_obj = time.localtime(time_obj_mk)
    val_times.append(time_obj_mk)
    parsed_times.append(time_obj)

# determine which day it is and print which time waking up on screen
def whichDay():
    now = time.localtime()
    current_day = now[6]
    now_mk = time.mktime((now[0], now[1], now[2], now[3], now[4], now[5], now[6], now[7], now[8]))
    # if it's after midnight and before todays wakeup time, display the wake up time of today
    for day in range(len(wake_up_times)):
        if now_mk < val_times[day]:
            if current_day == day:
                input_wake_up_time = wake_up_times[day]
                use_day = day
    # set wake up time to the next day's wake up time after current day's wake up time
        else:
            if current_day == 6:
                input_wake_up_time = wake_up_times[0]
                use_day = 0
            else:
                if current_day == day:
                    input_wake_up_time = wake_up_times[day+1]
                    use_day = day + 1
    input_wake_up_time_text = "Wake up " + days_str[use_day] + " at " + input_wake_up_time
    wakeup_time_textarea.text = input_wake_up_time_text
    return use_day

def displayTime():
    now = time.localtime()
    hour, minute = now[3:5]
    print(now)
    print("Current time: %02d:%02d" % (hour, minute))
    formatTime(hour, minute)
    time_textarea.text = formatTime(hour, minute)
    return formatTime(hour, minute)

def formatTime(raw_hours, raw_minutes):
    # display the time in a nice big font
    format_str = "%d:%02d"
    if raw_hours >= 12:
        raw_hours -= 12
        format_str = format_str+"P"
    else:
        format_str = format_str+"A"
    if raw_hours == 0:
        raw_hours = 12
    time_str = format_str % (raw_hours, raw_minutes)
    return time_str

def backLight():
    now = time.localtime()
    now_val = time.mktime((now[0], now[1], now[2], now[3], now[4], now[5], now[6], now[7], now[8]))
    wake_up_day_val = val_times[now[6]]
    # if time is more than 9 hours after current day's wake up time,
    # or time is before light start time, backlight off, tap to turn on
    if (now_val - wake_up_day_val) > 32400 or (now_val - wake_up_day_val) < -1800:
        pyportal.set_backlight(backlight_off)
        if pyportal.touchscreen.touch_point:
            pyportal.set_backlight(backlight_on)
            time.sleep(5)
            pyportal.set_backlight(backlight_off)
    else:
        pyportal.set_backlight(backlight_on)

def subtract30min(day): # subtract 30 min
    # get the time object from the corresponding day
    raw_wake_up_time = parsed_times[day]
    now = time.localtime()
    # new time subtracting 30 min from wake up time
    minus30 = time.mktime((now[0], now[1], now[2], raw_wake_up_time[3],
                           raw_wake_up_time[4] - 30, now[5], now[6], now[7], now[8]))
    time_minus30 = time.localtime(minus30)
    hour_minus30 = time_minus30[3]
    minutes_minus30 = time_minus30[4]
    light_on_time_textarea.text = "Light starting at: " + formatTime(hour_minus30, minutes_minus30)
    return formatTime(hour_minus30, minutes_minus30)

refresh_time = None

while True:
    time_now = time.localtime()
    # only query the online time once per hour (and on first run)
    if (not refresh_time) or (time.monotonic() - refresh_time) > 3600:
        try:
            print("Getting time from internet!")
            pyportal.get_local_time()
            refresh_time = time.monotonic()
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
            continue
    time_str_text = displayTime()
    print(time_str_text)
    # determine which wake up time to choose based on the day
    wake_up_day = whichDay()
    # if time is more than 9 hours after previous day's wake up time,
    # backlight off and can tap to turn on
    backLight()
    # start the light 30 min before wake up time
    start_light_time = subtract30min(wake_up_day)
    # If current day is same as wake up day and
    # wake up time - 30 minutes equals current time, start the light
    if wake_up_day == time_now[6] and time_str_text == start_light_time:
        print("Starting wake up light")
        # turn on backlight
        pyportal.set_backlight(backlight_on)
        for i in range(light_minutes - 1):
            BRIGHTNESS = BRIGHTNESS + (MAX_BRIGHTNESS/light_minutes) # max 0.25, min 0.0
            strip.fill(WHITE)
            strip.brightness = BRIGHTNESS
            displayTime()
            time.sleep(60) # 60 for once per min
        while not pyportal.touchscreen.touch_point: # turn strip off
            displayTime()
            time.sleep(1)
            continue
        strip.brightness = MIN_BRIGHTNESS
    # update every second so that screen can be tapped to view time
    time.sleep(1)
