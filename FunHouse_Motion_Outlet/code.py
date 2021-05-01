# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2021 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import digitalio
from adafruit_display_shapes.circle import Circle
from adafruit_funhouse import FunHouse

OUTLET_STATE_TOPIC = "funhouse/outlet/state"
OUTLET_COMMAND_TOPIC = "funhouse/outlet/set"
MOTION_TIMEOUT = 300  # Timeout in seconds

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

def set_outlet_state(value):
    global last_pir_timestamp
    if value:
        funhouse.peripherals.dotstars.fill(0x00FF00)
        last_pir_timestamp = time.monotonic()
    else:
        funhouse.peripherals.dotstars.fill(0xFF0000)
        last_pir_timestamp = time.monotonic() - MOTION_TIMEOUT

    outlet.value = value
    publish_outlet_state()

def publish_outlet_state():
    if OUTLET_STATE_TOPIC and OUTLET_COMMAND_TOPIC:
        funhouse.peripherals.led = True
        output = "on" if outlet.value else "off"
        # Publish the Dotstar State
        print("Publishing to {}".format(OUTLET_STATE_TOPIC))
        funhouse.network.mqtt_publish(OUTLET_STATE_TOPIC, output)
        funhouse.peripherals.led = False

def connected(client, userdata, result, payload):
    status.fill = 0x00FF00
    status.outline = 0x008800
    print("Connected to MQTT! Subscribing...")
    client.subscribe(OUTLET_COMMAND_TOPIC)

def disconnected(client):
    status.fill = 0xFF0000
    status.outline = 0x880000

def message(client, topic, payload):
    print("Topic {0} received new value: {1}".format(topic, payload))
    if topic == OUTLET_COMMAND_TOPIC:
        set_outlet_state(payload == "on")

def timeleft():
    seconds = int(last_pir_timestamp + MOTION_TIMEOUT - time.monotonic())
    if outlet.value and seconds >= 0:
        minutes = seconds // 60
        seconds -= minutes * 60
        return "{:01}:{:02}".format(minutes, seconds)
    return "Off"    

# Set Initial States
funhouse = FunHouse(default_bg=0x0F0F00)
funhouse.peripherals.dotstars.fill(0)
outlet = digitalio.DigitalInOut(board.A0)
outlet.direction = digitalio.Direction.OUTPUT
last_pir_timestamp = None
funhouse.display.show(None)
funhouse.add_text(
    text="Timeout Left:",
    text_position=(20, 60),
    text_color=0xFF0000,
    text_font="fonts/Arial-Bold-24.pcf",
)
countdown_label = funhouse.add_text(
    text_position=(120, 100),
    text_anchor_point=(0.5, 0.5),
    text_color=0xFFFF00,
    text_font="fonts/Arial-Bold-24.pcf",
)
funhouse.display.show(funhouse.splash)

status = Circle(229, 10, 10, fill=0xFF0000, outline=0x880000)
funhouse.splash.append(status)

# Initialize a new MQTT Client object
if OUTLET_STATE_TOPIC and OUTLET_COMMAND_TOPIC:
    funhouse.network.init_mqtt(
        secrets["mqtt_broker"],
        secrets["mqtt_port"],
        secrets["mqtt_username"],
        secrets["mqtt_password"],
    )
    funhouse.network.on_mqtt_connect = connected
    funhouse.network.on_mqtt_disconnect = disconnected
    funhouse.network.on_mqtt_message = message

    print("Attempting to connect to {}".format(secrets["mqtt_broker"]))
    funhouse.network.mqtt_connect()
set_outlet_state(False)

while True:
    if funhouse.peripherals.pir_sensor:
        last_pir_timestamp = time.monotonic()
        if not outlet.value:
            set_outlet_state(True)
    if outlet.value and time.monotonic() >= last_pir_timestamp + MOTION_TIMEOUT:
        set_outlet_state(False)
    funhouse.set_text(timeleft(), countdown_label) 
    # Check any topics we are subscribed to
    funhouse.network.mqtt_loop(0.5)
