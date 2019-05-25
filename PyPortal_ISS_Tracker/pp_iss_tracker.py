import time
import math
import board
import displayio
from terminalio import FONT
from adafruit_pyportal import PyPortal
from adafruit_display_shapes.circle import Circle
from adafruit_display_text.label import Label

#--| USER CONFIG |--------------------------
MARK_SIZE = 10           # marker radius
MARK_COLOR = 0xFF3030    # marker color
MARK_THICKNESS = 5       # marker thickness
TRAIL_LENGTH = 200       # trail length
TRAIL_COLOR = 0xFFFF00   # trail color
DATE_COLOR = 0x111111    # date color
TIME_COLOR = 0x111111    # time color
LAT_MAX = 80             # latitude (deg) of map top/bottom edge
UPDATE_RATE = 10         # update rate in seconds
#-------------------------------------------

DATA_SOURCE = "http://api.open-notify.org/iss-now.json"
DATA_LOCATION = ["iss_position"]

WIDTH = board.DISPLAY.width
HEIGHT = board.DISPLAY.height

# determine the current working directory needed so we know where to find files
cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = PyPortal(url=DATA_SOURCE,
                    json_path=DATA_LOCATION,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/map.bmp")

# Connect to the internet and get local time
pyportal.get_local_time()

# Date and time label
date_label = Label(FONT, text="0000-00-00", color=DATE_COLOR, x=165, y=223)
time_label = Label(FONT, text="00:00:00", color=TIME_COLOR, x=240, y=223)
pyportal.splash.append(date_label)
pyportal.splash.append(time_label)

# ISS trail
trail_bitmap = displayio.Bitmap(3, 3, 1)
trail_palette = displayio.Palette(1)
trail_palette[0] = TRAIL_COLOR
trail = displayio.Group(max_size=TRAIL_LENGTH)
pyportal.splash.append(trail)

# ISS location marker
marker = displayio.Group(max_size=MARK_THICKNESS)
for r in range(MARK_SIZE - MARK_THICKNESS, MARK_SIZE):
    marker.append(Circle(0, 0, r, outline=MARK_COLOR))
pyportal.splash.append(marker)

def get_location(width=WIDTH, height=HEIGHT):
    """Fetch current lat/lon, convert to (x, y) tuple scaled to width/height."""

    # Get location
    try:
        location = pyportal.fetch()
    except RuntimeError:
        return None, None

    # Compute (x, y) coordinates
    lat = float(location["latitude"])   # degrees, -90 to 90
    lon = float(location["longitude"])  # degrees, -180 to 180

    # Scale latitude for cropped map
    lat *= 90 / LAT_MAX

    # Mercator projection math
    # https://stackoverflow.com/a/14457180
    # https://en.wikipedia.org/wiki/Mercator_projection#Alternative_expressions
    x = lon + 180
    x = width * x / 360

    y = math.radians(lat)
    y = math.tan(math.pi / 4 + y / 2)
    y = math.log(y)
    y = (width * y) / (2 * math.pi)
    y = height / 2 - y

    return int(x), int(y)

def update_display(current_time, update_iss=False):
    """Update the display with current info."""

    # ISS location
    if update_iss:
        x, y = get_location()
        if x and y:
            marker.x = x
            marker.y = y
            if len(trail) >= TRAIL_LENGTH:
                trail.pop(0)
            trail.append(displayio.TileGrid(trail_bitmap,
                                            pixel_shader=trail_palette,
                                            x = x - 1,
                                            y = y - 1) )


    # Date and time
    date_label.text = "{:04}-{:02}-{:02}".format(current_time.tm_year,
                                                 current_time.tm_mon,
                                                 current_time.tm_mday)
    time_label.text = "{:02}:{:02}:{:02}".format(current_time.tm_hour,
                                                 current_time.tm_min,
                                                 current_time.tm_sec)

    board.DISPLAY.refresh_soon()

# Initial refresh
update_display(time.localtime(), True)
last_update = time.monotonic()

# Run forever
while True:
    now = time.monotonic()
    new_position = False
    if now - last_update > UPDATE_RATE:
        new_position = True
        last_update = now
    update_display(time.localtime(), new_position)
    time.sleep(0.5)
