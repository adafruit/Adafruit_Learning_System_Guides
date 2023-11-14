# SPDX-FileCopyrightText: 2023 Melissa-LeBlanc-Williams for Adafruit Industries
# SPDX-FileCopyrightText: 2023 Erin St. Blaine for Adafruit Industries
# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# SMS Message board matrix display
# uses AdafruitIO to serve up a message text feed and color feed
# messages are displayed in order, updates periodically to look for new messages

from collections import deque
import time
import random
import board
from adafruit_matrixportal.matrix import Matrix
from adafruit_matrixportal.network import Network
from messageboard import MessageBoard
from messageboard.fontpool import FontPool
from messageboard.message import Message

WIDTH = 64
HEIGHT = 32
DEFAULT_COLOR = 0x0000FF
DEFAULT_MESSAGE = "Text Adafruit IO to update"
DEFAULT_FONT = "arial_sm"
MESSAGES_FEED = "text"
COLORS_FEED = "color"
UPDATE_DELAY = 50  # Seconds between updates
SCROLL_DURATION = 6  # Seconds to scroll entire message
RANDOMIZE_FONTS = True  # Randomize fonts, make "False" to just use the default font
RANDOMIZE_COLORS = True  # Randomise colors, make "False" to just use the default color
KEEP_LATEST_MESSAGE = True  # Keep the last message in the Message Feed

# --- Display setup ---
matrix = Matrix(width=WIDTH, height=HEIGHT, bit_depth=5)
network = Network(status_neopixel=board.NEOPIXEL, debug=True)
messageboard = MessageBoard(matrix)

fontpool = FontPool()
fontpool.add_font("arial_sm", "fonts/Arial-10.pcf")
fontpool.add_font("arial_lg", "fonts/Arial-15.pcf")
fontpool.add_font("sofia", "fonts/Sofia-Regular-15.pcf")

system_message = Message(fontpool.find_font("arial_sm"))

message_fonts = ("sofia", "arial_lg")

message_queue = deque((), 10000)  # Use a double-ended queue for messages
colors = []


def update_data():
    print("Updating data from Adafruit IO")
    # Only show connecting message if not connected
    if not network.is_connected:
        system_message.clear()
        system_message.add_text("Connecting", color=0xFFFF00)
        messageboard.animate(system_message, "Static", "show")

    try:
        color_data = network.get_io_data(COLORS_FEED)
        colors.clear()
        for json_data in color_data:
            color = network.json_traverse(json_data, ["value"])
            colors.append(int(color[1:], 16))
    # pylint: disable=broad-except
    except Exception as error:
        print(error)

    try:
        messages_data = network.get_io_data(MESSAGES_FEED)
        message_ids = []
        sms_messages = []  # Temporary place for messages
        for json_data in messages_data:
            message_ids.append(network.json_traverse(json_data, ["id"]))
            sms_messages.append(network.json_traverse(json_data, ["value"]))

        # Results are returned in reverse order, so we reverse that and add to end of queue
        sms_messages.reverse()
        for sms_message in sms_messages:
            message_queue.append(sms_message)

        # Remove any messages that have been grabbed except the latest one if setting enabled
        start_index = 1 if KEEP_LATEST_MESSAGE else 0
        for index in range(start_index, len(message_ids)):
            message_id = message_ids[index]
            network.delete_io_data(MESSAGES_FEED, message_id)

    # pylint: disable=broad-except
    except Exception as error:
        print(error)

    messageboard.animate(system_message, "Static", "hide")


def get_new_rand_item(current_index, item_list):
    if not item_list:
        return None
    if len(item_list) > 1 and current_index is not None:
        new_index = current_index
        while new_index == current_index:
            new_index = random.randrange(0, len(item_list))
    else:
        new_index = random.randrange(0, len(item_list))
    return new_index


update_data()
last_update = time.monotonic()
quote_index = None
color_index = None
font_index = None
message_text = None

while True:
    if len(message_queue) >= 1:
        message_text = message_queue.popleft()

    if message_text is None:
        message_text = DEFAULT_MESSAGE

    # Choose a random color from colors
    if RANDOMIZE_COLORS:
        color_index = get_new_rand_item(color_index, colors)
        if color_index is None:
            message_color = DEFAULT_COLOR
        else:
            message_color = colors[color_index]
    else:
        message_color = DEFAULT_COLOR

    # Choose a random font from message_fonts
    if RANDOMIZE_FONTS:
        font_index = get_new_rand_item(font_index, message_fonts)
        if font_index is None:
            message_font = DEFAULT_FONT
        else:
            message_font = message_fonts[font_index]
    else:
        message_font = DEFAULT_FONT

    # Set the quote text and color
    message = Message(fontpool.find_font(message_font))
    message.add_text(message_text, color=message_color)

    # Scroll the message
    duration = SCROLL_DURATION / 2
    messageboard.animate(message, "Scroll", "in_from_right", duration=duration)
    messageboard.animate(message, "Scroll", "out_to_left", duration=duration)

    if time.monotonic() > last_update + UPDATE_DELAY:
        update_data()
        last_update = time.monotonic()
