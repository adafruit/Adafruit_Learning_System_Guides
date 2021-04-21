# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2021 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import time
import json
from adafruit_display_shapes.circle import Circle
from adafruit_funhouse import FunHouse

PUBLISH_DELAY = 60
ENVIRONMENT_CHECK_DELAY = 5
ENABLE_PIR = True
MQTT_TOPIC = "funhouse/state"
LIGHT_STATE_TOPIC = "funhouse/light/state"
LIGHT_COMMAND_TOPIC = "funhouse/light/set"
INITIAL_LIGHT_COLOR = 0x008000
USE_FAHRENHEIT = True

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

funhouse = FunHouse(default_bg=0x0F0F00)
funhouse.peripherals.dotstars.fill(INITIAL_LIGHT_COLOR)

funhouse.display.show(None)
funhouse.add_text(
    text="Temperature:",
    text_position=(20, 30),
    text_color=0xFF8888,
    text_font="fonts/Arial-Bold-24.pcf",
)
temp_label = funhouse.add_text(
    text_position=(120, 60),
    text_anchor_point=(0.5, 0.5),
    text_color=0xFFFF00,
    text_font="fonts/Arial-Bold-24.pcf",
)
funhouse.add_text(
    text="Humidity:",
    text_position=(20, 100),
    text_color=0x8888FF,
    text_font="fonts/Arial-Bold-24.pcf",
)
hum_label = funhouse.add_text(
    text_position=(120, 130),
    text_anchor_point=(0.5, 0.5),
    text_color=0xFFFF00,
    text_font="fonts/Arial-Bold-24.pcf",
)
funhouse.add_text(
    text="Pressure:",
    text_position=(20, 170),
    text_color=0xFF88FF,
    text_font="fonts/Arial-Bold-24.pcf",
)
pres_label = funhouse.add_text(
    text_position=(120, 200),
    text_anchor_point=(0.5, 0.5),
    text_color=0xFFFF00,
    text_font="fonts/Arial-Bold-24.pcf",
)
funhouse.display.show(funhouse.splash)

status = Circle(229, 10, 10, fill=0xFF0000, outline=0x880000)
funhouse.splash.append(status)


def update_enviro():
    global environment

    temp = funhouse.peripherals.temperature
    unit = "C"
    if USE_FAHRENHEIT:
        temp = temp * (9 / 5) + 32
        unit = "F"

    environment["temperature"] = temp
    environment["pressure"] = funhouse.peripherals.pressure
    environment["humidity"] = funhouse.peripherals.relative_humidity
    environment["light"] = funhouse.peripherals.light

    funhouse.set_text("{:.1f}{}".format(environment["temperature"], unit), temp_label)
    funhouse.set_text("{:.1f}%".format(environment["humidity"]), hum_label)
    funhouse.set_text("{}kPa".format(environment["light"]), pres_label)


def connected(client, userdata, result, payload):
    status.fill = 0x00FF00
    status.outline = 0x008800
    print("Connected to MQTT! Subscribing...")
    client.subscribe(LIGHT_COMMAND_TOPIC)


def disconnected(client):
    status.fill = 0xFF0000
    status.outline = 0x880000


def message(client, topic, payload):
    print("Topic {0} received new value: {1}".format(topic, payload))
    if topic == LIGHT_COMMAND_TOPIC:
        settings = json.loads(payload)
        if settings["state"] == "on":
            if "brightness" in settings:
                funhouse.peripherals.dotstars.brightness = settings["brightness"] / 255
            else:
                funhouse.peripherals.dotstars.brightness = 0.3
            if "color" in settings:
                funhouse.peripherals.dotstars.fill(settings["color"])
        else:
            funhouse.peripherals.dotstars.brightness = 0
        publish_light_state()


def publish_light_state():
    funhouse.peripherals.led = True
    output = {
        "brightness": round(funhouse.peripherals.dotstars.brightness * 255),
        "state": "on" if funhouse.peripherals.dotstars.brightness > 0 else "off",
        "color": funhouse.peripherals.dotstars[0],
    }
    # Publish the Dotstar State
    print("Publishing to {}".format(LIGHT_STATE_TOPIC))
    funhouse.network.mqtt_publish(LIGHT_STATE_TOPIC, json.dumps(output))
    funhouse.peripherals.led = False


# Initialize a new MQTT Client object
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

last_publish_timestamp = None

last_peripheral_state = {
    "button_up": funhouse.peripherals.button_up,
    "button_down": funhouse.peripherals.button_down,
    "button_sel": funhouse.peripherals.button_sel,
    "captouch6": funhouse.peripherals.captouch6,
    "captouch7": funhouse.peripherals.captouch7,
    "captouch8": funhouse.peripherals.captouch8,
}

if ENABLE_PIR:
    last_peripheral_state["pir_sensor"] = funhouse.peripherals.pir_sensor

environment = {}
update_enviro()
last_environment_timestamp = time.monotonic()

# Provide Initial light state
publish_light_state()

while True:
    if not environment or (
        time.monotonic() - last_environment_timestamp > ENVIRONMENT_CHECK_DELAY
    ):
        update_enviro()
        last_environment_timestamp = time.monotonic()
    output = environment

    peripheral_state_changed = False
    for peripheral in last_peripheral_state:
        current_item_state = getattr(funhouse.peripherals, peripheral)
        output[peripheral] = "on" if current_item_state else "off"
        if last_peripheral_state[peripheral] != current_item_state:
            peripheral_state_changed = True
            last_peripheral_state[peripheral] = current_item_state

    if funhouse.peripherals.slider is not None:
        output["slider"] = funhouse.peripherals.slider
        peripheral_state_changed = True

    # Every PUBLISH_DELAY, write temp/hum/press/light or if a peripheral changed
    if (
        last_publish_timestamp is None
        or peripheral_state_changed
        or (time.monotonic() - last_publish_timestamp) > PUBLISH_DELAY
    ):
        funhouse.peripherals.led = True
        print("Publishing to {}".format(MQTT_TOPIC))
        funhouse.network.mqtt_publish(MQTT_TOPIC, json.dumps(output))
        funhouse.peripherals.led = False
        last_publish_timestamp = time.monotonic()

    # Check any topics we are subscribed to
    funhouse.network.mqtt_loop(0.5)
