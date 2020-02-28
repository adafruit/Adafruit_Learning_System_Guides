import time
from calendar import alarms
from calendar import timers
import board
import displayio
from digitalio import DigitalInOut, Direction, Pull
from adafruit_button import Button
from adafruit_pyportal import PyPortal
import openweather_graphics  # pylint: disable=wrong-import-position

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Use cityname, country code where countrycode is ISO3166 format.
# E.g. "New York, US" or "London, GB"
LOCATION = secrets['location']

# Set up where we'll be fetching data from
DATA_SOURCE = "http://api.openweathermap.org/data/2.5/weather?q="+LOCATION
DATA_SOURCE += "&appid="+secrets['openweather_token']
# You'll need to get a token from openweather.org, looks like 'b6907d289e10d714a6e88b30761fae22'
DATA_LOCATION = []

# Initialize the pyportal object and let us know what data to fetch and where
# to display it
pyportal = PyPortal(url=DATA_SOURCE,
                    json_path=DATA_LOCATION,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=0x000000)

display = board.DISPLAY

#  the alarm sound file locations
alarm_sound_trash = "/sounds/trash.wav"
alarm_sound_bed = "/sounds/sleep.wav"
alarm_sound_eat = "/sounds/eat.wav"

#  the alarm sounds in an array that matches the order of the gfx & alarm check-ins
alarm_sounds = [alarm_sound_trash, alarm_sound_bed,
                alarm_sound_eat, alarm_sound_eat, alarm_sound_eat]

#  setting up the bitmaps for the alarms

#  sleep alarm
sleep_bitmap = displayio.OnDiskBitmap(open("/sleepBMP.bmp", "rb"))
sleep_tilegrid = displayio.TileGrid(sleep_bitmap, pixel_shader=displayio.ColorConverter())
group_bed = displayio.Group()
group_bed.append(sleep_tilegrid)

#  trash alarm
trash_bitmap = displayio.OnDiskBitmap(open("/trashBMP.bmp", "rb"))
trash_tilegrid = displayio.TileGrid(trash_bitmap, pixel_shader=displayio.ColorConverter())
group_trash = displayio.Group()
group_trash.append(trash_tilegrid)

#  meal alarm
eat_bitmap = displayio.OnDiskBitmap(open("/eatBMP.bmp", "rb"))
eat_tilegrid = displayio.TileGrid(eat_bitmap, pixel_shader=displayio.ColorConverter())
group_eat = displayio.Group()
group_eat.append(eat_tilegrid)

#  snooze touch screen buttons
#  one for each alarm bitmap
snooze_controls = [
    {'label': "snooze_trash", 'pos': (4, 222), 'size': (236, 90), 'color': None},
    {'label': "snooze_bed", 'pos': (4, 222), 'size': (236, 90), 'color': None},
    {'label': "snooze_eat", 'pos': (4, 222), 'size': (236, 90), 'color': None},
    ]

#  setting up the snooze buttons as buttons
snooze_buttons = []
for s in snooze_controls:
    snooze_button = Button(x=s['pos'][0], y=s['pos'][1],
                           width=s['size'][0], height=s['size'][1],
                           style=Button.RECT,
                           fill_color=s['color'], outline_color=None,
                           name=s['label'])
    snooze_buttons.append(snooze_button)

#  dismiss touch screen buttons
#  one for each alarm bitmap
dismiss_controls = [
    {'label': "dismiss_trash", 'pos': (245, 222), 'size': (230, 90), 'color': None},
    {'label': "dismiss_bed", 'pos': (245, 222), 'size': (230, 90), 'color': None},
    {'label': "dismiss_eat", 'pos': (245, 222), 'size': (230, 90), 'color': None},
    ]

#  setting up the dismiss buttons as buttons
dismiss_buttons = []
for d in dismiss_controls:
    dismiss_button = Button(x=d['pos'][0], y=d['pos'][1],
                            width=d['size'][0], height=d['size'][1],
                            style=Button.RECT,
                            fill_color=d['color'], outline_color=None,
                            name=d['label'])
    dismiss_buttons.append(dismiss_button)

#  adding the touch screen buttons to the different alarm gfx groups
group_trash.append(snooze_buttons[0].group)
group_trash.append(dismiss_buttons[0].group)
group_bed.append(snooze_buttons[1].group)
group_bed.append(dismiss_buttons[1].group)
group_eat.append(snooze_buttons[2].group)
group_eat.append(dismiss_buttons[2].group)

#  setting up the hardware snooze/dismiss buttons
switch_snooze = DigitalInOut(board.D3)
switch_snooze.direction = Direction.INPUT
switch_snooze.pull = Pull.UP

switch_dismiss = DigitalInOut(board.D4)
switch_dismiss.direction = Direction.INPUT
switch_dismiss.pull = Pull.UP

#  grabbing the alarm times from the calendar file
#  'None' is the placeholder for trash, which is weekly rather than daily
alarm_checks = [None, alarms['bed'],alarms['breakfast'],alarms['lunch'],alarms['dinner']]
#  all of the alarm graphics
alarm_gfx = [group_trash, group_bed, group_eat, group_eat, group_eat]

#  allows for the openweather_graphics to show
gfx = openweather_graphics.OpenWeather_Graphics(pyportal.splash, am_pm=True, celsius=False)

