# SPDX-FileCopyrightText: Copyright (c) 2021 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
Home Assistant Remote Procedure Call for MacroPad.
"""
import os
import time
import displayio
import terminalio
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label
from adafruit_macropad import MacroPad
from rpc import RpcClient, RpcError, MqttError

macropad = MacroPad()
rpc = RpcClient()

COMMAND_TOPIC = "macropad/peripheral"
SUBSCRIBE_TOPICS = ("stat/demoswitch/POWER", "stat/office-light/POWER")
ENCODER_ITEM = 0
KEY_LABELS = ("Demo", "Office")
UPDATE_DELAY = 0.25
NEOPIXEL_COLORS = {
    "OFF": 0xFF0000,
    "ON": 0x00FF00,
}

# Set up displayio group with all the labels
group = displayio.Group()
for key_index in range(12):
    x = key_index % 3
    y = key_index // 3
    group.append(
        label.Label(
            terminalio.FONT,
            text=(str(KEY_LABELS[key_index]) if key_index < len(KEY_LABELS) else ""),
            color=0xFFFFFF,
            anchored_position=(
                (macropad.display.width - 1) * x / 2,
                macropad.display.height - 1 - (3 - y) * 12,
            ),
            anchor_point=(x / 2, 1.0),
        )
    )
group.append(Rect(0, 0, macropad.display.width, 12, fill=0xFFFFFF))
group.append(
    label.Label(
        terminalio.FONT,
        text="Home Assistant",
        color=0x000000,
        anchored_position=(macropad.display.width // 2, -2),
        anchor_point=(0.5, 0.0),
    )
)
macropad.display.root_group = group

def rpc_call(function, *args, **kwargs):
    response = rpc.call(function, *args, **kwargs)
    if response["error"]:
        if response["error_type"] == "mqtt":
            raise MqttError(response["message"])
        raise RpcError(response["message"])
    return response["return_val"]

def mqtt_init():
    rpc_call(
        "mqtt_init",
        os.getenv("MQTT_BROKER"),
        username=os.getenv("MQTT_USERNAME"),
        password=os.getenv("MQTT_PASSWORD"),
        port=os.getenv("MQTT_PORT"),
    )
    rpc_call("mqtt_connect")

def update_key(key_id):
    if key_id < len(SUBSCRIBE_TOPICS):
        switch_state = rpc_call("mqtt_get_last_value", SUBSCRIBE_TOPICS[key_id])
        if switch_state is not None:
            macropad.pixels[key_id] = NEOPIXEL_COLORS[switch_state]
        else:
            macropad.pixels[key_id] = 0

server_is_running = False
print("Waiting for server...")
while not server_is_running:
    try:
        server_is_running = rpc_call("is_running")
        print("Connected")
    except RpcError:
        pass

mqtt_init()
last_macropad_encoder_value = macropad.encoder

for key_number, topic in enumerate(SUBSCRIBE_TOPICS):
    rpc_call("mqtt_subscribe", topic)
    update_key(key_number)

while True:
    output = {}

    key_event = macropad.keys.events.get()
    if key_event and key_event.pressed:
        output["key_number"] = key_event.key_number

    if macropad.encoder != last_macropad_encoder_value:
        output["encoder"] = macropad.encoder - last_macropad_encoder_value
        last_macropad_encoder_value = macropad.encoder

    macropad.encoder_switch_debounced.update()
    if (
        macropad.encoder_switch_debounced.pressed
        and "key_number" not in output
        and ENCODER_ITEM is not None
    ):
        output["key_number"] = ENCODER_ITEM

    if output:
        try:
            rpc_call("mqtt_publish", COMMAND_TOPIC, output)
            if "key_number" in output:
                time.sleep(UPDATE_DELAY)
                update_key(output["key_number"])
            elif ENCODER_ITEM is not None:
                update_key(ENCODER_ITEM)
        except MqttError:
            mqtt_init()
        except RpcError as err_msg:
            print(err_msg)
