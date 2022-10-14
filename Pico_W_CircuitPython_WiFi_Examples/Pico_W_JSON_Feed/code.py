# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import os
import ssl
import wifi
import socketpool
import microcontroller
import adafruit_requests

wifi.radio.connect(os.getenv('WIFI_SSID'), os.getenv('WIFI_PASSWORD'))

# Use cityname, country code where countrycode is ISO3166 format.
# E.g. "New York, US" or "London, GB"
location = "Manhattan, US"

# openweathermap URL, brings in your location & your token
url = "http://api.openweathermap.org/data/2.5/weather?q="+location
url += "&appid="+os.getenv('openweather_token')

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

while True:
    try:
        #  pings openweather
        response = requests.get(url)
        #  packs the response into a JSON
        response_as_json = response.json()
        print()
        #  prints the entire JSON
        print(response_as_json)
        #  gets location name
        place = response_as_json['name']
        #  gets weather type (clouds, sun, etc)
        weather = response_as_json['weather'][0]['main']
        #  gets humidity %
        humidity = response_as_json['main']['humidity']
        #  gets air pressure in hPa
        pressure = response_as_json['main']['pressure']
        #  gets temp in kelvin
        temperature = response_as_json['main']['temp']
        #  converts temp from kelvin to F
        converted_temp = (temperature - 273.15) * 9/5 + 32
        #  converts temp from kelvin to C
        #  converted_temp = temperature - 273.15

        #  prints out weather data formatted nicely as pulled from JSON
        print()
        print("The current weather in %s is:" % place)
        print(weather)
        print("%s°F" % converted_temp)
        print("%s%% Humidity" % humidity)
        print("%s hPa" % pressure)
        #  delay for 5 minutes
        time.sleep(300)
    # pylint: disable=broad-except
    except Exception as e:
        print("Error:\n", str(e))
        print("Resetting microcontroller in 10 seconds")
        time.sleep(10)
        microcontroller.reset()
