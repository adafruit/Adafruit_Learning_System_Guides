# SPDX-FileCopyrightText: 2021 Eva Herrada for Adafruit Industries
# SPDX-License-Identifier: MIT

# General imports

from os import getenv
import gc
import time
import math
import board

# Display imports
import displayio
from adafruit_display_text import label
from adafruit_display_shapes.circle import Circle
from adafruit_display_shapes.line import Line
import adafruit_datetime
from adafruit_bitmap_font import bitmap_font
import framebufferio
import sharpdisplay

# Rotary encoder imports
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.digitalio import DigitalIO
from adafruit_seesaw.rotaryio import IncrementalEncoder

# LED imports
import pwmio

# Adafruit IO imports
import ssl
import socketpool
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT

# Audio imputs
import audiocore
import audiobusio

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


TIMES = {}
ENABLED = {}

ALARM = False
WAIT = 0

LAST = False
LAST_TIME = 0

WARM_PERCENT = 0.0
COOL_PERCENT = 0.0

UTC_OFFSET = -4

days = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday",
}

print(f"Connecting to {ssid}")
wifi.radio.connect(ssid, password)
print(f"Connected to {ssid}!")

# Define callback functions which will be called when certain events happen.
# pylint: disable=unused-argument
def connected(client, userdata, flags, rc):
    print("Connected to Adafruit IO!")
    feeds = [
        "monday",
        "monday-enable",
        "tuesday",
        "tuesday-enable",
        "wednesday",
        "wednesday-enable",
        "thursday",
        "thursday-enable",
        "friday",
        "friday-enable",
        "saturday",
        "saturday-enable",
        "sunday",
        "sunday-enable",
        "alarm",
    ]
    for feed in feeds:
        feed_slug = f"{aio_username}/feeds/alarm-clock." + feed
        print("Subscribed to: alarm-clock." + feed)
        client.subscribe(feed_slug, 1)


def disconnected(client, userdata, rc):  # pylint: disable=unused-argument
    # Disconnected function will be called when the client disconnects.
    print("Disconnected from Adafruit IO!")


displayio.release_displays()


def fade(warm_val, cool_val):
    finished = False
    if warm_val < 100 and cool_val == 0:
        warm_val += 1
        warm.duty_cycle = duty_cycle(warm_val)
    elif warm_val == 100 and cool_val < 100:
        cool_val += 1
        cool.duty_cycle = duty_cycle(cool_val)
    elif cool_val == 100 and warm_val > 0:
        warm_val -= 1
        warm.duty_cycle = duty_cycle(warm_val)
        finished = True
    return warm_val, cool_val, finished


def get(feed_key):
    mqtt_client.publish(f'{aio_username}/feeds/{feed_key}/get', "\0")
    time.sleep(0.1)


def on_iso(client, feed_id, payload):
    timezone = adafruit_datetime.timezone.utc
    timezone._offset = adafruit_datetime.timedelta(seconds=UTC_OFFSET * 3600)
    datetime = adafruit_datetime.datetime.fromisoformat(payload[:-1]).replace(
        tzinfo=timezone
    )
    local_datetime = datetime.tzinfo.fromutc(datetime)
    print(local_datetime)
    dt_hour = local_datetime.hour
    dt_minute = local_datetime.minute
    if not local_datetime.second % 10:
        theta = (dt_hour / 6 + dt_minute / 360) - 0.5
        y_1 = int((72 * math.sin(math.pi * theta)) + 128)
        x_1 = int((72 * math.cos(math.pi * theta)) + 114)
        new_hour = Line(114, 128, x_1, y_1, 0xFFFFFF)
        splash[-3] = new_hour

        theta = (dt_minute / 30) - 0.5
        y_1 = int((96 * math.sin(math.pi * theta)) + 128)
        x_1 = int((96 * math.cos(math.pi * theta)) + 114)
        dt_minute = Line(114, 128, x_1, y_1, 0xFFFFFF)
        splash[-2] = dt_minute

    theta = (local_datetime.second / 30) - 0.5
    y_1 = int((96 * math.sin(math.pi * theta)) + 128)
    x_1 = int((96 * math.cos(math.pi * theta)) + 114)
    new_second = Line(114, 128, x_1, y_1, 0x808080)
    splash[-1] = new_second

    day = days[local_datetime.weekday()]
    alarm_hour, alarm_minute = TIMES[day].split(":")
    if dt_hour == int(alarm_hour):
        if (
            dt_minute == int(alarm_minute)
            and ENABLED[day]
            and not ALARM
            and WAIT < time.monotonic()
        ):
            mqtt_client.publish(
                f"{aio_username}/feeds/alarm-clock.alarm", "True"
            )
            get("alarm-clock.alarm")
    gc.collect()


