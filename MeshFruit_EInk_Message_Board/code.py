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

import time

import alarm
import board
import digitalio
import displayio
import microcontroller
import terminalio
import adafruit_rfm9x
import adafruit_ssd1683
from fourwire import FourWire
from adafruit_display_text import label
from adafruit_meshfruit import meshtastic as meshfruit

import mesh_fonts
from mesh_fonts import face, size_for, wrap_for
from mesh_sensors import USE_FAHRENHEIT, read_air, read_battery
from mesh_icons import draw_weather_icon, icon_moon, icon_sun_marker
from mesh_weather import (
    WEATHER_INTERVAL,
    describe_code,
    fetch_weather,
    moon_name,
    moon_phase,
)

FREQUENCY = 906.875
CHANNEL_HASH = 0x08
SYNC_WORD_REG = 0x39
MESHTASTIC_SYNC_WORD = 0x2B

WIDTH = 400
HEIGHT = 300
MARGIN = 10
TEXT_WIDTH = WIDTH - MARGIN * 2


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

WEATHER_INTERVAL = 1800  # seconds between fetches

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








air = None
charge = None
weather = None
weather_fetched = 0.0
















def refresh_weather():
    """Fetch if the cached forecast is stale."""
    global weather, weather_fetched  # pylint: disable=global-statement
    elapsed = time.monotonic()
    if weather is not None and elapsed - weather_fetched < WEATHER_INTERVAL:
        return
    fetched = fetch_weather(USE_FAHRENHEIT)
    if fetched is not None:
        weather = fetched
        weather_fetched = elapsed




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





if not all(mesh_fonts.FONTS.values()):
    print("bitmap fonts not found, falling back to terminalio")








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


def draw_messages(  # pylint: disable=too-many-locals
    group, top=CONTENT_TOP, bottom=CONTENT_BOTTOM, limit=None
):
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


def draw_nodes(group):  # pylint: disable=too-many-locals
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
























def draw_weather(group):  # pylint: disable=too-many-locals
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


def handle_packet(packet):  # pylint: disable=too-many-return-statements
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
