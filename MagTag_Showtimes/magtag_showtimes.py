# MagTag Showtimes Event Viewer
# Uses the events.json file to display next or current event
# Be sure to put WiFi access point info in secrets.py file to connect

import time
import json
import re
from adafruit_magtag.magtag import MagTag

# You can test by setting a time.struct here, to pretend its a different day
# (tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec, tm_wday, tm_yday, tm_isdst)
FAKETIME = False  # time.struct_time(2020, 12, 11,     15, 01, 00,    4, 346, -1)

BEEP_ON_EVENTSTART = True   # beep when the event begins?
EVENT_FILE = "events.json"  # file containing events
USE_24HR_TIME = False   # True for 24-hr time on display, false for 12 hour (am/pm) time

magtag = MagTag()
magtag.add_text(
    text_font="/fonts/Arial-Bold-12.pcf",
    text_color=0xFFFFFF,
    text_position=(2, 112),
    text_anchor_point=(0, 0),
)

# According to Python, monday is index 0...this array will help us track it
day_names = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
events = None
with open(EVENT_FILE, 'r') as evfile:
    events = json.load(evfile)

# validate data
for i, event in enumerate(events):
    if not event.get('name'):
        raise RuntimeError("No name in event %d" % i)
    if not event.get('day_of_week') or event['day_of_week'] not in day_names:
        raise RuntimeError("Invalid day of week for event '%s'" % event['name'])
    r = re.compile('[0-2]?[0-9]:[0-5][0-9]')
    if not event.get('start_time') or not r.match(event['start_time']) :
        raise RuntimeError("Invalid start time for event '%s'" % event['name'])
    if not event.get('end_time') or not r.match(event['end_time']) :
        raise RuntimeError("Invalid end time for event '%s'" % event['name'])

print(events)

now = None
if not FAKETIME:
    magtag.network.connect()
    magtag.get_local_time()
    now = time.localtime()
else:
    now = FAKETIME

print("Now: ", now)

# Helper to convert times into am/pm times
def time_format(timestr):
    if USE_24HR_TIME:
        return timestr
    hr, mn = [int(x) for x in timestr.split(":")]
    if hr > 12:
        return "%d:%02d PM" % (hr-12, mn)
    elif hr > 0:
        return "%d:%02d AM" % (hr, mn)
    else:
        return "12:%02d AM" % (mn)

# find next event!
remaining_starttimes = []
remaining_endtimes = []
current_event = None
for event in events:
    days_till_event = (day_names.index(event["day_of_week"]) - now[6] + 7) % 7

    # now figure out minutes until event
    eventstart_hr, eventstart_min = event["start_time"].split(":")
    eventstart_time_in_minutes = int(eventstart_hr) * 60 + int(eventstart_min)
    # we'll also track when it ends
    eventend_hr, eventend_min = event["end_time"].split(":")
    eventend_time_in_minutes = int(eventend_hr) * 60 + int(eventend_min)

    current_time_in_minutes = now[3] * 60 + now[4]
    print(
        "\tEvent start is at",
        eventstart_time_in_minutes,
        "now is",
        current_time_in_minutes,
    )
    minutes_till_eventstart = eventstart_time_in_minutes - current_time_in_minutes
    minutes_till_eventend = eventend_time_in_minutes - current_time_in_minutes

    # add the number of days to minutes:
    minutes_till_eventstart += days_till_event * 24 * 60
    minutes_till_eventend += days_till_event * 24 * 60

    # if time is negative, that means it already happened today, so skip ahead
    if minutes_till_eventstart < 0:
        minutes_till_eventstart += 7 * 24 * 60
    if minutes_till_eventend < 0:
        minutes_till_eventend += 7 * 24 * 60

    print(
        "\t%d minutes till start, %d minutes till end"
        % (minutes_till_eventstart, minutes_till_eventend)
    )
    if (minutes_till_eventstart == 0) or (
            minutes_till_eventend < minutes_till_eventstart
    ):
        current_event = event

    # now we can back-calculate when the event is for our debugging
    days = minutes_till_eventstart // (24 * 60)
    hrs = (minutes_till_eventstart - days * (24 * 60)) // 60
    mins = minutes_till_eventstart % 60
    print(event["name"], "starts in", days, "days", hrs, "hours and", mins, "minutes\n")

    remaining_starttimes.append(minutes_till_eventstart)
    remaining_endtimes.append(minutes_till_eventend)

mins_till_next_eventstart = min(remaining_starttimes)
mins_till_next_eventend = min(remaining_endtimes)
next_up = events[remaining_starttimes.index(mins_till_next_eventstart)]

# OK find the one with the smallest minutes remaining
sleep_time = None
if current_event:
    print("Currently: ", current_event)
    magtag.set_background("bmps/"+current_event["graphic"])
    magtag.set_text("Currently streaming until " + time_format(current_event["end_time"]))
    remaining_starttimes.index(mins_till_next_eventstart)
    if BEEP_ON_EVENTSTART:
        for _ in range(3):
            magtag.peripherals.play_tone(1760, 0.1)
            time.sleep(0.2)
    sleep_time = mins_till_next_eventend + 1
else:
    print("Next up! ", next_up)
    magtag.set_background("bmps/"+next_up["graphic"])

    string = (
        "Coming up on "
        + next_up["day_of_week"]
        + " at "
        + time_format(next_up["start_time"])
    )
    magtag.set_text(string)
    sleep_time = mins_till_next_eventstart

print("Sleeping for %d minutes" % sleep_time)
time.sleep(2)
magtag.exit_and_deep_sleep(sleep_time * 60)
