# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Adafruit IO Example for LC709203 Sensor
"""

from os import getenv
import time
import ssl
import alarm
import board
import digitalio
import wifi
import socketpool
import adafruit_requests
from adafruit_io.adafruit_io import IO_HTTP
from adafruit_lc709203f import LC709203F, PackSize

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

# Duration of sleep in seconds. Default is 600 seconds (10 minutes).
# Feather will sleep for this duration between sensor readings / sending data to AdafruitIO
sleep_duration = 600

# Update to match the mAh of your battery for more accurate readings.
# Can be MAH100, MAH200, MAH400, MAH500, MAH1000, MAH2000, MAH3000.
# Choose the closest match. Include "PackSize." before it, as shown.
battery_pack_size = PackSize.MAH400

# Setup the little red LED
led = digitalio.DigitalInOut(board.LED)
led.switch_to_output()

# Set up the LC709203 sensor
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
battery_monitor = LC709203F(i2c)
battery_monitor.pack_size = battery_pack_size

# Collect the sensor data values and format the data
battery_voltage = "{:.2f}".format(battery_monitor.cell_voltage)
battery_percent = "{:.1f}".format(battery_monitor.cell_percent)


def go_to_sleep(sleep_period):
    # Create a an alarm that will trigger sleep_period number of seconds from now.
    time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + sleep_period)
    # Exit and deep sleep until the alarm wakes us.
    alarm.exit_and_deep_sleep_until_alarms(time_alarm)


# Send the data. Requires a feed name and a value to send.
def send_io_data(feed, value):
    return io.send_data(feed["key"], value)


# Wi-Fi connections can have issues! This ensures the code will continue to run.
try:
    # Connect to Wi-Fi
    wifi.radio.connect(ssid, password)
    print(f"Connected to {ssid}!")
    print(f"IP: {wifi.radio.ipv4_address}")

    pool = socketpool.SocketPool(wifi.radio)
    requests = adafruit_requests.Session(pool, ssl.create_default_context())

# Wi-Fi connectivity fails with error messages, not specific errors, so this except is broad.
except Exception as e:  # pylint: disable=broad-except
    print(e)
    go_to_sleep(60)

# Initialize an Adafruit IO HTTP API object
io = IO_HTTP(aio_username, aio_key, requests)

# Turn on the LED to indicate data is being sent.
led.value = True
# Print data values to the serial console. Not necessary for Adafruit IO.
print("Current battery voltage: {0} V".format(battery_voltage))
print("Current battery percent: {0} %".format(battery_percent))

# Adafruit IO sending can run into issues if the network fails!
# This ensures the code will continue to run.
try:
    print("Sending data to AdafruitIO...")
    # Send data to Adafruit IO
    send_io_data(io.create_and_get_feed("battery-voltage"), battery_voltage)
    send_io_data(io.create_and_get_feed("battery-percent"), battery_percent)
    print("Data sent!")
    # Turn off the LED to indicate data sending is complete.
    led.value = False

# Adafruit IO can fail with multiple errors depending on the situation, so this except is broad.
except Exception as e:  # pylint: disable=broad-except
    print(e)
    go_to_sleep(60)

go_to_sleep(sleep_duration)
