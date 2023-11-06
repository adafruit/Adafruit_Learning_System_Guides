# SPDX-FileCopyrightText: 2021 John Park for Adafruit Industries
# SPDX-License-Identifier: MIT
# FunHouse PIR Motion Sensor for LIFX light bulbs
import time
import ssl
import socketpool
import wifi
import adafruit_requests
from adafruit_funhouse import FunHouse
import adafruit_lifx

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi and API secrets are kept in secrets.py, please add them there!")
    raise

# choose colors here. Note formatting differences.
default_bulb_color = "#002010"
default_led_color = 0x002010
tripped_bulb_color = "#440044"
tripped_led_color = 0x440044

# Set up ESP32-S2 and adafruit_requests session
wifi.radio.connect(ssid=secrets["ssid"], password=secrets["password"])
pool = socketpool.SocketPool(wifi.radio)
http_session = adafruit_requests.Session(pool, ssl.create_default_context())

# Add your LIFX Personal Access token to secrets.py
# (to obtain a token, visit: https://cloud.lifx.com/settings)
lifx_token = secrets["lifx_token"]

# Set this to your LIFX light separator label
# https://api.developer.lifx.com/docs/selectors
lifx_light = "label:Lamp"

# Initialize the LIFX API Client
lifx = adafruit_lifx.LIFX(http_session, lifx_token)

# List all lights
lights = lifx.list_lights()
# print(lights)  # uncomment for lots of LIFX light info

funhouse = FunHouse(default_bg=0x000F20, scale=3)

pir_state = 0
running_state = False
trip_time = 30  # seconds to stay tripped, adjust this with buttons while running

funhouse.peripherals.dotstars.fill(default_led_color)


def set_label_color(conditional, index, on_color):
    if conditional:
        funhouse.set_text_color(on_color, index)
    else:
        funhouse.set_text_color(0x606060, index)


# Create the labels
funhouse.display.root_group = None
up_label = funhouse.add_text(text="+", text_position=(3, 6), text_color=0x606060)
down_label = funhouse.add_text(text="-", text_position=(3, 40), text_color=0x606060)
running_label = funhouse.add_text(
    text="paused", text_position=(2, 68), text_color=0x606060
)
time_label = funhouse.add_text(
    text=trip_time, text_scale=2, text_position=(30, 25), text_color=0x606060
)

funhouse.display.root_group = funhouse.splash

# Turn on the light
print("Turning on light...")
lifx.toggle_light(lifx_light)

# Set the light's brightness
light_brightness = 0.65
lifx.set_brightness(lifx_light, light_brightness)
lifx.set_color(
    lifx_light, power="on", color=default_bulb_color, brightness=light_brightness
)


while True:

    if funhouse.peripherals.button_up:
        trip_time = trip_time + 1
        funhouse.set_text(trip_time, time_label)
        funhouse.set_text_color(0xFFFFFF, up_label)
        time.sleep(0.2)
    else:
        funhouse.set_text_color(0x606060, up_label)

    if funhouse.peripherals.button_sel:
        trip_time = abs(trip_time - 1)
        funhouse.set_text(trip_time, time_label)
        funhouse.set_text_color(0xFFFFFF, down_label)
        time.sleep(0.2)
    else:
        funhouse.set_text_color(0x606060, down_label)

    if funhouse.peripherals.button_down:
        if running_state is False:  # it's currently paused, so unpause it
            running_state = True  # flip the state
            funhouse.set_text("..prepping..", running_label)
            time.sleep(6)  # pause to get out of range
            funhouse.set_text("sensing...", running_label)

        else:  # it's currently running, so pause it
            running_state = False
            funhouse.set_text("paused", running_label)
            time.sleep(0.5)

    # when sensor is tripped, set the color x amount of time
    if running_state is True and funhouse.peripherals.pir_sensor and pir_state is 0:
        funhouse.peripherals.dotstars.fill(tripped_led_color)
        funhouse.set_text("tripped", running_label)
        lifx.set_color(
            lifx_light,
            power="on",
            color=tripped_bulb_color,
            brightness=light_brightness,
        )
        prior_trip_time = trip_time  # store the state of the trip time value
        for _ in range(trip_time):
            time.sleep(1)
            trip_time = trip_time - 1
            funhouse.set_text(trip_time, time_label)
        pir_state = 1
        trip_time = prior_trip_time  # restore the trip time value

    # return to default color
    elif (
            running_state is True and not funhouse.peripherals.pir_sensor and pir_state is 1
    ):
        funhouse.peripherals.dotstars.fill(default_led_color)
        funhouse.set_text("sensing...", running_label)
        lifx.set_color(
            lifx_light,
            power="on",
            color=default_bulb_color,
            brightness=light_brightness,
        )
        funhouse.set_text(trip_time, time_label)
        pir_state = 0
