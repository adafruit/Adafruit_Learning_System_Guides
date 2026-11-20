# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Home dashboard code for the Metro ESP32-P4
"""

import json
import os
import time
import board
import displayio
import framebufferio
import mipidsi
import rtc
import wifi
import adafruit_connection_manager
import adafruit_requests
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_HTTP, IO_MQTT
from adafruit_io.adafruit_io_errors import AdafruitIO_MQTTError, AdafruitIO_RequestError
import adafruit_ili9881
import adafruit_gt911
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_displayio_layout.layouts.grid_layout import GridLayout
from adafruit_displayio_layout.layouts.page_layout import PageLayout
from tiles import (WHITE, GREY, GREEN, RED, BLUE, TILE_COLOR, SMALL, MEDIUM,
                   text, circle, gradient, format_time, Gauge, TempTile, LightTile,
                   PhotoTile, WeatherTile, ForecastTile, ConditionTile, HistoryTile,
                   ClockTile, LiveTile)

# display
displayio.release_displays()
i2c = board.I2C()
bus = mipidsi.Bus(
    minimum_frequency=adafruit_ili9881.RaspberryPiTouchDisplay2.MINIMUM_BUS_FREQUENCY,
    num_lanes=2,
)
panel = adafruit_ili9881.RaspberryPiTouchDisplay2(bus, i2c)
display = framebufferio.FramebufferDisplay(panel, rotation=90)
ts = adafruit_gt911.GT911(i2c, rotation=90)
W, H = display.width, display.height

# Settings
CONFIG_FILE = "/config.json"
TAB_BG, TAB_ACTIVE = TILE_COLOR, 0x636366
MARGIN = 30        # outer edge spacing
PAD = 10           # half the gap between tiles
HEADER_H = 120     # space above the page content
TAB_W, TAB_H = 114, 60
HEADER_BOX_W = 190  # width of the title and clock boxes (fits "Grow Room")
SWIPE_MIN = 150    # horizontal travel (px) that counts as a swipe
NET_TIMEOUT = 0.1  # max time each MQTT check may block, in seconds
CLOCK_EVERY = 60 * 60    # seconds between clock syncs
WEATHER_EVERY = 15 * 60  # seconds between weather updates
HISTORY_EVERY = 15 * 60  # seconds between updates of the 24-hour graphs
TIME_URL = ("https://io.adafruit.com/api/v2/{}/integrations/time/strftime"
            "?fmt=%25s+%25z")
# Parts of the Adafruit IO weather report that are used -> hours from now
WEATHER_HOURS = {"current": 0, "forecast_hours_6": 6, "forecast_hours_12": 12}
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

with open(CONFIG_FILE) as config_file:
    config = json.load(config_file)
TABS = [tab["name"] for tab in config["tabs"]]

def parse_color(color):
    """A color from config.json: a palette name like "color1", or hex like "#30D158"
    or "0x30D158"."""
    color = config.get("colors", {}).get(color, color)
    return int(color.lstrip("#"), 16)

def parse_bands(bands):
    """Gauge bands from config.json: the name of an entry in its "bands" section, or
    a list of [upper limit, status, color], where a null limit means "anything higher".
    No bands at all gives a plain blue gauge."""
    if isinstance(bands, str):
        bands = config["bands"][bands]
    return [(float("inf") if limit is None else limit, status, parse_color(color))
            for limit, status, color in bands] or [(float("inf"), "", BLUE)]

# header: title + date box (left), clock box (right)
background = gradient(W, H, *[parse_color(color) for color in config["background"]])
title_box = RoundRect(MARGIN, 10, HEADER_BOX_W, 100, 28, fill=TILE_COLOR)
clock_box = RoundRect(W - MARGIN - HEADER_BOX_W, 10, HEADER_BOX_W, 100, 28, fill=TILE_COLOR)
title_label = text("Home", MEDIUM, WHITE, (0, 0), (MARGIN + 20, 23))
date_label = text("--", SMALL, GREY, (0, 0), (MARGIN + 20, 75))
status_dot = circle(7, MARGIN + HEADER_BOX_W - 24, 86, RED)  # green when MQTT is connected
clock = text("--:--", MEDIUM, WHITE, (0.5, 0.5), (W - MARGIN - HEADER_BOX_W // 2, 60))

# tab bar (centered) with a highlight pill
def make_tab_bar():
    """The row of tab names, and the pill that highlights the open tab."""
    tab_row = displayio.Group(x=(W - TAB_W * len(TABS)) // 2, y=30)
    tab_row.append(RoundRect(0, 0, TAB_W * len(TABS), TAB_H, TAB_H // 2, fill=TAB_BG))
    pill = RoundRect(4, 4, TAB_W - 8, TAB_H - 8, (TAB_H - 8) // 2, fill=TAB_ACTIVE)
    tab_row.append(pill)
    for index, name in enumerate(TABS):
        tab_row.append(text(name, SMALL, WHITE, (0.5, 0.5),
                            (index * TAB_W + TAB_W // 2, TAB_H // 2)))
    return tab_row, pill

tab_bar, highlight = make_tab_bar()

# pages, built from config.json
listeners = {}   # feed key
all_tiles = []   # every tile on every page

def listen(feed, receiver):
    if feed not in listeners:
        listeners[feed] = []
    listeners[feed].append(receiver)

TITLE_ONLY_TILES = {"photo": PhotoTile, "conditions": ConditionTile, "clock": ClockTile}

def make_tile(spec, tab_name):
    """Make one tile from its entry in config.json. tab_name is the tab it's on."""
    kind, title = spec["type"], spec.get("title", "")
    if kind in TITLE_ONLY_TILES:
        tile = TITLE_ONLY_TILES[kind](title)
    elif kind == "gauge":
        tile = Gauge(title, spec["min"], spec["max"], spec.get("format", "{:.0f}"),
                     parse_bands(spec.get("bands", [])))
    elif kind == "temperature":
        tile = TempTile(title, parse_bands(spec.get("bands", [])))
    elif kind == "light":
        tile = LightTile(title, spec["feed"])
    elif kind == "weather":
        tile = WeatherTile(title, spec.get("readings", []))
    elif kind == "forecast":
        tile = ForecastTile(title, max(WEATHER_HOURS.values()))
    elif kind == "history":
        tile = HistoryTile(title, [(line["label"], line["feed"], parse_color(line["color"]),
                                    line.get("format", "{:.0f}")) for line in spec["series"]])
    elif kind == "live":
        tile = LiveTile(title, i2c)
    else:
        raise ValueError(f"Unknown tile type in {CONFIG_FILE}: {kind}")
    for reading in getattr(tile, "readings", ()):
        listen(reading.feed, reading)
    if "feed" in spec:
        listen(spec["feed"], tile)
    tile.tab = tab_name
    all_tiles.append(tile)
    return tile

