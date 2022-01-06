# SPDX-FileCopyrightText: 2021 Eva Herrada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import ssl
import displayio
import board
from digitalio import DigitalInOut, Direction, Pull
from adafruit_display_text.label import Label
import terminalio
import touchio
import socketpool
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT
from adafruit_dash_display import Hub

# Set up navigation buttons
up = DigitalInOut(board.BUTTON_UP)
up.direction = Direction.INPUT
up.pull = Pull.DOWN

select = DigitalInOut(board.BUTTON_SELECT)
select.direction = Direction.INPUT
select.pull = Pull.DOWN

down = DigitalInOut(board.BUTTON_DOWN)
down.direction = Direction.INPUT
down.pull = Pull.DOWN

back = touchio.TouchIn(board.CAP7)
submit = touchio.TouchIn(board.CAP8)

# Check for secrets.py. Note: for this project, your secrets.py needs an adafruit io api key as
# well as the wifi information
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Make the rgb group for setting rgb hex values for NeoPixels
rgb_group = displayio.Group()
R_label = Label(
    terminalio.FONT,
    text="   +\nR:\n   -",
    color=0xFFFFFF,
    anchor_point=(0, 0.5),
    anchored_position=(5, 120),
    scale=2,
)
G_label = Label(
    terminalio.FONT,
    text="   +\nG:\n   -",
    color=0xFFFFFF,
    anchor_point=(0, 0.5),
    anchored_position=(90, 120),
    scale=2,
)
B_label = Label(
    terminalio.FONT,
    text="   +\nB:\n   -",
    color=0xFFFFFF,
    anchor_point=(0, 0.5),
    anchored_position=(175, 120),
    scale=2,
)
rgb_group.append(R_label)
rgb_group.append(G_label)
rgb_group.append(B_label)
R = Label(
    terminalio.FONT,
    text="00",
    color=0xFFFFFF,
    anchor_point=(0, 0.5),
    anchored_position=(35, 120),
    scale=2,
)
G = Label(
    terminalio.FONT,
    text="00",
    color=0xFFFFFF,
    anchor_point=(0, 0.5),
    anchored_position=(120, 120),
    scale=2,
)
B = Label(
    terminalio.FONT,
    text="00",
    color=0xFFFFFF,
    anchor_point=(0, 0.5),
    anchored_position=(205, 120),
    scale=2,
)
rgb_group.append(R)
rgb_group.append(G)
rgb_group.append(B)

# Set up callbacks

# pylint: disable=unused-argument
def rgb(last):
    """ Function for when the rgb screen is active """
    display.show(None)
    rgb_group[3].text = "00"
    rgb_group[4].text = "00"
    rgb_group[5].text = "00"
    display.show(rgb_group)
    time.sleep(0.2)
    index = 0
    colors = [00, 00, 00]

    while True:
        if select.value:
            index += 1
            if index == 3:
                index = 0
            time.sleep(0.3)
            continue

        if up.value:
            colors[index] += 1
            if colors[index] == 256:
                colors[index] = 0
            rgb_group[index + 3].text = hex(colors[index])[2:]
            time.sleep(0.01)
            continue

        if down.value:
            colors[index] -= 1
            if colors[index] == -1:
                colors[index] = 255
            rgb_group[index + 3].text = hex(colors[index])[2:]
            time.sleep(0.01)
            continue

        if submit.value:
            color = ["{:02x}".format(colors[i]) for i in range(len(colors))]
            color = "#" + "".join(color)
            iot.publish("neopixel", color)
            break

        if back.value:
            break
        time.sleep(0.1)

    display.show(None)
    time.sleep(0.1)

def rgb_set_color(message):
    """ Sets the color of the rgb label based on the value of the feed """
    return int(message[1:], 16)

def door_color(message):
    """ Sets the color of the door label based on the value of the feed """
    door = bool(int(message))
    if door:
        return int(0x00FF00)
    return int(0xFF0000)

def on_door(client, feed_id, message):
    """ Sets the door text based on the value of the feed """
    door = bool(int(message))
    if door:
        return "Door: Closed"
    return "Door: Open"

def pub_lamp(lamp):
    if isinstance(lamp, str):
        lamp = eval(lamp)  # pylint: disable=eval-used
    iot.publish("lamp", str(not lamp))
    # funhouse.set_text(f"Lamp: {not lamp}", 0)
    time.sleep(0.3)

display = board.DISPLAY

# Set your Adafruit IO Username and Key in secrets.py
# (visit io.adafruit.com if you need to create an account,
# or if you need your Adafruit IO key.)
aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]

print("Connecting to %s" % secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s!" % secrets["ssid"])

# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)

# Initialize a new MQTT Client object
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    username=secrets["aio_username"],
    password=secrets["aio_key"],
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

# Initialize an Adafruit IO MQTT Client
io = IO_MQTT(mqtt_client)

iot = Hub(display=display, io=io, nav=(up, select, down, back, submit))

iot.add_device(
    feed_key="lamp",
    default_text="Lamp: ",
    formatted_text="Lamp: {}",
    pub_method=pub_lamp,
)
iot.add_device(
    feed_key="temperature",
    default_text="Temperature: ",
    formatted_text="Temperature: {:.1f} C",
)
iot.add_device(
    feed_key="humidity", default_text="Humidity: ", formatted_text="Humidity: {:.2f}%"
)
iot.add_device(
    feed_key="neopixel",
    default_text="LED: ",
    formatted_text="LED: {}",
    color_callback=rgb_set_color,
    pub_method=rgb,
)
iot.add_device(
    feed_key="battery",
    default_text="Battery: ",
    formatted_text="Battery: {}%",
)
iot.add_device(
    feed_key="door",
    default_text="Door: ",
    formatted_text="Door: {}",
    color_callback=door_color,
    callback=on_door,
    )

iot.get()

while True:
    iot.loop()
    time.sleep(0.01)
