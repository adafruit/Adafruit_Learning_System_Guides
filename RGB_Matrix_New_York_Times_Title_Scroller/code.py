# SPDX-FileCopyrightText: 2023 Trevor Beaton for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import time
import ssl
import wifi
import board
import terminalio
import socketpool
from adafruit_matrixportal.matrixportal import MatrixPortal
import adafruit_requests

SCROLL_DELAY = 0.03
time_interval = 5

text_color = 0xFC6900  # e.g., Retro Orange

BASE_URL = "https://api.nytimes.com/svc/topstories/v2/"
CATEGORY = "arts"  # Change this to whatever category you want

# The following values are allowed:
# arts, automobiles, books/review, business, fashion, food, health, home, insider, magazine, movies,
# nyregion, obituaries, opinion, politics, realestate, science, sports, sundayreview, technology,
# theater, t-magazine, travel, upshot, us, world

# --- Wi-Fi setup ---
wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_SSID"))
print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}")

# --- Display setup ---
matrixportal = MatrixPortal(status_neopixel=board.NEOPIXEL, debug=True)

matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(0, (matrixportal.graphics.display.height // 2) - 1),
    scrolling=True,
)

NYT_header_text_area = matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(0, (matrixportal.graphics.display.height // 6) - 1),
)

matrixportal.set_text("NYT:", NYT_header_text_area)

# --- Networking setup ---
context = ssl.create_default_context()
with open("/api-nytimes-com-chain.pem", "rb") as certfile:
    context.load_verify_locations(cadata=certfile.read())

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, context)

NYT_API_KEY = os.getenv("NYT_API_KEY")
DATA_SOURCE = BASE_URL + CATEGORY + ".json?api-key=" + NYT_API_KEY

# --- Main Loop ---
while True:
    print("Fetching json from", DATA_SOURCE)
    response = requests.get(DATA_SOURCE)
    titles = [result["title"] for result in response.json()["results"]]

    for title in titles:
        matrixportal.set_text(title)
        matrixportal.set_text_color(text_color)
        matrixportal.scroll_text(SCROLL_DELAY)

    time.sleep(time_interval)
