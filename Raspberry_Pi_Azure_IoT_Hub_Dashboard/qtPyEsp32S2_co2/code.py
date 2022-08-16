# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import json
import digitalio
import supervisor
import board
import rtc
import socketpool
import wifi
import adafruit_ntp
from adafruit_azureiot import IoTHubDevice
import adafruit_scd4x

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

print("Connecting to WiFi...")
wifi.radio.connect(secrets["ssid"], secrets["password"])

print("Connected to WiFi!")

#  ntp clock - update tz_offset to your timezone
pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=0)
rtc.RTC().datetime = ntp.datetime

if time.localtime().tm_year < 2022:
    print("Setting System Time in UTC")
    rtc.RTC().datetime = ntp.datetime

else:
    print("Year seems good, skipping set time.")

esp = None
pool = socketpool.SocketPool(wifi.radio)
# Create an IoT Hub device client and connect
device = IoTHubDevice(pool, esp, secrets["device_connection_string"])

print("Connecting to Azure IoT Hub...")

# Connect to IoT Central
device.connect()

print("Connected to Azure IoT Hub!")

#  setup for I2C
i2c = board.STEMMA_I2C()
#  setup for SCD40
scd4x = adafruit_scd4x.SCD4X(i2c)

#  start measuring co2 with SCD40
scd4x.start_periodic_measurement()
co2 = scd4x.CO2

#  setup boot button as input
button = digitalio.DigitalInOut(board.BUTTON)
button.switch_to_input(pull=digitalio.Pull.UP)

#  clock to count down to sending data to Azure
azure_clock = 500

#  button debounce state
button_pressed = False

while True:
    try:
		#  button debouncing
        if button.value and button_pressed:
            button_pressed = False
		#  if you press boot
        if not button.value and not button_pressed:
            #  pack message
            message = {"CO2": co2,
                       "QT Connected": 1}
            #  send co2 measurement
            device.send_device_to_cloud_message(json.dumps(message))
		#  measure co2
        co2 = scd4x.CO2
		#  when the azure clock runs out
        if azure_clock > 500:
            print("getting msg")
			#  pack message
            message = {"CO2": co2,
                       "QT Connected": 1}
            print("sending json")
            device.send_device_to_cloud_message(json.dumps(message))
            print("data sent")
			#  reset azure clock
            azure_clock = 0
		#  if no clocks are running out
		#  increase counts by 1
        else:
            azure_clock += 1
		#  ping azure
        device.loop()
    #  if something disrupts the loop, reconnect
    # pylint: disable=broad-except
    except (ValueError, RuntimeError, OSError, ConnectionError) as e:
        print("Network error, reconnecting\n", str(e))
        time.sleep(10)
        supervisor.reload()
        continue
	#  delay
    time.sleep(1)
