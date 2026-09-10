# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
MeshFruit e-ink message board.

Listens for LoRa mesh broadcast text messages and renders the most
recent ones to a 4.2 inch tri-color e-ink panel, alongside a weather
forecast, air quality and battery runtime.

A button on A0 cycles views. Switching does not reboot, so the message
buffer survives a view change.

Receive only. This board does not transmit and will not appear in the
mesh node list.
"""

import os
import time

import adafruit_max1704x
import adafruit_rfm9x
import adafruit_ssd1683
import adafruit_stcc4
import alarm
import board
import digitalio
import displayio
import microcontroller
import neopixel
import terminalio
from adafruit_debouncer import Button
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label, wrap_text_to_pixels
from adafruit_meshfruit import meshtastic as meshfruit
from fourwire import FourWire

import mesh_icons
import mesh_weather

displayio.release_displays()

# --- settings ---------------------------------------------------------

LATITUDE = os.getenv("LATITUDE")
LONGITUDE = os.getenv("LONGITUDE")
WIFI_SSID = os.getenv("CIRCUITPY_WIFI_SSID")
WIFI_PASSWORD = os.getenv("CIRCUITPY_WIFI_PASSWORD")

USE_FAHRENHEIT = True

# --- radio ------------------------------------------------------------

# US 915MHz band, 250kHz slots. Slot N sits at 902.125 + (N - 1) * 0.25
# MHz, and slot 20 is the default for the public channel. Outside the
# US this has to match whatever the nodes around you are using: run
# "meshtastic --info" on a node to read its operating frequency.
FREQUENCY = 906.875
CHANNEL_HASH = 0x08
SYNC_WORD_REG = 0x39
MESH_SYNC_WORD = 0x2B
RADIO_IRQ_PIN = board.A5

# --- layout -----------------------------------------------------------

WIDTH = 400
HEIGHT = 300
MARGIN = 10
TEXT_WIDTH = WIDTH - MARGIN * 2

BLACK = 0x000000
RED = 0xFF0000
WHITE = 0xFFFFFF

HEADER_BASELINE = 16
RULE_Y = 30
CONTENT_TOP = 52
CONTENT_BOTTOM = 262
STATUS_RULE_Y = 272
NODES_TOP = 64
MESSAGE_GAP = 14
FOOTER_TEXT_OFFSET = 9

WEATHER_SPLIT_Y = 168
WEATHER_MSG_TOP = 182
WEATHER_MSG_LIMIT = 2
SKY_ICON_X = WIDTH - 100
SKY_TEXT_X = SKY_ICON_X + 18
SUN_ROW_Y = 6
MOON_ROW_Y = 62

# Weight carries recency, size carries fit. All faces are from the
# public domain Misc-Fixed family, trimmed to printable ASCII.
FONT_PATHS = {
    "large_bold": "/fonts/9x18B.pcf",
    "medium_bold": "/fonts/7x14B.pcf",
    "medium": "/fonts/7x14.pcf",
    "name": "/fonts/6x13B.pcf",
    "small": "/fonts/6x10.pcf",
}
MAX_LARGE_LINES = 2

# --- behaviour --------------------------------------------------------

MAX_MESSAGES = 12
SEEN_HISTORY = 20
REFRESH_SECONDS = 20

BUTTON_PIN = board.A0
LONG_PRESS_MS = 1000
VIEWS = ("weather", "messages", "nodes")
VIEW_TITLES = {"weather": "Weather", "messages": "MeshFruit", "nodes": "Nodes"}
CYCLE_VIEWS = ("weather", "messages")
HOLD_VIEW = "nodes"

# The panel cannot redraw more than once every 180 seconds, so the
# pixel carries the fast feedback the display cannot.
BLINK_SECONDS = 0.35
PIXEL_PRESS = (0, 0, 60)
PIXEL_MESSAGE = (0, 50, 0)
PIXEL_QUEUED = (60, 25, 0)
PIXEL_SOON = (50, 40, 0)
PIXEL_DRAWING = (40, 0, 40)
REFRESH_SOON_SECONDS = 10

CPU_FREQUENCY = 80_000_000
SLEEP_SECONDS = 0.3

AIR_SETTLE_SECONDS = 1.0
BATTERY_RATE_FLOOR = 0.5

# Learned short names are cached in NVM so they survive a reboot.
NAMES_MAGIC = b"MF1"
NAMES_MAX = 24
NAME_LEN = 4
ENTRY_LEN = 4 + NAME_LEN

# Nothing here is compute bound, so run the CPU slower.
microcontroller.cpu.frequency = CPU_FREQUENCY

# --- hardware ---------------------------------------------------------

# The STEMMA sensors come up first. board.STEMMA_I2C() claims and
# manages I2C_POWER itself, and if another peripheral gets there first
# the bus comes up with no pull ups, which surfaces as a wiring error
# rather than a power one.
i2c = board.STEMMA_I2C()
air_sensor = adafruit_stcc4.STCC4(i2c)
air_sensor.continuous_measurement = True
time.sleep(AIR_SETTLE_SECONDS)
battery = adafruit_max1704x.MAX17048(i2c)

spi = board.SPI()

# The eInk Feather Friend owns D5, D6, D9 and D10. Park the SRAM and SD
# chip selects so they do not drive the shared SPI bus.
for pin in (board.D6, board.D5):
    parked = digitalio.DigitalInOut(pin)
    parked.direction = digitalio.Direction.OUTPUT
    parked.value = True

# Leave reset and busy as None. The Feather Friend does not bring those
# out to D8 and D7, and claiming those pins corrupts the I2C bus.
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
rfm9x._write_u8(SYNC_WORD_REG, MESH_SYNC_WORD)  # pylint: disable=protected-access

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2, auto_write=True)

button_pin = digitalio.DigitalInOut(BUTTON_PIN)
button_pin.direction = digitalio.Direction.INPUT
button_pin.pull = digitalio.Pull.UP
button = Button(button_pin, long_duration_ms=LONG_PRESS_MS)

FONTS = {name: bitmap_font.load_font(path) for name, path in FONT_PATHS.items()}

rule_palette = displayio.Palette(1)
rule_palette[0] = BLACK

# --- state ------------------------------------------------------------

messages = []
seen = []
node_names = {}
node_stats = {}
view_index = 0
pending = False
warned_soon = False

# Held in dicts so the functions below can update them without a
# global statement.
radio_state = {"rssi": None}
forecast = {"data": None, "at": 0.0}

# --- sensors ----------------------------------------------------------


def read_air():
    """Read the air sensor. Returns a display string, or None.

    CO2 is read first: the driver fetches the whole measurement on that
    property, so asking for temperature first reports "not ready".
    """
    try:
        co2 = air_sensor.CO2
        humidity = air_sensor.relative_humidity
        celsius = air_sensor.temperature
    except (RuntimeError, OSError) as error:
        print("air read failed:", error)
        return None

    degrees = celsius * 9 / 5 + 32 if USE_FAHRENHEIT else celsius
    unit = "F" if USE_FAHRENHEIT else "C"
    return f"{co2} ppm   {round(degrees)}{unit}   {round(humidity)}%"


def format_hours(hours):
    """Render a duration compactly: 45m, 6h, 2d."""
    if hours < 1:
        return f"{max(round(hours * 60), 1)}m"
    if hours < 48:
        return f"{round(hours)}h"
    return f"{round(hours / 24)}d"


def read_battery():
    """Charge state and estimated time remaining.

    charge_rate is percent per hour, signed. Dividing the remaining
    capacity by it gives a runtime estimate, which matters more than a
    percentage on a board meant to outlast a power cut.
    """
    try:
        percent = min(max(battery.cell_percent, 0), 100)
        rate = battery.charge_rate
    except (RuntimeError, OSError) as error:
        print("battery read failed:", error)
        return None

    text = f"{round(percent)}%"
    if rate > BATTERY_RATE_FLOOR:
        return f"{text} +{format_hours((100.0 - percent) / rate)}"
    if rate < -BATTERY_RATE_FLOOR:
        return f"{text} {format_hours(percent / abs(rate))}"
    return text


# --- fonts and text ---------------------------------------------------


def face(size):
    """Return the font and its line height for a named face."""
    font = FONTS[size]
    return font, font.get_bounding_box()[1] + 4


def wrap_for(text, size):
    """Wrap text to the panel width for a named face."""
    font, line_height = face(size)
    return wrap_text_to_pixels(text, TEXT_WIDTH, font), font, line_height


def size_for(index, text):
    """Pick a face for a message at this position in the list.

    The newest message is always bold and red. It uses the large face
    unless it runs long, in which case it steps down so it does not
    crowd older messages off the panel.
    """
    if index != 0:
        return "medium"
    lines, _, _ = wrap_for(text, "large_bold")
    if len(lines) > MAX_LARGE_LINES:
        return "medium_bold"
    return "large_bold"


# --- node names -------------------------------------------------------


def load_names():
    """Restore cached short names from NVM."""
    blob = bytes(microcontroller.nvm[: 4 + NAMES_MAX * ENTRY_LEN])
    if blob[:3] != NAMES_MAGIC:
        return
    for index in range(min(blob[3], NAMES_MAX)):
        start = 4 + index * ENTRY_LEN
        number = int.from_bytes(blob[start : start + 4], "little")
        short = blob[start + 4 : start + ENTRY_LEN].rstrip(b"\x00")
        if short:
            node_names[f"!{number:08x}"] = short.decode("utf-8")
    print("restored", len(node_names), "node names")


def save_names():
    """Persist known short names to NVM.

    Only called when a name changes, since NVM sits in flash and has a
    finite write endurance.
    """
    items = list(node_names.items())[:NAMES_MAX]
    blob = bytearray(NAMES_MAGIC + bytes([len(items)]))
    for node, short in items:
        blob += int(node[1:], 16).to_bytes(4, "little")
        # CircuitPython's bytes has no ljust, so pad by hand.
        raw = short.encode("utf-8")[:NAME_LEN]
        blob += raw + b"\x00" * (NAME_LEN - len(raw))
    microcontroller.nvm[0 : len(blob)] = blob


def display_name(node):
    """Short name for a node if NodeInfo has been heard, else its ID."""
    return node_names.get(node, node)


# --- drawing ----------------------------------------------------------


def add_rule(group, y_pos, thickness=2):
    """Draw a horizontal rule across the content width."""
    bitmap = displayio.Bitmap(WIDTH - MARGIN * 2, thickness, 1)
    group.append(
        displayio.TileGrid(bitmap, pixel_shader=rule_palette, x=MARGIN, y=y_pos)
    )


def draw_header(group, air, charge):
    """Title, air readings and battery, above the rule."""
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
    name_font, _ = face("name")
    if air:
        group.append(
            label.Label(
                name_font,
                text=air,
                color=BLACK,
                anchor_point=(0.5, 0.5),
                anchored_position=(WIDTH // 2, HEADER_BASELINE),
            )
        )
    if charge:
        group.append(
            label.Label(
                name_font,
                text=charge,
                color=BLACK,
                anchor_point=(1.0, 0.5),
                anchored_position=(WIDTH - MARGIN, HEADER_BASELINE),
            )
        )
    add_rule(group, RULE_Y)


def draw_empty(group, text, y_pos):
    """Placeholder for a view with nothing to show yet."""
    group.append(
        label.Label(
            terminalio.FONT, text=text, color=BLACK, scale=2, x=MARGIN, y=y_pos
        )
    )


def draw_messages(  # pylint: disable=too-many-locals
    group, top=CONTENT_TOP, bottom=CONTENT_BOTTOM, limit=None
):
    """Message list. Returns the number of messages shown."""
    if not messages:
        draw_empty(group, "Listening for messages...", top + 10)
        return 0

    meta_font, meta_height = face("name")
    y_pos = top
    shown = 0

    for index, (node, text) in enumerate(messages):
        if limit is not None and shown >= limit:
            break
        size = size_for(index, text)
        lines, font, line_height = wrap_for(text, size)
        needed = meta_height + len(lines) * line_height + MESSAGE_GAP

        # Always show the newest message even if it runs long, but never
        # start a later block that cannot fit.
        if shown > 0 and y_pos + needed > bottom:
            break

        color = RED if index == 0 else BLACK
        group.append(
            label.Label(
                meta_font, text=display_name(node), color=color, x=MARGIN, y=y_pos
            )
        )

        line_y = y_pos + meta_height + 8
        for line in lines:
            if line_y > bottom:
                break
            group.append(
                label.Label(font, text=line, color=color, x=MARGIN, y=line_y)
            )
            line_y += line_height

        y_pos += needed
        shown += 1

    return shown


def draw_nodes(group):
    """Node list: who has been heard, how strongly, how often."""
    if not node_stats:
        draw_empty(group, "No nodes heard yet...", CONTENT_TOP + 10)
        return 0

    name_font, name_height = face("name")
    small_font, small_height = face("small")

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
            label.Label(name_font, text=name, color=color, x=MARGIN, y=y_pos)
        )
        group.append(
            label.Label(
                small_font,
                text=f"{stats['rssi']} dBm  {stats['count']} pkt",
                color=color,
                anchor_point=(1.0, 0.5),
                anchored_position=(WIDTH - MARGIN, y_pos),
            )
        )

        # Only worth a second line once NodeInfo has given us a name,
        # otherwise it would just repeat the ID above it.
        if has_name:
            group.append(
                label.Label(
                    small_font, text=node, color=color, x=MARGIN, y=y_pos + name_height
                )
            )

        y_pos += block
        shown += 1

    return shown


def draw_weather(group, weather):  # pylint: disable=too-many-locals
    """Forecast on the top half, newest messages underneath."""
    if weather is None:
        draw_empty(group, "No forecast yet...", CONTENT_TOP + 10)
    else:
        big_font, _ = face("large_bold")
        name_font, name_height = face("name")
        small_font, _ = face("small")
        unit = "F" if USE_FAHRENHEIT else "C"

        mesh_icons.draw_weather_icon(
            group, weather["code"], MARGIN + 24, CONTENT_TOP + 14, RED
        )
        group.append(
            label.Label(
                big_font,
                text=f"{weather['now']}{unit}",
                color=RED,
                x=MARGIN + 62,
                y=CONTENT_TOP + 22,
            )
        )
        group.append(
            label.Label(
                name_font,
                text=mesh_weather.describe_code(weather["code"]),
                color=RED,
                x=MARGIN + 152,
                y=CONTENT_TOP + 22,
            )
        )

        for offset, rising, value in (
            (SUN_ROW_Y, True, weather["sunrise"]),
            (SUN_ROW_Y + 20, False, weather["sunset"]),
        ):
            if not value:
                continue
            mesh_icons.icon_sun_marker(group, SKY_ICON_X, CONTENT_TOP + offset, rising)
            group.append(
                label.Label(
                    small_font,
                    text=value,
                    color=BLACK,
                    x=SKY_TEXT_X,
                    y=CONTENT_TOP + offset,
                )
            )

        phase = mesh_weather.moon_phase(weather["date"])
        if phase is not None:
            moon_y = CONTENT_TOP + MOON_ROW_Y
            mesh_icons.icon_moon(group, SKY_ICON_X, moon_y, phase)
            # Two short lines keep the column narrow instead of running
            # the name out to the panel edge.
            for index, word in enumerate(mesh_weather.moon_name(phase).split(" ")[:2]):
                group.append(
                    label.Label(
                        small_font,
                        text=word,
                        color=BLACK,
                        x=SKY_TEXT_X,
                        y=moon_y - 6 + index * 14,
                    )
                )

        labels = ("Today", "Tomorrow", "Next day")
        y_pos = CONTENT_TOP + 48
        for index in range(min(3, len(weather["highs"]))):
            group.append(
                label.Label(
                    small_font, text=labels[index], color=BLACK, x=MARGIN, y=y_pos
                )
            )
            group.append(
                label.Label(
                    small_font,
                    text=(
                        f"{weather['highs'][index]} / {weather['lows'][index]}{unit}"
                        f"   {mesh_weather.describe_code(weather['codes'][index])}"
                    ),
                    color=BLACK,
                    x=MARGIN + 90,
                    y=y_pos,
                )
            )
            y_pos += name_height

    add_rule(group, WEATHER_SPLIT_Y, thickness=1)
    return draw_messages(
        group, top=WEATHER_MSG_TOP, bottom=CONTENT_BOTTOM, limit=WEATHER_MSG_LIMIT
    )


def draw_status(group, hidden):
    """Pinned status bar along the bottom of the panel."""
    add_rule(group, STATUS_RULE_Y, thickness=1)
    small_font, _ = face("small")
    baseline = STATUS_RULE_Y + FOOTER_TEXT_OFFSET

    if VIEWS[view_index] == "nodes":
        left = f"{len(node_stats)} nodes heard"
    elif hidden > 0:
        left = f"{len(messages) - hidden} shown, {hidden} older"
    elif messages:
        left = f"{len(messages)} held"
    else:
        left = "no messages yet"

    group.append(
        label.Label(small_font, text=left, color=BLACK, x=MARGIN, y=baseline)
    )
    group.append(
        label.Label(
            small_font,
            text=(
                f"{radio_state['rssi']} dBm"
                if radio_state["rssi"] is not None
                else "listening"
            ),
            color=BLACK,
            anchor_point=(1.0, 0.5),
            anchored_position=(WIDTH - MARGIN, baseline),
        )
    )


def build_group(air, charge, weather):
    """Build the full display group for the current view."""
    group = displayio.Group()

    background = displayio.Bitmap(WIDTH, HEIGHT, 1)
    bg_palette = displayio.Palette(1)
    bg_palette[0] = WHITE
    group.append(displayio.TileGrid(background, pixel_shader=bg_palette))

    draw_header(group, air, charge)

    if VIEWS[view_index] == "nodes":
        shown = draw_nodes(group)
        hidden = max(len(node_stats) - shown, 0)
    elif VIEWS[view_index] == "weather":
        shown = draw_weather(group, weather)
        hidden = max(len(messages) - shown, 0)
    else:
        shown = draw_messages(group)
        hidden = max(len(messages) - shown, 0)

    draw_status(group, hidden)
    return group, shown, hidden


def blink(color):
    """Flash the pixel to signal something the panel cannot show yet."""
    pixel[0] = color
    time.sleep(BLINK_SECONDS)
    pixel[0] = (0, 0, 0)


def refresh_weather():
    """Fetch the forecast if the cached copy is stale."""
    elapsed = time.monotonic()
    if forecast["data"] is not None and elapsed - forecast["at"] < mesh_weather.INTERVAL:
        return
    fetched = mesh_weather.fetch(
        WIFI_SSID, WIFI_PASSWORD, LATITUDE, LONGITUDE, USE_FAHRENHEIT
    )
    if fetched is not None:
        forecast["data"] = fetched
        forecast["at"] = elapsed


def draw_board():
    """Render the board and block until the panel finishes updating."""
    if VIEWS[view_index] == "weather":
        refresh_weather()

    group, shown, hidden = build_group(
        read_air(), read_battery(), forecast["data"]
    )
    display.root_group = group
    print("drawing...", shown, "shown,", hidden, "hidden")
    pixel[0] = PIXEL_DRAWING
    display.refresh()
    time.sleep(REFRESH_SECONDS)
    pixel[0] = (0, 0, 0)
    print("refreshed")


def handle_packet(packet):  # pylint: disable=too-many-return-statements
    """Decode one packet. Returns True if the panel should redraw."""
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

    port, body = meshfruit.parse_data(meshfruit.decrypt(packet))
    if not body:
        return False

    node = meshfruit.sender_id(packet)
    radio_state["rssi"] = rfm9x.last_rssi

    stats = node_stats.get(node)
    if stats is None:
        node_stats[node] = {"rssi": rfm9x.last_rssi, "count": 1}
    else:
        stats["rssi"] = rfm9x.last_rssi
        stats["count"] += 1

    if port == meshfruit.PORT_NODEINFO:
        short = meshfruit.decode_text(meshfruit.parse_user(body).get("short_name"))
        if short and node_names.get(node) != short:
            node_names[node] = short
            save_names()
            print("node", node, "is", short)
            # Redraw only if this node is already on the panel.
            return any(entry[0] == node for entry in messages)
        return False

    if port != meshfruit.PORT_TEXT_MESSAGE:
        return False

    messages.insert(0, (node, meshfruit.decode_text(body) or "<non-utf8>"))
    del messages[MAX_MESSAGES:]
    print(node, messages[0][1])
    return True


def doze():
    """Light sleep until a packet arrives, or briefly for housekeeping.

    The radio is left in continuous receive so its DIO0 line can wake
    us, which means nothing is missed while asleep. Waking on a short
    timer as well keeps the button and refresh cooldown responsive.
    """
    rfm9x.listen()
    alarm.light_sleep_until_alarms(
        alarm.pin.PinAlarm(pin=RADIO_IRQ_PIN, value=True),
        alarm.time.TimeAlarm(monotonic_time=time.monotonic() + SLEEP_SECONDS),
    )


# --- main loop --------------------------------------------------------

load_names()
draw_board()
print("listening on", FREQUENCY, "MHz")

while True:
    doze()

    incoming = rfm9x.receive(with_header=True, timeout=0.2)
    if incoming and handle_packet(incoming):
        pending = True
        blink(PIXEL_MESSAGE)

    button.update()
    target = None
    if button.long_press:
        target = HOLD_VIEW
    elif button.short_count:
        current = VIEWS[view_index]
        spot = CYCLE_VIEWS.index(current) if current in CYCLE_VIEWS else -1
        target = CYCLE_VIEWS[(spot + 1) % len(CYCLE_VIEWS)]

    if target is not None and target != VIEWS[view_index]:
        view_index = VIEWS.index(target)
        print("view ->", target)
        blink(PIXEL_PRESS if display.time_to_refresh == 0 else PIXEL_QUEUED)
        pending = True

    # One warning as the cooldown runs out, so a queued change does not
    # appear to arrive from nowhere.
    remaining = display.time_to_refresh
    if pending and 0 < remaining <= REFRESH_SOON_SECONDS and not warned_soon:
        blink(PIXEL_SOON)
        warned_soon = True

    if pending and remaining == 0:
        draw_board()
        pending = False
        warned_soon = False
