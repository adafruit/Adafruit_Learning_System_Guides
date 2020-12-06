import time
import alarm
import terminalio
import displayio
import adafruit_imageload
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
from adafruit_magtag.magtag import MagTag

# --| USER CONFIG |--------------------------
STATION_ID = (
    "9447130"  # tide location, find yours here: https://tidesandcurrents.noaa.gov/
)
METRIC = False  # set to True for metric units
VSCALE = 2  # pixels per ft or m
DAILY_UPDATE_HOUR = 3  # 24 hour format
# -------------------------------------------

# don't change these
PLOT_WIDTH = 116
PLOT_HEIGHT = 116
PLOT_X = 174
PLOT_Y = 6
PLOT_Y_SCALE = round(PLOT_HEIGHT / (4 * VSCALE))
DATE_FONT = bitmap_font.load_font("/Kanit-Black-24.bdf")
TIME_FONT = bitmap_font.load_font("/Kanit-Medium-20.bdf")

# our MagTag
magtag = MagTag()
magtag.json_path = ["predictions"]

# ----------------------------
# Grid overlay for plot
# ----------------------------
grid_bmp, grid_pal = adafruit_imageload.load("/tides_bg_land.bmp")
grid_pal.make_transparent(1)
grid_overlay = displayio.TileGrid(grid_bmp, pixel_shader=grid_pal)

# ----------------------------
# Tide plot (bitmap, palette, tilegrid)
# ----------------------------
tide_plot = displayio.Bitmap(PLOT_WIDTH, PLOT_HEIGHT, 4)

tide_pal = displayio.Palette(4)
tide_pal[0] = 0x000000  # black
tide_pal[1] = 0x555555  # dark gray
tide_pal[2] = 0xAAAAAA  # light gray
tide_pal[3] = 0xFFFFFF  # white
tide_pal.make_transparent(3)

tide_tg = displayio.TileGrid(tide_plot, pixel_shader=tide_pal, x=PLOT_X, y=PLOT_Y)

# ----------------------------
# Plot scale labels
# ----------------------------
plot_y_pos = label.Label(terminalio.FONT, text="+99", color=0x000000)
plot_y_pos.text = "{:>3}".format(PLOT_Y_SCALE)
plot_y_pos.anchor_point = (1.0, 0.5)
plot_y_pos.anchored_position = (178, 34)

plot_y_neg = label.Label(terminalio.FONT, text="-99", color=0x000000)
plot_y_neg.text = "{:>3}".format(-1 * PLOT_Y_SCALE)
plot_y_neg.anchor_point = (1.0, 0.5)
plot_y_neg.anchored_position = (178, 92)

plot_y_labels = displayio.Group(max_size=2)
plot_y_labels.append(plot_y_pos)
plot_y_labels.append(plot_y_neg)

# ----------------------------
# Date label
# ----------------------------
date_label = displayio.Group(max_size=5)
date_text = [label.Label(DATE_FONT, text="A", color=0xFFFFFF) for _ in range(5)]
y_offset = 8
for text in date_text:
    date_label.append(text)
    text.anchor_point = (0.5, 0)
    text.anchored_position = (20, y_offset)
    y_offset += 23

# ----------------------------
# HiLo Times and Icons
# ----------------------------
tide_info = displayio.Group(max_size=8)

hilo_times = [label.Label(TIME_FONT, text="12:34 P", color=0x000000) for _ in range(4)]
y_offset = 18
for hilo in hilo_times:
    tide_info.append(hilo)
    hilo.hidden = True
    hilo.anchor_point = (1, 0.5)
    hilo.anchored_position = (158, y_offset)
    y_offset += 28

icon_bmp, icon_pal = adafruit_imageload.load("/tides_icons.bmp")
icon_pal.make_transparent(1)
hilo_icons = [
    displayio.TileGrid(
        icon_bmp,
        pixel_shader=icon_pal,
        width=1,
        height=1,
        tile_width=24,
        tile_height=24,
    )
    for _ in range(4)
]
y_offset = 6
for icon in hilo_icons:
    tide_info.append(icon)
    icon.hidden = True
    icon.x = 46
    icon.y = y_offset
    y_offset += 28

# ----------------------------
# Station ID
# ----------------------------
station_info = label.Label(
    terminalio.FONT, text="STATION ID: " + STATION_ID, color=0x000000
)
station_info.anchor_point = (1, 1)
station_info.anchored_position = (158, 126)

# ----------------------------
# Add all the graphic layers
# ----------------------------
magtag.splash.append(tide_tg)
magtag.splash.append(grid_overlay)
magtag.splash.append(plot_y_labels)
magtag.splash.append(tide_info)
magtag.splash.append(date_label)
magtag.splash.append(station_info)

