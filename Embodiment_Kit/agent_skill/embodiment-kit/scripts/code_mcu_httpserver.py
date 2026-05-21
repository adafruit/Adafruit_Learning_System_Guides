# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT
import json
from os import getenv

import board
import supervisor
import wifi
import socketpool
import rtc
import digitalio
import audiobusio
import pwmio

from adafruit_bme280 import basic as adafruit_bme280
from adafruit_debouncer import Debouncer
import adafruit_veml7700
import adafruit_lis3dh
import adafruit_drv2605
import neopixel
import adafruit_ntp
from embodiment_message_handler import EmbodimentMessageHandler
from adafruit_httpserver import Request, Response, Server, POST

# Get WiFi details and Adafruit IO keys, ensure these are setup in settings.toml
# (visit io.adafruit.com if you need to create an account, or if you need your Adafruit IO key.)
ssid = getenv("CIRCUITPY_WIFI_SSID")
password = getenv("CIRCUITPY_WIFI_PASSWORD")

### WiFi ###
if not wifi.radio.connected:
    print(f"Connecting to {ssid}")
    wifi.radio.connect(ssid, password)
    print(f"Connected to {ssid}!")

# update system time
pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=0, cache_seconds=3600)
cur_time = rtc.RTC()
cur_time.datetime = ntp.datetime

### Initialize hardware components ###
bme280 = adafruit_bme280.Adafruit_BME280_I2C(board.I2C())
veml7700 = adafruit_veml7700.VEML7700(board.I2C())
mic = audiobusio.PDMIn(board.D6, board.D5, sample_rate=16000, bit_depth=16)
buzzer = pwmio.PWMOut(board.D9, variable_frequency=True)

lis3dh = adafruit_lis3dh.LIS3DH_I2C(board.I2C())
lis3dh.data_rate = adafruit_lis3dh.DATARATE_1344_HZ

rgb_strip = neopixel.NeoPixel(board.D10, 8, brightness=0.3, auto_write=True)

drv = adafruit_drv2605.DRV2605(board.I2C())
drv.sequence[0] = adafruit_drv2605.Effect(15)  # Set the effect on slot 0.

embodiment_config = {
    "sensors": [
        {"type": "temperature", "sensor": bme280, "units": "C"},
        {"type": "pressure", "sensor": bme280, "units": "hPa"},
        {"type": "humidity", "sensor": bme280, "units": "%"},
        {"type": "lux", "sensor": veml7700, "units": "lux", "property": "autolux"},
        {"type": "pdm_mic", "sensor": mic, "units": "normalized_rms"},
        {
            "type": "accelerometer",
            "sensor": lis3dh,
            "units": "G",
        },
    ],
    "buttons": {},
    "piezo_buzzer": buzzer,
    "vibration_driver": drv,
    "neopixels": rgb_strip,
    "display": supervisor.runtime.display,
}

pins = [(board.D0, "D0"), (board.D1, "D1"), (board.D2, "D2")]
for pin_i in range(len(pins)):
    pin = pins[pin_i]
    dio = digitalio.DigitalInOut(pin[0])
    dio.direction = digitalio.Direction.INPUT
    # Pins D1 and D2 use different PULL from pin D0
    if pin_i == 0:
        dio.pull = digitalio.Pull.UP
    else:
        dio.pull = digitalio.Pull.DOWN
    btn = Debouncer(dio)
    embodiment_config["buttons"][pin[1]] = btn

embodiment_message_handler = EmbodimentMessageHandler(embodiment_config)

display = supervisor.runtime.display
display.root_group = embodiment_message_handler.main_group

# Set up HTTPServer
server = Server(pool, "/static", debug=True)
server.start(str(wifi.radio.ipv4_address), 5000)


@server.route("/embodiment_kit", POST)
def embodiment_kit(request: Request):
    print("getting data")
    data = request.json()
    print("data: ", data)
    if "messages" in data:
        resp_obj = embodiment_message_handler.handle_messages(data["messages"])
        return Response(request, json.dumps(resp_obj))
    return Response(request, json.dumps({"error": "no messages in request data"}))


while True:
    server.poll()
