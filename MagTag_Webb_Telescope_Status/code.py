# SPDX-FileCopyrightText: 2022 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
MagTag status display for James Webb Telescope
"""
import time
import json
import ssl
import board
import displayio
import terminalio
import supervisor
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import bitmap_label
import wifi
import socketpool
import alarm
import adafruit_requests as requests

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Update once per hour
SLEEP_TIME = 60 * 60  # seconds

# Update once per day
# SLEEP_TIME = 60 * 60 * 24 # seconds

# URL to fetch the data from
JSON_GET_URL = (
    "https://jwst.nasa.gov/content/webbLaunch/flightCurrentState2.0.json?unique={}"
)

# Whether to fetch live data or use cached
TEST_RUN = True
# Cached data, helpful when developing interface
# pylint: disable=line-too-long
FAKE_DATA = '{"currentState": {"STEPS": "MirrorAlignSteps, TempBlurb, MirrorBlurb, ArraysForPlots, Plots", "launchDateTimeString": "2021-12-25T12:20Z", "currentDeployTableIndex": 34, "tempWarmSide1C": 37.1, "tempWarmSide2C": 12.0, "tempCoolSide1C": -229.1, "tempCoolSide2C": -233.0, "---INST TEMPS IN KELVIN----": "", "tempInstNirCamK": 42.7, "tempInstNirSpecK": 39.9, "tempInstFgsNirissK": 47.3, "tempInstMiriK": 108.7, "tempInstFsmK": 37.1, "tempsShow": true, "last": ""}}'

# Background Color for the label texts
LBL_BACKGROUND = 0x444444


def try_refresh():
    """Attempt to refresh the display. Catch 'refresh too soon' error
    and retry after waiting 10 seconds.
    """
    try:
        board.DISPLAY.refresh()
    except RuntimeError as too_soon_error:
        # catch refresh too soon
        print(too_soon_error)
        print("waiting before retry refresh()")
        time.sleep(10)
        board.DISPLAY.refresh()


# Get the display object
display = board.DISPLAY

if not TEST_RUN:
    print("Connecting to AP...")
    try:
        # wifi connect
        wifi.radio.connect(secrets["ssid"], secrets["password"])

        # Create Socket, initialize requests
        socket = socketpool.SocketPool(wifi.radio)
        requests = requests.Session(socket, ssl.create_default_context())
    except OSError:
        print("Failed to connect to AP. Rebooting in 3 seconds...")
        time.sleep(3)
        supervisor.reload()


def get_time_str():
    return str(time.monotonic()).replace(".", "")


def make_name_text(text, anchor_point, anchored_position, bg_color=LBL_BACKGROUND):
    """
    Create label object for labeling data values.
    It will get a background color box and appropriate padding.

    :param text: Text to show
    :param anchor_point: location anchor_point
    :param anchored_position: location anchored_position
    :return bitmap_label.Label: the Label object
    """
    return bitmap_label.Label(
        font,
        text=text,
        anchor_point=anchor_point,
        anchored_position=anchored_position,
        background_color=bg_color,
        padding_left=4,
        padding_right=4,
        padding_bottom=3,
        padding_top=3,
        line_spacing=1.0,
    )


def make_value_text(
    anchor_point,
    anchored_position,
    custom_font=True,
    bg_color=0x000000,
    font_color=0xFFFFF,
):
    """
    Create label object for showing data values.

    :param anchor_point: location anchor_point
    :param anchored_position: location anchored_position
    :param bool custom_font: weather to use the custom font or system font
    :return bitmap_label.Label: the Label object
    """
    if custom_font:
        _font = font
    else:
        _font = terminalio.FONT
    return bitmap_label.Label(
        _font,
        text="",
        anchor_point=anchor_point,
        anchored_position=anchored_position,
        line_spacing=1.0,
        padding_top=3,
        background_color=bg_color,
        color=font_color,
        padding_right=4,
        padding_left=4,
        padding_bottom=4,
    )


# main_group to show things
main_group = displayio.Group()

# initialize custom font
font = bitmap_font.load_font("fonts/LeagueSpartan-Light.bdf")

# value text initializations

# top left. Hot side | Cold side temperature values
top_left_value = make_value_text(
    anchor_point=(0, 0),
    anchored_position=(0, 6),
    bg_color=0xBBBBBB,
    font_color=0x000000,
)

# top right. Instrument temperature values
top_right_value = make_value_text(
    anchor_point=(1.0, 0),
    anchored_position=(display.width - 6, 6),
)

# bottom left timestamp
timestamp_val = make_value_text(
    anchor_point=(0, 1.0), anchored_position=(0, display.height - 6), custom_font=False
)

main_group.append(top_left_value)
main_group.append(top_right_value)

main_group.append(timestamp_val)

# label text initialization

# middle left. Hot side | Cold side temps label
middle_left_name = make_name_text(
    text="Temperature", anchor_point=(0.0, 0), anchored_position=(0, 51)
)

# center. Instrument temp labels
inst_temp_labels = "NIRCam Bench\nNIRSpec Bench\nFGS Bench\nMIRI Bench\nFSM"
top_center_name = make_name_text(
    text=inst_temp_labels,
    anchor_point=(1.0, 0.0),
    anchored_position=(top_right_value.x - 2, 6),
)

main_group.append(middle_left_name)
main_group.append(top_center_name)

if not TEST_RUN:
    try:
        print("Fetching JSON data from {}".format(JSON_GET_URL.format(get_time_str())))
        response = requests.get(JSON_GET_URL.format(get_time_str()), timeout=30)
    except (RuntimeError, OSError) as e:
        print(e)
        print("Failed GET request. Rebooting in 3 seconds...")
        time.sleep(3)
        supervisor.reload()

    print("-" * 40)
    print(response.headers)
    json_data = response.json()
    _time_parts = response.headers["date"].split(" ")
    _time_str = "{}\n{}".format(" ".join(_time_parts[:4]), " ".join(_time_parts[4:]))

    print("JSON Response: ", json_data)
    print("-" * 40)
    response.close()
else:
    json_data = json.loads(FAKE_DATA)
    _time_parts = ["Mon,", "28", "Feb", "2022", "17:17:54 GMT"]
    _time_str = "{}\n{}".format(" ".join(_time_parts[:4]), " ".join(_time_parts[4:]))

# Date/Time
timestamp_val.text = _time_str

# instrument temps
top_right_value.text = "{}K\n{}K\n{}K\n{}K\n{}K".format(
    json_data["currentState"]["tempInstNirCamK"],
    json_data["currentState"]["tempInstNirSpecK"],
    json_data["currentState"]["tempInstFgsNirissK"],
    json_data["currentState"]["tempInstMiriK"],
    json_data["currentState"]["tempInstFsmK"],
)

# hot side | cold site temps
top_left_value.text = "{}C | {}C\n{}C | {}C".format(
    json_data["currentState"]["tempWarmSide1C"],
    json_data["currentState"]["tempCoolSide1C"],
    json_data["currentState"]["tempWarmSide2C"],
    json_data["currentState"]["tempCoolSide2C"],
)

# Set the name position after the instrument temps are in the value
# label, so that it's x will be in the proper position.
top_center_name.anchored_position = (top_right_value.x - 2, 6)

# show the group
display.show(main_group)

# refresh display
try_refresh()

# Create a an alarm that will trigger to wake us up
time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + SLEEP_TIME)

# Exit the program, and then deep sleep until the alarm wakes us.
alarm.exit_and_deep_sleep_until_alarms(time_alarm)
# Does not return, so we never get here.
