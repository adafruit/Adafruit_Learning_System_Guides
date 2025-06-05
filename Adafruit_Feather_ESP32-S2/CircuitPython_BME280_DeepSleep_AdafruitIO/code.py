# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
CircuitPython example for deep sleep and BME280 sensor sending data
to Adafruit IO.
"""
from os import getenv
import time
import alarm
import board
import digitalio
import neopixel
import wifi

from adafruit_bme280 import advanced as adafruit_bme280
import adafruit_connection_manager
import adafruit_requests
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError


# On MagTag, enable power to NeoPixels.
# Remove these two lines on boards without board.NEOPIXEL_POWER.
np_power = digitalio.DigitalInOut(board.NEOPIXEL_POWER)
np_power.switch_to_output(value=True)

builtin_led = digitalio.DigitalInOut(board.LED)
builtin_led.switch_to_output(value=True)

status_pixel = neopixel.NeoPixel(
    board.NEOPIXEL, 1, brightness=0.1, pixel_order=neopixel.GRB, auto_write=True
)
status_pixel[0] = 0xFF0000

# Create sensor object, using the board's default I2C bus.
i2c = board.I2C()  # uses board.SCL and board.SDA
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
print("Found BME280")
# change this to match the location's pressure (hPa) at sea level
bme280.sea_level_pressure = 1013.25

temperature = bme280.temperature * 9 / 5 + 32
humidity = bme280.relative_humidity
pressure = bme280.pressure
print("\nTemperature: %0.1f F" % temperature)
print("Humidity: %0.1f %%" % humidity)
print("Pressure: %0.1f hPa" % pressure)

bme280.mode = adafruit_bme280.MODE_SLEEP
bme280.overscan_temperature = adafruit_bme280.OVERSCAN_X16
bme280.overscan_humidity = adafruit_bme280.OVERSCAN_X16
bme280.overscan_pressure = adafruit_bme280.OVERSCAN_X16
bme280.iir_filter = adafruit_bme280.IIR_FILTER_DISABLE
bme280.standby_period = adafruit_bme280.STANDBY_TC_1000


status_pixel[0] = 0xFFFF00

print("Connecting to AdafruitIO")

# Get WiFi details and Adafruit IO keys, ensure these are setup in settings.toml
# (visit io.adafruit.com if you need to create an account, or if you need your Adafruit IO key.)
ssid = getenv("WIFI_SSID")
password = getenv("WIFI_PASSWORD")
aio_username = getenv("ADAFRUIT_AIO_USERNAME")
aio_key = getenv("ADAFRUIT_AIO_KEY")

print("Connecting to %s" % ssid)
wifi.radio.connect(ssid, password)
print("Connected to %s!" % ssid)

pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
requests = adafruit_requests.Session(pool, ssl_context)
# Initialize an Adafruit IO HTTP API object
io = IO_HTTP(aio_username, aio_key, requests)

status_pixel[0] = 0x00FF00

try:
    # Get the feeds from Adafruit IO
    temperature_feed = io.get_feed("temperature")
    humidity_feed = io.get_feed("humidity")
    pressure_feed = io.get_feed("pressure")

    # send data to the feeds
    io.send_data(temperature_feed["key"], temperature)
    io.send_data(humidity_feed["key"], humidity)
    io.send_data(pressure_feed["key"], pressure)

except AdafruitIO_RequestError as e:
    print(e)
    print(
        "You must create feeds on AdafruitIO for: temperature, humidity, and pressure"
    )

np_power.value = False
builtin_led.value = False

# Create an alarm that will trigger 5 minutes from now.
time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + (5 * 60))
# Exit the program, and then deep sleep until the alarm wakes us.
alarm.exit_and_deep_sleep_until_alarms(time_alarm)
# Does not return, so we never get here.
