# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2021 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import digitalio
import analogio
from adafruit_display_shapes.circle import Circle
from adafruit_funhouse import FunHouse

BOWL_STATE_TOPIC = "funhouse/catbowl/state"
LOW_VALUE = 4000
EMPTY_VALUE = 2000
UPDATE_INTERVAL = 1800	# Every 30 minutes

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Text labels for the Display
states = {
    "empty": "Add Water",
    "low": "Low",
    "full": "Full",
}

def publish_bowl_state(bowl_state):
    funhouse.peripherals.led = True
    # Publish the Bowl Level State
    print("Publishing to {}".format(BOWL_STATE_TOPIC))
    funhouse.network.mqtt_publish(BOWL_STATE_TOPIC, bowl_state)
    funhouse.peripherals.led = False

def connected(client, userdata, result, payload):
    status.fill = 0x00FF00
    status.outline = 0x008800

def disconnected(client):
    status.fill = 0xFF0000
    status.outline = 0x880000

def get_bowl_reading():
    water_enable.value = True
    level = water_level_sensor.value
    water_enable.value = False
    return level

def get_bowl_state(level):
    if level <= EMPTY_VALUE:
        return "empty"
    elif level <= LOW_VALUE:
        return "low"
    return "full"

def bowl_level_display(water_level):
    if funhouse.peripherals.button_sel:
        return water_level
    return states[get_bowl_state(water_level)]

# Set Initial States
funhouse = FunHouse(default_bg=0x0F0F00)
funhouse.peripherals.dotstars.fill(0)
water_enable = digitalio.DigitalInOut(board.A0)
water_enable.switch_to_output()
water_level_sensor = analogio.AnalogIn(board.A1)
funhouse.display.show(None)
funhouse.add_text(
    text="Bowl Level:",
    text_position=(120, 60),
    text_anchor_point=(0.5, 0.5),
    text_color=0xFF0000,
    text_font="fonts/Arial-Bold-24.pcf",
)
level_label = funhouse.add_text(
    text_position=(120, 100),
    text_anchor_point=(0.5, 0.5),
    text_color=0xFFFF00,
    text_font="fonts/Arial-Bold-24.pcf",
)
funhouse.display.show(funhouse.splash)

status = Circle(229, 10, 10, fill=0xFF0000, outline=0x880000)
funhouse.splash.append(status)

# Initialize a new MQTT Client object
funhouse.network.init_mqtt(
    secrets["mqtt_broker"],
    secrets["mqtt_port"],
    secrets["mqtt_username"],
    secrets["mqtt_password"],
)
funhouse.network.on_mqtt_connect = connected
funhouse.network.on_mqtt_disconnect = disconnected

print("Attempting to connect to {}".format(secrets["mqtt_broker"]))
funhouse.network.mqtt_connect()

last_reading_timestamp = None
last_bowl_state = None

while True:
    if last_reading_timestamp is None or time.monotonic() > last_reading_timestamp + UPDATE_INTERVAL:
        # Take Reading
        water_level = get_bowl_reading()
        # Update Display
        funhouse.set_text(bowl_level_display(water_level), level_label)
        # If changed, publish new result
        bowl_state = get_bowl_state(water_level)
        if bowl_state != last_bowl_state:
            publish_bowl_state(bowl_state)
            last_bowl_state = bowl_state
        last_reading_timestamp = time.monotonic()