#  state machines
localtile_refresh = None
weather_refresh = None
dismissed = None
touched = None
start = None
alarm = None
snoozed = None
touch_button_snooze = None
touch_button_dismiss = None
phys_dismiss = None
phys_snooze = None
mode = 0
button_mode = 0

#  weekday array
weekday = ["Mon.", "Tues.", "Wed.", "Thurs.", "Fri.", "Sat.", "Sun."]

#  weekly alarm setup. checks for weekday and time
weekly_alarms = [alarms['trash']]
weekly_day = [alarms['trash'][0]]
weekly_time = [alarms['trash'][1]]

while True:
    # while esp.is_connected:
    # only query the online time once per hour (and on first run)
    if (not localtile_refresh) or (time.monotonic() - localtile_refresh) > 3600:
        try:
            print("Getting time from internet!")
            pyportal.get_local_time()
            localtile_refresh = time.monotonic()
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
            continue

    if not alarm:
    # only query the weather every 10 minutes (and on first run)
    #  only updates if an alarm is not active
        if (not weather_refresh) or (time.monotonic() - weather_refresh) > 600:
            try:
                value = pyportal.fetch()
                print("Response is", value)
                gfx.display_weather(value)
                weather_refresh = time.monotonic()
            except RuntimeError as e:
                print("Some error occured, retrying! -", e)
                continue
    #  updates time to check alarms
    #  checks every 30 seconds
    #  identical to def(update_time) in openweather_graphics.py
    if (not start) or (time.monotonic() - start) > 30:
        #  grabs all the time data
        clock = time.localtime()
        date = clock[2]
        hour = clock[3]
        minute = clock[4]
        day = clock[6]
        today = weekday[day]
        format_str = "%d:%02d"
        date_format_str = " %d, %d"
        if hour >= 12:
            hour -= 12
            format_str = format_str+" PM"
        else:
            format_str = format_str+" AM"
        if hour == 0:
            hour = 12
        #  formats date display
        today_str = today
        time_str = format_str % (hour, minute)
        #  checks for weekly alarms
        for i in weekly_alarms:
            w = weekly_alarms.index(i)
            if time_str == weekly_time[w] and today == weekly_day[w]:
                print("trash time")
                alarm = True
                if alarm and not dismissed and not snoozed:
                    display.show(alarm_gfx[w])
                    pyportal.play_file(alarm_sounds[w])
                mode = w
                print("mode is:", mode)
        #  checks for daily alarms
        for i in alarm_checks:
            a = alarm_checks.index(i)
            if time_str == alarm_checks[a]:
                alarm = True
                if alarm and not dismissed and not snoozed:
                    display.show(alarm_gfx[a])
                    pyportal.play_file(alarm_sounds[a])
                mode = a
                print(mode)
        #  calls update_time() from openweather_graphics to update
        #  clock display
        gfx.update_time()
        gfx.update_date()
        #  resets time counter
        start = time.monotonic()

    #  allows for the touchscreen buttons to work
    if mode > 1:
        button_mode = 2
    else:
        button_mode = mode
        #  print("button mode is", button_mode)

    #  hardware snooze/dismiss button setup
    if switch_dismiss.value and phys_dismiss:
        phys_dismiss = False
    if switch_snooze.value and phys_snooze:
        phys_snooze = False
    if not switch_dismiss.value and not phys_dismiss:
        phys_dismiss = True
        print("pressed dismiss button")
        dismissed = True
        alarm = False
        display.show(pyportal.splash)
        touched = time.monotonic()
        mode = mode
    if not switch_snooze.value and not phys_snooze:
        phys_snooze = True
        print("pressed snooze button")
        display.show(pyportal.splash)
        snoozed = True
        alarm = False
        touched = time.monotonic()
        mode = mode

    #  touchscreen button setup
    touch = pyportal.touchscreen.touch_point
    if not touch and touch_button_snooze:
        touch_button_snooze = False
    if not touch and touch_button_dismiss:
        touch_button_dismiss = False
    if touch:
        if snooze_buttons[button_mode].contains(touch) and not touch_button_snooze:
            print("Touched snooze")
            display.show(pyportal.splash)
            touch_button_snooze = True
            snoozed = True
            alarm = False
            touched = time.monotonic()
            mode = mode
        if dismiss_buttons[button_mode].contains(touch) and not touch_button_dismiss:
            print("Touched dismiss")
            dismissed = True
            alarm = False
            display.show(pyportal.splash)
            touch_button_dismiss = True
            touched = time.monotonic()
            mode = mode

    #  this is a little delay so that the dismissed state
    #  doesn't collide with the alarm if it's dismissed
    #  during the same time that the alarm activates
    if (not touched) or (time.monotonic() - touched) > 70:
        dismissed = False
    #  snooze portion
    #  pulls snooze_time from calendar and then when it's up
    #  splashes the snoozed alarm's graphic, plays the alarm sound and goes back into
    #  alarm state
    if (snoozed) and (time.monotonic() - touched) > timers['snooze_time']:
        print("snooze over")
        snoozed = False
        alarm = True
        mode = mode
        display.show(alarm_gfx[mode])
        pyportal.play_file(alarm_sounds[mode])
        print(mode)
