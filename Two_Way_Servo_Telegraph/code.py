# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

from os import getenv
import time
import ssl
import board
import touchio
import pwmio
from analogio import AnalogIn
import adafruit_requests
import socketpool
import wifi
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError
from simpleio import map_range
from adafruit_motor import servo

# Get WiFi details and Adafruit IO keys, ensure these are setup in settings.toml
# (visit io.adafruit.com if you need to create an account, or if you need your Adafruit IO key.)
ssid = getenv("CIRCUITPY_WIFI_SSID")
password = getenv("CIRCUITPY_WIFI_PASSWORD")
aio_username = getenv("ADAFRUIT_AIO_USERNAME")
aio_key = getenv("ADAFRUIT_AIO_KEY")

if None in [ssid, password, aio_username, aio_key]:
    raise RuntimeError(
        "WiFi and Adafruit IO settings are kept in settings.toml, "
        "please add them there. The settings file must contain "
        "'CIRCUITPY_WIFI_SSID', 'CIRCUITPY_WIFI_PASSWORD', "
        "'ADAFRUIT_AIO_USERNAME' and 'ADAFRUIT_AIO_KEY' at a minimum."
    )

#  select which display is running the code
servo_one = True
#  servo_two = True

#  angles for servo
ANGLE_MIN = 0
ANGLE_MAX = 180

print(f"Connecting to {ssid}")
wifi.radio.connect(ssid, password)
print(f"Connected to {ssid}!")

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
# Initialize an Adafruit IO HTTP API object
io = IO_HTTP(aio_username, aio_key, requests)

#  pylint: disable=undefined-variable
#  disabling undefined-variable for ease of comment/uncomment
#  servo_one or servo_two at top for user

#  setup for display 1
if servo_one:
    #  servo calibration values
    CALIB_MIN = 15708
    CALIB_MAX = 43968
    #  create feeds
    try:
        # get feed
        out_feed = io.get_feed("touch-1")
        in_feed = io.get_feed("touch-2")
    except AdafruitIO_RequestError:
        # if no feed exists, create one and push the first value
        out_feed = io.create_new_feed("touch-1")
        in_feed = io.create_new_feed("touch-2")
        io.send_data(in_feed["key"], float(abs((ANGLE_MAX-ANGLE_MIN)/2)))
#  setup for display 2
if servo_two:
    CALIB_MIN = 15668
    CALIB_MAX = 43550
    try:
        # get feed
        out_feed = io.get_feed("touch-2")
        in_feed = io.get_feed("touch-1")
    except AdafruitIO_RequestError:
        # if no feed exists, create one and push the first value
        out_feed = io.create_new_feed("touch-2")
        in_feed = io.create_new_feed("touch-1")
        io.send_data(in_feed["key"], float(abs((ANGLE_MAX-ANGLE_MIN)/2)))

received_data = io.receive_data(in_feed["key"])

# Pin setup
SERVO_PIN = board.A1
FEEDBACK_PIN = board.A2
touch = touchio.TouchIn(board.TX)

# servo setup
pwm = pwmio.PWMOut(SERVO_PIN, duty_cycle=2 ** 15, frequency=50)
servo = servo.Servo(pwm)
servo.angle = None

# setup feedback
feedback = AnalogIn(FEEDBACK_PIN)

#  position finder function for servo
def get_position():
    return map_range(feedback.value, CALIB_MIN, CALIB_MAX, ANGLE_MIN, ANGLE_MAX)

#  touch debounce
touch_state = False
#  new_msg value
new_msg = None
#  last_msg value
last_msg = None
#  time.monotonic() holder for pinging IO
clock = 5

while True:
    #  check IO for new data every 5 seconds
    if (time.monotonic() - clock) > 5:
        #  get data
        received_data = io.receive_data(in_feed["key"])
        #  reset clock
        clock = time.monotonic()
    #  if touched...
    if touch.value and touch_state is False:
        touch_state = True
    #  when touch is released...
    if not touch.value and touch_state is True:
        #  get position of servo
        pos = get_position()
        #  send position to IO
        io.send_data(out_feed["key"], float(pos))
        #  delay to settle
        time.sleep(1)
        #  reset touch state
        touch_state = False
    #  if a new value is detected
    if float(received_data["value"]) != last_msg:
        #  assign value to new_msg
        new_msg = float(received_data["value"])
        #  set servo angle
        servo.angle = new_msg
        #  quick delay to settle
        time.sleep(1)
        #  release servo
        servo.angle = None
        #  log msg
        last_msg = new_msg