def on_alarm(client, feed_id, payload):
    global ALARM
    global WAIT
    global LAST
    ALARM = eval(payload)
    if ALARM is False and LAST is True:
        WAIT = time.monotonic() + 60
    LAST = ALARM

    print(f"{feed_id}: {payload}")


def on_time(client, feed_id, payload):
    global TIMES
    TIMES[feed_id.split(".")[-1]] = payload
    print(f"{feed_id}: {payload}")


def on_enable(client, feed_id, payload):
    global ENABLED
    ENABLED[feed_id.split(".")[-1].split("-")[0]] = payload == "ON"
    print(f"{feed_id}: {payload}")


# Set up rotary encoder
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller

seesaw = Seesaw(i2c, addr=0x36)

seesaw_product = (seesaw.get_version() >> 16) & 0xFFFF
print("Found product {}".format(seesaw_product))
if seesaw_product != 4991:
    print("Wrong firmware loaded?  Expected 4991")

button = DigitalIO(seesaw, 24)

encoder = IncrementalEncoder(seesaw)
LAST_POSITION = 0


# Set up display
bus = board.SPI()
chip_select_pin = board.IO12
framebuffer = sharpdisplay.SharpMemoryFramebuffer(bus, chip_select_pin, 400, 240)

display = framebufferio.FramebufferDisplay(framebuffer)

splash = displayio.Group()
display.root_group = splash


# Set up PWM LEDs
WARM_PIN = board.IO5
COOL_PIN = board.IO6


FADE_SLEEP = 0.01  # Number of milliseconds to delay between changes.
# Increase to slow down, decrease to speed up.

# Define PWM outputs:
warm = pwmio.PWMOut(WARM_PIN)
cool = pwmio.PWMOut(COOL_PIN)


def duty_cycle(percent):
    return int(percent / 100.0 * 65535.0)


# Set up UI
def brighten_warm(i):
    global WARM_PERCENT
    WARM_PERCENT = max(min(WARM_PERCENT + float(i * 2), 100), 0)
    warm.duty_cycle = duty_cycle(WARM_PERCENT)


def brighten_cool(i):
    global COOL_PERCENT
    COOL_PERCENT = max(min(COOL_PERCENT + float(i * 2), 100), 0)
    cool.duty_cycle = duty_cycle(COOL_PERCENT)


menu_funcs = [brighten_warm, brighten_cool]
font = bitmap_font.load_font("/fonts/LeagueGothic-Regular-36.bdf")

label1 = label.Label(
    font, text="Warm light", anchor_point=(0, 0.5), anchored_position=(235, 120)
)
splash.append(label1)

label2 = label.Label(
    font, text="Cool light", anchor_point=(0, 0.5), anchored_position=(235, 170)
)
splash.append(label2)

menu = [label1, label2]


# Set up clock
circle = Circle(114, 128, 96, outline=0xFFFFFF)
splash.append(circle)

circle = Circle(114, 128, 3, outline=0xFFFFFF, fill=0xFFFFFF)
splash.append(circle)

twelve = Line(114, 32, 114, 16, 0xFFFFFF)
splash.append(twelve)

for i in range(-2, 9):
    y0 = int((96 * math.sin(math.pi * (i / 6))) + 128)
    x0 = int((96 * math.cos(math.pi * (i / 6))) + 114)
    y1 = int((108 * math.sin(math.pi * (i / 6))) + 128)
    x1 = int((108 * math.cos(math.pi * (i / 6))) + 114)
    hour = Line(x0, y0, x1, y1, 0xFFFFFF)
    splash.append(hour)

hour = Line(114, 128, 114, 128, 0xFFFFFF)
splash.append(hour)

minute = Line(114, 128, 114, 128, 0xFFFFFF)
splash.append(minute)

second = Line(114, 128, 114, 128, 0x808080)
splash.append(second)

time.sleep(1)

# Audio setup
wave_file = open("alarm.wav", "rb")
wave = audiocore.WaveFile(wave_file)

