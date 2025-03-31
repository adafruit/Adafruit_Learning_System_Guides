# SPDX-FileCopyrightText: 2021 Melissa LeBlanc-Williams and John Park for Adafruit Industries
# SPDX-License-Identifier: MIT

# MagTag Sports Schedule Viewer
# Be sure to add your wifi credentials to the settings.toml file

# Press D to advance to next game
# Press C to go back one game
# Press B to refresh the schedule (this takes a minute)
# Press A to advance to next sport (this takes a minute)

from os import getenv
import time
import json
from adafruit_datetime import datetime, timedelta
from adafruit_magtag.magtag import MagTag

# Get WiFi details, ensure these are setup in settings.toml
ssid = getenv("CIRCUITPY_WIFI_SSID")
password = getenv("CIRCUITPY_WIFI_PASSWORD")

if None in [ssid, password]:
    raise RuntimeError(
        "WiFi settings are kept in settings.toml, "
        "please add them there. The settings file must contain "
        "'CIRCUITPY_WIFI_SSID', 'CIRCUITPY_WIFI_PASSWORD', "
        "at a minimum."
    )

USE_24HR_TIME = False
TIME_ZONE_OFFSET = -8  # hours ahead or behind Zulu time, e.g. Pacific is -8
TIME_ZONE_NAME = "PST"

#  API info here https://www.gpwa.org/forum/espns-hidden-api-scores-stats-json-endpoints-251149.html
#  Note, these will only work when the sport is in season.

SPORTS = [
    {
        "name": "NCAA Men's Basketball",
        # pylint: disable=line-too-long
        "url": "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard",
    },
    {
        "name": "NCAA Wmn's Basketball",
        # pylint: disable=line-too-long
        "url": "http://site.api.espn.com/apis/site/v2/sports/basketball/womens-college-basketball/scoreboard",
    },
    {
        "name": "NHL Hockey",
        "url": "http://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
    },
    {
        "name": "NFL Football",
        "url": "http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
    },
    {
        "name": "MLB Baseball",
        "url": "http://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
    },
    {
        "name": "College Baseball",
        "url": "http://site.api.espn.com/apis/site/v2/sports/baseball/college-baseball/scoreboard",
    },
    {
        "name": "NBA Basketball",
        "url": "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
    },
    {
        "name": "WNBA Basketball",
        "url": "http://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard",
    },
    {
        "name": "College Football",
        "url": "http://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard",
    },
    {
        "name": "MLS Soccer",
        "url": "http://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/scoreboard",
    },
    {
        "name": "Premiere League",
        "url": "http://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
    },
    {
        "name": "Italian Serie A",
        "url": "http://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/scoreboard",
    },
    {
        "name": "German Bundesliga",
        "url": "http://site.api.espn.com/apis/site/v2/sports/soccer/ger.1/scoreboard",
    },
]


current_game = 0
#  You can cycle among different sports with the A button, or set it here:
current_sport = 0
sports_data = []

EVENTS_LOCATION = ["events"]
STATUS_LOCATION = ["status", "type", "description"]
BROADCAST_LOCATION = ["competitions", 0, "broadcasts"]
IS_FINAL_LOCATION = ["competitions", 0, "status", "type", "id"]
SCORES_LOCATION = ["competitions", 0, "competitors"]
SCORE_0_LOCATION = ["competitions", 0, "competitors", 0, "score"]
SCORE_1_LOCATION = ["competitions", 0, "competitors", 1, "score"]

months = [
    "Jan",
    "Feb",
    "March",
    "April",
    "May",
    "June",
    "July",
    "Aug",
    "Sept",
    "Oct",
    "Nov",
    "Dec",
]

# Set up the MagTag with the JSON data parameters
magtag = MagTag(
    url=SPORTS[current_sport]["url"],
)


def format_date(iso_formatted_date):
    if iso_formatted_date is None:
        return "When: Unavailable"
    date = datetime.fromisoformat(iso_formatted_date[:-1])
    date += timedelta(hours=TIME_ZONE_OFFSET)

    if USE_24HR_TIME:
        timestring = "%d:%02d %s" % (date.hour, date.minute, TIME_ZONE_NAME)
    elif date.hour > 12:
        timestring = "%d:%02d pm %s" % (
            abs((date.hour - 12) % 12),
            date.minute,
            TIME_ZONE_NAME,
        )
    else:
        timestring = "%d:%02d am %s" % (date.hour, date.minute, TIME_ZONE_NAME)

    return "%s %d, %s" % (months[date.month - 1], date.day, timestring)


