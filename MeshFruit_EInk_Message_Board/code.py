# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Meshtastic e-ink message board.

Listens for LongFast broadcast text messages on the default channel and
renders the most recent ones to a 4.2 inch tri-color e-ink panel. Messages
are shown complete rather than truncated: the layout fills from the newest
message down until it runs out of vertical space, so a few long messages
crowd out older ones. The newest message is drawn in red.

A button on A0 cycles between views. Switching does not reboot, so
the message buffer survives a view change.

Receive only. This board does not transmit and will not appear in the
mesh node list.
"""

import math
import time
import board
import digitalio
import os
import microcontroller
import alarm
import displayio
import terminalio
import vectorio
import adafruit_ssd1683
import adafruit_rfm9x
from fourwire import FourWire
from adafruit_display_text import label, wrap_text_to_pixels
from adafruit_meshfruit import meshtastic as meshfruit

try:
    from adafruit_bitmap_font import bitmap_font
except ImportError:
    bitmap_font = None

FREQUENCY = 906.875
CHANNEL_HASH = 0x08
SYNC_WORD_REG = 0x39
MESHTASTIC_SYNC_WORD = 0x2B

WIDTH = 400
HEIGHT = 300
MARGIN = 10
TEXT_WIDTH = WIDTH - MARGIN * 2

# Colour carries recency: the newest message is red, older ones black.
# Size carries fit: a long newest message drops to the medium face so
# it does not crowd everything else off the panel.
# All three faces are from the public domain Misc-Fixed family.
# Weight carries recency (bold = newest), size carries fit.
FONT_PATHS = {
    "large_bold": "/fonts/9x18B.pcf",
    "medium_bold": "/fonts/7x14B.pcf",
    "medium": "/fonts/7x14.pcf",
    "name": "/fonts/6x13B.pcf",
    "small": "/fonts/6x10.pcf",
}
MAX_LARGE_LINES = 2

HEADER_BASELINE = 16
RULE_Y = 30
CONTENT_TOP = 52
# The node rows are single lines, so they need their own breathing
# room under the header rule.
NODES_TOP = 64

# Weather view splits the panel: forecast on top, newest messages
# underneath.
WEATHER_SPLIT_Y = 168
WEATHER_MSG_TOP = 182
WEATHER_MSG_LIMIT = 2

# Sun and moon column on the right of the current conditions row.
SKY_ICON_X = WIDTH - 100
SKY_TEXT_X = SKY_ICON_X + 18
SUN_ROW_Y = 6
MOON_ROW_Y = 62

# Open-Meteo is free and needs no API key. Coordinates come from
# settings.toml so the guide does not hardcode a location.
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=%s&longitude=%s"
    "&current=temperature_2m,weather_code"
    "&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset"
    "&temperature_unit=%s&timezone=auto&forecast_days=3"
)
WEATHER_INTERVAL = 1800  # seconds between fetches

# Open-Meteo wants coordinates, so a ZIP is resolved once per boot
# through Zippopotam, which is also free and keyless.
ZIP_URL = "https://api.zippopotam.us/us/%s"
CONTENT_BOTTOM = 262
STATUS_RULE_Y = 272
MESSAGE_GAP = 14
FOOTER_GAP = 4
FOOTER_TEXT_OFFSET = 9

BLACK = 0x000000
RED = 0xFF0000
WHITE = 0xFFFFFF

MAX_MESSAGES = 12
SEEN_HISTORY = 20
REFRESH_SECONDS = 20

# Power saving. Measured baseline before these: ~4.7%/hour on a
# 2000mAh cell, about 21 hours, dominated by the CPU spinning at
# full clock rather than by the radio.
CPU_FREQUENCY = 80_000_000
LOW_POWER = True
# The RFM95 DIO0 line, wired to A5. It goes high when a packet lands,
# which is what lets the board sleep without going deaf.
RADIO_IRQ_PIN = board.A5
# Short enough that the button and the refresh cooldown still get
# checked several times a second.
SLEEP_SECONDS = 0.3

BUTTON_PIN = board.A0
DEBOUNCE_SECONDS = 0.25
# A short press cycles the two main views; holding jumps straight to
# the node list, which is a lookup rather than something to page past.
LONG_PRESS_SECONDS = 1.0
CYCLE_VIEWS = ("weather", "messages")
HOLD_VIEW = "nodes"

# NeoPixel vocabulary. The panel is silent for the whole refresh and
# cannot redraw more than once every 180 seconds, so the pixel carries
# the fast feedback the display cannot.
BLINK_SECONDS = 0.35
PIXEL_PRESS = (0, 0, 60)      # blue   - button registered
PIXEL_MESSAGE = (0, 50, 0)    # green  - new message decoded
PIXEL_QUEUED = (60, 25, 0)    # amber  - change queued behind cooldown
PIXEL_SOON = (50, 40, 0)      # yellow - refresh due shortly
PIXEL_DRAWING = (40, 0, 40)   # purple - panel updating now
REFRESH_SOON_SECONDS = 10
VIEWS = ("weather", "messages", "nodes")
# Titles stay short: the air readings are centred on the same line,
# and a long title runs straight into them.
VIEW_TITLES = {
    "messages": "MeshFruit",
    "nodes": "Nodes",
    "weather": "Weather",
}

# Readings are pulled once per panel refresh. The display cannot
# update more than once every 180 seconds, so polling faster would
# only burn power.
USE_FAHRENHEIT = True
AIR_READ_ATTEMPTS = 3
AIR_READ_RETRY_SECONDS = 1.0
AIR_SETTLE_SECONDS = 1.0

# Below this percent-per-hour the gauge's rate is noise, so no
# runtime estimate is shown.
BATTERY_RATE_FLOOR = 0.5

# Bring the STEMMA sensor up before anything else touches hardware.
# board.STEMMA_I2C() claims and manages I2C_POWER itself, and if
# another peripheral gets there first the bus comes up with no pull
# ups, which surfaces as a wiring error rather than a power one.
def open_air_sensor():
    """Bring up the STCC4 on the STEMMA QT port."""
    try:
        import adafruit_stcc4  # pylint: disable=import-outside-toplevel
    except ImportError as import_error:
        print("air sensor library missing:", import_error)
        return None

    try:
        i2c = board.STEMMA_I2C()
        found = adafruit_stcc4.STCC4(i2c)
        # Continuous rather than single shot. Single shot returns
        # "measurement not ready" and then I/O errors on this part;
        # continuous is the pattern proven on the Data Dispenser
        # build with the same sensor.
        found.continuous_measurement = True
        # The sensor needs a moment before its first conversion.
        time.sleep(AIR_SETTLE_SECONDS)
        # Prove it reads here, before the display, radio and pixel
        # come up. If this works and later reads do not, something
        # in the rest of the setup is disturbing the bus.
        try:
            print("air sensor up:", found.CO2, "ppm")
        except (RuntimeError, OSError) as first_error:
            print("air sensor up but first read failed:", first_error)
        return found
    except (ValueError, RuntimeError, OSError) as sensor_error:
        print("air sensor unavailable:", sensor_error)
        return None


sensor = open_air_sensor()


def open_battery():
    """Open the onboard MAX17048 fuel gauge."""
    try:
        import adafruit_max1704x  # pylint: disable=import-outside-toplevel

        gauge = adafruit_max1704x.MAX17048(board.STEMMA_I2C())
        print("battery gauge up")
        return gauge
    except (ImportError, ValueError, RuntimeError, OSError) as gauge_error:
        print("battery gauge unavailable:", gauge_error)
        return None


battery = open_battery()

air = None
charge = None
weather = None
weather_fetched = 0.0
location = None


def restart_air():
    """Put the sensor back into continuous measurement."""
    if sensor is None:
        return
    try:
        sensor.continuous_measurement = True
        time.sleep(AIR_SETTLE_SECONDS)
    except (RuntimeError, OSError) as restart_error:
        print("air restart failed:", restart_error)


def format_hours(hours):
    """Render a duration compactly: 45m, 6h, 2d."""
    if hours < 1:
        return "%dm" % max(round(hours * 60), 1)
    if hours < 48:
        return "%dh" % round(hours)
    return "%dd" % round(hours / 24)


# Condensed WMO weather codes. Full table at open-meteo.com/en/docs
WMO_CODES = {
    0: "Clear",
    1: "Mostly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Showers",
    81: "Showers",
    82: "Heavy showers",
    85: "Snow showers",
    86: "Snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm",
    99: "Severe storm",
}


def describe_code(code):
    """Human readable form of a WMO weather code."""
    return WMO_CODES.get(code, "Code %s" % code)


def clock_time(stamp):
    """Turn an ISO timestamp into a short 12 hour clock time."""
    try:
        hour = int(stamp[11:13])
        minute = stamp[14:16]
    except (ValueError, IndexError, TypeError):
        return None
    suffix = "a" if hour < 12 else "p"
    hour = hour % 12 or 12
    return "%d:%s%s" % (hour, minute, suffix)


def resolve_location(session):
    """Return (latitude, longitude) as strings, or None.

    Explicit coordinates win. Otherwise a ZIP is looked up once and
    cached for the rest of the session.
    """
    global location  # pylint: disable=global-statement
    if location is not None:
        return location

    latitude = os.getenv("LATITUDE")
    longitude = os.getenv("LONGITUDE")
    if latitude and longitude:
        location = (latitude, longitude)
        return location

    zip_code = os.getenv("ZIP_CODE")
    if not zip_code:
        print("weather: set ZIP_CODE or LATITUDE/LONGITUDE in settings.toml")
        return None

    try:
        response = session.get(ZIP_URL % zip_code, timeout=20)
        data = response.json()
        response.close()
        place = data["places"][0]
        location = (place["latitude"], place["longitude"])
        print("weather: %s resolved to %s" % (zip_code, place["place name"]))
        return location
    except Exception as zip_error:  # pylint: disable=broad-except
        print("zip lookup failed:", zip_error)
        return None


def fetch_weather():
    """Pull a short forecast from Open-Meteo. Returns a dict or None.

    WiFi is brought up only for the fetch and shut down afterwards:
    the ESP32-S3 radio sits close to the LoRa front end, and there is
    no reason to keep it running between updates.
    """
    ssid = os.getenv("CIRCUITPY_WIFI_SSID")
    password = os.getenv("CIRCUITPY_WIFI_PASSWORD")
    if not ssid:
        print("weather: no wifi credentials in settings.toml")
        return None

    try:
        import wifi  # pylint: disable=import-outside-toplevel
        import socketpool  # pylint: disable=import-outside-toplevel
        import ssl  # pylint: disable=import-outside-toplevel
        import adafruit_requests  # pylint: disable=import-outside-toplevel

        wifi.radio.enabled = True
        if not wifi.radio.connected:
            wifi.radio.connect(ssid, password)
        session = adafruit_requests.Session(
            socketpool.SocketPool(wifi.radio), ssl.create_default_context()
        )

        coords = resolve_location(session)
        if coords is None:
            return None

        url = WEATHER_URL % (
            coords[0],
            coords[1],
            "fahrenheit" if USE_FAHRENHEIT else "celsius",
        )
        response = session.get(url, timeout=20)
        data = response.json()
        response.close()
    except Exception as weather_error:  # pylint: disable=broad-except
        print("weather fetch failed:", weather_error)
        return None
    finally:
        try:
            wifi.radio.enabled = False
        except Exception:  # pylint: disable=broad-except
            pass

    try:
        current = data["current"]
        daily = data["daily"]
        return {
            "now": round(current["temperature_2m"]),
            "code": current["weather_code"],
            "highs": [round(v) for v in daily["temperature_2m_max"]],
            "lows": [round(v) for v in daily["temperature_2m_min"]],
            "codes": daily["weather_code"],
            "sunrise": clock_time(daily["sunrise"][0]),
            "sunset": clock_time(daily["sunset"][0]),
            "date": current.get("time") or daily["sunrise"][0],
        }
    except (KeyError, TypeError, IndexError) as parse_error:
        print("weather parse failed:", parse_error)
        return None


def refresh_weather():
    """Fetch if the cached forecast is stale."""
    global weather, weather_fetched  # pylint: disable=global-statement
    now = time.monotonic()
    if weather is not None and now - weather_fetched < WEATHER_INTERVAL:
        return
    fetched = fetch_weather()
    if fetched is not None:
        weather = fetched
        weather_fetched = now


def read_battery():
    """Charge state and estimated time remaining.

    charge_rate is percent per hour, signed. Dividing the remaining
    capacity by it gives a runtime estimate, which matters more than
    a percentage on a board meant to outlast a power cut.
    """
    if battery is None:
        return None
    try:
        percent = min(max(battery.cell_percent, 0), 100)
        rate = battery.charge_rate
    except (RuntimeError, OSError) as gauge_error:
        print("battery read failed:", gauge_error)
        return None

    label_text = "%d%%" % round(percent)

    # Below about half a percent per hour the estimate is noise.
    if rate > BATTERY_RATE_FLOOR:
        return "%s +%s" % (
            label_text,
            format_hours((100.0 - percent) / rate),
        )
    if rate < -BATTERY_RATE_FLOOR:
        return "%s %s" % (
            label_text,
            format_hours(percent / abs(rate)),
        )
    return label_text


def read_air():
    """Read the sensor. Returns a display string, or None.

    Occasional I2C errors are normal here, so retry a couple of times
    before giving up on this refresh cycle.
    """
    if sensor is None:
        return None

    for attempt in range(AIR_READ_ATTEMPTS):
        try:
            # Read CO2 first. The driver fetches the whole
            # measurement on this property, so asking for
            # temperature first reports "measurement not ready".
            co2 = sensor.CO2
            humidity = sensor.relative_humidity
            celsius = sensor.temperature
            degrees = celsius * 9 / 5 + 32 if USE_FAHRENHEIT else celsius
            unit = "F" if USE_FAHRENHEIT else "C"
            return "%d ppm   %d%s   %d%%" % (
                co2,
                round(degrees),
                unit,
                round(humidity),
            )
        except (RuntimeError, OSError) as sensor_error:
            if attempt == AIR_READ_ATTEMPTS - 1:
                print("air read failed:", sensor_error)
                return None
            # A power blip drops the sensor back to idle, where it
            # never produces a measurement and every read reports
            # "not ready". Put it back into continuous mode and
            # give it a conversion to catch up.
            restart_air()
            time.sleep(AIR_READ_RETRY_SECONDS)
    return None


# Nothing here is compute bound, so run the CPU slower.
try:
    microcontroller.cpu.frequency = CPU_FREQUENCY
    print("cpu at", microcontroller.cpu.frequency // 1_000_000, "MHz")
except (AttributeError, ValueError, RuntimeError) as clock_error:
    print("cpu frequency unchanged:", clock_error)

displayio.release_displays()

# Park the Feather Friend's SRAM and SD chip selects so they do not
# drive the shared SPI bus while the radio is talking.
for pin in (board.D6, board.D5):
    parked = digitalio.DigitalInOut(pin)
    parked.direction = digitalio.Direction.OUTPUT
    parked.value = True

spi = board.SPI()

# The eInk Feather Friend does not bring RST or BUSY out to D8 and
# D7, so leave both as None. Claiming those pins corrupts the I2C
# bus on this board and knocks the STEMMA sensor offline.
display_bus = FourWire(
    spi, command=board.D10, chip_select=board.D9, reset=None, baudrate=1000000
)
time.sleep(1)
display = adafruit_ssd1683.SSD1683(
    display_bus, width=WIDTH, height=HEIGHT, highlight_color=RED, busy_pin=None
)

rfm9x = adafruit_rfm9x.RFM9x(
    spi,
    digitalio.DigitalInOut(board.D11),
    digitalio.DigitalInOut(board.D12),
    FREQUENCY,
)
rfm9x.signal_bandwidth = 250000
rfm9x.spreading_factor = 11
rfm9x.coding_rate = 5
rfm9x.preamble_length = 16
rfm9x.enable_crc = True
rfm9x._write_u8(  # pylint: disable=protected-access
    SYNC_WORD_REG, MESHTASTIC_SYNC_WORD
)

# Do not claim NEOPIXEL_POWER or I2C_POWER here. On this board
# board.STEMMA_I2C() already manages the accessory rail, and
# driving it again knocks the STEMMA sensor off the bus.

try:
    import neopixel

    pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2, auto_write=True)
except (ImportError, ValueError, AttributeError) as error:
    print("neopixel unavailable:", error)
    pixel = None


def blink(color, seconds=BLINK_SECONDS):
    """Flash the pixel to signal something the panel cannot show yet."""
    if pixel is None:
        return
    pixel[0] = color
    time.sleep(seconds)
    pixel[0] = (0, 0, 0)


def pixel_hold(color):
    """Hold the pixel on for the duration of a slow operation."""
    if pixel is not None:
        pixel[0] = color


button = digitalio.DigitalInOut(BUTTON_PIN)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP


def load_font(path):
    """Load a bitmap font, or return None if it is unavailable."""
    if bitmap_font is None:
        return None
    try:
        return bitmap_font.load_font(path)
    except (OSError, ValueError) as error:
        print("font", path, "unavailable:", error)
        return None


FONTS = {name: load_font(path) for name, path in FONT_PATHS.items()}

# Fall back to the built-in face so the board still runs with no font
# files installed. terminalio.FONT has no bold or intermediate size, so
# the fallback leans on scale alone.
FALLBACK = {
    "large_bold": (terminalio.FONT, 2, 26),
    "medium_bold": (terminalio.FONT, 1, 14),
    "medium": (terminalio.FONT, 1, 14),
    "name": (terminalio.FONT, 1, 14),
    "small": (terminalio.FONT, 1, 12),
}

if not all(FONTS.values()):
    print("bitmap fonts not found, falling back to terminalio")


def face(size):
    """Return (font, scale, line_height) for a named face."""
    font = FONTS.get(size)
    if font is not None:
        return font, 1, font.get_bounding_box()[1] + 4
    return FALLBACK.get(size, FALLBACK["medium"])


def wrap_for(text, size):
    """Wrap text to the panel width for a named size."""
    font, scale, line_height = face(size)
    lines = wrap_text_to_pixels(text, TEXT_WIDTH // scale, font)
    return lines, font, scale, line_height


def size_for(index, text):
    """Pick a face for a message at this position in the list.

    The newest message is always bold and red. It uses the large face
    unless it runs long, in which case it steps down to the medium
    bold face so it does not crowd older messages off the panel.
    """
    if index != 0:
        return "medium"
    lines, _, _, _ = wrap_for(text, "large_bold")
    if len(lines) > MAX_LARGE_LINES:
        return "medium_bold"
    return "large_bold"


messages = []
seen = []
last_rssi = None
node_names = {}

# Learned short names are cached in NVM so they survive a reboot.
# Without this the board shows raw node IDs until every node happens
# to rebroadcast, which defaults to once every three hours.
NAMES_MAGIC = b"MF1"
NAMES_MAX = 24
NAME_LEN = 4
ENTRY_LEN = 4 + NAME_LEN
node_stats = {}
view_index = 0

rule_palette = displayio.Palette(1)
rule_palette[0] = BLACK

black_palette = displayio.Palette(1)
black_palette[0] = BLACK

red_palette = displayio.Palette(1)
red_palette[0] = RED

white_palette = displayio.Palette(1)
white_palette[0] = WHITE


def add_rule(group, y_pos, thickness=2):
    """Draw a horizontal rule across the content width."""
    bitmap = displayio.Bitmap(WIDTH - MARGIN * 2, thickness, 1)
    group.append(
        displayio.TileGrid(bitmap, pixel_shader=rule_palette, x=MARGIN, y=y_pos)
    )


def message_height(lines, line_height, meta_height):
    """Vertical space one message block needs, in pixels."""
    return meta_height + len(lines) * line_height + MESSAGE_GAP


def load_names():
    """Restore cached short names from NVM."""
    store = getattr(microcontroller, "nvm", None)
    if not store:
        print("nvm unavailable, names will not persist")
        return
    try:
        blob = bytes(store[: 4 + NAMES_MAX * ENTRY_LEN])
    except (RuntimeError, OSError) as nvm_error:
        print("nvm read failed:", nvm_error)
        return
    if blob[:3] != NAMES_MAGIC:
        return
    count = min(blob[3], NAMES_MAX)
    for index in range(count):
        start = 4 + index * ENTRY_LEN
        number = int.from_bytes(blob[start : start + 4], "little")
        raw = blob[start + 4 : start + ENTRY_LEN]
        short = raw.rstrip(b"\x00")
        if not short:
            continue
        try:
            node_names["!%08x" % number] = short.decode("utf-8")
        except UnicodeError:
            continue
    print("restored", len(node_names), "node names")


def save_names():
    """Persist known short names to NVM.

    Only called when a name actually changes, since NVM sits in flash
    and has a finite write endurance.
    """
    store = getattr(microcontroller, "nvm", None)
    if not store:
        return
    items = list(node_names.items())[:NAMES_MAX]
    blob = bytearray(NAMES_MAGIC + bytes([len(items)]))
    for node, short in items:
        try:
            number = int(node[1:], 16)
        except ValueError:
            continue
        blob += number.to_bytes(4, "little")
        # CircuitPython's bytes has no ljust, so pad by hand.
        raw = short.encode("utf-8")[:NAME_LEN]
        blob += raw + b"\x00" * (NAME_LEN - len(raw))
    try:
        store[0 : len(blob)] = blob
    except (RuntimeError, OSError, ValueError) as nvm_error:
        print("nvm write failed:", nvm_error)


def display_name(node):
    """Short name for a node if NodeInfo has been heard, else its ID."""
    return node_names.get(node, node)


def draw_header(group):
    """Panel title for the current view, plus the rule under it."""
    group.append(
        label.Label(
            terminalio.FONT,
            text=VIEW_TITLES[VIEWS[view_index]],
            color=BLACK,
            scale=2,
            x=MARGIN,
            y=HEADER_BASELINE,
        )
    )
    if air:
        air_font, air_scale, _ = face("name")
        group.append(
            label.Label(
                air_font,
                text=air,
                color=BLACK,
                scale=air_scale,
                anchor_point=(0.5, 0.5),
                anchored_position=(WIDTH // 2, HEADER_BASELINE),
            )
        )

    if charge:
        charge_font, charge_scale, _ = face("name")
        group.append(
            label.Label(
                charge_font,
                text=charge,
                color=BLACK,
                scale=charge_scale,
                anchor_point=(1.0, 0.5),
                anchored_position=(WIDTH - MARGIN, HEADER_BASELINE),
            )
        )

    add_rule(group, RULE_Y)


def draw_empty(group, text, y_pos=None):
    """Placeholder for a view with nothing to show yet."""
    group.append(
        label.Label(
            terminalio.FONT,
            text=text,
            color=BLACK,
            scale=2,
            x=MARGIN,
            y=CONTENT_TOP + 10 if y_pos is None else y_pos,
        )
    )


def draw_messages(group, top=CONTENT_TOP, bottom=CONTENT_BOTTOM, limit=None):
    """Message list. Returns the number of messages shown."""
    if not messages:
        draw_empty(group, "Listening for messages...", y_pos=top + 10)
        return 0

    y_pos = top
    shown = 0

    for index, (node, text) in enumerate(messages):
        if limit is not None and shown >= limit:
            break
        size = size_for(index, text)
        lines, font, scale, line_height = wrap_for(text, size)
        meta_font, meta_scale, meta_height = face("name")
        needed = message_height(lines, line_height, meta_height)

        # Always show the newest message even if it runs long, but never
        # start a later block that cannot fit.
        if shown > 0 and y_pos + needed > bottom:
            break

        color = RED if index == 0 else BLACK
        group.append(
            label.Label(
                meta_font, text=display_name(node), color=color, scale=meta_scale,
                x=MARGIN, y=y_pos
            )
        )

        line_y = y_pos + meta_height + 8
        for line in lines:
            if line_y > bottom:
                break
            group.append(
                label.Label(
                    font, text=line, color=color, scale=scale, x=MARGIN, y=line_y
                )
            )
            line_y += line_height

        y_pos += needed
        shown += 1

    return shown


def draw_nodes(group):
    """Node list view: who has been heard, how strongly, how often."""
    if not node_stats:
        draw_empty(group, "No nodes heard yet...")
        return 0

    name_font, name_scale, name_height = face("name")
    small_font, small_scale, small_height = face("small")

    # Strongest signal first, so the nearest neighbours lead.
    nodes = sorted(node_stats.items(), key=lambda item: -item[1]["rssi"])

    y_pos = NODES_TOP
    shown = 0
    for node, stats in nodes:
        name = display_name(node)
        has_name = name != node
        block = name_height + (small_height if has_name else 0) + 12
        if y_pos + block > CONTENT_BOTTOM:
            break

        color = RED if shown == 0 else BLACK
        group.append(
            label.Label(
                name_font, text=name, color=color,
                scale=name_scale, x=MARGIN, y=y_pos
            )
        )
        detail = "%d dBm  %d pkt" % (stats["rssi"], stats["count"])
        group.append(
            label.Label(
                small_font, text=detail, color=color, scale=small_scale,
                anchor_point=(1.0, 0.5),
                anchored_position=(WIDTH - MARGIN, y_pos),
            )
        )

        # Only worth a second line once NodeInfo has given us a name;
        # otherwise it would just repeat the ID above it.
        if has_name:
            group.append(
                label.Label(
                    small_font, text=node, color=color, scale=small_scale,
                    x=MARGIN, y=y_pos + name_height
                )
            )

        y_pos += block
        shown += 1

    return shown


def icon_cloud(group, cx, cy, palette=None):
    """Three lobes over a slab, which reads as a cloud at this size."""
    shader = palette or black_palette
    group.append(vectorio.Circle(pixel_shader=shader, radius=9, x=cx - 8, y=cy))
    group.append(vectorio.Circle(pixel_shader=shader, radius=12, x=cx + 4, y=cy - 3))
    group.append(vectorio.Circle(pixel_shader=shader, radius=8, x=cx + 16, y=cy + 1))
    group.append(
        vectorio.Rectangle(
            pixel_shader=shader, width=32, height=10, x=cx - 10, y=cy
        )
    )


def icon_sun(group, cx, cy, radius=13, palette=None):
    """Filled disc with four spokes."""
    shader = palette or black_palette
    group.append(vectorio.Circle(pixel_shader=shader, radius=radius, x=cx, y=cy))
    reach = radius + 7
    for dx, dy, wide, high in (
        (-1, -reach, 3, 6),
        (-1, reach - 5, 3, 6),
        (-reach, -1, 6, 3),
        (reach - 5, -1, 6, 3),
    ):
        group.append(
            vectorio.Rectangle(
                pixel_shader=shader, width=wide, height=high,
                x=cx + dx, y=cy + dy,
            )
        )


def icon_drops(group, cx, cy, palette=None, count=3):
    """Short slanted strokes under a cloud."""
    shader = palette or black_palette
    for index in range(count):
        left = cx - 10 + index * 12
        group.append(
            vectorio.Polygon(
                pixel_shader=shader,
                points=[(0, 0), (4, 0), (0, 9), (-4, 9)],
                x=left,
                y=cy,
            )
        )


def icon_bolt(group, cx, cy):
    """Lightning, in red so severe weather carries the accent colour."""
    group.append(
        vectorio.Polygon(
            pixel_shader=red_palette,
            points=[(8, 0), (0, 12), (5, 12), (-2, 24), (12, 9), (6, 9), (13, 0)],
            x=cx - 4,
            y=cy,
        )
    )


def draw_weather_icon(group, code, cx, cy, color=BLACK):
    """Pick an icon for a WMO weather code."""
    shader = red_palette if color == RED else black_palette

    if code == 0:
        icon_sun(group, cx, cy + 6, palette=shader)
    elif code in (1, 2):
        icon_sun(group, cx - 8, cy - 4, radius=9, palette=shader)
        icon_cloud(group, cx + 2, cy + 8, palette=shader)
    elif code == 3:
        icon_cloud(group, cx - 4, cy + 4, palette=shader)
    elif code in (45, 48):
        for row in range(3):
            group.append(
                vectorio.Rectangle(
                    pixel_shader=shader,
                    width=40 - row * 6,
                    height=5,
                    x=cx - 18 + row * 3,
                    y=cy - 6 + row * 12,
                )
            )
    elif code in (71, 73, 75, 77, 85, 86):
        icon_cloud(group, cx - 4, cy - 4, palette=shader)
        for index in range(3):
            group.append(
                vectorio.Circle(
                    pixel_shader=shader,
                    radius=3,
                    x=cx - 12 + index * 12,
                    y=cy + 20,
                )
            )
    elif code in (95, 96, 99):
        icon_cloud(group, cx - 4, cy - 6, palette=shader)
        icon_bolt(group, cx, cy + 8)
    else:
        # every drizzle, rain and shower code
        icon_cloud(group, cx - 4, cy - 6, palette=shader)
        icon_drops(group, cx, cy + 10, palette=shader)


MOON_NAMES = (
    "New moon",
    "Waxing crescent",
    "First quarter",
    "Waxing gibbous",
    "Full moon",
    "Waning gibbous",
    "Last quarter",
    "Waning crescent",
)

# Days between new moons.
SYNODIC_MONTH = 29.530588853


def days_since_epoch(year, month, day):
    """Days from 2000-01-01 to the given date, via a Julian day count."""
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    julian = (
        int(365.25 * (year + 4716))
        + int(30.6001 * (month + 1))
        + day
        + b
        - 1524.5
    )
    return julian - 2451544.5


def moon_phase(stamp):
    """Fraction through the lunar cycle, 0 at new moon, from an ISO date."""
    try:
        year = int(stamp[0:4])
        month = int(stamp[5:7])
        day = int(stamp[8:10])
    except (ValueError, IndexError, TypeError):
        return None
    # 2000-01-06 was a new moon, five days past the epoch above.
    age = (days_since_epoch(year, month, day) - 5.0) % SYNODIC_MONTH
    return age / SYNODIC_MONTH


def moon_name(phase):
    """Name the phase, snapping to the exact quarters."""
    return MOON_NAMES[int((phase * 8) + 0.5) % 8]


def icon_moon(group, cx, cy, phase, radius=9):
    """Disc with a white disc slid across it to carve the lit portion."""
    lit = (1 - math.cos(2 * math.pi * phase)) / 2
    group.append(
        vectorio.Circle(pixel_shader=black_palette, radius=radius, x=cx, y=cy)
    )
    direction = 1 if phase < 0.5 else -1
    offset = int(direction * 2 * radius * lit)
    group.append(
        vectorio.Circle(
            pixel_shader=white_palette, radius=radius - 1, x=cx + offset, y=cy
        )
    )


def icon_sun_marker(group, cx, cy, rising):
    """Small half sun with an arrow, marking rise or set."""
    group.append(
        vectorio.Circle(pixel_shader=black_palette, radius=5, x=cx, y=cy - 1)
    )
    group.append(
        vectorio.Rectangle(
            pixel_shader=black_palette, width=16, height=2, x=cx - 8, y=cy + 5
        )
    )
    if rising:
        # Arrow sits above the disc, pointing up out of the horizon.
        points = [(0, 0), (4, 5), (-4, 5)]
        arrow_y = cy - 14
    else:
        # Arrow drops below the horizon line, pointing down.
        points = [(0, 5), (4, 0), (-4, 0)]
        arrow_y = cy + 8
    group.append(
        vectorio.Polygon(
            pixel_shader=black_palette, points=points, x=cx, y=arrow_y
        )
    )


def draw_weather(group):
    """Forecast on the top half, newest messages underneath."""
    if weather is None:
        draw_empty(group, "No forecast yet...")
    else:
        big_font, big_scale, _ = face("large_bold")
        name_font, name_scale, name_height = face("name")
        small_font, small_scale, _ = face("small")

        unit = "F" if USE_FAHRENHEIT else "C"
        draw_weather_icon(
            group, weather["code"], MARGIN + 24, CONTENT_TOP + 14, RED
        )
        group.append(
            label.Label(
                big_font,
                text="%d%s" % (weather["now"], unit),
                color=RED,
                scale=big_scale,
                x=MARGIN + 62,
                y=CONTENT_TOP + 22,
            )
        )
        group.append(
            label.Label(
                name_font,
                text=describe_code(weather["code"]),
                color=RED,
                scale=name_scale,
                x=MARGIN + 152,
                y=CONTENT_TOP + 22,
            )
        )

        # Sun and moon share a column on the right of the current row.
        for offset, rising, value in (
            (SUN_ROW_Y, True, weather["sunrise"]),
            (SUN_ROW_Y + 20, False, weather["sunset"]),
        ):
            if not value:
                continue
            icon_sun_marker(group, SKY_ICON_X, CONTENT_TOP + offset, rising)
            group.append(
                label.Label(
                    small_font,
                    text=value,
                    color=BLACK,
                    scale=small_scale,
                    x=SKY_TEXT_X,
                    y=CONTENT_TOP + offset,
                )
            )

        phase = moon_phase(weather.get("date"))
        if phase is not None:
            moon_y = CONTENT_TOP + MOON_ROW_Y
            icon_moon(group, SKY_ICON_X, moon_y, phase)
            # Two short lines keep the column narrow instead of running
            # the name out to the panel edge.
            words = moon_name(phase).split(" ")
            for index, word in enumerate(words[:2]):
                group.append(
                    label.Label(
                        small_font,
                        text=word,
                        color=BLACK,
                        scale=small_scale,
                        x=SKY_TEXT_X,
                        y=moon_y - 6 + index * 14,
                    )
                )

        # Three day outlook, one row each.
        labels = ("Today", "Tomorrow", "Next day")
        y_pos = CONTENT_TOP + 48
        for index in range(min(3, len(weather["highs"]))):
            group.append(
                label.Label(
                    small_font, text=labels[index], color=BLACK,
                    scale=small_scale, x=MARGIN, y=y_pos
                )
            )
            group.append(
                label.Label(
                    small_font,
                    text="%d / %d%s   %s" % (
                        weather["highs"][index],
                        weather["lows"][index],
                        unit,
                        describe_code(weather["codes"][index]),
                    ),
                    color=BLACK,
                    scale=small_scale,
                    x=MARGIN + 90,
                    y=y_pos,
                )
            )
            y_pos += name_height

    add_rule(group, WEATHER_SPLIT_Y, thickness=1)
    return draw_messages(
        group,
        top=WEATHER_MSG_TOP,
        bottom=CONTENT_BOTTOM,
        limit=WEATHER_MSG_LIMIT,
    )


def build_group():
    """Build the full display group for the current view."""
    group = displayio.Group()

    background = displayio.Bitmap(WIDTH, HEIGHT, 1)
    bg_palette = displayio.Palette(1)
    bg_palette[0] = WHITE
    group.append(displayio.TileGrid(background, pixel_shader=bg_palette))

    draw_header(group)

    if VIEWS[view_index] == "nodes":
        shown = draw_nodes(group)
        hidden = max(len(node_stats) - shown, 0)
    elif VIEWS[view_index] == "weather":
        shown = draw_weather(group)
        hidden = max(len(messages) - shown, 0)
    else:
        shown = draw_messages(group)
        hidden = max(len(messages) - shown, 0)

    draw_status(group, hidden)
    return group, shown, hidden


def draw_status(group, hidden):
    """Pinned status bar along the bottom of the panel.

    Sits at a fixed height so the layout never leaves an empty band,
    and carries information worth the space it takes: how many
    messages are held, and the signal strength of the last packet.
    """
    add_rule(group, STATUS_RULE_Y, thickness=1)
    status_font, status_scale, _ = face("small")
    baseline = STATUS_RULE_Y + FOOTER_TEXT_OFFSET

    if VIEWS[view_index] == "nodes":
        left = "%d nodes heard" % len(node_stats)
    elif hidden > 0:
        left = "%d shown, %d older" % (len(messages) - hidden, hidden)
    elif messages:
        left = "%d held" % len(messages)
    else:
        left = "no messages yet"

    group.append(
        label.Label(
            status_font,
            text=left,
            color=BLACK,
            scale=status_scale,
            x=MARGIN,
            y=baseline,
        )
    )

    right = "%d dBm" % last_rssi if last_rssi is not None else "listening"
    group.append(
        label.Label(
            status_font,
            text=right,
            color=BLACK,
            scale=status_scale,
            anchor_point=(1.0, 0.5),
            anchored_position=(WIDTH - MARGIN, baseline),
        )
    )


def draw_board():
    """Render the board and block until the panel finishes updating."""
    global air, charge  # pylint: disable=global-statement
    air = read_air()
    charge = read_battery()
    if VIEWS[view_index] == "weather":
        refresh_weather()
    group, shown, hidden = build_group()
    display.root_group = group
    print("drawing...", shown, "shown,", hidden, "hidden")
    pixel_hold(PIXEL_DRAWING)
    display.refresh()
    time.sleep(REFRESH_SECONDS)
    pixel_hold((0, 0, 0))
    print("refreshed")


def handle_packet(packet):
    """Decode one packet. Returns True if a new message was added."""
    global last_rssi  # pylint: disable=global-statement
    if len(packet) < meshfruit.HEADER_LEN + 1:
        return False
    if meshfruit.channel_hash(packet) != CHANNEL_HASH:
        return False

    # Sender plus packet ID uniquely identifies a message. The mesh
    # rebroadcasts each one several times as the hop count decrements.
    packet_key = bytes(packet[4:12])
    if packet_key in seen:
        return False
    seen.append(packet_key)
    if len(seen) > SEEN_HISTORY:
        seen.pop(0)

    plain = meshfruit.decrypt(packet)
    port, body = meshfruit.parse_data(plain)
    if not body:
        return False

    node = meshfruit.sender_id(packet)
    last_rssi = rfm9x.last_rssi

    stats = node_stats.get(node)
    if stats is None:
        node_stats[node] = {"rssi": last_rssi, "count": 1}
    else:
        stats["rssi"] = last_rssi
        stats["count"] += 1

    if port == meshfruit.PORT_NODEINFO:
        # Printed raw so the field numbers can be checked against a
        # real capture rather than taken on trust.
        print("nodeinfo from", node, bytes(body).hex())
        user = meshfruit.parse_user(body)
        short = meshfruit.decode_text(user.get("short_name"))
        if short and node_names.get(node) != short:
            node_names[node] = short
            save_names()
            print("node", node, "is", short)
            # Redraw only if this node is already on the panel.
            return any(entry[0] == node for entry in messages)
        return False

    if port != meshfruit.PORT_TEXT_MESSAGE:
        return False

    text = meshfruit.decode_text(body) or "<non-utf8>"
    messages.insert(0, (node, text))
    del messages[MAX_MESSAGES:]
    print(node, text)
    return True


load_names()

draw_board()
pending = False
print("listening on", FREQUENCY, "MHz")

press_started = None
warned_soon = False

def doze():
    """Light sleep until a packet arrives, or briefly for housekeeping.

    The radio is left in continuous receive so DIO0 can wake us, which
    means nothing is missed while asleep. Waking on a short timer as
    well keeps the button and the refresh cooldown responsive.
    """
    try:
        rfm9x.listen()
        alarm.light_sleep_until_alarms(
            alarm.pin.PinAlarm(pin=RADIO_IRQ_PIN, value=True),
            alarm.time.TimeAlarm(
                monotonic_time=time.monotonic() + SLEEP_SECONDS
            ),
        )
    except (AttributeError, ValueError, RuntimeError) as sleep_error:
        print("light sleep unavailable:", sleep_error)
        return False
    return True


sleeping = LOW_POWER

while True:
    if sleeping:
        sleeping = doze()

    incoming = rfm9x.receive(with_header=True, timeout=0.2)
    if incoming and handle_packet(incoming):
        pending = True
        blink(PIXEL_MESSAGE)

    # Active low with an internal pull up. The radio call above blocks
    # for up to a second, so a press can take that long to register.
    now = time.monotonic()
    if not button.value:
        if press_started is None:
            press_started = now
    elif press_started is not None:
        held = now - press_started
        press_started = None
        if held > DEBOUNCE_SECONDS:
            if held >= LONG_PRESS_SECONDS:
                target = HOLD_VIEW
            else:
                current = VIEWS[view_index]
                if current in CYCLE_VIEWS:
                    spot = CYCLE_VIEWS.index(current)
                    target = CYCLE_VIEWS[(spot + 1) % len(CYCLE_VIEWS)]
                else:
                    target = CYCLE_VIEWS[0]
            if target != VIEWS[view_index]:
                view_index = VIEWS.index(target)
                print("view ->", target)
                blink(
                    PIXEL_PRESS if display.time_to_refresh == 0 else PIXEL_QUEUED
                )
                pending = True

    # One warning as the cooldown runs out, so a queued change does
    # not appear to arrive from nowhere.
    remaining = display.time_to_refresh
    if pending and 0 < remaining <= REFRESH_SOON_SECONDS and not warned_soon:
        blink(PIXEL_SOON)
        warned_soon = True

    if pending and remaining == 0:
        draw_board()
        pending = False
        warned_soon = False
