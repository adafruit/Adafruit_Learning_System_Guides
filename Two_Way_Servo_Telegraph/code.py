# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

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

#  select which display is running the code
servo_one = True
#  servo_two = True

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise
#  connect to adafruitio
aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]

print("Connecting to %s" % secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s!" % secrets["ssid"])

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
        # if no feed exists, create one
        out_feed = io.create_new_feed("touch-1")
        in_feed = io.create_new_feed("touch-2")
#  setup for display 2
if servo_two:
    CALIB_MIN = 15668
    CALIB_MAX = 43550
    try:
        # get feed
        out_feed = io.get_feed("touch-2")
        in_feed = io.get_feed("touch-1")
    except AdafruitIO_RequestError:
        # if no feed exists, create one
        out_feed = io.create_new_feed("touch-2")
        in_feed = io.create_new_feed("touch-1")

received_data = io.receive_data(in_feed["key"])

# Pin setup
SERVO_PIN = board.A1
FEEDBACK_PIN = board.A2
touch = touchio.TouchIn(board.TX)

#  angles for servo
ANGLE_MIN = 0
ANGLE_MAX = 180

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
