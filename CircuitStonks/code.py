# SPDX-FileCopyrightText: 2020 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

from os import getenv
import time
import board
from digitalio import DigitalInOut
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
from adafruit_featherwing import minitft_featherwing
import terminalio
from adafruit_display_text import label
import displayio

minitft = minitft_featherwing.MiniTFTFeatherWing()

# Get WiFi details, ensure these are setup in settings.toml
ssid = getenv("CIRCUITPY_WIFI_SSID")
password = getenv("CIRCUITPY_WIFI_PASSWORD")

if None in [ssid, password]:
    raise RuntimeError(
        "WiFi settings are kept in settings.toml, "
        "please add them there. The settings file must contain "
        "'CIRCUITPY_WIFI_SSID', 'CIRCUITPY_WIFI_PASSWORD', "
        "at a minimum."
    )

# If you are using a board with pre-defined ESP32 Pins:
esp32_cs = DigitalInOut(board.D13)
esp32_ready = DigitalInOut(board.D11)
esp32_reset = DigitalInOut(board.D12)
spi = board.SPI()
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
wifi = adafruit_esp32spi_wifimanager.WiFiManager(esp, ssid, password)

# Symbol "INX" for S&P500, "DJIA" for Dow
DATA_SOURCE = "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&apikey="
DATA_SOURCE += getenv('alphavantage_key')
symbols = ["DJIA", "INX", "AAPL", "TSLA", "MSFT"]

# Set text, font, and color
group = displayio.Group()
symbol_text = label.Label(terminalio.FONT, text="WiFi", color=0xFFFFFF, scale=3)
symbol_text.anchor_point = (0.0, 0.0)
symbol_text.anchored_position = (0, 10)

price_text = label.Label(terminalio.FONT, text="Connect...", color=0xFFFF00, scale=3)
price_text.anchor_point = (0, 1)
price_text.anchored_position = (0, 75)

change_text = label.Label(terminalio.FONT, text="", color=0xFFFF00, scale=2)
change_text.anchor_point = (0, 0)
change_text.anchored_position = (80, 10)

group.append(symbol_text)
group.append(price_text)
group.append(change_text)
minitft.display.root_group = group

refresh = None
i = 0
while True:
    # only query the api every 10 sec (and on first run)
    if (not refresh) or ((time.monotonic() - refresh) > 10):
        try:
            symbol = symbols[i]
            i = (i + 1) % len(symbols)  # go to the next symbol
            response = wifi.get(DATA_SOURCE+"&symbol="+symbol).json()
            print("Response is", response)
            symbol_text.text = response['Global Quote']['01. symbol']
            spot = round(float(response['Global Quote']['05. price']))
            price_text.text = '${:,d}'.format(spot)
            change = float(response['Global Quote']['09. change'])
            print("Price is $", spot, "Change: $", change)
            if change >= 0:
                change_text.text = '+${:,d}'.format(round(change))
                change_text.color = 0x00FF00
            else:
                change_text.text = '-${:,d}'.format(abs(round(change)))
                change_text.color = 0xFF0000
            refresh = time.monotonic()
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
            time.sleep(5)
            continue
    time.sleep(5)
