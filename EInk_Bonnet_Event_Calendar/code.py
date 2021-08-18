from __future__ import print_function
from datetime import datetime
import time
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import textwrap
import digitalio
import busio
import board
from PIL import Image, ImageDraw, ImageFont
from adafruit_epd.epd import Adafruit_EPD
from adafruit_epd.ssd1675 import Adafruit_SSD1675
from adafruit_epd.ssd1680 import Adafruit_SSD1680

spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
ecs = digitalio.DigitalInOut(board.CE0)
dc = digitalio.DigitalInOut(board.D22)
rst = digitalio.DigitalInOut(board.D27)
busy = digitalio.DigitalInOut(board.D17)
up_button = digitalio.DigitalInOut(board.D5)
up_button.switch_to_input()
down_button = digitalio.DigitalInOut(board.D6)
down_button.switch_to_input()

# If modifying these scopes, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# Check for new/deleted events every 10 seconds
QUERY_DELAY = 10  # Time in seconds to delay between querying the Google Calendar API
MAX_EVENTS_PER_CAL = 5
MAX_LINES = 2
DEBOUNCE_DELAY = 0.3

# Initialize the Display
display = Adafruit_SSD1680(     # Newer eInk Bonnet
# display = Adafruit_SSD1675(   # Older eInk Bonnet
    122, 250, spi, cs_pin=ecs, dc_pin=dc, sramcs_pin=None, rst_pin=rst, busy_pin=busy,
)

display.rotation = 1

# RGB Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

creds = None
# The file token.pickle stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists("token.pickle"):
    with open("token.pickle", "rb") as token:
        creds = pickle.load(token)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_console()
    # Save the credentials for the next run
    with open("token.pickle", "wb") as token:
        pickle.dump(creds, token)

service = build("calendar", "v3", credentials=creds)

current_event_id = None
last_check = None
events = []


def display_event(event_id):
    event_index = search_id(event_id)
    if event_index is None:
        if len(events) > 0:
            # Event was probably deleted while we were updating
            event_index = 0
            event = events[0]
        else:
            event = None
    else:
        event = events[event_index]

    current_time = get_current_time()
    display.fill(Adafruit_EPD.WHITE)
    image = Image.new("RGB", (display.width, display.height), color=WHITE)
    draw = ImageDraw.Draw(image)
    event_font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24
    )
    time_font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18
    )
    next_event_font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16
    )

    # Draw Time
    current_time = get_current_time()
    (font_width, font_height) = time_font.getsize(current_time)
    draw.text(
        (display.width - font_width - 2, 2), current_time, font=time_font, fill=BLACK,
    )

    if event is None:
        text = "No events found"
        (font_width, font_height) = event_font.getsize(text)
        draw.text(
            (
                display.width // 2 - font_width // 2,
                display.height // 2 - font_height // 2,
            ),
            text,
            font=event_font,
            fill=BLACK,
        )
    else:
        how_long = format_interval(
            event["start"].get("dateTime", event["start"].get("date"))
        )
        draw.text(
            (2, 2), how_long, font=time_font, fill=BLACK,
        )

        (font_width, font_height) = event_font.getsize(event["summary"])
        lines = textwrap.wrap(event["summary"], width=20)
        for line_index, line in enumerate(lines):
            if line_index < MAX_LINES:
                draw.text(
                    (2, line_index * font_height + 22),
                    line,
                    font=event_font,
                    fill=BLACK,
                )

        # Draw Next Event if there is one
        if event_index < len(events) - 1:
            next_event = events[event_index + 1]
            next_time = format_event_date(
                next_event["start"].get("dateTime", next_event["start"].get("date"))
            )
            next_item = "Then " + next_time + ": "
            (font_width, font_height) = next_event_font.getsize(next_item)
            draw.text(
                (2, display.height - font_height * 2 - 8),
                next_item,
                font=next_event_font,
                fill=BLACK,
            )
            draw.text(
                (2, display.height - font_height - 2),
                next_event["summary"],
                font=next_event_font,
                fill=BLACK,
            )

    display.image(image)
    display.display()


def format_event_date(datestr):
    event_date = datetime.fromisoformat(datestr)
    # If the same day, just return time
    if event_date.date() == datetime.now().date():
        return event_date.strftime("%I:%M %p")
    # If a future date, return date and time
    return event_date.strftime("%m/%d/%y %I:%M %p")


def format_interval(datestr):
    event_date = datetime.fromisoformat(datestr).replace(tzinfo=None)
    delta = event_date - datetime.now()
    # if < 60 minutes, return minutes
    if delta.days < 0:
        return "Now:"
    if not delta.days and delta.seconds < 3600:
        value = round(delta.seconds / 60)
        return "In {} minute{}:".format(value, "s" if value > 1 else "")
    # if < 24 hours return hours
    if not delta.days:
        value = round(delta.seconds / 3600)
        return "In {} hour{}:".format(value, "s" if value > 1 else "")
    return "In {} day{}:".format(delta.days, "s" if delta.days > 1 else "")


def search_id(event_id):
    if event_id is not None:
        for index, event in enumerate(events):
            if event["id"] == event_id:
                return index
    return None


def get_current_time():
    now = datetime.now()
    return now.strftime("%I:%M %p")


current_time = get_current_time()


def get_events(calendar_id):
    print("Fetching Events for {}".format(calendar_id))
    page_token = None
    events = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=MAX_EVENTS_PER_CAL,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return events.get("items", [])


def get_all_calendar_ids():
    page_token = None
    calendar_ids = []
    while True:
        print("Fetching Calendar IDs")
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar_list_entry in calendar_list["items"]:
            calendar_ids.append(calendar_list_entry["id"])
        page_token = calendar_list.get("nextPageToken")
        if not page_token:
            break
    return calendar_ids


while True:
    last_event_id = current_event_id
    last_time = current_time

    if last_check is None or time.monotonic() >= last_check + QUERY_DELAY:
        # Call the Calendar API
        now = datetime.utcnow().isoformat() + "Z"
        calendar_ids = get_all_calendar_ids()
        events = []
        for calendar_id in calendar_ids:
            events += get_events(calendar_id)

        # Sort Events by Start Time
        events = sorted(
            events, key=lambda k: k["start"].get("dateTime", k["start"].get("date"))
        )
        last_check = time.monotonic()

        # Update the current time
        current_time = get_current_time()

    if not events:
        current_event_id = None
        current_index = None
    else:
        if current_event_id is None:
            current_index = 0
        else:
            current_index = search_id(current_event_id)

        if current_index is not None:
            # Check for Button Presses
            if up_button.value != down_button.value:
                if not up_button.value and current_index < len(events) - 1:
                    current_index += 1
                    time.sleep(DEBOUNCE_DELAY)
                if not down_button.value and current_index > 0:
                    current_index -= 1
                    time.sleep(DEBOUNCE_DELAY)

            current_event_id = events[current_index]["id"]
        else:
            current_event_id = None
    if current_event_id != last_event_id or current_time != last_time:
        display_event(current_event_id)
