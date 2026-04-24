# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
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
import microcontroller
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
from adafruit_datetime import datetime, timedelta
import neopixel

displayio.release_displays()

# font color for text on matrix
font_color = 0xFFFFFF
# your timezone UTC offset and timezone name
timezone_info = [-4, "EDT"]
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
    width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, bit_depth=4,
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
SPORT_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

context = ssl.create_default_context()
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, context)

# arrays for games and display groups
# the length and entries for both will vary depending on API response
games = []
groups = []

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

def get_data(data, dictionary):
    dictionary.clear()
    pixel.fill((0, 0, 255))
    print(f"Fetching data from {data}")
    # make the request to the API
    resp = requests.get(data)
    # json
    json_data = resp.json()
    for i in range(len(json_data["events"])):
        match_name = json_data["events"][i]["shortName"]
        print(match_name)
        date = json_data["events"][i]["date"]
        date = convert_date_format(date, timezone_info)
        home_team = match_name[0:3]
        away_team = match_name[6:9]
        score_home = json_data["events"][i]["competitions"][0]["competitors"][0]["score"]
        score_away = json_data["events"][i]["competitions"][0]["competitors"][1]["score"]
        clock = json_data["events"][i]["status"]["displayClock"]
        location = json_data["events"][i]["competitions"][0]["venue"]["address"]["city"]
        status = json_data["events"][i]["status"]["type"]["shortDetail"]
        dictionary.append({"home": home_team, "away": away_team, "score_home": score_home,
                           "score_away": score_away, "date": date, "clock": clock, "status": status,
                           "location": location})
    # debug printing
    # print(dictionary)
    got_data = True
    return dictionary, got_data

def make_gfx(dictionary, grps): # pylint: disable=too-many-locals
    grps.clear()
    for i in range(len(dictionary)):
        # check if it's pre-game
        if dictionary[i]["status"] == "Scheduled":
            status = "pre"
            print("match, pre-game")
        else:
            status = dictionary[i]["status"]
        # make a display group
        grp = displayio.Group()
        # load in logos
        logo0 = "/team_logos/" + dictionary[i]["home"] + ".bmp"
        bitmap0 = displayio.OnDiskBitmap(logo0)
        grid0 = displayio.TileGrid(bitmap0, pixel_shader=bitmap0.pixel_shader, x = 2)
        grp.append(grid0) # index 0
        logo1 = "/team_logos/" + dictionary[i]["away"] + ".bmp"
        bitmap1 = displayio.OnDiskBitmap(logo1)
        grid1 = displayio.TileGrid(bitmap1, pixel_shader=bitmap1.pixel_shader, x = 94)
        grp.append(grid1) # index 1
        home_text = adafruit_display_text.label.Label(terminalio.FONT, color=font_color,
                                                  text=" ")
        home_text.text=dictionary[i]["home"]
        home_text.anchor_point = (0.0, 0.5)
        home_text.anchored_position = (10, 32)
        grp.append(home_text) # index 2
        away_text = adafruit_display_text.label.Label(terminalio.FONT, color=font_color,
                                                      text=" ")
        away_text.text=dictionary[i]["away"]
        away_text.anchor_point = (1.0, 0.5)
        away_text.anchored_position = (120, 32)
        grp.append(away_text) # index 3
        vs_text = adafruit_display_text.label.Label(terminalio.FONT, color=font_color,
                                                    text=" ")
        vs_text.anchor_point = (0.5, 0.0)
        vs_text.anchored_position = (DISPLAY_WIDTH / 2, 14)
        grp.append(vs_text) # index 4
        info_text = adafruit_display_text.label.Label(terminalio.FONT, color=font_color,
                                                    text=" ")
        info_text.anchor_point = (0.5, 1.0)
        info_text.anchored_position = (DISPLAY_WIDTH / 2, DISPLAY_HEIGHT)
        grp.append(info_text) # index 5
        location_text = adafruit_display_text.label.Label(terminalio.FONT, color=font_color,
                                                    text=f"{dictionary[i]['location']}")
        location_text.anchor_point = (0.5, 1.0)
        location_text.anchored_position = (DISPLAY_WIDTH / 2, DISPLAY_HEIGHT - 12)
        grp.append(location_text) # index 6
        if status == "pre":
            vs_text.text="VS"
            info_text.text=dictionary[i]["date"]
        # if it's active or final show score
        else:
            info_text.text=f"Clock: {dictionary[i]['clock']}"
            vs_text.text=f"{dictionary[i]['score_home']} - {dictionary[i]['score_away']}"
        grps.append(grp)
    return grps

# clock for fetching
fetch_timer = fetch_timer * 1000
# index and clock for updating display
display_index = 0
display_timer = display_timer * 1000

# initial data fetch
try:
    games, just_fetched = get_data(SPORT_URL, games)
    groups = make_gfx(games, groups)
    display.root_group = groups[display_index]
# pylint: disable=broad-except
except Exception as Error:
    print(f"Error: {Error}")
    time.sleep(10)
    gc.collect()
    time.sleep(5)
    microcontroller.reset()
# start clocks
fetch_clock = ticks_ms()
display_clock = ticks_ms()

while True:
    try:
        if not just_fetched:
            # garbage collection for display groups
            gc.collect()
            # fetch the json for the next team
            games, just_fetched = get_data(SPORT_URL, games)
            groups = make_gfx(games, groups)
            # reset clocks
            fetch_clock = ticks_add(fetch_clock, fetch_timer)
            display_clock = ticks_add(display_clock, display_timer)
        # update display seperate from API request
        if ticks_diff(ticks_ms(), display_clock) >= display_timer:
            print("updating display")
            display.root_group = groups[display_index]
            display_index = (display_index + 1) % len(games)
            info_clock = ticks_ms()
            display_clock = ticks_add(display_clock, display_timer)
        # cleared for fetching after time has passed
        if ticks_diff(ticks_ms(), fetch_clock) >= fetch_timer:
            just_fetched = False
    # pylint: disable=broad-except
    except Exception as Error:
        print(f"Error: {Error}")
        time.sleep(10)
        gc.collect()
        time.sleep(5)
        microcontroller.reset()
