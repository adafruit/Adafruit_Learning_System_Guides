# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import supervisor
import terminalio

from adafruit_fruitjam import FruitJam
from adafruit_fruitjam.peripherals import request_display_config

BG_COLOR = 0x0000FF

# use built-in system font
OVERLAY_FONT = terminalio.FONT

# or un-comment to use a custom font. Fill in the path to your font file.
# OVERLAY_FONT = "Free_Mono_10.pcf"

request_display_config(320, 240)
display = supervisor.runtime.display

FETCH_DELAY = 12

# Set up where we'll be fetching data from
DATA_SOURCE = "https://www.adafruit.com/api/products/6358"

TITLE_LOCATION = ["product_name"]
SALE_PRICE_LOCATION = ["product_sale_price"]
REG_PRICE_LOCATION = ["product_price"]
STOCK_LOCATION = ["product_stock"]

config_index = 0

TEXT_POSITIONS = [
    {
        "title_anchor_point": (0, 0),
        "title_anchored_position": (4, 205 + 4),
        "stock_anchor_point": (1.0, 1.0),
        "stock_anchored_position": (display.width - 4, display.height - 4),
        "price_anchor_point": (1.0, 0),
        "price_anchored_position": (display.width - 4, 200),
        "outline_size": 1,
        "outline_color": 0x000000,
    },
    {
        "title_anchor_point": (0, 0),
        "title_anchored_position": (4, 205 + 4),
        "stock_anchor_point": (1.0, 1.0),
        "stock_anchored_position": (display.width - 4, display.height - 4),
        "price_anchor_point": (1.0, 0),
        "price_anchored_position": (display.width - 4, 200),
        "outline_size": 0,
        "outline_color": 0x000000,
    },
    {
        "title_anchor_point": (0, 0),
        "title_anchored_position": (4, 4),
        "stock_anchor_point": (1.0, 0),
        "stock_anchored_position": (display.width - 4, 26),
        "price_anchor_point": (1.0, 0),
        "price_anchored_position": (display.width - 4, 4),
        "outline_size": 0,
        "outline_color": 0x000000,
    },
    {
        "title_anchor_point": (0, 0),
        "title_anchored_position": (4, 4),
        "stock_anchor_point": (1.0, 0),
        "stock_anchored_position": (display.width - 4, 26),
        "price_anchor_point": (1.0, 0),
        "price_anchored_position": (display.width - 4, 4),
        "outline_size": 1,
        "outline_color": 0x000000,
    },
    {
        "title_anchor_point": (0, 0),
        "title_anchored_position": (4, -104),
        "stock_anchor_point": (1.0, 0),
        "stock_anchored_position": (display.width - 4, -126),
        "price_anchor_point": (1.0, 0),
        "price_anchored_position": (display.width - 4, -104),
        "outline_size": 1,
        "outline_color": 0x000000,
    },
]


def apply_hotkey_visuals(index):
    config = TEXT_POSITIONS[index]
    fruitjam.text_fields[0]["anchor_point"] = config["title_anchor_point"]
    fruitjam.text_fields[0]["position"] = config["title_anchored_position"]
    fruitjam.text_fields[0]["outline_color"] = config["outline_color"]
    fruitjam.text_fields[0]["outline_size"] = config["outline_size"]
    if fruitjam.text_fields[0]["label"] is not None:
        fruitjam.text_fields[0]["label"].anchor_point = config["title_anchor_point"]
        fruitjam.text_fields[0]["label"].anchored_position = config[
            "title_anchored_position"
        ]
        fruitjam.text_fields[0]["label"].outline_size = config["outline_size"]
        fruitjam.text_fields[0]["label"].outline_color = config["outline_color"]
    fruitjam.text_fields[1]["anchor_point"] = config["stock_anchor_point"]
    fruitjam.text_fields[1]["position"] = config["stock_anchored_position"]
    fruitjam.text_fields[1]["outline_color"] = config["outline_color"]
    fruitjam.text_fields[1]["outline_size"] = config["outline_size"]
    if fruitjam.text_fields[1]["label"] is not None:
        fruitjam.text_fields[1]["label"].anchor_point = config["stock_anchor_point"]
        fruitjam.text_fields[1]["label"].anchored_position = config[
            "stock_anchored_position"
        ]
        fruitjam.text_fields[1]["label"].outline_size = config["outline_size"]
        fruitjam.text_fields[1]["label"].outline_color = config["outline_color"]
    fruitjam.text_fields[2]["anchor_point"] = config["price_anchor_point"]
    fruitjam.text_fields[2]["position"] = config["price_anchored_position"]
    fruitjam.text_fields[2]["outline_color"] = config["outline_color"]
    fruitjam.text_fields[2]["outline_size"] = config["outline_size"]
    if fruitjam.text_fields[2]["label"] is not None:
        fruitjam.text_fields[2]["label"].anchor_point = config["price_anchor_point"]
        fruitjam.text_fields[2]["label"].anchored_position = config[
            "price_anchored_position"
        ]
        fruitjam.text_fields[2]["label"].outline_size = config["outline_size"]
        fruitjam.text_fields[2]["label"].outline_color = config["outline_color"]


