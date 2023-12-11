# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
import time
import random
import alarm
import terminalio
from adafruit_magtag.magtag import MagTag

# Set up where we'll be fetching data from
DATA_SOURCE = (
    "https://raw.githubusercontent.com/codyogden/killedbygoogle/main/graveyard.json"
)

# Get the MagTag ready
MAGTAG = MagTag()
MAGTAG.peripherals.neopixel_disable = True
MAGTAG.set_background("/bmps/background.bmp")
MAGTAG.network.connect()

# Prepare the three text fields
MAGTAG.add_text(
    text_font="/fonts/Deutsch-Gothic-14.bdf",
    text_position=(55, 60,),
    text_wrap=14,
    text_anchor_point=(0.5, 0.5),
    text_scale=1,
    line_spacing=0.9,
    is_data=False,
)

MAGTAG.add_text(
    text_font="/fonts/Deutsch-Gothic-14.bdf",
    text_position=(55, 85,),
    text_anchor_point=(0.5, 0.5),
    text_scale=1,
    is_data=False,
)

MAGTAG.add_text(
    text_font=terminalio.FONT,
    text_position=(115, 15,),
    text_wrap=29,
    text_anchor_point=(0, 0),
    text_scale=1,
    line_spacing=1.0,
    is_data=False,
)

MAGTAG.preload_font()  # preload characters

SONG = (
    (330, 1),
    (370, 1),
    (392, 2),
    (370, 2),
    (330, 2),
    (330, 1),
    (370, 1),
    (392, 1),
    (494, 1),
    (370, 1),
    (392, 1),
    (330, 2),
)

while True:
    try:
        # Get the response and turn it into json
        RESPONSE = MAGTAG.network.requests.get(DATA_SOURCE)
        VALUE = RESPONSE.json()

        # Choose a random project to display
        PROJECT = VALUE[random.randint(0, len(VALUE) - 1)]

        # Prepare the text to be displayed
        CLOSED = PROJECT["dateClose"].split("-")
        CLOSED.reverse()
        CLOSED = "/".join(CLOSED)

        print(PROJECT["name"])

        # Display the text
        MAGTAG.set_text(PROJECT["name"], 0, False)
        MAGTAG.set_text(CLOSED, 1, False)
        MAGTAG.set_text(PROJECT["description"], 2)

        # Play a song
        for notepair in SONG:
            MAGTAG.peripherals.play_tone(notepair[0], notepair[1] * 0.2)

        # Put the board to sleep for an hour
        time.sleep(2)
        print("Sleeping")
        PAUSE = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 60 * 60)
        alarm.exit_and_deep_sleep_until_alarms(PAUSE)

    except (ValueError, RuntimeError, ConnectionError, OSError) as e:
        print("Some error occured, retrying! -", e)
