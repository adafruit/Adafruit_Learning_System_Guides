# SPDX-FileCopyrightText: 2019 Brent Rubell for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
PyPortal Smart Scale
an internet of things smart-scale for Adafruit IO

Brent Rubell for Adafruit Industries, 2019
"""

from os import getenv
import time
import board
import adafruit_dymoscale
import busio
import digitalio

import displayio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font

from adafruit_esp32spi import adafruit_esp32spi, adafruit_esp32spi_wifimanager
import neopixel
from adafruit_io.adafruit_io import IO_HTTP

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

# the current working directory (where this file is)
cwd = ("/"+__file__).rsplit('/', 1)[0]
large_font = cwd+"/fonts/Helvetica-Bold-36.bdf"
small_font = cwd+"/fonts/Helvetica-Bold-16.bdf"

root_group = displayio.Group()
print('loading fonts...')
weight_font = bitmap_font.load_font(large_font)
weight_font.load_glyphs(b'0123456789.goz-SCALEROIO ')

text_font = bitmap_font.load_font(small_font)
text_font.load_glyphs(b'sendig!t.')

print('making labels...')
weight_label = Label(weight_font)
weight_label.x = 75
weight_label.y = 120
root_group.append(weight_label)
weight_label.text = "---"

title_label = Label(weight_font)
title_label.x = 65
title_label.y = 20
root_group.append(title_label)
title_label.text = "IO SCALE"

text_label = Label(text_font)
text_label.x = 100
text_label.y = 200
text_label.color = 0xFFFFFF
root_group.append(text_label)

board.DISPLAY.root_group = root_group

# PyPortal ESP32 Setup
esp32_cs = digitalio.DigitalInOut(board.ESP_CS)
esp32_ready = digitalio.DigitalInOut(board.ESP_BUSY)
esp32_reset = digitalio.DigitalInOut(board.ESP_RESET)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
status_pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
wifi = adafruit_esp32spi_wifimanager.WiFiManager(esp, ssid, password, status_pixel=status_pixel)

# Create an instance of the IO_HTTP client
io = IO_HTTP(aio_username, aio_key, wifi)

# Get the weight feed from IO
weight_feed = io.get_feed('weight')

# initialize the dymo scale
units_pin = digitalio.DigitalInOut(board.D3)
units_pin.switch_to_output()
dymo = adafruit_dymoscale.DYMOScale(board.D4, units_pin)

# take a reading of the current time, used for toggling the device out of sleep
time_stamp = time.monotonic()

while True:
    try:
        reading = dymo.weight
        text = "%0.1f g"%reading.weight
        print(text)
        weight_label.text = text
        weight_label.color = 0xFFFFFF
        try:
            print('Sending to Adafruit IO...')
            text_label.text = 'sending...'
            # send data to Adafruit IO (rounded to one decimal place)
            io.send_data(weight_feed['key'], round(reading.weight, 1))
        except (ValueError, RuntimeError, ConnectionError, OSError) as e:
            print("failed to send data..retrying...")
            wifi.reset()
            continue
        print('Data sent!')
        text_label.text = 'sent!'
        # to avoid sleep mode, toggle the units pin every 2mins.
        if (time.monotonic() - time_stamp) > 120:
            print('toggling units button')
            dymo.toggle_unit_button()
            # reset the time
            time_stamp = time.monotonic()
    except RuntimeError as e:
        weight_label.text = "SCALE\nERROR"
        weight_label.color = 0xFF0000
        print("Error: ", e)
