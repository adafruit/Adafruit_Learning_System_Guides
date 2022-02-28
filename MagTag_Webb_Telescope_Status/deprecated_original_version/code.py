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
JSON_GET_URL = "https://api.jwst-hub.com/track"

# Whether to fetch live data or use cached
TEST_RUN = False
# Cached data, helpful when developing interface
# pylint: disable=line-too-long
FAKE_DATA = '{"distanceEarthKm":"1103975.4","launchElapsedTime":"15:03:47:44","distanceL2Km":342356.2,"percentageCompleted":76.3291,"speedKmS":0.3778,"deploymentImgURL":"https://webb.nasa.gov/content/webbLaunch/assets/images/deployment/1000pxWide/123Crop.png","currentDeploymentStep":"WEBB IS FULLY DEPLOYED! - The largest, most complex telescope ever launched into space is fully deployed.","tempC":{"tempWarmSide1C":55,"tempWarmSide2C":11,"tempCoolSide1C":-178,"tempCoolSide2C":-200},"timestamp":"2022-01-09T16:07:44.147Z"}'

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


def make_label_text(text, anchor_point, anchored_position):
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
        background_color=LBL_BACKGROUND,
        padding_left=4,
        padding_right=4,
        padding_bottom=3,
        padding_top=3,
    )


def make_value_text(anchor_point, anchored_position, custom_font=True):
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
        _font, text="", anchor_point=anchor_point, anchored_position=anchored_position
    )


# main_group to show things
main_group = displayio.Group()

# initialize custom font
font = bitmap_font.load_font("fonts/LeagueSpartan-Light.bdf")

# value text initialization

# top left
elapsed_time_val = make_value_text(anchor_point=(0, 0), anchored_position=(6, 6))

# top right
distance_from_earth_val = make_value_text(
    anchor_point=(1.0, 0), anchored_position=(display.width - 6, 6)
)

# middle right
distance_to_l2_val = make_value_text(
    anchor_point=(1.0, 0), anchored_position=(display.width - 6, 56)
)

# bottom right
percent_complete_val = make_value_text(
    anchor_point=(1.0, 1.0), anchored_position=(display.width - 6, display.height - 6)
)

# middle left
speed_val = make_value_text(anchor_point=(0, 0), anchored_position=(6, 56))

# bottom left
timestamp_val = make_value_text(
    anchor_point=(0, 1.0), anchored_position=(6, display.height - 6), custom_font=False
)

# center
temperature_val = make_value_text(
    anchor_point=(0.5, 0.0), anchored_position=(display.width // 2, 6)
)

main_group.append(elapsed_time_val)
main_group.append(distance_from_earth_val)
main_group.append(distance_to_l2_val)
main_group.append(percent_complete_val)
main_group.append(speed_val)
main_group.append(timestamp_val)

# label text initialization

# top left
elapsed_time_lbl = make_label_text(
    text="Elapsed", anchor_point=(0.0, 0), anchored_position=(6, 26)
)

# top right
distance_from_earth_lbl = make_label_text(
    text="From Earth", anchor_point=(1.0, 0), anchored_position=(display.width - 6, 26)
)

# middle right
distance_to_l2_lbl = make_label_text(
    text="To L2 Orbit", anchor_point=(1.0, 0), anchored_position=(display.width - 6, 76)
)

# center
temperature_lbl = make_label_text(
    text="Temp", anchor_point=(0.5, 0.0), anchored_position=(display.width // 2, 54)
)

# middle left
speed_lbl = make_label_text(
    text="Speed", anchor_point=(0, 0), anchored_position=(6, 76)
)

main_group.append(elapsed_time_lbl)
main_group.append(distance_from_earth_lbl)
main_group.append(distance_to_l2_lbl)
main_group.append(temperature_lbl)
main_group.append(speed_lbl)
main_group.append(temperature_val)

if not TEST_RUN:
    try:
        print("Fetching JSON data from %s" % JSON_GET_URL)
        response = requests.get(JSON_GET_URL, timeout=30)
    except (RuntimeError, OSError) as e:
        print(e)
        print("Failed GET request. Rebooting in 3 seconds...")
        time.sleep(3)
        supervisor.reload()

    print("-" * 40)
    text_data = response.text
    text_data = text_data.replace('"distanceEarthKm":', '"distanceEarthKm":"').replace(
        ',"launchElapsedTime"', '","launchElapsedTime"'
    )

    json_data = json.loads(text_data)

    print("JSON Response: ", json_data)
    print("-" * 40)
    response.close()
else:
    json_data = json.loads(FAKE_DATA)

# update the labels to display values
elapsed_time_val.text = json_data["launchElapsedTime"]
distance_from_earth_val.text = "{}km".format(json_data["distanceEarthKm"])
distance_to_l2_val.text = "{}km".format(str(json_data["distanceL2Km"]))
percent_complete_val.text = "{}%".format(str(json_data["percentageCompleted"]))
speed_val.text = "{}km/s".format(str(json_data["speedKmS"]))
timestamp_val.text = str(json_data["timestamp"])
temperature_val.text = "{}c | {}c\n{}c | {}c".format(
    json_data["tempC"]["tempWarmSide1C"],
    json_data["tempC"]["tempCoolSide1C"],
    json_data["tempC"]["tempWarmSide2C"],
    json_data["tempC"]["tempCoolSide2C"],
)

# show the group
display.show(main_group)

# refresh display
try_refresh()

# Create a an alarm that will trigger to wake us up
time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + SLEEP_TIME)

# Exit the program, and then deep sleep until the alarm wakes us.
alarm.exit_and_deep_sleep_until_alarms(time_alarm)
# Does not return, so we never get here.
