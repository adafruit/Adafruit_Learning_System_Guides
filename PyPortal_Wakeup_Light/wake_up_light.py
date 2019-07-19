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


# Type in time to get up
input_wake_up_time = "8:00A"

board.DISPLAY.brightness = 0.1

BRIGHTNESS = 0
MIN_BRIGHTNESS = 0
MAX_BRIGHTNESS = 0.2 # brightness above 0.2 crashes pyportal

strip = neopixel.NeoPixel(board.D4, 144, brightness=BRIGHTNESS)

strip.brightness = MIN_BRIGHTNESS


light_minutes = 30

# Set to True for '12 hour + AM/PM' time, set to false for 24 hour time
AM_PM = True

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


input_wake_up_time_text = "Wake up 30 min after: " + input_wake_up_time
#light_on_time_text = "Light starting at: " # - 30 minutes? how?

time_color = 0xFFFFFF
time_position = (75,130)
time_textarea = Label(big_font, max_glyphs=15, color=time_color,
                                x=time_position[0], y=time_position[1])

wakeup_time_color = 0xFFFFFF
wakeup_time_position = (15,200)
wakeup_time_textarea = Label(info_font, max_glyphs=30, color=wakeup_time_color,
                                x=wakeup_time_position[0], y=wakeup_time_position[1])

pyportal.splash.append(time_textarea)
wakeup_time_textarea.text = input_wake_up_time_text
pyportal.splash.append(wakeup_time_textarea)

#def subtract30min(time_raw):


def displayTime():
    now = time.localtime()
    hour, minute = now[3:5]
    print(now)
    print("Current time: %02d:%02d" % (hour, minute))

    # display the time in a nice big font
    format_str = "%d:%02d"
    if AM_PM:
        if hour >= 12:
            hour -= 12
            format_str = format_str+"P"
        else:
            format_str = format_str+"A"
        if hour == 0:
            hour = 12
    if hour < 10:
        format_str = ""+format_str
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
    print(input_wake_up_time)

    # If wake up time - 30 minutes equals current time, start the light
    if time_str_text is input_wake_up_time:
        print("Starting wake up light")
        for i in range(light_minutes - 1):
            BRIGHTNESS = BRIGHTNESS + (MAX_BRIGHTNESS/light_minutes) # max 0.25, min 0.0
            print(BRIGHTNESS)

            strip.fill((255, 255, 255))
            strip.brightness = BRIGHTNESS

            displayTime()

            time.sleep(60)
        while not pyportal.touchscreen.touch_point:
            pass
        strip.brightness = MIN_BRIGHTNESS

    # update every 15 seconds
    time.sleep(15)