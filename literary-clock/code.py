# SPDX-FileCopyrightText: 2022 Eva Herrada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time

import ssl
import gc
import socketpool
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT
import adafruit_datetime
import adafruit_display_text
from adafruit_display_text import label
import board
from adafruit_bitmap_font import bitmap_font
import displayio
from adafruit_display_shapes.rect import Rect

UTC_OFFSET = -4

quotes = {}
with open("quotes.csv", "r", encoding="UTF-8") as F:
    for quote_line in F:
        split = quote_line.split("|")
        quotes[split[0]] = split[1:]

display = board.DISPLAY
splash = displayio.Group()
display.root_group = splash

arial = bitmap_font.load_font("fonts/Arial-12.pcf")
bold = bitmap_font.load_font("fonts/Arial-Bold-12.pcf")
LINE_SPACING = 0.8
HEIGHT = arial.get_bounding_box()[1]
QUOTE_X = 10
QUOTE_Y = 7

rect = Rect(0, 0, 296, 128, fill=0xFFFFFF, outline=0xFFFFFF)
splash.append(rect)

quote = label.Label(
    font=arial,
    x=QUOTE_X,
    y=QUOTE_Y,
    color=0x000000,
    line_spacing=LINE_SPACING,
)

splash.append(quote)
time_label = label.Label(
    font=bold,
    color=0x000000,
    line_spacing=LINE_SPACING,
)
splash.append(time_label)

time_label_2 = label.Label(
    font=bold,
    color=0x000000,
    line_spacing=LINE_SPACING,
)
splash.append(time_label_2)

after_label = label.Label(
    font=arial,
    color=0x000000,
    line_spacing=LINE_SPACING,
)
splash.append(after_label)

after_label_2 = label.Label(
    font=arial,
    color=0x000000,
    line_spacing=LINE_SPACING,
)
splash.append(after_label_2)

author_label = label.Label(
    font=arial, x=QUOTE_X, y=115, color=0x000000, line_spacing=LINE_SPACING
)
splash.append(author_label)

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]

print(f"Connecting to {secrets['ssid']}")
wifi.radio.connect(secrets["ssid"], secrets["password"])
print(f"Connected to {secrets['ssid']}!")


def get_width(font, text):
    return sum(font.get_glyph(ord(c)).shift_x for c in text)


def smart_split(text, font, width):
    words = ""
    spl = text.split(" ")
    for i, word in enumerate(spl):
        words += f" {word}"
        lwidth = get_width(font, words)
        if width + lwidth > 276:
            spl[i] = "\n" + spl[i]
            text = " ".join(spl)
            break
    return text


def connected(client):  # pylint: disable=unused-argument
    io.subscribe_to_time("iso")


def disconnected(client):  # pylint: disable=unused-argument
    print("Disconnected from Adafruit IO!")


def update_text(hour_min):
    quote.text = (
        time_label.text
    ) = time_label_2.text = after_label.text = after_label_2.text = ""

    before, time_text, after = quotes[hour_min][0].split("^")
    text = adafruit_display_text.wrap_text_to_pixels(before, 276, font=arial)
    quote.text = "\n".join(text)

    for line in text:
        width = get_width(arial, line)

    time_text = smart_split(time_text, bold, width)

    split_time = time_text.split("\n")
    if time_text[0] != "\n":
        time_label.x = time_x = QUOTE_X + width
        time_label.y = time_y = QUOTE_Y + int((len(text) - 1) * HEIGHT * LINE_SPACING)
        time_label.text = split_time[0]
    if "\n" in time_text:
        time_label_2.x = time_x = QUOTE_X
        time_label_2.y = time_y = QUOTE_Y + int(len(text) * HEIGHT * LINE_SPACING)
        wrapped = adafruit_display_text.wrap_text_to_pixels(
            split_time[1], 276, font=arial
        )
        time_label_2.text = "\n".join(wrapped)
    width = get_width(bold, split_time[-1]) + time_x - QUOTE_X

    if after:
        after = smart_split(after, arial, width)

        split_after = after.split("\n")
        if after[0] != "\n":
            after_label.x = QUOTE_X + width
            after_label.y = time_y
            after_label.text = split_after[0]
        if "\n" in after:
            after_label_2.x = QUOTE_X
            after_label_2.y = time_y + int(HEIGHT * LINE_SPACING)
            wrapped = adafruit_display_text.wrap_text_to_pixels(
                split_after[1], 276, font=arial
            )
            after_label_2.text = "\n".join(wrapped)

    author = f"{quotes[hour_min][2]} - {quotes[hour_min][1]}"
    author_label.text = adafruit_display_text.wrap_text_to_pixels(
        author, 276, font=arial
    )[0]
    time.sleep(display.time_to_refresh + 0.1)
    display.refresh()


LAST = None


def message(client, feed_id, payload):  # pylint: disable=unused-argument
    global LAST  # pylint: disable=global-statement
    timezone = adafruit_datetime.timezone.utc
    timezone._offset = adafruit_datetime.timedelta(  # pylint: disable=protected-access
        seconds=UTC_OFFSET * 3600
    )
    datetime = adafruit_datetime.datetime.fromisoformat(payload[:-1]).replace(
        tzinfo=timezone
    )
    local_datetime = datetime.tzinfo.fromutc(datetime)
    print(local_datetime)
    hour_min = f"{local_datetime.hour:02}:{local_datetime.minute:02}"
    if local_datetime.minute != LAST:
        if hour_min in quotes:
            update_text(hour_min)

    LAST = local_datetime.minute
    gc.collect()


# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)

# Initialize a new MQTT Client object
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    port=1883,
    username=secrets["aio_username"],
    password=secrets["aio_key"],
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

# Initialize an Adafruit IO MQTT Client
io = IO_MQTT(mqtt_client)

# Connect the callback methods defined above to Adafruit IO
io.on_connect = connected
io.on_disconnect = disconnected
io.on_message = message

# Connect to Adafruit IO
print("Connecting to Adafruit IO...")
io.connect()

while True:
    try:
        io.loop()
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        io.reconnect()
        continue
    time.sleep(1)