def format_score(scores, is_final):
    home_score = scores[0]["score"]
    away_score = scores[1]["score"]
    if not home_score or not away_score:
        return "Unavailable"
    if int(is_final) == 3:
        return "%s - %s" % (home_score, away_score)
    return " "


def format_available(value):
    if value is None:
        return "Unavailable"
    return value


def format_broadcast(value):
    if not value:
        value = "N/A"
    else:
        value = magtag.network.json_traverse(value, [0, "names", 0])
    return "Airing on: " + value


def get_game_number():
    return "Game %d of %d" % (current_game + 1, len(sports_data))


def play_tone(frequency, color=None):
    magtag.peripherals.neopixel_disable = False
    if color:
        magtag.peripherals.neopixels.fill(color)
    magtag.peripherals.play_tone(frequency, 0.2)
    magtag.peripherals.neopixel_disable = True


def update_labels():
    # Set the labels for the current game data
    magtag.set_text(SPORTS[current_sport]["name"], 0, False)
    magtag.set_text(sports_data[current_game]["name"], 1, False)
    magtag.set_text(sports_data[current_game]["date"], 2, False)
    magtag.set_text(sports_data[current_game]["broadcast"], 3, False)
    magtag.set_text(sports_data[current_game]["status"], 4, False)
    magtag.set_text(get_game_number(), 5, False)
    magtag.set_text(sports_data[current_game]["score"], 6)
    # wait 2 seconds for display to complete
    time.sleep(2)


def fetch_sports_data(reset_game_number=True):
    # Fetches and parses data for all games for the current sport
    # pylint: disable=global-statement
    global current_game
    magtag.url = SPORTS[current_sport]["url"]
    sports_data.clear()
    raw_data = json.loads(magtag.fetch(auto_refresh=False))
    events = raw_data["events"]
    for event in events:
        game_data = {}
        game_data["name"] = format_available(event["name"])
        game_data["date"] = format_date(event["date"])
        game_data["status"] = "Game status: " + format_available(
            magtag.network.json_traverse(event, STATUS_LOCATION)
        )
        game_data["broadcast"] = format_broadcast(
            magtag.network.json_traverse(event, BROADCAST_LOCATION)
        )
        scores = magtag.network.json_traverse(event, SCORES_LOCATION)
        is_final = magtag.network.json_traverse(event, IS_FINAL_LOCATION)
        game_data["score"] = format_score(scores, is_final)
        sports_data.append(game_data)
    if reset_game_number or current_game > len(sports_data):
        current_game = 0
    update_labels()


# Sports Name
magtag.add_text(
    text_font="/fonts/Lato-Bold-ltd-25.bdf", text_position=(10, 15), is_data=False
)

# Game Name
magtag.add_text(
    text_font="/fonts/Arial-Bold-12.pcf",
    text_wrap=35,
    line_spacing=0.75,
    text_position=(10, 70),
    is_data=False,
)

# Date
magtag.add_text(text_font="/fonts/Arial-12.bdf", text_position=(10, 40), is_data=False)

# Broadcast Information
magtag.add_text(
    text_font="/fonts/Arial-Italic-12.bdf", text_position=(10, 98), is_data=False
)

# Game Status
magtag.add_text(
    text_font="/fonts/Arial-Italic-12.bdf", text_position=(10, 116), is_data=False
)

# Game Number
magtag.add_text(
    text_font="/fonts/Arial-Italic-12.bdf", text_position=(190, 38), is_data=False
)

# Score
magtag.add_text(
    text_font="/fonts/Arial-Bold-24.bdf", text_position=(170, 94), is_data=False
)

fetch_sports_data()

while True:
    if magtag.peripherals.button_a_pressed:  # switch to next sport
        play_tone(620, 0x000033)
        current_sport += 1
        if current_sport >= len(SPORTS):
            current_sport = 0
        fetch_sports_data()
    elif magtag.peripherals.button_b_pressed:  # re-fetch data
        play_tone(220, 0x330000)
        fetch_sports_data(False)
    elif magtag.peripherals.button_c_pressed:  # display previous game
        play_tone(350, 0x330000)
        current_game -= 1
        if current_game < 0:
            current_game = len(sports_data) - 1
        update_labels()
    elif magtag.peripherals.button_d_pressed:  # display next game
        play_tone(440, 0x003300)
        current_game += 1
        if current_game >= len(sports_data):
            current_game = 0
        update_labels()

    time.sleep(0.01)
