# SPDX-FileCopyrightText: 2023 Trevor Beaton for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import os
import ssl
import time
import wifi
import board
import displayio
import terminalio
import socketpool
import adafruit_requests

from adafruit_display_text import bitmap_label

# Initialize Wi-Fi connection
try:
    wifi.radio.connect(
        os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")
    )
    print("Connected to %s!" % os.getenv("CIRCUITPY_WIFI_SSID"))
# Wi-Fi connectivity fails with error messages, not specific errors, so this except is broad.
except Exception as e:  # pylint: disable=broad-except
    print(
        "Failed to connect to WiFi. Error:", e, "\nBoard will hard reset in 30 seconds."
    )


# Create a socket pool and session object for making HTTP requests
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

# Set location and units for weather data
UNITS = "metric"
LOCATION = os.getenv("LOCATION")
print("Getting weather for {}".format(LOCATION))

# Set up the URL for fetching weather data
DATA_SOURCE = (
    "http://api.openweathermap.org/data/2.5/weather?q="
    + LOCATION
    + "&units="
    + UNITS
    + "&mode=json"
    + "&appid="
    + os.getenv("OPENWEATHER_KEY")
)

# Define time interval between requests
time_interval = 3000  # set the time interval to 30 minutes

# Set up display a default image
display = board.DISPLAY
bitmap = displayio.OnDiskBitmap("/images/sunny.bmp")
tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)

group = displayio.Group()
group.append(tile_grid)

# Create label for displaying temperature data
text_area = bitmap_label.Label(terminalio.FONT, scale=3)
text_area.anchor_point = (0.5, 0.5)
text_area.anchored_position = (display.width // 2, display.height // 2)

# Create main group to hold all display groups
main_group = displayio.Group()
main_group.append(group)
main_group.append(text_area)
# Show the main group on the display
display.show(main_group)

# Define function to get the appropriate weather icon
def get_weather_condition_icon(weather_condition):
    if "cloud" in weather_condition.lower():
        return "/images/cloudy.bmp"
    elif "rain" in weather_condition.lower():
        return "/images/rain.bmp"
    elif "snow" in weather_condition.lower():
        return "/images/snowy.bmp"
    elif "clear" in weather_condition.lower():
        return "/images/sunny.bmp"
    else:
        return "/images/sunny.bmp"


# Define function to update the background image based on weather conditions
def set_background(weather_condition, background_tile_grid):
    bitmap_path = get_weather_condition_icon(weather_condition)
    background_bitmap = displayio.OnDiskBitmap(bitmap_path)
    background_tile_grid.bitmap = background_bitmap


# Main loop to continuously fetch and display weather data
while True:

    # Fetch weather data from OpenWeatherMap API
    print("Fetching json from", DATA_SOURCE)
    response = requests.get(DATA_SOURCE)
    print(response.json())

    # Extract temperature and weather condition data from API response
    current_temp = response.json()["main"]["temp"]
    max_temp = response.json()["main"]["temp_max"]
    min_temp = response.json()["main"]["temp_min"]
    current_weather_condition = response.json()["weather"][0]["main"]

    print("Weather condition: ", current_weather_condition)

    # Convert temperatures to Fahrenheit
    max_temp = (max_temp * 9 / 5) + 32
    min_temp = (min_temp * 9 / 5) + 32
    current_temp = (current_temp * 9 / 5) + 32

    # Convert temperatures to Fahrenheit to Celsius
    # max_temp = (max_temp - 32) * 5/9
    # min_temp = (min_temp - 32) * 5/9
    # current_temp = (current_temp - 32) * 5/9
    print("Current temperature: {:.1f} °F".format(current_temp))

    # Update label for displaying temperature data
    text_area.text = "{}\n     {:.0f}°F\nH:{:.0f}°F   L:{:.0f}°F".format(
    LOCATION, round(current_temp), round(max_temp), round(min_temp))

    # Update background image
    set_background(current_weather_condition, tile_grid)

    time.sleep(time_interval)