def make_pages():
    """A page for each tab in config.json. Returns the PageLayout, and the GridLayout
    of each tab that has tiles (used to find which tile was tapped)."""
    layout = PageLayout(x=0, y=HEADER_H)
    tab_grids = {}
    for tab in config["tabs"]:
        name = tab["name"]
        if tab.get("tiles"):
            columns, rows = tab.get("grid", (4, 2))
            page = GridLayout(x=MARGIN - PAD, y=0, width=W - 2 * (MARGIN - PAD),
                              height=H - HEADER_H - (MARGIN - PAD),
                              grid_size=(columns, rows), cell_padding=PAD)
            for spec in tab["tiles"]:
                page.add_content(make_tile(spec, name), grid_position=tuple(spec["at"]),
                                 cell_size=tuple(spec.get("size", (1, 1))))
            tab_grids[name] = page
        else:
            page = displayio.Group()
            page.append(text(name + " page", MEDIUM, WHITE, (0.5, 0.5),
                             (W // 2, (H - HEADER_H) // 2)))
        layout.add_content(page, name)
    return layout, tab_grids

pages, grids = make_pages()
weather_tiles = [tile for tile in all_tiles if hasattr(tile, "show_weather")]
history_tiles = [tile for tile in all_tiles if isinstance(tile, HistoryTile)]
clock_tiles = [tile for tile in all_tiles if isinstance(tile, ClockTile)]
light_tiles = [tile for tile in all_tiles if isinstance(tile, LightTile)]
live_tiles = [tile for tile in all_tiles if isinstance(tile, LiveTile)]

root = displayio.Group()
for item in (background, title_box, clock_box, title_label, date_label, status_dot, clock,
             tab_bar, pages):
    root.append(item)
display.root_group = root

def deliver(feed, value):
    """Show a new value from a feed on every tile that displays it."""
    for receiver in listeners.get(feed, ()):
        receiver.receive(value)

# AIO
def connected(client):
    print("Connected to Adafruit IO")
    for feed in listeners:
        client.subscribe(feed)
        client.get(feed)

def message(_client, feed_id, payload):
    print("Feed:", feed_id, "=", payload[:60])
    deliver(feed_id, payload)

pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
aio_user, aio_key = os.getenv("ADAFRUIT_AIO_USERNAME"), os.getenv("ADAFRUIT_AIO_KEY")
requests = adafruit_requests.Session(pool, ssl_context)
io_http = IO_HTTP(aio_user, aio_key, requests)
io = IO_MQTT(MQTT.MQTT(broker="io.adafruit.com", username=aio_user, password=aio_key,
                       socket_pool=pool, ssl_context=ssl_context,
                       socket_timeout=NET_TIMEOUT))
io.on_connect = connected
io.on_message = message
# Errors from the network itself (Wi-Fi, sockets, Adafruit IO). These are printed
# and retried; any other error stops the program with a traceback.
NETWORK_ERRORS = (OSError, MQTT.MMQTTException, adafruit_requests.OutOfRetries,
                  AdafruitIO_MQTTError, AdafruitIO_RequestError)

clock_sync = {"utc_offset": None}  # seconds from UTC to local time, after the first sync

def sync_clock():
    """Set the board's clock to local time. Also keep the offset from UTC, since
    the weather gives sunrise and sunset in UTC."""
    url = TIME_URL.format(aio_user)
    if os.getenv("TIMEZONE"):  # otherwise Adafruit IO goes by the IP address
        url += "&tz=" + os.getenv("TIMEZONE")
    with requests.get(url, headers={"X-AIO-Key": aio_key}) as response:
        unix_time, offset = response.text.split()
    sign = -1 if offset[0] == "-" else 1
    clock_sync["utc_offset"] = sign * (int(offset[1:3]) * 3600 + int(offset[3:5]) * 60)
    rtc.RTC().datetime = time.localtime(int(unix_time) + clock_sync["utc_offset"])
    update_clock(time.localtime())
    print("Clock synced from Adafruit IO, UTC offset", offset)

def utc_to_local(stamp):
    """A UTC time like "2026-11-06T11:24:11Z" as local time (a struct_time)."""
    utc = time.mktime((int(stamp[0:4]), int(stamp[5:7]), int(stamp[8:10]),
                       int(stamp[11:13]), int(stamp[14:16]), int(stamp[17:19]), 0, -1, -1))
    return time.localtime(utc + clock_sync["utc_offset"])

def spaced(code):
    """Put spaces in a WeatherKit condition code: "MostlyCloudy" -> "Mostly Cloudy"."""
    words = ""
    for letter in code:
        words += " " + letter if letter.isupper() and words else letter
    return words

def fahrenheit(celsius):
    return celsius * 9 / 5 + 32

def load_weather():
    """One request returns the current conditions and every forecast."""
    report = io_http.receive_weather(os.getenv("ADAFRUIT_AIO_WEATHER_ID"))
    weather = {"temp": fahrenheit(report["current"]["temperature"]),
               "condition": spaced(report["current"]["conditionCode"]),
               "forecast": {hours: fahrenheit(report[kind]["temperature"])
                            for kind, hours in WEATHER_HOURS.items() if hours}}
    if clock_sync["utc_offset"] is not None:
        day = report["forecast_days_1"]
        weather["sunrise"] = format_time(utc_to_local(day["sunrise"]))
        weather["sunset"] = format_time(utc_to_local(day["sunset"]))
    for tile in weather_tiles:
        tile.show_weather(weather)
    print("Weather updated")

def load_history():
    """The last 24 hours of each history tile's feeds, as 30-minute averages, from
    Adafruit IO's chart API. Points are spaced evenly across the graph."""
    for tile in history_tiles:
        for i, feed in enumerate(tile.feeds):
            url = (f"https://io.adafruit.com/api/v2/{aio_user}/feeds/{feed}"
                   "/data/chart?hours=24&resolution=30")
            with requests.get(url, headers={"X-AIO-Key": aio_key}) as response:
                rows = response.json()["data"]  # [[time, value], ...], oldest first
            tile.set_series(i, [float(value) for _, value in rows if value is not None])
    print("History updated")

# HTTP requests made on a timer, in this order: [name, function, seconds apart, next run].
# Weather and history are only fetched if config.json has tiles that show them.
SCHEDULE = [["Clock sync", sync_clock, CLOCK_EVERY, 0]]
if weather_tiles:
    SCHEDULE.append(["Weather", load_weather, WEATHER_EVERY, 0])
if history_tiles:
    SCHEDULE.append(["History", load_history, HISTORY_EVERY, 0])

def run_schedule():
    for task in SCHEDULE:
        name, function, every, due = task
        if time.monotonic() >= due:
            task[3] = time.monotonic() + 60  # if this attempt fails, retry in a minute
            try:
                function()
                task[3] = time.monotonic() + every
            except NETWORK_ERRORS as e:
                print(name, "failed:", e)

def publish(feed, value):
    try:
        io.publish(feed, value)
        print("Sent:", feed, "=", value)
    except NETWORK_ERRORS as e:
        print("Publish failed:", e)

def light_changed(feed, color):
    """A light tile was used: sync any other tiles for that light, then send it."""
    deliver(feed, color)
    publish(feed, color)

for light in light_tiles:
    light.on_change = light_changed

# touch interface interractions
def show_tab(index):
    index = max(0, min(index, len(TABS) - 1))
    pages.show_page(page_name=TABS[index])
    for tile in live_tiles:  # only run live video while it's on screen
        if tile.tab == TABS[index]:
            grid = grids[tile.tab]
            tile.start(root, pages.x + grid.x + tile.x, pages.y + grid.y + tile.y)
        else:
            tile.stop(root)
    highlight.x = index * TAB_W + 4
    title_label.text = TABS[index]
    print("Tab:", TABS[index])

def tile_at(point):
    """The tile under a screen point (x, y), as (tile, its top left corner on
    the screen), or None."""
    grid = grids.get(TABS[pages.showing_page_index])
    if grid is None:
        return None
    for tile in grid:
        tile_x, tile_y = pages.x + grid.x + tile.x, pages.y + grid.y + tile.y
        if tile_x <= point[0] < tile_x + tile.width and tile_y <= point[1] < tile_y + tile.height:
            return tile, (tile_x, tile_y)
    return None

def relative(point, corner):
    """A screen point, relative to a tile's top left corner."""
    return (point[0] - corner[0], point[1] - corner[1])

def on_release(start, end, held, dragging):
    """Called when the finger lifts: finish a drag, or decide between swipe and tap."""
    if dragging:
        tile, corner = held
        tile.release(relative(end, corner))
        return

    dx, dy = end[0] - start[0], end[1] - start[1]
    current = TABS[pages.showing_page_index]

    if abs(dx) > SWIPE_MIN and abs(dx) > abs(dy):
        show_tab(TABS.index(current) + (1 if dx < 0 else -1))
        return

    x, y = start
    print("Touch:", start)
    tab_x = x - tab_bar.x
    if 0 <= tab_x < TAB_W * len(TABS) and tab_bar.y <= y < tab_bar.y + TAB_H:
        show_tab(tab_x // TAB_W)
    elif held:
        tile, corner = held
        tile.release(relative(start, corner))

def update_clock(now):
    clock.text = format_time(now)
    for tile in clock_tiles:
        tile.set_time(now)
    date_label.text = f"{DAYS[now.tm_wday]}, {MONTHS[now.tm_mon - 1]} {now.tm_mday}"

show_tab(0)
touch_start = touch_last = touched = None
drag_active = False
shown_minute = None
next_network = 0

while True:
    # Touch
    points = ts.touch
    if points:
        touch_last = (points[0]["x"], points[0]["y"])
        if touch_start is None:  # finger just touched down
            touch_start = touch_last
            touched = tile_at(touch_start)
            drag_active = touched is not None and touched[0].press(
                relative(touch_start, touched[1]))
        if drag_active:
            touched[0].drag(relative(touch_last, touched[1]))
    elif touch_start is not None:  # finger just lifted
        on_release(touch_start, touch_last, touched, drag_active)
        touch_start = None

    # Network: checked once per second so touch stays responsive
    if time.monotonic() >= next_network:
        next_network = time.monotonic() + 1
        try:
            if not wifi.radio.connected:
                print("Connecting to Wi-Fi...")
                wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"),
                                   os.getenv("CIRCUITPY_WIFI_PASSWORD"))
            run_schedule()  # clock, then weather, when each is due
            if not io.is_connected:  # then the live feeds
                print("Connecting to Adafruit IO...")
                io.connect()
            io.loop(timeout=NET_TIMEOUT)
        except NETWORK_ERRORS as error:
            print("Network error:", error)
            next_network = time.monotonic() + 30  # wait before retrying
        status_dot.pixel_shader[0] = GREEN if io.is_connected else RED

    # Clock: redraw when the minute changes, once the clock has been synced
    local_time = time.localtime()
    if local_time.tm_year > 2020 and local_time.tm_min != shown_minute:
        shown_minute = local_time.tm_min
        update_clock(local_time)
