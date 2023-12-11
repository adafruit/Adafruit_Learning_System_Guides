# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import gc
import ssl
import time
import wifi
import socketpool
import adafruit_requests
import adafruit_display_text.label
import board
import terminalio
import displayio
import framebufferio
import rgbmatrix
import adafruit_json_stream as json_stream
import microcontroller
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
from adafruit_datetime import datetime, timedelta
import neopixel

displayio.release_displays()

# font color for text on matrix
font_color = 0xFFFFFF
# your timezone UTC offset and timezone name
timezone_info = [-4, "EDT"]
# the name of the sports you want to follow
sport_name = ["football", "baseball", "soccer", "hockey", "basketball"]
# the name of the corresponding leages you want to follow
sport_league = ["nfl", "mlb", "usa.1", "nhl", "nba"]
# the team names you want to follow
# must match the order of sport/league arrays
# include full name and then abbreviation (usually city/region)
team0 = ["New England Patriots", "NE"]
team1 = ["Boston Red Sox", "BOS"]
team2 = ["New England Revolution", "NE"]
team3 = ["Boston Bruins", "BOS"]
team4 = ["Boston Celtics", "BOS"]
# how often the API should be fetched
fetch_timer = 300 # seconds
# how often the display should update
display_timer = 30 # seconds

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness = 0.3, auto_write=True)

# matrix setup
base_width = 64
base_height = 32
chain_across = 2
tile_down = 2
DISPLAY_WIDTH = base_width * chain_across
DISPLAY_HEIGHT = base_height * tile_down
matrix = rgbmatrix.RGBMatrix(
    width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, bit_depth=3,
    rgb_pins=[
        board.MTX_R1,
        board.MTX_G1,
        board.MTX_B1,
        board.MTX_R2,
        board.MTX_G2,
        board.MTX_B2
    ],
    addr_pins=[
        board.MTX_ADDRA,
        board.MTX_ADDRB,
        board.MTX_ADDRC,
        board.MTX_ADDRD
    ],
    clock_pin=board.MTX_CLK,
    latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE,
    tile=tile_down, serpentine=True,
    doublebuffer=False
)
display = framebufferio.FramebufferDisplay(matrix)

# connect to WIFI
wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}")

# add API URLs
SPORT_URLS = []
for i in range(5):
    d = (
    f"https://site.api.espn.com/apis/site/v2/sports/{sport_name[i]}/{sport_league[i]}/scoreboard"
    )
    SPORT_URLS.append(d)

context = ssl.create_default_context()
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, context)

# arrays for teams, logos and display groups
teams = []
logos = []
groups = []
# add team to array
teams.append(team0)
# grab logo bitmap name
logo0 = "/team0_logos/" + team0[1] + ".bmp"
# add logo to array
logos.append(logo0)
# create a display group
group0 = displayio.Group()
# add group to array
groups.append(group0)
# repeat:
teams.append(team1)
logo1 = "/team1_logos/" + team1[1] + ".bmp"
logos.append(logo1)
group1 = displayio.Group()
groups.append(group1)
teams.append(team2)
logo2 = "/team2_logos/" + team2[1] + ".bmp"
logos.append(logo2)
group2 = displayio.Group()
groups.append(group2)
teams.append(team3)
logo3 = "/team3_logos/" + team3[1] + ".bmp"
logos.append(logo3)
group3 = displayio.Group()
groups.append(group3)
teams.append(team4)
logo4 = "/team4_logos/" + team4[1] + ".bmp"
logos.append(logo4)
group4 = displayio.Group()
groups.append(group4)

# initial startup screen
# shows the five team logos you are following
def sport_startup(logo):
    try:
        group = displayio.Group()
        bitmap0 = displayio.OnDiskBitmap(logo[0])
        grid0 = displayio.TileGrid(bitmap0, pixel_shader=bitmap0.pixel_shader, x = 0)
        bitmap1 = displayio.OnDiskBitmap(logo[1])
        grid1 = displayio.TileGrid(bitmap1, pixel_shader=bitmap1.pixel_shader, x = 32)
        bitmap2 = displayio.OnDiskBitmap(logo[2])
        grid2 = displayio.TileGrid(bitmap2, pixel_shader=bitmap2.pixel_shader, x = 64)
        bitmap3 = displayio.OnDiskBitmap(logo[3])
        grid3 = displayio.TileGrid(bitmap3, pixel_shader=bitmap3.pixel_shader, x = 96)
        bitmap4 = displayio.OnDiskBitmap(logo[4])
        grid4 = displayio.TileGrid(bitmap4, pixel_shader=bitmap4.pixel_shader, x = 48, y=32)
        group.append(grid0)
        group.append(grid1)
        group.append(grid2)
        group.append(grid3)
        group.append(grid4)
        display.root_group = group
    # pylint: disable=broad-except
    except Exception:
        print("Can't find bitmap. Did you run the get_team_logos.py script?")

