import time
import math
import board
import displayio
import terminalio
from simpleio import map_range
import adafruit_imageload
from adafruit_pyportal import PyPortal
from adafruit_display_text.label import Label
from adafruit_display_shapes.line import Line

# --| User Config |---------------------------------------------------
UPDATE_RATE = 60  # minutes
MAX_STORMS = 3  # limit storms
NAME_COLOR = 0xFFFFFF  # label text color
NAME_BG_COLOR = 0x000000  # label background color
ARROW_COLOR = 0x0000FF  # movement direction arrow color
ARROW_LENGTH = 15  # movement direction arrow length
LAT_RANGE = (45, 5)  # set to match map
LON_RANGE = (-100, -40)  # set to match map
# --------------------------------------------------------------------

# setup pyportal
pyportal = PyPortal(
    url="https://www.nhc.noaa.gov/CurrentStorms.json",
    json_path=["activeStorms"],
    status_neopixel=board.NEOPIXEL,
    default_bg="/map.bmp",
)

# setup display group for storms
icons_bmp, icons_pal = adafruit_imageload.load(
    "/storm_icons.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette
)
for i, c in enumerate(icons_pal):
    if c == 0xFFFF00:
        icons_pal.make_transparent(i)
storm_icons = displayio.Group(max_size=MAX_STORMS)
pyportal.splash.append(storm_icons)
STORM_CLASS = ("TD", "TS", "HU")

# setup info label
info_update = Label(
    terminalio.FONT,
    text="1984-01-01T00:00:00.000Z",
    color=NAME_COLOR,
    background_color=NAME_BG_COLOR,
)
info_update.anchor_point = (0.0, 1.0)
info_update.anchored_position = (10, board.DISPLAY.height - 10)
pyportal.splash.append(info_update)

# these are need for lat/lon to screen x/y mapping
VIRTUAL_WIDTH = board.DISPLAY.width * 360 / (LON_RANGE[1] - LON_RANGE[0])
VIRTUAL_HEIGHT = board.DISPLAY.height * 360 / (LAT_RANGE[0] - LAT_RANGE[1])
Y_OFFSET = math.radians(LAT_RANGE[0])
Y_OFFSET = math.tan(math.pi / 4 + Y_OFFSET / 2)
Y_OFFSET = math.log(Y_OFFSET)
Y_OFFSET = (VIRTUAL_WIDTH * Y_OFFSET) / (2 * math.pi)
Y_OFFSET = VIRTUAL_HEIGHT / 2 - Y_OFFSET


def update_display():
    # clear out existing icons
    while len(storm_icons):
        _ = storm_icons.pop()

    # get latest storm data
    try:
        storm_data = pyportal.fetch()
    except RuntimeError:
        return
    print("Number of storms:", len(storm_data))

    # parse the storm data
    for storm in storm_data:
        # don't exceed max
        if len(storm_icons) >= MAX_STORMS:
            continue
        # get lat/lon
        lat = storm["latitudeNumeric"]
        lon = storm["longitudeNumeric"]
        # check if on map
        if (
            not LAT_RANGE[0] >= lat >= LAT_RANGE[1]
            or not LON_RANGE[0] <= lon <= LON_RANGE[1]
        ):
            continue
        # OK, let's make a group for all the graphics
        storm_gfx = displayio.Group(max_size=3)  # icon + label + arrow
        # convert to sreen coords
        x = int(map_range(lon, LON_RANGE[0], LON_RANGE[1], 0, board.DISPLAY.width - 1))
        y = math.radians(lat)
        y = math.tan(math.pi / 4 + y / 2)
        y = math.log(y)
        y = (VIRTUAL_WIDTH * y) / (2 * math.pi)
        y = VIRTUAL_HEIGHT / 2 - y
        y = int(y - Y_OFFSET)
        # icon type
        if storm["classification"] in STORM_CLASS:
            storm_type = STORM_CLASS.index(storm["classification"])
        else:
            storm_type = 0
        # create storm icon
        icon = displayio.TileGrid(
            icons_bmp,
            pixel_shader=icons_pal,
            width=1,
            height=1,
            tile_width=16,
            tile_height=16,
            default_tile=storm_type,
            x=x - 8,
            y=y - 8,
        )
        # add storm icon
        storm_gfx.append(icon)
        # add a label
        name = Label(
            terminalio.FONT,
            text=storm["name"],
            color=NAME_COLOR,
            background_color=NAME_BG_COLOR,
        )
        name.anchor_point = (0.0, 1.0)
        name.anchored_position = (x + 8, y - 8)
        storm_gfx.append(name)
        # add direction arrow
        angle = math.radians(storm["movementDir"])
        xd = x + int(ARROW_LENGTH * math.sin(angle))
        yd = y - int(ARROW_LENGTH * math.cos(angle))
        arrow = Line(x, y, xd, yd, color=ARROW_COLOR)
        storm_gfx.append(arrow)
        # add the storm graphics
        storm_icons.append(storm_gfx)
        # update time
        info_update.text = storm["lastUpdate"]
        # debug
        print(
            "{} @ {},{}".format(
                storm["name"], storm["latitudeNumeric"], storm["longitudeNumeric"]
            )
        )

    # no storms? at least say something
    if not len(storm_icons):
        print("No storms in map area.")
        storm_icons.append(
            Label(
                terminalio.FONT,
                scale=4,
                x=50,
                y=110,
                text="NO STORMS\n IN AREA",
                color=NAME_COLOR,
                background_color=NAME_BG_COLOR,
            )
        )


# --------------------------------------------------------------------
# M A I N
# --------------------------------------------------------------------
update_display()
last_update = time.monotonic()
while True:
    now = time.monotonic()
    if now - last_update > UPDATE_RATE * 60:
        print("Updating...")
        update_display()
        last_update = now