# /////////////////////////////////////////////////////////////////////////


def get_data_source_url(station=STATION_ID, metric=METRIC, hilo_only=True):
    """Build and return the URL for the tides API."""
    date = "{}{:02}{:02}".format(now.tm_year, now.tm_mon, now.tm_mday)

    URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?format=json"
    URL += "&product=predictions"
    URL += "&interval=hilo" if hilo_only else ""
    URL += "&datum=mllw"  # MLLW = "tides"
    URL += "&units=metric" if metric else "&units=english"
    URL += "&time_zone=lst_ldt" if now.tm_isdst == 1 else "&time_zone=lst"
    URL += "&begin_date=" + date
    URL += "&end_date=" + date
    URL += "&station=" + station

    return URL


def get_tide_data():
    """Fetch JSON tide data and return parsed results in a list."""
    # Get raw JSON data
    magtag.url = get_data_source_url(hilo_only=False)
    raw_data = magtag.fetch()

    # Results will be stored in a list that is PLOT_WIDTH long
    new_tide_data = [PLOT_HEIGHT] * PLOT_WIDTH

    # Convert raw data to display coordinates
    for data in raw_data:
        _, t = data["t"].split(" ")  # date and time
        h, m = t.split(":")  # hours and minutes
        v = data["v"]  # water level
        x = round((PLOT_WIDTH - 1) * (60 * float(h) + float(m)) / 1434)
        y = (PLOT_HEIGHT // 2) - round(VSCALE * float(v))
        y = 0 if y < 0 else y
        y = PLOT_HEIGHT - 1 if y >= PLOT_HEIGHT else y
        new_tide_data[x] = y

    return new_tide_data


def get_hilo_data():
    """Get high / low times."""
    # Get raw JSON data
    magtag.url = get_data_source_url(hilo_only=True)

    return magtag.fetch()


def show_today():
    """Display month and day."""
    month_text = (
        "JAN",
        "FEB",
        "MAR",
        "APR",
        "MAY",
        "JUN",
        "JUL",
        "AUG",
        "SEP",
        "OCT",
        "NOV",
        "DEC",
    )[now.tm_mon - 1]
    day_text = "{:2}".format(now.tm_mday)

    date_label[0].text = month_text[0]
    date_label[1].text = month_text[1]
    date_label[2].text = month_text[2]
    date_label[3].text = day_text[0]
    date_label[4].text = day_text[1]


def plot_tides():
    """Graphical plot of water level."""
    tide_plot.fill(3)
    for x in range(PLOT_WIDTH):
        y = tide_data[x]
        for yfill in range(y, PLOT_HEIGHT):
            try:
                tide_plot[x, yfill] = 2
            except IndexError:
                pass
        tide_plot[x, y] = 0


def show_hilo():
    """Show high / low times."""
    for i in hilo_icons:
        i.hidden = True
    for t in hilo_times:
        t.hidden = True
    for i, data in enumerate(hilo_data):
        # make it visible
        hilo_icons[i].hidden = False
        # icon
        hilo_icons[i][0] = 0 if data["type"] == "H" else 1
        # time
        h, m = data["t"].split(" ")[1].split(":")
        m = int(m)
        h = int(h)
        ampm = "A" if h < 12 else "P"
        h = h if h < 13 else h - 12
        hilo_times[i].text = "{:>2}:{:02} {}".format(h, m, ampm)


def time_to_sleep():
    """Compute amount of time to sleep."""
    # daily event time
    event_time = time.struct_time(
        (now[0], now[1], now[2], DAILY_UPDATE_HOUR, 0, 0, -1, -1, now[8])
    )
    # how long is that from now?
    remaining = time.mktime(event_time) - time.mktime(now)
    # is that today or tomorrow?
    if remaining < 0:  # ah its aready happened today...
        remaining += 24 * 60 * 60  # wrap around to the next day
    # return it
    return remaining

# ===========
#  M A I N
# ===========
while True:
    # get current time
    magtag.get_local_time()
    now = time.localtime()

    # show today's date
    show_today()

    # get and plot tide levels
    tide_data = get_tide_data()
    plot_tides()

    # get and show hilo tide times
    hilo_data = get_hilo_data()
    show_hilo()

    # refresh display
    time.sleep(magtag.display.time_to_refresh + 1)
    magtag.display.refresh()
    time.sleep(magtag.display.time_to_refresh + 1)

    # ZZZZZZzzzzzzzzz
    now = time.localtime()
    magtag.exit_and_deep_sleep(time_to_sleep())