# takes UTC time from JSON and reformats how its displayed
def convert_date_format(date, tz_information):
    # Manually extract year, month, day, hour, and minute from the string
    year = int(date[0:4])
    month = int(date[5:7])
    day = int(date[8:10])
    hour = int(date[11:13])
    minute = int(date[14:16])
    # Construct a datetime object using the extracted values
    dt = datetime(year, month, day, hour, minute)
    # Adjust the datetime object for the target timezone offset
    dt_adjusted = dt + timedelta(hours=tz_information[0])
    # Extract fields for output format
    month = dt_adjusted.month
    day = dt_adjusted.day
    hour = dt_adjusted.hour
    minute = dt_adjusted.minute
    # Convert 24-hour format to 12-hour format and determine AM/PM
    am_pm = "AM" if hour < 12 else "PM"
    hour_12 = hour if hour <= 12 else hour - 12
    minute = f"{minute:02}"
    # Determine the timezone abbreviation based on the offset
    time_zone_str = tz_information[1]
    return f"{month}/{day} - {hour_12}:{minute} {am_pm} {time_zone_str}"

# the actual API and display function
# pylint: disable=too-many-locals, too-many-branches, too-many-statements
def get_data(data, team, logo, group):
    pixel.fill((0, 0, 255))
    print(f"Fetching data from {data}")
    playing = False
    names = []
    scores = []
    info = []
    index = 0
    # the team you are following's logo
    bitmap0 = displayio.OnDiskBitmap(logo)
    grid0 = displayio.TileGrid(bitmap0, pixel_shader=bitmap0.pixel_shader, x = 2)
    home_text = adafruit_display_text.label.Label(terminalio.FONT, color=font_color,
                                                  text=" ")
    away_text = adafruit_display_text.label.Label(terminalio.FONT, color=font_color,
                                                  text=" ")
    vs_text = adafruit_display_text.label.Label(terminalio.FONT, color=font_color,
                                                text=" ")
    vs_text.anchor_point = (0.5, 0.0)
    vs_text.anchored_position = (DISPLAY_WIDTH / 2, 14)
    info_text = adafruit_display_text.label.Label(terminalio.FONT, color=font_color,
                                                  text=" ")
    info_text.anchor_point = (0.5, 1.0)
    info_text.anchored_position = (DISPLAY_WIDTH / 2, DISPLAY_HEIGHT)
    # make the request to the API
    resp = requests.get(data)
    # stream the json
    json_data = json_stream.load(resp.iter_content(32))
    for event in json_data["events"]:
        # clear the date and then add the date to the array
        # the date for your game will remain
        info.clear()
        info.append(event["date"])
        # check for your team playing
        if team[0] not in event["name"]:
            continue
        for competition in event["competitions"]:
            for competitor in competition["competitors"]:
                # if your team is playing:
                playing = True
                # get team names
                # index indicates home vs. away
                names.append(competitor["team"]["abbreviation"])
                # the current score
                scores.append(competitor["score"])
            # gets info on game
            info.append(event["status"]["type"]["shortDetail"])
        break
    if playing and len(names) != 2:
        print("did not get expected response, fetching full JSON..")
        try:
            resp.close()
        # pylint: disable=broad-except
        except Exception as e:
            print(f"{e}, continuing..")
            # pylint: disable=unnecessary-pass
            pass
        names.clear()
        scores.clear()
        info.clear()
        resp = requests.get(data)
        response_as_json = resp.json()
        for e in response_as_json["events"]:
            if team[0] in e["name"]:
                print(index)
                info.append(response_as_json["events"][0]["date"])
                names.append(response_as_json["events"][0]["competitions"]
                             [0]["competitors"][0]["team"]["abbreviation"])
                names.append(response_as_json["events"][0]["competitions"]
                             [0]["competitors"][1]["team"]["abbreviation"])
                scores.append(response_as_json["events"][0]["competitions"]
                             [0]["competitors"][0]["score"])
                scores.append(response_as_json["events"][0]["competitions"]
                             [0]["competitors"][1]["score"])
                info.append(response_as_json["events"][0]["status"]["type"]["shortDetail"])
            else:
                index += 1
    # debug printing
    print(names)
    print(scores)
    print(info)
    if playing and len(names) == 2:
        # pull out the date
        date = info[0]
        # convert it to be readable
        date = convert_date_format(date, timezone_info)
        print(date)
        # pull out the info
        info = info[1]
        # check if it's pre-game
        if str(info) == date or str(info) == "Scheduled":
            status = "pre"
            print("match, pre-game")
        else:
            status = info
        # home and away text
        # teams index determines which team is home or away
        home_text.text="HOME"
        away_text.text="AWAY"
        if team[1] is names[0]:
            home_game = True
            home_text.anchor_point = (0.0, 0.5)
            home_text.anchored_position = (5, 37)
            away_text.anchor_point = (1.0, 0.5)
            away_text.anchored_position = (124, 37)
            vs_team = names[1]
        else:
            home_game = False
            away_text.anchor_point = (0.0, 0.5)
            away_text.anchored_position = (5, 37)
            home_text.anchor_point = (1.0, 0.5)
            home_text.anchored_position = (124, 37)
            vs_team = names[0]
        # if it's pre-game, show "VS"
        if status == "pre":
            vs_text.text="VS"
            info_text.text=date
        # if it's active or final show score
        else:
            info_text.text=info
            if home_game:
                vs_text.text=f"{scores[0]} - {scores[1]}"
            else:
                vs_text.text=f"{scores[1]} - {scores[0]}"
        # load in logo from other team
        vs_logo = logo.replace(team[1], vs_team)
    # if there is no game matching your team:
    else:
        status = "pre"
        vs_logo = logo
        info_text.text="NO DATA AVAILABLE"
    # load in the other team's logo
    bitmap1 = displayio.OnDiskBitmap(vs_logo)
    grid1 = displayio.TileGrid(bitmap1, pixel_shader=bitmap1.pixel_shader, x = 94)
    print("done")
    # update the display group. try/except in case its the first time it's being added
    try:
        group[0] = grid0
        group[1] = grid1
        group[2] = home_text
        group[3] = away_text
        group[4] = vs_text
        group[5] = info_text
    except IndexError:
        group.append(grid0)
        group.append(grid1)
        group.append(home_text)
        group.append(away_text)
        group.append(vs_text)
        group.append(info_text)
    # close the response
    try:
        # sometimes an OSError is thrown:
        # "invalid syntax for integer with base 16"
        # the code can continue depite it though
        resp.close()
    # pylint: disable=broad-except
    except Exception as e:
        print(f"{e}, continuing..")
        # pylint: disable=unnecessary-pass
        pass
    pixel.fill((0, 0, 0))
    # return that data was just fetched
    fetch_status = True
    return fetch_status

