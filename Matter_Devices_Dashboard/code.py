# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import os
import ssl
import wifi
import socketpool
import microcontroller
import board
import digitalio
import displayio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import bitmap_label
from adafruit_display_shapes.circle import Circle
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
import adafruit_minimqtt.adafruit_minimqtt as MQTT

aio_username = os.getenv("ADAFRUIT_AIO_USERNAME")
aio_key = os.getenv("ADAFRUIT_AIO_KEY")

# feeds!
temp_feed = aio_username + "/feeds/eve-temp" # temperature sensor
humid_feed = aio_username + "/feeds/eve-humid" # humidity sensor
lux_feed = aio_username + "/feeds/eve-light" # lux sensor
occupy_feed = aio_username + "/feeds/eve-occupy" # occupation sensor
light_feed = aio_username + "/feeds/nanoleaf" # lightstrip

# buttons
button0 = digitalio.DigitalInOut(board.D0)
button0.direction = digitalio.Direction.INPUT
button0.pull = digitalio.Pull.UP
button0_state = False
button1 = digitalio.DigitalInOut(board.D1)
button1.direction = digitalio.Direction.INPUT
button1.pull = digitalio.Pull.DOWN
button1_state = False
button2 = digitalio.DigitalInOut(board.D2)
button2.direction = digitalio.Direction.INPUT
button2.pull = digitalio.Pull.DOWN
button2_state = False

display = board.DISPLAY
group = displayio.Group()
display.root_group = group

# load background bitmap
bitmap = displayio.OnDiskBitmap("/tft_bg.bmp")
tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
group = displayio.Group()
group.append(tile_grid)

# bitmap font
font_file = "/roundedHeavy-26.bdf"
font = bitmap_font.load_font(font_file)
# text elements
temp_text = bitmap_label.Label(font, text="00.0°C", x=55, y=70, color=0xFFFFFF)
group.append(temp_text)
humid_text = bitmap_label.Label(font, text="00.0%", x=120, y=70, color=0xFFFFFF)
group.append(humid_text)
lux_text = bitmap_label.Label(font, text="00 lx", x=190, y=70, color=0xFFFFFF)
group.append(lux_text)
occupy_text = bitmap_label.Label(font, text="Occupied?", x=128,
                                 y=display.height - 12, color=0xFFFFFF)
group.append(occupy_text)
onOff_circ = Circle(display.width - 12, display.height - 12, 10, fill=0xcc0000)
group.append(onOff_circ)
scene_select = RoundRect(0, 0, 42, 40, 8, fill=None, outline=0xcccc00, stroke=6)
scene_y = [0, int(display.height / 2) - int(scene_select.height / 2),
           display.height - scene_select.height - 1]
group.append(scene_select)

display.root_group = group
print()
print("Connecting to WiFi...")
#  connect to your SSID
wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
print("Connected to WiFi!")

# pylint: disable=unused-argument
# Define callback methods which are called when events occur
def connected(client, userdata, flags, rc): # pylint: disable=unused-argument
    # This function will be called when the client is connected
    # successfully to the broker.
    print("Connected to Adafruit IO!")
    # Subscribe to all changes on feeds
    client.subscribe(temp_feed)
    client.subscribe(humid_feed)
    client.subscribe(lux_feed)
    client.subscribe(occupy_feed)
    client.subscribe(light_feed)

def disconnected(client, userdata, rc): # pylint: disable=unused-argument
    # This method is called when the client is disconnected
    print("Disconnected from Adafruit IO!")

def on_message(client, topic, msg): # pylint: disable=unused-argument
    # This method is called when a topic the client is subscribed to
    # has a new message.
    print(f"New message on topic {topic}")

def on_temp_msg(client, topic, msg):
    print(f"temp feed data: {msg}°C")
    temp_text.text = f"{float(msg):.01f}°C"

def on_humid_msg(client, topic, msg):
    print(f"humid feed data: {msg}%")
    humid_text.text = f"{float(msg):.01f}%"

def on_lux_msg(client, topic, msg):
    print(f"lux feed data: {msg} lx")
    lux_text.text = f"{float(msg):.00f} lx"

def on_occupy_msg(client, topic, msg):
    print(f"occupation feed data: {msg}")
    if msg == "1":
        onOff_circ.fill = 0x00cc00
    else:
        onOff_circ.fill = 0xcc0000

def on_light_msg(client, topic, msg):
    print(f"light scene selected: {msg}")
    scene_select.y = scene_y[int(msg)]

pool = socketpool.SocketPool(wifi.radio)
ssl_context = ssl.create_default_context()
# Initialize an Adafruit IO HTTP API object
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    port=1883,
    username=aio_username,
    password=aio_key,
    socket_pool=pool,
    ssl_context=ssl_context,
)
# Setup the callback methods above
mqtt_client.on_connect = connected
mqtt_client.on_disconnect = disconnected
mqtt_client.on_message = on_message
mqtt_client.add_topic_callback(temp_feed, on_temp_msg)
mqtt_client.add_topic_callback(humid_feed, on_humid_msg)
mqtt_client.add_topic_callback(lux_feed, on_lux_msg)
mqtt_client.add_topic_callback(occupy_feed, on_occupy_msg)
mqtt_client.add_topic_callback(light_feed, on_light_msg)

# Connect the client to the MQTT broker.
print("Connecting to Adafruit IO...")
mqtt_client.connect()

clock_clock = ticks_ms()
clock_timer = 5 * 1000

while True:
    try:
        if ticks_diff(ticks_ms(), clock_clock) >= clock_timer:
            mqtt_client.loop(timeout=1)
            clock_clock = ticks_add(clock_clock, clock_timer)
        # reset button state on release
        if button0.value and button0_state:
            button0_state = False
        if not button1.value and button1_state:
            button1_state = False
        if not button2.value and button2_state:
            button2_state = False
        # buttons change light scenes
        if not button0.value and not button0_state:
            mqtt_client.publish(light_feed, 0)
            scene_select.y = scene_y[0]
            button0_state = True
        if button1.value and not button1_state:
            mqtt_client.publish(light_feed, 1)
            scene_select.y = scene_y[1]
            button1_state = True
        if button2.value and not button2_state:
            mqtt_client.publish(light_feed, 2)
            scene_select.y = scene_y[2]
            button2_state = True
    except Exception as error: # pylint: disable=broad-except
        print(error)
        mqtt_client.disconnect()
        time.sleep(5)
        microcontroller.reset()
