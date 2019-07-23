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

# Type in time to get up  each day of the week
input_wake_up_time = ""
up_time_monday = "6:30A"
up_time_tuesday = "6:30A"
up_time_wednesday = "6:30A"
up_time_thursday = "6:30A"
up_time_friday = "6:30A"
up_time_saturday = "10:00A"
up_time_sunday = "10:00A"

# set neopixel min and max brightness
BRIGHTNESS = 0
MIN_BRIGHTNESS = 0
MAX_BRIGHTNESS = 0.85
#initialize neopixel strip
strip = neopixel.NeoPixel(board.D3, 40, brightness=BRIGHTNESS)
strip.fill(0)
# number of minutes it takes for strip to fade from min to max
light_minutes = 30

# determine the current working directory
# needed so we know where to find files
cwd = ("/"+__file__).rsplit('/', 1)[0]

# Initialize the pyportal object and let us know what data to fetch and where
# to display it
pyportal = PyPortal(status_neopixel=board.NEOPIXEL,
                    default_bg=0x000000)

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
    current_day = now[6]
    if current_day == 0:
        input_wake_up_time = up_time_monday
    elif current_day == 1:
        input_wake_up_time = up_time_tuesday
    elif current_day == 2:
        input_wake_up_time = up_time_wednesday
    elif current_day == 3:
        input_wake_up_time = up_time_thursday
    elif current_day == 4:
        input_wake_up_time = up_time_friday
    elif current_day == 5:
        input_wake_up_time = up_time_saturday
    elif current_day == 6:
        input_wake_up_time = up_time_sunday
    input_wake_up_time_text = "Wake up at " + input_wake_up_time
    wakeup_time_textarea.text = input_wake_up_time_text
    return input_wake_up_time

def subtract30min(time_before):
    hours_before, minutes_before = time_before.split(":")
    AM_PM_str = minutes_before[-1:]
    minutes_before = int(minutes_before[:-1])
    if AM_PM_str == 'P':
        hours_before = int(hours_before) + 12
    elif ((hours_before == '12') and (AM_PM_str == 'A')):
        hours_before = 0
    else:
        hours_before = int(hours_before)
    if  minutes_before >= 30:
        minutes_after = minutes_before - 30
        # display the time in a nice big font
        format_str = "%d:%02d"
        if hours_before >= 12:
            hours_after = hours_before - 12
            format_str = format_str+"P"
        else:
            hours_after = hours_before
            format_str = format_str+"A"
        if hours_before == 0:
            hours_after = 12
        sub30_str = format_str % (hours_after, minutes_after)
        light_on_time_textarea.text = "Light starting at: " + sub30_str
        return sub30_str
    elif minutes_before < 30:
        minutes_after = minutes_before + 30
        hours_after = hours_before - 1
        format_str = "%d:%02d"
        if hours_before >= 12:
            hours_after = hours_before - 12
            format_str = format_str+"P"
        else:
            hours_after = hours_before
            format_str = format_str+"A"
        if hours_before == 0:
            hours_after = 11
            format_str = format_str[:-1]+"P"
        sub30_str = format_str % (hours_after, minutes_after)
        light_on_time_textarea.text = "Light starting at: " + sub30_str
        return sub30_str

def displayTime():
    now = time.localtime()
    hour, minute = now[3:5]
    print(now)
    print("Current time: %02d:%02d" % (hour, minute))
    # display the time in a nice big font
    format_str = "%d:%02d"
    if hour >= 12:
        hour -= 12
        format_str = format_str+"P"
    else:
        format_str = format_str+"A"
    if hour == 0:
        hour = 12
    time_str = format_str % (hour, minute)
    time_textarea.text = time_str
    return time_str

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
    # if after 9am and before 9pm light is = 0.8
    if currentHour[3] > 9 and currentHour[3] < 21:
        pyportal.set_backlight(0.8)
    # if after 9pm and before 9am light = 0.1
    else:
        pyportal.set_backlight(0.1)
    input_wake_up_time = whichDay()
   # sub30 = subtract30min(currentHour) # input needs to be input_wake_up_time_text
    subtract30min(input_wake_up_time)
    # If wake up time - 30 minutes equals current time, start the light
    if time_str_text is input_wake_up_time:
        print("Starting wake up light")
        for i in range(light_minutes - 1):
            BRIGHTNESS = BRIGHTNESS + (MAX_BRIGHTNESS/light_minutes) # max 0.25, min 0.0
            strip.fill((255, 255, 255))
            strip.brightness = BRIGHTNESS
            displayTime()
            time.sleep(60) # 60 for once per min
        while not pyportal.touchscreen.touch_point:
            displayTime()
            time.sleep(1)
            pass
        strip.brightness = MIN_BRIGHTNESS
    # update every 15 seconds
    time.sleep(15)