def format_data(json_data):
    if "product_sale_price" in json_data:
        json_data["product_sale_price"] = f'${json_data["product_sale_price"]}'
    else:
        json_data["product_sale_price"] = f'${json_data["product_price"]}'

    json_data["product_stock"] = f'Stock: {json_data["product_stock"]}'


# the current working directory (where this file is)
cwd = ("/" + __file__).rsplit("/", 1)[0]

fruitjam = FruitJam(
    url=DATA_SOURCE,
    json_path=(TITLE_LOCATION, STOCK_LOCATION, SALE_PRICE_LOCATION),
    status_neopixel=board.NEOPIXEL,
    default_bg=BG_COLOR,
    json_transform=[format_data],
    debug=True,
)
fruitjam.remove_all_text()
fruitjam.add_text(
    text_font=OVERLAY_FONT, text_wrap=35, text_maxlen=180, text_color=0xFFFFFF, outline_size=1
)  # title
fruitjam.add_text(
    text_font=OVERLAY_FONT, text_wrap=0, text_maxlen=30, text_color=0xFFFFFF, outline_size=1
)  # stock
fruitjam.add_text(
    text_font=OVERLAY_FONT, text_wrap=0, text_maxlen=30, text_color=0xFFFFFF, outline_size=1
)  # price
apply_hotkey_visuals(config_index)

fruitjam.neopixels.brightness = 0.1

fetch_success = False
data_values = None
last_fetch_time = 0

while not fetch_success:
    try:
        data_values = fruitjam.fetch()
        fruitjam._text[2]["label"].scale = 2  # pylint: disable=protected-access
        fetch_success = True
        last_fetch_time = time.monotonic()
    except ValueError as e:
        # no value found for product_sale_price
        print("product_sale_price not found. Using regular price.")
        print(fruitjam.json_path)
        fruitjam.json_path = (TITLE_LOCATION, STOCK_LOCATION, ["product_price"])
        print(fruitjam.json_path)
        time.sleep(5)
    except (RuntimeError, ConnectionError, OSError) as e:
        print("Some error occured, retrying! -", e)
        time.sleep(5)

old_btn1 = False
old_btn2 = False
old_btn3 = False

while True:
    btn1_pressed = fruitjam.button1
    if btn1_pressed and not old_btn1:
        config_index = (config_index + 1) % len(TEXT_POSITIONS)
        apply_hotkey_visuals(config_index)

    now = time.monotonic()
    if last_fetch_time + FETCH_DELAY <= now:
        try:
            data_values = fruitjam.fetch()
            print(f"type: {fruitjam.text_fields[1]['label']}")
            fruitjam._text[2]["label"].scale = 2  # pylint: disable=protected-access
            fetch_success = True
            last_fetch_time = time.monotonic()
        except (ValueError, RuntimeError, ConnectionError, OSError) as e:
            print("Some error occured, retrying! -", e)

    old_btn1 = btn1_pressed
