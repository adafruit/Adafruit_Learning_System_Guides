# Be sure to put WiFi access point info in secrets.py file to connect

import time
from adafruit_magtag.magtag import MagTag

FAKETIME = None  # time.struct_time(2020, 12, 9,     20, 01, 00,    2, 344, -1)
# (tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec, tm_wday, tm_yday, tm_isdst)

BEEP_ON_EVENTSTART = True

magtag = MagTag()
magtag.add_text(
    text_font="/fonts/Arial-Bold-12.pcf",
    text_color=0xFFFFFF,
    text_position=(10, 112),
    text_anchor_point=(0, 0),
)

# According to Python, monday is index 0...this array will help us track it
day_names = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
fullday_names = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

events = []
events.append(
    {
        "name": "JP's Product Pick of the Week",
        "day_of_week": day_names.index("Tue"),
        "graphic": "/bmps/jpp.bmp",
        "start_time": "13:00",  # 4:00 pm local time
        "end_time": "13:30",
    }
)
events.append(
    {
        "name": "3D Hangouts",
        "day_of_week": day_names.index("Wed"),
        "graphic": "/bmps/3dh.bmp",
        "start_time": "8:00",  # 11:00 am local time
        "end_time": "9:00",
    }
)
events.append(
    {
        "name": "Show & Tell",
        "day_of_week": day_names.index("Wed"),
        "graphic": "/bmps/snt.bmp",
        "start_time": "16:30",  # 7:30 pm local time
        "end_time": "17:00",
    }
)
events.append(
    {
        "name": "Ask An Engineer",
        "day_of_week": day_names.index("Wed"),
        "graphic": "/bmps/aae.bmp",
        "start_time": "17:00",  # 8:00 pm local time
        "end_time": "18:00",
    }
)
events.append(
    {
        "name": "John Park's Workshop",
        "day_of_week": day_names.index("Thu"),
        "graphic": "/bmps/jpw.bmp",
        "start_time": "13:00",  # 4:00 pm local time
        "end_time": "14:00",
    }
)
events.append(
    {
        "name": "Scott's Deep Dive",
        "day_of_week": day_names.index("Fri"),
        "graphic": "/bmps/dds.bmp",
        "start_time": "14:00",  # 5:00 pm local time
        "end_time": "15:00",
    }
)
print(events)
now = None
if not FAKETIME:
    magtag.network.connect()
    magtag.get_local_time()
    now = time.localtime()
else:
    now = FAKETIME

print("Now: ", now)

# find next event!
remaining_starttimes = []
remaining_endtimes = []
current_event = None
for event in events:
    days_till_event = (event["day_of_week"] - now[6] + 7) % 7

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
    magtag.set_background(current_event["graphic"])
    magtag.set_text("Currently streaming until " + current_event["end_time"])
    remaining_starttimes.index(mins_till_next_eventstart)
    if BEEP_ON_EVENTSTART:
        for _ in range(3):
            magtag.peripherals.play_tone(1760, 0.1)
            time.sleep(0.2)
    sleep_time = mins_till_next_eventend + 1
else:
    print("Next up! ", next_up)
    magtag.set_background(next_up["graphic"])

    string = (
        "Coming up on "
        + day_names[next_up["day_of_week"]]
        + " at "
        + next_up["start_time"]
    )
    magtag.set_text(string)
    sleep_time = mins_till_next_eventstart

print("Sleeping for %d minutes" % sleep_time)
time.sleep(2)
magtag.exit_and_deep_sleep(sleep_time * 60)
