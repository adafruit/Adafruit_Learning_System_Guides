# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import os
import json
import busio
import microcontroller
import board
import rtc
import socketpool
import wifi
import adafruit_ntp
import adafruit_ahtx0
from adafruit_azureiot import IoTCentralDevice

#  use Pico W's GP0 for SDA and GP1 for SCL
i2c = busio.I2C(board.GP1, board.GP0)
aht20 = adafruit_ahtx0.AHTx0(i2c)

print("Connecting to WiFi...")
wifi.radio.connect(os.getenv('WIFI_SSID'), os.getenv('WIFI_PASSWORD'))

print("Connected to WiFi!")

#  ntp clock
pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool)
rtc.RTC().datetime = ntp.datetime

if time.localtime().tm_year < 2022:
    print("Setting System Time in UTC")
    rtc.RTC().datetime = ntp.datetime

else:
    print("Year seems good, skipping set time.")

# Create an IoT Hub device client and connect
esp = None
pool = socketpool.SocketPool(wifi.radio)
device = IoTCentralDevice(
    pool, esp, os.getenv('id_scope'), os.getenv('device_id'), os.getenv('device_primary_key')
)

print("Connecting to Azure IoT Central...")

device.connect()

print("Connected to Azure IoT Central!")

#  clock to count down to sending data to Azure
azure_clock = 500

while True:
    try:
		#  when the azure clock runs out
        if azure_clock > 500:
			#  pack message
            message = {"Temperature": aht20.temperature,
                       "Humidity": aht20.relative_humidity}
            print("sending json")
            device.send_telemetry(json.dumps(message))
            print("data sent")
			#  reset azure clock
            azure_clock = 0
        else:
            azure_clock += 1
		#  ping azure
        device.loop()
	#  if something disrupts the loop, reconnect
    # pylint: disable=broad-except
    #  any errors, reset Pico W
    except Exception as e:
        print("Error:\n", str(e))
        print("Resetting microcontroller in 10 seconds")
        time.sleep(10)
        microcontroller.reset()
	#  delay
    time.sleep(1)
    print(azure_clock)
