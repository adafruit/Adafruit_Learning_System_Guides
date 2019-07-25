"""
This example uses a PyPortal and rgbw leds for a simple "wake up" light.
The strip starts to brighten 30 minutes before set wake up time.
This program assumes a neopixel strip is attached to D4 on the Adafruit PyPortal.
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
                 up_time_sunday)

# set neopixel min and max brightness
BRIGHTNESS = 0
MIN_BRIGHTNESS = 0
MAX_BRIGHTNESS = 0.85
# initialize neopixel strip
num_pixels = 30
ORDER = neopixel.RGBW
strip = neopixel.NeoPixel(board.D3, num_pixels, brightness=BRIGHTNESS,
                          pixel_order=ORDER)
strip.fill(0)
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

def whichDay():
    now = time.localtime()
    current_hour, current_minutes = now[3:5]
    current_day = now[6]
    wake_up_hour, wake_up_minutes = default_wake_up.split(":")
    wake_up_hour = int(wake_up_hour)
    wake_up_minutes = int(wake_up_minutes[:-1])
    print(wake_up_hour, ":", wake_up_minutes)
     # if it's after midnight and before the default wakeup time, display the wake up time of today
    for day in range(len(wake_up_times)):
        if current_hour < wake_up_hour and current_minutes < wake_up_minutes:
            if current_day == day:
                input_wake_up_time = wake_up_times[day]
    # set wake up time to the next day's wake up time the night before
        else:
            if current_day == 6:
                input_wake_up_time = wake_up_times[0]
            else:
                if current_day == day:
                    input_wake_up_time = wake_up_times[day+1]
    input_wake_up_time_text = "Wake up at " + input_wake_up_time
    wakeup_time_textarea.text = input_wake_up_time_text
    return input_wake_up_time

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

def parseTime(time_before):
    # parse given time string into hour minute and AM_PM elements
    hours_before, minutes_before = time_before.split(":")
    AM_PM_str = minutes_before[-1:]
    minutes_before = int(minutes_before[:-1])
    if AM_PM_str == 'P':
        hours_before = int(hours_before) + 12
    elif ((hours_before == '12') and (AM_PM_str == 'A')):
        hours_before = 0
    else:
        hours_before = int(hours_before)
    parsed_time = [hours_before, minutes_before]
    return parsed_time

def subtract30min(time_before): # subtract 30 min
    parsed_time = parseTime(time_before)
    hours_before, minutes_before = parsed_time[0:2]
    now = time.localtime()
    future = time.mktime((now[0], now[1], now[2], hours_before, minutes_before - 30, now[5], now[6], now[7], now[8]))
    futureTime = time.localtime(future)
    future_hour = futureTime[3]
    future_minutes = futureTime[4]
    light_on_time_textarea.text = "Light starting at: " + formatTime(future_hour, future_minutes)
    return formatTime(future_hour, future_minutes)

# backlight function - if screen tapped, turn on back light for 30 seconds?
def backLight(time_before):
    parsed_time = parseTime(time_before)
    hours_before, minutes_before = parsed_time[0:2]
    now = time.localtime()
    wakeUpNow = time.mktime((now[0], now[1], now[2], hours_before, minutes_before, now[5], now[6], now[7], now[8]))
    nowVal = time.mktime((now[0], now[1], now[2], now[3], now[4], now[5], now[6], now[7], now[8]))
    print(nowVal - wakeUpNow)
    if (nowVal - wakeUpNow) > 32400:
    # if time is more than 9 hours after wake up time, backlight off, tap to turn on
        if pyportal.touchscreen.touch_point:
            pyportal.set_backlight(backlight_on)
            time.sleep(5)
            pyportal.set_backlight(backlight_off)
    else:
        pyportal.set_backlight(backlight_on)

refresh_time = None

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
    time_str_text = displayTime()
    print(time_str_text)
    currentHour = time.localtime()
    # determine which wake up time to choose based on the day
    wake_up_time = whichDay()
    # if time is more than 9 hours after wake up time, backlight off and can tap to turn on
    backLight(wake_up_time)
    # start the light 30 min before wake up time
    start_light_time = subtract30min(wake_up_time)
    print(start_light_time)
    # If wake up time - 30 minutes equals current time, start the light
    if time_str_text == start_light_time:
        print("Starting wake up light")
        # turn on backlight
        pyportal.set_backlight(backlight_on)
        for i in range(light_minutes - 1):
            BRIGHTNESS = BRIGHTNESS + (MAX_BRIGHTNESS/light_minutes) # max 0.25, min 0.0
            strip.fill(WHITE)
            strip.brightness = BRIGHTNESS
            displayTime()
            time.sleep(1) # 60 for once per min
        while not pyportal.touchscreen.touch_point: # turn strip off
            displayTime()
            time.sleep(1)
            continue
        strip.brightness = MIN_BRIGHTNESS
    # update every 15 seconds
    time.sleep(15)