# index and clock for fetching
fetch_index = 0
fetch_timer = fetch_timer * 1000
# index and clock for updating display
display_index = 0
display_timer = display_timer * 1000
# load logos
sport_startup(logos)
# initial data fetch
for z in range(5):
    try:
        just_fetched = get_data(SPORT_URLS[z],
                 teams[z],
                 logos[z],
                 groups[z])
        display.root_group = groups[z]
    # pylint: disable=broad-except
    except Exception as Error:
        print(Error)
        time.sleep(10)
        gc.collect()
        time.sleep(5)
        microcontroller.reset()
# start clocks
just_fetched = True
fetch_clock = ticks_ms()
display_clock = ticks_ms()

while True:
    try:
        if not just_fetched:
            # garbage collection for display groups
            gc.collect()
            # fetch the json for the next team
            just_fetched = get_data(SPORT_URLS[fetch_index],
                     teams[fetch_index],
                     logos[fetch_index],
                     groups[fetch_index])
            # advance index
            fetch_index = (fetch_index + 1) % len(teams)
            # reset clocks
            fetch_clock = ticks_add(fetch_clock, fetch_timer)
            display_clock = ticks_add(display_clock, display_timer)
        # update display seperate from API request
        if ticks_diff(ticks_ms(), display_clock) >= display_timer:
            print("updating display")
            display.root_group = groups[display_index]
            display_index = (display_index + 1) % len(teams)
            display_clock = ticks_add(display_clock, display_timer)
        # cleared for fetching after time has passed
        if ticks_diff(ticks_ms(), fetch_clock) >= fetch_timer:
            just_fetched = False
    # pylint: disable=broad-except
    except Exception as Error:
        print(Error)
        time.sleep(10)
        gc.collect()
        time.sleep(5)
        microcontroller.reset()