audio = audiobusio.I2SOut(board.IO8, board.IO14, board.IO13)

# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)

# Initialize a new MQTT Client object
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    username=aio_username,
    password=aio_key,
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

# Connect the callback methods defined above to Adafruit IO
mqtt_client.on_connect = connected
mqtt_client.on_disconnect = disconnected


# Connect to Adafruit IO
mqtt_client.connect()

mqtt_client.add_topic_callback("time/ISO-8601", on_iso)

mqtt_client.add_topic_callback(
    f"{aio_username}/feeds/alarm-clock.alarm", on_alarm
)

mqtt_client.add_topic_callback(
    f"{aio_username}/feeds/alarm-clock.sunday", on_time
)
mqtt_client.add_topic_callback(
    f"{aio_username}/feeds/alarm-clock.monday", on_time
)
mqtt_client.add_topic_callback(
    f"{aio_username}/feeds/alarm-clock.tuesday", on_time
)
mqtt_client.add_topic_callback(
    f"{aio_username}/feeds/alarm-clock.wednesday", on_time
)
mqtt_client.add_topic_callback(
    f"{aio_username}/feeds/alarm-clock.thursday", on_time
)
mqtt_client.add_topic_callback(
    f"{aio_username}/feeds/alarm-clock.friday", on_time
)
mqtt_client.add_topic_callback(
    f"{aio_username}/feeds/alarm-clock.saturday", on_time
)

mqtt_client.add_topic_callback(
    f"{aio_username}/feeds/alarm-clock.sunday-enable", on_enable
)
mqtt_client.add_topic_callback(
    f"{aio_username}/feeds/alarm-clock.monday-enable", on_enable
)
mqtt_client.add_topic_callback(
    f"{aio_username}/feeds/alarm-clock.tuesday-enable", on_enable
)
mqtt_client.add_topic_callback(
    f"{aio_username}/feeds/alarm-clock.wednesday-enable", on_enable
)
mqtt_client.add_topic_callback(
    f"{aio_username}/feeds/alarm-clock.thursday-enable", on_enable
)
mqtt_client.add_topic_callback(
    f"{aio_username}/feeds/alarm-clock.friday-enable", on_enable
)
mqtt_client.add_topic_callback(
    f"{aio_username}/feeds/alarm-clock.saturday-enable", on_enable
)


get("alarm-clock.sunday")
get("alarm-clock.monday")
get("alarm-clock.tuesday")
get("alarm-clock.wednesday")
get("alarm-clock.thursday")
get("alarm-clock.friday")
get("alarm-clock.saturday")

get("alarm-clock.sunday-enable")
get("alarm-clock.monday-enable")
get("alarm-clock.tuesday-enable")
get("alarm-clock.wednesday-enable")
get("alarm-clock.thursday-enable")
get("alarm-clock.friday-enable")
get("alarm-clock.saturday-enable")

while len(TIMES) < 7 or len(ENABLED) < 7:
    mqtt_client.loop()

mqtt_client.publish(f"{aio_username}/feeds/alarm-clock.alarm", "False")
mqtt_client.subscribe("time/ISO-8601", 1)

print("Starting")

SELECTED = 0
while True:
    try:
        diff = time.monotonic() - LAST_TIME
        LAST_TIME = time.monotonic()

        if diff > 0.1:
            mqtt_client.loop(0.25)
            if ALARM:
                if WAIT > time.monotonic():
                    print("Alarm ringing")
                    WARM_PERCENT, COOL_PERCENT, done = fade(WARM_PERCENT, COOL_PERCENT)
                    if done and not audio.playing:
                        audio.play(wave)

            position = encoder.position
            if position < LAST_POSITION and button.value:
                SELECTED -= 1
                LAST_POSITION = position
                print("Position: {}".format(position))
                for i in menu:
                    i.y += 50
            if position > LAST_POSITION and button.value:
                SELECTED += 1
                LAST_POSITION = position

                for i in menu:
                    i.y -= 50

            if not button.value:
                if LAST_POSITION != position:
                    menu_funcs[SELECTED](position - LAST_POSITION)
                    LAST_POSITION = position

        else:
            pass
        gc.collect()
    except (ValueError, RuntimeError, ConnectionError, OSError) as err:
        print("Failed to get data, retrying\n", err)
        wifi.reset()
        mqtt_client.reconnect()
        continue
    except MemoryError:
        print("Buffer too large, retrying")
        continue
